# GTD Workflow Guide

TaskMajor implements a workflow inspired by GTD (Getting Things Done) adapted to multi-project personal/professional management with an AI agent.

## Key Concepts

### Review Queue
Any idea, task, or reminder quickly captured without organization. The review queue is the single entry point.

- **Capture**: `add_task(description="call the plumber", project="Inbox")`
- **Check**: `taskmajor://queue/unsorted`
- **Triage**: `update_task(id, task_input=TaskInputDTO(project="home", priority="M", due="saturday+10h"))`

### Contexts
Contexts completely isolate personal and professional universes. A context is a global filter applied to all requests.

```
# Create (init mode)
define_context("work", "project:work or project:infra")
define_context("perso", "project:perso or project:home")

# Use
python agent.py --context work     # Work only
python agent.py --context perso    # Personal only
python agent.py                    # Everything
```

### Task Types

| Type | Description | Convention |
|------|-------------|------------|
| `task` | Standard task | `due` = deadline |
| `appointment` | Appointment, fixed time slot | `scheduled` ≈ `due` = same time |
| `reminder` | Simple reminder | `due` only, no action |

The entry_type is stored as a UDA: `udas: {"entry_type": "appointment"}`.

### Estimation
The `estimate` UDA allows you to plan workload.

```
udas: {"estimate": "2h"}     # 2 hours
udas: {"estimate": "30min"}  # 30 minutes
udas: {"estimate": "1d"}     # 1 day
```

The agent can sum estimations by project to propose roadmaps.

---

## Daily Workflow

### 1. Capture (throughout the day)
Capture immediately when an idea comes:
```
> Note me: review the Lambda contract
> Reminder: Marie's birthday on March 15
> Appointment: haircut Thursday at 4pm
```

The agent uses `add_task` with `project: Inbox` to capture tasks without triage.

### 2. Triage (morning or when review queue overflows)
```
> Sort my tasks to review
```

The agent checks `taskmajor://queue/unsorted`, then for each task proposes triage:
- Assign a project
- Set a priority
- Set a date if relevant
- Define the entry_type (task/appointment/reminder)
- Estimate duration

### 3. Daily Review (morning)
```
> Daily review
```

The agent follows the `daily_review` prompt:
1. 🔴 Overdue tasks → proposal to reschedule
2. 📋 Today's agenda (appointments sorted by time, then tasks)
3. 📥 Review → push to triage
4. 🔄 Active tasks (started)
5. 💡 Suggestion: next action

### 4. Execution
```
> What should I do now?
```

The agent calls `next_task()` and proposes the most urgent task.

```
> I finished "Prepare the presentation"
```

The agent calls `done_task(id)` and proposes the next one.

### 5. End of Day
```
> Stop the current task
```

---

## Weekly Workflow

### Review (Sunday evening or Monday morning)
```
> Weekly review
```

The agent follows the `weekly_review` prompt:
1. ✅ Summary: tasks completed this week
2. 📅 Week ahead: day by day planning
3. ⚠️ Tasks without date: orphans to reschedule
4. 📥 Review: remaining unsorted tasks
5. 📁 Projects: progress per project
6. 💡 Recommendations

---

## Personal/Professional Separation

### Principle
Each agent runs in a context. Projects never mix.

```bash
# Terminal 1: professional context
python agent.py --context work

# Terminal 2: personal context
python agent.py --context perso
```

### Project Organization

```
work               # Main professional project
work.infra         # Infra sub-project
work.reports       # Reports sub-project
perso              # Main personal project
perso.home         # Home sub-project
perso.admin        # Admin sub-project
```

### Recommended Contexts

```
# Init mode
define_context("work", "project.is:work or project.startswith:work.")
define_context("perso", "project.is:perso or project.startswith:perso.")
```

---

## Appointments

### Create an Appointment
```
> Dentist appointment Friday at 2:30pm, duration 1h
```

The agent creates:
```json
{
  "description": "Dentist appointment",
  "due": "friday+14.5h",
  "scheduled": "friday+14.5h",
  "udas": {"entry_type": "appointment", "estimate": "1h"}
}
```

### View Your Schedule
```
> What do I have today?
```

The agent checks `taskmajor://agenda/today` and presents appointments first, sorted by time.

---

## Tips

- **Hyperactivity**: capture to Inbox with `add_task`, triage later
- **Indecision**: ask `next_task()` instead of choosing
- **Overload**: check `taskmajor://analytics/summary` to see the distribution
- **Forgetting**: check `taskmajor://status/overdue` at the start of the session
- **Planning**: use `taskmajor://agenda/week` to see the week ahead
- **Estimation**: always estimate with `estimate` for reliable roadmaps
