import pyodbc
import json
from config import SQL_SERVER, SQL_DATABASE, USE_DSN, DSN_NAME, USE_WINDOWS_AUTH, SQL_USERNAME, SQL_PASSWORD

def get_connection_string():
    if USE_DSN:
        if USE_WINDOWS_AUTH:
            return f"DSN={DSN_NAME};DATABASE={SQL_DATABASE};Trusted_Connection=yes;"
        else:
            return f"DSN={DSN_NAME};DATABASE={SQL_DATABASE};UID={SQL_USERNAME};PWD={SQL_PASSWORD}"
    return f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SQL_SERVER};DATABASE={SQL_DATABASE};Trusted_Connection=yes;"

def search_entities_db(table_name, id_col, name_col, address_col, master_type, search_term):
    conn_str = get_connection_string()
    print(f"Connecting with: {conn_str}")
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    search_pattern = f"%{search_term}%"
    
    query = f"""
    SELECT TOP 50
        m.{id_col}, 
        m.{name_col}, 
        COALESCE(inet.EmailToAddress, inet.INET1, '') as Email
    FROM {table_name} m
    LEFT JOIN SY01200 inet ON inet.Master_Type = ? 
        AND inet.Master_ID = m.{id_col} 
        AND inet.ADRSCODE = m.{address_col}
    WHERE m.{id_col} LIKE ? OR m.{name_col} LIKE ?
    ORDER BY m.{id_col}
    """
    
    print(f"Searching {table_name} for '{search_term}'...")
    cursor.execute(query, (master_type, search_pattern, search_pattern))
    
    rows = cursor.fetchall()
    if not rows:
        print("  No matches found.")
    for row in rows:
        print(f"  FOUND: {row[0]} - {row[1]} (Email: {row[2]})")
    conn.close()

if __name__ == "__main__":
    term = "ya" 
    print("--- Testing CUSTOMER Search (RM00101) ---")
    search_entities_db("RM00101", "CUSTNMBR", "CUSTNAME", "ADRSCODE", "CUS", term)
    print("\n--- Testing VENDOR Search (PM00200) ---")
    search_entities_db("PM00200", "VENDORID", "VENDNAME", "VADDCDPR", "VEN", term)
