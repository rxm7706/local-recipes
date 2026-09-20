"""Doctor Epic 25 -- chain-sprawl (25.1), fr-without-cap (25.2), and the
re-key map parser both share with ledger-regression / story-status (25.3).

Fixtures build a tiny planning tree under ``tmp_path``; the live-tree tests
at the bottom run the two gathers on this checkout and pin that neither
FAILs at the ruling snapshot (the conformance leg each story names).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyforge.doctor import rekey
from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import one_chain

try:
    _REPO_ROOT: Path | None = Path(__file__).resolve().parents[6]
except IndexError:
    _REPO_ROOT = None


def _live_root() -> Path:
    if _REPO_ROOT is None or not (_REPO_ROOT / ".claude").is_dir():
        pytest.skip("live repo root not resolvable from this checkout")
    return _REPO_ROOT


# --- fixture tree ------------------------------------------------------------

_STATIONS = ["herald", "marshal", "atlas", "warden", "mason", "doctor", "scribe", "steward"]


def _roster(root: Path, *, exemptions: list[str] | None = ["different-owner", "governance"]) -> None:
    data: dict = {"stations": _STATIONS, "guild_dreams": []}
    if exemptions is not None:
        data["fold_exemptions"] = exemptions
    (root / "docs" / "governance").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "governance" / "guild-roster.json").write_text(json.dumps(data))


def _dream(root: Path, name: str, **fm: str) -> Path:
    (root / "docs" / "dreams").mkdir(parents=True, exist_ok=True)
    p = root / "docs" / "dreams" / f"{name}.md"
    body = "---\n" + "".join(f"{k}: {v}\n" for k, v in fm.items()) + "---\n# x\n"
    p.write_text(body)
    return p


def _spec(root: Path, project: str, folder: str, **fm: str) -> Path:
    d = root / "_bmad-output" / "projects" / project / "planning-artifacts" / "specs" / folder
    d.mkdir(parents=True, exist_ok=True)
    body = "---\n" + "".join(f"{k}: {v}\n" for k, v in fm.items()) + "---\n"
    body += fm.pop("_body", "") if "_body" in fm else ""
    (d / "SPEC.md").write_text(body)
    return d


def _baseline(root: Path) -> None:
    data = one_chain.snapshot_chain_sprawl_baseline(root, ruling_sha="abc123")
    p = root / one_chain.CHAIN_SPRAWL_BASELINE_REL
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data))


def _tree(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    _roster(root)
    _dream(root, "pyforge-marshal", owner="marshal", status="realized")
    _dream(root, "old-satellite", owner="marshal", status="specified")
    _spec(root, "pyforge-marshal", "spec-pyforge-marshal", status="ready")
    _spec(root, "pyforge-marshal", "spec-old-thing", status="ready")
    # a story spec FILE beside the folders -- must be ignored structurally
    (root / "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-1-1-x.md").write_text("x")
    _baseline(root)
    return root


def _by_check(findings) -> dict[str, list]:
    out: dict[str, list] = {}
    for f in findings:
        out.setdefault(f.check, []).append(f)
    return out


# --- 25.1 chain-sprawl -------------------------------------------------------


def test_sprawl_clean_tree_is_ok(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    (f,) = one_chain.gather_chain_sprawl(root)
    assert f.source is Source.CHAIN_SPRAWL
    assert f.check == "chain-sprawl" and f.status is DoctorStatus.OK
    assert f.evidence["ruling_sha"] == "abc123"


def test_sprawl_new_dream_without_exemption_fails(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    _dream(root, "brand-new", owner="marshal", status="dreamt")
    by = _by_check(one_chain.gather_chain_sprawl(root))
    (f,) = by["chain-sprawl-unexempted"]
    assert f.status is DoctorStatus.FAIL
    assert f.evidence["path"] == "docs/dreams/brand-new.md"
    assert f.evidence["reason"] == "no fold-exemption"
    assert "docs/dreams/pyforge-marshal.md" in f.evidence["station_dreams"]


def test_sprawl_new_spec_folder_with_listed_value_is_visible_ok(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    _spec(root, "pyforge-marshal", "spec-seam", status="ready", **{"fold-exemption": "governance"})
    by = _by_check(one_chain.gather_chain_sprawl(root))
    assert "chain-sprawl-unexempted" not in by
    (f,) = by["chain-sprawl-exempt"]
    assert f.status is DoctorStatus.OK and f.evidence["fold_exemption"] == "governance"


def test_sprawl_unlisted_value_fails(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    _dream(root, "brand-new", owner="marshal", status="dreamt", **{"fold-exemption": "because"})
    by = _by_check(one_chain.gather_chain_sprawl(root))
    (f,) = by["chain-sprawl-unexempted"]
    assert "value not in" in f.evidence["reason"]


def test_sprawl_station_dream_and_station_spec_and_story_file_are_excluded(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    # remove them from the baseline to prove the exclusion is structural
    p = root / one_chain.CHAIN_SPRAWL_BASELINE_REL
    data = json.loads(p.read_text())
    assert "docs/dreams/pyforge-marshal.md" not in data["dreams"]
    assert not any(x.endswith("spec-pyforge-marshal") for x in data["spec_folders"])
    assert not any(x.endswith(".md") for x in data["spec_folders"])
    _dream(root, "pyforge-doctor", owner="doctor", status="realized")  # a station Dream, not in baseline
    _spec(root, "pyforge-doctor", "spec-pyforge-doctor", status="ready")
    (f,) = one_chain.gather_chain_sprawl(root)
    assert f.check == "chain-sprawl" and f.status is DoctorStatus.OK


def test_sprawl_missing_baseline_is_warn_not_fail(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    (root / one_chain.CHAIN_SPRAWL_BASELINE_REL).unlink()
    (f,) = one_chain.gather_chain_sprawl(root)
    assert f.check == "chain-sprawl-no-baseline" and f.status is DoctorStatus.WARN


def test_sprawl_exemption_list_comes_from_roster_only(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    _roster(root, exemptions=None)
    (f,) = one_chain.gather_chain_sprawl(root)
    assert f.check == "chain-sprawl-no-vocabulary" and f.status is DoctorStatus.WARN
    # and the module holds no list of its own
    src = Path(one_chain.__file__).read_text()
    for value in ("different-owner", "different-lifecycle", "cross-station-seam"):
        assert f'"{value}"' not in src, f"{value} hard-coded in one_chain.py"


def test_sprawl_prune_only_removes(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    (root / "docs/dreams/old-satellite.md").unlink()
    _dream(root, "brand-new", owner="marshal", status="dreamt")
    data, removed = one_chain.prune_chain_sprawl_baseline(root)
    assert removed == ["docs/dreams/old-satellite.md"]
    assert data is not None and "docs/dreams/brand-new.md" not in data["dreams"]


# --- 25.2 fr-without-cap -----------------------------------------------------


def _prd(root: Path, project: str, text: str) -> Path:
    d = root / "_bmad-output" / "projects" / project / "planning-artifacts" / "prds" / f"prd-{project}-2026-01-01"
    d.mkdir(parents=True, exist_ok=True)
    p = d / "prd.md"
    p.write_text(text)
    return p


def _fr_baseline(root: Path) -> None:
    data = one_chain.snapshot_fr_baseline(root, ruling_sha="abc123")
    p = root / one_chain.FR_BASELINE_REL
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data))


def _fr_tree(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    _roster(root)
    d = _spec(root, "pyforge-marshal", "spec-pyforge-marshal", status="ready")
    (d / "SPEC.md").write_text("---\nstatus: ready\n---\n- **CAP-1 — a.**\n- **CAP-2 — b.**\n")
    d2 = _spec(root, "pyforge-marshal", "spec-closed", status="archived")
    (d2 / "SPEC.md").write_text("---\nstatus: archived\n---\n- **CAP-99 — gone.**\n")
    _prd(root, "pyforge-marshal", "## FR-1: old thing\nno citation, pre-rule\n")
    _fr_baseline(root)
    return root


def test_fr_pre_rule_population_is_never_a_finding(tmp_path: Path) -> None:
    root = _fr_tree(tmp_path)
    (f,) = one_chain.gather_fr_without_cap(root)
    assert f.check == "fr-without-cap" and f.status is DoctorStatus.OK
    assert f.evidence["new_frs"] == 0


def test_fr_new_without_citation_fails(tmp_path: Path) -> None:
    root = _fr_tree(tmp_path)
    _prd(root, "pyforge-marshal", "## FR-1: old thing\n\n## FR-2: new thing\nno cap here\n")
    by = _by_check(one_chain.gather_fr_without_cap(root))
    (f,) = by["fr-without-cap"]
    assert f.status is DoctorStatus.FAIL and f.evidence["fr"] == "FR-2"
    assert f.evidence["spec_folder"].endswith("specs/spec-pyforge-marshal/")


def test_fr_new_with_resolving_citation_same_line_or_first_body_line(tmp_path: Path) -> None:
    root = _fr_tree(tmp_path)
    _prd(root, "pyforge-marshal", "## FR-1: old\n\n## FR-2: same line ← CAP-1\n\n- **FR-3** new\n  ← CAP-2\n")
    (f,) = one_chain.gather_fr_without_cap(root)
    assert f.status is DoctorStatus.OK and f.evidence["new_frs"] == 2


def test_fr_citation_to_closed_or_absent_cap_is_unresolved(tmp_path: Path) -> None:
    root = _fr_tree(tmp_path)
    _prd(root, "pyforge-marshal", "## FR-1: old\n\n## FR-2: x ← CAP-99\n\n## FR-3: y ← CAP-7\n")
    by = _by_check(one_chain.gather_fr_without_cap(root))
    got = {f.evidence["fr"]: f.evidence["unresolved"] for f in by["fr-cap-unresolved"]}
    assert got == {"FR-2": ["CAP-99"], "FR-3": ["CAP-7"]}
    assert all(f.status is DoctorStatus.FAIL for f in by["fr-cap-unresolved"])


def test_fr_missing_baseline_is_warn(tmp_path: Path) -> None:
    root = _fr_tree(tmp_path)
    (root / one_chain.FR_BASELINE_REL).unlink()
    (f,) = one_chain.gather_fr_without_cap(root)
    assert f.check == "fr-without-cap-no-baseline" and f.status is DoctorStatus.WARN


def test_fr_rebaseline_one_project_carries_the_others(tmp_path: Path) -> None:
    root = _fr_tree(tmp_path)
    _prd(root, "pyforge-doctor", "## FR-5: doctor\n")
    existing = json.loads((root / one_chain.FR_BASELINE_REL).read_text())
    existing["projects"]["pyforge-doctor"] = ["FR-1"]  # stale on purpose
    data = one_chain.snapshot_fr_baseline(root, ruling_sha="abc123", only_project="pyforge-marshal", existing=existing)
    assert data["projects"]["pyforge-doctor"] == ["FR-1"]  # untouched
    assert data["projects"]["pyforge-marshal"] == ["FR-1"]


# --- 25.3 the re-key map parser ----------------------------------------------


def test_rekey_parse_grammar() -> None:
    m = rekey.parse_rekey("# fold 2026-09-16\n\n46-1-a -> 12-1-a\n 46-2-b  ->  12-2-b \n")
    assert m.clean and m.mapping == {"46-1-a": "12-1-a", "46-2-b": "12-2-b"}


def test_rekey_parse_refuses_to_guess() -> None:
    m = rekey.parse_rekey("46-1-a -> 12-1-a\n46-1-a -> 13-1-a\nbogus line\n46-3-c -> 12-1-a\n")
    assert not m.clean
    assert m.duplicates == ((2, "46-1-a"),)
    assert m.malformed == ((3, "bogus line"),)
    assert m.collisions == ("12-1-a",)  # 46-1-a and 46-3-c both land on it


def test_rekey_reverse_map_resolves_chains(tmp_path: Path) -> None:
    a = rekey.parse_rekey("a -> b\n")
    b = rekey.parse_rekey("b -> c\n")
    rev = rekey.reverse_map([(tmp_path / "1.md", a), (tmp_path / "2.md", b)])
    assert rev == {"c": ("a", "b")}


def test_rekey_load_groups_by_project(tmp_path: Path) -> None:
    d = tmp_path / "_bmad-output/projects/pyforge-marshal/planning-artifacts"
    d.mkdir(parents=True)
    (d / "rekey-2026-09-20.md").write_text("46-1-a -> 1-1-a\n")
    maps = rekey.load_rekey_maps(tmp_path)
    assert list(maps) == ["pyforge-marshal"]
    assert maps["pyforge-marshal"][0][1].mapping == {"46-1-a": "1-1-a"}


# --- live tree (conformance legs) --------------------------------------------


def test_live_tree_chain_sprawl_has_no_fail_at_ruling_snapshot() -> None:
    root = _live_root()
    findings = one_chain.gather_chain_sprawl(root)
    fails = [f for f in findings if f.status is DoctorStatus.FAIL]
    assert not fails, [f.message for f in fails]
    assert not any(f.check == "chain-sprawl-no-baseline" for f in findings)


def test_live_tree_fr_without_cap_has_no_fail_at_ruling_snapshot() -> None:
    root = _live_root()
    findings = one_chain.gather_fr_without_cap(root)
    fails = [f for f in findings if f.status is DoctorStatus.FAIL]
    assert not fails, [f.message for f in fails]
    assert not any(f.check == "fr-without-cap-no-baseline" for f in findings)


def test_live_roster_declares_the_closed_list() -> None:
    root = _live_root()
    data = json.loads((root / "docs/governance/guild-roster.json").read_text())
    assert data["fold_exemptions"] == [
        "different-owner",
        "different-lifecycle",
        "cross-station-seam",
        "governance",
    ]
