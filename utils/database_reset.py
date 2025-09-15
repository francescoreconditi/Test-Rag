#!/usr/bin/env python3
"""Database Reset Utility for RAG System.

This utility provides functions to reset various databases to a clean state.
Useful for debugging, testing, and maintenance operations.
"""

import os
import sys
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))


def backup_database(db_path: str, backup_suffix: str = None) -> str:
    """Create a backup of the database before resetting."""
    if not os.path.exists(db_path):
        print(f"Database {db_path} does not exist, skipping backup")
        return None

    if backup_suffix is None:
        backup_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")

    backup_path = f"{db_path}.backup_{backup_suffix}"
    shutil.copy2(db_path, backup_path)
    print(f"[BACKUP] Database backed up to: {backup_path}")
    return backup_path


def reset_vector_database():
    """Reset Qdrant vector database by removing collections."""
    print("[RESET] Resetting vector database (Qdrant)...")

    try:
        from qdrant_client import QdrantClient
        from qdrant_client.http.exceptions import UnexpectedResponse

        # Try to connect to Qdrant
        client = QdrantClient(host="localhost", port=6333)

        # Get all collections
        collections = client.get_collections()

        for collection in collections.collections:
            collection_name = collection.name
            print(f"  Deleting collection: {collection_name}")
            try:
                client.delete_collection(collection_name)
                print(f"  [SUCCESS] Deleted collection: {collection_name}")
            except Exception as e:
                print(f"  [WARNING] Error deleting collection {collection_name}: {e}")

        print("[SUCCESS] Vector database reset completed")
        return True

    except ImportError:
        print("[WARNING] Qdrant client not available, skipping vector database reset")
        return False
    except Exception as e:
        print(f"[WARNING] Could not connect to Qdrant: {e}")
        print("   Make sure Qdrant is running with: docker-compose up qdrant")
        return False


def reset_fact_table_database(db_path: str = "data/facts.db", backup: bool = True):
    """Reset the fact table database to clean state."""
    print(f"[RESET] Resetting fact table database: {db_path}")

    if backup and os.path.exists(db_path):
        backup_database(db_path)

    # Remove existing database
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"  [SUCCESS] Removed existing database: {db_path}")

    # Ensure data directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # Recreate clean database with schema
    try:
        from src.infrastructure.repositories.fact_table_repository import FactTableRepository

        # Create new clean database
        fact_repo = FactTableRepository(db_path)
        print(f"  [SUCCESS] Created clean fact table database: {db_path}")
        return True

    except Exception as e:
        print(f"  [ERROR] Error creating fact table database: {e}")
        return False


def reset_secure_fact_table_database(db_path: str = "data/secure_facts.db", backup: bool = True):
    """Reset the secure fact table database to clean state."""
    print(f"[RESET] Resetting secure fact table database: {db_path}")

    if backup and os.path.exists(db_path):
        backup_database(db_path)

    # Remove existing database
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"  [SUCCESS] Removed existing database: {db_path}")

    # Ensure data directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    # Recreate clean database with security schema
    try:
        from src.infrastructure.repositories.secure_fact_table import SecureFactTableRepository

        # Create new clean secure database
        secure_repo = SecureFactTableRepository(db_path)
        print(f"  [SUCCESS] Created clean secure fact table database: {db_path}")
        return True

    except Exception as e:
        print(f"  [ERROR] Error creating secure fact table database: {e}")
        return False


def reset_cache_directories():
    """Clear all cache directories."""
    print("[RESET] Clearing cache directories...")

    cache_dirs = [
        "cache",
        "__pycache__",
        ".ruff_cache",
        "src/__pycache__",
        "services/__pycache__",
        "components/__pycache__",
        "utils/__pycache__",
    ]

    for cache_dir in cache_dirs:
        if os.path.exists(cache_dir):
            try:
                shutil.rmtree(cache_dir)
                print(f"  [SUCCESS] Cleared cache directory: {cache_dir}")
            except Exception as e:
                print(f"  [WARNING] Error clearing {cache_dir}: {e}")


def reset_log_files():
    """Clear log files."""
    print("[RESET] Clearing log files...")

    log_patterns = ["*.log", "logs/*.log", "data/*.log"]

    import glob

    for pattern in log_patterns:
        for log_file in glob.glob(pattern):
            try:
                os.remove(log_file)
                print(f"  [SUCCESS] Removed log file: {log_file}")
            except Exception as e:
                print(f"  [WARNING] Error removing {log_file}: {e}")


