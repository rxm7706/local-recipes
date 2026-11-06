"""Epic 119: a start tool runs one fixed station verb from one closed table.

A fake ``pyforge`` stands in for each pixi environment, so these tests run the
worker's whole path, subprocess included, and no real verb. The real CLIs run in
``test_station_cli_live.py``.
"""

from __future__ import annotations

import importlib
import json
import stat
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest
from celery.exceptions import SoftTimeLimitExceeded
from django_pyforge import station_cli
from django_pyforge.assertion.client import lookup_portal_job
from django_pyforge.assertion.crypto import mint_assertion
from django_pyforge.flags import evaluate_from_source
from django_pyforge.models import RunState
from django_pyforge.queues import BUILDS_QUEUE
from django_pyforge.queues import queue_for
from django_pyforge.roles import ROLE_ADMIN
from django_pyforge.station_cli import ENVIRONMENT_ALLOWLIST
from django_pyforge.station_cli import STATION_VERBS
from django_pyforge.station_cli import STEWARD_DUTIES
from django_pyforge.station_cli import task_limits
from django_pyforge.supervisor import RunnerNotWiredError
from django_pyforge.supervisor import StationVerbFailedError
from django_pyforge.supervisor import claim_only_attempt
from django_pyforge.supervisor import get_run
from django_pyforge.supervisor import register_runner
from django_pyforge.supervisor import start_bounded
from django_pyforge.tasks import execute_supervised_run
from mcp.server.mcpserver.exceptions import ToolError

HOOK = Path(__file__).resolve().parents[3] / ".claude" / "hooks" / "pre-shell.py"

START_TOOL_CLI_FLAG_KEY = "pyforge.steward.start_tool_cli"
START_LOOP_DISPATCH_FLAG_KEY = "pyforge.steward.start_loop_dispatch"

GUILD = "pyforge-guild"
MASON = "pyforge-mason"
WARDEN = "pyforge-warden"
ENVIRONMENTS = (GUILD, MASON, WARDEN)

MODULES = {
    "doctor": "django_doctor_portal.mcp_asgi",
    "herald": "django_herald_portal.mcp_asgi",
    "marshal": "django_marshal_portal.mcp_asgi",
    "mason": "django_mason_portal.mcp_asgi",
    "scribe": "django_scribe_portal.mcp_asgi",
    "steward": "django_steward_portal.mcp_asgi",
    "warden": "django_warden_fabric.mcp_asgi",
}

#: The whole table, as a caller can reach it: (station, run tool) -> (start tool,
#: environment, target, argv after ``pyforge <station>``, result codes, admin, flag).
PINNED: dict[tuple[str, str], tuple[Any, ...]] = {
    ("doctor", "run_scan"): (
        "start_scan",
        GUILD,
        "numpy",
        ("diagnose", "--target", "numpy", "--json"),
        {0, 2},
        False,
        None,
    ),
    ("herald", "run_notice"): (
        "start_notice",
        GUILD,
        "api",
        ("notice", "get", "api"),
        {0},
        False,
        None,
    ),
    ("marshal", "run_loop"): (
        "start_loop",
        GUILD,
        "pyforge-steward/119-1-a",
        ("factory", "dispatch", "pyforge-steward", "119-1-a", "--format", "json"),
        {0},
        True,
        START_LOOP_DISPATCH_FLAG_KEY,
    ),
    ("mason", "run_build"): (
        "start_build",
        MASON,
        "demo",
        ("recipe", "build", "recipes/demo", "--format", "json"),
        {0},
        False,
        None,
    ),
    ("scribe", "run_recall"): (
        "start_recall",
        GUILD,
        "--yes is text here",
        ("recall", "--", "--yes is text here"),
        {0},
        False,
        None,
    ),
    ("steward", "run_duty"): (
        "start_duty",
        GUILD,
        "ci-status",
        ("ci", "status", "--json"),
        {0, 1},
        False,
        None,
    ),
    ("warden", "run_audit"): (
        "start_audit",
        WARDEN,
        ".",
        ("scan", "<root>", "--format", "json"),
        {0, 1},
        False,
        None,
    ),
}

