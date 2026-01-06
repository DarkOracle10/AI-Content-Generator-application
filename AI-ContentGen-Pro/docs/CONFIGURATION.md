# Configuration System Documentation

## Overview

The AI-ContentGen-Pro configuration system provides production-ready configuration management with:

- ✅ Environment variable validation
- ✅ Multiple environment support (development, production, testing)
- ✅ Type safety with full type hints
- ✅ Singleton pattern for consistent configuration
- ✅ Cost estimation for OpenAI API usage
- ✅ Comprehensive error handling
- ✅ Configuration reload capability
- ✅ Secure API key handling

## Quick Start

### 1. Setup Environment

Copy the example environment file and configure your settings:

```bash
cp .env.example .env
```

Edit `.env` and set your OpenAI API key:

```bash
OPENAI_API_KEY=sk-your-actual-api-key-here
```

### 2. Basic Usage

```python
from src.config import load_config

# Load configuration (validates automatically)
config = load_config()

# Access configuration values
print(config.openai_model)    # "gpt-3.5-turbo"
print(config.max_tokens)       # 2000
print(config.temperature)      # 0.7
```

## Configuration Variables

### Required Variables

| Variable | Type | Description |
|----------|------|-------------|
| `OPENAI_API_KEY` | string | Your OpenAI API key (must start with 'sk-') |

### Optional Variables with Defaults

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `OPENAI_MODEL` | string | `gpt-3.5-turbo` | OpenAI model to use |
| `MAX_TOKENS` | int | `2000` | Maximum tokens per request |
| `TEMPERATURE` | float | `0.7` | Sampling temperature (0.0-2.0) |
| `LOG_LEVEL` | string | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `CACHE_ENABLED` | bool | `true` | Enable response caching |
| `CACHE_SIZE` | int | `100` | Maximum cached responses |
| `APP_ENV` | string | `development` | Environment mode (development, production, testing) |

## Core Constants

### API Configuration

```python
from src.config import API_TIMEOUT, RETRY_ATTEMPTS, RETRY_DELAY

API_TIMEOUT = 30      # seconds
RETRY_ATTEMPTS = 3    # number of retries
RETRY_DELAY = 2       # seconds between retries
```

### Model Pricing

```python
from src.config import MODEL_COSTS

# Cost per 1K tokens in USD
MODEL_COSTS = {
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "gpt-3.5-turbo-16k": {"input": 0.003, "output": 0.004},
}
```

## Advanced Features

### Cost Estimation

Calculate the cost of API calls before making them:

```python
config = load_config()

# Estimate cost for 1000 input tokens, 500 output tokens
cost = config.estimate_cost(input_tokens=1000, output_tokens=500)
print(f"Estimated cost: ${cost:.6f}")
```

### Configuration Display

View current configuration with masked secrets:

```python
config = load_config()
print(config.display())

# Output:
# === AI-ContentGen-Pro Configuration ===
# openai_api_key      : sk-test...cdef
# openai_model        : gpt-3.5-turbo
# max_tokens          : 2000
# temperature         : 0.7
# ...
```

### Export to Dictionary

```python
# Export with masked API key
config_dict = config.to_dict(include_secrets=False)

# Export with full API key (use carefully!)
config_dict = config.to_dict(include_secrets=True)
```

### Singleton Pattern

The configuration uses a singleton pattern to ensure consistency:

```python
from src.config import ConfigurationManager

# All calls return the same instance
config1 = ConfigurationManager.get_config()
config2 = ConfigurationManager.get_config()
assert config1 is config2  # True

# Force reload from environment
config3 = ConfigurationManager.get_config(force_reload=True)
```

### Runtime Reload

Reload configuration from environment variables without restarting:

```python
config = load_config()
print(config.max_tokens)  # 2000

# Update environment variable
os.environ['MAX_TOKENS'] = '3000'

# Reload configuration
config.reload()
print(config.max_tokens)  # 3000
```

## Error Handling

The configuration system provides clear error messages:

