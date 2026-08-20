"""Unit tests for ``pyforge.marshal.seed.detect.optout`` (Story 8.5) --
covers every classification and finding row of the spec's I/O & Edge-Case
Matrix, led by the AC's two contrasting tests:

* markers deleted (a ``managed[]`` claim recorded, the region no longer in
  the file) -> ``OPTED_OUT`` + one INFO ``opted-out`` finding;
* never installed (no claim, no recorded opt-out, ``state`` possibly
  ``None``) -> ``MISSING`` + one DRIFT ``managed-region-missing`` finding;

then the already-recorded (sticky) row, the region-present row, the
unparseable-file degrade, the non-hybrid degrade, and the reinstate round
trip through ``record_opt_out``/``clear_opt_out``.

Regions are built by round-tripping through ``render_begin``/``render_end``
rather than by hand-writing marker syntax, mirroring
``test_seed_regions_apply.py``'s own convention: a fixture that does not
actually parse proves nothing about a classifier that reads parsed spans.
"""

from __future__ import annotations

import ast
import dataclasses
from pathlib import Path

import pytest
from pyforge.marshal.seed.detect import optout as optout_module
from pyforge.marshal.seed.detect.findings import REMEDIES, FindingType, Severity
from pyforge.marshal.seed.detect.optout import (
    RegionDisposition,
    RegionStatus,
    classify_regions,
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


def test_a_claim_on_another_region_of_the_same_artifact_does_not_leak():
    """Rung 3 requires BOTH halves -- the id AND the recorded span's name."""
    entry = _hybrid("agents-md", "AGENTS.md", "tiers")
    state = _state(managed=(_region_claim("agents-md", "AGENTS.md", "model-badge"),))

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


def test_findings_carry_their_types_documented_remedy():
    """Built with ``Finding.new``, so ``remedy`` always resolves from
    ``REMEDIES`` rather than being hand-typed at the call site."""
    entry = _hybrid("agents-md", "AGENTS.md", "tiers", "model-badge")
    state = _state(opted_out=("agents-md#tiers",))

    opted, missing = region_findings(classify_regions(entry, _doc("intro"), state))

    assert opted.remedy == REMEDIES[FindingType.OPTED_OUT]
    assert missing.remedy == REMEDIES[FindingType.MANAGED_REGION_MISSING]
    assert "--reinstate" in opted.remedy


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


def test_optout_imports_nothing_upward_from_detect():
    """``detect`` sits below ``verbs``/``plan``/``apply`` in the
    architecture's module-dependency chain."""
    tree = ast.parse(Path(optout_module.__file__).read_text(encoding="utf-8"))
    modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert not {module for module in modules if module.startswith(("plan", "apply", "verbs"))}
