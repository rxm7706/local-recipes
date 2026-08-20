"""Unit tests for ``pyforge.marshal.seed.plan.build`` (Story 9.6) -- covers
the spec's I/O & Edge-Case Matrix for ``build_plan``/``write_plan``/
``load_plan``/``default_plan_path``: every classification -> ``Action``
mapping rule, chosen-anchor resolution (absent-hybrid, present-divergent
partial, unparseable-degrades-to-empty), the empty-plan case, the
non-git-target repo fingerprint fallback, two-runs determinism, the
write/load round trip, and a real-packaged-manifest regression test
(mirrors S-9.5's own real-manifest regression-test convention against
``templates/manifest.yaml``).

Story 10.3 appends the ``fingerprint_drift`` section at the end of this
file: the verifier lives beside the fingerprint's sole producer (P-07 --
see its own docstring), so its tests live beside the producer's tests too,
driven against a real ``tmp_path`` git repo through the same ``_git``/
``_init_git_repo`` helpers.

Story 8.5 appends the ``opted_out`` section: zero-pending suppression (for
``ABSENT`` and ``PRESENT_DIVERGENT`` alike, with no ``artifact_hashes``
entry either), the partial opt-out that still plans its one remaining
region, an unparseable file that is never "zero pending", and the
default-argument proof that every pre-story case is byte-identical.
"""

from __future__ import annotations

import dataclasses
import json
import subprocess
from importlib import resources
from pathlib import Path

import pytest
from pyforge.marshal.seed.detect.hashes import hash_content
from pyforge.marshal.seed.detect.inventory import ArtifactState, classify
from pyforge.marshal.seed.model.manifest import (
    AppliesTo,
    ArtifactClass,
    Manifest,
    ManifestEntry,
    Region,
    load_manifest,
)
from pyforge.marshal.seed.model.version import ModelVersion
from pyforge.marshal.seed.plan.build import (
    build_plan,
    default_plan_path,
    fingerprint_drift,
    load_plan,
    write_plan,
)
from pyforge.marshal.seed.plan.types import Plan
from pyforge.marshal.seed.regions.markers import (
    RegionFormat,
    region_sha,
    render_begin,
    render_end,
)
from pyforge.marshal.seed.state import SeedState, clear_opt_out, opt_out_key

_VERSION = ModelVersion.parse("1.0.0")


def _manifest(*entries: ManifestEntry, never_write: tuple[str, ...] = ()) -> Manifest:
    return Manifest(model_version=_VERSION, never_write=never_write, entries=tuple(entries))


def _referenced(entry_id: str, path: str = "unused") -> ManifestEntry:
    return ManifestEntry(
        id=entry_id,
        artifact_class=ArtifactClass.REFERENCED,
        path=path,
        applies_to=AppliesTo.BOTH,
        rationale="test",
        pin=">=1.0",
    )


def _whole_file(
    entry_id: str, path: str, artifact_class: ArtifactClass, *, legacy_of: str | None = None
) -> ManifestEntry:
    return ManifestEntry(
        id=entry_id,
        artifact_class=artifact_class,
        path=path,
        applies_to=AppliesTo.BOTH,
        rationale="test",
        legacy_of=legacy_of,
    )


def _hybrid(
    entry_id: str,
    path: str,
    *region_names: str,
    fmt: RegionFormat = RegionFormat.HTML,
    anchors: dict[str, tuple[str, ...]] | None = None,
) -> ManifestEntry:
    anchors = anchors or {}
    return ManifestEntry(
        id=entry_id,
        artifact_class=ArtifactClass.HYBRID_MANAGED_REGION,
        path=path,
        applies_to=AppliesTo.BOTH,
        rationale="test",
        format=fmt,
        regions=tuple(
            Region(name=name, anchor=anchors.get(name, ("# anchor",))) for name in region_names
        ),
    )


def _doc(*lines: str) -> str:
    return "".join(f"{line}\n" for line in lines)


def _hybrid_text(name: str, fmt: RegionFormat = RegionFormat.HTML) -> str:
    body = "line1\n"
    sha = region_sha(body)
    return _doc(
        "intro", render_begin(fmt, name, _VERSION, sha), "line1", render_end(fmt, name), "outro"
    )


