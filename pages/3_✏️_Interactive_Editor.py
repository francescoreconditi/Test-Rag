"""Interactive editor for financial metrics with real-time validation."""

import streamlit as st
import pandas as pd
from datetime import datetime
import json

# Import our services
try:
    from src.application.services.interactive_editor import InteractiveEditingService
    SERVICES_AVAILABLE = True
except ImportError:
    SERVICES_AVAILABLE = False
    st.error("Interactive editing services not available.")

def display_metric_editor(session_id, metric_name, metric_data, editor_service):
    """Display an individual metric editor."""
    col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
    
    with col1:
        st.write(f"**{metric_name.replace('_', ' ').title()}**")
        if metric_data.get('canonical_name'):
            st.caption(f"📋 {metric_data['canonical_name']}")
    
    with col2:
        current_value = metric_data.get('value')
        
        if metric_data.get('editable', True) and not metric_data.get('calculated', False):
            # Editable field
            if metric_data.get('unit') == 'percentage':
                new_value = st.number_input(
                    f"Value",
                    value=float(current_value) if current_value is not None else 0.0,
                    step=0.1,
                    format="%.2f",
                    key=f"edit_{metric_name}"
                )
                unit_display = "%"
            elif metric_data.get('unit') == 'days':
                new_value = st.number_input(
                    f"Value",
                    value=int(current_value) if current_value is not None else 0,
                    step=1,
                    key=f"edit_{metric_name}"
                )
                unit_display = "days"
            elif metric_data.get('unit') == 'count':
                new_value = st.number_input(
                    f"Value",
                    value=int(current_value) if current_value is not None else 0,
                    step=1,
                    key=f"edit_{metric_name}"
                )
                unit_display = ""
            else:
                new_value = st.number_input(
                    f"Value",
                    value=float(current_value) if current_value is not None else 0.0,
                    step=1000.0,
                    format="%.0f",
                    key=f"edit_{metric_name}"
                )
                unit_display = "€" if metric_data.get('unit') == 'currency' else ""
            
            # Update button
            if st.button(f"💾", key=f"save_{metric_name}", help="Save changes"):
                if new_value != current_value:
                    with st.spinner("Updating..."):
                        result = editor_service.update_metric_value(
                            session_id, metric_name, new_value,
                            user_comment=f"Updated via interactive editor"
                        )
                        
                        if result['success']:
                            st.success(f"✅ {metric_name} updated!")
                            st.rerun()
                        else:
                            st.error(f"❌ Update failed: {result.get('error', 'Unknown error')}")
                            
                            # Show validation errors if any
                            if 'validation_errors' in result:
                                for error in result['validation_errors']:
                                    st.warning(f"⚠️ {error['message']}")
                            
                            # Option to override validation
                            if result.get('requires_override'):
                                if st.button(f"Force Update", key=f"force_{metric_name}"):
                                    result = editor_service.update_metric_value(
                                        session_id, metric_name, new_value,
                                        validation_override=True
                                    )
                                    if result['success']:
                                        st.success(f"✅ {metric_name} force updated!")
                                        st.rerun()
        else:
            # Read-only field
            if current_value is not None:
                formatted_value = f"{current_value:,.2f}" if isinstance(current_value, (int, float)) else str(current_value)
                st.text_input(
                    f"Value",
                    value=formatted_value,
                    disabled=True,
                    key=f"readonly_{metric_name}"
                )
                unit_display = metric_data.get('unit', '')
            else:
                st.text_input(
                    f"Value",
                    value="Not available",
                    disabled=True,
                    key=f"readonly_{metric_name}"
                )
                unit_display = ""
    
    with col3:
        # Unit display
        st.caption(unit_display)
        
        # Confidence indicator
        confidence = metric_data.get('confidence', 0.5)
        confidence_color = "🟢" if confidence >= 0.8 else "🟡" if confidence >= 0.6 else "🔴"
        st.caption(f"{confidence_color} {confidence*100:.0f}%")
    
    with col4:
        # Status indicator
        status = metric_data.get('validation_status', 'unknown')
        status_colors = {
            'valid': '🟢',
            'warning': '🟡', 
            'error': '🔴',
            'pending': '⚪'
        }
        
        status_icon = status_colors.get(status, '❓')
        st.caption(f"{status_icon} {status}")
        
        # Additional info
        if metric_data.get('calculated'):
            st.caption("🧮 Calculated")
        elif metric_data.get('added_by_user'):
            st.caption("👤 User Added")