def create_sample_data():
    """Create some sample data for testing."""
    print("[SAMPLES] Creating sample data...")

    try:
        from src.domain.value_objects.source_reference import SourceReference, SourceType
        from src.infrastructure.repositories.secure_fact_table import SecureFactTableRepository
        from src.core.security.user_context import UserRole, DataClassification, create_user_context

        # Create admin user context for data insertion
        admin_user = create_user_context(user_id="admin", username="admin", role=UserRole.ADMIN)

        # Initialize secure repository
        secure_repo = SecureFactTableRepository("data/secure_facts.db")

        # Sample data
        sample_facts = [
            {
                "metric_name": "Ricavi",
                "value": 1000000.0,
                "entity_name": "Azienda_A",
                "period_key": "2024-Q1",
                "scenario": "Actual",
                "classification_level": DataClassification.INTERNAL,
                "department": "Finance",
                "region": "North",
                "cost_center_code": "CDC_100",
            },
            {
                "metric_name": "Costi Operativi",
                "value": 750000.0,
                "entity_name": "Azienda_A",
                "period_key": "2024-Q1",
                "scenario": "Actual",
                "classification_level": DataClassification.INTERNAL,
                "department": "Operations",
                "region": "North",
                "cost_center_code": "CDC_110",
            },
            {
                "metric_name": "EBITDA",
                "value": 250000.0,
                "entity_name": "Azienda_B",
                "period_key": "2024-Q1",
                "scenario": "Actual",
                "classification_level": DataClassification.CONFIDENTIAL,
                "department": "Finance",
                "region": "South",
                "cost_center_code": "CDC_200",
            },
        ]

        # Insert sample facts
        for fact_data in sample_facts:
            source_ref = SourceReference(
                file_path="utils/database_reset.py",
                file_name="database_reset.py",
                source_type=SourceType.TXT,
                extraction_timestamp=datetime.utcnow(),
            )

            fact_id = secure_repo.insert_secure_fact(user_context=admin_user, source_reference=source_ref, **fact_data)
            print(f"  [SUCCESS] Created sample fact: {fact_id}")

        print("[SUCCESS] Sample data creation completed")
        return True

    except Exception as e:
        print(f"[ERROR] Error creating sample data: {e}")
        return False


def reset_all_databases(create_samples: bool = False, backup: bool = True):
    """Reset all databases to clean state."""
    print("=" * 60)
    print("[RESET] RESETTING ALL DATABASES TO CLEAN STATE")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    results = {}

    # 1. Reset vector database
    results["vector_db"] = reset_vector_database()
    print()

    # 2. Reset fact table database
    results["fact_db"] = reset_fact_table_database(backup=backup)
    print()

    # 3. Reset secure fact table database
    results["secure_fact_db"] = reset_secure_fact_table_database(backup=backup)
    print()

    # 4. Clear caches
    reset_cache_directories()
    print()

    # 5. Clear logs
    reset_log_files()
    print()

    # 6. Create sample data if requested
    if create_samples:
        results["sample_data"] = create_sample_data()
        print()

    # Summary
    print("=" * 60)
    print("[SUMMARY] RESET SUMMARY")
    print("=" * 60)

    for operation, success in results.items():
        status = "[SUCCESS]" if success else "[FAILED]"
        print(f"{operation:20} : {status}")

    total_success = sum(1 for success in results.values() if success)
    total_operations = len(results)

    print(f"\nOperations completed: {total_success}/{total_operations}")

    if total_success == total_operations:
        print("[SUCCESS] All databases reset successfully!")
        print("\nNext steps:")
        print("  1. Restart Streamlit app if running")
        print("  2. Restart Qdrant if needed: docker-compose up qdrant")
        print("  3. Test authentication with demo users")
        return True
    else:
        print("[WARNING] Some operations failed. Check the logs above.")
        return False


def main():
    """Main function with command line interface."""
    import argparse

    parser = argparse.ArgumentParser(description="Database Reset Utility for RAG System")
    parser.add_argument("--vector", action="store_true", help="Reset vector database only")
    parser.add_argument("--facts", action="store_true", help="Reset fact table database only")
    parser.add_argument("--secure", action="store_true", help="Reset secure fact table database only")
    parser.add_argument("--cache", action="store_true", help="Clear cache directories only")
    parser.add_argument("--logs", action="store_true", help="Clear log files only")
    parser.add_argument("--samples", action="store_true", help="Create sample data after reset")
    parser.add_argument("--no-backup", action="store_true", help="Skip database backup")
    parser.add_argument("--all", action="store_true", help="Reset all databases (default)")

    args = parser.parse_args()

    # Default to all if no specific option selected
    if not any([args.vector, args.facts, args.secure, args.cache, args.logs]):
        args.all = True

    backup = not args.no_backup

    if args.all:
        return reset_all_databases(create_samples=args.samples, backup=backup)

    # Individual operations
    if args.vector:
        reset_vector_database()

    if args.facts:
        reset_fact_table_database(backup=backup)

    if args.secure:
        reset_secure_fact_table_database(backup=backup)

    if args.cache:
        reset_cache_directories()

    if args.logs:
        reset_log_files()

    if args.samples:
        create_sample_data()

    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n[CANCELLED] Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        sys.exit(1)
