# Prompt Tester

A systematic framework for testing and optimizing AI assistant prompts through controlled experimentation across the Cartesian product of prompts, test cases, and language models.

## Overview

This framework treats prompt optimization as a formal experimental process, exploring the solution manifold defined by **Prompts × Test Cases × Models**. Each combination represents a point in our experimental space, enabling rigorous comparative analysis of prompt effectiveness.

## Quick Start

### 1. Installation

```bash
# Clone or create the project
cd prompt_tester

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy the template configuration
cp config.template.json config.json

# Edit config.json with your API keys
```

Example configuration:
```json
{
  "request_delay_seconds": 1.0,
  "max_concurrent_requests": 5,
  "models": [
    {
      "name": "gpt-4",
      "api_key": "your-openai-api-key"
    },
    {
      "name": "claude-3-opus-20240229", 
      "api_key": "your-anthropic-api-key"
    }
  ]
}
```

### 3. Validate Setup

```bash
python -m promptester validate
```

### 4. Run Experiments

```bash
# Execute all prompt/test case/model combinations (async, fast)
python -m promptester run

# Execute with custom concurrency settings
python -m promptester run --max-concurrent=10

# Execute in legacy sequential mode
python -m promptester run --sync

# View latest results
python -m promptester latest

# View detailed results
python -m promptester results
```

## Architecture

### Core Components

- **Storage Layer** (`storage.py`): SQLite-based persistence with formal schema constraints
- **LLM Client** (`llm_client.py`): Unified interface to multiple language model APIs
- **Test Runner** (`test_runner.py`): Experimental execution engine
- **CLI Interface** (`cli.py`): Command-line interface for system interaction

### Directory Structure

```
prompt_tester/
├── prompts/              # System prompts (.md files)
│   ├── assistant.v1.md
│   ├── assistant.v2.md
│   └── assistant.v3.md
├── test_cases/           # Test scenarios (.md files)
│   ├── code_review_python_function.md
│   ├── debug_memory_leak.md
│   ├── refactoring_suggestions.md
│   ├── algorithm_optimization.md
│   └── design_pattern_advice.md
├── promptester/          # Framework implementation
│   ├── storage.py
│   ├── llm_client.py
│   ├── test_runner.py
│   └── cli.py
├── config.json          # Configuration (gitignored)
├── results.db           # Experimental results
└── requirements.txt
```

### Data Model

Each experimental result contains:
- **Identifiers**: run_id, prompt_file, test_case_file, model_name
- **Content**: system_message, user_message, response_content
- **Metadata**: timestamp, status, error_details
- **Constraints**: Unique constraint on (run_id, prompt_file, test_case_file, model_name)

## Usage

### Adding Prompts

Create `.md` files in the `prompts/` directory. Each file contains a complete system prompt:

```markdown
# prompts/assistant.v4.md
You are an expert code reviewer with a focus on security and performance...
```

### Adding Test Cases

Create `.md` files in the `test_cases/` directory. Each file contains a user query:

```markdown
# test_cases/security_review.md
Please review this authentication function for security vulnerabilities:

```python
def authenticate_user(username, password):
    # ... code here
```

### CLI Commands

#### Run Experiments
```bash
# Run all combinations (asynchronous, high-performance)
python -m promptester run

# Run with custom concurrency limit
python -m promptester run --max-concurrent=10

# Run in sequential mode (legacy compatibility)
python -m promptester run --sync

# Run specific models only
python -m promptester run --models gpt-4 claude-3-opus-20240229

# Combine options for fine-tuned control
python -m promptester run --models gpt-4 --max-concurrent=3
```

#### View Results
```bash
# Latest run summary
python -m promptester latest

# Detailed results (latest run)
python -m promptester results

# Specific run results
python -m promptester results --run-id=abc123

# Filter by status
python -m promptester results --status=success
python -m promptester results --status=failed

# Different output formats
python -m promptester results --format=json
python -m promptester results --format=summary

