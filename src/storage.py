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
        self._initialize_schema()
    
    def _initialize_schema(self) -> None:
        """Create the database schema with proper constraints and indices."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS experiment_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    prompt_file TEXT NOT NULL,
                    test_case_file TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    system_message TEXT NOT NULL,
                    user_message TEXT NOT NULL,
                    response_content TEXT,
                    status TEXT NOT NULL CHECK(status IN (
                        'success', 'api_error', 'timeout', 'rate_limit', 
                        'invalid_model', 'network_error', 'unknown_error'
                    )),
                    error_details TEXT,
                    UNIQUE(run_id, prompt_file, test_case_file, model_name)
                )
            """)
            
            # Create indices for efficient querying
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_run_id 
                ON experiment_results(run_id)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON experiment_results(timestamp)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_status 
                ON experiment_results(status)
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
    
    def store_result(
        self,
        run_id: str,
        prompt_file: str,
        test_case_file: str,
        model_name: str,
        system_message: str,
        user_message: str,
        response_content: Optional[str] = None,
        status: str = "success",
        error_details: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Store a single experimental result with atomic guarantees.
        
        Returns the database ID of the inserted record.
        """
        timestamp = datetime.utcnow().isoformat()
        error_json = json.dumps(error_details) if error_details else None
        
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT OR REPLACE INTO experiment_results (
                    run_id, timestamp, prompt_file, test_case_file,
                    model_name, system_message, user_message,
                    response_content, status, error_details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id, timestamp, prompt_file, test_case_file,
                model_name, system_message, user_message,
                response_content, status, error_json
            ))
            return cursor.lastrowid
    
    def get_results_by_run(self, run_id: str) -> List[Dict[str, Any]]:
        """Retrieve all results for a specific experimental run."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM experiment_results 
                WHERE run_id = ? 
                ORDER BY timestamp
            """, (run_id,))
            return [self._row_to_dict(row) for row in cursor.fetchall()]
    
    def get_latest_run_id(self) -> Optional[str]:
        """Get the run_id of the most recent experimental run."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT run_id FROM experiment_results 
                ORDER BY timestamp DESC 
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
                SELECT run_id 
                FROM experiment_results 
                GROUP BY run_id
                ORDER BY MIN(timestamp)
            """)
            return [row['run_id'] for row in cursor.fetchall()]
    
    def get_run_summary(self, run_id: str) -> Dict[str, Any]:
        """Get a statistical summary of an experimental run."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_experiments,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
                    COUNT(DISTINCT prompt_file) as unique_prompts,
                    COUNT(DISTINCT test_case_file) as unique_test_cases,
                    COUNT(DISTINCT model_name) as unique_models,
                    MIN(timestamp) as start_time,
                    MAX(timestamp) as end_time
                FROM experiment_results 
                WHERE run_id = ?
            """, (run_id,))
            row = cursor.fetchone()
            return dict(row) if row else {}
    
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
