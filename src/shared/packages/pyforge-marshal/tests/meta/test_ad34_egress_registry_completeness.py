"""Meta test -- the AD-34 egress-port registry completeness guard (Story
2.6). Mirrors ``tests/meta/test_ad26_seed_field_access_guard.py``/
``tests/meta/test_ad7_verdict_sole_ownership.py``'s AST-scan technique
exactly, adapted to a different structural signature.

Three guards:

(1) Every ``Protocol`` subclass defined under ``pyforge.marshal.ports.*``
    has an entry in ``core.egress.EGRESS_PORTS`` -- a new port module with
    no entry fails the build (AD-34's "adding a port without classifying it
    fails the build" AC).
(2) Every port classified ``True`` in that registry has no method
    parameter type-hinted bare ``str`` (must be ``Redacted``) -- the
    structural half of "egress ports accept only a Redacted payload type".
    Also flags an UNANNOTATED parameter (no type hint accepts a bare str
    just as readily as an explicit one) and an ``Optional[str]``/``str |
    None`` union (review finding: the original guard recognized only a
    literal ``ast.Name(id="str")``, so either shape silently passed an
    egress port's own structural guarantee).
(3) No module other than ``core/egress.py`` references its private
    ``_TOKEN_SHAPE_PATTERNS``, or embeds a hand-rolled COPY of the
    token-shape vocabulary (a known prefix followed by a regex character
    class) -- the structural proof that no call site can hand-roll its own
    redaction against a copy of that vocabulary.

Positively asserts the scan surfaces are non-empty and that ``RecordPort``
(the one real egress port shipped so far) is classified ``True`` -- the
guard is alive, not vacuous.

Bounds (stated, not aspirational): this is a best-effort STATIC check, like
the AD-23/AD-7/AD-26 guards it mirrors. Guard (1)/(2) only recognize a
literal ``class Foo(Protocol):`` base spelled as the bare name ``Protocol``
or an attribute access ending in ``.Protocol`` -- a Protocol reached only
through an intermediate alias that never spells either shape is out of
scope. Guard (2)'s bare-str detection recognizes a bare ``str`` annotation,
no annotation at all, an ``Optional[str]``/``str | None`` union (quoted or
unquoted -- a string annotation is parsed and re-checked), and the
``Any``/``object`` escape hatches, across both ``def`` and ``async def``
methods -- it does NOT recognize ``*args``/``**kwargs``, a ``str`` buried
inside a container type (``list[str]``), or an annotation reached only
through a type alias; none of those shapes appear on any port method in
this package today.

Guards (1) and (2) scan the ``ports/`` package RECURSIVELY and INCLUDE
``ports/__init__.py`` (review finding: excluding it by name left a Protocol
declared directly in the package init invisible to both guards), but they
scan only ``ports/`` -- **not** ``adapters/``. AD-34's own sentence is "a
meta-test asserts no egress **adapter** accepts a bare string", so this is
a narrower guard than the rule names: it proves the PROTOCOL is typed
correctly, and relies on the adapter conforming to the Protocol it
implements. `LocalFs.write_redacted_atomic` does conform today; the gap is
recorded in ``deferred-work.md`` rather than left implicit.

Guard (3) recognizes a literal ``_TOKEN_SHAPE_PATTERNS`` token (an
``ast.Name``, an ``ast.Attribute.attr``, or an ``ast.ImportFrom`` alias)
plus a copied regex literal matching ``_COPIED_TOKEN_REGEX`` -- it cannot
catch ``getattr``-based dynamic access, nor a copy that reaches the same
shapes by a different spelling (a runtime-assembled pattern, or one whose
prefix is not immediately followed by a character class).
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

import pyforge.marshal
from pyforge.marshal.core.egress import EGRESS_PORTS

_PACKAGE_FILE = pyforge.marshal.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
PACKAGE_DIR = Path(_PACKAGE_FILE).resolve().parent
PORTS_DIR = PACKAGE_DIR / "ports"
_EGRESS_MODULE = PACKAGE_DIR / "core" / "egress.py"

_PRIVATE_NAME = "_TOKEN_SHAPE_PATTERNS"
# A hand-rolled COPY of the token-shape vocabulary: one of `core/egress.py`'s
# known prefixes immediately followed by a regex character class. See
# `_token_shape_pattern_references`.
_COPIED_TOKEN_REGEX = re.compile(r"(?:ghp_|github_pat_|AKIA|sk-)\[")


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _module_id(path: Path) -> str:
    return str(path.relative_to(PACKAGE_DIR))


def _package_modules() -> list[Path]:
    return sorted(PACKAGE_DIR.rglob("*.py"))


def _non_egress_modules() -> list[Path]:
    # Full-path comparison, not basename -- mirrors the AD-23/AD-7/AD-26
    # guards' own rationale: only core/egress.py is exempt.
    return [path for path in _package_modules() if path != _EGRESS_MODULE]


def _port_modules(root: Path | None = None) -> list[Path]:
    # rglob, not glob (follow-up review finding): the non-recursive form let a
    # Protocol defined in a ports/ SUBPACKAGE escape guards (1) and (2)
    # entirely -- and this same module already used rglob for guard (3)'s
    # surface, so the two scans disagreed about what "the ports package" means.
    #
    # `__init__.py` is NOT filtered out (review finding, verified live: both
    # reviewers found it independently). Excluding it by name left a Protocol
    # declared directly in `ports/__init__.py` invisible to guards (1) and
    # (2) -- and that file is precisely where the Story-1.1 registry
    # placeholder lived and where a future shared base Protocol or re-export
    # would naturally go. `root` is injectable so the recursion itself can be
    # proven behaviorally rather than by grepping this function's source.
    return sorted((root if root is not None else PORTS_DIR).rglob("*.py"))


# --- guard (1)/(2): Protocol discovery + bare-str-param detection ------------


def _is_protocol_base(base: ast.expr) -> bool:
    if isinstance(base, ast.Name):
        return base.id == "Protocol"
    if isinstance(base, ast.Attribute):
        return base.attr == "Protocol"
    return False


def _protocol_classes(tree: ast.Module) -> list[ast.ClassDef]:
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and any(_is_protocol_base(base) for base in node.bases)
    ]


def _all_protocol_class_names() -> list[str]:
    names: list[str] = []
    for module_path in _port_modules():
        names.extend(cls.name for cls in _protocol_classes(_parse(module_path)))
    return names


def _is_bare_str_annotation(annotation: ast.expr | None) -> bool:
    """``True`` for a bare ``str`` (``ast.Name``), for NO annotation at all
    (``None`` -- unannotated accepts a bare str just as readily as an
    explicit one), and for an ``Optional[str]``/``str | None`` union
    (either the ``ast.Subscript`` form ``Optional[str]``/``Union[str,
    None]`` or the ``ast.BinOp`` ``|`` form) -- review finding: the
    original check recognized only the first shape, so the other two
    silently passed an egress port's own structural guarantee. Does NOT
    recognize ``str`` nested inside a container type (``list[str]``) or
    reached through a type alias -- see this module's own docstring
    Bounds."""
    if annotation is None:
        return True
    # `Any`/`object` accept a bare str exactly as readily as `str` does
    # (follow-up review finding, verified live: `payload: Any` on a synthetic
    # egress port produced zero violations) -- an escape hatch that would
    # defeat the one structural guarantee AD-34 rests on.
    if isinstance(annotation, ast.Name) and annotation.id in ("str", "Any", "object"):
        return True
    if isinstance(annotation, ast.Attribute) and annotation.attr in ("Any", "object"):
        return True
    if isinstance(annotation, ast.Constant) and isinstance(annotation.value, str):
        # A STRING annotation (`payload: "str | None"`) -- parse and recurse
        # (review finding, verified live: the check used to compare the
        # constant to the literal `"str"`, so the quoted forms
        # `"str | None"`/`"Optional[str]"` produced ZERO violations while
        # their unquoted equivalents fired correctly). A forward reference
        # that does not parse is simply not bare-str-shaped.
        try:
            inner = ast.parse(annotation.value, mode="eval").body
        except SyntaxError:
            return False
        return _is_bare_str_annotation(inner)
    if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
        return _is_bare_str_annotation(annotation.left) or _is_bare_str_annotation(
            annotation.right
        )
    if isinstance(annotation, ast.Subscript):
        base = annotation.value
        base_name = base.id if isinstance(base, ast.Name) else getattr(base, "attr", None)
        if base_name in ("Optional", "Union"):
            elements = (
                annotation.slice.elts
                if isinstance(annotation.slice, ast.Tuple)
                else [annotation.slice]
            )
            return any(_is_bare_str_annotation(element) for element in elements)
    return False


def _bare_str_param_violations(cls: ast.ClassDef) -> list[str]:
    violations: list[str] = []
    for item in cls.body:
        # AsyncFunctionDef too (follow-up review finding, verified live: an
        # `async def` egress method with a bare-str parameter produced zero
        # violations -- the guard did not look at async methods at all).
        if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        params = [*item.args.posonlyargs, *item.args.args, *item.args.kwonlyargs]
        for param in params:
            if param.arg == "self":
                continue
            if _is_bare_str_annotation(param.annotation):
                violations.append(f"{cls.name}.{item.name}({param.arg})")
    return violations


# --- guard (3): private token-shape-pattern reference detection -------------


def _token_shape_pattern_references(tree: ast.Module) -> list[int]:
    violations: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            violations.extend(
                node.lineno for alias in node.names if alias.name == _PRIVATE_NAME
            )
        elif isinstance(node, ast.Attribute) and node.attr == _PRIVATE_NAME:
            violations.append(node.lineno)
        elif isinstance(node, ast.Name) and node.id == _PRIVATE_NAME:
            violations.append(node.lineno)
        # A COPIED regex literal (review finding). Importing the private name
        # was the only thing the guard could see, yet the threat its own
        # docstring names -- "no call site can hand-roll its own redaction
        # against a COPY of this vocabulary" -- is served far more naturally
        # by pasting `re.compile(r"ghp_[A-Za-z0-9]{36,}")` into another
        # module, which was completely invisible. The signature is a known
        # token prefix immediately followed by a regex character class, so
        # ordinary prose mentioning `ghp_` or a test fixture containing a
        # literal token does not trip it.
        elif (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and _COPIED_TOKEN_REGEX.search(node.value)
        ):
            violations.append(node.lineno)
    return sorted(violations)


# --- guard (1) --------------------------------------------------------------


def test_port_scan_surface_is_not_empty():
    modules = _port_modules()
    assert modules, "AD-34 egress-registry guard found no port modules to scan"
    assert _all_protocol_class_names(), "no Protocol subclasses found under ports/"


def test_every_protocol_under_ports_has_an_egress_classification():
    missing = [name for name in _all_protocol_class_names() if name not in EGRESS_PORTS]
    assert not missing, (
        f"Protocol class(es) {missing} defined under ports/ have no EGRESS_PORTS "
        "entry -- every port must be classified egress: true|false (AD-34)"
    )


# --- guard (2) ---------------------------------------------------------------


@pytest.mark.parametrize("module_path", _port_modules(), ids=_module_id)
def test_egress_classified_ports_accept_no_bare_str_param(module_path: Path):
    for cls in _protocol_classes(_parse(module_path)):
        if not EGRESS_PORTS.get(cls.name, False):
            continue
        violations = _bare_str_param_violations(cls)
        assert not violations, (
            f"egress port {cls.name!r} in {module_path.name} has bare str-typed "
            f"method parameter(s) {violations} -- egress ports must accept only "
            "Redacted (AD-34)"
        )


# --- guard (3) ---------------------------------------------------------------


def test_scan_surface_is_not_empty():
    modules = _non_egress_modules()
    assert modules, "AD-34 token-shape-pattern guard found no modules to scan"
    names = {path.name for path in _package_modules()}
    assert "egress.py" in names, "core/egress.py missing from the installed package"


@pytest.mark.parametrize("module_path", _non_egress_modules(), ids=_module_id)
def test_no_token_shape_pattern_reference_outside_egress(module_path: Path):
    violations = _token_shape_pattern_references(_parse(module_path))
    assert not violations, (
        f"{module_path.name} references the private {_PRIVATE_NAME} at line(s) "
        f"{violations} -- only core/egress.py may redact; no other module may "
        "hand-roll its own token-shape scanning (AD-34)"
    )


# --- detector self-tests: non-vacuous proof ----------------------------------


def test_guard_is_alive_synthetic_missing_classification_fires():
    synthetic = (
        "from typing import Protocol\n\n"
        "class FifthPort(Protocol):\n"
        "    def do(self) -> None: ...\n"
    )
    tree = ast.parse(synthetic)
    names = [cls.name for cls in _protocol_classes(tree)]
    assert names == ["FifthPort"]
    assert "FifthPort" not in EGRESS_PORTS


def test_guard_is_alive_synthetic_bare_str_param_on_egress_port_fires():
    # `path` is annotated `Path` (not left bare) so this test isolates the
    # ORIGINAL bare-`str`-annotation case; unannotated/Optional[str]/`str |
    # None` each get their own dedicated self-test below.
    synthetic = (
        "from typing import Protocol\n"
        "from pathlib import Path\n\n"
        "class RecordPort(Protocol):\n"
        "    def write_redacted_atomic(self, path: Path, content: str) -> None: ...\n"
    )
    cls = _protocol_classes(ast.parse(synthetic))[0]
    assert EGRESS_PORTS["RecordPort"] is True
    assert _bare_str_param_violations(cls) == ["RecordPort.write_redacted_atomic(content)"]


def test_guard_does_not_fire_on_a_typed_sequence_param():
    """Regression for the guard's own false positive: a `Sequence[str]`
    parameter is an ast.Subscript, not a bare ast.Name -- must not fire."""
    synthetic = (
        "from typing import Protocol\n"
        "from collections.abc import Sequence\n\n"
        "class SomePort(Protocol):\n"
        "    def run(self, argv: Sequence[str]) -> None: ...\n"
    )
    cls = _protocol_classes(ast.parse(synthetic))[0]
    assert _bare_str_param_violations(cls) == []


def test_guard_is_alive_synthetic_unannotated_param_on_egress_port_fires():
    """Review finding: an unannotated parameter accepts a bare str just as
    readily as an explicit `str` annotation -- must fire too."""
    synthetic = (
        "from typing import Protocol\n\n"
        "class RecordPort(Protocol):\n"
        "    def write_redacted_atomic(self, path, payload) -> None: ...\n"
    )
    cls = _protocol_classes(ast.parse(synthetic))[0]
    assert _bare_str_param_violations(cls) == [
        "RecordPort.write_redacted_atomic(path)",
        "RecordPort.write_redacted_atomic(payload)",
    ]


def test_guard_is_alive_synthetic_optional_str_param_on_egress_port_fires():
    synthetic = (
        "from typing import Protocol, Optional\n\n"
        "class RecordPort(Protocol):\n"
        "    def write_redacted_atomic(self, path, payload: Optional[str]) -> None: ...\n"
    )
    cls = _protocol_classes(ast.parse(synthetic))[0]
    violations = _bare_str_param_violations(cls)
    assert "RecordPort.write_redacted_atomic(payload)" in violations


def test_guard_is_alive_synthetic_str_union_none_param_on_egress_port_fires():
    synthetic = (
        "from typing import Protocol\n\n"
        "class RecordPort(Protocol):\n"
        "    def write_redacted_atomic(self, path, payload: str | None) -> None: ...\n"
    )
    cls = _protocol_classes(ast.parse(synthetic))[0]
    violations = _bare_str_param_violations(cls)
    assert "RecordPort.write_redacted_atomic(payload)" in violations


def test_guard_is_alive_synthetic_async_method_bare_str_param_fires():
    """Review finding, verified live: the guard iterated only
    `ast.FunctionDef`, so an `async def` egress method with a bare-str
    parameter produced ZERO violations -- invisible to the one structural
    guarantee AD-34 rests on."""
    synthetic = (
        "from typing import Protocol\n\n"
        "class RecordPort(Protocol):\n"
        "    async def write_redacted_atomic(self, path, payload: str) -> None: ...\n"
    )
    cls = _protocol_classes(ast.parse(synthetic))[0]
    assert _bare_str_param_violations(cls) == [
        "RecordPort.write_redacted_atomic(path)",
        "RecordPort.write_redacted_atomic(payload)",
    ]


@pytest.mark.parametrize("annotation", ["Any", "object", "typing.Any"])
def test_guard_is_alive_synthetic_any_or_object_param_fires(annotation):
    """Review finding, verified live: `Any`/`object` accept a bare str as
    readily as `str` does, yet produced zero violations -- an escape hatch
    around the egress type boundary."""
    synthetic = (
        "import typing\n"
        "from typing import Protocol, Any\n"
        "from pathlib import Path\n\n"
        "class RecordPort(Protocol):\n"
        f"    def write_redacted_atomic(self, path: Path, payload: {annotation}) -> None: ...\n"
    )
    cls = _protocol_classes(ast.parse(synthetic))[0]
    assert _bare_str_param_violations(cls) == ["RecordPort.write_redacted_atomic(payload)"]


def test_port_scan_is_recursive(tmp_path):
    """Review finding: `_port_modules()` used a non-recursive glob while this
    same module's guard-(3) surface used rglob, so a Protocol in a ports/
    subpackage escaped guards (1) and (2) entirely.

    Behavioral, not textual (second review finding): this test used to assert
    `"rglob" in inspect.getsource(_port_modules)`, which passes for ANY
    implementation merely MENTIONING the string -- including a
    `# was rglob, now glob` comment above a non-recursive call -- so the
    regression it names was not actually guarded."""
    (tmp_path / "top.py").write_text("", encoding="utf-8")
    nested = tmp_path / "sub"
    nested.mkdir()
    (nested / "deep.py").write_text("", encoding="utf-8")

    found = {p.name for p in _port_modules(root=tmp_path)}
    assert found == {"top.py", "deep.py"}


def test_port_scan_includes_package_init(tmp_path):
    """Review finding, verified live by both reviewers: `__init__.py` was
    filtered out by name, so a Protocol declared directly in
    `ports/__init__.py` -- exactly where the Story-1.1 registry placeholder
    lived -- escaped guards (1) and (2) entirely while producing violations
    when parsed directly."""
    (tmp_path / "__init__.py").write_text(
        "from typing import Protocol\n\n"
        "class RecordPort(Protocol):\n"
        "    def write_redacted_atomic(self, path, payload: str) -> None: ...\n",
        encoding="utf-8",
    )
    modules = _port_modules(root=tmp_path)
    assert [p.name for p in modules] == ["__init__.py"]

    cls = _protocol_classes(_parse(modules[0]))[0]
    assert _bare_str_param_violations(cls) == [
        "RecordPort.write_redacted_atomic(path)",
        "RecordPort.write_redacted_atomic(payload)",
    ]


@pytest.mark.parametrize("annotation", ['"str"', '"str | None"', '"Optional[str]"'])
def test_guard_is_alive_synthetic_quoted_str_annotation_fires(annotation):
    """Review finding, verified live: the constant check compared the
    annotation to the literal `"str"`, so the quoted UNION forms produced
    zero violations while their unquoted equivalents fired correctly."""
    synthetic = (
        "from typing import Protocol, Optional\n"
        "from pathlib import Path\n\n"
        "class RecordPort(Protocol):\n"
        f"    def write_redacted_atomic(self, path: Path, payload: {annotation}) -> None: ...\n"
    )
    cls = _protocol_classes(ast.parse(synthetic))[0]
    assert _bare_str_param_violations(cls) == ["RecordPort.write_redacted_atomic(payload)"]


def test_guard_does_not_fire_on_a_quoted_non_str_annotation():
    """The real `ports/record.py` uses `from __future__ import annotations`,
    so a stringified `Redacted` must stay clean."""
    synthetic = (
        "from typing import Protocol\n\n"
        "class RecordPort(Protocol):\n"
        '    def write_redacted_atomic(self, path: "Path", payload: "Redacted") -> None: ...\n'
    )
    cls = _protocol_classes(ast.parse(synthetic))[0]
    assert _bare_str_param_violations(cls) == []


def test_guard_is_alive_synthetic_copied_token_regex_fires():
    """Review finding: guard (3) recognized only the literal
    `_TOKEN_SHAPE_PATTERNS` name, so the most natural way to hand-roll
    redaction -- pasting a COPY of the regex vocabulary into another module
    -- was completely invisible to the guard whose docstring names exactly
    that threat."""
    copied = 'import re\nP = re.compile(r"ghp_[A-Za-z0-9]{36,}")\n'
    assert _token_shape_pattern_references(ast.parse(copied)) == [2]

    for prefix in ("github_pat_", "AKIA", "sk-"):
        source = f'P = "{prefix}[A-Za-z0-9]+"\n'
        assert _token_shape_pattern_references(ast.parse(source)) == [1], prefix


def test_copied_token_regex_guard_does_not_fire_on_ordinary_text():
    """It must key on a token prefix followed by a regex CHARACTER CLASS --
    prose mentioning a prefix, or a literal token in a fixture, is not a
    hand-rolled vocabulary."""
    benign = (
        'DOC = "a GitHub PAT starts with ghp_ and an AWS key with AKIA"\n'
        'FIXTURE = "ghp_" + "a" * 36\n'
        'SELECTOR = "pytest -k sk-some-selector"\n'
    )
    assert _token_shape_pattern_references(ast.parse(benign)) == []


def test_guard_does_not_fire_on_the_real_record_port():
    """The real, shipped `RecordPort.write_redacted_atomic(path: Path,
    payload: Redacted)` must produce zero violations -- neither parameter is
    str-shaped."""
    from pyforge.marshal.ports import record as record_module

    module_path = Path(record_module.__file__)
    cls = _protocol_classes(_parse(module_path))[0]
    assert _bare_str_param_violations(cls) == []


def test_guard_is_alive_synthetic_token_shape_reference_fires():
    import_form = "from pyforge.marshal.core.egress import _TOKEN_SHAPE_PATTERNS\n"
    assert _token_shape_pattern_references(ast.parse(import_form)) == [1]

    attribute_form = "import pyforge.marshal.core.egress as egress\nx = egress._TOKEN_SHAPE_PATTERNS\n"
    assert _token_shape_pattern_references(ast.parse(attribute_form)) == [2]

    # An aliased import is still caught -- the ImportFrom node itself names
    # `_TOKEN_SHAPE_PATTERNS` in `alias.name` regardless of `asname` -- even
    # though the guard cannot then also track the alias's later bare-name
    # USES (a stated bound: it recognizes the literal token, not full
    # dataflow through an alias).
    aliased_import_form = "from pyforge.marshal.core.egress import _TOKEN_SHAPE_PATTERNS as X\nx = X\n"
    assert _token_shape_pattern_references(ast.parse(aliased_import_form)) == [1]


def test_real_record_port_is_classified_egress_true():
    assert EGRESS_PORTS["RecordPort"] is True


def test_egress_ports_registry_has_exactly_the_five_known_ports():
    assert set(EGRESS_PORTS.keys()) == {
        "ProcessPort",
        "FsPort",
        "HarnessPort",
        "VcsPort",
        "RecordPort",
    }
