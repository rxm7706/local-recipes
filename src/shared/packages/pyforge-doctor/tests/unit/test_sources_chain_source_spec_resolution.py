"""Story 21.5: ``source_spec`` resolves from the owning project root."""

from __future__ import annotations

from pathlib import Path

from pyforge.doctor.sources import chain

# Doctor Story 58.1 (spec-pyforge-doctor:CAP-97): no test here reads this repository, so the module runs in the
# package half; the tests that do run in test_live_sources_chain_source_spec_resolution.py.

_HERALD_DW_FU_15_1_SOURCE_SPEC = (
    "`planning-artifacts/specs/spec-15-1-template-parse-then-fill-produces-a-genuinely-editable-deck.md`"
)
_HERALD_SPEC_REL = "planning-artifacts/specs/spec-15-1-template-parse-then-fill-produces-a-genuinely-editable-deck.md"


def _project_dir(target: Path, project: str) -> Path:
    return target / "_bmad-output" / "projects" / project


def test_herald_dw_fu_15_1_project_relative_source_spec_resolves(tmp_path: Path) -> None:
    """I/O matrix: herald ``DW-FU-15-1`` project-relative ``source_spec``."""
    spec_path = _project_dir(tmp_path, "pyforge-herald") / _HERALD_SPEC_REL
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text("# spec\n", encoding="utf-8")

    resolution = chain.resolve_source_spec(
        _HERALD_DW_FU_15_1_SOURCE_SPEC,
        repo_root=tmp_path,
        project="pyforge-herald",
    )

    assert resolution.status is chain.SourceSpecResolutionStatus.PRESENT
    assert resolution.resolution_basis == "project_root"
    assert resolution.resolved_path == spec_path.resolve()
    assert chain.source_spec_verdict_phrase(resolution) == "source_spec present"
    assert chain.source_spec_mechanical_still_open_eligible(resolution) is False


def test_repo_root_relative_source_spec_still_resolves(tmp_path: Path) -> None:
    """I/O matrix: repo-root-relative ``source_spec`` (existing working case)."""
    # a join: a bare literal naming the tracked spec would read as a live read (steward's scan_strings)
    rel = "/".join(("_bmad-output", "projects", "pyforge-herald", _HERALD_SPEC_REL))
    spec_path = tmp_path / rel
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text("# spec\n", encoding="utf-8")

    resolution = chain.resolve_source_spec(
        f"`{rel}`",
        repo_root=tmp_path,
        project="pyforge-herald",
    )

    assert resolution.status is chain.SourceSpecResolutionStatus.PRESENT
    assert resolution.resolution_basis == "repo_root"
    assert resolution.resolved_path == spec_path.resolve()


def test_genuinely_absent_source_spec_reports_absent(tmp_path: Path) -> None:
    """I/O matrix: neither project-root nor repo-root resolution finds the file."""
    resolution = chain.resolve_source_spec(
        "`planning-artifacts/specs/spec-missing-entirely.md`",
        repo_root=tmp_path,
        project="pyforge-herald",
    )

    assert resolution.status is chain.SourceSpecResolutionStatus.ABSENT
    assert resolution.resolved_path is None
    assert chain.source_spec_verdict_phrase(resolution) == "spec absent at HEAD"
    assert chain.source_spec_mechanical_still_open_eligible(resolution) is True


def test_project_relative_without_project_context_is_not_located(
    tmp_path: Path,
) -> None:
    """A project-relative path with no ``project`` is a resolver miss, not absent."""
    spec_path = _project_dir(tmp_path, "pyforge-herald") / _HERALD_SPEC_REL
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text("# spec\n", encoding="utf-8")

    resolution = chain.resolve_source_spec(
        _HERALD_DW_FU_15_1_SOURCE_SPEC,
        repo_root=tmp_path,
        project=None,
    )

    assert resolution.status is chain.SourceSpecResolutionStatus.NOT_LOCATED
    assert chain.source_spec_verdict_phrase(resolution) == ("spec not located by this resolver")
    assert chain.source_spec_mechanical_still_open_eligible(resolution) is False


def test_tier3_source_spec_is_neither_present_nor_absent(tmp_path: Path) -> None:
    tier3_rel = "_bmad-output/projects/pyforge-marshal/implementation-artifacts/spec-1-2-story-identity.md"
    spec_path = tmp_path / tier3_rel
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text("# tier3\n", encoding="utf-8")

    resolution = chain.resolve_source_spec(
        f"`{tier3_rel}`",
        repo_root=tmp_path,
        project="pyforge-marshal",
    )

    assert resolution.status is chain.SourceSpecResolutionStatus.TIER3
    assert chain.source_spec_verdict_phrase(resolution) == ("source_spec is Tier-3 (gitignored, not in clone)")
    assert chain.source_spec_mechanical_still_open_eligible(resolution) is False
