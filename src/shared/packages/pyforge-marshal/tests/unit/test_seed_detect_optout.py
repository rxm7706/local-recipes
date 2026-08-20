"""Unit tests for ``pyforge.marshal.seed.detect.optout`` (Story 8.5) --
covers every classification and finding row of the spec's I/O & Edge-Case
Matrix, led by the AC's two contrasting tests:

* markers deleted (a ``managed[]`` claim recorded, the region no longer in
  the file) -> ``OPTED_OUT`` + one INFO ``opted-out`` finding;
* never installed (no claim, no recorded opt-out, ``state`` possibly
  ``None``) -> ``MISSING`` + one DRIFT ``managed-region-missing`` finding;

then the already-recorded (sticky) row, the region-present row, the
unparseable-file degrade, the empty-``text`` degrade (a DELETED file is not
a pile of opt-outs), the non-hybrid degrade, ``opt_outs_to_record``'s
verb-facing pair list, and both reinstate round trips through
``record_opt_out``/``clear_opt_out`` -- the recorded one and the DERIVED
one, whose withdrawal rests on the ``managed[]`` claim being dropped.

Regions are built by round-tripping through ``render_begin``/``render_end``
rather than by hand-writing marker syntax, mirroring
``test_seed_regions_apply.py``'s own convention: a fixture that does not
actually parse proves nothing about a classifier that reads parsed spans.
"""

from __future__ import annotations

import ast
import dataclasses
import importlib.util
from pathlib import Path

import pytest
from pyforge.marshal.seed.detect import optout as optout_module
from pyforge.marshal.seed.detect.findings import REMEDIES, FindingType, Severity
from pyforge.marshal.seed.detect.optout import (
    RegionDisposition,
    RegionStatus,
    classify_regions,
    opt_outs_to_record,
    region_findings,
)
from pyforge.marshal.seed.model.manifest import (
    AppliesTo,
    ArtifactClass,
    ManifestEntry,
    Region,
)
from pyforge.marshal.seed.model.version import ModelVersion
from pyforge.marshal.seed.regions.markers import (
    RegionFormat,
    region_sha,
    render_begin,
    render_end,
)
from pyforge.marshal.seed.state import (
    ManagedArtifact,
    RegionSpanRecord,
    SeedState,
    clear_opt_out,
    record_opt_out,
)

_VERSION = ModelVersion.parse("1.0.0")


def _hybrid(entry_id: str, path: str, *region_names: str) -> ManifestEntry:
    return ManifestEntry(
        id=entry_id,
        artifact_class=ArtifactClass.HYBRID_MANAGED_REGION,
        path=path,
        applies_to=AppliesTo.BOTH,
        rationale="test",
        format=RegionFormat.HTML,
        regions=tuple(Region(name=name, anchor=("# anchor",)) for name in region_names),
    )


def _whole_file(entry_id: str, path: str) -> ManifestEntry:
    return ManifestEntry(
        id=entry_id,
        artifact_class=ArtifactClass.COPIED_MANAGED,
        path=path,
        applies_to=AppliesTo.BOTH,
        rationale="test",
    )


def _doc(*lines: str) -> str:
    return "".join(f"{line}\n" for line in lines)


def _rendered_region(name: str, body: str = "line1") -> tuple[str, ...]:
    """One well-formed managed region's three lines, ready to splice into a
    ``_doc(...)`` call."""
    sha = region_sha(f"{body}\n")
    return (
        render_begin(RegionFormat.HTML, name, _VERSION, sha),
        body,
        render_end(RegionFormat.HTML, name),
    )


def _state(
    *,
    managed: tuple[ManagedArtifact, ...] = (),
    opted_out: tuple[str, ...] = (),
) -> SeedState:
    """A minimal schema-valid ``SeedState`` carrying only the two fields
    this module reads -- ``managed`` and ``opted_out``."""
    return SeedState(
        model_version=_VERSION,
        seed_model_version="0.1.0",
        adopted_at="2026-08-20T09:15:00Z",
        last_update="2026-08-20T09:15:00Z",
        mode="adopt",
        agents=("claude-code",),
        managed=managed,
        skips=(),
        legacy=(),
        migrations_applied=(),
        opted_out=opted_out,
    )


