#!/usr/bin/env python3
"""Conda-Forge FastMCP Server — exposes recipe validation and dependency checking as tools.

Allows Claude Code to programmatically validate recipes and check dependencies
without needing to parse bash output.
"""
import json
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, List

from fastmcp import FastMCP

mcp = FastMCP("conda-forge-expert")

# Paths to the scripts relative to this file
SCRIPTS_DIR = Path(__file__).parent.parent / "skills" / "conda-forge-expert" / "scripts"
VALIDATE_SCRIPT = SCRIPTS_DIR / "validate_recipe.py"
CHECKER_SCRIPT = SCRIPTS_DIR / "dependency-checker.py"
GENERATOR_SCRIPT = SCRIPTS_DIR / "recipe-generator.py"
HEALTH_CHECK_SCRIPT = SCRIPTS_DIR / "health_check.py"
CVE_MANAGER_SCRIPT = SCRIPTS_DIR / "cve_manager.py"
VULN_SCANNER_SCRIPT = SCRIPTS_DIR / "vulnerability_scanner.py"
RECIPE_EDITOR_SCRIPT = SCRIPTS_DIR / "recipe_editor.py"
MAPPING_MANAGER_SCRIPT = SCRIPTS_DIR / "mapping_manager.py"
NAME_RESOLVER_SCRIPT = SCRIPTS_DIR / "name_resolver.py"
FAILURE_ANALYZER_SCRIPT = SCRIPTS_DIR / "failure_analyzer.py"
RECIPE_OPTIMIZER_SCRIPT = SCRIPTS_DIR / "recipe_optimizer.py"

# Path to the build summary file
SUMMARY_FILE = Path(__file__).parent.parent.parent / "build_summary.json"


def _run_script(script_path: Path, args: List[str], input_text: str = None) -> Dict[str, Any]:
    """Run a Python script that outputs JSON and parse the result."""
    if not script_path.exists():
        return {"error": f"Script not found at {script_path}"}
        
    cmd = ["python", str(script_path)] + args
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            check=False,
            input=input_text
        )
        
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {
                "error": "Failed to parse JSON output",
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode
            }
            
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def validate_recipe(recipe_path: str) -> str:
    """Validate a conda-forge recipe (recipe.yaml or meta.yaml) against best practices."""
    args = ["--json", recipe_path]
    result = _run_script(VALIDATE_SCRIPT, args)
    return json.dumps(result, indent=2)


@mcp.tool()
def check_dependencies(recipe_path: str, suggest: bool = True) -> str:
    """Check if the dependencies in a conda recipe exist on conda-forge."""
    args = ["--json", recipe_path]
    if suggest:
        args.insert(0, "--suggest")
        
    result = _run_script(CHECKER_SCRIPT, args)
    return json.dumps(result, indent=2)


@mcp.tool()
def generate_recipe_from_pypi(package_name: str, version: str = None) -> str:
    """Generate a conda-forge recipe from a PyPI package using rattler-build or grayskull."""
    try:
        args = ["run", "-e", "grayskull", "pypi", package_name]
        if version:
            args.extend(["==", version])
        
        repo_root = Path(__file__).parent.parent.parent
        
        result = subprocess.run(
            ["pixi"] + args,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False
        )
        
        recipe_dir = repo_root / "recipes" / package_name
        if recipe_dir.exists():
            return json.dumps({
                "success": True,
                "message": f"Recipe generated at {recipe_dir}",
                "stdout": result.stdout
            }, indent=2)
        else:
            return json.dumps({
                "success": False,
                "error": "Failed to generate recipe.",
                "stdout": result.stdout,
                "stderr": result.stderr
            }, indent=2)
            
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)}, indent=2)


@mcp.tool()
def run_system_health_check() -> str:
    """Runs a comprehensive health check on the local development environment."""
    args = ["--json"]
    result = _run_script(HEALTH_CHECK_SCRIPT, args)
    return json.dumps(result, indent=2)


@mcp.tool()
def update_cve_database(force: bool = False) -> str:
    """Downloads and updates the local CVE database from osv.dev."""
    args = []
    if force:
        args.append("--force")
    result = _run_script(CVE_MANAGER_SCRIPT, args)
    return json.dumps(result, indent=2)


@mcp.tool()
def scan_for_vulnerabilities(recipe_path: str) -> str:
    """Scans a recipe's dependencies against the local CVE database."""
    args = ["--json", recipe_path]
    result = _run_script(VULN_SCANNER_SCRIPT, args)
    return json.dumps(result, indent=2)


@mcp.tool()
def trigger_build(config: str) -> str:
    """Triggers a local build process asynchronously."""
    if SUMMARY_FILE.exists():
        SUMMARY_FILE.unlink()
        
    build_script = Path(__file__).parent.parent.parent / "build-locally.py"
    
    subprocess.Popen(["python", str(build_script), config])
    
    return json.dumps({"status": "Build triggered", "config": config})


@mcp.tool()
def get_build_summary() -> str:
    """Retrieves the result of the last build."""
    if not SUMMARY_FILE.exists():
        return json.dumps({"status": "In progress", "message": "Build summary not yet available."})
    
    with open(SUMMARY_FILE) as f:
        summary = json.load(f)
    
    return json.dumps(summary, indent=2)


@mcp.tool()
def edit_recipe(recipe_path: str, actions: List[Dict[str, Any]]) -> str:
    """Programmatically edits a recipe file using a list of structured actions."""
    actions_json = json.dumps(actions)
    args = [recipe_path, actions_json]
    result = _run_script(RECIPE_EDITOR_SCRIPT, args)
    return json.dumps(result, indent=2)


@mcp.tool()
def update_mapping_cache(force: bool = False) -> str:
    """Updates the local PyPI-to-Conda name mapping cache from Grayskull."""
    args = []
    if force:
        args.append("--force")
    result = _run_script(MAPPING_MANAGER_SCRIPT, args)
    return json.dumps(result, indent=2)


@mcp.tool()
def get_conda_name(pypi_name: str) -> str:
    """Resolves a PyPI package name to its conda-forge equivalent using a tiered, cache-first strategy."""
    args = [pypi_name]
    result = _run_script(NAME_RESOLVER_SCRIPT, args)
    return json.dumps(result, indent=2)


@mcp.tool()
def analyze_build_failure(error_log: str) -> str:
    """Analyzes a build failure log and suggests a structured fix."""
    args = ["-"] # Read from stdin
    result = _run_script(FAILURE_ANALYZER_SCRIPT, args, input_text=error_log)
    return json.dumps(result, indent=2)


@mcp.tool()
def optimize_recipe(recipe_path: str) -> str:
    """Lints a recipe for optimizations and conda-forge best practices."""
    args = [recipe_path]
    result = _run_script(RECIPE_OPTIMIZER_SCRIPT, args)
    return json.dumps(result, indent=2)


if __name__ == "__main__":
    mcp.run()
