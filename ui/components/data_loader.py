"""
Data integration layer for Streamlit interface.

This module provides cached access to experimental data and transforms it
into formats optimized for UI consumption, treating data as invariant 
manifolds with efficient querying patterns.
"""

import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import json
from datetime import datetime


@st.cache_data(ttl=60)  # Cache for 60 seconds
def load_runs_data() -> Dict[str, Any]:
    """Load metadata for all experimental runs with caching."""
    # Look for database in project root (two levels up from ui/components/)
    db_path = Path(__file__).parent.parent.parent / "results.db"
    if not db_path.exists():
        return {"runs": [], "error": "No database found"}
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        # Get run summaries
        cursor = conn.execute("""
            SELECT 
                run_id,
                MIN(run_started_timestamp) as run_started,
                MIN(run_completed_timestamp) as run_completed,
                MIN(run_total_experiments) as total_experiments,
                MIN(run_successful_experiments) as successful_experiments,
                COUNT(*) as actual_experiments,
                COUNT(DISTINCT prompt_file) as unique_prompts,
                COUNT(DISTINCT test_case_file) as unique_test_cases,
                COUNT(DISTINCT model_name) as unique_models,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as actual_successful,
                MIN(run_config_snapshot) as config_json
            FROM experiments
            GROUP BY run_id
            ORDER BY MIN(run_started_timestamp) DESC
        """)
        
        runs = []
        for row in cursor.fetchall():
            run_data = dict(row)
            
            # Parse config if available
            if run_data.get('config_json'):
                try:
                    run_data['config'] = json.loads(run_data['config_json'])
                except json.JSONDecodeError:
                    run_data['config'] = {}
            else:
                run_data['config'] = {}
            
            # Clean up and add derived fields
            del run_data['config_json']
            run_data['success_rate'] = (
                run_data['actual_successful'] / run_data['actual_experiments'] 
                if run_data['actual_experiments'] > 0 else 0.0
            )
            run_data['is_completed'] = run_data['run_completed'] is not None
            
            # Format timestamps for display
            if run_data['run_started']:
                try:
                    dt = datetime.fromisoformat(run_data['run_started'])
                    run_data['run_started_display'] = dt.strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    run_data['run_started_display'] = run_data['run_started']
            
            runs.append(run_data)
        
        conn.close()
        return {"runs": runs, "error": None}
        
    except Exception as e:
        return {"runs": [], "error": f"Database error: {str(e)}"}


@st.cache_data(ttl=60)
def load_run_results(run_id: str) -> pd.DataFrame:
    """Load experimental results for a specific run as a pandas DataFrame."""
    # Look for database in project root (two levels up from ui/components/)
    db_path = Path(__file__).parent.parent.parent / "results.db"
    if not db_path.exists():
        return pd.DataFrame()
    
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query("""
            SELECT 
                id, run_id, timestamp, prompt_file, test_case_file, 
                model_name, response_model_name, system_message, user_message,
                response_content, status, error_details,
                run_started_timestamp, run_completed_timestamp
            FROM experiments 
            WHERE run_id = ?
            ORDER BY timestamp
        """, conn, params=(run_id,))
        conn.close()
        
        # Parse error details if present
        if 'error_details' in df.columns:
            df['error_details'] = df['error_details'].apply(
                lambda x: json.loads(x) if x and x.strip() else None
            )
        
        # Add derived columns for UI convenience
        df['prompt_name'] = df['prompt_file'].str.replace('.md', '').str.replace('_', ' ').str.title()
        df['test_case_name'] = df['test_case_file'].str.replace('.md', '').str.replace('_', ' ').str.title()
        df['model_display_name'] = df['model_name'].str.split('/').str[-1]  # Remove provider prefix
        
        # Response length for quick assessment
        df['response_length'] = df['response_content'].fillna('').str.len()
        df['has_response'] = df['response_content'].notna() & (df['response_content'] != '')
        
        return df
        
    except Exception as e:
        if hasattr(st, 'error'):  # Check if we're in a Streamlit context
            st.error(f"Error loading run results: {str(e)}")
        return pd.DataFrame()


def get_available_filters(df: pd.DataFrame) -> Dict[str, List[str]]:
    """Extract available filter options from the results DataFrame."""
    if df.empty:
        return {}
    
    return {
        'prompts': sorted(df['prompt_name'].dropna().unique().tolist()),
        'test_cases': sorted(df['test_case_name'].dropna().unique().tolist()),
        'models': sorted(df['model_display_name'].dropna().unique().tolist()),
        'statuses': sorted(df['status'].dropna().unique().tolist())
    }


