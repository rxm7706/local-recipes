"""Stdio JSON-RPC MCP startup probe (Story 103.1, AD-4).

The production ``McpProbePort``: start one declared MCP server exactly as an
agent would launch it from the home's rendered ``.mcp.json`` (the command and
args as written, the entry's ``env`` merged over the caller's environment, the
home as working directory), complete the MCP lifecycle's first two requests
as newline-delimited JSON-RPC over stdio -- ``initialize``, then
``notifications/initialized`` and ``tools/list`` once the ``initialize``
result has arrived -- and report one of six outcomes. It imports no MCP SDK,
so it judges any declared server the same way, and it never raises: every
failure is an outcome.

Process discipline. The child starts in its own session
(``start_new_session=True``), so its pid is its process-group id and a server
launched through a wrapper (``npx``, ``uvx``, ``pixi run``, a shell script) is
stopped together with every process it spawned: SIGTERM, a short grace, then
SIGKILL unconditionally, then the child is reaped -- once, in
``probe_server``'s ``finally``, on every path. Stdout is read against the
remaining deadline (``selectors`` on POSIX; a reader thread and a queue on
Windows, where ``selectors`` takes no pipe fd), stderr is read concurrently by
a thread so a chatty server cannot block on a full pipe, and the last 2 KiB of
stderr travel with the result (``core.mcp_probe`` redacts them before they
reach a finding).

Residual risk (recorded on the story spec): the entry's ``env`` values are
passed as written -- the ``${VAR}`` expansion Claude Code applies to
``.mcp.json`` is not applied here.
"""

from __future__ import annotations

import json
import os
import queue
import selectors
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import Literal

from pyforge.marshal.ports.mcp_probe import McpProbePort, McpProbeResult

MCP_PROBE_TIMEOUT_S = 15.0
_STDERR_TAIL_MAX = 2048
_PROTOCOL_VERSION = "2025-06-18"
_CLIENT_NAME = "marshal-preflight"
_READ_CHUNK = 4096
# One wait slice: how long a read blocks before the child's liveness is re-checked.
_POLL_SLICE_S = 0.05
# How long an exit is awaited after the child closed a pipe without replying.
_CLOSE_GRACE_S = 1.0
# SIGTERM to SIGKILL, and the final reap.
_TERM_GRACE_S = 1.0
_REAP_TIMEOUT_S = 2.0
_INIT_ID = 1
_TOOLS_ID = 2

_ReadError = Literal["exited", "timed-out", "bad-reply", "error-reply"]

_INITIALIZE: dict[str, object] = {
    "jsonrpc": "2.0",
    "id": _INIT_ID,
    "method": "initialize",
    "params": {
        "protocolVersion": _PROTOCOL_VERSION,
        "capabilities": {},
        "clientInfo": {"name": _CLIENT_NAME, "version": "0"},
    },
}
_INITIALIZED: dict[str, object] = {"jsonrpc": "2.0", "method": "notifications/initialized"}
_TOOLS_LIST: dict[str, object] = {"jsonrpc": "2.0", "id": _TOOLS_ID, "method": "tools/list", "params": {}}


def _merge_env(base: Mapping[str, str], overlay: Mapping[str, str]) -> dict[str, str]:
    """The entry's ``env`` (``overlay``) over the caller's environment (``base``), as Claude Code merges them."""
    merged = dict(base)
    merged.update(overlay)
    return merged


def _clip(text: str) -> str:
    return text[-_STDERR_TAIL_MAX:]


def _append_tail(tail: list[str], chunk: str) -> None:
    tail[0] = _clip(tail[0] + chunk)


def _stderr_reader_fd(fd: int, tail: list[str], stop: threading.Event) -> None:
    """Read stderr until EOF (or ``stop``), keeping the last 2 KiB in ``tail[0]``.

    A blocked read returns once every writer has closed the pipe, which the process-group stop guarantees for
    every member of the child's group; ``stop`` only keeps the loop from reading on after that.
    """
    while not stop.is_set():
        try:
            chunk = os.read(fd, _READ_CHUNK)
        except OSError:
            break
        if not chunk:
            break
        _append_tail(tail, chunk.decode("utf-8", errors="replace"))


