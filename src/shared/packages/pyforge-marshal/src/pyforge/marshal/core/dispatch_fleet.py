"""Fleet-wide drain planning (Story 22.7, FR-193 CAP-7).

Pure functions only (AD-4): campaign-mode parsing, per-station backlog
derivation from an already-read tracked ``sprint-status-ledger.yaml``, order
overrides, and the per-cycle queue decision. Every impure step -- reading a
ledger, judging a dispatch's liveness, launching a session, journaling a
cycle -- lives in ``cli/dispatch.py``.

This module owns NO dispatch, in-flight, verification, or landing logic: the
fleet mode composes ``cli/dispatch.py``'s already-shipped
``dispatch_once``/``station_in_flight_conflict``/
``cross_station_surface_overlap_advisories`` (Stories 22.1/22.2/22.5) and the
CAP-4 landing path a dispatched run's own supervisor already drives. It only
decides WHICH story a station should be handed next.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from pyforge.core.errors import PyforgeError

from .dispatch import canonical_repo_root, find_declared_surface_overlaps
from .identity import MalformedStoryKeyError, StoryKey, normalize
from .spec_deps import ready_backlog, story_transitively_depends_on

#: Journal kind for one fleet-drain cycle (intent/outcome pair).
KIND_FLEET_CYCLE = "dispatch-fleet-cycle"

#: The campaign journal lives under the marshal station's own run store --
#: the Spec's "in-repo under ``pyforge-marshal``, never session-local
#: ``.cursor/``" subsumption target. A DEDICATED directory, never the
#: per-story ``dispatch-runs/`` tree: ``latest_dispatch_run_dir`` /
#: ``station_in_flight_conflict`` walk that tree expecting per-story launch
#: journals, and a campaign run mixed in there would shadow the marshal
#: station's own latest dispatch run for ``dispatch-attach``/``-resume``.
FLEET_JOURNAL_SLUG = "pyforge-marshal"
_FLEET_RUNS_DIRNAME = "fleet-drain-runs"

#: Optional, hand-maintained order overrides + skip policies -- the in-repo
#: analog of the interim runner's ``.cursor/pyforge-fleet-drain/queues.yaml``
#: ``order_overrides``/``skip_policies`` blocks. Absent by default: the
#: tracked ledgers ARE the queue, and story-key order is the default order.
QUEUE_CONFIG_FILENAME = "fleet-drain-queue.yaml"

#: Station slugs this mode drains -- derived from the projects tree, never a
#: hardcoded eight-tuple (the interim runner's ``STATIONS`` constant is
#: exactly the shape that omits the newest station).
STATION_SLUG_PREFIX = "pyforge-"

#: The one ledger status that means "not in the backlog any more".
DONE_STATUS = "done"
#: Land/promote only — not a new implement session. ``review`` after merge
#: is still not ``done``, but re-dispatching it re-ran whole stories.
#: ``blocked`` is an operator hold (e.g. steward 43.6 waiting on mason 13.x)
#: — never an implementable drain head.
NON_IMPLEMENT_STATUSES = frozenset({DONE_STATUS, "review", "blocked"})

#: CAP-4 land-only refusal after a harness-done spec (Story 29.2). Not a
#: station-terminal derived block: the ledger often still says ``backlog``
#: until isolated promote, and treating 040 as BLOCKED exits ``drain_to_zero``.
HARNESS_DONE_ADVANCE_CODE = "MRS-DISP-040"


def is_harness_done_advance_reason(reason: str) -> bool:
    """True when a campaign-block reason is harness-done CAP-4 (MRS-DISP-040)."""
    return reason.startswith(HARNESS_DONE_ADVANCE_CODE)


#: Story 50.1 (CAP-244) Part B: a most-recent run that refused ITSELF because
#: the work was already merged. A plain sentinel, never an ``MRS-`` finding
#: code: nothing is refused here and no new code is registered -- the skip
#: still surfaces as ``MRS-DRAIN-004`` exactly the way harness-done does.
ALREADY_LANDED_ADVANCE_PREFIX = "already-landed"

#: Advance, never block: both families mean "this head cannot be worked, and
#: the station's remaining backlog must still dispatch".
ADVANCE_REASON_PREFIXES: tuple[str, ...] = (
    HARNESS_DONE_ADVANCE_CODE,
    ALREADY_LANDED_ADVANCE_PREFIX,
)


def is_advance_reason(reason: str) -> bool:
    """True when a campaign-block reason is an ADVANCE reason (Story 50.1).

    One test for both families so ``plan_station_queue`` keeps exactly one
    skip-under-every-mode branch rather than growing one per family.
    """
    return any(reason.startswith(prefix) for prefix in ADVANCE_REASON_PREFIXES)


def is_finalize_pending(
    *,
    supervisor_alive: bool,
    completion_journaled: bool,
    landing_complete: bool,
    story_on_backlog: bool,
) -> bool:
    """Is this station's most recent run still finalizing? (Story 50.1 Part A).

    The ~45 s window between a dispatch session exiting and
    ``dispatch_land_finalize`` promoting the tracked ledger is neither
    "live" (``resolve_dispatch_session_verdict`` reads ``session_pid``
    only) nor "done" (the ledger still says ``backlog``). Read as either,
    the campaign re-dispatches the story it just landed or blocks the
    station on a ``failed`` verdict. Read as IN FLIGHT, it simply chains the
    next ready story on the following cycle.

    Both clauses require ``story_on_backlog``, and clause (a) requires a
    LIVE supervisor, so this is self-limiting by construction: a supervisor
    that dies without journaling completion is not pending, and ledger
    promotion ends the condition on the very next cycle.
    """
    if not story_on_backlog:
        return False
    if landing_complete:
        # (b) dispatch-land journaled a successful CAP-4 outcome, but the
        # tracked ledger has not moved yet -- finalize is mid-flight.
        return True
    # (a) the supervisor is alive and has not journaled dispatch-completion.
    return supervisor_alive and not completion_journaled


#: Merged-evidence phrases a self-refusing session leaves in its own log.
_MERGED_EVIDENCE_PHRASES: tuple[str, ...] = (
    "already merged",
    "already landed",
    "already_landed",
    # bmad-build-auto's HALT wording when it finds the spec already done.
    "follow-up not recommended",
)

#: ``/pull/<n>`` or ``#<n>`` -- only counted on a line that also says "merged".
_PR_REFERENCE_RE = re.compile(r"/pull/\d+|#\d+")


def is_already_landed_self_refusal(*, changed_path_count: int, session_log: str | None) -> bool:
    """Did this failed dispatch refuse itself over already-merged work? (50.1).

    Two independent facts must agree: the campaign's OWN git observation
    that the session changed nothing (``changed_path_count == 0``), and
    merged evidence in the session log. The session is never believed about
    whether it *succeeded* -- git remains the sole authority for merged
    facts (Epic 50 HARD boundary). This only decides whether the CAMPAIGN
    halts a station or steps past a head it has independent reason to think
    is already landed.
    """
    if changed_path_count != 0:
        return False
    if not session_log:
        return False
    lowered = session_log.lower()
    if any(phrase in lowered for phrase in _MERGED_EVIDENCE_PHRASES):
        return True
    return any("merged" in line and _PR_REFERENCE_RE.search(line) for line in lowered.splitlines())


class FleetCampaignMode(StrEnum):
    """The three named campaign modes (CAP-7 / fleet-drain-playbook.md)."""

    DRAIN_TO_ZERO = "drain_to_zero"
    LEAVE_ONE = "leave_one"
    SKIP_ON_BLOCKED = "skip_on_blocked"


CAMPAIGN_MODES: tuple[str, ...] = tuple(mode.value for mode in FleetCampaignMode)


class InvalidCampaignModeError(PyforgeError, ValueError):
    """Raised for a missing or unrecognized ``--mode`` -- never defaulted."""


def parse_campaign_mode(raw: str | None) -> FleetCampaignMode:
    """The sole campaign-mode parser.

    A missing mode is refused exactly as loudly as an unknown one: the I/O
    matrix's "never silently default to ``drain_to_zero``" is the whole point
    of this function existing instead of an ``argparse`` default.
    """
    named = ", ".join(CAMPAIGN_MODES)
    if raw is None or not str(raw).strip():
        raise InvalidCampaignModeError(
            f"campaign mode is required: pass --mode with one of {named} -- a fleet drain never defaults to a mode"
        )
    try:
        return FleetCampaignMode(str(raw).strip())
    except ValueError as exc:
        raise InvalidCampaignModeError(f"unknown campaign mode {raw!r}: expected one of {named}") from exc


class FleetBlockClass(StrEnum):
    """Whether a derived fleet block is infrastructure or story work (Story 34.3)."""

    ENVIRONMENT = "environment"
    STORY = "story"


@dataclass(frozen=True)
class StationBlockEvidence:
    """One derived block with its environment/story classification."""

    reason: str
    block_class: FleetBlockClass


class StationQueueOutcome(StrEnum):
    """What this cycle's queue walk decided for one station."""

    #: Zero non-``done`` story keys in the tracked ledger.
    DRAINED = "drained"
    #: A story is eligible; the caller dispatches it.
    DISPATCH = "dispatch"
    #: ``leave_one``: the configured tail is deliberately left untouched.
    LEFT_REMAINING = "left-remaining"
    #: The next story is blocked and the mode does not skip past it.
    BLOCKED = "blocked"
    #: Every remaining story was skipped under ``skip_on_blocked``.
    ALL_SKIPPED = "all-skipped"


