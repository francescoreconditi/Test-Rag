#!/usr/bin/env python3
"""Test script for extended ontology with new domain metrics."""

from src.application.services.ontology_mapper import OntologyMapper
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_extended_ontology():
    """Test the extended ontology with new AR/AP, Sales, Inventory, and HR metrics."""
    
    # Initialize mapper with extended ontology
    mapper = OntologyMapper("config/ontology/financial_metrics.yaml")
    
    print("Testing Extended Financial Ontology")
    print("=" * 50)
    
    # Test basic stats
    stats = mapper.get_stats()
    print(f"Ontology Statistics:")
    print(f"   - Total canonical metrics: {stats['total_canonical_metrics']}")
    print(f"   - Total synonyms: {stats['total_synonyms']}")
    print(f"   - Categories: {', '.join(stats['categories'])}")
    print(f"   - Calculable metrics: {stats['calculable_metrics']}")
    print()
    
    # Test AR/AP metrics
    print("Testing AR/AP Metrics:")
    ar_ap_tests = [
        "giorni medi di incasso",
        "DSO", 
        "tempo medio pagamento",
        "crediti correnti",
        "fondo svalutazione crediti",
        "turnover crediti"
    ]
    
    for term in ar_ap_tests:
        result = mapper.map_metric(term, threshold=70)
        if result:
            metric_key, canonical_name, score = result
            print(f"   OK '{term}' -> '{canonical_name}' (score: {score:.1f}%)")
        else:
            print(f"   FAIL '{term}' -> No match found")
    
    print()
    
    # Test Sales metrics
    print("Testing Granular Sales Metrics:")
    sales_tests = [
        "ticket medio",
        "ARPU",
        "ricavo medio per cliente",
        "churn rate",
        "costo acquisizione cliente",
        "lifetime value",
        "tasso conversione"
    ]
    
    for term in sales_tests:
        result = mapper.map_metric(term, threshold=70)
        if result:
            metric_key, canonical_name, score = result
            print(f"   OK '{term}' -> '{canonical_name}' (score: {score:.1f}%)")
        else:
            print(f"   FAIL '{term}' -> No match found")
    
    print()
    
    # Test Inventory metrics
    print("Testing Inventory/Warehouse Metrics:")
    inventory_tests = [
        "rotazione magazzino",
        "giorni di scorta", 
        "giacenza media",
        "scorte obsolete",
        "stock out",
        "fill rate"
    ]
    
    for term in inventory_tests:
        result = mapper.map_metric(term, threshold=70)
        if result:
            metric_key, canonical_name, score = result
            print(f"   OK '{term}' -> '{canonical_name}' (score: {score:.1f}%)")
        else:
            print(f"   FAIL '{term}' -> No match found")
    
    print()
    
    # Test HR metrics
    print("Testing HR Metrics:")
    hr_tests = [
        "FTE",
        "costo medio dipendente",
        "turnover personale",
        "tasso assenteismo",
        "ore straordinari",
        "formazione per dipendente"
    ]
    
    for term in hr_tests:
        result = mapper.map_metric(term, threshold=70)
        if result:
            metric_key, canonical_name, score = result
            print(f"   OK '{term}' -> '{canonical_name}' (score: {score:.1f}%)")
        else:
            print(f"   FAIL '{term}' -> No match found")
    
    print()
    
    # Test calculations
    print("Testing Calculated Metrics:")
    calculable = mapper.get_calculable_metrics()
    
    example_calculations = [
        "dso", "margine_ebitda_pct", "capitale_circolante_netto", 
        "rotazione_magazzino", "tasso_churn_pct"
    ]
    
    for metric_key in example_calculations:
        if metric_key in calculable:
            formula = calculable[metric_key]
            details = mapper.get_metric_details(metric_key)
            canonical_name = details.get('canonical_name', metric_key) if details else metric_key
            print(f"   CALC {canonical_name}: {formula}")
    
    print()
    
    # Test category organization
    print("Category Organization:")
    hierarchy = mapper.get_category_hierarchy()
    
    for category, subcategories in hierarchy.items():
        metric_count = sum(len(metrics) for metrics in subcategories.values())
        print(f"   {category}: {metric_count} metrics")
        for subcategory, metrics in subcategories.items():
            print(f"      {subcategory}: {len(metrics)} metrics")
    
    print()
    
    # Test fuzzy suggestions
    print("Testing Suggestion System:")
    partial_tests = [
        "giorni med",
        "tick",
        "rotat",
        "turno"
    ]
    
    for partial in partial_tests:
        suggestions = mapper.suggest_metrics(partial, top_k=3)
        print(f"   '{partial}' suggestions:")
        for _, name, score in suggestions:
            print(f"      - {name} ({score:.1f}%)")
    
    print()
    print("Extended Ontology Test Complete!")
    return True

if __name__ == "__main__":
    test_extended_ontology()