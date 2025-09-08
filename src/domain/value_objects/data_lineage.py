"""Data lineage tracking for complete traceability of derived metrics."""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import json
import hashlib


class TransformationType(Enum):
    """Types of data transformations."""
    RAW_EXTRACTION = "raw_extraction"
    NORMALIZATION = "normalization"
    CALCULATION = "calculation"
    AGGREGATION = "aggregation"
    VALIDATION = "validation"
    CURRENCY_CONVERSION = "currency_conversion"
    SCALE_ADJUSTMENT = "scale_adjustment"
    PERIOD_ALIGNMENT = "period_alignment"


@dataclass
class LineageNode:
    """Represents a node in the data lineage graph."""
    
    fact_id: Optional[int] = None
    metric_name: str = ""
    value: Optional[float] = None
    source_ref: str = ""
    transformation: Optional[TransformationType] = None
    timestamp: datetime = field(default_factory=datetime.now)
    confidence: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'fact_id': self.fact_id,
            'metric_name': self.metric_name,
            'value': self.value,
            'source_ref': self.source_ref,
            'transformation': self.transformation.value if self.transformation else None,
            'timestamp': self.timestamp.isoformat(),
            'confidence': self.confidence
        }


@dataclass
class DataLineage:
    """Complete lineage tracking for a calculated metric."""
    
    # Core lineage information
    target_metric: str
    target_value: float
    calculation_formula: str
    
    # Source facts used in calculation
    source_facts: List[int] = field(default_factory=list)  # List of fact IDs
    source_nodes: List[LineageNode] = field(default_factory=list)
    
    # Transformation history
    transformations: List[Dict[str, Any]] = field(default_factory=list)
    
    # Metadata
    calculated_at: datetime = field(default_factory=datetime.now)
    confidence_score: float = 1.0
    calculation_method: str = "direct"  # direct, derived, estimated
    
    # Dependency graph (for complex calculations)
    dependency_graph: Dict[str, List[str]] = field(default_factory=dict)
    
    def add_source_fact(self, fact_id: int, metric_name: str, value: float, source_ref: str):
        """Add a source fact to the lineage."""
        self.source_facts.append(fact_id)
        self.source_nodes.append(LineageNode(
            fact_id=fact_id,
            metric_name=metric_name,
            value=value,
            source_ref=source_ref
        ))
    
    def add_transformation(self, 
                         trans_type: TransformationType,
                         description: str,
                         params: Optional[Dict[str, Any]] = None):
        """Record a transformation applied to the data."""
        self.transformations.append({
            'type': trans_type.value,
            'description': description,
            'params': params or {},
            'timestamp': datetime.now().isoformat()
        })
    
    def calculate_lineage_hash(self) -> str:
        """Generate a unique hash for this lineage chain."""
        lineage_string = json.dumps({
            'formula': self.calculation_formula,
            'sources': sorted(self.source_facts),
            'transformations': [t['type'] for t in self.transformations]
        }, sort_keys=True)
        return hashlib.sha256(lineage_string.encode()).hexdigest()[:12]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert lineage to dictionary for storage."""
        return {
            'target_metric': self.target_metric,
            'target_value': self.target_value,
            'calculation_formula': self.calculation_formula,
            'source_facts': self.source_facts,
            'source_nodes': [node.to_dict() for node in self.source_nodes],
            'transformations': self.transformations,
            'calculated_at': self.calculated_at.isoformat(),
            'confidence_score': self.confidence_score,
            'calculation_method': self.calculation_method,
            'dependency_graph': self.dependency_graph,
            'lineage_hash': self.calculate_lineage_hash()
        }
    
    def get_lineage_chain(self) -> str:
        """Get human-readable lineage chain."""
        chain_parts = []
        
        # Add sources
        for node in self.source_nodes:
            chain_parts.append(f"{node.metric_name}={node.value} (fact#{node.fact_id})")
        
        # Add formula
        chain_parts.append(f"→ [{self.calculation_formula}]")
        
        # Add transformations
        for trans in self.transformations:
            chain_parts.append(f"→ {trans['type']}")
        
        # Add result
        chain_parts.append(f"→ {self.target_metric}={self.target_value}")
        
        return " ".join(chain_parts)
    
    def validate_lineage(self) -> tuple[bool, List[str]]:
        """Validate the lineage chain for consistency."""
        errors = []
        
        # Check that all source facts exist
        if not self.source_facts and self.calculation_method != "direct":
            errors.append("No source facts for derived metric")
        
        # Check confidence score
        if self.confidence_score < 0 or self.confidence_score > 1:
            errors.append(f"Invalid confidence score: {self.confidence_score}")
        
        # Check that formula references all sources
        for node in self.source_nodes:
            if node.metric_name not in self.calculation_formula:
                errors.append(f"Source {node.metric_name} not in formula")
        
        return len(errors) == 0, errors


@dataclass
class LineageRepository:
    """Repository for storing and querying lineage information."""
    
    lineages: Dict[int, DataLineage] = field(default_factory=dict)
    
    def store_lineage(self, fact_id: int, lineage: DataLineage):
        """Store lineage for a fact."""
        self.lineages[fact_id] = lineage
    
    def get_lineage(self, fact_id: int) -> Optional[DataLineage]:
        """Retrieve lineage for a fact."""
        return self.lineages.get(fact_id)
    
    def get_dependencies(self, fact_id: int) -> List[int]:
        """Get all facts that this fact depends on."""
        lineage = self.get_lineage(fact_id)
        if lineage:
            return lineage.source_facts
        return []
    
    def get_dependents(self, fact_id: int) -> List[int]:
        """Get all facts that depend on this fact."""
        dependents = []
        for fid, lineage in self.lineages.items():
            if fact_id in lineage.source_facts:
                dependents.append(fid)
        return dependents
    
    def get_full_lineage_tree(self, fact_id: int, max_depth: int = 5) -> Dict[str, Any]:
        """Get complete lineage tree for a fact."""
        def build_tree(fid: int, depth: int = 0) -> Dict[str, Any]:
            if depth >= max_depth:
                return {'fact_id': fid, 'truncated': True}
            
            lineage = self.get_lineage(fid)
            if not lineage:
                return {'fact_id': fid, 'no_lineage': True}
            
            return {
                'fact_id': fid,
                'metric': lineage.target_metric,
                'value': lineage.target_value,
                'formula': lineage.calculation_formula,
                'sources': [build_tree(src_id, depth + 1) for src_id in lineage.source_facts],
                'transformations': lineage.transformations,
                'confidence': lineage.confidence_score
            }
        
        return build_tree(fact_id)