"""The ``local-recipes`` empty-plan oracle (Story 12.2, SC-02, NFR-M2, AD-60).

Runs ``marshal seed adopt`` in dry-run mode (``apply=False``) against the
monorepo checkout that hosts this package and asserts the plan carries **zero
actions** for every manifest artifact except the three ``unclassified-deferred``
entries (explicit exclusion below — not silent special-casing).

A non-empty filtered plan fails with a readable diff naming each diverged
artifact id, class, path, states, and rationale — the same fields a human
reviews in ``cli/seed.py``'s plan renderer.

**K-02:** if reaching an empty filtered plan requires excluding anything beyond
``unclassified-deferred``, this test is the escalation surface — do not widen
the exclusion set to greenwash drift.

Story 97.2 adds an ``update`` leg beside it: ``run_update`` in dry-run mode
plans zero actions, and its ``plan.skipped`` equals
``expected_update_dry_run_skipped`` -- the repo-wide skips plus the two
per-checkout symlink skips, each expected only where the checkout lacks its
target (a fresh clone, as CI runs it).

The live-repo integration tests is ``@pytest.mark.slow`` (real detect/plan
over the full tree); unit tests below pin the exclusion and diff helpers so
``pyforge-marshal-test`` still exercises the oracle contract without the cost.
"""

from __future__ import annotations

import subprocess
from importlib import resources
from pathlib import Path

import pytest

from pyforge.marshal.seed.detect.inventory import ArtifactState
from pyforge.marshal.seed.fs import NeverWrite
from pyforge.marshal.seed.model.manifest import (
    ArtifactClass,
    Manifest,
    load_manifest,
)
from pyforge.marshal.seed.plan.types import NO_PACKAGED_PAYLOAD_SKIP_PATTERN, Action, SkippedArtifact
from pyforge.marshal.seed.state import SeedState, write_state
from pyforge.marshal.seed.verbs.adopt import run_adopt
from pyforge.marshal.seed.verbs.update import run_update

# Explicit exclusion (Story 12.2 AC): the three ``unclassified-deferred`` ids
# from ``seed/templates/manifest.yaml`` — deferral is enumerated, not a gap.
UNCLASSIFIED_DEFERRED_ARTIFACT_IDS: frozenset[str] = frozenset(
    {
        "claude-skills",
        "pixi-toml-tasks",
        "library-llms-full",
    }
)

# Story 86.2: genesis bootstrap records explicit seed skips in
# ``.marshal/seed-state.yml``; reasons live here because skip patterns carry
# no reason field (K-02 — not a silent widening of the deferred-id filter).
# Story 97.2 (AC6): ``update`` dry-run skips on this repo — genesis-recorded
# ``state.skips`` patterns plus ``copied-managed`` entries with no packaged
# payload. Not a widened adopt oracle (K-02).
LOCAL_RECIPES_UPDATE_DRY_RUN_SKIPPED: dict[str, str] = {
    "agents-md": "AGENTS.md",
    "claude-md": "CLAUDE.md",
    "projects-index": "_bmad-output/PROJECTS.md",
    "bmad-switch": NO_PACKAGED_PAYLOAD_SKIP_PATTERN,
    "bmad-loop-worktree": NO_PACKAGED_PAYLOAD_SKIP_PATTERN,
}

# Story 97.2 CI fix (2026-10-12): the update skips that depend on the checkout,
# not on the repo. Both paths are per-checkout BMAD symlinks (gitignored;
# ``scripts/bmad-switch`` or ``steward workspace start`` creates them), so a
# fresh clone -- the ``marshal-local-recipes-seed-oracle`` CI lane -- has
# neither. There ``classify`` reads each ``absent``, ``build_plan`` plans its
# creation, and the genesis-recorded ``state.skips`` pattern (the path itself)
# moves that action into ``plan.skipped``. In a developer checkout both are
# ``present-conformant``, ``update`` plans nothing for them, and nothing is
# skipped. ``adopt`` needs no such split: its first-claim pass plans a present,
# unmanaged entry too, so the recorded skip catches both shapes. Each id here is
# expected exactly when its target is absent, by ``classify``'s own test (the
# path, symlinks followed, does not exist) -- one exact expectation per shape,
# never the union of both (K-02). The reasons are in
# ``LOCAL_RECIPES_GENESIS_RECORDED_SKIP_ARTIFACTS``.
LOCAL_RECIPES_UPDATE_SKIPPED_WHEN_ABSENT: dict[str, str] = {
    "planning-artifacts-symlink": "_bmad-output/planning-artifacts",
    "implementation-artifacts-symlink": "_bmad-output/implementation-artifacts",
}

