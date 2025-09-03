"""Main Streamlit application for Business Intelligence RAG System."""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import json
from datetime import datetime
import tempfile
import os

from services.csv_analyzer import CSVAnalyzer
from services.rag_engine import RAGEngine
from services.llm_service import LLMService
from config.settings import settings

# Page configuration
st.set_page_config(
    page_title="Business Intelligence RAG System",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize services
@st.cache_resource
def init_services():
    """Initialize and cache services."""
    return {
        'csv_analyzer': CSVAnalyzer(),
        'rag_engine': RAGEngine(),
        'llm_service': LLMService()
    }

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
        border-bottom: 2px solid #1f77b4;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .insight-box {
        background-color: #e8f4f8;
        padding: 1rem;
        border-left: 4px solid #1f77b4;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

def main():
    """Main application function."""
    
    # Header
    st.markdown('<h1 class="main-header">📊 Business Intelligence RAG System</h1>', unsafe_allow_html=True)
    
    # Initialize session state
    if 'services' not in st.session_state:
        with st.spinner("Initializing services..."):
            st.session_state.services = init_services()
    
    if 'csv_analysis' not in st.session_state:
        st.session_state.csv_analysis = None
    
    if 'rag_response' not in st.session_state:
        st.session_state.rag_response = None
    
    # Sidebar
    with st.sidebar:
        st.header("🔧 Configuration")
        
        # Navigation
        page = st.selectbox(
            "Select Module",
            ["📈 Data Analysis", "📚 Document RAG", "🤖 AI Insights", "📊 Dashboard", "⚙️ Settings"]
        )
        
        st.divider()
        
        # Quick Stats
        if st.session_state.services['rag_engine']:
            stats = st.session_state.services['rag_engine'].get_index_stats()
            st.metric("Indexed Vectors", stats.get('total_vectors', 0))
        
        if st.session_state.csv_analysis:
            st.metric("Data Loaded", "✅ Active")
    
    # Main content based on selected page
    if page == "📈 Data Analysis":
        show_data_analysis()
    elif page == "📚 Document RAG":
        show_document_rag()
    elif page == "🤖 AI Insights":
        show_ai_insights()
    elif page == "📊 Dashboard":
        show_dashboard()
    elif page == "⚙️ Settings":
        show_settings()

def show_data_analysis():
    """Show data analysis page."""
    st.header("📈 Financial Data Analysis")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Upload CSV Data")
        uploaded_file = st.file_uploader(
            "Choose a CSV file with financial data",
            type=['csv'],
            help="Upload balance sheets, revenue reports, or any structured business data"
        )
        
        if uploaded_file:
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name
            
            try:
                # Load and analyze CSV
                analyzer = st.session_state.services['csv_analyzer']
                df = analyzer.load_csv(tmp_path)
                
                st.success(f"✅ Loaded {len(df)} records with {len(df.columns)} columns")
                
                # Display data preview
                st.subheader("Data Preview")
                st.dataframe(df.head(10), use_container_width=True)
                
                # Column selection for analysis
                with col2:
                    st.subheader("Analysis Configuration")
                    
                    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
                    
                    year_col = st.selectbox(
                        "Year/Period Column",
                        options=[col for col in df.columns if 'year' in col.lower() or 'anno' in col.lower() or 'period' in col.lower()] + ['None'],
                        index=0
                    )
                    
                    revenue_col = st.selectbox(
                        "Revenue Column",
                        options=[col for col in numeric_cols if 'revenue' in col.lower() or 'fatturato' in col.lower() or 'sales' in col.lower()] + numeric_cols,
                        index=0 if any('revenue' in col.lower() or 'fatturato' in col.lower() for col in numeric_cols) else len(numeric_cols)-1
                    )
                    
                    if st.button("🔍 Analyze Data", type="primary"):
                        with st.spinner("Analyzing financial data..."):
                            # Perform analysis
                            if year_col != 'None':
                                analysis = analyzer.analyze_balance_sheet(
                                    df,
                                    year_column=year_col,
                                    revenue_column=revenue_col
                                )
                            else:
                                analysis = {
                                    'summary': analyzer.calculate_kpis(df),
                                    'insights': []
                                }
                            
                            st.session_state.csv_analysis = analysis
                
                # Display analysis results
                if st.session_state.csv_analysis:
                    st.divider()
                    display_analysis_results(st.session_state.csv_analysis, df)
                
                # Cleanup
                os.unlink(tmp_path)
                
            except Exception as e:
                st.error(f"Error analyzing data: {str(e)}")

def display_analysis_results(analysis, df):
    """Display analysis results with visualizations."""
    st.subheader("📊 Analysis Results")
    
    # Tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["Summary", "Trends", "Visualizations", "Recommendations"])
    
    with tab1:
        # Summary metrics
        if 'summary' in analysis:
            st.subheader("Key Metrics")
            cols = st.columns(3)
            for i, (key, value) in enumerate(analysis['summary'].items()):
                with cols[i % 3]:
                    st.metric(key.replace('_', ' ').title(), f"{value:,.2f}")
        
        # Insights
        if 'insights' in analysis and analysis['insights']:
            st.subheader("💡 Key Insights")
            for insight in analysis['insights']:
                st.markdown(f'<div class="insight-box">{insight}</div>', unsafe_allow_html=True)
    
    with tab2:
        # Trends
        if 'trends' in analysis and 'yoy_growth' in analysis['trends']:
            st.subheader("Growth Trends")
            
            growth_data = analysis['trends']['yoy_growth']
            if growth_data:
                # Create trend chart
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=[str(g['year']) for g in growth_data],
                    y=[g['growth_percentage'] for g in growth_data],
                    text=[f"{g['growth_percentage']:.1f}%" for g in growth_data],
                    textposition='auto',
                    marker_color=['green' if g['growth_percentage'] > 0 else 'red' for g in growth_data]
                ))
                fig.update_layout(
                    title="Year-over-Year Growth (%)",
                    xaxis_title="Year",
                    yaxis_title="Growth %",
                    showlegend=False
                )
                st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        # Visualizations
        st.subheader("Data Visualizations")
        
        # Allow user to create custom charts
        col1, col2 = st.columns(2)
        with col1:
            chart_type = st.selectbox("Chart Type", ["Line", "Bar", "Scatter", "Pie"])
        with col2:
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            if numeric_cols:
                y_axis = st.selectbox("Select Metric", numeric_cols)
                
                if chart_type == "Line":
                    fig = px.line(df, y=y_axis, title=f"{y_axis} Trend")
                elif chart_type == "Bar":
                    fig = px.bar(df, y=y_axis, title=f"{y_axis} Distribution")
                elif chart_type == "Scatter":
                    if len(numeric_cols) > 1:
                        x_axis = st.selectbox("X-Axis", [c for c in numeric_cols if c != y_axis])
                        fig = px.scatter(df, x=x_axis, y=y_axis, title=f"{y_axis} vs {x_axis}")
                    else:
                        fig = px.scatter(df, y=y_axis, title=f"{y_axis} Distribution")
                else:  # Pie
                    fig = px.pie(df, values=y_axis, title=f"{y_axis} Breakdown")
                
                st.plotly_chart(fig, use_container_width=True)
    
    with tab4:
        # Recommendations
        st.subheader("📋 Strategic Recommendations")
        
        if st.button("Generate AI Recommendations"):
            with st.spinner("Generating recommendations..."):
                llm_service = st.session_state.services['llm_service']
                insights = llm_service.generate_business_insights(analysis)
                st.markdown(insights)

