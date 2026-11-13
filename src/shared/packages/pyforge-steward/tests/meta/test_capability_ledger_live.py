"""Story 121.7 (spec-foundry-capability-ledger fcl:CAP-1): the capability ledger holds against the live Specs.

``docs/foundry/capability-ledger.yaml`` is written by ``pyforge steward cutover plan --regenerate`` (Story 121.1) from
the live Specs, its decided fields settled by ``modes.md``'s rules, and judged by ``cutover_ledger_check.check``
(Story 121.6). This module holds the committed ledger to both:

* ``check`` returns no finding on the repository but the one exemption below;
* every row id resolves to a live Spec heading: the id is a live capability, and the row's ``heading`` and ``path``
  are that capability's.

**The one exemption.** ``spec-pyforge-steward CAP-181``'s building Story 123.1 depends on Story 121.7 (its oracle map names
this module), so while 123.1 is not ``done`` the capability's heading reads ``(ready`` and no citing story reads
``done``: ``check`` reports ``rebuild-never-built`` on it. It is not a never-built capability (123.1 builds it on A and
steward Story 122.5 flips its marker to shipped), so its row stays ``rebuild``, and that one finding is excused by id
and code only while the steward ledger key of Story 123.1 is not ``done``. The exemption lapses by itself once it is;
Story 122.5 runs the check with no exemption.

The module reads the ledger, every live Spec, the stations' ``epics.md`` and sprint ledgers, so it is a live-tree test;
the repository root is found inside a function, never at import.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from pyforge.steward.cutover_ledger import DEFAULT_LEDGER, LiveCap, live_caps
from pyforge.steward.cutover_ledger_check import CheckReport, Issue, check

pytestmark = pytest.mark.live_tree

# The one exemption (story spec 121.7, § The one exemption): the id, the finding code and the reason.
EXEMPT_ID = "pyforge-steward:CAP-181"
EXEMPT_CODE = "rebuild-never-built"
EXEMPT_REASON = (
    "Story 123.1 builds pyforge-steward:CAP-181 on A in this PR and depends on Story 121.7, so no citing story reads "
    "done when 121.7 runs; the row stays rebuild, and Story 122.5 runs the check with no exemption"
)
# The exemption applies only while this steward ledger key is not `done`.
EXEMPT_UNTIL_DONE = "123-1-every-steward-capability-names-the-modules-that-realize-it-and-the-tests-that-prove-it"
STEWARD_SPRINT_LEDGER = Path("_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml")
STATION_PACKAGES = Path("src/shared/packages")
DONE = "done"


def _repo_root() -> Path:
    """The checkout this test reads, resolved inside a function and never at import (the live-tree split rule)."""
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "pixi.toml").is_file() and (candidate / STATION_PACKAGES).is_dir():
            return candidate
    raise AssertionError("could not locate the repository root (pixi.toml beside src/shared/packages)")


def exemptions(sprint_ledger: Path) -> frozenset[tuple[str, str]]:
    """The ``(code, id)`` findings excused: the spec-pyforge-steward CAP-181 one while ``EXEMPT_UNTIL_DONE`` does not read ``done``."""
    data = yaml.safe_load(sprint_ledger.read_text(encoding="utf-8")) if sprint_ledger.is_file() else None
    entries = data.get("development_status") if isinstance(data, dict) else None
    if isinstance(entries, dict) and entries.get(EXEMPT_UNTIL_DONE) == DONE:
        return frozenset()
    return frozenset({(EXEMPT_CODE, EXEMPT_ID)})


def unexcused(report: CheckReport, excused: frozenset[tuple[str, str]]) -> list[Issue]:
    return [finding for finding in report.findings if (finding[0], finding[1]) not in excused]


def exempt_mode_problem(rows: list[dict[str, Any]], excused: frozenset[tuple[str, str]]) -> str | None:
    """While the exemption holds, the exempt row must read ``rebuild``, whether or not ``check`` reports it.

    ``check`` judges never-built only on rebuild rows, so a B-only ``EXEMPT_ID`` row draws no finding at all: the mode
    is asserted on its own, not only when the excused finding is present.
    """
    if not excused:
        return None
    mode = {row.get("id"): row.get("mode") for row in rows}.get(EXEMPT_ID)
    if mode == "rebuild":
        return None
    return f"{EXEMPT_ID} is excused only as a rebuild row ({EXEMPT_REASON}); it reads {mode!r}"


@pytest.fixture(scope="module")
def repo_root() -> Path:
    return _repo_root()


@pytest.fixture(scope="module")
def ledger_rows(repo_root: Path) -> list[dict[str, Any]]:
    data = yaml.safe_load((repo_root / DEFAULT_LEDGER).read_text(encoding="utf-8"))
    rows = data.get("capabilities") if isinstance(data, dict) else None
    assert isinstance(rows, list) and rows, f"{DEFAULT_LEDGER}: no capabilities rows"
    return rows


def test_the_ledger_has_no_finding_but_the_exemption(repo_root: Path, ledger_rows: list[dict[str, Any]]) -> None:
    excused = exemptions(repo_root / STEWARD_SPRINT_LEDGER)
    report = check(repo_root, DEFAULT_LEDGER)
    assert unexcused(report, excused) == []
    assert exempt_mode_problem(ledger_rows, excused) is None


@pytest.mark.parametrize(
    ("mode", "excused", "fires"),
    [
        ("rebuild", frozenset({(EXEMPT_CODE, EXEMPT_ID)}), False),
        ("B-only", frozenset({(EXEMPT_CODE, EXEMPT_ID)}), True),
        (None, frozenset({(EXEMPT_CODE, EXEMPT_ID)}), True),
        ("B-only", frozenset(), False),
    ],
)
def test_the_exempt_row_must_read_rebuild_while_excused(
    mode: str | None, excused: frozenset[tuple[str, str]], fires: bool
) -> None:
    rows: list[dict[str, Any]] = [{"id": "pyforge-atlas:CAP-68", "mode": "B-only"}]
    if mode is not None:
        rows.append({"id": EXEMPT_ID, "mode": mode})
    assert (exempt_mode_problem(rows, excused) is not None) is fires


def test_every_row_id_resolves_to_a_live_spec_heading(repo_root: Path, ledger_rows: list[dict[str, Any]]) -> None:
    caps: dict[str, LiveCap] = {cap.id: cap for cap in live_caps(repo_root)}
    problems: list[str] = []
    for row in ledger_rows:
        cap = caps.get(row["id"])
        if cap is None:
            problems.append(f"{row['id']}: no live Spec holds this capability")
        elif (row.get("heading"), row.get("path")) != (cap.heading, cap.path):
            problems.append(
                f"{row['id']}: row reads {row.get('heading')!r} at {row.get('path')}, the Spec {cap.heading!r}"
            )
    assert problems == []


@pytest.mark.parametrize(
    ("status", "excused"),
    [
        ("backlog", frozenset({(EXEMPT_CODE, EXEMPT_ID)})),
        ("in-review", frozenset({(EXEMPT_CODE, EXEMPT_ID)})),
        (DONE, frozenset()),
    ],
)
def test_the_exemption_lapses_when_story_123_1_is_done(
    tmp_path: Path, status: str, excused: frozenset[tuple[str, str]]
) -> None:
    sprint_ledger = tmp_path / "sprint-status-ledger.yaml"
    sprint_ledger.write_text(yaml.safe_dump({"development_status": {EXEMPT_UNTIL_DONE: status}}), encoding="utf-8")
    assert exemptions(sprint_ledger) == excused
    finding: Issue = (EXEMPT_CODE, EXEMPT_ID, "reads (ready")
    other: Issue = (EXEMPT_CODE, "pyforge-steward:CAP-182", "reads (ready")
    report = CheckReport(findings=(finding, other))
    assert unexcused(report, exemptions(sprint_ledger)) == ([other] if excused else [finding, other])
