# Weekly Review

Perform a comprehensive weekly review to plan the upcoming week.

## Steps
1. Count completed tasks from the last 7 days.
2. Check `taskmajor://agenda/week` for the next 7 days.
3. Find pending tasks without a due date (orphans).
4. Check `taskmajor://analytics/summary` for project status.

## Output Format
📊 Weekly Review — Week of {monday} to {sunday}

✅ COMPLETED ({count})
• {description}

�� WEEK AHEAD
Monday: {count} tasks
Tuesday: {count} tasks
...

⚠️ ORPHANS ({count})
• {description} (No due date)

📁 PROJECT STATUS
{project}: {count} pending

💡 RECOMMENDATIONS
- Schedule orphans.
- Clear inbox.
- Focus on high-priority items.
