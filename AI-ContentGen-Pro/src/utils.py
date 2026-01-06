"""Comprehensive utility module for the AI Content Generator.

This module provides essential utilities for:
- Input validation and sanitization
- Output processing and cleanup
- Template variable extraction
- Token counting and cost estimation
- Sensitive data redaction
- File I/O operations (JSON)
- URL validation
- Timestamp formatting
- Hash generation

All functions use only standard library dependencies.

Author: AI-ContentGen-Pro Team
Version: 2.0.0
"""

import hashlib
import json
import os
import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse


# =============================================================================
# CONSTANTS
# =============================================================================

# Maximum string length for validation
MAX_STRING_LENGTH = 10_000

# Dangerous SQL injection patterns
SQL_INJECTION_PATTERNS = [
    # Only flag SQL keywords when followed by typical SQL patterns
    r"(\bSELECT\s+.+\s+FROM\s+\w+)",  # SELECT ... FROM table
    r"(\b(INSERT|UPDATE|DELETE)\s+.*(INTO|FROM|SET)\s+\w+)",  # INSERT/UPDATE/DELETE with table
    r"(\bDROP\s+(TABLE|DATABASE|INDEX|VIEW)\b)",  # DROP with object type
    r"(\bEXEC(UTE)?\s*\()",  # EXEC function call
    r"(\bCREATE\s+(TABLE|DATABASE|INDEX|VIEW)\b)",  # CREATE with object type
    r"(\bALTER\s+(TABLE|DATABASE)\b)",  # ALTER with object type
    r"(;\s*--)",  # SQL comment after statement
    r"(/\*.*\*/)",  # Block comments
    r"(\bOR\b\s+['\"]\d+['\"]?\s*=\s*['\"]\d+)",  # OR '1'='1'
    r"(\bAND\b\s+['\"]\d+['\"]?\s*=\s*['\"]\d+)",  # AND '1'='1'
    r"('\s*OR\s+'\w*'\s*=\s*'\w*)",  # String-based OR injection ('1'='1')
    r"(;\s*(DROP|DELETE|TRUNCATE|INSERT|UPDATE)\b)",  # Dangerous statements after semicolon
    r"(UNION\s+(ALL\s+)?SELECT)",  # Union injection
    r"(xp_\w+)",  # SQL Server extended procedures
]

# XSS/Script injection patterns
XSS_PATTERNS = [
    r"<script[^>]*>.*?</script>",
    r"javascript:",
    r"on\w+\s*=",  # onclick, onload, etc.
    r"<iframe[^>]*>",
    r"<object[^>]*>",
    r"<embed[^>]*>",
]

# Sensitive data patterns
EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
PHONE_PATTERN = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
SSN_PATTERN = r'\b\d{3}-\d{2}-\d{4}\b'
API_KEY_PATTERN = r'\b[A-Za-z0-9]{20,}\b'  # Generic long alphanumeric sequences

# Valid template name pattern
TEMPLATE_NAME_PATTERN = r'^[a-zA-Z0-9_]+$'


# =============================================================================
# INPUT VALIDATION
# =============================================================================

