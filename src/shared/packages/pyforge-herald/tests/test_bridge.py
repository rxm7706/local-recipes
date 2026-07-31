"""``bridge.run``'s seam and the determinism-boundary static import check
(Story 1.4, AD-3/AD-4).

The double here is hand-written, matching the shipped suite's no-
``unittest.mock`` convention (``conftest.py``'s ``FakeCaller`` is the same
pattern one layer down, at the ``ToolCaller`` seam).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from pyforge.herald import bridge
from pyforge.herald.cli import dispatch
from pyforge.herald.errors import (
    HeraldError,
    SeedConflictError,
    TransportUnreachableError,
)
from pyforge.herald.transport import (
    DesignTransport,
    FileRead,
    PlanHandle,
    PreviewRef,
    ProjectRef,
)


class FakeTransport:
    """A hand-written ``DesignTransport`` double: no network, no adapter,
    structurally conforms to the ``runtime_checkable`` protocol."""

    def get_design_prompt(
        self, *, design_system_id: str | None = None, project_id: str | None = None
    ) -> str:
        return "PROMPT"

    def create_project(
        self, *, name: str, design_system_id: str | None = None
    ) -> ProjectRef:
        return ProjectRef(project_id="p-1", url="https://claude.ai/design/p/p-1")

    def finalize_plan(
        self, *, project_id, writes=(), deletes=(), scope="paths"
    ) -> PlanHandle:
        return PlanHandle(plan_token="tok")

    def create_support_js(
        self, *, project_id, if_match, path="support.js", plan_token=None
    ):
        return {}

    def copy_files(self, *, project_id, files, plan_token=None):
        return {}

    def write_files(self, *, project_id, files, plan_token=None):
        return {}

    def read_file(
        self, *, project_id, path, if_none_match=None, offset=None, limit=None
    ) -> FileRead:
        return FileRead(path=path, etag="E1", body="x", unchanged=False)

    def render_preview(self, *, project_id, path) -> PreviewRef:
        return PreviewRef(open_url="https://claude.ai/design/p/p-1")


def test_fake_transport_conforms_to_the_design_transport_protocol():
    assert isinstance(FakeTransport(), DesignTransport)


def test_run_calls_operation_with_the_transport_and_returns_its_result():
    transport = FakeTransport()
    seen = []

    def operation(t: DesignTransport) -> str:
        seen.append(t)
        return "result"

    assert bridge.run(transport, operation) == "result"
    assert seen == [transport]


@pytest.mark.parametrize(
    "error",
    [SeedConflictError("edits exist"), TransportUnreachableError("no route")],
)
def test_run_propagates_any_herald_error_unchanged(error):
    transport = FakeTransport()

    def operation(t: DesignTransport):
        raise error

    with pytest.raises(type(error)) as excinfo:
        bridge.run(transport, operation)
    assert excinfo.value is error


# --- determinism boundary: bridge.py's own source ---------------------------

_FORBIDDEN_ADAPTER_MODULES = {"mcp_transport", "agent_sdk_transport"}
"""Concrete transport adapter *modules* bridge.py may never name directly
(AD-3)."""

_FORBIDDEN_ADAPTER_NAMES = {"McpTransport", "AgentSdkTransport"}
"""Concrete transport adapter *classes*. ``transport/__init__.py`` re-exports
these alongside the ``DesignTransport`` protocol, so ``from .transport import
McpTransport`` is a real, reachable violation distinct from naming the
adapter's own module -- both must be checked."""

_FORBIDDEN_INFERENCE_PACKAGES = {
    "anthropic",
    "openai",
    "mcp",
    "ollama",
    "claude_agent_sdk",
    "pydantic_ai",
    "langchain_anthropic",
    "langchain_mcp_adapters",
    "a2a_sdk",
}
"""A documented short list of LLM/inference-SDK package names bridge.py may
never name directly (AD-4). Not all of these are necessarily cataloged in
``docs/reference/library-llms-full.md`` today -- the list is a defensive,
hand-maintained denylist, not a derived one."""

_FORBIDDEN_DYNAMIC_IMPORT_NAMES = {"importlib", "import_module", "__import__"}
"""A static check cannot see what a *runtime* import loads -- so the
machinery for one may not be named in bridge.py at all. (A string fed to it
would still be invisible; forbidding the machinery's own names is the
strongest guarantee a static check can give, and that limit is deliberate:
the epics AC asks for a static/code-level proof.)"""


def _import_statements(source: str) -> list[tuple[str, tuple[str, ...]]]:
    """Every import statement as ``(module_path, imported_names)``.

    ``import x.y.z as w``       -> ``("x.y.z", ())``
    ``from x.y import a, b``    -> ``("x.y", ("a", "b"))``
    ``from . import transport`` -> ``(".", ("transport",))``
    ``from .x.y import a``      -> ``(".x.y", ("a",))``

    Relative dots are reconstructed from ``ImportFrom.level`` -- the AST
    stores them there, never in ``module``, and ``module`` is ``None`` for
    ``from . import x``, which a ``node.module``-only reading drops
    entirely. Plain ``import`` statements are kept with their full dotted
    path, not just the first segment. These are exactly the blind spots an
    earlier version of this check had."""
    statements: list[tuple[str, tuple[str, ...]]] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            statements.extend((alias.name, ()) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = "." * node.level + (node.module or "")
            statements.append((module, tuple(alias.name for alias in node.names)))
    return statements


def _all_identifiers(source: str) -> set[str]:
    """Every identifier the source's AST mentions anywhere: names, attribute
    accesses, and every dotted segment plus alias of every import statement.
    Broader than imports alone, so ``t.McpTransport`` attribute traversal
    after an innocent-looking import -- or a bare ``__import__`` call -- is
    caught too. Docstrings and other string constants are not identifiers
    and are deliberately not included."""
    identifiers: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Name):
            identifiers.add(node.id)
        elif isinstance(node, ast.Attribute):
            identifiers.add(node.attr)
        elif isinstance(node, ast.ImportFrom) and node.module:
            # The `m` in `from m import x` is on the ImportFrom node, not in
            # an alias -- without this branch `from anthropic import
            # Anthropic` contributes only "Anthropic".
            identifiers.update(seg for seg in node.module.split(".") if seg)
        elif isinstance(node, ast.alias):
            identifiers.update(seg for seg in node.name.split(".") if seg)
            if node.asname:
                identifiers.add(node.asname)
    return identifiers


