"""The SINGLE Kedro-API touch point for the MCP surface (Story B3, AD-23).

Everything in ``pyforge.atlas.mcp`` that needs a live Kedro object goes
through this module — one bootstrap path, one session factory, one catalog
accessor. That keeps the tool bodies (``tools.py``) trivially thin (AD-7)
and gives the tests exactly one seam to patch for offline exercise (AD-11).

Import discipline (survives the whole-package ``test_no_inline_io`` +
AD-1 scans): ``__future__`` + stdlib (``contextlib`` / ``pathlib`` /
``typing``) + ``kedro.framework.{session,startup}`` ONLY. No ``dagster``,
no ``kedro_mcp``, no HTTP/DB client, no pandas.
"""

from __future__ import annotations

import contextlib
from pathlib import Path
from typing import Any, Iterator

from kedro.framework.session import KedroSession
from kedro.framework.startup import bootstrap_project
from pyforge.core.flags import read_boolean

# The member dir (the Kedro project root):
# .../pyforge-atlas/src/pyforge/atlas/mcp/session.py
#     parents[0]=mcp  [1]=atlas  [2]=pyforge  [3]=src  [4]=pyforge-atlas
PROJECT_ROOT = Path(__file__).resolve().parents[4]

# The project root must carry the declared catalog — this package is
# repo-local (src-layout, never installed to site-packages), so the conf
# tree is always adjacent.
assert (PROJECT_ROOT / "conf" / "base" / "catalog.yml").is_file(), (
    f"PROJECT_ROOT mis-resolved: no conf/base/catalog.yml under {PROJECT_ROOT}"
)


# Epic 42 (spec-feature-flag-governance CAP-7): the kill switches for atlas's pre-rule runtime capabilities, read
# here on the one execution plane (AD-23) through ``pyforge.core.flags`` only, defaulting ON. OFF raises
# ``AtlasMCPError`` naming the flag (the surface's own error, no new exit code); ``pyforge atlas run`` refuses with
# 2 in ``__main__`` reading the same keys. Spelled literally so the gate's orphan check finds them.
AGENT_PIPELINE_TOOLS_FLAG_KEY = "pyforge.atlas.agent_pipeline_tools"  # CAP-9, Story 42.1
MANIFEST_INVENTORY_FLAG_KEY = "pyforge.atlas.manifest_inventory"  # CAP-13, Story 42.2
MANIFEST_INVENTORY_PIPELINE = "universal_sbom"


def _flag_off_error(key: str) -> Exception:
    from pyforge.atlas.mcp.tools import AtlasMCPError  # noqa: PLC0415 -- tools imports this module at load

    return AtlasMCPError(f"flag {key} is off")


def require_agent_pipeline_tools() -> None:
    """Raise ``AtlasMCPError`` when the CAP-9 switch reads OFF (a trigger or a read); return when ON."""
    if not read_boolean(AGENT_PIPELINE_TOOLS_FLAG_KEY, default=True):
        raise _flag_off_error(AGENT_PIPELINE_TOOLS_FLAG_KEY)


def require_manifest_inventory() -> None:
    """Raise ``AtlasMCPError`` when the CAP-13 switch reads OFF (the ``universal_sbom`` trigger); return when ON."""
    if not read_boolean(MANIFEST_INVENTORY_FLAG_KEY, default=True):
        raise _flag_off_error(MANIFEST_INVENTORY_FLAG_KEY)


@contextlib.contextmanager
def bootstrapped_session(
    project_path: Path | str | None = None,
    extra_params: dict[str, Any] | None = None,
    env: str | None = None,
) -> Iterator[KedroSession]:
    """Bootstrap the project and yield a ``KedroSession`` — the ONE
    execution plane (AD-23): every MCP trigger/read rides the identical
    session machinery (runner, hooks, profile) a CLI run uses.

    ``extra_params`` is the surface's public name for run-scoped parameter
    overrides; kedro 1.5.0's ``KedroSession.create`` calls them
    ``runtime_params`` — mapped here, in the single touch point.
    """
    root = Path(project_path) if project_path is not None else PROJECT_ROOT
    bootstrap_project(root)
    session = KedroSession.create(
        project_path=root,
        runtime_params=extra_params or {},
        env=env,
    )
    with session:
        yield session


def loaded_catalog(session: KedroSession):
    """The session's loaded ``DataCatalog`` — the one read plane."""
    return session.load_context().catalog
