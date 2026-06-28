@echo off
setlocal EnableExtensions
title Job Search Pipeline Launcher

set "ROOT=%~dp0"
cd /d "%ROOT%"

echo.
echo ============================================================
echo   Job Search - Local Pipeline (single click start)
echo ============================================================
echo.
echo   Window 1  Project 1  Scrape NEW job URLs from career pages
echo             (runs company-by-company, 24/7 scheduler)
echo.
echo   Window 2  Project 2  Scrape FULL job details from queue
echo             (picks up new jobs automatically as they arrive)
echo.
echo   Window 3  Admin dashboard  http://localhost:8090
echo             (click jobs to see status / details / metrics)
echo.
echo ============================================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH.
    pause
    exit /b 1
)

REM --- Project 1: career page scraper (scheduler) ---
start "Project 1 - Scrape New Jobs" cmd /k ^
  "cd /d "%ROOT%1_scrape_job_careers_pages" && ^
   call conda activate job_search && ^
   echo. && echo [Project 1] Scheduler started - scraping companies one by one... && echo. && ^
   python scheduler.py"

timeout /t 2 /nobreak >nul

REM --- Project 2: job details pipeline workers (parallel) ---
start "Project 2 - Job Details Pipeline" cmd /k ^
  "cd /d "%ROOT%" && ^
   call conda activate job_search 2>nul && ^
   echo. && echo [Project 2] Listening for new jobs in queue... && echo. && ^
   python pipeline\run_workers.py --workers details"

timeout /t 1 /nobreak >nul

REM --- Admin monitoring dashboard ---
start "Pipeline Admin - Port 8090" cmd /k ^
  "cd /d "%ROOT%" && ^
   call conda activate job_search 2>nul && ^
   echo. && echo [Admin] Dashboard: http://localhost:8090 && echo. && ^
   python pipeline\admin\app.py"

echo.
echo All services started in separate windows.
echo.
echo   Dashboard:  http://localhost:8090
echo   Demo test:  python pipeline\run_demo.py  (3 Cognizant + 2 HCL jobs)
echo.
echo Close each window to stop that service.
echo.
pause
