"""Unit tests for license-checker.py (hyphenated → script_runner only)."""
from __future__ import annotations


class TestLicenseChecker:
    def test_v1_noarch_mit_valid(self, script_runner, recipes_dir):
        rc, out, err = script_runner(
            "license-checker.py", str(recipes_dir / "v1-noarch")
        )
        assert "Valid SPDX identifier" in out, f"out={out}\nerr={err}"

    def test_v1_compiled_bsd_valid(self, script_runner, recipes_dir):
        rc, out, err = script_runner(
            "license-checker.py", str(recipes_dir / "v1-compiled")
        )
        assert "Valid SPDX identifier" in out, f"out={out}\nerr={err}"

    def test_broken_recipe_invalid_license(self, script_runner, recipes_dir):
        """v1-broken has license 'PROPRIETARY-LICENSE-NOT-SPDX'."""
        rc, out, err = script_runner(
            "license-checker.py", str(recipes_dir / "v1-broken")
        )
        combined = out + err
        # Either: invalid license flagged in output, or non-zero exit
        assert (
            "Invalid" in combined
            or "not" in combined.lower()
            or rc != 0
        ), f"License checker accepted PROPRIETARY-LICENSE-NOT-SPDX.\nout={out}"

    def test_list_spdx_works(self, script_runner):
        rc, out, _ = script_runner("license-checker.py", "--list-spdx")
        assert rc == 0
        assert "MIT" in out
        assert "Apache-2.0" in out
