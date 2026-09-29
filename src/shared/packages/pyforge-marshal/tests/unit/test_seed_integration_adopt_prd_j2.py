"""Integration test for PRD Journey J2 -- "Adopt the model into a repo that
already ships" (``prd-pyforge-marshal-2026-07-25/prd.md`` § J2, cited
verbatim by Story 10.6's own epics AC): "A team has a working data-platform
monorepo -- CI, releases, an existing ``CLAUDE.md``, and a ``docs/adr/``
convention they like. They run ``marshal seed adopt`` ... Genesis prints a
plan: N artifacts absent (will create), M present-conformant (skip), 1
present-divergent (``CLAUDE.md`` -- will insert a managed region at an
anchor, leaving all existing content), 1 present-legacy (``docs/adr/`` --
recorded, preserved, untouched). Nothing has been written. They review the
plan ..., run ``marshal seed adopt --apply``, and their build still works
because Genesis never touched a file it did not name."

This is the one test in this story's suite that deliberately exercises the
REAL production defaults end to end -- no injected ``commit=``, no injected
``template_path=``: every materialized artifact here is a
``hybrid-managed-region`` entry, whose body is read from the REAL packaged
``seed/templates/files/*.j2`` fragments (``verbs/adopt.py``'s own
``_region_body_from_template``, never routed through ``engine.copier.
materialize()`` -- see that module's docstring for why a whole-file class
is deliberately NOT exercised here: the packaged template tree ships no
whole-file content yet, a known, named, pre-existing gap this story does not
close). The narrative's numeric detail ("9 absent", "3 present-conformant")
is illustrative, not a literal fixture requirement (the Code Map's own,
narrower bullet: "an existing CLAUDE.md ... and a legacy convention ...
adopts cleanly ... build-relevant files untouched") -- this file covers
exactly that: one present-divergent hybrid host (``CLAUDE.md``, existing
content preserved, a region inserted), one absent hybrid entry (created
fresh), one present-legacy artifact (recorded, byte-identical before and
after), one referenced entry (present-conformant, never inspected), and an
unrelated "build-relevant" file (``pyproject.toml``, not named by the
manifest at all) proving Genesis "never touched a file it did not name"."""

from __future__ import annotations

import subprocess
from pathlib import Path

from pyforge.marshal.seed.model.manifest import (
    AppliesTo,
    ArtifactClass,
    Manifest,
    ManifestEntry,
    Region,
)
from pyforge.marshal.seed.model.version import ModelVersion
from pyforge.marshal.seed.regions.markers import RegionFormat
from pyforge.marshal.seed.state import read_state
from pyforge.marshal.seed.verbs.adopt import run_adopt

_VERSION = ModelVersion.parse("1.0.0")

_EXISTING_CLAUDE_MD = (
    "# CLAUDE.md\n\n"
    "This file provides guidance to Claude Code when working in this repo.\n\n"
    "## Our own build conventions\n\n"
    "Run `make test` before every commit. Deploy via `make release`.\n"
)

_EXISTING_ADR = "# ADR 0001: Use PostgreSQL\n\nWe chose PostgreSQL for its JSONB support and mature tooling.\n"

_BUILD_FILE = '[project]\nname = "data-platform"\nversion = "3.2.1"\n'


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    return result


def _prd_j2_manifest() -> Manifest:
    return Manifest(
        model_version=_VERSION,
        never_write=(),
        entries=(
            # present-divergent: existing CLAUDE.md, a managed region is
            # inserted, everything else in the file is left alone.
            ManifestEntry(
                id="claude-md",
                artifact_class=ArtifactClass.HYBRID_MANAGED_REGION,
                path="CLAUDE.md",
                applies_to=AppliesTo.BOTH,
                rationale="the neutral contract's tier core",
                format=RegionFormat.HTML,
                regions=(Region(name="tiers", anchor=("### Spec-driven, framework-neutral layout",)),),
            ),
            # absent: a fresh hybrid artifact this team never had before.
            ManifestEntry(
                id="readme-badge",
                artifact_class=ArtifactClass.HYBRID_MANAGED_REGION,
                path="README.md",
                applies_to=AppliesTo.BOTH,
                rationale="a badge, opt-in and off by default",
                format=RegionFormat.HTML,
                regions=(Region(name="model-badge", anchor=("<top>",)),),
            ),
            # present-legacy: the docs/adr/ convention this team already
            # has and likes -- recorded, never modified.
            ManifestEntry(
                id="legacy-adr",
                artifact_class=ArtifactClass.COPIED_MANAGED,
                path="docs/adr/0001-use-postgresql.md",
                applies_to=AppliesTo.BOTH,
                rationale="test",
                legacy_of="claude-md",
            ),
            # present-conformant: not materialized at all, never inspected.
            ManifestEntry(
                id="bmad-method",
                artifact_class=ArtifactClass.REFERENCED,
                path="n/a",
                applies_to=AppliesTo.BOTH,
                rationale="upstream product",
                pin=">=6.10.0",
            ),
        ),
    )


