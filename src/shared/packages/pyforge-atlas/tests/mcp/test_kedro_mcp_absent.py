"""AC-3 (behavioral half) — the surface works with ``kedro_mcp`` ABSENT.

``sys.modules["kedro_mcp"] = None`` makes any ``import kedro_mcp`` raise
``ImportError``; the surface is then freshly imported AND exercised (both
the trigger and the read shapes), proving ``kedro-mcp`` is never
load-bearing (spec § 4.5 / § 5.5, FR-7).

The STRUCTURAL half of this proof is
``tests/catalog/test_no_inline_io.py::test_ad1_import_direction`` — the
whole-package AST scan forbidding any ``kedro_mcp`` (or ``dagster``)
import anywhere in ``pyforge.atlas``.
"""

from __future__ import annotations

import contextlib
import importlib
import sys

import pytest
from kedro.io import DataCatalog, MemoryDataset

_MCP_MODULES = (
    "pyforge.atlas.mcp",
    "pyforge.atlas.mcp.session",
    "pyforge.atlas.mcp.tools",
)


@pytest.fixture()
def kedro_mcp_unimportable():
    """Poison ``kedro_mcp`` and force a FRESH import of the mcp surface,
    restoring ``sys.modules`` afterwards."""
    saved = {name: sys.modules.get(name) for name in ("kedro_mcp", *_MCP_MODULES)}
    try:
        sys.modules["kedro_mcp"] = None  # any `import kedro_mcp` -> ImportError
        for name in _MCP_MODULES:
            sys.modules.pop(name, None)
        mcp_pkg = importlib.import_module("pyforge.atlas.mcp")
        tools = importlib.import_module("pyforge.atlas.mcp.tools")
        session_mod = importlib.import_module("pyforge.atlas.mcp.session")
        yield mcp_pkg, tools, session_mod
    finally:
        for name, mod in saved.items():
            if mod is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = mod


def test_kedro_mcp_import_is_actually_poisoned(kedro_mcp_unimportable):
    with pytest.raises(ImportError):
        import kedro_mcp  # noqa: F401


def test_surface_imports_and_triggers_with_kedro_mcp_absent(
    kedro_mcp_unimportable, monkeypatch
):
    mcp_pkg, tools, session_mod = kedro_mcp_unimportable
    assert mcp_pkg.PIPELINE_NAMES == tools.PIPELINE_NAMES

    run_calls = []

    class FakeSession:
        def run(self, **kwargs):
            run_calls.append(kwargs)
            return {"vulnerability_package_rollup": object()}

    @contextlib.contextmanager
    def fake_bootstrapped_session(project_path=None, extra_params=None, env=None):
        yield FakeSession()

    monkeypatch.setattr(session_mod, "bootstrapped_session", fake_bootstrapped_session)

    receipt = tools.run_pipeline("vulnerability")
    assert run_calls == [{"pipeline_name": "vulnerability"}]
    assert receipt["outputs"] == ["vulnerability_package_rollup"]


def test_surface_reads_with_kedro_mcp_absent(kedro_mcp_unimportable, monkeypatch):
    _, tools, session_mod = kedro_mcp_unimportable
    sentinel = object()
    catalog = DataCatalog(
        datasets={"demo_ds": MemoryDataset(sentinel, copy_mode="assign")}
    )

    class FakeContext:
        pass

    class FakeSession:
        def load_context(self):
            ctx = FakeContext()
            ctx.catalog = catalog
            return ctx

    @contextlib.contextmanager
    def fake_bootstrapped_session(project_path=None, extra_params=None, env=None):
        yield FakeSession()

    monkeypatch.setattr(session_mod, "bootstrapped_session", fake_bootstrapped_session)

    assert tools.read_dataset("demo_ds") is sentinel
