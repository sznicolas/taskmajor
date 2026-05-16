# Contributing to TaskMajor

Thank you for your interest in contributing! This guide will help you get started.

## Quick Start for Contributors

### 1. Set Up Your Development Environment

```bash
# Clone the repository
git clone https://github.com/yourusername/taskmajor.git
cd taskmajor

# Install dependencies with uv (recommended)
uv sync

# Or with pip
pip install -e ".[dev]"

# Install pre-commit hooks (recommended for automatic formatting)
pip install pre-commit
pre-commit install
```

### 2. Make Your Changes

```bash
# Create a new branch
git checkout -b feature/your-feature-name

# Make changes to the code
# ...

# Run tests to verify nothing broke
pytest

# Check code style
ruff check .
mypy taskmajor/
```

### 3. Write Tests

Every new feature or bug fix should include tests. See [TESTING.md](./testing.md) for examples.

```bash
# Example: Write a test for your feature
# File: tests/domains/tasks/test_my_feature.py

from unittest.mock import Mock
from taskmajor.domains.tasks import TaskService

def test_my_feature():
    mock_tw = Mock()
    service = TaskService(mock_tw)
    
    result = service.my_new_method()
    
    assert result is not None
    mock_tw.some_method.assert_called_once()

# Run just your tests
pytest tests/domains/tasks/test_my_feature.py -v
```

### 4. Commit and Push

```bash
# Commit with a clear message
git commit -m "feat(tasks): add filtering by custom field

- Explain what the change does
- If it fixes an issue: Fixes #123
"

# Push to your fork
git push origin feature/your-feature-name
```

### 5. Open a Pull Request

On GitHub:
1. Create a PR from your branch to `main`
2. Fill in the PR template
3. Link to any related issues
4. Wait for CI to pass (tests, coverage, linting)
5. Request review from maintainers

## Common Tasks

### Running Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/domains/tasks/test_task_service.py

# Specific test function
pytest tests/domains/tasks/test_task_service.py::test_add_task

# With coverage
pytest --cov=taskmajor

# Only fast tests (skip slow edge cases)
pytest -m "not slow"

# Property-based tests only
pytest -m "property" -v
```

### Debugging Tests

```bash
# Print debug output
pytest -s tests/domains/tasks/test_my_test.py

# Full traceback on failure
pytest -vv --tb=long

# Stop on first failure
pytest -x

# Run last failed tests
pytest --lf
```

### Code Style

```bash
# Check style issues
ruff check .

# Fix style issues automatically
ruff check . --fix

# Type checking
mypy taskmajor/

# Format code
ruff format taskmajor/ tests/
```

### Building Documentation

```bash
# Build HTML docs (requires mkdocs)
pip install mkdocs mkdocs-material
mkdocs serve

# Open http://localhost:8000 in browser
```

## Code Style Guidelines

### Naming Conventions

- **Functions/methods:** `lowercase_with_underscores`
- **Classes:** `PascalCase`
- **Constants:** `UPPERCASE_WITH_UNDERSCORES`
- **Private methods:** `_leading_underscore`

### Comments and Docstrings

```python
def query_tasks(self, filters: TaskQueryFilters) -> dict:
    """Brief description of what the function does.
    
    Longer description if needed. Explain edge cases and assumptions.
    
    Args:
        filters: The query filters to apply
        
    Returns:
        A dict with keys 'tasks' (list) and 'total' (int)
        
    Raises:
        ValueError: If filters are invalid
        
    Example:
        >>> result = service.query_tasks(project="Work")
        >>> len(result['tasks'])
        5
    """
    # Implementation with inline comments for non-obvious logic
    ...
```

### Type Hints

Always use type hints:

```python
# ❌ Bad
def add_task(self, task):
    return task

# ✅ Good
def add_task(self, task: TaskInputDTO) -> TaskOutputDTO:
    return task
```

## Testing Standards

### What to Test

✅ **Business logic** — "Does it work correctly?"  
✅ **Error cases** — "Does it fail gracefully?"  
✅ **Edge cases** — "Does it handle unusual inputs?"  
✅ **Contracts** — "Is the JSON format correct?"  

❌ **Don't test trivial getters** — Unless they have side effects  
❌ **Don't test third-party code** — Unless integrating  
❌ **Don't test implementation details** — Test behavior  

### Test Quality Checklist

- [ ] Test has a descriptive name: `test_query_tasks_filters_by_project`
- [ ] Test has a docstring explaining what it tests
- [ ] Test follows: Setup → Exercise → Verify
- [ ] Test uses appropriate fixtures or mocks
- [ ] Test has assertions that would catch the bug if code changed
- [ ] Test is independent (doesn't depend on other tests)

### Example: Good vs. Bad Tests

```python
# ❌ Bad: Unclear name, multiple assertions, no setup clarity
def test_service():
    service = TaskService(Mock())
    result = service.query_tasks()
    assert result
    assert result['total'] == 0

# ✅ Good: Clear name, focused test, setup/exercise/verify
def test_query_tasks_returns_empty_when_no_tasks_in_taskwarrior(mock_task_service):
    """Empty TaskWarrior returns empty result with total=0."""
    result = mock_task_service.query_tasks()
    
    assert result['tasks'] == []
    assert result['total'] == 0
```

## Pull Request Checklist

Before submitting a PR:

- [ ] Tests written and passing (`pytest`)
- [ ] Code follows style guide (`ruff check .`, `mypy`)
- [ ] Documentation updated if needed
- [ ] Commit messages are clear and follow convention
- [ ] No debug code or print statements left
- [ ] No breaking changes without discussion
- [ ] Changelog entry added (if applicable)

## Getting Help

- **Documentation:** [TESTING.md](./testing.md) for test examples
- **Questions:** Open a discussion or ask in PR comments
- **Bugs:** Open an issue with reproduction steps
- **Ideas:** Discuss in Issues before implementing

## Code of Conduct

Please be respectful and constructive in all interactions.

## Questions?

If you're stuck:
1. Check the [TESTING.md](./testing.md) guide
2. Look at similar tests for examples
3. Run with `-s` flag to see debug output
4. Ask in the PR or open a discussion

Happy contributing! 🎉