def _region_claim(
    entry_id: str, path: str, region: str, *, start: int = 7, end: int = 20
) -> ManagedArtifact:
    return ManagedArtifact(
        id=entry_id,
        path=path,
        artifact_class="hybrid-managed-region",
        body_sha="0123abcd",
        inserted_region_span=RegionSpanRecord(name=region, start=start, end=end),
    )


# --- the AC's two contrasting tests (I/O Matrix rows 1 and 2) ---------------


def test_markers_deleted_from_a_previously_installed_region_classify_opted_out():
    """The AC's first test: state records that Genesis installed this
    region, and the file no longer carries it. That deletion IS the opt-out
    (FR-112) -- never ``managed-region-missing``."""
    entry = _hybrid("agents-md", "AGENTS.md", "tiers")
    text = _doc("intro", "outro")
    state = _state(managed=(_region_claim("agents-md", "AGENTS.md", "tiers"),))

    (status,) = classify_regions(entry, text, state)

    assert status == RegionStatus(
        artifact_id="agents-md",
        path="AGENTS.md",
        region="tiers",
        disposition=RegionDisposition.OPTED_OUT,
    )

    (finding,) = region_findings((status,))
    assert finding.severity is Severity.INFO
    assert finding.type is FindingType.OPTED_OUT
    assert finding.severity is not Severity.HARD
    assert finding.severity is not Severity.DRIFT


def test_a_region_that_was_never_installed_classifies_missing():
    """The AC's second test: same file, same manifest entry -- but nothing
    in state says Genesis ever put the region there."""
    entry = _hybrid("agents-md", "AGENTS.md", "tiers")
    text = _doc("intro", "outro")

    (status,) = classify_regions(entry, text, _state())

    assert status.disposition is RegionDisposition.MISSING

    (finding,) = region_findings((status,))
    assert finding.severity is Severity.DRIFT
    assert finding.type is FindingType.MANAGED_REGION_MISSING


def test_a_never_adopted_repo_classifies_every_declared_region_missing():
    """``read_state`` returns ``None`` for a repo Genesis never adopted --
    the same ``MISSING`` verdict, reached without a state document at all."""
    entry = _hybrid("agents-md", "AGENTS.md", "tiers", "model-badge")

    statuses = classify_regions(entry, _doc("intro"), None)

    assert [status.disposition for status in statuses] == [
        RegionDisposition.MISSING,
        RegionDisposition.MISSING,
    ]


# --- I/O Matrix row 3: an already-recorded opt-out is sticky ----------------


def test_a_recorded_opt_out_is_sticky_once_the_managed_claim_is_gone():
    """``record_opt_out`` drops the ``managed[]`` claim, so rung 3 can no
    longer fire -- rung 2 (the recorded key) is what keeps the opt-out
    permanent, which is the whole reason the ladder has both."""
    entry = _hybrid("agents-md", "AGENTS.md", "tiers")
    state = _state(opted_out=("agents-md#tiers",))

    (status,) = classify_regions(entry, _doc("intro"), state)

    assert state.managed == ()
    assert status.disposition is RegionDisposition.OPTED_OUT


def test_an_opt_out_recorded_for_another_artifact_does_not_leak():
    entry = _hybrid("agents-md", "AGENTS.md", "tiers")
    state = _state(opted_out=("claude-md#tiers",))

    (status,) = classify_regions(entry, _doc("intro"), state)

    assert status.disposition is RegionDisposition.MISSING


