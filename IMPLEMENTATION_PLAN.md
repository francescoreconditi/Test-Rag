# 🚀 Piano di Implementazione - Componenti Mancanti
## Sistema RAG Enterprise - Gap Analysis Follow-up

---

## 🎯 Panoramica Strategica

**Obiettivo**: Portare il sistema RAG da **85% coverage** a **production-grade enterprise readiness (98%)**

**Timeline**: 6-8 settimane di sviluppo  
**Resources**: 1 Senior Developer + DevOps support  
**Budget Impact**: Medio (principalmente tempo sviluppo)

---

## 📋 Piano di Implementazione - Fase per Fase

### 🔴 **FASE 1: SECURITY & COMPLIANCE CRITICAL (P0)**
**Timeline**: 3-4 settimane  
**Risk**: ALTO - Blocca deployment enterprise

#### 1.1 Encryption at Rest & Transit
**Files da creare/modificare**:
- `src/core/security/encryption_service.py`
- `src/infrastructure/repositories/encrypted_fact_table.py`  
- `src/core/config.py` (encryption settings)

**Implementazione**:
```python
# src/core/security/encryption_service.py
from cryptography.fernet import Fernet
from typing import Union, Dict, Any
import base64
import os

class EncryptionService:
    def __init__(self, key: bytes = None):
        self.key = key or self._generate_key()
        self.cipher = Fernet(self.key)
    
    def encrypt_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt PII fields in data dictionary."""
        sensitive_fields = ['cf', 'iban', 'email', 'phone']
        encrypted_data = data.copy()
        
        for field in sensitive_fields:
            if field in data and data[field]:
                encrypted_data[field] = self.cipher.encrypt(
                    str(data[field]).encode()
                ).decode()
        
        return encrypted_data
    
    def encrypt_fact_value(self, value: float, metadata: Dict) -> str:
        """Encrypt fact table sensitive values."""
        if metadata.get('is_sensitive', False):
            return self.cipher.encrypt(str(value).encode()).decode()
        return str(value)
```

**Effort**: 1.5 settimane

#### 1.2 PII Detection & Masking
**Files da creare**:
- `src/core/security/pii_detector.py`
- `src/core/security/data_masking.py`

**Implementazione**:
```python
# src/core/security/pii_detector.py
import re
from typing import Dict, List, Any

class PIIDetector:
    def __init__(self):
        self.patterns = {
            'italian_cf': r'[A-Z]{6}[0-9]{2}[A-Z][0-9]{2}[A-Z][0-9]{3}[A-Z]',
            'iban': r'[A-Z]{2}[0-9]{2}[A-Z0-9]{4}[0-9]{7}[A-Z0-9]{12}',
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'(\+39)?[\s.-]?([0-9]{2,3})[\s.-]?([0-9]{6,7})',
            'vat_number': r'IT[0-9]{11}'
        }
    
    def detect_pii_in_text(self, text: str) -> Dict[str, List[str]]:
        """Detect PII patterns in text."""
        detected = {}
        for pii_type, pattern in self.patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                detected[pii_type] = matches
        return detected
    
    def mask_text(self, text: str) -> str:
        """Mask PII in text for logging."""
        masked_text = text
        for pii_type, pattern in self.patterns.items():
            masked_text = re.sub(pattern, f'***{pii_type.upper()}***', masked_text)
        return masked_text
```

**Effort**: 1 settimana

#### 1.3 Access Control & Row-Level Security
**Files da creare**:
- `src/core/security/access_control.py`
- `src/infrastructure/repositories/secure_fact_table.py`

