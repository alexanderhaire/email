
import pyodbc
from datetime import datetime
from config import (
    SQL_SERVER, SQL_DATABASE, SQL_USERNAME, SQL_PASSWORD,
    USE_WINDOWS_AUTH, USE_DSN, DSN_NAME
)

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

def verify_fix():
    print("Verifying fix...")
    conn = pyodbc.connect(get_connection_string())
    cursor = conn.cursor()
    
    # Timestamp from start of today to ensure we would have caught them
    ts = datetime(2026, 1, 23, 0, 0, 0)
    
    # The NEW Query logic
    query = """
    SELECT 
        h.PONUMBER, h.POSTATUS
    FROM POP10100 h
    WHERE h.POSTATUS = 1 
    AND h.DEX_ROW_TS > ?
    AND h.PONUMBER IN ('431-8113', '431-8134')
    """
    
    cursor.execute(query, (ts,))
    rows = cursor.fetchall()
    
    if len(rows) == 0:
        print("PASS: No POs found with Status 4 (Received). The fix is working.")
    else:
        print(f"FAIL: Found {len(rows)} POs that should have been excluded:")
        for row in rows:
            print(f"  PO: {row.PONUMBER}, Status: {row.POSTATUS}")
            
    # Also verify we can still see them if we remove the check (sanity check)
    query_sanity = """
    SELECT 
        h.PONUMBER, h.POSTATUS
    FROM POP10100 h
    WHERE h.DEX_ROW_TS > ?
    AND h.PONUMBER IN ('431-8113', '431-8134')
    """
    cursor.execute(query_sanity, (ts,))
    rows_sanity = cursor.fetchall()
    print(f"\nSanity Check: {len(rows_sanity)} POs found without status filter (Expected: 2)")
    for row in rows_sanity:
         print(f"  PO: {row.PONUMBER}, Status: {row.POSTATUS}")

    conn.close()

if __name__ == "__main__":
    verify_fix()
