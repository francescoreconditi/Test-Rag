"""
Authentication and Multi-Tenant Middleware for FastAPI
=======================================================

JWT authentication and tenant context management for API endpoints.
"""

import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel

from src.domain.entities.tenant_context import TenantContext
from src.core.security.multi_tenant_manager import MultiTenantManager
from config.settings import settings

# Security scheme
security = HTTPBearer()

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_HOURS = int(os.getenv("SESSION_DURATION_HOURS", "8"))

# Initialize multi-tenant manager
multi_tenant_manager = MultiTenantManager()


class TokenData(BaseModel):
    """JWT Token payload data."""
    tenant_id: str
    user_id: str
    email: str
    tier: str
    exp: datetime


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


def create_access_token(tenant_context: TenantContext, user_id: str, email: str) -> str:
    """Create JWT access token for tenant."""
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    
    payload = {
        "tenant_id": tenant_context.tenant_id,
        "user_id": user_id,
        "email": email,
        "tier": tenant_context.tier.value,
        "exp": expire.timestamp(),
        "iat": datetime.utcnow().timestamp(),
        "iss": "zcs-rag-api"
    }
    
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> TokenData:
    """Verify JWT token and extract tenant data."""
    token = credentials.credentials
    
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        
        # Extract token data
        token_data = TokenData(
            tenant_id=payload.get("tenant_id"),
            user_id=payload.get("user_id"),
            email=payload.get("email"),
            tier=payload.get("tier"),
            exp=datetime.fromtimestamp(payload.get("exp"))
        )
        
        # Check expiration
        if datetime.utcnow() > token_data.exp:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return token_data
        
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_tenant(token_data: TokenData = Depends(verify_token)) -> TenantContext:
    """Get current tenant context from JWT token."""
    try:
        # Get tenant from manager
        tenant = multi_tenant_manager.get_tenant(token_data.tenant_id)
        
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant {token_data.tenant_id} not found"
            )
        
        # Validate session
        is_valid = multi_tenant_manager.validate_session(
            token_data.tenant_id,
            token_data.user_id
        )
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired session"
            )
        
        return tenant
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tenant context: {str(e)}"
        )


async def get_optional_tenant(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> Optional[TenantContext]:
    """Get optional tenant context (for endpoints that work with or without auth)."""
    if not credentials:
        return None
    
    try:
        token_data = verify_token(credentials)
        return await get_current_tenant(token_data)
    except:
        return None


def check_tenant_limits(tenant: TenantContext, resource_type: str, count: int = 1) -> bool:
    """Check if tenant has not exceeded resource limits."""
    # Get current usage
    current_usage = multi_tenant_manager.get_tenant_usage(tenant.tenant_id)
    
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
    """Authenticate user and create session."""
    try:
        # For demo purposes, create or get tenant based on email domain
        domain = request.email.split("@")[1] if "@" in request.email else "default"
        tenant_id = request.tenant_id or f"tenant_{domain.replace('.', '_')}"
        
        # Check if tenant exists, create if not
        tenant = multi_tenant_manager.get_tenant(tenant_id)
        if not tenant:
            # Create new tenant for demo
            from src.domain.entities.tenant_context import TenantTier
            tenant = multi_tenant_manager.create_tenant(
                tenant_id=tenant_id,
                company_name=domain.title() + " Company",
                tier=TenantTier.PREMIUM,
                admin_email=request.email
            )
        
        # Create session
        user_id = f"user_{request.email.replace('@', '_').replace('.', '_')}"
        session_token = multi_tenant_manager.create_session(
            tenant_id=tenant_id,
            user_id=user_id,
            user_email=request.email
        )
        
        # Create JWT token
        access_token = create_access_token(tenant, user_id, request.email)
        
        return LoginResponse(
            access_token=access_token,
            tenant_id=tenant_id,
            tier=tenant.tier.value,
            expires_in=JWT_EXPIRATION_HOURS * 3600
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )