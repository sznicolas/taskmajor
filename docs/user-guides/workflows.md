# TaskMajor — GTD Usage Guide

This document explains how to use TaskMajor as a personal organization tool following the GTD (Getting Things Done) method. It contains concepts, workflows, CLI examples, and Python scripts to automate next action suggestions and application.

---

## 1. Overview

TaskMajor exposes TaskWarrior via a model (FastMCP) and provides:

- Fast capture & triage (review queue).
- Useful views (review, today, week, overdue).
- Project, context, priority, and UDA management (custom attributes like `estimate` or `entry_type`).
- Analytics and logs for weekly review.
- Easy integration with AI assistants for automatic "next action" suggestions.

This guide describes how to map the GTD workflow onto TaskMajor/TaskWarrior and provides automation scripts.

---

## 2. Principles & GTD → TaskMajor Mapping

- **Capture**: configured review project (default `Inbox`).
- **Clarify**: decide if action (do, delegate, schedule, reference); tag `next` / UDA `entry_type` for actions.
- **Organize**: project, contexts (tags), priority, due/estimate UDAs.
- **Review**: views `today`, `week`, `project:XXX` and analytics for weekly review.
- **Act**: filter by context, priority, and tag `next`.

**Tip**: choose one or more projects dedicated to review (default `Inbox`) and stick with it.

---

## 3. TaskMajor Service Endpoints (resources & tools)

This chapter lists the endpoints (MCP resources and tools) exposed by TaskMajor and explains how to use them in a GTD workflow. The endpoints are meant to be consumed by:

- AI agents / assistants (via *tools* and pydantic_ai wrappers)
- Scripts or integrations (in-process via create_mcp() or via an MCP client)

Resources (read-only)

- `taskmajor://queue/unsorted` — Review Queue
  - Description: JSON resource that returns pending tasks in the Inbox project (configurable per profile).
  - GTD usage: triage recent captures before assigning to final project.
  - Example (pseudocode client):

    ```py
    content = await mcp_client.read_resource("taskmajor://queue/unsorted")
    tasks = json.loads(content)["tasks"]
    ```

- `taskmajor://debug/errors` — Agent Error Log
  - Description: JSON journal of errors raised by tools (useful for diagnosing agent behavior).

Tools (operations / mutators)

List of registered tools (name and signature) — used by agents and scripts:

- add_task(task_input: TaskInputDTO) -> dict
  - Create a task. For quick capture (GTD "Capture" phase), use `project: Inbox`.
  - Example: `add_task(description="Remind Sophie about the report", project="Inbox")`

- update_task(task_id: str, task_input: TaskInputDTO) -> dict
  - Triage a task: assign project, priority, due date, and tags. Supports both simple triage and advanced modifications.
  - **Requirement**: At least one field must be modified. Raises `ValueError` if no changes would be applied.
  - Example: `update_task(task_id="<uuid>", task_input=TaskInputDTO(project="Personal", priority="M", due="tomorrow+17h", tags=["next"]))`

- next_task() -> dict
  - Returns the recommended task (urgency-based) in current context. Usage: ask "What should I do now?".

- add_task(task_input: TaskInputDTO) -> dict
  - Create a complete task (description, project, priority, due, tags, udas...). Usage: programmatic creation or import.
  - Example input (TaskInputDTO, illustrative):

    ```json
    {
      "description": "Call the bank",
      "project": "Personal",
      "priority": "H",
      "due": "2026-03-22T17:00:00",
      "tags": ["phone","urgent"],
      "udas": {"estimate":"30m","entry_type":"task"}
    }
    ```

- update_task(task_id: str, task_input: TaskInputDTO) -> dict
  - Modify an existing task (fine triage, correction, add UDAs).

- done_task(task_id: str) -> str
  - Mark a task as completed (phase "Do / Done").

- delete_task(task_id: str) -> str
  - Deletion (soft delete) of a task.

- start_task(task_id: str) / stop_task(task_id: str) -> str
  - Start/stop task tracking (useful for time-tracking / focus sessions).

- list_contexts() -> dict / set_context(name: str) -> str / unset_context() -> str
  - TaskWarrior context management (allows client/agent to filter tasks by active context).

- report_error(tool_name: str, parameters: dict, error: str) -> str
  - Diagnostic tool: agent can log an error, useful for debug and audit.

How to Consume These Endpoints

1) In-process usage (library)

