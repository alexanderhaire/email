# dynamics gp email automation configuration
import os
from dotenv import load_dotenv

load_dotenv()


# SQL Server Connection (Dynamics GP Database)
SQL_SERVER = "Dynamics GP"  # GP SQL Server
# Test Mode Toggle
#   True  = Use Test Company (TWO)
#   False = Use Production (CDI)
IS_TEST_MODE = False

# Dry Run Mode
#   True  = Check for invoices but DO NOT send emails (prints to console only)
#   False = Actually send emails
DRY_RUN = False

# Safe Redirection
#   True  = Intercept emails and send to TEST_EMAIL_RECIPIENT instead of client
#   False = Send to actual clients
REDIRECT_EMAILS = False
TEST_EMAIL_RECIPIENT = "alexh@chemicaldynamics.com"  # Your email for testing

# Tracking
# If True, invoices that exist when the script starts will NOT be emailed.
# Only invoices created AFTER startup will be processed.
SKIP_EXISTING_ON_STARTUP = True

if IS_TEST_MODE:
    SQL_DATABASE = "TWO"  # Standard GP Test Company
    DSN_NAME = "Customix" # Backup DSN
else:
    SQL_DATABASE = "CDI"  # Your GP company database
    DSN_NAME = "Customix" # Primary DSN for Production

# Connection Method
#   True  = Use ODBC DSN (Recommended if found)
#   False = Use Manual Server/Password
USE_DSN = True

SQL_USERNAME = "sa"  # SQL username (not used if USE_DSN + Windows Auth)
SQL_PASSWORD = "YOUR_PASSWORD"  # <-- CHANGE THIS

# Set to True to use Windows Authentication instead of SQL username/password
USE_WINDOWS_AUTH = True

# Resend API Key (now loaded from .env)
RESEND_API_KEY = os.getenv("RESEND_API_KEY")

# Email Settings
FROM_EMAIL = "alexh@chemicaldynamics.com"  # Must be verified in Resend
FROM_NAME = "Chemical Dynamics"

# Global CC (Always CC these addresses on every PO email)
# Comma-separated list of emails
PO_GLOBAL_CC = "alexh@chemicaldynamics.com"

# How often to check for new invoices (in seconds)
CHECK_INTERVAL = 60

# ============================================
# EMAIL THROTTLING (Prevent Outlook 451 Errors)
# ============================================
# Delay between emails in a batch (seconds)
# Recommended: 20-30 seconds to avoid Outlook throttling
EMAIL_DELAY_SECONDS = 25

# Batch pause: After this many emails, pause for BATCH_PAUSE_SECONDS
BATCH_SIZE = 10
BATCH_PAUSE_SECONDS = 120  # 2 minute pause after every 10 emails
