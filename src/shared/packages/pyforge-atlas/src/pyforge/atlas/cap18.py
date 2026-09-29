"""CAP-18 audit: map live Kedro hooks onto ``pyforge.core.hooks`` (FR-43).

Kedro remains the runtime (``settings.HOOKS`` and the four ``@hook_impl``
backends are unchanged). This module is a registration/audit surface only:
named atlas process specs, an explicit method map (mapped or N/A-with-reason),
and thin ``HookPlugin`` wrappers so today's backends load as default plugins
on the canonical ``pyforge.core.hooks`` group.

``call()`` does not dispatch into Kedro and does not require a live session.
``around`` is a documented no-op (Kedro has no around; wrapping the hook
manager would rebuild Kedro). ``on_pipeline_error`` / ``on_node_error`` stay
on the Kedro backends — they are not FR-43 points.
"""

from __future__ import annotations

from collections.abc import MutableMapping
from dataclasses import dataclass
from typing import Any

from pyforge.core.hooks import HOOK_POINTS, HookSpec, PluginError

from pyforge.atlas.admission import RunAdmissionHooks
from pyforge.atlas.hooks import ProjectHooks
from pyforge.atlas.observability import AtlasObservabilityHooks
from pyforge.atlas.validation import DataValidationHooks

ATLAS_OWNER = "atlas"

CATALOG_HOOK_SPEC = HookSpec(name="pyforge.atlas.catalog", owner=ATLAS_OWNER)
PIPELINE_HOOK_SPEC = HookSpec(name="pyforge.atlas.pipeline", owner=ATLAS_OWNER)
NODE_HOOK_SPEC = HookSpec(name="pyforge.atlas.node", owner=ATLAS_OWNER)

ATLAS_HOOK_SPECS: tuple[HookSpec, ...] = (
    CATALOG_HOOK_SPEC,
    PIPELINE_HOOK_SPEC,
    NODE_HOOK_SPEC,
)

AROUND_NA_REASON = "Kedro has no around hook; wrapping the Kedro hook manager would rebuild Kedro"

_NA_UNUSED_DATASET = (
    "DatasetSpecs load/save hooks are unused in atlas: TTL injects on "
    "after_catalog_created and validation/observability run on node hooks, "
    "not before/after_dataset_loaded or *_saved"
)
_NA_UNUSED_CONTEXT = "after_context_created is unused in atlas (TTL injection uses after_catalog_created)"
_NA_ERROR_NOT_FR43 = (
    "on_*_error is a Kedro lifecycle hook, not an FR-43 point (HOOK_POINTS is "
    "before/after/around only); it stays on the existing Kedro backend"
)


@dataclass(frozen=True)
class KedroHookMapRow:
    """One Kedro 1.5 ``hooks.specs`` method, mapped or N/A-with-reason."""

    kedro_spec: str
    kedro_method: str
    fr43_point: str | None
    hook_spec: str | None
    backends: tuple[type, ...]
    na_reason: str | None = None

    def mapped(self) -> bool:
        return self.na_reason is None


