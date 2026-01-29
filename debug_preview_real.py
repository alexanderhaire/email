"""
Generate an email preview using REAL data from the database for a specific invoice.
"""
import pyodbc
from datetime import datetime
from config import (
    SQL_SERVER, SQL_DATABASE, SQL_USERNAME, SQL_PASSWORD,
    USE_WINDOWS_AUTH, USE_DSN, DSN_NAME, FROM_NAME
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

def get_invoice_lines(conn, invoice_number):
    cursor = conn.cursor()
    query = """
    SELECT ITEMNMBR, ITEMDESC, QUANTITY, UNITPRCE, XTNDPRCE, UOFM
    FROM SOP30300
    WHERE SOPNUMBE = ? AND SOPTYPE = 3
    ORDER BY LNITMSEQ
    """
    cursor.execute(query, (invoice_number,))
    lines = []
    for row in cursor.fetchall():
        lines.append({
            'item_number': row.ITEMNMBR.strip(),
            'description': row.ITEMDESC.strip(),
            'quantity': float(row.QUANTITY),
            'unit_price': float(row.UNITPRCE),
            'extended_price': float(row.XTNDPRCE),
            'uom': row.UOFM.strip()
        })
    return lines

def get_real_invoice(invoice_number):
    conn = pyodbc.connect(get_connection_string())
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
        h.CSTPONBR as PONumber
    FROM SOP30200 h
    INNER JOIN RM00101 c ON h.CUSTNMBR = c.CUSTNMBR
    WHERE h.SOPNUMBE = ?
    """
    cursor.execute(query, (invoice_number,))
    row = cursor.fetchone()
    
    if not row:
        print(f"Invoice {invoice_number} not found!")
        conn.close()
        return None
    
    lines = get_invoice_lines(conn, invoice_number)
    
    invoice = {
        'number': row.InvoiceNumber.strip(),
        'date': row.InvoiceDate,
        'amount': float(row.Amount),
        'subtotal': float(row.Subtotal),
        'freight': float(row.Freight),
        'tax': float(row.Tax),
        'discount': float(row.Discount),
        'po_number': row.PONumber.strip() if row.PONumber else '',
        'customer_id': row.CustomerID.strip(),
        'customer_name': row.CustomerName.strip(),
        'lines': lines
    }
    
    conn.close()
    return invoice

def generate_html(invoice):
    """Generate the email HTML (copied from invoice_emailer.py)"""
    
    lines_html = ""
    for line in invoice['lines']:
        lines_html += f"""
        <tr>
            <td style="padding: 12px 15px; border-bottom: 1px solid #eee; color: #333;">{line['item_number']}</td>
            <td style="padding: 12px 15px; border-bottom: 1px solid #eee; color: #333;">{line['description']}</td>
            <td style="padding: 12px 15px; border-bottom: 1px solid #eee; text-align: center; color: #555;">{line['quantity']:,.2f}</td>
            <td style="padding: 12px 15px; border-bottom: 1px solid #eee; text-align: right; color: #555;">${line['unit_price']:,.2f}</td>
            <td style="padding: 12px 15px; border-bottom: 1px solid #eee; text-align: right; color: #333; font-weight: 500;">${line['extended_price']:,.2f}</td>
        </tr>
        """

    invoice_date = invoice['date'].strftime('%B %d, %Y') if invoice['date'] else 'N/A'
    po_display = invoice['po_number'] if invoice['po_number'] else '—'

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <body style="margin: 0; padding: 0; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f4f6f8;">
        
        <div style="max-width: 680px; margin: 40px auto; background: #ffffff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); overflow: hidden;">
            
            <!-- Company Header -->
            <div style="background: #ffffff; padding: 40px 40px 20px 40px; border-bottom: 1px solid #f0f0f0;">
                <table width="100%">
                    <tr>
                        <td>
                            <h1 style="margin: 0; color: #0f172a; font-size: 24px; letter-spacing: -0.5px;">Chemical Dynamics, Inc.</h1>
                            <p style="margin: 5px 0 0 0; color: #64748b; font-size: 14px;">4206 Business Lane <br> Plant City, FL 33566</p>
                        </td>
                        <td style="text-align: right; vertical-align: top;">
                            <div style="background: #e0f2fe; color: #0284c7; padding: 6px 12px; border-radius: 4px; display: inline-block; font-weight: 600; font-size: 13px;">INVOICE</div>
                        </td>
                    </tr>
                </table>
            </div>
            
            <!-- Invoice Details Banner -->
            <div style="background: #f8fafc; padding: 30px 40px; border-bottom: 1px solid #f0f0f0;">
                <table width="100%">
                    <tr>
                        <td width="33%">
                            <p style="margin: 0 0 5px 0; font-size: 11px; text-transform: uppercase; color: #94a3b8; font-weight: 600; letter-spacing: 0.5px;">Amount Due</p>
                            <p style="margin: 0; font-size: 24px; font-weight: 700; color: #0f172a;">${invoice['amount']:,.2f}</p>
                        </td>
                        <td width="33%">
                            <p style="margin: 0 0 5px 0; font-size: 11px; text-transform: uppercase; color: #94a3b8; font-weight: 600; letter-spacing: 0.5px;">Invoice Number</p>
                            <p style="margin: 0; font-size: 16px; color: #334155;">#{invoice['number']}</p>
                        </td>
                         <td width="33%">
                            <p style="margin: 0 0 5px 0; font-size: 11px; text-transform: uppercase; color: #94a3b8; font-weight: 600; letter-spacing: 0.5px;">Date</p>
                            <p style="margin: 0; font-size: 16px; color: #334155;">{invoice_date}</p>
                        </td>
                    </tr>
                </table>
            </div>

            <!-- Content Area -->
            <div style="padding: 40px;">
                
                <!-- Bill To -->
                <table width="100%" style="margin-bottom: 30px;">
                    <tr>
                        <td>
                             <p style="margin: 0 0 8px 0; font-size: 11px; text-transform: uppercase; color: #94a3b8; font-weight: 600; letter-spacing: 0.5px;">Bill To</p>
                             <h3 style="margin: 0; color: #334155; font-size: 18px;">{invoice['customer_name']}</h3>
                             <p style="margin: 4px 0 0 0; color: #64748b; font-size: 14px;">Customer ID: {invoice['customer_id']}</p>
                        </td>
                         <td style="text-align: right; vertical-align: bottom;">
                            <p style="margin: 0; color: #64748b; font-size: 14px;">PO #: <strong style="color: #334155;">{po_display}</strong></p>
                        </td>
                    </tr>
                </table>

                <!-- Line Items -->
                <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 30px; font-size: 14px;">
                    <thead>
                        <tr>
                            <th style="padding: 10px 15px; text-align: left; background: #f8fafc; color: #64748b; font-weight: 600; font-size: 12px; border-radius: 4px 0 0 4px;">ITEM</th>
                            <th style="padding: 10px 15px; text-align: left; background: #f8fafc; color: #64748b; font-weight: 600; font-size: 12px;">DESCRIPTION</th>
                            <th style="padding: 10px 15px; text-align: center; background: #f8fafc; color: #64748b; font-weight: 600; font-size: 12px;">QTY</th>
                            <th style="padding: 10px 15px; text-align: right; background: #f8fafc; color: #64748b; font-weight: 600; font-size: 12px;">RATE</th>
                            <th style="padding: 10px 15px; text-align: right; background: #f8fafc; color: #64748b; font-weight: 600; font-size: 12px; border-radius: 0 4px 4px 0;">AMOUNT</th>
                        </tr>
                    </thead>
                    <tbody>
                        {lines_html}
                    </tbody>
                </table>

                <!-- Totals -->
                <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                        <td width="55%"></td>
                        <td width="45%">
                            <table width="100%">
                                <tr>
                                    <td style="padding: 5px 0; color: #64748b; font-size: 14px;">Subtotal</td>
                                    <td style="padding: 5px 0; text-align: right; color: #334155; font-size: 14px; font-weight: 500;">${invoice['subtotal']:,.2f}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 5px 0; color: #64748b; font-size: 14px;">Freight</td>
                                    <td style="padding: 5px 0; text-align: right; color: #334155; font-size: 14px; font-weight: 500;">${invoice['freight']:,.2f}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 5px 0; color: #64748b; font-size: 14px;">Tonnage, Nitrate & Sales Tax</td>
                                    <td style="padding: 5px 0; text-align: right; color: #334155; font-size: 14px; font-weight: 500;">${invoice['tax']:,.2f}</td>
                                </tr>
                                {f'<tr><td style="padding: 5px 0; color: #ef4444; font-size: 14px;">Discount</td><td style="padding: 5px 0; text-align: right; color: #ef4444; font-size: 14px; font-weight: 500;">-${invoice["discount"]:,.2f}</td></tr>' if invoice['discount'] > 0 else ''}
                                <tr>
                                    <td style="padding: 15px 0 0 0; border-top: 2px solid #e2e8f0; color: #0f172a; font-weight: 700; font-size: 16px;">Total</td>
                                    <td style="padding: 15px 0 0 0; border-top: 2px solid #e2e8f0; text-align: right; color: #0f172a; font-weight: 700; font-size: 18px;">${invoice['amount']:,.2f}</td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </div>

            <!-- Footer & Terms -->
            <div style="background: #f8fafc; padding: 30px 40px; border-top: 1px solid #f0f0f0;">
                <h4 style="margin: 0 0 10px 0; color: #475569; font-size: 12px; font-weight: 700; text-transform: uppercase;">Terms & Conditions</h4>
                <p style="margin: 0; color: #64748b; font-size: 11px; line-height: 1.6; text-align: justify;">
                    TERMS: NET 30 DAYS. A finance charge of 1½% per month (18% per annum) will be charged on all past due accounts. 
                    In the event it becomes necessary to enforce collection of this invoice, the purchaser agrees to pay all costs 
                    of collection, including reasonable attorney's fees. "WE APPRECIATE YOUR BUSINESS"
                </p>
                
                <div style="margin-top: 20px; text-align: center; color: #94a3b8; font-size: 12px;">
                    <p style="margin: 0;">Chemical Dynamics, Inc. &bull; 4206 Business Lane &bull; Plant City, FL 33566</p>
                </div>
            </div>
            
        </div>
        
    </body>
    </html>
    """
    return html_content

if __name__ == "__main__":
    invoice_number = "100004467"
    print(f"Fetching real data for Invoice #{invoice_number}...")
    
    invoice = get_real_invoice(invoice_number)
    
    if invoice:
        print(f"  Customer: {invoice['customer_name']}")
        print(f"  Amount: ${invoice['amount']:,.2f}")
        print(f"  Line items: {len(invoice['lines'])}")
        
        for i, line in enumerate(invoice['lines'], 1):
            print(f"    {i}. {line['item_number']} - {line['description']} (Qty: {line['quantity']}, Price: ${line['unit_price']:,.2f})")
        
        html = generate_html(invoice)
        with open('email_preview_real.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("\n✓ Preview saved to email_preview_real.html")
