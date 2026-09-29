"""Deck/export format plugins on ``pyforge.core.hooks`` (Story 16.1, FR-45).

Herald's Marp, PPTX, and ``.dc.html`` exporters register as default plugins
on the shared contract (canonical group ``pyforge.core.hooks`` only -- never
a parallel ``pyforge.herald.hooks`` group). A new format is another plugin
on the same spec; Herald's process is not forked.

Export success is a station result recorded on the hook context. It is not
a PR quality-gate / Warden verdict. ``publish_verdict`` is allowed only for
``DECK_EXPORT_HOOK_SPEC`` (owner ``herald``); publishing onto a
Warden-owned spec raises ``SecondVerdictError``.
"""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

from pyforge.core.hooks import HookSpec, PluginError, PluginRegistry

DECK_EXPORT_HOOK_SPEC_NAME = "pyforge.herald.deck_export"
DECK_EXPORT_OWNER = "herald"
DECK_EXPORT_HOOK_SPEC = HookSpec(name=DECK_EXPORT_HOOK_SPEC_NAME, owner=DECK_EXPORT_OWNER)

FORMAT_MARP = "marp"
FORMAT_PPTX = "pptx"
FORMAT_DC_HTML = "dc.html"
DEFAULT_EXPORT_FORMATS: tuple[str, ...] = (FORMAT_MARP, FORMAT_PPTX, FORMAT_DC_HTML)


def _format_matches(requested: object, format_id: str) -> bool:
    return requested in (None, "*", format_id)


def _continue_around(context: MutableMapping[str, Any]) -> Any:
    nxt = context.get("next")
    if callable(nxt):
        return nxt(context)
    return context


def _record_export(context: MutableMapping[str, Any], format_id: str) -> None:
    exported = context.setdefault("exported", [])
    if format_id not in exported:
        exported.append(format_id)


class _DeckExportPlugin:
    """Shared around-filter: run only when ``context["format"]`` is
    missing, ``*``, or this plugin's ``format_id``. Inject
    ``context["backends"][format_id]`` to stub the backend (unit tests
    must never spawn marp / Chrome / pixi)."""

    hook_spec: str = DECK_EXPORT_HOOK_SPEC_NAME
    owner: str = DECK_EXPORT_OWNER
    format_id: str

    def call(self, point: str, context: MutableMapping[str, Any]) -> Any:
        if point != "around":
            return context
        if not _format_matches(context.get("format"), self.format_id):
            return _continue_around(context)
        backends = context.get("backends") or {}
        if self.format_id in backends:
            backend = backends[self.format_id]
            if not callable(backend):
                raise PluginError(f"backends[{self.format_id!r}] must be callable, got {type(backend).__name__}")
            backend(context)
        self._record_after_backend(context)
        return _continue_around(context)

    def _record_after_backend(self, context: MutableMapping[str, Any]) -> None:
        """Today's backends are the default plugins: a matching around
        records the format. Inject ``backends[format_id]`` to run a real
        exporter; without it this is record-only (no pixi / marp / Chrome)."""
        _record_export(context, self.format_id)


class MarpExportPlugin(_DeckExportPlugin):
    format_id = FORMAT_MARP


class PptxExportPlugin(_DeckExportPlugin):
    format_id = FORMAT_PPTX


class DcHtmlExportPlugin(_DeckExportPlugin):
    format_id = FORMAT_DC_HTML


def default_export_plugins() -> tuple[MarpExportPlugin, PptxExportPlugin, DcHtmlExportPlugin]:
    return (MarpExportPlugin(), PptxExportPlugin(), DcHtmlExportPlugin())


def register_default_export_plugins(registry: PluginRegistry) -> None:
    for plugin in default_export_plugins():
        registry.register(plugin)


def export_via_hooks(
    format: str,
    context: MutableMapping[str, Any] | None = None,
    *,
    registry: PluginRegistry | None = None,
) -> list[str]:
    """Dispatch ``around`` on ``DECK_EXPORT_HOOK_SPEC`` for ``format``.

    Unknown format with no matching plugin: empty ``exported`` list, no
    error. Extra plugins already on ``registry`` for the same spec run
    when their ``format_id`` matches -- no second entry-point group.
    """
    ctx: MutableMapping[str, Any] = {} if context is None else context
    ctx["format"] = format
    ctx.setdefault("exported", [])
    reg = PluginRegistry() if registry is None else registry
    register_default_export_plugins(reg)
    reg.invoke("around", ctx, spec_name=DECK_EXPORT_HOOK_SPEC_NAME)
    return list(ctx["exported"])
