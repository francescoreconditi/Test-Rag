#!/bin/bash

# =================================================================
# Performance Optimization Deployment Script
# Deploys all performance enhancements for the RAG system
# =================================================================

set -e  # Exit on error

echo "🚀 Starting Performance Optimization Deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Docker
    if ! command_exists docker; then
        print_error "Docker is required but not installed"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command_exists docker-compose; then
        print_warning "docker-compose not found, trying docker compose"
        if ! docker compose version >/dev/null 2>&1; then
            print_error "Docker Compose is required but not installed"
            exit 1
        fi
        DOCKER_COMPOSE="docker compose"
    else
        DOCKER_COMPOSE="docker-compose"
    fi
    
    # Check Python
    if ! command_exists python; then
        print_error "Python is required but not installed"
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Install performance dependencies
install_dependencies() {
    print_status "Installing performance dependencies..."
    
    # Create virtual environment if it doesn't exist
    if [ ! -d ".venv" ]; then
        python -m venv .venv
    fi
    
    # Activate virtual environment
    if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
    elif [ -f ".venv/Scripts/activate" ]; then
        source .venv/Scripts/activate
    else
        print_error "Cannot find virtual environment activation script"
        exit 1
    fi
    
    # Install dependencies
    pip install -r requirements.performance.txt
    
    print_success "Dependencies installed"
}

# Setup Redis
setup_redis() {
    print_status "Setting up Redis..."
    
    # Check if Redis is already running
    if docker ps --format "table {{.Names}}" | grep -q "rag_redis"; then
        print_warning "Redis container already running"
    else
        docker run -d \
            --name rag_redis \
            -p 6379:6379 \
            -v redis_data:/data \
            redis:7-alpine \
            redis-server --appendonly yes --maxmemory 2gb --maxmemory-policy allkeys-lru
    fi
    
    # Wait for Redis to be ready
    print_status "Waiting for Redis to be ready..."
    timeout=30
    counter=0
    while ! docker exec rag_redis redis-cli ping >/dev/null 2>&1; do
        if [ $counter -ge $timeout ]; then
            print_error "Redis failed to start within ${timeout} seconds"
            exit 1
        fi
        sleep 1
        counter=$((counter + 1))
    done
    
    print_success "Redis is ready"
}

# Setup Qdrant
setup_qdrant() {
    print_status "Setting up Qdrant..."
    
    if docker ps --format "table {{.Names}}" | grep -q "rag_qdrant"; then
        print_warning "Qdrant container already running"
    else
        docker run -d \
            --name rag_qdrant \
            -p 6333:6333 \
            -p 6334:6334 \
            -v qdrant_data:/qdrant/storage \
            qdrant/qdrant
    fi
    
    # Wait for Qdrant to be ready
    print_status "Waiting for Qdrant to be ready..."
    timeout=60
    counter=0
    while ! curl -f http://localhost:6333/health >/dev/null 2>&1; do
        if [ $counter -ge $timeout ]; then
            print_error "Qdrant failed to start within ${timeout} seconds"
            exit 1
        fi
        sleep 2
        counter=$((counter + 2))
    done
    
    print_success "Qdrant is ready"
}

# Start Celery workers
start_celery() {
    print_status "Starting Celery workers..."
    
    # Kill existing Celery processes
    pkill -f celery || true
    
    # Start Celery worker in background
    celery -A src.infrastructure.performance.celery_tasks worker \
        --loglevel=info \
        --concurrency=4 \
        --queues=default,indexing,analysis,training,export \
        --detach \
        --pidfile=celery_worker.pid \
        --logfile=logs/celery_worker.log
    
    # Start Celery beat scheduler in background
    celery -A src.infrastructure.performance.celery_tasks beat \
        --loglevel=info \
        --detach \
        --pidfile=celery_beat.pid \
        --logfile=logs/celery_beat.log
    
    # Start Flower monitoring
    celery -A src.infrastructure.performance.celery_tasks flower \
        --port=5555 \
        --detach \
        --pidfile=celery_flower.pid \
        --logfile=logs/celery_flower.log
    
    print_success "Celery services started"
}

