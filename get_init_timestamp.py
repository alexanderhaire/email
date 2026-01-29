
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

def get_max_timestamp():
    conn = pyodbc.connect(get_connection_string())
    cursor = conn.cursor()
    
    # Get the Maximum DEX_ROW_TS from invoices today to initialize our watermark
    query = """
    SELECT MAX(DEX_ROW_TS) as MaxTS
    FROM SOP30200
    WHERE SOPTYPE = 3 
    AND DOCDATE >= CAST(GETDATE() AS DATE)
    """
    
    cursor.execute(query)
    row = cursor.fetchone()
    if row and row.MaxTS:
        print(f"{row.MaxTS}")
    else:
        print("No invoices found.")
        
    conn.close()

if __name__ == "__main__":
    get_max_timestamp()
