@echo off
REM Quick Start Script for Development Mode (Windows)
REM Starts mock server, backend, and frontend

echo ============================================
echo   NotebookLM Clone - Development Mode
echo ============================================
echo.

REM Switch to development environment
call %~dp0switch-env.bat dev

echo.
echo Starting services...
echo.

REM Start mock server in new window
start "Mock Server (Port 8001)" cmd /k "cd /d %~dp0..\backend && python -m uvicorn mock_server.main:app --port 8001 --reload"

REM Wait a moment for mock server to start
timeout /t 2 /nobreak > nul

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
echo   Mock Server: http://localhost:8001
echo   Backend API: http://localhost:8000
echo   Frontend:    http://localhost:5173
echo.
echo   Press any key to exit this window...
pause > nul
