"""``core/chain_regen.py`` (Story 17.4, FR-148/FR-149/FR-151, AD-72).

Pure orchestration types + helpers for one named project's planning-chain
regeneration. No I/O beyond what callers pass in: the CLI loads the
promote-sprint-status guard, runs an injectable phase runner in dependency
order, applies the existing ``regressions`` guard before any ledger write,
and reports orphans without deleting them.

Story 17.4 owns the four-phase dry-run contract (order, guard reuse, orphan
report, per-project scope). Story 21.2 extends this module with the Full /
minimal orchestrated chain (journal resume, FR-52 skill seam, orphan
manifest). Story 21.3 implements CAP-2 code-status preservation (snapshot
before regen; re-apply after epics by stable story id; default on; never
auto-commit). Story 21.4 implements CAP-4 review-gated orphan cleanup
(``orphans.json``/``.md`` always; disk deletes only with ``--apply-orphans``;
optional ``--stage`` indexes regenerated + orphan-rm paths; never commit /
push). Story 21.5 (FR-192 CAP-5) documents the per-station parameter surface
so the same workflow runs against any project by ``project`` / dream /
``mode`` / preserve / stage / apply_orphans / resume only — never a
hardcoded station slug, never ``scripts/bmad-switch``, never auto-commit.
"""

from __future__ import annotations

import json
import re
import shutil
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Protocol

PhaseName = Literal["spec", "prd", "architecture", "epics"]
PhaseStatus = Literal["done", "skipped", "failed"]
OrphanKind = Literal["spec", "epic"]

# Dependency order for CAP-1's core skill chain (research/brief deferred to
# Epic 21.2 / Q4 — no confirmed 1:1 skill mapping yet).
CHAIN_PHASES: tuple[PhaseName, ...] = ("spec", "prd", "architecture", "epics")

_PHASE_SKILLS: dict[PhaseName, str] = {
    "spec": "bmad-spec",
    "prd": "bmad-prd",
    "architecture": "bmad-architecture",
    "epics": "bmad-create-epics-and-stories",
}

_OWNER_DREAM_RE = re.compile(
    r"^owner-dream:\s*['\"]?([^\s'\"]+)['\"]?\s*$",
    re.MULTILINE,
)
# Epics prose often cites ``spec-<slug>`` (folder under planning-artifacts/specs/).
_SPEC_CITE_RE = re.compile(r"\bspec-([a-z0-9][a-z0-9-]*)\b", re.IGNORECASE)


@dataclass(frozen=True)
class PhaseOutcome:
    """One regeneration phase result (AD-21-style step status)."""

    name: PhaseName
    status: PhaseStatus
    detail: str = ""
    skill: str = ""


@dataclass(frozen=True)
class OrphanRef:
    """One review-gated orphan candidate — never auto-deleted (FR-151)."""

    kind: OrphanKind
    path: str
    reason: str


@dataclass(frozen=True)
class RegenerationReport:
    """Full result of one ``chain regenerate`` invocation."""

    project: str
    phases: tuple[PhaseOutcome, ...]
    statuses_before: Mapping[str, str]
    statuses_after: Mapping[str, str]
    preserved_done_keys: tuple[str, ...]
    regressions_blocked: tuple[tuple[str, str, str], ...]
    orphans: tuple[OrphanRef, ...]
    wrote_ledger: bool
    apply: bool


class PhaseRunner(Protocol):
    """Injectable per-phase backend (fixtures / future skill adapters)."""

    def run_phase(
        self,
        phase: PhaseName,
        *,
        root: Path,
        project: str,
        apply: bool,
    ) -> PhaseOutcome:
        """Execute one phase; must not touch another project's tree."""

    def propose_statuses(
        self,
        *,
        root: Path,
        project: str,
        statuses_before: Mapping[str, str],
    ) -> dict[str, str]:
        """Return the post-regen status map to validate with ``regressions``."""


def skill_for(phase: PhaseName) -> str:
    return _PHASE_SKILLS[phase]


def planning_dir(root: Path, project: str) -> Path:
    return root / "_bmad-output" / "projects" / project / "planning-artifacts"


def ledger_file(root: Path, project: str) -> Path:
    return planning_dir(root, project) / "sprint-status-ledger.yaml"


def parse_ledger_statuses(text: str) -> dict[str, str]:
    """Minimal ``development_status:`` map parser (ledger twin shape)."""
    out: dict[str, str] = {}
    in_block = False
    for line in text.splitlines():
        if line.startswith("development_status:"):
            in_block = True
            continue
        if not in_block:
            continue
        if line and not line.startswith(" ") and not line.startswith("\t"):
            break
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            continue
        key, _, val = stripped.partition(":")
        out[key.strip()] = val.strip()
    return out


def done_keys(statuses: Mapping[str, str]) -> tuple[str, ...]:
    return tuple(sorted(k for k, v in statuses.items() if v == "done"))


