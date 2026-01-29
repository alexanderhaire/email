@echo off
echo ===================================================
echo   GP Emailer COMPLETE REMOVAL Tool
echo ===================================================

echo.
echo 1. Removing Startup Shortcut...
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Start_GP_Emailer.lnk"
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Launch_GP_Emailer.bat"
if exist "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Start_GP_Emailer.lnk" (
    echo [ERROR] Failed to delete shortcut.
) else (
    echo [OK] Startup shortcut removed.
)

echo.
echo 2. Stopping Windows Services...
nssm stop GPEmailDashboard
nssm stop GPInvoiceEmailer
nssm stop GPPoEmailer

echo.
echo 3. Disabling Windows Services...
sc config GPEmailDashboard start= disabled
sc config GPInvoiceEmailer start= disabled
sc config GPPoEmailer start= disabled

echo.
echo 4. Killing remaining Python processes...
taskkill /F /IM python.exe

echo.
echo ===================================================
echo   System Cleaned. Use start_system.bat to run manually.
echo ===================================================
pause
