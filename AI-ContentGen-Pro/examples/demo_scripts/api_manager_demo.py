#!/usr/bin/env python3
"""Demo script showcasing the Enterprise-grade OpenAI API Manager.

This script demonstrates all major features of the api_manager module:
1. Basic content generation
2. Batch generation (sequential and parallel)
3. Error handling
4. Cost estimation
5. Usage statistics
6. Caching behavior
7. Mock manager for testing
8. Monitoring callbacks

Run with: python examples/demo_scripts/api_manager_demo.py

Author: AI-ContentGen-Pro Team
"""

import os
import sys
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.api_manager import (
    OpenAIManager,
    MockOpenAIManager,
    create_manager,
    create_mock_manager,
    # Utilities
    mask_api_key,
    sanitize_prompt_for_log,
    # Exceptions
    InvalidPromptError,
    RateLimitExceeded,
    APIKeyInvalidError,
)


def print_header(title: str) -> None:
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_response(result: dict, show_content: bool = True) -> None:
    """Print formatted API response."""
    print(f"  Success: {result['success']}")
    print(f"  Request ID: {result['request_id']}")
    
    if result['success']:
        if show_content:
            content = result['content'][:100] + "..." if len(result['content']) > 100 else result['content']
            print(f"  Content: {content}")
        print(f"  Model: {result['model']}")
        print(f"  Tokens: {result['tokens_used']['total']} (prompt: {result['tokens_used']['prompt']}, completion: {result['tokens_used']['completion']})")
        print(f"  Cost: ${result['cost']:.6f}")
        print(f"  Finish reason: {result['finish_reason']}")
        if result.get('latency_ms'):
            print(f"  Latency: {result['latency_ms']:.0f}ms")
    else:
        print(f"  Error: {result['error']}")


def demo_mock_manager() -> None:
    """Demonstrate using the mock manager for testing."""
    print_header("DEMO: Mock Manager for Testing")
    
    # Create mock manager
    mock = create_mock_manager(
        mock_response="This is a mock response for testing purposes.",
        mock_tokens=150,
    )
    
    print("\n[*] Creating mock manager with predefined response...")
    print(f"  Mock response: 'This is a mock response for testing purposes.'")
    print(f"  Mock tokens: 150")
    
    # Generate content
    print("\n[*] Generating content with mock manager...")
    result = mock.generate_content(
        prompt="Write about artificial intelligence",
        system_message="You are a tech writer"
    )
    print_response(result)
    
    # Batch generation
    print("\n[*] Batch generation (3 prompts)...")
    prompts = [
        "Write about machine learning",
        "Write about deep learning",
        "Write about neural networks",
    ]
    results = mock.generate_batch(prompts)
    print(f"  Generated {len(results)} responses")
    print(f"  All successful: {all(r['success'] for r in results)}")


def demo_cost_estimation() -> None:
    """Demonstrate cost estimation feature."""
    print_header("DEMO: Cost Estimation")
    
    mock = MockOpenAIManager()
    
    # Short prompt
    print("\n[*] Estimating cost for short prompt...")
    short_prompt = "Write a haiku about coding"
    estimate = mock.estimate_cost(short_prompt)
    print(f"  Prompt: '{short_prompt}'")
    print(f"  Input tokens: {estimate['input_tokens']}")
    print(f"  Estimated output tokens: {estimate['estimated_output_tokens']}")
    print(f"  Total tokens: {estimate['total_tokens']}")
    print(f"  Input cost: ${estimate['input_cost']:.6f}")
    print(f"  Output cost: ${estimate['output_cost']:.6f}")
    print(f"  Total estimated cost: ${estimate['total_cost']:.6f}")
    
    # Long prompt
    print("\n[*] Estimating cost for long prompt...")
    long_prompt = "Write a comprehensive guide about " + "software development " * 50
    estimate = mock.estimate_cost(long_prompt)
    print(f"  Prompt length: {len(long_prompt)} characters")
    print(f"  Input tokens: {estimate['input_tokens']}")
    print(f"  Estimated output tokens: {estimate['estimated_output_tokens']}")
    print(f"  Total estimated cost: ${estimate['total_cost']:.6f}")
    
    # Different models
    print("\n[*] Cost comparison across models...")
    test_prompt = "Write a blog post about AI trends"
    for model in ["gpt-3.5-turbo", "gpt-4", "gpt-4o"]:
        estimate = mock.estimate_cost(test_prompt, model=model)
        print(f"  {model}: ${estimate['total_cost']:.6f} ({estimate['total_tokens']} tokens)")