def display_suggestions(suggestions, session_id, editor_service):
    """Display automatic correction suggestions."""
    if not suggestions:
        st.info("No automatic suggestions available.")
        return
    
    st.subheader("💡 Suggested Corrections")
    
    selected_suggestions = []
    
    for i, suggestion in enumerate(suggestions):
        col1, col2, col3, col4, col5 = st.columns([1, 2, 2, 2, 1])
        
        with col1:
            if st.checkbox("", key=f"suggest_{i}"):
                selected_suggestions.append(i)
        
        with col2:
            st.write(f"**{suggestion['metric']}**")
        
        with col3:
            current_val = suggestion['current_value']
            if current_val is not None:
                st.write(f"Current: {current_val}")
            else:
                st.write("Current: *Not set*")
        
        with col4:
            suggested_val = suggestion['suggested_value']
            st.write(f"Suggested: **{suggested_val}**")
        
        with col5:
            confidence = suggestion.get('confidence', 0.5)
            st.write(f"{confidence*100:.0f}%")
        
        # Reason
        st.caption(f"💭 {suggestion['reason']}")
        
        st.markdown("---")
    
    # Apply suggestions
    if selected_suggestions:
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("✅ Apply Selected Suggestions"):
                with st.spinner("Applying suggestions..."):
                    result = editor_service.apply_suggestions(session_id, selected_suggestions)
                    
                    if result['applied_count'] > 0:
                        st.success(f"✅ Applied {result['applied_count']} suggestions!")
                        
                        for metric in result['applied_metrics']:
                            st.success(f"• {metric} updated")
                    
                    if result['failed_count'] > 0:
                        st.error(f"❌ {result['failed_count']} suggestions failed:")
                        for reason in result['failed_reasons']:
                            st.error(f"• {reason}")
                    
                    st.rerun()
        
        with col2:
            st.caption(f"{len(selected_suggestions)} suggestions selected")

def display_edit_history(history):
    """Display edit history."""
    if not history:
        st.info("No edits made yet.")
        return
    
    st.subheader("📝 Edit History")
    
    # Convert to DataFrame for better display
    history_data = []
    
    for operation in reversed(history):  # Show most recent first
        history_data.append({
            'Timestamp': datetime.fromisoformat(operation['timestamp']).strftime('%H:%M:%S'),
            'Operation': operation['operation_type'].title(),
            'Metric': operation['target_metric'],
            'Old Value': operation.get('old_value', 'N/A'),
            'New Value': operation.get('new_value', 'N/A'),
            'Comment': operation.get('user_comment', ''),
            'ID': operation['operation_id']
        })
    
    if history_data:
        df = pd.DataFrame(history_data)
        
        # Display as a table
        st.dataframe(df.drop('ID', axis=1), use_container_width=True)
        
        # Undo functionality
        with st.expander("🔄 Undo Operations"):
            operation_options = [(op['ID'], f"{op['Timestamp']} - {op['Operation']} {op['Metric']}") 
                               for op in history_data]
            
            if operation_options:
                selected_op = st.selectbox(
                    "Select operation to undo:",
                    operation_options,
                    format_func=lambda x: x[1]
                )
                
                if st.button("↶ Undo Selected Operation"):
                    # This would call the undo functionality
                    st.warning("Undo functionality would be implemented here")

