"""Path confinement for recipe-facing CLIs (AUD-CFE-001 / -002 / -006).

Three surfaces take a caller-supplied path or recipe slug and act on it:

  * ``submit_pr.prepare_branch``  -- joins a slug onto ``recipes/`` and
    ``copytree``s the result into a PUBLIC fork.
  * ``recipe_editor.execute_actions`` -- rewrites the file in place.
  * ``conda_forge_server.trigger_build`` -- builds whatever recipe it is given.

All three are reachable as MCP tool arguments, so the path is untrusted input.
Every one of them confines through this module, so the notion of "inside the
recipes tree" is defined exactly once.

The confinement root is resolved **per call** (not captured at import) so the
test suite can point it at a tmp tree via ``CFE_RECIPES_ROOT``. That is a
launch-time configuration knob; the untrusted input this module guards is the
path argument, never the root.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

# .claude/skills/conda-forge-expert/scripts/ -> repo root (4 levels up)
REPO_ROOT = Path(__file__).resolve().parents[4]

#: Default confinement root. Prefer :func:`recipes_root` — this constant does
#: not honour ``CFE_RECIPES_ROOT``.
RECIPES_ROOT = REPO_ROOT / "recipes"

ROOT_ENV_VAR = "CFE_RECIPES_ROOT"

# conda package names are [a-z0-9._-]; local mirror dirs occasionally carry
# upstream capitalisation (see G94's case-variant output dirs), so uppercase is
# allowed too. Everything else -- separators, "..", spaces, control bytes -- is
# rejected by the same rule.
_SAFE_NAME_RE = re.compile(r"\A[A-Za-z0-9._-]+\Z")


def recipes_root() -> Path:
    """Return the directory every recipe-facing write is confined to."""
    override = os.environ.get(ROOT_ENV_VAR)
    if override:
        return Path(override).expanduser().resolve()
    return RECIPES_ROOT.resolve()


def validate_recipe_name(recipe_name: str) -> None:
    """Reject anything that is not a single flat recipe slug.

    Raises ``ValueError`` for path separators, traversal, control characters,
    and the bare ``.`` / ``..`` names.
    """
    if not isinstance(recipe_name, str) or not recipe_name:
        raise ValueError(f"Invalid recipe name: {recipe_name!r}")
    if recipe_name in (".", ".."):
        raise ValueError(f"Invalid recipe name: {recipe_name!r}")
    if not _SAFE_NAME_RE.match(recipe_name):
        raise ValueError(
            "Recipe name must be a single feedstock slug under recipes/ "
            f"(letters, digits, '.', '_', '-'), got: {recipe_name!r}"
        )


def resolve_under_recipes(path: Path | str) -> Path:
    """Resolve ``path`` and require that it lies inside the recipes root.

    ``Path.resolve()`` follows symlinks, so a symlink inside ``recipes/`` that
    points outside the tree is rejected as well -- which is the intent.
    """
    resolved = Path(path).expanduser().resolve()
    root = recipes_root()
    if resolved != root and not resolved.is_relative_to(root):
        raise ValueError(f"Path must be under {root}, got: {path}")
    return resolved


def validate_recipe_file_path(recipe_path: Path | str) -> Path:
    """YAML suffix check plus confinement to the recipes root.

    Accepts an existing file or a new file in an existing recipe directory.
    Relative paths are interpreted against the repo root, matching how the
    CLIs are normally invoked.
    """
    recipe_path = Path(recipe_path).expanduser()
    if recipe_path.suffix not in (".yaml", ".yml"):
        raise ValueError(f"Recipe path must be a .yaml/.yml file, got: {recipe_path}")
    if not recipe_path.is_absolute():
        recipe_path = REPO_ROOT / recipe_path
    resolved = resolve_under_recipes(recipe_path)
    if resolved.exists() and not resolved.is_file():
        raise ValueError(f"Recipe path is not a file: {resolved}")
    if not resolved.exists() and not resolved.parent.exists():
        raise ValueError(f"Recipe directory does not exist: {resolved.parent}")
    return resolved
