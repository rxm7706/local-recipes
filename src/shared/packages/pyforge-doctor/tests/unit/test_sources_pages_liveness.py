"""Story 48.2 -- pages-liveness source (spec-pyforge-doctor CAP-91 / FR-24).

Every test replaces ``pages_liveness.urlopen`` and ``cli_bridge.run_git`` with readers of a
recorded fixture under ``tests/fixtures/pages_liveness/``; an autouse guard refuses every socket
(and fails the test at teardown if one was even attempted), so nothing here touches the network.
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
from pathlib import Path
from typing import Any

import pytest

from pyforge.doctor import cli_bridge
from pyforge.doctor.cli_bridge import CliBridgeError
from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.refs import ORIGIN_MAIN
from pyforge.doctor.sources import REGISTRY, pages_liveness
from pyforge.doctor.sources import __main__ as dispatch

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "pages_liveness"
_ALL_FIXTURES = sorted(FIXTURES.glob("*.json"))
_FIXTURE_IDS = [path.stem for path in _ALL_FIXTURES]
_UNAVAILABLE_FIXTURES = [
    path for path in _ALL_FIXTURES if json.loads(path.read_text())["expect"]["check"] == "pages-liveness-unavailable"
]
_URL = "https://rxm7706.github.io/local-recipes/"
_SOURCE_FILE = Path(pages_liveness.__file__)


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

    monkeypatch.setattr(pages_liveness, "urlopen", fake_urlopen)
    monkeypatch.setattr(cli_bridge, "run_git", fake_run_git)
    return recorder


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
    if "cause" in expect:
        assert expect["cause"] in finding.message
        assert finding.evidence["unevaluable"] is True
    for request in recorder.requests:
        assert request["url"] == _URL
        assert request["timeout"] == 10.0
        assert request["agent"] == "pyforge-doctor-pages-liveness"


# --- AC1: fresh, and within a day ---------------------------------------------------------------


def test_site_newer_than_its_inputs_is_one_ok_row_naming_the_url_and_both_dates(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    findings, recorder, _ = _gather(monkeypatch, tmp_path, "site_newer_than_commit.json")
    assert [f.status for f in findings] == [DoctorStatus.OK]
    message = findings[0].message
    assert _URL in message
    assert "2026-10-14T15:46:03Z" in message
    assert "2026-10-14T14:00:00+00:00" in message
    assert recorder.methods == ["HEAD"]


def test_a_commit_23_hours_newer_is_one_ok_row(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    findings, _, _ = _gather(monkeypatch, tmp_path, "commit_23_hours_newer.json")
    assert [(f.check, f.status) for f in findings] == [("pages-liveness", DoctorStatus.OK)]
    assert "2026-10-13T12:00:00Z" in findings[0].message
    assert "2026-10-14T11:00:00+00:00" in findings[0].message


# --- AC2: stale ---------------------------------------------------------------------------------


def test_a_commit_25_hours_newer_is_one_stale_warn_naming_both_dates_the_sha_and_the_lag(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    findings, _, case = _gather(monkeypatch, tmp_path, "commit_25_hours_newer.json")
    assert [(f.check, f.status) for f in findings] == [("pages-liveness-stale", DoctorStatus.WARN)]
    message = findings[0].message
    sha, _, commit_date = case["git_log"].partition(" ")
    assert _URL in message
    assert "2026-10-13T12:00:00Z" in message
    assert commit_date in message
    assert sha in message
    assert "25 hours" in message
    assert "more than" not in message  # a whole 25 hours reads exactly
    assert findings[0].evidence["commit"] == sha


def test_mutation_a_lag_of_exactly_24_hours_is_the_ok_row_not_stale(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """AC9: reporting a lag of exactly 24 hours stale (``>=`` for ``>``) fails here."""
    findings, _, _ = _gather(monkeypatch, tmp_path, "commit_exactly_24_hours_newer.json")
    assert [(f.check, f.status) for f in findings] == [("pages-liveness", DoctorStatus.OK)]
    assert findings[0].evidence["lag_hours"] == 24


# --- AC3: the 2026-10-06 replay ------------------------------------------------------------------


def test_the_2026_10_06_replay_is_stale_by_its_own_figure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    findings, _, _ = _gather(monkeypatch, tmp_path, "replay_2026_10_06.json")
    assert [(f.check, f.status) for f in findings] == [("pages-liveness-stale", DoctorStatus.WARN)]
    # 2026-10-06T03:12Z to 2026-10-08T15:30-05:00 (20:30Z) is 65 h 18 min.
    assert findings[0].evidence["lag_hours"] == 65
    assert findings[0].evidence["lag_hours"] >= 24
    assert "65 hours" in findings[0].message
    assert "2026-10-06T03:12:00Z" in findings[0].message
    assert "2026-10-08T15:30:00-05:00" in findings[0].message


def test_a_stale_lag_never_reads_as_the_threshold(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """24 h 30 min is stale, and its message says "more than 24 hours", never "24 hours" next to a
    rule of "more than 24"."""
    case = {
        **_load("commit_25_hours_newer.json"),
        "git_log": "c4d5e6f708192a3b4c5d6e7f8091a2b3c4d5e6f7 2026-10-14T12:30:00+00:00",
    }
    _install(monkeypatch, case)
    findings = pages_liveness.gather(tmp_path)
    assert [(f.check, f.status) for f in findings] == [("pages-liveness-stale", DoctorStatus.WARN)]
    message = findings[0].message
    assert "more than 24 hours behind" in message
    assert not re.search(r"(?<!than )\b24 hours", message)
    assert findings[0].evidence["lag_hours"] == 24


def test_the_stale_line_keeps_its_evidence_inside_fleet_pictures_cut(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """fleet-picture prints a WARN's first 110 characters: the lag and both dates lead, the URL is last."""
    findings, _, case = _gather(monkeypatch, tmp_path, "replay_2026_10_06.json")
    message = findings[0].message
    cut = message[:110]
    assert "more than 65 hours" in cut
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
    case = _load("commit_25_hours_newer.json")
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


def test_the_published_inputs_are_the_herald_dreams_m1_list() -> None:
    assert pages_liveness.PUBLISHED_INPUTS == (
        "docs/tutorials",
        "docs/how-to",
        "docs/reference",
        "docs/explanation",
        "docs/index.md",
        "docs/404.md",
        "docs/map.yaml",
        "docs/dashboard",
        "docs-site",
        "presentations",
    )
    assert pages_liveness.PAGES_ROOT_URL == _URL
    assert pages_liveness.STALE_AFTER.total_seconds() == 24 * 3600


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
