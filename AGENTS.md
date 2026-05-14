# TaskMajor

Python MCP server that connects AI agents to TaskWarrior through a composable profile system. Each profile declares allowed tools, UDAs, contexts, and agent behavioral instructions.

## Commands

```bash
uv run -m taskmajor.bootstrap.server                          # start server
uv run -m taskmajor.bootstrap.server --profile productivity   # explicit profile
pytest                                                         # run tests
ruff check .                                                   # lint
```

## Context Menu

Load only the files relevant to your task — keep context small.

| Task | Load |
|---|---|
| Review or create a profile | `doc_agents/PROFILES.md` + `doc_agents/MCP_INTERFACE.md` |
| Architecture discussion | `doc_agents/ARCHITECTURE.md` + `doc_agents/DEPENDENCIES.md` |
| Implement a skill | `doc_agents/PROFILES.md` (Skills section) |
| Bug at the pytaskwarrior boundary | `doc_agents/DEPENDENCIES.md` + `doc_agents/ARCHITECTURE.md` |
| Add a MCP tool or resource | `doc_agents/MCP_INTERFACE.md` + `doc_agents/ARCHITECTURE.md` |
| Architectural decision | `doc_agents/ADRs.md` |

## Documentation

- `doc_agents/ARCHITECTURE.md` — modules, initialization flow
- `doc_agents/DEPENDENCIES.md` — pytaskwarrior relationship and boundary rules
- `doc_agents/MCP_INTERFACE.md` — available tools and resources
- `doc_agents/PROFILES.md` — profile system, inheritance, skills
- `doc_agents/ADRs.md` — architectural decisions not to reopen

## Keeping Docs Current

If you modify code, update the corresponding doc if observable behavior changes:

- `taskmajor/profiles/` → `doc_agents/PROFILES.md`
- `taskmajor/mcp/tools/` or `taskmajor/mcp/resources/` → `doc_agents/MCP_INTERFACE.md`
- `taskmajor/bootstrap/` or `taskmajor/domains/` → `doc_agents/ARCHITECTURE.md`
- pytaskwarrior interface → `doc_agents/DEPENDENCIES.md`
