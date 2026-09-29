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

The live-repo integration test is ``@pytest.mark.slow`` (real detect/plan
over the full tree); unit tests below pin the exclusion and diff helpers so
``pyforge-marshal-test`` still exercises the oracle contract without the cost.
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path

import pytest

from pyforge.marshal.seed.detect.inventory import ArtifactState
from pyforge.marshal.seed.model.manifest import (
    ArtifactClass,
    Manifest,
    load_manifest,
)
from pyforge.marshal.seed.plan.types import Action
from pyforge.marshal.seed.verbs.adopt import run_adopt

# Explicit exclusion (Story 12.2 AC): the three ``unclassified-deferred`` ids
# from ``seed/templates/manifest.yaml`` — deferral is enumerated, not a gap.
UNCLASSIFIED_DEFERRED_ARTIFACT_IDS: frozenset[str] = frozenset(
    {
        "claude-skills",
        "pixi-toml-tasks",
        "library-llms-full",
    }
)


def _local_recipes_root() -> Path | None:
    """Return the ``local-recipes`` monorepo root when this test runs in-tree."""
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (candidate / "recipes").is_dir():
            package_root = candidate / "src" / "shared" / "packages" / "pyforge-marshal"
            if package_root.is_dir():
                return candidate
    return None


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

        result = run_adopt(
            repo_root,
            manifest,
            apply=False,
            confirm=_unreachable_confirm,
        )
        filtered = assertable_adopt_actions(result.plan.actions)
        assert filtered == (), format_plan_diff(filtered)
    finally:
        if had_plan:
            plan_path.write_bytes(prior_plan_bytes)  # type: ignore[arg-type]
        elif plan_path.is_file():
            plan_path.unlink()
            marshal_dir = plan_path.parent
            if marshal_dir.is_dir() and not any(marshal_dir.iterdir()):
                marshal_dir.rmdir()
