"""Story 103.1: ``marshal-mcp`` on the official SDK, and preflight proves it with a stdio handshake.

AC1 (the real console script answers ``initialize`` and ``tools/list``), AC2 (the eight tools are registered in
process and delegate to ``tools.py``), AC3 (no ``fastmcp``; the server module imports with the SDK blocked),
AC4 (``--help`` / ``--version`` / an unknown argument never build the server), AC5 (every probe outcome through
``_probe_mcp_servers``), AC6 (the adapter against scripted servers, no process of the child's group left
running), AC7 (preflight end to end through the real adapter) and AC8 (the three mutations each fail a named
test). The shared preflight fakes come from ``test_init`` the way ``test_teardown_preserve`` and
``test_init_teardown_preserve`` already take them.
"""

from __future__ import annotations

import ast
import io
import json
import os
import shutil
import subprocess
import sys
import textwrap
import threading
import time
from importlib.metadata import version as installed_version
from pathlib import Path

import pytest

import pyforge.marshal.adapters.mcp_stdio_probe as probe_mod
from pyforge.marshal.adapters.mcp_stdio_probe import (
    StdioMcpProbe,
    _append_tail,
    _open_chunks,
    _parse_buffered,
    _read_reply,
    _SelectorChunks,
    _stderr_reader_fd,
    _stop_process_group,
    _ThreadChunks,
    default_mcp_probe,
    probe_server_from_rendered,
)
from pyforge.marshal.cli import init as init_module
from pyforge.marshal.cli.init import run_preflight
from pyforge.marshal.core.mcp_probe import evaluate_mcp_probe
from pyforge.marshal.core.verdict import EXIT_OK
from pyforge.marshal.ports.mcp_probe import McpProbeResult

PACKAGE_SRC = Path(__file__).resolve().parents[2] / "src" / "pyforge" / "marshal"

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

# A GitHub-token-shaped string: ``core.egress.redact_raw_text`` must replace it before it reaches a finding.
_TOKEN = "ghp_" + "A1b2C3d4" * 6
_REDACTED = "***REDACTED***"


@pytest.fixture(autouse=True)
def _sandbox_loop_home_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BMAD_LOOP_HOME_ROOT", str(tmp_path / "loop-homes"))


@pytest.fixture(autouse=True)
def _sandbox_state_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MARSHAL_STATE_HOME", str(tmp_path / "state-home"))


@pytest.fixture
def repo_root(tmp_path: Path) -> Path:
    return tmp_path / "repo"


# --- scripted servers -------------------------------------------------------------------------------------------

_PGID_PREAMBLE = (
    "import os as _os\n"
    "with open({marker!r}, 'w', encoding='utf-8') as _f:\n"
    "    _f.write(str(_os.getpgid(0)))\n"
)

_ANSWERING_BODY = """
    import json, sys

    def _reply(mid, result):
        print(json.dumps({"jsonrpc": "2.0", "id": mid, "result": result}))
        sys.stdout.flush()

    for line in sys.stdin:
        msg = json.loads(line)
        if msg.get("method") == "initialize":
            _reply(msg["id"], {"serverInfo": {"name": "fixture"}, "capabilities": {}})
        elif msg.get("method") == "tools/list":
            _reply(msg["id"], {"tools": [{"name": "alpha"}, {"name": "beta"}]})
            break
"""


def _py_server(tmp_path: Path, name: str, body: str) -> tuple[str, Path]:
    """A Python server script that first records its own process-group id, then runs ``body``."""
    pgid_file = tmp_path / f"{name}.pgid"
    script = tmp_path / f"{name}.py"
    script.write_text(_PGID_PREAMBLE.format(marker=str(pgid_file)) + textwrap.dedent(body), encoding="utf-8")
    return str(script), pgid_file


def _probe(tmp_path: Path, script: str, *, timeout_s: float = 5.0) -> McpProbeResult:
    return StdioMcpProbe().probe_server(
        server_name="fixture",
        command=sys.executable,
        args=(script,),
        env={},
        cwd=str(tmp_path),
        timeout_s=timeout_s,
    )


def _assert_group_gone(pgid_file: Path, *, within_s: float = 2.0) -> None:
    """No process of the child's group is left running.

    A grandchild the probe just killed is a zombie until init reaps it, and a zombie is still a group member
    for ``killpg(pgid, 0)``, so the check is retried briefly -- then asserted, unconditionally.
    """
    assert pgid_file.is_file(), f"the fixture never started ({pgid_file} missing)"
    pgid = int(pgid_file.read_text(encoding="utf-8").strip())
    deadline = time.monotonic() + within_s
    while True:
        try:
            os.killpg(pgid, 0)
        except ProcessLookupError:
            return
        if time.monotonic() > deadline:
            pytest.fail(f"process group {pgid} still has a live member {within_s}s after the probe returned")
        time.sleep(0.02)


# --- AC6: the adapter against scripted servers ------------------------------------------------------------------


def test_adapter_answers_initialize_and_tools_list(tmp_path: Path):
    script, pgid_file = _py_server(tmp_path, "answers", _ANSWERING_BODY)
    result = _probe(tmp_path, script)
    assert result.outcome == "started"
    assert result.tool_count == 2
    assert result.tool_names == ("alpha", "beta")
    assert result.reported_server_name == "fixture"
    assert result.detail == ""
    _assert_group_gone(pgid_file)


def test_adapter_exited_after_writing_stderr(tmp_path: Path):
    script, pgid_file = _py_server(
        tmp_path,
        "exits",
        "import sys\nprint('Traceback (most recent call last):', file=sys.stderr)\n"
        "print(\"ModuleNotFoundError: No module named 'fastmcp'\", file=sys.stderr)\nsys.exit(1)\n",
    )
    result = _probe(tmp_path, script)
    assert result.outcome == "exited"
    assert result.exit_code == 1
    assert "ModuleNotFoundError: No module named 'fastmcp'" in result.stderr_tail
    _assert_group_gone(pgid_file)


def test_adapter_timed_out_when_the_server_never_answers(tmp_path: Path):
    script, pgid_file = _py_server(tmp_path, "never", "import sys\nfor _line in sys.stdin:\n    pass\n")
    started = time.monotonic()
    result = _probe(tmp_path, script, timeout_s=1.0)
    elapsed = time.monotonic() - started
    assert result.outcome == "timed-out"
    assert elapsed < 4.0, elapsed
    _assert_group_gone(pgid_file)


