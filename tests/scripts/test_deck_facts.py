"""Unit tests for scripts/deck_facts.py (herald Story 20.2; spec-deck-family-currency
CAP-2 / CAP-5): the per-deck fact ledger is derived deterministically from tracked
sources via the real sprint parser, and ``--check`` reads a poster against it
(unmarked / mismatch / drifted / unsourced / unshown), advisory exit 0.

Fixture style mirrors tests/scripts/test_llms_full_check.py: a synthetic repo root
under tmp_path, the module reached through sys.path since scripts/ has no
__init__.py, and the module's ROOT / git / groundtruth seams monkeypatched so the
run is offline and independent of the live tree.
"""

from __future__ import annotations

import ast
import shlex
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import tomllib
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import deck_facts

_REAL_GROUNDTRUTH = deck_facts.groundtruth  # captured before any fixture patches it

HEAD = {"sha": "cafef00dcafef00dcafef00dcafef00dcafef00d", "date": "2026-01-01T00:00:00+00:00",
        "short_date": "2026-01-01", "dirty": False}
POSTER_DATE = "2025-12-31"

POSTER = """<html><head><title>Alpha 7.7.7</title>
<style>.x::after { content: "9.9.9"; }</style>
<script>var hidden = "1/1";</script></head>
<body>
<h1>Alpha</h1>
<p>BMAD core <span data-fact="bmad_core_version">6.10.0</span></p>
<table><tr><td>128/333</td><td>5/18</td></tr></table>
<div><span class="k">01 · The Proclaimer</span><span class="tag">4/27</span></div>
<p>bmad-loop v0.11.1 &middot; herald 2026-07-31 &middot; ruled 2026-02-02</p>
<p>fleet <b>4</b>/6 stories &middot; epics <span data-fact="fleet_epics_done_total">2 / 4</span></p>
<p>stories 2/3 done<br>verbs <b data-fact="cli_verbs"><i>1</i></b>
&middot; skill <em data-fact="cfe_skill_version">v8.90.5</em>
&middot; <span data-fact="no_such_row">42</span></p>
</body></html>
"""

