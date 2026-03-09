@echo off
TITLE Schedule Daily Production Report
cd %~dp0
echo Starting the Daily Production Report scheduler...
python.exe schedule_daily_report.py
pause
