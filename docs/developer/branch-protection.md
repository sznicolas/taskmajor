# GitHub Branch Protection Rules for TaskMajor

## Configuration for `main` branch

### Rule Details

**Branch name pattern:** `main`

### Protection Rules

#### 1. Require Pull Request Reviews
- **Dismissal restrictions:** None
- **Require code review:** Yes
- **Require approvals:** 1
- **Dismiss stale pull request approvals:** Yes
- **Require review from code owners:** No
- **Require last push approval:** No

#### 2. Require Status Checks
All of the following must pass before merging:
- ✅ `test (3.10)`
- ✅ `test (3.11)`
- ✅ `test (3.12)`
- ✅ `coverage`
- ✅ `lint`
- ✅ `summary`

**Require branches to be up to date:** Yes
**Require status checks to pass:** Yes

#### 3. Require Dismissal of Pull Request Reviews
- **Require code review:** Yes
- **Require last push approval:** No
- **Dismiss stale reviews:** Yes

#### 4. Restrict Who Can Push
- **Allowed users/teams:** None (all team members can push)

#### 5. Additional Settings
- **Require signed commits:** No (optional)
- **Require conversation resolution:** No
- **Include administrators:** Yes (admins must follow rules too)

## How to Configure in GitHub UI

1. Go to repository → **Settings**
2. Click **Branches** in left sidebar
3. Under "Branch protection rules", click **Add rule**
4. Enter `main` in "Branch name pattern"
5. Check these options:
   - ✅ Require a pull request before merging
   - ✅ Require approvals (set to 1)
   - ✅ Dismiss stale pull request approvals
   - ✅ Require status checks to pass before merging
   - ✅ Require branches to be up to date before merging
   - ✅ Include administrators
6. Search for and select these status checks:
   - test (3.10)
   - test (3.11)
   - test (3.12)
   - coverage
   - lint
   - summary
7. Click **Create**

## Why These Rules?

### Require Pull Request Reviews
- Ensures at least one other developer reviews changes
- Prevents direct pushing to main
- Encourages discussion and knowledge sharing

### Require Status Checks
- **Python 3.10, 3.11, 3.12:** Ensures compatibility across versions
- **coverage:** Prevents coverage from dropping below 60%
- **lint:** Catches style/formatting issues automatically
- **summary:** Ensures all checks passed

### Require Branches Up to Date
- Prevents merge conflicts
- Ensures code works with latest main branch
- Protects against race conditions

## Enforcement for Contributors

### Before Opening PR:
```bash
# Run local validation
./scripts/run_tests.sh

# Fix any issues
uv run ruff format .    # Auto-fix formatting
uv run pytest          # Run all tests
```

### After Opening PR:
1. Wait for CI to run (takes ~2-3 minutes)
2. If any check fails, click on it for details
3. Fix issues locally and push again
4. Once all checks pass, request review from team
5. After review approval, your PR can be merged

## CI Status Badges

Add to README.md:
```markdown
[![CI Status](https://github.com/[owner]/[repo]/workflows/CI/badge.svg)](https://github.com/[owner]/[repo]/actions)
[![Coverage Status](https://codecov.io/gh/[owner]/[repo]/branch/main/graph/badge.svg)](https://codecov.io/gh/[owner]/[repo])
```

## Troubleshooting

### "CI build failed" error
1. Click on the failing check for details
2. Common issues:
   - Tests don't pass → Run `pytest` locally to see errors
   - Coverage dropped → Write more tests
   - Lint errors → Run `uv run ruff check . --fix`

### "Changes need to be reviewed"
1. Request review from a team member
2. Address any feedback they provide
3. They will approve once satisfied

### "This branch is out of date"
1. Click "Update branch" to merge main into your PR
2. Or locally: `git pull origin main && git push`

## See Also

- [TESTING.md](testing.md) — How to write and run tests
- [contributing.md](contributing.md) — Contributing guidelines
- [CI Workflow](https://github.com/yourusername/taskmajor/issues) — Detailed CI configuration
