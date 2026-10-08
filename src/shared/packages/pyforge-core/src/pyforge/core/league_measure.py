"""Published measure cite gate (Story 62.3 / spec-build-league-scorecard CAP-3).

Herald, Atlas, Marshal, and Doctor call :func:`validate_measure_cite` before
treating a league measure id as steering work. Only rows whose ``State`` is
``on`` in the steward companion catalog are allowed; ``off``, ``archived``, and
unknown ids are refuses. Hub Outcome Guards are out of scope here.

Stdlib-only; reads the tracked companion markdown table, never a second list.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

MEASURE_CATALOG_RELATIVE = Path(
    "_bmad-output/projects/pyforge-steward/planning-artifacts/specs/"
    "spec-build-league-scorecard/measure-catalog.md"
)

_VALID_STATES = frozenset({"on", "off", "archived"})

# id | Dimension | Source | State | Notes — State is the fourth data column.
_ROW_RE = re.compile(
    r"^\|\s*`([^`]+)`\s*\|[^|\n]*\|[^|\n]*\|\s*`(on|off|archived)`\s*\|",
    re.MULTILINE,
)


class LeagueMeasureError(OSError):
    """Catalog missing or unparsable at the resolved repo root."""


@dataclass(frozen=True)
class MeasureCiteVerdict:
    """Result of :func:`validate_measure_cite` — not a PR gate."""

    allowed: bool
    measure_id: str
    state: str | None
    reason: str | None = None


def resolve_repo_root(start: Path | None = None) -> Path:
    """Walk parents from ``start`` (or cwd) until the companion catalog exists."""
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        if (candidate / MEASURE_CATALOG_RELATIVE).is_file():
            return candidate
    raise LeagueMeasureError(
        f"measure catalog not found at {MEASURE_CATALOG_RELATIVE.as_posix()} "
        f"walking up from {here}"
    )


def parse_measure_catalog(text: str) -> dict[str, str]:
    """Parse id → state from the First-cut registry table body."""
    states: dict[str, str] = {}
    for match in _ROW_RE.finditer(text):
        measure_id, state = match.group(1), match.group(2)
        if state not in _VALID_STATES:
            continue
        states[measure_id] = state
    if not states:
        raise LeagueMeasureError("measure catalog table has no data rows")
    return states


def load_measure_states(repo_root: Path | None = None) -> dict[str, str]:
    root = resolve_repo_root(repo_root)
    text = (root / MEASURE_CATALOG_RELATIVE).read_text(encoding="utf-8")
    return parse_measure_catalog(text)


def validate_measure_cite(measure_id: str, repo_root: Path | None = None) -> MeasureCiteVerdict:
    """Allow only ``on`` rows; refuse ``off``, ``archived``, and unknown ids."""
    try:
        states = load_measure_states(repo_root)
    except LeagueMeasureError as exc:
        return MeasureCiteVerdict(
            allowed=False,
            measure_id=measure_id,
            state=None,
            reason=str(exc),
        )
    state = states.get(measure_id)
    if state is None:
        return MeasureCiteVerdict(
            allowed=False,
            measure_id=measure_id,
            state=None,
            reason="unknown measure id",
        )
    if state != "on":
        return MeasureCiteVerdict(
            allowed=False,
            measure_id=measure_id,
            state=state,
            reason=f"measure state is {state!r}, not on",
        )
    return MeasureCiteVerdict(
        allowed=True,
        measure_id=measure_id,
        state="on",
        reason=None,
    )
