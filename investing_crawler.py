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
options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
driver = webdriver.Chrome(r'chromedriver',options=options) # put chromedriver path

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
def get_company_info(bs_obj):
    company_name, company_code = get_company_name_code(bs_obj)
    pr_date = datetime.today().strftime("%Y/%m/%d")
    sec_cd = bs_obj.findAll("span", {"class": "elp"})[2].text.replace("\xa0", "")
    mkt_price = bs_obj.find("span", {"id": "last_last"}).text

    company_info = {"PR_DATE": pr_date, "SEC_CD": sec_cd, 'SEC_CD_S': company_code, 'SEC_NM': company_name, "MKT_PRICE": mkt_price}

    blocks = bs_obj.find('div', {'class': 'clear overviewDataTable overviewDataTableWithTooltip'}).children
    for block in blocks:
        if block == '\n': continue

        title = block.find('span', {'class': 'float_lang_base_1'}).text
        value = block.find('span', {'class': 'float_lang_base_2'}).text
        if value == "N/A": value = str(0); # 값이 결측값인 경우 0으로 설정.

        if title == "전일 종가":
            company_info["BASE_PRICE"] = value
        elif title == "거래량":
            company_info["TR_QTY"] = value
        elif title == "발행주식수":
            company_info["LIST_QTY"] = value

    mkt_price = float(company_info["MKT_PRICE"].replace(",", ""))
    tr_qty = float(company_info["TR_QTY"].replace(",", ""))
    base_price = float(company_info["BASE_PRICE"].replace(",", ""))
    tr_amt = mkt_price * tr_qty
    yield_1d = round((mkt_price - base_price) / base_price * 100, 2)

    company_info["TR_AMT"] = tr_amt
    company_info["YIELD_1D"] = yield_1d

    # 과거데이터 텝 url 얻기
    hist_url = "https://kr.investing.com/" + bs_obj.find("ul", {"id": "pairSublinksLevel2"}).findAll("li")[2].find("a").get("href")
    company_info["과거데이터경로"] = hist_url

    return company_info

# get all rows of a stock table
def get_table_rows(option, url="https://kr.investing.com/equities/south-korea"):
    driver.get(url)
    stock_filter = driver.find_element_by_id('stocksFilter')
    selector = Select(stock_filter)
    selector.select_by_visible_text(option)

    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "cross_rate_markets_stocks_1"))
        )
        stock_table = driver.find_element_by_tag_name('tbody')
        rows = stock_table.find_elements_by_tag_name('tr')

        return rows
    except TimeoutException:
        print("time-out")

# get all paths
def get_path_to_company(rows, company_check_list):
    path_to_company = []
    for row in rows:
        td_a_obj = row.find_elements_by_tag_name('td')[1].find_element_by_tag_name('a')
        company_name = td_a_obj.text
        if company_name in company_check_list:
            href = td_a_obj.get_attribute('href')
            path_to_company.append(href)
    return path_to_company

# get options
def get_options(url="https://kr.investing.com/equities/south-korea"):
    driver.get(url)
    options = []
    lists = driver.find_element_by_class_name('selectBox').find_elements_by_tag_name('option')
    for item in lists:
        options.append(item.text)
    return options

# 해당 회사의 과거 데이터 얻기
def get_historical_data(url, start_date, end_date):
    hist_data = []

    driver.get(url)
    picker = driver.find_element_by_id("picker")
    driver.execute_script("$(arguments[0]).click()", picker)

    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "ui-datepicker-div"))
        )

        s_date = driver.find_element_by_id("startDate") # 조회 시작 날짜
        s_date.clear()
        s_date.send_keys(start_date)

        e_date = driver.find_element_by_id("endDate") # 조회 끝 날짜
        e_date.clear()
        e_date.send_keys(end_date)

        driver.find_element_by_xpath('//*[@id="applyBtn"]').click() # 적용

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
                if len(tds) == 1 and tds[0].text == "결과를 찾을 수 없습니다": return hist_data

                pr_date = tds[0].text.replace("년 ", "-").replace("월 ", "-").replace("일", "")
                mkt_price = float(tds[1].text.replace(",", ""))
                tr_qty = tds[5].text
                base_price = hist_data[idx-1]["MKT_PRICE"] if idx != 0 else 0

                if tr_qty[-1] == "K":
                    tr_qty = float(tr_qty[:-1]) * 1000
                elif tr_qty[-1] == "M":
                    tr_qty = float(tr_qty[:-1]) * 1000000
                else:
                    tr_qty = 0

                record["PR_DATE"] = pr_date
                record["MKT_PRICE"] = mkt_price
                record["BASE_PRICE"] = base_price
                record["TR_QTY"] = tr_qty
                record["TR_AMT"] = mkt_price * tr_qty
                record["YIELD_1D"] = round((mkt_price - base_price) / base_price * 100, 2) if base_price != 0 else 0
                hist_data.append(record)

            return hist_data
        except TimeoutException:
            print("time-out")
    except TimeoutException:
        print("time-out")

# 해당 회사 과거 데이터 db 삽입
def insert_hist_data(curs, url, start_date, end_date, sec_cd, sec_cd_s, sec_nm):
    hist_data = get_historical_data(url, start_date, end_date)
    for record in hist_data:
        pr_date = record["PR_DATE"]
        mkt_price = record["MKT_PRICE"]
        tr_qty = record["TR_QTY"]
        tr_amt = record["TR_AMT"]
        base_price = record["BASE_PRICE"]
        yield_1d = record["YIELD_1D"]

        query2 = "INSERT INTO 'database.table' (PR_DATE, SEC_CD, SEC_CD_S, SEC_NM, CLOSE_PRICE, LIST_QTY, VOLUME, TR_AMT, BASE_PRICE, YIELD_1D) " \
                f"VALUES ('{pr_date}', '{sec_cd}', '{sec_cd_s}', '{sec_nm}', '{mkt_price}', '0', '{tr_qty}', '{tr_amt}', '{base_price}', '{yield_1d}');"
        curs.execute(query2)

# 종목코드로 종목 경로 얻기
def get_company_path(check_list, url="https://kr.investing.com/equities/south-korea"):
    path_to_company = []

    driver.get(url)
    search = driver.find_element_by_xpath("/html/body/div[5]/header/div[1]/div/div[3]/div[1]/input")

    for code in check_list:
        search.clear()
        search.send_keys(code)
        print(code)
        sleep(2)

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "/html/body/div[5]/header/div[1]/div/div[3]/div[2]/div[1]/div[1]/div[2]/div/a"))
            )
            path = driver.find_element_by_xpath("/html/body/div[5]/header/div[1]/div/div[3]/div[2]/div[1]/div[1]/div[2]/div/a").get_attribute("href")
            path_to_company.append(path)
        except TimeoutException:
            print("time-out")
    print(len(path_to_company))
    return path_to_company