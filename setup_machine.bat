@echo off
echo ==========================================
echo   GP EMAIL MANAGER SETUP
echo ==========================================
echo.
echo This script will:
echo 1. Open Port 5000 in Windows Firewall (so others can access the web app)
echo 2. Add 'start_system.bat' to your Startup folder
echo.

:: Check for Admin privileges
net session >nul 2>&1
if %errorLevel% == 0 (
    echo [OK] Running as Administrator
) else (
    echo [ERROR] This script must be run as Administrator!
    echo Right-click this file and select "Run as administrator"
    pause
    exit /b
)

echo.
echo --- Step 1: Configuring Firewall ---
netsh advfirewall firewall delete rule name="GP Email Manager Web" >nul 2>&1
netsh advfirewall firewall add rule name="GP Email Manager Web" dir=in action=allow protocol=TCP localport=5000 enable=yes
echo Firewall rule added.

echo.
echo --- Step 2: Creating Startup Shortcut ---
powershell -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut('%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Start_GP_Emailer.lnk');$s.TargetPath='c:\Users\alexh\email\start_system.bat';$s.WorkingDirectory='c:\Users\alexh\email';$s.IconLocation='c:\Users\alexh\email\start_system.bat,0';$s.Save()"
echo Shortcut created in Startup folder.

echo.
echo ==========================================
echo   SETUP COMPLETE!
echo ==========================================
echo.
pause
