"""Unit tests for scripts/deck_facts.py (herald Stories 20.2 and 20.14;
spec-deck-family-currency CAP-2 / CAP-5 / CAP-6): the per-deck fact ledger is derived
deterministically from tracked sources via the real sprint parser, ``--check`` reads a
poster against it (unmarked / mismatch / drifted / unsourced / unshown), and
``--refresh`` (CAP-6, Story 20.14) rewrites every stale ``data-fact`` literal the check
reads -- and only those, by the old literal's shape. Advisory, exit 0.

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
    monkeypatch.setattr(deck_facts, "tracked_recipe_dirs", lambda root: ["r1", "r2"])  # git ls-files seam (the synthetic root is not a git repo)
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
    assert rows["recipes_count"]["value"] == "2"  # tracked dirs only (seam)
    assert "git ls-files" in rows["recipes_count"]["method"]
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
    with pytest.raises(SystemExit) as unknown_refresh:
        deck_facts.main(["nope", "--refresh"])
    assert unknown_refresh.value.code == 2
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


def test_recipes_count_omitted_when_git_cannot_answer(root, monkeypatch, capsys):
    monkeypatch.setattr(deck_facts, "tracked_recipe_dirs", lambda root: None)
    deck_facts.main(["pyforge-alpha"])
    assert "omitted recipes_count" in capsys.readouterr().err
    assert "recipes_count" not in _rows(root, "pyforge-alpha")


def test_tracked_recipe_dirs_reads_git_and_drops_templates_and_dotdirs(monkeypatch, tmp_path):
    class P:  # a fake CompletedProcess
        returncode = 0
        stdout = ("recipes/a/recipe.yaml\0recipes/a/build.sh\0recipes/b/meta.yaml\0"
                  "recipes/example/meta.yaml\0recipes/.scratch/x\0recipes/README.md\0")
    monkeypatch.setattr(deck_facts.subprocess, "run", lambda *a, **k: P())
    assert deck_facts.tracked_recipe_dirs(tmp_path) == ["a", "b"]

    class F:
        returncode = 128
        stdout = ""
    monkeypatch.setattr(deck_facts.subprocess, "run", lambda *a, **k: F())
    assert deck_facts.tracked_recipe_dirs(tmp_path) is None


# ------------------------------------------------------------------ refresh
# (herald Story 20.14; CAP-6): `--refresh` rewrites every stale plain data-fact
# mark from the fresh ledger by the OLD literal's shape, splicing bytes.

REFRESH_POSTER = (
    "<html><head><title>Alpha</title></head>\r\n"
    "<body>\r\n"
    '<p>fleet <span data-fact="fleet_stories_done_total">4/6</span> · '
    '<span class="k" data-fact="fleet_epics_done_total">2 of 4</span></p>\r\n'
    '<p>loop <em data-fact="bmad_loop_version">v0.11.1</em> · '
    'core <span data-fact="bmad_core_version">6.12.0</span></p>\r\n'
    '<p>verbs <b data-fact="cli_verbs"><i>1</i></b> · '
    'tests <span data-fact="tests_collected">2132</span></p>\r\n'
    '<p>prose keeps 4/6 and v0.11.1; gamma <span data-fact="gamma_stories_done_total"> 1 / 2 </span></p>\r\n'
    "</body></html>\r\n"
)
# What --refresh must produce after the `stale` move: four spans, nothing else.
REFRESHED_POSTER = (
    REFRESH_POSTER.replace(">4/6<", ">5/6<").replace(">2 of 4<", ">3 of 4<")
    .replace(">v0.11.1<", ">v0.11.2<").replace("> 1 / 2 <", "> 2/2 <")
)


def _poster(root: Path) -> Path:
    return root / "presentations/pyforge-alpha/project/Alpha Infographic standalone.html"


def _stale_poster(root: Path, body: str) -> Path:
    """`body` authored as the alpha poster against today's ledger, then the sources
    move: gamma lands its second story and its epic (fleet 4/6 -> 5/6 stories, 2/4
    -> 3/4 epics; gamma 1/2 -> 2/2) and the lock bumps bmad-loop 0.11.1 -> 0.11.2.
    facts.yaml still holds the previous values -- the state --refresh is for."""
    poster = _poster(root)
    poster.write_bytes(body.encode("utf-8"))
    assert deck_facts.main(["pyforge-alpha"]) == 0
    _write(root / "_bmad-output/projects/pyforge-gamma/planning-artifacts/sprint-status-ledger.yaml",
           GAMMA_LEDGER.replace("1-2-g: backlog", "1-2-g: done").replace("epic-1: backlog", "epic-1: done"))
    lock = root / "pixi.lock"
    lock.write_text(lock.read_text().replace("bmad-loop-0.11.1", "bmad-loop-0.11.2"))
    return poster


@pytest.fixture
def stale(root) -> Path:
    return _stale_poster(root, REFRESH_POSTER)


def _refresh_lines(capsys, *flags: str) -> list[str]:
    capsys.readouterr()
    assert deck_facts.main(["pyforge-alpha", "--refresh", *flags]) == 0
    return capsys.readouterr().out.splitlines()


def test_refresh_rewrites_stale_marks_by_the_old_literals_shape(root, stale, capsys):
    out = _refresh_lines(capsys)
    assert out[0].startswith("pyforge-alpha: wrote")  # the ledger is written first
    assert _kind(out, "refreshed") == [
        'refreshed  fleet_stories_done_total  "4/6" -> "5/6"',            # value -> value
        'refreshed  fleet_epics_done_total  "2 of 4" -> "3 of 4"',        # shown_as[1] keeps its shape
        'refreshed  bmad_loop_version  "v0.11.1" -> "v0.11.2"',           # the stripped v restored
        'refreshed  gamma_stories_done_total  "1/2" -> "2/2"',            # `1 / 2` normalised like --check
    ]
    assert _kind(out, "skipped") == ["skipped  cli_verbs  nested mark", "skipped  tests_collected  no row"]
    assert not any("bmad_core_version" in l for l in out)  # already resolves: untouched, unprinted
    assert out[-1] == "summary   pyforge-alpha: 4 refreshed, 2 skipped"
    assert _rows(root, "pyforge-alpha")["fleet_stories_done_total"]["value"] == "5/6"


def test_refresh_splices_bytes_only_inside_rewritten_spans(root, stale, capsys):
    _refresh_lines(capsys)
    # CRLF line endings, the middle dots, the prose tokens `4/6` / `v0.11.1`, the
    # nested and no-row marks and the span's own edge whitespace all survive.
    assert stale.read_bytes() == REFRESHED_POSTER.encode("utf-8")


def test_refresh_is_idempotent_and_leaves_check_clean(root, stale, monkeypatch, capsys):
    monkeypatch.setattr(deck_facts, "tests_collected", lambda root, station: "2140")
    out = _refresh_lines(capsys, "--with-tests", "--check")
    # a row the previous ledger lacked (tests_collected on a plain run) still refreshes
    assert 'refreshed  tests_collected  "2132" -> "2140"' in out
    summary = _kind(out, "summary")
    assert summary[0] == "summary   pyforge-alpha: 5 refreshed, 1 skipped"  # nested cli_verbs only
    # --refresh --check: the check runs after the refresh, against the ledger just written
    assert out.index(summary[0]) < out.index(summary[1])
    assert not _kind(out, "mismatch") and not _kind(out, "drifted")
    assert "0 mismatch" in summary[1] and "0 drifted" in summary[1]

    after = stale.read_bytes()
    again = _refresh_lines(capsys, "--with-tests")
    assert not _kind(again, "refreshed")
    assert again[-1] == "summary   pyforge-alpha: 0 refreshed, 1 skipped"
    assert stale.read_bytes() == after


def test_refresh_keeps_the_shape_when_facts_yaml_was_already_rederived(root, stale, capsys):
    assert deck_facts.main(["pyforge-alpha"]) == 0  # a plain derive after the move: previous == fresh
    out = _refresh_lines(capsys)
    assert 'refreshed  fleet_epics_done_total  "2 of 4" -> "3 of 4"' in out
    assert 'refreshed  bmad_loop_version  "v0.11.1" -> "v0.11.2"' in out
    assert stale.read_bytes() == REFRESHED_POSTER.encode("utf-8")


def test_refresh_with_no_stale_mark_leaves_the_poster_bytes_unchanged(root, capsys):
    poster = _poster(root)
    poster.write_bytes(REFRESH_POSTER.encode("utf-8"))
    assert deck_facts.main(["pyforge-alpha"]) == 0
    before = poster.stat().st_mtime_ns
    out = _refresh_lines(capsys)
    assert out[-1] == "summary   pyforge-alpha: 0 refreshed, 2 skipped"
    assert poster.read_bytes() == REFRESH_POSTER.encode("utf-8")
    assert poster.stat().st_mtime_ns == before  # not even rewritten with identical bytes


def test_refresh_without_a_poster_says_so_and_still_writes_the_ledger(root, capsys):
    assert deck_facts.main(["pyforge-beta", "--refresh"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert f"no poster: presentations/pyforge-beta/project/*{deck_facts.POSTER_SUFFIX}" in out
    assert out[-1] == "summary   pyforge-beta: 0 refreshed, 0 skipped"
    assert (root / "presentations/pyforge-beta/facts.yaml").is_file()


def test_replacement_maps_value_to_value_and_shown_as_index_to_index():
    prev = {"value": "848/878", "shown_as": ["848/878", "848 of 878", "848 done"]}
    new = {"value": "852/878", "shown_as": ["852/878", "852 of 878"]}
    assert deck_facts._replacement("848/878", prev, new) == "852/878"
    assert deck_facts._replacement("848 of 878", prev, new) == "852 of 878"
    assert deck_facts._replacement("848 done", prev, new) == "852/878"      # shown_as[2] gone: the value
    assert deck_facts._replacement("848 of 878", None, new) == "852 of 878"  # no previous row: same digit shape
    assert deck_facts._replacement("848 of 878", new, new) == "852 of 878"   # ledger already re-derived
    assert deck_facts._replacement("stale", prev, new) == "852/878"          # no shape match: the value
    status = {"value": "in-progress", "shown_as": ["in-progress"]}
    assert deck_facts._replacement("ready", None, status) == "in-progress"


# --- Story 20.14 review round: --refresh must rewrite exactly the marks --check
# reads -- located with the parser's own tag bookkeeping, never a regex over raw
# text -- and must leave every other `data-fact` in the file alone.

def test_a_quoted_angle_bracket_in_an_attribute_does_not_cut_the_span(root, capsys):
    body = '<p>fleet <span data-fact="fleet_stories_done_total" title="4/6 -> 5/6">4/6</span></p>\n'
    poster = _stale_poster(root, body)
    out = _refresh_lines(capsys)
    assert _kind(out, "refreshed") == ['refreshed  fleet_stories_done_total  "4/6" -> "5/6"']
    assert not _kind(out, "skipped")
    assert poster.read_text(encoding="utf-8") == body.replace(">4/6<", ">5/6<")  # the attribute survives


def test_an_untokenizable_start_tag_is_reported_not_spliced(root, capsys):
    """An unterminated attribute quote: the parser cannot read the tag, so nothing
    downstream of it is a mark anyone can trust -- report, never guess."""
    body = '<p>fleet <span data-fact="fleet_stories_done_total" title="oops>4/6</span> tail</p>\n'
    poster = _stale_poster(root, body)
    out = _refresh_lines(capsys)
    assert _kind(out, "skipped") == ["skipped  fleet_stories_done_total  unparsed tag"]
    assert poster.read_text(encoding="utf-8") == body


def test_unquoted_and_spaced_data_fact_attributes_are_refreshed(root, capsys):
    """Both forms --check's parser accepts; the old regex visited neither."""
    body = ('<p><span data-fact=fleet_stories_done_total>4/6</span> · '
            '<span data-fact = "fleet_epics_done_total">2 of 4</span></p>\n')
    poster = _stale_poster(root, body)
    out = _refresh_lines(capsys)
    assert _kind(out, "refreshed") == [
        'refreshed  fleet_stories_done_total  "4/6" -> "5/6"',
        'refreshed  fleet_epics_done_total  "2 of 4" -> "3 of 4"',
    ]
    assert poster.read_text(encoding="utf-8") == body.replace(">4/6<", ">5/6<").replace(">2 of 4<", ">3 of 4<")


