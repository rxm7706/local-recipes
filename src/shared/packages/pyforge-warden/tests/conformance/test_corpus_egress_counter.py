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
subprocess it forks -- osv-scanner on this corpus; deptry only when
hygiene applies, which a manifests-only corpus does not trigger) is
wrapped in ``strace -f -e trace=network``, scanning the full corpus (not
a toy fixture, per the deferred item's own "at corpus scale" wording) --
asserting ZERO internet-family connect/send-variant syscalls anywhere in
the trace.

Linux-only, skip-if-``strace``-unavailable (mirrors ``test_extraction_
oracle.py``'s skip-if-renderer-unavailable convention -- never a hard
requirement on a platform/environment without it). Marked
``@pytest.mark.slow`` (a real subprocess-heavy corpus scan under strace
instrumentation -- the same corpus-scale-real-subprocess cost class as
``test_corpus_determinism.py``)."""

from __future__ import annotations

import os
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
    # This test only observes a real engine subprocess because tests/
    # conftest.py's autouse `_osv_ambient_db_env` fixture exports the
    # ambient OSV DB path into os.environ, which subprocess.run inherits
    # -- without it, `warden scan` of a manifests-only corpus forks NO
    # engine subprocess at all (osv-scanner early-returns unprovisioned;
    # deptry needs hygiene applicability) and the zero-network assertion
    # below would be vacuous (follow-up review finding). Assert the
    # dependency explicitly so a future conftest refactor fails loud here
    # instead of silently un-closing the deferred-work item.
    assert os.environ.get("OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY"), (
        "ambient OSV DB env var missing (tests/conftest.py's "
        "_osv_ambient_db_env fixture) -- without it the scan forks no "
        "engine subprocess and this egress counter observes nothing"
    )
    # strace writes its trace to stderr by default (stdout stays the
    # traced program's own, which is warden's -- irrelevant here). A
    # sandboxed/seccomp-restricted runner without CAP_SYS_PTRACE can make
    # `strace` fail to attach -- and strace's own error message ("strace:
    # ptrace(PTRACE_TRACEME, ...): Operation not permitted") ALSO lands on
    # stderr, so a mere non-empty-stderr check proves nothing (follow-up
    # review finding on the first pass's guard). The tell that tracing
    # actually happened is strace's per-process exit marker: `-f` emits
    # one "+++ exited with N +++" line per traced process. Requiring >= 2
    # markers proves BOTH that tracing attached AND that at least one
    # child process (an engine subprocess) ran under the trace.
    exit_markers = completed.stderr.count("+++ exited with")
    assert exit_markers >= 2, (
        "expected strace to trace the warden process AND at least one "
        f"engine subprocess (saw {exit_markers} '+++ exited with' "
        "marker(s)) -- either tracing failed to attach (e.g. missing "
        "CAP_SYS_PTRACE in a sandboxed runner) or the scan forked no "
        "engine subprocess; either way the zero-network-syscalls claim "
        "below would be vacuous\n"
        f"strace exit code: {completed.returncode}\n"
        f"stderr head: {completed.stderr[:500]}"
    )
    # The syscalls that can egress data or reveal a DNS/transitive-
    # resolution attempt (Story 5.2 review finding: the original filter
    # only matched connect/sendto, missing an already-connected socket's
    # plain send()/sendmsg(), and glibc's sendmmsg()-based parallel DNS
    # resolver path). `-e trace=network` traces ALL socket domains,
    # including purely LOCAL AF_UNIX (nscd/sssd NSS lookups) and
    # AF_NETLINK (glibc interface enumeration) traffic that is not egress
    # (follow-up review finding: an unqualified substring match spuriously
    # fails on hosts using such NSS backends). Requiring an AF_INET/
    # AF_INET6 token in the line stays leak-tight: any internet-bound path
    # must show the family in a connect()/sendto() sockaddr within this
    # same -f trace -- a family-less send() on an already-connected socket
    # is always preceded by that socket's flagged connect().
    _NETWORK_SYSCALL_NAMES = ("connect", "send", "sendto", "sendmsg", "sendmmsg")
    _INET_FAMILIES = ("AF_INET", "AF_INET6")
    network_lines = [
        line
        for line in completed.stderr.splitlines()
        if any(f"{name}(" in line for name in _NETWORK_SYSCALL_NAMES)
        and any(family in line for family in _INET_FAMILIES)
    ]
    assert not network_lines, (
        "unexpected internet-family network syscall(s) during the corpus "
        "scan (engines run under their own --offline discipline):\n"
        + "\n".join(network_lines[:20])
    )