def show_document_rag():
    """Show document RAG page."""
    st.header("📚 Document Analysis (RAG)")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📄 Upload Documents")
        uploaded_files = st.file_uploader(
            "Choose documents for analysis",
            type=['pdf', 'txt', 'docx', 'md'],
            accept_multiple_files=True,
            help="Upload business reports, contracts, or any relevant documents"
        )
        
        if uploaded_files:
            if st.button("🔄 Index Documents", type="primary"):
                with st.spinner("Indexing documents..."):
                    file_paths = []
                    
                    # Save uploaded files temporarily
                    for uploaded_file in uploaded_files:
                        suffix = Path(uploaded_file.name).suffix
                        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                            tmp_file.write(uploaded_file.getbuffer())
                            file_paths.append(tmp_file.name)
                    
                    # Index documents
                    rag_engine = st.session_state.services['rag_engine']
                    results = rag_engine.index_documents(file_paths)
                    
                    # Display results
                    if results['indexed_files']:
                        st.success(f"✅ Successfully indexed {len(results['indexed_files'])} documents with {results['total_chunks']} chunks")
                    if results['failed_files']:
                        st.error(f"❌ Failed to index {len(results['failed_files'])} files")
                        for error in results['errors']:
                            st.error(error)
                    
                    # Cleanup
                    for path in file_paths:
                        os.unlink(path)
    
    with col2:
        st.subheader("🔍 Query Documents")
        
        # Query interface
        query = st.text_area(
            "Ask questions about your documents",
            placeholder="e.g., What are the main business risks mentioned? What was the strategic focus for 2024?",
            height=100
        )
        
        col1_query, col2_query = st.columns([1, 1])
        with col1_query:
            top_k = st.slider("Number of sources", min_value=1, max_value=10, value=5)
        with col2_query:
            use_context = st.checkbox("Include CSV analysis context", value=bool(st.session_state.csv_analysis))
        
        if st.button("🤔 Ask Question", type="primary", disabled=not query):
            with st.spinner("Searching and analyzing documents..."):
                rag_engine = st.session_state.services['rag_engine']
                
                if use_context and st.session_state.csv_analysis:
                    response = rag_engine.query_with_context(
                        query,
                        st.session_state.csv_analysis,
                        top_k=top_k
                    )
                else:
                    response = rag_engine.query(query, top_k=top_k)
                
                st.session_state.rag_response = response
    
    # Display RAG response
    if st.session_state.rag_response:
        st.divider()
        st.subheader("📝 Answer")
        st.markdown(st.session_state.rag_response['answer'])
        
        if st.session_state.rag_response['sources']:
            st.subheader("📚 Sources")
            for i, source in enumerate(st.session_state.rag_response['sources'], 1):
                with st.expander(f"Source {i} (Score: {source['score']:.3f})"):
                    st.text(source['text'])
                    if source['metadata']:
                        st.json(source['metadata'])

