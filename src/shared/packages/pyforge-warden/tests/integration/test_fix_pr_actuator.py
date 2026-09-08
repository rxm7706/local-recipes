"""Conformance E2E for the fix-PR actuator (Story 6.9).

Drives ``cli.main(["scan", ...])`` in-process (capsys), same as
``test_scan_harness``. The dry-run rows populate ``actuation`` without opening
a socket and leave the verdict/status/exit byte-identical to the no-flag run;
the real ``--open-fix-prs`` row drives the default ``GitHubForgeClient`` against
a LOCAL raw-socket fake forge, reachable only because the actuator's
``_EGRESS_ACTIVE`` marker unlocks the conftest deny-harness carve-out for the
loopback target. A forge failure leaves the exit unchanged plus a stderr line;
a duplicate is skipped; blocking findings still exit non-zero; and a no-flag
run stays byte-identical (``actuation`` is ``null``).

The fake forge is a raw ``socket`` server (bind/listen/accept are not denied by
the harness — only client ``connect`` is), deliberately NOT ``http.server``:
``HTTPServer.server_bind`` calls ``socket.getfqdn`` -> ``gethostbyaddr``, which
the deny harness intercepts (no carve-out) and would crash server startup.
"""

from __future__ import annotations

import json
import socket
import threading
from importlib import resources
from pathlib import Path

import jsonschema

from pyforge.warden.cli import main

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "projects"
VULN_CRITICAL = FIXTURES / "vuln_critical"

VULN_FINDING_ID = "vuln:PDOS-FIXTURE-0001:pdos-vuln-fixture@1.0.0"
DEP002_FINDING_ID = "hygiene:DEP002:pdos-vuln-fixture"
REPO = "octo/warden-test"


def load_schema() -> dict:
    schema_file = resources.files("pyforge.warden") / "data" / "report-schema.json"
    return json.loads(schema_file.read_text(encoding="utf-8"))


def run_scan(capsys, target, *extra: str) -> tuple[int, str, str]:
    capsys.readouterr()
    rc = main(["scan", str(target), "--format", "json", *extra])
    captured = capsys.readouterr()
    return rc, captured.out, captured.err


def parse_report(stdout: str) -> dict:
    document = json.loads(stdout)  # raises unless exactly one JSON document
    jsonschema.Draft202012Validator(load_schema()).validate(document)
    return document


# --- a local raw-socket fake forge ------------------------------------------


class _FakeForge:
    """A single-threaded raw-socket HTTP/1.1 responder on 127.0.0.1. Each
    ``_api`` call is a fresh connection (urllib does not pool across
    ``urlopen`` calls), so a serial accept loop suffices."""

    def __init__(self, responder):
        self._responder = responder
        self.requests: list[tuple[str, str, bytes]] = []
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(("127.0.0.1", 0))
        self._sock.listen(16)
        self._sock.settimeout(0.25)
        self.port = self._sock.getsockname()[1]
        self._stop = False
        self._thread = threading.Thread(target=self._serve, daemon=True)

    @property
    def api_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def __enter__(self) -> _FakeForge:
        self._thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self._stop = True
        self._thread.join(timeout=2)
        self._sock.close()

    def _serve(self) -> None:
        while not self._stop:
            try:
                conn, _ = self._sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            with conn:
                try:
                    self._handle(conn)
                except OSError:
                    pass

    def _handle(self, conn: socket.socket) -> None:
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = conn.recv(4096)
            if not chunk:
                return
            data += chunk
        head, _, rest = data.partition(b"\r\n\r\n")
        lines = head.decode("latin1").split("\r\n")
        method, path, _ = lines[0].split(" ", 2)
        headers = {}
        for line in lines[1:]:
            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip().lower()] = value.strip()
        length = int(headers.get("content-length", "0"))
        body = rest
        while len(body) < length:
            more = conn.recv(4096)
            if not more:
                break
            body += more
        self.requests.append((method, path, body))
        status, payload = self._responder(method, path, body)
        encoded = b"" if payload is None else json.dumps(payload).encode("utf-8")
        response = (
            f"HTTP/1.1 {status} X\r\n"
            "Content-Type: application/json\r\n"
            f"Content-Length: {len(encoded)}\r\n"
            "Connection: close\r\n\r\n"
        ).encode("latin1") + encoded
        conn.sendall(response)


def _happy_responder(method, path, body):
    p = path.split("?", 1)[0]
    if method == "GET" and p.endswith("/pulls"):
        return 200, []  # existing_open_pr -> None
    if method == "GET" and p == f"/repos/{REPO}":
        return 200, {"default_branch": "main"}
    if method == "GET" and "/branches/" in p:
        return 200, {"commit": {"sha": "base", "commit": {"tree": {"sha": "tree"}}}}
    if method == "POST" and p.endswith("/git/commits"):
        return 201, {"sha": "newcommit"}
    if method == "POST" and p.endswith("/git/refs"):
        return 201, {"ref": "refs/heads/warden"}
    if method == "POST" and p.endswith("/pulls"):
        return 201, {"html_url": f"https://forge.example/{REPO}/pull/1"}
    return 404, {"message": "unexpected"}


