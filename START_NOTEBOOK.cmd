@echo off
cd /d "%~dp0"
py -3.12 --version >nul 2>&1
if errorlevel 1 (
 python run_quality.py --notebook
) else (
 py -3.12 run_quality.py --notebook
)
pause
