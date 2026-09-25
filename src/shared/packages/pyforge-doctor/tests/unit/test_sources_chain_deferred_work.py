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

import pytest

from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import chain

# Guarded, mirroring test_check_speed_budget.py's own idiom: an IndexError
# from a shallower-than-7-levels layout (e.g. an extracted sdist) degrades to
# a skip rather than a collection error for the whole file.
try:
    _REPO_ROOT: Path | None = Path(__file__).resolve().parents[6]
except IndexError:
    _REPO_ROOT = None

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


# --- Content-comparison exemption (2026-08-28) ----------------------------------
#
# Live finding: a Tier-3 entry already reached the tracked ledger by some OTHER
# path (a prior promotion run, a hand-edit) under a DIFFERENT, independently-
# minted id -- an id-only comparison (above) wrongly reports it as missing.
# Two independent signals, mirroring `deferred_work_promote.py`'s own write-side
# collision guard and `frontmatter_deferral_in_tracked`'s own needle search.


def test_tier3_only_id_with_matching_summary_in_tracked_reports_nothing(
    tmp_path: Path,
) -> None:
    """Real shape, confirmed live (pyforge-atlas Tier-3 line 7 vs. its own
    tracked ``DW-A1-6``): a Tier-3 entry's normalized summary already exists
    in the tracked ledger under a completely different id."""
    _write_tier3(
        tmp_path,
        "proj",
        "## DW-1\n- source_spec: `x`\n  summary: The workstation re-lock is blocked.\n",
    )
    _write_tracked(
        tmp_path,
        "proj",
        "## DW-A1-6\nstatus: open\n- source_spec: `x`\n  summary: The workstation re-lock is blocked.\n",
    )

    findings = chain.gather_deferred_work(tmp_path)

    assert not any(f.check == "tier3-only-deferral" for f in findings), findings


def test_tier3_only_id_with_a_different_summary_still_reports_fail(
    tmp_path: Path,
) -> None:
    """The exemption requires a REAL content match -- a merely-present
    ``summary:`` field on both sides, with genuinely different text, must
    not launder every unpromoted entry."""
    _write_tier3(
        tmp_path,
        "proj",
        "## DW-1\n- source_spec: `x`\n  summary: A completely different finding.\n",
    )
    _write_tracked(
        tmp_path,
        "proj",
        "## DW-A1-6\nstatus: open\n- source_spec: `x`\n  summary: The workstation re-lock is blocked.\n",
    )

    findings = chain.gather_deferred_work(tmp_path)

    assert any(f.check == "tier3-only-deferral" for f in findings), findings


def test_tier3_only_id_with_matching_origin_fingerprint_reports_nothing(
    tmp_path: Path,
) -> None:
    """Real shape, confirmed live (pyforge-atlas's own ``DW-10``): a bmad-loop
    harvest-damping entry carries no ``summary:`` field at all (so the check
    above can never fire for it), only an ``origin: spec-deferred
    <fingerprint>`` marker -- already present in the tracked ledger, promoted
    via the spec-frontmatter path under a different id entirely."""
    _write_tier3(
        tmp_path,
        "proj",
        "## DW-10\n- source_spec: `x`\n  origin: spec-deferred 8b4c28559f93\n",
    )
    _write_tracked(
        tmp_path,
        "proj",
        "## DW-FU-17-2\nstatus: open\n- source_spec: `x`\n"
        "  origin: spec-deferred 8b4c28559f93 -- ingested from spec frontmatter\n",
    )

    findings = chain.gather_deferred_work(tmp_path)

    assert not any(f.check == "tier3-only-deferral" for f in findings), findings


def test_tier3_only_id_with_a_different_fingerprint_still_reports_fail(
    tmp_path: Path,
) -> None:
    """A different fingerprint (a different harvested spec-frontmatter
    finding) must not exempt an unrelated entry."""
    _write_tier3(
        tmp_path,
        "proj",
        "## DW-10\n- source_spec: `x`\n  origin: spec-deferred 8b4c28559f93\n",
    )
    _write_tracked(
        tmp_path,
        "proj",
        "## DW-FU-17-2\nstatus: open\n- source_spec: `x`\n"
        "  origin: spec-deferred aaaaaaaaaaaa -- ingested from spec frontmatter\n",
    )

    findings = chain.gather_deferred_work(tmp_path)

    assert any(f.check == "tier3-only-deferral" for f in findings), findings


def test_tier3_only_plain_entry_with_truncated_title_matching_tracked_prefix_reports_nothing(
    tmp_path: Path,
) -> None:
    """Real shape, confirmed live 2026-08-29 (pyforge-atlas's own ``DW-6``,
    fingerprint ``81ca01b1f565``): an ``IDENTIFIED_PLAIN`` entry with NO
    ``summary:`` field of its own -- the heading holds the only summary
    text there is, truncated to a fixed character budget -- and whose
    ``origin:`` fingerprint no longer matches (the underlying spec was
    edited after harvest, changing the hash). The LATER promotion
    (``deferred_work_intake.py``, re-reading the spec's current frontmatter)
    carries the full, untruncated text under a fresh fingerprint the old
    heading predates. Neither check 1 (no ``summary:`` field) nor check 2
    (fingerprint mismatch) can fire; only the truncated-title-prefix check
    (3) recognizes this as already-promoted content."""
    title = (
        'write_ops_canvas: records whose P/Work falls back to the "?" '
        "sentinel are counted in the total but invisible in every "
        "per-bucket breakdown table; build_by_type silently drops recipe "
        "types outside the"
    )
    assert len(title) >= chain._TRUNCATED_TITLE_MIN_LEN
    _write_baseline(tmp_path, {"proj": 0})
    _write_tier3(
        tmp_path,
        "proj",
        f"### DW-6: {title}\n"
        "origin: spec-deferred 81ca01b1f565\n"
        "location: scripts/openteams_identity_dashboards.py:write_ops_canvas\n"
        "source_spec: `x`\n"
        "status: open\n",
    )
    _write_tracked(
        tmp_path,
        "proj",
        "### DW-FU-17-2-3: "
        f"{title} fixed RECIPE_TYPE_ORDER list.\n\n"
        "- source_spec: `x`\n"
        f"  summary: {title} fixed RECIPE_TYPE_ORDER list.\n"
        "  origin: spec-deferred 5682282eafff -- ingested from spec frontmatter\n"
        "  status: open\n",
    )

    findings = chain.gather_deferred_work(tmp_path)

    assert not any(f.check == "tier3-only-deferral" for f in findings), findings


def test_tier3_only_plain_entry_with_unrelated_title_still_reports_fail(
    tmp_path: Path,
) -> None:
    """Mutation guard: a Tier-3 ``IDENTIFIED_PLAIN`` entry whose title does
    NOT appear anywhere in the tracked ledger -- even one long enough to
    clear ``_TRUNCATED_TITLE_MIN_LEN`` -- must still report
    ``tier3-only-deferral``. Proves check 3 is a real prefix match against
    genuine tracked content, not a blanket exemption for every
    ``IDENTIFIED_PLAIN`` entry that merely lacks a ``summary:`` field."""
    title = (
        "an entirely unrelated finding about a completely different module "
        "that has never been promoted anywhere, long enough on its own to "
        "clear the truncated-title length floor with room to spare"
    )
    assert len(title) >= chain._TRUNCATED_TITLE_MIN_LEN
    _write_baseline(tmp_path, {"proj": 0})
    _write_tier3(
        tmp_path,
        "proj",
        f"### DW-7: {title}\norigin: spec-deferred ffffffffffff\nsource_spec: `x`\nstatus: open\n",
    )
    _write_tracked(
        tmp_path,
        "proj",
        "### DW-FU-1-1: Something else entirely\n\n"
        "- source_spec: `x`\n"
        "  summary: Something else entirely, sharing no text with the other finding.\n"
        "  status: open\n",
    )

    findings = chain.gather_deferred_work(tmp_path)

    assert any(f.check == "tier3-only-deferral" for f in findings), findings


def test_anonymous_tier3_entry_with_matching_summary_reports_nothing(
    tmp_path: Path,
) -> None:
    """The same content-comparison exemption applies on the
    ``tier3-entry-unidentified`` (anonymous/orphan) path, not just
    ``tier3-only-deferral`` -- the two checks share one helper."""
    _write_baseline(tmp_path, {"proj": 0})
    _write_tier3(
        tmp_path,
        "proj",
        "- source_spec: `x`\n  summary: The workstation re-lock is blocked.\n",
    )
    _write_tracked(
        tmp_path,
        "proj",
        "## DW-A1-6\nstatus: open\n- source_spec: `x`\n  summary: The workstation re-lock is blocked.\n",
    )

    findings = chain.gather_deferred_work(tmp_path)

    assert not any(f.check == "tier3-entry-unidentified" for f in findings), findings


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
        tmp_path,
        "proj",
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
    tmp_path: Path,
    monkeypatch,
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
        tmp_path,
        "proj",
        "## DW-1\nno status here\n\n## DW-2\nstatus: open\n",
    )

    unstatused = {
        f.evidence["id"] for f in chain.gather_deferred_work(tmp_path) if f.check == "ledger-entry-unstatused"
    }

    assert unstatused == {"DW-1"}, f"a later entry's status: leaked backwards into an earlier one: {unstatused}"


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
        tmp_path,
        "proj",
        "## DW-1\nstatus: open\n\n## Notes\n- source_spec: `b`\n",
    )

    anon = [f for f in chain.gather_deferred_work(tmp_path) if f.check == "ledger-entry-unidentified"]

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
        tmp_path,
        "proj",
        "## DW-1\nstatus: open\n- source_spec: `a`\n- source_spec: `b`\n",
    )

    anon = [f.evidence["id"] for f in chain.gather_deferred_work(tmp_path) if f.check == "ledger-entry-unidentified"]

    assert anon == ["line 4"], f"the positional first-field rule did not hold: {anon}"


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

    assert "tier3-only-deferral" not in checks, f"a family prefix was reported as an unpromoted id: {checks}"


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
        tmp_path,
        "proj",
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
        tmp_path,
        "proj",
        "## DW-x\nstatus: open\n- source_spec: foo\n\n- source_spec: bar\n",
    )

    findings = chain.gather_deferred_work(tmp_path)

    kinds = {f.check for f in findings}
    assert {"ledger-entry-unidentified", "tier3-entry-unidentified"} <= kinds, (
        f"expected both anonymous-entry finding kinds to fire in the same run: {sorted(kinds)}"
    )
    ledger = next(f for f in findings if f.check == "ledger-entry-unidentified")
    tier3 = next(f for f in findings if f.check == "tier3-entry-unidentified")
    assert ledger.source is Source.DEFERRED_WORK
    assert tier3.source is Source.DEFERRED_WORK
    assert ledger.status is DoctorStatus.FAIL
    assert tier3.status is DoctorStatus.FAIL
    assert ledger.status == tier3.status, (
        f"anonymous entries on the two sides diverged in severity: ledger={ledger.status!r} tier3={tier3.status!r}"
    )


# --- Story 8.1: classify_tier3_entries -----------------------------------------
#
# Fixtures below are VERBATIM excerpts from real Tier-3/tracked-ledger files
# (cited file + line range in each test's own docstring, per this repo's own
# convention) -- not paraphrased or invented markdown, per the story spec's
# own requirement.


