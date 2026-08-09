"""Unit tests for ``pyforge.doctor.sources.chain.gather_deferred_work``
(Story 6.6) -- covers every row of the spec's I/O & Edge-Case Matrix that
belongs to Tier-3/tracked-ledger durability against REAL tmp fixture trees,
mirroring ``test_sources_ledger.py``'s own real-fixture discipline.

Every kind below was independently verified, during development, to actually
FIRE its own dedicated test: temporarily removing that finding's
``findings.append(...)`` branch in
``sources/chain.py::_check_project_deferred_work`` and re-running the single
test made it fail. That verification is not re-encoded as a permanent
mutation here -- see the story spec's own Tasks & Acceptance for the
requirement.
"""

from __future__ import annotations

from pathlib import Path

from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import chain

# --- fixture helpers ---------------------------------------------------------


def _project_dir(target: Path, project: str) -> Path:
    return target / "_bmad-output" / "projects" / project


def _write_tier3(target: Path, project: str, text: str) -> Path:
    path = _project_dir(target, project) / "implementation-artifacts" / "deferred-work.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _write_tracked(target: Path, project: str, text: str) -> Path:
    path = _project_dir(target, project) / "planning-artifacts" / "deferred-work-ledger.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# --- Tier-3-only deferral -------------------------------------------------------


def test_tier3_only_id_reports_fail(tmp_path: Path) -> None:
    _write_tier3(tmp_path, "proj", "## DW-1\nnever promoted\n")
    _write_tracked(tmp_path, "proj", "## DW-other\nstatus: open\n")

    findings = chain.gather_deferred_work(tmp_path)

    kinds = {f.check for f in findings}
    assert "tier3-only-deferral" in kinds
    finding = next(f for f in findings if f.check == "tier3-only-deferral")
    assert finding.source is Source.DEFERRED_WORK
    assert finding.status is DoctorStatus.FAIL
    assert finding.evidence["id"] == "DW-1"
    assert finding.evidence["generic_id"] is True
    assert "a generic id" in finding.message


def test_non_generic_tier3_only_id_carries_no_generic_hint(tmp_path: Path) -> None:
    _write_tier3(tmp_path, "proj", "## DW-story-3-1\nnever promoted\n")
    _write_tracked(tmp_path, "proj", "## DW-other\nstatus: open\n")

    findings = chain.gather_deferred_work(tmp_path)

    finding = next(f for f in findings if f.check == "tier3-only-deferral")
    assert finding.evidence["generic_id"] is False
    assert "a generic id" not in finding.message


def test_promoted_id_reports_no_finding(tmp_path: Path) -> None:
    _write_tier3(tmp_path, "proj", "## DW-1\npromoted already\n")
    _write_tracked(tmp_path, "proj", "## DW-story-1-1\nstatus: open\nDW-1\n")

    findings = chain.gather_deferred_work(tmp_path)

    assert not any(f.check == "tier3-only-deferral" for f in findings)


# --- No tracked ledger at all (substantive Tier-3) ------------------------------


def test_substantive_tier3_with_no_tracked_ledger_reports_fail(tmp_path: Path) -> None:
    _write_tier3(tmp_path, "proj", "x" * 4096)  # >= _SUBSTANTIVE_BYTES, no DW- ids

    findings = chain.gather_deferred_work(tmp_path)

    kinds = {f.check for f in findings}
    assert "no-tracked-ledger" in kinds
    finding = next(f for f in findings if f.check == "no-tracked-ledger")
    assert finding.status is DoctorStatus.FAIL
    assert finding.evidence["project"] == "proj"
    assert "gitignored" in finding.message


def test_boilerplate_tier3_with_no_tracked_ledger_reports_no_finding(tmp_path: Path) -> None:
    _write_tier3(tmp_path, "proj", "tiny\n")  # well below _SUBSTANTIVE_BYTES

    findings = chain.gather_deferred_work(tmp_path)

    assert not any(f.check == "no-tracked-ledger" for f in findings)


# --- Ledger entry missing status -------------------------------------------------


