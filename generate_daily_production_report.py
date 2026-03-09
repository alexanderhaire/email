import datetime
import argparse
import os
import json
try:
    import tomllib
except ModuleNotFoundError:
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        tomllib = None
from db_pool import get_connection
from production_queries import fetch_completed_production, fetch_open_orders_buckets

def generate_report(target_date_str: str = None):
    # Default to "Yesterday" for production, "Today" for Open Orders reference
    today = datetime.date.today()
    if target_date_str:
        try:
            target_date = datetime.datetime.strptime(target_date_str, "%Y-%m-%d").date()
        except ValueError:
            print("Invalid date format. Use YYYY-MM-DD")
            return
    else:
        # Default target date is the previous business day
        # If today is Monday (0), go back 3 days to Friday.
        # Otherwise, go back 1 day.
        if today.weekday() == 0:
            target_date = today - datetime.timedelta(days=3)
        else:
            target_date = today - datetime.timedelta(days=1)

    print(f"Generating Report for Production Date: {target_date} (Run Date: {today})\n")

    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Fetch Production Data
        print("Fetching Production Data...")
        prod_data = fetch_completed_production(cursor, target_date)
        
        # 2. Fetch Open Orders
        print("Fetching Open Orders...")
        orders_data = fetch_open_orders_buckets(cursor, today)

    # --- FORMAT OUTPUT (HTML) ---
    
    html_content = []
    
    # CSS Styles
    css_styles = """
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; background-color: #f4f4f9; color: #333; }
        h1 { color: #2c3e50; border-bottom: 2px solid #2c3e50; padding-bottom: 10px; }
        h2 { color: #34495e; margin-top: 30px; border-bottom: 1px solid #bdc3c7; padding-bottom: 5px; }
        h3 { color: #7f8c8d; margin-top: 20px; margin-bottom: 10px; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); background-color: white; }
        th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #3498db; color: white; text-transform: uppercase; letter-spacing: 0.1em; font-size: 0.9em; }
        tr:hover { background-color: #f1f1f1; }
        .bucket-title { background-color: #e67e22; color: white; padding: 5px 10px; border-radius: 4px; display: inline-block; margin-bottom: 10px; }
        .past-due { color: #c0392b; font-weight: bold; }
        .empty-message { font-style: italic; color: #7f8c8d; padding: 10px; }
        .footer { margin-top: 40px; font-size: 0.8em; color: #95a5a6; text-align: center; border-top: 1px solid #ddd; padding-top: 10px; }
    </style>
    """
    
    html_content.append("<!DOCTYPE html>")
    html_content.append("<html>")
    html_content.append("<head>")
    html_content.append(f"<title>Daily Production & Inventory Report - {target_date}</title>")
    html_content.append(css_styles)
    html_content.append("</head>")
    html_content.append("<body>")
    
    html_content.append(f"<h1>Daily Production & Inventory Report</h1>")
    html_content.append(f"<p><strong>Production Date:</strong> {target_date.strftime('%A, %b %d, %Y')}</p>")
    html_content.append(f"<p><strong>Report Generated:</strong> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>")
    
    # PRODUCTION SECTION
    html_content.append(f"<h2>Production ({target_date})</h2>")
    
    # Mixing
    html_content.append(f"<h3>Mixing Sheets (X)</h3>")
    if prod_data['mixing']:
        html_content.append("<table>")
        html_content.append("<thead><tr><th>MO Number</th><th>Item Number</th><th>Quantity</th><th>Description</th></tr></thead>")
        html_content.append("<tbody>")
        for item in prod_data['mixing']:
            html_content.append(f"<tr><td>{item['mo_number']}</td><td>{item['item_number']}</td><td>{item['quantity']:.2f} {item['uofm']}</td><td>{item['description']}</td></tr>")
        html_content.append("</tbody></table>")
    else:
        html_content.append("<p class='empty-message'>No mixing activity recorded.</p>")

    # Canning
    html_content.append(f"<h3>Canning Sheets (C)</h3>")
    if prod_data['canning']:
        html_content.append("<table>")
        html_content.append("<thead><tr><th>MO Number</th><th>Item Number</th><th>Quantity</th><th>Description</th></tr></thead>")
        html_content.append("<tbody>")
        for item in prod_data['canning']:
            html_content.append(f"<tr><td>{item['mo_number']}</td><td>{item['item_number']}</td><td>{item['quantity']:.2f} {item['uofm']}</td><td>{item['description']}</td></tr>")
        html_content.append("</tbody></table>")
    else:
        html_content.append("<p class='empty-message'>No canning activity recorded.</p>")

    # ORDER LOGISTICS SECTION
    html_content.append(f"<h2>Order Logistics</h2>")
    buckets = orders_data['buckets']
    
    # Helper to print bucket (HTML)
    def add_bucket_html(title, items, bucket_id):
        html_content.append(f"<h3 class='bucket-title'>[{bucket_id}] {title} ({len(items)} Items)</h3>")
        if not items:
            html_content.append("<p class='empty-message'>No orders in this category.</p>")
            return

        html_content.append("<table>")
        html_content.append("<thead><tr><th>Order</th><th>Date</th><th>Customer</th><th>Item</th><th>Qty</th></tr></thead>")
        html_content.append("<tbody>")
        
        for item in items:
            # Removed limit based on user request
            
            row_class = "past-due" if bucket_id == 1 else ""
            cust_short = item['customer'] # No need to truncate for HTML usually, but can if needed
            html_content.append(f"<tr class='{row_class}'><td>{item['order_number']}</td><td>{item['req_date']}</td><td>{cust_short}</td><td>{item['item_number']}</td><td>{item['quantity']:.2f} {item['uofm']}</td></tr>")
        html_content.append("</tbody></table>")

    add_bucket_html(f"PAST DUE (Before {today})", buckets['past_due'], 1)
    add_bucket_html(f"DUE TODAY ({today})", buckets['due_today'], 2)
    add_bucket_html(f"DUE TOMORROW ({today + datetime.timedelta(days=1)})", buckets['due_tomorrow'], 3)
    
    # Future
    bucket_id = 4
    future_items = buckets['future']
    # Filter future for next 7 days only for the report
    next_week = today + datetime.timedelta(days=7)
    near_future = [i for i in future_items if i['req_date'] <= next_week.strftime('%Y-%m-%d')]
    
    add_bucket_html("FUTURE ORDERS (Next 7 Days Preview)", near_future, 4)

    html_content.append("<div class='footer'>")
    html_content.append("<p>Report generated by automated system. Please verify critical data.</p>")
    html_content.append("</div>")
    
    html_content.append("</body>")
    html_content.append("</html>")

    final_output = "\n".join(html_content)
    # print(final_output) # Optional: don't print huge HTML to console
    print("Report HTML generated.")
    
    # Save to file
    filename = "daily_production_report.html"
    with open(filename, "w") as f:
        f.write(final_output)
    print(f"\nReport saved to '{filename}' using absolute path {os.path.abspath(filename)}")
    
    return final_output, prod_data, orders_data, target_date

