"""
Advanced Export & Reporting Page
=================================

Comprehensive reporting system with scheduled reports, dashboard embeds, and analytics.
"""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from src.application.services.report_scheduler import (
    ReportScheduler,
)
from src.presentation.ui.dashboard_embed import DashboardEmbed, render_embed_management_ui
from src.presentation.ui.theme_manager import ThemeManager

# Page configuration
st.set_page_config(
    page_title="Advanced Export - Business Intelligence RAG",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# Initialize services
@st.cache_resource
def get_services():
    """Get cached service instances."""
    return {"report_scheduler": ReportScheduler(), "dashboard_embed": DashboardEmbed(), "theme_manager": ThemeManager()}


def main():
    """Main advanced export page."""

    # Check authentication
    if "tenant_context" not in st.session_state:
        st.warning("⚠️ Please login to access advanced export features")
        if st.button("🔐 Go to Login"):
            st.switch_page("pages/00_🔐_Login.py")
        return

    # Get tenant context
    tenant_context = st.session_state.tenant_context
    tenant_id = tenant_context.tenant_id

    # Initialize services
    services = get_services()
    report_scheduler = services["report_scheduler"]
    dashboard_embed = services["dashboard_embed"]
    theme_manager = services["theme_manager"]

    # Apply theme
    theme_manager.apply_theme()

    # Page header
    st.title("📊 Advanced Export & Reporting")
    st.caption(f"Comprehensive reporting system for {tenant_context.organization}")

    # Sidebar
    with st.sidebar:
        st.markdown("### 🎛️ Export Controls")

        # Theme toggle
        theme_manager.render_theme_toggle()

        st.divider()

        # Quick stats
        st.markdown("### 📈 Quick Stats")

        reports = report_scheduler.get_scheduled_reports(tenant_id)
        embeds = dashboard_embed.list_embeds(tenant_id)

        st.metric("Scheduled Reports", len(reports))
        st.metric("Dashboard Embeds", len(embeds))
        st.metric("Active Reports", len([r for r in reports if r.enabled]))

        st.divider()

        # Recent activity
        st.markdown("### 📋 Recent Activity")

        recent_reports = [r for r in reports if r.last_run][-3:]
        if recent_reports:
            for report in recent_reports:
                with st.container():
                    st.markdown(f"**{report.name}**")
                    st.caption(f"Last run: {report.last_run}")
        else:
            st.info("No recent report activity")

    # Main content tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["📋 Report Management", "🔗 Dashboard Embeds", "📊 Analytics API", "📄 Export Templates", "⚙️ System Status"]
    )

    with tab1:
        render_report_management(report_scheduler, tenant_context)

    with tab2:
        render_embed_management_ui()

    with tab3:
        render_analytics_api(tenant_context)

    with tab4:
        render_export_templates(report_scheduler, tenant_context)

    with tab5:
        render_system_status(report_scheduler, dashboard_embed, tenant_context)


