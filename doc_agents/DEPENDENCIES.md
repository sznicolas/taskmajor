# Dependencies

## pytaskwarrior

pytaskwarrior is a stable library maintained separately. Touch it only for confirmed bugs or missing generic TaskWarrior access features. TaskMajor is the innovation space.

**Boundary rule:**
- Feature concerns raw TaskWarrior access (CLI wrapping, DTOs, config) → belongs in pytaskwarrior
- Feature concerns orchestration, profiles, or MCP semantics → belongs in taskmajor

**What pytaskwarrior exposes (used by TaskMajor):**

```python
from taskwarrior import (
    TaskWarrior,            # main client
    TaskInputDTO,           # task creation/update input
    TaskOutputDTO,          # task read output (immutable)
    ContextDTO,             # context definition
    UdaConfig, UdaType,     # user-defined attribute config
    TaskConfigurationError, # raised when task binary not found
)
from taskwarrior.adapters import AccessMode  # ReadOnly / ReadWrite (pytaskwarrior >= 3.0)
```

**Key client methods used:**  
`get_tasks()`, `get_task(id)`, `add_task(dto)`, `modify_task(dto, id)`, `done_task(id)`, `delete_task(id)`, `start_task(id)`, `stop_task(id)`, `task_calc(expr)`, `apply_context(name)`, `unset_context()`, `get_contexts()`, `get_current_context()`, `get_udas()`, `define_uda(config)`, `delete_uda(def)`, `define_context(ctx)`, `delete_context(name)`, `is_sync_configured()`, `synchronize()`

Config access via `taskwarrior_client.config_store` — notably `config_store.set_value(key, val)` and `config_store.delete_value(key)` for direct `.taskrc` writes (no CLI required, pytaskwarrior >= 3.0).

**Note (pytaskwarrior 3.0+):** `context_service` and `uda_service` sub-objects have been **removed** from `TaskWarrior`. Use the façade methods directly (`tw.define_context()`, `tw.get_contexts()`, `tw.define_uda()`, etc.). TaskMajor uses only the façade methods.

**TaskConfigService** (`domains/taskwarrior/task_config.py`) wraps the client to provide a stable interface for configuration operations (timezone, UDAs, contexts, sync).
