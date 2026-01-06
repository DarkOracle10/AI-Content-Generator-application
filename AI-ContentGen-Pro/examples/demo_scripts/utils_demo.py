#!/usr/bin/env python3
"""Demo script showcasing the comprehensive utility module.

This script demonstrates all utility functions:
1. Input validation
2. Output sanitization
3. Text processing
4. Sensitive data redaction
5. Timestamp and ID generation
6. File I/O operations
7. Hashing and URL validation

Run with: python examples/demo_scripts/utils_demo.py

Author: AI-ContentGen-Pro Team
"""

import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.utils import (
    validate_input,
    sanitize_output,
    truncate_text,
    extract_variables_from_template,
    calculate_token_count,
    redact_sensitive_data,
    format_timestamp,
    generate_request_id,
    load_json_file,
    save_json_file,
    create_hash,
    validate_url,
)


def print_header(title: str) -> None:
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def demo_input_validation() -> None:
    """Demonstrate input validation."""
    print_header("DEMO: Input Validation")
    
    # Valid input
    print("\n[*] Test 1: Valid input")
    is_valid, error = validate_input(
        "blog_post",
        {"title": "Hello World", "author": "John Doe", "word_count": 500}
    )
    print(f"  Result: {'✓ PASS' if is_valid else 'X FAIL'}")
    if error:
        print(f"  Error: {error}")
    
    # Empty template name
    print("\n[*] Test 2: Empty template name")
    is_valid, error = validate_input("", {"title": "Test"})
    print(f"  Result: {'✓ PASS' if is_valid else 'X FAIL (expected)'}")
    if error:
        print(f"  Error: {error}")
    
    # SQL injection attempt
    print("\n[*] Test 3: SQL injection detection")
    is_valid, error = validate_input(
        "user_profile",
        {"username": "admin'; DROP TABLE users--"}
    )
    print(f"  Result: {'✓ PASS' if is_valid else 'X FAIL (expected)'}")
    if error:
        print(f"  Error: {error}")
    
    # String too long
    print("\n[*] Test 4: String length validation")
    is_valid, error = validate_input(
        "document",
        {"content": "x" * 15000}
    )
    print(f"  Result: {'✓ PASS' if is_valid else 'X FAIL (expected)'}")
    if error:
        print(f"  Error: {error}")
    
    # Valid list input
    print("\n[*] Test 5: List variable validation")
    is_valid, error = validate_input(
        "email_campaign",
        {"recipients": ["user1@example.com", "user2@example.com"], "active": True}
    )
    print(f"  Result: {'✓ PASS' if is_valid else 'X FAIL'}")


def demo_output_sanitization() -> None:
    """Demonstrate output sanitization."""
    print_header("DEMO: Output Sanitization")
    
    # Remove XSS attempts
    print("\n[*] Test 1: Remove script tags")
    dirty = "<script>alert('XSS')</script><p>Clean content</p>"
    clean = sanitize_output(dirty)
    print(f"  Input:  {repr(dirty)}")
    print(f"  Output: {repr(clean)}")
    
    # Normalize whitespace
    print("\n[*] Test 2: Normalize whitespace")
    dirty = "Hello    World    with   many  spaces"
    clean = sanitize_output(dirty)
    print(f"  Input:  '{dirty}'")
    print(f"  Output: '{clean}'")
    
    # Fix smart quotes
    print("\n[*] Test 3: Fix encoding issues (smart quotes)")
    dirty = "\u201cSmart quotes\u201d and \u2018apostrophes\u2019"
    clean = sanitize_output(dirty)
    print(f"  Input:  {repr(dirty)}")
    print(f"  Output: {repr(clean)}")
    
    # Collapse multiple newlines
    print("\n[*] Test 4: Collapse excessive newlines")
    dirty = "Line 1\n\n\n\n\nLine 2"
    clean = sanitize_output(dirty)
    print(f"  Input:  {repr(dirty)}")
    print(f"  Output: {repr(clean)}")


