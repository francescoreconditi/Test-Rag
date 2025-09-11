# ============================================
# FILE DI TEST/DEBUG - NON PER PRODUZIONE
# Creato da: Claude Code
# Data: 2025-09-10
# Scopo: Setup semplificato per le ottimizzazioni di performance
# ============================================

import subprocess
import sys
import time

import requests


def run_command(command, check=True):
    """Run a shell command and return the result."""
    print(f"[INFO] Running: {command}")
    try:
        result = subprocess.run(command, shell=True, check=check,
                              capture_output=True, text=True)
        if result.stdout:
            print(result.stdout.strip())
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Command failed: {e}")
        if e.stderr:
            print(e.stderr.strip())
        return False

def check_docker():
    """Check if Docker is available."""
    print("[INFO] Checking Docker...")
    if run_command("docker --version"):
        print("[SUCCESS] Docker is available")
        return True
    else:
        print("[ERROR] Docker is not available")
        return False

def setup_redis():
    """Setup Redis container."""
    print("[INFO] Setting up Redis...")

    # Check if Redis container exists
    result = subprocess.run("docker ps -a --format {{.Names}}",
                          shell=True, capture_output=True, text=True)

    if "rag_redis" in result.stdout:
        print("[WARNING] Redis container already exists, restarting...")
        run_command("docker restart rag_redis", check=False)
    else:
        print("[INFO] Creating Redis container...")
        if not run_command("docker run -d --name rag_redis -p 6379:6379 redis:7-alpine"):
            return False

    # Wait for Redis to be ready
    print("[INFO] Waiting for Redis to be ready...")
    for _i in range(30):
        if run_command("docker exec rag_redis redis-cli ping", check=False):
            print("[SUCCESS] Redis is ready")
            return True
        time.sleep(1)

    print("[ERROR] Redis failed to start")
    return False

def setup_qdrant():
    """Setup Qdrant container."""
    print("[INFO] Setting up Qdrant...")

    # Check if Qdrant container exists
    result = subprocess.run("docker ps -a --format {{.Names}}",
                          shell=True, capture_output=True, text=True)

    if "rag_qdrant" in result.stdout:
        print("[WARNING] Qdrant container already exists, restarting...")
        run_command("docker restart rag_qdrant", check=False)
    else:
        print("[INFO] Creating Qdrant container...")
        if not run_command("docker run -d --name rag_qdrant -p 6333:6333 qdrant/qdrant"):
            return False

    # Wait for Qdrant to be ready
    print("[INFO] Waiting for Qdrant to be ready...")
    for _i in range(60):
        try:
            response = requests.get("http://localhost:6333/", timeout=2)
            if response.status_code == 200:
                print("[SUCCESS] Qdrant is ready")
                return True
        except:
            pass
        time.sleep(1)

    print("[ERROR] Qdrant failed to start")
    return False

def install_dependencies():
    """Install performance dependencies."""
    print("[INFO] Installing performance dependencies...")

    # Install basic dependencies
    packages = ["redis", "celery", "flower", "requests"]

    for package in packages:
        print(f"[INFO] Installing {package}...")
        if not run_command(f"pip install {package}"):
            print(f"[WARNING] Failed to install {package}")

    print("[SUCCESS] Dependencies installation complete")
    return True

def test_connections():
    """Test Redis and Qdrant connections."""
    print("[INFO] Testing connections...")

    # Test Redis
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        r.ping()
        print("[SUCCESS] Redis connection test passed")
    except Exception as e:
        print(f"[ERROR] Redis test failed: {e}")

    # Test Qdrant
    try:
        response = requests.get('http://localhost:6333/', timeout=5)
        if response.status_code == 200:
            print("[SUCCESS] Qdrant connection test passed")
        else:
            print(f"[ERROR] Qdrant returned status: {response.status_code}")
    except Exception as e:
        print(f"[ERROR] Qdrant test failed: {e}")

def create_monitoring_info():
    """Create monitoring information file."""
    info = """
Monitoring Endpoints:

Application:
   - Main App: http://localhost:8502
   - Health Check: http://localhost:6333/health

Services:
   - Redis: localhost:6379
   - Qdrant: localhost:6333

Management Commands:
   - Redis CLI: docker exec -it rag_redis redis-cli
   - View Redis logs: docker logs rag_redis
   - View Qdrant logs: docker logs rag_qdrant
   - Stop Redis: docker stop rag_redis
   - Stop Qdrant: docker stop rag_qdrant
   - Start containers: docker start rag_redis rag_qdrant

Performance Tips:
   - Test Redis: docker exec -it rag_redis redis-cli ping
   - Test Qdrant: curl http://localhost:6333/health
   - View container status: docker ps
"""

    with open("monitoring_endpoints.txt", "w", encoding="utf-8") as f:
        f.write(info)

    print("[SUCCESS] Monitoring info created in monitoring_endpoints.txt")

def main():
    print("RAG System Performance Optimization Setup")
    print("=" * 50)

    # Check Docker
    if not check_docker():
        sys.exit(1)

    # Install dependencies
    install_dependencies()

    # Setup Redis
    if not setup_redis():
        print("[ERROR] Redis setup failed")
        sys.exit(1)

    # Setup Qdrant
    if not setup_qdrant():
        print("[ERROR] Qdrant setup failed")
        sys.exit(1)

    # Test connections
    test_connections()

    # Create monitoring info
    create_monitoring_info()

    print("\nPerformance optimization setup complete!")
    print("\nNext steps:")
    print("1. Check containers: docker ps")
    print("2. Test Redis: docker exec -it rag_redis redis-cli ping")
    print("3. Test Qdrant: curl http://localhost:6333/health")
    print("4. View monitoring info: type monitoring_endpoints.txt")
    print("5. Start Celery worker: celery -A src.infrastructure.performance.celery_tasks worker --loglevel=info")

if __name__ == "__main__":
    main()
