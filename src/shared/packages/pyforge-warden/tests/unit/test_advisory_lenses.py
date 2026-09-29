"""Advisory-lens boundary test (Story 11.1).

Steward 46.2 provisioned two ``bmad-utility-skills`` for Warden to wield as
advisory lenses: ``bmad-os-review-pr`` (PR-review depth) and
``bmad-os-findings-triage`` (finding consolidation). Neither ships as a
hook-book plugin class in production code (``hooks.py`` / ``scanner_plugins.py``
stay unchanged) -- they operate at the persona/skill layer, consulted by an
agent embodying ``bmad-agent-warden`` during PR review.

This test builds a test-local stand-in plugin (mirroring
``scanner_plugins.OptionalScanPlugin``'s shape) purely to give the "cannot
alter composed status" claim a concrete, executable proof against the real
``PluginRegistry`` / ``compose()`` infrastructure -- the structural boundary
this story's Surface line calls for, not an integration of the skills'
own content.
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from typing import Any

import pytest
from pyforge.core.hooks import PluginRegistry, SecondVerdictError, publish_verdict

from pyforge.warden.hooks import PR_GATE_SCAN, PR_GATE_VERDICT, invoke_pr_gate
from pyforge.warden.models import AXIS_VULNERABILITY, Status, StatusDriver
from pyforge.warden.scanner_plugins import findings_from_plugin_context
from pyforge.warden.verdict import compose

# Fixed "real" engine-derived rungs -- stand-ins for whatever the actual
# scanner engines fed `compose()` this run. Advisory content must never
# change this set.
_BASE_RUNGS: tuple[tuple[Status, StatusDriver | None], ...] = (
    (Status.CLEAN, None),
    (
        Status.WARN,
        StatusDriver(axis=AXIS_VULNERABILITY, finding_id="warn:vulnerability:demo"),
    ),
)


class _AdvisoryLensPlugin:
    """Test-local stand-in for an advisory-lens plugin (mirrors
    ``scanner_plugins.OptionalScanPlugin``'s shape). Writes only into
    ``context["advisory_notes"]`` -- never ``context["plugin_findings"]`` --
    and is never registered on ``PR_GATE_VERDICT``."""

    hook_spec: str = PR_GATE_SCAN.name

    def __init__(self, owner: str, note: str) -> None:
        self.owner = owner
        self.note = note

    def call(self, point: str, context: MutableMapping[str, Any]) -> Any:
        if point == "around":
            notes = context.get("advisory_notes")
            if not isinstance(notes, list):
                notes = []
                context["advisory_notes"] = notes
            notes.append(self.note)
            nxt = context.get("next")
            if callable(nxt):
                return nxt(context)
        return context


class _AdvisoryLensVerdictClaim:
    """An advisory-lens plugin that attempts to claim ``PR_GATE_VERDICT`` --
    the specific theft this story's boundary test must foreclose."""

    hook_spec: str = PR_GATE_VERDICT.name
    owner: str = "bmad-os-findings-triage"

    def call(self, point: str, context: MutableMapping[str, Any]) -> Any:
        return context


def _rungs_fed_from(
    context: Mapping[str, Any],
) -> tuple[tuple[Status, StatusDriver | None], ...]:
    """In production, a plugin-contributed `Finding` never produces a rung at
    all -- `DefaultPolicy.evaluate()` builds `rungs` before
    `findings_from_plugin_context()` is even merged into `findings`, and that
    merge never touches `rungs`. This helper still runs
    `findings_from_plugin_context()` over `context` so the proof is
    end-to-end: an advisory lens's notes never reach `plugin_findings`, so
    there is nothing here for `compose()` to observe either way."""
    extra = tuple(
        (Status.INDETERMINATE, StatusDriver(axis=finding.axis, finding_id=finding.id))
        for finding in findings_from_plugin_context(context)
    )
    return _BASE_RUNGS + extra


def test_advisory_lens_contributes_a_note_never_a_finding():
    plugin = _AdvisoryLensPlugin("bmad-os-review-pr", "PR review depth note")
    registry = PluginRegistry()
    registry.register(plugin)

    context: dict[str, Any] = {}
    invoke_pr_gate(PR_GATE_SCAN, "around", context, registry=registry)

    assert context["advisory_notes"] == ["PR review depth note"]
    assert "plugin_findings" not in context
    assert findings_from_plugin_context(context) == ()


def test_compose_is_identical_with_and_without_the_advisory_lens():
    registry_without = PluginRegistry()
    context_without: dict[str, Any] = {}
    invoke_pr_gate(PR_GATE_SCAN, "around", context_without, registry=registry_without)

    plugin = _AdvisoryLensPlugin("bmad-os-findings-triage", "finding consolidation note")
    registry_with = PluginRegistry()
    registry_with.register(plugin)
    context_with: dict[str, Any] = {}
    invoke_pr_gate(PR_GATE_SCAN, "around", context_with, registry=registry_with)

    assert context_with["advisory_notes"] == ["finding consolidation note"]
    assert "plugin_findings" not in context_with

    without_plugin = compose(_rungs_fed_from(context_without))
    with_plugin = compose(_rungs_fed_from(context_with))

    expected = (
        Status.WARN,
        StatusDriver(axis=AXIS_VULNERABILITY, finding_id="warn:vulnerability:demo"),
    )
    assert without_plugin == expected
    assert with_plugin == without_plugin


def test_advisory_lens_cannot_publish_the_pr_gate_verdict():
    with pytest.raises(SecondVerdictError):
        publish_verdict(PR_GATE_VERDICT, _AdvisoryLensVerdictClaim(), "stolen")
