"""Stdio JSON-RPC MCP startup probe (Story 103.1, AD-4).

Imports no MCP SDK -- any declared server is judged the same way.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import threading
from collections.abc import Mapping
from pathlib import Path

from pyforge.marshal.ports.mcp_probe import McpProbePort, McpProbeResult

MCP_PROBE_TIMEOUT_S = 15.0
_STDERR_TAIL_MAX = 2048
_PROTOCOL_VERSION = "2025-06-18"
_CLIENT_NAME = "marshal-preflight"


def _merge_env(base: Mapping[str, str], overlay: Mapping[str, str]) -> dict[str, str]:
    merged = dict(os.environ)
    merged.update(base)
    merged.update(overlay)
    return merged


def _read_json_line(
    proc: subprocess.Popen[str],
    *,
    deadline: float,
    stderr_tail: list[str],
) -> tuple[dict[str, object] | None, str | None]:
    """Return (parsed object, error tag) where error is bad-reply | error-reply | timed-out."""
    import time

    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return None, "exited"
        line = proc.stdout.readline() if proc.stdout is not None else ""
        if not line:
            if proc.poll() is not None:
                return None, "exited"
            time.sleep(0.01)
            continue
        line = line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            stderr_tail[0] = (stderr_tail[0] + line + "\n")[-_STDERR_TAIL_MAX:]
            return None, "bad-reply"
        if not isinstance(parsed, dict):
            return None, "bad-reply"
        if parsed.get("error") is not None:
            return None, "error-reply"
        return parsed, None
    return None, "timed-out"


def _stderr_reader(proc: subprocess.Popen[str], tail_holder: list[str]) -> None:
    if proc.stderr is None:
        return
    try:
        for chunk in iter(proc.stderr.read, ""):
            if not chunk:
                break
            tail_holder[0] = (tail_holder[0] + chunk)[-_STDERR_TAIL_MAX:]
    except OSError:
        pass


def _stop_process_group(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is not None:
        return
    try:
        pgid = os.getpgid(proc.pid)
    except OSError:
        pgid = None
    try:
        if pgid is not None:
            os.killpg(pgid, signal.SIGTERM)
        else:
            proc.terminate()
    except OSError:
        pass
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        try:
            if pgid is not None:
                os.killpg(pgid, signal.SIGKILL)
            else:
                proc.kill()
        except OSError:
            pass
        proc.wait(timeout=2)


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
        try:
            proc = subprocess.Popen(
                argv,
                cwd=cwd,
                env=merged,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                start_new_session=True,
            )
        except OSError as exc:
            return McpProbeResult(
                outcome="spawn-failed",
                server_name=server_name,
                stderr_tail=str(exc)[-_STDERR_TAIL_MAX:],
            )

        reader = threading.Thread(target=_stderr_reader, args=(proc, stderr_tail), daemon=True)
        reader.start()

        def write_line(payload: dict[str, object]) -> None:
            if proc.stdin is None:
                return
            proc.stdin.write(json.dumps(payload) + "\n")
            proc.stdin.flush()

        try:
            write_line(
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
            )
            init_reply, init_err = _read_json_line(proc, deadline=deadline, stderr_tail=stderr_tail)
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
            if init_reply is None or "result" not in init_reply:
                return McpProbeResult(
                    outcome="bad-reply",
                    server_name=server_name,
                    stderr_tail=stderr_tail[0],
                )

            write_line({"jsonrpc": "2.0", "method": "notifications/initialized"})
            write_line({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})

            tools_reply, tools_err = _read_json_line(proc, deadline=deadline, stderr_tail=stderr_tail)
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
        finally:
            _stop_process_group(proc)
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
