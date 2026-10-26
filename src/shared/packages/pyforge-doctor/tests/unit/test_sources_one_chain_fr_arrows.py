"""Doctor Story 50.1 (spec-pyforge-doctor CAP-92) -- the FR <- CAP arrow
grammar behind ``fr-without-cap`` (``sources/one_chain.py``).

Every fixture is a tiny planning tree under ``tmp_path`` with a known answer:
which lines define a requirement, what an arrow may carry, where a bare or
prefixed ``CAP-m`` resolves, which second definitions are duplicates, when a
lockstep run is a counted run, and how the baseline ratchet hides, stales
and prunes. The live-tree legs at the bottom pin the reference-heading
and honest-lockstep cases this checkout carries.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyforge.doctor.models import DoctorStatus
from pyforge.doctor.sources import one_chain
from pyforge.doctor.verdict import exit_code_for

try:
    _REPO_ROOT: Path | None = Path(__file__).resolve().parents[6]
except IndexError:
    _REPO_ROOT = None


def _live_root() -> Path:
    if _REPO_ROOT is None or not (_REPO_ROOT / ".claude").is_dir():
        pytest.skip("live repo root not resolvable from this checkout")
    return _REPO_ROOT


# --- fixture tree ------------------------------------------------------------

_STATION = "pyforge-marshal"


def _spec(root: Path, folder: str, body: str, *, project: str = _STATION, status: str = "ready") -> Path:
    d = root / "_bmad-output" / "projects" / project / "planning-artifacts" / "specs" / folder
    d.mkdir(parents=True, exist_ok=True)
    (d / "SPEC.md").write_text(f"---\nstatus: {status}\n---\n{body}")
    return d


def _governance_spec(root: Path, folder: str, body: str) -> Path:
    d = root / "docs" / "governance" / folder
    d.mkdir(parents=True, exist_ok=True)
    (d / "SPEC.md").write_text(f"---\nstatus: ready\n---\n{body}")
    return d


def _prd(root: Path, text: str, *, project: str = _STATION, name: str = "prd.md") -> Path:
    d = root / "_bmad-output" / "projects" / project / "planning-artifacts" / "prds" / f"prd-{project}-2026-01-01"
    d.mkdir(parents=True, exist_ok=True)
    p = d / name
    p.write_text(text)
    return p


def _baseline(
    root: Path,
    *,
    projects: dict[str, list[str]] | None = None,
    findings: dict[str, list[str]] | None = None,
) -> Path:
    data: dict = {"ruling_sha": "abc123", "projects": projects if projects is not None else {}}
    if findings is not None:
        data["findings"] = findings
        data["findings_sha"] = "def456"
    p = root / one_chain.FR_BASELINE_REL
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data))
    return p


def _tree(
    tmp_path: Path, prd: str, *, spec: str = "- **CAP-1 — the first thing.**\n- **CAP-2 — the second thing.**\n"
) -> Path:
    root = tmp_path / "repo"
    (root / "docs" / "governance").mkdir(parents=True, exist_ok=True)
    (root / "docs" / "governance" / "guild-roster.json").write_text(json.dumps({"stations": ["marshal"]}))
    _spec(root, f"spec-{_STATION}", spec)
    _prd(root, prd)
    _baseline(root)
    return root


def _by_check(findings) -> dict[str, list]:
    out: dict[str, list] = {}
    for f in findings:
        out.setdefault(f.check, []).append(f)
    return out


def _fails(findings) -> list:
    return [f for f in findings if f.status is DoctorStatus.FAIL]


# --- 1. the definition grammar -----------------------------------------------


def test_definition_grammar_markers_separators_and_references() -> None:
    text = "\n".join(
        [
            "## FR-1 — heading with em dash ← CAP-1",
            "#### FR-2: heading with colon ← CAP-1",
            "### FR-3 heading with whitespace title ← CAP-1",
            "- **FR-4** ← CAP-1 — bullet, bold, closes at once",
            "* **FR-5 — bullet with title** ← CAP-1",
            "| FR-6 | table cell | ← CAP-1 |",
            "**FR-7.1: dotted bold** ← CAP-1",
            "- **NFR-C2 (lettered, parenthetical title):** no arrow",
            "- **FR33** ← CAP-1 *(v1)*: unhyphenated",
            "FR-66–FR-71 encode and SC-10 tests.",
            "FR9 promises downstream consumers a field.",
            "  FR-10.)",
            "  (FR-8, FR-9.)",
            "### FR-8..FR-11 superseded in part",
            "### FR-7.1..FR-7.4: four arrows corrected",
            "- **FR9-was-KEV — cut REVERSED:** the original cut",
            "   - **FR-7.2 scheduler:** shipped as a cron job",
            "- **FR-12 is amended to include the push.** Returning is not enough",
            "- FR-13, FR-14 are covered elsewhere",
            "```",
            "#### FR-15: inside a fence ← CAP-1",
            "```",
            "#### FR-16: after the fence ← CAP-1",
        ]
    )
    defs, dups = one_chain._fr_definitions(text)
    assert [d.fr for d in defs] == ["FR-1", "FR-2", "FR-3", "FR-4", "FR-5", "FR-6", "FR-7.1", "NFR-C2", "FR33", "FR-16"]
    assert dups == {}
    by = {d.fr: d for d in defs}
    assert by["FR-1"].heading and by["FR-4"].heading is False
    assert by["FR-3"].title == "heading with whitespace title"
    assert by["FR-4"].title == "" and by["FR-4"].text == "bullet, bold, closes at once"
    assert by["FR-5"].title == "bullet with title"
    assert by["NFR-C2"].title.startswith("lettered, parenthetical title")
    assert by["NFR-C2"].arrowless and not by["FR33"].arrowless
    assert all(d.cites == ((None, 1),) for d in defs if d.fr != "NFR-C2")


def test_citation_from_first_body_line_and_heading_parenthetical() -> None:
    text = "\n".join(
        [
            "- **FR-1** new",
            "  ← CAP-2",
            "",
            "## FR-2 — the documentation is right (spec-pyforge-marshal CAP-1, CAP-2)",
            "body",
            "",
            "## FR-3 — nothing on the line",
            "body without a cite",
            "prose that mentions CAP-1 on the second body line",
        ]
    )
    defs, _ = one_chain._fr_definitions(text)
    by = {d.fr: d for d in defs}
    assert by["FR-1"].cites == ((None, 2),) and by["FR-1"].has_arrow
    assert by["FR-2"].cites == (("spec-pyforge-marshal", 1), (None, 2)) and not by["FR-2"].has_arrow
    assert by["FR-3"].arrowless  # the first non-blank body line only


# --- 2. the arrow carries CAP cites and nothing else -------------------------


def test_arrow_with_non_capability_item_fails_and_names_the_item(tmp_path: Path) -> None:
    root = _tree(
        tmp_path,
        '#### FR-1: Pixi-first ← Constraint "Conda-forge-only, pixi-managed"\n\n'
        '- **FR-2** ← CAP-1, Constraint "Copier is a dependency, not a framework" — `seed update --force`\n\n'
        "- **FR-3** ← CAP-1 and CAP-2 — both cites\n\n"
        "- **FR-4** ← CAP-1..CAP-2 *(a range)*: both cites\n",
    )
    by = _by_check(one_chain.gather_fr_without_cap(root))
    got = {f.evidence["fr"]: f.evidence["offending"] for f in by["fr-cites-non-capability"]}
    assert got == {
        "FR-1": ['Constraint "Conda-forge-only, pixi-managed"'],
        "FR-2": ['Constraint "Copier is a dependency, not a framework"'],
    }
    assert all(f.status is DoctorStatus.FAIL for f in by["fr-cites-non-capability"])
    assert {f.evidence["key"] for f in by["fr-cites-non-capability"]} == {
        "fr-cites-non-capability:FR-1",
        "fr-cites-non-capability:FR-2",
    }
    assert "fr-without-cap" not in by or by["fr-without-cap"][0].status is DoctorStatus.OK
    assert "fr-cap-unresolved" not in by


def test_arrowless_fr_outside_projects_is_fr_without_cap_but_a_constraint_arrow_is_not(tmp_path: Path) -> None:
    root = _tree(tmp_path, '#### FR-1: no arrow at all\n\n#### FR-2: an arrow ← Constraint "x"\n')
    by = _by_check(one_chain.gather_fr_without_cap(root))
    assert [f.evidence["fr"] for f in by["fr-without-cap"]] == ["FR-1"]
    assert [f.evidence["fr"] for f in by["fr-cites-non-capability"]] == ["FR-2"]


# --- 3. resolution against definitions, not mentions -------------------------


def test_bare_cap_resolves_only_against_the_station_spec_definition_lines(tmp_path: Path) -> None:
    root = _tree(
        tmp_path,
        "#### FR-1: defined ← CAP-1\n\n#### FR-2: mentioned only ← CAP-9\n\n#### FR-3: another spec's ← CAP-7\n",
        spec=(
            "- **CAP-1 — the first thing.**\n"
            "- **CAP-9's catalog names only what exists:** a mention, not a definition\n"
            "CAP-9 is cited in prose here too.\n"
        ),
    )
    _spec(root, "spec-other-open", "- **CAP-7 — lives in another open folder under the station.**\n")
    by = _by_check(one_chain.gather_fr_without_cap(root))
    got = {f.evidence["fr"]: (f.evidence["unresolved"], f.evidence["reasons"]) for f in by["fr-cap-unresolved"]}
    assert got == {
        "FR-2": (["CAP-9"], {"CAP-9": "cap-not-defined"}),
        "FR-3": (["CAP-7"], {"CAP-7": "cap-not-defined"}),
    }


def test_prefixed_cite_resolves_against_that_spec_wherever_it_lives(tmp_path: Path) -> None:
    root = _tree(
        tmp_path,
        "\n".join(
            [
                "#### FR-1: governance ← spec-guild-thing CAP-2",
                "#### FR-2: governance, undefined ← spec-guild-thing CAP-7",
                "#### FR-3: no such spec ← spec-nowhere CAP-1",
                "#### FR-4: absorbed pointer ← spec-folded CAP-1",
                "#### FR-5: another station's seam ← spec-pyforge-core CAP-3",
                "",
            ]
        ),
    )
    _governance_spec(root, "spec-guild-thing", "- **CAP-1 — one.**\n- **CAP-2 — two.**\n")
    _spec(root, "spec-folded", "# Absorbed into spec-pyforge-marshal\n\nDerived body disposed.\n", status="absorbed")
    _spec(root, "spec-pyforge-core", "### CAP-3 — the leaf exists\n", project="pyforge-core-host")
    by = _by_check(one_chain.gather_fr_without_cap(root))
    got = {f.evidence["fr"]: f.evidence["reasons"] for f in by["fr-cap-unresolved"]}
    assert got == {
        "FR-2": {"spec-guild-thing CAP-7": "cap-not-defined"},
        "FR-3": {"spec-nowhere CAP-1": "spec-not-found"},
        "FR-4": {"spec-folded CAP-1": "cap-not-defined"},
    }
    assert {f.evidence["key"] for f in by["fr-cap-unresolved"]} == {
        "fr-cap-unresolved:FR-2",
        "fr-cap-unresolved:FR-3",
        "fr-cap-unresolved:FR-4",
    }


def test_cap_definition_lines_heading_bullet_bold_and_titleless() -> None:
    caps = one_chain._cap_definitions(
        "\n".join(
            [
                "### CAP-1 — a heading form",
                "  - **intent:** an operator can do a thing",
                "  - **success:** the thing is done",
                "- **CAP-2**",
                "- **CAP-3 (a parenthetical title):** body",
                "**CAP-4 — bold at column zero.** *Intent:* inline intent.",
                "- **CAP-3 — a second definition loses.**",
                "- **CAP-5 keeps the refusal semantics** of a story",
                "```",
                "- **CAP-6 — fenced.**",
                "```",
            ]
        )
    )
    assert sorted(caps) == [1, 2, 3, 4]
    assert caps[1] == one_chain._CapDef("a heading form", "an operator can do a thing", "the thing is done")
    assert caps[2].title == ""
    assert caps[3].title.startswith("a parenthetical title")
    assert caps[4].intent == "inline intent."


# --- 4. ids ------------------------------------------------------------------


def test_unhyphenated_id_fails(tmp_path: Path) -> None:
    root = _tree(
        tmp_path, "- **FR33** ← CAP-1 *(v1, flag-activated)*: the license gate\n\n- **FR-34** ← CAP-1 — fine\n"
    )
    by = _by_check(one_chain.gather_fr_without_cap(root))
    (f,) = by["fr-id-unhyphenated"]
    assert (
        f.status is DoctorStatus.FAIL and f.evidence["fr"] == "FR33" and f.evidence["key"] == "fr-id-unhyphenated:FR33"
    )


# --- 5. one id, one definition -----------------------------------------------

_DUPLICATE_PRD = "\n".join(
    [
        "## 2. Requirements",
        "#### FR-1: The first ← CAP-1",
        "#### FR-2: The second ← CAP-2",
        "- **FR-1** is mentioned again without a title or an arrow",
        "",
        "## Satellite: Unity Data Stack",
        "###### FR-1: The first, pasted from the satellite",
        "###### FR-2: The second, pasted from the satellite",
        "",
        "## Currency reconciliation — 2026-09-28 (later)",
        "### FR-1: a dated note (2026-09-28, later)",
        "- **FR-2 (← CAP-2), as written.** Holds.",
        "",
        "## 31. Fold provenance",
        "#### FR-1: provenance reference",
        "",
        "## Test-tree convergence — reconciled",
        "### FR-2 checked against the code",
        "",
        "## Deferred-work verification state — reconciled 2026-09-08",
        "#### FR-2: another dated reference ← CAP-2",
        "",
        "## 3. A plain later section",
        "- **FR-2** ← CAP-2 — a bullet with an arrow description is a definition again",
        "",
    ]
)


def test_duplicate_fires_outside_record_sections_only(tmp_path: Path) -> None:
    root = _tree(tmp_path, _DUPLICATE_PRD)
    defs, dups = one_chain._fr_definitions(_DUPLICATE_PRD)
    assert [d.fr for d in defs] == ["FR-1", "FR-2"]
    assert dups == {"FR-1": [7], "FR-2": [8, 24]}
    by = _by_check(one_chain.gather_fr_without_cap(root))
    got = {f.evidence["fr"]: f.evidence["duplicate_lines"] for f in by["fr-duplicate-id"]}
    assert got == {"FR-1": [7], "FR-2": [8, 24]}
    assert {f.evidence["key"] for f in by["fr-duplicate-id"]} == {"fr-duplicate-id:FR-1", "fr-duplicate-id:FR-2"}


def test_record_section_detection() -> None:
    assert one_chain._record_section("Currency reconciliation — 2026-09-28")
    assert one_chain._record_section("31. Currency reconciliation — 2026-09-28")
    assert one_chain._record_section("Fold provenance")
    assert one_chain._record_section("Test-tree convergence — reconciled")
    assert one_chain._record_section("Two open Specs, decomposed 2026-08-08")
    assert not one_chain._record_section("Satellite: Unity Data Stack")
    assert not one_chain._record_section("7. Features")


# --- 6. counted runs ---------------------------------------------------------

_RUN_PRD = "\n".join(
    [
        "#### FR-1: A baseline can be stamped for one spec ← CAP-10",
        "#### FR-2: A stamp without a memlog line is refused ← CAP-11",
        "#### FR-3: The detector names every co-governor ← CAP-12",
        "#### FR-4: A stale stamp is a finding ← CAP-13",
        "",
    ]
)
_DAMAGED_TITLES = "- **CAP-10 — b**\n- **CAP-11 — a**\n- **CAP-12 — t**\n- **CAP-13 — t**\n"
_HONEST_TITLES = "- **CAP-10 — b**\n- **CAP-11 — a**\n- **CAP-12 — t**\n- **CAP-13 — the stale stamps are findings**\n"


def test_counted_run_fires_when_no_title_overlaps(tmp_path: Path) -> None:
    root = _tree(tmp_path, _RUN_PRD, spec=_DAMAGED_TITLES)
    by = _by_check(one_chain.gather_fr_without_cap(root))
    (f,) = by["fr-counted-run"]
    assert f.status is DoctorStatus.FAIL
    assert f.evidence["key"] == "fr-counted-run:FR-1..FR-4"
    assert f.evidence["fr_range"] == "FR-1..FR-4" and f.evidence["cap_range"] == "CAP-10..CAP-13"
    assert f.evidence["frs"] == ["FR-1", "FR-2", "FR-3", "FR-4"]


def test_counted_run_is_quiet_when_one_title_overlaps(tmp_path: Path) -> None:
    root = _tree(tmp_path, _RUN_PRD, spec=_HONEST_TITLES)  # "stale" / "finding" overlap on FR-4
    assert "fr-counted-run" not in _by_check(one_chain.gather_fr_without_cap(root))


@pytest.mark.parametrize(
    "prd",
    [
        _RUN_PRD.replace("#### FR-4: A stale stamp is a finding ← CAP-13\n", ""),  # three is not a run
        _RUN_PRD.replace("← CAP-13", "← CAP-14"),  # the offset moves
        _RUN_PRD.replace("← CAP-13", "← CAP-13, CAP-10"),  # two cites
        _RUN_PRD.replace("← CAP-13", "← spec-elsewhere CAP-13"),  # not the station Spec
        _RUN_PRD.replace("#### FR-4:", "#### FR-4.1:"),  # dotted id
    ],
)
def test_counted_run_needs_four_lockstep_single_own_cites(tmp_path: Path, prd: str) -> None:
    root = _tree(tmp_path, prd, spec=_DAMAGED_TITLES + "- **CAP-14 — x**\n")
    _spec(root, "spec-elsewhere", "- **CAP-13 — elsewhere**\n")
    assert "fr-counted-run" not in _by_check(one_chain.gather_fr_without_cap(root))


def test_content_words() -> None:
    assert one_chain._content_words("The stale stamps are findings (of CAP-13).") == {
        "stale",
        "stamp",
        "finding",
        "cap",
    }
    assert one_chain._content_words("an or by") == set()


# --- 7. the advisory ---------------------------------------------------------


def test_no_title_overlap_is_one_warn_per_station_and_never_changes_the_exit_code(tmp_path: Path) -> None:
    root = _tree(
        tmp_path,
        "#### FR-1: Unified Command Dispatcher ← CAP-1\n\n#### FR-2: the first thing, done ← CAP-1\n\n- **FR-3** ← CAP-2\n",
        spec=(
            "- **CAP-1 — the first thing.**\n  - **intent:** nothing in common\n  - **success:** nothing in common\n"
            "- **CAP-2 — the second thing.**\n"
        ),
    )
    findings = one_chain.gather_fr_without_cap(root)
    by = _by_check(findings)
    (w,) = by["fr-arrow-no-title-overlap"]
    assert w.status is DoctorStatus.WARN and w.evidence["frs"] == ["FR-1"]  # FR-2 overlaps; FR-3 has no words
    (ok,) = by["fr-without-cap"]
    assert ok.status is DoctorStatus.OK and ok.evidence["counts"][_STATION]["definitions"] == 3
    assert exit_code_for(findings) == 0


# --- 8. the baseline ratchet -------------------------------------------------


def test_baselined_finding_is_ok_and_a_stale_key_warns(tmp_path: Path) -> None:
    root = _tree(tmp_path, "- **FR33** ← CAP-1 *(v1)*: unhyphenated\n\n#### FR-2: fine ← CAP-2\n")
    _baseline(root, findings={_STATION: ["fr-id-unhyphenated:FR33", "fr-counted-run:FR-9..FR-12"]})
    findings = one_chain.gather_fr_without_cap(root)
    by = _by_check(findings)
    assert not _fails(findings)
    (b,) = by["fr-baselined"]
    assert b.status is DoctorStatus.OK and b.evidence["keys"] == ["fr-id-unhyphenated:FR33"]
    (stale,) = by["fr-baseline-stale"]
    assert stale.status is DoctorStatus.WARN and stale.evidence["key"] == "fr-counted-run:FR-9..FR-12"
    assert by["fr-without-cap"][0].status is DoctorStatus.OK
    assert exit_code_for(findings) == 0


def test_projects_entry_hides_only_the_missing_arrow(tmp_path: Path) -> None:
    root = _tree(tmp_path, "- **FR9** no arrow, pre-rule\n\n#### FR-2: new, no arrow\n")
    _baseline(root, projects={_STATION: ["FR9"]})
    by = _by_check(one_chain.gather_fr_without_cap(root))
    assert [f.evidence["fr"] for f in by["fr-without-cap"]] == ["FR-2"]
    assert [f.evidence["fr"] for f in by["fr-id-unhyphenated"]] == ["FR9"]  # structural checks ignore `projects`


def test_snapshot_records_the_arrowless_population_only_and_carries_findings(tmp_path: Path) -> None:
    root = _tree(
        tmp_path,
        '#### FR-1: cited ← CAP-1\n\n#### FR-2: bare\n\n#### FR-3: constraint ← Constraint "x"\n\n- **NFR-1 (y).**\n',
    )
    existing = {"ruling_sha": "abc123", "projects": {}, "findings": {_STATION: ["k"]}, "findings_sha": "def456"}
    data = one_chain.snapshot_fr_baseline(root, ruling_sha="abc123", existing=existing)
    assert data["projects"] == {_STATION: ["FR-2", "NFR-1"]}
    assert data["findings"] == {_STATION: ["k"]} and data["findings_sha"] == "def456"
    assert any("arrow" in line for line in data["$comment"])


def test_snapshot_fr_findings_lists_every_structural_key(tmp_path: Path) -> None:
    root = _tree(tmp_path, "- **FR33** ← CAP-1 *(v1)*: unhyphenated\n\n#### FR-2: x ← CAP-9\n")
    assert one_chain.snapshot_fr_findings(root) == {_STATION: ["fr-cap-unresolved:FR-2", "fr-id-unhyphenated:FR33"]}


def test_prune_drops_ids_that_gained_an_arrow_and_keys_that_stopped_firing(tmp_path: Path) -> None:
    root = _tree(
        tmp_path, "#### FR-1: now cited ← CAP-1\n\n#### FR-2: still bare\n\n- **FR33** ← CAP-1 *(v1)*: fires\n"
    )
    _baseline(
        root,
        projects={_STATION: ["FR-1", "FR-2", "FR-99"], "pyforge-gone": ["FR-1"]},
        findings={_STATION: ["fr-id-unhyphenated:FR33", "fr-counted-run:FR-9..FR-12"]},
    )
    data, removed = one_chain.prune_fr_baseline(root)
    assert data is not None
    assert data["projects"] == {_STATION: ["FR-2"], "pyforge-gone": []}
    assert data["findings"] == {_STATION: ["fr-id-unhyphenated:FR33"]}
    assert removed == [
        f"{_STATION}: FR-1",
        f"{_STATION}: FR-99",
        "pyforge-gone: FR-1",
        f"{_STATION}: fr-counted-run:FR-9..FR-12",
    ]
    (root / one_chain.FR_BASELINE_REL).unlink()
    assert one_chain.prune_fr_baseline(root) == (None, [])


def test_only_prd_md_is_a_prd(tmp_path: Path) -> None:
    root = _tree(tmp_path, "#### FR-1: the one ← CAP-1\n")
    _prd(root, "#### FR-1: a reviewer's copy\n#### FR-2: and a review-only id\n", name="review-adversarial.md")
    findings = one_chain.gather_fr_without_cap(root)
    assert not _fails(findings)
    assert _by_check(findings)["fr-without-cap"][0].evidence["counts"][_STATION]["definitions"] == 1


# --- live tree ---------------------------------------------------------------


def test_live_tree_reference_headings_never_duplicate_and_satellites_do() -> None:
    keys = one_chain.snapshot_fr_findings(_live_root())
    dups = {slug: [k for k in v if k.startswith("fr-duplicate-id:")] for slug, v in keys.items()}
    assert dups["pyforge-steward"] == [] and dups["pyforge-herald"] == [] and dups["pyforge-marshal"] == []
    assert "fr-duplicate-id:FR-1" in dups["pyforge-atlas"]  # the Unity / Wasm satellite sections


def test_live_tree_honest_lockstep_runs_stay_quiet() -> None:
    keys = one_chain.snapshot_fr_findings(_live_root())
    assert "fr-counted-run:FR-32..FR-41" not in keys["pyforge-steward"]
    assert "fr-counted-run:FR-69..FR-77" not in keys["pyforge-atlas"]
    assert not any(k.startswith("fr-counted-run:") for k in keys["pyforge-doctor"])
