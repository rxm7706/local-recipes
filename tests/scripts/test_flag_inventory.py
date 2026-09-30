"""Unit tests for ``scripts/flag_inventory.py`` -- the per-station flag inventory (doctor Story 34.4,
spec-feature-flag-governance CAP-7).

One test per acceptance-criteria row and per I/O-matrix row of the story spec. Every judgement runs against a
fixture repo written under ``tmp_path`` (its own roster, baseline, tree, station packages, Specs and ``epics.md``),
so no test depends on which stories the live tree carries; the live-tree tests pin only what holds whatever the
tree carries (eight reports, and the header counts agreeing with the gate).

The suite runs from ``pyforge-guild`` (``pixi run -e pyforge-guild python -m pytest
tests/scripts/test_flag_inventory.py -q``) and from ``pyforge-ci`` (the ``scripts-suite`` lane): Doctor's join is
stdlib-only and loads from this checkout's source tree when ``pyforge.doctor`` is not installed.
"""

from __future__ import annotations

import ast
import json
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

pytest.importorskip("yaml")

REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import detectors  # noqa: E402
import flag_gate_check  # noqa: E402
import flag_inventory  # noqa: E402
import flag_rule  # noqa: E402

INVENTORY = _SCRIPTS_DIR / "flag_inventory.py"
SLUG = "spec-alpha"
KEY = "pyforge.atlas.alpha_feature"
git = shutil.which("git")

FLAG_BLOCK = """\
flag:
  key: {key}
  provider: openfeature-file
  default: {{production: off, staging: on, dev: on}}
  scope: global
  fallback: "the legacy behaviour"
  cleanup: 90 days after ON in every environment (Q4)
"""


def _write(root: Path, rel: str, text: str = "") -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _fixture(
    tmp_path: Path,
    *,
    stations=("atlas",),
    ended=("archived", "absorbed", "superseded"),
    tree_keys=(),
    baseline=(),
) -> Path:
    """A repo root with its own roster, baseline and tree; no Specs, no story specs, no station code."""
    _write(
        tmp_path,
        "docs/governance/guild-roster.json",
        json.dumps({"stations": list(stations), "spec_statuses_ended_acts": list(ended), "flag_exemptions": ["docs-only"]}),
    )
    _write(
        tmp_path,
        "docs/governance/flag-rule-baseline.json",
        json.dumps({"rule_date": "2026-09-28", "specs": sorted(baseline)}),
    )
    flags = {k: {"state": "ENABLED", "variants": {"on": True, "off": False}, "defaultVariant": "on"} for k in tree_keys}
    _write(tmp_path, "src/platform/config/flags.json", json.dumps({"flags": flags}))
    return tmp_path


def _spec(root: Path, caps=(1,), *, station="atlas", slug=SLUG, status="ready") -> None:
    """One Spec folder under the station's project, declaring ``caps``."""
    bullets = "".join(f"- **CAP-{n} - a capability.**\n  - intent: it does a thing.\n" for n in caps)
    _write(
        root,
        f"_bmad-output/projects/pyforge-{station}/planning-artifacts/specs/{slug}/SPEC.md",
        f"---\nspec: {slug}\nstatus: {status}   # a comment\n---\n\n# SPEC\n\n## Capabilities\n\n{bullets}\n## Constraints\n\nnone\n",
    )


def _epics(root: Path, *stories: tuple[str, str | None], station="atlas", slug=SLUG) -> None:
    """An ``epics.md`` with one story per ``(cited CAPs, Surface: line or None)``."""
    blocks = []
    for number, (caps, surface) in enumerate(stories, start=1):
        surface_line = f"**Surface:** {surface}\n" if surface is not None else ""
        blocks.append(f"### Story 1.{number}: story {number}\n\nLiving CAP citations: `{slug}` {caps}.\n{surface_line}\n")
    _write(
        root,
        f"_bmad-output/projects/pyforge-{station}/planning-artifacts/epics.md",
        "# Epics\n\n## Epic 1\n\n" + "".join(blocks),
    )


def _code(root: Path, rel: str, text: str = "", *, station="atlas") -> None:
    _write(root, f"src/shared/packages/pyforge-{station}/src/pyforge/{station}/{rel}", text)


def _story_spec(
    root: Path, name: str, frontmatter: str = "", *, station="atlas", type_="feature", status="backlog", body="body"
) -> str:
    rel = f"_bmad-output/projects/pyforge-{station}/planning-artifacts/specs/{name}"
    _write(root, rel, f"---\ntitle: a story\ntype: {type_}\nstatus: {status}\n{frontmatter}---\n\n{body}\n")
    return rel


