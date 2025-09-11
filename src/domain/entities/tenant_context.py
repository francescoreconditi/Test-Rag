# ============================================
# FILE DI SERVIZIO ENTERPRISE - PRODUZIONE
# Creato da: Claude Code
# Data: 2025-09-08
# Scopo: Multi-tenant context management per enterprise RAG
# ============================================

"""
Tenant context entities for multi-tenant RAG enterprise system.
Handles tenant isolation, security, and resource allocation.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import uuid


class TenantTier(str, Enum):
    """Tenant subscription tiers with different resource limits."""

    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


class TenantStatus(str, Enum):
    """Tenant account status."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    TRIAL = "trial"
    EXPIRED = "expired"


@dataclass
class TenantResourceLimits:
    """Resource limits per tenant tier."""

    max_documents_per_month: int
    max_queries_per_day: int
    max_storage_gb: float
    max_concurrent_users: int
    rate_limit_per_minute: int
    premium_features_enabled: bool
    api_access_enabled: bool
    custom_models_allowed: bool

    @classmethod
    def get_tier_limits(cls, tier: TenantTier) -> "TenantResourceLimits":
        """Get resource limits for a specific tier."""
        limits_map = {
            TenantTier.BASIC: cls(
                max_documents_per_month=100,
                max_queries_per_day=1000,
                max_storage_gb=1.0,
                max_concurrent_users=3,
                rate_limit_per_minute=60,
                premium_features_enabled=False,
                api_access_enabled=False,
                custom_models_allowed=False,
            ),
            TenantTier.PREMIUM: cls(
                max_documents_per_month=1000,
                max_queries_per_day=10000,
                max_storage_gb=10.0,
                max_concurrent_users=10,
                rate_limit_per_minute=300,
                premium_features_enabled=True,
                api_access_enabled=True,
                custom_models_allowed=False,
            ),
            TenantTier.ENTERPRISE: cls(
                max_documents_per_month=10000,
                max_queries_per_day=100000,
                max_storage_gb=100.0,
                max_concurrent_users=100,
                rate_limit_per_minute=1000,
                premium_features_enabled=True,
                api_access_enabled=True,
                custom_models_allowed=True,
            ),
            TenantTier.CUSTOM: cls(
                max_documents_per_month=-1,  # Unlimited
                max_queries_per_day=-1,
                max_storage_gb=-1,
                max_concurrent_users=-1,
                rate_limit_per_minute=-1,
                premium_features_enabled=True,
                api_access_enabled=True,
                custom_models_allowed=True,
            ),
        }
        return limits_map[tier]


@dataclass
class TenantUsageStats:
    """Current usage statistics for a tenant."""

    documents_this_month: int = 0
    queries_today: int = 0
    storage_used_gb: float = 0.0
    current_concurrent_users: int = 0
    api_calls_this_hour: int = 0
    last_activity: Optional[datetime] = None

    def is_within_limits(self, limits: TenantResourceLimits) -> bool:
        """Check if current usage is within tenant limits."""
        if limits.max_documents_per_month > 0 and self.documents_this_month >= limits.max_documents_per_month:
            return False
        if limits.max_queries_per_day > 0 and self.queries_today >= limits.max_queries_per_day:
            return False
        if limits.max_storage_gb > 0 and self.storage_used_gb >= limits.max_storage_gb:
            return False
        return not (limits.max_concurrent_users > 0 and self.current_concurrent_users >= limits.max_concurrent_users)

    def get_usage_percentage(self, limits: TenantResourceLimits) -> dict[str, float]:
        """Get usage as percentage of limits."""
        usage = {}

        if limits.max_documents_per_month > 0:
            usage["documents"] = (self.documents_this_month / limits.max_documents_per_month) * 100

        if limits.max_queries_per_day > 0:
            usage["queries"] = (self.queries_today / limits.max_queries_per_day) * 100

        if limits.max_storage_gb > 0:
            usage["storage"] = (self.storage_used_gb / limits.max_storage_gb) * 100

        if limits.max_concurrent_users > 0:
            usage["users"] = (self.current_concurrent_users / limits.max_concurrent_users) * 100

        return usage


