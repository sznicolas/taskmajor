# Sprint Planning

Help the user plan the next sprint.

## Steps
1. Check `taskmajor://queue/unsorted` for new candidates.
2. Check `taskmajor://analytics/summary` for current capacity.
3. Select tasks for the sprint.
4. Assign `sprint` UDA and `estimate` to selected tasks.
5. Ensure dependencies are resolved.

## Output Format
🚀 Sprint Planning — {sprint_name}

📋 CANDIDATES
• {description} (Estimate: {estimate})

✅ SELECTED FOR SPRINT
• {description} (Owner: {owner})

⚠️ BLOCKERS
• {description} depends on {blocked_by}

💡 CAPACITY
Total Estimate: {total_hours} hours