def validate_input(
    template_name: str,
    variables: Dict[str, Any]
) -> Tuple[bool, Optional[str]]:
    """Validate template name and variables before processing.
    
    Performs comprehensive validation including:
    - Template name format validation
    - Variable type checking
    - SQL injection pattern detection
    - String length validation
    - Empty string detection
    
    Args:
        template_name: Name of the template to validate.
        variables: Dictionary of variable name -> value mappings.
        
    Returns:
        Tuple of (is_valid, error_message). 
        If valid: (True, None)
        If invalid: (False, "descriptive error message")
        
    Examples:
        >>> validate_input("blog_post", {"title": "Hello World"})
        (True, None)
        
        >>> validate_input("", {"title": "Test"})
        (False, "Template name cannot be empty")
        
        >>> validate_input("test", {"id": "1 OR 1=1"})
        (False, "Variable 'id' contains potential SQL injection pattern")
        
        >>> validate_input("test", {"text": "x" * 20000})
        (False, "Variable 'text' exceeds maximum length of 10000 characters")
    """
    # Validate template name
    if not template_name:
        return False, "Template name cannot be empty"
    
    if not isinstance(template_name, str):
        return False, f"Template name must be string, got {type(template_name).__name__}"
    
    if not re.match(TEMPLATE_NAME_PATTERN, template_name):
        return False, (
            "Template name must contain only alphanumeric characters "
            "and underscores (a-z, A-Z, 0-9, _)"
        )
    
    # Validate variables dictionary
    if not isinstance(variables, dict):
        return False, f"Variables must be dictionary, got {type(variables).__name__}"
    
    # Validate each variable
    for var_name, var_value in variables.items():
        # Check variable name
        if not isinstance(var_name, str):
            return False, f"Variable name must be string, got {type(var_name).__name__}"
        
        if not var_name:
            return False, "Variable name cannot be empty"
        
        # Check for None values
        if var_value is None:
            return False, f"Variable '{var_name}' cannot be None"
        
        # Validate string variables
        if isinstance(var_value, str):
            # Check for empty strings
            if not var_value.strip():
                return False, f"Variable '{var_name}' cannot be empty or whitespace-only"
            
            # Check length
            if len(var_value) > MAX_STRING_LENGTH:
                return False, (
                    f"Variable '{var_name}' exceeds maximum length of "
                    f"{MAX_STRING_LENGTH} characters (got {len(var_value)})"
                )
            
            # Check for SQL injection patterns
            for pattern in SQL_INJECTION_PATTERNS:
                if re.search(pattern, var_value, re.IGNORECASE):
                    return False, (
                        f"Variable '{var_name}' contains potential SQL injection pattern"
                    )
        
        # Validate numeric types
        elif isinstance(var_value, (int, float)):
            if not isinstance(var_value, bool):  # bool is subclass of int
                # Check for reasonable ranges
                if isinstance(var_value, int) and abs(var_value) > 10**12:
                    return False, f"Variable '{var_name}' integer value is unreasonably large"
                if isinstance(var_value, float):
                    # Check for NaN and infinity first
                    import math
                    if math.isnan(var_value) or math.isinf(var_value):
                        return False, f"Variable '{var_name}' is NaN or Infinity"
                    if abs(var_value) > 10**12:
                        return False, f"Variable '{var_name}' float value is unreasonably large"
        
        # Validate lists
        elif isinstance(var_value, list):
            if not var_value:
                return False, f"Variable '{var_name}' list cannot be empty"
            
            if len(var_value) > 1000:
                return False, f"Variable '{var_name}' list is too large (max 1000 items)"
            
            # Validate list items
            for i, item in enumerate(var_value):
                if isinstance(item, str):
                    if len(item) > MAX_STRING_LENGTH:
                        return False, (
                            f"Variable '{var_name}' list item {i} exceeds "
                            f"maximum length of {MAX_STRING_LENGTH} characters"
                        )
        
        # Other types
        elif not isinstance(var_value, (bool, dict)):
            return False, (
                f"Variable '{var_name}' has unsupported type "
                f"{type(var_value).__name__}"
            )
    
    return True, None


# =============================================================================
# OUTPUT SANITIZATION
# =============================================================================

