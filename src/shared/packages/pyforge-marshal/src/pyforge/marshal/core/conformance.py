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
    adapter: str, report: SmokeReport, *, binary: str, binary_present: bool
) -> dict[str, object]:
    """Shape an already-classified `SmokeReport` (Story 6.5, FR-44) into the
    plain dict `cli/adapters.py::run_adapters_smoke` reports as `data.smoke`
    and (after routing through `core.egress.to_redacted` at the write
    boundary -- never here, AD-4) persists to the machine-scoped smoke
    record file. Mirrors `build_probe_record`'s own "the caller already
    gathered every fact, this function only shapes" convention -- no I/O, no
    redaction."""
    return {
        "adapter": adapter,
        "binary": binary,
        "binary_present": binary_present,
        "status": report.status,
        "failing_stage": report.failing_stage,
        "detail": report.detail,
    }
