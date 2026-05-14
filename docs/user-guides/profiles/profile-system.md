# Profile Overview

This page gives a short overview of profiles. For the authoritative, detailed composition rules see:

- [Profile composition rules](../../developer/profile-composition.md)

## What is a profile?

A profile is a directory containing a `manifest.yaml` plus optional files (prompts, `instructions/` fragments, resources.yaml). Profiles are the primary extension mechanism for TaskMajor.

Keep manifests small and prefer composition via `extends` and shared fragments.

See the [available profiles](reference/README.md)

## Manifest components

A manifest can declare any combination of the following components:

| Component | Description |
|-----------|-------------|
| `extends` | Parent profile(s) to inherit from |
| `tools` | MCP tools enabled for this profile |
| `resources` | Read-only MCP resource views |
| `udas` | TaskWarrior User-Defined Attributes |
| `prompts` | Agent instruction prompts (explicit file paths) |
| `contexts` | TaskWarrior contexts defined at startup |
| `instructions/` | Directory of instruction fragment files (auto-discovered) |

### `extends`

Inherit tools, resources, udas, prompts, and contexts from a parent profile. Accepts a string (single parent) or a list (multiple parents, chained in order). Composition semantics per component are described in the Profile composition rules page linked above.

```yaml
# Single parent
extends: standard

# Multiple parents (chained in declaration order)
extends:
  - base
  - my-shared-bundle
```

### `tools`

List of MCP tool names to enable. Tools are unioned with the parent profile (duplicates removed). See [API Reference → Tools](../../api-reference/tools.md) for the full list.

```yaml
tools:
  # Task CRUD
  - add_task
  - get_task
  - query_tasks
  - update_task
  - delete_task
  - done_task
  - start_task
  - stop_task
  - next_task
  # Metadata
  - get_projects
  - get_tags
  - get_udas
  # Date utilities
  - resolve_date
  - validate_date
  # Context management
  - list_contexts
  - set_context
  - unset_context
  # Configuration
  - get_config
  - set_timezone
  - add_uda
  - delete_uda
  - define_context
  - delete_context
  # Diagnostics
  - report_error
```

### `resources`

Read-only MCP views accessible to agents via `read_mcp_resource(uri)`. Each resource maps a URI to a backend function. See [API Reference → Resources](../../api-reference/resources.md#backend-functions) for available backend functions.

```yaml
resources:
  # Filter with query_tasks
  - uri: "taskmajor://queue/unsorted"
    name: "Unsorted Queue"
    description: "Pending tasks without a project (Inbox)"
    backend:
      function: query_tasks
      params:
        filter: "status:pending project:Inbox"
        sort: ["priority", "due"]

  # Aggregate stats
  - uri: "taskmajor://analytics/summary"
    name: "Task Statistics"
    description: "Task counts by status, project, and priority"
    backend:
      function: get_stats
      params:
        filters: {status: all}

  # Group by scope (project | priority | day | week)
  - uri: "taskmajor://roadmap/project"
    name: "Project Roadmap"
    description: "Pending tasks grouped by project"
    backend:
      function: get_tasks_by_scope
      params:
        scope: project
        filters: {status: pending}

  # Metadata lookup (no params needed)
  - uri: "taskmajor://metadata/projects"
    name: "Projects"
    description: "All projects in use by pending tasks"
    backend:
      function: get_projects
```

### `udas`

Declare TaskWarrior User-Defined Attributes. UDAs are inherited from parent profiles; child profiles cannot change a UDA's `type` or extend the parent's `values` list.

Valid types: `string`, `numeric`, `date`, `duration`.

```yaml
udas:
  # String UDA with allowed values
  - name: energy
    type: string
    label: "Energy"
    description: "Energy required: low | medium | high"
    values: [low, medium, high]
    default: medium        # optional default value

  # Numeric UDA (no allowed-values restriction)
  - name: estimate
    type: numeric
    label: "Estimate (hours)"
    description: "Estimated effort in hours."

  # Date UDA
  - name: reviewed_on
    type: date
    label: "Last Reviewed"

  # Free-form string UDA
  - name: owner
    type: string
    label: "Owner"
    description: "Person responsible for the task."
```

### `prompts`

Prompts are discovered automatically from the profile's `prompts/*.md` directory — no declaration needed for this common case.

To declare a prompt with an explicit file path (useful when the file lives outside `prompts/`), use the dict form:

```yaml
prompts:
  - name: sprint_planning
    file: prompts/sprint_planning.md
```

> **Note**: String-only entries (e.g. `- daily_review`) are not processed by the loader and have no effect. Always use the dict form or rely on filesystem auto-discovery.

### `contexts`

Declare TaskWarrior contexts to define at server startup. Each context is a named filter pair applied when the agent activates it.

```yaml
contexts:
  - name: work
    read_filter: "project:work or project:infra"
    write_filter: "project:work"
  - name: perso
    read_filter: "project:perso or project:home"
    write_filter: "project:perso"
```

### `instructions/` directory

Instruction fragments are loaded automatically from the `instructions/` directory inside the profile folder — no manifest key needed. Fragments are merged in filename order across the extends chain. An empty file (0 bytes) removes the inherited fragment.

```
my-profile/
├── manifest.yaml
└── instructions/
    ├── 010_objective.md      # custom guidance
    └── 030_date_usage.md     # empty → removes parent fragment
```

---

## Complete example

A profile extending `standard` with custom tools, a resource, a UDA, and prompts:

```yaml
name: my-team
version: "1.0.0"
extends: standard

tools:
  - get_udas

udas:
  - name: sprint
    type: string
    label: "Sprint"
    description: "Sprint name (e.g., Sprint-42)."

contexts:
  - name: team
    read_filter: "project:my-team"
    write_filter: "project:my-team"

resources:
  - uri: "taskmajor://queue/blockers"
    name: "Blocked Queue"
    description: "Tasks blocked by dependencies"
    backend:
      function: query_tasks
      params:
        filter: "is_blocked:true"
        sort: ["priority", "due"]

prompts:
  - name: sprint_planning
    file: prompts/sprint_planning.md
```

---

## Tools and validation

- Resources declared in manifests use backend functions documented in [API Reference → Resources](../../api-reference/resources.md#backend-functions).
- Available tools are listed in [API Reference → Tools](../../api-reference/tools.md).
- Resource parameters are validated during profile load. See `taskmajor/domains/profiles/resource_mapper.py` for exact rules.
- Use `backend.params.filters` for `get_stats` rather than passing unknown top-level keys (e.g. `type`).

## Simulation & validation

A small simulation helper exists under `tools/simulate_profiles.py` to preview the real `ProfileManager` load result, inspect final resources, and produce reports. Use it for local validation before submitting a profile.

Example:

```bash
python3 tools/simulate_profiles.py --profiles project-mgmt
```

For composition semantics, examples, and contributor checklist see the Profile composition rules page linked above.
