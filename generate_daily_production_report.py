import datetime
import argparse
import os
import json
import re
try:
    import tomllib
except ModuleNotFoundError:
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        tomllib = None
from db_pool import get_connection
from production_queries import fetch_completed_production, fetch_open_orders_buckets
from inventory_queries import fetch_on_hand_by_item

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
        orders_data = fetch_open_orders_buckets(cursor, target_date)

        # 3. Fetch On-Hand Inventory for alerts
        print("Fetching On-Hand Inventory for Discrepancy Alerts...")
        buckets = orders_data['buckets']
        alert_candidates = buckets['due_today'] + buckets['past_due']
        items_to_check = list({order['item_number'] for order in alert_candidates})
        on_hand_inventory, _ = fetch_on_hand_by_item(cursor, items_to_check)

    # --- FORMAT OUTPUT (HTML) ---

    buckets = orders_data['buckets']
    tomorrow = target_date + datetime.timedelta(days=1)
    all_future = buckets['future']

    # Cross-reference: match each canned item to its earliest open order
    all_orders = buckets['past_due'] + buckets['due_today'] + buckets['due_tomorrow'] + all_future + buckets.get('invoiced', [])
    item_to_order = {}
    for order in sorted(all_orders, key=lambda o: (o.get('is_history', False), o['req_date'])):
        item = order['item_number']
        if item not in item_to_order:
            item_to_order[item] = order

    # Match Canning
    for entry in prod_data['canning']:
        match = item_to_order.get(entry['item_number'])
        if not match:
            for order in all_orders:
                if order['item_number'].startswith(entry['item_number']):
                    match = order
                    break

        if match:
            entry['customer'] = match['customer']
            entry['req_date'] = 'Invoiced' if match.get('is_history') else match['req_date']
            entry['order_number'] = match['order_number']
        else:
            entry['customer'] = 'No open order'
            entry['req_date'] = ''
            entry['order_number'] = ''

    # Match Mixing
    for entry in prod_data['mixing']:
        prod_item = entry['item_number']
        base_prefix = re.sub(r'00[#G]?$', '', prod_item)
        match = item_to_order.get(prod_item)
        
        if not match:
            for order in all_orders:
                if order['item_number'].startswith(base_prefix):
                    match = order
                    break

        if match:
            entry['customer'] = match['customer']
            entry['req_date'] = 'Invoiced' if match.get('is_history') else match['req_date']
            entry['order_number'] = match['order_number']
        else:
            entry['customer'] = 'No open order'
            entry['req_date'] = ''
            entry['order_number'] = ''

    # Calculate summary stats
    total_produced_gal = sum(i['quantity'] for i in prod_data['canning'])
    total_ordered_gal = sum(i['quantity'] for i in buckets['due_today'])
    past_due_count = len(buckets['past_due'])
    now_str = datetime.datetime.now().strftime('%I:%M %p')

    # --- Helper: build a table of items ---
    def _make_table_rows(items, columns, row_bg_alt=True):
        """Build <tr> rows for a list of dicts. columns = list of (key, label, align, formatter)"""
        rows = []
        for idx, item in enumerate(items):
            bg = ' style="background: #fafbfc;"' if (row_bg_alt and idx % 2 == 1) else ''
            cells = []
            for key, _label, align, fmt in columns:
                val = item.get(key, '')
                if fmt:
                    val = fmt(val, item)
                a = f' text-align: {align};' if align != 'left' else ''
                fw = ' font-weight: 600;' if align == 'right' else ''
                cells.append(f'<td style="padding: 8px 12px; border-bottom: 1px solid #f1f5f9;{a}{fw}">{val}</td>')
            rows.append(f'<tr{bg}>{"".join(cells)}</tr>')
        return "\n".join(rows)

    def _make_header(columns):
        cells = []
        for _key, label, align, _fmt in columns:
            a = f' text-align: {align};' if align != 'left' else ''
            cells.append(f'<th style="padding: 8px 12px;{a} color: #64748b; font-weight: 600; font-size: 11px; border-bottom: 2px solid #e2e8f0;">{label}</th>')
        return f'<tr style="background: #f1f5f9;">{"".join(cells)}</tr>'

    # --- Quantity formatter ---
    def qty_fmt(val, item):
        try:
            return f'{float(val):,.0f} {item.get("uofm", "")}'
        except (ValueError, TypeError):
            return str(val)

    def qty_only(val, _item):
        try:
            return f'{float(val):,.0f}'
        except (ValueError, TypeError):
            return str(val)

    def relative_date(val, item):
        """Show date as relative days from production date: -5, 0, +10"""
        if item.get('order_number') and item.get('req_date') == 'Invoiced':
            return '<span class="label-invoiced" style="color: #059669; font-weight: 600; font-size: 11px; padding: 3px 8px; border-radius: 4px; background: #d1fae5;">Shipped</span>'

        if str(val) == 'Invoiced':
            return '<span class="label-invoiced" style="color: #059669; font-weight: 600; font-size: 11px; padding: 3px 8px; border-radius: 4px; background: #d1fae5;">Shipped</span>'

        try:
            req = datetime.datetime.strptime(str(val), '%Y-%m-%d').date()
            delta = (req - target_date).days
            if delta == 0:
                return 'Today'
            return f'{delta:+d}d'
        except (ValueError, TypeError):
            return str(val)

    # ==================== BUILD HTML ====================
    # Using inline styles for email compatibility

    # --- Mixing rows ---
    mix_cols = [
        ('mo_number', 'MO NUMBER', 'left', None),
        ('item_number', 'ITEM NUMBER', 'left', None),
        ('description', 'DESCRIPTION', 'left', None),
        ('quantity', 'QUANTITY', 'right', qty_only),
        ('uofm', 'UNIT', 'center', None),
        ('customer', 'CUSTOMER', 'left', None),
        ('req_date', 'DAYS', 'center', relative_date),
    ]
    mixing_rows = _make_table_rows(prod_data['mixing'], mix_cols) if prod_data['mixing'] else '<tr><td colspan="7" style="padding: 12px; color: #94a3b8; font-style: italic;">No mixing activity recorded.</td></tr>'

    # --- Canning rows (with order link: customer + days) ---
    can_cols = [
        ('mo_number', 'MO NUMBER', 'left', None),
        ('item_number', 'ITEM NUMBER', 'left', None),
        ('description', 'DESCRIPTION', 'left', None),
        ('quantity', 'QUANTITY', 'right', qty_only),
        ('uofm', 'UNIT', 'center', None),
        ('customer', 'CUSTOMER', 'left', None),
        ('req_date', 'DAYS', 'center', relative_date),
    ]
    canning_rows = _make_table_rows(prod_data['canning'], can_cols) if prod_data['canning'] else '<tr><td colspan="7" style="padding: 12px; color: #94a3b8; font-style: italic;">No canning activity recorded.</td></tr>'

    # --- Bucket rows (all buckets include relative date) ---
    bucket_cols = [
        ('order_number', 'ORDER #', 'left', None),
        ('req_date', 'DAYS', 'center', relative_date),
        ('customer', 'CUSTOMER', 'left', None),
        ('item_number', 'ITEM', 'left', None),
        ('quantity', 'QTY', 'right', qty_fmt),
    ]

    def _bucket_section(title, subtitle, items, cols, bg_color, border_color, text_color, header_color, empty_msg="No orders in this category."):
        header = _make_header(cols)
        rows = _make_table_rows(items, cols) if items else f'<tr><td colspan="{len(cols)}" style="padding: 12px; color: #94a3b8; font-style: italic;">{empty_msg}</td></tr>'
        return f'''
        <div style="background: {bg_color}; border: 1px solid {border_color}; border-radius: 6px; padding: 18px 20px; margin-bottom: 18px;">
            <h3 style="margin: 0 0 4px 0; font-size: 14px; color: {text_color}; font-weight: 700;">{title}</h3>
            <p style="margin: 0 0 8px 0; font-size: 12px; color: {header_color};">{subtitle}</p>
            <p style="margin: 0 0 10px 0; font-size: 13px; color: {text_color}; font-weight: 600;">{len(items)} item(s)</p>
            <table width="100%" cellpadding="0" cellspacing="0" style="font-size: 13px; border-collapse: collapse;">
                <thead>{header}</thead>
                <tbody>{rows}</tbody>
            </table>
        </div>'''

    past_due_html = _bucket_section(
        f"BUCKET 1: PAST DUE (Critical Attention)",
        f"Orders with delivery dates before {target_date.strftime('%b %d')} that have not been invoiced",
        buckets['past_due'], bucket_cols,
        '#fef2f2', '#fecaca', '#dc2626', '#991b1b'
    )
    due_today_html = _bucket_section(
        f"BUCKET 2: DUE TODAY &mdash; {target_date.strftime('%b %d')} (Current Focus)",
        "Orders scheduled for delivery today",
        buckets['due_today'], bucket_cols,
        '#fffbeb', '#fde68a', '#d97706', '#92400e'
    )
    due_tomorrow_html = _bucket_section(
        f"BUCKET 3: DUE TOMORROW &mdash; {tomorrow.strftime('%b %d')} (Planning)",
        "Orders scheduled for tomorrow",
        buckets['due_tomorrow'], bucket_cols,
        '#eff6ff', '#bfdbfe', '#2563eb', '#1e40af'
    )
    future_html = _bucket_section(
        "BUCKET 4: FUTURE ORDERS &amp; DEFERRED",
        "All open orders with future delivery dates",
        all_future, bucket_cols,
        '#f8fafc', '#e2e8f0', '#475569', '#64748b'
    )

    # --- Discrepancy Alerts ---
    # Cross-reference: items due today/past due that have no matching canning completion AND insufficient inventory
    canned_items = {i['item_number'] for i in prod_data['canning']}
    alerts_html = ""
    for order in buckets['due_today'] + buckets['past_due']:
        qty_needed = order['quantity']
        on_hand = on_hand_inventory.get(order['item_number'], 0)
        
        if order['item_number'] not in canned_items and qty_needed > 0 and on_hand < qty_needed:
            bucket_label = "past due" if order in buckets['past_due'] else "due today"
            alerts_html += f'''
            <div style="background: #fef2f2; border-left: 4px solid #dc2626; border-radius: 0 6px 6px 0; padding: 14px 18px; margin-bottom: 12px;">
                <p style="margin: 0 0 2px 0; font-size: 11px; text-transform: uppercase; color: #dc2626; font-weight: 700; letter-spacing: 0.3px;">Production Gap</p>
                <p style="margin: 0; font-size: 14px; color: #1e293b; line-height: 1.5;">Order <strong>#{order['order_number']}</strong> ({order['customer']}) requires <strong>{qty_needed:,.0f} {order['uofm']}</strong> of {order['item_number']} ({bucket_label}), but no C-Sheet completion was found and only <strong>{on_hand:,.0f}</strong> are in stock.</p>
            </div>'''
            # Limit to first 5 alerts to keep email manageable
            if alerts_html.count('Production Gap') >= 5:
                alerts_html += f'<p style="margin: 10px 0 0 0; font-size: 12px; color: #991b1b; font-style: italic;">+ additional gaps exist &mdash; see full report for details</p>'
                break

    if not alerts_html:
        alerts_html = '<p style="color: #16a34a; font-size: 14px; font-weight: 500;">No discrepancies detected. Production and orders are aligned.</p>'

    # --- Assemble full HTML ---
    final_output = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Daily Production &amp; Logistics Report - {target_date}</title></head>