def test_a_mark_check_reads_but_refresh_misses_is_reported_unvisited(root, monkeypatch, capsys):
    """The cross-check that keeps `0 skipped` from ever hiding a stale mark."""
    body = ('<p><span data-fact="fleet_stories_done_total">4/6</span> · '
            '<span data-fact="fleet_epics_done_total">2 of 4</span></p>\n')
    poster = _stale_poster(root, body)
    real = deck_facts._mark_spans
    monkeypatch.setattr(deck_facts, "_mark_spans",
                        lambda text: [m for m in real(text) if m["id"] != "fleet_epics_done_total"])
    out = _refresh_lines(capsys)
    assert "unvisited  fleet_epics_done_total  mark not reachable by --refresh" in out
    assert out[-1] == "summary   pyforge-alpha: 1 refreshed, 0 skipped"
    assert ">2 of 4<" in poster.read_text(encoding="utf-8")  # still stale, and now said out loud


def test_marks_the_check_never_reads_are_skipped_not_rewritten(root, capsys):
    body = (
        '<head><title><span data-fact="fleet_stories_done_total">4/6</span></title>\n'
        '<style>/* <span data-fact="fleet_stories_done_total">4/6</span> */</style>\n'
        '<script>var s = "<span data-fact=\'fleet_stories_done_total\'>4/6</span>";</script></head>\n'
        '<body><!-- <span data-fact="fleet_stories_done_total">4/6</span> -->\n'
        '<p><b data-fact="cli_verbs"><i data-fact="fleet_stories_done_total">4/6</i></b></p>\n'
        "</body>\n")
    poster = _stale_poster(root, body)
    out = _refresh_lines(capsys)
    assert _kind(out, "skipped") == [
        "skipped  fleet_stories_done_total  inside <title>",
        "skipped  fleet_stories_done_total  inside <style>",
        "skipped  fleet_stories_done_total  inside <script>",
        "skipped  fleet_stories_done_total  inside <comment>",
        "skipped  cli_verbs  nested mark",
        "skipped  fleet_stories_done_total  inside nested mark",
    ]
    assert not _kind(out, "refreshed")
    assert poster.read_text(encoding="utf-8") == body


