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
            # First, create tables with new schema
            self._create_tables(conn)
            # Then, handle any necessary migrations
            self._migrate_schema(conn)
    
    def _create_tables(self, conn) -> None:
        """Create database tables with the latest schema."""
        conn.execute("""
            CREATE TABLE IF NOT EXISTS experiment_results (
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
                UNIQUE(run_id, prompt_file, test_case_file, model_name)
            )
        """)
        
        # Create run metadata table for tracking run-level information
        conn.execute("""
            CREATE TABLE IF NOT EXISTS experiment_runs (
                run_id TEXT PRIMARY KEY,
                started_timestamp TEXT NOT NULL,
                completed_timestamp TEXT,
                total_experiments INTEGER,
                successful_experiments INTEGER,
                config_snapshot TEXT
            )
        """)
    
    def _migrate_schema(self, conn) -> None:
        """Handle database schema migrations for backward compatibility."""
        # Check if response_model_name column exists
        cursor = conn.execute("PRAGMA table_info(experiment_results)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'response_model_name' not in columns:
            try:
                conn.execute("ALTER TABLE experiment_results ADD COLUMN response_model_name TEXT")
                print("📈 Database schema upgraded: Added response_model_name column")
            except Exception as e:
                print(f"⚠️  Schema migration note: {e}")
        
        # Ensure experiment_runs table exists (may be missing in older versions)
        cursor = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='experiment_runs'
        """)
        if not cursor.fetchone():
            conn.execute("""
                CREATE TABLE experiment_runs (
                    run_id TEXT PRIMARY KEY,
                    started_timestamp TEXT NOT NULL,
                    completed_timestamp TEXT,
                    total_experiments INTEGER,
                    successful_experiments INTEGER,
                    config_snapshot TEXT
                )
            """)
            print("📈 Database schema upgraded: Added experiment_runs table")
            
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
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_runs_started 
            ON experiment_runs(started_timestamp)
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
        """Record the start of an experimental run."""
        started_timestamp = datetime.utcnow().isoformat()
        config_json = json.dumps(config_snapshot) if config_snapshot else None
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO experiment_runs (
                    run_id, started_timestamp, total_experiments, config_snapshot
                ) VALUES (?, ?, ?, ?)
            """, (run_id, started_timestamp, total_experiments, config_json))
    
    def complete_run(self, run_id: str, successful_experiments: int) -> None:
        """Mark an experimental run as completed."""
        completed_timestamp = datetime.utcnow().isoformat()
        
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE experiment_runs 
                SET completed_timestamp = ?, successful_experiments = ?
                WHERE run_id = ?
            """, (completed_timestamp, successful_experiments, run_id))
    
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
        Store a single experimental result with atomic guarantees.
        
        Returns the database ID of the inserted record.
        """
        timestamp = datetime.utcnow().isoformat()
        error_json = json.dumps(error_details) if error_details else None
        
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT OR REPLACE INTO experiment_results (
                    run_id, timestamp, prompt_file, test_case_file,
                    model_name, response_model_name, system_message, user_message,
                    response_content, status, error_details
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run_id, timestamp, prompt_file, test_case_file,
                model_name, response_model_name, system_message, user_message,
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
            # First try to get from run metadata table, then fall back to experiment results
            cursor = conn.execute("""
                SELECT run_id, started_timestamp as sort_time
                FROM experiment_runs
                UNION
                SELECT run_id, MIN(timestamp) as sort_time
                FROM experiment_results
                WHERE run_id NOT IN (SELECT run_id FROM experiment_runs)
                GROUP BY run_id
                ORDER BY sort_time
            """)
            return [row['run_id'] for row in cursor.fetchall()]
    
    def get_run_summary(self, run_id: str) -> Dict[str, Any]:
        """Get a statistical summary of an experimental run."""
        with self._get_connection() as conn:
            # Get run metadata
            cursor = conn.execute("""
                SELECT * FROM experiment_runs WHERE run_id = ?
            """, (run_id,))
            run_metadata = cursor.fetchone()
            
            # Get experiment statistics with graceful handling of missing columns
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_experiments,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
                    COUNT(DISTINCT prompt_file) as unique_prompts,
                    COUNT(DISTINCT test_case_file) as unique_test_cases,
                    COUNT(DISTINCT model_name) as unique_models,
                    COUNT(DISTINCT CASE WHEN response_model_name IS NOT NULL THEN response_model_name END) as unique_response_models,
                    MIN(timestamp) as first_experiment_time,
                    MAX(timestamp) as last_experiment_time
                FROM experiment_results 
                WHERE run_id = ?
            """, (run_id,))
            experiment_stats = cursor.fetchone()
            
            if not experiment_stats:
                return {}
                
            result = dict(experiment_stats)
            
            # Add run metadata if available
            if run_metadata:
                result.update({
                    'run_started_timestamp': run_metadata['started_timestamp'],
                    'run_completed_timestamp': run_metadata['completed_timestamp'],
                    'config_snapshot': json.loads(run_metadata['config_snapshot']) if run_metadata['config_snapshot'] else None
                })
            
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
