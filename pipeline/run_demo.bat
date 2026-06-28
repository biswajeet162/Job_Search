@echo off
cd /d "%~dp0\.."
echo === Demo: reset queue + 3 Cognizant + 2 HCLTech ===
python pipeline\run_demo.py %*
if "%1"=="" (
  echo.
  echo Start workers in another terminal:
  echo   python pipeline\run_workers.py --workers details metrics
  echo.
  echo Start dashboard:
  echo   python pipeline\admin\app.py
)
