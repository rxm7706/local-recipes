"""Story 103.1: marshal-mcp on official SDK + preflight stdio handshake."""

from __future__ import annotations

import ast
import json
import os
import shutil
import sys
import textwrap
import threading
import time
from pathlib import Path

import pytest

from pyforge.marshal.adapters.mcp_stdio_probe import (
    StdioMcpProbe,
    _append_tail,
    _read_json_line,
    _stderr_reader_fd,
    _stop_process_group,
    default_mcp_probe,
    probe_server_from_rendered,
)
from pyforge.marshal.cli import init as init_module
from pyforge.marshal.cli.init import run_preflight
from pyforge.marshal.core.mcp_probe import evaluate_mcp_probe
from pyforge.marshal.mcp.server import build_server, main
from pyforge.marshal.ports.mcp_probe import McpProbeResult

PACKAGE_SRC = Path(__file__).resolve().parents[2] / "src" / "pyforge" / "marshal"


@pytest.fixture(autouse=True)
def _sandbox_loop_home_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(tmp_path / "loop-homes"))


@pytest.fixture(autouse=True)
def _sandbox_state_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MARSHAL_STATE_HOME", str(tmp_path / "state-home"))


@pytest.fixture
def repo_root(tmp_path: Path) -> Path:
    return tmp_path / "repo"


def test_default_mcp_probe_factory():
    assert isinstance(default_mcp_probe(), StdioMcpProbe)


def test_read_json_line_skips_blank_lines_and_parses_success():
    import io
    import time

    r, w = os.pipe()
    os.write(w, b'{"jsonrpc":"2.0","id":1,"result":{}}\n')
    os.close(w)

    class _Proc:
        def __init__(self):
            self.stdout = io.TextIOWrapper(io.FileIO(r, "r"), encoding="utf-8")
            self._returncode = None

        def poll(self):
            return self._returncode

    tail: list[str] = [""]
    buf = bytearray()
    parsed, err = _read_json_line(
        _Proc(),
        deadline=time.monotonic() + 1,
        stderr_tail=tail,
        expected_id=1,
        stdout_buf=buf,
    )
    assert err is None and parsed is not None and parsed.get("id") == 1


def _proc_from_pipe_payload(payload: bytes) -> tuple[object, bytearray]:
    import io

    r, w = os.pipe()
    os.write(w, payload)
    os.close(w)

    class _Proc:
        def __init__(self):
            self.stdout = io.TextIOWrapper(io.FileIO(r, "r"), encoding="utf-8")
            self._returncode = None

        def poll(self):
            return self._returncode

    return _Proc(), bytearray()


def test_read_json_line_non_dict_json_is_bad_reply():
    proc, buf = _proc_from_pipe_payload(b"[1,2,3]\n")
    tail: list[str] = [""]
    parsed, err = _read_json_line(
        proc,
        deadline=time.monotonic() + 1,
        stderr_tail=tail,
        stdout_buf=buf,
    )
    assert parsed is None and err == "bad-reply"


def test_read_json_line_bad_reply_and_error_reply():
    tail: list[str] = [""]
    deadline = time.monotonic() + 1
    proc1, buf1 = _proc_from_pipe_payload(b"not-json\n")
    parsed, err = _read_json_line(proc1, deadline=deadline, stderr_tail=tail, stdout_buf=buf1)
    assert parsed is None and err == "bad-reply"

    proc2, buf2 = _proc_from_pipe_payload(b'{"jsonrpc":"2.0","id":1,"error":{"code":1,"message":"x"}}\n')
    parsed2, err2 = _read_json_line(proc2, deadline=deadline, stderr_tail=tail, stdout_buf=buf2)
    assert parsed2 is None and err2 == "error-reply"


EIGHT_TOOLS = {
    "list_marshal_tools",
    "marshal_status",
    "marshal_check",
    "marshal_homes",
    "marshal_preflight",
    "marshal_upstream",
    "marshal_refresh",
    "marshal_watch",
}


@pytest.mark.parametrize(
    "tool_name,arguments",
    [
        ("list_marshal_tools", {}),
        ("marshal_status", {"project": None}),
        ("marshal_check", {"scope": "all", "project": None}),
        ("marshal_homes", {}),
        ("marshal_preflight", {"slug": "pyforge-marshal"}),
        ("marshal_upstream", {}),
        ("marshal_refresh", {"project": None, "base": None}),
        ("marshal_watch", {"project": None, "run": None, "fleet": False}),
    ],
)
def test_build_server_tool_handlers_invoke(tool_name, arguments, monkeypatch):
    """AC2: each registered tool is callable through the SDK surface."""
    import asyncio

    monkeypatch.setattr(
        "pyforge.marshal.mcp.tools.run_marshal",
        lambda *a, **k: {"ok": True, "command": "stub"},
    )
    monkeypatch.setattr(
        "pyforge.marshal.mcp.tools.list_marshal_tools",
        lambda: {"ok": True, "tools": [], "count": 0},
    )
    server = build_server()
    outcome = asyncio.run(server.call_tool(tool_name, arguments))
    assert outcome.is_error is False