def test_ledger_entry_without_status_reports_fail(tmp_path: Path) -> None:
    _write_tier3(tmp_path, "proj", "## DW-x\nsomething\n")
    _write_tracked(tmp_path, "proj", "## DW-x\nno status line here\n")

    findings = chain.gather_deferred_work(tmp_path)

    kinds = {f.check for f in findings}
    assert "ledger-entry-unstatused" in kinds
    finding = next(f for f in findings if f.check == "ledger-entry-unstatused")
    assert finding.status is DoctorStatus.FAIL
    assert finding.evidence["id"] == "DW-x"
    assert "cannot be counted as open or closed" in finding.message


def test_ledger_entry_with_status_reports_no_unstatused_finding(tmp_path: Path) -> None:
    _write_tier3(tmp_path, "proj", "## DW-x\nsomething\n")
    _write_tracked(tmp_path, "proj", "## DW-x\nstatus: open\n")

    findings = chain.gather_deferred_work(tmp_path)

    assert not any(f.check == "ledger-entry-unstatused" for f in findings)


# --- Ledger entry unidentified (anonymous) ---------------------------------------


def test_anonymous_ledger_entry_reports_fail(tmp_path: Path) -> None:
    _write_tier3(tmp_path, "proj", "## DW-x\nsomething\n")
    _write_tracked(
        tmp_path, "proj",
        "## DW-x\nstatus: open\n- source_spec: foo\n\n- source_spec: bar\n",
    )

    findings = chain.gather_deferred_work(tmp_path)

    kinds = {f.check for f in findings}
    assert "ledger-entry-unidentified" in kinds
    finding = next(f for f in findings if f.check == "ledger-entry-unidentified")
    assert finding.status is DoctorStatus.FAIL
    assert finding.evidence["id"].startswith("line ")
    assert "cannot be cited" in finding.message


# --- Clean project: no Tier-3 ledger at all --------------------------------------


