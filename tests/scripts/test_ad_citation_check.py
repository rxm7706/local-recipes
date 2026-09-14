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