def test_unclosed_and_void_marks_are_not_a_plain_span(root, capsys):
    """`nested mark` means "the span holds another tag"; a span that never closes
    and a tag with no span at all are a different thing and say so."""
    body = ('<p><span data-fact="fleet_stories_done_total">4/6</p>\n'
            '<p><img data-fact="fleet_epics_done_total"/> · '
            '<img data-fact="bmad_loop_version"> · '
            '<span data-fact="gamma_stories_done_total"/></p>\n')
    poster = _stale_poster(root, body)
    out = _refresh_lines(capsys)
    assert _kind(out, "skipped") == [
        "skipped  fleet_stories_done_total  not a plain span",
        "skipped  fleet_epics_done_total  not a plain span",
        "skipped  bmad_loop_version  not a plain span",
        "skipped  gamma_stories_done_total  not a plain span",
    ]
    assert poster.read_text(encoding="utf-8") == body


def test_entity_encoded_mark_text_is_left_to_the_author(root, capsys):
    """Rewriting would flatten the entities to plain text, changing bytes beyond
    the literal -- and a mark that already resolves stays unprinted either way."""
    body = ('<p><span data-fact="fleet_stories_done_total">&nbsp;4/6&nbsp;</span> · '
            '<span data-fact="fleet_epics_done_total">2&#32;of&#32;4</span> · '
            '<span data-fact="gamma_stories_done_total">&nbsp;2/2&nbsp;</span></p>\n')
    poster = _stale_poster(root, body)
    out = _refresh_lines(capsys)
    assert _kind(out, "skipped") == [
        "skipped  fleet_stories_done_total  entities",
        "skipped  fleet_epics_done_total  entities",
    ]
    assert not _kind(out, "refreshed")
    assert poster.read_text(encoding="utf-8") == body