LOCAL_RECIPES_GENESIS_RECORDED_SKIP_ARTIFACTS: dict[str, str] = {
    "agents-md": "AGENTS.md already carries instruction-surface content (scribe CAP-27, point-don't-copy)",
    "claude-md": "CLAUDE.md already carries instruction-surface content (scribe CAP-27, point-don't-copy)",
    "projects-index": "_bmad-output/PROJECTS.md already carries the live projects table",
    "gemini-md": "GEMINI.md is a per-tool addendum owned by scribe's instruction-surface parity test",
    "copilot-instructions": (
        ".github/copilot-instructions.md is a per-tool addendum owned by scribe's instruction-surface parity test"
    ),
    "cursor-rules": ".cursor/rules/specs.mdc is a per-tool addendum owned by scribe's instruction-surface parity test",
    "planning-artifacts-symlink": (
        "_bmad-output/planning-artifacts is a per-checkout symlink that scripts/bmad-switch creates"
    ),
    "implementation-artifacts-symlink": (
        "_bmad-output/implementation-artifacts is a per-checkout symlink that scripts/bmad-switch creates"
    ),
    "specs-dir-legacy": "docs/specs/ is the retired legacy intake tier (doctor Story 37.1 removed it)",
}


def _local_recipes_root() -> Path | None:
    """Return the ``local-recipes`` monorepo root when this test runs in-tree."""
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (candidate / "recipes").is_dir():
            package_root = candidate / "src" / "shared" / "packages" / "pyforge-marshal"
            if package_root.is_dir():
                return candidate
    return None


def _resolve_project_slug(repo_root: Path) -> str:
    marker = repo_root / "_bmad" / "custom" / ".active-project"
    if marker.is_file():
        text = marker.read_text(encoding="utf-8").strip()
        if text:
            return text
    from_env = __import__("os").environ.get("BMAD_ACTIVE_PROJECT", "").strip()
    if from_env:
        return from_env
    return "pyforge-marshal"


def _load_packaged_manifest() -> Manifest:
    manifest_ref = resources.files("pyforge.marshal.seed.templates") / "manifest.yaml"
    with resources.as_file(manifest_ref) as manifest_path:
        return load_manifest(manifest_path)


def assertable_adopt_actions(
    actions: tuple[Action, ...],
    *,
    deferred_ids: frozenset[str] = UNCLASSIFIED_DEFERRED_ARTIFACT_IDS,
) -> tuple[Action, ...]:
    """Manifest-scoped actions only — drops ``unclassified-deferred`` by id."""
    unknown_deferred = deferred_ids - {
        entry.id
        for entry in _load_packaged_manifest().entries
        if entry.artifact_class is ArtifactClass.UNCLASSIFIED_DEFERRED
    }
    if unknown_deferred:
        raise AssertionError(
            "UNCLASSIFIED_DEFERRED_ARTIFACT_IDS lists ids no longer "
            f"unclassified-deferred in the packaged manifest: {sorted(unknown_deferred)}"
        )
    return tuple(action for action in actions if action.artifact_id not in deferred_ids)


def expected_update_dry_run_skipped(repo_root: Path) -> dict[str, str]:
    """The exact skip set ``update`` emits on ``repo_root``: the repo-wide
    ``LOCAL_RECIPES_UPDATE_DRY_RUN_SKIPPED`` plus each
    ``LOCAL_RECIPES_UPDATE_SKIPPED_WHEN_ABSENT`` id whose target this checkout
    does not hold (its recorded pattern is its path)."""
    expected = dict(LOCAL_RECIPES_UPDATE_DRY_RUN_SKIPPED)
    for artifact_id, path in LOCAL_RECIPES_UPDATE_SKIPPED_WHEN_ABSENT.items():
        if not (repo_root / path).exists():
            expected[artifact_id] = path
    return expected