#: What the session hook denies an agent at the shell. No row's verb may name one.
DENIED_TOKENS = frozenset(
    {
        "--yes",
        "--open-fix-prs",
        "--fix-prs-dry-run",
        "--bypass",
        "--auto-approve",
        "--transitive",
        "submit",
        "ship",
        "publish",
        "author",
        "close",
        "archive",
        "spin",
        "drain",
        "challenge",
    },
)


def _fake(root: Path, environment: str, body: str) -> Path:
    bin_dir = root / ".pixi" / "envs" / environment / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    executable = bin_dir / "pyforge"
    executable.write_text(
        "#!/bin/sh\n"
        f"printf '%s\\n' \"$@\" > {root}/argv\n"
        f"env > {root}/environment\n"
        f"{body}\n",
        encoding="utf-8",
    )
    executable.chmod(executable.stat().st_mode | stat.S_IXUSR)
    return executable


def _argv(root: Path) -> list[str]:
    return (root / "argv").read_text(encoding="utf-8").splitlines()


def _ran(root: Path) -> bool:
    return (root / "argv").exists()


@pytest.fixture
def root(tmp_path: Path, settings: Any) -> Path:
    """A checkout with all three environments and one tracked recipe."""
    checkout = tmp_path / "checkout"
    (checkout / "recipes" / "demo").mkdir(parents=True)
    (checkout / "recipes" / "demo" / "recipe.yaml").write_text(
        "package: {}\n", encoding="utf-8"
    )
    (checkout / "recipes" / "untracked").mkdir()
    subprocess.run(["git", "init", "-q", str(checkout)], check=True)  # noqa: S603, S607
    subprocess.run(["git", "-C", str(checkout), "add", "recipes/demo"], check=True)  # noqa: S603, S607
    for environment in ENVIRONMENTS:
        _fake(checkout, environment, """echo '{"ok": true}'""")
    _fake(checkout, MASON, _build_report(0))
    settings.STATION_CLI_ROOT = str(checkout)
    return checkout


def _flagd_tree(tmp_path: Path, key: str, variant: str) -> Path:
    """A tree holding one flag in one state."""
    tree = {
        "flags": {
            key: {
                "state": "ENABLED",
                "variants": {"on": True, "off": False},
                "defaultVariant": variant,
            },
        },
    }
    path = tmp_path / f"flags-{variant}.json"
    path.write_text(json.dumps(tree, indent=2) + "\n", encoding="utf-8")
    return path


def _runner(station: str, tool: str) -> Any:
    return getattr(importlib.import_module(MODULES[station]), tool)


def _assertion(station: str, *extra: str) -> str:
    return mint_assertion(
        sub="agent-119",
        roles=[f"pyforge:station:{station}", *extra],
        station=station,
    )


def test_the_flag_keys_here_are_the_module_keys() -> None:
    assert station_cli.START_TOOL_CLI_FLAG_KEY == START_TOOL_CLI_FLAG_KEY
    assert station_cli.START_LOOP_DISPATCH_FLAG_KEY == START_LOOP_DISPATCH_FLAG_KEY


def test_the_table_is_pinned_and_closed() -> None:
    assert set(STATION_VERBS) == set(PINNED)
    for key, verb in STATION_VERBS.items():
        start_tool, environment, _target, _argv_expected, codes, admin, flag = PINNED[
            key
        ]
        assert verb.start_tool == start_tool
        assert verb.environment == environment
        assert verb.result_codes == codes
        assert verb.admin_only is admin
        assert verb.flag == flag


def test_the_table_names_each_face_own_tools() -> None:
    for (station, run_tool), verb in STATION_VERBS.items():
        module = importlib.import_module(MODULES[station])
        assert run_tool in vars(module).values()
        assert verb.start_tool in vars(module).values()


