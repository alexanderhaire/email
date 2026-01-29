import pyodbc
from datetime import datetime
from invoice_emailer import get_connection_string

def check_time():
    conn = pyodbc.connect(get_connection_string())
    cursor = conn.cursor()
    
    local_time = datetime.now()
    print(f"Local Machine Time: {local_time}")
    
    cursor.execute("SELECT GETDATE(), GETUTCDATE()")
    row = cursor.fetchone()
    print(f"SQL Server GETDATE():   {row[0]}")
    print(f"SQL Server GETUTCDATE(): {row[1]}")
    
    conn.close()

if __name__ == "__main__":
    check_time()
