"""Base repository implementation with common functionality."""

from abc import ABC
from datetime import datetime
import json
import logging
from pathlib import Path
import sqlite3
from typing import Any, Optional, TypeVar

from src.application.interfaces.repository_interfaces import IRepository

logger = logging.getLogger(__name__)

T = TypeVar('T')


class BaseRepository(IRepository, ABC):
    """Base repository with SQLite implementation."""

    def __init__(self, db_path: Path, table_name: str, entity_class: type[T]):
        """Initialize repository with database connection."""
        self.db_path = db_path
        self.table_name = table_name
        self.entity_class = entity_class

        # Ensure database directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_database()

    def _init_database(self):
        """Initialize database table."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Add indexes
            conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self.table_name}_created_at
                ON {self.table_name} (created_at)
            """)
            conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self.table_name}_updated_at
                ON {self.table_name} (updated_at)
            """)

            conn.commit()

    def _serialize_entity(self, entity: T) -> str:
        """Serialize entity to JSON string."""
        if hasattr(entity, 'to_dict'):
            return json.dumps(entity.to_dict())
        return json.dumps(entity.__dict__)

    def _deserialize_entity(self, data: str) -> T:
        """Deserialize JSON string to entity."""
        data_dict = json.loads(data)

        # Try to use from_dict method if available
        if hasattr(self.entity_class, 'from_dict'):
            return self.entity_class.from_dict(data_dict)

        # Otherwise use constructor
        return self.entity_class(**data_dict)

    def save(self, entity: T) -> str:
        """Save an entity and return its ID."""
        entity_id = getattr(entity, 'id', None)

        # Generate ID if not present
        if not entity_id:
            from uuid import uuid4
            entity_id = str(uuid4())
            if hasattr(entity, 'id'):
                entity.id = entity_id

        now = datetime.now().isoformat()
        data = self._serialize_entity(entity)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(f"""
                INSERT OR REPLACE INTO {self.table_name}
                (id, data, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (entity_id, data, now, now))
            conn.commit()

        logger.info(f"Saved entity {entity_id} to {self.table_name}")
        return entity_id

    def find_by_id(self, entity_id: str) -> Optional[T]:
        """Find an entity by ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(f"""
                SELECT data FROM {self.table_name}
                WHERE id = ?
            """, (entity_id,))

            row = cursor.fetchone()
            if row:
                return self._deserialize_entity(row[0])

        return None

    def find_all(self, limit: int = 100, offset: int = 0) -> list[T]:
        """Find all entities with pagination."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(f"""
                SELECT data FROM {self.table_name}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))

            return [self._deserialize_entity(row[0]) for row in cursor.fetchall()]

    def update(self, entity_id: str, entity: T) -> bool:
        """Update an entity."""
        if not self.exists(entity_id):
            return False

        data = self._serialize_entity(entity)
        now = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(f"""
                UPDATE {self.table_name}
                SET data = ?, updated_at = ?
                WHERE id = ?
            """, (data, now, entity_id))
            conn.commit()

            updated = cursor.rowcount > 0

        if updated:
            logger.info(f"Updated entity {entity_id} in {self.table_name}")

        return updated

    def delete(self, entity_id: str) -> bool:
        """Delete an entity."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(f"""
                DELETE FROM {self.table_name}
                WHERE id = ?
            """, (entity_id,))
            conn.commit()

            deleted = cursor.rowcount > 0

        if deleted:
            logger.info(f"Deleted entity {entity_id} from {self.table_name}")

        return deleted

    def exists(self, entity_id: str) -> bool:
        """Check if an entity exists."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(f"""
                SELECT 1 FROM {self.table_name}
                WHERE id = ?
                LIMIT 1
            """, (entity_id,))

            return cursor.fetchone() is not None

    def count(self) -> int:
        """Count total entities."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(f"""
                SELECT COUNT(*) FROM {self.table_name}
            """)

            return cursor.fetchone()[0]

    def find_by_criteria(self, criteria: dict[str, Any], limit: int = 100) -> list[T]:
        """Find entities matching criteria in JSON data."""
        entities = []

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(f"""
                SELECT data FROM {self.table_name}
                ORDER BY created_at DESC
            """)

            for row in cursor:
                entity_data = json.loads(row[0])

                # Check if all criteria match
                match = all(
                    entity_data.get(key) == value
                    for key, value in criteria.items()
                )

                if match:
                    entities.append(self._deserialize_entity(row[0]))
                    if len(entities) >= limit:
                        break

        return entities

    def execute_query(self, query: str, params: tuple = ()) -> list[Any]:
        """Execute a custom query."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            return cursor.fetchall()

    def clear_all(self) -> int:
        """Clear all entities from the table."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(f"DELETE FROM {self.table_name}")
            conn.commit()
            deleted_count = cursor.rowcount

        logger.warning(f"Cleared {deleted_count} entities from {self.table_name}")
        return deleted_count
