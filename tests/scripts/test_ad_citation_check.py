"""Story 43.1 (spec-fleet-consistency-standard CAP-6, DW-AD-CITATION-2026-09-14-2):
the citation detector shows everything it knows.

Two defects, both found live on 2026-09-14 when `detectors-ci` was red on
`origin/main`:

* `main()` printed at most ten NEW rows per class (`new[:10]`, `cap_new[:10]`)
  under a headline carrying the full count, so a red with 4 + 57 NEW findings
  was read from the printed rows and recorded as 14. The NEW set is the
  actionable set; a detector that exits 1 must show what it exits on.
* `--write-baseline` / `--write-cap-baseline` stamped `recorded:` with two
  hard-coded literals, so every later re-stamp still claimed 2026-09-08 /
  2026-09-10.

The fixture is a minimal conformant project: one spine whose folder names the
project (`architecture-<project>-<date>`, the rule the detector itself
enforces) defining `AD-1` in canonical form, one SPEC.md defining `CAP-1`,
and N files each citing a distinct undefined id. Nothing in the real repo is
read: `PROJECTS` and both baseline paths are monkeypatched into `tmp_path`.
"""

from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import ad_citation_check as m  # noqa: E402  (sys.path must be set up first)


def _project(tmp_path: Path, n_ad: int, n_cap: int) -> Path:
    """A project with exactly ``n_ad`` bare undefined AD citations and
    ``n_cap`` bare undefined CAP citations, one per file, plus one defined
    id of each kind so the project is not degenerate."""
    proj = tmp_path / "_bmad-output" / "projects" / "pyforge-fixture"
    pa = proj / "planning-artifacts"
    spine_dir = pa / "architecture" / "architecture-pyforge-fixture-2026-01-01"
    spine_dir.mkdir(parents=True)
    (spine_dir / "ARCHITECTURE-SPINE.md").write_text(
        "# Spine\n\n### AD-1 — The one defined decision\n\nBody.\n", encoding="utf-8"
    )
    spec_dir = pa / "specs" / "spec-fixture"
    spec_dir.mkdir(parents=True)
    (spec_dir / "SPEC.md").write_text(
        "---\nstatus: ready\n---\n\n## Capabilities\n\n- **CAP-1 — the one defined capability.**\n\n"
        "## Constraints\n\nNone.\n",
        encoding="utf-8",
    )
    notes = pa / "notes"
    notes.mkdir()
    # Ids start well above anything the fixture defines; each file cites one.
    for i in range(n_ad):
        (notes / f"ad-{i:02d}.md").write_text(f"This note cites AD-{50 + i} bare.\n", encoding="utf-8")
    for i in range(n_cap):
        (notes / f"cap-{i:02d}.md").write_text(f"This note cites CAP-{50 + i} bare.\n", encoding="utf-8")
    return proj


@pytest.fixture
def isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    proj = _project(tmp_path, n_ad=13, n_cap=17)
    monkeypatch.setattr(m, "ROOT", tmp_path)  # finding messages are ROOT-relative
    monkeypatch.setattr(m, "PROJECTS", proj.parent)
    monkeypatch.setattr(m, "_BASELINE_PATH", tmp_path / ".ad-citation-baseline.json")
    monkeypatch.setattr(m, "_CAP_BASELINE_PATH", tmp_path / ".cap-citation-baseline.json")
    monkeypatch.setattr(sys, "argv", ["ad_citation_check.py"])
    return tmp_path


