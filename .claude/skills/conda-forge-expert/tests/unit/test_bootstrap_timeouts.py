"""Per-step timeouts honour BOOTSTRAP_<X>_TIMEOUT env vars."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"


def _load(name: str):
    path = _SCRIPTS_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    if str(_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_DIR))
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def bootstrap_mod():
    return _load("bootstrap_data")


def _scrub(monkeypatch):
    for k in (
        "BOOTSTRAP_MAPPING_CACHE_TIMEOUT", "BOOTSTRAP_CVE_DB_TIMEOUT",
        "BOOTSTRAP_VDB_TIMEOUT", "BOOTSTRAP_CF_ATLAS_TIMEOUT",
        "BOOTSTRAP_PHASE_GP_TIMEOUT", "BOOTSTRAP_PHASE_N_TIMEOUT",
    ):
        monkeypatch.delenv(k, raising=False)


class TestTimeoutResolver:
    def test_defaults_match_sized_for_cold_run(self, monkeypatch, bootstrap_mod):
        _scrub(monkeypatch)
        # cf_atlas must be at least 1h to survive a real --fresh cold build
        # (the original 2400s ceiling was the source of the v7.7 timeout bug)
        assert bootstrap_mod._timeout_for("cf_atlas") >= 3600
        assert bootstrap_mod._timeout_for("vdb") >= 1800
        # Fast steps stay tight
        assert bootstrap_mod._timeout_for("mapping_cache") <= 600
        assert bootstrap_mod._timeout_for("cve_db") <= 1200

    def test_env_override_wins(self, monkeypatch, bootstrap_mod):
        _scrub(monkeypatch)
        monkeypatch.setenv("BOOTSTRAP_CF_ATLAS_TIMEOUT", "14400")
        assert bootstrap_mod._timeout_for("cf_atlas") == 14400

    def test_zero_env_falls_back_to_default(self, monkeypatch, bootstrap_mod):
        _scrub(monkeypatch)
        monkeypatch.setenv("BOOTSTRAP_CF_ATLAS_TIMEOUT", "0")
        assert bootstrap_mod._timeout_for("cf_atlas") == bootstrap_mod._DEFAULT_TIMEOUTS["cf_atlas"]

    def test_invalid_env_falls_back_to_default(self, monkeypatch, bootstrap_mod, capsys):
        _scrub(monkeypatch)
        monkeypatch.setenv("BOOTSTRAP_CF_ATLAS_TIMEOUT", "not-a-number")
        assert bootstrap_mod._timeout_for("cf_atlas") == bootstrap_mod._DEFAULT_TIMEOUTS["cf_atlas"]
        out = capsys.readouterr().out
        assert "ignoring invalid" in out

    def test_negative_env_falls_back_to_default(self, monkeypatch, bootstrap_mod):
        _scrub(monkeypatch)
        monkeypatch.setenv("BOOTSTRAP_VDB_TIMEOUT", "-100")
        assert bootstrap_mod._timeout_for("vdb") == bootstrap_mod._DEFAULT_TIMEOUTS["vdb"]

    def test_every_step_has_a_default(self, bootstrap_mod):
        for step in ("mapping_cache", "cve_db", "vdb", "cf_atlas",
                     "phase_gp", "phase_n"):
            assert step in bootstrap_mod._DEFAULT_TIMEOUTS
            assert bootstrap_mod._DEFAULT_TIMEOUTS[step] > 0
