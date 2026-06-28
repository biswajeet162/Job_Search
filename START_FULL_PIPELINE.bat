@echo off
setlocal EnableExtensions
title Job Search FULL Pipeline Launcher

set "ROOT=%~dp0"
cd /d "%ROOT%"

echo.
echo ============================================================
echo   Job Search - FULL Pipeline (projects 1 + 2 + 3)
echo ============================================================
echo.
echo   Window 1  Project 1   Scrape NEW job URLs
echo   Window 2  Projects 2+3  Details + LLM metrics (Ollama)
echo   Window 3  Admin dashboard  http://localhost:8090
echo.
echo   Requires: Ollama running with llama3.1:8b
echo ============================================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH.
    pause
    exit /b 1
)

start "Project 1 - Scrape New Jobs" cmd /k ^
  "cd /d "%ROOT%1_scrape_job_careers_pages" && ^
   call conda activate job_search && ^
   echo [Project 1] Scheduler started... && ^
   python scheduler.py"

timeout /t 2 /nobreak >nul

start "Pipeline - Details + Metrics" cmd /k ^
  "cd /d "%ROOT%" && ^
   call conda activate job_search 2>nul && ^
   echo [Pipeline] details + metrics workers (parallel)... && ^
   python pipeline\run_workers.py --workers details metrics"

timeout /t 1 /nobreak >nul

start "Pipeline Admin - Port 8090" cmd /k ^
  "cd /d "%ROOT%" && ^
   call conda activate job_search 2>nul && ^
   echo [Admin] http://localhost:8090 && ^
   python pipeline\admin\app.py"

echo.
echo All services started. Dashboard: http://localhost:8090
echo.
pause
