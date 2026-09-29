"""Unit tests for ``pyforge.doctor.sources.chain.gather_dream_chain`` (Story
6.6) -- covers every row of the spec's I/O & Edge-Case Matrix that belongs to
the Dream-to-Code chain (INV-0..3) against REAL tmp fixture trees (Dreams,
Specs, sharded planning-artifacts directories), mirroring
``test_sources_board_chain_completeness.py``'s own real-fixture discipline.

Every invariant below was independently verified, during development, to
actually FIRE its own dedicated test: temporarily removing that invariant's
``findings.append(...)`` branch in ``sources/chain.py::_check_dream_chain``
(or, for INV-3, ``_check_project_sharded``) and re-running the single test
made it fail. That verification is not re-encoded as a permanent mutation
here -- see the story spec's own Tasks & Acceptance for the requirement.
"""

from __future__ import annotations

import json
from pathlib import Path

from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import chain

# --- fixture helpers ---------------------------------------------------------


def _write_roster(target: Path) -> None:
    path = target / "docs" / "governance" / "guild-roster.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "stations": [
                    "herald",
                    "marshal",
                    "atlas",
                    "warden",
                    "mason",
                    "doctor",
                    "scribe",
                    "steward",
                ],
                "guild_dreams": ["pyforge-charter"],
                "dream_statuses": [
                    "dreamt",
                    "pitched",
                    "specified",
                    "realized",
                    "archived",
                ],
                "dream_types": ["dream", "practice"],
            }
        ),
        encoding="utf-8",
    )


def _write_dream(target: Path, slug: str, owner: str, *, status: str = "draft", title: str = "") -> Path:
    path = target / "docs" / "dreams" / f"{slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---", f"owner: {owner}", f"status: {status}"]
    if title:
        lines.append(f"title: {title}")
    lines += ["---", "", "body"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _write_spec(
    target: Path,
    project: str,
    spec_dir: str,
    *,
    owner_dream: str | None = None,
    covers: list[str] | None = None,
    satellite: str | None = None,
) -> Path:
    path = target / "_bmad-output" / "projects" / project / "planning-artifacts" / "specs" / spec_dir / "SPEC.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---"]
    if owner_dream:
        lines.append(f"owner-dream: docs/dreams/{owner_dream}.md")
    if covers:
        lines.append("covers-dreams:")
        lines.extend(f"  - docs/dreams/{c}.md" for c in covers)
    lines.append("---")
    lines.append("")
    if satellite:
        lines.append(f"## Satellite: {satellite}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _write_sharded_project(
    target: Path, project: str, *, prd: bool = True, architecture: bool = True, epics: bool = True
) -> None:
    pa = target / "_bmad-output" / "projects" / project / "planning-artifacts"
    pa.mkdir(parents=True, exist_ok=True)
    if prd:
        prd_dir = pa / "prds" / "prd-x"
        prd_dir.mkdir(parents=True, exist_ok=True)
        (prd_dir / "prd.md").write_text("prd\n", encoding="utf-8")
    if architecture:
        arch_dir = pa / "architecture" / "architecture-x"
        arch_dir.mkdir(parents=True, exist_ok=True)
        (arch_dir / "architecture.md").write_text("arch\n", encoding="utf-8")
    if epics:
        (pa / "epics.md").write_text("# epics\n", encoding="utf-8")


def _clean_chain(target: Path) -> None:
    """A fully consistent one-Dream, one-Spec, one-sharded-project chain --
    the baseline every "does NOT fire" test starts from."""
    _write_dream(target, "foo", "doctor")
    _write_spec(target, "pyforge-doctor", "spec-foo", owner_dream="foo")
    _write_sharded_project(target, "pyforge-doctor")


# --- INV-0: every Spec declares owner-dream -----------------------------------