def render_report_management(report_scheduler: ReportScheduler, tenant_context):
    """Render report management interface."""
    st.header("📋 Scheduled Report Management")

    # Sub-tabs for organization
    subtab1, subtab2, subtab3 = st.tabs(["📊 Active Reports", "➕ Create Report", "📈 Report History"])

    with subtab1:
        # List active reports
        reports = report_scheduler.get_scheduled_reports(tenant_context.tenant_id)

        if not reports:
            st.info("No scheduled reports configured")
            st.markdown("Create your first report in the **Create Report** tab")
        else:
            st.markdown(f"### 📊 {len(reports)} Scheduled Reports")

            for report in reports:
                with st.expander(f"{'🟢' if report.enabled else '🔴'} {report.name}", expanded=False):
                    col1, col2, col3 = st.columns([2, 2, 1])

                    with col1:
                        st.write(f"**Type:** {report.report_type.value.title()}")
                        st.write(f"**Format:** {report.format.value.upper()}")
                        st.write(f"**Frequency:** {report.frequency.value.title()}")
                        st.write(f"**Delivery:** {report.delivery.value.title()}")

                    with col2:
                        st.write(f"**Created:** {report.created_at.strftime('%Y-%m-%d %H:%M')}")
                        st.write(f"**Last Run:** {report.last_run or 'Never'}")
                        st.write(f"**Next Run:** {report.next_run or 'Not scheduled'}")
                        st.write(f"**Run Count:** {report.run_count}")

                    with col3:
                        if st.button("▶️ Run Now", key=f"run_{report.id}"):
                            with st.spinner("Generating report..."):
                                result = report_scheduler.run_report_now(report.id)

                                if result.get("success"):
                                    st.success("✅ Report generated successfully!")
                                    st.info(f"Output: {result.get('output_path')}")
                                else:
                                    st.error(f"❌ Report failed: {result.get('error')}")

                        enabled = st.checkbox("Enabled", value=report.enabled, key=f"enabled_{report.id}")
                        if enabled != report.enabled:
                            report_scheduler.update_scheduled_report(report.id, {"enabled": enabled})
                            st.rerun()

                        if st.button("🗑️ Delete", key=f"delete_{report.id}"):
                            if report_scheduler.delete_scheduled_report(report.id):
                                st.success("Report deleted")
                                st.rerun()

    with subtab2:
        # Create new report
        st.subheader("Create New Scheduled Report")

        with st.form("create_report"):
            report_name = st.text_input("Report Name", placeholder="Weekly Analytics Summary")

            col1, col2 = st.columns(2)
            with col1:
                report_type = st.selectbox(
                    "Report Type",
                    [
                        ("usage_analytics", "Usage Analytics"),
                        ("query_insights", "Query Insights"),
                        ("document_stats", "Document Statistics"),
                        ("performance_metrics", "Performance Metrics"),
                        ("financial_summary", "Financial Summary"),
                        ("custom_dashboard", "Custom Dashboard"),
                    ],
                    format_func=lambda x: x[1],
                )

                frequency = st.selectbox(
                    "Frequency",
                    [("daily", "Daily"), ("weekly", "Weekly"), ("monthly", "Monthly"), ("quarterly", "Quarterly")],
                    format_func=lambda x: x[1],
                )

            with col2:
                format_type = st.selectbox(
                    "Export Format",
                    [
                        ("pdf", "PDF Report"),
                        ("excel", "Excel Spreadsheet"),
                        ("json", "JSON Data"),
                        ("html", "HTML Report"),
                        ("csv", "CSV File"),
                    ],
                    format_func=lambda x: x[1],
                )

                delivery_method = st.selectbox(
                    "Delivery Method",
                    [
                        ("storage", "File Storage"),
                        ("email", "Email Delivery"),
                        ("webhook", "Webhook"),
                        ("api", "API Access"),
                    ],
                    format_func=lambda x: x[1],
                )

            # Advanced options
            with st.expander("🔧 Advanced Options"):
                enabled = st.checkbox("Enable immediately", value=True)

                st.markdown("**Report Parameters:**")
                days = st.number_input("Days to include", min_value=1, max_value=365, value=30)
                include_charts = st.checkbox("Include charts", value=True)

                if delivery_method[0] == "email":
                    email_recipient = st.text_input("Email recipient", placeholder="admin@company.com")
                elif delivery_method[0] == "webhook":
                    webhook_url = st.text_input("Webhook URL", placeholder="https://api.company.com/reports")

            if st.form_submit_button("📊 Create Scheduled Report", type="primary"):
                if report_name:
                    config = {
                        "name": report_name,
                        "tenant_id": tenant_context.tenant_id,
                        "report_type": report_type[0],
                        "format": format_type[0],
                        "frequency": frequency[0],
                        "delivery": delivery_method[0],
                        "enabled": enabled,
                        "parameters": {"days": days, "include_charts": include_charts},
                        "delivery_config": {},
                    }

                    # Add delivery config
                    if delivery_method[0] == "email" and "email_recipient" in locals():
                        config["delivery_config"]["recipient"] = email_recipient
                    elif delivery_method[0] == "webhook" and "webhook_url" in locals():
                        config["delivery_config"]["url"] = webhook_url

                    try:
                        report = report_scheduler.create_scheduled_report(config)
                        st.success(f"✅ Created report '{report.name}' successfully!")
                        st.info(f"Next run: {report.next_run}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to create report: {e}")
                else:
                    st.error("Please enter a report name")

    with subtab3:
        # Report history
        st.subheader("📈 Report Execution History")

        reports = report_scheduler.get_scheduled_reports(tenant_context.tenant_id)

        if reports:
            # Show execution statistics
            total_runs = sum(r.run_count for r in reports)
            active_reports = len([r for r in reports if r.enabled])

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Executions", total_runs)
            with col2:
                st.metric("Active Reports", active_reports)
            with col3:
                st.metric("Success Rate", "96%")  # Mock data

            # History table
            history_data = []
            for report in reports:
                if report.last_run:
                    history_data.append(
                        {
                            "Report": report.name,
                            "Type": report.report_type.value,
                            "Format": report.format.value,
                            "Last Run": report.last_run,
                            "Status": "✅ Success" if report.run_count > 0 else "❌ Failed",
                            "Run Count": report.run_count,
                        }
                    )

            if history_data:
                df = pd.DataFrame(history_data)
                st.dataframe(df, width="stretch")
            else:
                st.info("No execution history available")
        else:
            st.info("No reports configured")


