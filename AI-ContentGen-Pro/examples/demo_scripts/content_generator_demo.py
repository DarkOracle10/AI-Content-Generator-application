"""Demonstration script for the ContentGenerator orchestrator.

This script showcases all the key features of the ContentGenerator:
- Basic content generation
- Multiple variations
- Batch processing
- History tracking
- Cache management
- Statistics
- Callbacks
- Export functionality
- Context manager support

Run with: python -m examples.demo_scripts.content_generator_demo
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.content_generator import (
    ContentGenerator,
    create_generator,
    create_mock_generator,
)


def print_header(title: str) -> None:
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_subheader(title: str) -> None:
    """Print a formatted subheader."""
    print("\n" + "-" * 50)
    print(f"  {title}")
    print("-" * 50)


def demo_basic_generation(gen: ContentGenerator) -> None:
    """Demonstrate basic content generation."""
    print_subheader("Basic Generation")
    
    result = gen.generate(
        "product_description",
        product_name="Smart Watch Pro",
        features="Heart Rate Monitor, GPS, 7-day Battery, Water Resistant",
        audience="Fitness enthusiasts and busy professionals",
        tone="energetic",
        length="120"
    )
    
    print(f"\nTemplate: product_description")
    print(f"Success: {result['success']}")
    
    if result['success']:
        print(f"\nGenerated Content:")
        print(f"  {result['content']}")
        print(f"\nMetadata:")
        print(f"  - Request ID: {result['request_id'][:8]}...")
        print(f"  - Timestamp: {result['timestamp'][:19]}")
        print(f"  - Tokens: {result['tokens_used']['total']}")
        print(f"  - Cost: ${result['cost']:.6f}")
        print(f"  - Generation Time: {result['generation_time']:.3f}s")
        print(f"  - Cached: {result['cached']}")
    else:
        print(f"  Error: {result.get('error')}")


def demo_cache_functionality(gen: ContentGenerator) -> None:
    """Demonstrate caching functionality."""
    print_subheader("Cache Functionality")
    
    variables = {
        "product_name": "Wireless Earbuds",
        "features": "Noise Cancellation, 30hr Battery",
        "audience": "Music Lovers",
    }
    
    # First generation (cache miss)
    result1 = gen.generate("product_description", variables=variables)
    print(f"\n1st generation - Cached: {result1['cached']} (cache miss)")
    print(f"   Time: {result1['generation_time']:.4f}s")
    
    # Second generation (cache hit)
    result2 = gen.generate("product_description", variables=variables)
    print(f"2nd generation - Cached: {result2['cached']} (cache hit)")
    print(f"   Time: {result2['generation_time']:.4f}s")
    
    # Generation with cache disabled
    result3 = gen.generate("product_description", variables=variables, use_cache=False)
    print(f"3rd generation - Cached: {result3['cached']} (cache disabled)")
    print(f"   Time: {result3['generation_time']:.4f}s")
    
    print(f"\nCache hit rate: {gen._cache.hit_rate:.1f}%")


def demo_multiple_variations(gen: ContentGenerator) -> None:
    """Demonstrate generating multiple variations."""
    print_subheader("Multiple Variations")
    
    variations = gen.generate_multiple_variations(
        "social_media_post",
        {
            "platform": "Twitter",
            "topic": "AI-powered productivity tools",
            "cta": "Try it free today!"
        },
        count=3,
        temperature_range=(0.5, 1.0)
    )
    
    print(f"\nGenerated {len(variations)} variations:")
    for var in variations:
        print(f"\n  Variation #{var['variation_number']}:")
        print(f"    Temperature: {var.get('variation_temperature', 0):.2f}")
        print(f"    Success: {var['success']}")
        if var['success']:
            content_preview = var['content'][:60] + "..." if len(var['content']) > 60 else var['content']
            print(f"    Content: {content_preview}")


def demo_batch_processing(gen: ContentGenerator) -> None:
    """Demonstrate batch processing."""
    print_subheader("Batch Processing")
    
    requests = [
        {
            "template_name": "product_description",
            "variables": {
                "product_name": "Laptop Stand",
                "features": "Ergonomic, Aluminum, Adjustable",
                "audience": "Remote Workers"
            }
        },
        {
            "template_name": "meta_description",
            "variables": {
                "page_topic": "Home Office Setup Guide",
                "primary_keyword": "ergonomic workspace",
                "brand": "WorkSmart"
            }
        },
        {
            "template_name": "social_media_post",
            "variables": {
                "platform": "LinkedIn",
                "topic": "Remote Work Tips",
                "cta": "Share your tips below!"
            }
        }
    ]
    
    print(f"\nProcessing {len(requests)} requests in batch...")
    results = gen.generate_batch(requests, parallel=False)
    
    print("\nResults:")
    for i, result in enumerate(results, 1):
        status = "[OK]" if result['success'] else "[FAIL]"
        template = result.get('template_used', 'unknown')
        print(f"  {i}. {status} {template}")


def demo_callbacks(gen: ContentGenerator) -> None:
    """Demonstrate callback functionality."""
    print_subheader("Callbacks")
    
    # Track callback invocations
    callback_count = [0]
    
    def my_callback(result):
        callback_count[0] += 1
        status = "SUCCESS" if result['success'] else "FAILED"
        print(f"  [Callback #{callback_count[0]}] Generation {status} - "
              f"Template: {result['template_used']}")
    
    # Register callback
    gen.register_callback(my_callback)
    print("\nCallback registered. Generating content...")
    
    # Generate content (callback will be invoked)
    gen.generate(
        "product_description",
        product_name="Callback Test Product",
        features="Feature",
        audience="Testers",
        use_cache=False
    )
    
    # Unregister callback
    gen.unregister_callback(my_callback)
    print("\nCallback unregistered.")
    
    # Generate again (callback NOT invoked)
    gen.generate(
        "product_description",
        product_name="Another Product",
        features="Feature",
        audience="Testers",
        use_cache=False
    )
    print(f"\nTotal callback invocations: {callback_count[0]}")


def demo_history_and_statistics(gen: ContentGenerator) -> None:
    """Demonstrate history tracking and statistics."""
    print_subheader("History & Statistics")
    
    # Get statistics
    stats = gen.get_statistics()
    
    print("\nSession Statistics:")
    print(f"  - Session ID: {stats['session_id'][:8]}...")
    print(f"  - Total Generations: {stats['total_generations']}")
    print(f"  - Total Cost: ${stats['total_cost']:.6f}")
    print(f"  - Total Tokens: {stats['total_tokens']}")
    print(f"  - Success Rate: {stats['success_rate']:.1f}%")
    print(f"  - Cache Hit Rate: {stats['cache_hit_rate']:.1f}%")
    print(f"  - Avg Generation Time: {stats['average_generation_time']:.3f}s")
    
    print("\n  Templates Used:")
    for template, count in stats['templates_used'].items():
        cost = stats['cost_by_template'].get(template, 0)
        print(f"    - {template}: {count} times (${cost:.6f})")
    
    # Get history
    history = gen.get_history(limit=3)
    
    print(f"\n  Recent History (last {len(history)} items):")
    for item in history:
        status = "[OK]" if item['success'] else "[FAIL]"
        print(f"    {status} {item['template_used']} - {item['timestamp'][:19]}")


def demo_template_validation(gen: ContentGenerator) -> None:
    """Demonstrate template validation."""
    print_subheader("Template Validation & Cost Estimation")
    
    # List available templates
    templates = gen.list_available_templates()[:5]
    
    print(f"\nAvailable Templates ({len(templates)} shown):")
    for t in templates:
        vars_preview = ', '.join(t.get('required_variables', [])[:3])
        print(f"  - {t['name']}")
        print(f"    Description: {t['description'][:50]}...")
        print(f"    Required: {vars_preview}")
    
    # Validate variables
    print("\nVariable Validation:")
    
    # Valid case
    valid, missing = gen.validate_template_variables(
        "product_description",
        {"product_name": "Test", "features": "F", "audience": "A"}
    )
    print(f"  Valid variables: {valid}, Missing: {missing}")
    
    # Invalid case
    valid, missing = gen.validate_template_variables(
        "product_description",
        {"product_name": "Test"}  # Missing required vars
    )
    print(f"  Invalid variables: {valid}, Missing: {missing}")
    
    # Cost estimation
    print("\nCost Estimation (before generation):")
    estimate = gen.estimate_cost(
        "product_description",
        {"product_name": "Smart Widget", "features": "AI-powered, Fast", "audience": "Developers"}
    )
    if estimate['success']:
        print(f"  Estimated prompt tokens: {estimate['estimated_prompt_tokens']}")
        print(f"  Estimated completion tokens: {estimate['estimated_completion_tokens']}")
        print(f"  Estimated total cost: ${estimate['estimated_cost']:.6f}")
        print(f"  Model: {estimate['model']}")
    else:
        print(f"  Estimation failed: {estimate.get('error')}")


def demo_custom_template(gen: ContentGenerator) -> None:
    """Demonstrate registering and using custom templates."""
    print_subheader("Custom Template")
    
    # Register a custom template
    gen.register_template(
        name="quick_summary",
        template="Summarize the following in one sentence: {text_to_summarize}",
        system_instructions="You are a concise summarizer.",
        required_variables=["text_to_summarize"]
    )
    
    print("\nRegistered custom template: 'quick_summary'")
    
    # Use the custom template
    result = gen.generate(
        "quick_summary",
        text_to_summarize="The AI Generator is a powerful tool that helps "
                         "produce various types of marketing material using templates."
    )
    
    print(f"\nGeneration Success: {result['success']}")
    if result['success']:
        print(f"Content: {result['content']}")


def demo_export(gen: ContentGenerator) -> None:
    """Demonstrate history export."""
    print_subheader("History Export")
    
    import tempfile
    import os
    
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    
    # Export to different formats
    formats = ['json', 'csv', 'txt']
    
    print("\nExporting history:")
    for fmt in formats:
        filepath = os.path.join(temp_dir, f"history.{fmt}")
        gen.export_history(filepath, format=fmt)
        size = os.path.getsize(filepath)
        print(f"  - {fmt.upper()}: {filepath}")
        print(f"    Size: {size} bytes")
    
    print(f"\nFiles saved to: {temp_dir}")


def demo_context_manager() -> None:
    """Demonstrate context manager usage."""
    print_subheader("Context Manager")
    
    print("\nUsing ContentGenerator as context manager:")
    
    with create_mock_generator() as gen:
        print(f"  Session started: {gen.session_id[:8]}...")
        
        # Generate some content
        gen.generate(
            "product_description",
            product_name="Context Manager Test",
            features="Auto cleanup",
            audience="Developers"
        )
        
        print(f"  Generated content, cache size: {len(gen._cache)}")
    
    # After exiting context
    print(f"  After exit, cache size: {len(gen._cache)}")
    print("  [History auto-saved on exit]")


def main() -> None:
    """Run the complete demonstration."""
    print_header("ContentGenerator - Complete Feature Demo")
    
    print("\nThis demo showcases all major features of the ContentGenerator.")
    print("Using MockOpenAIManager for demonstration (no API calls).")
    
    # Create generator with mock API
    gen = create_mock_generator(
        mock_response="This is a professionally crafted mock response "
                     "that demonstrates the content generation capabilities."
    )
    
    # Run demonstrations
    try:
        demo_basic_generation(gen)
        demo_cache_functionality(gen)
        demo_multiple_variations(gen)
        demo_batch_processing(gen)
        demo_callbacks(gen)
        demo_template_validation(gen)
        demo_custom_template(gen)
        demo_history_and_statistics(gen)
        demo_export(gen)
        demo_context_manager()
        
        print_header("Demo Complete!")
        
        # Final statistics
        final_stats = gen.get_statistics()
        print(f"\nFinal Session Summary:")
        print(f"  - Total Generations: {final_stats['total_generations']}")
        print(f"  - Success Rate: {final_stats['success_rate']:.1f}%")
        print(f"  - Cache Hit Rate: {final_stats['cache_hit_rate']:.1f}%")
        
        print("\n[All demonstrations completed successfully]")
        
    except Exception as e:
        print(f"\n[ERROR] Demo failed: {e}")
        raise


if __name__ == "__main__":
    main()