def test_spec_without_dream_link_reports_fail(tmp_path: Path) -> None:
    # `_write_spec` also creates the project's planning-artifacts directory,
    # which would independently trip INV-3 (not sharded) -- shard it here so
    # this test isolates INV-0 alone, matching every other single-invariant
    # test in this file.
    _write_spec(tmp_path, "pyforge-doctor", "spec-foo")  # no owner-dream
    _write_sharded_project(tmp_path, "pyforge-doctor")

    findings = chain.gather_dream_chain(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.DREAM_CHAIN
    assert finding.check == "spec-without-dream-link"
    assert finding.status is DoctorStatus.FAIL
    assert finding.evidence["inv"] == "INV-0"
    assert finding.evidence["subject"] == "spec-foo"
    assert "owner-dream" in finding.message


def test_spec_with_dream_link_reports_no_inv0_finding(tmp_path: Path) -> None:
    _clean_chain(tmp_path)

    findings = chain.gather_dream_chain(tmp_path)

    assert not any(f.check == "spec-without-dream-link" for f in findings)


# --- INV-1: every Dream has a Spec --------------------------------------------


def test_dream_without_spec_reports_fail(tmp_path: Path) -> None:
    _write_dream(tmp_path, "orphan", "doctor")

    findings = chain.gather_dream_chain(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "dream-without-spec"
    assert finding.status is DoctorStatus.FAIL
    assert finding.evidence["inv"] == "INV-1"
    assert finding.evidence["subject"] == "orphan"
    assert finding.evidence["owner"] == "doctor"


def test_dream_with_spec_reports_no_inv1_finding(tmp_path: Path) -> None:
    _clean_chain(tmp_path)

    findings = chain.gather_dream_chain(tmp_path)

    assert not any(f.check == "dream-without-spec" for f in findings)


def test_satellite_consolidation_via_covers_dreams_frontmatter_covers_the_dream(
    tmp_path: Path,
) -> None:
    """A consolidating Spec's ``covers-dreams:`` frontmatter satisfies INV-1
    for a Dream whose whole chain was folded in -- no Spec of its own."""
    _write_dream(tmp_path, "satellite-a", "doctor")
    _write_dream(tmp_path, "host", "doctor")
    _write_spec(
        tmp_path,
        "pyforge-doctor",
        "spec-host",
        owner_dream="host",
        covers=["satellite-a"],
    )

    findings = chain.gather_dream_chain(tmp_path)

    assert not any(f.check == "dream-without-spec" for f in findings)


def test_satellite_consolidation_via_heading_covers_the_dream(tmp_path: Path) -> None:
    """The fallback mechanism: a ``## Satellite: <Title>`` heading matching
    the Dream's own ``title:`` covers it without a ``covers-dreams:``
    declaration."""
    _write_dream(tmp_path, "satellite-b", "doctor", title="The Satellite Dream")
    _write_dream(tmp_path, "host2", "doctor")
    _write_spec(
        tmp_path,
        "pyforge-doctor",
        "spec-host2",
        owner_dream="host2",
        satellite="The Satellite Dream",
    )

    findings = chain.gather_dream_chain(tmp_path)

    assert not any(f.check == "dream-without-spec" for f in findings)


# --- INV-2a: owner-unassigned (guild, non-constitutive) -----------------------


def test_owner_unassigned_guild_dream_reports_fail(tmp_path: Path) -> None:
    _write_dream(tmp_path, "unassigned", "guild")

    findings = chain.gather_dream_chain(tmp_path)

    kinds = {f.check for f in findings}
    assert "owner-unassigned" in kinds
    finding = next(f for f in findings if f.check == "owner-unassigned")
    assert finding.status is DoctorStatus.FAIL
    assert finding.evidence["inv"] == "INV-2"
    assert finding.evidence["owner"] == "guild"


def test_constitutive_guild_dream_is_exempt(tmp_path: Path) -> None:
    """``pyforge-charter`` is the one Dream ``guild`` is terminal for."""
    _write_dream(tmp_path, "pyforge-charter", "guild")
    _write_spec(tmp_path, "docs/governance", "spec-pyforge-charter", owner_dream="pyforge-charter")

    findings = chain.gather_dream_chain(tmp_path)

    assert not any(f.check == "owner-unassigned" for f in findings)


# --- INV-2: the chain lives where its owner lives ------------------------------


def test_spec_location_mismatch_reports_fail(tmp_path: Path) -> None:
    _write_dream(tmp_path, "foo", "doctor")
    _write_spec(tmp_path, "pyforge-wrongplace", "spec-foo", owner_dream="foo")

    findings = chain.gather_dream_chain(tmp_path)

    kinds = {f.check for f in findings}
    assert "spec-location-mismatch" in kinds
    finding = next(f for f in findings if f.check == "spec-location-mismatch")
    assert finding.status is DoctorStatus.FAIL
    assert finding.evidence["inv"] == "INV-2"
    assert finding.evidence["owner"] == "doctor"
    assert "pyforge-wrongplace" in finding.message


def test_spec_in_owners_project_reports_no_location_mismatch(tmp_path: Path) -> None:
    _clean_chain(tmp_path)

    findings = chain.gather_dream_chain(tmp_path)

    assert not any(f.check == "spec-location-mismatch" for f in findings)


def test_guild_owned_spec_lives_in_docs_governance(tmp_path: Path) -> None:
    _write_dream(tmp_path, "pyforge-charter", "guild")
    _write_spec(tmp_path, "docs/governance", "spec-pyforge-charter", owner_dream="pyforge-charter")

    findings = chain.gather_dream_chain(tmp_path)

    assert not any(f.check == "spec-location-mismatch" for f in findings)


# --- INV-3: sharded build tree --------------------------------------------------


def test_flat_prd_reports_prd_not_sharded_fail(tmp_path: Path) -> None:
    _clean_chain(tmp_path)
    pa = tmp_path / "_bmad-output" / "projects" / "pyforge-doctor" / "planning-artifacts"
    import shutil

    shutil.rmtree(pa / "prds")
    (pa / "prd.md").write_text("flat\n", encoding="utf-8")

    findings = chain.gather_dream_chain(tmp_path)

    kinds = {f.check for f in findings}
    assert "prd-not-sharded" in kinds
    finding = next(f for f in findings if f.check == "prd-not-sharded")
    assert finding.status is DoctorStatus.FAIL
    assert finding.evidence["inv"] == "INV-3"
    assert finding.evidence["status"] == "flat prd.md"


def test_absent_prd_reports_prd_not_sharded_fail(tmp_path: Path) -> None:
    _clean_chain(tmp_path)
    import shutil

    shutil.rmtree(tmp_path / "_bmad-output" / "projects" / "pyforge-doctor" / "planning-artifacts" / "prds")

    findings = chain.gather_dream_chain(tmp_path)

    finding = next(f for f in findings if f.check == "prd-not-sharded")
    assert finding.evidence["status"] == "absent"


def test_flat_architecture_reports_fail(tmp_path: Path) -> None:
    _clean_chain(tmp_path)
    pa = tmp_path / "_bmad-output" / "projects" / "pyforge-doctor" / "planning-artifacts"
    import shutil

    shutil.rmtree(pa / "architecture")
    (pa / "architecture.md").write_text("flat\n", encoding="utf-8")

    findings = chain.gather_dream_chain(tmp_path)

    kinds = {f.check for f in findings}
    assert "architecture-not-sharded" in kinds
    finding = next(f for f in findings if f.check == "architecture-not-sharded")
    assert finding.status is DoctorStatus.FAIL
    assert finding.evidence["inv"] == "INV-3"
    assert finding.evidence["status"] == "flat architecture.md"


def test_missing_epics_reports_fail(tmp_path: Path) -> None:
    _clean_chain(tmp_path)
    (tmp_path / "_bmad-output" / "projects" / "pyforge-doctor" / "planning-artifacts" / "epics.md").unlink()

    findings = chain.gather_dream_chain(tmp_path)

    kinds = {f.check for f in findings}
    assert "epics-missing" in kinds
    finding = next(f for f in findings if f.check == "epics-missing")
    assert finding.status is DoctorStatus.FAIL
    assert finding.evidence["inv"] == "INV-3"


# --- Clean chain: one OK Finding -----------------------------------------------


def test_clean_chain_reports_ok(tmp_path: Path) -> None:
    _clean_chain(tmp_path)

    findings = chain.gather_dream_chain(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.DREAM_CHAIN
    assert finding.check == "dream-chain"
    assert finding.status is DoctorStatus.OK
    assert finding.evidence == {"dreams": 1, "specs": 1}


def test_project_tree_with_no_dreams_dir_still_reports_ok(tmp_path: Path) -> None:
    """A monorepo root that HAS a projects tree but no Dreams yet is a real,
    evaluable state -- the confident OK is honest here (contrast with
    ``test_target_with_neither_input_tree_reports_unevaluable_warn``)."""
    _write_sharded_project(tmp_path, "pyforge-doctor")

    findings = chain.gather_dream_chain(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK
    assert findings[0].evidence == {"dreams": 0, "specs": 0}


def test_target_with_neither_input_tree_reports_unevaluable_warn(
    tmp_path: Path,
) -> None:
    """A target holding neither ``docs/dreams/`` nor ``_bmad-output/projects/``
    is not a monorepo root -- the shape `doctor check`'s own ``path="."``
    default takes when it is run from a SUBDIRECTORY. Claiming "every Dream
    has a Spec" there is a clean bill of health for a question never asked,
    so this must WARN rather than report the vacuous OK (mirrors
    ``sources/ledger.py``'s own honest "cannot be evaluated" WARN)."""
    findings = chain.gather_dream_chain(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.DREAM_CHAIN
    assert finding.check == "dream-chain-unevaluable"
    assert finding.status is DoctorStatus.WARN
    assert finding.evidence == {"target": str(tmp_path)}


# --- Never raises ---------------------------------------------------------------


def test_non_utf8_dream_frontmatter_surfaces_unparseable_finding(tmp_path: Path) -> None:
    dream = tmp_path / "docs" / "dreams" / "bad.md"
    dream.parent.mkdir(parents=True, exist_ok=True)
    dream.write_bytes(b"---\nowner: doctor\ntitle: caf\xe9\n---\n\nbody\n")

    findings = chain.gather_dream_chain(tmp_path)

    assert findings
    assert all(f.source is Source.DREAM_CHAIN for f in findings)
    unparsed = next(f for f in findings if f.check == "unparseable-frontmatter")
    assert unparsed.status is DoctorStatus.WARN
    assert unparsed.evidence["subject"] == "bad"


def test_non_dict_frontmatter_surfaces_unparseable_finding(tmp_path: Path) -> None:
    """A frontmatter block that parses to a YAML list (structurally valid,
    wrong shape) must surface as ``unparseable-frontmatter``, never silently
    degrade to absent metadata."""
    dream = tmp_path / "docs" / "dreams" / "listlike.md"
    dream.parent.mkdir(parents=True, exist_ok=True)
    dream.write_text("---\n- just\n- a\n- list\n---\n\nbody\n", encoding="utf-8")

    findings = chain.gather_dream_chain(tmp_path)

    unparsed = next(f for f in findings if f.check == "unparseable-frontmatter")
    assert unparsed.status is DoctorStatus.WARN
    assert unparsed.evidence["subject"] == "listlike"


# --- Multi-project isolation: INV-3 -------------------------------------------


def test_multiple_projects_inv3_findings_are_all_reported_independently(
    tmp_path: Path,
) -> None:
    _write_sharded_project(tmp_path, "pyforge-alpha", epics=False)
    _write_sharded_project(tmp_path, "pyforge-beta", epics=False)

    findings = chain.gather_dream_chain(tmp_path)

    epics_findings = [f for f in findings if f.check == "epics-missing"]
    assert {f.evidence["subject"] for f in epics_findings} == {
        "pyforge-alpha",
        "pyforge-beta",
    }


def test_one_unevaluable_project_does_not_hide_another_projects_real_fail(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """One project's ``planning-artifacts`` directory that cannot be listed
    must not discard a DIFFERENT, well-formed project's real INV-3 FAIL --
    the isolation Design Notes calls for, structured in from the first draft
    rather than rediscovered across review passes (mirrors
    ``sources/board.py``'s own ``test_a_project_that_cannot_be_evaluated_at_all_
    warns_without_hiding_others``)."""
    _write_sharded_project(tmp_path, "pyforge-good", epics=False)  # real epics-missing
    (tmp_path / "_bmad-output" / "projects" / "pyforge-zbroken" / "planning-artifacts").mkdir(
        parents=True, exist_ok=True
    )

    real = chain._check_project_sharded

    def _explode(pdir, findings):
        if pdir.parent.name == "pyforge-zbroken":
            raise RuntimeError("unanticipated shape")
        return real(pdir, findings)

    monkeypatch.setattr(chain, "_check_project_sharded", _explode)

    findings = chain.gather_dream_chain(tmp_path)

    by_check = {f.check: f for f in findings}
    assert "epics-missing" in by_check, f"one project's failure hid another's real FAIL: {[f.check for f in findings]}"
    assert by_check["epics-missing"].status is DoctorStatus.FAIL
    warn = by_check["dream-chain-unevaluable"]
    assert warn.status is DoctorStatus.WARN
    assert warn.evidence["subject"] == "pyforge-zbroken"


def test_non_string_dream_title_does_not_hide_another_dreams_real_fail(
    tmp_path: Path,
) -> None:
    """``title:`` with no value parses to YAML ``null`` and ``title: 2026`` to
    an ``int``; both reach ``_normalize_title``'s ``.lower()`` in
    ``_check_dream_chain``'s satellite loop -- which runs over ALREADY-
    COLLECTED in-memory data and so sits outside every per-unit try/except in
    the module. Reproduced live during review: the ``AttributeError`` escaped
    to ``degrade_on_exception`` and replaced an unrelated Dream's real
    ``dream-without-spec`` FAIL with one vacuous WARN. The loop only runs at
    all when some Spec carries a ``## Satellite:`` heading, so the fixture
    below needs one. Regression: the real FAILs now survive."""
    _write_dream(tmp_path, "orphan", "doctor")  # real dream-without-spec FAIL
    (tmp_path / "docs" / "dreams" / "nulltitle.md").write_text(
        "---\nowner: doctor\nstatus: draft\ntitle:\n---\n\nbody\n", encoding="utf-8"
    )
    (tmp_path / "docs" / "dreams" / "inttitle.md").write_text(
        "---\nowner: doctor\nstatus: draft\ntitle: 2026\n---\n\nbody\n",
        encoding="utf-8",
    )
    _write_dream(tmp_path, "host", "doctor")
    _write_spec(
        tmp_path,
        "pyforge-doctor",
        "spec-host",
        owner_dream="host",
        satellite="Some Other Dream",
    )
    _write_sharded_project(tmp_path, "pyforge-doctor")

    findings = chain.gather_dream_chain(tmp_path)

    subjects = {f.evidence["subject"] for f in findings if f.check == "dream-without-spec"}
    assert "orphan" in subjects, (
        f"a non-string Dream title collapsed every real finding: {[(f.check, f.status) for f in findings]}"
    )
    # The two malformed-title Dreams are themselves spec-less, so they FAIL
    # on their own merits -- what matters is that they FAIL rather than crash.
    assert {"nulltitle", "inttitle"} <= subjects


def test_one_malformed_spec_does_not_hide_another_specs_real_fail(
    tmp_path: Path,
) -> None:
    """A SPEC.md whose ``owner-dream:`` is written as a YAML list (a
    plausible typo next to the legitimately-list-shaped ``covers-dreams:``)
    parses cleanly via ``yaml.safe_load`` and then raises ``AttributeError``
    out of ``_spec_entry``'s own ``.split("/")`` call -- reproduced live
    during review, where this collapsed a well-formed, unrelated Dream's real
    ``dream-without-spec`` FAIL behind one vacuous WARN. Regression for that
    fix: the malformed spec now degrades to its own WARN while the real FAIL
    for the untouched Dream survives in the same run."""
    _write_dream(tmp_path, "orphan", "doctor")  # real dream-without-spec FAIL
    _write_sharded_project(tmp_path, "pyforge-doctor")
    bad_spec = (
        tmp_path
        / "_bmad-output"
        / "projects"
        / "pyforge-doctor"
        / "planning-artifacts"
        / "specs"
        / "spec-malformed"
        / "SPEC.md"
    )
    bad_spec.parent.mkdir(parents=True, exist_ok=True)
    bad_spec.write_text("---\nowner-dream:\n  - docs/dreams/foo.md\n---\nbody\n", encoding="utf-8")

    findings = chain.gather_dream_chain(tmp_path)

    by_check = {f.check: f for f in findings}
    assert "dream-without-spec" in by_check, (
        f"the malformed spec hid the unrelated dream's real FAIL: {[f.check for f in findings]}"
    )
    assert by_check["dream-without-spec"].status is DoctorStatus.FAIL
    assert by_check["dream-without-spec"].evidence["subject"] == "orphan"
    warn = by_check["dream-chain-unevaluable"]
    assert warn.status is DoctorStatus.WARN
    assert warn.evidence["subject"] == "spec-malformed"


# --- Unreadable input directories ------------------------------------------------
#
# `Path.glob` swallows `OSError` mid-traversal and yields nothing, so an
# unreadable input directory used to be indistinguishable from an empty one --
# and "empty" reads as a clean chain. These pin the honest degradation.


def test_unreadable_dreams_dir_is_unevaluable_not_a_clean_chain(
    tmp_path: Path,
) -> None:
    """``chmod 000 docs/dreams/`` must not read as "there are no Dreams", which
    the confident OK would then report as a clean chain. Reproduced during
    review: a real ``dream-without-spec`` FAIL vanished behind ``dream-chain
    ok``."""
    _write_dream(tmp_path, "orphan", "doctor")
    _write_sharded_project(tmp_path, "pyforge-doctor")
    dreams_dir = tmp_path / "docs" / "dreams"
    dreams_dir.chmod(0o000)
    try:
        findings = chain.gather_dream_chain(tmp_path)
    finally:
        dreams_dir.chmod(0o755)

    # The whole-gather `degrade_on_exception` fallback keeps `check` at the
    # source's own label, so the OK is told apart by STATUS, not by name.
    assert not any(f.status is DoctorStatus.OK for f in findings), (
        f"an unreadable dreams/ was reported as a clean chain: {findings}"
    )
    assert [f.status for f in findings] == [DoctorStatus.WARN]
    assert "PermissionError" in findings[0].message


def test_one_projects_unlistable_specs_dir_does_not_hide_another_projects_finding(
    tmp_path: Path,
) -> None:
    """An unreadable ``planning-artifacts/specs/`` degrades to a WARN naming
    THAT project only -- it must neither silently read as "this project has no
    Specs" (which INV-1 would report as its Dreams being spec-less) nor
    discard another project's real finding."""
    _write_dream(tmp_path, "orphan", "doctor")
    _write_sharded_project(tmp_path, "pyforge-doctor")
    _write_sharded_project(tmp_path, "pyforge-mason")
    blind = tmp_path / "_bmad-output" / "projects" / "pyforge-mason" / "planning-artifacts" / "specs"
    blind.mkdir(parents=True, exist_ok=True)
    blind.chmod(0o000)
    try:
        findings = chain.gather_dream_chain(tmp_path)
    finally:
        blind.chmod(0o755)

    by_check = {f.check: f for f in findings}
    assert "dream-without-spec" in by_check, (
        f"one project's unreadable specs/ hid an unrelated real FAIL: {[f.check for f in findings]}"
    )
    warn = by_check["dream-chain-unevaluable"]
    assert warn.status is DoctorStatus.WARN
    assert "pyforge-mason" in warn.message


def test_empty_dreams_dir_with_no_project_tree_is_unevaluable(
    tmp_path: Path,
) -> None:
    """The unevaluable guard tests what was COLLECTED, not merely whether both
    directories exist: a present-but-empty ``docs/dreams/`` alongside no
    projects tree passed the old both-must-be-missing test and still produced
    the confident OK, asserting "every project uses the sharded planning tree"
    about zero projects."""
    (tmp_path / "docs" / "dreams").mkdir(parents=True)
    (tmp_path / "docs" / "dreams" / "README.md").write_text("x\n", encoding="utf-8")

    findings = chain.gather_dream_chain(tmp_path)

    assert [f.check for f in findings] == ["dream-chain-unevaluable"]
    assert findings[0].status is DoctorStatus.WARN
    assert findings[0].source is Source.DREAM_CHAIN


# --- Ported branches that survived mutation (review pass 4) -----------------------
#
# Each test below pins a ported branch that the suite did NOT previously kill
# under mutation, which the story's own Acceptance Criteria require ("a
# mutation of that invariant's branch makes the corresponding test fail").
# Every one was mutation-confirmed when written.


def test_guild_spec_is_collected_from_docs_governance(tmp_path: Path) -> None:
    """The REAL governance-Spec location -- ``docs/governance/spec-<slug>/``,
    not a project under ``_bmad-output/projects/``.

    ``_collect_specs``'s governance loop had no coverage at all: the two
    existing guild tests call ``_write_spec(target, "docs/governance", ...)``,
    which lands at ``_bmad-output/projects/docs/governance/...`` -- a path the
    gather never walks -- and then assert the ABSENCE of a finding, which a
    never-collected Spec satisfies trivially. Deleting the whole governance
    loop left them green."""
    _write_roster(tmp_path)
    _write_dream(tmp_path, "pyforge-charter", "guild")
    sd = tmp_path / "docs" / "governance" / "spec-pyforge-charter"
    sd.mkdir(parents=True)
    (sd / "SPEC.md").write_text("---\nowner-dream: docs/dreams/pyforge-charter.md\n---\n", encoding="utf-8")

    findings = chain.gather_dream_chain(tmp_path)

    assert [f.check for f in findings] == ["dream-chain"], (
        f"the guild Spec in docs/governance/ was not collected: {findings}"
    )


def test_guild_dream_remedy_names_the_flat_governance_path(tmp_path: Path) -> None:
    """``_expected_spec_dir``'s guild branch: ``docs/governance/`` holds
    ``spec-<slug>/`` DIRECTLY, with no ``planning-artifacts/specs/`` nesting.
    Deleting that branch sent guild Dreams the Smith-shaped nested remedy and
    no test noticed."""
    _write_dream(tmp_path, "pyforge-charter", "guild")

    findings = chain.gather_dream_chain(tmp_path)

    remedy = next(f for f in findings if f.check == "dream-without-spec").evidence["remedy"]
    assert remedy == "author a Spec under docs/governance/spec-pyforge-charter/", remedy


def test_unlinked_spec_matching_a_dream_slug_is_not_also_dream_without_spec(
    tmp_path: Path,
) -> None:
    """INV-1's slug fallback. The original records why it exists: without it
    a Spec that merely forgot ``owner-dream:`` is counted TWICE -- once as
    ``spec-without-dream-link`` (correct) and again as its Dream being
    spec-less (wrong; the Spec is right there)."""
    _write_dream(tmp_path, "foo", "doctor")
    _write_spec(tmp_path, "pyforge-doctor", "spec-foo")  # no owner-dream

    checks = [f.check for f in chain.gather_dream_chain(tmp_path)]

    assert "spec-without-dream-link" in checks
    assert "dream-without-spec" not in checks, (
        f"an unlinked Spec whose slug matches its Dream was double-counted: {checks}"
    )


def test_satellite_heading_matches_across_punctuation_drift(tmp_path: Path) -> None:
    """``_normalize_title`` lowercases and strips punctuation so a
    consolidating Spec's ``## Satellite:`` heading still matches a Dream's
    own ``title:`` through ordinary wording drift -- the whole point of
    normalizing rather than comparing raw strings. Every existing satellite
    test used titles that matched exactly, so dropping either transform
    changed nothing.

    Note the tolerance is punctuation-and-case only, NOT whitespace: stripping
    a SPACE-DELIMITED hyphen leaves a double space, so ``A - B`` does not
    match ``A B``. This test pins the behaviour that exists, not a wider
    one."""
    _write_dream(tmp_path, "sat", "doctor", title="The Seed (Part 1)")
    _write_dream(tmp_path, "host", "doctor")
    _write_spec(tmp_path, "pyforge-doctor", "spec-host", owner_dream="host", satellite="the SEED part 1")

    subjects = {f.evidence["subject"] for f in chain.gather_dream_chain(tmp_path) if f.check == "dream-without-spec"}

    assert "sat" not in subjects, f"punctuation drift broke satellite matching: {subjects}"


def test_markdown_without_a_leading_frontmatter_fence_is_absent_not_unparseable(
    tmp_path: Path,
) -> None:
    """A complete ``---``/YAML/``---`` block displaced below prose -- no
    leading opener -- is absent metadata, not malformed frontmatter
    (Story 28.1 / CAP-81): ``_frontmatter_parse`` requires the opening
    fence to be LINE-ANCHORED on the very first line of the document, so
    prose preceding a ``---``-delimited block is simply a Dream with no
    recognized frontmatter at all -- same as any other Dream missing it --
    and reports ``dream-without-spec`` (owner unknown) rather than an
    elevated ``unparseable-frontmatter`` WARN.

    Story 28.1's Always clause ("a prose file with a ``---`` rule and no
    leading fence is ``({}, False)``") supersedes the Story 17-1 / FR-144
    pin this exact fixture used to carry. That story's concern -- a
    malformed block must not silently masquerade as ``owner: (none)`` --
    still holds for a block that legitimately OPENS with ``---`` but never
    closes, and for an attempted-but-unbounded opener such as a glued
    ``---title:`` (see ``test_sources_chain_frontmatter_parse.py``); it no
    longer extends to a ``---`` that merely appears somewhere in the body
    with no leading fence."""
    path = tmp_path / "docs" / "dreams" / "nofence.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        "Prose that precedes the fence.\n---\nowner: marshal\nstatus: shipped\n---\n",
        encoding="utf-8",
    )

    findings = chain.gather_dream_chain(tmp_path)
    checks = {f.check for f in findings}

    assert "unparseable-frontmatter" not in checks
    assert "dream-without-spec" in checks
    gap = next(f for f in findings if f.check == "dream-without-spec")
    assert gap.evidence["subject"] == "nofence"
    assert gap.evidence["owner"] == "(none)"


def test_spec_unparseable_frontmatter_does_not_report_spec_without_owner_dream(
    tmp_path: Path,
) -> None:
    """The 2026-07-28 INV-0 incident: unparseable Spec frontmatter must not
    masquerade as a missing ``owner-dream:`` HARD finding."""
    _write_dream(tmp_path, "host", "doctor")
    spec = (
        tmp_path
        / "_bmad-output"
        / "projects"
        / "pyforge-doctor"
        / "planning-artifacts"
        / "specs"
        / "spec-broken"
        / "SPEC.md"
    )
    spec.parent.mkdir(parents=True, exist_ok=True)
    spec.write_text("---\n- not\n- a\n- mapping\n---\n", encoding="utf-8")
    _write_sharded_project(tmp_path, "pyforge-doctor")

    findings = chain.gather_dream_chain(tmp_path)
    checks = {f.check for f in findings}

    assert "unparseable-frontmatter" in checks
    assert "spec-without-owner-dream" not in checks


# --- Unreadable input trees must not discard unrelated findings -------------------


def test_unreadable_dreams_dir_does_not_discard_unrelated_inv3_findings(
    tmp_path: Path,
) -> None:
    """``docs/dreams/`` is not an input to INV-3 at all, so an unreadable one
    must not take INV-3's findings down with it.

    ``_listdir``'s ``PermissionError`` used to escape ``_collect_dreams``
    entirely, past ``_check_dream_chain``, to the outer
    ``degrade_on_exception`` -- reproduced live during review: three real
    ``prd-not-sharded``/``architecture-not-sharded``/``epics-missing`` FAILs
    plus a ``dream-without-spec`` FAIL collapsed into one vacuous WARN. That
    is the story's own AC inverted."""
    _write_dream(tmp_path, "orphan", "doctor")
    _write_sharded_project(tmp_path, "pyforge-mason", prd=False, architecture=False, epics=False)

    dreams_dir = tmp_path / "docs" / "dreams"
    dreams_dir.chmod(0o000)
    try:
        findings = chain.gather_dream_chain(tmp_path)
    finally:
        dreams_dir.chmod(0o755)

    checks = [f.check for f in findings]
    assert "prd-not-sharded" in checks and "epics-missing" in checks, (
        f"an unreadable docs/dreams/ discarded unrelated INV-3 FAILs: {checks}"
    )
    warn = next(f for f in findings if f.check == "dream-chain-unevaluable")
    assert warn.status is DoctorStatus.WARN
    assert "docs/dreams/" in warn.message


def test_unreadable_docs_parent_is_a_warn_not_a_silent_zero(tmp_path: Path) -> None:
    """``Path.is_dir()`` answers ``False`` for an unreadable ANCESTOR, so
    ``chmod 000 docs/`` used to zero every Dream silently and a real
    ``dream-without-spec`` FAIL simply vanished -- no WARN, no trace. The
    ``_listdir`` honesty rule only covered LISTING; ``_is_dir`` extends it to
    the existence probe that decides whether to list."""
    _write_dream(tmp_path, "orphan", "doctor")
    _write_sharded_project(tmp_path, "pyforge-mason")

    docs = tmp_path / "docs"
    docs.chmod(0o000)
    try:
        findings = chain.gather_dream_chain(tmp_path)
    finally:
        docs.chmod(0o755)

    # Named specifically: `docs/governance/` is unreadable for the same
    # reason and reports its own WARN, so a bare "some WARN exists" assertion
    # passes even when the Dreams probe silently answers "absent".
    messages = [f.message for f in findings if f.check == "dream-chain-unevaluable"]
    assert any("docs/dreams/" in m for m in messages), (
        f"an unreadable docs/ zeroed the Dreams with no WARN naming them: {messages}"
    )
    assert all(f.status is DoctorStatus.WARN for f in findings)


def test_unreadable_spec_dir_names_the_project_not_the_literal_specs_dir(
    tmp_path: Path,
) -> None:
    """Two projects with unreadable ``specs/`` directories must be tellable
    apart by a machine consumer: every project's is literally named
    ``specs``, so keying ``evidence["subject"]`` on the directory name made
    both WARNs identical."""
    _write_dream(tmp_path, "foo", "doctor")
    for project in ("pyforge-doctor", "pyforge-mason"):
        sd = _write_spec(tmp_path, project, "spec-foo", owner_dream="foo").parent
        sd.parent.chmod(0o000)
    try:
        findings = chain.gather_dream_chain(tmp_path)
    finally:
        for project in ("pyforge-doctor", "pyforge-mason"):
            (tmp_path / "_bmad-output" / "projects" / project / "planning-artifacts" / "specs").chmod(0o755)

    subjects = {f.evidence["subject"] for f in findings if f.check == "dream-chain-unevaluable"}
    assert subjects == {"pyforge-doctor", "pyforge-mason"}, subjects