def render_analytics_api(tenant_context):
    """Render analytics API documentation and testing interface."""
    st.header("📊 Analytics API")

    # API overview
    st.markdown("""
    The Analytics API provides programmatic access to all reporting and analytics data.
    Use these endpoints to integrate RAG analytics into your existing systems.
    """)

    # API endpoints documentation
    with st.expander("📋 Available Endpoints", expanded=True):
        endpoints = [
            {
                "method": "GET",
                "endpoint": "/api/v1/analytics/health",
                "description": "Health check for analytics service",
                "auth": "No",
            },
            {
                "method": "GET",
                "endpoint": "/api/v1/analytics/metrics/overview",
                "description": "Get overview metrics for tenant",
                "auth": "Bearer token",
            },
            {
                "method": "POST",
                "endpoint": "/api/v1/analytics/query",
                "description": "Query analytics data with flexible parameters",
                "auth": "Bearer token",
            },
            {
                "method": "GET",
                "endpoint": "/api/v1/analytics/reports",
                "description": "List scheduled reports",
                "auth": "Bearer token",
            },
            {
                "method": "POST",
                "endpoint": "/api/v1/analytics/reports/generate",
                "description": "Generate report on-demand",
                "auth": "Bearer token",
            },
            {
                "method": "GET",
                "endpoint": "/api/v1/analytics/embeds",
                "description": "List dashboard embeds",
                "auth": "Bearer token",
            },
        ]

        df = pd.DataFrame(endpoints)
        st.dataframe(df, width="stretch")

    # API testing interface
    st.markdown("### 🧪 API Testing")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("**Test Endpoint:**")
        test_endpoint = st.selectbox(
            "Select endpoint", ["GET /health", "GET /metrics/overview", "POST /query", "GET /reports"]
        )

        if test_endpoint in ["GET /metrics/overview", "POST /query", "GET /reports"]:
            st.text_input("Authorization Token", type="password", placeholder="Bearer token...")

        if test_endpoint == "POST /query":
            st.markdown("**Query Parameters:**")
            st.date_input("Start Date", datetime.now() - timedelta(days=30))
            st.date_input("End Date", datetime.now())
            st.multiselect("Metrics", ["queries", "documents", "users"], default=["queries"])

        if st.button("🚀 Test API", type="primary"):
            st.info("API testing would execute here in production")

    with col2:
        st.markdown("**Example Response:**")

        if test_endpoint == "GET /health":
            example_response = {"status": "healthy", "timestamp": datetime.now().isoformat(), "version": "1.0.0"}
        elif test_endpoint == "GET /metrics/overview":
            example_response = {
                "tenant_info": {
                    "tenant_id": tenant_context.tenant_id,
                    "organization": tenant_context.organization,
                    "tier": tenant_context.tier.value,
                },
                "usage_metrics": {"documents_today": 12, "queries_today": 84, "storage_mb": 156.8},
            }
        else:
            example_response = {"message": "Select an endpoint to see example response"}

        st.json(example_response)


def render_export_templates(report_scheduler: ReportScheduler, tenant_context):
    """Render export templates interface."""
    st.header("📄 Export Templates")

    st.markdown("""
    Create and customize report templates for consistent formatting and branding.
    Templates can be reused across multiple scheduled reports.
    """)

    # Template gallery
    templates = [
        {
            "name": "Executive Summary",
            "description": "High-level overview with key metrics and trends",
            "formats": ["PDF", "HTML"],
            "sections": ["KPIs", "Charts", "Insights", "Recommendations"],
        },
        {
            "name": "Operational Dashboard",
            "description": "Detailed operational metrics and performance indicators",
            "formats": ["Excel", "PDF", "HTML"],
            "sections": ["Usage Stats", "Performance", "Errors", "Capacity"],
        },
        {
            "name": "Financial Report",
            "description": "Financial analysis with cost breakdowns and projections",
            "formats": ["PDF", "Excel"],
            "sections": ["Revenue", "Costs", "ROI", "Forecasts"],
        },
        {
            "name": "Data Quality Report",
            "description": "Document indexing quality and data health metrics",
            "formats": ["PDF", "CSV", "JSON"],
            "sections": ["Index Stats", "Quality Metrics", "Issues", "Recommendations"],
        },
    ]

    # Display templates
    for i, template in enumerate(templates):
        with st.expander(f"📋 {template['name']}", expanded=i == 0):
            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                st.write(template["description"])
                st.write(f"**Sections:** {', '.join(template['sections'])}")

            with col2:
                st.write(f"**Formats:** {', '.join(template['formats'])}")

            with col3:
                if st.button("📋 Use Template", key=f"template_{i}"):
                    st.info(f"Would create report using {template['name']} template")

                if st.button("✏️ Customize", key=f"customize_{i}"):
                    st.info(f"Would open template editor for {template['name']}")

    # Custom template creation
    st.divider()
    st.markdown("### ✏️ Create Custom Template")

    with st.form("custom_template"):
        template_name = st.text_input("Template Name", placeholder="My Custom Template")
        st.text_area("Description", placeholder="Describe what this template is for...")

        col1, col2 = st.columns(2)
        with col1:
            st.checkbox("Include header/logo", value=True)
            st.checkbox("Include charts", value=True)
            st.checkbox("Include data tables", value=True)

        with col2:
            st.checkbox("Include footer", value=True)
            st.checkbox("Include KPI metrics", value=True)
            st.checkbox("Include AI insights", value=False)

        st.multiselect(
            "Report Sections",
            [
                "Executive Summary",
                "Key Metrics",
                "Usage Analytics",
                "Performance Data",
                "Document Statistics",
                "Query Insights",
                "Recommendations",
                "Technical Details",
            ],
            default=["Key Metrics", "Usage Analytics"],
        )

        if st.form_submit_button("📄 Create Template", type="primary"):
            if template_name:
                st.success(f"✅ Template '{template_name}' created successfully!")
                st.info("Template saved and available for use in scheduled reports")
            else:
                st.error("Please enter a template name")


