"""Story 43.1: pages_one_generator flag states (CAP-61 / CAP-4)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from pyforge.testing_kit import make_flag_provider_fixture
from pyforge.testing_kit.flags import flag_states

from pyforge.herald.pages_one_generator import PAGES_ONE_GENERATOR_FLAG

flag_provider = make_flag_provider_fixture()


def _load_pages_one_tool():
    root = _repo_root()
    tools = root / "docsite" / "tools"
    path = tools / "pages_one_generator.py"
    spec = importlib.util.spec_from_file_location("pages_one_generator_under_test", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (
            candidate / "src" / "shared" / "packages" / "pyforge-herald"
        ).is_dir():
            return candidate
    raise AssertionError("could not locate repo root")


@flag_states(PAGES_ONE_GENERATOR_FLAG)
def test_ac6_dossier_path_follows_flag(flag_provider: dict[str, bool]) -> None:
    pog = _load_pages_one_tool()
    enabled = flag_provider[PAGES_ONE_GENERATOR_FLAG]
    choice = pog.select_dossier_generator(flag_enabled=enabled)
    if enabled:
        assert choice == "astro"
    else:
        assert choice == "jinja"
