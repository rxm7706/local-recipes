"""Corpus-scale egress counter (Story 5.2) -- closes the ``deferred-work.md``
item raised during the spec-1-4-osv-db-offline-provisioning-spike review
(Blind Hunter finding 7, "owned by Story 5.2"):

    "the 1.4 proof test establishes offline behavior by passing --offline
    and pointing at the fixture DB, but does NOT observe the osv-scanner
    subprocess's network (the in-process socket-deny harness cannot patch
    a child process) -- a future osv that egressed under --offline
    (telemetry, transitive resolution) would pass silently ... Hardening =
    run the engine subprocess in a network namespace / with an egress
    counter at corpus scale -- owned by Story 5.2."

``OsvEngine.run`` (``engines.py``) always passes osv-scanner's own
``--offline`` flag -- this test OBSERVES that promise from OUTSIDE the
process, the one vantage point the in-process socket-deny harness
(``tests/conftest.py``) structurally cannot reach for a forked child. The
whole ``warden scan`` process tree (the CLI process + every engine
subprocess it forks -- deptry, osv-scanner) is wrapped in
``strace -f -e trace=network``, scanning the full corpus (not a toy
fixture, per the deferred item's own "at corpus scale" wording) --
asserting ZERO ``connect``/``sendto`` syscalls anywhere in the trace.

Linux-only, skip-if-``strace``-unavailable (mirrors ``test_extraction_
oracle.py``'s skip-if-renderer-unavailable convention -- never a hard
requirement on a platform/environment without it). Marked
``@pytest.mark.slow`` (a real subprocess-heavy corpus scan under strace
instrumentation -- the same corpus-scale-real-subprocess cost class as
``test_corpus_determinism.py``)."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.slow

CORPUS_RECIPES_DIR = (
    Path(__file__).resolve().parent.parent / "fixtures" / "corpus" / "recipes"
)

_STRACE_AVAILABLE = sys.platform.startswith("linux") and shutil.which("strace") is not None
_WARDEN_AVAILABLE = shutil.which("warden") is not None


@pytest.mark.skipif(
    not _STRACE_AVAILABLE,
    reason="strace unavailable or non-Linux -- skip, never a hard requirement",
)
@pytest.mark.skipif(
    not _WARDEN_AVAILABLE,
    reason="the 'warden' console script is not on PATH in this environment",
)
def test_corpus_scan_makes_zero_network_syscalls_under_strace():
    assert CORPUS_RECIPES_DIR.is_dir(), (
        f"{CORPUS_RECIPES_DIR} missing -- run scripts/harvest_corpus.py"
    )
    argv = [
        "strace",
        "-f",  # follow forks -- deptry/osv-scanner run as child subprocesses
        "-e",
        "trace=network",
        "warden",
        "scan",
        str(CORPUS_RECIPES_DIR),
    ]
    completed = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        timeout=180,
    )
    # strace writes its trace to stderr by default (stdout stays the
    # traced program's own, which is warden's -- irrelevant here). A
    # sandboxed/seccomp-restricted runner without CAP_SYS_PTRACE can make
    # `strace` fail to attach entirely -- silently producing an EMPTY
    # trace that would let `not network_lines` pass vacuously below,
    # proving nothing (review finding). `strace -f` on a real, non-trivial
    # `warden scan` always emits substantial diagnostic output (at minimum
    # one "+++ exited with N +++"/"+++ killed by" line per traced process),
    # so a blank trace is itself the tell that tracing never happened.
    assert completed.stderr.strip(), (
        "strace produced no output at all -- tracing likely failed to "
        "attach (e.g. missing CAP_SYS_PTRACE in a sandboxed runner); this "
        "test cannot make its zero-network-syscalls claim in that state\n"
        f"strace exit code: {completed.returncode}"
    )
    # The network syscall family strace's `-e trace=network` already
    # restricts to: connect/send variants are the ones that can egress
    # data or reveal a DNS/transitive-resolution attempt (Story 5.2 review
    # finding: the original filter only matched connect/sendto, missing an
    # already-connected socket's plain send()/sendmsg(), and glibc's
    # sendmmsg()-based parallel DNS resolver path).
    _NETWORK_SYSCALL_NAMES = ("connect", "send", "sendto", "sendmsg", "sendmmsg")
    network_lines = [
        line
        for line in completed.stderr.splitlines()
        if any(f"{name}(" in line for name in _NETWORK_SYSCALL_NAMES)
    ]
    assert not network_lines, (
        "unexpected network syscall(s) during an --offline corpus scan:\n"
        + "\n".join(network_lines[:20])
    )