def assertable_update_skipped(
    skipped: tuple[SkippedArtifact, ...],
    *,
    expected: dict[str, str] = LOCAL_RECIPES_UPDATE_DRY_RUN_SKIPPED,
) -> None:
    """Every skip ``update`` emits on this repo, with the expected pattern."""
    actual = {item.artifact_id: item.pattern for item in skipped}
    if actual != expected:
        missing = set(expected) - set(actual)
        extra = set(actual) - set(expected)
        wrong = {
            artifact_id: (expected[artifact_id], actual[artifact_id])
            for artifact_id in set(expected) & set(actual)
            if actual[artifact_id] != expected[artifact_id]
        }
        raise AssertionError(
            "update dry-run skip set drifted — reconcile LOCAL_RECIPES_UPDATE_DRY_RUN_SKIPPED"
            " or LOCAL_RECIPES_UPDATE_SKIPPED_WHEN_ABSENT."
            f" missing={sorted(missing)!r} extra={sorted(extra)!r} wrong_pattern={wrong!r}"
        )


def assertable_skipped_artifact_ids(
    skipped: tuple[SkippedArtifact, ...],
    *,
    expected: dict[str, str] = LOCAL_RECIPES_GENESIS_RECORDED_SKIP_ARTIFACTS,
) -> frozenset[str]:
    """The skip set the oracle expects after genesis bootstrap — ids only."""
    unknown = set(expected) - {entry.id for entry in _load_packaged_manifest().entries}
    if unknown:
        raise AssertionError(
            f"LOCAL_RECIPES_GENESIS_RECORDED_SKIP_ARTIFACTS lists ids absent from the manifest: {sorted(unknown)}"
        )
    actual = frozenset(item.artifact_id for item in skipped)
    if actual != frozenset(expected):
        missing = frozenset(expected) - actual
        extra = actual - frozenset(expected)
        raise AssertionError(
            "genesis skip set drifted — update LOCAL_RECIPES_GENESIS_RECORDED_SKIP_ARTIFACTS or"
            f" reconcile seed state. missing={sorted(missing)!r} extra={sorted(extra)!r}"
        )
    return actual


def format_plan_diff(actions: tuple[Action, ...]) -> str:
    """Readable, line-oriented diff of non-empty adopt plan actions."""
    if not actions:
        return "plan is empty"
    lines = [f"non-empty adopt plan ({len(actions)} action(s)):"]
    for action in actions:
        lines.append(
            "  "
            f"{action.artifact_id} ({action.target_path}): "
            f"{action.current_state.value} -> {action.target_state.value}; "
            f"{action.rationale}"
        )
    return "\n".join(lines)


def test_unclassified_deferred_exclusion_is_explicit_and_manifest_aligned():
    packaged = _load_packaged_manifest()
    deferred_in_manifest = {
        entry.id for entry in packaged.entries if entry.artifact_class is ArtifactClass.UNCLASSIFIED_DEFERRED
    }
    assert deferred_in_manifest == UNCLASSIFIED_DEFERRED_ARTIFACT_IDS

    actions = (
        Action(
            artifact_id="claude-skills",
            artifact_class=ArtifactClass.UNCLASSIFIED_DEFERRED,
            current_state=ArtifactState.ABSENT,
            target_state=ArtifactState.PRESENT_CONFORMANT,
            target_path=".claude/skills/**",
            rationale="deferred",
            chosen_anchor=(),
        ),
        Action(
            artifact_id="agents-md",
            artifact_class=ArtifactClass.HYBRID_MANAGED_REGION,
            current_state=ArtifactState.PRESENT_DIVERGENT,
            target_state=ArtifactState.PRESENT_CONFORMANT,
            target_path="AGENTS.md",
            rationale="missing region",
            chosen_anchor=(("## The tiers",),),
        ),
    )
    filtered = assertable_adopt_actions(actions, deferred_ids=UNCLASSIFIED_DEFERRED_ARTIFACT_IDS)
    assert [action.artifact_id for action in filtered] == ["agents-md"]