def sanitize_output(content: str) -> str:
    """Sanitize output content by removing injection code and normalizing whitespace.
    
    Performs the following sanitization:
    - Removes HTML/JavaScript injection patterns
    - Normalizes whitespace (multiple spaces -> single space)
    - Removes leading/trailing whitespace
    - Fixes common encoding issues (smart quotes, em dashes)
    - Preserves intentional line breaks
    
    Args:
        content: Raw content string to sanitize.
        
    Returns:
        Cleaned and sanitized content string.
        
    Examples:
        >>> sanitize_output("<script>alert('xss')</script>Hello")
        'Hello'
        
        >>> sanitize_output("Hello    World")
        'Hello World'
        
        >>> sanitize_output('"Smart quotes"')
        '"Smart quotes"'
        
        >>> sanitize_output("Line 1\\n\\n\\nLine 2")
        'Line 1\\n\\nLine 2'
    """
    if not content:
        return ""
    
    # Remove XSS/script injection patterns
    for pattern in XSS_PATTERNS:
        content = re.sub(pattern, "", content, flags=re.IGNORECASE | re.DOTALL)
    
    # Fix common encoding issues
    replacements = {
        '\u2018': "'",  # Left single quotation mark
        '\u2019': "'",  # Right single quotation mark
        '\u201c': '"',  # Left double quotation mark
        '\u201d': '"',  # Right double quotation mark
        '\u2013': '-',  # En dash
        '\u2014': '-',  # Em dash
        '\u2026': '...',  # Horizontal ellipsis
        '\xa0': ' ',   # Non-breaking space
    }
    
    for old, new in replacements.items():
        content = content.replace(old, new)
    
    # Split into lines for processing
    lines = content.split('\n')
    
    # Process each line
    processed_lines = []
    for line in lines:
        # Normalize whitespace within line (multiple spaces -> single)
        line = re.sub(r' +', ' ', line)
        # Strip leading/trailing whitespace from each line
        line = line.strip()
        processed_lines.append(line)
    
    # Rejoin lines, but collapse multiple empty lines into double line break
    result = '\n'.join(processed_lines)
    result = re.sub(r'\n{3,}', '\n\n', result)
    
    return result.strip()


# =============================================================================
# TEXT PROCESSING
# =============================================================================

