"""Stdio JSON-RPC MCP startup probe (Story 103.1, AD-4).

Imports no MCP SDK -- any declared server is judged the same way.
"""

from __future__ import annotations

import json
import os
import selectors
import signal
import subprocess
import sys
import threading
from collections.abc import Mapping
from pathlib import Path

from pyforge.marshal.ports.mcp_probe import McpProbePort, McpProbeResult

MCP_PROBE_TIMEOUT_S = 15.0
_STDERR_TAIL_MAX = 2048
_PROTOCOL_VERSION = "2025-06-18"
_CLIENT_NAME = "marshal-preflight"
_READ_CHUNK = 4096


def _merge_env(base: Mapping[str, str], overlay: Mapping[str, str]) -> dict[str, str]:
    merged = dict(os.environ)
    merged.update(base)
    merged.update(overlay)
    return merged


def _append_tail(tail: list[str], chunk: str) -> None:
    tail[0] = (tail[0] + chunk)[-_STDERR_TAIL_MAX:]


def _stderr_reader_fd(fd: int, tail: list[str], stop: threading.Event) -> None:
    while not stop.is_set():
        try:
            chunk = os.read(fd, _READ_CHUNK)
        except OSError:
            break
        if not chunk:
            break
        _append_tail(tail, chunk.decode("utf-8", errors="replace"))


def _drain_stdout(proc: subprocess.Popen[str], buf: bytearray) -> None:
    if proc.stdout is None:
        return
    try:
        fd = proc.stdout.fileno()
    except (AttributeError, ValueError, OSError):
        return
    while True:
        try:
            chunk = os.read(fd, _READ_CHUNK)
        except OSError:
            break
        if not chunk:
            break
        buf.extend(chunk)


def _read_json_line(
    proc: subprocess.Popen[str],
    *,
    deadline: float,
    stderr_tail: list[str],
    expected_id: int | None = None,
    stdout_buf: bytearray,
) -> tuple[dict[str, object] | None, str | None]:
    """Return (parsed object, error tag) where error is bad-reply | error-reply | timed-out | exited."""
    import time

    if proc.stdout is None:
        return None, "bad-reply"

    try:
        fd = proc.stdout.fileno()
    except (AttributeError, ValueError, OSError):
        return None, "bad-reply"

    sel = selectors.DefaultSelector()
    try:
        sel.register(fd, selectors.EVENT_READ)
    except OSError:
        return None, "bad-reply"

    try:
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                _drain_stdout(proc, stdout_buf)
                return None, "exited"

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None, "timed-out"

            events = sel.select(timeout=min(remaining, 0.05))
            if not events:
                continue

            try:
                chunk = os.read(fd, _READ_CHUNK)
            except OSError:
                if proc.poll() is not None:
                    _drain_stdout(proc, stdout_buf)
                    return None, "exited"
                continue

            if not chunk:
                if proc.poll() is not None:
                    _drain_stdout(proc, stdout_buf)
                    return None, "exited"
                continue

            stdout_buf.extend(chunk)
            while True:
                nl = stdout_buf.find(b"\n")
                if nl < 0:
                    break
                line_bytes = stdout_buf[:nl]
                del stdout_buf[: nl + 1]
                line = line_bytes.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                try:
                    parsed = json.loads(line)
                except json.JSONDecodeError:
                    _append_tail(stderr_tail, line + "\n")
                    return None, "bad-reply"
                if not isinstance(parsed, dict):
                    return None, "bad-reply"
                if parsed.get("error") is not None:
                    return None, "error-reply"
                msg_id = parsed.get("id")
                if expected_id is not None and msg_id != expected_id:
                    continue
                if expected_id is not None and msg_id is None:
                    continue
                return parsed, None

        return None, "timed-out"
    finally:
        sel.close()


def _popen_kwargs(*, start_new_session: bool) -> dict[str, object]:
    if sys.platform == "win32":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    if start_new_session:
        return {"start_new_session": True}
    return {}


