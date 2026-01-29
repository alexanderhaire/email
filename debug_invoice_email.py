
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

def debug_invoice_details(invoice_number):
    print(f"Checking full details for: {invoice_number}")
    conn = pyodbc.connect(get_connection_string())
    cursor = conn.cursor()
    
    query = """
    SELECT 
        h.SOPNUMBE as InvoiceNumber,
        h.DOCDATE as InvoiceDate,
        h.CUSTNMBR as CustomerID,
        c.CUSTNAME as CustomerName,
        COALESCE(inet.EmailToAddress, inet.INET1) as CustomerEmail
    FROM SOP30200 h
    INNER JOIN RM00101 c ON h.CUSTNMBR = c.CUSTNMBR
    LEFT JOIN SY01200 inet ON inet.Master_Type = 'CUS' 
        AND inet.Master_ID = h.CUSTNMBR 
        AND inet.ADRSCODE = c.ADRSCODE
    WHERE h.SOPNUMBE = ?
    """
    
    cursor.execute(query, (invoice_number,))
    row = cursor.fetchone()
    
    if row:
        print(f"Invoice Found:")
        print(f"  Number: {row.InvoiceNumber}")
        print(f"  Date: {row.InvoiceDate}")
        print(f"  Customer: {row.CustomerName} ({row.CustomerID})")
        print(f"  Email: {row.CustomerEmail}")
    else:
        print("Invoice NOT returned by main query logic.")
        
    conn.close()

if __name__ == "__main__":
    debug_invoice_details("100004467")
