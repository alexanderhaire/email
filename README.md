# Dynamics GP Invoice Email Automation

Automatically sends email notifications when invoices are created in Microsoft Dynamics GP.

## Quick Setup

### 1. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 2. Get Resend API Key
1. Sign up free at [resend.com](https://resend.com)
2. Create an API key
3. Add and verify your sending domain

### 3. Configure Settings
Edit `config.py` with your:
- SQL Server name and credentials
- GP database name
- Resend API key
- From email address

### 4. Run
```bash
python invoice_emailer.py
```

## How It Works

1. Script checks GP database every 60 seconds for new invoices
2. New invoices trigger an email to the customer
3. Sent invoices are tracked in `sent_invoices.json` to avoid duplicates

## Customer Email Source

The script looks for customer email in:
1. `RM00102` (Customer Address table - EMAIL field)
2. `RM00101` (Customer Master - USERDEF1 as fallback)

Make sure customer emails are populated in GP!

## Purchase Order Automation (New)

The system now supports emailing Purchase Orders to vendors.

### Quick Start
Run the PO Monitor separately:
```bash
start_po_monitor.bat
# OR
python po_emailer.py
```

### Features
- Monitors `POP10100` for new Purchase Orders.
- Sends emails to Vendors using the primary address email.
- Tracks processed POs in `processed_pos.json` to handle edits/updates safely.
- Uses the same `config.py` as the Invoice system.
