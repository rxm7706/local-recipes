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
* Rung 6 alone is not enough (review pass 1): excusing a deleted region there
  while the plan still built from ``state.opted_out`` alone would turn the old
  accidental refusal into a silent undo of FR-112. The mutating-run tests below
  run ``adopt --apply`` and ``update --run`` over a DERIVED and a RECORDED
  opt-out and read the files and the written state afterwards.

Every test here fails when the fix it names is reverted; the mutation checks
are recorded in the story spec's Auto Run Result.
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
from pyforge.marshal.seed.errors import InternalError, PreconditionFailure
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
    RegionSpanRecord,
    SeedState,
    read_state,
    record_opt_out,
    write_state,
)
from pyforge.marshal.seed.verbs import adopt as adopt_module
from pyforge.marshal.seed.verbs import update as update_module
from pyforge.marshal.seed.verbs.adopt import run_adopt
from pyforge.marshal.seed.verbs.check import run_check
from pyforge.marshal.seed.verbs.preconditions import ManagedRecord, check_preconditions
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


def _dry_run(verb: str, repo: Path, manifest: Manifest):
    """A plain, no-flags run of the verb: ``dry_run`` bypasses only rung 2, so
    rung 6 -- the one under test -- still runs."""
    if verb == "adopt":
        return run_adopt(repo, manifest, confirm=_unreachable_confirm)
    return run_update(repo, manifest, confirm=_unreachable_confirm)


def _mutating_run(verb: str, repo: Path, manifest: Manifest, **overrides):
    """A real, applying run of the verb -- ``--apply --yes`` / ``--run --yes`` --
    with no ``--force`` unless ``overrides`` says so. ``adopt`` writes through the
    fake commit; ``update`` through its real default one."""
    if verb == "adopt":
        return run_adopt(
            repo,
            manifest,
            apply=True,
            yes=True,
            confirm=_unreachable_confirm,
            commit=_fake_commit(manifest, repo),
            **overrides,
        )
    return run_update(repo, manifest, run=True, yes=True, confirm=_unreachable_confirm, **overrides)


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
    assert text.strip() == _HUMAN_TEXT.strip()
    assert "marshal-seed" not in text

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
    write_state(dataclasses.replace(state, managed=(old_shape,)), repo_root=clean_repo, never_write=_NO_NEVER_WRITE)
    _commit_all(clean_repo)

    run_update(clean_repo, manifest, run=True, yes=True, confirm=_unreachable_confirm)

    recovered = read_state(clean_repo)
    assert recovered is not None
    (rewritten,) = recovered.managed
    assert [span.name for span in rewritten.inserted_region_spans] == ["tiers", "model-badge"]


def test_a_later_adopt_that_inserts_one_more_region_keeps_the_regions_already_recorded(clean_repo):
    """A touched id's old record is replaced outright, so the new one must carry
    what the old one attested to as well as what this run wrote -- otherwise
    the first adopt's regions would fall out of state the moment a second one
    ran."""
    first = _manifest(_hybrid("hybrid", "HYBRID.md", "tiers"))
    _adopt_with_human_text(clean_repo, first)
    second = _manifest(_hybrid("hybrid", "HYBRID.md", "tiers", "model-badge"))

    run_adopt(
        clean_repo, second, apply=True, yes=True, confirm=_unreachable_confirm, commit=_fake_commit(second, clean_repo)
    )

    state = read_state(clean_repo)
    assert state is not None
    (claim,) = state.managed
    assert [span.name for span in claim.inserted_region_spans] == ["tiers", "model-badge"]
    text = (clean_repo / "HYBRID.md").read_text(encoding="utf-8")
    parsed = {span.name: span for span in parse_regions(text, RegionFormat.HTML)}
    for recorded in claim.inserted_region_spans:
        assert recorded.body_sha == hash_content(region_body_text(text, parsed[recorded.name]))
    assert claim.body_sha == claim.inserted_region_spans[0].body_sha


