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

import json
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


def _write_baseline(target: Path, data: dict) -> Path:
    """Write the Story 7.2 grandfather baseline (``{project_slug: count}``)
    a test fixture needs so ``gather_deferred_work`` does not degrade to the
    ``no-deferred-work-baseline`` finding -- most tests below are exercising
    something ORTHOGONAL to the baseline itself and want a clean ``{}``."""
    path = target / "scripts" / ".deferred-work-baseline.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
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
    _write_baseline(tmp_path, {})
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
    _write_baseline(tmp_path, {})
    _write_tier3(tmp_path, "proj", "## DW-story-1-1\npromoted\n")
    _write_tracked(tmp_path, "proj", "## DW-story-1-1\nstatus: closed\n")

    findings = chain.gather_deferred_work(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.status is DoctorStatus.OK
    assert finding.evidence == {"projects_scanned": 1}


# --- Multi-project isolation ------------------------------------------------------


def test_multiple_projects_are_all_reported_independently(tmp_path: Path) -> None:
    _write_baseline(tmp_path, {})
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
    _write_baseline(tmp_path, {})
    _write_tier3(tmp_path, "good", "## DW-1\nnever promoted\n")  # real FAIL
    _write_tracked(tmp_path, "good", "## DW-other\nstatus: open\n")
    _write_tier3(tmp_path, "zbroken", "## DW-2\nsomething\n")

    real = chain._check_project_deferred_work

    def _explode(target, proj, findings, baseline):
        if proj.name == "zbroken":
            raise RuntimeError("unanticipated shape")
        return real(target, proj, findings, baseline)

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
    _write_baseline(tmp_path, {})
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
    _write_baseline(tmp_path, {})
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


# --- Story 7.3: Tier-3-anonymous entries against the grandfather baseline ---------


def test_anonymous_tier3_entries_beyond_baseline_are_reported_fail(
    tmp_path: Path,
) -> None:
    """The core I/O matrix row: N=3 anonymous Tier-3 entries, baseline stamps
    K=1 -- the two entries past the stamped count (positional slice, not a
    lookup) each become one ``tier3-entry-unidentified`` FAIL."""
    _write_baseline(tmp_path, {"proj": 1})
    _write_tier3(
        tmp_path, "proj",
        "- source_spec: `a`\n\n- source_spec: `b`\n\n- source_spec: `c`\n",
    )
    _write_tracked(tmp_path, "proj", "## DW-x\nstatus: open\n")

    findings = chain.gather_deferred_work(tmp_path)

    reported = [f for f in findings if f.check == "tier3-entry-unidentified"]
    assert len(reported) == 2, findings
    assert all(f.source is Source.DEFERRED_WORK for f in reported)
    assert all(f.status is DoctorStatus.FAIL for f in reported)
    assert {f.evidence["id"] for f in reported} == {"line 3", "line 5"}
    assert "cannot be cited" in reported[0].message


def test_anonymous_tier3_entries_within_baseline_report_nothing(
    tmp_path: Path,
) -> None:
    """The grandfather row: exactly K=2 anonymous Tier-3 entries, baseline
    stamps K=2 -- entirely grandfathered, zero findings for this project."""
    _write_baseline(tmp_path, {"proj": 2})
    _write_tier3(tmp_path, "proj", "- source_spec: `a`\n\n- source_spec: `b`\n")
    _write_tracked(tmp_path, "proj", "## DW-x\nstatus: open\n")

    findings = chain.gather_deferred_work(tmp_path)

    assert not any(f.check == "tier3-entry-unidentified" for f in findings), findings


def test_project_absent_from_baseline_is_treated_as_count_zero(
    tmp_path: Path,
) -> None:
    """A project present in the Tier-3 tree but with no key in the committed
    baseline is never silently grandfathered -- every one of its current
    anonymous entries is reported."""
    _write_baseline(tmp_path, {"other-project": 5})
    _write_tier3(tmp_path, "proj", "- source_spec: `a`\n")
    _write_tracked(tmp_path, "proj", "## DW-x\nstatus: open\n")

    findings = chain.gather_deferred_work(tmp_path)

    reported = [f for f in findings if f.check == "tier3-entry-unidentified"]
    assert len(reported) == 1, findings
    assert reported[0].evidence["project"] == "proj"
    assert reported[0].evidence["id"] == "line 1"


def test_tier3_cap2_mutation_pair_identified_then_anonymous(tmp_path: Path) -> None:
    """CAP-2's proof standard, applied to the Tier-3 side (mirrors the
    tracked-ledger proof ``_anonymous()``'s own docstring already records): a
    claimed ``## DW-1`` entry (its own ``- source_spec:`` field, positionally
    the first under the heading) produces no Tier-3-anonymous finding.
    Deleting the id heading turns the SAME entry anonymous and, being beyond
    the baseline-stamped count of 0, reds the detector where it was
    previously clean -- demonstrated by mutation, not asserted by inspection."""
    _write_baseline(tmp_path, {"proj": 0})
    _write_tier3(tmp_path, "proj", "## DW-1\n- source_spec: `spec-x`\n")
    _write_tracked(tmp_path, "proj", "## DW-1\nstatus: open\n")

    before = chain.gather_deferred_work(tmp_path)
    assert not any(f.check == "tier3-entry-unidentified" for f in before), before

    # Mutation: delete the id heading, leaving a bare anonymous entry behind.
    _write_tier3(tmp_path, "proj", "- source_spec: `spec-x`\n")

    after = chain.gather_deferred_work(tmp_path)
    finding = next(f for f in after if f.check == "tier3-entry-unidentified")
    assert finding.source is Source.DEFERRED_WORK
    assert finding.status is DoctorStatus.FAIL
    assert finding.evidence["id"] == "line 1"


def test_missing_baseline_reports_one_fail_and_suppresses_tier3_anonymous_checks(
    tmp_path: Path,
) -> None:
    """Given no ``scripts/.deferred-work-baseline.json`` at all: exactly one
    ``no-deferred-work-baseline`` FAIL, and the genuinely anonymous Tier-3
    entry present is NOT individually reported -- silently treating a
    missing baseline as count 0 would flood it as a fresh FAIL instead."""
    _write_tier3(tmp_path, "proj", "- source_spec: `a`\n")
    _write_tracked(tmp_path, "proj", "## DW-x\nstatus: open\n")
    # deliberately: no _write_baseline(...) call

    findings = chain.gather_deferred_work(tmp_path)

    kinds = [f.check for f in findings]
    assert kinds.count("no-deferred-work-baseline") == 1, kinds
    assert "tier3-entry-unidentified" not in kinds, kinds
    finding = next(f for f in findings if f.check == "no-deferred-work-baseline")
    assert finding.source is Source.DEFERRED_WORK
    assert finding.status is DoctorStatus.FAIL


def test_malformed_baseline_json_degrades_like_missing(tmp_path: Path) -> None:
    """Invalid JSON is handled, not raised, and degrades exactly like a
    missing file -- one named FAIL, Tier-3-anonymous check skipped repo-wide."""
    baseline_path = tmp_path / "scripts" / ".deferred-work-baseline.json"
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_path.write_text("{not valid json", encoding="utf-8")
    _write_tier3(tmp_path, "proj", "- source_spec: `a`\n")
    _write_tracked(tmp_path, "proj", "## DW-x\nstatus: open\n")

    findings = chain.gather_deferred_work(tmp_path)

    kinds = [f.check for f in findings]
    assert kinds.count("no-deferred-work-baseline") == 1, kinds
    assert "tier3-entry-unidentified" not in kinds, kinds


def test_baseline_wrong_top_level_shape_degrades_like_missing(tmp_path: Path) -> None:
    """Valid JSON but the wrong shape (a list, not a ``{project: count}``
    object) is the second malformed-but-parseable failure mode the matrix
    names -- same one-FAIL degrade, not a crash on ``.get()``/``isinstance``."""
    baseline_path = tmp_path / "scripts" / ".deferred-work-baseline.json"
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_path.write_text(json.dumps(["proj", 1]), encoding="utf-8")
    _write_tier3(tmp_path, "proj", "- source_spec: `a`\n")
    _write_tracked(tmp_path, "proj", "## DW-x\nstatus: open\n")

    findings = chain.gather_deferred_work(tmp_path)

    kinds = [f.check for f in findings]
    assert kinds.count("no-deferred-work-baseline") == 1, kinds
    assert "tier3-entry-unidentified" not in kinds, kinds


def test_missing_baseline_does_not_suppress_unrelated_finding_kinds(
    tmp_path: Path,
) -> None:
    """A missing baseline only silences the NEW Tier-3-anonymous check --
    every pre-existing finding kind (here, ``tier3-only-deferral``) still
    fires normally, since it is unrelated to this story's grandfathering."""
    _write_tier3(tmp_path, "proj", "## DW-1\nnever promoted\n")
    _write_tracked(tmp_path, "proj", "## DW-other\nstatus: open\n")
    # deliberately: no _write_baseline(...) call

    findings = chain.gather_deferred_work(tmp_path)

    kinds = {f.check for f in findings}
    assert "no-deferred-work-baseline" in kinds
    assert "tier3-only-deferral" in kinds


def test_baseline_count_larger_than_live_entries_reports_nothing(
    tmp_path: Path,
) -> None:
    """Review-pass addition: a stamped count that exceeds the file's current
    number of anonymous entries (e.g. some were later given headings) must
    not crash or under/over-report -- the positional slice is simply empty."""
    _write_baseline(tmp_path, {"proj": 99})
    _write_tier3(tmp_path, "proj", "- source_spec: `a`\n")
    _write_tracked(tmp_path, "proj", "## DW-x\nstatus: open\n")

    findings = chain.gather_deferred_work(tmp_path)

    assert not any(f.check == "tier3-entry-unidentified" for f in findings), findings


def test_baseline_bool_or_negative_value_degrades_like_missing(
    tmp_path: Path,
) -> None:
    """Review-pass addition: ``bool`` is an ``int`` subclass in Python, so
    ``{"proj": true}`` would otherwise pass an ``isinstance(v, int)`` shape
    guard and mis-slice as ``[1:]``; a negative count would mis-slice as a
    tail-only ``[-1:]`` via Python's negative-index semantics. Both must be
    rejected as malformed shape, not silently coerced."""
    for bad_value in (True, -1):
        baseline_path = tmp_path / "scripts" / ".deferred-work-baseline.json"
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(json.dumps({"proj": bad_value}), encoding="utf-8")
        _write_tier3(tmp_path, "proj", "- source_spec: `a`\n")
        _write_tracked(tmp_path, "proj", "## DW-x\nstatus: open\n")

        findings = chain.gather_deferred_work(tmp_path)

        kinds = [f.check for f in findings]
        assert kinds.count("no-deferred-work-baseline") == 1, (bad_value, kinds)
        assert "tier3-entry-unidentified" not in kinds, (bad_value, kinds)


# --- Story 7.4: severity parity across ledger/Tier-3 sides -------------------------


def test_ledger_and_tier3_anonymous_entries_carry_the_same_severity(
    tmp_path: Path,
) -> None:
    """CAP-2's closing AC: proof, not an inference from reading the code, that
    the two anonymous-entry finding kinds -- tracked-side
    ``ledger-entry-unidentified`` and Tier-3-side ``tier3-entry-unidentified``
    -- resolve to the same status within ONE run. Neither finding-building
    branch in ``_check_project_deferred_work`` sets the ``"warn"`` key, so
    both must come back FAIL; this pins that fact so a future one-sided edit
    (e.g. adding ``"warn"`` to only one branch) cannot silently desync them."""
    _write_baseline(tmp_path, {"proj": 0})
    _write_tier3(tmp_path, "proj", "- source_spec: `a`\n")
    _write_tracked(
        tmp_path, "proj",
        "## DW-x\nstatus: open\n- source_spec: foo\n\n- source_spec: bar\n",
    )

    findings = chain.gather_deferred_work(tmp_path)

    kinds = {f.check for f in findings}
    assert {"ledger-entry-unidentified", "tier3-entry-unidentified"} <= kinds, (
        f"expected both anonymous-entry finding kinds to fire in the same run: "
        f"{sorted(kinds)}"
    )
    ledger = next(f for f in findings if f.check == "ledger-entry-unidentified")
    tier3 = next(f for f in findings if f.check == "tier3-entry-unidentified")
    assert ledger.source is Source.DEFERRED_WORK
    assert tier3.source is Source.DEFERRED_WORK
    assert ledger.status is DoctorStatus.FAIL
    assert tier3.status is DoctorStatus.FAIL
    assert ledger.status == tier3.status, (
        f"anonymous entries on the two sides diverged in severity: "
        f"ledger={ledger.status!r} tier3={tier3.status!r}"
    )
