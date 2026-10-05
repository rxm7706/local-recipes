"""scripts/bmad_drift_check.py counts every pixi environment, table-form ones too (doctor Story 6.12).

The script writes the sync baseline Doctor's `check_baseline` compares against, so its count must
agree with Doctor's `_env_count` and with `tomllib`. Harness style matches
test_bmad_drift_check_specs_retired.py: importlib-load the script by path.
"""

from __future__ import annotations

import importlib.util
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "bmad_drift_check.py"


@pytest.fixture
def drift_module():
    spec = importlib.util.spec_from_file_location("bmad_drift_check_env_count_under_test", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_env_count_counts_an_environment_declared_as_its_own_table(drift_module, tmp_path, monkeypatch) -> None:
    (tmp_path / "pixi.toml").write_text(
        '[environments]\ndefault = ["a"]\nbuild = { features = ["b"], no-default-feature = true }\n\n'
        '[environments.platform]\nfeatures = ["c"]\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(drift_module, "REPO_ROOT", tmp_path)
    assert drift_module.env_count() == 3


def test_env_count_raises_on_a_manifest_that_does_not_parse(drift_module, tmp_path, monkeypatch) -> None:
    (tmp_path / "pixi.toml").write_text("[environments\n", encoding="utf-8")
    monkeypatch.setattr(drift_module, "REPO_ROOT", tmp_path)
    with pytest.raises(tomllib.TOMLDecodeError):
        drift_module.env_count()


def test_env_count_raises_when_environments_is_not_a_table(drift_module, tmp_path, monkeypatch) -> None:
    (tmp_path / "pixi.toml").write_text('environments = "x"\n', encoding="utf-8")
    monkeypatch.setattr(drift_module, "REPO_ROOT", tmp_path)
    with pytest.raises(ValueError, match="not a table"):
        drift_module.env_count()


def test_env_count_matches_tomllib_on_the_live_manifest(drift_module) -> None:
    with (REPO_ROOT / "pixi.toml").open("rb") as fh:
        assert drift_module.env_count() == len(tomllib.load(fh)["environments"])