<body style="margin: 0; padding: 0; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f4f6f8; color: #1e293b;">

<div style="max-width: 780px; margin: 30px auto; background: #ffffff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); overflow: hidden;">

    <!-- Logo Header -->
    <div style="background: #ffffff; padding: 25px 40px 15px 40px; text-align: center; border-bottom: 1px solid #e2e8f0;">
        <img src="https://www.chemicaldynamics.com/wp-content/uploads/2022/10/CD-logo-350x20-NEW2-1.png" width="200" alt="Chemical Dynamics Inc." style="display: inline-block; border: 0; outline: none; text-decoration: none; height: auto; max-width: 200px;" />
    </div>

    <!-- Report Title Banner -->
    <div style="background: #0f172a; padding: 20px 40px; text-align: center;">
        <h1 style="margin: 0; color: #ffffff; font-size: 20px; font-weight: 700; letter-spacing: 0.5px;">Daily Production &amp; Logistics Report</h1>
    </div>

    <!-- ==================== HEADER: SNAPSHOT SUMMARY ==================== -->
    <div style="background: #f8fafc; padding: 25px 40px; border-bottom: 2px solid #e2e8f0;">
        <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
                <td width="50%" style="vertical-align: top;">
                    <p style="margin: 0 0 4px 0; font-size: 11px; text-transform: uppercase; color: #94a3b8; font-weight: 600; letter-spacing: 0.5px;">Production Date</p>
                    <p style="margin: 0 0 14px 0; font-size: 16px; color: #0f172a; font-weight: 600;">{target_date.strftime('%A, %b %d, %Y')}</p>
                    <p style="margin: 0 0 4px 0; font-size: 11px; text-transform: uppercase; color: #94a3b8; font-weight: 600; letter-spacing: 0.5px;">Report Generated</p>
                    <p style="margin: 0; font-size: 16px; color: #0f172a; font-weight: 600;">{datetime.datetime.now().strftime('%A, %b %d, %Y')} at {now_str}</p>
                </td>
                <td width="50%" style="vertical-align: top;">
                    <p style="margin: 0 0 4px 0; font-size: 11px; text-transform: uppercase; color: #94a3b8; font-weight: 600; letter-spacing: 0.5px;">Daily Production Total</p>
                    <p style="margin: 0 0 14px 0; font-size: 16px; color: #0f172a; font-weight: 600;">{total_produced_gal:,.0f} produced &nbsp;/&nbsp; {total_ordered_gal:,.0f} due today</p>
                    <p style="margin: 0 0 4px 0; font-size: 11px; text-transform: uppercase; color: #94a3b8; font-weight: 600; letter-spacing: 0.5px;">Production Activity</p>
                    <p style="margin: 0; font-size: 16px; color: #0f172a; font-weight: 600;">{len(prod_data['mixing'])} mixing &nbsp;/&nbsp; {len(prod_data['canning'])} canning</p>
                </td>
            </tr>
        </table>
        <!-- Alert Badges -->
        <div style="margin-top: 15px;">
            <span style="display: inline-block; background: {'#fef2f2' if past_due_count > 0 else '#f0fdf4'}; color: {'#dc2626' if past_due_count > 0 else '#16a34a'}; padding: 6px 14px; border-radius: 4px; font-size: 13px; font-weight: 600; margin-right: 10px; border: 1px solid {'#fecaca' if past_due_count > 0 else '#bbf7d0'};">{past_due_count} Past Due Item{'s' if past_due_count != 1 else ''}</span>
            <span style="display: inline-block; background: #eff6ff; color: #2563eb; padding: 6px 14px; border-radius: 4px; font-size: 13px; font-weight: 600; border: 1px solid #bfdbfe;">{len(buckets['due_today'])} Due Today</span>
            <span style="display: inline-block; background: #f8fafc; color: #475569; padding: 6px 14px; border-radius: 4px; font-size: 13px; font-weight: 600; margin-left: 10px; border: 1px solid #e2e8f0;">{len(buckets['due_tomorrow'])} Due Tomorrow</span>
        </div>
    </div>

    <!-- ==================== SECTION 1: PRODUCTION THROUGHPUT ==================== -->
    <div style="padding: 30px 40px 0 40px;">
        <h2 style="margin: 0 0 5px 0; font-size: 17px; color: #0f172a; font-weight: 700;">Section 1: Production Throughput</h2>
        <p style="margin: 0 0 20px 0; font-size: 13px; color: #64748b;">Grouped by activity type</p>

        <!-- 1.1 Mixing & Blending -->
        <h3 style="margin: 0 0 10px 0; font-size: 14px; color: #334155; font-weight: 700; text-transform: uppercase; letter-spacing: 0.3px; border-left: 4px solid #3b82f6; padding-left: 10px;">1.1 Mixing &amp; Blending (X-Sheets)</h3>
        <p style="margin: 0 0 10px 0; font-size: 12px; color: #94a3b8;">What is staged and ready for packaging</p>
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 25px; font-size: 13px; border-collapse: collapse;">
            <thead>{_make_header(mix_cols)}</thead>
            <tbody>{mixing_rows}</tbody>
        </table>

        <!-- 1.2 Packaging & Canning -->
        <h3 style="margin: 0 0 10px 0; font-size: 14px; color: #334155; font-weight: 700; text-transform: uppercase; letter-spacing: 0.3px; border-left: 4px solid #10b981; padding-left: 10px;">1.2 Packaging &amp; Canning (C-Sheets)</h3>
        <p style="margin: 0 0 10px 0; font-size: 12px; color: #94a3b8;">Finished goods ready for shipment</p>
        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom: 25px; font-size: 13px; border-collapse: collapse;">
            <thead>{_make_header(can_cols)}</thead>
            <tbody>{canning_rows}</tbody>
        </table>
    </div>

    <!-- Divider -->
    <div style="padding: 0 40px;"><hr style="border: none; border-top: 2px solid #e2e8f0; margin: 10px 0 30px 0;" /></div>

    <!-- ==================== SECTION 2: ORDER LOGISTICS (4-BUCKET SYSTEM) ==================== -->
    <div style="padding: 0 40px;">
        <h2 style="margin: 0 0 5px 0; font-size: 17px; color: #0f172a; font-weight: 700;">Section 2: Order Logistics</h2>
        <p style="margin: 0 0 25px 0; font-size: 13px; color: #64748b;">The &ldquo;4-Bucket&rdquo; system &mdash; identifying breaks in the chain</p>

        {past_due_html}
        {due_today_html}
        {due_tomorrow_html}
        {future_html}
    </div>

    <!-- Divider -->
    <div style="padding: 0 40px;"><hr style="border: none; border-top: 2px solid #e2e8f0; margin: 5px 0 30px 0;" /></div>

    <!-- ==================== SECTION 3: DISCREPANCY ALERTS ==================== -->
    <div style="padding: 0 40px 30px 40px;">
        <h2 style="margin: 0 0 5px 0; font-size: 17px; color: #0f172a; font-weight: 700;">Section 3: Discrepancy Alerts</h2>
        <p style="margin: 0 0 20px 0; font-size: 13px; color: #64748b;">Automated gap analysis &mdash; flagging orders without matching production</p>
        {alerts_html}
    </div>

    <!-- ==================== FOOTER ==================== -->
    <div style="background: #0f172a; padding: 25px 40px; text-align: center;">
        <p style="margin: 0 0 5px 0; color: #94a3b8; font-size: 12px;">Chemical Dynamics, Inc. &bull; 4206 Business Lane &bull; Plant City, FL 33566</p>
        <p style="margin: 0; color: #64748b; font-size: 11px;">This is an automated daily report. Report generated at {now_str} on {datetime.datetime.now().strftime('%b %d, %Y')}.</p>
    </div>

</div>

</body>
</html>"""

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
