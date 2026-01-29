import pyodbc
from invoice_emailer import get_connection_string
from config import START_FROM_INVOICE_NUMBER

def list_recent_invoices():
    conn = pyodbc.connect(get_connection_string())
    cursor = conn.cursor()
    
    print(f"Checking for Invoices > {START_FROM_INVOICE_NUMBER}...")
    
    query = """
    SELECT SOPNUMBE, DOCDATE, CUSTNMBR, DOCAMNT
    FROM SOP30200 
    WHERE SOPTYPE = 3 
    AND VOIDSTTS = 0
    AND SOPNUMBE > ?
    ORDER BY SOPNUMBE ASC
    """
    
    cursor.execute(query, START_FROM_INVOICE_NUMBER)
    rows = cursor.fetchall()
    
    if rows:
        print(f"\nFOUND {len(rows)} INVOICES:")
        for row in rows:
            print(f"  - {row.SOPNUMBE} | Date: {row.DOCDATE} | Cust: {row.CUSTNMBR} | Amt: ${row.DOCAMNT:,.2f}")
    else:
        print("\nNO invoices found greater than that number.")
        
    conn.close()

if __name__ == "__main__":
    list_recent_invoices()
