
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

def check_po_tables():
    conn = pyodbc.connect(get_connection_string())
    cursor = conn.cursor()
    
    print("Checking PM00200 (Vendor Master) Schema...")
    try:
        cursor.execute("SELECT TOP 1 * FROM PM00200")
        columns = [column[0] for column in cursor.description]
        print(f"Columns: {columns}")
        
    except Exception as e:
        print(f"Error checking PM00200: {e}")

    conn.close()

if __name__ == "__main__":
    check_po_tables()
