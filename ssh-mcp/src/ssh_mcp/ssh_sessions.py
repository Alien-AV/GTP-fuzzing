from __future__ import annotations

import re
import socket
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass
from typing import Any

import paramiko


def _coerce_text(value: Any, *, default: str = "", minimum: int | None = None, maximum: int | None = None) -> str:
    text = default if value is None else str(value)
    if minimum is not None and len(text) < minimum:
        raise ValueError(f"value must be at least {minimum} characters")
    if maximum is not None and len(text) > maximum:
        raise ValueError(f"value must be at most {maximum} characters")
    return text


def _coerce_int(value: Any, *, default: int, minimum: int | None = None, maximum: int | None = None) -> int:
    if value is None:
        number = default
    else:
        number = int(value)
    if minimum is not None and number < minimum:
        raise ValueError(f"value must be >= {minimum}")
    if maximum is not None and number > maximum:
        raise ValueError(f"value must be <= {maximum}")
    return number


def _coerce_bool(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    raise ValueError("value must be boolean")


@dataclass(slots=True)
class SessionSnapshot:
    session_id: str
    host: str
    port: int
    username: str
    created_at: float
    last_activity_at: float
    closed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "created_at": self.created_at,
            "last_activity_at": self.last_activity_at,
            "closed": self.closed,
        }