**Implementazione**:
```python
# src/core/security/access_control.py
from enum import Enum
from typing import List, Dict, Optional
from dataclasses import dataclass

class UserRole(Enum):
    ADMIN = "admin"
    ANALYST = "analyst" 
    VIEWER = "viewer"
    BU_MANAGER = "bu_manager"

@dataclass
class UserContext:
    user_id: str
    role: UserRole
    accessible_entities: List[str]  # Company/BU access
    accessible_periods: List[str]   # Time period access
    data_classification_level: int  # 1=Public, 2=Internal, 3=Confidential

class AccessControlService:
    def __init__(self):
        self.role_permissions = {
            UserRole.ADMIN: ['read', 'write', 'delete', 'manage'],
            UserRole.ANALYST: ['read', 'write'],
            UserRole.VIEWER: ['read'],
            UserRole.BU_MANAGER: ['read', 'write']  # Limited to own BU
        }
    
    def can_access_entity(self, user: UserContext, entity_id: str) -> bool:
        """Check if user can access specific entity data."""
        return (user.role == UserRole.ADMIN or 
                entity_id in user.accessible_entities)
    
    def filter_query_results(self, results: List[Dict], user: UserContext) -> List[Dict]:
        """Filter query results based on user permissions."""
        filtered = []
        for result in results:
            if self.can_access_entity(user, result.get('entity_id', '')):
                filtered.append(self._mask_sensitive_fields(result, user))
        return filtered
```

**Effort**: 1.5 settimane

---

### 🟡 **FASE 2: DATA GOVERNANCE & QUALITY (P1)**  
**Timeline**: 2-3 settimane  
**Risk**: MEDIO - Migliora qualità ma non blocca deployment

#### 2.1 Deduplication & Conflict Resolution
**Files da creare**:
- `src/domain/services/deduplication_engine.py`
- `src/domain/services/conflict_resolution.py`

**Implementazione**:
```python
# src/domain/services/deduplication_engine.py
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import hashlib

@dataclass
class DuplicateCandidate:
    metric_name: str
    period: str
    entity: str
    perimeter: str
    scenario: str
    values: List[Tuple[float, str, float]]  # (value, source_ref, confidence)
    
class DeduplicationEngine:
    def __init__(self):
        self.truth_criteria_weights = {
            'recency': 0.4,      # More recent data preferred
            'specificity': 0.3,   # More specific labels preferred  
            'source_quality': 0.2, # Known good sources
            'confidence': 0.1     # Extraction confidence
        }
    
    def find_duplicates(self, facts: List[Dict[str, Any]]) -> List[DuplicateCandidate]:
        """Find potential duplicate facts."""
        grouped = {}
        
        for fact in facts:
            key = self._create_dedup_key(fact)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(fact)
        
        duplicates = []
        for key, fact_group in grouped.items():
            if len(fact_group) > 1:
                duplicates.append(self._create_duplicate_candidate(fact_group))
        
        return duplicates
    
    def resolve_conflicts(self, candidate: DuplicateCandidate) -> Tuple[float, str, Dict]:
        """Resolve conflicts using truth criteria."""
        best_value = None
        best_source = None
        best_score = -1
        resolution_details = {}
        
        for value, source_ref, confidence in candidate.values:
            score = self._calculate_truth_score(value, source_ref, confidence)
            
            if score > best_score:
                best_score = score
                best_value = value
                best_source = source_ref
        
        resolution_details = {
            'resolution_method': 'weighted_scoring',
            'criteria_weights': self.truth_criteria_weights,
            'final_score': best_score,
            'alternatives_count': len(candidate.values) - 1
        }
        
        return best_value, best_source, resolution_details
```

**Effort**: 2 settimane

#### 2.2 Advanced Dimensional Coherence
**Files da creare**:
- `src/domain/services/dimensional_validator.py`

**Implementazione**:
```python
# src/domain/services/dimensional_validator.py
from typing import List, Dict, Any, Set
from dataclasses import dataclass

@dataclass
class CoherenceRule:
    name: str
    description: str
    affected_metrics: List[str]
    validation_function: callable
    severity: str  # 'error', 'warning', 'info'

class DimensionalValidator:
    def __init__(self):
        self.coherence_rules = [
            CoherenceRule(
                name="same_period_calculation",
                description="Calculated metrics must use same period inputs",
                affected_metrics=["margine_lordo", "ebitda_margin"],
                validation_function=self._validate_same_period,
                severity="error"
            ),
            CoherenceRule(
                name="same_perimeter_calculation", 
                description="Financial ratios must use same perimeter",
                affected_metrics=["roe", "roa", "debt_equity"],
                validation_function=self._validate_same_perimeter,
                severity="error"
            )
        ]
    
    def validate_dimensional_coherence(self, facts: List[Dict]) -> List[Dict]:
        """Validate dimensional coherence across related facts."""
        violations = []
        
        for rule in self.coherence_rules:
            affected_facts = [f for f in facts 
                            if f.get('metric_name') in rule.affected_metrics]
            
            if len(affected_facts) > 1:
                rule_violations = rule.validation_function(affected_facts)
                for violation in rule_violations:
                    violations.append({
                        'rule_name': rule.name,
                        'severity': rule.severity,
                        'description': rule.description,
                        'violation_details': violation
                    })
        
        return violations
```

