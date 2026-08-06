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
unquoted -- a string annotation is parsed and re-checked), ``Annotated[str,
...]``, and the ``Any``/``object`` escape hatches, on positional, keyword-only,
``*args`` and ``**kwargs`` parameters, across both ``def`` and ``async def``
methods, including methods nested under an ``if`` (e.g. ``if TYPE_CHECKING:``)
and methods INHERITED from a base class defined in the SAME module. It does
NOT recognize a ``str`` buried inside a container type (``list[str]``), an
annotation reached only through a type alias, or a method inherited from a
base class imported from another module; none of those shapes appear on any
port method in this package today (no port inherits at all).

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
# `_token_shape_pattern_references`. Tracks `_TOKEN_SHAPE_PATTERNS`'s full
# prefix set, including the `gh[pousr]_`/`ASIA` spellings a review finding
# added -- a copy of a prefix this list omitted would be invisible to the
# guard whose whole purpose is catching copies.
_COPIED_TOKEN_REGEX = re.compile(r"(?:gh[pousr]_|github_pat_|AKIA|ASIA|sk-)\[")


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


def _all_protocol_class_names(root: Path | None = None) -> list[str]:
    # `root` is injectable for the same reason `_port_modules`'s is: so
    # guard (1)'s "guard is alive" self-test can run the guard's OWN
    # scan-and-assert path over a synthetic tree, rather than assert around it
    # (follow-up review finding -- the same "asserts around the guard rather
    # than through it" shape a previous pass already patched out of
    # `test_port_scan_is_recursive`).
    names: list[str] = []
    for module_path in _port_modules(root):
        names.extend(cls.name for cls in _protocol_classes(_parse(module_path)))
    return names


def _unclassified_ports(root: Path | None = None) -> list[str]:
    """Guard (1) itself, extracted so both the real test and its synthetic
    self-test exercise the identical code path."""
    return [name for name in _all_protocol_class_names(root) if name not in EGRESS_PORTS]


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
        if base_name == "Annotated":
            # `Annotated[str, ...]` IS a `str` at runtime -- the metadata is
            # inert to the type checker's assignability rule (follow-up
            # review finding, verified live: it produced zero violations).
            # Only the FIRST element is the type.
            elements = (
                annotation.slice.elts
                if isinstance(annotation.slice, ast.Tuple)
                else [annotation.slice]
            )
            return bool(elements) and _is_bare_str_annotation(elements[0])
    return False


