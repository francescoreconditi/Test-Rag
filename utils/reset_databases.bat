@echo off
REM Database Reset Utility for Windows
REM Usage: reset_databases.bat [options]

setlocal EnableDelayedExpansion

echo.
echo ======================================================
echo   RAG System Database Reset Utility
echo ======================================================
echo.

cd /d "%~dp0\.."

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python or activate virtual environment.
    echo Try: .venv\Scripts\activate
    pause
    exit /b 1
)

REM Check if virtual environment exists
if exist ".venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
) else (
    echo Warning: Virtual environment not found at .venv\Scripts\activate.bat
    echo Continuing with system Python...
)

REM Run the database reset utility
echo Running database reset utility...
echo.

if "%1"=="" (
    REM No arguments, reset all with samples
    python utils\database_reset.py --all --samples
) else (
    REM Pass all arguments to Python script
    python utils\database_reset.py %*
)

echo.
if %ERRORLEVEL%==0 (
    echo ======================================================
    echo   Database reset completed successfully!
    echo ======================================================
    echo.
    echo Next steps:
    echo   1. Restart Streamlit if running
    echo   2. Check Qdrant: docker-compose up qdrant
    echo   3. Test with: streamlit run app.py
) else (
    echo ======================================================
    echo   Database reset failed. Check errors above.
    echo ======================================================
)

echo.
pause