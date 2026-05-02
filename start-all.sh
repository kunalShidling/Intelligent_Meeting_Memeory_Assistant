#!/bin/bash
# Full Application Startup Script
# Starts both backend and frontend servers

echo "========================================"
echo "   Meeting Assistant - Full Stack App"
echo "========================================"
echo ""

# Check if MongoDB is running
echo "Checking MongoDB..."
if ! pgrep -x "mongod" > /dev/null; then
    echo "⚠ MongoDB is not running!"
    echo "Please start MongoDB first:"
    echo "  - Windows: Start MongoDB service"
    echo "  - Linux/Mac: sudo systemctl start mongod"
    echo ""
    read -p "Continue anyway? (y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠ .env file not found!"
    echo "Creating .env file..."
    echo "GROQ_API_KEY=your_api_key_here" > .env
    echo ""
    echo "Please edit .env and add your Groq API key"
    echo "Get your API key from: https://console.groq.com/keys"
    echo ""
    read -p "Press Enter when ready..."
fi

echo ""
echo "Starting servers..."
echo "========================================"
echo ""

# Start backend in background
echo "Starting Backend API (Flask)..."
cd backend
./start.sh &
BACKEND_PID=$!
cd ..

# Wait a moment for backend to start
sleep 3

# Start frontend in background
echo ""
echo "Starting Frontend (React)..."
cd frontend
./start.sh &
FRONTEND_PID=$!
cd ..

echo ""
echo "========================================"
echo "   Application Started Successfully!"
echo "========================================"
echo ""
echo "Backend API:  http://localhost:5000"
echo "Frontend App: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop both servers"
echo "========================================"
echo ""

# Wait for Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
