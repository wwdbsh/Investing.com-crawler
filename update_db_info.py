import numpy as np
from time import sleep

from get_db_connection import get_connection
from investing_crawler_global import *

'''
PR_DATE: 거래날짜 VARCHAR
SEC_CD: 회사코드(long) VARCHAR
SEC_CD_S: 회사코드(short) VARCHAR
SEC_NM: 회사명 VARCHAR
MKT_PRICE: 현재가 DOUBLE
LIST_QTY: 발행주식수 DOUBLE
TR_QTY: 거래량 DOUBLE
TR_AMT: MKT_PRICE * TR_QTY DOUBLE
BASE_PRICE: 전일 종가 DOUBLE
YIELD_1D: 전일대비 하루 수익률 (MKT_PRICE * BASE_PRICE)/BASE_PRICE * 100 DOUBLE
'''
def main():
    query1 = "SELECT SEC_CD FROM 'database.table';"

    conn = get_connection()
    curs = conn.cursor()
    curs.execute(query1)
    company_check_list = curs.fetchall()
    company_check_list = [record[0] for record in company_check_list] # db에서 회사 이름 가져오기
    path_to_company = get_company_path(company_check_list)

    print(path_to_company)
    for idx, url in enumerate(path_to_company):
        sleep(np.random.randint(3))
        html = open_url(url)
        bs_obj = create_bs_obj(html)
        company_info = get_company_info(bs_obj)
    
        sec_cd = company_info["SEC_CD"]
        sec_cd_s = company_info["SEC_CD_S"]
        sec_nm = company_info["SEC_NM"]
    

        insert_hist_data(curs, url, "01/01/1970", "06/01/2020", sec_cd, sec_cd_s, sec_nm)
    
        # 당일 데이터 갱신
        # pr_date = company_info["PR_DATE"]
        # mkt_price = float(company_info["MKT_PRICE"].replace(",", ""))
        # tr_qty = float(company_info["TR_QTY"].replace(",", ""))
        # tr_amt = company_info["TR_AMT"]
        # base_price = float(company_info["BASE_PRICE"].replace(",", ""))
        # list_qty = float(company_info["LIST_QTY"].replace(",", ""))
        # yield_1d = company_info["YIELD_1D"]

        # query3 = "INSERT INTO fmsoft.ch6100 (PR_DATE, SEC_CD, SEC_CD_S, SEC_NM, CLOSE_PRICE, LIST_QTY, VOLUME, TR_AMT, BASE_PRICE, YIELD_1D) " \
        #          f"VALUES ('{pr_date}', '{sec_cd}', '{sec_cd_s}', '{sec_nm}', '{mkt_price}', '{list_qty}', '{tr_qty}', '{tr_amt}', '{base_price}', '{yield_1d}');"
        # curs.execute(query3)
    
        print(idx, company_info)
        break

    conn.close()

main()