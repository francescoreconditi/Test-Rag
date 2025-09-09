"""
Dashboard Embed System
======================

Embeddable dashboard components for external integration.
"""

import streamlit as st
from typing import Dict, Any, Optional, List
import json
import uuid
from datetime import datetime
from pathlib import Path
import base64

from src.presentation.ui.theme_manager import ThemeManager
from src.presentation.ui.dashboard_manager import DashboardManager, WidgetType
from src.core.security.multi_tenant_manager import MultiTenantManager

class EmbedConfig:
    """Configuration for embeddable dashboard."""
    
    def __init__(self, config: Dict[str, Any]):
        self.id = config.get('id', str(uuid.uuid4()))
        self.name = config['name']
        self.tenant_id = config['tenant_id']
        self.dashboard_id = config['dashboard_id']
        
        # Embed settings
        self.width = config.get('width', '100%')
        self.height = config.get('height', '600px')
        self.theme = config.get('theme', 'light')
        self.interactive = config.get('interactive', True)
        self.show_header = config.get('show_header', True)
        self.show_filters = config.get('show_filters', True)
        self.auto_refresh = config.get('auto_refresh', False)
        self.refresh_interval = config.get('refresh_interval', 300)  # seconds
        
        # Security settings
        self.allowed_domains = config.get('allowed_domains', [])
        self.api_key_required = config.get('api_key_required', True)
        self.public_access = config.get('public_access', False)
        
        # Metadata
        self.created_at = datetime.fromisoformat(config.get('created_at', datetime.now().isoformat()))
        self.updated_at = datetime.fromisoformat(config.get('updated_at', datetime.now().isoformat()))
        self.access_count = config.get('access_count', 0)
        self.last_accessed = config.get('last_accessed')
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'id': self.id,
            'name': self.name,
            'tenant_id': self.tenant_id,
            'dashboard_id': self.dashboard_id,
            'width': self.width,
            'height': self.height,
            'theme': self.theme,
            'interactive': self.interactive,
            'show_header': self.show_header,
            'show_filters': self.show_filters,
            'auto_refresh': self.auto_refresh,
            'refresh_interval': self.refresh_interval,
            'allowed_domains': self.allowed_domains,
            'api_key_required': self.api_key_required,
            'public_access': self.public_access,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'access_count': self.access_count,
            'last_accessed': self.last_accessed
        }

