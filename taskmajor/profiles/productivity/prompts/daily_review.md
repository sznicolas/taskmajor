# Daily Review

Perform a quick daily review to set the day's focus.

## Steps
1. Check `taskmajor://status/overdue`. List overdue tasks.
2. Check `taskmajor://agenda/today`. List appointments and tasks due today.
3. Check `taskmajor://queue/unsorted`. Count inbox items.
4. Call `next_task()` to get the top recommendation.

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
