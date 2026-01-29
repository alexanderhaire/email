@echo off
echo ===================================================
echo   GP Emailer Clean Cleanup Tool
echo ===================================================

echo.
echo 1. Stopping Windows Services...
nssm stop GPEmailDashboard
nssm stop GPInvoiceEmailer
nssm stop GPPoEmailer

echo.
echo 2. Disabling Windows Services (Prevent Start on Reboot)...
sc config GPEmailDashboard start= disabled
sc config GPInvoiceEmailer start= disabled
sc config GPPoEmailer start= disabled

echo.
echo 3. Killing any remaining Python processes...
taskkill /F /IM python.exe

echo.
echo ===================================================
echo   Cleanup Complete.
echo   You can now run start_system.bat safely.
echo ===================================================
pause
