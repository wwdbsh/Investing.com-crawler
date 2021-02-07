import sys
import numpy as np
from time import sleep
from datetime import datetime

from get_db_connection import get_connection
from investing_crawler_global import *

def main():
    query1 = "SELECT SEC_CD, WEB_URL FROM 'database.table' WHERE NATION_CD='KOR' AND WEB_URL IS NOT null;" # write query to get ISIN code and stock item page web url.

    conn = get_connection()
    curs = conn.cursor()
    curs.execute(query1)
    company_check_list = curs.fetchall()
    company_check_list = [(record[0], record[1]) for record in company_check_list]
    path_to_company = get_company_path(curs, company_check_list)
    # print(path_to_company)

    tday = datetime.today().strftime("%m/%d/%Y")

    for idx, url in enumerate(path_to_company):
        try:
            html = open_url(url)
            bs_obj = create_bs_obj(html)
            company_info = get_company_info(bs_obj, url)
            if company_info is False: continue

            sec_cd = company_info["SEC_CD"]
            sec_cd_s = company_info["SEC_CD_S"]
            sec_nm = company_info["SEC_NM"]
            insert_hist_data(curs, company_info["HIST_DATA_PATH"], tday, tday, sec_cd, sec_cd_s, sec_nm)
            print(idx, company_info)
        except Exception as e:
            print(e)
    conn.close()
    sys.exit()

main()