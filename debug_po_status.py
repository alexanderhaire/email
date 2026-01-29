
import pyodbc
from config import (
    SQL_SERVER, SQL_DATABASE, SQL_USERNAME, SQL_PASSWORD,
    USE_WINDOWS_AUTH, USE_DSN, DSN_NAME
)

def get_connection_string():
    if USE_DSN:
        if USE_WINDOWS_AUTH:
            return f"DSN={DSN_NAME};DATABASE={SQL_DATABASE};Trusted_Connection=yes;"
        else:
            return f"DSN={DSN_NAME};DATABASE={SQL_DATABASE};UID={SQL_USERNAME};PWD={SQL_PASSWORD}"
    if USE_WINDOWS_AUTH:
        return f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SQL_SERVER};DATABASE={SQL_DATABASE};Trusted_Connection=yes;"
    else:
        return f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SQL_SERVER};DATABASE={SQL_DATABASE};UID={SQL_USERNAME};PWD={SQL_PASSWORD}"

def check_po_status(po_number):
    try:
        conn = pyodbc.connect(get_connection_string())
        cursor = conn.cursor()
        
        query = "SELECT PONUMBER, POSTATUS, DEX_ROW_TS, CREATDDT FROM POP10100 WHERE PONUMBER = ?"
        cursor.execute(query, (po_number,))
        row = cursor.fetchone()
        
        if row:
            print(f"PO: {row.PONUMBER}, Status: {row.POSTATUS}, Created: {row.CREATDDT}, Modified: {row.DEX_ROW_TS}")
        else:
            print(f"PO {po_number} not found.")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("Checking PO Status...")
    check_po_status('431-8113')
    check_po_status('431-8134')
