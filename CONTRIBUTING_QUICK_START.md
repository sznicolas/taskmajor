# TaskMajor Contributor Quick Start

> **New to TaskMajor?** This guide will get you contributing in <10 minutes.

## Prerequisites

- Python 3.10+ (check: `python --version`)
- Git (check: `git --version`)
- TaskWarrior (optional, only needed for live testing)

## Setup (5 minutes)

### 1. Clone & Install

```bash
git clone https://github.com/nschmeltz/taskmajor.git
cd taskmajor
uv sync              # Install dependencies
```

### 2. Install Pre-commit Hooks (recommended)

```bash
pip install pre-commit
pre-commit install    # Auto-formats code before each commit
```

### 3. Verify Everything Works

```bash
./scripts/run_tests.sh --quick    # Should pass (148 tests in ~10s)
```

✅ **You're ready to code!**

---

## Making Your First Contribution

### 1. Create a Feature Branch

```bash
git checkout -b feature/my-cool-feature
```

### 2. Make Changes

```bash
# Edit files
nano taskmajor/domains/tasks/service.py

# Run tests to ensure nothing broke
./scripts/run_tests.sh --quick
```

### 3. Write Tests

Every change needs tests. See examples:

```bash
# Browse test examples
cat TESTING.md                    # Full guide with 4 examples
cat tests/conftest.py             # 9 available fixtures

# Copy an example test
cp tests/domains/tasks/test_task_service.py \
   tests/domains/tasks/test_my_feature.py

# Modify and run
pytest tests/domains/tasks/test_my_feature.py -v
```

### 4. Validate Locally

```bash
# Run everything (tests, coverage, lint)
./scripts/run_tests.sh

# Should show: ✅ All checks passed!
```

### 5. Commit & Push

```bash
git add .
git commit -m "feat: add my cool feature

- Brief explanation
- Why it's needed
- Any trade-offs"
git push origin feature/my-cool-feature
```

**Note:** Pre-commit hooks will auto-format your code before committing.

### 6. Open Pull Request

1. Go to https://github.com/nschmeltz/taskmajor
2. Click "Pull Requests" → "New Pull Request"
3. Select your branch
4. Fill in the description
5. Click "Create Pull Request"

**GitHub Actions will automatically:**
- Run all 148 tests on Python 3.10, 3.11, 3.12
- Check code coverage (must be ≥60%)
- Lint code with ruff and mypy
- Comment with results

### 7. Address Feedback

If a check fails:
1. See details by clicking the failing check
2. Fix locally: `./scripts/run_tests.sh`
3. Commit and push again
4. CI automatically re-runs

### 8. Merge!

Once all checks pass and a team member approves → you can merge.

---

## Common Tasks

### Run all tests
```bash
./scripts/run_tests.sh
# or
pytest
```

### Run specific test
```bash
pytest tests/domains/tasks/test_task_service.py::test_query_tasks -v
```

### Check code coverage
```bash
./scripts/run_tests.sh --coverage
open htmlcov/index.html    # View in browser
```

### Fix formatting automatically
```bash
uv run ruff format .       # Code style
uv run ruff check . --fix  # Lint errors
```

### See what tests exist
```bash
pytest --collect-only -q  # List all tests
pytest -k "filter"         # Run only tests matching "filter"
```

### Debug a test
```bash
# Show print() output
pytest tests/my_test.py -s

# Verbose output
pytest tests/my_test.py -vv

# Stop at first failure
pytest tests/my_test.py -x
```

---

## Test File Structure

Choose where to put your test:

```
Feature Type              → Test Location
─────────────────────────────────────────────────
TaskService logic         → tests/domains/tasks/test_task_service.py
Task filtering            → tests/domains/tasks/test_filters.py
Edge cases/boundaries     → tests/domains/tasks/test_edge_cases.py
MCP endpoint validation   → tests/mcp/test_mcp_endpoints.py
Config/TaskWarrior init   → tests/domains/taskwarrior/test_*.py
End-to-end integration    → tests/integration/test_*.py
```

---

## Test Writing Examples

### Example 1: Simple Unit Test

```python
from unittest.mock import Mock
from taskmajor.domains.tasks import TaskService

def test_query_tasks_returns_empty_when_no_matches(mock_taskwarrior):
    """Test that query_tasks returns empty list when no tasks match."""
    mock_taskwarrior.get_tasks.return_value = {"tasks": []}
    service = TaskService(mock_taskwarrior)
    
    result = service.query_tasks()
    
    assert result.tasks == []
    assert result.total == 0
```

### Example 2: With Fixtures

```python
def test_add_task_with_project(mock_task_service, sample_task):
    """Test adding task with project assignment."""
    sample_task.project = "Work"
    
    result = mock_task_service.add_task(
        title="New task",
        project="Work"
    )
    
    assert result.project == "Work"
    mock_task_service._taskwarrior.add_task.assert_called_once()
```

### Example 3: Testing Errors

