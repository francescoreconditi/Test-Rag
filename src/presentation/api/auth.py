"""
Multi-Tenant Authentication System v2 - Based on MultiTenantManager
====================================================================

This module provides FastAPI authentication using the enterprise MultiTenantManager.
All authentication, authorization, and session management is delegated to MultiTenantManager.
"""

import os
from typing import Optional
from datetime import datetime

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from src.core.security.multi_tenant_manager import MultiTenantManager, TenantSession
from src.domain.entities.tenant_context import TenantContext, TenantTier

# Security scheme
security = HTTPBearer()

# JWT Configuration (from environment or defaults)
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

# Initialize multi-tenant manager singleton
_manager_instance = None

def get_manager() -> MultiTenantManager:
    """Get or create the MultiTenantManager singleton instance."""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = MultiTenantManager(jwt_secret=JWT_SECRET_KEY)
    return _manager_instance


class LoginRequest(BaseModel):
    """Login request model."""
    email: str
    password: str
    tenant_id: Optional[str] = None


class LoginResponse(BaseModel):
    """Login response model."""
    access_token: str
    token_type: str = "bearer"
    tenant_id: str
    tier: str
    expires_in: int
    session_id: str
    permissions: list[str]


class TokenData(BaseModel):
    """Decoded JWT token data."""
    session_id: str
    tenant_id: str
    user_id: str
    user_email: str
    permissions: list[str]
    exp: datetime
    iat: datetime


async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> TokenData:
    """
    Verify JWT token and extract session data.
    Uses MultiTenantManager's JWT verification.
    """
    token = credentials.credentials
    manager = get_manager()

    try:
        # Decode token using manager's secret
        payload = jwt.decode(
            token,
            manager.jwt_secret,
            algorithms=[manager.jwt_algorithm]
        )

        # Validate session exists and is active
        session_id = payload.get("session_id")
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing session_id",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Get session from manager
        session = await manager._get_session(session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired or invalid",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if session is expired
        if datetime.now() > session.expires_at:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create TokenData from session
        return TokenData(
            session_id=session.session_id,
            tenant_id=session.tenant_id,
            user_id=session.user_id,
            user_email=session.user_email,
            permissions=session.permissions,
            exp=session.expires_at,
            iat=session.created_at
        )

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token verification failed: {str(e)}"
        )


async def get_current_tenant(token_data: TokenData = Depends(verify_token)) -> TenantContext:
    """
    Get current tenant context from verified token.
    Retrieves tenant information from MultiTenantManager.
    """
    manager = get_manager()

    try:
        # Get tenant from manager
        tenant = manager.get_tenant(token_data.tenant_id)

        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant {token_data.tenant_id} not found"
            )

        # Validate session is still active
        is_valid = manager.validate_session(
            token_data.tenant_id,
            token_data.user_id
        )

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session is no longer valid"
            )

        return tenant

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tenant context: {str(e)}"
        )


async def get_optional_tenant(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> Optional[TenantContext]:
    """
    Get optional tenant context (for endpoints that work with or without auth).
    Returns None if no valid credentials are provided.
    """
    if not credentials:
        return None

    try:
        token_data = await verify_token(credentials)
        return await get_current_tenant(token_data)
    except:
        return None


def check_tenant_limits(tenant: TenantContext, resource_type: str, count: int = 1) -> bool:
    """
    Check if tenant has not exceeded resource limits.
    Uses MultiTenantManager's usage tracking.
    """
    manager = get_manager()

    # Get current usage from manager
    current_usage = manager.get_tenant_usage(tenant.tenant_id)

    if resource_type == "documents":
        limit = tenant.resource_limits.max_documents_per_month
        current = current_usage.get("documents_this_month", 0)
    elif resource_type == "storage":
        limit = tenant.resource_limits.max_storage_gb * 1024 * 1024 * 1024  # Convert GB to bytes
        current = current_usage.get("storage_bytes", 0)
    elif resource_type == "queries":
        limit = tenant.resource_limits.max_queries_per_day
        current = current_usage.get("queries_today", 0)
    else:
        return True

    if limit == -1:  # Unlimited
        return True

    return (current + count) <= limit


async def login(request: LoginRequest) -> LoginResponse:
    """
    Authenticate user and create session using MultiTenantManager.
    This is the main login endpoint that delegates everything to MultiTenantManager.
    """
    manager = get_manager()

    try:
        # Determine tenant_id (from request or derive from email)
        if request.tenant_id:
            tenant_id = request.tenant_id
        else:
            # Derive from email domain
            domain = request.email.split("@")[1] if "@" in request.email else "default"
            tenant_id = f"tenant_{domain.replace('.', '_')}"

        # Check if tenant exists
        tenant = manager.get_tenant(tenant_id)
        if not tenant:
            # Create new tenant for demo/testing
            # In production, this should be an admin-only operation
            tenant = manager.create_tenant(
                tenant_id=tenant_id,
                company_name=f"{domain.title()} Company" if "@" in request.email else "Default Company",
                tier=TenantTier.PREMIUM,
                admin_email=request.email
            )

            # Create user for the new tenant
            await manager.create_tenant_user(
                tenant_id=tenant_id,
                email=request.email,
                password=request.password,
                permissions=["read", "write", "delete"]
            )

        # Authenticate using MultiTenantManager
        # Note: login_tenant_user doesn't take tenant_id, it finds it from email
        token = await manager.login_tenant_user(
            email=request.email,
            password=request.password,
            ip_address=None,  # Could be extracted from request
            user_agent=None   # Could be extracted from request
        )

        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        # Decode token to get session_id
        payload = jwt.decode(token, manager.jwt_secret, algorithms=[manager.jwt_algorithm])
        session_id = payload.get("session_id")
        permissions = payload.get("permissions", [])

        return LoginResponse(
            access_token=token,
            token_type="bearer",
            tenant_id=tenant_id,
            tier=tenant.tier.value,
            expires_in=int(manager.session_duration.total_seconds()),
            session_id=session_id,
            permissions=permissions
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


async def logout(token_data: TokenData = Depends(verify_token)) -> dict:
    """
    Logout user by invalidating their session.
    """
    manager = get_manager()

    try:
        success = await manager.logout_tenant_user(token_data.session_id)

        if success:
            return {"message": "Logged out successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to logout"
            )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout failed: {str(e)}"
        )


# Backward compatibility aliases
multi_tenant_manager = get_manager()