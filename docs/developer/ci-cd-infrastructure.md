# TaskMajor CI/CD Infrastructure

This document provides a comprehensive overview of TaskMajor's continuous integration and deployment setup.

## Overview

```
Developer        →  Git Push  →  GitHub   →  GitHub Actions  →  Codecov
  (local)                        Actions       (automated)        (coverage)
                                   ↓
                            Run 7 Jobs in Parallel
                                   ↓
                  ┌─────┬────────┬──────┬────┬────┬────┐
                  │     │        │      │    │    │    │
               Test  Test  Test  Cover  Lint Type Build
               3.10  3.11  3.12  -age   Check Check Sum
                  │     │        │      │    │    │    │
                  └─────┴────────┴──────┴────┴────┴────┘
                              ↓
                        All Passed?
                          │    │
                       YES│    │NO
                          ↓    ↓
                    ✅ Merge  ❌ Fix &
                    Ready    Retry
```

## Files Overview

### `.github/workflows/ci.yml` (139 lines)

**Purpose:** GitHub Actions workflow definition  
**Trigger:** Push to `main`/`develop`, all PRs  
**Concurrency:** Cancels previous runs on same branch (fast feedback)

**Jobs:**
1. **test** (3 parallel runs for Python 3.10, 3.11, 3.12)
   - Installs dependencies with `uv sync --all-groups`
   - Runs `pytest -v --tb=short`
   - Validates minimum 140 tests collected
   - Runtime: ~60 seconds

2. **coverage** (depends on test)
   - Generates XML and HTML coverage reports
   - Uploads to Codecov (auto-comments on PRs)
   - Checks minimum 60% coverage
   - Archives HTML report for 7 days
   - Runtime: ~60 seconds

3. **lint** (independent)
   - Ruff linter: `ruff check .`
   - Ruff formatter: `ruff format . --check`
   - mypy type checker: `mypy taskmajor`
   - Exit codes suppressed (warnings OK)
   - Runtime: ~30 seconds

4. **summary** (depends on all above)
   - Gate keeper: fails if ANY job failed
   - Prevents accidental merges with failures
   - Runtime: ~5 seconds

### `.codecov.yml` (23 lines)

**Purpose:** Codecov configuration  
**Behavior:**
- Precision: 2 decimal places (61.25%, not 61.2542%)
- Range: 60-100% (reports if coverage in this range)
- Comment: Auto-comments on PRs with coverage delta
- Ignore: Tests, docs, scripts directories

### `scripts/run_tests.sh` (192 lines)

**Purpose:** Local validation script for developers  
**Provides:**
- `--quick`: Tests only (~10 seconds)
- `--coverage`: Tests + coverage report (~20 seconds)
- `--lint`: Tests + linting (~30 seconds)
- Default: All checks with colored output

**Features:**
- Colored output (✅, ❌, ⚠️)
- Coverage threshold check (>60%)
- Test count validation (>140)
- Execution time reporting
- Coverage report path displayed

### `.pre-commit-config.yaml` (60 lines)

**Purpose:** Local pre-commit hooks  
**Runs:** Before each commit automatically  
**Checks:**
- Trailing whitespace
- File endings
- YAML/JSON syntax
- Merge conflicts
- Ruff format + lint
- mypy type checking
- Markdown linting
- Secrets detection

**CI Integration:** Auto-updates hooks weekly, optionally auto-fixes on pushes

### `docs/branch-protection.md` (136 lines)

**Purpose:** GitHub UI setup guide for branch protection rules  
**Configures:**
- Require 1 PR review approval
- Require all 7 CI jobs to pass
- Require branches up to date before merge
- Include administrators

## Workflow in Action

### A typical PR workflow:

```
1. Developer branches off main
   git checkout -b feature/new-feature

2. Installs pre-commit hooks (if not done)
   pre-commit install

3. Makes changes
   nano taskmajor/domains/tasks/service.py

4. Pre-commit runs automatically on commit
   git commit -m "Add new feature"
   → Ruff formats code
   → mypy checks types
   → If issues, fixes them and you re-add+commit

5. Pushes to fork
   git push origin feature/new-feature

6. Opens PR on GitHub

7. GitHub Actions automatically runs:
   → 3 test jobs (all Python versions in parallel)
   → 1 coverage job (waits for tests)
   → 1 lint job (independent)
   → 1 summary job (waits for all above)

8. PR status shows results:
   ✅ All checks pass  OR  ❌ Some check failed

9. If failed, developer:
   → Checks detailed job logs
   → Makes fixes locally
   → Runs ./scripts/run_tests.sh to validate
   → Pushes fixes (CI re-runs automatically)

10. Once all pass:
    → Team member reviews PR
    → Comments/approves
    → Merges (branch protection ensures all checks passed)

11. Post-merge:
    → Codecov updates coverage trend
    → Badge on README reflects new coverage %
    → CI continues to run on main for monitoring
```

## Performance Characteristics