def _sample_plan(tmp_path) -> Plan:
    manifest = _manifest(_whole_file("a", "missing.txt", ArtifactClass.COPIED_MANAGED))
    inventory = classify(manifest, tmp_path)
    return build_plan(manifest, inventory)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Mirrors ``test_vcs_git.py``'s own real-git-repo test convention:
    real ``git`` I/O against a ``tmp_path``, never mocked."""
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    return result


def _init_git_repo(repo: Path) -> None:
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "initial")


# --- classification -> Action mapping rules --------------------------------


def test_absent_whole_file_entry_produces_one_action_naming_materialization(tmp_path):
    manifest = _manifest(_whole_file("a", "seeded.txt", ArtifactClass.COPIED_SEEDED))
    inventory = classify(manifest, tmp_path)
    plan = build_plan(manifest, inventory)

    (action,) = plan.actions
    assert action.artifact_id == "a"
    assert action.artifact_class == ArtifactClass.COPIED_SEEDED
    assert action.current_state == ArtifactState.ABSENT
    assert action.target_state == ArtifactState.PRESENT_CONFORMANT
    assert action.target_path == "seeded.txt"
    assert action.chosen_anchor == ()
    assert "materialize" in action.rationale


def test_absent_hybrid_entry_with_two_declared_regions_gets_one_pair_per_region(tmp_path):
    manifest = _manifest(
        _hybrid(
            "h",
            "CLAUDE.md",
            "tiers",
            "model-badge",
            anchors={"tiers": ("### Spec-driven",), "model-badge": ("<top>",)},
        )
    )
    inventory = classify(manifest, tmp_path)
    plan = build_plan(manifest, inventory)

    (action,) = plan.actions
    assert action.current_state == ArtifactState.ABSENT
    # Resolved against "" (nothing on disk): "tiers"'s anchor text matches
    # no line in empty text -> EOF fallback (matched=None); "<top>" always
    # resolves regardless of content.
    assert action.chosen_anchor == (("tiers", None), ("model-badge", "<top>"))


def test_present_divergent_hybrid_with_one_of_two_regions_missing_gets_exactly_one_pair(
    tmp_path,
):
    (tmp_path / "CLAUDE.md").write_text(_hybrid_text("tiers"))
    manifest = _manifest(
        _hybrid("h", "CLAUDE.md", "tiers", "model-badge", anchors={"model-badge": ("<top>",)})
    )
    inventory = classify(manifest, tmp_path)
    plan = build_plan(manifest, inventory)

    (action,) = plan.actions
    assert action.current_state == ArtifactState.PRESENT_DIVERGENT
    assert action.chosen_anchor == (("model-badge", "<top>"),)


def test_present_conformant_entry_produces_no_action(tmp_path):
    (tmp_path / "seeded.txt").write_text("hello\n")
    manifest = _manifest(_whole_file("a", "seeded.txt", ArtifactClass.COPIED_SEEDED))
    inventory = classify(manifest, tmp_path)
    plan = build_plan(manifest, inventory)
    assert plan.actions == ()


def test_present_legacy_entry_produces_no_action_regardless_of_manifest_state(tmp_path):
    (tmp_path / "old.txt").write_text("hand-authored\n")
    manifest = _manifest(
        _whole_file("a", "old.txt", ArtifactClass.COPIED_MANAGED, legacy_of="succ")
    )
    inventory = classify(manifest, tmp_path)
    plan = build_plan(manifest, inventory)
    assert plan.actions == ()


def test_referenced_entry_never_gets_an_action_even_when_its_path_is_absent(tmp_path):
    manifest = _manifest(_referenced("dep", "does-not-exist"))
    inventory = classify(manifest, tmp_path)
    plan = build_plan(manifest, inventory)
    assert plan.actions == ()


def test_unparseable_hybrid_file_gets_an_action_with_chosen_anchor_best_effort_skipped(tmp_path):
    (tmp_path / "CLAUDE.md").write_text(
        _doc("intro", render_end(RegionFormat.HTML, "tiers"), "outro")
    )
    manifest = _manifest(_hybrid("h", "CLAUDE.md", "tiers"))
    inventory = classify(manifest, tmp_path)
    plan = build_plan(manifest, inventory)

    (action,) = plan.actions
    assert action.current_state == ArtifactState.PRESENT_DIVERGENT
    assert action.chosen_anchor == ()


def test_empty_plan_when_every_entry_is_present_conformant_or_present_legacy(tmp_path):
    (tmp_path / "seeded.txt").write_text("hello\n")
    (tmp_path / "old.txt").write_text("hand\n")
    manifest = _manifest(
        _whole_file("a", "seeded.txt", ArtifactClass.COPIED_SEEDED),
        _whole_file("b", "old.txt", ArtifactClass.COPIED_MANAGED, legacy_of="succ"),
        _referenced("dep"),
    )
    inventory = classify(manifest, tmp_path)
    plan = build_plan(manifest, inventory)

    assert plan.actions == ()
    assert isinstance(plan, Plan)
    restored = Plan.from_json_dict(json.loads(json.dumps(plan.to_json_dict())))
    assert restored == plan


# --- ordering / determinism -------------------------------------------------


def test_actions_are_sorted_by_artifact_id_regardless_of_manifest_authoring_order(tmp_path):
    manifest = _manifest(
        _whole_file("zeta", "z.txt", ArtifactClass.COPIED_MANAGED),
        _whole_file("alpha", "a.txt", ArtifactClass.COPIED_MANAGED),
        _whole_file("mid", "m.txt", ArtifactClass.COPIED_MANAGED),
    )
    inventory = classify(manifest, tmp_path)
    plan = build_plan(manifest, inventory)
    assert [action.artifact_id for action in plan.actions] == ["alpha", "mid", "zeta"]


def test_artifact_hashes_are_sorted_by_artifact_id(tmp_path):
    manifest = _manifest(
        _whole_file("zeta", "z.txt", ArtifactClass.COPIED_MANAGED),
        _whole_file("alpha", "a.txt", ArtifactClass.COPIED_MANAGED),
    )
    inventory = classify(manifest, tmp_path)
    plan = build_plan(manifest, inventory)
    assert [pair[0] for pair in plan.repo_fingerprint.artifact_hashes] == ["alpha", "zeta"]


def test_two_build_plan_calls_against_identical_repo_state_produce_byte_identical_json(tmp_path):
    manifest = _manifest(
        _whole_file("a", "seeded.txt", ArtifactClass.COPIED_SEEDED),
        _whole_file("b", "another.txt", ArtifactClass.COPIED_MANAGED),
    )
    inventory = classify(manifest, tmp_path)

    plan_one = build_plan(manifest, inventory)
    plan_two = build_plan(manifest, inventory)

    assert plan_one.actions == plan_two.actions
    assert plan_one.repo_fingerprint.artifact_hashes == plan_two.repo_fingerprint.artifact_hashes
    assert json.dumps(plan_one.to_json_dict()) == json.dumps(plan_two.to_json_dict())


# --- artifact_hashes content -------------------------------------------------


def test_artifact_hashes_for_an_absent_artifact_hashes_the_empty_string(tmp_path):
    manifest = _manifest(_whole_file("a", "missing.txt", ArtifactClass.COPIED_MANAGED))
    inventory = classify(manifest, tmp_path)
    plan = build_plan(manifest, inventory)

    ((artifact_id, sha),) = plan.repo_fingerprint.artifact_hashes
    assert artifact_id == "a"
    assert sha == hash_content("")


def test_artifact_hashes_for_a_present_divergent_hybrid_entry_hashes_its_real_content(tmp_path):
    text = _doc("no markers in this file at all")
    (tmp_path / "CLAUDE.md").write_text(text)
    manifest = _manifest(_hybrid("h", "CLAUDE.md", "tiers"))
    inventory = classify(manifest, tmp_path)
    plan = build_plan(manifest, inventory)

    ((artifact_id, sha),) = plan.repo_fingerprint.artifact_hashes
    assert artifact_id == "h"
    assert sha == hash_content(text)


def test_artifact_hashes_only_covers_actioned_artifacts_not_the_whole_manifest(tmp_path):
    (tmp_path / "seeded.txt").write_text("hello\n")
    manifest = _manifest(
        _whole_file("present", "seeded.txt", ArtifactClass.COPIED_SEEDED),
        _whole_file("absent", "missing.txt", ArtifactClass.COPIED_MANAGED),
        _referenced("dep"),
    )
    inventory = classify(manifest, tmp_path)
    plan = build_plan(manifest, inventory)
    assert [pair[0] for pair in plan.repo_fingerprint.artifact_hashes] == ["absent"]


# --- repo_fingerprint: non-git target repo ----------------------------------


def test_non_git_target_repo_reports_none_head_and_dirty_true(tmp_path):
    manifest = _manifest()
    inventory = classify(manifest, tmp_path)
    plan = build_plan(manifest, inventory)
    assert plan.repo_fingerprint.git_head is None
    assert plan.repo_fingerprint.dirty is True


def test_real_git_repo_reports_the_actual_head_sha_and_dirty_false_when_clean(tmp_path):
    # AD-57's own reason `RepoFingerprint` exists: a real, committed HEAD
    # and a clean worktree must report a real 40-hex-char sha and
    # `dirty=False` -- the positive path the non-git test above cannot
    # exercise (review finding: only the "not a git repo" branch was
    # covered; the branch that is the whole point of this field was not).
    _init_git_repo(tmp_path)
    expected_head = _git(tmp_path, "rev-parse", "HEAD").stdout.strip()

    manifest = _manifest()
    inventory = classify(manifest, tmp_path)
    plan = build_plan(manifest, inventory)

    assert plan.repo_fingerprint.git_head == expected_head
    assert len(plan.repo_fingerprint.git_head) == 40
    assert plan.repo_fingerprint.dirty is False


def test_real_git_repo_reports_dirty_true_once_a_tracked_file_is_edited(tmp_path):
    _init_git_repo(tmp_path)
    (tmp_path / "README.md").write_text("changed\n", encoding="utf-8")

    manifest = _manifest()
    inventory = classify(manifest, tmp_path)
    plan = build_plan(manifest, inventory)

    assert plan.repo_fingerprint.dirty is True


def test_real_git_repo_reports_dirty_true_for_an_untracked_file(tmp_path):
    _init_git_repo(tmp_path)
    (tmp_path / "untracked.txt").write_text("new\n", encoding="utf-8")

    manifest = _manifest()
    inventory = classify(manifest, tmp_path)
    plan = build_plan(manifest, inventory)

    assert plan.repo_fingerprint.dirty is True


# --- manifest / inventory mismatch ------------------------------------------


def test_build_plan_raises_value_error_when_inventory_was_not_built_from_this_manifest(tmp_path):
    # `classify(manifest_one, ...)` produces one `Classification` per
    # `manifest_one.entries`; handing that `Inventory` to `build_plan`
    # alongside an unrelated `manifest_two` means every `entry_id` it
    # carries is unknown to `manifest_two.entries` (review finding: this
    # previously raised a bare, unnamed `KeyError`).
    manifest_one = _manifest(_whole_file("a", "a.txt", ArtifactClass.COPIED_MANAGED))
    manifest_two = _manifest(_whole_file("b", "b.txt", ArtifactClass.COPIED_MANAGED))
    inventory = classify(manifest_one, tmp_path)

    with pytest.raises(ValueError, match="not built from this manifest"):
        build_plan(manifest_two, inventory)


# --- write_plan / load_plan / default_plan_path -----------------------------


def test_write_plan_then_load_plan_round_trips_field_for_field(tmp_path):
    plan = _sample_plan(tmp_path)

    plan_path = tmp_path / "out" / "plan.json"  # parent does not exist yet
    write_plan(plan, plan_path)
    restored = load_plan(plan_path)

    assert restored == plan
    assert plan_path.is_file()


def test_default_plan_path_is_dot_marshal_plan_json_under_repo_root(tmp_path):
    assert default_plan_path(tmp_path) == tmp_path / ".marshal" / "plan.json"


def test_write_plan_at_default_plan_path_lands_under_dot_marshal(tmp_path):
    plan = _sample_plan(tmp_path)
    path = default_plan_path(tmp_path)

    write_plan(plan, path)

    assert path == tmp_path / ".marshal" / "plan.json"
    assert path.is_file()
    assert load_plan(path) == plan


def test_load_plan_raises_value_error_naming_a_missing_key(tmp_path):
    path = tmp_path / "plan.json"
    path.write_text(json.dumps({"actions": []}))  # missing "repo_fingerprint"
    with pytest.raises(ValueError, match="repo_fingerprint"):
        load_plan(path)


def test_load_plan_raises_value_error_for_syntactically_invalid_json(tmp_path):
    path = tmp_path / "plan.json"
    path.write_text("{not valid json")
    with pytest.raises(ValueError):
        load_plan(path)


def test_write_plan_does_not_escape_non_ascii_characters(tmp_path):
    # `Plan` is "the single artifact a human reviews before Genesis writes
    # anything" (P-04) -- a non-ASCII path should read as itself in
    # `plan.json`, not as `\uXXXX` escapes (review finding: the stdlib
    # `json.dumps` default escapes every non-ASCII code point).
    manifest = _manifest(_whole_file("a", "café/déjà-vu.txt", ArtifactClass.COPIED_MANAGED))
    inventory = classify(manifest, tmp_path)
    plan = build_plan(manifest, inventory)

    path = tmp_path / "plan.json"
    write_plan(plan, path)

    raw = path.read_text(encoding="utf-8")
    assert "café/déjà-vu.txt" in raw
    assert "\\u" not in raw
    assert load_plan(path) == plan


def test_load_plan_raises_value_error_for_a_bad_enum_value_inside_an_action(tmp_path):
    plan = _sample_plan(tmp_path)
    data = plan.to_json_dict()
    data["actions"][0]["current_state"] = "not-a-real-state"
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        load_plan(path)


# --- real packaged manifest regression (mirrors S-9.5's own convention) ----

# templates/manifest.yaml (Story 7.5): 43 entries, 16 referenced -- so
# exactly 27 non-referenced entries, each ABSENT against a repo missing
# every materialized artifact. Region counts per hybrid entry, pinned like
# test_seed_templates_manifest.py's own EXPECTED_* constants.
EXPECTED_NON_REFERENCED_ENTRY_COUNT = 27
EXPECTED_HYBRID_REGION_COUNTS = {
    "agents-md": 3,
    "claude-md": 2,
    "gitignore": 1,
    "readme-badge": 1,
}


@pytest.fixture(scope="module")
def real_manifest():
    manifest_ref = resources.files("pyforge.marshal.seed.templates") / "manifest.yaml"
    with resources.as_file(manifest_ref) as manifest_path:
        return load_manifest(manifest_path)


def test_real_manifest_over_a_repo_missing_every_artifact_gives_one_absent_action_per_non_referenced_entry(
    real_manifest, tmp_path
):
    inventory = classify(real_manifest, tmp_path)
    plan = build_plan(real_manifest, inventory)

    expected_ids = sorted(
        entry.id
        for entry in real_manifest.entries
        if entry.artifact_class is not ArtifactClass.REFERENCED
    )
    assert len(expected_ids) == EXPECTED_NON_REFERENCED_ENTRY_COUNT
    assert [action.artifact_id for action in plan.actions] == expected_ids
    assert all(action.current_state == ArtifactState.ABSENT for action in plan.actions)
    assert all(action.target_state == ArtifactState.PRESENT_CONFORMANT for action in plan.actions)

    by_id = {action.artifact_id: action for action in plan.actions}
    for entry_id, expected_region_count in EXPECTED_HYBRID_REGION_COUNTS.items():
        assert len(by_id[entry_id].chosen_anchor) == expected_region_count, entry_id

    for action in plan.actions:
        if action.artifact_class is not ArtifactClass.HYBRID_MANAGED_REGION:
            assert action.chosen_anchor == ()


def test_real_manifest_plan_over_an_empty_repo_round_trips_through_write_and_load(
    real_manifest, tmp_path
):
    inventory = classify(real_manifest, tmp_path)
    plan = build_plan(real_manifest, inventory)

    path = default_plan_path(tmp_path)
    write_plan(plan, path)

    assert load_plan(path) == plan


# --- fingerprint_drift (Story 10.3) -----------------------------------------

# Every case below builds a plan with `build_plan` and then verifies it with
# `fingerprint_drift` against the SAME repo -- producer and verifier in one
# assertion, which is the whole reason the two live in one module.
#
# Isolating one divergence at a time takes some care: editing or creating a
# file in a CLEAN git repo also flips `dirty`, so the artifact-level cases
# below deliberately build their plan against an ALREADY-dirty repo (one
# untracked file), leaving `git_head`/`dirty` unchanged by the mutation
# under test and the artifact entry as the only reported drift.


def test_fingerprint_drift_is_empty_for_a_plan_just_built_against_a_clean_git_repo(tmp_path):
    _init_git_repo(tmp_path)
    manifest = _manifest(_whole_file("a", "missing.txt", ArtifactClass.COPIED_MANAGED))
    inventory = classify(manifest, tmp_path)
    plan = build_plan(manifest, inventory)

    assert fingerprint_drift(plan, tmp_path) == ()


def test_fingerprint_drift_is_empty_for_a_plan_just_built_against_a_non_git_repo(tmp_path):
    # `_git_head`/`_repo_is_dirty` degrade to `None`/`True` for a non-git
    # target; the verifier must compare against those same degraded values
    # rather than treating "not a git repo" as drift on its own.
    plan = _sample_plan(tmp_path)
    assert fingerprint_drift(plan, tmp_path) == ()


def test_fingerprint_drift_names_git_head_once_a_new_commit_lands(tmp_path):
    _init_git_repo(tmp_path)
    plan = _sample_plan(tmp_path)
    assert fingerprint_drift(plan, tmp_path) == ()

    _git(tmp_path, "commit", "--allow-empty", "-m", "second")

    drift = fingerprint_drift(plan, tmp_path)
    assert len(drift) == 1
    assert "git_head" in drift[0]


def test_fingerprint_drift_names_dirty_once_the_worktree_is_dirtied(tmp_path):
    _init_git_repo(tmp_path)
    plan = _sample_plan(tmp_path)
    assert fingerprint_drift(plan, tmp_path) == ()

    (tmp_path / "untracked.txt").write_text("new\n", encoding="utf-8")

    drift = fingerprint_drift(plan, tmp_path)
    assert len(drift) == 1
    assert "dirty" in drift[0]


def test_fingerprint_drift_names_the_artifact_id_when_an_actioned_file_is_hand_edited(tmp_path):
    _init_git_repo(tmp_path)
    (tmp_path / "CLAUDE.md").write_text(_doc("no markers in this file at all"), encoding="utf-8")
    manifest = _manifest(_hybrid("h", "CLAUDE.md", "tiers"))
    inventory = classify(manifest, tmp_path)
    plan = build_plan(manifest, inventory)
    assert plan.actions[0].current_state == ArtifactState.PRESENT_DIVERGENT
    assert fingerprint_drift(plan, tmp_path) == ()

    (tmp_path / "CLAUDE.md").write_text(_doc("hand-edited since the plan"), encoding="utf-8")

    drift = fingerprint_drift(plan, tmp_path)
    assert len(drift) == 1
    # `startswith`, not `in`: a bare `"h" in message` would pass on the word
    # "hashed" alone and prove nothing about the artifact id.
    assert drift[0].startswith("h:")
    assert "CLAUDE.md" in drift[0]


def test_fingerprint_drift_names_the_artifact_id_when_an_absent_artifact_has_appeared(tmp_path):
    # The case a `current_state`-gated read would miss entirely: `build_plan`
    # recorded `hash_content("")` for an ABSENT artifact WITHOUT touching the
    # filesystem, so re-hashing through that same gate would match forever
    # and let apply clobber a file that appeared in between (AR-5).
    _init_git_repo(tmp_path)
    (tmp_path / "unrelated.txt").write_text("dirties the worktree\n", encoding="utf-8")
    manifest = _manifest(_whole_file("a", "seeded.txt", ArtifactClass.COPIED_SEEDED))
    inventory = classify(manifest, tmp_path)
    plan = build_plan(manifest, inventory)
    assert plan.actions[0].current_state == ArtifactState.ABSENT
    assert fingerprint_drift(plan, tmp_path) == ()

    (tmp_path / "seeded.txt").write_text("appeared out of nowhere\n", encoding="utf-8")

    drift = fingerprint_drift(plan, tmp_path)
    assert len(drift) == 1
    assert drift[0].startswith("a:")
    assert "seeded.txt" in drift[0]


def test_fingerprint_drift_names_a_hashed_id_that_no_action_carries(tmp_path):
    # `build_plan` emits exactly one hash per action, so an orphan pair can
    # only come from a corrupted or hand-edited plan.json -- a Plan that no
    # longer holds its own construction invariant, which must be refused
    # rather than partially verified.
    plan = _sample_plan(tmp_path)
    tampered = dataclasses.replace(
        plan,
        repo_fingerprint=dataclasses.replace(
            plan.repo_fingerprint,
            artifact_hashes=plan.repo_fingerprint.artifact_hashes + (("ghost", "deadbeef"),),
        ),
    )

    drift = fingerprint_drift(tampered, tmp_path)
    assert len(drift) == 1
    assert "ghost" in drift[0]


@pytest.mark.parametrize(
    "reappeared",
    [b"\xff\xfe hand-written latin-1 \xe9\n", b""],
    ids=["undecodable-bytes", "empty-file"],
)
def test_fingerprint_drift_names_an_absent_artifact_that_reappeared_unreadable(
    tmp_path, reappeared
):
    """Review finding, reproduced by executing the real code: an `ABSENT`
    artifact is recorded as `hash_content("")`, and the verification read
    degrades an undecodable or empty target back to `''` -- so a pure
    CONTENT comparison matches, reports no drift, and apply destroys a file
    a human put there. Existence, not the hash, is what separates "still
    absent" from "something appeared here"."""
    plan = _sample_plan(tmp_path)
    absent = next(
        action
        for action in plan.actions
        if action.current_state is ArtifactState.ABSENT
    )
    target = tmp_path / absent.target_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(reappeared)

    drift = fingerprint_drift(plan, tmp_path)
    assert any(absent.artifact_id in line for line in drift), drift


