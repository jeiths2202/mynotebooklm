@echo off
REM Quick Start Script for Production Mode (Windows)
REM Starts backend and frontend (uses real GPU server)

echo ============================================
echo   NotebookLM Clone - Production Mode
echo ============================================
echo.

REM Switch to production environment
call %~dp0switch-env.bat prod

echo.
echo Starting services...
echo.

REM Start backend in new window
start "Backend (Port 8000)" cmd /k "cd /d %~dp0..\backend && python -m uvicorn app.main:app --port 8000 --reload"

REM Wait a moment for backend to start
timeout /t 2 /nobreak > nul

REM Start frontend in new window
start "Frontend (Port 5173)" cmd /k "cd /d %~dp0..\frontend && npm run dev"

echo.
echo ============================================
echo   All services starting...
echo ============================================
echo.
echo   GPU Server:  http://192.168.8.11:12800
echo   Backend API: http://localhost:8000
echo   Frontend:    http://localhost:5173
echo.
echo   Press any key to exit this window...
pause > nul
