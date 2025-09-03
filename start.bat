@echo off
echo Starting Business Intelligence RAG System...
echo.

REM Check if .env exists
if not exist .env (
    echo ERROR: .env file not found!
    echo Please copy .env.example to .env and configure your settings.
    pause
    exit /b 1
)

REM Check if Docker is running
docker version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not running!
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)

echo Starting Qdrant vector database...
docker-compose up -d qdrant

REM Wait for Qdrant to be ready
echo Waiting for Qdrant to initialize...
timeout /t 5 /nobreak >nul

REM Install uv if not present
where uv >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing uv...
    powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install uv. Please install manually: https://docs.astral.sh/uv/getting-started/installation/
        pause
        exit /b 1
    )
    echo uv installed successfully. Please restart this script.
    pause
    exit /b 0
)

REM Check if virtual environment exists
if not exist .venv (
    echo Creating virtual environment with uv...
    uv venv
    echo Installing dependencies with uv...
    uv pip install -r requirements.txt
)

REM Activate virtual environment
call .venv\Scripts\activate

echo.
echo Starting Streamlit application...
echo.
echo The application will open in your browser at http://localhost:8501
echo Press Ctrl+C to stop the application
echo.

streamlit run app.py