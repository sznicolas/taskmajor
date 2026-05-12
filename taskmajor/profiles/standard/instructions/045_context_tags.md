# Context Tags (`+@`)

## Concept
A **context tag** indicates *where* or *with what* a task must be performed.
Unlike categorical tags (`+urgent`), context tags use the `@` symbol to
signal a location, tool, or situation.

| Type | Prefix | Meaning | Examples |
|------|--------|---------|----------|
| Categorical | `+` | Quality or category | `+urgent`, `+grocery`, `+someday` |
| Context | `+@` | Location or tool | `+@home`, `+@computer`, `+@phone`, `+@errands` |

## Why `+@` instead of TaskWarrior Contexts?
TaskWarrior's native `context` is a **global persistent filter**. If set,
it silently hides tasks until unset, which is dangerous for AI agents.
Context tags (`+@`) are safer because:
- They live **on the task**, not in global state.
- They are **explicit** (you filter by them only when needed).
- They **never hide** tasks by accident.

## Usage Rules
1. **Prefix:** Always use `+@` for contexts (e.g., `+@home`, never `+home`).
2. **Filtering:** Use `query_tasks(tags_any=["+@computer"])` to find tasks for a specific context.
3. **Assignment:** Assign at least one context tag during triage (e.g., "Call dentist" → `+@phone`).
4. **No Native Contexts:** Never use `set_context` or `list_contexts`.

## Common Context Tags
- `+@home`: Chores, family, personal tasks.
- `+@office`: Work-specific tasks.
- `+@computer`: Requires a laptop/desktop.
- `+@phone`: Calls or messaging.
- `+@errands`: Requires leaving the house.
- `+@anywhere`: Can be done anywhere (reading, thinking).