def demo_text_processing() -> None:
    """Demonstrate text processing functions."""
    print_header("DEMO: Text Processing")
    
    # Truncate text
    print("\n[*] Test 1: Truncate text at word boundary")
    text = "The quick brown fox jumps over the lazy dog"
    truncated = truncate_text(text, 25)
    print(f"  Original: '{text}'")
    print(f"  Truncated (25 chars): '{truncated}'")
    
    # Extract template variables
    print("\n[*] Test 2: Extract template variables")
    template = "Hello {name}, your order #{order_id} will arrive on {delivery_date}."
    variables = extract_variables_from_template(template)
    print(f"  Template: '{template}'")
    print(f"  Variables: {variables}")
    
    # Calculate token count
    print("\n[*] Test 3: Estimate token count")
    texts = [
        "Hello world",
        "The quick brown fox jumps over the lazy dog",
        "AI and machine learning are transforming technology"
    ]
    for text in texts:
        tokens = calculate_token_count(text)
        print(f"  '{text}' -> {tokens} tokens")


def demo_sensitive_data_redaction() -> None:
    """Demonstrate sensitive data redaction."""
    print_header("DEMO: Sensitive Data Redaction")
    
    sensitive_texts = [
        "My email is john.doe@example.com",
        "Call me at 555-123-4567",
        "SSN: 123-45-6789",
        "Contact alice@company.com or bob@startup.io for details",
    ]
    
    for i, text in enumerate(sensitive_texts, 1):
        print(f"\n[*] Test {i}:")
        redacted = redact_sensitive_data(text)
        print(f"  Original: {text}")
        print(f"  Redacted: {redacted}")


def demo_timestamp_and_ids() -> None:
    """Demonstrate timestamp and ID generation."""
    print_header("DEMO: Timestamp and ID Generation")
    
    # Current timestamp
    print("\n[*] Test 1: Format current timestamp")
    timestamp = format_timestamp()
    print(f"  Current timestamp (ISO 8601): {timestamp}")
    
    # Specific timestamp
    print("\n[*] Test 2: Format specific datetime")
    dt = datetime(2024, 1, 15, 14, 30, 0, tzinfo=timezone.utc)
    timestamp = format_timestamp(dt)
    print(f"  Formatted: {timestamp}")
    
    # Generate request IDs
    print("\n[*] Test 3: Generate unique request IDs")
    ids = [generate_request_id() for _ in range(3)]
    for i, request_id in enumerate(ids, 1):
        print(f"  Request ID {i}: {request_id}")
    print(f"  All unique: {len(ids) == len(set(ids))}")


def demo_file_operations() -> None:
    """Demonstrate file I/O operations."""
    print_header("DEMO: File I/O Operations")
    
    # Create temporary directory for demo
    with tempfile.TemporaryDirectory() as tmpdir:
        json_file = Path(tmpdir) / "demo_data.json"
        
        # Save JSON
        print("\n[*] Test 1: Save JSON file")
        data = {
            "name": "AI Content Generator",
            "version": "2.0.0",
            "features": ["validation", "sanitization", "templates"],
            "config": {
                "max_tokens": 2000,
                "temperature": 0.7
            }
        }
        save_json_file(data, str(json_file))
        print(f"  Saved to: {json_file}")
        print(f"  File exists: {json_file.exists()}")
        
        # Load JSON
        print("\n[*] Test 2: Load JSON file")
        loaded = load_json_file(str(json_file))
        print(f"  Loaded data:")
        print(f"    Name: {loaded['name']}")
        print(f"    Version: {loaded['version']}")
        print(f"    Features: {len(loaded['features'])} items")
        
        # Verify atomic write
        print("\n[*] Test 3: Atomic write (overwrite)")
        updated_data = data.copy()
        updated_data["version"] = "2.1.0"
        save_json_file(updated_data, str(json_file))
        reloaded = load_json_file(str(json_file))
        print(f"  Original version: {data['version']}")
        print(f"  Updated version: {reloaded['version']}")