def test_state_records_at_most_one_region_span_per_artifact():
    """What replaced a VACUOUS test. This slot used to assert that a claim
    on ANOTHER region of the same artifact does not leak into this one --
    a state ``SeedState`` forbids, so it passed by construction and proved
    nothing about rung 3.

    The real, now-documented constraint is this one (module docstring):
    duplicate ``managed[].id`` is rejected, so one artifact carries at most
    one recorded ``inserted_region_span``."""
    claim = _region_claim("agents-md", "AGENTS.md", "tiers")
    sibling = dataclasses.replace(
        claim,
        path="AGENTS-2.md",
        inserted_region_span=RegionSpanRecord(name="model-badge", start=30, end=40),
    )
    with pytest.raises(ValueError, match=r"SeedState\.managed\[\]\.id: must be unique"):
        _state(managed=(claim, sibling))


def test_the_one_recorded_span_retires_its_region_and_leaves_its_siblings_missing():
    """That limitation stated as behavior, so nobody reads rung 3 as
    covering every declared region: both regions were deleted from the file,
    state can attest to only one of them, and the other stays eligible for
    insertion."""
    entry = _hybrid("agents-md", "AGENTS.md", "tiers", "model-badge")
    state = _state(managed=(_region_claim("agents-md", "AGENTS.md", "tiers"),))

    statuses = classify_regions(entry, _doc("intro", "outro"), state)

    assert [status.disposition for status in statuses] == [
        RegionDisposition.OPTED_OUT,
        RegionDisposition.MISSING,
    ]


def test_a_region_claim_on_a_different_artifact_does_not_leak():
    """Rung 3 requires BOTH halves -- the id AND the recorded span's name --
    and the id is the half state can actually vary: two artifacts may each
    carry a claim on a region of the same NAME."""
    entry = _hybrid("agents-md", "AGENTS.md", "tiers")
    state = _state(managed=(_region_claim("claude-md", "CLAUDE.md", "tiers"),))

    (status,) = classify_regions(entry, _doc("intro"), state)

    assert status.disposition is RegionDisposition.MISSING


def test_a_whole_file_claim_on_the_same_artifact_never_retires_a_region():
    """A ``managed[]`` entry with no recorded span claims the whole file,
    and says nothing at all about any region of it."""
    entry = _hybrid("agents-md", "AGENTS.md", "tiers")
    whole_file_claim = ManagedArtifact(
        id="agents-md",
        path="AGENTS.md",
        artifact_class="copied-managed",
        body_sha="0123abcd",
        inserted_region_span=None,
    )
    state = _state(managed=(whole_file_claim,))

    (status,) = classify_regions(entry, _doc("intro"), state)

    assert status.disposition is RegionDisposition.MISSING


# --- I/O Matrix row 4: the region is actually there -------------------------


def test_a_region_the_parser_finds_classifies_present_and_emits_no_finding():
    entry = _hybrid("agents-md", "AGENTS.md", "tiers")
    text = _doc("intro", *_rendered_region("tiers"), "outro")

    (status,) = classify_regions(entry, text, _state())

    assert status.disposition is RegionDisposition.PRESENT
    assert region_findings((status,)) == ()


def test_a_present_region_wins_over_a_recorded_opt_out():
    """What is actually in the file is rung 1, ahead of everything state
    believes: a region a maintainer put back is present, not opted out."""
    entry = _hybrid("agents-md", "AGENTS.md", "tiers")
    text = _doc("intro", *_rendered_region("tiers"), "outro")
    state = _state(
        managed=(_region_claim("agents-md", "AGENTS.md", "tiers"),),
        opted_out=("agents-md#tiers",),
    )

    (status,) = classify_regions(entry, text, state)

    assert status.disposition is RegionDisposition.PRESENT


# --- I/O Matrix row 5: an unparseable file degrades to () -------------------