class DashboardEmbed:
    """Dashboard embedding system for external integration."""
    
    def __init__(self):
        """Initialize dashboard embed system."""
        self.embeds_dir = Path("data/dashboard_embeds")
        self.embeds_dir.mkdir(exist_ok=True)
        
        self.embed_configs: Dict[str, EmbedConfig] = {}
        self._load_embed_configs()
        
        # Initialize managers
        self.theme_manager = ThemeManager()
        
    def _load_embed_configs(self):
        """Load embed configurations from storage."""
        for config_file in self.embeds_dir.glob("*.json"):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    embed_config = EmbedConfig(config)
                    self.embed_configs[embed_config.id] = embed_config
            except Exception as e:
                st.error(f"Failed to load embed config {config_file}: {e}")
    
    def create_embed(self, config: Dict[str, Any]) -> EmbedConfig:
        """Create a new embeddable dashboard."""
        embed_config = EmbedConfig(config)
        
        # Save configuration
        self._save_embed_config(embed_config)
        
        # Add to memory
        self.embed_configs[embed_config.id] = embed_config
        
        return embed_config
    
    def update_embed(self, embed_id: str, updates: Dict[str, Any]) -> Optional[EmbedConfig]:
        """Update an existing embed configuration."""
        if embed_id not in self.embed_configs:
            return None
        
        embed_config = self.embed_configs[embed_id]
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(embed_config, key):
                setattr(embed_config, key, value)
        
        embed_config.updated_at = datetime.now()
        
        # Save updated configuration
        self._save_embed_config(embed_config)
        
        return embed_config
    
    def delete_embed(self, embed_id: str) -> bool:
        """Delete an embed configuration."""
        if embed_id not in self.embed_configs:
            return False
        
        # Remove configuration file
        config_file = self.embeds_dir / f"{embed_id}.json"
        if config_file.exists():
            config_file.unlink()
        
        # Remove from memory
        del self.embed_configs[embed_id]
        
        return True
    
    def generate_embed_code(self, embed_id: str, api_key: Optional[str] = None) -> Dict[str, str]:
        """Generate HTML embed code for dashboard."""
        if embed_id not in self.embed_configs:
            return {'error': 'Embed configuration not found'}
        
        embed_config = self.embed_configs[embed_id]
        
        # Generate base URL
        base_url = "http://localhost:8501"  # In production, use actual domain
        embed_url = f"{base_url}/embed/{embed_id}"
        
        if api_key and embed_config.api_key_required:
            embed_url += f"?api_key={api_key}"
        
        # Generate iframe code
        iframe_code = f"""<iframe 
    src="{embed_url}"
    width="{embed_config.width}" 
    height="{embed_config.height}"
    frameborder="0"
    scrolling="auto"
    sandbox="allow-scripts allow-same-origin">
</iframe>"""
        
        # Generate JavaScript integration code
        js_code = f"""
<script>
window.RAGDashboard = {{
    embedId: '{embed_id}',
    config: {json.dumps(embed_config.to_dict(), indent=2)},
    
    // Refresh dashboard
    refresh: function() {{
        const iframe = document.querySelector('iframe[src*="{embed_id}"]');
        if (iframe) {{
            iframe.src = iframe.src;
        }}
    }},
    
    // Auto-refresh setup
    setupAutoRefresh: function() {{
        if ({str(embed_config.auto_refresh).lower()}) {{
            setInterval(this.refresh, {embed_config.refresh_interval * 1000});
        }}
    }}
}};

// Initialize auto-refresh
document.addEventListener('DOMContentLoaded', function() {{
    window.RAGDashboard.setupAutoRefresh();
}});
</script>"""
        
        # Generate React component code
        react_code = f"""
import React, {{ useEffect, useState }} from 'react';

const RAGDashboardEmbed = ({{ apiKey }}) => {{
    const [refreshKey, setRefreshKey] = useState(0);
    
    useEffect(() => {{
        if ({str(embed_config.auto_refresh).lower()}) {{
            const interval = setInterval(() => {{
                setRefreshKey(prev => prev + 1);
            }}, {embed_config.refresh_interval * 1000});
            
            return () => clearInterval(interval);
        }}
    }}, []);
    
    const embedUrl = `{embed_url}&refresh=${{refreshKey}}`;
    
    return (
        <iframe
            src={{embedUrl}}
            width="{embed_config.width}"
            height="{embed_config.height}"
            frameBorder="0"
            scrolling="auto"
            sandbox="allow-scripts allow-same-origin"
        />
    );
}};

export default RAGDashboardEmbed;"""
        
        return {
            'iframe': iframe_code,
            'javascript': js_code,
            'react': react_code,
            'embed_url': embed_url,
            'embed_id': embed_id
        }
    
    def render_embedded_dashboard(self, embed_id: str, api_key: Optional[str] = None, 
                                 domain: Optional[str] = None) -> bool:
        """Render dashboard in embed mode."""
        if embed_id not in self.embed_configs:
            st.error("Dashboard embed not found")
            return False
        
        embed_config = self.embed_configs[embed_id]
        
        # Security checks
        if not self._validate_embed_access(embed_config, api_key, domain):
            st.error("Access denied")
            return False
        
        # Update access tracking
        embed_config.access_count += 1
        embed_config.last_accessed = datetime.now().isoformat()
        self._save_embed_config(embed_config)
        
        # Apply embed theme
        if embed_config.theme == 'dark':
            self.theme_manager.set_theme(self.theme_manager.ThemeMode.DARK)
        else:
            self.theme_manager.set_theme(self.theme_manager.ThemeMode.LIGHT)
        
        self.theme_manager.apply_theme()
        
        # Hide Streamlit elements for clean embed
        st.markdown("""
        <style>
            /* Hide Streamlit UI elements */
            .stApp > header {display: none;}
            .stApp > .main > div.block-container {padding-top: 1rem;}
            #MainMenu {display: none;}
            footer {display: none;}
            .stDeployButton {display: none;}
            
            /* Embed-specific styling */
            .embed-container {
                background: var(--background-color);
                border-radius: 8px;
                padding: 1rem;
                height: 100vh;
                overflow: auto;
            }
            
            .embed-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 1rem;
                padding-bottom: 0.5rem;
                border-bottom: 1px solid var(--divider-color);
            }
        </style>
        """, unsafe_allow_html=True)
        
        # Render embed container
        with st.container():
            # Optional header
            if embed_config.show_header:
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"<h3>{embed_config.name}</h3>", unsafe_allow_html=True)
                    with col2:
                        if embed_config.auto_refresh:
                            st.caption(f"Auto-refresh: {embed_config.refresh_interval}s")
            
            # Render dashboard
            try:
                # Get tenant context
                tenant_manager = MultiTenantManager()
                tenant_context = tenant_manager.get_tenant(embed_config.tenant_id)
                
                if not tenant_context:
                    st.error("Tenant not found")
                    return False
                
                # Initialize dashboard manager
                dashboard_manager = DashboardManager(embed_config.tenant_id)
                
                # Data provider for widgets
                def embed_data_provider(request: str, widget=None):
                    # Simplified data provider for embed mode
                    import random
                    
                    mock_data = {
                        'total_documents': {'value': random.randint(100, 500), 'delta': random.randint(-10, 20)},
                        'queries_today': {'value': random.randint(20, 100), 'delta': random.randint(-5, 15)},
                        'avg_response_time': {'value': f"{random.uniform(0.5, 2.0):.2f}s", 'delta': None},
                        'active_users': {'value': random.randint(5, 25), 'delta': random.randint(-2, 5)}
                    }
                    
                    return mock_data.get(request, {'value': 0, 'delta': None})
                
                # Render the dashboard
                dashboard_manager.render_dashboard(embed_config.dashboard_id, embed_data_provider)
                
                # Auto-refresh logic
                if embed_config.auto_refresh:
                    import time
                    time.sleep(embed_config.refresh_interval)
                    st.rerun()
                
                return True
                
            except Exception as e:
                st.error(f"Error rendering dashboard: {e}")
                return False
    
    def get_embed_analytics(self, embed_id: str) -> Dict[str, Any]:
        """Get analytics for an embed."""
        if embed_id not in self.embed_configs:
            return {'error': 'Embed not found'}
        
        embed_config = self.embed_configs[embed_id]
        
        return {
            'embed_id': embed_id,
            'name': embed_config.name,
            'total_views': embed_config.access_count,
            'last_accessed': embed_config.last_accessed,
            'created_at': embed_config.created_at.isoformat(),
            'is_active': embed_config.last_accessed is not None,
            'settings': {
                'theme': embed_config.theme,
                'auto_refresh': embed_config.auto_refresh,
                'public_access': embed_config.public_access
            }
        }
    
    def list_embeds(self, tenant_id: Optional[str] = None) -> List[EmbedConfig]:
        """List all embed configurations."""
        embeds = list(self.embed_configs.values())
        
        if tenant_id:
            embeds = [e for e in embeds if e.tenant_id == tenant_id]
        
        return sorted(embeds, key=lambda x: x.created_at, reverse=True)
    
    def _validate_embed_access(self, embed_config: EmbedConfig, api_key: Optional[str], 
                             domain: Optional[str]) -> bool:
        """Validate access to embedded dashboard."""
        # Public access check
        if embed_config.public_access:
            return True
        
        # API key check
        if embed_config.api_key_required and not api_key:
            return False
        
        # Domain whitelist check
        if embed_config.allowed_domains and domain:
            if domain not in embed_config.allowed_domains:
                return False
        
        return True
    
    def _save_embed_config(self, embed_config: EmbedConfig):
        """Save embed configuration to file."""
        config_file = self.embeds_dir / f"{embed_config.id}.json"
        with open(config_file, 'w') as f:
            json.dump(embed_config.to_dict(), f, indent=2)

