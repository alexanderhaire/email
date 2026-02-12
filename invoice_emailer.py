"""
Dynamics GP Invoice Email Automation
Monitors GP for new invoices and sends emails via Resend

IMPORTANT: Uses 'High Water Mark' strategy (DEX_ROW_TS) to ensure no invoices are missed
during downtime (e.g. weekends) while avoiding duplicates.
"""

import pyodbc
import resend
import time
import json
import os
from datetime import datetime, timedelta, timezone
from config import (
    SQL_SERVER, SQL_DATABASE, SQL_USERNAME, SQL_PASSWORD,
    USE_WINDOWS_AUTH, RESEND_API_KEY, FROM_EMAIL, FROM_NAME, CHECK_INTERVAL,
    DRY_RUN, REDIRECT_EMAILS, TEST_EMAIL_RECIPIENT, USE_DSN, DSN_NAME,
    EMAIL_DELAY_SECONDS, BATCH_SIZE, BATCH_PAUSE_SECONDS
)

# Configuration for Invoices
LAST_INVOICE_CHECK_FILE = "last_invoice_check.txt"



def get_connection_string():
    """Build SQL Server connection string"""
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
    """Fetch line items for a specific invoice"""
    cursor = conn.cursor()
    query = """
    SELECT 
        ITEMNMBR, ITEMDESC, QUANTITY, UNITPRCE, XTNDPRCE, UOFM
    FROM SOP30300
    WHERE SOPNUMBE = ? AND SOPTYPE = 3
    ORDER BY LNITMSEQ
    """
    try:
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
    except Exception as e:
        print(f"Error fetching lines for {invoice_number}: {e}")
        return []


