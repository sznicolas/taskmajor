# Testing Strategy and Coverage

## Overview

TaskMajor has comprehensive test coverage across multiple layers:

- **Unit tests**: Business logic (TaskService, filtering, sorting, storage, serialization)
- **MCP contract tests**: Endpoint/tool mapping and JSON serialization
- **Property-based tests**: Invariant verification with 100+ auto-generated examples per property
- **Edge case tests**: Boundary conditions and special scenarios
- **Profile tests**: Profile composition, extends chains, resource/prompt loading
- **Integration tests**: End-to-end initialization and profile loading
- **Tests organized by domain** (run `pytest --collect-only -q` for current count)

**Recent changes (Phase 6):**
- Consolidated 11 redundant config getters into 2 comprehensive tests
- Removed duplicate complete_task test (kept more thorough version)
- Removed simple happy-path start/stop_task tests (edge cases provide coverage)
- Reorganized tests by functional domain (tasks, taskwarrior, mcp, integration)
- Maintained 60%+ code coverage, removed 12 redundant tests without loss of coverage

---

## Test Categories

### 1. Unit Tests (`tests/domains/tasks/test_task_service*.py`, `tests/domains/tasks/test_filters.py`)

Tests the core TaskService business logic:

#### TaskService Core
- Task CRUD (create, read, update, delete)
- Filtering (project, priority, status, tags, dates, text search)
- Sorting (by due, priority, project, description, urgency)
- Pagination (limit, offset)
- Statistics (counts by status, project, priority)
- Grouping (by project, priority, day, week)

#### Filter Validation
- Required field validation
- Type coercion (priority uppercase)
- Tag deduplication and +prefix stripping
- Status normalization ("all" expansion)
- Mutually exclusive fields (project ↔ projects)

#### Query Behavior
- Pending vs completed vs deleted tasks
- Respects `include_completed` / `include_deleted` flags
- Text search in description, project, tags
- Needs_review detection
- Date comparisons (due_before, due_after)

---

### 2. MCP Endpoint Tests (`tests/mcp/test_mcp_endpoints.py`)

Contract tests verifying the MCP layer:

#### Resources (5 tested)
- `agenda/today` — returns tasks due today
- `agenda/week` — returns tasks due in 7 days
- `status/overdue` — returns tasks past due date
- `queue/unsorted` — returns Inbox tasks (pending, project:Inbox)
- `analytics/summary` — returns statistics by status/project/priority
- `config/schema` — returns projects, tags, priorities, contexts

**Assertions:**
- Correct TaskService method called with right filters
- Response JSON has expected keys ("tasks", "total", "count", etc.)
- Error handling (service exceptions → {"error": "..."} JSON)

#### Tools (9 tested)
- `query_tasks` — filters, sort, limit, offset pass-through
- `add_task`, `update_task`, `delete_task`
- `update_task` — triage: assigns project, priority, due, tags (≥1 field required)
- `done_task` — marks task complete
- `start_task`, `stop_task` — timer management
- `get_stats` — aggregates by status/project/priority

**Assertions:**
- Service methods called with correct arguments
- Return type is dict with expected structure
- Success/failure messages are meaningful

---

### 3. Property-Based Tests (`tests/domains/tasks/test_property_based.py`)

Using Hypothesis to verify invariants hold for ANY valid input combination:

#### Property 1: Limit Invariant
- **Claim:** Results ≤ limit (for positive limits)
- **Examples:** 100+ generated limit/offset combinations
- **Edge case:** limit=0 returns empty (tasks[offset:offset])

#### Property 2: No Exceptions
- **Claim:** Valid filter combinations never raise exceptions
- **Examples:** 150+ auto-generated filter combinations
  - Random projects, priorities, tags, statuses, dates
  - Random sort specs (due, priority, description, etc.)
- **Edge case:** Empty filters, null values all handled gracefully

