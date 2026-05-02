#!/bin/bash
# Frontend Startup Script

echo "===================================="
echo "Meeting Assistant - Frontend (React)"
echo "===================================="
echo ""

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
    echo ""
fi

echo "Starting React development server..."
echo "Frontend will be available at: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop the server"
echo "===================================="
echo ""

# Start the development server
npm run dev
