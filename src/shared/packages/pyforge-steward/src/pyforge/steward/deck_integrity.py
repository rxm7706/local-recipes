"""Steward `deck-drift` duty -- flags silent size/etag drift on a pulled
Design deck artifact (Story 59.4 / spec-vocabulary-one-name-one-job CAP-5).

Herald owns the Design pull itself (`herald deck pull`, `.herald/bridge-state.json`'s
per-slug etags); this module owns the *drift* half named on Q10 of that Spec's Dream
rulings: "Herald owns Design pull; detector owns etag/size recurrence." A pulled
`.dc.html` artifact carries no provenance sidecar of its own (unlike a *derived*
export -- `stamps.py`'s `<artifact>.stamp.json` -- which this module deliberately
does not touch or extend); a hand-edit or partial write to the raw pulled file is
therefore invisible to Herald's own tooling as long as `.herald/bridge-state.json`'s
recorded etag stays unchanged. This module closes that gap with its own baseline
sidecar (`.steward/deck-integrity-baseline.json`), fingerprinting the artifact
(size + sha256) the first time it observes a given etag and comparing that
fingerprint again on every later run: an unchanged etag with a changed fingerprint
is exactly "the pull cannot silently rot" -- a finding. An etag that DID change
between runs is a legitimate re-pull, never a finding; the baseline simply advances
to match.

This module never imports `pyforge.herald` (no cross-station import; the estate's
own doctor sources already establish this convention) -- `.herald/bridge-state.json`
is read here as plain JSON, tolerantly (a missing file or missing slug/artifact key
reads as "nothing pulled yet", never an error; a structurally malformed file --
not a JSON object, or a slug entry that isn't one -- is a named finding, since a
hand-edited bridge-state file is itself a plausible tamper vector this detector
exists to catch). `_PROTOTYPE_ARTIFACT_KEY` mirrors `deck_pipeline.PROTOTYPE_ARTIFACT_KEY`
/ `stamps._PROTOTYPE_ARTIFACT_KEY` as a string literal, for the same reason
`stamps.py` itself gives for duplicating it rather than importing it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from pyforge.core.atomic_write import atomic_write_text

from .bootstrap import repo_root
from .interfaces import DutyResult

DEFAULT_BRIDGE_STATE_PATH = Path(".herald/bridge-state.json")
DEFAULT_BASELINE_PATH = Path(".steward/deck-integrity-baseline.json")
_PROTOTYPE_ARTIFACT_KEY = "prototype"


class DeckIntegrityError(Exception):
    """A structurally malformed bridge-state or baseline file."""


@dataclass(frozen=True)
class Fingerprint:
    size: int
    sha256: str


def _fingerprint(path: Path) -> Fingerprint | None:
    try:
        data = path.read_bytes()
    except FileNotFoundError:
        return None
    return Fingerprint(size=len(data), sha256=hashlib.sha256(data).hexdigest())


def _read_bridge_etag(bridge_state_path: Path, slug: str, artifact_key: str) -> str | None:
    try:
        text = bridge_state_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        raise DeckIntegrityError(f"{bridge_state_path} is not valid JSON: {exc}") from exc
    if not isinstance(document, dict):
        raise DeckIntegrityError(f"{bridge_state_path} does not hold a JSON object at its top level")
    entry = document.get(slug)
    if entry is None:
        return None
    if not isinstance(entry, dict):
        raise DeckIntegrityError(f"{bridge_state_path}: slug {slug!r} entry is not a JSON object")
    etags = entry.get("etags")
    if etags is None:
        return None
    if not isinstance(etags, dict):
        raise DeckIntegrityError(f"{bridge_state_path}: slug {slug!r} field 'etags' is not a JSON object")
    etag = etags.get(artifact_key)
    if etag is not None and not isinstance(etag, str):
        raise DeckIntegrityError(f"{bridge_state_path}: slug {slug!r} artifact {artifact_key!r} etag is not a string")
    return etag


def _read_baseline(baseline_path: Path) -> dict:
    try:
        text = baseline_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        raise DeckIntegrityError(f"{baseline_path} is not valid JSON: {exc}") from exc
    if not isinstance(document, dict):
        raise DeckIntegrityError(f"{baseline_path} does not hold a JSON object at its top level")
    return document


def _write_baseline(baseline_path: Path, document: dict) -> None:
    atomic_write_text(baseline_path, json.dumps(document, indent=2, sort_keys=True) + "\n")


@dataclass(frozen=True)
class DriftCheck:
    """The outcome of one `check_drift` call.

    `recorded` distinguishes a baseline write (unseeded->first-observation or
    an advance on a legitimate new pull) from a plain compare, so callers and
    tests can tell "nothing to report, and nothing changed on disk either"
    apart from "nothing to report, but the baseline file just moved."
    """

    drifted: bool
    recorded: bool
    summary: str


def check_drift(
    *,
    slug: str,
    artifact_key: str,
    artifact_path: Path,
    bridge_state_path: Path,
    baseline_path: Path,
) -> DriftCheck:
    current_etag = _read_bridge_etag(bridge_state_path, slug, artifact_key)
    current_fp = _fingerprint(artifact_path)
    document = _read_baseline(baseline_path)
    slug_entry = document.get(slug)
    if not isinstance(slug_entry, dict):
        slug_entry = {}
    recorded_entry = slug_entry.get(artifact_key)

    def _record(reason: str) -> DriftCheck:
        new_slug_entry = dict(slug_entry)
        if current_fp is None:
            new_slug_entry.pop(artifact_key, None)
        else:
            new_slug_entry[artifact_key] = {
                "etag": current_etag,
                "size": current_fp.size,
                "sha256": current_fp.sha256,
            }
        new_document = dict(document)
        if new_slug_entry:
            new_document[slug] = new_slug_entry
        else:
            new_document.pop(slug, None)
        _write_baseline(baseline_path, new_document)
        return DriftCheck(drifted=False, recorded=True, summary=reason)

    if not isinstance(recorded_entry, dict):
        if current_etag is None and current_fp is None:
            return DriftCheck(
                drifted=False,
                recorded=False,
                summary=f"{slug}/{artifact_key}: nothing pulled yet, no baseline needed",
            )
        return _record(f"{slug}/{artifact_key}: first observation recorded")

    recorded_etag = recorded_entry.get("etag")
    recorded_size = recorded_entry.get("size")
    recorded_sha256 = recorded_entry.get("sha256")

    if current_etag != recorded_etag:
        return _record(f"{slug}/{artifact_key}: new pull recorded ({recorded_etag!r} -> {current_etag!r})")

    if current_fp is None:
        return DriftCheck(
            drifted=True,
            recorded=False,
            summary=(
                f"{slug}/{artifact_key}: silent drift -- {artifact_path} is missing but "
                f"etag {current_etag!r} was never re-pulled"
            ),
        )

    if current_fp.size != recorded_size or current_fp.sha256 != recorded_sha256:
        return DriftCheck(
            drifted=True,
            recorded=False,
            summary=(
                f"{slug}/{artifact_key}: silent drift -- {artifact_path} changed "
                f"(size {recorded_size} -> {current_fp.size}) with no recorded new pull "
                f"(etag stayed {current_etag!r})"
            ),
        )

    return DriftCheck(drifted=False, recorded=False, summary=f"{slug}/{artifact_key}: unchanged, no drift")


class DeckDriftDuty:
    name = "deck-drift"

    def run(self, ns: argparse.Namespace) -> DutyResult:
        slug = (getattr(ns, "slug", "") or "").strip()
        path_arg = getattr(ns, "path", None)
        if not slug or not path_arg:
            return DutyResult(ok=False, summary="deck-drift: --slug and --path are required")
        artifact_key = (getattr(ns, "artifact_key", None) or _PROTOTYPE_ARTIFACT_KEY).strip()

        root = repo_root()
        artifact_path = Path(path_arg)
        if not artifact_path.is_absolute():
            artifact_path = root / artifact_path
        bridge_state_arg = getattr(ns, "bridge_state", None)
        bridge_state_path = Path(bridge_state_arg) if bridge_state_arg else root / DEFAULT_BRIDGE_STATE_PATH
        baseline_arg = getattr(ns, "baseline", None)
        baseline_path = Path(baseline_arg) if baseline_arg else root / DEFAULT_BASELINE_PATH

        try:
            result = check_drift(
                slug=slug,
                artifact_key=artifact_key,
                artifact_path=artifact_path,
                bridge_state_path=bridge_state_path,
                baseline_path=baseline_path,
            )
        except DeckIntegrityError as exc:
            return DutyResult(
                ok=False,
                summary=f"deck-drift: {exc}",
                details={"slug": slug, "artifact_key": artifact_key},
            )

        return DutyResult(
            ok=not result.drifted,
            summary=result.summary,
            details={
                "slug": slug,
                "artifact_key": artifact_key,
                "drifted": result.drifted,
                "recorded": result.recorded,
            },
        )