def test_replacement_prefers_the_shape_over_a_reordered_shown_as_index():
    prev = {"value": "848/878", "shown_as": ["848/878", "848 of 878"]}
    fresh = {"value": "852/878", "shown_as": ["852/878", "852 done", "852 of 878"]}
    # the index alone would return `852 done`: a literal of a different shape
    assert deck_facts._replacement("848 of 878", prev, fresh) == "852 of 878"
    assert deck_facts._replacement("848/878", prev, fresh) == "852/878"


def test_a_corrupt_ledger_never_breaks_the_regeneration_command(root, capsys):
    corrupt = "facts: [\n  - id: x\n   value: 'unclosed\n"
    ledger = root / "presentations/pyforge-alpha/facts.yaml"
    _write(ledger, corrupt)
    assert deck_facts.main(["pyforge-alpha"]) == 0  # the plain run is what REPAIRS it
    assert _rows(root, "pyforge-alpha")["bmad_core_version"]["value"] == "6.12.0"

    ledger.write_text(corrupt, encoding="utf-8")
    _poster(root).write_bytes(REFRESH_POSTER.encode("utf-8"))
    capsys.readouterr()
    assert deck_facts.main(["pyforge-alpha", "--refresh"]) == 0  # simply no previous ledger
    assert "facts.yaml is not valid YAML -- treated as no previous ledger" in capsys.readouterr().err


