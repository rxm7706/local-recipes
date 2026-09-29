"""Unit tests for ``pyforge.doctor.sources.board.gather_chain_completeness``
(Story 6.5) -- covers every row of the spec's I/O & Edge-Case Matrix that
belongs to ``chain_completeness`` (INV-A/B/C/D) against REAL tmp fixture
trees (planning-artifacts directories, a ledger, a data.js), mirroring
``test_sources_ledger.py``'s own real-fixture discipline.

Each of the four invariants below was independently verified, during
development, to actually FIRE its own dedicated test: temporarily commenting
out that invariant's ``findings.append(...)`` branch in
``sources/board.py::_check_chain_completeness`` and re-running the single
test made it fail (the invariant it exercises stopped being enforced). That
verification is not re-encoded here -- see the story spec's own Tasks &
Acceptance for the requirement.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import board
from pyforge.doctor.verdict import exit_code_for

# --- fixture helpers ---------------------------------------------------------


def _write_spec(path: Path, status: str, *, capabilities: list[int] | None = None) -> None:
    """``capabilities``, when given, appends a real ``## Capabilities``
    section declaring one ``- **CAP-<n> — ...**`` bullet per id -- the CAP-id
    coverage path fires only when this is non-empty. Byte-identical to the
    original (no section at all) when omitted, so every pre-existing
    zero-CAP test is unaffected."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = f"---\nstatus: {status}\nowner-dream: docs/dreams/x.md\n---\n\nbody\n"
    if capabilities:
        text += "\n## Capabilities\n\n"
        for n in capabilities:
            text += f"- **CAP-{n} — capability {n} title.**\n"
    path.write_text(text, encoding="utf-8")


def _write_epics_md(
    path: Path,
    story_ids: list[str],
    *,
    canonical: bool = True,
    extra_epics: list[int] | None = None,
) -> None:
    """``extra_epics`` appends bare ``## Epic N`` headings after the stories,
    so a test can drive INV-B's epic arm without disturbing its story arm."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---"]
    if canonical:
        lines.append("epics_role: canonical")
    lines.append("---")
    lines.append("")
    lines.append("## Epic 1: Test Epic")
    lines.extend(f"### Story {sid}: title" for sid in story_ids)
    lines.extend(f"## Epic {n}: Test Epic {n}" for n in extra_epics or [])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_ledger(path: Path, rows: dict[str, str]) -> None:
    """Writes ``rows``, plus a default ``epic-1: done`` when the caller
    supplied no ``epic-*`` key at all.

    ``_write_epics_md`` always emits exactly one ``## Epic 1`` heading, and
    INV-B's epic arm (2026-09-14) compares those headings against ``epic-N``
    keys. A real ledger always pairs them — every one of the fleet's eight
    does — so a fixture that omits the key is the unfaithful artifact, not
    the detector. Defaulting it here keeps all eighteen call sites honest
    without restating the pairing in each. A test exercising epic-arm drift
    passes its own ``epic-*`` key and opts out of the default."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not any(k.startswith("epic-") for k in rows):
        rows = {**rows, "epic-1": "done"}
    lines = ["development_status:"]
    lines.extend(f"  {k}: {v}" for k, v in rows.items())
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_data_js(path: Path, projects: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({"projects": projects})
    path.write_text(f"window.DASHBOARD_DATA = {payload};\n", encoding="utf-8")


def _pa(target: Path, project: str) -> Path:
    return target / "_bmad-output" / "projects" / project / "planning-artifacts"


def _write_roster(target: Path) -> None:
    """A valid ``guild-roster.json`` whose declared values equal ``board``'s
    own fallback constants (``OPEN_SPEC_STATUSES``/``DELIVERED_SPEC_STATUSES``)
    -- Story 59.2 sources INV-A's Spec-status vocabulary from this file, read
    fresh per call rather than a hardcoded module constant."""
    path = target / "docs" / "governance" / "guild-roster.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "spec_statuses": [
                    "draft",
                    "ready",
                    "in-progress",
                    "shipped",
                    "archived",
                    "absorbed",
                    "superseded",
                    "extension-point",
                ],
                "spec_statuses_terminal": [
                    "shipped",
                    "archived",
                    "absorbed",
                    "superseded",
                ],
                "spec_statuses_ended_acts": [
                    "archived",
                    "absorbed",
                    "superseded",
                ],
            }
        ),
        encoding="utf-8",
    )


@pytest.fixture(autouse=True)
def _seed_guild_roster(tmp_path: Path) -> None:
    """Every test below exercises ``gather_chain_completeness``, whose INV-A
    Spec-status vocabulary is sourced from ``guild-roster.json`` (Story 59.2)
    rather than a hardcoded module constant. Seed a valid roster at
    ``tmp_path`` automatically so every pre-existing test here keeps
    exercising the LIVE-DERIVED path -- which yields byte-identical
    open/delivered sets to ``board``'s own fallback constants -- rather than
    the degrade-to-fallback path, preserving each test's existing assertions
    unchanged. A test exercising the degrade path itself writes its own
    (missing/malformed) roster under a target that is NOT bare ``tmp_path``,
    or overwrites this file directly."""
    _write_roster(tmp_path)


# --- Story 59.2: guild-roster.json degrade-to-fallback ----------------------


def test_missing_roster_degrades_to_fallback_and_warns(tmp_path: Path) -> None:
    """A target with no ``docs/governance/guild-roster.json`` at all (a
    subdirectory of the autouse-seeded ``tmp_path``, so the seeded roster
    above does not leak in) still classifies Spec statuses correctly -- via
    ``OPEN_SPEC_STATUSES``/``DELIVERED_SPEC_STATUSES``, the module's own
    fallback -- and surfaces a ``spec-status-roster-degraded`` WARN rather
    than crashing or degrading silently (Story 59.2)."""
    root = tmp_path / "no-roster"
    pa = _pa(root, "pyforge-testproj")
    _write_spec(pa / "specs" / "spec-foo" / "SPEC.md", "draft")

    findings = board.gather_chain_completeness(root)

    by_check = {f.check: f for f in findings}
    assert "spec-not-decomposed" in by_check, f"fallback classification failed: {[f.check for f in findings]}"
    assert by_check["spec-not-decomposed"].status is DoctorStatus.FAIL
    assert "spec-status-roster-degraded" in by_check
    degraded = by_check["spec-status-roster-degraded"]
    assert degraded.status is DoctorStatus.WARN
    assert degraded.evidence["project"] == "pyforge-testproj"


# --- INV-A: every open Spec is decomposed ------------------------------------


def test_open_undecomposed_spec_reports_fail(tmp_path: Path) -> None:
    pa = _pa(tmp_path, "pyforge-testproj")
    _write_spec(pa / "specs" / "spec-foo" / "SPEC.md", "draft")

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.CHAIN_COMPLETENESS
    assert finding.check == "spec-not-decomposed"
    assert finding.status is DoctorStatus.FAIL
    assert finding.evidence["inv"] == "INV-A"
    assert finding.evidence["project"] == "pyforge-testproj"
    assert finding.evidence["subject"] == "spec-foo"
    assert "no FR or epic references" in finding.message


def test_spec_decomposed_in_prd_prose_reports_no_finding(tmp_path: Path) -> None:
    """The mirror-image control: the same open Spec, but its slug DOES appear
    in the project's PRD prose -- INV-A must not fire."""
    pa = _pa(tmp_path, "pyforge-testproj")
    _write_spec(pa / "specs" / "spec-foo" / "SPEC.md", "draft")
    prd = pa / "prds" / "prd-x" / "prd.md"
    prd.parent.mkdir(parents=True, exist_ok=True)
    prd.write_text("This PRD decomposes spec-foo into FR-1.\n", encoding="utf-8")

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK


