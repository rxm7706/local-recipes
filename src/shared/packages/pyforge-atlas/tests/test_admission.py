"""Story 10.6 — run-admission tests (collected by ``kedro-test``).

The defect this story closes is **cross-process**, so the gate is cross-process: a real
second OS process spawned with ``subprocess.Popen([sys.executable, "-c", ...])``, driving a
real ``kedro.pipeline.Pipeline`` + ``DataCatalog`` through the real
:class:`~pyforge.atlas.admission.RunAdmissionHooks`. No threads, no mocks, no monkeypatched
lock in the gate. (``subprocess`` is banned inside ``src/pyforge/atlas/**``, never in
``tests/`` — ``tests/catalog/test_credential_scoping.py`` is the in-suite precedent.)

Review pass 1 — the gap that let a CWD-relative lock root ship green
--------------------------------------------------------------------
Every test of the first implementation injected ``lock_root=tmp_path``, so nothing ever
exercised :func:`~pyforge.atlas.admission.default_lock_root` against reality, and the one
test named for it asserted a hardcoded ``Path("data")/".locks"``. Two processes writing the
SAME Parquet from different working directories therefore took locks in different
directories and never contended — the flagship race was completely open behind a green gate.
So this module opens with three tests that exercise the shipped default rather than an
injected one: the cross-CWD anchor (compared against a *real catalog entry's* resolved
filepath), an absolute ``PYFORGE_ATLAS_DATA_ROOT``, and the real ``settings.HOOKS`` driven
through kedro's real ``_create_hook_manager()`` with NO injected lock root.

Review pass 2 — the wait test that passed with the wait switched off
--------------------------------------------------------------------
``test_gate_opt_in_wait_admits_...`` used to spawn a holder that released after 0.3s and
then a waiter, asserting only ``elapsed >= 0.2``. The waiter's own interpreter + kedro
import spends seconds before it ever touches a lock, so the holder had always released
before the waiter contended: the test passed unchanged with ``wait_seconds=0.0``, i.e. with
the feature it names disabled. Half of AC D3 shipped unproven. The rewrite makes the PARENT
hold the ticket (no startup cost), announces the child's readiness over a stderr handshake,
and requires the child to stay SILENT while the lock is held — a reject-fast child speaks
inside that window, so the mutation now reds.

The harness must never HANG an unattended run: every child read is bounded by
:data:`_CHILD_TIMEOUT` and fails loudly on expiry, and no child's ``stderr`` is left on an
undrained pipe (it goes to a file, so a child that floods it cannot deadlock the parent).
"""

from __future__ import annotations

import copy
import json
import os
import pickle
import queue
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

import filelock
import pytest
from kedro.framework.hooks.manager import _create_hook_manager
from kedro.io import DataCatalog
from kedro.pipeline import Pipeline, node

from pyforge.atlas import admission
from pyforge.atlas.admission import (
    AdmissionConfigError,
    AdmissionTicket,
    RunAdmissionHooks,
    RunAdmissionRejected,
    acquire,
    default_lock_root,
    release,
)

MEMBER_DIR = Path(__file__).resolve().parents[1]

# Bound on every read from a child process. Generous enough for interpreter start +
# kedro/pandas import on a loaded machine, finite so a wedged child reds the suite instead
# of wedging it.
_CHILD_TIMEOUT = 45.0

# How long a child that must be BLOCKED is required to stay silent. It is measured AFTER the
# stderr readiness handshake, so it bounds "is it blocked on the lock?" and not "has it
# finished importing kedro?" — the confusion that made the old wait test vacuous. The suite's
# precedent for a bare interpreter+import warmup is the 3.0s in
# ``tests/dashboard/test_dashboard_e2e.py``; a reject-fast verdict lands in milliseconds once
# the handshake has fired, so this is orders of magnitude of margin either way.
_BLOCKED_WINDOW = 3.0

# Written to stderr by the child immediately before it calls the hook. stderr is already
# drained to a file, so this side channel leaves the stdout verdict protocol untouched.
_READY_TOKEN = "admission-child-ready"


# --------------------------------------------------------------------------- #
# The child program — a real pipeline + real hook in a real second OS process
# --------------------------------------------------------------------------- #

_CHILD_PROGRAM = r'''
import json, os, sys, time
from kedro.io import DataCatalog
from kedro.pipeline import Pipeline, node
from pyforge.atlas.admission import RunAdmissionHooks, RunAdmissionRejected


def _emit():
    """Never executed — only before_pipeline_run/after_pipeline_run run in this child."""
    return None


def main():
    lock_root, run_id = sys.argv[1], sys.argv[2]
    wait_seconds, hold_seconds = float(sys.argv[3]), float(sys.argv[4])
    datasets = sys.argv[5:]
    pipe = Pipeline([node(_emit, None, ds, name="emit_" + ds) for ds in datasets])
    catalog = DataCatalog({})
    run_params = {"run_id": run_id}
    hooks = RunAdmissionHooks(lock_root=lock_root, wait_seconds=wait_seconds)
    # Readiness handshake: everything expensive (interpreter start, kedro import) is behind
    # us, so a parent that sees this token and then hears NOTHING knows the child is blocked
    # on the lock rather than still booting.
    print("READY_TOKEN", file=sys.stderr, flush=True)
    try:
        hooks.before_pipeline_run(run_params=run_params, pipeline=pipe)
    except RunAdmissionRejected as exc:
        print(json.dumps({
            "verdict": "rejected", "pid": os.getpid(), "conflicting": exc.conflicting,
            "datasets": list(exc.datasets), "holder_run_id": exc.holder_run_id,
            "holder_pid": exc.holder_pid, "held_since": exc.held_since,
            "message": str(exc),
        }), flush=True)
        return
    # private registry read: the point is to exercise the HOOK path, then report what it took
    ticket = hooks._tickets[run_id][-1]
    print(json.dumps({
        "verdict": "admitted", "pid": os.getpid(),
        "datasets": list(ticket.datasets), "reclaimed": list(ticket.reclaimed),
    }), flush=True)
    if hold_seconds < 0:
        sys.stdin.readline()      # hold until the parent says stop (or SIGKILLs us)
    else:
        time.sleep(hold_seconds)  # hold for a fixed window, then release
    hooks.after_pipeline_run(run_params=run_params, pipeline=pipe)
    print(json.dumps({"verdict": "released", "pid": os.getpid()}), flush=True)


main()
'''.replace("READY_TOKEN", _READY_TOKEN)

_HOLD_UNTIL_TOLD = -1.0


class _Child:
    """One spawned admission process plus the bounded, deadlock-free way to read it."""

    def __init__(self, proc, stderr_path: Path, stderr_file) -> None:
        self.proc = proc
        self.stderr_path = stderr_path
        self._stderr_file = stderr_file
        # ONE reader thread per child, draining stdout into a queue. `readline()` takes no
        # timeout, so a per-read thread has to be ABANDONED on expiry — and an abandoned
        # reader silently swallows the very line the NEXT read wants. Pumping into a queue
        # makes a timed-out read lossless, which is what lets `poll_verdict` ("the child is
        # still blocked") be followed by `verdict` ("...and here is what it finally said").
        self._lines: queue.Queue[str] = queue.Queue()
        self._reader = threading.Thread(target=self._pump, daemon=True)
        self._reader.start()

    def _pump(self) -> None:
        try:
            for line in self.proc.stdout:
                self._lines.put(line)
        except (OSError, ValueError):  # the stream was closed under us during teardown
            pass

    def poll_verdict(self, timeout: float) -> dict | None:
        """The next verdict, or ``None`` when the child stayed silent for ``timeout``.

        Unlike :meth:`verdict` this does NOT kill on expiry: silence is the expected — and
        asserted — outcome when the child is supposed to be blocked on a held lock.
        """
        try:
            line = self._lines.get(timeout=timeout)
        except queue.Empty:
            return None
        return json.loads(line) if line.strip() else None

    def verdict(self, timeout: float = _CHILD_TIMEOUT) -> dict:
        verdict = self.poll_verdict(timeout)
        if verdict is None:
            self.kill()
            raise AssertionError(
                f"child produced no verdict within {timeout}s (the harness must never hang "
                f"an unattended run). stderr:\n{self._stderr_text()}"
            )
        return verdict

    def wait_until_ready(self, timeout: float = _CHILD_TIMEOUT) -> None:
        """Block until the child has imported kedro and is about to call the hook.

        Without this handshake, "the child said nothing for N seconds" is indistinguishable
        from "the child was still importing kedro" — precisely the ambiguity that let the
        opt-in-wait test pass with the wait disabled.
        """
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if _READY_TOKEN in self._stderr_text(whole=True):
                return
            if self.proc.poll() is not None:
                break
            time.sleep(0.05)
        self.kill()
        raise AssertionError(
            f"child never announced itself within {timeout}s. "
            f"stderr:\n{self._stderr_text()}"
        )

    def tell_to_release(self) -> None:
        try:
            self.proc.stdin.write("go\n")
            self.proc.stdin.flush()
        except (BrokenPipeError, ValueError):
            pass

    def _stderr_text(self, whole: bool = False) -> str:
        try:
            text = self.stderr_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return "<unreadable>"
        # The readiness token is written FIRST and kedro logging may push it out of a tail
        # window, so the handshake reads the whole file; diagnostics stay tail-only.
        return text if whole else text[-2000:]

    def kill(self) -> None:
        if self.proc.poll() is None:
            self.proc.kill()
        self.proc.wait(timeout=_CHILD_TIMEOUT)

    def close(self) -> None:
        # Callers always kill() first, so stdout is already at EOF and the pump has exited;
        # the bounded join only exists so we never close a stream out from under a live read.
        self._reader.join(timeout=5.0)
        for stream in (self.proc.stdin, self.proc.stdout):
            try:
                stream.close()
            except (OSError, ValueError):
                pass
        self._stderr_file.close()