@pytest.mark.parametrize(
    "text",
    [
        pytest.param(
            _doc("intro", render_end(RegionFormat.HTML, "tiers"), "outro"),
            id="end-marker-with-nothing-open",
        ),
        pytest.param(
            _doc("intro", render_begin(RegionFormat.HTML, "tiers", _VERSION, "0123abcd")),
            id="region-never-closed",
        ),
        pytest.param(_doc("intro", "```python", "body"), id="fence-never-closed"),
    ],
)
def test_an_unparseable_file_degrades_to_no_statuses_at_all(text):
    """A structural defect must never RETIRE a region: if "cannot parse"
    read as "the region is gone", rung 3 would convert an unterminated fence
    into a permanent opt-out for every region in the file."""
    entry = _hybrid("agents-md", "AGENTS.md", "tiers")
    state = _state(managed=(_region_claim("agents-md", "AGENTS.md", "tiers"),))

    assert classify_regions(entry, text, state) == ()


def test_a_reserved_format_degrades_rather_than_raising_not_implemented():
    """``RegionFormat.SLASHSTAR`` is a legally-constructible manifest value
    whose parser raises a bare ``NotImplementedError`` -- caught here like
    the other two structural failures, never propagated."""
    entry = ManifestEntry(
        id="some-c-file",
        artifact_class=ArtifactClass.HYBRID_MANAGED_REGION,
        path="src/main.c",
        applies_to=AppliesTo.BOTH,
        rationale="test",
        format=RegionFormat.SLASHSTAR,
        regions=(Region(name="tiers", anchor=("/* anchor */",)),),
    )

    assert classify_regions(entry, _doc("int main(void) {}"), _state()) == ()


# --- an ABSENT, empty, or unreadable artifact is not a pile of opt-outs ----


def test_an_empty_text_never_derives_an_opt_out_from_a_claim():
    """FR-112 sanctions deleting the MARKERS, not the FILE. A deleted,
    empty, or unreadable artifact reaches this module as ``""`` -- the same
    ``""`` ``plan/build.py::_current_text`` hands back for
    ``ArtifactState.ABSENT`` -- and ``parse_regions("")`` then finds
    nothing, so without the guard ``rm AGENTS.md`` would silently retire
    every claimed region of it, permanently."""
    entry = _hybrid("agents-md", "AGENTS.md", "tiers")
    state = _state(managed=(_region_claim("agents-md", "AGENTS.md", "tiers"),))

    (status,) = classify_regions(entry, "", state)

    assert status.disposition is RegionDisposition.MISSING


def test_a_recorded_opt_out_is_still_sticky_with_an_empty_text():
    """Rung 2 is a fact a verb WROTE, not one inferred from a file, so the
    empty-text guard deliberately leaves it alone: staying true through a
    vanished file is exactly what makes a recorded opt-out permanent."""
    entry = _hybrid("agents-md", "AGENTS.md", "tiers")
    state = _state(opted_out=("agents-md#tiers",))

    (status,) = classify_regions(entry, "", state)

    assert status.disposition is RegionDisposition.OPTED_OUT


@pytest.mark.parametrize("text", ["\n", " ", "   \n\t\n"])
def test_a_whitespace_only_text_never_derives_an_opt_out_either(text):
    """The guard asks "is there a FILE here to have deleted markers from",
    and a file a botched script truncated to a newline answers that no just
    as much as a zero-byte one does. ``bool(text)`` split those two apart on
    a single byte: ``""`` re-offered the region, ``"\\n"`` retired it
    PERMANENTLY -- the exact outcome the empty-text guard above exists to
    prevent, reachable by one stray newline. ``bool(text.strip())`` closes
    it. Confirmed real by reverting to ``bool(text)`` and watching this
    fail."""
    entry = _hybrid("agents-md", "AGENTS.md", "tiers")
    state = _state(managed=(_region_claim("agents-md", "AGENTS.md", "tiers"),))

    (status,) = classify_regions(entry, text, state)

    assert status.disposition is RegionDisposition.MISSING