def test_an_opted_out_region_is_not_resurrected_by_the_next_adopt_write(clean_repo):
    """A region absent from the file after the apply is left out of the new
    record rather than invented, and an opt-out already recorded keeps
    suppressing its insertion: a later adopt that adds a THIRD region records
    the surviving second and the new one, never the deleted first."""
    first = _manifest(_hybrid("hybrid", "HYBRID.md", "tiers", "model-badge"))
    state = _adopt_with_human_text(clean_repo, first)
    _delete_regions(clean_repo, "tiers")
    write_state(record_opt_out(state, "hybrid", "tiers"), repo_root=clean_repo, never_write=_NO_NEVER_WRITE)
    _commit_all(clean_repo)
    second = _manifest(_hybrid("hybrid", "HYBRID.md", "tiers", "model-badge", "portability-contract"))

    result = run_adopt(
        clean_repo, second, apply=True, yes=True, confirm=_unreachable_confirm, commit=_fake_commit(second, clean_repo)
    )

    assert result.applied == ("hybrid",)
    recovered = read_state(clean_repo)
    assert recovered is not None
    (claim,) = recovered.managed
    assert [span.name for span in claim.inserted_region_spans] == ["model-badge", "portability-contract"]
    assert recovered.opted_out == ("hybrid#tiers",)
    assert "region=tiers" not in (clean_repo / "HYBRID.md").read_text(encoding="utf-8")
    assert claim.body_sha == claim.inserted_region_spans[0].body_sha


def test_a_hybrid_action_with_no_region_to_record_is_an_internal_error_not_a_bare_value_error(clean_repo):
    """Reachable only through a broken `commit` (it returned having written
    nothing the action named): the constructor would raise a bare `ValueError`
    for a hybrid claim with no span, after `run_apply` has already written."""
    from pyforge.marshal.seed.detect.inventory import ArtifactState
    from pyforge.marshal.seed.errors import InternalError
    from pyforge.marshal.seed.verbs import adopt as adopt_module

    manifest = _manifest(_hybrid("hybrid", "HYBRID.md", "tiers"))
    (entry,) = manifest.entries
    (clean_repo / "HYBRID.md").write_text(_HUMAN_TEXT, encoding="utf-8")
    action = Action(
        artifact_id="hybrid",
        artifact_class=ArtifactClass.HYBRID_MANAGED_REGION,
        current_state=ArtifactState.PRESENT_DIVERGENT,
        target_state=ArtifactState.PRESENT_CONFORMANT,
        target_path="HYBRID.md",
        chosen_anchor=(("tiers", None),),
        rationale="test",
    )

    with pytest.raises(InternalError, match="no managed region"):
        adopt_module._managed_artifact_after_apply(action, entry, clean_repo)


@pytest.mark.parametrize("verb", ["adopt", "update"])
def test_the_new_record_carries_what_the_replaced_one_attested_to_beside_what_the_action_names(clean_repo, verb):
    """A touched id's old record is replaced outright. An action that names only
    one region (an adopt's pending one; any update source narrower than the
    wholesale pass) must not drop the regions the prior record attested to --
    and a prior record at a MOVED path describes a different file, so it is not
    carried."""
    from pyforge.marshal.seed.detect.inventory import ArtifactState
    from pyforge.marshal.seed.verbs import adopt as adopt_module
    from pyforge.marshal.seed.verbs import update as update_module

    function = (adopt_module if verb == "adopt" else update_module)._managed_artifact_after_apply
    manifest = _manifest(_hybrid("hybrid", "HYBRID.md", "tiers", "model-badge"))
    (entry,) = manifest.entries
    (prior,) = _adopt_with_human_text(clean_repo, manifest).managed
    action = Action(
        artifact_id="hybrid",
        artifact_class=ArtifactClass.HYBRID_MANAGED_REGION,
        current_state=ArtifactState.PRESENT_DIVERGENT,
        target_state=ArtifactState.PRESENT_CONFORMANT,
        target_path="HYBRID.md",
        chosen_anchor=(("model-badge", None),),
        rationale="test",
    )

    carried = function(action, entry, clean_repo, prior)
    assert [span.name for span in carried.inserted_region_spans] == ["tiers", "model-badge"]
    assert carried.inserted_region_spans == prior.inserted_region_spans
    assert carried.body_sha == carried.inserted_region_spans[0].body_sha

    assert [span.name for span in function(action, entry, clean_repo).inserted_region_spans] == ["model-badge"]
    moved = dataclasses.replace(prior, path="OLD.md")
    assert [span.name for span in function(action, entry, clean_repo, moved).inserted_region_spans] == ["model-badge"]


# --- DW-FU-8-5-5: rung 6 and an opt-out ---------------------------------------


