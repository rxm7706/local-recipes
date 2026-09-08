"""Legacy-fixture recapture tooling (Story B4, DW-B1-1 part a).

The B1/B2/B3 parity fixtures are **shape-only seeds** (``provenance:
"shape-only-seed-B2-needs-B4-recapture"``): their ``expected`` frame is the node's
OWN transform of a representative input, NOT a credentialed legacy capture — so a
green ``parity-diff`` proves port==implementer-belief, not port==legacy
(PARITY_NOTES.md, DW-B1-1 part a). B4 must recapture the fixtures from a REAL
legacy orchestrator run before parity can be trusted as the retirement gate
(AD-19).

This module is that CAPTURE TOOLING. B4 ships the tool; the actual recapture runs
at the attended credentialed event (there is no credentialed ``cf_atlas.db`` in
the loop). In-loop it is exercised against a SYNTHETIC capture source — no real DB
is touched. A recaptured fixture is stamped ``provenance:
"credentialed-legacy-capture-<date>"`` so it is distinguishable from a shape-only
seed and the harness/PARITY_NOTES can tell which fixtures still need recapture.

Lives in ``tests/parity/`` (writes fixture files; not pipeline code).
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import date
from pathlib import Path
from typing import Protocol

CREDENTIALED_PROVENANCE_PREFIX = "credentialed-legacy-capture"
SHAPE_ONLY_PROVENANCE_PREFIX = "shape-only-seed"


class LegacyCaptureSource(Protocol):
    """A source of legacy per-node input/output snapshots.

    The ATTENDED event supplies an implementation backed by the credentialed
    ``cf_atlas.db`` (reading each node's real input frames + its real legacy
    OUTPUT snapshot). Tests supply a synthetic implementation — so no real DB is
    ever opened in the loop.
    """

    def node_names(self) -> Iterable[str]:
        ...

    def capture(self, node: str) -> dict:
        """Return ``{"phase": str, "inputs": {catalog: [records]},
        "expected": {output: [records]}}`` for one node, captured from the real
        legacy run."""
        ...


def capture_legacy_fixtures(
    source: LegacyCaptureSource,
    out_dir: str | Path,
    *,
    node_names: Iterable[str] | None = None,
    captured_at: str | None = None,
) -> list[Path]:
    """Recapture legacy fixtures for the given nodes into ``out_dir`` in the
    harness fixture shape, stamped with the credentialed-capture provenance.

    Returns the list of written fixture paths. Does NOT read any real DB itself —
    all legacy extraction is delegated to ``source`` (synthetic in tests,
    credentialed at the event).
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = captured_at or date.today().isoformat()
    provenance = f"{CREDENTIALED_PROVENANCE_PREFIX}-{stamp}"

    nodes = list(node_names) if node_names is not None else list(source.node_names())
    written: list[Path] = []
    for node in nodes:
        snap = source.capture(node)
        fixture = {
            "phase": snap.get("phase", node),
            "node": node,
            "provenance": provenance,
            "inputs": snap["inputs"],
            "expected": snap["expected"],
        }
        path = out / f"{node}.json"
        path.write_text(json.dumps(fixture, indent=2) + "\n", encoding="utf-8")
        written.append(path)
    return written


def is_shape_only_seed(fixture_path: str | Path) -> bool:
    """True if a fixture is still a shape-only seed (recapture pending)."""
    data = json.loads(Path(fixture_path).read_text(encoding="utf-8"))
    prov = data.get("provenance") or ""  # tolerate an explicit `null`
    return prov.startswith(SHAPE_ONLY_PROVENANCE_PREFIX)


def is_credentialed_capture(fixture_path: str | Path) -> bool:
    """True if a fixture has been recaptured from a credentialed legacy run."""
    data = json.loads(Path(fixture_path).read_text(encoding="utf-8"))
    return (data.get("provenance") or "").startswith(CREDENTIALED_PROVENANCE_PREFIX)
