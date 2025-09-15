"""Access Control Service for Row-level Security implementation."""

import logging
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

from .user_context import UserContext, UserRole, DataClassification

logger = logging.getLogger(__name__)


@dataclass
class AccessConstraint:
    """Represents an access constraint for RLS filtering."""

    field: str
    operator: str  # "in", "eq", "lte", "gte", "not_in"
    values: Any
    description: str = ""


@dataclass
class RLSFilter:
    """Complete RLS filter with all constraints."""

    constraints: List[AccessConstraint]
    tenant_constraint: Optional[AccessConstraint] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class SecurityViolationError(Exception):
    """Raised when a security violation is detected."""

    pass


class AccessControlService:
    """Service for managing Row-level Security access control."""

    def __init__(self):
        """Initialize access control service."""
        self.logger = logging.getLogger(__name__)
        self._permission_cache: Dict[str, Dict] = {}
        self._last_cache_update: datetime = datetime.utcnow()
        self.cache_ttl_seconds = 300  # 5 minutes

    def generate_rls_filter(self, user_context: UserContext, target_table: str = "facts") -> RLSFilter:
        """Generate RLS filter for a user context and target table."""
        try:
            constraints = []

            # Admin bypass
            if user_context.is_admin() and user_context.has_permission("bypass_rls"):
                self.logger.info(f"Admin {user_context.user_id} bypassing RLS")
                return RLSFilter(constraints=[], metadata={"bypass": True, "reason": "admin"})

            # Tenant constraint (always applied for multi-tenant)
            tenant_constraint = None
            if user_context.tenant_id:
                tenant_constraint = AccessConstraint(
                    field="tenant_id", operator="eq", values=user_context.tenant_id, description="Tenant isolation"
                )

            # Entity constraints
            if user_context.accessible_entities:
                constraints.append(
                    AccessConstraint(
                        field="entity_id",
                        operator="in",
                        values=user_context.accessible_entities,
                        description="Entity access control",
                    )
                )
            elif user_context.role != UserRole.ADMIN:
                # If no entities specified and not admin, deny all
                constraints.append(
                    AccessConstraint(
                        field="entity_id",
                        operator="in",
                        values=[],  # Empty list = no access
                        description="No entity access granted",
                    )
                )

            # Period constraints
            if user_context.accessible_periods:
                constraints.append(
                    AccessConstraint(
                        field="period",
                        operator="in",
                        values=user_context.accessible_periods,
                        description="Time period access control",
                    )
                )

            # Cost center constraints
            if user_context.cost_centers:
                constraints.append(
                    AccessConstraint(
                        field="cost_center_code",
                        operator="in",
                        values=user_context.cost_centers,
                        description="Cost center access control",
                    )
                )

            # Data classification constraints
            constraints.append(
                AccessConstraint(
                    field="classification_level",
                    operator="lte",
                    values=user_context.max_classification_level.value,
                    description="Data classification filter",
                )
            )

            # Region constraints
            if user_context.accessible_regions:
                constraints.append(
                    AccessConstraint(
                        field="region",
                        operator="in",
                        values=user_context.accessible_regions,
                        description="Geographic access control",
                    )
                )

            # Department constraints for BU managers
            if user_context.role == UserRole.BU_MANAGER and user_context.department:
                constraints.append(
                    AccessConstraint(
                        field="department",
                        operator="eq",
                        values=user_context.department,
                        description="Department access for BU manager",
                    )
                )

            filter_metadata = {
                "user_id": user_context.user_id,
                "role": user_context.role.value,
                "generated_at": datetime.utcnow().isoformat(),
                "constraints_count": len(constraints),
                "tenant_id": user_context.tenant_id,
            }

            rls_filter = RLSFilter(
                constraints=constraints, tenant_constraint=tenant_constraint, metadata=filter_metadata
            )

            self.logger.info(
                f"Generated RLS filter for user {user_context.user_id} with {len(constraints)} constraints"
            )

            return rls_filter

        except Exception as e:
            self.logger.error(f"Error generating RLS filter: {e}")
            # Fail-safe: very restrictive filter
            return RLSFilter(
                constraints=[
                    AccessConstraint(
                        field="entity_id", operator="in", values=[], description="Error fallback - no access"
                    )
                ],
                metadata={"error": str(e), "fallback": True},
            )

    def validate_access_attempt(
        self, user_context: UserContext, resource_type: str, resource_id: str = None, operation: str = "read"
    ) -> bool:
        """Validate if user can perform operation on resource."""
        try:
            # Admin check
            if user_context.is_admin():
                return True

            # Permission check
            permission_map = {
                "read": "read_assigned",
                "write": "write_assigned",
                "delete": "delete_assigned",
                "manage": "manage_assigned",
            }

            required_permission = permission_map.get(operation, operation)
            if not user_context.has_permission(required_permission):
                self.logger.warning(
                    f"User {user_context.user_id} lacks permission {required_permission} "
                    f"for {operation} on {resource_type}"
                )
                return False

            # Resource-specific validation
            if resource_type == "entity" and resource_id:
                return user_context.can_access_entity(resource_id)
            elif resource_type == "cost_center" and resource_id:
                return user_context.can_access_cost_center(resource_id)
            elif resource_type == "period" and resource_id:
                return user_context.can_access_period(resource_id)

            return True

        except Exception as e:
            self.logger.error(f"Error validating access: {e}")
            return False  # Fail secure

    def check_data_classification_access(
        self, user_context: UserContext, data_classification: DataClassification
    ) -> bool:
        """Check if user can access data with given classification level."""
        return user_context.can_access_classification(data_classification)

    def get_accessible_entities(self, user_context: UserContext) -> List[str]:
        """Get list of entities user can access."""
        if user_context.is_admin():
            # Admin can access all - would need to query actual entities
            return ["*"]  # Special marker for all entities
        return user_context.accessible_entities

    def get_accessible_periods(self, user_context: UserContext) -> List[str]:
        """Get list of periods user can access."""
        if user_context.is_admin():
            return ["*"]  # Special marker for all periods
        return user_context.accessible_periods

    def audit_access_attempt(
        self,
        user_context: UserContext,
        resource_type: str,
        operation: str,
        success: bool,
        resource_id: str = None,
        additional_info: Dict[str, Any] = None,
    ):
        """Log access attempt for audit purposes."""
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_context.user_id,
            "username": user_context.username,
            "role": user_context.role.value,
            "tenant_id": user_context.tenant_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "operation": operation,
            "success": success,
            "session_id": user_context.session_id,
            "additional_info": additional_info or {},
        }

        if success:
            self.logger.info(f"Access granted: {audit_entry}")
        else:
            self.logger.warning(f"Access denied: {audit_entry}")

    def convert_rls_to_sql_where(self, rls_filter: RLSFilter, table_alias: str = "") -> Tuple[str, Dict]:
        """Convert RLS filter to SQL WHERE clause and parameters."""
        if not rls_filter.constraints and not rls_filter.tenant_constraint:
            return "", {}

        where_clauses = []
        parameters = {}
        param_counter = 0

        table_prefix = f"{table_alias}." if table_alias else ""

        # Add tenant constraint first
        if rls_filter.tenant_constraint:
            constraint = rls_filter.tenant_constraint
            param_name = f"param_{param_counter}"
            where_clauses.append(f"{table_prefix}{constraint.field} = :{param_name}")
            parameters[param_name] = constraint.values
            param_counter += 1

        # Add other constraints
        for constraint in rls_filter.constraints:
            param_name = f"param_{param_counter}"

            if constraint.operator == "eq":
                where_clauses.append(f"{table_prefix}{constraint.field} = :{param_name}")
                parameters[param_name] = constraint.values
            elif constraint.operator == "in":
                if isinstance(constraint.values, (list, tuple)) and len(constraint.values) > 0:
                    placeholders = ",".join([f":{param_name}_{i}" for i in range(len(constraint.values))])
                    where_clauses.append(f"{table_prefix}{constraint.field} IN ({placeholders})")
                    for i, value in enumerate(constraint.values):
                        parameters[f"{param_name}_{i}"] = value
                else:
                    # Empty list = no access
                    where_clauses.append("1 = 0")  # Always false
            elif constraint.operator == "not_in":
                if isinstance(constraint.values, (list, tuple)) and len(constraint.values) > 0:
                    placeholders = ",".join([f":{param_name}_{i}" for i in range(len(constraint.values))])
                    where_clauses.append(f"{table_prefix}{constraint.field} NOT IN ({placeholders})")
                    for i, value in enumerate(constraint.values):
                        parameters[f"{param_name}_{i}"] = value
            elif constraint.operator == "lte":
                where_clauses.append(f"{table_prefix}{constraint.field} <= :{param_name}")
                parameters[param_name] = constraint.values
            elif constraint.operator == "gte":
                where_clauses.append(f"{table_prefix}{constraint.field} >= :{param_name}")
                parameters[param_name] = constraint.values

            param_counter += 1

        where_clause = " AND ".join(where_clauses) if where_clauses else ""
        return where_clause, parameters

    def convert_rls_to_mongo_filter(self, rls_filter: RLSFilter) -> Dict[str, Any]:
        """Convert RLS filter to MongoDB query filter."""
        mongo_filter = {}

        # Add tenant constraint
        if rls_filter.tenant_constraint:
            constraint = rls_filter.tenant_constraint
            mongo_filter[constraint.field] = constraint.values

        # Add other constraints
        for constraint in rls_filter.constraints:
            if constraint.operator == "eq":
                mongo_filter[constraint.field] = constraint.values
            elif constraint.operator == "in":
                if isinstance(constraint.values, (list, tuple)) and len(constraint.values) > 0:
                    mongo_filter[constraint.field] = {"$in": list(constraint.values)}
                else:
                    # Empty list = no documents match
                    mongo_filter[constraint.field] = {"$in": []}
            elif constraint.operator == "not_in":
                if isinstance(constraint.values, (list, tuple)) and len(constraint.values) > 0:
                    mongo_filter[constraint.field] = {"$nin": list(constraint.values)}
            elif constraint.operator == "lte":
                mongo_filter[constraint.field] = {"$lte": constraint.values}
            elif constraint.operator == "gte":
                mongo_filter[constraint.field] = {"$gte": constraint.values}

        return mongo_filter

    def is_rls_bypass_allowed(self, user_context: UserContext) -> bool:
        """Check if user is allowed to bypass RLS."""
        return user_context.is_admin() and user_context.has_permission("bypass_rls")