@pytest.fixture
def spawn(tmp_path):
    """Spawn admission children and guarantee every one is reaped."""
    children: list[_Child] = []

    def _spawn(lock_root, run_id, datasets, *, wait_seconds=0.0, hold=_HOLD_UNTIL_TOLD):
        stderr_path = tmp_path / f"child-{run_id}-{len(children)}.stderr"
        # stderr goes to a FILE, never to an undrained pipe: a child that writes >64 KiB of
        # kedro/rich logging would otherwise deadlock while the parent blocks on stdout.
        stderr_file = stderr_path.open("w", encoding="utf-8")
        proc = subprocess.Popen(
            [
                sys.executable, "-c", _CHILD_PROGRAM,
                str(lock_root), run_id, str(wait_seconds), str(hold), *datasets,
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=stderr_file,
            text=True,
        )
        child = _Child(proc, stderr_path, stderr_file)
        children.append(child)
        return child

    yield _spawn

    for child in children:
        # One unreapable child must not abandon the rest still holding flocks in tmp_path:
        # `kill()` waits with a timeout and can raise `TimeoutExpired`, which would otherwise
        # break out of this loop.
        try:
            child.kill()
        except Exception:  # noqa: BLE001 - teardown reaps every child or none
            pass
        finally:
            child.close()


def _pipeline(*datasets: str) -> Pipeline:
    return Pipeline([node(_no_op, None, ds, name=f"emit_{ds}") for ds in datasets])


def _no_op():
    return None


def _is_free(lock_root, name: str) -> bool:
    """Can a fresh lock object take ``name``? The only honest way to say 'released'."""
    probe = filelock.FileLock(str(Path(lock_root) / f"{name}.lock"), thread_local=False)
    try:
        probe.acquire(timeout=0)
    except filelock.Timeout:
        return False
    probe.release()
    return True


# --------------------------------------------------------------------------- #
# Lock root: PROJECT-anchored, never CWD-relative (review pass 1 — the headline)
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def catalog_filepath_root() -> Path:
    """The root a REAL catalog entry's ``filepath`` resolves to.

    Kedro's ``KedroContext._get_catalog`` runs ``_convert_paths_to_absolute_posix(
    project_path=...)``, so this is the project root — NOT the CWD. Comparing the lock root
    against this (rather than against a hardcoded ``Path("data")/".locks"``) is what makes
    the assertion real.
    """
    _seed_stub_credentials()
    from kedro.framework.session import KedroSession
    from kedro.framework.startup import bootstrap_project

    bootstrap_project(MEMBER_DIR)
    with KedroSession.create(project_path=MEMBER_DIR) as session:
        filepath = session.load_context().catalog["core_feedstock_health"]._describe()["filepath"]
    # <root>/data/primary/core_feedstock_health/core_feedstock_health.parquet -> <root>
    return Path(str(filepath)).resolve().parents[3]


# Credential stubs are a test-harness concern; ``tests/orchestration/conftest.py`` owns the
# canonical version and the rationale. Repeated here (never overwriting an existing file) so
# this module is hermetic and collection-order-independent rather than relying on that
# directory being collected first.
_CREDENTIALS_KEY_RE = re.compile(r"^\s*credentials:\s*([A-Za-z_][A-Za-z0-9_]*)\s*$")


def _seed_stub_credentials() -> None:
    target = MEMBER_DIR / "conf" / "local" / "credentials.yml"
    if target.exists():
        return
    catalog = MEMBER_DIR / "conf" / "base" / "catalog.yml"
    keys = sorted(
        {
            m.group(1)
            for line in catalog.read_text(encoding="utf-8").splitlines()
            if (m := _CREDENTIALS_KEY_RE.match(line))
        }
    )
    if not keys:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "# AUTO-GENERATED STUB — see tests/orchestration/conftest.py.\n"
        + "\n".join(f'{key}: ["stub-user", "not-a-real-credential"]' for key in keys)
        + "\n",
        encoding="utf-8",
    )


def test_default_lock_root_is_project_anchored_not_cwd_relative(monkeypatch, tmp_path, catalog_filepath_root):
    """THE regression test for review pass 1's high finding.

    From a CWD that is not the project root, the lock root must still land under the same
    root a real catalog entry's filepath resolves to. A CWD-relative root would put the
    locks in ``<cwd>/data/.locks`` while the guarded Parquet lives under
    ``<project>/data/primary/...`` — two writers of one file, contending on nothing.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PYFORGE_ATLAS_LOCK_ROOT", raising=False)
    monkeypatch.delenv("PYFORGE_ATLAS_DATA_ROOT", raising=False)

    root = default_lock_root()

    assert root == (catalog_filepath_root / "data" / ".locks").resolve()
    # ...and explicitly NOT anchored to the foreign CWD.
    assert tmp_path.resolve() not in root.parents
    assert root != (tmp_path / "data" / ".locks").resolve()


def test_default_lock_root_is_identical_from_two_different_cwds(monkeypatch, tmp_path):
    """The property that actually closes the race: the MCP server (repo root) and a
    ``kedro run`` (the pixi tasks set ``cwd = src/shared/packages/pyforge-atlas``) must
    resolve the SAME lock root."""
    monkeypatch.delenv("PYFORGE_ATLAS_LOCK_ROOT", raising=False)
    monkeypatch.delenv("PYFORGE_ATLAS_DATA_ROOT", raising=False)
    monkeypatch.chdir(tmp_path)
    from_elsewhere = default_lock_root()
    monkeypatch.chdir(MEMBER_DIR)
    from_project = default_lock_root()

    assert from_elsewhere == from_project


def test_default_lock_root_honors_an_absolute_data_root_verbatim(monkeypatch, tmp_path):
    """Relocating the store relocates the locks with it (the documented override)."""
    monkeypatch.delenv("PYFORGE_ATLAS_LOCK_ROOT", raising=False)
    monkeypatch.setenv("PYFORGE_ATLAS_DATA_ROOT", str(tmp_path / "elsewhere"))
    monkeypatch.chdir(tmp_path)

    assert default_lock_root() == (tmp_path / "elsewhere" / ".locks").resolve()


def test_default_lock_root_resolves_a_relative_data_root_against_the_project(monkeypatch, tmp_path):
    monkeypatch.delenv("PYFORGE_ATLAS_LOCK_ROOT", raising=False)
    monkeypatch.setenv("PYFORGE_ATLAS_DATA_ROOT", "var/store")
    monkeypatch.chdir(tmp_path)

    assert default_lock_root() == (MEMBER_DIR / "var" / "store" / ".locks").resolve()


def test_lock_root_env_beats_data_root(monkeypatch, tmp_path):
    monkeypatch.setenv("PYFORGE_ATLAS_LOCK_ROOT", str(tmp_path / "locks-here"))
    monkeypatch.setenv("PYFORGE_ATLAS_DATA_ROOT", str(tmp_path / "data-there"))

    assert default_lock_root() == (tmp_path / "locks-here" / ".locks").resolve()


def test_empty_env_var_is_treated_as_unset(monkeypatch, tmp_path):
    """Mirrors ``settings._env_or`` (review-pass P6): ``export PYFORGE_ATLAS_DATA_ROOT=``
    must fall back to the default, not resolve the locks to the filesystem root."""
    monkeypatch.setenv("PYFORGE_ATLAS_LOCK_ROOT", "")
    monkeypatch.setenv("PYFORGE_ATLAS_DATA_ROOT", "")
    monkeypatch.chdir(tmp_path)

    assert default_lock_root() == (MEMBER_DIR / "data" / ".locks").resolve()


def test_a_whitespace_only_env_var_is_treated_as_unset(monkeypatch, tmp_path):
    """``export PYFORGE_ATLAS_DATA_ROOT="  "`` is a blanked override, not a request for a
    store directory literally named after the spaces — which is what a bare
    ``os.environ.get(...) or "data"`` would have created, one lock root per typo."""
    monkeypatch.setenv("PYFORGE_ATLAS_LOCK_ROOT", "   ")
    monkeypatch.setenv("PYFORGE_ATLAS_DATA_ROOT", "  ")
    monkeypatch.chdir(tmp_path)

    root = default_lock_root()

    assert root == (MEMBER_DIR / "data" / ".locks").resolve()
    assert not any(part.strip() == "" for part in root.parts), f"whitespace path {root}"


@pytest.mark.parametrize("relative", ["relative/path", "data", ".", "../elsewhere", Path("rel")])
def test_a_relative_project_path_is_refused(relative):
    """A relative ``project_path`` would quietly restore the CWD-anchoring review pass 1
    reverted. Kedro always supplies an absolute ``run_params["project_path"]``, but a Dagster
    resource-config override or a direct :func:`acquire` caller need not — so this fails
    loudly instead of guarding a directory the Parquet does not live in."""
    with pytest.raises(AdmissionConfigError, match="absolute"):
        default_lock_root(relative)


@pytest.mark.parametrize("relative", ["locks", "data/.locks", ".", "../locks", Path("rel")])
def test_a_relative_lock_root_is_refused(relative, tmp_path, monkeypatch):
    """The guard ``_resolve_base`` applies to ``project_path``, on the input path that used to
    skip it. ``acquire(lock_root="locks")`` — or ``RunAdmissionHooks(lock_root="locks")`` —
    silently re-anchored the locks to the CWD, which is the exact defect review pass 1
    reverted, reachable through a different door."""
    monkeypatch.chdir(tmp_path)
    with pytest.raises(AdmissionConfigError, match="absolute"):
        acquire(["a"], run_id="r1", lock_root=relative)
    assert list(tmp_path.iterdir()) == [], "a config error must take no locks"


def test_an_empty_project_path_falls_back_to_the_package_derived_root(monkeypatch, tmp_path):
    """``""`` means "not supplied", not "anchor here": it falls through to the
    ``__file__``-derived project root — still absolute, still the tree the guarded Parquet
    lives in — and never to the CWD."""
    monkeypatch.delenv("PYFORGE_ATLAS_LOCK_ROOT", raising=False)
    monkeypatch.delenv("PYFORGE_ATLAS_DATA_ROOT", raising=False)
    monkeypatch.chdir(tmp_path)

    assert default_lock_root("") == (MEMBER_DIR / "data" / ".locks").resolve()


def test_default_lock_root_uses_the_run_params_project_path(monkeypatch, tmp_path):
    """``run_params["project_path"]`` is the per-run channel the hook prefers — kedro
    supplies it in ``record_data``."""
    monkeypatch.delenv("PYFORGE_ATLAS_LOCK_ROOT", raising=False)
    monkeypatch.delenv("PYFORGE_ATLAS_DATA_ROOT", raising=False)

    assert default_lock_root(str(tmp_path)) == (tmp_path / "data" / ".locks").resolve()


def test_shipped_settings_hooks_lock_under_the_project_anchored_default(monkeypatch, tmp_path):
    """The wiring that actually ships is what this exercises: the real ``settings.HOOKS``,
    kedro's real hook manager, and NO injected ``lock_root`` — run from a foreign CWD."""
    from pyforge.atlas import settings

    monkeypatch.delenv("PYFORGE_ATLAS_LOCK_ROOT", raising=False)
    monkeypatch.delenv("PYFORGE_ATLAS_DATA_ROOT", raising=False)
    monkeypatch.chdir(tmp_path)

    name = "admission_wiring_probe"
    expected = (MEMBER_DIR / "data" / ".locks" / f"{name}.lock").resolve()
    hook_manager = _create_hook_manager()
    for hook in settings.HOOKS:
        hook_manager.register(hook)
    pipe, catalog = _pipeline(name), DataCatalog({})
    run_params = {"run_id": "wiring-probe", "project_path": str(MEMBER_DIR)}

    holder = expected.parent / f"{name}.holder.json"
    try:
        hook_manager.hook.before_pipeline_run(
            run_params=run_params, pipeline=pipe, catalog=catalog
        )
        try:
            assert expected.is_file(), f"no lock at the project-anchored default {expected}"
            assert not _is_free(expected.parent, name), "the shipped wiring took no real lock"
        finally:
            hook_manager.hook.after_pipeline_run(
                run_params=run_params, run_result={}, pipeline=pipe, catalog=catalog
            )
        assert _is_free(expected.parent, name)
        assert not holder.exists()
    finally:
        # This is the ONE test that writes into the REAL project tree instead of tmp_path,
        # and `filelock` never unlinks a lock file — so without this the probe's lock sits in
        # `data/.locks/` forever after the first run. Gitignored, but not hermetic.
        for leftover in (expected, holder):
            try:
                leftover.unlink(missing_ok=True)
            except OSError:  # never mask the real assertion with a cleanup failure
                pass