def test_a_pair_the_opt_out_grammar_cannot_spell_is_never_derived_opted_out():
    """Rung 3 read the raw ``managed[].id``, which is the LOOSER grammar --
    ``SeedState`` accepts an id the ``opted_out`` item pattern rejects. So a
    derived ``OPTED_OUT`` could name a pair ``record_opt_out`` REFUSES, and
    the sanctioned verb sequence this module documents broke at its own
    seam: ``opt_outs_to_record`` handed the caller the pair and feeding it
    straight to ``record_opt_out`` raised ``ValueError``. Rung 3 now applies
    the same grammar rung 2 gets for free through ``is_opted_out``."""
    entry = _hybrid("has a space", "AGENTS.md", "tiers")
    state = _state(managed=(_region_claim("has a space", "AGENTS.md", "tiers"),))

    (status,) = classify_regions(entry, _doc("intro"), state)

    assert status.disposition is RegionDisposition.MISSING


def test_every_pair_opt_outs_to_record_returns_is_one_record_opt_out_accepts():
    """The property the rung-3 gate above exists to guarantee, asserted
    directly over both the admissible and the inadmissible id: whatever
    ``opt_outs_to_record`` hands back can be fed to ``record_opt_out``
    without raising. An id the grammar cannot spell simply never appears in
    that tuple."""
    state = _state(
        managed=(
            _region_claim("agents-md", "AGENTS.md", "tiers"),
            _region_claim("has a space", "OTHER.md", "tiers"),
        )
    )
    statuses = classify_regions(
        _hybrid("agents-md", "AGENTS.md", "tiers"), _doc("intro"), state
    ) + classify_regions(_hybrid("has a space", "OTHER.md", "tiers"), _doc("intro"), state)

    pairs = opt_outs_to_record(statuses)

    assert pairs == (("agents-md", "tiers"),)
    for artifact_id, region in pairs:
        record_opt_out(state, artifact_id, region)


def test_an_empty_text_still_reports_one_status_per_declared_region():
    """The guard switches rung 3 off; it does not switch the entry off. A
    missing region is still reported (and still remediable) rather than
    disappearing from the report along with its file."""
    entry = _hybrid("agents-md", "AGENTS.md", "tiers", "model-badge")

    statuses = classify_regions(entry, "", _state())

    assert [status.region for status in statuses] == ["tiers", "model-badge"]
    assert {status.disposition for status in statuses} == {RegionDisposition.MISSING}


# --- I/O Matrix row 6: a non-hybrid entry declares no regions --------------


def test_a_non_hybrid_entry_classifies_nothing():
    assert classify_regions(_whole_file("dream-template", "docs/dreams/x.md"), "", _state()) == ()


# --- ordering, addressing, and message shape -------------------------------


def test_statuses_come_back_in_declared_order_not_parse_order():
    entry = _hybrid("agents-md", "AGENTS.md", "tiers", "model-badge", "portability")
    # The file carries the LAST declared region first.
    text = _doc("intro", *_rendered_region("portability"), "outro")

    statuses = classify_regions(entry, text, _state())

    assert [status.region for status in statuses] == ["tiers", "model-badge", "portability"]
    assert [status.disposition for status in statuses] == [
        RegionDisposition.MISSING,
        RegionDisposition.MISSING,
        RegionDisposition.PRESENT,
    ]


def test_a_mixed_entry_reports_one_finding_per_non_present_region():
    entry = _hybrid("agents-md", "AGENTS.md", "tiers", "model-badge", "portability")
    text = _doc("intro", *_rendered_region("tiers"), "outro")
    state = _state(opted_out=("agents-md#model-badge",))

    findings = region_findings(classify_regions(entry, text, state))

    assert [finding.type for finding in findings] == [
        FindingType.OPTED_OUT,
        FindingType.MANAGED_REGION_MISSING,
    ]
    assert [finding.severity for finding in findings] == [Severity.INFO, Severity.DRIFT]


def test_every_status_carries_both_the_artifact_id_and_the_path():
    entry = _hybrid("agents-md", "AGENTS.md", "tiers")
    (status,) = classify_regions(entry, _doc("intro"), _state())
    assert status.artifact_id == "agents-md"
    assert status.path == "AGENTS.md"


