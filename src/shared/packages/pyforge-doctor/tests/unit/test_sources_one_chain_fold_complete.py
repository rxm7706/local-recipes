"""Doctor Story 36.1 -- fold-complete (spec-one-chain-per-station CAP-11).

An archived Dream under ``archive/docs/dreams/`` must have every long
paragraph of its body in its station Dream before its file moves. Fixtures
build a tiny tree under ``tmp_path``; the live-tree tests at the bottom run
the gather and the CLI on this checkout (the "today's main" leg).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import __main__ as dispatch
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


def _para(tag: str) -> str:
    """A paragraph comfortably over the 80-character floor, unique by ``tag``."""
    return f"The {tag} paragraph is long enough to count toward a fold, because it runs well past eighty characters."


def _write(root: Path, rel: str, text: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def _dream_text(body: str, **fm: str) -> str:
    return "---\n" + "".join(f"{k}: {v}\n" for k, v in fm.items()) + "---\n" + body


def _archived(root: Path, name: str, body: str, **fm: str) -> Path:
    fm = {"owner": "mason", "status": "archived", **fm}
    return _write(root, f"archive/docs/dreams/{name}.md", _dream_text(body, **fm))


def _station(root: Path, owner: str, body: str) -> Path:
    return _write(
        root,
        f"docs/dreams/pyforge-{owner}.md",
        _dream_text(body, owner=owner, status="specified"),
    )


def _baseline(root: Path, *paths: str) -> None:
    _write(root, str(one_chain.FOLD_COMPLETE_BASELINE_REL), json.dumps({"paths": list(paths)}))


def _tree(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    _baseline(root)
    return root


def _by_check(findings) -> dict[str, list]:
    out: dict[str, list] = {}
    for f in findings:
        out.setdefault(f.check, []).append(f)
    return out


def _fails(findings) -> list:
    return [f for f in findings if f.status is DoctorStatus.FAIL]


# --- the paragraph splitter --------------------------------------------------


def test_long_paragraphs_drops_frontmatter_headings_and_short_paragraphs() -> None:
    text = _dream_text(
        f"# Title\n\nshort one\n\n{_para('first')}\n\n## Heading\n{_para('second')}\n",
        owner="mason",
    )
    assert one_chain.long_paragraphs(text) == [_para("first"), _para("second")]


def test_long_paragraphs_collapses_whitespace_and_joins_wrapped_lines() -> None:
    wrapped = "alpha   beta\ngamma\t delta\n" + "x" * 70
    (only,) = one_chain.long_paragraphs(_dream_text(wrapped, owner="mason"))
    assert only == "alpha beta gamma delta " + "x" * 70


def test_long_paragraphs_floor_is_strictly_longer_than_eighty() -> None:
    at_floor = "a" * 80
    over_floor = "b" * 81
    assert one_chain.long_paragraphs(f"{at_floor}\n\n{over_floor}\n") == [over_floor]


# --- AC 1-3: complete, incomplete, demoted -----------------------------------


def test_complete_fold_is_ok(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    _archived(root, "foo", f"# Foo\n\n{_para('one')}\n\n{_para('two')}\n")
    _station(root, "mason", f"# Mason\n\n## 2026-09-29\n\n{_para('one')}\n\n{_para('two')}\n")
    findings = one_chain.gather_fold_complete(root)
    assert not _fails(findings)
    (ok,) = _by_check(findings)["fold-complete"]
    assert ok.source is Source.FOLD_COMPLETE and ok.status is DoctorStatus.OK
    assert ok.evidence["complete"] == ["archive/docs/dreams/foo.md"]


def test_one_missing_paragraph_fails_naming_file_and_count(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    _archived(root, "foo", f"{_para('one')}\n\n{_para('two')}\n")
    _station(root, "mason", f"{_para('one')}\n")
    (f,) = _by_check(one_chain.gather_fold_complete(root))["fold-complete-incomplete"]
    assert f.status is DoctorStatus.FAIL
    assert "archive/docs/dreams/foo.md" in f.message
    assert "1 paragraph missing" in f.message
    assert f.evidence["missing"] == 1 and f.evidence["paragraphs"] == 2
    assert f.evidence["missing_excerpts"] == [_para("two")[:80]]
    assert f.evidence["station_dream"] == "docs/dreams/pyforge-mason.md"


def test_several_missing_paragraphs_are_counted_and_pluralised(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    _archived(root, "foo", "\n\n".join(_para(t) for t in ("a", "b", "c", "d", "e")))
    _station(root, "mason", _para("a"))
    (f,) = _by_check(one_chain.gather_fold_complete(root))["fold-complete-incomplete"]
    assert "4 paragraphs missing" in f.message
    assert f.evidence["missing"] == 4
    assert len(f.evidence["missing_excerpts"]) == 3  # capped


def test_a_short_paragraph_missing_from_the_station_dream_is_not_a_finding(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    _archived(root, "foo", f"{_para('one')}\n\nA short aside.\n")
    _station(root, "mason", _para("one"))
    assert not _fails(one_chain.gather_fold_complete(root))


def test_headings_one_level_deeper_still_match(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    _archived(root, "foo", f"# Foo\n\n## Part\n\n{_para('one')}\n\n### Sub\n\n{_para('two')}\n")
    _station(root, "mason", f"## Foo\n\n### Part\n\n{_para('one')}\n\n#### Sub\n\n{_para('two')}\n")
    findings = one_chain.gather_fold_complete(root)
    assert not _fails(findings)
    assert _by_check(findings)["fold-complete"][0].evidence["complete"] == ["archive/docs/dreams/foo.md"]


def test_a_paragraph_abutting_a_heading_still_matches_a_demoted_paste(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    _archived(root, "foo", f"## Part\n{_para('one')}\n")
    _station(root, "mason", f"### Part\n\n{_para('one')}\n")
    assert not _fails(one_chain.gather_fold_complete(root))


def test_whitespace_differences_between_the_two_copies_do_not_matter(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    words = _para("one").split(" ")
    _archived(root, "foo", " ".join(words) + "\n")
    _station(root, "mason", "\n".join(words[:6]) + "\n" + "   ".join(words[6:]) + "\n")
    assert not _fails(one_chain.gather_fold_complete(root))


def test_a_leftover_consolidated_into_banner_is_a_missing_paragraph(tmp_path: Path) -> None:
    banner = (
        "> Consolidated into [[pyforge-mason]] on 2026-09-17; this file is kept as the "
        "pre-fold record of the effort, not as a live Dream."
    )
    root = _tree(tmp_path)
    _archived(root, "foo", f"{banner}\n\n{_para('one')}\n")
    _station(root, "mason", _para("one"))
    (f,) = _by_check(one_chain.gather_fold_complete(root))["fold-complete-incomplete"]
    assert f.evidence["missing"] == 1


# --- AC 4-5: unreadable owner, missing station Dream -------------------------


@pytest.mark.parametrize(
    "text",
    [
        pytest.param(f"# No frontmatter at all\n\n{_para('one')}\n", id="no-frontmatter"),
        pytest.param(f"---title: Glued\nowner: mason\n---\n{_para('one')}\n", id="glued-opener"),
        pytest.param(f"---\nstatus: archived\n---\n{_para('one')}\n", id="no-owner-key"),
        pytest.param(f"---\nowner: ../secrets\n---\n{_para('one')}\n", id="owner-not-a-slug"),
    ],
)
def test_unreadable_owner_fails_naming_the_file(tmp_path: Path, text: str) -> None:
    root = _tree(tmp_path)
    _write(root, "archive/docs/dreams/foo.md", text)
    _station(root, "mason", _para("one"))
    (f,) = _by_check(one_chain.gather_fold_complete(root))["fold-complete-no-owner"]
    assert f.status is DoctorStatus.FAIL
    assert "archive/docs/dreams/foo.md" in f.message


def test_missing_station_dream_fails_naming_it(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    _archived(root, "foo", f"{_para('one')}\n", owner="atlas")
    (f,) = _by_check(one_chain.gather_fold_complete(root))["fold-complete-no-station-dream"]
    assert f.status is DoctorStatus.FAIL
    assert "archive/docs/dreams/foo.md" in f.message
    assert "docs/dreams/pyforge-atlas.md" in f.message


def test_each_archived_dream_is_judged_on_its_own(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    _archived(root, "good", _para("one"))
    _archived(root, "bad", _para("two"))
    _station(root, "mason", _para("one"))
    findings = one_chain.gather_fold_complete(root)
    (f,) = _fails(findings)
    assert "bad.md" in f.message
    assert _by_check(findings)["fold-complete"][0].evidence["complete"] == ["archive/docs/dreams/good.md"]


# --- AC 6: the archived-in-live-tree countdown -------------------------------


def test_archived_dreams_in_the_live_tree_are_one_warn_with_per_station_counts(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    _write(root, "docs/dreams/one.md", _dream_text("x\n", owner="doctor", status="archived"))
    _write(root, "docs/dreams/two.md", _dream_text("x\n", owner="herald", status="archived"))
    _write(root, "docs/dreams/live.md", _dream_text("x\n", owner="doctor", status="specified"))
    findings = one_chain.gather_fold_complete(root)
    assert not _fails(findings)
    (warn,) = [f for f in findings if f.status is DoctorStatus.WARN]
    assert warn.check == "fold-complete-archived-in-live-tree"
    assert "doctor 1, herald 1" in warn.message
    assert warn.evidence["total"] == 2
    assert warn.evidence["by_station"] == {"doctor": 1, "herald": 1}


def test_no_archived_dream_in_the_live_tree_is_no_warn(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    _write(root, "docs/dreams/live.md", _dream_text("x\n", owner="doctor", status="specified"))
    assert not [f for f in one_chain.gather_fold_complete(root) if f.status is DoctorStatus.WARN]


def test_an_ownerless_archived_dream_is_counted_under_unknown(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    _write(root, "docs/dreams/one.md", "---\nstatus: archived\n---\nx\n")
    (warn,) = [f for f in one_chain.gather_fold_complete(root) if f.status is DoctorStatus.WARN]
    assert warn.evidence["by_station"] == {"unknown": 1}


def test_unreadable_frontmatter_in_the_live_tree_is_reported_beside_the_count(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    _write(root, "docs/dreams/one.md", _dream_text("x\n", owner="doctor", status="archived"))
    _write(root, "docs/dreams/glued.md", "---title: Glued\nstatus: archived\n---\nx\n")
    (warn,) = [f for f in one_chain.gather_fold_complete(root) if f.status is DoctorStatus.WARN]
    assert warn.evidence["total"] == 1 and warn.evidence["unreadable_frontmatter"] == 1
    assert "1 more have unreadable frontmatter" in warn.message


def test_the_countdown_never_reads_docs_dreams_archive(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    _write(root, "docs/dreams/archive/old.md", _dream_text("x\n", owner="doctor", status="archived"))
    assert not [f for f in one_chain.gather_fold_complete(root) if f.status is DoctorStatus.WARN]


# --- AC 7: the baseline ------------------------------------------------------


def test_a_baselined_file_is_ok_and_never_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "repo"
    listed = "archive/docs/dreams/deckcraft.md"
    _write(root, listed, "no frontmatter, no owner: would be a FAIL if it were read\n")
    _baseline(root, listed)

    opened: list[str] = []
    real = one_chain._frontmatter_parse

    def spy(path: Path):
        opened.append(path.name)
        return real(path)

    monkeypatch.setattr(one_chain, "_frontmatter_parse", spy)
    findings = one_chain.gather_fold_complete(root)
    assert not _fails(findings)
    assert "deckcraft.md" not in opened
    (ok,) = _by_check(findings)["fold-complete"]
    assert ok.evidence["baselined"] == [listed] and ok.evidence["complete"] == []


def test_a_file_missing_from_the_baseline_is_measured(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _write(root, "archive/docs/dreams/deckcraft.md", "no owner here\n")
    _baseline(root, "archive/docs/dreams/other.md")
    assert [f.check for f in _fails(one_chain.gather_fold_complete(root))] == ["fold-complete-no-owner"]


@pytest.mark.parametrize("payload", [None, "not json", "[]", '{"paths": "archive/x.md"}'])
def test_a_missing_or_unreadable_baseline_is_a_warn_not_a_crash(tmp_path: Path, payload: str | None) -> None:
    root = tmp_path / "repo"
    _write(root, "archive/docs/dreams/foo.md", "no owner here\n")
    if payload is not None:
        _write(root, str(one_chain.FOLD_COMPLETE_BASELINE_REL), payload)
    (f,) = one_chain.gather_fold_complete(root)
    assert f.check == "fold-complete-no-baseline" and f.status is DoctorStatus.WARN


def test_an_empty_tree_is_an_ok_summary(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    (f,) = one_chain.gather_fold_complete(root)
    assert f.check == "fold-complete" and f.status is DoctorStatus.OK
    assert f.evidence == {"complete": [], "baselined": []}


def test_the_check_is_read_only(tmp_path: Path) -> None:
    root = _tree(tmp_path)
    archived = _archived(root, "foo", _para("one"))
    station = _station(root, "mason", _para("one"))
    before = {p: p.read_bytes() for p in (archived, station)}
    one_chain.gather_fold_complete(root)
    assert {p: p.read_bytes() for p in before} == before
    assert sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()) == [
        "archive/docs/dreams/foo.md",
        "docs/dreams/pyforge-mason.md",
        "docs/governance/fold-complete-baseline.json",
    ]


# --- CLI ---------------------------------------------------------------------


def test_cli_exits_2_on_an_incomplete_fold_and_0_on_a_complete_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _tree(tmp_path)
    _archived(root, "foo", _para("one"))
    _station(root, "mason", "nothing pasted in yet\n")
    monkeypatch.chdir(root)
    # doctor's exit domain is {0, 2, 130}: a FAIL finding exits 2, never 1
    assert dispatch.main(["fold-complete"]) == 2
    assert "fold-complete-incomplete: fail" in capsys.readouterr().out

    _station(root, "mason", _para("one"))
    assert dispatch.main(["fold-complete"]) == 0


# --- live tree (conformance legs) --------------------------------------------


def test_live_baseline_names_the_seven_non_fold_paths() -> None:
    root = _live_root()
    data = json.loads((root / one_chain.FOLD_COMPLETE_BASELINE_REL).read_text(encoding="utf-8"))
    assert "$comment" in data
    assert data["paths"] == sorted(data["paths"])
    assert set(data["paths"]) <= {
        "archive/docs/dreams/deckcraft.md",
        "archive/docs/dreams/design-code-bridge.md",
        "archive/docs/dreams/herald-pitch-deck-family-expansion.md",
        "archive/docs/dreams/modernist-identity.md",
        "archive/docs/dreams/pyforge-genesis.md",
        "archive/docs/dreams/pyforge-unifying-strategy-2026-08-23-topology.md",
        "archive/docs/dreams/video-scripts.md",
    }  # the baseline only ever shrinks


def test_live_tree_has_no_fail_and_no_stray_baseline_warn() -> None:
    root = _live_root()
    findings = one_chain.gather_fold_complete(root)
    assert not _fails(findings), [f.message for f in _fails(findings)]
    assert not any(f.check == "fold-complete-no-baseline" for f in findings)
    # the only WARN the live tree may carry is the migration countdown
    assert {f.check for f in findings if f.status is DoctorStatus.WARN} <= {"fold-complete-archived-in-live-tree"}


def test_live_cli_exits_0(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(_live_root())
    assert dispatch.main(["fold-complete"]) == 0
