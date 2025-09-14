"""Security Dashboard page for Row-level Security management."""

import streamlit as st
from components.security_ui import security_ui, require_authentication

# Page configuration
st.set_page_config(
    page_title="Security Dashboard - RAG System", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded"
)


def main():
    """Main security dashboard function."""

    # Require authentication
    if not require_authentication():
        st.error("🔐 Please login to access the Security Dashboard")
        if st.button("Go to Main App"):
            st.switch_page("app.py")
        return

    # Render security dashboard
    security_ui.render_security_dashboard()


if __name__ == "__main__":
    main()
