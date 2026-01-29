
import pyodbc
import po_emailer
from config import TEST_EMAIL_RECIPIENT

def test_single_po(po_number):
    print(f"Testing PO Email for: {po_number}")
    
    # Connect
    conn = pyodbc.connect(po_emailer.get_connection_string())
    
    # Get Details
    po = po_emailer.get_po_details(conn, po_number)
    
    if po:
        print("PO Found:")
        print(f"  Vendor: {po['vendor_name']}")
        print(f"  Amount: ${po['amount']:,.2f}")
        print(f"  Existing Email: {po['email']}")
        print(f"  Lines: {len(po['lines'])}")
        
        # Override email for safety testing
        print(f"  Create Override: Sending to {TEST_EMAIL_RECIPIENT} instead of vendor.")
        po['email'] = TEST_EMAIL_RECIPIENT
        
        # Send
        print("Sending email...")
        success = po_emailer.send_po_email(po)
        
        if success:
            print("✓ Email Sent Successfully!")
        else:
            print("✗ Email Failed.")
            
    else:
        print("PO Not Found")
        
    conn.close()

if __name__ == "__main__":
    # Use the latest PO
    test_single_po("431-8142")
