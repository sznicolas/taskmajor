# Architectural Decision Records

Key decisions that should not be reopened without strong justification. Each entry documents what was decided, why, and what was ruled out.

---

## ADR-001: Composable profiles via YAML inheritance

**Decision:** Profiles are declarative YAML manifests that can extend other profiles. Instructions, prompts, resources, UDAs, and contexts accumulate across the inheritance chain.

**Why:** A flat configuration approach would require repeating common definitions across profiles or creating a single monolithic config. Inheritance allows building specialized workflows (productivity, project-mgmt) on top of a stable foundation (base, standard) without duplication.

**Ruled out:** Single config file per deployment — doesn't scale to multiple workflow contexts. Runtime feature flags — adds complexity without the composability benefit.

---

## ADR-002: Tool whitelisting per profile

**Decision:** Only tools explicitly listed in the active profile's `tools` array are registered with the MCP server. Tools outside the whitelist are not exposed.

**Why:** Reduces the agent's action surface to what the profile's workflow actually needs. Prevents accidental use of destructive or out-of-scope operations (e.g., a `minimal` profile agent shouldn't be calling sprint planning tools).

**Ruled out:** Register all tools always — gives agents access to operations irrelevant or harmful to their configured workflow. Per-call permission checks — adds runtime complexity; declarative whitelisting is simpler and auditable.

---

## ADR-004: TaskWarriorProxy for PyO3 thread-affinity

**Decision:** Introduce `TaskWarriorProxy` to confine the `TaskWarrior` instance (and its underlying PyO3 `Replica`) to a single dedicated worker thread. All calls from FastMCP's `ThreadPoolExecutor` are routed through a `queue.Queue`.

**Why:** `pytaskwarrior` with `TaskChampionAdapter` exposes a `Replica` object (Rust/PyO3) that is NOT thread-safe — it panics if accessed from any thread other than its creator. FastMCP runs synchronous tool handlers via `ThreadPoolExecutor`, making concurrent `TaskWarrior` access unavoidable without isolation. A threading lock (`TaskCommandSerializer`) was already a no-op for this adapter, so a proper thread-confinement solution was required.

**Ruled out:**
- `threading.Lock` serializer — prevents concurrent access but does not fix thread-affinity (the `Replica` must be *owned* by its creator thread, not merely accessed serially).
- `asyncio.Lock` — inapplicable in a synchronous thread-pool context.
- Re-creating `TaskWarrior` per call — prohibitively expensive and incompatible with TaskChampion's SQLite ownership model.

---

## ADR-003: FastMCP as the MCP framework

**Decision:** TaskMajor uses FastMCP (≥3.0.0) rather than the low-level MCP SDK.

**Why:** FastMCP provides decorator-based tool and resource registration, handles protocol details, and reduces boilerplate. The low-level SDK would require manual message routing and schema management.

**Ruled out:** Official MCP Python SDK (low-level) — too much protocol-layer work for no benefit at this project scale. Custom HTTP implementation — no justification given FastMCP's maturity.
