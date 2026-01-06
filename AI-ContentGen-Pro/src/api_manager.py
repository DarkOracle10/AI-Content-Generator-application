"""Enterprise-grade OpenAI API manager with comprehensive error handling.

This module provides a production-ready interface to the OpenAI API with:
- Automatic retry logic with exponential backoff
- Comprehensive error handling and custom exceptions
- Request/response logging with security redaction
- Cost tracking and usage statistics
- Batch generation with parallel processing
- Response caching and connection pooling
- Monitoring hooks for observability

Example Usage:
    >>> from src.api_manager import OpenAIManager, create_manager
    >>> 
    >>> # Create manager with defaults from config
    >>> manager = create_manager()
    >>> 
    >>> # Validate API key
    >>> if manager.validate_api_key():
    ...     print("API key is valid")
    >>> 
    >>> # Estimate cost before generation
    >>> cost = manager.estimate_cost("Write a blog post about AI")
    >>> print(f"Estimated cost: ${cost['total_cost']:.4f}")
    >>> 
    >>> # Generate content
    >>> result = manager.generate_content(
    ...     prompt="Write a short blog intro about AI",
    ...     system_message="You are a tech blogger",
    ...     max_tokens=200
    ... )
    >>> if result['success']:
    ...     print(result['content'])
    ...     print(f"Cost: ${result['cost']:.4f}")
    >>> 
    >>> # Batch generation
    >>> prompts = ["Write about cats", "Write about dogs"]
    >>> results = manager.generate_batch(prompts, parallel=True)
    >>> 
    >>> # Get usage statistics
    >>> stats = manager.get_usage_statistics()
    >>> print(f"Total requests: {stats['total_requests']}")
    >>> print(f"Total cost: ${stats['total_cost']:.4f}")

Author: AI-ContentGen-Pro Team
Version: 2.0.0
"""

import asyncio
import functools
import hashlib
import logging
import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Protocol,
    Tuple,
    TypeVar,
    Union,
)

import tiktoken
from openai import OpenAI, APIError as OpenAIAPIError, APIConnectionError, RateLimitError, AuthenticationError

from .config import (
    API_TIMEOUT,
    RETRY_ATTEMPTS,
    RETRY_DELAY,
    MODEL_COSTS,
    load_config,
    ConfigurationError,
)

# Configure module logger
logger = logging.getLogger(__name__)

# Type variable for generic retry decorator
T = TypeVar("T")


# =============================================================================
# CONSTANTS
# =============================================================================

# Default configuration
DEFAULT_REQUEST_TIMEOUT: int = 30
EXTENDED_REQUEST_TIMEOUT: int = 45
MAX_CONCURRENT_REQUESTS: int = 3
CACHE_TTL_SECONDS: int = 3600  # 1 hour
API_KEY_VALIDATION_CACHE_TTL: int = 3600  # 1 hour

# Retry configuration
MAX_RETRY_ATTEMPTS: int = 3
BASE_RETRY_DELAY: float = 2.0  # seconds
RETRY_BACKOFF_MULTIPLIER: float = 2.0

# Token estimation
AVG_CHARS_PER_TOKEN: float = 4.0
OUTPUT_TOKEN_MULTIPLIER: float = 1.5  # Estimate output as 1.5x input

# Logging format
LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(request_id)s] %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


# =============================================================================
# CUSTOM EXCEPTIONS
# =============================================================================

class APIManagerError(Exception):
    """Base exception for API manager errors."""
    
    def __init__(self, message: str, request_id: Optional[str] = None) -> None:
        self.message = message
        self.request_id = request_id
        super().__init__(self.message)


class RateLimitExceeded(APIManagerError):
    """Raised when rate limit is exceeded after all retries."""
    
    def __init__(
        self,
        message: str = "Rate limit exceeded after maximum retries",
        retry_after: Optional[int] = None,
        request_id: Optional[str] = None
    ) -> None:
        super().__init__(message, request_id)
        self.retry_after = retry_after


class APIConnectionFailed(APIManagerError):
    """Raised when API connection fails after all retries."""
    
    def __init__(
        self,
        message: str = "Failed to connect to OpenAI API",
        original_error: Optional[Exception] = None,
        request_id: Optional[str] = None
    ) -> None:
        super().__init__(message, request_id)
        self.original_error = original_error


