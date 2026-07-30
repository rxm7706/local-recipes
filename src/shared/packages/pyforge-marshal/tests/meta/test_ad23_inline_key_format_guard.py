"""Meta test -- the AD-23 "one owner of the story-key format" guard (Story
1.2). Mirrors ``tests/meta/test_ad7_verdict_sole_ownership.py``'s AST-scan
technique exactly, adapted to a different structural signature.

AST-scan every module in the installed package EXCEPT ``core/identity.py``
and fail if any of them inline-formats what looks structurally like a story
key: either

(a) an f-string (``ast.JoinedStr``) containing exactly two
    ``ast.FormattedValue`` nodes with a literal ``.`` or ``-`` as the ONLY
    text directly between them (other literal text may surround the pair --
    only the middle separator is checked); or
(b) a ``str.format()`` call on a string literal containing exactly two
    ``{}``/``{name}`` placeholders with a literal ``.`` or ``-`` as the only
    text between them.

Positively asserts ``core/identity.py`` itself defines
``normalize``/``render_feed_key``/``render_filename_slug``/
``render_branch_segment``/``render_merge_subject``/``parse_merge_subject``
(a simple introspection check, not AST -- that module is the one place this
formatting shape is legitimate and is excluded from the scan).

Bounds (stated, not aspirational): this is a best-effort STATIC check, like
the AD-7 guard it mirrors. It only recognizes exactly-two-placeholder
literals with a bare ``.``/``-`` separator; a key built via concatenation,
an f-string with an intervening variable, or a template stored in a
non-literal string (``call_format_on_a_variable.format(...)``) is out of
scope. ``tests/unit/test_identity.py``'s round-trip tests are the
behavioral backstop for identity's own correctness.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

import pyforge.marshal
from pyforge.marshal.core import identity

_PACKAGE_FILE = pyforge.marshal.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
PACKAGE_DIR = Path(_PACKAGE_FILE).resolve().parent

_IDENTITY_MODULE = PACKAGE_DIR / "core" / "identity.py"

_SEPARATORS = frozenset({".", "-"})

# f"{a}{b}"-shaped-but-with-a-named-field .format() placeholder scan.
_FORMAT_PLACEHOLDER_RE = re.compile(r"\{[^{}]*\}")


def _package_modules() -> list[Path]:
    return sorted(PACKAGE_DIR.rglob("*.py"))


def _non_identity_modules() -> list[Path]:
    # Full-path comparison, not basename -- mirrors the AD-7 guard's own
    # rationale: only core/identity.py is exempt, not any future same-named
    # file elsewhere in the tree.
    return [path for path in _package_modules() if path != _IDENTITY_MODULE]


def _module_id(path: Path) -> str:
    return str(path.relative_to(PACKAGE_DIR))


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _formatted_value_indices(values: list[ast.expr]) -> list[int]:
    return [i for i, value in enumerate(values) if isinstance(value, ast.FormattedValue)]


def _middle_literal(values: list[ast.expr], start: int, end: int) -> str | None:
    """The concatenation of every literal fragment strictly between indices
    ``start`` and ``end`` in an f-string's ``.values`` list -- ``None`` if
    anything in that span isn't a plain string ``Constant`` (defensive; a
    JoinedStr's fragments between two FormattedValues are always a single
    Constant in practice, but this stays a total function regardless)."""
    parts: list[str] = []
    for node in values[start + 1 : end]:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            parts.append(node.value)
        else:
            return None
    return "".join(parts)


def _joined_str_violations(tree: ast.Module) -> list[int]:
    violations: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.JoinedStr):
            continue
        indices = _formatted_value_indices(node.values)
        if len(indices) != 2:
            continue
        middle = _middle_literal(node.values, indices[0], indices[1])
        if middle in _SEPARATORS:
            violations.append(node.lineno)
    return violations


def _format_call_violations(tree: ast.Module) -> list[int]:
    violations: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (
            isinstance(func, ast.Attribute)
            and func.attr == "format"
            and isinstance(func.value, ast.Constant)
            and isinstance(func.value.value, str)
        ):
            continue
        template = func.value.value
        placeholders = list(_FORMAT_PLACEHOLDER_RE.finditer(template))
        if len(placeholders) != 2:
            continue
        middle = template[placeholders[0].end() : placeholders[1].start()]
        if middle in _SEPARATORS:
            violations.append(node.lineno)
    return violations


def _inline_key_format_violations(tree: ast.Module) -> list[int]:
    """The combined (a)+(b) detector, sorted by line number."""
    return sorted(_joined_str_violations(tree) + _format_call_violations(tree))


def test_package_scan_surface_is_not_empty():
    modules = _non_identity_modules()
    assert modules, "inline-key-format guard found no modules to scan"
    names = {path.name for path in _package_modules()}
    assert "identity.py" in names, "identity.py missing from the installed package"


@pytest.mark.parametrize("module_path", _non_identity_modules(), ids=_module_id)
def test_no_inline_key_format_outside_identity(module_path: Path):
    violations = _inline_key_format_violations(_parse(module_path))
    assert not violations, (
        f"{module_path.name} inline-formats a story-key-shaped literal "
        f"(two placeholders joined by a bare '.'/'-') at line(s) "
        f"{violations} -- only core/identity.py owns the story-key format "
        "(AD-23)"
    )


def test_identity_module_defines_the_full_ad23_surface():
    for name in (
        "normalize",
        "render_feed_key",
        "render_filename_slug",
        "render_branch_segment",
        "render_merge_subject",
        "parse_merge_subject",
    ):
        assert hasattr(identity, name), f"core/identity.py is missing {name!r}"


# --- detector self-tests: non-vacuous proof ---------------------------------


def test_detector_fires_on_dot_joined_f_string():
    tree = ast.parse('epic = 1\nseq = 2\nkey = f"{epic}.{seq}"\n')
    assert _inline_key_format_violations(tree) == [3]


def test_detector_fires_on_hyphen_joined_f_string():
    tree = ast.parse('epic = 1\nseq = 2\nkey = f"{epic}-{seq}"\n')
    assert _inline_key_format_violations(tree) == [3]


def test_detector_fires_on_dot_joined_format_call():
    tree = ast.parse('key = "{}.{}".format(1, 2)\n')
    assert _inline_key_format_violations(tree) == [1]


def test_detector_fires_on_named_placeholder_format_call():
    tree = ast.parse('key = "{epic}-{seq}".format(epic=1, seq=2)\n')
    assert _inline_key_format_violations(tree) == [1]


def test_detector_fires_with_surrounding_literal_text():
    tree = ast.parse('epic = 1\nseq = 2\nkey = f"story {epic}.{seq} merged"\n')
    assert _inline_key_format_violations(tree) == [3]


def test_detector_does_not_fire_on_unrelated_f_string_with_one_placeholder():
    tree = ast.parse('x = 1\ny = f"only {x} here"\n')
    assert _inline_key_format_violations(tree) == []


def test_detector_does_not_fire_on_three_placeholder_f_string():
    tree = ast.parse('a = 1\nb = 2\nc = 3\ny = f"{a}.{b}.{c}"\n')
    assert _inline_key_format_violations(tree) == []


def test_detector_does_not_fire_on_a_different_separator():
    tree = ast.parse('a = 1\nb = 2\ny = f"{a}/{b}"\n')
    assert _inline_key_format_violations(tree) == []


def test_detector_does_not_fire_when_placeholders_are_glued_together():
    tree = ast.parse('a = 1\nb = 2\ny = f"{a}{b}"\n')
    assert _inline_key_format_violations(tree) == []


def test_detector_does_not_fire_on_a_two_placeholder_format_call_with_a_different_separator():
    tree = ast.parse('key = "{}/{}".format(1, 2)\n')
    assert _inline_key_format_violations(tree) == []


def test_guard_is_alive_synthetic_violation_fires_and_identity_defines_surface():
    """Non-vacuous proof, mirroring the AD-7 guard's own final test: (1) the
    detector demonstrably fires on a synthetic violation, and (2)
    ``core/identity.py`` itself structurally defines every AD-23 render/parse
    function the positive assertion above checks for."""
    synthetic_violation = 'epic = 1\nseq = 2\nkey = f"{epic}.{seq}"\n'
    assert _inline_key_format_violations(ast.parse(synthetic_violation)) == [3]

    tree = _parse(_IDENTITY_MODULE)
    functions = {
        node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
    }
    assert {
        "normalize",
        "render_feed_key",
        "render_filename_slug",
        "render_branch_segment",
        "render_merge_subject",
        "parse_merge_subject",
    } <= functions
