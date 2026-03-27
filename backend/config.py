import mysql.connector
from mysql.connector import Error

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',   
    'database': 'ban_ve_may_bay',
    'charset': 'utf8mb4'
}

def get_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"Lỗi kết nối database: {e}")
        return None