"""Content generation orchestration with history tracking and advanced features.

This module provides the ContentGenerator class that serves as the main
facade for the AI Content Generator system. It integrates:
- OpenAIManager for API interactions
- PromptEngine for template management
- Utils for validation and sanitization
- Config for settings management

Architecture Pattern: Facade Pattern
- Hides complexity of underlying components
- Provides simple, intuitive interface
- Handles all coordination logic

Example Usage:
    >>> # Basic usage
    >>> generator = ContentGenerator(api_key='sk-...')
    >>> 
    >>> result = generator.generate(
    ...     'product_description',
    ...     product_name='Wireless Mouse',
    ...     features='Ergonomic, Bluetooth, Rechargeable',
    ...     audience='Remote workers'
    ... )
    >>> 
    >>> print(result['content'])
    >>> print(f"Cost: ${result['cost']:.4f}")
    >>> 
    >>> # Generate variations
    >>> variations = generator.generate_multiple_variations(
    ...     'social_media_post',
    ...     {'topic': 'New Product Launch', 'platform': 'Twitter'},
    ...     count=3
    ... )
    >>> 
    >>> # Batch processing
    >>> requests = [
    ...     {'template_name': 'product_description', 'variables': {...}},
    ...     {'template_name': 'meta_description', 'variables': {...}}
    ... ]
    >>> results = generator.generate_batch(requests)
    >>> 
    >>> # Statistics
    >>> stats = generator.get_statistics()
    >>> print(f"Total spent: ${stats['total_cost']:.2f}")
    >>> 
    >>> # Context manager (auto-saves history on exit)
    >>> with ContentGenerator() as gen:
    ...     result = gen.generate(...)

Author: AI-ContentGen-Pro Team
Version: 2.0.0
"""

import csv
import json
import logging
import threading
import time
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from .api_manager import OpenAIManager, create_mock_manager
from .config import load_config, ConfigurationError
from .prompt_engine import (
    PromptEngine,
    PromptTemplate,
    create_template,
    create_engine_with_defaults,
    TemplateNotFoundError,
    VariableValidationError,
)
from .utils import (
    validate_input,
    sanitize_output,
    format_timestamp,
    generate_request_id,
    create_hash,
    save_json_file,
    load_json_file,
)

logger = logging.getLogger(__name__)


# =============================================================================
# CONSTANTS
# =============================================================================

MAX_HISTORY_SIZE = 1000
MAX_CACHE_SIZE = 100
CACHE_TTL_SECONDS = 3600  # 1 hour
DEFAULT_RETRY_ATTEMPTS = 1
DEFAULT_COST_ALERT_THRESHOLD = 1.0  # $1.00


# =============================================================================
# LRU CACHE IMPLEMENTATION
# =============================================================================

class LRUCache:
    """Thread-safe LRU cache with TTL support.
    
    Attributes:
        max_size: Maximum number of items in cache.
        ttl_seconds: Time-to-live for cache entries.
    """
    
    def __init__(self, max_size: int = MAX_CACHE_SIZE, ttl_seconds: int = CACHE_TTL_SECONDS):
        self._cache: OrderedDict = OrderedDict()
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get item from cache, returning None if not found or expired."""
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            
            entry = self._cache[key]
            
            # Check TTL
            if datetime.now(timezone.utc) > entry['expires_at']:
                del self._cache[key]
                self._misses += 1
                return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._hits += 1
            return entry['data']
    
    def set(self, key: str, data: Dict[str, Any]) -> None:
        """Add item to cache with TTL."""
        with self._lock:
            # Remove if exists (to update position)
            if key in self._cache:
                del self._cache[key]
            
            # Evict oldest if at capacity
            while len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)
            
            # Add new entry
            self._cache[key] = {
                'data': data,
                'expires_at': datetime.now(timezone.utc) + timedelta(seconds=self._ttl_seconds),
                'created_at': datetime.now(timezone.utc),
            }
    
    def clear(self) -> int:
        """Clear all cache entries, returning count cleared."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate as percentage."""
        total = self._hits + self._misses
        return (self._hits / total * 100) if total > 0 else 0.0
    
    def __len__(self) -> int:
        return len(self._cache)


# =============================================================================
# CONTENT GENERATOR CLASS
# =============================================================================

