@echo off
echo ============================================
echo   GP Email Automation - Service Installer
echo ============================================
echo.
echo This will install the following services:
echo 1. GPInvoiceEmailer (Invoices)
echo 2. GPPoEmailer (Purchase Orders)
echo 3. GPEmailDashboard (Web Interface)
echo.
echo IMPORTANT: Run as Administrator.
echo.

:: Refresh PATH to pick up nssm
set "PATH=%PATH%;C:\Program Files\NSSM\win64;C:\Program Files\NSSM"

:: Base Directory
set "BASE_DIR=c:\Users\alexh\email"
set "PYTHON_EXE=C:\Users\alexh\AppData\Local\Programs\Python\Python312\python.exe"

:: Create logs directory
if not exist "%BASE_DIR%\logs" mkdir "%BASE_DIR%\logs"

echo --------------------------------------------
echo Installing GPInvoiceEmailer...
nssm stop GPInvoiceEmailer >nul 2>&1
nssm remove GPInvoiceEmailer confirm >nul 2>&1
nssm install GPInvoiceEmailer "%PYTHON_EXE%" "%BASE_DIR%\invoice_emailer.py"
nssm set GPInvoiceEmailer AppDirectory "%BASE_DIR%"
nssm set GPInvoiceEmailer Start SERVICE_AUTO_START
nssm set GPInvoiceEmailer AppExit Default Restart
nssm set GPInvoiceEmailer AppRestartDelay 10000
nssm set GPInvoiceEmailer AppStdout "%BASE_DIR%\logs\invoice_service.log"
nssm set GPInvoiceEmailer AppStderr "%BASE_DIR%\logs\invoice_service_error.log"
nssm start GPInvoiceEmailer
echo Done.

echo --------------------------------------------
echo Installing GPPoEmailer...
nssm stop GPPoEmailer >nul 2>&1
nssm remove GPPoEmailer confirm >nul 2>&1
nssm install GPPoEmailer "%PYTHON_EXE%" "%BASE_DIR%\po_emailer.py"
nssm set GPPoEmailer AppDirectory "%BASE_DIR%"
nssm set GPPoEmailer Start SERVICE_AUTO_START
nssm set GPPoEmailer AppExit Default Restart
nssm set GPPoEmailer AppRestartDelay 10000
nssm set GPPoEmailer AppStdout "%BASE_DIR%\logs\po_service.log"
nssm set GPPoEmailer AppStderr "%BASE_DIR%\logs\po_service_error.log"
nssm start GPPoEmailer
echo Done.

echo --------------------------------------------
echo Installing GPEmailDashboard...
nssm stop GPEmailDashboard >nul 2>&1
nssm remove GPEmailDashboard confirm >nul 2>&1
nssm install GPEmailDashboard "%PYTHON_EXE%" "%BASE_DIR%\email_manager_app.py"
nssm set GPEmailDashboard AppDirectory "%BASE_DIR%"
nssm set GPEmailDashboard Start SERVICE_AUTO_START
nssm set GPEmailDashboard AppExit Default Restart
nssm set GPEmailDashboard AppRestartDelay 10000
nssm set GPEmailDashboard AppStdout "%BASE_DIR%\logs\dashboard_service.log"
nssm set GPEmailDashboard AppStderr "%BASE_DIR%\logs\dashboard_service_error.log"
nssm start GPEmailDashboard
echo Done.

echo.
echo ============================================
echo   Done! All services are installed and running.
echo   Check logs in %BASE_DIR%\logs
echo ============================================
pause
