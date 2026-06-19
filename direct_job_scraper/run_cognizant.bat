@echo off
setlocal

cd /d "%~dp0"

call conda activate job_search
if errorlevel 1 (
    echo Failed to activate conda environment: job_search
    pause
    exit /b 1
)

python main.py --company cognizant
set EXITCODE=%errorlevel%

pause
exit /b %EXITCODE%