def render_embed_management_ui():
    """Render UI for managing dashboard embeds."""
    st.header("🔗 Dashboard Embed Management")
    
    # Check authentication
    if 'tenant_context' not in st.session_state:
        st.warning("Please login to manage dashboard embeds")
        return
    
    tenant_context = st.session_state.tenant_context
    embed_system = DashboardEmbed()
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["📋 Manage Embeds", "➕ Create Embed", "📊 Analytics"])
    
    with tab1:
        # List existing embeds
        embeds = embed_system.list_embeds(tenant_context.tenant_id)
        
        if not embeds:
            st.info("No dashboard embeds created yet")
        else:
            for embed_config in embeds:
                with st.expander(f"🔗 {embed_config.name}", expanded=False):
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.write(f"**Dashboard ID:** {embed_config.dashboard_id}")
                        st.write(f"**Theme:** {embed_config.theme}")
                        st.write(f"**Size:** {embed_config.width} x {embed_config.height}")
                        st.write(f"**Views:** {embed_config.access_count}")
                        
                        if embed_config.last_accessed:
                            st.write(f"**Last Accessed:** {embed_config.last_accessed}")
                    
                    with col2:
                        if st.button(f"📋 Get Code", key=f"code_{embed_config.id}"):
                            embed_code = embed_system.generate_embed_code(embed_config.id)
                            
                            st.markdown("### 🔗 Embed Code")
                            
                            code_tab1, code_tab2, code_tab3 = st.tabs(["HTML/iframe", "JavaScript", "React"])
                            
                            with code_tab1:
                                st.code(embed_code['iframe'], language='html')
                                st.caption("Copy this code to embed the dashboard in any website")
                            
                            with code_tab2:
                                st.code(embed_code['javascript'], language='javascript')
                                st.caption("Advanced integration with auto-refresh functionality")
                            
                            with code_tab3:
                                st.code(embed_code['react'], language='javascript')
                                st.caption("React component for modern web applications")
                        
                        if st.button(f"🗑️ Delete", key=f"delete_{embed_config.id}"):
                            if embed_system.delete_embed(embed_config.id):
                                st.success("Embed deleted successfully")
                                st.rerun()
    
    with tab2:
        # Create new embed
        st.subheader("Create New Dashboard Embed")
        
        # Get available dashboards
        dashboard_manager = DashboardManager(tenant_context.tenant_id)
        dashboards = dashboard_manager.list_layouts()
        
        if not dashboards:
            st.warning("No dashboards available. Create a dashboard first.")
            return
        
        with st.form("create_embed"):
            embed_name = st.text_input("Embed Name", placeholder="Sales Dashboard Embed")
            
            dashboard_options = [d['name'] for d in dashboards]
            selected_dashboard_idx = st.selectbox("Select Dashboard", range(len(dashboard_options)), format_func=lambda x: dashboard_options[x])
            selected_dashboard_id = dashboards[selected_dashboard_idx]['id']
            
            col1, col2 = st.columns(2)
            with col1:
                width = st.text_input("Width", value="100%")
                theme = st.selectbox("Theme", ["light", "dark"])
                show_header = st.checkbox("Show Header", value=True)
                auto_refresh = st.checkbox("Auto Refresh", value=False)
            
            with col2:
                height = st.text_input("Height", value="600px")
                public_access = st.checkbox("Public Access", value=False)
                show_filters = st.checkbox("Show Filters", value=True)
                refresh_interval = st.number_input("Refresh Interval (seconds)", value=300, min_value=30)
            
            # Advanced settings
            with st.expander("🔒 Security Settings"):
                api_key_required = st.checkbox("Require API Key", value=not public_access)
                allowed_domains = st.text_area("Allowed Domains (one per line)", placeholder="example.com\napp.company.com")
            
            if st.form_submit_button("🚀 Create Embed", type="primary"):
                embed_config = {
                    'name': embed_name,
                    'tenant_id': tenant_context.tenant_id,
                    'dashboard_id': selected_dashboard_id,
                    'width': width,
                    'height': height,
                    'theme': theme,
                    'show_header': show_header,
                    'show_filters': show_filters,
                    'auto_refresh': auto_refresh,
                    'refresh_interval': refresh_interval,
                    'public_access': public_access,
                    'api_key_required': api_key_required,
                    'allowed_domains': [d.strip() for d in allowed_domains.split('\n') if d.strip()]
                }
                
                try:
                    new_embed = embed_system.create_embed(embed_config)
                    st.success(f"✅ Embed '{embed_name}' created successfully!")
                    st.info(f"Embed ID: {new_embed.id}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to create embed: {e}")
    
    with tab3:
        # Analytics
        st.subheader("📊 Embed Analytics")
        
        embeds = embed_system.list_embeds(tenant_context.tenant_id)
        
        if not embeds:
            st.info("No embeds to analyze")
        else:
            # Summary metrics
            total_views = sum(e.access_count for e in embeds)
            active_embeds = len([e for e in embeds if e.last_accessed])
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Embeds", len(embeds))
            with col2:
                st.metric("Total Views", total_views)
            with col3:
                st.metric("Active Embeds", active_embeds)
            
            # Detailed analytics
            st.markdown("### 📋 Embed Performance")
            
            analytics_data = []
            for embed_config in embeds:
                analytics = embed_system.get_embed_analytics(embed_config.id)
                analytics_data.append({
                    'Name': analytics['name'],
                    'Views': analytics['total_views'],
                    'Last Accessed': analytics['last_accessed'] or 'Never',
                    'Theme': analytics['settings']['theme'],
                    'Public': analytics['settings']['public_access']
                })
            
            if analytics_data:
                import pandas as pd
                df = pd.DataFrame(analytics_data)
                st.dataframe(df, use_container_width=True)

# Streamlit page for embed management
if __name__ == "__main__":
    render_embed_management_ui()