class _SelectorChunks:
    """POSIX stdout source: ``selectors`` waits for readable data, ``os.read`` takes one chunk."""

    def __init__(self, fd: int) -> None:
        self._fd = fd
        self._eof = False
        self._selector = selectors.DefaultSelector()
        self._selector.register(fd, selectors.EVENT_READ)

    def next_chunk(self, timeout: float) -> bytes | None:
        """A chunk; ``b""`` at EOF (from then on, without waiting); ``None`` when nothing arrived in ``timeout``."""
        if self._eof:
            return b""
        if not self._selector.select(timeout=max(timeout, 0.0)):
            return None
        try:
            chunk = os.read(self._fd, _READ_CHUNK)
        except OSError:
            chunk = b""
        if not chunk:
            # EOF stays readable forever: unregister so no caller can spin on it.
            self._eof = True
            self._selector.unregister(self._fd)
        return chunk

    def busy(self) -> bool:
        return False

    def close(self) -> None:
        self._selector.close()


class _ThreadChunks:
    """Windows stdout source: ``selectors`` takes no pipe fd there, so a reader thread feeds a queue."""

    def __init__(self, fd: int) -> None:
        self._chunks: queue.Queue[bytes] = queue.Queue()
        self._eof = False
        self._thread = threading.Thread(target=self._pump, args=(fd,), name="marshal-mcp-probe-stdout", daemon=True)
        self._thread.start()

    def _pump(self, fd: int) -> None:
        while True:
            try:
                chunk = os.read(fd, _READ_CHUNK)
            except OSError:
                chunk = b""
            self._chunks.put(chunk)
            if not chunk:
                return

    def next_chunk(self, timeout: float) -> bytes | None:
        if self._eof:
            return b""
        try:
            chunk = self._chunks.get(timeout=max(timeout, 0.0))
        except queue.Empty:
            return None
        if not chunk:
            self._eof = True
        return chunk

    def busy(self) -> bool:
        return self._thread.is_alive()

    def close(self) -> None:
        self._thread.join(timeout=_POLL_SLICE_S)


_ChunkSource = _SelectorChunks | _ThreadChunks


def _open_chunks(fd: int) -> _ChunkSource:
    if sys.platform == "win32":
        return _ThreadChunks(fd)
    return _SelectorChunks(fd)


def _parse_buffered(buf: bytearray, *, expected_id: int) -> tuple[dict[str, object] | None, _ReadError | None, str]:
    """Consume complete lines from ``buf``: ``(reply, error, detail)`` for the request ``expected_id``.

    A line that is not a JSON object is ``bad-reply`` (the line is the detail); a JSON-RPC ``error`` addressed
    to our request -- its ``id``, or ``null`` for a request the server could not parse -- is ``error-reply``;
    a notification, a server-initiated request or another request's reply is skipped. ``(None, None, "")``
    means no complete reply is buffered yet.
    """
    while True:
        newline = buf.find(b"\n")
        if newline < 0:
            return None, None, ""
        line = bytes(buf[:newline]).decode("utf-8", errors="replace").strip()
        del buf[: newline + 1]
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            return None, "bad-reply", _clip(f"stdout line is not JSON-RPC: {line}")
        if not isinstance(message, dict):
            return None, "bad-reply", _clip(f"stdout line is not a JSON-RPC object: {line}")
        if "method" in message:
            continue
        message_id = message.get("id")
        if message.get("error") is not None and message_id in (expected_id, None):
            return None, "error-reply", _clip(f"JSON-RPC error: {json.dumps(message.get('error'))}")
        if message_id != expected_id:
            continue
        return message, None, ""


