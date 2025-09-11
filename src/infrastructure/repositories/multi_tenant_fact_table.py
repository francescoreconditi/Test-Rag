# ============================================
# FILE DI SERVIZIO ENTERPRISE - PRODUZIONE
# Creato da: Claude Code
# Data: 2025-09-08
# Scopo: Multi-tenant fact table repository per enterprise RAG
# ============================================

"""
Multi-tenant fact table repository for enterprise RAG system.
Provides tenant-isolated data storage with dimensional modeling and provenance tracking.
"""

from dataclasses import dataclass
from datetime import datetime
import json
import logging
from pathlib import Path
import sqlite3
from typing import Any, Optional

from src.domain.entities.tenant_context import TenantContext
from src.domain.value_objects.source_reference import SourceReference
from src.infrastructure.repositories.fact_table_repository import FactRecord, FactTableRepository

logger = logging.getLogger(__name__)

@dataclass
class TenantFactRecord(FactRecord):
    """Fact record with tenant isolation."""
    tenant_id: str
    tenant_schema: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary including tenant information."""
        base_dict = super().to_dict()
        base_dict.update({
            'tenant_id': self.tenant_id,
            'tenant_schema': self.tenant_schema
        })
        return base_dict

class MultiTenantFactTableRepository:
    """
    Enterprise multi-tenant fact table repository.
    Provides complete tenant isolation for financial metrics data.
    """

    def __init__(self, base_database_path: str = "data/multi_tenant_facts.db"):
        self.base_database_path = Path(base_database_path)
        self.base_database_path.parent.mkdir(exist_ok=True)

        # Tenant-specific repositories
        self._tenant_repositories: dict[str, FactTableRepository] = {}

        # Master tenant registry
        self._init_master_database()

    def _init_master_database(self):
        """Initialize master database for tenant registry."""
        try:
            with sqlite3.connect(self.base_database_path) as conn:
                conn.executescript("""
                    CREATE TABLE IF NOT EXISTS tenant_databases (
                        tenant_id TEXT PRIMARY KEY,
                        database_path TEXT NOT NULL,
                        schema_name TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        last_accessed TEXT NOT NULL,
                        fact_count INTEGER DEFAULT 0,
                        storage_size_bytes INTEGER DEFAULT 0
                    );

                    CREATE TABLE IF NOT EXISTS tenant_metrics_summary (
                        tenant_id TEXT NOT NULL,
                        metric_name TEXT NOT NULL,
                        entity_name TEXT NOT NULL,
                        period_key TEXT NOT NULL,
                        latest_value REAL,
                        value_count INTEGER DEFAULT 1,
                        last_updated TEXT NOT NULL,
                        PRIMARY KEY (tenant_id, metric_name, entity_name, period_key),
                        FOREIGN KEY (tenant_id) REFERENCES tenant_databases (tenant_id)
                    );

                    CREATE TABLE IF NOT EXISTS cross_tenant_analytics (
                        analytics_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        analytics_type TEXT NOT NULL,
                        tenant_count INTEGER NOT NULL,
                        metrics_analyzed TEXT NOT NULL,
                        results TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );

                    CREATE INDEX IF NOT EXISTS idx_tenant_db_path ON tenant_databases(database_path);
                    CREATE INDEX IF NOT EXISTS idx_tenant_summary_metric ON tenant_metrics_summary(metric_name);
                    CREATE INDEX IF NOT EXISTS idx_cross_tenant_type ON cross_tenant_analytics(analytics_type);
                """)
            logger.info("Master multi-tenant database initialized")
        except Exception as e:
            logger.error(f"Failed to initialize master database: {e}")
            raise

    async def get_tenant_repository(self, tenant_context: TenantContext) -> FactTableRepository:
        """Get or create tenant-specific fact table repository."""
        tenant_id = tenant_context.tenant_id

        # Return cached repository if available
        if tenant_id in self._tenant_repositories:
            await self._update_tenant_access(tenant_id)
            return self._tenant_repositories[tenant_id]

        try:
            # Create tenant-specific database path
            tenant_db_path = self.base_database_path.parent / f"tenant_{tenant_id}_facts.db"

            # Initialize tenant repository
            tenant_repo = FactTableRepository(str(tenant_db_path))

            # Customize for tenant isolation
            await self._setup_tenant_schema(tenant_repo, tenant_context)

            # Register tenant database
            await self._register_tenant_database(tenant_context, str(tenant_db_path))

            # Cache repository
            self._tenant_repositories[tenant_id] = tenant_repo

            logger.info(f"Created tenant repository for: {tenant_id}")
            return tenant_repo

        except Exception as e:
            logger.error(f"Failed to create tenant repository for {tenant_id}: {e}")
            raise

    async def _setup_tenant_schema(self, repository: FactTableRepository, tenant_context: TenantContext):
        """Setup tenant-specific schema modifications."""
        try:
            # Add tenant-specific columns to fact table
            with sqlite3.connect(repository.database_path) as conn:
                # Check if tenant columns exist
                cursor = conn.execute("PRAGMA table_info(facts)")
                columns = [row[1] for row in cursor.fetchall()]

                if 'tenant_id' not in columns:
                    conn.execute("ALTER TABLE facts ADD COLUMN tenant_id TEXT NOT NULL DEFAULT ''")

                if 'tenant_schema' not in columns:
                    conn.execute("ALTER TABLE facts ADD COLUMN tenant_schema TEXT NOT NULL DEFAULT ''")

                if 'encryption_key_id' not in columns:
                    conn.execute("ALTER TABLE facts ADD COLUMN encryption_key_id TEXT")

                # Create tenant-specific indexes
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_facts_tenant_id
                    ON facts(tenant_id)
                """)

                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_facts_tenant_metric
                    ON facts(tenant_id, metric_name)
                """)

                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_facts_tenant_entity
                    ON facts(tenant_id, entity_name)
                """)

            logger.debug(f"Setup tenant schema for: {tenant_context.tenant_id}")

        except Exception as e:
            logger.error(f"Failed to setup tenant schema: {e}")
            raise

    async def _register_tenant_database(self, tenant_context: TenantContext, database_path: str):
        """Register tenant database in master registry."""
        try:
            now = datetime.now().isoformat()

            with sqlite3.connect(self.base_database_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO tenant_databases
                    (tenant_id, database_path, schema_name, created_at, last_accessed)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    tenant_context.tenant_id,
                    database_path,
                    tenant_context.database_schema,
                    now,
                    now
                ))

            logger.debug(f"Registered tenant database: {tenant_context.tenant_id}")

        except Exception as e:
            logger.error(f"Failed to register tenant database: {e}")
            raise

    async def _update_tenant_access(self, tenant_id: str):
        """Update last access time for tenant."""
        try:
            with sqlite3.connect(self.base_database_path) as conn:
                conn.execute("""
                    UPDATE tenant_databases
                    SET last_accessed = ?
                    WHERE tenant_id = ?
                """, (datetime.now().isoformat(), tenant_id))
        except Exception as e:
            logger.warning(f"Failed to update tenant access time: {e}")

    async def store_tenant_fact(self,
                              tenant_context: TenantContext,
                              metric_name: str,
                              value: float,
                              entity_name: str,
                              period_key: str,
                              scenario: str,
                              source_reference: SourceReference,
                              confidence_score: float = 1.0,
                              metadata: Optional[dict[str, Any]] = None) -> bool:
        """Store a fact record for a specific tenant."""
        try:
            tenant_repo = await self.get_tenant_repository(tenant_context)

            # Create tenant fact record
            tenant_fact = TenantFactRecord(
                fact_id=f"{tenant_context.tenant_id}_{datetime.now().timestamp()}_{hash(metric_name + entity_name + period_key)}",
                metric_name=metric_name,
                value=value,
                entity_name=entity_name,
                period_key=period_key,
                scenario=scenario,
                source_reference=source_reference,
                confidence_score=confidence_score,
                metadata=metadata or {},
                created_at=datetime.now(),
                tenant_id=tenant_context.tenant_id,
                tenant_schema=tenant_context.database_schema
            )

            # Store in tenant repository with additional tenant fields
            success = await self._store_tenant_fact_record(tenant_repo, tenant_fact, tenant_context)

            if success:
                # Update tenant metrics summary
                await self._update_tenant_metrics_summary(tenant_context.tenant_id, tenant_fact)

                # Update tenant usage
                tenant_context.update_usage(storage_delta_gb=0.001)  # Approximate storage increase

            return success

        except Exception as e:
            logger.error(f"Failed to store tenant fact for {tenant_context.tenant_id}: {e}")
            return False

    async def _store_tenant_fact_record(self,
                                      repository: FactTableRepository,
                                      tenant_fact: TenantFactRecord,
                                      tenant_context: TenantContext) -> bool:
        """Store tenant fact record with encryption support."""
        try:
            with sqlite3.connect(repository.database_path) as conn:
                # Prepare fact data
                fact_data = {
                    'fact_id': tenant_fact.fact_id,
                    'metric_name': tenant_fact.metric_name,
                    'value': tenant_fact.value,
                    'entity_name': tenant_fact.entity_name,
                    'period_key': tenant_fact.period_key,
                    'scenario': tenant_fact.scenario,
                    'source_reference': json.dumps(tenant_fact.source_reference.to_dict()),
                    'confidence_score': tenant_fact.confidence_score,
                    'metadata': json.dumps(tenant_fact.metadata),
                    'created_at': tenant_fact.created_at.isoformat(),
                    'tenant_id': tenant_fact.tenant_id,
                    'tenant_schema': tenant_fact.tenant_schema,
                    'encryption_key_id': tenant_context.encryption_key_id
                }

                # Insert fact record
                conn.execute("""
                    INSERT INTO facts (
                        fact_id, metric_name, value, entity_name, period_key, scenario,
                        source_reference, confidence_score, metadata, created_at,
                        tenant_id, tenant_schema, encryption_key_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, tuple(fact_data.values()))

            logger.debug(f"Stored tenant fact: {tenant_fact.fact_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to store tenant fact record: {e}")
            return False

    async def _update_tenant_metrics_summary(self, tenant_id: str, fact: TenantFactRecord):
        """Update tenant metrics summary for fast lookups."""
        try:
            with sqlite3.connect(self.base_database_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO tenant_metrics_summary
                    (tenant_id, metric_name, entity_name, period_key, latest_value, value_count, last_updated)
                    VALUES (
                        ?, ?, ?, ?, ?,
                        COALESCE((SELECT value_count + 1 FROM tenant_metrics_summary
                                 WHERE tenant_id=? AND metric_name=? AND entity_name=? AND period_key=?), 1),
                        ?
                    )
                """, (
                    tenant_id, fact.metric_name, fact.entity_name, fact.period_key, fact.value,
                    tenant_id, fact.metric_name, fact.entity_name, fact.period_key,
                    datetime.now().isoformat()
                ))
        except Exception as e:
            logger.warning(f"Failed to update tenant metrics summary: {e}")

    async def query_tenant_facts(self,
                               tenant_context: TenantContext,
                               filters: Optional[dict[str, Any]] = None,
                               limit: int = 100) -> list[TenantFactRecord]:
        """Query facts for a specific tenant."""
        try:
            tenant_repo = await self.get_tenant_repository(tenant_context)

            # Build query with tenant isolation
            base_query = """
                SELECT fact_id, metric_name, value, entity_name, period_key, scenario,
                       source_reference, confidence_score, metadata, created_at,
                       tenant_id, tenant_schema, encryption_key_id
                FROM facts
                WHERE tenant_id = ?
            """

            params = [tenant_context.tenant_id]

            # Add filters
            if filters:
                for key, value in filters.items():
                    if key in ['metric_name', 'entity_name', 'period_key', 'scenario']:
                        base_query += f" AND {key} = ?"
                        params.append(value)
                    elif key == 'confidence_threshold':
                        base_query += " AND confidence_score >= ?"
                        params.append(value)

            base_query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            with sqlite3.connect(tenant_repo.database_path) as conn:
                cursor = conn.execute(base_query, params)
                facts = []

                for row in cursor.fetchall():
                    source_ref_data = json.loads(row[6])
                    source_reference = SourceReference(
                        file_path=source_ref_data['file_path'],
                        source_type=source_ref_data['source_type'],
                        page_number=source_ref_data.get('page_number'),
                        table_index=source_ref_data.get('table_index'),
                        cell_reference=source_ref_data.get('cell_reference'),
                        extraction_timestamp=datetime.fromisoformat(source_ref_data['extraction_timestamp']),
                        content_hash=source_ref_data['content_hash']
                    )

                    fact = TenantFactRecord(
                        fact_id=row[0],
                        metric_name=row[1],
                        value=row[2],
                        entity_name=row[3],
                        period_key=row[4],
                        scenario=row[5],
                        source_reference=source_reference,
                        confidence_score=row[7],
                        metadata=json.loads(row[8]),
                        created_at=datetime.fromisoformat(row[9]),
                        tenant_id=row[10],
                        tenant_schema=row[11]
                    )
                    facts.append(fact)

            return facts

        except Exception as e:
            logger.error(f"Failed to query tenant facts: {e}")
            return []

    async def get_tenant_metrics_summary(self, tenant_id: str) -> dict[str, Any]:
        """Get metrics summary for a tenant."""
        try:
            with sqlite3.connect(self.base_database_path) as conn:
                cursor = conn.execute("""
                    SELECT metric_name, entity_name, period_key, latest_value, value_count, last_updated
                    FROM tenant_metrics_summary
                    WHERE tenant_id = ?
                    ORDER BY last_updated DESC
                """, (tenant_id,))

                metrics = []
                for row in cursor.fetchall():
                    metrics.append({
                        'metric_name': row[0],
                        'entity_name': row[1],
                        'period_key': row[2],
                        'latest_value': row[3],
                        'value_count': row[4],
                        'last_updated': row[5]
                    })

                # Get overall statistics
                cursor = conn.execute("""
                    SELECT COUNT(*) as total_metrics,
                           COUNT(DISTINCT metric_name) as unique_metrics,
                           COUNT(DISTINCT entity_name) as unique_entities,
                           MAX(last_updated) as last_activity
                    FROM tenant_metrics_summary
                    WHERE tenant_id = ?
                """, (tenant_id,))

                stats_row = cursor.fetchone()

                return {
                    'tenant_id': tenant_id,
                    'metrics': metrics,
                    'statistics': {
                        'total_metrics': stats_row[0],
                        'unique_metrics': stats_row[1],
                        'unique_entities': stats_row[2],
                        'last_activity': stats_row[3]
                    }
                }

        except Exception as e:
            logger.error(f"Failed to get tenant metrics summary: {e}")
            return {}

    async def delete_tenant_data(self, tenant_id: str) -> bool:
        """Delete all data for a tenant (GDPR compliance)."""
        try:
            # Get tenant database path
            with sqlite3.connect(self.base_database_path) as conn:
                cursor = conn.execute("""
                    SELECT database_path FROM tenant_databases WHERE tenant_id = ?
                """, (tenant_id,))
                row = cursor.fetchone()

                if not row:
                    logger.warning(f"Tenant database not found: {tenant_id}")
                    return True  # Already deleted

                tenant_db_path = Path(row[0])

            # Delete tenant database file
            if tenant_db_path.exists():
                tenant_db_path.unlink()
                logger.info(f"Deleted tenant database: {tenant_db_path}")

            # Remove from master registry
            with sqlite3.connect(self.base_database_path) as conn:
                conn.execute("DELETE FROM tenant_databases WHERE tenant_id = ?", (tenant_id,))
                conn.execute("DELETE FROM tenant_metrics_summary WHERE tenant_id = ?", (tenant_id,))

            # Remove from cache
            if tenant_id in self._tenant_repositories:
                del self._tenant_repositories[tenant_id]

            logger.info(f"Completely deleted tenant data: {tenant_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete tenant data {tenant_id}: {e}")
            return False

    async def get_tenant_storage_usage(self, tenant_id: str) -> dict[str, Any]:
        """Get storage usage statistics for a tenant."""
        try:
            with sqlite3.connect(self.base_database_path) as conn:
                cursor = conn.execute("""
                    SELECT database_path FROM tenant_databases WHERE tenant_id = ?
                """, (tenant_id,))
                row = cursor.fetchone()

                if not row:
                    return {'error': 'Tenant not found'}

                tenant_db_path = Path(row[0])

                if not tenant_db_path.exists():
                    return {'error': 'Database file not found'}

                # Get file size
                file_size_bytes = tenant_db_path.stat().st_size
                file_size_mb = file_size_bytes / (1024 * 1024)

                # Get record counts
                with sqlite3.connect(tenant_db_path) as tenant_conn:
                    cursor = tenant_conn.execute("SELECT COUNT(*) FROM facts WHERE tenant_id = ?", (tenant_id,))
                    fact_count = cursor.fetchone()[0]

                    cursor = tenant_conn.execute("""
                        SELECT COUNT(DISTINCT metric_name), COUNT(DISTINCT entity_name),
                               COUNT(DISTINCT period_key)
                        FROM facts WHERE tenant_id = ?
                    """, (tenant_id,))
                    unique_counts = cursor.fetchone()

                return {
                    'tenant_id': tenant_id,
                    'database_path': str(tenant_db_path),
                    'file_size_bytes': file_size_bytes,
                    'file_size_mb': round(file_size_mb, 2),
                    'fact_count': fact_count,
                    'unique_metrics': unique_counts[0],
                    'unique_entities': unique_counts[1],
                    'unique_periods': unique_counts[2],
                    'avg_bytes_per_fact': round(file_size_bytes / fact_count, 2) if fact_count > 0 else 0
                }

        except Exception as e:
            logger.error(f"Failed to get storage usage for tenant {tenant_id}: {e}")
            return {'error': str(e)}

    async def export_tenant_data(self, tenant_id: str, export_format: str = 'json') -> Optional[str]:
        """Export all tenant data for migration or backup."""
        try:
            tenant_summary = await self.get_tenant_metrics_summary(tenant_id)
            storage_info = await self.get_tenant_storage_usage(tenant_id)

            # Get all facts (no limit for export)
            with sqlite3.connect(self.base_database_path) as conn:
                cursor = conn.execute("""
                    SELECT database_path FROM tenant_databases WHERE tenant_id = ?
                """, (tenant_id,))
                row = cursor.fetchone()

                if not row:
                    return None

                tenant_db_path = row[0]

            # Export all facts
            with sqlite3.connect(tenant_db_path) as conn:
                cursor = conn.execute("""
                    SELECT fact_id, metric_name, value, entity_name, period_key, scenario,
                           source_reference, confidence_score, metadata, created_at,
                           tenant_id, tenant_schema, encryption_key_id
                    FROM facts
                    WHERE tenant_id = ?
                    ORDER BY created_at
                """, (tenant_id,))

                facts = []
                for row in cursor.fetchall():
                    facts.append({
                        'fact_id': row[0],
                        'metric_name': row[1],
                        'value': row[2],
                        'entity_name': row[3],
                        'period_key': row[4],
                        'scenario': row[5],
                        'source_reference': json.loads(row[6]),
                        'confidence_score': row[7],
                        'metadata': json.loads(row[8]),
                        'created_at': row[9],
                        'tenant_id': row[10],
                        'tenant_schema': row[11],
                        'encryption_key_id': row[12]
                    })

            export_data = {
                'tenant_id': tenant_id,
                'export_timestamp': datetime.now().isoformat(),
                'export_format': export_format,
                'summary': tenant_summary,
                'storage_info': storage_info,
                'facts': facts
            }

            if export_format == 'json':
                return json.dumps(export_data, indent=2)
            else:
                # Could add CSV, XML, etc. formats here
                return json.dumps(export_data, indent=2)

        except Exception as e:
            logger.error(f"Failed to export tenant data {tenant_id}: {e}")
            return None
