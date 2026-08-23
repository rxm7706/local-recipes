"""Unit tests for ``sources.sibling_dreams`` (Story 16.1 / CAP-1)."""

from __future__ import annotations

from pathlib import Path

import pytest
from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import sibling_dreams

_DECK_TITLE = "Herald's Pitch Deck — Moment 1 Orchestration (Consolidated)"


def _dream_text(*, title: str, status: str, owner: str, body: str = "body\n") -> str:
    return (
        f"---\ntitle: {title}\nstatus: {status}\nowner: {owner}\n---\n{body}"
    )


def test_owner_axis_drift_emits_warn(tmp_path: Path, monkeypatch):
    dreams = tmp_path / "docs" / "dreams"
    dreams.mkdir(parents=True)
    (dreams / "herald-pitch.md").write_text(
        _dream_text(title=_DECK_TITLE, status="realized", owner="herald"),
        encoding="utf-8",
    )
    sibling = {
        _DECK_TITLE: {
            "title": _DECK_TITLE,
            "status": "realized",
            "owner": "scribe",
            "content_hash": sibling_dreams._parse_dream_fingerprint(
                _dream_text(title=_DECK_TITLE, status="realized", owner="scribe")
            )["content_hash"],
        }
    }
    # Match local body so only owner differs.
    local_fp = sibling_dreams._parse_dream_fingerprint(
        _dream_text(title=_DECK_TITLE, status="realized", owner="herald")
    )
    sibling[_DECK_TITLE]["content_hash"] = local_fp["content_hash"]
    sibling[_DECK_TITLE]["status"] = "realized"

    monkeypatch.setattr(sibling_dreams, "_operator_token", lambda: "tok")
    monkeypatch.setattr(
        sibling_dreams, "_fetch_sibling_fingerprints", lambda token: sibling
    )

    findings = sibling_dreams.gather(tmp_path)
    assert len(findings) == 1
    f = findings[0]
    assert f.source == Source.SIBLING_DREAMS_DRIFT
    assert f.check == "sibling-dreams-drift"
    assert f.status == DoctorStatus.WARN
    assert f.evidence["axes"] == ["owner"]
    assert "scribe" not in str(f.evidence).lower() or f.evidence["sibling_owner"] == "scribe"
    # No sibling prose stored beyond fingerprints.
    assert "body" not in f.evidence


def test_agreeing_titles_emit_nothing(tmp_path: Path, monkeypatch):
    dreams = tmp_path / "docs" / "dreams"
    dreams.mkdir(parents=True)
    text = _dream_text(title=_DECK_TITLE, status="realized", owner="herald")
    (dreams / "herald-pitch.md").write_text(text, encoding="utf-8")
    fp = sibling_dreams._parse_dream_fingerprint(text)
    monkeypatch.setattr(sibling_dreams, "_operator_token", lambda: "tok")
    monkeypatch.setattr(
        sibling_dreams, "_fetch_sibling_fingerprints", lambda token: {fp["title"]: fp}
    )
    assert sibling_dreams.gather(tmp_path) == ()


def test_no_token_is_silent(tmp_path: Path, monkeypatch):
    dreams = tmp_path / "docs" / "dreams"
    dreams.mkdir(parents=True)
    (dreams / "x.md").write_text(
        _dream_text(title="X", status="draft", owner="herald"), encoding="utf-8"
    )
    monkeypatch.setattr(sibling_dreams, "_operator_token", lambda: None)

    def _forbid(token):
        raise AssertionError("must not fetch without token")

    monkeypatch.setattr(sibling_dreams, "_fetch_sibling_fingerprints", _forbid)
    assert sibling_dreams.gather(tmp_path) == ()


def test_unreachable_sibling_is_silent(tmp_path: Path, monkeypatch):
    dreams = tmp_path / "docs" / "dreams"
    dreams.mkdir(parents=True)
    (dreams / "x.md").write_text(
        _dream_text(title="X", status="draft", owner="herald"), encoding="utf-8"
    )
    monkeypatch.setattr(sibling_dreams, "_operator_token", lambda: "tok")
    monkeypatch.setattr(
        sibling_dreams, "_fetch_sibling_fingerprints", lambda token: None
    )
    assert sibling_dreams.gather(tmp_path) == ()


def test_one_sided_titles_emit_nothing(tmp_path: Path, monkeypatch):
    dreams = tmp_path / "docs" / "dreams"
    dreams.mkdir(parents=True)
    (dreams / "local-only.md").write_text(
        _dream_text(title="Local Only", status="draft", owner="herald"),
        encoding="utf-8",
    )
    monkeypatch.setattr(sibling_dreams, "_operator_token", lambda: "tok")
    monkeypatch.setattr(
        sibling_dreams,
        "_fetch_sibling_fingerprints",
        lambda token: {
            "Sibling Only": {
                "title": "Sibling Only",
                "status": "draft",
                "owner": "scribe",
                "content_hash": "abc",
            }
        },
    )
    assert sibling_dreams.gather(tmp_path) == ()


def test_missing_dreams_dir_is_silent(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(sibling_dreams, "_operator_token", lambda: "tok")
    assert sibling_dreams.gather(tmp_path) == ()
