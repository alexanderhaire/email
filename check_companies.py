import pyodbc
from config import SQL_SERVER, SQL_USERNAME, SQL_PASSWORD, USE_WINDOWS_AUTH

def get_connection_string_master():
    # Connect to the 'DYNAMICS' system database
    if USE_WINDOWS_AUTH:
        return f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SQL_SERVER};DATABASE=DYNAMICS;Trusted_Connection=yes;"
    else:
        return f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SQL_SERVER};DATABASE=DYNAMICS;UID={SQL_USERNAME};PWD={SQL_PASSWORD}"

def list_companies():
    print("Connecting to DYNAMICS system database...")
    try:
        conn = pyodbc.connect(get_connection_string_master())
        cursor = conn.cursor()
        
        # SY01500 is the Company Master table
        query = "SELECT CMPNYNAM, INTERID FROM SY01500 ORDER BY CMPNYNAM"
        cursor.execute(query)
        
        print("\nAvailable Companies:")
        print(f"{'Company Name':<50} | {'Database ID (INTERID)'}")
        print("-" * 75)
        
        for row in cursor.fetchall():
            print(f"{row.CMPNYNAM:<50} | {row.INTERID}")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
        print("\nNote: Ensure the user has permissions to access the 'DYNAMICS' database.")

if __name__ == "__main__":
    list_companies()