def test_fingerprint_drift_names_a_present_artifact_that_became_unreadable(tmp_path):
    """The mirror of the case above: a target present and readable when the
    plan was built, now undecodable. A hash comparison alone would miss this
    whenever the recorded hash happens to be `hash_content("")` -- i.e. a
    genuinely empty artifact -- so readability is compared, not inferred."""
    (tmp_path / "CLAUDE.md").write_text("", encoding="utf-8")
    manifest = _manifest(_hybrid("claude-md", "CLAUDE.md", "tiers"))
    plan = build_plan(manifest, classify(manifest, tmp_path))
    assert plan.actions, "fixture must produce an action"

    (tmp_path / "CLAUDE.md").write_bytes(b"\xff\xfe not utf-8 at all \xe9\n")

    drift = fingerprint_drift(plan, tmp_path)
    assert any("claude-md" in line for line in drift), drift


def test_fingerprint_drift_names_a_duplicate_artifact_id(tmp_path):
    """Review finding: the id -> target lookup is a dict, so two actions
    sharing an `artifact_id` silently collapse onto the last one and the
    first one's target is never verified. `Plan.from_json_dict` rejects
    duplicates, but `Plan` carries no `__post_init__` and direct
    construction is a supported entry path, so `fingerprint_drift` must
    refuse rather than partially verify."""
    (tmp_path / "a.txt").write_text("a\n", encoding="utf-8")
    (tmp_path / "b.txt").write_text("b\n", encoding="utf-8")
    plan = _sample_plan(tmp_path)
    first = plan.actions[0]
    tampered = dataclasses.replace(
        plan,
        actions=(
            dataclasses.replace(first, target_path="a.txt"),
            dataclasses.replace(first, target_path="b.txt"),
        ),
        repo_fingerprint=dataclasses.replace(
            plan.repo_fingerprint,
            artifact_hashes=((first.artifact_id, hash_content("a\n")),),
        ),
    )

    drift = fingerprint_drift(tampered, tmp_path)
    assert any("more than one Action" in line for line in drift), drift


