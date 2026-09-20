"""Re-preflight for fleet-drain campaign blocks (Story 28.18, CAP-1).

When a story was refused for a reason whose predicate can change (spec glob,
configured verify commands, …), the next drain tick re-evaluates that
predicate cheaply — never by executing ``verify_commands``. Identical
refuse is rate-limited; a changed predicate clears the campaign block so
``dispatch_once`` runs again.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from . import dispatch as dispatch_core

_REFUSE_GATE_RE = re.compile(r"^(MRS-[A-Z0-9-]+)\s*:")


class RePreflightDecision(StrEnum):
    """What to do with one campaign-blocked story on this tick."""

    STILL_BLOCKED = "still-blocked"
    CLEARED = "cleared"
    RATE_LIMITED = "rate-limited"


@dataclass(frozen=True)
class RefusePredicate:
    """Cheap, tick-local inputs to a refuse decision — never executes verify."""

    gate: str
    spec_fingerprint: str
    verify_fingerprint: str

    def digest(self) -> str:
        payload = f"{self.gate}|{self.spec_fingerprint}|{self.verify_fingerprint}"
        return hashlib.sha256(payload.encode()).hexdigest()


@dataclass(frozen=True)
class RePreflightResult:
    story: str
    gate: str
    decision: RePreflightDecision
    prior_detail: str
    predicate: RefusePredicate | None = None


# Gates whose refuse reason can change without operator intervention.
_RE_PREFLIGHTABLE_GATES: frozenset[str] = frozenset(
    {
        "MRS-DISP-005",  # missing/unreadable tracked spec
        "MRS-GATE-001",
        "MRS-GATE-002",
        "MRS-GATE-003",
        "MRS-GATE-004",
        "MRS-GATE-005",
        "MRS-GATE-006",
        "MRS-GATE-010",
        "MRS-GATE-011",
        "MRS-GATE-012",
        "MRS-GATE-013",
    }
)


def parse_refuse_gate(detail: str) -> str | None:
    """Extract the leading ``MRS-*`` code from a campaign-block detail string."""
    match = _REFUSE_GATE_RE.match(str(detail).strip())
    return match.group(1) if match else None


def is_re_preflightable_gate(gate: str | None) -> bool:
    return gate is not None and gate in _RE_PREFLIGHTABLE_GATES


def spec_fingerprint(repo_root: Path, slug: str, story: str) -> str:
    """Glob/read-free spec presence fingerprint for one story."""
    spec_path = dispatch_core.resolve_story_spec_path(repo_root, slug, story)
    if spec_path is None:
        return "spec:missing"
    try:
        stat = spec_path.stat()
    except OSError:
        return "spec:unreadable"
    return f"spec:{spec_path.name}:{stat.st_mtime_ns}:{stat.st_size}"


def verify_commands_fingerprint(verify_commands: Sequence[str]) -> str:
    """Hash configured verify commands — never executes them."""
    joined = "\n".join(str(command) for command in verify_commands)
    digest = hashlib.sha256(joined.encode()).hexdigest()
    return f"verify:{digest}"


def compute_refuse_predicate(
    *,
    repo_root: Path,
    slug: str,
    story: str,
    gate: str,
    verify_commands: Sequence[str] = (),
) -> RefusePredicate:
    return RefusePredicate(
        gate=gate,
        spec_fingerprint=spec_fingerprint(repo_root, slug, story),
        verify_fingerprint=verify_commands_fingerprint(verify_commands),
    )


def refuse_still_applies(*, predicate: RefusePredicate, gate: str) -> bool:
    """Whether the cheap predicate still predicts the same refuse."""
    if gate == "MRS-DISP-005":
        return predicate.spec_fingerprint in ("spec:missing", "spec:unreadable")
    if gate.startswith("MRS-GATE-"):
        # Verify refuses depend on configured commands, not on executing them.
        return True
    return True


def reconcile_station_re_preflight(
    *,
    repo_root: Path,
    slug: str,
    blocked: Mapping[str, str],
    verify_commands: Sequence[str] = (),
    prior_predicates: Mapping[str, RefusePredicate] | None = None,
) -> tuple[dict[str, str], tuple[RePreflightResult, ...]]:
    """Drop or rate-limit campaign blocks whose refuse predicate changed."""
    prior = dict(prior_predicates or {})
    kept: dict[str, str] = {}
    results: list[RePreflightResult] = []
    for story, detail in blocked.items():
        gate = parse_refuse_gate(detail)
        if not is_re_preflightable_gate(gate):
            kept[story] = detail
            continue
        assert gate is not None
        current = compute_refuse_predicate(
            repo_root=repo_root,
            slug=slug,
            story=story,
            gate=gate,
            verify_commands=verify_commands,
        )
        if not refuse_still_applies(predicate=current, gate=gate):
            results.append(
                RePreflightResult(
                    story=story,
                    gate=gate,
                    decision=RePreflightDecision.CLEARED,
                    prior_detail=detail,
                    predicate=current,
                )
            )
            continue
        previous = prior.get(story)
        if previous is not None and previous.digest() == current.digest():
            results.append(
                RePreflightResult(
                    story=story,
                    gate=gate,
                    decision=RePreflightDecision.RATE_LIMITED,
                    prior_detail=detail,
                    predicate=current,
                )
            )
            kept[story] = detail
            continue
        if previous is None:
            # First re-preflight after refuse: predicate unchanged, rate-limit.
            results.append(
                RePreflightResult(
                    story=story,
                    gate=gate,
                    decision=RePreflightDecision.RATE_LIMITED,
                    prior_detail=detail,
                    predicate=current,
                )
            )
            kept[story] = detail
            continue
        # Predicate changed but refuse still applies.
        if gate.startswith("MRS-GATE-") and verify_rerun_needed(prior=previous, current=current):
            # Verify config changed — clear so the next tick re-dispatches.
            results.append(
                RePreflightResult(
                    story=story,
                    gate=gate,
                    decision=RePreflightDecision.CLEARED,
                    prior_detail=detail,
                    predicate=current,
                )
            )
            continue
        # Spec-only change on verify gates (AC3), unreadable spec, or any other
        # gate where refuse_still_applies — rate-limit, do not re-dispatch.
        results.append(
            RePreflightResult(
                story=story,
                gate=gate,
                decision=RePreflightDecision.RATE_LIMITED,
                prior_detail=detail,
                predicate=current,
            )
        )
        kept[story] = detail
    return kept, tuple(results)


def verify_rerun_needed(
    *,
    prior: RefusePredicate | None,
    current: RefusePredicate,
) -> bool:
    """True when verify commands fingerprint changed between refuses."""
    if prior is None:
        return True
    return prior.verify_fingerprint != current.verify_fingerprint