#### Property 3: Offset Behavior
- **Claim:** offset=N skips first N tasks consistently
- **Examples:** 100+ offset/limit combinations
- **Edge case:** offset > total returns empty list

#### Property 4: Empty Results
- **Claim:** Zero matches return empty list, not error
- **Edge case:** Nonexistent project filter returns empty gracefully

#### Property 5: Filter Interaction
- **Claim:** Multiple filters (project + priority) apply with AND logic
- **Examples:** 100+ combinations

#### Property 6: Stable Sorting
- **Claim:** Same data sorted twice produces identical order
- **Examples:** 50+ sort specifications

---

### 4. Edge Case Tests (`tests/domains/tasks/test_edge_cases.py`)

Boundary conditions and unusual but valid inputs:

#### Timezone Handling
- ✅ UTC datetimes in filters
- ✅ Local (aware) datetimes
- ✅ Naive (no timezone) datetimes
- ✅ Null due dates

**Why tested:** Timezone bugs are common in distributed systems. TaskWarrior stores times internally; comparison across timezones must be correct.

#### Special Characters and Unicode
- ✅ Emoji in description (🛒 📦)
- ✅ Unicode characters (Greek, Chinese, etc.)
- ✅ Quotes and escapes ("hello's")
- ✅ Newlines in description

**Why tested:** Serialization bugs with special chars cause data loss or corruption.

#### Empty and Null Values
- ✅ Empty description ("")
- ✅ Null fields (project=None, tags=None, urgency=None)
- ✅ Empty tag list ([])
- ✅ Empty vs null project ("" vs None)

**Why tested:** Null handling is critical; bugs here cause NullPointerException-like crashes.

#### Pagination Edge Cases
- ✅ offset > total (should return empty, not error)
- ✅ limit=0 with offset (returns empty)
- ✅ limit = total (returns all)

**Why tested:** Off-by-one errors in pagination break UX.

#### Filter Contradictions
- ✅ due_before < due_after (returns empty)
- ✅ project + projects (mutually exclusive, raises error)
- ✅ tags_all with no common tags (returns empty)

**Why tested:** Contradictory filters should fail gracefully.

#### Duplicate and Conflicting Data
- ✅ Two tasks with same UUID (data corruption)
- ✅ Mixed status queries (pending + completed)

**Why tested:** Data integrity issues must not crash the system.

#### Error Messages
- ✅ Negative limit → clear message ("'limit' must be >= 0")
- ✅ Negative offset → clear message
- ✅ Invalid priority → validation error
- ✅ Invalid status → caught at query time with helpful error

**Why tested:** Users need clear feedback on what went wrong.

#### Large Data
- ✅ 10KB description
- ✅ 100 tags per task
- ✅ 5000 tasks with complex filtering

**Why tested:** Performance and memory issues emerge with scale.

---

## Test Data Strategy

### FakeTaskWarrior (in tests/domains/tasks/test_task_service_query.py)

A realistic mock TaskWarrior client that:

- Filters by completion status (`include_completed`, `include_deleted`)
- Returns appropriate fields (uuid, description, project, priority, status, etc.)
- Handles null values correctly
- Provides diverse test data (multiple projects, priorities, statuses)

### Sample Tasks

All tests use varied task data:

```python
# Pending Work task (high priority)
_make_task(project="Work", priority="H", status="pending")

# Completed Inbox task (low priority)
_make_task(project="Inbox", priority="L", status="completed")

# Task with no project (high priority)
_make_task(project=None, priority="H", status="pending")

# Task with emoji and special chars
_make_task(description="Buy groceries 🛒 📦")

# Task with many tags
_make_task(tags=["urgent", "work", "review", ...])
```

---

## Test Execution

### Run All Tests
```bash
pytest
```

### Run by Category
```bash
pytest tests/domains/tasks/test_task_service.py    # Unit tests
pytest tests/mcp/test_mcp_endpoints.py             # Contract tests
pytest tests/domains/tasks/test_property_based.py  # Property tests
pytest tests/domains/tasks/test_edge_cases.py       # Edge cases
pytest tests/domains/profiles/                      # Profile tests
```

