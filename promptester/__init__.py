"""
Prompt Tester - A systematic framework for AI prompt optimization.

This package provides a mathematically rigorous approach to testing and
optimizing system prompts for AI programming assistants through controlled
experimentation across the Cartesian product of prompts, test cases, and models.
"""

__version__ = "1.0.0"
__author__ = "The Axiomatic Sage"

from .storage import ExperimentStorage
from .llm_client import LLMClient, LLMResponse
from .test_runner import TestRunner, ExperimentConfig
from .cli import PromptTesterCLI

__all__ = [
    "ExperimentStorage",
    "LLMClient", 
    "LLMResponse",
    "TestRunner",
    "ExperimentConfig", 
    "PromptTesterCLI"
]
