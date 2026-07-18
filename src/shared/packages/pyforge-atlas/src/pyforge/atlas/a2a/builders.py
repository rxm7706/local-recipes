"""Builders that construct an A2A payload from a BSL insight or an alert condition.

These are the analytical-agent-side constructors. Both take an **injected** ``build_stamp``
(AD-17) — the caller passes the pipeline build timestamp; the builders never read
``datetime.now()``. Insight construction validates ``metric_id`` against the BSL registry
(AD-8) via the schema, so a builder can only mint an insight that references a real metric.
"""

from __future__ import annotations

from typing import Any

from pyforge.atlas.a2a.schema import AtlasAlert, AtlasInsight, Severity


def build_insight_payload(
    *,
    subject: str,
    metric_id: str,
    build_stamp: str,
    value: Any = None,
    detail: dict[str, Any] | None = None,
) -> AtlasInsight:
    """Construct an :class:`AtlasInsight` from an already-computed BSL metric.

    ``metric_id`` MUST be a ``semantic.METRIC_PROVENANCE`` key (AD-8 — the arithmetic
    stays in ``semantic/``); ``value`` is whatever that metric produced. ``build_stamp``
    is injected (AD-17).
    """
    return AtlasInsight(
        subject=subject,
        metric_id=metric_id,
        value=value,
        detail=dict(detail or {}),
        build_stamp=build_stamp,
    )


def build_alert_payload(
    *,
    subject: str,
    severity: Severity | str,
    rule: str,
    build_stamp: str,
    evidence: dict[str, Any] | None = None,
) -> AtlasAlert:
    """Construct an :class:`AtlasAlert` from a contract violation / policy breach.

    ``severity`` accepts a :class:`Severity` or its string value; ``rule`` names the
    violated rule; ``evidence`` is optional structured context. ``build_stamp`` is
    injected (AD-17).
    """
    return AtlasAlert(
        subject=subject,
        severity=Severity(severity),
        rule=rule,
        evidence=dict(evidence or {}),
        build_stamp=build_stamp,
    )