class PersistentSshSession:
    def __init__(
        self,
        *,
        session_id: str,
        host: str,
        port: int,
        username: str,
        password: str,
        connect_timeout_s: int,
        encoding: str,
        term: str,
        width: int,
        height: int,
    ) -> None:
        self.session_id = session_id
        self.host = host
        self.port = port
        self.username = username
        self.encoding = encoding
        self._created_at = time.time()
        self._last_activity_at = self._created_at

        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self._client.connect(
            hostname=host,
            port=port,
            username=username,
            password=password,
            timeout=connect_timeout_s,
            banner_timeout=connect_timeout_s,
            auth_timeout=connect_timeout_s,
            channel_timeout=connect_timeout_s,
            look_for_keys=False,
            allow_agent=False,
        )
        transport = self._client.get_transport()
        if transport is None or not transport.is_active():
            raise RuntimeError("SSH transport did not become active")
        transport.set_keepalive(15)

        self._channel = self._client.invoke_shell(term=term, width=width, height=height)

        self._write_lock = threading.RLock()
        self._interaction_lock = threading.RLock()
        self._buffer_ready = threading.Condition(threading.Lock())
        self._chunks: deque[str] = deque()
        self._closed = False
        self._close_reason: str | None = None
        self._reader = threading.Thread(target=self._reader_loop, name=f"ssh-reader-{session_id}", daemon=True)
        self._reader.start()

    @property
    def closed(self) -> bool:
        return self._closed

    def snapshot(self) -> SessionSnapshot:
        return SessionSnapshot(
            session_id=self.session_id,
            host=self.host,
            port=self.port,
            username=self.username,
            created_at=self._created_at,
            last_activity_at=self._last_activity_at,
            closed=self._closed,
        )

    def _touch(self) -> None:
        self._last_activity_at = time.time()

    def _reader_loop(self) -> None:
        while True:
            if self._closed:
                return
            try:
                if not self._channel.recv_ready():
                    if self._channel.closed or self._channel.eof_received:
                        self._mark_closed("remote channel closed")
                        return
                    time.sleep(0.05)
                    continue

                chunk = self._channel.recv(4096)
                if not chunk:
                    self._mark_closed("remote channel closed")
                    return

                decoded = chunk.decode(self.encoding, errors="replace")
                with self._buffer_ready:
                    self._chunks.append(decoded)
                    self._touch()
                    self._buffer_ready.notify_all()
            except socket.timeout:
                continue
            except EOFError:
                self._mark_closed("remote channel closed")
                return
            except OSError as exc:
                if self._channel.closed or self._channel.eof_received:
                    self._mark_closed("remote channel closed")
                    return
                if getattr(exc, "errno", None) in {11, 35, 10035}:
                    time.sleep(0.05)
                    continue
                self._mark_closed(f"reader stopped: {exc}")
                return
            except Exception as exc:  # pragma: no cover
                if self._channel.closed or self._channel.eof_received:
                    self._mark_closed("remote channel closed")
                else:
                    self._mark_closed(f"reader stopped: {exc}")
                return

    def _mark_closed(self, reason: str) -> None:
        with self._buffer_ready:
            if self._closed:
                return
            self._closed = True
            self._close_reason = reason
            self._buffer_ready.notify_all()

    def send(
        self,
        command: str,
        *,
        append_newline: bool,
        wait_for_ms: int,
        quiet_ms: int,
        max_output_chars: int,
    ) -> dict[str, Any]:
        self._ensure_open()
        with self._interaction_lock:
            if not append_newline:
                payload = command
                with self._write_lock:
                    self._channel.sendall(payload.encode(self.encoding, errors="replace"))
                    self._touch()
                output = self._read_until_quiet(
                    wait_for_ms=wait_for_ms,
                    quiet_ms=quiet_ms,
                    max_output_chars=max_output_chars,
                )
                return {"sent": command, "exit_status": None, **output}

            token = uuid.uuid4().hex
            marker_prefix = f"__MCP_DONE__{token}__"
            marker_pattern = re.compile(re.escape(marker_prefix) + r"(?P<status>\d+)__\r?\n?")
            payload = f"{command}\nprintf '\\n{marker_prefix}%s__\\n' \"$?\"\n"
            with self._write_lock:
                self._channel.sendall(payload.encode(self.encoding, errors="replace"))
                self._touch()
            output, exit_status, truncated = self._read_until_marker(
                marker_pattern=marker_pattern,
                wait_for_ms=wait_for_ms,
                max_output_chars=max_output_chars,
            )
            return {
                "sent": command,
                "output": output,
                "exit_status": exit_status,
                "truncated": truncated,
                "closed": self._closed,
                "close_reason": self._close_reason,
            }

    def read(self, *, wait_for_ms: int, quiet_ms: int, max_output_chars: int) -> dict[str, Any]:
        self._ensure_open()
        with self._interaction_lock:
            result = self._read_until_quiet(
                wait_for_ms=wait_for_ms,
                quiet_ms=quiet_ms,
                max_output_chars=max_output_chars,
            )
        return result

    def _read_until_quiet(self, *, wait_for_ms: int, quiet_ms: int, max_output_chars: int) -> dict[str, Any]:
        deadline = time.monotonic() + max(wait_for_ms, 0) / 1000.0
        quiet_deadline: float | None = None
        collected: list[str] = []
        collected_chars = 0

        with self._buffer_ready:
            while True:
                while self._chunks and collected_chars < max_output_chars:
                    chunk = self._chunks.popleft()
                    remaining = max_output_chars - collected_chars
                    piece = chunk[:remaining]
                    collected.append(piece)
                    collected_chars += len(piece)
                    quiet_deadline = time.monotonic() + max(quiet_ms, 0) / 1000.0
                    if len(piece) < len(chunk):
                        self._chunks.appendleft(chunk[remaining:])
                        break

                if collected_chars >= max_output_chars:
                    break

                now = time.monotonic()
                if quiet_deadline is not None and now >= quiet_deadline:
                    break
                if quiet_deadline is None and now >= deadline:
                    break
                if self._closed and not self._chunks:
                    break

                next_deadline = quiet_deadline if quiet_deadline is not None else deadline
                timeout = max(0.0, next_deadline - now)
                self._buffer_ready.wait(timeout=timeout)

        output = "".join(collected)
        self._touch()
        return {
            "output": output,
            "truncated": collected_chars >= max_output_chars,
            "closed": self._closed,
            "close_reason": self._close_reason,
        }

    def _read_until_marker(
        self,
        *,
        marker_pattern: re.Pattern[str],
        wait_for_ms: int,
        max_output_chars: int,
    ) -> tuple[str, int | None, bool]:
        deadline = time.monotonic() + max(wait_for_ms, 0) / 1000.0
        collected = ""

        with self._buffer_ready:
            while True:
                while self._chunks and len(collected) < max_output_chars:
                    chunk = self._chunks.popleft()
                    remaining = max_output_chars - len(collected)
                    piece = chunk[:remaining]
                    collected += piece
                    if len(piece) < len(chunk):
                        self._chunks.appendleft(chunk[remaining:])

                    match = marker_pattern.search(collected)
                    if match:
                        before = collected[: match.start()]
                        after = collected[match.end() :]
                        if after:
                            self._chunks.appendleft(after)
                        self._touch()
                        return before, int(match.group("status")), False

                    if len(collected) >= max_output_chars:
                        self._touch()
                        return collected, None, True

                now = time.monotonic()
                if now >= deadline:
                    self._touch()
                    raise TimeoutError("timed out waiting for command completion marker")
                if self._closed and not self._chunks:
                    self._touch()
                    raise RuntimeError(self._close_reason or "session closed while waiting for command completion")

                self._buffer_ready.wait(timeout=max(0.0, deadline - now))

    def close(self) -> dict[str, Any]:
        with self._write_lock:
            self._mark_closed("session closed by client")
            try:
                self._channel.close()
            finally:
                self._client.close()
        return {"session_id": self.session_id, "closed": True, "close_reason": self._close_reason}

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError(self._close_reason or "session is closed")


