#!/usr/bin/env python3
"""Conda-Forge FastMCP Server — exposes recipe validation and dependency checking as tools.

Allows Claude Code to programmatically validate recipes and check dependencies
without needing to parse bash output.
"""
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

from fastmcp import FastMCP, Context

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
RECIPE_UPDATER_SCRIPT = SCRIPTS_DIR / "recipe_updater.py"
SUBMIT_PR_SCRIPT = SCRIPTS_DIR / "submit_pr.py"
GITHUB_VERSION_CHECKER_SCRIPT = SCRIPTS_DIR / "github_version_checker.py"
GITHUB_UPDATER_SCRIPT = SCRIPTS_DIR / "github_updater.py"

# Path to the build summary file
SUMMARY_FILE = Path(__file__).parent.parent.parent / "build_summary.json"
BUILD_PID_FILE = Path(__file__).parent.parent.parent / "build.pid"
_active_build: Optional[subprocess.Popen] = None
# Use the interpreter running this server — guaranteed to be the correct conda env.
_PYTHON = sys.executable


def _run_script(script_path: Path, args: List[str], input_text: str | None = None, timeout: int = 120) -> Dict[str, Any]:
    """Run a Python script that outputs JSON and parse the result."""
    if not script_path.exists():
        return {"error": f"Script not found at {script_path}"}

    cmd = [_PYTHON, str(script_path)] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            input=input_text,
            timeout=timeout,
        )
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {
                "error": "Failed to parse JSON output",
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
            }
    except subprocess.TimeoutExpired:
        return {"error": f"Script timed out after {timeout}s", "script": str(script_path)}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def validate_recipe(recipe_path: str) -> str:
    """Validate a conda-forge recipe (recipe.yaml or meta.yaml) against best practices."""
    args = ["--json", recipe_path]
    result = _run_script(VALIDATE_SCRIPT, args)
    return json.dumps(result, indent=2)


@mcp.tool()
def check_dependencies(
    recipe_path: str,
    suggest: bool = True,
    channel: str | None = None,
    subdirs: List[str] | None = None,
) -> str:
    """Check if the dependencies in a conda recipe exist on conda-forge (or a custom channel).

    Uses batch repodata.json fetching — one HTTP request per (channel, subdir) pair —
    instead of per-package API calls, making it fast and suitable for air-gapped environments.

    For JFrog/Artifactory channels set JFROG_API_KEY (or JFROG_TOKEN / JFROG_USER +
    JFROG_PASSWORD) and pass the channel URL. For fully offline use, pre-populate
    CONDA_DEP_CACHE_DIR with repodata files and the tool will work without network access.

    Args:
        recipe_path: Path to a recipe file or directory.
        suggest: If True, include conda-forge name suggestions for missing packages.
        channel: Channel URL to check against (default: https://conda.anaconda.org/conda-forge).
                 Supports file:// paths for local mirrors and JFrog Artifactory URLs.
        subdirs: List of subdirs to fetch, e.g. ['linux-64', 'noarch'] (default: noarch + linux-64).
    """
    args = ["--json"]
    if suggest:
        args.append("--suggest")
    if channel:
        args.extend(["--channel", channel])
    if subdirs:
        for s in subdirs:
            args.extend(["--subdir", s])
    args.append(recipe_path)
    result = _run_script(CHECKER_SCRIPT, args)
    return json.dumps(result, indent=2)


@mcp.tool()
def generate_recipe_from_pypi(package_name: str, version: str | None = None) -> str:
    """Generate a conda-forge recipe from a PyPI package using grayskull."""
    try:
        pkg_spec = f"{package_name}=={version}" if version else package_name
        args = ["run", "-e", "grayskull", "pypi", pkg_spec]
        
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
async def update_cve_database(force: bool = False, ctx: Context | None = None) -> str:
    """Downloads and updates the local CVE database from osv.dev."""
    if ctx:
        await ctx.info("Starting CVE database update (may take up to 10 minutes)…")
    args = []
    if force:
        args.append("--force")
    result = _run_script(CVE_MANAGER_SCRIPT, args, timeout=600)
    if ctx:
        success = result.get("success", not result.get("error"))
        msg = result.get("message", "done") if success else result.get("error", "failed")
        await ctx.info(f"CVE database update {'succeeded' if success else 'failed'}: {msg}")
    return json.dumps(result, indent=2)


