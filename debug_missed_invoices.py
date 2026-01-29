
import pyodbc
from datetime import datetime
from config import SQL_SERVER, SQL_DATABASE, SQL_USERNAME, SQL_PASSWORD, USE_WINDOWS_AUTH, USE_DSN, DSN_NAME

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

def find_mismatched_invoices():
    print("Searching for invoices created TODAY but dated YESTERDAY (or earlier)...")
    conn = pyodbc.connect(get_connection_string())
    cursor = conn.cursor()
    
    # Query for invoices created in the last 24 hours but with DOCDATE < Today
    # Note: DEX_ROW_TS is UTC, so we look for recent ones.
    # We'll just look for DEX_ROW_TS >= '2026-01-22' (Server Time)
    
    query = """
    SELECT SOPNUMBE, DOCDATE, DEX_ROW_TS
    FROM SOP30200
    WHERE SOPTYPE = 3
    AND DEX_ROW_TS >= CAST(GETDATE() AS DATE) 
    AND DOCDATE < CAST(GETDATE() AS DATE)
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    
    if rows:
        print(f"Found {len(rows)} potentially missed invoices:")
        for row in rows:
            print(f"  {row.SOPNUMBE} - DocDate: {row.DOCDATE}, Created: {row.DEX_ROW_TS}")
    else:
        print("No mismatched invoices found.")
        
    conn.close()

if __name__ == "__main__":
    find_mismatched_invoices()
