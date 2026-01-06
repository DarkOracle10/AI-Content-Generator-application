#!/usr/bin/env python3
"""Demo script showcasing the production-ready configuration system."""

import sys
import os

# Add src to path for demo purposes
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from config import (
    ConfigurationManager,
    ConfigurationError,
    load_config,
    MODEL_COSTS,
)


def main():
    """Demonstrate configuration features."""
    print("=" * 60)
    print("AI-ContentGen-Pro Configuration System Demo")
    print("=" * 60)
    print()

    try:
        # Load configuration
        print("1. Loading configuration...")
        config = load_config()
        print("✓ Configuration loaded successfully")
        print()

        # Display configuration (API key masked)
        print("2. Current configuration:")
        print(config.display())
        print()

        # Show cost estimation
        print("3. Cost estimation example:")
        print(f"   Model: {config.openai_model}")
        if config.openai_model in MODEL_COSTS:
            cost = config.estimate_cost(input_tokens=1000, output_tokens=500)
            print(f"   Input: 1000 tokens, Output: 500 tokens")
            print(f"   Estimated cost: ${cost:.6f} USD")
        else:
            print(f"   Cost data not available for {config.openai_model}")
        print()

        # Show available models and pricing
        print("4. Available model pricing (per 1K tokens):")
        for model, costs in MODEL_COSTS.items():
            print(f"   {model:20s} - Input: ${costs['input']:.4f}, Output: ${costs['output']:.4f}")
        print()

        # Export to dictionary
        print("5. Configuration as dictionary (secrets masked):")
        config_dict = config.to_dict(include_secrets=False)
        for key, value in config_dict.items():
            print(f"   {key:20s}: {value}")
        print()

        # Singleton pattern demonstration
        print("6. Singleton pattern verification:")
        config2 = ConfigurationManager.get_config()
        print(f"   Same instance: {config is config2}")
        print()

        # Environment detection
        print("7. Environment detection:")
        print(f"   Current environment: {config.environment.value}")
        print()

        print("=" * 60)
        print("Demo completed successfully!")
        print("=" * 60)

    except ConfigurationError as e:
        print(f"\n❌ Configuration Error: {e}")
        print("\nPlease ensure:")
        print("  1. Copy .env.example to .env")
        print("  2. Set OPENAI_API_KEY in .env file")
        print("  3. Verify all configuration values are valid")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