@mcp.tool()
def scan_for_vulnerabilities(recipe_path: str) -> str:
    """Scans a recipe's dependencies for known vulnerabilities.

    Primary mode: queries OSV.dev querybatch API (https://api.osv.dev/v1/querybatch).
    Offline fallback: uses local CVE database if OSV.dev is unreachable.
    Run update_cve_database() periodically to keep the local database fresh.
    """
    args = ["--json", recipe_path]
    result = _run_script(VULN_SCANNER_SCRIPT, args)
    return json.dumps(result, indent=2)


@mcp.tool()
async def trigger_build(config: str, ctx: Context | None = None) -> str:
    """Triggers a local build process asynchronously. Returns error if a build is already running."""
    global _active_build

    # Guard against concurrent builds
    if _active_build is not None and _active_build.poll() is None:
        return json.dumps({"error": "A build is already running.", "pid": _active_build.pid})

    for f in (SUMMARY_FILE, BUILD_PID_FILE):
        if f.exists():
            f.unlink()

    build_script = Path(__file__).parent.parent.parent / "build-locally.py"
    _active_build = subprocess.Popen([_PYTHON, str(build_script), config])
    BUILD_PID_FILE.write_text(str(_active_build.pid))

    started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if ctx:
        await ctx.info(f"Build started for config '{config}' (PID {_active_build.pid}). Poll get_build_summary() to check progress.")
    return json.dumps({"status": "Build triggered", "config": config, "pid": _active_build.pid,
                       "started_at": started_at})


@mcp.tool()
def get_build_summary() -> str:
    """Retrieves the result of the last build, or reports if still running."""
    global _active_build

    if not SUMMARY_FILE.exists():
        still_running = _active_build is not None and _active_build.poll() is None
        pid = _active_build.pid if _active_build else None
        return json.dumps({"status": "in_progress" if still_running else "unknown",
                           "message": "Build still running." if still_running else "No build summary found — build may have crashed.",
                           "pid": pid})

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
def analyze_build_failure(error_log: str, first_only: bool = False) -> str:
    """Analyze a build failure log and return structured fix suggestions.

    Scans the log against 33 known error patterns across 10 categories:
    COMPILER, BUILD_TOOLS, LINKER, PYTHON, RATTLER_SCHEMA, RUST, NODE, SOURCE, SYSTEM, TEST_FAILURE.

    Returns all matches ordered by first appearance in the log. The top-level
    'error_class', 'diagnosis', 'matched_text', and 'suggestion' fields always
    reflect the primary (earliest) match for backward compatibility. The
    'all_matches' list contains every match for multi-root-cause analysis.

    Args:
        error_log: The raw text of the build failure log.
        first_only: If True, return only the primary match (smaller response).
    """
    args = ["-"]  # read log from stdin
    if first_only:
        args.append("--first-only")
    result = _run_script(FAILURE_ANALYZER_SCRIPT, args, input_text=error_log)
    return json.dumps(result, indent=2)


@mcp.tool()
def optimize_recipe(recipe_path: str) -> str:
    """Lints a recipe for optimizations and conda-forge best practices.

    Check codes:
      DEP-001  Dev dependency (pytest, ruff, etc.) found in run requirements.
      DEP-002  noarch:python recipe with Python upper-bound in run instead of run_constrained.
      PIN-001  Exact-version (==) pin in run requirements — blocks security updates.
      ABT-001  Missing license_file in about section.
      SCRIPT-001  'sudo' used in build.sh — builds must not require root.
      SCRIPT-002  'pip install --upgrade' in build.sh — breaks reproducibility.
      SEL-001  Recipe restricted to one platform; redundant if/then conditions may be removable.
      SEL-002  noarch:python recipe missing python_min context variable (CFEP-25).
    """
    args = [recipe_path]
    result = _run_script(RECIPE_OPTIMIZER_SCRIPT, args)
    return json.dumps(result, indent=2)


