
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

def check_specific_po(po_number):
    print(f"Checking PO: {po_number}")
    try:
        conn = pyodbc.connect(get_connection_string())
        cursor = conn.cursor()
        
        query = """
        SELECT PONUMBER, DOCDATE, CREATDDT, MODIFDT, POSTATUS, DEX_ROW_TS
        FROM POP10100
        WHERE PONUMBER = ?
        """
        cursor.execute(query, (po_number,))
        row = cursor.fetchone()
        
        if row:
            print(f"FOUND PO: {row.PONUMBER}")
            print(f"  POSTATUS:   {row.POSTATUS}")
            print(f"  DOCDATE:    {row.DOCDATE}")
            print(f"  CREATDDT:   {row.CREATDDT} (Created Date)")
            print(f"  MODIFDT:    {row.MODIFDT} (Modified Date)")
            print(f"  DEX_ROW_TS: {row.DEX_ROW_TS}")
        else:
            print("❌ PO NOT FOUND in POP10100")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_specific_po("431-8144")
