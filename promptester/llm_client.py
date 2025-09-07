"""
LLM Client abstraction layer.

This module provides a unified interface to various language models through LiteLLM,
treating each model as a function in the space of prompt transformations.

Dependencies:
    - litellm>=1.0.0: Core API abstraction layer providing unified access to all model providers

Environment Variables:
    - OPENAI_API_KEY: For OpenAI GPT models
    - ANTHROPIC_API_KEY: For Anthropic Claude models  
    - GEMINI_API_KEY: For Google Gemini models (primary)
    - GOOGLE_API_KEY: For Google Gemini models (fallback/compatibility)
"""

import json
import os
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

try:
    import litellm
    from litellm import completion, acompletion
except ImportError:
    raise ImportError(
        "LiteLLM is required but not installed. "
        "Please run: pip install litellm>=1.0.0"
    )



@dataclass
class ModelConfig:
    """Configuration for a language model endpoint."""
    name: str
    api_key: str


@dataclass
class LLMResponse:
    """Structured response from a language model invocation."""
    content: str
    model: str
    usage: Optional[Dict[str, Any]] = None
    finish_reason: Optional[str] = None


class LLMClient:
    """
    A unified client for multiple language model providers.
    
    This class abstracts the complexity of different API formats into
    a single, consistent interface that treats all models as functions
    in the same mathematical space.
    """
    
    def __init__(self, config_path: str = "config.json"):
        """Initialize client with configuration from JSON file."""
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.request_delay = self.config.get("request_delay_seconds", 1.0)
        self.max_concurrent_requests = self.config.get("max_concurrent_requests", 5)
        self.models = [ModelConfig(**model) for model in self.config.get("models", [])]
        self._setup_environment()
        
        # Rate limiting semaphore for async operations
        self._rate_limiter = asyncio.Semaphore(self.max_concurrent_requests)
        self._last_request_time = 0
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file with proper error handling."""
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {self.config_path}\n"
                f"Please copy config.template.json to config.json and configure your API keys."
            )
        
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file: {e}")
    
    def _setup_environment(self) -> None:
        """Configure environment variables for API access."""
        for model in self.models:
            # Set environment variables for LiteLLM
            if "gpt" in model.name.lower() or "openai" in model.name.lower():
                os.environ["OPENAI_API_KEY"] = model.api_key
            elif "claude" in model.name.lower() or "anthropic" in model.name.lower():
                os.environ["ANTHROPIC_API_KEY"] = model.api_key
            elif "gemini" in model.name.lower() or "google" in model.name.lower():
                # LiteLLM expects GEMINI_API_KEY for Gemini models
                # Set both for maximum compatibility
                os.environ["GEMINI_API_KEY"] = model.api_key
                os.environ["GOOGLE_API_KEY"] = model.api_key
            # Add more provider mappings as needed
    
    def get_available_models(self) -> List[str]:
        """Return list of configured model names."""
        return [model.name for model in self.models]
    
    async def complete_async(
        self,
        system_message: str,
        user_message: str,
        model_name: str,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Asynchronous completion using litellm's async interface.
        
        This method implements true concurrent processing while maintaining
        rate limiting through semaphores, creating an antifragile system
        that can handle multiple simultaneous requests elegantly.
        """
        if model_name not in self.get_available_models():
            raise ValueError(
                f"Model '{model_name}' not found in configuration. "
                f"Available models: {self.get_available_models()}"
            )
        
        async with self._rate_limiter:
            # Apply rate limiting delay in async manner
            current_time = time.time()
            if hasattr(self, '_last_request_time'):
                elapsed = current_time - self._last_request_time
                if elapsed < self.request_delay:
                    delay_needed = self.request_delay - elapsed
                    print(f"⏳ Rate limiting: waiting {delay_needed:.1f}s for {model_name}")
                    await asyncio.sleep(delay_needed)

            self._last_request_time = time.time()
            
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ]
            
            completion_kwargs = {
                "model": model_name,
                "messages": messages,
                "temperature": temperature,
                **kwargs
            }
            
            if max_tokens is not None:
                completion_kwargs["max_tokens"] = max_tokens
            
            try:
                # Use litellm's async completion
                response = await acompletion(**completion_kwargs)
                
                # Extract response content
                content = response.choices[0].message.content
                
                return LLMResponse(
                    content=content,
                    model=response.model,
                    usage=response.usage.model_dump() if hasattr(response.usage, 'model_dump') else dict(response.usage) if response.usage else None,
                    finish_reason=response.choices[0].finish_reason
                )
                
            except Exception as e:
                # Re-raise with additional context
                raise self._classify_error(e, model_name)
    
    def complete(
        self,
        system_message: str,
        user_message: str,
        model_name: str,
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate a completion using the specified model.
        
        This method treats the language model as a pure function that maps
        (system_prompt, user_prompt) -> response, maintaining referential
        transparency where possible through low temperature settings.
        """
        if model_name not in self.get_available_models():
            raise ValueError(
                f"Model '{model_name}' not found in configuration. "
                f"Available models: {self.get_available_models()}"
            )
        
        
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]
        
        completion_kwargs = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            **kwargs
        }
        
        if max_tokens is not None:
            completion_kwargs["max_tokens"] = max_tokens
        
        try:
            # Apply rate limiting delay
            if hasattr(self, '_last_request_time'):
                elapsed = time.time() - self._last_request_time
                if elapsed < self.request_delay:
                    time.sleep(self.request_delay - elapsed)
            
            response = completion(**completion_kwargs)
            self._last_request_time = time.time()
            
            # Extract response content
            content = response.choices[0].message.content
            
            return LLMResponse(
                content=content,
                model=response.model,
                usage=response.usage.model_dump() if hasattr(response.usage, 'model_dump') else dict(response.usage) if response.usage else None,
                finish_reason=response.choices[0].finish_reason
            )
            
        except Exception as e:
            # Re-raise with additional context
            raise self._classify_error(e, model_name)
    
    def _classify_error(self, error: Exception, model_name: str) -> Exception:
        """
        Classify and enhance error information for better debugging.
        
        This method transforms various API errors into a standardized
        error taxonomy for consistent handling upstream.
        """
        error_str = str(error).lower()
        
        # Gemini-specific error handling
        if "gemini" in model_name.lower():
            if "gemini_api_key" in error_str or "google_api_key" in error_str:
                return AuthenticationError(
                    f"Gemini API key not set. Please ensure GEMINI_API_KEY and GOOGLE_API_KEY "
                    f"environment variables are set for model {model_name}: {error}"
                )
            elif "quota exceeded" in error_str or "billing" in error_str:
                return RateLimitError(
                    f"Gemini API quota exceeded or billing issue for model {model_name}. "
                    f"Check your Google Cloud billing and API quotas: {error}"
                )
        
        # General error classification
        if "rate limit" in error_str or "429" in error_str:
            return RateLimitError(f"Rate limit exceeded for model {model_name}: {error}")
        elif "api key" in error_str or "authentication" in error_str or "401" in error_str:
            return AuthenticationError(f"Authentication failed for model {model_name}: {error}")
        elif "timeout" in error_str:
            return TimeoutError(f"Request timeout for model {model_name}: {error}")
        elif "network" in error_str or "connection" in error_str:
            return NetworkError(f"Network error for model {model_name}: {error}")
        elif "model" in error_str and ("not found" in error_str or "invalid" in error_str):
            return InvalidModelError(f"Invalid model {model_name}: {error}")
        else:
            return APIError(f"API error for model {model_name}: {error}")


# Custom exception classes for better error handling
class LLMError(Exception):
    """Base exception for LLM-related errors."""
    pass


class RateLimitError(LLMError):
    """Raised when API rate limits are exceeded."""
    pass


class AuthenticationError(LLMError):
    """Raised when API authentication fails."""
    pass


class TimeoutError(LLMError):
    """Raised when requests timeout."""
    pass


class NetworkError(LLMError):
    """Raised when network connectivity issues occur."""
    pass


class InvalidModelError(LLMError):
    """Raised when an invalid model is specified."""
    pass


class APIError(LLMError):
    """Raised for general API errors."""
    pass
