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
import base64

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
    
    /* Suppress browser console warnings for Popper.js */
    .st-emotion-cache-1wmy9hl { 
        z-index: 999999; 
    }
</style>
""", unsafe_allow_html=True)

def main():
    """Main application function."""
    
    # Header
    st.markdown('<h1 class="main-header">📊 Sistema di Business Intelligence RAG</h1>', unsafe_allow_html=True)
    
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
        st.header("🔧 Configurazione")
        
        # Navigation
        page = st.selectbox(
            "Seleziona Modulo",
            ["📈 Analisi Dati", "📚 RAG Documenti", "🤖 Approfondimenti IA", "📊 Cruscotto", "⚙️ Impostazioni"]
        )
        
        st.divider()
        
        # Quick Stats
        if st.session_state.services['rag_engine']:
            stats = st.session_state.services['rag_engine'].get_index_stats()
            st.metric("Vettori Indicizzati", stats.get('total_vectors', 0))
        
        if st.session_state.csv_analysis:
            st.metric("Dati Caricati", "✅ Attivi")
    
    # Main content based on selected page
    if page == "📈 Analisi Dati":
        show_data_analysis()
    elif page == "📚 RAG Documenti":
        show_document_rag()
    elif page == "🤖 Approfondimenti IA":
        show_ai_insights()
    elif page == "📊 Cruscotto":
        show_dashboard()
    elif page == "⚙️ Impostazioni":
        show_settings()

def show_data_analysis():
    """Show data analysis page."""
    st.header("📈 Analisi Dati Finanziari")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Carica Dati CSV")
        uploaded_file = st.file_uploader(
            "Scegli un file CSV con dati finanziari",
            type=['csv'],
            help="Carica bilanci, report sui ricavi, o qualsiasi dato aziendale strutturato"
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
                
                st.success(f"✅ Caricati {len(df)} record con {len(df.columns)} colonne")
                
                # Display data preview
                st.subheader("Anteprima Dati")
                st.dataframe(df.head(10), use_container_width=True)
                
                # Column selection for analysis
                with col2:
                    st.subheader("Configurazione Analisi")
                    
                    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
                    
                    year_col = st.selectbox(
                        "Colonna Anno/Periodo",
                        options=[col for col in df.columns if 'year' in col.lower() or 'anno' in col.lower() or 'period' in col.lower()] + ['None'],
                        index=0
                    )
                    
                    revenue_col = st.selectbox(
                        "Colonna Fatturato",
                        options=[col for col in numeric_cols if 'revenue' in col.lower() or 'fatturato' in col.lower() or 'sales' in col.lower()] + numeric_cols,
                        index=0 if any('revenue' in col.lower() or 'fatturato' in col.lower() for col in numeric_cols) else len(numeric_cols)-1
                    )
                    
                    if st.button("🔍 Analizza Dati", type="primary"):
                        with st.spinner("Analizzando dati finanziari..."):
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
                st.error(f"Errore nell'analisi dei dati: {str(e)}")

def display_analysis_results(analysis, df):
    """Display analysis results with visualizations."""
    st.subheader("📊 Risultati Analisi")
    
    # Tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["Riepilogo", "Tendenze", "Visualizzazioni", "Raccomandazioni"])
    
    with tab1:
        # Summary metrics
        if 'summary' in analysis:
            st.subheader("Metriche Principali")
            cols = st.columns(3)
            for i, (key, value) in enumerate(analysis['summary'].items()):
                with cols[i % 3]:
                    st.metric(key.replace('_', ' ').title(), f"{value:,.2f}")
        
        # Insights
        if 'insights' in analysis and analysis['insights']:
            st.subheader("💡 Approfondimenti Chiave")
            for i, insight in enumerate(analysis['insights']):
                # Debug: stampa il tipo e il valore
                st.write(f"**{i+1}.** {insight}")
    
    with tab2:
        # Trends
        if 'trends' in analysis and 'yoy_growth' in analysis['trends']:
            st.subheader("Tendenze di Crescita")
            
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
                    title="Crescita Anno su Anno (%)",
                    xaxis_title="Anno",
                    yaxis_title="Crescita %",
                    showlegend=False
                )
                st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        # Visualizations
        st.subheader("Visualizzazioni Dati")
        
        # Allow user to create custom charts
        col1, col2 = st.columns(2)
        with col1:
            chart_type = st.selectbox("Tipo Grafico", ["Linea", "Barre", "Dispersione", "Torta"])
        with col2:
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            if numeric_cols:
                y_axis = st.selectbox("Seleziona Metrica", numeric_cols)
                
                if chart_type == "Linea":
                    fig = px.line(df, y=y_axis, title=f"{y_axis} Trend")
                elif chart_type == "Barre":
                    fig = px.bar(df, y=y_axis, title=f"{y_axis} Distribution")
                elif chart_type == "Dispersione":
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
        st.subheader("📋 Raccomandazioni Strategiche")
        
        if st.button("Genera Raccomandazioni IA"):
            with st.spinner("Generando raccomandazioni..."):
                llm_service = st.session_state.services['llm_service']
                insights = llm_service.generate_business_insights(analysis)
                st.markdown(insights)

def show_document_rag():
    """Show document RAG page."""
    st.header("📚 Analisi Documenti (RAG)")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📄 Carica Documenti")
        uploaded_files = st.file_uploader(
            "Scegli documenti per l'analisi",
            type=['pdf', 'txt', 'docx', 'md'],
            accept_multiple_files=True,
            help="Carica report aziendali, contratti, o qualsiasi documento rilevante"
        )
        
        if uploaded_files:
            if st.button("🔄 Indicizza Documenti", type="primary"):
                with st.spinner("Indicizzando documenti..."):
                    file_paths = []
                    original_names = []
                    permanent_paths = []
                    
                    # Create documents directory if it doesn't exist
                    docs_dir = Path("data/documents")
                    docs_dir.mkdir(exist_ok=True)
                    
                    # Save uploaded files permanently for PDF viewing
                    for uploaded_file in uploaded_files:
                        # Save temporarily for processing
                        suffix = Path(uploaded_file.name).suffix
                        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                            tmp_file.write(uploaded_file.getbuffer())
                            file_paths.append(tmp_file.name)
                            original_names.append(uploaded_file.name)
                            
                        # Also save permanently for PDF viewer
                        permanent_path = docs_dir / uploaded_file.name
                        with open(permanent_path, 'wb') as f:
                            uploaded_file.seek(0)  # Reset file pointer
                            f.write(uploaded_file.getbuffer())
                        permanent_paths.append(str(permanent_path))
                    
                    # Index documents with original names and permanent paths
                    rag_engine = st.session_state.services['rag_engine']
                    results = rag_engine.index_documents(file_paths, original_names=original_names, permanent_paths=permanent_paths)
                    
                    # Display results
                    if results['indexed_files']:
                        st.success(f"✅ Indicizzati con successo {len(results['indexed_files'])} documenti con {results['total_chunks']} blocchi")
                        
                        # Store document analyses in session state
                        if 'document_analyses' not in st.session_state:
                            st.session_state.document_analyses = {}
                        st.session_state.document_analyses.update(results.get('document_analyses', {}))
                        
                    if results['failed_files']:
                        st.error(f"❌ Fallita indicizzazione di {len(results['failed_files'])} file")
                        for error in results['errors']:
                            st.error(error)
                    
                    # Cleanup
                    for path in file_paths:
                        os.unlink(path)
    
    with col2:
        st.subheader("🔍 Interroga Documenti")
        
        # Query interface with auto-execution support
        default_value = ""
        auto_execute = False
        
        # Check for auto query
        if hasattr(st.session_state, 'auto_query'):
            default_value = st.session_state.auto_query
            auto_execute = True
            delattr(st.session_state, 'auto_query')  # Clear after use
            
        query = st.text_area(
            "Fai domande sui tuoi documenti",
            value=default_value,
            placeholder="es., Quali sono i principali rischi aziendali menzionati? Qual era il focus strategico per il 2024?",
            height=100
        )
        
        col1_query, col2_query = st.columns([1, 1])
        with col1_query:
            top_k = st.slider("Numero di fonti", min_value=1, max_value=10, value=5)
        with col2_query:
            use_context = st.checkbox("Includi contesto analisi CSV", value=bool(st.session_state.csv_analysis))
        
        # Execute query either manually or automatically
        execute_query = st.button("🤔 Fai Domanda", type="primary", disabled=not query) or auto_execute
        
        if execute_query and query:
            # Show different spinner message for auto queries
            spinner_message = "Eseguendo query automatica..." if auto_execute else "Cercando e analizzando documenti..."
            with st.spinner(spinner_message):
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
        st.subheader("📝 Risposta")
        st.markdown(st.session_state.rag_response['answer'])
        
        if st.session_state.rag_response['sources']:
            st.subheader("📚 Fonti")
            for i, source in enumerate(st.session_state.rag_response['sources'], 1):
                with st.expander(f"Fonte {i} (Punteggio: {source['score']:.3f})"):
                    st.text(source['text'])
                    if source['metadata']:
                        # Check if it's a PDF with viewable path
                        metadata = source['metadata']
                        if metadata.get('file_type') == '.pdf' and 'pdf_path' in metadata:
                            col_meta, col_view = st.columns([2, 1])
                            with col_meta:
                                st.json(source['metadata'])
                            with col_view:
                                page_num = metadata.get('page', 1)
                                if st.button(f"📄 Visualizza Pagina {page_num}", key=f"view_{i}_{page_num}"):
                                    # Store PDF viewing info in session state
                                    st.session_state.pdf_to_view = {
                                        'path': metadata['pdf_path'],
                                        'page': page_num,
                                        'source_name': metadata.get('source', 'Documento')
                                    }
                                    st.rerun()
                        else:
                            st.json(source['metadata'])
    
    # Show document analyses (like NotebookLM)
    if hasattr(st.session_state, 'document_analyses') and st.session_state.document_analyses:
        st.divider()
        st.subheader("📑 Analisi Automatica dei Documenti")
        st.caption("Riepilogo intelligente del contenuto, simile a NotebookLM")
        st.info("ℹ️ I documenti sono stati processati e indicizzati. I file temporanei sono stati rimossi per sicurezza, ma il contenuto rimane accessibile per le query.")
        
        for file_name, analysis in st.session_state.document_analyses.items():
            with st.expander(f"📄 {file_name}", expanded=True):
                st.markdown(analysis)
                
                # Add some useful actions
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button(f"💬 Fai domande su questo documento", key=f"ask_{file_name}"):
                        query_text = f"Analizza il contenuto di {file_name} e fornisci una panoramica completa"
                        st.session_state.auto_query = query_text
                        st.rerun()
                        
                with col2:
                    if st.button(f"🔗 Confronta con CSV", key=f"compare_{file_name}"):
                        if st.session_state.csv_analysis:
                            query_text = f"Confronta i dati nel documento {file_name} con l'analisi CSV caricata e identifica correlazioni, discrepanze e insights"
                            st.session_state.auto_query = query_text
                            st.rerun()
                        else:
                            st.warning("⚠️ Carica prima i dati CSV nella sezione 'Analisi Dati'")
                            
                with col3:
                    if st.button(f"📊 Estrai KPI", key=f"kpi_{file_name}"):
                        query_text = f"Estrai tutti i KPI, metriche quantitative, percentuali, valori finanziari e indicatori di performance dal documento {file_name}. Organizza i risultati in categorie."
                        st.session_state.auto_query = query_text
                        st.rerun()
    
    # PDF Viewer Section
    if hasattr(st.session_state, 'pdf_to_view') and st.session_state.pdf_to_view:
        st.divider()
        pdf_info = st.session_state.pdf_to_view
        
        col_header, col_close = st.columns([4, 1])
        with col_header:
            st.subheader(f"📄 {pdf_info['source_name']} - Pagina {pdf_info['page']}")
        with col_close:
            if st.button("❌ Chiudi PDF", key="close_pdf"):
                del st.session_state.pdf_to_view
                st.rerun()
        
        # Try to display PDF
        try:
            pdf_path = Path(pdf_info['path'])
            if pdf_path.exists():
                # Read PDF file
                with open(pdf_path, 'rb') as f:
                    pdf_bytes = f.read()
                
                # Display PDF using Streamlit's built-in viewer
                st.markdown(f"**📍 Mostrando pagina {pdf_info['page']} del documento {pdf_info['source_name']}**")
                
                # Create download button for the PDF
                st.download_button(
                    label=f"📥 Scarica {pdf_info['source_name']}",
                    data=pdf_bytes,
                    file_name=pdf_info['source_name'],
                    mime="application/pdf"
                )
                
                # Show PDF (Streamlit doesn't have built-in PDF viewer, so we provide alternative)
                st.info(f"""
                💡 **Come visualizzare la pagina {pdf_info['page']}:**
                1. Clicca 'Scarica {pdf_info['source_name']}' qui sopra
                2. Apri il PDF con il tuo lettore preferito
                3. Vai alla pagina {pdf_info['page']} per vedere il contenuto citato
                """)
                
                # Show embedded PDF if possible (experimental)
                try:
                    import base64
                    # This is a simple embed attempt - may not work in all browsers
                    pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
                    pdf_display = f'''
                    <iframe 
                        src="data:application/pdf;base64,{pdf_base64}#page={pdf_info['page']}" 
                        width="100%" 
                        height="600px"
                        style="border: none;">
                        Il tuo browser non supporta la visualizzazione PDF integrata.
                    </iframe>
                    '''
                    st.markdown("### 📖 Anteprima PDF:")
                    st.markdown(pdf_display, unsafe_allow_html=True)
                except:
                    st.warning("⚠️ Visualizzazione PDF integrata non disponibile. Usa il pulsante di download.")
                    
            else:
                st.error(f"❌ File PDF non trovato: {pdf_path}")
                
        except Exception as e:
            st.error(f"❌ Errore nella visualizzazione del PDF: {str(e)}")

def show_ai_insights():
    """Show AI insights page."""
    st.header("🤖 Approfondimenti Basati sull'IA")
    
    if not st.session_state.csv_analysis:
        st.warning("⚠️ Per favore analizza prima i dati CSV nella sezione Analisi Dati")
        return
    
    # Tabs for different AI features
    tab1, tab2, tab3, tab4 = st.tabs(["Approfondimenti Aziendali", "Report Esecutivo", "Domande e Risposte", "Azioni da Intraprendere"])
    
    with tab1:
        st.subheader("💡 Approfondimenti Aziendali Completi")
        
        if st.button("Genera Approfondimenti", type="primary"):
            with st.spinner("Generando approfondimenti completi..."):
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
        st.subheader("📋 Report Esecutivo")
        
        # Custom sections input
        custom_sections = st.multiselect(
            "Seleziona sezioni del report",
            ["Riepilogo Esecutivo", "Performance Finanziaria", "Evidenze Operative",
             "Posizione di Mercato", "Valutazione del Rischio", "Raccomandazioni", "Prossimi Passi"],
            default=["Riepilogo Esecutivo", "Performance Finanziaria", "Raccomandazioni"]
        )
        
        if st.button("Genera Report Esecutivo", type="primary"):
            with st.spinner("Preparando report esecutivo..."):
                llm_service = st.session_state.services['llm_service']
                
                report = llm_service.generate_executive_report(
                    st.session_state.csv_analysis,
                    rag_insights=st.session_state.rag_response.get('answer') if st.session_state.rag_response else None,
                    custom_sections=custom_sections
                )
                
                st.markdown(report)
                
                # Download button
                st.download_button(
                    label="📥 Scarica Report",
                    data=report,
                    file_name=f"executive_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown"
                )
    
    with tab3:
        st.subheader("❓ Domande e Risposte Aziendali")
        
        question = st.text_area(
            "Fai domande aziendali specifiche",
            placeholder="es., Quali fattori hanno contribuito al cambiamento del fatturato? Quali sono i principali driver dei costi?",
            height=100
        )
        
        if st.button("Ottieni Risposta", type="primary", disabled=not question):
            with st.spinner("Elaborando domanda..."):
                llm_service = st.session_state.services['llm_service']
                
                # Combine all context
                context = {
                    'csv_analysis': st.session_state.csv_analysis,
                    'rag_context': st.session_state.rag_response if st.session_state.rag_response else None
                }
                
                answer = llm_service.answer_business_question(question, context)
                
                st.markdown(answer)
    
    with tab4:
        st.subheader("✅ Generatore di Azioni")
        
        priority_count = st.slider("Numero di azioni", min_value=5, max_value=20, value=10)
        
        if st.button("Genera Azioni", type="primary"):
            with st.spinner("Creando azioni prioritizzate..."):
                llm_service = st.session_state.services['llm_service']
                
                action_items = llm_service.generate_action_items(
                    st.session_state.csv_analysis,
                    priority_count=priority_count
                )
                
                if action_items:
                    # Traduci le chiavi in italiano se necessario
                    for action in action_items:
                        if 'action' not in action and 'azione' in action:
                            action['action'] = action.pop('azione')
                        if 'priority' not in action and 'priorita' in action:
                            action['priority'] = action.pop('priorita')
                        if 'timeline' not in action and 'tempistica' in action:
                            action['timeline'] = action.pop('tempistica')
                        if 'impact' not in action and 'impatto' in action:
                            action['impact'] = action.pop('impatto')
                        if 'owner' not in action and 'responsabile' in action:
                            action['owner'] = action.pop('responsabile')
                    
                    # Display as cards per migliore leggibilità
                    priority_order = {'alta': 1, 'high': 1, 'media': 2, 'medium': 2, 'bassa': 3, 'low': 3}
                    sorted_actions = sorted(action_items, key=lambda x: priority_order.get(x.get('priority', 'media').lower(), 2))
                    
                    for i, action in enumerate(sorted_actions, 1):
                        priority = action.get('priority', 'media').lower()
                        
                        # Colori per priorità
                        if priority in ['alta', 'high']:
                            color = "🔴"
                            bg_color = "#ffebee"
                        elif priority in ['media', 'medium']:
                            color = "🟡"
                            bg_color = "#fff8e1"
                        else:
                            color = "🟢"
                            bg_color = "#e8f5e8"
                        
                        with st.container():
                            st.markdown(f"""
                            <div style="background-color: {bg_color}; padding: 15px; border-radius: 10px; margin: 10px 0; border-left: 4px solid #2196F3;">
                                <h4>{color} Azione {i}: {action.get('action', 'N/A')}</h4>
                                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px;">
                                    <div><strong>📊 Priorità:</strong> {action.get('priority', 'N/A').title()}</div>
                                    <div><strong>⏰ Tempistica:</strong> {action.get('timeline', 'N/A')}</div>
                                    <div><strong>💪 Impatto:</strong> {action.get('impact', 'N/A')}</div>
                                    <div><strong>👤 Responsabile:</strong> {action.get('owner', 'N/A')}</div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                    
                    # Download as CSV
                    df_actions = pd.DataFrame(action_items)
                    # Traduci le colonne per il CSV
                    df_actions.columns = [
                        col.replace('action', 'azione')
                           .replace('priority', 'priorita')
                           .replace('timeline', 'tempistica') 
                           .replace('impact', 'impatto')
                           .replace('owner', 'responsabile')
                        for col in df_actions.columns
                    ]
                    
                    csv = df_actions.to_csv(index=False)
                    st.download_button(
                        label="📥 Scarica Azioni",
                        data=csv,
                        file_name=f"azioni_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.error("Fallita generazione delle azioni")

def show_dashboard():
    """Show dashboard page."""
    st.header("📊 Cruscotto Esecutivo")
    
    if not st.session_state.csv_analysis:
        st.info("📈 Carica dati nella sezione Analisi Dati per vedere il cruscotto")
        return
    
    # Key metrics row
    st.subheader("Indicatori Chiave di Performance")
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
                    title="Trend di Crescita Fatturato",
                    xaxis_title="Anno",
                    yaxis_title="Crescita %",
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
                    title="Rapporti Finanziari",
                    xaxis_title="Rapporto",
                    yaxis_title="Percentuale",
                    height=350
                )
                st.plotly_chart(fig, use_container_width=True)
    
    # Insights section
    st.subheader("💡 Approfondimenti Chiave")
    if 'insights' in st.session_state.csv_analysis:
        for insight in st.session_state.csv_analysis['insights'][:5]:
            st.info(insight)
    
    # RAG stats
    if st.session_state.services['rag_engine']:
        st.subheader("📚 Repository Documenti")
        stats = st.session_state.services['rag_engine'].get_index_stats()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Vettori Totali", stats.get('total_vectors', 0))
        with col2:
            st.metric("Dimensione Vettori", stats.get('vector_dimension', 0))
        with col3:
            st.metric("Metrica Distanza", stats.get('distance_metric', 'N/A'))

