
import pyodbc
import time
from invoice_emailer import get_connection_string, send_invoice_email, get_invoice_lines
from config import EMAIL_DELAY_SECONDS

def force_send(invoice_numbers):
    print(f"Force sending {len(invoice_numbers)} invoices...")
    print(f"  (Throttling: {EMAIL_DELAY_SECONDS}s between emails)")
    conn = pyodbc.connect(get_connection_string())
    
    for i, inv_num in enumerate(invoice_numbers):
        print(f"\nProcessing {inv_num}...")
        
        # We need to manually construct the invoice object since get_new_invoices filters by date
        cursor = conn.cursor()
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
            COALESCE(inet.EmailToAddress, inet.INET1) as CustomerEmail
        FROM SOP30200 h
        INNER JOIN RM00101 c ON h.CUSTNMBR = c.CUSTNMBR
        LEFT JOIN SY01200 inet ON inet.Master_Type = 'CUS' 
            AND inet.Master_ID = h.CUSTNMBR 
            AND inet.ADRSCODE = c.ADRSCODE
        WHERE h.SOPTYPE = 3 AND h.SOPNUMBE = ?
        """
        
        cursor.execute(query, (inv_num,))
        row = cursor.fetchone()
        
        if row:
            lines = get_invoice_lines(conn, inv_num)
            
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
                'lines': lines
            }
            
            print(f"  Found Invoice #{invoice['number']} for {invoice['customer_name']}")
            if send_invoice_email(invoice):
                print("  ✓ Email Sent Successfully!")
                
                # Throttle: Add delay before next email (except after the last one)
                if i < len(invoice_numbers) - 1:
                    print(f"  ⏳ Throttling: waiting {EMAIL_DELAY_SECONDS}s before next email...")
                    time.sleep(EMAIL_DELAY_SECONDS)
            else:
                print("  ✗ Failed to send.")
        else:
            print(f"  ✗ Invoice {inv_num} not found in SOP30200.")
            
    conn.close()

if __name__ == "__main__":
    # List of invoices to force send
    invoices_to_send = ["100004472", "100004473"]
    force_send(invoices_to_send)
