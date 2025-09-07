"""Advanced Document Preview with content extraction and thumbnails."""

import streamlit as st
import os
from pathlib import Path
import base64
from datetime import datetime
import json

# Import our services
try:
    from src.application.services.document_preview import DocumentPreviewService
    SERVICES_AVAILABLE = True
except ImportError:
    SERVICES_AVAILABLE = False
    st.error("Document preview services not available.")

def display_file_info(file_info):
    """Display file information in a nice format."""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("File Size", file_info['size_formatted'])
    
    with col2:
        st.metric("File Type", file_info['extension'].upper())
    
    with col3:
        modified_date = datetime.fromisoformat(file_info['modified']).strftime('%Y-%m-%d %H:%M')
        st.metric("Modified", modified_date)

def display_thumbnails(thumbnails):
    """Display document thumbnails."""
    if not thumbnails:
        st.info("No thumbnails available for this document type.")
        return
    
    st.subheader("📄 Document Pages")
    
    # Display thumbnails in a grid
    cols = st.columns(min(len(thumbnails), 4))
    
    for i, thumb in enumerate(thumbnails):
        col_idx = i % 4
        
        with cols[col_idx]:
            st.markdown(f"**Page {thumb['page']}**")
            st.image(thumb['thumbnail'], use_column_width=True)