def test_legacy_flat_shape_from_atlas_real_excerpt(tmp_path: Path) -> None:
    """``_bmad-output/projects/pyforge-atlas/implementation-artifacts/
    deferred-work.md`` lines 1-16 (verbatim) -- three headerless
    ``- source_spec:`` bullets (only an H1 document title sits above them,
    not a ``## Deferred from:`` scoping heading) all classify
    ``LEGACY_FLAT`` with ``id=None``."""
    path = tmp_path / "deferred-work.md"
    path.write_text(
        """# Deferred Work Ledger — pyforge-atlas

<!-- Appended by bmad-dev-auto review passes (step-04 defer category). One entry
     per finding; do not modify existing entries. Triage via bmad-loop-sweep or
     at wave boundaries. -->

- source_spec: `a1-scaffold-the-kedro-pixi-project-via-nebi.md`
  summary: The registered `[verify]` command `pixi run --frozen -e pyforge-atlas kedro-test` cannot run until the workstation re-lock lands pixi.lock entries for the pyforge-atlas env — until then EVERY bmad-loop story (including pyforge-warden ones) fails at the verify step.
  evidence: `pixi.lock` has zero `pyforge-atlas` occurrences; `--frozen` cannot materialize an env absent from the lock; container re-lock is blocked by the stubbed `build_artifacts` channel (bmad-ui/bmad-dashboard co-solve — see Story A1 Dev Agent Record). Workstation re-lock is the recorded precondition; do not weaken the gate (NFR-12).

- source_spec: `a1-scaffold-the-kedro-pixi-project-via-nebi.md`
  summary: `.bmad-loop/policy.toml [scm] worktree_seed` still lists only pyforge-warden's implementation-artifacts path — an atlas loop story's worktree (first: A3) would reproduce the documented missing-artifacts-dir crash until the seed adds `_bmad-output/projects/pyforge-atlas/implementation-artifacts`.
  evidence: policy.toml `worktree_seed = ["_bmad-output/projects/pyforge-warden/implementation-artifacts", "_bmad/custom/.active-project"]` with the adjacent comment citing crash run 20260712-164312; A3 is the designated first loop story (sprint story_meta). A1's scope note: "the worktree bootstrap is A3's to validate, not A1's" (AD-18).

- source_spec: `a1-scaffold-the-kedro-pixi-project-via-nebi.md`
  summary: `[verify].commands` is a flat list — every loop story in either package now materializes BOTH the pyforge-warden and pyforge-atlas envs and runs both suites; a red test in one package blocks the other package's loop, and A3's worktree env-materialization cost measurement will include warden's env. Consider per-project/conditional gating when A3 measures.
""",
        encoding="utf-8",
    )

    entries = chain.classify_tier3_entries(path)

    assert len(entries) == 3
    assert all(e.shape is chain.Tier3Shape.LEGACY_FLAT for e in entries)
    assert all(e.id is None for e in entries)
    assert all(e.fields["source_spec"] == "`a1-scaffold-the-kedro-pixi-project-via-nebi.md`" for e in entries)


def test_legacy_flat_and_legacy_header_freeform_skip_from_warden_real_excerpt(
    tmp_path: Path,
) -> None:
    """``_bmad-output/projects/pyforge-warden/implementation-artifacts/
    deferred-work.md`` lines 1-20 (verbatim) -- two headerless
    ``- source_spec:`` bullets (``LEGACY_FLAT``) followed by TWO
    ``## Deferred from: ...`` headings whose own bullets are all freeform
    prose with no ``source_spec:`` field -- both headings own zero entries,
    proving the freeform-skip case: a bullet with no ``source_spec:`` field
    is never returned, and never misread as an owned entry."""
    path = tmp_path / "deferred-work.md"
    path.write_text(
        """# Deferred Work

- source_spec: `_bmad-output/projects/python-deptry-osv-scanner/implementation-artifacts/spec-1-1-frozen-contract-verdict-lattice-projection-safety.md`
  summary: The loop's exact `[verify]` command (`pixi run -e python-deptry-osv-scanner python-deptry-osv-scanner-test`, unfrozen) fails environmentally in every bmad-loop worktree — pixi-build-python 0.8.3 panics (`tools.rs:461` byte-index underflow) when the build `workDirectory` exceeds ~250 chars (run-worktree roots are ~162 chars), and behind it any successful unfrozen re-solve in a worktree rewrites `pixi.lock` with worktree-absolute paths for the gitignored `file://…/build_artifacts` channel (toxic to commit via the loop's `git add -A` squash-merge); switch `.bmad-loop/policy.toml` `[verify]` to `pixi run --frozen -e python-deptry-osv-scanner python-deptry-osv-scanner-test` (or export `PIXI_FROZEN=true` in the engine env / shorten the runs-dir path / pin pixi-build-python past the underflow), and note the related risk that a stale pixi build cache can resolve the package to non-worktree sources, so the verify gate should always run `--frozen` from the worktree root.
  evidence: Reproduced at baseline (before this story's changes) and re-confirmed after — the unfrozen solve dies with "the build backend (pixi-build-python) exited prematurely" during the `python-deptry-osv-scanner` env solve, while `pixi run --frozen -e python-deptry-osv-scanner python-deptry-osv-scanner-test` passes the identical suite (111 passed at implementation, all green at review patch close); a controlled experiment showed the same package solves at a 149-char root and panics at 162 (path-length-driven), and the `detached-environments = true` + `build_artifacts` symlink workaround made the exact unfrozen command pass 111/111 before both tracked files were reverted to keep the story diff clean.

- source_spec: `docs/specs/bmad-loop-adoption.md`
  summary: "`scm.isolation = \"worktree\"` + `cleanup.trim_artifacts = true` silently lose any dev/review-session update to a gitignored `implementation-artifacts/` file (`sprint-status.yaml`, `deferred-work.md`, a newly-authored `spec-{story-key}.md`) once the run's worktree is torn down after a successful merge. `scm.worktree_seed` copies these files INTO a fresh worktree at start, but nothing copies the worktree's updated copies back OUT before cleanup deletes it — only git-tracked source changes survive the squash-merge, because `implementation-artifacts/` is gitignored by design (CLAUDE.md Tier 3). Net effect: the code ships correctly, but the BMAD paper trail (the sprint-status flip to `done`, the story's own `spec-*.md`, any `deferred-work.md` append the session made) silently vanishes unless a human happens to have a copy in hand and manually reconstructs it. Not story-scoped — will recur for every future bmad-loop-driven story until fixed at the orchestrator level. Fix candidates: (a) sync the worktree's `implementation-artifacts/` back to the main checkout before merge/cleanup (the `worktree_seed` copy, in reverse); (b) don't trim/delete a run's worktree until its gitignored-artifact delta is reconciled; (c) have the merge step in `bmad-loop resume` explicitly copy `implementation-artifacts/` back regardless of git-tracked status."
  evidence: Run `20260716-043830-a9bb` (story `1-5-osv-scanner-as-the-second-engine`, 2026-07-16) — after `bmad-loop resume` completed the merge (`ce2ed97bc4`) and the worktree was torn down, the main checkout's `sprint-status.yaml` still read `1-5-osv-scanner-as-the-second-engine: backlog`, and the worktree's updated `deferred-work.md` (8682 bytes, one new section appended by the review session) plus the newly-authored `spec-1-5-osv-scanner-as-the-second-engine.md` (25308 bytes) were both gone — `.bmad-loop/archive/` had no copy for this run, and `trim_artifacts=true` had already removed `worktrees/`. All three were manually reconstructed from conversation context (the spec had been read in full during the pre-merge spec-approval review) rather than recovered from disk.

## Deferred from: code review of spec-1-1-frozen-contract-verdict-lattice-projection-safety (2026-07-13)

- `status_driver.finding_id` has no referential integrity against `findings[]` (models.py:281) — a `policy-violation` report whose driver names a finding absent from `findings[]` validates at both the model and schema layers; blanket enforcement is not safely expressible in 1.1 because the error-driver grammar is owned by Story 1.7 and waiver-suppression semantics by Epic 3. Revisit when 1.7 lands the error-driver grammar.
- PEP-440-equal version spellings (`2.31` vs `2.31.0`) split component identity, double-count inventory, and fork finding IDs across runs whose extractor source flips (inventory.py:94) — `packaging` is already a declared dep that could canonicalize, but changing frozen identity semantics needs spec grounding; owned by the extractor/producer stories (1.3+/2.x).

## Deferred from: code review of spec-1-2-interfaces-null-engine-regression-harness-socket-deny (2026-07-13, Opus cycle 3)

- Poetry/PDM `pyproject.toml` whose dependencies live outside `[project].dependencies` (`[tool.poetry.dependencies]`, `[tool.pdm]`, optional-dependencies, dependency-groups) currently scans as `not-applicable`/exit-0 — a residual false-green for exit-code-only CI consumers (the only signal is a stderr line an exit-code check never sees). The single-manifest `[project].dependencies`-only extractor is by-design for 1.2; **section-aware discovery + the D2 fail-closed split is owned by Story 1.9.** When 1.9 lands, a dependency-bearing Poetry manifest must resolve to `indeterminate`/exit-1 (or a parsed inventory), never `not-applicable`. A CHARACTERIZATION test (`test_poetry_only_deps_scan_as_not_applicable_KNOWN_GAP` in tests/unit/test_discovery_extract_cli.py) pins the current behavior so 1.9 must consciously flip it. (Also raised — and already recorded — in the dev-session review's defer; re-confirmed by the Opus cycle-3 Blind Hunter.)

## Deferred from: code review of spec-1-3-deptry-as-the-first-engine (2026-07-14, independent Opus cycle)
""",
        encoding="utf-8",
    )

    entries = chain.classify_tier3_entries(path)

    assert len(entries) == 2
    assert all(e.shape is chain.Tier3Shape.LEGACY_FLAT for e in entries)
    assert all(e.id is None for e in entries)
    assert entries[0].fields["source_spec"] == (
        "`_bmad-output/projects/python-deptry-osv-scanner/implementation-artifacts/"
        "spec-1-1-frozen-contract-verdict-lattice-projection-safety.md`"
    )
    assert entries[1].fields["source_spec"] == "`docs/specs/bmad-loop-adoption.md`"


def test_legacy_header_shape_from_warden_real_excerpt(tmp_path: Path) -> None:
    """``_bmad-output/projects/pyforge-warden/implementation-artifacts/
    deferred-work.md`` lines 26-32 (verbatim) -- a non-DW
    ``## Deferred from: code review of spec-1-4-...`` heading immediately
    owning a bulleted ``- source_spec:`` field classifies ``LEGACY_HEADER``
    with ``id=None``; the SECOND, freeform bullet under the very same
    heading (no ``source_spec:`` field of its own) is correctly skipped,
    not merged into the first entry and not returned as a second one."""
    path = tmp_path / "deferred-work.md"
    path.write_text(
        """## Deferred from: code review of spec-1-4-osv-db-offline-provisioning-spike (2026-07-14, Blind Hunter + Edge Case Hunter, Opus)

- source_spec: `_bmad-output/projects/python-deptry-osv-scanner/implementation-artifacts/spec-1-4-osv-db-offline-provisioning-spike.md`
  summary: The 1.4 fixture proves offline OSV matching only for the literal pin `pdos-vuln-fixture==1.0.0`; PEP-503 name-normalization (e.g. `pdos_vuln_fixture` / `PDOS.Vuln.Fixture`) and PEP-440 version-equivalence (`1.0` vs `1.0.0`) matching against the offline DB are unexercised — Story 1.5's osv-input synthesis + Story 2.1's conda↔pypi identity map must ensure a differently-spelled-but-equivalent package still matches, or a real CVE could be silently missed.
  evidence: osv-scanner matches by normalized package name + version; the spike deliberately used a synthetic exact-name/exact-version fixture for hermeticity, so the normalization paths never ran. Raised by the Edge Case Hunter (EC11) and reflected in the decision record's Residual risks § (version-exact matching only).
- **RESOLVED (Story 5.2, 2026-07-24):** The 1.4 proof test establishes offline behavior by passing `--offline` and pointing at the fixture DB, but does NOT observe the osv-scanner subprocess's network (the in-process socket-deny harness cannot patch a child process) — a future osv that egressed under `--offline` (telemetry, transitive resolution) would pass silently; NFR-S2's central "never fetch silently" claim was trusted, not measured, for the subprocess.
  evidence: `conftest.py`'s socket-deny harness is in-process only (its own docstring notes engine subprocesses are outside it); nothing asserted zero connections occurred. Closed via the lighter "egress counter" alternative this item itself named: `tests/conformance/test_corpus_egress_counter.py` wraps the WHOLE `warden scan` process tree (CLI + every forked engine subprocess) in `strace -f -e trace=network` over the full 5.2 corpus, asserting 0 `connect`/`sendto` syscalls (Linux-only, skip-if-`strace`-unavailable — never a hard requirement elsewhere); live-verified green. Originally: source_spec `_bmad-output/projects/python-deptry-osv-scanner/implementation-artifacts/spec-1-4-osv-db-offline-provisioning-spike.md`, raised by the Blind Hunter (finding 7).
""",
        encoding="utf-8",
    )

    entries = chain.classify_tier3_entries(path)

    assert len(entries) == 1
    entry = entries[0]
    assert entry.shape is chain.Tier3Shape.LEGACY_HEADER
    assert entry.id is None
    assert entry.fields["source_spec"] == (
        "`_bmad-output/projects/python-deptry-osv-scanner/implementation-artifacts/"
        "spec-1-4-osv-db-offline-provisioning-spike.md`"
    )
    assert "PEP-503 name-normalization" in entry.fields["summary"]


