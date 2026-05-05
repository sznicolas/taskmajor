# Review Protocols

## Daily Review
1. **Overdue**: Check `taskmajor://status/overdue`. Reschedule or delete.
2. **Today**: Check `taskmajor://agenda/today`. Confirm capacity.
3. **Inbox**: Check `taskmajor://queue/unsorted`. Triage items.
4. **Next Action**: Call `next_task()` or select manually.

Output format:
📅 Daily Review
🔴 OVERDUE: ...
📋 TODAY: ...
📥 INBOX: ...
💡 NEXT: ...

## Weekly Review
1. **Summary**: Count completed tasks this week.
2. **Planning**: Check `taskmajor://agenda/week`. Identify busy days.
3. **Orphans**: Find tasks without due dates. Assign dates or move to `+someday`.
4. **Projects**: Check `taskmajor://analytics/summary`. Ensure no project is blocked.

Output format:
📊 Weekly Review
✅ COMPLETED: ...
📅 WEEK AHEAD: ...
⚠️ ORPHANS: ...
📁 PROJECTS: ...
