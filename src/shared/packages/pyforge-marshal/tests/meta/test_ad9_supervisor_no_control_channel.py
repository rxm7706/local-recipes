"""Meta test -- AD-9 import-linter contract (Story 3.4): the supervisor
sidecar has no control channel back into the agent session/CLI (the
architecture's own "a session can never disable, silence, or reconfigure
its own supervisor" rule, made structural). Mirrors
``test_ad3_ad4_import_linter.py``'s own approach: parse ``pyproject.toml``
for the NEW contract's declared shape and invoke the real ``lint-imports``
CLI to prove it (and its two siblings) hold against the installed package.

Import-linter reasons about IMPORTS only, never about call expressions or
stdlib usage -- it cannot see a raw socket, a ``multiprocessing`` handle, or
a blocking ``sys.stdin`` read, none of which requires an ``import`` of
``pyforge.marshal.cli`` to build a control channel. The AST/text scans below
cover exactly that gap, over the supervisor package's own source files.
"""

from __future__ import annotations

import ast
import re
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

_PACKAGE_ROOT = Path(__file__).resolve().parents[2]
_PYPROJECT = _PACKAGE_ROOT / "pyproject.toml"
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

# The concrete control-channel primitives no port/adapter in this package
# legitimately needs: a raw socket, a subprocess-spawning IPC mechanism
# (multiprocessing), or a blocking read of this process's OWN stdin --
# AD-9's own "reads argv once at start and touches no other
# externally-writable input for its own control flow."
_FORBIDDEN_TOP_LEVEL_MODULES = frozenset({"socket", "multiprocessing"})


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def _contracts() -> list[dict]:
    data = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))
    return data["tool"]["importlinter"]["contracts"]


def _contract_forbidding_cli() -> dict:
    # .get: a contract of another import-linter type has no
    # forbidden_modules key -- skip it rather than KeyError-ing and masking
    # the real assertion (mirrors test_ad3_ad4_import_linter.py's own
    # `_contract_forbidding` helper).
    for contract in _contracts():
        if "pyforge.marshal.cli" in contract.get("forbidden_modules", []):
            return contract
    raise AssertionError("no contract forbids pyforge.marshal.cli")


def test_ad9_supervisor_no_control_channel_contract_shape():
    contract = _contract_forbidding_cli()
    assert contract["type"] == "forbidden"
    assert contract["source_modules"] == ["pyforge.marshal.supervisor"]
    assert contract["forbidden_modules"] == ["pyforge.marshal.cli"]


def _installed_package_dir() -> Path:
    import pyforge.marshal

    package_file = pyforge.marshal.__file__
    assert package_file is not None
    return Path(package_file).resolve().parent


def _supervisor_source_files() -> list[Path]:
    supervisor_dir = _installed_package_dir() / "supervisor"
    assert supervisor_dir.is_dir(), f"expected a supervisor package at {supervisor_dir}"
    return sorted(supervisor_dir.rglob("*.py"))


def test_supervisor_package_exists_and_has_source_files():
    """A guard against the scans below silently passing over an empty
    ``rglob`` (e.g. a renamed/relocated package) -- both scans report
    trivially "no offenders" over zero files, which proves nothing."""
    assert _supervisor_source_files()


# Every callable that takes a module NAME as a literal string argument and
# returns the imported module -- the shapes the static ast.Import/
# ast.ImportFrom scan below is structurally blind to. `import_module` was
# added by one review pass; `__import__` (CPython's own import builtin, and
# the shorter of the two spellings) by the next -- it is the same evasion
# family, not a new one, and was left open while its rarer sibling was
# closed.
_LAZY_IMPORT_CALLABLES = frozenset({"import_module", "__import__"})


def _is_lazy_import_call(node: ast.AST) -> bool:
    """``True`` for a call shaped like ``importlib.import_module(...)`` /
    ``builtins.__import__(...)`` (attribute spelling) OR a bare
    ``import_module(...)`` / ``__import__(...)`` (name spelling, the former
    reachable via ``from importlib import import_module``, the latter always
    available as a builtin) -- review finding: the static ``ast.Import``/
    ``ast.ImportFrom`` scan below cannot see a module name that arrives as a
    STRING argument to a function call rather than an import statement, so
    ``importlib.import_module("socket")`` -- and, until this pass,
    ``__import__("socket")`` -- evaded it entirely."""
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr in _LAZY_IMPORT_CALLABLES
    if isinstance(func, ast.Name):
        return func.id in _LAZY_IMPORT_CALLABLES
    return False