**Effort**: 1 settimana

---

### 🟢 **FASE 3: MONITORING & MLOPS (P2)**
**Timeline**: 2-3 settimane  
**Risk**: BASSO - Migliora osservabilità

#### 3.1 Gold Standard Benchmarking
**Files da creare**:
- `src/domain/services/quality_benchmark.py`
- `data/gold_standard/financial_metrics_gold.yaml`
- `tests/benchmarks/extraction_accuracy_test.py`

**Implementazione**:
```python
# src/domain/services/quality_benchmark.py
from typing import Dict, List, Any, Tuple
import yaml
import pandas as pd
from pathlib import Path

class QualityBenchmark:
    def __init__(self, gold_standard_path: str):
        self.gold_standard = self._load_gold_standard(gold_standard_path)
        self.metrics = {}
    
    def _load_gold_standard(self, path: str) -> Dict:
        """Load gold standard test cases."""
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def benchmark_extraction_accuracy(self, extracted_facts: List[Dict]) -> Dict[str, float]:
        """Benchmark extraction accuracy against gold standard."""
        precision_scores = []
        recall_scores = []
        f1_scores = []
        
        for test_case in self.gold_standard['test_cases']:
            expected = test_case['expected_metrics']
            actual = self._filter_facts_for_document(
                extracted_facts, test_case['document_path']
            )
            
            precision = self._calculate_precision(expected, actual)
            recall = self._calculate_recall(expected, actual)
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            
            precision_scores.append(precision)
            recall_scores.append(recall)  
            f1_scores.append(f1)
        
        return {
            'precision_avg': sum(precision_scores) / len(precision_scores),
            'recall_avg': sum(recall_scores) / len(recall_scores),
            'f1_avg': sum(f1_scores) / len(f1_scores),
            'test_cases_count': len(self.gold_standard['test_cases'])
        }
    
    def track_model_performance(self, model_name: str, metrics: Dict[str, float]):
        """Track ML model performance over time."""
        timestamp = datetime.now().isoformat()
        
        if model_name not in self.metrics:
            self.metrics[model_name] = []
        
        self.metrics[model_name].append({
            'timestamp': timestamp,
            'metrics': metrics
        })
        
        # Save to persistent storage
        self._save_performance_metrics()
```

**Gold Standard YAML Example**:
```yaml
# data/gold_standard/financial_metrics_gold.yaml
test_cases:
  - document_path: "test_documents/bilancio_2023_sample.pdf"
    expected_metrics:
      - metric_name: "ricavi"
        expected_value: 5000000.0
        unit: "EUR"
        tolerance: 0.01
        source_page: 12
      - metric_name: "ebitda"
        expected_value: 800000.0  
        unit: "EUR"
        tolerance: 0.01
        source_page: 12
        
  - document_path: "test_documents/ce_excel_sample.xlsx"
    expected_metrics:
      - metric_name: "cogs"
        expected_value: 3200000.0
        unit: "EUR"
        tolerance: 0.01
        source_sheet: "Conto Economico"
        source_cell: "B15"
```

**Effort**: 2 settimane

#### 3.2 Data Versioning con DVC
**Files da creare**:
- `.dvc/config`
- `dvc.yaml` (pipeline definition)
- `src/infrastructure/versioning/dvc_manager.py`

