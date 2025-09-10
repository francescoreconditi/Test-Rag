@echo off
echo Starting Flower monitoring dashboard...
set FLOWER_UNAUTHENTICATED_API=true
python -m celery -A src.infrastructure.performance.celery_tasks flower --port=5555 --unauthenticated_api