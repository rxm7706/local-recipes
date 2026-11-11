"""Doctor Story 58.1 (spec-pyforge-doctor:CAP-97) -- the live-tree half of
``test_sources_chain_spec_surface.py``.

These four tests load this repository's own ``scripts/spec_surface_check.py``
(the stamp script that must stay aligned with ``chain``, Story 41.1), so they
run in the station's live-tree half. Every ``gather_spec_surface`` test builds
its own git repository and stays in ``test_sources_chain_spec_surface.py``
(the package half).
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

import pytest
from test_sources_chain_spec_surface import _init_repo, _isolate_git_env  # noqa: F401 -- the module's autouse scrub

from pyforge.doctor.sources import chain

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree


def _repo_root() -> Path:
    """This repository's root, resolved when a test runs (never at import time)."""
    root = Path(__file__).resolve().parents[6]
    assert (root / ".claude").is_dir(), f"{root} is not the local-recipes checkout root (no .claude/)"
    return root


@lru_cache
def _stamp_script_module():
    """Mutation script twin — must stay aligned with chain (Story 41.1)."""
    path = _repo_root() / "scripts" / "spec_surface_check.py"
    spec = importlib.util.spec_from_file_location("_spec_surface_check_parity", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize(
    ("frontmatter", "expected"),
    [
        ("surface:\n  - a.py\n", ["a.py"]),
        ("surface: [a.py, b.py]\n", ["a.py", "b.py"]),
        ("surface: a.py\n", ["a.py"]),
        ("surface:\n    - meta/\n", ["meta/"]),
    ],
)
def test_stamp_script_parse_surface_matches_chain(tmp_path: Path, frontmatter: str, expected: list[str]) -> None:
    """Story 41.1: `parse_surface` and `_parse_surface` read the contract identically."""
    spec_md = tmp_path / "SPEC.md"
    spec_md.write_text(f"---\n{frontmatter}---\n\nbody\n", encoding="utf-8")
    script = _stamp_script_module()
    globs_script, _, _ = script.parse_surface(spec_md)
    globs_chain, _, _ = chain._parse_surface(spec_md)
    assert globs_script == globs_chain == expected


@pytest.mark.parametrize(
    ("pattern", "path"),
    [
        ("src/", "src/deep/mod.py"),
        ("pkg/**", "pkg/a/b.py"),
        ("exact.py", "exact.py"),
    ],
)
def test_stamp_script_glob_to_re_matches_chain(pattern: str, path: str) -> None:
    script = _stamp_script_module()
    script_hit = script.glob_to_re(pattern).match(path)
    chain_hit = chain._glob_to_re(pattern).match(path)
    assert bool(script_hit) == bool(chain_hit)
    if script_hit and chain_hit:
        assert script_hit.group(0) == chain_hit.group(0)


def test_stamp_script_tracked_files_reads_non_ascii_paths_literally(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """DW-FU-6-6-4: the stamp script's ``tracked_files()`` matches chain's read."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "diátaxis.md").write_text("x\n", encoding="utf-8")
    (repo / 'we"ird.md').write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "diátaxis.md", 'we"ird.md'], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "add", "--date", "2026-01-01T00:00:00+00:00"],
        check=True,
        env={
            **os.environ,
            "GIT_AUTHOR_DATE": "2026-01-01T00:00:00+00:00",
            "GIT_COMMITTER_DATE": "2026-01-01T00:00:00+00:00",
        },
    )

    script = _stamp_script_module()
    monkeypatch.setattr(script, "REPO_ROOT", repo, raising=False)

    script_paths = set(script.tracked_files())
    chain_paths = set(chain._tracked_files(repo) or [])

    assert "diátaxis.md" in script_paths
    assert 'we"ird.md' in script_paths
    assert script_paths == chain_paths


def test_stamp_script_full_stamp_over_a_corrupt_baseline_refuses_and_writes_nothing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Story 41.1: a ``--spec``-less full stamp reads the committed baseline
    BEFORE it writes, so a corrupt baseline refuses (exit 1, naming the file
    and its ``git checkout`` recovery) even when discovery found Specs. The
    full stamp used to read the baseline only on its zero-Spec guard, so with
    any Spec discovered it replaced the corrupt file at exit 0 and the damage
    was never reported."""
    script = _stamp_script_module()
    (tmp_path / "scripts").mkdir()
    baseline = tmp_path / "scripts" / ".spec-surface-baseline.json"
    corrupt = b'{"proj/spec-alpha": "abc'
    baseline.write_bytes(corrupt)
    live = {"proj/spec-alpha": {"memlog": "0" * 40, "files": {"a.py": "1" * 40}}}
    monkeypatch.setattr(script, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(script, "BASELINE", baseline)
    monkeypatch.setattr(script, "_live_state", lambda unevaluable=None: live)
    monkeypatch.setattr(sys, "argv", ["spec_surface_check.py", "--write-baseline"])

    assert script.main() == 1

    assert baseline.read_bytes() == corrupt
    assert not baseline.with_name(baseline.name + ".tmp").exists()
    err = capsys.readouterr().err
    assert "scripts/.spec-surface-baseline.json" in err
    assert "git checkout --" in err
