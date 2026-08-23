"""``core/chain_regen.py`` (Story 17.4, FR-148/FR-149/FR-151, AD-72).

Pure orchestration types + helpers for one named project's planning-chain
regeneration. No I/O beyond what callers pass in: the CLI loads the
promote-sprint-status guard, runs an injectable phase runner in dependency
order, applies the existing ``regressions`` guard before any ledger write,
and reports orphans without deleting them.

Live BMAD-skill backends remain Epic 21.2 (Spec Q1). This module owns the
marshal-side contract: order, guard reuse, orphan report, per-project scope.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
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
                reason = (
                    f"references orphaned spec {sid}"
                    if is_orphan_spec
                    else f"references missing spec {sid}"
                )
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
    regressions_fn: Callable[
        [Mapping[str, str], Mapping[str, str]], Sequence[tuple[str, str, str]]
    ],
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

    proposed = runner.propose_statuses(
        root=root, project=project, statuses_before=before
    )
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