def apply_status_guard(
    existing: Mapping[str, str],
    incoming: Mapping[str, str],
    regressions_fn: Callable[[Mapping[str, str], Mapping[str, str]], Sequence[tuple[str, str, str]]],
) -> tuple[dict[str, str] | None, tuple[tuple[str, str, str], ...]]:
    """Reuse ``promote_sprint_status.regressions`` — refuse any ``done`` loss.

    Returns ``(safe_incoming_or_None, blocked_regressions)``. When blocked,
    the caller must not write the ledger.
    """
    blocked = tuple(regressions_fn(dict(existing), dict(incoming)))
    if blocked:
        return None, blocked
    return dict(incoming), ()


def find_orphans(root: Path, project: str) -> tuple[OrphanRef, ...]:
    """Report specs whose Dreams are gone, and epics citing missing/orphan specs.

    Never deletes. Paths are repo-relative strings when possible.
    """
    planning = planning_dir(root, project)
    if not planning.is_dir():
        return ()

    orphans: list[OrphanRef] = []
    orphan_spec_ids: set[str] = set()
    specs_root = planning / "specs"
    present_spec_ids = _present_spec_ids(specs_root)

    if specs_root.is_dir():
        for path in sorted(specs_root.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix not in {".md", ".yaml", ".yml"} and path.name != "SPEC.md":
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            dream = _owner_dream(text)
            if dream is None:
                continue
            dream_path = _resolve_dream(root, dream)
            if dream_path is not None and dream_path.is_file():
                continue
            rel = _rel(root, path)
            orphans.append(
                OrphanRef(
                    kind="spec",
                    path=rel,
                    reason=f"owner-dream missing: {dream}",
                )
            )
            sid = _spec_id_from_path(specs_root, path)
            if sid:
                orphan_spec_ids.add(sid)

    epics = planning / "epics.md"
    if epics.is_file():
        try:
            epic_text = epics.read_text(encoding="utf-8")
        except OSError:
            epic_text = ""
        for match in _SPEC_CITE_RE.finditer(epic_text):
            sid = match.group(0).lower()
            # Normalize to ``spec-<slug>`` form (regex already includes prefix).
            if not sid.startswith("spec-"):
                sid = f"spec-{sid}"
            missing = sid not in present_spec_ids
            is_orphan_spec = sid in orphan_spec_ids
            if missing or is_orphan_spec:
                reason = f"references orphaned spec {sid}" if is_orphan_spec else f"references missing spec {sid}"
                orphans.append(
                    OrphanRef(
                        kind="epic",
                        path=_rel(root, epics),
                        reason=reason,
                    )
                )

    # De-dupe epic citations (same epic file + reason).
    seen: set[tuple[str, str, str]] = set()
    unique: list[OrphanRef] = []
    for o in orphans:
        key = (o.kind, o.path, o.reason)
        if key in seen:
            continue
        seen.add(key)
        unique.append(o)
    return tuple(unique)


def run_regeneration(
    *,
    root: Path,
    project: str,
    runner: PhaseRunner,
    regressions_fn: Callable[[Mapping[str, str], Mapping[str, str]], Sequence[tuple[str, str, str]]],
    apply: bool,
    statuses_before: Mapping[str, str] | None = None,
    write_ledger: Callable[[Path, Mapping[str, str]], None] | None = None,
) -> RegenerationReport:
    """Run phases in ``CHAIN_PHASES`` order, guard statuses, report orphans."""
    planning = planning_dir(root, project)
    before = dict(statuses_before) if statuses_before is not None else {}
    if statuses_before is None:
        lp = ledger_file(root, project)
        if lp.is_file():
            before = parse_ledger_statuses(lp.read_text(encoding="utf-8"))

    outcomes: list[PhaseOutcome] = []
    for phase in CHAIN_PHASES:
        outcome = runner.run_phase(phase, root=root, project=project, apply=apply)
        outcomes.append(outcome)
        if outcome.status == "failed":
            orphans = find_orphans(root, project)
            return RegenerationReport(
                project=project,
                phases=tuple(outcomes),
                statuses_before=before,
                statuses_after=before,
                preserved_done_keys=done_keys(before),
                regressions_blocked=(),
                orphans=orphans,
                wrote_ledger=False,
                apply=apply,
            )

    proposed = runner.propose_statuses(root=root, project=project, statuses_before=before)
    safe, blocked = apply_status_guard(before, proposed, regressions_fn)
    wrote = False
    after = dict(before)
    if apply and safe is not None and write_ledger is not None and planning.is_dir():
        write_ledger(ledger_file(root, project), safe)
        wrote = True
        after = safe
    elif safe is not None:
        after = safe

    orphans = find_orphans(root, project)
    preserved = done_keys(before)
    # Byte-identical: every pre-done key still present with value done.
    if blocked:
        after = dict(before)
    return RegenerationReport(
        project=project,
        phases=tuple(outcomes),
        statuses_before=before,
        statuses_after=after,
        preserved_done_keys=preserved,
        regressions_blocked=blocked,
        orphans=orphans,
        wrote_ledger=wrote,
        apply=apply,
    )


class PlanPhaseRunner:
    """Default runner: records planned skill names; proposes caller-supplied map.

    On ``propose_statuses``, returns ``statuses_before`` unchanged unless a
    ``proposal`` dict was provided at construction (tests inject drops /
    backlog restructures here).
    """

    def __init__(self, proposal: Mapping[str, str] | None = None) -> None:
        self._proposal = dict(proposal) if proposal is not None else None
        self.phase_order: list[PhaseName] = []

    def run_phase(
        self,
        phase: PhaseName,
        *,
        root: Path,
        project: str,
        apply: bool,
    ) -> PhaseOutcome:
        del root, project  # plan runner is project-scoped by the orchestrator
        self.phase_order.append(phase)
        skill = skill_for(phase)
        mode = "apply-planned" if apply else "dry-run"
        return PhaseOutcome(
            name=phase,
            status="done",
            detail=f"{mode}: {skill}",
            skill=skill,
        )

    def propose_statuses(
        self,
        *,
        root: Path,
        project: str,
        statuses_before: Mapping[str, str],
    ) -> dict[str, str]:
        del root, project
        if self._proposal is not None:
            return dict(self._proposal)
        return dict(statuses_before)


def _owner_dream(text: str) -> str | None:
    m = _OWNER_DREAM_RE.search(text)
    return m.group(1) if m else None


def _resolve_dream(root: Path, dream: str) -> Path | None:
    raw = dream.strip()
    if not raw:
        return None
    # Absolute-within-repo style: docs/dreams/foo.md
    candidate = root / raw
    if candidate.is_file():
        return candidate
    # Relative memlog-style ../../../../../../docs/dreams/foo.md — normalize
    # by taking the docs/dreams/… suffix when present.
    if "docs/dreams/" in raw.replace("\\", "/"):
        suffix = raw.replace("\\", "/").split("docs/dreams/", 1)[1]
        candidate = root / "docs" / "dreams" / suffix
        if candidate.is_file():
            return candidate
    return candidate if candidate.exists() else None


def _present_spec_ids(specs_root: Path) -> set[str]:
    ids: set[str] = set()
    if not specs_root.is_dir():
        return ids
    for child in specs_root.iterdir():
        name = child.name
        if child.is_dir() and name.startswith("spec-"):
            ids.add(name.lower())
        elif child.is_file() and name.startswith("spec-") and name.endswith(".md"):
            ids.add(name[: -len(".md")].lower())
    return ids


def _spec_id_from_path(specs_root: Path, path: Path) -> str | None:
    try:
        rel = path.relative_to(specs_root)
    except ValueError:
        return None
    parts = rel.parts
    if not parts:
        return None
    top = parts[0]
    if top.startswith("spec-"):
        if top.endswith(".md"):
            return top[: -len(".md")].lower()
        return top.lower()
    return None


def _rel(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


# ---------------------------------------------------------------------------
# Story 21.2 — orchestrated Full / minimal chain (FR-192 CAP-1)
# Story 21.5 — CAP-5 parameter surface / defaults (any station by params)
# ---------------------------------------------------------------------------

OrchestratedPhase = Literal[
    "spec",
    "research",
    "brief",
    "prd",
    "architecture",
    "epics",
    "code_linkage",
    "orphan_report",
]
ChainMode = Literal["full", "minimal"]
OrchestratedStatus = Literal[
    "pending",
    "complete",
    "skipped",
    "blocked",
    "failed",
]
ChainRunStatus = Literal["in_progress", "complete", "blocked", "failed"]

FULL_CHAIN_PHASES: tuple[OrchestratedPhase, ...] = (
    "spec",
    "research",
    "brief",
    "prd",
    "architecture",
    "epics",
    "code_linkage",
    "orphan_report",
)
MINIMAL_SKIP_PHASES: frozenset[OrchestratedPhase] = frozenset({"research", "brief"})


def cap5_defaults() -> dict[str, object]:
    """Return the CAP-5 (Story 21.5) default parameter matrix.

    Keys match ``run_orchestrated_chain`` / CLI semantics:

    - ``mode`` / ``chain_mode``: ``\"full\"``
    - ``preserve_code_status``: ``True``
    - ``stage``: ``False``
    - ``apply_orphans``: ``False``
    - ``resume``: ``False``
    - ``auto_commit``: ``False`` (not offered; rejected if True)
    """
    return {
        "mode": "full",
        "chain_mode": "full",
        "preserve_code_status": True,
        "stage": False,
        "apply_orphans": False,
        "resume": False,
        "auto_commit": False,
    }


# First attempt + up to 2 retries ⇒ maximum 3 attempts.
MAX_PHASE_RETRIES = 2

_ORCHESTRATED_SKILLS: dict[OrchestratedPhase, str | None] = {
    "spec": "bmad-spec",
    "research": "bmad-deep-recon",
    "brief": "bmad-product-brief",
    "prd": "bmad-prd",
    "architecture": "bmad-architecture",
    "epics": "bmad-create-epics-and-stories",
    "code_linkage": None,
    "orphan_report": None,
}


@dataclass(frozen=True)
class OrchestratedPhaseOutcome:
    """One Full/minimal chain phase result."""

    name: OrchestratedPhase
    status: OrchestratedStatus
    detail: str = ""
    skill: str = ""
    attempts: int = 0


@dataclass(frozen=True)
class ChainJournal:
    """Persisted run journal (``state.yaml`` under ``.chain-regen/<run-id>/``)."""

    run_id: str
    project: str
    dream: str
    mode: ChainMode
    status: ChainRunStatus
    current_phase: OrchestratedPhase | None
    phases: Mapping[str, Mapping[str, object]]
    auto_commit: bool = False
    preserve_code_status: bool = True
    apply_orphans: bool = False
    stage: bool = False


@dataclass(frozen=True)
class OrchestratedChainReport:
    """Result of one ``planning chain-regenerate`` invocation."""

    project: str
    dream: str
    mode: ChainMode
    run_id: str
    run_dir: str
    status: ChainRunStatus
    phases: tuple[OrchestratedPhaseOutcome, ...]
    orphans: tuple[OrphanRef, ...]
    orphan_manifest_written: bool
    auto_commit: bool
    preserve_code_status_hook: bool
    apply_orphans_hook: bool
    stage_hook: bool


class SkillPhaseInvoker(Protocol):
    """Injectable FR-52 skill seam (CLI wires ``SkillInvokePort`` here)."""

    def invoke_planning_skill(
        self,
        skill: str,
        *,
        root: Path,
        project: str,
        dream: Path,
        phase: str,
        run_dir: Path,
    ) -> object:
        """Return an object with ``.status`` and ``.detail``.

        ``status`` must be one of ``complete`` / ``blocked`` / ``failed``.
        Must never call ``scripts/bmad-switch``.
        """
        ...


def skill_for_orchestrated(phase: OrchestratedPhase) -> str | None:
    return _ORCHESTRATED_SKILLS[phase]


def chain_regen_root(root: Path, project: str) -> Path:
    return planning_dir(root, project) / ".chain-regen"


def new_run_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}_{uuid.uuid4().hex[:8]}"


def write_orphan_manifest(
    run_dir: Path,
    orphans: Sequence[OrphanRef],
) -> tuple[Path, Path]:
    """Write ``orphans.json`` + ``orphans.md`` (report only; never deletes)."""
    run_dir.mkdir(parents=True, exist_ok=True)
    json_path = run_dir / "orphans.json"
    md_path = run_dir / "orphans.md"
    payload = [{"kind": o.kind, "path": o.path, "reason": o.reason} for o in orphans]
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Orphan report",
        "",
        "Review-gated candidates. Nothing was deleted.",
        "",
    ]
    if not orphans:
        lines.append("_No orphans detected._")
    else:
        for o in orphans:
            lines.append(f"- **{o.kind}** `{o.path}` — {o.reason}")
    lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def load_journal(run_dir: Path) -> ChainJournal | None:
    path = run_dir / "state.yaml"
    if not path.is_file():
        return None
    data = _parse_simple_yaml(path.read_text(encoding="utf-8"))
    phases_raw = data.get("phases")
    phases: dict[str, Mapping[str, object]] = {}
    if isinstance(phases_raw, dict):
        for key, val in phases_raw.items():
            if isinstance(val, dict):
                phases[str(key)] = dict(val)
    current = data.get("current_phase")
    mode = str(data.get("mode", "full"))
    if mode not in ("full", "minimal"):
        mode = "full"
    status = str(data.get("status", "in_progress"))
    if status not in ("in_progress", "complete", "blocked", "failed"):
        status = "in_progress"
    current_phase: OrchestratedPhase | None
    if current in (None, "", "null"):
        current_phase = None
    else:
        current_phase = str(current)  # type: ignore[assignment]
    return ChainJournal(
        run_id=str(data.get("run_id", "")),
        project=str(data.get("project", "")),
        dream=str(data.get("dream", "")),
        mode=mode,  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        current_phase=current_phase,
        phases=phases,
        auto_commit=False,
        preserve_code_status=bool(data.get("preserve_code_status", True)),
        apply_orphans=bool(data.get("apply_orphans", False)),
        stage=bool(data.get("stage", False)),
    )


