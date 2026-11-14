@echo off
REM OMA one-click start (Windows). Needs Python 3.10+. Node.js only if the frontend isn't built yet.
cd /d "%~dp0"
python -m pip install -q -r backend\requirements.txt
if not exist frontend\dist\index.html (
  cd frontend && call npm install && call npm run build && cd ..
)
start "" http://localhost:8000
cd backend
python -m uvicorn app:app --host 0.0.0.0 --port 8000
