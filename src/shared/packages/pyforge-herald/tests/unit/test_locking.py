"""``locking.py``'s cross-platform advisory-lock primitive (Story 13.1,
closing ``DW-1-4-2``) -- unit tests for the lock itself, independent of any
particular document-store module (``test_state.py``/``test_progress.py``/
``test_claims.py``/``test_notices.py`` each carry their own regression test
proving the lock actually closes their module's lost-update race).
"""

from __future__ import annotations

import errno
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from pyforge.herald import locking
from pyforge.herald.errors import HeraldError


def test_locked_serializes_two_threads(tmp_path: Path):
    """Two threads racing for the same lock never interleave: whichever
    acquires first runs its whole (deliberately slow) critical section to
    completion before the other's critical section starts -- proof that
    ``locked`` actually excludes, not just "usually happens to" via thread
    scheduling luck."""
    lock_path = tmp_path / "doc.lock"
    events: list[str] = []

    def worker(name: str) -> None:
        with locking.locked(lock_path):
            events.append(f"{name}-start")
            time.sleep(0.1)
            events.append(f"{name}-end")

    t1 = threading.Thread(target=worker, args=("a",))
    t2 = threading.Thread(target=worker, args=("b",))
    t1.start()
    time.sleep(0.02)  # give t1 a head start acquiring the lock first
    t2.start()
    # Bounded joins: a lock regression that deadlocks a worker must fail this
    # test, not hang pytest until the CI job's own timeout kills the run.
    t1.join(timeout=10)
    t2.join(timeout=10)
    assert not t1.is_alive() and not t2.is_alive(), "a worker deadlocked on the lock"

    assert events in (
        ["a-start", "a-end", "b-start", "b-end"],
        ["b-start", "b-end", "a-start", "a-end"],
    )


_HOLD_LOCK_SCRIPT = """
import sys
import time
from pathlib import Path
from pyforge.herald import locking

lock_path = Path(sys.argv[1])
with locking.locked(lock_path):
    print("ACQUIRED", flush=True)
    time.sleep(60)
"""


def _readline_or_fail(proc: subprocess.Popen, *, timeout: float = 15.0) -> str:
    """One line from ``proc``'s stdout, or a test failure if it does not
    arrive within ``timeout``.

    A bare ``proc.stdout.readline()`` blocks forever if the child never
    reaches its ``print`` (a slow import, a differently-resolved
    ``pyforge.herald``, an fd-inheritance quirk). This suite configures no
    pytest-level timeout, so that would hang CI until the job timeout
    instead of failing. Read on a daemon thread and bound the wait."""
    line: list[str] = []

    def _read() -> None:
        if proc.stdout is not None:
            line.append(proc.stdout.readline())

    t = threading.Thread(target=_read, daemon=True)
    t.start()
    t.join(timeout=timeout)
    if not line:
        proc.kill()
        pytest.fail(f"child process produced no output within {timeout}s")
    return line[0]


def test_locked_releases_when_the_holding_process_is_killed(tmp_path: Path):
    """The I/O matrix's "process crashes while holding the lock" row: a
    genuine, separate OS process acquires the lock and is then SIGKILLed --
    no ``finally``, no context-manager cleanup, nothing but the OS's own
    process-exit fd cleanup runs. A fresh acquire must still succeed
    promptly, proving the lock is never left stuck-held by a dead holder
    (no stale-lock cleanup needed, matching the spec's own Never list)."""
    lock_path = tmp_path / "doc.lock"
    proc = subprocess.Popen(
        [sys.executable, "-c", _HOLD_LOCK_SCRIPT, str(lock_path)],
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        line = _readline_or_fail(proc)
        assert line.strip() == "ACQUIRED", "background process never acquired the lock"

        acquired = threading.Event()
        waiting = threading.Event()

        def _try_acquire() -> None:
            waiting.set()
            with locking.locked(lock_path):
                acquired.set()

        t = threading.Thread(target=_try_acquire, daemon=True)
        t.start()
        # Wait until the thread is actually at (or entering) the blocking
        # acquire before killing the holder. Without this the child is
        # usually dead before the thread reaches `locked`, and the test
        # silently degrades into "acquire an already-free lock" -- which
        # would pass even if a dead holder DID leave the lock stuck.
        assert waiting.wait(timeout=5), "waiter thread never started"
        time.sleep(0.2)
        assert not acquired.is_set(), (
            "waiter acquired the lock while the holder was still alive -- the lock is not excluding across processes"
        )

        proc.kill()
        proc.wait(timeout=5)
        t.join(timeout=5)
        assert acquired.is_set(), "lock was not released after the holding process was killed"
    finally:
        if proc.stdout is not None:
            proc.stdout.close()
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)