class StationCycleStatus(StrEnum):
    """What actually happened to one station in one cycle."""

    DRAINED = "drained"
    LEFT_REMAINING = "left-remaining"
    BLOCKED = "blocked"
    ALL_SKIPPED = "all-skipped"
    LEDGER_UNREADABLE = "ledger-unreadable"
    DISPATCHED = "dispatched"
    #: A live in-flight story (CAP-2 facts) held the station's one slot.
    IN_FLIGHT = "in-flight"
    #: Dispatch was refused for a reason that is not liveness.
    REFUSED = "refused"


#: Statuses from which this campaign can make no further progress on a
#: station. ``IN_FLIGHT``/``DISPATCHED`` are deliberately absent: those
#: stations are working, and the next cycle chains their next story once
#: merge-through-finalize advances the tracked ledger.
TERMINAL_STATION_STATUSES: frozenset[StationCycleStatus] = frozenset(
    {
        StationCycleStatus.DRAINED,
        StationCycleStatus.LEFT_REMAINING,
        StationCycleStatus.BLOCKED,
        StationCycleStatus.ALL_SKIPPED,
        StationCycleStatus.LEDGER_UNREADABLE,
    }
)


@dataclass(frozen=True)
class StationQueuePlan:
    """One station's decision for one cycle (pure)."""

    slug: str
    backlog: tuple[str, ...]
    outcome: StationQueueOutcome
    next_story: str | None = None
    blocked_story: str | None = None
    blocked_reason: str | None = None
    skipped: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class MissingSpecEscalation:
    """One station blocked on ``MRS-DISP-005`` with remaining backlog (28.19)."""

    story: str
    expected_spec_glob: str


