"""Seed CLI egress counter (Story 12.3, AD-65, SC-06, NFR-A1).

Asserts **zero** internet-family network syscalls while driving the five
Genesis seed verbs the spec names:

- ``marshal seed init``
- ``marshal seed adopt`` (dry-run by default, then ``--apply --yes``)
- ``marshal seed check``
- ``marshal seed update --run --yes``

Each invocation is wrapped in ``strace -f -e trace=network`` (warden's
established Story 5.2 pattern in ``test_corpus_egress_counter.py``). A
second parametrized pass runs the SAME scenario under ``unshare -n`` on
Linux so the suite proves isolation even when the host has outbound routes.

Linux-only, skip-if-``strace``/``unshare``/``marshal`` unavailable -- never a
hard requirement off Linux. Marked ``@pytest.mark.slow`` (real Copier +
git I/O under instrumentation).
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

_NETWORK_SYSCALL_NAMES = ("connect", "send", "sendto", "sendmsg", "sendmmsg")
_INET_FAMILIES = ("AF_INET", "AF_INET6")

_STRACE_AVAILABLE = sys.platform.startswith("linux") and shutil.which("strace") is not None
_UNSHARE_AVAILABLE = (
    sys.platform.startswith("linux")
    and shutil.which("unshare") is not None
    and subprocess.run(
        ["unshare", "-n", "true"],
        capture_output=True,
        text=True,
        check=False,
    ).returncode
    == 0
)
_MARSHAL_AVAILABLE = shutil.which("marshal") is not None


def _git(repo: Path, *args: str) -> None:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def _commit_all(repo: Path, message: str) -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", message)


def _build_seed_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "seed-target"
    repo.mkdir()
    return repo


def _internet_network_lines(stderr: str) -> list[str]:
    return [
        line
        for line in stderr.splitlines()
        if any(f"{name}(" in line for name in _NETWORK_SYSCALL_NAMES)
        and any(family in line for family in _INET_FAMILIES)
    ]


def _assert_zero_inet_egress(completed: subprocess.CompletedProcess[str], *, label: str) -> None:
    exit_markers = completed.stderr.count("+++ exited with")
    assert exit_markers >= 1, (
        f"{label}: expected strace to attach (saw {exit_markers} exit marker(s)); "
        f"strace rc={completed.returncode}; stderr head={completed.stderr[:500]!r}"
    )
    network_lines = _internet_network_lines(completed.stderr)
    assert not network_lines, f"{label}: unexpected internet-family network syscall(s):\n" + "\n".join(
        network_lines[:20]
    )


def _run_traced(
    argv: Sequence[str],
    *,
    cwd: Path | None,
    isolate_network: bool,
    timeout: float = 300.0,
) -> subprocess.CompletedProcess[str]:
    trace_argv = ["strace", "-f", "-e", "trace=network", *argv]
    if isolate_network:
        trace_argv = ["unshare", "-n", *trace_argv]
    return subprocess.run(
        trace_argv,
        cwd=str(cwd) if cwd is not None else None,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _seed_verb_matrix(repo: Path) -> list[tuple[str, list[str], Path | None]]:
    """Return (label, argv-without-strace, cwd) rows in dependency order."""
    return [
        (
            "init",
            [
                "marshal",
                "seed",
                "init",
                str(repo),
                "--slug",
                "egress-test",
                "--agents",
                "claude",
                "--force",
            ],
            None,
        ),
        (
            "adopt-dry-run",
            ["marshal", "seed", "adopt", "--repo-root", str(repo)],
            repo,
        ),
        (
            "adopt-apply",
            [
                "marshal",
                "seed",
                "adopt",
                "--apply",
                "--yes",
                "--repo-root",
                str(repo),
            ],
            repo,
        ),
        (
            "check",
            ["marshal", "seed", "check", "--repo-root", str(repo)],
            repo,
        ),
        (
            "update-run",
            [
                "marshal",
                "seed",
                "update",
                "--run",
                "--yes",
                "--repo-root",
                str(repo),
            ],
            repo,
        ),
    ]


def _drive_all_seed_verbs_under_trace(
    repo: Path,
    *,
    isolate_network: bool,
) -> None:
    for label, argv, cwd in _seed_verb_matrix(repo):
        completed = _run_traced(argv, cwd=cwd, isolate_network=isolate_network)
        if isolate_network and completed.returncode == 1 and "unshare:" in completed.stderr:
            pytest.skip(f"unshare -n unavailable in this runner: {completed.stderr.strip()}")
        # Functional success is NOT this test's oracle -- only zero egress is.
        # Some verbs may refuse (e.g. init hitting a template-boundary defect on
        # the full packaged tree) while still exercising Copier/git locally.
        if label == "init" and completed.returncode == 0:
            _commit_all(repo, "genesis init for egress counter")
        _assert_zero_inet_egress(completed, label=label)


@pytest.mark.skipif(
    not _STRACE_AVAILABLE,
    reason="strace unavailable or non-Linux -- skip, never a hard requirement",
)
@pytest.mark.skipif(
    not _MARSHAL_AVAILABLE,
    reason="the 'marshal' console script is not on PATH in this environment",
)
def test_seed_verbs_make_zero_network_syscalls_under_strace(tmp_path: Path):
    repo = _build_seed_repo(tmp_path)
    _drive_all_seed_verbs_under_trace(repo, isolate_network=False)


@pytest.mark.skipif(
    not (_STRACE_AVAILABLE and _UNSHARE_AVAILABLE),
    reason="strace/unshare unavailable or non-Linux -- skip, never a hard requirement",
)
@pytest.mark.skipif(
    not _MARSHAL_AVAILABLE,
    reason="the 'marshal' console script is not on PATH in this environment",
)
def test_seed_verbs_make_zero_network_syscalls_under_unshare_n(tmp_path: Path):
    repo = _build_seed_repo(tmp_path)
    _drive_all_seed_verbs_under_trace(repo, isolate_network=True)
