import resend
from config import RESEND_API_KEY

def debug_resend():
    resend.api_key = RESEND_API_KEY
    print(f"resend.emails type: {type(resend.emails)}")
    print(f"resend.emails dir: {dir(resend.emails)}")
    
    if hasattr(resend, 'Emails'):
         print(f"resend.Emails type: {type(resend.Emails)}")
         print(f"resend.Emails dir: {dir(resend.Emails)}")

if __name__ == "__main__":
    debug_resend()
