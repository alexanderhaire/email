import os
import resend
from config import RESEND_API_KEY, FROM_EMAIL, FROM_NAME

# Setup Resend
resend.api_key = RESEND_API_KEY

# Report File Path
REPORT_FILE = r"C:\Users\alexh\Downloads\mod\daily_production_report.txt"

def send_daily_report():
    if not os.path.exists(REPORT_FILE):
        print(f"Error: Report file not found at {REPORT_FILE}")
        return

    try:
        with open(REPORT_FILE, 'r') as f:
            report_content = f.read()
    except Exception as e:
        print(f"Error reading report file: {e}")
        return

    # Prepare Email
    # Using <pre> tag to preserve formatting of the text report
    html_content = f"""
    <html>
    <body style="font-family: monospace;">
        <h2>Daily Production & Inventory Report</h2>
        <pre>{report_content}</pre>
    </body>
    </html>
    """

    params = {
        "from": f"{FROM_NAME} <{FROM_EMAIL}>",
        "to": ["alexh@chemicaldynamics.com"],
        "subject": "Daily Production Report",
        "html": html_content
    }

    try:
        print("Sending email...")
        email = resend.Emails.send(params)
        print(f"Email sent successfully! ID: {email.get('id')}")
    except Exception as e:
        print(f"Failed to send email: {e}")

if __name__ == "__main__":
    send_daily_report()
