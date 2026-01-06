# Contributing to AI-ContentGen-Pro

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Code Style](#code-style)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)

---

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inspiring community for all. Please be respectful and constructive in all interactions.

### Expected Behavior

- Use welcoming and inclusive language
- Be respectful of differing viewpoints
- Gracefully accept constructive criticism
- Focus on what is best for the community
- Show empathy towards other community members

### Unacceptable Behavior

- Harassment, discrimination, or trolling
- Publishing others' private information
- Other conduct which could reasonably be considered inappropriate

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Git
- Virtual environment tool (venv)
- OpenAI API key for testing

### Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/AI-ContentGen-Pro.git
cd AI-ContentGen-Pro

# Add upstream remote
git remote add upstream https://github.com/ORIGINAL_OWNER/AI-ContentGen-Pro.git
```

### Development Setup

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Configure environment
cp .env.example .env
# Edit .env with your API key
```

---

## Development Workflow

### 1. Create a Branch

```bash
# Update your fork
git fetch upstream
git checkout main
git merge upstream/main

# Create feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/bug-description
```

### 2. Make Changes

- Write code following our [Code Style](#code-style)
- Add tests for new features
- Update documentation as needed
- Keep commits logical and atomic

### 3. Commit Changes

```bash
# Stage changes
git add .

# Commit with descriptive message
git commit -m "feat: add new template for email campaigns"
```

#### Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples**:
```bash
feat(templates): add newsletter template
fix(api): resolve rate limiting issue
docs(readme): update installation instructions
test(generator): add unit tests for caching
```

### 4. Push Changes

```bash
git push origin feature/your-feature-name
```

### 5. Create Pull Request

Go to GitHub and create a Pull Request from your fork to the main repository.

---

## Code Style

### Python Style Guide

We follow [PEP 8](https://pep8.org/) with these tools:

#### Black (Code Formatter)

```bash
# Format all files
black src/ tests/ gui/

# Check without formatting
black --check src/
```

#### Flake8 (Linter)

```bash
# Lint all files
flake8 src/ tests/ gui/

# Configuration in setup.cfg
```

#### isort (Import Sorting)

```bash
# Sort imports
isort src/ tests/ gui/

# Check only
isort --check-only src/
```

#### mypy (Type Checking)

```bash
# Type check
mypy src/
```

### Code Conventions

#### 1. Type Hints

Always use type hints:

```python
# Good ✓
def generate_content(template: str, variables: Dict[str, str]) -> Dict[str, Any]:
    """Generate content using template and variables."""
    pass

# Bad ✗
def generate_content(template, variables):
    pass
```

#### 2. Docstrings

Use Google-style docstrings:

```python
def calculate_cost(tokens: int, model: str) -> float:
    """Calculate cost for token usage.
    
    Args:
        tokens: Number of tokens used
        model: Model identifier (e.g., 'gpt-3.5-turbo')
        
    Returns:
        Cost in USD
        
    Raises:
        ValueError: If tokens is negative
        
    Example:
        >>> calculate_cost(1000, 'gpt-3.5-turbo')
        0.002
    """
    pass
```

#### 3. Error Handling

Be explicit with exception handling:

```python
# Good ✓
try:
    result = api_call()
except APIError as e:
    logger.error(f"API call failed: {e}")
    raise GenerationError("Failed to generate content") from e
except ValidationError as e:
    logger.warning(f"Invalid input: {e}")
    return {"error": "Invalid input"}

# Bad ✗
try:
    result = api_call()
except Exception:
    pass
```

#### 4. Logging

Use structured logging:

```python
import logging

logger = logging.getLogger(__name__)

# Good ✓
logger.info(
    "Content generated",
    extra={
        "template": template_name,
        "tokens": tokens_used,
        "cost": cost,
        "duration": duration
    }
)

# Bad ✗
print("Content generated")
```

#### 5. Naming Conventions

```python
# Classes: PascalCase
class ContentGenerator:
    pass

# Functions/methods: snake_case
def generate_content():
    pass

# Constants: UPPER_SNAKE_CASE
MAX_RETRIES = 3
DEFAULT_TEMPERATURE = 0.7

# Private: leading underscore
def _internal_helper():
    pass
```

---

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_prompt_engine.py

# Run specific test
pytest tests/test_prompt_engine.py::test_template_rendering

# Run with verbose output
pytest -v

# Run and show print statements
pytest -s
```

### Writing Tests

#### Test Structure

```python
import pytest
from src.content_generator import ContentGenerator

class TestContentGenerator:
    """Test suite for ContentGenerator."""
    
    @pytest.fixture
    def generator(self):
        """Create generator instance for testing."""
        return ContentGenerator()
    
    def test_list_templates(self, generator):
        """Test listing available templates."""
        templates = generator.list_available_templates()
        assert len(templates) > 0
        assert all('name' in t for t in templates)
    
    def test_invalid_template(self, generator):
        """Test handling of invalid template."""
        with pytest.raises(ValueError):
            generator.generate("nonexistent_template", {})
```

#### Mocking API Calls

```python
from unittest.mock import Mock, patch

def test_generation_with_mock():
    """Test content generation with mocked API."""
    with patch('src.api_manager.OpenAIManager') as mock_api:
        mock_api.return_value.chat_completion.return_value = "Test content"
        
        generator = ContentGenerator()
        result = generator.generate("test_template", {"topic": "AI"})
        
        assert result['content'] == "Test content"
        mock_api.return_value.chat_completion.assert_called_once()
```

#### Test Coverage Goals

- Maintain >90% code coverage
- Test all public APIs
- Test error conditions
- Test edge cases

---

## Pull Request Process

### Before Submitting

1. **Update your branch**:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run quality checks**:
   ```bash
   # Format code
   black src/ tests/
   isort src/ tests/
   
   # Lint
   flake8 src/ tests/
   mypy src/
   
   # Test
   pytest --cov=src
   ```

3. **Update documentation**:
   - Update README.md if needed
   - Add/update docstrings
   - Update relevant docs in `docs/`

4. **Commit checklist**:
   - [ ] Code follows style guidelines
   - [ ] Tests pass
   - [ ] New tests added for new features
   - [ ] Documentation updated
   - [ ] No merge conflicts
   - [ ] Commit messages are clear

### PR Description Template

```markdown
## Description
Brief description of the changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Changes Made
- List of specific changes
- Another change
- etc.

## Testing
Description of tests added/modified

## Screenshots (if applicable)
Add screenshots here

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-reviewed code
- [ ] Commented complex code
- [ ] Updated documentation
- [ ] No new warnings
- [ ] Added tests
- [ ] Tests pass locally
- [ ] Dependent changes merged
```

### Review Process

1. **Automated checks** must pass:
   - Linting (flake8)
   - Type checking (mypy)
   - Tests (pytest)
   - Coverage check

2. **Code review** by maintainer(s):
   - Code quality
   - Test coverage
   - Documentation
   - Best practices

3. **Address feedback**:
   ```bash
   # Make changes
   git add .
   git commit -m "fix: address review feedback"
   git push origin feature/your-feature-name
   ```

4. **Approval and merge**:
   - Approved PRs are merged by maintainers
   - Squash merge for feature branches
   - Merge commit for main branches

---

## Issue Reporting

### Bug Reports

Use the bug report template:

```markdown
**Describe the bug**
Clear description of the bug

**To Reproduce**
Steps to reproduce:
1. Go to '...'
2. Click on '....'
3. See error

**Expected behavior**
What you expected to happen

**Actual behavior**
What actually happened

**Screenshots**
If applicable, add screenshots

**Environment:**
 - OS: [e.g. Windows 10]
 - Python version: [e.g. 3.11]
 - Version: [e.g. 1.0.0]

**Additional context**
Any other relevant information
```

### Feature Requests

Use the feature request template:

```markdown
**Is your feature request related to a problem?**
Description of the problem

**Describe the solution you'd like**
Clear description of what you want

**Describe alternatives you've considered**
Alternative solutions or features

**Additional context**
Any other relevant information
```

---

## Project Structure

```
AI-ContentGen-Pro/
├── src/                    # Core application code
│   ├── __init__.py
│   ├── config.py          # Configuration management
│   ├── prompt_engine.py   # Template system
│   ├── api_manager.py     # API integration
│   ├── content_generator.py  # Main logic
│   ├── utils.py           # Utilities
│   └── cli.py             # CLI interface
├── gui/                    # Web application
│   ├── app.py             # Flask application
│   ├── templates/         # Jinja2 templates
│   └── static/            # Static assets
├── tests/                  # Test suite
│   ├── test_*.py          # Test files
│   └── conftest.py        # Pytest configuration
├── docs/                   # Documentation
│   ├── *.md               # Documentation files
│   └── screenshots/       # UI screenshots
├── examples/               # Example usage
├── deployment/             # Deployment configs
├── requirements.txt        # Dependencies
├── requirements-dev.txt    # Dev dependencies
├── setup.py               # Package setup
├── .env.example           # Example environment config
├── .gitignore             # Git ignore rules
└── README.md              # Main documentation
```

---

## Development Best Practices

### 1. Keep Changes Focused

- One feature/fix per PR
- Small, reviewable changes
- Logical commit history

### 2. Write Tests First

- TDD approach when possible
- Write failing test
- Implement feature
- Verify test passes

### 3. Document As You Go

- Update docs with code changes
- Add inline comments for complex logic
- Keep README up to date

### 4. Communication

- Comment on issues before starting work
- Ask questions in discussions
- Be responsive to review feedback
- Update issue/PR status

---

## Resources

- [Python PEP 8](https://pep8.org/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Pytest Documentation](https://docs.pytest.org/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)

---

## Questions?

- Check [docs/](docs/) for detailed guides
- Search [existing issues](https://github.com/yourusername/AI-ContentGen-Pro/issues)
- Ask in [Discussions](https://github.com/yourusername/AI-ContentGen-Pro/discussions)
- Contact maintainers

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

## Thank You!

Your contributions make this project better for everyone. We appreciate your time and effort! 🙏
