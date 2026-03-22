from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ssh_mcp.ssh_sessions import SessionManager


mcp = FastMCP("ssh-mcp")
sessions = SessionManager()


@mcp.tool()
def ssh_session_open(
    host: str,
    username: str,
    password: str,
    session_id: str | None = None,
    port: int = 22,
    connect_timeout_s: int = 10,
    encoding: str = "utf-8",
    term: str = "xterm",
    width: int = 160,
    height: int = 48,
) -> dict[str, Any]:
    """Open a persistent interactive SSH shell session and keep it available for later calls."""
    arguments = {
        "host": host,
        "username": username,
        "password": password,
        "session_id": session_id,
        "port": port,
        "connect_timeout_s": connect_timeout_s,
        "encoding": encoding,
        "term": term,
        "width": width,
        "height": height,
    }
    return sessions.open_session(arguments)


@mcp.tool()
def ssh_session_send(
    session_id: str,
    command: str,
    append_newline: bool = True,
    wait_for_ms: int = 1500,
    quiet_ms: int = 250,
    max_output_chars: int = 65536,
) -> dict[str, Any]:
    """Send text into an existing SSH shell session, then collect output until the stream goes quiet."""
    return sessions.send(
        {
            "session_id": session_id,
            "command": command,
            "append_newline": append_newline,
            "wait_for_ms": wait_for_ms,
            "quiet_ms": quiet_ms,
            "max_output_chars": max_output_chars,
        }
    )


@mcp.tool()
def ssh_session_read(
    session_id: str,
    wait_for_ms: int = 0,
    quiet_ms: int = 250,
    max_output_chars: int = 65536,
) -> dict[str, Any]:
    """Read any buffered output from an SSH session without sending new input."""
    return sessions.read(
        {
            "session_id": session_id,
            "wait_for_ms": wait_for_ms,
            "quiet_ms": quiet_ms,
            "max_output_chars": max_output_chars,
        }
    )


@mcp.tool()
def ssh_session_list() -> dict[str, Any]:
    """List all currently open SSH sessions."""
    return sessions.list_sessions()


@mcp.tool()
def ssh_session_close(session_id: str) -> dict[str, Any]:
    """Close a persistent SSH session and release its resources."""
    return sessions.close({"session_id": session_id})


def main() -> int:
    mcp.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