def test_fingerprint_drift_names_an_actioned_id_the_fingerprint_never_hashed(tmp_path):
    """Review finding: the correspondence has to be checked in BOTH
    directions. `Plan.from_json_dict` validates that `actions` are unique
    and sorted but never cross-checks them against `artifact_hashes`, so a
    hand-edited plan.json that DROPS a pair would leave that artifact
    silently unverified -- the one hole through which exactly the stale
    content `fingerprint_drift` exists to catch could still reach apply."""
    plan = _sample_plan(tmp_path)
    assert plan.repo_fingerprint.artifact_hashes, "fixture must hash at least one artifact"
    dropped_id = plan.repo_fingerprint.artifact_hashes[0][0]
    tampered = dataclasses.replace(
        plan,
        repo_fingerprint=dataclasses.replace(
            plan.repo_fingerprint,
            artifact_hashes=plan.repo_fingerprint.artifact_hashes[1:],
        ),
    )

    drift = fingerprint_drift(tampered, tmp_path)
    assert len(drift) == 1
    assert dropped_id in drift[0]


def test_fingerprint_drift_reports_every_divergence_not_just_the_first(tmp_path):
    _init_git_repo(tmp_path)
    manifest = _manifest(_whole_file("a", "seeded.txt", ArtifactClass.COPIED_SEEDED))
    inventory = classify(manifest, tmp_path)
    plan = build_plan(manifest, inventory)

    (tmp_path / "seeded.txt").write_text("appeared\n", encoding="utf-8")
    _git(tmp_path, "commit", "--allow-empty", "-m", "second")

    drift = fingerprint_drift(plan, tmp_path)
    assert len(drift) == 3
    assert drift[0].startswith("git_head:")
    assert drift[1].startswith("dirty:")
    assert drift[2].startswith("a:")