def test_genesis_recorded_skip_artifact_ids_are_manifest_backed():
    packaged = _load_packaged_manifest()
    by_id = {entry.id: entry for entry in packaged.entries}
    for artifact_id, reason in LOCAL_RECIPES_GENESIS_RECORDED_SKIP_ARTIFACTS.items():
        assert artifact_id in by_id, reason
        assert reason.strip()


def test_checkout_dependent_update_skips_are_manifest_backed_and_genesis_recorded():
    by_id = {entry.id: entry for entry in _load_packaged_manifest().entries}
    for artifact_id, path in LOCAL_RECIPES_UPDATE_SKIPPED_WHEN_ABSENT.items():
        assert by_id[artifact_id].path == path
        assert artifact_id in LOCAL_RECIPES_GENESIS_RECORDED_SKIP_ARTIFACTS
    assert not set(LOCAL_RECIPES_UPDATE_SKIPPED_WHEN_ABSENT) & set(LOCAL_RECIPES_UPDATE_DRY_RUN_SKIPPED)


_PLANNING = LOCAL_RECIPES_UPDATE_SKIPPED_WHEN_ABSENT["planning-artifacts-symlink"]
_IMPLEMENTATION = LOCAL_RECIPES_UPDATE_SKIPPED_WHEN_ABSENT["implementation-artifacts-symlink"]


def _link_bmad_artifacts(repo_root: Path, *, dangling: frozenset[str] = frozenset()) -> None:
    """Both per-checkout symlinks, as ``scripts/bmad-switch`` makes them; a
    link named in ``dangling`` points at a project directory that is missing."""
    for link_path in (_PLANNING, _IMPLEMENTATION):
        link = repo_root / link_path
        target = Path("projects") / "demo" / link.name
        if link_path not in dangling:
            (link.parent / target).mkdir(parents=True)
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(target, target_is_directory=True)


@pytest.mark.parametrize(
    ("shape", "expected_skipped"),
    [
        # A fresh clone (the CI lane): neither symlink exists.
        ("fresh-clone", {"planning-artifacts-symlink": _PLANNING, "implementation-artifacts-symlink": _IMPLEMENTATION}),
        # A developer checkout or dispatch worktree: both resolve.
        ("developer-checkout", {}),
        # A link whose project directory is gone reads absent, as `classify` reads it.
        ("dangling-implementation-link", {"implementation-artifacts-symlink": _IMPLEMENTATION}),
    ],
)
def test_update_skips_a_checkout_dependent_entry_exactly_when_its_target_is_absent(
    tmp_path: Path, shape: str, expected_skipped: dict[str, str]
):
    """Pins both checkout shapes against the real ``run_update``: a recorded
    skip reaches ``plan.skipped`` only for an entry the plan would create, and
    ``expected_update_dry_run_skipped`` predicts exactly that set."""
    # Rung 1 needs a git repo even for a dry run; rung 2 (a clean tree) does not.
    subprocess.run(["git", "-C", str(tmp_path), "init", "-q", "-b", "main"], check=True, capture_output=True)
    if shape == "developer-checkout":
        _link_bmad_artifacts(tmp_path)
    elif shape == "dangling-implementation-link":
        _link_bmad_artifacts(tmp_path, dangling=frozenset({_IMPLEMENTATION}))
    packaged = _load_packaged_manifest()
    manifest = Manifest(
        model_version=packaged.model_version,
        never_write=packaged.never_write,
        entries=tuple(entry for entry in packaged.entries if entry.id in LOCAL_RECIPES_UPDATE_SKIPPED_WHEN_ABSENT),
    )
    write_state(
        SeedState(
            model_version=packaged.model_version,
            seed_model_version="0.1.0",
            adopted_at="2026-10-11T08:57:57Z",
            last_update="2026-10-11T08:57:57Z",
            mode="adopt",
            agents=(),
            managed=(),
            skips=tuple(LOCAL_RECIPES_UPDATE_SKIPPED_WHEN_ABSENT.values()),
            legacy=(),
            migrations_applied=(),
            opted_out=(),
        ),
        repo_root=tmp_path,
        never_write=NeverWrite(patterns=()),
    )

    def _unreachable_confirm() -> bool:
        raise AssertionError("dry-run must not confirm")

    result = run_update(tmp_path, manifest, confirm=_unreachable_confirm, in_loop_home=False)

    assert result.plan.actions == (), format_plan_diff(result.plan.actions)
    assert {item.artifact_id: item.pattern for item in result.plan.skipped} == expected_skipped
    predicted = expected_update_dry_run_skipped(tmp_path)
    assert {key: predicted[key] for key in predicted if key in LOCAL_RECIPES_UPDATE_SKIPPED_WHEN_ABSENT} == (
        expected_skipped
    )
    assert {key: predicted[key] for key in predicted if key not in LOCAL_RECIPES_UPDATE_SKIPPED_WHEN_ABSENT} == (
        LOCAL_RECIPES_UPDATE_DRY_RUN_SKIPPED
    )