@dataclass(frozen=True)
class FinalizeEscalation:
    """Supervisor finalize shell failed — operator must act in the worktree (28.24)."""

    story: str
    worktree_path: str


@dataclass(frozen=True)
class StationCycleResult:
    """One station's observed outcome for one cycle (journal payload shape)."""

    slug: str
    status: StationCycleStatus
    remaining: int
    story: str | None = None
    detail: str | None = None
    skipped: tuple[tuple[str, str], ...] = field(default=())
    refuse_predicate: dict[str, str] | None = None

    def to_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "station": self.slug,
            "status": self.status.value,
            "remaining": self.remaining,
            "story": self.story,
            "detail": self.detail,
            "skipped": [{"story": s, "reason": r} for s, r in self.skipped],
        }
        if self.refuse_predicate is not None:
            payload["refuse_predicate"] = dict(self.refuse_predicate)
        return payload


def fleet_station_slugs(slugs: Iterable[str]) -> tuple[str, ...]:
    """The pyforge stations among ``slugs``, in stable order (Story 22.7).

    Derived from ``core.dispatch.list_station_slugs``' live enumeration of
    ``_bmad-output/projects/``, never declared -- a ninth station joins the
    drain by existing, not by editing a tuple.
    """
    return tuple(sorted(s for s in slugs if s.startswith(STATION_SLUG_PREFIX)))


def station_ledger_path(repo_root: Path, slug: str) -> Path:
    """The TRACKED ``sprint-status-ledger.yaml`` twin for ``slug``."""
    return (
        canonical_repo_root(repo_root)
        / "_bmad-output"
        / "projects"
        / slug
        / "planning-artifacts"
        / "sprint-status-ledger.yaml"
    )


def fleet_runs_dir(repo_root: Path) -> Path:
    return (
        canonical_repo_root(repo_root)
        / "_bmad-output"
        / "projects"
        / FLEET_JOURNAL_SLUG
        / "implementation-artifacts"
        / _FLEET_RUNS_DIRNAME
    )


def fleet_run_dir(repo_root: Path, run_id: str) -> Path:
    return fleet_runs_dir(repo_root) / run_id


def latest_fleet_campaign_run_id(repo_root: Path) -> str | None:
    """Most recent fleet-drain campaign id, or ``None`` when no campaigns exist."""
    runs = fleet_runs_dir(repo_root)
    if not runs.is_dir():
        return None
    candidates = sorted(entry.name for entry in runs.iterdir() if entry.is_dir() and entry.name != "campaign")
    return candidates[-1] if candidates else None


