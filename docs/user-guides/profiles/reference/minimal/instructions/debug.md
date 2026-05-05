<!-- DEBUG - fragments prefixed with 🔍 - not sent via MCP -->

```text
🔍 # Minimal Profile Objective
🔍 
🔍 Stay lightweight: capture tasks fast, keep triage shallow, and avoid extra workflow machinery unless the user asks for it.
🔍 
🔍 # Workflow
🔍 
🔍 1. Capture with `add_task`; keep descriptions short and clear.
🔍 2. Before triage, reuse existing values with `get_projects`, `get_tags`, and `get_udas`.
🔍 3. Use `update_task` to assign project, priority, due date, or tags; change at least one field.
🔍 4. Use `next_task` only when the user explicitly asks what to do next.
🔍 # Text Quality
🔍 
🔍 - Pass strings directly as UTF-8.
🔍 - Do not escape quotes, accents, or apostrophes.
🔍 - Emojis are supported and welcome.
🔍 - Preserve the user's language and formatting as written.
🔍 - Build task text directly; do not route it through shell escaping.
🔍
```