- When your script/assistant runs on the same machine or in same process, using `create_mcp()` and `task_service` is the simplest way:

```py
from taskmajor.bootstrap import create_mcp

mcp, task_service, error_log = create_mcp()
# Direct read
pending = task_service.list_pending_tasks()
# Quick capture via service layer
created = task_service.add_task(TaskInputDTO(description="Buy milk", project="Inbox"))
```

2) Remote agent / client (MCP protocol)

- For external assistants (LLM agents, Pydantic-AI), recommend exposing:
  - *resources* (read) via `taskmajor://...` (use `read_resource(uri)`),
  - and *tools* wrapping mutating operations (add_task, update_task, next_task...).

- The repository provides a convenient helper to expose a generic resource to the model: `taskmajor.domains.agent.create_generic_resource_tool(mcp_server)` — this Tool allows the agent to read any resource by URI (e.g: `taskmajor://queue/unsorted`) without knowing implementation details.

3) Recommended GTD + AI pattern (secure and verifiable)

- **Capture**: agent calls `add_task(description, project="Inbox")` to capture without triage.
- **Clarify / Triage**: human or agent runs `update_task(uuid, task_input=TaskInputDTO(project=..., priority=..., due=..., ...))` to organize task.
- **Organize**: `update_task` / `add_task` for sub-tasks or scheduling.
- **Review**: read `taskmajor://queue/unsorted` then run `next_task()` to choose next action.
- **Act**: `start_task(uuid)` / `stop_task(uuid)` and `done_task(uuid)`.

Example Automated Application (Safe Flow)

1. Agent reads `taskmajor://queue/unsorted` (items to sort).
2. It generates via LLM JSON suggestions `{id, next_action, suggested_due}` (strict format).
3. Next step: *human verifies* (recommended mode); if validated, call `update_task` to apply.

Prompts & Templates for Models

- Typical prompt (return JSON only):

```
You are a GTD assistant. Receive a JSON array of tasks: [{"uuid", "description", "project", "tags", "due", "priority", "udas"}]. For each task, propose an object {"uuid":..., "next_action": "verb + short object", "reason": "1 sentence", "suggested_due": "YYYY-MM-DD" | null}. Respond strictly in JSON array.
```

- Tips: limit number of tasks sent (top 20) and keep temperature low for stable results.

GTD-Specific Best Practices

- Use `add_task` with `project: Inbox` for instant capture, then `update_task` for grouped decisions during review.
- Provide at least one field to modify when calling `update_task` (validates that changes are intentional).
- Always log an annotation or use `report_error` if a tool returns unexpected error.

---

## 4. Quick Start

Debug / dev:

- Inspector:
```
uv run fastmcp dev inspector taskmajor/bootstrap/core.py:main
```

- Start server:
```
python -m taskmajor.bootstrap.server
# or
python -m taskmajor.bootstrap.server
```

- In-code usage (non-intrusive factory):
```py
from taskmajor.bootstrap import create_mcp
mcp, task_service, error_log = create_mcp()
```

`task_service` gives access to task operations (API depends on version; adapt to implementation).

---

## 5. Basic CLI Examples (TaskWarrior)

Quick capture to inbox (tag):

```
# Add a task to inbox
task add "Call the bank about lost card" +inbox project:Personal due:tomorrow

# Variant (inbox as project)
task add "Clean the basement" project:INBOX
```

Triage / clarification:

```
# Assign project, priority, UDA estimate and mark as next-action (tag)
task 42 modify project:Work priority:H +next estimate:30m

# If using UDA entry_type to mark entry type (to configure in TaskWarrior)
task 42 modify entry_type:next
```

Start / stop / complete:
```
task 42 start
task 42 stop
task 42 done
```

Useful views:
```
# Inbox
task +inbox

# Overdue tasks
task status:pending and due.before:today

# Tasks today
task due:today

# By project
task project:Work
```

Create a "next" report in `.taskrc` (example):
```
report.next.description=Next actions
report.next.filter=status:pending and +next
report.next.columns=project,priority,due,description
```

---

## 6. Python Scripts — Practical Patterns

A) Read inbox via `create_mcp()` (generic example — adapt to actual `task_service` API)