# Export results (defaults to latest run)
python -m promptester export
python -m promptester export --run-id=abc123
python -m promptester export --status=success
```

#### Manage Runs
```bash
# List all experimental runs
python -m promptester list-runs

# Validate setup
python -m promptester validate
```

## Experimental Design

### Systematic Exploration

The framework generates the complete Cartesian product:
- **P** prompts × **T** test cases × **M** models = **P×T×M** experiments

Each experiment is an atomic unit that:
1. Loads a system prompt from `prompts/`
2. Loads a user message from `test_cases/`
3. Sends both to a specified model
4. Records the response and metadata

### Error Handling

The system maintains experimental integrity through:
- **Graceful Degradation**: Individual failures don't stop the experiment
- **Structured Error Classification**: API errors, timeouts, rate limits, etc.
- **Complete Recording**: All attempts are stored regardless of success/failure
- **Rate Limiting**: Configurable delays prevent API violations

### Result Analysis

Results can be analyzed through:
- **Status Filtering**: Compare success rates across prompts/models
- **Content Analysis**: Examine response quality and consistency
- **Performance Metrics**: Analyze response times and error patterns
- **Comparative Studies**: A/B testing between prompt versions

## Example Workflow

1. **Design Phase**: Create multiple prompt variations in `prompts/`
2. **Test Development**: Create diverse test cases in `test_cases/`
3. **Execution**: Run experiments across all combinations
4. **Analysis**: Compare results to identify optimal prompts
5. **Iteration**: Refine prompts based on empirical evidence

## Advanced Usage

### Custom Model Configuration

Add new models to `config.json`:
```json
{
  "request_delay_seconds": 1.0,
  "max_concurrent_requests": 5,
  "models": [
    {
      "name": "gpt-3.5-turbo",
      "api_key": "your-key"
    },
    {
      "name": "gemini-pro",
      "api_key": "your-google-key"
    }
  ]
}
```

### Performance Configuration

- **max_concurrent_requests**: Controls how many API requests run simultaneously (default: 5)
- **request_delay_seconds**: Minimum delay between requests for rate limiting (default: 1.0)

Optimal settings depend on your API rate limits and system capacity. Higher concurrency increases throughput but may trigger rate limiting.

### Programmatic Access

```python
import asyncio
from promptester import TestRunner, ExperimentConfig, ExperimentStorage

# Configure experiment
config = ExperimentConfig(
    models=["gpt-4", "claude-3-opus-20240229"]
)

# Run experiments asynchronously (recommended)
async def run_async_experiments():
    runner = TestRunner(config)
    run_id = await runner.run_experiments_async()
    return run_id

# Execute async experiments
run_id = asyncio.run(run_async_experiments())

# Or run synchronously (legacy mode)
runner = TestRunner(config)
run_id = runner.run_experiments()

# Analyze results
storage = ExperimentStorage()
results = storage.get_results_by_run(run_id)
```

## Theoretical Foundation

This framework embodies several key principles:

### Experimental Rigor
- **Reproducibility**: Identical inputs produce identical experiments
- **Isolation**: Each test is independent and atomic
- **Completeness**: All combinations are systematically explored

### Data Integrity
- **Immutable Records**: Experimental results are never modified
- **Referential Transparency**: Clear mapping between inputs and outputs
- **Formal Constraints**: Database schema enforces data consistency

### Scalable Architecture
- **Asynchronous Execution**: Concurrent request processing with intelligent rate limiting
- **Modular Design**: Components are loosely coupled and independently testable
- **Extensible Framework**: New models and test types integrate seamlessly
- **Efficient Storage**: Optimized database schema with proper indexing
- **Antifragile Concurrency**: System becomes more efficient under load through elegant parallelization

## Contributing

When extending the framework:

1. **Maintain Immutability**: Preserve existing data structures
2. **Follow Constraints**: Respect database schema and API contracts
3. **Test Thoroughly**: Validate changes against existing functionality
4. **Document Changes**: Update this README and inline documentation

## License

This framework is designed for systematic prompt optimization research and development.
