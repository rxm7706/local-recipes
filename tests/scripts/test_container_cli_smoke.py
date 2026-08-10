"""Tests for `scripts/container-gates`'s `cli-smoke` subcommand (Story 7.5,
"The image proves itself at build time").

Real, non-mocked: every test but the timeout-budget one subprocess-invokes
the real `container-gates` script against small synthetic fixture scripts
written under `tmp_path` and `chmod +x`'d -- no real station binary and no
Docker needed. `cli-smoke` is duty-agnostic (it only knows how to run
whatever `--cli` value it is given); the eight real station names live in
the Containerfile's own `RUN` line, not here, so this suite never needs
them. That is also why this file lives under `tests/scripts/` with no
special fixture: it is picked up by the existing `pyforge-doctor-scripts-test`
sweep (pure stdlib, no runtime deps required).

The timeout-budget test imports the module directly (see
`_load_container_gates` below) so it can pass a tiny timeout straight to
`_check_cli` without waiting out the full `_CLI_SMOKE_TIMEOUT_SECONDS`
production budget -- `cli-smoke` deliberately exposes no `--timeout` flag
(one documented constant applies to all eight stations; see the story
spec's Boundaries & Constraints), so a fast test of that one path has no
CLI surface to go through.

Mirrors the story spec's I/O & Edge-Case Matrix, one test per row.

    pixi run -e pyforge-ci pyforge-doctor-scripts-test
"""

from __future__ import annotations

import importlib.util
from importlib.machinery import SourceFileLoader
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTAINER_GATES = REPO_ROOT / "scripts" / "container-gates"


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CONTAINER_GATES), *args],
        capture_output=True,
        text=True,
        timeout=60,
    )


def _load_container_gates():
    """Import `scripts/container-gates` (a hyphenated filename, so it can't
    be `import`ed normally) to reach `_check_cli` directly -- only the
    timeout-budget test needs this; every other test below goes through the
    real CLI via `_run`."""
    loader = SourceFileLoader("container_gates", str(CONTAINER_GATES))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def _write_script(tmp_path: Path, name: str, body: str) -> Path:
    script = tmp_path / name
    script.write_text(body)
    script.chmod(0o755)
    return script


def test_happy_path_one_cli_exits_zero():
    """Matrix row 1: `--cli "true"` (or any exit-0 command) reports OK,
    exit 0."""
    proc = _run("cli-smoke", "--cli", "true")

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "true: OK" in proc.stdout


def test_happy_path_multiple_clis_all_pass_exits_zero(tmp_path):
    """Matrix row 2 (shaped like the real all-eight-real-stations case,
    with synthetic fixture scripts standing in for them): every `--cli`
    value passes, so the aggregate exits 0 only because ALL of them
    passed."""
    ok_scripts = [
        _write_script(tmp_path, f"ok{i}.py", "#!/usr/bin/env python3\nimport sys\nsys.exit(0)\n")
        for i in range(3)
    ]

    args = ["cli-smoke"]
    for script in ok_scripts:
        args += ["--cli", str(script)]
    proc = _run(*args)

    assert proc.returncode == 0, proc.stdout + proc.stderr
    for script in ok_scripts:
        assert f"{script}: OK" in proc.stdout


def test_missing_binary_fails_cleanly_not_with_a_traceback():
    """Matrix row 3: a nonexistent binary raises `FileNotFoundError`
    internally -- caught, reported as clean stderr naming the binary,
    exit 1, never a raw traceback."""
    proc = _run("cli-smoke", "--cli", "does-not-exist-binary --help")

    assert proc.returncode != 0
    assert "does-not-exist-binary" in proc.stderr
    assert "not found on PATH" in proc.stderr
    assert "Traceback" not in proc.stderr


def test_broken_cli_nonzero_exit_reports_exit_code_and_stderr_tail(tmp_path):
    """Matrix row 4: a CLI that runs but exits non-zero (unimportable/
    broken) is reported as a failure naming the exit code and a tail of
    its stderr."""
    broken = _write_script(
        tmp_path,
        "broken.py",
        "#!/usr/bin/env python3\nimport sys\nprint('boom', file=sys.stderr)\nsys.exit(3)\n",
    )

    proc = _run("cli-smoke", "--cli", str(broken))

    assert proc.returncode != 0
    assert "exited 3" in proc.stderr
    assert "boom" in proc.stderr


def test_broken_cli_with_long_stderr_reports_only_the_last_five_lines(tmp_path):
    """Review-pass patch (Blind Hunter): the `[-5:]` stderr-tail slice had no
    test emitting more than one line. A 7-line stderr proves only the last
    5 survive and the first 2 are dropped."""
    broken = _write_script(
        tmp_path,
        "broken_long.py",
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "for i in range(1, 8):\n"
        "    print(f'line{i}', file=sys.stderr)\n"
        "sys.exit(1)\n",
    )

    proc = _run("cli-smoke", "--cli", str(broken))

    assert proc.returncode != 0
    for i in range(3, 8):
        assert f"line{i}" in proc.stderr
    assert "line1" not in proc.stderr
    assert "line2" not in proc.stderr