def test_deferred_spec_reports_no_finding(tmp_path: Path) -> None:
    """A slug registered in DEFERRED_SPECS is a recorded decision, not a
    silent gap -- INV-A must not fire for it even though it is undecomposed."""
    pa = _pa(tmp_path, "pyforge-testproj")
    _write_spec(pa / "specs" / "spec-pyforge-charter" / "SPEC.md", "draft")

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK


def test_shipped_spec_with_no_epic_reference_reports_delivered_not_decomposed(
    tmp_path: Path,
) -> None:
    """Replaces ``test_shipped_spec_is_not_open_and_reports_no_finding``
    (2026-09-14). That test asserted the original design — every non-open
    status skipped INV-A entirely — which is right for ``absorbed`` /
    ``archived`` / ``superseded`` / ``extension-point`` and wrong for
    ``shipped``: work really delivered, with no epic and no ledger row, leaves
    the station under-reporting what it shipped. Ten such Specs were live
    fleet-wide when this was found."""
    pa = _pa(tmp_path, "pyforge-testproj")
    _write_spec(pa / "specs" / "spec-foo" / "SPEC.md", "shipped")

    findings = board.gather_chain_completeness(tmp_path)

    delivered = [f for f in findings if f.check == "delivered-spec-not-decomposed"]
    assert len(delivered) == 1
    assert delivered[0].status is DoctorStatus.FAIL
    assert "spec-foo" in delivered[0].message
    # The remedy must NOT point at DEFERRED_SPECS: that is the escape hatch for
    # work deliberately not done, and this is work already delivered.
    assert "DEFERRED_SPECS" not in delivered[0].evidence.get("remedy", "").split("never")[0]


def test_shipped_spec_referenced_by_an_epic_reports_no_finding(tmp_path: Path) -> None:
    """The delivered branch is held to the WHOLE-SPEC standard, never INV-A's
    per-CAP citation test: an epic that names the Spec at all clears it, even
    without enumerating every ``CAP-n``. Running per-CAP here flagged 34 Specs
    against 12 real ones, because epics written before the cite-every-CAP-id
    convention name the Spec or its Dream and stop."""
    pa = _pa(tmp_path, "pyforge-testproj")
    _write_spec(pa / "specs" / "spec-foo" / "SPEC.md", "shipped")
    (pa / "epics.md").write_text(
        "## Epic 1: Foo\n\nDecomposes spec-foo.\n\n### Story 1.1: Bar\n**Status:** done\n",
        encoding="utf-8",
    )

    findings = board.gather_chain_completeness(tmp_path)

    assert not [f for f in findings if f.check == "delivered-spec-not-decomposed"]


def test_shipped_spec_claimed_by_its_dream_path_reports_no_finding(tmp_path: Path) -> None:
    """An epic may claim a Spec by its ``owner-dream`` path instead of its slug
    (steward Epic 51 claims spec-platform-datastores-consumed-not-self-hosted
    that way). Matching only ``spec-<slug>`` reported it as a false positive."""
    pa = _pa(tmp_path, "pyforge-testproj")
    _write_spec(pa / "specs" / "spec-foo" / "SPEC.md", "shipped")
    (pa / "epics.md").write_text(
        "## Epic 1: Foo\n\nSeeded from docs/dreams/x.md.\n\n### Story 1.1: Bar\n**Status:** done\n",
        encoding="utf-8",
    )

    findings = board.gather_chain_completeness(tmp_path)

    assert not [f for f in findings if f.check == "delivered-spec-not-decomposed"]


def test_absorbed_and_archived_specs_stay_exempt_from_decomposition(
    tmp_path: Path,
) -> None:
    """The guard-removed companion: only ``shipped`` joined the checked set.
    ``absorbed`` CAPs live in the absorbing chain's epic, ``archived`` and
    ``superseded`` were abandoned rather than delivered, and
    ``extension-point`` is a standing seam — none owes a story trail."""
    for status in ("absorbed", "archived", "superseded", "extension-point"):
        root = tmp_path / status
        _write_roster(root)
        pa = _pa(root, "pyforge-testproj")
        _write_spec(pa / "specs" / "spec-foo" / "SPEC.md", status)

        findings = board.gather_chain_completeness(root)

        assert not [f for f in findings if f.check == "delivered-spec-not-decomposed"], f"{status} must stay exempt"


def test_spec_without_status_key_reports_spec_status_missing(tmp_path: Path) -> None:
    """A missing ``status:`` key must not silently exempt a Spec the way a
    declared-terminal status does — it fires ``spec-status-missing`` instead."""
    pa = _pa(tmp_path, "pyforge-testproj")
    spec_path = pa / "specs" / "spec-foo" / "SPEC.md"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(
        "---\nowner-dream: docs/dreams/x.md\n---\n\nbody\n",
        encoding="utf-8",
    )

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.CHAIN_COMPLETENESS
    assert finding.check == "spec-status-missing"
    assert finding.status is DoctorStatus.FAIL
    assert finding.evidence["inv"] == "INV-A"
    assert finding.evidence["subject"] == "spec-foo"
    assert "no status:" in finding.message
    assert "DEFERRED_SPECS" in finding.evidence["remedy"]
    assert "status: line" in finding.evidence["remedy"]


def test_deferred_spec_without_status_key_reports_no_finding(tmp_path: Path) -> None:
    """``DEFERRED_SPECS`` remains a whole-Spec escape hatch even when the
    ``status:`` key is absent."""
    pa = _pa(tmp_path, "pyforge-testproj")
    spec_path = pa / "specs" / "spec-pyforge-charter" / "SPEC.md"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(
        "---\nowner-dream: docs/dreams/x.md\n---\n\nbody\n",
        encoding="utf-8",
    )

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK


# --- INV-A: CAP-id coverage (Story 12.3, Round 4) -----------------------------
#
# A Spec that declares real `## Capabilities` CAP ids is judged by CAP-id
# coverage, not the bare-substring test above (that test stays the fallback
# for a Spec with zero declared ids -- see the two tests above, which must
# keep passing unmodified as proof of that fallback).


def test_multi_cap_spec_partial_coverage_names_uncovered_ids(tmp_path: Path) -> None:
    """The DW-CHAIN-COMPLETENESS-1 repro: a Spec grows CAP ids faster than
    stories decompose them, and the check must name the specific gap, never
    read `ok` just because SOME of the Spec's ids are cited somewhere."""
    pa = _pa(tmp_path, "pyforge-testproj")
    _write_spec(pa / "specs" / "spec-foo" / "SPEC.md", "draft", capabilities=list(range(1, 11)))
    epics = pa / "epics.md"
    epics.parent.mkdir(parents=True, exist_ok=True)
    epics.write_text(
        "---\nepics_role: canonical\n---\n\n## Epic 1: Test\n\nDecomposes `spec-foo` CAP-1..3.\n",
        encoding="utf-8",
    )

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "spec-not-decomposed"
    assert finding.status is DoctorStatus.FAIL
    assert finding.evidence["inv"] == "INV-A"
    assert "CAP-4..10" in finding.message
    assert "CAP-4..10" in finding.evidence["remedy"]
    assert "DEFERRED_SPECS" in finding.evidence["remedy"]