# --------------------------------------------------------------------------- #
# Registration + the deepcopy/pickle contract (AD-23)
# --------------------------------------------------------------------------- #


def test_hook_registered_in_settings_beside_the_others():
    from pyforge.atlas import settings

    kinds = [type(h).__name__ for h in settings.HOOKS]
    assert "RunAdmissionHooks" in kinds
    assert {"ProjectHooks", "AtlasObservabilityHooks", "DataValidationHooks"} <= set(kinds)


def _dispatch_order(hook_manager, hook_name: str) -> list[str]:
    """Plugin class names in the order pluggy will CALL them.

    ``get_hookimpls()`` returns the internal list, whose LAST element is called first.
    """
    impls = getattr(hook_manager.hook, hook_name).get_hookimpls()
    return [type(impl.plugin).__name__ for impl in reversed(impls)]


def test_admission_is_dispatched_first_on_a_real_session_not_merely_last_in_the_tuple():
    """The claim is about DISPATCH order, so assert dispatch order — on a real session.

    The version this replaces asserted ``settings.HOOKS[-1] is RunAdmissionHooks`` and called
    that "LIFO ⇒ dispatched first". It is not the same statement, and the difference was
    live: ``KedroSession.__init__`` registers ``settings.HOOKS`` and THEN
    ``_register_hooks_entry_points(...)``, so an installed plugin registers later and — under
    LIFO — dispatches EARLIER. Measured before the fix, kedro-viz's ``PipelineRunStatusHook``
    preceded admission on all three hooks. ``@hook_impl(tryfirst=True)`` is what actually buys
    the ordering; this test is what stops it being removed as decoration.
    """
    _seed_stub_credentials()
    from kedro.framework.session import KedroSession
    from kedro.framework.startup import bootstrap_project

    bootstrap_project(MEMBER_DIR)
    with KedroSession.create(project_path=MEMBER_DIR) as session:
        hook_manager = session._hook_manager
        for hook_name in ("before_pipeline_run", "after_pipeline_run", "on_pipeline_error"):
            order = _dispatch_order(hook_manager, hook_name)
            assert order[0] == "RunAdmissionHooks", (
                f"{hook_name} dispatch order is {order} — admission must acquire before, and "
                f"release before, every other implementation (including entry-point plugins)"
            )


def test_deepcopy_is_a_working_hook_with_empty_per_run_state(tmp_path):
    """Defence, not a measured copy: kedro-dagster 0.7.x passes the hook manager BY REFERENCE
    (``translator.py`` -> ``self._context._hook_manager``), so the Dagster plane runs against
    this very object. The contract still has to hold for whichever of deepcopy/pickle a future
    translator or multiprocess runner reaches for — configuration by value, tickets never."""
    original = RunAdmissionHooks(lock_root=tmp_path)
    original.before_pipeline_run(run_params={"run_id": "r1"}, pipeline=_pipeline("a"))
    try:
        dup = copy.deepcopy(original)
        assert isinstance(dup, RunAdmissionHooks)
        assert dup._tickets == {}          # per-run state is fresh, never a copied handle
        assert dup._lock_root == tmp_path  # configuration carries over
    finally:
        original.after_pipeline_run(run_params={"run_id": "r1"}, pipeline=_pipeline("a"))
    # and the copy is still a working hook
    dup.before_pipeline_run(run_params={"run_id": "r2"}, pipeline=_pipeline("a"))
    assert not _is_free(tmp_path, "a")
    dup.after_pipeline_run(run_params={"run_id": "r2"}, pipeline=_pipeline("a"))
    assert _is_free(tmp_path, "a")


def test_pickle_roundtrip_drops_tickets_and_still_works(tmp_path):
    """Multiprocess runners pickle the hooks. A FileLock cannot cross a process boundary —
    the flock belongs to the ORIGINAL process's open file description — so tickets are
    dropped rather than shipped as a lie."""
    original = RunAdmissionHooks(lock_root=tmp_path, wait_seconds=2)
    original.before_pipeline_run(run_params={"run_id": "r1"}, pipeline=_pipeline("a"))
    try:
        dup = pickle.loads(pickle.dumps(original))
    finally:
        original.after_pipeline_run(run_params={"run_id": "r1"}, pipeline=_pipeline("a"))
    assert dup._tickets == {}
    assert dup._wait_seconds == 2
    dup.before_pipeline_run(run_params={"run_id": "r3"}, pipeline=_pipeline("b"))
    dup.after_pipeline_run(run_params={"run_id": "r3"}, pipeline=_pipeline("b"))
    assert _is_free(tmp_path, "b")


def test_the_hooks_are_callable_on_both_the_kedro_and_the_dagster_plane(tmp_path):
    """Kedro passes ``run_result``; kedro-dagster passes ``run_results=None`` and omits it.

    Our ``after_pipeline_run`` declares only the subset it reads, so BOTH call shapes reach
    it and release. Driven through kedro's REAL ``_create_hook_manager()``.
    """
    hooks = RunAdmissionHooks(lock_root=tmp_path)
    hook_manager = _create_hook_manager()
    hook_manager.register(hooks)
    pipe, catalog = _pipeline("a"), DataCatalog({})

    for plane_kwargs in ({"run_result": {}}, {"run_results": None}):
        run_params = {"run_id": f"run-{sorted(plane_kwargs)[0]}"}
        hook_manager.hook.before_pipeline_run(
            run_params=run_params, pipeline=pipe, catalog=catalog
        )
        assert not _is_free(tmp_path, "a")
        hook_manager.hook.after_pipeline_run(
            run_params=run_params, pipeline=pipe, catalog=catalog, **plane_kwargs
        )
        assert _is_free(tmp_path, "a"), f"not released on the {plane_kwargs} plane"


def test_admission_releases_before_the_observability_hookcallerror_on_the_dagster_plane(tmp_path):
    """DW-AD23-2, pinned. kedro-dagster's after-op omits kedro's ``run_result``; pluggy's
    missing-argument check is per-IMPL, so ``AtlasObservabilityHooks`` (which still declares
    it) raises ``HookCallError``. Admission is dispatched FIRST — bought by
    ``@hook_impl(tryfirst=True)``, NOT by its position in ``settings.HOOKS`` (review pass 3
    measured tuple position to be insufficient) — so the locks are already released when that
    raise happens."""
    from pyforge.atlas.observability import AtlasObservabilityHooks

    hooks = RunAdmissionHooks(lock_root=tmp_path)
    hook_manager = _create_hook_manager()
    for hook in (AtlasObservabilityHooks(), hooks):  # settings.HOOKS order
        hook_manager.register(hook)
    pipe, catalog = _pipeline("a"), DataCatalog({})
    run_params = {"run_id": "dagster-plane"}

    hook_manager.hook.before_pipeline_run(
        run_params=run_params, pipeline=pipe, catalog=catalog
    )
    with pytest.raises(Exception, match="run_result"):
        hook_manager.hook.after_pipeline_run(
            run_results=None, run_params=run_params, pipeline=pipe, catalog=catalog
        )
    assert _is_free(tmp_path, "a"), "admission must release before the E2 hook raises"


# --------------------------------------------------------------------------- #
# THE GATE — a real second OS process
# --------------------------------------------------------------------------- #


def test_gate_same_set_contender_is_rejected_across_processes(tmp_path, spawn):
    """Process A holds ``{a, b}``; process B requests ``{a, b}`` → rejected immediately,
    naming the first conflict in sorted order plus A's run id, PID and hold start."""
    holder = spawn(tmp_path, "run-A", ["b", "a"])
    admitted = holder.verdict()
    assert admitted["verdict"] == "admitted"
    assert admitted["datasets"] == ["a", "b"]  # sorted acquisition order (D4)

    contender = spawn(tmp_path, "run-B", ["a", "b"])
    rejected = contender.verdict()

    assert rejected["verdict"] == "rejected"
    assert rejected["conflicting"] == "a"
    assert rejected["holder_run_id"] == "run-A"
    assert rejected["holder_pid"] == admitted["pid"]
    assert isinstance(rejected["held_since"], float)
    assert holder.proc.poll() is None, "the holder must still be running"


