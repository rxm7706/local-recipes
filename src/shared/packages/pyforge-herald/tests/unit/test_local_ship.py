"""Story 19.2: unit tests for the local landing ship caller (no network)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from pyforge.core import roster
from pyforge.herald import local_ship, webhook


def _landing_subject(station: str, key: str) -> str:
    slug = roster.long_form(station)
    return f"Merge {slug}/{key} into main"


@pytest.mark.parametrize("station", roster.STATIONS)
def test_classify_landing_subject_one_per_station(station: str) -> None:
    classified = local_ship.classify_landing_subject(_landing_subject(station, "1-1"))
    assert classified is not None
    short, key = classified
    assert short == station
    assert key.hyphen_form() == "1-1"


def test_non_landing_subject_refuses_before_send(tmp_path: Path) -> None:
    landing = local_ship.LandingCommit(
        sha="abc123",
        subject="chore: not a merge",
        station="herald",
        story_key="19-2",
    )
    with pytest.raises(SystemExit):
        local_ship.classify_landing_subject(landing.subject)


def test_handlers_accept_bodies_from_local_ship(tmp_path: Path) -> None:
    landing = local_ship.LandingCommit(
        sha="deadbeef" * 5,
        subject=_landing_subject("marshal", "20-10"),
        station="marshal",
        story_key="20-10",
    )
    on_ship = json.loads(local_ship.build_on_ship_body(landing))
    on_close = json.loads(local_ship.build_on_pr_close_body(landing))

    ship_resp = webhook.handle_on_ship(tmp_path, on_ship)
    assert ship_resp.status == 201

    close_resp = webhook.handle_on_pr_close(tmp_path, on_close)
    assert close_resp.status == 201
    assert "claim_id" in close_resp.body


def test_signature_round_trips_like_webhook() -> None:
    secret = b"unit-test-secret"
    body = local_ship.build_on_ship_body(
        local_ship.LandingCommit("a" * 40, _landing_subject("warden", "11-1"), "warden", "11-1")
    )
    ts = "1700000000"
    header = local_ship._sign(secret, ts, body)
    assert webhook.verify_signature(secret, body, header, ts) is True


def test_main_refuses_unset_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HERALD_WEBHOOK_SECRET", raising=False)
    assert local_ship.main(["--url", "http://127.0.0.1:9"]) == 1


def test_main_refuses_non_loopback_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HERALD_WEBHOOK_SECRET", "s")
    assert local_ship.main(["--url", "http://192.168.1.1:8000"]) == 1


def test_resolve_landing_commit_rejects_non_landing(tmp_path: Path) -> None:
    with patch.object(
        local_ship.subprocess,
        "run",
        return_value=type("R", (), {"returncode": 0, "stdout": "sha\tnot a landing", "stderr": ""})(),
    ):
        with pytest.raises(SystemExit, match="not a landing"):
            local_ship.resolve_landing_commit(tmp_path, "sha")


def test_main_does_not_post_when_resolve_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HERALD_WEBHOOK_SECRET", "s")
    with patch.object(local_ship, "post_signed") as post:
        with patch.object(local_ship, "resolve_landing_commit", side_effect=SystemExit(1)):
            with pytest.raises(SystemExit):
                local_ship.main(["--url", "http://127.0.0.1:9"])
        post.assert_not_called()
