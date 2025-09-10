@echo off
echo Starting Flower monitoring dashboard...
set FLOWER_UNAUTHENTICATED_API=true

REM Start Celery worker
start celery -A src.infrastructure.performance.celery_tasks worker --loglevel=info --pool=solo

REM Start Flower dashboard
start python -m celery -A src.infrastructure.performance.celery_tasks flower --port=5555 --unauthenticated_api