def _transport_import_violations(source: str) -> list[str]:
    """Import statements that reach the transport package anywhere except a
    ``from <...>.transport.base import <names>`` form -- the Protocol +
    value types module. The package root (``from . import transport``,
    ``import pyforge.herald.transport``, ``from .transport import X``) is a
    violation even for a protocol name: its ``__init__.py`` re-exports
    concrete adapters alongside it, and a plain ``import`` of any
    ``transport``-dotted path binds a root package the adapters are then
    one attribute access away from."""
    violations = []
    for module, imported in _import_statements(source):
        segments = [seg for seg in module.split(".") if seg]
        if "transport" not in segments and "transport" not in imported:
            continue
        is_from_base = bool(imported) and segments[-2:] == ["transport", "base"]
        if "transport" in imported or not is_from_base:
            violations.append(f"module {module!r} importing {imported!r}")
    return violations


def _bridge_py_source() -> str:
    return Path(bridge.__file__).read_text(encoding="utf-8")


def test_bridge_py_reaches_transport_only_via_transport_base():
    assert _transport_import_violations(_bridge_py_source()) == []


def test_bridge_py_never_names_a_concrete_transport_adapter():
    identifiers = _all_identifiers(_bridge_py_source())
    assert identifiers.isdisjoint(_FORBIDDEN_ADAPTER_MODULES)
    assert identifiers.isdisjoint(_FORBIDDEN_ADAPTER_NAMES)


def test_bridge_py_never_names_a_recognized_inference_sdk_package():
    assert _all_identifiers(_bridge_py_source()).isdisjoint(
        _FORBIDDEN_INFERENCE_PACKAGES
    )


def test_bridge_py_never_names_dynamic_import_machinery():
    assert _all_identifiers(_bridge_py_source()).isdisjoint(
        _FORBIDDEN_DYNAMIC_IMPORT_NAMES
    )


@pytest.mark.parametrize(
    "evasion",
    [
        "from . import transport",
        "from .transport import DesignTransport",
        "from .transport import McpTransport",
        "import pyforge.herald.transport",
        "import pyforge.herald.transport as t",
        "import pyforge.herald.transport.mcp_transport as mt",
        "import pyforge.herald.transport.base",
    ],
)
def test_guard_flags_every_known_transport_evasion_form(evasion):
    """Each of these forms reaches the transport package other than through
    ``from ....transport.base import``; several evaded an earlier version of
    this check (``from . import transport`` has ``module=None`` in the AST;
    plain ``import`` was reduced to its first segment). Pin them all."""
    assert _transport_import_violations(evasion)


@pytest.mark.parametrize(
    "evasion",
    [
        "from .transport import McpTransport",
        "from .transport.mcp_transport import McpTransport",
        "import pyforge.herald.transport.mcp_transport as mt",
        "t.McpTransport()",
    ],
)
def test_guard_flags_adapter_names_in_any_position(evasion):
    forbidden = _FORBIDDEN_ADAPTER_MODULES | _FORBIDDEN_ADAPTER_NAMES
    assert not _all_identifiers(evasion).isdisjoint(forbidden)


@pytest.mark.parametrize(
    "evasion",
    [
        "import anthropic",
        "from anthropic import Anthropic",
        "from mcp import ClientSession",
        "import importlib",
        "from importlib import import_module",
        'x = __import__("anthropic")',
    ],
)
def test_guard_flags_inference_and_dynamic_import_forms(evasion):
    """``from anthropic import Anthropic`` evaded the earlier leaf-name-only
    check (only ``Anthropic`` was collected, never ``anthropic``); dynamic
    imports were invisible to it entirely. Pin both closed."""
    forbidden = _FORBIDDEN_INFERENCE_PACKAGES | _FORBIDDEN_DYNAMIC_IMPORT_NAMES
    assert not _all_identifiers(evasion).isdisjoint(forbidden)


# --- the epics AC's composed flow: raise in bridge.run, catch in dispatch ---


@pytest.mark.parametrize(
    ("error", "expected_code"),
    [
        (SeedConflictError("edits exist"), 3),
        (TransportUnreachableError("no route"), 4),
        (HeraldError("unmapped"), 1),
    ],
)
def test_dispatch_over_bridge_run_catches_each_error_exactly_once_at_the_boundary(
    capsys, error, expected_code
):
    """The epics AC's literal scenario, composed end to end: a transport
    double raises inside ``bridge.run``, nothing in between catches (1.4
    ships no layer in between), and ``cli.dispatch`` -- the CLI boundary --
    maps it to exactly one exit code and exactly one stderr line."""
    transport = FakeTransport()

    def operation(t: DesignTransport):
        raise error

    assert dispatch(lambda: bridge.run(transport, operation)) == expected_code
    err_lines = capsys.readouterr().err.splitlines()
    assert len(err_lines) == 1
    assert type(error).__name__ in err_lines[0]