def test_finding_messages_use_the_path_hash_region_convention():
    """``detect/hashes.py::check_managed_region`` already addresses a region
    as ``f"{path}#{span.name}: ..."``; the two region-level finding
    producers must not spell it two ways."""
    entry = _hybrid("agents-md", "AGENTS.md", "tiers", "model-badge")
    state = _state(opted_out=("agents-md#tiers",))

    findings = region_findings(classify_regions(entry, _doc("intro"), state))

    assert findings[0].message.startswith("AGENTS.md#tiers: ")
    assert findings[1].message.startswith("AGENTS.md#model-badge: ")
    assert all(finding.path == "AGENTS.md" for finding in findings)


def test_the_opted_out_message_carries_the_key_its_own_remedy_asks_for():
    """A region has two addresses -- ``AGENTS.md#tiers`` (path) and
    ``agents-md#tiers`` (``opt_out_key``). ``Finding`` carries only ``path``,
    so the report showed one while its remedy told the operator to run
    ``--reinstate <artifact>#<region>`` with the OTHER, and the obvious
    copy-paste was the wrong token. The contract-mandated
    ``f"{path}#{region}: ..."`` prefix is unchanged; the key is spelled in
    the tail, where the remedy can be acted on."""
    entry = _hybrid("agents-md", "AGENTS.md", "tiers")
    state = _state(opted_out=("agents-md#tiers",))

    (opted,) = region_findings(classify_regions(entry, _doc("intro"), state))

    assert opted.message.startswith("AGENTS.md#tiers: ")
    assert "agents-md#tiers" in opted.message
    assert "<artifact>#<region>" in REMEDIES[FindingType.OPTED_OUT]


def test_the_opted_out_message_does_not_promise_a_durability_it_cannot_know():
    """For a DERIVED opt-out (claim present, nothing recorded) durability
    depends on the caller recording ``opt_outs_to_record``'s pairs before
    the plan is built -- and a read-only ``check`` deliberately does not
    (FR-88). An unconditional "the tool will not re-insert this region" was
    the same unprovable claim already removed from the
    ``managed-region-missing`` message."""
    entry = _hybrid("agents-md", "AGENTS.md", "tiers")
    state = _state(managed=(_region_claim("agents-md", "AGENTS.md", "tiers"),))

    (opted,) = region_findings(classify_regions(entry, _doc("intro"), state))

    assert "while this opt-out stands" in opted.message
    assert not opted.message.endswith("the tool will not re-insert this region")


def test_findings_carry_their_types_documented_remedy():
    """Built with ``Finding.new``, so ``remedy`` always resolves from
    ``REMEDIES`` rather than being hand-typed at the call site."""
    entry = _hybrid("agents-md", "AGENTS.md", "tiers", "model-badge")
    state = _state(opted_out=("agents-md#tiers",))

    opted, missing = region_findings(classify_regions(entry, _doc("intro"), state))

    assert opted.remedy == REMEDIES[FindingType.OPTED_OUT]
    assert missing.remedy == REMEDIES[FindingType.MANAGED_REGION_MISSING]
    assert "--reinstate" in opted.remedy


def test_the_missing_finding_message_claims_only_what_is_known():
    """The message used to end "and was never installed" -- a fact this code
    cannot establish. A region whose artifact's single claim slot is held by
    a SIBLING region reaches this exact branch having been installed and
    then deleted (see the one-span-per-artifact limitation above), and the
    message asserted the opposite."""
    entry = _hybrid("agents-md", "AGENTS.md", "tiers", "model-badge")
    state = _state(managed=(_region_claim("agents-md", "AGENTS.md", "tiers"),))

    _opted, missing = region_findings(classify_regions(entry, _doc("intro", "outro"), state))

    assert missing.type is FindingType.MANAGED_REGION_MISSING
    assert missing.message == "AGENTS.md#model-badge: declared managed region is not present"
    assert "never installed" not in missing.message


def test_region_findings_over_an_empty_tuple_is_empty():
    assert region_findings(()) == ()


# --- I/O Matrix row 9: the reinstate round trip -----------------------------