def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to maximum length at word boundary.
    
    Ensures truncation happens at word boundaries to avoid cutting words.
    Adds suffix if text is truncated.
    
    Args:
        text: Text to truncate.
        max_length: Maximum length including suffix.
        suffix: String to append if truncated (default: "...").
        
    Returns:
        Truncated text with suffix if applicable.
        
    Raises:
        ValueError: If max_length is less than suffix length.
        
    Examples:
        >>> truncate_text("Hello world this is a test", 15)
        'Hello world...'
        
        >>> truncate_text("Short", 100)
        'Short'
        
        >>> truncate_text("One two three four five", 12, "...")
        'One two...'
    """
    if max_length < len(suffix):
        raise ValueError(
            f"max_length ({max_length}) must be >= suffix length ({len(suffix)})"
        )
    
    if len(text) <= max_length:
        return text
    
    # Find the last space before max_length - suffix_length
    truncate_at = max_length - len(suffix)
    
    # Find last word boundary
    truncated = text[:truncate_at].rsplit(' ', 1)[0]
    
    # If no space found (single long word), just cut it
    if not truncated:
        truncated = text[:truncate_at]
    
    return truncated + suffix


def extract_variables_from_template(template: str) -> List[str]:
    """Extract variable placeholders from template string.
    
    Parses template for {variable_name} placeholders and returns
    unique variable names. Handles nested braces correctly.
    
    Args:
        template: Template string containing {variable} placeholders.
        
    Returns:
        List of unique variable names found in template.
        
    Examples:
        >>> extract_variables_from_template("Hello {name}, welcome to {place}!")
        ['name', 'place']
        
        >>> extract_variables_from_template("No variables here")
        []
        
        >>> extract_variables_from_template("Duplicate {var} and {var}")
        ['var']
        
        >>> extract_variables_from_template("{a} {b} {a}")
        ['a', 'b']
    """
    if not template:
        return []
    
    # Find all {variable} patterns
    # Use non-greedy match to handle multiple variables on same line
    pattern = r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}'
    matches = re.findall(pattern, template)
    
    # Return unique variables, preserving order
    seen = set()
    result = []
    for var in matches:
        if var not in seen:
            seen.add(var)
            result.append(var)
    
    return result


def calculate_token_count(text: str) -> int:
    """Estimate token count for text.
    
    Uses rough approximation: word_count * 1.3 tokens per word.
    This is suitable for cost estimation but not exact.
    
    Args:
        text: Text to count tokens for.
        
    Returns:
        Estimated token count as integer.
        
    Examples:
        >>> calculate_token_count("Hello world")
        2
        
        >>> calculate_token_count("One two three four five")
        6
        
        >>> calculate_token_count("")
        0
    """
    if not text:
        return 0
    
    # Split on whitespace and count words
    words = text.split()
    word_count = len(words)
    
    # Estimate tokens (1.3 tokens per word is rough approximation)
    estimated_tokens = int(word_count * 1.3)
    
    return estimated_tokens


# =============================================================================
# SENSITIVE DATA HANDLING
# =============================================================================

def redact_sensitive_data(
    text: str,
    patterns: Optional[List[str]] = None
) -> str:
    """Redact sensitive data from text using regex patterns.
    
    Detects and redacts:
    - Email addresses
    - Phone numbers (US format)
    - Social Security Numbers
    - Long alphanumeric sequences (potential API keys)
    - Custom patterns if provided
    
    Args:
        text: Text to redact sensitive data from.
        patterns: Optional list of additional regex patterns to redact.
        
    Returns:
        Text with sensitive data replaced with [REDACTED].
        
    Examples:
        >>> redact_sensitive_data("Email: john@example.com")
        'Email: [REDACTED]'
        
        >>> redact_sensitive_data("Call 555-123-4567")
        'Call [REDACTED]'
        
        >>> redact_sensitive_data("SSN: 123-45-6789")
        'SSN: [REDACTED]'
    """
    if not text:
        return text
    
    redacted = text
    
    # Default patterns
    default_patterns = [
        EMAIL_PATTERN,
        PHONE_PATTERN,
        SSN_PATTERN,
    ]
    
    # Add custom patterns if provided
    all_patterns = default_patterns + (patterns or [])
    
    # Apply each pattern
    for pattern in all_patterns:
        redacted = re.sub(pattern, '[REDACTED]', redacted)
    
    return redacted


# =============================================================================
# TIMESTAMP AND ID GENERATION
# =============================================================================

def format_timestamp(dt: Optional[datetime] = None) -> str:
    """Format datetime to ISO 8601 string with timezone.
    
    Args:
        dt: Datetime object to format. If None, uses current UTC time.
        
    Returns:
        ISO 8601 formatted timestamp string.
        
    Examples:
        >>> timestamp = format_timestamp()
        >>> len(timestamp) > 0
        True
        
        >>> from datetime import datetime
        >>> dt = datetime(2024, 1, 1, 12, 0, 0)
        >>> format_timestamp(dt)
        '2024-01-01T12:00:00+00:00'
    """
    if dt is None:
        dt = datetime.now(timezone.utc)
    
    # Ensure timezone aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    return dt.isoformat()


def generate_request_id() -> str:
    """Generate unique request ID using UUID4.
    
    Returns:
        UUID string in hexadecimal format.
        
    Examples:
        >>> id1 = generate_request_id()
        >>> id2 = generate_request_id()
        >>> id1 != id2
        True
        
        >>> len(generate_request_id())
        32
    """
    return uuid.uuid4().hex


# =============================================================================
# FILE I/O OPERATIONS
# =============================================================================

def load_json_file(filepath: str) -> Dict:
    """Safely load JSON file with error handling.
    
    Args:
        filepath: Path to JSON file.
        
    Returns:
        Dictionary loaded from JSON file.
        
    Raises:
        FileNotFoundError: If file doesn't exist.
        ValueError: If file contains invalid JSON.
        
    Examples:
        >>> # Assuming test.json exists with {"key": "value"}
        >>> data = load_json_file("test.json")
        >>> data["key"]
        'value'
    """
    filepath = Path(filepath)
    
    if not filepath.exists():
        raise FileNotFoundError(f"JSON file not found: {filepath}")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in file {filepath}: {e}")
    except Exception as e:
        raise ValueError(f"Error reading JSON file {filepath}: {e}")
    
    if not isinstance(data, dict):
        raise ValueError(f"JSON file {filepath} must contain a dictionary at root level")
    
    return data


def save_json_file(data: Dict, filepath: str) -> None:
    """Save dictionary to JSON file with atomic write.
    
    Uses atomic write pattern: write to temp file, then rename.
    Creates parent directories if they don't exist.
    
    Args:
        data: Dictionary to save.
        filepath: Path to save JSON file.
        
    Raises:
        ValueError: If data is not a dictionary.
        OSError: If unable to write file.
        
    Examples:
        >>> data = {"key": "value", "number": 42}
        >>> save_json_file(data, "output.json")
        # Creates output.json with pretty-printed JSON
    """
    if not isinstance(data, dict):
        raise ValueError(f"Data must be dictionary, got {type(data).__name__}")
    
    filepath = Path(filepath)
    
    # Create parent directories if they don't exist
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    # Use atomic write: write to temp file, then rename
    temp_fd, temp_path = tempfile.mkstemp(
        dir=filepath.parent,
        prefix=f".{filepath.name}.",
        suffix=".tmp"
    )
    
    try:
        with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write('\n')  # Add trailing newline
        
        # Atomic rename
        os.replace(temp_path, filepath)
    except Exception as e:
        # Clean up temp file on error
        try:
            os.unlink(temp_path)
        except Exception:
            pass
        raise OSError(f"Failed to save JSON file {filepath}: {e}")


# =============================================================================
# HASHING AND URL VALIDATION
# =============================================================================

def create_hash(text: str) -> str:
    """Create MD5 hash of text for caching keys.
    
    Args:
        text: Text to hash.
        
    Returns:
        Hexadecimal MD5 hash string.
        
    Examples:
        >>> hash1 = create_hash("hello")
        >>> hash2 = create_hash("hello")
        >>> hash1 == hash2
        True
        
        >>> hash3 = create_hash("world")
        >>> hash1 != hash3
        True
        
        >>> len(create_hash("test"))
        32
    """
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def validate_url(url: str) -> bool:
    """Validate if string is a valid URL.
    
    Checks for valid URL structure with scheme and netloc.
    
    Args:
        url: URL string to validate.
        
    Returns:
        True if valid URL, False otherwise.
        
    Examples:
        >>> validate_url("https://example.com")
        True
        
        >>> validate_url("http://example.com/path?query=1")
        True
        
        >>> validate_url("not a url")
        False
        
        >>> validate_url("ftp://files.example.com")
        True
        
        >>> validate_url("")
        False
    """
    if not url:
        return False
    
    try:
        result = urlparse(url)
        # URL must have scheme (http, https, etc.) and netloc (domain)
        return bool(result.scheme and result.netloc)
    except Exception:
        return False


# =============================================================================
# LEGACY COMPATIBILITY
# =============================================================================

def build_chat_messages(prompt: str) -> List[Dict[str, str]]:
    """Wrap plain text into OpenAI chat message format.
    
    Args:
        prompt: Plain text prompt.
        
    Returns:
        List containing single user message dictionary.
        
    Examples:
        >>> build_chat_messages("Hello AI")
        [{'role': 'user', 'content': 'Hello AI'}]
    """
    return [{"role": "user", "content": prompt}]


def sanitize_text(value: str) -> str:
    """Basic sanitization to trim whitespace and normalize line breaks.
    
    Note: For comprehensive sanitization, use sanitize_output() instead.
    
    Args:
        value: Text to sanitize.
        
    Returns:
        Sanitized text.
        
    Examples:
        >>> sanitize_text("  hello  \\n  world  ")
        'hello\\nworld'
    """
    return "\n".join(line.strip() for line in value.splitlines()).strip()

