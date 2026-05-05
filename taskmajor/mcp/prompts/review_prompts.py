"""
Review prompts: daily standup and weekly review.
"""

from __future__ import annotations

from fastmcp import FastMCP

DAILY_REVIEW_PROMPT = """\
# Daily Review

Perform a complete daily review for the user.

## Steps

1. **Overdue** — Check `taskmajor://status/overdue`. List each overdue task with its delay.
   If any, propose rescheduling or completing them.

2. **Today's Agenda** — Check `taskmajor://agenda/today`. Present:
   - Appointments (entry_type=appointment) with their time
   - Tasks due today, sorted by priority
   - Active tasks (started)

3. **Inbox** — Check `taskmajor://queue/unsorted`. If count > 0:
   "You have {count} tasks in the inbox. Quick triage?"

4. **Suggestion** — Call `next_task()`. Propose:
   "Your next recommended action: {description} ({project}, urgency: {urgency})"

## Output Format

```
📅 [Today's Date] — Daily Review

🔴 OVERDUE ({count})
   • {description} — overdue by {overdue_by}

📋 TODAY ({count})
   🕐 {time} — {description} [appointment]
   • {description} (priority: {priority}, estimated: {estimate})

🔄 IN PROGRESS ({count})
   • {description} — started at {start}

📥 INBOX: {count} task(s) awaiting triage

💡 NEXT ACTION: {description}
```
"""

WEEKLY_REVIEW_PROMPT = """\
# Weekly Review

Perform a complete weekly review.

## Steps

1. **Week Summary** — Call `list_tasks(status="completed")`.
   Filter those completed this week (last 7 days).
   Summary: "{count} tasks completed this week."

2. **Week Ahead** — Check `taskmajor://agenda/week`. Present the planning day by day.
   - Identify busy and free days.
   - Identify appointments and reminders (entry_type=appointment and entry_type=reminder) with their time

3. **Tasks without Date** — Call `list_tasks(status="pending")`.
   Filter those without `due`. These are orphans to reschedule.
   "There are {count} pending tasks without a due date."

4. **Inbox** — Check `taskmajor://queue/unsorted`.
   "Inbox: {count} unsorted tasks."

5. **Projects** — Check `taskmajor://analytics/summary` and `taskmajor://config/schema`.
   For each active project, indicate the number of pending tasks.

6. **Recommendations** — Propose:
   - Reschedule tasks without date
   - Sort inbox
   - Identify blocked projects (tasks with depends)

## Output Format

```
📊 Weekly Review — Week of {monday} to {sunday}

✅ SUMMARY ({count} completed)
   • {description} — {project}

📅 WEEK AHEAD
   Monday ({count}):
     • {description} — {due}
   Tuesday ({count}):
     ...

⚠️ NO DATE ({count})
   • {description} — {project}

📥 INBOX: {count}

📁 PROJECTS
   {project}: {pending_count} pending, {estimate_total} estimated
   ...

💡 RECOMMENDATIONS
   - ...
```
"""

def register_review_prompts(mcp: FastMCP) -> None:
    """Register daily and weekly review prompts."""

    @mcp.prompt(
        name="daily_review",
        description="Daily review guide: overdue, agenda, inbox, suggestion",
    )
    def daily_review() -> str:
        return DAILY_REVIEW_PROMPT

    @mcp.prompt(
        name="weekly_review",
        description="Weekly review guide: summary, planning, orphans, projects",
    )
    def weekly_review() -> str:
        return WEEKLY_REVIEW_PROMPT