def test_fingerprint_drift_agrees_with_classify_about_a_dangling_symlink(tmp_path):
    """Review finding, verified by execution: the verifier was STRICTER than the
    producer, and a dangling symlink is the state where they disagreed.

    ``detect/inventory.py::_classify_entry`` asks ``target.exists()``, which
    follows the broken link and reports False -- so ``build_plan`` records
    ``ABSENT``. ``fingerprint_drift`` had been given an extra
    ``or target.is_symlink()``, which reports True, so it refused the plan the
    INSTANT ``build_plan`` produced it. Re-planning yielded the identical plan,
    leaving apply permanently unreachable with a remedy string ("re-run the
    plan") that could not work.

    Producer and verifier agreeing is the stated reason this function lives in
    ``plan/build.py`` at all, so the predicate must be ``exists()`` and nothing
    more. (What rollback does to a symlinked target is a separate, filed bound.)
    """
    _init_git_repo(tmp_path)
    (tmp_path / "CLAUDE.md").symlink_to(tmp_path / "nowhere.txt")
    manifest = _manifest(_whole_file("claude-md", "CLAUDE.md", ArtifactClass.COPIED_SEEDED))
    inventory = classify(manifest, tmp_path)
    plan = build_plan(manifest, inventory)

    assert plan.actions[0].current_state == ArtifactState.ABSENT
    assert fingerprint_drift(plan, tmp_path) == (), (
        "a plan build_plan just produced must never be refused as stale"
    )