def test_format_plan_diff_names_diverged_artifacts():
    actions = (
        Action(
            artifact_id="gitignore",
            artifact_class=ArtifactClass.HYBRID_MANAGED_REGION,
            current_state=ArtifactState.PRESENT_DIVERGENT,
            target_state=ArtifactState.PRESENT_CONFORMANT,
            target_path=".gitignore",
            rationale="missing model-ignores region",
            chosen_anchor=(("<top>",),),
        ),
    )
    text = format_plan_diff(actions)
    assert "gitignore (.gitignore):" in text
    assert "missing model-ignores region" in text


@pytest.mark.slow
def test_local_recipes_adopt_dry_run_yields_empty_plan_excluding_deferred():
    repo_root = _local_recipes_root()
    if repo_root is None:
        pytest.skip("not running inside the local-recipes monorepo checkout")

    manifest = _load_packaged_manifest()
    plan_path = repo_root / ".marshal" / "plan.json"
    had_plan = plan_path.is_file()
    prior_plan_bytes = plan_path.read_bytes() if had_plan else None

    try:

        def _unreachable_confirm() -> bool:
            raise AssertionError("dry-run must not confirm")

        slug = _resolve_project_slug(repo_root)
        result = run_adopt(
            repo_root,
            manifest,
            apply=False,
            confirm=_unreachable_confirm,
            slug=slug or None,
            in_loop_home=False,
        )
        filtered = assertable_adopt_actions(result.plan.actions)
        assert filtered == (), format_plan_diff(filtered)
        assertable_skipped_artifact_ids(result.plan.skipped)
    finally:
        if had_plan:
            plan_path.write_bytes(prior_plan_bytes)  # type: ignore[arg-type]
        elif plan_path.is_file():
            plan_path.unlink()
            marshal_dir = plan_path.parent
            if marshal_dir.is_dir() and not any(marshal_dir.iterdir()):
                marshal_dir.rmdir()


@pytest.mark.slow
def test_local_recipes_update_dry_run_yields_empty_plan_with_documented_skips():
    repo_root = _local_recipes_root()
    if repo_root is None:
        pytest.skip("not running inside the local-recipes monorepo checkout")

    manifest = _load_packaged_manifest()
    plan_path = repo_root / ".marshal" / "plan.json"
    had_plan = plan_path.is_file()
    prior_plan_bytes = plan_path.read_bytes() if had_plan else None

    try:

        def _unreachable_confirm() -> bool:
            raise AssertionError("dry-run must not confirm")

        slug = _resolve_project_slug(repo_root)
        result = run_update(
            repo_root,
            manifest,
            confirm=_unreachable_confirm,
            slug=slug or None,
            in_loop_home=False,
        )
        assert result.plan.actions == (), format_plan_diff(result.plan.actions)
        assertable_update_skipped(result.plan.skipped, expected=expected_update_dry_run_skipped(repo_root))
    finally:
        if had_plan:
            plan_path.write_bytes(prior_plan_bytes)  # type: ignore[arg-type]
        elif plan_path.is_file():
            plan_path.unlink()
            marshal_dir = plan_path.parent
            if marshal_dir.is_dir() and not any(marshal_dir.iterdir()):
                marshal_dir.rmdir()