KEDRO_HOOK_MAP: tuple[KedroHookMapRow, ...] = (
    KedroHookMapRow(
        kedro_spec="DataCatalogSpecs",
        kedro_method="after_catalog_created",
        fr43_point="after",
        hook_spec=CATALOG_HOOK_SPEC.name,
        backends=(ProjectHooks,),
    ),
    KedroHookMapRow(
        kedro_spec="DatasetSpecs",
        kedro_method="before_dataset_loaded",
        fr43_point=None,
        hook_spec=None,
        backends=(),
        na_reason=_NA_UNUSED_DATASET,
    ),
    KedroHookMapRow(
        kedro_spec="DatasetSpecs",
        kedro_method="after_dataset_loaded",
        fr43_point=None,
        hook_spec=None,
        backends=(),
        na_reason=_NA_UNUSED_DATASET,
    ),
    KedroHookMapRow(
        kedro_spec="DatasetSpecs",
        kedro_method="before_dataset_saved",
        fr43_point=None,
        hook_spec=None,
        backends=(),
        na_reason=_NA_UNUSED_DATASET,
    ),
    KedroHookMapRow(
        kedro_spec="DatasetSpecs",
        kedro_method="after_dataset_saved",
        fr43_point=None,
        hook_spec=None,
        backends=(),
        na_reason=_NA_UNUSED_DATASET,
    ),
    KedroHookMapRow(
        kedro_spec="KedroContextSpecs",
        kedro_method="after_context_created",
        fr43_point=None,
        hook_spec=None,
        backends=(),
        na_reason=_NA_UNUSED_CONTEXT,
    ),
    KedroHookMapRow(
        kedro_spec="NodeSpecs",
        kedro_method="before_node_run",
        fr43_point="before",
        hook_spec=NODE_HOOK_SPEC.name,
        backends=(AtlasObservabilityHooks,),
    ),
    KedroHookMapRow(
        kedro_spec="NodeSpecs",
        kedro_method="after_node_run",
        fr43_point="after",
        hook_spec=NODE_HOOK_SPEC.name,
        backends=(AtlasObservabilityHooks, DataValidationHooks),
    ),
    KedroHookMapRow(
        kedro_spec="NodeSpecs",
        kedro_method="on_node_error",
        fr43_point=None,
        hook_spec=None,
        backends=(AtlasObservabilityHooks,),
        na_reason=_NA_ERROR_NOT_FR43,
    ),
    KedroHookMapRow(
        kedro_spec="PipelineSpecs",
        kedro_method="before_pipeline_run",
        fr43_point="before",
        hook_spec=PIPELINE_HOOK_SPEC.name,
        backends=(AtlasObservabilityHooks, RunAdmissionHooks),
    ),
    KedroHookMapRow(
        kedro_spec="PipelineSpecs",
        kedro_method="after_pipeline_run",
        fr43_point="after",
        hook_spec=PIPELINE_HOOK_SPEC.name,
        backends=(AtlasObservabilityHooks, RunAdmissionHooks),
    ),
    KedroHookMapRow(
        kedro_spec="PipelineSpecs",
        kedro_method="on_pipeline_error",
        fr43_point=None,
        hook_spec=None,
        backends=(AtlasObservabilityHooks, RunAdmissionHooks),
        na_reason=_NA_ERROR_NOT_FR43,
    ),
)

SETTINGS_HOOK_BACKENDS: tuple[type, ...] = (
    ProjectHooks,
    AtlasObservabilityHooks,
    DataValidationHooks,
    RunAdmissionHooks,
)


class _AtlasHookPlugin:
    """Thin FR-43 wrapper. Does not replace Kedro ``@hook_impl`` dispatch."""

    hook_spec: str
    owner: str = ATLAS_OWNER
    backend_class: type

    def __init__(self, backend: object | None = None) -> None:
        self.backend = backend if backend is not None else self.backend_class()

    def call(self, point: str, context: MutableMapping[str, Any]) -> Any:
        if point not in HOOK_POINTS:
            raise PluginError(f"unknown hook point: {point!r}")
        if point == "around":
            nxt = context.get("next")
            if callable(nxt):
                return nxt(context)
            return context
        return context


class CatalogTtlPlugin(_AtlasHookPlugin):
    hook_spec = CATALOG_HOOK_SPEC.name
    backend_class = ProjectHooks


class PipelineObservabilityPlugin(_AtlasHookPlugin):
    hook_spec = PIPELINE_HOOK_SPEC.name
    backend_class = AtlasObservabilityHooks


class NodeObservabilityPlugin(_AtlasHookPlugin):
    hook_spec = NODE_HOOK_SPEC.name
    backend_class = AtlasObservabilityHooks


class NodeValidationPlugin(_AtlasHookPlugin):
    hook_spec = NODE_HOOK_SPEC.name
    backend_class = DataValidationHooks


class PipelineAdmissionPlugin(_AtlasHookPlugin):
    hook_spec = PIPELINE_HOOK_SPEC.name
    backend_class = RunAdmissionHooks


DEFAULT_PLUGIN_CLASSES: tuple[type, ...] = (
    CatalogTtlPlugin,
    PipelineObservabilityPlugin,
    NodeObservabilityPlugin,
    NodeValidationPlugin,
    PipelineAdmissionPlugin,
)