def _forbidden_module_references(tree: ast.AST, path: str = "<test>") -> list[str]:
    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in _FORBIDDEN_TOP_LEVEL_MODULES:
                    offenders.append(f"{path}:{node.lineno} imports {alias.name!r}")
        elif isinstance(node, ast.ImportFrom):
            if (
                node.module is not None
                and node.module.split(".")[0] in _FORBIDDEN_TOP_LEVEL_MODULES
            ):
                offenders.append(f"{path}:{node.lineno} imports from {node.module!r}")
        elif (
            isinstance(node, ast.Call)
            and _is_lazy_import_call(node)
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
            and node.args[0].value.split(".")[0] in _FORBIDDEN_TOP_LEVEL_MODULES
        ):
            offenders.append(
                f"{path}:{node.lineno} lazily imports {node.args[0].value!r}"
            )
    return offenders


def test_supervisor_imports_no_socket_or_multiprocessing_module():
    offenders: list[str] = []
    for path in _supervisor_source_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        offenders.extend(_forbidden_module_references(tree, str(path)))
    assert not offenders, (
        "the supervisor sidecar must have no control channel (AD-9) -- "
        f"found: {offenders}"
    )


@pytest.mark.parametrize(
    "snippet",
    [
        'import socket',
        'from multiprocessing import Process',
        'import importlib\nimportlib.import_module("socket")',
        'from importlib import import_module\nimport_module("multiprocessing")',
        '__import__("socket")',
        'import builtins\nbuiltins.__import__("multiprocessing")',
    ],
)
def test_forbidden_module_references_catches_every_evasion_shape(snippet):
    """Proves the scanner itself catches a synthetic violation of each
    shape (plain import, ``from`` import, both ``importlib.import_module``
    call spellings, and both ``__import__`` builtin spellings) -- run
    against an in-memory snippet, never the real supervisor source, so this
    test cannot be satisfied by coincidentally-clean production code.

    Two successive review findings built this list: the original scan saw
    only the first two shapes, so ``importlib.import_module("socket")``
    evaded it; the widening that closed THAT left ``__import__("socket")``
    -- the shorter, always-available spelling of the identical evasion --
    open."""
    tree = ast.parse(snippet)
    assert _forbidden_module_references(tree)


@pytest.mark.parametrize(
    "snippet",
    [
        'import importlib\nimportlib.import_module("json")',
        '__import__("json")',
    ],
)
def test_forbidden_module_references_does_not_flag_an_unrelated_lazy_import(snippet):
    """The widened check must stay scoped to the two forbidden module
    NAMES -- a lazy import of an unrelated module must not false-positive,
    in either callable spelling."""
    tree = ast.parse(snippet)
    assert _forbidden_module_references(tree) == []


def test_supervisor_never_reads_stdin_or_calls_input():
    offenders: list[str] = []
    for path in _supervisor_source_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "input"
            ):
                offenders.append(f"{path}:{node.lineno} calls input()")
            if isinstance(node, ast.Attribute) and node.attr == "stdin":
                offenders.append(f"{path}:{node.lineno} references .stdin")
    assert not offenders, (
        "the supervisor sidecar must never read its own stdin (AD-9) -- "
        f"found: {offenders}"
    )


def test_lint_imports_passes_against_the_installed_package():
    if shutil.which("lint-imports") is None:
        pytest.fail(
            "lint-imports not on PATH -- run this suite via the env that "
            "provisions import-linter: "
            "`pixi run -e pyforge-marshal pyforge-marshal-test`"
        )
    result = subprocess.run(
        ["lint-imports", "--config", str(_PYPROJECT), "--no-cache"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    stdout = _strip_ansi(result.stdout)
    assert result.returncode == 0, (
        f"lint-imports failed (exit {result.returncode}):\n"
        f"stdout:\n{stdout}\nstderr:\n{_strip_ansi(result.stderr)}"
    )
    assert re.search(r"\b0\s+broken\b", stdout), (
        f"expected a '0 broken' summary in lint-imports output:\n{stdout}"
    )
