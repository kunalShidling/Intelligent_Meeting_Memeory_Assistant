@echo off
REM Full Application Startup Script for Windows
REM Starts both backend and frontend servers

echo ========================================
echo    Meeting Assistant - Full Stack App
echo ========================================
echo.

REM Check if .env file exists
if not exist ".env" (
    echo Warning: .env file not found!
    echo Creating .env file...
    echo GROQ_API_KEY=your_api_key_here > .env
    echo.
    echo Please edit .env and add your Groq API key
    echo Get your API key from: https://console.groq.com/keys
    echo.
    pause
)

echo.
echo Starting servers...
echo ========================================
echo.

REM Set Python path for imports
set PYTHONPATH=%CD%;%CD%\opencv;%CD%\audio_to_text

REM Start backend in new window
echo Starting Backend API (Flask)...
start "Meeting Assistant - Backend" cmd /k "set PYTHONPATH=%CD%;%CD%\opencv;%CD%\audio_to_text && cd backend && start.bat"

REM Poll the health endpoint until the backend is actually ready (max 120s)
echo Waiting for backend to become ready...
set MAX_WAIT=40
set WAITED=0

:WAIT_LOOP
timeout /t 3 /nobreak > nul
set /a WAITED=%WAITED%+1

powershell -NoProfile -Command "try { $null = Invoke-WebRequest -Uri 'http://127.0.0.1:5000/api/health' -UseBasicParsing -TimeoutSec 2; exit 0 } catch { exit 1 }"

if %ERRORLEVEL% EQU 0 (
    echo Backend is ready!
    goto BACKEND_READY
)

if %WAITED% LSS %MAX_WAIT% (
    set /a SECS=%WAITED%*3
    echo   Still waiting... (%SECS%s elapsed^)
    goto WAIT_LOOP
)

echo WARNING: Backend did not respond within 120 seconds.
echo Starting frontend anyway - it will retry automatically.

:BACKEND_READY
echo.
echo Starting Frontend (React)...
start "Meeting Assistant - Frontend" cmd /k "cd frontend && start.bat"

echo.
echo ========================================
echo    Application Started Successfully!
echo ========================================
echo.
echo Backend API:  http://localhost:5000
echo Frontend App: http://localhost:3000
echo.
echo Close the terminal windows to stop the servers
echo ========================================
echo.

pause
