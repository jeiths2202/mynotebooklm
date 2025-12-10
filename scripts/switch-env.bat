@echo off
REM Environment Switching Script for Windows
REM Usage: scripts\switch-env.bat [dev|prod]

set SCRIPT_DIR=%~dp0
set BACKEND_DIR=%SCRIPT_DIR%..\backend

if "%1"=="dev" goto dev
if "%1"=="development" goto dev
if "%1"=="prod" goto prod
if "%1"=="production" goto prod
if "%1"=="status" goto status
goto usage

:dev
copy /Y "%BACKEND_DIR%\.env.development" "%BACKEND_DIR%\.env" > nul
echo.
echo [OK] Switched to DEVELOPMENT environment
echo.
echo Configuration:
echo   - LLM API: http://localhost:8001 (Mock)
echo   - Embedding API: http://localhost:8001 (Mock)
echo.
echo To start:
echo   1. Start mock server: cd backend ^&^& python -m uvicorn mock_server.main:app --port 8001 --reload
echo   2. Start backend:     cd backend ^&^& python -m uvicorn app.main:app --port 8000 --reload
echo   3. Start frontend:    cd frontend ^&^& npm run dev
goto end

:prod
copy /Y "%BACKEND_DIR%\.env.production" "%BACKEND_DIR%\.env" > nul
echo.
echo [OK] Switched to PRODUCTION environment
echo.
echo Configuration:
echo   - LLM API: http://192.168.8.11:12800 (GPU Server)
echo   - Embedding API: http://192.168.8.11:12800 (GPU Server)
echo.
echo To start:
echo   1. Start backend:  cd backend ^&^& python -m uvicorn app.main:app --port 8000 --reload
echo   2. Start frontend: cd frontend ^&^& npm run dev
goto end

:status
if exist "%BACKEND_DIR%\.env" (
    echo Current environment configuration:
    findstr /B "ENVIRONMENT=" "%BACKEND_DIR%\.env"
    findstr /B "USE_MOCK_SERVICES=" "%BACKEND_DIR%\.env"
) else (
    echo No .env file found. Run 'scripts\switch-env.bat dev' or 'scripts\switch-env.bat prod' first.
)
goto end

:usage
echo Usage: %0 [dev^|prod^|status]
echo.
echo Commands:
echo   dev, development  - Switch to development mode (uses mock services)
echo   prod, production  - Switch to production mode (uses GPU server)
echo   status            - Show current environment
echo.
echo Examples:
echo   %0 dev     - Use mock services for testing
echo   %0 prod    - Use real GPU server
echo   %0 status  - Check current environment
exit /b 1

:end
