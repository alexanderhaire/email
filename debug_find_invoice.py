import pyodbc
from invoice_emailer import get_connection_string

def find_invoice(invoice_number):
    conn = pyodbc.connect(get_connection_string())
    cursor = conn.cursor()
    
    print(f"Searching for Invoice: {invoice_number}...")
    
    # Check SOP10100 (Work / Unposted)
    print("\n--- Checking SOP10100 (Unposted/Work) ---")
    query_work = """
    SELECT SOPNUMBE, SOPTYPE, DOCDATE, CREATDDT, DEX_ROW_TS
    FROM SOP10100 
    WHERE SOPNUMBE = ?
    """
    cursor.execute(query_work, invoice_number)
    row = cursor.fetchone()
    if row:
        print(f"FOUND in SOP10100!")
        print(f"  SOPNUMBE: {row.SOPNUMBE}")
        print(f"  DOCDATE:  {row.DOCDATE}")
        print(f"  CREATDDT: {row.CREATDDT}")
        print(f"  Last Mod: {row.DEX_ROW_TS}")
    else:
        print("Not found in SOP10100.")

    # Check SOP30200 (History / Posted)
    print("\n--- Checking SOP30200 (Posted/History) ---")
    query_hist = """
    SELECT SOPNUMBE, SOPTYPE, DOCDATE, CREATDDT, DEX_ROW_TS
    FROM SOP30200 
    WHERE SOPNUMBE = ?
    """
    cursor.execute(query_hist, invoice_number)
    row = cursor.fetchone()
    if row:
        print(f"FOUND in SOP30200!")
        print(f"  SOPNUMBE: {row.SOPNUMBE}")
        print(f"  DOCDATE:  {row.DOCDATE}")
        print(f"  CREATDDT: {row.CREATDDT}")
        print(f"  Last Mod: {row.DEX_ROW_TS}")
    else:
        print("Not found in SOP30200.")
        
    conn.close()

if __name__ == "__main__":
    # Invoice from screenshot
    find_invoice("100004461")