def fleet_cycle_lock_path(repo_root: Path) -> Path:
    """The FLEET-WIDE cycle-lock path (``FsPort.acquire_advisory_lock``
    locks a ``.lock`` sibling of this, never this path itself).

    Deliberately NOT scoped to a campaign id: the failure this serializes is
    two *different* campaigns racing on the same station, so a per-campaign
    lock would let exactly the case it exists to prevent straight through.
    """
    return fleet_runs_dir(repo_root) / "campaign"


def queue_config_path(repo_root: Path) -> Path:
    """The optional in-repo order-override / skip-policy file."""
    return (
        canonical_repo_root(repo_root)
        / "_bmad-output"
        / "projects"
        / FLEET_JOURNAL_SLUG
        / "planning-artifacts"
        / QUEUE_CONFIG_FILENAME
    )


def normalize_station_slug(raw: str) -> str:
    """``steward`` and ``pyforge-steward`` both name the steward station."""
    text = str(raw).strip()
    return text if text.startswith(STATION_SLUG_PREFIX) else f"{STATION_SLUG_PREFIX}{text}"


# Story 28.12 (CAP-14): dependency-derived dispatch ordering. Regex shapes
# mirror ``pyforge.doctor.sources.deps`` -- marshal restates them (AD-13) so
# core stays doctor-free; the conformance test pins parity separately.
_STORY_HEADING_RE = re.compile(
    r"^### Story (?P<pe>\d+)\.(?P<pn>\d+[a-z]?): ?"
    r"(?P<title>.*?)(?:\s*\*\(.*?\)\*)?\s*$",
    re.M,
)
_DEPS_FIELD_RE = re.compile(r"\*\*(?:Deps|Depends on):\*\* ?(.*?)(?:\s*•|\n|$)")
_DEP_RE = re.compile(
    r"(?:(?P<station>[a-z][a-z0-9-]*):)?S-(?P<epic>\d+)\.(?P<num>\d+[a-z]?|\*)",
    re.I,
)
_NO_DEP_RE = re.compile(r"^\s*(?:—|–|-|none|nothing|n/?a)(?![\w-])", re.I)


@dataclass(frozen=True)
class ParsedStoryDeps:
    """One story's machine-readable dependency declaration."""

    story_keys: tuple[StoryKey, ...] = ()
    whole_epics: tuple[int, ...] = ()


def station_epics_paths(repo_root: Path, slug: str) -> tuple[Path, ...]:
    """Every epics-family doc for ``slug`` that can carry a ``**Deps:**`` field."""
    planning = canonical_repo_root(repo_root) / "_bmad-output" / "projects" / slug / "planning-artifacts"
    if not planning.is_dir():
        return ()
    # The glob stays: it also matches chain-scoped epics (this station's own
    # epics-regenerable-factory.md, mason's epics-presenton-pixi-image.md). The
    # epics-with-stories.md exclusion was dropped 2026-09-07 with the file itself
    # (Story 32.4, spec-fleet-consistency-standard CAP-3).
    return tuple(sorted(planning.glob("epics*.md")))


def _story_key_from_dep_num(epic: int, num: str) -> StoryKey | None:
    if num == "*":
        return None
    match = re.fullmatch(r"(\d+)([a-z]?)", num, re.I)
    if match is None:
        return None
    suffix = (match.group(2) or "").lower()
    return StoryKey(epic=epic, seq=int(match.group(1)), suffix=suffix)


def parse_epics_dependencies(epics_text: str) -> dict[StoryKey, ParsedStoryDeps]:
    """``{declaring_story: parsed_deps}`` from one epics-family document."""
    headings = list(_STORY_HEADING_RE.finditer(epics_text))
    out: dict[StoryKey, ParsedStoryDeps] = {}
    for index, match in enumerate(headings):
        block_end = headings[index + 1].start() if index + 1 < len(headings) else len(epics_text)
        block = epics_text[match.end() : block_end]
        declaring = _story_key_from_dep_num(int(match.group("pe")), match.group("pn"))
        if declaring is None:
            continue
        deps_match = _DEPS_FIELD_RE.search(block)
        deps_text = deps_match.group(1).strip() if deps_match else ""
        if not deps_text or _NO_DEP_RE.match(deps_text):
            out[declaring] = ParsedStoryDeps()
            continue
        story_keys: list[StoryKey] = []
        whole_epics: list[int] = []
        for dep_match in _DEP_RE.finditer(deps_text):
            if dep_match.group("station"):
                continue
            epic = int(dep_match.group("epic"))
            num = dep_match.group("num")
            if num == "*":
                whole_epics.append(epic)
                continue
            parsed = _story_key_from_dep_num(epic, num)
            if parsed is not None:
                story_keys.append(parsed)
        out[declaring] = ParsedStoryDeps(
            story_keys=tuple(story_keys),
            whole_epics=tuple(sorted(set(whole_epics))),
        )
    return out