def test_gate_disjoint_set_contender_is_admitted_concurrently(tmp_path, spawn):
    """Admission is per dataset set, not global: ``{c}`` runs while ``{a, b}`` is held."""
    holder = spawn(tmp_path, "run-A", ["a", "b"])
    assert holder.verdict()["verdict"] == "admitted"

    contender = spawn(tmp_path, "run-C", ["c"])
    verdict = contender.verdict()

    assert verdict["verdict"] == "admitted"
    assert verdict["datasets"] == ["c"]
    assert holder.proc.poll() is None, "both runs must hold at the same time"


def test_gate_sigkilled_holder_is_reclaimed_and_recorded(tmp_path, spawn):
    """D5: a ``SIGKILL``ed run never wedges the factory. The kernel drops its flock; the
    surviving sidecar is reclaimed and RECORDED (never lock-breaking)."""
    holder = spawn(tmp_path, "run-A", ["a"])
    assert holder.verdict()["verdict"] == "admitted"
    sidecar = tmp_path / "a.holder.json"
    assert sidecar.is_file()

    holder.proc.kill()
    holder.proc.wait(timeout=_CHILD_TIMEOUT)
    assert sidecar.is_file(), "the holder record must survive the kill (that is the point)"

    successor = spawn(tmp_path, "run-D", ["a"])
    verdict = successor.verdict()

    assert verdict["verdict"] == "admitted"
    assert verdict["reclaimed"] == ["a"]
    assert json.loads(sidecar.read_text())["run_id"] == "run-D"


def test_gate_release_then_readmit_across_processes(tmp_path, spawn):
    holder = spawn(tmp_path, "run-A", ["a"])
    assert holder.verdict()["verdict"] == "admitted"
    holder.tell_to_release()
    assert holder.verdict()["verdict"] == "released"

    successor = spawn(tmp_path, "run-E", ["a"])
    verdict = successor.verdict()

    assert verdict["verdict"] == "admitted"
    assert verdict["reclaimed"] == [], "a clean release is not a reclaim"


def test_gate_opt_in_wait_admits_only_after_the_holder_actually_releases(tmp_path, spawn):
    """AC D3, second half: the opt-in wait is a REAL wait — the contender blocks on a lock it
    cannot take and is admitted only once the holder lets go.

    The PARENT holds the ticket, so the contention window is already open when the child is
    spawned; the child announces readiness on stderr once kedro is imported, and must then
    stay SILENT for the whole time the parent keeps holding. That silence is the proof: with
    the wait disabled the child prints ``rejected`` milliseconds after the handshake.

    (The version this replaces spawned a 0.3s holder, then a waiter, and asserted
    ``elapsed >= 0.2`` — a bar the waiter's own interpreter + kedro import cleared on its
    own. It passed with ``wait_seconds=0.0``, i.e. with the feature switched off.)
    """
    held = acquire(["a"], run_id="run-holder", lock_root=tmp_path)
    try:
        spawned_at = time.monotonic()
        waiter = spawn(tmp_path, "run-F", ["a"], wait_seconds=30.0)
        waiter.wait_until_ready()
        early = waiter.poll_verdict(_BLOCKED_WINDOW)
        assert early is None, f"the waiter never blocked on the held lock: {early}"
        # ...and it was SILENT because it was blocking, not because it had died. Without this
        # the assertion above passes for a child that crashed after the handshake, and the
        # real failure surfaces `_CHILD_TIMEOUT` later as an unrelated-looking timeout.
        assert waiter.proc.poll() is None, (
            f"the waiter exited instead of blocking (rc={waiter.proc.returncode}); "
            f"stderr:\n{waiter._stderr_text()}"
        )
    finally:
        released_at = time.monotonic()
        release(held)

    verdict = waiter.verdict()

    assert verdict["verdict"] == "admitted"
    assert verdict["datasets"] == ["a"]
    assert verdict["reclaimed"] == [], "a live holder that releases cleanly is not a reclaim"
    # `_BLOCKED_WINDOW` of proven silence, then admission only after the release. (There used
    # to be an `admitted_at > released_at > spawned_at + _BLOCKED_WINDOW` line here; it read
    # as independent corroboration but was true by construction — `released_at` is sampled
    # after a mandatory blocking poll, and monotonic time supplies the rest.)
    assert released_at - spawned_at >= _BLOCKED_WINDOW


def test_gate_opt_in_wait_rejects_when_the_deadline_expires(tmp_path, spawn):
    holder = spawn(tmp_path, "run-A", ["a"])
    assert holder.verdict()["verdict"] == "admitted"

    wait = 1.0
    started = time.monotonic()
    waiter = spawn(tmp_path, "run-G", ["a"], wait_seconds=wait)
    verdict = waiter.verdict()
    elapsed = time.monotonic() - started

    assert verdict["verdict"] == "rejected"
    assert verdict["conflicting"] == "a"
    assert verdict["holder_run_id"] == "run-A"
    # It must reject BECAUSE THE DEADLINE PASSED, not merely reject. Without this the test
    # was vacuous: a mutant that ignores `wait_seconds` entirely and always rejects fast
    # produced the identical three assertions above (the same defect class review passes 2
    # and 3 each removed from a different wait test). Verified RED under that mutation.
    assert elapsed >= wait, (
        f"rejected after {elapsed:.3f}s — the {wait}s deadline was never waited out, so "
        f"reject-fast is indistinguishable from the opt-in wait"
    )


def test_gate_partial_overlap_rejects_and_leaves_the_uncontended_lock_free(tmp_path, spawn):
    """A holds ``{b}``; B requests ``{a, b}`` → B takes ``a``, hits ``b``, rolls ``a`` back."""
    holder = spawn(tmp_path, "run-A", ["b"])
    assert holder.verdict()["verdict"] == "admitted"

    contender = spawn(tmp_path, "run-H", ["a", "b"])
    verdict = contender.verdict()

    # assert BEFORE reaping: a contender that was wrongly ADMITTED holds its locks until
    # told to release, so waiting on it first would turn a clean assertion failure into a
    # 45s timeout (observed while running the mutation check).
    assert verdict["verdict"] == "rejected"
    assert verdict["conflicting"] == "b"
    contender.proc.wait(timeout=_CHILD_TIMEOUT)
    assert _is_free(tmp_path, "a"), "a rejected run must leave no trail of held locks"


def test_gate_a_rejected_run_leaves_no_holder_record_to_be_mistaken_for_a_corpse(
    tmp_path, spawn, caplog
):
    """Rollback must remove the SIDECARS the failed attempt wrote, not just its locks.

    A run rejected at dataset k has already written ``k-1`` holder records naming ITSELF.
    Once its process exits those records describe a dead pid, so the next acquirer of any of
    them fires the D5 ``reclaimed`` WARNING — the operator's one signal that a run was
    SIGKILLed. A ``kedro run`` of ``__default__`` (46 outputs) rejected late would fire it
    dozens of times for an entirely orderly rejection: that is how a real signal becomes
    noise.
    """
    holder = spawn(tmp_path, "run-A", ["b"])
    assert holder.verdict()["verdict"] == "admitted"

    contender = spawn(tmp_path, "run-R", ["a", "b"])
    assert contender.verdict()["verdict"] == "rejected"
    contender.proc.wait(timeout=_CHILD_TIMEOUT)  # its pid now reads as dead

    assert not (tmp_path / "a.holder.json").exists(), "rollback left a self-named record"

    with caplog.at_level("WARNING", logger=admission.logger.name):
        successor = acquire(["a"], run_id="run-next", lock_root=tmp_path)
    try:
        assert successor.reclaimed == (), "an orderly rejection was reported as a corpse"
        assert "reclaimed" not in caplog.text
    finally:
        release(successor)


def test_the_harness_fails_fast_when_a_child_hangs(tmp_path):
    """The gate must never wedge an unattended run: a bounded read, not ``readline()``."""
    stderr_file = (tmp_path / "hang.stderr").open("w")
    proc = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(600)"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=stderr_file, text=True,
    )
    child = _Child(proc, tmp_path / "hang.stderr", stderr_file)
    try:
        started = time.monotonic()
        with pytest.raises(AssertionError, match="no verdict within"):
            child.verdict(timeout=1.0)
        assert time.monotonic() - started < 30.0
    finally:
        child.kill()
        child.close()


def test_the_harness_survives_a_child_that_floods_stderr(tmp_path):
    """>64 KiB on stderr would deadlock a parent blocked on stdout if stderr were an
    undrained pipe. It is a file, so it cannot."""
    program = (
        "import sys; sys.stderr.write('x' * 512 * 1024); sys.stderr.flush();"
        "print('{\"verdict\": \"admitted\"}', flush=True)"
    )
    stderr_file = (tmp_path / "flood.stderr").open("w")
    proc = subprocess.Popen(
        [sys.executable, "-c", program],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=stderr_file, text=True,
    )
    child = _Child(proc, tmp_path / "flood.stderr", stderr_file)
    try:
        assert child.verdict(timeout=30.0)["verdict"] == "admitted"
    finally:
        child.kill()
        child.close()


# --------------------------------------------------------------------------- #
# I/O matrix — single-process units
# --------------------------------------------------------------------------- #


def test_uncontended_run_takes_every_lock_in_order_and_releases(tmp_path):
    ticket = acquire(["b", "a"], run_id="r1", lock_root=tmp_path)

    assert ticket.datasets == ("a", "b")
    assert ticket.reclaimed == ()
    for name in ("a", "b"):
        assert (tmp_path / f"{name}.lock").is_file()
        record = json.loads((tmp_path / f"{name}.holder.json").read_text())
        assert record == {"run_id": "r1", "pid": os.getpid(), "started_at": record["started_at"]}
        assert not _is_free(tmp_path, name)

    release(ticket)

    for name in ("a", "b"):
        assert _is_free(tmp_path, name)
        assert not (tmp_path / f"{name}.holder.json").exists()


