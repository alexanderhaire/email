@echo off
echo Starting Dynamics GP Invoice Emailer System...
echo =====================================================

echo 1. Starting Web Interface...
start /B "C:\Users\alexh\AppData\Local\Programs\Python\Python312\python.exe" email_manager_app.py

echo 2. Starting Invoice Monitor...
start /B "C:\Users\alexh\AppData\Local\Programs\Python\Python312\python.exe" invoice_emailer.py

echo 3. Starting Purchase Order Monitor...
start /B "C:\Users\alexh\AppData\Local\Programs\Python\Python312\python.exe" po_emailer.py

pause
