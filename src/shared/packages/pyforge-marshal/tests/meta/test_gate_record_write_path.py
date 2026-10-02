"""Meta test -- a gate record is written only through ``RecordPort.write_redacted_atomic`` (Story 82.9,
DW-FU-2-6-4, AD-34).

``LocalFs`` serves both ``RecordPort.write_redacted_atomic(path, Redacted)`` and ``FsPort.write_text_atomic(path,
str)`` on the same sink with the same mechanics, so a call site could write an unredacted gate record in one
line with no test failing -- the AD-34 boundary was one method call wide. ``FsPort`` is NOT classified egress
(its general writes are not records), so the registry cannot close this; the file NAME can. It is one constant,
``core.egress.GATE_RECORD_FILENAME``, and this scan fails

(a) any module other than ``core/egress.py`` that spells the literal ``"gate-record.json"`` (a docstring is
    prose, not a path, and is skipped) -- the name is reachable only through the constant, so (b) can see it;
(b) any call that passes the constant, or a name bound from it, to a writer other than
    ``write_redacted_atomic`` -- ``FsPort.write_text_atomic``, ``Path.write_text``/``write_bytes``, ``open``,
    ``atomic_write_text`` and the like, whether the name sits in an argument or in the receiver.

Bounds (stated, not aspirational): a best-effort STATIC check like its AD-34 siblings. Taint is tracked per
module through assignments (``path = directory / GATE_RECORD_FILENAME``), an ``import ... as`` alias and
a ``module.GATE_RECORD_FILENAME`` attribute; it does not follow a value through a function's return, a
container, ``getattr`` or another module's re-export. It proves the writer's NAME, not that the payload is
the output of ``to_redacted`` -- that half is ``Redacted``'s type boundary (``RecordPort`` accepts nothing
else).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

import pyforge.marshal
from pyforge.marshal.core.egress import GATE_RECORD_FILENAME

_PACKAGE_FILE = pyforge.marshal.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
PACKAGE_DIR = Path(_PACKAGE_FILE).resolve().parent
_EGRESS_MODULE = PACKAGE_DIR / "core" / "egress.py"

_CONSTANT = "GATE_RECORD_FILENAME"
_ALLOWED_WRITER = "write_redacted_atomic"
#: Callee names that write bytes somewhere. `write_redacted_atomic` is the one allowed to receive the record's path.
_WRITER_NAMES = frozenset(
    {
        "open",
        "atomic_write_text",
        "atomic_write_bytes",
        "copy_file",
        "copy",
        "copy2",
        "copyfile",
        "move",
        "replace",
        "rename",
        "touch",
        "dump",
    }
)


def _is_writer(name: str) -> bool:
    return name != _ALLOWED_WRITER and (name.startswith("write") or name in _WRITER_NAMES)


def _callee_name(call: ast.Call) -> str:
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _docstring_nodes(tree: ast.Module) -> set[int]:
    """``id`` of every docstring ``Constant`` -- prose, not a path."""
    found: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                if isinstance(body[0].value.value, str):
                    found.add(id(body[0].value))
    return found


def _spells_the_file_name(tree: ast.Module) -> list[int]:
    """Lines of a non-docstring string constant whose final path component is the record's file name."""
    docstrings = _docstring_nodes(tree)
    lines: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings:
            if node.value.replace("\\", "/").rsplit("/", 1)[-1] == GATE_RECORD_FILENAME:
                lines.append(node.lineno)
    return sorted(lines)


def _tainted_names(tree: ast.Module) -> set[str]:
    """Names bound (directly or through assignments) from ``GATE_RECORD_FILENAME``."""
    tainted: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            tainted.update(alias.asname or alias.name for alias in node.names if alias.name == _CONSTANT)

    def mentions(expr: ast.AST) -> bool:
        # A READ of the record (`path.read_text()`) yields its content, not its name: opaque, never tainted.
        if isinstance(expr, ast.Call) and _callee_name(expr).startswith("read"):
            return False
        if isinstance(expr, ast.Name):
            return expr.id == _CONSTANT or expr.id in tainted
        if isinstance(expr, ast.Attribute) and expr.attr == _CONSTANT:
            return True
        return any(mentions(child) for child in ast.iter_child_nodes(expr))

    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                targets, value = node.targets, node.value
            elif isinstance(node, (ast.AnnAssign, ast.NamedExpr)) and node.value is not None:
                targets, value = [node.target], node.value
            else:
                continue
            if not mentions(value):
                continue
            for target in targets:
                for sub in ast.walk(target):
                    if isinstance(sub, ast.Name) and sub.id not in tainted:
                        tainted.add(sub.id)
                        changed = True
    return tainted


def _writes_through_the_wrong_writer(tree: ast.Module) -> list[str]:
    """``line:callee`` for a writer other than ``write_redacted_atomic`` handed the record's file name."""
    tainted = _tainted_names(tree)

    def carries(expr: ast.AST) -> bool:
        for sub in ast.walk(expr):
            if isinstance(sub, ast.Name) and (sub.id == _CONSTANT or sub.id in tainted):
                return True
            if isinstance(sub, ast.Attribute) and sub.attr == _CONSTANT:
                return True
        return False

    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _callee_name(node)
        if not _is_writer(name):
            continue
        operands: list[ast.AST] = [*node.args, *(kw.value for kw in node.keywords)]
        if isinstance(node.func, ast.Attribute):
            operands.append(node.func.value)  # `(d / GATE_RECORD_FILENAME).write_text(...)`, `path.write_text(...)`
        if any(carries(operand) for operand in operands):
            found.append(f"{node.lineno}:{name}")
    return sorted(found)


