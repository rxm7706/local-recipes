"""Doctor gather/prescribe hook specs and default plugins (Story 17.1, FR-45).

Process specs live on the shared ``pyforge.core.hooks`` contract. This
module does not ship a second loader. Default plugins call today's
``atlas.gather`` / ``warden.gather`` / ``env_hygiene.gather`` and
``prescribe.*`` backends live on those modules (no import-time bind of
``gather``). They never call ``publish_verdict``: findings stay
``Finding`` / ``Prescription`` report data, not a competing PR verdict.
"""

from __future__ import annotations

from collections.abc import MutableMapping, Sequence
from pathlib import Path
from typing import Any

from pyforge.core.hooks import HookSpec, PluginRegistry

from . import prescribe
from .checks import env_hygiene
from .models import DoctorStatus, Finding, Partition, Prescription
from .sources import atlas
from .sources import warden as warden_source

GATHER_HOOK_SPEC = HookSpec(name="pyforge.doctor.gather", owner="doctor")
PRESCRIBE_HOOK_SPEC = HookSpec(name="pyforge.doctor.prescribe", owner="doctor")

# Same default axis set as ``__main__._DEFAULT_DIAGNOSE_AXES`` (Story 3.4).
# The CLI keeps the canonical name; helpers pass it through context.
_FALLBACK_DIAGNOSE_AXES: tuple[str, ...] = ("staleness", "cve")


def _action_text(pf: prescribe.PartitionedFinding) -> str:
    """Story 3.4's WHAT-TO-DO text, distinct from ``root_cause``'s WHY --
    derived from the partition, never duplicating the root-cause string.

    A clean (``DoctorStatus.OK``) ``Finding`` lands in ``ACTIONABLE`` too
    (``prescribe._partition_one``'s "every Finding lands somewhere" rule),
    but with ``reason="clean -- no remediation needed"`` -- review finding:
    this branch used to render that case as ``"address X"`` regardless,
    telling the operator to remediate something that already passed."""
    if pf.partition is Partition.ACTIONABLE:
        if pf.finding.status is DoctorStatus.OK:
            return pf.reason
        return f"address {pf.finding.check} ({pf.finding.source.value})"
    if pf.partition is Partition.BLOCKED:
        return f"blocked -- {pf.reason}"
    return f"accepted risk -- {pf.reason}"  # Partition.ACCEPTED_RISK


def _prescriptions_from_findings(
    findings: tuple[Finding, ...],
) -> tuple[Prescription, ...]:
    """Today's ``partition`` / ``rank`` / ``name_root_cause`` /
    ``recommend_safe_upgrade`` pipeline (Story 3.4). Live attribute
    lookups so CLI tests that monkeypatch ``prescribe`` still apply."""
    partitioned = prescribe.partition(findings)
    ranked = prescribe.rank(partitioned)
    rank_by_finding = {id(rp.finding): (rp.rank, rp.rank_factors) for rp in ranked}

    prescriptions: list[Prescription] = []
    for pf in partitioned:
        rank_value, rank_factors = rank_by_finding.get(id(pf.finding), (None, None))
        safe_upgrade_target, safe_upgrade_reason = prescribe.recommend_safe_upgrade(pf.finding)
        prescriptions.append(
            Prescription(
                finding_ref=f"{pf.finding.source.value}:{pf.finding.check}",
                partition=pf.partition,
                rank=rank_value,
                rank_factors=rank_factors,
                action=_action_text(pf),
                root_cause=prescribe.name_root_cause(pf.finding, findings),
                safe_upgrade_target=safe_upgrade_target,
                safe_upgrade_reason=safe_upgrade_reason,
            )
        )
    return tuple(prescriptions)


class DefaultGatherPlugin:
    """Default diagnose gather: atlas axes, plus warden + env_hygiene when
    ``directory_checks`` is true."""

    hook_spec: str = GATHER_HOOK_SPEC.name
    owner: str = GATHER_HOOK_SPEC.owner

    def call(self, point: str, context: MutableMapping[str, Any]) -> Any:
        if point == "around":
            context["findings"] = self._gather(context)
            nxt = context.get("next")
            if callable(nxt):
                return nxt(context)
        return context

    def _gather(self, context: MutableMapping[str, Any]) -> tuple[Finding, ...]:
        diagnose_target = context["diagnose_target"]
        directory_checks = bool(context.get("directory_checks"))
        axes = context["axes"] if "axes" in context else _FALLBACK_DIAGNOSE_AXES
        if axes is None:
            axes = _FALLBACK_DIAGNOSE_AXES
        findings: tuple[Finding, ...] = ()
        for axis in axes:
            findings += atlas.gather(axis, target=diagnose_target)
        if directory_checks:
            target_path = Path(diagnose_target)
            findings += warden_source.gather(target_path)
            findings += env_hygiene.gather(target_path)
        return findings


class DefaultPrescribePlugin:
    """Default prescribe actuator over already-gathered findings."""

    hook_spec: str = PRESCRIBE_HOOK_SPEC.name
    owner: str = PRESCRIBE_HOOK_SPEC.owner

    def call(self, point: str, context: MutableMapping[str, Any]) -> Any:
        if point == "around":
            findings = tuple(context["findings"])
            context["prescriptions"] = _prescriptions_from_findings(findings)
            nxt = context.get("next")
            if callable(nxt):
                return nxt(context)
        return context


def default_registry() -> PluginRegistry:
    """In-process registry with both default plugins (idempotent register)."""
    registry = PluginRegistry()
    registry.register(DefaultGatherPlugin())
    registry.register(DefaultPrescribePlugin())
    return registry


def gather_for_diagnose(
    diagnose_target: str,
    *,
    directory_checks: bool,
    axes: Sequence[str] | None = None,
) -> tuple[Finding, ...]:
    """CLI path: register defaults in-process and invoke the gather spec."""
    registry = default_registry()
    context: dict[str, Any] = {
        "diagnose_target": diagnose_target,
        "directory_checks": directory_checks,
        "axes": tuple(axes) if axes is not None else _FALLBACK_DIAGNOSE_AXES,
    }
    registry.invoke("around", context, spec_name=GATHER_HOOK_SPEC.name)
    return tuple(context["findings"])


def build_prescriptions(
    findings: tuple[Finding, ...],
) -> tuple[Prescription, ...]:
    """CLI path: register defaults in-process and invoke the prescribe spec."""
    registry = default_registry()
    context: dict[str, Any] = {"findings": findings}
    registry.invoke("around", context, spec_name=PRESCRIBE_HOOK_SPEC.name)
    return tuple(context["prescriptions"])