@mcp.tool()
def update_recipe(recipe_path: str, dry_run: bool = False) -> str:
    """Checks for a new version of a package on PyPI and updates the recipe if found."""
    args = [recipe_path]
    if dry_run:
        args.append("--dry-run")
    result = _run_script(RECIPE_UPDATER_SCRIPT, args)
    return json.dumps(result, indent=2)


@mcp.tool()
def submit_pr(
    recipe_name: str,
    dry_run: bool = False,
    pr_title: str | None = None,
    pr_body: str | None = None,
) -> str:
    """Submit a finished recipe as a PR to conda-forge/staged-recipes via your GitHub fork.

    Workflow:
      1. Validates the recipe exists locally at recipes/<recipe_name>/.
      2. Checks 'gh auth status' — requires prior 'gh auth login'.
      3. Clones your fork of staged-recipes if not already present locally.
      4. Syncs the fork's main branch with upstream conda-forge/staged-recipes.
      5. Creates branch 'add-recipe-<recipe_name>', copies the recipe, commits, pushes.
      6. Opens a PR against conda-forge/staged-recipes main.

    Always call with dry_run=True first to verify prerequisites without making any
    network writes. The result includes 'pr_url' on success.

    Args:
        recipe_name: The recipe directory name under recipes/ (e.g. 'numpy').
        dry_run: If True, validate prerequisites only — do not push or create PR.
        pr_title: Optional custom PR title. Defaults to 'Add recipe for <name>'.
        pr_body: Optional custom PR body. Defaults to the standard checklist template.
    """
    args = [recipe_name]
    if dry_run:
        args.append("--dry-run")
    if pr_title:
        args.extend(["--title", pr_title])
    if pr_body:
        args.extend(["--body", pr_body])
    result = _run_script(SUBMIT_PR_SCRIPT, args, timeout=300)  # 5 min for clone + push
    return json.dumps(result, indent=2)


@mcp.tool()
def update_recipe_from_github(
    recipe_path: str,
    github_repo: str | None = None,
    dry_run: bool = False,
    allow_prerelease: bool = False,
) -> str:
    """Autotick bot for GitHub-only packages: fetch the latest release and update the recipe.

    Mirrors update_recipe (PyPI autotick) but uses the GitHub Releases API as the
    version source. Use this for packages that publish releases on GitHub before
    or instead of PyPI (e.g. apple-fm-sdk).

    The recipe's GitHub repo is auto-detected from source.url, context variables,
    or about.home. Pass github_repo to override when auto-detection fails.

    Always call with dry_run=True first to verify the detected repo and version
    before allowing file writes.

    Args:
        recipe_path: Path to a recipe file or directory.
        github_repo: 'owner/repo' or full GitHub URL (overrides auto-detect).
        dry_run: If True, report what would change without writing the file.
        allow_prerelease: If True, include pre-release versions.
    """
    args = [recipe_path]
    if github_repo:
        args.extend(["--repo", github_repo])
    if dry_run:
        args.append("--dry-run")
    if allow_prerelease:
        args.append("--pre")
    result = _run_script(GITHUB_UPDATER_SCRIPT, args)
    return json.dumps(result, indent=2)


@mcp.tool()
def check_github_version(recipe_path: str | None = None, github_repo: str | None = None) -> str:
    """Check the latest GitHub release for a recipe or a specific GitHub repo.

    Complements update_recipe (PyPI-only) for packages whose canonical source is GitHub.
    Auto-detects the GitHub URL from the recipe when recipe_path is given.

    Args:
        recipe_path: Path to a recipe file or directory. The GitHub URL is extracted
                     from context variables, source.url, or about.home.
        github_repo: GitHub repo in 'owner/repo' format or a full github.com URL.
                     Use this when the recipe doesn't contain a detectable GitHub URL.

    Returns JSON with latest_version, current_version (if recipe provided), and
    update_available flag. Exit code 2 from the script means an update is available.
    """
    args = []
    if recipe_path:
        args.append(recipe_path)
    if github_repo:
        args.extend(["--repo", github_repo])
    args.append("--json")
    result = _run_script(GITHUB_VERSION_CHECKER_SCRIPT, args)
    return json.dumps(result, indent=2)


if __name__ == "__main__":
    mcp.run()
