@echo off
echo ============================================
echo   GP Invoice Emailer - Service Installer
echo ============================================
echo.
echo This will install the GP Invoice Emailer as a Windows Service.
echo You may need to run this as Administrator.
echo.

:: Refresh PATH to pick up nssm
set "PATH=%PATH%;C:\Program Files\NSSM"

:: Install the service
nssm install GPInvoiceEmailer "C:\Users\alexh\AppData\Local\Programs\Python\Python312\python.exe" "c:\Users\alexh\email\invoice_emailer.py"

:: Set the working directory
nssm set GPInvoiceEmailer AppDirectory "c:\Users\alexh\email"

:: Set to auto-start
nssm set GPInvoiceEmailer Start SERVICE_AUTO_START

:: Set restart on failure
nssm set GPInvoiceEmailer AppExit Default Restart
nssm set GPInvoiceEmailer AppRestartDelay 10000

echo.
echo Service installed! Starting now...
nssm start GPInvoiceEmailer

echo.
echo ============================================
echo   Done! Service is now running.
echo ============================================
pause
