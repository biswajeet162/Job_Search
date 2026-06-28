@echo off
setlocal

cd /d "%~dp0"

if "%~1"=="" (
    echo Usage: run_company.bat ^<company^>
    echo Example: run_company.bat cognizant
    exit /b 1
)

call conda activate job_search
if errorlevel 1 (
    echo Failed to activate conda environment: job_search
    exit /b 1
)

python main.py --company %1
exit /b %errorlevel%