class InvalidPromptError(APIManagerError):
    """Raised when the prompt is invalid or too long."""
    
    def __init__(
        self,
        message: str,
        prompt_length: Optional[int] = None,
        max_length: Optional[int] = None,
        request_id: Optional[str] = None
    ) -> None:
        super().__init__(message, request_id)
        self.prompt_length = prompt_length
        self.max_length = max_length


class APIKeyInvalidError(APIManagerError):
    """Raised when the API key is invalid or expired."""
    
    def __init__(
        self,
        message: str = "Invalid or expired API key",
        request_id: Optional[str] = None
    ) -> None:
        super().__init__(message, request_id)


class APIServerError(APIManagerError):
    """Raised when OpenAI server returns an error."""
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        request_id: Optional[str] = None
    ) -> None:
        super().__init__(message, request_id)
        self.status_code = status_code


class RequestTimeoutError(APIManagerError):
    """Raised when a request times out."""
    
    def __init__(
        self,
        message: str = "Request timed out",
        timeout_seconds: Optional[int] = None,
        request_id: Optional[str] = None
    ) -> None:
        super().__init__(message, request_id)
        self.timeout_seconds = timeout_seconds


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class TokenUsage:
    """Container for token usage information."""
    
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    
    def to_dict(self) -> Dict[str, int]:
        return {
            "prompt": self.prompt_tokens,
            "completion": self.completion_tokens,
            "total": self.total_tokens,
        }


@dataclass
class APIResponse:
    """Structured response from API calls."""
    
    success: bool
    content: str = ""
    model: str = ""
    tokens_used: TokenUsage = field(default_factory=TokenUsage)
    cost: float = 0.0
    timestamp: str = ""
    request_id: str = ""
    finish_reason: str = ""
    error: Optional[str] = None
    latency_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "content": self.content,
            "model": self.model,
            "tokens_used": self.tokens_used.to_dict(),
            "cost": self.cost,
            "timestamp": self.timestamp,
            "request_id": self.request_id,
            "finish_reason": self.finish_reason,
            "error": self.error,
            "latency_ms": self.latency_ms,
        }


@dataclass
class CacheEntry:
    """Cache entry with TTL tracking."""
    
    response: APIResponse
    created_at: datetime
    ttl_seconds: int = CACHE_TTL_SECONDS
    
    @property
    def is_expired(self) -> bool:
        return datetime.now() > self.created_at + timedelta(seconds=self.ttl_seconds)


@dataclass
class UsageStatistics:
    """Container for usage statistics."""
    
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    requests_by_model: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    tokens_by_model: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    cost_by_model: Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": (
                self.successful_requests / self.total_requests * 100
                if self.total_requests > 0 else 0
            ),
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_tokens,
            "total_cost": round(self.total_cost, 6),
            "requests_by_model": dict(self.requests_by_model),
            "tokens_by_model": dict(self.tokens_by_model),
            "cost_by_model": {k: round(v, 6) for k, v in self.cost_by_model.items()},
        }


# =============================================================================
# LOGGING UTILITIES
# =============================================================================

class RequestIdFilter(logging.Filter):
    """Add request_id to log records."""
    
    def __init__(self, request_id: str = "-") -> None:
        super().__init__()
        self.request_id = request_id
    
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = getattr(record, "request_id", self.request_id)
        return True


def mask_api_key(api_key: str) -> str:
    """Mask API key for safe logging, showing only last 4 characters.
    
    Args:
        api_key: The full API key.
        
    Returns:
        Masked key like 'sk-...xyz1'
    """
    if not api_key or len(api_key) < 8:
        return "***"
    return f"{api_key[:3]}...{api_key[-4:]}"


def sanitize_prompt_for_log(prompt: str, max_length: int = 100) -> str:
    """Sanitize prompt for logging by truncating and removing sensitive patterns.
    
    Args:
        prompt: The prompt to sanitize.
        max_length: Maximum length to show.
        
    Returns:
        Sanitized prompt safe for logging.
    """
    import re
    
    # Truncate
    if len(prompt) > max_length:
        prompt = prompt[:max_length] + "..."
    
    # Remove potential PII patterns (emails, phone numbers)
    prompt = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', prompt)
    prompt = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', prompt)
    prompt = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]', prompt)
    
    return prompt


# =============================================================================
# RETRY DECORATOR
# =============================================================================