def test_record_then_clear_opt_out_returns_the_region_to_missing():
    """The full FR-112 loop through the real store functions: markers
    deleted -> recorded opt-out -> ``clear_opt_out`` -> planned again."""
    entry = _hybrid("agents-md", "AGENTS.md", "tiers")
    text = _doc("intro", "outro")
    installed = _state(managed=(_region_claim("agents-md", "AGENTS.md", "tiers"),))
    assert classify_regions(entry, text, installed)[0].disposition is RegionDisposition.OPTED_OUT

    recorded = record_opt_out(installed, "agents-md", "tiers")
    assert classify_regions(entry, text, recorded)[0].disposition is RegionDisposition.OPTED_OUT

    reinstated = clear_opt_out(recorded, "agents-md", "tiers")
    assert classify_regions(entry, text, reinstated)[0].disposition is RegionDisposition.MISSING


def test_a_derived_opt_out_is_reinstated_by_clear_opt_out_alone():
    """The ``--reinstate`` path against a DERIVED opt-out -- claim present,
    ``opted_out`` still empty because no mutating verb has run yet. There is
    no recorded key to remove, so a ``clear_opt_out`` that touched only
    ``opted_out`` would be a no-op, rung 3 would fire again on the very next
    run, and the region could never come back. Dropping the claim is what
    makes the withdrawal real."""
    entry = _hybrid("agents-md", "AGENTS.md", "tiers")
    text = _doc("intro", "outro")
    derived = _state(managed=(_region_claim("agents-md", "AGENTS.md", "tiers"),))
    assert derived.opted_out == ()
    assert classify_regions(entry, text, derived)[0].disposition is RegionDisposition.OPTED_OUT

    reinstated = clear_opt_out(derived, "agents-md", "tiers")

    assert classify_regions(entry, text, reinstated)[0].disposition is RegionDisposition.MISSING


# --- opt_outs_to_record: the derivation a mutating verb owes state ---------


def test_opt_outs_to_record_returns_a_pair_for_every_opted_out_status():
    """Every ``OPTED_OUT`` status, derived (rung 3) and recorded (rung 2)
    alike, in the order given. Telling the two apart would be a second
    spelling of rung 2 to save nothing -- ``record_opt_out`` is idempotent,
    so re-recording the already-recorded pair costs an equal
    ``SeedState``."""
    entry = _hybrid("agents-md", "AGENTS.md", "tiers", "model-badge", "portability")
    text = _doc("intro", *_rendered_region("portability"), "outro")
    state = _state(
        managed=(_region_claim("agents-md", "AGENTS.md", "tiers"),),
        opted_out=("agents-md#model-badge",),
    )

    statuses = classify_regions(entry, text, state)

    assert [status.disposition for status in statuses] == [
        RegionDisposition.OPTED_OUT,
        RegionDisposition.OPTED_OUT,
        RegionDisposition.PRESENT,
    ]
    assert opt_outs_to_record(statuses) == (
        ("agents-md", "tiers"),
        ("agents-md", "model-badge"),
    )


def test_opt_outs_to_record_skips_present_and_missing_statuses():
    entry = _hybrid("agents-md", "AGENTS.md", "tiers", "model-badge")
    text = _doc("intro", *_rendered_region("tiers"), "outro")

    assert opt_outs_to_record(classify_regions(entry, text, _state())) == ()


def test_opt_outs_to_record_over_an_empty_tuple_is_empty():
    assert opt_outs_to_record(()) == ()


def test_every_pair_opt_outs_to_record_returns_feeds_record_opt_out_directly():
    """Plain pairs, never rendered ``opt_out_key`` strings: the mutators
    take the two halves separately, so the verb's obligation is a splat.
    This is the sequencing contract the module docstring states -- record
    what detect derived, THEN build a plan -- executed end to end."""
    entry = _hybrid("agents-md", "AGENTS.md", "tiers")
    derived = _state(managed=(_region_claim("agents-md", "AGENTS.md", "tiers"),))

    recorded = derived
    for artifact_id, region in opt_outs_to_record(classify_regions(entry, _doc("intro"), derived)):
        recorded = record_opt_out(recorded, artifact_id, region)

    assert recorded.opted_out == ("agents-md#tiers",)
    assert recorded.managed == ()