def test_locked_excludes_a_second_os_process(tmp_path: Path):
    """Cross-PROCESS exclusion, not just cross-thread. Every other
    concurrency test in this package races threads inside one interpreter,
    so all of them would stay green if ``_acquire`` were ever "simplified"
    into a module-level ``threading.Lock`` -- which would silently reopen
    the multi-process lost-update race this whole story exists to close
    (the motivating case is two separate ``herald`` invocations). This test
    is the one that would fail."""
    lock_path = tmp_path / "doc.lock"
    proc = subprocess.Popen(
        [sys.executable, "-c", _HOLD_LOCK_SCRIPT, str(lock_path)],
        stdout=subprocess.PIPE,
        text=True,
    )
    acquired = threading.Event()
    release = threading.Event()
    failures: list[BaseException] = []

    def _try_acquire() -> None:
        # A full `with` block, and every exception recorded: `acquired`
        # staying clear because `locked` RAISED looks identical to it
        # staying clear because `locked` correctly BLOCKED, so an
        # unrecorded failure would make this test pass against a lock that
        # does not work at all. Entering the contextmanager by hand
        # (`.__enter__()` with no matching `__exit__`) would also strand
        # the lock and its descriptor for the rest of the session.
        try:
            with locking.locked(lock_path):
                acquired.set()
                release.wait(timeout=5)
        except BaseException as exc:  # noqa: BLE001 - re-raised via `failures`
            failures.append(exc)

    t = threading.Thread(target=_try_acquire, daemon=True)
    try:
        assert _readline_or_fail(proc).strip() == "ACQUIRED"

        t.start()
        # The other PROCESS holds the lock, so this must not succeed.
        assert not acquired.wait(timeout=1.0), (
            "acquired a lock held by another OS process -- the lock is thread-local, not process-level"
        )
        assert not failures, f"locked() raised instead of blocking on a lock another process holds: {failures[0]!r}"
    finally:
        release.set()
        if proc.stdout is not None:
            proc.stdout.close()
        proc.kill()
        proc.wait(timeout=5)
        # The holder is gone, so the waiter can now take and release the
        # lock -- joined so it cannot outlive the test holding it. Guarded
        # on `ident` because an assertion above can fail before `t.start()`,
        # and joining an unstarted thread raises RuntimeError, which would
        # replace the real failure.
        if t.ident is not None:
            t.join(timeout=5)
            assert not t.is_alive(), "waiter thread never finished"


def test_locked_releases_when_the_guarded_block_raises(tmp_path: Path):
    """``locked``'s ``finally: _release(fd)`` is the single most load-bearing
    line in the module, and this story adds several raise-inside-the-lock
    paths (``claims``' ``ClaimNotFoundError``/``ClaimStateError``, every
    ``notices`` ``HeraldError`` now moved inside the ``with``). If an
    exception ever leaked without releasing, the next acquire would wedge
    the process forever -- so prove the lock is reusable after one."""
    lock_path = tmp_path / "doc.lock"

    with pytest.raises(RuntimeError, match="boom"), locking.locked(lock_path):
        raise RuntimeError("boom")

    acquired_again = threading.Event()

    def _reacquire() -> None:
        with locking.locked(lock_path):
            acquired_again.set()

    t = threading.Thread(target=_reacquire, daemon=True)
    t.start()
    t.join(timeout=5)
    assert acquired_again.is_set(), "lock stayed held after the guarded block raised -- next acquire wedged"


