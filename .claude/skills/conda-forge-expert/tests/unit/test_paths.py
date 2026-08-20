"""Unit tests for _paths.py — the Rule-2 retro's canonical path helper.

Introduced to replace ~30 hand-rolled `Path(__file__)` parent-walk copies
that had drifted into three shapes across scripts/*.py, including two
(`feedstock_context.py`, `feedstock_lookup.py`) that resolved a data
directory one level shallow (`.claude/skills/data/...` instead of
`.claude/data/...`).
"""
from __future__ import annotations

from pathlib import Path


class TestPaths:
    def test_get_repo_root_is_the_monorepo_root(self, load_module):
        mod = load_module("_paths.py")
        root = mod.get_repo_root()
        # The repo root is the parent of .claude/, not .claude/ itself.
        assert (root / ".claude" / "skills" / "conda-forge-expert").is_dir()

    def test_get_data_dir_is_directly_under_claude(self, load_module):
        mod = load_module("_paths.py")
        data_dir = mod.get_data_dir()
        assert data_dir == mod.get_repo_root() / ".claude" / "data" / "conda-forge-expert"
        # Regression guard for the specific bug this module fixes: must NOT
        # be nested one level deeper under .claude/skills/.
        assert "skills" not in data_dir.parts

    def test_get_repo_root_returns_none_rather_than_raising_on_resolution_failure(
        self, load_module, monkeypatch
    ):
        """Regression guard: get_repo_root() used to compute `_REPO_ROOT` at
        MODULE IMPORT TIME with no guard, so an IndexError/OSError there took
        down every script importing this module. It's now a per-call,
        try/except-guarded computation returning None on failure — verified
        here by making the underlying resolve() raise directly."""
        mod = load_module("_paths.py")

        class _BoomPath:
            def resolve(self):
                raise OSError("simulated broken symlink chain")

        monkeypatch.setattr(mod, "Path", lambda *_a, **_kw: _BoomPath())
        assert mod.get_repo_root() is None

    def test_get_data_dir_returns_none_when_repo_root_unresolvable(
        self, load_module, monkeypatch
    ):
        mod = load_module("_paths.py")
        monkeypatch.setattr(mod, "get_repo_root", lambda: None)
        assert mod.get_data_dir() is None


class TestNoneContractIsHonouredByEveryCaller:
    """`None` is a real return value, and it is never raised — so nothing
    downstream catches it for you.

    Making the helper lazy fixed the import-time crash INSIDE `_paths`, but
    three of its four callers then bound `get_data_dir()` straight into a
    module-scope `_DIR / "name"`, which is `TypeError: unsupported operand
    type(s) for /: 'NoneType' and 'str'` at import — the same crash, one file
    over, and a `TypeError` that the `except ImportError` guards wrapping
    sibling-module loads elsewhere in this skill do not catch.
    """

    def test_feedstock_lookup_disables_caching_instead_of_crashing(
        self, load_module, monkeypatch, tmp_path
    ):
        import _paths  # noqa: F401 — imported by the module under test

        mod = load_module("feedstock_lookup.py")
        monkeypatch.setattr(mod, "_DATA_DIR", None)
        monkeypatch.setattr(mod, "_CACHE_DIR", None)
        assert mod._cache_path("numpy") is None
        assert mod._load_cache("numpy") is None
        mod._store_cache("numpy", {"a": 1})  # must not raise

    def test_feedstock_context_disables_caching_instead_of_crashing(
        self, load_module, monkeypatch
    ):
        mod = load_module("feedstock_context.py")
        monkeypatch.setattr(mod, "_DATA_DIR", None)
        monkeypatch.setattr(mod, "_CACHE_DIR", None)
        assert mod._cache_path("numpy") is None
        assert mod._load_cache("numpy") is None
        mod._store_cache("numpy", {"a": 1})  # must not raise

    def test_bootstrap_data_main_exits_with_a_diagnostic(
        self, load_module, monkeypatch, capsys
    ):
        """`bootstrap_data` has no degraded mode — DATA_DIR/REPO_ROOT are
        essential — so it must fail at the entry point with a readable
        message, not several hundred lines deeper with `'NoneType' object has
        no attribute 'mkdir'`."""
        mod = load_module("bootstrap_data.py")
        monkeypatch.setattr(mod, "DATA_DIR", None)
        monkeypatch.setattr(mod, "REPO_ROOT", None)
        monkeypatch.setattr(mod.sys, "argv", ["bootstrap_data.py"])
        assert mod.main() == 2
        assert "cannot resolve the repo root" in capsys.readouterr().err

    def test_module_import_survives_an_unresolvable_data_dir(self, monkeypatch, tmp_path):
        """End-to-end: with `get_data_dir` stubbed to None BEFORE the module
        is first imported, importing it must still succeed."""
        import importlib.util
        import sys

        scripts = Path(__file__).resolve().parents[2] / "scripts"
        if str(scripts) not in sys.path:
            sys.path.insert(0, str(scripts))
        import _paths

        monkeypatch.setattr(_paths, "get_data_dir", lambda: None)
        for name in ("feedstock_lookup", "feedstock_context"):
            previous = sys.modules.get(name)
            spec = importlib.util.spec_from_file_location(name, scripts / f"{name}.py")
            module = importlib.util.module_from_spec(spec)
            # Register BEFORE exec: both modules define dataclasses, and
            # @dataclass resolves string annotations via
            # sys.modules[cls.__module__].
            sys.modules[name] = module
            try:
                spec.loader.exec_module(module)  # must not raise TypeError
                assert module._CACHE_DIR is None
            finally:
                if previous is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = previous
