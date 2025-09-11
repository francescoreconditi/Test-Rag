@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion

echo Starting Performance Optimization Deployment...

:: Function to check if command exists
set "check_commands=docker python"

echo [INFO] Checking prerequisites...

for %%c in (%check_commands%) do (
    where %%c >nul 2>&1
    if !errorlevel! neq 0 (
        echo [ERROR] %%c is required but not installed
        pause
        exit /b 1
    ) else (
        echo [SUCCESS] %%c found
    )
)

:: Check Docker Compose
where docker-compose >nul 2>&1
if !errorlevel! neq 0 (
    echo [WARNING] docker-compose not found, trying docker compose
    docker compose version >nul 2>&1
    if !errorlevel! neq 0 (
        echo [ERROR] Docker Compose is required but not installed
        pause
        exit /b 1
    )
    set DOCKER_COMPOSE=docker compose
) else (
    set DOCKER_COMPOSE=docker-compose
    echo [SUCCESS] docker-compose found
)

echo [SUCCESS] All prerequisites check passed

:: Install performance dependencies
echo [INFO] Installing performance dependencies...

:: Check if virtual environment exists
if not exist ".venv" (
    echo [INFO] Creating virtual environment...
    python -m venv .venv
)

:: Activate virtual environment
if exist ".venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment...
    call .venv\Scripts\activate.bat
) else (
    echo [ERROR] Cannot find virtual environment activation script
    pause
    exit /b 1
)

:: Install basic dependencies
echo [INFO] Installing Redis, Celery, and Flower...
pip install redis celery flower requests eventlet

echo [SUCCESS] Dependencies installation complete

:: Setup Redis
echo [INFO] Setting up Redis...

:: Check if Redis container exists and is running
docker ps --format "table {{.Names}}" 2>nul | findstr /C:"rag_redis" >nul
if !errorlevel! equ 0 (
    echo [WARNING] Redis container already running
    goto :redis_ready
)

:: Check if container exists but stopped
docker ps -a --format "table {{.Names}}" 2>nul | findstr /C:"rag_redis" >nul
if !errorlevel! equ 0 (
    echo [INFO] Starting existing Redis container...
    docker start rag_redis
) else (
    echo [INFO] Creating new Redis container...
    docker run -d --name rag_redis -p 6379:6379 redis:7-alpine
)

:: Wait for Redis to be ready
echo [INFO] Waiting for Redis to be ready...
set /a timeout=30
set /a counter=0

:redis_loop
timeout /t 1 >nul 2>&1
docker exec rag_redis redis-cli ping >nul 2>&1
if !errorlevel! equ 0 goto :redis_ready

set /a counter+=1
if !counter! geq !timeout! (
    echo [ERROR] Redis failed to start within !timeout! seconds
    pause
    exit /b 1
)

goto :redis_loop

:redis_ready
echo [SUCCESS] Redis is ready and running

:: Setup Qdrant
echo [INFO] Setting up Qdrant...

:: Check if Qdrant container exists and is running
docker ps --format "table {{.Names}}" 2>nul | findstr /C:"rag_qdrant" >nul
if !errorlevel! equ 0 (
    echo [WARNING] Qdrant container already running
    goto :qdrant_ready
)

:: Stop and remove any conflicting containers
docker stop bi_rag_qdrant >nul 2>&1
docker rm bi_rag_qdrant >nul 2>&1

:: Check if container exists but stopped
docker ps -a --format "table {{.Names}}" 2>nul | findstr /C:"rag_qdrant" >nul
if !errorlevel! equ 0 (
    echo [INFO] Starting existing Qdrant container...
    docker start rag_qdrant
) else (
    echo [INFO] Creating new Qdrant container...
    docker run -d --name rag_qdrant -p 6333:6333 qdrant/qdrant
)

:: Wait for Qdrant to be ready
echo [INFO] Waiting for Qdrant to be ready...
set /a timeout=60
set /a counter=0

:qdrant_loop
timeout /t 2 >nul 2>&1
curl -s http://localhost:6333/ | findstr "qdrant" >nul 2>&1
if !errorlevel! equ 0 goto :qdrant_ready

set /a counter+=2
if !counter! geq !timeout! (
    echo [ERROR] Qdrant failed to start within !timeout! seconds
    echo [INFO] Check Qdrant logs: docker logs rag_qdrant
    pause
    exit /b 1
)

goto :qdrant_loop

:qdrant_ready
echo [SUCCESS] Qdrant is ready and running

:: Test connections
echo [INFO] Testing connections...

:: Test Redis
docker exec rag_redis redis-cli ping >nul 2>&1
if !errorlevel! equ 0 (
    echo [SUCCESS] Redis connection test passed
) else (
    echo [ERROR] Redis connection test failed
)

:: Test Qdrant
curl -s http://localhost:6333/ | findstr "qdrant" >nul 2>&1
if !errorlevel! equ 0 (
    echo [SUCCESS] Qdrant connection test passed
) else (
    echo [ERROR] Qdrant connection test failed
)

:: Create monitoring info
echo [INFO] Creating monitoring information...

(
echo Monitoring Endpoints:
echo.
echo Application:
echo    - Main App: http://localhost:8502
echo    - Qdrant API: http://localhost:6333
echo.
echo Services:
echo    - Redis: localhost:6379
echo    - Qdrant: localhost:6333
echo.
echo Management Commands:
echo    - Redis CLI: docker exec -it rag_redis redis-cli
echo    - Redis logs: docker logs rag_redis
echo    - Qdrant logs: docker logs rag_qdrant
echo    - Stop services: docker stop rag_redis rag_qdrant
echo    - Start services: docker start rag_redis rag_qdrant
echo.
echo Performance Features:
echo    - Connection pooling: Available
echo    - Distributed caching: Redis ready
echo    - Background jobs: Celery installed
echo    - Vector database: Qdrant ready
echo.
echo Next Steps:
echo    1. Test Redis: docker exec -it rag_redis redis-cli ping
echo    2. Test Qdrant: curl http://localhost:6333/
echo    3. Start Celery: celery -A src.infrastructure.performance.celery_tasks worker --loglevel=info --pool=solo
echo    4. Start Flower: python -m celery -A src.infrastructure.performance.celery_tasks flower --port=5555
) > monitoring_endpoints.txt

echo [SUCCESS] Monitoring info created in monitoring_endpoints.txt

:: Final summary
echo.
echo ============================================================
echo Performance optimization deployment complete!
echo ============================================================
echo.
echo Services Status:
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | findstr "rag_"
echo.
echo View monitoring info: type monitoring_endpoints.txt
echo.
echo Ready to use enhanced performance features!
echo Press any key to continue...
pause >nul

exit /b 0