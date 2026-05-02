@echo off
REM Frontend Startup Script for Windows

echo ====================================
echo Meeting Assistant - Frontend (React)
echo ====================================
echo.

REM Check if node_modules exists
if not exist "node_modules\" (
    echo Installing dependencies...
    npm install
    echo.
)

echo Starting React development server...
echo Frontend will be available at: http://localhost:3000
echo.
echo Press Ctrl+C to stop the server
echo ====================================
echo.

REM Start the development server
npm run dev
