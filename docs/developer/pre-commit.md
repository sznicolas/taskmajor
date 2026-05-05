# Pre-commit Hooks Setup for TaskMajor

Pre-commit hooks automatically catch and fix code issues **before you commit**, preventing CI failures and speeding up PR reviews.

## Why Use Pre-commit Hooks?

### Without hooks:
1. You write code with style/lint issues
2. You commit and push to GitHub
3. CI runs and fails (takes 2-3 minutes)
4. You have to fix issues and push again
5. Repeat cycle

### With hooks:
1. You write code
2. You run `git commit`
3. Pre-commit hooks run automatically
4. Issues are auto-fixed or you fix them
5. You commit only clean code
6. CI passes first time ✅

## Installation

### Step 1: Install pre-commit (one-time)

```bash
# Using pip
pip install pre-commit

# Or using your favorite package manager
brew install pre-commit      # macOS
apt install pre-commit       # Ubuntu/Debian
```

### Step 2: Install hooks in repository

```bash
cd /path/to/taskmajor
pre-commit install
```

This creates a `.git/hooks/pre-commit` file that runs before each commit.

### Step 3: (Optional) Verify installation

```bash
pre-commit --version
pre-commit run --all-files  # Run hooks on all files to check everything
```

## How to Use

### Typical workflow:

```bash
# Make changes
nano taskmajor/domains/tasks/service.py

# Stage changes
git add taskmajor/

# Commit (hooks run automatically)
git commit -m "Add new filtering feature"

# Output:
# trim trailing whitespace...........................Passed
# fix end of file fixer.............................Passed
# check yaml..........................................Passed
# ruff.................................................Passed
# ruff-format.........................................Passed
# mypy.................................................Passed

# ✅ Commit successful!
```

### If hooks find issues:

1. **Auto-fixable issues** (formatting, trailing whitespace):
   - Hooks automatically fix them
   - You must `git add` the fixed files again
   - Then `git commit` again

   ```bash
   git commit -m "Fix formatting"
   # Output:
   # trim trailing whitespace...........................Fixed
   # ❌ FAILED: Some hooks changed files
   #
   # Git diff:
   #   - extra trailing whitespace
   #   + (removed)
   
   git add .
   git commit -m "Fix formatting"  # This time it passes
   ```

2. **Manual-fix issues** (logic errors, type issues):
   - Hooks show you the problem
   - You manually fix the code
   - Then `git add` and `git commit` again

   ```bash
   git commit -m "Add function"
   # Output:
   # mypy.................................................Failed
   # taskmajor/domains/tasks/service.py:42: error: Argument 1 has 
   # incompatible type "int"; expected "str"
   
   # Fix the issue in your editor
   nano taskmajor/domains/tasks/service.py
   
   git add taskmajor/domains/tasks/service.py
   git commit -m "Add function"  # Now it passes
   ```

## What Hooks Run?

### 1. **Trailing Whitespace**
Removes spaces at end of lines (messy, causes diffs)

### 2. **End-of-file Fixer**
Ensures files end with a newline (POSIX standard)

### 3. **YAML/JSON Validation**
Checks `.yml`, `.yaml`, `.json` files are valid (prevents CI config errors)

### 4. **Merge Conflict Checker**
Catches unresolved merge conflicts (prevents accidental broken merges)

### 5. **Ruff Formatter & Linter**
Auto-formats code to consistent style:
```python
# Before
x=1
def  foo( ):pass

# After (automatically fixed)
x = 1
def foo():
    pass
```

### 6. **mypy Type Checker**
Catches type errors:
```python
def add(x: int, y: int) -> int:
    return x + y

add(1, "2")  # ❌ mypy catches this before you commit
```

### 7. **Markdown Linter**
Checks markdown formatting (README.md, TESTING.md, etc.)

### 8. **Secrets Detection**
Prevents accidentally committing API keys, passwords, tokens

## Skip Hooks (When Necessary)

If you absolutely must skip hooks for a commit:

```bash
git commit --no-verify -m "Skip hooks (not recommended)"
```

⚠️ **Use sparingly!** This bypasses all quality checks.

## Update Hooks

Hooks automatically update weekly via GitHub Actions (see `.pre-commit-config.yaml`).

To manually update:

```bash
pre-commit autoupdate
git add .pre-commit-config.yaml
git commit -m "chore(pre-commit): update hooks"
```

## Troubleshooting

### Problem: "pre-commit not found" error

**Solution:** Install pre-commit:
```bash
pip install --upgrade pre-commit
pre-commit install
```

### Problem: "Hooks keep modifying files"

**Cause:** Formatting hooks are auto-fixing style issues.

**Solution:** Run once to auto-fix everything:
```bash
pre-commit run --all-files
git add .
git commit -m "chore: auto-fix code style"
```

Then all future commits will pass immediately.

### Problem: "mypy keeps failing on valid code"

**Solution:** Add type hints or ignore annotations:

```python
# Option 1: Add type hints
def my_func(x: int) -> int:
    return x * 2

# Option 2: Ignore specific error
result = some_function()  # type: ignore[call-arg]

# Option 3: Skip file
# taskmajor/legacy_module.py  # mypy: ignore
```

### Problem: "I want to skip a specific hook"

Edit `.pre-commit-config.yaml`:

```yaml
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.13
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
        stages: [commit]  # Skip in push stage, only commit
```

## Integration with Your Workflow

### Local development:
1. Pre-commit hooks catch issues before you push
2. You see failures immediately (not after 3min CI wait)
3. You can iterate fast on formatting

### Before opening PR:
Run one final check:
```bash
pre-commit run --all-files
./scripts/run_tests.sh
git push
```

### In CI:
GitHub Actions still runs all checks (as backup)

## See Also

- [Pre-commit documentation](https://pre-commit.com)
- [Ruff documentation](https://docs.astral.sh/ruff)
- [mypy documentation](https://mypy.readthedocs.io)
- [Contributing guide](contributing.md)
- [Testing guide](testing.md)
