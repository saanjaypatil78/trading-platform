#!/bin/bash
# Trading Platform - GitHub Codespaces / Gitpod One-Click Setup
# This script sets up and runs the entire trading platform

set -e

echo "=============================================="
echo "   Trading Platform - Auto Setup"
echo "=============================================="

# Install Python dependencies
echo "[1/4] Installing Python dependencies..."
pip install fastapi uvicorn pydantic httpx aiohttp --quiet

# Create __init__.py files if missing
echo "[2/4] Setting up Python packages..."
find backend -type d -exec touch {}/__init__.py \; 2>/dev/null || true

# Start backend services in background
echo "[3/4] Starting backend services..."

# Brain Service (Port 8007)
python -c "
import sys
sys.path.insert(0, '.')
from backend.services.brain.main import app
import uvicorn
uvicorn.run(app, host='0.0.0.0', port=8007, log_level='warning')
" &
BRAIN_PID=$!
echo "  - Brain Service started (PID: $BRAIN_PID)"
sleep 2

# Scanner Service (Port 8008)
python -c "
import sys
sys.path.insert(0, '.')
from backend.services.scanner.main import app
import uvicorn
uvicorn.run(app, host='0.0.0.0', port=8008, log_level='warning')
" &
SCANNER_PID=$!
echo "  - Scanner Service started (PID: $SCANNER_PID)"
sleep 2

# Orders Service (Port 8009)
python -c "
import sys
sys.path.insert(0, '.')
from backend.services.broker.main import app
import uvicorn
uvicorn.run(app, host='0.0.0.0', port=8009, log_level='warning')
" &
ORDERS_PID=$!
echo "  - Orders Service started (PID: $ORDERS_PID)"
sleep 2

# Start static file server for frontend
echo "[4/4] Starting frontend server..."
cd frontend/static
python -m http.server 8000 &
FRONTEND_PID=$!
cd ../..
echo "  - Frontend Server started (PID: $FRONTEND_PID)"

echo ""
echo "=============================================="
echo "   ALL SERVICES RUNNING!"
echo "=============================================="
echo ""
echo "Services:"
echo "  - Frontend:      http://localhost:8000"
echo "  - Brain API:     http://localhost:8007"
echo "  - Scanner API:   http://localhost:8008"
echo "  - Orders API:    http://localhost:8009"
echo ""
echo "API Docs:"
echo "  - Brain:    http://localhost:8007/docs"
echo "  - Scanner:  http://localhost:8008/docs"
echo "  - Orders:   http://localhost:8009/docs"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for user interrupt
wait

# Cleanup on exit
trap "kill $BRAIN_PID $SCANNER_PID $ORDERS_PID $FRONTEND_PID 2>/dev/null" EXIT
