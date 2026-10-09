"""Offline negative corpus — each defect must stay rejected (Story 23.3)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

NEGATIVE_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "negative"
RECIPES_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "recipes"
SCRIPTS = Path(__file__).resolve().parent.parent.parent / "scripts"
SENTINEL_FIXTURE = RECIPES_DIR / "v1-sentinel-key"

CORPUS_PATHS = [
    NEGATIVE_DIR / "grayskull-flask-pydantic.yaml",
    NEGATIVE_DIR / "grayskull-starlette-prometheus",
    NEGATIVE_DIR / "compiler-no-stdlib",
]


def _recipe_yaml(path: Path) -> Path:
    if path.is_dir():
        return path / "recipe.yaml"
    return path


def _load_optimizer(load_module):
    return load_module("recipe_optimizer.py")


def _load_license_checker():
    path = SCRIPTS / "license-checker.py"
    spec = importlib.util.spec_from_file_location("license_checker_corpus", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["license_checker_corpus"] = mod
    spec.loader.exec_module(mod)
    return mod


def _optimizer_codes(optimizer, path: Path) -> set[str]:
    recipe = _recipe_yaml(path)
    suggestions = optimizer.optimize_recipe(recipe)
    return {s.code for s in suggestions}


def _corpus_is_rejected(path: Path, optimizer, lc) -> bool:
    codes = _optimizer_codes(optimizer, path)
    if codes:
        return True
    recipe = _recipe_yaml(path)
    if path.name == "grayskull-starlette-prometheus" or (
        path.is_dir() and path.name == "grayskull-starlette-prometheus"
    ):
        data = yaml.safe_load(recipe.read_text(encoding="utf-8"))
        declared = (data.get("about") or {}).get("license", "")
        status, _ = lc.check_license_semantics(declared, path if path.is_dir() else path.parent)
        if status == "fail":
            return True
    return False


class TestNegativeCorpusDefects:
    def test_flask_pydantic_test_002_and_sel_005_and_sel_004(self, load_module):
        optimizer = _load_optimizer(load_module)
        path = NEGATIVE_DIR / "grayskull-flask-pydantic.yaml"
        codes = _optimizer_codes(optimizer, path)
        assert "TEST-002" in codes
        assert "SEL-005" in codes
        assert "SEL-004" in codes

    def test_starlette_prometheus_test_002_and_license_semantics(self, load_module):
        optimizer = _load_optimizer(load_module)
        lc = _load_license_checker()
        fixture = NEGATIVE_DIR / "grayskull-starlette-prometheus"
        codes = _optimizer_codes(optimizer, fixture)
        assert "TEST-002" in codes
        data = yaml.safe_load((fixture / "recipe.yaml").read_text(encoding="utf-8"))
        status, message = lc.check_license_semantics(
            data["about"]["license"], fixture
        )
        assert status == "fail"
        assert "or-later" in message.lower() or "or later" in message.lower()

    def test_compiler_no_stdlib_std_001(self, load_module):
        optimizer = _load_optimizer(load_module)
        path = NEGATIVE_DIR / "compiler-no-stdlib"
        codes = _optimizer_codes(optimizer, path)
        assert "STD-001" in codes

    def test_sentinel_key_validate_recipe_repr_error(self, script_runner):
        rc, out, err = script_runner(
            "validate_recipe.py", str(SENTINEL_FIXTURE)
        )
        combined = out + err
        assert rc != 0
        assert "tests[1]" in combined
        assert "SentinelType" in combined or "object repr" in combined

    @pytest.mark.parametrize("fixture_path", CORPUS_PATHS, ids=lambda p: p.name)
    def test_each_corpus_fixture_rejected_by_something(self, load_module, fixture_path):
        optimizer = _load_optimizer(load_module)
        lc = _load_license_checker()
        assert _corpus_is_rejected(fixture_path, optimizer, lc), (
            f"{fixture_path.name} is no longer rejected — a check may have regressed"
        )

    def test_mutation_analyze_noarch_python_test_matrix_disables_test_002(
        self, load_module, monkeypatch
    ):
        """Disabling TEST-002 must red the flask-pydantic fixture test."""
        optimizer = _load_optimizer(load_module)
        path = NEGATIVE_DIR / "grayskull-flask-pydantic.yaml"

        def _empty(_data):
            return []

        monkeypatch.setattr(optimizer, "analyze_noarch_python_test_matrix", _empty)
        codes = _optimizer_codes(optimizer, path)
        assert "TEST-002" not in codes
        # The dedicated test above would fail; this asserts the mutation clause inline.
        assert "SEL-005" in codes or "SEL-004" in codes


class TestSEL005SkipOnNoarch:
    def test_skip_on_noarch_python_fires_sel_005(self, load_module, tmp_path):
        optimizer = _load_optimizer(load_module)
        recipe = tmp_path / "recipe.yaml"
        recipe.write_text(
            "schema_version: 1\n"
            "package:\n  name: x\n  version: \"1\"\n"
            "source:\n"
            "  url: https://example.com/x-1.tar.gz\n"
            "  sha256: 0000000000000000000000000000000000000000000000000000000000000000\n"
            "build:\n  number: 0\n  noarch: python\n"
            "  skip: match(python, \"<3.11\")\n"
            "  script: pip install .\n"
            "requirements:\n  host: [python, pip]\n  run: [python]\n"
            "tests:\n  - python:\n      imports: [x]\n"
            "      python_version: [\"3.11.*\", \"*\"]\n"
            "about:\n  summary: x\n  license: MIT\n  license_file: LICENSE\n"
            "extra:\n  recipe-maintainers: [rxm7706]\n",
            encoding="utf-8",
        )
        codes = _optimizer_codes(optimizer, recipe)
        assert "SEL-005" in codes