# --- vocabulary + dataclass conventions ------------------------------------


def test_region_disposition_is_exactly_three_kebab_case_members():
    assert {member.value for member in RegionDisposition} == {
        "present",
        "opted-out",
        "missing",
    }


def test_the_opted_out_disposition_and_finding_type_share_one_wire_value():
    """The AC speaks one word for this state; the two enums must not spell
    it two ways."""
    assert RegionDisposition.OPTED_OUT.value == FindingType.OPTED_OUT.value


def test_region_status_is_frozen_and_hashable():
    status = RegionStatus("agents-md", "AGENTS.md", "tiers", RegionDisposition.MISSING)
    with pytest.raises(dataclasses.FrozenInstanceError):
        status.region = "other"  # type: ignore[misc]
    assert isinstance(hash(status), int)


def _called_names(tree: ast.AST) -> set[str]:
    """Every function/method name CALLED anywhere in ``tree``, by spelling.

    AST-based rather than a substring grep, matching
    ``test_seed_state_store.py``'s own write-mechanics guard: this module's
    docstring explains at length that it never writes, and saying so must
    not trip the check that proves it."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Attribute):
            names.add(node.func.attr)
        elif isinstance(node.func, ast.Name):
            names.add(node.func.id)
    return names


def test_optout_never_writes_and_never_reads_the_state_file():
    """This module classifies and reports; recording is
    ``state.record_opt_out`` returning a new ``SeedState`` for a verb to
    persist through the existing ``write_state``. It also never reaches the
    filesystem at all -- the caller passes ``text`` in (P-03)."""
    tree = ast.parse(Path(optout_module.__file__).read_text(encoding="utf-8"))
    forbidden = {
        "write",
        "write_state",
        "write_text",
        "write_bytes",
        "read_state",
        "read_text",
        "read_bytes",
        "open",
    }
    assert not _called_names(tree) & forbidden


def _imported_modules(tree: ast.AST, package: str) -> set[str]:
    """Every module name ``tree`` imports, ABSOLUTE -- relative imports
    resolved against ``package`` rather than read off ``ImportFrom.module``.

    ``node.module`` carries the name with the leading dots STRIPPED, and
    this module imports relatively throughout, so a guard that ignores
    ``node.level`` tests a name nothing means: ``from ..state import x``
    presents as ``"state"``, and the very import this test exists to forbid
    -- ``from ...verbs import x`` -- would present as ``"verbs"`` only by
    coincidence of spelling, while ``from ...seed.verbs import x`` would
    present as ``"seed.verbs"`` and sail straight through a
    ``startswith("verbs")`` check. ``resolve_name`` does the arithmetic the
    interpreter itself does."""
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                if node.module is not None:
                    modules.add(node.module)
            else:
                modules.add(
                    importlib.util.resolve_name("." * node.level + (node.module or ""), package)
                )
    return modules


def test_optout_imports_nothing_upward_from_detect():
    """``detect`` sits below ``verbs``/``plan``/``apply`` in the
    architecture's module-dependency chain."""
    tree = ast.parse(Path(optout_module.__file__).read_text(encoding="utf-8"))
    modules = _imported_modules(tree, optout_module.__package__)

    # Proof the resolution actually happened: this module imports
    # ``from ..state import ...``, whose absolute name must be present. A
    # guard that read ``node.module`` alone would see ``"state"`` here, and
    # every assertion below would be about stripped names.
    assert "pyforge.marshal.seed.state" in modules

    upward = (
        "pyforge.marshal.seed.plan",
        "pyforge.marshal.seed.apply",
        "pyforge.marshal.seed.verbs",
    )
    assert not {
        module
        for module in modules
        if any(module == layer or module.startswith(f"{layer}.") for layer in upward)
    }