def _run(root: Path, out: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, str, str]:
    rc = flag_inventory.main(["--root", str(root), "--out-dir", str(out)])
    captured = capsys.readouterr()
    return rc, captured.out, captured.err


def _report(root: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str], station="atlas") -> str:
    out = tmp_path / "out"
    rc, _out, err = _run(root, out, capsys)
    assert rc == 0, err
    return (out / f"pyforge-{station}.md").read_text(encoding="utf-8")


def _row(report: str, cap: int) -> str:
    rows = [ln for ln in report.splitlines() if ln.startswith(f"| CAP-{cap} |")]
    assert len(rows) == 1, f"expected one row for CAP-{cap}, found {rows}"
    return rows[0]


def _header(report: str, label: str) -> int:
    match = re.search(rf"^- {re.escape(label)}: (\d+)$", report, re.MULTILINE)
    assert match, f"no `{label}` header line"
    return int(match.group(1))


def _warned_paths(report: str) -> set[str]:
    section = report.split("## Warned specs", 1)[1]
    return {
        cells[3]
        for line in section.splitlines()
        if line.startswith("| ") and (cells := [c.strip() for c in line.split("|")]) and cells[3].endswith(".md")
    }


# --- CLI CAP, no flag -----------------------------------------------------------------------


def test_a_cli_cap_whose_story_names_a_verb_module_and_no_flag_is_listed_with_its_verb_and_none(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    root = _fixture(tmp_path)
    _spec(root)
    _epics(root, ("CAP-1", "`cli.py`"))
    _code(root, "cli.py", 'sub.add_parser("frobnicate")\nsub.add_parser("defrobnicate")\n')

    report = _report(root, tmp_path, capsys)

    row = _row(report, 1)
    assert "| runtime |" in row
    assert "CLI `cli.py` (defrobnicate, frobnicate)" in row
    assert row.endswith("| none |")
    assert _header(report, "Runtime CAPs with no flag") == 1


# --- flagged CAP ----------------------------------------------------------------------------


def test_the_same_cap_with_its_key_in_the_tree_lists_the_key(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    root = _fixture(tmp_path, tree_keys=[KEY])
    _spec(root)
    _epics(root, ("CAP-1", "`cli.py`"))
    _code(root, "cli.py", 'sub.add_parser("frobnicate")\n')
    _story_spec(root, "spec-1-1-alpha.md", FLAG_BLOCK.format(key=KEY), body=f"Living CAP: `{SLUG}` CAP-1.")

    report = _report(root, tmp_path, capsys)

    row = _row(report, 1)
    assert "| runtime |" in row
    assert f"`{KEY}`" in row
    assert "none" not in row
    assert _header(report, "Runtime CAPs with no flag") == 0


def test_a_key_the_tree_lacks_reads_none_naming_the_key_and_still_counts_as_unflagged(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    root = _fixture(tmp_path, tree_keys=[])
    _spec(root)
    _epics(root, ("CAP-1", "`cli.py`"))
    _code(root, "cli.py", 'sub.add_parser("frobnicate")\n')
    _story_spec(root, "spec-1-1-alpha.md", FLAG_BLOCK.format(key=KEY), body=f"Living CAP: `{SLUG}` CAP-1.")

    report = _report(root, tmp_path, capsys)

    assert f"| none (key {KEY} not in tree) |" in _row(report, 1)
    assert _header(report, "Runtime CAPs with no flag") == 1


def test_a_flag_block_that_cites_another_cap_or_another_station_gates_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    root = _fixture(tmp_path, stations=("atlas", "warden"), tree_keys=[KEY])
    _spec(root, caps=(1, 2))
    _epics(root, ("CAP-1", "`cli.py`"), ("CAP-2", "`cli.py`"))
    _code(root, "cli.py", 'sub.add_parser("frobnicate")\n')
    _story_spec(root, "spec-1-1-alpha.md", FLAG_BLOCK.format(key=KEY), body=f"Living CAP: `{SLUG}` CAP-2.")
    _story_spec(root, "spec-1-2-elsewhere.md", FLAG_BLOCK.format(key=KEY), station="warden", body=f"`{SLUG}` CAP-1.")

    report = _report(root, tmp_path, capsys)

    assert _row(report, 1).endswith("| none |")
    assert f"`{KEY}`" in _row(report, 2)


# --- planning-only CAP ----------------------------------------------------------------------


def test_a_cap_whose_surface_is_only_a_planning_document_is_listed_not_reachable_and_never_unflagged(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    root = _fixture(tmp_path)
    _spec(root)
    _epics(root, ("CAP-1", "`docs/how-to/some-guide.md`, `_bmad-output/x/plan.yaml`"))

    report = _report(root, tmp_path, capsys)

    row = _row(report, 1)
    assert "| planning |" in row
    assert "| n/a |" in row
    assert _header(report, "Runtime CAPs with no flag") == 0


def test_a_document_reference_with_a_line_suffix_is_still_a_document(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    root = _fixture(tmp_path)
    _spec(root)
    _epics(root, ("CAP-1", "`specs/spec-beta/SPEC.md:5`"))
    _write(root, "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-beta/SPEC.md", "x\n")

    row = _row(_report(root, tmp_path, capsys), 1)

    assert "| planning |" in row


# --- unresolvable CAP -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("stories", "why"),
    [
        (
            [("CAP-2", "`cli.py`")],
            "no story in epics.md cites this CAP",
        ),
        (
            [("CAP-1", None)],
            "no `Surface:` line",
        ),
        (
            [("CAP-1", "`does_not_exist.py`")],
            "no `Surface:` code path exists: `does_not_exist.py`",
        ),
    ],
    ids=["no-citing-story", "no-surface-line", "no-fragment-resolves"],
)
def test_an_unresolvable_cap_is_its_own_unresolved_row_never_unflagged_and_never_dropped(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], stories, why
):
    root = _fixture(tmp_path)
    _spec(root)
    _epics(root, *stories)
    _code(root, "cli.py", 'sub.add_parser("frobnicate")\n')

    report = _report(root, tmp_path, capsys)

    row = _row(report, 1)
    assert "| unresolved |" in row
    assert why in row
    assert _header(report, "Runtime CAPs with no flag") == 0


def test_a_project_with_no_epics_file_lists_every_cap_unresolved(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    root = _fixture(tmp_path)
    _spec(root, caps=(1, 2))

    report = _report(root, tmp_path, capsys)

    assert "| unresolved |" in _row(report, 1)
    assert "| unresolved |" in _row(report, 2)


# --- module: code that is no named entry point ----------------------------------------------


def test_a_cap_that_resolves_to_code_with_no_entry_point_is_module_and_not_counted_as_unflagged(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    root = _fixture(tmp_path)
    _spec(root)
    _epics(root, ("CAP-1", "`store.py`, `scripts/helper.py`"))
    _code(root, "store.py", "X = 1\n")
    _write(root, "scripts/helper.py", "Y = 2\n")

    report = _report(root, tmp_path, capsys)

    row = _row(report, 1)
    assert "| module |" in row
    assert "`scripts/helper.py`" in row
    assert _header(report, "Runtime CAPs with no flag") == 0


# --- how a runtime CAP is reached -----------------------------------------------------------


@pytest.mark.parametrize(
    ("surface", "files", "expected"),
    [
        ("`__main__.py`", {"__main__.py": 'p.add_subparsers().add_parser("run")\n'}, "CLI `__main__.py` (run)"),
        (
            "`cli/`",
            {"cli/a.py": 'p.add_parser("one")\n', "cli/b.py": 'p.add_parser("two")\n'},
            "CLI `cli/` (one, two)",
        ),
        ("`cli/quiet.py`", {"cli/quiet.py": "X = 1\n"}, "CLI `cli/quiet.py`"),
        (
            "`mcp/tools.py`",
            {"mcp/tools.py": 'TOOL_SPECS = {"run_a": {}, "run_b": {}}\n'},
            "MCP `mcp/tools.py` (run_a, run_b)",
        ),
        (
            "`mcp/server.py`",
            {"mcp/server.py": "def build(mcp):\n    @mcp.tool()\n    def ping():\n        pass\n"},
            "MCP `mcp/server.py` (ping)",
        ),
        (
            "`dashboard/urls.py`",
            {"dashboard/urls.py": 'urlpatterns = [path("items/", v), path("", w), re_path("^ws/$", c)]\n'},
            "REST `dashboard/urls.py` ((root), ^ws/$, items/)",
        ),
        ("`station_api.py`", {"station_api.py": "X = 1\n"}, "REST `station_api.py`"),
        ("`dashboard/views.py`", {"dashboard/views.py": "X = 1\n"}, "portal `dashboard/views.py`"),
    ],
    ids=["main", "cli-dir", "cli-no-verbs", "mcp-specs", "mcp-decorator", "rest-routes", "station-api", "portal"],
)
def test_a_cap_whose_surface_is_an_entry_point_is_runtime_and_names_what_reaches_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], surface, files, expected
):
    root = _fixture(tmp_path)
    _spec(root)
    _epics(root, ("CAP-1", surface))
    for rel, text in files.items():
        _code(root, rel, text)

    row = _row(_report(root, tmp_path, capsys), 1)

    assert "| runtime |" in row
    assert expected in row


def test_a_top_level_routing_module_and_an_ordinary_module_named_api_are_not_entry_points(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    root = _fixture(tmp_path)
    _spec(root)
    _epics(root, ("CAP-1", "`routing.py`, `api_client.py`"))
    _code(root, "routing.py", 'path("looks/like/a/route")\n')
    _code(root, "api_client.py", "X = 1\n")

    assert "| module |" in _row(_report(root, tmp_path, capsys), 1)


def test_names_past_six_collapse_to_a_count(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    root = _fixture(tmp_path)
    _spec(root)
    _epics(root, ("CAP-1", "`cli.py`"))
    _code(root, "cli.py", "".join(f'sub.add_parser("verb{n}")\n' for n in range(1, 9)))

    row = _row(_report(root, tmp_path, capsys), 1)

    assert "(verb1, verb2, verb3, verb4, verb5, verb6, (+2 more))" in row


def test_a_module_that_cannot_be_parsed_is_named_by_its_path(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    root = _fixture(tmp_path)
    _spec(root)
    _epics(root, ("CAP-1", "`cli.py`"))
    _code(root, "cli.py", "def broken(:\n")

    row = _row(_report(root, tmp_path, capsys), 1)

    assert "| runtime |" in row
    assert "CLI `cli.py` |" in row


def test_a_cell_never_carries_a_bare_pipe(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    root = _fixture(tmp_path)
    _spec(root)
    _epics(root, ("CAP-1", "`dashboard/urls.py`"))
    _code(root, "dashboard/urls.py", 'path("a|b/", v)\n')

    row = _row(_report(root, tmp_path, capsys), 1)

    assert "a\\|b/" in row
    assert len(re.split(r"(?<!\\)\|", row)) == 6


# --- which Specs are read -------------------------------------------------------------------


def test_only_open_specs_are_inventoried_and_the_ended_statuses_are_read_from_the_roster(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    root = _fixture(tmp_path, ended=("archived", "shipped"))
    _spec(root, slug="spec-alpha", status="ready")
    _spec(root, slug="spec-old", status="shipped")
    _spec(root, slug="spec-gone", status="archived")
    _spec(root, slug="spec-absorbed", status="absorbed")  # not ended under this roster

    report = _report(root, tmp_path, capsys)

    assert "### spec-alpha (ready)" in report
    assert "### spec-absorbed (absorbed)" in report
    assert "spec-old" not in report
    assert "spec-gone" not in report


def test_an_open_spec_that_declares_no_cap_is_named_not_dropped(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    root = _fixture(tmp_path)
    _spec(root, caps=(1,))
    _write(
        root,
        "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-plain/SPEC.md",
        "---\nstatus: draft\n---\n\n# no capabilities heading\n",
    )

    report = _report(root, tmp_path, capsys)

    assert "Open Specs declaring no CAP: `spec-plain`." in report


def test_every_roster_station_gets_a_report_even_with_no_project_folder(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    root = _fixture(tmp_path, stations=("atlas", "warden", "mason"))
    _spec(root)
    out = tmp_path / "out"

    rc, stdout, _ = _run(root, out, capsys)

    assert rc == 0
    assert "wrote 3 report(s)" in stdout
    assert sorted(p.name for p in out.iterdir()) == ["pyforge-atlas.md", "pyforge-mason.md", "pyforge-warden.md"]
    assert "_No open Spec._" in (out / "pyforge-mason.md").read_text(encoding="utf-8")


# --- the warned list ------------------------------------------------------------------------


def test_a_pre_rule_feature_spec_with_neither_block_nor_exemption_is_in_its_stations_warned_list(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    rel = "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-3-2-old-feature.md"
    root = _fixture(tmp_path, stations=("atlas", "warden"), baseline=[rel])
    _story_spec(root, "spec-3-2-old-feature.md", status="in-review")
    out = tmp_path / "out"

    rc, _stdout, _err = _run(root, out, capsys)
    atlas = (out / "pyforge-atlas.md").read_text(encoding="utf-8")
    warden = (out / "pyforge-warden.md").read_text(encoding="utf-8")

    assert rc == 0
    assert _header(atlas, "Warned specs") == 1
    assert f"| 3-2-old-feature | in-review | {rel} |" in atlas
    assert _header(warden, "Warned specs") == 0
    assert "_None._" in warden


def test_only_the_specs_the_gate_warns_on_are_warned(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    names = {
        "warned": "spec-1-1-warned.md",
        "fix": "spec-1-2-fix.md",
        "exempt": "spec-1-3-exempt.md",
        "flagged": "spec-1-4-flagged.md",
        "post": "spec-1-5-post-rule.md",
    }
    prefix = "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/"
    root = _fixture(tmp_path, baseline=[prefix + n for n in list(names.values())[:4]])
    _story_spec(root, names["warned"])
    _story_spec(root, names["fix"], type_="fix")
    _story_spec(root, names["exempt"], "flag-exempt: docs-only\n")
    _story_spec(root, names["flagged"], FLAG_BLOCK.format(key=KEY))
    _story_spec(root, names["post"])  # post-rule: a gate FAIL, not a warning

    report = _report(root, tmp_path, capsys)

    assert _warned_paths(report) == {prefix + names["warned"]}


def test_the_warned_list_of_a_station_holds_the_same_paths_as_the_gates_warn_list_for_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    prefix = "_bmad-output/projects/pyforge-{}/planning-artifacts/specs/"
    pre = [(s, f"spec-{n}-1-story-{n}.md") for s in ("atlas", "warden") for n in range(1, 5)]
    root = _fixture(tmp_path, stations=("atlas", "warden"), baseline=[prefix.format(s) + n for s, n in pre])
    for station, name in pre:
        _story_spec(root, name, station=station)
    _story_spec(root, "spec-9-1-new.md")  # post-rule -> FAIL, never a warning
    out = tmp_path / "out"

    _run(root, out, capsys)
    rc = flag_gate_check.main(["--root", str(root), "--json"])
    gate = json.loads(capsys.readouterr().out)

    assert rc == 1  # the fixture has one red spec; the inventory must not care
    for station in ("atlas", "warden"):
        expected = {f["path"] for f in gate["findings"] if f["kind"] == "flag-pre-rule" and f["station"] == f"pyforge-{station}"}
        report = (out / f"pyforge-{station}.md").read_text(encoding="utf-8")
        assert len(expected) == 4
        assert _warned_paths(report) == expected
        assert _header(report, "Warned specs") == len(expected)


def test_the_warned_list_is_sorted_and_carries_each_specs_own_status(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    prefix = "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/"
    root = _fixture(tmp_path, baseline=[prefix + "spec-2-1-b.md", prefix + "spec-1-1-a.md"])
    _story_spec(root, "spec-2-1-b.md", status="done")
    _story_spec(root, "spec-1-1-a.md", status="backlog")

    report = _report(root, tmp_path, capsys)

    rows = [ln for ln in report.splitlines() if ln.startswith(("| 1-1-a", "| 2-1-b"))]
    assert [r.split("|")[1].strip() for r in rows] == ["1-1-a", "2-1-b"]
    assert [r.split("|")[2].strip() for r in rows] == ["backlog", "done"]


# --- the header -----------------------------------------------------------------------------


def test_the_header_names_the_sha_it_read_or_unknown_outside_a_checkout(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    root = _fixture(tmp_path)
    _spec(root)

    report = _report(root, tmp_path, capsys)

    assert "- Read at SHA: `unknown`" in report


@pytest.mark.skipif(git is None, reason="git is not installed")
def test_in_a_git_checkout_the_header_names_head(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    root = _fixture(tmp_path)
    _spec(root)
    env = ["-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "commit.gpgsign=false"]
    for args in (["init", "-q"], ["add", "-A"], [*env, "commit", "-q", "-m", "fixture"]):
        subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)
    head = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()

    report = _report(root, tmp_path, capsys)

    assert f"- Read at SHA: `{head}`" in report


# --- rerun ----------------------------------------------------------------------------------


def test_a_second_run_on_the_same_tree_is_byte_identical(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    prefix = "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/"
    root = _fixture(tmp_path, tree_keys=[KEY], baseline=[prefix + "spec-1-1-old.md"])
    _spec(root, caps=(1, 2, 3))
    _epics(root, ("CAP-1", "`cli.py`"), ("CAP-2", "`docs/x.md`"), ("CAP-3", None))
    _code(root, "cli.py", 'sub.add_parser("frobnicate")\n')
    _story_spec(root, "spec-1-1-old.md")
    first, second = tmp_path / "first", tmp_path / "second"

    assert _run(root, first, capsys)[0] == 0
    assert _run(root, second, capsys)[0] == 0

    names = sorted(p.name for p in first.iterdir())
    assert names == sorted(p.name for p in second.iterdir()) == ["pyforge-atlas.md"]
    for name in names:
        assert (first / name).read_bytes() == (second / name).read_bytes()


def test_a_rerun_over_existing_reports_replaces_them_in_place(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    root = _fixture(tmp_path)
    _spec(root)
    out = tmp_path / "out"
    out.mkdir()
    (out / "pyforge-atlas.md").write_text("stale\n", encoding="utf-8")

    assert _run(root, out, capsys)[0] == 0

    assert (out / "pyforge-atlas.md").read_text(encoding="utf-8").startswith("# Flag inventory: pyforge-atlas\n")


# --- unreadable input: exit 2, the input named, nothing written ------------------------------


def _break(root: Path, which: str, how: str) -> None:
    path = {
        "roster": root / "docs/governance/guild-roster.json",
        "baseline": root / "docs/governance/flag-rule-baseline.json",
        "tree": root / "src/platform/config/flags.json",
    }[which]
    if how == "missing":
        path.unlink()
    elif how == "not-json":
        path.write_text("{ not json", encoding="utf-8")
    elif how == "wrong-shape":
        path.write_text(json.dumps({"unrelated": True}), encoding="utf-8")
    else:  # pragma: no cover
        raise AssertionError(how)


@pytest.mark.parametrize("which", ["roster", "baseline", "tree"])
@pytest.mark.parametrize("how", ["missing", "not-json", "wrong-shape"])
def test_an_unreadable_roster_baseline_or_tree_exits_2_names_the_input_and_writes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], which: str, how: str
):
    root = _fixture(tmp_path)
    _spec(root)
    _break(root, which, how)
    name = {"roster": "guild-roster.json", "baseline": "flag-rule-baseline.json", "tree": "flags.json"}[which]
    out = tmp_path / "out"

    rc, stdout, err = _run(root, out, capsys)

    assert rc == 2
    assert name in err
    assert "unknown" in err
    assert "wrote" not in stdout
    assert not out.exists()


def test_a_roster_without_stations_or_ended_statuses_exits_2_naming_the_roster(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    root = _fixture(tmp_path)
    roster = root / "docs/governance/guild-roster.json"
    for missing in ("stations", "spec_statuses_ended_acts"):
        data = json.loads(roster.read_text(encoding="utf-8"))
        del data[missing]
        roster.write_text(json.dumps(data), encoding="utf-8")
        out = tmp_path / f"out-{missing}"

        rc, _stdout, err = _run(root, out, capsys)

        assert rc == 2
        assert "guild-roster.json" in err
        assert missing in err
        assert not out.exists()
        _fixture(tmp_path)


def test_an_unreadable_epics_file_exits_2_names_it_and_writes_no_partial_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    root = _fixture(tmp_path, stations=("atlas", "warden"))
    _spec(root)
    _spec(root, station="warden", slug="spec-omega")
    _epics(root, ("CAP-1", "`cli.py`"), station="warden", slug="spec-omega")
    epics = _write(root, "_bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md")
    epics.write_bytes(b"\xff\xfe not utf-8 \x80")
    out = tmp_path / "out"

    rc, stdout, err = _run(root, out, capsys)

    assert rc == 2
    assert "_bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md" in err
    assert "wrote" not in stdout
    assert not out.exists()  # warden's report was buildable and still was not written


def test_an_epics_path_that_is_a_directory_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    root = _fixture(tmp_path)
    _spec(root)
    (root / "_bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md").mkdir(parents=True)

    rc, _stdout, err = _run(root, tmp_path / "out", capsys)

    assert rc == 2
    assert "epics.md" in err


def test_an_unreadable_open_spec_exits_2_naming_it(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    root = _fixture(tmp_path)
    spec = _write(root, "_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-bad/SPEC.md")
    spec.write_bytes(b"\xff\xfe\x80")

    rc, _stdout, err = _run(root, tmp_path / "out", capsys)

    assert rc == 2
    assert "spec-bad/SPEC.md" in err


def test_a_root_that_does_not_exist_exits_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    rc, _stdout, err = _run(tmp_path / "nowhere", tmp_path / "out", capsys)

    assert rc == 2
    assert "unknown" in err
    assert not (tmp_path / "out").exists()


@pytest.mark.skipif(git is None, reason="git is not installed")
def test_a_git_checkout_whose_tracked_files_cannot_be_listed_exits_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    root = _fixture(tmp_path)
    (root / ".git").mkdir()  # not a repository: `git ls-files` fails

    rc, _stdout, err = _run(root, tmp_path / "out", capsys)

    assert rc == 2
    assert "git ls-files" in err
    assert not (tmp_path / "out").exists()


def test_a_crash_is_unknown_exit_2_never_a_partial_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    root = _fixture(tmp_path)

    def boom(_root: Path) -> dict[str, str]:
        raise RuntimeError("boom")

    monkeypatch.setattr(flag_inventory, "build_reports", boom)

    rc, _stdout, err = _run(root, tmp_path / "out", capsys)

    assert rc == 2
    assert "crashed" in err
    assert not (tmp_path / "out").exists()


# --- Doctor's join: the one station-side import ----------------------------------------------


def test_the_seam_finds_all_eight_names_of_doctors_join():
    join = flag_inventory._load_join()

    expected = {name for names in flag_inventory.JOIN_NAMES.values() for name in names}
    assert len(expected) == 8
    assert set(vars(join)) == expected
    assert all(callable(getattr(join, name)) for name in expected)


def test_the_eight_underscore_names_exist_in_doctors_modules():
    import importlib

    for module_name, names in flag_inventory.JOIN_NAMES.items():
        module = importlib.import_module(module_name)
        for attribute in names.values():
            assert callable(getattr(module, attribute)), f"{module_name}.{attribute} is gone"


def test_an_import_error_in_the_join_is_exit_2_naming_the_join(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    root = _fixture(tmp_path)
    _spec(root)

    def gone() -> flag_inventory.Join:
        raise ImportError("no module named pyforge.doctor")

    monkeypatch.setattr(flag_inventory, "_import_join", gone)

    rc, _stdout, err = _run(root, tmp_path / "out", capsys)

    assert rc == 2
    assert "pyforge.doctor.sources.capability_effect" in err
    assert not (tmp_path / "out").exists()


def test_a_renamed_join_name_is_exit_2_not_a_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    root = _fixture(tmp_path)
    _spec(root)
    renamed = {
        module: {**names, "canonical_epics": "_canonical_epics_renamed"} for module, names in flag_inventory.JOIN_NAMES.items()
    }
    monkeypatch.setattr(flag_inventory, "JOIN_NAMES", renamed)

    rc, _stdout, err = _run(root, tmp_path / "out", capsys)

    assert rc == 2
    assert "_canonical_epics_renamed" in err


def test_the_join_loads_from_this_checkouts_source_tree_in_an_interpreter_that_has_no_doctor_installed():
    import yaml

    # `-S`: no site-packages processing, so an editable install of pyforge-doctor is invisible. Only PyYAML's
    # directory is added back (the scripts need it), as the lean `pyforge-ci` environment has it.
    script = (
        "import sys\n"
        f"sys.path.append({str(Path(yaml.__file__).resolve().parent.parent)!r})\n"
        f"sys.path.insert(0, {str(_SCRIPTS_DIR)!r})\n"
        "import flag_inventory\n"
        "join = flag_inventory._load_join()\n"
        "print(type(join).__name__, len(vars(join)))\n"
    )
    proc = subprocess.run([sys.executable, "-S", "-c", script], capture_output=True, text=True, check=False)

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.split() == ["Join", "8"]


def test_a_doctor_that_cannot_be_imported_at_all_is_a_named_unavailable_error_never_a_traceback():
    script = (
        "import sys, importlib.abc\n"
        "class Block(importlib.abc.MetaPathFinder):\n"
        "    def find_spec(self, name, path, target=None):\n"
        "        if name == 'pyforge.doctor' or name.startswith('pyforge.doctor.'):\n"
        "            raise ImportError('blocked')\n"
        "sys.meta_path.insert(0, Block())\n"
        f"sys.path.insert(0, {str(_SCRIPTS_DIR)!r})\n"
        "import flag_inventory\n"
        "try:\n"
        "    flag_inventory._load_join()\n"
        "except flag_inventory.JoinUnavailable as exc:\n"
        "    print('unavailable:', exc)\n"
    )
    proc = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, check=False)

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.startswith("unavailable: cannot load Doctor's capability join")


# --- the live tree ---------------------------------------------------------------------------


@pytest.mark.skipif(git is None, reason="git is not installed")
def test_the_live_tree_builds_eight_reports_and_exits_0(tmp_path: Path):
    out = tmp_path / "out"

    proc = subprocess.run(
        [sys.executable, str(INVENTORY), "--out-dir", str(out)], capture_output=True, text=True, check=False, cwd=REPO_ROOT
    )

    stations = json.loads((REPO_ROOT / "docs/governance/guild-roster.json").read_text(encoding="utf-8"))["stations"]
    assert proc.returncode == 0, proc.stderr
    assert len(stations) == 8
    assert sorted(p.name for p in out.iterdir()) == sorted(f"pyforge-{s}.md" for s in stations)


@pytest.mark.skipif(git is None, reason="git is not installed")
def test_the_live_reports_agree_with_the_gate_on_the_warned_specs_of_every_station(tmp_path: Path, capsys):
    out = tmp_path / "out"
    assert flag_inventory.main(["--out-dir", str(out)]) == 0
    capsys.readouterr()
    inputs = flag_gate_check.load_inputs(REPO_ROOT)
    _judged, findings = flag_gate_check.judge_tree(REPO_ROOT, inputs)

    for report_path in sorted(out.iterdir()):
        station = report_path.stem
        text = report_path.read_text(encoding="utf-8")
        expected = {f.path for f in findings if f.kind == flag_gate_check.K_PRE_RULE and f.station == station}
        assert _warned_paths(text) == expected, station
        assert _header(text, "Warned specs") == len(expected)
        assert text.startswith(f"# Flag inventory: {station}\n")
        assert re.search(r"^- Read at SHA: `[0-9a-f]{40}`$", text, re.MULTILINE)
        rows = [ln for ln in text.splitlines() if re.match(r"\| CAP-\d+ \| (runtime|module|planning|unresolved) \|", ln)]
        unflagged = [r for r in rows if "| runtime |" in r and r.endswith("| none |")]
        assert _header(text, "Runtime CAPs with no flag") >= len(unflagged)


def test_the_checked_in_reports_exist_for_every_roster_station():
    stations = json.loads((REPO_ROOT / "docs/governance/guild-roster.json").read_text(encoding="utf-8"))["stations"]

    for station in stations:
        report = REPO_ROOT / "docs/governance/flag-inventory" / f"pyforge-{station}.md"
        assert report.is_file(), f"{report} is missing: run `pixi run -e pyforge-guild flag-inventory`"
        text = report.read_text(encoding="utf-8")
        assert text.startswith(f"# Flag inventory: pyforge-{station}\n")
        _header(text, "Runtime CAPs with no flag")
        _header(text, "Warned specs")


# --- a report, not a detector; outside every station -------------------------------------------


def test_the_inventory_is_not_a_detector_and_the_registry_reports_no_gap():
    found, gaps = detectors.discover()

    assert "flag_inventory" not in {d["name"] for d in found}
    assert not [g for g in gaps if "flag_inventory" in g]
    module = ast.parse(INVENTORY.read_text(encoding="utf-8"))
    assert not [
        node
        for node in module.body
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "DETECTOR" for t in node.targets)
    ]


def test_the_flag_inventory_task_is_registered_and_is_no_detectors_ci_row():
    manifest = tomllib.loads((REPO_ROOT / "pixi.toml").read_text(encoding="utf-8"))
    tasks = manifest["feature"]["guild-tasks"]["tasks"]

    assert tasks["flag-inventory"]["cmd"] == "python scripts/flag_inventory.py"
    assert "flag-inventory" not in tasks.get("detectors-ci", {}).get("depends-on", [])
    assert "flag_inventory" not in tasks.get("detectors-ci", {}).get("cmd", "")


def test_the_allowlist_carries_a_reason_tagged_line_for_the_script():
    lines = (_SCRIPTS_DIR / "spec_surface_allowlist.txt").read_text(encoding="utf-8").splitlines()

    line = next((ln for ln in lines if ln.startswith("scripts/flag_inventory.py")), None)
    assert line is not None
    assert "#" in line
    assert line.split("#", 1)[1].strip()


_ALLOWED_PYFORGE_MODULES = frozenset(flag_inventory.JOIN_NAMES)


def test_the_script_imports_no_pyforge_module_except_doctors_join_and_no_station_runtime_code():
    tree = ast.parse(INVENTORY.read_text(encoding="utf-8"))
    imported = {
        alias.name if isinstance(node, ast.Import) else (node.module or "")
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in (node.names if isinstance(node, ast.Import) else [node])
    }
    named = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and re.fullmatch(r"pyforge(\.\w+)+", node.value)
    }

    assert not {m for m in imported if m == "pyforge" or m.startswith("pyforge.")}
    assert named == _ALLOWED_PYFORGE_MODULES
    assert imported == {
        "__future__", "argparse", "ast", "collections.abc", "dataclasses", "flag_gate_check", "flag_rule",
        "importlib", "json", "os", "pathlib", "subprocess", "sys", "typing",
    }  # fmt: skip


def test_the_script_holds_no_copy_of_the_exemption_list_and_names_no_live_key():
    source = INVENTORY.read_text(encoding="utf-8")

    assert [v for v in flag_rule.load_exemptions() if v in source] == []
    assert [k for k in flag_gate_check.load_tree(REPO_ROOT) if k in source] == []


def test_the_script_reuses_the_gates_classifier_and_never_reads_the_second_tree():
    source = INVENTORY.read_text(encoding="utf-8")

    assert "flag_gate_check.judge_one" in source
    assert "flag_gate_check.K_PRE_RULE" in source
    assert ".steward/flags.json" not in source