def test_build_server_registers_eight_tools():
    """AC2: SDK tool list matches the eight named tools."""
    import asyncio

    server = build_server()
    tools = asyncio.run(server.list_tools())
    names = {t.name for t in tools}
    assert names == EIGHT_TOOLS


def test_no_fastmcp_imports_in_marshal_package():
    """AC3: no module under pyforge.marshal imports fastmcp."""
    for path in PACKAGE_SRC.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("fastmcp")
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("fastmcp")


def test_server_module_import_blocks_mcp_for_build_server(monkeypatch):
    """AC3: build_server raises ImportError naming mcp when SDK blocked."""
    import builtins
    import importlib

    real_import = builtins.__import__

    def blocked(name, *args, **kwargs):
        if name == "mcp" or (name and name.startswith("mcp.")):
            raise ImportError("mcp blocked for test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked)
    for key in list(sys.modules):
        if key == "pyforge.marshal.mcp.server":
            del sys.modules[key]
    mod = importlib.import_module("pyforge.marshal.mcp.server")
    with pytest.raises(ImportError, match="mcp"):
        mod.build_server()


def test_marshal_mcp_help_and_version_exit_zero():
    """AC4: --help and --version exit 0 without building the server."""
    assert main(["--help"]) == 0
    assert main(["--version"]) == 0


def test_marshal_mcp_unknown_argument_exits_two():
    assert main(["--totally-unknown"]) == 2


def test_evaluate_probe_started_is_startable():
    ok, findings = evaluate_mcp_probe(
        McpProbeResult(outcome="started", server_name="marshal", tool_count=8),
        mcp_json_path="/tmp/.mcp.json",
    )
    assert ok is True
    assert not findings


@pytest.mark.parametrize(
    "outcome",
    ["exited", "timed-out", "bad-reply", "error-reply", "spawn-failed"],
)
def test_evaluate_probe_failure_emits_preflight_012(outcome):
    ok, findings = evaluate_mcp_probe(
        McpProbeResult(outcome=outcome, server_name="marshal", stderr_tail="ModuleNotFoundError: x"),
        mcp_json_path="/tmp/.mcp.json",
    )
    assert ok is False
    assert len(findings) == 1
    assert findings[0].code == "MRS-PREFLIGHT-012"
    assert "marshal" in findings[0].message


def _script_fixture(content: str, tmp_path: Path) -> str:
    path = tmp_path / "fake_mcp_server.py"
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)
    return str(path)


def _assert_pgid_dead(pgid: int) -> None:
    with pytest.raises(ProcessLookupError):
        os.killpg(pgid, 0)


def test_stdio_probe_answers_initialize_and_tools_list(tmp_path):
    """AC6/AC1 helper: scripted server returns started with tool count."""
    script = _script_fixture(
        textwrap.dedent(
            """
            import json, sys
            for line in sys.stdin:
                msg = json.loads(line)
                mid = msg.get("id")
                method = msg.get("method")
                if method == "initialize":
                    print(json.dumps({"jsonrpc":"2.0","id":mid,"result":{"serverInfo":{"name":"t"},"capabilities":{}}}))
                    sys.stdout.flush()
                elif method == "tools/list":
                    print(json.dumps({"jsonrpc":"2.0","id":mid,"result":{"tools":[{"name":"a"}]}}))
                    sys.stdout.flush()
                    break
            """
        ),
        tmp_path,
    )
    probe = StdioMcpProbe()
    result = probe.probe_server(
        server_name="t",
        command=sys.executable,
        args=(script,),
        env={},
        cwd=str(tmp_path),
        timeout_s=5,
    )
    assert result.outcome == "started"
    assert result.tool_count == 1


def test_stderr_reader_fd_appends_tail():
    r, w = os.pipe()
    os.write(w, b"hello stderr")
    os.close(w)
    tail = [""]
    stop = threading.Event()
    _stderr_reader_fd(r, tail, stop)
    assert "hello stderr" in tail[0]


def test_append_tail_respects_max():
    tail = [""]
    _append_tail(tail, "x" * 3000)
    assert len(tail[0]) <= 2048


def test_probe_leaves_no_grandchild_process_group(tmp_path):
    """AC6/AC8: background sleep in the probe group is gone after a timed-out probe."""
    pgid_file = tmp_path / "pgid.txt"
    script = _script_fixture(
        textwrap.dedent(
            f"""
            import os, subprocess, sys, time
            marker = {str(pgid_file)!r}
            with open(marker, "w") as f:
                f.write(str(os.getpgid(0)))
            subprocess.Popen(
                [sys.executable, "-c", "import time; time.sleep(600)"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(0.05)
            for line in sys.stdin:
                pass
            """
        ),
        tmp_path,
    )
    result = StdioMcpProbe().probe_server(
        server_name="t",
        command=sys.executable,
        args=(script,),
        env={},
        cwd=str(tmp_path),
        timeout_s=1,
    )
    assert result.outcome == "timed-out"
    pgid = int(pgid_file.read_text(encoding="utf-8").strip())
    _assert_pgid_dead(pgid)