def test_multi_cap_spec_full_coverage_via_mixed_citation_shapes_reports_ok(
    tmp_path: Path,
) -> None:
    """Bare, slash-grouped, and inclusive-range citations together cover
    every declared id -- no finding."""
    pa = _pa(tmp_path, "pyforge-testproj")
    _write_spec(pa / "specs" / "spec-foo" / "SPEC.md", "draft", capabilities=[1, 2, 3, 4, 5])
    epics = pa / "epics.md"
    epics.parent.mkdir(parents=True, exist_ok=True)
    epics.write_text(
        "---\nepics_role: canonical\n---\n\n## Epic 1: Test\n\nDecomposes `spec-foo` CAP-1, CAP-2/3, CAP-4..5.\n",
        encoding="utf-8",
    )

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK


def test_prefixed_range_citation_shape_covers_the_inclusive_range(tmp_path: Path) -> None:
    """`CAP-N..CAP-M` (not just `CAP-N..M`) must expand, not get silently
    dropped -- the shape review pass 1 found live, 5 fleet occurrences."""
    pa = _pa(tmp_path, "pyforge-testproj")
    _write_spec(pa / "specs" / "spec-foo" / "SPEC.md", "draft", capabilities=[1, 2, 3, 4, 5])
    epics = pa / "epics.md"
    epics.parent.mkdir(parents=True, exist_ok=True)
    epics.write_text(
        "---\nepics_role: canonical\n---\n\n## Epic 1: Test\n\nDecomposes `spec-foo` CAP-1..CAP-5.\n",
        encoding="utf-8",
    )

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK


def test_malformed_capabilities_section_falls_back_to_bare_substring(tmp_path: Path) -> None:
    """A `## Capabilities` heading whose lines never match the declared-bullet
    shape parses to zero ids -- treated exactly like no heading at all."""
    pa = _pa(tmp_path, "pyforge-testproj")
    spec_path = pa / "specs" / "spec-foo" / "SPEC.md"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(
        "---\nstatus: draft\n---\n\nbody\n\n## Capabilities\n\n"
        "Some free-form prose that never matches the CAP-N bullet shape.\n",
        encoding="utf-8",
    )
    prd = pa / "prds" / "prd-x" / "prd.md"
    prd.parent.mkdir(parents=True, exist_ok=True)
    prd.write_text("This PRD decomposes spec-foo into FR-1.\n", encoding="utf-8")

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK  # fallback: slug found in prose


def test_reversed_range_citation_contributes_no_ids(tmp_path: Path) -> None:
    """`CAP-10..4` (end before start) must not credit ANY id -- not even its
    own start value -- and must not crash."""
    pa = _pa(tmp_path, "pyforge-testproj")
    _write_spec(
        pa / "specs" / "spec-foo" / "SPEC.md",
        "draft",
        capabilities=list(range(1, 11)),
    )
    epics = pa / "epics.md"
    epics.parent.mkdir(parents=True, exist_ok=True)
    epics.write_text(
        "---\nepics_role: canonical\n---\n\n## Epic 1: Test\n\nDecomposes `spec-foo` CAP-10..4.\n",
        encoding="utf-8",
    )

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.status is DoctorStatus.FAIL
    assert "CAP-1..10" in finding.message  # nothing at all was credited


def test_two_specs_overlapping_cap_ids_only_the_cited_one_is_covered(tmp_path: Path) -> None:
    """The Round 2 repro: two open Specs in the same project both number
    their own capabilities CAP-1..3. Only `spec-bar` is actually cited --
    `spec-foo` must still fire, not be covered by `spec-bar`'s citation."""
    pa = _pa(tmp_path, "pyforge-testproj")
    _write_spec(pa / "specs" / "spec-foo" / "SPEC.md", "draft", capabilities=[1, 2, 3])
    _write_spec(pa / "specs" / "spec-bar" / "SPEC.md", "draft", capabilities=[1, 2, 3])
    epics = pa / "epics.md"
    epics.parent.mkdir(parents=True, exist_ok=True)
    epics.write_text(
        "---\nepics_role: canonical\n---\n\n## Epic 1: Test\n\nDecomposes `spec-bar` CAP-1..3.\n",
        encoding="utf-8",
    )

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.evidence["subject"] == "spec-foo"
    assert finding.status is DoctorStatus.FAIL


def test_citation_coasts_across_exactly_one_unanchored_heading(tmp_path: Path) -> None:
    """The real `spec-deferred-work-visibility` Epic 8 -> Epic 9 shape: a
    Spec's own citations continue into the NEXT epic without repeating the
    Spec's slug there -- still counts, because the window is capped at the
    SECOND heading past the anchor, not the first."""
    pa = _pa(tmp_path, "pyforge-testproj")
    _write_spec(pa / "specs" / "spec-foo" / "SPEC.md", "draft", capabilities=[1, 2, 3])
    epics = pa / "epics.md"
    epics.parent.mkdir(parents=True, exist_ok=True)
    epics.write_text(
        "---\nepics_role: canonical\n---\n\n"
        "## Epic 1: Test\n\n"
        "Decomposes `spec-foo` CAP-1.\n\n"
        "## Epic 2: Continued\n\n"
        "More detail here, still covering CAP-2 and CAP-3.\n\n"
        "## Epic 3: Unrelated\n\n"
        "Nothing to do with spec-foo here.\n",
        encoding="utf-8",
    )

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK


def test_citation_does_not_leak_past_two_headings(tmp_path: Path) -> None:
    """The real Epic-14-to-Epic-16 marshal shape that motivated the cap: a
    CAP id appearing TWO OR MORE headings past a Spec's own anchor must NOT
    count as covering that Spec."""
    pa = _pa(tmp_path, "pyforge-testproj")
    _write_spec(pa / "specs" / "spec-foo" / "SPEC.md", "draft", capabilities=[1, 2])
    epics = pa / "epics.md"
    epics.parent.mkdir(parents=True, exist_ok=True)
    epics.write_text(
        "---\nepics_role: canonical\n---\n\n"
        "## Epic 1: Test\n\n"
        "Decomposes `spec-foo` CAP-1.\n\n"
        "## Epic 2: Continued\n\n"
        "Unrelated epic content here, nothing about coverage.\n\n"
        "## Epic 3: Also unrelated\n\n"
        "Still nothing.\n\n"
        "## Epic 4: Far away\n\n"
        "Only here does CAP-2 appear, two headings past the anchor's own heading.\n",
        encoding="utf-8",
    )

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.status is DoctorStatus.FAIL
    assert "CAP-2" in finding.message


