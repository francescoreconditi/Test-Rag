"""Secure RAG Engine with Row-level Security integration."""

import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from .rag_engine import RAGEngine
from src.core.security import (
    UserContext,
    AccessControlService,
    AuthenticationService,
    SecurityViolationError,
    DataClassification,
)
from src.infrastructure.repositories.secure_fact_table import SecureFactTableRepository
from src.domain.entities.tenant_context import TenantContext

logger = logging.getLogger(__name__)


class SecureRAGEngine:
    """Secure RAG Engine with Row-level Security and authentication."""

    def __init__(self, user_context: Optional[UserContext] = None):
        """Initialize secure RAG engine with user context."""
        self.user_context = user_context
        self.access_control = AccessControlService()
        self.auth_service = AuthenticationService()
        self.secure_fact_repository = SecureFactTableRepository()

        # Initialize base RAG engine - simplified to avoid complex tenant context
        tenant_context = None

        self.rag_engine = RAGEngine(tenant_context=tenant_context)
        self.logger = logging.getLogger(__name__)

        # Track access for audit
        if user_context:
            self.logger.info(
                f"Initialized SecureRAGEngine for user {user_context.user_id} "
                f"(role: {user_context.role.value}, tenant: {user_context.tenant_id})"
            )

    def authenticate_and_initialize(self, session_token: str) -> bool:
        """Authenticate using session token and initialize user context."""
        try:
            user_context = self.auth_service.validate_session(session_token)
            if not user_context:
                return False

            self.user_context = user_context

            # Reinitialize with tenant context if needed
            if user_context.tenant_id:
                tenant_context = TenantContext(tenant_id=user_context.tenant_id, isolation_level="STRICT")
                self.rag_engine = RAGEngine(tenant_context=tenant_context)

            self.logger.info(f"Authenticated user {user_context.user_id} via session token")
            return True

        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            return False

    def _validate_document_access(self, documents: List[Any]) -> List[Any]:
        """Filter documents based on user access rights."""
        if not self.user_context:
            raise SecurityViolationError("No authenticated user context")

        if self.user_context.is_admin():
            return documents  # Admin can access all documents

        filtered_docs = []

        for doc in documents:
            try:
                # Check document metadata for security attributes
                metadata = getattr(doc, "metadata", {})

                # Check entity access
                entity = metadata.get("entity", metadata.get("source", ""))
                if entity and not self.user_context.can_access_entity(entity):
                    continue

                # Check classification level
                classification_level = metadata.get("classification_level", 2)  # Default INTERNAL
                classification = DataClassification(classification_level)
                if not self.user_context.can_access_classification(classification):
                    continue

                # Check period access
                period = metadata.get("period", "")
                if period and not self.user_context.can_access_period(period):
                    continue

                # Check cost center access
                cost_center = metadata.get("cost_center_code", "")
                if cost_center and not self.user_context.can_access_cost_center(cost_center):
                    continue

                filtered_docs.append(doc)

            except Exception as e:
                self.logger.warning(f"Error filtering document: {e}")
                continue  # Skip problematic document

        self.logger.info(
            f"Filtered {len(documents)} documents to {len(filtered_docs)} for user {self.user_context.user_id}"
        )

        return filtered_docs

    def query(
        self, query_text: str, top_k: int = 5, analysis_type: Optional[str] = None, include_metadata: bool = True
    ) -> Dict[str, Any]:
        """Secure query with RLS applied."""
        if not self.user_context:
            raise SecurityViolationError("Authentication required")

        try:
            # Validate query permission
            if not self.access_control.validate_access_attempt(self.user_context, "query", operation="read"):
                raise SecurityViolationError("Insufficient permissions for query")

            # Execute base RAG query
            base_response = self.rag_engine.query(query_text=query_text, top_k=top_k, analysis_type=analysis_type)

            # Apply RLS filtering to sources/documents
            if "sources" in base_response:
                filtered_sources = self._apply_rls_to_sources(base_response["sources"])
                base_response["sources"] = filtered_sources

            # Add security metadata
            if include_metadata:
                base_response["security_metadata"] = {
                    "user_id": self.user_context.user_id,
                    "tenant_id": self.user_context.tenant_id,
                    "access_level": self.user_context.max_classification_level.name,
                    "filtered_sources": len(base_response.get("sources", [])),
                    "query_time": datetime.utcnow().isoformat(),
                }

            # Audit successful query
            self.access_control.audit_access_attempt(
                self.user_context,
                "query",
                "read",
                True,
                None,
                {
                    "query_length": len(query_text),
                    "analysis_type": analysis_type,
                    "sources_returned": len(base_response.get("sources", [])),
                    "top_k": top_k,
                },
            )

            return base_response

        except SecurityViolationError:
            self.access_control.audit_access_attempt(
                self.user_context,
                "query",
                "read",
                False,
                None,
                {"query": query_text[:100], "reason": "security_violation"},
            )
            raise
        except Exception as e:
            self.logger.error(f"Secure query error: {e}")
            self.access_control.audit_access_attempt(
                self.user_context, "query", "read", False, None, {"query": query_text[:100], "error": str(e)}
            )
            raise

    def _apply_rls_to_sources(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply RLS filtering to query sources."""
        filtered_sources = []

        for source in sources:
            try:
                # Check entity access
                entity = source.get("entity", source.get("source", ""))
                if entity and not self.user_context.can_access_entity(entity):
                    continue

                # Check classification
                classification_level = source.get("classification_level", 2)
                classification = DataClassification(classification_level)
                if not self.user_context.can_access_classification(classification):
                    continue

                # Check period
                period = source.get("period", "")
                if period and not self.user_context.can_access_period(period):
                    continue

                # Sanitize sensitive information for non-admin users
                if not self.user_context.is_admin():
                    sanitized_source = source.copy()
                    # Remove or mask sensitive fields
                    sensitive_fields = ["file_path", "internal_id", "raw_content"]
                    for field in sensitive_fields:
                        if field in sanitized_source:
                            sanitized_source[field] = "[REDACTED]"
                    filtered_sources.append(sanitized_source)
                else:
                    filtered_sources.append(source)

            except Exception as e:
                self.logger.warning(f"Error filtering source: {e}")
                continue

        return filtered_sources

    def index_documents(
        self, file_paths: List[str], metadata_overrides: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Index documents with security metadata."""
        if not self.user_context:
            raise SecurityViolationError("Authentication required")

        try:
            # Validate write permission
            if not self.access_control.validate_access_attempt(self.user_context, "documents", operation="write"):
                raise SecurityViolationError("Insufficient permissions for document indexing")

            # Add security metadata to documents
            security_metadata = {
                "indexed_by": self.user_context.user_id,
                "tenant_id": self.user_context.tenant_id,
                "indexed_at": datetime.utcnow().isoformat(),
                "classification_level": metadata_overrides.get(
                    "classification_level", DataClassification.INTERNAL.value
                ),
            }

            if metadata_overrides:
                metadata_overrides.update(security_metadata)
            else:
                metadata_overrides = security_metadata

            # Index documents
            result = self.rag_engine.parse_insert_docs(file_paths, metadata_overrides=metadata_overrides)

            # Audit successful indexing
            self.access_control.audit_access_attempt(
                self.user_context,
                "documents",
                "write",
                True,
                None,
                {
                    "file_count": len(file_paths),
                    "files": [f.split("/")[-1] for f in file_paths[:5]],  # First 5 filenames
                    "metadata_keys": list(metadata_overrides.keys()) if metadata_overrides else [],
                },
            )

            return result

        except SecurityViolationError:
            self.access_control.audit_access_attempt(
                self.user_context,
                "documents",
                "write",
                False,
                None,
                {"file_count": len(file_paths), "reason": "security_violation"},
            )
            raise
        except Exception as e:
            self.logger.error(f"Document indexing error: {e}")
            self.access_control.audit_access_attempt(
                self.user_context, "documents", "write", False, None, {"file_count": len(file_paths), "error": str(e)}
            )
            raise

    def get_accessible_entities(self) -> List[str]:
        """Get entities accessible to current user."""
        if not self.user_context:
            return []

        return self.secure_fact_repository.get_accessible_entities(self.user_context)

    def get_user_stats(self) -> Dict[str, Any]:
        """Get user-specific statistics."""
        if not self.user_context:
            return {}

        try:
            stats = {
                "user_info": {
                    "user_id": self.user_context.user_id,
                    "username": self.user_context.username,
                    "role": self.user_context.role.value,
                    "tenant_id": self.user_context.tenant_id,
                    "login_time": self.user_context.login_time.isoformat() if self.user_context.login_time else None,
                    "session_duration": str(datetime.utcnow() - self.user_context.login_time)
                    if self.user_context.login_time
                    else None,
                },
                "access_summary": {
                    "accessible_entities": len(self.user_context.accessible_entities),
                    "accessible_periods": len(self.user_context.accessible_periods),
                    "cost_centers": len(self.user_context.cost_centers),
                    "max_classification": self.user_context.max_classification_level.name,
                    "permissions": list(self.user_context.permissions),
                },
                "accessible_entities": self.get_accessible_entities(),
            }

            # Add security stats for admins
            if self.user_context.is_admin():
                security_stats = self.secure_fact_repository.get_security_stats(self.user_context)
                stats["security_stats"] = security_stats

            return stats

        except Exception as e:
            self.logger.error(f"Error getting user stats: {e}")
            return {"error": str(e)}

    def delete_documents(self, source_names: List[str]) -> Dict[str, Any]:
        """Delete documents with security validation."""
        if not self.user_context:
            raise SecurityViolationError("Authentication required")

        try:
            # Validate delete permission
            if not self.access_control.validate_access_attempt(self.user_context, "documents", operation="delete"):
                raise SecurityViolationError("Insufficient permissions for document deletion")

            # Validate access to each document/entity
            for source_name in source_names:
                # Extract entity from source name (basic heuristic)
                potential_entity = source_name.split("_")[0] if "_" in source_name else source_name
                if not self.user_context.can_access_entity(potential_entity):
                    raise SecurityViolationError(f"No access to delete document from entity: {potential_entity}")

            # Delete documents
            results = {}
            for source_name in source_names:
                success = self.rag_engine.delete_document_by_source(source_name)
                results[source_name] = success

            # Audit deletion
            self.access_control.audit_access_attempt(
                self.user_context,
                "documents",
                "delete",
                True,
                None,
                {"source_names": source_names, "deletion_results": results},
            )

            return {"success": True, "results": results, "deleted_count": sum(1 for v in results.values() if v)}

        except SecurityViolationError:
            self.access_control.audit_access_attempt(
                self.user_context,
                "documents",
                "delete",
                False,
                None,
                {"source_names": source_names, "reason": "security_violation"},
            )
            raise
        except Exception as e:
            self.logger.error(f"Document deletion error: {e}")
            self.access_control.audit_access_attempt(
                self.user_context, "documents", "delete", False, None, {"source_names": source_names, "error": str(e)}
            )
            raise

    def cleanup_session(self):
        """Cleanup session and audit logout."""
        if self.user_context and self.user_context.session_id:
            self.auth_service.logout(self.user_context.session_id)
            self.logger.info(f"Cleaned up session for user {self.user_context.user_id}")
            self.user_context = None