def test_probe_exited_grandchild_detached_pipes_gone(tmp_path):
    """AC6: ``sleep … & exit 1`` with detached stdio leaves a background child in the group."""
    bg_pid_file = tmp_path / "bg.pid"
    shell_cmd = f"sleep 600 </dev/null >/dev/null 2>&1 & echo $! > {bg_pid_file}; sleep 0.05; exit 1"
    t0 = time.monotonic()
    result = StdioMcpProbe().probe_server(
        server_name="t",
        command="/bin/sh",
        args=("-c", shell_cmd),
        env={},
        cwd=str(tmp_path),
        timeout_s=2,
    )
    assert time.monotonic() - t0 < 5.0
    assert result.outcome == "exited"
    bg_pid = int(bg_pid_file.read_text(encoding="utf-8").strip())
    with pytest.raises(ProcessLookupError):
        os.kill(bg_pid, 0)


def test_probe_exited_grandchild_holds_stdout_gone(tmp_path):
    """AC6: parent exits while a background sleep keeps stdout open (``sleep & exit 1``)."""
    pgid_file = tmp_path / "pgid.txt"
    script = _script_fixture(
        textwrap.dedent(
            f"""
            import os, subprocess, sys
            marker = {str(pgid_file)!r}
            with open(marker, "w") as f:
                f.write(str(os.getpgid(0)))
            subprocess.Popen(
                [sys.executable, "-c", "import time; time.sleep(600)"],
            )
            import time
            time.sleep(0.05)
            raise SystemExit(1)
            """
        ),
        tmp_path,
    )
    t0 = time.monotonic()
    result = StdioMcpProbe().probe_server(
        server_name="t",
        command=sys.executable,
        args=(script,),
        env={},
        cwd=str(tmp_path),
        timeout_s=2,
    )
    assert time.monotonic() - t0 < 5.0
    assert result.outcome == "exited"
    _assert_pgid_dead(int(pgid_file.read_text(encoding="utf-8").strip()))


def test_probe_sigterm_ignoring_grandchild_gone(tmp_path):
    """AC6: a grandchild ignores SIGTERM; probe still tears down the whole group."""
    pgid_file = tmp_path / "pgid.txt"
    script = _script_fixture(
        textwrap.dedent(
            f"""
            import os, subprocess, sys
            marker = {str(pgid_file)!r}
            with open(marker, "w") as f:
                f.write(str(os.getpgid(0)))
            subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    "import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(600)",
                ],
            )
            import time
            time.sleep(600)
            """
        ),
        tmp_path,
    )
    t0 = time.monotonic()
    result = StdioMcpProbe().probe_server(
        server_name="t",
        command=sys.executable,
        args=(script,),
        env={},
        cwd=str(tmp_path),
        timeout_s=2,
    )
    assert time.monotonic() - t0 < 8.0
    assert result.outcome in ("timed-out", "exited")
    _assert_pgid_dead(int(pgid_file.read_text(encoding="utf-8").strip()))


def test_stdio_probe_timeout_is_wall_clock_bounded(tmp_path):
    """AC6: timeout fires while stdout read would block (server sleeps before replying)."""
    script = _script_fixture(
        textwrap.dedent(
            """
            import json, sys, time
            for line in sys.stdin:
                msg = json.loads(line)
                if msg.get("method") == "initialize":
                    time.sleep(12)
                    print(json.dumps({"jsonrpc":"2.0","id":msg["id"],"result":{"serverInfo":{"name":"t"},"capabilities":{}}}))
                    sys.stdout.flush()
            """
        ),
        tmp_path,
    )
    t0 = time.monotonic()
    result = StdioMcpProbe().probe_server(
        server_name="t",
        command=sys.executable,
        args=(script,),
        env={},
        cwd=str(tmp_path),
        timeout_s=1,
    )
    elapsed = time.monotonic() - t0
    assert result.outcome == "timed-out"
    assert elapsed < 3.0


def test_stdio_probe_initialize_reply_missing_result(tmp_path):
    script = _script_fixture(
        'import json,sys\nprint(json.dumps({"jsonrpc":"2.0","id":1}))\n',
        tmp_path,
    )
    result = StdioMcpProbe().probe_server(
        server_name="t",
        command=sys.executable,
        args=(script,),
        env={},
        cwd=str(tmp_path),
        timeout_s=5,
    )
    assert result.outcome == "bad-reply"