def _drain_available(chunks: _ChunkSource, buf: bytearray, *, deadline: float) -> None:
    """Take what is already in the pipe; never wait past one slice for more, never past ``deadline``."""
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return
        chunk = chunks.next_chunk(min(remaining, _POLL_SLICE_S))
        if not chunk:
            return
        buf.extend(chunk)


def _wait_exit(proc: subprocess.Popen[bytes], timeout: float) -> int | None:
    """The child's exit code if it exits within ``timeout`` (reaping it), else ``None``."""
    try:
        return proc.wait(timeout=max(timeout, 0.0))
    except subprocess.TimeoutExpired:
        return None


def _read_reply(
    proc: subprocess.Popen[bytes],
    chunks: _ChunkSource,
    buf: bytearray,
    *,
    deadline: float,
    expected_id: int,
) -> tuple[dict[str, object] | None, _ReadError | None, str]:
    """The reply whose ``id`` is ``expected_id``, read against ``deadline``: ``(reply, error, detail)``.

    Lines are parsed as they arrive. When the child exits, what it already wrote is read and parsed first --
    a server that answers and then exits is still read -- and only then is it ``exited``. When the child closes
    stdout but lives on it can never answer: its exit is awaited for a short grace (``exited``), else the closed
    pipe is ``bad-reply``. Every wait is bounded by ``deadline`` (``timed-out``).
    """
    while True:
        reply, error, detail = _parse_buffered(buf, expected_id=expected_id)
        if reply is not None or error is not None:
            return reply, error, detail
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None, "timed-out", ""
        chunk = chunks.next_chunk(min(remaining, _POLL_SLICE_S))
        if chunk:
            buf.extend(chunk)
            continue
        if chunk is None and proc.poll() is None:
            continue
        # The child exited, or closed its stdout: take the rest, judge it, then report why there is no reply.
        _drain_available(chunks, buf, deadline=deadline)
        reply, error, detail = _parse_buffered(buf, expected_id=expected_id)
        if reply is not None or error is not None:
            return reply, error, detail
        if proc.poll() is None and _wait_exit(proc, min(remaining, _CLOSE_GRACE_S)) is None:
            return None, "bad-reply", "the server closed its stdout before replying"
        return None, "exited", ""


def _write(proc: subprocess.Popen[bytes], message: Mapping[str, object]) -> bool:
    if proc.stdin is None:
        return False
    try:
        proc.stdin.write((json.dumps(message) + "\n").encode("utf-8"))
        proc.stdin.flush()
    except OSError:
        return False
    return True


def _handshake(
    proc: subprocess.Popen[bytes],
    chunks: _ChunkSource,
    *,
    server_name: str,
    deadline: float,
) -> McpProbeResult:
    """Run initialize -> notifications/initialized -> tools/list; the caller fills in the stderr tail."""
    buf = bytearray()

    def closed_stdin() -> McpProbeResult:
        remaining = deadline - time.monotonic()
        code = _wait_exit(proc, min(max(remaining, 0.0), _CLOSE_GRACE_S))
        if code is None:
            return McpProbeResult(
                outcome="bad-reply",
                server_name=server_name,
                detail="the server closed its stdin before replying",
            )
        return McpProbeResult(outcome="exited", server_name=server_name, exit_code=code)

    def failed(error: _ReadError, detail: str, **carried: object) -> McpProbeResult:
        exit_code = proc.returncode if error == "exited" else None
        return McpProbeResult(
            outcome=error,
            server_name=server_name,
            exit_code=exit_code,
            detail=detail,
            **carried,  # type: ignore[arg-type]
        )

    if not _write(proc, _INITIALIZE):
        return closed_stdin()
    reply, error, detail = _read_reply(proc, chunks, buf, deadline=deadline, expected_id=_INIT_ID)
    if error is not None or reply is None:
        return failed(error or "bad-reply", detail)
    result = reply.get("result")
    server_info = result.get("serverInfo") if isinstance(result, dict) else None
    if not isinstance(server_info, dict):
        return failed("bad-reply", "initialize result carries no serverInfo object")
    reported = server_info.get("name")
    reported_name = reported if isinstance(reported, str) else None

    if not _write(proc, _INITIALIZED) or not _write(proc, _TOOLS_LIST):
        return closed_stdin()
    reply, error, detail = _read_reply(proc, chunks, buf, deadline=deadline, expected_id=_TOOLS_ID)
    if error is not None or reply is None:
        return failed(error or "bad-reply", detail, reported_server_name=reported_name)
    result = reply.get("result")
    tools = result.get("tools") if isinstance(result, dict) else None
    if not isinstance(tools, list):
        return failed("bad-reply", "tools/list result carries no tools list", reported_server_name=reported_name)
    names = tuple(tool["name"] for tool in tools if isinstance(tool, dict) and isinstance(tool.get("name"), str))
    return McpProbeResult(
        outcome="started",
        server_name=server_name,
        tool_count=len(tools),
        reported_server_name=reported_name,
        tool_names=names,
    )


