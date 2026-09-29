"""Meta test -- P-03's detect purity / write-blocking fixture (Story 12.4).

Runs the installed ``seed/detect/`` surface against a real git fixture repo
while every ``seed/fs`` write primitive is monkeypatched to explode. Detect
must classify, hash-check, and emit findings without creating ``.marshal/``,
without mutating tracked files, and without calling a guarded write at all.

Mirrors ``tests/unit/test_seed_verbs_check.py``'s own write-blocking fixture
but lives in ``tests/meta/`` so the invariant is enforced as a package-wide
pattern rule, not only as check-verb regression coverage.

Bounds (stated, not aspirational): read-only ``Path.read_text`` /
``git`` subprocess probes inside ``referenced_dep_findings`` are expected
and in scope for detect's job; only ``fs.write`` / ``replace_span`` /
``remove`` / ``symlink`` are blocked.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from pyforge.marshal.seed import fs
from pyforge.marshal.seed.detect.hashes import check_managed_file, hash_content
from pyforge.marshal.seed.detect.inventory import (
    classify,
    coverage_findings,
    effective_never_write,
    legacy_findings,
    writable_exemptions,
)
from pyforge.marshal.seed.detect.kit import kit_checks, kit_findings
from pyforge.marshal.seed.detect.optout import classify_regions
from pyforge.marshal.seed.detect.referenced_deps import referenced_dep_findings
from pyforge.marshal.seed.model.manifest import (
    AppliesTo,
    ArtifactClass,
    Manifest,
    ManifestEntry,
    Region,
)
from pyforge.marshal.seed.model.version import ModelVersion
from pyforge.marshal.seed.regions.markers import RegionFormat
from pyforge.marshal.seed.state import SeedState

_V1 = ModelVersion.parse("1.0.0")


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    return result


def _init_git_repo(repo: Path) -> None:
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "initial")


def _commit_all(repo: Path) -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "fixture")


def _manifest(*entries: ManifestEntry) -> Manifest:
    return Manifest(model_version=_V1, never_write=("docs/dreams/*.md",), entries=entries)


def _whole_file(entry_id: str, path: str) -> ManifestEntry:
    return ManifestEntry(
        id=entry_id,
        artifact_class=ArtifactClass.COPIED_MANAGED,
        path=path,
        applies_to=AppliesTo.BOTH,
        rationale="meta-test",
    )


def _hybrid(entry_id: str, path: str, region_name: str) -> ManifestEntry:
    return ManifestEntry(
        id=entry_id,
        artifact_class=ArtifactClass.HYBRID_MANAGED_REGION,
        path=path,
        applies_to=AppliesTo.BOTH,
        rationale="meta-test",
        format=RegionFormat.HTML,
        regions=(Region(name=region_name, anchor=("# anchor",)),),
    )


def _hybrid_text(region_name: str, body: str) -> str:
    return (
        "before\n"
        f"<!-- marshal-seed:begin region={region_name} model-version=1.0.0 sha=deadbeef -->\n"
        f"{body}"
        f"<!-- marshal-seed:end region={region_name} -->\n"
        "after\n"
    )


@pytest.fixture
def detect_repo(tmp_path: Path) -> Path:
    _init_git_repo(tmp_path)
    (tmp_path / "WHOLE.md").write_text("managed whole\n", encoding="utf-8")
    (tmp_path / "HYBRID.md").write_text(_hybrid_text("tiers", "body\n"), encoding="utf-8")
    (tmp_path / "docs" / "dreams").mkdir(parents=True)
    (tmp_path / "docs" / "dreams" / "dream.md").write_text("tier-0\n", encoding="utf-8")
    _commit_all(tmp_path)
    return tmp_path


def _install_write_blocker(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*args, **kwargs):
        raise AssertionError("detect must never call a seed/fs write primitive")

    monkeypatch.setattr(fs, "write", _boom)
    monkeypatch.setattr(fs, "replace_span", _boom)
    monkeypatch.setattr(fs, "remove", _boom)
    monkeypatch.setattr(fs, "symlink", _boom)


def _tracked_files(repo: Path) -> list[str]:
    return sorted(path.relative_to(repo).as_posix() for path in repo.rglob("*") if path.is_file())


def test_detect_surface_never_writes(detect_repo: Path, monkeypatch: pytest.MonkeyPatch):
    manifest = _manifest(_whole_file("whole", "WHOLE.md"), _hybrid("hybrid", "HYBRID.md", "tiers"))
    _install_write_blocker(monkeypatch)
    before = _tracked_files(detect_repo)

    inventory = classify(manifest, detect_repo)
    assert inventory.classifications
    assert effective_never_write(manifest, inventory)
    writable_exemptions(manifest, inventory)
    legacy_findings(inventory)
    coverage_findings(manifest)
    referenced_dep_findings(manifest, detect_repo)
    # Story 28.3: the kit detector, with every layer ON so each of its three
    # per-item branches actually runs (an off layer never touches disk, and
    # would exercise nothing). Its module docstring invokes THIS test as its
    # purity guard, so it has to be in the call list for that to be true --
    # a defensive `mkdir` added inside one of those branches must fail here.
    kit_findings(
        kit_checks(
            detect_repo,
            {layer: {"enabled": True, "aggressiveness": "medium"} for layer in ("wire", "output", "structure-graph")},
        )
    )
    check_managed_file("WHOLE.md", "managed whole\n", hash_content("managed whole\n"))
    hybrid_entry = _hybrid("hybrid", "HYBRID.md", "tiers")
    hybrid_text = (detect_repo / "HYBRID.md").read_text(encoding="utf-8")
    classify_regions(
        hybrid_entry,
        hybrid_text,
        SeedState(
            model_version=_V1,
            seed_model_version="0.1.0",
            adopted_at="2026-08-21T00:00:00Z",
            last_update="2026-08-21T00:00:00Z",
            mode="adopt",
            agents=(),
            managed=(),
            skips=(),
            legacy=(),
            migrations_applied=(),
            opted_out=(),
        ),
    )

    assert not (detect_repo / ".marshal").exists()
    assert _tracked_files(detect_repo) == before
    assert _git(detect_repo, "status", "--porcelain").stdout == ""
