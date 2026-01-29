
import pyodbc
from invoice_emailer import get_connection_string

def check_po():
    conn = pyodbc.connect(get_connection_string())
    cursor = conn.cursor()
    
    query = """
    SELECT TOP 1 PONUMBER, DOCDATE, CREATDDT
    FROM POP10100
    WHERE POSTATUS >= 1
    ORDER BY CREATDDT DESC
    """
    cursor.execute(query)
    row = cursor.fetchone()
    
    if row:
        print(f"PO: {row.PONUMBER}")
        print(f"DOCDATE:    {row.DOCDATE}")
        print(f"CREATDDT:   {row.CREATDDT}")
    else:
        print("No POs found")
        
    conn.close()

if __name__ == "__main__":
    check_po()