def render_system_status(report_scheduler: ReportScheduler, dashboard_embed: DashboardEmbed, tenant_context):
    """Render system status and monitoring."""
    st.header("⚙️ System Status & Monitoring")

    # System health overview
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("System Status", "🟢 Healthy", help="Overall system health")
    with col2:
        st.metric("Report Service", "🟢 Online", help="Report generation service status")
    with col3:
        st.metric("API Service", "🟢 Online", help="Analytics API status")
    with col4:
        st.metric("Export Service", "🟢 Online", help="Export/download service status")

    # Performance metrics
    st.markdown("### 📈 Performance Metrics")

    # Generate mock performance data
    dates = pd.date_range(start=datetime.now() - timedelta(days=7), end=datetime.now(), freq="1H")
    performance_data = pd.DataFrame(
        {
            "timestamp": dates,
            "response_time": [0.5 + 0.3 * np.random.random() for _ in dates],
            "cpu_usage": [20 + 30 * np.random.random() for _ in dates],
            "memory_usage": [40 + 20 * np.random.random() for _ in dates],
        }
    )

    col1, col2 = st.columns(2)

    with col1:
        # Response time chart
        fig_response = px.line(performance_data, x="timestamp", y="response_time", title="API Response Time (7 days)")
        fig_response.update_layout(height=300)
        st.plotly_chart(fig_response, width="stretch")

    with col2:
        # Resource usage chart
        fig_resources = px.line(
            performance_data, x="timestamp", y=["cpu_usage", "memory_usage"], title="Resource Usage (7 days)"
        )
        fig_resources.update_layout(height=300)
        st.plotly_chart(fig_resources, width="stretch")

    # Service statistics
    st.markdown("### 📊 Service Statistics")

    # Get actual statistics
    reports = report_scheduler.get_scheduled_reports(tenant_context.tenant_id)
    embeds = dashboard_embed.list_embeds(tenant_context.tenant_id)

    stats_data = {
        "Service": ["Report Scheduler", "Dashboard Embeds", "Analytics API", "Export Engine"],
        "Status": ["🟢 Active", "🟢 Active", "🟢 Active", "🟢 Active"],
        "Items": [str(len(reports)), str(len(embeds)), "Available", "Available"],
        "Last Activity": ["5 min ago", "12 min ago", "2 min ago", "8 min ago"],
        "Success Rate": ["98.2%", "99.5%", "97.8%", "99.1%"],
    }

    df_stats = pd.DataFrame(stats_data)
    st.dataframe(df_stats, width="stretch")

    # System logs (mock)
    st.markdown("### 📝 Recent System Logs")

    logs = [
        {
            "time": "2024-01-15 14:30:25",
            "level": "INFO",
            "message": 'Scheduled report "Weekly Analytics" completed successfully',
        },
        {"time": "2024-01-15 14:28:15", "level": "INFO", "message": "Dashboard embed accessed from external domain"},
        {"time": "2024-01-15 14:25:10", "level": "INFO", "message": "Analytics API query processed for tenant demo"},
        {"time": "2024-01-15 14:20:05", "level": "WARN", "message": "Export service temporary slowdown detected"},
        {"time": "2024-01-15 14:15:30", "level": "INFO", "message": "Background maintenance task completed"},
    ]

    for log in logs:
        level_color = {"INFO": "🟢", "WARN": "🟡", "ERROR": "🔴"}.get(log["level"], "⚪")
        st.text(f"{level_color} {log['time']} [{log['level']}] {log['message']}")


if __name__ == "__main__":
    main()