**Implementazione**:
```python
# src/infrastructure/versioning/dvc_manager.py
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

class DVCManager:
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        self.dvc_dir = self.repo_path / ".dvc"
        
    def init_dvc_repo(self):
        """Initialize DVC repository."""
        if not self.dvc_dir.exists():
            subprocess.run(["dvc", "init"], cwd=self.repo_path, check=True)
    
    def add_dataset(self, data_path: str, remote_name: str = "origin") -> str:
        """Add dataset to DVC tracking."""
        result = subprocess.run(
            ["dvc", "add", data_path], 
            cwd=self.repo_path, 
            capture_output=True, 
            text=True,
            check=True
        )
        
        # Commit the .dvc file to git
        dvc_file = f"{data_path}.dvc"
        subprocess.run(["git", "add", dvc_file], cwd=self.repo_path)
        
        return dvc_file
    
    def create_model_snapshot(self, model_artifacts: Dict[str, str], 
                            version_tag: str) -> Dict[str, str]:
        """Create versioned snapshot of model artifacts."""
        snapshot_info = {
            'timestamp': datetime.now().isoformat(),
            'version_tag': version_tag,
            'artifacts': {}
        }
        
        for artifact_name, artifact_path in model_artifacts.items():
            dvc_file = self.add_dataset(artifact_path)
            snapshot_info['artifacts'][artifact_name] = {
                'path': artifact_path,
                'dvc_file': dvc_file
            }
        
        # Save snapshot metadata
        snapshot_file = f"snapshots/{version_tag}_snapshot.json"
        with open(snapshot_file, 'w') as f:
            json.dump(snapshot_info, f, indent=2)
        
        subprocess.run(["git", "add", snapshot_file], cwd=self.repo_path)
        subprocess.run([
            "git", "commit", "-m", f"Model snapshot {version_tag}"
        ], cwd=self.repo_path)
        
        return snapshot_info
```

**Effort**: 1 settimana

---

## 📊 Priorità e Timeline Consolidate

### **Sprint 1 (Settimane 1-2): Security Foundation**
- 🔴 Encryption Service Implementation  
- 🔴 PII Detection & Masking
- 🔴 Basic Access Control

**Deliverables**:
- Encrypted fact table storage
- PII-safe logging
- Role-based data filtering

### **Sprint 2 (Settimane 3-4): Advanced Security & Governance**  
- 🔴 Row-level Security Implementation
- 🟡 Deduplication Engine
- 🟡 Conflict Resolution

**Deliverables**:
- Multi-tenant ready architecture
- Automated duplicate detection
- Truth criteria resolution

### **Sprint 3 (Settimane 5-6): Quality & Monitoring**
- 🟡 Dimensional Coherence Validation
- 🟢 Gold Standard Benchmarking
- 🟢 DVC Integration

**Deliverables**:
- Advanced data quality rules
- ML model performance tracking  
- Data/model versioning pipeline

---

## 🎯 Success Criteria

### **Phase 1 Complete (Security)**
- [ ] All sensitive data encrypted at rest
- [ ] PII automatically detected and masked in logs
- [ ] Row-level security enforces data isolation
- [ ] Security audit passes with zero critical findings

### **Phase 2 Complete (Governance)**  
- [ ] <1% false positive rate in duplicate detection
- [ ] Conflict resolution achieves >95% accuracy vs manual review
- [ ] Dimensional coherence violations caught automatically

### **Phase 3 Complete (Monitoring)**
- [ ] Baseline accuracy metrics established on gold standard
- [ ] Model performance tracked with <5% degradation alerts
- [ ] Complete data lineage from raw input to final output

### **Production Readiness Achieved**
- [ ] **Coverage**: >98% of analisi.md requirements implemented
- [ ] **Security**: SOX/GDPR compliance ready
- [ ] **Quality**: Automated data quality monitoring
- [ ] **Observability**: Full ML/data pipeline monitoring  
- [ ] **Governance**: Audit trail and data lineage complete

---

## 💰 Resource Requirements & Cost Estimate

### **Human Resources**
- **1x Senior Python Developer**: 6-8 settimane full-time
- **0.5x DevOps Engineer**: 2-3 settimane (security setup, monitoring)
- **0.2x Data Architect**: 1 settimana (review e validation)

### **Infrastructure**
- **Secure Storage**: Encrypted database backend (+20% storage cost)
- **Monitoring Stack**: Prometheus/Grafana setup (cloud ~$200/month)
- **DVC Remote Storage**: S3/GCS for model artifacts (~$100/month)

### **Total Effort Estimate**: 7-10 person-weeks
### **Timeline**: 6-8 calendar weeks (with 1 dev)

---

**Con questo piano di implementazione, il sistema RAG raggiungerà production-grade enterprise readiness con compliance, governance e monitoring di livello aziendale.**