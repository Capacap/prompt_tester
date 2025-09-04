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
python -m src validate
```

### 4. Run Experiments

```bash
# Execute all prompt/test case/model combinations
python -m src run

# View latest results
python -m src latest

# View detailed results
python -m src results
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
├── src/                  # Framework implementation
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
# Run all combinations
python -m src run

# Run specific models only
python -m src run --models gpt-4 claude-3-opus-20240229
```

#### View Results
```bash
# Latest run summary
python -m src latest

# Detailed results (latest run)
python -m src results

# Specific run results
python -m src results --run-id=abc123

# Filter by status
python -m src results --status=success
python -m src results --status=failed

# Different output formats
python -m src results --format=json
python -m src results --format=summary
```

#### Manage Runs
```bash
# List all experimental runs
python -m src list-runs

# Validate setup
python -m src validate
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

### Programmatic Access

```python
from src import TestRunner, ExperimentConfig, ExperimentStorage

# Configure experiment
config = ExperimentConfig(
    models=["gpt-4", "claude-3-opus-20240229"]
)

# Run experiments
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
- **Modular Design**: Components are loosely coupled and independently testable
- **Extensible Framework**: New models and test types integrate seamlessly
- **Efficient Storage**: Optimized database schema with proper indexing

## Contributing

When extending the framework:

1. **Maintain Immutability**: Preserve existing data structures
2. **Follow Constraints**: Respect database schema and API contracts
3. **Test Thoroughly**: Validate changes against existing functionality
4. **Document Changes**: Update this README and inline documentation

## License

This framework is designed for systematic prompt optimization research and development.