def test_identified_bulleted_shape_from_doctor_tracked_ledger_real_excerpt(
    tmp_path: Path,
) -> None:
    """``_bmad-output/projects/pyforge-doctor/planning-artifacts/
    deferred-work-ledger.md`` lines 120-127 (verbatim) -- CAP-1's current
    shape, a ``### DW-FU-7-1: ...`` header with an immediate bulleted
    ``- source_spec:`` field, classifies ``IDENTIFIED_BULLETED`` and
    carries its real id."""
    path = tmp_path / "deferred-work-ledger.md"
    path.write_text(
        """### DW-FU-7-1: The Review Triage Log's `addressed_findings` never itemizes `defer` entries by the id they were just minted
- source_spec: `_bmad-output/implementation-artifacts/spec-7-1-the-emitter-mints-identity-at-defer-time.md`
  summary: The Review Triage Log's `addressed_findings` never itemizes `defer` entries by the id they were just minted, unlike `patch`/`bad_spec`, so a review pass and the DW id(s) it produced aren't linked anywhere in the spec file itself.
  evidence: Found by review pass 1 (Blind Hunter, independent adversarial pass on this story's own diff). Confirmed by inspection of `step-04-review.md`'s Classify section (step 4): the triage-log template records only `intent_gap`/`bad_spec`/`patch`/`defer`/`reject` counts plus a free-text `addressed_findings` list, and only the `patch`/`bad_spec` triage branches (step 5) actually instruct listing specifics under `addressed_findings` — the `defer` branch never did, before or after this story's edit. Pre-existing (not introduced by this story's change to the `defer` bullet itself), but now more valuable to close since `defer` entries carry real, citable ids going forward. Deferred rather than patched in this pass: fixing it means extending the Classify section's shared triage-log format and step 5's `defer` branch — a change to a different part of the file than this story's own scoped edit — and deserves its own focused pass.
  severity: medium
  status: open
  promoted: 2026-08-11 (landing pass for doctor 7-1)

""",
        encoding="utf-8",
    )

    entries = chain.classify_tier3_entries(path)

    assert len(entries) == 1
    entry = entries[0]
    assert entry.shape is chain.Tier3Shape.IDENTIFIED_BULLETED
    assert entry.id == "DW-FU-7-1"
    assert entry.fields["severity"] == "medium"
    assert entry.fields["status"] == "open"
    assert entry.fields["promoted"] == "2026-08-11 (landing pass for doctor 7-1)"


def test_identified_bulleted_shape_with_every_field_as_its_own_dashed_bullet_real_excerpt(
    tmp_path: Path,
) -> None:
    """``_bmad-output/projects/pyforge-doctor/implementation-artifacts/
    deferred-work.md`` lines 573-580 (verbatim) -- a real, live shape the
    doctor tracked-ledger excerpt above does NOT cover: every field of an
    ``IDENTIFIED_BULLETED`` entry written as its OWN top-level
    ``- <key>: value`` bullet (``- origin:``, ``- source_spec:``,
    ``- summary:``, ``- status:``), never as 2-space-indented
    continuations. Before the 2026-08-28 fix, the block-ending "sibling
    bulleted line" rule fired on ``- source_spec:`` even inside a
    header-owned block, truncating this entry to just its ``origin``
    field and misreading the rest (``source_spec``/``summary``/``status``)
    as a spurious, unrelated ``LEGACY_FLAT`` orphan with no ``summary`` of
    its own -- live-confirmed as 3 of the 4 real "blank/whitespace-only
    summary" collisions ``deferred_work_promote.py --fix`` reported
    fleet-wide that session (the other 1 was steward's ``DW-FU-11-4``,
    the identical shape)."""
    path = tmp_path / "deferred-work.md"
    path.write_text(
        """### DW-FU-12-4: A glob-less, trailing-slash spec-surface entry that can never match — foreign defect surfaced by Story 12.4's review

- origin: review-deferred (Story 12.4 pass 2, Blind Hunter, low)
- source_spec: `spec-12-4-dream-chain-gap-count-surfaces-in-the-ambient-attention-block.md`
- summary: `spec-dream-to-code-model-self-verification/SPEC.md:13` declares the glob-less, trailing-slash surface entry `.claude/skills/conda-forge-expert/tests/meta/`, which `chain.py::_glob_to_re`'s exact-match rule can never match — the directory is actually governed by pyforge-mason's `spec-packaging-factory` blanket glob. Pre-existing foreign defect (that spec is marshal-owned), surfaced incidentally; not this story's fix to make.
- status: open
- relayed: 2026-08-21 — minted in the story worktree's ephemeral Tier-3 file, re-appended to the shared checkout at landing per the spec's Auto Run Result instruction.

### DW-FU-12-5: A corrupt/hand-mangled committed baseline dies with a raw JSONDecodeError on scoped stamps

- origin: review-deferred (Story 12.5, low, both hunters)
- source_spec: `spec-12-5-the-spec-surface-baseline-write-race-is-closed.md`
- summary: `_read_baseline()` (and the pre-fix expression before it) raises a raw `json.JSONDecodeError` when `scripts/.spec-surface-baseline.json` is corrupt — pre-existing; a friendly diagnostic naming the file and the recover path (re-stamp) is the remedy. Deliberately NOT an `except -> {}` fallback, which would reintroduce the drop-every-other-spec hazard the review rejected.
- status: open
- relayed: 2026-08-21 — re-appended to the shared checkout at landing (story-worktree Tier-3 is ephemeral).
""",
        encoding="utf-8",
    )

    entries = chain.classify_tier3_entries(path)

    assert len(entries) == 2, entries
    first, second = entries
    assert first.shape is chain.Tier3Shape.IDENTIFIED_BULLETED
    assert first.id == "DW-FU-12-4"
    assert list(first.fields.keys()) == [
        "origin",
        "source_spec",
        "summary",
        "status",
    ]  # "relayed:" is not in _KNOWN_FIELD_KEYS, correctly ends the block there (pre-existing, deliberate)
    assert "chain.py::_glob_to_re" in first.fields["summary"]
    assert first.fields["status"] == "open"

    assert second.shape is chain.Tier3Shape.IDENTIFIED_BULLETED
    assert second.id == "DW-FU-12-5"
    assert "JSONDecodeError" in second.fields["summary"]

    # The regression proof: neither entry's real content spilled out as a
    # separate, spurious LEGACY_FLAT orphan.
    assert not any(e.id is None for e in entries), entries


def test_identified_bulleted_all_dashed_fields_does_not_swallow_a_real_trailing_orphan(
    tmp_path: Path,
) -> None:
    """The header-owned block's own claim must still end at the next
    HEADING (per ``_consume_identified_entry``'s own documented promise) --
    not run away and swallow a genuinely separate, TRAILING headerless
    entry that also happens to use the all-dashed-fields shape. Mirrors
    ``_bmad-output/projects/pyforge-steward/implementation-artifacts/
    deferred-work.md`` lines 702-712 (verbatim): ``DW-FU-11-4`` (all-dashed)
    immediately followed by a headerless ``- source_spec:`` orphan using
    the ORIGINAL, correct (indented-continuation) shape."""
    path = tmp_path / "deferred-work.md"
    path.write_text(
        """### DW-FU-11-4: `langflow_integration/tests.py` keeps an unguarded `cursor.fetchone()[0]`

- origin: review-deferred (Story 11.4, low)
- source_spec: `spec-11-4-isolation-and-statelessness-proven.md`
- summary: the identical `cursor.fetchone()[0]` pattern Story 11.4's own gates forced a None-guard for (mypy `[index]`) survives unguarded in `langflow_integration/tests.py` — latent only because that file sits outside the `mypy platformapp config tests` surface. Pre-existing; the story treated the file as read-only.
- status: open
- relayed: 2026-08-21 — re-appended to the shared checkout at landing (story-worktree Tier-3 is ephemeral).

- source_spec: `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-34-1-read-only-live-attach.md`
  summary: Federated-read and write-refused tests skip when the DuckDB `postgres` extension is not already in the local cache, so a CI image without that cache can stay green without proving FR-46 live ATTACH.
  evidence: `requires_postgres_ext` skipif in `test_read_only_live_attach.py`. Spec allowed AST/string gates for INSTALL; live ATTACH still needs a provisioned cache. Not a 34.1 product-path change.
""",
        encoding="utf-8",
    )

    entries = chain.classify_tier3_entries(path)

    assert len(entries) == 2, entries
    header, trailing_orphan = entries

    assert header.shape is chain.Tier3Shape.IDENTIFIED_BULLETED
    assert header.id == "DW-FU-11-4"
    assert list(header.fields.keys()) == [
        "origin",
        "source_spec",
        "summary",
        "status",
    ]  # "relayed:" is not in _KNOWN_FIELD_KEYS, correctly ends the block there (pre-existing, deliberate)
    assert "cursor.fetchone()[0]" in header.fields["summary"]

    # The genuinely separate trailing entry is its OWN orphan, not absorbed.
    assert trailing_orphan.shape is chain.Tier3Shape.LEGACY_FLAT
    assert trailing_orphan.id is None
    assert "spec-34-1-read-only-live-attach" in trailing_orphan.fields["source_spec"]
    assert "FR-46 live ATTACH" in trailing_orphan.fields["summary"]


def test_headerless_stacked_entries_still_end_at_the_next_dashed_bullet(
    tmp_path: Path,
) -> None:
    """The fix is scoped to HEADER-owned blocks only -- a headerless
    (LEGACY_FLAT) block has no heading to bound its own span, so a dashed
    ``- source_spec:`` bullet must still, deliberately, end it exactly as
    before. Two back-to-back headerless entries (the dominant real shape
    fleet-wide, e.g. atlas's own Tier-3) must classify as TWO separate
    entries, never merged into one."""
    path = tmp_path / "deferred-work.md"
    path.write_text(
        """- source_spec: `spec-one.md`
  summary: First entry's summary.
  evidence: First entry's evidence.
- source_spec: `spec-two.md`
  summary: Second entry's summary.
  evidence: Second entry's evidence.
""",
        encoding="utf-8",
    )

    entries = chain.classify_tier3_entries(path)

    assert len(entries) == 2, entries
    assert all(e.shape is chain.Tier3Shape.LEGACY_FLAT for e in entries)
    assert all(e.id is None for e in entries)
    assert entries[0].fields["summary"] == "First entry's summary."
    assert entries[1].fields["summary"] == "Second entry's summary."


