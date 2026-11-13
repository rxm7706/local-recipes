"""Story 19.2: unit tests for the local landing ship caller (no network).

Story 52.2 (a fix under spec-pyforge-herald CAP-38): the on-pr-close body names this checkout's forge, read from
``roots.this`` of a roster through ``pyforge.core.cutover_root.forge_slug_for``. This is a package-half module: every
case passes ``repo=`` or writes its own roster under ``tmp_path`` and works there, none walks up to the live
``docs/governance/guild-roster.json``, and none reads a flag tree (the autouse guard below fails any case that does).
"""

from __future__ import annotations

import json
import time
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import pytest
from pyforge.core import cutover_root, roster

from pyforge.herald import local_ship, webhook, webhook_host

A_SLUG = "rxm7706/local-recipes"
SHA = "a" * 40


def _landing_subject(station: str, key: str) -> str:
    slug = roster.long_form(station)
    return f"Merge {slug}/{key} into main"


def _write_roster(root: Path, payload: object) -> Path:
    path = root / local_ship.ROSTER_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


@pytest.fixture(autouse=True)
def _no_flag_tree(monkeypatch: pytest.MonkeyPatch) -> None:
    """Herald's landing record is not a root-of-record consumer: any read of the flag tree fails the case."""

    def _refuse(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("local_ship must not read the flag tree (src/platform/config/flags.json)")

    for name in ("resolve_flags_path", "read_cutover_root", "root_of_record"):
        monkeypatch.setattr(cutover_root, name, _refuse)


@pytest.fixture
def checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A temporary checkout whose roster names ``local-recipes``, made the working directory."""
    _write_roster(tmp_path, {"roots": {"this": "local-recipes"}})
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _herald_landing() -> local_ship.LandingCommit:
    return local_ship.LandingCommit(SHA, _landing_subject("herald", "19-2"), "herald", "19-2")


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
    on_close = json.loads(local_ship.build_on_pr_close_body(landing, repo=A_SLUG))

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


@pytest.mark.usefixtures("checkout")
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


@pytest.mark.usefixtures("checkout")
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


def test_post_signed_records_url_error_instead_of_exiting() -> None:
    with patch.object(local_ship, "urlopen", side_effect=URLError("down")):
        status, body = local_ship.post_signed("http://127.0.0.1/x", b"s", b"{}")
    assert status is None
    assert body == {"error": "POST http://127.0.0.1/x failed: down"}


def test_post_signed_records_a_response_timeout() -> None:
    # urllib wraps only connect-time errors in URLError; a timeout while
    # waiting for the response surfaces as a bare TimeoutError.
    with patch.object(local_ship, "urlopen", side_effect=TimeoutError("timed out")):
        status, body = local_ship.post_signed("http://127.0.0.1/x", b"s", b"{}")
    assert status is None
    assert "TimeoutError" in str(body["error"])


def test_request_timeout_outlasts_the_webhook_host_timeout() -> None:
    assert local_ship.REQUEST_TIMEOUT_SECONDS > webhook_host.REQUEST_TIMEOUT_SECONDS


def test_deliver_landing_posts_both_webhooks() -> None:
    landing = local_ship.LandingCommit("d" * 40, _landing_subject("herald", "19-2"), "herald", "19-2")
    with patch.object(
        local_ship,
        "post_signed",
        side_effect=[(201, {"a": 1}), (201, {"b": 2})],
    ) as post:
        out = local_ship.deliver_landing("http://127.0.0.1:8001/", b"s", landing, repo=A_SLUG)
    assert post.call_count == 2
    urls = [call.args[0] for call in post.call_args_list]
    assert urls[0].endswith("/stations/herald/api/v1/webhooks/on-ship")
    assert urls[1].endswith("/stations/herald/api/v1/webhooks/on-pr-close")
    assert out["target"] == "http://127.0.0.1:8001"
    assert out["on_ship"] == {"url": urls[0], "status": 201, "body": {"a": 1}}
    assert out["on_pr_close"] == {"url": urls[1], "status": 201, "body": {"b": 2}}


def test_deliver_landing_keeps_on_ship_when_on_pr_close_fails() -> None:
    landing = local_ship.LandingCommit("d" * 40, _landing_subject("herald", "19-2"), "herald", "19-2")
    with patch.object(
        local_ship,
        "post_signed",
        side_effect=[(201, {"station": "herald"}), (None, {"error": "POST x failed: refused"})],
    ):
        out = local_ship.deliver_landing("http://127.0.0.1:8001", b"s", landing, repo=A_SLUG)
    assert out["on_ship"]["status"] == 201
    assert out["on_ship"]["body"] == {"station": "herald"}
    assert out["on_pr_close"]["status"] is None
    assert out["on_pr_close"]["body"] == {"error": "POST x failed: refused"}


@pytest.mark.usefixtures("checkout")
def test_main_exits_nonzero_and_prints_both_when_one_request_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("HERALD_WEBHOOK_SECRET", "s")
    landing = local_ship.LandingCommit("a" * 40, _landing_subject("herald", "19-2"), "herald", "19-2")
    with patch.object(local_ship, "resolve_landing_commit", return_value=landing):
        with patch.object(
            local_ship,
            "post_signed",
            side_effect=[(201, {"station": "herald"}), (None, {"error": "POST x failed: refused"})],
        ):
            assert local_ship.main(["--url", "http://127.0.0.1:9"]) == 1
    printed = json.loads(capsys.readouterr().out)
    assert printed["target"] == "http://127.0.0.1:9"
    assert printed["on_ship"]["status"] == 201
    assert printed["on_pr_close"]["status"] is None


@pytest.mark.usefixtures("checkout")
def test_default_url_is_the_rendered_host_port(monkeypatch: pytest.MonkeyPatch) -> None:
    assert local_ship.DEFAULT_HOST_URL == "http://127.0.0.1:8001"
    monkeypatch.delenv("HERALD_WEBHOOK_URL", raising=False)
    monkeypatch.setenv("HERALD_WEBHOOK_SECRET", "s")
    landing = local_ship.LandingCommit("a" * 40, _landing_subject("herald", "19-2"), "herald", "19-2")
    ok = {"on_ship": {"status": 201, "body": {}}, "on_pr_close": {"status": 201, "body": {}}}
    with patch.object(local_ship, "resolve_landing_commit", return_value=landing):
        with patch.object(local_ship, "deliver_landing", return_value=ok) as deliver:
            assert local_ship.main([]) == 0
    assert deliver.call_args.args[0] == "http://127.0.0.1:8001"
    assert deliver.call_args.kwargs == {"repo": A_SLUG}


@pytest.mark.usefixtures("checkout")
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


# --- Story 52.2: the forge slug is this checkout's, read at call time -----------------------------------------------


def test_roots_this_local_recipes_names_a_in_the_on_pr_close_body(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_roster(tmp_path, {"roots": {"this": "local-recipes"}})
    nested = tmp_path / "src" / "deep"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)  # the roster is found by walking up from the working directory
    body = json.loads(local_ship.build_on_pr_close_body(_herald_landing()))
    assert body["event_id"] == f"{A_SLUG}@{SHA}"
    assert body["evidence"][0]["url"] == f"https://github.com/{A_SLUG}/commit/{SHA}"


def test_roots_this_foundry_names_cores_foundry_slug(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_roster(tmp_path, {"roots": {"this": "foundry"}})
    monkeypatch.chdir(tmp_path)
    foundry = cutover_root.FORGE_SLUGS["foundry"]
    assert foundry != A_SLUG
    body = json.loads(local_ship.build_on_pr_close_body(_herald_landing()))
    assert body["event_id"] == f"{foundry}@{SHA}"
    assert body["evidence"][0]["url"] == f"https://github.com/{foundry}/commit/{SHA}"


def test_the_slug_is_read_at_call_time_not_import(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    roster_path = _write_roster(tmp_path, {"roots": {"this": "local-recipes"}})
    monkeypatch.chdir(tmp_path)
    assert local_ship.this_forge_slug() == A_SLUG
    roster_path.write_text(json.dumps({"roots": {"this": "foundry"}}), encoding="utf-8")
    assert local_ship.this_forge_slug() == cutover_root.FORGE_SLUGS["foundry"]


def test_an_explicit_repo_wins_and_reads_no_roster(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_roster(tmp_path, {"roots": {"this": "foundry"}})
    monkeypatch.chdir(tmp_path)
    with patch.object(local_ship, "this_forge_slug", side_effect=AssertionError("roster read")) as read:
        body = json.loads(local_ship.build_on_pr_close_body(_herald_landing(), repo="acme/widgets"))
    read.assert_not_called()
    assert body["event_id"] == f"acme/widgets@{SHA}"
    assert body["evidence"][0]["url"] == f"https://github.com/acme/widgets/commit/{SHA}"


@pytest.mark.parametrize(
    "payload",
    [{}, {"roots": {}}, {"roots": {"this": ""}}, {"roots": "local-recipes"}, []],
    ids=["no-roots", "no-this", "empty-this", "roots-not-object", "not-an-object"],
)
def test_a_roster_without_roots_this_is_a_named_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, payload: object
) -> None:
    _write_roster(tmp_path, payload)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(local_ship.ForgeSlugError, match=r"declares no 'roots\.this'"):
        local_ship.build_on_pr_close_body(_herald_landing())


def test_no_roster_above_the_working_directory_is_a_named_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    with pytest.raises(local_ship.ForgeSlugError, match="guild-roster.json at or above"):
        local_ship.build_on_pr_close_body(_herald_landing())


def test_an_unknown_root_or_unreadable_roster_is_a_named_refusal(tmp_path: Path) -> None:
    _write_roster(tmp_path, {"roots": {"this": "elsewhere"}})
    with pytest.raises(local_ship.ForgeSlugError, match="unknown root 'elsewhere'"):
        local_ship.this_forge_slug(tmp_path)
    (tmp_path / local_ship.ROSTER_RELATIVE).write_text("{not json", encoding="utf-8")
    with pytest.raises(local_ship.ForgeSlugError, match="unreadable roster"):
        local_ship.this_forge_slug(tmp_path)


def test_deliver_landing_refuses_before_any_post(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    with patch.object(local_ship, "post_signed") as post:
        with pytest.raises(local_ship.ForgeSlugError):
            local_ship.deliver_landing("http://127.0.0.1:9", b"s", _herald_landing())
    post.assert_not_called()


@pytest.mark.parametrize("roster_payload", [None, {"roots": {}}], ids=["no-roster", "no-roots-this"])
def test_main_prints_the_refusal_and_returns_1_before_any_post(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    roster_payload: object,
) -> None:
    if roster_payload is not None:
        _write_roster(tmp_path, roster_payload)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HERALD_WEBHOOK_SECRET", "s")
    with patch.object(local_ship, "resolve_landing_commit", return_value=_herald_landing()):
        with patch.object(local_ship, "post_signed") as post:
            assert local_ship.main(["--url", "http://127.0.0.1:9"]) == 1
    post.assert_not_called()
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "refusing to ship" in captured.err
    assert "roots.this" in captured.err or "guild-roster.json" in captured.err
    assert A_SLUG not in captured.err


def test_main_reads_the_roster_of_its_repo_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    checkout = tmp_path / "b"
    _write_roster(checkout, {"roots": {"this": "foundry"}})
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    monkeypatch.setenv("HERALD_WEBHOOK_SECRET", "s")
    with patch.object(local_ship, "resolve_landing_commit", return_value=_herald_landing()):
        with patch.object(local_ship, "post_signed", side_effect=[(201, {}), (201, {})]) as post:
            assert local_ship.main(["--url", "http://127.0.0.1:9", "--repo-root", str(checkout)]) == 0
    close_body = json.loads(post.call_args_list[1].args[2])
    assert close_body["event_id"] == f"{cutover_root.FORGE_SLUGS['foundry']}@{SHA}"
    assert "on_pr_close" in capsys.readouterr().out