def test_each_row_passes_and_repeats_only_what_is_pinned() -> None:
    assert {
        key: verb.passthrough for key, verb in STATION_VERBS.items() if verb.passthrough
    } == {
        ("scribe", "run_recall"): ("SCRIBE_GRAPH_DSN",),
        ("warden", "run_audit"): (
            "OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY",
            "PYFORGE_WARDEN_FEED_CACHE_DIR",
        ),
    }
    once = {key for key, verb in STATION_VERBS.items() if verb.at_most_once}
    assert once == {("marshal", "run_loop"), ("mason", "run_build")}


def test_the_environment_allowlist_is_pinned() -> None:
    assert set(ENVIRONMENT_ALLOWLIST) == {
        "CURL_CA_BUNDLE",
        "HOME",
        "HTTPS_PROXY",
        "HTTP_PROXY",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "LOGNAME",
        "NODE_EXTRA_CA_CERTS",
        "NO_PROXY",
        "PYFORGE_ENVIRONMENT",
        "PYFORGE_FLAGS_PATH",
        "REQUESTS_CA_BUNDLE",
        "SSL_CERT_DIR",
        "SSL_CERT_FILE",
        "TMPDIR",
        "TZ",
        "USER",
        "XDG_CACHE_HOME",
        "XDG_CONFIG_HOME",
        "XDG_DATA_HOME",
        "http_proxy",
        "https_proxy",
        "no_proxy",
    }
    assert station_cli.SYSTEM_PATH == "/usr/local/bin:/usr/bin:/bin"


def test_steward_duties_are_pinned() -> None:
    assert STEWARD_DUTIES == {
        "ci-status": ("ci", "status", "--json"),
        "estate-plan": ("estate", "plan", "--json"),
        "estate-status": ("estate", "status", "--json"),
    }


def _row_commands(root: Path) -> list[tuple[str, ...]]:
    """Every verb a row can run: one per row, and one per steward duty."""
    commands = [
        (
            station,
            *STATION_VERBS[(station, tool)].args(PINNED[(station, tool)][2], root),
        )
        for station, tool in sorted(PINNED)
        if station != "steward"
    ]
    return [*commands, *(("steward", *argv) for argv in STEWARD_DUTIES.values())]


def test_no_row_names_a_denied_token(root: Path) -> None:
    for command in _row_commands(root):
        fixed = [arg for arg in command if arg != "--yes is text here"]
        assert not DENIED_TOKENS.intersection(fixed), command


def _hook_denies(command: str) -> bool:
    """Ask the real session hook, the one a worker never passes through."""
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "cwd": str(HOOK.parents[2]),
    }
    done = subprocess.run(  # noqa: S603
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
    )
    return '"deny"' in done.stdout


@pytest.mark.parametrize(
    "command",
    [
        "pyforge steward estate refresh --transitive",
        "pyforge steward estate realize --yes",
        "pyforge mason recipe submit x --yes",
    ],
)
def test_the_hook_check_can_see_a_denied_verb(command: str) -> None:
    assert _hook_denies(command)


def test_the_session_hook_would_allow_every_row(root: Path) -> None:
    for command in _row_commands(root):
        assert not _hook_denies(" ".join(("pyforge", *command))), command


