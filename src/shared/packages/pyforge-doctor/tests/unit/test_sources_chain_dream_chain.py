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

from pathlib import Path

from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import chain

# --- fixture helpers ---------------------------------------------------------


def _write_dream(
    target: Path, slug: str, owner: str, *, status: str = "draft", title: str = ""
) -> Path:
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
    path = (
        target / "_bmad-output" / "projects" / project / "planning-artifacts"
        / "specs" / spec_dir / "SPEC.md"
    )
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
        tmp_path, "pyforge-doctor", "spec-host",
        owner_dream="host", covers=["satellite-a"],
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
        tmp_path, "pyforge-doctor", "spec-host2",
        owner_dream="host2", satellite="The Satellite Dream",
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
    _write_spec(tmp_path, "docs/governance", "spec-pyforge-charter",
                owner_dream="pyforge-charter")

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
    _write_spec(tmp_path, "docs/governance", "spec-pyforge-charter",
                owner_dream="pyforge-charter")

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
    shutil.rmtree(
        tmp_path / "_bmad-output" / "projects" / "pyforge-doctor"
        / "planning-artifacts" / "prds"
    )

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
    (
        tmp_path / "_bmad-output" / "projects" / "pyforge-doctor"
        / "planning-artifacts" / "epics.md"
    ).unlink()

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


def test_non_utf8_dream_frontmatter_never_raises(tmp_path: Path) -> None:
    dream = tmp_path / "docs" / "dreams" / "bad.md"
    dream.parent.mkdir(parents=True, exist_ok=True)
    dream.write_bytes(b"---\nowner: doctor\ntitle: caf\xe9\n---\n\nbody\n")

    findings = chain.gather_dream_chain(tmp_path)

    assert findings  # returned rather than raised
    assert all(f.source is Source.DREAM_CHAIN for f in findings)


def test_non_dict_frontmatter_never_raises(tmp_path: Path) -> None:
    """A frontmatter block that parses to a YAML list (structurally valid,
    wrong shape) must degrade to ``{}`` rather than raising ``AttributeError``
    on the first ``.get()`` call."""
    dream = tmp_path / "docs" / "dreams" / "listlike.md"
    dream.parent.mkdir(parents=True, exist_ok=True)
    dream.write_text("---\n- just\n- a\n- list\n---\n\nbody\n", encoding="utf-8")

    findings = chain.gather_dream_chain(tmp_path)

    assert findings
    assert all(f.source is Source.DREAM_CHAIN for f in findings)


# --- Multi-project isolation: INV-3 -------------------------------------------


def test_multiple_projects_inv3_findings_are_all_reported_independently(
    tmp_path: Path,
) -> None:
    _write_sharded_project(tmp_path, "pyforge-alpha", epics=False)
    _write_sharded_project(tmp_path, "pyforge-beta", epics=False)

    findings = chain.gather_dream_chain(tmp_path)

    epics_findings = [f for f in findings if f.check == "epics-missing"]
    assert {f.evidence["subject"] for f in epics_findings} == {
        "pyforge-alpha", "pyforge-beta",
    }


def test_one_unevaluable_project_does_not_hide_another_projects_real_fail(
    tmp_path: Path, monkeypatch,
) -> None:
    """One project's ``planning-artifacts`` directory that cannot be listed
    must not discard a DIFFERENT, well-formed project's real INV-3 FAIL --
    the isolation Design Notes calls for, structured in from the first draft
    rather than rediscovered across review passes (mirrors
    ``sources/board.py``'s own ``test_a_project_that_cannot_be_evaluated_at_all_
    warns_without_hiding_others``)."""
    _write_sharded_project(tmp_path, "pyforge-good", epics=False)  # real epics-missing
    (
        tmp_path / "_bmad-output" / "projects" / "pyforge-zbroken"
        / "planning-artifacts"
    ).mkdir(parents=True, exist_ok=True)

    real = chain._check_project_sharded

    def _explode(pdir, findings):
        if pdir.parent.name == "pyforge-zbroken":
            raise RuntimeError("unanticipated shape")
        return real(pdir, findings)

    monkeypatch.setattr(chain, "_check_project_sharded", _explode)

    findings = chain.gather_dream_chain(tmp_path)

    by_check = {f.check: f for f in findings}
    assert "epics-missing" in by_check, (
        f"one project's failure hid another's real FAIL: {[f.check for f in findings]}"
    )
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
        tmp_path, "pyforge-doctor", "spec-host",
        owner_dream="host", satellite="Some Other Dream",
    )
    _write_sharded_project(tmp_path, "pyforge-doctor")

    findings = chain.gather_dream_chain(tmp_path)

    subjects = {f.evidence["subject"] for f in findings if f.check == "dream-without-spec"}
    assert "orphan" in subjects, (
        f"a non-string Dream title collapsed every real finding: "
        f"{[(f.check, f.status) for f in findings]}"
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
        tmp_path / "_bmad-output" / "projects" / "pyforge-doctor"
        / "planning-artifacts" / "specs" / "spec-malformed" / "SPEC.md"
    )
    bad_spec.parent.mkdir(parents=True, exist_ok=True)
    bad_spec.write_text(
        "---\nowner-dream:\n  - docs/dreams/foo.md\n---\nbody\n", encoding="utf-8"
    )

    findings = chain.gather_dream_chain(tmp_path)

    by_check = {f.check: f for f in findings}
    assert "dream-without-spec" in by_check, (
        f"the malformed spec hid the unrelated dream's real FAIL: "
        f"{[f.check for f in findings]}"
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
    blind = (
        tmp_path / "_bmad-output" / "projects" / "pyforge-mason"
        / "planning-artifacts" / "specs"
    )
    blind.mkdir(parents=True, exist_ok=True)
    blind.chmod(0o000)
    try:
        findings = chain.gather_dream_chain(tmp_path)
    finally:
        blind.chmod(0o755)

    by_check = {f.check: f for f in findings}
    assert "dream-without-spec" in by_check, (
        f"one project's unreadable specs/ hid an unrelated real FAIL: "
        f"{[f.check for f in findings]}"
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
