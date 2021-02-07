import pymysql

def get_connection():
    conn = pymysql.connect(host="", user="", password="", db="", charset="utf8") # put db information
    return conn
