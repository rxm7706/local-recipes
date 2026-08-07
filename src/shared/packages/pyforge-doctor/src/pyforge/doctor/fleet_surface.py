"""Persistent fleet-health surface -- Story 4.2, FR-11, architecture spine
AD-8.

``AD-8``: the surface is written STRICTLY from ``monitor --fleet``'s own
already-gathered ``Finding``/``Source`` output (Epic 2's existing shape) --
never a second, independent gather path. :func:`build_surface` is a pure
function over ``(findings, axes)``; :func:`write_surface` is the ONE
non-pure step this module adds (a plain file write, no subprocess/MCP call
of its own).

Idempotency (FR-11 AC2, "regenerating from the same underlying findings
produces byte-identical output"): unlike ``DoctorReport`` (which legitimately
timestamps each per-invocation snapshot via ``generated_at``), the surface
carries NO wall-clock field anywhere in its content -- a timestamp would make
every regeneration a spurious diff against a tracked file, defeating the
whole "at-a-glance, diff-when-something-actually-changed" purpose a tracked
surface exists for. ``build_surface`` also sorts its own findings
deterministically (by source, check, status, message) so the OUTPUT is
independent of whatever order the triggering ``monitor --fleet`` run
happened to gather them in.

``schema_version`` starts at ``1`` (NFR-5's existing ``DoctorReport``
precedent, extended to this new artifact per FR-11 AC3)."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from .models import Finding

FLEET_SURFACE_SCHEMA_VERSION = 1


def build_surface(
    findings: Sequence[Finding], *, axes: Sequence[str]
) -> dict[str, object]:
    """Pure -- a deterministic function of ``(findings, axes)`` only, no
    wall-clock read anywhere (FR-11 AC2's idempotency requirement). ``axes``
    is recorded verbatim (sorted, de-duplicated) so the surface documents
    exactly which Watch axes the triggering run covered -- never a
    hardcoded subset (FR-11 AC4), automatically correct for whatever axis
    set ``monitor --fleet`` was invoked with, including Story 4.3's
    ``adoption`` axis with zero changes needed here."""
    sorted_findings = sorted(
        findings,
        key=lambda f: (f.source.value, f.check, f.status.value, f.message),
    )
    ok = sum(1 for f in sorted_findings if f.status.value == "ok")
    warn = sum(1 for f in sorted_findings if f.status.value == "warn")
    fail = sum(1 for f in sorted_findings if f.status.value == "fail")
    return {
        "schema_version": FLEET_SURFACE_SCHEMA_VERSION,
        "axes": sorted(dict.fromkeys(axes)),
        "summary": {"ok": ok, "warn": warn, "fail": fail, "total": len(sorted_findings)},
        "findings": [finding.to_json_dict() for finding in sorted_findings],
    }


def write_surface(
    path: Path, findings: Sequence[Finding], *, axes: Sequence[str]
) -> dict[str, object]:
    """Writes :func:`build_surface`'s document to ``path`` as sorted-key
    JSON (mirrors ``__main__._emit_json``'s own ``sort_keys=True``
    discipline) and returns the document. The write itself is the ONE
    non-pure step in this module -- no gather, no subprocess/MCP call
    (AD-8: strictly derived from already-gathered findings). Creates
    ``path``'s parent directory if missing; overwrites an existing file
    (idempotent regeneration, not an append)."""
    document = build_surface(findings, axes=axes)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return document