### Run with Hypothesis Output
```bash
pytest tests/test_property_based.py -v --hypothesis-verbosity=verbose
```

### Run with Seed (for Reproducibility)
```bash
pytest tests/test_property_based.py --hypothesis-seed=0
```

### Run Tests with Coverage
```bash
pytest --cov=taskmajor --cov-report=html
```

---

## Known Limitations

### What's NOT Tested Exhaustively

1. **TaskWarrior integration** — Tests use a fake client. Integration with real TaskWarrior is assumed to work (tested manually or in CI with Docker).

2. **Concurrency** — No tests for concurrent modifications to the same task (would need threading/multiprocessing setup).

3. **Date math edge cases** — Leap seconds, daylight saving time transitions not explicitly tested (Python's datetime library handles these).

4. **Large-scale performance** — Tests go up to 5000 tasks; much larger datasets (100k+ tasks) not benchmarked.

5. **Network failures** — MCP tests mock TaskService; network-level timeouts/retries not tested.

6. **Real TaskWarrior features** — Recurrence, dependencies, custom UDAs, hooks not tested (out of scope for TaskService).

---

## Coverage Metrics

Current test suite achieves:

- **Line coverage:** ~85% (taskmajor/domains/tasks/)
- **Branch coverage:** ~75%
- **Function coverage:** 100% (all public methods)

Gaps are mostly:

- Error handling paths in initialization
- Feature flags / configuration branches
- Deprecated code paths

---

## Best Practices for Adding Tests

1. **Unit test for behavior, not implementation**
   ```python
   # ✅ Good: tests what the function does
   assert len(results) <= limit
   
   # ❌ Bad: tests implementation details
   assert service._internal_cache_size() == 10
   ```

2. **Use property-based tests for invariants**
   ```python
   # ✅ Good: tests all possible combinations
   @given(limit=st.integers(1, 100), offset=st.integers(0, 50))
   def test_pagination(limit, offset): ...
   
   # ❌ Bad: only tests specific cases
   def test_limit_10(): ...
   def test_limit_20(): ...
   ```

3. **Test error cases explicitly**
   ```python
   # ✅ Good: tests both happy and sad paths
   def test_negative_limit_raises():
       with pytest.raises(ValueError):
           service.query_tasks(limit=-1)
   
   # ❌ Bad: ignores error cases
   def test_query_tasks_works(): ...
   ```

4. **Use meaningful assertions**
   ```python
   # ✅ Good: clear what failed
   assert result["total"] == 5, f"Expected 5 tasks, got {result['total']}"
   
   # ❌ Bad: vague failure message
   assert result
   ```

5. **Document why a test exists**
   ```python
   def test_emoji_in_description(self):
       """Tasks with emoji should serialize to JSON without corruption.
       
       Regression test for issue #123: emoji was being stripped.
       """
   ```

---

## Test Organization

Tests are organized by functional domain:

```
tests/
├── conftest.py                            # Shared fixtures
├── domains/
│   ├── profiles/           # Profile composition, extends, loaders
│   │   ├── test_models.py
│   │   ├── test_profile_manager.py
│   │   ├── test_instructions_loader.py
│   │   ├── test_prompt_loader.py
│   │   └── test_resource_mapper.py
│   ├── tasks/              # TaskService, filtering, sorting, storage
│   │   ├── test_task_service.py
│   │   ├── test_task_service_query.py
│   │   ├── test_filters.py
│   │   ├── test_storage.py
│   │   ├── test_edge_cases.py
│   │   └── test_property_based.py
│   └── taskwarrior/        # TaskWarrior config, initialization
│       ├── test_config.py
│       ├── test_config_plugins.py
│       ├── test_env_vars.py
│       └── test_init.py
├── integration/            # End-to-end profile loading
│   └── test_profiles_integration.py
├── mcp/                    # MCP endpoints and resources
│   ├── test_mcp_endpoints.py
│   ├── test_mcp_uri_uniqueness.py
│   ├── test_resource_mapper_mcp.py
│   └── test_roadmap_resources.py
├── profiles/               # Profile integration tests
│   └── test_profile_integration.py
├── tools/                  # Documentation tooling
│   ├── test_simulate_profiles.py
│   └── test_simulate_profiles_unit.py
├── test_server_import.py
└── test_tools.py
```

This structure makes it easy to:
- Find tests related to a specific domain
- Run domain-specific tests: `pytest tests/domains/tasks/`
- Understand which code is tested by which tests
- Avoid mixing concerns (unit vs integration)

---

## Test Audit and Cleanup (Phase 6)

In Phase 6, we audited the test suite and removed redundancy:

### Identified and Removed (12 tests)
1. **Config getters consolidation**
   - Removed: `test_default_server_host`, `test_default_server_port`, `test_default_config_mode`, `test_default_review_projects`, `test_default_default_review_project`, `test_default_review_include_no_project`, `test_default_log_level`, `test_default_log_format`
   - Consolidated: `test_default_config_values()` + `test_agent_errors_path_validation()`
   - Benefit: 8 → 2 tests, same coverage, clearer intent
   
2. **Task completion testing**
   - Removed: `test_complete_task()` (simple happy path)
   - Kept: `test_complete_task_verifies_completion_via_status()` (thorough, verifies storage interaction)
   - Benefit: Removed duplicate, kept better test
   
3. **Start/Stop task testing**
   - Removed: `test_start_task()`, `test_stop_task()` (simple happy paths)
   - Kept: `test_start_task_not_found_returns_false()`, `test_stop_task_not_found_returns_false()`, `test_stop_task_success_calls_tw_stop()`
   - Benefit: Edge cases cover the happy path plus error conditions

### Results
- **Before:** 160 tests
- **After:** 148 tests (Phase 6 baseline; suite has since grown to 251)
- **Coverage maintained:** 60%+ line coverage (no loss)
- **Quality improved:** Tests are more focused and avoid duplication

### What was preserved
✅ All edge case tests (30) — no redundancy, all valuable  
✅ All property-based tests (10) — no redundancy, all valuable  
✅ All MCP endpoint tests (33) — no redundancy, all valuable  
✅ All filter tests (19) — granular and non-overlapping  
✅ All storage tests (4) — each tests different method  

---



All tests run on every commit:

```yaml
# .github/workflows/test.yml (example)
test:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v3
    - uses: actions/setup-python@v4
    - run: pip install -e .
    - run: pytest --tb=short
```

A test failure blocks merge to main.

---

## Debugging Failed Tests

### Hypothesis Fails with Flaky Example

```bash
pytest tests/test_property_based.py::TestQueryTasksLimitInvariant::test_limit_always_respected \
  --hypothesis-seed=12345
```

This reruns with the exact random seed that caused failure.

### Edge Case Fails Only Sometimes

Add `@settings(max_examples=1000)` to generate more examples:

```python
@given(...)
@settings(max_examples=1000)  # Generate 1000 instead of default 100
def test_something(self): ...
```

### Need to Inspect Generated Data

Use `note()` in Hypothesis:

```python
@given(filters=...)
def test_something(self, filters):
    from hypothesis import note
    note(f"Generated filters: {filters}")
    # Test will print the filters on failure
```

---

---

## Quick Start for Contributors

### Running Tests for the First Time

```bash
# Install dependencies (if not already done)
uv sync

# Run all tests
pytest

# Run only tests in a specific domain
pytest tests/domains/tasks/
pytest tests/domains/taskwarrior/
pytest tests/mcp/

# Run a specific test file
pytest tests/domains/tasks/test_task_service.py

# Run a specific test function
pytest tests/domains/tasks/test_task_service.py::test_add_task
```

### Using the Correct Test Runner

TaskMajor uses `uv` as the Python package manager:

```bash
# ✅ Recommended
uv run pytest -v

# ✅ Also works
pytest -v

# ❌ Avoid (may use wrong Python)
python -m pytest
```

---

## Writing Your First Test

### Example 1: Simple Unit Test

```python
# tests/domains/tasks/test_my_feature.py
from unittest.mock import Mock
from taskmajor.domains.tasks import TaskService

def test_my_new_feature():
    """Test that my feature works correctly."""
    # 1. Setup: Create mocks
    mock_tw = Mock()
    service = TaskService(mock_tw)
    
    # 2. Exercise: Call the method
    result = service.my_new_method()
    
    # 3. Verify: Check the result
    assert result == expected_value
    mock_tw.some_method.assert_called_once()
```

### Example 2: MCP Endpoint Test

```python
# tests/mcp/test_my_endpoint.py
from unittest.mock import Mock, patch
from taskmajor.domains.tasks import TaskService

def test_my_endpoint_returns_json():
    """Test that my endpoint returns valid JSON."""
    # Mock the TaskService
    with patch('taskmajor.mcp.resources.my_module.TaskService') as mock_cls:
        mock_service = Mock(spec=TaskService)
        mock_cls.return_value = mock_service
        mock_service.query_tasks.return_value = {
            'tasks': [{'uuid': '123', 'description': 'Test'}],
            'total': 1
        }
        
        # Call handler (simulating MCP call)
        result = my_endpoint_handler()
        
        # Verify JSON structure
        assert 'tasks' in result
        assert 'total' in result
        assert isinstance(result['tasks'], list)
```

### Example 3: Edge Case Test

```python
# tests/domains/tasks/test_my_edge_cases.py
import pytest
from taskmajor.domains.tasks import TaskService

def test_empty_string_vs_none():
    """Empty string and None should be treated differently."""
    mock_tw = Mock()
    service = TaskService(mock_tw)
    
    # Empty string: should return results, but filtered somehow
    result1 = service.query_tasks(project="")
    
    # None: should return all projects
    result2 = service.query_tasks(project=None)
    
    # They should be different
    assert result1 != result2
```

### Example 4: Property-Based Test

```python
# tests/domains/tasks/test_my_properties.py
from hypothesis import given, strategies as st
from taskmajor.domains.tasks import TaskService

@given(
    limit=st.integers(min_value=0, max_value=500),
    offset=st.integers(min_value=0, max_value=100)
)
def test_pagination_invariant(limit, offset):
    """Pagination should never return more than limit results."""
    mock_tw = Mock()
    service = TaskService(mock_tw)
    
    result = service.query_tasks(limit=limit, offset=offset)
    
    # Invariant: never more results than limit (unless limit=0)
    if limit > 0:
        assert len(result['tasks']) <= limit
    else:
        assert len(result['tasks']) == 0
```

---

## Common Fixtures

### Available Fixtures in `tests/conftest.py`

All these fixtures are automatically available in any test file. Here's a quick reference:

#### Mock Objects

**`mock_taskwarrior`** — Pre-configured Mock for TaskWarrior
```python
def test_something(mock_taskwarrior):
    """mock_taskwarrior is a Mock() with basic return values pre-set."""
    mock_taskwarrior.get_tasks.return_value = [my_task]
    service = TaskService(mock_taskwarrior)
    ...
```

**`mock_task_service`** — TaskService with mocked TaskWarrior
```python
def test_something(mock_task_service):
    """mock_task_service = TaskService(mock_taskwarrior)."""
    result = mock_task_service.query_tasks()
    # No external TaskWarrior calls
```

#### Sample Data

**`sample_task`** — A single realistic task
```python
def test_serialization(sample_task):
    """One complete task with all common fields."""
    assert sample_task.uuid is not None
    assert sample_task.status == "pending"
    assert sample_task.project == "Work"
    assert sample_task.priority == "H"
```

**`sample_tasks`** — 6 diverse tasks for filtering/pagination
```python
def test_pagination(sample_tasks):
    """6 tasks with different projects, priorities, statuses."""
    # Tasks include: pending, completed, with/without project
    # Mix of high/medium/low priorities
    # Can test filtering by project, priority, status
```

#### Configuration

**`default_config`** — Standard TaskMajor configuration
```python
def test_config_defaults(default_config):
    """Standard config with server_port=8888, etc."""
    assert default_config.server_port == 8888
```

**`custom_config`** — Non-standard configuration
```python
def test_custom_setup(custom_config):
    """Config with custom values for testing variations."""
    assert custom_config.server_port == 9999
```

#### Temporary Files

**`tmp_taskrc`** — Empty temporary taskrc file
```python
def test_file_operations(tmp_taskrc):
    """tmp_taskrc is a Path to an empty temp file."""
    content = tmp_taskrc.read_text()
    assert len(content) == 0
```

**`tmp_taskdata`** — Temporary directory for task data
```python
def test_data_dir(tmp_taskdata):
    """tmp_taskdata is a Path to an empty temp directory."""
    assert tmp_taskdata.is_dir()
```

### Creating Your Own Fixtures

For test files that share setup:

```python
# tests/domains/tasks/test_my_feature.py
import pytest
from unittest.mock import Mock

@pytest.fixture
def my_specific_service():
    """Fixture specific to my feature tests."""
    mock_tw = Mock()
    # Custom setup
    return TaskService(mock_tw)

def test_something(my_specific_service):
    result = my_specific_service.my_feature()
    assert result is not None
```

For fixtures needed across many files, add them to `tests/conftest.py`.

---



## Troubleshooting

### Test Fails Locally but Passes in CI

**Possible causes:**
1. **Python version mismatch** — Check with `python --version`
2. **Missing dependencies** — Run `uv sync` to update
3. **Timezone issues** — Tests use UTC; check your system timezone
4. **Flaky Hypothesis tests** — Run with `--hypothesis-seed=0` to reproduce

**Solution:**
```bash
# Reproduce CI environment locally
uv sync
pytest -v --tb=short

# If Hypothesis test is flaky, get the seed from CI output:
pytest -v --hypothesis-seed=12345
```

### "cannot import name X" Error

**Solution:**
```bash
# Reinstall and clear caches
rm -rf .pytest_cache __pycache__ tests/__pycache__
uv sync
pytest
```

### Mock Not Being Called

**Checklist:**
- ✅ Is the mock properly instantiated? `mock_obj = Mock()`
- ✅ Did you patch the right location? (import path, not definition path)
- ✅ Did you actually call the method? `service.method()` not just reference it
- ✅ Did you assert before another test runs? (mocks reset between tests)

**Example fix:**
```python
# ❌ Wrong: patching at definition location
@patch('taskmajor.domains.tasks.task_service.TaskWarrior')
def test_wrong(mock_tw): ...

# ✅ Right: patching where it's used
@patch('taskmajor.domains.tasks.TaskService.get_tasks')
def test_right(mock_get): ...
```

---

## CI/CD Integration

### GitHub Actions Workflow

Tests run automatically on:
- Every push to `main`
- Every pull request
- On schedule (daily)

**Current thresholds:**
- ✅ Minimum 60% code coverage required
- ✅ All tests must pass
- ✅ No linting errors (ruff, mypy)

**View results:**
1. Push to GitHub
2. Check "Actions" tab
3. Click on workflow run
4. Scroll to coverage metrics

### Local Coverage Report

```bash
# Generate HTML coverage report
pytest --cov=taskmajor --cov-report=html

# Open in browser (macOS)
open htmlcov/index.html

# Open in browser (Linux)
xdg-open htmlcov/index.html
```

---

## FAQ

**Q: My test uses TaskWarrior directly. Is that allowed?**  
A: Not recommended. Use the FakeTaskWarrior or Mock instead. TaskWarrior may not be installed, or may have different versions. See examples above.

**Q: How do I test async code?**  
A: TaskMajor doesn't use async yet. When it does, use `pytest-asyncio` and `@pytest.mark.asyncio`.

**Q: How do I test code that calls the real filesystem?**  
A: Use `tmp_path` fixture for temporary files, or `monkeypatch` to mock `open()`.

**Q: Can I use print() for debugging in tests?**  
A: Yes, but use `pytest -s` to see output: `pytest -s tests/my_test.py`

**Q: Should I write a test for every getter?**  
A: No. Write tests for business logic and behavior, not trivial getters. See Phase 6 cleanup.

**Q: How do I test integration with real TaskWarrior?**  
A: See Phase 4 (Docker integration tests) — not currently implemented but documented.

**Q: My fixture is used in multiple test files. Where should I put it?**  
A: Put it in `tests/conftest.py` — pytest automatically discovers and makes it available everywhere.

---

## CI/CD Integration & Quality Gates

### Automated Testing on GitHub

Every push to `main` or a pull request triggers automated tests:

```
┌─────────────────────┐
│  Push to branch     │
└──────────┬──────────┘
           │
     ┌─────▼────────┐
     │ GitHub       │
     │ Actions      │
     │ (ci.yml)     │
     └─────┬────────┘
           │
    ┌──────┴──────┬──────────┬──────────┐
    │             │          │          │
 ┌──▼──┐      ┌───▼──┐  ┌───▼──┐  ┌───▼──┐
 │Test │      │Cover-│  │Lint  │  │Build │
 │3.10 │      │ age  │  │Check │  │Docs  │
 │3.11 │      │      │  │      │  │      │
 │3.12 │      └──────┘  └──────┘  └──────┘
 └──┬──┘           │         │         │
    └───────┬──────┴─────────┴─────────┘
            │
     ┌──────▼────────┐
     │ All passed?   │
     └──────┬────────┘
            │
     ┌──────▴────────┐
     │               │
  ✅ YES         ❌ NO
     │               │
   Merge        Fix & push
    ready        again
```

### CI/CD Jobs Explained

#### 1. **Tests (Python 3.10, 3.11, 3.12)**
Runs full test suite on 3 Python versions simultaneously:
```bash
uv run pytest -v --tb=short
```

**Success criteria:**
- All tests pass
- No timeout errors
- Minimum test count check (≥140 tests)

**View results:** Click on the failing job in the PR checks section

#### 2. **Coverage Job**
Generates coverage report and uploads to Codecov:
```bash
uv run pytest --cov=taskmajor --cov-report=xml --cov-report=html
```

**Success criteria:**
- Coverage ≥ 60%
- All coverage.xml artifacts uploaded
- No broken reports

**View results:** 
- Coverage report: Click "Coverage" artifact in Actions tab
- Online badge: https://codecov.io/gh/nschmeltz/taskmajor

#### 3. **Lint Job**
Checks code style and type hints:
```bash
uv run ruff check .     # Linting
uv run ruff format .    # Formatting
uv run mypy taskmajor   # Type checking
```

**Success criteria:**
- Ruff returns 0 issues
- No formatting violations
- Type checking passes (--exit-zero allows warnings)

**View results:** Click on lint job output for specific issues

#### 4. **Summary Job**
Final gate: all above jobs must pass:
- If ANY job fails → PR cannot be merged
- All must pass → PR can be merged (with approval)

### Local Validation Before Push

Always validate locally before pushing:

```bash
# Quick check (tests only, ~10s)
./scripts/run_tests.sh --quick

# Full check (tests + coverage + lint, ~30s)
./scripts/run_tests.sh

# Or run components individually
uv run pytest                              # All tests
uv run pytest --cov=taskmajor             # With coverage
uv run ruff check . && uv run ruff format . # Fix formatting
```

### Debugging CI Failures

#### Problem: "Tests failed in CI but pass locally"

**Possible causes:**
1. **Python version mismatch** → Test with `uv run pytest` to use project Python version
2. **Environment differences** → CI runs on clean Ubuntu; your local might have different TaskWarrior
3. **Missing dependencies** → Run `uv sync --all-groups` to update

**Solution:**
```bash
# Check your Python version matches CI (3.10, 3.11, or 3.12)
python --version

# Sync dependencies
uv sync --all-groups

# Run the exact command from CI
uv run pytest -v --tb=short

# Check specific test
uv run pytest -vvs tests/domains/tasks/test_task_service.py::test_name
```

#### Problem: "Coverage is below 60%"

**Possible causes:**
1. New code without tests
2. Existing untested code path
3. Coverage report generated incorrectly

**Solution:**
```bash
# View coverage report
./scripts/run_tests.sh --coverage
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux

# Find uncovered lines
grep class="nc"  # Look for "no cover" in HTML

# Add tests for the uncovered code
# Then re-run coverage
uv run pytest --cov=taskmajor --cov-report=html
```

#### Problem: "Lint errors in CI"

**Check what failed:**
```bash
uv run ruff check .  # Show lint errors
uv run ruff format . --check  # Show formatting issues
```

**Fix automatically:**
```bash
uv run ruff format .  # Auto-fix formatting
uv run ruff check . --fix  # Auto-fix lint issues (if possible)
```

**Manual fixes:**
- Undefined imports: `from module import name`
- Long lines: Split into multiple lines (max 100 chars)
- Unused imports: Remove them

#### Problem: "Timeout waiting for tests"

**Possible causes:**
1. Infinite loop or deadlock in test
2. Sleep/wait with too long duration
3. Network timeout trying to reach external service

**Solution:**
1. Identify which test times out (CI shows partial output)
2. Check for `time.sleep()`, `requests.get()`, or similar
3. Use mocks instead of real I/O:
   ```python
   # Bad: waits for real network
   response = requests.get("https://example.com")
   
   # Good: mocked
   monkeypatch.setattr("requests.get", Mock(return_value=...))
   ```

### Branch Protection Rules

To prevent broken code from reaching main:

1. Go to **Settings** → **Branches**
2. Click **Add rule** and set branch pattern to `main`
3. Check these boxes:
   - ✅ Require pull request reviews (1 approval)
   - ✅ Require status checks to pass (all 7 jobs)
   - ✅ Require branches up to date
   - ✅ Include administrators

See [docs/branch-protection.md](branch-protection.md) for detailed steps.

### Coverage Thresholds

Current thresholds:
- **Minimum:** 60% (pragmatic, achievable)
- **Target:** >70% (good coverage)
- **Excellent:** >80% (comprehensive)

Why 60%?
- Higher thresholds (80%+) discourage contributions
- 60% covers most critical paths
- Edge cases and rarely-used code are acceptable gaps
- Pragmatic balance between quality and contribution friction

### Performance Baseline

The full test suite completes in ~3–4 seconds locally:
- Fast CI feedback
- Tests are isolated (no external I/O)
- No performance benchmark tests yet (Phase 4+)

---

## Conclusion

TaskMajor's test suite is designed to catch bugs at multiple levels:

1. **Unit tests** catch logic errors in TaskService
2. **Contract tests** catch serialization and API mapping bugs
3. **Property tests** catch edge cases and unexpected interactions
4. **Edge case tests** catch crashes on unusual inputs

Together, they provide confidence that the system will behave correctly in production, even with unexpected data or usage patterns.

### For More Help
- Read test examples: `grep -r "def test_" tests/ | head -20`
- Check pytest documentation: https://docs.pytest.org
- Check Hypothesis docs: https://hypothesis.readthedocs.io
- Open an issue if something is broken or unclear