@_VERBS
def test_a_recorded_opt_out_with_its_claim_dropped_is_not_refused_without_force(clean_repo, verb):
    """Pins the OUTCOME, not the rung 6 skip: `record_opt_out` dropped the
    claim, so rung 6 holds no record for the region and has nothing to excuse --
    reverting the skip leaves this test green. The claim-present test below
    pins the skip through the verbs, and
    `test_a_derived_opt_out_is_excused_at_rung_6_while_its_claim_still_stands`
    pins it for a derived pair."""
    manifest = _manifest(_hybrid("hybrid", "HYBRID.md", "tiers", "model-badge"))
    state = _adopt_with_human_text(clean_repo, manifest)
    _delete_regions(clean_repo, "tiers")
    write_state(record_opt_out(state, "hybrid", "tiers"), repo_root=clean_repo, never_write=_NO_NEVER_WRITE)

    _dry_run(verb, clean_repo, manifest)


@_VERBS
def test_a_recorded_opt_out_with_its_claim_still_present_is_not_refused_without_force(clean_repo, verb):
    """Pins the rung 6 skip: the key is recorded AND the claim still stands (the
    verbs record only DERIVED pairs, so they do not drop it), so rung 6 holds a
    record whose region is absent from the file and only the opt-out set excuses
    it."""
    manifest = _manifest(_hybrid("hybrid", "HYBRID.md", "tiers", "model-badge"))
    state = _adopt_with_human_text(clean_repo, manifest)
    _delete_regions(clean_repo, "tiers")
    write_state(
        dataclasses.replace(state, opted_out=("hybrid#tiers",)), repo_root=clean_repo, never_write=_NO_NEVER_WRITE
    )

    _dry_run(verb, clean_repo, manifest)


@_VERBS
def test_a_derived_opt_out_is_not_refused_without_force(clean_repo, verb):
    """The real FR-112 scenario: nothing is recorded, the claim survives and the
    markers are gone. Pins the OUTCOME: the verb records the derived pair in
    memory before it asks rung 6, so rung 6 is handed a state without the claim.
    The skip itself, for a derived pair, is pinned at the seam by
    `test_a_derived_opt_out_is_excused_at_rung_6_while_its_claim_still_stands`."""
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


def test_a_derived_opt_out_is_excused_at_rung_6_while_its_claim_still_stands(clean_repo):
    """The rung 6 skip itself, for a DERIVED opt-out: the claim survives, the
    markers are gone and nothing is recorded. Handed the claim as a record, rung
    6 reports the region missing; handed `opted_out_regions`' answer beside it,
    it does not."""
    manifest = _manifest(_hybrid("hybrid", "HYBRID.md", "tiers", "model-badge"))
    (entry,) = manifest.entries
    state = _adopt_with_human_text(clean_repo, manifest)
    _delete_regions(clean_repo, "tiers")
    text = (clean_repo / "HYBRID.md").read_text(encoding="utf-8")
    (claim,) = state.managed
    record = ManagedRecord(
        artifact_id="hybrid",
        path="HYBRID.md",
        region_shas=tuple((span.name, span.body_sha) for span in claim.inserted_region_spans),
        region_format=RegionFormat.HTML,
    )
    recorded = record_opt_out(state, "hybrid", "tiers")
    plan = build_plan(manifest, classify(manifest, clean_repo), opted_out=frozenset(recorded.opted_out))
    kwargs = {"repo_root": clean_repo, "never_write": _NO_NEVER_WRITE, "managed": (record,), "dry_run": True}

    with pytest.raises(PreconditionFailure, match=r"HYBRID\.md#tiers"):
        check_preconditions(plan, **kwargs)

    pairs = opted_out_regions([(entry, text)], state)
    assert pairs == frozenset({("hybrid", "tiers")})
    assert check_preconditions(plan, opted_out=pairs, **kwargs) is None


# --- a mutating run holds the opt-out through the plan, not only rung 6 --------

_EXTRA = ("extra", "EXTRA.md", "portability-contract")


def _repo_that_deleted_tiers(repo: Path, kind: str) -> tuple[Manifest, SeedState]:
    """A repo whose `HYBRID.md` lost its `tiers` markers after `adopt` installed
    `tiers` and `model-badge`, and the manifest to run against it. The manifest
    adds a second hybrid entry still to install, so `adopt` has something to
    apply (an empty plan writes no state) and `update` has more than one artifact.

    `kind` is how the opt-out stands: `derived` (the claim survives, nothing is
    recorded) or `recorded` (`record_opt_out`'s result: the key is recorded and
    the claim dropped)."""
    base = _manifest(_hybrid("hybrid", "HYBRID.md", "tiers", "model-badge"))
    state = _adopt_with_human_text(repo, base)
    _delete_regions(repo, "tiers")
    if kind == "recorded":
        write_state(record_opt_out(state, "hybrid", "tiers"), repo_root=repo, never_write=_NO_NEVER_WRITE)
        _commit_all(repo)
    return _manifest(*base.entries, _hybrid(*_EXTRA)), state


