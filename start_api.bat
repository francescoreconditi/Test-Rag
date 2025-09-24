@echo off
echo Starting FastAPI application...
cd /d C:\Progetti\RAG
call .venv\Scripts\activate
python -m uvicorn api:app --host 127.0.0.1 --port 8000
pause