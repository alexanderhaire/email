
"""
Dynamics GP Purchase Order Email Automation
Monitors GP for new POs and sends emails via Resend

IMPORTANT: Uses 'High Water Mark' strategy (CREATDDT) to detect newly ENTERED POs.
This ensures we only email POs when they are first created, not when they are edited.
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
    EMAIL_DELAY_SECONDS, BATCH_SIZE, BATCH_PAUSE_SECONDS, PO_GLOBAL_CC
)

# Configuration for POs
PROCESSED_POS_FILE = "processed_pos.json"
LAST_CHECK_FILE = "last_po_check.txt"

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

def load_processed_pos():
    """Load list of processed PO numbers"""
    if os.path.exists(PROCESSED_POS_FILE):
        try:
            with open(PROCESSED_POS_FILE, 'r') as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def save_processed_pos(processed_set):
    """Save list of processed PO numbers"""
    try:
        with open(PROCESSED_POS_FILE, 'w') as f:
            json.dump(list(processed_set), f)
    except Exception as e:
        print(f"Error saving processed POs: {e}")

def get_po_lines(conn, po_number):
    """Fetch line items for a specific PO"""
    cursor = conn.cursor()
    query = """
    SELECT 
        ITEMNMBR, ITEMDESC, QTYORDER, UNITCOST, EXTDCOST, UOFM
    FROM POP10110
    WHERE PONUMBER = ?
    ORDER BY ORD
    """
    try:
        cursor.execute(query, (po_number,))
        lines = []
        for row in cursor.fetchall():
            lines.append({
                'item_number': row.ITEMNMBR.strip(),
                'description': row.ITEMDESC.strip(),
                'quantity': float(row.QTYORDER),
                'unit_price': float(row.UNITCOST),
                'extended_price': float(row.EXTDCOST),
                'uom': row.UOFM.strip()
            })
        return lines
    except Exception as e:
        print(f"Error fetching lines for PO {po_number}: {e}")
        return []

def get_new_pos_since(conn, last_timestamp):
    """
    Query GP for POs MODIFIED AFTER the given timestamp.
    Uses DEX_ROW_TS (Row Timestamp) to detect newly saved POs.
    """
    cursor = conn.cursor()
    
    query = """
    SELECT 
        h.PONUMBER as PONumber,
        h.DOCDATE as PODate,
        (h.SUBTOTAL + h.FRTAMNT + h.TAXAMNT + h.MSCCHAMT - h.TRDISAMT) as Amount,
        h.SUBTOTAL as Subtotal,
        h.FRTAMNT as Freight,
        h.TAXAMNT as Tax,
        h.MSCCHAMT as Misc,
        h.TRDISAMT as Discount,
        h.VENDORID as VendorID,
        h.VENDNAME as VendorName,
        h.DEX_ROW_TS as ModifiedAt,
        COALESCE(inet.EmailToAddress, inet.INET1) as VendorEmail
    FROM POP10100 h
    INNER JOIN PM00200 v ON h.VENDORID = v.VENDORID
    LEFT JOIN SY01200 inet ON inet.Master_Type = 'VEN' 
        AND inet.Master_ID = h.VENDORID 
        AND inet.ADRSCODE = v.VADDCDPR
    WHERE h.POSTATUS = 1 
    AND h.DEX_ROW_TS > ?
    ORDER BY h.DEX_ROW_TS ASC
    """
    
    try:
        cursor.execute(query, (last_timestamp,))
        pos = []
        for row in cursor.fetchall():
            po_num = row.PONumber.strip()
            lines = get_po_lines(conn, po_num)
            
            pos.append({
                'number': po_num,
                'date': row.PODate,
                'amount': float(row.Amount),
                'subtotal': float(row.Subtotal),
                'freight': float(row.Freight),
                'tax': float(row.Tax),
                'misc': float(row.Misc),
                'discount': float(row.Discount),
                'vendor_id': row.VendorID.strip(),
                'vendor_name': row.VendorName.strip(),
                'email': row.VendorEmail.strip() if row.VendorEmail else None,
                'timestamp': row.ModifiedAt,
                'lines': lines
            })
        return pos
    except Exception as e:
        print(f"Error querying POs: {e}")
        return []

def get_po_details(conn, po_number):
    """Fetch full details for a specific PO (Test Helper)"""
    cursor = conn.cursor()
    
    query = """
    SELECT 
        h.PONUMBER as PONumber,
        h.DOCDATE as PODate,
        (h.SUBTOTAL + h.FRTAMNT + h.TAXAMNT + h.MSCCHAMT - h.TRDISAMT) as Amount,
        h.SUBTOTAL as Subtotal,
        h.FRTAMNT as Freight,
        h.TAXAMNT as Tax,
        h.MSCCHAMT as Misc,
        h.TRDISAMT as Discount,
        h.VENDORID as VendorID,
        h.VENDNAME as VendorName,
        h.CREATDDT as CreatedAt,
        COALESCE(inet.EmailToAddress, inet.INET1) as VendorEmail
    FROM POP10100 h
    INNER JOIN PM00200 v ON h.VENDORID = v.VENDORID
    LEFT JOIN SY01200 inet ON inet.Master_Type = 'VEN' 
        AND inet.Master_ID = h.VENDORID 
        AND inet.ADRSCODE = v.VADDCDPR
    WHERE h.PONUMBER = ?
    """
    
    try:
        cursor.execute(query, (po_number,))
        row = cursor.fetchone()
        if row:
            lines = get_po_lines(conn, row.PONumber.strip())
            return {
                'number': row.PONumber.strip(),
                'date': row.PODate,
                'amount': float(row.Amount),
                'subtotal': float(row.Subtotal),
                'freight': float(row.Freight),
                'tax': float(row.Tax),
                'misc': float(row.Misc),
                'discount': float(row.Discount),
                'vendor_id': row.VendorID.strip(),
                'vendor_name': row.VendorName.strip(),
                'email': row.VendorEmail.strip() if row.VendorEmail else None,
                'created_at': row.CreatedAt,
                'lines': lines
            }
        return None
    except Exception as e:
        print(f"Error fetching PO details: {e}")
        return None

# External Email Mapping File
VENDOR_EMAILS_FILE = "vendor_emails.json"

def load_vendor_emails():
    """Load external email mapping from JSON file"""
    if os.path.exists(VENDOR_EMAILS_FILE):
        try:
            with open(VENDOR_EMAILS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading vendor emails: {e}")
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

def send_po_email(po):
    """Send PO notification email via Resend"""
    
    # 1. Check External Mapping First
    vendor_emails = load_vendor_emails()
    vendor_id = po['vendor_id']
    
    email_to = []
    email_cc = []

    # Default from GP
    if po['email']:
        email_to = [e.strip() for e in po['email'].replace(';', ',').split(',') if e.strip()]
    
    # Override/Append from External Mapping
    if vendor_id in vendor_emails:
        config = vendor_emails[vendor_id]
        
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

    # 1.5 Add Global CC (from config.py AND global_config.json)
    
    # Static config (legacy/hardcoded)
    if PO_GLOBAL_CC:
        global_ccs = [e.strip() for e in PO_GLOBAL_CC.replace(';', ',').split(',') if e.strip()]
        for gc in global_ccs:
            if gc not in email_cc and gc not in email_to:
                email_cc.append(gc)

    # Dynamic UI config
    global_config = load_global_config()
    ui_ccs_str = global_config.get("po_cc", "")
    if ui_ccs_str:
        ui_ccs = [e.strip() for e in ui_ccs_str.replace(';', ',').split(',') if e.strip()]
        for gc in ui_ccs:
             if gc not in email_cc and gc not in email_to:
                email_cc.append(gc)

    # 2. Check if we have an email
    # If explicitly set to empty string in config or just missing
    if not email_to:
        print(f"    ⚠ No email for vendor {po['vendor_name']} ({po['vendor_id']}) - skipping")
        return False
    
    # Update object for display/logging
    po['email'] = ", ".join(email_to)
    if email_cc:
        po['email'] += f" (CC: {', '.join(email_cc)})"
    
    if DRY_RUN:
        print(f"    [DRY RUN] Would send email to {email_to} (CC: {email_cc}) for PO #{po['number']}")
        return True

    resend.api_key = RESEND_API_KEY
    
    # Handle Redirection for Testing
    final_to = email_to
    final_cc = email_cc
    subject_prefix = ""
    
    if REDIRECT_EMAILS:
        final_to = [TEST_EMAIL_RECIPIENT]
        final_cc = []
        subject_prefix = f"[TEST - Originally for {','.join(email_to)}] "

    # Format Line Items HTML
    lines_html = ""
    for line in po['lines']:
        lines_html += f"""
        <tr>
            <td style="padding: 12px 15px; border-bottom: 1px solid #eee; color: #333;">{line['item_number']}</td>
            <td style="padding: 12px 15px; border-bottom: 1px solid #eee; color: #333;">{line['description']}</td>
            <td style="padding: 12px 15px; border-bottom: 1px solid #eee; text-align: center; color: #555;">{line['quantity']:,.2f}</td>
            <td style="padding: 12px 15px; border-bottom: 1px solid #eee; text-align: right; color: #555;">${line['unit_price']:,.2f}</td>
            <td style="padding: 12px 15px; border-bottom: 1px solid #eee; text-align: right; color: #333; font-weight: 500;">${line['extended_price']:,.2f}</td>
        </tr>
        """

    po_date_str = po['date'].strftime('%B %d, %Y') if po['date'] else 'N/A'

    # Format the email
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
                            <div style="background: #e0f2fe; color: #0284c7; padding: 6px 12px; border-radius: 4px; display: inline-block; font-weight: 600; font-size: 13px;">PURCHASE ORDER</div>
                        </td>
                    </tr>
                </table>
            </div>
            
            <!-- Details Banner -->
            <div style="background: #f8fafc; padding: 30px 40px; border-bottom: 1px solid #f0f0f0;">
                <table width="100%">
                    <tr>
                        <td width="33%">
                            <p style="margin: 0 0 5px 0; font-size: 11px; text-transform: uppercase; color: #94a3b8; font-weight: 600; letter-spacing: 0.5px;">PO Total</p>
                            <p style="margin: 0; font-size: 24px; font-weight: 700; color: #0f172a;">${po['amount']:,.2f}</p>
                        </td>
                        <td width="33%">
                            <p style="margin: 0 0 5px 0; font-size: 11px; text-transform: uppercase; color: #94a3b8; font-weight: 600; letter-spacing: 0.5px;">PO Number</p>
                            <p style="margin: 0; font-size: 16px; color: #334155;">#{po['number']}</p>
                        </td>
                        <td width="33%">
                            <p style="margin: 0 0 5px 0; font-size: 11px; text-transform: uppercase; color: #94a3b8; font-weight: 600; letter-spacing: 0.5px;">Date</p>
                            <p style="margin: 0; font-size: 16px; color: #334155;">{po_date_str}</p>
                        </td>
                    </tr>
                </table>
            </div>

            <!-- Content Area -->
            <div style="padding: 40px;">
                
                <!-- Vendor Info -->
                <table width="100%" style="margin-bottom: 30px;">
                    <tr>
                        <td>
                             <p style="margin: 0 0 8px 0; font-size: 11px; text-transform: uppercase; color: #94a3b8; font-weight: 600; letter-spacing: 0.5px;">Vendor</p>
                             <h3 style="margin: 0; color: #334155; font-size: 18px;">{po['vendor_name']}</h3>
                             <p style="margin: 4px 0 0 0; color: #64748b; font-size: 14px;">Vendor ID: {po['vendor_id']}</p>
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
                            <th style="padding: 10px 15px; text-align: right; background: #f8fafc; color: #64748b; font-weight: 600; font-size: 12px;">UNIT COST</th>
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
                        <td width="55%">
                            <!-- Blank space -->
                        </td>
                        <td width="45%">
                            <table width="100%">
                                <tr>
                                    <td style="padding: 5px 0; color: #64748b; font-size: 14px;">Subtotal</td>
                                    <td style="padding: 5px 0; text-align: right; color: #334155; font-size: 14px; font-weight: 500;">${po['subtotal']:,.2f}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 5px 0; color: #64748b; font-size: 14px;">Freight</td>
                                    <td style="padding: 5px 0; text-align: right; color: #334155; font-size: 14px; font-weight: 500;">${po['freight']:,.2f}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 5px 0; color: #64748b; font-size: 14px;">Tax</td>
                                    <td style="padding: 5px 0; text-align: right; color: #334155; font-size: 14px; font-weight: 500;">${po['tax']:,.2f}</td>
                                </tr>
                                {f'<tr><td style="padding: 5px 0; color: #ef4444; font-size: 14px;">Discount</td><td style="padding: 5px 0; text-align: right; color: #ef4444; font-size: 14px; font-weight: 500;">-${po["discount"]:,.2f}</td></tr>' if po['discount'] > 0 else ''}
                                <tr>
                                    <td style="padding: 15px 0 0 0; border-top: 2px solid #e2e8f0; color: #0f172a; font-weight: 700; font-size: 16px;">Total</td>
                                    <td style="padding: 15px 0 0 0; border-top: 2px solid #e2e8f0; text-align: right; color: #0f172a; font-weight: 700; font-size: 18px;">${po['amount']:,.2f}</td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </div>

            <!-- Footer -->
            <div style="background: #f8fafc; padding: 30px 40px; border-top: 1px solid #f0f0f0;">
                <div style="margin-top: 20px; text-align: center; color: #94a3b8; font-size: 12px;">
                    <p style="margin: 0;">Chemical Dynamics, Inc. &bull; 4206 Business Lane &bull; Plant City, FL 33566</p>
                </div>
            </div>
            
        </div>
        
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
                "subject": f"{subject_prefix}Purchase Order #{po['number']} from {FROM_NAME}",
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
    print("  DYNAMICS GP PO EMAIL AUTOMATION")
    print("=" * 60)
    print(f"  Server: {SQL_SERVER}")
    print(f"  Database: {SQL_DATABASE}")
    
    # Processed POs
    processed_pos = load_processed_pos()
    print(f"  Loaded {len(processed_pos)} processed POs")

    # Connect
    print("\n→ Connecting to database...")
    try:
        conn = pyodbc.connect(get_connection_string())
        print("  ✓ Connected successfully!")
    except Exception as e:
        print(f"  ✗ Connection failed: {e}")
        return
    
    # Load last progress
    # Default to START OF TODAY if no history
    # This ensures we catch POs created earlier today if we just started the script
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    last_processed_ts = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    if os.path.exists(LAST_CHECK_FILE):
        try:
            with open(LAST_CHECK_FILE, 'r') as f:
                ts_str = f.read().strip()
                last_processed_ts = datetime.fromisoformat(ts_str)
                
                if last_processed_ts > (now + timedelta(days=1)):
                    print(f"  ⚠ Found future date {ts_str} in history file. Resetting to START OF TODAY.")
                    last_processed_ts = now.replace(hour=0, minute=0, second=0, microsecond=0)
                    # Save the corrected timestamp immediately so we don't warn again next time
                    try:
                         with open(LAST_CHECK_FILE, 'w') as f:
                            f.write(last_processed_ts.isoformat())
                         print("    ✓ Corrupted history file repaired.")
                    except Exception as e:
                        print(f"    ⚠ Failed to repair history file: {e}")
                else:
                    print(f"  ✓ Resuming from last check: {ts_str}")
        except:
             print("  ⚠ Could not load last check time, starting from START OF TODAY.")
    else:
        print(f"  ✓ No history found. Monitoring started from: {last_processed_ts} (Start of Day)")

    print("\n" + "=" * 60)
    print("  PO MONITORING ACTIVE... (Ctrl+C to stop)")
    print("=" * 60 + "\n")
    
    while True:
        try:
            # Check for new POs
            new_pos = get_new_pos_since(conn, last_processed_ts)
            
            # Filter out already processed POs (handle edits)
            valid_pos = [p for p in new_pos if p['number'] not in processed_pos]
            
            if valid_pos:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Found {len(valid_pos)} new PO(s)")
                
                emails_sent_in_batch = 0
                max_ts_in_batch = last_processed_ts

                for i, po in enumerate(valid_pos):
                    print(f"  → PO #{po['number']} - ${po['amount']:,.2f} for {po['vendor_name']}")
                    
                    if send_po_email(po):
                         print(f"    ✓ Email sent to {po['email']}")
                         processed_pos.add(po['number'])
                         emails_sent_in_batch += 1
                         
                         # Save state immediately
                         save_processed_pos(processed_pos)
                         
                         # Throttling
                         if i < len(valid_pos) - 1:
                             if emails_sent_in_batch >= BATCH_SIZE:
                                 print(f"    ⏸ Batch pause: waiting {BATCH_PAUSE_SECONDS}s...")
                                 time.sleep(BATCH_PAUSE_SECONDS)
                                 emails_sent_in_batch = 0
                             else:
                                 time.sleep(EMAIL_DELAY_SECONDS)
                    else:
                        print("    ✗ Skipped (No Email or Error)")
                        # Even if skipped (no email), we mark as processed so we don't retry forever?
                        # Yes, otherwise we loop on it.
                        processed_pos.add(po['number'])
                        save_processed_pos(processed_pos)

                    # Update high water mark
                    if po['timestamp'] > max_ts_in_batch:
                         max_ts_in_batch = po['timestamp']

                # Update global high water mark
                last_processed_ts = max_ts_in_batch
                
                # Save timestamp
                with open(LAST_CHECK_FILE, 'w') as f:
                    f.write(last_processed_ts.isoformat())

            else:
                # If we found POs but they were all processed, we still update TS
                if new_pos:
                    max_ts = max(p['timestamp'] for p in new_pos)
                    if max_ts > last_processed_ts:
                        last_processed_ts = max_ts
                        with open(LAST_CHECK_FILE, 'w') as f:
                            f.write(last_processed_ts.isoformat())
            
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            print("\n\n→ Stopping...")
            break
        except Exception as e:
            print(f"Error in main loop: {e}")
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
