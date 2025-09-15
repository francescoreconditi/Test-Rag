"""Secure Fact Table Repository with Row-level Security (RLS) implementation."""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

from .fact_table_repository import FactTableRepository, FactRecord
from src.core.security import UserContext, AccessControlService, RLSFilter, DataClassification, SecurityViolationError
from src.domain.value_objects.source_reference import SourceReference

logger = logging.getLogger(__name__)


@dataclass
class SecureFactRecord(FactRecord):
    """Extended fact record with security metadata."""

    tenant_id: Optional[str] = None
    classification_level: DataClassification = DataClassification.INTERNAL
    created_by: Optional[str] = None
    department: Optional[str] = None
    region: Optional[str] = None
    cost_center_code: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert secure fact record to dictionary."""
        base_dict = super().to_dict()
        base_dict.update(
            {
                "tenant_id": self.tenant_id,
                "classification_level": self.classification_level.value if self.classification_level else 2,
                "created_by": self.created_by,
                "department": self.department,
                "region": self.region,
                "cost_center_code": self.cost_center_code,
            }
        )
        return base_dict


class SecureFactTableRepository(FactTableRepository):
    """Secure fact table repository with Row-level Security."""

    def __init__(self, db_path: str = "data/secure_facts.db", use_duckdb: bool = True):
        """Initialize secure fact table repository."""
        super().__init__(db_path, use_duckdb)
        self.access_control = AccessControlService()
        self.logger = logging.getLogger(__name__)
        self._setup_security_schema()

    def _setup_security_schema(self):
        """Setup database schema with security columns."""
        try:
            # Add security columns to facts table
            security_columns = [
                "ALTER TABLE facts ADD COLUMN IF NOT EXISTS tenant_id TEXT",
                "ALTER TABLE facts ADD COLUMN IF NOT EXISTS classification_level INTEGER DEFAULT 2",
                "ALTER TABLE facts ADD COLUMN IF NOT EXISTS created_by TEXT",
                "ALTER TABLE facts ADD COLUMN IF NOT EXISTS department TEXT",
                "ALTER TABLE facts ADD COLUMN IF NOT EXISTS region TEXT",
                "ALTER TABLE facts ADD COLUMN IF NOT EXISTS cost_center_code TEXT",
            ]

            for sql in security_columns:
                try:
                    self.conn.execute(sql)
                except Exception as e:
                    # Column might already exist
                    self.logger.debug(f"Security column setup: {e}")

            # Create indexes for RLS performance
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_facts_tenant ON facts(tenant_id)",
                "CREATE INDEX IF NOT EXISTS idx_facts_classification ON facts(classification_level)",
                "CREATE INDEX IF NOT EXISTS idx_facts_entity ON facts(entity_name)",
                "CREATE INDEX IF NOT EXISTS idx_facts_period ON facts(period_key)",
                "CREATE INDEX IF NOT EXISTS idx_facts_department ON facts(department)",
                "CREATE INDEX IF NOT EXISTS idx_facts_cost_center ON facts(cost_center_code)",
            ]

            for sql in indexes:
                try:
                    self.conn.execute(sql)
                except Exception as e:
                    self.logger.debug(f"Index creation: {e}")

            self.conn.commit()
            self.logger.info("Security schema setup completed")

        except Exception as e:
            self.logger.error(f"Error setting up security schema: {e}")

    def insert_secure_fact(
        self,
        user_context: UserContext,
        metric_name: str,
        value: float,
        entity_name: str,
        period_key: str,
        scenario: str,
        source_reference: SourceReference,
        confidence_score: float = 0.9,
        metadata: Optional[Dict[str, Any]] = None,
        classification_level: DataClassification = DataClassification.INTERNAL,
        department: Optional[str] = None,
        region: Optional[str] = None,
        cost_center_code: Optional[str] = None,
    ) -> str:
        """Insert fact with security context."""
        try:
            # Validate user permissions
            if not self.access_control.validate_access_attempt(user_context, "fact", operation="write"):
                raise SecurityViolationError(f"User {user_context.user_id} not authorized to insert facts")

            # Validate entity access
            if not user_context.can_access_entity(entity_name):
                raise SecurityViolationError(
                    f"User {user_context.user_id} not authorized to access entity {entity_name}"
                )

            # Validate classification level
            if not user_context.can_access_classification(classification_level):
                raise SecurityViolationError(
                    f"User {user_context.user_id} not authorized for classification level {classification_level.name}"
                )

            # Create secure fact record
            fact_id = f"fact_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"

            secure_fact = SecureFactRecord(
                fact_id=fact_id,
                metric_name=metric_name,
                value=value,
                entity_name=entity_name,
                period_key=period_key,
                scenario=scenario,
                source_reference=source_reference,
                confidence_score=confidence_score,
                metadata=metadata or {},
                created_at=datetime.utcnow(),
                tenant_id=user_context.tenant_id,
                classification_level=classification_level,
                created_by=user_context.user_id,
                department=department or user_context.department,
                region=region,
                cost_center_code=cost_center_code,
            )

            # Insert with security metadata
            sql = """
                INSERT INTO facts (
                    fact_id, metric_name, value, entity_name, period_key, scenario,
                    source_reference, confidence_score, metadata, created_at,
                    tenant_id, classification_level, created_by, department, 
                    region, cost_center_code
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            params = (
                secure_fact.fact_id,
                secure_fact.metric_name,
                secure_fact.value,
                secure_fact.entity_name,
                secure_fact.period_key,
                secure_fact.scenario,
                json.dumps(secure_fact.source_reference.to_dict()),
                secure_fact.confidence_score,
                json.dumps(secure_fact.metadata),
                secure_fact.created_at.isoformat(),
                secure_fact.tenant_id,
                secure_fact.classification_level.value if secure_fact.classification_level else 2,
                secure_fact.created_by,
                secure_fact.department,
                secure_fact.region,
                secure_fact.cost_center_code,
            )

            self.conn.execute(sql, params)
            self.conn.commit()

            # Audit log
            self.access_control.audit_access_attempt(
                user_context,
                "fact",
                "write",
                True,
                fact_id,
                {"metric": metric_name, "entity": entity_name, "classification": classification_level.name},
            )

            self.logger.info(f"Inserted secure fact {fact_id} by user {user_context.user_id}")
            return fact_id

        except SecurityViolationError:
            # Audit failed attempt
            self.access_control.audit_access_attempt(
                user_context,
                "fact",
                "write",
                False,
                None,
                {"metric": metric_name, "entity": entity_name, "reason": "security_violation"},
            )
            raise
        except Exception as e:
            self.logger.error(f"Error inserting secure fact: {e}")
            raise

    def get_facts_with_rls(
        self,
        user_context: UserContext,
        entity_name: Optional[str] = None,
        period_key: Optional[str] = None,
        metric_name: Optional[str] = None,
        limit: int = 1000,
    ) -> List[SecureFactRecord]:
        """Get facts with Row-level Security applied."""
        try:
            # Generate RLS filter
            rls_filter = self.access_control.generate_rls_filter(user_context, "facts")

            # Build base query
            base_sql = """
                SELECT fact_id, metric_name, value, entity_name, period_key, scenario,
                       source_reference, confidence_score, metadata, created_at,
                       tenant_id, classification_level, created_by, department,
                       region, cost_center_code
                FROM facts
            """

            # Add WHERE conditions
            where_conditions = []
            params = {}
            param_counter = 0

            # Add RLS constraints
            rls_where, rls_params = self.access_control.convert_rls_to_sql_where(rls_filter, "")
            if rls_where:
                where_conditions.append(f"({rls_where})")
                params.update(rls_params)
                param_counter = len(rls_params)

            # Add user filters
            if entity_name:
                where_conditions.append(f"entity_name = :user_param_{param_counter}")
                params[f"user_param_{param_counter}"] = entity_name
                param_counter += 1

            if period_key:
                where_conditions.append(f"period_key = :user_param_{param_counter}")
                params[f"user_param_{param_counter}"] = period_key
                param_counter += 1

            if metric_name:
                where_conditions.append(f"metric_name = :user_param_{param_counter}")
                params[f"user_param_{param_counter}"] = metric_name
                param_counter += 1

            # Construct final query
            if where_conditions:
                sql = f"{base_sql} WHERE {' AND '.join(where_conditions)}"
            else:
                sql = base_sql

            sql += f" ORDER BY created_at DESC LIMIT {limit}"

            # Execute query
            if self.use_duckdb:
                result = self.conn.execute(sql, params).fetchall()
            else:
                # For SQLite, convert named parameters to positional
                sqlite_sql = sql
                sqlite_params = []
                for key in sorted(params.keys()):
                    sqlite_sql = sqlite_sql.replace(f":{key}", "?")
                    sqlite_params.append(params[key])
                result = self.conn.execute(sqlite_sql, sqlite_params).fetchall()

            # Convert to SecureFactRecord objects
            facts = []
            for row in result:
                try:
                    source_ref = SourceReference.from_dict(json.loads(row[6]))
                    metadata = json.loads(row[8]) if row[8] else {}

                    fact = SecureFactRecord(
                        fact_id=row[0],
                        metric_name=row[1],
                        value=row[2],
                        entity_name=row[3],
                        period_key=row[4],
                        scenario=row[5],
                        source_reference=source_ref,
                        confidence_score=row[7],
                        metadata=metadata,
                        created_at=datetime.fromisoformat(row[9]),
                        tenant_id=row[10],
                        classification_level=DataClassification(row[11]) if row[11] else DataClassification.INTERNAL,
                        created_by=row[12],
                        department=row[13],
                        region=row[14],
                        cost_center_code=row[15],
                    )
                    facts.append(fact)

                except Exception as e:
                    self.logger.warning(f"Error parsing fact record: {e}")
                    continue

            # Audit successful access
            self.access_control.audit_access_attempt(
                user_context,
                "facts",
                "read",
                True,
                None,
                {
                    "entity_filter": entity_name,
                    "period_filter": period_key,
                    "metric_filter": metric_name,
                    "results_count": len(facts),
                    "rls_constraints": len(rls_filter.constraints),
                },
            )

            self.logger.info(
                f"Retrieved {len(facts)} facts for user {user_context.user_id} "
                f"with {len(rls_filter.constraints)} RLS constraints"
            )

            return facts

        except Exception as e:
            self.logger.error(f"Error retrieving facts with RLS: {e}")
            # Audit failed access
            self.access_control.audit_access_attempt(user_context, "facts", "read", False, None, {"error": str(e)})
            raise

    def delete_facts_with_rls(
        self,
        user_context: UserContext,
        entity_name: Optional[str] = None,
        period_key: Optional[str] = None,
        fact_ids: Optional[List[str]] = None,
    ) -> int:
        """Delete facts with Row-level Security validation."""
        try:
            # Validate delete permission
            if not self.access_control.validate_access_attempt(user_context, "fact", operation="delete"):
                raise SecurityViolationError(f"User {user_context.user_id} not authorized to delete facts")

            # First, get facts to verify access before deletion
            facts_to_delete = self.get_facts_with_rls(user_context, entity_name, period_key, limit=10000)

            if fact_ids:
                # Filter by specific fact IDs
                facts_to_delete = [f for f in facts_to_delete if f.fact_id in fact_ids]

            if not facts_to_delete:
                self.logger.info(f"No facts found to delete for user {user_context.user_id}")
                return 0

            # Delete facts
            fact_id_list = [f.fact_id for f in facts_to_delete]
            placeholders = ",".join(["?" for _ in fact_id_list])
            sql = f"DELETE FROM facts WHERE fact_id IN ({placeholders})"

            result = self.conn.execute(sql, fact_id_list)
            deleted_count = result.rowcount if hasattr(result, "rowcount") else len(fact_id_list)
            self.conn.commit()

            # Audit successful deletion
            self.access_control.audit_access_attempt(
                user_context,
                "facts",
                "delete",
                True,
                None,
                {
                    "deleted_count": deleted_count,
                    "entity_filter": entity_name,
                    "period_filter": period_key,
                    "fact_ids": fact_ids[:10] if fact_ids else None,  # First 10 for audit
                },
            )

            self.logger.info(f"Deleted {deleted_count} facts for user {user_context.user_id}")
            return deleted_count

        except SecurityViolationError:
            self.access_control.audit_access_attempt(
                user_context, "facts", "delete", False, None, {"reason": "security_violation"}
            )
            raise
        except Exception as e:
            self.logger.error(f"Error deleting facts with RLS: {e}")
            self.access_control.audit_access_attempt(user_context, "facts", "delete", False, None, {"error": str(e)})
            raise

    def get_accessible_entities(self, user_context: UserContext) -> List[str]:
        """Get list of entities accessible to user."""
        try:
            if user_context.is_admin():
                # Admin can see all entities
                sql = "SELECT DISTINCT entity_name FROM facts ORDER BY entity_name"
                result = self.conn.execute(sql).fetchall()
                return [row[0] for row in result]

            # Apply RLS filter
            rls_filter = self.access_control.generate_rls_filter(user_context, "facts")
            base_sql = "SELECT DISTINCT entity_name FROM facts"

            rls_where, rls_params = self.access_control.convert_rls_to_sql_where(rls_filter, "")
            if rls_where:
                sql = f"{base_sql} WHERE {rls_where} ORDER BY entity_name"
                if self.use_duckdb:
                    result = self.conn.execute(sql, rls_params).fetchall()
                else:
                    # Convert to positional parameters for SQLite
                    sqlite_params = []
                    for key in sorted(rls_params.keys()):
                        sql = sql.replace(f":{key}", "?")
                        sqlite_params.append(rls_params[key])
                    result = self.conn.execute(sql, sqlite_params).fetchall()
            else:
                result = self.conn.execute(f"{base_sql} ORDER BY entity_name").fetchall()

            return [row[0] for row in result]

        except Exception as e:
            self.logger.error(f"Error getting accessible entities: {e}")
            return []

    def get_security_stats(self, user_context: UserContext) -> Dict[str, Any]:
        """Get security statistics for user context."""
        try:
            if not user_context.is_admin():
                # Only admins can see security stats
                raise SecurityViolationError("Insufficient permissions for security statistics")

            stats = {}

            # Total facts by tenant
            sql = """
                SELECT tenant_id, COUNT(*) as fact_count
                FROM facts
                GROUP BY tenant_id
                ORDER BY fact_count DESC
            """
            result = self.conn.execute(sql).fetchall()
            stats["facts_by_tenant"] = {row[0] or "no_tenant": row[1] for row in result}

            # Facts by classification level
            sql = """
                SELECT classification_level, COUNT(*) as fact_count
                FROM facts
                GROUP BY classification_level
                ORDER BY classification_level
            """
            result = self.conn.execute(sql).fetchall()
            classification_names = {1: "PUBLIC", 2: "INTERNAL", 3: "CONFIDENTIAL", 4: "RESTRICTED"}
            stats["facts_by_classification"] = {
                classification_names.get(row[0], f"LEVEL_{row[0]}"): row[1] for row in result
            }

            # Facts by entity
            sql = """
                SELECT entity_name, COUNT(*) as fact_count
                FROM facts
                GROUP BY entity_name
                ORDER BY fact_count DESC
                LIMIT 10
            """
            result = self.conn.execute(sql).fetchall()
            stats["top_entities"] = {row[0]: row[1] for row in result}

            # Recent activity
            sql = """
                SELECT DATE(created_at) as date, COUNT(*) as fact_count
                FROM facts
                WHERE created_at >= datetime('now', '-30 days')
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """
            result = self.conn.execute(sql).fetchall()
            stats["recent_activity"] = {row[0]: row[1] for row in result}

            return stats

        except SecurityViolationError:
            raise
        except Exception as e:
            self.logger.error(f"Error getting security stats: {e}")
            return {}
