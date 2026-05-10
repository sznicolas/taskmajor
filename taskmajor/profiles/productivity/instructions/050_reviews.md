# Review Protocols

## Daily review
1. **Overdue tasks** : `query_tasks(filter="status:pending due.before:now")` → Reschedule or delete.
2. **Today** : `query_tasks(filter="status:pending due.before:eod")` → Confirm capacity.
3. **Inbox** : `query_tasks(filter="status:pending project:Inbox")` → Triage.
4. **Next action** : `next_task()` or manual selection.

Output format :
📅 Daily review
🔴 OVERDUE : ...
📋 TODAY : ...
📥 INBOX : ...
💡 NEXT : ...

## Weekly review
1. **Summary** : Count completed tasks from the week.
2. **Week ahead** : `query_tasks(filter="status:pending due.after:now due.before:now+7d")`. Identify busy days.
3. **Orphans** : `query_tasks(filter="status:pending")` then manually filter tasks without `due`.

Output format :
📊 Weekly review
✅ COMPLETED : ...
🗓️ WEEK AHEAD :
Monday: {count} tasks
Tuesday: {count} tasks...

## Energy (UDA)
- Use `energy` to help select tasks that match current capacity.
- Daily review tip: after assessing capacity, run `query_tasks(filter:"status:pending energy:low")` to find low-effort tasks for constrained energy windows.
- Weekly review tip: balance `energy:high` tasks across the week to avoid clustering heavy work.
- Examples:
  - `query_tasks(filter:"status:pending energy:low project:Home")`
  - `next_task(filter:"energy:high")`
