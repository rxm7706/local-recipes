"""Steward deploy-profile adapters as plugins (Story 32.2, FR-45).

Publishes ``pyforge.steward.deploy_profile`` (owner ``steward``) on the
shared ``pyforge.core.hooks`` surface. Today's backends — Harness, Splunk,
StorageGRID, EPLX GHA, Tachyon, and Jira — register as default plugins.
Swapping a vendor is another plugin on the same spec; the Golden Path is
not forked.

All six are optional at runtime. The Golden Path Pixi task
(``pyforge-steward-test``) must succeed with none of them enabled.
Tachyon is a production LLM adapter plugin and must not be required in
local/CI (``required_in_ci=False``).

These plugins do not publish a PR quality-gate verdict. Warden owns that
surface; ``publish_verdict`` for a Warden-owned spec raises
``SecondVerdictError``.
"""

from __future__ import annotations

from collections.abc import Iterable, MutableMapping
from typing import Any

from pyforge.core.hooks import (
    HOOK_POINTS,
    HookPlugin,
    HookSpec,
    PluginError,
    PluginRegistry,
)

DEPLOY_PROFILE_HOOK_SPEC_NAME = "pyforge.steward.deploy_profile"
DEPLOY_PROFILE_OWNER = "steward"
DEPLOY_PROFILE_HOOK_SPEC = HookSpec(name=DEPLOY_PROFILE_HOOK_SPEC_NAME, owner=DEPLOY_PROFILE_OWNER)

PLUGIN_HARNESS = "harness"
PLUGIN_SPLUNK = "splunk"
PLUGIN_STORAGEGRID = "storagegrid"
PLUGIN_EPLX_GHA = "eplx-gha"
PLUGIN_TACHYON = "tachyon"
PLUGIN_JIRA = "jira"

DEFAULT_DEPLOY_PROFILE_IDS: tuple[str, ...] = (
    PLUGIN_HARNESS,
    PLUGIN_SPLUNK,
    PLUGIN_STORAGEGRID,
    PLUGIN_EPLX_GHA,
    PLUGIN_TACHYON,
    PLUGIN_JIRA,
)

GOLDEN_PATH_PIXI_TASK = "pyforge-steward-test"

OPTIONAL_VENDOR_TOKENS: frozenset[str] = frozenset(
    {
        "harness",
        "splunk",
        "storagegrid",
        "eplx",
        "tachyon",
        "jira",
    }
)


def _continue_around(context: MutableMapping[str, Any]) -> Any:
    nxt = context.get("next")
    if callable(nxt):
        return nxt(context)
    return context


def _record_plugin(context: MutableMapping[str, Any], plugin_id: str) -> None:
    ran = context.setdefault("ran", [])
    if plugin_id not in ran:
        ran.append(plugin_id)


class DeployProfilePlugin:
    """Shared ``around``: optional vendor adapter.

    Inject ``context["backends"][plugin_id]`` to stub a real backend.
    Without an inject this is record-only (no vendor SDK, no network).
    """

    hook_spec: str = DEPLOY_PROFILE_HOOK_SPEC_NAME
    owner: str = DEPLOY_PROFILE_OWNER
    plugin_id: str
    optional: bool = True
    required_in_ci: bool = False

    def call(self, point: str, context: MutableMapping[str, Any]) -> Any:
        if point not in HOOK_POINTS:
            raise PluginError(f"unknown hook point: {point!r}")
        if point != "around":
            return context
        backends = context.get("backends") or {}
        if self.plugin_id in backends:
            backend = backends[self.plugin_id]
            if not callable(backend):
                raise PluginError(f"backends[{self.plugin_id!r}] must be callable, got {type(backend).__name__}")
            backend(context)
        _record_plugin(context, self.plugin_id)
        return _continue_around(context)


class HarnessDeployPlugin(DeployProfilePlugin):
    plugin_id = PLUGIN_HARNESS


class SplunkDeployPlugin(DeployProfilePlugin):
    plugin_id = PLUGIN_SPLUNK


class StoragegridDeployPlugin(DeployProfilePlugin):
    plugin_id = PLUGIN_STORAGEGRID


class EplxGhaDeployPlugin(DeployProfilePlugin):
    plugin_id = PLUGIN_EPLX_GHA


class TachyonDeployPlugin(DeployProfilePlugin):
    """Production LLM adapter plugin — local/CI must not require it."""

    plugin_id = PLUGIN_TACHYON
    required_in_ci = False


class JiraDeployPlugin(DeployProfilePlugin):
    plugin_id = PLUGIN_JIRA


def default_deploy_profile_plugins() -> tuple[DeployProfilePlugin, ...]:
    return (
        HarnessDeployPlugin(),
        SplunkDeployPlugin(),
        StoragegridDeployPlugin(),
        EplxGhaDeployPlugin(),
        TachyonDeployPlugin(),
        JiraDeployPlugin(),
    )


def register_default_deploy_profile_plugins(registry: PluginRegistry) -> None:
    for plugin in default_deploy_profile_plugins():
        registry.register(plugin)


def default_deploy_profile_registry() -> PluginRegistry:
    registry = PluginRegistry()
    register_default_deploy_profile_plugins(registry)
    return registry


def select_deploy_profile_plugin(
    plugin_id: str,
    registry: PluginRegistry | None = None,
) -> HookPlugin:
    """Return one plugin on ``DEPLOY_PROFILE_HOOK_SPEC`` by ``plugin_id``.

    Unknown id raises ``PluginError``. An in-process alternate with the
    same spec and a distinct ``plugin_id`` is selected without a steward
    fork.
    """
    registry = registry if registry is not None else default_deploy_profile_registry()
    for plugin in registry.plugins:
        if plugin.hook_spec != DEPLOY_PROFILE_HOOK_SPEC_NAME:
            continue
        if getattr(plugin, "plugin_id", None) == plugin_id:
            return plugin
    raise PluginError(f"unknown deploy-profile plugin: {plugin_id!r}")


def run_golden_path(
    *,
    enabled: Iterable[str] | None = None,
    context: MutableMapping[str, Any] | None = None,
    registry: PluginRegistry | None = None,
) -> MutableMapping[str, Any]:
    """Run the Golden Path deploy-profile step.

    ``enabled`` defaults to empty: optional vendors (including Tachyon)
    are not invoked. Disabling any shipped vendor still succeeds.
    Select one plugin at a time; do not ``invoke`` every vendor.
    """
    ctx: MutableMapping[str, Any] = {} if context is None else context
    ctx.setdefault("ran", [])
    enabled_ids = frozenset() if enabled is None else frozenset(enabled)
    if registry is None:
        reg = default_deploy_profile_registry()
    else:
        reg = registry
    known = {
        getattr(plugin, "plugin_id", None)
        for plugin in reg.plugins
        if plugin.hook_spec == DEPLOY_PROFILE_HOOK_SPEC_NAME
    }
    unknown = enabled_ids - known
    if unknown:
        raise PluginError(f"unknown deploy-profile plugin: {sorted(unknown)!r}")
    for plugin_id in DEFAULT_DEPLOY_PROFILE_IDS:
        if plugin_id not in enabled_ids:
            continue
        plugin = select_deploy_profile_plugin(plugin_id, registry=reg)
        plugin.call("around", ctx)
    extra_enabled = sorted(plugin_id for plugin_id in enabled_ids if plugin_id not in DEFAULT_DEPLOY_PROFILE_IDS)
    for plugin_id in extra_enabled:
        plugin = select_deploy_profile_plugin(plugin_id, registry=reg)
        plugin.call("around", ctx)
    ctx["ok"] = True
    return ctx
