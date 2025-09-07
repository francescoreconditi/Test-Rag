"""Interactive editing service for financial metrics and data corrections."""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import json
import logging
from pathlib import Path

from src.domain.value_objects.source_reference import ProvenancedValue, SourceReference
from src.application.services.ontology_mapper import OntologyMapper
from src.application.services.data_normalizer import DataNormalizer
from src.domain.value_objects.guardrails import FinancialGuardrails, ValidationResult

logger = logging.getLogger(__name__)


@dataclass
class EditOperation:
    """Represents a user edit operation."""
    operation_id: str
    timestamp: datetime
    operation_type: str  # 'update', 'add', 'delete', 'correct'
    target_metric: str
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    source_ref: Optional[str] = None
    user_comment: Optional[str] = None
    validation_override: bool = False
    confidence_adjustment: Optional[float] = None


@dataclass
class EditSession:
    """Manages a editing session with multiple operations."""
    session_id: str
    created_at: datetime
    user_id: str
    document_path: str
    operations: List[EditOperation]
    auto_save: bool = True
    
    def add_operation(self, operation: EditOperation):
        """Add an operation to the session."""
        self.operations.append(operation)


class InteractiveEditingService:
    """Service for interactive editing of financial data and metrics."""
    
    def __init__(self):
        """Initialize interactive editing service."""
        self.ontology_mapper = OntologyMapper()
        self.data_normalizer = DataNormalizer()
        self.guardrails = FinancialGuardrails()
        self.active_sessions: Dict[str, EditSession] = {}
        self.sessions_dir = Path("cache/edit_sessions")
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
    
    def start_editing_session(self, 
                             document_path: str,
                             user_id: str = "default",
                             session_id: Optional[str] = None) -> str:
        """Start a new editing session."""
        if not session_id:
            session_id = f"edit_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        session = EditSession(
            session_id=session_id,
            created_at=datetime.now(),
            user_id=user_id,
            document_path=document_path,
            operations=[]
        )
        
        self.active_sessions[session_id] = session
        return session_id
    
    def get_editable_data(self, session_id: str) -> Dict[str, Any]:
        """Get data structure ready for interactive editing."""
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.active_sessions[session_id]
        
        # Mock extracted data - in real scenario, would come from document extraction
        extracted_data = {
            'ricavi': {
                'value': 10000000,
                'source_ref': 'bilancio_2024.pdf|p.2|tab:1|row:Ricavi',
                'confidence': 0.95,
                'unit': 'EUR',
                'period': 'FY2024',
                'editable': True,
                'validation_status': 'valid'
            },
            'ebitda': {
                'value': 1500000,
                'source_ref': 'bilancio_2024.pdf|p.3|tab:2|row:EBITDA',
                'confidence': 0.90,
                'unit': 'EUR',
                'period': 'FY2024',
                'editable': True,
                'validation_status': 'warning',
                'validation_message': 'Valore sotto la media del settore'
            },
            'dipendenti': {
                'value': 150,
                'source_ref': 'bilancio_2024.pdf|p.15|tab:5|row:Organico',
                'confidence': 0.85,
                'unit': 'count',
                'period': 'FY2024',
                'editable': True,
                'validation_status': 'valid'
            },
            'dso': {
                'value': None,  # Calculated field
                'calculated': True,
                'formula': '(crediti_commerciali / ricavi) * 365',
                'dependencies': ['crediti_commerciali', 'ricavi'],
                'editable': False,
                'validation_status': 'pending'
            }
        }
        
        # Add available metric suggestions
        available_metrics = self._get_available_metrics()
        
        # Add validation rules
        validation_rules = self._get_validation_rules()
        
        return {
            'session_id': session_id,
            'data': extracted_data,
            'available_metrics': available_metrics,
            'validation_rules': validation_rules,
            'edit_history': [asdict(op) for op in session.operations]
        }
    
    def update_metric_value(self, 
                           session_id: str,
                           metric_name: str,
                           new_value: Any,
                           user_comment: Optional[str] = None,
                           validation_override: bool = False) -> Dict[str, Any]:
        """Update a metric value with validation."""
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.active_sessions[session_id]
        
        # Get current data
        current_data = self.get_editable_data(session_id)['data']
        
        if metric_name not in current_data:
            raise ValueError(f"Metric {metric_name} not found")
        
        old_value = current_data[metric_name].get('value')
        
        # Normalize the new value
        try:
            normalized_result = self.data_normalizer.normalize_number(str(new_value))
            normalized_value = normalized_result.value
            unit = normalized_result.currency or current_data[metric_name].get('unit') or 'numeric'
        except Exception as e:
            return {
                'success': False,
                'error': f'Error normalizing value: {str(e)}',
                'value_kept': old_value
            }
        
        # Validate the new value
        validation_results = self._validate_metric_update(
            metric_name, old_value, normalized_value, current_data
        )
        
        # Check if validation passed or override is allowed
        has_errors = any(not r.passed and r.level.value == 'error' for r in validation_results)
        
        if has_errors and not validation_override:
            return {
                'success': False,
                'validation_errors': [r.to_dict() for r in validation_results if not r.passed],
                'value_kept': old_value,
                'requires_override': True
            }
        
        # Create edit operation
        operation = EditOperation(
            operation_id=f"op_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            timestamp=datetime.now(),
            operation_type='update',
            target_metric=metric_name,
            old_value=old_value,
            new_value=normalized_value,
            source_ref=current_data[metric_name].get('source_ref'),
            user_comment=user_comment,
            validation_override=validation_override
        )
        
        # Add to session
        session.add_operation(operation)
        
        # Update the value
        current_data[metric_name]['value'] = normalized_value
        current_data[metric_name]['unit'] = unit
        current_data[metric_name]['last_modified'] = datetime.now().isoformat()
        current_data[metric_name]['modified_by'] = session.user_id
        
        # Recalculate dependent metrics
        dependent_updates = self._recalculate_dependent_metrics(metric_name, current_data)
        
        # Save session if auto-save enabled
        if session.auto_save:
            self._save_session(session)
        
        return {
            'success': True,
            'old_value': old_value,
            'new_value': normalized_value,
            'validation_results': [r.to_dict() for r in validation_results],
            'dependent_updates': dependent_updates,
            'operation_id': operation.operation_id
        }
    
    def add_new_metric(self,
                      session_id: str,
                      metric_name: str,
                      value: Any,
                      source_ref: Optional[str] = None,
                      unit: Optional[str] = None,
                      period: Optional[str] = None) -> Dict[str, Any]:
        """Add a new metric to the dataset."""
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.active_sessions[session_id]
        
        # Check if metric already exists
        current_data = self.get_editable_data(session_id)['data']
        if metric_name in current_data:
            return {
                'success': False,
                'error': f'Metric {metric_name} already exists. Use update instead.'
            }
        
        # Try to map metric to canonical name
        mapping_result = self.ontology_mapper.map_metric(metric_name)
        canonical_name = mapping_result[1] if mapping_result else metric_name
        
        # Normalize value
        try:
            normalized_result = self.data_normalizer.normalize_number(str(value))
            normalized_value = normalized_result.value
            detected_unit = normalized_result.currency or unit or "numeric"
        except Exception as e:
            return {
                'success': False,
                'error': f'Error normalizing value: {str(e)}'
            }
        
        # Create edit operation
        operation = EditOperation(
            operation_id=f"op_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            timestamp=datetime.now(),
            operation_type='add',
            target_metric=metric_name,
            old_value=None,
            new_value=normalized_value,
            source_ref=source_ref or f"user_added_{datetime.now().isoformat()}"
        )
        
        session.add_operation(operation)
        
        # Add the metric
        current_data[metric_name] = {
            'value': normalized_value,
            'canonical_name': canonical_name,
            'source_ref': operation.source_ref,
            'confidence': 0.8,  # Lower confidence for user-added
            'unit': detected_unit,
            'period': period or 'FY2024',
            'editable': True,
            'validation_status': 'valid',
            'added_by_user': True,
            'created_at': datetime.now().isoformat()
        }
        
        # Save session
        if session.auto_save:
            self._save_session(session)
        
        return {
            'success': True,
            'metric_name': metric_name,
            'canonical_name': canonical_name,
            'value': normalized_value,
            'unit': detected_unit,
            'operation_id': operation.operation_id
        }
    
    def delete_metric(self, session_id: str, metric_name: str, reason: str = "") -> Dict[str, Any]:
        """Delete a metric from the dataset."""
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.active_sessions[session_id]
        current_data = self.get_editable_data(session_id)['data']
        
        if metric_name not in current_data:
            return {
                'success': False,
                'error': f'Metric {metric_name} not found'
            }
        
        # Check dependencies
        dependents = self._find_dependent_metrics(metric_name, current_data)
        if dependents:
            return {
                'success': False,
                'error': f'Cannot delete {metric_name}. Used by: {", ".join(dependents)}',
                'dependent_metrics': dependents
            }
        
        old_value = current_data[metric_name].get('value')
        
        # Create operation
        operation = EditOperation(
            operation_id=f"op_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            timestamp=datetime.now(),
            operation_type='delete',
            target_metric=metric_name,
            old_value=old_value,
            new_value=None,
            user_comment=reason
        )
        
        session.add_operation(operation)
        
        # Remove metric
        del current_data[metric_name]
        
        # Save session
        if session.auto_save:
            self._save_session(session)
        
        return {
            'success': True,
            'deleted_metric': metric_name,
            'old_value': old_value,
            'operation_id': operation.operation_id
        }
    
    def suggest_corrections(self, session_id: str) -> List[Dict[str, Any]]:
        """Suggest automatic corrections based on validation rules."""
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        current_data = self.get_editable_data(session_id)['data']
        suggestions = []
        
        # Run comprehensive validation
        financial_data = {k: v.get('value') for k, v in current_data.items() if v.get('value') is not None}
        validation_results = self.guardrails.validate_comprehensive(financial_data)
        
        for result in validation_results:
            if not result.passed and result.expected_value is not None:
                suggestions.append({
                    'metric': result.rule_name.split('_')[0],
                    'current_value': result.actual_value,
                    'suggested_value': result.expected_value,
                    'reason': result.message,
                    'confidence': 0.7,
                    'auto_correctable': True
                })
        
        # Suggest missing calculated metrics
        calculable_metrics = self.ontology_mapper.get_calculable_metrics()
        available_metrics = set(current_data.keys())
        
        for metric, formula in calculable_metrics.items():
            if metric not in available_metrics:
                # Check if all dependencies are available
                dependencies = self._extract_formula_dependencies(formula)
                if all(dep in available_metrics for dep in dependencies):
                    calculated_value = self._calculate_metric_value(formula, financial_data)
                    if calculated_value is not None:
                        suggestions.append({
                            'metric': metric,
                            'current_value': None,
                            'suggested_value': calculated_value,
                            'reason': f'Can be calculated from: {", ".join(dependencies)}',
                            'confidence': 0.9,
                            'auto_correctable': True,
                            'is_calculated': True,
                            'formula': formula
                        })
        
        return suggestions
    
    def apply_suggestions(self, 
                         session_id: str, 
                         suggestion_ids: List[int],
                         user_comment: str = "Applied automatic suggestions") -> Dict[str, Any]:
        """Apply selected suggestions."""
        suggestions = self.suggest_corrections(session_id)
        applied = []
        failed = []
        
        for suggestion_id in suggestion_ids:
            if suggestion_id >= len(suggestions):
                failed.append(f"Suggestion {suggestion_id} not found")
                continue
            
            suggestion = suggestions[suggestion_id]
            metric = suggestion['metric']
            new_value = suggestion['suggested_value']
            
            if suggestion.get('is_calculated'):
                # Add calculated metric
                result = self.add_new_metric(
                    session_id, metric, new_value, 
                    source_ref=f"calculated_{datetime.now().isoformat()}"
                )
            else:
                # Update existing metric
                result = self.update_metric_value(
                    session_id, metric, new_value, 
                    user_comment=user_comment, validation_override=True
                )
            
            if result['success']:
                applied.append(metric)
            else:
                failed.append(f"{metric}: {result.get('error', 'Unknown error')}")
        
        return {
            'applied_count': len(applied),
            'applied_metrics': applied,
            'failed_count': len(failed),
            'failed_reasons': failed
        }
    
    def get_edit_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get edit history for a session."""
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.active_sessions[session_id]
        return [asdict(op) for op in session.operations]
    
    def undo_operation(self, session_id: str, operation_id: str) -> Dict[str, Any]:
        """Undo a specific operation."""
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.active_sessions[session_id]
        
        # Find operation
        operation = None
        for op in session.operations:
            if op.operation_id == operation_id:
                operation = op
                break
        
        if not operation:
            return {
                'success': False,
                'error': f'Operation {operation_id} not found'
            }
        
        # Create undo operation
        undo_op = EditOperation(
            operation_id=f"undo_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}",
            timestamp=datetime.now(),
            operation_type=f'undo_{operation.operation_type}',
            target_metric=operation.target_metric,
            old_value=operation.new_value,
            new_value=operation.old_value,
            user_comment=f"Undo operation {operation_id}"
        )
        
        session.add_operation(undo_op)
        
        # Apply undo based on original operation type
        if operation.operation_type == 'update':
            if operation.old_value is not None:
                self.update_metric_value(
                    session_id, operation.target_metric, 
                    operation.old_value, validation_override=True
                )
        elif operation.operation_type == 'add':
            self.delete_metric(session_id, operation.target_metric, "Undo add operation")
        elif operation.operation_type == 'delete':
            if operation.old_value is not None:
                self.add_new_metric(
                    session_id, operation.target_metric, operation.old_value
                )
        
        return {
            'success': True,
            'undone_operation': operation_id,
            'undo_operation_id': undo_op.operation_id
        }
    
    def _validate_metric_update(self, 
                               metric_name: str, 
                               old_value: Any, 
                               new_value: Any,
                               current_data: Dict) -> List[ValidationResult]:
        """Validate a metric update."""
        # Create test dataset with the new value
        test_data = {k: v.get('value') for k, v in current_data.items() if v.get('value') is not None}
        test_data[metric_name] = new_value
        
        # Run validation
        return self.guardrails.validate_comprehensive(test_data)
    
    def _recalculate_dependent_metrics(self, 
                                     changed_metric: str, 
                                     current_data: Dict) -> List[Dict[str, Any]]:
        """Recalculate metrics that depend on the changed metric."""
        updates = []
        
        # Find calculated metrics that depend on this metric
        calculable_metrics = self.ontology_mapper.get_calculable_metrics()
        
        for metric, formula in calculable_metrics.items():
            if metric in current_data and changed_metric in formula:
                # Recalculate
                available_values = {k: v.get('value') for k, v in current_data.items() 
                                  if v.get('value') is not None}
                
                new_calculated_value = self._calculate_metric_value(formula, available_values)
                if new_calculated_value is not None:
                    old_value = current_data[metric].get('value')
                    current_data[metric]['value'] = new_calculated_value
                    current_data[metric]['last_calculated'] = datetime.now().isoformat()
                    
                    updates.append({
                        'metric': metric,
                        'old_value': old_value,
                        'new_value': new_calculated_value,
                        'reason': f'Dependent on {changed_metric}'
                    })
        
        return updates
    
    def _find_dependent_metrics(self, metric_name: str, current_data: Dict) -> List[str]:
        """Find metrics that depend on the given metric."""
        dependents = []
        calculable_metrics = self.ontology_mapper.get_calculable_metrics()
        
        for metric, formula in calculable_metrics.items():
            if metric in current_data and metric_name in formula:
                dependents.append(metric)
        
        return dependents
    
    def _extract_formula_dependencies(self, formula: str) -> List[str]:
        """Extract metric dependencies from a formula."""
        import re
        return re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', formula)
    
    def _calculate_metric_value(self, formula: str, available_data: Dict[str, float]) -> Optional[float]:
        """Safely calculate a metric value from formula."""
        try:
            # Replace metric names with values
            calc_formula = formula
            for metric, value in available_data.items():
                if value is not None:
                    calc_formula = calc_formula.replace(metric, str(value))
            
            # Safe evaluation (only allow basic math operations)
            import ast
            import operator
            
            ops = {
                ast.Add: operator.add,
                ast.Sub: operator.sub,
                ast.Mult: operator.mul,
                ast.Div: operator.truediv,
                ast.USub: operator.neg,
            }
            
            def eval_expr(expr):
                return eval_(ast.parse(expr, mode='eval').body)
            
            def eval_(node):
                if isinstance(node, ast.Num):
                    return node.n
                elif isinstance(node, ast.BinOp):
                    return ops[type(node.op)](eval_(node.left), eval_(node.right))
                elif isinstance(node, ast.UnaryOp):
                    return ops[type(node.op)](eval_(node.operand))
                else:
                    raise TypeError(node)
            
            return eval_expr(calc_formula)
        except:
            return None
    
    def _get_available_metrics(self) -> List[Dict[str, Any]]:
        """Get available metrics from ontology."""
        hierarchy = self.ontology_mapper.get_category_hierarchy()
        metrics = []
        
        for category, subcategories in hierarchy.items():
            for subcategory, metric_list in subcategories.items():
                for metric_key in metric_list:
                    details = self.ontology_mapper.get_metric_details(metric_key)
                    if details:
                        metrics.append({
                            'key': metric_key,
                            'name': details.get('canonical_name', metric_key),
                            'category': category,
                            'subcategory': subcategory,
                            'unit': details.get('unit', 'numeric'),
                            'calculable': 'calculation' in details
                        })
        
        return metrics
    
    def _get_validation_rules(self) -> Dict[str, Any]:
        """Get validation rules for the UI."""
        return {
            'ranges': {
                'dso': {'min': 15, 'max': 180, 'unit': 'days'},
                'dpo': {'min': 15, 'max': 120, 'unit': 'days'},
                'tasso_churn_pct': {'min': 0, 'max': 50, 'unit': 'percentage'},
                'turnover_personale_pct': {'min': 0, 'max': 100, 'unit': 'percentage'}
            },
            'required_positive': ['ricavi', 'attivo_totale'],
            'balance_equations': {
                'balance_sheet': 'attivo_totale = passivo_totale',
                'pfn': 'pfn = debito_lordo - cassa',
                'margine_lordo': 'margine_lordo = ricavi - cogs'
            }
        }
    
    def _save_session(self, session: EditSession) -> None:
        """Save session to disk."""
        session_file = self.sessions_dir / f"{session.session_id}.json"
        
        try:
            with open(session_file, 'w', encoding='utf-8') as f:
                session_data = asdict(session)
                json.dump(session_data, f, default=str, indent=2)
        except Exception as e:
            logger.error(f"Error saving session {session.session_id}: {e}")
    
    def load_session(self, session_id: str) -> bool:
        """Load session from disk."""
        session_file = self.sessions_dir / f"{session_id}.json"
        
        if not session_file.exists():
            return False
        
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            # Convert back to objects
            operations = [EditOperation(**op_data) for op_data in session_data['operations']]
            session_data['operations'] = operations
            session_data['created_at'] = datetime.fromisoformat(session_data['created_at'])
            
            session = EditSession(**session_data)
            self.active_sessions[session_id] = session
            return True
            
        except Exception as e:
            logger.error(f"Error loading session {session_id}: {e}")
            return False