@dataclass
class TenantContext:
    """Complete tenant context information."""

    tenant_id: str
    tenant_name: str
    organization: str
    tier: TenantTier
    status: TenantStatus
    created_at: datetime
    updated_at: datetime

    # Resource management
    resource_limits: TenantResourceLimits
    current_usage: TenantUsageStats

    # Security and isolation
    encryption_key_id: str
    database_schema: str
    vector_collection_name: str

    # Configuration
    custom_settings: dict[str, Any]
    feature_flags: dict[str, bool]

    # Contact and billing
    admin_email: str
    billing_contact: Optional[str] = None
    contract_end_date: Optional[datetime] = None

    @classmethod
    def create_new_tenant(
        cls, tenant_name: str, organization: str, admin_email: str, tier: TenantTier = TenantTier.BASIC
    ) -> "TenantContext":
        """Create a new tenant with default settings."""
        tenant_id = str(uuid.uuid4())
        now = datetime.now()

        return cls(
            tenant_id=tenant_id,
            tenant_name=tenant_name,
            organization=organization,
            tier=tier,
            status=TenantStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            resource_limits=TenantResourceLimits.get_tier_limits(tier),
            current_usage=TenantUsageStats(),
            encryption_key_id=f"key_{tenant_id[:8]}",
            database_schema=f"tenant_{tenant_id.replace('-', '_')}",
            vector_collection_name=f"docs_{tenant_id[:8]}",
            custom_settings={},
            feature_flags={
                "enterprise_mode": tier in [TenantTier.ENTERPRISE, TenantTier.CUSTOM],
                "api_access": tier in [TenantTier.PREMIUM, TenantTier.ENTERPRISE, TenantTier.CUSTOM],
                "custom_models": tier in [TenantTier.ENTERPRISE, TenantTier.CUSTOM],
                "advanced_analytics": tier in [TenantTier.ENTERPRISE, TenantTier.CUSTOM],
                "white_labeling": tier == TenantTier.CUSTOM,
            },
            admin_email=admin_email,
        )

    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a feature is enabled for this tenant."""
        return self.feature_flags.get(feature_name, False)

    def can_perform_action(self, action: str) -> bool:
        """Check if tenant can perform a specific action based on limits."""
        if self.status != TenantStatus.ACTIVE:
            return False

        if not self.current_usage.is_within_limits(self.resource_limits):
            return False

        # Action-specific checks
        action_checks = {
            "upload_document": self.resource_limits.max_documents_per_month < 0
            or self.current_usage.documents_this_month < self.resource_limits.max_documents_per_month,
            "execute_query": self.resource_limits.max_queries_per_day < 0
            or self.current_usage.queries_today < self.resource_limits.max_queries_per_day,
            "api_access": self.resource_limits.api_access_enabled,
            "use_custom_model": self.resource_limits.custom_models_allowed,
        }

        return action_checks.get(action, True)

    def update_usage(
        self,
        documents_added: int = 0,
        queries_executed: int = 0,
        storage_delta_gb: float = 0.0,
        concurrent_users_delta: int = 0,
    ):
        """Update tenant usage statistics."""
        self.current_usage.documents_this_month += documents_added
        self.current_usage.queries_today += queries_executed
        self.current_usage.storage_used_gb += storage_delta_gb
        self.current_usage.current_concurrent_users += concurrent_users_delta
        self.current_usage.last_activity = datetime.now()
        self.updated_at = datetime.now()

    def upgrade_tier(self, new_tier: TenantTier):
        """Upgrade tenant to a new tier."""
        if new_tier.value >= self.tier.value:  # Only allow upgrades
            self.tier = new_tier
            self.resource_limits = TenantResourceLimits.get_tier_limits(new_tier)
            self.updated_at = datetime.now()

            # Update feature flags
            self.feature_flags.update(
                {
                    "enterprise_mode": new_tier in [TenantTier.ENTERPRISE, TenantTier.CUSTOM],
                    "api_access": new_tier in [TenantTier.PREMIUM, TenantTier.ENTERPRISE, TenantTier.CUSTOM],
                    "custom_models": new_tier in [TenantTier.ENTERPRISE, TenantTier.CUSTOM],
                    "advanced_analytics": new_tier in [TenantTier.ENTERPRISE, TenantTier.CUSTOM],
                    "white_labeling": new_tier == TenantTier.CUSTOM,
                }
            )

    def to_dict(self) -> dict[str, Any]:
        """Convert tenant context to dictionary for storage."""
        return {
            "tenant_id": self.tenant_id,
            "tenant_name": self.tenant_name,
            "organization": self.organization,
            "tier": self.tier.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "resource_limits": {
                "max_documents_per_month": self.resource_limits.max_documents_per_month,
                "max_queries_per_day": self.resource_limits.max_queries_per_day,
                "max_storage_gb": self.resource_limits.max_storage_gb,
                "max_concurrent_users": self.resource_limits.max_concurrent_users,
                "rate_limit_per_minute": self.resource_limits.rate_limit_per_minute,
                "premium_features_enabled": self.resource_limits.premium_features_enabled,
                "api_access_enabled": self.resource_limits.api_access_enabled,
                "custom_models_allowed": self.resource_limits.custom_models_allowed,
            },
            "current_usage": {
                "documents_this_month": self.current_usage.documents_this_month,
                "queries_today": self.current_usage.queries_today,
                "storage_used_gb": self.current_usage.storage_used_gb,
                "current_concurrent_users": self.current_usage.current_concurrent_users,
                "api_calls_this_hour": self.current_usage.api_calls_this_hour,
                "last_activity": self.current_usage.last_activity.isoformat()
                if self.current_usage.last_activity
                else None,
            },
            "encryption_key_id": self.encryption_key_id,
            "database_schema": self.database_schema,
            "vector_collection_name": self.vector_collection_name,
            "custom_settings": self.custom_settings,
            "feature_flags": self.feature_flags,
            "admin_email": self.admin_email,
            "billing_contact": self.billing_contact,
            "contract_end_date": self.contract_end_date.isoformat() if self.contract_end_date else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TenantContext":
        """Create tenant context from dictionary."""
        resource_limits = TenantResourceLimits(**data["resource_limits"])

        usage_data = data["current_usage"]
        current_usage = TenantUsageStats(
            documents_this_month=usage_data["documents_this_month"],
            queries_today=usage_data["queries_today"],
            storage_used_gb=usage_data["storage_used_gb"],
            current_concurrent_users=usage_data["current_concurrent_users"],
            api_calls_this_hour=usage_data["api_calls_this_hour"],
            last_activity=datetime.fromisoformat(usage_data["last_activity"]) if usage_data["last_activity"] else None,
        )

        return cls(
            tenant_id=data["tenant_id"],
            tenant_name=data["tenant_name"],
            organization=data["organization"],
            tier=TenantTier(data["tier"]),
            status=TenantStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            resource_limits=resource_limits,
            current_usage=current_usage,
            encryption_key_id=data["encryption_key_id"],
            database_schema=data["database_schema"],
            vector_collection_name=data["vector_collection_name"],
            custom_settings=data["custom_settings"],
            feature_flags=data["feature_flags"],
            admin_email=data["admin_email"],
            billing_contact=data.get("billing_contact"),
            contract_end_date=datetime.fromisoformat(data["contract_end_date"])
            if data.get("contract_end_date")
            else None,
        )