def test_two_file_preamble_leak_is_excluded_while_real_citation_still_found(
    tmp_path: Path,
) -> None:
    """Round 4's required miniature repro: the FIRST-concatenated file (a
    `prds/*/prd.md`, which always sorts ahead of `epics*.md` in the prose
    build) carries a header-less preamble mentioning a Spec's slug near an
    unrelated CAP id, before ITS OWN first `## ` heading. The SECOND file has
    that Spec's real, legitimate citation under a real heading.

    The preamble mention must not leak into coverage -- proven here by
    declaring a CAP id (CAP-9) that is ONLY EVER mentioned in the preamble,
    never for real: if the leak happened, CAP-9 would read as covered and
    this Spec's real, still-open gap would silently vanish (status OK
    instead of FAIL). The real CAP-1..3 citation must still count.

    This replaces Round 3's single-file, first-position-only version of this
    test (a whole-blob "before the first heading" exclusion, which only ever
    protected whichever file sorted first)."""
    pa = _pa(tmp_path, "pyforge-testproj")
    _write_spec(pa / "specs" / "spec-foo" / "SPEC.md", "draft", capabilities=[1, 2, 3, 9])

    prd = pa / "prds" / "prd-x" / "prd.md"
    prd.parent.mkdir(parents=True, exist_ok=True)
    prd.write_text(
        "changelog note: spec-foo's CAP-9 was discussed and deferred, no heading yet\n\n"
        "## Unrelated Section\n\nNothing about spec-foo here.\n",
        encoding="utf-8",
    )

    epics = pa / "epics.md"
    epics.parent.mkdir(parents=True, exist_ok=True)
    epics.write_text(
        "---\nepics_role: canonical\n---\n\n## Epic 1: Test\n\nDecomposes `spec-foo` CAP-1..3.\n",
        encoding="utf-8",
    )

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.status is DoctorStatus.FAIL, (
        f"the preamble's CAP-9 mention leaked into coverage, hiding a real gap: {finding}"
    )
    assert finding.check == "spec-not-decomposed"
    assert "CAP-9" in finding.message


def test_end_to_end_multi_file_prose_via_gather_chain_completeness(tmp_path: Path) -> None:
    """The REAL end-to-end path, through the public entrypoint, with TWO
    `epics*.md`-matching files feeding `prose` -- proving the sorted-glob,
    multi-file, separator-joined build actually works, not just the helper
    functions in isolation. The SECOND-sorted file additionally carries its
    own header-less preamble mentioning the Spec's slug near an unrelated
    CAP id (the exact shape Blind Hunter found live in `pyforge-doctor`'s
    own `epics.md`'s `currency_review` frontmatter field) -- it must not
    leak, while the FIRST file's real, headed citation must still be found."""
    pa = _pa(tmp_path, "pyforge-testproj")
    _write_spec(pa / "specs" / "spec-foo" / "SPEC.md", "draft", capabilities=[1, 2])

    epics_a = pa / "epics-a.md"
    epics_a.parent.mkdir(parents=True, exist_ok=True)
    epics_a.write_text(
        "---\nepics_role: canonical\n---\n\n## Epic 1: Test\n\nDecomposes `spec-foo` CAP-1..2.\n",
        encoding="utf-8",
    )

    epics_b = pa / "epics-b.md"
    epics_b.write_text(
        '---\ncurrency_review: "mentions spec-foo and CAP-9 in passing, no heading yet"'
        "\n---\n\n## Notes\n\nNothing further about spec-foo here.\n",
        encoding="utf-8",
    )

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK


def test_format_cap_ids_collapses_consecutive_runs() -> None:
    assert board._format_cap_ids({4, 6, 7, 8, 9, 10}) == "CAP-4, CAP-6..10"
    assert board._format_cap_ids({1}) == "CAP-1"
    assert board._format_cap_ids(set()) == ""


def test_parse_declared_cap_ids_skips_unparseable_lines() -> None:
    text = (
        "## Capabilities\n\n"
        "- **CAP-1 — real.**\n"
        "  - **intent:** ok\n"
        "some free-form prose that does not match\n"
        "- **CAP-2 — also real.**\n"
    )
    assert board._parse_declared_cap_ids(text) == {1, 2}
    assert board._parse_declared_cap_ids("no capabilities heading at all") == set()


def test_expand_cap_token_handles_every_citation_shape() -> None:
    def ids(text: str) -> set[int]:
        m = board._CAP_CITATION_RE.search(text)
        assert m is not None
        return board._expand_cap_token(m)

    assert ids("CAP-5") == {5}
    assert ids("CAP-4..10") == {4, 5, 6, 7, 8, 9, 10}
    assert ids("CAP-4..CAP-10") == {4, 5, 6, 7, 8, 9, 10}
    assert ids("CAP-1/2/3") == {1, 2, 3}
    assert ids("CAP-10..4") == set()  # reversed -- contributes nothing


# --- INV-B: epics.md set == ledger set ---------------------------------------


def test_ledger_key_without_epics_story_reports_fail(tmp_path: Path) -> None:
    pa = _pa(tmp_path, "pyforge-testproj")
    _write_epics_md(pa / "epics.md", ["1.1"])
    _write_ledger(
        pa / "sprint-status-ledger.yaml",
        {
            "1-1-foo": "done",
            "9-9-orphan": "done",
        },
    )

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "ledger-key-without-story"
    assert finding.status is DoctorStatus.FAIL
    assert finding.evidence["inv"] == "INV-B"
    assert "9-9" in finding.evidence["status"]


def test_epics_story_without_ledger_key_reports_fail(tmp_path: Path) -> None:
    pa = _pa(tmp_path, "pyforge-testproj")
    _write_epics_md(pa / "epics.md", ["1.1", "1.2"])
    _write_ledger(pa / "sprint-status-ledger.yaml", {"1-1-foo": "done"})

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "story-without-ledger-key"
    assert finding.status is DoctorStatus.FAIL
    assert finding.evidence["inv"] == "INV-B"
    assert "1-2" in finding.evidence["status"]


def test_unparseable_ledger_key_reports_fail(tmp_path: Path) -> None:
    """A ledger key with no recognisable id shape is REPORTED, not silently
    dropped from the comparison (the original script's own rationale)."""
    pa = _pa(tmp_path, "pyforge-testproj")
    _write_epics_md(pa / "epics.md", ["1.1"])
    _write_ledger(
        pa / "sprint-status-ledger.yaml",
        {
            "1-1-foo": "done",
            "not_a_recognisable_key": "done",
        },
    )

    findings = board.gather_chain_completeness(tmp_path)

    kinds = {f.check for f in findings}
    assert "unparseable-ledger-key" in kinds
    unparsed = next(f for f in findings if f.check == "unparseable-ledger-key")
    assert unparsed.status is DoctorStatus.FAIL
    assert unparsed.evidence["inv"] == "INV-B"


def test_epics_and_ledger_in_full_agreement_reports_no_finding(tmp_path: Path) -> None:
    pa = _pa(tmp_path, "pyforge-testproj")
    _write_epics_md(pa / "epics.md", ["1.1", "1.2"])
    _write_ledger(
        pa / "sprint-status-ledger.yaml",
        {
            "1-1-foo": "done",
            "1-2-bar": "in-progress",
        },
    )

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK


# --- INV-B: epic headings == ledger epic keys (2026-09-14) -------------------
#
# The story arm above compares STORIES. Until 2026-09-14 nothing compared
# EPICS, because `_ledger_story_ids` discarded every `epic-*` key as
# "not a story id" — so an epic could exist on one side alone indefinitely.
# It did, twice: steward Epic 18 sat at H3 (never promoted to a `##` heading)
# and marshal Epic 29 had no heading at any level, a gap marshal's own
# frontmatter had admitted in prose — "183 (181 + Epic 29's two, never
# counted)" — without any detector ever reading it.


def test_epic_heading_without_ledger_key_reports_fail(tmp_path: Path) -> None:
    pa = _pa(tmp_path, "pyforge-testproj")
    _write_epics_md(pa / "epics.md", ["1.1"], extra_epics=[7])
    _write_ledger(
        pa / "sprint-status-ledger.yaml",
        {
            "epic-1": "done",
            "1-1-foo": "done",
        },
    )

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "epic-heading-without-ledger-key"
    assert finding.status is DoctorStatus.FAIL
    assert finding.evidence["inv"] == "INV-B"
    assert "7" in finding.evidence["status"]