def test_fingerprint_drift_reports_an_id_hashed_twice_in_the_fingerprint(tmp_path):
    """The mirror of the duplicate-ACTION-id check. Review finding, verified by
    execution: only the actions side was guarded, so a fingerprint carrying the
    same id twice reported ``()`` -- against this function's own "a corrupted
    plan is refused, never partially verified". ``Plan.from_json_dict``
    validates uniqueness for ``actions`` only, and direct construction validates
    neither."""
    _init_git_repo(tmp_path)
    plan = _sample_plan(tmp_path)
    assert plan.repo_fingerprint.artifact_hashes, "fixture must hash at least one artifact"
    first = plan.repo_fingerprint.artifact_hashes[0]
    tampered = dataclasses.replace(
        plan,
        repo_fingerprint=dataclasses.replace(
            plan.repo_fingerprint,
            artifact_hashes=(first, *plan.repo_fingerprint.artifact_hashes),
        ),
    )

    drift = fingerprint_drift(tampered, tmp_path)
    assert any(
        d.startswith(f"{first[0]}:") and "hashed more than once" in d for d in drift
    ), drift


# --- opted_out (Story 8.5) ---------------------------------------------------
#
# `opted_out` carries already-read `state.opt_out_key` strings; the verb
# layer passes `frozenset(state.opted_out)` through. Every case below spells
# its keys with the real `opt_out_key`, never a hand-typed "id#region"
# literal, so a change to the wire form cannot leave these tests asserting a
# spelling nothing produces.