@_VERBS
@pytest.mark.parametrize("kind", ["derived", "recorded"])
def test_a_mutating_run_keeps_a_deleted_region_deleted_and_records_the_opt_out(clean_repo, verb, kind):
    """The core of review pass 1: `adopt --apply` and `update --run`, no
    `--force`, over an opt-out. Excusing the deletion at rung 6 is not enough --
    the plan must not re-insert the region either, and the state the run writes
    must hold the opt-out (derived ones included) and no span for the region."""
    manifest, before = _repo_that_deleted_tiers(clean_repo, kind)
    (sibling_before,) = [span for span in before.managed[0].inserted_region_spans if span.name == "model-badge"]

    result = _mutating_run(verb, clean_repo, manifest)

    text = (clean_repo / "HYBRID.md").read_text(encoding="utf-8")
    assert "region=tiers" not in text
    assert "region=model-badge" in text
    assert "region=portability-contract" in (clean_repo / "EXTRA.md").read_text(encoding="utf-8")
    recovered = read_state(clean_repo)
    assert recovered is not None
    assert recovered.opted_out == ("hybrid#tiers",)
    claim = next(artifact for artifact in recovered.managed if artifact.id == "hybrid")
    (sibling,) = claim.inserted_region_spans
    assert sibling.name == "model-badge"
    parsed = {span.name: span for span in parse_regions(text, RegionFormat.HTML)}
    assert sibling.body_sha == hash_content(region_body_text(text, parsed["model-badge"]))
    assert claim.body_sha == sibling.body_sha
    if verb == "adopt":
        # `adopt` never rewrites a region that is present, and plans no insertion
        # for the opted-out one: the sibling's hash is the one it was installed with.
        assert sibling.body_sha == sibling_before.body_sha
        (action,) = [action for action in result.plan.actions if action.artifact_id == "hybrid"]
        assert action.chosen_anchor == ()
    else:
        # `update` regenerated the sibling and named only it.
        (action,) = [action for action in result.plan.actions if action.artifact_id == "hybrid"]
        assert [name for name, _anchor in action.chosen_anchor] == ["model-badge"]
        assert "body for model-badge" not in text
    assert [finding.type for finding in run_check(clean_repo, manifest).findings] == [FindingType.OPTED_OUT]


def test_a_dry_run_records_nothing_even_when_it_derives_an_opt_out(clean_repo):
    """The derived pair is recorded in memory only: a dry run, like `check`,
    writes no state."""
    manifest, _before = _repo_that_deleted_tiers(clean_repo, "derived")
    state_file = clean_repo / ".marshal" / "seed-state.yml"
    written = state_file.read_bytes()

    for verb in ("adopt", "update"):
        _dry_run(verb, clean_repo, manifest)
        assert state_file.read_bytes() == written
    run_check(clean_repo, manifest)
    assert state_file.read_bytes() == written


def test_an_empty_plan_writes_no_state_so_a_derived_opt_out_stays_derived(clean_repo):
    """State is written after a non-empty apply, as before: an `adopt --apply`
    that has nothing to apply leaves the file as it was. Every region deleted
    and so every region opted out: the artifact has nothing left to plan."""
    manifest = _manifest(_hybrid("hybrid", "HYBRID.md", "tiers", "model-badge"))
    _adopt_with_human_text(clean_repo, manifest)
    _delete_regions(clean_repo, "tiers", "model-badge")
    state_file = clean_repo / ".marshal" / "seed-state.yml"
    written = state_file.read_bytes()

    result = _mutating_run("adopt", clean_repo, manifest)

    assert result.plan.actions == ()
    assert state_file.read_bytes() == written
    assert "marshal-seed" not in (clean_repo / "HYBRID.md").read_text(encoding="utf-8")


