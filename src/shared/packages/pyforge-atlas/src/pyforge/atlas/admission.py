"""Cross-run admission control (Story 10.6, AD-23, audit ``AUD-ATLAS-046``).

This module is the **single admission seam**. AD-23's rule — *a dataset has one writing
run at a time* — was asserted by the spine and by
``orchestration/definitions.py`` for months while **nothing implemented it**
(``AUD-ATLAS-046``; the claim was retracted and AD-23 DEMOTED on 2026-07-27). The
``in_process`` Dagster executor serializes ops *within* one run and gives no cross-run or
cross-process admission at all, so two MCP ``run_*`` triggers — or an MCP trigger racing a
``kedro run`` — could interleave writes to the same Parquet file. This module builds the
property so the claim can be restored truthfully.

Mechanism
---------
:class:`RunAdmissionHooks` is registered ONCE in ``settings.HOOKS``, so every entry point
that dispatches through the kedro **hook manager** inherits admission: the CLI, the seven
MCP ``run_*`` tools, and the Dagster plane. ``before_pipeline_run`` takes one OS file lock
(``filelock``, ``fcntl.flock``) per dataset in ``pipeline.all_outputs()``, in ``sorted()``
order; ``after_pipeline_run`` AND ``on_pipeline_error`` both release. The default is
reject-fast with :class:`RunAdmissionRejected`; a bounded wait is opt-in via the
``admission_wait_seconds`` runtime param.

Granularity is the pipeline's declared OUTPUT dataset set (D4), never a single global lock:
``seed_gaps`` and ``vulnerability`` write disjoint sets and must still run concurrently.
Concretely that set is ``pipeline.all_outputs()`` — every node output, *including* in-run
intermediates, not the terminal-only ``outputs()``. That is a deliberate SUPERSET: catalog-
registered intermediates really are written to Parquet, and over-locking fails safe while
under-locking fails silently. Measured against the live project (46 outputs across the 7
pipelines, exactly one unregistered name, no name shared by two pipelines), it costs nothing
today. It is not free forever: if two pipelines ever adopt the same in-memory intermediate
name, they would reject each other despite writing disjoint FILES, which would contradict
D4's "disjoint outputs run concurrently". Narrow to catalog-persisted names at that point —
not before.

Boundaries — write them down rather than overclaim
--------------------------------------------------
* **Single machine.** ``flock`` is a kernel primitive on one host; NFS ``flock`` is
  unreliable. A multi-machine atlas re-opens the mechanism choice.
* **``RunAdmissionHooks`` runs FIRST — but only because it asks to.** Tuple order is NOT
  enough. ``KedroSession.__init__`` registers ``settings.HOOKS`` and *then*
  ``_register_hooks_entry_points(...)``, and pluggy dispatches LIFO — so an installed plugin
  (``kedro-viz`` is in this env) registers LATER and would therefore be dispatched EARLIER
  than anything in ``settings.HOOKS``. Measured: without an explicit marker the real session
  dispatched ``PipelineRunStatusHook`` (kedro-viz) ahead of this hook on all three of
  ``before_pipeline_run`` / ``after_pipeline_run`` / ``on_pipeline_error``. The three
  ``@hook_impl(tryfirst=True)`` markers below are what actually buy the ordering: pluggy puts
  ``tryfirst`` impls at the head of the call list, ahead of every plain ``@hook_impl``
  regardless of registration order. Do not remove them — the guarantee they buy is that the
  locks are taken before, and released before, any other implementation gets to run (and so
  before any other implementation gets to *raise*).
* **A raising hook on either side strands this run's locks.** Kedro calls BOTH
  ``before_pipeline_run`` and ``after_pipeline_run`` OUTSIDE its ``try`` (``session.py``):
  only exceptions from ``runner.run`` reach ``on_pipeline_error``. ``tryfirst`` means we have
  already acquired (resp. released) before any other impl runs, which closes the
  ``after_pipeline_run`` side entirely and narrows the ``before_pipeline_run`` side to "a
  hook that raises after we acquired but before the runner starts". In that window kedro
  fires NO error hook and this run's locks stay held until the process exits. For a
  ``kedro run`` that is immediate; for the long-lived MCP server it is not. Recorded, not
  "fixed": releasing another run's ticket would be actively wrong under a concurrently-serving
  process. Tracked as ``DW-AD23-2``.
* **Dagster-plane release is process-local.** kedro-dagster fires the hooks itself from a
  ``before_pipeline_run_hook_<job>`` op, and its after-op calls ``after_pipeline_run``
  without kedro's ``run_result`` argument. Ours declares only the subset it reads, so it
  releases; ``AtlasObservabilityHooks.after_pipeline_run`` still declares ``run_result`` and
  pluggy raises ``HookCallError`` from it — *after* our release has run. Tracked as
  ``DW-AD23-2`` (E2-owned).
* **A FAILED Dagster run releases nothing in-process.** kedro-dagster's after-op is SKIPPED
  when an upstream op fails, and it fires ``on_pipeline_error`` from a
  ``@dg.run_failure_sensor`` that executes in the Dagster DAEMON process — where
  ``_tickets`` is empty, so ``_release_for`` is a no-op. On that plane a failed run's locks
  are therefore freed only by the run worker's process exit. Survivable today only because
  Dagster launches run workers as separate short-lived processes — the same undeclared
  coupling as ``in_process``, and recorded in ``DW-AD23-2`` for the same reason.
* **The ``in_process`` executor is load-bearing on the Dagster plane.** Acquisition happens
  inside an op; under a multiprocess executor that op's subprocess exits immediately and the
  kernel drops the flock before the first node runs. ``conf/base/dagster.yml`` declares
  ``in_process`` and carries the same warning (``DW-AD23-2``).

Imports are stdlib + ``filelock`` + ``kedro.framework.hooks`` only — no ``pandas``, no
``dashboard.*``, no ``dagster``, and (the file is scanned by
``tests/catalog/test_no_inline_io.py``) never ``subprocess``: the lock must not shell out.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import filelock
from kedro.framework.hooks import hook_impl

logger = logging.getLogger(__name__)

# The kedro PROJECT root: src/pyforge/atlas/admission.py -> <member>/.
# Deliberately NOT the CWD, and deliberately not `dashboard.data.default_data_root()`
# (importing that would drag pandas + semantic.models into a module loaded on every
# `settings` import). See `default_lock_root` for why the anchor matters.
_PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Module-level indirection so a test can exercise the non-POSIX branch of `_pid_alive`
# WITHOUT monkeypatching `os.name` process-wide (`admission.os` IS the stdlib module, so
# patching through it changes `os.name` for everything running in that window).
_IS_POSIX = os.name == "posix"

# Runtime param that opts a run into a bounded wait instead of reject-fast (D3).
WAIT_PARAM = "admission_wait_seconds"

# Sidecar suffixes under the lock root.
_LOCK_SUFFIX = ".lock"
_HOLDER_SUFFIX = ".holder.json"


class AdmissionConfigError(ValueError):
    """A malformed admission configuration — raised BEFORE any lock is taken.

    Never silently falls back to reject-fast or to an unbounded wait: a run that asked for
    ``admission_wait_seconds="soon"`` gets a loud refusal, not a different policy than the
    one it requested.
    """


class RunAdmissionRejected(RuntimeError):
    """AD-23: the requested output dataset set is already held by another run.

    Carries the full diagnostic set the AC demands — which dataset conflicted, and who is
    holding it. Any field the holder record could not supply reports as ``None`` rather than
    raising: a torn or absent sidecar must still yield a readable rejection.
    """

    def __init__(
        self,
        datasets: tuple[str, ...],
        conflicting: str,
        holder_run_id: str | None = None,
        holder_pid: int | None = None,
        held_since: float | None = None,
    ) -> None:
        self.datasets = tuple(datasets)
        self.conflicting = conflicting
        self.holder_run_id = holder_run_id
        self.holder_pid = holder_pid
        self.held_since = held_since
        super().__init__(
            f"run admission rejected (AD-23): dataset {conflicting!r} is already being "
            f"written by run {holder_run_id!r} (pid {holder_pid}, held since "
            f"{_format_epoch(held_since)}). Requested output set: "
            f"{', '.join(self.datasets) or '<empty>'}. "
            f"To wait for the holder instead of rejecting, a `kedro run` can pass "
            f"`--params {WAIT_PARAM}=<seconds>`, and a caller of "
            f"`mcp.tools.run_pipeline` can pass `extra_params={{{WAIT_PARAM!r}: <seconds>}}` "
            f"(the seven FastMCP `run_*` tools currently hardcode no params, so from those "
            f"retry once the holding run finishes)."
        )


@dataclass
class AdmissionTicket:
    """The locks one admitted run holds. Returned by :func:`acquire`, consumed by
    :func:`release`.

    ``datasets`` and ``locks`` are parallel and in ``sorted()`` acquisition order.
    ``reclaimed`` names the datasets whose previous holder was found dead (D5) — recorded,
    never silent.
    """

    run_id: str
    datasets: tuple[str, ...] = ()
    reclaimed: tuple[str, ...] = ()
    locks: tuple[Any, ...] = ()
    lock_root: Path | None = None


def _format_epoch(value: float | None) -> str:
    """Render an epoch seconds value as UTC, defensively.

    ``time.gmtime`` raises ``OverflowError``/``OSError`` on an out-of-range value, and a
    torn sidecar can carry one. A rejection must never turn into a different exception on
    the way to being reported (correctness requirement 7)."""
    if value is None:
        return "unknown"
    try:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(value))
    except (OverflowError, OSError, ValueError):
        return f"unparseable({value!r})"


def default_lock_root(project_path: Any = None) -> Path:
    """The lock root, anchored to the kedro PROJECT ROOT — never to the CWD.

    This is the correctness core of the story. Kedro does **not** resolve catalog filepaths
    against the process CWD: ``KedroContext._get_catalog`` calls
    ``_convert_paths_to_absolute_posix(project_path=...)``, so every ``filepath`` in
    ``catalog.yml`` becomes absolute under the project root. Measured from ``/tmp``, the
    ``core_feedstock_health`` filepath still resolves to ``<member>/data/primary/...``.

    A CWD-relative lock root would therefore make two processes writing the *same* Parquet
    take locks in *different* directories and never contend — silently voiding admission.
    That is not hypothetical: the MCP server runs from wherever Claude Code launched it (the
    repo root) while the repo's own pixi tasks set ``cwd = src/shared/packages/pyforge-atlas``,
    i.e. exactly the flagship "MCP trigger racing a ``kedro run``" race.

    ``PYFORGE_ATLAS_LOCK_ROOT`` then ``PYFORGE_ATLAS_DATA_ROOT`` (the catalog's own
    ``globals.yml`` ``paths.data_root`` override) select the store; an ABSOLUTE value is
    honored verbatim, so relocating the store relocates the locks with it. An empty OR
    whitespace-only env var is treated as unset — deliberately STRICTER than
    ``settings._env_or``, which passes any truthy value through unstripped: ``export
    PYFORGE_ATLAS_DATA_ROOT="  "`` is a blanked override, and creating a store directory
    named after the spaces (one per typo) is not a behaviour worth mirroring.
    """
    base = _resolve_base(project_path)
    env = (
        (os.environ.get("PYFORGE_ATLAS_LOCK_ROOT") or "").strip()
        or (os.environ.get("PYFORGE_ATLAS_DATA_ROOT") or "").strip()
        or "data"
    )
    root = Path(env)
    return ((root if root.is_absolute() else base / root) / ".locks").resolve()


def _resolve_base(project_path: Any) -> Path:
    """The absolute project root a relative store path anchors to.

    Two guards, both against the SAME failure class the reverted first implementation shipped
    — a lock root that silently resolves somewhere the guarded Parquet is not:

    * A caller-supplied ``project_path`` must be absolute. Kedro always supplies an absolute
      ``run_params["project_path"]``, but a Dagster resource-config override or a direct
      ``acquire()`` caller could pass ``""`` or a relative string, which would quietly restore
      CWD-anchoring.
    * The ``__file__``-derived fallback is only trusted when it actually looks like this Kedro
      project (``conf/base/catalog.yml`` present), mirroring the assertion
      ``mcp/session.py`` makes about the identical derivation. Installed from the built
      ``.conda`` artifact, ``parents[3]`` would resolve into ``site-packages`` and admission
      would guard the wrong tree. Failing loudly beats guarding nothing.
    """
    if project_path is not None and str(project_path) != "":
        base = Path(project_path)
        if not base.is_absolute():
            raise AdmissionConfigError(
                f"project_path must be absolute so the lock root cannot become "
                f"CWD-relative; got {project_path!r}"
            )
        return base
    if not (_PROJECT_ROOT / "conf" / "base" / "catalog.yml").is_file():
        raise AdmissionConfigError(
            f"cannot locate the Kedro project root from {__file__!r} (derived "
            f"{str(_PROJECT_ROOT)!r}, which has no conf/base/catalog.yml). Pass "
            f"project_path explicitly, or set PYFORGE_ATLAS_LOCK_ROOT to an absolute path — "
            f"guessing would anchor the locks away from the data they guard."
        )
    return _PROJECT_ROOT


def _lock_names(datasets: Any) -> tuple[str, ...]:
    """Normalize a dataset iterable into sorted, de-duplicated lock identities.

    A bare ``str``/``bytes`` is REFUSED rather than iterated character by character — that
    would take 26 one-letter locks instead of one (correctness requirement 7). Transcoded
    names (``ds@pandas``) collapse to their base name: two transcoded views of one file are
    one file, the same correction kedro's own ``_remove_intermediates`` makes.
    """
    if isinstance(datasets, (str, bytes)):
        raise AdmissionConfigError(
            f"datasets must be an iterable of dataset names, not a bare "
            f"{type(datasets).__name__}: {datasets!r}"
        )
    try:
        names = {str(name).split("@", 1)[0] for name in datasets}
    except TypeError as exc:
        raise AdmissionConfigError(f"datasets is not iterable: {datasets!r}") from exc
    return tuple(sorted(names))


def _validate_wait_seconds(wait_seconds: Any) -> float:
    """Coerce the opt-in wait to a finite, non-negative float or raise
    :class:`AdmissionConfigError`.

    ``float()`` raises ``OverflowError`` on a huge int and ``ValueError``/``TypeError`` on
    junk; ``inf`` and ``nan`` pass ``float()`` but are not a finite deadline. All four
    become the ONE typed error, so a bad value can never silently degrade into reject-fast
    or into an unbounded wait (correctness requirement 7).
    """
    if isinstance(wait_seconds, bool):  # bool is an int subclass; `True` is not 1 second
        raise AdmissionConfigError(f"{WAIT_PARAM} must be a number, got bool {wait_seconds!r}")
    try:
        value = float(wait_seconds)
    except (TypeError, ValueError, OverflowError) as exc:
        raise AdmissionConfigError(
            f"{WAIT_PARAM} must be a finite non-negative number of seconds, "
            f"got {wait_seconds!r}"
        ) from exc
    if value != value or value in (float("inf"), float("-inf")):
        raise AdmissionConfigError(
            f"{WAIT_PARAM} must be finite, got {wait_seconds!r}"
        )
    if value < 0:
        raise AdmissionConfigError(
            f"{WAIT_PARAM} must be >= 0, got {wait_seconds!r}"
        )
    return value


def _pid_alive(pid: int) -> bool:
    """Is ``pid`` still running? Conservative in every ambiguous direction.

    POSIX-GATED (correctness requirement 5): on Windows — a declared platform in the root
    ``pixi.toml`` — ``os.kill(pid, 0)`` calls ``TerminateProcess``, so the liveness *probe
    would kill the process it probes*. Off POSIX a holder record is treated as alive; the
    kernel still frees the flock when its owner dies, so D5 degrades to "no reclaim
    message", never to "wedged dataset". An ``OSError`` that is not ``ProcessLookupError``
    (e.g. ``EPERM`` — a live process owned by someone else) also reads as alive.

    ``OverflowError`` is caught for the same reason ``_format_epoch`` catches it: a torn or
    hostile sidecar can carry a JSON integer wider than a C ``int`` (``os.kill(10**20, 0)``
    raises it, and it is neither ``OSError`` nor ``ValueError``), which would escape and turn
    a SUCCESSFUL admission — the locks are already held at this point — into an untyped crash.
    """
    if not _IS_POSIX:
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except (OSError, OverflowError, ValueError):
        return True
    return True


def _read_holder(path: Path) -> dict[str, Any]:
    """Read a holder sidecar into the :class:`RunAdmissionRejected` field shape.

    Every failure mode — absent file, unparseable JSON, a non-object payload, a ``pid`` that
    is not an int — degrades to ``None`` for that field. A corrupt sidecar must never turn a
    clean rejection into a ``JSONDecodeError``.
    """
    blank: dict[str, Any] = {"holder_run_id": None, "holder_pid": None, "held_since": None}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return blank
    if not isinstance(raw, dict):
        return blank
    run_id = raw.get("run_id")
    pid = raw.get("pid")
    started = raw.get("started_at")
    held_since: float | None = None
    if isinstance(started, (int, float)) and not isinstance(started, bool):
        # A JSON integer wider than float range raises OverflowError here — which is neither
        # OSError nor ValueError, so it would escape this function and turn a clean rejection
        # into an untyped crash, breaking the contract two lines up.
        try:
            held_since = float(started)
        except OverflowError:
            held_since = None
    # A pid must be POSITIVE to be a holder: `os.kill(0, 0)` signals this process's whole
    # group and `os.kill(-1, 0)` every process the user may signal — both would answer
    # "alive" for a record that names no process at all.
    return {
        "holder_run_id": str(run_id) if isinstance(run_id, (str, int)) else None,
        "holder_pid": (
            pid if isinstance(pid, int) and not isinstance(pid, bool) and pid > 0 else None
        ),
        "held_since": held_since,
    }


def _write_holder(path: Path, run_id: str) -> None:
    """Write this run's holder record. Written AFTER the lock is taken, so it only ever
    describes a real holder."""
    path.write_text(
        json.dumps({"run_id": run_id, "pid": os.getpid(), "started_at": time.time()}),
        encoding="utf-8",
    )


def _release_one(lock: Any) -> bool:
    """Release ONE lock. Returns whether it actually let go; never raises."""
    try:
        lock.release(force=True)
    except Exception as exc:  # noqa: BLE001 - a stuck handle must not strand the rest
        logger.warning(
            "run admission: releasing %s failed (%s: %s); continuing",
            getattr(lock, "lock_file", lock),
            type(exc).__name__,
            exc,
        )
        return False
    return True


def _release_locks(locks: list[Any]) -> None:
    """Release a list of held locks, never aborting mid-loop (correctness requirement 3)."""
    for lock in locks:
        _release_one(lock)


def acquire(
    datasets: Any,
    *,
    run_id: str,
    lock_root: Any = None,
    wait_seconds: Any = 0.0,
) -> AdmissionTicket:
    """Take one OS file lock per output dataset, in sorted order (D3/D4/D5).

    Reject-fast by default: the first conflicting dataset raises
    :class:`RunAdmissionRejected` naming the holder. ``wait_seconds > 0`` opts into a bounded
    wait enforced as ONE shared deadline across all locks — not ``wait_seconds`` per lock,
    which would silently multiply the caller's stated budget by the dataset count.

    Partial acquisition ALWAYS rolls back, on any exception and not just on
    ``filelock.Timeout`` (correctness requirement 2): an ``OSError`` from ``mkdir`` /
    ``acquire`` / the sidecar write (ENOSPC, EACCES, EROFS) is precisely the failure with no
    recovery path, so the k-1 locks already held must not be stranded unreleasable.
    """
    # Validated BEFORE the empty-set early return, so the check does not depend on which
    # path you enter (correctness requirement 7).
    timeout = _validate_wait_seconds(wait_seconds)
    names = _lock_names(datasets)
    run_id = str(run_id)
    if not names:
        # A pipeline with no declared outputs writes nothing: admitted, no lock files.
        return AdmissionTicket(run_id=run_id)

    if lock_root is not None:
        root = Path(lock_root)
        if not root.is_absolute():
            # The SAME guard `_resolve_base` applies to `project_path`, on the one input path
            # that reached the lock root without it. A relative `lock_root` re-anchors the
            # locks to the CWD — precisely the defect the first implementation of this story
            # shipped and was reverted for — and does it silently.
            raise AdmissionConfigError(
                f"lock_root must be absolute so the locks cannot become CWD-relative; "
                f"got {lock_root!r}"
            )
    else:
        root = default_lock_root()
    deadline = time.monotonic() + timeout
    held: list[Any] = []
    written: list[Path] = []
    reclaimed: list[str] = []
    try:
        root.mkdir(parents=True, exist_ok=True)
        for name in names:
            holder_path = root / f"{name}{_HOLDER_SUFFIX}"
            # thread_local=False (correctness requirement 1): filelock's default makes the
            # re-entrancy counter thread-local, so a release() from a different thread than
            # the acquirer is a SILENT NO-OP — the flock would then be held for the process
            # lifetime with the sidecar already unlinked, i.e. unattributable AND
            # unreclaimable. Verified live in this env.
            #
            # fallback_to_soft=False: on a filesystem whose flock returns ENOSYS (9p, some
            # FUSE/bind mounts) filelock 3.32 REWRITES ITS OWN CLASS to SoftFileLock behind a
            # UserWarning. Mutual exclusion would then rest on O_CREAT|O_EXCL and holder
            # liveness on filelock's marker file — not on "the kernel drops its flock", which
            # is the exact sentence D5, the spine and SPEC.md all rest on. Relocating the
            # store onto such a mount is a SUPPORTED override, so this must fail loudly
            # rather than keep reporting success on a weaker primitive.
            lock = filelock.FileLock(
                str(root / f"{name}{_LOCK_SUFFIX}"),
                thread_local=False,
                fallback_to_soft=False,
            )
            try:
                lock.acquire(timeout=max(0.0, deadline - time.monotonic()))
            except filelock.Timeout:
                raise RunAdmissionRejected(
                    datasets=names, conflicting=name, **_read_holder(holder_path)
                ) from None
            held.append(lock)
            # We hold the flock, so any sidecar still here belongs to a holder that did not
            # release: the kernel dropped its flock when it died (D5). Record the reclaim —
            # never break someone else's lock. Only claim it when there is a PID to judge
            # (correctness requirement 6).
            stale = _read_holder(holder_path)
            stale_pid = stale["holder_pid"]
            if stale_pid is not None and not _pid_alive(stale_pid):
                reclaimed.append(name)
                logger.warning(
                    "run admission: reclaimed dataset %r from dead holder run %r (pid %s, "
                    "held since %s) — its lock was released by the kernel, the holder record "
                    "was stale",
                    name,
                    stale["holder_run_id"],
                    stale_pid,
                    _format_epoch(stale["held_since"]),
                )
            # Recorded BEFORE the write, not after: `Path.write_text` truncates on open, so
            # an OSError part-way through (ENOSPC — the very failure the rollback exists for)
            # leaves a torn sidecar behind. Appending afterwards meant rollback never unlinked
            # exactly the record that failure created.
            written.append(holder_path)
            _write_holder(holder_path, run_id)
    except BaseException:
        # Remove the sidecars this failed attempt wrote BEFORE dropping its locks. Otherwise
        # a rejected run leaves a record naming itself; once its process exits, `_pid_alive`
        # says dead and the NEXT acquirer of each of those datasets reports a D5 reclaim.
        # That WARNING is the operator's only signal that a run was SIGKILLed — a `kedro run`
        # of `__default__` (46 outputs) rejected at index 37 would fire it 37 times for an
        # orderly rejection, which is how a real signal becomes noise.
        for holder_path in written:
            try:
                holder_path.unlink(missing_ok=True)
            except OSError as exc:  # noqa: BLE001 - a stuck sidecar must not mask the cause
                logger.warning(
                    "run admission: could not remove holder record %s during rollback "
                    "(%s: %s)",
                    holder_path,
                    type(exc).__name__,
                    exc,
                )
        _release_locks(held)
        raise

    return AdmissionTicket(
        run_id=run_id,
        datasets=names,
        reclaimed=tuple(reclaimed),
        locks=tuple(held),
        lock_root=root,
    )


def release(ticket: AdmissionTicket) -> None:
    """Release every lock the ticket holds. Never raises, never aborts mid-loop.

    A failure here must not convert a successful run into a failed one — ``after_pipeline_run``
    is the last thing kedro calls (correctness requirement 3).

    The sidecar is unlinked only AFTER the lock actually let go. The two orderings each leave
    one window, and this is the harmless one: a free lock that still advertises a holder is
    self-correcting (the next acquirer takes the lock FIRST, then finds our still-live pid,
    claims no reclaim, and overwrites the record), whereas a still-HELD lock whose record was
    already removed is exactly the unattributable, unreclaimable state correctness
    requirement 1 exists to prevent — ``run None (pid None)`` for the life of the process.
    """
    root = ticket.lock_root
    for name, lock in zip(ticket.datasets, ticket.locks):
        released = _release_one(lock)
        if root is not None and released:
            try:
                (root / f"{name}{_HOLDER_SUFFIX}").unlink(missing_ok=True)
            except OSError as exc:
                logger.warning(
                    "run admission: could not remove holder record for %r (%s: %s); "
                    "continuing",
                    name,
                    type(exc).__name__,
                    exc,
                )


class RunAdmissionHooks:
    """AD-23 run admission, registered ONCE in ``settings.HOOKS`` (D2).

    One registration is what makes the CLI, the seven MCP ``run_*`` tools and the Dagster
    plane all inherit admission: they dispatch through the same kedro HOOK MANAGER. (Note
    the Dagster plane does *not* ride ``KedroSession.run`` — kedro-dagster fires the hooks
    itself — which is why the guarantee is stated against the hook manager, not the session.)

    Parameters
    ----------
    lock_root:
        Override the project-anchored :func:`default_lock_root`. ``None`` (the shipped
        default) resolves per-run from ``run_params["project_path"]`` — the channel kedro
        supplies in ``record_data`` — falling back to the package-derived project root.
    wait_seconds:
        Constructor-level default for the opt-in bounded wait. ``settings.HOOKS`` constructs
        with no arguments, so the live channel is ``run_params["runtime_params"]``
        (``kedro run --params admission_wait_seconds=30``); this kwarg exists for direct
        testing.
    """

    def __init__(self, *, lock_root: Any = None, wait_seconds: Any = 0.0) -> None:
        self._lock_root = Path(lock_root) if lock_root is not None else None
        self._wait_seconds = wait_seconds
        # run_id -> LIFO stack of outstanding tickets. Per-run mutable state; reset on
        # deepcopy/pickle (see below).
        self._tickets: dict[str, list[AdmissionTicket]] = {}

    # -- deepcopy / pickle contract (mirrors AtlasObservabilityHooks) ---------- #

    def __deepcopy__(self, memo: dict[int, Any]) -> "RunAdmissionHooks":
        # C1's KedroProjectTranslator DEEP-COPIES settings.HOOKS at to_dagster() build time,
        # so the Dagster plane runs against a copy. Configuration carries over by value; the
        # outstanding tickets do NOT — a live filelock handle owns a thread lock and an open
        # file descriptor, so deep-copying one would either fail or (worse) hand a second
        # object the illusion of holding a lock it does not own.
        cls = self.__class__
        new = cls.__new__(cls)
        memo[id(self)] = new
        new._lock_root = self._lock_root
        new._wait_seconds = self._wait_seconds
        new._tickets = {}  # fresh per-run state
        return new

    def __getstate__(self) -> dict[str, Any]:
        # Pickle fallback (multiprocess runners). Same rule as __deepcopy__: a FileLock
        # handle cannot cross a process boundary — the flock belongs to the open file
        # description in the ORIGINAL process — so tickets are dropped, never shipped.
        state = self.__dict__.copy()
        state["_tickets"] = {}
        return state

    def __setstate__(self, state: dict[str, Any]) -> None:
        self.__dict__.update(state)

    # -- helpers -------------------------------------------------------------- #

    @staticmethod
    def _run_id(run_params: dict[str, Any] | None) -> str:
        # kedro 1.5.0 run_params carries `run_id` (there is NO `session_id` and NO
        # `pipeline_name` key — session.py record_data). kedro-dagster passes its own
        # run_params through the same key.
        return str((run_params or {}).get("run_id") or "")

    def _resolve_wait(self, run_params: dict[str, Any] | None) -> Any:
        runtime_params = (run_params or {}).get("runtime_params") or {}
        if isinstance(runtime_params, dict) and WAIT_PARAM in runtime_params:
            return runtime_params[WAIT_PARAM]
        return self._wait_seconds

    def _resolve_lock_root(self, run_params: dict[str, Any] | None) -> Path:
        if self._lock_root is not None:
            return self._lock_root
        return default_lock_root((run_params or {}).get("project_path"))

    # -- hooks ---------------------------------------------------------------- #

    # tryfirst on all three: settings.HOOKS tuple order is NOT enough, because kedro registers
    # entry-point plugins AFTER settings.HOOKS and pluggy dispatches LIFO — measured, an
    # installed kedro-viz took `before_pipeline_run` ahead of this hook. See the module
    # docstring; removing these markers silently gives that ordering away.
    @hook_impl(tryfirst=True)
    def before_pipeline_run(
        self, run_params: dict[str, Any], pipeline: Any, catalog: Any
    ) -> None:
        run_id = self._run_id(run_params)
        outputs = pipeline.all_outputs() if pipeline is not None else ()
        ticket = acquire(
            outputs,
            run_id=run_id,
            lock_root=self._resolve_lock_root(run_params),
            wait_seconds=self._resolve_wait(run_params),
        )
        stack = self._tickets.setdefault(run_id, [])
        if stack:
            # Correctness requirement 4: kedro-dagster reuses ONE run_id (the build-time
            # session id) for every job, so a naive `self._tickets[run_id] = ticket` would
            # orphan the first ticket's locks — or let run A's after-hook release run B's.
            # Refuse to overwrite: PUSH, and say so. Two co-outstanding tickets under one
            # run_id necessarily hold DISJOINT sets (an overlapping request would already
            # have been rejected — in-process locks contend), which is what makes
            # `_release_for`'s pairing BY DATASET SET exact. Do not "simplify" that back to a
            # bare LIFO pop: set-disjointness says nothing about which ticket belongs to the
            # pipeline that is finishing.
            logger.warning(
                "run admission: run id %r already has %d outstanding ticket(s) (datasets "
                "%s); stacking rather than overwriting so no lock is orphaned",
                run_id,
                len(stack),
                [t.datasets for t in stack],
            )
        stack.append(ticket)

    @hook_impl(tryfirst=True)
    def after_pipeline_run(
        self, run_params: dict[str, Any], pipeline: Any, catalog: Any
    ) -> None:
        # SUBSET signature, deliberately: pluggy's missing-argument check is per-IMPL, and
        # this hook is dispatched FIRST (by `tryfirst`, above). kedro-dagster calls
        # after_pipeline_run WITHOUT kedro's `run_result`, so a full signature here would make
        # THIS impl the raiser — and it would never release. Declaring only what it reads
        # means the locks are freed before any other impl's HookCallError.
        self._release_for(run_params, pipeline)

    @hook_impl(tryfirst=True)
    def on_pipeline_error(
        self, error: Exception, run_params: dict[str, Any], pipeline: Any, catalog: Any
    ) -> None:
        self._release_for(run_params, pipeline)

    def _release_for(self, run_params: dict[str, Any] | None, pipeline: Any = None) -> None:
        run_id = self._run_id(run_params)
        stack = self._tickets.get(run_id)
        if not stack:
            # Release without acquire (a run rejected at admission, or a hook manager that
            # only fires the after-hook): a no-op, never an error.
            return
        # Pair by the ticket's DATASET SET, not by LIFO position. When two runs share a
        # run_id (kedro-dagster reuses the build-time session id for every job) and overlap
        # in one process, popping the top would release the OTHER run's locks while it is
        # still writing — the precise interleaving admission exists to prevent. Matching on
        # the set the finishing pipeline declared is exact, because two co-outstanding
        # tickets always hold disjoint sets (an overlapping request would have been rejected).
        index = len(stack) - 1
        if pipeline is not None:
            wanted = _lock_names(pipeline.all_outputs())
            index = next(
                (i for i in range(len(stack) - 1, -1, -1) if stack[i].datasets == wanted),
                -1,
            )
            if index < 0:
                if len(stack) > 1:
                    # AMBIGUOUS: several runs share this run_id and none declared this output
                    # set, so there is no evidence about which ticket is the finishing one.
                    # Falling back to the most recent here would perform exactly the LIFO
                    # wrong-release the block above forbids — freeing a run that is still
                    # writing. Releasing NOTHING is the safe answer: those locks are freed by
                    # process exit, and no second writer is ever admitted in the meantime.
                    logger.error(
                        "run admission: no outstanding ticket for run %r matches the "
                        "finishing pipeline's outputs %s, and %d tickets are outstanding "
                        "(%s); releasing NOTHING rather than guessing — these locks are now "
                        "held until the process exits",
                        run_id,
                        list(wanted),
                        len(stack),
                        [t.datasets for t in stack],
                    )
                    return
                logger.warning(
                    "run admission: the finishing pipeline's outputs %s do not match run "
                    "%r's single outstanding ticket %s; releasing it (no other candidate)",
                    list(wanted),
                    run_id,
                    list(stack[0].datasets),
                )
                index = 0
        release(stack.pop(index))
        if not stack:
            # Do not let the registry grow one dead key per run in a long-lived MCP server.
            self._tickets.pop(run_id, None)
