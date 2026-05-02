#!/bin/bash
# Backend Server Startup Script

echo "================================"
echo "Meeting Assistant - Backend API"
echo "================================"
echo ""

# Check if virtual environment exists
if [ ! -d "../.venv" ]; then
    echo "Error: Virtual environment not found!"
    echo "Please run setup from the project root first."
    exit 1
fi

echo "Activating virtual environment..."
source ../.venv/Scripts/activate

# Install backend-specific requirements
echo "Installing backend dependencies..."
pip install -q Flask Flask-CORS Flask-SocketIO python-socketio python-engineio

# Check MongoDB connection
echo "Checking MongoDB connection..."
python -c "from pymongo import MongoClient; MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=2000).admin.command('ping'); print('✓ MongoDB connected')" 2>/dev/null || echo "⚠ MongoDB not running - some features will not work"

echo ""
echo "Starting Flask API server..."
echo "API will be available at: http://localhost:5000"
echo "Health check: http://localhost:5000/api/health"
echo ""
echo "Press Ctrl+C to stop the server"
echo "================================"
echo ""

# Start the server
python app.py
