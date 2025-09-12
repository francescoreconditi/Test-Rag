"""Main Streamlit application for Business Intelligence RAG System."""

from datetime import datetime
import os
from pathlib import Path
import tempfile

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config.settings import settings
from services.csv_analyzer import CSVAnalyzer
from services.llm_service import LLMService
from services.rag_engine import RAGEngine

# Page configuration
st.set_page_config(
    page_title="Business Intelligence RAG System", page_icon="📊", layout="wide", initial_sidebar_state="expanded"
)


# Initialize services
@st.cache_resource
def init_services(tenant_id: str = "default"):
    """Initialize and cache services with optional tenant context."""
    from src.core.security.multi_tenant_manager import MultiTenantManager

    # Get tenant context if available
    tenant_context = None
    if tenant_id != "default":
        manager = MultiTenantManager()
        tenant_context = manager.get_tenant(tenant_id)

    return {
        "csv_analyzer": CSVAnalyzer(),
        "rag_engine": RAGEngine(tenant_context=tenant_context),
        "llm_service": LLMService(),
    }


# Custom CSS
st.markdown(
    """
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
""",
    unsafe_allow_html=True,
)


def show_intelligent_faq():
    """Show intelligent FAQ generation page."""
    st.header("💬 FAQ Intelligenti")
    st.caption("Genera automaticamente domande frequenti basate sui tuoi documenti, come Google NotebookLM")

    rag_engine = st.session_state.services["rag_engine"]

    # Check if there are documents in the database
    stats = rag_engine.get_index_stats()

    if stats.get("total_vectors", 0) == 0:
        st.warning("📭 Nessun documento nel database. Carica documenti nella sezione 'RAG Documenti' per generare FAQ.")
        return

    # Show current database stats
    st.info(f"📊 Database pronto: {stats.get('total_vectors', 0)} blocchi indicizzati")

    # FAQ Generation Section
    st.subheader("🎯 Genera FAQ")

    col1, col2 = st.columns([2, 1])

    with col1:
        num_questions = st.slider(
            "Numero di domande FAQ da generare",
            min_value=5,
            max_value=20,
            value=10,
            step=1,
            help="Scegli quante domande frequenti vuoi generare",
        )

    with col2:
        st.metric("Documenti Indicizzati", stats.get("total_vectors", 0))

    # Generate FAQ button
    col_generate, col_info = st.columns([1, 2])

    with col_generate:
        generate_button = st.button("🤖 Genera FAQ", type="primary")

    with col_info:
        if generate_button:
            st.info("⚡ L'AI sta analizzando il database per creare domande intelligenti...")

    # Generate FAQ when button is clicked
    if generate_button:
        with st.spinner("🧠 Generando FAQ intelligenti basate sui tuoi documenti..."):
            faq_result = rag_engine.generate_faq(num_questions=num_questions)

        if faq_result.get("success", False):
            # Store FAQ in session state
            st.session_state.generated_faq = faq_result
            st.rerun()

    # Display generated FAQ
    if hasattr(st.session_state, "generated_faq") and st.session_state.generated_faq:
        faq_data = st.session_state.generated_faq

        if faq_data.get("error"):
            st.error(f"❌ {faq_data['error']}")
        else:
            faqs = faq_data.get("faqs", [])
            metadata = faq_data.get("metadata", {})

            if faqs:
                st.divider()
                st.subheader("📝 FAQ Generate")
                st.caption(f"Generate {len(faqs)} domande il {metadata.get('generated_at', 'N/A')}")

                # Show metadata
                if metadata.get("document_types"):
                    st.info(f"📊 Basate su documenti di tipo: {', '.join(metadata.get('document_types', []))}")

                # PDF Export functionality for FAQ
                st.divider()
                st.subheader("📄 Esporta FAQ")

                col_export_faq1, col_export_faq2 = st.columns([1, 1])

                with col_export_faq1:
                    if st.button("📄 Esporta FAQ PDF", type="primary", key="export_faq_pdf"):
                        try:
                            from src.presentation.streamlit.pdf_exporter import PDFExporter

                            # Generate PDF
                            pdf_exporter = PDFExporter()
                            pdf_buffer = pdf_exporter.export_faq(faqs=faqs, metadata=metadata)

                            # Create download button
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            filename = f"faq_intelligenti_{timestamp}.pdf"

                            st.download_button(
                                label="📥 Scarica FAQ PDF",
                                data=pdf_buffer.getvalue(),
                                file_name=filename,
                                mime="application/pdf",
                                key="download_faq_pdf",
                            )

                            st.success(f"✅ PDF FAQ generato con successo! ({len(faqs)} domande)")

                        except Exception as e:
                            st.error(f"❌ Errore nella generazione del PDF: {str(e)}")

                with col_export_faq2:
                    st.info(f"📊 {len(faqs)} domande pronte per l'esportazione")

                st.divider()

                # Display each FAQ
                for i, faq in enumerate(faqs, 1):
                    with st.expander(f"❓ Domanda {i}: {faq.get('question', 'N/A')[:80]}...", expanded=i <= 3):
                        # Question
                        st.markdown("**🤔 Domanda:**")
                        st.write(faq.get("question", "N/A"))

                        # Answer
                        st.markdown("**💡 Risposta:**")
                        st.write(faq.get("answer", "N/A"))

                        # Sources
                        sources = faq.get("sources", [])
                        if sources:
                            st.markdown(f"**📚 Fonti ({len(sources)}):**")
                            for j, source in enumerate(sources, 1):
                                with st.container():
                                    score = source.get("score", 0)
                                    st.caption(f"Fonte {j} (Rilevanza: {score:.1%})")

                                    # Source text preview
                                    source_text = source.get("text", "N/A")
                                    if len(source_text) > 200:
                                        source_text = source_text[:200] + "..."
                                    st.text(source_text)

                                    # Source metadata
                                    if source.get("metadata"):
                                        metadata_items = []
                                        for key in ["source", "page", "file_type"]:
                                            if key in source["metadata"]:
                                                value = source["metadata"][key]
                                                metadata_items.append(f"{key.title()}: {value}")

                                        if metadata_items:
                                            st.caption(" | ".join(metadata_items))

                        st.caption(f"Generata il: {faq.get('generated_at', 'N/A')}")

                # Action buttons at the bottom
                st.divider()
                col_actions1, col_actions2, col_actions3 = st.columns(3)

                with col_actions1:
                    if st.button("🔄 Genera Nuove FAQ", key="regenerate_faq"):
                        del st.session_state.generated_faq
                        st.rerun()

                with col_actions2:
                    if st.button("📋 Salva FAQ", key="save_faq"):
                        if "saved_faqs" not in st.session_state:
                            st.session_state.saved_faqs = []

                        st.session_state.saved_faqs.append(
                            {
                                "faqs": faqs,
                                "metadata": metadata,
                                "saved_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                            }
                        )

                        st.success(f"✅ FAQ salvate! (Totale salvate: {len(st.session_state.saved_faqs)})")

                with col_actions3:
                    if hasattr(st.session_state, "saved_faqs") and st.session_state.saved_faqs:
                        st.info(f"💾 {len(st.session_state.saved_faqs)} set di FAQ salvate")


def main():
    """Main application function."""

    # Check authentication
    if "tenant_context" not in st.session_state:
        st.warning("🔐 Please login first to access the application")
        if st.button("Go to Login Page"):
            st.switch_page("pages/00_🔐_Login.py")
        return

    # Get tenant context
    tenant = st.session_state.tenant_context

    # Header with tenant info
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown('<h1 class="main-header">📊 Sistema di Business Intelligence RAG</h1>', unsafe_allow_html=True)
    with col2:
        st.caption(f"🏢 {tenant.organization}")
        st.caption(f"📦 {tenant.tier.value} Plan")

    # Initialize services with tenant context
    if "services" not in st.session_state or st.session_state.get("current_tenant_id") != tenant.tenant_id:
        with st.spinner("Initializing tenant services..."):
            st.session_state.services = init_services(tenant.tenant_id)
            st.session_state.current_tenant_id = tenant.tenant_id

    if "csv_analysis" not in st.session_state:
        st.session_state.csv_analysis = None

    if "rag_response" not in st.session_state:
        st.session_state.rag_response = None

    # Sidebar
    with st.sidebar:
        # Tenant Info Section
        st.header(f"🏢 {tenant.organization}")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Tier", tenant.tier.value)
        with col2:
            st.metric("Tenant ID", tenant.tenant_id[:10] + "...")

        # Usage metrics
        from src.core.security.multi_tenant_manager import MultiTenantManager

        manager = MultiTenantManager()
        usage = manager.get_tenant_usage(tenant.tenant_id)

        with st.expander("📊 Usage Metrics", expanded=False):
            st.metric(
                "Documents Today", f"{usage.get('documents_today', 0)}/{tenant.resource_limits.max_documents_per_month}"
            )
            st.metric("Queries Today", f"{usage.get('queries_today', 0)}/{tenant.resource_limits.max_queries_per_day}")
            st.metric("Storage Used", f"{usage.get('storage_mb', 0):.1f} MB")

        # Logout button
        if st.button("🚪 Logout", use_container_width=True):
            for key in ["tenant_context", "jwt_token", "user_email", "services", "current_tenant_id"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.switch_page("pages/00_🔐_Login.py")

        st.divider()
        st.header("🔧 Configurazione")

        # Navigation
        page = st.selectbox(
            "Seleziona Modulo",
            [
                "📈 Analisi Dati",
                "📚 RAG Documenti",
                "💬 FAQ Intelligenti",
                "🔍 Explorer Database",
                "🤖 Approfondimenti IA",
                "📊 Cruscotto",
                "⚙️ Impostazioni",
            ],
        )

        st.divider()

        # Enterprise Mode Toggle
        st.header("🚀 Modalità Enterprise")
        enable_enterprise = st.checkbox(
            "Abilita funzionalità Enterprise",
            value=True,
            help="Attiva validazioni contabili, normalizzazione dati, retrieval ibrido e fact table",
        )

        if enable_enterprise:
            st.success("✅ Modalità Enterprise Attiva")
            st.caption("• Source References & Provenance")
            st.caption("• Validazioni Contabili")
            st.caption("• Normalizzazione Dati")
            st.caption("• Retrieval Ibrido BM25+Embeddings")
            st.caption("• Ontologia Sinonimi")
            st.caption("• Fact Table Dimensionale")
        else:
            st.info("ℹ️ Modalità Standard")

        # Store enterprise mode in session state
        st.session_state["enterprise_mode"] = enable_enterprise

        st.divider()

        # Quick Stats
        if st.session_state.services["rag_engine"]:
            stats = st.session_state.services["rag_engine"].get_index_stats()
            st.metric("Vettori Indicizzati", stats.get("total_vectors", 0))

            # Show enterprise orchestrator stats if available
            if enable_enterprise and hasattr(st.session_state.services["rag_engine"], "enterprise_orchestrator"):
                try:
                    enterprise_stats = st.session_state.services[
                        "rag_engine"
                    ].enterprise_orchestrator.get_processing_stats()
                    if enterprise_stats.get("total_queries", 0) > 0:
                        st.metric("Query Enterprise", enterprise_stats["total_queries"])
                        st.metric("Tasso di Successo", f"{enterprise_stats.get('success_rate_pct', 0):.1f}%")
                except Exception:
                    pass

        if st.session_state.csv_analysis:
            st.metric("Dati Caricati", "✅ Attivi")

    # Main content based on selected page
    if page == "📈 Analisi Dati":
        show_data_analysis()
    elif page == "📚 RAG Documenti":
        show_document_rag()
    elif page == "💬 FAQ Intelligenti":
        show_intelligent_faq()
    elif page == "🔍 Explorer Database":
        show_database_explorer()
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
            type=["csv"],
            help="Carica bilanci, report sui ricavi, o qualsiasi dato aziendale strutturato",
        )

        if uploaded_file:
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_path = tmp_file.name

            try:
                # Load and analyze CSV
                analyzer = st.session_state.services["csv_analyzer"]
                df = analyzer.load_csv(tmp_path)

                st.success(f"✅ Caricati {len(df)} record con {len(df.columns)} colonne")

                # Display data preview
                st.subheader("Anteprima Dati")
                st.dataframe(df.head(10), use_container_width=True)

                # Column selection for analysis
                with col2:
                    st.subheader("Configurazione Analisi")

                    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()

                    year_col = st.selectbox(
                        "Colonna Anno/Periodo",
                        options=[
                            col
                            for col in df.columns
                            if "year" in col.lower() or "anno" in col.lower() or "period" in col.lower()
                        ]
                        + ["None"],
                        index=0,
                    )

                    revenue_col = st.selectbox(
                        "Colonna Fatturato",
                        options=[
                            col
                            for col in numeric_cols
                            if "revenue" in col.lower() or "fatturato" in col.lower() or "sales" in col.lower()
                        ]
                        + numeric_cols,
                        index=0
                        if any("revenue" in col.lower() or "fatturato" in col.lower() for col in numeric_cols)
                        else len(numeric_cols) - 1,
                    )

                    if st.button("🔍 Analizza Dati", type="primary"):
                        with st.spinner("Analizzando dati finanziari..."):
                            # Perform analysis
                            if year_col != "None":
                                analysis = analyzer.analyze_balance_sheet(
                                    df, year_column=year_col, revenue_column=revenue_col
                                )
                            else:
                                analysis = {"summary": analyzer.calculate_kpis(df), "insights": []}

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
        if "summary" in analysis:
            st.subheader("Metriche Principali")
            cols = st.columns(3)
            for i, (key, value) in enumerate(analysis["summary"].items()):
                with cols[i % 3]:
                    st.metric(key.replace("_", " ").title(), f"{value:,.2f}")

        # Insights
        if "insights" in analysis and analysis["insights"]:
            st.subheader("💡 Approfondimenti Chiave")
            for i, insight in enumerate(analysis["insights"]):
                # Debug: stampa il tipo e il valore
                st.write(f"**{i + 1}.** {insight}")

    with tab2:
        # Trends
        if "trends" in analysis and "yoy_growth" in analysis["trends"]:
            st.subheader("Tendenze di Crescita")

            growth_data = analysis["trends"]["yoy_growth"]
            if growth_data:
                # Create trend chart
                fig = go.Figure()
                fig.add_trace(
                    go.Bar(
                        x=[str(g["year"]) for g in growth_data],
                        y=[g["growth_percentage"] for g in growth_data],
                        text=[f"{g['growth_percentage']:.1f}%" for g in growth_data],
                        textposition="auto",
                        marker_color=["green" if g["growth_percentage"] > 0 else "red" for g in growth_data],
                    )
                )
                fig.update_layout(
                    title="Crescita Anno su Anno (%)", xaxis_title="Anno", yaxis_title="Crescita %", showlegend=False
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
            numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
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
                llm_service = st.session_state.services["llm_service"]
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
            type=["pdf", "txt", "docx", "md", "json", "csv"],
            accept_multiple_files=True,
            help="Carica report aziendali, contratti, CSV con dati finanziari, o qualsiasi documento rilevante",
        )

        # Prompt selection
        st.subheader("🎯 Tipo di Analisi")
        prompt_options = ["Automatico (raccomandato)"] + [
            f"{prompt_type.capitalize()} - {desc}"
            for prompt_type, desc in zip(
                ["bilancio", "fatturato", "magazzino", "contratto", "presentazione", "csv", "generale"],
                [
                    "Analisi finanziaria per bilanci e report finanziari",
                    "Analisi vendite e ricavi",
                    "Analisi logistica e gestione scorte",
                    "Analisi legale e contrattuale",
                    "Analisi di presentazioni e slide deck",
                    "Analisi dati CSV con insights automatici",
                    "Analisi generica per qualsiasi tipo di documento",
                ],
            )
        ]

        selected_prompt = st.selectbox(
            "Seleziona il tipo di prompt per l'analisi:",
            options=prompt_options,
            index=0,
            help="Il sistema sceglierà automaticamente il prompt migliore, ma puoi forzare un tipo specifico se necessario",
        )

        if uploaded_files:
            col_btn1, col_btn2 = st.columns([1, 1])
            with col_btn1:
                index_button = st.button("🔄 Indicizza Documenti", type="primary")
            with col_btn2:
                reanalyze_button = st.button(
                    "🔄 Ri-analizza con Prompt Selezionato",
                    disabled=not hasattr(st.session_state, "document_analyses")
                    or not st.session_state.document_analyses,
                    help="Ri-esegui l'analisi dei documenti già indicizzati con il prompt selezionato",
                )

            if index_button:
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
                        with open(permanent_path, "wb") as f:
                            uploaded_file.seek(0)  # Reset file pointer
                            f.write(uploaded_file.getbuffer())
                        permanent_paths.append(str(permanent_path))

                    # Get the selected prompt type for analysis
                    force_prompt_type = None
                    if selected_prompt != "Automatico (raccomandato)":
                        # Extract the prompt type from the selection (e.g., "Bilancio - ..." -> "bilancio")
                        force_prompt_type = selected_prompt.split(" - ")[0].lower()

                    # Index documents with original names and permanent paths
                    rag_engine = st.session_state.services["rag_engine"]
                    csv_analyzer = st.session_state.services["csv_analyzer"]

                    # Check if any files are CSV and show special handling
                    csv_files = [name for name in original_names if name.lower().endswith(".csv")]
                    if csv_files:
                        st.info(f"📊 Rilevati {len(csv_files)} file CSV che saranno analizzati con insights automatici")

                    results = rag_engine.index_documents(
                        file_paths,
                        original_names=original_names,
                        permanent_paths=permanent_paths,
                        force_prompt_type=force_prompt_type,
                        csv_analyzer=csv_analyzer,  # Pass CSV analyzer for enhanced processing
                    )

                    # Display results
                    if results["indexed_files"]:
                        st.success(
                            f"✅ Indicizzati con successo {len(results['indexed_files'])} documenti con {results['total_chunks']} blocchi"
                        )

                        # Show CSV-specific results
                        if csv_files:
                            csv_processed = [f for f in results["indexed_files"] if f.lower().endswith(".csv")]
                            if csv_processed:
                                st.info(f"📊 File CSV processati con analisi automatica: {', '.join(csv_processed)}")
                                st.caption(
                                    "I CSV sono stati convertiti in documenti searchable con insights AI-generated"
                                )

                        # Show prompt type used
                        if force_prompt_type:
                            st.info(f"🎯 Utilizzato prompt specializzato: {selected_prompt}")
                        else:
                            st.info("🤖 Utilizzata selezione automatica del prompt ottimale per ogni documento")

                        # Store document analyses in session state
                        if "document_analyses" not in st.session_state:
                            st.session_state.document_analyses = {}
                        st.session_state.document_analyses.update(results.get("document_analyses", {}))

                    if results["failed_files"]:
                        st.error(f"❌ Fallita indicizzazione di {len(results['failed_files'])} file")
                        for error in results["errors"]:
                            st.error(error)

                    # Cleanup
                    for path in file_paths:
                        os.unlink(path)

            elif reanalyze_button and selected_prompt != "Automatico (raccomandato)":
                # Re-analyze existing documents with the selected prompt
                with st.spinner("Ri-analizzando documenti con il prompt selezionato..."):
                    # Extract prompt type
                    force_prompt_type = selected_prompt.split(" - ")[0].lower()

                    # Re-analyze documents
                    rag_engine = st.session_state.services["rag_engine"]
                    new_analyses = rag_engine.reanalyze_documents_with_prompt(force_prompt_type)

                    if "error" in new_analyses:
                        st.error(f"❌ {new_analyses['error']}")
                    else:
                        # Update session state with new analyses
                        st.session_state.document_analyses = new_analyses
                        st.success(
                            f"✅ Ri-analizzati {len(new_analyses)} documenti con prompt '{force_prompt_type.upper()}'"
                        )
                        st.info(f"🎯 Utilizzato prompt specializzato: {selected_prompt}")

            elif reanalyze_button and selected_prompt == "Automatico (raccomandato)":
                st.warning("⚠️ Seleziona un tipo di prompt specifico per ri-analizzare i documenti")

    with col2:
        st.subheader("🔍 Interroga Documenti")

        # Query interface with auto-execution support
        default_value = ""
        auto_execute = False

        # Check for auto query
        if hasattr(st.session_state, "auto_query"):
            default_value = st.session_state.auto_query
            auto_execute = True
            delattr(st.session_state, "auto_query")  # Clear after use

        query = st.text_area(
            "Fai domande sui tuoi documenti",
            value=default_value,
            placeholder="es., Quali sono i principali rischi aziendali menzionati? Qual era il focus strategico per il 2024?",
            height=100,
        )

        # Analysis type selection for queries
        st.subheader("🎯 Tipo di Analisi per Query")
        query_analysis_options = [
            "Standard (RAG normale)",
            "Bilancio - Analisi finanziaria per bilanci e report finanziari",
            "Report Dettagliato - Stile Investment memo",
            "Fatturato - Analisi vendite e ricavi",
            "Magazzino - Analisi logistica e gestione scorte",
            "Contratto - Analisi legale e contrattuale",
            "Presentazione - Analisi di presentazioni e slide deck",
        ]

        selected_query_analysis = st.selectbox(
            "Applica un tipo di analisi specializzata alla risposta:",
            options=query_analysis_options,
            index=0,
            help="Puoi applicare un'analisi specializzata anche alle query sui documenti già indicizzati",
        )

        # Extract analysis type from selection
        query_analysis_type = None
        if selected_query_analysis != "Standard (RAG normale)":
            query_analysis_type = selected_query_analysis.split(" - ")[0].lower().replace(" ", "_")

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
            if query_analysis_type:
                spinner_message = f"Applicando analisi {query_analysis_type.upper()}..."

            with st.spinner(spinner_message):
                rag_engine = st.session_state.services["rag_engine"]

                # Check if enterprise mode is enabled
                enterprise_mode = st.session_state.get("enterprise_mode", False)

                try:
                    if enterprise_mode:
                        # Use enterprise query mode
                        import asyncio

                        try:
                            # Run enterprise query asynchronously
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)

                            response = loop.run_until_complete(
                                rag_engine.enterprise_query(
                                    query_text=query,
                                    enable_enterprise_features=True,
                                    top_k=top_k,
                                    use_context=use_context,
                                    csv_analysis=st.session_state.csv_analysis if use_context else None,
                                )
                            )

                            # Show enterprise processing details
                            if "enterprise_data" in response:
                                enterprise_data = response["enterprise_data"]

                                # Show processing stats in sidebar
                                with st.sidebar:
                                    st.header("🚀 Stats Enterprise")
                                    st.metric("Tempo Elaborazione", f"{enterprise_data['processing_time_ms']:.0f}ms")
                                    st.metric("Confidenza", f"{response['confidence']:.1%}")
                                    st.metric("Record Fact Table", enterprise_data["fact_table_records"])

                                    if enterprise_data["warnings"]:
                                        st.warning(f"⚠️ {len(enterprise_data['warnings'])} avvisi")
                                    if enterprise_data["errors"]:
                                        st.error(f"❌ {len(enterprise_data['errors'])} errori")

                        except Exception as e:
                            st.warning(f"Enterprise mode fallback: {e}")
                            # Fallback to standard mode
                            if use_context and st.session_state.csv_analysis:
                                response = rag_engine.query_with_context(
                                    query, st.session_state.csv_analysis, top_k=top_k, analysis_type=query_analysis_type
                                )
                            else:
                                response = rag_engine.query(query, top_k=top_k, analysis_type=query_analysis_type)
                    else:
                        # Standard mode
                        if use_context and st.session_state.csv_analysis:
                            response = rag_engine.query_with_context(
                                query, st.session_state.csv_analysis, top_k=top_k, analysis_type=query_analysis_type
                            )
                        else:
                            response = rag_engine.query(query, top_k=top_k, analysis_type=query_analysis_type)

                except Exception as e:
                    st.error(f"Errore durante la query: {e}")
                    response = {"answer": f"Errore durante l'elaborazione: {str(e)}", "sources": [], "confidence": 0}

                st.session_state.rag_response = response

    # Display RAG response
    if st.session_state.rag_response:
        st.divider()
        st.subheader("📝 Risposta")
        st.markdown(st.session_state.rag_response["answer"])

        # PDF Export functionality
        st.divider()
        st.subheader("📄 Esporta Sessione Q&A")

        # Import PDF exporter
        from src.presentation.streamlit.pdf_exporter import PDFExporter

        col_export1, col_export2, col_export3 = st.columns([1, 1, 2])

        with col_export1:
            if st.button("📄 Esporta PDF", type="primary", key="export_single_pdf"):
                try:
                    # Get the current Q&A session data
                    if hasattr(st.session_state, "last_query"):
                        question = st.session_state.last_query
                    else:
                        # Try to get from text area (may not work in all cases)
                        question = query if "query" in locals() and query else "Domanda non disponibile"

                    answer = st.session_state.rag_response["answer"]
                    sources = st.session_state.rag_response["sources"]

                    # Create metadata
                    metadata = {
                        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                        "sources_count": len(sources),
                        "analysis_type": query_analysis_type
                        if "query_analysis_type" in locals() and query_analysis_type
                        else "Standard",
                    }

                    # Generate PDF
                    pdf_exporter = PDFExporter()
                    pdf_buffer = pdf_exporter.export_qa_session(
                        question=question, answer=answer, sources=sources, metadata=metadata
                    )

                    # Create download button
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"qa_session_{timestamp}.pdf"

                    st.download_button(
                        label="📥 Scarica PDF",
                        data=pdf_buffer.getvalue(),
                        file_name=filename,
                        mime="application/pdf",
                        key="download_qa_pdf",
                    )

                    st.success("✅ PDF generato con successo! Usa il pulsante 'Scarica PDF' per salvarlo.")

                except Exception as e:
                    st.error(f"❌ Errore nella generazione del PDF: {str(e)}")

        with col_export2:
            if st.button("📋 Salva Sessione", key="save_session"):
                # Store the current session for later export
                if "qa_sessions" not in st.session_state:
                    st.session_state.qa_sessions = []

                session_data = {
                    "question": st.session_state.get(
                        "last_query", query if "query" in locals() and query else "Domanda non disponibile"
                    ),
                    "answer": st.session_state.rag_response["answer"],
                    "sources": st.session_state.rag_response["sources"],
                    "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                    "metadata": {
                        "analysis_type": query_analysis_type
                        if "query_analysis_type" in locals() and query_analysis_type
                        else "Standard"
                    },
                }

                st.session_state.qa_sessions.append(session_data)
                st.success(f"✅ Sessione salvata! ({len(st.session_state.qa_sessions)} sessioni totali)")

        with col_export3:
            # Show export multiple sessions option if sessions exist
            if hasattr(st.session_state, "qa_sessions") and st.session_state.qa_sessions:
                if st.button(
                    f"📑 Esporta tutte ({len(st.session_state.qa_sessions)} sessioni)", key="export_all_sessions"
                ):
                    try:
                        pdf_exporter = PDFExporter()
                        pdf_buffer = pdf_exporter.export_multiple_sessions(st.session_state.qa_sessions)

                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"qa_sessions_report_{timestamp}.pdf"

                        st.download_button(
                            label="📥 Scarica Report Completo",
                            data=pdf_buffer.getvalue(),
                            file_name=filename,
                            mime="application/pdf",
                            key="download_all_sessions_pdf",
                        )

                        st.success(f"✅ Report completo generato con {len(st.session_state.qa_sessions)} sessioni!")

                    except Exception as e:
                        st.error(f"❌ Errore nella generazione del report: {str(e)}")

        # Store current query for PDF export
        if "query" in locals() and query:
            st.session_state.last_query = query

        if st.session_state.rag_response["sources"]:
            st.subheader("📚 Fonti")
            for i, source in enumerate(st.session_state.rag_response["sources"], 1):
                with st.expander(f"Fonte {i} (Punteggio: {source['score']:.3f})"):
                    st.text(source["text"])
                    if source["metadata"]:
                        # Check if it's a PDF with viewable path
                        metadata = source["metadata"]
                        if metadata.get("file_type") == ".pdf" and "pdf_path" in metadata:
                            col_meta, col_view = st.columns([2, 1])
                            with col_meta:
                                st.json(source["metadata"])
                            with col_view:
                                page_num = metadata.get("page", 1)
                                if st.button(f"📄 Visualizza Pagina {page_num}", key=f"view_{i}_{page_num}"):
                                    # Store PDF viewing info in session state
                                    st.session_state.pdf_to_view = {
                                        "path": metadata["pdf_path"],
                                        "page": page_num,
                                        "source_name": metadata.get("source", "Documento"),
                                    }
                                    st.rerun()
                        else:
                            st.json(source["metadata"])

    # Show document analyses (like NotebookLM)
    if hasattr(st.session_state, "document_analyses") and st.session_state.document_analyses:
        st.divider()
        st.subheader("📑 Analisi Automatica dei Documenti")
        st.caption("Riepilogo intelligente del contenuto, simile a NotebookLM")
        st.info(
            "ℹ️ I documenti sono stati processati e indicizzati. I file temporanei sono stati rimossi per sicurezza, ma il contenuto rimane accessibile per le query."
        )

        # PDF Export functionality for document analyses
        st.divider()
        st.subheader("📄 Esporta Analisi Documenti")

        col_export_docs1, col_export_docs2 = st.columns([1, 1])

        with col_export_docs1:
            if st.button("📄 Esporta Analisi PDF", type="primary", key="export_document_analysis_pdf"):
                try:
                    from src.presentation.streamlit.pdf_exporter import PDFExporter

                    # Create metadata for the analysis
                    analysis_metadata = {
                        "numero_documenti": len(st.session_state.document_analyses),
                        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                        "tipo_analisi": "Analisi Automatica Documenti RAG",
                    }

                    # Generate PDF
                    pdf_exporter = PDFExporter()
                    pdf_buffer = pdf_exporter.export_document_analysis(
                        document_analyses=st.session_state.document_analyses, metadata=analysis_metadata
                    )

                    # Create download button
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"analisi_documenti_{timestamp}.pdf"

                    st.download_button(
                        label="📥 Scarica Analisi PDF",
                        data=pdf_buffer.getvalue(),
                        file_name=filename,
                        mime="application/pdf",
                        key="download_analysis_pdf",
                    )

                    st.success(
                        f"✅ PDF delle analisi generato con successo! ({len(st.session_state.document_analyses)} documenti)"
                    )

                except Exception as e:
                    st.error(f"❌ Errore nella generazione del PDF: {str(e)}")

        with col_export_docs2:
            st.info(f"📊 {len(st.session_state.document_analyses)} documenti analizzati pronti per l'esportazione")

        st.divider()

        for file_name, analysis in st.session_state.document_analyses.items():
            with st.expander(f"📄 {file_name}", expanded=True):
                st.markdown(analysis)

                # Add some useful actions
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("💬 Fai domande su questo documento", key=f"ask_{file_name}"):
                        query_text = f"Analizza il contenuto di {file_name} e fornisci una panoramica completa"
                        st.session_state.auto_query = query_text
                        st.rerun()

                with col2:
                    if st.button("🔗 Confronta con CSV", key=f"compare_{file_name}"):
                        if st.session_state.csv_analysis:
                            query_text = f"Confronta i dati nel documento {file_name} con l'analisi CSV caricata e identifica correlazioni, discrepanze e insights"
                            st.session_state.auto_query = query_text
                            st.rerun()
                        else:
                            st.warning("⚠️ Carica prima i dati CSV nella sezione 'Analisi Dati'")

                with col3:
                    if st.button("📊 Estrai KPI", key=f"kpi_{file_name}"):
                        query_text = f"Estrai tutti i KPI, metriche quantitative, percentuali, valori finanziari e indicatori di performance dal documento {file_name}. Organizza i risultati in categorie."
                        st.session_state.auto_query = query_text
                        st.rerun()

    # PDF Viewer Section
    if hasattr(st.session_state, "pdf_to_view") and st.session_state.pdf_to_view:
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
            pdf_path = Path(pdf_info["path"])
            if pdf_path.exists():
                # Read PDF file
                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()

                # Display PDF using Streamlit's built-in viewer
                st.markdown(f"**📍 Mostrando pagina {pdf_info['page']} del documento {pdf_info['source_name']}**")

                # Create download button for the PDF
                st.download_button(
                    label=f"📥 Scarica {pdf_info['source_name']}",
                    data=pdf_bytes,
                    file_name=pdf_info["source_name"],
                    mime="application/pdf",
                )

                # Show PDF (Streamlit doesn't have built-in PDF viewer, so we provide alternative)
                st.info(f"""
                💡 **Come visualizzare la pagina {pdf_info["page"]}:**
                1. Clicca 'Scarica {pdf_info["source_name"]}' qui sopra
                2. Apri il PDF con il tuo lettore preferito
                3. Vai alla pagina {pdf_info["page"]} per vedere il contenuto citato
                """)

                # Show embedded PDF if possible (experimental)
                try:
                    import base64

                    # This is a simple embed attempt - may not work in all browsers
                    pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
                    pdf_display = f"""
                    <iframe
                        src="data:application/pdf;base64,{pdf_base64}#page={pdf_info["page"]}"
                        width="100%"
                        height="600px"
                        style="border: none;">
                        Il tuo browser non supporta la visualizzazione PDF integrata.
                    </iframe>
                    """
                    st.markdown("### 📖 Anteprima PDF:")
                    st.markdown(pdf_display, unsafe_allow_html=True)
                except Exception:
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
    tab1, tab2, tab3, tab4 = st.tabs(
        ["Approfondimenti Aziendali", "Report Esecutivo", "Domande e Risposte", "Azioni da Intraprendere"]
    )

    with tab1:
        st.subheader("💡 Approfondimenti Aziendali Completi")

        if st.button("Genera Approfondimenti", type="primary"):
            with st.spinner("Generando approfondimenti completi..."):
                llm_service = st.session_state.services["llm_service"]

                # Get RAG context if available
                rag_context = None
                if st.session_state.rag_response:
                    rag_context = st.session_state.rag_response.get("answer", "")

                insights = llm_service.generate_business_insights(st.session_state.csv_analysis, rag_context)

                st.markdown(insights)

    with tab2:
        st.subheader("📋 Report Esecutivo")

        # Custom sections input
        custom_sections = st.multiselect(
            "Seleziona sezioni del report",
            [
                "Riepilogo Esecutivo",
                "Performance Finanziaria",
                "Evidenze Operative",
                "Posizione di Mercato",
                "Valutazione del Rischio",
                "Raccomandazioni",
                "Prossimi Passi",
            ],
            default=["Riepilogo Esecutivo", "Performance Finanziaria", "Raccomandazioni"],
        )

        if st.button("Genera Report Esecutivo", type="primary"):
            with st.spinner("Preparando report esecutivo..."):
                llm_service = st.session_state.services["llm_service"]

                report = llm_service.generate_executive_report(
                    st.session_state.csv_analysis,
                    rag_insights=st.session_state.rag_response.get("answer") if st.session_state.rag_response else None,
                    custom_sections=custom_sections,
                )

                st.markdown(report)

                # Download button
                st.download_button(
                    label="📥 Scarica Report",
                    data=report,
                    file_name=f"executive_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown",
                )

    with tab3:
        st.subheader("❓ Domande e Risposte Aziendali")

        question = st.text_area(
            "Fai domande aziendali specifiche",
            placeholder="es., Quali fattori hanno contribuito al cambiamento del fatturato? Quali sono i principali driver dei costi?",
            height=100,
        )

        if st.button("Ottieni Risposta", type="primary", disabled=not question):
            with st.spinner("Elaborando domanda..."):
                llm_service = st.session_state.services["llm_service"]

                # Combine all context
                context = {
                    "csv_analysis": st.session_state.csv_analysis,
                    "rag_context": st.session_state.rag_response if st.session_state.rag_response else None,
                }

                answer = llm_service.answer_business_question(question, context)

                st.markdown(answer)

    with tab4:
        st.subheader("✅ Generatore di Azioni")

        priority_count = st.slider("Numero di azioni", min_value=5, max_value=20, value=10)

        if st.button("Genera Azioni", type="primary"):
            with st.spinner("Creando azioni prioritizzate..."):
                llm_service = st.session_state.services["llm_service"]

                action_items = llm_service.generate_action_items(
                    st.session_state.csv_analysis, priority_count=priority_count
                )

                if action_items:
                    # Traduci le chiavi in italiano se necessario
                    for action in action_items:
                        if "action" not in action and "azione" in action:
                            action["action"] = action.pop("azione")
                        if "priority" not in action and "priorita" in action:
                            action["priority"] = action.pop("priorita")
                        if "timeline" not in action and "tempistica" in action:
                            action["timeline"] = action.pop("tempistica")
                        if "impact" not in action and "impatto" in action:
                            action["impact"] = action.pop("impatto")
                        if "owner" not in action and "responsabile" in action:
                            action["owner"] = action.pop("responsabile")

                    # Display as cards per migliore leggibilità
                    priority_order = {"alta": 1, "high": 1, "media": 2, "medium": 2, "bassa": 3, "low": 3}
                    sorted_actions = sorted(
                        action_items, key=lambda x: priority_order.get(x.get("priority", "media").lower(), 2)
                    )

                    for i, action in enumerate(sorted_actions, 1):
                        priority = action.get("priority", "media").lower()

                        # Colori per priorità
                        if priority in ["alta", "high"]:
                            color = "🔴"
                            bg_color = "#ffebee"
                        elif priority in ["media", "medium"]:
                            color = "🟡"
                            bg_color = "#fff8e1"
                        else:
                            color = "🟢"
                            bg_color = "#e8f5e8"

                        with st.container():
                            st.markdown(
                                f"""
                            <div style="background-color: {bg_color}; padding: 15px; border-radius: 10px; margin: 10px 0; border-left: 4px solid #2196F3;">
                                <h4>{color} Azione {i}: {action.get("action", "N/A")}</h4>
                                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px;">
                                    <div><strong>📊 Priorità:</strong> {action.get("priority", "N/A").title()}</div>
                                    <div><strong>⏰ Tempistica:</strong> {action.get("timeline", "N/A")}</div>
                                    <div><strong>💪 Impatto:</strong> {action.get("impact", "N/A")}</div>
                                    <div><strong>👤 Responsabile:</strong> {action.get("owner", "N/A")}</div>
                                </div>
                            </div>
                            """,
                                unsafe_allow_html=True,
                            )

                    # Download as CSV
                    df_actions = pd.DataFrame(action_items)
                    # Traduci le colonne per il CSV
                    df_actions.columns = [
                        col.replace("action", "azione")
                        .replace("priority", "priorita")
                        .replace("timeline", "tempistica")
                        .replace("impact", "impatto")
                        .replace("owner", "responsabile")
                        for col in df_actions.columns
                    ]

                    csv = df_actions.to_csv(index=False)
                    st.download_button(
                        label="📥 Scarica Azioni",
                        data=csv,
                        file_name=f"azioni_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
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
    metrics = st.session_state.csv_analysis.get("summary", {})

    if metrics:
        cols = st.columns(4)
        for i, (key, value) in enumerate(list(metrics.items())[:4]):
            with cols[i]:
                st.metric(
                    label=key.replace("_", " ").title(),
                    value=f"{value:,.2f}" if isinstance(value, (int, float)) else str(value),
                )

    # Charts row
    col1, col2 = st.columns(2)

    with col1:
        # Growth trend chart
        if "trends" in st.session_state.csv_analysis and "yoy_growth" in st.session_state.csv_analysis["trends"]:
            growth_data = st.session_state.csv_analysis["trends"]["yoy_growth"]
            if growth_data:
                fig = go.Figure()
                fig.add_trace(
                    go.Scatter(
                        x=[str(g["year"]) for g in growth_data],
                        y=[g["growth_percentage"] for g in growth_data],
                        mode="lines+markers",
                        name="YoY Growth",
                        line={"color": "#1f77b4", "width": 3},
                        marker={"size": 8},
                    )
                )
                fig.update_layout(
                    title="Trend di Crescita Fatturato", xaxis_title="Anno", yaxis_title="Crescita %", height=350
                )
                st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Ratios chart
        if "ratios" in st.session_state.csv_analysis:
            ratios = st.session_state.csv_analysis["ratios"]
            if ratios:
                fig = go.Figure()
                fig.add_trace(go.Bar(x=list(ratios.keys()), y=list(ratios.values()), marker_color="#2ca02c"))
                fig.update_layout(
                    title="Rapporti Finanziari", xaxis_title="Rapporto", yaxis_title="Percentuale", height=350
                )
                st.plotly_chart(fig, use_container_width=True)

    # Insights section
    st.subheader("💡 Approfondimenti Chiave")
    if "insights" in st.session_state.csv_analysis:
        for insight in st.session_state.csv_analysis["insights"][:5]:
            st.info(insight)

    # RAG stats
    if st.session_state.services["rag_engine"]:
        st.subheader("📚 Repository Documenti")
        stats = st.session_state.services["rag_engine"].get_index_stats()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Vettori Totali", stats.get("total_vectors", 0))
        with col2:
            st.metric("Dimensione Vettori", stats.get("vector_dimension", 0))
        with col3:
            st.metric("Metrica Distanza", stats.get("distance_metric", "N/A"))


def show_database_explorer():
    """Show database explorer page."""
    st.header("🔍 Explorer Database Qdrant")

    rag_engine = st.session_state.services["rag_engine"]

    # Get database stats
    stats = rag_engine.get_index_stats()

    # Top metrics row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Vettori Totali", stats.get("total_vectors", 0))
    with col2:
        st.metric("Dimensioni Vettori", stats.get("vector_dimension", 0))
    with col3:
        st.metric("Collezione", stats.get("collection_name", "N/A"))
    with col4:
        st.metric("Distanza", stats.get("distance_metric", "N/A").split(".")[-1])

    if stats.get("total_vectors", 0) == 0:
        st.warning("📭 Il database è vuoto. Carica alcuni documenti nella sezione 'RAG Documenti' per iniziare.")
        return

    st.divider()

    # Create tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(
        ["📋 Panoramica Documenti", "🔍 Ricerca Semantica", "📄 Dettagli Chunk", "🛠️ Gestione"]
    )

    with tab1:
        st.subheader("📋 Documenti Indicizzati")

        # Get exploration data
        with st.spinner("Caricando informazioni database..."):
            exploration_data = rag_engine.explore_database(limit=50)

        if "error" in exploration_data:
            st.error(f"❌ Errore nel caricamento: {exploration_data['error']}")
            return

        # Display summary stats
        stats_data = exploration_data.get("stats", {})
        if stats_data:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Documenti Unici", stats_data.get("total_documents", 0))
            with col2:
                st.metric("Chunk Totali", stats_data.get("total_chunks", 0))
            with col3:
                st.metric("Dimensione Media Chunk", f"{stats_data.get('avg_chunk_size', 0)} bytes")
            with col4:
                total_size_mb = stats_data.get("total_size_bytes", 0) / (1024 * 1024)
                st.metric("Dimensione Totale", f"{total_size_mb:.1f} MB")

        # File types breakdown
        if stats_data.get("file_types"):
            st.subheader("📊 Tipi di File")
            file_types = stats_data["file_types"]
            fig = px.pie(
                values=list(file_types.values()), names=list(file_types.keys()), title="Distribuzione Tipi di File"
            )
            st.plotly_chart(fig, use_container_width=True)

        # Documents table
        st.subheader("📄 Lista Documenti")
        unique_sources = exploration_data.get("unique_sources", [])

        if unique_sources:
            # Create a DataFrame for better display
            docs_df = pd.DataFrame(
                [
                    {
                        "Nome File": doc["name"],
                        "Tipo": doc["file_type"],
                        "Chunk": doc["chunk_count"],
                        "Pagine": doc["page_count"] if doc["page_count"] else "N/A",
                        "Dimensione": f"{doc['total_size'] / 1024:.1f} KB" if doc["total_size"] > 0 else "N/A",
                        "Indicizzato": doc["indexed_at"][:19] if doc["indexed_at"] != "Unknown" else "Unknown",
                        "Analisi": "✅" if doc["has_analysis"] else "❌",
                    }
                    for doc in unique_sources
                ]
            )

            st.dataframe(
                docs_df,
                use_container_width=True,
                column_config={
                    "Nome File": st.column_config.TextColumn("Nome File", width="medium"),
                    "Tipo": st.column_config.TextColumn("Tipo", width="small"),
                    "Chunk": st.column_config.NumberColumn("Chunk", width="small"),
                    "Pagine": st.column_config.TextColumn("Pagine", width="small"),
                    "Dimensione": st.column_config.TextColumn("Dimensione", width="small"),
                    "Indicizzato": st.column_config.DatetimeColumn("Indicizzato", width="medium"),
                    "Analisi": st.column_config.TextColumn("Analisi", width="small"),
                },
            )

            # Document actions
            st.subheader("🛠️ Azioni sui Documenti")
            selected_doc = st.selectbox(
                "Seleziona documento per azioni dettagliate:",
                options=[doc["name"] for doc in unique_sources],
                help="Scegli un documento per vedere i dettagli o eliminarlo",
            )

            if selected_doc:
                selected_doc_info = next((doc for doc in unique_sources if doc["name"] == selected_doc), None)
                if selected_doc_info:
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        if st.button("👁️ Visualizza Chunk", key="view_chunks"):
                            st.session_state.explorer_selected_doc = selected_doc
                            st.session_state.explorer_tab = "chunk_details"
                            st.rerun()

                    with col2:
                        if st.button("🗑️ Elimina Documento", key="delete_doc", type="secondary"):
                            if st.button("⚠️ Conferma Eliminazione", key="confirm_delete", type="primary"):
                                with st.spinner(f"Eliminando {selected_doc}..."):
                                    if rag_engine.delete_document_by_source(selected_doc):
                                        st.success(f"✅ Documento '{selected_doc}' eliminato con successo")
                                        st.rerun()
                                    else:
                                        st.error("❌ Errore durante l'eliminazione")

                    with col3:
                        if selected_doc_info.get("pdf_path") and Path(selected_doc_info["pdf_path"]).exists():
                            if st.button("📄 Visualizza PDF", key="view_pdf"):
                                # Converti il path in assoluto se è relativo
                                pdf_path = Path(selected_doc_info["pdf_path"])
                                if not pdf_path.is_absolute():
                                    pdf_path = Path.cwd() / pdf_path
                                st.session_state.pdf_to_view_explorer = {
                                    "path": str(pdf_path),
                                    "page": 1,
                                    "source_name": selected_doc,
                                }
                                st.rerun()
        else:
            st.info("Nessun documento trovato nel database.")

    with tab2:
        st.subheader("🔍 Ricerca Semantica nel Database")

        search_query = st.text_input(
            "Cerca contenuti nel database:",
            placeholder="es., ricavi 2024, rischi aziendali, budget forecast",
            help="Usa la ricerca semantica per trovare contenuti simili",
        )

        col1, col2 = st.columns([1, 3])
        with col1:
            search_limit = st.slider("Numero di risultati", min_value=5, max_value=50, value=10)

        if st.button("🔍 Cerca", disabled=not search_query):
            with st.spinner("Cercando nel database..."):
                search_results = rag_engine.search_in_database(search_query, limit=search_limit)

            if search_results:
                st.success(f"✅ Trovati {len(search_results)} risultati")

                for i, result in enumerate(search_results, 1):
                    with st.expander(f"Risultato {i}: {result['source']} (Score: {result['score']:.3f})"):
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            st.markdown(f"**Fonte:** {result['source']}")
                            if result["page"]:
                                st.markdown(f"**Pagina:** {result['page']}")
                            st.markdown(f"**Rilevanza:** {result['score']:.3f}")
                        with col2:
                            st.metric("Score", f"{result['score']:.3f}")

                        st.markdown("**Contenuto:**")
                        st.text(result["text"])
            else:
                st.warning("🔍 Nessun risultato trovato per la ricerca specificata")

    with tab3:
        st.subheader("📄 Dettagli Chunk per Documento")

        # Check if we have a selected document from the overview tab
        if hasattr(st.session_state, "explorer_selected_doc") and hasattr(st.session_state, "explorer_tab"):
            if st.session_state.explorer_tab == "chunk_details":
                selected_doc_for_chunks = st.session_state.explorer_selected_doc
                # Clear the session state
                del st.session_state.explorer_selected_doc
                del st.session_state.explorer_tab
            else:
                selected_doc_for_chunks = None
        else:
            selected_doc_for_chunks = None

        # Get unique sources for selection
        exploration_data = rag_engine.explore_database(limit=10)  # Quick call to get sources
        unique_sources = exploration_data.get("unique_sources", [])

        if unique_sources:
            doc_names = [doc["name"] for doc in unique_sources]
            default_index = 0

            # If we have a pre-selected document, set it as default
            if selected_doc_for_chunks and selected_doc_for_chunks in doc_names:
                default_index = doc_names.index(selected_doc_for_chunks)

            selected_doc_chunks = st.selectbox(
                "Seleziona documento per vedere i chunk:",
                options=doc_names,
                index=default_index,
                help="Visualizza tutti i chunk (blocchi) di testo per il documento selezionato",
            )

            if st.button("📋 Carica Chunk", key="load_chunks"):
                with st.spinner(f"Caricando chunk per {selected_doc_chunks}..."):
                    chunks = rag_engine.get_document_chunks(selected_doc_chunks)

                if chunks:
                    st.success(f"✅ Trovati {len(chunks)} chunk per '{selected_doc_chunks}'")

                    # Display chunks
                    for i, chunk in enumerate(chunks, 1):
                        with st.expander(f"Chunk {i}" + (f" (Pagina {chunk['page']})" if chunk["page"] else "")):
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                st.markdown(f"**ID:** {chunk['id']}")
                                if chunk["page"]:
                                    st.markdown(f"**Pagina:** {chunk['page']}")
                            with col2:
                                st.metric("Dimensione", f"{len(chunk['text'])} caratteri")

                            st.markdown("**Contenuto:**")
                            st.text_area(
                                "Testo del chunk:",
                                value=chunk["text"],
                                height=150,
                                key=f"chunk_text_{i}",
                                disabled=True,
                            )
                else:
                    st.warning(f"🔍 Nessun chunk trovato per '{selected_doc_chunks}'")
        else:
            st.info("Nessun documento disponibile per l'analisi dei chunk.")

    with tab4:
        st.subheader("🛠️ Gestione Database")

        st.warning("⚠️ Le operazioni di gestione sono irreversibili. Procedi con cautela.")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Pulizia Database")
            if st.button("🗑️ Elimina Tutti i Documenti", type="secondary"):
                if st.button("⚠️ CONFERMA: Elimina Tutto", type="primary", key="confirm_delete_all"):
                    with st.spinner("Eliminando tutto il database..."):
                        if rag_engine.delete_documents("*"):
                            st.success("✅ Database completamente pulito")
                            # Clear session state
                            if "document_analyses" in st.session_state:
                                del st.session_state.document_analyses
                            if "pdf_to_view" in st.session_state:
                                del st.session_state.pdf_to_view
                            st.rerun()
                        else:
                            st.error("❌ Errore durante la pulizia del database")

        with col2:
            st.markdown("### Statistiche Avanzate")
            if st.button("📊 Aggiorna Statistiche", key="refresh_stats"):
                st.rerun()

            # Display collection info
            collection_info = stats
            if collection_info:
                st.json(
                    {
                        "Collezione": collection_info.get("collection_name"),
                        "Vettori": collection_info.get("total_vectors"),
                        "Dimensioni": collection_info.get("vector_dimension"),
                        "Metrica": collection_info.get("distance_metric"),
                    }
                )

    # PDF Viewer Section (similar to RAG Documents page)
    if hasattr(st.session_state, "pdf_to_view_explorer") and st.session_state.pdf_to_view_explorer:
        pdf_info = st.session_state.pdf_to_view_explorer

        col_header, col_close = st.columns([4, 1])
        with col_header:
            st.subheader(f"📄 {pdf_info['source_name']} - Pagina {pdf_info['page']}")
        with col_close:
            if st.button("❌ Chiudi PDF", key="close_pdf_explorer"):
                del st.session_state.pdf_to_view_explorer
                st.rerun()

        # Display PDF
        try:
            pdf_path = Path(pdf_info["path"])

            if pdf_path.exists():
                # Read PDF file
                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()

                # Show document header
                st.markdown(f"**📍 Documento: {pdf_info['source_name']} - Pagina {pdf_info['page']}**")

                # Create download button
                import base64

                b64 = base64.b64encode(pdf_bytes).decode()
                href = f'<a href="data:application/pdf;base64,{b64}" download="{pdf_info["source_name"]}" style="background-color: #ff4b4b; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 10px 0;">📥 Scarica {pdf_info["source_name"]}</a>'
                st.markdown(href, unsafe_allow_html=True)

                # Show embedded PDF directly in browser
                try:
                    pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
                    pdf_display = f"""
                    <iframe
                        src="data:application/pdf;base64,{pdf_base64}#page={pdf_info["page"]}"
                        width="100%"
                        height="600px"
                        style="border: none;">
                        Il tuo browser non supporta la visualizzazione PDF integrata.
                    </iframe>
                    """
                    st.markdown("### 📖 Anteprima PDF:")
                    st.markdown(pdf_display, unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"❌ Errore visualizzazione PDF embedded: {str(e)}")
                    st.warning("⚠️ Visualizzazione PDF integrata non disponibile. Usa il pulsante di download.")

                # Navigation controls
                col1, col2, col3 = st.columns([1, 2, 1])
                with col1:
                    if st.button("⬅️ Pagina Precedente", disabled=pdf_info["page"] <= 1):
                        st.session_state.pdf_to_view_explorer["page"] = max(1, pdf_info["page"] - 1)
                        st.rerun()
                with col2:
                    st.write(f"Pagina {pdf_info['page']}")
                with col3:
                    if st.button("➡️ Pagina Successiva"):
                        st.session_state.pdf_to_view_explorer["page"] = pdf_info["page"] + 1
                        st.rerun()

            else:
                st.error(f"❌ File PDF non trovato: {pdf_path}")
                del st.session_state.pdf_to_view_explorer
                st.rerun()

        except Exception as e:
            st.error(f"❌ Errore nel caricamento PDF: {str(e)}")
            del st.session_state.pdf_to_view_explorer
            st.rerun()


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
            if st.session_state.services["rag_engine"].delete_documents("*"):
                st.success("✅ Database vettoriale pulito")
                # Clear document analyses from session
                if "document_analyses" in st.session_state:
                    del st.session_state.document_analyses
                # Also clear PDF viewer
                if "pdf_to_view" in st.session_state:
                    del st.session_state.pdf_to_view
                st.rerun()
            else:
                st.error("❌ Fallita pulizia database vettoriale")

    with col2:
        if st.button(
            "Rimuovi Path Temporanei", type="secondary", help="Pulisce i percorsi temporanei dai metadata esistenti"
        ):
            if st.session_state.services["rag_engine"].clean_metadata_paths():
                st.success("✅ Percorsi temporanei rimossi")
                # Clear analyses since documents were re-indexed
                if "document_analyses" in st.session_state:
                    del st.session_state.document_analyses
                st.rerun()
            else:
                st.error("❌ Errore nella pulizia dei percorsi")

    with col3:
        if st.button("Resetta Sessione", type="secondary"):
            st.session_state.csv_analysis = None
            st.session_state.rag_response = None
            if "document_analyses" in st.session_state:
                del st.session_state.document_analyses
            if "pdf_to_view" in st.session_state:
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
                if st.button(
                    "🗑️ Elimina Tutti i PDF",
                    type="secondary",
                    help="Rimuove tutti i PDF salvati (NON influenza l'indicizzazione)",
                ):
                    try:
                        for pdf in pdf_files:
                            pdf.unlink()
                        st.success(f"✅ Eliminati {len(pdf_files)} PDF")
                        if "pdf_to_view" in st.session_state:
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
