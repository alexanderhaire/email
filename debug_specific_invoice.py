
import pyodbc
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

def check_invoice(invoice_number):
    print(f"Checking invoice: {invoice_number}")
    conn = pyodbc.connect(get_connection_string())
    cursor = conn.cursor()
    
    # Check SOP30200 (History)
    query_hist = "SELECT SOPNUMBE, DOCDATE, SOPTYPE, VOIDSTTS, DEX_ROW_TS FROM SOP30200 WHERE SOPNUMBE = ?"
    cursor.execute(query_hist, (invoice_number,))
    row = cursor.fetchone()
    if row:
        print(f"FOUND in SOP30200 (History):")
        print(f"  Date: {row.DOCDATE}")
        print(f"  Type: {row.SOPTYPE} (3=Invoice)")
        print(f"  Void: {row.VOIDSTTS}")
        print(f"  Timestamp: {row.DEX_ROW_TS}")
    else:
        print("NOT FOUND in SOP30200 (History)")

    # Check SOP10100 (Work/Unposted)
    query_work = "SELECT SOPNUMBE, DOCDATE, SOPTYPE, VOIDSTTS, DEX_ROW_TS FROM SOP10100 WHERE SOPNUMBE = ?"
    cursor.execute(query_work, (invoice_number,))
    row = cursor.fetchone()
    if row:
        print(f"FOUND in SOP10100 (Work/Unposted):")
        print(f"  Date: {row.DOCDATE}")
        print(f"  Type: {row.SOPTYPE}")
        print(f"  Void: {row.VOIDSTTS}")
        print(f"  Timestamp: {row.DEX_ROW_TS}")
    else:
        print("NOT FOUND in SOP10100 (Work)")
        
    conn.close()

if __name__ == "__main__":
    check_invoice("100004467")
