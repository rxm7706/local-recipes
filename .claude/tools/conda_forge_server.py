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


def _run_script(script_path: Path, args: List[str]) -> Dict[str, Any]:
    """Run a Python script that outputs JSON and parse the result."""
    if not script_path.exists():
        return {"error": f"Script not found at {script_path}"}
        
    cmd = ["python", str(script_path)] + args
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            check=False
        )
        
        # Some scripts might print non-JSON stuff before/after, or stderr
        # We try to parse the stdout as JSON
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            # If JSON parsing fails, return raw output
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
    """Validate a conda-forge recipe (recipe.yaml or meta.yaml) against best practices.
    
    Args:
        recipe_path: Absolute or relative path to the recipe file or directory.
        
    Returns:
        A JSON string containing validation results (passed, errors, warnings, info).
    """
    args = ["--json", recipe_path]
    result = _run_script(VALIDATE_SCRIPT, args)
    return json.dumps(result, indent=2)


@mcp.tool()
def check_dependencies(recipe_path: str, suggest: bool = True) -> str:
    """Check if the dependencies in a conda recipe exist on conda-forge.
    
    Args:
        recipe_path: Absolute or relative path to the recipe file or directory.
        suggest: Whether to provide suggestions for missing dependencies (e.g. PyPI to Conda mappings).
        
    Returns:
        A JSON string listing found and missing dependencies.
    """
    args = ["--json", recipe_path]
    if suggest:
        args.insert(0, "--suggest")
        
    result = _run_script(CHECKER_SCRIPT, args)
    return json.dumps(result, indent=2)


@mcp.tool()
def generate_recipe_from_pypi(package_name: str, version: str = None) -> str:
    """Generate a conda-forge recipe from a PyPI package using rattler-build or grayskull.
    
    Args:
        package_name: The name of the PyPI package.
        version: Optional version to generate (defaults to latest).
        
    Returns:
        A JSON string indicating success or failure, and the path to the generated recipe.
    """
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
    # This is a long-running process, so we just return the stdout/stderr
    result = _run_script(CVE_MANAGER_SCRIPT, args)
    return json.dumps(result, indent=2)


@mcp.tool()
def scan_for_vulnerabilities(recipe_path: str) -> str:
    """Scans a recipe's dependencies against the local CVE database."""
    args = ["--json", recipe_path]
    result = _run_script(VULN_SCANNER_SCRIPT, args)
    return json.dumps(result, indent=2)


if __name__ == "__main__":
    mcp.run()
