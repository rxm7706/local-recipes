"""Story 82.13 end to end, through the real verbs: a marker opt-out is
representable for every artifact, accepted by rung 6, and recorded per region.

``adopt`` installs a hybrid artifact's regions (the real ``insert_region``
through a fake ``commit``), the test deletes some markers the way a
maintainer would, and the verbs are asked what they make of it:

* DW-FU-8-5-5 -- rung 6 refuses a DELETED region as a hand-edit and offers
  ``--force``, while ``build_plan`` already honours the same opt-out. Rung 6
  now excuses a region whose ``(artifact_id, region)`` is opted out, recorded
  or derived, in ``adopt`` and ``update`` alike -- and still refuses a region
  that is merely modified.
* DW-FU-8-5-6 -- state recorded ONE span per artifact, so an opt-out covered
  one region of a multi-region artifact and its siblings were re-inserted.
  State now holds a span (with its own hash) per installed region.

Every test here fails when the fix it names is reverted; the mutation checks
are recorded in the story spec's Review Triage Log.
"""

from __future__ import annotations

import dataclasses
import re
import subprocess
from pathlib import Path

import pytest

from pyforge.marshal.seed.detect.findings import FindingType
from pyforge.marshal.seed.detect.hashes import hash_content, region_body_text
from pyforge.marshal.seed.detect.inventory import classify
from pyforge.marshal.seed.detect.optout import (
    RegionDisposition,
    classify_regions,
    opt_outs_to_record,
    opted_out_regions,
)
from pyforge.marshal.seed.errors import PreconditionFailure
from pyforge.marshal.seed.fs import NeverWrite
from pyforge.marshal.seed.model.manifest import (
    AppliesTo,
    ArtifactClass,
    Manifest,
    ManifestEntry,
    Region,
)
from pyforge.marshal.seed.model.version import ModelVersion
from pyforge.marshal.seed.plan.build import build_plan
from pyforge.marshal.seed.plan.types import Action
from pyforge.marshal.seed.regions.apply import insert_region
from pyforge.marshal.seed.regions.markers import RegionFormat
from pyforge.marshal.seed.regions.parse import parse_regions
from pyforge.marshal.seed.state import (
    ManagedArtifact,
    SeedState,
    read_state,
    record_opt_out,
    write_state,
)
from pyforge.marshal.seed.verbs.adopt import run_adopt
from pyforge.marshal.seed.verbs.check import run_check
from pyforge.marshal.seed.verbs.update import run_update

_VERSION = ModelVersion.parse("1.0.0")
_NO_NEVER_WRITE = NeverWrite(patterns=())
_HUMAN_TEXT = "# Project\n\nWritten by a human, never by marshal.\n"


# --- fixtures and doubles ----------------------------------------------------


def _git(repo: Path, *args: str) -> None:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def _commit_all(repo: Path) -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "fixture")


@pytest.fixture
def clean_repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-b", "main")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "README.md").write_text("hello\n", encoding="utf-8")
    _git(tmp_path, "add", "README.md")
    _git(tmp_path, "commit", "-m", "initial")
    return tmp_path


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


def _manifest(*entries: ManifestEntry) -> Manifest:
    return Manifest(model_version=_VERSION, never_write=(), entries=tuple(entries))


def _unreachable_confirm() -> bool:
    raise AssertionError("confirm() should not have been called")


def _fake_commit(manifest: Manifest, repo_root: Path):
    """Inserts each region the action names through the REAL
    ``insert_region``, with a body that names the region."""
    entries_by_id = {entry.id: entry for entry in manifest.entries}

    def commit(action: Action) -> None:
        entry = entries_by_id[action.artifact_id]
        assert entry.format is not None
        target = repo_root / action.target_path
        for region_name, _matched_anchor in action.chosen_anchor:
            region = next(candidate for candidate in entry.regions if candidate.name == region_name)
            text = target.read_text(encoding="utf-8") if target.is_file() else None
            insert_region(
                text,
                target,
                region_name,
                region.anchor,
                f"body for {region_name}\n",
                model_version=manifest.model_version,
                fmt=entry.format,
                repo_root=repo_root,
                never_write=_NO_NEVER_WRITE,
            )

    return commit