def test_prd_j2_adopt_a_repo_that_already_ships(tmp_path: Path) -> None:
    repo = tmp_path
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")

    (repo / "CLAUDE.md").write_text(_EXISTING_CLAUDE_MD, encoding="utf-8")
    (repo / "docs" / "adr").mkdir(parents=True)
    (repo / "docs" / "adr" / "0001-use-postgresql.md").write_text(_EXISTING_ADR, encoding="utf-8")
    (repo / "pyproject.toml").write_text(_BUILD_FILE, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "existing data-platform monorepo")

    manifest = _prd_j2_manifest()

    # --- dry-run: "Genesis prints a plan ... Nothing has been written." ----
    dry_run = run_adopt(repo, manifest, confirm=lambda: (_ for _ in ()).throw(AssertionError))

    dry_run_ids = {action.artifact_id for action in dry_run.plan.actions}
    assert dry_run_ids == {"claude-md", "readme-badge"}
    assert not (repo / "README.md").exists()
    assert (repo / "CLAUDE.md").read_text(encoding="utf-8") == _EXISTING_CLAUDE_MD
    assert (repo / "pyproject.toml").read_text(encoding="utf-8") == _BUILD_FILE
    assert (repo / "docs" / "adr" / "0001-use-postgresql.md").read_text(encoding="utf-8") == (_EXISTING_ADR)
    assert not (repo / ".marshal" / "seed-state.yml").exists()

    # "They review the plan in a PR" -- committing the reviewed plan.json is
    # what makes the worktree clean again for the apply run below (rung 2).
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "review: marshal seed adopt plan")

    # --- "run `marshal seed adopt --apply`, and their build still works
    # because Genesis never touched a file it did not name." -------------
    result = run_adopt(repo, manifest, apply=True, yes=True, confirm=lambda: (_ for _ in ()).throw(AssertionError))

    assert set(result.applied) == {"claude-md", "readme-badge"}

    # CLAUDE.md: existing content preserved, a region inserted at its anchor.
    claude_md = (repo / "CLAUDE.md").read_text(encoding="utf-8")
    assert "Run `make test` before every commit." in claude_md
    assert "Deploy via `make release`." in claude_md
    assert "marshal-seed:begin region=tiers" in claude_md
    assert "Build More Architect Dreams" in claude_md  # the real packaged fragment's own content

    # README.md: created fresh.
    readme = (repo / "README.md").read_text(encoding="utf-8")
    assert "marshal-seed:begin region=model-badge" in readme

    # docs/adr/: present-legacy, recorded, byte-identical, never touched.
    assert (repo / "docs" / "adr" / "0001-use-postgresql.md").read_text(encoding="utf-8") == (_EXISTING_ADR)

    # The unrelated build file: byte-identical, proving Genesis "never
    # touched a file it did not name."
    assert (repo / "pyproject.toml").read_text(encoding="utf-8") == _BUILD_FILE

    state = read_state(repo)
    assert state is not None
    assert {record.id for record in state.managed} == {"claude-md", "readme-badge"}
    assert [record.id for record in state.legacy] == ["legacy-adr"]
    assert state.legacy[0].path == "docs/adr/0001-use-postgresql.md"
    assert state.legacy[0].legacy_of == "claude-md"

    # Re-adopting the now-committed, unchanged repo is a true no-op
    # (FR-84/AD-60) -- the same repeatability J2 itself closes on.
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "adopted")
    second = run_adopt(repo, manifest, apply=True, yes=True, confirm=lambda: (_ for _ in ()).throw(AssertionError))
    assert second.plan.actions == ()
    assert second.applied == ()