def test_ledger_epic_key_without_heading_reports_fail(tmp_path: Path) -> None:
    """marshal Epic 29's live shape: the ledger tracks it, no heading declares
    it. The story arm cannot see this — `epic-29` parses as no story id."""
    pa = _pa(tmp_path, "pyforge-testproj")
    _write_epics_md(pa / "epics.md", ["1.1"])
    _write_ledger(
        pa / "sprint-status-ledger.yaml",
        {
            "epic-1": "done",
            "epic-9": "done",
            "1-1-foo": "done",
        },
    )

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "ledger-epic-key-without-heading"
    assert finding.status is DoctorStatus.FAIL
    assert finding.evidence["inv"] == "INV-B"
    assert "9" in finding.evidence["status"]


def test_epic_headings_and_ledger_keys_in_agreement_reports_no_finding(
    tmp_path: Path,
) -> None:
    pa = _pa(tmp_path, "pyforge-testproj")
    _write_epics_md(pa / "epics.md", ["1.1"], extra_epics=[2])
    _write_ledger(
        pa / "sprint-status-ledger.yaml",
        {
            "epic-1": "done",
            "epic-2": "backlog",
            "1-1-foo": "done",
        },
    )

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK


def test_a_retrospective_key_is_not_a_second_epic(tmp_path: Path) -> None:
    """Guard-removed companion: every station pairs `epic-N` with
    `epic-N-retrospective`, so matching the epic key loosely would demand a
    heading per retrospective and red the whole fleet at once."""
    pa = _pa(tmp_path, "pyforge-testproj")
    _write_epics_md(pa / "epics.md", ["1.1"])
    _write_ledger(
        pa / "sprint-status-ledger.yaml",
        {
            "epic-1": "done",
            "epic-1-retrospective": "optional",
            "1-1-foo": "done",
        },
    )

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK


# --- INV-D: canonical epics declares zero stories ----------------------------


def test_canonical_epics_with_zero_stories_reports_fail(tmp_path: Path) -> None:
    pa = _pa(tmp_path, "pyforge-testproj")
    _write_epics_md(pa / "epics.md", [])  # zero `### Story` headings
    _write_ledger(pa / "sprint-status-ledger.yaml", {"1-1-foo": "done"})

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "canonical-epics-declares-no-stories"
    assert finding.status is DoctorStatus.FAIL
    assert finding.evidence["inv"] == "INV-D"
    assert "0 `### Story` headings vs 1 ledger key(s)" == finding.evidence["status"]


# --- INV-C: board line == ledger ---------------------------------------------


def test_board_diverging_from_ledger_reports_fail(tmp_path: Path) -> None:
    """Herald's own 2026-08-08 incident, shrunk to a fixture: the board
    renders a smaller/different story set than the durable ledger record."""
    pa = _pa(tmp_path, "pyforge-herald")
    _write_ledger(
        pa / "sprint-status-ledger.yaml",
        {
            "1-1-a": "done",
            "1-2-b": "done",
            "1-3-c": "in-progress",
        },
    )
    _write_data_js(
        tmp_path / "docs" / "dashboard" / "data.js",
        {
            "herald": {"epics": [{"stories": [["1.1", "done", "a"], ["1.2", "pending", "b"]]}]},
        },
    )

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "board-diverges-from-ledger"
    assert finding.status is DoctorStatus.FAIL
    assert finding.evidence["inv"] == "INV-C"
    assert finding.evidence["subject"] == "herald"
    assert "board 1/2 vs ledger 2/3" == finding.evidence["status"]


def test_board_matching_ledger_reports_no_finding(tmp_path: Path) -> None:
    pa = _pa(tmp_path, "pyforge-herald")
    _write_ledger(pa / "sprint-status-ledger.yaml", {"1-1-a": "done", "1-2-b": "in-progress"})
    _write_data_js(
        tmp_path / "docs" / "dashboard" / "data.js",
        {
            "herald": {"epics": [{"stories": [["1.1", "done", "a"], ["1.2", "pending", "b"]]}]},
        },
    )

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK


# --- data.js unreadable: INV-C silently skipped; INV-A/B/D unaffected -------


def test_unreadable_data_js_skips_inv_c_without_affecting_others(tmp_path: Path) -> None:
    pa = _pa(tmp_path, "pyforge-testproj")
    _write_spec(pa / "specs" / "spec-foo" / "SPEC.md", "draft")  # INV-A fires
    data_js = tmp_path / "docs" / "dashboard" / "data.js"
    data_js.parent.mkdir(parents=True, exist_ok=True)
    data_js.write_text("not the expected prefix at all\n", encoding="utf-8")

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    assert findings[0].check == "spec-not-decomposed"
    assert findings[0].status is DoctorStatus.FAIL
    assert not any(f.check == "board-diverges-from-ledger" for f in findings)


def test_missing_data_js_never_raises(tmp_path: Path) -> None:
    pa = _pa(tmp_path, "pyforge-testproj")
    _write_ledger(pa / "sprint-status-ledger.yaml", {"1-1-foo": "done"})
    # deliberately no docs/dashboard/data.js at all, and no epics.md either

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK


# --- No projects / never raises ----------------------------------------------


def test_no_projects_directory_reports_ok_with_zero_projects(tmp_path: Path) -> None:
    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.CHAIN_COMPLETENESS
    assert finding.check == "chain-completeness"
    assert finding.status is DoctorStatus.OK
    # `board_read` is False here: with no docs/dashboard/data.js there is no
    # board to compare, and the OK must say so rather than assert agreement.
    assert finding.evidence == {"projects": 0, "board_read": False}


def test_multiple_projects_are_all_reported_independently(tmp_path: Path) -> None:
    """BOTH projects must be dirty: with one dirty and one clean, a bug that
    dropped every project after the first would still pass."""
    pa_a = _pa(tmp_path, "pyforge-alpha")
    _write_spec(pa_a / "specs" / "spec-foo" / "SPEC.md", "draft")

    pa_b = _pa(tmp_path, "pyforge-beta")
    _write_spec(pa_b / "specs" / "spec-bar" / "SPEC.md", "draft")

    findings = board.gather_chain_completeness(tmp_path)

    assert {f.evidence["project"] for f in findings} == {"pyforge-alpha", "pyforge-beta"}
    assert all(f.check == "spec-not-decomposed" for f in findings)
    assert all(f.status is DoctorStatus.FAIL for f in findings)


# --- one project's malformed input must not swallow another's real finding --