def test_stdio_probe_tools_reply_none_without_error(monkeypatch, tmp_path):
    script = _script_fixture(
        textwrap.dedent(
            """
            import json, sys
            for line in sys.stdin:
                msg = json.loads(line)
                mid = msg.get("id")
                if msg.get("method") == "initialize":
                    print(json.dumps({"jsonrpc":"2.0","id":mid,"result":{"serverInfo":{"name":"t"},"capabilities":{}}}))
                    sys.stdout.flush()
            """
        ),
        tmp_path,
    )
    import pyforge.marshal.adapters.mcp_stdio_probe as probe_mod

    real_read = probe_mod._read_json_line
    calls = {"n": 0}

    def patched_read(proc, *, deadline, stderr_tail, expected_id=None, stdout_buf=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return real_read(
                proc,
                deadline=deadline,
                stderr_tail=stderr_tail,
                expected_id=expected_id,
                stdout_buf=stdout_buf or bytearray(),
            )
        return None, None

    monkeypatch.setattr(probe_mod, "_read_json_line", patched_read)
    result = StdioMcpProbe().probe_server(
        server_name="t",
        command=sys.executable,
        args=(script,),
        env={},
        cwd=str(tmp_path),
        timeout_s=5,
    )
    assert result.outcome == "bad-reply"


def test_stdio_probe_bad_reply(tmp_path):
    script = _script_fixture('print("not json at all")\n', tmp_path)
    result = StdioMcpProbe().probe_server(
        server_name="t",
        command=sys.executable,
        args=(script,),
        env={},
        cwd=str(tmp_path),
        timeout_s=5,
    )
    assert result.outcome == "bad-reply"


def test_stdio_probe_error_reply(tmp_path):
    script = _script_fixture(
        'import json,sys\nprint(json.dumps({"jsonrpc":"2.0","id":1,"error":{"code":-1,"message":"nope"}}))\n',
        tmp_path,
    )
    result = StdioMcpProbe().probe_server(
        server_name="t",
        command=sys.executable,
        args=(script,),
        env={},
        cwd=str(tmp_path),
        timeout_s=5,
    )
    assert result.outcome == "error-reply"


def test_stdio_probe_timed_out_waiting_for_tools_list(tmp_path):
    """AC6: never answers tools/list -> timed-out."""
    script = _script_fixture(
        textwrap.dedent(
            """
            import json, sys
            for line in sys.stdin:
                msg = json.loads(line)
                if msg.get("method") == "initialize":
                    print(json.dumps({"jsonrpc":"2.0","id":msg["id"],"result":{"serverInfo":{"name":"t"},"capabilities":{}}}))
                    sys.stdout.flush()
                elif msg.get("method") == "tools/list":
                    pass
            """
        ),
        tmp_path,
    )
    result = StdioMcpProbe().probe_server(
        server_name="t",
        command=sys.executable,
        args=(script,),
        env={},
        cwd=str(tmp_path),
        timeout_s=1,
    )
    assert result.outcome == "timed-out"


def test_stdio_probe_tools_list_missing_tools_key(tmp_path):
    script = _script_fixture(
        textwrap.dedent(
            """
            import json, sys
            for line in sys.stdin:
                msg = json.loads(line)
                mid = msg.get("id")
                method = msg.get("method")
                if method == "initialize":
                    print(json.dumps({"jsonrpc":"2.0","id":mid,"result":{"serverInfo":{"name":"t"},"capabilities":{}}}))
                    sys.stdout.flush()
                elif method == "tools/list":
                    print(json.dumps({"jsonrpc":"2.0","id":mid,"result":{}}))
                    sys.stdout.flush()
                    break
            """
        ),
        tmp_path,
    )
    result = StdioMcpProbe().probe_server(
        server_name="t",
        command=sys.executable,
        args=(script,),
        env={},
        cwd=str(tmp_path),
        timeout_s=5,
    )
    assert result.outcome == "bad-reply"


def test_stdio_probe_heavy_stderr_still_started(tmp_path):
    script = _script_fixture(
        textwrap.dedent(
            """
            import json, sys
            sys.stderr.write("x" * (1024 * 1024))
            sys.stderr.flush()
            for line in sys.stdin:
                msg = json.loads(line)
                mid = msg.get("id")
                if msg.get("method") == "initialize":
                    print(json.dumps({"jsonrpc":"2.0","id":mid,"result":{"serverInfo":{"name":"t"},"capabilities":{}}}))
                    sys.stdout.flush()
                elif msg.get("method") == "tools/list":
                    print(json.dumps({"jsonrpc":"2.0","id":mid,"result":{"tools":[]}}))
                    sys.stdout.flush()
                    break
            """
        ),
        tmp_path,
    )
    result = StdioMcpProbe().probe_server(
        server_name="t",
        command=sys.executable,
        args=(script,),
        env={},
        cwd=str(tmp_path),
        timeout_s=5,
    )
    assert result.outcome == "started"
    assert len(result.stderr_tail) <= 2048


def test_stdio_probe_spawn_failed():
    result = StdioMcpProbe().probe_server(
        server_name="t",
        command="/no/such/binary-ever",
        args=(),
        env={},
        cwd="/tmp",
        timeout_s=1,
    )
    assert result.outcome == "spawn-failed"


def test_probe_server_from_rendered_with_args_and_env(tmp_path):
    script = _script_fixture(
        textwrap.dedent(
            """
            import json, os, sys
            assert os.environ.get("PROBE_FOO") == "bar"
            for line in sys.stdin:
                msg = json.loads(line)
                mid = msg.get("id")
                if msg.get("method") == "initialize":
                    print(json.dumps({"jsonrpc":"2.0","id":mid,"result":{"serverInfo":{"name":"t"},"capabilities":{}}}))
                    sys.stdout.flush()
                elif msg.get("method") == "tools/list":
                    print(json.dumps({"jsonrpc":"2.0","id":mid,"result":{"tools":[]}}))
                    sys.stdout.flush()
                    break
            """
        ),
        tmp_path,
    )
    result = probe_server_from_rendered(
        server_name="s",
        rendered={"command": sys.executable, "args": [script], "env": {"PROBE_FOO": "bar"}},
        home=tmp_path,
    )
    assert result.outcome == "started"


def test_probe_server_from_rendered_missing_command(tmp_path):
    result = probe_server_from_rendered(
        server_name="x",
        rendered={},
        home=tmp_path,
    )
    assert result.outcome == "spawn-failed"


def test_stdio_probe_exited_after_initialize(tmp_path):
    script = _script_fixture(
        textwrap.dedent(
            """
            import json, sys
            for line in sys.stdin:
                msg = json.loads(line)
                if msg.get("method") == "initialize":
                    print(json.dumps({"jsonrpc":"2.0","id":msg["id"],"result":{"serverInfo":{"name":"t"},"capabilities":{}}}))
                    sys.stdout.flush()
                    sys.exit(3)
            """
        ),
        tmp_path,
    )
    result = StdioMcpProbe().probe_server(
        server_name="t",
        command=sys.executable,
        args=(script,),
        env={},
        cwd=str(tmp_path),
        timeout_s=5,
    )
    assert result.outcome == "exited"
    assert result.exit_code == 3


def test_stdio_probe_exited_on_early_failure(tmp_path):
    script = _script_fixture(
        'import sys; print("fail", file=sys.stderr); sys.exit(1)\n',
        tmp_path,
    )
    result = StdioMcpProbe().probe_server(
        server_name="t",
        command=sys.executable,
        args=(script,),
        env={},
        cwd=str(tmp_path),
        timeout_s=5,
    )
    assert result.outcome == "exited"
    assert result.exit_code == 1


def test_mutation_timed_out_not_startable():
    """AC8: mapping timed-out to startable must fail this test."""
    ok, _ = evaluate_mcp_probe(
        McpProbeResult(outcome="timed-out", server_name="x"),
        mcp_json_path="/x",
    )
    assert ok is False


def test_mutation_skipping_handshake_in_probe_would_miss_finding(repo_root, tmp_path, monkeypatch, capsys):
    """AC8: resolvable server with failing probe must emit MRS-PREFLIGHT-012."""
    import test_init as init_mod

    class _FailProbe:
        called = False

        def probe_server(self, **kwargs):
            _FailProbe.called = True
            return McpProbeResult(
                outcome="exited",
                server_name="atlas",
                exit_code=1,
                stderr_tail="ModuleNotFoundError: fastmcp",
            )

    slug = "acme"
    home = tmp_path / "loop-homes" / slug
    fs = init_mod.FakeFs(project_dirs={home})
    fs.texts[home / ".mcp.json"] = json.dumps({"mcpServers": {"atlas": {"command": "atlas-mcp"}}})
    harness = init_mod._converged_harness()
    harness.binaries_present.add("atlas-mcp")
    init_mod._seed_acknowledged(fs, tmp_path, ["claude"])
    policy_path = tmp_path / "marshal-policy.toml"
    policy_path.write_text('[mcp_servers.atlas]\ncommand = "atlas-mcp"\n', encoding="utf-8")
    monkeypatch.setattr(
        init_module,
        "conventional_project_policy_path",
        lambda s: policy_path,
    )

    vcs = init_mod.FakeVcs(repo_root=repo_root)
    exit_code = run_preflight(
        init_mod._preflight_namespace(slug, fmt="json"),
        vcs=vcs,
        fs=fs,
        harness=harness,
        mcp_probe=_FailProbe(),
    )
    assert _FailProbe.called
    assert exit_code != 0
    out = capsys.readouterr().out
    assert "MRS-PREFLIGHT-012" in out
    assert "exited" in out


def test_preflight_json_mcp_startable_eight_tools(repo_root, tmp_path, monkeypatch, capsys):
    """AC7: real preflight JSON shows startable marshal-mcp with tool_count 8."""
    import test_init as init_mod

    slug = "pyforge-marshal"
    home = tmp_path / "loop-homes" / slug
    fs = init_mod.FakeFs(project_dirs={home})
    fs.texts[home / ".mcp.json"] = json.dumps({"mcpServers": {"marshal": {"command": "marshal-mcp"}}})
    harness = init_mod._converged_harness()
    harness.binaries_present.add("marshal-mcp")
    init_mod._seed_acknowledged(fs, tmp_path, ["claude"])
    policy_path = tmp_path / "marshal-policy.toml"
    policy_path.write_text('[mcp_servers.marshal]\ncommand = "marshal-mcp"\n', encoding="utf-8")
    monkeypatch.setattr(init_module, "conventional_project_policy_path", lambda s: policy_path)
    vcs = init_mod.FakeVcs(repo_root=repo_root)

    exit_code = run_preflight(
        init_mod._preflight_namespace(slug, fmt="json"),
        vcs=vcs,
        fs=fs,
        harness=harness,
        mcp_probe=_FakeMcpProbeStarted(),
    )
    assert exit_code == 0
    out = capsys.readouterr().out
    envelope = json.loads(out)
    servers = envelope["data"]["mcp_servers"]
    assert len(servers) == 1
    assert servers[0]["startable"] is True
    assert servers[0]["tool_count"] == 8
    assert "MRS-PREFLIGHT-012" not in out


def test_preflight_json_fastmcp_stand_in_reports_012(repo_root, tmp_path, monkeypatch, capsys):
    """AC7: failing handshake surfaces ModuleNotFoundError in MRS-PREFLIGHT-012."""
    import test_init as init_mod

    class _FastmcpStandIn:
        def probe_server(self, **kwargs):
            return McpProbeResult(
                outcome="exited",
                server_name="marshal",
                exit_code=1,
                stderr_tail="ModuleNotFoundError: No module named 'fastmcp'",
            )

    slug = "pyforge-marshal"
    home = tmp_path / "loop-homes" / slug
    fs = init_mod.FakeFs(project_dirs={home})
    fs.texts[home / ".mcp.json"] = json.dumps({"mcpServers": {"marshal": {"command": "marshal-mcp"}}})
    harness = init_mod._converged_harness()
    harness.binaries_present.add("marshal-mcp")
    init_mod._seed_acknowledged(fs, tmp_path, ["claude"])
    policy_path = tmp_path / "marshal-policy.toml"
    policy_path.write_text('[mcp_servers.marshal]\ncommand = "marshal-mcp"\n', encoding="utf-8")
    monkeypatch.setattr(init_module, "conventional_project_policy_path", lambda s: policy_path)
    vcs = init_mod.FakeVcs(repo_root=repo_root)

    exit_code = run_preflight(
        init_mod._preflight_namespace(slug, fmt="json"),
        vcs=vcs,
        fs=fs,
        harness=harness,
        mcp_probe=_FastmcpStandIn(),
    )
    assert exit_code != 0
    out = capsys.readouterr().out
    assert "MRS-PREFLIGHT-012" in out
    assert "ModuleNotFoundError" in out


class _FakeMcpProbeStarted:
    def probe_server(self, **kwargs):
        return McpProbeResult(outcome="started", server_name="marshal", tool_count=8)


def test_mutation_dropping_stop_process_group_fails_grandchild_test(tmp_path):
    """AC8: real ``_stop_process_group`` clears the stdout grandchild (mutation: no-op stop leaves pgid alive)."""
    pgid_file = tmp_path / "pgid.txt"
    script = _script_fixture(
        textwrap.dedent(
            f"""
            import os, subprocess, sys
            marker = {str(pgid_file)!r}
            with open(marker, "w") as f:
                f.write(str(os.getpgid(0)))
            subprocess.Popen([sys.executable, "-c", "import time; time.sleep(600)"])
            import time
            time.sleep(0.05)
            raise SystemExit(1)
            """
        ),
        tmp_path,
    )
    result = StdioMcpProbe().probe_server(
        server_name="t",
        command=sys.executable,
        args=(script,),
        env={},
        cwd=str(tmp_path),
        timeout_s=2,
    )
    assert result.outcome == "exited"
    _assert_pgid_dead(int(pgid_file.read_text(encoding="utf-8").strip()))


def test_read_json_line_times_out_with_no_data():
    import io

    r, _w = os.pipe()
    proc = type("P", (), {"stdout": io.TextIOWrapper(io.FileIO(r, "r"), encoding="utf-8"), "poll": lambda self: None})()
    parsed, err = _read_json_line(
        proc,
        deadline=time.monotonic() + 0.05,
        stderr_tail=[""],
        stdout_buf=bytearray(),
    )
    assert parsed is None and err == "timed-out"


def test_stdio_probe_initialize_missing_server_info(tmp_path):
    script = _script_fixture(
        'import json,sys\nprint(json.dumps({"jsonrpc":"2.0","id":1,"result":{"capabilities":{}}}))\n',
        tmp_path,
    )
    result = StdioMcpProbe().probe_server(
        server_name="t",
        command=sys.executable,
        args=(script,),
        env={},
        cwd=str(tmp_path),
        timeout_s=5,
    )
    assert result.outcome == "bad-reply"


def test_stdio_probe_skips_unexpected_json_rpc_id(tmp_path):
    script = _script_fixture(
        textwrap.dedent(
            """
            import json, sys
            print(json.dumps({"jsonrpc":"2.0","id":99,"result":{"serverInfo":{"name":"x"},"capabilities":{}}}))
            sys.stdout.flush()
            for line in sys.stdin:
                msg = json.loads(line)
                mid = msg.get("id")
                if msg.get("method") == "initialize":
                    print(json.dumps({"jsonrpc":"2.0","id":mid,"result":{"serverInfo":{"name":"t"},"capabilities":{}}}))
                    sys.stdout.flush()
                elif msg.get("method") == "tools/list":
                    print(json.dumps({"jsonrpc":"2.0","id":mid,"result":{"tools":[]}}))
                    sys.stdout.flush()
                    break
            """
        ),
        tmp_path,
    )
    result = StdioMcpProbe().probe_server(
        server_name="t",
        command=sys.executable,
        args=(script,),
        env={},
        cwd=str(tmp_path),
        timeout_s=5,
    )
    assert result.outcome == "started"


def test_stop_process_group_terminates_running_child(tmp_path):
    script = _script_fixture("import time\ntime.sleep(60)\n", tmp_path)
    import subprocess

    proc = subprocess.Popen(
        [sys.executable, script],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    _stop_process_group(proc)
    assert proc.poll() is not None


def test_popen_kwargs_windows_branch(monkeypatch):
    import pyforge.marshal.adapters.mcp_stdio_probe as mod

    monkeypatch.setattr(mod.sys, "platform", "win32")
    monkeypatch.setattr(mod.subprocess, "CREATE_NEW_PROCESS_GROUP", 512, raising=False)
    assert "creationflags" in mod._popen_kwargs(start_new_session=True)


def test_popen_kwargs_unix_branch():
    import pyforge.marshal.adapters.mcp_stdio_probe as mod

    assert mod._popen_kwargs(start_new_session=True) == {"start_new_session": True}
    assert mod._popen_kwargs(start_new_session=False) == {}


def test_stdio_probe_unexpected_exception_becomes_bad_reply(monkeypatch, tmp_path):
    import pyforge.marshal.adapters.mcp_stdio_probe as probe_mod

    script = _script_fixture("import time\ntime.sleep(60)\n", tmp_path)
    monkeypatch.setattr(probe_mod.json, "dumps", lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("boom")))
    result = StdioMcpProbe().probe_server(
        server_name="t",
        command=sys.executable,
        args=(script,),
        env={},
        cwd=str(tmp_path),
        timeout_s=5,
    )
    assert result.outcome == "bad-reply"
    assert "boom" in result.stderr_tail


def test_stdio_probe_spawns_with_windows_creationflags(monkeypatch, tmp_path):
    import pyforge.marshal.adapters.mcp_stdio_probe as mod

    creationflags: list[int] = []

    class _FakeProc:
        returncode = 0
        stdin = None
        stdout = None
        stderr = None

        def poll(self):
            return 0

        def terminate(self):
            pass

        def kill(self):
            pass

        def wait(self, timeout=None):
            return 0

    def fake_popen(_argv, **kwargs):
        flag = kwargs.get("creationflags")
        if isinstance(flag, int):
            creationflags.append(flag)
        return _FakeProc()

    monkeypatch.setattr(mod.sys, "platform", "win32")
    monkeypatch.setattr(mod.subprocess, "CREATE_NEW_PROCESS_GROUP", 512, raising=False)
    monkeypatch.setattr(mod.subprocess, "Popen", fake_popen)

    result = mod.StdioMcpProbe().probe_server(
        server_name="t",
        command=sys.executable,
        args=("-c", "pass"),
        env={},
        cwd=str(tmp_path),
        timeout_s=5,
    )
    assert creationflags == [512]
    assert result.outcome == "exited"


def test_stop_process_group_windows_branch(monkeypatch):
    import pyforge.marshal.adapters.mcp_stdio_probe as mod

    class _WinProc:
        pid = 1
        terminated = False
        killed = False

        def poll(self):
            return None

        def terminate(self):
            self.terminated = True

        def kill(self):
            self.killed = True

        def wait(self, timeout=None):
            return 0

    monkeypatch.setattr(mod.sys, "platform", "win32")
    proc = _WinProc()
    mod._stop_process_group(proc)
    assert proc.terminated


def test_stop_process_group_windows_kills_when_wait_times_out(monkeypatch):
    import subprocess

    import pyforge.marshal.adapters.mcp_stdio_probe as mod

    class _WinProc:
        pid = 1
        killed = False

        def terminate(self):
            pass

        def kill(self):
            self.killed = True

        def wait(self, timeout=None):
            raise subprocess.TimeoutExpired("cmd", timeout)

    monkeypatch.setattr(mod.sys, "platform", "win32")
    proc = _WinProc()
    mod._stop_process_group(proc)
    assert proc.killed


def test_stop_process_group_killpg_oserror_falls_back_to_terminate(monkeypatch):
    import signal

    import pyforge.marshal.adapters.mcp_stdio_probe as mod

    terminated: list[int] = []

    class _Proc:
        pid = 7

        def poll(self):
            return None

        def terminate(self):
            terminated.append(1)

        def kill(self):
            pass

        def wait(self, timeout=None):
            return 0

    def killpg(_pg, sig):
        if sig == signal.SIGTERM:
            raise OSError("killpg failed")

    monkeypatch.setattr(mod.os, "killpg", killpg)
    mod._stop_process_group(_Proc())
    assert terminated


def test_read_json_line_exited_drains_stdout(monkeypatch):
    import io

    import pyforge.marshal.adapters.mcp_stdio_probe as probe_mod

    monkeypatch.setattr(probe_mod, "_stop_process_group", lambda _proc: None)

    r, w = os.pipe()
    os.write(w, b'{"jsonrpc":"2.0","id":1,"result":{}}\n')
    os.close(w)

    class _Proc:
        pid = 99999

        def __init__(self):
            self.stdout = io.TextIOWrapper(io.FileIO(r, "r"), encoding="utf-8")
            self._code = 1

        def poll(self):
            return self._code

    buf = bytearray()
    parsed, err = _read_json_line(
        _Proc(),
        deadline=time.monotonic() + 1,
        stderr_tail=[""],
        stdout_buf=buf,
    )
    assert parsed is None and err == "exited"


def test_stdio_probe_write_fails_when_stdin_closed(tmp_path):
    script = _script_fixture("import sys\nsys.stdin.close()\n", tmp_path)
    result = StdioMcpProbe().probe_server(
        server_name="t",
        command=sys.executable,
        args=(script,),
        env={},
        cwd=str(tmp_path),
        timeout_s=5,
    )
    assert result.outcome == "exited"


def test_stop_process_group_sigkill_after_wait_timeout(monkeypatch):
    import signal
    import subprocess

    import pyforge.marshal.adapters.mcp_stdio_probe as mod

    class _SlowProc:
        pid = 42

        def poll(self):
            return None

        def terminate(self):
            pass

        def kill(self):
            pass

        def wait(self, timeout=None):
            raise subprocess.TimeoutExpired("cmd", timeout)

    kills: list[tuple[int, int]] = []
    monkeypatch.setattr(mod.os, "killpg", lambda pg, sig: kills.append((pg, sig)))
    mod._stop_process_group(_SlowProc())
    assert (42, signal.SIGTERM) in kills
    assert (42, signal.SIGKILL) in kills


def test_stdio_probe_unknown_read_error_tag_is_bad_reply(tmp_path, monkeypatch):
    script = _script_fixture("import time\ntime.sleep(60)\n", tmp_path)
    import pyforge.marshal.adapters.mcp_stdio_probe as probe_mod

    monkeypatch.setattr(
        probe_mod,
        "_read_json_line",
        lambda *a, **k: (None, "not-a-valid-outcome-tag"),
    )
    result = StdioMcpProbe().probe_server(
        server_name="t",
        command=sys.executable,
        args=(script,),
        env={},
        cwd=str(tmp_path),
        timeout_s=5,
    )
    assert result.outcome == "bad-reply"


def test_stop_process_group_killpg_lookup_error_still_sends_sigkill(monkeypatch):
    import signal

    import pyforge.marshal.adapters.mcp_stdio_probe as mod

    class _Proc:
        pid = 3

        def poll(self):
            return None

        def terminate(self):
            pass

        def kill(self):
            pass

        def wait(self, timeout=None):
            return 0

    signals: list[int] = []

    def killpg(_pg, sig):
        signals.append(sig)
        raise ProcessLookupError()

    monkeypatch.setattr(mod.os, "killpg", killpg)
    mod._stop_process_group(_Proc())
    assert signal.SIGTERM in signals
    assert signal.SIGKILL in signals


def test_probe_server_from_rendered_with_string_args(tmp_path):
    script = _script_fixture(
        textwrap.dedent(
            """
            import json, sys
            for line in sys.stdin:
                msg = json.loads(line)
                mid = msg.get("id")
                if msg.get("method") == "initialize":
                    print(json.dumps({"jsonrpc":"2.0","id":mid,"result":{"serverInfo":{"name":"t"},"capabilities":{}}}))
                    sys.stdout.flush()
                elif msg.get("method") == "tools/list":
                    print(json.dumps({"jsonrpc":"2.0","id":mid,"result":{"tools":[{"name":"a"}]}}))
                    sys.stdout.flush()
                    break
            """
        ),
        tmp_path,
    )
    result = probe_server_from_rendered(
        server_name="s",
        rendered={"command": sys.executable, "args": [script, "extra"], "env": {"K": "V"}},
        home=tmp_path,
    )
    assert result.outcome == "started"
    assert result.tool_count == 1


@pytest.mark.skipif(shutil.which("marshal-mcp") is None, reason="marshal-mcp not on PATH")
def test_real_marshal_mcp_handshake_via_adapter():
    """AC1: real console script answers initialize and tools/list."""
    resolved = shutil.which("marshal-mcp")
    assert resolved is not None
    probe = StdioMcpProbe()
    result = probe.probe_server(
        server_name="marshal",
        command=resolved,
        args=(),
        env={},
        cwd=str(Path.cwd()),
        timeout_s=20,
    )
    assert result.outcome == "started"
    assert result.tool_count == 8