def test_broken_cli_with_no_output_reports_a_placeholder_not_a_bare_colon(tmp_path):
    """Review-pass patch (both reviewers, independently): a non-zero exit
    with empty stderr AND empty stdout used to print a bare trailing
    "exited N: " with no diagnostic content. Now falls back to a clear
    placeholder."""
    silent = _write_script(
        tmp_path, "silent.py", "#!/usr/bin/env python3\nimport sys\nsys.exit(7)\n"
    )

    proc = _run("cli-smoke", "--cli", str(silent))

    assert proc.returncode != 0
    assert "exited 7: (no output captured)" in proc.stderr


def test_broken_cli_reporting_only_to_stdout_still_surfaces_a_diagnostic(tmp_path):
    """Review-pass patch: a CLI that reports its failure reason on stdout
    (not stderr) used to produce the same empty tail as true silence. Now
    falls back to the stdout tail when stderr is empty."""
    stdout_only = _write_script(
        tmp_path,
        "stdout_only.py",
        "#!/usr/bin/env python3\nimport sys\nprint('explained on stdout')\nsys.exit(2)\n",
    )

    proc = _run("cli-smoke", "--cli", str(stdout_only))

    assert proc.returncode != 0
    assert "explained on stdout" in proc.stderr


def test_non_executable_target_fails_cleanly_not_with_a_raw_traceback(tmp_path):
    """Review-pass patch (Edge Case Hunter): `argv[0]` resolving to a
    non-executable file raises `PermissionError` (a plain `OSError`
    subclass, not `FileNotFoundError`) -- must reach the general `except
    (OSError, ValueError)` fallback, never an unhandled traceback."""
    not_executable = tmp_path / "not_executable.sh"
    not_executable.write_text("#!/bin/bash\necho hi\n")
    not_executable.chmod(0o644)  # no execute bit

    proc = _run("cli-smoke", "--cli", str(not_executable))

    assert proc.returncode != 0
    assert "Traceback" not in proc.stderr
    assert str(not_executable) in proc.stderr


def test_over_budget_cli_times_out_cleanly(tmp_path):
    """Matrix row 5: a CLI that sleeps past the timeout budget is caught as
    `TimeoutExpired` (which already kills the child process), reported
    cleanly naming the budget, never a raw traceback. Calls `_check_cli`
    directly with a tiny timeout (see `_load_container_gates`'s docstring)
    so this test stays fast rather than waiting out the full production
    `_CLI_SMOKE_TIMEOUT_SECONDS` budget."""
    sleepy = _write_script(tmp_path, "sleepy.sh", "#!/bin/bash\nsleep 5\n")
    module = _load_container_gates()

    ok = module._check_cli(str(sleepy), timeout=0.2)

    assert ok is False


def test_cmd_cli_smoke_threads_its_timeout_override_to_every_check(tmp_path):
    """Review-pass patch (Blind Hunter): the timeout row above calls
    `_check_cli` directly, so `cmd_cli_smoke`'s own parameter-threading
    (`cmd_cli_smoke(clis, timeout=...)` -> each `_check_cli(cli, timeout)`
    call) had no coverage of its own. Calls `cmd_cli_smoke` itself with a
    tiny override -- the actual path `main()` exercises with the module
    default -- and asserts the aggregate verdict reflects the timeout."""
    sleepy = _write_script(tmp_path, "sleepy2.sh", "#!/bin/bash\nsleep 5\n")
    module = _load_container_gates()

    rc = module.cmd_cli_smoke([str(sleepy)], timeout=0.2)

    assert rc == 1


def test_one_of_several_fails_others_still_attempted(tmp_path):
    """Matrix row 6: three `--cli` values, one broken -- all three are
    still attempted (no short-circuit), aggregate exit 1, and each CLI's
    own pass/fail line is printed."""
    good_a = _write_script(tmp_path, "good_a.py", "#!/usr/bin/env python3\nimport sys\nsys.exit(0)\n")
    broken = _write_script(tmp_path, "broken.py", "#!/usr/bin/env python3\nimport sys\nsys.exit(1)\n")
    good_b = _write_script(tmp_path, "good_b.py", "#!/usr/bin/env python3\nimport sys\nsys.exit(0)\n")

    proc = _run(
        "cli-smoke",
        "--cli", str(good_a),
        "--cli", str(broken),
        "--cli", str(good_b),
    )

    assert proc.returncode != 0
    combined = proc.stdout + proc.stderr
    assert f"{good_a}: OK" in combined
    assert f"{broken}: exited 1" in combined
    assert f"{good_b}: OK" in combined


def test_malformed_cli_value_unbalanced_quoting_fails_cleanly():
    """Matrix row 7 (unbalanced quoting): `shlex.split` raises
    `ValueError`, caught upfront and reported cleanly naming the bad value
    -- never reaches `subprocess.run`."""
    proc = _run("cli-smoke", "--cli", "unterminated 'quote")

    assert proc.returncode != 0
    assert "invalid --cli value" in proc.stderr
    assert "Traceback" not in proc.stderr


def test_malformed_cli_value_empty_string_fails_cleanly():
    """Matrix row 7 (empty string): `shlex.split` returns `[]`, caught
    upfront and reported cleanly rather than reaching `subprocess.run`
    with an empty argv."""
    proc = _run("cli-smoke", "--cli", "   ")

    assert proc.returncode != 0
    assert "invalid --cli value" in proc.stderr
    assert "empty command" in proc.stderr