def retry_with_backoff(
    max_attempts: int = MAX_RETRY_ATTEMPTS,
    base_delay: float = BASE_RETRY_DELAY,
    backoff_multiplier: float = RETRY_BACKOFF_MULTIPLIER,
    retryable_exceptions: Tuple[type, ...] = (RateLimitError, APIConnectionError)
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for retrying functions with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts.
        base_delay: Initial delay in seconds.
        backoff_multiplier: Multiplier for each subsequent delay.
        retryable_exceptions: Tuple of exception types to retry on.
        
    Returns:
        Decorated function with retry logic.
        
    Example:
        >>> @retry_with_backoff(max_attempts=3)
        ... def make_api_call():
        ...     # API call that might fail
        ...     pass
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Optional[Exception] = None
            delay = base_delay
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt < max_attempts:
                        # Extract request_id if available
                        request_id = kwargs.get("request_id", "-")
                        
                        logger.warning(
                            f"Attempt {attempt}/{max_attempts} failed: {e}. "
                            f"Retrying in {delay:.1f}s...",
                            extra={"request_id": request_id}
                        )
                        time.sleep(delay)
                        delay *= backoff_multiplier
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed. Last error: {e}",
                            extra={"request_id": kwargs.get("request_id", "-")}
                        )
            
            # Raise appropriate custom exception
            if isinstance(last_exception, RateLimitError):
                raise RateLimitExceeded(
                    f"Rate limit exceeded after {max_attempts} attempts",
                    request_id=kwargs.get("request_id")
                )
            elif isinstance(last_exception, APIConnectionError):
                raise APIConnectionFailed(
                    f"Connection failed after {max_attempts} attempts",
                    original_error=last_exception,
                    request_id=kwargs.get("request_id")
                )
            else:
                raise last_exception  # type: ignore
        
        return wrapper
    return decorator


# =============================================================================
# MONITORING PROTOCOL
# =============================================================================

class MonitoringCallback(Protocol):
    """Protocol for monitoring callbacks."""
    
    def on_request_start(self, request_id: str, prompt: str, model: str) -> None:
        """Called when a request starts."""
        ...
    
    def on_request_complete(self, request_id: str, response: APIResponse) -> None:
        """Called when a request completes successfully."""
        ...
    
    def on_request_error(self, request_id: str, error: Exception) -> None:
        """Called when a request fails."""
        ...


class NullMonitoringCallback:
    """Default no-op monitoring callback."""
    
    def on_request_start(self, request_id: str, prompt: str, model: str) -> None:
        pass
    
    def on_request_complete(self, request_id: str, response: APIResponse) -> None:
        pass
    
    def on_request_error(self, request_id: str, error: Exception) -> None:
        pass


# =============================================================================
# OPENAI MANAGER CLASS
# =============================================================================

