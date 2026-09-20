"""The apply runner -- the transactional envelope (Story 10.3,
architecture NFR-R1/AR-5/AD-57/P-01/P-04/P-07).

Story 9.6 built a `Plan` carrying a `RepoFingerprint` explicitly so that "a
later `apply` story can refuse a `Plan` whose fingerprint no longer
matches" (`plan/types.py`'s own words), and nothing consumed it: no code
path anywhere under `seed/` turned a `Plan` into writes at all. This module
is that path, and ONLY that path -- `run_apply` refuses a stale plan before
touching disk, then executes the plan's actions in the plan's own order,
snapshotting each action's target immediately before that action runs and
restoring every snapshot in reverse order on ANY failure, so a run either
completes or leaves the repo exactly as it found it (NFR-R1: no partial
state).

**What this module deliberately does NOT do.** It never decides WHAT to
write. Materializing an artifact -- rendering a Copier template, inserting
a managed region, branching on `ArtifactClass` -- is the caller-supplied
`commit` callback's entire job, so this module imports no `engine`, no
`copier`, no `regions`, and no `Manifest`: region bodies, formats, and
model version would all drag a `Manifest` back in. It is also what makes
the AC's fault injection at three different action indices expressible at
all -- the per-action step has to be injectable to be interrupted on
demand.

**Where P-04 and P-07 are REINTERPRETED, not simply met.** Stated plainly
because a review pass was right to call the earlier wording overclaimed.
`run_apply`'s first act is to consult `plan.build.fingerprint_drift`, which
shells out to `git rev-parse`/`git status` and hashes every actioned target
on disk. That IS repo state being re-derived at apply time, and it IS
hashing happening during apply -- the literal words of P-04 ("apply
consumes only a `Plan` -- never re-derives state") and P-07 ("hash guards
are checked in detect, never in apply") both push against it. It is done
anyway, deliberately, because AD-57 and AR-5 require exactly this refusal
and nothing else in the pipeline can perform it. The reconciling argument:
P-04/P-07 exist to stop apply from forming its OWN opinion, per artifact,
about what should happen -- second-guessing detect's verdicts, and drifting
from the plan a human reviewed. This module forms no such opinion: the only
question it asks is whether the whole `Plan` is still true, and its only
two answers are proceed-with-everything or refuse-everything. No per-
artifact fate is decided here. The `hashlib`/`detect.hashes` import ban
(`tests/meta/test_p07_no_hash_comparison_in_apply.py`) is a direct-import
AST scan, so keeping the call one module away satisfies its letter; that
alone is NOT the justification, and this paragraph exists so nobody reads
the green meta test as proof the underlying rule was untouched.

**The `commit` contract.** `commit(action)` is contracted to write only
within `repo_root / action.target_path`. That single path is what this
module snapshots, and therefore the exact and only extent of the
transaction: anything `commit` writes ELSEWHERE is outside it and will not
be rolled back. Stated here rather than pretended away.

**Exactly what "leaves the repo as it found it" covers, and what it does
not.** A snapshot is the target's BYTES (or `None` for anything that is not
a regular file), so rollback restores file CONTENT and nothing else. Four
residues survive a rolled-back run, each verified by execution during
review and each filed as deferred work rather than silently implied away:
(1) the restored file's MODE is whatever `atomic_write_bytes` produces
(`0o666 & ~umask`), so an executable target -- the packaged manifest ships
`scripts/bmad-switch` as `copied-managed` -- comes back non-executable;
`fs.write` exposes no `mode=` passthrough to fix this from here. (2)
Anything at the target that is not a REGULAR FILE snapshots as `None` and is
never removed, since `fs` ships no removal primitive for it and P-01 forbids
reaching around it. Directories are the case that matters in practice -- a
directory-shaped artifact (the manifest's `presentations/{{ slug }}/`) and
everything under it survives, as do empty parent directories
`atomic_write_bytes` created for a nested target -- but the predicate is
`is_file()`, so the same is true of a dangling symlink, a symlink to a
directory, and a FIFO a `commit` leaves at a previously-absent target
(review finding: the earlier wording named only directories). (3) A
SYMLINK target snapshots its referent's bytes (`is_file()` follows links)
while `os.replace` replaces the link itself (`fs.py`'s own documented
behavior), so rollback leaves a regular file where the link was and the
referent still holding whatever `commit` wrote; `fs.py` accepts the same
bound on the grounds that no real V1 target artifact is expected to be a
symlink, and this module accepts it identically. (4) A target `commit`
wrote that the caller's own `never_write` set matches cannot be restored at
all -- the guard refuses the restore, and the run ends in `InternalError`
naming it for manual repair.

**Preconditions.** Exactly one is checked: the fingerprint
(`plan.build.fingerprint_drift`). Not-a-git-repo, dirty-worktree,
hand-edit, `--force` and `--skip` are Story 10.4's surface, which owns this
same file next. The stale check runs FIRST -- before any snapshot, before
any `commit` call, and before the empty-plan case can short-circuit
anything (see `run_apply`'s own docstring for why refusing beats
no-op-ing).

**Why the hash comparison is not here.** P-07's structural guard
(`tests/meta/test_p07_no_hash_comparison_in_apply.py`) bans `hashlib` and
`detect.hashes` from every module under `seed/apply/`. `fingerprint_drift`
lives in `plan/build.py`, beside `build_plan`, the fingerprint's sole
producer -- see that function's own docstring for the full argument. This
module imports the VERDICT (a tuple of drift strings), never the mechanism.

Never in this module: no state read or write (`seed/state/` is not imported
here in any form, so Story 10.2's own module can land beside this one
without either touching the other); no `.marshal/plan.json` read or write;
no CLI wiring and no exit-code dispatch (mapping a caught `SeedError` to
`sys.exit(exc.exit_code)` stays a later CLI story's surface, per
`errors.py`'s own Never bullet); no staged-output reconciliation and no
staging-directory cleanup despite `engine/copier.py`'s docstring assigning
both to "Story 10.3's apply runner" -- `MaterializeResult` exposes only
absolute `staged_paths`, never the staging root, so neither is implementable
against the shipped API (filed as deferred work, routed to whoever wires
materialization); and no removal of the empty parent directories
`atomic_write_bytes` may have created -- `fs` ships no directory-removal
primitive and P-01 forbids reaching around it, so rollback restores file
CONTENT and an empty directory may survive (a stated bound, also filed as
deferred work).

Imports `fs` as the MODULE (`from .. import fs`), never its individual
functions -- `regions/apply.py`'s established idiom, so a test can
monkeypatch `run.fs.write`/`run.fs.remove` and prove every byte the runner
itself writes goes through the never-write guard (P-01).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from pyforge.core.process import ProcessError

from .. import fs
from ..errors import InternalError, PreconditionFailure
from ..plan.build import fingerprint_drift
from ..plan.types import Action, Plan

#: The per-action step `run_apply` drives. Contracted to write only within
#: `repo_root / action.target_path` (see the module docstring); anything it
#: raises unwinds the whole run. A plain `Callable` alias rather than a
#: `Protocol`: it takes one positional argument and returns nothing, so
#: there is no structural surface a `Protocol` would pin that the alias
#: does not.
CommitAction = Callable[[Action], None]

#: Shared by every containment refusal below. Deliberately does NOT say "this
#: plan did not come from `build_plan`" -- review finding, verified by
#: execution: it can have. `detect/inventory.py::_resolve_within_repo` returns
#: `None` for a manifest entry whose `path` is absolute, traverses upward, or
#: is an in-repo symlink pointing out, and `_classify_entry` treats `None` as
#: `ABSENT` -- so `build_plan` emits a perfectly ordinary `Action` carrying the
#: raw escaping path. Telling an operator to re-plan would send them around a
#: loop that reproduces the identical plan; the manifest entry is what has to
#: change.
_ESCAPING_TARGET_REMEDY = (
    "correct the offending entry's `path` in the model manifest so it is a"
    " normalized repo-relative path inside the target repo, then re-plan; if"
    " the plan was hand-edited, discard it and rebuild from a fresh detect pass"
)


@dataclass(frozen=True)
class ApplyResult:
    """What a completed `run_apply` returns: the artifact ids it applied,
    in the order it applied them (which is `plan.actions` order, unmodified).

    Deliberately not a count and not a bool -- a caller rendering "what did
    this run do" needs the ids themselves, and the ORDER is the observable
    proof that the runner neither re-sorted nor filtered the plan it was
    handed. `applied=()` for an empty plan is a complete, successful result,
    never an error (AD-60: idempotence is defined as plan-emptiness).

    Frozen, like every other computed shape this package ships
    (`Plan`/`Action`/`Classification`), and carrying no `__post_init__`
    validation for the same reason those do not: it is constructed once,
    here, from values this module already computed."""

    applied: tuple[str, ...]


def _restore(
    snapshots: list[tuple[Path, bytes | None]],
    *,
    repo_root: Path,
    never_write: fs.NeverWrite,
) -> tuple[str, ...]:
    """Undo `snapshots` in REVERSE order, returning one message per path
    that could not be restored (`()` when every restore succeeded).

    Reverse order is what makes two actions naming the same `target_path`
    unwind correctly: a forward restore would write the EARLIER snapshot
    first and the later one -- itself already post-first-write content --
    second, leaving that intermediate state as the final result. Unwinding
    from the newest snapshot backwards ends at the oldest, which is the
    pre-run truth.

    `bytes` restores through `fs.write`; `None` (the target was not a file
    before its action ran) removes through `fs.remove`, but only `if
    target.is_file()` -- the exact predicate the snapshot itself was taken
    under, so a target that was (and still is) a directory or absent is
    left alone rather than reported as an unrestorable `IsADirectoryError`/
    `FileNotFoundError` it never actually diverged into.

    Every restore is attempted even after one fails -- a single
    unrestorable path must never abandon the rest, since each abandoned
    restore is another byte of the partial state NFR-R1 forbids. Catches
    `Exception`, not `BaseException`: a `KeyboardInterrupt` arriving DURING
    rollback is not a restore failure to aggregate and report, it is the
    operator interrupting the recovery itself, and swallowing it would make
    the process unkillable at exactly the moment a human is trying to stop
    it. That leaves the remaining restores unattempted, which is the honest
    outcome of a second interrupt and is stated rather than hidden -- and,
    review finding, it ALSO discards the `unrestorable` list accumulated so
    far, because the interrupt unwinds past `run_apply`'s inspection of this
    function's return value. The caller then sees a bare `KeyboardInterrupt`
    with maximum partial state and zero diagnostics. Reporting it anyway
    would mean either downgrading the interrupt to a catchable `SeedError`
    (worse) or writing to stderr from a library module that deliberately
    does no I/O; the choice is deferred rather than made badly here.

    That reasoning covers an interrupt arriving DURING rollback, and only
    that. A later review pass was right that it does not hold for the
    ORIGINAL exception: when `commit` raised `KeyboardInterrupt`/`SystemExit`
    and any restore then fails, `run_apply` wraps it in `InternalError` --
    a catchable `SeedError` -- so a CLI doing `except SeedError` exits 10 on
    an operator interrupt rather than dying. That is the I/O matrix's
    "rollback itself fails" row applied literally (it mandates `InternalError`
    naming every unrestored path, and carves out no exception for an
    interrupt), and reconciling it against the "interrupt propagates
    unchanged" row is a contract-level question, not a local fix. Filed as
    deferred work; stated here so the wrapping is not read as an oversight."""
    unrestorable: list[str] = []
    resolved_root = repo_root.resolve()
    for target, snapshot in reversed(snapshots):
        try:
            # Containment is re-checked HERE, not just once before the run.
            # Review finding, verified by execution (a real host file outside
            # the repo was destroyed): `run_apply`'s pre-loop check runs before
            # any `commit`, so it can only see the tree as it was THEN. An
            # action whose parent directory did not yet exist passes that check,
            # and a `commit` that materializes the parent as a SYMLINK to a host
            # directory makes this same path resolve outside the repo by the
            # time rollback reaches it. `fs`'s never-write guard cannot catch it
            # -- an out-of-repo path falls back to an absolute POSIX string no
            # repo-relative pattern matches, which is the whole reason the
            # containment check exists. Refusing to touch it and reporting it as
            # unrestorable is fail-safe: the run already ends in `InternalError`
            # naming the residue, which is strictly better than a silent
            # deletion outside the repo.
            if resolved_root not in target.resolve().parents:
                unrestorable.append(
                    f"{target}: no longer resolves inside {resolved_root}"
                    " (a commit redirected its parent); left untouched"
                )
                continue
            if snapshot is None:
                if target.is_file():
                    fs.remove(target, repo_root=repo_root, never_write=never_write)
            else:
                fs.write(target, snapshot, repo_root=repo_root, never_write=never_write)
        except Exception as failure:  # noqa: BLE001 -- aggregated, never swallowed
            unrestorable.append(f"{target}: {failure!r}")
    return tuple(unrestorable)


def run_apply(
    plan: Plan,
    *,
    repo_root: Path,
    never_write: fs.NeverWrite,
    commit: CommitAction,
) -> ApplyResult:
    """Apply `plan` against `repo_root` transactionally: either every
    action's `commit` succeeds, or the repo is left exactly as it was
    found.

    Refuses FIRST. `plan.build.fingerprint_drift` is consulted before any
    snapshot and before any `commit` call; a non-empty result raises
    `PreconditionFailure` (exit 3) whose message carries the literal token
    `stale-plan` and names every way the fingerprint diverged, so a human
    reading the failure knows WHICH assumption broke, not merely that one
    did.

    **Why that refusal precedes the empty-plan case.** "Apply is a no-op on
    an empty plan" and "apply refuses a plan whose fingerprint no longer
    matches" collide when both hold, and refusing wins: an empty plan
    asserts "this repo needs nothing", and if the repo has moved since the
    plan was built, that assertion is exactly what is no longer known to be
    true. Re-planning is the correct next step and AD-60 makes it cheap. On
    a FRESH plan -- the only state in which "nothing to do" is a
    trustworthy answer -- an empty `plan.actions` needs no special case at
    all: the loop below takes zero snapshots, calls `commit` zero times,
    writes nothing (not even `.marshal/`), and returns
    `ApplyResult(applied=())`.

    Executes in `plan.actions` order, unmodified -- never re-sorted, never
    filtered, never deduplicated. Each iteration snapshots
    `repo_root / action.target_path` as `bytes` (a regular file) or `None`
    (anything else) IMMEDIATELY before that action's `commit` call, so the
    snapshot reflects whatever the preceding actions left behind rather
    than a single stale pre-run read of the whole repo.

    On ANY `BaseException` -- `KeyboardInterrupt` and `SystemExit` included,
    since an interrupted run leaves the same partial state a failed one
    does -- every snapshot taken so far is restored in reverse order and the
    ORIGINAL exception is re-raised unchanged (a bare `raise`), so a caller
    sees what `commit` actually raised, never a rollback artifact. The one
    exception to "unchanged" is a rollback that itself fails: that IS the
    partial state NFR-R1 forbids, so it is reported loudly as
    `InternalError` (exit 10) naming both the original failure and every
    path left unrestored, chained `from` the original rather than replacing
    it.

    A failure raised while TAKING a snapshot (an unreadable target) is not
    special-cased: that action's `commit` never runs, its target never
    enters `snapshots`, every prior action is still rolled back, and the
    `OSError` propagates unchanged -- `fs.py`'s own "never wraps a generic
    `OSError`" line, applied one layer up.

    `never_write` is used only for the runner's own restore writes; whether
    `commit` honors it for its own writes is `commit`'s contract, not
    something this function can enforce (its `NeverWriteViolation`, exit 4,
    simply propagates like any other `commit` failure, unwinding the run).
    """
    resolved_root = repo_root.resolve()
    for action in plan.actions:
        # Checked on the LITERAL `target_path`, before any resolution, and
        # re-derived nowhere else. Review finding, verified by execution: the
        # earlier check resolved the path but the snapshot/restore loops below
        # re-derive the RAW `repo_root / action.target_path`, so the guard did
        # not bind the path it was guarding. With `sub` absent, `'sub/../b.txt'`
        # resolved inside the repo and passed; the raw path then stat'd as
        # absent (no `sub`), snapshotted `None`, and once `commit`'s
        # `mkdir(parents=True)` materialized `sub` the same raw path resolved
        # onto the REAL `b.txt`, which rollback then deleted. Refusing
        # non-normalized targets outright closes that gap at the source: no
        # legitimate `build_plan` artifact path is absolute or traverses upward.
        if Path(action.target_path).is_absolute() or ".." in Path(action.target_path).parts:
            raise PreconditionFailure(
                f"escaping-target: action {action.artifact_id!r} names target_path"
                f" {action.target_path!r}, which is absolute or traverses upward"
                " -- a target must be a normalized repo-relative path",
                remedy=_ESCAPING_TARGET_REMEDY,
            )
        target = repo_root / action.target_path
        try:
            resolved = target.resolve()
        except (OSError, ValueError) as failure:
            # `Plan.from_json_dict` type-checks `target_path` as `str` and
            # nothing more, so an embedded NUL reaches `resolve()` and raises a
            # raw `ValueError` -- escaping the closed six-leaf taxonomy exactly
            # as the untranslated `ProcessError` below did before it was
            # wrapped. Review finding, verified by execution.
            raise PreconditionFailure(
                f"unusable-target: action {action.artifact_id!r} names target_path"
                f" {action.target_path!r}, which cannot be resolved to a path"
                f" -- {failure!r}",
                remedy=_ESCAPING_TARGET_REMEDY,
            ) from failure
        # `resolved == resolved_root` is refused too, not excepted: a target
        # that IS the repo root ('.', '', 'sub/..') is not a legitimate
        # artifact, and the earlier `resolved != resolved_root` short-circuit
        # let it through as a successful apply (review finding).
        if resolved_root not in resolved.parents:
            raise PreconditionFailure(
                f"escaping-target: action {action.artifact_id!r} names target_path"
                f" {action.target_path!r}, which resolves to {resolved} -- not a path"
                f" strictly inside {resolved_root}",
                remedy=_ESCAPING_TARGET_REMEDY,
            )

    try:
        drift = fingerprint_drift(plan, repo_root)
    except ProcessError as failure:
        raise PreconditionFailure(
            f"plan freshness could not be verified against {repo_root}: {failure}",
            remedy=(
                "ensure `git` is installed and on PATH and that repo_root names an"
                " existing directory, then re-run apply"
            ),
        ) from failure
    if drift:
        raise PreconditionFailure(
            f"stale-plan: the repo no longer matches the fingerprint this plan was built against -- {'; '.join(drift)}",
            remedy=("re-run the plan against the current repo state and review the fresh plan before applying it"),
        )

    snapshots: list[tuple[Path, bytes | None]] = []
    # Accumulated inside the loop, never recomputed from `plan.actions` on
    # the way out (review finding): a result derived from the INPUT cannot
    # be evidence of anything about the EXECUTION, and this tuple is exactly
    # what `ApplyResult`'s docstring offers as proof that the runner neither
    # re-sorted nor filtered the plan it was handed.
    applied: list[str] = []
    try:
        for action in plan.actions:
            target = repo_root / action.target_path
            snapshots.append((target, target.read_bytes() if target.is_file() else None))
            commit(action)
            applied.append(action.artifact_id)
    except BaseException as original:
        unrestorable = _restore(snapshots, repo_root=repo_root, never_write=never_write)
        if unrestorable:
            raise InternalError(
                f"apply failed with {original!r} and its rollback could not fully undo"
                f" the run -- unrestored: {'; '.join(unrestorable)}",
                remedy=(
                    "inspect and restore the listed path(s) by hand (git checkout, if"
                    " they are tracked) before running apply again"
                ),
            ) from original
        raise

    return ApplyResult(applied=tuple(applied))