class ContentGenerator:
    """Main orchestrator for AI content generation.
    
    This class serves as the facade for the entire content generation system,
    coordinating between the prompt engine, API manager, and utility functions.
    It provides a simple interface while handling complexity internally.
    
    Features:
    - Template-based content generation
    - Generation history tracking
    - Result caching with LRU eviction
    - Batch processing (sequential and parallel)
    - Multiple variation generation
    - Usage statistics and cost tracking
    - Callback support for monitoring
    - Context manager support for auto-cleanup
    - Thread-safe operations
    
    Attributes:
        api_manager: Manager for OpenAI API interactions.
        prompt_engine: Engine for template management.
        session_id: Unique identifier for this generator instance.
    
    Example:
        >>> generator = ContentGenerator()
        >>> result = generator.generate(
        ...     'product_description',
        ...     product_name='Smart Watch',
        ...     features='GPS, Heart Rate',
        ...     audience='Athletes'
        ... )
        >>> if result['success']:
        ...     print(result['content'])
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        config: Optional[Any] = None,
        api_manager: Optional[OpenAIManager] = None,
        prompt_engine: Optional[PromptEngine] = None,
        load_defaults: bool = True,
        cost_alert_threshold: Optional[float] = None,
    ) -> None:
        """Initialize the content generator.
        
        Args:
            api_key: Optional OpenAI API key (uses config if not provided).
            config: Optional configuration object.
            api_manager: Optional pre-configured API manager (for testing).
            prompt_engine: Optional pre-configured prompt engine.
            load_defaults: Whether to load built-in templates (default: True).
            cost_alert_threshold: Optional cost threshold for warnings.
        """
        # Generate session ID
        self.session_id = generate_request_id()
        self._session_start = datetime.now(timezone.utc)
        
        # Load configuration
        if config is not None:
            self._config = config
        else:
            try:
                self._config = load_config()
            except ConfigurationError:
                self._config = None
        
        # Initialize API manager
        if api_manager is not None:
            self.api_manager = api_manager
        else:
            try:
                self.api_manager = OpenAIManager(api_key=api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize API manager: {e}")
                self.api_manager = None
        
        # Initialize prompt engine
        if prompt_engine is not None:
            self.prompt_engine = prompt_engine
        else:
            self.prompt_engine = create_engine_with_defaults() if load_defaults else PromptEngine()
        
        # Initialize history and cache
        self._history: List[Dict[str, Any]] = []
        self._cache = LRUCache(max_size=MAX_CACHE_SIZE, ttl_seconds=CACHE_TTL_SECONDS)
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Callbacks
        self._callbacks: List[Callable[[Dict[str, Any]], None]] = []
        
        # Cost tracking
        self._cost_alert_threshold = cost_alert_threshold or DEFAULT_COST_ALERT_THRESHOLD
        self._total_cost = 0.0
        
        # Statistics counters
        self._cache_checks = 0
        self._cache_hits = 0
        
        logger.info(
            f"ContentGenerator initialized (session_id={self.session_id})"
        )
    
    # =========================================================================
    # CONTEXT MANAGER SUPPORT
    # =========================================================================
    
    def __enter__(self) -> 'ContentGenerator':
        """Enter context manager."""
        return self
    
    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[Exception],
        exc_tb: Optional[Any]
    ) -> bool:
        """Exit context manager, auto-saving history."""
        try:
            # Auto-backup history if there are entries
            if self._history:
                backup_path = f"content_history_{self.session_id[:8]}.json"
                self.export_history(backup_path, format='json')
                logger.info(f"Auto-saved history to {backup_path}")
        except Exception as e:
            logger.error(f"Failed to auto-save history: {e}")
        
        # Clear cache
        self.clear_cache()
        
        return False  # Don't suppress exceptions
    
    # =========================================================================
    # CALLBACK MANAGEMENT
    # =========================================================================
    
    def register_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register a callback to be called after each generation.
        
        Args:
            callback: Function that receives the generation result dict.
        
        Example:
            >>> def my_callback(result):
            ...     print(f"Generated: {result['success']}")
            >>> generator.register_callback(my_callback)
        """
        with self._lock:
            self._callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable[[Dict[str, Any]], None]) -> bool:
        """Remove a previously registered callback.
        
        Returns:
            True if callback was found and removed, False otherwise.
        """
        with self._lock:
            try:
                self._callbacks.remove(callback)
                return True
            except ValueError:
                return False
    
    def _invoke_callbacks(self, result: Dict[str, Any]) -> None:
        """Invoke all registered callbacks with the result."""
        for callback in self._callbacks:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"Callback error: {e}")
    
    # =========================================================================
    # CORE GENERATION METHODS
    # =========================================================================
    
    def generate(
        self,
        template_name: str,
        variables: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
        retry_on_failure: bool = True,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Generate content using a template.
        
        This is the main content generation method. It:
        1. Validates inputs
        2. Retrieves and renders the template
        3. Checks cache for existing results
        4. Calls the API if needed
        5. Sanitizes output
        6. Tracks history and statistics
        
        Args:
            template_name: Name of the template to use.
            variables: Dictionary of template variables.
            use_cache: Whether to use cached results (default: True).
            retry_on_failure: Whether to retry once on failure (default: True).
            **kwargs: Additional variables merged into variables dict,
                     or API overrides (temperature, max_tokens).
        
        Returns:
            Result dictionary with keys:
            - success: Whether generation succeeded
            - content: Generated text (empty string on failure)
            - template_used: Name of template used
            - variables: Variables used for generation
            - timestamp: ISO 8601 timestamp
            - request_id: Unique request identifier
            - model: Model used for generation
            - tokens_used: Token usage breakdown
            - cost: Generation cost in USD
            - cached: Whether result came from cache
            - generation_time: Time taken in seconds
            - error: Error message (only on failure)
        
        Example:
            >>> result = generator.generate(
            ...     'product_description',
            ...     product_name='Smart Watch',
            ...     features='GPS, Heart Rate',
            ...     audience='Athletes'
            ... )
            >>> if result['success']:
            ...     print(result['content'])
            ... else:
            ...     print(f"Error: {result['error']}")
        """
        request_id = generate_request_id()
        start_time = time.perf_counter()
        timestamp = format_timestamp()
        
        # Merge variables and kwargs
        merged_variables = dict(variables or {})
        
        # Separate API overrides from template variables
        api_overrides = {}
        for key in list(kwargs.keys()):
            if key in ('temperature', 'max_tokens', 'model'):
                api_overrides[key] = kwargs.pop(key)
        
        # Merge remaining kwargs as variables
        merged_variables.update(kwargs)
        
        # Build base result
        result: Dict[str, Any] = {
            'success': False,
            'content': '',
            'template_used': template_name,
            'variables': merged_variables,
            'timestamp': timestamp,
            'request_id': request_id,
            'model': '',
            'tokens_used': {'prompt': 0, 'completion': 0, 'total': 0},
            'cost': 0.0,
            'cached': False,
            'generation_time': 0.0,
        }
        
        try:
            # Validate inputs
            is_valid, error_msg = validate_input(template_name, merged_variables)
            if not is_valid:
                result['error'] = f"Validation failed: {error_msg}"
                logger.warning(f"[{request_id}] Validation failed: {error_msg}")
                self._add_to_history(result)
                return result
            
            # Get template
            try:
                template = self.prompt_engine.get_template(template_name)
            except TemplateNotFoundError as e:
                result['error'] = f"Template not found: {template_name}"
                logger.error(f"[{request_id}] Template not found: {template_name}")
                self._add_to_history(result)
                return result
            
            # Generate prompt
            try:
                prompt_text = template.generate(merged_variables, include_system=True)
            except VariableValidationError as e:
                result['error'] = f"Variable validation failed: {e}"
                logger.error(f"[{request_id}] Variable validation failed: {e}")
                self._add_to_history(result)
                return result
            
            # Check cache
            cache_key = self._generate_cache_key(template_name, merged_variables)
            self._cache_checks += 1
            
            if use_cache:
                cached_result = self._cache.get(cache_key)
                if cached_result:
                    self._cache_hits += 1
                    logger.debug(f"[{request_id}] Cache hit for {template_name}")
                    
                    # Update metadata for cached result
                    cached_result['request_id'] = request_id
                    cached_result['timestamp'] = timestamp
                    cached_result['cached'] = True
                    cached_result['generation_time'] = time.perf_counter() - start_time
                    
                    self._add_to_history(cached_result)
                    self._invoke_callbacks(cached_result)
                    return cached_result
            
            # Check API manager
            if self.api_manager is None:
                result['error'] = "API manager not initialized"
                logger.error(f"[{request_id}] API manager not available")
                self._add_to_history(result)
                return result
            
            # Apply template recommendations if not overridden
            if 'temperature' not in api_overrides and hasattr(template, 'temperature_recommendation'):
                api_overrides['temperature'] = template.temperature_recommendation
            if 'max_tokens' not in api_overrides and hasattr(template, 'max_tokens_recommendation'):
                api_overrides['max_tokens'] = template.max_tokens_recommendation
            
            # Call API
            logger.info(f"[{request_id}] Generating content with template '{template_name}'")
            
            api_result = self._call_api_with_retry(
                prompt_text,
                api_overrides,
                retry_on_failure,
                request_id
            )
            
            if not api_result['success']:
                result['error'] = api_result.get('error', 'Unknown API error')
                result['generation_time'] = time.perf_counter() - start_time
                self._add_to_history(result)
                return result
            
            # Sanitize output
            content = sanitize_output(api_result.get('content', ''))
            
            # Build successful result
            result.update({
                'success': True,
                'content': content,
                'model': api_result.get('model', ''),
                'tokens_used': api_result.get('tokens_used', {'prompt': 0, 'completion': 0, 'total': 0}),
                'cost': api_result.get('cost', 0.0),
                'cached': False,
                'generation_time': time.perf_counter() - start_time,
            })
            
            # Update cost tracking
            with self._lock:
                self._total_cost += result['cost']
            
            # Check cost alert
            if result['cost'] > self._cost_alert_threshold:
                logger.warning(
                    f"[{request_id}] Cost alert: ${result['cost']:.4f} "
                    f"exceeds threshold ${self._cost_alert_threshold:.4f}"
                )
            
            # Cache result
            self._cache.set(cache_key, result.copy())
            
            # Add to history
            self._add_to_history(result)
            
            # Invoke callbacks
            self._invoke_callbacks(result)
            
            logger.info(
                f"[{request_id}] Generation successful: "
                f"{result['tokens_used']['total']} tokens, ${result['cost']:.6f}"
            )
            
            return result
            
        except Exception as e:
            result['error'] = f"Unexpected error: {str(e)}"
            result['generation_time'] = time.perf_counter() - start_time
            logger.exception(f"[{request_id}] Unexpected error during generation")
            self._add_to_history(result)
            return result
    
    def _call_api_with_retry(
        self,
        prompt: str,
        api_overrides: Dict[str, Any],
        retry_on_failure: bool,
        request_id: str
    ) -> Dict[str, Any]:
        """Call API with optional retry logic."""
        attempts = DEFAULT_RETRY_ATTEMPTS + 1 if retry_on_failure else 1
        last_error = None
        
        for attempt in range(1, attempts + 1):
            try:
                result = self.api_manager.generate_content(
                    prompt=prompt,
                    **api_overrides
                )
                
                if result.get('success', False):
                    return result
                
                last_error = result.get('error', 'Unknown error')
                
                if attempt < attempts:
                    logger.warning(
                        f"[{request_id}] Attempt {attempt} failed: {last_error}. Retrying..."
                    )
                    time.sleep(1)  # Brief delay before retry
                    
            except Exception as e:
                last_error = str(e)
                if attempt < attempts:
                    logger.warning(
                        f"[{request_id}] Attempt {attempt} exception: {e}. Retrying..."
                    )
                    time.sleep(1)
        
        return {
            'success': False,
            'error': f"Failed after {attempts} attempts: {last_error}"
        }
    
    def generate_multiple_variations(
        self,
        template_name: str,
        variables: Dict[str, Any],
        count: int = 3,
        temperature_range: Optional[Tuple[float, float]] = None
    ) -> List[Dict[str, Any]]:
        """Generate multiple variations of content.
        
        Creates N different versions of the same content by varying
        the temperature or adding variation instructions.
        
        Args:
            template_name: Name of the template to use.
            variables: Template variables.
            count: Number of variations to generate (default: 3).
            temperature_range: Optional (min, max) temperature range to vary.
        
        Returns:
            List of result dictionaries, one per variation.
        
        Example:
            >>> variations = generator.generate_multiple_variations(
            ...     'social_media_post',
            ...     {'topic': 'AI', 'platform': 'Twitter'},
            ...     count=3,
            ...     temperature_range=(0.5, 1.0)
            ... )
            >>> for i, var in enumerate(variations):
            ...     print(f"Variation {i+1}: {var['content'][:50]}...")
        """
        results = []
        
        for i in range(count):
            # Create variation-specific overrides
            overrides: Dict[str, Any] = {}
            
            if temperature_range:
                # Vary temperature linearly across range
                min_temp, max_temp = temperature_range
                if count > 1:
                    temp = min_temp + (max_temp - min_temp) * (i / (count - 1))
                else:
                    temp = (min_temp + max_temp) / 2
                overrides['temperature'] = temp
            
            # Add variation context to variables
            variation_vars = variables.copy()
            variation_vars['_variation_number'] = i + 1
            variation_vars['_total_variations'] = count
            
            # Generate (don't use cache for variations)
            result = self.generate(
                template_name,
                variation_vars,
                use_cache=False,
                **overrides
            )
            
            # Add variation metadata
            result['variation_number'] = i + 1
            result['variation_temperature'] = overrides.get('temperature')
            
            results.append(result)
        
        return results
    
    def generate_batch(
        self,
        requests: List[Dict[str, Any]],
        parallel: bool = False
    ) -> List[Dict[str, Any]]:
        """Process multiple generation requests.
        
        Args:
            requests: List of request dictionaries, each containing:
                     - template_name: Name of template to use
                     - variables: Dict of template variables (optional)
            parallel: Whether to process requests in parallel (default: False).
        
        Returns:
            List of result dictionaries in same order as input.
        
        Example:
            >>> requests = [
            ...     {'template_name': 'product_description', 'variables': {...}},
            ...     {'template_name': 'meta_description', 'variables': {...}},
            ... ]
            >>> results = generator.generate_batch(requests)
        """
        if not requests:
            return []
        
        # Validate all requests first
        validated_requests = []
        for i, req in enumerate(requests):
            if not isinstance(req, dict):
                validated_requests.append({
                    'valid': False,
                    'error': f"Request {i} is not a dictionary"
                })
                continue
            
            template_name = req.get('template_name')
            if not template_name:
                validated_requests.append({
                    'valid': False,
                    'error': f"Request {i} missing 'template_name'"
                })
                continue
            
            validated_requests.append({
                'valid': True,
                'template_name': template_name,
                'variables': req.get('variables', {})
            })
        
        # Process requests
        results = []
        
        if parallel and self.api_manager:
            # Parallel processing
            results = self._process_batch_parallel(validated_requests)
        else:
            # Sequential processing
            for req in validated_requests:
                if not req['valid']:
                    results.append({
                        'success': False,
                        'error': req['error'],
                        'timestamp': format_timestamp(),
                        'request_id': generate_request_id(),
                    })
                else:
                    result = self.generate(
                        req['template_name'],
                        req['variables']
                    )
                    results.append(result)
        
        return results
    
    def _process_batch_parallel(
        self,
        validated_requests: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Process batch requests in parallel using threads."""
        import concurrent.futures
        
        results = [None] * len(validated_requests)
        
        def process_single(index: int, req: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
            if not req['valid']:
                return index, {
                    'success': False,
                    'error': req['error'],
                    'timestamp': format_timestamp(),
                    'request_id': generate_request_id(),
                }
            return index, self.generate(req['template_name'], req['variables'])
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [
                executor.submit(process_single, i, req)
                for i, req in enumerate(validated_requests)
            ]
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    index, result = future.result()
                    results[index] = result
                except Exception as e:
                    logger.error(f"Parallel batch processing error: {e}")
        
        return results
    
    # =========================================================================
    # HISTORY MANAGEMENT
    # =========================================================================
    
    def get_history(
        self,
        limit: Optional[int] = None,
        template_filter: Optional[str] = None,
        start_date: Optional[datetime] = None,
        success_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Retrieve generation history with optional filtering.
        
        Args:
            limit: Maximum number of items to return.
            template_filter: Only include items using this template.
            start_date: Only include items after this date.
            success_only: Only include successful generations.
        
        Returns:
            List of history items (deep copy to prevent modification).
        
        Example:
            >>> # Get last 10 successful product descriptions
            >>> history = generator.get_history(
            ...     limit=10,
            ...     template_filter='product_description',
            ...     success_only=True
            ... )
        """
        with self._lock:
            filtered = self._history.copy()
        
        # Apply filters
        if template_filter:
            filtered = [
                h for h in filtered
                if h.get('template_used') == template_filter
            ]
        
        if start_date:
            start_iso = start_date.isoformat() if isinstance(start_date, datetime) else str(start_date)
            filtered = [
                h for h in filtered
                if h.get('timestamp', '') >= start_iso
            ]
        
        if success_only:
            filtered = [h for h in filtered if h.get('success', False)]
        
        # Apply limit
        if limit:
            filtered = filtered[-limit:]
        
        # Return deep copy
        import copy
        return copy.deepcopy(filtered)
    
    def export_history(
        self,
        filepath: str,
        format: str = 'json'
    ) -> None:
        """Export generation history to file.
        
        Args:
            filepath: Path to save file.
            format: Export format ('json', 'csv', or 'txt').
        
        Raises:
            ValueError: If format is not supported.
        
        Example:
            >>> generator.export_history('history.json', format='json')
            >>> generator.export_history('history.csv', format='csv')
        """
        format = format.lower()
        
        with self._lock:
            history = self._history.copy()
        
        if format == 'json':
            export_data = {
                'session_id': self.session_id,
                'session_start': self._session_start.isoformat(),
                'export_timestamp': format_timestamp(),
                'total_entries': len(history),
                'history': history
            }
            save_json_file(export_data, filepath)
            
        elif format == 'csv':
            if not history:
                Path(filepath).write_text('')
                return
            
            # Flatten nested dicts for CSV
            flat_history = []
            for item in history:
                flat_item = {
                    'success': item.get('success'),
                    'template_used': item.get('template_used'),
                    'timestamp': item.get('timestamp'),
                    'request_id': item.get('request_id'),
                    'model': item.get('model'),
                    'tokens_prompt': item.get('tokens_used', {}).get('prompt', 0),
                    'tokens_completion': item.get('tokens_used', {}).get('completion', 0),
                    'tokens_total': item.get('tokens_used', {}).get('total', 0),
                    'cost': item.get('cost', 0),
                    'cached': item.get('cached', False),
                    'generation_time': item.get('generation_time', 0),
                    'content_preview': (item.get('content', '')[:100] + '...')
                        if len(item.get('content', '')) > 100
                        else item.get('content', ''),
                    'error': item.get('error', ''),
                }
                flat_history.append(flat_item)
            
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=flat_history[0].keys())
                writer.writeheader()
                writer.writerows(flat_history)
                
        elif format == 'txt':
            lines = [
                f"Content Generation History",
                f"Session ID: {self.session_id}",
                f"Session Start: {self._session_start.isoformat()}",
                f"Export Time: {format_timestamp()}",
                f"Total Entries: {len(history)}",
                "=" * 60,
                ""
            ]
            
            for i, item in enumerate(history, 1):
                lines.extend([
                    f"[{i}] {item.get('timestamp', 'N/A')}",
                    f"    Template: {item.get('template_used', 'N/A')}",
                    f"    Success: {item.get('success', False)}",
                    f"    Model: {item.get('model', 'N/A')}",
                    f"    Tokens: {item.get('tokens_used', {}).get('total', 0)}",
                    f"    Cost: ${item.get('cost', 0):.6f}",
                    f"    Cached: {item.get('cached', False)}",
                ])
                
                if item.get('success'):
                    content = item.get('content', '')[:200]
                    lines.append(f"    Content: {content}...")
                else:
                    lines.append(f"    Error: {item.get('error', 'Unknown')}")
                
                lines.append("-" * 40)
            
            Path(filepath).write_text('\n'.join(lines), encoding='utf-8')
            
        else:
            raise ValueError(f"Unsupported format: {format}. Use 'json', 'csv', or 'txt'.")
        
        logger.info(f"History exported to {filepath} ({format} format)")
    
    def clear_history(self) -> int:
        """Clear all generation history.
        
        Returns:
            Number of history entries cleared.
        """
        with self._lock:
            count = len(self._history)
            self._history.clear()
        
        logger.info(f"Cleared {count} history entries")
        return count
    
    def _add_to_history(self, result: Dict[str, Any]) -> None:
        """Add result to history, trimming if necessary."""
        with self._lock:
            self._history.append(result.copy())
            
            # Trim if exceeds max size
            while len(self._history) > MAX_HISTORY_SIZE:
                self._history.pop(0)
    
    # =========================================================================
    # CACHE MANAGEMENT
    # =========================================================================
    
    def clear_cache(self) -> int:
        """Clear the result cache.
        
        Returns:
            Number of cache entries cleared.
        """
        count = self._cache.clear()
        logger.info(f"Cleared {count} cache entries")
        return count
    
    def _generate_cache_key(
        self,
        template_name: str,
        variables: Dict[str, Any]
    ) -> str:
        """Generate unique cache key for template + variables."""
        # Sort variables for consistent hashing
        sorted_vars = json.dumps(variables, sort_keys=True, default=str)
        return create_hash(f"{template_name}:{sorted_vars}")
    
    # =========================================================================
    # STATISTICS
    # =========================================================================
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive usage statistics.
        
        Returns:
            Dictionary containing:
            - total_generations: Total number of generations
            - total_cost: Total cost in USD
            - total_tokens: Total tokens consumed
            - templates_used: Count per template
            - success_rate: Percentage of successful generations
            - cache_hit_rate: Percentage of cache hits
            - average_generation_time: Average time in seconds
            - cost_by_template: Cost breakdown by template
            - session_id: Current session ID
            - session_start: Session start timestamp
        
        Example:
            >>> stats = generator.get_statistics()
            >>> print(f"Total cost: ${stats['total_cost']:.2f}")
            >>> print(f"Success rate: {stats['success_rate']:.1f}%")
        """
        with self._lock:
            history = self._history.copy()
        
        if not history:
            return {
                'total_generations': 0,
                'total_cost': 0.0,
                'total_tokens': 0,
                'templates_used': {},
                'success_rate': 0.0,
                'cache_hit_rate': self._cache.hit_rate,
                'average_generation_time': 0.0,
                'cost_by_template': {},
                'session_id': self.session_id,
                'session_start': self._session_start.isoformat(),
            }
        
        # Calculate statistics
        total_generations = len(history)
        successful = [h for h in history if h.get('success', False)]
        total_successful = len(successful)
        
        total_cost = sum(h.get('cost', 0) for h in history)
        total_tokens = sum(h.get('tokens_used', {}).get('total', 0) for h in history)
        
        # Template counts
        templates_used: Dict[str, int] = {}
        cost_by_template: Dict[str, float] = {}
        
        for h in history:
            template = h.get('template_used', 'unknown')
            templates_used[template] = templates_used.get(template, 0) + 1
            cost_by_template[template] = cost_by_template.get(template, 0) + h.get('cost', 0)
        
        # Average generation time
        gen_times = [h.get('generation_time', 0) for h in history if h.get('generation_time', 0) > 0]
        avg_gen_time = sum(gen_times) / len(gen_times) if gen_times else 0.0
        
        return {
            'total_generations': total_generations,
            'total_cost': round(total_cost, 6),
            'total_tokens': total_tokens,
            'templates_used': templates_used,
            'success_rate': (total_successful / total_generations * 100) if total_generations > 0 else 0.0,
            'cache_hit_rate': self._cache.hit_rate,
            'average_generation_time': round(avg_gen_time, 3),
            'cost_by_template': {k: round(v, 6) for k, v in cost_by_template.items()},
            'session_id': self.session_id,
            'session_start': self._session_start.isoformat(),
            'history_size': len(history),
            'cache_size': len(self._cache),
        }
    
    # =========================================================================
    # COST ESTIMATION
    # =========================================================================
    
    def estimate_cost(
        self,
        template_name: str,
        variables: Dict[str, Any],
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Estimate cost before generating content.
        
        This method allows you to preview the approximate cost of a generation
        without actually making an API call. Useful for budgeting and planning.
        
        Args:
            template_name: Name of the template to use.
            variables: Template variables.
            model: Optional model override (uses default if not specified).
        
        Returns:
            Dictionary containing:
            - success: Whether estimation succeeded
            - estimated_prompt_tokens: Estimated input tokens
            - estimated_completion_tokens: Estimated output tokens
            - estimated_total_tokens: Total estimated tokens
            - estimated_cost: Estimated cost in USD
            - model: Model used for estimation
            - error: Error message (only on failure)
        
        Example:
            >>> estimate = generator.estimate_cost(
            ...     'product_description',
            ...     {'product_name': 'Widget', 'features': 'Fast', 'audience': 'Users'}
            ... )
            >>> if estimate['success']:
            ...     print(f"Estimated cost: ${estimate['estimated_cost']:.4f}")
            ...     if estimate['estimated_cost'] > budget:
            ...         print("Warning: exceeds budget!")
        """
        result = {
            'success': False,
            'estimated_prompt_tokens': 0,
            'estimated_completion_tokens': 0,
            'estimated_total_tokens': 0,
            'estimated_cost': 0.0,
            'model': model or 'gpt-4o-mini',
        }
        
        try:
            # Validate template exists
            try:
                template = self.prompt_engine.get_template(template_name)
            except TemplateNotFoundError:
                result['error'] = f"Template '{template_name}' not found"
                return result
            
            # Validate variables
            required = getattr(template, 'required_variables', []) or []
            missing = [var for var in required if var not in variables]
            if missing:
                result['error'] = f"Missing required variables: {missing}"
                return result
            
            # Generate the full prompt
            try:
                prompt_text = template.generate(variables, include_system=True)
            except VariableValidationError as e:
                result['error'] = f"Variable validation failed: {e}"
                return result
            
            # Estimate prompt tokens
            from .utils import calculate_token_count
            prompt_tokens = calculate_token_count(prompt_text)
            
            # Estimate completion tokens based on template settings
            max_tokens = getattr(template, 'max_tokens_recommendation', 500) or 500
            # Assume average completion is about 60% of max_tokens
            estimated_completion = int(max_tokens * 0.6)
            
            total_tokens = prompt_tokens + estimated_completion
            
            # Get model for cost calculation
            use_model = model or 'gpt-4o-mini'
            result['model'] = use_model
            
            # Calculate estimated cost using API manager if available
            if self.api_manager and hasattr(self.api_manager, 'estimate_cost'):
                cost_estimate = self.api_manager.estimate_cost(
                    text=prompt_text,
                    model=use_model
                )
                estimated_cost = cost_estimate.get('total_cost', 0.0)
                # Use API manager's token estimates if available
                prompt_tokens = cost_estimate.get('input_tokens', prompt_tokens)
                estimated_completion = cost_estimate.get('estimated_output_tokens', estimated_completion)
                total_tokens = prompt_tokens + estimated_completion
            else:
                # Fallback cost estimation (approximate rates)
                # GPT-4o-mini: ~$0.00015/1K input, ~$0.0006/1K output
                # GPT-4o: ~$0.005/1K input, ~$0.015/1K output
                cost_rates = {
                    'gpt-4o-mini': {'input': 0.00015, 'output': 0.0006},
                    'gpt-4o': {'input': 0.005, 'output': 0.015},
                    'gpt-4': {'input': 0.03, 'output': 0.06},
                    'gpt-3.5-turbo': {'input': 0.0005, 'output': 0.0015},
                }
                rates = cost_rates.get(use_model, cost_rates['gpt-4o-mini'])
                estimated_cost = (
                    (prompt_tokens / 1000) * rates['input'] +
                    (estimated_completion / 1000) * rates['output']
                )
            
            result.update({
                'success': True,
                'estimated_prompt_tokens': prompt_tokens,
                'estimated_completion_tokens': estimated_completion,
                'estimated_total_tokens': total_tokens,
                'estimated_cost': round(estimated_cost, 6),
            })
            
            return result
            
        except Exception as e:
            result['error'] = f"Estimation failed: {str(e)}"
            logger.error(f"Cost estimation error: {e}")
            return result
    
    # =========================================================================
    # TEMPLATE MANAGEMENT
    # =========================================================================
    
    def list_available_templates(self) -> List[Dict[str, str]]:
        """Get all available templates with their descriptions.
        
        Returns:
            List of dictionaries with template name, description, and category.
        
        Example:
            >>> templates = generator.list_available_templates()
            >>> for t in templates:
            ...     print(f"{t['name']}: {t['description']}")
        """
        template_names = self.prompt_engine.list_templates()
        result = []
        
        for name in template_names:
            try:
                info = self.prompt_engine.get_template_info(name)
                result.append({
                    'name': name,
                    'description': info.get('description', 'No description'),
                    'category': info.get('category', 'uncategorized'),
                    'version': info.get('version', '1.0'),
                    'required_variables': info.get('required_variables', []),
                })
            except Exception:
                result.append({
                    'name': name,
                    'description': 'Unknown',
                    'category': 'unknown',
                })
        
        return result
    
    def validate_template_variables(
        self,
        template_name: str,
        variables: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """Check if variables match template requirements.
        
        Args:
            template_name: Name of the template.
            variables: Variables to validate.
        
        Returns:
            Tuple of (is_valid, list_of_missing_variables).
        
        Example:
            >>> valid, missing = generator.validate_template_variables(
            ...     'product_description',
            ...     {'product_name': 'Widget'}
            ... )
            >>> if not valid:
            ...     print(f"Missing: {missing}")
        """
        try:
            template = self.prompt_engine.get_template(template_name)
        except TemplateNotFoundError:
            return False, [f"Template '{template_name}' not found"]
        
        required = getattr(template, 'required_variables', []) or []
        missing = [var for var in required if var not in variables]
        
        return len(missing) == 0, missing
    
    def register_template(
        self,
        name: str,
        template: str,
        system_instructions: str = "You are a helpful assistant.",
        required_variables: Optional[List[str]] = None,
        optional_variables: Optional[Dict[str, str]] = None,
        **kwargs: Any
    ) -> PromptTemplate:
        """Register a new template.
        
        Args:
            name: Unique template identifier.
            template: Template string with {variable} placeholders.
            system_instructions: Context for the AI model.
            required_variables: List of required variable names.
            optional_variables: Dict of optional variables with defaults.
            **kwargs: Additional PromptTemplate attributes.
        
        Returns:
            The registered PromptTemplate instance.
        
        Example:
            >>> generator.register_template(
            ...     name='quick_post',
            ...     template='Write a quick post about {topic}.',
            ...     required_variables=['topic']
            ... )
        """
        new_template = create_template(
            name=name,
            template=template,
            system_instructions=system_instructions,
            required_variables=required_variables,
            optional_variables=optional_variables,
            **kwargs
        )
        self.prompt_engine.register_template(new_template)
        logger.info(f"Registered template: {name}")
        return new_template
    
    def list_templates(self, category: Optional[str] = None) -> List[str]:
        """List available template names.
        
        Args:
            category: Optional category filter.
        
        Returns:
            List of template names.
        """
        return self.prompt_engine.list_templates(category=category)
    
    def get_template_info(self, name: str) -> Dict[str, Any]:
        """Get information about a specific template.
        
        Args:
            name: Template name.
        
        Returns:
            Dictionary with template details.
        """
        return self.prompt_engine.get_template_info(name)


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_generator(
    api_key: Optional[str] = None,
    load_defaults: bool = True,
    **kwargs: Any
) -> ContentGenerator:
    """Factory function to create a ContentGenerator with defaults.
    
    Args:
        api_key: Optional API key.
        load_defaults: Whether to load built-in templates.
        **kwargs: Additional arguments for ContentGenerator.
    
    Returns:
        Configured ContentGenerator instance.
    
    Example:
        >>> generator = create_generator()
        >>> result = generator.generate('product_description', {...})
    """
    return ContentGenerator(
        api_key=api_key,
        load_defaults=load_defaults,
        **kwargs
    )


def create_mock_generator(
    mock_response: str = "Mock generated content",
    **kwargs: Any
) -> ContentGenerator:
    """Factory function to create a ContentGenerator with mock API for testing.
    
    Args:
        mock_response: Content to return for all generations.
        **kwargs: Additional arguments for ContentGenerator.
    
    Returns:
        ContentGenerator with mock API manager.
    
    Example:
        >>> mock_gen = create_mock_generator("Test content")
        >>> result = mock_gen.generate('any_template', {...})
        >>> assert result['content'] == "Test content"
    """
    mock_api = create_mock_manager(mock_response=mock_response)
    return ContentGenerator(
        api_manager=mock_api,
        load_defaults=True,
        **kwargs
    )


# =============================================================================
# BACKWARD COMPATIBILITY
# =============================================================================

# Keep old function for compatibility
def build_chat_messages(prompt: str) -> List[Dict[str, str]]:
    """Wrap plain text into OpenAI chat message format."""
    from .utils import build_chat_messages as _build_chat_messages
    return _build_chat_messages(prompt)


# =============================================================================
# MAIN DEMO
# =============================================================================

def main() -> None:  # pragma: no cover - convenience entry point
    """Demo the content generator with a mock API."""
    print("\n" + "=" * 60)
    print("  AI Content Generator - Demo")
    print("=" * 60)
    
    # Create generator with mock API
    generator = create_mock_generator(
        mock_response="This is a beautifully crafted product description "
                     "that highlights all the amazing features of your product."
    )
    
    # Show available templates
    print("\nAvailable templates:")
    for template in generator.list_available_templates()[:5]:
        print(f"  - {template['name']}: {template['description'][:50]}...")
    
    # Generate content
    print("\n" + "-" * 60)
    print("Generating product description...")
    print("-" * 60)
    
    result = generator.generate(
        'product_description',
        product_name='Smart Watch Pro',
        features='heart rate monitor, GPS tracking, 7-day battery',
        audience='fitness enthusiasts and busy professionals',
        tone='energetic',
        length='120'
    )
    
    if result['success']:
        print(f"\nContent: {result['content']}")
        print(f"\nMetadata:")
        print(f"  Model: {result['model']}")
        print(f"  Tokens: {result['tokens_used']['total']}")
        print(f"  Cost: ${result['cost']:.6f}")
        print(f"  Time: {result['generation_time']:.3f}s")
        print(f"  Request ID: {result['request_id']}")
    else:
        print(f"\nError: {result.get('error', 'Unknown error')}")
    
    # Generate variations
    print("\n" + "-" * 60)
    print("Generating 3 variations...")
    print("-" * 60)
    
    variations = generator.generate_multiple_variations(
        'social_media_post',
        {'platform': 'Twitter', 'topic': 'AI trends', 'cta': 'Follow for more!'},
        count=3,
        temperature_range=(0.5, 1.0)
    )
    
    for var in variations:
        print(f"\n  Variation {var.get('variation_number')} "
              f"(temp={var.get('variation_temperature', 0):.2f}):")
        print(f"    Success: {var['success']}")
    
    # Show statistics
    print("\n" + "-" * 60)
    print("Session Statistics:")
    print("-" * 60)
    
    stats = generator.get_statistics()
    print(f"  Total generations: {stats['total_generations']}")
    print(f"  Total cost: ${stats['total_cost']:.4f}")
    print(f"  Success rate: {stats['success_rate']:.1f}%")
    print(f"  Session ID: {stats['session_id'][:8]}...")
    
    print("\n[Demo completed successfully]")


if __name__ == "__main__":  # pragma: no cover
    main()
