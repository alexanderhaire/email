
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

def check_dates(invoice_number):
    print(f"Checking dates for: {invoice_number}")
    conn = pyodbc.connect(get_connection_string())
    cursor = conn.cursor()
    
    query = """
    SELECT 
        SOPNUMBE, 
        DOCDATE, 
        GLPOSTDT, 
        QUOTEDAT, 
        ORDRDATE, 
        INVODATE, 
        BACKDATE, 
        DEX_ROW_TS
    FROM SOP30200 
    WHERE SOPNUMBE = ?
    """
    
    cursor.execute(query, (invoice_number,))
    row = cursor.fetchone()
    
    if row:
        columns = [column[0] for column in cursor.description]
        for col, val in zip(columns, row):
            print(f"  {col}: {val}")
    else:
        print("Invoice NOT found.")
        
    conn.close()

if __name__ == "__main__":
    check_dates("100004472")
    check_dates("100004473")
