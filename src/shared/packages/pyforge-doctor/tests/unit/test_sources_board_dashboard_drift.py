"""Unit tests for ``pyforge.doctor.sources.board.gather_dashboard_drift``
(Story 6.5) -- covers the spec's I/O & Edge-Case Matrix rows for
``dashboard_drift`` against real tmp fixtures mirroring
``PROJECT_SOURCES``/tracked-ledger-twin layout, plus the WARN-degrade paths
for a missing/unparseable ``generate.py`` or ``data.js`` (the Boundaries'
explicit ``SystemExit`` -> WARN Finding requirement).

``gather_dashboard_drift`` is called DIRECTLY -- no dispatcher exists yet in
this story (Design Notes), mirroring how ``test_sources_ledger.py`` tests
``ledger.gather`` directly.

The real ``docs/dashboard/generate.py`` is NOT used here: it does a
module-level ``from bmad_drift_check import GUILD_DREAMS, STATIONS`` that
only resolves against the live monorepo's own ``scripts/`` tree, which would
make these fixtures depend on the whole repo rather than on
``gather_dashboard_drift``'s own port logic. A minimal stub -- carrying the
same ``parse_sprint_status``/``dashboard_id_to_status`` bodies plus a
fixture-controlled ``PROJECT_SOURCES`` -- is written into each tmp target
instead; ``_load_dashboard_generate`` loads it via the exact same
``importlib.util.spec_from_file_location`` path the production code uses, so
the DYNAMIC-LOAD mechanism under test is real, only the loaded file's
content is a fixture.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import board

_REPO_ROOT = Path(__file__).resolve().parents[6]
_HAVE_REAL_DASHBOARD = (_REPO_ROOT / "docs" / "dashboard" / "generate.py").is_file()

# --- fixture helpers ---------------------------------------------------------

_STUB_GENERATE = '''
import re

_ENTRY = re.compile(r"^\\s{{2}}(?P<key>[^:#\\s][^:]*?):\\s*(?P<val>[a-z][a-z-]*)\\s*(#.*)?$")


def parse_sprint_status(path):
    out = {{}}
    in_block = False
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not in_block:
            if stripped == "development_status:":
                in_block = True
            continue
        if line and not line[0].isspace() and not stripped.startswith("#"):
            break
        m = _ENTRY.match(line)
        if m:
            out[m.group("key")] = m.group("val")
    return out


def dashboard_id_to_status(story_id, sprint):
    prefix = story_id.lower().replace(".", "-") + "-"
    for key, status in sprint.items():
        if key.startswith(prefix):
            return status
    return None


PROJECT_SOURCES = {project_sources!r}
_KEY_SLUG_OVERRIDE = {key_slug_override!r}
_DERIVE_EXCLUDE = {derive_exclude!r}
'''


def _write_generate_stub(
    target: Path,
    project_sources: dict[str, str],
    *,
    key_slug_override: dict[str, str] | None = None,
    derive_exclude: set[str] | None = None,
) -> None:
    path = target / "docs" / "dashboard" / "generate.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        _STUB_GENERATE.format(
            project_sources=project_sources,
            key_slug_override=key_slug_override or {},
            derive_exclude=derive_exclude or set(),
        ),
        encoding="utf-8",
    )


def _write_sprint_file(path: Path, rows: dict[str, str]) -> None:
    """Shared shape for both a Tier-3 feed and a tracked twin ledger."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["development_status:"]
    lines.extend(f"  {k}: {v}" for k, v in rows.items())
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_data_js(path: Path, projects: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({"projects": projects})
    path.write_text(f"window.DASHBOARD_DATA = {payload};\n", encoding="utf-8")


_FEED_REL = "_bmad-output/projects/pyforge-testproj/implementation-artifacts/sprint-status.yaml"
_TWIN_REL = "_bmad-output/projects/pyforge-testproj/planning-artifacts/sprint-status-ledger.yaml"
_EPICS_REL = "_bmad-output/projects/pyforge-testproj/planning-artifacts/epics.md"


def _seed(target: Path, *, project_sources: dict[str, str] | None = None) -> None:
    _write_generate_stub(
        target, project_sources if project_sources is not None else {"testproj": _FEED_REL}
    )


# --- Board status stale -------------------------------------------------


def test_stale_done_reports_fail_and_never_self_heals(tmp_path: Path) -> None:
    _seed(tmp_path)
    _write_sprint_file(tmp_path / _FEED_REL, {"1-1-foo": "done"})
    _write_sprint_file(tmp_path / _TWIN_REL, {"1-1-foo": "done"})  # twin matches feed
    _write_data_js(tmp_path / "docs" / "dashboard" / "data.js", {
        "testproj": {"epics": [{"stories": [["1.1", "pending", "t"]]}]},
    })

    findings = board.gather_dashboard_drift(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.DASHBOARD_DRIFT
    assert finding.check == "stale-done"
    assert finding.status is DoctorStatus.FAIL
    assert "will NOT self-heal" in finding.message
    assert finding.evidence["project"] == "testproj"


# --- Twin ahead of feed --------------------------------------------------


def test_twin_ahead_of_feed_forbids_sprint_ledger_sync(tmp_path: Path) -> None:
    _seed(tmp_path)
    _write_sprint_file(tmp_path / _FEED_REL, {"1-1-foo": "backlog"})  # feed regressed
    _write_sprint_file(tmp_path / _TWIN_REL, {"1-1-foo": "done"})     # twin still done
    _write_data_js(tmp_path / "docs" / "dashboard" / "data.js", {
        "testproj": {"epics": [{"stories": [["1.1", "pending", "t"]]}]},
    })

    findings = board.gather_dashboard_drift(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "twin-ahead"
    assert finding.status is DoctorStatus.FAIL
    assert "Do NOT run sprint-ledger-sync" in finding.message
    assert "sprint-ledger-sync --repair-feed" in finding.message


# --- Twin stale (drifted, but nothing un-finishing) ----------------------


def test_twin_stale_without_regression_reports_fail(tmp_path: Path) -> None:
    _seed(tmp_path)
    _write_sprint_file(tmp_path / _FEED_REL, {"1-1-foo": "in-progress"})
    _write_sprint_file(tmp_path / _TWIN_REL, {"1-1-foo": "gated"})  # differs, neither is 'done'
    _write_data_js(tmp_path / "docs" / "dashboard" / "data.js", {
        "testproj": {"epics": [{"stories": [["1.1", "pending", "t"]]}]},
    })

    findings = board.gather_dashboard_drift(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "twin-stale"
    assert finding.status is DoctorStatus.FAIL
    assert "sprint-ledger-sync --project testproj" in finding.message
    assert "Do NOT" not in finding.message


# --- Twin missing ----------------------------------------------------------


def test_twin_missing_reports_fail(tmp_path: Path) -> None:
    _seed(tmp_path)
    _write_sprint_file(tmp_path / _FEED_REL, {"1-1-foo": "done"})
    # deliberately no tracked twin ledger at all
    _write_data_js(tmp_path / "docs" / "dashboard" / "data.js", {
        "testproj": {"epics": [{"stories": [["1.1", "done", "t"]]}]},
    })

    findings = board.gather_dashboard_drift(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "twin-missing"
    assert finding.status is DoctorStatus.FAIL
    assert "sprint-ledger-sync" in finding.message


# --- Missing story on the board --------------------------------------------


def test_missing_story_reports_fail(tmp_path: Path) -> None:
    target = tmp_path
    _seed(target, project_sources={})  # no Tier-3 feed wired -- isolate this check
    epics_md = target / _EPICS_REL
    epics_md.parent.mkdir(parents=True, exist_ok=True)
    epics_md.write_text("## Epic 1: T\n\n### Story 1.1: title\n", encoding="utf-8")
    _write_data_js(target / "docs" / "dashboard" / "data.js", {"testproj": {"epics": []}})

    findings = board.gather_dashboard_drift(target)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "missing-story"
    assert finding.status is DoctorStatus.FAIL
    assert "1.1" in finding.message


# --- No drift ---------------------------------------------------------------


def test_no_drift_reports_one_ok_finding(tmp_path: Path) -> None:
    _seed(tmp_path)
    _write_sprint_file(tmp_path / _FEED_REL, {"1-1-foo": "done"})
    _write_sprint_file(tmp_path / _TWIN_REL, {"1-1-foo": "done"})
    _write_data_js(tmp_path / "docs" / "dashboard" / "data.js", {
        "testproj": {"epics": [{"stories": [["1.1", "done", "t"]]}]},
    })
    # no epics.md -- missing-story check is a no-op without one

    findings = board.gather_dashboard_drift(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.DASHBOARD_DRIFT
    assert finding.check == "dashboard-drift"
    assert finding.status is DoctorStatus.OK
    assert finding.evidence == {"projects": 1}


# --- Cannot-evaluate degrades to WARN, never raises -------------------------


def test_missing_generate_py_degrades_to_warn(tmp_path: Path) -> None:
    # deliberately no docs/dashboard/generate.py at all
    findings = board.gather_dashboard_drift(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.DASHBOARD_DRIFT
    assert finding.status is DoctorStatus.WARN
    assert "dashboard-drift" in finding.check or finding.check == "dashboard-drift"


def test_missing_data_js_degrades_to_warn(tmp_path: Path) -> None:
    _seed(tmp_path)
    # deliberately no docs/dashboard/data.js

    findings = board.gather_dashboard_drift(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.WARN


def test_unparseable_data_js_degrades_to_warn_not_systemexit(tmp_path: Path) -> None:
    """The Boundaries' explicit requirement: the original script's own
    ``_load_data_js`` raises ``SystemExit`` on an unparseable ``data.js`` --
    this port must never let that (or any other) exception escape
    ``gather_dashboard_drift``; it becomes a WARN Finding instead."""
    _seed(tmp_path)
    data_js = tmp_path / "docs" / "dashboard" / "data.js"
    data_js.parent.mkdir(parents=True, exist_ok=True)
    data_js.write_text("this is not the expected window.DASHBOARD_DATA shape\n",
                        encoding="utf-8")

    findings = board.gather_dashboard_drift(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.DASHBOARD_DRIFT
    assert finding.status is DoctorStatus.WARN


def test_malformed_project_entry_does_not_hide_another_projects_real_finding(
    tmp_path: Path,
) -> None:
    """Adversarial-review regression: a station whose ``data.js`` entry holds
    a malformed story (an empty list -- ``s[0]`` used to raise ``IndexError``
    mid-scan) must not swallow a DIFFERENT station's real drift finding."""
    _write_generate_stub(tmp_path, {"good": _FEED_REL})
    _write_sprint_file(tmp_path / _FEED_REL, {"1-1-foo": "done"})
    _write_data_js(tmp_path / "docs" / "dashboard" / "data.js", {
        "good": {"epics": [{"stories": [["1.1", "pending", "t"]]}]},  # real stale-done
        "bad": {"epics": [{"stories": [[]]}]},  # malformed: empty story tuple
    })

    findings = board.gather_dashboard_drift(tmp_path)

    kinds = {f.check for f in findings}
    assert "stale-done" in kinds
    good_finding = next(f for f in findings if f.check == "stale-done")
    assert good_finding.evidence["project"] == "good"
    assert good_finding.status is DoctorStatus.FAIL


def test_non_dict_project_entry_is_skipped_without_crashing(tmp_path: Path) -> None:
    _write_generate_stub(tmp_path, {"good": _FEED_REL})
    _write_sprint_file(tmp_path / _FEED_REL, {"1-1-foo": "done"})
    _write_data_js(tmp_path / "docs" / "dashboard" / "data.js", {
        "bad": None,
        "good": {"epics": [{"stories": [["1.1", "pending", "t"]]}]},
    })

    findings = board.gather_dashboard_drift(tmp_path)

    kinds = {f.check for f in findings}
    assert "stale-done" in kinds
    stale = next(f for f in findings if f.check == "stale-done")
    assert stale.evidence["project"] == "good"
    assert not any(f.evidence.get("project") == "bad" for f in findings)


def test_unreadable_tier3_feed_degrades_to_warn(tmp_path: Path) -> None:
    """A host-state read (the Tier-3 feed) that raises mid-gather -- e.g. a
    non-UTF-8 byte -- must degrade via ``sources.degrade_on_exception``
    rather than escape."""
    _seed(tmp_path)
    feed = tmp_path / _FEED_REL
    feed.parent.mkdir(parents=True, exist_ok=True)
    feed.write_bytes(b"development_status:\n  1-1-f\xe9o: done\n")
    _write_sprint_file(tmp_path / _TWIN_REL, {"1-1-foo": "done"})
    _write_data_js(tmp_path / "docs" / "dashboard" / "data.js", {
        "testproj": {"epics": [{"stories": [["1.1", "done", "t"]]}]},
    })

    findings = board.gather_dashboard_drift(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.WARN


# --- real generate.py fidelity (skips if unavailable) ------------------------


@pytest.mark.skipif(not _HAVE_REAL_DASHBOARD,
                     reason="real docs/dashboard/generate.py not present in this checkout")
def test_real_generate_py_loads_and_exposes_the_expected_attribute_surface() -> None:
    """The stub fixtures above intentionally do NOT exercise the real
    ``generate.py`` (its own module-level ``bmad_drift_check`` import ties it
    to the whole repo -- see this file's own header). This test instead pins
    that the attributes ``_load_dashboard_generate``/``_check_dashboard_drift``
    actually read (``PROJECT_SOURCES``, ``_KEY_SLUG_OVERRIDE``, ``_DERIVE_
    EXCLUDE``, ``parse_sprint_status``, ``dashboard_id_to_status``) still
    exist with the expected shape on the REAL file, via the exact same
    dynamic-load path production code uses -- so a rename/removal in the real
    module would fail this test even though the stub-based tests above
    wouldn't notice."""
    gen = board._load_dashboard_generate(_REPO_ROOT)

    assert isinstance(gen.PROJECT_SOURCES, dict) and gen.PROJECT_SOURCES
    assert isinstance(gen._KEY_SLUG_OVERRIDE, dict)
    assert isinstance(gen._DERIVE_EXCLUDE, set)
    assert callable(gen.parse_sprint_status)
    assert callable(gen.dashboard_id_to_status)
    # dashboard_id_to_status("1.1", {"1-1-x": "done"}) -> "done": the exact
    # feed-key -> board-id contract gather_dashboard_drift depends on.
    assert gen.dashboard_id_to_status("1.1", {"1-1-x": "done"}) == "done"
