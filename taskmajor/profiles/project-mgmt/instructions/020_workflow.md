# Workflow

## Capture
Same as Standard.

## Triage (Enhanced)
When triaging a task:
1. **Assign Owner**: Who is responsible? (Use `owner` UDA).
2. **Estimate**: How much effort? (Use `estimate` UDA in hours or story points).
3. **Sprint**: Which sprint does this belong to? (Use `sprint` UDA).
4. **Dependencies**: Does this block or depend on another task? (Use `depends` field).

## Monitor
- Check `taskmajor://queue/blockers` for blocked tasks.
- Check `taskmajor://analytics/effort` to see total effort per project.
- Use `taskmajor://roadmap/sprint` to view sprint progress.