def test_same_process_second_acquire_of_the_same_set_is_rejected(tmp_path):
    """Two distinct FileLock objects on one path conflict even inside ONE process (separate
    open file descriptions), so a long-lived MCP server cannot double-admit itself."""
    held = acquire(["a"], run_id="r1", lock_root=tmp_path)
    try:
        with pytest.raises(RunAdmissionRejected) as excinfo:
            acquire(["a"], run_id="r2", lock_root=tmp_path)
    finally:
        release(held)
    assert excinfo.value.conflicting == "a"
    assert excinfo.value.holder_run_id == "r1"
    assert excinfo.value.holder_pid == os.getpid()


def test_disjoint_sets_do_not_contend(tmp_path):
    first = acquire(["a", "b"], run_id="r1", lock_root=tmp_path)
    second = acquire(["c"], run_id="r2", lock_root=tmp_path)
    try:
        assert second.datasets == ("c",)
    finally:
        release(first)
        release(second)


def test_a_pipeline_with_no_outputs_is_admitted_with_no_lock_files(tmp_path):
    ticket = acquire([], run_id="r1", lock_root=tmp_path)

    assert ticket.datasets == ()
    assert ticket.locks == ()
    assert list(tmp_path.iterdir()) == []
    release(ticket)  # a no-op, never an error


def test_wait_seconds_is_validated_before_the_empty_set_early_return(tmp_path):
    """The check must not depend on which path you enter."""
    with pytest.raises(AdmissionConfigError):
        acquire([], run_id="r1", lock_root=tmp_path, wait_seconds="soon")


@pytest.mark.parametrize(
    "bad", ["soon", -1, float("inf"), float("nan"), 10**400, None, True, object()]
)
def test_invalid_wait_value_raises_the_typed_config_error(tmp_path, bad):
    """Never silently falls back to reject-fast or to an unbounded wait. ``10**400`` is the
    ``OverflowError`` path and ``True`` the bool-is-an-int path — both must stay typed."""
    with pytest.raises(AdmissionConfigError):
        acquire(["a"], run_id="r1", lock_root=tmp_path, wait_seconds=bad)
    assert list(tmp_path.iterdir()) == [], "a config error must take no locks"


def test_a_bare_string_dataset_argument_is_refused(tmp_path):
    """Iterating a ``str`` would lock it character by character."""
    with pytest.raises(AdmissionConfigError, match="bare str"):
        acquire("abc", run_id="r1", lock_root=tmp_path)


def test_transcoded_names_collapse_to_one_lock(tmp_path):
    ticket = acquire(["ds@pandas", "ds@spark"], run_id="r1", lock_root=tmp_path)
    try:
        assert ticket.datasets == ("ds",)
    finally:
        release(ticket)


@pytest.mark.parametrize("payload", ["", "{not json", "[]", '{"run_id": null, "pid": "x"}'])
def test_a_corrupt_or_missing_holder_record_still_rejects_cleanly(tmp_path, payload):
    """Never a ``JSONDecodeError`` — the unknown fields report as ``None``."""
    held = acquire(["a"], run_id="r1", lock_root=tmp_path)
    (tmp_path / "a.holder.json").write_text(payload, encoding="utf-8")
    try:
        with pytest.raises(RunAdmissionRejected) as excinfo:
            acquire(["a"], run_id="r2", lock_root=tmp_path)
    finally:
        release(held)
    assert excinfo.value.conflicting == "a"
    assert excinfo.value.holder_run_id is None
    assert excinfo.value.holder_pid is None
    assert excinfo.value.held_since is None
    assert "unknown" in str(excinfo.value)


def test_a_missing_holder_record_still_rejects_cleanly(tmp_path):
    held = acquire(["a"], run_id="r1", lock_root=tmp_path)
    (tmp_path / "a.holder.json").unlink()
    try:
        with pytest.raises(RunAdmissionRejected) as excinfo:
            acquire(["a"], run_id="r2", lock_root=tmp_path)
    finally:
        release(held)
    assert excinfo.value.holder_run_id is None


def test_the_opt_in_wait_is_one_deadline_shared_across_all_locks(tmp_path):
    """Not ``wait_seconds`` per lock, which would multiply the caller's budget by the
    dataset count.

    The contender must actually REACH a second lock for the distinction to exist. The version
    this replaces held ``{a, b, c}`` and asked for ``{a, b, c}``: ``a`` is first in sorted
    order and was already held, so the contender timed out on lock #1 and never got to #2 —
    measured, a per-lock-deadline mutant of :func:`acquire` finished in 0.504s against the
    shipped 0.505s and cleared the same ``< 1.4`` bar. The property was unproven while three
    artifacts asserted it.

    So: hold ``a`` and ``b`` as SEPARATE tickets, hand ``a`` back part-way through the budget,
    and keep ``b``. The contender now spends ~``FREE_AT`` on ``a`` and must reject on ``b``
    when the ONE shared deadline expires at ~``BUDGET``. A per-lock mutant would restart the
    clock at ``b`` and only reject at ~``FREE_AT + BUDGET``.
    """
    # Widened from (1.0, 0.4): the upper bound below left ~150 ms of slack on an unattended,
    # possibly loaded runner, which is a flake waiting to happen. The property is a RATIO, so
    # scaling both keeps the discrimination identical while tripling the margin.
    budget, free_at = 3.0, 1.2
    first = acquire(["a"], run_id="holder-a", lock_root=tmp_path)
    second = acquire(["b"], run_id="holder-b", lock_root=tmp_path)
    releaser = threading.Timer(free_at, release, args=(first,))
    releaser.start()
    started = time.monotonic()
    try:
        with pytest.raises(RunAdmissionRejected) as excinfo:
            acquire(["a", "b"], run_id="r2", lock_root=tmp_path, wait_seconds=budget)
        elapsed = time.monotonic() - started
    finally:
        releaser.cancel()
        releaser.join(timeout=10.0)
        release(second)

    assert excinfo.value.conflicting == "b", "the contender never got past the freed lock"
    # It waited out the whole shared budget...
    assert elapsed >= budget * 0.9, f"rejected early at {elapsed:.3f}s"
    # ...and did NOT restart the clock at `b` (which would land near free_at + budget).
    assert elapsed < free_at + budget * 0.8, (
        f"the deadline was applied per lock, not once: {elapsed:.3f}s"
    )
    assert _is_free(tmp_path, "a"), "the rolled-back lock was left held"


def test_release_without_acquire_is_a_no_op(tmp_path):
    hooks = RunAdmissionHooks(lock_root=tmp_path)
    hooks.after_pipeline_run(run_params={"run_id": "never-started"}, pipeline=_pipeline("a"))
    hooks.on_pipeline_error(
        run_params={"run_id": "never-started"},
        pipeline=_pipeline("a"),
    )
    assert _is_free(tmp_path, "a")


# --------------------------------------------------------------------------- #
# Correctness requirements found by review pass 1
# --------------------------------------------------------------------------- #


def test_locks_are_not_thread_local_so_a_cross_thread_release_really_releases(tmp_path):
    """filelock's default is ``thread_local=True``, under which a release from a different
    thread than the acquirer is a SILENT NO-OP: the handle is popped and the sidecar
    unlinked while the flock stays held for the process lifetime, reporting
    ``run None (pid None)`` — unreclaimable. Reproduced before the fix."""
    ticket = acquire(["a"], run_id="r1", lock_root=tmp_path)
    worker = threading.Thread(target=release, args=(ticket,))
    worker.start()
    worker.join(timeout=10.0)

    assert not worker.is_alive()
    assert _is_free(tmp_path, "a")
    successor = acquire(["a"], run_id="r2", lock_root=tmp_path)
    release(successor)


def test_any_exception_inside_acquire_rolls_back_the_locks_already_taken(monkeypatch, tmp_path):
    """Not just ``filelock.Timeout``: an ``OSError`` from the sidecar write (ENOSPC, EACCES,
    EROFS) is precisely the failure with no recovery path."""
    real_write = admission._write_holder

    def boom(path, run_id):
        if path.name.startswith("b"):
            raise OSError(28, "No space left on device")
        return real_write(path, run_id)

    monkeypatch.setattr(admission, "_write_holder", boom)

    with pytest.raises(OSError):
        acquire(["a", "b"], run_id="r1", lock_root=tmp_path)

    assert _is_free(tmp_path, "a"), "the k-1 locks already held were stranded"
    assert _is_free(tmp_path, "b")


def test_a_torn_holder_record_is_rolled_back_too(monkeypatch, tmp_path):
    """``written`` is appended to BEFORE the write, not after: a sidecar write that fails
    part-way must still be unlinked by the rollback, or the failed run leaves a self-named
    corpse on a lock nobody holds — the same false-reclaim noise the rollback was added to
    remove. (Review pass 4 also made ``_write_holder`` itself atomic, so it no longer AUTHORS
    a torn record; this test injects the failure at that boundary, so it pins the rollback's
    ordering independently of how the write is implemented.)"""
    real_write = admission._write_holder

    def torn(path, run_id):
        if path.name.startswith("b"):
            path.write_text('{"run_id": "r1", "pi', encoding="utf-8")  # torn mid-write
            raise OSError(28, "No space left on device")
        return real_write(path, run_id)

    monkeypatch.setattr(admission, "_write_holder", torn)

    with pytest.raises(OSError):
        acquire(["a", "b"], run_id="r1", lock_root=tmp_path)

    assert not (tmp_path / "b.holder.json").exists(), "rollback left a torn record behind"
    assert not (tmp_path / "a.holder.json").exists()
    assert _is_free(tmp_path, "a") and _is_free(tmp_path, "b")