def generate_ai_summary(prod_data, orders_data, target_date):
    import openai
    
    api_key = None
    if tomllib is not None:
        try:
            with open("secrets.toml", "rb") as f:
                secrets = tomllib.load(f)
                api_key = secrets.get("openai", {}).get("api_key")
        except Exception as e:
            print(f"Error loading OpenAI API key from secrets: {e}")
            
    if not api_key:
        print("Warning: OpenAI API key not found. Using default summary.")
        return f"Daily Production Report - {target_date}", "Please find the attached daily production report."

    client = openai.OpenAI(api_key=api_key)
    
    # Calculate counts
    mixing_count = len(prod_data['mixing'])
    canning_count = len(prod_data['canning'])
    past_due_count = len(orders_data['buckets']['past_due'])
    due_today_count = len(orders_data['buckets']['due_today'])
    due_tomorrow_count = len(orders_data['buckets']['due_tomorrow'])

    # Format detailed data for the AI prompt
    mixing_details = "\n".join([f"- {item['quantity']:.0f} {item['uofm']} of {item['item_number']} ({item['description']})" for item in prod_data['mixing']])
    if not mixing_details: mixing_details = "None"
    
    canning_details = "\n".join([f"- {item['quantity']:.0f} {item['uofm']} of {item['item_number']} ({item['description']})" for item in prod_data['canning']])
    if not canning_details: canning_details = "None"
    
    past_due_details = "\n".join([f"- {item['customer']}: {item['quantity']:.0f} {item['uofm']} of {item['item_number']} (Req. Date: {item['req_date']})" for item in orders_data['buckets']['past_due']])
    if not past_due_details: past_due_details = "None"

    due_today_details = "\n".join([f"- {item['customer']}: {item['quantity']:.0f} {item['uofm']} of {item['item_number']}" for item in orders_data['buckets']['due_today']])
    if not due_today_details: due_today_details = "None"
    
    due_tomorrow_details = "\n".join([f"- {item['customer']}: {item['quantity']:.0f} {item['uofm']} of {item['item_number']}" for item in orders_data['buckets']['due_tomorrow']])
    if not due_tomorrow_details: due_tomorrow_details = "None"

    prompt = f"""
You are writing a high-level, narrative-style informative report for the production floor and shipping logistics.
Date: {target_date}

Here are the summary counts:
- Mixing tasks completed: {mixing_count}
- Canning tasks completed: {canning_count}
- Past Due Orders: {past_due_count}
- Due Today Orders: {due_today_count}
- Due Tomorrow Orders: {due_tomorrow_count}

Here is the raw data of what happened in Production:
MIXING:
{mixing_details}

CANNING/PACKAGING:
{canning_details}

Here is the raw data of the Shipping Logistics:
PAST DUE ORDERS:
{past_due_details}

DUE TODAY:
{due_today_details}

DUE TOMORROW:
{due_tomorrow_details}

Instructions:
You must return the summary in two parts within the HTML body:

1. A bulleted list of the summary counts exactly as provided above. Format it nicely with headings like "Production Activity:" and "Order Logistics:". Highlight past due orders in red if they exist.
2. Below the counts, write a highly descriptive, narrative report providing a high-level overview of the day's activity and current logistics situation based on the detailed data.
Use a storytelling narrative tone combining similar items when appropriate to make it readable in paragraph form.
Group large numbers and point out specific large quantities or notable customers as highlights.
Point out bottlenecks or crunch periods if there are many past due or due today orders.
The format for the narrative part should be 2-4 readable paragraphs of text formatted in HTML (use <p>, <b>, etc. as appropriate).
Don't just list the items in the narrative; weave them into a story about what the factory accomplished and the workload ahead of the logistics crew.

End with a brief mention that the full detailed report is attached as a PDF.
Do not wrap the JSON in markdown code blocks if returning JSON.
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates succinct email summaries for production reports. Always return valid JSON with two string keys: 'subject' and 'body'. Do NOT wrap the JSON in markdown."},
                {"role": "user", "content": prompt}
            ],
            response_format={ "type": "json_object" },
            temperature=0.7
        )
        content = response.choices[0].message.content
        result = json.loads(content)
        return result.get("subject", f"Daily Production Report - {target_date}"), result.get("body", "Please find the attached daily production report.")
    except Exception as e:
        print(f"OpenAI API Error: {e}")
        return f"Daily Production Report - {target_date}", "Please find the attached daily production report (AI summary failed)."

def html_to_pdf(html_content, output_filename):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html_content)
        page.pdf(path=output_filename, format="A4", print_background=True, margin={"top": "20px", "right": "20px", "bottom": "20px", "left": "20px"})
        browser.close()
    return os.path.abspath(output_filename)

def send_report_email(recipients, subject, body_html, pdf_path):
    import resend
    from config import RESEND_API_KEY, FROM_EMAIL, FROM_NAME
    
    if not RESEND_API_KEY:
        print("Error: RESEND_API_KEY not found in environment or config.")
        return

    resend.api_key = RESEND_API_KEY
    
    attachment = []
    if pdf_path and os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
            attachment = [{
                "filename": os.path.basename(pdf_path),
                "content": list(pdf_bytes)
            }]
            
    # Ensure recipients is a list
    if isinstance(recipients, str):
        recipients = [recipients]

    print(f"Sending email to {recipients}...")
    try:
        params = {
            "from": f"{FROM_NAME} <{FROM_EMAIL}>",
            "to": recipients,
            "subject": subject,
            "html": body_html
        }
        if attachment:
            params["attachments"] = attachment
            
        resend.Emails.send(params)
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="Target production date YYYY-MM-DD")
    parser.add_argument("--email", help="Command-separated email address(es) to send the report to")
    args = parser.parse_args()
    
    result = generate_report(args.date)
    
    if result:
        report_html, prod_data, orders_data, target_date = result
        
        pdf_path = "daily_production_report.pdf"
        print(f"Converting HTML to PDF ({pdf_path})...")
        html_to_pdf(report_html, pdf_path)
        
        if args.email:
            emails = [e.strip() for e in args.email.split(",") if e.strip()]
            print("Generating AI Summary...")
            subject, body = generate_ai_summary(prod_data, orders_data, target_date)
            send_report_email(emails, subject, body, pdf_path)
        else:
            print("No email address provided. Report generation complete.")
    else:
        print("No report content generated.")