def _spawn(argv: list[str], *, cwd: str, env: Mapping[str, str]) -> subprocess.Popen[bytes]:
    """Start the server with every pipe ours, in its own process group (session on POSIX)."""
    if sys.platform == "win32":
        return subprocess.Popen(
            argv,
            cwd=cwd,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
    return subprocess.Popen(
        argv,
        cwd=cwd,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
        start_new_session=True,
    )


def _signal_child(proc: subprocess.Popen[bytes], method: Literal["terminate", "kill"]) -> None:
    try:
        getattr(proc, method)()
    except OSError:
        pass


def _killpg(pgid: int, sig: int) -> bool:
    """Signal a whole process group. ``True`` when it was signalled or is already gone; ``False`` on any other error."""
    try:
        os.killpg(pgid, sig)
    except ProcessLookupError:
        return True
    except OSError:
        return False
    return True


def _stop_windows(proc: subprocess.Popen[bytes]) -> None:
    ctrl_break = getattr(signal, "CTRL_BREAK_EVENT", None)
    if ctrl_break is not None:
        try:
            # Reaches the whole CREATE_NEW_PROCESS_GROUP console group, not just the direct child.
            os.kill(proc.pid, ctrl_break)
        except OSError:
            pass
    _signal_child(proc, "terminate")
    if _wait_exit(proc, _TERM_GRACE_S) is None:
        _signal_child(proc, "kill")
        _wait_exit(proc, _REAP_TIMEOUT_S)


def _stop_process_group(proc: subprocess.Popen[bytes]) -> None:
    """Stop everything the probe started -- SIGTERM, a grace, SIGKILL unconditionally -- then reap the child.

    ``start_new_session=True`` made the child the leader of its own session and group, so ``proc.pid`` IS the
    group id; it is never looked up with ``getpgid``, which fails once the child is reaped. SIGKILL is sent
    whether or not the grace was enough, so a member that ignores SIGTERM (or was spawned by a wrapper that
    already exited) dies with the rest. The grace reaps the leader if it exits early; the group id stays valid
    while any member lives, and a group with no members raises ``ProcessLookupError``, which is swallowed. When
    ``killpg`` itself fails for another reason the direct child is signalled instead. Never raises.
    """
    if sys.platform == "win32":
        _stop_windows(proc)
        return
    pgid = proc.pid
    if not _killpg(pgid, signal.SIGTERM):
        _signal_child(proc, "terminate")
    _wait_exit(proc, _TERM_GRACE_S)
    if not _killpg(pgid, signal.SIGKILL):
        _signal_child(proc, "kill")
    if _wait_exit(proc, _REAP_TIMEOUT_S) is None:
        _signal_child(proc, "kill")
        _wait_exit(proc, _REAP_TIMEOUT_S)


def _close_pipes(proc: subprocess.Popen[bytes], *, keep_stdout: bool, keep_stderr: bool) -> None:
    """Close our ends of the pipes -- except one a reader thread is still blocked on (it closes at EOF)."""
    streams = [proc.stdin]
    if not keep_stdout:
        streams.append(proc.stdout)
    if not keep_stderr:
        streams.append(proc.stderr)
    for stream in streams:
        if stream is None:
            continue
        try:
            stream.close()
        except OSError:
            pass


def _pipe_fd(stream: object) -> int:
    fileno = getattr(stream, "fileno", None)
    if fileno is None:
        raise OSError("the child has no such pipe")
    return int(fileno())


class StdioMcpProbe(McpProbePort):
    """Production ``McpProbePort`` using newline-delimited JSON-RPC over stdio."""

    def probe_server(
        self,
        *,
        server_name: str,
        command: str,
        args: tuple[str, ...],
        env: Mapping[str, str],
        cwd: str,
        timeout_s: float,
    ) -> McpProbeResult:
        deadline = time.monotonic() + timeout_s
        stderr_tail = [""]
        stop_stderr = threading.Event()
        stderr_reader: threading.Thread | None = None
        chunks: _ChunkSource | None = None

        try:
            proc = _spawn([command, *args], cwd=cwd, env=_merge_env(os.environ, env))
        except (OSError, ValueError) as exc:
            return McpProbeResult(
                outcome="spawn-failed",
                server_name=server_name,
                detail=_clip(f"{type(exc).__name__}: {exc}"),
            )

        try:
            stderr_reader = threading.Thread(
                target=_stderr_reader_fd,
                args=(_pipe_fd(proc.stderr), stderr_tail, stop_stderr),
                name="marshal-mcp-probe-stderr",
                daemon=True,
            )
            stderr_reader.start()
            chunks = _open_chunks(_pipe_fd(proc.stdout))
            result = _handshake(proc, chunks, server_name=server_name, deadline=deadline)
        except Exception as exc:  # noqa: BLE001 -- the probe is a verdict, never a crash
            detail = _clip(f"{type(exc).__name__}: {exc}")
            if proc.poll() is not None:
                result = McpProbeResult(
                    outcome="exited", server_name=server_name, exit_code=proc.returncode, detail=detail
                )
            else:
                result = McpProbeResult(outcome="bad-reply", server_name=server_name, detail=detail)
        finally:
            # The one stop, on every path: the group first (which closes every pipe's write end), then the readers.
            _stop_process_group(proc)
            stop_stderr.set()
            if chunks is not None:
                chunks.close()
            if stderr_reader is not None:
                stderr_reader.join(timeout=_CLOSE_GRACE_S)
            _close_pipes(
                proc,
                keep_stdout=chunks is not None and chunks.busy(),
                keep_stderr=stderr_reader is not None and stderr_reader.is_alive(),
            )
        # Built after the stop and the joins, so the tail carries everything the server wrote.
        return replace(result, stderr_tail=stderr_tail[0])


def default_mcp_probe() -> McpProbePort:
    return StdioMcpProbe()


def probe_server_from_rendered(
    *,
    server_name: str,
    rendered: Mapping[str, object],
    home: Path,
    timeout_s: float = MCP_PROBE_TIMEOUT_S,
    probe: McpProbePort | None = None,
) -> McpProbeResult:
    """Probe one ``mcpServers`` entry as the home's ``.mcp.json`` renders it (AD-43: the home's file, nothing else)."""
    command = rendered.get("command")
    if not isinstance(command, str) or not command:
        return McpProbeResult(
            outcome="spawn-failed",
            server_name=server_name,
            detail="the rendered entry has no command",
        )
    raw_args = rendered.get("args")
    args: tuple[str, ...] = ()
    if isinstance(raw_args, list):
        args = tuple(str(a) for a in raw_args)
    raw_env = rendered.get("env")
    env: dict[str, str] = {}
    if isinstance(raw_env, dict):
        env = {str(k): str(v) for k, v in raw_env.items()}
    port = probe if probe is not None else StdioMcpProbe()
    return port.probe_server(
        server_name=server_name,
        command=command,
        args=args,
        env=env,
        cwd=str(home),
        timeout_s=timeout_s,
    )