def _adopt_with_human_text(repo: Path, manifest: Manifest, *, path: str = "HYBRID.md") -> SeedState:
    """The realistic shape: a file a human already wrote, which ``adopt`` then
    inserts its regions into -- never a file made of nothing but markers."""
    (repo / path).write_text(_HUMAN_TEXT, encoding="utf-8")
    _commit_all(repo)
    run_adopt(repo, manifest, apply=True, yes=True, confirm=_unreachable_confirm, commit=_fake_commit(manifest, repo))
    _commit_all(repo)
    state = read_state(repo)
    assert state is not None
    return state


def _delete_regions(repo: Path, *regions: str, path: str = "HYBRID.md") -> None:
    """Delete the named regions -- markers and body -- the way a maintainer
    opts out, leaving every other line alone."""
    kept: list[str] = []
    inside: str | None = None
    for line in (repo / path).read_text(encoding="utf-8").splitlines(keepends=True):
        if inside is None:
            begin = re.search(r"marshal-seed:begin region=(\S+)", line)
            if begin and begin.group(1) in regions:
                inside = begin.group(1)
                continue
            kept.append(line)
        elif f"marshal-seed:end region={inside}" in line:
            inside = None
    (repo / path).write_text("".join(kept), encoding="utf-8")
    _commit_all(repo)


def _hand_edit_body(repo: Path, region: str, *, path: str = "HYBRID.md") -> None:
    target = repo / path
    text = target.read_text(encoding="utf-8")
    assert f"body for {region}\n" in text
    target.write_text(text.replace(f"body for {region}\n", "hand edited, markers intact\n"), encoding="utf-8")
    _commit_all(repo)


def _dry_run(verb: str, repo: Path, manifest: Manifest) -> None:
    """A plain, no-flags run of the verb: ``dry_run`` bypasses only rung 2, so
    rung 6 -- the one under test -- still runs."""
    if verb == "adopt":
        run_adopt(repo, manifest, confirm=_unreachable_confirm)
    else:
        run_update(repo, manifest, confirm=_unreachable_confirm)


_VERBS = pytest.mark.parametrize("verb", ["adopt", "update"])


# --- DW-FU-8-5-6: one span per installed region -------------------------------


def test_a_fresh_adopt_records_one_entry_with_a_span_and_a_hash_per_region(clean_repo):
    manifest = _manifest(_hybrid("hybrid", "HYBRID.md", "tiers", "model-badge", "portability-contract"))

    state = _adopt_with_human_text(clean_repo, manifest)

    (claim,) = state.managed
    assert [span.name for span in claim.inserted_region_spans] == ["tiers", "model-badge", "portability-contract"]
    text = (clean_repo / "HYBRID.md").read_text(encoding="utf-8")
    parsed = {span.name: span for span in parse_regions(text, RegionFormat.HTML)}
    for recorded in claim.inserted_region_spans:
        assert (recorded.start, recorded.end) == parsed[recorded.name].body_span
        assert recorded.body_sha == hash_content(region_body_text(text, parsed[recorded.name]))
    # Three different bodies, three different hashes -- a hash PER region,
    # not the first one repeated -- and the artifact's own is the first's.
    assert len({recorded.body_sha for recorded in claim.inserted_region_spans}) == 3
    assert claim.body_sha == claim.inserted_region_spans[0].body_sha


