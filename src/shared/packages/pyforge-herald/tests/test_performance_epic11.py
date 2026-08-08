"""Story 11.4: performance testing, scaled to what is actually
CLI-testable in this architecture (see
``docs/dreams/herald-moments-2-4-live-backend.md``).

The original AC has four bullets:

* "CLI commands <1s (95th percentile)" -- real, tested below: seed a
  moderately-sized local dataset (100 records per Moment, written directly
  via each module's own storage functions -- ``progress.upsert``/
  ``claims.create``+``claims.publish``/``notices.author_notice`` -- not
  through 100 CLI subprocess calls, which would measure process-spawn
  overhead instead of the command itself) and time
  ``herald progress``/``herald success list``/``herald notice list``
  end to end via ``cli.main`` (no subprocess -- in-process timing, the same
  boundary the CLI's own test suite already exercises everywhere else).
* "Archive search responsive" -- covered by the same three timed listing
  calls above (each already includes the module's own filter/search path
  -- ``list_records``/``list_claims``/``list_notices``); there is no
  separate "archive search" surface to exercise on top of that.
* "Web tabs <2s load" -- **not tested here.** There is no server and no
  browser in this test suite (Herald's web dashboard is a static Vite
  bundle reading a pre-generated JSON snapshot -- see
  ``docs/reference/mcp-server-architecture.md``-adjacent web README); a
  "load time" claim would have to fake an entire browser/network stack to
  even approximate, and the result would prove nothing about the actual
  static bundle. Left honestly untested rather than inventing a fake
  proxy for a claim no code path in this package exercises.
* "No memory leaks during long sessions" -- **not tested here.** ``herald``
  is a one-shot CLI process (``cli.main`` runs once and exits) with no
  long-running session anywhere in this architecture to leak memory
  across; the AC describes a live-backend property (a persistent server
  process) this scaled-down pass does not build.
"""

from __future__ import annotations

import json
import time
from datetime import date, timedelta

import pytest

from pyforge.herald import claims, cli, evidence, notices, progress

RECORD_COUNT = 100
TIME_BUDGET_SECONDS = 1.0


@pytest.fixture(autouse=True)
def _stub_evidence_validation(monkeypatch):
    """Seeding 100 published claims runs every evidence link through
    ``claims.publish``'s validation loop -- stub it so seeding never
    reaches ``deny_network`` (mirrors ``test_cli_success.py``'s own
    autouse stub)."""
    monkeypatch.setattr(evidence, "validate_for_publish", lambda url, **_k: None)


def _seed_progress(progress_path, count):
    base = date(2026, 1, 1)
    for i in range(count):
        progress.upsert(
            progress_path,
            station=progress.STATIONS[i % len(progress.STATIONS)],
            date=(base + timedelta(days=i)).isoformat(),
            shipped_capabilities=[f"capability-{i}"],
            compute_hours=1.0,
            token_spend=1000,
            wall_clock_hours=1.0,
            unblock_narrative="",
        )


def _seed_claims(claims_path, count):
    for i in range(count):
        claim = claims.create(
            claims_path,
            project_name=f"project-{i}",
            evidence=[
                claims.Evidence(
                    type="test_results", url=f"https://ci.example/{i}", label="tests"
                )
            ],
        )
        claims.publish(claims_path, claim.id, thesis=f"Shipped project {i}")


def _seed_notices(repo_root, count):
    for i in range(count):
        notices.author_notice(
            repo_root,
            notice_type="fix",
            component=f"component-{i}",
            what=f"what {i}",
            why=f"why {i}",
            migration=f"migration {i}",
            deadline=None,
            reason_link=None,
            publish=True,
        )


def test_herald_progress_list_under_one_second(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _seed_progress(tmp_path / progress.DEFAULT_PROGRESS_PATH, RECORD_COUNT)

    start = time.perf_counter()
    rc = cli.main(["progress", "--json"])
    elapsed = time.perf_counter() - start

    assert rc == 0
    lines = [line for line in capsys.readouterr().out.splitlines() if line]
    assert len(lines) == RECORD_COUNT
    assert elapsed < TIME_BUDGET_SECONDS, f"herald progress took {elapsed:.3f}s"


def test_herald_success_list_under_one_second(tmp_path, capsys):
    claims_path = tmp_path / claims.DEFAULT_CLAIMS_PATH
    _seed_claims(claims_path, RECORD_COUNT)

    start = time.perf_counter()
    rc = cli.main(["success", "--repo-root", str(tmp_path), "--json", "list"])
    elapsed = time.perf_counter() - start

    assert rc == 0
    lines = [line for line in capsys.readouterr().out.splitlines() if line]
    assert len(lines) == RECORD_COUNT
    assert elapsed < TIME_BUDGET_SECONDS, f"herald success list took {elapsed:.3f}s"


def test_herald_notice_list_under_one_second(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _seed_notices(tmp_path, RECORD_COUNT)

    start = time.perf_counter()
    rc = cli.main(["notice", "--json", "list"])
    elapsed = time.perf_counter() - start

    assert rc == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert len(payload) == RECORD_COUNT
    assert elapsed < TIME_BUDGET_SECONDS, f"herald notice list took {elapsed:.3f}s"


def test_herald_success_list_filtered_by_status_under_one_second(tmp_path, capsys):
    """ "Archive search responsive" -- the same listing path, exercised
    through its own filter (``--status``), not just the unfiltered case."""
    claims_path = tmp_path / claims.DEFAULT_CLAIMS_PATH
    _seed_claims(claims_path, RECORD_COUNT)

    start = time.perf_counter()
    rc = cli.main(
        [
            "success",
            "--repo-root",
            str(tmp_path),
            "--json",
            "list",
            "--status",
            "published",
        ]
    )
    elapsed = time.perf_counter() - start

    assert rc == 0
    lines = [line for line in capsys.readouterr().out.splitlines() if line]
    assert len(lines) == RECORD_COUNT
    assert elapsed < TIME_BUDGET_SECONDS, (
        f"herald success list --status took {elapsed:.3f}s"
    )
