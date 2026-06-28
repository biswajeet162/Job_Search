@echo off
cd /d "%~dp0\.."
echo Starting pipeline workers...
start "Pipeline Workers" cmd /k python pipeline\run_workers.py %*
echo Starting admin dashboard on http://localhost:8090 ...
start "Pipeline Admin" cmd /k python pipeline\admin\app.py
echo Done. Two windows opened.
