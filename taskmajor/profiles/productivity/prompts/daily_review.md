# Daily Review

Quick review to define the day's focus.

## Steps
1. `query_tasks(filter="status:pending due.before:now", sort=["due"])` → Overdue tasks.
2. `query_tasks(filter="status:pending due.before:eod", sort=["priority"])` → Today's tasks.
3. `get_stats(filters={"project": "Inbox"})` → Count items to triage.
4. `next_task()` → Main recommendation.

## Output Format
📅 Daily Review — {date}

🔴 OVERDUE ({count})
• {description} (Project: {project})

📋 TODAY ({count})
• {time} — {description} [Appointment]
• {description} (Priority: {priority})

📥 INBOX ({count})
{count} items awaiting triage.

💡 NEXT ACTION: {description}