def test_identified_plain_shape_and_marshal_swallow_regression_real_excerpt(
    tmp_path: Path,
) -> None:
    """``_bmad-output/projects/pyforge-marshal/implementation-artifacts/
    deferred-work.md`` lines 47-58 (verbatim) -- the exact fleet-wide bug
    case this story exists to not repeat. ``### DW-1: ...`` (line 47) uses
    plain, non-bulleted ``origin:``/``source_spec:``/``severity:``/
    ``reason:``/``status:`` keys -- ``_anonymous()`` never satisfies
    ``_ANON_RE`` against any of them, so its in-entry/field-taken state
    never advances past this header. The very next, topically UNRELATED
    headerless ``- source_spec:`` bullet (line 54, about a completely
    different spec) is what ``_anonymous()`` then wrongly treats as
    DW-1's own field (swallowed -- dropped from the anonymous count).

    ``classify_tier3_entries`` must not repeat that: DW-1 classifies
    ``IDENTIFIED_PLAIN`` with its real id, and the line-54 bullet classifies
    ``LEGACY_FLAT`` with ``id=None``, proving it is read as its own, unowned
    entry rather than absorbed into DW-1."""
    path = tmp_path / "deferred-work.md"
    path.write_text(
        """### DW-1: Follow-up review still recommended for 1-1-package-spine-verdict-lattice-findings-registry-and-the-meta-tests-that-enforce-them after the damping cap was spent
origin: review-budget-followup
source_spec: `spec-1-1-package-spine-verdict-lattice-findings-registry-and-the-meta-tests-that-enforce-them.md`
severity: low
reason: The follow-up-review damping cap (limits.max_followup_reviews = 1) was spent with the story finalized (status: done, verify green) while the review pass still recommended an independent follow-up. The work was committed by bmad-loop run 20260725-234618-4c9d; this entry preserves the lingering recommendation for a deliberate later review.
status: open

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-2-story-identity-merge-subject-rendering-and-feed-completeness.md`
  summary: `architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md`'s AD-23 rule text still literally says the canonical story key is "purely numeric on both parts," directly contradicting AD-38 (added the same day), which requires an optional ordered suffix to be preserved on read.
  evidence: Confirmed live by reading the architecture file during Story 1.2's implementation: AD-23's rule sentence is unamended even though the 2026-07-25 adversarial review (`architecture-pyforge-marshal-2026-07-25/reviews/review-ad25-39-adversarial-2026-07-25.md`, finding F-12) already flagged this exact contradiction as HIGH and noted the harness's own `bmad-loop run --story` documents accepting a split suffix (`2-6a`). Story 1.2's `core/identity.py` implements the epics.md-and-AD-38-correct behavior (suffix preserved, lowercased) per its own Design Notes, but the architecture document itself was left self-contradictory for the next reader who trusts AD-23's rule text without also reading identity.py's docstring. Pre-existing in already-final planning artifacts, outside this story's declared surface (`core/identity.py`, `core/findings.py`, `core/verdict.py`, their tests).

- source_spec: `_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-3-layered-policy-composition-with-provenance-and-validation.md`
""",
        encoding="utf-8",
    )

    entries = chain.classify_tier3_entries(path)

    assert len(entries) == 3
    header, swallow_victim, truncated_tail = entries

    # DW-1 itself: IDENTIFIED_PLAIN, its own five plain keys, real id.
    assert header.shape is chain.Tier3Shape.IDENTIFIED_PLAIN
    assert header.id == "DW-1"
    assert header.fields["origin"] == "review-budget-followup"
    assert header.fields["status"] == "open"

    # The regression proof: the very next, unrelated bullet is NOT swallowed
    # into DW-1 -- it is its own LEGACY_FLAT entry with id=None.
    assert swallow_victim.shape is chain.Tier3Shape.LEGACY_FLAT
    assert swallow_victim.id is None
    assert "spec-1-2-story-identity-merge" in swallow_victim.fields["source_spec"]

    # Cross-check against the live (buggy) `_anonymous()` on this same
    # fixture: it must NOT count the swallow victim's line as anonymous --
    # reproducing the bug this story's Never clause leaves untouched, so the
    # regression proof above is meaningful (not a no-op comparison).
    anon_lines = chain._anonymous(path)
    assert swallow_victim.start_line not in anon_lines, (
        "fixture stopped reproducing _anonymous()'s swallow bug -- "
        "the classify_tier3_entries assertions above no longer prove anything"
    )

    assert truncated_tail.shape is chain.Tier3Shape.LEGACY_FLAT
    assert truncated_tail.id is None


def test_live_marshal_file_all_nine_identified_plain_headers_do_not_swallow() -> None:
    """Story 8.1's own AC: "the bullet at line 54 (and the analogous bullet
    after each of DW-2/3/4/5/6/7/8/9) classifies as LEGACY_FLAT with
    id=None, never as owned by the preceding IDENTIFIED_PLAIN header."
    Verified here against the REAL, live
    ``_bmad-output/projects/pyforge-marshal/implementation-artifacts/
    deferred-work.md`` (not a copied fixture) -- keyed by id rather than by
    line number so it stays correct as the file grows (append-only
    discipline, this module's own Design Notes). Skips when that gitignored
    Tier-3 file is not present in this checkout (it does not survive a
    clone or a bmad-loop worktree teardown)."""
    if _REPO_ROOT is None:
        pytest.skip("not running inside a monorepo checkout (parents[6] out of range)")
    marshal_path = (
        _REPO_ROOT / "_bmad-output" / "projects" / "pyforge-marshal" / "implementation-artifacts" / "deferred-work.md"
    )
    if not marshal_path.is_file():
        pytest.skip(
            "pyforge-marshal's Tier-3 deferred-work.md is not present in this "
            "checkout (gitignored -- does not survive a clone/worktree teardown)"
        )

    entries = sorted(chain.classify_tier3_entries(marshal_path), key=lambda e: e.start_line)
    plain_ids = {f"DW-{n}" for n in range(1, 10)}
    found = {e.id for e in entries if e.shape is chain.Tier3Shape.IDENTIFIED_PLAIN and e.id in plain_ids}
    assert found == plain_ids, f"expected all of DW-1..DW-9 present as identified-plain headers, got {sorted(found)}"

    for idx, entry in enumerate(entries):
        if entry.shape is not chain.Tier3Shape.IDENTIFIED_PLAIN or entry.id not in plain_ids:
            continue
        if idx + 1 >= len(entries):
            pytest.fail(
                f"{entry.id} is the LAST entry in the file -- no following entry to "
                "check it did not swallow (the ledger's own append-only shape changed "
                "under this test; re-derive the expectation rather than IndexError)"
            )
        following = entries[idx + 1]
        assert following.shape in (chain.Tier3Shape.LEGACY_FLAT, chain.Tier3Shape.LEGACY_HEADER), (
            f"{entry.id}'s following entry was not a legacy shape: {following}"
        )
        assert following.id is None, f"{entry.id} swallowed the following entry (id={following.id!r}): {following}"


def test_wrapped_summary_and_evidence_continuation_lines_join_from_herald_real_excerpt(
    tmp_path: Path,
) -> None:
    """``_bmad-output/projects/pyforge-herald/implementation-artifacts/
    deferred-work.md`` lines 125-151 (verbatim) -- a LEGACY_FLAT entry whose
    ``summary:``/``evidence:`` fields each wrap several physical lines with
    no per-line key. ``fields["summary"]``/``fields["evidence"]`` must hold
    the FULL joined text, not just each field's first physical line."""
    path = tmp_path / "deferred-work.md"
    path.write_text(
        """- source_spec: `_bmad-output/implementation-artifacts/spec-13-2-the-serverless-intermediate-decision-recorded.md`
  summary: `herald snapshot` -- a single command consolidating the three currently-separate,
  mostly-unwired dashboard exporters (`scripts/export_web_snapshot.py`,
  `scripts/export_notices_snapshot.py`, `web/scripts/sync-progress.mjs`) into one, stamping
  `generated_at` on each -- should be built as near-term follow-up, not skipped: it would close
  the shipped v1's real "three hand-cranked snapshot hops" staleness risk (technical research
  risk #1 of 6). Worth prioritizing over routine low-priority ledger sweeps -- the fix candidate
  below is small and fully scoped, not exploratory.
  evidence: `export_web_snapshot.py`'s own docstring (lines 3-8) already designs itself as the
  shared exporter and explicitly anticipates "a future Epic 8/10 snapshot adds a sibling
  export_*_snapshot function here rather than a duplicate script"; `export_notices_snapshot.py`'s
  docstring likewise says "a later story can fold all three into one generic... script once the
  shape each Moment needs is settled" -- deferred there deliberately (Simplicity First,
  YAGNI-until-second-confirmed-use), not because of architectural uncertainty. That uncertainty
  is now resolved: all three exporters exist, ship working output, and their shapes are
  individually stable (confirmed 2026-08-11) -- the deferred precondition ("once the shape... is
  settled") is met. This work is independent of Epic 13's DB/webhook/cron scope (LB-1/2/3): it
  would close a real risk in the CURRENTLY-SHIPPED v1 dashboard regardless of whether or when the
  live backend lands, so it is not gated on any Epic 13 story and does not need insertion into
  Epic 13's own numbering -- it is overdue Epics 9/10 follow-up (whose own Stories 9.4/10.5
  shipped with a docstring explicitly deferring exactly this consolidation "to a later story"),
  not a claim that Epic 9 or 10 is reopened. Currently only `web/scripts/sync-progress.mjs` is
  wired into npm `predev`/`prebuild` (`web/package.json:8-11`); no snapshot JSON anywhere carries
  a `generated_at` field. Fix candidate: add `export_progress_snapshot`/`export_notices_snapshot`
  functions to `export_web_snapshot.py` alongside the existing `export_success_snapshot`, stamp
  `generated_at` in each, expose all three via one `herald snapshot` CLI subcommand (`cli.py`),
  and decide whether it supersedes or complements `sync-progress.mjs`'s npm-hook wiring.
""",
        encoding="utf-8",
    )

    entries = chain.classify_tier3_entries(path)

    assert len(entries) == 1
    entry = entries[0]
    assert entry.shape is chain.Tier3Shape.LEGACY_FLAT
    # `summary:` spans lines 126-132 of the real file (7 physical lines) --
    # only the first is `  summary: ...`, the rest are unmarked wrapped text.
    summary = entry.fields["summary"]
    assert "a single command consolidating the three currently-separate," in summary
    assert "mostly-unwired dashboard exporters" in summary
    assert "not exploratory." in summary
    # `evidence:` spans lines 133-151 (19 physical lines) similarly.
    evidence = entry.fields["evidence"]
    assert "own docstring (lines 3-8) already designs itself as the shared" in evidence
    assert "sync-progress.mjs`'s npm-hook wiring." in evidence


def test_continuation_join_does_not_split_on_a_bare_indented_word_colon_real_excerpts() -> None:
    """Story 8.1 review pass (2026-08-15), HIGH finding 1: the pre-fix
    ``_CONT_KEY_RE`` treated ANY indented ``word:``-shaped line as a new
    field start, not just a real known field key -- silently truncating
    ``summary``/``evidence`` and misattributing the remainder to a spurious
    key. Reproduced live in 5 real tracked-ledger entries across 3 projects
    -- read directly from the real files (not hand-transcribed, per the
    review's own instruction) so this stays byte-accurate as those ledgers
    grow:

    - atlas ``DW-AD23-2``: ``summary`` wraps through "Not fixed\\n    here:
      the `run_result` signature is E2-owned..." -- the pre-fix code split
      there, leaving ``summary`` truncated and a spurious ``here`` key
      holding the rest through ``resolution:``'s own real key line.
    - herald ``DW-13-6-1``: ``evidence`` wraps through "Not pursued in this
      story: making `deploy perimeter`..." -- same corruption, spurious
      ``story`` key.
    - herald ``DW-14-3-1``: ``evidence`` wraps through "against the real
      extractor: `extract-slides.mjs`'s `slugify..." -- same corruption,
      spurious ``extractor`` key.

    All three must now read back with the false split-text INSIDE the real
    field (not truncated, not a spurious key), and doctor's own
    ``DW-CHAIN-COMPLETENESS-1`` / atlas's ``DW-AD23-3`` (both cited by the
    review as confirmation cases, though neither happens to contain a false
    split) must still read back their real fields intact -- proving the fix
    is not a regression for the common (single-physical-line) case either.
    """
    if _REPO_ROOT is None:
        pytest.skip("not running inside a monorepo checkout (parents[6] out of range)")

    def _entry(project: str, id_needle: str) -> chain.LegacyEntry:
        path = _REPO_ROOT / "_bmad-output" / "projects" / project / "planning-artifacts" / "deferred-work-ledger.md"
        if not path.is_file():
            pytest.skip(f"{project}'s tracked deferred-work-ledger.md is not present")
        for e in chain.classify_tier3_entries(path):
            if e.id and id_needle in e.id:
                return e
        pytest.fail(f"{id_needle} not found in {path}")
        raise AssertionError("unreachable")  # for the type checker

    ad23_2 = _entry("pyforge-atlas", "AD23-2")
    assert ad23_2.shape is chain.Tier3Shape.IDENTIFIED_BULLETED
    assert "here" not in ad23_2.fields
    assert ("here: the `run_result` signature is E2-owned and touches 10 positional call sites") in ad23_2.fields[
        "summary"
    ]
    assert ad23_2.fields["summary"].endswith("kedro fires `on_pipeline_error` in-process there.")
    assert ad23_2.fields["resolution"].endswith(
        "replacing two undeclared process-lifetime couplings with one explicit lifetime."
    )

    herald_13_6_1 = _entry("pyforge-herald", "13-6-1")
    assert herald_13_6_1.shape is chain.Tier3Shape.IDENTIFIED_BULLETED
    assert "story" not in herald_13_6_1.fields
    assert ("story: making `deploy perimeter` support an arbitrary ASGI target") in herald_13_6_1.fields["evidence"]
    assert herald_13_6_1.fields["evidence"].endswith("before Herald's webhook is ever pointed at it for real.")

    herald_14_3_1 = _entry("pyforge-herald", "14-3-1")
    assert herald_14_3_1.shape is chain.Tier3Shape.IDENTIFIED_BULLETED
    assert "extractor" not in herald_14_3_1.fields
    assert ("extractor: `extract-slides.mjs`'s `slugify(label, i)`") in herald_14_3_1.fields["evidence"]

    chain_completeness = _entry("pyforge-doctor", "CHAIN-COMPLETENESS-1")
    assert chain_completeness.shape is chain.Tier3Shape.IDENTIFIED_BULLETED
    assert chain_completeness.fields["evidence"].endswith("the detector's blind spot easy to keep not noticing.")
    assert "raised" in chain_completeness.fields

    ad23_3 = _entry("pyforge-atlas", "AD23-3")
    assert ad23_3.shape is chain.Tier3Shape.IDENTIFIED_BULLETED
    assert ad23_3.fields["summary"].endswith("this one is the sole CORRECTNESS exposure among them.")