def save_journal(run_dir: Path, journal: ChainJournal) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "state.yaml"
    lines = [
        f"run_id: {journal.run_id}",
        f"project: {journal.project}",
        f"dream: {_yaml_quote(journal.dream)}",
        f"mode: {journal.mode}",
        f"status: {journal.status}",
        (f"current_phase: {journal.current_phase}" if journal.current_phase else "current_phase: null"),
        "auto_commit: false",
        f"preserve_code_status: {'true' if journal.preserve_code_status else 'false'}",
        f"apply_orphans: {'true' if journal.apply_orphans else 'false'}",
        f"stage: {'true' if journal.stage else 'false'}",
        "phases:",
    ]
    for name in FULL_CHAIN_PHASES:
        entry = dict(journal.phases.get(name, {}))
        status = entry.get("status", "pending")
        attempts = entry.get("attempts", 0)
        detail = str(entry.get("detail", "")).replace("\n", " ")
        skill = entry.get("skill", "") or "null"
        lines.append(f"  {name}:")
        lines.append(f"    status: {status}")
        lines.append(f"    attempts: {attempts}")
        lines.append(f"    skill: {skill}")
        lines.append(f"    detail: {_yaml_quote(detail)}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def find_latest_incomplete_run(root: Path, project: str) -> Path | None:
    base = chain_regen_root(root, project)
    if not base.is_dir():
        return None
    candidates: list[tuple[str, Path]] = []
    for child in base.iterdir():
        if not child.is_dir():
            continue
        journal = load_journal(child)
        if journal is None or journal.status == "complete":
            continue
        candidates.append((child.name, child))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def verify_code_linkage(root: Path, project: str) -> OrchestratedPhaseOutcome:
    """Read-only code-linkage verify — never edits implementation code."""
    planning = planning_dir(root, project)
    epics = planning / "epics.md"
    if not epics.is_file():
        return OrchestratedPhaseOutcome(
            name="code_linkage",
            status="complete",
            detail="read-only verify: epics.md absent (nothing to link)",
            attempts=1,
        )
    try:
        text = epics.read_text(encoding="utf-8")
    except OSError as exc:
        return OrchestratedPhaseOutcome(
            name="code_linkage",
            status="failed",
            detail=f"cannot read epics.md: {exc}",
            attempts=1,
        )
    cites = sorted({f"spec-{m.group(1).lower()}" for m in _SPEC_CITE_RE.finditer(text)})
    present = _present_spec_ids(planning / "specs")
    missing = [c for c in cites if c not in present]
    return OrchestratedPhaseOutcome(
        name="code_linkage",
        status="complete",
        detail=(f"read-only verify: {len(cites)} spec cite(s); {len(missing)} missing"),
        attempts=1,
    )


_CODE_STATUS_VALUES = frozenset({"done", "in-progress", "backlog"})
_SNAPSHOT_NAME = "code-status-snapshot.yaml"


def snapshot_code_statuses(statuses: Mapping[str, str]) -> dict[str, str]:
    """Snapshot development statuses keyed by stable story id (CAP-2)."""
    return {str(k): str(v) for k, v in statuses.items()}


def apply_preserved_code_statuses(
    preserved: Mapping[str, str],
    current: Mapping[str, str],
) -> dict[str, str]:
    """Re-apply preserved statuses onto regenerated story keys.

    Matching keys keep the pre-regen status byte-identical. New keys start
    as ``backlog``. Retired keys are not resurrected. Never invents status
    for unmatched keys beyond the backlog default for newcomers.
    """
    out: dict[str, str] = {}
    for key in current:
        if key in preserved:
            out[key] = preserved[key]
        else:
            out[key] = "backlog"
    return out


def write_ledger_statuses(path: Path, statuses: Mapping[str, str]) -> None:
    """Rewrite the ``development_status:`` map in-place. Never git-commits."""
    path.parent.mkdir(parents=True, exist_ok=True)
    head = ""
    if path.is_file():
        existing = path.read_text(encoding="utf-8")
        if "development_status:" in existing:
            head = existing.split("development_status:", 1)[0]
        else:
            head = existing.rstrip() + "\n"
    body = "".join(f"  {k}: {v}\n" for k, v in sorted(statuses.items()))
    path.write_text(head + "development_status:\n" + body, encoding="utf-8")


def save_code_status_snapshot(run_dir: Path, statuses: Mapping[str, str]) -> Path:
    """Persist the pre-regen snapshot beside the journal (resume-safe)."""
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / _SNAPSHOT_NAME
    lines = ["development_status:"]
    for key, val in sorted(statuses.items()):
        lines.append(f"  {key}: {val}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def load_code_status_snapshot(run_dir: Path) -> dict[str, str] | None:
    path = run_dir / _SNAPSHOT_NAME
    if not path.is_file():
        return None
    return parse_ledger_statuses(path.read_text(encoding="utf-8"))


def preserve_code_status_hook(
    statuses_before: Mapping[str, str],
    statuses_after: Mapping[str, str] | None = None,
) -> Mapping[str, str]:
    """CAP-2 (Story 21.3): snapshot or re-apply preserved code statuses.

    With one argument (legacy call site): return a snapshot copy.
    With ``statuses_after``: re-apply preserved values onto regenerated keys.
    """
    if statuses_after is None:
        return snapshot_code_statuses(statuses_before)
    return apply_preserved_code_statuses(statuses_before, statuses_after)


def reapply_code_statuses_after_epics(
    *,
    root: Path,
    project: str,
    preserved: Mapping[str, str],
) -> dict[str, str]:
    """After epics generation, restore preserved statuses onto the ledger.

    Runs before the orphan report. Writes the ledger only — never commits.
    """
    lp = ledger_file(root, project)
    current: dict[str, str] = {}
    if lp.is_file():
        current = parse_ledger_statuses(lp.read_text(encoding="utf-8"))
    # Empty current means the regen left no story keys (or deleted the
    # ledger). Do not resurrect retired keys from the snapshot — CAP-2
    # only re-applies onto keys that still exist after epics regen.
    if not current:
        return {}
    merged = apply_preserved_code_statuses(preserved, current)
    write_ledger_statuses(lp, merged)
    return merged


def orphan_delete_units(root: Path, orphans: Sequence[OrphanRef]) -> tuple[Path, ...]:
    """Resolve deletable orphan units from the manifest.

    Only ``kind=spec`` paths are deletable. Epic citations point at
    ``epics.md`` and must never be removed. File paths under a ``spec-*``
    directory collapse to that directory so the whole orphaned folder goes.
    """
    units: set[Path] = set()
    root_res = root.resolve()
    for orphan in orphans:
        if orphan.kind != "spec":
            continue
        raw = Path(orphan.path)
        path = raw if raw.is_absolute() else (root / raw)
        try:
            resolved = path.resolve()
        except OSError:
            resolved = path
        collapsed: Path | None = None
        for candidate in (resolved, *resolved.parents):
            try:
                rel = candidate.relative_to(root_res)
            except ValueError:
                continue
            parts = rel.parts
            if len(parts) >= 2 and parts[-1].startswith("spec-") and parts[-2] == "specs":
                collapsed = candidate
                break
        units.add(collapsed if collapsed is not None else resolved)
    return tuple(sorted(units, key=lambda p: str(p)))


def apply_orphans_hook(
    orphans: Sequence[OrphanRef],
    *,
    apply: bool,
    root: Path | None = None,
) -> int:
    """CAP-4 (Story 21.4): disk-delete orphan units only when ``apply`` is true.

    Never commits or pushes. Returns the number of units removed. Empty
    orphan lists and ``apply=False`` are no-ops (return 0).
    """
    if not apply or not orphans:
        return 0
    base = root if root is not None else Path.cwd()
    deleted = 0
    for unit in orphan_delete_units(base, orphans):
        if not unit.exists():
            continue
        if unit.is_dir():
            shutil.rmtree(unit)
        elif unit.is_file():
            unit.unlink()
        else:
            continue
        deleted += 1
    return deleted


# Callable injected by the CLI/adapters layer (AD-4: core must not import
# ``subprocess``). ``update=True`` means stage deletions of tracked paths
# (``git add -u --``); otherwise stage paths as-is (``git add --``).
# Never commits. Returns the number of paths successfully handed to git.
StageIndexFn = Callable[[Path, Sequence[str], bool], int]


def stage_hook(
    paths: Sequence[Path | str],
    *,
    stage: bool,
    root: Path | None = None,
    stager: StageIndexFn | None = None,
) -> int:
    """CAP-4 (Story 21.4): stage regenerated / orphan-rm paths; never commit.

    Core only resolves relative paths and classifies existing vs missing
    entries. The actual ``git add`` / ``git add -u`` calls are performed by
    ``stager`` (wired from ``adapters/vcs_git.py`` by the CLI). Returns the
    number of path arguments handed to the stager (0 when ``stage`` is false,
    ``paths`` is empty, or no stager is provided).
    """
    if not stage or not paths or stager is None:
        return 0
    base = (root if root is not None else Path.cwd()).resolve()
    existing: list[str] = []
    missing: list[str] = []
    for raw in paths:
        path = Path(raw)
        if not path.is_absolute():
            path = base / path
        try:
            rel = str(path.resolve().relative_to(base))
        except ValueError:
            rel = str(path)
        if path.exists():
            existing.append(rel)
        else:
            missing.append(rel)
    staged = 0
    if existing:
        staged += stager(base, existing, False)
    if missing:
        staged += stager(base, missing, True)
    return staged


def planning_stage_paths(root: Path, project: str) -> tuple[Path, ...]:
    """Paths under planning-artifacts eligible for ``--stage`` (excl. journals)."""
    planning = planning_dir(root, project)
    if not planning.is_dir():
        return ()
    out: list[Path] = []
    for child in sorted(planning.iterdir()):
        if child.name == ".chain-regen":
            continue
        out.append(child)
    return tuple(out)


def run_orchestrated_chain(
    *,
    root: Path,
    project: str,
    dream: Path,
    invoker: SkillPhaseInvoker,
    mode: ChainMode = "full",
    resume: bool = False,
    run_id: str | None = None,
    auto_commit: bool = False,
    preserve_code_status: bool = True,
    apply_orphans: bool = False,
    stage: bool = False,
    stager: StageIndexFn | None = None,
) -> OrchestratedChainReport:
    """Orchestrate Full/minimal planning-chain regeneration with journal resume.

    CAP-5 (Story 21.5) parameter surface — same workflow for any station:

    - ``project``: ``project_slug`` (physical tree
      ``_bmad-output/projects/<slug>/planning-artifacts/``; never hardcoded)
    - ``dream``: ``dream_path``
    - ``mode``: ``chain_mode`` (``full`` default | ``minimal``)
    - ``preserve_code_status``: default ``True``
    - ``stage``: default ``False``
    - ``apply_orphans``: default ``False``
    - ``resume``: continue latest incomplete journal for ``project``
    - ``auto_commit``: must stay ``False`` (raises if ``True``; not offered)

    Cross-station / multi-slug: callers pass literal physical paths under
    each slug and rely on the invoker for ``BMAD_ACTIVE_PROJECT=<slug>`` per
    invoke — never ``scripts/bmad-switch``. Never hand-overwrites
    memlog-derived artifacts — skill phases go through ``invoker``.
    """
    if auto_commit:
        raise ValueError("auto_commit is not offered; regeneration output stays unstaged")

    planning = planning_dir(root, project)
    if not planning.is_dir():
        raise FileNotFoundError(f"planning-artifacts missing: {planning}")
    dream_path = dream if dream.is_file() else (root / dream)
    if not dream_path.is_file():
        raise FileNotFoundError(f"dream not found: {dream}")

    if resume:
        existing = find_latest_incomplete_run(root, project)
        if existing is None:
            raise FileNotFoundError(f"no incomplete chain-regen journal under {chain_regen_root(root, project)}")
        loaded = load_journal(existing)
        if loaded is None:
            raise FileNotFoundError(f"state.yaml missing in {existing}")
        if loaded.project and loaded.project != project:
            raise ValueError(f"journal project {loaded.project!r} does not match --project {project!r}")
        run_dir = existing
        journal = loaded
        phase_state: dict[str, dict[str, object]] = {k: dict(v) for k, v in loaded.phases.items()}
        mode = journal.mode
        preserve_code_status = journal.preserve_code_status
        apply_orphans = journal.apply_orphans
        stage = journal.stage
    else:
        rid = run_id or new_run_id()
        run_dir = chain_regen_root(root, project) / rid
        run_dir.mkdir(parents=True, exist_ok=True)
        phase_state = {
            name: {
                "status": "pending",
                "attempts": 0,
                "skill": skill_for_orchestrated(name) or "",
                "detail": "",
            }
            for name in FULL_CHAIN_PHASES
        }
        journal = ChainJournal(
            run_id=rid,
            project=project,
            dream=_rel(root, dream_path),
            mode=mode,
            status="in_progress",
            current_phase=FULL_CHAIN_PHASES[0],
            phases=phase_state,
            auto_commit=False,
            preserve_code_status=preserve_code_status,
            apply_orphans=apply_orphans,
            stage=stage,
        )
        save_journal(run_dir, journal)

    before: dict[str, str] = {}
    lp = ledger_file(root, project)
    if lp.is_file():
        before = parse_ledger_statuses(lp.read_text(encoding="utf-8"))
    if preserve_code_status:
        # Resume: prefer the snapshot taken at the start of this run so a
        # mid-chain ledger wipe cannot poison the preserved map.
        loaded_snap = load_code_status_snapshot(run_dir)
        if loaded_snap is not None:
            before = loaded_snap
        else:
            before = dict(preserve_code_status_hook(before))
            save_code_status_snapshot(run_dir, before)

    outcomes: list[OrchestratedPhaseOutcome] = []
    orphans: tuple[OrphanRef, ...] = ()
    orphan_written = False

    for phase in FULL_CHAIN_PHASES:
        prior = phase_state.get(phase, {})
        prior_status = str(prior.get("status", "pending"))
        if prior_status in ("complete", "skipped"):
            outcomes.append(
                OrchestratedPhaseOutcome(
                    name=phase,
                    status=prior_status,  # type: ignore[arg-type]
                    detail=str(prior.get("detail", "resumed: already finished")),
                    skill=str(prior.get("skill", "") or ""),
                    attempts=_safe_int(prior.get("attempts", 0), default=0),
                )
            )
            # Resume safety: epics may have completed before CAP-2 reapply ran.
            if phase == "epics" and preserve_code_status and prior_status == "complete":
                reapply_code_statuses_after_epics(
                    root=root,
                    project=project,
                    preserved=before,
                )
            continue

        if mode == "minimal" and phase in MINIMAL_SKIP_PHASES:
            outcome = OrchestratedPhaseOutcome(
                name=phase,
                status="skipped",
                detail="skipped by --minimal (research/brief)",
                skill=skill_for_orchestrated(phase) or "",
                attempts=0,
            )
            outcomes.append(outcome)
            phase_state[phase] = {
                "status": "skipped",
                "attempts": 0,
                "skill": outcome.skill,
                "detail": outcome.detail,
            }
            journal = _journal_replace(
                journal,
                current_phase=phase,
                phases=phase_state,
                status="in_progress",
            )
            save_journal(run_dir, journal)
            continue

        outcome = _execute_orchestrated_phase(
            phase=phase,
            root=root,
            project=project,
            dream=dream_path,
            run_dir=run_dir,
            invoker=invoker,
            prior_attempts=_safe_int(prior.get("attempts", 0), default=0),
        )
        outcomes.append(outcome)
        phase_state[phase] = {
            "status": outcome.status,
            "attempts": outcome.attempts,
            "skill": outcome.skill,
            "detail": outcome.detail,
        }

        if outcome.status in ("blocked", "failed"):
            journal = _journal_replace(
                journal,
                current_phase=phase,
                phases=phase_state,
                status=outcome.status,  # type: ignore[arg-type]
            )
            save_journal(run_dir, journal)
            orphans = find_orphans(root, project)
            try:
                write_orphan_manifest(run_dir, orphans)
                orphan_written = True
            except OSError:
                orphan_written = False
            return OrchestratedChainReport(
                project=project,
                dream=str(dream_path),
                mode=mode,
                run_id=journal.run_id,
                run_dir=str(run_dir),
                status=outcome.status,  # type: ignore[arg-type]
                phases=tuple(outcomes),
                orphans=orphans,
                orphan_manifest_written=orphan_written,
                auto_commit=False,
                preserve_code_status_hook=preserve_code_status,
                apply_orphans_hook=apply_orphans,
                stage_hook=stage,
            )

        journal = _journal_replace(
            journal,
            current_phase=phase,
            phases=phase_state,
            status="in_progress",
        )
        save_journal(run_dir, journal)

        if phase == "epics" and preserve_code_status:
            reapply_code_statuses_after_epics(
                root=root,
                project=project,
                preserved=before,
            )

        if phase == "orphan_report":
            orphans = find_orphans(root, project)
            write_orphan_manifest(run_dir, orphans)
            orphan_written = True
            apply_orphans_hook(orphans, apply=apply_orphans, root=root)

    stage_paths: list[Path] = []
    if stage:
        stage_paths.extend(planning_stage_paths(root, project))
        if apply_orphans:
            stage_paths.extend(orphan_delete_units(root, orphans))
    stage_hook(stage_paths, stage=stage, root=root, stager=stager)

    journal = _journal_replace(
        journal,
        current_phase=None,
        phases=phase_state,
        status="complete",
    )
    save_journal(run_dir, journal)

    if not orphan_written:
        orphans = find_orphans(root, project)

    return OrchestratedChainReport(
        project=project,
        dream=str(dream_path),
        mode=mode,
        run_id=journal.run_id,
        run_dir=str(run_dir),
        status="complete",
        phases=tuple(outcomes),
        orphans=orphans,
        orphan_manifest_written=orphan_written,
        auto_commit=False,
        preserve_code_status_hook=preserve_code_status,
        apply_orphans_hook=apply_orphans,
        stage_hook=stage,
    )


def _execute_orchestrated_phase(
    *,
    phase: OrchestratedPhase,
    root: Path,
    project: str,
    dream: Path,
    run_dir: Path,
    invoker: SkillPhaseInvoker,
    prior_attempts: int,
) -> OrchestratedPhaseOutcome:
    skill = skill_for_orchestrated(phase)

    if phase == "code_linkage":
        return verify_code_linkage(root, project)

    if phase == "orphan_report":
        return OrchestratedPhaseOutcome(
            name="orphan_report",
            status="complete",
            detail="orphan report phase (manifest written by orchestrator)",
            attempts=1,
        )

    assert skill is not None
    attempts = prior_attempts
    last_detail = ""
    while attempts <= MAX_PHASE_RETRIES:
        attempts += 1
        result = invoker.invoke_planning_skill(
            skill,
            root=root,
            project=project,
            dream=dream,
            phase=phase,
            run_dir=run_dir,
        )
        status = str(getattr(result, "status", "failed"))
        last_detail = str(getattr(result, "detail", ""))
        # Map SkillInvokePort vocabulary onto orchestrated statuses.
        if status in ("complete", "done"):
            return OrchestratedPhaseOutcome(
                name=phase,
                status="complete",
                detail=last_detail,
                skill=skill,
                attempts=attempts,
            )
        if status == "blocked":
            return OrchestratedPhaseOutcome(
                name=phase,
                status="blocked",
                detail=last_detail,
                skill=skill,
                attempts=attempts,
            )
        if attempts > MAX_PHASE_RETRIES:
            break
    return OrchestratedPhaseOutcome(
        name=phase,
        status="failed",
        detail=last_detail or f"phase {phase} failed after {attempts} attempt(s)",
        skill=skill,
        attempts=attempts,
    )


def _journal_replace(
    journal: ChainJournal,
    *,
    current_phase: OrchestratedPhase | None,
    phases: Mapping[str, Mapping[str, object]],
    status: ChainRunStatus,
) -> ChainJournal:
    return ChainJournal(
        run_id=journal.run_id,
        project=journal.project,
        dream=journal.dream,
        mode=journal.mode,
        status=status,
        current_phase=current_phase,
        phases=dict(phases),
        auto_commit=False,
        preserve_code_status=journal.preserve_code_status,
        apply_orphans=journal.apply_orphans,
        stage=journal.stage,
    )


def _safe_int(value: object, *, default: int = 0) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except TypeError, ValueError:
        return default


def _yaml_quote(value: str) -> str:
    if value == "":
        return '""'
    if any(ch in value for ch in (":", "#", "{", "}", "[", "]", ",", '"', "'", " ")):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return value


def _parse_simple_yaml(text: str) -> dict[str, object]:
    """Minimal YAML subset reader for journal state (no PyYAML dependency)."""
    root: dict[str, object] = {}
    phases: dict[str, dict[str, object]] = {}
    current_phase_key: str | None = None
    in_phases = False
    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()
        if indent == 0 and line == "phases:":
            in_phases = True
            root["phases"] = phases
            current_phase_key = None
            continue
        if indent == 0 and ":" in line:
            in_phases = False
            current_phase_key = None
            key, _, val = line.partition(":")
            root[key.strip()] = _yaml_scalar(val.strip())
            continue
        if in_phases and indent == 2 and line.endswith(":"):
            current_phase_key = line[:-1].strip()
            phases[current_phase_key] = {}
            continue
        if in_phases and indent >= 4 and current_phase_key is not None and ":" in line:
            key, _, val = line.partition(":")
            phases[current_phase_key][key.strip()] = _yaml_scalar(val.strip())
            continue
    return root


def _yaml_scalar(raw: str) -> object:
    if raw in ("", "null", "~"):
        return None
    if raw in ("true", "True"):
        return True
    if raw in ("false", "False"):
        return False
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ('"', "'"):
        inner = raw[1:-1]
        return inner.replace('\\"', '"').replace("\\\\", "\\")
    try:
        return int(raw)
    except ValueError:
        return raw
