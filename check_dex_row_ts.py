
import pyodbc
from invoice_emailer import get_connection_string

def check_ts():
    conn = pyodbc.connect(get_connection_string())
    cursor = conn.cursor()
    
    # Get the latest invoice's timestamps
    query = """
    SELECT TOP 1 SOPNUMBE, DOCDATE, DEX_ROW_TS, GETUTCDATE() as CurrentUTC
    FROM SOP30200 
    WHERE SOPTYPE = 3
    ORDER BY DEX_ROW_TS DESC
    """
    cursor.execute(query)
    row = cursor.fetchone()
    
    if row:
        print(f"Invoice: {row.SOPNUMBE}")
        print(f"DOCDATE:    {row.DOCDATE}")
        print(f"DEX_ROW_TS: {row.DEX_ROW_TS}")
        print(f"CurrentUTC: {row.CurrentUTC}")
    else:
        print("No invoices found")
        
    conn.close()

if __name__ == "__main__":
    check_ts()
