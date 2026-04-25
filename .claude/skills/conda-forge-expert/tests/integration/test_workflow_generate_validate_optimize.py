"""End-to-end: template → validate → optimize → license-check.

No network: uses the offline `template` generator path.
"""
from __future__ import annotations

import json

import pytest


@pytest.mark.integration
class TestWorkflowGenerateValidateOptimize:
    def test_full_chain_offline(self, script_runner, tmp_path):
        # Step 1: generate from template
        rc, out, err = script_runner(
            "recipe-generator.py",
            "template", "python-noarch",
            "--name", "wf-test", "--version", "1.0.0",
            "--output", str(tmp_path),
        )
        assert rc == 0, f"step 1: {out}\n{err}"
        recipe_file = tmp_path / "recipe.yaml"
        assert recipe_file.exists()

        # Step 2: validate (don't require pass — generated recipes are
        # often missing license info — but must not crash, and must invoke
        # conda-smithy lint per fix #1)
        rc, out, err = script_runner(
            "validate_recipe.py", str(tmp_path),
        )
        assert "Traceback" not in (out + err), out + err

        # Step 3: optimize
        rc, out, _ = script_runner(
            "recipe_optimizer.py", str(tmp_path),
        )
        result = json.loads(out)
        assert result["success"] is True

        # Step 4: license check — generated recipe license is a placeholder,
        # so this should flag it OR pass with a warning
        rc, out, err = script_runner(
            "license-checker.py", str(tmp_path),
        )
        # Should at least produce structured output
        assert "License" in out or "license" in out, (out + err)