def demo_hashing_and_url() -> None:
    """Demonstrate hashing and URL validation."""
    print_header("DEMO: Hashing and URL Validation")
    
    # Create hashes
    print("\n[*] Test 1: Create MD5 hashes for caching")
    texts = [
        "cache_key_1",
        "cache_key_1",  # Duplicate
        "cache_key_2",
    ]
    for text in texts:
        hash_value = create_hash(text)
        print(f"  '{text}' -> {hash_value}")
    
    # Validate URLs
    print("\n[*] Test 2: URL validation")
    test_urls = [
        ("https://example.com", True),
        ("http://api.example.com/v1/users", True),
        ("ftp://files.server.com", True),
        ("not a url", False),
        ("example.com", False),  # Missing scheme
        ("", False),
    ]
    
    for url, expected in test_urls:
        is_valid = validate_url(url)
        status = "✓" if is_valid == expected else "X"
        print(f"  {status} '{url}' -> {is_valid}")


def demo_real_world_example() -> None:
    """Demonstrate a real-world usage example."""
    print_header("DEMO: Real-World Example - Process User Input")
    
    print("\n[*] Scenario: Processing user-submitted blog post template")
    
    # User input (potentially unsafe)
    template_name = "blog_post_seo"
    user_variables = {
        "title": "10 Tips for Better <script>alert('xss')</script> SEO",
        "author": "John Doe (john.doe@example.com)",
        "keywords": ["SEO", "Marketing", "Content"],
        "publish": True
    }
    
    print(f"\n  Step 1: Validate input")
    is_valid, error = validate_input(template_name, user_variables)
    if not is_valid:
        print(f"    [X] Validation failed: {error}")
        return
    print(f"    [✓] Input is valid")
    
    print(f"\n  Step 2: Sanitize output")
    title = user_variables["title"]
    sanitized_title = sanitize_output(title)
    print(f"    Original: {repr(title)}")
    print(f"    Sanitized: {repr(sanitized_title)}")
    
    print(f"\n  Step 3: Redact sensitive data from author field")
    author = user_variables["author"]
    redacted_author = redact_sensitive_data(author)
    print(f"    Original: {author}")
    print(f"    Redacted: {redacted_author}")
    
    print(f"\n  Step 4: Estimate tokens for cost calculation")
    content = f"{sanitized_title}. Article by {redacted_author}. Keywords: {', '.join(user_variables['keywords'])}"
    tokens = calculate_token_count(content)
    print(f"    Content: '{content}'")
    print(f"    Estimated tokens: {tokens}")
    
    print(f"\n  Step 5: Generate unique request ID for tracking")
    request_id = generate_request_id()
    print(f"    Request ID: {request_id}")
    
    print(f"\n  Step 6: Create cache key")
    cache_key = create_hash(template_name + str(user_variables))
    print(f"    Cache key: {cache_key}")
    
    print(f"\n  [✓] Processing complete - safe to proceed to content generation")


def main():
    """Run all demos."""
    print("\n" + "#" * 70)
    print("#  Comprehensive Utility Module - Feature Demo")
    print("#" * 70)
    print(f"\n  Demo started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        demo_input_validation()
        demo_output_sanitization()
        demo_text_processing()
        demo_sensitive_data_redaction()
        demo_timestamp_and_ids()
        demo_file_operations()
        demo_hashing_and_url()
        demo_real_world_example()
        
        print_header("DEMO COMPLETE")
        print("\n  All demos completed successfully!")
        print("\n  Key Features Demonstrated:")
        print("  - Input validation (SQL injection protection, type checking)")
        print("  - Output sanitization (XSS removal, whitespace normalization)")
        print("  - Text processing (truncation, template parsing, token counting)")
        print("  - Sensitive data redaction (emails, phones, SSN)")
        print("  - Timestamp formatting (ISO 8601)")
        print("  - Unique ID generation (UUID)")
        print("  - Safe file I/O (atomic writes, error handling)")
        print("  - Hash generation (MD5 for caching)")
        print("  - URL validation")
        
    except Exception as e:
        print(f"\n[ERROR] Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