def test_adapter_timed_out_is_wall_clock_bounded_while_a_read_would_block(tmp_path: Path):
    """The server sleeps 12 s before answering; a one-second probe returns in about one second."""
    script, pgid_file = _py_server(
        tmp_path,
        "slow",
        """
        import json, sys, time
        for line in sys.stdin:
            msg = json.loads(line)
            if msg.get("method") == "initialize":
                time.sleep(12)
                print(json.dumps({"jsonrpc": "2.0", "id": msg["id"], "result": {"serverInfo": {"name": "s"}}}))
                sys.stdout.flush()
        """,
    )
    started = time.monotonic()
    result = _probe(tmp_path, script, timeout_s=1.0)
    assert result.outcome == "timed-out"
    assert time.monotonic() - started < 4.0
    _assert_group_gone(pgid_file)


def test_adapter_bad_reply_for_a_line_that_is_not_json_rpc(tmp_path: Path):
    script, pgid_file = _py_server(tmp_path, "notjson", "print('hello from a server that is not MCP')\n")
    result = _probe(tmp_path, script)
    assert result.outcome == "bad-reply"
    assert "hello from a server that is not MCP" in result.detail
    _assert_group_gone(pgid_file)


def test_adapter_error_reply_to_initialize(tmp_path: Path):
    script, pgid_file = _py_server(
        tmp_path,
        "errinit",
        'import json\nprint(json.dumps({"jsonrpc": "2.0", "id": 1, "error": {"code": -32602, "message": "nope"}}))\n',
    )
    result = _probe(tmp_path, script)
    assert result.outcome == "error-reply"
    assert "nope" in result.detail
    _assert_group_gone(pgid_file)


def test_adapter_error_reply_to_tools_list(tmp_path: Path):
    script, pgid_file = _py_server(
        tmp_path,
        "errtools",
        """
        import json, sys
        for line in sys.stdin:
            msg = json.loads(line)
            if msg.get("method") == "initialize":
                print(json.dumps({"jsonrpc": "2.0", "id": msg["id"], "result": {"serverInfo": {"name": "e"}}}))
            elif msg.get("method") == "tools/list":
                print(json.dumps({"jsonrpc": "2.0", "id": msg["id"], "error": {"code": -1, "message": "no tools"}}))
                sys.stdout.flush()
                break
            sys.stdout.flush()
        """,
    )
    result = _probe(tmp_path, script)
    assert result.outcome == "error-reply"
    assert result.reported_server_name == "e"
    _assert_group_gone(pgid_file)


def test_adapter_timed_out_with_a_forked_grandchild_and_the_group_is_gone(tmp_path: Path):
    """The server forks a grandchild (which inherits our pipes) and never answers: the whole group is stopped."""
    script, pgid_file = _py_server(
        tmp_path,
        "grandchild",
        """
        import subprocess, sys
        subprocess.Popen([sys.executable, "-c", "import time; time.sleep(600)"])
        for _line in sys.stdin:
            pass
        """,
    )
    started = time.monotonic()
    result = _probe(tmp_path, script, timeout_s=1.0)
    assert result.outcome == "timed-out"
    assert time.monotonic() - started < 5.0
    _assert_group_gone(pgid_file)


def test_adapter_started_after_one_mebibyte_of_stderr(tmp_path: Path):
    """stderr is read concurrently: a server that writes 1 MiB to stderr before answering still starts."""
    script, pgid_file = _py_server(
        tmp_path,
        "chatty",
        "import sys\nsys.stderr.write('x' * (1024 * 1024))\nsys.stderr.flush()\n" + textwrap.dedent(_ANSWERING_BODY),
    )
    started = time.monotonic()
    result = _probe(tmp_path, script)
    assert result.outcome == "started"
    assert result.tool_count == 2
    assert time.monotonic() - started < 4.0
    assert 0 < len(result.stderr_tail) <= 2048
    assert set(result.stderr_tail) == {"x"}
    _assert_group_gone(pgid_file)


def test_adapter_reads_a_reply_from_a_server_that_answers_and_exits(tmp_path: Path):
    """What the child wrote is parsed before its exit is judged: answering tools/list and exiting is ``started``."""
    script, pgid_file = _py_server(tmp_path, "answerexit", _ANSWERING_BODY.replace("break", "sys.exit(0)"))
    result = _probe(tmp_path, script)
    assert result.outcome == "started"
    assert result.tool_count == 2
    _assert_group_gone(pgid_file)


def test_adapter_exited_after_answering_initialize_only(tmp_path: Path):
    script, pgid_file = _py_server(
        tmp_path,
        "initexit",
        """
        import json, sys
        for line in sys.stdin:
            msg = json.loads(line)
            if msg.get("method") == "initialize":
                print(json.dumps({"jsonrpc": "2.0", "id": msg["id"], "result": {"serverInfo": {"name": "i"}}}))
                sys.stdout.flush()
                sys.exit(3)
        """,
    )
    result = _probe(tmp_path, script)
    assert result.outcome == "exited"
    assert result.exit_code == 3
    _assert_group_gone(pgid_file)


def test_adapter_exited_while_a_grandchild_holds_stdout(tmp_path: Path):
    """``sleep 600 & exit 1``: the shell exits, its background child keeps our stdout pipe open; no hang."""
    pgid_file = tmp_path / "shell.pgid"
    started = time.monotonic()
    result = StdioMcpProbe().probe_server(
        server_name="fixture",
        command="/bin/sh",
        args=("-c", f"echo $$ > {pgid_file}; sleep 600 & exit 1"),
        env={},
        cwd=str(tmp_path),
        timeout_s=2.0,
    )
    assert time.monotonic() - started < 5.0
    assert result.outcome == "exited"
    assert result.exit_code == 1
    _assert_group_gone(pgid_file)


def test_adapter_exited_while_a_grandchild_with_detached_pipes_lives(tmp_path: Path):
    pgid_file = tmp_path / "shell.pgid"
    result = StdioMcpProbe().probe_server(
        server_name="fixture",
        command="/bin/sh",
        args=("-c", f"echo $$ > {pgid_file}; sleep 600 </dev/null >/dev/null 2>&1 & exit 1"),
        env={},
        cwd=str(tmp_path),
        timeout_s=2.0,
    )
    assert result.outcome == "exited"
    _assert_group_gone(pgid_file)


def test_adapter_stops_a_grandchild_that_ignores_sigterm(tmp_path: Path):
    script, pgid_file = _py_server(
        tmp_path,
        "ignoreterm",
        """
        import subprocess, sys, time
        subprocess.Popen(
            [sys.executable, "-c", "import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(600)"]
        )
        time.sleep(600)
        """,
    )
    started = time.monotonic()
    result = _probe(tmp_path, script, timeout_s=1.0)
    assert result.outcome == "timed-out"
    assert time.monotonic() - started < 8.0
    _assert_group_gone(pgid_file)


