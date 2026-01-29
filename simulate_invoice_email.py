from datetime import datetime
from invoice_emailer import send_invoice_email
from config import TEST_EMAIL_RECIPIENT

def simulate_test():
    # Create a dummy invoice object similar to what the SQL query returns
    dummy_invoice = {
        'number': 'INV00099999',
        'date': datetime.now(),
        'amount': 1250.55,
        'customer_id': 'TEST-CUST001',
        'customer_name': 'Acme Test Corp',
        'email': 'customer@example.com' # This will be redirected to you
    }
    
    print(f"Simulating invoice for {dummy_invoice['customer_name']}...")
    print(f"Original recipient would be: {dummy_invoice['email']}")
    print(f"Actual recipient (Safety Mode): {TEST_EMAIL_RECIPIENT}")
    
    # Call the actual email function
    success = send_invoice_email(dummy_invoice)
    
    if success:
        print("\n✓ Simulation successful! Check your inbox.")
    else:
        print("\n✗ Simulation failed.")

if __name__ == "__main__":
    simulate_test()