def test_a_failing_teardown_never_masks_the_guarded_block(tmp_path: Path, monkeypatch):
    """``locked`` closes its descriptor in a ``finally``, so an ``os.close``
    that fails (EIO on an odd filesystem, EBADF) would replace whatever
    exception the guarded block raised -- and surface as a raw ``OSError``
    out of a module that documents ``HeraldError`` as its only failure mode
    (AD-6). Both teardown steps are suppressed; the fd is freed by the OS
    either way."""
    lock_path = tmp_path / "doc.lock"
    real_open = os.open
    real_close = os.close
    ours: set[int] = set()
    closed: list[int] = []

    def tracking_open(*args, **kwargs) -> int:
        fd = real_open(*args, **kwargs)
        ours.add(fd)
        return fd

    def failing_close(fd: int) -> None:
        # Scoped to the descriptors `locked` itself opened. `locking.os` IS
        # the global `os` module, so an unconditional patch would make every
        # `os.close` in the interpreter fail for the duration of this test --
        # safe only by accident today, and a trap for anything later added to
        # this test body (a subprocess, a tempfile error path, a capfd read).
        real_close(fd)
        if fd not in ours:
            return
        closed.append(fd)
        raise OSError(errno.EIO, "close failed")

    monkeypatch.setattr(locking.os, "open", tracking_open)
    monkeypatch.setattr(locking.os, "close", failing_close)

    with (
        pytest.raises(HeraldError, match="the real failure"),
        locking.locked(lock_path),
    ):
        raise HeraldError("the real failure")
    assert closed, "the descriptor was never closed"

    # ...and a clean block does not surface the teardown failure either.
    with locking.locked(lock_path):
        pass


def test_lock_path_for_refuses_a_path_with_no_file_name():
    """``Path.with_name`` raises a raw ``ValueError`` on an empty-name path
    (``Path("/")``, ``Path(".")``). Deriving the sidecar path through
    ``lock_path_for`` turns that into a ``HeraldError`` instead, so a
    caller handing in a directory where a document was expected still gets
    this package's structural-failure contract (AD-6) rather than a stray
    ``ValueError``.

    ``Path("..")`` is deliberately not in this list: its ``name`` is
    ``".."``, not empty, so ``with_name`` accepts it and no guard fires."""
    for bad in (Path("/"), Path(".")):
        with pytest.raises(HeraldError, match="not a file path"):
            locking.lock_path_for(bad)


def test_locked_raises_herald_error_when_the_lock_call_itself_fails(tmp_path: Path, monkeypatch):
    """The OTHER acquisition-failure wrap: everything else here trips on
    ``mkdir``/``os.open``, so nothing drove the ``_acquire`` branch -- the
    one the Windows ``EDEADLOCK``-only retry exists to make reachable. A
    permanent lock failure (EACCES, EBADF, EINVAL, a volume without
    byte-range locking) must surface as ``HeraldError`` naming the lock
    path, never as the raw ``OSError`` ``_acquire`` re-raises."""
    lock_path = tmp_path / "doc.lock"

    def failing_acquire(fd: int) -> None:
        raise OSError(errno.EINVAL, "lock unsupported on this volume")

    monkeypatch.setattr(locking, "_acquire", failing_acquire)

    with (
        pytest.raises(HeraldError, match=str(lock_path)) as excinfo,
        locking.locked(lock_path),
    ):
        pytest.fail("the guarded block must not run when acquire fails")
    assert isinstance(excinfo.value.__cause__, OSError)


def test_locked_raises_herald_error_on_unwritable_parent_directory(tmp_path: Path):
    """A plain file where the lock's parent directory should be must
    surface as ``HeraldError`` naming the lock path, never a raw
    ``OSError`` -- mirrors ``state.py``'s own AD-6 discipline."""
    blocker = tmp_path / "not-a-directory"
    blocker.write_text("plain file")
    lock_path = blocker / "doc.lock"
    with pytest.raises(HeraldError, match=str(lock_path)), locking.locked(lock_path):
        pass