def test_adapter_bad_reply_when_the_server_closes_stdout_and_lives(tmp_path: Path):
    """EOF on stdout while the child lives is not a busy loop: a short grace for an exit, then ``bad-reply``."""
    script, pgid_file = _py_server(tmp_path, "closeout", "import os, time\nos.close(1)\ntime.sleep(600)\n")
    started = time.monotonic()
    result = _probe(tmp_path, script, timeout_s=5.0)
    assert result.outcome == "bad-reply"
    assert "closed its stdout" in result.detail
    assert time.monotonic() - started < 4.0
    _assert_group_gone(pgid_file)


def test_adapter_judges_a_server_that_closes_stdin_without_crashing(tmp_path: Path):
    script, pgid_file = _py_server(tmp_path, "closein", "import os, time\nos.close(0)\ntime.sleep(600)\n")
    result = _probe(tmp_path, script, timeout_s=1.0)
    assert result.outcome in ("bad-reply", "timed-out")
    _assert_group_gone(pgid_file)


def test_adapter_bad_reply_when_initialize_result_has_no_server_info(tmp_path: Path):
    script, pgid_file = _py_server(
        tmp_path,
        "noinfo",
        'import json\nprint(json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"capabilities": {}}}))\n',
    )
    result = _probe(tmp_path, script)
    assert result.outcome == "bad-reply"
    assert "serverInfo" in result.detail
    _assert_group_gone(pgid_file)


def test_adapter_bad_reply_when_tools_list_result_has_no_tools(tmp_path: Path):
    script, pgid_file = _py_server(tmp_path, "notools", _ANSWERING_BODY.replace('{"tools": [{"name": "alpha"}, {"name": "beta"}]}', "{}"))
    result = _probe(tmp_path, script)
    assert result.outcome == "bad-reply"
    assert "tools" in result.detail
    assert result.reported_server_name == "fixture"
    _assert_group_gone(pgid_file)


def test_adapter_skips_notifications_and_other_ids(tmp_path: Path):
    script, pgid_file = _py_server(
        tmp_path,
        "noise",
        textwrap.dedent(
            """
            import json, sys
            print(json.dumps({"jsonrpc": "2.0", "method": "notifications/message", "params": {"level": "info"}}))
            print(json.dumps({"jsonrpc": "2.0", "id": 99, "result": {"serverInfo": {"name": "stale"}}}))
            sys.stdout.flush()
            """
        )
        + textwrap.dedent(_ANSWERING_BODY),
    )
    result = _probe(tmp_path, script)
    assert result.outcome == "started"
    assert result.reported_server_name == "fixture"
    _assert_group_gone(pgid_file)


def test_adapter_spawn_failed_for_a_missing_binary(tmp_path: Path):
    result = StdioMcpProbe().probe_server(
        server_name="fixture",
        command=str(tmp_path / "no-such-binary"),
        args=(),
        env={},
        cwd=str(tmp_path),
        timeout_s=1.0,
    )
    assert result.outcome == "spawn-failed"
    assert "no-such-binary" in result.detail


def test_adapter_passes_rendered_args_and_env_with_the_home_as_cwd(tmp_path: Path):
    home = tmp_path / "home"
    home.mkdir()
    script, pgid_file = _py_server(
        tmp_path,
        "envcheck",
        textwrap.dedent(
            """
            import os, sys
            assert os.environ.get("PROBE_FOO") == "bar", os.environ.get("PROBE_FOO")
            assert os.getcwd() == os.path.realpath(sys.argv[2]), (os.getcwd(), sys.argv[2])
            assert sys.argv[1] == "extra", sys.argv
            """
        )
        + textwrap.dedent(_ANSWERING_BODY),
    )
    result = probe_server_from_rendered(
        server_name="s",
        rendered={"command": sys.executable, "args": [script, "extra", str(home)], "env": {"PROBE_FOO": "bar"}},
        home=home,
    )
    assert result.outcome == "started", result
    _assert_group_gone(pgid_file)


def test_probe_server_from_rendered_without_a_command_is_spawn_failed(tmp_path: Path):
    result = probe_server_from_rendered(server_name="x", rendered={}, home=tmp_path)
    assert result.outcome == "spawn-failed"
    assert "no command" in result.detail


def test_probe_server_from_rendered_forwards_to_the_injected_port(tmp_path: Path):
    seen: dict[str, object] = {}

    class _Recording:
        def probe_server(self, **kwargs):
            seen.update(kwargs)
            return McpProbeResult(outcome="started", server_name=kwargs["server_name"], tool_count=0)

    probe_server_from_rendered(
        server_name="s",
        rendered={"command": "cmd", "args": ["a", 1], "env": {"K": 2}},
        home=tmp_path,
        probe=_Recording(),
    )
    assert seen == {
        "server_name": "s",
        "command": "cmd",
        "args": ("a", "1"),
        "env": {"K": "2"},
        "cwd": str(tmp_path),
        "timeout_s": probe_mod.MCP_PROBE_TIMEOUT_S,
    }
    assert probe_mod.MCP_PROBE_TIMEOUT_S == 15.0


def test_default_mcp_probe_is_the_stdio_adapter():
    assert isinstance(default_mcp_probe(), StdioMcpProbe)


# --- the adapter's parts ----------------------------------------------------------------------------------------


def test_parse_buffered_waits_for_a_complete_line():
    buf = bytearray(b'{"jsonrpc":"2.0","id":1,"result":{}')
    assert _parse_buffered(buf, expected_id=1) == (None, None, "")
    assert bytes(buf).startswith(b'{"jsonrpc"')


def test_parse_buffered_skips_blank_lines_notifications_requests_and_other_ids():
    buf = bytearray(
        b"\n"
        b'{"jsonrpc":"2.0","method":"notifications/message","params":{}}\n'
        b'{"jsonrpc":"2.0","id":"srv-1","method":"roots/list"}\n'
        b'{"jsonrpc":"2.0","id":7,"result":{"other":true}}\n'
        b'{"jsonrpc":"2.0","id":7,"error":{"code":1,"message":"not ours"}}\n'
        b'{"jsonrpc":"2.0","id":1,"result":{"serverInfo":{"name":"x"}}}\n'
    )
    reply, error, detail = _parse_buffered(buf, expected_id=1)
    assert error is None and detail == ""
    assert reply is not None and reply["id"] == 1
    assert not buf


@pytest.mark.parametrize(
    "line, error, fragment",
    [
        (b"not json at all\n", "bad-reply", "not json at all"),
        (b"[1, 2, 3]\n", "bad-reply", "[1, 2, 3]"),
        (b'{"jsonrpc":"2.0","id":1,"error":{"code":-32600,"message":"bad"}}\n', "error-reply", "bad"),
        (b'{"jsonrpc":"2.0","id":null,"error":{"code":-32700,"message":"parse error"}}\n', "error-reply", "parse"),
    ],
)
def test_parse_buffered_reports_bad_and_error_replies_with_detail(line: bytes, error: str, fragment: str):
    reply, got_error, detail = _parse_buffered(bytearray(line), expected_id=1)
    assert reply is None
    assert got_error == error
    assert fragment in detail


