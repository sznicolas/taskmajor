# MCP JSON configuration (fastmcp)

This project provides a small automation to generate MCP artifacts and a client configuration compatible with MCP clients (Claude Desktop, VS Code, Cursor).

Generating locally

1. Ensure dependencies: Python 3.11+, pip, and optionally fastmcp.
2. From the repository root run:

```bash
# regenerate artifacts and generate mcp-json for clients
./scripts/regen_mcp.sh
```

This writes:
- `artifacts/mcp_components.json` and `docs/mcp_components.md` (from `scripts/extract_mcp_static.py`)
- `artifacts/mcp_mcpjson.json` (output from `fastmcp install mcp-json`)

Using the generated config

- Add the generated block from `artifacts/mcp_mcpjson.json` into your client config (e.g. `~/.claude/claude_desktop_config.json`, `~/.cursor/mcp.json`, or `.vscode/mcp.json`):

```json
{
  "mcpServers": {
    // paste contents of artifacts/mcp_mcpjson.json here
  }
}
```

CI integration

A GitHub Actions workflow `.github/workflows/mcp-regenerate.yml` is included to regenerate the artifacts and fail the run if the generated files differ from the committed versions. This encourages contributors to regenerate artifacts locally and commit them.

Notes

- The script will attempt a user-level pip install of `fastmcp` if the CLI is not present.
- Prefer to run `fastmcp install mcp-json fastmcp.json` if you add a `fastmcp.json` file to customize dependencies or entrypoint.