def test_the_holder_record_outlives_a_failed_release(tmp_path, caplog):
    """A lock that did NOT let go keeps its holder record.

    ``release()`` unlinks the sidecar first, so this is the one state that ordering risks: a
    still-held flock whose record is already gone reports ``run None (pid None)`` —
    unattributable and unreclaimable for the life of the process, the state correctness
    requirement 1 exists to prevent. It is repaired by re-writing the record whenever the
    release did not actually succeed.
    """
    ticket = acquire(["a"], run_id="r1", lock_root=tmp_path)

    class _Angry:
        lock_file = "angry"

        def release(self, force=False):
            raise OSError("cannot release")

    poisoned = AdmissionTicket(
        run_id="r1", datasets=("a",), locks=(_Angry(),), lock_root=ticket.lock_root
    )
    with caplog.at_level("WARNING", logger=admission.logger.name):
        release(poisoned)  # must not raise

    assert (tmp_path / "a.holder.json").is_file(), (
        "a lock that is still held must keep its holder record, or it is unattributable"
    )
    assert json.loads((tmp_path / "a.holder.json").read_text())["run_id"] == "r1"
    release(ticket)  # the real handle still lets go cleanly
    assert _is_free(tmp_path, "a")
    assert not (tmp_path / "a.holder.json").exists()


def test_release_does_not_abort_mid_loop_when_one_handle_raises(tmp_path):
    """A stuck handle must not strand the rest, and must never convert a successful run into
    a failure from ``after_pipeline_run``."""
    ticket = acquire(["a", "b"], run_id="r1", lock_root=tmp_path)

    class _Angry:
        lock_file = "angry"

        def release(self, force=False):
            raise OSError("cannot release")

    poisoned = AdmissionTicket(
        run_id=ticket.run_id,
        datasets=("a", "z", "b"),
        locks=(ticket.locks[0], _Angry(), ticket.locks[1]),
        lock_root=ticket.lock_root,
    )
    release(poisoned)  # must not raise

    assert _is_free(tmp_path, "a")
    assert _is_free(tmp_path, "b"), "the loop aborted at the raising handle"


def test_a_second_ticket_under_one_run_id_is_stacked_not_overwritten(tmp_path, caplog):
    """kedro-dagster reuses ONE run id (the build-time session id) for every job. Overwriting
    would orphan the first ticket's locks — or let run A's after-hook release run B's."""
    hooks = RunAdmissionHooks(lock_root=tmp_path)
    first, second = _pipeline("a"), _pipeline("b")
    run_params = {"run_id": "shared"}

    hooks.before_pipeline_run(run_params=run_params, pipeline=first)
    with caplog.at_level("WARNING", logger=admission.logger.name):
        hooks.before_pipeline_run(run_params=run_params, pipeline=second)

    assert "already has 1 outstanding ticket" in caplog.text, "the collision must be loud"
    assert len(hooks._tickets["shared"]) == 2
    assert not _is_free(tmp_path, "a") and not _is_free(tmp_path, "b")

    hooks.after_pipeline_run(run_params=run_params, pipeline=second)
    assert _is_free(tmp_path, "b")
    assert not _is_free(tmp_path, "a"), "the first ticket must not have been orphaned"
    hooks.after_pipeline_run(run_params=run_params, pipeline=first)
    assert _is_free(tmp_path, "a")


def test_tickets_pair_by_dataset_set_so_the_run_that_started_first_may_finish_first(tmp_path):
    """Correctness requirement 4 — the half a LIFO pop gets WRONG.

    The test above finishes the MOST RECENT pipeline, which a bare ``stack.pop()`` also gets
    right. Two jobs sharing one run id (kedro-dagster reuses the build-time session id for
    every job) have no such ordering: the one that started FIRST may finish first, and then
    popping the top releases the locks of the run that is still writing — the exact
    interleaving admission exists to prevent, re-introduced by the release path.
    """
    hooks = RunAdmissionHooks(lock_root=tmp_path)
    first, second = _pipeline("a"), _pipeline("b")
    run_params = {"run_id": "shared"}

    hooks.before_pipeline_run(run_params=run_params, pipeline=first)
    hooks.before_pipeline_run(run_params=run_params, pipeline=second)

    hooks.after_pipeline_run(run_params=run_params, pipeline=first)

    assert _is_free(tmp_path, "a"), "the finishing pipeline's own lock was not released"
    assert not _is_free(tmp_path, "b"), "a LIFO pop freed the run that is still writing"
    assert not (tmp_path / "a.holder.json").exists()
    assert (tmp_path / "b.holder.json").is_file(), "the live run lost its holder record"

    hooks.after_pipeline_run(run_params=run_params, pipeline=second)
    assert _is_free(tmp_path, "b")


def test_an_ambiguous_no_match_release_frees_nothing_rather_than_guessing(tmp_path, caplog):
    """The no-match fallback used to release ``stack[-1]`` — the bare LIFO pop the block five
    lines above it forbids by name, and which
    ``test_tickets_pair_by_dataset_set_...`` exists to prove wrong.

    With two runs outstanding under one ``run_id`` and a finishing pipeline matching neither,
    there is NO evidence about which ticket is finishing. Guessing frees a run that is still
    writing — the exact interleaving admission exists to prevent, re-introduced by the release
    path. Holding both is the safe answer: process exit still frees them, and no second writer
    is admitted meanwhile.
    """
    hooks = RunAdmissionHooks(lock_root=tmp_path)
    run_params = {"run_id": "shared"}
    hooks.before_pipeline_run(run_params=run_params, pipeline=_pipeline("a"))
    hooks.before_pipeline_run(run_params=run_params, pipeline=_pipeline("b"))

    with caplog.at_level("ERROR", logger=admission.logger.name):
        hooks.after_pipeline_run(run_params=run_params, pipeline=_pipeline("zzz"))

    assert "releasing NOTHING" in caplog.text, "an ambiguous release must be loud"
    assert not _is_free(tmp_path, "a"), "a LIFO guess freed a run that is still writing"
    assert not _is_free(tmp_path, "b")
    assert len(hooks._tickets["shared"]) == 2, "no ticket may be dropped either"

    hooks.after_pipeline_run(run_params=run_params, pipeline=_pipeline("a"))
    hooks.after_pipeline_run(run_params=run_params, pipeline=_pipeline("b"))
    assert _is_free(tmp_path, "a") and _is_free(tmp_path, "b")


def test_a_single_outstanding_ticket_is_still_released_on_a_no_match(tmp_path, caplog):
    """With exactly ONE ticket there is no ambiguity to protect against, and refusing would
    strand the common case (a pipeline object that differs between the before- and after-hook)
    for no gain."""
    hooks = RunAdmissionHooks(lock_root=tmp_path)
    run_params = {"run_id": "solo"}
    hooks.before_pipeline_run(run_params=run_params, pipeline=_pipeline("a"))

    with caplog.at_level("WARNING", logger=admission.logger.name):
        hooks.after_pipeline_run(run_params=run_params, pipeline=_pipeline("zzz"))

    assert "no other candidate" in caplog.text
    assert _is_free(tmp_path, "a")
    assert hooks._tickets == {}


def test_the_ticket_registry_does_not_grow_one_dead_key_per_run(tmp_path):
    """The MCP server is long-lived and dispatches every ``run_*`` tool through ONE hook
    instance, so a registry that keeps an empty stack per finished run leaks a key per run
    for the life of the process."""
    hooks = RunAdmissionHooks(lock_root=tmp_path)
    for index in range(3):
        run_params = {"run_id": f"run-{index}"}
        hooks.before_pipeline_run(run_params=run_params, pipeline=_pipeline("a"))
        hooks.after_pipeline_run(run_params=run_params, pipeline=_pipeline("a"))
    assert hooks._tickets == {}, f"leaked run ids: {sorted(hooks._tickets)}"

    # ...and the key must survive while the run still holds something.
    run_params = {"run_id": "shared"}
    hooks.before_pipeline_run(run_params=run_params, pipeline=_pipeline("a"))
    hooks.before_pipeline_run(run_params=run_params, pipeline=_pipeline("b"))
    hooks.after_pipeline_run(run_params=run_params, pipeline=_pipeline("a"))
    assert list(hooks._tickets) == ["shared"], "dropped a key that still holds a lock"

    hooks.on_pipeline_error(run_params=run_params, pipeline=_pipeline("b"),
    )
    assert hooks._tickets == {}
    assert _is_free(tmp_path, "a") and _is_free(tmp_path, "b")


def test_locks_never_silently_downgrade_to_a_soft_lock(tmp_path):
    """D5, the spine and SPEC.md all rest on one sentence: *the kernel drops the flock when
    its owner dies*. On a filesystem whose ``flock`` returns ``ENOSYS`` (9p, some FUSE/bind
    mounts) filelock 3.32 REWRITES ITS OWN CLASS to ``SoftFileLock`` behind a
    ``UserWarning``, moving mutual exclusion onto ``O_CREAT|O_EXCL`` and holder liveness onto
    a marker file. Relocating the store onto such a mount is a SUPPORTED override
    (``PYFORGE_ATLAS_DATA_ROOT``), so the downgrade must fail loudly rather than keep
    reporting success on a weaker primitive.
    """
    ticket = acquire(["a", "b"], run_id="r1", lock_root=tmp_path)
    try:
        assert len(ticket.locks) == 2
        for lock in ticket.locks:
            # `fallback_to_soft` is filelock's own public property (3.30+) — no internals.
            assert lock.fallback_to_soft is False, "an ENOSYS mount would downgrade silently"
            assert not isinstance(lock, filelock.SoftFileLock)
            # Platform-conditional: `win-64` is a declared workspace platform (root
            # pixi.toml), which is why `_pid_alive` is POSIX-gated at all. Asserting
            # `UnixFileLock` unconditionally would red this gate on the one platform the
            # module goes out of its way to support. The invariant is "a kernel lock, not
            # filelock's userspace marker-file emulation" — which is what both names mean.
            kernel_lock = filelock.UnixFileLock if os.name == "posix" else filelock.WindowsFileLock
            assert isinstance(lock, kernel_lock), "not a kernel-enforced lock"
    finally:
        release(ticket)


def test_pid_liveness_probe_is_posix_gated(monkeypatch):
    """``os.kill(pid, 0)`` calls ``TerminateProcess`` on Windows — a declared platform — so
    the probe would KILL the process it probes.

    The branch is flipped through ``admission._IS_POSIX``, NOT through ``admission.os.name``:
    ``admission.os`` *is* the stdlib module, so patching the name through it would tell every
    other library in the process it is running on Windows for the duration of this test.
    """
    def forbidden(*args, **kwargs):
        raise AssertionError("os.kill must never be called off POSIX")

    monkeypatch.setattr(admission, "_IS_POSIX", False)
    monkeypatch.setattr(admission.os, "kill", forbidden)

    assert admission._pid_alive(999_999) is True  # conservative: treat as alive


