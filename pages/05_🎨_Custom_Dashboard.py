"""
Customizable Dashboard Page with Drag-and-Drop and Dark Mode
=============================================================

Interactive dashboard with customizable widgets and theme support.
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any
import json

# Import custom managers
from src.presentation.ui.theme_manager import ThemeManager, ThemeMode
from src.presentation.ui.dashboard_manager import (
    DashboardManager, WidgetType, WidgetSize
)
from src.core.security.multi_tenant_manager import MultiTenantManager
from services.rag_engine import RAGEngine

# Page configuration
st.set_page_config(
    page_title="Custom Dashboard - Business Intelligence RAG",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize managers
@st.cache_resource
def get_theme_manager():
    """Get cached theme manager instance."""
    return ThemeManager()

@st.cache_resource
def get_dashboard_manager(tenant_id: str = "default"):
    """Get cached dashboard manager instance."""
    return DashboardManager(tenant_id)

@st.cache_resource
def get_rag_engine(tenant_id: str = "default"):
    """Get cached RAG engine instance."""
    tenant_context = None
    if tenant_id != "default" and 'tenant_context' in st.session_state:
        tenant_context = st.session_state.tenant_context
    return RAGEngine(tenant_context=tenant_context)

def get_mock_data(metric: str) -> Dict[str, Any]:
    """Get mock data for widgets."""
    import random
    
    mock_data = {
        'total_documents': {
            'value': random.randint(500, 1500),
            'delta': random.randint(-10, 50)
        },
        'queries_today': {
            'value': random.randint(50, 200),
            'delta': random.randint(-5, 20)
        },
        'avg_response_time': {
            'value': f"{random.uniform(0.5, 2.5):.2f}s",
            'delta': f"{random.uniform(-0.5, 0.5):.2f}s"
        },
        'active_users': {
            'value': random.randint(10, 50),
            'delta': random.randint(-2, 5)
        },
        'query_volume': pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=30),
            'value': np.random.randn(30).cumsum() + 100
        }).to_dict('records'),
        'doc_categories': pd.DataFrame({
            'category': ['Financial', 'Technical', 'Legal', 'Marketing', 'Other'],
            'value': [35, 25, 20, 15, 5]
        }).to_dict('records'),
        'top_queries': pd.DataFrame({
            'Query': ['Revenue 2023', 'Profit margin Q4', 'Customer growth', 'Market share', 'Cost analysis'],
            'Count': [145, 89, 67, 45, 32],
            'Avg Time': ['0.8s', '1.2s', '0.5s', '0.9s', '1.1s'],
            'Success Rate': ['98%', '95%', '99%', '97%', '96%']
        }).to_dict('records'),
        'timeline_events': [
            {'time': '2 min ago', 'event': 'Document uploaded', 'user': 'admin@demo.com', 'type': 'upload'},
            {'time': '15 min ago', 'event': 'Query executed', 'user': 'user1@demo.com', 'type': 'query'},
            {'time': '1 hour ago', 'event': 'Index rebuilt', 'user': 'system', 'type': 'system'},
            {'time': '3 hours ago', 'event': 'User login', 'user': 'admin@demo.com', 'type': 'auth'},
            {'time': '5 hours ago', 'event': 'Report generated', 'user': 'user2@demo.com', 'type': 'report'},
        ]
    }
    
    return mock_data.get(metric, {'value': 0, 'delta': None})

def data_provider(request: str, widget=None) -> Any:
    """Provide data for dashboard widgets."""
    # Handle None or empty request
    if not request:
        return {'value': 0, 'delta': None}
    
    if request.startswith('custom_'):
        # Handle custom widget rendering
        if widget:
            st.info(f"Custom widget: {widget.title}")
        return None
    
    return get_mock_data(request)

def render_edit_mode(dashboard_manager: DashboardManager):
    """Render dashboard edit mode interface."""
    st.subheader("✏️ Edit Dashboard")
    
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        # Widget library
        st.markdown("### 📦 Widget Library")
        
        widget_types = {
            "KPI Metric": WidgetType.KPI,
            "Chart": WidgetType.CHART,
            "Table": WidgetType.TABLE,
            "Timeline": WidgetType.TIMELINE,
            "Text": WidgetType.TEXT,
            "Custom": WidgetType.CUSTOM
        }
        
        selected_widget = st.selectbox("Select widget type", list(widget_types.keys()))
        widget_title = st.text_input("Widget title", f"New {selected_widget}")
        
        size_options = {
            "Small (1x1)": WidgetSize.SMALL,
            "Medium (2x1)": WidgetSize.MEDIUM,
            "Large (2x2)": WidgetSize.LARGE,
            "Wide (4x1)": WidgetSize.WIDE,
            "Tall (1x2)": WidgetSize.TALL,
            "Full (4x2)": WidgetSize.FULL
        }
        
        selected_size = st.selectbox("Widget size", list(size_options.keys()), index=1)
        
        col_a, col_b = st.columns(2)
        with col_a:
            pos_x = st.number_input("Position X", min_value=0, max_value=3, value=0)
        with col_b:
            pos_y = st.number_input("Position Y", min_value=0, max_value=5, value=0)
        
        if st.button("➕ Add Widget", type="primary", use_container_width=True):
            current_layout = st.session_state.get('current_layout_id', 'default')
            
            # Create new widget
            new_widget = dashboard_manager.create_widget(
                widget_type=widget_types[selected_widget],
                title=widget_title,
                position=(pos_x, pos_y),
                size=size_options[selected_size],
                content={'metric': 'total_documents'} if selected_widget == "KPI Metric" else {}
            )
            
            # Add to layout
            if dashboard_manager.add_widget_to_layout(current_layout, new_widget):
                st.success(f"✅ Added {widget_title}")
                st.rerun()
            else:
                st.error("Failed to add widget")
    
    with col2:
        # Layout properties
        st.markdown("### 🎨 Layout Properties")
        
        current_layout = dashboard_manager.load_layout(
            st.session_state.get('current_layout_id', 'default')
        )
        
        if current_layout:
            st.text_input("Layout name", current_layout.name, key="layout_name")
            st.text_area("Description", current_layout.description, key="layout_desc")
            
            grid_cols = st.slider("Grid columns", 2, 6, current_layout.grid_columns)
            grid_rows = st.slider("Grid rows", 2, 10, current_layout.grid_rows)
            
            if st.button("💾 Save Layout", type="primary", use_container_width=True):
                current_layout.name = st.session_state.layout_name
                current_layout.description = st.session_state.layout_desc
                current_layout.grid_columns = grid_cols
                current_layout.grid_rows = grid_rows
                dashboard_manager.save_layout(current_layout)
                st.success("✅ Layout saved")
    
    with col3:
        # Widget list
        st.markdown("### 📋 Current Widgets")
        
        if current_layout:
            for widget in current_layout.widgets:
                with st.expander(f"{widget.title}", expanded=False):
                    st.text(f"Type: {widget.type.value}")
                    st.text(f"Pos: ({widget.position['x']}, {widget.position['y']})")
                    st.text(f"Size: {widget.size['width']}x{widget.size['height']}")
                    
                    if st.button(f"🗑️ Remove", key=f"remove_{widget.id}"):
                        dashboard_manager.remove_widget_from_layout(
                            current_layout.id, widget.id
                        )
                        st.rerun()

def main():
    """Main dashboard page."""
    
    # Check authentication
    if 'tenant_context' not in st.session_state:
        st.warning("⚠️ Please login to access the dashboard")
        if st.button("🔐 Go to Login"):
            st.switch_page("pages/00_🔐_Login.py")
        return
    
    # Get tenant context
    tenant_context = st.session_state.tenant_context
    tenant_id = tenant_context.tenant_id
    
    # Initialize managers
    theme_manager = get_theme_manager()
    dashboard_manager = get_dashboard_manager(tenant_id)
    rag_engine = get_rag_engine(tenant_id)
    
    # Apply theme
    theme_manager.apply_theme()
    
    # Page header
    st.markdown(f"""
    <h1 style='text-align: center; color: var(--primary-color);'>
        🎨 Custom Dashboard
    </h1>
    <p style='text-align: center; color: var(--text-secondary);'>
        Personalized analytics for {tenant_context.organization}
    </p>
    """, unsafe_allow_html=True)
    
    # Sidebar controls
    with st.sidebar:
        st.markdown("### 🎛️ Dashboard Controls")
        
        # Theme toggle
        theme_manager.render_theme_toggle()
        
        st.divider()
        
        # Layout selector
        st.markdown("### 📐 Layout Management")
        
        layouts = dashboard_manager.list_layouts()
        layout_names = [l['name'] for l in layouts]
        layout_ids = [l['id'] for l in layouts]
        
        if layouts:
            selected_idx = st.selectbox(
                "Select layout",
                range(len(layout_names)),
                format_func=lambda x: layout_names[x],
                key="layout_selector"
            )
            
            current_layout_id = layout_ids[selected_idx]
            st.session_state.current_layout_id = current_layout_id
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📋 Duplicate", use_container_width=True):
                    new_name = f"Copy of {layout_names[selected_idx]}"
                    new_layout = dashboard_manager.duplicate_layout(
                        current_layout_id, new_name
                    )
                    if new_layout:
                        st.success(f"Created: {new_name}")
                        st.rerun()
            
            with col2:
                if current_layout_id != "default":
                    if st.button("🗑️ Delete", use_container_width=True):
                        if dashboard_manager.delete_layout(current_layout_id):
                            st.success("Layout deleted")
                            st.session_state.current_layout_id = "default"
                            st.rerun()
        
        # Create new layout
        with st.expander("➕ Create New Layout"):
            new_layout_name = st.text_input("Layout name")
            new_layout_desc = st.text_area("Description")
            
            if st.button("Create Layout", type="primary", use_container_width=True):
                if new_layout_name:
                    import uuid
                    from src.presentation.ui.dashboard_manager import DashboardLayout
                    
                    new_layout = DashboardLayout(
                        id=str(uuid.uuid4())[:8],
                        name=new_layout_name,
                        description=new_layout_desc,
                        widgets=[]
                    )
                    dashboard_manager.save_layout(new_layout)
                    st.success(f"Created: {new_layout_name}")
                    st.rerun()
        
        st.divider()
        
        # View mode toggle
        st.markdown("### 👁️ View Mode")
        edit_mode = st.checkbox("Edit Mode", value=False)
        
        # Auto-refresh toggle
        auto_refresh = st.checkbox("Auto Refresh", value=False)
        if auto_refresh:
            refresh_interval = st.slider("Refresh interval (seconds)", 5, 60, 10)
            st.info(f"Refreshing every {refresh_interval} seconds")
        
        st.divider()
        
        # Dashboard statistics
        st.markdown("### 📊 Dashboard Stats")
        
        stats = rag_engine.get_index_stats()
        
        st.metric("Total Documents", stats.get('total_vectors', 0))
        st.metric("Index Size", f"{stats.get('index_size_mb', 0):.1f} MB")
        
        # Get usage from tenant manager
        if tenant_context:
            manager = MultiTenantManager()
            usage = manager.get_tenant_usage(tenant_id)
            
            st.metric("Queries Today", usage.get('queries_today', 0))
            st.metric("Storage Used", f"{usage.get('storage_mb', 0):.1f} MB")
    
    # Main content area
    if edit_mode:
        # Edit mode interface
        render_edit_mode(dashboard_manager)
        st.divider()
        st.markdown("### 👁️ Dashboard Preview")
    
    # Render dashboard
    current_layout_id = st.session_state.get('current_layout_id', 'default')
    
    if current_layout_id:
        dashboard_manager.render_dashboard(current_layout_id, data_provider)
    else:
        st.info("No dashboard layout selected. Please create or select a layout.")
    
    # Auto-refresh logic
    if auto_refresh:
        import time
        time.sleep(refresh_interval)
        st.rerun()
    
    # Footer with theme info
    st.divider()
    current_theme = theme_manager.get_current_theme()
    st.caption(f"""
    🎨 Theme: {current_theme.value.title()} | 
    📐 Layout: {current_layout_id} | 
    🏢 Tenant: {tenant_context.organization} ({tenant_context.tier.value})
    """)

if __name__ == "__main__":
    main()