def _duplicate_responder(method, path, body):
    p = path.split("?", 1)[0]
    if method == "GET" and p.endswith("/pulls"):
        return 200, [{"html_url": f"https://forge.example/{REPO}/pull/9"}]
    return _happy_responder(method, path, body)


def _failing_responder(method, path, body):
    p = path.split("?", 1)[0]
    if method == "GET" and p.endswith("/pulls"):
        return 200, []  # dedup passes, so the open attempt is reached
    return 500, {"message": "forge exploded"}


def _set_forge_env(monkeypatch, api_url):
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.setenv("GITHUB_REPOSITORY", REPO)
    monkeypatch.setenv("GITHUB_API_URL", api_url)


# --- neither flag: byte-identical to pre-6.9 --------------------------------


def test_no_flag_run_leaves_actuation_null_and_byte_identical(capsys):
    rc1, out1, err1 = run_scan(capsys, VULN_CRITICAL)
    rc2, out2, err2 = run_scan(capsys, VULN_CRITICAL)
    assert out1 == out2  # twice-run byte identity (no volatile actuation)
    document = parse_report(out1)
    assert document["actuation"] is None
    assert rc1 == rc2 == 1  # policy-violation, unchanged


# --- dry-run: populated, no socket, verdict identical -----------------------


def test_dry_run_populates_actuation_without_changing_the_verdict(capsys):
    rc_plain, out_plain, _ = run_scan(capsys, VULN_CRITICAL)
    plain = parse_report(out_plain)

    rc_dry, out_dry, err_dry = run_scan(capsys, VULN_CRITICAL, "--fix-prs-dry-run")
    dry = parse_report(out_dry)

    # Verdict/status/exit identical to the no-flag run.
    assert rc_dry == rc_plain == 1
    assert dry["status"] == plain["status"]
    assert dry["exit_code"] == plain["exit_code"]
    assert dry["findings"] == plain["findings"]
    # The ONLY difference is the actuation section.
    assert plain["actuation"] is None
    actuation = dry["actuation"]
    assert actuation["dry_run"] is True
    outcomes = {o["finding_id"]: o for o in actuation["outcomes"]}
    assert set(outcomes) == {VULN_FINDING_ID, DEP002_FINDING_ID}
    assert outcomes[VULN_FINDING_ID]["status"] == "planned"
    assert outcomes[VULN_FINDING_ID]["action"] == "upgrade"
    assert outcomes[DEP002_FINDING_ID]["status"] == "planned"
    assert outcomes[DEP002_FINDING_ID]["action"] == "removal"
    assert all(o["pr_url"] is None for o in actuation["outcomes"])


def test_dry_run_wins_when_both_flags_are_set(capsys):
    # Both flags -> dry-run wins -> planned, no socket, no creds needed.
    rc, out, err = run_scan(
        capsys, VULN_CRITICAL, "--open-fix-prs", "--fix-prs-dry-run"
    )
    document = parse_report(out)
    assert rc == 1
    assert document["actuation"]["dry_run"] is True
    assert {o["status"] for o in document["actuation"]["outcomes"]} == {"planned"}


def test_dry_run_actuation_lines_render_in_text(capsys):
    capsys.readouterr()
    rc = main(["scan", str(VULN_CRITICAL), "--fix-prs-dry-run"])
    out = capsys.readouterr().out
    assert rc == 1
    assert f"[actuation] planned upgrade {VULN_FINDING_ID}" in out
    assert f"[actuation] planned removal {DEP002_FINDING_ID}" in out


# --- real open against the local fake forge ---------------------------------


def test_real_open_records_opened_and_keeps_exit_unchanged(capsys, monkeypatch):
    with _FakeForge(_happy_responder) as forge:
        _set_forge_env(monkeypatch, forge.api_url)
        rc, out, err = run_scan(capsys, VULN_CRITICAL, "--open-fix-prs")
    document = parse_report(out)
    # Blocking findings + --open-fix-prs: exit stays non-zero (false-green
    # stays zero); the actuator never touches the verdict.
    assert rc == 1
    assert document["status"]["value"] == "policy-violation"
    outcomes = {o["finding_id"]: o for o in document["actuation"]["outcomes"]}
    assert set(outcomes) == {VULN_FINDING_ID, DEP002_FINDING_ID}
    assert {o["status"] for o in outcomes.values()} == {"opened"}
    assert all(o["pr_url"] for o in outcomes.values())
    assert err == ""  # no failure summary on a clean open


