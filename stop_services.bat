@echo off
echo Stopping conflicting background services...
echo.
echo Asking for Administrator privileges...
nssm stop GPEmailDashboard
nssm stop GPInvoiceEmailer
nssm stop GPPoEmailer
echo.
echo Services stopped. Now your manual script should work (you may need to close and reopen it).
pause
