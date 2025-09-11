# ============================================
# FILE DI SERVIZIO ENTERPRISE - PRODUZIONE
# Creato da: Claude Code
# Data: 2025-09-08
# Scopo: Multi-tenant security manager per enterprise RAG
# ============================================

"""
Multi-tenant security and isolation manager for enterprise RAG system.
Handles tenant authentication, authorization, resource isolation, and security policies.
"""

from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import json
import logging
from pathlib import Path
import sqlite3
from typing import Any, Optional

import jwt

from src.domain.entities.tenant_context import TenantContext, TenantStatus, TenantTier

logger = logging.getLogger(__name__)

@dataclass
class TenantSession:
    """Active tenant session information."""
    session_id: str
    tenant_id: str
    user_id: str
    user_email: str
    created_at: datetime
    expires_at: datetime
    permissions: list[str]
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

class SecurityViolation(Exception):
    """Raised when a security policy is violated."""
    def __init__(self, message: str, tenant_id: str, violation_type: str):
        super().__init__(message)
        self.tenant_id = tenant_id
        self.violation_type = violation_type

class MultiTenantManager:
    """
    Enterprise multi-tenant security manager.
    Provides tenant isolation, authentication, authorization, and resource management.
    """

    def __init__(self, database_path: str = "data/multi_tenant.db",
                 jwt_secret: Optional[str] = None):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(exist_ok=True)

        # Security configuration
        self.jwt_secret = jwt_secret or self._generate_jwt_secret()
        self.jwt_algorithm = "HS256"
        self.session_duration = timedelta(hours=8)

        # In-memory caches
        self._tenant_cache: dict[str, TenantContext] = {}
        self._session_cache: dict[str, TenantSession] = {}

        # Rate limiting
        self._rate_limits: dict[str, list[datetime]] = {}

        self._init_database()

    def _generate_jwt_secret(self) -> str:
        """Generate a secure JWT secret key."""
        import secrets
        return secrets.token_urlsafe(32)

    def _init_database(self):
        """Initialize the multi-tenant database schema."""
        try:
            with sqlite3.connect(self.database_path) as conn:
                conn.executescript("""
                    CREATE TABLE IF NOT EXISTS tenants (
                        tenant_id TEXT PRIMARY KEY,
                        tenant_data TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS tenant_users (
                        user_id TEXT PRIMARY KEY,
                        tenant_id TEXT NOT NULL,
                        email TEXT NOT NULL,
                        password_hash TEXT NOT NULL,
                        permissions TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        last_login TEXT,
                        FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id),
                        UNIQUE(tenant_id, email)
                    );

                    CREATE TABLE IF NOT EXISTS tenant_sessions (
                        session_id TEXT PRIMARY KEY,
                        tenant_id TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        session_data TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        expires_at TEXT NOT NULL,
                        FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id),
                        FOREIGN KEY (user_id) REFERENCES tenant_users (user_id)
                    );

                    CREATE TABLE IF NOT EXISTS security_events (
                        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tenant_id TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        event_data TEXT NOT NULL,
                        ip_address TEXT,
                        user_agent TEXT,
                        timestamp TEXT NOT NULL,
                        FOREIGN KEY (tenant_id) REFERENCES tenants (tenant_id)
                    );

                    CREATE INDEX IF NOT EXISTS idx_tenants_id ON tenants(tenant_id);
                    CREATE INDEX IF NOT EXISTS idx_sessions_tenant ON tenant_sessions(tenant_id);
                    CREATE INDEX IF NOT EXISTS idx_sessions_expires ON tenant_sessions(expires_at);
                    CREATE INDEX IF NOT EXISTS idx_security_events_tenant ON security_events(tenant_id);
                    CREATE INDEX IF NOT EXISTS idx_security_events_type ON security_events(event_type);
                """)
            logger.info("Multi-tenant database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def create_tenant(self, tenant_id: str, company_name: str, tier: TenantTier, admin_email: str) -> TenantContext:
        """Create a new tenant with specified parameters (sync version)."""
        from datetime import datetime

        from src.domain.entities.tenant_context import TenantResourceLimits, TenantUsageStats

        # Create resource limits based on tier
        resource_limits = TenantResourceLimits.get_tier_limits(tier)

        # Create tenant context
        tenant_context = TenantContext(
            tenant_id=tenant_id,
            tenant_name=company_name,
            organization=company_name,
            tier=tier,
            resource_limits=resource_limits,
            current_usage=TenantUsageStats(),
            encryption_key_id=f"key_{tenant_id[:8]}",
            database_schema=f"schema_{tenant_id}",
            vector_collection_name=f"tenant_{tenant_id}_docs",
            custom_settings={},
            feature_flags={},
            admin_email=admin_email,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            status=TenantStatus.ACTIVE
        )

        # Store tenant
        tenant_data = json.dumps(tenant_context.to_dict())

        with sqlite3.connect(self.database_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO tenants (tenant_id, tenant_data, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (
                tenant_context.tenant_id,
                tenant_data,
                tenant_context.created_at.isoformat(),
                tenant_context.updated_at.isoformat()
            ))

        # Add to cache
        self._tenant_cache[tenant_context.tenant_id] = tenant_context

        logger.info(f"Created new tenant: {tenant_context.tenant_id}")
        return tenant_context

    async def create_tenant_async(self, tenant_context: TenantContext) -> bool:
        """Create a new tenant in the system."""
        try:
            tenant_data = json.dumps(tenant_context.to_dict())

            with sqlite3.connect(self.database_path) as conn:
                conn.execute("""
                    INSERT INTO tenants (tenant_id, tenant_data, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (
                    tenant_context.tenant_id,
                    tenant_data,
                    tenant_context.created_at.isoformat(),
                    tenant_context.updated_at.isoformat()
                ))

            # Add to cache
            self._tenant_cache[tenant_context.tenant_id] = tenant_context

            # Log security event
            await self._log_security_event(
                tenant_context.tenant_id,
                "tenant_created",
                {"tenant_name": tenant_context.tenant_name, "tier": tenant_context.tier.value}
            )

            logger.info(f"Created new tenant: {tenant_context.tenant_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to create tenant {tenant_context.tenant_id}: {e}")
            return False

    def get_tenant(self, tenant_id: str) -> Optional[TenantContext]:
        """Get tenant context by ID (sync version)."""
        # Check cache first
        if tenant_id in self._tenant_cache:
            return self._tenant_cache[tenant_id]

        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.execute(
                    "SELECT tenant_data FROM tenants WHERE tenant_id = ?",
                    (tenant_id,)
                )
                row = cursor.fetchone()

                if row:
                    tenant_data = json.loads(row[0])
                    tenant_context = TenantContext.from_dict(tenant_data)

                    # Add to cache
                    self._tenant_cache[tenant_id] = tenant_context
                    return tenant_context

            return None

        except Exception as e:
            logger.error(f"Failed to get tenant {tenant_id}: {e}")
            return None

    async def get_tenant_async(self, tenant_id: str) -> Optional[TenantContext]:
        """Get tenant context by ID."""
        # Check cache first
        if tenant_id in self._tenant_cache:
            return self._tenant_cache[tenant_id]

        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.execute(
                    "SELECT tenant_data FROM tenants WHERE tenant_id = ?",
                    (tenant_id,)
                )
                row = cursor.fetchone()

                if row:
                    tenant_data = json.loads(row[0])
                    tenant_context = TenantContext.from_dict(tenant_data)

                    # Add to cache
                    self._tenant_cache[tenant_id] = tenant_context
                    return tenant_context

            return None

        except Exception as e:
            logger.error(f"Failed to get tenant {tenant_id}: {e}")
            return None

    async def update_tenant(self, tenant_context: TenantContext) -> bool:
        """Update tenant information."""
        try:
            tenant_data = json.dumps(tenant_context.to_dict())

            with sqlite3.connect(self.database_path) as conn:
                conn.execute("""
                    UPDATE tenants
                    SET tenant_data = ?, updated_at = ?
                    WHERE tenant_id = ?
                """, (
                    tenant_data,
                    tenant_context.updated_at.isoformat(),
                    tenant_context.tenant_id
                ))

            # Update cache
            self._tenant_cache[tenant_context.tenant_id] = tenant_context

            logger.info(f"Updated tenant: {tenant_context.tenant_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update tenant {tenant_context.tenant_id}: {e}")
            return False

    async def authenticate_tenant_request(self,
                                        token: str,
                                        ip_address: Optional[str] = None,
                                        user_agent: Optional[str] = None) -> Optional[TenantSession]:
        """Authenticate a tenant request using JWT token."""
        try:
            # Decode JWT token
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])

            session_id = payload.get('session_id')
            tenant_id = payload.get('tenant_id')
            user_id = payload.get('user_id')

            if not all([session_id, tenant_id, user_id]):
                await self._log_security_event(
                    tenant_id or "unknown",
                    "invalid_token",
                    {"reason": "missing_claims", "ip": ip_address}
                )
                return None

            # Check session exists and is valid
            session = await self._get_session(session_id)
            if not session or session.expires_at < datetime.now():
                await self._log_security_event(
                    tenant_id,
                    "expired_session",
                    {"session_id": session_id, "ip": ip_address}
                )
                return None

            # Check tenant status
            tenant = await self.get_tenant(tenant_id)
            if not tenant or tenant.status != TenantStatus.ACTIVE:
                await self._log_security_event(
                    tenant_id,
                    "inactive_tenant_access",
                    {"status": tenant.status.value if tenant else "not_found", "ip": ip_address}
                )
                return None

            # Check rate limits
            if not await self._check_rate_limit(tenant_id, tenant.resource_limits.rate_limit_per_minute):
                await self._log_security_event(
                    tenant_id,
                    "rate_limit_exceeded",
                    {"ip": ip_address}
                )
                raise SecurityViolation(
                    f"Rate limit exceeded for tenant {tenant_id}",
                    tenant_id,
                    "rate_limit"
                )

            # Update session activity
            session.ip_address = ip_address
            session.user_agent = user_agent

            logger.debug(f"Authenticated session for tenant: {tenant_id}")
            return session

        except jwt.ExpiredSignatureError:
            await self._log_security_event(
                "unknown",
                "expired_token",
                {"ip": ip_address}
            )
            return None
        except jwt.InvalidTokenError as e:
            await self._log_security_event(
                "unknown",
                "invalid_token",
                {"error": str(e), "ip": ip_address}
            )
            return None
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None

    async def create_tenant_user(self,
                               tenant_id: str,
                               email: str,
                               password: str,
                               permissions: list[str]) -> bool:
        """Create a new user for a tenant."""
        try:
            # Verify tenant exists
            tenant = await self.get_tenant(tenant_id)
            if not tenant:
                return False

            # Hash password
            password_hash = self._hash_password(password)
            user_id = f"{tenant_id}_{hashlib.md5(email.encode()).hexdigest()[:8]}"

            with sqlite3.connect(self.database_path) as conn:
                conn.execute("""
                    INSERT INTO tenant_users (user_id, tenant_id, email, password_hash, permissions, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    tenant_id,
                    email,
                    password_hash,
                    json.dumps(permissions),
                    datetime.now().isoformat()
                ))

            await self._log_security_event(
                tenant_id,
                "user_created",
                {"email": email, "permissions": permissions}
            )

            logger.info(f"Created user {email} for tenant {tenant_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to create user {email} for tenant {tenant_id}: {e}")
            return False

    async def login_tenant_user(self,
                              email: str,
                              password: str,
                              ip_address: Optional[str] = None,
                              user_agent: Optional[str] = None) -> Optional[str]:
        """Login a tenant user and return JWT token."""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.execute("""
                    SELECT user_id, tenant_id, password_hash, permissions
                    FROM tenant_users
                    WHERE email = ?
                """, (email,))
                row = cursor.fetchone()

                if not row:
                    await self._log_security_event(
                        "unknown",
                        "login_failed",
                        {"email": email, "reason": "user_not_found", "ip": ip_address}
                    )
                    return None

                user_id, tenant_id, password_hash, permissions_json = row
                permissions = json.loads(permissions_json)

                # Verify password
                if not self._verify_password(password, password_hash):
                    await self._log_security_event(
                        tenant_id,
                        "login_failed",
                        {"email": email, "reason": "invalid_password", "ip": ip_address}
                    )
                    return None

                # Check tenant is active
                tenant = await self.get_tenant(tenant_id)
                if not tenant or tenant.status != TenantStatus.ACTIVE:
                    await self._log_security_event(
                        tenant_id,
                        "login_failed",
                        {"email": email, "reason": "inactive_tenant", "ip": ip_address}
                    )
                    return None

                # Create session
                session = await self._create_session(
                    tenant_id, user_id, email, permissions, ip_address, user_agent
                )

                # Generate JWT token
                token = self._generate_jwt_token(session)

                # Update last login
                conn.execute("""
                    UPDATE tenant_users
                    SET last_login = ?
                    WHERE user_id = ?
                """, (datetime.now().isoformat(), user_id))

                await self._log_security_event(
                    tenant_id,
                    "login_successful",
                    {"email": email, "ip": ip_address}
                )

                logger.info(f"User {email} logged in for tenant {tenant_id}")
                return token

        except Exception as e:
            logger.error(f"Login failed for {email}: {e}")
            return None

    async def logout_tenant_user(self, session_id: str) -> bool:
        """Logout a tenant user by invalidating their session."""
        try:
            with sqlite3.connect(self.database_path) as conn:
                # Get session info for logging
                cursor = conn.execute("""
                    SELECT tenant_id FROM tenant_sessions WHERE session_id = ?
                """, (session_id,))
                row = cursor.fetchone()

                if row:
                    tenant_id = row[0]

                    # Delete session
                    conn.execute("DELETE FROM tenant_sessions WHERE session_id = ?", (session_id,))

                    # Remove from cache
                    if session_id in self._session_cache:
                        del self._session_cache[session_id]

                    await self._log_security_event(
                        tenant_id,
                        "logout",
                        {"session_id": session_id}
                    )

                    logger.info(f"User logged out from session {session_id}")
                    return True

            return False

        except Exception as e:
            logger.error(f"Logout failed for session {session_id}: {e}")
            return False

    @asynccontextmanager
    async def tenant_context(self, session: TenantSession):
        """Context manager for tenant-isolated operations."""
        tenant = await self.get_tenant(session.tenant_id)
        if not tenant:
            raise SecurityViolation(f"Tenant not found: {session.tenant_id}",
                                  session.tenant_id, "tenant_not_found")

        # Set up tenant-specific context
        try:
            # This would typically set database schema, vector collection, etc.
            logger.debug(f"Entering tenant context: {tenant.tenant_id}")
            yield tenant
        finally:
            # Clean up tenant-specific context
            logger.debug(f"Exiting tenant context: {tenant.tenant_id}")

    async def _get_session(self, session_id: str) -> Optional[TenantSession]:
        """Get session from cache or database."""
        # Check cache first
        if session_id in self._session_cache:
            return self._session_cache[session_id]

        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.execute("""
                    SELECT session_data FROM tenant_sessions
                    WHERE session_id = ? AND expires_at > ?
                """, (session_id, datetime.now().isoformat()))
                row = cursor.fetchone()

                if row:
                    session_data = json.loads(row[0])
                    session = TenantSession(
                        session_id=session_data['session_id'],
                        tenant_id=session_data['tenant_id'],
                        user_id=session_data['user_id'],
                        user_email=session_data['user_email'],
                        created_at=datetime.fromisoformat(session_data['created_at']),
                        expires_at=datetime.fromisoformat(session_data['expires_at']),
                        permissions=session_data['permissions'],
                        ip_address=session_data.get('ip_address'),
                        user_agent=session_data.get('user_agent')
                    )

                    # Add to cache
                    self._session_cache[session_id] = session
                    return session

            return None

        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None

    async def _create_session(self,
                            tenant_id: str,
                            user_id: str,
                            user_email: str,
                            permissions: list[str],
                            ip_address: Optional[str] = None,
                            user_agent: Optional[str] = None) -> TenantSession:
        """Create a new user session."""
        import secrets

        session_id = secrets.token_urlsafe(32)
        now = datetime.now()
        expires_at = now + self.session_duration

        session = TenantSession(
            session_id=session_id,
            tenant_id=tenant_id,
            user_id=user_id,
            user_email=user_email,
            created_at=now,
            expires_at=expires_at,
            permissions=permissions,
            ip_address=ip_address,
            user_agent=user_agent
        )

        # Store in database
        session_data = {
            'session_id': session_id,
            'tenant_id': tenant_id,
            'user_id': user_id,
            'user_email': user_email,
            'created_at': now.isoformat(),
            'expires_at': expires_at.isoformat(),
            'permissions': permissions,
            'ip_address': ip_address,
            'user_agent': user_agent
        }

        with sqlite3.connect(self.database_path) as conn:
            conn.execute("""
                INSERT INTO tenant_sessions (session_id, tenant_id, user_id, session_data, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                tenant_id,
                user_id,
                json.dumps(session_data),
                now.isoformat(),
                expires_at.isoformat()
            ))

        # Add to cache
        self._session_cache[session_id] = session

        return session

    def _generate_jwt_token(self, session: TenantSession) -> str:
        """Generate JWT token for session."""
        payload = {
            'session_id': session.session_id,
            'tenant_id': session.tenant_id,
            'user_id': session.user_id,
            'user_email': session.user_email,
            'permissions': session.permissions,
            'exp': session.expires_at,
            'iat': session.created_at
        }

        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)

    def _hash_password(self, password: str) -> str:
        """Hash password using PBKDF2."""
        import hashlib
        import secrets

        salt = secrets.token_hex(16)
        pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
        return f"{salt}:{pwdhash.hex()}"

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash."""
        import hashlib

        try:
            salt, stored_hash = password_hash.split(':')
            pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
            return pwdhash.hex() == stored_hash
        except:
            return False

    async def _check_rate_limit(self, tenant_id: str, limit_per_minute: int) -> bool:
        """Check if tenant is within rate limits."""
        if limit_per_minute <= 0:  # Unlimited
            return True

        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)

        # Clean old entries and check current count
        if tenant_id not in self._rate_limits:
            self._rate_limits[tenant_id] = []

        # Remove old entries
        self._rate_limits[tenant_id] = [
            timestamp for timestamp in self._rate_limits[tenant_id]
            if timestamp > minute_ago
        ]

        # Check if within limit
        if len(self._rate_limits[tenant_id]) >= limit_per_minute:
            return False

        # Add current request
        self._rate_limits[tenant_id].append(now)
        return True

    async def _log_security_event(self,
                                tenant_id: str,
                                event_type: str,
                                event_data: dict[str, Any],
                                ip_address: Optional[str] = None,
                                user_agent: Optional[str] = None):
        """Log security events for audit trail."""
        try:
            with sqlite3.connect(self.database_path) as conn:
                conn.execute("""
                    INSERT INTO security_events (tenant_id, event_type, event_data, ip_address, user_agent, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    tenant_id,
                    event_type,
                    json.dumps(event_data),
                    ip_address,
                    user_agent,
                    datetime.now().isoformat()
                ))
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")

    async def cleanup_expired_sessions(self):
        """Clean up expired sessions from database and cache."""
        try:
            now = datetime.now().isoformat()

            with sqlite3.connect(self.database_path) as conn:
                # Get expired session IDs
                cursor = conn.execute("""
                    SELECT session_id FROM tenant_sessions WHERE expires_at <= ?
                """, (now,))
                expired_sessions = [row[0] for row in cursor.fetchall()]

                # Delete expired sessions
                conn.execute("DELETE FROM tenant_sessions WHERE expires_at <= ?", (now,))

            # Remove from cache
            for session_id in expired_sessions:
                if session_id in self._session_cache:
                    del self._session_cache[session_id]

            if expired_sessions:
                logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")

        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")

    async def get_tenant_security_events(self,
                                       tenant_id: str,
                                       event_types: Optional[list[str]] = None,
                                       limit: int = 100) -> list[dict[str, Any]]:
        """Get security events for a tenant."""
        try:
            query = """
                SELECT event_type, event_data, ip_address, user_agent, timestamp
                FROM security_events
                WHERE tenant_id = ?
            """
            params = [tenant_id]

            if event_types:
                query += f" AND event_type IN ({','.join(['?' for _ in event_types])})"
                params.extend(event_types)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.execute(query, params)
                events = []

                for row in cursor.fetchall():
                    events.append({
                        'event_type': row[0],
                        'event_data': json.loads(row[1]),
                        'ip_address': row[2],
                        'user_agent': row[3],
                        'timestamp': row[4]
                    })

            return events

        except Exception as e:
            logger.error(f"Failed to get security events for tenant {tenant_id}: {e}")
            return []

    def create_session(self, tenant_id: str, user_id: str, user_email: str) -> str:
        """Create a new session for a user (sync version)."""
        import uuid

        session_id = str(uuid.uuid4())
        now = datetime.now()
        expires_at = now + self.session_duration

        session = TenantSession(
            session_id=session_id,
            tenant_id=tenant_id,
            user_id=user_id,
            user_email=user_email,
            created_at=now,
            expires_at=expires_at,
            permissions=["read", "write"]
        )

        # Store in cache
        self._session_cache[session_id] = session

        # Store in database
        session_data = json.dumps({
            "user_id": user_id,
            "user_email": user_email,
            "permissions": session.permissions
        })

        with sqlite3.connect(self.database_path) as conn:
            conn.execute("""
                INSERT INTO tenant_sessions (session_id, tenant_id, user_id, session_data, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                tenant_id,
                user_id,
                session_data,
                now.isoformat(),
                expires_at.isoformat()
            ))

        return session_id

    def validate_session(self, tenant_id: str, user_id: str) -> bool:
        """Validate if a session exists and is valid (sync version)."""
        # Check cache first
        for _session_id, session in self._session_cache.items():
            if session.tenant_id == tenant_id and session.user_id == user_id:
                if datetime.now() < session.expires_at:
                    return True

        # Check database
        with sqlite3.connect(self.database_path) as conn:
            cursor = conn.execute("""
                SELECT expires_at FROM tenant_sessions
                WHERE tenant_id = ? AND user_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (tenant_id, user_id))

            row = cursor.fetchone()
            if row:
                expires_at = datetime.fromisoformat(row[0])
                if datetime.now() < expires_at:
                    return True

        return False

    def get_tenant_usage(self, tenant_id: str) -> dict[str, Any]:
        """Get usage statistics for a tenant (sync version)."""
        # Simple mock implementation for testing
        return {
            "documents_today": 0,
            "documents_this_month": 0,
            "queries_today": 0,
            "storage_mb": 0.0,
            "storage_bytes": 0,
            "last_activity": datetime.now().isoformat()
        }

    def track_usage(self, tenant_id: str, resource_type: str, amount: int = 1):
        """Track resource usage for a tenant (sync version)."""
        # Simple implementation for testing
        logger.info(f"Tracking usage for tenant {tenant_id}: {resource_type} +{amount}")
        # In production, this would update usage counters in database
