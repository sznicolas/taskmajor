# Profiles

A profile is a declarative workflow definition. It controls what an agent can do (tool whitelist), what data structures exist (UDAs, contexts), what views are available (resources), and how the agent should behave (instructions, prompts).

Source: `taskmajor/profiles/`

## Inheritance Chain

```
base  →  minimal
      →  standard  →  productivity
                   →  project-mgmt
```

Each child inherits and extends its parent. Instructions and prompts accumulate across the chain.

## Built-In Profiles

| Profile | Extends | Purpose |
|---|---|---|
| `base` | — | Minimal CRUD: add/update/delete/query tasks |
| `minimal` | base | Same as base, explicit minimal scope |
| `standard` | base | Universal: adds stats, date tools, contexts, metadata, agenda/roadmap resources |
| `productivity` | standard | GTD-inspired: adds UDAs, daily/weekly review prompts and resources |
| `project-mgmt` | standard | Advanced PM: adds sprint planning, effort analytics, blockers queue |

## Profile File Structure

```
profiles/<name>/
  manifest.yaml          # declarative definition
  instructions/          # .md files loaded as agent instructions
    010_objective.md
    020_workflow.md
    ...
  prompts/               # optional; named prompts (e.g. daily_review.md)
```

## manifest.yaml Structure

```yaml
name: profile-name
version: 1.0.0
description: "..."
extends: [base]          # parent profiles, resolved recursively

tools:                   # whitelist — only these are registered
  - query_tasks
  - add_task

udas:                    # User Defined Attributes added to TaskWarrior
  - name: energy
    type: enum            # enum | string | numeric | date
    label: "Energy Level"
    values: [low, medium, high]
    default: medium

contexts:                # TaskWarrior context filters
  - name: work
    read_filter: "project:Work"
    write_filter: "project:Work"

resources:               # read-only views declared declaratively
  - uri: "taskmajor://agenda/today"
    name: "Today's Agenda"
    description: "..."
    backend:
      function: query_tasks   # must be in ALLOWED_BACKENDS
      params:
        filter: "status:pending due.before:eod"

prompts:
  - daily_review         # references prompts/daily_review.md
```

## Skills

Skills are `.md` files in `instructions/` that teach the agent a specific behavior within the profile context. Unlike generic instructions, a skill describes a concrete workflow the agent can execute on request.

Examples: GTD weekly review procedure, sprint planning sequence, daily standup preparation.

Skills are not yet formalized as a separate construct — they live as instruction files with a focused, action-oriented scope. A future `skills/` subdirectory per profile may be introduced to distinguish them from ambient instructions.

## Resource Composition

Child profiles can override or merge parent resources using `merge: true`. URI uniqueness is validated across the full profile chain at startup.

## Updating This Doc

Update this file when:
- A new built-in profile is added or its purpose changes
- The manifest.yaml schema gains new fields
- The inheritance structure changes
- The skills concept is formalized