ALPHA_LEDGER = (
    "# generated\ndevelopment_status:\n"
    "  1-1-first: done\n  1-2-second: done\n  2-1-third: backlog\n"
    "  epic-1: done\n  epic-1-retrospective: optional\n  epic-2: backlog\n"
)
BETA_LEDGER = "development_status:\n  1-1-only: done\n  epic-1: done\n  epic-1-retrospective: done\n"
GAMMA_LEDGER = "development_status:\n  1-1-g: done\n  1-2-g: backlog\n  epic-1: backlog\n"
# fleet over alpha (2/3, 1/2) + beta (1/1, 1/1) + gamma (1/2, 0/1) = 4/6 stories, 2/4 epics


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def root(tmp_path, monkeypatch) -> Path:
    """A synthetic repo with three stations; ``pyforge-alpha`` has a poster, ``pyforge-beta`` none,
    ``pyforge-gamma`` has a ``cli/`` sub-package; ``pyforge-genesis`` is a non-station deck."""
    _write(tmp_path / "docs/governance/guild-roster.json", '{"stations": ["beta", "alpha", "gamma"]}')
    proj = tmp_path / "_bmad-output/projects"
    _write(proj / "pyforge-alpha/planning-artifacts/sprint-status-ledger.yaml", ALPHA_LEDGER)
    _write(proj / "pyforge-beta/planning-artifacts/sprint-status-ledger.yaml", BETA_LEDGER)
    _write(proj / "pyforge-gamma/planning-artifacts/sprint-status-ledger.yaml", GAMMA_LEDGER)
    _write(tmp_path / "_bmad/_config/manifest.yaml", "installation:\n  version: 6.12.0\n  installDate: x\n")
    _write(
        tmp_path / "pixi.lock",
        "environments:\n  default:\n    packages:\n      linux-64:\n"
        "      - conda: https://x/noarch/bmad-loop-0.11.1-pyha7a566d_0.conda\n"
        "      - conda: https://x/noarch/other-1.0-py_0.conda\n",
    )
    _write(tmp_path / ".claude/skills/conda-forge-expert/SKILL.md", "---\nname: cfe\nversion: 8.90.5\n---\n# x\n")
    for d in ("r1", "r2", ".hidden", "example", "examples"):
        (tmp_path / "recipes" / d).mkdir(parents=True)
    (tmp_path / "recipes" / "stray-file").write_text("")
    _write(
        proj / "pyforge-alpha/planning-artifacts/specs/spec-pyforge-alpha/SPEC.md",
        '---\nid: SPEC-alpha\nstatus: "ready"   # quoted, with a comment\n---\n'
        "## Capabilities\n- **CAP-1**\n  - intent: a\n- **CAP-2 — titled bullet**\n"
        "## Notes\n- CAP-1..CAP-2 above; see also CAP-7 of spec-other and CAP-9's prose mention\n",
    )
    _write(
        tmp_path / "docs/dreams/pyforge-alpha.md",
        "---\ntitle: a\nstatus: dreamt   # 2026-01-01\n---\n## Realization log\n"
        "- **2026-02-02** — first\n- **2026-02-02 (later)** — same day\n- **2026-03-03/04** — span\n"
        "- plain bullet with a 2026-04-04 date is not an entry\n",
    )
    _write(tmp_path / "docs/dreams/README.md", "# no frontmatter\n")
    pkgs = tmp_path / "src/shared/packages"
    _write(
        pkgs / "pyforge-alpha/pyproject.toml",
        '[project]\nname = "pyforge-alpha"\nversion = "0.1.0"\n\n[project.scripts]\nalpha = "pyforge.alpha.cli:main"\n',
    )
    _write(
        pkgs / "pyforge-alpha/src/pyforge/alpha/cli.py",
        "import argparse\n\ndef main():\n    p = argparse.ArgumentParser()\n    s = p.add_subparsers()\n"
        '    s.add_parser(\n        "scan", help="x")\n    for n in ("dyn",):\n        s.add_parser(n)\n',
    )
    _write(
        pkgs / "pyforge-gamma/pyproject.toml",
        '[project]\nname = "pyforge-gamma"\nversion = "0.2.0"\n\n[project.scripts]\ngamma = "pyforge.gamma.cli.main:main"\n',
    )
    _write(pkgs / "pyforge-gamma/src/pyforge/gamma/cli/main.py", 'sub.add_parser("run")\n')
    _write(pkgs / "pyforge-gamma/src/pyforge/gamma/cli/extra.py", 'sub.add_parser("show")\n')
    _write(pkgs / "pyforge-gamma/src/pyforge/gamma/tools.py", 'sub.add_parser("stray")\n')
    _write(tmp_path / "presentations/pyforge-alpha/project/Alpha Infographic standalone.html", POSTER)
    for deck in ("pyforge-beta", "pyforge-gamma", "pyforge-genesis"):
        (tmp_path / "presentations" / deck).mkdir(parents=True)

    monkeypatch.setattr(deck_facts, "ROOT", tmp_path)
    monkeypatch.setattr(deck_facts, "head_info", lambda root: dict(HEAD))
    monkeypatch.setattr(deck_facts, "poster_commit_date", lambda root, poster: POSTER_DATE)
    monkeypatch.setattr(deck_facts, "groundtruth",
                        lambda root: {"mcp_tools": 46, "atlas_phases": 22, "schema_version": None})
    return tmp_path


def _rows(root: Path, slug: str) -> dict[str, dict]:
    doc = yaml.safe_load((root / "presentations" / slug / "facts.yaml").read_text(encoding="utf-8"))
    return {f["id"]: f for f in doc["facts"]}


def _check_lines(capsys, slug: str) -> list[str]:
    capsys.readouterr()
    assert deck_facts.main([slug, "--check"]) == 0
    return capsys.readouterr().out.splitlines()


def _kind(lines: list[str], kind: str) -> list[str]:
    return [l for l in lines if l.startswith(kind)]


# ------------------------------------------------------------------- derive

def test_derive_is_deterministic_and_every_row_has_five_fields(root, capsys):
    assert deck_facts.main(["pyforge-alpha"]) == 0
    ledger = root / "presentations/pyforge-alpha/facts.yaml"
    first = ledger.read_bytes()
    assert deck_facts.main(["pyforge-alpha"]) == 0
    assert ledger.read_bytes() == first
    assert "unchanged" in capsys.readouterr().out

    doc = yaml.safe_load(first)
    assert doc["deck"] == "pyforge-alpha"
    assert doc["persona"] == "Alpha"
    assert doc["tree"] == HEAD["sha"]
    assert doc["derived_at"] == HEAD["date"]  # quoted: stays a string, not a YAML timestamp
    ids = [f["id"] for f in doc["facts"]]
    assert ids == sorted(ids) and len(set(ids)) == len(ids)
    for f in doc["facts"]:
        assert set(f) == {"id", "value", "source", "method", "shown_as"}
        assert isinstance(f["value"], str) and f["value"]
        assert f["value"] in f["shown_as"]


