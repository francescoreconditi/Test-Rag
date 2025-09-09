"""
Theme Manager for Dark/Light Mode Support
==========================================

Manages application themes with smooth transitions and persistent preferences.
"""

import streamlit as st
from typing import Dict, Any, Optional
import json
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

class ThemeMode(Enum):
    """Available theme modes."""
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"  # Follow system preference

@dataclass
class ThemeColors:
    """Theme color definitions."""
    # Primary colors
    primary: str
    primary_dark: str
    primary_light: str
    
    # Background colors
    background: str
    surface: str
    surface_variant: str
    
    # Text colors
    text_primary: str
    text_secondary: str
    text_disabled: str
    
    # Status colors
    success: str
    warning: str
    error: str
    info: str
    
    # Border and divider
    border: str
    divider: str
    
    # Chart colors
    chart_colors: list

class ThemeManager:
    """Manages application themes and styling."""
    
    # Predefined themes
    THEMES = {
        ThemeMode.LIGHT: ThemeColors(
            primary="#1976d2",
            primary_dark="#115293",
            primary_light="#4791db",
            background="#ffffff",
            surface="#f5f5f5",
            surface_variant="#e0e0e0",
            text_primary="#000000de",
            text_secondary="#00000099",
            text_disabled="#00000061",
            success="#4caf50",
            warning="#ff9800",
            error="#f44336",
            info="#2196f3",
            border="#0000001f",
            divider="#0000001f",
            chart_colors=["#1976d2", "#42a5f5", "#66bb6a", "#ffa726", "#ef5350", "#ab47bc", "#26c6da"]
        ),
        ThemeMode.DARK: ThemeColors(
            primary="#90caf9",
            primary_dark="#5d99c6",
            primary_light="#c3fdff",
            background="#121212",
            surface="#1e1e1e",
            surface_variant="#2e2e2e",
            text_primary="#ffffffde",
            text_secondary="#ffffff99",
            text_disabled="#ffffff61",
            success="#66bb6a",
            warning="#ffa726",
            error="#ef5350",
            info="#42a5f5",
            border="#ffffff1f",
            divider="#ffffff1f",
            chart_colors=["#90caf9", "#64b5f6", "#81c784", "#ffb74d", "#e57373", "#ba68c8", "#4dd0e1"]
        )
    }
    
    def __init__(self):
        """Initialize theme manager."""
        self.preferences_file = Path("data/user_preferences.json")
        self.preferences_file.parent.mkdir(exist_ok=True)
    
    def get_current_theme(self) -> ThemeMode:
        """Get current theme mode from session state or preferences."""
        if 'theme_mode' not in st.session_state:
            # Load from preferences or default to light
            st.session_state.theme_mode = self.load_theme_preference()
        return st.session_state.theme_mode
    
    def set_theme(self, mode: ThemeMode):
        """Set the current theme mode."""
        st.session_state.theme_mode = mode
        self.save_theme_preference(mode)
    
    def toggle_theme(self):
        """Toggle between light and dark themes."""
        current = self.get_current_theme()
        new_theme = ThemeMode.DARK if current == ThemeMode.LIGHT else ThemeMode.LIGHT
        self.set_theme(new_theme)
    
    def get_theme_colors(self) -> ThemeColors:
        """Get colors for current theme."""
        mode = self.get_current_theme()
        if mode == ThemeMode.AUTO:
            # Default to light for auto mode (could be enhanced with system detection)
            mode = ThemeMode.LIGHT
        return self.THEMES[mode]
    
    def load_theme_preference(self) -> ThemeMode:
        """Load theme preference from file."""
        try:
            if self.preferences_file.exists():
                with open(self.preferences_file, 'r') as f:
                    prefs = json.load(f)
                    theme_str = prefs.get('theme', 'light')
                    return ThemeMode(theme_str)
        except:
            pass
        return ThemeMode.LIGHT
    
    def save_theme_preference(self, mode: ThemeMode):
        """Save theme preference to file."""
        try:
            prefs = {}
            if self.preferences_file.exists():
                with open(self.preferences_file, 'r') as f:
                    prefs = json.load(f)
            
            prefs['theme'] = mode.value
            
            with open(self.preferences_file, 'w') as f:
                json.dump(prefs, f, indent=2)
        except Exception as e:
            st.warning(f"Could not save theme preference: {e}")
    
    def apply_theme(self):
        """Apply current theme to Streamlit app."""
        colors = self.get_theme_colors()
        mode = self.get_current_theme()
        
        # Generate CSS based on current theme
        css = f"""
        <style>
            /* Root variables */
            :root {{
                --primary-color: {colors.primary};
                --primary-dark: {colors.primary_dark};
                --primary-light: {colors.primary_light};
                --background-color: {colors.background};
                --surface-color: {colors.surface};
                --surface-variant: {colors.surface_variant};
                --text-primary: {colors.text_primary};
                --text-secondary: {colors.text_secondary};
                --text-disabled: {colors.text_disabled};
                --success-color: {colors.success};
                --warning-color: {colors.warning};
                --error-color: {colors.error};
                --info-color: {colors.info};
                --border-color: {colors.border};
                --divider-color: {colors.divider};
            }}
            
            /* Main app container */
            .stApp {{
                background-color: {colors.background};
                color: {colors.text_primary};
            }}
            
            /* Sidebar */
            section[data-testid="stSidebar"] {{
                background-color: {colors.surface};
                border-right: 1px solid {colors.divider};
            }}
            
            section[data-testid="stSidebar"] .stMarkdown {{
                color: {colors.text_primary};
            }}
            
            /* Headers */
            h1, h2, h3, h4, h5, h6 {{
                color: {colors.text_primary} !important;
            }}
            
            /* Text elements */
            .stMarkdown, .stText {{
                color: {colors.text_primary};
            }}
            
            /* Metrics */
            div[data-testid="metric-container"] {{
                background-color: {colors.surface};
                border: 1px solid {colors.border};
                padding: 1rem;
                border-radius: 0.5rem;
                box-shadow: 0 1px 3px {colors.border};
            }}
            
            div[data-testid="metric-container"] label {{
                color: {colors.text_secondary};
            }}
            
            div[data-testid="metric-container"] [data-testid="stMetricValue"] {{
                color: {colors.text_primary};
            }}
            
            /* Buttons */
            .stButton > button {{
                background-color: {colors.primary};
                color: white;
                border: none;
                transition: all 0.3s ease;
            }}
            
            .stButton > button:hover {{
                background-color: {colors.primary_dark};
                transform: translateY(-1px);
                box-shadow: 0 4px 8px {colors.border};
            }}
            
            /* Input fields */
            .stTextInput > div > div > input,
            .stSelectbox > div > div > select,
            .stTextArea > div > div > textarea {{
                background-color: {colors.surface};
                color: {colors.text_primary};
                border: 1px solid {colors.border};
            }}
            
            /* Expanders */
            .streamlit-expanderHeader {{
                background-color: {colors.surface};
                color: {colors.text_primary};
                border: 1px solid {colors.border};
            }}
            
            /* Info, warning, error boxes */
            .stAlert {{
                background-color: {colors.surface_variant};
                color: {colors.text_primary};
                border-left: 4px solid {colors.primary};
            }}
            
            div[data-baseweb="notification"][kind="info"] {{
                background-color: {colors.info}22;
                border-left-color: {colors.info};
            }}
            
            div[data-baseweb="notification"][kind="warning"] {{
                background-color: {colors.warning}22;
                border-left-color: {colors.warning};
            }}
            
            div[data-baseweb="notification"][kind="error"] {{
                background-color: {colors.error}22;
                border-left-color: {colors.error};
            }}
            
            div[data-baseweb="notification"][kind="success"] {{
                background-color: {colors.success}22;
                border-left-color: {colors.success};
            }}
            
            /* Tables */
            .stDataFrame {{
                background-color: {colors.surface};
            }}
            
            .stDataFrame thead tr th {{
                background-color: {colors.surface_variant} !important;
                color: {colors.text_primary} !important;
            }}
            
            .stDataFrame tbody tr {{
                background-color: {colors.surface};
                color: {colors.text_primary};
            }}
            
            .stDataFrame tbody tr:hover {{
                background-color: {colors.surface_variant};
            }}
            
            /* Tabs */
            .stTabs [data-baseweb="tab-list"] {{
                background-color: {colors.surface};
                border-bottom: 1px solid {colors.divider};
            }}
            
            .stTabs [data-baseweb="tab"] {{
                color: {colors.text_secondary};
            }}
            
            .stTabs [aria-selected="true"] {{
                color: {colors.primary} !important;
                border-bottom: 2px solid {colors.primary};
            }}
            
            /* Code blocks */
            .stCodeBlock {{
                background-color: {colors.surface_variant};
            }}
            
            /* Plotly charts dark mode support */
            {'''
            .js-plotly-plot .plotly .modebar {{
                background-color: transparent !important;
            }}
            
            .js-plotly-plot .plotly .modebar-btn {{
                color: {colors.text_secondary} !important;
            }}
            ''' if mode == ThemeMode.DARK else ''}
            
            /* Custom scrollbar */
            ::-webkit-scrollbar {{
                width: 8px;
                height: 8px;
            }}
            
            ::-webkit-scrollbar-track {{
                background: {colors.surface};
            }}
            
            ::-webkit-scrollbar-thumb {{
                background: {colors.border};
                border-radius: 4px;
            }}
            
            ::-webkit-scrollbar-thumb:hover {{
                background: {colors.text_disabled};
            }}
            
            /* Smooth transitions */
            * {{
                transition: background-color 0.3s ease, color 0.3s ease, border-color 0.3s ease;
            }}
        </style>
        """
        
        st.markdown(css, unsafe_allow_html=True)
    
    def render_theme_toggle(self, location: str = "sidebar"):
        """Render theme toggle button."""
        colors = self.get_theme_colors()
        current_mode = self.get_current_theme()
        
        # Theme toggle with icon
        icon = "🌙" if current_mode == ThemeMode.LIGHT else "☀️"
        label = "Dark Mode" if current_mode == ThemeMode.LIGHT else "Light Mode"
        
        if location == "sidebar":
            with st.sidebar:
                if st.button(f"{icon} {label}", key="theme_toggle_sidebar", use_container_width=True):
                    self.toggle_theme()
                    st.rerun()
        else:
            if st.button(f"{icon} {label}", key="theme_toggle_main"):
                self.toggle_theme()
                st.rerun()
    
    def get_plotly_template(self) -> str:
        """Get Plotly template name for current theme."""
        mode = self.get_current_theme()
        return "plotly_dark" if mode == ThemeMode.DARK else "plotly_white"
    
    def get_plotly_layout(self) -> Dict[str, Any]:
        """Get Plotly layout configuration for current theme."""
        colors = self.get_theme_colors()
        mode = self.get_current_theme()
        
        return {
            'template': self.get_plotly_template(),
            'paper_bgcolor': colors.background,
            'plot_bgcolor': colors.surface,
            'font': {
                'color': colors.text_primary
            },
            'colorway': colors.chart_colors,
            'xaxis': {
                'gridcolor': colors.divider,
                'linecolor': colors.border,
            },
            'yaxis': {
                'gridcolor': colors.divider,
                'linecolor': colors.border,
            }
        }