| Component | Time | Notes |
|-----------|------|-------|
| Local unit tests | 2.6s | No I/O, mocked services |
| Local coverage | 3.2s | Includes coverage instrumentation |
| Local lint | 1.2s | Ruff (very fast) |
| GitHub Actions (tests) | 60s | Setup + run on Ubuntu |
| GitHub Actions (coverage) | 60s | Includes Codecov upload |
| GitHub Actions (lint) | 30s | Parallel with tests |
| **Total CI time** | **60s** | Jobs run in parallel |

## Coverage Strategy

### Current thresholds:
- **Minimum:** 60% (enforced by CI)
- **Target:** >70% (good, well-tested)
- **Excellent:** >80% (comprehensive)
- **Current:** 61% (well-balanced)

### Coverage by domain:

```
taskmajor/domains/tasks/     89%  ✅ Well-tested
taskmajor/domains/taskwarrior/  74%  ✅ Mostly tested
taskmajor/mcp/               35%  ⚠️  Lightly tested (async/decorator complexity)
taskmajor/bootstrap/          100% ✅ Fully tested
```

### Why 60% minimum?

1. **Achievable** - Doesn't discourage contributions
2. **Covers critical paths** - Business logic well-tested
3. **Pragmatic** - Avoids perfectionism paralysis
4. **Flexible** - Can increase as project matures
5. **Realistic** - Acknowledges that some code (MCP layer) is hard to test in isolation

## Branch Protection Rules

To prevent broken code from merging:

1. **Require PR reviews** — At least 1 person reviews the code
2. **Require status checks** — All 7 GitHub Actions jobs must pass
3. **Require up to date** — PR must be synced with main (no stale PRs)
4. **Include admins** — Rules apply to everyone, including maintainers

See [branch-protection.md](branch-protection.md) for setup steps.

## Debugging CI Failures

### Problem: "Tests failed in CI but pass locally"

**Checklist:**
- [ ] Using same Python version? (CI uses 3.10, 3.11, 3.12)
- [ ] Ran `uv sync --all-groups`? (May be missing dev dependencies)
- [ ] Environment-specific code? (Check for hardcoded paths, TaskWarrior version differences)
- [ ] Flaky test? (Try running 3 times: `pytest tests/my_test.py` × 3)

**Solution:**
```bash
python --version                    # Check version
uv sync --all-groups               # Update deps
uv run pytest -v --tb=short        # Run exact CI command locally
```

### Problem: "Coverage dropped below 60%"

**Solution:**
```bash
# Generate report
./scripts/run_tests.sh --coverage

# Find uncovered lines
open htmlcov/index.html

# Add tests for those lines
nano tests/domains/tasks/test_my_module.py

# Verify coverage restored
./scripts/run_tests.sh --coverage
```

### Problem: "Linting failed in CI"

**Solution:**
```bash
uv run ruff check . --fix    # Auto-fix lint errors
uv run ruff format .         # Auto-format code
git add .
git commit -m "chore: fix linting"
git push
```

### Problem: "Codecov upload failed (but CI passed)"

**Note:** Codecov failures don't block merges (non-blocking job).  
This is intentional—network issues shouldn't block valid PRs.

## Secrets & Security

TaskMajor CI doesn't require secrets:
- ✅ No API keys
- ✅ No database credentials
- ✅ No deployment tokens

All CI jobs use public GitHub runners with no special access.

## Extending CI/CD

### To add a new job:

1. Edit `.github/workflows/ci.yml`
2. Add new job with:
   - `name:` (displayed in PR checks)
   - `runs-on: ubuntu-latest`
   - `steps:` with actions
3. Add to `summary` job `needs:` list
4. Test locally: `act -j new-job-name` (requires [act](https://github.com/nektos/act))

### To change thresholds:

1. **Coverage:** Edit `.github/workflows/ci.yml` line ~70
2. **Test count:** Edit `.github/workflows/ci.yml` line ~43
3. **Python versions:** Edit matrix in `.github/workflows/ci.yml` line ~15

### To skip CI for a commit:

```bash
# Not recommended, but sometimes necessary
git push --no-verify

# Or use GitHub UI to skip workflow
# (Not recommended without good reason)
```

## Monitoring & Maintenance

### Weekly:
- [ ] Check Codecov trends (improving? declining?)
- [ ] Review test execution times (should be <90s)
- [ ] Monitor failed builds (any systemic issues?)

### Monthly:
- [ ] Update hooks: `pre-commit autoupdate`
- [ ] Review test coverage report
- [ ] Look for slow tests or flaky tests
- [ ] Clean up old workflow artifacts

### As needed:
- [ ] Update Python version support (3.10, 3.11, 3.12, etc.)
- [ ] Add new linting rules
- [ ] Adjust coverage thresholds based on project maturity

## See Also

- [TESTING.md](testing.md) — How to write tests
- [branch-protection.md](branch-protection.md) — GitHub UI setup
- [pre-commit.md](pre-commit.md) — Local hooks setup
- [contributing.md](contributing.md) — How to contribute
- [GitHub Actions docs](https://docs.github.com/en/actions)
- [Codecov docs](https://docs.codecov.io)
