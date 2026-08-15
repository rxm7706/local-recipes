"""Static view catalog over the live ``cf_atlas.db`` — Story 14.1 (CAP-1), now with a live
WebSocket session mode for the ``"grid"`` widget — Story 14.3 (CAP-2).

Mirrors the 6 conda-forge-expert skill CLIs whose ``query()`` runs with zero required
arguments (``staleness-report``, ``feedstock-health``, ``behind-upstream``, ``cve-watcher``,
``release-cadence``, ``adoption-stage``) as static, self-contained Bokeh HTML fragments — no
new SQL, no second data layer (see :mod:`pyforge.atlas.views.cli_bridge`). The other 5
skill CLIs all require a package-name/path argument and are deferred to a future story.

``live.py``'s ``LIVE_VIEWS``/``build_application``/``build_live_server`` are re-exported here
(the host-agnostic Bokeh WebSocket runtime); ``asgi.py``'s ``app`` is deliberately NOT —
it is a deployment entrypoint (mount target for an ASGI server), not a package-level symbol
(Boundaries & Constraints, Story 14.3). ``resources.py``'s ``current_mode``/``is_airgapped``
(Story 14.4) are re-exported here too, matching every other module's public surface.
"""

from __future__ import annotations

from .cli_bridge import CfAtlasDbUnavailableError
from .live import LIVE_VIEWS, build_application, build_live_server
from .registry import STATIC_VIEWS
from .render import render_view
from .resources import current_mode, is_airgapped
from .widgets import WIDGETS, Widget, get_widget

__all__ = [
    "STATIC_VIEWS",
    "CfAtlasDbUnavailableError",
    "render_view",
    "Widget",
    "WIDGETS",
    "get_widget",
    "LIVE_VIEWS",
    "build_application",
    "build_live_server",
    "current_mode",
    "is_airgapped",
]
