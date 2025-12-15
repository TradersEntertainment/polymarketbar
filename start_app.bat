@echo off
echo Starting Backend...
start "Backend" cmd /k "uvicorn backend.main:app --reload"

echo Starting Frontend...
start "Frontend" cmd /k "cd frontend && npm run dev"

echo Application started!
