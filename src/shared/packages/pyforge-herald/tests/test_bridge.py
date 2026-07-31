"""``bridge.run``'s seam and the determinism-boundary static check
(Story 1.4, AD-3/AD-4) -- swept over every bridge-core module
(``bridge.py``, ``state.py``, ``errors.py``), not just the seam file.

The double here is hand-written, matching the shipped suite's no-
``unittest.mock`` convention (``conftest.py``'s ``FakeCaller`` is the same
pattern one layer down, at the ``ToolCaller`` seam).
"""

from __future__ import annotations

import ast
import pkgutil
import subprocess
import sys
from pathlib import Path

import pyforge.herald as herald_pkg
import pytest
from pyforge.herald import bridge, errors, registry, state
from pyforge.herald import transport as transport_pkg
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
from pyforge.herald.transport import base as transport_base


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
    """``runtime_checkable`` ``isinstance`` proves method *presence* only --
    Python compares no signatures at runtime, so parameter drift between a
    double and the protocol is the type checker's to catch, not this
    test's."""
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


# --- determinism boundary: bridge-core's own source -------------------------

_BRIDGE_CORE_MODULES = (bridge, state, errors, registry)
"""The modules on the deterministic side of the boundary today. ``cli.py``
is the CLI layer (AD-2) and ``transport/`` is the adapter side (AD-3) --
neither belongs in this sweep. ``registry.py`` (Story 1.5) joins here: it is
bridge-core, not the CLI layer or a transport adapter, so it has no cause
for exclusion."""

_SPECULATIVE_ADAPTER_MODULES = {"agent_sdk_transport"}
"""Story 1.3's planned adapter, denied by name before it exists --
derivation below cannot cover an unwritten module."""

_FORBIDDEN_ADAPTER_MODULES = {
    module.name
    for module in pkgutil.iter_modules(transport_pkg.__path__)
    if module.name != "base"
} | _SPECULATIVE_ADAPTER_MODULES
"""Concrete transport adapter *modules* bridge-core may never name directly
(AD-3). Derived from the live package -- every submodule except ``base`` is
an adapter by construction -- so a new adapter is covered the day it lands,
not the day someone remembers this set; the speculative names are unioned
in because derivation cannot see what does not exist yet."""

_SPECULATIVE_ADAPTER_NAMES = {"AgentSdkTransport"}

_FORBIDDEN_ADAPTER_NAMES = {
    name for name in transport_pkg.__all__ if not hasattr(transport_base, name)
} | _SPECULATIVE_ADAPTER_NAMES
"""Everything ``transport/__init__.py`` re-exports that does not come from
``transport.base`` -- the adapter classes plus their companions
(``DesignCredential``, ``resolve_design_credential``, ``DESIGN_MCP_URL``,
...). ``from .transport import McpTransport`` is a real, reachable
violation distinct from naming the adapter's own module -- both are
checked, and deriving the set keeps the newest adapter's exports covered
automatically."""

_FORBIDDEN_INFERENCE_PACKAGES = {
    "a2a_sdk",
    "anthropic",
    "boto3",
    "claude_agent_sdk",
    "cohere",
    "fastmcp",
    "genai",
    "generativeai",
    "groq",
    "huggingface_hub",
    "langchain",
    "langchain_anthropic",
    "langchain_core",
    "langchain_mcp_adapters",
    "langgraph",
    "litellm",
    "llama_cpp",
    "mcp",
    "mistralai",
    "ollama",
    "openai",
    "pydantic_ai",
    "transformers",
    "vertexai",
    "vllm",
}
"""A documented short list of LLM/inference-SDK package names bridge-core
may never name directly (AD-4) -- a defensive, hand-maintained denylist,
not a derived one. ``google-genai`` appears as its import segment ``genai``
and the still-widely-installed legacy ``google-generativeai`` as
``generativeai``; ``fastmcp`` is in this repo's own pixi environments (and
a Gemini MCP server is in its tool config), so those are foreseeable
reaches, not hypothetical ones. Local-inference stacks (``transformers``,
``vllm``, ``llama_cpp``, ``huggingface_hub``) and hosted-inference clients
(``vertexai``, ``boto3`` for Bedrock) clear the same foreseeable-reach
bar."""

_FORBIDDEN_DYNAMIC_IMPORT_NAMES = {
    "__dict__",
    "__getattribute__",
    "__import__",
    "attrgetter",
    "eval",
    "exec",
    "getattr",
    "globals",
    "import_module",
    "importlib",
    "locals",
    "modules",
    "pkgutil",
    "resolve_name",
    "runpy",
    "vars",
}
"""A static check cannot see what *runtime* machinery loads -- so none of
it may be named in bridge-core at all: dynamic import (``importlib``,
``__import__``, ``pkgutil``/``resolve_name``, ``runpy``), string execution
(``eval``/``exec``, which can synthesize an import out of concatenated
strings), dynamic attribute access (``getattr``, ``vars``, ``__dict__``,
``__getattribute__``, ``operator.attrgetter``, ``globals``/``locals`` --
each reaches an adapter as an attribute of an innocently imported parent
while the attribute's name hides in a string), and the already-imported-
module registry (``sys.modules``, via its ``modules`` attribute -- a
lookup there imports nothing, so the runtime subprocess probe stays green
while an adapter some other layer already loaded is fished out by string
key). A string fed to any of these is invisible to this check by design;
forbidding the machinery's own names is the strongest guarantee a static
check can give, and that limit is deliberate: the epics AC asks for a
static/code-level proof."""