def test_dirty_tree_is_named_in_the_header(root, monkeypatch):
    monkeypatch.setattr(deck_facts, "head_info", lambda root: dict(HEAD, dirty=True))
    deck_facts.main(["pyforge-alpha"])
    doc = yaml.safe_load((root / "presentations/pyforge-alpha/facts.yaml").read_text())
    assert doc["tree"] == HEAD["sha"] + "-dirty"
    assert isinstance(doc["tree"], str)


def test_counts_come_from_the_real_parser_and_tracked_sources(root):
    deck_facts.main(["pyforge-alpha"])
    rows = _rows(root, "pyforge-alpha")
    # own ledger: stories = non-epic keys, epics = epic-N minus retrospectives, `done` literal
    assert rows["stories_done_total"]["value"] == "2/3"
    assert "2 of 3" in rows["stories_done_total"]["shown_as"]
    assert rows["epics_done_total"]["value"] == "1/2"
    # one per-station pair on every deck, plus fleet totals over every roster station's twin
    assert rows["alpha_stories_done_total"]["value"] == "2/3"
    assert rows["beta_stories_done_total"]["value"] == "1/1"
    assert rows["gamma_epics_done_total"]["value"] == "0/1"
    assert rows["fleet_stories_done_total"]["value"] == "4/6"
    assert rows["fleet_epics_done_total"]["value"] == "2/4"
    assert rows["bmad_core_version"]["value"] == "6.12.0"
    assert rows["bmad_loop_version"]["value"] == "0.11.1"
    assert rows["cfe_skill_version"]["value"] == "8.90.5"
    assert rows["groundtruth_mcp_tools"]["value"] == "46"
    assert rows["recipes_count"]["value"] == "2"  # hidden dir, stray file, example/ + examples/ excluded
    assert "recipes/example/" in rows["recipes_count"]["method"]
    assert rows["spec_status"]["value"] == "ready"  # quotes and trailing comment stripped
    assert rows["spec_capabilities"]["value"] == "2"  # definition lines only; CAP-7 / CAP-9 prose ignored
    assert "CAP-1..2" in rows["spec_capabilities"]["shown_as"]
    assert "never prose mentions" in rows["spec_capabilities"]["method"]
    assert rows["dream_status"]["value"] == "dreamt"
    assert rows["package_version"]["value"] == "0.1.0"
    assert rows["console_entry"]["value"] == "alpha"
    assert rows["cli_verbs"]["value"] == "1"  # literal "scan" only; dynamic add_parser(n) not counted
    assert "scan" in rows["cli_verbs"]["shown_as"]
    # the date class
    assert rows["tree_commit_date"]["value"] == "2026-01-01"
    assert rows["poster_last_commit_date"]["value"] == POSTER_DATE
    assert {k for k in rows if k.startswith("dream_log_")} == {"dream_log_2026-02-02", "dream_log_2026-03-03"}
    assert rows["dream_log_2026-02-02"]["method"] == "Realization log entry date"
    assert "tests_collected" not in rows  # only under --with-tests


def test_her_scheme_and_heading_ranges_count_as_definitions(root):
    spec = root / "_bmad-output/projects/pyforge-alpha/planning-artifacts/specs/spec-pyforge-alpha/SPEC.md"
    spec.write_text(
        "---\nstatus: shipped\n---\n- **HER-1 — a.**\n- **HER-2 — b.**\n- **HER-3 — c.**\n"
        "### HER-4..HER-10 — folded (was CAP-1..CAP-7)\n### HER-11..HER-13 — more (was CAP-1..CAP-3)\n"
    )
    deck_facts.main(["pyforge-alpha"])
    row = _rows(root, "pyforge-alpha")["spec_capabilities"]
    assert row["value"] == "13"
    assert row["shown_as"] == ["13", "HER-1..13", "HER-1..HER-13"]


