@echo off
echo Disabling conflicting Windows Services...
echo.
echo Asking for Administrator privileges...
sc config GPEmailDashboard start= disabled
sc config GPInvoiceEmailer start= disabled
sc config GPPoEmailer start= disabled
echo.
echo Services disabled. They will not start automatically on reboot.
echo Please run Launch_GP_Emailer.bat (or just log in) to start the system.
pause
