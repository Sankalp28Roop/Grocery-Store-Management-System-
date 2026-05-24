#!/bin/bash
# FreshMart Grocery Store Management System — Dev Server Launcher

set -e

# Get the absolute project root directory
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# Trap SIGINT (Ctrl+C) and SIGTERM signals to terminate background servers cleanly
trap cleanup SIGINT SIGTERM

cleanup() {
  echo ""
  echo "🛑 Stopping FreshMart full-stack server processes..."
  if [ -n "$BACKEND_PID" ]; then
    echo "Stopping backend (PID: $BACKEND_PID)..."
    kill $BACKEND_PID 2>/dev/null || true
  fi
  if [ -n "$FRONTEND_PID" ]; then
    echo "Stopping frontend server (PID: $FRONTEND_PID)..."
    kill $FRONTEND_PID 2>/dev/null || true
  fi
  echo "✨ All background processes terminated cleanly. Goodbye!"
  exit 0
}

# 1. Activate virtual environment and launch backend FastAPI server on port 8000
echo "🚀 Starting FreshMart Backend Server on port 8000..."
if [ ! -d ".venv" ]; then
  echo "⚠️  Virtual environment not found! Please run ./start.sh first."
  exit 1
fi

# Start uvicorn in the background
.venv/bin/uvicorn backend.main:app --reload --port 8000 &
BACKEND_PID=$!
echo "Backend running under PID: $BACKEND_PID"

# 2. Host the frontend assets on port 8080
echo "🌐 Hosting Frontend assets on port 8080..."
cd frontend
python -m http.server 8080 &
FRONTEND_PID=$!
echo "Frontend server running under PID: $FRONTEND_PID"

# 3. Delay safety check and open the browser
echo "⏳ Waiting for servers to initialize..."
sleep 3

echo "✨ Opening http://127.0.0.1:8080 in your default browser..."
open http://127.0.0.1:8080

# Keep the shell script alive to trap SIGINT
echo "💡 Press Ctrl+C to terminate both servers safely."
while true; do
  sleep 1
done
