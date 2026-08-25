"""Warden PR-gate hook book (Story 9.1, FR-43 consumer).

Publishes named ``HookSpec``s for scan / aggregate / verdict. Plugins
register through ``pyforge.core.hooks`` only — this module does not ship a
second loader. Spec owner is ``"warden"`` for every PR-gate spec; scanner
plugins may attach to scan/aggregate by matching ``hook_spec`` and must
not own the verdict spec.

``publish_pr_gate_verdict`` uses an in-tree owner plugin so only Warden
can publish the gate verdict. ``verdict.py`` stays sole owner of the
lattice + ``exit_code_for``; hooks do not project exits.
"""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

from pyforge.core.hooks import (
    ENTRY_POINT_GROUP,
    HOOK_POINTS,
    HookPlugin,
    HookSpec,
    PluginError,
    PluginRegistry,
    SecondVerdictError,
    publish_verdict,
)

PR_GATE_SCAN = HookSpec(name="pyforge.warden.pr_gate.scan", owner="warden")
PR_GATE_AGGREGATE = HookSpec(name="pyforge.warden.pr_gate.aggregate", owner="warden")
PR_GATE_VERDICT = HookSpec(name="pyforge.warden.pr_gate.verdict", owner="warden")

PR_GATE_HOOK_SPECS: tuple[HookSpec, ...] = (
    PR_GATE_SCAN,
    PR_GATE_AGGREGATE,
    PR_GATE_VERDICT,
)

_DEFAULT_REGISTRY = PluginRegistry()


class WardenVerdictOwner:
    """Identity for ``publish_verdict`` on ``PR_GATE_VERDICT``. Not a scanner."""

    hook_spec: str = PR_GATE_VERDICT.name
    owner: str = PR_GATE_VERDICT.owner

    def call(self, point: str, context: MutableMapping[str, Any]) -> Any:
        return context


def pr_gate_registry() -> PluginRegistry:
    """The default in-process PR-gate registry (empty until ``register`` /
    ``load_entry_points``). Callers that need isolation pass their own
    ``PluginRegistry`` to ``invoke_pr_gate``."""
    return _DEFAULT_REGISTRY


def invoke_pr_gate(
    spec: HookSpec,
    point: str,
    context: MutableMapping[str, Any] | None = None,
    *,
    registry: PluginRegistry | None = None,
) -> list[Any]:
    """Invoke plugins registered for ``spec`` at ``point``.

    Delegates to ``PluginRegistry.invoke(..., spec_name=spec.name)`` so
    core's dummy (``pyforge.core.example``) never runs on the PR gate.
    Unknown ``spec`` (not in ``PR_GATE_HOOK_SPECS``) or unknown ``point``
    raises ``PluginError`` from core. Empty registry returns ``[]``.
    """
    if spec not in PR_GATE_HOOK_SPECS:
        raise PluginError(f"unknown PR-gate spec: {spec.name!r}")
    active = pr_gate_registry() if registry is None else registry
    ctx: MutableMapping[str, Any] = {} if context is None else context
    return active.invoke(point, ctx, spec_name=spec.name)


def publish_pr_gate_verdict(verdict: object) -> object:
    """Publish the PR-gate verdict as Warden. Owner-matched only."""
    return publish_verdict(PR_GATE_VERDICT, WardenVerdictOwner(), verdict)


__all__ = (
    "ENTRY_POINT_GROUP",
    "HOOK_POINTS",
    "HookPlugin",
    "HookSpec",
    "PR_GATE_AGGREGATE",
    "PR_GATE_HOOK_SPECS",
    "PR_GATE_SCAN",
    "PR_GATE_VERDICT",
    "PluginError",
    "PluginRegistry",
    "SecondVerdictError",
    "WardenVerdictOwner",
    "invoke_pr_gate",
    "pr_gate_registry",
    "publish_pr_gate_verdict",
    "publish_verdict",
)