def test_an_absent_hybrid_whose_only_region_is_opted_out_produces_no_action(tmp_path):
    """FR-112's whole point: an opted-out region is never re-inserted, so
    the entry has nothing left to do and never reaches the plan at all."""
    manifest = _manifest(_hybrid("h", "CLAUDE.md", "tiers"))
    inventory = classify(manifest, tmp_path)

    plan = build_plan(manifest, inventory, opted_out=frozenset({opt_out_key("h", "tiers")}))

    assert plan.actions == ()
    assert plan.repo_fingerprint.artifact_hashes == ()


def test_a_present_divergent_hybrid_whose_missing_region_is_opted_out_produces_no_action(
    tmp_path,
):
    """The AC's plan-suppression row: the markers were deleted from a file
    that is otherwise present, which classifies `present-divergent` -- and
    with the region opted out there is nothing to insert."""
    (tmp_path / "CLAUDE.md").write_text(_doc("intro", "outro"), encoding="utf-8", newline="")
    manifest = _manifest(_hybrid("h", "CLAUDE.md", "tiers"))
    inventory = classify(manifest, tmp_path)
    assert inventory.classifications[0].state is ArtifactState.PRESENT_DIVERGENT

    plan = build_plan(manifest, inventory, opted_out=frozenset({opt_out_key("h", "tiers")}))

    assert plan.actions == ()
    assert plan.repo_fingerprint.artifact_hashes == ()


def test_a_partially_opted_out_hybrid_keeps_one_action_naming_only_the_pending_region(
    tmp_path,
):
    manifest = _manifest(
        _hybrid("h", "CLAUDE.md", "tiers", "model-badge", anchors={"model-badge": ("<top>",)})
    )
    inventory = classify(manifest, tmp_path)

    plan = build_plan(manifest, inventory, opted_out=frozenset({opt_out_key("h", "tiers")}))

    (action,) = plan.actions
    assert action.current_state == ArtifactState.ABSENT
    assert action.chosen_anchor == (("model-badge", "<top>"),)
    assert [pair[0] for pair in plan.repo_fingerprint.artifact_hashes] == ["h"]


def test_an_opt_out_naming_another_artifacts_region_suppresses_nothing(tmp_path):
    manifest = _manifest(_hybrid("h", "CLAUDE.md", "tiers"))
    inventory = classify(manifest, tmp_path)

    plan = build_plan(
        manifest, inventory, opted_out=frozenset({opt_out_key("other", "tiers")})
    )

    (action,) = plan.actions
    assert action.chosen_anchor == (("tiers", None),)


def test_an_unparseable_hybrid_file_is_never_zero_pending_and_keeps_its_action(tmp_path):
    """A structural defect must not retire an entry: "cannot parse" degrades
    `chosen_anchor` to `()`, but the `Action` (and its hash) stay, so a
    broken file is still reported rather than silently dropped."""
    (tmp_path / "CLAUDE.md").write_text(
        _doc("intro", render_end(RegionFormat.HTML, "tiers"), "outro"),
        encoding="utf-8",
        newline="",
    )
    manifest = _manifest(_hybrid("h", "CLAUDE.md", "tiers"))
    inventory = classify(manifest, tmp_path)

    plan = build_plan(manifest, inventory, opted_out=frozenset({opt_out_key("h", "tiers")}))

    (action,) = plan.actions
    assert action.current_state == ArtifactState.PRESENT_DIVERGENT
    assert action.chosen_anchor == ()
    assert [pair[0] for pair in plan.repo_fingerprint.artifact_hashes] == ["h"]


