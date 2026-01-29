
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

def check_time():
    print(f"Python Local: {datetime.now()}")
    print(f"Python UTC:   {datetime.utcnow()}")
    
    conn = pyodbc.connect(get_connection_string())
    cursor = conn.cursor()
    
    cursor.execute("SELECT GETDATE(), GETUTCDATE()")
    row = cursor.fetchone()
    print(f"SQL GETDATE:  {row[0]}")
    print(f"SQL UTC:      {row[1]}")
    
    conn.close()

if __name__ == "__main__":
    check_time()
