"""Parity-evidence record + the legacy-retirement gate (Story B4, AC-3).

AD-19 (binding): the legacy orchestrator runs in parallel until B4 proves parity
— Q1 default, exact row-count + value parity on the ``v_actionable_packages``
family — **with recorded evidence and attended sign-off**; ``phase_state`` and
``bootstrap-data`` retire with it (FR-4). This module is the machine encoding of
that gate.

- ``ParityEvidenceRecord`` is the artifact the attended credentialed run records
  per legacy-surface view: view · legacy row count · kedro row count ·
  material-drift verdict · benign-diff notes · run mode · human sign-off.
- ``may_retire_legacy`` returns ``allowed=True`` ONLY when EVERY legacy-surface
  view has a **credentialed**, **zero-material-drift**, **human-signed** record.
  In-loop (no credentialed records, no sign-off) it correctly returns
  ``allowed=False`` — the honest state until the attended event.

Pure: dataclasses + stdlib only. No IO, no DB, no ``phase_state`` mutation. The
actual sign-off and the retirement action (FR-4 ``phase_state`` removal) are
DEFERRED to the attended event (DW-B4).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass

RUN_MODE_FIXTURE = "fixture"
RUN_MODE_CREDENTIALED = "credentialed"


@dataclass(frozen=True)
class ParityEvidenceRecord:
    """One recorded parity result for one legacy-surface view.

    ``material_drift`` is the verdict AFTER benign-diff classification: a
    timestamp/ordering-only difference is documented in ``benign_diffs`` and does
    NOT set ``material_drift`` (Q1: "timestamp/ordering-only diffs documented
    benign"). ``human_sign_off`` stays ``None`` until a human signs at the
    attended event — it is the load-bearing gate on retirement.
    """

    view: str
    legacy_row_count: int
    kedro_row_count: int
    material_drift: bool
    run_mode: str  # RUN_MODE_FIXTURE | RUN_MODE_CREDENTIALED
    benign_diffs: tuple[str, ...] = ()
    legacy_db_ref: str | None = None
    kedro_store_ref: str | None = None
    captured_at: str | None = None
    human_sign_off: str | None = None
    detail: str = ""

    @property
    def row_count_delta(self) -> int:
        return self.kedro_row_count - self.legacy_row_count

    @property
    def is_credentialed(self) -> bool:
        return self.run_mode == RUN_MODE_CREDENTIALED

    @property
    def is_signed(self) -> bool:
        return bool(self.human_sign_off)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["benign_diffs"] = list(self.benign_diffs)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "ParityEvidenceRecord":
        d = dict(d)
        if "benign_diffs" in d and d["benign_diffs"] is not None:
            d["benign_diffs"] = tuple(d["benign_diffs"])
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})


@dataclass(frozen=True)
class RetirementDecision:
    """The output of the retirement gate. ``allowed`` is the ONLY signal FR-4
    (``phase_state`` removal / legacy retirement) may act on."""

    allowed: bool
    reason: str
    covered_views: tuple[str, ...] = ()
    missing_views: tuple[str, ...] = ()
    unsigned_views: tuple[str, ...] = ()
    drifted_views: tuple[str, ...] = ()
    non_credentialed_views: tuple[str, ...] = ()


def may_retire_legacy(
    records: Iterable[ParityEvidenceRecord],
    *,
    required_views: Sequence[str],
) -> RetirementDecision:
    """Decide whether the legacy orchestrator may be marked for retirement.

    Retirement is allowed ONLY when EVERY view in ``required_views`` (the Q1
    legacy-surface family) has a matching evidence record that is ALL of:
    credentialed, zero-material-drift, and human-signed. Any gap → not allowed,
    with a precise reason. This never mutates anything — the actual FR-4
    ``phase_state`` removal is a separate, attended action gated on ``allowed``.
    """
    required = list(dict.fromkeys(required_views))  # de-dupe, preserve order

    # Fail closed: an empty required-view set must NEVER vacuously allow
    # retirement — there is no parity evidence to stand on.
    if not required:
        return RetirementDecision(
            allowed=False,
            reason=(
                "legacy retirement BLOCKED (AD-19/FR-4): no required legacy-surface "
                "views specified — the gate fails closed on an empty parity set"
            ),
        )

    by_view: dict[str, list[ParityEvidenceRecord]] = {}
    for r in records:
        by_view.setdefault(r.view, []).append(r)

    missing: list[str] = []
    non_credentialed: list[str] = []
    drifted: list[str] = []
    unsigned: list[str] = []
    covered: list[str] = []

    for view in required:
        recs = by_view.get(view, [])
        if not recs:
            missing.append(view)
            continue
        cred = [r for r in recs if r.is_credentialed]
        if not cred:
            non_credentialed.append(view)
            continue
        # Fail closed: ANY credentialed record showing material drift blocks the
        # view — a coexisting clean record must NOT mask a recorded drift.
        if any(r.material_drift for r in cred):
            drifted.append(view)
            continue
        # No drift on any credentialed record; require at least one that is signed
        # (and therefore clean+signed, since none drifted).
        clean_signed = [r for r in cred if not r.material_drift and r.is_signed]
        if not clean_signed:
            unsigned.append(view)
            continue
        covered.append(view)

    allowed = len(covered) == len(required) and not (
        missing or non_credentialed or drifted or unsigned
    )
    if allowed:
        reason = (
            f"all {len(required)} legacy-surface view(s) have a credentialed, "
            "zero-material-drift, human-signed parity record"
        )
    else:
        blockers = []
        if missing:
            blockers.append(f"no evidence for {missing}")
        if non_credentialed:
            blockers.append(f"only fixture-mode evidence for {non_credentialed}")
        if drifted:
            blockers.append(f"material drift on {drifted}")
        if unsigned:
            blockers.append(f"no human sign-off for {unsigned}")
        reason = (
            "legacy retirement BLOCKED (AD-19/FR-4): " + "; ".join(blockers)
            if blockers
            else "legacy retirement blocked"
        )

    return RetirementDecision(
        allowed=allowed,
        reason=reason,
        covered_views=tuple(covered),
        missing_views=tuple(missing),
        unsigned_views=tuple(unsigned),
        drifted_views=tuple(drifted),
        non_credentialed_views=tuple(non_credentialed),
    )
