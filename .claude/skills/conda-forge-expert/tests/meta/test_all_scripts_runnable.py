"""Meta: every script in scripts/ must produce sensible output for `--help`.

Catches: import errors, missing dependencies, broken argparse, scripts that
crash before printing usage.
"""
from __future__ import annotations

import pytest


# Hyphenated and underscored — no exclusions
SCRIPTS = [
    "adoption_stage.py",
    "atlas_phase.py",
    "behind_upstream.py",
    "bootstrap_data.py",
    "conda_forge_atlas.py",
    "cve_manager.py",
    "cve_watcher.py",
    "dependency-checker.py",
    "detail_cf_atlas.py",
    "failure_analyzer.py",
    "feedstock_context.py",
    "feedstock_enrich.py",
    "feedstock_health.py",
    "feedstock_lookup.py",
    "feedstock-migrator.py",
    "find_alternative.py",
    "github_updater.py",
    "github_version_checker.py",
    "health_check.py",
    "inventory_channel.py",
    "license-checker.py",
    "local_builder.py",
    "mapping_manager.py",
    "name_resolver.py",
    "npm_updater.py",
    "recipe_editor.py",
    "recipe-generator.py",
    "recipe_optimizer.py",
    "recipe_updater.py",
    "release_cadence.py",
    "scan_project.py",
    "staleness_report.py",
    "submit_pr.py",
    "validate_recipe.py",
    "version_downloads.py",
    "vulnerability_scanner.py",
    "whodepends.py",
]

# These scripts run on import / on empty args (not argparse-driven)
NO_HELP = {
    "health_check.py",   # Runs the check directly
    "mapping_manager.py",  # No --help in current CLI
}


@pytest.mark.meta
@pytest.mark.parametrize("script", SCRIPTS)
def test_script_responds_to_help(script_runner, script):
    if script in NO_HELP:
        pytest.skip(f"{script} does not implement --help")
    rc, out, err = script_runner(script, "--help", timeout=30)
    assert rc == 0, f"{script} --help failed:\nout={out}\nerr={err}"
    assert "Traceback" not in (out + err)
    assert "usage" in (out + err).lower(), f"No usage line for {script}"


@pytest.mark.meta
def test_all_scripts_listed(scripts_dir):
    """Make sure SCRIPTS in this file matches what's actually in scripts/."""
    actual = {
        p.name for p in scripts_dir.glob("*.py")
        if p.name != "test-skill.py"
        and not p.name.startswith("_")  # internal helpers (_http, _sbom)
    }
    declared = set(SCRIPTS)
    missing_in_test = actual - declared
    missing_in_dir = declared - actual
    assert not missing_in_test, (
        f"New scripts added to scripts/ but not declared in tests: {missing_in_test}"
    )
    assert not missing_in_dir, (
        f"Declared in tests but not present in scripts/: {missing_in_dir}"
    )