def test_a_later_update_and_check_find_no_divergence_in_a_fully_recorded_artifact(clean_repo):
    manifest = _manifest(_hybrid("hybrid", "HYBRID.md", "tiers", "model-badge", "portability-contract"))
    _adopt_with_human_text(clean_repo, manifest)

    # No `--force` and no refusal: rung 6 finds every region recorded.
    result = run_update(clean_repo, manifest, confirm=_unreachable_confirm)
    assert [action.artifact_id for action in result.plan.actions] == ["hybrid"]

    report = run_check(clean_repo, manifest)
    assert [finding.type for finding in report.findings] == []


def test_a_modified_sibling_is_caught_against_its_own_recorded_hash(clean_repo):
    """The point of a hash per region: with one artifact-level hash the second
    and third regions had nothing to compare against."""
    manifest = _manifest(_hybrid("hybrid", "HYBRID.md", "tiers", "model-badge"))
    _adopt_with_human_text(clean_repo, manifest)
    _hand_edit_body(clean_repo, "model-badge")

    with pytest.raises(PreconditionFailure, match=r"HYBRID\.md#model-badge"):
        run_update(clean_repo, manifest, confirm=_unreachable_confirm)

    report = run_check(clean_repo, manifest)
    assert [finding.type for finding in report.findings] == [FindingType.MANAGED_REGION_MODIFIED]
    assert "HYBRID.md#model-badge" in report.findings[0].message


def test_both_deleted_regions_are_opted_out_recorded_and_neither_is_planned_again(clean_repo):
    """DW-FU-8-5-6 end to end: both regions installed by `adopt`, both
    deleted, detection runs, the derived pairs are recorded, the state is
    written and read back -- then both are opted out and `build_plan` plans no
    insertion for either. Before 82.13 the second fell to `MISSING`."""
    manifest = _manifest(_hybrid("hybrid", "HYBRID.md", "tiers", "model-badge"))
    (entry,) = manifest.entries
    state = _adopt_with_human_text(clean_repo, manifest)
    _delete_regions(clean_repo, "tiers", "model-badge")
    text = (clean_repo / "HYBRID.md").read_text(encoding="utf-8")
    assert text == _HUMAN_TEXT

    statuses = classify_regions(entry, text, state)
    assert [status.disposition for status in statuses] == [RegionDisposition.OPTED_OUT] * 2

    pairs = opt_outs_to_record(statuses, state)
    assert pairs == (("hybrid", "tiers"), ("hybrid", "model-badge"))
    for artifact_id, region in pairs:
        state = record_opt_out(state, artifact_id, region)
    write_state(state, repo_root=clean_repo, never_write=_NO_NEVER_WRITE)
    recovered = read_state(clean_repo)

    assert recovered == state
    assert recovered is not None
    assert recovered.opted_out == ("hybrid#model-badge", "hybrid#tiers")
    assert recovered.managed == ()
    assert [status.disposition for status in classify_regions(entry, text, recovered)] == [
        RegionDisposition.OPTED_OUT
    ] * 2
    plan = build_plan(manifest, classify(manifest, clean_repo), opted_out=frozenset(recovered.opted_out))
    assert plan.actions == ()


def test_opting_out_of_one_deleted_region_leaves_the_siblings_claim_and_check_still_guards_it(clean_repo):
    manifest = _manifest(_hybrid("hybrid", "HYBRID.md", "tiers", "model-badge"))
    (entry,) = manifest.entries
    state = _adopt_with_human_text(clean_repo, manifest)
    _delete_regions(clean_repo, "tiers")
    text = (clean_repo / "HYBRID.md").read_text(encoding="utf-8")

    statuses = classify_regions(entry, text, state)
    assert [(status.region, status.disposition) for status in statuses] == [
        ("tiers", RegionDisposition.OPTED_OUT),
        ("model-badge", RegionDisposition.PRESENT),
    ]
    recorded = record_opt_out(state, "hybrid", "tiers")
    (claim,) = recorded.managed
    assert [span.name for span in claim.inserted_region_spans] == ["model-badge"]

    # The surviving claim still guards its region.
    write_state(recorded, repo_root=clean_repo, never_write=_NO_NEVER_WRITE)
    _commit_all(clean_repo)
    _hand_edit_body(clean_repo, "model-badge")
    with pytest.raises(PreconditionFailure, match=r"HYBRID\.md#model-badge"):
        run_update(clean_repo, manifest, confirm=_unreachable_confirm)