```python
from src.config import ConfigurationError

try:
    config = load_config()
except ConfigurationError as e:
    print(f"Configuration error: {e}")
    # Handle missing or invalid configuration
```

### Common Errors

1. **Missing API Key**
   ```
   ConfigurationError: OPENAI_API_KEY is required but not set.
   Please set it in your .env file or environment variables.
   ```

2. **Invalid Temperature**
   ```
   ConfigurationError: TEMPERATURE must be between 0.0 and 2.0, got 3.5
   ```

3. **Invalid Log Level**
   ```
   ConfigurationError: LOG_LEVEL must be one of ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], got 'TRACE'
   ```

## Environment-Specific Configuration

### Development

```bash
APP_ENV=development
LOG_LEVEL=DEBUG
CACHE_ENABLED=true
```

### Production

```bash
APP_ENV=production
LOG_LEVEL=WARNING
CACHE_ENABLED=true
CACHE_SIZE=500
```

### Testing

```bash
APP_ENV=testing
LOG_LEVEL=ERROR
CACHE_ENABLED=false
```

## Validation Rules

The configuration system enforces the following validations:

1. **API Key**: Must be non-empty and preferably start with 'sk-'
2. **Model**: Warning logged if model not in known pricing table
3. **Max Tokens**: Must be at least 1 (warning if > 128000)
4. **Temperature**: Must be between 0.0 and 2.0
5. **Log Level**: Must be valid Python logging level
6. **Cache Size**: Must be non-negative

## Best Practices

### 1. Never Commit `.env` Files

Add to `.gitignore`:
```
.env
.env.local
.env.production
```

### 2. Use Environment-Specific Files

```bash
.env.development
.env.production
.env.testing
```

### 3. Validate Early

Load configuration at application startup to fail fast:

```python
def main():
    try:
        config = load_config()
    except ConfigurationError as e:
        print(f"Failed to start: {e}")
        sys.exit(1)
    
    # Continue with application logic
```

### 4. Monitor Costs

Use cost estimation for budget control:

```python
config = load_config()
estimated_cost = config.estimate_cost(1000, 500)

if estimated_cost and estimated_cost > budget_threshold:
    logging.warning(f"High API cost detected: ${estimated_cost}")
```

### 5. Secure Logging

Never log full API keys:

```python
# Good - uses masked display
logging.info(f"Config: {config.display()}")

# Bad - exposes full API key
logging.info(f"Key: {config.openai_api_key}")
```

## Testing

### Unit Tests

The configuration module includes comprehensive tests:

```bash
pytest tests/test_config.py -v
```

### Mock Configuration for Tests

```python
import pytest
from src.config import ConfigurationManager

@pytest.fixture
def test_config(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    monkeypatch.setenv("APP_ENV", "testing")
    ConfigurationManager.reset()
    return ConfigurationManager.get_config()
```

## Troubleshooting

### Issue: Configuration not loading

**Solution**: Ensure `.env` file exists in project root:
```bash
ls -la .env
```

### Issue: API key validation fails

**Solution**: Verify key format:
```bash
echo $OPENAI_API_KEY
# Should start with: sk-
```

### Issue: Integer/float parsing errors

**Solution**: Check value format in `.env`:
```bash
# Wrong
MAX_TOKENS=2,000

# Correct
MAX_TOKENS=2000
```

### Issue: Boolean not working

**Solution**: Use valid boolean strings:
```bash
# Valid: true, 1, yes, on
# Invalid: True (works), TRUE (works), t, y
CACHE_ENABLED=true
```

## API Reference

See [API_GUIDE.md](./API_GUIDE.md) for complete API reference.

## Examples

See example scripts in `examples/demo_scripts/`:
- `config_demo.py` - Complete configuration demonstration

## Contributing

When modifying the configuration system:

1. Update this documentation
2. Add tests for new features
3. Update `.env.example` with new variables
4. Maintain backward compatibility
5. Follow PEP 8 style guidelines

## License

MIT License - See [LICENSE](../LICENSE) for details.
