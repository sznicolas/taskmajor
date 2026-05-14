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
| `extends` | Parent profile to inherit from |
| `tools` | MCP tools enabled for this profile |
| `resources` | Read-only MCP resource views |
| `udas` | TaskWarrior User-Defined Attributes |
| `prompts` | Agent instruction prompts |
| `instructions_file` | Directory of instruction fragment files |

### `extends`

Inherit tools, resources, udas, and prompts from a parent profile. Composition semantics per component are described in the Profile composition rules page linked above.

```yaml
extends: standard
```

### `tools`

List of MCP tool names to enable. Tools are unioned with the parent profile (duplicates removed). See [API Reference → Tools](../../api-reference/tools.md) for the full list.

```yaml
tools:
  - add_task
  - get_task
  - query_tasks
  - update_task
  - delete_task
  - done_task
  - start_task
  - stop_task
  - next_task
  - resolve_date
  - validate_date
  - get_projects
  - get_tags
  - get_udas
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

```yaml
udas:
  # String UDA with allowed values
  - name: energy
    type: string
    label: "Energy"
    description: "Energy required: low | medium | high"
    values: [low, medium, high]

  # Numeric UDA (no allowed-values restriction)
  - name: estimate
    type: numeric
    label: "Estimate (hours)"
    description: "Estimated effort in hours."

  # Free-form string UDA
  - name: owner
    type: string
    label: "Owner"
    description: "Person responsible for the task."
```

### `prompts`

List of named prompts to expose to the agent. Prompts are loaded from `taskmajor/mcp/prompts/` or the profile's own `prompts/` directory.

```yaml
prompts:
  - daily_review
  - weekly_review
```

### `instructions_file`

Path (relative to the profile directory) to a folder of Markdown instruction fragments. Fragments are merged with the parent profile's instructions in filename order. An empty file removes the parent fragment.

```yaml
instructions_file: instructions/
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
  - sprint_planning

instructions_file: instructions/
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
