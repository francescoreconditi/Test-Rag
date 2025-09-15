"""User context and role management for Row-level Security."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional, Set


class UserRole(Enum):
    """User roles with different access levels."""

    ADMIN = "admin"  # Full system access
    ANALYST = "analyst"  # Read/write access to assigned entities
    VIEWER = "viewer"  # Read-only access
    BU_MANAGER = "bu_manager"  # Business unit manager with limited scope
    TENANT_ADMIN = "tenant_admin"  # Admin for specific tenant only


class DataClassification(Enum):
    """Data classification levels for RLS."""

    PUBLIC = 1  # Accessible to all authenticated users
    INTERNAL = 2  # Internal company data
    CONFIDENTIAL = 3  # Confidential business data
    RESTRICTED = 4  # Highly restricted data


@dataclass
class UserContext:
    """Complete user context for Row-level Security."""

    user_id: str
    username: str
    role: UserRole
    tenant_id: Optional[str] = None

    # Entity access control
    accessible_entities: List[str] = None  # Companies, BUs, departments
    accessible_periods: List[str] = None  # Time periods (2023, Q1_2024, etc.)
    accessible_regions: List[str] = None  # Geographic regions

    # Security levels
    data_classification_level: DataClassification = DataClassification.PUBLIC
    max_classification_level: DataClassification = DataClassification.INTERNAL

    # Additional constraints
    department: Optional[str] = None
    cost_centers: List[str] = None  # Accessible cost centers

    # Session information
    session_id: str = None
    login_time: datetime = None
    last_activity: datetime = None

    # Permissions
    permissions: Set[str] = None

    def __post_init__(self):
        """Initialize default values."""
        if self.accessible_entities is None:
            self.accessible_entities = []
        if self.accessible_periods is None:
            self.accessible_periods = []
        if self.accessible_regions is None:
            self.accessible_regions = []
        if self.cost_centers is None:
            self.cost_centers = []
        if self.permissions is None:
            self.permissions = set()
        if self.login_time is None:
            self.login_time = datetime.utcnow()
        if self.last_activity is None:
            self.last_activity = datetime.utcnow()

    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission."""
        return permission in self.permissions or self.role == UserRole.ADMIN

    def can_access_entity(self, entity_id: str) -> bool:
        """Check if user can access specific entity."""
        if self.role == UserRole.ADMIN:
            return True
        return entity_id in self.accessible_entities

    def can_access_period(self, period: str) -> bool:
        """Check if user can access specific time period."""
        if self.role == UserRole.ADMIN:
            return True
        return period in self.accessible_periods

    def can_access_cost_center(self, cdc_code: str) -> bool:
        """Check if user can access specific cost center."""
        if self.role == UserRole.ADMIN:
            return True
        return cdc_code in self.cost_centers

    def can_access_classification(self, classification: DataClassification) -> bool:
        """Check if user can access data with specific classification."""
        return classification.value <= self.max_classification_level.value

    def is_admin(self) -> bool:
        """Check if user is system admin."""
        return self.role == UserRole.ADMIN

    def is_tenant_admin(self) -> bool:
        """Check if user is tenant admin."""
        return self.role in [UserRole.ADMIN, UserRole.TENANT_ADMIN]

    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.utcnow()

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "role": self.role.value,
            "tenant_id": self.tenant_id,
            "accessible_entities": self.accessible_entities,
            "accessible_periods": self.accessible_periods,
            "accessible_regions": self.accessible_regions,
            "data_classification_level": self.data_classification_level.value,
            "max_classification_level": self.max_classification_level.value,
            "department": self.department,
            "cost_centers": self.cost_centers,
            "session_id": self.session_id,
            "login_time": self.login_time.isoformat() if self.login_time else None,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "permissions": list(self.permissions),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UserContext":
        """Create UserContext from dictionary."""
        return cls(
            user_id=data["user_id"],
            username=data["username"],
            role=UserRole(data["role"]),
            tenant_id=data.get("tenant_id"),
            accessible_entities=data.get("accessible_entities", []),
            accessible_periods=data.get("accessible_periods", []),
            accessible_regions=data.get("accessible_regions", []),
            data_classification_level=DataClassification(data.get("data_classification_level", 1)),
            max_classification_level=DataClassification(data.get("max_classification_level", 2)),
            department=data.get("department"),
            cost_centers=data.get("cost_centers", []),
            session_id=data.get("session_id"),
            login_time=datetime.fromisoformat(data["login_time"]) if data.get("login_time") else None,
            last_activity=datetime.fromisoformat(data["last_activity"]) if data.get("last_activity") else None,
            permissions=set(data.get("permissions", [])),
        )


# Predefined role configurations
ROLE_CONFIGURATIONS = {
    UserRole.ADMIN: {
        "permissions": {
            "read_all",
            "write_all",
            "delete_all",
            "manage_users",
            "manage_tenants",
            "system_admin",
            "bypass_rls",
        },
        "max_classification_level": DataClassification.RESTRICTED,
        "description": "Full system administrator",
    },
    UserRole.TENANT_ADMIN: {
        "permissions": {"read_tenant", "write_tenant", "manage_tenant_users", "tenant_admin"},
        "max_classification_level": DataClassification.CONFIDENTIAL,
        "description": "Administrator for specific tenant",
    },
    UserRole.ANALYST: {
        "permissions": {"read_assigned", "write_assigned", "create_reports", "export_data"},
        "max_classification_level": DataClassification.INTERNAL,
        "description": "Business analyst with read/write access to assigned data",
    },
    UserRole.BU_MANAGER: {
        "permissions": {"read_bu", "write_bu", "manage_bu_data", "view_reports"},
        "max_classification_level": DataClassification.CONFIDENTIAL,
        "description": "Business unit manager with scope limited to their BU",
    },
    UserRole.VIEWER: {
        "permissions": {"read_assigned", "view_reports"},
        "max_classification_level": DataClassification.INTERNAL,
        "description": "Read-only access to assigned data",
    },
}


def create_user_context(
    user_id: str, username: str, role: UserRole, tenant_id: Optional[str] = None, **kwargs
) -> UserContext:
    """Factory function to create UserContext with role-based defaults."""
    role_config = ROLE_CONFIGURATIONS.get(role, {})

    permissions = role_config.get("permissions", set())
    max_classification = role_config.get("max_classification_level", DataClassification.PUBLIC)

    context = UserContext(
        user_id=user_id,
        username=username,
        role=role,
        tenant_id=tenant_id,
        max_classification_level=max_classification,
        permissions=permissions.copy(),
        **kwargs,
    )

    return context
