
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

def main():
    conn = pyodbc.connect(get_connection_string())
    cursor = conn.cursor()
    
    po_number = "431-8147"
    print(f"Checking details for PO: {po_number}")
    
    query = """
    SELECT PONUMBER, POSTATUS, STATGRP, CREATDDT, DEX_ROW_TS, VENDORID
    FROM POP10100
    WHERE PONUMBER = ?
    """
    
    cursor.execute(query, (po_number,))
    row = cursor.fetchone()
    
    if row:
        print(f"Found PO {row.PONUMBER}")
        print(f"POSTATUS: {row.POSTATUS}")
        print(f"STATGRP: {row.STATGRP}")
        print(f"CREATDDT: {row.CREATDDT}")
        print(f"DEX_ROW_TS: {row.DEX_ROW_TS}")
        
        # Check last check time
        try:
            with open("last_po_check.txt", "r") as f:
                last_check = f.read().strip()
                print(f"Last Check Time: {last_check}")
                
            if str(row.DEX_ROW_TS) > last_check:
                print("DEX_ROW_TS is NEWER than last check (Should have been picked up if STATUS matched)")
            else:
                print("DEX_ROW_TS is OLDER than last check")
                
        except Exception as e:
            print(f"Error reading last check: {e}")
            
    else:
        print("PO not found in POP10100")

    conn.close()

if __name__ == "__main__":
    main()