def _stop_process_group(proc: subprocess.Popen[str]) -> None:
    if sys.platform == "win32":
        try:
            proc.terminate()
        except OSError:
            pass
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            try:
                proc.kill()
            except OSError:
                pass
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass
        return

    pgid: int | None = None
    try:
        pgid = os.getpgid(proc.pid)
    except OSError:
        pgid = None

    if pgid is not None:
        try:
            os.killpg(pgid, signal.SIGTERM)
        except ProcessLookupError:
            try:
                proc.terminate()
            except OSError:
                pass
        except OSError:
            try:
                proc.terminate()
            except OSError:
                pass
    else:
        try:
            proc.terminate()
        except OSError:
            pass

    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        if pgid is not None:
            try:
                os.killpg(pgid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except OSError:
                pass
        try:
            proc.kill()
        except OSError:
            pass
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass


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
        import time

        argv = [command, *args]
        merged = _merge_env({}, env)
        stderr_tail = [""]
        deadline = time.monotonic() + timeout_s
        stdout_buf = bytearray()
        proc: subprocess.Popen[str] | None = None
        reader: threading.Thread | None = None
        stop_stderr = threading.Event()

        try:
            proc = subprocess.Popen(
                argv,
                cwd=cwd,
                env=merged,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,
                bufsize=0,
                **_popen_kwargs(start_new_session=True),
            )
        except OSError as exc:
            return McpProbeResult(
                outcome="spawn-failed",
                server_name=server_name,
                stderr_tail=str(exc)[-_STDERR_TAIL_MAX:],
            )

        assert proc is not None
        if proc.stderr is not None:
            try:
                stderr_fd = proc.stderr.fileno()
            except (AttributeError, ValueError, OSError):
                stderr_fd = None
            if stderr_fd is not None:
                reader = threading.Thread(
                    target=_stderr_reader_fd,
                    args=(stderr_fd, stderr_tail, stop_stderr),
                    daemon=True,
                )
                reader.start()

        def write_line(payload: dict[str, object]) -> bool:
            if proc is None or proc.stdin is None:
                return False
            try:
                proc.stdin.write((json.dumps(payload) + "\n").encode("utf-8"))
                proc.stdin.flush()
            except OSError:
                return False
            return True

        try:
            if not write_line(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": _PROTOCOL_VERSION,
                        "capabilities": {},
                        "clientInfo": {"name": _CLIENT_NAME, "version": "0"},
                    },
                }
            ):
                code = proc.wait(timeout=1) if proc.poll() is None else proc.returncode
                return McpProbeResult(
                    outcome="exited",
                    server_name=server_name,
                    exit_code=code,
                    stderr_tail=stderr_tail[0],
                )

            init_reply, init_err = _read_json_line(
                proc,
                deadline=deadline,
                stderr_tail=stderr_tail,
                expected_id=1,
                stdout_buf=stdout_buf,
            )
            if init_err == "exited":
                code = proc.wait(timeout=1)
                return McpProbeResult(
                    outcome="exited",
                    server_name=server_name,
                    exit_code=code,
                    stderr_tail=stderr_tail[0],
                )
            if init_err is not None:
                outcome = init_err if init_err in ("timed-out", "bad-reply", "error-reply") else "bad-reply"
                return McpProbeResult(
                    outcome=outcome,  # type: ignore[arg-type]
                    server_name=server_name,
                    stderr_tail=stderr_tail[0],
                )
            if init_reply is None:
                return McpProbeResult(
                    outcome="bad-reply",
                    server_name=server_name,
                    stderr_tail=stderr_tail[0],
                )
            init_result = init_reply.get("result")
            if not isinstance(init_result, dict):
                return McpProbeResult(
                    outcome="bad-reply",
                    server_name=server_name,
                    stderr_tail=stderr_tail[0],
                )
            server_info = init_result.get("serverInfo")
            if not isinstance(server_info, dict):
                return McpProbeResult(
                    outcome="bad-reply",
                    server_name=server_name,
                    stderr_tail=stderr_tail[0],
                )

            if not write_line({"jsonrpc": "2.0", "method": "notifications/initialized"}):
                code = proc.wait(timeout=1) if proc.poll() is None else proc.returncode
                return McpProbeResult(
                    outcome="exited",
                    server_name=server_name,
                    exit_code=code,
                    stderr_tail=stderr_tail[0],
                )
            if not write_line({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}):
                code = proc.wait(timeout=1) if proc.poll() is None else proc.returncode
                return McpProbeResult(
                    outcome="exited",
                    server_name=server_name,
                    exit_code=code,
                    stderr_tail=stderr_tail[0],
                )

            tools_reply, tools_err = _read_json_line(
                proc,
                deadline=deadline,
                stderr_tail=stderr_tail,
                expected_id=2,
                stdout_buf=stdout_buf,
            )
            if tools_err == "exited":
                code = proc.wait(timeout=1)
                return McpProbeResult(
                    outcome="exited",
                    server_name=server_name,
                    exit_code=code,
                    stderr_tail=stderr_tail[0],
                )
            if tools_err is not None:
                outcome = tools_err if tools_err in ("timed-out", "bad-reply", "error-reply") else "bad-reply"
                return McpProbeResult(
                    outcome=outcome,  # type: ignore[arg-type]
                    server_name=server_name,
                    stderr_tail=stderr_tail[0],
                )
            if tools_reply is None:
                return McpProbeResult(
                    outcome="bad-reply",
                    server_name=server_name,
                    stderr_tail=stderr_tail[0],
                )
            result = tools_reply.get("result")
            tools = result.get("tools") if isinstance(result, dict) else None
            if not isinstance(tools, list):
                return McpProbeResult(
                    outcome="bad-reply",
                    server_name=server_name,
                    stderr_tail=stderr_tail[0],
                )
            return McpProbeResult(
                outcome="started",
                server_name=server_name,
                tool_count=len(tools),
                stderr_tail=stderr_tail[0],
            )
        except OSError as exc:
            return McpProbeResult(
                outcome="spawn-failed",
                server_name=server_name,
                stderr_tail=str(exc)[-_STDERR_TAIL_MAX:],
            )
        finally:
            stop_stderr.set()
            if proc is not None:
                _stop_process_group(proc)
            if reader is not None:
                reader.join(timeout=1)


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
    """Convenience entry: parse one ``mcpServers`` value and run the probe."""
    command = rendered.get("command")
    if not isinstance(command, str) or not command:
        return McpProbeResult(
            outcome="spawn-failed",
            server_name=server_name,
            stderr_tail="missing command",
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