def _calls_the_allowed_writer_with_the_file_name(tree: ast.Module) -> bool:
    tainted = _tainted_names(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _callee_name(node) == _ALLOWED_WRITER and node.args:
            for sub in ast.walk(node.args[0]):
                if isinstance(sub, ast.Name) and (sub.id == _CONSTANT or sub.id in tainted):
                    return True
    return False


def _modules() -> list[Path]:
    return sorted(path for path in PACKAGE_DIR.rglob("*.py") if path != _EGRESS_MODULE)


def _module_id(path: Path) -> str:
    return str(path.relative_to(PACKAGE_DIR))


# --- the real tree ------------------------------------------------------------------------------------------------


def test_the_constant_is_defined_in_egress_and_the_scan_surface_is_not_empty():
    assert GATE_RECORD_FILENAME == "gate-record.json"
    assert _modules(), "no modules to scan"
    egress_tree = ast.parse(_EGRESS_MODULE.read_text(encoding="utf-8"))
    assert len(_spells_the_file_name(egress_tree)) == 1, "core/egress.py spells the name exactly once, as the constant"


@pytest.mark.parametrize("module_path", _modules(), ids=_module_id)
def test_no_module_spells_the_record_file_name_or_writes_it_through_a_plain_writer(module_path: Path):
    tree = ast.parse(module_path.read_text(encoding="utf-8"), filename=str(module_path))
    spelled = _spells_the_file_name(tree)
    assert not spelled, (
        f"{_module_id(module_path)} spells {GATE_RECORD_FILENAME!r} at line(s) {spelled} -- the name lives in "
        "core/egress.py as GATE_RECORD_FILENAME so the write-path scan can see it (AD-34)"
    )
    wrong = _writes_through_the_wrong_writer(tree)
    assert not wrong, (
        f"{_module_id(module_path)} hands the gate record's file name to {wrong} -- a gate record is written "
        "ONLY through RecordPort.write_redacted_atomic (AD-34: FsPort.write_text_atomic takes a bare str)"
    )


def test_the_real_gate_command_writes_its_record_through_the_allowed_writer():
    """The guard is alive over the real tree: `cli/gate.py` is the one caller, and it uses the allowed writer."""
    tree = ast.parse((PACKAGE_DIR / "cli" / "gate.py").read_text(encoding="utf-8"))
    assert _calls_the_allowed_writer_with_the_file_name(tree)
    assert _writes_through_the_wrong_writer(tree) == []


# --- detector self-tests: non-vacuous proof ------------------------------------------------------------------------


def test_guard_is_alive_fs_port_write_text_atomic_with_the_constant_fails():
    source = "FsPort.write_text_atomic(directory / GATE_RECORD_FILENAME, json.dumps(record))\n"
    assert _writes_through_the_wrong_writer(ast.parse(source)) == ["1:write_text_atomic"]


def test_guard_is_alive_a_name_bound_from_the_constant_is_followed():
    source = (
        "from pyforge.marshal.core.egress import GATE_RECORD_FILENAME as NAME\n"
        "path = directory / NAME\n"
        "target = path\n"
        "fs.write_text_atomic(target, text)\n"
    )
    assert _writes_through_the_wrong_writer(ast.parse(source)) == ["4:write_text_atomic"]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("(d / GATE_RECORD_FILENAME).write_text(x)\n", ["1:write_text"]),
        ("p = d / GATE_RECORD_FILENAME\np.write_bytes(b'')\n", ["2:write_bytes"]),
        ("p = egress.GATE_RECORD_FILENAME\nopen(p, 'w')\n", ["2:open"]),
        ("atomic_write_text(d / GATE_RECORD_FILENAME, text)\n", ["1:atomic_write_text"]),
        ("shutil.copy(src, d / GATE_RECORD_FILENAME)\n", ["1:copy"]),
    ],
)
def test_guard_is_alive_every_plain_writer_spelling_fails(source, expected):
    assert _writes_through_the_wrong_writer(ast.parse(source)) == expected


def test_guard_stays_silent_on_the_allowed_writer_and_on_reads_of_the_name():
    source = (
        "path = directory / GATE_RECORD_FILENAME\n"
        "record.write_redacted_atomic(path, to_redacted(body))\n"
        "info = {'path': str(path)}\n"
        "text = path.read_text()\n"
        "fs.write_text_atomic(directory / 'notes.txt', text)\n"
    )
    tree = ast.parse(source)
    assert _writes_through_the_wrong_writer(tree) == []
    assert _calls_the_allowed_writer_with_the_file_name(tree)


def test_guard_is_alive_spelling_the_literal_fails_but_a_docstring_may_name_it():
    assert _spells_the_file_name(ast.parse("NAME = 'gate-record.json'\n")) == [1]
    assert _spells_the_file_name(ast.parse("path = d / 'gate-record.json'\n")) == [1]
    assert _spells_the_file_name(ast.parse("path = f'{d}/gate-record.json'\n")) == [1]
    assert _spells_the_file_name(ast.parse('"""the record is gate-record.json"""\n')) == []
    assert _spells_the_file_name(ast.parse("def f():\n    '''writes gate-record.json'''\n")) == []
    assert _spells_the_file_name(ast.parse("x = 'gate-records'\n")) == []