class OpenAIManager:
    """Enterprise-grade OpenAI API manager with comprehensive error handling.
    
    This class provides a production-ready interface to the OpenAI API with:
    - Automatic retry logic with exponential backoff
    - Comprehensive error handling
    - Request/response logging with security redaction
    - Cost tracking and usage statistics
    - Response caching
    - Thread-safe operations
    
    Attributes:
        model: Default model to use for generations.
        max_tokens: Default max tokens for completions.
        temperature: Default temperature for generations.
        
    Example:
        >>> manager = OpenAIManager()
        >>> result = manager.generate_content("Write about AI")
        >>> if result['success']:
        ...     print(result['content'])
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        timeout: int = DEFAULT_REQUEST_TIMEOUT,
        monitoring_callback: Optional[MonitoringCallback] = None,
        client: Optional[Any] = None,  # For testing injection
    ) -> None:
        """Initialize the OpenAI manager.
        
        Args:
            api_key: OpenAI API key (defaults to config).
            model: Model to use (defaults to config).
            max_tokens: Max tokens per request (defaults to config).
            temperature: Sampling temperature (defaults to config).
            timeout: Request timeout in seconds.
            monitoring_callback: Optional callback for monitoring.
            client: Optional pre-configured client (for testing).
        """
        # Load config for defaults
        if client is None:
            try:
                config = load_config()
                self._api_key = api_key or config.openai_api_key
                self.model = model or config.openai_model
                self.max_tokens = max_tokens or config.max_tokens
                self.temperature = temperature or config.temperature
            except ConfigurationError:
                # Allow initialization without config for testing
                self._api_key = api_key or ""
                self.model = model or "gpt-3.5-turbo"
                self.max_tokens = max_tokens or 2000
                self.temperature = temperature or 0.7
        else:
            # Testing mode with injected client
            self._api_key = api_key or "sk-test"
            self.model = model or "gpt-3.5-turbo"
            self.max_tokens = max_tokens or 2000
            self.temperature = temperature or 0.7
        
        self._timeout = timeout
        self._monitoring = monitoring_callback or NullMonitoringCallback()
        
        # Initialize client
        if client is not None:
            self._client = client
        else:
            self._client = OpenAI(
                api_key=self._api_key,
                timeout=self._timeout,
            )
        
        # Thread-safe counters and caches
        self._lock = threading.RLock()
        self._stats = UsageStatistics()
        self._cache: Dict[str, CacheEntry] = {}
        self._api_key_valid: Optional[bool] = None
        self._api_key_validated_at: Optional[datetime] = None
        
        # Request counter for unique IDs
        self._request_counter = 0
        
        # Token encoder for estimation
        try:
            self._encoder = tiktoken.encoding_for_model(self.model)
        except KeyError:
            self._encoder = tiktoken.get_encoding("cl100k_base")
        
        logger.info(
            f"OpenAIManager initialized with model={self.model}, "
            f"api_key={mask_api_key(self._api_key)}",
            extra={"request_id": "-"}
        )
    
    def _generate_request_id(self) -> str:
        """Generate a unique request ID."""
        with self._lock:
            self._request_counter += 1
            return f"req-{uuid.uuid4().hex[:8]}-{self._request_counter}"
    
    def _get_cache_key(self, prompt: str, system_message: Optional[str], model: str) -> str:
        """Generate a cache key for the request."""
        content = f"{prompt}|{system_message or ''}|{model}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _check_cache(self, cache_key: str) -> Optional[APIResponse]:
        """Check cache for a valid response."""
        with self._lock:
            if cache_key in self._cache:
                entry = self._cache[cache_key]
                if not entry.is_expired:
                    return entry.response
                else:
                    del self._cache[cache_key]
        return None
    
    def _store_cache(self, cache_key: str, response: APIResponse) -> None:
        """Store a response in the cache."""
        with self._lock:
            self._cache[cache_key] = CacheEntry(
                response=response,
                created_at=datetime.now()
            )
    
    def _update_stats(self, response: APIResponse) -> None:
        """Update usage statistics with response data."""
        with self._lock:
            self._stats.total_requests += 1
            
            if response.success:
                self._stats.successful_requests += 1
                self._stats.total_prompt_tokens += response.tokens_used.prompt_tokens
                self._stats.total_completion_tokens += response.tokens_used.completion_tokens
                self._stats.total_tokens += response.tokens_used.total_tokens
                self._stats.total_cost += response.cost
                
                self._stats.requests_by_model[response.model] += 1
                self._stats.tokens_by_model[response.model] += response.tokens_used.total_tokens
                self._stats.cost_by_model[response.model] += response.cost
            else:
                self._stats.failed_requests += 1
    
    def _calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate the cost based on token usage and model.
        
        Args:
            model: The model used.
            prompt_tokens: Number of input tokens.
            completion_tokens: Number of output tokens.
            
        Returns:
            Total cost in USD.
        """
        if model not in MODEL_COSTS:
            logger.warning(f"Unknown model '{model}' for cost calculation")
            return 0.0
        
        costs = MODEL_COSTS[model]
        input_cost = (prompt_tokens / 1000) * costs["input"]
        output_cost = (completion_tokens / 1000) * costs["output"]
        
        return round(input_cost + output_cost, 6)
    
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken.
        
        Args:
            text: The text to count tokens for.
            
        Returns:
            Number of tokens.
        """
        try:
            return len(self._encoder.encode(text))
        except Exception:
            # Fallback to character-based estimation
            return int(len(text) / AVG_CHARS_PER_TOKEN)
    
    @retry_with_backoff(
        max_attempts=MAX_RETRY_ATTEMPTS,
        base_delay=BASE_RETRY_DELAY,
        retryable_exceptions=(RateLimitError, APIConnectionError)
    )
    def _make_api_call(
        self,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: int,
        temperature: float,
        request_id: str,
    ) -> Tuple[Any, float]:
        """Make the actual API call with retry logic.
        
        Args:
            messages: List of message dictionaries.
            model: Model to use.
            max_tokens: Maximum tokens.
            temperature: Sampling temperature.
            request_id: Request ID for logging.
            
        Returns:
            Tuple of (API response, latency in ms).
            
        Raises:
            Various exceptions based on error type.
        """
        start_time = time.perf_counter()
        
        try:
            response = self._client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            latency_ms = (time.perf_counter() - start_time) * 1000
            return response, latency_ms
            
        except AuthenticationError as e:
            logger.critical(
                f"Authentication failed: {e}",
                extra={"request_id": request_id}
            )
            raise APIKeyInvalidError(
                f"Invalid API key: {e}",
                request_id=request_id
            )
        
        except RateLimitError:
            # Let the retry decorator handle this
            raise
        
        except APIConnectionError:
            # Let the retry decorator handle this
            raise
        
        except OpenAIAPIError as e:
            logger.error(
                f"OpenAI API error: {e}",
                extra={"request_id": request_id}
            )
            raise APIServerError(
                f"OpenAI server error: {e}",
                status_code=getattr(e, "status_code", None),
                request_id=request_id
            )
        
        except Exception as e:
            # Check for timeout
            if "timeout" in str(e).lower():
                raise RequestTimeoutError(
                    f"Request timed out after {self._timeout}s",
                    timeout_seconds=self._timeout,
                    request_id=request_id
                )
            raise
    
    def generate_content(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        system_message: Optional[str] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """Generate content using the OpenAI API.
        
        Args:
            prompt: The prompt to generate content from.
            max_tokens: Override default max tokens.
            temperature: Override default temperature.
            system_message: Optional system message for context.
            use_cache: Whether to use response caching.
            
        Returns:
            Structured response dictionary with:
            - success: Whether the request succeeded
            - content: Generated text
            - model: Model used
            - tokens_used: Token usage breakdown
            - cost: Cost in USD
            - timestamp: ISO 8601 timestamp
            - request_id: Unique request identifier
            - finish_reason: Completion reason
            - error: Error message if failed
            
        Raises:
            InvalidPromptError: If prompt is empty or too long.
            APIKeyInvalidError: If API key is invalid.
            RateLimitExceeded: If rate limit exceeded after retries.
            APIConnectionFailed: If connection fails after retries.
            
        Example:
            >>> result = manager.generate_content(
            ...     prompt="Write a haiku about coding",
            ...     system_message="You are a poet",
            ...     max_tokens=50
            ... )
            >>> print(result['content'])
        """
        request_id = self._generate_request_id()
        timestamp = datetime.now().isoformat()
        
        # Input validation
        if not prompt or not prompt.strip():
            raise InvalidPromptError(
                "Prompt cannot be empty",
                request_id=request_id
            )
        
        # Use defaults if not specified
        model = self.model
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature or self.temperature
        
        # Check cache
        if use_cache:
            cache_key = self._get_cache_key(prompt, system_message, model)
            cached = self._check_cache(cache_key)
            if cached:
                logger.debug(
                    f"Cache hit for prompt: {sanitize_prompt_for_log(prompt)}",
                    extra={"request_id": request_id}
                )
                # Update request_id and timestamp for the cached response
                cached.request_id = request_id
                cached.timestamp = timestamp
                return cached.to_dict()
        
        # Build messages
        messages: List[Dict[str, str]] = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        
        # Log request
        logger.debug(
            f"Generating content with model={model}, "
            f"max_tokens={max_tokens}, temperature={temperature}, "
            f"prompt={sanitize_prompt_for_log(prompt)}",
            extra={"request_id": request_id}
        )
        
        # Notify monitoring
        self._monitoring.on_request_start(request_id, prompt, model)
        
        try:
            # Make API call
            api_response, latency_ms = self._make_api_call(
                messages=messages,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                request_id=request_id,
            )
            
            # Extract response data
            choice = api_response.choices[0]
            content = choice.message.content or ""
            finish_reason = choice.finish_reason or "unknown"
            
            usage = api_response.usage
            tokens = TokenUsage(
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
            )
            
            cost = self._calculate_cost(
                model=model,
                prompt_tokens=tokens.prompt_tokens,
                completion_tokens=tokens.completion_tokens,
            )
            
            response = APIResponse(
                success=True,
                content=content,
                model=model,
                tokens_used=tokens,
                cost=cost,
                timestamp=timestamp,
                request_id=request_id,
                finish_reason=finish_reason,
                latency_ms=latency_ms,
            )
            
            # Update stats and cache
            self._update_stats(response)
            if use_cache:
                self._store_cache(cache_key, response)
            
            # Log success
            logger.info(
                f"Generation successful: {tokens.total_tokens} tokens, "
                f"${cost:.6f}, {latency_ms:.0f}ms",
                extra={"request_id": request_id}
            )
            
            # Notify monitoring
            self._monitoring.on_request_complete(request_id, response)
            
            return response.to_dict()
            
        except APIManagerError as e:
            # Handle our custom exceptions
            response = APIResponse(
                success=False,
                timestamp=timestamp,
                request_id=request_id,
                error=str(e),
            )
            self._update_stats(response)
            self._monitoring.on_request_error(request_id, e)
            
            logger.error(
                f"Generation failed: {e}",
                extra={"request_id": request_id}
            )
            
            return response.to_dict()
        
        except Exception as e:
            # Handle unexpected exceptions
            response = APIResponse(
                success=False,
                timestamp=timestamp,
                request_id=request_id,
                error=f"Unexpected error: {e}",
            )
            self._update_stats(response)
            self._monitoring.on_request_error(request_id, e)
            
            logger.error(
                f"Unexpected error during generation: {e}",
                extra={"request_id": request_id},
                exc_info=True
            )
            
            return response.to_dict()
    
    def generate_batch(
        self,
        prompts: List[str],
        parallel: bool = False,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        system_message: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Generate content for multiple prompts.
        
        Args:
            prompts: List of prompts to process.
            parallel: Whether to process in parallel (default: False).
            max_tokens: Override default max tokens.
            temperature: Override default temperature.
            system_message: Optional system message for all prompts.
            
        Returns:
            List of response dictionaries, one per prompt.
            
        Example:
            >>> prompts = ["Write about cats", "Write about dogs"]
            >>> results = manager.generate_batch(prompts, parallel=True)
            >>> for result in results:
            ...     if result['success']:
            ...         print(result['content'][:50])
        """
        if not prompts:
            return []
        
        logger.info(
            f"Starting batch generation for {len(prompts)} prompts, "
            f"parallel={parallel}",
            extra={"request_id": "-"}
        )
        
        if parallel:
            return self._generate_batch_parallel(
                prompts, max_tokens, temperature, system_message
            )
        else:
            return self._generate_batch_sequential(
                prompts, max_tokens, temperature, system_message
            )
    
    def _generate_batch_sequential(
        self,
        prompts: List[str],
        max_tokens: Optional[int],
        temperature: Optional[float],
        system_message: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Process prompts sequentially."""
        results = []
        for i, prompt in enumerate(prompts):
            logger.debug(f"Processing prompt {i+1}/{len(prompts)}")
            result = self.generate_content(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                system_message=system_message,
            )
            results.append(result)
        return results
    
    def _generate_batch_parallel(
        self,
        prompts: List[str],
        max_tokens: Optional[int],
        temperature: Optional[float],
        system_message: Optional[str],
    ) -> List[Dict[str, Any]]:
        """Process prompts in parallel with rate limiting."""
        
        async def process_prompt(prompt: str, semaphore: asyncio.Semaphore) -> Dict[str, Any]:
            async with semaphore:
                # Run sync generation in thread pool
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(
                    None,
                    lambda: self.generate_content(
                        prompt=prompt,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        system_message=system_message,
                    )
                )
        
        async def process_all() -> List[Dict[str, Any]]:
            semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
            tasks = [process_prompt(p, semaphore) for p in prompts]
            return await asyncio.gather(*tasks)
        
        # Run async processing
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(process_all())
    
    def estimate_cost(
        self,
        text: str,
        model: Optional[str] = None,
        expected_output_ratio: float = OUTPUT_TOKEN_MULTIPLIER,
    ) -> Dict[str, float]:
        """Estimate the cost of a generation request.
        
        Args:
            text: The input text/prompt.
            model: Model to use (defaults to configured model).
            expected_output_ratio: Ratio of output to input tokens.
            
        Returns:
            Dictionary with cost breakdown:
            - input_tokens: Estimated input tokens
            - estimated_output_tokens: Estimated output tokens
            - total_tokens: Total estimated tokens
            - input_cost: Cost for input tokens
            - output_cost: Cost for output tokens
            - total_cost: Total estimated cost
            
        Example:
            >>> cost = manager.estimate_cost("Write a long blog post")
            >>> print(f"Estimated cost: ${cost['total_cost']:.4f}")
        """
        model = model or self.model
        
        input_tokens = self._count_tokens(text)
        estimated_output = int(input_tokens * expected_output_ratio)
        
        # Cap at max_tokens
        estimated_output = min(estimated_output, self.max_tokens)
        
        total_tokens = input_tokens + estimated_output
        
        # Calculate costs
        if model in MODEL_COSTS:
            costs = MODEL_COSTS[model]
            input_cost = (input_tokens / 1000) * costs["input"]
            output_cost = (estimated_output / 1000) * costs["output"]
        else:
            input_cost = 0.0
            output_cost = 0.0
        
        return {
            "input_tokens": input_tokens,
            "estimated_output_tokens": estimated_output,
            "total_tokens": total_tokens,
            "input_cost": round(input_cost, 6),
            "output_cost": round(output_cost, 6),
            "total_cost": round(input_cost + output_cost, 6),
            "model": model,
        }
    
    def get_usage_statistics(self) -> Dict[str, Any]:
        """Get comprehensive usage statistics.
        
        Returns:
            Dictionary with usage statistics including:
            - total_requests: Total API requests made
            - successful_requests: Number of successful requests
            - failed_requests: Number of failed requests
            - success_rate: Percentage of successful requests
            - total_tokens: Total tokens consumed
            - total_cost: Total cost in USD
            - Breakdowns by model
            
        Example:
            >>> stats = manager.get_usage_statistics()
            >>> print(f"Total cost: ${stats['total_cost']:.4f}")
            >>> print(f"Success rate: {stats['success_rate']:.1f}%")
        """
        with self._lock:
            return self._stats.to_dict()
    
    def validate_api_key(self, force_check: bool = False) -> bool:
        """Validate the API key with a minimal request.
        
        Args:
            force_check: Force validation even if cached.
            
        Returns:
            True if API key is valid, False otherwise.
            
        Example:
            >>> if manager.validate_api_key():
            ...     print("API key is valid!")
        """
        # Check cache
        if not force_check and self._api_key_valid is not None:
            if self._api_key_validated_at:
                cache_age = datetime.now() - self._api_key_validated_at
                if cache_age.total_seconds() < API_KEY_VALIDATION_CACHE_TTL:
                    return self._api_key_valid
        
        logger.debug(
            f"Validating API key: {mask_api_key(self._api_key)}",
            extra={"request_id": "-"}
        )
        
        try:
            # Make minimal request
            self._client.models.list()
            self._api_key_valid = True
            self._api_key_validated_at = datetime.now()
            logger.info("API key validation successful", extra={"request_id": "-"})
            return True
        except AuthenticationError:
            self._api_key_valid = False
            self._api_key_validated_at = datetime.now()
            logger.warning("API key validation failed", extra={"request_id": "-"})
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error during API key validation: {e}",
                extra={"request_id": "-"}
            )
            return False
    
    def check_rate_limit(self) -> Dict[str, Any]:
        """Check current rate limit status.
        
        Note: OpenAI doesn't provide a direct rate limit check endpoint.
        This method returns information based on response headers from
        the last request or makes a minimal request to check.
        
        Returns:
            Dictionary with rate limit information.
        """
        # Make a minimal request to get headers
        try:
            response = self._client.models.list()
            return {
                "status": "ok",
                "note": "Rate limit information not directly available from API",
                "recommendation": "Monitor for RateLimitError responses",
            }
        except RateLimitError as e:
            return {
                "status": "rate_limited",
                "message": str(e),
                "retry_after": getattr(e, "retry_after", None),
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
            }
    
    def clear_cache(self) -> int:
        """Clear the response cache.
        
        Returns:
            Number of entries cleared.
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cleared {count} cache entries", extra={"request_id": "-"})
            return count
    
    def reset_statistics(self) -> None:
        """Reset all usage statistics."""
        with self._lock:
            self._stats = UsageStatistics()
            logger.info("Usage statistics reset", extra={"request_id": "-"})
    
    def export_metrics(self) -> Dict[str, Any]:
        """Export metrics in a format suitable for monitoring tools.
        
        Returns:
            Dictionary with metrics for Prometheus/Grafana.
        """
        stats = self.get_usage_statistics()
        
        return {
            "openai_requests_total": stats["total_requests"],
            "openai_requests_successful": stats["successful_requests"],
            "openai_requests_failed": stats["failed_requests"],
            "openai_tokens_total": stats["total_tokens"],
            "openai_tokens_prompt": stats["total_prompt_tokens"],
            "openai_tokens_completion": stats["total_completion_tokens"],
            "openai_cost_usd": stats["total_cost"],
            "openai_cache_size": len(self._cache),
            "openai_success_rate": stats["success_rate"],
        }


# =============================================================================
# MOCK MANAGER FOR TESTING
# =============================================================================

class MockOpenAIManager(OpenAIManager):
    """Mock manager for testing without real API calls.
    
    Example:
        >>> mock = MockOpenAIManager(mock_response="Test content")
        >>> result = mock.generate_content("Any prompt")
        >>> assert result['content'] == "Test content"
    """
    
    def __init__(
        self,
        mock_response: str = "Mock generated content",
        mock_tokens: int = 100,
        should_fail: bool = False,
        fail_error: Optional[str] = None,
    ) -> None:
        """Initialize mock manager.
        
        Args:
            mock_response: Content to return for generations.
            mock_tokens: Token count to report.
            should_fail: Whether to simulate failures.
            fail_error: Error message for failures.
        """
        self._mock_response = mock_response
        self._mock_tokens = mock_tokens
        self._should_fail = should_fail
        self._fail_error = fail_error or "Mock error"
        
        # Initialize with test values
        self._api_key = "sk-mock"
        self.model = "gpt-3.5-turbo"
        self.max_tokens = 2000
        self.temperature = 0.7
        self._timeout = 30
        self._monitoring = NullMonitoringCallback()
        
        self._lock = threading.RLock()
        self._stats = UsageStatistics()
        self._cache: Dict[str, CacheEntry] = {}
        self._request_counter = 0
        self._api_key_valid = True
        self._api_key_validated_at = datetime.now()
        
        try:
            self._encoder = tiktoken.encoding_for_model(self.model)
        except Exception:
            self._encoder = tiktoken.get_encoding("cl100k_base")
    
    def generate_content(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        system_message: Optional[str] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """Return mock response."""
        request_id = self._generate_request_id()
        timestamp = datetime.now().isoformat()
        
        if self._should_fail:
            response = APIResponse(
                success=False,
                timestamp=timestamp,
                request_id=request_id,
                error=self._fail_error,
            )
        else:
            tokens = TokenUsage(
                prompt_tokens=self._mock_tokens // 2,
                completion_tokens=self._mock_tokens // 2,
                total_tokens=self._mock_tokens,
            )
            
            response = APIResponse(
                success=True,
                content=self._mock_response,
                model=self.model,
                tokens_used=tokens,
                cost=0.001,
                timestamp=timestamp,
                request_id=request_id,
                finish_reason="stop",
                latency_ms=50.0,
            )
        
        self._update_stats(response)
        return response.to_dict()
    
    def validate_api_key(self, force_check: bool = False) -> bool:
        """Always return True for mock."""
        return not self._should_fail


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_manager(
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs: Any
) -> OpenAIManager:
    """Factory function to create an OpenAIManager with defaults.
    
    Args:
        api_key: Optional API key override.
        model: Optional model override.
        **kwargs: Additional arguments for OpenAIManager.
        
    Returns:
        Configured OpenAIManager instance.
        
    Example:
        >>> manager = create_manager()
        >>> result = manager.generate_content("Hello!")
    """
    return OpenAIManager(api_key=api_key, model=model, **kwargs)


def create_mock_manager(
    mock_response: str = "Mock content",
    **kwargs: Any
) -> MockOpenAIManager:
    """Factory function to create a MockOpenAIManager for testing.
    
    Args:
        mock_response: Content to return.
        **kwargs: Additional mock configuration.
        
    Returns:
        Configured MockOpenAIManager instance.
    """
    return MockOpenAIManager(mock_response=mock_response, **kwargs)


# =============================================================================
# BACKWARD COMPATIBILITY
# =============================================================================

# Alias for backward compatibility
APIManager = OpenAIManager
APIError = APIManagerError