def test_sub_package_cli_scan_covers_only_the_entry_module_package(root):
    deck_facts.main(["pyforge-gamma"])
    row = _rows(root, "pyforge-gamma")["cli_verbs"]
    assert row["value"] == "2"  # cli/main.py + cli/extra.py; the stray tools.py is outside cli/
    assert row["source"].endswith("/cli")
    assert "run, show" in row["shown_as"]


def test_ledger_proxy_annotates_the_stations_pair_and_adds_no_package_rows(root, monkeypatch):
    monkeypatch.setattr(deck_facts, "LEDGER_PROXY", {"pyforge-canopy": "alpha"})
    (root / "presentations/pyforge-canopy").mkdir()
    deck_facts.main(["pyforge-canopy"])
    rows = _rows(root, "pyforge-canopy")
    assert rows["alpha_stories_done_total"]["value"] == "2/3"
    assert rows["alpha_epics_done_total"]["value"] == "1/2"
    assert rows["alpha_stories_done_total"]["method"].endswith("(LEDGER_PROXY)")
    assert not rows["beta_stories_done_total"]["method"].endswith("(LEDGER_PROXY)")
    assert "stories_done_total" not in rows  # no unprefixed duplicate of the proxied pair
    assert "package_version" not in rows


def test_genesis_rows_and_omissions_for_a_non_station_deck(root, capsys):
    deck_facts.main(["pyforge-genesis", "--with-tests"])
    err = capsys.readouterr().err
    rows = _rows(root, "pyforge-genesis")
    assert rows["guild_stations"]["value"] == "3"
    assert rows["dreams_total"]["value"] == "1"  # README.md has no frontmatter
    assert rows["dreams_dreamt"]["value"] == "1"
    assert "omitted spec_status, spec_capabilities: 0 SPEC.md match" in err  # spec_hits != 1
    assert "omitted tests_collected: pyforge-genesis is not a station" in err
    assert "omitted dream_log_*" in err
    # two SPEC.md matches are just as unusable as none
    for project in ("p1", "p2"):
        _write(root / "_bmad-output/projects" / project / "planning-artifacts/specs/spec-pyforge-genesis/SPEC.md",
               "---\nstatus: ready\n---\n- **CAP-1**\n")
    deck_facts.main(["pyforge-genesis"])
    assert "2 SPEC.md match" in capsys.readouterr().err
    assert "spec_status" not in _rows(root, "pyforge-genesis")


def test_unsourceable_facts_are_omitted_and_named_on_stderr(root, capsys):
    (root / "pixi.lock").unlink()
    deck_facts.main(["pyforge-alpha"])
    err = capsys.readouterr().err
    rows = _rows(root, "pyforge-alpha")
    assert "omitted bmad_loop_version" in err and "bmad_loop_version" not in rows
    assert "omitted groundtruth_schema_version: null" in err  # a JSON null is never the fact "None"
    assert "groundtruth_schema_version" not in rows


def test_ambiguous_bmad_loop_lock_is_omitted_naming_both_versions(root, capsys):
    lock = root / "pixi.lock"
    lock.write_text(lock.read_text() + "  other:\n    packages:\n      linux-64:\n"
                    "      - conda: https://x/noarch/bmad-loop-0.11.0-pyha7a566d_0.conda\n")
    deck_facts.main(["pyforge-alpha"])
    err = capsys.readouterr().err
    assert "omitted bmad_loop_version" in err and "0.11.0" in err and "0.11.1" in err
    assert "bmad_loop_version" not in _rows(root, "pyforge-alpha")


def test_two_component_manifest_version_stays_a_string(root):
    (root / "_bmad/_config/manifest.yaml").write_text("installation:\n  version: 6.10\n")
    deck_facts.main(["pyforge-alpha"])
    assert _rows(root, "pyforge-alpha")["bmad_core_version"]["value"] == "6.10"


def test_multiple_posters_are_named_and_the_first_is_used(root, capsys):
    _write(root / "presentations/pyforge-alpha/project/Alpha Two Infographic standalone.html", POSTER)
    deck_facts.main(["pyforge-alpha"])
    err = capsys.readouterr().err
    assert "multiple posters match" in err
    assert "Alpha Infographic standalone.html" in err and "Alpha Two Infographic standalone.html" in err
    assert any(l.endswith("-- using Alpha Infographic standalone.html") for l in err.splitlines())
    doc = yaml.safe_load((root / "presentations/pyforge-alpha/facts.yaml").read_text())
    assert doc["persona"] == "Alpha"


