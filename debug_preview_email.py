
import os
from datetime import datetime
from invoice_emailer import send_invoice_email  # We'll mock the send part or just inspect the HTML building
import resend

# Mock invoice data
mock_invoice = {
    'number': '100004467',
    'date': datetime(2026, 1, 21),
    'amount': 3450.75,
    'subtotal': 3200.00,
    'freight': 150.00,
    'tax': 100.75,
    'discount': 0.00,
    'po_number': 'PO-998877',
    'customer_id': 'GREENRES',
    'customer_name': 'Green Resource LLC',
    'email': 'janec@chemicaldynamics.com',
    'lines': [
        {'item_number': 'CHEM-001', 'description': 'Industrial Solvent (55 Gal)', 'quantity': 2.0, 'unit_price': 850.00, 'extended_price': 1700.00, 'uom': 'Drum'},
        {'item_number': 'CHEM-002', 'description': 'Safety Gloves (Box of 100)', 'quantity': 5.0, 'unit_price': 25.00, 'extended_price': 125.00, 'uom': 'Box'},
        {'item_number': 'CHEM-003', 'description': 'Mixing Agent A', 'quantity': 10.0, 'unit_price': 137.50, 'extended_price': 1375.00, 'uom': 'Gal'}
    ]
}

# Monkey patch resend.Emails.send to just save the HTML
def capture_email(params):
    print(f"Captured email to {params['to']}")
    with open('email_preview.html', 'w', encoding='utf-8') as f:
        f.write(params['html'])
    print("HTML saved to email_preview.html")

resend.Emails.send = capture_email

# Run the function
if __name__ == "__main__":
    print("Generating Email Preview...")
    send_invoice_email(mock_invoice)
