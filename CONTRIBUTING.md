# Contributing to Article Editor

Thank you for your interest in contributing to Article Editor! This document provides guidelines and information for contributors.

## 🤝 How to Contribute

### Reporting Issues

1. **Search existing issues** to avoid duplicates
2. **Use the issue template** and provide detailed information
3. **Include steps to reproduce** the problem
4. **Attach relevant logs** or error messages
5. **Specify your environment** (OS, Python version, etc.)

### Suggesting Features

1. **Check existing feature requests** first
2. **Explain the use case** and why it would be valuable
3. **Provide mockups or examples** if applicable
4. **Consider backward compatibility** implications

### Contributing Code

1. **Fork the repository** and create a feature branch
2. **Follow coding standards** (see below)
3. **Add tests** for new functionality
4. **Update documentation** as needed
5. **Submit a pull request** with a clear description

## 🛠️ Development Setup

### Prerequisites

- Python 3.8 or higher
- Git
- Anthropic API key for testing

### Local Development

```bash
# Clone your fork
git clone https://github.com/yourusername/article-editor.git
cd article-editor

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install black flake8 mypy pytest pytest-asyncio pytest-cov

# Set up environment
export ANTHROPIC_API_KEY="your-test-api-key"

# Run tests
pytest tests/

# Run formatting
black src/

# Run linting
flake8 src/
```

### Project Structure

```
article_editor/
├── src/                    # Main source code
│   ├── core/              # Core processing logic
│   ├── api/               # API clients
│   ├── cli/               # Command line interfaces
│   ├── web/               # Web application
│   └── utils/             # Utilities
├── web/                   # Frontend assets
├── tests/                 # Test suite
├── examples/              # Usage examples
└── docs/                  # Documentation
```

## 📝 Coding Standards

### Python Code Style

- **Follow PEP 8** with some modifications
- **Use Black** for code formatting
- **Maximum line length**: 100 characters
- **Use type hints** for all function signatures
- **Write docstrings** for all public functions and classes

### Code Quality

```bash
# Format code
black src/ tests/

# Check linting
flake8 src/ tests/

# Type checking
mypy src/

# Run tests with coverage
pytest --cov=src tests/
```

### Commit Messages

Follow conventional commit format:

```
type(scope): description

- feat: new features
- fix: bug fixes
- docs: documentation changes
- style: formatting changes
- refactor: code restructuring
- test: adding tests
- chore: maintenance tasks
```

Examples:
```
feat(chunker): add support for PDF files
fix(api): handle rate limit errors gracefully
docs(readme): update installation instructions
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_chunker.py

# Run with verbose output
pytest -v
```

### Writing Tests

- **Write tests for new features** and bug fixes
- **Use descriptive test names** that explain what is being tested
- **Mock external dependencies** (API calls, file operations)
- **Test both success and failure cases**
- **Include edge cases** and boundary conditions

Example test structure:
```python
def test_chunker_preserves_paragraph_boundaries():
    """Test that chunker respects paragraph boundaries."""
    # Given
    text = "Paragraph 1.\n\nParagraph 2.\n\nParagraph 3."
    chunker = TextChunker(max_tokens=100)
    
    # When
    chunks = chunker.create_chunks_with_overlap(text)
    
    # Then
    assert len(chunks) >= 1
    # More assertions...
```

## 📚 Documentation

### Code Documentation

- **Write clear docstrings** for all public APIs
- **Include parameter and return type information**
- **Provide usage examples** in docstrings
- **Document any exceptions** that may be raised

### README Updates

- **Update feature lists** when adding new functionality
- **Keep examples current** and working
- **Update installation instructions** if dependencies change

## 🐛 Bug Reports

When reporting bugs, please include:

1. **Clear description** of the problem
2. **Steps to reproduce** the issue
3. **Expected vs actual behavior**
4. **Environment information**:
   - Operating system
   - Python version
   - Package versions
   - API model used
5. **Log files** or error messages
6. **Sample files** that reproduce the issue (if applicable)

## 💡 Feature Requests

For feature requests, please provide:

1. **Problem statement** - what issue does this solve?
2. **Proposed solution** - how should it work?
3. **Use cases** - who would benefit from this?
4. **Alternatives considered** - other approaches you've thought of
5. **Implementation notes** - any technical considerations

## 🚀 Pull Request Process

1. **Create a feature branch** from `main`
2. **Make your changes** following the coding standards
3. **Add or update tests** as needed
4. **Update documentation** if necessary
5. **Ensure all tests pass** and code is properly formatted
6. **Submit pull request** with:
   - Clear title and description
   - Reference to related issues
   - Screenshots (for UI changes)
   - Breaking change notes (if any)

### Pull Request Checklist

- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Tests added/updated and passing
- [ ] Documentation updated
- [ ] No merge conflicts
- [ ] Conventional commit messages used

## 🔄 Release Process

1. **Update version numbers** in relevant files
2. **Update CHANGELOG.md** with new features and fixes
3. **Create release notes** highlighting major changes
4. **Tag the release** following semantic versioning
5. **Publish to PyPI** (maintainers only)

## 🆘 Getting Help

- **GitHub Discussions** for questions and general discussion
- **GitHub Issues** for bug reports and feature requests
- **Code reviews** for feedback on pull requests

## 🙏 Recognition

Contributors will be recognized in:
- **README.md** contributors section
- **Release notes** for significant contributions
- **GitHub contributors** page

Thank you for contributing to Article Editor!