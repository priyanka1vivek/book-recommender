@echo off
echo.
echo =========================================================
echo   BOOK RECOMMENDER BACKEND
echo   API:  http://localhost:8000
echo   Docs: http://localhost:8000/docs
echo =========================================================
echo.

cd /d "%~dp0backend"
call .venv\Scripts\activate.bat
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