def test_a_non_utf8_poster_is_skipped_not_a_traceback(root, capsys):
    poster = _poster(root)
    poster.write_bytes(b'<p><span data-fact="fleet_stories_done_total">4/6 \xff\xfe</span></p>\n')
    before = poster.read_bytes()
    capsys.readouterr()
    assert deck_facts.main(["pyforge-alpha", "--refresh"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert "skipped poster: not UTF-8" in out
    assert out[-1] == "summary   pyforge-alpha: 0 refreshed, 0 skipped"
    assert poster.read_bytes() == before
    assert (root / "presentations/pyforge-alpha/facts.yaml").is_file()


def test_refresh_reads_the_poster_before_it_advances_the_ledger(root, monkeypatch):
    """A ledger written past an unreadable poster would leave the poster stale with
    nothing left to compare it against."""
    ghost = root / "presentations/pyforge-alpha/project/Ghost Infographic standalone.html"
    monkeypatch.setattr(deck_facts, "poster_hits", lambda r, slug: [ghost])
    with pytest.raises(OSError):
        deck_facts.main(["pyforge-alpha", "--refresh"])
    assert not (root / "presentations/pyforge-alpha/facts.yaml").exists()


def test_refresh_with_no_previous_ledger_rewrites_by_shape(root, capsys):
    poster = _poster(root)
    original = ('<p>fleet <SPAN data-fact="fleet_stories_done_total">1/6</SPAN> · '
                "<span data-fact='fleet_epics_done_total'>1 of 4</span> · "
                '<em data-fact="bmad_loop_version">v0.9.9</em></p>\r\n')
    poster.write_bytes(original.encode("utf-8"))
    assert not (root / "presentations/pyforge-alpha/facts.yaml").exists()  # the `previous or {}` guard
    out = _refresh_lines(capsys)
    assert out[0].startswith("pyforge-alpha: wrote")
    assert out[1] == "poster: presentations/pyforge-alpha/project/Alpha Infographic standalone.html"
    assert _kind(out, "refreshed") == [
        'refreshed  fleet_stories_done_total  "1/6" -> "4/6"',      # uppercase <SPAN>
        'refreshed  fleet_epics_done_total  "1 of 4" -> "2 of 4"',  # single-quoted id, shape kept
        'refreshed  bmad_loop_version  "v0.9.9" -> "v0.11.1"',
    ]
    assert poster.read_bytes() == (original.replace(">1/6<", ">4/6<").replace(">1 of 4<", ">2 of 4<")
                                   .replace(">v0.9.9<", ">v0.11.1<")).encode("utf-8")
    assert not list((root / "presentations/pyforge-alpha/project").glob("*.tmp"))  # temp file + os.replace


# --- Story 21.3 (spec-deck-family-lockstep CAP-2): both verbs now walk every
# MARKED surface of the deck -- poster, head, Infographic Deck, exec summary,
# and the three marp sources -- not the poster alone. A surface only enters the
# walk once it exists AND already carries at least one `data-fact` occurrence;
# a deck where nothing but the poster is marked (the whole fleet, as of this
# story) is provably unaffected -- every test above this comment passes with
# zero changes, and `test_extra_surfaces_with_no_marks_behave_exactly_as_today`
# pins it explicitly.

def test_discover_surfaces_gates_optional_surfaces_on_marks(root):
    project = root / "presentations/pyforge-alpha/project"
    _write(project / "Alpha - Infographic.dc.html", "<p>82/94 no marks at all here</p>")
    _write(project / "Alpha - Infographic Deck.dc.html", '<p data-fact="stories_done_total">2/3</p>')
    notes: list[str] = []
    names = [n for n, _ in deck_facts.discover_surfaces(root, "pyforge-alpha", notes)]
    assert names == ["poster", "infographic-deck"]  # head unmarked -> excluded; poster always present
    assert notes == []


def test_discover_surfaces_reports_the_poster_slot_even_when_missing(root):
    notes: list[str] = []
    assert deck_facts.discover_surfaces(root, "pyforge-beta", notes) == [("poster", None)]


def test_discover_surfaces_marp_date_glob_skips_the_narration_sibling(root):
    """A real fleet sibling: `<slug>-infographic-deck-narration-<date>.md` starts
    with the same `<slug>-infographic-` prefix as the genuine source and sorts
    after it by date -- deck_export.py's own looser glob would pick it as
    "newest". The date must anchor immediately after the kind."""
    marp = root / "presentations/pyforge-alpha/src/marp"
    _write(marp / "pyforge-alpha-infographic-2026-07-24.md", '<p data-fact="x">1</p>')
    _write(marp / "pyforge-alpha-infographic-deck-narration-2026-07-31.md", '<p data-fact="x">1</p>')
    notes: list[str] = []
    surfaces = dict(deck_facts.discover_surfaces(root, "pyforge-alpha", notes))
    assert surfaces["marp-infographic"].name == "pyforge-alpha-infographic-2026-07-24.md"


def test_discover_surfaces_picks_the_newest_dated_marp_source(root):
    marp = root / "presentations/pyforge-alpha/src/marp"
    _write(marp / "pyforge-alpha-infographic-2026-07-24.md", '<p data-fact="x">1</p>')
    _write(marp / "pyforge-alpha-infographic-2026-08-31.md", '<p data-fact="x">1</p>')
    notes: list[str] = []
    surfaces = dict(deck_facts.discover_surfaces(root, "pyforge-alpha", notes))
    assert surfaces["marp-infographic"].name == "pyforge-alpha-infographic-2026-08-31.md"


def test_discover_surfaces_names_ambiguous_suffix_matches(root):
    project = root / "presentations/pyforge-alpha/project"
    _write(project / "Alpha - Executive Summary.dc.html", '<p data-fact="x">1</p>')
    _write(project / "Zeta - Executive Summary.dc.html", '<p data-fact="x">1</p>')
    notes: list[str] = []
    surfaces = dict(deck_facts.discover_surfaces(root, "pyforge-alpha", notes))
    assert any("multiple matches" in n and "Executive Summary" in n for n in notes)
    # the tie-break itself, not just the stderr note: sorted-first, matching
    # poster_hits'/derive's own precedent (test_multiple_posters_are_named_and_the_first_is_used)
    assert surfaces["exec-summary"].name == "Alpha - Executive Summary.dc.html"


def test_check_names_the_surface_and_a_clean_surface_is_silent(root, capsys):
    project = root / "presentations/pyforge-alpha/project"
    # fleet_epics_done_total resolves cleanly on the poster already ("2 / 4");
    # planting a stale mark on head isolates a mismatch to that surface alone.
    _write(project / "Alpha - Infographic.dc.html",
           '<p>epics <span data-fact="fleet_epics_done_total">9 / 9</span></p>')
    _write(project / "Alpha - Infographic Deck.dc.html", "<p>no marks here, just 1/2 prose</p>")
    deck_facts.main(["pyforge-alpha"])
    out = _check_lines(capsys, "pyforge-alpha")
    assert "head: presentations/pyforge-alpha/project/Alpha - Infographic.dc.html" in out
    assert not any(l.startswith("infographic-deck:") for l in out)  # unmarked: never walked
    head_mismatch = [l for l in _kind(out, "mismatch") if "fleet_epics_done_total" in l and '"9/9"' in l]
    assert len(head_mismatch) == 1
    assert not any("1/2" in l for l in _kind(out, "unmarked"))  # the unmarked surface was never swept


def test_check_prints_no_header_for_a_marked_but_fully_clean_surface(root, capsys):
    project = root / "presentations/pyforge-alpha/project"
    _write(project / "Alpha - Executive Summary.dc.html",
           '<p>epics <span data-fact="fleet_epics_done_total">2/4</span></p>')  # already resolves
    deck_facts.main(["pyforge-alpha"])
    out = _check_lines(capsys, "pyforge-alpha")
    assert not any(l.startswith("exec-summary:") for l in out)


def test_unshown_aggregates_across_every_walked_surface(root, capsys):
    """`package_version` ("0.1.0") appears nowhere in the poster fixture and is
    `unshown` there alone; marking it correctly on another surface must clear it
    deck-wide, since `unshown` asks whether ANY walked surface shows the value."""
    project = root / "presentations/pyforge-alpha/project"
    deck_facts.main(["pyforge-alpha"])
    baseline = _check_lines(capsys, "pyforge-alpha")
    assert "package_version" in {l.split()[1] for l in _kind(baseline, "unshown")}
    _write(project / "Alpha - Executive Summary.dc.html",
           '<p>version <span data-fact="package_version">0.1.0</span></p>')
    out = _check_lines(capsys, "pyforge-alpha")
    assert "package_version" not in {l.split()[1] for l in _kind(out, "unshown")}


def test_extra_surfaces_with_no_marks_behave_exactly_as_today(root, capsys):
    """The AC's own wording: a deck whose extra surfaces carry no marks behaves
    exactly as today. Real content, real files, zero `data-fact` anywhere in
    them -- output must be byte-identical to the poster-only baseline."""
    project = root / "presentations/pyforge-alpha/project"
    marp = root / "presentations/pyforge-alpha/src/marp"
    extras = {
        project / "Alpha - Infographic.dc.html": "<p>82/94 completely unmarked prose</p>",
        project / "Alpha - Infographic Deck.dc.html": "<p>more unmarked prose, 2026-01-01</p>",
        project / "Alpha - Executive Summary.dc.html": "<p>yet more, v1.2.3</p>",
        marp / "pyforge-alpha-deck-2026-07-24.md": "# unmarked deck\n",
    }
    for path, text in extras.items():
        _write(path, text)
    deck_facts.main(["pyforge-alpha"])
    with_extras = _check_lines(capsys, "pyforge-alpha")
    for path in extras:
        path.unlink()
    without_extras = _check_lines(capsys, "pyforge-alpha")
    assert with_extras == without_extras


def test_refresh_rewrites_every_marked_surface_and_sums_the_summary(root, stale, capsys):
    project = root / "presentations/pyforge-alpha/project"
    _write(project / "Alpha - Infographic.dc.html",
           '<p>fleet <span data-fact="fleet_stories_done_total">4/6</span></p>')
    out = _refresh_lines(capsys)
    assert "head: presentations/pyforge-alpha/project/Alpha - Infographic.dc.html" in out
    assert 'refreshed  fleet_stories_done_total  "4/6" -> "5/6"' in _kind(out, "refreshed")
    # 4 refreshed + 2 skipped from the poster (base fixture) + 1 refreshed from head
    assert out[-1] == "summary   pyforge-alpha: 5 refreshed, 2 skipped"
    assert (project / "Alpha - Infographic.dc.html").read_text(encoding="utf-8") == (
        '<p>fleet <span data-fact="fleet_stories_done_total">5/6</span></p>')


def test_refresh_never_touches_an_unmarked_surface(root, stale, capsys):
    project = root / "presentations/pyforge-alpha/project"
    deck_path = project / "Alpha - Infographic Deck.dc.html"
    _write(deck_path, "<p>no marks here, just 1/2 prose</p>")
    before = deck_path.read_bytes()
    before_mtime = deck_path.stat().st_mtime_ns
    out = _refresh_lines(capsys)
    assert not any(l.startswith("infographic-deck:") for l in out)
    assert deck_path.read_bytes() == before
    assert deck_path.stat().st_mtime_ns == before_mtime


def test_refresh_reads_every_marked_surface_before_it_advances_the_ledger(root, monkeypatch):
    """The poster-only invariant (`test_refresh_reads_the_poster_before_it_advances_the_ledger`),
    generalized: an unreadable NON-poster marked surface must equally abort
    before the ledger is written, leaving nothing stale with no comparison left."""
    ghost = root / "presentations/pyforge-alpha/project/Ghost - Infographic.dc.html"
    real_suffix_hit = deck_facts._suffix_hit
    monkeypatch.setattr(
        deck_facts, "_suffix_hit",
        lambda project, suffix, notes: ghost if suffix == deck_facts.HEAD_SUFFIX
        else real_suffix_hit(project, suffix, notes))
    monkeypatch.setattr(deck_facts, "_has_marks", lambda path: True)
    with pytest.raises(OSError):
        deck_facts.main(["pyforge-alpha", "--refresh"])
    assert not (root / "presentations/pyforge-alpha/facts.yaml").exists()


def test_check_reports_non_utf8_on_a_non_poster_surface_instead_of_crashing(root, capsys):
    """`_check_surface` reads with the same undefended `encoding="utf-8"` the
    poster always has, but --check now walks MORE files than just the poster --
    a marked non-UTF-8 head must be reported and skipped, not raise out of an
    advisory tool that promises exit 0 always."""
    project = root / "presentations/pyforge-alpha/project"
    (project / "Alpha - Infographic.dc.html").write_bytes(
        b'<p><span data-fact="fleet_epics_done_total">9 / 9 \xff\xfe</span></p>\n')
    deck_facts.main(["pyforge-alpha"])
    out = _check_lines(capsys, "pyforge-alpha")
    assert "skipped head: not UTF-8" in out
    assert not any("fleet_epics_done_total" in l for l in _kind(out, "mismatch"))
    assert out[-1].startswith("summary")  # advisory: reaches the end, never raises


def test_refresh_skip_reasons_apply_on_a_non_poster_surface(root, stale, capsys):
    """The skip machinery (`refresh()`, unchanged) is exercised on the poster
    extensively elsewhere; this pins that the SAME reasons fire when the
    surface is something other than the poster, since Story 21.3's own AC says
    they "apply per surface"."""
    project = root / "presentations/pyforge-alpha/project"
    _write(project / "Alpha - Infographic.dc.html",
           '<p><b data-fact="cli_verbs"><i>1</i></b> · '
           '<span data-fact="fleet_stories_done_total">4/6</span></p>')
    out = _refresh_lines(capsys)
    assert "skipped  cli_verbs  nested mark" in _kind(out, "skipped")
    assert 'refreshed  fleet_stories_done_total  "4/6" -> "5/6"' in _kind(out, "refreshed")


def test_unvisited_cross_check_applies_on_a_non_poster_surface(root, monkeypatch, capsys):
    project = root / "presentations/pyforge-alpha/project"
    _write(project / "Alpha - Infographic.dc.html",
           '<p><span data-fact="fleet_stories_done_total">4/6</span> · '
           '<span data-fact="fleet_epics_done_total">2 of 4</span></p>')
    deck_facts.main(["pyforge-alpha"])
    _write(
        root / "_bmad-output/projects/pyforge-gamma/planning-artifacts/sprint-status-ledger.yaml",
        GAMMA_LEDGER.replace("1-2-g: backlog", "1-2-g: done").replace("epic-1: backlog", "epic-1: done"))
    real = deck_facts._mark_spans
    monkeypatch.setattr(deck_facts, "_mark_spans",
                        lambda text: [m for m in real(text) if m["id"] != "fleet_epics_done_total"])
    out = _refresh_lines(capsys)
    assert "unvisited  fleet_epics_done_total  mark not reachable by --refresh" in out


# --- DW-FU-20-2: the collect-count regex against REAL pytest output ---------
#
# The suite above stubs `tests_collected` wholesale, so `_PYTEST_COLLECTED` and
# the reversed-line scan had only ever run against synthetic strings. That is
# the whole of DW-FU-20-2: the plumbing was proven, the parse was not, and a
# pytest release changing its summary line would have gone unnoticed until a
# deck silently lost its test-count row (`tests_collected` returns None on no
# match, and the row is advisory).
#
# These run a REAL `pytest --collect-only -q` over a throwaway package, so they
# pin the parse against whatever pytest is actually installed. They deliberately
# do NOT shell out through `tests_command()`'s `pixi run -e pyforge-<station>`:
# that needs a provisioned station env, which would make the test skip on most
# machines -- exactly the "only the plumbing is verified" hole being closed.


def _collect_output(tmp_path: Path, n: int, deselect: bool = False) -> str:
    """Real `pytest --collect-only -q` stdout for `n` trivial tests."""
    import subprocess

    pkg = tmp_path / "realcollect"
    pkg.mkdir()
    body = "".join(
        f"def test_n{i}():\n    assert True\n\n\ndef test_slow{i}():\n    assert True\n\n\n"
        if deselect else f"def test_n{i}():\n    assert True\n\n\n"
        for i in range(n)
    )
    if deselect:
        (pkg / "conftest.py").write_text(
            "import pytest\n\n\n"
            "def pytest_collection_modifyitems(config, items):\n"
            "    keep, drop = [], []\n"
            "    for it in items:\n"
            "        (drop if 'slow' in it.name else keep).append(it)\n"
            "    if drop:\n"
            "        config.hook.pytest_deselected(items=drop)\n"
            "        items[:] = keep\n",
            encoding="utf-8",
        )
    (pkg / "test_real.py").write_text(body, encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider", str(pkg)],
        capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return proc.stdout


def test_collected_regex_matches_real_pytest_summary(tmp_path):
    """The plain `N tests collected` form, parsed from real pytest stdout."""
    out = _collect_output(tmp_path, 3)
    assert "collected" in out, out
    hit = None
    for line in reversed(out.splitlines()):          # the function's own scan order
        m = deck_facts._PYTEST_COLLECTED.search(line)
        if m:
            hit = m.group(1)
            break
    assert hit == "3", f"regex did not parse real pytest output:\n{out}"


def test_collected_regex_matches_real_deselected_summary(tmp_path):
    """The `N/M tests collected` form pytest emits once anything is deselected.

    `(?:/\\d+)?` exists for exactly this, and the group must capture the
    SELECTED count (the left number), not the total.
    """
    out = _collect_output(tmp_path, 3, deselect=True)
    hit = None
    for line in reversed(out.splitlines()):
        m = deck_facts._PYTEST_COLLECTED.search(line)
        if m:
            hit = m.group(1)
            break
    assert hit == "3", f"expected the selected count from real output:\n{out}"


def test_collected_scan_is_reversed_so_a_later_summary_wins(tmp_path):
    """Real stdout lists every test id before the summary, so a forward scan
    could match a digit in a node id. The function scans in reverse; this pins
    that the summary line is what is read, not the first line containing a
    number."""
    out = _collect_output(tmp_path, 2)
    lines = out.splitlines()
    summary_idx = max(
        i for i, line in enumerate(lines) if deck_facts._PYTEST_COLLECTED.search(line)
    )
    assert summary_idx > 0, f"summary was the first line; fixture too small:\n{out}"
    assert deck_facts._PYTEST_COLLECTED.search(lines[summary_idx]).group(1) == "2"
