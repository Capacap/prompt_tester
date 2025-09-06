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
from typing import List, Tuple, Dict, Any, Iterator
from dataclasses import dataclass

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
    and result persistence.
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
        prompts = list(self.config.prompts_dir.glob("*.md"))
        return sorted(prompts)
    
    def discover_test_cases(self) -> List[Path]:
        """Discover all test case files in the test cases directory."""
        test_cases = list(self.config.test_cases_dir.glob("*.md"))
        return sorted(test_cases)
    
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
    
    async def run_single_experiment_async(
        self, 
        prompt_file: Path, 
        test_case_file: Path, 
        model_name: str
    ) -> ExperimentResult:
        """
        Execute a single experimental trial asynchronously.
        
        This method represents the atomic unit of our experimental process,
        treating each trial as an isolated transformation in the prompt space,
        now enhanced with the elegant concurrency of async operations.
        """
        start_time = time.time()
        
        # Load prompt and test case content
        system_message = self.load_file_content(prompt_file)
        user_message = self.load_file_content(test_case_file)
        
        result = ExperimentResult(
            prompt_file=prompt_file.name,
            test_case_file=test_case_file.name,
            model_name=model_name,
            system_message=system_message,
            user_message=user_message
        )
        
        try:
            # Execute the LLM completion asynchronously
            response = await self.llm_client.complete_async(
                system_message=system_message,
                user_message=user_message,
                model_name=model_name
            )
            
            result.response_content = response.content
            result.response_model_name = response.model  # Capture actual API response model
            result.status = "success"
            
        except LLMError as e:
            # Handle known LLM errors with proper classification
            result.status = self._classify_llm_error(e)
            result.error_details = {
                "error_type": type(e).__name__,
                "message": str(e),
                "timestamp": time.time()
            }
            
        except Exception as e:
            # Handle unexpected errors
            result.status = "unknown_error"
            result.error_details = {
                "error_type": type(e).__name__,
                "message": str(e),
                "timestamp": time.time()
            }
        
        finally:
            result.duration_seconds = time.time() - start_time
        
        return result
    
    def run_single_experiment(
        self, 
        prompt_file: Path, 
        test_case_file: Path, 
        model_name: str
    ) -> ExperimentResult:
        """
        Execute a single experimental trial.
        
        This method represents the atomic unit of our experimental process,
        treating each trial as an isolated transformation in the prompt space.
        """
        start_time = time.time()
        
        # Load prompt and test case content
        system_message = self.load_file_content(prompt_file)
        user_message = self.load_file_content(test_case_file)
        
        result = ExperimentResult(
            prompt_file=prompt_file.name,
            test_case_file=test_case_file.name,
            model_name=model_name,
            system_message=system_message,
            user_message=user_message
        )
        
        try:
            # Execute the LLM completion
            response = self.llm_client.complete(
                system_message=system_message,
                user_message=user_message,
                model_name=model_name
            )
            
            result.response_content = response.content
            result.response_model_name = response.model  # Capture actual API response model
            result.status = "success"
            
        except LLMError as e:
            # Handle known LLM errors with proper classification
            result.status = self._classify_llm_error(e)
            result.error_details = {
                "error_type": type(e).__name__,
                "message": str(e),
                "timestamp": time.time()
            }
            
        except Exception as e:
            # Handle unexpected errors
            result.status = "unknown_error"
            result.error_details = {
                "error_type": type(e).__name__,
                "message": str(e),
                "timestamp": time.time()
            }
        
        finally:
            result.duration_seconds = time.time() - start_time
        
        return result
    
    def _classify_llm_error(self, error: LLMError) -> str:
        """Map LLM error types to status codes."""
        error_type = type(error).__name__
        
        mapping = {
            'RateLimitError': 'rate_limit',
            'AuthenticationError': 'api_error',
            'TimeoutError': 'timeout',
            'NetworkError': 'network_error',
            'InvalidModelError': 'invalid_model',
            'APIError': 'api_error'
        }
        
        return mapping.get(error_type, 'unknown_error')
    
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
        
        # Record run start with metadata
        config_snapshot = {
            'max_concurrent_requests': getattr(self.llm_client, 'max_concurrent_requests', None),
            'request_delay_seconds': getattr(self.llm_client, 'request_delay', None),
            'models': [model.name for model in self.llm_client.models],
            'prompts_count': len(self.discover_prompts()),
            'test_cases_count': len(self.discover_test_cases())
        }
        self.storage.start_run(run_id, total_experiments, config_snapshot)
        
        print(f"Starting asynchronous experimental run: {run_id}")
        print(f"Total combinations to test: {total_experiments}")
        print(f"Prompts: {len(self.discover_prompts())}")
        print(f"Test cases: {len(self.discover_test_cases())}")
        print(f"Models: {len(self.config.models or self.llm_client.get_available_models())}")
        print(f"Max concurrent requests: {self.llm_client.max_concurrent_requests}")
        print("-" * 60)
        
        successful_experiments = 0
        completed_experiments = 0
        
        # Create semaphore for progress reporting
        progress_lock = asyncio.Lock()
        
        async def run_and_store_experiment(prompt_file, test_case_file, model_name, experiment_index):
            """Execute single experiment and store result with progress tracking."""
            nonlocal successful_experiments, completed_experiments
            
            result = await self.run_single_experiment_async(prompt_file, test_case_file, model_name)
            
            # Store result in database (synchronously - SQLite handles this well)
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
            
            # Update progress with thread safety
            async with progress_lock:
                completed_experiments += 1
                if result.status == "success":
                    successful_experiments += 1
                    print(f"  [{completed_experiments}/{total_experiments}] ✓ {prompt_file.name} × {test_case_file.name} × {model_name} ({result.duration_seconds:.2f}s)")
                else:
                    print(f"  [{completed_experiments}/{total_experiments}] ✗ {prompt_file.name} × {test_case_file.name} × {model_name} - {result.status}")
                    if result.error_details:
                        error_msg = result.error_details.get('message', 'Unknown error')
                        print(f"    Error: {error_msg[:100]}{'...' if len(error_msg) > 100 else ''}")
            
            return result
        
        # Create tasks for all experiments
        tasks = [
            run_and_store_experiment(prompt_file, test_case_file, model_name, i)
            for i, (prompt_file, test_case_file, model_name) in enumerate(combinations, 1)
        ]
        
        # Execute all experiments concurrently
        try:
            await asyncio.gather(*tasks, return_exceptions=False)
        except Exception as e:
            print(f"\nExperiment batch encountered an error: {e}")
            print("Continuing with completed experiments...")
        
        print("-" * 60)
        print(f"Asynchronous experimental run completed: {run_id}")
        print(f"Successful experiments: {successful_experiments}/{total_experiments}")
        print(f"Success rate: {(successful_experiments/total_experiments)*100:.1f}%")
        
        # Mark run as completed
        self.storage.complete_run(run_id, successful_experiments)
        
        return run_id
    
    def run_experiments(self, run_id: str = None) -> str:
        """
        Execute the complete experimental matrix.
        
        This method orchestrates the systematic exploration of our
        experimental space, ensuring proper persistence and error recovery.
        
        Returns the run_id for the completed experiment batch.
        """
        if run_id is None:
            run_id = self.storage.generate_run_id()
        
        combinations = list(self.generate_experiment_combinations())
        total_experiments = len(combinations)
        
        # Record run start with metadata
        config_snapshot = {
            'request_delay_seconds': getattr(self.llm_client, 'request_delay', None),
            'models': [model.name for model in self.llm_client.models],
            'prompts_count': len(self.discover_prompts()),
            'test_cases_count': len(self.discover_test_cases()),
            'execution_mode': 'synchronous'
        }
        self.storage.start_run(run_id, total_experiments, config_snapshot)
        
        print(f"Starting synchronous experimental run: {run_id}")
        print("[LEGACY MODE] Using synchronous execution for backward compatibility")
        print(f"Total combinations to test: {total_experiments}")
        print(f"Prompts: {len(self.discover_prompts())}")
        print(f"Test cases: {len(self.discover_test_cases())}")
        print(f"Models: {len(self.config.models or self.llm_client.get_available_models())}")
        print("-" * 60)
        
        successful_experiments = 0
        
        for i, (prompt_file, test_case_file, model_name) in enumerate(combinations, 1):
            print(f"[{i}/{total_experiments}] Testing: {prompt_file.name} × {test_case_file.name} × {model_name}")
            
            result = self.run_single_experiment(prompt_file, test_case_file, model_name)
            
            # Store result in database
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
            
            if result.status == "success":
                successful_experiments += 1
                print(f"  ✓ Success ({result.duration_seconds:.2f}s)")
            else:
                print(f"  ✗ Failed: {result.status}")
                if result.error_details:
                    print(f"    Error: {result.error_details.get('message', 'Unknown error')}")
        
        print("-" * 60)
        print(f"Synchronous experimental run completed: {run_id}")
        print(f"Successful experiments: {successful_experiments}/{total_experiments}")
        print(f"Success rate: {(successful_experiments/total_experiments)*100:.1f}%")
        
        # Mark run as completed
        self.storage.complete_run(run_id, successful_experiments)
        
        return run_id
    
    def get_experiment_summary(self, run_id: str = None) -> Dict[str, Any]:
        """Get a statistical summary of experimental results."""
        if run_id is None:
            run_id = self.storage.get_latest_run_id()
            if not run_id:
                return {"error": "No experimental runs found"}
        
        return self.storage.get_run_summary(run_id)
