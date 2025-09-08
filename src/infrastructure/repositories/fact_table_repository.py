"""Fact table repository for structured financial data storage."""

import sqlite3
import duckdb
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime, date
import json
import logging
from dataclasses import dataclass, asdict

from src.domain.value_objects.source_reference import ProvenancedValue, SourceReference


logger = logging.getLogger(__name__)

@dataclass
class FactRecord:
    """Fact record for dimensional data warehouse."""
    fact_id: str
    metric_name: str
    value: float
    entity_name: str
    period_key: str
    scenario: str
    source_reference: SourceReference
    confidence_score: float
    metadata: Dict[str, Any]
    created_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert fact record to dictionary."""
        return {
            'fact_id': self.fact_id,
            'metric_name': self.metric_name,
            'value': self.value,
            'entity_name': self.entity_name,
            'period_key': self.period_key,
            'scenario': self.scenario,
            'source_reference': self.source_reference.to_dict(),
            'confidence_score': self.confidence_score,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat()
        }


class FactTableRepository:
    """Repository for managing fact table with dimensional model."""
    
    def __init__(self, db_path: str = "data/facts.db", use_duckdb: bool = True):
        """Initialize fact table repository."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        
        self.use_duckdb = use_duckdb
        self.conn = None
        
        self._initialize_database()
        self._create_tables()
    
    def _initialize_database(self):
        """Initialize database connection."""
        try:
            if self.use_duckdb:
                # DuckDB for analytics performance
                self.conn = duckdb.connect(str(self.db_path))
                logger.info(f"Connected to DuckDB at {self.db_path}")
            else:
                # SQLite for simplicity
                self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
                self.conn.row_factory = sqlite3.Row  # Enable dict-like access
                logger.info(f"Connected to SQLite at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def _create_tables(self):
        """Create fact and dimension tables."""
        
        # Dimension tables
        dim_tables = {
            'dim_entity': '''
                CREATE TABLE IF NOT EXISTS dim_entity (
                    entity_key INTEGER PRIMARY KEY,
                    entity_id TEXT UNIQUE NOT NULL,
                    entity_name TEXT NOT NULL,
                    entity_type TEXT,  -- Company, BU, Subsidiary
                    parent_entity TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''',
            
            'dim_metric': '''
                CREATE TABLE IF NOT EXISTS dim_metric (
                    metric_key INTEGER PRIMARY KEY,
                    metric_id TEXT UNIQUE NOT NULL,
                    canonical_name TEXT NOT NULL,
                    category TEXT,
                    subcategory TEXT,
                    unit TEXT,
                    calculation_formula TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''',
            
            'dim_period': '''
                CREATE TABLE IF NOT EXISTS dim_period (
                    period_key INTEGER PRIMARY KEY,
                    period_id TEXT UNIQUE NOT NULL,
                    period_type TEXT NOT NULL,  -- FY, Q, M, YTD, CUSTOM
                    year INTEGER NOT NULL,
                    period_number INTEGER,  -- Quarter (1-4), Month (1-12)
                    start_date DATE,
                    end_date DATE,
                    display_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''',
            
            'dim_scenario': '''
                CREATE TABLE IF NOT EXISTS dim_scenario (
                    scenario_key INTEGER PRIMARY KEY,
                    scenario_id TEXT UNIQUE NOT NULL,
                    scenario_name TEXT NOT NULL,  -- Actual, Budget, Forecast, Plan
                    scenario_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''',
            
            'dim_source': '''
                CREATE TABLE IF NOT EXISTS dim_source (
                    source_key INTEGER PRIMARY KEY,
                    file_name TEXT NOT NULL,
                    file_hash TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    upload_timestamp TIMESTAMP,
                    file_size INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            '''
        }
        
        # Main fact table
        fact_table = '''
            CREATE TABLE IF NOT EXISTS fact_kpi (
                fact_id INTEGER PRIMARY KEY,
                entity_key INTEGER NOT NULL,
                metric_key INTEGER NOT NULL,
                period_key INTEGER NOT NULL,
                scenario_key INTEGER NOT NULL,
                
                -- The actual value and metadata
                value REAL NOT NULL,
                original_value TEXT,
                currency TEXT,
                unit TEXT,
                
                -- Source provenance
                source_key INTEGER NOT NULL,
                source_reference TEXT NOT NULL,  -- Detailed reference string
                page_number INTEGER,
                sheet_name TEXT,
                cell_reference TEXT,
                table_index INTEGER,
                row_label TEXT,
                column_label TEXT,
                
                -- Quality and lineage
                confidence_score REAL DEFAULT 1.0,
                is_calculated BOOLEAN DEFAULT FALSE,
                calculation_formula TEXT,
                input_sources TEXT,  -- JSON array of source fact_ids
                
                -- Quality flags  
                quality_flags TEXT,  -- JSON object with validation results
                validation_status TEXT DEFAULT 'pending',  -- pending, passed, failed, warning
                
                -- Normalization info
                scale_applied TEXT,  -- units, thousands, millions
                scale_multiplier INTEGER DEFAULT 1,
                
                -- Temporal info
                extraction_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Constraints
                FOREIGN KEY (entity_key) REFERENCES dim_entity(entity_key),
                FOREIGN KEY (metric_key) REFERENCES dim_metric(metric_key),
                FOREIGN KEY (period_key) REFERENCES dim_period(period_key),
                FOREIGN KEY (scenario_key) REFERENCES dim_scenario(scenario_key),
                FOREIGN KEY (source_key) REFERENCES dim_source(source_key),
                
                -- Business key constraint (prevent duplicates)
                UNIQUE(entity_key, metric_key, period_key, scenario_key, source_reference)
            )
        '''
        
        # Create all tables
        try:
            for table_name, create_sql in dim_tables.items():
                self.conn.execute(create_sql)
                logger.debug(f"Created/verified table: {table_name}")
            
            self.conn.execute(fact_table)
            logger.debug("Created/verified fact_kpi table")
            
            # Create indices for performance
            indices = [
                "CREATE INDEX IF NOT EXISTS idx_fact_entity ON fact_kpi(entity_key)",
                "CREATE INDEX IF NOT EXISTS idx_fact_metric ON fact_kpi(metric_key)", 
                "CREATE INDEX IF NOT EXISTS idx_fact_period ON fact_kpi(period_key)",
                "CREATE INDEX IF NOT EXISTS idx_fact_scenario ON fact_kpi(scenario_key)",
                "CREATE INDEX IF NOT EXISTS idx_fact_source ON fact_kpi(source_key)",
                "CREATE INDEX IF NOT EXISTS idx_fact_extraction_time ON fact_kpi(extraction_timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_dim_period_year ON dim_period(year)",
                "CREATE INDEX IF NOT EXISTS idx_dim_metric_category ON dim_metric(category)"
            ]
            
            for index_sql in indices:
                self.conn.execute(index_sql)
            
            # Commit if SQLite
            if not self.use_duckdb:
                self.conn.commit()
                
            logger.info("Successfully created fact and dimension tables")
            
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise
    
    def insert_provenanced_value(self, pv: ProvenancedValue) -> int:
        """Insert a provenanced value into the fact table."""
        
        # Get or create dimension keys
        entity_key = self._get_or_create_entity(pv.entity or "default")
        metric_key = self._get_or_create_metric(pv.metric_name or "unknown", pv.unit)
        period_key = self._get_or_create_period(pv.period, pv.period_start, pv.period_end)
        scenario_key = self._get_or_create_scenario(pv.scenario or "actual")
        source_key = self._get_or_create_source(pv.source_ref)
        
        # Prepare fact record
        fact_data = {
            'entity_key': entity_key,
            'metric_key': metric_key,
            'period_key': period_key,
            'scenario_key': scenario_key,
            'source_key': source_key,
            'value': float(pv.value),
            'original_value': str(pv.value),
            'currency': pv.currency,
            'unit': pv.unit,
            'source_reference': pv.source_ref.to_string(),
            'page_number': pv.source_ref.page,
            'sheet_name': pv.source_ref.sheet,
            'cell_reference': pv.source_ref.cell,
            'table_index': pv.source_ref.table_index,
            'row_label': pv.source_ref.row_label,
            'column_label': pv.source_ref.column_label,
            'confidence_score': pv.source_ref.confidence_score or 1.0,
            'is_calculated': pv.is_calculated,
            'calculation_formula': pv.calculation_formula,
            'input_sources': json.dumps(pv.input_sources) if pv.input_sources else None,
            'quality_flags': json.dumps(pv.quality_flags) if pv.quality_flags else None,
            'scale_applied': getattr(pv, 'scale_applied', 'units'),
            'scale_multiplier': 1,
            'extraction_timestamp': pv.source_ref.extraction_timestamp
        }
        
        # Insert fact record
        insert_sql = '''
            INSERT OR REPLACE INTO fact_kpi (
                entity_key, metric_key, period_key, scenario_key, source_key,
                value, original_value, currency, unit, source_reference,
                page_number, sheet_name, cell_reference, table_index, 
                row_label, column_label, confidence_score, is_calculated,
                calculation_formula, input_sources, quality_flags,
                scale_applied, scale_multiplier, extraction_timestamp
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        '''
        
        try:
            if self.use_duckdb:
                result = self.conn.execute(insert_sql, list(fact_data.values()))
            else:
                cursor = self.conn.execute(insert_sql, list(fact_data.values()))
                self.conn.commit()
                return cursor.lastrowid
            
            logger.debug(f"Inserted fact: {pv.metric_name} = {pv.value}")
            return 1  # DuckDB doesn't return rowid easily
            
        except Exception as e:
            logger.error(f"Failed to insert provenanced value: {e}")
            raise
    
    def _get_or_create_entity(self, entity_id: str) -> int:
        """Get or create entity dimension record."""
        
        # Try to find existing
        select_sql = "SELECT entity_key FROM dim_entity WHERE entity_id = ?"
        result = self.conn.execute(select_sql, [entity_id]).fetchone()
        
        if result:
            return result[0] if self.use_duckdb else result['entity_key']
        
        # Create new
        insert_sql = '''
            INSERT INTO dim_entity (entity_id, entity_name, entity_type) 
            VALUES (?, ?, ?)
        '''
        
        self.conn.execute(insert_sql, [entity_id, entity_id.title(), 'company'])
        
        if not self.use_duckdb:
            self.conn.commit()
        
        # Get the new key
        result = self.conn.execute(select_sql, [entity_id]).fetchone()
        return result[0] if self.use_duckdb else result['entity_key']
    
    def _get_or_create_metric(self, metric_name: str, unit: Optional[str] = None) -> int:
        """Get or create metric dimension record."""
        
        metric_id = metric_name.lower().replace(' ', '_')
        
        select_sql = "SELECT metric_key FROM dim_metric WHERE metric_id = ?"
        result = self.conn.execute(select_sql, [metric_id]).fetchone()
        
        if result:
            return result[0] if self.use_duckdb else result['metric_key']
        
        # Create new
        insert_sql = '''
            INSERT INTO dim_metric (metric_id, canonical_name, unit) 
            VALUES (?, ?, ?)
        '''
        
        self.conn.execute(insert_sql, [metric_id, metric_name, unit])
        
        if not self.use_duckdb:
            self.conn.commit()
        
        result = self.conn.execute(select_sql, [metric_id]).fetchone()
        return result[0] if self.use_duckdb else result['metric_key']
    
    def _get_or_create_period(self, 
                             period: Optional[str],
                             start_date: Optional[date] = None,
                             end_date: Optional[date] = None) -> int:
        """Get or create period dimension record."""
        
        period_id = period or f"custom_{start_date}_{end_date}"
        
        select_sql = "SELECT period_key FROM dim_period WHERE period_id = ?"
        result = self.conn.execute(select_sql, [period_id]).fetchone()
        
        if result:
            return result[0] if self.use_duckdb else result['period_key']
        
        # Parse period info
        if period and period.startswith('FY'):
            period_type = 'FY'
            year = int(period[2:]) if len(period) > 2 else datetime.now().year
            period_number = None
        elif period and period.startswith('Q'):
            period_type = 'Q'
            parts = period.split()
            year = int(parts[1]) if len(parts) > 1 else datetime.now().year
            period_number = int(period[1])
        else:
            period_type = 'CUSTOM'
            year = start_date.year if start_date else datetime.now().year
            period_number = None
        
        # Create new
        insert_sql = '''
            INSERT INTO dim_period (period_id, period_type, year, period_number, 
                                  start_date, end_date, display_name) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        '''
        
        self.conn.execute(insert_sql, [
            period_id, period_type, year, period_number,
            start_date, end_date, period or period_id
        ])
        
        if not self.use_duckdb:
            self.conn.commit()
        
        result = self.conn.execute(select_sql, [period_id]).fetchone()
        return result[0] if self.use_duckdb else result['period_key']
    
    def _get_or_create_scenario(self, scenario_name: str) -> int:
        """Get or create scenario dimension record."""
        
        scenario_id = scenario_name.lower()
        
        select_sql = "SELECT scenario_key FROM dim_scenario WHERE scenario_id = ?"
        result = self.conn.execute(select_sql, [scenario_id]).fetchone()
        
        if result:
            return result[0] if self.use_duckdb else result['scenario_key']
        
        # Create new
        insert_sql = '''
            INSERT INTO dim_scenario (scenario_id, scenario_name, scenario_type) 
            VALUES (?, ?, ?)
        '''
        
        self.conn.execute(insert_sql, [scenario_id, scenario_name.title(), 'financial'])
        
        if not self.use_duckdb:
            self.conn.commit()
        
        result = self.conn.execute(select_sql, [scenario_id]).fetchone()
        return result[0] if self.use_duckdb else result['scenario_key']
    
    def _get_or_create_source(self, source_ref: SourceReference) -> int:
        """Get or create source dimension record."""
        
        select_sql = "SELECT source_key FROM dim_source WHERE file_name = ? AND file_hash = ?"
        result = self.conn.execute(select_sql, [source_ref.file_name, source_ref.file_hash]).fetchone()
        
        if result:
            return result[0] if self.use_duckdb else result['source_key']
        
        # Create new
        insert_sql = '''
            INSERT INTO dim_source (file_name, file_hash, source_type, upload_timestamp) 
            VALUES (?, ?, ?, ?)
        '''
        
        self.conn.execute(insert_sql, [
            source_ref.file_name, 
            source_ref.file_hash,
            source_ref.source_type.value,
            source_ref.extraction_timestamp
        ])
        
        if not self.use_duckdb:
            self.conn.commit()
        
        result = self.conn.execute(select_sql, [source_ref.file_name, source_ref.file_hash]).fetchone()
        return result[0] if self.use_duckdb else result['source_key']
    
    def query_facts(self, 
                   entity_id: Optional[str] = None,
                   metric_ids: Optional[List[str]] = None,
                   period_ids: Optional[List[str]] = None,
                   scenario_id: Optional[str] = None,
                   limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Query facts with dimensional filters."""
        
        sql_parts = ['''
            SELECT 
                f.fact_id, f.value, f.currency, f.unit,
                e.entity_name, m.canonical_name as metric_name,
                p.display_name as period_name, s.scenario_name,
                f.source_reference, f.confidence_score,
                f.extraction_timestamp
            FROM fact_kpi f
            JOIN dim_entity e ON f.entity_key = e.entity_key  
            JOIN dim_metric m ON f.metric_key = m.metric_key
            JOIN dim_period p ON f.period_key = p.period_key
            JOIN dim_scenario s ON f.scenario_key = s.scenario_key
        ''']
        
        conditions = []
        params = []
        
        if entity_id:
            conditions.append("e.entity_id = ?")
            params.append(entity_id)
        
        if metric_ids:
            placeholders = ','.join(['?' for _ in metric_ids])
            conditions.append(f"m.metric_id IN ({placeholders})")
            params.extend(metric_ids)
        
        if period_ids:
            placeholders = ','.join(['?' for _ in period_ids])
            conditions.append(f"p.period_id IN ({placeholders})")
            params.extend(period_ids)
        
        if scenario_id:
            conditions.append("s.scenario_id = ?")
            params.append(scenario_id)
        
        if conditions:
            sql_parts.append("WHERE " + " AND ".join(conditions))
        
        sql_parts.append("ORDER BY f.extraction_timestamp DESC")
        
        if limit:
            sql_parts.append(f"LIMIT {limit}")
        
        query_sql = " ".join(sql_parts)
        
        try:
            results = self.conn.execute(query_sql, params).fetchall()
            
            # Convert to dict format
            if self.use_duckdb:
                columns = [desc[0] for desc in self.conn.description]
                return [dict(zip(columns, row)) for row in results]
            else:
                return [dict(row) for row in results]
                
        except Exception as e:
            logger.error(f"Failed to query facts: {e}")
            return []
    
    def get_metrics_summary(self, entity_id: Optional[str] = None) -> Dict[str, Any]:
        """Get summary statistics for stored metrics."""
        
        base_sql = '''
            SELECT 
                m.category,
                m.canonical_name,
                COUNT(*) as fact_count,
                MIN(f.value) as min_value,
                MAX(f.value) as max_value,
                AVG(f.value) as avg_value,
                AVG(f.confidence_score) as avg_confidence
            FROM fact_kpi f
            JOIN dim_metric m ON f.metric_key = m.metric_key
            JOIN dim_entity e ON f.entity_key = e.entity_key
        '''
        
        if entity_id:
            base_sql += " WHERE e.entity_id = ?"
            params = [entity_id]
        else:
            params = []
        
        base_sql += " GROUP BY m.category, m.canonical_name ORDER BY m.category, fact_count DESC"
        
        try:
            results = self.conn.execute(base_sql, params).fetchall()
            
            summary = {
                'total_metrics': len(results),
                'by_category': {},
                'metrics': []
            }
            
            for row in results:
                if self.use_duckdb:
                    row_dict = dict(zip([desc[0] for desc in self.conn.description], row))
                else:
                    row_dict = dict(row)
                
                category = row_dict['category']
                if category not in summary['by_category']:
                    summary['by_category'][category] = []
                
                summary['by_category'][category].append(row_dict)
                summary['metrics'].append(row_dict)
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get metrics summary: {e}")
            return {'error': str(e)}
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit.""" 
        self.close()