def _method_defs(body: list[ast.stmt]) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Every method in a class body, descending into `if` blocks (follow-up
    review finding, verified live: a method declared under `if TYPE_CHECKING:`
    -- an ordinary way to spell a Protocol's surface -- was invisible to the
    guard, since the original iterated `cls.body` directly)."""
    methods: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
    for item in body:
        # AsyncFunctionDef too (follow-up review finding, verified live: an
        # `async def` egress method with a bare-str parameter produced zero
        # violations -- the guard did not look at async methods at all).
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            methods.append(item)
        elif isinstance(item, ast.If):
            methods.extend(_method_defs(item.body))
            methods.extend(_method_defs(item.orelse))
    return methods


def _bare_str_param_violations(
    cls: ast.ClassDef, class_map: dict[str, ast.ClassDef] | None = None
) -> list[str]:
    """Violations on ``cls``, INCLUDING methods inherited from a base class
    defined in the same module (follow-up review finding, verified live: a
    bare-`str` method inherited from a shared base Protocol produced zero
    violations, since it never appears in the subclass's own body). Bound:
    only SAME-MODULE bases are resolved -- `class_map` is built per module,
    so a base imported from elsewhere is still out of scope; no port inherits
    at all today."""
    violations: list[str] = []
    bodies = [cls.body]
    if class_map:
        for base in cls.bases:
            base_name = base.id if isinstance(base, ast.Name) else getattr(base, "attr", None)
            base_cls = class_map.get(base_name) if base_name else None
            if base_cls is not None and base_cls is not cls:
                bodies.append(base_cls.body)
    for body in bodies:
        for item in _method_defs(body):
            # `vararg`/`kwarg` too: `*parts: str` and `**kw: str` each accept
            # a bare string as readily as a positional one (follow-up review
            # finding -- previously a STATED bound, now covered).
            params = [
                *item.args.posonlyargs,
                *item.args.args,
                *item.args.kwonlyargs,
                *([item.args.vararg] if item.args.vararg else []),
                *([item.args.kwarg] if item.args.kwarg else []),
            ]
            for param in params:
                if param.arg == "self":
                    continue
                if _is_bare_str_annotation(param.annotation):
                    entry = f"{cls.name}.{item.name}({param.arg})"
                    if entry not in violations:
                        violations.append(entry)
    return violations


# --- guard (3): private token-shape-pattern reference detection -------------


def _token_shape_pattern_references(tree: ast.Module) -> list[tuple[int, str]]:
    """``(lineno, cause)`` pairs. The CAUSE is carried, not just the line
    (follow-up review finding): the two branches are different defects, and a
    single shared message told a module that pasted
    ``re.compile(r"ghp_[A-Za-z0-9]{36,}")`` -- and never mentions
    ``_TOKEN_SHAPE_PATTERNS`` at all -- that it "references
    ``_TOKEN_SHAPE_PATTERNS``", sending the reader to grep for a symbol its
    source does not contain."""
    violations: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            violations.extend(
                (node.lineno, f"references {_PRIVATE_NAME}")
                for alias in node.names
                if alias.name == _PRIVATE_NAME
            )
        elif isinstance(node, ast.Attribute) and node.attr == _PRIVATE_NAME:
            violations.append((node.lineno, f"references {_PRIVATE_NAME}"))
        elif isinstance(node, ast.Name) and node.id == _PRIVATE_NAME:
            violations.append((node.lineno, f"references {_PRIVATE_NAME}"))
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
            violations.append(
                (node.lineno, "embeds a hand-rolled COPY of the token-shape vocabulary")
            )
    return sorted(violations)


# --- guard (1) --------------------------------------------------------------


def test_port_scan_surface_is_not_empty():
    modules = _port_modules()
    assert modules, "AD-34 egress-registry guard found no port modules to scan"
    assert _all_protocol_class_names(), "no Protocol subclasses found under ports/"


def test_every_protocol_under_ports_has_an_egress_classification():
    missing = _unclassified_ports()
    assert not missing, (
        f"Protocol class(es) {missing} defined under ports/ have no EGRESS_PORTS "
        "entry -- every port must be classified egress: true|false (AD-34)"
    )


# --- guard (2) ---------------------------------------------------------------


@pytest.mark.parametrize("module_path", _port_modules(), ids=_module_id)
def test_egress_classified_ports_accept_no_bare_str_param(module_path: Path):
    tree = _parse(module_path)
    class_map = {node.name: node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}
    for cls in _protocol_classes(tree):
        if not EGRESS_PORTS.get(cls.name, False):
            continue
        violations = _bare_str_param_violations(cls, class_map)
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
        f"{module_path.name} "
        + "; ".join(f"{cause} at line {lineno}" for lineno, cause in violations)
        + " -- only core/egress.py may redact; no other module may hand-roll its "
        "own token-shape scanning (AD-34)"
    )


# --- detector self-tests: non-vacuous proof ----------------------------------


def test_guard_is_alive_synthetic_missing_classification_fires(tmp_path):
    """Runs guard (1)'s OWN scan-and-assert path (`_unclassified_ports`) over
    a synthetic ports tree (follow-up review finding: this test used to assert
    only that `_protocol_classes` finds the class and that the name is absent
    from EGRESS_PORTS -- it never exercised the guard, so it would have stayed
    green if the real test's surface stopped being fed by
    `_all_protocol_class_names`)."""
    (tmp_path / "fifth.py").write_text(
        "from typing import Protocol\n\n"
        "class FifthPort(Protocol):\n"
        "    def do(self) -> None: ...\n",
        encoding="utf-8",
    )
    assert _unclassified_ports(root=tmp_path) == ["FifthPort"]
    # ...and stays silent once the port IS classified -- otherwise the guard
    # would be "always fires", which is just as vacuous as "never fires".
    (tmp_path / "fifth.py").write_text(
        "from typing import Protocol\n\n"
        "class RecordPort(Protocol):\n"
        "    def do(self) -> None: ...\n",
        encoding="utf-8",
    )
    assert _unclassified_ports(root=tmp_path) == []


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


@pytest.mark.parametrize(
    "annotation", ["Annotated[str, 'meta']", "Annotated[str | None, 1]", "typing.Annotated[str, 1]"]
)
def test_guard_is_alive_synthetic_annotated_str_param_fires(annotation):
    """Review finding, verified live: `Annotated[str, ...]` IS a `str` at
    runtime and to a type checker, yet produced zero violations -- the same
    escape-hatch class as the `Any`/`object` gap a previous pass closed."""
    synthetic = (
        "import typing\n"
        "from typing import Protocol, Annotated\n"
        "from pathlib import Path\n\n"
        "class RecordPort(Protocol):\n"
        f"    def write_redacted_atomic(self, path: Path, payload: {annotation}) -> None: ...\n"
    )
    cls = _protocol_classes(ast.parse(synthetic))[0]
    assert _bare_str_param_violations(cls) == ["RecordPort.write_redacted_atomic(payload)"]


def test_guard_does_not_fire_on_annotated_non_str():
    """Only the FIRST element of `Annotated[...]` is the type -- metadata
    that happens to mention `str` must not trip the guard."""
    synthetic = (
        "from typing import Protocol, Annotated\n\n"
        "class RecordPort(Protocol):\n"
        "    def write(self, path, payload: Annotated[Redacted, str]) -> None: ...\n"
    )
    cls = _protocol_classes(ast.parse(synthetic))[0]
    assert _bare_str_param_violations(cls) == ["RecordPort.write(path)"]


@pytest.mark.parametrize(
    ("signature", "expected"),
    [
        ("self, *parts: str", "RecordPort.write_redacted_atomic(parts)"),
        ("self, **kw: str", "RecordPort.write_redacted_atomic(kw)"),
    ],
)
def test_guard_is_alive_synthetic_varargs_bare_str_fires(signature, expected):
    """Review finding: `*args`/`**kwargs` were a STATED bound, but each
    accepts a bare string exactly as readily as a positional parameter."""
    synthetic = (
        "from typing import Protocol\n\n"
        "class RecordPort(Protocol):\n"
        f"    def write_redacted_atomic({signature}) -> None: ...\n"
    )
    cls = _protocol_classes(ast.parse(synthetic))[0]
    assert _bare_str_param_violations(cls) == [expected]


def test_guard_is_alive_synthetic_method_under_type_checking_fires():
    """Review finding, verified live: the guard iterated `cls.body` directly,
    so a method declared under `if TYPE_CHECKING:` -- an ordinary way to
    spell a Protocol's surface -- was invisible."""
    synthetic = (
        "from typing import Protocol, TYPE_CHECKING\n\n"
        "class RecordPort(Protocol):\n"
        "    if TYPE_CHECKING:\n"
        "        def write_redacted_atomic(self, payload: str) -> None: ...\n"
    )
    cls = _protocol_classes(ast.parse(synthetic))[0]
    assert _bare_str_param_violations(cls) == ["RecordPort.write_redacted_atomic(payload)"]


def test_guard_is_alive_synthetic_inherited_bare_str_method_fires():
    """Review finding, verified live: a bare-`str` method inherited from a
    shared base Protocol never appears in the subclass's own body, so it
    produced zero violations. Same-module bases are now resolved (a
    cross-module base remains a stated bound -- no port inherits today)."""
    synthetic = (
        "from typing import Protocol\n\n"
        "class BaseWriter(Protocol):\n"
        "    def write_redacted_atomic(self, payload: str) -> None: ...\n\n"
        "class RecordPort(BaseWriter, Protocol):\n"
        "    def other(self) -> None: ...\n"
    )
    tree = ast.parse(synthetic)
    class_map = {node.name: node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}
    cls = next(c for c in _protocol_classes(tree) if c.name == "RecordPort")
    assert _bare_str_param_violations(cls, class_map) == [
        "RecordPort.write_redacted_atomic(payload)"
    ]
    # ...and stays silent when the inherited method is correctly typed.
    clean = synthetic.replace("payload: str", "payload: Redacted")
    clean_tree = ast.parse(clean)
    clean_map = {n.name: n for n in ast.walk(clean_tree) if isinstance(n, ast.ClassDef)}
    clean_cls = next(c for c in _protocol_classes(clean_tree) if c.name == "RecordPort")
    assert _bare_str_param_violations(clean_cls, clean_map) == []


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
    assert _token_shape_pattern_references(ast.parse(copied)) == [
        (2, "embeds a hand-rolled COPY of the token-shape vocabulary")
    ]

    # Every prefix in the real vocabulary, incl. the `gh[pousr]_`/`ASIA`
    # spellings a review finding added -- a copy of an omitted prefix would be
    # invisible to the guard that exists to catch copies.
    for prefix in ("ghs_", "gho_", "ghu_", "ghr_", "github_pat_", "AKIA", "ASIA", "sk-"):
        source = f'P = "{prefix}[A-Za-z0-9]+"\n'
        assert _token_shape_pattern_references(ast.parse(source)) == [
            (1, "embeds a hand-rolled COPY of the token-shape vocabulary")
        ], prefix


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
    reference = f"references {_PRIVATE_NAME}"
    import_form = "from pyforge.marshal.core.egress import _TOKEN_SHAPE_PATTERNS\n"
    assert _token_shape_pattern_references(ast.parse(import_form)) == [(1, reference)]

    attribute_form = "import pyforge.marshal.core.egress as egress\nx = egress._TOKEN_SHAPE_PATTERNS\n"
    assert _token_shape_pattern_references(ast.parse(attribute_form)) == [(2, reference)]

    # An aliased import is still caught -- the ImportFrom node itself names
    # `_TOKEN_SHAPE_PATTERNS` in `alias.name` regardless of `asname` -- even
    # though the guard cannot then also track the alias's later bare-name
    # USES (a stated bound: it recognizes the literal token, not full
    # dataflow through an alias).
    aliased_import_form = "from pyforge.marshal.core.egress import _TOKEN_SHAPE_PATTERNS as X\nx = X\n"
    assert _token_shape_pattern_references(ast.parse(aliased_import_form)) == [(1, reference)]


def test_real_record_port_is_classified_egress_true():
    assert EGRESS_PORTS["RecordPort"] is True


def test_egress_ports_registry_has_exactly_the_nine_known_ports():
    assert set(EGRESS_PORTS.keys()) == {
        "ProcessPort",
        "FsPort",
        "HarnessPort",
        "VcsPort",
        "RecordPort",
        "ClockPort",
        "SessionObserverPort",
        "NotifyPort",
        "ForgePort",
    }


def test_notify_port_is_classified_egress_true():
    assert EGRESS_PORTS["NotifyPort"] is True


def test_forge_port_is_classified_egress_true():
    assert EGRESS_PORTS["ForgePort"] is True


def test_guard_does_not_fire_on_the_real_notify_port():
    """The real, shipped ``NotifyPort`` (``notify_file(path: Path, payload:
    Redacted)``, ``notify_desktop(payload: Redacted)``) must produce zero
    violations -- no parameter on either method is str-shaped (Story 3.7's
    own reason for NOT literally mirroring the intent-contract's
    ``notify_desktop(title: str, payload: Redacted)`` wording -- see that
    port's own module docstring)."""
    from pyforge.marshal.ports import notify as notify_module

    module_path = Path(notify_module.__file__)
    cls = _protocol_classes(_parse(module_path))[0]
    assert _bare_str_param_violations(cls) == []


def test_guard_does_not_fire_on_the_real_forge_port():
    """The real, shipped ``ForgePort`` -- every non-``Redacted`` identifier
    parameter (``repo``/``head_branch``/``base``/``head``/``ref``/
    ``check_name``) wrapped in ``ForgeRef``, ``number`` an ``int``,
    ``labels`` a ``tuple[str, ...]`` -- must produce zero violations (Story
    4.4's own reason for NOT literally mirroring the intent-contract's bare
    ``str`` wording -- see that port's own module docstring)."""
    from pyforge.marshal.ports import forge as forge_module

    module_path = Path(forge_module.__file__)
    cls = _protocol_classes(_parse(module_path))[0]
    assert _bare_str_param_violations(cls) == []
