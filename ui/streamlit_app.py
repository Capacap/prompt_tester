"""
Prompt Tester Streamlit Interface

A minimal viable web interface for side-by-side comparison of experimental results
and analysis of prompt testing data. Built with mathematical precision and 
algorithmic elegance for optimal user experience.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Import our data layer components
try:
    from components.data_loader import (
        load_runs_data, 
        load_run_results, 
        get_available_filters,
        apply_filters,
        get_comparison_data,
        export_results_to_text
    )
except ImportError as e:
    st.error(f"Import error: {e}")
    st.info("Please ensure you're running this with: streamlit run ui/streamlit_app.py")
    st.stop()

# Configure Streamlit page
st.set_page_config(
    page_title="Prompt Tester Analysis",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    """Main application orchestrator."""
    
    # Header Section
    st.title("Prompt Tester Analysis")
    st.markdown("Side-by-side comparison of experimental prompt results")
    
    # Load runs data
    runs_data = load_runs_data()
    
    if runs_data["error"]:
        st.error(f"Database Error: {runs_data['error']}")
        st.info("Please ensure you have experimental data by running the CLI tool first.")
        return
    
    if not runs_data["runs"]:
        st.warning("No experimental runs found in database.")
        st.info("Run some experiments using the CLI tool to see results here.")
        return
    
    # Sidebar: Run Selection and Controls
    with st.sidebar:
        st.header("Run Selection")
        
        # Run selector
        run_options = []
        for run in runs_data["runs"]:
            success_rate = f"{run['success_rate']:.1%}"
            completed_status = "Complete" if run['is_completed'] else "Running"
            display_name = f"{run['run_started_display']} ({success_rate})"
            run_options.append((display_name, run['run_id']))
        
        selected_run_display, selected_run_id = st.selectbox(
            "Select Run:",
            run_options,
            format_func=lambda x: x[0]
        )
        
        # Load results for selected run
        results_df = load_run_results(selected_run_id)
        
        if results_df.empty:
            st.error("No results found for selected run.")
            return
        
        # Filters Section
        st.subheader("Filters")
        available_filters = get_available_filters(results_df)
        
        # Prompt selection (most important for comparison)
        selected_prompts = st.multiselect(
            "Prompts to Compare:",
            available_filters.get('prompts', []),
            default=available_filters.get('prompts', [])[:3]  # Default to first 3
        )
        
        # Other filters
        selected_test_cases = st.multiselect(
            "Test Cases:",
            available_filters.get('test_cases', []),
            default=[]
        )
        
        selected_models = st.multiselect(
            "Models:",
            available_filters.get('models', []),
            default=[]
        )
        
        selected_statuses = st.multiselect(
            "Status:",
            available_filters.get('statuses', []),
            default=['success']  # Default to successful results
        )
        
        # Text search
        search_query = st.text_input("Search in responses:", "")
        
        # Apply filters
        filtered_df = apply_filters(
            results_df,
            selected_prompts=selected_prompts if selected_prompts else None,
            selected_test_cases=selected_test_cases if selected_test_cases else None,
            selected_models=selected_models if selected_models else None,
            selected_statuses=selected_statuses if selected_statuses else None,
            search_query=search_query
        )
        
        # Filter summary
        st.info(f"Showing {len(filtered_df)} of {len(results_df)} results")
        
        # Clear filters button
        if st.button("Clear All Filters"):
            st.rerun()
    
    # Main content area
    if filtered_df.empty:
        st.warning("No results match current filters. Please adjust your selection.")
        return
    
    # Primary view: Side-by-Side Comparison
    show_comparison_view(filtered_df, selected_prompts)
    
    # Auxiliary features in tabs
    with st.expander("Additional Analysis", expanded=False):
        aux_tab1, aux_tab2 = st.tabs(["Summary", "Data Explorer"])
        
        with aux_tab1:
            show_results_summary(filtered_df)
        
        with aux_tab2:
            show_data_explorer(filtered_df)


def show_results_summary(df: pd.DataFrame):
    """Display results summary with key metrics and insights."""
    st.header("Results Summary")
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        success_count = len(df[df['status'] == 'success'])
        st.metric(
            "Successful Results", 
            success_count,
            delta=f"{success_count/len(df):.1%} success rate"
        )
    
    with col2:
        avg_response_length = df[df['has_response']]['response_length'].mean()
        st.metric(
            "Avg Response Length",
            f"{avg_response_length:.0f}" if pd.notna(avg_response_length) else "N/A",
            delta="characters"
        )
    
    with col3:
        unique_prompts = df['prompt_name'].nunique()
        st.metric("Prompts", unique_prompts)
    
    with col4:
        unique_test_cases = df['test_case_name'].nunique()
        st.metric("Test Cases", unique_test_cases)
    
    # Status distribution
    st.subheader("Status Distribution")
    status_counts = df['status'].value_counts()
    st.bar_chart(status_counts)
    
    # Response length distribution for successful results
    successful_df = df[df['status'] == 'success']
    if not successful_df.empty and len(successful_df) > 1:
        st.subheader("Response Length Distribution")
        # Create histogram using pandas and display with bar_chart
        # Convert intervals to string labels for Streamlit compatibility
        hist_data = pd.cut(successful_df['response_length'], bins=10).value_counts().sort_index()
        hist_data.index = [f"{int(interval.left)}-{int(interval.right)}" for interval in hist_data.index]
        st.bar_chart(hist_data)
    
    # Recent results table
    st.subheader("Recent Results")
    display_columns = ['timestamp', 'prompt_name', 'test_case_name', 'model_display_name', 'status', 'response_length']
    recent_results = df.sort_values('timestamp', ascending=False).head(10)[display_columns]
    st.dataframe(recent_results, width='stretch')


def show_comparison_view(df: pd.DataFrame, selected_prompts: List[str]):
    """Display side-by-side comparison of selected prompts."""
    st.header("Side-by-Side Comparison")
    
    if not selected_prompts:
        st.warning("Select prompts in the sidebar to enable comparison.")
        return
    
    if len(selected_prompts) < 2:
        st.info("Select at least 2 prompts for comparison.")
        return
    
    # Test case selector for detailed comparison
    available_test_cases = sorted(df['test_case_name'].unique())
    selected_test_case = st.selectbox(
        "Test Case:",
        available_test_cases
    )
    
    # Get comparison data
    comparison_data = get_comparison_data(df, selected_prompts, selected_test_case)
    
    if not comparison_data or selected_test_case not in comparison_data:
        st.warning(f"No data available for test case: {selected_test_case}")
        return
    
    test_data = comparison_data[selected_test_case]
    
    # Display user message
    st.subheader("Test Case Input")
    with st.expander("Show Input", expanded=False):
        st.markdown(test_data['user_message'])
    
    # Side-by-side comparison
    st.subheader("Responses")
    
    # Create columns for each prompt
    cols = st.columns(len(selected_prompts))
    
    for i, prompt_name in enumerate(selected_prompts):
        with cols[i]:
            st.markdown(f"**{prompt_name}**")
            
            prompt_data = test_data['prompts'].get(prompt_name, {})
            
            if prompt_data.get('status') == 'no_data':
                st.warning("No data available")
                continue
            
            # Status indicator
            status = prompt_data.get('status', 'unknown')
            status_indicator = "SUCCESS" if status == 'success' else "FAILED"
            st.markdown(f"**Status:** {status_indicator}")
            
            # Model and metadata
            if prompt_data.get('model_name'):
                st.caption(f"Model: {prompt_data['model_name']}")
            
            if prompt_data.get('response_length'):
                st.caption(f"Length: {prompt_data['response_length']} chars")
            
            # Response content
            response = prompt_data.get('response_content', '')
            if response:
                with st.expander(f"View Response ({len(response)} chars)", expanded=True):
                    st.markdown(response)
            else:
                st.warning("No response available")
    
    # Comparison summary
    st.subheader("Summary")
    
    summary_data = []
    for prompt_name in selected_prompts:
        prompt_data = test_data['prompts'].get(prompt_name, {})
        summary_data.append({
            'Prompt': prompt_name,
            'Status': prompt_data.get('status', 'no_data'),
            'Model': prompt_data.get('model_name', 'N/A'),
            'Response Length': prompt_data.get('response_length', 0),
            'Has Response': 'Yes' if prompt_data.get('has_response') else 'No'
        })
    
    st.dataframe(pd.DataFrame(summary_data), width='stretch')


def show_data_explorer(df: pd.DataFrame):
    """Display detailed data exploration interface."""
    st.header("Data Explorer")
    
    # Raw data table with search and sorting
    st.subheader("Detailed Results")
    
    # Column selector
    all_columns = df.columns.tolist()
    display_columns = st.multiselect(
        "Columns to Display:",
        all_columns,
        default=['timestamp', 'prompt_name', 'test_case_name', 'model_display_name', 'status', 'response_length']
    )
    
    if display_columns:
        # Sort options
        sort_column = st.selectbox("Sort by:", display_columns, index=0)
        sort_ascending = st.radio("Sort order:", ["Ascending", "Descending"], index=1) == "Ascending"
        
        # Display sorted data
        sorted_df = df.sort_values(sort_column, ascending=sort_ascending)
        st.dataframe(sorted_df[display_columns], width='stretch')
        
        # Export functionality
        st.subheader("Export Data")
        if st.button("Generate Export File"):
            filters_applied = {
                'columns': display_columns,
                'sort_by': sort_column,
                'sort_order': 'ascending' if sort_ascending else 'descending'
            }
            
            export_text = export_results_to_text(sorted_df, filters_applied)
            
            # Offer download
            st.download_button(
                label="Download Results",
                data=export_text,
                file_name=f"prompt_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )


if __name__ == "__main__":
    main()