def test_derived_adapter_denylists_cover_the_known_adapter():
    """The derivation's own coverage pin: if the package layout ever shifts
    so the derivation goes blind (``base`` renamed, ``__all__`` pruned),
    this fails before the guard silently covers nothing."""
    assert "mcp_transport" in _FORBIDDEN_ADAPTER_MODULES
    assert "McpTransport" in _FORBIDDEN_ADAPTER_NAMES


def test_bridge_core_sweep_covers_every_non_excluded_package_module():
    """``_BRIDGE_CORE_MODULES`` is declared while every denylist above is
    derived -- this pin makes the declaration loud instead of silently
    stale: a new package module (Story 1.5's ``registry.py``) fails here
    until it is either added to the sweep or, with cause, to the exclusion
    set (``cli`` is the CLI layer, AD-2; ``transport`` is the adapter
    side, AD-3)."""
    package_modules = {
        module.name for module in pkgutil.iter_modules(herald_pkg.__path__)
    }
    swept = {module.__name__.rsplit(".", 1)[-1] for module in _BRIDGE_CORE_MODULES}
    assert package_modules - {"cli", "transport"} == swept


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


def _module_source(module) -> str:
    return Path(module.__file__).read_text(encoding="utf-8")


def test_bridge_py_reaches_transport_only_via_transport_base():
    assert _transport_import_violations(_module_source(bridge)) == []


@pytest.mark.parametrize("module", (state, errors, registry), ids=lambda m: m.__name__)
def test_state_and_errors_never_touch_transport_at_all(module):
    """Stricter than bridge.py's rule: these bridge-core modules have no
    business with the transport package in any form, not even ``base`` --
    the identifier sweep catches attribute traversal as well as imports.
    ``registry.py`` (Story 1.5) joins ``state``/``errors`` here rather than
    ``bridge``'s own laxer test: unlike ``bridge.run``, it has no legitimate
    reason to name ``transport.base`` at all."""
    assert "transport" not in _all_identifiers(_module_source(module))


@pytest.mark.parametrize("module", _BRIDGE_CORE_MODULES, ids=lambda m: m.__name__)
def test_bridge_core_never_names_a_concrete_transport_adapter(module):
    identifiers = _all_identifiers(_module_source(module))
    assert identifiers.isdisjoint(_FORBIDDEN_ADAPTER_MODULES)
    assert identifiers.isdisjoint(_FORBIDDEN_ADAPTER_NAMES)


@pytest.mark.parametrize("module", _BRIDGE_CORE_MODULES, ids=lambda m: m.__name__)
def test_bridge_core_never_names_a_recognized_inference_sdk_package(module):
    assert _all_identifiers(_module_source(module)).isdisjoint(
        _FORBIDDEN_INFERENCE_PACKAGES
    )


@pytest.mark.parametrize("module", _BRIDGE_CORE_MODULES, ids=lambda m: m.__name__)
def test_bridge_core_never_names_dynamic_import_machinery(module):
    assert _all_identifiers(_module_source(module)).isdisjoint(
        _FORBIDDEN_DYNAMIC_IMPORT_NAMES
    )


def test_importing_bridge_does_not_load_the_transport_package(tmp_path: Path):
    """The ``TYPE_CHECKING``-only import, proven at runtime: a fresh
    interpreter that imports ``bridge`` must not execute
    ``transport/__init__.py`` (which eagerly loads the concrete
    ``McpTransport``) -- the boundary holds in ``sys.modules``, not only in
    this file's AST. A subprocess is unavoidable here: this test module
    itself imports the transport package, so the current interpreter's
    ``sys.modules`` is already polluted."""
    probe = (
        "import sys; import pyforge.herald.bridge; "
        "sys.exit(1 if any(m.startswith('pyforge.herald.transport') "
        "for m in sys.modules) else 0)"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr


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
        "import fastmcp",
        "import importlib",
        "from importlib import import_module",
        'x = __import__("anthropic")',
        'exec("imp" + "ort anthropic")',
        'eval("__im" + "port__(\'anthropic\')")',
        'getattr(h.transport, "Mcp" + "Transport")',
        'sys.modules["pyforge.herald.transport." + "mcp_" + "transport"]',
        'vars(mod)["Mcp" + "Transport"]',
        'h.transport.__dict__["Mcp" + "Transport"]',
        'pkgutil.resolve_name("pyforge.herald.transport:McpTransport")',
        'operator.attrgetter("Mcp" + "Transport")(mod)',
        'globals()["__buil" + "tins__"]',
    ],
)
def test_guard_flags_inference_and_dynamic_import_forms(evasion):
    """``from anthropic import Anthropic`` evaded the earlier leaf-name-only
    check (only ``Anthropic`` was collected, never ``anthropic``); dynamic
    imports were invisible to it entirely, and ``eval``/``exec``/``getattr``
    could each smuggle an adapter or SDK behind a string the AST cannot see
    -- so the machinery's own names are forbidden. The later six forms each
    evaded the first eval/exec/getattr denylist too (``sys.modules`` fishes
    an already-loaded adapter out by string key without importing anything;
    ``vars``/``__dict__`` substitute for the denied ``getattr``;
    ``pkgutil.resolve_name`` is a full dynamic import under another name;
    ``attrgetter`` and ``globals`` are the same machinery one module over).
    Pin every known form closed."""
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
