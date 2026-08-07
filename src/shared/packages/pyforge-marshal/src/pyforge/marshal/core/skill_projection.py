"""Skill-tree projection planning (Story 6.2, FR-41, AD-12/AD-36).

89 skills live only under this repo's canonical `.claude/skills/`; four of
the six packaged ``bmad-loop`` adapter profiles (``codex``, ``gemini``,
``copilot``, ``antigravity``) declare ``skill_tree = ".agents/skills"`` --
a directory that does not exist. `cli/adapters.py::run_adapters_sync`
projects the canonical tree into every OTHER tree a configured adapter
declares. This module is the pure planning core (AD-4: no I/O, no
``os``/``subprocess``/``time``, no ``pyforge.marshal.adapters`` import) --
every filesystem read/write lives in ``cli/adapters.py`` and
``adapters/fs_local.py`` instead.

``CANONICAL_SKILL_TREE_REL`` is a plain, declared constant (AD-12:
"canonical versus derived, declared not inferred") -- never derived from
any adapter's own profile, even though the ``claude``/``opencode-http``
profiles happen to declare the identical value today.

``PROJECTION_MECHANISM_BY_PLATFORM`` is the ONE ``(platform -> mechanism)``
table AD-36 requires: "the projection mechanism per (adapter, platform) is
declared in one table with one owner; no module branches on platform
outside it." Today it has exactly one row -- ``{"posix": "symlink"}`` --
because this project's only supported install targets (linux-64,
osx-arm64, NFR-13) are both POSIX and Windows is explicitly deferred
(architecture.md, "Windows-native operation... maturity, not
availability"). It stays a real, addressable table: a future Windows row
is a one-line addition here, never a new branch at any caller.
``mechanism_for_platform`` is the one pure lookup function every caller
uses instead of comparing ``os.name``/``sys.platform`` directly --
enforced by ``tests/meta/test_ad36_projection_mechanism_table.py``.

A single whole-directory symlink is the projection mechanism, never a
per-skill link or copy: the cheapest mechanism FR-41 asks for, and the one
that makes "re-projection after a source change converges" true BY
CONSTRUCTION -- a directory symlink cannot drift in CONTENT (only in
TARGET), so a canonical-tree content change is visible through every
projected tree with zero additional writes. ``plan_projection`` therefore
only ever decides, per DISTINCT declared tree value (never per adapter --
several packaged profiles commonly share one tree value, and one repoint
satisfies all of them), whether that tree needs to be projected, and which
previously-projected trees are now stale (a tree the manifest recorded but
no configured adapter declares any more)."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

# AD-36's one declared table. NFR-13 scopes install targets to
# linux-64/osx-arm64 (both POSIX); Windows is deferred. Adding a Windows
# row here needs no caller change.
PROJECTION_MECHANISM_BY_PLATFORM: Mapping[str, str] = {
    "posix": "symlink",
}

# AD-12: the canonical source tree is declared, never inferred.
CANONICAL_SKILL_TREE_REL = ".claude/skills"


def mechanism_for_platform(platform_name: str) -> str | None:
    """The ONE pure lookup into ``PROJECTION_MECHANISM_BY_PLATFORM`` --
    ``None`` for a platform with no declared row (AD-36: no filesystem
    action is safe to take without a declared mechanism)."""
    return PROJECTION_MECHANISM_BY_PLATFORM.get(platform_name)


@dataclass(frozen=True)
class TreeProjectionAction:
    """One DISTINCT non-canonical tree value that at least one configured
    adapter declares, plus every adapter name that declares it (for
    reporting -- ``cli/adapters.py`` never repoints more than once per
    distinct ``tree``)."""

    tree: str
    adapters: tuple[str, ...]


@dataclass(frozen=True)
class ProjectionPlan:
    """The full, pure output of ``plan_projection`` -- ``cli/adapters.py``
    executes it against real ``FsPort``/``HarnessPort`` instances and
    reports what it did; this dataclass carries no I/O result itself."""

    canonical: str
    platform_mechanism: str | None
    to_project: tuple[TreeProjectionAction, ...]
    to_remove: tuple[str, ...]
    unsupported_trees: tuple[str, ...]


def plan_projection(
    skill_trees_by_adapter: Mapping[str, str],
    *,
    canonical: str = CANONICAL_SKILL_TREE_REL,
    previously_projected: Iterable[str] = (),
    platform_name: str,
) -> ProjectionPlan:
    """Compute what ``cli/adapters.py::run_adapters_sync`` must do, given:

    - ``skill_trees_by_adapter`` -- every CONFIGURED adapter's declared
      ``skill_tree`` (``HarnessPort.adapter_skill_trees``'s return value --
      every profile ``bmad_loop.adapters.profile.load_profiles`` resolves
      for the project, not merely the one loop home's own active adapter;
      see this story's own Design Notes for why "configured adapters" is
      read this way).
    - ``canonical`` -- the declared canonical tree (AD-12); a tree equal to
      it needs no projection at all (it already IS the canonical tree).
    - ``previously_projected`` -- the tree values a prior run's manifest
      recorded as projected; anything here no longer in the DESIRED set is
      stale and belongs in ``to_remove``.
    - ``platform_name`` -- looked up via ``mechanism_for_platform``. When
      it resolves to ``None`` (no declared row), BOTH ``to_project`` and
      ``to_remove`` come back empty and every desired tree is named in
      ``unsupported_trees`` instead -- this function takes no stance on
      whether removal would be safe on an undeclared platform, so it
      conservatively proposes none (see Design Notes: "conservative --
      this story does not attempt to reason about whether a POSIX-created
      symlink is safely removable from an unsupported-platform process").
    """
    mechanism = mechanism_for_platform(platform_name)

    desired_trees: dict[str, list[str]] = {}
    for adapter_name, tree in skill_trees_by_adapter.items():
        if tree == canonical:
            continue
        desired_trees.setdefault(tree, []).append(adapter_name)

    desired = frozenset(desired_trees)
    previously_projected_set = frozenset(previously_projected)

    if mechanism is None:
        return ProjectionPlan(
            canonical=canonical,
            platform_mechanism=None,
            to_project=(),
            to_remove=(),
            unsupported_trees=tuple(sorted(desired)),
        )

    to_project = tuple(
        TreeProjectionAction(tree=tree, adapters=tuple(sorted(desired_trees[tree])))
        for tree in sorted(desired)
    )
    to_remove = tuple(sorted(previously_projected_set - desired))

    return ProjectionPlan(
        canonical=canonical,
        platform_mechanism=mechanism,
        to_project=to_project,
        to_remove=to_remove,
        unsupported_trees=(),
    )
