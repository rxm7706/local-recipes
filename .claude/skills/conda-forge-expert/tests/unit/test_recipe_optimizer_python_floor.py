"""Regression guard for `_read_conda_forge_python_floor`'s repo-root resolution.

Rule-2 retro (Story 5.5): the function resolved `repo_root` one level
shallow (`Path(__file__).resolve().parents[3]`, landing on `.claude/`
instead of the monorepo root), so
`repo_root / ".pixi/envs/local-recipes/conda_build_config.yaml"` could
never exist on any real checkout, and the function silently fell back to
the hardcoded default on every call — SEL-004 never actually worked. The
function now resolves through the shared `_paths.get_repo_root()`.
"""
from __future__ import annotations

import sys


class TestReadCondaForgePythonFloor:
    def test_reads_the_real_pinning_file_at_the_true_repo_root(
        self, load_module, tmp_path, monkeypatch
    ):
        """Point the shared helper at a fake repo root containing a real
        pinning file one level shallower than the old (buggy) resolution
        would have looked — proves the fixed depth, not just "returns a
        string"."""
        paths = load_module("_paths.py")
        pinning_dir = tmp_path / ".pixi" / "envs" / "local-recipes"
        pinning_dir.mkdir(parents=True)
        (pinning_dir / "conda_build_config.yaml").write_text(
            "python_min:\n  - 3.13\n"
        )
        monkeypatch.setattr(paths, "get_repo_root", lambda: tmp_path)

        optimizer = load_module("recipe_optimizer.py")
        result = optimizer._read_conda_forge_python_floor()
        assert result == "3.13"

    def test_falls_back_to_default_when_pinning_file_absent(
        self, load_module, tmp_path, monkeypatch
    ):
        """The real pinning file's first `python_min` entry happens to equal
        `_DEFAULT_CONDA_FORGE_PYTHON_FLOOR`, so asserting against the default
        alone cannot distinguish "fell back" from "read the real file" — the
        test would pass even if the monkeypatch silently failed to apply.
        Re-point the default at a sentinel so only the fallback path can
        produce it."""
        paths = load_module("_paths.py")
        monkeypatch.setattr(paths, "get_repo_root", lambda: tmp_path)
        optimizer = load_module("recipe_optimizer.py")
        monkeypatch.setattr(
            optimizer, "_DEFAULT_CONDA_FORGE_PYTHON_FLOOR", "0.0-sentinel"
        )
        result = optimizer._read_conda_forge_python_floor()
        assert result == "0.0-sentinel"

    def test_falls_back_to_default_when_repo_root_unresolvable(
        self, load_module, monkeypatch
    ):
        """Regression guard: `get_repo_root()` returning None (a resolution
        failure) must degrade to the documented default, not raise — this is
        the specific resilience `recipe_optimizer.py` had before switching to
        the shared `_paths` helper (a bare `repo_root / "..."` on `None`
        would otherwise raise `TypeError`)."""
        paths = load_module("_paths.py")
        monkeypatch.setattr(paths, "get_repo_root", lambda: None)
        optimizer = load_module("recipe_optimizer.py")
        # Sentinel for the same reason as the test above: the real file's
        # value equals the default, so a plain default-comparison could not
        # fail.
        monkeypatch.setattr(
            optimizer, "_DEFAULT_CONDA_FORGE_PYTHON_FLOOR", "0.0-sentinel"
        )
        result = optimizer._read_conda_forge_python_floor()
        assert result == "0.0-sentinel"