def test_a_hybrid_artifact_with_every_region_opted_out_gets_no_wholesale_action(clean_repo):
    """`update`'s wholesale pass names every declared region that is not opted
    out, so an artifact with every region opted out gets no action -- and its
    record is carried over untouched, for rung 6 and `check` to keep seeing."""
    base = _manifest(_hybrid("hybrid", "HYBRID.md", "tiers", "model-badge"))
    state = _adopt_with_human_text(clean_repo, base)
    _delete_regions(clean_repo, "tiers", "model-badge")
    standing = dataclasses.replace(state, opted_out=("hybrid#model-badge", "hybrid#tiers"))
    write_state(standing, repo_root=clean_repo, never_write=_NO_NEVER_WRITE)
    _commit_all(clean_repo)
    manifest = _manifest(*base.entries, _hybrid(*_EXTRA))
    inventory = classify(manifest, clean_repo)

    # The control: with no opt-out set the pass names both deleted regions.
    (action,), _hashes = update_module._wholesale_regenerate_actions(standing, manifest, inventory)
    assert [name for name, _anchor in action.chosen_anchor] == ["tiers", "model-badge"]
    pairs = frozenset({("hybrid", "tiers"), ("hybrid", "model-badge")})
    assert update_module._wholesale_regenerate_actions(standing, manifest, inventory, pairs) == ((), ())

    dry = run_update(clean_repo, manifest, confirm=_unreachable_confirm)
    assert [action.artifact_id for action in dry.plan.actions] == ["extra"]
    _commit_all(clean_repo)  # the dry run wrote .marshal/plan.json

    run_update(clean_repo, manifest, run=True, yes=True, confirm=_unreachable_confirm)

    recovered = read_state(clean_repo)
    assert recovered is not None
    assert recovered.opted_out == standing.opted_out
    assert next(artifact for artifact in recovered.managed if artifact.id == "hybrid") == state.managed[0]
    text = (clean_repo / "HYBRID.md").read_text(encoding="utf-8")
    assert "marshal-seed" not in text


def test_force_on_update_rewrites_a_hand_edited_sibling_and_leaves_the_opted_out_region_deleted(clean_repo):
    manifest = _manifest(_hybrid("hybrid", "HYBRID.md", "tiers", "model-badge"))
    _adopt_with_human_text(clean_repo, manifest)
    _delete_regions(clean_repo, "tiers")
    _hand_edit_body(clean_repo, "model-badge")

    with pytest.raises(PreconditionFailure, match=r"HYBRID\.md#model-badge"):
        _mutating_run("update", clean_repo, manifest)

    _mutating_run("update", clean_repo, manifest, force=True)

    text = (clean_repo / "HYBRID.md").read_text(encoding="utf-8")
    assert "hand edited, markers intact" not in text
    assert "region=model-badge" in text
    assert "region=tiers" not in text
    recovered = read_state(clean_repo)
    assert recovered is not None
    assert recovered.opted_out == ("hybrid#tiers",)
    (claim,) = recovered.managed
    (sibling,) = claim.inserted_region_spans
    parsed = {span.name: span for span in parse_regions(text, RegionFormat.HTML)}
    assert sibling.name == "model-badge"
    assert sibling.body_sha == hash_content(region_body_text(text, parsed["model-badge"]))


def test_force_on_adopt_records_a_hand_edited_sibling_as_the_new_baseline_and_keeps_the_opt_out(clean_repo):
    """`adopt` never rewrites a region that is present, so under `--force` the
    hand-edited sibling stays as the operator left it -- and, being carried into
    the rebuilt record at its CURRENT hash, becomes the baseline later runs
    compare against. The opted-out region stays deleted and the pending third
    region is inserted."""
    first = _manifest(_hybrid("hybrid", "HYBRID.md", "tiers", "model-badge"))
    _adopt_with_human_text(clean_repo, first)
    _delete_regions(clean_repo, "tiers")
    _hand_edit_body(clean_repo, "model-badge")
    second = _manifest(_hybrid("hybrid", "HYBRID.md", "tiers", "model-badge", "portability-contract"))

    with pytest.raises(PreconditionFailure, match=r"HYBRID\.md#model-badge"):
        _mutating_run("adopt", clean_repo, second)

    _mutating_run("adopt", clean_repo, second, force=True)

    text = (clean_repo / "HYBRID.md").read_text(encoding="utf-8")
    assert "hand edited, markers intact" in text
    assert "region=tiers" not in text
    assert "region=portability-contract" in text
    recovered = read_state(clean_repo)
    assert recovered is not None
    assert recovered.opted_out == ("hybrid#tiers",)
    (claim,) = recovered.managed
    assert [span.name for span in claim.inserted_region_spans] == ["model-badge", "portability-contract"]
    parsed = {span.name: span for span in parse_regions(text, RegionFormat.HTML)}
    for span in claim.inserted_region_spans:
        assert span.body_sha == hash_content(region_body_text(text, parsed[span.name]))
    # The edit is the baseline now: a plain run no longer refuses it.
    _dry_run("update", clean_repo, second)


