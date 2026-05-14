# MCP Interface

## Server & transport

See `doc_agents/AGENT_CONFIGURATION.md` for server transport configuration, CLI flags, and examples (stdio vs network transports and their behaviors).

Only tools declared in the active profile's `tools` whitelist are registered. Tools not in the whitelist are not exposed to the agent.

Source: `taskmajor/mcp/tools/`

## Tools

### Task Management
| Tool | Key parameters | Purpose |
|---|---|---|
| `query_tasks` | `filters`, `sort`, `limit`, `offset` | Search and paginate tasks |
| `get_task` | `task_id` | Fetch single task with all fields |
| `add_task` | `task_input: TaskInputDTO` | Create task |
| `update_task` | `task_id`, `task_input: TaskInputDTO` | Modify task |
| `done_task` | `task_id` | Mark completed |
| `delete_task` | `task_id` | Soft delete |
| `start_task` / `stop_task` | `task_id` | Track active work |
| `next_task` | `filters` | Highest-urgency unblocked task |
| `get_stats` | `filters` | Aggregate counts by status/project/priority |

**TaskQueryFilters:** `project`, `projects`, `priority`, `status`, `tags_any`, `tags_all`, `due_before`, `due_after`, `text`, `has_depends`, `is_blocked`  
**Sort options:** `due`, `-due`, `priority`, `-priority`, `project`, `urgency`, `description`, `status`, `entry`

### Date Tools
| Tool | Purpose |
|---|---|
| `resolve_date` | Convert TaskWarrior date expression to ISO 8601 (e.g. `eom`, `friday`, `now+3d`) |
| `validate_date` | Check if string is a valid TaskWarrior date expression |

### Context Tools
| Tool | Purpose |
|---|---|
| `list_contexts` | List all contexts, indicate active |
| `set_context` | Activate a context filter |
| `unset_context` | Deactivate current context |

### Configuration Tools
| Tool | Purpose |
|---|---|
| `get_config` | Full TaskWarrior config (timezone, UDAs) |
| `set_timezone` | Set timezone (IANA name) |
| `add_uda` / `delete_uda` | Manage User Defined Attributes |
| `define_context` / `delete_context` | Manage context definitions |

### Metadata & Diagnostic
| Tool | Purpose |
|---|---|
| `get_projects` / `get_tags` / `get_udas` | List active projects, tags, UDA definitions |
| `get_metadata` | API capabilities, resource URIs, filter/sort options |
| `report_error` | Log a tool error to the agent error log |

### Sync (optional — only registered when `sync.enabled = true`)
| Tool | Purpose |
|---|---|
| `force_sync` | Force an immediate TaskWarrior synchronization |
| `sync_status` | Return sync health: mode, last_sync, consecutive_failures, sync_configured |

---

## Resources (Read-Only)

Resources are declared in profile manifests and registered dynamically. URIs below assume standard or higher profile.

| URI | Returns |
|---|---|
| `taskmajor://now` | Current datetime, timezone, shortcut expressions |
| `taskmajor://context/current` | Active context and all defined contexts |
| `taskmajor://agenda/today` | Pending tasks due today |
| `taskmajor://agenda/week` | Pending tasks due within 7 days |
| `taskmajor://status/overdue` | Overdue pending tasks |
| `taskmajor://queue/unsorted` | Tasks in Inbox project |
| `taskmajor://roadmap/project\|priority\|day\|week` | Tasks grouped by scope |
| `taskmajor://analytics/summary` | Stats across all statuses |
| `taskmajor://metadata/projects\|tags\|udas\|config` | Metadata views |
| `taskmajor://debug/errors` | Agent error log |

Productivity profile adds: `taskmajor://dashboard/overview`, `taskmajor://review/daily`, `taskmajor://review/weekly`  
Project-mgmt profile adds: `taskmajor://roadmap/sprint`, `taskmajor://analytics/effort`, `taskmajor://queue/blockers`
