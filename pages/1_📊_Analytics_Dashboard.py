"""Advanced Analytics Dashboard with KPIs, trends, and interactive visualizations."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from datetime import datetime, timedelta
import numpy as np

# Import our services
try:
    from src.application.services.analytics_dashboard import AnalyticsDashboardService
    from src.application.services.ontology_mapper import OntologyMapper
    SERVICES_AVAILABLE = True
except ImportError:
    SERVICES_AVAILABLE = False
    st.error("Advanced services not available. Please install required dependencies.")

def main():
    st.set_page_config(page_title="Analytics Dashboard", page_icon="📊", layout="wide")
    
    st.title("📊 Advanced Analytics Dashboard")
    st.markdown("---")
    
    if not SERVICES_AVAILABLE:
        st.stop()
    
    # Initialize services
    if 'analytics_service' not in st.session_state:
        st.session_state.analytics_service = AnalyticsDashboardService()
    
    analytics_service = st.session_state.analytics_service
    
    # Sample financial data (in real app, this would come from data extraction)
    sample_data = {
        'ricavi': 12000000,
        'cogs': 7200000,
        'ebitda': 1800000,
        'ebit': 1200000,
        'utile_netto': 840000,
        'attivo_totale': 18000000,
        'passivo_totale': 18000000,
        'patrimonio_netto': 6000000,
        'debito_lordo': 8000000,
        'cassa': 2000000,
        'crediti_commerciali': 2400000,
        'rimanenze': 1800000,
        'dipendenti': 150,
        'dso': 73,
        'rotazione_magazzino': 4.0,
        'leverage': 1.33
    }
    
    # Historical data for trends
    sample_periods = [
        {'period': 'FY2022', 'ricavi': 10000000, 'ebitda': 1300000, 'utile_netto': 650000},
        {'period': 'FY2023', 'ricavi': 11200000, 'ebitda': 1560000, 'utile_netto': 728000},
        {'period': 'FY2024', 'ricavi': 12000000, 'ebitda': 1800000, 'utile_netto': 840000}
    ]
    
    # Sidebar controls
    st.sidebar.header("Dashboard Controls")
    
    industry = st.sidebar.selectbox(
        "Industry Benchmark",
        ["manufacturing", "services", "retail"],
        index=0
    )
    
    auto_refresh = st.sidebar.checkbox("Auto-refresh data", value=False)
    
    if auto_refresh:
        # Add some randomization to simulate real data changes
        for key in ['ricavi', 'ebitda', 'utile_netto']:
            if key in sample_data:
                sample_data[key] *= (1 + np.random.uniform(-0.05, 0.05))
    
    # Generate dashboard data
    with st.spinner("Generating analytics..."):
        dashboard_data = analytics_service.generate_dashboard_data(
            sample_data, 
            sample_periods, 
            industry
        )
    
    # Main dashboard layout
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Health Score - prominently displayed
        health_data = dashboard_data['health_score']
        
        # Create health score gauge
        fig_health = go.Figure(go.Indicator(
            mode = "gauge+number+delta",
            value = health_data['score'],
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': f"Financial Health Score<br><span style='font-size:0.8em;color:gray'>{health_data['level']}</span>"},
            delta = {'reference': 75, 'increasing': {'color': "green"}, 'decreasing': {'color': "red"}},
            gauge = {
                'axis': {'range': [None, 100]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 50], 'color': "lightgray"},
                    {'range': [50, 80], 'color': "yellow"},
                    {'range': [80, 100], 'color': "lightgreen"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 90
                }
            }
        ))
        
        fig_health.update_layout(height=300)
        st.plotly_chart(fig_health, width='stretch')
        
        st.markdown(f"**{health_data['description']}**")
    
    # Performance Summary Cards
    st.subheader("📈 Performance Summary")
    
    perf_summary = dashboard_data['performance_summary']
    key_metrics = perf_summary.get('key_metrics', {})
    trends = perf_summary.get('trends', {})
    
    cols = st.columns(4)
    
    metric_configs = [
        ('ricavi', 'Revenue', '💰'),
        ('ebitda', 'EBITDA', '📊'),
        ('utile_netto', 'Net Income', '💎'),
        ('dipendenti', 'Employees', '👥')
    ]
    
    for i, (metric, label, icon) in enumerate(metric_configs):
        with cols[i]:
            if metric in key_metrics:
                value = key_metrics[metric]['formatted']
                trend_data = trends.get(metric, {})
                
                delta_value = trend_data.get('formatted', '')
                delta_color = 'normal' if trend_data.get('direction') == 'up' else 'inverse'
                
                st.metric(
                    label=f"{icon} {label}",
                    value=value,
                    delta=delta_value,
                    delta_color=delta_color
                )
    
    # KPIs Section
    st.subheader("🎯 Key Performance Indicators")
    
    kpis = dashboard_data['kpis']
    
    # KPI Grid
    kpi_cols = st.columns(4)
    
    for i, kpi in enumerate(kpis[:8]):  # Show first 8 KPIs
        col_idx = i % 4
        
        with kpi_cols[col_idx]:
            if kpi['actual_value'] is not None:
                # Color based on status
                status_colors = {
                    'green': '#28a745',
                    'yellow': '#ffc107', 
                    'red': '#dc3545',
                    'gray': '#6c757d'
                }
                
                status_color = status_colors.get(kpi.get('status', 'gray'), '#6c757d')
                
                # KPI Card
                st.markdown(f"""
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 10px; 
                           border-left: 4px solid {status_color}; margin-bottom: 10px;">
                    <h5 style="margin: 0; color: #333;">{kpi['name']}</h5>
                    <h3 style="margin: 5px 0; color: {status_color};">
                        {kpi['actual_value']:.1f}{' %' if kpi['unit'] == 'percentage' else ''}
                    </h3>
                    <small style="color: #666;">
                        Target: {kpi.get('target_value', 'N/A')}
                        {' %' if kpi['unit'] == 'percentage' else ''}
                    </small>
                </div>
                """, unsafe_allow_html=True)
    
    # Charts Section
    st.subheader("📊 Visual Analytics")
    
    chart_tabs = st.tabs(["KPI Overview", "Profitability", "Trends", "Efficiency"])
    
    with chart_tabs[0]:
        # KPI Overview with gauges
        st.markdown("#### KPI Dashboard")
        
        # Create subplot with gauges for main KPIs
        main_kpis = [kpi for kpi in kpis if kpi['name'] in ['Margine EBITDA %', 'ROS %', 'DSO', 'ROE %']]
        
        if len(main_kpis) >= 4:
            gauge_cols = st.columns(2)
            
            with gauge_cols[0]:
                # EBITDA Margin
                ebitda_kpi = next((k for k in main_kpis if k['name'] == 'Margine EBITDA %'), None)
                if ebitda_kpi and ebitda_kpi['actual_value']:
                    fig_ebitda = go.Figure(go.Indicator(
                        mode = "gauge+number",
                        value = ebitda_kpi['actual_value'],
                        title = {'text': "EBITDA Margin %"},
                        gauge = {'axis': {'range': [None, 30]},
                                'bar': {'color': "darkblue"},
                                'steps': [{'range': [0, 10], 'color': "lightgray"},
                                         {'range': [10, 20], 'color': "yellow"}],
                                'threshold': {'line': {'color': "red", 'width': 4},
                                            'thickness': 0.75, 'value': ebitda_kpi.get('target_value', 15)}}
                    ))
                    fig_ebitda.update_layout(height=250)
                    st.plotly_chart(fig_ebitda, width='stretch')
            
            with gauge_cols[1]:
                # DSO
                dso_kpi = next((k for k in main_kpis if k['name'] == 'DSO'), None)
                if dso_kpi and dso_kpi['actual_value']:
                    fig_dso = go.Figure(go.Indicator(
                        mode = "gauge+number",
                        value = dso_kpi['actual_value'],
                        title = {'text': "Days Sales Outstanding"},
                        gauge = {'axis': {'range': [0, 120]},
                                'bar': {'color': "darkgreen"},
                                'steps': [{'range': [60, 90], 'color': "yellow"},
                                         {'range': [90, 120], 'color': "lightcoral"}],
                                'threshold': {'line': {'color': "red", 'width': 4},
                                            'thickness': 0.75, 'value': dso_kpi.get('target_value', 45)}}
                    ))
                    fig_dso.update_layout(height=250)
                    st.plotly_chart(fig_dso, width='stretch')
    
    with chart_tabs[1]:
        # Profitability Waterfall
        st.markdown("#### Profitability Breakdown")
        
        # Create waterfall chart
        ricavi = sample_data.get('ricavi', 0)
        cogs = sample_data.get('cogs', 0)
        ebitda = sample_data.get('ebitda', 0)
        ebit = sample_data.get('ebit', 0)
        utile_netto = sample_data.get('utile_netto', 0)
        
        fig_waterfall = go.Figure(go.Waterfall(
            name = "Profitability",
            orientation = "v",
            measure = ["absolute", "relative", "relative", "relative", "total"],
            x = ["Revenue", "COGS", "Other Op. Costs", "Interests/Taxes", "Net Income"],
            text = [f"€{ricavi/1e6:.1f}M", f"-€{cogs/1e6:.1f}M", 
                   f"-€{(ebitda-ebit)/1e6:.1f}M", f"-€{(ebit-utile_netto)/1e6:.1f}M", 
                   f"€{utile_netto/1e6:.1f}M"],
            y = [ricavi/1e6, -cogs/1e6, -(ebitda-ebit)/1e6, -(ebit-utile_netto)/1e6, utile_netto/1e6],
            connector = {"line":{"color":"rgb(63, 63, 63)"}},
        ))
        
        fig_waterfall.update_layout(
            title = "Profitability Waterfall (€ Millions)",
            height=400
        )
        
        st.plotly_chart(fig_waterfall, width='stretch')
        
        # Profitability ratios
        col1, col2, col3 = st.columns(3)
        
        with col1:
            gross_margin = ((ricavi - cogs) / ricavi * 100) if ricavi > 0 else 0
            st.metric("Gross Margin %", f"{gross_margin:.1f}%")
        
        with col2:
            ebitda_margin = (ebitda / ricavi * 100) if ricavi > 0 else 0
            st.metric("EBITDA Margin %", f"{ebitda_margin:.1f}%")
        
        with col3:
            net_margin = (utile_netto / ricavi * 100) if ricavi > 0 else 0
            st.metric("Net Margin %", f"{net_margin:.1f}%")
    
    with chart_tabs[2]:
        # Trend Analysis
        st.markdown("#### Trend Analysis")
        
        if sample_periods:
            # Revenue and Profitability Trends
            periods_df = pd.DataFrame(sample_periods)
            
            fig_trends = go.Figure()
            
            fig_trends.add_trace(go.Scatter(
                x=periods_df['period'],
                y=periods_df['ricavi'] / 1e6,
                mode='lines+markers',
                name='Revenue (€M)',
                line=dict(color='blue', width=3)
            ))
            
            fig_trends.add_trace(go.Scatter(
                x=periods_df['period'],
                y=periods_df['ebitda'] / 1e6,
                mode='lines+markers', 
                name='EBITDA (€M)',
                line=dict(color='green', width=3)
            ))
            
            fig_trends.add_trace(go.Scatter(
                x=periods_df['period'],
                y=periods_df['utile_netto'] / 1e6,
                mode='lines+markers',
                name='Net Income (€M)',
                line=dict(color='red', width=3)
            ))
            
            fig_trends.update_layout(
                title="Financial Trends (€ Millions)",
                xaxis_title="Period",
                yaxis_title="Amount (€M)",
                height=400
            )
            
            st.plotly_chart(fig_trends, width='stretch')
            
            # Growth rates
            if len(sample_periods) >= 2:
                latest = sample_periods[-1]
                previous = sample_periods[-2]
                
                growth_cols = st.columns(3)
                
                metrics_growth = [
                    ('ricavi', 'Revenue Growth', '💰'),
                    ('ebitda', 'EBITDA Growth', '📊'),
                    ('utile_netto', 'Net Income Growth', '💎')
                ]
                
                for i, (metric, label, icon) in enumerate(metrics_growth):
                    if metric in latest and metric in previous and previous[metric] > 0:
                        growth = (latest[metric] - previous[metric]) / previous[metric] * 100
                        
                        with growth_cols[i]:
                            st.metric(
                                label=f"{icon} {label}",
                                value=f"{growth:+.1f}%",
                                delta=None,
                                delta_color="normal" if growth > 0 else "inverse"
                            )
    
    with chart_tabs[3]:
        # Efficiency Analysis
        st.markdown("#### Operational Efficiency")
        
        # Efficiency metrics radar chart
        efficiency_metrics = {
            'DSO (Inverted)': max(0, 100 - (sample_data.get('dso', 45) - 30) * 1.5),
            'Inventory Turnover': min(100, sample_data.get('rotazione_magazzino', 6) / 10 * 100),
            'Asset Efficiency': min(100, (ricavi / sample_data.get('attivo_totale', 18000000)) * 100 * 5),
            'Revenue per Employee': min(100, (ricavi / sample_data.get('dipendenti', 150)) / 100000 * 100)
        }
        
        fig_radar = go.Figure(data=go.Scatterpolar(
            r=list(efficiency_metrics.values()),
            theta=list(efficiency_metrics.keys()),
            fill='toself',
            name='Current Performance',
            line_color='blue'
        ))
        
        # Add industry benchmark (sample)
        benchmark_values = [75, 70, 65, 80]  # Sample benchmark values
        fig_radar.add_trace(go.Scatterpolar(
            r=benchmark_values,
            theta=list(efficiency_metrics.keys()),
            fill='toself',
            name='Industry Benchmark',
            line_color='red',
            opacity=0.6
        ))
        
        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100]
                )
            ),
            showlegend=True,
            title="Efficiency Radar Chart (0-100 scale)",
            height=500
        )
        
        st.plotly_chart(fig_radar, width='stretch')
    
    # Insights Section
    st.subheader("🔍 Key Insights")
    
    insights = dashboard_data.get('insights', [])
    
    if insights:
        # Group insights by severity
        high_insights = [i for i in insights if i['severity'] == 'high']
        medium_insights = [i for i in insights if i['severity'] == 'medium']
        
        if high_insights:
            st.markdown("#### 🚨 High Priority Insights")
            for insight in high_insights:
                st.error(f"**{insight['title']}**: {insight['description']}")
                if insight.get('recommendation'):
                    st.markdown(f"💡 *Recommendation: {insight['recommendation']}*")
        
        if medium_insights:
            st.markdown("#### ⚠️ Medium Priority Insights")
            for insight in medium_insights:
                st.warning(f"**{insight['title']}**: {insight['description']}")
                if insight.get('recommendation'):
                    st.markdown(f"💡 *Recommendation: {insight['recommendation']}*")
    else:
        st.info("No significant insights detected. All metrics appear to be within normal ranges.")
    
    # Risk Assessment
    st.subheader("⚠️ Risk Assessment")
    
    risk_data = dashboard_data.get('risk_assessment', {})
    risks = risk_data.get('risks', {})
    
    risk_cols = st.columns(4)
    risk_labels = {
        'liquidity_risk': 'Liquidity Risk',
        'leverage_risk': 'Leverage Risk', 
        'profitability_risk': 'Profitability Risk',
        'operational_risk': 'Operational Risk'
    }
    
    risk_colors = {'low': 'green', 'medium': 'orange', 'high': 'red'}
    
    for i, (risk_key, risk_label) in enumerate(risk_labels.items()):
        risk_level = risks.get(risk_key, 'low')
        color = risk_colors.get(risk_level, 'gray')
        
        with risk_cols[i]:
            st.markdown(f"""
            <div style="text-align: center; padding: 10px; border-radius: 5px; 
                       background-color: {color}; color: white; margin: 5px 0;">
                <strong>{risk_label}</strong><br>
                {risk_level.upper()}
            </div>
            """, unsafe_allow_html=True)
    
    # Risk factors
    risk_factors = risk_data.get('risk_factors', [])
    if risk_factors:
        st.markdown("#### Risk Factors Identified:")
        for factor in risk_factors:
            st.markdown(f"• {factor}")
    
    # Data Quality Assessment
    st.subheader("📋 Data Quality")
    
    data_quality = dashboard_data.get('data_quality', {})
    
    quality_cols = st.columns(3)
    
    with quality_cols[0]:
        completeness = data_quality.get('completeness_pct', 0)
        st.metric("Data Completeness", f"{completeness:.1f}%")
    
    with quality_cols[1]:
        quality_level = data_quality.get('quality_level', 'unknown').title()
        st.metric("Quality Level", quality_level)
    
    with quality_cols[2]:
        available = data_quality.get('available_metrics', 0)
        total = data_quality.get('total_expected', 0)
        st.metric("Available Metrics", f"{available}/{total}")
    
    # Quality issues
    quality_issues = data_quality.get('issues', [])
    if quality_issues:
        st.markdown("#### Data Quality Issues:")
        for issue in quality_issues:
            st.warning(f"• {issue}")
    
    # Recommendations
    st.subheader("💡 Recommendations")
    
    recommendations = dashboard_data.get('recommendations', [])
    
    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            priority_color = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(rec.get('priority', 'medium'), '🟡')
            
            st.markdown(f"""
            {priority_color} **{i}. {rec['title']}**  
            {rec['description']}  
            *Confidence: {rec.get('confidence', 0.5)*100:.0f}%*
            """)
    
    # Footer with refresh info
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.caption(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    with col2:
        if st.button("🔄 Refresh Dashboard"):
            st.rerun()
    
    with col3:
        st.caption(f"Industry: {industry.title()}")

if __name__ == "__main__":
    main()