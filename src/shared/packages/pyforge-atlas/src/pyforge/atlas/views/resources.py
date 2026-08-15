"""Render-profile introspection — Story 14.4 (CAP-4).

Read-only. This module never writes/sets ``BOKEH_RESOURCES`` or Bokeh's settings singleton —
it only *reports* which render profile is currently active, mirroring the conda-forge-expert
skill's ``_http.py`` (a sibling area of this same repo, ``.claude/skills/conda-forge-expert/
scripts/_http.py`` — no such module exists inside this package) posture of reading environment
variables that operators set before the process starts, never writing them at runtime.

Why there is no dedicated ``PYFORGE_ATLAS_AIRGAP``-style env var: the air-gapped render
profile is already governed entirely by Bokeh's own native ``BOKEH_RESOURCES`` env var.
``bokeh/server/tornado.py`` resolves its asset-serving mode via
``settings.resources(default="server")`` — not the library-wide ``PrioritizedSetting``
default of ``"cdn"`` — so a ``bokeh.server.server.Server``-hosted app (this package's
``live.py::build_live_server``) already serves its own bundled BokehJS/CSS same-origin
(``/static/js/...``) unless an operator explicitly sets ``BOKEH_RESOURCES=cdn``. Introducing a
second, pyforge-specific toggle would duplicate that env var with no behavioral gain: this
module would have to write ``BOKEH_RESOURCES`` (or the settings singleton) at runtime for a
one-shot override to have any effect, since the resource mode is resolved fresh on every
request. ``current_mode()`` therefore calls the exact same ``settings.resources(default=
"server")`` Bokeh's own server code path uses internally, so this introspection reflects
reality rather than a second, possibly-diverging assumption.
"""

from __future__ import annotations

from bokeh.settings import settings

# Every Bokeh resource mode that serves BokehJS/CSS without a network fetch to an external
# host (i.e. every mode except "cdn") -- Bokeh's own documented ResourcesMode set
# (bokeh.resources.Resources' docstring), verified against this env's installed Bokeh 3.9.2.
# is_airgapped() allowlists against this rather than denylisting just "cdn", so an
# unrecognized/malformed BOKEH_RESOURCES value (which Resources(mode=...) itself rejects with
# ValueError -- verified empirically) is reported as NOT air-gapped instead of silently
# defaulting to "safe" (review-pass patch: a denylist gave a false-safe reading for any typo'd
# or unknown value).
_LOCALLY_SERVED_MODES = frozenset(
    {"inline", "server", "server-dev", "relative", "relative-dev", "absolute", "absolute-dev"}
)


def current_mode() -> str:
    """The Bokeh resource mode that would be resolved right now, using the same call and
    default (``"server"``) that ``bokeh/server/tornado.py`` uses internally to serve
    ``live.py::build_live_server``'s applications. Governed entirely by the ``BOKEH_RESOURCES``
    env var (or Bokeh's own defaults/config file if unset) — this function never sets it."""
    return settings.resources(default="server")


def is_airgapped() -> bool:
    """``True`` only when the current render profile is one of Bokeh's known locally-served
    modes (``server``, ``server-dev``, ``inline``, ``relative``, ``relative-dev``, ``absolute``,
    ``absolute-dev``) -- ``False`` for ``"cdn"`` AND for any unrecognized/malformed
    ``BOKEH_RESOURCES`` value (a conservative default: an unknown mode is reported as NOT
    verified air-gap-safe, never assumed safe)."""
    return current_mode() in _LOCALLY_SERVED_MODES