def apply_filters(
    df: pd.DataFrame, 
    selected_prompts: List[str] = None,
    selected_test_cases: List[str] = None,
    selected_models: List[str] = None,
    selected_statuses: List[str] = None,
    search_query: str = ""
) -> pd.DataFrame:
    """Apply filters to the DataFrame based on user selections."""
    if df.empty:
        return df
    
    filtered_df = df.copy()
    
    # Apply categorical filters
    if selected_prompts:
        filtered_df = filtered_df[filtered_df['prompt_name'].isin(selected_prompts)]
    
    if selected_test_cases:
        filtered_df = filtered_df[filtered_df['test_case_name'].isin(selected_test_cases)]
    
    if selected_models:
        filtered_df = filtered_df[filtered_df['model_display_name'].isin(selected_models)]
    
    if selected_statuses:
        filtered_df = filtered_df[filtered_df['status'].isin(selected_statuses)]
    
    # Apply text search across relevant columns
    if search_query.strip():
        search_cols = ['prompt_name', 'test_case_name', 'user_message', 'response_content']
        search_mask = pd.Series([False] * len(filtered_df), index=filtered_df.index)
        
        for col in search_cols:
            if col in filtered_df.columns:
                search_mask |= filtered_df[col].fillna('').str.contains(
                    search_query, case=False, na=False
                )
        
        filtered_df = filtered_df[search_mask]
    
    return filtered_df


def get_comparison_data(
    df: pd.DataFrame, 
    selected_prompts: List[str],
    test_case: str = None
) -> Dict[str, Any]:
    """
    Prepare data for side-by-side comparison of prompts.
    
    Returns data structured for easy comparison display.
    """
    if df.empty or not selected_prompts:
        return {}
    
    # Filter for selected prompts
    comparison_df = df[df['prompt_name'].isin(selected_prompts)].copy()
    
    # Further filter by test case if specified
    if test_case:
        comparison_df = comparison_df[comparison_df['test_case_name'] == test_case]
    
    # Group by test case and organize by prompt
    comparison_data = {}
    
    for test_case_name in comparison_df['test_case_name'].unique():
        test_data = comparison_df[comparison_df['test_case_name'] == test_case_name]
        
        comparison_data[test_case_name] = {
            'user_message': test_data['user_message'].iloc[0] if len(test_data) > 0 else "",
            'prompts': {}
        }
        
        for prompt_name in selected_prompts:
            prompt_data = test_data[test_data['prompt_name'] == prompt_name]
            
            if len(prompt_data) > 0:
                result = prompt_data.iloc[0]
                comparison_data[test_case_name]['prompts'][prompt_name] = {
                    'system_message': result['system_message'],
                    'response_content': result['response_content'],
                    'status': result['status'],
                    'model_name': result['model_display_name'],
                    'timestamp': result['timestamp'],
                    'response_length': result['response_length'],
                    'has_response': result['has_response']
                }
            else:
                # No data for this prompt-test case combination
                comparison_data[test_case_name]['prompts'][prompt_name] = {
                    'system_message': None,
                    'response_content': None,
                    'status': 'no_data',
                    'model_name': None,
                    'timestamp': None,
                    'response_length': 0,
                    'has_response': False
                }
    
    return comparison_data


def export_results_to_text(df: pd.DataFrame, filters_applied: Dict[str, Any]) -> str:
    """Export filtered results to a formatted text string."""
    if df.empty:
        return "No data to export."
    
    output_lines = []
    output_lines.append("=" * 80)
    output_lines.append("PROMPT TESTER RESULTS EXPORT")
    output_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    output_lines.append(f"Total Results: {len(df)}")
    output_lines.append("=" * 80)
    
    # Add filter information
    if filters_applied:
        output_lines.append("\nFILTERS APPLIED:")
        for filter_name, filter_values in filters_applied.items():
            if filter_values:
                output_lines.append(f"  {filter_name}: {', '.join(map(str, filter_values))}")
    
    output_lines.append("\n" + "-" * 80)
    
    # Export each result
    for idx, row in df.iterrows():
        output_lines.append(f"\nRESULT #{idx + 1}")
        output_lines.append(f"Prompt: {row['prompt_name']}")
        output_lines.append(f"Test Case: {row['test_case_name']}")
        output_lines.append(f"Model: {row['model_display_name']}")
        output_lines.append(f"Status: {row['status']}")
        output_lines.append(f"Timestamp: {row['timestamp']}")
        
        output_lines.append(f"\nUser Message:")
        output_lines.append(row['user_message'][:500] + ("..." if len(row['user_message']) > 500 else ""))
        
        if row['has_response']:
            output_lines.append(f"\nResponse ({row['response_length']} chars):")
            output_lines.append(row['response_content'][:1000] + ("..." if len(row['response_content']) > 1000 else ""))
        else:
            output_lines.append("\nNo response available.")
        
        output_lines.append("-" * 80)
    
    return "\n".join(output_lines)
