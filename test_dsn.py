import pyodbc

def test_dsn(dsn_name):
    print(f"Testing DSN: {dsn_name}...")
    conn_str = f"DSN={dsn_name};Trusted_Connection=yes;"
    try:
        conn = pyodbc.connect(conn_str)
        print("  ✓ Connected successfully!")
        
        cursor = conn.cursor()
        cursor.execute("SELECT DB_NAME()")
        db_name = cursor.fetchone()[0]
        print(f"  → Current Database: {db_name}")
        
        conn.close()
        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return False

if __name__ == "__main__":
    dsns = ["Customix_Dynamics", "Customix"]
    for dsn in dsns:
        test_dsn(dsn)
