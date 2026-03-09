"""
Test script to send a specific invoice
"""
import pyodbc
import json
from config import *
from invoice_emailer import (
    get_connection_string,
    get_invoice_lines,
    send_invoice_email,
    init_tracking_db,
    mark_invoice_sent
)

# Initialize tracking DB
init_tracking_db()

# Connect to database
conn = pyodbc.connect(get_connection_string())
cursor = conn.cursor()

# Query specific invoice
invoice_number = '100004668'
query = """
SELECT
    h.SOPNUMBE as InvoiceNumber,
    h.DOCDATE as InvoiceDate,
    h.DOCAMNT as Amount,
    h.SUBTOTAL as Subtotal,
    h.FRTAMNT as Freight,
    h.TAXAMNT as Tax,
    h.TRDISAMT as Discount,
    h.CUSTNMBR as CustomerID,
    c.CUSTNAME as CustomerName,
    h.CSTPONBR as PONumber,
    h.DEX_ROW_TS as CreatedAt,
    COALESCE(inet.EmailToAddress, inet.INET1) as CustomerEmail
FROM SOP30200 h
INNER JOIN RM00101 c ON h.CUSTNMBR = c.CUSTNMBR
LEFT JOIN SY01200 inet ON inet.Master_Type = 'CUS'
    AND inet.Master_ID = h.CUSTNMBR
    AND inet.ADRSCODE = c.ADRSCODE
WHERE h.SOPNUMBE = ? AND h.SOPTYPE = 3
"""

cursor.execute(query, (invoice_number,))
row = cursor.fetchone()

if not row:
    print(f"Invoice {invoice_number} not found!")
    exit(1)

# Get line items
lines = get_invoice_lines(conn, invoice_number)

# Build invoice object
invoice = {
    'number': row.InvoiceNumber.strip(),
    'date': row.InvoiceDate,
    'amount': float(row.Amount),
    'subtotal': float(row.Subtotal),
    'freight': float(row.Freight),
    'tax': float(row.Tax),
    'discount': float(row.Discount),
    'po_number': row.PONumber.strip(),
    'customer_id': row.CustomerID.strip(),
    'customer_name': row.CustomerName.strip(),
    'email': row.CustomerEmail.strip() if row.CustomerEmail else None,
    'created_at': row.CreatedAt,
    'lines': lines
}

print(f"Invoice: {invoice['number']}")
print(f"Customer: {invoice['customer_name']} ({invoice['customer_id']})")
print(f"Amount: ${invoice['amount']:,.2f}")
print(f"Line items: {len(lines)}")
print(f"Original email: {invoice['email']}")
print()

# Override email to test recipient
print("Overriding email to: alexh@chemicaldynamics.com")

# Temporarily modify customer_emails.json for this test
customer_emails = {}
try:
    with open('customer_emails.json', 'r', encoding='utf-8') as f:
        customer_emails = json.load(f)
except:
    pass

# Add/update this customer to send to test email
customer_emails[invoice['customer_id']] = {
    "to": "alexh@chemicaldynamics.com",
    "cc": ""
}

# Save back to file
with open('customer_emails.json', 'w', encoding='utf-8') as f:
    json.dump(customer_emails, f, indent=4)

print(f"Updated customer_emails.json for {invoice['customer_id']}")
print()

# Send the invoice
print("Sending invoice...")
if send_invoice_email(invoice):
    print("[OK] Email sent successfully!")
    mark_invoice_sent(invoice['number'])
    print("[OK] Marked as sent in tracking database")
else:
    print("[FAIL] Failed to send email")

conn.close()