def test_project_with_no_tier3_ledger_reports_ok(tmp_path: Path) -> None:
    """A real projects tree whose projects simply carry no Tier-3 ledger is an
    evaluable, genuinely clean state -- the confident OK is honest here."""
    _project_dir(tmp_path, "proj").mkdir(parents=True, exist_ok=True)

    findings = chain.gather_deferred_work(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.DEFERRED_WORK
    assert finding.check == "deferred-work"
    assert finding.status is DoctorStatus.OK
    assert finding.evidence == {"projects_scanned": 0}


def test_target_with_no_projects_tree_reports_unevaluable_warn(
    tmp_path: Path,
) -> None:
    """A target with no ``_bmad-output/projects/`` at all is not a monorepo
    root -- the shape `doctor check`'s own ``path="."`` default takes when it
    is run from a SUBDIRECTORY. "Every Tier-3 deferral has a tracked twin" is
    then a true-but-vacuous claim about zero deferrals that reads as a clean
    bill of health, so this must WARN instead (mirrors
    ``gather_dream_chain``'s own guard and ``sources/ledger.py``'s WARN)."""
    findings = chain.gather_deferred_work(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.DEFERRED_WORK
    assert finding.check == "deferred-work-unevaluable"
    assert finding.status is DoctorStatus.WARN
    assert finding.evidence == {"target": str(tmp_path)}


def test_fully_promoted_project_reports_ok(tmp_path: Path) -> None:
    _write_tier3(tmp_path, "proj", "## DW-story-1-1\npromoted\n")
    _write_tracked(tmp_path, "proj", "## DW-story-1-1\nstatus: closed\n")

    findings = chain.gather_deferred_work(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.status is DoctorStatus.OK
    assert finding.evidence == {"projects_scanned": 1}


# --- Multi-project isolation ------------------------------------------------------


def test_multiple_projects_are_all_reported_independently(tmp_path: Path) -> None:
    _write_tier3(tmp_path, "alpha", "## DW-1\nnever promoted\n")
    _write_tracked(tmp_path, "alpha", "## DW-other\nstatus: open\n")
    _write_tier3(tmp_path, "beta", "## DW-story-1-1\npromoted\n")
    _write_tracked(tmp_path, "beta", "## DW-story-1-1\nstatus: closed\n")  # clean

    findings = chain.gather_deferred_work(tmp_path)

    assert len(findings) == 1
    assert findings[0].evidence["project"] == "alpha"


def test_one_unevaluable_project_does_not_hide_another_projects_real_fail(
    tmp_path: Path, monkeypatch,
) -> None:
    """One project's unreadable Tier-3/tracked ledger must not discard a
    DIFFERENT, well-formed project's real ``tier3-only-deferral`` FAIL --
    isolation structured in from the first draft (Design Notes), mirroring
    ``sources/board.py``'s own per-project isolation tests."""
    _write_tier3(tmp_path, "good", "## DW-1\nnever promoted\n")  # real FAIL
    _write_tracked(tmp_path, "good", "## DW-other\nstatus: open\n")
    _write_tier3(tmp_path, "zbroken", "## DW-2\nsomething\n")

    real = chain._check_project_deferred_work

    def _explode(target, proj, findings):
        if proj.name == "zbroken":
            raise RuntimeError("unanticipated shape")
        return real(target, proj, findings)

    monkeypatch.setattr(chain, "_check_project_deferred_work", _explode)

    findings = chain.gather_deferred_work(tmp_path)

    by_check = {f.check: f for f in findings}
    assert "tier3-only-deferral" in by_check, (
        f"one project's failure hid another's real FAIL: {[f.check for f in findings]}"
    )
    assert by_check["tier3-only-deferral"].status is DoctorStatus.FAIL
    assert by_check["tier3-only-deferral"].evidence["project"] == "good"
    warn = by_check["deferred-work-unevaluable"]
    assert warn.status is DoctorStatus.WARN
    assert warn.evidence["project"] == "zbroken"


# --- Never raises: non-UTF-8 bytes -----------------------------------------------


def test_non_utf8_tracked_ledger_never_raises(tmp_path: Path) -> None:
    _write_tier3(tmp_path, "proj", "## DW-1\nsomething\n")
    tracked = _project_dir(tmp_path, "proj") / "planning-artifacts" / "deferred-work-ledger.md"
    tracked.parent.mkdir(parents=True, exist_ok=True)
    tracked.write_bytes(b"## DW-1\nstatus: caf\xe9\n")

    findings = chain.gather_deferred_work(tmp_path)

    assert findings  # returned rather than raised
    assert all(f.source is Source.DEFERRED_WORK for f in findings)


# --- Ported branches that survived mutation (review pass 4) -----------------------
#
# Each test below pins a ported branch the suite did NOT previously kill under
# mutation, which the story's own Acceptance Criteria require. All were
# mutation-confirmed when written.


def test_a_later_entrys_status_does_not_satisfy_an_earlier_one(
    tmp_path: Path,
) -> None:
    """``_entries`` slices the ledger text per entry (heading to next
    heading). Without the slice boundary, ``_STATUS_RE`` searches the whole
    remaining document, so ONE ``status:`` anywhere below silently marks
    every earlier entry as statused. No fixture had two entries where only
    the later one carried a status."""
    _write_tier3(tmp_path, "proj", "## DW-1\nx\n")
    _write_tracked(
        tmp_path, "proj",
        "## DW-1\nno status here\n\n## DW-2\nstatus: open\n",
    )

    unstatused = {f.evidence["id"] for f in chain.gather_deferred_work(tmp_path)
                  if f.check == "ledger-entry-unstatused"}

    assert unstatused == {"DW-1"}, (
        f"a later entry's status: leaked backwards into an earlier one: {unstatused}"
    )


def test_a_plain_heading_ends_the_current_entry_for_anonymity(
    tmp_path: Path,
) -> None:
    """``_anonymous``'s non-``DW-`` heading branch resets the entry state, so
    a ``- source_spec:`` under an ordinary ``## Notes`` heading is an
    anonymous entry rather than a field of the DW entry above it.

    The DW entry deliberately carries NO ``source_spec`` of its own: with one,
    ``field_taken`` is already ``True`` by the time ``## Notes`` arrives and
    the entry below is reported anonymous whether the heading reset ran or
    not -- the mutation survives such a fixture."""
    _write_tier3(tmp_path, "proj", "## DW-1\nx\n")
    _write_tracked(
        tmp_path, "proj",
        "## DW-1\nstatus: open\n\n## Notes\n- source_spec: `b`\n",
    )

    anon = [f for f in chain.gather_deferred_work(tmp_path)
            if f.check == "ledger-entry-unidentified"]

    assert len(anon) == 1, f"expected exactly the entry under ## Notes: {anon}"
    assert anon[0].evidence["id"] == "line 5", anon[0].evidence


def test_only_the_first_source_spec_in_an_entry_is_its_own_field(
    tmp_path: Path,
) -> None:
    """``_anonymous``'s positional ``field_taken`` rule -- the original
    records this one as "proved by mutation". The FIRST ``- source_spec:``
    under a ``## DW-`` heading is that entry's own field; a SECOND one is a
    separate, anonymous entry that lost its heading."""
    _write_tier3(tmp_path, "proj", "## DW-1\nx\n")
    _write_tracked(
        tmp_path, "proj",
        "## DW-1\nstatus: open\n- source_spec: `a`\n- source_spec: `b`\n",
    )

    anon = [f.evidence["id"] for f in chain.gather_deferred_work(tmp_path)
            if f.check == "ledger-entry-unidentified"]

    assert anon == ["line 4"], (
        f"the positional first-field rule did not hold: {anon}"
    )


def test_a_trailing_hyphen_family_prefix_is_not_a_distinct_id(
    tmp_path: Path,
) -> None:
    """``_ids``' ``rstrip("-")``. Prose in a Tier-3 ledger routinely names a
    FAMILY as ``DW-B4-``; without the strip that reads as an id of its own
    and is reported unpromoted forever, because no tracked entry can ever
    match it."""
    _write_tier3(tmp_path, "proj", "## DW-B4\nsee the DW-B4- family\n")
    _write_tracked(tmp_path, "proj", "## DW-B4\nstatus: open\n")

    checks = [f.check for f in chain.gather_deferred_work(tmp_path)]

    assert "tier3-only-deferral" not in checks, (
        f"a family prefix was reported as an unpromoted id: {checks}"
    )


# --- Unreadable inputs are WARNs, never a clean bill of health --------------------


def test_unreadable_tier3_directory_is_a_warn_not_a_confident_ok(
    tmp_path: Path,
) -> None:
    """``Path.is_file()`` answers ``False`` for an unreadable ANCESTOR, so an
    unreadable ``implementation-artifacts/`` read as "this project defers
    nothing" -- reproduced live during review, two real FAILs became a
    confident ``deferred-work ok``. Empty must never be inferred from
    unreadable."""
    _write_tier3(tmp_path, "proj", "## DW-1\nx\n" + "y" * 3000)

    t3_dir = _project_dir(tmp_path, "proj") / "implementation-artifacts"
    t3_dir.chmod(0o000)
    try:
        findings = chain.gather_deferred_work(tmp_path)
    finally:
        t3_dir.chmod(0o755)

    assert [f.check for f in findings] == ["deferred-work-unevaluable"], findings
    assert findings[0].status is DoctorStatus.WARN
    assert "could not be evaluated here" in findings[0].message


def test_unreadable_tracked_ledger_directory_does_not_claim_the_ledger_is_absent(
    tmp_path: Path,
) -> None:
    """The mirror image: an unreadable ``planning-artifacts/`` used to read as
    "the tracked ledger does not exist", asserting the WHOLE record was
    gitignored -- and re-flagging every already-promoted id as Tier-3-only --
    about a project whose ledger is right there."""
    _write_tier3(tmp_path, "proj", "## DW-1\nx\n" + "y" * 3000)
    _write_tracked(tmp_path, "proj", "## DW-1\nstatus: open\n")
    assert [f.check for f in chain.gather_deferred_work(tmp_path)] == ["deferred-work"]

    pa_dir = _project_dir(tmp_path, "proj") / "planning-artifacts"
    pa_dir.chmod(0o000)
    try:
        findings = chain.gather_deferred_work(tmp_path)
    finally:
        pa_dir.chmod(0o755)

    checks = [f.check for f in findings]
    assert checks == ["deferred-work-unevaluable"], (
        f"an unreadable planning-artifacts/ produced confidently wrong FAILs: {checks}"
    )
    assert findings[0].status is DoctorStatus.WARN