def demo_usage_statistics() -> None:
    """Demonstrate usage statistics tracking."""
    print_header("DEMO: Usage Statistics")
    
    mock = create_mock_manager(mock_response="Generated content", mock_tokens=100)
    
    print("\n[*] Initial statistics (before any requests)...")
    stats = mock.get_usage_statistics()
    print(f"  Total requests: {stats['total_requests']}")
    print(f"  Successful: {stats['successful_requests']}")
    print(f"  Failed: {stats['failed_requests']}")
    print(f"  Total tokens: {stats['total_tokens']}")
    print(f"  Total cost: ${stats['total_cost']:.6f}")
    
    # Generate some content
    print("\n[*] Generating 5 pieces of content...")
    for i in range(5):
        mock.generate_content(f"Prompt {i+1}")
    
    print("\n[*] Statistics after 5 requests...")
    stats = mock.get_usage_statistics()
    print(f"  Total requests: {stats['total_requests']}")
    print(f"  Successful: {stats['successful_requests']}")
    print(f"  Success rate: {stats['success_rate']:.1f}%")
    print(f"  Total tokens: {stats['total_tokens']}")
    print(f"  Total cost: ${stats['total_cost']:.6f}")
    
    # Export metrics
    print("\n[*] Exporting metrics for monitoring...")
    metrics = mock.export_metrics()
    for key, value in metrics.items():
        print(f"  {key}: {value}")


def demo_caching() -> None:
    """Demonstrate response caching."""
    print_header("DEMO: Response Caching")
    
    mock = MockOpenAIManager(mock_response="Cached response")
    
    print("\n[*] First request (cache miss)...")
    result1 = mock.generate_content("Same prompt for caching test")
    print(f"  Request ID: {result1['request_id']}")
    
    print("\n[*] Second request with same prompt (cache hit)...")
    result2 = mock.generate_content("Same prompt for caching test")
    print(f"  Request ID: {result2['request_id']}")
    print(f"  Note: Different request IDs but same content from cache")
    
    print("\n[*] Request with cache disabled...")
    result3 = mock.generate_content("Same prompt for caching test", use_cache=False)
    print(f"  Request ID: {result3['request_id']}")
    
    print("\n[*] Clearing cache...")
    cleared = mock.clear_cache()
    print(f"  Cleared {cleared} cache entries")


def demo_error_handling() -> None:
    """Demonstrate error handling."""
    print_header("DEMO: Error Handling")
    
    mock = MockOpenAIManager()
    
    # Empty prompt
    print("\n[*] Testing empty prompt validation...")
    try:
        mock.generate_content("")
    except InvalidPromptError as e:
        print(f"  [OK] Caught InvalidPromptError: {e}")
    
    # Whitespace-only prompt
    print("\n[*] Testing whitespace-only prompt...")
    try:
        mock.generate_content("   ")
    except InvalidPromptError as e:
        print(f"  [OK] Caught InvalidPromptError: {e}")
    
    # Mock failure mode
    print("\n[*] Testing mock failure mode...")
    failing_mock = MockOpenAIManager(should_fail=True, fail_error="Simulated API failure")
    result = failing_mock.generate_content("Test prompt")
    print(f"  Success: {result['success']}")
    print(f"  Error: {result['error']}")


def demo_utility_functions() -> None:
    """Demonstrate utility functions."""
    print_header("DEMO: Utility Functions")
    
    # API key masking
    print("\n[*] API Key Masking...")
    keys = [
        "sk-1234567890abcdefghijklmnop",
        "sk-test",
        "",
    ]
    for key in keys:
        masked = mask_api_key(key)
        display_key = key if key else "(empty)"
        print(f"  '{display_key}' -> '{masked}'")
    
    # Prompt sanitization
    print("\n[*] Prompt Sanitization...")
    prompts = [
        "Contact john@example.com for info",
        "Call me at 555-123-4567",
        "SSN: 123-45-6789",
        "A" * 200,  # Long prompt
    ]
    for prompt in prompts:
        sanitized = sanitize_prompt_for_log(prompt, max_length=50)
        print(f"  Original: '{prompt[:40]}...'")
        print(f"  Sanitized: '{sanitized}'")
        print()


