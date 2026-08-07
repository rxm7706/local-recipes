"""Projection drift detection -- "link-target identity" (Story 6.3, FR-42,
AD-31/AD-36).

Story 6.2's `core/skill_projection.py` projects the canonical `.claude/skills`
tree into every OTHER tree a configured adapter declares via ONE directory
symlink per distinct tree, and that module's own docstring already names the
property this module exploits: "a directory symlink cannot drift in CONTENT
(only in TARGET)." This module is the pure planning core for VERIFYING that
property still holds -- no I/O, no `os`/`subprocess`/`time`, no
`pyforge.marshal.adapters` import (AD-4); every filesystem read lives in
`cli/adapters.py::gather_conformance_findings` instead, which is also the
sole caller reachable from BOTH `marshal adapters conform` and (via a local
import to avoid a load-time circular dependency) `marshal preflight`.

The status vocabulary is deliberately closed and small: `STATUS_LINK_TARGET_
CONFIRMED` is the ONE passing outcome, returned if and only if a live
symlink's raw target equals the canonical-relative target `sync` would
compute -- a genuinely falsifiable condition, proven non-vacuous by
`tests/meta/test_ad31_conformance_check_can_genuinely_fail.py`. `STATUS_
ADDED`/`STATUS_REMOVED`/`STATUS_MODIFIED` are the three DRIFT outcomes (this
story's resolved reading of the AC's generic "added, removed and modified
skills per adapter tree" wording for a mechanism that operates at TREE
granularity only -- see the story's own spec Design Notes for why "skills"
in that phrasing is not read as a literal per-skill-file report; Story 6.2
already forbids per-skill link/copy tracking outright).

`MECHANISM_CHECKERS` mirrors `skill_projection.PROJECTION_MECHANISM_BY_
PLATFORM`'s own declared-not-branched shape: ONE table, one owner. A
mechanism string absent from it -- including `None`, the "no declared
projection mechanism for this platform" case `skill_projection.
mechanism_for_platform` already returns -- NEVER reaches a checker function
at all. `evaluate_conformance` is the total entry point every caller uses:
for an unrecognized mechanism, EVERY tree in scope (both an explicit
`unevaluated_trees` argument and every tree in the supplied `live_states`)
folds into `ConformanceReport.unevaluated_trees`, `checks` stays empty --
never a fabricated pass, and never `not-applicable`, which `core.verdict`'s
own closed six-member lattice (`error > gate-failed > scope-violation >
unevaluable > warn > clean`) has no member for. This is the AC's own
"reporting clean for a check that cannot fail is a meta-test failure" rule,
made structural rather than a convention a future call site could quietly
violate.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

# `ports/` is NOT in AD-4's forbidden-modules list (only `subprocess`/`os`/
# `time`/`pyforge.marshal.adapters` are) -- `core/status.py` already imports
# `..ports.harness` (`DeferredStory`, `TaskPhaseSnapshot`) for the identical
# reason: a Protocol/dataclass module declares shapes only, no I/O of its
# own to import transitively.
from ..ports.harness import AdapterProbe

STATUS_LINK_TARGET_CONFIRMED = "link-target-confirmed"
STATUS_ADDED = "added"
STATUS_REMOVED = "removed"
STATUS_MODIFIED = "modified"

ALL_STATUSES: frozenset[str] = frozenset(
    {STATUS_LINK_TARGET_CONFIRMED, STATUS_ADDED, STATUS_REMOVED, STATUS_MODIFIED}
)

# Story 6.4 (FR-43, AD-31) -- a SECOND, independent closed status pair for a
# DIFFERENT fact ("does this adapter exist on this host", never conflated
# with the tree-drift vocabulary above). Deliberately excluded from
# `ALL_STATUSES`, which stays Story 6.3's own closed set unchanged.
STATUS_AVAILABLE = "available"
STATUS_UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class TreeLiveState:
    """One tree's already-read filesystem facts, gathered by the I/O
    boundary (`cli/adapters.py::gather_conformance_findings`) -- nothing is
    read here (AD-4).

    - ``desired`` -- at least one CURRENTLY configured adapter declares this
      tree (mirrors ``skill_projection.plan_projection``'s own ``to_project``
      set).
    - ``previously_projected`` -- the skill-projection manifest recorded this
      tree as projected by a prior ``sync`` run.
    - ``live_target`` -- the raw ``FsPort.read_symlink_target`` result (a
      relative path string) if the tree's path is currently a symlink,
      ``None`` otherwise (absent, or a real file/directory).
    - ``live_exists`` -- ``FsPort.exists`` (follows a symlink) -- distinguishes
      a dangling symlink (``live_target is not None``, ``live_exists`` False)
      from a real, non-symlink occupant (``live_target is None``,
      ``live_exists`` True) from genuine absence (both ``None``/``False``).
    - ``expected_target`` -- the relative target ``sync`` would repoint this
      tree to, computed the SAME way ``run_adapters_sync`` computes it
      (``os.path.relpath`` of the canonical dir from the tree's parent).
    """

    tree: str
    adapters: tuple[str, ...]
    desired: bool
    previously_projected: bool
    live_target: str | None
    live_exists: bool
    expected_target: str


@dataclass(frozen=True)
class TreeConformance:
    """One tree's classified drift-check outcome."""

    tree: str
    adapters: tuple[str, ...]
    status: str
    detail: str


@dataclass(frozen=True)
class ConformanceReport:
    """The full, pure output of ``evaluate_conformance`` -- ``cli/adapters.py``
    turns this into finding(s) and an envelope's own ``data`` payload; this
    dataclass carries no I/O result itself."""

    mechanism: str | None
    checks: tuple[TreeConformance, ...]
    unevaluated_trees: tuple[str, ...]


def _check_symlink_identity(state: TreeLiveState) -> TreeConformance:
    """The ONE mechanism-specific checker this story ships, for the
    ``"symlink"`` mechanism ``skill_projection.PROJECTION_MECHANISM_BY_
    PLATFORM`` declares. Asserts LINK-TARGET IDENTITY only -- never a
    content diff (a directory symlink has no content of its own to diff).

    Raises ``ValueError`` if ``state`` is neither ``desired`` nor
    ``previously_projected`` -- callers only ever construct
    ``TreeLiveState`` for trees in ``{t.tree for t in plan.to_project} |
    previously_projected`` (a caller-contract violation otherwise, never
    silently folded into a passing outcome)."""
    if not state.desired and not state.previously_projected:
        raise ValueError(
            f"tree {state.tree!r} is neither desired nor previously projected "
            "-- caller contract violated (TreeLiveState must only be "
            "constructed for a tree in scope)"
        )

    if state.live_target is not None:
        live_kind = "symlink_correct" if state.live_target == state.expected_target else "symlink_wrong"
    elif state.live_exists:
        # `read_symlink_target` is `None` but `exists` (which FOLLOWS a
        # symlink) is True: a real, non-symlink file or directory occupies
        # this path -- the exact structural-conflict shape `sync`'s own
        # create path already refuses to clobber (MRS-ADP-007).
        live_kind = "conflict"
    else:
        live_kind = "absent"

    if live_kind == "symlink_correct":
        if state.desired:
            return TreeConformance(
                state.tree,
                state.adapters,
                STATUS_LINK_TARGET_CONFIRMED,
                "live symlink target matches the canonical-relative target -- "
                "the falsifiable identity check this mechanism supports, confirmed",
            )
        return TreeConformance(
            state.tree,
            state.adapters,
            STATUS_REMOVED,
            "no configured adapter declares this tree any more, but its "
            "symlink still resolves to canonical -- run 'marshal adapters "
            "sync' to remove it",
        )

    if live_kind == "absent":
        if state.previously_projected:
            return TreeConformance(
                state.tree,
                state.adapters,
                STATUS_REMOVED,
                "the skill-projection manifest recorded this tree as "
                "projected, but nothing exists at its path any more -- "
                "removed outside 'marshal adapters sync'",
            )
        # state.desired is True here (the ValueError guard above already
        # ruled out neither-desired-nor-tracked).
        return TreeConformance(
            state.tree,
            state.adapters,
            STATUS_ADDED,
            "a configured adapter declares this tree but it has never been "
            "projected -- run 'marshal adapters sync'",
        )

    # live_kind in {"symlink_wrong", "conflict"} -- present, but the
    # identity check fails regardless of desired/previously_projected
    # (mirrors `sync`'s own structural-conflict handling: real content in
    # the way, or a hand-repointed link, is refused, never silently
    # accepted as correct).
    if live_kind == "symlink_wrong":
        detail = (
            f"live symlink target {state.live_target!r} does not match the "
            f"canonical-relative target {state.expected_target!r}"
        )
    else:
        detail = "a real file or directory occupies this path, not a symlink to canonical"
    return TreeConformance(state.tree, state.adapters, STATUS_MODIFIED, detail)


# AD-36's own declared-table shape, mirrored: the ONE (mechanism -> checker)
# table, one owner. A mechanism string absent here -- including the `None`
# "no declared projection mechanism" case -- is handled entirely by
# `evaluate_conformance` below, which never invokes a checker for it.
MECHANISM_CHECKERS: Mapping[str, Callable[[TreeLiveState], TreeConformance]] = {
    "symlink": _check_symlink_identity,
}


def evaluate_conformance(
    live_states: Iterable[TreeLiveState],
    *,
    mechanism: str | None,
    unevaluated_trees: tuple[str, ...] = (),
) -> ConformanceReport:
    """The total entry point every caller uses.

    When ``mechanism`` has no entry in ``MECHANISM_CHECKERS`` (including
    ``None``), EVERY tree in scope -- both the explicit
    ``unevaluated_trees`` argument (typically ``plan_projection``'s own
    ``unsupported_trees``) and every tree named in ``live_states`` -- folds
    into ``ConformanceReport.unevaluated_trees``; ``checks`` stays empty.
    This is deliberately unconditional: a mechanism string that IS declared
    in ``skill_projection``'s own platform table but has no registered
    checker HERE (a future platform row added there before a checker exists
    in this module) degrades identically to the ``None`` case, never a
    silently-invented pass.

    When ``mechanism`` IS registered, every state in ``live_states`` is run
    through its checker; ``unevaluated_trees`` passes through unchanged
    (there is no case where BOTH a registered mechanism and a non-empty
    explicit ``unevaluated_trees`` argument are expected together in
    practice, but the parameter is honored either way rather than silently
    dropped)."""
    checker = MECHANISM_CHECKERS.get(mechanism) if mechanism is not None else None
    if checker is None:
        return ConformanceReport(
            mechanism=mechanism,
            checks=(),
            unevaluated_trees=tuple(sorted(set(unevaluated_trees) | {state.tree for state in live_states})),
        )
    checks = tuple(checker(state) for state in live_states)
    return ConformanceReport(mechanism=mechanism, checks=checks, unevaluated_trees=tuple(unevaluated_trees))


def build_probe_record(probe: AdapterProbe) -> dict[str, object]:
    """Shape an already-observed ``AdapterProbe`` (Story 6.4, FR-43) into the
    plain dict ``cli/adapters.py::run_adapters_probe`` reports as
    ``data.probe`` and (after routing the WHOLE dict through
    ``core.egress.to_redacted`` at the write boundary -- never here, AD-4)
    persists to the machine-scoped probe-record file. Mirrors ``core.egress.
    build_gate_record``'s own "the caller already gathered every fact, this
    function only shapes" convention -- no I/O, no redaction (redaction is a
    port-boundary property, AD-34; this module has no port boundary).

    ``status`` is ``STATUS_UNAVAILABLE`` if and only if ``probe.binary_present``
    is ``False`` -- the ONE condition this closed, two-member vocabulary
    distinguishes (AD-31); every other ``AdapterProbe`` field passes through
    unchanged."""
    status = STATUS_UNAVAILABLE if not probe.binary_present else STATUS_AVAILABLE
    return {
        "adapter": probe.adapter,
        "binary": probe.binary,
        "status": status,
        "binary_present": probe.binary_present,
        "binary_version": probe.binary_version,
        "capabilities": dict(probe.capabilities),
        "probe_output": probe.probe_output,
        "probe_note": probe.probe_note,
    }


# Story 6.5 (FR-44, AD-31/AD-37) -- a THIRD, independent closed status pair
# for a THIRD distinct fact ("did the canonical smoke story complete end to
# end on this adapter, on this machine"), never conflated with either of the
# two pairs above even though the string literal "unavailable" happens to
# coincide with Story 6.4's own STATUS_UNAVAILABLE -- AD-31's "never
# conflated, never sharing a constant" is about the CLASSIFICATION/constant,
# not incidental string equality between two independently-declared,
# independently-owned vocabularies.
STATUS_SMOKE_PASS = "pass"
STATUS_SMOKE_FAIL = "fail"
STATUS_SMOKE_UNAVAILABLE = "unavailable"

# The AC's own "spec read -> change -> verify -> commit" lifecycle -- a
# closed, ordered four-member vocabulary naming the FAILING stage when
# `evaluate_smoke` classifies `STATUS_SMOKE_FAIL`. `None` for `pass`/
# `unavailable` (there is no "failing stage" for either).
STAGE_READ = "read"
STAGE_CHANGE = "change"
STAGE_VERIFY = "verify"
STAGE_COMMIT = "commit"
SMOKE_STAGES: tuple[str, ...] = (STAGE_READ, STAGE_CHANGE, STAGE_VERIFY, STAGE_COMMIT)


@dataclass(frozen=True)
class SmokeFacts:
    """Already-gathered raw facts from ONE `HarnessPort.run_smoke` attempt
    plus the caller's own pre/post git-worktree observation (Story 6.5) --
    nothing is read here (AD-4); `cli/adapters.py::run_adapters_smoke`
    gathers every field via `VcsPort`/`FsPort` and `SmokeRunResult`.

    - `binary_present`/`launched`/`timed_out`/`returncode` mirror
      `SmokeRunResult`'s own same-named fields verbatim.
    - `file_changed` -- the smoke's own target file (`SMOKE.md`) differs
      from its seeded content after the run.
    - `commit_made` -- the ephemeral worktree's `HEAD` sha advanced past
      its pre-run baseline (`VcsPort.worktree_head_sha`, AD-33: git is the
      sole authority for repository facts).
    """

    binary_present: bool
    launched: bool
    timed_out: bool
    returncode: int | None
    file_changed: bool
    commit_made: bool


@dataclass(frozen=True)
class SmokeReport:
    """The full, pure output of `evaluate_smoke` -- `cli/adapters.py` turns
    this into a finding (when `status == STATUS_SMOKE_FAIL`) and an
    envelope's own `data` payload; this dataclass carries no I/O result
    itself."""

    status: str
    failing_stage: str | None
    detail: str


def evaluate_smoke(facts: SmokeFacts) -> SmokeReport:
    """The total, pure classifier every caller uses (Story 6.5, FR-44):
    `not binary_present` -> `STATUS_SMOKE_UNAVAILABLE`, no failing stage
    (the AC's own "an adapter absent from the host reports unavailable
    without failing the command"). `commit_made` -> `STATUS_SMOKE_PASS` --
    the ONE passing condition, since a durable commit is only reachable
    after read/change/verify already completed in `bmad-loop`'s own
    dev-session lifecycle. Short of a commit, the EARLIEST stage lacking
    positive OBSERVABLE evidence is named the failing one: `file_changed`
    (but no commit) -> `STAGE_VERIFY` (a change landed, so read+change
    plausibly completed, but verify -- or the commit step itself -- never
    did); `launched` (but no file change) -> `STAGE_CHANGE` (the harness
    ran but produced no observable edit); otherwise (never launched despite
    a present binary -- a launch-time OSError) -> `STAGE_READ`. This is a
    genuine, documented fidelity limit (see the spec's own Design Notes):
    Marshal cannot observe "read" or "verify" succeeding independently from
    OUTSIDE the adapter's own session, so the classification is inferred
    from the outermost observable boundary a git worktree and a known
    target file expose, never from adapter-internal introspection.
    `timed_out` is folded into `detail` whenever informative, never into
    `status`/`failing_stage` itself. `returncode` is different: PASS
    requires `commit_made` AND `file_changed` AND a clean exit (`0` or
    `None`) all together (review finding: a commit landing is not, on its
    own, sufficient corroboration -- a non-zero exit alongside a landed
    commit, or a commit that never touched the smoke's own target file,
    both used to misreport PASS). Short of that full corroboration, a
    `commit_made` without it still names `STAGE_COMMIT` as the failing
    stage rather than falling through to the weaker `file_changed`/
    `launched` checks below, which assume no commit landed at all."""
    if not facts.binary_present:
        return SmokeReport(
            status=STATUS_SMOKE_UNAVAILABLE,
            failing_stage=None,
            detail="adapter binary not present on this host",
        )
    detail_suffix = ""
    if facts.timed_out:
        detail_suffix = " (the bounded harness call timed out before returning)"
    elif facts.launched and facts.returncode not in (0, None):
        detail_suffix = f" (bmad-loop run exited {facts.returncode})"
    if facts.commit_made:
        if facts.file_changed and facts.returncode in (0, None):
            return SmokeReport(
                status=STATUS_SMOKE_PASS,
                failing_stage=None,
                detail="spec read, change, verify, and commit all completed" + detail_suffix,
            )
        return SmokeReport(
            status=STATUS_SMOKE_FAIL,
            failing_stage=STAGE_COMMIT,
            detail=(
                "a commit landed but does not fully corroborate a completed run "
                f"(target file changed={facts.file_changed}, returncode={facts.returncode})"
                + detail_suffix
            ),
        )
    if facts.file_changed:
        return SmokeReport(
            status=STATUS_SMOKE_FAIL,
            failing_stage=STAGE_VERIFY,
            detail=(
                "a change was made but never committed -- verify (or the "
                "commit step itself) did not complete" + detail_suffix
            ),
        )
    if facts.launched:
        return SmokeReport(
            status=STATUS_SMOKE_FAIL,
            failing_stage=STAGE_CHANGE,
            detail=(
                "the harness launched but produced no observable change"
                + detail_suffix
            ),
        )
    return SmokeReport(
        status=STATUS_SMOKE_FAIL,
        failing_stage=STAGE_READ,
        detail="the harness could not be launched against this adapter at all" + detail_suffix,
    )


def build_smoke_record(
    adapter: str,
    report: SmokeReport,
    *,
    binary: str,
    binary_present: bool,
    harness_version: str | None = None,
    recorded_at: str | None = None,
) -> dict[str, object]:
    """Shape an already-classified `SmokeReport` (Story 6.5, FR-44) into the
    plain dict `cli/adapters.py::run_adapters_smoke` reports as `data.smoke`
    and (after routing through `core.egress.to_redacted` at the write
    boundary -- never here, AD-4) persists to the machine-scoped smoke
    record file. Mirrors `build_probe_record`'s own "the caller already
    gathered every fact, this function only shapes" convention -- no I/O, no
    redaction.

    `harness_version`/`recorded_at` (Story 6.6, FR-45) are additive,
    backward-compatible keyword parameters -- mirroring Story 6.5's own
    `render_policy_toml`/`write_policy_toml` `adapter=` precedent -- capturing
    the bmad-loop version and the UTC ISO-8601 instant THIS smoke ran, since
    that fact is only ever truthfully known at smoke time, never
    reconstructible later when `core.conformance.build_matrix_row`
    accumulates it into a tracked matrix row."""
    return {
        "adapter": adapter,
        "binary": binary,
        "binary_present": binary_present,
        "status": report.status,
        "failing_stage": report.failing_stage,
        "detail": report.detail,
        "harness_version": harness_version,
        "recorded_at": recorded_at,
    }


# Story 6.6 (conformance matrix, FR-45/SM-6/AD-31/AD-37) -- a FOURTH,
# independent closed status pair for a FOURTH distinct fact ("what does the
# accumulated, tracked matrix claim about this adapter on this host"),
# deliberately excluded from `ALL_STATUSES` and from Story 6.4's/6.5's own
# pairs even though three of the four string literals happen to coincide
# with `STATUS_SMOKE_*` -- AD-31's "never conflated, never sharing a
# constant" is about the CLASSIFICATION/constant, not incidental string
# equality (the identical reasoning Story 6.5's own docstring already gives
# for its coincidence with Story 6.4's `STATUS_UNAVAILABLE`).
STATUS_MATRIX_NOT_ATTEMPTED = "not-attempted"
STATUS_MATRIX_UNAVAILABLE = "unavailable"
STATUS_MATRIX_FAIL = "fail"
STATUS_MATRIX_PASS = "pass"

# `not-attempted` has no corresponding `STATUS_SMOKE_*` entry -- it is not a
# fact `evaluate_smoke` can ever classify (a smoke either ran, "unavailable",
# or classified pass/fail); it is what `build_matrix_row` reports when NO
# smoke record exists for an adapter at all.
_SMOKE_STATUS_TO_MATRIX_STATUS: Mapping[str, str] = {
    STATUS_SMOKE_PASS: STATUS_MATRIX_PASS,
    STATUS_SMOKE_FAIL: STATUS_MATRIX_FAIL,
    STATUS_SMOKE_UNAVAILABLE: STATUS_MATRIX_UNAVAILABLE,
}


@dataclass(frozen=True)
class MatrixRow:
    """One adapter's accumulated conformance-matrix row (Story 6.6, FR-45)
    -- the FULL contract `cli/adapters.py::run_adapters_matrix` renders into
    the tracked matrix file. `stale` is `True` iff `date` parses and is
    older than the caller-supplied staleness threshold -- `False`, never
    fabricated, for `not-attempted` (no claim was ever made, so "how old is
    the claim" does not apply) and for an unparseable/missing `date`."""

    adapter: str
    status: str
    adapter_version: str | None
    harness_version: str | None
    date: str | None
    failing_stage: str | None
    stale: bool


def build_matrix_row(
    adapter: str,
    *,
    smoke_record: Mapping[str, object] | None,
    probe_record: Mapping[str, object] | None,
    now: datetime,
    stale_after_days: int,
) -> MatrixRow:
    """The pure, total classifier every caller uses (Story 6.6, FR-45/SM-6):
    no I/O, no clock read (`now` is caller-supplied, AD-4) -- `cli/
    adapters.py::run_adapters_matrix` gathers `smoke_record`/`probe_record`
    from the two EXISTING machine-scoped files (`_read_smoke_state`/
    `_read_probe_state`) before calling this function.

    `smoke_record is None` -> `STATUS_MATRIX_NOT_ATTEMPTED`, with `date`/
    `stale`/`harness_version`/`failing_stage` all `None`/`False` (no smoke
    claim exists at all to carry those facts) -- but `adapter_version`
    STILL comes from `probe_record` when one is available (SM-6's "not
    gameable" requirement is about `status`, never about discarding a real,
    already-known probe fact just because smoke hasn't run yet -- review
    finding: an earlier draft hardcoded `adapter_version=None` here too,
    silently dropping a known probed version).

    Otherwise `smoke_record["status"]` maps through
    `_SMOKE_STATUS_TO_MATRIX_STATUS`; an unrecognized/missing value degrades
    to `STATUS_MATRIX_NOT_ATTEMPTED` rather than fabricating a `pass` --
    defensive against a record this module did not itself produce (e.g. a
    hand-edited `adapter-smoke.json`). This degraded case ALSO reports
    `date: None`, `stale: False` -- the same "no claim exists to age" rule
    as the `smoke_record is None` case applies here too (review finding: an
    earlier draft computed `date`/`stale` from the malformed record's own
    `recorded_at` even when `status` itself was unrecognized, producing a
    self-contradictory `not-attempted, stale=True` row).

    `date`/`stale` (only computed when `status` is a recognized, real
    smoke-run status): `smoke_record["recorded_at"]` is parsed via
    `datetime.fromisoformat`; a naive result is treated as UTC (matches
    `core.egress`'s own timestamp convention). An unparseable or missing
    value reports `date: None`, `stale: False` -- never raises, and never
    fabricates staleness from an absent fact."""
    raw_adapter_version = probe_record.get("binary_version") if probe_record is not None else None
    adapter_version = raw_adapter_version if isinstance(raw_adapter_version, str) else None

    if smoke_record is None:
        return MatrixRow(
            adapter=adapter,
            status=STATUS_MATRIX_NOT_ATTEMPTED,
            adapter_version=adapter_version,
            harness_version=None,
            date=None,
            failing_stage=None,
            stale=False,
        )

    raw_status = smoke_record.get("status")
    status = _SMOKE_STATUS_TO_MATRIX_STATUS.get(
        raw_status if isinstance(raw_status, str) else "", STATUS_MATRIX_NOT_ATTEMPTED
    )

    if status == STATUS_MATRIX_NOT_ATTEMPTED:
        return MatrixRow(
            adapter=adapter,
            status=status,
            adapter_version=adapter_version,
            harness_version=None,
            date=None,
            failing_stage=None,
            stale=False,
        )

    raw_date = smoke_record.get("recorded_at")
    date = raw_date if isinstance(raw_date, str) else None
    stale = False
    if date is not None:
        try:
            parsed = datetime.fromisoformat(date)
        except ValueError:
            parsed = None
        if parsed is not None:
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            stale = (now - parsed) > timedelta(days=stale_after_days)

    raw_harness_version = smoke_record.get("harness_version")
    harness_version = raw_harness_version if isinstance(raw_harness_version, str) else None

    raw_failing_stage = smoke_record.get("failing_stage")
    failing_stage = raw_failing_stage if isinstance(raw_failing_stage, str) else None

    return MatrixRow(
        adapter=adapter,
        status=status,
        adapter_version=adapter_version,
        harness_version=harness_version,
        date=date,
        failing_stage=failing_stage,
        stale=stale,
    )


def render_matrix_markdown(rows: Iterable[MatrixRow], *, hostname: str, generated_at: str) -> str:
    """Pure markdown-table rendering (Story 6.6, FR-45) -- no I/O (AD-4);
    `cli/adapters.py::run_adapters_matrix` writes the returned text to the
    ONE tracked, per-host path AD-37's F-7 amendment names. Rows sort by
    adapter name for a deterministic diff across runs."""
    lines = [
        f"# Adapter conformance matrix -- {hostname}",
        "",
        f"Generated: {generated_at}",
        "",
        "| Adapter | Status | Adapter version | Harness version | Date | Failing stage | Stale |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in sorted(rows, key=lambda entry: entry.adapter):
        lines.append(
            "| "
            + " | ".join(
                [
                    row.adapter,
                    row.status,
                    row.adapter_version or "-",
                    row.harness_version or "-",
                    row.date or "-",
                    row.failing_stage or "-",
                    "yes" if row.stale else "no",
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


# =====================================================================
# Story 6.7 -- entry-file family drift check, detect-only (FR-46, C-3,
# AD-11).
# =====================================================================
#
# This repo's own cross-tool "entry-file family": AGENTS.md is the declared
# hub (the cross-tool entry point), and each of the other four is a
# per-tool satellite pointer at THAT tool's own conventional path. Ownership
# between stations for these shared, repo-level files is unsettled (C-3/
# AD-11) -- Marshal never edits one; this concern is detection only.
#
# Family membership is a declared table, never inline branching on a
# filename literal (the AC's own "family membership is configuration, not
# a literal") -- mirrors `MECHANISM_CHECKERS`'s own "ONE table, one owner"
# shape. Hub first, by convention (`ENTRY_FILE_FAMILY[0]`).
ENTRY_FILE_FAMILY: tuple[str, ...] = (
    "AGENTS.md",
    "CLAUDE.md",
    ".cursor/rules/specs.mdc",
    "GEMINI.md",
    ".github/copilot-instructions.md",
)


@dataclass(frozen=True)
class EntryFileTool:
    """One CLI tool's own entry-file consumption contract: `reads` is the
    subset of `ENTRY_FILE_FAMILY` that tool's own runtime actually loads at
    session start. `len(reads) > 1` is exactly the AC's own "applies the
    union of two files" shape."""

    tool: str
    reads: tuple[str, ...]


# Confirmed against each tool's own documented behavior (this repo's own
# CLAUDE.md/AGENTS.md text): Claude Code reads `CLAUDE.md` directly, and
# `CLAUDE.md`'s own text documents `AGENTS.md` as the cross-tool hub it
# forwards to -- Claude Code applies the union of both. Cursor, Gemini, and
# Copilot each read only their own single satellite pointer.
ENTRY_FILE_TOOLS: tuple[EntryFileTool, ...] = (
    EntryFileTool("claude", ("CLAUDE.md", "AGENTS.md")),
    EntryFileTool("cursor", (".cursor/rules/specs.mdc",)),
    EntryFileTool("gemini", ("GEMINI.md",)),
    EntryFileTool("copilot", (".github/copilot-instructions.md",)),
)

_ENTRY_FILE_HUB: str = ENTRY_FILE_FAMILY[0]


@dataclass(frozen=True)
class EntryFileState:
    """One family member's already-read presence/content facts (Story 6.7)
    -- gathered by `cli/adapters.py::run_adapters_entry_files`, nothing is
    read here (AD-4). `mentions_hub` is `None` for the hub's own row (not
    applicable to itself) -- `True`/`False` for every satellite, per
    whether its content contains the hub's own filename as a substring."""

    path: str
    exists: bool
    mentions_hub: bool | None


@dataclass(frozen=True)
class EntryFileDivergence:
    """One detected divergence (Story 6.7) -- `affected_tools` is computed
    from `ENTRY_FILE_TOOLS` itself, never hand-listed per divergence.
    `cross_contaminating` is `True` exactly when at least one affected
    tool's own `reads` set has more than one member (the AC's own
    "cross-contaminating, not merely cosmetic" requirement, made
    structural)."""

    path: str
    detail: str
    affected_tools: tuple[str, ...]
    cross_contaminating: bool


def evaluate_entry_file_family(
    states: Mapping[str, EntryFileState],
    *,
    tools: Iterable[EntryFileTool] = ENTRY_FILE_TOOLS,
) -> tuple[EntryFileDivergence, ...]:
    """The pure, total classifier every caller uses (Story 6.7, FR-46): no
    I/O (AD-4) -- `states` is caller-supplied, keyed by `ENTRY_FILE_FAMILY`
    path. A missing `states` entry for a family member is treated the same
    as `exists=False` (never crashes on a partial read).

    A divergence is reported for a family member that is ABSENT, or
    (satellites only, never the hub itself) present but `mentions_hub is
    False` -- a satellite that has drifted away from forwarding to the hub
    is exactly the "instruction content is not isolated per-CLI" hazard
    this story targets. The hub's own `mentions_hub` field is never
    consulted (it is `None`, not applicable to itself)."""
    tools_tuple = tuple(tools)
    divergences: list[EntryFileDivergence] = []
    for path in ENTRY_FILE_FAMILY:
        state = states.get(path)
        affected_tools = tuple(sorted(tool.tool for tool in tools_tuple if path in tool.reads))
        cross_contaminating = any(
            path in tool.reads and len(tool.reads) > 1 for tool in tools_tuple
        )
        if state is None or not state.exists:
            divergences.append(
                EntryFileDivergence(
                    path=path,
                    detail=f"{path!r} is absent",
                    affected_tools=affected_tools,
                    cross_contaminating=cross_contaminating,
                )
            )
            continue
        if path != _ENTRY_FILE_HUB and state.mentions_hub is False:
            divergences.append(
                EntryFileDivergence(
                    path=path,
                    detail=f"{path!r} exists but no longer references the hub {_ENTRY_FILE_HUB!r}",
                    affected_tools=affected_tools,
                    cross_contaminating=cross_contaminating,
                )
            )
    return tuple(divergences)