def test_every_new_row_is_printed_not_just_the_first_ten(isolated: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = m.main()
    out = capsys.readouterr().out.splitlines()

    ad_rows = [l for l in out if l.startswith("[ad-citation]   NEW: ")]
    cap_rows = [l for l in out if l.startswith("[cap-citation]   NEW: ")]

    assert rc == 1
    # The headline and the rows must agree: 13 and 17 are both past the old
    # `[:10]` slice, so the pre-fix detector printed 10 + 10 here.
    assert "[ad-citation] 13 NEW issue(s), not in the baseline:" in out
    assert "[cap-citation] 17 NEW issue(s), not in the baseline:" in out
    assert len(ad_rows) == 13
    assert len(cap_rows) == 17
    # Every cited id appears exactly once -- the rows are the real findings,
    # deduplicated per (file, id), not a padded or repeated list.
    assert sorted(int(l.split("bare AD-")[1].split(",")[0]) for l in ad_rows) == list(range(50, 63))
    assert sorted(int(l.split("bare CAP-")[1].split(",")[0]) for l in cap_rows) == list(range(50, 67))


def test_baseline_stamps_carry_the_stamping_date(isolated: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    today = datetime.date.today().isoformat()

    monkeypatch.setattr(sys, "argv", ["ad_citation_check.py", "--write-baseline"])
    assert m.main() == 0
    ad = json.loads((isolated / ".ad-citation-baseline.json").read_text(encoding="utf-8"))
    assert ad["recorded"] == today
    assert len(ad["known"]) == 13

    monkeypatch.setattr(sys, "argv", ["ad_citation_check.py", "--write-cap-baseline"])
    assert m.main() == 0
    cap = json.loads((isolated / ".cap-citation-baseline.json").read_text(encoding="utf-8"))
    assert cap["recorded"] == today
    assert len(cap["known"]) == 17

    # The ratchet is unchanged by the fix: with both baselines written, the
    # same tree is green and prints no NEW rows at all.
    capsys.readouterr()
    monkeypatch.setattr(sys, "argv", ["ad_citation_check.py"])
    assert m.main() == 0
    out = capsys.readouterr().out
    assert "NEW:" not in out
    assert "[ad-citation] ok: no new issues" in out
    assert "[cap-citation] ok: no new issues" in out


def test_a_baselined_subset_still_prints_every_remaining_new_row(isolated: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Baseline the first three CAP findings by hand; the other fourteen must
    all still print -- the count and the rows agree at every size, not only
    at zero and at everything."""
    monkeypatch.setattr(sys, "argv", ["ad_citation_check.py", "--write-cap-baseline"])
    assert m.main() == 0
    path = isolated / ".cap-citation-baseline.json"
    full = json.loads(path.read_text(encoding="utf-8"))
    path.write_text(json.dumps({"recorded": full["recorded"], "known": full["known"][:3]}), encoding="utf-8")
    capsys.readouterr()

    monkeypatch.setattr(sys, "argv", ["ad_citation_check.py"])
    rc = m.main()
    out = capsys.readouterr().out.splitlines()
    cap_rows = [l for l in out if l.startswith("[cap-citation]   NEW: ")]

    assert rc == 1
    assert "[cap-citation] 14 NEW issue(s), not in the baseline:" in out
    assert len(cap_rows) == 14


# --- marshal Story 123.1: station source is held to the same rule as planning prose -------------------------------


def _source(tmp_path: Path, package: str, name: str, text: str) -> Path:
    path = tmp_path / "src" / "shared" / "packages" / package / "src" / "pyforge" / "fixture" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def clean(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The fixture project with no broken planning citation, a spine that also defines the qualified
    ``suite:AD-9`` and ``canopy:AD-14``, and a second project, so only source findings show."""
    proj = _project(tmp_path, n_ad=0, n_cap=0)
    spine = next(proj.glob("planning-artifacts/architecture/*/ARCHITECTURE-SPINE.md"))
    spine.write_text(
        spine.read_text(encoding="utf-8") + "\n#### suite:AD-9 — A satellite decision\n\n#### canopy:AD-14 — Another\n",
        encoding="utf-8",
    )
    other = proj.parent / "pyforge-other" / "planning-artifacts" / "architecture" / "architecture-pyforge-other-2026-01-01"
    other.mkdir(parents=True)
    (other / "ARCHITECTURE-SPINE.md").write_text("# Spine\n\n### AD-24 — The other project's decision\n", encoding="utf-8")
    monkeypatch.setattr(m, "ROOT", tmp_path)
    monkeypatch.setattr(m, "PROJECTS", proj.parent)
    monkeypatch.setattr(m, "_BASELINE_PATH", tmp_path / ".ad-citation-baseline.json")
    monkeypatch.setattr(m, "_CAP_BASELINE_PATH", tmp_path / ".cap-citation-baseline.json")
    monkeypatch.setattr(sys, "argv", ["ad_citation_check.py"])
    return tmp_path


def test_a_bare_tag_in_station_source_that_its_own_spine_lacks_is_a_finding(
    clean: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _source(clean, "pyforge-fixture", "ok.py", "# AD-1 is this station's own decision\n")
    _source(clean, "pyforge-fixture", "bad.py", "# the AD-9 module roster is another spine's\n")
    assert m.main() == 1
    out = capsys.readouterr().out
    assert "SOURCE: pyforge-fixture: src/shared/packages/pyforge-fixture/src/pyforge/fixture/bad.py cites bare AD-9" in out
    assert "ok.py" not in out


def test_a_qualified_tag_that_resolves_is_not_a_finding(clean: Path) -> None:
    _source(
        clean,
        "pyforge-fixture",
        "qualified.py",
        "# suite:AD-9 by colon, canopy AD-14 by space, pyforge-other:AD-24 by project,\n"
        "# spec-pyforge-fixture:AD-1 by the station Spec's name\n",
    )
    assert m.main() == 0


@pytest.mark.parametrize(
    ("line", "named"),
    [
        ("# suit:AD-9 is a typo of the prefix\n", "cites suit:AD-9, and no spine is named `suit`"),
        ("# suite:AD-99 is an id that spine lacks\n", "cites suite:AD-99, which `suite` does not define"),
        ("# pyforge-other:AD-7 is an id that project lacks\n", "cites pyforge-other:AD-7, which `pyforge-other` does not define"),
        ("# canopy AD-15 is an id the canopy lacks\n", "cites canopy:AD-15, which `canopy` does not define"),
    ],
)
def test_a_qualified_tag_that_does_not_resolve_is_a_finding(
    clean: Path, capsys: pytest.CaptureFixture[str], line: str, named: str
) -> None:
    _source(clean, "pyforge-fixture", "wrong.py", line)
    assert m.main() == 1
    assert named in capsys.readouterr().out


@pytest.mark.parametrize(
    "line",
    ["# the roster AD-9 names is another spine's\n", "# the test suite AD-9 must not read as qualified\n", "# Canopy AD-9\n"],
)
def test_a_word_before_a_tag_is_not_a_qualifier(clean: Path, capsys: pytest.CaptureFixture[str], line: str) -> None:
    _source(clean, "pyforge-fixture", "prose.py", line)
    assert m.main() == 1
    assert "prose.py cites bare AD-9" in capsys.readouterr().out


def test_a_source_finding_is_never_absolved_by_the_baseline(
    clean: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``--write-baseline`` records prose debt only: a source finding still fails on the next run."""
    _source(clean, "pyforge-fixture", "bad.py", "# AD-9 is another spine's\n")
    monkeypatch.setattr(sys, "argv", ["ad_citation_check.py", "--write-baseline"])
    assert m.main() == 0
    assert json.loads((clean / ".ad-citation-baseline.json").read_text(encoding="utf-8"))["known"] == []
    monkeypatch.setattr(sys, "argv", ["ad_citation_check.py"])
    capsys.readouterr()
    assert m.main() == 1
    assert "bad.py cites bare AD-9" in capsys.readouterr().out


def test_a_kernel_package_is_held_to_its_home_projects_spine(
    clean: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """``pyforge-core`` has no project of its own; ``_SOURCE_HOME`` names the project its Spec lives in."""
    monkeypatch.setattr(m, "_SOURCE_HOME", {"pyforge-core": "pyforge-fixture"})
    _source(clean, "pyforge-core", "home.py", "# AD-1 resolves in the home project; AD-7 does not\n")
    assert m.main() == 1
    out = capsys.readouterr().out
    assert "home.py cites bare AD-7" in out and "AD-1," not in out


def test_a_package_with_no_home_project_is_a_finding_and_tests_are_not_scanned(
    clean: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    tests = clean / "src" / "shared" / "packages" / "pyforge-fixture" / "tests" / "test_x.py"
    tests.parent.mkdir(parents=True)
    tests.write_text("# a fixture may quote AD-99\n", encoding="utf-8")
    assert m.main() == 0
    _source(clean, "pyforge-orphan", "x.py", "# anything\n")
    assert m.main() == 1
    assert "pyforge-orphan: no project `pyforge-orphan`" in capsys.readouterr().out


def test_the_two_kernel_packages_are_homed_in_marshals_project() -> None:
    assert m._SOURCE_HOME == {"pyforge-core": "pyforge-marshal", "pyforge-testing-kit": "pyforge-marshal"}


def test_the_committed_baseline_holds_no_source_row() -> None:
    known = json.loads((REPO_ROOT / "scripts" / ".ad-citation-baseline.json").read_text(encoding="utf-8"))["known"]
    assert [row for row in known if "src/shared/packages" in row] == []
