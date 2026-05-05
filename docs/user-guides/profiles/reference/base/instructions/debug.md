<!-- DEBUG - fragments prefixed with 🔍 - not sent via MCP -->

```text
🔍 # Base Profile Objective
🔍 
🔍 Provide the shared TaskMajor foundation for every profile. Capture tasks quickly, keep triage consistent, and make the next action obvious.
🔍 
🔍 # Workflow
🔍 
🔍 1. Capture with `add_task`; keep the description direct and action-oriented.
🔍 2. Triage with `update_task`; change at least one field before saving.
🔍 3. Execute with `done_task` when work is finished.
🔍 
🔍 # TaskWarrior Date Expressions
🔍 
🔍 ## Workflow
🔍 - Always call `resolve_date` before using any date in `add_task` or `update_task`.
🔍 - Call `validate_date` when the expression comes from user input.
🔍 - Call `read_mcp_resource("taskmajor://now")` to know the current date, time, timezone, and shortcuts (`eod`, `eow`, `eom`).
🔍 
🔍 ## Precision
🔍 - `due:today+17h` → today at 17:00:00
🔍 - `due:now+2h` → 2 hours from now
🔍 - `due:today+9.5h` → today at 09:30:00
🔍 - `due:today+570min` → today at 09:30:00
🔍 - `⚠ due:today+9h30m` → BROKEN (do not use)
🔍 
🔍 ## Synonyms (case-insensitive)
🔍 - `today` / `now` — current datetime
🔍 - `yesterday` / `tomorrow`
🔍 - `monday` … `sunday` (or `mon` … `sun`)
🔍 - `eod` — end of day (today 23:59:59)
🔍 - `eow` — end of week (Sunday 23:59:59)
🔍 - `eom` — end of month (last day of current month 23:59:59)
🔍 - `sod` — start of day (today 00:00:00)
🔍 - `sow` — start of week (Monday 00:00:00)
🔍 - `som` — start of month (1st 00:00:00)
🔍 
🔍 ## Relative expressions
🔍 - `now+2h`, `now+30min`, `now+90s`
🔍 - `today+3d`, `today+2w`, `today+1mo`
🔍 - `next monday`, `last friday`
🔍 
🔍 ## ISO 8601 durations
🔍 - `P2W` → `P14D`
🔍 - `PT3H` → `PT3H`
🔍 - `P1M`, `P1Y`
🔍 
🔍 ## Rules
🔍 - Always `resolve_date` before submitting to avoid silent failures.
🔍 - Use `now` for relative precision, `today` for day-level dates.
🔍 - Never use `today+XhYm` syntax; use decimal hours or total minutes.
🔍 - Confirm the timezone with `taskmajor://now` when scheduling across timezones.
🔍 
🔍 # Text Quality
🔍 
🔍 - Pass strings directly as UTF-8.
🔍 - Do not escape quotes, accents, or apostrophes.
🔍 - Emojis are supported and welcome.
🔍 - Preserve the user's language and formatting as written.
🔍 - Build task text directly; do not route it through shell escaping.
🔍
```
