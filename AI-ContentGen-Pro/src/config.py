"""Production-ready configuration management for AI-ContentGen-Pro.

This module handles all application configuration including:
- Environment variable loading and validation
- Multiple environment modes (development, production, testing)
- API cost estimation constants
- Singleton configuration instance
- Logging setup
"""

import logging
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Environment(Enum):
    """Application environment modes."""

    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing required values."""

    pass


# API Constants
API_TIMEOUT: int = 30  # seconds
RETRY_ATTEMPTS: int = 3
RETRY_DELAY: int = 2  # seconds

# Cost per 1K tokens (in USD) - Input/Output pricing
MODEL_COSTS: Dict[str, Dict[str, float]] = {
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "gpt-3.5-turbo-16k": {"input": 0.003, "output": 0.004},
}

# Valid log levels
VALID_LOG_LEVELS: list[str] = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


@dataclass
class AppConfig:
    """Application configuration container with validation.

    Attributes:
        openai_api_key: OpenAI API key (required)
        openai_model: Model name for content generation
        max_tokens: Maximum tokens per API request
        temperature: Sampling temperature (0.0-1.0)
        log_level: Logging level
        cache_enabled: Whether to enable response caching
        cache_size: Maximum number of cached responses
        environment: Current environment mode
    """

    # Required fields
    openai_api_key: str

    # Optional fields with defaults
    openai_model: str = "gpt-3.5-turbo"
    max_tokens: int = 2000
    temperature: float = 0.7
    log_level: str = "INFO"
    cache_enabled: bool = True
    cache_size: int = 100
    environment: Environment = field(default=Environment.DEVELOPMENT)

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        self._validate_all()
        self._setup_logging()

    def _validate_all(self) -> None:
        """Run all validation checks on configuration values."""
        self._validate_api_key()
        self._validate_model()
        self._validate_max_tokens()
        self._validate_temperature()
        self._validate_log_level()
        self._validate_cache_size()

    def _validate_api_key(self) -> None:
        """Ensure API key is present and non-empty."""
        if not self.openai_api_key or not self.openai_api_key.strip():
            raise ConfigurationError(
                "OPENAI_API_KEY is required but not set. "
                "Please set it in your .env file or environment variables."
            )

        # Basic format validation (OpenAI keys start with 'sk-')
        if not self.openai_api_key.startswith("sk-"):
            logging.warning(
                "API key does not start with 'sk-'. "
                "This may indicate an invalid key format."
            )

    def _validate_model(self) -> None:
        """Validate model name is recognized."""
        if self.openai_model not in MODEL_COSTS:
            logging.warning(
                f"Model '{self.openai_model}' not in known models. "
                f"Cost estimation may be unavailable. "
                f"Known models: {list(MODEL_COSTS.keys())}"
            )

    def _validate_max_tokens(self) -> None:
        """Ensure max_tokens is within reasonable bounds."""
        if self.max_tokens < 1:
            raise ConfigurationError(
                f"MAX_TOKENS must be at least 1, got {self.max_tokens}"
            )
        if self.max_tokens > 128000:
            logging.warning(
                f"MAX_TOKENS is very high ({self.max_tokens}). "
                "This may result in expensive API calls."
            )

    def _validate_temperature(self) -> None:
        """Ensure temperature is within valid range."""
        if not 0.0 <= self.temperature <= 2.0:
            raise ConfigurationError(
                f"TEMPERATURE must be between 0.0 and 2.0, got {self.temperature}"
            )

    def _validate_log_level(self) -> None:
        """Validate log level is recognized."""
        if self.log_level.upper() not in VALID_LOG_LEVELS:
            raise ConfigurationError(
                f"LOG_LEVEL must be one of {VALID_LOG_LEVELS}, "
                f"got '{self.log_level}'"
            )
        # Normalize to uppercase
        self.log_level = self.log_level.upper()

    def _validate_cache_size(self) -> None:
        """Ensure cache size is reasonable."""
        if self.cache_size < 0:
            raise ConfigurationError(
                f"CACHE_SIZE must be non-negative, got {self.cache_size}"
            )

    def _setup_logging(self) -> None:
        """Configure logging based on configuration."""
        numeric_level = getattr(logging, self.log_level)
        logging.basicConfig(
            level=numeric_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        logging.info(f"Logging initialized at {self.log_level} level")

    def estimate_cost(
        self, input_tokens: int, output_tokens: int
    ) -> Optional[float]:
        """Estimate API call cost based on token usage.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD, or None if model pricing unavailable
        """
        if self.openai_model not in MODEL_COSTS:
            return None

        costs = MODEL_COSTS[self.openai_model]
        input_cost = (input_tokens / 1000) * costs["input"]
        output_cost = (output_tokens / 1000) * costs["output"]

        return round(input_cost + output_cost, 6)

    def to_dict(self, include_secrets: bool = False) -> Dict[str, Any]:
        """Export configuration as dictionary.

        Args:
            include_secrets: Whether to include sensitive values (API key)

        Returns:
            Dictionary representation of configuration
        """
        config_dict = {
            "openai_model": self.openai_model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "log_level": self.log_level,
            "cache_enabled": self.cache_enabled,
            "cache_size": self.cache_size,
            "environment": self.environment.value,
        }

        if include_secrets:
            config_dict["openai_api_key"] = self.openai_api_key
        else:
            # Show only first and last 4 characters
            key = self.openai_api_key
            config_dict["openai_api_key"] = f"{key[:7]}...{key[-4:]}"

        return config_dict

    def display(self) -> str:
        """Generate human-readable configuration display.

        Returns:
            Formatted configuration string (API key masked)
        """
        config = self.to_dict(include_secrets=False)
        lines = ["=== AI-ContentGen-Pro Configuration ==="]
        for key, value in config.items():
            lines.append(f"{key:20s}: {value}")
        lines.append("=" * 40)
        return "\n".join(lines)

    def reload(self) -> None:
        """Reload configuration from environment variables.

        Note: This modifies the instance in-place.
        """
        logging.info("Reloading configuration from environment")
        load_dotenv(override=True)

        # Re-read values
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        self.max_tokens = int(os.getenv("MAX_TOKENS", "2000"))
        self.temperature = float(os.getenv("TEMPERATURE", "0.7"))
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.cache_enabled = os.getenv("CACHE_ENABLED", "true").lower() in (
            "true",
            "1",
            "yes",
        )
        self.cache_size = int(os.getenv("CACHE_SIZE", "100"))

        # Re-validate
        self._validate_all()
        logging.info("Configuration reloaded successfully")


class ConfigurationManager:
    """Singleton configuration manager.

    Ensures only one configuration instance exists throughout the application.
    """

    _instance: Optional[AppConfig] = None
    _initialized: bool = False

    @classmethod
    def get_config(cls, force_reload: bool = False) -> AppConfig:
        """Get or create the singleton configuration instance.

        Args:
            force_reload: Force recreation of configuration instance

        Returns:
            Application configuration instance
        """
        if cls._instance is None or force_reload:
            cls._instance = cls._load_config()
            cls._initialized = True
            logging.info("Configuration instance created")
        return cls._instance

    @classmethod
    def _load_config(cls) -> AppConfig:
        """Load configuration from environment variables.

        Returns:
            Configured AppConfig instance

        Raises:
            ConfigurationError: If required configuration is missing or invalid
        """
        # Detect environment
        env_str = os.getenv("APP_ENV", "development").lower()
        try:
            environment = Environment(env_str)
        except ValueError:
            logging.warning(
                f"Unknown environment '{env_str}', defaulting to development"
            )
            environment = Environment.DEVELOPMENT

        # Parse boolean for cache enabled
        cache_enabled_str = os.getenv("CACHE_ENABLED", "true").lower()
        cache_enabled = cache_enabled_str in ("true", "1", "yes", "on")

        try:
            config = AppConfig(
                openai_api_key=os.getenv("OPENAI_API_KEY", ""),
                openai_model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
                max_tokens=int(os.getenv("MAX_TOKENS", "2000")),
                temperature=float(os.getenv("TEMPERATURE", "0.7")),
                log_level=os.getenv("LOG_LEVEL", "INFO"),
                cache_enabled=cache_enabled,
                cache_size=int(os.getenv("CACHE_SIZE", "100")),
                environment=environment,
            )
            return config
        except ValueError as e:
            raise ConfigurationError(
                f"Error parsing configuration values: {e}"
            ) from e

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance (mainly for testing)."""
        cls._instance = None
        cls._initialized = False
        logging.info("Configuration manager reset")


# Convenience function for backward compatibility
def load_config() -> AppConfig:
    """Load and return the application configuration.

    This is the main entry point for accessing configuration.

    Returns:
        Application configuration instance

    Raises:
        ConfigurationError: If configuration is invalid
    """
    return ConfigurationManager.get_config()


# Module-level convenience for direct import
config: AppConfig = ConfigurationManager.get_config()
