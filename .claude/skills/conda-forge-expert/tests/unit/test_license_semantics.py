"""Unit tests for license-checker licence-semantics gate (Story 23.1)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "license-semantics"
SCRIPTS = Path(__file__).resolve().parent.parent.parent / "scripts"


def _load_license_checker():
    path = SCRIPTS / "license-checker.py"
    spec = importlib.util.spec_from_file_location("license_checker", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["license_checker"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def lc():
    return _load_license_checker()


class TestLicenseSemanticsCli:
    def test_only_vs_or_later_exits_nonzero_and_names_or_later(
        self, script_runner
    ):
        recipe = FIXTURES / "only-vs-or-later" / "recipe.yaml"
        src = FIXTURES / "only-vs-or-later"
        rc, out, err = script_runner(
            "license-checker.py", str(recipe), "--check-source", str(src)
        )
        combined = out + err
        assert rc != 0
        assert "GPL-3.0-or-later" in combined

    def test_or_later_agreement_exits_zero(self, script_runner):
        recipe = FIXTURES / "or-later" / "recipe.yaml"
        src = FIXTURES / "or-later"
        rc, out, err = script_runner(
            "license-checker.py", str(recipe), "--check-source", str(src)
        )
        combined = out + err
        assert rc == 0
        assert "licence semantics mismatch" not in combined.lower()
        assert "Licence semantics check skipped" not in combined

    def test_silent_license_skips_without_forcing_fail(self, script_runner):
        recipe = FIXTURES / "only-silent" / "recipe.yaml"
        src = FIXTURES / "only-silent"
        rc, out, err = script_runner(
            "license-checker.py", str(recipe), "--check-source", str(src)
        )
        combined = out + err
        assert rc == 0
        assert "needs a human read" in combined

    def test_mit_skips_semantics(self, script_runner):
        recipe = FIXTURES / "mit" / "recipe.yaml"
        src = FIXTURES / "mit"
        rc, out, err = script_runner(
            "license-checker.py", str(recipe), "--check-source", str(src)
        )
        combined = out + err
        assert rc == 0
        assert "no copyleft -only/-or-later axis" in combined

    def test_copying_filename_is_read(self, script_runner):
        recipe = FIXTURES / "copying-name" / "recipe.yaml"
        src = FIXTURES / "copying-name"
        rc, out, err = script_runner(
            "license-checker.py", str(recipe), "--check-source", str(src)
        )
        combined = out + err
        assert rc != 0
        assert "GPL-3.0-or-later" in combined

    def test_missing_license_file_exits_nonzero(self, script_runner, tmp_path):
        recipe = FIXTURES / "missing-file" / "recipe.yaml"
        empty_src = tmp_path / "empty-src"
        empty_src.mkdir()
        rc, out, err = script_runner(
            "license-checker.py", str(recipe), "--check-source", str(empty_src)
        )
        assert rc != 0
        assert "File not found in source" in out + err

    def test_licence_txt_filename_is_read(self, script_runner, tmp_path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "LICENCE.txt").write_text(
            "either version 3 of the License, or (at your option) any later version.\n",
            encoding="utf-8",
        )
        recipe_dir = tmp_path / "recipe"
        recipe_dir.mkdir()
        (recipe_dir / "recipe.yaml").write_text(
            """
about:
  license: GPL-3.0-only
  license_file: LICENCE.txt
""".strip()
            + "\n",
            encoding="utf-8",
        )
        rc, out, err = script_runner(
            "license-checker.py",
            str(recipe_dir / "recipe.yaml"),
            "--check-source",
            str(src),
        )
        assert rc != 0
        assert "GPL-3.0-or-later" in out + err


class TestCheckLicenseSemanticsPure:
    def test_import_and_call_does_not_print_or_exit(self, lc, capsys):
        status, message = lc.check_license_semantics(
            "MIT", FIXTURES / "mit"
        )
        assert status == "skip"
        assert message
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

    def test_mismatch_direct_oracle(self, lc):
        status, message = lc.check_license_semantics(
            "GPL-3.0-only", FIXTURES / "only-vs-or-later"
        )
        assert status == "fail"
        assert "GPL-3.0-or-later" in message

    def test_mutation_guard_mismatch_must_fail(self, lc):
        """Removing the comparison would make this assertion fail (mutation)."""
        status, _ = lc.check_license_semantics(
            "GPL-3.0-only", FIXTURES / "only-vs-or-later"
        )
        assert status == "fail"
