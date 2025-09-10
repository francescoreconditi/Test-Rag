"""Business domain exceptions."""

from typing import Any, Optional


class DomainException(Exception):
    """Base exception for domain layer."""

    def __init__(self, message: str, code: Optional[str] = None, details: Optional[dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            'error': self.code,
            'message': self.message,
            'details': self.details
        }


class BusinessRuleViolation(DomainException):
    """Raised when a business rule is violated."""

    def __init__(self, rule: str, message: str, **details):
        super().__init__(
            message=message,
            code=f"BUSINESS_RULE_{rule.upper()}",
            details=details
        )
        self.rule = rule


class InsufficientDataError(DomainException):
    """Raised when there's insufficient data for analysis."""

    def __init__(self, required_data: str, available_data: Optional[str] = None, minimum_required: Optional[int] = None):
        details = {
            'required': required_data,
            'available': available_data
        }
        if minimum_required:
            details['minimum_required'] = minimum_required

        super().__init__(
            message=f"Insufficient data: {required_data} required",
            code="INSUFFICIENT_DATA",
            details=details
        )


class InvalidFinancialDataError(DomainException):
    """Raised when financial data is invalid."""

    def __init__(self, field: str, value: Any, reason: str, valid_range: Optional[tuple] = None):
        details = {
            'field': field,
            'value': str(value),
            'reason': reason
        }
        if valid_range:
            details['valid_range'] = {
                'min': valid_range[0],
                'max': valid_range[1]
            }

        super().__init__(
            message=f"Invalid financial data in field '{field}': {reason}",
            code="INVALID_FINANCIAL_DATA",
            details=details
        )


class DocumentProcessingError(DomainException):
    """Raised when document processing fails."""

    def __init__(self, document_path: str, operation: str, reason: str, supported_formats: Optional[list[str]] = None):
        details = {
            'document': document_path,
            'operation': operation,
            'reason': reason
        }
        if supported_formats:
            details['supported_formats'] = supported_formats

        super().__init__(
            message=f"Failed to process document '{document_path}': {reason}",
            code="DOCUMENT_PROCESSING_ERROR",
            details=details
        )


class AnalysisError(DomainException):
    """Raised when analysis fails."""

    def __init__(self, analysis_type: str, reason: str, data_source: Optional[str] = None, **extra_details):
        details = {
            'analysis_type': analysis_type,
            'reason': reason
        }
        if data_source:
            details['data_source'] = data_source
        details.update(extra_details)

        super().__init__(
            message=f"Analysis failed for {analysis_type}: {reason}",
            code="ANALYSIS_ERROR",
            details=details
        )


class DataValidationError(DomainException):
    """Raised when data validation fails."""

    def __init__(self, errors: list[str], data_type: str):
        super().__init__(
            message=f"Validation failed for {data_type}",
            code="DATA_VALIDATION_ERROR",
            details={
                'data_type': data_type,
                'errors': errors,
                'error_count': len(errors)
            }
        )
        self.errors = errors


class ConfigurationError(DomainException):
    """Raised when configuration is invalid."""

    def __init__(self, config_key: str, reason: str, required_value: Optional[str] = None):
        details = {
            'config_key': config_key,
            'reason': reason
        }
        if required_value:
            details['required_value'] = required_value

        super().__init__(
            message=f"Configuration error for '{config_key}': {reason}",
            code="CONFIGURATION_ERROR",
            details=details
        )


class ExternalServiceError(DomainException):
    """Raised when an external service fails."""

    def __init__(self, service_name: str, operation: str, reason: str, retry_after: Optional[int] = None):
        details = {
            'service': service_name,
            'operation': operation,
            'reason': reason
        }
        if retry_after:
            details['retry_after_seconds'] = retry_after

        super().__init__(
            message=f"External service '{service_name}' failed during {operation}: {reason}",
            code="EXTERNAL_SERVICE_ERROR",
            details=details
        )
