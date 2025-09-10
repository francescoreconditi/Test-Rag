"""Enhanced fact table repository with complete data lineage tracking."""

import json
import logging
from pathlib import Path
import sqlite3
from typing import Any, Optional

from src.domain.value_objects.data_lineage import DataLineage, LineageRepository
from src.domain.value_objects.source_reference import SourceReference

logger = logging.getLogger(__name__)


class EnhancedFactTableRepository:
    """Enhanced repository with data lineage tracking."""

    def __init__(self, db_path: str = "data/facts_enhanced.db", use_duckdb: bool = True):
        """Initialize enhanced fact table repository."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)

        self.use_duckdb = use_duckdb
        self.conn = None
        self.lineage_repo = LineageRepository()

        self._initialize_database()
        self._create_enhanced_tables()

    def _initialize_database(self):
        """Initialize database connection."""
        if self.use_duckdb:
            try:
                import duckdb
                self.conn = duckdb.connect(str(self.db_path))
                logger.info(f"Using DuckDB at {self.db_path}")
            except ImportError:
                logger.warning("DuckDB not available, falling back to SQLite")
                self.use_duckdb = False

        if not self.use_duckdb:
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.row_factory = sqlite3.Row
            logger.info(f"Using SQLite at {self.db_path}")

    def _create_enhanced_tables(self):
        """Create enhanced fact table schema with lineage tracking."""

        # Enhanced fact table with lineage columns
        fact_table_sql = """
        CREATE TABLE IF NOT EXISTS fact_kpi_enhanced (
            fact_id INTEGER PRIMARY KEY,

            -- Standard dimensions
            entity_id TEXT NOT NULL,
            metric_name TEXT NOT NULL,
            period_type TEXT NOT NULL,
            period_year INTEGER NOT NULL,
            scenario TEXT NOT NULL DEFAULT 'actual',

            -- Core value
            value REAL NOT NULL,
            currency TEXT,
            unit TEXT,

            -- Source tracking
            source_file TEXT NOT NULL,
            source_hash TEXT NOT NULL,
            source_ref TEXT NOT NULL,
            extraction_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            -- Enhanced lineage tracking
            is_calculated BOOLEAN DEFAULT FALSE,
            calculation_formula TEXT,
            source_fact_ids TEXT,  -- JSON array of source fact IDs
            lineage_data TEXT,  -- Full lineage JSON object
            lineage_hash TEXT,  -- Unique hash of lineage chain
            transformation_history TEXT,  -- JSON array of transformations
            dependency_graph TEXT,  -- JSON graph of dependencies

            -- Quality and confidence
            confidence_score REAL DEFAULT 1.0,
            validation_status TEXT DEFAULT 'pending',
            quality_flags TEXT,  -- JSON object with validation results

            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """

        # Lineage relationships table
        lineage_relationships_sql = """
        CREATE TABLE IF NOT EXISTS lineage_relationships (
            relationship_id INTEGER PRIMARY KEY,
            source_fact_id INTEGER NOT NULL,
            target_fact_id INTEGER NOT NULL,
            relationship_type TEXT NOT NULL,  -- 'direct_source', 'derived_from', 'aggregated_from'
            transformation_applied TEXT,
            confidence REAL DEFAULT 1.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (source_fact_id) REFERENCES fact_kpi_enhanced(fact_id),
            FOREIGN KEY (target_fact_id) REFERENCES fact_kpi_enhanced(fact_id)
        )
        """

        # Transformation log table
        transformation_log_sql = """
        CREATE TABLE IF NOT EXISTS transformation_log (
            log_id INTEGER PRIMARY KEY,
            fact_id INTEGER NOT NULL,
            transformation_type TEXT NOT NULL,
            transformation_params TEXT,  -- JSON
            input_value REAL,
            output_value REAL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (fact_id) REFERENCES fact_kpi_enhanced(fact_id)
        )
        """

        # Create indexes for performance
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_fact_entity ON fact_kpi_enhanced(entity_id)",
            "CREATE INDEX IF NOT EXISTS idx_fact_metric ON fact_kpi_enhanced(metric_name)",
            "CREATE INDEX IF NOT EXISTS idx_fact_period ON fact_kpi_enhanced(period_year, period_type)",
            "CREATE INDEX IF NOT EXISTS idx_fact_calculated ON fact_kpi_enhanced(is_calculated)",
            "CREATE INDEX IF NOT EXISTS idx_lineage_source ON lineage_relationships(source_fact_id)",
            "CREATE INDEX IF NOT EXISTS idx_lineage_target ON lineage_relationships(target_fact_id)",
            "CREATE INDEX IF NOT EXISTS idx_lineage_hash ON fact_kpi_enhanced(lineage_hash)"
        ]

        # Execute table creation
        cursor = self.conn.cursor() if not self.use_duckdb else self.conn

        for sql in [fact_table_sql, lineage_relationships_sql, transformation_log_sql] + indexes:
            cursor.execute(sql)

        if not self.use_duckdb:
            self.conn.commit()

        logger.info("Enhanced fact tables created with lineage tracking")

    def insert_fact_with_lineage(self,
                                 metric_name: str,
                                 value: float,
                                 entity_id: str,
                                 period_type: str,
                                 period_year: int,
                                 source_ref: SourceReference,
                                 lineage: Optional[DataLineage] = None,
                                 **kwargs) -> int:
        """Insert a fact with complete lineage tracking."""

        cursor = self.conn.cursor() if not self.use_duckdb else self.conn

        # Prepare lineage data
        lineage_data = None
        lineage_hash = None
        source_fact_ids = None
        transformation_history = None
        dependency_graph = None

        if lineage:
            lineage_data = json.dumps(lineage.to_dict())
            lineage_hash = lineage.calculate_lineage_hash()
            source_fact_ids = json.dumps(lineage.source_facts)
            transformation_history = json.dumps(lineage.transformations)
            dependency_graph = json.dumps(lineage.dependency_graph)

        # Insert fact
        sql = """
        INSERT INTO fact_kpi_enhanced (
            entity_id, metric_name, value, period_type, period_year,
            scenario, currency, unit, source_file, source_hash, source_ref,
            is_calculated, calculation_formula, source_fact_ids,
            lineage_data, lineage_hash, transformation_history,
            dependency_graph, confidence_score
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        params = (
            entity_id, metric_name, value, period_type, period_year,
            kwargs.get('scenario', 'actual'),
            kwargs.get('currency'),
            kwargs.get('unit'),
            source_ref.file_path,
            source_ref.file_hash,
            source_ref.to_string(),
            lineage is not None,
            lineage.calculation_formula if lineage else None,
            source_fact_ids,
            lineage_data,
            lineage_hash,
            transformation_history,
            dependency_graph,
            lineage.confidence_score if lineage else 1.0
        )

        cursor.execute(sql, params)

        # Get the inserted fact ID
        fact_id = cursor.execute("SELECT last_insert_rowid()").fetchone()[0] if self.use_duckdb else cursor.lastrowid

        # Store lineage in repository
        if lineage:
            self.lineage_repo.store_lineage(fact_id, lineage)

            # Create lineage relationships
            for source_fact_id in lineage.source_facts:
                self._create_lineage_relationship(source_fact_id, fact_id, 'direct_source')

            # Log transformations
            for transformation in lineage.transformations:
                self._log_transformation(fact_id, transformation)

        if not self.use_duckdb:
            self.conn.commit()

        logger.info(f"Inserted fact {fact_id} with lineage tracking")
        return fact_id

    def _create_lineage_relationship(self, source_id: int, target_id: int, rel_type: str):
        """Create a lineage relationship between facts."""
        sql = """
        INSERT INTO lineage_relationships (
            source_fact_id, target_fact_id, relationship_type
        ) VALUES (?, ?, ?)
        """
        cursor = self.conn.cursor() if not self.use_duckdb else self.conn
        cursor.execute(sql, (source_id, target_id, rel_type))

    def _log_transformation(self, fact_id: int, transformation: dict[str, Any]):
        """Log a transformation applied to a fact."""
        sql = """
        INSERT INTO transformation_log (
            fact_id, transformation_type, transformation_params
        ) VALUES (?, ?, ?)
        """
        cursor = self.conn.cursor() if not self.use_duckdb else self.conn
        cursor.execute(sql, (
            fact_id,
            transformation.get('type', 'unknown'),
            json.dumps(transformation.get('params', {}))
        ))

    def get_fact_lineage(self, fact_id: int) -> Optional[dict[str, Any]]:
        """Get complete lineage for a fact."""

        # Get from repository first
        lineage = self.lineage_repo.get_lineage(fact_id)
        if lineage:
            return lineage.to_dict()

        # Otherwise fetch from database
        sql = """
        SELECT lineage_data, lineage_hash, source_fact_ids,
               transformation_history, dependency_graph
        FROM fact_kpi_enhanced
        WHERE fact_id = ?
        """

        cursor = self.conn.cursor() if not self.use_duckdb else self.conn
        result = cursor.execute(sql, (fact_id,)).fetchone()

        if result and result[0]:  # lineage_data
            return json.loads(result[0])

        return None

    def get_lineage_tree(self, fact_id: int, max_depth: int = 5) -> dict[str, Any]:
        """Get complete lineage tree for a fact."""
        return self.lineage_repo.get_full_lineage_tree(fact_id, max_depth)

    def get_fact_dependencies(self, fact_id: int) -> list[int]:
        """Get all facts that this fact depends on."""
        sql = """
        SELECT source_fact_id
        FROM lineage_relationships
        WHERE target_fact_id = ?
        """
        cursor = self.conn.cursor() if not self.use_duckdb else self.conn
        results = cursor.execute(sql, (fact_id,)).fetchall()
        return [row[0] for row in results]

    def get_fact_dependents(self, fact_id: int) -> list[int]:
        """Get all facts that depend on this fact."""
        sql = """
        SELECT target_fact_id
        FROM lineage_relationships
        WHERE source_fact_id = ?
        """
        cursor = self.conn.cursor() if not self.use_duckdb else self.conn
        results = cursor.execute(sql, (fact_id,)).fetchall()
        return [row[0] for row in results]

    def validate_lineage_consistency(self) -> tuple[bool, list[str]]:
        """Validate consistency of all lineage chains."""
        errors = []

        sql = "SELECT fact_id, lineage_data FROM fact_kpi_enhanced WHERE is_calculated = 1"
        cursor = self.conn.cursor() if not self.use_duckdb else self.conn
        results = cursor.execute(sql).fetchall()

        for row in results:
            fact_id = row[0]
            if row[1]:  # lineage_data
                lineage_dict = json.loads(row[1])
                # Verify source facts exist
                for source_id in lineage_dict.get('source_facts', []):
                    check_sql = "SELECT COUNT(*) FROM fact_kpi_enhanced WHERE fact_id = ?"
                    count = cursor.execute(check_sql, (source_id,)).fetchone()[0]
                    if count == 0:
                        errors.append(f"Fact {fact_id} references non-existent source {source_id}")

        return len(errors) == 0, errors

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
