import schedule
import time
import datetime
import pytz
from generate_daily_production_report import generate_report, html_to_pdf, generate_ai_summary, send_report_email

RECIPIENTS = ["alexh@chemicaldynamics.com", "benc@chemicaldynamics.com"]

def job():
    print(f"[{datetime.datetime.now()}] Starting scheduled daily report job...")
    
    # 1. Generate Report Data (Default is "yesterday" production, "today" logic)
    result = generate_report(None)
    
    if result:
        report_html, prod_data, orders_data, target_date = result
        
        # 2. Convert Data to PDF
        pdf_path = "daily_production_report.pdf"
        print(f"[{datetime.datetime.now()}] Converting to PDF...")
        html_to_pdf(report_html, pdf_path)
        
        # 3. Generate Smart Summary Subject/Body
        print(f"[{datetime.datetime.now()}] Requesting AI Email Summary...")
        subject, body = generate_ai_summary(prod_data, orders_data, target_date)
        
        # 4. Dispatch the Report
        print(f"[{datetime.datetime.now()}] Dispatching email to {RECIPIENTS}...")
        send_report_email(RECIPIENTS, subject, body, pdf_path)
        
        print(f"[{datetime.datetime.now()}] Scheduled job completed successfully.")
    else:
        print(f"[{datetime.datetime.now()}] Job aborted. No report content generated.")

# Important: ensure timezone is explicitly 'US/Eastern' to handle DST changes seamlessly
# Note that `schedule` library version >= 1.2.0 supports `.at(tz=...)" natively. 
# Alternatively, since the server seems to be East Coast locally, we configure it safely.
# If schedule doesn't support the kwarg cleanly, we wrap the clock time in timezone.

# The modern way on schedule>=1.2.0 is to pass time and tz as arguments:
for day_method in [schedule.every().monday, schedule.every().tuesday, schedule.every().wednesday, schedule.every().thursday, schedule.every().friday]:    
    day_method.at("08:30", "US/Eastern").do(job)

if __name__ == "__main__":
    print(f"[{datetime.datetime.now()}] Service Start. Daily Production Report automatically scheduled for M-F @ 8:30 AM ET.")
    print(f"Target distribution list: {RECIPIENTS}")
    
    while True:
        schedule.run_pending()
        time.sleep(60) # Wake up every 60 seconds and check if it's 8:30 AM

