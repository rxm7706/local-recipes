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
from pyforge.herald.errors import SeedConflictError, TransportUnreachableError
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


# --- determinism boundary: bridge.py's own import statements ---------------

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

_ALLOWED_TRANSPORT_IMPORT_MODULES = {"transport.base", ".transport.base"}
"""The only transport-package module bridge.py may import from: the
Protocol + value types. The package root ``.transport`` (whose
``__init__.py`` re-exports concrete adapter classes alongside the protocol)
is deliberately excluded -- importing from it at all, even for a protocol
name, is disallowed so a later edit can't accidentally reach an adapter
through the wider surface."""


def _bridge_py_ast() -> ast.Module:
    source = Path(bridge.__file__).read_text(encoding="utf-8")
    return ast.parse(source, filename=bridge.__file__)


def _bridge_py_imported_names() -> set[str]:
    """Every name bridge.py imports -- the alias actually bound into its
    namespace, from both ``import x`` and ``from m import x`` forms. Checking
    only ``ImportFrom.module`` (the ``m`` in ``from m import x``) would miss
    ``x`` entirely, which is exactly how ``from .transport import
    McpTransport`` would evade a module-name-only check."""
    names: set[str] = set()
    for node in ast.walk(_bridge_py_ast()):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.update(alias.name for alias in node.names)
    return names


def _bridge_py_importfrom_modules() -> set[str]:
    """The exact dotted module path of every ``from X import ...`` in
    bridge.py (unsplit, so ``transport.base`` and bare ``transport`` are
    distinguishable)."""
    return {
        node.module
        for node in ast.walk(_bridge_py_ast())
        if isinstance(node, ast.ImportFrom) and node.module
    }


def test_bridge_py_only_imports_transport_from_base():
    """Every ``from`` import naming anything under ``transport`` must name
    exactly ``transport.base`` -- never the package root (which re-exports
    concrete adapters) and never an adapter module directly."""
    transport_related = {
        module
        for module in _bridge_py_importfrom_modules()
        if module.split(".")[-1] == "transport" or "transport" in module.split(".")
    }
    assert transport_related <= _ALLOWED_TRANSPORT_IMPORT_MODULES


def test_bridge_py_never_names_a_concrete_transport_adapter():
    imported = _bridge_py_imported_names()
    assert imported.isdisjoint(_FORBIDDEN_ADAPTER_MODULES)
    assert imported.isdisjoint(_FORBIDDEN_ADAPTER_NAMES)


def test_bridge_py_never_names_a_recognized_inference_sdk_package():
    assert _bridge_py_imported_names().isdisjoint(_FORBIDDEN_INFERENCE_PACKAGES)
