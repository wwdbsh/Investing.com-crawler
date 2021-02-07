from time import sleep

import requests
from bs4 import BeautifulSoup as bs

from datetime import datetime

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--log-level=3')
options.add_argument("--disable-gpu")
options.add_argument('--ignore-certificate-errors')
options.add_argument('--ignore-ssl-errors')
driver = webdriver.Chrome(r'chromedriver.exe', options=options) # put chromedriver path
keyboard_controller = ActionChains(driver)

# open url
def open_url(url):
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:40.0) Gecko/20100101 Firefox/40.0',
               'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
               'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3'
               }
    response = requests.get(url=url, headers=headers)
    return response.text

# create BeautifulSoup object
def create_bs_obj(html):
    bs_obj = bs(html, 'html.parser')
    return bs_obj

# get company name and code
def get_company_name_code(bs_obj):
    info = bs_obj.find('h1', {'class': 'float_lang_base_1 relativeAttr'}).text.split()
    company_name = ' '.join(info[:-1])
    company_code = info[-1][1:-1].zfill(6 - len(info[-1][1:-1]))
    return company_name, company_code

# get company's info
def get_company_info(bs_obj, url):
    company_name, company_code = get_company_name_code(bs_obj)
    sec_cd = bs_obj.findAll("span", {"class": "elp"})[2].text.replace("\xa0", "")
    
    company_info = {"SEC_CD": sec_cd, 'SEC_CD_S': company_code, 'SEC_NM': company_name}

    # get historical data page url
    company_info["HIST_DATA_PATH"] = url + "-historical-data"
    
    return company_info

# get company's historical data
def get_historical_data(url, start_date, end_date):
    hist_data = []

    driver.get(url)
    try:
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "widgetFieldDateRange")))
        picker = driver.find_element_by_id("widgetFieldDateRange")
        driver.execute_script("$(arguments[0]).click()", picker)

        try:
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "startDate")))
            s_date = driver.find_element_by_id("startDate")
            s_date.clear()
            s_date.send_keys(start_date)
            
            e_date = driver.find_element_by_id("endDate")
            e_date.clear()
            e_date.send_keys(end_date)

            driver.find_element_by_xpath('//*[@id="applyBtn"]').click()

            try:
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.ID, "curr_table"))
                )

                table = driver.find_element_by_id("curr_table")
                table = table.find_element_by_tag_name("tbody")
                table = table.find_elements_by_tag_name("tr")

                for idx, tr in enumerate(reversed(table)):
                    record = {}

                    tds = tr.find_elements_by_tag_name("td")
                    if len(tds) == 1 and (tds[0].text == "No results matched your search" or tds[0].text == "No results found"): return hist_data

                    pr_date = tds[0].text.split()
                    pr_date = pr_date[2] + "-" + get_num_month(pr_date[0]) + "-" + pr_date[1].replace(",", "")

                    mkt_price = float(tds[1].text.replace(",", ""))
                    open_price = float(tds[2].text.replace(",", ""))
                    high_price = float(tds[3].text.replace(",", ""))
                    low_price = float(tds[4].text.replace(",", ""))
                    tr_qty = tds[5].text
                    change = float(tds[6].text.replace("%", "").replace(",", ""))

                    if tr_qty[-1] == "K":
                        tr_qty = float(tr_qty[:-1]) * 1000
                    elif tr_qty[-1] == "M":
                        tr_qty = float(tr_qty[:-1]) * 1000000
                    else:
                        tr_qty = 0

                    record["PR_DATE"] = pr_date
                    record["MKT_PRICE"] = mkt_price
                    record["OPEN_PRICE"] = open_price
                    record["HIGH_PRICE"] = high_price
                    record["LOW_PRICE"] = low_price
                    record["TR_QTY"] = tr_qty
                    record["EXCHANGE_RATE"] = change
                    hist_data.append(record)

                return hist_data
            except TimeoutException:
                print("time-out")
        except TimeoutException:
            print("time-out")
    except TimeoutException:
        print("time-out")
    return hist_data

# insert historical data into database
def insert_hist_data(cur, url, start_date, end_date, sec_cd, sec_cd_s, sec_nm):
    hist_data = get_historical_data(url, start_date, end_date)
    for record in hist_data:
        pr_date = record["PR_DATE"]
        mkt_price = record["MKT_PRICE"]
        open_price = record["OPEN_PRICE"]
        high_price = record["HIGH_PRICE"]
        low_price = record["LOW_PRICE"]
        tr_qty = record["TR_QTY"]
        change = record["EXCHANGE_RATE"]

        try:
            query = "INSERT INTO 'database.table' (PR_DATE, SEC_CD, SEC_CD_S, SEC_NM, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, CLOSE_PRICE, LIST_QTY, VOLUME, EXCHANGE_RATE) " \
                    f"VALUES ('{pr_date}', '{sec_cd}', '{sec_cd_s}', '{sec_nm}', '{open_price}', '{high_price}', '{low_price}', '{mkt_price}', '0', '{tr_qty}', '{change}');"
            cur.execute(query)
        except Exception as e:
            print(e)

# get urls with ISO codes
def get_company_path(curs, check_list, url="https://www.investing.com/equities/"):
    market_exception = ['Stock - OTC Markets']
    path_to_company = []

    driver.get(url)
    search = driver.find_element_by_xpath("/html/body/div[6]/header/div[1]/div/div[3]/div[1]/input")

    for idx, code in enumerate(check_list):
        if code[1] is None:
            search.clear()
            search.send_keys(code[0])
            sleep(3)
            print(code)

            try:
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "/html/body/div[5]/header/div[1]/div/div[3]/div[2]/div[1]/div[1]/div[2]/div/a")))

                list = driver.find_element_by_xpath("/html/body/div[5]/header/div[1]/div/div[3]/div[2]/div[1]/div[1]/div[2]/div")
                items = list.find_elements_by_tag_name("a")
                e = items[0]

                for item in items:
                    spans = item.find_elements_by_tag_name("span")
                    if spans[3].text not in market_exception:
                        e = item
                        break

                path = e.get_attribute("href")
                print(path)

                try:
                    query = f"UPDATE 'database.table' SET WEB_URL='{path}' WHERE SEC_CD='{code[0]}';"
                    curs.execute(query)
                except Exception as e:
                    print(e)
                
                if path not in path_to_company:
                    path_to_company.append(path)

            except TimeoutException:
                print(str(idx) + ": " + code[0] + "=> no result searched.")
            keyboard_controller.send_keys(Keys.ESCAPE).perform()
            WebDriverWait(driver, 20).until(EC.invisibility_of_element_located((By.XPATH, "/html/body/div[5]/header/div[1]/div/div[3]/div[2]/div[1]/div[1]/div[2]/div/a")))
        else:
            print(code)
            path_to_company.append(code[1])

    return path_to_company

# convert month format
def get_num_month(m):
    if m == "Jan":
        m = "01"
    elif m == "Feb":
        m = "02"
    elif m == "Mar":
        m = "03"
    elif m == "Apr":
        m = "04"
    elif m == "May":
        m = "05"
    elif m == "Jun":
        m = "06"
    elif m == "Jul":
        m = "07"
    elif m == "Aug":
        m = "08"
    elif m == "Sep":
        m = "09"
    elif m == "Oct":
        m = "10"
    elif m == "Nov":
        m = "11"
    else:
        m = "12"
    return m
