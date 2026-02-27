#!/bin/bash
# Quick-start script for local development

set -e

echo "=================================================="
echo "  Two-Wheeler Sales Intelligence App"
echo "=================================================="

# Backend
echo ""
echo "[1/3] Setting up Python backend..."
cd backend
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt
echo "✓ Backend dependencies installed"

echo ""
echo "[2/3] Starting backend server (http://localhost:8000)..."
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo "✓ Backend started (PID: $BACKEND_PID)"

# Frontend
cd ../frontend
echo ""
echo "[3/3] Setting up and starting frontend (http://localhost:3000)..."
npm install --silent
npm run dev &
FRONTEND_PID=$!
echo "✓ Frontend started (PID: $FRONTEND_PID)"

echo ""
echo "=================================================="
echo "  App is running!"
echo "  Frontend: http://localhost:3000"
echo "  Backend:  http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo "=================================================="
echo "Press Ctrl+C to stop"

wait
