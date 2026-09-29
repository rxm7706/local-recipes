"""Unit tests for ``pyforge.marshal.seed.verbs.explain`` (Story 11.6)."""

from __future__ import annotations

import argparse
import json

import pytest

from pyforge.marshal.cli import seed as seed_cli
from pyforge.marshal.seed.errors import UsageError
from pyforge.marshal.seed.model.manifest import (
    AppliesTo,
    ArtifactClass,
    Manifest,
    ManifestEntry,
    Region,
)
from pyforge.marshal.seed.model.version import ModelVersion
from pyforge.marshal.seed.verbs.explain import (
    render_explain_text,
    resolve_entry,
    run_explain,
)

_VERSION = ModelVersion.parse("1.0.0")


def _manifest(*entries: ManifestEntry) -> Manifest:
    return Manifest(model_version=_VERSION, never_write=(), entries=tuple(entries))


def _hybrid(entry_id: str, path: str, region_name: str, anchor: str) -> ManifestEntry:
    return ManifestEntry(
        id=entry_id,
        artifact_class=ArtifactClass.HYBRID_MANAGED_REGION,
        path=path,
        applies_to=AppliesTo.BOTH,
        rationale="hybrid rationale",
        format="html",
        regions=(Region(name=region_name, anchor=(anchor,)),),
    )


def test_explain_by_id_includes_class_rationale_and_update_behavior():
    manifest = _manifest(
        ManifestEntry(
            id="whole",
            artifact_class=ArtifactClass.COPIED_MANAGED,
            path="WHOLE.md",
            applies_to=AppliesTo.BOTH,
            rationale="managed rationale",
        )
    )

    report = run_explain(manifest, "whole")

    assert report.artifact_id == "whole"
    assert report.artifact_class == "copied-managed"
    assert report.rationale == "managed rationale"
    assert report.update_behavior == "regenerated wholesale"
    assert report.regions == ()


def test_explain_by_path_resolves_entry():
    manifest = _manifest(_hybrid("agents-md", "AGENTS.md", "tiers", "## The tiers"))

    report = run_explain(manifest, "AGENTS.md")

    assert report.artifact_id == "agents-md"
    assert len(report.regions) == 1
    assert report.regions[0]["name"] == "tiers"
    assert report.regions[0]["anchor"] == ["## The tiers"]


def test_explain_hybrid_includes_regions_and_anchors_in_text():
    manifest = _manifest(_hybrid("agents-md", "AGENTS.md", "tiers", "## The tiers"))

    text = render_explain_text(run_explain(manifest, "agents-md"))

    assert "regions:" in text
    assert "tiers: anchor ## The tiers" in text


def test_explain_json_matches_text_fields():
    manifest = _manifest(_hybrid("agents-md", "AGENTS.md", "tiers", "## The tiers"))

    payload = run_explain(manifest, "agents-md").to_json_dict()

    assert payload["artifact_id"] == "agents-md"
    assert payload["class"] == "hybrid-managed-region"
    assert payload["regions"][0]["name"] == "tiers"


def test_unknown_artifact_lists_near_matches():
    manifest = _manifest(
        _hybrid("agents-md", "AGENTS.md", "tiers", "## The tiers"),
        ManifestEntry(
            id="agents-json",
            artifact_class=ArtifactClass.COPIED_MANAGED,
            path="AGENTS.json",
            applies_to=AppliesTo.BOTH,
            rationale="other",
        ),
    )

    with pytest.raises(UsageError) as exc:
        resolve_entry(manifest, "agent-md")

    assert "Near matches" in str(exc.value)
    assert "agents-md" in str(exc.value)


def test_explain_cli_json_flag(capsys):
    manifest = _manifest(
        ManifestEntry(
            id="whole",
            artifact_class=ArtifactClass.COPIED_MANAGED,
            path="WHOLE.md",
            applies_to=AppliesTo.BOTH,
            rationale="managed rationale",
        )
    )
    args = argparse.Namespace(artifact="whole", json=True)

    code = seed_cli.run_explain(args, manifest=manifest)

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["verb"] == "explain"
    assert payload["ok"] is True
    assert payload["result"]["artifact_id"] == "whole"


def test_explain_cli_unknown_exits_usage_error(capsys):
    manifest = _manifest(
        ManifestEntry(
            id="whole",
            artifact_class=ArtifactClass.COPIED_MANAGED,
            path="WHOLE.md",
            applies_to=AppliesTo.BOTH,
            rationale="managed rationale",
        )
    )
    args = argparse.Namespace(artifact="missing-id", json=False)

    code = seed_cli.run_explain(args, manifest=manifest)

    assert code == UsageError.exit_code
    assert "unknown artifact" in capsys.readouterr().out
