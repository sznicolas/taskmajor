# Profile composition rules

This document explains how TaskMajor profiles compose. It is intended for contributors who create or maintain profiles.

## 1. Overview

A profile is a directory containing a `manifest.yaml` plus zero or more auxiliary files (resources.yaml, prompts, `instructions/`, etc.). A profile manifest is represented by `ProfileManifest` in `taskmajor/domains/profiles/models.py`.

Key profile components:
- resources
- prompts
- instructions (`instructions/`)
- tools
- UDAs (user-defined attributes)

Profiles extend a parent via `extends` (a chain parent → child). A single parent string (`extends: base`) is the recommended form; a list (`extends: [p1, p2]`) is also supported for multi-parent chains, but introduces complexity and should be used sparingly. Composition is always deterministic along the chain.

To share common components across profiles, create a base profile (e.g. `base`) and have other profiles extend it via `extends: base`.

## 2. Composition semantics by component

| Component     | Parent→Child behavior        | Example |
|---------------|-----------------------------|---------|
| Resources     | Replacement (child wins)    | Child resource with same `uri` replaces parent resource |
| Prompts       | Replacement (child wins)    | Child prompt with same `name` replaces parent prompt |
| Instructions  | Fragment merge              | Parent fragments are inherited; child fragments with the same filename override them |
| Tools         | Union with deduplication    | Parent tools ∪ child tools (unique) |
| UDAs          | Union with validation       | UDAs inherited; if same name but different type → error |

Detailed rules and examples follow.

### Resources (replacement)
Parent `manifest.yaml` excerpt:

```yaml
resources:
  - uri: "test://foo"
    name: "parent-foo"
    description: "parent"
    backend:
      function: get_stats
      params:
        filters:
          status: pending
```

Child `manifest.yaml` excerpt (same URI):

```yaml
resources:
  - uri: "test://foo"
    name: "child-foo"
    description: "child override"
    backend:
      function: query_tasks
      params:
        filter: "status:pending"
```

Effect: the child entry replaces the parent entry for `test://foo`. The runtime logs an informational message when an override occurs (see `ResourceMapper.load_from_profile` in `taskmajor/domains/profiles/resource_mapper.py`).

### Partial resource merge

You can request a partial merge of the parameters for a resource declared in a parent profile by adding `merge: true` to the child entry. When `merge: true` is set, only `backend.params` are deep-merged — the other fields (name, description, `backend.function`) from the child profile replace the parent's values when provided.

Merge rules:

- Dictionaries: recursive merge (keys set by the child replace or extend the parent's values).
- Lists: replacement (the child replaces the list entirely; there is no concatenation).
- Scalars (str, int, bool...): replaced by the child.

Example:

Parent:

```yaml
resources:
  - uri: "test://foo"
    name: "parent-foo"
    backend:
      function: get_stats
      params:
        filter: "status:pending"
        sort: ["due"]
        limit: 50
```

Child:

```yaml
resources:
  - uri: "test://foo"
    merge: true
    backend:
      function: get_stats
      params:
        filter: "status:pending project:Inbox"
```

Effective result: `backend.params` = `{filter: "status:pending project:Inbox", sort: ["due"], limit: 50}`.

When to use: `merge: true` is useful when the child only needs to change part of the parameters (for example, add a filter) and keep inheriting the parent's other settings (sort order, limit, and so on). Use the default override behavior when the child should replace the resource definition completely.

### Prompts (replacement)
Parent:

```yaml
prompts:
  - name: code_review
    file: prompts/code_review.md
```

Child:

```yaml
prompts:
  - name: code_review
    file: prompts/team_code_review.md
```

Effect: the child prompt (same `name`) replaces the parent prompt.

### Instructions (`instructions/` fragments)
Profiles load `instructions/*.md` fragments in filename order. Fragments with the same filename override inherited fragments, and an empty child fragment removes the inherited fragment entirely. YAML front matter is supported and stripped before concatenation.

### Removing a parent fragment
To cancel an inherited instruction fragment from a parent profile (for example, to remove date guidance), create an empty file (0 bytes) with the same filename under the child's `instructions/` directory. The loader treats an empty fragment as an instruction to remove the parent's fragment from the merged result.

Example: the `minimal` profile removes `030_date_usage.md` inherited from `base` by creating an empty `profiles/minimal/instructions/030_date_usage.md` file. This is the official mechanism for "removing" a parent fragment.

### Tools (union)
Parent:

```yaml
tools:
  - git
  - docker
```

Child:

```yaml
tools:
  - docker
  - jq
```

Effect: resulting tools = [`git`, `docker`, `jq`] (order is not guaranteed; duplicates removed).

### UDAs (union with validation)
Parent:

```yaml
udas:
  - name: priority
    type: string
    label: "Priority"
```

Child may inherit the UDA. If child declares a UDA with the same `name` but a different `type`, this is a configuration error and must fail validation (contributors should keep UDA types stable across inheritance).

Additional rules (UDAs values):

- If a parent declares an explicit list of allowed values (`values:`), any child that re-declares the same UDA must restrict its `values` to a subset of the parent's list (or keep it identical). Adding new allowed values in a child when the parent had an explicit list is a configuration error.
- If the parent does not declare an explicit `values:` list (empty or omitted), a child may introduce a `values:` list (a legitimate restriction).
- Type mismatches (e.g. `string` vs `integer`) are always treated as errors and will cause profile loading to fail.

These checks are performed at profile-load time by `ProfileManager` to prevent inconsistent UDA definitions across extends chains.

## 3. Path resolution (search order, 3 levels)
When resolving a profile name to a filesystem path, check in this order:

1. Absolute path provided in `extends` (if path starts with `/` or `~` — `~` is expanded).
2. User config directory: `~/.config/taskmajor/profiles/<name>/` (or `$XDG_CONFIG_HOME/taskmajor/profiles/<name>/`).
3. Built-in profiles shipped with the application: `taskmajor/profiles/<name>/` (inside the codebase or system package).

This order guarantees that a local override (user config) can shadow a built-in profile, but an explicit absolute path always wins.

## 4. Conflict detection

- Sibling conflict (two profiles merged at the same depth declare the same resource `uri` or prompt `name` and neither is a descendant of the other): treated as an error. The loader raises `ProfileConflictError` (see `profile_manager.py`).
- Parent→child override (different depth): allowed — child wins. Loader emits an informational log (override message) and proceeds.
- Duplicate entries within the *same* manifest (two identical `uri` values in one `manifest.yaml`): treated as an immediate error — `ValueError` is raised during manifest loading (see `ResourceMapper.load_from_profile`).

## 5. Validation of backend parameters (ResourceMapper rules)

Resource parameters in a resource's `backend.params` are validated during profile load by `ResourceMapper.load_from_profile` (`taskmajor/domains/profiles/resource_mapper.py`):

- `backend.function` must be a member of `ResourceMapper.ALLOWED_BACKENDS`.
- `backend.params` must be a mapping (YAML dict).
- The runtime `TaskService` instance must expose the callable named by `backend.function`. If not present or not callable → `ValueError`.
- `inspect.signature()` is used to obtain the function signature. If the callable accepts `**kwargs` (VAR_KEYWORD) or `*args` (VAR_POSITIONAL), parameter validation is skipped (the backend accepts arbitrary kwargs/args).
- Otherwise, the set of accepted parameter names is derived from positional-or-keyword and keyword-only parameters (excluding `self`). Any keys in `backend.params` that are not in the accepted set cause a `ValueError` with a clear, actionable message. The message contains the profile name, resource URI, provided keys, and accepted keys.

Example — incorrect (before):

```yaml
backend:
  function: get_stats
  params:
    type: ci_status
```

This failed at runtime with a `TypeError` because `get_stats` expects `filters` (or other named args), not `type`.

Corrected (after):

```yaml
backend:
  function: get_stats
  params:
    filters:
      type: ci_status
```

(Validation now fails fast at profile load with `ValueError` and a clear message instead of a late `TypeError`.)

## 6. Contributor checklist

Before submitting a profile, verify the following:

- [ ] No duplicate `uri` values inside the same `manifest.yaml`.
- [ ] All `backend.function` values are listed in `ResourceMapper.ALLOWED_BACKENDS`.
- [ ] All `backend.params` keys match the `TaskService` function signature (or the function accepts `**kwargs`).
- [ ] No sibling conflicts with profiles provided by parent profiles in the extends chain (resolve or rename to avoid conflict).
- [ ] UDAs are consistent with parent definitions (same `type` for same `name`).
- [ ] `instructions/` fragments reviewed and tested for clarity.
- [ ] Add or update tests under `tests/domains/profiles/` when introducing new behavior.

## 7. Example: create a child profile `my-team` that extends `minimal`

1. Create directory: `profiles/my-team/`
2. Add `manifest.yaml`:

```yaml
name: my-team
version: "1.0.0"
extends: minimal
tools:
  - query_tasks
  - add_task
resources:
  - uri: "taskmajor://team/tasks"
    name: "Team tasks"
    description: "Tasks for my team"
    backend:
      function: get_stats
      params:
        filters:
          project: "my-team"
```

3. Add `instructions/010_objective.md` with team-specific guidance.
4. Run unit tests and validate loading:

- Run targeted tests: `pytest tests/domains/profiles/test_resource_mapper.py -q`
- Inspect logs for override messages when expected.

## See also (code references)
- `taskmajor/domains/profiles/profile_manager.py` — profile loading & extends resolution
- `taskmajor/domains/profiles/resource_mapper.py` — resource composition and backend param validation
- `taskmajor/domains/profiles/models.py` — manifest model
