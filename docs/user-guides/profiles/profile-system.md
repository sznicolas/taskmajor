# Profile Overview

This page gives a short overview of profiles. For the authoritative, detailed composition rules see:

- [Profile composition rules](../../developer/profile-composition.md)

## What is a profile?

A profile is a directory containing a `manifest.yaml` plus optional files (prompts, `instructions/` fragments, resources.yaml). Profiles are the primary extension mechanism for TaskMajor.

Keep manifests small and prefer composition via `extends` and shared fragments.

See the [available profiles](reference/README.md)

## Quick manifest example

```yaml
name: my-profile
version: 1.0.0
extends: default
resources:
  - uri: "taskmajor://my-queue"
    name: "My Queue"
    description: "Team queue"
    backend:
      function: get_stats
      params:
        filters:
          project: "my-team"
```

## Tools and validation

- Resource parameters are validated during profile load. See `taskmajor/domains/profiles/resource_mapper.py` for exact rules.
- Use `backend.params.filters` for `get_stats` rather than passing unknown top-level keys (e.g. `type`).

## Simulation & validation

A small simulation helper exists under `tools/simulate_profiles.py` to preview the real `ProfileManager` load result, inspect final resources, and produce reports. Use it for local validation before submitting a profile.

Example:

```bash
python3 tools/simulate_profiles.py --profiles project-mgmt
```

For composition semantics, examples, and contributor checklist see [Profile composition rules](../../developer/profile-composition.md).
