"""Stories 48.2 and 48.3 -- pages-liveness source (spec-pyforge-doctor CAP-91 / FR-24).

Every test replaces ``pages_liveness.urlopen``, ``pages_liveness.now`` and ``cli_bridge.run_git``
with readers of a recorded fixture under ``tests/fixtures/pages_liveness/`` (every fixture that
reaches the rule names its ``now``); an autouse guard refuses every socket (and fails the test at
teardown if one was even attempted), so nothing here touches the network.
"""

from __future__ import annotations

import ast
import email.message
import http.client
import io
import json
import re
import socket
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import yaml

from pyforge.doctor import cli_bridge
from pyforge.doctor.cli_bridge import CliBridgeError
from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.refs import ORIGIN_MAIN
from pyforge.doctor.sources import REGISTRY, pages_liveness
from pyforge.doctor.sources import __main__ as dispatch

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "pages_liveness"
_ALL_FIXTURES = sorted(FIXTURES.glob("*.json"))
_FIXTURE_IDS = [path.stem for path in _ALL_FIXTURES]
_UNAVAILABLE_FIXTURES = [
    path for path in _ALL_FIXTURES if json.loads(path.read_text())["expect"]["check"] == "pages-liveness-unavailable"
]
_URL = "https://rxm7706.github.io/local-recipes/"
_SOURCE_FILE = Path(pages_liveness.__file__)
_REPO_ROOT = Path(__file__).resolve().parents[6]
_PAGES_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "pages.yml"
#: Story 48.3: on pages.yml's filter, these build or deploy the site and publish nothing (Story 48.2's
#: change log); every other filter entry is a published input.
_NOT_PUBLISHED = frozenset(
    {
        ".github/workflows/pages.yml",
        "scripts/pages_*.py",
        "src/shared/packages/pyforge-steward/src/pyforge/steward/pages.py",
        "src/shared/packages/pyforge-steward/src/pyforge/steward/marketplace_pages.py",
        "src/shared/packages/pyforge-herald/src/pyforge/herald/pages_env.py",
    }
)
#: Read by a fixture-less clock: a date no fixture is near, so a read the test did not expect never
#: passes for a fresh one.
_UNSET_CLOCK = datetime(1970, 1, 1, tzinfo=UTC)


# --- the socket guard ---------------------------------------------------------------------------


class _SocketRefusedError(OSError):
    """Raised by the guard in place of any socket; an OSError so urllib reacts as it would offline."""


@pytest.fixture(autouse=True)
def socket_attempts(monkeypatch: pytest.MonkeyPatch):
    """Refuse every socket, DNS lookup and connection; a test that even tried one fails."""
    attempts: list[str] = []

    def _refuse(name: str):
        def _guard(*args: Any, **kwargs: Any):
            attempts.append(name)
            raise _SocketRefusedError(f"test opened a socket via socket.{name}")

        return _guard

    for name in ("socket", "create_connection", "getaddrinfo"):
        monkeypatch.setattr(socket, name, _refuse(name))
    yield attempts
    assert not attempts, f"a test reached the network: {attempts}"


# --- fixture readers ----------------------------------------------------------------------------


