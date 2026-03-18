"""
Example Invoice - Send to alexh@chemicaldynamics.com for approval
Demonstrates: Separate Bill-To / Ship-To addresses + PDF attachment

This is a PREVIEW ONLY. Does not touch the production invoice system.
"""

import os
import resend
from config import RESEND_API_KEY, FROM_EMAIL, FROM_NAME


def build_invoice_html(invoice):
    """Build invoice HTML with full Bill-To / Ship-To addresses"""

    # Format line items
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

    invoice_date = invoice['date']
    po_display = invoice['po_number'] if invoice['po_number'] else '\u2014'

    # Build Bill-To address block
    bill_to_lines = f'<h3 style="margin: 0; color: #334155; font-size: 16px; font-weight: 600;">{invoice["bill_to"]["name"]}</h3>'
    if invoice["bill_to"].get("address1"):
        bill_to_lines += f'<p style="margin: 4px 0 0 0; color: #64748b; font-size: 14px;">{invoice["bill_to"]["address1"]}</p>'
    if invoice["bill_to"].get("address2"):
        bill_to_lines += f'<p style="margin: 2px 0 0 0; color: #64748b; font-size: 14px;">{invoice["bill_to"]["address2"]}</p>'
    city_st_zip = []
    if invoice["bill_to"].get("city"):
        city_st_zip.append(invoice["bill_to"]["city"])
    if invoice["bill_to"].get("state"):
        city_st_zip.append(invoice["bill_to"]["state"])
    if invoice["bill_to"].get("zip"):
        city_st_zip[-1] = city_st_zip[-1] + "  " + invoice["bill_to"]["zip"]
    if city_st_zip:
        bill_to_lines += f'<p style="margin: 2px 0 0 0; color: #64748b; font-size: 14px;">{", ".join(city_st_zip)}</p>'

    # Build Ship-To address block
    ship_to_lines = f'<h3 style="margin: 0; color: #334155; font-size: 16px; font-weight: 600;">{invoice["ship_to"]["name"]}</h3>'
    if invoice["ship_to"].get("attention"):
        ship_to_lines += f'<p style="margin: 4px 0 0 0; color: #64748b; font-size: 14px;">{invoice["ship_to"]["attention"]}</p>'
    if invoice["ship_to"].get("address1"):
        ship_to_lines += f'<p style="margin: 4px 0 0 0; color: #64748b; font-size: 14px;">{invoice["ship_to"]["address1"]}</p>'
    if invoice["ship_to"].get("address2"):
        ship_to_lines += f'<p style="margin: 2px 0 0 0; color: #64748b; font-size: 14px;">{invoice["ship_to"]["address2"]}</p>'
    ship_city_st_zip = []
    if invoice["ship_to"].get("city"):
        ship_city_st_zip.append(invoice["ship_to"]["city"])
    if invoice["ship_to"].get("state"):
        ship_city_st_zip.append(invoice["ship_to"]["state"])
    if invoice["ship_to"].get("zip"):
        ship_city_st_zip[-1] = ship_city_st_zip[-1] + "  " + invoice["ship_to"]["zip"]
    if ship_city_st_zip:
        ship_to_lines += f'<p style="margin: 2px 0 0 0; color: #64748b; font-size: 14px;">{", ".join(ship_city_st_zip)}</p>'

    html = f"""
    <!DOCTYPE html>
    <html>
    <body style="margin: 0; padding: 0; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f4f6f8;">

        <div style="max-width: 680px; margin: 40px auto; background: #ffffff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); overflow: hidden;">

            <!-- Logo Header -->
            <div style="background: #ffffff; padding: 30px 40px 20px 40px; text-align: center; border-bottom: 1px solid #f0f0f0;">
                <img src="https://www.chemicaldynamics.com/wp-content/uploads/2022/10/CD-logo-350x20-NEW2-1.png"
                     width="220"
                     alt="Chemical Dynamics Inc."
                     style="display: inline-block; border: 0; outline: none; text-decoration: none; height: auto; max-width: 220px;" />
                <p style="margin: 10px 0 0 0; color: #64748b; font-size: 13px;">P.O. Box 486<br>Plant City, FL 33564-0468<br>Phone: 1-813-752-4950</p>
            </div>

            <!-- Company Header -->
            <div style="background: #ffffff; padding: 20px 40px 20px 40px; border-bottom: 1px solid #f0f0f0;">
                <table width="100%">
                    <tr>
                        <td style="vertical-align: top;">
                            <p style="margin: 0 0 5px 0; font-size: 11px; text-transform: uppercase; color: #94a3b8; font-weight: 600; letter-spacing: 0.5px;">PO #</p>
                            <p style="margin: 0; font-size: 16px; color: #334155; font-weight: 600;">{po_display}</p>
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

                <!-- Bill To & Ship To -->
                <table width="100%" style="margin-bottom: 30px;">
                    <tr>
                        <td width="50%" style="vertical-align: top; padding-right: 20px;">
                             <p style="margin: 0 0 8px 0; font-size: 11px; text-transform: uppercase; color: #94a3b8; font-weight: 600; letter-spacing: 0.5px;">Bill To</p>
                             {bill_to_lines}
                        </td>
                        <td width="50%" style="vertical-align: top; padding-left: 20px;">
                             <p style="margin: 0 0 8px 0; font-size: 11px; text-transform: uppercase; color: #94a3b8; font-weight: 600; letter-spacing: 0.5px;">Ship To</p>
                             {ship_to_lines}
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
                        <td width="55%">
                            <!-- Blank space -->
                        </td>
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
                    TERMS: NET 30 DAYS. A finance charge of 1\u00bd% per month (18% per annum) will be charged on all past due accounts.
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
    return html


def html_to_pdf(html_content, output_filename):
    """Convert HTML invoice to PDF using Playwright"""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html_content)
        page.pdf(
            path=output_filename,
            format="A4",
            print_background=True,
            margin={"top": "20px", "right": "20px", "bottom": "20px", "left": "20px"}
        )
        browser.close()
    return os.path.abspath(output_filename)


def send_example():
    """Send example invoice with separate bill-to / ship-to + PDF attachment"""

    # Example data based on the physical invoice (Golf Ventures / Yacht & Country Club)
    invoice = {
        'number': '100004904A',
        'date': 'March 4, 2026',
        'amount': 1387.50,
        'subtotal': 1387.50,
        'freight': 0.00,
        'tax': 0.00,
        'discount': 0.00,
        'po_number': '058626',
        'customer_id': 'GOLFVENTURES',
        'bill_to': {
            'name': 'Golf Ventures, Inc.',
            'address1': '5385 Gateway Blvd, Ste 12',
            'city': 'Lakeland',
            'state': 'FL',
            'zip': '33811',
        },
        'ship_to': {
            'name': 'Golf Ventures, Inc.',
            'attention': 'The Yacht & Country Club, Inc.',
            'address1': '3750 SE Fairway West',
            'city': 'Stuart',
            'state': 'FL',
            'zip': '34997',
        },
        'lines': [
            {
                'item_number': 'FLOMOLA250',
                'description': 'Bay Cane Molasses',
                'quantity': 250.00,
                'unit_price': 5.55,
                'extended_price': 1387.50,
            }
        ]
    }

    # 1. Build invoice HTML
    print("Building invoice HTML...")
    invoice_html = build_invoice_html(invoice)

    # 2. Convert to PDF
    pdf_filename = "example_invoice_100004904A.pdf"
    print(f"Converting to PDF ({pdf_filename})...")
    pdf_path = html_to_pdf(invoice_html, pdf_filename)
    print(f"  PDF saved: {pdf_path}")

    # 3. Send email with PDF attached
    resend.api_key = RESEND_API_KEY

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    email_body = """
    <div style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <p style="color: #334155; font-size: 16px;">Hi Alex,</p>
        <p style="color: #475569; font-size: 15px; line-height: 1.6;">
            Attached is an <strong>example invoice PDF</strong> for your review. This demonstrates the updated invoice layout with:
        </p>
        <ul style="color: #475569; font-size: 15px; line-height: 1.8;">
            <li><strong>Separate Bill-To and Ship-To addresses</strong> &mdash; pulled from GP's customer address master (RM00102) and the invoice's ship-to address code</li>
            <li><strong>PDF attachment</strong> &mdash; the invoice is now attached as a PDF rather than only displayed in the email body</li>
        </ul>
        <p style="color: #475569; font-size: 15px; line-height: 1.6;">
            The example uses data from the Golf Ventures / Yacht &amp; Country Club invoice you provided.
        </p>
        <p style="color: #475569; font-size: 15px; line-height: 1.6;">
            Please review and let me know if the layout looks good or if you'd like any changes before I implement this into the production invoice system.
        </p>
        <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 30px 0;" />
        <p style="color: #94a3b8; font-size: 12px;">This is a test email. No changes have been made to the production invoice system.</p>
    </div>
    """

    print("Sending example invoice to alexh@chemicaldynamics.com...")
    try:
        resend.Emails.send({
            "from": f"{FROM_NAME} <{FROM_EMAIL}>",
            "to": ["alexh@chemicaldynamics.com"],
            "subject": "[PREVIEW] Example Invoice with Bill-To / Ship-To + PDF Attachment",
            "html": email_body,
            "attachments": [{
                "filename": f"Invoice_{invoice['number']}.pdf",
                "content": list(pdf_bytes)
            }]
        })
        print("  Email sent successfully!")
    except Exception as e:
        print(f"  Failed to send email: {e}")

    # Cleanup
    if os.path.exists(pdf_filename):
        os.remove(pdf_filename)
        print(f"  Cleaned up temp file: {pdf_filename}")


if __name__ == "__main__":
    send_example()
