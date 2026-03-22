# ssh-mcp

Minimal MCP server for persistent SSH shell sessions.

## Minimal Files To Copy

If you want the smallest subset that can be copied elsewhere and still installed with `pip`, copy only:

- `pyproject.toml`
- `src/ssh_mcp/__init__.py`
- `src/ssh_mcp/server.py`
- `src/ssh_mcp/ssh_sessions.py`

## Local Install

Install for the current Windows user:

```powershell
cd C:\wherever\ssh-mcp
py -3 -m pip install --user .
```

## Codex App Setup

In the Windows Codex app custom MCP screen use:

- Name: `ssh-mcp`
- Transport: `STDIO`
- Command to launch: `py`
- Arguments: `-3`, `-m`, `ssh_mcp.server`
- Environment variables: leave empty
- Environment variable passthrough: leave empty
- Working directory: `C:\wherever\ssh-mcp`

If `py -3` is not available, use the full path to `python.exe` instead.

## Developer Notes

Everything else moved to [CODING.md](CODING.md).
