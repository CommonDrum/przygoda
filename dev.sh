#!/bin/bash
# Start both backend and frontend dev servers
# Usage: ./dev.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Starting Przygoda dev servers..."
echo "  Backend:  http://localhost:8000"
echo "  Frontend: http://localhost:5173"
echo ""

# Start backend
cd "$SCRIPT_DIR/backend"
.venv/bin/uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

# Start frontend
cd "$SCRIPT_DIR/frontend"
~/.bun/bin/bun dev &
FRONTEND_PID=$!

# Cleanup on exit
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM

echo "Press Ctrl+C to stop both servers"
wait