def test_a_state_in_the_old_one_span_shape_is_rewritten_in_full_by_the_next_update(clean_repo):
    """Reading never rejects an old file, and the next apply re-records every
    region (update's wholesale pass names them all) in the new shape."""
    manifest = _manifest(_hybrid("hybrid", "HYBRID.md", "tiers", "model-badge"))
    state = _adopt_with_human_text(clean_repo, manifest)
    (claim,) = state.managed
    # The pre-82.13 shape: one span, the artifact's hash standing for it.
    old_shape = dataclasses.replace(claim, inserted_region_spans=claim.inserted_region_spans[:1])
    write_state(
        dataclasses.replace(state, managed=(old_shape,)), repo_root=clean_repo, never_write=_NO_NEVER_WRITE
    )
    _commit_all(clean_repo)

    run_update(clean_repo, manifest, run=True, yes=True, confirm=_unreachable_confirm)

    recovered = read_state(clean_repo)
    assert recovered is not None
    (rewritten,) = recovered.managed
    assert [span.name for span in rewritten.inserted_region_spans] == ["tiers", "model-badge"]


# --- DW-FU-8-5-5: rung 6 and an opt-out ---------------------------------------


@_VERBS
def test_a_recorded_opt_out_with_its_claim_dropped_is_not_refused_without_force(clean_repo, verb):
    manifest = _manifest(_hybrid("hybrid", "HYBRID.md", "tiers", "model-badge"))
    state = _adopt_with_human_text(clean_repo, manifest)
    _delete_regions(clean_repo, "tiers")
    write_state(
        record_opt_out(state, "hybrid", "tiers"), repo_root=clean_repo, never_write=_NO_NEVER_WRITE
    )

    _dry_run(verb, clean_repo, manifest)


@_VERBS
def test_a_recorded_opt_out_with_its_claim_still_present_is_not_refused_without_force(clean_repo, verb):
    manifest = _manifest(_hybrid("hybrid", "HYBRID.md", "tiers", "model-badge"))
    state = _adopt_with_human_text(clean_repo, manifest)
    _delete_regions(clean_repo, "tiers")
    write_state(
        dataclasses.replace(state, opted_out=("hybrid#tiers",)), repo_root=clean_repo, never_write=_NO_NEVER_WRITE
    )

    _dry_run(verb, clean_repo, manifest)


@_VERBS
def test_a_derived_opt_out_is_not_refused_without_force(clean_repo, verb):
    """The real FR-112 scenario: nothing is recorded, the claim survives and
    the markers are gone. No mutating verb records a derived opt-out yet, so a
    rung 6 reading `state.opted_out` alone would still refuse it."""
    manifest = _manifest(_hybrid("hybrid", "HYBRID.md", "tiers", "model-badge"))
    state = _adopt_with_human_text(clean_repo, manifest)
    assert state.opted_out == ()
    _delete_regions(clean_repo, "tiers")

    _dry_run(verb, clean_repo, manifest)


@_VERBS
def test_every_deleted_region_of_a_multi_region_artifact_is_excused(clean_repo, verb):
    manifest = _manifest(_hybrid("hybrid", "HYBRID.md", "tiers", "model-badge", "portability-contract"))
    _adopt_with_human_text(clean_repo, manifest)
    _delete_regions(clean_repo, "tiers", "portability-contract")

    _dry_run(verb, clean_repo, manifest)