def show_ai_insights():
    """Show AI insights page."""
    st.header("🤖 AI-Powered Insights")
    
    if not st.session_state.csv_analysis:
        st.warning("⚠️ Please analyze CSV data first in the Data Analysis section")
        return
    
    # Tabs for different AI features
    tab1, tab2, tab3, tab4 = st.tabs(["Business Insights", "Executive Report", "Q&A", "Action Items"])
    
    with tab1:
        st.subheader("💡 Comprehensive Business Insights")
        
        if st.button("Generate Insights", type="primary"):
            with st.spinner("Generating comprehensive insights..."):
                llm_service = st.session_state.services['llm_service']
                
                # Get RAG context if available
                rag_context = None
                if st.session_state.rag_response:
                    rag_context = st.session_state.rag_response.get('answer', '')
                
                insights = llm_service.generate_business_insights(
                    st.session_state.csv_analysis,
                    rag_context
                )
                
                st.markdown(insights)
    
    with tab2:
        st.subheader("📋 Executive Report")
        
        # Custom sections input
        custom_sections = st.multiselect(
            "Select report sections",
            ["Executive Summary", "Financial Performance", "Operational Highlights",
             "Market Position", "Risk Assessment", "Recommendations", "Next Steps"],
            default=["Executive Summary", "Financial Performance", "Recommendations"]
        )
        
        if st.button("Generate Executive Report", type="primary"):
            with st.spinner("Preparing executive report..."):
                llm_service = st.session_state.services['llm_service']
                
                report = llm_service.generate_executive_report(
                    st.session_state.csv_analysis,
                    rag_insights=st.session_state.rag_response.get('answer') if st.session_state.rag_response else None,
                    custom_sections=custom_sections
                )
                
                st.markdown(report)
                
                # Download button
                st.download_button(
                    label="📥 Download Report",
                    data=report,
                    file_name=f"executive_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown"
                )
    
    with tab3:
        st.subheader("❓ Business Q&A")
        
        question = st.text_area(
            "Ask specific business questions",
            placeholder="e.g., What factors contributed to the revenue change? What are the main cost drivers?",
            height=100
        )
        
        if st.button("Get Answer", type="primary", disabled=not question):
            with st.spinner("Processing question..."):
                llm_service = st.session_state.services['llm_service']
                
                # Combine all context
                context = {
                    'csv_analysis': st.session_state.csv_analysis,
                    'rag_context': st.session_state.rag_response if st.session_state.rag_response else None
                }
                
                answer = llm_service.answer_business_question(question, context)
                
                st.markdown(answer)
    
    with tab4:
        st.subheader("✅ Action Items Generator")
        
        priority_count = st.slider("Number of action items", min_value=5, max_value=20, value=10)
        
        if st.button("Generate Action Items", type="primary"):
            with st.spinner("Creating prioritized action items..."):
                llm_service = st.session_state.services['llm_service']
                
                action_items = llm_service.generate_action_items(
                    st.session_state.csv_analysis,
                    priority_count=priority_count
                )
                
                if action_items:
                    # Display as table
                    df_actions = pd.DataFrame(action_items)
                    
                    # Color code by priority
                    def highlight_priority(row):
                        colors = {
                            'high': 'background-color: #ffcccc',
                            'medium': 'background-color: #ffffcc',
                            'low': 'background-color: #ccffcc'
                        }
                        return [colors.get(row['priority'], '')] * len(row)
                    
                    styled_df = df_actions.style.apply(highlight_priority, axis=1)
                    st.dataframe(styled_df, use_container_width=True)
                    
                    # Download as CSV
                    csv = df_actions.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Action Items",
                        data=csv,
                        file_name=f"action_items_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.error("Failed to generate action items")