def _load(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _headers(raw: dict[str, str]) -> email.message.Message:
    message = email.message.Message()
    for key, value in raw.items():
        message[key] = value
    return message


class _FakeResponse:
    def __init__(self, status: int, headers: email.message.Message) -> None:
        self.status = status
        self.headers = headers

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def read(self, *args: Any) -> bytes:  # pragma: no cover - the source never reads the body
        raise AssertionError("pages-liveness must never read the body")


def _respond(req: urllib.request.Request, spec: dict[str, Any]) -> _FakeResponse:
    error = spec.get("error")
    if error == "URLError":
        raise urllib.error.URLError(spec["reason"])
    if error == "timeout":
        raise TimeoutError("timed out")
    status = spec["status"]
    headers = _headers(spec.get("headers", {}))
    if 200 <= status < 300:
        return _FakeResponse(status, headers)
    # urllib's default opener raises HTTPError for every status outside 2xx.
    raise urllib.error.HTTPError(req.full_url, status, http.client.responses.get(status, ""), headers, None)


class _Recorder:
    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []
        self.git_argvs: list[list[str]] = []
        self.clock_reads = 0

    @property
    def methods(self) -> list[str]:
        return [request["method"] for request in self.requests]


def _install(monkeypatch: pytest.MonkeyPatch, case: dict[str, Any]) -> _Recorder:
    recorder = _Recorder()

    def fake_urlopen(req: urllib.request.Request, timeout: float | None = None) -> _FakeResponse:
        method = req.get_method()
        recorder.requests.append(
            {"method": method, "url": req.full_url, "timeout": timeout, "agent": req.get_header("User-agent")}
        )
        spec = case.get(method.lower())
        assert spec is not None, f"unexpected {method} request"
        return _respond(req, spec)

    def fake_run_git(cwd: Path, args: list[str], *, timeout: float = 30.0, ok_exit_codes=frozenset({0})) -> str:
        recorder.git_argvs.append(list(args))
        if "git_error" in case:
            raise CliBridgeError(case["git_error"])
        line = case["git_log"]
        return f"{line}\n" if line else ""

    def fake_now() -> datetime:
        recorder.clock_reads += 1
        return _parse_now(case["now"]) if "now" in case else _UNSET_CLOCK

    monkeypatch.setattr(pages_liveness, "urlopen", fake_urlopen)
    monkeypatch.setattr(pages_liveness, "now", fake_now)
    monkeypatch.setattr(cli_bridge, "run_git", fake_run_git)
    return recorder


def _parse_now(text: str) -> datetime:
    parsed = datetime.fromisoformat(text)
    assert parsed.tzinfo is not None, f"a fixture clock names its zone: {text!r}"
    return parsed


def _gather(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, name: str):
    case = _load(name)
    recorder = _install(monkeypatch, case)
    return pages_liveness.gather(tmp_path), recorder, case


# --- every fixture yields its recorded verdict --------------------------------------------------


@pytest.mark.parametrize("fixture_path", _ALL_FIXTURES, ids=_FIXTURE_IDS)
def test_every_fixture_yields_exactly_its_recorded_verdict(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fixture_path: Path
) -> None:
    findings, recorder, case = _gather(monkeypatch, tmp_path, fixture_path.name)
    expect = case["expect"]
    assert len(findings) == 1
    (finding,) = findings
    assert finding.source is Source.PAGES_LIVENESS
    assert finding.check == expect["check"]
    assert finding.status.value == expect["status"]
    assert recorder.methods == expect["requests"]
    if "lag_hours" in expect:
        assert finding.evidence["lag_hours"] == expect["lag_hours"]
    if "waited_hours" in expect:
        assert finding.evidence["waited_hours"] == expect["waited_hours"]
    if "now" in case:
        # The rule reads the injected clock once and names it.
        assert recorder.clock_reads == 1
        assert _parse_now(finding.evidence["now"]) == _parse_now(case["now"])
    else:
        assert recorder.clock_reads == 0
    if "cause" in expect:
        assert expect["cause"] in finding.message
        assert finding.evidence["unevaluable"] is True
    for request in recorder.requests:
        assert request["url"] == _URL
        assert request["timeout"] == 10.0
        assert request["agent"] == "pyforge-doctor-pages-liveness"


# --- AC1: fresh, and within a day ---------------------------------------------------------------


def test_site_newer_than_its_inputs_is_one_ok_row_naming_the_url_both_dates_and_the_clock(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    findings, recorder, _ = _gather(monkeypatch, tmp_path, "site_newer_than_commit.json")
    assert [f.status for f in findings] == [DoctorStatus.OK]
    message = findings[0].message
    assert _URL in message
    assert "2026-10-14T15:46:03Z" in message
    assert "2026-10-14T14:00:00+00:00" in message
    assert "deployed after it (clock 2026-10-14T16:41:00Z)" in message
    assert recorder.methods == ["HEAD"]


def test_an_input_waiting_23_hours_is_one_ok_row(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    findings, _, _ = _gather(monkeypatch, tmp_path, "input_waited_23_hours.json")
    assert [(f.check, f.status) for f in findings] == [("pages-liveness", DoctorStatus.OK)]
    message = findings[0].message
    assert "2026-10-13T12:00:00Z" in message
    assert "2026-10-13T14:00:00+00:00" in message
    assert "not yet deployed, waiting within 24 hours (clock 2026-10-14T13:00:00Z)" in message


# --- AC2: stale ---------------------------------------------------------------------------------


def test_an_input_waiting_25_hours_is_one_stale_warn_naming_both_dates_the_sha_and_the_wait(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """48.3 AC4: deployed at T, an input landing at T+2 h, the clock at T+2 h+25 h -- the stall
    within a day of the last good deploy, which the commit-against-header rule read as OK."""
    findings, _, case = _gather(monkeypatch, tmp_path, "input_waited_25_hours.json")
    assert [(f.check, f.status) for f in findings] == [("pages-liveness-stale", DoctorStatus.WARN)]
    message = findings[0].message
    sha, _, commit_date = case["git_log"].partition(" ")
    assert message.startswith("Pages input waited 25 hours: last-modified 2026-10-13T12:00:00Z, ")
    assert _URL in message
    assert commit_date in message
    assert sha in message
    assert "2026-10-14T15:00:00Z" in message
    assert "more than" not in message  # a whole 25 hours reads exactly
    assert findings[0].evidence["commit"] == sha
    assert findings[0].evidence["lag_hours"] == 2
    assert findings[0].evidence["waited_hours"] == 25
    assert findings[0].evidence["now"] == "2026-10-14T15:00:00Z"


def test_mutation_a_wait_of_exactly_24_hours_is_the_ok_row_not_stale(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """48.3 AC6: reporting a wait of exactly 24 hours stale (``>=`` for ``>``) fails here."""
    findings, _, _ = _gather(monkeypatch, tmp_path, "input_waited_exactly_24_hours.json")
    assert [(f.check, f.status) for f in findings] == [("pages-liveness", DoctorStatus.OK)]
    assert findings[0].evidence["waited_hours"] == 24


def test_a_wait_of_24_hours_and_one_second_is_stale(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    findings, _, _ = _gather(monkeypatch, tmp_path, "input_waited_24_hours_and_one_second.json")
    assert [(f.check, f.status) for f in findings] == [("pages-liveness-stale", DoctorStatus.WARN)]
    assert "Pages input waited more than 24 hours: " in findings[0].message


def test_mutation_a_fresh_input_on_a_two_day_old_deploy_is_the_ok_row(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """48.3 AC4/AC6: an input that landed fifteen minutes ago is in its build-and-deploy window,
    however old the deploy; the commit-against-header rule (47 h 45 min) read it stale."""
    findings, _, _ = _gather(monkeypatch, tmp_path, "fresh_input_on_a_two_day_old_deploy.json")
    assert [(f.check, f.status) for f in findings] == [("pages-liveness", DoctorStatus.OK)]
    assert findings[0].evidence["lag_hours"] == 47
    assert findings[0].evidence["waited_hours"] == 0
    assert "2026-10-14T12:00:00Z" in findings[0].message


@pytest.mark.parametrize(
    "clock",
    ["2026-10-14T16:41:00Z", "2026-10-15T16:00:00Z", "2026-11-14T00:00:00Z", "2027-10-14T00:00:00Z"],
)
def test_an_input_the_site_was_deployed_after_is_the_ok_row_whatever_the_clock(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, clock: str
) -> None:
    case = {**_load("site_newer_than_commit.json"), "now": clock}
    _install(monkeypatch, case)
    findings = pages_liveness.gather(tmp_path)
    assert [(f.check, f.status) for f in findings] == [("pages-liveness", DoctorStatus.OK)]
    assert findings[0].evidence["waited_hours"] == 0
    assert findings[0].evidence["now"] == clock


def test_an_input_dated_at_the_deploy_itself_is_the_ok_row(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Stale needs ``last-modified`` before the commit: a commit at the deploy's own second is published."""
    case = {
        **_load("site_newer_than_commit.json"),
        "git_log": "3c1f0a9d2b7e4f6a8c5d1e0b9a7f6e5d4c3b2a10 2026-10-14T15:46:03+00:00",
        "now": "2026-10-20T00:00:00Z",
    }
    _install(monkeypatch, case)
    findings = pages_liveness.gather(tmp_path)
    assert [(f.check, f.status) for f in findings] == [("pages-liveness", DoctorStatus.OK)]


def test_mutation_the_rule_reads_the_injected_clock_never_the_real_one(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """48.3 AC6: reading ``datetime.now`` in place of the module's ``now`` fails here -- the
    fixture's clock is in October 2026, a day after the input; any later real clock reads stale."""
    findings, recorder, _ = _gather(monkeypatch, tmp_path, "input_waited_23_hours.json")
    assert recorder.clock_reads == 1
    assert [(f.check, f.status) for f in findings] == [("pages-liveness", DoctorStatus.OK)]
    assert findings[0].evidence["now"] == "2026-10-14T13:00:00Z"


def test_the_module_clock_is_an_aware_utc_now() -> None:
    before = datetime.now(UTC)
    reading = pages_liveness._utc_now()
    assert reading.tzinfo is not None
    assert before <= reading <= datetime.now(UTC) + timedelta(seconds=1)


# --- AC3: the 2026-10-06 replay ------------------------------------------------------------------


def test_the_2026_10_06_replay_is_stale_by_its_own_figure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    findings, _, _ = _gather(monkeypatch, tmp_path, "replay_2026_10_06.json")
    assert [(f.check, f.status) for f in findings] == [("pages-liveness-stale", DoctorStatus.WARN)]
    # 2026-10-06T03:12Z to 2026-10-08T15:30-05:00 (20:30Z) is 65 h 18 min; from that landing to the
    # clock (2026-10-12T03:12Z, six days after the deploy) is 78 h 42 min.
    assert findings[0].evidence["lag_hours"] == 65
    assert findings[0].evidence["waited_hours"] == 78
    assert "more than 78 hours" in findings[0].message
    assert "2026-10-06T03:12:00Z" in findings[0].message
    assert "2026-10-08T15:30:00-05:00" in findings[0].message


def test_a_stale_wait_never_reads_as_the_threshold(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """24 h 30 min is stale, and its message says "more than 24 hours", never "24 hours" next to a
    rule of "more than 24"."""
    case = {**_load("input_waited_25_hours.json"), "now": "2026-10-14T14:30:00Z"}
    _install(monkeypatch, case)
    findings = pages_liveness.gather(tmp_path)
    assert [(f.check, f.status) for f in findings] == [("pages-liveness-stale", DoctorStatus.WARN)]
    message = findings[0].message
    assert "waited more than 24 hours:" in message
    assert not re.search(r"(?<!than )\b24 hours", message)
    assert findings[0].evidence["waited_hours"] == 24


def test_the_stale_line_keeps_its_evidence_inside_fleet_pictures_cut(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """fleet-picture prints a WARN's first 110 characters: the wait and both dates lead, the URL is last."""
    findings, _, case = _gather(monkeypatch, tmp_path, "replay_2026_10_06.json")
    message = findings[0].message
    cut = message[:110]
    assert "more than 78 hours" in cut
    assert "2026-10-06T03:12:00Z" in cut
    assert "2026-10-08T15:30:00-05:00" in cut
    assert message.endswith(_URL)
    assert case["git_log"].split()[0] in message


# --- AC4: HEAD then GET -------------------------------------------------------------------------


def test_mutation_get_follows_a_non_2xx_head(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """AC9: skipping the GET after a non-2xx HEAD fails here."""
    findings, recorder, _ = _gather(monkeypatch, tmp_path, "head_405_get_200.json")
    assert recorder.methods == ["HEAD", "GET"]
    assert [(f.check, f.status) for f in findings] == [("pages-liveness", DoctorStatus.OK)]
    assert findings[0].evidence["requests"] == ["HEAD 405", "GET 200"]


def test_head_200_with_the_header_makes_exactly_one_request(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    findings, recorder, _ = _gather(monkeypatch, tmp_path, "site_newer_than_commit.json")
    assert recorder.methods == ["HEAD"]
    assert findings[0].evidence["requests"] == ["HEAD 200"]


@pytest.mark.parametrize(("name", "status"), [("head_404_get_404.json", 404), ("head_503_get_503.json", 503)])
def test_non_2xx_on_both_requests_is_one_unavailable_warn_naming_the_status(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, name: str, status: int
) -> None:
    findings, recorder, _ = _gather(monkeypatch, tmp_path, name)
    assert recorder.methods == ["HEAD", "GET"]
    assert [(f.check, f.status) for f in findings] == [("pages-liveness-unavailable", DoctorStatus.WARN)]
    assert f"HEAD {status}, GET {status}" in findings[0].message


# --- AC5: never a false clean -------------------------------------------------------------------


@pytest.mark.parametrize("fixture_path", _UNAVAILABLE_FIXTURES, ids=[p.stem for p in _UNAVAILABLE_FIXTURES])
def test_mutation_an_unreadable_side_is_never_the_ok_row(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fixture_path: Path
) -> None:
    """AC9: returning the OK row for an unreadable site (or git read) fails here."""
    findings, _, case = _gather(monkeypatch, tmp_path, fixture_path.name)
    assert [(f.check, f.status) for f in findings] == [("pages-liveness-unavailable", DoctorStatus.WARN)]
    assert not any(f.status is DoctorStatus.OK for f in findings)
    assert case["expect"]["cause"] in findings[0].message


def test_every_fixture_that_reaches_the_rule_names_its_clock() -> None:
    """48.3 AC5: a fixture with a verdict names the ``now`` it was judged at; an unreadable one
    never reaches the rule, so it names none (and the every-fixture test proves no clock read)."""
    for path in _ALL_FIXTURES:
        case = json.loads(path.read_text(encoding="utf-8"))
        reaches_rule = case["expect"]["check"] != "pages-liveness-unavailable"
        assert ("now" in case) is reaches_rule, path.name


def test_the_unavailable_set_covers_every_named_cause() -> None:
    assert {p.name for p in _UNAVAILABLE_FIXTURES} == {
        "head_404_get_404.json",
        "head_503_get_503.json",
        "offline_url_error.json",
        "socket_timeout.json",
        "no_last_modified.json",
        "last_modified_not_a_date.json",
        "git_error.json",
        "git_log_empty.json",
    }


def test_a_git_error_names_its_first_line_and_never_asks_the_site(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    findings, recorder, _ = _gather(monkeypatch, tmp_path, "git_error.json")
    assert recorder.methods == []
    assert "fatal: bad revision" in findings[0].message
    assert "hint: run git fetch" not in findings[0].message


@pytest.mark.parametrize(
    "line",
    [
        "deadbeef not-a-date",
        "deadbeef 2026-10-14T14:00:00",  # no zone: never compared as if it were UTC
        " 2026-10-14T14:00:00+00:00",
    ],
)
def test_an_unreadable_git_line_is_unavailable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, line: str) -> None:
    case = {**_load("site_newer_than_commit.json"), "git_log": line}
    recorder = _install(monkeypatch, case)
    findings = pages_liveness.gather(tmp_path)
    assert [(f.check, f.status) for f in findings] == [("pages-liveness-unavailable", DoctorStatus.WARN)]
    assert recorder.methods == []


def test_a_head_405_then_get_url_error_is_unavailable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    case = {**_load("head_405_get_200.json"), "get": {"error": "URLError", "reason": "connection reset"}}
    recorder = _install(monkeypatch, case)
    findings = pages_liveness.gather(tmp_path)
    assert recorder.methods == ["HEAD", "GET"]
    assert [(f.check, f.status) for f in findings] == [("pages-liveness-unavailable", DoctorStatus.WARN)]
    assert "GET https://rxm7706.github.io/local-recipes/: URLError: connection reset" in findings[0].message


def test_an_http_error_response_is_closed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """HEAD 405 raises an HTTPError carrying the response; the source closes it explicitly (not
    only when the exception is collected) and asks with GET."""
    _install(monkeypatch, _load("head_405_get_200.json"))
    closed: list[int] = []
    fake_urlopen = pages_liveness.urlopen

    class _RecordingHTTPError(urllib.error.HTTPError):
        def close(self) -> None:
            closed.append(self.code)
            super().close()

    def _urlopen(req: urllib.request.Request, timeout: float | None = None) -> Any:
        if req.get_method() == "HEAD":
            raise _RecordingHTTPError(req.full_url, 405, "Method Not Allowed", _headers({}), io.BytesIO(b"no"))
        return fake_urlopen(req, timeout=timeout)

    monkeypatch.setattr(pages_liveness, "urlopen", _urlopen)
    findings = pages_liveness.gather(tmp_path)
    assert [(f.check, f.status) for f in findings] == [("pages-liveness", DoctorStatus.OK)]
    assert closed == [405]


def test_a_dropped_connection_is_unavailable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _install(monkeypatch, _load("site_newer_than_commit.json"))

    def _dropped(req: urllib.request.Request, timeout: float | None = None) -> None:
        raise http.client.RemoteDisconnected("Remote end closed connection without response")

    monkeypatch.setattr(pages_liveness, "urlopen", _dropped)
    findings = pages_liveness.gather(tmp_path)
    assert [(f.check, f.status) for f in findings] == [("pages-liveness-unavailable", DoctorStatus.WARN)]
    assert "RemoteDisconnected" in findings[0].message


def test_an_unexpected_exception_degrades_to_one_unavailable_warn(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def _boom(cwd: Path, args: list[str], **kwargs: Any) -> str:
        raise RuntimeError("unforeseen")

    monkeypatch.setattr(cli_bridge, "run_git", _boom)
    findings = pages_liveness.gather(tmp_path)
    assert [(f.check, f.status) for f in findings] == [("pages-liveness-unavailable", DoctorStatus.WARN)]
    assert "RuntimeError: unforeseen" in findings[0].message


def test_a_zoneless_http_date_reads_as_utc(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    case = _load("input_waited_25_hours.json")
    case["head"] = {"status": 200, "headers": {"last-modified": "Tue, 13 Oct 2026 12:00:00 -0000"}}
    _install(monkeypatch, case)
    findings = pages_liveness.gather(tmp_path)
    assert findings[0].check == "pages-liveness-stale"
    assert findings[0].evidence["last_modified"] == "2026-10-13T12:00:00Z"


def test_a_response_without_a_status_attribute_reads_its_code(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _install(monkeypatch, _load("site_newer_than_commit.json"))

    class _CodeOnly:
        headers = _headers({"last-modified": "Wed, 14 Oct 2026 15:46:03 GMT"})

        def __enter__(self) -> _CodeOnly:
            return self

        def __exit__(self, *exc: object) -> None:
            return None

        def getcode(self) -> int:
            return 200

    monkeypatch.setattr(pages_liveness, "urlopen", lambda req, timeout=None: _CodeOnly())
    findings = pages_liveness.gather(tmp_path)
    assert [(f.check, f.status) for f in findings] == [("pages-liveness", DoctorStatus.OK)]


# --- AC6: warn never moves the exit code --------------------------------------------------------


@pytest.mark.parametrize("fixture_path", _ALL_FIXTURES, ids=_FIXTURE_IDS)
def test_the_dispatcher_exits_zero_and_prints_a_json_list_on_every_fixture(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], fixture_path: Path
) -> None:
    case = json.loads(fixture_path.read_text(encoding="utf-8"))
    _install(monkeypatch, case)
    assert dispatch.main(["pages-liveness", "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)
    assert isinstance(rows, list)
    assert len(rows) == 1
    for row in rows:
        assert row["source"] == "pages-liveness"
        expected = "ok" if row["check"] == "pages-liveness" else "warn"
        assert row["status"] == expected == case["expect"]["status"]


@pytest.mark.parametrize("fixture_path", _ALL_FIXTURES, ids=_FIXTURE_IDS)
def test_mutation_no_finding_is_ever_fail(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fixture_path: Path) -> None:
    """AC9: emitting any finding as ``fail`` fails here (AD-2: warn never moves the exit code)."""
    findings, _, _ = _gather(monkeypatch, tmp_path, fixture_path.name)
    assert all(f.status is not DoctorStatus.FAIL for f in findings)
    assert all(f.status is DoctorStatus.WARN for f in findings if f.check != "pages-liveness")


# --- AC7: wired ---------------------------------------------------------------------------------


def test_the_source_is_registered_runtime_with_subject_steward_and_owner_doctor() -> None:
    (registration,) = [r for r in REGISTRY if r.source is Source.PAGES_LIVENESS]
    assert Source.PAGES_LIVENESS.value == "pages-liveness"
    assert (registration.scope, registration.subject_station, registration.owning_station) == (
        "runtime",
        "steward",
        "doctor",
    )
    assert dispatch.DISPATCH["pages-liveness"] is pages_liveness.gather


# --- AC8: boundaries hold -----------------------------------------------------------------------


def test_mutation_the_git_argv_names_the_full_refname_never_a_bare_main(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """AC9: a bare ``main`` (or ``origin/main``) in the git argv fails here (CAP-85)."""
    _, recorder, _ = _gather(monkeypatch, tmp_path, "site_newer_than_commit.json")
    (argv,) = recorder.git_argvs
    assert ORIGIN_MAIN == "refs/remotes/origin/main"
    assert argv[:5] == ["log", "-1", "--first-parent", "--format=%H %cI", "refs/remotes/origin/main"]
    assert "main" not in argv
    assert "origin/main" not in argv
    assert not [arg for arg in argv if arg.startswith("origin/")]
    assert "fetch" not in argv
    separator = argv.index("--")
    assert tuple(argv[separator + 1 :]) == pages_liveness.PUBLISHED_INPUTS


def _pages_push_paths() -> list[str]:
    data = yaml.safe_load(_PAGES_WORKFLOW.read_text(encoding="utf-8"))
    # PyYAML (YAML 1.1) reads the bare ``on:`` key as the boolean True.
    triggers = data.get("on", data.get(True))
    paths = triggers["push"]["paths"]
    assert isinstance(paths, list) and paths, f"{_PAGES_WORKFLOW} carries no on.push.paths filter"
    return [str(path) for path in paths]


def test_the_published_inputs_are_pages_yml_s_filter_less_the_named_exclusions() -> None:
    """48.3 AC1: the source's inputs are the deploy's own trigger filter (each trailing ``/**``
    dropped) less what builds or deploys the site and publishes nothing; a filter change is
    steward's, and this pin names what the source must follow."""
    filter_paths = [path.removesuffix("/**") for path in _pages_push_paths()]
    missing_exclusions = sorted(_NOT_PUBLISHED - set(filter_paths))
    assert not missing_exclusions, f"named exclusions no longer on pages.yml's filter: {missing_exclusions}"
    expected = set(filter_paths) - _NOT_PUBLISHED
    inputs = pages_liveness.PUBLISHED_INPUTS
    duplicates = sorted({path for path in inputs if inputs.count(path) > 1})
    assert not duplicates, f"PUBLISHED_INPUTS repeats {duplicates}"
    missing_from_source = sorted(expected - set(inputs))
    not_on_filter = sorted(set(inputs) - expected)
    assert not missing_from_source and not not_on_filter, (
        f"PUBLISHED_INPUTS lacks pages.yml filter paths {missing_from_source}; "
        f"PUBLISHED_INPUTS names paths not on the filter (or excluded) {not_on_filter}"
    )


def test_mutation_the_marketplace_tree_is_a_published_input() -> None:
    """48.3 AC2/AC6: dropping ``docs/foundry/marketplace`` (steward Story 109.3) fails here and in
    the pin above; a stuck marketplace-only deploy would read clean."""
    assert "docs/foundry/marketplace" in pages_liveness.PUBLISHED_INPUTS


def test_mutation_no_excluded_path_is_a_published_input() -> None:
    """48.3 AC6: adding an excluded path (``scripts/pages_*.py``) to the inputs fails here and in the
    pin above: a build-script edit publishes nothing new."""
    assert not set(pages_liveness.PUBLISHED_INPUTS) & _NOT_PUBLISHED


def test_the_url_and_the_threshold_are_constants() -> None:
    assert pages_liveness.PAGES_ROOT_URL == _URL
    assert pages_liveness.STALE_AFTER.total_seconds() == 24 * 3600


def test_the_comments_name_pages_yml_and_the_pages_row_never_a_retired_source() -> None:
    """48.3 AC3: the comments say where the inputs and the 24 h come from; neither names
    ``dashboard.deploy`` nor the herald Dream's M1 list as the source."""
    text = _SOURCE_FILE.read_text(encoding="utf-8")
    assert "dashboard.deploy" not in text
    assert "M1" not in text
    assert ".github/workflows/pages.yml" in text
    assert "docs/governance/ci-surfaces.yaml" in text
    assert "``pages`` row" in text


def _module_tree() -> ast.Module:
    return ast.parse(_SOURCE_FILE.read_text(encoding="utf-8"))


def test_the_module_imports_no_subprocess_and_reads_no_environment() -> None:
    imported: set[str] = set()
    for node in ast.walk(_module_tree()):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imported.add(node.module)
    assert not {name for name in imported if name.split(".")[0] in {"subprocess", "os", "socket", "requests"}}


def test_the_module_names_no_gh_no_github_api_and_no_token() -> None:
    tree = _module_tree()
    docstrings = {
        id(node.body[0].value)
        for node in ast.walk(tree)
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef))
        and node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
    }
    literals = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings
    ]
    text = _SOURCE_FILE.read_text(encoding="utf-8")
    assert "gh" not in literals
    assert not [value for value in literals if "api.github.com" in value]
    for forbidden in ("GH_TOKEN", "GITHUB_TOKEN", "Authorization", "Bearer"):
        assert forbidden not in text


def test_the_socket_guard_is_alive(socket_attempts: list[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """With the real ``urlopen`` back in place, the guard refuses the connection: the source reads
    it as unavailable (offline), and the guard recorded the attempt (then cleared, so teardown passes)."""
    recorder = _install(monkeypatch, _load("site_newer_than_commit.json"))
    monkeypatch.setattr(pages_liveness, "urlopen", urllib.request.urlopen)
    findings = pages_liveness.gather(tmp_path)
    assert recorder.git_argvs  # the git side was read through the fake
    assert [(f.check, f.status) for f in findings] == [("pages-liveness-unavailable", DoctorStatus.WARN)]
    assert socket_attempts, "the guard never saw the connection attempt"
    socket_attempts.clear()