def test_identified_header_field_search_skips_interposed_html_comment_real_marshal_excerpts() -> None:
    """Story 8.1 review pass (2026-08-15), HIGH finding 2: the pre-fix
    ``_consume_identified_entry`` gave up after the first non-blank line
    beneath a ``### DW-<id>:`` header, so a header separated from its own
    ``- source_spec:`` bullet by an interposed ``<!-- id assigned ... -->``
    HTML comment (a real, live convention from the 2026-07-30 verification
    campaign) read as an EMPTY header plus a spurious, unrelated
    ``LEGACY_FLAT`` orphan for its own real content. Reproduced live in
    marshal's tracked ledger at ``## DW-1-2-1`` and ``## DW-1-10-7`` -- read
    directly from the real file (not hand-transcribed)."""
    if _REPO_ROOT is None:
        pytest.skip("not running inside a monorepo checkout (parents[6] out of range)")
    path = (
        _REPO_ROOT / "_bmad-output" / "projects" / "pyforge-marshal" / "planning-artifacts" / "deferred-work-ledger.md"
    )
    if not path.is_file():
        pytest.skip("pyforge-marshal's tracked deferred-work-ledger.md is not present")

    entries = sorted(chain.classify_tier3_entries(path), key=lambda e: e.start_line)
    by_id = {e.id: e for e in entries if e.id}

    for entry_id, summary_needle in (
        ("DW-1-2-1", "AD-23 rule text still literally says the canonical story key"),
        ("DW-1-10-7", "No project-policy source anywhere in the repo currently supplies"),
    ):
        assert entry_id in by_id, f"{entry_id} missing entirely from {path}"
        entry = by_id[entry_id]
        assert entry.shape is chain.Tier3Shape.IDENTIFIED_BULLETED, (
            f"{entry_id} misclassified as {entry.shape} -- the interposed HTML "
            "comment defeated the header's own field search"
        )
        assert summary_needle in entry.fields.get("summary", ""), (
            f"{entry_id}'s real content was not captured: {entry.fields}"
        )
        assert "evidence" in entry.fields

        duplicate_orphans = [
            other
            for other in entries
            if other.shape is chain.Tier3Shape.LEGACY_FLAT
            and other.fields.get("source_spec") == entry.fields.get("source_spec")
        ]
        assert not duplicate_orphans, (
            f"{entry_id}'s own real content also leaked out as a spurious orphan entry: {duplicate_orphans}"
        )


def test_all_four_shapes_plus_one_freeform_bullet_combined_fixture(tmp_path: Path) -> None:
    """Acceptance Criteria row 2: a fixture combining all four shapes plus
    one freeform-prose bullet -- each shape returns its correct
    ``Tier3Shape`` and id-or-None, and the freeform bullet is absent from
    the result."""
    path = tmp_path / "deferred-work.md"
    path.write_text(
        "# Deferred Work\n"
        "\n"
        "- source_spec: `flat-one.md`\n"
        "  summary: a headerless entry\n"
        "\n"
        "## Deferred from: code review of spec-x (2026-01-01)\n"
        "\n"
        "- freeform bullet with no source_spec field at all, skip me\n"
        "\n"
        "- source_spec: `legacy-header-one.md`\n"
        "  summary: owned by the Deferred-from heading above\n"
        "\n"
        "### DW-FU-8-x: a CAP-1-shaped entry\n"
        "- source_spec: `bulleted-one.md`\n"
        "  summary: identified and bulleted\n"
        "\n"
        "### DW-9: a review-budget-followup-shaped entry\n"
        "origin: review-budget-followup\n"
        "source_spec: `plain-one.md`\n"
        "status: open\n",
        encoding="utf-8",
    )

    entries = {e.id or e.fields.get("source_spec"): e for e in chain.classify_tier3_entries(path)}

    assert len(entries) == 4
    flat = entries["`flat-one.md`"]
    assert flat.shape is chain.Tier3Shape.LEGACY_FLAT
    assert flat.id is None

    header = entries["`legacy-header-one.md`"]
    assert header.shape is chain.Tier3Shape.LEGACY_HEADER
    assert header.id is None

    bulleted = entries["DW-FU-8-x"]
    assert bulleted.shape is chain.Tier3Shape.IDENTIFIED_BULLETED
    assert bulleted.fields["source_spec"] == "`bulleted-one.md`"

    plain = entries["DW-9"]
    assert plain.shape is chain.Tier3Shape.IDENTIFIED_PLAIN
    assert plain.fields["source_spec"] == "`plain-one.md`"
    assert plain.fields["origin"] == "review-budget-followup"

    assert not any("freeform bullet" in v for e in entries.values() for v in e.fields.values())


# --- classify_tier3_entries: I/O & Edge-Case Matrix rows not already covered ------


def test_classify_tier3_entries_missing_file_returns_empty_tuple(tmp_path: Path) -> None:
    entries = chain.classify_tier3_entries(tmp_path / "does-not-exist.md")

    assert entries == ()


def test_classify_tier3_entries_never_raises_on_non_utf8_bytes(tmp_path: Path) -> None:
    path = tmp_path / "deferred-work.md"
    path.write_bytes(b"### DW-1: caf\xe9 header\norigin: review-budget-followup\n")

    entries = chain.classify_tier3_entries(path)

    assert len(entries) == 1
    assert entries[0].id == "DW-1"


# --- Story 8.2: mint_id_for_entry --------------------------------------------
#
# Covers every row of the story spec's I/O & Edge-Case Matrix. Where the
# fleet's real tracked ledgers exercise the same edge-case SHAPE the spec's
# own anecdote names, the real ids are used (embedded as verbatim excerpts,
# mirroring this file's own real-excerpt discipline above) rather than
# fabricated ones -- see each test's docstring for exactly which real file
# and ids it reproduces. Two of the spec's own anecdotal ids
# (`DW-10-5-1..8`, `DW-13-3-1`) had already moved by the time this story was
# implemented (2026-08-15 same-day ledger churn); the real ids used here
# exercise the identical shape instead -- see docstrings.


def _entry_with_source_spec(source_spec: str, start_line: int = 1) -> chain.LegacyEntry:
    return chain.LegacyEntry(
        chain.Tier3Shape.LEGACY_FLAT,
        None,
        start_line,
        start_line,
        {"source_spec": source_spec},
    )


# _derive_story_key ------------------------------------------------------------


def test_derive_story_key_two_digit_groups() -> None:
    assert chain._derive_story_key("`spec-6-1-something.md`") == "6-1"


def test_derive_story_key_multi_digit_groups_both_multi_digit_real_excerpt() -> None:
    """step-04-review.md's own worked example: both numeric groups can be
    multi-digit (`6-10`, not `6-1`). Real `source_spec` value, from
    `_bmad-output/projects/pyforge-marshal/planning-artifacts/
    deferred-work-ledger.md`."""
    real = (
        "`_bmad-output/projects/pyforge-marshal/implementation-artifacts/"
        "spec-1-10-render-the-harness-policy-from-the-canonical-effectivepolicy.md`"
    )
    assert chain._derive_story_key(real) == "1-10"


def test_derive_story_key_stops_at_second_numeric_group() -> None:
    """step-04-review.md's own worked example: `spec-2-1-3-way-merge-....md`
    -> `2-1`, never `2-1-3` -- matching stops at the second numeric group."""
    assert chain._derive_story_key("`spec-2-1-3-way-merge-of-something.md`") == "2-1"


def test_derive_story_key_keeps_a_letter_suffix() -> None:
    """I/O matrix row 6. No letter-suffixed spec file exists live in the
    fleet today -- step-04-review.md's own step 2 admits this is "a latent
    shape, not a live one" -- so this is necessarily synthetic. A letter
    suffix must be kept, and must mint under a base distinct from the
    unsuffixed story."""
    assert chain._derive_story_key("`spec-6-1a-something.md`") == "6-1a"
    assert chain._derive_story_key("`spec-6-1a-something.md`") != chain._derive_story_key("`spec-6-1-something.md`")


def test_derive_story_key_falls_back_to_parent_dir_for_generic_stem_real_excerpt() -> None:
    """Real excerpt: `_bmad-output/projects/pyforge-doctor/planning-artifacts/
    deferred-work-ledger.md`'s `DW-CHAIN-COMPLETENESS-1` entry cites a
    durable story spec at `planning-artifacts/specs/
    spec-deferred-work-visibility/SPEC.md` -- stem `SPEC` is one of the
    generic container names step-04-review.md step 2 names by name, so the
    PARENT directory name (`spec-` stripped) is used instead, exactly its
    own worked fallback-slug example ("a fallback slug
    (`deferred-work-visibility`, whose trailing segment is not an
    integer)")."""
    real = "`_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-deferred-work-visibility/SPEC.md`"
    assert chain._derive_story_key(real) == "deferred-work-visibility"


def test_derive_story_key_bare_filename_with_no_directory_uses_whole_stem_real_excerpt() -> None:
    """Real excerpt: `_bmad-output/projects/pyforge-atlas/
    implementation-artifacts/deferred-work.md`'s real `source_spec` value
    (also used by this file's own
    ``test_legacy_flat_shape_from_atlas_real_excerpt`` above) has no
    `spec-<digits>-<digits>` key and no directory to fall back to -- the
    whole sanitized stem is used verbatim."""
    assert (
        chain._derive_story_key("`a1-scaffold-the-kedro-pixi-project-via-nebi.md`")
        == "a1-scaffold-the-kedro-pixi-project-via-nebi"
    )


def test_derive_story_key_raises_on_empty_or_blank_source_spec() -> None:
    with pytest.raises(ValueError):
        chain._derive_story_key("")
    with pytest.raises(ValueError):
        chain._derive_story_key("   ")
    with pytest.raises(ValueError):
        chain._derive_story_key("``")


# _collect_dw_tokens -------------------------------------------------------------


def test_collect_dw_tokens_missing_files_contribute_nothing(tmp_path: Path) -> None:
    assert (
        chain._collect_dw_tokens(
            tmp_path / "tier3-missing.md",
            tmp_path / "tracked-missing.md",
        )
        == set()
    )