def test_a_pid_wider_than_a_c_int_does_not_crash_an_otherwise_successful_admission(tmp_path):
    """``os.kill(10**20, 0)`` raises ``OverflowError`` — neither ``OSError`` nor
    ``ValueError``, so it escaped ``_pid_alive`` and propagated.

    This is worse than the sibling ``held_since`` cases: they corrupt a REJECTION, whereas
    this fires on the success path, *after* the lock has been taken. The run would have died
    with an untyped ``OverflowError`` (rolled back, but never admitted) because a sidecar left
    by something else carried a garbage integer. Conservative answer: unreadable pid ⇒ treat
    the holder as alive ⇒ claim no reclaim.
    """
    (tmp_path / "a.holder.json").write_text(
        json.dumps({"run_id": "ghost", "pid": 10**20, "started_at": time.time()}),
        encoding="utf-8",
    )
    ticket = acquire(["a"], run_id="r1", lock_root=tmp_path)
    try:
        assert ticket.datasets == ("a",)
        assert ticket.reclaimed == (), "an unreadable pid is not evidence of a corpse"
    finally:
        release(ticket)


@pytest.mark.parametrize("pid", [0, -1, -12345])
def test_a_non_positive_pid_is_not_a_holder(tmp_path, pid, caplog):
    """``os.kill(0, 0)`` signals this process's whole group and ``os.kill(-1, 0)`` every
    process the caller may signal — both return cleanly, so a record naming no process at all
    would read as a live holder."""
    (tmp_path / "a.holder.json").write_text(
        json.dumps({"run_id": "ghost", "pid": pid, "started_at": time.time()}),
        encoding="utf-8",
    )
    with caplog.at_level("WARNING", logger=admission.logger.name):
        ticket = acquire(["a"], run_id="r1", lock_root=tmp_path)
    try:
        assert ticket.reclaimed == ()
        assert "reclaimed" not in caplog.text
    finally:
        release(ticket)


def test_pid_liveness_treats_a_permission_error_as_alive(monkeypatch):
    monkeypatch.setattr(admission, "_IS_POSIX", True)
    monkeypatch.setattr(
        admission.os, "kill", lambda *_: (_ for _ in ()).throw(PermissionError(1, "EPERM"))
    )

    assert admission._pid_alive(1) is True


def test_no_reclaim_is_claimed_without_a_pid_to_judge(tmp_path, caplog):
    """A holder record carrying a run id but no usable pid must not be logged as a SIGKILL
    reclaim — we cannot know."""
    (tmp_path).mkdir(parents=True, exist_ok=True)
    (tmp_path / "a.holder.json").write_text(
        json.dumps({"run_id": "ghost", "pid": None, "started_at": time.time()}),
        encoding="utf-8",
    )
    with caplog.at_level("WARNING", logger=admission.logger.name):
        ticket = acquire(["a"], run_id="r1", lock_root=tmp_path)
    try:
        assert ticket.reclaimed == ()
        assert "reclaimed" not in caplog.text
    finally:
        release(ticket)


def test_an_out_of_range_hold_start_does_not_break_the_rejection(tmp_path):
    """``time.gmtime()`` raises ``OverflowError``/``OSError`` on an out-of-range value, and a
    torn sidecar can carry one (correctness requirement 7)."""
    held = acquire(["a"], run_id="r1", lock_root=tmp_path)
    (tmp_path / "a.holder.json").write_text(
        json.dumps({"run_id": "r1", "pid": os.getpid(), "started_at": 1e300}), encoding="utf-8"
    )
    try:
        with pytest.raises(RunAdmissionRejected) as excinfo:
            acquire(["a"], run_id="r2", lock_root=tmp_path)
    finally:
        release(held)
    assert excinfo.value.held_since == 1e300
    assert "unparseable" in str(excinfo.value)


def test_an_integer_hold_start_wider_than_float_does_not_break_the_rejection(tmp_path):
    """The sibling case above only proves the FORMATTER is defensive: ``1e300`` is JSON
    *float* syntax, so ``float(started)`` is a no-op and it reaches ``_format_epoch``. A JSON
    *integer* of ~400 digits parses into a Python ``int`` instead, and ``float()`` on it
    raises ``OverflowError`` — neither ``OSError`` nor ``ValueError``, so it escaped
    ``_read_holder`` entirely and turned a clean rejection into an untyped crash
    (correctness requirement 7). The unknown field must degrade to ``None`` like every other.
    """
    held = acquire(["a"], run_id="r1", lock_root=tmp_path)
    (tmp_path / "a.holder.json").write_text(
        json.dumps({"run_id": "r1", "pid": os.getpid(), "started_at": 10**400}),
        encoding="utf-8",
    )
    try:
        with pytest.raises(RunAdmissionRejected) as excinfo:
            acquire(["a"], run_id="r2", lock_root=tmp_path)
    finally:
        release(held)
    assert excinfo.value.held_since is None
    assert excinfo.value.holder_run_id == "r1", "the readable fields must survive"
    assert excinfo.value.holder_pid == os.getpid()
    assert "held since unknown" in str(excinfo.value)


def test_the_rejection_message_is_honest_for_both_planes(tmp_path):
    """It used to advise ``--params admission_wait_seconds=…``, which is unreachable from
    MCP: all seven FastMCP tools call ``run_pipeline("<name>")`` with no params."""
    held = acquire(["a"], run_id="r1", lock_root=tmp_path)
    try:
        with pytest.raises(RunAdmissionRejected) as excinfo:
            acquire(["a"], run_id="r2", lock_root=tmp_path)
    finally:
        release(held)
    message = str(excinfo.value)
    assert "--params admission_wait_seconds=" in message
    # `mcp.tools.run_pipeline(name, extra_params=...)` DOES reach `runtime_params`
    # (`session.bootstrapped_session` -> `KedroSession.create(runtime_params=...)`), so the
    # message must not claim MCP has no params channel at all — only that the seven shipped
    # FastMCP wrappers hardcode none.
    assert "extra_params=" in message
    assert "FastMCP" in message and "retry once the holding run finishes" in message


def test_on_pipeline_error_releases_and_a_same_set_run_is_then_admitted(tmp_path):
    hooks = RunAdmissionHooks(lock_root=tmp_path)
    pipe, catalog = _pipeline("a", "b"), DataCatalog({})

    hooks.before_pipeline_run(run_params={"run_id": "r1"}, pipeline=pipe)
    hooks.on_pipeline_error(run_params={"run_id": "r1"}, pipeline=pipe)

    assert _is_free(tmp_path, "a") and _is_free(tmp_path, "b")
    hooks.before_pipeline_run(run_params={"run_id": "r2"}, pipeline=pipe)
    hooks.after_pipeline_run(run_params={"run_id": "r2"}, pipeline=pipe)


def test_a_real_runner_failure_releases_through_on_pipeline_error(tmp_path):
    """End to end through kedro's own hook manager + SequentialRunner: the run raises inside
    the runner, kedro fires ``on_pipeline_error``, the locks come back."""
    from kedro.io import MemoryDataset
    from kedro.runner import SequentialRunner

    def _explode(_):
        raise RuntimeError("node blew up")

    hooks = RunAdmissionHooks(lock_root=tmp_path)
    hook_manager = _create_hook_manager()
    hook_manager.register(hooks)
    pipe = Pipeline([node(_explode, "raw_in", "a", name="boom")])
    catalog = DataCatalog({"raw_in": MemoryDataset(1)})
    run_params = {"run_id": "r1"}

    hook_manager.hook.before_pipeline_run(run_params=run_params, pipeline=pipe, catalog=catalog)
    with pytest.raises(Exception):
        SequentialRunner().run(pipe, catalog, hook_manager=hook_manager)
    hook_manager.hook.on_pipeline_error(
        error=RuntimeError("node blew up"), run_params=run_params,
        pipeline=pipe, catalog=catalog,
    )

    assert _is_free(tmp_path, "a")


def test_the_runtime_param_is_the_live_wait_channel(tmp_path):
    """``settings.HOOKS`` constructs with no arguments, so ``kedro run --params
    admission_wait_seconds=…`` (i.e. ``run_params["runtime_params"]``) is how an operator
    turns the wait on."""
    hooks = RunAdmissionHooks(lock_root=tmp_path)
    held = acquire(["a"], run_id="holder", lock_root=tmp_path)
    started = time.monotonic()
    try:
        with pytest.raises(RunAdmissionRejected):
            hooks.before_pipeline_run(
                run_params={"run_id": "r1", "runtime_params": {"admission_wait_seconds": 0.4}},
                pipeline=_pipeline("a"),
            )
    finally:
        release(held)
    assert time.monotonic() - started >= 0.3, "the runtime param was not honored"


def test_an_invalid_runtime_param_refuses_the_run(tmp_path):
    hooks = RunAdmissionHooks(lock_root=tmp_path)
    with pytest.raises(AdmissionConfigError):
        hooks.before_pipeline_run(
            run_params={"run_id": "r1", "runtime_params": {"admission_wait_seconds": "soon"}},
            pipeline=_pipeline("a"),
        )


def test_filelock_is_declared_in_both_manifests():
    """AUD-ATLAS-010: an undeclared module-level import is a runtime dependency whether or
    not the manifest says so. ``filelock`` was in the env only TRANSITIVELY."""
    pyproject = (MEMBER_DIR / "pyproject.toml").read_text(encoding="utf-8")
    member_pixi = (MEMBER_DIR / "pixi.toml").read_text(encoding="utf-8")

    assert '"filelock>=3.32.0",' in pyproject
    assert 'filelock = ">=3.32.0"' in member_pixi


