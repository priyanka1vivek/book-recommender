@echo off
echo.
echo =========================================================
echo   BOOK RECOMMENDER - FIRST-TIME SETUP
echo =========================================================
echo.

cd /d "%~dp0backend"

echo [1/3] Creating Python virtual environment...
python -m venv .venv
call .venv\Scripts\activate.bat

echo.
echo [2/3] Installing Python dependencies (this may take a few minutes)...
pip install -r requirements.txt

echo.
echo [3/3] Seeding the database and building the AI vector index...
echo       (The embedding model downloads ~90MB on first run - please wait)
python seed.py

echo.
echo =========================================================
echo   Setup complete! Run start_server.bat to launch.
echo =========================================================
pause