def test_unreadable_spec_in_one_project_does_not_hide_a_real_finding_in_another(
    tmp_path: Path,
) -> None:
    """A non-UTF-8 byte in ONE project's SPEC.md must not disturb a
    DIFFERENT, well-formed project's real ``spec-not-decomposed`` FAIL.

    NOTE on what this does and does NOT pin: ``_frontmatter`` catches the
    ``UnicodeDecodeError`` itself and returns ``{}``, so this fixture never
    reaches the per-project ``try/except`` in ``_check_chain_completeness``
    -- it passes with that isolation deleted. (An earlier revision of this
    docstring claimed otherwise; a follow-up review disproved it.) A LATER
    revision then redirected to the ``_board_lines`` tests below, which is also
    no longer true -- those triggers are caught per-station inside
    ``_board_lines`` itself now. This test is kept as an end-to-end guard on
    the degradation contract; the per-project catch-all is pinned directly by
    ``test_a_project_that_cannot_be_evaluated_at_all_warns_without_hiding_others``.
    """
    pa_alpha = _pa(tmp_path, "pyforge-alpha")
    _write_spec(pa_alpha / "specs" / "spec-foo" / "SPEC.md", "draft")  # real FAIL

    pa_beta = _pa(tmp_path, "pyforge-beta")
    bad_spec = pa_beta / "specs" / "spec-bar" / "SPEC.md"
    bad_spec.parent.mkdir(parents=True, exist_ok=True)
    bad_spec.write_bytes(b"---\nstatus: draft\n---\n\n\xe9 bad byte\n")  # malformed

    findings = board.gather_chain_completeness(tmp_path)

    by_check = {f.check: f for f in findings}
    assert "spec-not-decomposed" in by_check, (
        f"alpha's real FAIL was masked: {[(f.check, f.evidence.get('project')) for f in findings]}"
    )
    finding = by_check["spec-not-decomposed"]
    assert finding.status is DoctorStatus.FAIL
    assert finding.evidence["project"] == "pyforge-alpha"
    # beta's non-UTF-8 SPEC.md degrades to empty text → no status: key →
    # spec-status-missing (no longer a silent exemption).
    assert by_check.get("spec-status-missing") is not None
    assert by_check["spec-status-missing"].evidence["project"] == "pyforge-beta"


def test_non_dict_data_js_project_entry_does_not_crash_or_hide_other_findings(
    tmp_path: Path,
) -> None:
    """A malformed ``data.js`` entry (e.g. ``null``) for one station must not
    take down INV-C for a different, well-formed station."""
    pa_herald = _pa(tmp_path, "pyforge-herald")
    _write_ledger(pa_herald / "sprint-status-ledger.yaml", {"1-1-a": "done"})
    _write_data_js(
        tmp_path / "docs" / "dashboard" / "data.js",
        {
            "alpha": None,
            "herald": {"epics": [{"stories": [["1.1", "pending", "a"]]}]},
        },
    )

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "board-diverges-from-ledger"
    assert finding.evidence["subject"] == "herald"


# --- follow-up review regressions: masking via _board_lines ------------------
#
# These are the tests that genuinely exercise the per-project isolation. Each
# trigger below raised from INSIDE `_board_lines`, which is called at the top
# of `_check_chain_completeness` OUTSIDE the per-project try -- so the error
# reached the whole-gather `degrade_on_exception` and replaced every project's
# real FAIL with one vacuous WARN (exit 2 -> exit 0). All three reproduced
# live before the fix.


def _alpha_with_real_fail(tmp_path: Path) -> None:
    """One well-formed project owning a genuine INV-A violation."""
    _write_spec(_pa(tmp_path, "pyforge-alpha") / "specs" / "spec-foo" / "SPEC.md", "draft")


def _assert_alpha_fail_survives(tmp_path: Path) -> None:
    findings = board.gather_chain_completeness(tmp_path)
    assert [f.check for f in findings] == ["spec-not-decomposed"], (
        f"the real FAIL was masked: {[(f.check, f.status.value) for f in findings]}"
    )
    assert findings[0].status is DoctorStatus.FAIL
    assert findings[0].evidence["project"] == "pyforge-alpha"


def test_null_epic_entry_does_not_mask_another_projects_real_fail(tmp_path: Path) -> None:
    """A `null` in a station's `epics` list. The `isinstance(e, dict)` guard
    used to TRAIL the second `for`, where a comprehension never consults it
    before evaluating `e.get("stories")`."""
    _alpha_with_real_fail(tmp_path)
    _write_data_js(tmp_path / "docs" / "dashboard" / "data.js", {"beta": {"epics": [None]}})

    _assert_alpha_fail_survives(tmp_path)


def test_non_list_epics_value_does_not_mask_another_projects_real_fail(
    tmp_path: Path,
) -> None:
    """`epics` as a string: iterating it yields characters, not epic dicts."""
    _alpha_with_real_fail(tmp_path)
    _write_data_js(tmp_path / "docs" / "dashboard" / "data.js", {"beta": {"epics": "nope"}})

    _assert_alpha_fail_survives(tmp_path)


def test_non_mapping_projects_does_not_mask_another_projects_real_fail(
    tmp_path: Path,
) -> None:
    """`projects` as a list -- valid JSON, wrong shape, `.items()` explodes
    after `_board_lines`' own try/except has already closed."""
    data_js = tmp_path / "docs" / "dashboard" / "data.js"
    data_js.parent.mkdir(parents=True, exist_ok=True)
    data_js.write_text('window.DASHBOARD_DATA = {"projects": [1, 2, 3]};\n', encoding="utf-8")
    _alpha_with_real_fail(tmp_path)

    _assert_alpha_fail_survives(tmp_path)


# --- follow-up review regression: frontmatter scalar decoding ----------------


def test_quoted_open_status_is_still_treated_as_open(tmp_path: Path) -> None:
    """`status: 'draft'` must not silently exempt an undecomposed Spec. The
    hand-rolled parser replaced `yaml.safe_load`, which decoded the quotes."""
    _write_spec(_pa(tmp_path, "pyforge-alpha") / "specs" / "spec-foo" / "SPEC.md", "'draft'")

    _assert_alpha_fail_survives(tmp_path)


def test_inline_commented_open_status_is_still_treated_as_open(tmp_path: Path) -> None:
    """`status: draft  # still open` -- YAML reads the comment off; so must we."""
    _write_spec(
        _pa(tmp_path, "pyforge-alpha") / "specs" / "spec-foo" / "SPEC.md",
        "draft  # still open",
    )

    _assert_alpha_fail_survives(tmp_path)


def test_quoted_epics_role_still_selects_the_canonical_epics_doc(tmp_path: Path) -> None:
    """A quoted `epics_role: "canonical"` used to miss, dropping the doc and
    skipping INV-B/INV-D entirely."""
    pa = _pa(tmp_path, "pyforge-alpha")
    path = pa / "epics-v2.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '---\nepics_role: "canonical"\n---\n\n## Epic 1: E\n### Story 1.1: title\n',
        encoding="utf-8",
    )
    _write_ledger(pa / "sprint-status-ledger.yaml", {"9-9-orphan": "done"})

    findings = board.gather_chain_completeness(tmp_path)

    assert "ledger-key-without-story" in {f.check for f in findings}, (
        f"INV-B was skipped: {[f.check for f in findings]}"
    )


def test_scalar_decoding_does_not_over_strip_an_ordinary_value() -> None:
    """Only surrounding quotes and a real ` #` inline comment come off."""
    assert board._scalar("  draft  ") == "draft"
    assert board._scalar("'draft'") == "draft"
    assert board._scalar('"draft"') == "draft"
    assert board._scalar("draft # note") == "draft"
    assert board._scalar("issue#12") == "issue#12"  # no space -> not a comment
    assert board._scalar("it's") == "it's"  # unbalanced quote left alone
    assert board._scalar("") == ""


# --- adversarial-review regressions (2026-08-09, third pass) -----------------
#
# Every test below reproduces a defect a review pass found in `_board_lines`
# and `_scalar`, each confirmed by reverting the fix and watching the test
# fail. `_board_lines` runs OUTSIDE `_check_chain_completeness`'s own
# per-project try, so anything it raises escapes to the whole-gather
# `degrade_on_exception` and replaces EVERY project's real findings with one
# WARN -- turning exit 2 into exit 0. That is the shared consequence.


