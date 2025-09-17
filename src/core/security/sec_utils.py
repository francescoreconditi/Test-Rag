from typing import Optional

from services.secure_rag_engine import SecureRAGEngine
from src.core.security import UserContext
from src.core.security.multi_tenant_manager import MultiTenantManager
from src.domain.entities.tenant_context import TenantContext, TenantTier


def initialize_secure_rag(
    user_context: UserContext, fallback_email: Optional[str] = None
) -> tuple[SecureRAGEngine, TenantContext]:
    """
    Ensure tenant context exists and initialize SecureRAGEngine.
    Used by both Streamlit and REST login flows.
    """
    manager = MultiTenantManager()

    effective_tenant_id = user_context.tenant_id
    tenant = None
    if effective_tenant_id:
        tenant = manager.get_tenant(effective_tenant_id)
        if not tenant:
            # Auto-create tenant with default PREMIUM tier
            tenant = manager.create_tenant(
                tenant_id=effective_tenant_id,
                company_name=f"Company {effective_tenant_id}",
                tier=TenantTier.PREMIUM,
                admin_email=fallback_email or f"{user_context.username}@company.com",
            )

    # Initialize SecureRAGEngine
    sec_rag_engine = SecureRAGEngine(user_context)

    return sec_rag_engine, tenant