def demo_batch_generation() -> None:
    """Demonstrate batch generation."""
    print_header("DEMO: Batch Generation")
    
    mock = MockOpenAIManager(mock_response="Batch generated content")
    
    prompts = [
        "Write about cats",
        "Write about dogs",
        "Write about birds",
        "Write about fish",
    ]
    
    # Sequential batch
    print("\n[*] Sequential batch generation (4 prompts)...")
    import time
    start = time.perf_counter()
    results = mock.generate_batch(prompts, parallel=False)
    seq_time = time.perf_counter() - start
    print(f"  Time: {seq_time*1000:.0f}ms")
    print(f"  Results: {len(results)}")
    print(f"  All successful: {all(r['success'] for r in results)}")
    
    # Parallel batch
    print("\n[*] Parallel batch generation (4 prompts)...")
    start = time.perf_counter()
    results = mock.generate_batch(prompts, parallel=True)
    par_time = time.perf_counter() - start
    print(f"  Time: {par_time*1000:.0f}ms")
    print(f"  Results: {len(results)}")
    print(f"  All successful: {all(r['success'] for r in results)}")


def demo_monitoring_callback() -> None:
    """Demonstrate monitoring callbacks."""
    print_header("DEMO: Monitoring Callbacks")
    
    class SimpleMonitor:
        """Simple monitoring callback implementation."""
        
        def __init__(self):
            self.requests = []
            self.completions = []
            self.errors = []
        
        def on_request_start(self, request_id: str, prompt: str, model: str) -> None:
            self.requests.append({
                'request_id': request_id,
                'prompt_preview': prompt[:30],
                'model': model,
                'timestamp': datetime.now().isoformat()
            })
            print(f"  [MONITOR] Request started: {request_id}")
        
        def on_request_complete(self, request_id: str, response) -> None:
            self.completions.append({
                'request_id': request_id,
                'success': response.success,
                'tokens': response.tokens_used.total_tokens if response.success else 0
            })
            print(f"  [MONITOR] Request completed: {request_id} (success={response.success})")
        
        def on_request_error(self, request_id: str, error: Exception) -> None:
            self.errors.append({
                'request_id': request_id,
                'error': str(error)
            })
            print(f"  [MONITOR] Request error: {request_id} - {error}")
    
    print("\n[*] Creating manager with monitoring callback...")
    monitor = SimpleMonitor()
    
    # We'll use a mock client to demonstrate
    from unittest.mock import Mock
    
    mock_choice = Mock()
    mock_choice.message.content = "Monitored response"
    mock_choice.finish_reason = "stop"
    
    mock_usage = Mock()
    mock_usage.prompt_tokens = 50
    mock_usage.completion_tokens = 100
    mock_usage.total_tokens = 150
    
    mock_response = Mock()
    mock_response.choices = [mock_choice]
    mock_response.usage = mock_usage
    
    mock_client = Mock()
    mock_client.chat.completions.create.return_value = mock_response
    
    manager = OpenAIManager(
        api_key="sk-test",
        client=mock_client,
        monitoring_callback=monitor,
    )
    
    print("\n[*] Generating content with monitoring enabled...")
    result = manager.generate_content("Test prompt for monitoring")
    
    print("\n[*] Monitor captured events:")
    print(f"  Requests started: {len(monitor.requests)}")
    print(f"  Requests completed: {len(monitor.completions)}")
    print(f"  Errors: {len(monitor.errors)}")


def main():
    """Run all demos."""
    print("\n" + "#" * 70)
    print("#  Enterprise-grade OpenAI API Manager - Feature Demo")
    print("#" * 70)
    print(f"\n  Demo started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("  Note: Using MockOpenAIManager - no actual API calls are made")
    
    try:
        demo_mock_manager()
        demo_cost_estimation()
        demo_usage_statistics()
        demo_caching()
        demo_error_handling()
        demo_utility_functions()
        demo_batch_generation()
        demo_monitoring_callback()
        
        print_header("DEMO COMPLETE")
        print("\n  All demos completed successfully!")
        print("\n  Key Features Demonstrated:")
        print("  - Mock manager for testing without API calls")
        print("  - Cost estimation before making requests")
        print("  - Comprehensive usage statistics tracking")
        print("  - Response caching with TTL")
        print("  - Robust error handling with custom exceptions")
        print("  - Utility functions for security (masking, sanitization)")
        print("  - Batch generation (sequential and parallel)")
        print("  - Monitoring callbacks for observability")
        print("\n  For production use with real OpenAI API:")
        print("  1. Set OPENAI_API_KEY in .env file")
        print("  2. Use create_manager() or OpenAIManager()")
        print("  3. Call generate_content() with your prompts")
        
    except Exception as e:
        print(f"\n[ERROR] Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
