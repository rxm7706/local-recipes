"""Meta test -- the AD-19 "no adapter-name branching outside the seam"
guard (Story 6.1). Mirrors ``test_ad23_inline_key_format_guard.py``'s
AST-scan technique exactly, adapted to a different structural signature.

AST-scan every module in ``pyforge.marshal.cli``/``core``/``supervisor``/
``ports`` -- EXCLUDING ``pyforge.marshal.adapters`` entirely (AD-3 already
reserves that package, specifically ``adapters/harness_bmadloop.py``, as
the one module structurally permitted to know adapter identities via the
vendored ``bmad_loop`` package -- see that module's own docstring) -- and
fail if any of them contains an ``ast.Compare`` node testing equality
(``==``) between something plausibly named ``adapter``/``adapter_name`` (a
``Name`` or ``Attribute`` node whose ``id``/``attr`` contains "adapter",
case-insensitively) and a string constant. This is the exact shape FR-51's
own "profile-driven, zero adapter-name branching" invariant forbids: a
``cli/``/``core/``/``supervisor/``/``ports/`` module that special-cases
"if this is the claude adapter, do X" rather than sourcing every
adapter-specific fact from ``HarnessPort``'s own profile-backed methods
(``adapter_binary``/``adapter_seed_files``/``adapter_first_run_note``).

Bounds (stated, not aspirational): this is a best-effort STATIC check, like
the AD-7/AD-23 guards it mirrors. It only recognizes a direct ``==``
comparison against a string constant where one side's own name plausibly
mentions "adapter" -- a branch expressed some other way (a dict dispatch
keyed by adapter name, a ``match`` statement, an indirect alias that does
not carry "adapter" in its own name) is out of scope. The detector's own
aliveness is proven via a synthetic violation it is asserted to catch,
mirroring the AD-7/AD-23 guards' own "fires on a synthetic violation"
proof."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import pyforge.marshal

_PACKAGE_FILE = pyforge.marshal.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
PACKAGE_DIR = Path(_PACKAGE_FILE).resolve().parent

# The one module AD-3 structurally permits to know adapter identities --
# excluded from the scan entirely, not just this one detector's own
# carve-out (mirrors AD-23's identical "one legitimate owner, everything
# else is scanned" shape).
_ADAPTERS_DIR = PACKAGE_DIR / "adapters"

# The scan surface: exactly the four packages the spec names, never the
# whole installed tree (which would also sweep up `adapters/` a second,
# redundant way and this package's own top-level `__init__.py`/`schemas/`,
# neither of which is in scope for this invariant).
_SCANNED_SUBPACKAGES = ("cli", "core", "supervisor", "ports")


def _package_modules() -> list[Path]:
    modules: list[Path] = []
    for subpackage in _SCANNED_SUBPACKAGES:
        modules.extend(sorted((PACKAGE_DIR / subpackage).rglob("*.py")))
    return modules


def _module_id(path: Path) -> str:
    return str(path.relative_to(PACKAGE_DIR))


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _mentions_adapter(node: ast.expr) -> bool:
    """``True`` if ``node`` is a ``Name``/``Attribute`` whose own ``id``/
    ``attr`` contains "adapter" (case-insensitively) -- the plausibly-
    adapter-identity side of a comparison."""
    if isinstance(node, ast.Name):
        return "adapter" in node.id.lower()
    if isinstance(node, ast.Attribute):
        return "adapter" in node.attr.lower()
    return False


def _is_string_constant(node: ast.expr) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, str)


def _adapter_branch_violations(tree: ast.Module) -> list[int]:
    """Every ``ast.Compare`` node testing ``==`` between an adapter-named
    name/attribute and a string constant -- either operand order
    (``adapter_name == "claude"`` or ``"claude" == adapter_name``)."""
    violations: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        if len(node.ops) != 1 or not isinstance(node.ops[0], ast.Eq):
            continue
        left = node.left
        [right] = node.comparators
        if (_mentions_adapter(left) and _is_string_constant(right)) or (
            _is_string_constant(left) and _mentions_adapter(right)
        ):
            violations.append(node.lineno)
    return violations


def test_package_scan_surface_is_not_empty():
    modules = _package_modules()
    assert modules, "AD-19 adapter-branch guard found no modules to scan"


def test_adapters_package_is_excluded_from_the_scan_surface():
    scanned = {path.resolve() for path in _package_modules()}
    assert not any(_ADAPTERS_DIR in path.parents for path in scanned)


@pytest.mark.parametrize("module_path", _package_modules(), ids=_module_id)
def test_no_adapter_name_branch_outside_adapters_package(module_path: Path):
    violations = _adapter_branch_violations(_parse(module_path))
    assert not violations, (
        f"{_module_id(module_path)} branches on an adapter-name-shaped "
        f"equality comparison at line(s) {violations} -- only "
        "adapters/harness_bmadloop.py is structurally permitted to know "
        "adapter identities (AD-3/AD-19); every adapter-specific fact must "
        "come from HarnessPort's own profile-backed methods instead"
    )


# --- detector self-test: non-vacuous proof -----------------------------------


def test_detector_fires_on_synthetic_adapter_name_branch():
    synthetic_violation = 'adapter_name = "claude"\nif adapter_name == "claude":\n    pass\n'
    assert _adapter_branch_violations(ast.parse(synthetic_violation)) == [2]


def test_detector_fires_on_synthetic_branch_with_reversed_operand_order():
    synthetic_violation = 'adapter_name = "claude"\nif "claude" == adapter_name:\n    pass\n'
    assert _adapter_branch_violations(ast.parse(synthetic_violation)) == [2]


def test_detector_fires_on_attribute_access_form():
    synthetic_violation = "if profile.adapter_name == 'claude':\n    pass\n"
    assert _adapter_branch_violations(ast.parse(synthetic_violation)) == [1]


def test_detector_does_not_fire_on_an_unrelated_equality_comparison():
    tree = ast.parse('story_key = "1.1"\nif story_key == "1.1":\n    pass\n')
    assert _adapter_branch_violations(tree) == []


def test_detector_does_not_fire_on_a_non_string_comparison():
    tree = ast.parse("adapter_count = 1\nif adapter_count == 1:\n    pass\n")
    assert _adapter_branch_violations(tree) == []


def test_detector_does_not_fire_on_membership_rather_than_equality():
    tree = ast.parse(
        'adapter_name = "claude"\nif adapter_name in ("claude", "codex"):\n    pass\n'
    )
    assert _adapter_branch_violations(tree) == []