def show_dashboard():
    """Show dashboard page."""
    st.header("📊 Executive Dashboard")
    
    if not st.session_state.csv_analysis:
        st.info("📈 Load data in the Data Analysis section to see the dashboard")
        return
    
    # Key metrics row
    st.subheader("Key Performance Indicators")
    metrics = st.session_state.csv_analysis.get('summary', {})
    
    if metrics:
        cols = st.columns(4)
        for i, (key, value) in enumerate(list(metrics.items())[:4]):
            with cols[i]:
                st.metric(
                    label=key.replace('_', ' ').title(),
                    value=f"{value:,.2f}" if isinstance(value, (int, float)) else str(value)
                )
    
    # Charts row
    col1, col2 = st.columns(2)
    
    with col1:
        # Growth trend chart
        if 'trends' in st.session_state.csv_analysis and 'yoy_growth' in st.session_state.csv_analysis['trends']:
            growth_data = st.session_state.csv_analysis['trends']['yoy_growth']
            if growth_data:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=[str(g['year']) for g in growth_data],
                    y=[g['growth_percentage'] for g in growth_data],
                    mode='lines+markers',
                    name='YoY Growth',
                    line=dict(color='#1f77b4', width=3),
                    marker=dict(size=8)
                ))
                fig.update_layout(
                    title="Revenue Growth Trend",
                    xaxis_title="Year",
                    yaxis_title="Growth %",
                    height=350
                )
                st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Ratios chart
        if 'ratios' in st.session_state.csv_analysis:
            ratios = st.session_state.csv_analysis['ratios']
            if ratios:
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=list(ratios.keys()),
                    y=list(ratios.values()),
                    marker_color='#2ca02c'
                ))
                fig.update_layout(
                    title="Financial Ratios",
                    xaxis_title="Ratio",
                    yaxis_title="Percentage",
                    height=350
                )
                st.plotly_chart(fig, use_container_width=True)
    
    # Insights section
    st.subheader("💡 Key Insights")
    if 'insights' in st.session_state.csv_analysis:
        for insight in st.session_state.csv_analysis['insights'][:5]:
            st.info(insight)
    
    # RAG stats
    if st.session_state.services['rag_engine']:
        st.subheader("📚 Document Repository")
        stats = st.session_state.services['rag_engine'].get_index_stats()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Vectors", stats.get('total_vectors', 0))
        with col2:
            st.metric("Vector Dimension", stats.get('vector_dimension', 0))
        with col3:
            st.metric("Distance Metric", stats.get('distance_metric', 'N/A'))

def show_settings():
    """Show settings page."""
    st.header("⚙️ Settings")
    
    # Display current configuration
    st.subheader("Current Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### OpenAI Settings")
        st.info(f"Model: {settings.llm_model}")
        st.info(f"Embedding Model: {settings.embedding_model}")
        st.info(f"Temperature: {settings.temperature}")
        st.info(f"Max Tokens: {settings.max_tokens}")
    
    with col2:
        st.markdown("### Qdrant Settings")
        st.info(f"Host: {settings.qdrant_host}")
        st.info(f"Port: {settings.qdrant_port}")
        st.info(f"Collection: {settings.qdrant_collection_name}")
    
    st.divider()
    
    # Instructions
    st.subheader("📝 Configuration Instructions")
    
    st.markdown("""
    To modify settings:
    
    1. Create a `.env` file in the project root
    2. Copy contents from `.env.example`
    3. Add your OpenAI API key
    4. Adjust other parameters as needed
    5. Restart the application
    
    ### Required Environment Variables:
    - `OPENAI_API_KEY`: Your OpenAI API key
    - `QDRANT_HOST`: Qdrant server host (default: localhost)
    - `QDRANT_PORT`: Qdrant server port (default: 6333)
    
    ### Optional Configuration:
    - `LLM_MODEL`: OpenAI model to use (default: gpt-4-turbo-preview)
    - `CHUNK_SIZE`: Document chunk size (default: 512)
    - `TEMPERATURE`: LLM temperature (default: 0.7)
    """)
    
    st.divider()
    
    # Data management
    st.subheader("🗑️ Data Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Clear Vector Database", type="secondary"):
            if st.session_state.services['rag_engine'].delete_documents("*"):
                st.success("✅ Vector database cleared")
                st.rerun()
            else:
                st.error("❌ Failed to clear vector database")
    
    with col2:
        if st.button("Reset Session", type="secondary"):
            st.session_state.csv_analysis = None
            st.session_state.rag_response = None
            st.success("✅ Session reset")
            st.rerun()

if __name__ == "__main__":
    main()