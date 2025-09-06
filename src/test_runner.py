"""
Experiment execution engine for systematic prompt testing.

This module implements the core experimental logic, treating the testing process
as a formal exploration of the Cartesian product: Prompts × TestCases × Models.
Each combination represents a point in our experimental manifold.
"""

import os
import time
import asyncio
from pathlib import Path
from typing import List, Tuple, Dict, Any, Iterator, Optional, Union
from dataclasses import dataclass
from contextlib import asynccontextmanager

from .storage import ExperimentStorage
from .llm_client import LLMClient, LLMError


@dataclass
class ExperimentConfig:
    """Configuration parameters for an experimental run."""
    prompts_dir: Path = Path("prompts")
    test_cases_dir: Path = Path("test_cases")
    models: List[str] = None
    storage_path: str = "results.db"
    config_path: str = "config.json"


@dataclass
class ExperimentResult:
    """Result of a single experimental trial."""
    prompt_file: str
    test_case_file: str
    model_name: str  # Configured model name (what we sent to the API)
    system_message: str
    user_message: str
    response_content: str = None
    response_model_name: str = None  # Actual model name from API response
    status: str = "success"
    error_details: Dict[str, Any] = None
    duration_seconds: float = 0.0


class TestRunner:
    """
    Experimental engine for systematic prompt evaluation.
    
    This class orchestrates the execution of all combinations in the
    experimental space, ensuring proper error handling, rate limiting,
    and result persistence through elegant functional composition.
    """
    
    def __init__(self, config: ExperimentConfig = None):
        """Initialize the test runner with configuration."""
        self.config = config or ExperimentConfig()
        self.storage = ExperimentStorage(self.config.storage_path)
        self.llm_client = LLMClient(self.config.config_path)
        
        # Validate directory structure
        self._validate_directories()
    
    def _validate_directories(self) -> None:
        """Ensure required directories exist and contain files."""
        if not self.config.prompts_dir.exists():
            raise FileNotFoundError(f"Prompts directory not found: {self.config.prompts_dir}")
        
        if not self.config.test_cases_dir.exists():
            raise FileNotFoundError(f"Test cases directory not found: {self.config.test_cases_dir}")
        
        prompts = list(self.config.prompts_dir.glob("*.md"))
        if not prompts:
            raise ValueError(f"No prompt files (*.md) found in {self.config.prompts_dir}")
        
        test_cases = list(self.config.test_cases_dir.glob("*.md"))
        if not test_cases:
            raise ValueError(f"No test case files (*.md) found in {self.config.test_cases_dir}")
    
    def discover_prompts(self) -> List[Path]:
        """Discover all prompt files in the prompts directory."""
        return sorted(self.config.prompts_dir.glob("*.md"))
    
    def discover_test_cases(self) -> List[Path]:
        """Discover all test case files in the test cases directory."""
        return sorted(self.config.test_cases_dir.glob("*.md"))
    
    def load_file_content(self, file_path: Path) -> str:
        """Load content from a markdown file, treating it as pure text."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except UnicodeDecodeError:
            # Fallback for files with different encodings
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read().strip()
    
    def generate_experiment_combinations(self) -> Iterator[Tuple[Path, Path, str]]:
        """
        Generate all combinations for the experimental matrix.
        
        Yields tuples of (prompt_file, test_case_file, model_name)
        representing each point in our experimental manifold.
        """
        prompts = self.discover_prompts()
        test_cases = self.discover_test_cases()
        models = self.config.models or self.llm_client.get_available_models()
        
        for prompt_file in prompts:
            for test_case_file in test_cases:
                for model_name in models:
                    yield (prompt_file, test_case_file, model_name)
    
    def _create_experiment_result(
        self, 
        prompt_file: Path, 
        test_case_file: Path, 
        model_name: str,
        system_message: str,
        user_message: str
    ) -> ExperimentResult:
        """Create a standardized experiment result object."""
        return ExperimentResult(
            prompt_file=prompt_file.name,
            test_case_file=test_case_file.name,
            model_name=model_name,
            system_message=system_message,
            user_message=user_message
        )
    
    def _classify_llm_error(self, error: LLMError) -> str:
        """Map LLM error types to status codes using pure functional mapping."""
        error_type = type(error).__name__
        
        error_mapping = {
            'RateLimitError': 'rate_limit',
            'AuthenticationError': 'api_error',
            'TimeoutError': 'timeout',
            'NetworkError': 'network_error',
            'InvalidModelError': 'invalid_model',
            'APIError': 'api_error'
        }
        
        return error_mapping.get(error_type, 'unknown_error')
    
    def _handle_experiment_error(self, result: ExperimentResult, error: Exception) -> ExperimentResult:
        """Apply error transformation to experiment result in a pure functional manner."""
        if isinstance(error, LLMError):
            result.status = self._classify_llm_error(error)
        else:
            result.status = "unknown_error"
            
        result.error_details = {
            "error_type": type(error).__name__,
            "message": str(error),
            "timestamp": time.time()
        }
        
        return result
    
    def _log_experiment_start(self, prompt_file: Path, test_case_file: Path, model_name: str) -> None:
        """Log the initiation of an experiment trial."""
        print(f"→ Initiating: {prompt_file.name} × {test_case_file.name} × {model_name}")
    
    def _log_experiment_result(
        self, 
        result: ExperimentResult, 
        experiment_number: int, 
        total_experiments: int
    ) -> None:
        """Log the completion of an experiment trial."""
        if result.status == "success":
            print(f"  [{experiment_number}/{total_experiments}] ✓ Completed ({result.duration_seconds:.2f}s)")
        else:
            print(f"  [{experiment_number}/{total_experiments}] ✗ Failed: {result.status}")
            if result.error_details:
                error_msg = result.error_details.get('message', 'Unknown error')
                print(f"    Error: {error_msg[:100]}{'...' if len(error_msg) > 100 else ''}")
    
    async def _execute_llm_request_async(
        self, 
        system_message: str, 
        user_message: str, 
        model_name: str
    ) -> Tuple[str, str]:
        """Execute LLM request asynchronously, returning (content, model_name)."""
        response = await self.llm_client.complete_async(
            system_message=system_message,
            user_message=user_message,
            model_name=model_name
        )
        return response.content, response.model
    
    def _execute_llm_request_sync(
        self, 
        system_message: str, 
        user_message: str, 
        model_name: str
    ) -> Tuple[str, str]:
        """Execute LLM request synchronously, returning (content, model_name)."""
        response = self.llm_client.complete(
            system_message=system_message,
            user_message=user_message,
            model_name=model_name
        )
        return response.content, response.model
    
    async def _run_experiment_core_async(
        self, 
        prompt_file: Path, 
        test_case_file: Path, 
        model_name: str,
        log_start: bool = True
    ) -> ExperimentResult:
        """Core experiment execution logic for async operations."""
        if log_start:
            self._log_experiment_start(prompt_file, test_case_file, model_name)
        
        start_time = time.time()
        
        # Load content - this is a pure, side-effect-free operation
        system_message = self.load_file_content(prompt_file)
        user_message = self.load_file_content(test_case_file)
        
        # Create result object in its initial state
        result = self._create_experiment_result(
            prompt_file, test_case_file, model_name, system_message, user_message
        )
        
        try:
            # Execute the transformation through the LLM manifold
            content, response_model = await self._execute_llm_request_async(
                system_message, user_message, model_name
            )
            result.response_content = content
            result.response_model_name = response_model
            result.status = "success"
            
        except Exception as e:
            result = self._handle_experiment_error(result, e)
        
        finally:
            result.duration_seconds = time.time() - start_time
        
        return result
    
    def _run_experiment_core_sync(
        self, 
        prompt_file: Path, 
        test_case_file: Path, 
        model_name: str,
        log_start: bool = True
    ) -> ExperimentResult:
        """Core experiment execution logic for synchronous operations."""
        if log_start:
            self._log_experiment_start(prompt_file, test_case_file, model_name)
        
        start_time = time.time()
        
        # Load content - this is a pure, side-effect-free operation
        system_message = self.load_file_content(prompt_file)
        user_message = self.load_file_content(test_case_file)
        
        # Create result object in its initial state
        result = self._create_experiment_result(
            prompt_file, test_case_file, model_name, system_message, user_message
        )
        
        try:
            # Execute the transformation through the LLM manifold
            content, response_model = self._execute_llm_request_sync(
                system_message, user_message, model_name
            )
            result.response_content = content
            result.response_model_name = response_model
            result.status = "success"
            
        except Exception as e:
            result = self._handle_experiment_error(result, e)
        
        finally:
            result.duration_seconds = time.time() - start_time
        
        return result
    
    def _store_experiment_result(self, run_id: str, result: ExperimentResult) -> None:
        """Store experiment result in persistent storage."""
        self.storage.store_result(
            run_id=run_id,
            prompt_file=result.prompt_file,
            test_case_file=result.test_case_file,
            model_name=result.model_name,
            response_model_name=result.response_model_name,
            system_message=result.system_message,
            user_message=result.user_message,
            response_content=result.response_content,
            status=result.status,
            error_details=result.error_details
        )
    
    def _create_run_config_snapshot(self, is_async: bool = False) -> Dict[str, Any]:
        """Create configuration snapshot for run metadata."""
        config_snapshot = {
            'models': [model.name for model in self.llm_client.models],
            'prompts_count': len(self.discover_prompts()),
            'test_cases_count': len(self.discover_test_cases()),
            'execution_mode': 'asynchronous' if is_async else 'synchronous'
        }
        
        if is_async and hasattr(self.llm_client, 'max_concurrent_requests'):
            config_snapshot['max_concurrent_requests'] = self.llm_client.max_concurrent_requests
        
        if hasattr(self.llm_client, 'request_delay'):
            config_snapshot['request_delay_seconds'] = self.llm_client.request_delay
        
        return config_snapshot
    
    def _print_run_header(self, run_id: str, total_experiments: int, is_async: bool = False) -> None:
        """Print standardized run header information."""
        mode = "asynchronous" if is_async else "synchronous"
        print(f"Starting {mode} experimental run: {run_id}")
        
        if not is_async:
            print("[LEGACY MODE] Using synchronous execution for backward compatibility")
            
        print(f"Total combinations to test: {total_experiments}")
        print(f"Prompts: {len(self.discover_prompts())}")
        print(f"Test cases: {len(self.discover_test_cases())}")
        print(f"Models: {len(self.config.models or self.llm_client.get_available_models())}")
        
        if is_async and hasattr(self.llm_client, 'max_concurrent_requests'):
            print(f"Max concurrent requests: {self.llm_client.max_concurrent_requests}")
            
        print("-" * 60)
    
    def _print_run_summary(self, run_id: str, successful_count: int, total_count: int, is_async: bool = False) -> None:
        """Print standardized run summary information."""
        mode = "Asynchronous" if is_async else "Synchronous"
        print("-" * 60)
        print(f"{mode} experimental run completed: {run_id}")
        print(f"Successful experiments: {successful_count}/{total_count}")
        print(f"Success rate: {(successful_count/total_count)*100:.1f}%")
    
    # Public API methods preserved for backward compatibility
    async def run_single_experiment_async(
        self, 
        prompt_file: Path, 
        test_case_file: Path, 
        model_name: str
    ) -> ExperimentResult:
        """Execute a single experimental trial asynchronously."""
        return await self._run_experiment_core_async(prompt_file, test_case_file, model_name, log_start=False)
    
    def run_single_experiment(
        self, 
        prompt_file: Path, 
        test_case_file: Path, 
        model_name: str
    ) -> ExperimentResult:
        """Execute a single experimental trial synchronously."""
        return self._run_experiment_core_sync(prompt_file, test_case_file, model_name, log_start=False)
    
    async def run_experiments_async(self, run_id: str = None) -> str:
        """
        Execute the complete experimental matrix asynchronously.
        
        This method orchestrates the concurrent exploration of our
        experimental space, transforming what was once a linear process
        into an elegant parallel computation that respects rate limits
        while maximizing throughput.
        
        Returns the run_id for the completed experiment batch.
        """
        if run_id is None:
            run_id = self.storage.generate_run_id()
        
        combinations = list(self.generate_experiment_combinations())
        total_experiments = len(combinations)
        
        # Initialize run with metadata
        config_snapshot = self._create_run_config_snapshot(is_async=True)
        self.storage.start_run(run_id, total_experiments, config_snapshot)
        
        # Print run initialization
        self._print_run_header(run_id, total_experiments, is_async=True)
        
        # Execution state management
        successful_experiments = 0
        completed_experiments = 0
        progress_lock = asyncio.Lock()
        
        async def execute_and_track_experiment(
            prompt_file: Path, 
            test_case_file: Path, 
            model_name: str, 
            experiment_index: int
        ) -> ExperimentResult:
            """Execute experiment with integrated progress tracking."""
            nonlocal successful_experiments, completed_experiments
            
            result = await self._run_experiment_core_async(prompt_file, test_case_file, model_name)
            
            # Store result atomically
            self._store_experiment_result(run_id, result)
            
            # Update progress with thread safety
            async with progress_lock:
                completed_experiments += 1
                if result.status == "success":
                    successful_experiments += 1
                self._log_experiment_result(result, completed_experiments, total_experiments)
            
            return result
        
        # Create and execute all experiment tasks
        tasks = [
            execute_and_track_experiment(prompt_file, test_case_file, model_name, i)
            for i, (prompt_file, test_case_file, model_name) in enumerate(combinations, 1)
        ]
        
        try:
            await asyncio.gather(*tasks, return_exceptions=False)
        except Exception as e:
            print(f"\nExperiment batch encountered an error: {e}")
            print("Continuing with completed experiments...")
        
        # Finalize run
        self._print_run_summary(run_id, successful_experiments, total_experiments, is_async=True)
        self.storage.complete_run(run_id, successful_experiments)
        
        return run_id
    
    def run_experiments(self, run_id: str = None) -> str:
        """
        Execute the complete experimental matrix synchronously.
        
        This method orchestrates the systematic exploration of our
        experimental space, ensuring proper persistence and error recovery.
        
        Returns the run_id for the completed experiment batch.
        """
        if run_id is None:
            run_id = self.storage.generate_run_id()
        
        combinations = list(self.generate_experiment_combinations())
        total_experiments = len(combinations)
        
        # Initialize run with metadata
        config_snapshot = self._create_run_config_snapshot(is_async=False)
        self.storage.start_run(run_id, total_experiments, config_snapshot)
        
        # Print run initialization
        self._print_run_header(run_id, total_experiments, is_async=False)
        
        successful_experiments = 0
        
        for i, (prompt_file, test_case_file, model_name) in enumerate(combinations, 1):
            result = self._run_experiment_core_sync(prompt_file, test_case_file, model_name)
            
            # Store result
            self._store_experiment_result(run_id, result)
            
            if result.status == "success":
                successful_experiments += 1
            
            self._log_experiment_result(result, i, total_experiments)
        
        # Finalize run
        self._print_run_summary(run_id, successful_experiments, total_experiments, is_async=False)
        self.storage.complete_run(run_id, successful_experiments)
        
        return run_id
    
    def get_experiment_summary(self, run_id: str = None) -> Dict[str, Any]:
        """Get a statistical summary of experimental results."""
        if run_id is None:
            run_id = self.storage.get_latest_run_id()
            if not run_id:
                return {"error": "No experimental runs found"}
        
        return self.storage.get_run_summary(run_id)