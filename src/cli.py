"""
Command-line interface for the prompt testing framework.

This module provides the user interface for interacting with our experimental
system, treating each command as a formal operation on the experimental manifold.
"""

import sys
import argparse
import asyncio
from pathlib import Path
from typing import List, Dict, Any
import json
from datetime import datetime

from .storage import ExperimentStorage
from .test_runner import TestRunner, ExperimentConfig
from .llm_client import LLMClient


class PromptTesterCLI:
    """
    Command-line interface for systematic prompt testing.
    
    This class provides a structured interface to our experimental framework,
    enabling users to execute experiments and analyze results through
    well-defined command operations.
    """
    
    def __init__(self):
        """Initialize the CLI with proper argument parsing."""
        self.parser = self._create_parser()
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """Create the argument parser with all available commands."""
        parser = argparse.ArgumentParser(
            prog="prompt_tester",
            description="Systematic testing and optimization of AI assistant prompts",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  python -m src.cli run                    # Run all experiments (async, fast)
  python -m src.cli run --sync             # Run experiments sequentially (legacy)
  python -m src.cli run --max-concurrent=10  # Override concurrency limit
  python -m src.cli results               # View latest results  
  python -m src.cli results --run-id=abc  # View specific run
  python -m src.cli latest                # Show latest run summary
  python -m src.cli list-runs             # List all experimental runs
  python -m src.cli export                # Export latest results to file
  python -m src.cli export --run-id=abc   # Export specific run to file
            """
        )
        
        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        
        # Run experiments command
        run_parser = subparsers.add_parser('run', help='Execute experimental matrix')
        run_parser.add_argument(
            '--models', 
            nargs='*', 
            help='Specific models to test (default: all configured models)'
        )
        run_parser.add_argument(
            '--config', 
            default='config.json',
            help='Configuration file path (default: config.json)'
        )
        run_parser.add_argument(
            '--async', 
            action='store_true',
            default=True,
            help='Use asynchronous concurrent execution (default: True)'
        )
        run_parser.add_argument(
            '--sync', 
            action='store_true',
            help='Force synchronous sequential execution (legacy mode)'
        )
        run_parser.add_argument(
            '--max-concurrent',
            type=int,
            help='Override max concurrent requests from config'
        )
        
        # View results command
        results_parser = subparsers.add_parser('results', help='View experimental results')
        results_parser.add_argument(
            '--run-id', 
            help='Specific run ID to display (default: latest run)'
        )
        results_parser.add_argument(
            '--format', 
            choices=['table', 'json', 'summary'], 
            default='table',
            help='Output format (default: table)'
        )
        results_parser.add_argument(
            '--status',
            choices=['all', 'success', 'failed'],
            default='all',
            help='Filter by result status (default: all)'
        )
        
        # Latest results command (shortcut)
        subparsers.add_parser('latest', help='Show latest run summary')
        
        # List runs command
        list_parser = subparsers.add_parser('list-runs', help='List all experimental runs')
        list_parser.add_argument(
            '--format',
            choices=['table', 'json'],
            default='table',
            help='Output format (default: table)'
        )
        
        # Validate configuration command
        subparsers.add_parser('validate', help='Validate configuration and setup')
        
        # Export results command
        export_parser = subparsers.add_parser('export', help='Export experimental results to file')
        export_parser.add_argument(
            '--run-id', 
            help='Specific run ID to export (default: latest run)'
        )
        export_parser.add_argument(
            '--output', 
            '-o',
            help='Output file path (default: exports/results_<run_id>.txt)'
        )
        export_parser.add_argument(
            '--status',
            choices=['all', 'success', 'failed'],
            default='all',
            help='Filter by result status (default: all)'
        )
        
        
        return parser
    
    def run(self, args: List[str] = None) -> int:
        """Main entry point for CLI execution."""
        if args is None:
            args = sys.argv[1:]
        
        parsed_args = self.parser.parse_args(args)
        
        if not parsed_args.command:
            self.parser.print_help()
            return 1
        
        try:
            if parsed_args.command == 'run':
                return self._run_experiments(parsed_args)
            elif parsed_args.command == 'results':
                return self._show_results(parsed_args)
            elif parsed_args.command == 'latest':
                return self._show_latest(parsed_args)
            elif parsed_args.command == 'list-runs':
                return self._list_runs(parsed_args)
            elif parsed_args.command == 'validate':
                return self._validate_setup(parsed_args)
            elif parsed_args.command == 'export':
                return self._export_results(parsed_args)
            else:
                print(f"Unknown command: {parsed_args.command}")
                return 1
                
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
    
    def _run_experiments(self, args) -> int:
        """Execute the experimental matrix with async or sync mode."""
        print("Initializing experimental framework...")
        
        config = ExperimentConfig(
            models=args.models,
            config_path=args.config
        )
        
        runner = TestRunner(config)
        
        # Override concurrent requests if specified
        if hasattr(args, 'max_concurrent') and args.max_concurrent:
            runner.llm_client.max_concurrent_requests = args.max_concurrent
            # Update the semaphore
            runner.llm_client._rate_limiter = asyncio.Semaphore(args.max_concurrent)
        
        # Determine execution mode
        use_async = not args.sync if hasattr(args, 'sync') else True
        
        try:
            if use_async:
                print("Using asynchronous concurrent execution for optimal performance...")
                run_id = asyncio.run(runner.run_experiments_async())
            else:
                print("Using synchronous sequential execution (legacy mode)...")
                run_id = runner.run_experiments()
            
            print(f"\nExperimental run completed successfully.")
            print(f"Run ID: {run_id}")
            print(f"\nTo view results: python -m src.cli results --run-id={run_id}")
            return 0
            
        except KeyboardInterrupt:
            print("\nExperiment interrupted by user.")
            return 1
        except Exception as e:
            print(f"Experiment failed: {e}")
            return 1
    
    def _show_results(self, args) -> int:
        """Display experimental results."""
        storage = ExperimentStorage()
        
        if args.run_id:
            results = storage.get_results_by_run(args.run_id)
            if not results:
                print(f"No results found for run ID: {args.run_id}")
                return 1
        else:
            results = storage.get_latest_results()
            if not results:
                print("No experimental results found.")
                return 1
        
        # Filter by status if requested
        if args.status != 'all':
            if args.status == 'success':
                results = [r for r in results if r['status'] == 'success']
            elif args.status == 'failed':
                results = [r for r in results if r['status'] != 'success']
        
        # Display results in requested format
        if args.format == 'json':
            print(json.dumps(results, indent=2, default=str))
        elif args.format == 'summary':
            self._print_results_summary(results)
        else:  # table format
            self._print_results_table(results)
        
        return 0
    
    def _show_latest(self, args) -> int:
        """Show summary of the most recent experimental run."""
        storage = ExperimentStorage()
        
        latest_run_id = storage.get_latest_run_id()
        if not latest_run_id:
            print("No experimental runs found.")
            return 1
        
        summary = storage.get_run_summary(latest_run_id)
        results = storage.get_latest_results()
        
        print(f"Latest Experimental Run: {latest_run_id}")
        print("=" * 60)
        print(f"Total experiments: {summary.get('total_experiments', 0)}")
        print(f"Successful: {summary.get('successful', 0)}")
        print(f"Success rate: {(summary.get('successful', 0) / max(summary.get('total_experiments', 1), 1) * 100):.1f}%")
        print(f"Unique prompts: {summary.get('unique_prompts', 0)}")
        print(f"Unique test cases: {summary.get('unique_test_cases', 0)}")
        print(f"Configured models: {summary.get('unique_models', 0)}")
        print(f"Response models: {summary.get('unique_response_models', 0)}")
        
        # Show enhanced timing information
        run_start = summary.get('run_started_timestamp', summary.get('first_experiment_time', 'Unknown'))
        run_end = summary.get('run_completed_timestamp', summary.get('last_experiment_time', 'Unknown'))
        print(f"Run started: {run_start}")
        print(f"Run completed: {run_end}")
        
        # Show configuration snapshot if available
        config_snapshot = summary.get('config_snapshot')
        if config_snapshot:
            print(f"\nConfiguration:")
            if 'max_concurrent_requests' in config_snapshot:
                print(f"  Max concurrent requests: {config_snapshot['max_concurrent_requests']}")
            if 'request_delay_seconds' in config_snapshot:
                print(f"  Request delay: {config_snapshot['request_delay_seconds']}s")
            if 'execution_mode' in config_snapshot:
                print(f"  Execution mode: {config_snapshot['execution_mode']}")
        
        # Show status breakdown
        status_counts = {}
        for result in results:
            status = result['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        if status_counts:
            print("\nStatus Breakdown:")
            for status, count in sorted(status_counts.items()):
                print(f"  {status}: {count}")
        
        return 0
    
    def _list_runs(self, args) -> int:
        """List all experimental runs."""
        storage = ExperimentStorage()
        run_ids = storage.get_all_run_ids()
        
        if not run_ids:
            print("No experimental runs found.")
            return 1
        
        if args.format == 'json':
            run_data = []
            for run_id in run_ids:
                summary = storage.get_run_summary(run_id)
                summary['run_id'] = run_id
                run_data.append(summary)
            print(json.dumps(run_data, indent=2, default=str))
        else:
            print("Experimental Runs:")
            print("-" * 60)
            for run_id in run_ids:
                summary = storage.get_run_summary(run_id)
                success_rate = (summary.get('successful', 0) / max(summary.get('total_experiments', 1), 1) * 100)
                print(f"{run_id}: {summary.get('successful', 0)}/{summary.get('total_experiments', 0)} ({success_rate:.1f}%) - {summary.get('start_time', 'Unknown')}")
        
        return 0
    
    def _validate_setup(self, args) -> int:
        """Validate the experimental setup and configuration."""
        print("Validating experimental setup...")
        
        # Check directory structure
        required_dirs = ['prompts', 'test_cases', 'src']
        for dir_name in required_dirs:
            dir_path = Path(dir_name)
            if dir_path.exists():
                print(f"✓ Directory {dir_name} exists")
            else:
                print(f"✗ Directory {dir_name} missing")
                return 1
        
        # Check for prompt and test case files
        prompts_dir = Path('prompts')
        test_cases_dir = Path('test_cases')
        
        prompt_files = list(prompts_dir.glob('*.md')) if prompts_dir.exists() else []
        test_case_files = list(test_cases_dir.glob('*.md')) if test_cases_dir.exists() else []
        
        print(f"✓ Found {len(prompt_files)} prompt files")
        print(f"✓ Found {len(test_case_files)} test case files")
        
        if not prompt_files:
            print("⚠ Warning: No prompt files found in prompts/ directory")
        
        if not test_case_files:
            print("⚠ Warning: No test case files found in test_cases/ directory")
        
        # Check configuration
        config_path = Path('config.json')
        if config_path.exists():
            print("✓ Configuration file exists")
            try:
                client = LLMClient('config.json')
                models = client.get_available_models()
                print(f"✓ Found {len(models)} configured models: {', '.join(models)}")
            except Exception as e:
                print(f"✗ Configuration error: {e}")
                return 1
        else:
            print("✗ Configuration file (config.json) not found")
            print("  Please copy config.template.json to config.json and configure your API keys")
            return 1
        
        print("\nSetup validation completed successfully!")
        return 0
    
    def _export_results(self, args) -> int:
        """Export experimental results to a text file."""
        storage = ExperimentStorage()
        
        # Get results
        if args.run_id:
            results = storage.get_results_by_run(args.run_id)
            run_id = args.run_id
            if not results:
                print(f"No results found for run ID: {args.run_id}")
                return 1
        else:
            results = storage.get_latest_results()
            run_id = storage.get_latest_run_id()
            if not results:
                print("No experimental results found.")
                return 1
        
        # Filter by status if requested
        if args.status != 'all':
            if args.status == 'success':
                results = [r for r in results if r['status'] == 'success']
            elif args.status == 'failed':
                results = [r for r in results if r['status'] != 'success']
        
        # Determine output file path with default export directory
        if args.output:
            output_path = Path(args.output)
        else:
            # Create default export directory if it doesn't exist
            export_dir = Path("exports")
            export_dir.mkdir(exist_ok=True)
            output_path = export_dir / f"results_{run_id[:8]}.txt"
        
        # Get enhanced run metadata
        run_summary = storage.get_run_summary(run_id)
        
        # Export results with comprehensive metadata
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"# Experimental Results Export\n")
                f.write(f"# Run ID: {run_id}\n")
                f.write(f"# Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# Total Results: {len(results)}\n")
                f.write(f"# Status Filter: {args.status}\n")
                f.write(f"#\n")
                f.write(f"# === RUN METADATA ===\n")
                
                # Run timing information
                run_start = run_summary.get('run_started_timestamp', run_summary.get('first_experiment_time', 'Unknown'))
                run_end = run_summary.get('run_completed_timestamp', run_summary.get('last_experiment_time', 'Unknown'))
                f.write(f"# Run Started: {run_start}\n")
                f.write(f"# Run Completed: {run_end}\n")
                
                # Run statistics
                total_experiments = run_summary.get('total_experiments', len(results))
                successful = run_summary.get('successful', len([r for r in results if r['status'] == 'success']))
                success_rate = (successful / max(total_experiments, 1)) * 100
                f.write(f"# Success Rate: {successful}/{total_experiments} ({success_rate:.1f}%)\n")
                f.write(f"# Unique Prompts: {run_summary.get('unique_prompts', 'Unknown')}\n")
                f.write(f"# Unique Test Cases: {run_summary.get('unique_test_cases', 'Unknown')}\n")
                f.write(f"# Configured Models: {run_summary.get('unique_models', 'Unknown')}\n")
                f.write(f"# Response Models: {run_summary.get('unique_response_models', 'Unknown')}\n")
                
                # Configuration snapshot
                config_snapshot = run_summary.get('config_snapshot')
                if config_snapshot:
                    f.write(f"#\n")
                    f.write(f"# === CONFIGURATION SNAPSHOT ===\n")
                    if 'max_concurrent_requests' in config_snapshot:
                        f.write(f"# Max Concurrent Requests: {config_snapshot['max_concurrent_requests']}\n")
                    if 'request_delay_seconds' in config_snapshot:
                        f.write(f"# Request Delay: {config_snapshot['request_delay_seconds']}s\n")
                    if 'execution_mode' in config_snapshot:
                        f.write(f"# Execution Mode: {config_snapshot['execution_mode']}\n")
                    if 'models' in config_snapshot:
                        f.write(f"# Configured Models: {', '.join(config_snapshot['models'])}\n")
                    if 'prompts_count' in config_snapshot:
                        f.write(f"# Prompts Count: {config_snapshot['prompts_count']}\n")
                    if 'test_cases_count' in config_snapshot:
                        f.write(f"# Test Cases Count: {config_snapshot['test_cases_count']}\n")
                
                f.write(f"#\n")
                f.write(f"# === EXPERIMENTAL RESULTS ===\n")
                f.write(f"#\n\n")
                
                for i, result in enumerate(results, 1):
                    f.write("---\n\n")
                    
                    # Experiment header with metadata
                    f.write(f"EXPERIMENT {i}/{len(results)}\n")
                    f.write(f"TIMESTAMP: {result.get('timestamp', 'Unknown')}\n")
                    f.write(f"STATUS: {result['status']}\n")
                    f.write(f"\n")
                    
                    # Test case name
                    test_case_name = Path(result['test_case_file']).stem
                    f.write(f"TEST CASE: {test_case_name}\n")

                    # Model information
                    config_model_name = Path(result['model_name']).stem
                    f.write(f"CONFIGURED MODEL: {config_model_name}\n")
                    
                    response_model_name = result.get('response_model_name')
                    if response_model_name:
                        if response_model_name != result['model_name']:
                            f.write(f"RESPONSE MODEL: {response_model_name} ⚠️  (differs from config)\n")
                        else:
                            f.write(f"RESPONSE MODEL: {response_model_name} ✓ (matches config)\n")
                    else:
                        f.write(f"RESPONSE MODEL: Not captured\n")

                    # Prompt file name
                    prompt_file = Path(result['prompt_file']).stem
                    f.write(f"PROMPT FILE: {prompt_file}\n\n")

                    # System message
                    f.write(f"SYSTEM MESSAGE:\n{result['system_message']}\n\n")
                    
                    # User message
                    f.write(f"USER MESSAGE:\n{result['user_message']}\n\n")
                    
                    # Response content (or error message if failed)
                    if result['status'] == 'success' and result['response_content']:
                        f.write(f"ASSISTANT MESSAGE:\n{result['response_content']}\n\n")
                    else:
                        f.write(f"[EXPERIMENT FAILED - Status: {result['status']}]\n")
                        if result.get('error_details'):
                            # Parse error details if it's JSON
                            error_info = result['error_details']
                            if isinstance(error_info, str):
                                try:
                                    error_info = json.loads(error_info)
                                except json.JSONDecodeError:
                                    pass
                            if isinstance(error_info, dict):
                                f.write(f"Error: {error_info.get('message', 'Unknown error')}\n")
                            else:
                                f.write(f"Error: {error_info}\n")
                        f.write("\n")
                
                f.write("---\n")
            
            print(f"✓ Exported {len(results)} results to: {output_path}")
            print(f"  Run ID: {run_id}")
            print(f"  Run started: {run_summary.get('run_started_timestamp', 'Unknown')}")
            print(f"  Run completed: {run_summary.get('run_completed_timestamp', 'Unknown')}")
            print(f"  Status filter: {args.status}")
            print(f"  Success rate: {run_summary.get('successful', 0)}/{run_summary.get('total_experiments', len(results))} experiments")
            
            # Show configuration info if available
            config_snapshot = run_summary.get('config_snapshot')
            if config_snapshot and config_snapshot.get('max_concurrent_requests'):
                print(f"  Execution mode: {'Async' if config_snapshot.get('max_concurrent_requests', 0) > 1 else 'Sync'} ({config_snapshot.get('max_concurrent_requests', 1)} concurrent)")
            
            return 0
            
        except Exception as e:
            print(f"Error writing export file: {e}")
            return 1
    
    
    def _print_results_table(self, results: List[Dict[str, Any]]) -> None:
        """Print results in a formatted table."""
        if not results:
            print("No results to display.")
            return
        
        print(f"Results ({len(results)} experiments):")
        print("-" * 120)
        print(f"{'Prompt':<20} {'Test Case':<20} {'Config Model':<18} {'Response Model':<18} {'Status':<10}")
        print("-" * 120)
        
        for result in results:
            prompt = result['prompt_file'][:19]
            test_case = result['test_case_file'][:19]
            config_model = result['model_name'][:17]
            response_model = (result.get('response_model_name') or 'N/A')[:17]
            status = result['status']
            
            print(f"{prompt:<20} {test_case:<20} {config_model:<18} {response_model:<18} {status:<10}")
    
    def _print_results_summary(self, results: List[Dict[str, Any]]) -> None:
        """Print a statistical summary of results."""
        if not results:
            print("No results to display.")
            return
        
        total = len(results)
        successful = len([r for r in results if r['status'] == 'success'])
        
        print(f"Results Summary ({total} experiments):")
        print(f"Success rate: {successful}/{total} ({(successful/total)*100:.1f}%)")
        
        # Status breakdown
        status_counts = {}
        for result in results:
            status = result['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print("\nStatus breakdown:")
        for status, count in sorted(status_counts.items()):
            print(f"  {status}: {count} ({(count/total)*100:.1f}%)")


def main():
    """Entry point for the CLI application."""
    cli = PromptTesterCLI()
    return cli.run()


if __name__ == "__main__":
    sys.exit(main())
