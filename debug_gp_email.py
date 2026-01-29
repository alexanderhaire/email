import pyodbc
from invoice_emailer import get_connection_string

def list_columns(conn, table_name):
    cursor = conn.cursor()
    print(f"\n--- Columns in {table_name} ---")
    try:
        cursor.execute(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{table_name}' ORDER BY COLUMN_NAME")
        columns = [row.COLUMN_NAME for row in cursor.fetchall()]
        # Filter for anything that looks like email or internet
        relevant = [c for c in columns if 'EMAIL' in c.upper() or 'INET' in c.upper() or 'ADDRESS' in c.upper()]
        print(f"Relevant columns: {relevant}")
    except Exception as e:
        print(f"Error reading {table_name}: {e}")

def main():
    try:
        conn = pyodbc.connect(get_connection_string())
        print("Connected.")
        
        list_columns(conn, 'RM00101') # Customer Master
        list_columns(conn, 'RM00102') # Address Master
        list_columns(conn, 'SY01200') # Internet Info (Likely here)

        conn.close()
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    main()
