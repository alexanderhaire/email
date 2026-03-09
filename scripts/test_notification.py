
import sys
import os

# Add root directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from secrets_loader import load_project_secrets
from notifications.teams_notifier import send_test_message

def main():
    print("Loading secrets...")
    secrets = load_project_secrets()
    webhook_url = secrets.get("teams", {}).get("webhook_url")
    
    if not webhook_url:
        print("Error: 'teams_webhook_url' not found in secrets.toml")
        return

    print(f"Sending test message to: {webhook_url[:30]}...")
    success = send_test_message(webhook_url)
    
    if success:
        print("Test message sent successfully!")
    else:
        print("Failed to send test message.")

if __name__ == "__main__":
    main()