@_VERBS
def test_a_deleted_region_beside_a_hand_edited_one_still_refuses_for_the_edited_one(clean_repo, verb):
    manifest = _manifest(_hybrid("hybrid", "HYBRID.md", "tiers", "model-badge"))
    _adopt_with_human_text(clean_repo, manifest)
    _delete_regions(clean_repo, "tiers")
    _hand_edit_body(clean_repo, "model-badge")

    with pytest.raises(PreconditionFailure, match="managed-content-modified") as excinfo:
        _dry_run(verb, clean_repo, manifest)

    assert "HYBRID.md#model-badge" in excinfo.value.message
    assert "HYBRID.md#tiers" not in excinfo.value.message


@_VERBS
def test_a_file_emptied_to_nothing_is_not_an_opt_out_and_rung_6_does_not_excuse_it(clean_repo, verb):
    """The derivation's own guards hold at rung 6: a file truncated to a
    newline is not a maintainer deleting markers (rung 3 needs real content),
    so a recorded region missing from it is still reported."""
    manifest = _manifest(_hybrid("hybrid", "HYBRID.md", "tiers", "model-badge"))
    _adopt_with_human_text(clean_repo, manifest)
    (clean_repo / "HYBRID.md").write_text("\n", encoding="utf-8")
    _commit_all(clean_repo)

    with pytest.raises(PreconditionFailure, match="managed-content-modified"):
        _dry_run(verb, clean_repo, manifest)


@_VERBS
def test_force_still_discards_a_hand_edit_beside_an_opt_out(clean_repo, verb):
    manifest = _manifest(_hybrid("hybrid", "HYBRID.md", "tiers", "model-badge"))
    _adopt_with_human_text(clean_repo, manifest)
    _delete_regions(clean_repo, "tiers")
    _hand_edit_body(clean_repo, "model-badge")

    if verb == "adopt":
        run_adopt(clean_repo, manifest, force=True, confirm=_unreachable_confirm)
    else:
        run_update(clean_repo, manifest, force=True, confirm=_unreachable_confirm)


# --- opted_out_regions: the pure set rung 6 is handed -------------------------


def test_opted_out_regions_returns_recorded_and_derived_pairs_alike(clean_repo):
    manifest = _manifest(_hybrid("hybrid", "HYBRID.md", "tiers", "model-badge"))
    (entry,) = manifest.entries
    state = _adopt_with_human_text(clean_repo, manifest)
    _delete_regions(clean_repo, "tiers", "model-badge")
    text = (clean_repo / "HYBRID.md").read_text(encoding="utf-8")

    derived = opted_out_regions([(entry, text)], state)
    recorded = opted_out_regions(
        [(entry, text)], record_opt_out(record_opt_out(state, "hybrid", "tiers"), "hybrid", "model-badge")
    )

    assert derived == recorded == frozenset({("hybrid", "tiers"), ("hybrid", "model-badge")})


def test_opted_out_regions_is_empty_for_present_missing_and_non_hybrid_input():
    hybrid = _hybrid("hybrid", "HYBRID.md", "tiers")
    whole = ManifestEntry(
        id="whole",
        artifact_class=ArtifactClass.COPIED_MANAGED,
        path="WHOLE.md",
        applies_to=AppliesTo.BOTH,
        rationale="test",
    )

    assert opted_out_regions([], None) == frozenset()
    assert opted_out_regions([(hybrid, _HUMAN_TEXT)], None) == frozenset()
    assert opted_out_regions([(whole, "anything")], None) == frozenset()


def test_opted_out_regions_does_not_derive_from_a_claim_when_the_file_has_no_content():
    """`classify_regions`' own guard: an absent or emptied file is not a
    deletion of markers, so nothing is derived."""
    hybrid = _hybrid("hybrid", "HYBRID.md", "tiers")
    claim = ManagedArtifact(
        id="hybrid",
        path="HYBRID.md",
        artifact_class="hybrid-managed-region",
        body_sha="0123abcd",
        inserted_region_spans=(),
    ) if False else None
    assert claim is None
    assert opted_out_regions([(hybrid, "")], None) == frozenset()