def get_new_invoices_since(conn, last_timestamp):
    """
    Query GP for invoices created AFTER the given timestamp.
    Relies on DEX_ROW_TS (System Creation Time).
    """
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
        h.DEX_ROW_TS as CreatedAt,
        COALESCE(inet.EmailToAddress, inet.INET1) as CustomerEmail
    FROM SOP30200 h
    INNER JOIN RM00101 c ON h.CUSTNMBR = c.CUSTNMBR
    LEFT JOIN SY01200 inet ON inet.Master_Type = 'CUS' 
        AND inet.Master_ID = h.CUSTNMBR 
        AND inet.ADRSCODE = c.ADRSCODE
    WHERE h.SOPTYPE = 3  -- Invoice type
    AND h.VOIDSTTS = 0   -- Not voided
    AND h.DEX_ROW_TS > ? -- STRICTLY GREATER THAN last check
    ORDER BY h.DEX_ROW_TS ASC -- Process oldest to newest
    """
    
    try:
        cursor.execute(query, (last_timestamp,))
        invoices = []
        for row in cursor.fetchall():
            # Get Line Items
            invoice_num = row.InvoiceNumber.strip()
            lines = get_invoice_lines(conn, invoice_num)
            
            invoices.append({
                'number': invoice_num,
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
            })
        return invoices
    except Exception as e:
        print(f"Error querying invoices: {e}")
        return []


# External Email Mapping File
EXTERNAL_EMAILS_FILE = "customer_emails.json"

def load_external_emails():
    """Load external email mapping from JSON file"""
    if os.path.exists(EXTERNAL_EMAILS_FILE):
        try:
            with open(EXTERNAL_EMAILS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading external emails: {e}")
    return {}
    
GLOBAL_CONFIG_FILE = "global_config.json"

def load_global_config():
    """Load global config for CCs"""
    if os.path.exists(GLOBAL_CONFIG_FILE):
        try:
            with open(GLOBAL_CONFIG_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def send_invoice_email(invoice):
    """Send invoice notification email via Resend"""
    
    # 1. Check External Mapping First
    external_emails = load_external_emails()
    customer_id = invoice['customer_id']
    
    email_to = []
    email_cc = []

    # Default from GP
    if invoice['email']:
        email_to = [e.strip() for e in invoice['email'].replace(';', ',').split(',') if e.strip()]
    
    # Override/Append from External Mapping
    if customer_id in external_emails:
        config = external_emails[customer_id]
        
        # Handle both old string format and new dict format
        if isinstance(config, str):
            # Old format: Just a string of emails
            email_to = [e.strip() for e in config.replace(';', ',').split(',') if e.strip()]
        elif isinstance(config, dict):
            # New format: { "to": "...", "cc": "..." }
            if config.get("to"):
                email_to = [e.strip() for e in config["to"].replace(';', ',').split(',') if e.strip()]
            
            if config.get("cc"):
                email_cc = [e.strip() for e in config["cc"].replace(';', ',').split(',') if e.strip()]

    # Global CC (Dynamic UI config)
    global_config = load_global_config()
    ui_ccs_str = global_config.get("invoice_cc", "")
    if ui_ccs_str:
        ui_ccs = [e.strip() for e in ui_ccs_str.replace(';', ',').split(',') if e.strip()]
        for gc in ui_ccs:
             if gc not in email_cc and gc not in email_to:
                email_cc.append(gc)

    # 2. Check if we have an email
    if not email_to:
        print(f"    [WARN] No email for customer {invoice['customer_id']} - skipping")
        return False
    
    # Update object for display/logging
    invoice['email'] = ", ".join(email_to)
    if email_cc:
        invoice['email'] += f" (CC: {', '.join(email_cc)})"
    
    if DRY_RUN:
        print(f"    [DRY RUN] Would send email to {email_to} (CC: {email_cc}) for Invoice #{invoice['number']}")
        return True

    resend.api_key = RESEND_API_KEY
    
    # Handle Redirection for Testing
    final_to = email_to
    final_cc = email_cc
    subject_prefix = ""
    
    if REDIRECT_EMAILS:
        final_to = [TEST_EMAIL_RECIPIENT]
        final_cc = [] # clear CCs in test mode to avoid leaking
        subject_prefix = f"[TEST - Originally for {', '.join(email_to)}] "

    # Format Line Items HTML
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

    # Format date properly
    invoice_date = invoice['date'].strftime('%B %d, %Y') if invoice['date'] else 'N/A'
    po_display = invoice['po_number'] if invoice['po_number'] else '—'

    # Format the email
    html_content = f"""
   <!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="x-apple-disable-message-reformatting" />
    <title>Invoice</title>
  </head>

  <body style="margin:0; padding:0; background-color:#f4f6f8;">
    <!-- Preheader (hidden) -->
    <div style="display:none; font-size:1px; line-height:1px; max-height:0; max-width:0; opacity:0; overflow:hidden; mso-hide:all;">
      Invoice #{invoice['number']} from Chemical Dynamics.
    </div>

    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#f4f6f8; margin:0; padding:0;">
      <tr>
        <td align="center" style="padding:40px 12px;">
          <!-- Container -->
          <table role="presentation" width="680" cellpadding="0" cellspacing="0" border="0" style="width:680px; max-width:680px; background:#ffffff; border-radius:8px; overflow:hidden;">
            <!-- Header -->
            <tr>
              <td style="padding:40px 40px 20px 40px; border-bottom:1px solid #f0f0f0;">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                  <tr>
                    <td align="left" style="vertical-align:top;"></td>
                    <td align="right" style="vertical-align:top;">
                      <div style="background:#e0f2fe; color:#0284c7; padding:6px 12px; border-radius:4px; display:inline-block; font-weight:600; font-size:13px; font-family:Helvetica, Arial, sans-serif;">
                        INVOICE
                      </div>
                    </td>
                  </tr>

                  <tr>
                    <td colspan="2" align="center" style="padding-top:12px;">
                      <img
                        src="https://www.chemicaldynamics.com/wp-content/uploads/2022/10/CD-logo-350x20-NEW2-1.png"
                        width="220"
                        alt="Chemical Dynamics Inc."
                        style="display:block; border:0; outline:none; text-decoration:none; height:auto; width:220px; max-width:220px;"
                      />
                      <p style="margin:8px 0 0 0; color:#64748b; font-size:14px; font-family:Helvetica, Arial, sans-serif;">
                        P.O. Box 486
                      </p>
                      <p style="margin:5px 0 0 0; color:#64748b; font-size:14px; font-family:Helvetica, Arial, sans-serif;">
                        Plant City, FL 33564-0468
                      </p>
                      <p style="margin:5px 0 0 0; color:#64748b; font-size:14px; font-family:Helvetica, Arial, sans-serif;">
                        Phone:
                        <a href="tel:+18137524950" style="color:#2563eb; text-decoration:underline; font-weight:600;">
                          1-813-752-4950
                        </a>
                      </p>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>

            <!-- Bill/Ship + Summary Banner -->
            <tr>
              <td style="background:#f8fafc; padding:30px 40px; border-bottom:1px solid #f0f0f0;">
                <!-- PO row -->
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                  <tr>
                    <td align="right" style="padding:0 0 12px 0;">
                      <p style="margin:0; color:#64748b; font-size:14px; font-family:Helvetica, Arial, sans-serif;">
                        PO #:
                        <strong style="color:#334155;">{po_display}</strong>
                      </p>
                    </td>
                  </tr>
                </table>

                <!-- Bill To / Ship To -->
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:0 0 20px 0;">
                  <tr>
                    <td width="50%" valign="top" style="padding-right:20px;">
                      <p style="margin:0 0 8px 0; font-size:11px; text-transform:uppercase; color:#94a3b8; font-weight:600; letter-spacing:0.5px; font-family:Helvetica, Arial, sans-serif;">
                        Bill To
                      </p>

                      <p style="margin:0; color:#334155; font-size:14px; font-weight:700; font-family:Helvetica, Arial, sans-serif;">
                        {invoice['customer_name']}
                      </p>
                      <p style="margin:4px 0 0 0; color:#64748b; font-size:14px; font-family:Helvetica, Arial, sans-serif;">
                        Customer ID: {invoice['customer_id']}
                      </p>

                      <p style="margin:10px 0 0 0; color:#64748b; font-size:14px; line-height:20px; font-family:Helvetica, Arial, sans-serif;">
                        {invoice['billing_address_line1']}<br />
                        {invoice['billing_address_line2']}<br />
                        {invoice['billing_city']}, {invoice['billing_state']} {invoice['billing_zip']}
                      </p>
                    </td>

                    <td width="50%" valign="top" style="padding-left:20px;">
                      <p style="margin:0 0 8px 0; font-size:11px; text-transform:uppercase; color:#94a3b8; font-weight:600; letter-spacing:0.5px; font-family:Helvetica, Arial, sans-serif;">
                        Ship To
                      </p>

                      <p style="margin:0; color:#334155; font-size:14px; font-weight:700; font-family:Helvetica, Arial, sans-serif;">
                        {invoice['ship_to_name']}
                      </p>

                      <p style="margin:10px 0 0 0; color:#64748b; font-size:14px; line-height:20px; font-family:Helvetica, Arial, sans-serif;">
                        {invoice['ship_to_address_line1']}<br />
                        {invoice['ship_to_address_line2']}<br />
                        {invoice['ship_to_city']}, {invoice['ship_to_state']} {invoice['ship_to_zip']}
                      </p>
                    </td>
                  </tr>
                </table>

                <!-- Summary -->
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                  <tr>
                    <td width="33%" valign="top">
                      <p style="margin:0 0 5px 0; font-size:11px; text-transform:uppercase; color:#94a3b8; font-weight:600; letter-spacing:0.5px; font-family:Helvetica, Arial, sans-serif;">
                        Amount Due
                      </p>
                      <p style="margin:0; font-size:24px; font-weight:700; color:#0f172a; font-family:Helvetica, Arial, sans-serif;">
                        ${invoice['amount']:,.2f}
                      </p>
                    </td>

                    <td width="33%" valign="top">
                      <p style="margin:0 0 5px 0; font-size:11px; text-transform:uppercase; color:#94a3b8; font-weight:600; letter-spacing:0.5px; font-family:Helvetica, Arial, sans-serif;">
                        Invoice Number
                      </p>
                      <p style="margin:0; font-size:16px; color:#334155; font-family:Helvetica, Arial, sans-serif;">
                        #{invoice['number']}
                      </p>
                    </td>

                    <td width="33%" valign="top">
                      <p style="margin:0 0 5px 0; font-size:11px; text-transform:uppercase; color:#94a3b8; font-weight:600; letter-spacing:0.5px; font-family:Helvetica, Arial, sans-serif;">
                        Invoice Date
                      </p>
                      <p style="margin:0; font-size:16px; color:#334155; font-family:Helvetica, Arial, sans-serif;">
                        {invoice_date}
                      </p>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>

            <!-- Content -->
            <tr>
              <td style="padding:40px;">
                <!-- Line Items -->
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:0 0 30px 0; font-size:14px; font-family:Helvetica, Arial, sans-serif;">
                  <thead>
                    <tr>
                      <th align="left" style="padding:10px 15px; background:#f8fafc; color:#64748b; font-weight:600; font-size:12px; border-radius:4px 0 0 4px;">
                        ITEM
                      </th>
                      <th align="left" style="padding:10px 15px; background:#f8fafc; color:#64748b; font-weight:600; font-size:12px;">
                        DESCRIPTION
                      </th>
                      <th align="center" style="padding:10px 15px; background:#f8fafc; color:#64748b; font-weight:600; font-size:12px;">
                        QTY
                      </th>
                      <th align="right" style="padding:10px 15px; background:#f8fafc; color:#64748b; font-weight:600; font-size:12px;">
                        UNIT PRICE
                      </th>
                      <th align="right" style="padding:10px 15px; background:#f8fafc; color:#64748b; font-weight:600; font-size:12px; border-radius:0 4px 4px 0;">
                        AMOUNT
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    <!-- TERM row (static) -->
                    <tr>
                      <td style="padding:10px 15px; border-bottom:1px solid #e2e8f0; color:#64748b; font-size:12px; font-weight:600; text-transform:uppercase; letter-spacing:0.5px;">
                        TERM
                      </td>
                      <td colspan="4" style="padding:10px 15px; border-bottom:1px solid #e2e8f0; color:#334155; font-size:14px; font-weight:600;">
                        Net 30
                      </td>
                    </tr>

                    <!-- Line item rows -->
                    {lines_html}
                  </tbody>
                </table>

                <!-- Totals -->
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                  <tr>
                    <td width="55%"></td>
                    <td width="45%">
                      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">
                        <tr>
                          <td style="padding:5px 0; color:#64748b; font-size:14px; font-family:Helvetica, Arial, sans-serif;">Subtotal</td>
                          <td align="right" style="padding:5px 0; color:#334155; font-size:14px; font-weight:500; font-family:Helvetica, Arial, sans-serif;">
                            ${invoice['subtotal']:,.2f}
                          </td>
                        </tr>

                        <tr>
                          <td style="padding:5px 0; color:#64748b; font-size:14px; font-family:Helvetica, Arial, sans-serif;">Freight</td>
                          <td align="right" style="padding:5px 0; color:#334155; font-size:14px; font-weight:500; font-family:Helvetica, Arial, sans-serif;">
                            ${invoice['freight']:,.2f}
                          </td>
                        </tr>

                        <tr>
                          <td style="padding:5px 0; color:#64748b; font-size:14px; font-family:Helvetica, Arial, sans-serif;">Tonnage, Nitrate &amp; Sales Tax</td>
                          <td align="right" style="padding:5px 0; color:#334155; font-size:14px; font-weight:500; font-family:Helvetica, Arial, sans-serif;">
                            ${invoice['tax']:,.2f}
                          </td>
                        </tr>

                        <!-- Optional discount row: inject "" if none -->
                        {discount_row}

                        <tr>
                          <td style="padding:15px 0 0 0; border-top:2px solid #e2e8f0; color:#0f172a; font-weight:700; font-size:16px; font-family:Helvetica, Arial, sans-serif;">
                            Total
                          </td>
                          <td align="right" style="padding:15px 0 0 0; border-top:2px solid #e2e8f0; color:#0f172a; font-weight:700; font-size:18px; font-family:Helvetica, Arial, sans-serif;">
                            ${invoice['amount']:,.2f}
                          </td>
                        </tr>
                      </table>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>

            <!-- Footer -->
            <tr>
              <td style="background:#f8fafc; padding:30px 40px; border-top:1px solid #f0f0f0;">
                <h4 style="margin:0 0 10px 0; color:#475569; font-size:12px; font-weight:700; text-transform:uppercase; font-family:Helvetica, Arial, sans-serif;">
                  Terms &amp; Conditions
                </h4>

                <p style="margin:0; color:#64748b; font-size:11px; line-height:1.6; font-family:Helvetica, Arial, sans-serif;">
                  TERMS: NET 30 DAYS. A finance charge of 1&#189;% per month (18% per annum) will be charged on all past due accounts.
                  In the event it becomes necessary to enforce collection of this invoice, the purchaser agrees to pay all costs
                  of collection, including reasonable attorney's fees. "WE APPRECIATE YOUR BUSINESS"
                </p>

                <p style="margin:20px 0 0 0; text-align:center; color:#94a3b8; font-size:12px; font-family:Helvetica, Arial, sans-serif;">
                  Chemical Dynamics, Inc. &bull; 4206 Business Lane &bull; Plant City, FL 33566
                </p>
              </td>
            </tr>
          </table>
          <!-- /Container -->
        </td>
      </tr>
    </table>
  </body>
