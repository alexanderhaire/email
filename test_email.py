import resend
from config import RESEND_API_KEY, FROM_EMAIL, FROM_NAME

def send_test_email():
    print("Sending test email...")
    resend.api_key = RESEND_API_KEY
    
    # Send to the sender for testing purposes
    # to_email = "janec@chemicaldynamics.com"
    to_email = FROM_EMAIL 
    
    print(f"From: {FROM_NAME} <{FROM_EMAIL}>")
    print(f"To: {to_email}")
    print(f"Using Key: {RESEND_API_KEY[:5]}...")
    
    try:
        r = resend.Emails.send({
            "from": f"{FROM_NAME} <{FROM_EMAIL}>",
            "to": [to_email],
            "subject": "Test Email from Invoice Automator",
            "html": "<p><strong>Success!</strong> Your email configuration is working correctly.</p>"
        })
        print("Success! Email sent.")
        print(f"ID: {r.get('id')}")
    except Exception as e:
        print(f"Failed to send email: {e}")

if __name__ == "__main__":
    send_test_email()
