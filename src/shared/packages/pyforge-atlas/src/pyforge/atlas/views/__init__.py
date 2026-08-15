"""Static view catalog over the live ``cf_atlas.db`` — Story 14.1 (CAP-1).

Mirrors the 6 conda-forge-expert skill CLIs whose ``query()`` runs with zero required
arguments (``staleness-report``, ``feedstock-health``, ``behind-upstream``, ``cve-watcher``,
``release-cadence``, ``adoption-stage``) as static, self-contained Bokeh HTML fragments — no
new SQL, no second data layer (see :mod:`pyforge.atlas.views.cli_bridge`). The other 5
skill CLIs all require a package-name/path argument and are deferred to the interactive
layer (Story 14.3).
"""

from __future__ import annotations

from .cli_bridge import CfAtlasDbUnavailableError
from .registry import STATIC_VIEWS
from .render import render_view

__all__ = [
    "STATIC_VIEWS",
    "CfAtlasDbUnavailableError",
    "render_view",
]