@_VERBS
def test_an_escaping_hybrid_entry_is_never_read_for_opt_outs(clean_repo, monkeypatch, verb):
    """Story 82.11: an entry whose path resolves outside the repo is reported and
    planned for nothing, and its target is never read. The opt-out pass reads
    every hybrid entry's file, so it must skip an escaping one."""
    module = adopt_module if verb == "adopt" else update_module
    manifest = _manifest(_hybrid("escaper", "ESCAPER.md", "tiers"), _hybrid("good", "GOOD.md", "tiers"))
    for name in ("ESCAPER.md", "GOOD.md"):
        (clean_repo / name).write_text(_HUMAN_TEXT, encoding="utf-8")
    _commit_all(clean_repo)
    run_adopt(
        clean_repo,
        manifest,
        apply=True,
        yes=True,
        confirm=_unreachable_confirm,
        commit=_fake_commit(manifest, clean_repo),
    )
    _commit_all(clean_repo)
    # ESCAPER.md later becomes a symlink to a file outside the repository.
    outside = clean_repo.parent / f"{clean_repo.name}-outside"
    outside.mkdir()
    escaper = clean_repo / "ESCAPER.md"
    (outside / "target.md").write_text(escaper.read_text(encoding="utf-8"), encoding="utf-8")
    escaper.unlink()
    escaper.symlink_to(outside / "target.md")
    _commit_all(clean_repo)
    read_targets: list[Path] = []
    real_read = module._read_text_or_blank

    def spy(target: Path) -> str:
        read_targets.append(target)
        return real_read(target)

    monkeypatch.setattr(module, "_read_text_or_blank", spy)

    result = _dry_run(verb, clean_repo, manifest)

    assert [finding.path for finding in result.escape_findings] == ["ESCAPER.md"]
    assert escaper not in read_targets
    assert clean_repo / "GOOD.md" in read_targets


@pytest.mark.parametrize("verb", ["adopt", "update"])
def test_the_no_region_to_record_error_names_only_the_regions_the_action_named(clean_repo, verb):
    """The message says what the ACTION named, in a stable order -- not the
    regions a replaced record carried over, which the action never asked for."""
    from pyforge.marshal.seed.detect.inventory import ArtifactState

    function = (adopt_module if verb == "adopt" else update_module)._managed_artifact_after_apply
    manifest = _manifest(_hybrid("hybrid", "HYBRID.md", "tiers", "model-badge"))
    (entry,) = manifest.entries
    (clean_repo / "HYBRID.md").write_text(_HUMAN_TEXT, encoding="utf-8")
    action = Action(
        artifact_id="hybrid",
        artifact_class=ArtifactClass.HYBRID_MANAGED_REGION,
        current_state=ArtifactState.PRESENT_DIVERGENT,
        target_state=ArtifactState.PRESENT_CONFORMANT,
        target_path="HYBRID.md",
        chosen_anchor=(("tiers", None),),
        rationale="test",
    )
    prior = ManagedArtifact(
        id="hybrid",
        path="HYBRID.md",
        artifact_class="hybrid-managed-region",
        body_sha="0123abcd",
        inserted_region_spans=(RegionSpanRecord(name="model-badge", start=0, end=4, body_sha="0123abcd"),),
    )

    with pytest.raises(InternalError) as excinfo:
        function(action, entry, clean_repo, prior)

    assert "['tiers']" in excinfo.value.message
    assert "model-badge" not in excinfo.value.message


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
    deletion of markers, so nothing is derived from the surviving claim."""
    hybrid = _hybrid("hybrid", "HYBRID.md", "tiers")
    state = SeedState(
        model_version=_VERSION,
        seed_model_version="0.1.0",
        adopted_at="2026-10-02T00:00:00Z",
        last_update="2026-10-02T00:00:00Z",
        mode="adopt",
        agents=(),
        managed=(
            ManagedArtifact(
                id="hybrid",
                path="HYBRID.md",
                artifact_class="hybrid-managed-region",
                body_sha="0123abcd",
                inserted_region_spans=(RegionSpanRecord(name="tiers", start=0, end=4, body_sha="0123abcd"),),
            ),
        ),
        skips=(),
        legacy=(),
        migrations_applied=(),
        opted_out=(),
    )

    assert opted_out_regions([(hybrid, "")], state) == frozenset()
    assert opted_out_regions([(hybrid, "\n")], state) == frozenset()
    assert opted_out_regions([(hybrid, _HUMAN_TEXT)], state) == frozenset({("hybrid", "tiers")})
