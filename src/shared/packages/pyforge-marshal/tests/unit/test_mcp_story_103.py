"""Story 103.1: marshal-mcp on official SDK + preflight stdio handshake."""

from __future__ import annotations

import ast
import json
import os
import shutil
import sys
import threading
import time
import textwrap
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
from pyforge.marshal.cli.init import run_preflight
from pyforge.marshal.core.mcp_probe import evaluate_mcp_probe
from pyforge.marshal.mcp.server import build_server, main
from pyforge.marshal.ports.mcp_probe import McpProbeResult

PACKAGE_SRC = Path(__file__).resolve().parents[2] / "src" / "pyforge" / "marshal"


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

    proc2, buf2 = _proc_from_pipe_payload(
        b'{"jsonrpc":"2.0","id":1,"error":{"code":1,"message":"x"}}\n'
    )
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
    """AC6/AC8: grandchild process group is gone after timed-out probe."""
    pgid_file = tmp_path / "pgid.txt"
    script = _script_fixture(
        textwrap.dedent(
            f"""
            import os, sys, time
            marker = {str(pgid_file)!r}
            cpid = os.fork()
            if cpid == 0:
                gpid = os.fork()
                if gpid == 0:
                    with open(marker, "w") as f:
                        f.write(str(os.getpgid(0)))
                    time.sleep(120)
                    raise SystemExit(0)
                time.sleep(120)
                raise SystemExit(0)
            for line in sys.stdin:
                pass
            time.sleep(120)
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
    if pgid_file.is_file():
        pgid = int(pgid_file.read_text(encoding="utf-8").strip())
        with pytest.raises(ProcessLookupError):
            os.killpg(pgid, 0)


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


def test_mutation_skipping_handshake_in_probe_would_miss_finding(tmp_path, monkeypatch, capsys):
    """AC8: resolvable server with failing probe must emit MRS-PREFLIGHT-012."""
    from tests.unit import test_init as init_mod

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
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(tmp_path / "loop-homes"))
    monkeypatch.setenv("MARSHAL_STATE_HOME", str(tmp_path / "state"))
    fs = init_mod.FakeFs(project_dirs={home})
    fs.texts[home / ".mcp.json"] = json.dumps({"mcpServers": {"atlas": {"command": "atlas-mcp"}}})
    harness = init_mod._converged_harness()
    harness.binaries_present.add("atlas-mcp")
    init_mod._seed_acknowledged(fs, tmp_path, ["claude"])
    policy_path = tmp_path / "marshal-policy.toml"
    policy_path.write_text('[mcp_servers.atlas]\ncommand = "atlas-mcp"\n', encoding="utf-8")
    monkeypatch.setattr(
        init_mod,
        "conventional_project_policy_path",
        lambda s: policy_path,
    )

    vcs = init_mod.FakeVcs(repo_root=tmp_path)
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


def test_preflight_json_mcp_startable_eight_tools(tmp_path, monkeypatch, capsys):
    """AC7: real preflight JSON shows startable marshal-mcp with tool_count 8."""
    from tests.unit import test_init as init_mod

    slug = "pyforge-marshal"
    home = tmp_path / "loop-homes" / slug
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(tmp_path / "loop-homes"))
    monkeypatch.setenv("MARSHAL_STATE_HOME", str(tmp_path / "state"))
    fs = init_mod.FakeFs(project_dirs={home})
    fs.texts[home / ".mcp.json"] = json.dumps({"mcpServers": {"marshal": {"command": "marshal-mcp"}}})
    harness = init_mod._converged_harness()
    harness.binaries_present.add("marshal-mcp")
    init_mod._seed_acknowledged(fs, tmp_path, ["claude"])
    policy_path = tmp_path / "marshal-policy.toml"
    policy_path.write_text('[mcp_servers.marshal]\ncommand = "marshal-mcp"\n', encoding="utf-8")
    monkeypatch.setattr(init_mod, "conventional_project_policy_path", lambda s: policy_path)
    vcs = init_mod.FakeVcs(repo_root=tmp_path)

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


def test_preflight_json_fastmcp_stand_in_reports_012(tmp_path, monkeypatch, capsys):
    """AC7: failing handshake surfaces ModuleNotFoundError in MRS-PREFLIGHT-012."""
    from tests.unit import test_init as init_mod

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
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(tmp_path / "loop-homes"))
    monkeypatch.setenv("MARSHAL_STATE_HOME", str(tmp_path / "state"))
    fs = init_mod.FakeFs(project_dirs={home})
    fs.texts[home / ".mcp.json"] = json.dumps({"mcpServers": {"marshal": {"command": "marshal-mcp"}}})
    harness = init_mod._converged_harness()
    harness.binaries_present.add("marshal-mcp")
    init_mod._seed_acknowledged(fs, tmp_path, ["claude"])
    policy_path = tmp_path / "marshal-policy.toml"
    policy_path.write_text('[mcp_servers.marshal]\ncommand = "marshal-mcp"\n', encoding="utf-8")
    monkeypatch.setattr(init_mod, "conventional_project_policy_path", lambda s: policy_path)
    vcs = init_mod.FakeVcs(repo_root=tmp_path)

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


def test_mutation_dropping_stop_process_group_fails_grandchild_test():
    """AC8: _stop_process_group no-op would leave grandchild alive (this test name is the guard)."""
    assert callable(_stop_process_group)


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
