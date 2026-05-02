@echo off
REM Setup Script - Run Once from Root Folder
REM This installs all dependencies and prepares the application

echo ========================================
echo    Meeting Assistant - Setup Script
echo ========================================
echo.

REM Check if virtual environment exists
if not exist ".venv\" (
    echo Error: Virtual environment not found!
    echo Please create it first: python -m venv .venv
    pause
    exit /b 1
)

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo.
echo ========================================
echo Installing Frontend Dependencies...
echo ========================================
cd frontend
npm install
if errorlevel 1 (
    echo Error installing frontend dependencies!
    pause
    exit /b 1
)
cd ..

echo.
echo ========================================
echo Installing Backend Dependencies...
echo ========================================
pip install Flask Flask-CORS Flask-SocketIO python-socketio python-engineio
if errorlevel 1 (
    echo Error installing backend dependencies!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Setting up Python path...
echo ========================================
REM This adds opencv and audio_to_text to Python path
set PYTHONPATH=%CD%;%CD%\opencv;%CD%\audio_to_text

echo.
echo ========================================
echo    Setup Complete!
echo ========================================
echo.
echo You can now run the application with:
echo    .\start-all.bat
echo.
echo Or manually:
echo    Backend: cd backend ^& .\start.bat
echo    Frontend: cd frontend ^& .\start.bat
echo.
pause