def test_collect_dw_tokens_unions_both_files_and_harvests_prose_not_just_headings(
    tmp_path: Path,
) -> None:
    """Boundaries: collect every `DW-` token anywhere in the text, from
    BOTH files -- not just headings, and not just one file."""
    tier3 = tmp_path / "deferred-work.md"
    tier3.write_text("### DW-FU-6-1\nsee also DW-FU-6-2 in prose, no heading of its own\n", encoding="utf-8")
    tracked = tmp_path / "deferred-work-ledger.md"
    tracked.write_text("### DW-FU-5-1\n", encoding="utf-8")

    assert chain._collect_dw_tokens(tier3, tracked) == {"DW-FU-6-1", "DW-FU-6-2", "DW-FU-5-1"}


def test_collect_dw_tokens_unreadable_file_degrades_visibly_not_silently(
    tmp_path: Path,
) -> None:
    """Review Triage Log 2026-08-15, item 1 (HIGH): an unreadable file used
    to degrade SILENTLY to "contributes nothing" (`except Exception:
    continue`), which can mask an already-minted id and produce a duplicate
    mint -- exactly the failure this whole module exists to prevent
    (`_probe`/`_is_file`'s own masking-prevention philosophy). Narrowed to
    `except OSError`, and the degrade is now VISIBLE: it raises, mirroring
    `_load_deferred_work_baseline`'s own "visible on failure" precedent,
    rather than the removed docstring's now-incorrect "residual risk
    accepted" framing."""
    d = tmp_path / "locked"
    d.mkdir()
    tier3 = d / "deferred-work.md"
    tier3.write_text("### DW-FU-6-1\n", encoding="utf-8")
    d.chmod(0o000)
    try:
        with pytest.raises(OSError):
            chain._collect_dw_tokens(tier3, tmp_path / "does-not-exist.md")
    finally:
        d.chmod(0o755)


def test_mint_id_for_entry_unreadable_ledger_propagates_not_silently_empty(
    tmp_path: Path,
) -> None:
    """The same visible-degrade fix, exercised end-to-end through
    `mint_id_for_entry` itself -- the caller must not silently proceed as
    if an unreadable ledger were simply empty."""
    d = tmp_path / "locked"
    d.mkdir()
    tier3 = d / "deferred-work.md"
    tier3.write_text("### DW-FU-6-1\n", encoding="utf-8")
    d.chmod(0o000)
    try:
        with pytest.raises(OSError):
            chain.mint_id_for_entry(
                _entry_with_source_spec("`spec-6-1-something.md`"),
                "doctor",
                tier3,
                tmp_path / "does-not-exist.md",
            )
    finally:
        d.chmod(0o755)


# _next_free_suffix ---------------------------------------------------------------


def test_next_free_suffix_returns_none_when_nothing_collected() -> None:
    assert chain._next_free_suffix("DW-FU-7-1", set()) is None


def test_next_free_suffix_bare_base_id_counts_as_one() -> None:
    assert chain._next_free_suffix("DW-FU-6-1", {"DW-FU-6-1"}) == 2


def test_next_free_suffix_numeric_not_lexicographic_comparison() -> None:
    """`9 < 10` numerically but `"9" > "10"` lexicographically -- the
    highest counting suffix must be picked numerically."""
    collected = {"DW-FU-1-1-2", "DW-FU-1-1-9", "DW-FU-1-1-10"}
    assert chain._next_free_suffix("DW-FU-1-1", collected) == 11


def test_next_free_suffix_ignores_non_integer_remainder() -> None:
    """A `-draft` suffix and a longer dotted/multi-segment tail both reserve
    nothing."""
    collected = {"DW-FU-1-1-draft", "DW-FU-1-1-2-3"}
    assert chain._next_free_suffix("DW-FU-1-1", collected) is None


def test_next_free_suffix_whole_remainder_must_be_integer_not_last_segment() -> None:
    """step-04-review.md's own worked example: mason's real `DW-1-10-1`
    must not count toward base `DW-1-1`'s suffix, even though its LAST
    segment (`1`) looks like a valid suffix number -- the WHOLE remainder
    (`0-1`) is judged, and it is not a plain integer."""
    assert chain._next_free_suffix("DW-1-1", {"DW-1-10-1"}) is None


# mint_id_for_entry ----------------------------------------------------------------


def test_mint_id_for_entry_non_mason_no_collision(tmp_path: Path) -> None:
    """I/O matrix row 1: station=doctor, nothing collected for `DW-doctor-
    7-1*` -> bare `DW-doctor-7-1` (vocabulary Dream Ruling 14: every new
    mint carries the real station token, replacing the old generic `FU`
    placeholder)."""
    entry = _entry_with_source_spec("`spec-7-1-something-brand-new.md`")
    result = chain.mint_id_for_entry(
        entry,
        "doctor",
        tmp_path / "no-tier3.md",
        tmp_path / "no-tracked.md",
    )
    assert result == "DW-doctor-7-1"


def test_mint_id_for_entry_non_mason_bare_already_taken(tmp_path: Path) -> None:
    """I/O matrix row 2, new-grammar shape (Ruling 14): a `DW-doctor-10-1`
    sibling already collected for the same story (`10-1`) must be suffixed
    past: `DW-doctor-10-1-2`. `_bmad-output/projects/pyforge-steward/
    planning-artifacts/deferred-work-ledger.md` line 222 carries the
    pre-ruling `DW-FU-10-1` shape for this same story (proof the "harvest
    prose, not just headings" rule still applies) -- that id is untouched
    on disk (no retro-rename) and, by construction, no longer shares a
    prefix with any new-grammar base, so it cannot suffix-collide with a
    fresh mint; this test's fixture uses the new shape instead to prove the
    suffix-continuation logic still holds under it."""
    tracked = tmp_path / "deferred-work-ledger.md"
    tracked.write_text(
        "  promoted: 2026-08-15 — promoted from Tier-3 "
        "`implementation-artifacts/deferred-work.md` (id `DW-doctor-10-1` there) "
        "during the pre-shutdown deferred-work audit.\n",
        encoding="utf-8",
    )
    entry = _entry_with_source_spec("`spec-10-1-something.md`")
    result = chain.mint_id_for_entry(entry, "doctor", tmp_path / "no-tier3.md", tracked)
    assert result == "DW-doctor-10-1-2"


def test_mint_id_for_entry_non_mason_suffix_continuation(tmp_path: Path) -> None:
    """I/O matrix row 3, new-grammar shape (Ruling 14). `_bmad-output/
    projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md`
    carries the pre-ruling shape for story `9-3` (`DW-FU-9-3` bare plus
    `DW-FU-9-3-2` through `DW-FU-9-3-10`, untouched on disk); this fixture
    mirrors that same suffix run under the new `DW-doctor-9-3...` shape to
    prove minting for the same story continues past the highest, `-10`, to
    `-11` -- numerically, never by re-using the bare id or restarting at
    `-1`."""
    tracked = tmp_path / "deferred-work-ledger.md"
    tracked.write_text(
        "  promoted: 2026-08-15 — promoted from Tier-3 "
        "`implementation-artifacts/deferred-work.md` (id `DW-doctor-9-3` there) "
        "during the pre-shutdown deferred-work audit.\n"
        "  promoted: 2026-08-15 — promoted from Tier-3 "
        "`implementation-artifacts/deferred-work.md` (id `DW-doctor-9-3-2` there) "
        "during the pre-shutdown deferred-work audit.\n"
        "  promoted: 2026-08-15 — promoted from Tier-3 "
        "`implementation-artifacts/deferred-work.md` (id `DW-doctor-9-3-3` there) "
        "during the pre-shutdown deferred-work audit.\n"
        "  promoted: 2026-08-15 — promoted from Tier-3 "
        "`implementation-artifacts/deferred-work.md` (id `DW-doctor-9-3-4` there) "
        "during the pre-shutdown deferred-work audit.\n"
        "  promoted: 2026-08-15 — promoted from Tier-3 "
        "`implementation-artifacts/deferred-work.md` (id `DW-doctor-9-3-5` there) "
        "during the pre-shutdown deferred-work audit.\n"
        "  promoted: 2026-08-15 — promoted from Tier-3 "
        "`implementation-artifacts/deferred-work.md` (id `DW-doctor-9-3-6` there) "
        "during the pre-shutdown deferred-work audit.\n"
        "  promoted: 2026-08-15 — promoted from Tier-3 "
        "`implementation-artifacts/deferred-work.md` (id `DW-doctor-9-3-7` there) "
        "during the pre-shutdown deferred-work audit.\n"
        "  promoted: 2026-08-15 — promoted from Tier-3 "
        "`implementation-artifacts/deferred-work.md` (id `DW-doctor-9-3-8` there) "
        "during the pre-shutdown deferred-work audit.\n"
        "  promoted: 2026-08-15 — promoted from Tier-3 "
        "`implementation-artifacts/deferred-work.md` (id `DW-doctor-9-3-9` there) "
        "during the pre-shutdown deferred-work audit.\n"
        "  promoted: 2026-08-15 — promoted from Tier-3 "
        "`implementation-artifacts/deferred-work.md` (id `DW-doctor-9-3-10` there) "
        "during the pre-shutdown deferred-work audit.\n",
        encoding="utf-8",
    )
    entry = _entry_with_source_spec("`spec-9-3-something.md`")
    result = chain.mint_id_for_entry(entry, "doctor", tmp_path / "no-tier3.md", tracked)
    assert result == "DW-doctor-9-3-11"


def test_mint_id_for_entry_mason_no_suffix_collected(tmp_path: Path) -> None:
    """I/O matrix row 4, post-Ruling-14: mason now mints under the same
    bare-when-free convention as every other station -- `DW-mason-2-1`,
    with the real station token where mason previously had none and
    every other station carried the generic `FU` placeholder instead.
    Mason's old always-suffixed special case (`DW-{story}-<n>`, never
    bare) is retired for new mints; the 1338 existing ids it already
    produced are untouched."""
    entry = _entry_with_source_spec("`spec-2-1-something-brand-new.md`")
    result = chain.mint_id_for_entry(
        entry,
        "mason",
        tmp_path / "no-tier3.md",
        tmp_path / "no-tracked.md",
    )
    assert result == "DW-mason-2-1"


def test_mint_id_for_entry_mason_dw_1_10_1_does_not_count_toward_1_1_real_excerpt(
    tmp_path: Path,
) -> None:
    """I/O matrix row 5 and this story's Acceptance Criteria row 2, against
    a VERBATIM excerpt of `_bmad-output/projects/pyforge-mason/
    planning-artifacts/deferred-work-ledger.md` lines 57-64 -- mason's real
    pre-ruling `DW-1-10-1` entry (untouched on disk; no retro-rename).
    Minting for a NEW orphan whose derived story is `1-1` must not be
    skipped past it: under the new grammar the mint is `DW-mason-1-1`,
    mason's normal bare-when-free mint for a story with nothing collected
    under the NEW shape -- the old-shaped `DW-1-10-1` shares no prefix with
    it at all, so it trivially cannot count toward its suffix either way."""
    tracked = tmp_path / "deferred-work-ledger.md"
    tracked.write_text(
        "### DW-1-10-1\n"
        "\n"
        "- source_spec: `_bmad-output/implementation-artifacts/"
        "spec-1-10-configuration-surface-logging-and-child-output-streaming.md`\n"
        "  summary: follow-up review still recommended for 1-10 after the "
        "damping cap was spent — an independent pass is owed on the "
        "configuration surface, logging, and child-output streaming.\n"
        "  evidence: the follow-up-review damping cap "
        "(`limits.max_followup_reviews = 2`) was spent with the story "
        "finalized (status `done`, verify green) while the review pass "
        "still recommended an independent follow-up. Committed by bmad-loop "
        "run `20260809-231234-a3cb`. 1-10 also ran to both ceilings — dev "
        "attempt 2/2 and review cycle 3/3 — and cleared on its LAST cycle "
        "rather than escalating, which is exactly the profile where an "
        "independent pass is worth spending.\n"
        "  promoted: 2026-08-10 — promoted from Tier-3 "
        "`implementation-artifacts/deferred-work.md` (id `DW-1` there) under "
        "THIS ledger's own `DW-<story>-<n>` convention (`DW-1-3-1`, "
        "`DW-1-4-1`, `DW-1-4-2`), which differs from doctor's and atlas's "
        "`DW-FU-<story>`; the station's own precedent wins. A generic `DW-1` "
        "would collide with the next damped story, and Tier-3 is gitignored "
        "so the entry would not survive a clone. Marshal Story 4.13 — "
        "landed earlier today in PR #381 — exists to make this promotion an "
        "obligation of the story rather than archaeology someone performs "
        "later.\n"
        "  status: open\n",
        encoding="utf-8",
    )
    entry = _entry_with_source_spec("`spec-1-1-something-brand-new.md`")
    result = chain.mint_id_for_entry(entry, "mason", tmp_path / "no-tier3.md", tracked)
    assert result == "DW-mason-1-1"