</html>

    """
    
    # FINAL SAFETY CHECK
    if REDIRECT_EMAILS and final_to != [TEST_EMAIL_RECIPIENT]:
        print(f"    [CRITICAL SAFETY] Attempted to send to {final_to} but REDIRECT_EMAILS is True. BLOCKED.")
        return False
        
    # Retry Loop for Network Reliability
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            email_params = {
                "from": f"{FROM_NAME} <{FROM_EMAIL}>",
                "to": final_to,
                "subject": f"{subject_prefix}Invoice #{invoice['number']} from {FROM_NAME}",
                "html": html_content
            }
            
            if final_cc:
                email_params["cc"] = final_cc

            resend.Emails.send(email_params)
            return True
            
        except Exception as e:
            print(f"    ⚠ Attempt {attempt}/{max_retries} failed: {e}")
            if attempt < max_retries:
                wait_time = 2 * attempt # Exponential backoff: 2s, 4s
                print(f"      Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"    ✗ Failed after {max_retries} attempts.")
                return False


def main():
    """Main loop"""
    
    print("=" * 60)
    print("  DYNAMICS GP INVOICE EMAIL AUTOMATION (Persistent Mode)")
    print("=" * 60)
    print(f"  Server: {SQL_SERVER}")
    print(f"  Database: {SQL_DATABASE}")
    
    # Test database connection
    print("\n-> Connecting to database...")
    try:
        conn = pyodbc.connect(get_connection_string())
        print("  [OK] Connected successfully!")
    except Exception as e:
        print(f"  [X] Connection failed: {e}")
        return
    
    # Load last progress
    # Default to START OF TODAY if no history (or just now if preferred, but today captures anything from today)
    # Using START OF TODAY to be safe on fresh start
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    last_processed_ts = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    if os.path.exists(LAST_INVOICE_CHECK_FILE):
        try:
            with open(LAST_INVOICE_CHECK_FILE, 'r') as f:
                ts_str = f.read().strip()
                last_processed_ts = datetime.fromisoformat(ts_str)
                print(f"  [OK] Resuming from last check: {ts_str}")
                
                # Safety check for future dates
                if last_processed_ts > (now + timedelta(days=1)):
                     print(f"  [WARN] Found future date in history. Resetting to NOW.")
                     last_processed_ts = now
        except Exception as e:
             print(f"  [WARN] Could not load last check time: {e}")
             # Default to now if file error, to avoid re-sending old stuff? 
             # Or start of day? Let's do START OF DAY to be safe.
    else:
        print(f"  [OK] No history found. Monitoring started from: {last_processed_ts} (Start of Day)")
    
    print("\n" + "=" * 60)
    print("  MONITORING ACTIVE... (Ctrl+C to stop)")
    print("=" * 60 + "\n")
    
    while True:
        try:
            # Check for new invoices
            new_invoices = get_new_invoices_since(conn, last_processed_ts)
            
            if new_invoices:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Found {len(new_invoices)} new invoice(s)")
                
                emails_sent_in_batch = 0
                max_ts_in_batch = last_processed_ts
                
                for i, invoice in enumerate(new_invoices):
                    print(f"  → Invoice #{invoice['number']} - ${invoice['amount']:,.2f} to {invoice['customer_name']}")
                    
                    if send_invoice_email(invoice):
                         print(f"    ✓ Email sent to {invoice['email']}")
                         emails_sent_in_batch += 1
                         
                         # Throttling: Add delay between emails (except after the last one)
                         if i < len(new_invoices) - 1:
                             # Check if we need a longer batch pause
                             if emails_sent_in_batch >= BATCH_SIZE:
                                 print(f"    ⏸ Batch pause: waiting {BATCH_PAUSE_SECONDS}s after {BATCH_SIZE} emails...")
                                 time.sleep(BATCH_PAUSE_SECONDS)
                                 emails_sent_in_batch = 0
                             else:
                                 # print(f"    ⏳ Throttling: waiting {EMAIL_DELAY_SECONDS}s...")
                                 time.sleep(EMAIL_DELAY_SECONDS)
                    else:
                        print("    ✗ Skipped (No Email or Error)")
                    
                    # Update high water mark
                    if invoice['created_at'] > max_ts_in_batch:
                        max_ts_in_batch = invoice['created_at']
                
                # Update global high water mark
                last_processed_ts = max_ts_in_batch
                
                # Save timestamp
                try:
                    with open(LAST_INVOICE_CHECK_FILE, 'w') as f:
                        f.write(last_processed_ts.isoformat())
                except Exception as e:
                    print(f"    [WARN] Failed to save checkpoint: {e}")

            else:
                 # Even if no invoices found, update processed time if we want to move the window?
                 # Actually, get_new_invoices_since filters by > timestamp.
                 # If we don't find any, we don't change execution time.
                 pass
            
        except KeyboardInterrupt:
            print("\n\n-> Stopping...")
            break
        except Exception as e:
            print(f"Error in main loop: {e}")
            # Try to reconnect if connection lost
            try:
                conn.close()
            except:
                pass
            try:
                print("  Attempting to reconnect...")
                conn = pyodbc.connect(get_connection_string())
                print("  Reconnected.")
            except:
                print("  Reconnect failed. Retrying in 60s...")
            time.sleep(CHECK_INTERVAL)
    
    conn.close()
    print("→ Goodbye!")


if __name__ == "__main__":
    main()