def test_with_tests_adds_the_row_only_when_the_collect_succeeds(root, monkeypatch, capsys):
    monkeypatch.setattr(deck_facts, "tests_collected", lambda root, station: "2132")
    deck_facts.main(["pyforge-alpha", "--with-tests"])
    row = _rows(root, "pyforge-alpha")["tests_collected"]
    assert row["value"] == "2132"
    assert row["source"] == ("pixi run -e pyforge-alpha pytest --collect-only -q "
                             "src/shared/packages/pyforge-alpha/tests")
    monkeypatch.setattr(deck_facts, "tests_collected", lambda root, station: None)  # pytest failed
    deck_facts.main(["pyforge-alpha", "--with-tests"])
    assert "omitted tests_collected" in capsys.readouterr().err
    assert "tests_collected" not in _rows(root, "pyforge-alpha")


def test_pytest_collect_summary_accepts_a_deselected_fraction(root, monkeypatch):
    fake = SimpleNamespace(returncode=0, stdout="x.py::t\n45/50 tests collected (5 deselected) in 0.1s\n")
    monkeypatch.setattr(deck_facts.subprocess, "run", lambda *a, **k: fake)
    assert deck_facts.tests_collected(root, "alpha") == "45"
    fake.stdout = "2132 tests collected in 1.30s\n"
    assert deck_facts.tests_collected(root, "alpha") == "2132"
    fake.returncode = 3
    assert deck_facts.tests_collected(root, "alpha") is None


def test_groundtruth_runs_the_declared_pixi_task_command(root, monkeypatch):
    cfg = tomllib.loads((REPO_ROOT / "pixi.toml").read_text(encoding="utf-8"))
    cmd = shlex.split(cfg["feature"]["local-recipes"]["tasks"]["bmad-groundtruth"]["cmd"])
    assert cmd[0] == "python"
    calls: list[list[str]] = []

    def fake_run(argv, **kwargs):
        calls.append(list(argv))
        return SimpleNamespace(returncode=0, stdout='{"mcp_tools": 46}')

    monkeypatch.setattr(deck_facts.subprocess, "run", fake_run)
    assert _REAL_GROUNDTRUTH(root) == {"mcp_tools": 46}
    assert calls[0][0] == sys.executable
    assert calls[0][1:] == cmd[1:]


@pytest.mark.parametrize("returncode, stdout", [(1, '{"mcp_tools": 46}'), (0, "not json"), (0, "[1, 2]")])
def test_groundtruth_failures_yield_none_and_a_named_omission(root, monkeypatch, capsys, returncode, stdout):
    fake = SimpleNamespace(returncode=returncode, stdout=stdout)
    monkeypatch.setattr(deck_facts.subprocess, "run", lambda *a, **k: fake)
    monkeypatch.setattr(deck_facts, "groundtruth", _REAL_GROUNDTRUTH)
    assert _REAL_GROUNDTRUTH(root) is None
    deck_facts.main(["pyforge-alpha"])
    assert "omitted groundtruth_*" in capsys.readouterr().err
    assert not [k for k in _rows(root, "pyforge-alpha") if k.startswith("groundtruth_")]


def test_render_yaml_with_zero_facts_is_valid_yaml():
    text = deck_facts.render_yaml({"deck": "x", "persona": "", "derived_at": "d", "tree": "t", "facts": []})
    assert "facts: []" in text
    doc = yaml.safe_load(text)
    assert doc["facts"] == [] and doc["tree"] == "t"


# -------------------------------------------------------------------- check

