"""Default + optional scanner plugins on the PR-gate book (Story 9.2).

Wraps today's ``register_engine`` factories as the default plugin bundle.
Optional commercial scanners are stubs (no vendor SDKs). ``tea-test-review``
(Story 11.2) is the one optional scanner that is real production wiring,
not a stub -- it shells out to a runnable CLI (steward 46.3's pixi task)
and appends a non-``Finding`` advisory note, never a stub finding; see
``tea_advisory.py``. Plugins register through ``pyforge.core.hooks`` only;
this module does not ship a second loader and does not
``load_entry_points()`` the shared group (other stations' plugins would
load).

``select_scanner_plugins`` returns defaults plus only *enabled* optionals.
A missing or not-enabled optional is omitted, not an error
(``OPTIONAL_ABSENT_IS_NOT_FAILURE`` — Story 9.3 owns the
fail-if-absence-is-failure CI test).
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping, MutableMapping, Sequence
from typing import Any

from pyforge.core.hooks import PluginError, PluginRegistry

from .engines import (
    CurrencyEngine,
    DeptryEngine,
    LicenseEngine,
    NullEngine,
    OsvEngine,
    engine_factories,
)
from .hooks import PR_GATE_SCAN
from .interfaces import Engine
from .models import AXIS_INGESTION, Finding
from .tea_advisory import TeaAdvisoryScanPlugin

OPTIONAL_SCANNER_IDS: tuple[str, ...] = (
    "checkmarx",
    "sonar",
    "blackduck",
    "ghas",
    "profile-local",
    # Story 11.2: tea-test-review is NOT an OptionalScanPlugin subclass (it
    # appends to context["advisory_notes"], never context["plugin_findings"]
    # -- a stub Finding would be a lie about what an advisory lens does), so
    # TeaAdvisoryScanPlugin is registered directly in
    # scanner_plugin_registry() below rather than joining OPTIONAL_SCAN_PLUGINS'
    # homogeneous tuple. Its scanner_id is still listed here so
    # select_scanner_plugins()'s enable/omit-not-error machinery covers it.
    "tea-test-review",
)

OPTIONAL_SCANNER_ID_SET: frozenset[str] = frozenset(OPTIONAL_SCANNER_IDS)

# Story 9.3 hook: omit-not-error. The fail-if-absence-is-failure CI test
# lives in tests/unit/test_default_warden_without_checkmarx.py.
OPTIONAL_ABSENT_IS_NOT_FAILURE: bool = True

WARDEN_OPTIONAL_SCANNERS_ENV = "WARDEN_OPTIONAL_SCANNERS"


class EngineScanPlugin:
    """Default-bundle wrapper: holds the same factory ``register_engine``
    listed. Distinct subclasses so ``PluginRegistry`` uniqueness
    ``(type, hook_spec, owner)`` keeps every engine."""

    hook_spec: str = PR_GATE_SCAN.name
    owner: str = "warden"
    is_default: bool = True
    scanner_id: str
    factory: Callable[[], Engine]

    def call(self, point: str, context: MutableMapping[str, Any]) -> Any:
        if point == "around":
            nxt = context.get("next")
            if callable(nxt):
                return nxt(context)
        return context


class NullScanPlugin(EngineScanPlugin):
    scanner_id = "null"
    factory = NullEngine


class DeptryScanPlugin(EngineScanPlugin):
    scanner_id = "deptry"
    factory = DeptryEngine


class OsvScanPlugin(EngineScanPlugin):
    scanner_id = "osv"
    factory = OsvEngine


class LicenseScanPlugin(EngineScanPlugin):
    scanner_id = "license"
    factory = LicenseEngine


class CurrencyScanPlugin(EngineScanPlugin):
    scanner_id = "currency"
    factory = CurrencyEngine


DEFAULT_SCAN_PLUGINS: tuple[type[EngineScanPlugin], ...] = (
    NullScanPlugin,
    DeptryScanPlugin,
    OsvScanPlugin,
    LicenseScanPlugin,
    CurrencyScanPlugin,
)


def _plugin_for_factory(factory: Callable[[], Engine]) -> EngineScanPlugin:
    """Wrap one live ``register_engine`` factory. A distinct subclass keeps
    ``PluginRegistry`` uniqueness ``(type, hook_spec, owner)`` from
    collapsing the bundle."""
    raw_name = getattr(factory, "__name__", "engine")
    scanner_id = raw_name.removesuffix("Engine").lower() or "engine"
    cls = type(
        f"{raw_name}ScanPlugin",
        (EngineScanPlugin,),
        {"scanner_id": scanner_id, "factory": factory},
    )
    return cls()


def stub_finding_dict(scanner_id: str) -> dict[str, Any]:
    """One schema-legal finding dict an optional stub may append."""
    return {
        "id": f"indeterminate:{scanner_id}:plugin",
        "axis": AXIS_INGESTION,
        "message": (f"optional scanner {scanner_id} contributed a stub finding"),
        "subject": scanner_id,
        "severity": None,
    }


class OptionalScanPlugin:
    """Named commercial/profile stub. Never calls ``publish_verdict``."""

    hook_spec: str = PR_GATE_SCAN.name
    is_default: bool = False
    scanner_id: str

    def __init__(self, scanner_id: str) -> None:
        self.scanner_id = scanner_id
        self.owner = scanner_id

    def call(self, point: str, context: MutableMapping[str, Any]) -> Any:
        if point == "around":
            enabled = context.get("enabled_optional") or ()
            if isinstance(enabled, str):
                enabled = (enabled,)
            if self.scanner_id in enabled:
                findings = context.get("plugin_findings")
                if not isinstance(findings, list):
                    findings = []
                    context["plugin_findings"] = findings
                findings.append(stub_finding_dict(self.scanner_id))
            nxt = context.get("next")
            if callable(nxt):
                return nxt(context)
        return context


class CheckmarxScanPlugin(OptionalScanPlugin):
    def __init__(self) -> None:
        super().__init__("checkmarx")


class SonarScanPlugin(OptionalScanPlugin):
    def __init__(self) -> None:
        super().__init__("sonar")


class BlackduckScanPlugin(OptionalScanPlugin):
    def __init__(self) -> None:
        super().__init__("blackduck")


class GhasScanPlugin(OptionalScanPlugin):
    def __init__(self) -> None:
        super().__init__("ghas")


class ProfileLocalScanPlugin(OptionalScanPlugin):
    def __init__(self) -> None:
        super().__init__("profile-local")


OPTIONAL_SCAN_PLUGINS: tuple[type[OptionalScanPlugin], ...] = (
    CheckmarxScanPlugin,
    SonarScanPlugin,
    BlackduckScanPlugin,
    GhasScanPlugin,
    ProfileLocalScanPlugin,
)


def scanner_plugin_registry() -> PluginRegistry:
    """Fresh in-tree registry of default + optional scanner plugins.

    Does not ``load_entry_points()`` the shared ``pyforge.core.hooks``
    group (core's dummy and other stations would load).
    """
    registry = PluginRegistry()
    # Wrap the live ``register_engine`` list so extras/test replacements
    # still reach the CLI thread pool. Named DEFAULT_SCAN_PLUGINS stay
    # the entry-point targets.
    for factory in engine_factories():
        registry.register(_plugin_for_factory(factory))
    for cls in OPTIONAL_SCAN_PLUGINS:
        registry.register(cls())
    # Story 11.2: registered directly (not via OPTIONAL_SCAN_PLUGINS -- see
    # the OPTIONAL_SCANNER_IDS comment above). No injected runner here: a
    # shipped registry always resolves the real tea-test-review binary.
    registry.register(TeaAdvisoryScanPlugin())
    return registry


def enabled_optional_from_environ(
    environ: Mapping[str, str] | None = None,
) -> tuple[str, ...]:
    """Comma-separated ids from ``WARDEN_OPTIONAL_SCANNERS``. Empty → ``()``."""
    env = os.environ if environ is None else environ
    raw = env.get(WARDEN_OPTIONAL_SCANNERS_ENV, "")
    if not raw.strip():
        return ()
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def select_scanner_plugins(
    enabled_optional: Sequence[str] = (),
    *,
    registry: PluginRegistry | None = None,
) -> tuple[Any, ...]:
    """Defaults plus only enabled optionals. Unknown id → ``PluginError``.

    A named optional that is not in the registry is omitted (not an
    error) when ``OPTIONAL_ABSENT_IS_NOT_FAILURE`` is true.
    """
    if enabled_optional is None:
        enabled_optional = ()
    elif isinstance(enabled_optional, str):
        enabled_optional = (enabled_optional,)
    unknown = [scanner_id for scanner_id in enabled_optional if scanner_id not in OPTIONAL_SCANNER_ID_SET]
    if unknown:
        raise PluginError(f"unknown optional scanner id: {unknown[0]!r}")
    enabled = frozenset(enabled_optional)
    source = scanner_plugin_registry() if registry is None else registry
    present_ids = {getattr(plugin, "scanner_id", plugin.owner) for plugin in source.plugins}
    if not OPTIONAL_ABSENT_IS_NOT_FAILURE:
        missing = sorted(enabled - present_ids)
        if missing:
            raise PluginError(f"optional scanner absent: {missing[0]!r}")
    selected: list[Any] = []
    for plugin in source.plugins:
        if getattr(plugin, "is_default", False):
            selected.append(plugin)
            continue
        scanner_id = getattr(plugin, "scanner_id", plugin.owner)
        if scanner_id in enabled:
            selected.append(plugin)
    return tuple(selected)


def default_engine_factories(plugins: Sequence[Any]) -> tuple[Callable[[], Engine], ...]:
    """Factory objects from default plugins, in selection order."""
    return tuple(plugin.factory for plugin in plugins if getattr(plugin, "is_default", False))


def coerce_plugin_finding(raw: object) -> Finding:
    if isinstance(raw, Finding):
        return raw
    if not isinstance(raw, Mapping):
        raise PluginError(f"plugin finding is not a mapping: {raw!r}")
    try:
        return Finding(
            id=str(raw["id"]),
            axis=str(raw["axis"]),
            message=str(raw["message"]),
            subject=raw.get("subject"),
            severity=raw.get("severity"),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise PluginError(f"plugin finding is not a Finding: {exc}") from exc


def findings_from_plugin_context(
    context: Mapping[str, Any],
) -> tuple[Finding, ...]:
    raw_list = context.get("plugin_findings") or ()
    return tuple(coerce_plugin_finding(item) for item in raw_list)


def merge_plugin_findings(
    findings: Sequence[Finding],
    extra: Sequence[Finding],
) -> tuple[Finding, ...]:
    """Append extras that do not collide on ``Finding.id``."""
    existing = {finding.id for finding in findings}
    merged = list(findings)
    for finding in extra:
        if finding.id in existing:
            continue
        merged.append(finding)
        existing.add(finding.id)
    return tuple(merged)
