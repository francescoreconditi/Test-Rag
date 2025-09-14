"""Authentication service for Row-level Security."""

import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from .user_context import UserContext, UserRole, DataClassification, create_user_context

logger = logging.getLogger(__name__)


@dataclass
class AuthenticationResult:
    """Result of authentication attempt."""

    success: bool
    user_context: Optional[UserContext] = None
    error_message: Optional[str] = None
    session_token: Optional[str] = None


@dataclass
class UserCredentials:
    """User credentials and metadata."""

    user_id: str
    username: str
    password_hash: str
    salt: str
    role: UserRole
    tenant_id: Optional[str] = None
    is_active: bool = True
    created_at: datetime = None
    last_login: Optional[datetime] = None
    failed_login_attempts: int = 0

    # Access permissions
    accessible_entities: List[str] = None
    accessible_periods: List[str] = None
    accessible_regions: List[str] = None
    cost_centers: List[str] = None
    department: Optional[str] = None
    max_classification_level: DataClassification = DataClassification.INTERNAL

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.accessible_entities is None:
            self.accessible_entities = []
        if self.accessible_periods is None:
            self.accessible_periods = []
        if self.accessible_regions is None:
            self.accessible_regions = []
        if self.cost_centers is None:
            self.cost_centers = []


class AuthenticationService:
    """Service for user authentication and session management."""

    def __init__(self):
        """Initialize authentication service."""
        self.logger = logging.getLogger(__name__)
        self._users_db: Dict[str, UserCredentials] = {}
        self._sessions: Dict[str, UserContext] = {}
        self.session_timeout_hours = 8
        self.max_failed_attempts = 5
        self.lockout_duration_minutes = 30

        # Initialize with demo users
        self._initialize_demo_users()

    def _initialize_demo_users(self):
        """Initialize demo users for testing."""
        demo_users = [
            {
                "user_id": "admin",
                "username": "admin",
                "password": "admin123",
                "role": UserRole.ADMIN,
                "tenant_id": None,
                "max_classification_level": DataClassification.RESTRICTED,
            },
            {
                "user_id": "analyst_a",
                "username": "analyst.azienda.a",
                "password": "analyst123",
                "role": UserRole.ANALYST,
                "tenant_id": "tenant_a",
                "accessible_entities": ["Azienda_A", "BU_Finance"],
                "accessible_periods": ["2023", "Q1_2024", "Q2_2024"],
                "cost_centers": ["CDC_100", "CDC_110", "CDC_120"],
                "max_classification_level": DataClassification.INTERNAL,
            },
            {
                "user_id": "manager_b",
                "username": "manager.bu.sales",
                "password": "manager123",
                "role": UserRole.BU_MANAGER,
                "tenant_id": "tenant_b",
                "accessible_entities": ["Azienda_B"],
                "accessible_periods": ["2023", "2024"],
                "cost_centers": ["CDC_200", "CDC_210"],
                "department": "Sales",
                "max_classification_level": DataClassification.CONFIDENTIAL,
            },
            {
                "user_id": "viewer_c",
                "username": "viewer.general",
                "password": "viewer123",
                "role": UserRole.VIEWER,
                "tenant_id": "tenant_c",
                "accessible_entities": ["Azienda_C"],
                "accessible_periods": ["2023"],
                "max_classification_level": DataClassification.PUBLIC,
            },
            {
                "user_id": "tenant_admin_a",
                "username": "tenant.admin.a",
                "password": "tenantadmin123",
                "role": UserRole.TENANT_ADMIN,
                "tenant_id": "tenant_a",
                "accessible_entities": ["Azienda_A", "BU_Finance", "BU_Operations"],
                "accessible_periods": ["2022", "2023", "2024"],
                "cost_centers": ["CDC_100", "CDC_110", "CDC_120", "CDC_130"],
                "max_classification_level": DataClassification.CONFIDENTIAL,
            },
        ]

        for user_data in demo_users:
            password = user_data.pop("password")
            self.create_user(password=password, **user_data)

        self.logger.info(f"Initialized {len(demo_users)} demo users")

    def _hash_password(self, password: str, salt: str = None) -> tuple[str, str]:
        """Hash password with salt."""
        if salt is None:
            salt = secrets.token_hex(32)

        # Use PBKDF2 for password hashing
        password_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            100000,  # 100k iterations
        ).hex()

        return password_hash, salt

    def create_user(
        self, user_id: str, username: str, password: str, role: UserRole, tenant_id: Optional[str] = None, **kwargs
    ) -> bool:
        """Create new user."""
        try:
            if user_id in self._users_db:
                self.logger.warning(f"User {user_id} already exists")
                return False

            password_hash, salt = self._hash_password(password)

            user_credentials = UserCredentials(
                user_id=user_id,
                username=username,
                password_hash=password_hash,
                salt=salt,
                role=role,
                tenant_id=tenant_id,
                **kwargs,
            )

            self._users_db[user_id] = user_credentials
            self.logger.info(f"Created user {user_id} with role {role.value}")
            return True

        except Exception as e:
            self.logger.error(f"Error creating user {user_id}: {e}")
            return False

    def authenticate(self, username: str, password: str, tenant_id: Optional[str] = None) -> AuthenticationResult:
        """Authenticate user with username/password and optional tenant_id.

        Args:
            username: User's username
            password: User's password
            tenant_id: Optional tenant ID to override user's default tenant
        """
        try:
            # Find user by username
            user_creds = None
            for creds in self._users_db.values():
                if creds.username == username:
                    user_creds = creds
                    break

            if not user_creds:
                self.logger.warning(f"Authentication failed: user {username} not found")
                return AuthenticationResult(success=False, error_message="Invalid username or password")

            # Check if user is active
            if not user_creds.is_active:
                self.logger.warning(f"Authentication failed: user {username} is inactive")
                return AuthenticationResult(success=False, error_message="Account is inactive")

            # Check for account lockout
            if user_creds.failed_login_attempts >= self.max_failed_attempts:
                # Check if lockout period has expired
                if user_creds.last_login and (
                    datetime.utcnow() - user_creds.last_login < timedelta(minutes=self.lockout_duration_minutes)
                ):
                    return AuthenticationResult(
                        success=False, error_message="Account is locked due to too many failed attempts"
                    )
                else:
                    # Reset failed attempts after lockout period
                    user_creds.failed_login_attempts = 0

            # Verify password
            password_hash, _ = self._hash_password(password, user_creds.salt)

            if password_hash != user_creds.password_hash:
                # Increment failed attempts
                user_creds.failed_login_attempts += 1
                self.logger.warning(
                    f"Authentication failed for {username}: invalid password "
                    f"(attempt {user_creds.failed_login_attempts})"
                )
                return AuthenticationResult(success=False, error_message="Invalid username or password")

            # Authentication successful
            user_creds.failed_login_attempts = 0
            user_creds.last_login = datetime.utcnow()

            # Use provided tenant_id if specified, otherwise use user's default
            effective_tenant_id = tenant_id if tenant_id else user_creds.tenant_id

            # For admin users, allow access to any tenant or no tenant
            if user_creds.role == UserRole.ADMIN and tenant_id:
                effective_tenant_id = tenant_id

            # Create user context with effective tenant
            user_context = create_user_context(
                user_id=user_creds.user_id,
                username=user_creds.username,
                role=user_creds.role,
                tenant_id=effective_tenant_id,
                accessible_entities=user_creds.accessible_entities,
                accessible_periods=user_creds.accessible_periods,
                accessible_regions=user_creds.accessible_regions,
                cost_centers=user_creds.cost_centers,
                department=user_creds.department,
                # max_classification_level is set automatically by role configuration
            )

            # Generate session token
            session_token = secrets.token_urlsafe(32)
            user_context.session_id = session_token

            # Store session
            self._sessions[session_token] = user_context

            self.logger.info(
                f"Authentication successful for {username} "
                f"(role: {user_creds.role.value}, tenant: {effective_tenant_id})"
            )

            return AuthenticationResult(success=True, user_context=user_context, session_token=session_token)

        except Exception as e:
            self.logger.error(f"Error during authentication for {username}: {e}")
            return AuthenticationResult(success=False, error_message="Authentication error")

    def validate_session(self, session_token: str) -> Optional[UserContext]:
        """Validate session token and return user context."""
        try:
            if not session_token or session_token not in self._sessions:
                return None

            user_context = self._sessions[session_token]

            # Check session timeout
            if user_context.last_activity and datetime.utcnow() - user_context.last_activity > timedelta(
                hours=self.session_timeout_hours
            ):
                # Session expired
                del self._sessions[session_token]
                self.logger.info(f"Session expired for user {user_context.user_id}")
                return None

            # Update last activity
            user_context.update_activity()

            return user_context

        except Exception as e:
            self.logger.error(f"Error validating session {session_token}: {e}")
            return None

    def logout(self, session_token: str) -> bool:
        """Logout user by invalidating session."""
        try:
            if session_token in self._sessions:
                user_context = self._sessions[session_token]
                del self._sessions[session_token]
                self.logger.info(f"User {user_context.user_id} logged out")
                return True
            return False

        except Exception as e:
            self.logger.error(f"Error during logout: {e}")
            return False

    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Get list of active sessions."""
        sessions = []
        current_time = datetime.utcnow()

        for token, context in self._sessions.items():
            if not context.last_activity or current_time - context.last_activity <= timedelta(
                hours=self.session_timeout_hours
            ):
                sessions.append(
                    {
                        "session_token": token,
                        "user_id": context.user_id,
                        "username": context.username,
                        "role": context.role.value,
                        "tenant_id": context.tenant_id,
                        "login_time": context.login_time.isoformat() if context.login_time else None,
                        "last_activity": context.last_activity.isoformat() if context.last_activity else None,
                    }
                )

        return sessions

    def cleanup_expired_sessions(self):
        """Remove expired sessions."""
        current_time = datetime.utcnow()
        expired_tokens = []

        for token, context in self._sessions.items():
            if context.last_activity and current_time - context.last_activity > timedelta(
                hours=self.session_timeout_hours
            ):
                expired_tokens.append(token)

        for token in expired_tokens:
            user_context = self._sessions[token]
            del self._sessions[token]
            self.logger.info(f"Cleaned up expired session for user {user_context.user_id}")

        return len(expired_tokens)

    def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user information (without sensitive data)."""
        if user_id not in self._users_db:
            return None

        creds = self._users_db[user_id]
        return {
            "user_id": creds.user_id,
            "username": creds.username,
            "role": creds.role.value,
            "tenant_id": creds.tenant_id,
            "is_active": creds.is_active,
            "created_at": creds.created_at.isoformat(),
            "last_login": creds.last_login.isoformat() if creds.last_login else None,
            "accessible_entities": creds.accessible_entities,
            "accessible_periods": creds.accessible_periods,
            "accessible_regions": creds.accessible_regions,
            "cost_centers": creds.cost_centers,
            "department": creds.department,
            "max_classification_level": creds.max_classification_level.value,
        }
