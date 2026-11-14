#!/usr/bin/env sh
# OMA start (macOS/Linux). Needs Python 3.10+. Node.js only if the frontend isn't built yet.
cd "$(dirname "$0")"
python3 -m pip install -q -r backend/requirements.txt
[ -f frontend/dist/index.html ] || (cd frontend && npm install && npm run build)
cd backend && python3 -m uvicorn app:app --host 0.0.0.0 --port 8000