```python
import pytest

def test_query_tasks_raises_on_invalid_status(mock_task_service):
    """Test that invalid status raises ValueError."""
    with pytest.raises(ValueError, match="invalid status"):
        mock_task_service.query_tasks(status="invalid")
```

See [TESTING.md](TESTING.md) for more examples and detailed explanations.

---

## Available Fixtures

Use these in your tests (defined in `tests/conftest.py`):

| Fixture | Purpose | Example |
|---------|---------|---------|
| `mock_taskwarrior` | Mocked TaskWarrior client | `mock_taskwarrior.get_tasks()` |
| `mock_task_service` | Pre-configured TaskService | `mock_task_service.query_tasks()` |
| `sample_task` | Single test task | `sample_task.title = "Test"` |
| `sample_tasks` | 6 diverse test tasks | `assert len(sample_tasks) == 6` |
| `default_config` | Default TaskMajor config | `config.server_port` |
| `custom_config` | Custom config values | `config.server_port` |
| `tmp_taskrc` | Temporary taskrc file | For file I/O tests |
| `tmp_taskdata` | Temporary task data dir | For file I/O tests |
| `hypothesis_settings` | Hypothesis configuration | For property-based tests |

---

## Troubleshooting

### Problem: Tests fail locally but CI passed

**Solution:**
```bash
uv sync --all-groups    # Update dependencies
python --version         # Check Python version matches CI (3.10+)
```

### Problem: Pre-commit hook keeps fixing files

**Solution:**
Run once to fix everything, then commit again:
```bash
pre-commit run --all-files
git add .
git commit -m "chore: fix code style"
```

### Problem: Can't figure out what the test should do

**Solution:**
1. Read the existing test in that file
2. Check [TESTING.md](TESTING.md) for 4 complete examples
3. Ask in GitHub Issues or Discussions

### Problem: Pre-commit hook takes too long

**Solution:**
It's running mypy (type checking). If it hangs:
```bash
# Cancel it (Ctrl+C) and commit without verification
git commit --no-verify -m "your message"
```

Then run manually:
```bash
uv run mypy taskmajor
```

---

## Code Style

TaskMajor uses:
- **Formatting:** Ruff formatter (auto-enforced)
- **Linting:** Ruff linter (auto-enforced)
- **Type checking:** mypy (enforced in CI)
- **Max line length:** 100 characters

**Good news:** Pre-commit hooks auto-fix 90% of style issues!

---

## Documentation

When writing code, update docs:

- **New feature:** Add example to README.md
- **New parameter:** Update docstring in code
- **Test discovery:** Document in [TESTING.md](TESTING.md)
- **Major change:** Update relevant file in `docs/`

---

## Getting Help

1. **How to run tests?** → See [TESTING.md](TESTING.md)
2. **How to write tests?** → See [TESTING.md](TESTING.md#writing-tests)
3. **How does the code work?** → See [docs/architecture.md](docs/architecture.md)
4. **How do I set up development?** → See [docs/contributing.md](docs/contributing.md)
5. **Debugging CI failures?** → See [TESTING.md](TESTING.md#cicd-integration--quality-gates)

---

## What to Contribute

### Good First Issues
- [ ] Add tests for uncovered code
- [ ] Improve error messages
- [ ] Add documentation examples
- [ ] Fix edge cases found in property tests

### Medium Issues
- [ ] Add new TaskService methods
- [ ] Add new MCP resources
- [ ] Improve filtering performance
- [ ] Add new config options

### Advanced Issues
- [ ] Add async/await support
- [ ] Add Docker integration tests
- [ ] Optimize critical paths
- [ ] Add new agent integrations

---

## Tips for Great PRs

1. **Small & focused** — One feature per PR
2. **Well-tested** — Include tests (required)
3. **Good messages** — Clear commit messages
4. **Documentation** — Update docs as needed
5. **No breaking changes** — Maintain backward compatibility (unless documented)

---

## What Happens After You Open a PR

```
1. GitHub Actions runs (60 seconds)
   → Tests on Python 3.10, 3.11, 3.12
   → Coverage check
   → Lint check

2. You see results
   ✅ All passed!  OR  ❌ Something failed

3. If failed:
   → See details (click the red X)
   → Fix locally (./scripts/run_tests.sh)
   → Push again (CI auto-reruns)

4. Once all green:
   → Team member reviews your code
   → They comment or approve
   → You address feedback
   → They merge when ready
```

---

## Success Checklist

Before opening a PR:

- [ ] Created a new branch (`git checkout -b feature/...`)
- [ ] Made changes to code
- [ ] Wrote or updated tests
- [ ] All tests pass (`./scripts/run_tests.sh`)
- [ ] Pre-commit hooks installed and run
- [ ] Committed with clear message
- [ ] Pushed to your fork
- [ ] Ready to open PR on GitHub

---

**Questions?** Open an issue on GitHub or check [docs/contributing.md](docs/contributing.md)

**Ready to contribute?** Start with the setup section above! 🚀