@pytest.mark.parametrize("key", sorted(PINNED), ids="/".join)
def test_a_row_runs_its_exact_argv_with_no_shell(
    root: Path,
    key: tuple[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "PYFORGE_FLAGS_PATH",
        str(_flagd_tree(tmp_path, START_LOOP_DISPATCH_FLAG_KEY, "on")),
    )
    station, run_tool = key
    target = PINNED[key][2]

    result = _runner(station, run_tool)({"target": target})

    expected = [
        station,
        *(str(root) if arg == "<root>" else arg for arg in PINNED[key][3]),
    ]
    assert _argv(root) == expected
    assert result["exit_code"] == 0
    assert result["argv"] == expected
    assert result["report"]["data" if station == "mason" else "ok"]


@pytest.mark.parametrize(
    ("station", "run_tool", "target"),
    [
        ("doctor", "run_scan", "--prescribe"),
        ("doctor", "run_scan", "a/b"),
        ("doctor", "run_scan", ""),
        ("doctor", "run_scan", "a b"),
        ("herald", "run_notice", "--json"),
        ("herald", "run_notice", "a;id"),
        ("scribe", "run_recall", ""),
        ("scribe", "run_recall", "two\nlines"),
        ("scribe", "run_recall", "lone \ud800 surrogate"),
        ("scribe", "run_recall", "x" * 2001),
        ("steward", "run_duty", "keys"),
        ("steward", "run_duty", "ci status"),
        ("steward", "run_duty", "--version"),
        ("warden", "run_audit", ".."),
        ("warden", "run_audit", "/etc"),
        ("warden", "run_audit", "no-such-dir"),
        ("warden", "run_audit", "a\x00b"),
        ("warden", "run_audit", ""),
        ("mason", "run_build", "../secret"),
        ("mason", "run_build", "recipes/demo"),
        ("mason", "run_build", "untracked"),
        ("mason", "run_build", "--docker"),
    ],
)
def test_a_refused_target_starts_nothing(
    root: Path, station: str, run_tool: str, target: str
) -> None:
    with pytest.raises(RunnerNotWiredError, match="target refused"):
        _runner(station, run_tool)({"target": target})
    assert not _ran(root)


@pytest.mark.parametrize(
    "target", ["", "steward", "/story", "steward/", "a/b/c", "--yes/x"]
)
def test_a_refused_loop_target_starts_nothing(
    root: Path,
    target: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "PYFORGE_FLAGS_PATH",
        str(_flagd_tree(tmp_path, START_LOOP_DISPATCH_FLAG_KEY, "on")),
    )
    with pytest.raises(RunnerNotWiredError, match="target refused"):
        _runner("marshal", "run_loop")({"target": target})
    assert not _ran(root)


def test_a_symlink_out_of_the_checkout_is_refused(root: Path, tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "link").symlink_to(outside)
    with pytest.raises(RunnerNotWiredError, match="target refused"):
        _runner("warden", "run_audit")({"target": "link"})
    assert not _ran(root)


def test_a_cli_never_sees_the_worker_secrets(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DJANGO_SECRET_KEY", "worker-secret")
    monkeypatch.setenv("DATABASE_URL", "postgres://worker-secret")
    monkeypatch.setenv("LANG", "C.UTF-8")

    _runner("doctor", "run_scan")({"target": "numpy"})

    seen = (root / "environment").read_text(encoding="utf-8")
    assert "worker-secret" not in seen
    assert "LANG=C.UTF-8" in seen
    assert f"PATH={root}/.pixi/envs/{GUILD}/bin:{Path.home()}/.local/bin:" in seen


def test_a_row_passes_only_its_own_variables(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SCRIBE_GRAPH_DSN", "postgres://scribe")
    monkeypatch.setenv("PYFORGE_ENVIRONMENT", "dev")

    _runner("doctor", "run_scan")({"target": "numpy"})
    assert "SCRIBE_GRAPH_DSN" not in (root / "environment").read_text(encoding="utf-8")

    _runner("scribe", "run_recall")({"target": "why"})
    seen = (root / "environment").read_text(encoding="utf-8")
    assert "SCRIBE_GRAPH_DSN=postgres://scribe" in seen
    assert "PYFORGE_ENVIRONMENT=dev" in seen


def test_an_unset_root_says_so(settings: Any) -> None:
    settings.STATION_CLI_ROOT = ""
    with pytest.raises(RunnerNotWiredError, match="no station CLI"):
        _runner("doctor", "run_scan")({"target": "numpy"})


def test_a_missing_environment_says_so(root: Path) -> None:
    (root / ".pixi" / "envs" / WARDEN / "bin" / "pyforge").unlink()
    with pytest.raises(RunnerNotWiredError, match=f"no {WARDEN} environment"):
        _runner("warden", "run_audit")({"target": "."})


def _build_report(returncode: int) -> str:
    report = {"status": "ok", "data": {"returncode": returncode, "stdout": "log"}}
    return f"echo '{json.dumps(report)}'"


def test_a_failed_build_fails_the_run_though_mason_exits_0(root: Path) -> None:
    _fake(root, MASON, f"{_build_report(1)}\necho 'Script failed' >&2")
    with pytest.raises(
        StationVerbFailedError, match="the build exited 1: Script failed"
    ):
        _runner("mason", "run_build")({"target": "demo"})


def test_a_build_with_no_result_fails_the_run(root: Path) -> None:
    _fake(root, MASON, """echo '{"status": "ok"}'""")
    with pytest.raises(StationVerbFailedError, match="no build result"):
        _runner("mason", "run_build")({"target": "demo"})


def test_a_build_keeps_its_verdict_when_the_log_is_large(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(station_cli, "STDERR_TAIL_BYTES", 2)
    _fake(root, MASON, _build_report(0))
    result = _runner("mason", "run_build")({"target": "demo"})
    assert result["report"]["data"] == {"returncode": 0, "stdout": "og"}


def test_a_report_quoting_the_text_of_a_nul_stays_a_report(root: Path) -> None:
    _fake(root, GUILD, """cat <<'EOF'\n{"a": "x\\\\u0000y"}\nEOF""")
    result = _runner("doctor", "run_scan")({"target": "numpy"})
    assert result["report"] == {"a": "x\\u0000y"}


def test_a_report_cap_counts_its_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(station_cli, "OUTPUT_CAP_BYTES", 100)
    report = {f"{'k' * 40}{index}": 1 for index in range(10)}
    kept, omitted = station_cli._fit_report(report)  # noqa: SLF001
    assert len(json.dumps(kept)) <= 100 + len(kept) * 2
    assert len(kept) + len(omitted) == len(report)


def test_a_gated_flag_reads_off_with_no_pyforge_core(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "pyforge.core.flags", None)
    assert station_cli._flag_on(START_LOOP_DISPATCH_FLAG_KEY) is False  # noqa: SLF001


def test_a_nul_in_a_failed_verb_stderr_never_reaches_the_store(root: Path) -> None:
    _fake(root, GUILD, "printf 'bad\\000news' >&2\nexit 3")
    with pytest.raises(StationVerbFailedError) as caught:
        _runner("doctor", "run_scan")({"target": "numpy"})
    assert "\x00" not in str(caught.value)
    assert "badnews" in str(caught.value)


def test_an_exit_code_outside_the_row_fails_the_run(root: Path) -> None:
    _fake(root, GUILD, "echo 'it broke' >&2\nexit 3")
    with pytest.raises(StationVerbFailedError, match="exited 3: it broke"):
        _runner("doctor", "run_scan")({"target": "numpy"})


def test_a_doctor_fail_finding_is_a_result(root: Path) -> None:
    _fake(root, GUILD, """echo '{"findings": ["fail"]}'\nexit 2""")
    result = _runner("doctor", "run_scan")({"target": "numpy"})
    assert result["exit_code"] == 2  # noqa: PLR2004
    assert result["report"] == {"findings": ["fail"]}


def test_a_result_code_with_no_report_fails_the_run(root: Path) -> None:
    _fake(root, GUILD, "echo 'traceback' >&2\nexit 2")
    with pytest.raises(
        StationVerbFailedError, match="exited 2 with no report: traceback"
    ):
        _runner("doctor", "run_scan")({"target": "numpy"})


@pytest.mark.parametrize("code", [0, 1])
def test_a_warden_finding_is_a_result(root: Path, code: int) -> None:
    _fake(root, WARDEN, f"""echo '{{"status": "red"}}'\nexit {code}""")
    result = _runner("warden", "run_audit")({"target": "."})
    assert result["exit_code"] == code
    assert result["report"] == {"status": "red"}


def test_a_warden_error_is_an_audit_that_did_not_finish(root: Path) -> None:
    _fake(root, WARDEN, """echo '{"status": "error"}'\necho 'symlinked' >&2\nexit 2""")
    with pytest.raises(StationVerbFailedError, match="exited 2: symlinked"):
        _runner("warden", "run_audit")({"target": "."})


def _slow_child(root: Path) -> str:
    """A wrapper waiting on a child, the shape of ``pyforge`` over a station CLI."""
    return f"(sleep 2; touch {root}/survived) &\nwait"


def test_a_timeout_stops_the_whole_verb(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake(root, GUILD, _slow_child(root))
    monkeypatch.setattr(
        station_cli,
        "time_limit_for_queue",
        lambda _queue: station_cli.VERB_MARGIN_SECONDS + 1,
    )
    with pytest.raises(StationVerbFailedError, match="timed out after 1 s"):
        _runner("doctor", "run_scan")({"target": "numpy"})
    time.sleep(1.5)
    assert not (root / "survived").exists()


def test_a_soft_limit_stops_the_whole_verb(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _fake(root, GUILD, _slow_child(root))
    real = subprocess.Popen.communicate
    calls: list[int] = []

    def soft_limit_on_first_call(self: Any, *args: Any, **kwargs: Any) -> Any:
        calls.append(1)
        if len(calls) == 1:
            time.sleep(0.5)  # let the wrapper start its child
            raise SoftTimeLimitExceeded
        return real(self, *args, **kwargs)

    monkeypatch.setattr(subprocess.Popen, "communicate", soft_limit_on_first_call)
    with pytest.raises(SoftTimeLimitExceeded):
        _runner("doctor", "run_scan")({"target": "numpy"})
    time.sleep(2.5)
    assert not (root / "survived").exists()


def test_a_report_keeps_what_fits_and_names_the_rest(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(station_cli, "OUTPUT_CAP_BYTES", 40)
    big = ", ".join(['"x"'] * 30)
    _fake(root, WARDEN, f"""echo '{{"status": "green", "findings": [{big}]}}'""")

    result = _runner("warden", "run_audit")({"target": "."})

    assert result["report"] == {"status": "green"}
    assert result["omitted"]["findings"]["items"] == 30  # noqa: PLR2004


@pytest.mark.parametrize(
    "body",
    [
        pytest.param('{"a": NaN}', id="nan"),
        pytest.param('{"a": 1e999}', id="overflow"),
        pytest.param('{"a": "x\\u0000y"}', id="nul"),
        pytest.param('{"a": "\\ud800"}', id="surrogate"),
        pytest.param("[" * 200000, id="deep"),
    ],
)
def test_output_the_run_store_refuses_stays_text(root: Path, body: str) -> None:
    _fake(root, GUILD, f"cat <<'EOF'\n{body}\nEOF")
    result = _runner("herald", "run_notice")({"target": "api"})
    assert "report" not in result
    assert "\x00" not in result["stdout"]


def test_plain_output_is_capped(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _fake(root, GUILD, "echo 0123456789")
    monkeypatch.setattr(station_cli, "OUTPUT_CAP_BYTES", 4)

    result = _runner("herald", "run_notice")({"target": "api"})

    assert result["stdout"] == "0123"
    assert result["truncated"] is True


def test_start_tool_cli_kill_switch_on_runs_the_verb(
    root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tree = _flagd_tree(tmp_path, START_TOOL_CLI_FLAG_KEY, "on")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    assert evaluate_from_source(key=START_TOOL_CLI_FLAG_KEY, source=tree) is True

    _runner("doctor", "run_scan")({"target": "numpy"})

    assert _ran(root)


def test_start_tool_cli_kill_switch_off_starts_nothing(
    root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tree = _flagd_tree(tmp_path, START_TOOL_CLI_FLAG_KEY, "off")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    assert evaluate_from_source(key=START_TOOL_CLI_FLAG_KEY, source=tree) is False

    with pytest.raises(RunnerNotWiredError, match=START_TOOL_CLI_FLAG_KEY):
        _runner("doctor", "run_scan")({"target": "numpy"})

    assert not _ran(root)


@pytest.mark.django_db
def test_eager_start_ends_with_the_report_in_get(root: Path) -> None:
    register_runner("doctor", "run_scan", _runner("doctor", "run_scan"))
    assertion = _assertion("doctor")

    handle = start_bounded(
        station="doctor",
        assertion=assertion,
        tool="run_scan",
        payload={"target": "numpy"},
    )

    run = get_run(station="doctor", handle=handle, assertion=assertion)
    assert run["status"] == RunState.Status.SUCCEEDED
    assert run["result"]["report"] == {"ok": True}
    assert _argv(root)[:3] == ["doctor", "diagnose", "--target"]


@pytest.mark.django_db
def test_eager_failed_verb_keeps_the_handle(root: Path) -> None:
    _fake(root, GUILD, "exit 3")
    register_runner("doctor", "run_scan", _runner("doctor", "run_scan"))
    assertion = _assertion("doctor")

    handle = start_bounded(
        station="doctor",
        assertion=assertion,
        tool="run_scan",
        payload={"target": "numpy"},
    )

    run = get_run(station="doctor", handle=handle, assertion=assertion)
    assert run["status"] == RunState.Status.FAILED
    assert "exited 3" in run["result"]["error"]


@pytest.mark.django_db
def test_loop_without_the_admin_role_is_refused_before_a_run_row(
    root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "PYFORGE_FLAGS_PATH",
        str(_flagd_tree(tmp_path, START_LOOP_DISPATCH_FLAG_KEY, "on")),
    )
    before = RunState.objects.count()

    with pytest.raises(ToolError, match=ROLE_ADMIN):
        start_bounded(
            station="marshal",
            assertion=_assertion("marshal"),
            tool="run_loop",
            payload={"target": "pyforge-steward/119-1-a"},
        )

    assert RunState.objects.count() == before
    assert not _ran(root)


@pytest.mark.django_db
def test_start_loop_dispatch_off_refuses_an_admin_before_a_run_row(
    root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tree = _flagd_tree(tmp_path, START_LOOP_DISPATCH_FLAG_KEY, "off")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    assert evaluate_from_source(key=START_LOOP_DISPATCH_FLAG_KEY, source=tree) is False
    before = RunState.objects.count()

    with pytest.raises(ToolError, match=START_LOOP_DISPATCH_FLAG_KEY):
        start_bounded(
            station="marshal",
            assertion=_assertion("marshal", ROLE_ADMIN),
            tool="run_loop",
            payload={"target": "pyforge-steward/119-1-a"},
        )

    assert RunState.objects.count() == before
    assert not _ran(root)


@pytest.mark.django_db
def test_start_loop_dispatch_on_dispatches_for_an_admin(
    root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tree = _flagd_tree(tmp_path, START_LOOP_DISPATCH_FLAG_KEY, "on")
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", str(tree))
    assert evaluate_from_source(key=START_LOOP_DISPATCH_FLAG_KEY, source=tree) is True
    register_runner("marshal", "run_loop", _runner("marshal", "run_loop"))
    assertion = _assertion("marshal", ROLE_ADMIN)

    handle = start_bounded(
        station="marshal",
        assertion=assertion,
        tool="run_loop",
        payload={"target": "pyforge-steward/119-1-a"},
    )

    run = get_run(station="marshal", handle=handle, assertion=assertion)
    assert run["status"] == RunState.Status.SUCCEEDED
    assert _argv(root) == [
        "marshal",
        "factory",
        "dispatch",
        "pyforge-steward",
        "119-1-a",
        "--format",
        "json",
    ]


def test_start_loop_dispatch_flipped_off_after_the_start_dispatches_nothing(
    root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "PYFORGE_FLAGS_PATH",
        str(_flagd_tree(tmp_path, START_LOOP_DISPATCH_FLAG_KEY, "off")),
    )
    with pytest.raises(RunnerNotWiredError, match=START_LOOP_DISPATCH_FLAG_KEY):
        _runner("marshal", "run_loop")({"target": "pyforge-steward/119-1-a"})
    assert not _ran(root)


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("station", "tool", "target"),
    [("mason", "run_build", "demo"), ("marshal", "run_loop", "pyforge-steward/x")],
)
def test_a_lost_worker_never_starts_a_spending_verb_twice(  # noqa: PLR0913, PLR0917
    root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    station: str,
    tool: str,
    target: str,
) -> None:
    monkeypatch.setenv(
        "PYFORGE_FLAGS_PATH",
        str(_flagd_tree(tmp_path, START_LOOP_DISPATCH_FLAG_KEY, "on")),
    )
    delayed: list[dict[str, Any]] = []
    monkeypatch.setattr(
        execute_supervised_run,
        "apply_async",
        lambda *_a, **kwargs: delayed.append(kwargs),
    )
    register_runner(station, tool, _runner(station, tool))
    assertion = _assertion(station, ROLE_ADMIN)
    handle = start_bounded(
        station=station, assertion=assertion, tool=tool, payload={"target": target}
    )
    run_id = delayed[0]["args"][0]
    assert claim_only_attempt(run_id)  # the first attempt got this far; its worker died

    execute_supervised_run.push_request(delivery_info={"redelivered": True})
    try:
        execute_supervised_run.run(*delayed[0]["args"])
    finally:
        execute_supervised_run.pop_request()

    run = get_run(station=station, handle=handle, assertion=assertion)
    assert run["status"] == RunState.Status.FAILED
    assert "was not run again" in run["result"]["error"]
    assert not _ran(root)


@pytest.mark.django_db
def test_a_row_run_is_published_with_its_own_limits(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    delayed: list[dict[str, Any]] = []
    monkeypatch.setattr(
        execute_supervised_run,
        "apply_async",
        lambda *_a, **kwargs: delayed.append(kwargs),
    )
    start_bounded(
        station="steward",
        assertion=_assertion("steward"),
        tool="run_duty",
        payload={"target": "estate-plan"},
    )
    limits = task_limits("steward", "run_duty")
    assert delayed[0]["soft_time_limit"] == limits["soft_time_limit"]
    assert delayed[0]["time_limit"] == limits["time_limit"]
    assert not _ran(root)


def test_a_build_lands_on_the_builds_queue() -> None:
    assert queue_for("mason", "run_build") == BUILDS_QUEUE


def test_a_row_names_limits_above_its_verb_and_a_plain_run_names_none(
    settings: Any,
) -> None:
    limits = task_limits("steward", "run_duty")
    assert limits == {
        "soft_time_limit": settings.CELERY_TASK_TIME_LIMIT
        - station_cli.SOFT_LIMIT_MARGIN_SECONDS,
        "time_limit": settings.CELERY_TASK_TIME_LIMIT
        - station_cli.HARD_LIMIT_MARGIN_SECONDS,
    }
    assert (
        limits["soft_time_limit"]
        > settings.CELERY_TASK_TIME_LIMIT - station_cli.VERB_MARGIN_SECONDS
    )
    build = task_limits("mason", "run_build")
    assert (
        build["time_limit"]
        == settings.CELERY_BUILDS_TASK_TIME_LIMIT
        - station_cli.HARD_LIMIT_MARGIN_SECONDS
    )
    assert task_limits("atlas", "run_pipeline") == {}


def test_a_failed_recall_reads_as_a_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    failed = subprocess.CompletedProcess(
        args=[], returncode=2, stdout="", stderr="no graph"
    )
    monkeypatch.setattr(
        "django_pyforge.assertion.client.subprocess.run", lambda *_a, **_k: failed
    )

    answer = lookup_portal_job("scribe", "recall")(assertion="", payload={"query": "q"})

    assert answer["grounded"] is False
    assert "exit 2" in answer["text"]
    assert "no graph" in answer["text"]
