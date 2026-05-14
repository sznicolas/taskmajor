# MCP Components (tools/resources/prompts)

## Resources

### get_history_undo

- URI: `taskmajor://history/undo`

- Source: `taskmajor/mcp/resources/history_resources.py:28`

- Signature: () -> str

- Metadata: {"uri": "taskmajor://history/undo", "name": "Undo Stack", "description": "Recent reversible actions (done/deleted tasks)", "mime_type": "application/json"}



### get_now

- URI: `taskmajor://now`

- Source: `taskmajor/mcp/resources/date_resources.py:29`

- Signature: () -> str

- Doc: Return current datetime with timezone and common shortcuts.

- Metadata: {"uri": "taskmajor://now", "name": "Current Date & Time", "description": "Current datetime with timezone and common date shortcuts", "mime_type": "application/json"}



### get_debug_errors

- URI: `taskmajor://debug/errors`

- Source: `taskmajor/mcp/resources/debug_resources.py:23`

- Signature: () -> str

- Metadata: {"uri": "taskmajor://debug/errors", "name": "Agent Error Log", "description": "Errors reported by the agent, newest first", "mime_type": "application/json"}



### get_context_current

- URI: `taskmajor://context/current`

- Source: `taskmajor/mcp/resources/context_resources.py:24`

- Signature: () -> str

- Metadata: {"uri": "taskmajor://context/current", "name": "TaskWarrior Context", "description": "Current active context and list of all defined contexts", "mime_type": "application/json"}



### get_date

- URI: `taskmajor://date/{expression}`

- Source: `taskmajor/mcp/templates/date_templates.py:20`

- Signature: (expression: str) -> str

- Doc: Resolve a TaskWarrior date expression and return ISO datetime.

- Metadata: {"uri": "taskmajor://date/{expression}", "name": "Resolved Date", "description": "Resolve any TaskWarrior date expression to an ISO datetime string", "mime_type": "application/json"}



### get_project_tasks

- URI: `taskmajor://project/{project_name}/tasks`

- Source: `taskmajor/mcp/templates/project_templates.py:23`

- Signature: (project_name: str) -> str

- Metadata: {"uri": "taskmajor://project/{project_name}/tasks", "name": "Project Tasks", "description": "Tasks filtered by project name", "mime_type": "application/json"}



## Tools

### report_error

- Source: `taskmajor/mcp/tools/diagnostic_tools.py:32`

- Signature: (tool_name: str, parameters: dict[str, Any], error: str) -> str

- Doc: Report an error encountered while using a tool.



### get_config

- Source: `taskmajor/mcp/tools/config_tools.py:32`

- Signature: () -> dict[str, Any]

- Doc: Return the current TaskWarrior configuration: timezone and UDAs.



### set_timezone

- Source: `taskmajor/mcp/tools/config_tools.py:43`

- Signature: (timezone: str) -> str

- Doc: Set the timezone in the configuration.



### add_uda

- Source: `taskmajor/mcp/tools/config_tools.py:62`

- Signature: (uda_config: UdaConfig) -> str

- Doc: Define or update a User Defined Attribute (UDA).



### delete_uda

- Source: `taskmajor/mcp/tools/config_tools.py:81`

- Signature: (name: str) -> str

- Doc: Delete a User Defined Attribute (UDA).



### define_context

- Source: `taskmajor/mcp/tools/config_tools.py:102`

- Signature: (context: ContextDTO) -> str

- Doc: Create or update a TaskWarrior context.



### delete_context

- Source: `taskmajor/mcp/tools/config_tools.py:124`

- Signature: (name: str) -> str

- Doc: Delete a TaskWarrior context.



### query_tasks

- Source: `taskmajor/mcp/tools/task_tools.py:33`

- Signature: (filters: TaskQueryFilters | None = None, sort: list[str] | None = None, limit: int = 50, offset: int = 0) -> dict[str, Any]

- Doc: Query tasks with the shared MCP business filters and canonical response shape.



### get_stats

- Source: `taskmajor/mcp/tools/task_tools.py:55`

- Signature: (filters: TaskQueryFilters | None = None) -> dict[str, Any]

- Doc: Aggregate tasks by status, project, priority, and review queue membership.



### next_task

- Source: `taskmajor/mcp/tools/task_tools.py:68`

- Signature: (filters: TaskQueryFilters | None = None) -> dict[str, Any]

- Doc: Return the next recommended actionable task.



### get_task

- Source: `taskmajor/mcp/tools/task_tools.py:80`

- Signature: (task_id: str) -> dict[str, Any]

- Doc: Get a single task with full details (depends, annotations, UDAs).



### done_task

- Source: `taskmajor/mcp/tools/task_tools.py:112`

- Signature: (task_id: str) -> str

- Doc: Mark a task as completed.



### add_task

- Source: `taskmajor/mcp/tools/task_tools.py:126`

- Signature: (task_input: TaskInputDTO) -> dict[str, Any]

- Doc: Add a new task.



### update_task

- Source: `taskmajor/mcp/tools/task_tools.py:139`

- Signature: (task_id: str, task_input: TaskInputDTO) -> dict[str, Any]

- Doc: Update an existing task.



### delete_task

- Source: `taskmajor/mcp/tools/task_tools.py:153`

- Signature: (task_id: str) -> str

- Doc: Mark a task as deleted (soft delete).



### start_task

- Source: `taskmajor/mcp/tools/task_tools.py:167`

- Signature: (task_id: str) -> str

- Doc: Start working on a task (sets start time).



### stop_task

- Source: `taskmajor/mcp/tools/task_tools.py:181`

- Signature: (task_id: str) -> str

- Doc: Stop working on a task (clears start time).



### get_projects

- Source: `taskmajor/mcp/tools/task_tools.py:195`

- Signature: () -> dict[str, Any]

- Doc: List all projects currently in use by pending tasks.



### get_tags

- Source: `taskmajor/mcp/tools/task_tools.py:206`

- Signature: () -> dict[str, Any]

- Doc: List all tags currently in use by pending tasks.



### get_udas

- Source: `taskmajor/mcp/tools/task_tools.py:217`

- Signature: () -> dict[str, Any]

- Doc: List all UDAs defined in TaskWarrior configuration.



### list_contexts

- Source: `taskmajor/mcp/tools/context_tools.py:30`

- Signature: () -> dict

- Doc: List all defined TaskWarrior contexts and indicate which is active.



### set_context

- Source: `taskmajor/mcp/tools/context_tools.py:58`

- Signature: (name: str) -> str

- Doc: Activate a TaskWarrior context. All subsequent task queries will be



### unset_context

- Source: `taskmajor/mcp/tools/context_tools.py:75`

- Signature: () -> str

- Doc: Deactivate the current TaskWarrior context. Queries will no longer



### resolve_date

- Source: `taskmajor/mcp/tools/date_tools.py:45`

- Signature: (expression: str) -> dict

- Doc: Resolve a TaskWarrior date expression to an ISO datetime string.



### validate_date

- Source: `taskmajor/mcp/tools/date_tools.py:95`

- Signature: (expression: str) -> dict

- Doc: Check whether a string is a valid TaskWarrior date expression.



## Prompts



