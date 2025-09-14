"""Security UI components for Streamlit authentication and RLS."""

import streamlit as st
from typing import Optional, Dict, Any
from datetime import datetime

from src.core.security import AuthenticationService, UserContext, UserRole, AccessControlService, SecurityViolationError
from services.secure_rag_engine import SecureRAGEngine


class SecurityUI:
    """UI components for security and authentication."""

    def __init__(self):
        self.auth_service = AuthenticationService()
        self.access_control = AccessControlService()

    def render_login_form(self) -> bool:
        """Render login form and handle authentication."""
        st.title("🔐 Login - Business Intelligence RAG System")

        # Check if already logged in
        if self._is_authenticated():
            user_context = st.session_state.user_context
            st.success(f"✅ Authenticated as {user_context.username} ({user_context.role.value})")

            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("📊 Continue to Application", type="primary"):
                    st.session_state.show_login = False
                    st.rerun()

            with col2:
                if st.button("🚪 Logout"):
                    self._logout()
                    st.rerun()

            return True

        # Login form
        st.markdown("### Enter your credentials")

        with st.form("login_form"):
            col1, col2 = st.columns([2, 1])

            with col1:
                username = st.text_input("👤 Username", placeholder="Enter your username")
                password = st.text_input("🔑 Password", type="password", placeholder="Enter your password")
                tenant_id = st.text_input("🏢 Tenant ID (optional)", placeholder="Leave empty for default tenant",
                                        help="Specify tenant ID if you have access to multiple tenants")

            with col2:
                st.markdown("<br>", unsafe_allow_html=True)  # Spacing
                submitted = st.form_submit_button("🔓 Login", type="primary")

        # Demo users info
        with st.expander("🎭 Demo Users (for testing)"):
            demo_users = [
                ("admin", "admin123", "System Administrator - Full access"),
                ("analyst.azienda.a", "analyst123", "Analyst - Access to Azienda A data"),
                ("manager.bu.sales", "manager123", "BU Manager - Sales department"),
                ("viewer.general", "viewer123", "Viewer - Read-only access"),
                ("tenant.admin.a", "tenantadmin123", "Tenant Admin - Azienda A"),
            ]

            for user, pwd, desc in demo_users:
                st.code(f"Username: {user} | Password: {pwd}")
                st.caption(desc)
                st.divider()

        # Handle login
        if submitted and username and password:
            with st.spinner("🔍 Authenticating..."):
                # Authenticate with optional tenant_id
                result = self.auth_service.authenticate(username, password, tenant_id)

                if result.success:
                    # Store session
                    st.session_state.user_context = result.user_context
                    st.session_state.session_token = result.session_token
                    st.session_state.authenticated = True
                    st.session_state.show_login = False

                    # Initialize secure RAG engine
                    st.session_state.secure_rag_engine = SecureRAGEngine(result.user_context)

                    # Create tenant context for compatibility with multi-tenant system
                    if tenant_id or result.user_context.tenant_id:
                        from src.core.security.multi_tenant_manager import MultiTenantManager
                        from src.domain.entities.tenant_context import TenantContext, TenantTier

                        manager = MultiTenantManager()
                        effective_tenant_id = tenant_id or result.user_context.tenant_id

                        # Get or create tenant
                        tenant = manager.get_tenant(effective_tenant_id)
                        if not tenant:
                            # Create tenant if doesn't exist
                            tenant = manager.create_tenant(
                                tenant_id=effective_tenant_id,
                                company_name=f"Company {effective_tenant_id}",
                                tier=TenantTier.PREMIUM,
                                admin_email=f"{username}@company.com"
                            )

                        st.session_state.tenant_context = tenant

                    st.success(f"✅ Welcome {result.user_context.username}!")
                    if tenant_id:
                        st.info(f"🏢 Connected to tenant: {tenant_id}")
                    st.balloons()
                    st.rerun()
                else:
                    st.error(f"❌ {result.error_message}")

        return False

    def render_user_info_sidebar(self):
        """Render user information in sidebar."""
        if not self._is_authenticated():
            return

        user_context = st.session_state.user_context

        st.sidebar.markdown("---")
        st.sidebar.markdown("### 👤 User Info")

        # User details
        st.sidebar.info(
            f"**User:** {user_context.username}\n"
            f"**Role:** {user_context.role.value}\n"
            f"**Tenant:** {user_context.tenant_id or 'Global'}\n"
            f"**Max Classification:** {user_context.max_classification_level.name}"
        )

        # Access summary
        if user_context.accessible_entities:
            st.sidebar.markdown("**📊 Accessible Entities:**")
            for entity in user_context.accessible_entities[:5]:  # Show first 5
                st.sidebar.caption(f"• {entity}")
            if len(user_context.accessible_entities) > 5:
                st.sidebar.caption(f"... and {len(user_context.accessible_entities) - 5} more")

        if user_context.cost_centers:
            st.sidebar.markdown("**💰 Cost Centers:**")
            for cdc in user_context.cost_centers[:3]:  # Show first 3
                st.sidebar.caption(f"• {cdc}")
            if len(user_context.cost_centers) > 3:
                st.sidebar.caption(f"... and {len(user_context.cost_centers) - 3} more")

        # Session info
        if user_context.login_time:
            session_duration = datetime.utcnow() - user_context.login_time
            hours, remainder = divmod(int(session_duration.total_seconds()), 3600)
            minutes, _ = divmod(remainder, 60)
            st.sidebar.caption(f"⏱️ Session: {hours:02d}:{minutes:02d}")

        # Logout button
        if st.sidebar.button("🚪 Logout", key="sidebar_logout"):
            self._logout()
            st.rerun()

    def render_security_dashboard(self):
        """Render security dashboard for admins."""
        if not self._is_authenticated():
            st.error("Authentication required")
            return

        user_context = st.session_state.user_context

        if not user_context.is_admin():
            st.error("Admin access required")
            return

        st.title("🛡️ Security Dashboard")

        # Get user statistics
        secure_rag = st.session_state.get("secure_rag_engine")
        if not secure_rag:
            st.error("Secure RAG Engine not initialized")
            return

        user_stats = secure_rag.get_user_stats()

        # User info section
        st.header("👤 Current User")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("User ID", user_stats["user_info"]["user_id"])
            st.metric("Role", user_stats["user_info"]["role"])

        with col2:
            st.metric("Tenant", user_stats["user_info"]["tenant_id"] or "Global")
            st.metric("Session Duration", user_stats["user_info"]["session_duration"] or "N/A")

        with col3:
            st.metric("Access Level", user_stats["access_summary"]["max_classification"])
            st.metric("Permissions", len(user_stats["access_summary"]["permissions"]))

        # Security statistics
        if "security_stats" in user_stats:
            st.header("📊 Security Statistics")
            security_stats = user_stats["security_stats"]

            # Facts by tenant
            if "facts_by_tenant" in security_stats:
                st.subheader("Facts by Tenant")
                tenant_data = security_stats["facts_by_tenant"]
                if tenant_data:
                    st.bar_chart(tenant_data)
                else:
                    st.info("No tenant data available")

            # Facts by classification
            if "facts_by_classification" in security_stats:
                st.subheader("Facts by Classification Level")
                class_data = security_stats["facts_by_classification"]
                if class_data:
                    st.bar_chart(class_data)
                else:
                    st.info("No classification data available")

            # Top entities
            if "top_entities" in security_stats:
                st.subheader("Top Entities by Fact Count")
                entity_data = security_stats["top_entities"]
                if entity_data:
                    st.bar_chart(entity_data)
                else:
                    st.info("No entity data available")

        # Active sessions
        st.header("🔗 Active Sessions")
        active_sessions = self.auth_service.get_active_sessions()

        if active_sessions:
            for session in active_sessions:
                with st.expander(f"👤 {session['username']} ({session['role']})"):
                    st.json(
                        {
                            "User ID": session["user_id"],
                            "Tenant": session["tenant_id"] or "Global",
                            "Login Time": session["login_time"],
                            "Last Activity": session["last_activity"],
                        }
                    )
        else:
            st.info("No active sessions found")

        # Session cleanup
        if st.button("🧹 Cleanup Expired Sessions"):
            cleaned = self.auth_service.cleanup_expired_sessions()
            st.success(f"Cleaned up {cleaned} expired sessions")

    def check_permission(self, resource: str, operation: str = "read") -> bool:
        """Check if current user has permission."""
        if not self._is_authenticated():
            return False

        user_context = st.session_state.user_context
        return self.access_control.validate_access_attempt(user_context, resource, operation=operation)

    def require_permission(self, resource: str, operation: str = "read", message: str = None):
        """Require permission or show error."""
        if not self.check_permission(resource, operation):
            error_msg = message or f"You don't have permission to {operation} {resource}"
            st.error(f"🚫 {error_msg}")
            st.stop()

    def _is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        return st.session_state.get("authenticated", False) and st.session_state.get("user_context") is not None

    def _logout(self):
        """Handle user logout."""
        # Cleanup session
        if hasattr(st.session_state, "secure_rag_engine") and st.session_state.secure_rag_engine:
            st.session_state.secure_rag_engine.cleanup_session()

        # Clear session state
        for key in ["authenticated", "user_context", "session_token", "secure_rag_engine"]:
            if key in st.session_state:
                del st.session_state[key]

        st.session_state.show_login = True
        st.success("👋 Logged out successfully")


def init_security_session():
    """Initialize security-related session state."""
    if "show_login" not in st.session_state:
        st.session_state.show_login = True

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False


def require_authentication():
    """Decorator-like function to require authentication."""
    init_security_session()

    if not st.session_state.get("authenticated", False):
        st.session_state.show_login = True
        return False

    return True


# Initialize security UI instance for reuse
security_ui = SecurityUI()
