# Contributing to Agent Orchestration Platform

Thank you for your interest in contributing to the Agent Orchestration Platform! This document provides guidelines and information for contributors.

## Code of Conduct

This project follows a code of conduct to ensure a welcoming environment for all contributors. By participating, you agree to:

- Be respectful and inclusive
- Focus on constructive feedback
- Accept responsibility for mistakes
- Show empathy towards other contributors
- Help create a positive community

## Development Setup

### Prerequisites

- Python 3.11 or later
- Git
- Docker (recommended)

### Local Development

1. **Fork and clone the repository**:
   ```bash
   git clone https://github.com/your-org/agent-orchestration.git
   cd agent-orchestration
   ```

2. **Set up the development environment**:
   ```bash
   # Create virtual environment
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate

   # Install dependencies
   pip install -e .[dev,test]

   # Install pre-commit hooks
   pre-commit install
   ```

3. **Verify setup**:
   ```bash
   # Run tests
   pytest

   # Run linting
   pre-commit run --all-files

   # Run type checking
   mypy src/
   ```

## Development Workflow

### 1. Choose an Issue

- Check the [issue tracker](https://github.com/your-org/agent-orchestration/issues) for open issues
- Look for issues labeled `good first issue` or `help wanted`
- Comment on the issue to indicate you're working on it

### 2. Create a Branch

```bash
# Create and switch to a feature branch
git checkout -b feature/your-feature-name
# Or for bug fixes
git checkout -b fix/issue-number-description
```

### 3. Write Tests First (TDD)

This project follows Test-Driven Development principles:

```bash
# Create test file first
touch tests/test_your_feature.py

# Write failing tests
pytest tests/test_your_feature.py  # Should fail

# Implement the feature
# Write code until tests pass
pytest tests/test_your_feature.py  # Should pass
```

### 4. Implement Your Changes

- Follow the existing code style and patterns
- Add type hints for all function parameters and return values
- Write clear, concise commit messages
- Keep changes focused and atomic

### 5. Run Quality Checks

```bash
# Run all tests
pytest --cov=src --cov-report=term-missing

# Run linting and formatting
pre-commit run --all-files

# Run type checking
mypy src/

# Build documentation (if applicable)
# sphinx-build docs/ docs/_build/
```

### 6. Update Documentation

- Update README.md if adding new features
- Add docstrings to all public functions/classes
- Update type hints and examples

### 7. Commit Your Changes

```bash
# Stage your changes
git add .

# Commit with a clear message
git commit -m "feat: add new workflow execution feature

- Add support for parallel workflow execution
- Implement workflow step dependencies
- Add comprehensive error handling

Closes #123"
```

### 8. Create a Pull Request

1. Push your branch to GitHub:
   ```bash
   git push origin feature/your-feature-name
   ```

2. Create a Pull Request on GitHub with:
   - Clear title describing the change
   - Detailed description of what was changed and why
   - Reference to any related issues
   - Screenshots/demos if applicable

3. Wait for review and address any feedback

## Coding Standards

### Python Style

- Follow [PEP 8](https://pep8.org/) style guidelines
- Use [Black](https://black.readthedocs.io/) for code formatting
- Use [Flake8](https://flake8.pycqa.org/) for linting
- Use [MyPy](https://mypy.readthedocs.io/) for type checking

### Code Structure

- Organize code into logical modules
- Use clear, descriptive names for variables and functions
- Add docstrings to all public functions and classes
- Keep functions small and focused on a single responsibility

### Testing

- Write tests for all new features and bug fixes
- Aim for high test coverage (>80%)
- Use descriptive test names that explain what they're testing
- Test both success and failure scenarios

### Documentation

- Write clear, concise docstrings using Google style
- Include type hints for all parameters and return values
- Provide usage examples where helpful
- Keep documentation up to date with code changes

## Commit Message Guidelines

Follow conventional commit format:

```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Test additions/changes
- `chore`: Maintenance tasks

Examples:
```
feat(cli): add workflow status command
fix(api): handle timeout errors gracefully
docs(readme): update installation instructions
```

## Testing Strategy

### Unit Tests

- Test individual functions and classes in isolation
- Mock external dependencies
- Focus on logic and edge cases

### Integration Tests

- Test interactions between components
- Use real dependencies where possible
- Test complete workflows end-to-end

### Contract Tests

- Test API contracts and interfaces
- Ensure compatibility between versions
- Validate data structures and schemas

### E2E Tests

- Test complete user workflows
- Validate real-world usage scenarios
- Run in staging environment before production

## Release Process

1. **Version Bumping**: Update version in `pyproject.toml`
2. **Changelog**: Update CHANGELOG.md with new features and fixes
3. **Release Branch**: Create release branch from main
4. **Testing**: Run full test suite and integration tests
5. **Release**: Create GitHub release with changelog
6. **Deploy**: Automated deployment to PyPI and Docker Hub

## Getting Help

- 📖 [Documentation](https://agent-orchestration.readthedocs.io/)
- 🐛 [Issue Tracker](https://github.com/your-org/agent-orchestration/issues)
- 💬 [Discussions](https://github.com/your-org/agent-orchestration/discussions)
- 📧 [Mailing List](mailto:agent-orchestration-dev@googlegroups.com)

## Recognition

Contributors are recognized in:
- CHANGELOG.md for significant contributions
- GitHub's contributor insights
- Release notes
- Project documentation

Thank you for contributing to the Agent Orchestration Platform! 🎉