def _one_real_fail(target: Path) -> None:
    """A well-formed project carrying a genuine `spec-not-decomposed` FAIL --
    the finding each masking test below asserts does NOT disappear."""
    pa = _pa(target, "pyforge-good")
    _write_spec(pa / "specs" / "spec-orphan" / "SPEC.md", "draft")
    _write_epics_md(pa / "epics.md", ["1.1"])


def test_truthy_non_iterable_stories_does_not_hide_another_projects_finding(
    tmp_path: Path,
) -> None:
    """`{"stories": 7}` -- truthy, so `or ()` does not catch it, and not a
    list, so it raised `TypeError: 'int' object is not iterable` out of
    `_board_lines`. Reproduced live: the well-formed project's real FAIL
    vanished behind one `chain-completeness` WARN."""
    _one_real_fail(tmp_path)
    _write_data_js(
        tmp_path / "docs" / "dashboard" / "data.js",
        {"marshal": {"epics": [{"stories": 7}]}},
    )

    findings = board.gather_chain_completeness(tmp_path)

    assert "spec-not-decomposed" in {f.check for f in findings}, (
        f"a malformed board line masked a real finding: {[f.check for f in findings]}"
    )
    assert any(f.status is DoctorStatus.FAIL for f in findings)


def test_stories_as_a_mapping_does_not_hide_another_projects_finding(
    tmp_path: Path,
) -> None:
    """The same class one shape over: a mapping iterates to its KEYS, so this
    reached `len(s) > 1 and s[1]` with a string and raised there instead."""
    _one_real_fail(tmp_path)
    _write_data_js(
        tmp_path / "docs" / "dashboard" / "data.js",
        {"marshal": {"epics": [{"stories": {"1.1": "done"}}]}},
    )

    findings = board.gather_chain_completeness(tmp_path)

    assert "spec-not-decomposed" in {f.check for f in findings}, (
        f"a malformed board line masked a real finding: {[f.check for f in findings]}"
    )


def test_one_malformed_station_does_not_drop_a_well_formed_stations_board_line(
    tmp_path: Path,
) -> None:
    """Per-STATION isolation, not merely per-project: a broken `marshal` line
    must not cost `good` its INV-C comparison."""
    pa = _pa(tmp_path, "pyforge-good")
    _write_epics_md(pa / "epics.md", ["1.1", "1.2"])
    _write_ledger(pa / "sprint-status-ledger.yaml", {"1-1-a": "done", "1-2-b": "todo"})
    _write_data_js(
        tmp_path / "docs" / "dashboard" / "data.js",
        {
            "marshal": {"epics": 7},  # malformed
            "good": {"epics": [{"stories": [["1.1", "done"]]}]},  # 1 story vs 2 rows
        },
    )

    findings = board.gather_chain_completeness(tmp_path)

    inv_c = [f for f in findings if f.check == "board-diverges-from-ledger"]
    assert len(inv_c) == 1, f"INV-C was skipped for the healthy station: {findings}"
    assert inv_c[0].evidence["status"] == "board 1/1 vs ledger 1/2"


def test_empty_epics_list_is_skipped_exactly_as_the_original_skips_it(
    tmp_path: Path,
) -> None:
    """The original guards with `if not epics: continue`, so a well-formed
    `"epics": []` is a station it deliberately does not compare. Recording
    (0, 0) for it instead fired a false `board-diverges-from-ledger` -- a
    divergence on input the original handled cleanly, not one where it
    crashed."""
    pa = _pa(tmp_path, "pyforge-good")
    _write_epics_md(pa / "epics.md", ["1.1", "1.2"])
    _write_ledger(pa / "sprint-status-ledger.yaml", {"1-1-a": "done", "1-2-b": "todo"})
    _write_data_js(tmp_path / "docs" / "dashboard" / "data.js", {"good": {"epics": []}})

    findings = board.gather_chain_completeness(tmp_path)

    assert "board-diverges-from-ledger" not in {f.check for f in findings}, (
        f"an empty board line produced a false INV-C FAIL: {findings}"
    )


def test_an_empty_story_slot_still_counts_toward_the_boards_total(
    tmp_path: Path,
) -> None:
    """INV-C is a COUNT comparison, and the original counts an empty `[]`
    slot into the total (`len(s) > 1` already guards the done-count).
    Filtering it out shrank the denominator until a 3-slot board read as
    matching a 2-row ledger -- a false NEGATIVE."""
    pa = _pa(tmp_path, "pyforge-good")
    _write_epics_md(pa / "epics.md", ["1.1", "1.2"])
    _write_ledger(pa / "sprint-status-ledger.yaml", {"1-1-a": "done", "1-2-b": "todo"})
    _write_data_js(
        tmp_path / "docs" / "dashboard" / "data.js",
        {"good": {"epics": [{"stories": [["1.1", "done"], ["1.2", "todo"], []]}]}},
    )

    findings = board.gather_chain_completeness(tmp_path)

    inv_c = [f for f in findings if f.check == "board-diverges-from-ledger"]
    assert len(inv_c) == 1, f"INV-C missed a real 3-vs-2 divergence: {findings}"
    assert inv_c[0].evidence["status"] == "board 1/3 vs ledger 1/2"


def test_scalar_keeps_a_hash_that_lives_inside_quotes() -> None:
    """YAML treats `#` inside quotes as data. Stripping the comment BEFORE the
    quotes truncated `"a # b"` to `"a` -- a mis-decode of exactly the kind
    `_scalar` exists to prevent, with a stray quote left on the front."""
    assert board._scalar('"a # b"') == "a # b"
    assert board._scalar("'draft # x'") == "draft # x"
    assert board._scalar("'draft' # trailing note") == "draft"
    assert board._scalar('"draft"  # trailing note') == "draft"


# --- adversarial-review regressions (2026-08-09, fourth pass) ----------------


def test_non_utf8_ledger_does_not_discard_the_same_projects_own_finding(
    tmp_path: Path,
) -> None:
    """The per-project isolation protected every project EXCEPT the one that
    failed: `_check_project_chain_completeness` accumulated into a local list
    and returned it at the end, so a raise part-way through threw away the
    INV-A FAILs it had already computed for that very project.

    Trigger: `_ledger_rows` caught only `OSError`, but a non-UTF-8 byte raises
    `UnicodeDecodeError` -- a `ValueError`. Reproduced live: exit 2 -> exit 0.
    """
    pa = _pa(tmp_path, "pyforge-alpha")
    _write_spec(pa / "specs" / "spec-foo" / "SPEC.md", "draft")  # real INV-A FAIL
    (pa / "sprint-status-ledger.yaml").write_bytes(b"development_status:\n  1-1-a: done\n  \xe9bad: todo\n")

    findings = board.gather_chain_completeness(tmp_path)

    assert "spec-not-decomposed" in {f.check for f in findings}, (
        f"the project's own real FAIL was discarded: {[(f.check, f.status.value) for f in findings]}"
    )
    assert exit_code_for(findings) == 2