def dependency_ordered_backlog(
    backlog: Sequence[str],
    *,
    deps_by_story: Mapping[StoryKey, ParsedStoryDeps],
) -> tuple[str, ...]:
    """Topological order over ``backlog`` honoring declared ``Deps:`` edges.

    Tie-break among ready stories is ledger order (``backlog``'s own sequence),
    never story-key sort or an invented preference. Cycles fall back to ledger
    order for the unresolved tail so empty/single-story backlogs never crash.
    """
    ordered = tuple(backlog)
    if len(ordered) <= 1:
        return ordered

    ledger_index = {raw: index for index, raw in enumerate(ordered)}
    key_to_raw: dict[StoryKey, str] = {}
    raw_to_key: dict[str, StoryKey] = {}
    for raw in ordered:
        try:
            key = normalize(raw)
        except MalformedStoryKeyError:
            continue
        key_to_raw[key] = raw
        raw_to_key[raw] = key

    predecessors: dict[str, set[str]] = {raw: set() for raw in ordered}
    successor_count: dict[str, int] = {raw: 0 for raw in ordered}

    for raw in ordered:
        declaring = raw_to_key.get(raw)
        if declaring is None:
            continue
        parsed = deps_by_story.get(declaring, ParsedStoryDeps())
        for dep_key in parsed.story_keys:
            dep_raw = key_to_raw.get(dep_key)
            if dep_raw is not None and dep_raw != raw:
                if raw not in predecessors[dep_raw]:
                    predecessors[dep_raw].add(raw)
                    successor_count[raw] += 1
        for epic in parsed.whole_epics:
            for other_raw, other_key in raw_to_key.items():
                if other_raw == raw:
                    continue
                if other_key.epic == epic:
                    if raw not in predecessors[other_raw]:
                        predecessors[other_raw].add(raw)
                        successor_count[raw] += 1

    ready = sorted(
        (raw for raw in ordered if successor_count[raw] == 0),
        key=lambda raw: ledger_index[raw],
    )
    result: list[str] = []
    while ready:
        current = ready.pop(0)
        result.append(current)
        for successor in sorted(predecessors[current], key=lambda raw: ledger_index[raw]):
            successor_count[successor] -= 1
            if successor_count[successor] == 0:
                ready.append(successor)
        ready.sort(key=lambda raw: ledger_index[raw])

    if len(result) < len(ordered):
        seen = set(result)
        result.extend(raw for raw in ordered if raw not in seen)
    return tuple(result)


def _sort_key(raw_key: str) -> tuple[StoryKey, str]:
    # Story-key order, never lexicographic: the interim runner's plain
    # `sorted()` put "10-1-..." ahead of "2-1-...". A key that reaches here
    # has already passed `normalize` in `station_backlog`.
    return (normalize(raw_key), raw_key)


def station_backlog(
    statuses: Iterable[tuple[str, str]],
    *,
    order_override: Sequence[str] | None = None,
    deps_by_story: Mapping[StoryKey, ParsedStoryDeps] | None = None,
) -> tuple[str, ...]:
    """The station's ordered backlog from its tracked ledger's pairs.

    ``statuses`` is ``HarnessPort.ledger_story_statuses``' raw
    ``(key, status)`` output -- this function never reads a file, and never
    sees ``.cursor/pyforge-fleet-drain/queues.yaml``. A key that does not
    normalize is skipped (the established Epic 5 convention), never a crash.

    Story 28.12: when ``order_override`` is absent and ``deps_by_story`` was
    successfully loaded from the station's epics doc, dispatch order is a
    topological sort over declared ``Deps:`` edges with ledger order as the
    tie-break. ``order_override`` and caller ``--stories`` paths are unchanged.
    """
    backlog: list[str] = []
    for raw_key, raw_status in statuses:
        if not isinstance(raw_key, str):
            continue
        if str(raw_status).strip().lower() in NON_IMPLEMENT_STATUSES:
            continue
        try:
            normalize(raw_key)
        except MalformedStoryKeyError:
            continue
        backlog.append(raw_key)
    raw_backlog = tuple(backlog)
    if order_override:
        return apply_order_override(raw_backlog, order_override)
    if deps_by_story is not None:
        return dependency_ordered_backlog(raw_backlog, deps_by_story=deps_by_story)
    return apply_order_override(raw_backlog, None)