def test_a_whole_file_entry_is_never_suppressed_by_an_empty_pending_set(tmp_path):
    """Suppression is a HYBRID rule. A whole-file artifact declares no
    regions at all, so "nothing pending" must never be read as "nothing to
    do" for it."""
    manifest = _manifest(_whole_file("a", "seeded.txt", ArtifactClass.COPIED_SEEDED))
    inventory = classify(manifest, tmp_path)

    plan = build_plan(manifest, inventory, opted_out=frozenset({opt_out_key("a", "tiers")}))

    (action,) = plan.actions
    assert action.artifact_id == "a"
    assert action.chosen_anchor == ()


def test_a_manifest_id_the_opt_out_grammar_cannot_spell_still_plans(tmp_path):
    """`ManifestEntry` requires only a non-blank `id`, so an id carrying an
    interior space is legal while `state.opted_out`'s grammar cannot spell
    it. Such an entry must plan exactly as it did before this story -- never
    raise the `ValueError` `opt_out_key` reserves for a caller minting a
    key."""
    manifest = _manifest(_hybrid("has a space", "CLAUDE.md", "tiers"))
    inventory = classify(manifest, tmp_path)

    plan = build_plan(manifest, inventory, opted_out=frozenset({"has a space#tiers"}))

    (action,) = plan.actions
    assert action.artifact_id == "has a space"
    assert action.chosen_anchor == (("tiers", None),)


def _seed_state(*, opted_out: tuple[str, ...]) -> SeedState:
    """A minimal schema-valid ``SeedState`` carrying only the field the verb
    layer projects into ``build_plan`` -- built here rather than imported so
    the reinstate test below runs against the REAL ``clear_opt_out``, not a
    hand-edited tuple that could diverge from what it produces."""
    return SeedState(
        model_version=_VERSION,
        seed_model_version="0.1.0",
        adopted_at="2026-08-20T09:15:00Z",
        last_update="2026-08-20T09:15:00Z",
        mode="adopt",
        agents=("claude-code",),
        managed=(),
        skips=(),
        legacy=(),
        migrations_applied=(),
        opted_out=opted_out,
    )


def test_a_cleared_opt_out_makes_the_region_planned_for_insertion_again(tmp_path):
    """The AC's reinstate row, through the exact projection the verb layer
    performs (`frozenset(state.opted_out)`): the region produces no action
    while the opt-out stands, and is planned again the moment
    `clear_opt_out` withdraws it -- the `--reinstate` path S-10.6 calls."""
    manifest = _manifest(_hybrid("h", "CLAUDE.md", "tiers"))
    inventory = classify(manifest, tmp_path)
    opted = _seed_state(opted_out=(opt_out_key("h", "tiers"),))

    suppressed = build_plan(manifest, inventory, opted_out=frozenset(opted.opted_out))
    assert suppressed.actions == ()

    reinstated = clear_opt_out(opted, "h", "tiers")
    plan = build_plan(manifest, inventory, opted_out=frozenset(reinstated.opted_out))

    (action,) = plan.actions
    assert action.current_state == ArtifactState.ABSENT
    assert action.chosen_anchor == (("tiers", None),)


def test_opted_out_is_keyword_only(tmp_path):
    """Positional would let a caller pass it where a future third parameter
    belongs, silently."""
    manifest = _manifest(_hybrid("h", "CLAUDE.md", "tiers"))
    inventory = classify(manifest, tmp_path)
    with pytest.raises(TypeError):
        build_plan(manifest, inventory, frozenset())  # type: ignore[misc]


@pytest.mark.parametrize(
    "build_fixture",
    [
        pytest.param(lambda root: None, id="absent-hybrid"),
        pytest.param(
            lambda root: (root / "CLAUDE.md").write_text(
                _hybrid_text("tiers"), encoding="utf-8", newline=""
            ),
            id="present-divergent-hybrid",
        ),
        pytest.param(
            lambda root: (root / "CLAUDE.md").write_text(
                _doc("intro", render_end(RegionFormat.HTML, "tiers"), "outro"),
                encoding="utf-8",
                newline="",
            ),
            id="unparseable-hybrid",
        ),
    ],
)
def test_the_default_empty_opted_out_leaves_output_byte_identical(tmp_path, build_fixture):
    """The AC's compatibility clause, asserted on the JSON rather than on
    the objects: with the default, `build_plan`'s output must be exactly
    what an explicit empty frozenset produces -- and therefore exactly what
    it produced before this story."""
    build_fixture(tmp_path)
    manifest = _manifest(
        _hybrid("h", "CLAUDE.md", "tiers", "model-badge", anchors={"model-badge": ("<top>",)}),
        _whole_file("a", "seeded.txt", ArtifactClass.COPIED_SEEDED),
    )
    inventory = classify(manifest, tmp_path)

    defaulted = build_plan(manifest, inventory)
    explicit = build_plan(manifest, inventory, opted_out=frozenset())

    assert json.dumps(defaulted.to_json_dict()) == json.dumps(explicit.to_json_dict())
    assert defaulted.actions, "fixture must produce at least one action"