def test_non_utf8_epics_doc_does_not_discard_the_same_projects_own_finding(
    tmp_path: Path,
) -> None:
    """The same class through INV-A's own prose loop and
    `_story_ids_from_epics`, which also caught only `OSError`."""
    pa = _pa(tmp_path, "pyforge-alpha")
    _write_spec(pa / "specs" / "spec-foo" / "SPEC.md", "draft")
    (pa / "epics.md").write_bytes(b"---\nepics_role: canonical\n---\n\n\xe9 bad\n")
    _write_ledger(pa / "sprint-status-ledger.yaml", {"1-1-a": "done"})

    findings = board.gather_chain_completeness(tmp_path)

    assert "spec-not-decomposed" in {f.check for f in findings}, (
        f"the project's own real FAIL was discarded: {[f.check for f in findings]}"
    )


def test_a_project_that_cannot_be_evaluated_at_all_warns_without_hiding_others(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The per-project catch-all itself, pinned. Every NATURAL trigger a
    previous pass reached for is now swallowed further in (`_frontmatter`,
    `_ledger_rows` and `_story_ids_from_epics` all degrade on their own, and
    `_board_lines` guards per station), so the branch was reachable but
    exercised by nothing -- deleting it kept the whole suite green, which is
    how the isolation could silently regress. This drives it directly."""
    _write_spec(_pa(tmp_path, "pyforge-alpha") / "specs" / "spec-foo" / "SPEC.md", "draft")
    _pa(tmp_path, "pyforge-zbroken").mkdir(parents=True, exist_ok=True)

    real = board._check_project_chain_completeness

    def _explode(project_dir, board_lines, findings):
        if project_dir.name == "pyforge-zbroken":
            raise RuntimeError("unanticipated shape")
        return real(project_dir, board_lines, findings)

    monkeypatch.setattr(board, "_check_project_chain_completeness", _explode)

    findings = board.gather_chain_completeness(tmp_path)

    by_check = {f.check: f for f in findings}
    assert "spec-not-decomposed" in by_check, (
        f"one project's failure hid another's real FAIL: {[f.check for f in findings]}"
    )
    assert by_check["spec-not-decomposed"].status is DoctorStatus.FAIL
    warn = by_check["chain-completeness-unevaluable"]
    assert warn.status is DoctorStatus.WARN
    assert warn.evidence["project"] == "pyforge-zbroken"
    assert warn.evidence["inv"] == ""  # the catch wraps all four invariants
    assert exit_code_for(findings) == 2


def test_a_malformed_epic_entry_does_not_fabricate_a_zero_of_zero_divergence(
    tmp_path: Path,
) -> None:
    """A `null` epic entry used to be FILTERED out of the story comprehension,
    which quietly recorded `(0, 0)` for the station and fired a false
    `board-diverges-from-ledger` reading "board 0/0 vs ledger 1/2". A line
    this reader cannot interpret is "cannot compare this station", not a
    measured zero -- the same rule the empty-`epics` guard already encodes.
    """
    pa = _pa(tmp_path, "pyforge-good")
    _write_epics_md(pa / "epics.md", ["1.1", "1.2"])
    _write_ledger(pa / "sprint-status-ledger.yaml", {"1-1-a": "done", "1-2-b": "todo"})
    _write_data_js(tmp_path / "docs" / "dashboard" / "data.js", {"good": {"epics": [None]}})

    findings = board.gather_chain_completeness(tmp_path)

    assert "board-diverges-from-ledger" not in {f.check for f in findings}, (
        f"a malformed board line produced a fabricated INV-C FAIL: "
        f"{[(f.check, f.evidence.get('status')) for f in findings]}"
    )


def test_a_non_list_stories_value_does_not_fabricate_a_zero_of_zero_divergence(
    tmp_path: Path,
) -> None:
    """The same fabrication one shape over: `"stories": "1.1"` iterates to
    characters, every one of which the old `isinstance` filter dropped."""
    pa = _pa(tmp_path, "pyforge-good")
    _write_epics_md(pa / "epics.md", ["1.1", "1.2"])
    _write_ledger(pa / "sprint-status-ledger.yaml", {"1-1-a": "done", "1-2-b": "todo"})
    _write_data_js(
        tmp_path / "docs" / "dashboard" / "data.js",
        {"good": {"epics": [{"stories": "1.1"}]}},
    )

    findings = board.gather_chain_completeness(tmp_path)

    assert "board-diverges-from-ledger" not in {f.check for f in findings}, (
        f"a malformed board line produced a fabricated INV-C FAIL: {findings}"
    )


def test_an_unreadable_board_is_never_reported_as_agreement(tmp_path: Path) -> None:
    """`projects` present but not a mapping makes `_board_lines` return None,
    so INV-C is skipped for EVERY station -- and the OK finding still claimed
    "...and board agree" over a board it had never read, with nothing in
    `evidence` to tell a consumer apart. The sibling `_board_projects` refuses
    the identical bytes, so one data.js produced a confident OK here and an
    honest WARN in `gather_dashboard_drift`."""
    pa = _pa(tmp_path, "pyforge-good")
    _write_epics_md(pa / "epics.md", ["1.1"])
    _write_ledger(pa / "sprint-status-ledger.yaml", {"1-1-a": "done"})
    data_js = tmp_path / "docs" / "dashboard" / "data.js"
    data_js.parent.mkdir(parents=True, exist_ok=True)
    data_js.write_text('window.DASHBOARD_DATA = {"projects": [1, 2, 3]};\n', encoding="utf-8")

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.status is DoctorStatus.OK  # INV-A/B/D really did pass
    assert finding.evidence["board_read"] is False
    assert "INV-C was NOT evaluated" in finding.message
    assert "board agree" not in finding.message


def test_a_readable_board_still_says_so(tmp_path: Path) -> None:
    """The other side of the same flag -- it must not report every clean run
    as unread."""
    pa = _pa(tmp_path, "pyforge-good")
    _write_epics_md(pa / "epics.md", ["1.1"])
    _write_ledger(pa / "sprint-status-ledger.yaml", {"1-1-a": "done"})
    _write_data_js(
        tmp_path / "docs" / "dashboard" / "data.js",
        {"good": {"epics": [{"stories": [["1.1", "done"]]}]}},
    )

    findings = board.gather_chain_completeness(tmp_path)

    assert len(findings) == 1
    assert findings[0].evidence["board_read"] is True
    assert "board agree" in findings[0].message


def test_a_status_written_on_the_next_line_is_still_an_open_spec(tmp_path: Path) -> None:
    """`status:` with its value on the following indented line is valid YAML
    that `yaml.safe_load` decodes to "draft". The hand-rolled parser stored the
    value-less key as `""`, which fails the `OPEN_SPEC_STATUSES` test and
    silently EXEMPTS an open, undecomposed Spec -- the same false negative
    `_scalar` was added to close, through a different bit of YAML syntax."""
    path = _pa(tmp_path, "pyforge-alpha") / "specs" / "spec-foo" / "SPEC.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\nstatus:\n  draft\nowner-dream: docs/dreams/x.md\n---\n\nbody\n", encoding="utf-8")

    _assert_alpha_fail_survives(tmp_path)


def test_frontmatter_still_skips_real_block_openers() -> None:
    """The continuation read must not turn a list or a nested mapping into a
    scalar -- those are the shapes `_frontmatter` has always skipped."""
    assert board._continuation_scalar(["surface:", "  - src/a.py"], 0) is None
    assert board._continuation_scalar(["sources:", "  a: b"], 0) is None
    assert board._continuation_scalar(["status:", "next: x"], 0) is None
    assert board._continuation_scalar(["status:"], 0) is None
    assert board._continuation_scalar(["status:", "  draft"], 0) == "draft"
    assert board._continuation_scalar(["status:", "", "  'draft'"], 0) == "draft"