def apply_order_override(backlog: Sequence[str], override: Sequence[str] | None) -> tuple[str, ...]:
    """Override entries first (in override order), then the rest by story key.

    The override file is hand-maintained, so a repeated key is a plausible
    edit: de-duplicated here rather than passed through, since a backlog
    carrying the same story twice inflates ``remaining`` and re-plans a
    story already dispatched this cycle. An override entry naming a key that
    is not in the backlog (a typo, or a story since marked ``done``) is
    simply inert.
    """
    if not override:
        return tuple(sorted(backlog, key=_sort_key))
    present: list[str] = []
    seen: set[str] = set()
    for key in override:
        if key in backlog and key not in seen:
            seen.add(key)
            present.append(key)
    tail = sorted((key for key in backlog if key not in seen), key=_sort_key)
    return tuple(present + tail)


def parse_story_sequence(raw: str) -> tuple[str, ...]:
    """Split ``--stories``' comma-separated value into ordered raw entries
    (Story 22.11, FR-193 CAP-10).

    Blank segments (a trailing comma, doubled commas, surrounding
    whitespace) are dropped rather than becoming an empty-string key that
    fails ``normalize()`` with a confusing message.
    """
    return tuple(part.strip() for part in str(raw).split(",") if part.strip())


def unresolved_story_sequence_keys(stories: Sequence[str], backlog: Sequence[str]) -> tuple[str, ...]:
    """Which caller-supplied ``--stories`` entries are NOT eligible to
    dispatch (Story 22.11, FR-193 CAP-10).

    An entry is eligible when it normalizes to a ``StoryKey`` matching (by
    normalized identity, never raw string equality) some entry in the
    station's own tracked, not-yet-``done`` ``backlog`` -- the same source
    ``station_backlog`` reads. A malformed entry, an unknown key, or a key
    already ``done`` on the tracked ledger are all "not eligible": ``done``
    keys are already absent from ``backlog`` (``station_backlog`` drops
    them), so no separate done-check is needed. Empty return means every
    key is eligible -- the caller refuses BEFORE any worktree is
    provisioned when this is non-empty, never partway through the sequence.
    """
    backlog_keys: set[StoryKey] = set()
    for raw in backlog:
        try:
            backlog_keys.add(normalize(raw))
        except MalformedStoryKeyError:
            continue
    unresolved: list[str] = []
    for raw in stories:
        try:
            key = normalize(raw)
        except MalformedStoryKeyError:
            unresolved.append(raw)
            continue
        if key not in backlog_keys:
            unresolved.append(raw)
    return tuple(unresolved)


def explicit_story_backlog(statuses: Iterable[tuple[str, str]], stories: Sequence[str]) -> tuple[str, ...]:
    """The caller's own ``--stories`` sequence, filtered to not-yet-``done``
    (Story 22.11, FR-193 CAP-10) -- the effective backlog for a
    ``dispatch --stories`` campaign.

    Unlike ``station_backlog``'s ``order_override`` (which reorders the
    FULL ledger backlog and leaves the untouched tail after it), this IS
    the entire effective backlog: only the caller's own keys, in the
    caller's own order, never the rest of the station's tracked backlog.
    Re-derived every cycle from the LIVE ``statuses``, exactly as
    ``station_backlog`` is, so a key that lands mid-campaign naturally
    advances the head to the next one.
    """
    done: set[StoryKey] = set()
    for raw_key, raw_status in statuses:
        if not isinstance(raw_key, str):
            continue
        if str(raw_status).strip().lower() != DONE_STATUS:
            continue
        try:
            done.add(normalize(raw_key))
        except MalformedStoryKeyError:
            continue
    backlog: list[str] = []
    for raw in stories:
        try:
            key = normalize(raw)
        except MalformedStoryKeyError:
            continue
        if key in done:
            continue
        backlog.append(raw)
    return tuple(backlog)


def has_review_verify_cycle_evidence(
    *,
    verification_verdict: str | None,
    verification_failed_gate: str | None,
    completion_stop_reason: str | None,
) -> bool:
    """True when the last dispatch left review/verify-cycle evidence (Story 34.3)."""
    if verification_failed_gate:
        return True
    if verification_verdict in {"verified", "failed", "refused"}:
        return True
    if completion_stop_reason and "escalation" in completion_stop_reason.lower():
        return True
    return False


def classify_fleet_block(
    *,
    changed_path_count: int,
    has_review_verify_evidence: bool,
) -> FleetBlockClass:
    """Pure: environment when the session died before real story work began."""
    if changed_path_count == 0 and not has_review_verify_evidence:
        return FleetBlockClass.ENVIRONMENT
    return FleetBlockClass.STORY


