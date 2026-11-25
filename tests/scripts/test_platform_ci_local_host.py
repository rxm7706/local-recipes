"""Steward Story 133.3: ``platform-ci-local``'s test stage runs on a host with no container engine, on UTF-8.

``DW-steward-review-2026-11-24-3``: the script refused, exit 2, when its container engine was not on
``PATH`` even for ``--test``, a stage that builds and runs no image; and it ran ``initdb`` with no
encoding, so under a ``C`` locale the throwaway cluster was ``SQL_ASCII``.

The script runs here against stand-ins for every tool it starts, with an engine name no host has.
"""

from __future__ import annotations

import os
import re
import socket
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "platform-ci-local.sh"

# An engine no host has on PATH, so the run reads the same on a laptop and on a CI runner that ships docker.
ABSENT_ENGINE = "no-such-engine-story-133-3"

_OK = "#!/usr/bin/env bash\nexit 0\n"
_LOGS_ITS_CALL = '#!/usr/bin/env bash\necho "$(basename "$0") $*" >> "$PLATFORM_CI_STUB_LOG"\nexit 0\n'


def _write_executable(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _stub_root(root: Path) -> Path:
    """A checkout stand-in: ``bin/`` first on PATH, the three pixi envs' tools, a minimal ``src/platform``."""
    bin_dir = root / "bin"
    _write_executable(bin_dir / "python", _OK)
    _write_executable(bin_dir / "pixi", _OK)
    (bin_dir / "python3").symlink_to(sys.executable)
    for name in ("initdb", "pg_ctl", "pg_isready", "psql", "redis-server"):
        _write_executable(
            root / ".pixi" / "envs" / "platform-dev" / "bin" / name, _LOGS_ITS_CALL
        )
    for name in ("python", "ruff", "mypy"):
        _write_executable(
            root / ".pixi" / "envs" / "platform-ci-test" / "bin" / name, _OK
        )
    _write_executable(
        root / ".pixi" / "envs" / "pyforge-warden" / "bin" / "python", _OK
    )
    (root / "src" / "platform").mkdir(parents=True)
    return bin_dir


def _run(root: Path, *args: str) -> tuple[subprocess.CompletedProcess[str], str]:
    """Run the script in ``root`` under ``LC_ALL=C`` with no engine; return the process and the stand-ins' log."""
    bin_dir = _stub_root(root)
    stub_log = root / "stub.log"
    stub_log.write_text("", encoding="utf-8")
    env = {
        "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        "HOME": os.environ.get("HOME", str(root)),
        "TMPDIR": str(root),
        "LC_ALL": "C",
        "PIXI_PROJECT_ROOT": str(root),
        "PLATFORM_CI_LOCAL_ENGINE": ABSENT_ENGINE,
        "PLATFORM_CI_LOCAL_NO_LOCK": "1",
        "PLATFORM_CI_LOCAL_WORK": str(root / "work"),
        "PLATFORM_CI_LOCAL_PG_PORT": str(_free_port()),
        "PLATFORM_CI_LOCAL_REDIS_PORT": str(_free_port()),
        "PLATFORM_CI_STUB_LOG": str(stub_log),
    }
    proc = subprocess.run(
        ["bash", str(SCRIPT), *args],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    return proc, stub_log.read_text(encoding="utf-8")


def test_the_test_stage_does_not_ask_for_the_container_engine(tmp_path: Path) -> None:
    proc, log = _run(tmp_path, "--test")
    assert f"{ABSENT_ENGINE} is not on PATH" not in proc.stderr
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "initdb " in log, "the test stage never reached its services"
    assert "RESULT: PASS" in proc.stdout


@pytest.mark.parametrize(
    "args",
    [
        ("--images",),
        ("--container",),
        ("--promotion",),
        ("--test", "--images"),
        (),
    ],
    ids=["images", "container", "promotion", "test+images", "all-four"],
)
def test_a_stage_that_uses_the_engine_still_refuses_without_it(
    tmp_path: Path, args: tuple[str, ...]
) -> None:
    proc, log = _run(tmp_path, *args)
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert f"{ABSENT_ENGINE} is not on PATH" in proc.stderr
    assert "initdb " not in log, "the script started services before it refused"


def test_initdb_builds_a_utf8_cluster_under_a_c_locale(tmp_path: Path) -> None:
    _proc, log = _run(tmp_path, "--test")
    calls = [line for line in log.splitlines() if line.startswith("initdb ")]
    assert len(calls) == 1, log
    assert re.search(r" -E UTF8( |$)", calls[0]), calls[0]
    assert re.search(r" --locale=C(\.UTF-8)?( |$)", calls[0]), calls[0]


def test_the_initdb_line_names_its_encoding() -> None:
    """The story's AC2, as a test: no ``initdb`` call in the script leaves the encoding to the host's locale."""
    code = [
        line
        for line in SCRIPT.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("#")
    ]
    calls = [line for line in code if "/initdb" in line]
    assert calls, "expected an initdb call"
    for line in calls:
        assert re.search(r" -E UTF8 ", line), line
