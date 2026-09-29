"""Story 59.4 — `pyforge steward deck-drift --slug <slug> --path <path>`.

Flags silent size/etag drift on a pulled Design deck artifact: Herald owns
the pull itself (`.herald/bridge-state.json`); this duty owns the recurrence
check against its own baseline sidecar. Every test uses a `tmp_path` for
both the bridge-state file and the baseline, never the real (gitignored,
usually-absent) `.herald/bridge-state.json` in this checkout.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyforge.steward.cli import DUTIES, build_parser, main, resolve_duty
from pyforge.steward.deck_integrity import (
    DeckDriftDuty,
    DeckIntegrityError,
    check_drift,
)
from pyforge.steward.interfaces import Duty

EXIT_USAGE = 2


def _write_bridge_state(root: Path, slug: str, artifact_key: str, etag: str | None) -> Path:
    bridge_state = root / ".herald" / "bridge-state.json"
    bridge_state.parent.mkdir(parents=True, exist_ok=True)
    document = {slug: {"project_id": "proj-1", "etags": {artifact_key: etag} if etag else {}, "last_pull": None}}
    bridge_state.write_text(json.dumps(document), encoding="utf-8")
    return bridge_state


def _artifact(root: Path, content: bytes = b"hello world") -> Path:
    path = root / "deck.dc.html"
    path.write_bytes(content)
    return path


def _ns(
    slug: str = "agentic-sdlc",
    path: str = "deck.dc.html",
    *,
    artifact_key: str | None = None,
    bridge_state: str | None = None,
    baseline: str | None = None,
):
    argv = ["deck-drift", "--slug", slug, "--path", path]
    if artifact_key is not None:
        argv += ["--artifact-key", artifact_key]
    if bridge_state is not None:
        argv += ["--bridge-state", bridge_state]
    if baseline is not None:
        argv += ["--baseline", baseline]
    return build_parser().parse_args(argv)


def test_deck_drift_is_a_registered_duty():
    assert "deck-drift" in DUTIES
    impl = resolve_duty("deck-drift")
    assert isinstance(impl, DeckDriftDuty)
    assert isinstance(impl, Duty)
    assert impl.name == "deck-drift"


def test_slug_and_path_are_required():
    assert main(["deck-drift"]) == EXIT_USAGE
    assert main(["deck-drift", "--slug", "agentic-sdlc"]) == EXIT_USAGE
    assert main(["deck-drift", "--path", "deck.dc.html"]) == EXIT_USAGE


def test_nothing_pulled_yet_is_not_a_finding(tmp_path: Path):
    bridge_state = tmp_path / ".herald" / "bridge-state.json"
    baseline = tmp_path / ".steward" / "deck-integrity-baseline.json"
    artifact = tmp_path / "missing.dc.html"

    result = check_drift(
        slug="agentic-sdlc",
        artifact_key="prototype",
        artifact_path=artifact,
        bridge_state_path=bridge_state,
        baseline_path=baseline,
    )

    assert result.drifted is False
    assert result.recorded is False
    assert not baseline.exists()


def test_first_observation_is_recorded_not_flagged(tmp_path: Path):
    _write_bridge_state(tmp_path, "agentic-sdlc", "prototype", "etag-1")
    artifact = _artifact(tmp_path)
    baseline = tmp_path / ".steward" / "deck-integrity-baseline.json"

    result = check_drift(
        slug="agentic-sdlc",
        artifact_key="prototype",
        artifact_path=artifact,
        bridge_state_path=tmp_path / ".herald" / "bridge-state.json",
        baseline_path=baseline,
    )

    assert result.drifted is False
    assert result.recorded is True
    document = json.loads(baseline.read_text(encoding="utf-8"))
    assert document["agentic-sdlc"]["prototype"]["etag"] == "etag-1"


def test_unchanged_etag_and_fingerprint_is_no_drift(tmp_path: Path):
    _write_bridge_state(tmp_path, "agentic-sdlc", "prototype", "etag-1")
    artifact = _artifact(tmp_path)
    bridge_state_path = tmp_path / ".herald" / "bridge-state.json"
    baseline_path = tmp_path / ".steward" / "deck-integrity-baseline.json"

    first = check_drift(
        slug="agentic-sdlc",
        artifact_key="prototype",
        artifact_path=artifact,
        bridge_state_path=bridge_state_path,
        baseline_path=baseline_path,
    )
    assert first.recorded is True

    second = check_drift(
        slug="agentic-sdlc",
        artifact_key="prototype",
        artifact_path=artifact,
        bridge_state_path=bridge_state_path,
        baseline_path=baseline_path,
    )

    assert second.drifted is False
    assert second.recorded is False


def test_a_new_pull_advances_the_baseline_without_a_finding(tmp_path: Path):
    artifact = _artifact(tmp_path, content=b"version one")
    bridge_state_path = tmp_path / ".herald" / "bridge-state.json"
    baseline_path = tmp_path / ".steward" / "deck-integrity-baseline.json"
    _write_bridge_state(tmp_path, "agentic-sdlc", "prototype", "etag-1")

    first = check_drift(
        slug="agentic-sdlc",
        artifact_key="prototype",
        artifact_path=artifact,
        bridge_state_path=bridge_state_path,
        baseline_path=baseline_path,
    )
    assert first.recorded is True

    # A legitimate re-pull: both the etag and the file change together.
    artifact.write_bytes(b"version two, much longer content than before")
    _write_bridge_state(tmp_path, "agentic-sdlc", "prototype", "etag-2")

    second = check_drift(
        slug="agentic-sdlc",
        artifact_key="prototype",
        artifact_path=artifact,
        bridge_state_path=bridge_state_path,
        baseline_path=baseline_path,
    )

    assert second.drifted is False
    assert second.recorded is True
    document = json.loads(baseline_path.read_text(encoding="utf-8"))
    assert document["agentic-sdlc"]["prototype"]["etag"] == "etag-2"


def test_a_changed_file_with_an_unchanged_etag_is_silent_drift(tmp_path: Path):
    artifact = _artifact(tmp_path, content=b"original content")
    bridge_state_path = tmp_path / ".herald" / "bridge-state.json"
    baseline_path = tmp_path / ".steward" / "deck-integrity-baseline.json"
    _write_bridge_state(tmp_path, "agentic-sdlc", "prototype", "etag-1")

    first = check_drift(
        slug="agentic-sdlc",
        artifact_key="prototype",
        artifact_path=artifact,
        bridge_state_path=bridge_state_path,
        baseline_path=baseline_path,
    )
    assert first.recorded is True

    # A hand-edit: the file changes on disk but the etag stays put.
    artifact.write_bytes(b"tampered content, etag never moved")

    second = check_drift(
        slug="agentic-sdlc",
        artifact_key="prototype",
        artifact_path=artifact,
        bridge_state_path=bridge_state_path,
        baseline_path=baseline_path,
    )

    assert second.drifted is True
    assert "silent drift" in second.summary


def test_a_missing_file_with_an_unchanged_etag_is_silent_drift(tmp_path: Path):
    artifact = _artifact(tmp_path)
    bridge_state_path = tmp_path / ".herald" / "bridge-state.json"
    baseline_path = tmp_path / ".steward" / "deck-integrity-baseline.json"
    _write_bridge_state(tmp_path, "agentic-sdlc", "prototype", "etag-1")

    first = check_drift(
        slug="agentic-sdlc",
        artifact_key="prototype",
        artifact_path=artifact,
        bridge_state_path=bridge_state_path,
        baseline_path=baseline_path,
    )
    assert first.recorded is True

    artifact.unlink()

    second = check_drift(
        slug="agentic-sdlc",
        artifact_key="prototype",
        artifact_path=artifact,
        bridge_state_path=bridge_state_path,
        baseline_path=baseline_path,
    )

    assert second.drifted is True
    assert "missing" in second.summary


@pytest.mark.parametrize(
    "bad_document",
    ["not an object at all", json.dumps([1, 2, 3]), json.dumps({"agentic-sdlc": "not-an-object"})],
    ids=["not-json", "not-a-json-object", "slug-entry-not-a-json-object"],
)
def test_a_malformed_bridge_state_raises_named_error(tmp_path: Path, bad_document: str):
    bridge_state_path = tmp_path / ".herald" / "bridge-state.json"
    bridge_state_path.parent.mkdir(parents=True)
    bridge_state_path.write_text(bad_document, encoding="utf-8")

    with pytest.raises(DeckIntegrityError):
        check_drift(
            slug="agentic-sdlc",
            artifact_key="prototype",
            artifact_path=tmp_path / "deck.dc.html",
            bridge_state_path=bridge_state_path,
            baseline_path=tmp_path / ".steward" / "deck-integrity-baseline.json",
        )


def test_a_malformed_baseline_raises_named_error(tmp_path: Path):
    baseline_path = tmp_path / ".steward" / "deck-integrity-baseline.json"
    baseline_path.parent.mkdir(parents=True)
    baseline_path.write_text("not json", encoding="utf-8")

    with pytest.raises(DeckIntegrityError):
        check_drift(
            slug="agentic-sdlc",
            artifact_key="prototype",
            artifact_path=tmp_path / "deck.dc.html",
            bridge_state_path=tmp_path / ".herald" / "bridge-state.json",
            baseline_path=baseline_path,
        )


def test_duty_reports_a_malformed_bridge_state_as_a_failed_duty_not_a_crash(monkeypatch, tmp_path: Path):
    bridge_state_path = tmp_path / ".herald" / "bridge-state.json"
    bridge_state_path.parent.mkdir(parents=True)
    bridge_state_path.write_text("not json", encoding="utf-8")
    monkeypatch.setattr("pyforge.steward.deck_integrity.repo_root", lambda: tmp_path)

    result = DeckDriftDuty().run(_ns(bridge_state=str(bridge_state_path), baseline=str(tmp_path / "baseline.json")))

    assert result.ok is False
    assert "not valid JSON" in result.summary


def test_duty_reports_no_drift_as_success(monkeypatch, tmp_path: Path):
    _write_bridge_state(tmp_path, "agentic-sdlc", "prototype", "etag-1")
    _artifact(tmp_path)
    monkeypatch.setattr("pyforge.steward.deck_integrity.repo_root", lambda: tmp_path)

    duty = DeckDriftDuty()
    ns = _ns()
    first = duty.run(ns)
    assert first.ok is True

    second = duty.run(ns)
    assert second.ok is True
    assert second.details["drifted"] is False


def test_duty_reports_drift_as_failure(monkeypatch, tmp_path: Path):
    _write_bridge_state(tmp_path, "agentic-sdlc", "prototype", "etag-1")
    artifact = _artifact(tmp_path)
    monkeypatch.setattr("pyforge.steward.deck_integrity.repo_root", lambda: tmp_path)

    duty = DeckDriftDuty()
    ns = _ns()
    first = duty.run(ns)
    assert first.ok is True

    artifact.write_bytes(b"tampered, no new pull recorded")
    second = duty.run(ns)

    assert second.ok is False
    assert second.details["drifted"] is True