def plan_station_queue(
    *,
    slug: str,
    backlog: Sequence[str],
    mode: FleetCampaignMode,
    leave_remaining: int = 1,
    blocked: Mapping[str, str] | None = None,
    block_classes: Mapping[str, FleetBlockClass] | None = None,
    retry_environment_blocks: bool = False,
    declared_skips: Mapping[str, str] | None = None,
) -> StationQueuePlan:
    """Decide this cycle's story for one station (pure).

    Two kinds of "not this story", deliberately NOT the same thing:

    * ``declared_skips`` -- the operator's own hand-authored instruction
      ("steward 12-7 needs a live OCP cluster"), the in-repo analog of the
      interim runner's ``skip_policies`` entries, every one of which carried
      ``action: skip_on_blocked``. A declared skip is honored under EVERY
      mode: the 2026-08-22/23 campaign ran ``mode: drain_to_zero`` WITH those
      seven steward skip policies, and skipping to 12-8 is exactly the
      outcome the hand ritual produced. Treating an explicit "don't try this
      one" as "halt the whole station" would make replaying that campaign
      impossible in its own mode.
    * ``blocked`` -- DERIVED evidence that a story may not be dispatched:
      CAP-2 git/process facts showing its last dispatch ended ``failed``, or
      a non-liveness refusal this campaign already recorded. Story 34.3
      classifies each derived block as ``environment`` (zero git progress and
      zero review/verify-cycle evidence) or ``story`` (everything else).
      ``skip_on_blocked`` steps past **environment** blocks only; genuine
      story failures still halt the station. ``retry_environment_blocks``
      applies the same environment-only skip under ``drain_to_zero`` /
      ``leave_one``.
    * ``MRS-DISP-040`` (harness-done, CAP-4 land-only) is recorded as a
      campaign block so the same story is never relaunched, but it is
      skipped under every mode the way a declared skip is: remaining
      implementable backlog must still dispatch. A real derived block
      (missing spec, CAP-2 failed) still stops ``drain_to_zero``.
    * ``ALREADY_LANDED_ADVANCE_PREFIX`` (Story 50.1 Part B) is the same
      shape one layer down: the head's most recent dispatch refused ITSELF
      over already-merged work (zero changed paths + merged evidence in its
      session log). Neither transient (re-dispatching it is the loop this
      story closes) nor terminal (the work is done) -- so it advances,
      through the same ``is_advance_reason`` test as ``MRS-DISP-040``.

    Neither kind is ever removed from the backlog or auto-retried -- both
    stay queued, reported by name, for a human.
    """
    ordered = tuple(backlog)
    blocked = dict(blocked or {})
    classes = dict(block_classes or {})
    declared = dict(declared_skips or {})
    if not ordered:
        return StationQueuePlan(slug=slug, backlog=ordered, outcome=StationQueueOutcome.DRAINED)
    if mode is FleetCampaignMode.LEAVE_ONE and len(ordered) <= max(0, leave_remaining):
        return StationQueuePlan(slug=slug, backlog=ordered, outcome=StationQueueOutcome.LEFT_REMAINING)
    skipped: list[tuple[str, str]] = []
    for story in ordered:
        declared_reason = declared.get(story)
        if declared_reason is not None:
            skipped.append((story, declared_reason))
            continue
        reason = blocked.get(story)
        if reason is None:
            return StationQueuePlan(
                slug=slug,
                backlog=ordered,
                outcome=StationQueueOutcome.DISPATCH,
                next_story=story,
                skipped=tuple(skipped),
            )
        if is_advance_reason(reason):
            skipped.append((story, reason))
            continue
        block_class = classes.get(story, FleetBlockClass.STORY)
        environment_retry = block_class is FleetBlockClass.ENVIRONMENT and (
            mode is FleetCampaignMode.SKIP_ON_BLOCKED or retry_environment_blocks
        )
        if environment_retry:
            skipped.append((story, reason))
            continue
        return StationQueuePlan(
            slug=slug,
            backlog=ordered,
            outcome=StationQueueOutcome.BLOCKED,
            blocked_story=story,
            blocked_reason=reason,
            skipped=tuple(skipped),
        )
    return StationQueuePlan(
        slug=slug,
        backlog=ordered,
        outcome=StationQueueOutcome.ALL_SKIPPED,
        skipped=tuple(skipped),
    )


def campaign_complete(results: Iterable[StationCycleResult]) -> bool:
    """True when no station can make further progress in this campaign.

    This is the SUPERVISOR'S STOP SIGNAL -- "nothing more this campaign can
    do", not "everything drained". A station whose ledger will not read, or
    whose head story is blocked, is terminal *for this campaign* precisely
    because marshal cannot fix it by ticking again; ``unresolved_stations``
    below is what keeps that honest in the operator's report.

    An empty fleet counts as complete (nothing to drain). A station that was
    dispatched or is in flight is progress, so the campaign continues.
    """
    return all(result.status in TERMINAL_STATION_STATUSES for result in results)


