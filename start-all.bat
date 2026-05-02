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

REM Wait a moment for backend to start
timeout /t 3 /nobreak > nul

REM Start frontend in new window
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
