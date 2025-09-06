"""Ontology mapper for automatic metric synonym resolution."""

import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import re
try:
    from rapidfuzz import fuzz, process
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    try:
        from fuzzywuzzy import fuzz, process
        RAPIDFUZZ_AVAILABLE = True
    except ImportError:
        RAPIDFUZZ_AVAILABLE = False
import logging


logger = logging.getLogger(__name__)


class OntologyMapper:
    """Maps financial terms to canonical metrics using ontology and fuzzy matching."""
    
    def __init__(self, ontology_path: str = "config/ontology/financial_metrics.yaml"):
        """Initialize ontology mapper."""
        self.ontology_path = Path(ontology_path)
        self.ontology: Dict[str, Any] = {}
        self.synonym_index: Dict[str, str] = {}  # synonym -> canonical_metric
        self.canonical_metrics: Dict[str, Dict] = {}  # metric -> details
        
        self._load_ontology()
        self._build_synonym_index()
        
    def _load_ontology(self) -> None:
        """Load financial metrics ontology from YAML."""
        try:
            if not self.ontology_path.exists():
                logger.warning(f"Ontology file not found: {self.ontology_path}")
                return
                
            with open(self.ontology_path, 'r', encoding='utf-8') as f:
                self.ontology = yaml.safe_load(f) or {}
                
            logger.info(f"Loaded ontology with {len(self.ontology)} canonical metrics")
            
        except Exception as e:
            logger.error(f"Failed to load ontology: {e}")
            self.ontology = {}
    
    def _build_synonym_index(self) -> None:
        """Build reverse index from synonyms to canonical metrics."""
        self.synonym_index = {}
        self.canonical_metrics = {}
        
        for metric_key, metric_data in self.ontology.items():
            if not isinstance(metric_data, dict):
                continue
                
            canonical_name = metric_data.get('canonical_name', metric_key)
            self.canonical_metrics[metric_key] = metric_data
            
            # Add the canonical key itself
            self.synonym_index[metric_key.lower()] = metric_key
            self.synonym_index[canonical_name.lower()] = metric_key
            
            # Add all synonyms
            synonyms = metric_data.get('synonyms', [])
            for synonym in synonyms:
                if isinstance(synonym, str):
                    clean_synonym = self._clean_text(synonym)
                    self.synonym_index[clean_synonym] = metric_key
            
            # Add Italian synonyms
            italian_synonyms = metric_data.get('italian_synonyms', [])
            for synonym in italian_synonyms:
                if isinstance(synonym, str):
                    clean_synonym = self._clean_text(synonym)
                    self.synonym_index[clean_synonym] = metric_key
            
            # Add English synonyms  
            english_synonyms = metric_data.get('english_synonyms', [])
            for synonym in english_synonyms:
                if isinstance(synonym, str):
                    clean_synonym = self._clean_text(synonym)
                    self.synonym_index[clean_synonym] = metric_key
        
        logger.info(f"Built synonym index with {len(self.synonym_index)} entries")
    
    def _clean_text(self, text: str) -> str:
        """Clean text for matching."""
        if not text:
            return ""
        
        # Convert to lowercase
        clean = text.lower()
        
        # Remove special characters but keep spaces
        clean = re.sub(r'[^\w\s%€$]', ' ', clean)
        
        # Normalize whitespace
        clean = re.sub(r'\s+', ' ', clean).strip()
        
        return clean
    
    def map_metric(self, 
                  input_text: str, 
                  threshold: float = 70.0,
                  use_fuzzy: bool = True) -> Optional[Tuple[str, str, float]]:
        """
        Map input text to canonical metric.
        
        Returns:
            Tuple of (canonical_key, canonical_name, confidence_score) or None
        """
        if not input_text:
            return None
            
        clean_input = self._clean_text(input_text)
        
        # Direct exact match
        if clean_input in self.synonym_index:
            metric_key = self.synonym_index[clean_input]
            canonical_name = self.canonical_metrics[metric_key].get('canonical_name', metric_key)
            return (metric_key, canonical_name, 100.0)
        
        # Fuzzy matching if enabled and available
        if use_fuzzy and RAPIDFUZZ_AVAILABLE:
            return self._fuzzy_match(clean_input, threshold)
            
        return None
    
    def _fuzzy_match(self, 
                    clean_input: str, 
                    threshold: float = 70.0) -> Optional[Tuple[str, str, float]]:
        """Perform fuzzy matching against synonym index."""
        if not clean_input or not self.synonym_index or not RAPIDFUZZ_AVAILABLE:
            return None
            
        # Use rapidfuzz for fast fuzzy matching
        result = process.extractOne(
            clean_input, 
            self.synonym_index.keys(),
            scorer=fuzz.WRatio,  # Weighted ratio for better results
            score_cutoff=threshold
        )
        
        if result:
            matched_synonym, score, _ = result
            metric_key = self.synonym_index[matched_synonym]
            canonical_name = self.canonical_metrics[metric_key].get('canonical_name', metric_key)
            
            logger.debug(f"Fuzzy match: '{clean_input}' -> '{matched_synonym}' -> '{canonical_name}' (score: {score:.1f})")
            return (metric_key, canonical_name, float(score))
        
        return None
    
    def batch_map_metrics(self, 
                         input_texts: List[str],
                         threshold: float = 70.0) -> Dict[str, Optional[Tuple[str, str, float]]]:
        """Map multiple texts to canonical metrics."""
        results = {}
        
        for text in input_texts:
            mapping = self.map_metric(text, threshold)
            results[text] = mapping
        
        return results
    
    def get_metric_details(self, metric_key: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a canonical metric."""
        return self.canonical_metrics.get(metric_key)
    
    def get_metrics_by_category(self, category: str) -> List[str]:
        """Get all metrics in a specific category."""
        metrics = []
        
        for metric_key, metric_data in self.canonical_metrics.items():
            if metric_data.get('category') == category:
                metrics.append(metric_key)
        
        return metrics
    
    def get_calculable_metrics(self) -> Dict[str, str]:
        """Get metrics that can be calculated from other metrics."""
        calculable = {}
        
        for metric_key, metric_data in self.canonical_metrics.items():
            if 'calculation' in metric_data:
                calculable[metric_key] = metric_data['calculation']
        
        return calculable
    
    def suggest_metrics(self, 
                       partial_text: str, 
                       top_k: int = 5,
                       min_score: float = 50.0) -> List[Tuple[str, str, float]]:
        """Suggest possible metrics based on partial input."""
        if not partial_text:
            return []
            
        clean_input = self._clean_text(partial_text)
        
        # Get top matches using fuzzy search
        matches = process.extract(
            clean_input,
            self.synonym_index.keys(),
            scorer=fuzz.partial_ratio,  # Partial matching for suggestions
            limit=top_k * 2  # Get more to filter
        )
        
        suggestions = []
        seen_metrics = set()
        
        for match_text, score, _ in matches:
            if score < min_score:
                continue
                
            metric_key = self.synonym_index[match_text]
            
            # Avoid duplicate metrics
            if metric_key in seen_metrics:
                continue
                
            seen_metrics.add(metric_key)
            canonical_name = self.canonical_metrics[metric_key].get('canonical_name', metric_key)
            suggestions.append((metric_key, canonical_name, float(score)))
            
            if len(suggestions) >= top_k:
                break
        
        return suggestions
    
    def validate_calculation(self, 
                            metric_key: str, 
                            available_metrics: List[str]) -> Tuple[bool, List[str]]:
        """
        Check if a calculated metric can be computed from available metrics.
        
        Returns:
            Tuple of (can_calculate, missing_dependencies)
        """
        metric_data = self.get_metric_details(metric_key)
        if not metric_data or 'calculation' not in metric_data:
            return (False, [])
        
        formula = metric_data['calculation']
        
        # Extract metric names from formula (simple regex approach)
        # This is a simplified parser - could be enhanced with a proper expression parser
        metric_names = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', formula)
        
        missing = []
        for required_metric in metric_names:
            if required_metric not in available_metrics:
                missing.append(required_metric)
        
        can_calculate = len(missing) == 0
        return (can_calculate, missing)
    
    def get_category_hierarchy(self) -> Dict[str, Dict[str, List[str]]]:
        """Get metrics organized by category and subcategory."""
        hierarchy = {}
        
        for metric_key, metric_data in self.canonical_metrics.items():
            category = metric_data.get('category', 'unknown')
            subcategory = metric_data.get('subcategory', 'general')
            
            if category not in hierarchy:
                hierarchy[category] = {}
            if subcategory not in hierarchy[category]:
                hierarchy[category][subcategory] = []
            
            hierarchy[category][subcategory].append(metric_key)
        
        return hierarchy
    
    def export_mapping_report(self, 
                             mapped_metrics: Dict[str, Optional[Tuple[str, str, float]]],
                             output_file: Optional[str] = None) -> str:
        """Export mapping results to a report."""
        report_lines = []
        report_lines.append("# Metric Mapping Report")
        report_lines.append(f"Generated: {pd.Timestamp.now()}")
        report_lines.append("")
        
        # Summary
        total = len(mapped_metrics)
        mapped = sum(1 for v in mapped_metrics.values() if v is not None)
        unmapped = total - mapped
        
        report_lines.append(f"## Summary")
        report_lines.append(f"- Total inputs: {total}")
        report_lines.append(f"- Successfully mapped: {mapped} ({mapped/total*100:.1f}%)")
        report_lines.append(f"- Unmapped: {unmapped} ({unmapped/total*100:.1f}%)")
        report_lines.append("")
        
        # Successful mappings
        report_lines.append("## Successful Mappings")
        for input_text, mapping in mapped_metrics.items():
            if mapping:
                metric_key, canonical_name, score = mapping
                report_lines.append(f"- `{input_text}` → `{canonical_name}` (confidence: {score:.1f}%)")
        
        report_lines.append("")
        
        # Failed mappings
        report_lines.append("## Failed Mappings")
        for input_text, mapping in mapped_metrics.items():
            if not mapping:
                suggestions = self.suggest_metrics(input_text, top_k=3)
                report_lines.append(f"- `{input_text}` (no match)")
                if suggestions:
                    report_lines.append("  Suggestions:")
                    for _, name, score in suggestions:
                        report_lines.append(f"    - {name} ({score:.1f}%)")
        
        report_content = "\n".join(report_lines)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
            logger.info(f"Mapping report saved to {output_file}")
        
        return report_content
    
    def reload_ontology(self) -> None:
        """Reload ontology from file (useful for hot-reloading)."""
        self._load_ontology()
        self._build_synonym_index()
        logger.info("Ontology reloaded")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get ontology statistics."""
        categories = set()
        subcategories = set()
        units = set()
        
        for metric_data in self.canonical_metrics.values():
            if 'category' in metric_data:
                categories.add(metric_data['category'])
            if 'subcategory' in metric_data:
                subcategories.add(metric_data['subcategory'])
            if 'unit' in metric_data:
                units.add(metric_data['unit'])
        
        calculable_count = sum(1 for data in self.canonical_metrics.values() 
                             if 'calculation' in data)
        
        return {
            'total_canonical_metrics': len(self.canonical_metrics),
            'total_synonyms': len(self.synonym_index),
            'categories': list(categories),
            'subcategories': list(subcategories),
            'units': list(units),
            'calculable_metrics': calculable_count
        }