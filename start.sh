#!/bin/bash
# FreshMart Grocery Store Management System — Dev Server Launcher
# Requires Python 3.10-3.12 (not 3.14+)

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# Create virtual environment if not exists
if [ ! -d ".venv" ]; then
  echo "🔧 Creating virtual environment with Python 3.10..."
  /opt/homebrew/bin/python3.10 -m venv .venv
fi

# Install dependencies
echo "📦 Installing dependencies..."
.venv/bin/pip install -r backend/requirements.txt -q

# Start the server
echo ""
echo "✅ Starting FreshMart backend server..."
echo "🌐 App:    http://localhost:8000"
echo "📖 Docs:   http://localhost:8000/docs"
echo "🗄️  ReDoc:  http://localhost:8000/redoc"
echo ""
.venv/bin/uvicorn backend.main:app --reload --port 8000