def test_mint_id_for_entry_letter_suffixed_story_key_distinct_from_unsuffixed(
    tmp_path: Path,
) -> None:
    """I/O matrix row 6 -- necessarily synthetic (no letter-suffixed spec
    file exists live in the fleet today, step-04-review.md's own
    admission)."""
    no_tier3 = tmp_path / "no-tier3.md"
    no_tracked = tmp_path / "no-tracked.md"
    result_a = chain.mint_id_for_entry(
        _entry_with_source_spec("`spec-6-1a-something.md`"),
        "doctor",
        no_tier3,
        no_tracked,
    )
    result_plain = chain.mint_id_for_entry(
        _entry_with_source_spec("`spec-6-1-something.md`"),
        "doctor",
        no_tier3,
        no_tracked,
    )
    assert result_a == "DW-doctor-6-1a"
    assert result_plain == "DW-doctor-6-1"


def test_mint_id_for_entry_raises_on_missing_source_spec_field(tmp_path: Path) -> None:
    """I/O matrix row 7 and this story's Acceptance Criteria row 3: no
    `source_spec` field at all -> raise, never mint a phantom
    `DW-`-prefixed-nothing id."""
    entry = chain.LegacyEntry(chain.Tier3Shape.LEGACY_FLAT, None, 12, 12, {})
    with pytest.raises(ValueError, match="line 12"):
        chain.mint_id_for_entry(
            entry,
            "doctor",
            tmp_path / "no-tier3.md",
            tmp_path / "no-tracked.md",
        )


def test_mint_id_for_entry_raises_on_blank_source_spec_field(tmp_path: Path) -> None:
    entry = _entry_with_source_spec("   ")
    with pytest.raises(ValueError):
        chain.mint_id_for_entry(
            entry,
            "doctor",
            tmp_path / "no-tier3.md",
            tmp_path / "no-tracked.md",
        )


def test_mint_id_for_entry_never_writes_to_either_path(tmp_path: Path) -> None:
    """Boundaries: 'Never write to tier3_path/tracked_path' -- pure
    computation, no side effects."""
    tier3 = tmp_path / "deferred-work.md"
    tracked = tmp_path / "deferred-work-ledger.md"
    tier3.write_text("### DW-FU-3-1\n", encoding="utf-8")
    tracked.write_text("### DW-FU-3-1\n", encoding="utf-8")
    tier3_before = tier3.read_bytes()
    tracked_before = tracked.read_bytes()

    chain.mint_id_for_entry(
        _entry_with_source_spec("`spec-3-1-something.md`"),
        "doctor",
        tier3,
        tracked,
    )

    assert tier3.read_bytes() == tier3_before
    assert tracked.read_bytes() == tracked_before


def test_mint_id_for_entry_station_is_never_derived_from_ambient_state(tmp_path: Path) -> None:
    """Design Notes: `station` is an explicit caller-supplied parameter,
    never resolved from ambient active-project state -- an arbitrary KNOWN
    station string mints under its OWN token, never a generic placeholder
    (updated 2026-08-15: the original used a garbage `"unknown"` value, but
    Review Triage Log item 3 now requires an unrecognized station to raise
    rather than silently fall through -- see
    `test_mint_id_for_entry_unrecognized_station_raises` for that case;
    `"atlas"` here is a real, known station)."""
    result = chain.mint_id_for_entry(
        _entry_with_source_spec("`spec-11-1-something.md`"),
        "atlas",
        tmp_path / "no-tier3.md",
        tmp_path / "no-tracked.md",
    )
    assert result == "DW-atlas-11-1"


# Review Triage Log 2026-08-15, item 3 (HIGH): station-string robustness ----------


def test_mint_id_for_entry_mason_station_variants_normalize_to_mason_branch(
    tmp_path: Path,
) -> None:
    """`"pyforge-mason"`, `"Mason"`, and `" mason "` must all normalize to
    the same literal `mason` station token in the minted id -- normalizing
    common variants defensively is zero-cost and the safer choice given
    `station` is caller-supplied."""
    no_tier3, no_tracked = tmp_path / "no-tier3.md", tmp_path / "no-tracked.md"
    for station in ("pyforge-mason", "Mason", " mason "):
        result = chain.mint_id_for_entry(
            _entry_with_source_spec("`spec-2-1-something-brand-new.md`"),
            station,
            no_tier3,
            no_tracked,
        )
        assert result == "DW-mason-2-1", station


def test_mint_id_for_entry_unrecognized_station_raises(tmp_path: Path) -> None:
    """An unrecognized or empty/blank station must raise, never silently
    fall through to the generic FU-prefixed branch -- the exact defect
    Blind Hunter + Edge Case Hunter found live (a garbage value silently
    corrupting mason's id shape with no symptom)."""
    entry = _entry_with_source_spec("`spec-1-1-something.md`")
    for bad_station in ("", "   ", "not-a-station", "pyforge-unknown"):
        with pytest.raises(ValueError):
            chain.mint_id_for_entry(
                entry,
                bad_station,
                tmp_path / "no-tier3.md",
                tmp_path / "no-tracked.md",
            )


def test_mint_id_for_entry_mason_bare_legacy_id_already_collected_real_excerpt(
    tmp_path: Path,
) -> None:
    """Review Triage Log 2026-08-15, item 9: no end-to-end test previously
    exercised mason's BARE (non-suffixed) legacy id already-collected case
    through `mint_id_for_entry` itself -- only unit-tested directly against
    `_next_free_suffix`. A bare `DW-<story>` legacy id counts as suffix `1`,
    so mason's next mint for the same story continues from `2`."""
    tracked = tmp_path / "deferred-work-ledger.md"
    tracked.write_text("### DW-1-1\n\n- status: open\n", encoding="utf-8")
    entry = _entry_with_source_spec("`spec-1-1-something-else.md`")
    result = chain.mint_id_for_entry(entry, "mason", tmp_path / "no-tier3.md", tracked)
    assert result == "DW-1-1-2"


# Review Triage Log 2026-08-15, item 4 (medium): guard against re-minting ---------


def test_mint_id_for_entry_raises_if_entry_already_has_an_id(tmp_path: Path) -> None:
    """A plausible Story 8.3 caller mistake: minting a fresh id for an entry
    that already carries one (an `IDENTIFIED_*` shape) must raise rather
    than produce a redundant, orphaned id."""
    entry = chain.LegacyEntry(
        chain.Tier3Shape.IDENTIFIED_PLAIN,
        "DW-FU-5-1",
        10,
        10,
        {"source_spec": "`spec-5-1-something.md`"},
    )
    with pytest.raises(ValueError, match="DW-FU-5-1"):
        chain.mint_id_for_entry(
            entry,
            "doctor",
            tmp_path / "no-tier3.md",
            tmp_path / "no-tracked.md",
        )


# Review Triage Log 2026-08-15, item 5 (medium): backtick/`.md`-stripping boundaries -


def test_derive_story_key_single_leading_backtick_no_matching_pair() -> None:
    """Item 5a: a lone LEADING backtick with no matching trailing one must
    still be handled sensibly, not garbled into the fallback whole-stem
    path with the backtick still attached."""
    assert chain._derive_story_key("`spec-6-1-something.md") == "6-1"


def test_derive_story_key_single_trailing_backtick_immediately_after_md() -> None:
    """Item 5a/5b: a lone TRAILING backtick glued immediately after `.md`
    (no matching leading backtick) must not defeat the `.md`-suffix check --
    the un-stripped backtick used to make `filename.lower().endswith(".md")`
    false, leaving the whole `"...md`"` string as the stem."""
    assert chain._derive_story_key("spec-6-1-something.md`") == "6-1"


def test_derive_story_key_trailing_parenthetical_prose_after_backtick_span_real_excerpt() -> None:
    """Item 5c, VERBATIM real excerpt: `_bmad-output/projects/pyforge-atlas/
    planning-artifacts/deferred-work-ledger.md` line 398's `source_spec`
    value -- a backtick-quoted filename followed by trailing parenthetical
    prose OUTSIDE the backticks (19 lines fleet-wide carry this exact
    shape). Only the backtick-quoted span must be isolated; the trailing
    prose must never reach the derivation."""
    real = "`cfe-atlas-datapipeline-kedro-migration.md` (Story E1, FR-11)"
    assert chain._derive_story_key(real) == "cfe-atlas-datapipeline-kedro-migration"


# Review Triage Log 2026-08-15, item 6 (low): case-insensitive generic stems ------


def test_derive_story_key_generic_stems_are_case_insensitive() -> None:
    """`Spec.md`/`Readme.md`/`INDEX.md` are the same generic container as
    `SPEC.md`/`README.md`/`index.md` under a different casing -- all must
    fall back to the parent directory name, not be treated as a distinct
    (wrong) story key."""
    assert (
        chain._derive_story_key(
            "`_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-deferred-work-visibility/Spec.md`"
        )
        == "deferred-work-visibility"
    )
    assert (
        chain._derive_story_key(
            "`_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-deferred-work-visibility/Readme.md`"
        )
        == "deferred-work-visibility"
    )
    assert (
        chain._derive_story_key(
            "`_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-deferred-work-visibility/INDEX.md`"
        )
        == "deferred-work-visibility"
    )


# Review Triage Log 2026-08-15, item 2 (HIGH): batch-minting accumulator ----------
#
# Fixture below is a VERBATIM excerpt (the `- source_spec:` bullet line,
# repeated -- summary/evidence prose omitted as immaterial to minting, same
# discipline as this file's other real-excerpt tests trimming unrelated
# prose) of `_bmad-output/projects/pyforge-doctor/implementation-artifacts/
# deferred-work.md`'s real 24 `LEGACY_FLAT` orphan entries, all sharing
# `source_spec` `spec-6-4-the-ledger-verdicts-come-home.md` (story key
# `6-4`) -- this IS the SAME live scenario Blind Hunter used, live-verified
# again in this review pass (24 real entries, all 8 real fleet ledgers hold
# 76 total). The tracked-ledger heading line is the identical real
# `### DW-FU-6-4: ...` heading from `_bmad-output/projects/pyforge-doctor/
# planning-artifacts/deferred-work-ledger.md`.

_REAL_6_4_ORPHAN_BULLET = (
    "- source_spec: `_bmad-output/implementation-artifacts/spec-6-4-the-ledger-verdicts-come-home.md`\n"
)
_REAL_6_4_TRACKED_HEADING = (
    "### DW-FU-6-4: Follow-up review still recommended for "
    "6-4-the-ledger-verdicts-come-home after the damping cap was spent\n"
)


def test_mint_id_for_entry_batch_minting_without_accumulator_collides_real_data(
    tmp_path: Path,
) -> None:
    """Regression proof for the ORIGINAL bug, against real data: minting
    repeatedly for entries that share a derived story key, with no
    accumulator threaded through, collides every time -- confirming the
    defect the companion test below then fixes. Every one of the 24 real
    orphans mints the identical `DW-FU-6-4-2` without an accumulator."""
    tier3 = tmp_path / "deferred-work.md"
    tier3.write_text("# Deferred Work\n\n" + _REAL_6_4_ORPHAN_BULLET * 24, encoding="utf-8")
    tracked = tmp_path / "deferred-work-ledger.md"
    tracked.write_text(_REAL_6_4_TRACKED_HEADING, encoding="utf-8")

    entries = chain.classify_tier3_entries(tier3)
    orphans = [e for e in entries if e.id is None]
    assert len(orphans) == 24

    results = [chain.mint_id_for_entry(e, "doctor", tier3, tracked) for e in orphans]
    assert results == ["DW-FU-6-4-2"] * 24