def test_append_tail_keeps_the_last_two_kibibytes():
    tail = [""]
    _append_tail(tail, "a" * 3000)
    _append_tail(tail, "b" * 10)
    assert len(tail[0]) == 2048
    assert tail[0].endswith("b" * 10)


def test_stderr_reader_fd_reads_chunks_to_eof():
    read_end, write_end = os.pipe()
    os.write(write_end, b"hello stderr")
    os.close(write_end)
    tail = [""]
    _stderr_reader_fd(read_end, tail, threading.Event())
    os.close(read_end)
    assert tail[0] == "hello stderr"


@pytest.mark.parametrize("source_type", [_SelectorChunks, _ThreadChunks])
def test_chunk_sources_deliver_data_then_report_eof_without_waiting(source_type):
    read_end, write_end = os.pipe()
    source = source_type(read_end)
    try:
        assert source.next_chunk(0.05) is None  # nothing yet
        os.write(write_end, b"abc")
        assert source.next_chunk(1.0) == b"abc"
        os.close(write_end)
        started = time.monotonic()
        assert source.next_chunk(1.0) == b""
        assert source.next_chunk(1.0) == b""  # EOF stays EOF, and never spins or blocks
        assert time.monotonic() - started < 0.5
        assert source.busy() is False
    finally:
        source.close()
        os.close(read_end)


def test_open_chunks_uses_a_reader_thread_on_windows(monkeypatch: pytest.MonkeyPatch):
    read_end, write_end = os.pipe()
    try:
        monkeypatch.setattr(probe_mod.sys, "platform", "win32")
        source = _open_chunks(read_end)
        assert isinstance(source, _ThreadChunks)
        os.close(write_end)
        assert source.next_chunk(1.0) == b""
        source.close()
        monkeypatch.setattr(probe_mod.sys, "platform", "linux")
        assert isinstance(_open_chunks(read_end), _SelectorChunks)
    finally:
        os.close(read_end)


class _FakeProc:
    """A ``Popen`` stand-in for ``_read_reply``: ``returncode`` is what ``poll``/``wait`` report."""

    pid = 424242

    def __init__(self, returncode: int | None = None, *, exits_after_wait: int | None = None) -> None:
        self.returncode = returncode
        self._exits_after_wait = exits_after_wait
        self.waits: list[float] = []

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        self.waits.append(timeout)
        if self.returncode is None and self._exits_after_wait is not None:
            self.returncode = self._exits_after_wait
        if self.returncode is None:
            raise subprocess.TimeoutExpired("fake", timeout)
        return self.returncode


def _reply_line(request_id: int, result: dict) -> bytes:
    return json.dumps({"jsonrpc": "2.0", "id": request_id, "result": result}).encode() + b"\n"


def test_read_reply_returns_the_matching_reply():
    read_end, write_end = os.pipe()
    os.write(write_end, _reply_line(1, {"ok": True}))
    source = _SelectorChunks(read_end)
    try:
        reply, error, detail = _read_reply(_FakeProc(), source, bytearray(), deadline=time.monotonic() + 1, expected_id=1)
    finally:
        source.close()
        os.close(write_end)
        os.close(read_end)
    assert error is None and detail == ""
    assert reply == {"jsonrpc": "2.0", "id": 1, "result": {"ok": True}}


def test_read_reply_parses_what_an_exited_child_wrote_before_reporting_exited():
    read_end, write_end = os.pipe()
    os.write(write_end, _reply_line(2, {"tools": []}))
    os.close(write_end)
    source = _SelectorChunks(read_end)
    try:
        reply, error, _ = _read_reply(_FakeProc(returncode=0), source, bytearray(), deadline=time.monotonic() + 1, expected_id=2)
        assert error is None and reply is not None and reply["id"] == 2
        reply, error, _ = _read_reply(_FakeProc(returncode=0), source, bytearray(), deadline=time.monotonic() + 1, expected_id=3)
        assert (reply, error) == (None, "exited")
    finally:
        source.close()
        os.close(read_end)


def test_read_reply_times_out_at_the_deadline_while_the_child_lives():
    read_end, write_end = os.pipe()
    source = _SelectorChunks(read_end)
    try:
        started = time.monotonic()
        reply, error, _ = _read_reply(_FakeProc(), source, bytearray(), deadline=time.monotonic() + 0.2, expected_id=1)
        assert (reply, error) == (None, "timed-out")
        assert 0.15 < time.monotonic() - started < 1.0
    finally:
        source.close()
        os.close(write_end)
        os.close(read_end)