def test_duplicate_pr_is_skipped_not_reopened(capsys, monkeypatch):
    with _FakeForge(_duplicate_responder) as forge:
        _set_forge_env(monkeypatch, forge.api_url)
        rc, out, err = run_scan(capsys, VULN_CRITICAL, "--open-fix-prs")
    document = parse_report(out)
    assert rc == 1
    outcomes = document["actuation"]["outcomes"]
    assert {o["status"] for o in outcomes} == {"skipped"}
    assert all(o["pr_url"] for o in outcomes)


def test_forge_failure_leaves_exit_unchanged_with_a_stderr_line(
    capsys, monkeypatch
):
    with _FakeForge(_failing_responder) as forge:
        _set_forge_env(monkeypatch, forge.api_url)
        rc, out, err = run_scan(capsys, VULN_CRITICAL, "--open-fix-prs")
    document = parse_report(out)  # stdout is STILL one pure document
    assert rc == 1  # exit unchanged despite the failed opens
    assert {o["status"] for o in document["actuation"]["outcomes"]} == {"failed"}
    assert "fix-pr actuator" in err
    assert "failed" in err


def test_no_creds_records_a_single_failed_resolution(capsys, monkeypatch):
    # --open-fix-prs but no token in the env -> resolution fails loud, opens
    # nothing, one failed record + a stderr line, exit unchanged.
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_REPOSITORY", REPO)
    rc, out, err = run_scan(capsys, VULN_CRITICAL, "--open-fix-prs")
    document = parse_report(out)
    assert rc == 1
    outcomes = document["actuation"]["outcomes"]
    assert len(outcomes) == 1
    assert outcomes[0]["status"] == "failed"
    assert outcomes[0]["finding_id"] == ""
    assert "fix-pr actuator" in err


# --- review-hardening rows (2026-07-24 review pass) -------------------------


def test_baselined_finding_is_not_actuated(capsys, tmp_path):
    # A finding the operator already ACCEPTED via baseline (grandfathered debt)
    # must NOT spawn a remediation PR -- auto-PRs for accepted debt defeat the
    # whole point of grandfathering. Dry-run keeps it credential-free.
    baseline = tmp_path / ".warden-baseline.yaml"
    baseline.write_text(
        "version: 1\n"
        "baseline:\n"
        f"  - id: {VULN_FINDING_ID!r}\n"
        "    expires_at: '2099-01-01T00:00:00+00:00'\n",
        encoding="utf-8",
    )
    rc, out, err = run_scan(
        capsys, VULN_CRITICAL, "--baseline", str(baseline), "--fix-prs-dry-run"
    )
    document = parse_report(out)
    outcomes = {o["finding_id"] for o in document["actuation"]["outcomes"]}
    assert VULN_FINDING_ID not in outcomes  # baselined -> excluded from actuation
    assert DEP002_FINDING_ID in outcomes  # unsuppressed -> still actuatable


def _branch_exists_responder(method, path, body):
    p = path.split("?", 1)[0]
    if method == "GET" and p.endswith("/pulls"):
        return 200, []  # no OPEN pr -> dedup passes, the open attempt is reached
    if method == "POST" and p.endswith("/git/refs"):
        return 422, {"message": "Reference already exists"}
    return _happy_responder(method, path, body)


def test_existing_branch_without_open_pr_is_skipped_not_failed(capsys, monkeypatch):
    # An orphan branch (prior partial open, or a since-closed PR) must resolve
    # to skipped, never a permanent failed loop on every subsequent run.
    with _FakeForge(_branch_exists_responder) as forge:
        _set_forge_env(monkeypatch, forge.api_url)
        rc, out, err = run_scan(capsys, VULN_CRITICAL, "--open-fix-prs")
    document = parse_report(out)
    assert rc == 1  # exit unchanged
    assert {o["status"] for o in document["actuation"]["outcomes"]} == {"skipped"}
    assert err == ""  # a skip is not a failure -> no stderr summary


def _urlless_open_responder(method, path, body):
    p = path.split("?", 1)[0]
    if method == "POST" and p.endswith("/pulls"):
        return 201, {}  # a 2xx with no html_url/url -- not a real success
    return _happy_responder(method, path, body)


def test_open_returning_no_url_is_recorded_failed_not_opened(capsys, monkeypatch):
    with _FakeForge(_urlless_open_responder) as forge:
        _set_forge_env(monkeypatch, forge.api_url)
        rc, out, err = run_scan(capsys, VULN_CRITICAL, "--open-fix-prs")
    document = parse_report(out)
    assert rc == 1
    assert {o["status"] for o in document["actuation"]["outcomes"]} == {"failed"}
    assert "fix-pr actuator" in err