def test_mint_id_for_entry_batch_minting_with_accumulator_no_collisions_real_data(
    tmp_path: Path,
) -> None:
    """The fix, against the identical real data above: threading a shared
    `already_minted` accumulator through each call in the batch -- adding
    every returned id to it immediately, matching the source prose's own
    "mint one at a time, write before minting next" discipline -- produces
    24 UNIQUE ids with zero duplicates, where the unfixed code minted
    `DW-FU-6-4-2` 24 times over."""
    tier3 = tmp_path / "deferred-work.md"
    tier3.write_text("# Deferred Work\n\n" + _REAL_6_4_ORPHAN_BULLET * 24, encoding="utf-8")
    tracked = tmp_path / "deferred-work-ledger.md"
    tracked.write_text(_REAL_6_4_TRACKED_HEADING, encoding="utf-8")

    entries = chain.classify_tier3_entries(tier3)
    orphans = [e for e in entries if e.id is None]
    assert len(orphans) == 24

    already_minted: set[str] = set()
    results = []
    for e in orphans:
        minted = chain.mint_id_for_entry(e, "doctor", tier3, tracked, already_minted)
        already_minted.add(minted)
        results.append(minted)

    assert len(results) == 24
    assert len(set(results)) == 24, "batch minting must not collide within one batch"
    assert results == [f"DW-FU-6-4-{n}" for n in range(2, 26)]


def test_mint_id_for_entry_accumulator_folds_in_like_a_collected_ledger_id(
    tmp_path: Path,
) -> None:
    """`already_minted` must be treated exactly as if its contents had
    already been read from the ledger files -- a synthetic, minimal proof
    alongside the real-data regression tests above."""
    entry = _entry_with_source_spec("`spec-4-1-something.md`")
    no_tier3, no_tracked = tmp_path / "no-tier3.md", tmp_path / "no-tracked.md"

    first = chain.mint_id_for_entry(entry, "doctor", no_tier3, no_tracked)
    assert first == "DW-FU-4-1"

    already_minted = {first}
    second = chain.mint_id_for_entry(entry, "doctor", no_tier3, no_tracked, already_minted)
    assert second == "DW-FU-4-1-2"


# --- Story 25.6: spec-frontmatter deferred intake --------------------------------


def _write_spec(target: Path, project: str, rel: str, body: str) -> Path:
    path = _project_dir(target, project) / "planning-artifacts" / "specs" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


_CANARY_SPEC = """\
---
title: canary
status: done
deferred:
  - summary: GitHub-releases fallback for npm-invisible packages
    evidence: bmad-loop 404 on npm
    location: src/pyforge/doctor/sources/bmad_method.py
    severity: medium
---

# Canary
"""


def test_spec_frontmatter_only_deferral_reports_fail(tmp_path: Path) -> None:
    _write_baseline(tmp_path, {})
    _write_spec(tmp_path, "proj", "spec-14-1-canary.md", _CANARY_SPEC)
    _write_tracked(tmp_path, "proj", "# empty\n")

    findings = chain.gather_deferred_work(tmp_path)

    assert any(f.check == "spec-frontmatter-only-deferral" for f in findings)
    finding = next(f for f in findings if f.check == "spec-frontmatter-only-deferral")
    assert finding.status is DoctorStatus.FAIL


def test_spec_frontmatter_deferral_ingested_reports_no_finding(tmp_path: Path) -> None:
    _write_baseline(tmp_path, {})
    spec_path = _write_spec(tmp_path, "proj", "spec-14-1-canary.md", _CANARY_SPEC)
    findings_raw, _ = chain.parse_spec_frontmatter_deferrals(spec_path, project_dir=_project_dir(tmp_path, "proj"))
    assert len(findings_raw) == 1
    finding = findings_raw[0]
    new_id = chain.mint_id_for_entry(
        chain.LegacyEntry(
            chain.Tier3Shape.LEGACY_FLAT,
            None,
            0,
            0,
            {"source_spec": f"`{finding.spec_rel}`", "summary": finding.summary},
        ),
        "doctor",
        tmp_path / "missing-tier3.md",
        tmp_path / "missing-tracked.md",
    )
    block = chain.format_frontmatter_intake_entry(new_id, finding)
    _write_tracked(tmp_path, "proj", block + "\n")

    findings = chain.gather_deferred_work(tmp_path)
    assert not any(f.check == "spec-frontmatter-only-deferral" for f in findings)


def test_flatten_deferred_scalar_marks_truncation_and_records_original_length() -> None:
    # DW-FU-21-8-6: a scalar longer than the limit used to be hard-sliced with no
    # marker (silent, mid-sentence/mid-word data loss). It must now say so, and the
    # original (untruncated) length must be recoverable from the marker itself.
    long_text = "word " * 200  # 1000 chars, well past the 500-char summary limit
    flat = " ".join(long_text.split())
    out = chain._flatten_deferred_scalar(long_text, 500)
    assert "[truncated" in out
    assert str(len(flat)) in out  # original length is recorded, not silently lost
    assert out.startswith(flat[:20])  # the surviving head is real content, not mangled


def test_flatten_deferred_scalar_short_value_is_returned_unmarked() -> None:
    # No truncation occurred -> no marker, exact value preserved (regression guard
    # against over-eagerly appending the marker to values under the limit).
    assert chain._flatten_deferred_scalar("short summary", 500) == "short summary"


def test_spec_frontmatter_deferral_long_summary_is_marked_not_silently_corrupted(
    tmp_path: Path,
) -> None:
    # DW-FU-21-8-6 end-to-end: a spec frontmatter `summary:` over 500 chars must not
    # be silently corrupted mid-sentence in the ingested finding (which becomes both
    # the ledger's `###` heading AND its `summary:` line).
    long_summary = "The widget subsystem silently drops every third request. " * 12
    assert len(long_summary) > 500
    spec_body = (
        "---\n"
        "title: canary\n"
        "status: done\n"
        "deferred:\n"
        f"  - summary: {long_summary.strip()!r}\n"
        "    evidence: seen in prod logs\n"
        "    location: src/pyforge/doctor/sources/widget.py\n"
        "    severity: medium\n"
        "---\n\n# Canary\n"
    )
    spec_path = _write_spec(tmp_path, "proj", "spec-long-summary.md", spec_body)
    findings, malformed = chain.parse_spec_frontmatter_deferrals(spec_path, project_dir=_project_dir(tmp_path, "proj"))
    assert not malformed
    assert len(findings) == 1
    summary = findings[0].summary
    assert "[truncated" in summary
    assert str(len(" ".join(long_summary.split()).strip())) in summary


# --- Story 28.1 / CAP-81: line-anchored fences, not the first `---` ------------

_CHAIN_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "chain"


def test_marshal_50_5_fixture_parses_both_deferrals() -> None:
    """The bug that motivated Story 28.1: marshal's tracked
    ``spec-50-5-the-promoter-reads-a-spec-through-its-banner.md`` declares
    TWO ``deferred:`` frontmatter items, but the first item's own
    ``evidence:`` block quotes the literal text ``lines[0] == "---"`` --
    a ``"---"`` substring embedded mid-block. The old
    ``_frontmatter_parse`` (``text.split("---", 2)``) truncated the YAML at
    THAT occurrence instead of the real closing fence, silently losing the
    first item's ``location:`` and the second item entirely (verified,
    during development: before this story's fix, this exact fixture
    produced one deferral with no ``location:`` and fingerprint
    ``fdd6bce25c09``; reverting ``_frontmatter_parse`` to the old
    split-based form and re-running this test reproduces that failure).

    Reads a byte-verbatim SNAPSHOT under ``tests/fixtures/chain/`` -- NOT
    marshal's live planning tree. Provenance: copied from
    ``_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/
    spec-50-5-the-promoter-reads-a-spec-through-its-banner.md`` as landed
    on ``main`` at ``62c09c2e27`` (24,222 bytes), 2026-09-19. A live read
    would let a marshal-only edit to that spec's ``deferred:`` red doctor's
    suite on the next unrelated doctor PR, and CI's ``src/shared/packages/**``
    paths filter cannot fire this lane on the marshal edit (the
    MRS-GATE-001 live-baseline class that blocked this story at pass 0).
    Fingerprints/location/severity cross-checked against the same entries'
    already-hand-reconciled ``origin:``/``severity:`` fields in marshal's
    ``deferred-work-ledger.md`` (``DW-FU-50-5``/``DW-FU-50-6``), which is how
    both were independently verified correct outside this parser."""
    spec_path = _CHAIN_FIXTURES / "spec-50-5-the-promoter-reads-a-spec-through-its-banner.md"
    assert spec_path.is_file()

    fm, unparseable = chain._frontmatter_parse(spec_path)
    assert unparseable is False
    assert len(fm.get("deferred") or []) == 2

    findings, malformed = chain.parse_spec_frontmatter_deferrals(spec_path)
    assert malformed == ()
    assert len(findings) == 2

    first, second = findings
    assert first.location == (
        "src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/spec_low_risk.py::parse_declared_low_risk"
    )
    assert first.severity == "medium"
    assert first.fingerprint == "3bc3d91bdf95"  # matches the ledger's own `origin:` line

    assert second.location == (
        "src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/promotion.py::_skip_leading_banner"
    )
    assert second.severity == "high"
    assert second.fingerprint == "5434eca8c9e5"


def test_tier3_only_deferral_still_reports_fail(tmp_path: Path) -> None:
    """Loop-run bridge regression: Tier-3-only ids still fire."""
    _write_baseline(tmp_path, {})
    _write_tier3(tmp_path, "proj", "## DW-99\nloop harvest placeholder\n")
    _write_tracked(tmp_path, "proj", "## DW-other\nstatus: open\n")

    findings = chain.gather_deferred_work(tmp_path)

    assert any(f.check == "tier3-only-deferral" for f in findings)


# --- Intake location gate (Story 21.8 / CAP-9) ---------------------------------


def _finding(summary: str, evidence: str, location: str = "") -> chain.SpecDeferredFinding:
    return chain.SpecDeferredFinding(
        summary=summary,
        evidence=evidence,
        location=location,
        severity="",
        fingerprint="fp1",
        spec_path=Path("specs/spec-x/SPEC.md"),
        spec_rel="_bmad-output/projects/p/planning-artifacts/specs/spec-x/SPEC.md",
    )


def test_intake_entry_citing_no_code_has_no_resolvable_location() -> None:
    finding = _finding("deferred to a later story", "out of scope for this pass")
    assert not chain.finding_has_resolvable_location(finding)
    assert "missing resolvable `location:`" in chain.format_intake_location_refusal(finding)


def test_intake_entry_prose_with_slash_is_not_resolvable() -> None:
    finding = _finding(
        "deferred to a later story",
        "out of scope / follow-up pass",
    )
    assert not chain.finding_has_resolvable_location(finding)


def test_intake_entry_citing_code_in_summary_is_resolvable() -> None:
    finding = _finding(
        "fix `scripts/deferred_work_intake.py` gate ordering",
        "out of scope for this pass",
    )
    assert chain.finding_has_resolvable_location(finding)


def test_intake_entry_citing_code_in_evidence_is_resolvable() -> None:
    finding = _finding(
        "tighten the parser",
        "`src/pyforge/doctor/sources/chain.py` over-matches",
    )
    assert chain.finding_has_resolvable_location(finding)


def test_intake_entry_with_explicit_location_is_resolvable() -> None:
    finding = _finding(
        "a thing",
        "some prose",
        location="scripts/detectors.py",
    )
    assert chain.finding_has_resolvable_location(finding)
    block = chain.format_frontmatter_intake_entry("DW-1-3", finding)
    assert "location: scripts/detectors.py" in block


def test_intake_entry_citing_only_a_dotted_symbol_is_not_resolvable() -> None:
    finding = _finding("a thing", "`os.replace` is not atomic on Windows")
    assert not chain.finding_has_resolvable_location(finding)


def test_intake_entry_source_spec_path_does_not_count_as_a_citation() -> None:
    finding = _finding("a thing", "no code named here at all")
    assert not chain.finding_has_resolvable_location(finding)
