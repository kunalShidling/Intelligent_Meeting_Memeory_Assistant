@echo off
REM Backend Server Startup Script for Windows

echo ================================
echo Meeting Assistant - Backend API
echo ================================
echo.

REM Check if virtual environment exists
if not exist "..\.venv\" (
    echo Error: Virtual environment not found!
    echo Please run setup from the project root first.
    exit /b 1
)

echo Activating virtual environment...
call ..\.venv\Scripts\activate.bat

REM Install backend-specific requirements
echo Installing backend dependencies...
pip install -q Flask Flask-CORS Flask-SocketIO python-socketio python-engineio

echo.
echo Starting Flask API server...
echo API will be available at: http://localhost:5000
echo Health check: http://localhost:5000/api/health
echo.
echo Press Ctrl+C to stop the server
echo ================================
echo.

REM Set Python path to include parent directories
set PYTHONPATH=%CD%\..;%CD%\..\opencv;%CD%\..\audio_to_text

REM Start the server
python app.py
