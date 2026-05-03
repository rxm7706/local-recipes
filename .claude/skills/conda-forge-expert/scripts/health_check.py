#!/usr/bin/env python3
"""
System Health Check for the local-recipes development environment.

Verifies that all required tools, configurations, and network connections
are in place for a smooth development workflow.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, List

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# Define the checks as a list of functions
CHECKS = []

def health_check(func):
    """Decorator to register a function as a health check."""
    CHECKS.append(func)
    return func

@health_check
def check_git_upstream_remote() -> Dict[str, Any]:
    """Checks if the 'upstream' git remote for conda-forge/staged-recipes is configured."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "upstream"],
            capture_output=True, text=True, check=False
        )
        if result.returncode == 0 and "conda-forge/staged-recipes" in result.stdout:
            return {"status": "OK", "message": "Git remote 'upstream' is correctly configured."}
        else:
            return {
                "status": "FAIL",
                "message": "Git remote 'upstream' is not configured for conda-forge/staged-recipes.",
                "fix": "Run 'pixi run sync-upstream-conda-forge' to configure it automatically.",
            }
    except FileNotFoundError:
        return {"status": "FAIL", "message": "Git command not found."}
    except Exception as e:
        return {"status": "FAIL", "message": f"An unexpected error occurred: {e}"}

@health_check
def check_github_cli_auth() -> Dict[str, Any]:
    """Verifies that the GitHub CLI ('gh') is installed and authenticated."""
    if not shutil.which("gh"):
        return {"status": "FAIL", "message": "GitHub CLI ('gh') is not installed.", "fix": "Install 'gh' from conda-forge."}
    
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True, text=True, check=False
        )
        if result.returncode == 0:
            return {"status": "OK", "message": "GitHub CLI is installed and authenticated."}
        else:
            return {
                "status": "FAIL",
                "message": "GitHub CLI is not authenticated.",
                "fix": "Run 'gh auth login' to authenticate with your GitHub account.",
            }
    except Exception as e:
        return {"status": "FAIL", "message": f"Failed to check gh auth status: {e}"}

@health_check
def check_docker_daemon() -> Dict[str, Any]:
    """Checks if the Docker daemon is running and responsive."""
    if not shutil.which("docker"):
        return {"status": "WARN", "message": "Docker command not found. Linux builds will not be possible."}
        
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True, text=True, check=False, timeout=5
        )
        if result.returncode == 0 and "Server Version" in result.stdout:
            return {"status": "OK", "message": "Docker daemon is running."}
        else:
            return {
                "status": "FAIL",
                "message": "Docker daemon is not responsive.",
                "fix": "Start the Docker Desktop application or ensure the Docker service is running.",
            }
    except subprocess.TimeoutExpired:
        return {"status": "FAIL", "message": "Docker command timed out. The daemon may be frozen."}
    except Exception as e:
        return {"status": "FAIL", "message": f"Failed to check Docker status: {e}"}

@health_check
def check_mcp_scripts() -> Dict[str, Any]:
    """Ensures the Python scripts for the MCP server are present."""
    scripts_dir = Path(__file__).parent
    required_scripts = [
        "validate_recipe.py",
        "dependency-checker.py",
        "recipe-generator.py",
    ]
    missing = [s for s in required_scripts if not (scripts_dir / s).exists()]
    
    if not missing:
        return {"status": "OK", "message": "All required MCP tool scripts are present."}
    else:
        return {
            "status": "FAIL",
            "message": f"Missing MCP tool scripts: {', '.join(missing)}",
            "fix": "Ensure the '.claude/skills/conda-forge-expert/scripts/' directory is complete.",
        }

@health_check
def check_api_connectivity() -> Dict[str, Any]:
    """Tests network connectivity to critical external APIs."""
    if not REQUESTS_AVAILABLE:
        return {"status": "WARN", "message": "'requests' library not found, skipping API connectivity check."}

    urls_to_check = {
        "Anaconda API": "https://api.anaconda.org",
        "OSV API (Vulnerabilities)": "https://api.osv.dev/v1/query",
        "PyPI": "https://pypi.org",
    }
    
    errors = []
    for name, url in urls_to_check.items():
        try:
            response = requests.head(url, timeout=5)
            if response.status_code >= 400 and url.endswith("query"): # OSV returns 400 on HEAD/GET
                 response = requests.post(url, json={}, timeout=5)

            if response.status_code >= 400:
                 errors.append(f"{name}: Failed (status {response.status_code})")
        except requests.RequestException as e:
            errors.append(f"{name}: Failed ({e.__class__.__name__})")

    if not errors:
        return {"status": "OK", "message": "Successfully connected to all required external APIs."}
    else:
        return {
            "status": "WARN",
            "message": f"Could not connect to some external APIs: {', '.join(errors)}",
            "fix": "Check your internet connection, VPN, or corporate firewall settings.",
        }


def run_all_checks() -> List[Dict[str, Any]]:
    """Run all registered health checks and return the results."""
    results = []
    for check_func in CHECKS:
        result = {"check": check_func.__name__}
        result.update(check_func())
        results.append(result)
    return results


def print_results(results: List[Dict[str, Any]], use_json: bool) -> int:
    """Print results in human-readable or JSON format."""
    if use_json:
        print(json.dumps({"health_checks": results}, indent=2))
        return 0

    overall_status = "OK"
    exit_code = 0
    
    print("="*60)
    print("Running Development Environment Health Check...")
    print("="*60)

    for res in results:
        status = res.get("status", "FAIL")
        message = res.get("message", "No message.")
        
        if status == "OK":
            symbol = "✅"
        elif status == "WARN":
            symbol = "⚠️"
            if overall_status != "FAIL":
                overall_status = "WARN"
        else: # FAIL
            symbol = "❌"
            overall_status = "FAIL"
            exit_code = 1
            
        print(f"{symbol} [{status:^4s}] {message}")
        
        if status != "OK" and "fix" in res:
            print(f"       └─ Recommendation: {res['fix']}")

    print("="*60)
    print(f"Overall Status: {overall_status}")
    print("="*60)
    
    return exit_code


def main():
    parser = argparse.ArgumentParser(description="Run a health check on the local-recipes environment.")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format.")
    args = parser.parse_args()

    results = run_all_checks()
    exit_code = print_results(results, args.json)
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
