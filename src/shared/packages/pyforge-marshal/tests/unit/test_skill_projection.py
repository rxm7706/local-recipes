"""Unit tests for ``core.skill_projection`` (Story 6.2, FR-41, AD-12/AD-36)
-- pure, no filesystem, no ``HarnessPort``/``FsPort``."""

from __future__ import annotations

from pyforge.marshal.core.skill_projection import (
    CANONICAL_SKILL_TREE_REL,
    PROJECTION_MECHANISM_BY_PLATFORM,
    ProjectionPlan,
    TreeProjectionAction,
    mechanism_for_platform,
    plan_projection,
)


def test_canonical_constant_is_declared():
    assert CANONICAL_SKILL_TREE_REL == ".claude/skills"


def test_mechanism_table_has_a_posix_row():
    assert PROJECTION_MECHANISM_BY_PLATFORM["posix"] == "symlink"


def test_mechanism_for_platform_posix():
    assert mechanism_for_platform("posix") == "symlink"


def test_mechanism_for_platform_unknown_returns_none():
    assert mechanism_for_platform("nt") is None
    assert mechanism_for_platform("bogus") is None


def test_plan_projection_no_adapters_configured():
    plan = plan_projection({}, platform_name="posix")
    assert plan == ProjectionPlan(
        canonical=CANONICAL_SKILL_TREE_REL,
        platform_mechanism="symlink",
        to_project=(),
        to_remove=(),
        unsupported_trees=(),
    )


def test_plan_projection_adapters_matching_canonical_need_no_projection():
    skill_trees = {"claude": ".claude/skills", "opencode-http": ".claude/skills"}
    plan = plan_projection(skill_trees, platform_name="posix")
    assert plan.to_project == ()
    assert plan.to_remove == ()


def test_plan_projection_groups_multiple_adapters_sharing_one_tree():
    skill_trees = {
        "codex": ".agents/skills",
        "gemini": ".agents/skills",
        "copilot": ".agents/skills",
        "antigravity": ".agents/skills",
        "claude": ".claude/skills",
    }
    plan = plan_projection(skill_trees, platform_name="posix")
    assert plan.to_project == (
        TreeProjectionAction(
            tree=".agents/skills",
            adapters=("antigravity", "codex", "copilot", "gemini"),
        ),
    )
    assert plan.to_remove == ()


def test_plan_projection_first_sync_creates_everything_desired():
    skill_trees = {"codex": ".agents/skills"}
    plan = plan_projection(skill_trees, previously_projected=(), platform_name="posix")
    assert [action.tree for action in plan.to_project] == [".agents/skills"]
    assert plan.to_remove == ()


def test_plan_projection_source_change_moves_old_tree_to_removal():
    # A project-local overlay used to declare .other/skills for "codex";
    # it now declares .agents/skills instead.
    skill_trees = {"codex": ".agents/skills"}
    plan = plan_projection(
        skill_trees, previously_projected={".other/skills"}, platform_name="posix"
    )
    assert [action.tree for action in plan.to_project] == [".agents/skills"]
    assert plan.to_remove == (".other/skills",)


def test_plan_projection_converged_state_is_still_reported_as_desired():
    # A tree already projected AND still desired: plan_projection still
    # names it in to_project (whether it is a filesystem no-op is decided
    # by cli/adapters.py comparing live symlink state, not by this pure
    # function -- see this module's own docstring).
    skill_trees = {"codex": ".agents/skills"}
    plan = plan_projection(
        skill_trees, previously_projected={".agents/skills"}, platform_name="posix"
    )
    assert [action.tree for action in plan.to_project] == [".agents/skills"]
    assert plan.to_remove == ()


def test_plan_projection_unsupported_platform_takes_no_action():
    skill_trees = {"codex": ".agents/skills"}
    plan = plan_projection(
        skill_trees, previously_projected={".stale/skills"}, platform_name="nt"
    )
    assert plan.platform_mechanism is None
    assert plan.to_project == ()
    assert plan.to_remove == ()  # conservative: removal is skipped too
    assert plan.unsupported_trees == (".agents/skills",)


def test_plan_projection_unsupported_platform_with_nothing_desired_reports_nothing():
    plan = plan_projection({"claude": ".claude/skills"}, platform_name="nt")
    assert plan.platform_mechanism is None
    assert plan.unsupported_trees == ()


def test_plan_projection_desired_trees_sorted_deterministically():
    skill_trees = {"gemini": ".agents/skills", "zzz-custom": ".zzz/skills"}
    plan = plan_projection(skill_trees, platform_name="posix")
    assert [action.tree for action in plan.to_project] == [".agents/skills", ".zzz/skills"]


def test_plan_projection_removal_set_sorted_deterministically():
    plan = plan_projection(
        {}, previously_projected={".z/skills", ".a/skills"}, platform_name="posix"
    )
    assert plan.to_remove == (".a/skills", ".z/skills")
