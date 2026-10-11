"""Story 19.2: unit tests for the local landing ship caller (no network)."""

from __future__ import annotations

import json
import time
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError

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
    assert local_ship.classify_landing_subject("chore: not a merge") is None
    with patch.object(
        local_ship.subprocess,
        "run",
        return_value=type("R", (), {"returncode": 0, "stdout": "sha\tchore: not a merge", "stderr": ""})(),
    ):
        with pytest.raises(SystemExit, match="not a landing merge"):
            local_ship.resolve_landing_commit(tmp_path, "sha")


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
    ts = str(int(time.time()))
    header = local_ship._sign(secret, ts, body)
    assert webhook.verify_signature(secret, body, header, ts) is True


def test_main_refuses_unset_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HERALD_WEBHOOK_SECRET", raising=False)
    assert local_ship.main(["--url", "http://127.0.0.1:9"]) == 1


def test_main_refuses_non_loopback_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HERALD_WEBHOOK_SECRET", "s")
    assert local_ship.main(["--url", "http://192.168.1.1:8000"]) == 1


def test_main_refuses_non_http_scheme(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HERALD_WEBHOOK_SECRET", "s")
    assert local_ship.main(["--url", "file:///tmp/x"]) == 1


def test_main_exits_nonzero_when_host_returns_401(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HERALD_WEBHOOK_SECRET", "s")
    landing = local_ship.LandingCommit("a" * 40, _landing_subject("herald", "19-2"), "herald", "19-2")
    with patch.object(local_ship, "resolve_landing_commit", return_value=landing):
        with patch.object(
            local_ship,
            "deliver_landing",
            return_value={"on_ship": {"status": 401, "body": {}}, "on_pr_close": {"status": 201, "body": {}}},
        ):
            assert local_ship.main(["--url", "http://127.0.0.1:9"]) == 1


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


def test_resolve_landing_commit_from_explicit_sha(tmp_path: Path) -> None:
    subject = _landing_subject("herald", "19-2")
    sha = "a" * 40
    with patch.object(
        local_ship.subprocess,
        "run",
        return_value=type("R", (), {"returncode": 0, "stdout": f"{sha}\t{subject}", "stderr": ""})(),
    ):
        landing = local_ship.resolve_landing_commit(tmp_path, sha)
    assert landing.sha == sha
    assert landing.station == "herald"
    assert landing.story_key == "19-2"


def test_resolve_landing_commit_scans_origin_main(tmp_path: Path) -> None:
    subject = _landing_subject("scribe", "3-1")
    with patch.object(
        local_ship.subprocess,
        "run",
        return_value=type(
            "R",
            (),
            {
                "returncode": 0,
                "stdout": f"{'b' * 40}\tchore: noop\n{'c' * 40}\t{subject}",
                "stderr": "",
            },
        )(),
    ):
        landing = local_ship.resolve_landing_commit(tmp_path, None)
    assert landing.subject == subject
    assert landing.station == "scribe"


def test_resolve_landing_commit_commit_not_found(tmp_path: Path) -> None:
    with patch.object(
        local_ship.subprocess,
        "run",
        return_value=type("R", (), {"returncode": 1, "stdout": "", "stderr": "nope"})(),
    ):
        with pytest.raises(SystemExit, match="commit not found"):
            local_ship.resolve_landing_commit(tmp_path, "missing")


def test_post_signed_success_and_http_error() -> None:
    class OkResp:
        status = 201

        def read(self) -> bytes:
            return b'{"ok": true}'

        def __enter__(self) -> OkResp:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    with patch.object(local_ship, "urlopen", return_value=OkResp()):
        status, body = local_ship.post_signed("http://127.0.0.1/x", b"s", b"{}")
    assert status == 201
    assert body == {"ok": True}

    err = HTTPError("http://127.0.0.1/x", 502, "bad", {}, BytesIO(b"not-json"))
    with patch.object(local_ship, "urlopen", side_effect=err):
        status, body = local_ship.post_signed("http://127.0.0.1/x", b"s", b"{}")
    assert status == 502
    assert "raw" in body


def test_post_signed_url_error_exits() -> None:
    with patch.object(local_ship, "urlopen", side_effect=URLError("down")):
        with pytest.raises(SystemExit, match="POST .* failed"):
            local_ship.post_signed("http://127.0.0.1/x", b"s", b"{}")


def test_deliver_landing_posts_both_webhooks() -> None:
    landing = local_ship.LandingCommit("d" * 40, _landing_subject("herald", "19-2"), "herald", "19-2")
    with patch.object(
        local_ship,
        "post_signed",
        side_effect=[(201, {"a": 1}), (201, {"b": 2})],
    ) as post:
        out = local_ship.deliver_landing("http://127.0.0.1:8000/", b"s", landing)
    assert post.call_count == 2
    urls = [call.args[0] for call in post.call_args_list]
    assert urls[0].endswith("/stations/herald/api/v1/webhooks/on-ship")
    assert urls[1].endswith("/stations/herald/api/v1/webhooks/on-pr-close")
    assert out["on_ship"]["status"] == 201
    assert out["on_pr_close"]["status"] == 201


def test_main_returns_zero_on_success(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("HERALD_WEBHOOK_SECRET", "s")
    landing = local_ship.LandingCommit("a" * 40, _landing_subject("herald", "19-2"), "herald", "19-2")
    ok = {
        "landing": {},
        "on_ship": {"status": 201, "body": {}},
        "on_pr_close": {"status": 201, "body": {}},
    }
    with patch.object(local_ship, "resolve_landing_commit", return_value=landing):
        with patch.object(local_ship, "deliver_landing", return_value=ok):
            assert local_ship.main(["--url", "http://127.0.0.1:9"]) == 0
    assert "on_ship" in capsys.readouterr().out