```py
from taskmajor.bootstrap import create_mcp

mcp, task_service, error_log = create_mcp()

# Example access (illustrative API)
inbox = task_service.search(tags=["inbox"], status="pending")
for t in inbox:
    print(t.id, t.description)

# Mark task as next-action (e.g: tag +next and UDA entry_type)
# task_service.modify(task_id, tags_add=["next"], udas={"entry_type": "next"})
```

B) Minimal pipeline (TaskWarrior export → LLM → applying suggestions)

1. Export tasks to JSON:
```
task export > tasks.json
```

2. Python script (OpenAI illustrative):

```py
import os, json, subprocess
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Read tasks
tasks_json = subprocess.run(["task", "export"], capture_output=True, text=True, check=True).stdout
tasks = json.loads(tasks_json)

# Build concise prompt
system = (
    "You are a GTD assistant. For each input task (id, description, project, tags, due), "
    "propose a single short 'next_action' and one-line reason. Return strict JSON array: "
    "[{\"id\": int, \"next_action\": string, \"reason\": string, \"suggested_due\": string|null}]."
)
user = "Tasks: " + json.dumps(tasks)

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role":"system","content":system}, {"role":"user","content":user}],
    temperature=0.2,
)

suggestions = json.loads(response.choices[0].message.content)

# Apply suggestions (dry-run first!)
for s in suggestions:
    tid = s.get("id")
    action = s.get("next_action")
    reason = s.get("reason")
    if not tid or not action:
        continue
    # Tag as next
    subprocess.run(["task", str(tid), "modify", "+next"], check=True)
    # Add annotation with suggestion
    subprocess.run(["task", str(tid), "annotate", f"Suggestion: {action} — {reason}"], check=True)

print("Suggestions applied (check the journal).")
```

Notes:
- Test first in display mode (dry-run) before applying. Don't automate overwriting without review.
- Protect API key and limit model (low temperature) for stable suggestions.

---

## 7. More Direct AI Integration Example (FastMCP pattern)

Idea: use TaskMajor as business layer to gather context (tasks, metadata, analytics) then invoke a model to produce structured suggestions. Pattern:

1. Get relevant tasks via `task_service`.
2. Build a synthetic prompt (limit items, provide project/context/estimation).
3. Ask model for strict JSON output (id, next_action, reason, suggested_due, confidence).
4. Validate and apply (or produce human review via notification).

Example prompt (text to send to model):

```
You are a GTD assistant. Here are pending tasks (id, description, project, tags, due). For each, propose ONE short next action, a one-sentence reason, and a suggested date OR null. Answer in JSON array only.
```

---

## 8. Daily Review / Checklist (practical)

- Empty inbox: sort each item (do / delegate / schedule / archive).
- Assign project and context.
- Mark next action (tag +next or UDA `entry_type=next`).
- Check tasks due today and 48h, prioritize H/M/L.
- Run AI assistant script in dry-run mode for suggestions.

## 9. Weekly Review — Checklist

- Examine active projects and blocked tasks.
- Clean backlog and transform ideas into actionable tasks.
- Check estimates (UDA) and re-prioritize for the week.
- Examine analytics (time spent, completed tasks per project) to adjust focus.

---

## 10. Best Practices & Security

- Always run in dry-run before applying automatic modifications.
- Protect LLM API keys (environment variables) and logs.
- Configure UDAs in TaskWarrior if needed (e.g: `estimate`, `entry_type`).
- Keep history (annotations) when AI proposes a change.
- Limit script scope (don't modify all tasks without strict filter).

---

## 11. Template / Short Prompt Examples (copy-paste)

Prompt to request next actions (to send to model):

```
You are a GTD assistant. Input: a JSON array of tasks with fields: id, description, project, tags, due. For each, return an object {"id": id, "next_action": "short verb+object", "reason": "one sentence", "suggested_due": "YYYY-MM-DD" or null}. Return only JSON.
```

---

## 12. Automation Checklist (cron)

- Daily / morning cron: export inbox -> run suggestions script -> send report via mail/Slack for human validation.
- Weekly cron: run analytics and deploy weekly review report.

---

## 13. Resources & Notes

- Refer to TaskWarrior for full command syntax and UDA configuration.
- `create_mcp()` allows using TaskMajor as library for test integrations.
- Adapt Python examples to `task_service` API version provided by TaskMajor.

---

If needed, add practical sections:
- Complete snippets for OpenAI/Anthropic integration
- CI/cron automation playbooks
- Detailed `.taskrc` examples

Ask if we add these sections to the repository.

---

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