def test_check_reports_planted_mismatch_unmarked_and_unshown(root, capsys):
    deck_facts.main(["pyforge-alpha"])
    out = _check_lines(capsys, "pyforge-alpha")

    mismatch = _kind(out, "mismatch")
    assert len(mismatch) == 2
    planted = [l for l in mismatch if "bmad_core_version" in l]
    assert len(planted) == 1 and '"6.10.0"' in planted[0] and 'ledger "6.12.0"' in planted[0]
    assert any("no_such_row" in l and "no such row" in l for l in mismatch)

    unmarked = {l.split()[1] for l in _kind(out, "unmarked")}
    assert unmarked == {"128/333", "5/18", "4/27", "2026-07-31"}  # sibling chips never fuse
    # <title>/style/script are not visible; v0.11.1 resolves to 0.11.1; <b>4</b>/6 is one
    # token; adjacent <td>s never fuse; the Dream's Realization-log date resolves
    for tok in ("7.7.7", "9.9.9", "1/1", "0.11.1", "4/6", "2/3", "2026-02-02"):
        assert tok not in unmarked, tok
    assert not any("128/3334" in l for l in out)

    unshown = {l.split()[1] for l in _kind(out, "unshown")}
    assert "package_version" in unshown  # 0.1.0 appears nowhere
    for shown_or_marked in ("stories_done_total", "fleet_stories_done_total", "fleet_epics_done_total",
                            "bmad_loop_version", "cfe_skill_version", "dream_log_2026-02-02",
                            "bmad_core_version", "cli_verbs"):
        assert shown_or_marked not in unshown, shown_or_marked

    assert not _kind(out, "drifted") and not _kind(out, "unsourced")
    summary = _kind(out, "summary")
    assert len(summary) == 1 and out[-1] == summary[0]
    assert "2 mismatch" in summary[0] and "4 unmarked" in summary[0] and "0 unsourced" in summary[0]


def test_check_reports_drift_when_a_source_moved(root, capsys):
    deck_facts.main(["pyforge-alpha"])
    (root / "_bmad/_config/manifest.yaml").write_text("installation:\n  version: 6.13.0\n")
    drifted = _kind(_check_lines(capsys, "pyforge-alpha"), "drifted")
    assert len(drifted) == 1
    assert "bmad_core_version" in drifted[0] and 'ledger "6.12.0", fresh "6.13.0"' in drifted[0]


def test_check_tells_unsourced_from_drifted_on_one_sided_rows(root, monkeypatch, capsys):
    monkeypatch.setattr(deck_facts, "tests_collected", lambda root, station: "2132")
    deck_facts.main(["pyforge-alpha", "--with-tests"])
    # a plain --check cannot derive tests_collected: that is `unsourced`, not drift
    out = _check_lines(capsys, "pyforge-alpha")
    unsourced = _kind(out, "unsourced")
    assert len(unsourced) == 1
    assert unsourced[0].startswith('unsourced  tests_collected  ledger "2132" -- not derived this run: only derived under')
    assert not _kind(out, "drifted")
    assert "1 unsourced" in out[-1]
    # a row new in the fresh derivation is `drifted … ledger absent`
    (root / "docs/dreams/pyforge-alpha.md").write_text(
        (root / "docs/dreams/pyforge-alpha.md").read_text() + "- **2026-05-05** — new ruling\n")
    drifted = _kind(_check_lines(capsys, "pyforge-alpha"), "drifted")
    assert drifted == ['drifted   dream_log_2026-05-05  ledger absent, fresh "2026-05-05"']


def test_check_without_a_poster_says_so_and_exits_zero(root, capsys):
    deck_facts.main(["pyforge-beta"])
    err = capsys.readouterr().err
    assert "no poster" in err
    assert yaml.safe_load((root / "presentations/pyforge-beta/facts.yaml").read_text())["persona"] == ""
    out = _check_lines(capsys, "pyforge-beta")
    assert "no poster: presentations/pyforge-beta/project/* Infographic standalone.html" in out[0]
    assert out[-1].startswith("summary")


def test_usage_errors_exit_two(root):
    with pytest.raises(SystemExit) as unknown:
        deck_facts.main(["nope"])
    assert unknown.value.code == 2
    with pytest.raises(SystemExit) as before_derive:  # --check before any ledger exists
        deck_facts.main(["pyforge-alpha", "--check"])
    assert before_derive.value.code == 2


def test_deck_facts_is_not_a_detector():
    """Spec Never-boundary: no DETECTOR marker. The detector registry's glob is
    `scripts/*_check.py` (scripts/detectors.py SEARCH), so `deck_facts.py` is
    invisible to `detectors -- --list` by construction -- only the marker needs
    asserting, and it is the AST assignment `detectors._declared_scope` parses,
    not the word in prose."""
    tree = ast.parse((REPO_ROOT / "scripts/deck_facts.py").read_text(encoding="utf-8"))
    markers = [n for n in tree.body if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == "DETECTOR" for t in n.targets)]
    assert markers == []