# Deploy with Docker Compose
deploy_scaling() {
    print_status "Deploying scaling infrastructure..."
    
    # Create necessary directories
    mkdir -p logs nginx/ssl
    
    # Build and start services
    $DOCKER_COMPOSE -f docker-compose.scaling.yml build
    $DOCKER_COMPOSE -f docker-compose.scaling.yml up -d
    
    # Wait for services to be ready
    print_status "Waiting for services to be ready..."
    sleep 30
    
    # Check service health
    services=("nginx" "app1" "app2" "app3" "api1" "api2")
    for service in "${services[@]}"; do
        if docker ps --format "table {{.Names}}" | grep -q "rag_${service}"; then
            print_success "Service ${service} is running"
        else
            print_warning "Service ${service} may not be running properly"
        fi
    done
}

# Run performance tests
run_tests() {
    print_status "Running performance tests..."
    
    # Run unit tests
    python -m pytest tests/test_performance.py -v
    
    # Run basic load test
    # locust -f tests/load_test.py --host=http://localhost --users=10 --spawn-rate=2 --run-time=30s --headless
    
    print_success "Performance tests completed"
}

# Create monitoring dashboard
setup_monitoring() {
    print_status "Setting up monitoring..."
    
    # Create monitoring endpoints info
    cat > monitoring_endpoints.txt << EOF
🔍 Monitoring Endpoints:

📊 Application:
   - Main App: http://localhost
   - API: http://localhost/api
   - Health Check: http://localhost/health

📈 Monitoring:
   - Flower (Celery): http://localhost:5555
   - Nginx Status: http://localhost/nginx-status
   - Redis CLI: docker exec -it rag_redis redis-cli

🔧 Management:
   - View logs: docker-compose -f docker-compose.scaling.yml logs
   - Scale services: docker-compose -f docker-compose.scaling.yml up -d --scale app=5
   - Stop services: docker-compose -f docker-compose.scaling.yml down

💡 Performance Tips:
   - Monitor Redis hit rate: docker exec rag_redis redis-cli info stats
   - Check connection pool stats: curl http://localhost/api/stats/pool
   - View active Celery tasks: curl http://localhost:5555/api/tasks
EOF

    print_success "Monitoring setup complete"
}

# Cleanup function
cleanup() {
    print_status "Cleaning up on exit..."
    # Kill background processes if they exist
    [ -f celery_worker.pid ] && kill $(cat celery_worker.pid) 2>/dev/null || true
    [ -f celery_beat.pid ] && kill $(cat celery_beat.pid) 2>/dev/null || true
    [ -f celery_flower.pid ] && kill $(cat celery_flower.pid) 2>/dev/null || true
}

# Trap cleanup on exit
trap cleanup EXIT

# Main deployment flow
main() {
    echo "🔧 RAG System Performance Optimization Deployment"
    echo "=================================================="
    
    # Parse command line arguments
    MODE="full"  # Default mode
    while [[ $# -gt 0 ]]; do
        case $1 in
            --mode)
                MODE="$2"
                shift 2
                ;;
            --help)
                echo "Usage: $0 [--mode MODE]"
                echo "Modes: full, local, scaling, test"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Execute based on mode
    case $MODE in
        "full")
            check_prerequisites
            install_dependencies
            setup_redis
            setup_qdrant
            start_celery
            deploy_scaling
            run_tests
            setup_monitoring
            ;;
        "local")
            check_prerequisites
            install_dependencies
            setup_redis
            setup_qdrant
            start_celery
            setup_monitoring
            ;;
        "scaling")
            check_prerequisites
            deploy_scaling
            setup_monitoring
            ;;
        "test")
            run_tests
            ;;
        *)
            print_error "Invalid mode: $MODE"
            exit 1
            ;;
    esac
    
    print_success "🎉 Performance optimization deployment complete!"
    
    if [ -f monitoring_endpoints.txt ]; then
        echo ""
        cat monitoring_endpoints.txt
    fi
    
    echo ""
    echo "📝 Next steps:"
    echo "1. Test the application: http://localhost"
    echo "2. Monitor performance: http://localhost:5555"
    echo "3. Check logs: docker-compose -f docker-compose.scaling.yml logs"
    echo "4. Scale as needed: docker-compose -f docker-compose.scaling.yml up -d --scale app=N"
}

# Run main function
main "$@"