def display_statistics(statistics):
    """Display document statistics."""
    st.subheader("📊 Document Statistics")
    
    if 'error' in statistics:
        st.error(f"Error: {statistics['error']}")
        return
    
    # Create expandable sections for different types of statistics
    if 'total_pages' in statistics:
        # PDF statistics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Pages", statistics['total_pages'])
        
        with col2:
            st.metric("Previewed Pages", statistics.get('previewed_pages', 0))
        
        with col3:
            has_text = "✅" if statistics.get('has_text', False) else "❌"
            st.metric("Has Text Content", has_text)
        
        # Metadata
        if 'metadata' in statistics and statistics['metadata']:
            with st.expander("📋 Document Metadata"):
                for key, value in statistics['metadata'].items():
                    if value:
                        st.write(f"**{key.replace('_', ' ').title()}**: {value}")
    
    elif 'total_sheets' in statistics:
        # Excel statistics
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Total Sheets", statistics['total_sheets'])
        
        with col2:
            sheet_names = statistics.get('sheet_names', [])
            st.metric("Available Sheets", len(sheet_names))
        
        if sheet_names:
            st.write("**Sheet Names:**")
            for sheet in sheet_names:
                st.write(f"• {sheet}")
        
        # Individual sheet statistics
        for key, value in statistics.items():
            if key.startswith('sheet_') and isinstance(value, dict):
                sheet_name = key.replace('sheet_', '')
                with st.expander(f"📊 {sheet_name} Details"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Rows", value.get('rows', 0))
                        st.metric("Numeric Columns", value.get('numeric_columns', 0))
                    with col2:
                        st.metric("Columns", value.get('columns', 0))
                        st.metric("Text Columns", value.get('text_columns', 0))
    
    elif 'total_rows' in statistics:
        # CSV statistics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Rows", statistics['total_rows'])
        
        with col2:
            st.metric("Total Columns", statistics['total_columns'])
        
        with col3:
            st.metric("Numeric Columns", statistics.get('numeric_columns', 0))
        
        with col4:
            st.metric("Text Columns", statistics.get('text_columns', 0))
        
        # Null values
        null_values = statistics.get('null_values', {})
        if null_values:
            with st.expander("🔍 Data Quality - Null Values"):
                null_df = pd.DataFrame(list(null_values.items()), columns=['Column', 'Null Count'])
                st.dataframe(null_df, use_container_width=True)
    
    elif 'format' in statistics:
        # Image statistics  
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Format", statistics['format'])
        
        with col2:
            st.metric("Mode", statistics['mode'])
        
        with col3:
            st.metric("Size", statistics['size'])

def display_key_metrics(key_metrics):
    """Display extracted key metrics."""
    if not key_metrics:
        st.info("No financial metrics automatically detected.")
        return
    
    st.subheader("💰 Extracted Financial Metrics")
    
    # Simple metrics (string values)
    simple_metrics = {k: v for k, v in key_metrics.items() if isinstance(v, str)}
    
    if simple_metrics:
        cols = st.columns(min(len(simple_metrics), 3))
        
        for i, (metric, value) in enumerate(simple_metrics.items()):
            col_idx = i % 3
            with cols[col_idx]:
                metric_name = metric.replace('_', ' ').title()
                st.metric(metric_name, value)
    
    # Complex metrics (with statistics)
    complex_metrics = {k: v for k, v in key_metrics.items() if isinstance(v, dict)}
    
    if complex_metrics:
        with st.expander("📊 Detailed Metrics Statistics"):
            for metric, stats in complex_metrics.items():
                st.write(f"**{metric.replace('_', ' ').title()}**")
                
                if isinstance(stats, dict):
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        if 'min' in stats and stats['min'] is not None:
                            st.write(f"Min: {stats['min']:,.2f}")
                    
                    with col2:
                        if 'max' in stats and stats['max'] is not None:
                            st.write(f"Max: {stats['max']:,.2f}")
                    
                    with col3:
                        if 'mean' in stats and stats['mean'] is not None:
                            st.write(f"Avg: {stats['mean']:,.2f}")
                    
                    with col4:
                        if 'count' in stats:
                            st.write(f"Count: {stats['count']}")
                
                st.write("---")

def main():
    st.set_page_config(page_title="Document Preview", page_icon="🔍", layout="wide")
    
    st.title("🔍 Advanced Document Preview")
    st.markdown("Upload or select documents for detailed preview and content extraction.")
    st.markdown("---")
    
    if not SERVICES_AVAILABLE:
        st.stop()
    
    # Initialize preview service
    if 'preview_service' not in st.session_state:
        st.session_state.preview_service = DocumentPreviewService()
    
    preview_service = st.session_state.preview_service
    
    # File selection method
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📁 Select Document Source")
        
        source_method = st.radio(
            "Choose method:",
            ["Upload File", "Select from Documents Folder"],
            horizontal=True
        )
    
    with col2:
        st.subheader("⚙️ Preview Settings")
        
        max_pages = st.slider("Max pages to preview", 1, 10, 3)
        thumbnail_size = st.selectbox(
            "Thumbnail size",
            [("Small", (150, 150)), ("Medium", (200, 200)), ("Large", (300, 300))],
            index=1,
            format_func=lambda x: x[0]
        )[1]
    
    selected_file = None
    
    if source_method == "Upload File":
        st.subheader("📤 Upload Document")
        
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=['pdf', 'xlsx', 'xls', 'csv', 'txt', 'md', 'json', 'png', 'jpg', 'jpeg'],
            help="Supported formats: PDF, Excel, CSV, Text, Markdown, JSON, Images"
        )
        
        if uploaded_file is not None:
            # Save uploaded file temporarily
            temp_dir = Path("temp_uploads")
            temp_dir.mkdir(exist_ok=True)
            
            temp_path = temp_dir / uploaded_file.name
            
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            selected_file = temp_path
    
    else:
        st.subheader("📂 Select from Documents")
        
        # List available documents
        docs_folder = Path("documents")
        
        if docs_folder.exists():
            doc_files = []
            for ext in ['*.pdf', '*.xlsx', '*.xls', '*.csv', '*.txt', '*.md', '*.json']:
                doc_files.extend(docs_folder.glob(ext))
            
            if doc_files:
                selected_path = st.selectbox(
                    "Available documents:",
                    doc_files,
                    format_func=lambda x: x.name
                )
                
                selected_file = selected_path
            else:
                st.info("No documents found in the documents folder.")
        else:
            st.info("Documents folder not found. Please create a 'documents' folder and add some files.")
    
    # Generate preview if file is selected
    if selected_file:
        st.markdown("---")
        
        # File path display
        st.info(f"📄 **Selected file**: {selected_file.name}")
        
        # Generate preview with spinner
        with st.spinner("Generating document preview..."):
            try:
                preview_data = preview_service.generate_preview(
                    str(selected_file),
                    max_pages=max_pages,
                    thumbnail_size=thumbnail_size
                )
                
                if preview_data.get('status') == 'error':
                    st.error(f"Error generating preview: {preview_data.get('error')}")
                    return
                
                # Display results
                st.success("✅ Preview generated successfully!")
                
                # Create tabs for different sections
                tabs = st.tabs(["📋 File Info", "👁️ Content Preview", "🖼️ Thumbnails", "📊 Statistics", "💰 Key Metrics"])
                
                with tabs[0]:
                    st.subheader("📋 File Information")
                    display_file_info(preview_data['file_info'])
                    
                    # Additional file info in expandable section
                    with st.expander("🔍 Detailed File Info"):
                        file_info = preview_data['file_info']
                        st.json(file_info)
                
                with tabs[1]:
                    st.subheader("👁️ Content Preview")
                    
                    content_preview = preview_data.get('content_preview', '')
                    
                    if content_preview and content_preview != 'No text content found':
                        # Display content in a nice text area
                        st.text_area(
                            "Document Content (Preview)",
                            value=content_preview,
                            height=400,
                            disabled=True
                        )
                        
                        # Word count
                        word_count = len(content_preview.split())
                        char_count = len(content_preview)
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Words (Preview)", f"{word_count:,}")
                        with col2:
                            st.metric("Characters (Preview)", f"{char_count:,}")
                    else:
                        st.info("No text content available for preview.")
                
                with tabs[2]:
                    thumbnails = preview_data.get('thumbnails', [])
                    display_thumbnails(thumbnails)
                
                with tabs[3]:
                    statistics = preview_data.get('statistics', {})
                    display_statistics(statistics)
                
                with tabs[4]:
                    key_metrics = preview_data.get('key_metrics', {})
                    display_key_metrics(key_metrics)
                
                # Action buttons
                st.markdown("---")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("🔄 Regenerate Preview"):
                        st.rerun()
                
                with col2:
                    # Download preview data as JSON
                    preview_json = json.dumps(preview_data, indent=2, default=str)
                    st.download_button(
                        label="📥 Download Preview Data",
                        data=preview_json,
                        file_name=f"preview_{selected_file.stem}.json",
                        mime="application/json"
                    )
                
                with col3:
                    if st.button("🗑️ Clear Cache"):
                        # Clear cached preview
                        try:
                            cache_file = preview_service.cache_dir / f"{preview_data['file_info']['hash']}.json"
                            if cache_file.exists():
                                cache_file.unlink()
                                st.success("Cache cleared!")
                        except Exception as e:
                            st.error(f"Error clearing cache: {e}")
                
                # Technical details in expander
                with st.expander("🔧 Technical Details"):
                    st.write("**Processing Info:**")
                    st.write(f"• File hash: {preview_data['file_info']['hash']}")
                    st.write(f"• Processing time: < 1 second")
                    st.write(f"• Thumbnail size: {thumbnail_size[0]}×{thumbnail_size[1]}px")
                    st.write(f"• Max pages processed: {max_pages}")
                    
                    # Show full preview data
                    if st.checkbox("Show full preview data (JSON)"):
                        st.json(preview_data)
                
            except Exception as e:
                st.error(f"Unexpected error: {str(e)}")
                st.exception(e)
    
    else:
        # Welcome message when no file is selected
        st.markdown("""
        ## 🎯 How to Use Document Preview
        
        1. **Upload a file** or **select from documents folder**
        2. **Adjust preview settings** (max pages, thumbnail size)  
        3. **View the generated preview** with:
           - File information and metadata
           - Content extraction and text preview
           - Page thumbnails (for supported formats)
           - Document statistics and metrics
           - Automatically extracted financial data
        
        ### 📚 Supported File Types
        
        | Type | Extensions | Features |
        |------|-----------|----------|
        | **PDF** | `.pdf` | Text extraction, page thumbnails, metadata |
        | **Excel** | `.xlsx`, `.xls` | Sheet preview, data statistics, metrics extraction |
        | **CSV** | `.csv` | Data preview, column analysis, null value detection |
        | **Text** | `.txt`, `.md` | Full content preview, metrics detection |
        | **Images** | `.png`, `.jpg`, `.jpeg` | Thumbnails, image properties |
        | **JSON** | `.json` | Structured data preview, metrics extraction |
        
        ### 🚀 Advanced Features
        
        - **Intelligent Content Extraction**: Automatically detects and extracts financial metrics
        - **Multi-format Support**: Handles various document types with format-specific optimizations
        - **Caching System**: Speeds up repeated previews of the same document
        - **Thumbnail Generation**: Visual previews for PDFs and images
        - **Data Quality Analysis**: Identifies missing data and quality issues
        """)
    
    # Footer
    st.markdown("---")
    st.caption(f"Document Preview Service - Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()