def test_the_in_process_executor_coupling_is_recorded_in_dagster_yml():
    """Acquisition happens inside an op; under a multiprocess executor that op's subprocess
    exits and the kernel drops the lock before the first node runs (``DW-AD23-2``).

    Asserts the CONFIGURED EXECUTOR, not the presence of the warning that describes it. The
    string checks alone were vacuous: both ``admission`` and ``in_process`` appear inside the
    warning comment, so flipping ``jobs.__default__.executor`` to ``multiprocess`` — the one
    change the whole comment forbids, and the one that silently voids admission on this
    plane — left them satisfied and the gate green.
    """
    import yaml

    text = (MEMBER_DIR / "conf" / "base" / "dagster.yml").read_text(encoding="utf-8")
    cfg = yaml.safe_load(text)

    assert "admission" in text.lower(), "the coupling must stay documented in the file"
    for job_name, job in (cfg.get("jobs") or {}).items():
        assert job.get("executor") == "in_process", (
            f"job {job_name!r} uses executor {job.get('executor')!r}; admission is acquired "
            f"inside an op, so any out-of-process executor drops the lock before the first "
            f"node runs (DW-AD23-2)"
        )
    assert "in_process" in (cfg.get("executors") or {})


# --------------------------------------------------------------------------- #
# Review pass 4 — what three passes of a green gate did not cover
# --------------------------------------------------------------------------- #


def test_the_holder_record_is_removed_before_the_lock_is_dropped(tmp_path):
    """Ordering pin. Releasing the flock FIRST and unlinking after was measured to delete the
    SUCCESSOR's record: a contender can win the lock and write its own sidecar inside that
    gap, and the departing run then unlinks the live holder's file — after which a third
    contender's rejection reports ``run None (pid None)`` and a later ``SIGKILL`` of that
    holder produces no D5 reclaim WARNING. Unlinking while we still hold the lock closes it,
    because nobody else can be the holder yet."""
    ticket = acquire(["d"], run_id="run-A", lock_root=tmp_path)
    holder = tmp_path / "d.holder.json"
    assert holder.is_file()

    class _Spy:
        def __init__(self, inner):
            self._inner = inner
            self.lock_file = inner.lock_file
            self.record_present_at_release = None

        def release(self, force=False):
            self.record_present_at_release = holder.exists()
            return self._inner.release(force=force)

    spy = _Spy(ticket.locks[0])
    release(
        AdmissionTicket(
            run_id="run-A", datasets=("d",), locks=(spy,), lock_root=ticket.lock_root
        )
    )

    assert spy.record_present_at_release is False, (
        "the sidecar was still on disk when the flock was dropped — a successor admitted in "
        "that window would have its own holder record unlinked by this run"
    )
    assert _is_free(tmp_path, "d")


def test_the_holder_record_is_replaced_atomically_not_truncated_in_place(tmp_path):
    """A contender reads this file WITHOUT holding the lock, and the write happens right
    after the winner takes the flock — i.e. exactly when a contender is reading. ``write_text``
    opens with ``O_TRUNC``, so that reader sees zero bytes and every diagnostic field the AC
    demands degrades to ``None``. An already-open reader is the deterministic probe: under
    ``os.replace`` it still sees the whole previous record; under truncate-in-place it sees a
    torn one."""
    path = tmp_path / "d.holder.json"
    admission._write_holder(path, "run-first")

    reader = path.open("r", encoding="utf-8")  # a contender, mid-flight
    try:
        admission._write_holder(path, "run-second")
        assert json.loads(reader.read())["run_id"] == "run-first", (
            "the in-flight reader saw a torn record — the write truncated in place"
        )
    finally:
        reader.close()

    assert json.loads(path.read_text(encoding="utf-8"))["run_id"] == "run-second"
    assert not list(tmp_path.glob("*.tmp")), "the temp file was left behind"


def test_an_absolute_lock_root_env_var_needs_no_derivable_project_root(monkeypatch, tmp_path):
    """Installed from the built ``.conda`` artifact, ``_PROJECT_ROOT`` lands in
    ``site-packages`` and the guard refuses to guess — while its own message names an absolute
    ``PYFORGE_ATLAS_LOCK_ROOT`` as the remedy. Resolving the base BEFORE reading the env made
    that remedy unreachable: the guard fired before the override was ever read."""
    monkeypatch.setattr(admission, "_PROJECT_ROOT", tmp_path / "site-packages" / "pyforge")
    monkeypatch.setenv("PYFORGE_ATLAS_LOCK_ROOT", str(tmp_path / "elsewhere"))
    monkeypatch.delenv("PYFORGE_ATLAS_DATA_ROOT", raising=False)

    assert default_lock_root() == (tmp_path / "elsewhere" / ".locks").resolve()


def test_the_derived_project_root_is_refused_when_it_is_not_a_kedro_project(
    monkeypatch, tmp_path
):
    """The other half of the same guard: with no absolute override there IS no anchor, and
    guessing would anchor the locks away from the Parquet they guard — the defect the first
    implementation of this story shipped and was reverted for."""
    monkeypatch.setattr(admission, "_PROJECT_ROOT", tmp_path / "site-packages" / "pyforge")
    monkeypatch.delenv("PYFORGE_ATLAS_LOCK_ROOT", raising=False)
    monkeypatch.delenv("PYFORGE_ATLAS_DATA_ROOT", raising=False)

    with pytest.raises(AdmissionConfigError, match="cannot locate the Kedro project root"):
        default_lock_root()


def test_a_non_iterable_datasets_argument_is_refused(tmp_path):
    """The other half of correctness requirement 7's input guard: only the bare-``str`` case
    was covered."""
    with pytest.raises(AdmissionConfigError, match="not iterable"):
        acquire(123, run_id="r1", lock_root=tmp_path)


@pytest.mark.parametrize("name", ["../escaped", "sub/dir", "", ".", ".."])
def test_a_dataset_name_that_cannot_be_a_lock_identity_is_refused(tmp_path, name):
    """Every name becomes ``<lock_root>/<name>.lock``. Measured before the guard:
    ``acquire(["../escaped"])`` created the lock file OUTSIDE the lock root, where no other
    process anchored to that root will ever contend with it — admission silently off for that
    dataset."""
    with pytest.raises(AdmissionConfigError, match="not a safe lock identity"):
        acquire([name], run_id="r1", lock_root=tmp_path)
    assert not list(tmp_path.parent.glob("escaped.lock"))


def test_the_hooks_declare_only_the_arguments_they_read(tmp_path):
    """pluggy's missing-argument check is per-IMPL, so every argument an impl NAMES is one a
    caller must supply or that impl raises ``HookCallError`` — and under ``tryfirst`` this
    impl is asked first, so it would be the raiser. Verified before the fix: an
    ``after_pipeline_run`` call without ``catalog`` raised from admission itself, left the
    ticket outstanding and left the flock held. kedro and kedro-dagster both pass ``catalog``
    today; declaring an argument this module never reads stakes the release path on that."""
    import inspect

    for name in ("before_pipeline_run", "after_pipeline_run", "on_pipeline_error"):
        params = set(inspect.signature(getattr(RunAdmissionHooks, name)).parameters) - {"self"}
        assert params == {"run_params", "pipeline"}, f"{name} declares {params}"

    hooks = RunAdmissionHooks(lock_root=tmp_path)
    hook_manager = _create_hook_manager()
    hook_manager.register(hooks)
    pipe, run_params = _pipeline("a"), {"run_id": "r1"}

    # Every call shape below omits at least one hookspec argument.
    hook_manager.hook.before_pipeline_run(run_params=run_params, pipeline=pipe)
    assert not _is_free(tmp_path, "a")
    hook_manager.hook.after_pipeline_run(run_params=run_params, pipeline=pipe, run_result={})
    assert _is_free(tmp_path, "a"), "a HookCallError from our own impl stranded the lock"

    hook_manager.hook.before_pipeline_run(run_params=run_params, pipeline=pipe)
    hook_manager.hook.on_pipeline_error(run_params=run_params, pipeline=pipe)
    assert _is_free(tmp_path, "a")


def test_a_release_with_no_usable_pipeline_and_two_tickets_frees_nothing(tmp_path, caplog):
    """The ambiguity guard covered the no-MATCH case but not the no-PIPELINE one, so
    ``_release_for(run_params, None)`` fell through to the bare LIFO pop the same function
    forbids by name — freeing a run that is still writing. Measured: with ``{x}`` and ``{y}``
    outstanding under one run id, ``y`` was released."""
    hooks = RunAdmissionHooks(lock_root=tmp_path)
    run_params = {"run_id": "shared"}
    hooks.before_pipeline_run(run_params=run_params, pipeline=_pipeline("x"))
    hooks.before_pipeline_run(run_params=run_params, pipeline=_pipeline("y"))

    with caplog.at_level("ERROR", logger=admission.logger.name):
        hooks._release_for(run_params, None)

    assert "releasing NOTHING" in caplog.text
    assert not _is_free(tmp_path, "x") and not _is_free(tmp_path, "y")
    assert len(hooks._tickets["shared"]) == 2

    hooks.after_pipeline_run(run_params=run_params, pipeline=_pipeline("x"))
    hooks.after_pipeline_run(run_params=run_params, pipeline=_pipeline("y"))
    assert _is_free(tmp_path, "x") and _is_free(tmp_path, "y")


def test_a_pipeline_whose_outputs_cannot_be_read_does_not_fail_a_successful_run(tmp_path):
    """``release()`` promises never to raise, but ``_release_for`` computed
    ``_lock_names(pipeline.all_outputs())`` outside every guard — and kedro calls
    ``after_pipeline_run`` OUTSIDE its ``try``. So an ``AdmissionConfigError`` or an
    ``AttributeError`` there failed a run whose nodes had all SUCCEEDED, and stranded the
    ticket on the way out."""

    class _Broken:
        def all_outputs(self):
            raise AttributeError("no outputs here")

    hooks = RunAdmissionHooks(lock_root=tmp_path)
    run_params = {"run_id": "solo"}
    hooks.before_pipeline_run(run_params=run_params, pipeline=_pipeline("a"))

    hooks.after_pipeline_run(run_params=run_params, pipeline=_Broken())  # must not raise

    assert _is_free(tmp_path, "a"), "the single unambiguous ticket must still be released"
    assert hooks._tickets == {}
