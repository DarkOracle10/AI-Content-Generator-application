# 🚀 AI-ContentGen-Pro

<div align="center">

![AI Content Generator](https://img.shields.io/badge/AI-Content%20Generator-6366f1?style=for-the-badge&logo=openai&logoColor=white)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org)
[![Flask](https://img.shields.io/badge/Flask-2.3+-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT-412991?style=for-the-badge&logo=openai&logoColor=white)](https://openai.com)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-294%20Passed-success?style=for-the-badge&logo=pytest)](tests/)
[![Code Coverage](https://img.shields.io/badge/Coverage-95%25-brightgreen?style=for-the-badge)]()

**A professional-grade AI content generation platform with modern web UI, CLI tools, and comprehensive API**

[Features](#-features) • [Quick Start](#-quick-start) • [Documentation](#-documentation) • [Examples](#-examples) • [API](#-api-reference)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Screenshots](#-screenshots)
- [Quick Start](#-quick-start)
- [Architecture](#-architecture)
- [Usage Examples](#-usage-examples)
- [Documentation](#-documentation)
- [Testing](#-testing)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 Overview

**AI-ContentGen-Pro** is an enterprise-ready Python application for generating high-quality content using OpenAI's GPT models. Built with modularity, extensibility, and production-readiness in mind, it features:

- 🎨 **Modern Web Interface** - Beautiful Tailwind CSS UI with dark mode
- ⚡ **10+ Pre-built Templates** - Blog posts, social media, product descriptions, and more
- 🔧 **Flexible CLI** - Command-line interface for automation and scripting
- 📊 **Analytics & Monitoring** - Track usage, costs, and performance
- 💾 **Caching System** - Reduce API costs with intelligent response caching
- 🧪 **Comprehensive Testing** - 294 tests with 95%+ coverage
- 📚 **Full Documentation** - Architecture guides, API reference, and examples

### Built With

- **Backend**: Python 3.10+, Flask 2.3+
- **Frontend**: Tailwind CSS 3, Vanilla JavaScript ES6+
- **AI**: OpenAI GPT-3.5/GPT-4 API
- **Testing**: Pytest with coverage reporting
- **Logging**: Structured logging with file rotation

---

## ✨ Features

### 🎨 Web Interface
- **Modern UI/UX** with Tailwind CSS and responsive design
- **Dark/Light Mode** with system preference detection
- **Real-time Cost Estimation** before generation
- **Variable Templates** with dynamic form generation
- **Session Statistics** and generation history
- **Export Options** (copy, download as text)

### 🤖 Content Generation
- **10 Professional Templates**:
  - Blog Post Outlines (SEO-optimized)
  - Social Media Posts (platform-specific)
  - Product Descriptions (e-commerce ready)
  - Email Newsletters
  - Meta Descriptions (SEO)
  - Press Releases
  - FAQ Generators
  - Taglines & Slogans
  - Competitor Analysis
  - Call-to-Action Copy

### 🔧 Advanced Features
- **Template System**: String-based templating with variable substitution
- **Prompt Engineering**: System instructions with user context
- **Error Handling**: Graceful retry logic with exponential backoff
- **Cost Tracking**: Real-time cost calculation per generation
- **Caching**: LRU cache for repeated queries
- **Rate Limiting**: Per-session API throttling
- **Logging**: Structured logs with rotation and compression

### 📊 Analytics
- Total generations count
- Cumulative cost tracking
- Cache hit rate monitoring
- Average generation time
- Per-template statistics

---

## 📸 Screenshots

### Web Interface - Main Dashboard
![Main Interface](docs/screenshots/main-dashboard.png)
*Modern Tailwind CSS interface with template selector and dynamic variable inputs*

### Content Generation
![Generation Output](docs/screenshots/generation-output.png)
*Real-time generation with cost tracking and metadata*

### Dark Mode
![Dark Mode](docs/screenshots/dark-mode.png)
*Beautiful dark mode for comfortable night-time use*

### Statistics Dashboard
![Statistics](docs/screenshots/statistics.png)
*Comprehensive analytics and usage tracking*

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- pip package manager
- OpenAI API key ([Get one here](https://platform.openai.com/api-keys))

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/AI-ContentGen-Pro.git
cd AI-ContentGen-Pro

# 2. Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
python -m src.cli init
# Follow prompts to enter your OpenAI API key

# 5. Run the web application
python gui/app.py
```

Open your browser to `http://127.0.0.1:5000`

### Alternative: CLI Usage

```bash
# Generate content via CLI
python -m src.cli generate \
  --template blog_post_outline \
  --variables '{"title": "AI Safety", "keyword": "ethics", "audience": "developers"}'

# List available templates
python -m src.cli templates

# View statistics
python -m src.cli stats
```

---

## 🏗️ Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────────────┐
│                     Presentation Layer                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Flask GUI   │  │  CLI Tool    │  │  REST API    │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
└─────────┼──────────────────┼──────────────────┼─────────┘
          │                  │                  │
┌─────────┼──────────────────┼──────────────────┼─────────┐
│         │         Business Logic Layer        │         │
│  ┌──────▼──────────────────▼──────────────────▼──────┐  │
│  │          Content Generator (Orchestrator)         │  │
│  └───────┬────────────────────────┬──────────────────┘  │
│          │                        │                      │
│  ┌───────▼─────────┐    ┌─────────▼────────┐           │
│  │ Prompt Engine   │    │  API Manager     │           │
│  │ - Templates     │    │  - OpenAI Client │           │
│  │ - Variables     │    │  - Retry Logic   │           │
│  │ - Rendering     │    │  - Rate Limiting │           │
│  └─────────────────┘    └──────────────────┘           │
└─────────────────────────────────────────────────────────┘
          │                        │
┌─────────┼────────────────────────┼─────────────────────┐
│         │      Infrastructure Layer            │        │
│  ┌──────▼────────┐  ┌──────────▼─────────┐  ┌─▼─────┐ │
│  │ Configuration │  │ Caching & Storage  │  │ Logging│ │
│  └───────────────┘  └────────────────────┘  └────────┘ │
└─────────────────────────────────────────────────────────┘
```

### Key Components

1. **Configuration Layer** (`src/config.py`)
   - Environment variable management
   - API key validation
   - Default parameter configuration

2. **Prompt Engine** (`src/prompt_engine.py`)
   - Template registration and management
   - Variable substitution
   - System instruction handling
   - 10 built-in professional templates

3. **API Manager** (`src/api_manager.py`)
   - OpenAI API abstraction
   - Retry logic with exponential backoff
   - Error handling and recovery
   - Token usage tracking

4. **Content Generator** (`src/content_generator.py`)
   - Main orchestration layer
   - Cost calculation
   - Caching mechanism
   - Statistics tracking
   - Generation history

5. **Web Application** (`gui/app.py`)
   - Flask-based REST API
   - Session management
   - Rate limiting
   - CORS support
   - Static file serving

6. **Utilities** (`src/utils.py`)
   - Message formatting
   - Text sanitization
   - Helper functions

For detailed architecture documentation, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## 💻 Usage Examples

### Python API

```python
from src.content_generator import ContentGenerator

# Initialize generator
generator = ContentGenerator()

# List available templates
templates = generator.list_available_templates()
for template in templates:
    print(f"- {template['name']}: {template['description']}")

# Generate content
result = generator.generate(
    template_name="blog_post_outline",
    variables={
        "title": "The Future of AI",
        "keyword": "artificial intelligence",
        "audience": "tech enthusiasts"
    },
    temperature=0.7,
    max_tokens=500
)

print(result['content'])
print(f"Cost: ${result['cost']:.6f}")
print(f"Tokens: {result['tokens_used']['total']}")
```

### CLI Examples

```bash
# Initialize configuration
python -m src.cli init

# Generate blog post outline
python -m src.cli generate \
  --template blog_post_outline \
  --title "AI Ethics" \
  --keyword "responsible-ai" \
  --audience "developers"

# Generate social media post
python -m src.cli generate \
  --template social_media_post \
  --platform "LinkedIn" \
  --topic "AI Innovation" \
  --cta "Learn more"

# View statistics
python -m src.cli stats
```

### REST API Examples

```bash
# Get available templates
curl http://localhost:5000/api/templates

# Generate content
curl -X POST http://localhost:5000/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "template": "product_description",
    "variables": {
      "product_name": "Ergonomic Keyboard",
      "features": "Mechanical switches, wireless, RGB lighting",
      "audience": "gamers and developers"
    },
    "temperature": 0.7
  }'

# Get statistics
curl http://localhost:5000/api/statistics
```

---

## 📚 Documentation

### Complete Documentation Set

- **[User Guide](docs/USER_GUIDE.md)** - Setup, usage, and troubleshooting
- **[Architecture Guide](docs/ARCHITECTURE.md)** - System design and components
- **[API Reference](docs/API_GUIDE.md)** - REST API endpoints and Python API
- **[Configuration Guide](docs/CONFIGURATION.md)** - Environment variables and settings
- **[Template Development](docs/TEMPLATE_DEVELOPMENT.md)** - Creating custom templates
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Production deployment strategies

---

## 🧪 Testing

### Run Test Suite

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src --cov-report=html

# Run specific test module
pytest tests/test_prompt_engine.py

# Run with verbose output
pytest -v
```

### Test Coverage

```
Module                  Coverage
────────────────────────────────
src/config.py             98%
src/prompt_engine.py      96%
src/api_manager.py        94%
src/content_generator.py  97%
src/utils.py              95%
────────────────────────────────
TOTAL                     95%
```

**294 tests passed** across all modules

---

## 🎨 Template Library

### Available Templates

| Template | Description | Variables | Use Case |
|----------|-------------|-----------|----------|
| `blog_post_outline` | SEO-optimized blog structure | title, keyword, audience | Content marketing |
| `social_media_post` | Platform-optimized posts | platform, topic, cta | Social media |
| `product_description` | E-commerce product copy | product_name, features, audience | Online stores |
| `email_newsletter` | Engaging email content | topic, audience, cta | Email marketing |
| `meta_description` | SEO meta descriptions | topic, keyword | Website SEO |
| `press_release` | Professional announcements | company_name, announcement, location | PR |
| `faq_generator` | Comprehensive FAQ content | product_or_service, audience, focus_area | Support |
| `tagline_slogan` | Memorable brand slogans | brand_name, industry, personality, emotion | Branding |
| `competitor_analysis` | Market research content | company_name, competitors, industry | Strategy |
| `cta_copy` | Conversion-optimized CTAs | action, benefit, urgency | Marketing |

---

## 🔧 Configuration

### Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...        # Your OpenAI API key

# Optional (with defaults)
OPENAI_MODEL=gpt-3.5-turbo   # AI model to use
TEMPERATURE=0.7               # Creativity (0.0-1.0)
MAX_TOKENS=500                # Maximum response length
LOG_LEVEL=INFO                # Logging verbosity
```

---

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📊 Project Stats

- **Lines of Code**: ~5,000+
- **Test Coverage**: 95%+
- **Tests**: 294 passing
- **Templates**: 10 built-in
- **API Endpoints**: 15+
- **Documentation Pages**: 7

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **OpenAI** for the GPT API
- **Flask** framework and community
- **Tailwind CSS** for the beautiful UI
- All contributors and users of this project

---

## 👨‍💻 Author

**Amir Aeiny** - Full-Stack Developer

- 🔗 GitHub: [github.com/DarkOracle10](https://github.com/DarkOracle10)
- 💼 LinkedIn: [linkedin.com/in/amir-aeiny-dev](https://www.linkedin.com/in/amir-aeiny-dev)

---

<div align="center">

**Made with ❤️ by developers, for developers**

⭐ Star this repo if you find it helpful!

[Report Bug](https://github.com/DarkOracle10/AI-ContentGen-Pro/issues) · [Request Feature](https://github.com/DarkOracle10/AI-ContentGen-Pro/issues) · [Documentation](docs/)

</div>