def show_settings():
    """Show settings page."""
    st.header("⚙️ Impostazioni")
    
    # Display current configuration
    st.subheader("Configurazione Corrente")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Impostazioni OpenAI")
        st.info(f"Modello: {settings.llm_model}")
        st.info(f"Modello Embedding: {settings.embedding_model}")
        st.info(f"Temperatura: {settings.temperature}")
        st.info(f"Token Massimi: {settings.max_tokens}")
    
    with col2:
        st.markdown("### Impostazioni Qdrant")
        st.info(f"Host: {settings.qdrant_host}")
        st.info(f"Port: {settings.qdrant_port}")
        st.info(f"Collezione: {settings.qdrant_collection_name}")
    
    st.divider()
    
    # Instructions
    st.subheader("📝 Istruzioni di Configurazione")
    
    st.markdown("""
    Per modificare le impostazioni:
    
    1. Crea un file `.env` nella root del progetto
    2. Copia il contenuto da `.env.example`
    3. Aggiungi la tua chiave API OpenAI
    4. Modifica altri parametri se necessario
    5. Riavvia l'applicazione
    
    ### Variabili di Ambiente Richieste:
    - `OPENAI_API_KEY`: La tua chiave API OpenAI
    - `QDRANT_HOST`: Host del server Qdrant (default: localhost)
    - `QDRANT_PORT`: Porta del server Qdrant (default: 6333)
    
    ### Configurazione Opzionale:
    - `LLM_MODEL`: Modello OpenAI da usare (default: gpt-4-turbo-preview)
    - `CHUNK_SIZE`: Dimensione blocchi documenti (default: 512)
    - `TEMPERATURE`: Temperatura LLM (default: 0.7)
    """)
    
    st.divider()
    
    # Data management
    st.subheader("🗑️ Gestione Dati")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Pulisci Database Vettoriale", type="secondary"):
            if st.session_state.services['rag_engine'].delete_documents("*"):
                st.success("✅ Database vettoriale pulito")
                # Clear document analyses from session
                if 'document_analyses' in st.session_state:
                    del st.session_state.document_analyses
                # Also clear PDF viewer
                if 'pdf_to_view' in st.session_state:
                    del st.session_state.pdf_to_view
                st.rerun()
            else:
                st.error("❌ Fallita pulizia database vettoriale")
    
    with col2:
        if st.button("Rimuovi Path Temporanei", type="secondary", help="Pulisce i percorsi temporanei dai metadata esistenti"):
            if st.session_state.services['rag_engine'].clean_metadata_paths():
                st.success("✅ Percorsi temporanei rimossi")
                # Clear analyses since documents were re-indexed
                if 'document_analyses' in st.session_state:
                    del st.session_state.document_analyses
                st.rerun()
            else:
                st.error("❌ Errore nella pulizia dei percorsi")
    
    with col3:
        if st.button("Resetta Sessione", type="secondary"):
            st.session_state.csv_analysis = None
            st.session_state.rag_response = None
            if 'document_analyses' in st.session_state:
                del st.session_state.document_analyses
            if 'pdf_to_view' in st.session_state:
                del st.session_state.pdf_to_view
            st.success("✅ Sessione resettata")
            st.rerun()
    
    # PDF Storage Management
    st.divider()
    st.subheader("📄 Gestione PDF")
    
    docs_dir = Path("data/documents")
    if docs_dir.exists():
        pdf_files = list(docs_dir.glob("*.pdf"))
        if pdf_files:
            st.info(f"📁 PDF salvati: {len(pdf_files)} file in {docs_dir}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📋 Mostra PDF Salvati", type="secondary"):
                    for pdf in pdf_files:
                        file_size = pdf.stat().st_size / 1024 / 1024  # MB
                        st.text(f"📄 {pdf.name} ({file_size:.1f} MB)")
            
            with col2:
                if st.button("🗑️ Elimina Tutti i PDF", type="secondary", help="Rimuove tutti i PDF salvati (NON influenza l'indicizzazione)"):
                    try:
                        for pdf in pdf_files:
                            pdf.unlink()
                        st.success(f"✅ Eliminati {len(pdf_files)} PDF")
                        if 'pdf_to_view' in st.session_state:
                            del st.session_state.pdf_to_view
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Errore nell'eliminazione: {str(e)}")
        else:
            st.info("📁 Nessun PDF salvato per la visualizzazione")
    else:
        st.info("📁 Cartella documenti non ancora creata")

if __name__ == "__main__":
    main()