def test_read_reply_eof_while_alive_waits_a_grace_then_is_bad_reply(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(probe_mod, "_CLOSE_GRACE_S", 0.1)
    read_end, write_end = os.pipe()
    os.close(write_end)
    source = _SelectorChunks(read_end)
    proc = _FakeProc()
    try:
        reply, error, detail = _read_reply(proc, source, bytearray(), deadline=time.monotonic() + 5, expected_id=1)
    finally:
        source.close()
        os.close(read_end)
    assert (reply, error) == (None, "bad-reply")
    assert "closed its stdout" in detail
    assert proc.waits and proc.waits[0] <= 0.1


def test_read_reply_eof_while_alive_is_exited_when_the_child_exits_in_the_grace():
    read_end, write_end = os.pipe()
    os.close(write_end)
    source = _SelectorChunks(read_end)
    try:
        reply, error, _ = _read_reply(
            _FakeProc(exits_after_wait=5), source, bytearray(), deadline=time.monotonic() + 5, expected_id=1
        )
    finally:
        source.close()
        os.close(read_end)
    assert (reply, error) == (None, "exited")


class _StopProc:
    """A ``Popen`` stand-in for ``_stop_process_group``: records every call."""

    def __init__(self, pid: int = 7, *, wait_outcomes: list[int | None] | None = None) -> None:
        self.pid = pid
        self.returncode: int | None = None
        self.calls: list[str] = []
        self._wait_outcomes = list(wait_outcomes or [])

    def poll(self):
        return self.returncode

    def terminate(self):
        self.calls.append("terminate")

    def kill(self):
        self.calls.append("kill")

    def wait(self, timeout=None):
        self.calls.append(f"wait({timeout})")
        outcome = self._wait_outcomes.pop(0) if self._wait_outcomes else 0
        if outcome is None:
            raise subprocess.TimeoutExpired("fake", timeout)
        self.returncode = outcome
        return outcome


def test_stop_process_group_signals_the_group_term_then_kill_then_reaps(monkeypatch: pytest.MonkeyPatch):
    signals: list[tuple[int, int]] = []
    monkeypatch.setattr(probe_mod.os, "killpg", lambda pgid, sig: signals.append((pgid, sig)))
    proc = _StopProc(pid=42)
    _stop_process_group(proc)
    assert signals == [(42, probe_mod.signal.SIGTERM), (42, probe_mod.signal.SIGKILL)]
    assert proc.calls == [f"wait({probe_mod._TERM_GRACE_S})", f"wait({probe_mod._REAP_TIMEOUT_S})"]


def test_stop_process_group_sends_sigkill_even_when_the_group_is_already_gone(monkeypatch: pytest.MonkeyPatch):
    signals: list[int] = []

    def killpg(_pgid, sig):
        signals.append(sig)
        raise ProcessLookupError

    monkeypatch.setattr(probe_mod.os, "killpg", killpg)
    proc = _StopProc()
    _stop_process_group(proc)
    assert signals == [probe_mod.signal.SIGTERM, probe_mod.signal.SIGKILL]
    assert "terminate" not in proc.calls and "kill" not in proc.calls


def test_stop_process_group_falls_back_to_the_child_when_killpg_fails(monkeypatch: pytest.MonkeyPatch):
    def killpg(_pgid, _sig):
        raise PermissionError("killpg refused")

    monkeypatch.setattr(probe_mod.os, "killpg", killpg)
    proc = _StopProc()
    _stop_process_group(proc)
    assert "terminate" in proc.calls and "kill" in proc.calls


def test_stop_process_group_kills_the_child_again_when_the_reap_times_out(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(probe_mod.os, "killpg", lambda _pgid, _sig: None)
    proc = _StopProc(wait_outcomes=[None, None, -9])
    _stop_process_group(proc)
    assert proc.calls.count("kill") == 1
    assert proc.returncode == -9


def test_stop_process_group_terminates_a_real_running_child(tmp_path: Path):
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    _stop_process_group(proc)
    assert proc.poll() is not None
    with pytest.raises(ProcessLookupError):
        os.killpg(proc.pid, 0)


def test_stop_windows_terminates_then_kills_and_sends_ctrl_break(monkeypatch: pytest.MonkeyPatch):
    kills: list[tuple[int, int]] = []
    monkeypatch.setattr(probe_mod.sys, "platform", "win32")
    monkeypatch.setattr(probe_mod.signal, "CTRL_BREAK_EVENT", 21, raising=False)
    monkeypatch.setattr(probe_mod.os, "kill", lambda pid, sig: kills.append((pid, sig)))
    gentle = _StopProc(pid=9)
    _stop_process_group(gentle)
    assert kills == [(9, 21)]
    assert gentle.calls == ["terminate", f"wait({probe_mod._TERM_GRACE_S})"]
    stubborn = _StopProc(pid=10, wait_outcomes=[None, 1])
    _stop_process_group(stubborn)
    assert stubborn.calls == ["terminate", f"wait({probe_mod._TERM_GRACE_S})", "kill", f"wait({probe_mod._REAP_TIMEOUT_S})"]


def test_stop_windows_without_ctrl_break_only_signals_the_child(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(probe_mod.sys, "platform", "win32")
    monkeypatch.delattr(probe_mod.signal, "CTRL_BREAK_EVENT", raising=False)
    monkeypatch.setattr(probe_mod.os, "kill", lambda *_a: pytest.fail("os.kill must not run without CTRL_BREAK_EVENT"))
    proc = _StopProc()
    _stop_process_group(proc)
    assert proc.calls[0] == "terminate"


class _FakeDuplexProc:
    """Stands in for ``Popen`` on the Windows path: answers each request through a real pipe."""

    pid = 4242

    def __init__(self) -> None:
        out_read, self._out_write = os.pipe()
        err_read, err_write = os.pipe()
        os.close(err_write)
        self.stdout = io.FileIO(out_read, "r")
        self.stderr = io.FileIO(err_read, "r")
        self.stdin = self
        self.returncode: int | None = None
        self.calls: list[str] = []

    def write(self, data: bytes) -> None:
        message = json.loads(data)
        if message.get("method") == "initialize":
            os.write(self._out_write, _reply_line(message["id"], {"serverInfo": {"name": "win"}, "capabilities": {}}))
        elif message.get("method") == "tools/list":
            os.write(self._out_write, _reply_line(message["id"], {"tools": [{"name": "w"}]}))

    def flush(self) -> None:
        pass

    def close(self) -> None:
        pass

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        if self.returncode is None:
            raise subprocess.TimeoutExpired("fake", timeout)
        return self.returncode

    def terminate(self) -> None:
        self.calls.append("terminate")
        if self.returncode is None:
            self.returncode = 0
            os.close(self._out_write)

    def kill(self) -> None:
        self.calls.append("kill")


def test_probe_server_on_windows_spawns_a_new_process_group_and_reads_through_the_thread(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    spawned: list[dict[str, object]] = []
    fake = _FakeDuplexProc()

    def fake_popen(argv, **kwargs):
        spawned.append({"argv": argv, **kwargs})
        return fake

    monkeypatch.setattr(probe_mod.sys, "platform", "win32")
    monkeypatch.delattr(probe_mod.signal, "CTRL_BREAK_EVENT", raising=False)
    monkeypatch.setattr(probe_mod.subprocess, "CREATE_NEW_PROCESS_GROUP", 512, raising=False)
    monkeypatch.setattr(probe_mod.subprocess, "Popen", fake_popen)

    result = StdioMcpProbe().probe_server(
        server_name="win", command="server.exe", args=("--stdio",), env={"K": "V"}, cwd=str(tmp_path), timeout_s=5.0
    )
    assert result.outcome == "started"
    assert result.tool_names == ("w",)
    assert result.reported_server_name == "win"
    assert spawned[0]["argv"] == ["server.exe", "--stdio"]
    assert spawned[0]["creationflags"] == 512
    assert "start_new_session" not in spawned[0]
    assert spawned[0]["env"]["K"] == "V"
    assert "terminate" in fake.calls


def test_probe_server_maps_an_unexpected_exception_to_bad_reply_and_still_stops(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    script, pgid_file = _py_server(tmp_path, "boom", "import sys\nfor _line in sys.stdin:\n    pass\n")

    def exploding(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(probe_mod, "_handshake", exploding)
    result = _probe(tmp_path, script)
    assert result.outcome == "bad-reply"
    assert "RuntimeError: boom" in result.detail
    _assert_group_gone(pgid_file)


def test_probe_server_maps_an_unexpected_exception_to_exited_when_the_child_already_exited(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    script, pgid_file = _py_server(tmp_path, "boomexit", "import sys\nsys.exit(4)\n")

    def exploding(proc, *_args, **_kwargs):
        proc.wait(timeout=5)
        raise RuntimeError("boom")

    monkeypatch.setattr(probe_mod, "_handshake", exploding)
    result = _probe(tmp_path, script)
    assert result.outcome == "exited"
    assert result.exit_code == 4
    assert "boom" in result.detail
    _assert_group_gone(pgid_file)


def test_probe_server_result_carries_stderr_written_up_to_the_stop(tmp_path: Path):
    """The result is built after the stop and the reader join, so stderr written just before exit is in the tail."""
    script, pgid_file = _py_server(
        tmp_path,
        "lateerr",
        """
        import json, sys
        for line in sys.stdin:
            msg = json.loads(line)
            if msg.get("method") == "initialize":
                print("late stderr line", file=sys.stderr)
                sys.stderr.flush()
                sys.exit(2)
        """,
    )
    result = _probe(tmp_path, script)
    assert result.outcome == "exited"
    assert "late stderr line" in result.stderr_tail
    _assert_group_gone(pgid_file)


# --- the pure verdict (core/mcp_probe.py) -----------------------------------------------------------------------


def test_evaluate_started_with_tools_is_startable_without_findings():
    ok, findings = evaluate_mcp_probe(
        McpProbeResult(outcome="started", server_name="marshal", tool_count=8), mcp_json_path="/h/.mcp.json"
    )
    assert ok is True
    assert findings == []


def test_evaluate_started_without_a_tool_count_is_not_startable():
    ok, findings = evaluate_mcp_probe(McpProbeResult(outcome="started", server_name="m"), mcp_json_path="/h/.mcp.json")
    assert ok is False
    assert [f.code for f in findings] == ["MRS-PREFLIGHT-012"]


@pytest.mark.parametrize("outcome", ["exited", "timed-out", "bad-reply", "error-reply", "spawn-failed"])
def test_evaluate_failure_is_one_redacted_preflight_012(outcome: str):
    ok, findings = evaluate_mcp_probe(
        McpProbeResult(
            outcome=outcome,
            server_name="marshal",
            exit_code=1 if outcome == "exited" else None,
            stderr_tail=f"ModuleNotFoundError: No module named 'fastmcp' (token {_TOKEN})",
            detail=f"detail with {_TOKEN}",
        ),
        mcp_json_path="/h/.mcp.json",
    )
    assert ok is False
    assert len(findings) == 1
    finding = findings[0]
    assert finding.code == "MRS-PREFLIGHT-012"
    assert finding.path == "/h/.mcp.json"
    assert "'marshal'" in finding.message
    assert f"outcome={outcome}" in finding.message
    assert ("exit_code=1" in finding.message) == (outcome == "exited")
    assert "ModuleNotFoundError" in finding.message
    assert _TOKEN not in finding.message
    assert finding.message.count(_REDACTED) == 2


def test_evaluate_never_prints_text_it_could_not_redact(monkeypatch: pytest.MonkeyPatch):
    import pyforge.marshal.core.mcp_probe as core_mod

    monkeypatch.setattr(core_mod, "redact_raw_text", lambda _text: None)
    _, findings = evaluate_mcp_probe(
        McpProbeResult(outcome="exited", server_name="m", stderr_tail="secret"), mcp_json_path="/h/.mcp.json"
    )
    assert "secret" not in findings[0].message
    assert "[unredactable]" in findings[0].message


def test_mutation_timed_out_not_startable():
    """AC8: mapping ``timed-out`` to startable fails here."""
    ok, findings = evaluate_mcp_probe(McpProbeResult(outcome="timed-out", server_name="x"), mcp_json_path="/x")
    assert ok is False
    assert findings and "outcome=timed-out" in findings[0].message


# --- AC5: the outcomes through _probe_mcp_servers (run_preflight --format json) --------------------------------


class _ScriptedProbe:
    """Injected ``McpProbePort``: returns the scripted result and records every call."""

    def __init__(self, result: McpProbeResult) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def probe_server(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


class _FailIfCalledProbe:
    def probe_server(self, **kwargs):
        pytest.fail(f"the probe ran where no probe is due: {kwargs!r}")


def _preflight_json(repo_root: Path, tmp_path: Path, monkeypatch, capsys, *, mcp_json, probe, slug="acme", server="atlas", command="atlas-mcp", binaries=("atlas-mcp",)):
    import test_init as init_mod

    home = tmp_path / "loop-homes" / slug
    fs = init_mod.FakeFs(project_dirs={home})
    if mcp_json is not None:
        fs.texts[home / ".mcp.json"] = mcp_json
    harness = init_mod._converged_harness()
    harness.binaries_present.update(binaries)
    init_mod._seed_acknowledged(fs, tmp_path, ["claude"])
    policy_path = tmp_path / "marshal-policy.toml"
    policy_path.write_text(f'[mcp_servers.{server}]\ncommand = "{command}"\n', encoding="utf-8")
    monkeypatch.setattr(init_module, "conventional_project_policy_path", lambda _slug: policy_path)
    vcs = init_mod.FakeVcs(repo_root=repo_root)
    exit_code = run_preflight(init_mod._preflight_namespace(slug, fmt="json"), vcs=vcs, fs=fs, harness=harness, mcp_probe=probe)
    envelope = json.loads(capsys.readouterr().out)
    return exit_code, envelope, home


def _preflight_012(envelope: dict) -> list[dict]:
    return [f for f in envelope["findings"] if f["code"] == "MRS-PREFLIGHT-012"]


def test_probe_mcp_servers_started_is_startable_with_its_tool_count(repo_root, tmp_path, monkeypatch, capsys):
    probe = _ScriptedProbe(McpProbeResult(outcome="started", server_name="atlas", tool_count=3, tool_names=("a", "b", "c")))
    exit_code, envelope, home = _preflight_json(
        repo_root, tmp_path, monkeypatch, capsys,
        mcp_json=json.dumps({"mcpServers": {"atlas": {"command": "atlas-mcp", "args": ["--x"], "env": {"A": "1"}}}}),
        probe=probe,
    )
    assert exit_code == EXIT_OK
    assert envelope["data"]["mcp_servers"] == [
        {"name": "atlas", "command": "atlas-mcp", "resolvable": True, "startable": True, "tool_count": 3}
    ]
    assert _preflight_012(envelope) == []
    # The handshake used the home's rendered entry, with the home as cwd.
    assert probe.calls == [
        {"server_name": "atlas", "command": "atlas-mcp", "args": ("--x",), "env": {"A": "1"}, "cwd": str(home), "timeout_s": 15.0}
    ]


@pytest.mark.parametrize("outcome", ["exited", "timed-out", "bad-reply", "error-reply", "spawn-failed"])
def test_probe_mcp_servers_failure_outcome_is_not_startable_and_one_redacted_012(
    outcome: str, repo_root, tmp_path, monkeypatch, capsys
):
    probe = _ScriptedProbe(
        McpProbeResult(
            outcome=outcome,
            server_name="atlas",
            exit_code=1 if outcome == "exited" else None,
            stderr_tail=f"ModuleNotFoundError: No module named 'fastmcp' {_TOKEN}",
        )
    )
    exit_code, envelope, _ = _preflight_json(
        repo_root, tmp_path, monkeypatch, capsys,
        mcp_json=json.dumps({"mcpServers": {"atlas": {"command": "atlas-mcp"}}}),
        probe=probe,
    )
    assert exit_code != EXIT_OK
    assert len(probe.calls) == 1
    (entry,) = envelope["data"]["mcp_servers"]
    assert entry["resolvable"] is True
    assert entry["startable"] is False
    assert "tool_count" not in entry
    (finding,) = _preflight_012(envelope)
    assert "'atlas'" in finding["message"]
    assert f"outcome={outcome}" in finding["message"]
    assert "ModuleNotFoundError" in finding["message"]
    assert _TOKEN not in finding["message"]
    assert _REDACTED in finding["message"]


def test_probe_mcp_servers_unresolvable_command_keeps_its_message_and_runs_no_probe(repo_root, tmp_path, monkeypatch, capsys):
    exit_code, envelope, _ = _preflight_json(
        repo_root, tmp_path, monkeypatch, capsys,
        mcp_json=json.dumps({"mcpServers": {"atlas": {"command": "definitely-not-a-real-binary-xyz"}}}),
        probe=_FailIfCalledProbe(),
        command="definitely-not-a-real-binary-xyz",
        binaries=(),
    )
    assert exit_code != EXIT_OK
    (entry,) = envelope["data"]["mcp_servers"]
    assert entry == {"name": "atlas", "command": "definitely-not-a-real-binary-xyz", "resolvable": False}
    (finding,) = _preflight_012(envelope)
    assert "not resolvable on PATH or as an absolute path" in finding["message"]


def test_probe_mcp_servers_missing_mcp_json_runs_no_probe(repo_root, tmp_path, monkeypatch, capsys):
    exit_code, envelope, _ = _preflight_json(repo_root, tmp_path, monkeypatch, capsys, mcp_json=None, probe=_FailIfCalledProbe())
    assert exit_code != EXIT_OK
    assert envelope["data"]["mcp_servers"] == []
    (finding,) = _preflight_012(envelope)
    assert "does not exist" in finding["message"]


def test_mutation_skipping_handshake_in_probe_would_miss_finding(repo_root, tmp_path, monkeypatch, capsys):
    """AC8: a resolvable server whose handshake fails must reach the probe and emit MRS-PREFLIGHT-012."""
    probe = _ScriptedProbe(
        McpProbeResult(outcome="exited", server_name="atlas", exit_code=1, stderr_tail="ModuleNotFoundError: fastmcp")
    )
    exit_code, envelope, _ = _preflight_json(
        repo_root, tmp_path, monkeypatch, capsys,
        mcp_json=json.dumps({"mcpServers": {"atlas": {"command": "atlas-mcp"}}}),
        probe=probe,
    )
    assert probe.calls, "the handshake was never attempted"
    assert exit_code != EXIT_OK
    (finding,) = _preflight_012(envelope)
    assert "outcome=exited" in finding["message"]


def test_mutation_dropping_stop_process_group_leaves_a_grandchild(tmp_path: Path):
    """AC8: with the stop dropped, the ``sleep 600`` grandchild of an exited child survives and this fails."""
    script, pgid_file = _py_server(
        tmp_path,
        "orphan",
        """
        import subprocess, sys, time
        subprocess.Popen([sys.executable, "-c", "import time; time.sleep(600)"])
        time.sleep(0.05)
        sys.exit(1)
        """,
    )
    result = _probe(tmp_path, script, timeout_s=2.0)
    assert result.outcome == "exited"
    _assert_group_gone(pgid_file)


# --- AC7: preflight end to end through the real adapter --------------------------------------------------------


@pytest.mark.skipif(shutil.which("marshal-mcp") is None, reason="marshal-mcp is not on PATH")
def test_preflight_json_through_the_real_adapter_shows_marshal_mcp_startable_with_eight_tools(
    repo_root, tmp_path, monkeypatch, capsys
):
    (tmp_path / "loop-homes" / "pyforge-marshal").mkdir(parents=True)  # the home is the server's cwd
    exit_code, envelope, _ = _preflight_json(
        repo_root, tmp_path, monkeypatch, capsys,
        slug="pyforge-marshal",
        server="marshal",
        command="marshal-mcp",
        binaries=("marshal-mcp",),
        mcp_json=json.dumps({"mcpServers": {"marshal": {"command": "marshal-mcp", "args": []}}}),
        probe=StdioMcpProbe(),
    )
    assert exit_code == EXIT_OK
    (entry,) = envelope["data"]["mcp_servers"]
    assert entry["startable"] is True
    assert entry["tool_count"] == 8
    assert _preflight_012(envelope) == []


def test_preflight_json_through_the_real_adapter_reports_a_fastmcp_style_crash(repo_root, tmp_path, monkeypatch, capsys):
    """A stand-in for the pre-103.1 server: ``marshal-mcp`` on PATH imports a module that is not installed."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    crashing = tmp_path / "crashing_server.py"
    crashing.write_text("import fastmcp_stand_in_for_the_absent_dependency\n", encoding="utf-8")
    stand_in = bin_dir / "marshal-mcp"
    stand_in.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{crashing}" "$@"\n', encoding="utf-8")
    stand_in.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    (tmp_path / "loop-homes" / "pyforge-marshal").mkdir(parents=True)

    exit_code, envelope, _ = _preflight_json(
        repo_root, tmp_path, monkeypatch, capsys,
        slug="pyforge-marshal",
        server="marshal",
        command="marshal-mcp",
        binaries=("marshal-mcp",),
        mcp_json=json.dumps({"mcpServers": {"marshal": {"command": "marshal-mcp"}}}),
        probe=StdioMcpProbe(),
    )
    assert exit_code != EXIT_OK
    (entry,) = envelope["data"]["mcp_servers"]
    assert entry["startable"] is False
    (finding,) = _preflight_012(envelope)
    assert "outcome=exited" in finding["message"]
    assert "exit_code=1" in finding["message"]
    assert "ModuleNotFoundError" in finding["message"]


# --- AC1: the real console script through the adapter ----------------------------------------------------------


@pytest.mark.skipif(shutil.which("marshal-mcp") is None, reason="marshal-mcp is not on PATH")
def test_real_marshal_mcp_answers_initialize_and_lists_exactly_the_eight_tools(tmp_path: Path):
    resolved = shutil.which("marshal-mcp")
    assert resolved is not None
    result = StdioMcpProbe().probe_server(
        server_name="marshal", command=resolved, args=(), env={}, cwd=str(tmp_path), timeout_s=20.0
    )
    assert result.outcome == "started", result
    assert result.reported_server_name == "pyforge-marshal"
    assert result.tool_count == 8
    assert set(result.tool_names) == EIGHT_TOOLS


# --- AC2: the tools are registered, in process ------------------------------------------------------------------


def test_build_server_registers_exactly_the_eight_tools():
    import asyncio

    from pyforge.marshal.mcp import server as server_mod

    server = server_mod.build_server()
    tools = asyncio.run(server.list_tools())
    assert {t.name for t in tools} == EIGHT_TOOLS


@pytest.mark.parametrize(
    "tool_name, arguments, forwarded",
    [
        ("list_marshal_tools", {}, {}),
        ("marshal_status", {"project": "acme"}, {"project": "acme"}),
        ("marshal_check", {"scope": "all", "project": None}, {"scope": "all", "project": None}),
        ("marshal_homes", {}, {}),
        ("marshal_preflight", {"slug": "pyforge-marshal"}, {"slug": "pyforge-marshal"}),
        ("marshal_upstream", {}, {}),
        ("marshal_refresh", {"project": "acme", "base": "main"}, {"project": "acme", "base": "main"}),
        ("marshal_watch", {"project": None, "run": "r1", "fleet": True}, {"project": None, "run": "r1", "fleet": True}),
    ],
)
def test_build_server_tool_call_returns_the_tools_function_value(tool_name, arguments, forwarded, monkeypatch):
    """Each registered tool delegates to its ``tools.py`` function: a monkeypatched one is what the call returns."""
    import asyncio

    from pyforge.marshal.mcp import server as server_mod
    from pyforge.marshal.mcp import tools as tools_mod

    stub_value = {"stubbed": tool_name, "forwarded": forwarded}
    received: list[dict] = []

    def stub(**kwargs):
        received.append(kwargs)
        return stub_value

    monkeypatch.setattr(tools_mod, tool_name, stub)
    server = server_mod.build_server()
    outcome = asyncio.run(server.call_tool(tool_name, arguments))
    assert outcome.is_error is False
    assert json.loads(outcome.content[0].text) == stub_value
    assert received == [forwarded]


def test_build_server_name_is_pyforge_marshal():
    from pyforge.marshal.mcp import server as server_mod

    assert server_mod.SERVER_NAME == "pyforge-marshal"
    assert server_mod.build_server().name == "pyforge-marshal"


# --- AC3: no fastmcp --------------------------------------------------------------------------------------------


def test_no_module_under_pyforge_marshal_imports_fastmcp():
    offenders: list[str] = []
    for path in PACKAGE_SRC.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                offenders.extend(str(path) for alias in node.names if alias.name.split(".")[0] == "fastmcp")
            elif isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[0] == "fastmcp":
                offenders.append(str(path))
    assert offenders == []


def test_server_module_imports_with_the_mcp_sdk_blocked_and_build_server_names_mcp(monkeypatch):
    import builtins
    import importlib

    real_import = builtins.__import__

    def blocked(name, *args, **kwargs):
        if name == "mcp" or name.startswith("mcp."):
            raise ImportError("No module named 'mcp' (blocked for this test)")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked)
    sys.modules.pop("pyforge.marshal.mcp.server", None)
    module = importlib.import_module("pyforge.marshal.mcp.server")
    with pytest.raises(ImportError, match="mcp"):
        module.build_server()


# --- AC4: --help, --version, an unknown argument ----------------------------------------------------------------


def _never_build_server(*_args, **_kwargs):
    pytest.fail("build_server() ran for an argument that must never build the server")


def test_main_help_exits_zero_names_mcp_stdio_and_the_policy_key_without_building(monkeypatch, capsys):
    from pyforge.marshal.mcp import server as server_mod

    monkeypatch.setattr(server_mod, "build_server", _never_build_server)
    assert server_mod.main(["--help"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("usage: marshal-mcp")
    assert "MCP" in out and "stdio" in out and "[mcp_servers.marshal]" in out


def test_main_version_prints_the_installed_version_without_building(monkeypatch, capsys):
    from pyforge.marshal.mcp import server as server_mod

    monkeypatch.setattr(server_mod, "build_server", _never_build_server)
    assert server_mod.main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == installed_version("pyforge-marshal")


def test_main_unknown_argument_exits_two_without_building(monkeypatch, capsys):
    from pyforge.marshal.mcp import server as server_mod

    monkeypatch.setattr(server_mod, "build_server", _never_build_server)
    assert server_mod.main(["--totally-unknown"]) == 2
    assert "unrecognized arguments: --totally-unknown" in capsys.readouterr().err


def test_main_without_arguments_builds_and_runs_the_server(monkeypatch):
    from pyforge.marshal.mcp import server as server_mod

    ran: list[str] = []

    class _Server:
        def run(self):
            ran.append("run")

    monkeypatch.setattr(server_mod, "build_server", lambda: _Server())
    assert server_mod.main([]) == 0
    assert ran == ["run"]


def test_installed_version_degrades_when_the_distribution_is_absent(monkeypatch):
    from importlib import metadata

    from pyforge.marshal.mcp import server as server_mod

    def missing(_name):
        raise metadata.PackageNotFoundError("pyforge-marshal")

    monkeypatch.setattr(server_mod, "version", missing)
    assert "not installed" in server_mod._installed_version()


def _marshal_mcp_argv() -> list[str]:
    resolved = shutil.which("marshal-mcp")
    return [resolved] if resolved else [sys.executable, "-m", "pyforge.marshal.mcp"]


@pytest.mark.parametrize("flag", ["--help", "--version"])
def test_console_script_help_and_version_exit_zero_with_stdin_closed_within_five_seconds(flag: str):
    started = time.monotonic()
    completed = subprocess.run(
        [*_marshal_mcp_argv(), flag],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert time.monotonic() - started < 5.0
    if flag == "--help":
        assert "MCP" in completed.stdout and "stdio" in completed.stdout
    else:
        assert completed.stdout.strip() == installed_version("pyforge-marshal")


@pytest.mark.parametrize("flag", ["--help", "--version"])
def test_console_script_help_and_version_exit_zero_with_stdin_left_open(flag: str):
    """Nothing is ever written to or closed on stdin: an entry point that served stdio here would hang."""
    with subprocess.Popen(
        [*_marshal_mcp_argv(), flag], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    ) as proc:
        try:
            returncode = proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            pytest.fail(f"marshal-mcp {flag} did not exit within 5 s with stdin open")
        assert returncode == 0
        assert proc.stdout is not None and proc.stdout.read()


def test_python_m_pyforge_marshal_mcp_propagates_the_usage_exit_code():
    completed = subprocess.run(
        [sys.executable, "-m", "pyforge.marshal.mcp", "--bogus"],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert completed.returncode == 2
    assert "unrecognized arguments" in completed.stderr
