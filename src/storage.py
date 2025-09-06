"""
Storage layer for prompt testing experiments.

This module implements a SQLite-based persistence layer that treats experimental
data as an invariant manifold, ensuring data integrity through proper schema
design and transaction management.
"""

import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager


class ExperimentStorage:
    """
    A storage abstraction that maintains experimental data integrity
    through formal database constraints and atomic operations.
    """
    
    def __init__(self, db_path: str = "results.db"):
        """Initialize storage with proper schema constraints."""
        self.db_path = Path(db_path)
        self._current_run_metadata = {}  # Cache for active run metadata
        self._initialize_schema()
    
    def _initialize_schema(self) -> None:
        """Create the database schema with proper constraints and indices."""
        with self._get_connection() as conn:
            self._create_tables(conn)
    
    def _create_tables(self, conn) -> None:
        """Create database tables with the unified schema and indices."""
        conn.execute("""
            CREATE TABLE IF NOT EXISTS experiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                prompt_file TEXT NOT NULL,
                test_case_file TEXT NOT NULL,
                model_name TEXT NOT NULL,
                response_model_name TEXT,
                system_message TEXT NOT NULL,
                user_message TEXT NOT NULL,
                response_content TEXT,
                status TEXT NOT NULL CHECK(status IN (
                    'success', 'api_error', 'timeout', 'rate_limit', 
                    'invalid_model', 'network_error', 'unknown_error'
                )),
                error_details TEXT,
                run_started_timestamp TEXT NOT NULL,
                run_completed_timestamp TEXT,
                run_total_experiments INTEGER,
                run_successful_experiments INTEGER,
                run_config_snapshot TEXT,
                UNIQUE(run_id, prompt_file, test_case_file, model_name)
            )
        """)
        
        # Create indices for efficient querying
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_experiments_run_id 
            ON experiments(run_id)
        """)
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_experiments_timestamp 
            ON experiments(timestamp)
        """)
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_experiments_status 
            ON experiments(status)
        """)
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_experiments_run_started 
            ON experiments(run_started_timestamp)
        """)
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections with proper transaction handling."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access to rows
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def generate_run_id(self) -> str:
        """Generate a unique identifier for an experimental run."""
        return str(uuid.uuid4())
    
    def start_run(
        self, 
        run_id: str, 
        total_experiments: int,
        config_snapshot: Optional[Dict[str, Any]] = None
    ) -> None:
        """Prepare run metadata for an experimental run."""
        started_timestamp = datetime.utcnow().isoformat()
        config_json = json.dumps(config_snapshot) if config_snapshot else None
        
        # Cache run metadata to be included with each experiment result
        self._current_run_metadata[run_id] = {
            'run_started_timestamp': started_timestamp,
            'run_completed_timestamp': None,
            'run_total_experiments': total_experiments,
            'run_successful_experiments': None,
            'run_config_snapshot': config_json
        }
    
    def complete_run(self, run_id: str, successful_experiments: int) -> None:
        """Mark an experimental run as completed by updating all experiments."""
        completed_timestamp = datetime.utcnow().isoformat()
        
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE experiments 
                SET run_completed_timestamp = ?, run_successful_experiments = ?
                WHERE run_id = ?
            """, (completed_timestamp, successful_experiments, run_id))
            
        # Update cached metadata if present
        if run_id in self._current_run_metadata:
            self._current_run_metadata[run_id]['run_completed_timestamp'] = completed_timestamp
            self._current_run_metadata[run_id]['run_successful_experiments'] = successful_experiments
    
    def _get_run_metadata(self, run_id: str) -> Dict[str, Any]:
        """Get run metadata from cache or existing experiment data."""
        # First check cache
        if run_id in self._current_run_metadata:
            return self._current_run_metadata[run_id]
        
        # If not in cache, try to get from existing experiment in database
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT run_started_timestamp, run_completed_timestamp,
                       run_total_experiments, run_successful_experiments, run_config_snapshot
                FROM experiments WHERE run_id = ? LIMIT 1
            """, (run_id,))
            row = cursor.fetchone()
            
            if row:
                return {
                    'run_started_timestamp': row['run_started_timestamp'],
                    'run_completed_timestamp': row['run_completed_timestamp'],
                    'run_total_experiments': row['run_total_experiments'],
                    'run_successful_experiments': row['run_successful_experiments'],
                    'run_config_snapshot': row['run_config_snapshot']
                }
        
        # If no existing data, provide defaults (this shouldn't happen in normal flow)
        return {
            'run_started_timestamp': datetime.utcnow().isoformat(),
            'run_completed_timestamp': None,
            'run_total_experiments': None,
            'run_successful_experiments': None,
            'run_config_snapshot': None
        }
    
    def store_result(
        self,
        run_id: str,
        prompt_file: str,
        test_case_file: str,
        model_name: str,
        system_message: str,
        user_message: str,
        response_content: Optional[str] = None,
        response_model_name: Optional[str] = None,
        status: str = "success",
        error_details: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Store a single experimental result with atomic guarantees and run metadata.
        
        Returns the database ID of the inserted record.
        """
        timestamp = datetime.utcnow().isoformat()
        error_json = json.dumps(error_details) if error_details else None
        
        # Get run metadata from cache or query existing experiment
        run_metadata = self._get_run_metadata(run_id)
        
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT OR REPLACE INTO experiments (
                    run_id, timestamp, prompt_file, test_case_file,
                    model_name, response_model_name, system_message, user_message,
                    response_content, status, error_details,
                    run_started_timestamp, run_completed_timestamp,
                    run_total_experiments, run_successful_experiments, run_config_snapshot
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id, timestamp, prompt_file, test_case_file,
                model_name, response_model_name, system_message, user_message,
                response_content, status, error_json,
                run_metadata['run_started_timestamp'],
                run_metadata['run_completed_timestamp'],
                run_metadata['run_total_experiments'],
                run_metadata['run_successful_experiments'],
                run_metadata['run_config_snapshot']
            ))
            return cursor.lastrowid
    
    def get_results_by_run(self, run_id: str) -> List[Dict[str, Any]]:
        """Retrieve all results for a specific experimental run."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM experiments 
                WHERE run_id = ? 
                ORDER BY timestamp
            """, (run_id,))
            return [self._row_to_dict(row) for row in cursor.fetchall()]
    
    def get_latest_run_id(self) -> Optional[str]:
        """Get the run_id of the most recent experimental run."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT run_id FROM experiments 
                ORDER BY run_started_timestamp DESC 
                LIMIT 1
            """)
            row = cursor.fetchone()
            return row['run_id'] if row else None
    
    def get_latest_results(self) -> List[Dict[str, Any]]:
        """Retrieve results from the most recent experimental run."""
        latest_run_id = self.get_latest_run_id()
        if not latest_run_id:
            return []
        return self.get_results_by_run(latest_run_id)
    
    def get_all_run_ids(self) -> List[str]:
        """Get all unique run IDs in chronological order."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT DISTINCT run_id, MIN(run_started_timestamp) as sort_time
                FROM experiments
                GROUP BY run_id
                ORDER BY sort_time
            """)
            return [row['run_id'] for row in cursor.fetchall()]
    
    def get_run_summary(self, run_id: str) -> Dict[str, Any]:
        """Get a statistical summary of an experimental run."""
        with self._get_connection() as conn:
            # Get experiment statistics and run metadata in a single query
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_experiments,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
                    COUNT(DISTINCT prompt_file) as unique_prompts,
                    COUNT(DISTINCT test_case_file) as unique_test_cases,
                    COUNT(DISTINCT model_name) as unique_models,
                    COUNT(DISTINCT CASE WHEN response_model_name IS NOT NULL THEN response_model_name END) as unique_response_models,
                    MIN(timestamp) as first_experiment_time,
                    MAX(timestamp) as last_experiment_time,
                    MIN(run_started_timestamp) as run_started_timestamp,
                    MIN(run_completed_timestamp) as run_completed_timestamp,
                    MIN(run_total_experiments) as run_total_experiments,
                    MIN(run_successful_experiments) as run_successful_experiments,
                    MIN(run_config_snapshot) as run_config_snapshot
                FROM experiments 
                WHERE run_id = ?
            """, (run_id,))
            row = cursor.fetchone()
            
            if not row:
                return {}
                
            result = dict(row)
            
            # Parse config snapshot if available
            if result.get('run_config_snapshot'):
                try:
                    result['config_snapshot'] = json.loads(result['run_config_snapshot'])
                except json.JSONDecodeError:
                    result['config_snapshot'] = None
            else:
                result['config_snapshot'] = None
                
            # Remove the raw JSON field
            result.pop('run_config_snapshot', None)
            
            return result
    
    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert a database row to a dictionary with proper JSON parsing."""
        result = dict(row)
        if result.get('error_details'):
            try:
                result['error_details'] = json.loads(result['error_details'])
            except json.JSONDecodeError:
                # Handle legacy or malformed JSON
                result['error_details'] = {'raw_error': result['error_details']}
        return result