def main():
    st.set_page_config(page_title="Interactive Editor", page_icon="✏️", layout="wide")
    
    st.title("✏️ Interactive Metrics Editor")
    st.markdown("Edit financial metrics with real-time validation and automatic suggestions.")
    st.markdown("---")
    
    if not SERVICES_AVAILABLE:
        st.stop()
    
    # Initialize editing service
    if 'editor_service' not in st.session_state:
        st.session_state.editor_service = InteractiveEditingService()
    
    editor_service = st.session_state.editor_service
    
    # Session management
    st.sidebar.header("📁 Session Management")
    
    # Create or select session
    if 'current_session_id' not in st.session_state:
        st.session_state.current_session_id = None
    
    # Start new session
    if st.sidebar.button("🆕 Start New Session"):
        session_id = editor_service.start_editing_session(
            document_path="sample_document.pdf",
            user_id="user_001"
        )
        st.session_state.current_session_id = session_id
        st.sidebar.success(f"Started session: {session_id}")
    
    # Current session info
    if st.session_state.current_session_id:
        st.sidebar.success(f"Active Session: {st.session_state.current_session_id[:12]}...")
        
        # Session actions
        if st.sidebar.button("💾 Save Session"):
            st.sidebar.info("Session auto-saved")
        
        if st.sidebar.button("🔄 Reload Session"):
            st.rerun()
    else:
        st.sidebar.warning("No active session")
        st.info("Please start a new session to begin editing.")
        return
    
    session_id = st.session_state.current_session_id
    
    # Get editable data
    try:
        editable_data = editor_service.get_editable_data(session_id)
    except Exception as e:
        st.error(f"Error loading session data: {e}")
        return
    
    # Main tabs
    tabs = st.tabs(["📊 Edit Metrics", "💡 Suggestions", "➕ Add New", "📝 History", "📋 Validation"])
    
    with tabs[0]:
        st.subheader("📊 Financial Metrics Editor")
        
        data = editable_data['data']
        
        if not data:
            st.info("No metrics available for editing.")
            return
        
        # Group metrics by category
        categories = {}
        for metric_name, metric_data in data.items():
            # Try to categorize based on metric name
            if any(x in metric_name.lower() for x in ['ricavi', 'ebitda', 'utile', 'margine']):
                category = "Profitability"
            elif any(x in metric_name.lower() for x in ['dso', 'dpo', 'rotazione', 'giorni']):
                category = "Efficiency" 
            elif any(x in metric_name.lower() for x in ['attivo', 'passivo', 'patrimonio', 'debito', 'cassa']):
                category = "Balance Sheet"
            elif any(x in metric_name.lower() for x in ['dipendenti', 'turnover', 'formazione']):
                category = "Human Resources"
            else:
                category = "Other"
            
            if category not in categories:
                categories[category] = {}
            categories[category][metric_name] = metric_data
        
        # Display metrics by category
        for category, metrics in categories.items():
            with st.expander(f"📁 {category} ({len(metrics)} metrics)", expanded=True):
                for metric_name, metric_data in metrics.items():
                    display_metric_editor(session_id, metric_name, metric_data, editor_service)
                    st.markdown("---")
    
    with tabs[1]:
        # Suggestions tab
        with st.spinner("Generating suggestions..."):
            try:
                suggestions = editor_service.suggest_corrections(session_id)
                display_suggestions(suggestions, session_id, editor_service)
            except Exception as e:
                st.error(f"Error generating suggestions: {e}")
    
    with tabs[2]:
        # Add new metric
        st.subheader("➕ Add New Metric")
        
        # Get available metrics from ontology
        available_metrics = editable_data.get('available_metrics', [])
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Metric selection
            if available_metrics:
                metric_options = [(m['key'], f"{m['name']} ({m['category']})") for m in available_metrics]
                
                selected_metric = st.selectbox(
                    "Select metric to add:",
                    options=[None] + metric_options,
                    format_func=lambda x: "Choose..." if x is None else x[1]
                )
                
                if selected_metric:
                    metric_key = selected_metric[0]
                    metric_info = next(m for m in available_metrics if m['key'] == metric_key)
                    
                    st.info(f"**Unit**: {metric_info['unit']}")
                    st.info(f"**Category**: {metric_info['category']} > {metric_info['subcategory']}")
                    
                    if metric_info.get('calculable'):
                        st.warning("This metric can be automatically calculated.")
            else:
                metric_key = st.text_input("Metric key:", placeholder="e.g., new_metric_name")
                metric_info = {'unit': 'numeric'}
        
        with col2:
            # Value input
            if available_metrics and selected_metric:
                unit = metric_info['unit']
                
                if unit == 'percentage':
                    new_value = st.number_input("Value (%)", step=0.1, format="%.2f")
                elif unit == 'days':
                    new_value = st.number_input("Value (days)", step=1)
                elif unit == 'count':
                    new_value = st.number_input("Value", step=1)
                else:
                    new_value = st.number_input("Value", step=1000.0, format="%.0f")
            else:
                new_value = st.number_input("Value", step=1.0)
            
            # Optional fields
            source_ref = st.text_input("Source reference (optional)", 
                                     placeholder="e.g., document.pdf|p.5|row:New Metric")
            
            period = st.text_input("Period", value="FY2024")
        
        # Add button
        if st.button("➕ Add Metric"):
            if available_metrics and selected_metric:
                metric_key = selected_metric[0]
            elif not available_metrics and metric_key:
                pass  # Use manual input
            else:
                st.error("Please select or enter a metric name.")
                return
            
            with st.spinner("Adding metric..."):
                try:
                    result = editor_service.add_new_metric(
                        session_id=session_id,
                        metric_name=metric_key,
                        value=new_value,
                        source_ref=source_ref or None,
                        period=period
                    )
                    
                    if result['success']:
                        st.success(f"✅ Added {result['canonical_name']}!")
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to add metric: {result.get('error')}")
                        
                except Exception as e:
                    st.error(f"Error adding metric: {e}")
    
    with tabs[3]:
        # Edit history
        try:
            history = editor_service.get_edit_history(session_id)
            display_edit_history(history)
        except Exception as e:
            st.error(f"Error loading history: {e}")
    
    with tabs[4]:
        # Validation rules
        st.subheader("📋 Validation Rules")
        
        validation_rules = editable_data.get('validation_rules', {})
        
        if validation_rules:
            # Range constraints
            if 'ranges' in validation_rules:
                st.markdown("#### 📏 Range Constraints")
                ranges_df = []
                
                for metric, range_info in validation_rules['ranges'].items():
                    ranges_df.append({
                        'Metric': metric.replace('_', ' ').title(),
                        'Min': range_info.get('min', 'N/A'),
                        'Max': range_info.get('max', 'N/A'),
                        'Unit': range_info.get('unit', '')
                    })
                
                if ranges_df:
                    st.dataframe(pd.DataFrame(ranges_df), use_container_width=True)
            
            # Balance equations
            if 'balance_equations' in validation_rules:
                st.markdown("#### ⚖️ Balance Equations")
                for name, equation in validation_rules['balance_equations'].items():
                    st.code(f"{name}: {equation}")
            
            # Required positive
            if 'required_positive' in validation_rules:
                st.markdown("#### ➕ Must Be Positive")
                positive_metrics = validation_rules['required_positive']
                for metric in positive_metrics:
                    st.write(f"• {metric.replace('_', ' ').title()}")
        else:
            st.info("No validation rules configured.")
    
    # Status bar
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_metrics = len(editable_data.get('data', {}))
        editable_count = sum(1 for m in editable_data.get('data', {}).values() 
                           if m.get('editable', True))
        st.caption(f"📊 {editable_count}/{total_metrics} editable metrics")
    
    with col2:
        history_count = len(editable_data.get('edit_history', []))
        st.caption(f"📝 {history_count} edits made")
    
    with col3:
        st.caption(f"🕒 Last update: {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    main()