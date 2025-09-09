"""
Multi-Tenant Login Page for Streamlit Application
==================================================

Provides authentication and tenant management for the RAG system.
"""

import streamlit as st
import requests
import json
from datetime import datetime, timedelta
from typing import Optional

from src.core.security.multi_tenant_manager import MultiTenantManager
from src.domain.entities.tenant_context import TenantTier

# Page configuration
st.set_page_config(
    page_title="Login - Business Intelligence RAG",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize multi-tenant manager
@st.cache_resource
def get_tenant_manager():
    """Get cached tenant manager instance."""
    return MultiTenantManager()


def login_via_api(email: str, password: str, tenant_id: Optional[str] = None) -> dict:
    """Login via FastAPI backend."""
    try:
        response = requests.post(
            "http://localhost:8000/auth/login",
            json={
                "email": email,
                "password": password,
                "tenant_id": tenant_id
            }
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Login failed: {response.text}"}
    except Exception as e:
        return {"error": f"Connection error: {str(e)}"}


def create_demo_tenant(email: str, company_name: str, tier: str) -> Optional[str]:
    """Create a demo tenant for testing."""
    manager = get_tenant_manager()
    
    # Generate tenant ID from company name
    tenant_id = f"tenant_{company_name.lower().replace(' ', '_')}"
    
    try:
        # Check if tenant exists
        existing = manager.get_tenant(tenant_id)
        if existing:
            return tenant_id
        
        # Create new tenant
        tier_enum = TenantTier[tier.upper()]
        tenant = manager.create_tenant(
            tenant_id=tenant_id,
            company_name=company_name,
            tier=tier_enum,
            admin_email=email
        )
        
        return tenant.tenant_id if tenant else None
        
    except Exception as e:
        st.error(f"Failed to create tenant: {str(e)}")
        return None


def main():
    """Main login page."""
    
    # Custom CSS for login page
    st.markdown("""
    <style>
        .login-container {
            max-width: 500px;
            margin: auto;
            padding: 2rem;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .company-logo {
            text-align: center;
            font-size: 3rem;
            margin-bottom: 2rem;
        }
        .tier-badge {
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.875rem;
            font-weight: bold;
            margin-left: 0.5rem;
        }
        .tier-basic { background: #f0f0f0; color: #666; }
        .tier-premium { background: #ffd700; color: #333; }
        .tier-enterprise { background: #4169e1; color: white; }
        .tier-custom { background: #8b008b; color: white; }
    </style>
    """, unsafe_allow_html=True)
    
    # Check if already logged in
    if 'tenant_context' in st.session_state and st.session_state.tenant_context:
        tenant = st.session_state.tenant_context
        
        st.success(f"✅ Logged in as **{tenant.organization}**")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Tenant ID", tenant.tenant_id)
        with col2:
            tier_color = tenant.tier.value.lower()
            st.markdown(f"**Tier:** <span class='tier-badge tier-{tier_color}'>{tenant.tier.value}</span>", 
                       unsafe_allow_html=True)
        with col3:
            if st.button("🚪 Logout", use_container_width=True):
                # Clear session
                for key in ['tenant_context', 'jwt_token', 'user_email']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
        
        st.divider()
        
        # Show tenant info
        with st.expander("📊 Tenant Details", expanded=False):
            st.json({
                "tenant_id": tenant.tenant_id,
                "company_name": tenant.organization,
                "tier": tenant.tier.value,
                "created_at": tenant.created_at.isoformat(),
                "status": tenant.status.value,
                "limits": {
                    "max_documents_per_month": tenant.resource_limits.max_documents_per_month,
                    "max_storage_gb": tenant.resource_limits.max_storage_gb,
                    "max_queries_per_day": tenant.resource_limits.max_queries_per_day,
                    "max_concurrent_users": tenant.resource_limits.max_concurrent_users
                }
            })
        
        # Navigation
        st.info("👈 Use the sidebar to navigate to different sections of the application")
        
        # Quick links
        st.subheader("🚀 Quick Links")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📄 RAG Documents", use_container_width=True):
                st.switch_page("pages/01_📄_RAG_Documenti.py")
        with col2:
            if st.button("📊 CSV Analysis", use_container_width=True):
                st.switch_page("pages/02_📊_Analisi_CSV.py")
                
    else:
        # Login form
        st.markdown("<div class='company-logo'>🏢</div>", unsafe_allow_html=True)
        st.title("Business Intelligence RAG System")
        st.subheader("Multi-Tenant Login")
        
        tab1, tab2 = st.tabs(["🔑 Login", "🆕 Create Demo Tenant"])
        
        with tab1:
            with st.form("login_form"):
                email = st.text_input("Email", placeholder="admin@company.com")
                password = st.text_input("Password", type="password", placeholder="Enter password")
                tenant_id = st.text_input("Tenant ID (optional)", placeholder="Leave empty for auto-detection")
                
                col1, col2 = st.columns(2)
                with col1:
                    submit = st.form_submit_button("🔐 Login", use_container_width=True, type="primary")
                with col2:
                    demo = st.form_submit_button("🎮 Demo Login", use_container_width=True)
                
                if submit:
                    if email and password:
                        with st.spinner("Authenticating..."):
                            # Try API login first
                            result = login_via_api(email, password, tenant_id)
                            
                            if "error" in result:
                                # Fallback to local authentication for demo
                                manager = get_tenant_manager()
                                
                                # Create demo tenant if needed
                                domain = email.split("@")[1] if "@" in email else "demo"
                                tenant_id = tenant_id or f"tenant_{domain.replace('.', '_')}"
                                
                                tenant = manager.get_tenant(tenant_id)
                                if not tenant:
                                    # Create demo tenant
                                    tenant = manager.create_tenant(
                                        tenant_id=tenant_id,
                                        company_name=f"{domain.title()} Company",
                                        tier=TenantTier.PREMIUM,
                                        admin_email=email
                                    )
                                
                                if tenant:
                                    # Create session
                                    user_id = f"user_{email.replace('@', '_').replace('.', '_')}"
                                    session_token = manager.create_session(
                                        tenant_id=tenant_id,
                                        user_id=user_id,
                                        user_email=email
                                    )
                                    
                                    # Store in session state
                                    st.session_state.tenant_context = tenant
                                    st.session_state.user_email = email
                                    st.session_state.session_token = session_token
                                    
                                    st.success(f"✅ Logged in successfully as {tenant.organization}!")
                                    st.rerun()
                                else:
                                    st.error("Failed to authenticate")
                            else:
                                # API login successful
                                manager = get_tenant_manager()
                                tenant = manager.get_tenant(result["tenant_id"])
                                
                                if not tenant:
                                    # Create tenant from API response
                                    tenant = manager.create_tenant(
                                        tenant_id=result["tenant_id"],
                                        company_name=f"Company {result['tenant_id']}",
                                        tier=TenantTier[result["tier"].upper()],
                                        admin_email=email
                                    )
                                
                                st.session_state.tenant_context = tenant
                                st.session_state.jwt_token = result["access_token"]
                                st.session_state.user_email = email
                                
                                st.success(f"✅ Logged in successfully!")
                                st.rerun()
                    else:
                        st.error("Please enter both email and password")
                
                if demo:
                    # Quick demo login
                    demo_email = "demo@example.com"
                    demo_tenant_id = "tenant_demo"
                    
                    manager = get_tenant_manager()
                    tenant = manager.get_tenant(demo_tenant_id)
                    
                    if not tenant:
                        tenant = manager.create_tenant(
                            tenant_id=demo_tenant_id,
                            company_name="Demo Company",
                            tier=TenantTier.PREMIUM,
                            admin_email=demo_email
                        )
                    
                    # Create session
                    session_token = manager.create_session(
                        tenant_id=demo_tenant_id,
                        user_id="demo_user",
                        user_email=demo_email
                    )
                    
                    st.session_state.tenant_context = tenant
                    st.session_state.user_email = demo_email
                    st.session_state.session_token = session_token
                    
                    st.success("✅ Logged in with demo account!")
                    st.rerun()
        
        with tab2:
            st.info("Create a demo tenant for testing the multi-tenant features")
            
            with st.form("create_tenant_form"):
                company_name = st.text_input("Company Name", placeholder="Acme Corporation")
                admin_email = st.text_input("Admin Email", placeholder="admin@acme.com")
                tier = st.selectbox(
                    "Subscription Tier",
                    ["BASIC", "PREMIUM", "ENTERPRISE", "CUSTOM"],
                    index=1
                )
                
                # Show tier details
                tier_details = {
                    "BASIC": "100 docs/month, 1GB storage, 50 queries/day",
                    "PREMIUM": "1,000 docs/month, 10GB storage, 500 queries/day",
                    "ENTERPRISE": "10,000 docs/month, 100GB storage, 5,000 queries/day",
                    "CUSTOM": "Unlimited resources"
                }
                st.caption(f"📋 {tier_details[tier]}")
                
                if st.form_submit_button("🏢 Create Tenant", use_container_width=True, type="primary"):
                    if company_name and admin_email:
                        tenant_id = create_demo_tenant(admin_email, company_name, tier)
                        if tenant_id:
                            st.success(f"✅ Tenant created successfully! ID: **{tenant_id}**")
                            st.info("You can now login with this tenant")
                    else:
                        st.error("Please fill all fields")
        
        # Footer
        st.divider()
        st.caption("🔒 Multi-tenant Business Intelligence RAG System - ZCS Company")


if __name__ == "__main__":
    main()