class SessionManager:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._sessions: dict[str, PersistentSshSession] = {}

    def open_session(self, arguments: dict[str, Any]) -> dict[str, Any]:
        host = _coerce_text(arguments.get("host"), minimum=1)
        port = _coerce_int(arguments.get("port"), default=22, minimum=1, maximum=65535)
        username = _coerce_text(arguments.get("username"), minimum=1)
        password = _coerce_text(arguments.get("password"), minimum=1)
        connect_timeout_s = _coerce_int(arguments.get("connect_timeout_s"), default=10, minimum=1, maximum=120)
        encoding = _coerce_text(arguments.get("encoding"), default="utf-8", minimum=1, maximum=32)
        term = _coerce_text(arguments.get("term"), default="xterm", minimum=1, maximum=64)
        width = _coerce_int(arguments.get("width"), default=160, minimum=40, maximum=500)
        height = _coerce_int(arguments.get("height"), default=48, minimum=10, maximum=300)
        session_id = _coerce_text(arguments.get("session_id"), default=f"ssh-{uuid.uuid4().hex[:12]}", minimum=1, maximum=80)

        session = PersistentSshSession(
            session_id=session_id,
            host=host,
            port=port,
            username=username,
            password=password,
            connect_timeout_s=connect_timeout_s,
            encoding=encoding,
            term=term,
            width=width,
            height=height,
        )

        with self._lock:
            if session_id in self._sessions:
                session.close()
                raise ValueError(f"session_id already exists: {session_id}")
            self._sessions[session_id] = session

        warmup = session.read(wait_for_ms=1500, quiet_ms=250, max_output_chars=65536)
        return {"session": session.snapshot().to_dict(), "initial_output": warmup["output"]}

    def list_sessions(self) -> dict[str, Any]:
        with self._lock:
            sessions = [session.snapshot().to_dict() for session in self._sessions.values()]
        return {"sessions": sessions}

    def send(self, arguments: dict[str, Any]) -> dict[str, Any]:
        session = self._get_session(arguments)
        command = _coerce_text(arguments.get("command"), minimum=0)
        append_newline = _coerce_bool(arguments.get("append_newline"), default=True)
        wait_for_ms = _coerce_int(arguments.get("wait_for_ms"), default=1500, minimum=0, maximum=120000)
        quiet_ms = _coerce_int(arguments.get("quiet_ms"), default=250, minimum=0, maximum=30000)
        max_output_chars = _coerce_int(arguments.get("max_output_chars"), default=65536, minimum=1, maximum=1_000_000)
        result = session.send(
            command,
            append_newline=append_newline,
            wait_for_ms=wait_for_ms,
            quiet_ms=quiet_ms,
            max_output_chars=max_output_chars,
        )
        return {"session": session.snapshot().to_dict(), **result}

    def read(self, arguments: dict[str, Any]) -> dict[str, Any]:
        session = self._get_session(arguments)
        wait_for_ms = _coerce_int(arguments.get("wait_for_ms"), default=0, minimum=0, maximum=120000)
        quiet_ms = _coerce_int(arguments.get("quiet_ms"), default=250, minimum=0, maximum=30000)
        max_output_chars = _coerce_int(arguments.get("max_output_chars"), default=65536, minimum=1, maximum=1_000_000)
        result = session.read(wait_for_ms=wait_for_ms, quiet_ms=quiet_ms, max_output_chars=max_output_chars)
        return {"session": session.snapshot().to_dict(), **result}

    def close(self, arguments: dict[str, Any]) -> dict[str, Any]:
        session_id = _coerce_text(arguments.get("session_id"), minimum=1)
        with self._lock:
            session = self._sessions.pop(session_id, None)
        if session is None:
            raise KeyError(f"unknown session_id: {session_id}")
        return session.close()

    def close_all(self) -> None:
        with self._lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()
        for session in sessions:
            session.close()

    def _get_session(self, arguments: dict[str, Any]) -> PersistentSshSession:
        session_id = _coerce_text(arguments.get("session_id"), minimum=1)
        with self._lock:
            session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(f"unknown session_id: {session_id}")
        return session