def unresolved_stations(
    results: Iterable[StationCycleResult],
) -> tuple[StationCycleResult, ...]:
    """Terminal-but-NOT-drained stations -- what "complete" does not cover.

    ``campaign_complete`` answers "can this campaign still act?", which is
    the right signal for the supervisor and the wrong one to hand an
    operator on its own: a fleet whose last unread ledger went terminal
    reports complete while real backlog goes unattended. Every station here
    still has work, and every one of them is already named by its own
    ``MRS-DRAIN-003``/``-004``/``-005`` finding.
    """
    return tuple(
        result
        for result in results
        if result.status in TERMINAL_STATION_STATUSES and result.status is not StationCycleStatus.DRAINED
    )


@dataclass(frozen=True)
class WaveRefused:
    """One story refused from a parallel wave batch (Story 28.16, CAP-3)."""

    story: str
    reason: str
    overlap_with: str | None = None
    paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class WaveBatch:
    """Up to ``cap`` ready stories with pairwise disjoint surfaces (CAP-1)."""

    wave_id: str
    members: tuple[str, ...]
    refused: tuple[WaveRefused, ...] = ()
    max_parallel: int = 1


def _surface_known(surface: tuple[str, ...] | None) -> bool:
    """``None`` means unknown/undeclared -- never fan out (CAP-5)."""
    return surface is not None


def _pairwise_disjoint(left: tuple[str, ...] | None, right: tuple[str, ...] | None) -> bool:
    if left is None or right is None:
        return False
    return not find_declared_surface_overlaps(left, right)


def build_wave_batch(
    *,
    wave_id: str,
    ready: Sequence[str],
    cap: int,
    surfaces: Mapping[str, tuple[str, ...] | None],
    deps_graph: Mapping[str, tuple[StoryKey, ...]] | None = None,
) -> WaveBatch:
    """Select up to ``cap`` pairwise-disjoint ready stories (Story 28.16).

    ``surfaces`` maps feed story key -> effective frozen surface tuple, or
    ``None`` when unknown. Stories with unknown surfaces are skipped for
    batching (conservative default, CAP-5). ``batch_deps`` holds story keys
    already chosen in this batch -- a candidate that transitively depends on
    any batch member is refused with reason ``dep-unmet``.
    """
    if cap <= 1:
        if not ready:
            return WaveBatch(wave_id=wave_id, members=(), max_parallel=cap)
        return WaveBatch(wave_id=wave_id, members=(ready[0],), max_parallel=cap)
    members: list[str] = []
    refused: list[WaveRefused] = []
    for story in ready:
        if len(members) >= cap:
            refused.append(WaveRefused(story=story, reason="cap"))
            continue
        surface = surfaces.get(story)
        if not _surface_known(surface):
            refused.append(WaveRefused(story=story, reason="unknown-surface"))
            continue
        blocked = False
        for member in members:
            member_surface = surfaces.get(member)
            if deps_graph is not None and story_transitively_depends_on(story, member, deps_graph):
                refused.append(WaveRefused(story=story, reason="dep-unmet"))
                blocked = True
                break
            if not _pairwise_disjoint(surface, member_surface):
                overlap = find_declared_surface_overlaps(surface, member_surface)
                paths = tuple(f"{left} ∩ {right}" for left, right in overlap)
                refused.append(
                    WaveRefused(
                        story=story,
                        reason="surface-overlap",
                        overlap_with=member,
                        paths=paths,
                    )
                )
                blocked = True
                break
        if blocked:
            continue
        members.append(story)
    return WaveBatch(
        wave_id=wave_id,
        members=tuple(members),
        refused=tuple(refused),
        max_parallel=cap,
    )


def ordered_ready_backlog(
    backlog: Sequence[str],
    statuses: Iterable[tuple[str, str]],
    graph: Mapping[str, tuple[StoryKey, ...]],
) -> tuple[str, ...]:
    """Ready-set among ``backlog``, preserving backlog order (28.12 tie-break)."""
    return ready_backlog(backlog, statuses, graph)


def render_cycle_summary(results: Sequence[StationCycleResult]) -> str:
    """One line per station -- the marshal-native replacement for the interim
    runner's hand-maintained ``STATUS.md`` snapshot."""
    lines: list[str] = []
    for result in results:
        story = result.story or "—"
        lines.append(f"  {result.slug:<18} {result.status.value:<18} remaining={result.remaining:<4} story={story}")
    return "\n".join(lines)
