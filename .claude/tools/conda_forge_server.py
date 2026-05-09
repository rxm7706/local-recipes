#!/usr/bin/env python3
"""Conda-Forge FastMCP Server — exposes recipe validation and dependency checking as tools.

Allows Claude Code to programmatically validate recipes and check dependencies
without needing to parse bash output.
"""
import json
import platform
import shutil
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
FEEDSTOCK_LOOKUP_SCRIPT = SCRIPTS_DIR / "feedstock_lookup.py"
FEEDSTOCK_ENRICH_SCRIPT = SCRIPTS_DIR / "feedstock_enrich.py"
FEEDSTOCK_CONTEXT_SCRIPT = SCRIPTS_DIR / "feedstock_context.py"
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


def _detect_host_config() -> str:
    """Detect the host platform and return the matching .ci_support/<name>.yaml stem.

    Linux x86_64 → 'linux64', Linux aarch64 → 'linux_aarch64',
    macOS Intel → 'osx64', macOS Apple Silicon → 'osxarm64',
    Windows → 'win64'.
    """
    sysname = platform.system().lower()
    machine = platform.machine().lower()
    if sysname == "linux":
        return "linux64" if machine in ("x86_64", "amd64") else "linux_aarch64"
    if sysname == "darwin":
        return "osxarm64" if machine in ("arm64", "aarch64") else "osx64"
    if sysname == "windows":
        return "win64"
    raise RuntimeError(f"Unsupported host platform: {sysname}/{machine}")


@mcp.tool()
async def trigger_build(
    config: str | None = None,
    mode: str = "native",
    recipe: str | None = None,
    ctx: Context | None = None,
) -> str:
    """Triggers a local build process asynchronously.

    Two modes:

    - **'native'** (default, recommended): runs `rattler-build build` on the host,
      passing both the platform variant config from .ci_support/ and the
      conda-forge-pinning overlay from the local-recipes pixi env. Faster than
      Docker, no Docker daemon required, and recipes that reference
      `${{ python_min }}` resolve correctly via the pinning overlay.
      Auto-detects the host platform from `uname -ms` if `config` is omitted.

    - **'docker'**: runs `python build-locally.py <config>`. Full conda-forge CI
      fidelity (alma9 sysroot, isolated build env). Requires Docker daemon
      access. Should only be invoked when the user explicitly asks for it —
      never as the default verification step (see SKILL.md Step 7a vs 7b).

    Returns an error if another build is already in flight.

    Args:
        config: Platform config stem matching `.ci_support/<config>.yaml`
                (e.g., 'linux64', 'osxarm64', 'win64'). For mode='native',
                omit to auto-detect from the current host. For mode='docker',
                required (no auto-detect — Docker can run any config).
        mode: 'native' (default) or 'docker'.
        recipe: Path to a recipe.yaml or its directory. Required for mode='native';
                ignored for mode='docker' (build-locally.py builds all recipes/).
        ctx: MCP context for progress messages.
    """
    global _active_build

    # Guard against concurrent builds
    if _active_build is not None and _active_build.poll() is None:
        return json.dumps({"error": "A build is already running.", "pid": _active_build.pid})

    if mode not in ("native", "docker"):
        return json.dumps({"error": f"Invalid mode '{mode}'. Use 'native' or 'docker'."})

    for f in (SUMMARY_FILE, BUILD_PID_FILE):
        if f.exists():
            f.unlink()

    repo_root = Path(__file__).parent.parent.parent
    recipe_path: Optional[Path] = None

    if mode == "native":
        if config is None:
            try:
                config = _detect_host_config()
            except RuntimeError as e:
                return json.dumps({"error": str(e)})
        if recipe is None:
            return json.dumps({"error": "mode='native' requires a recipe path. "
                                        "Pass `recipe=` pointing to recipe.yaml or its directory."})

        recipe_path = Path(recipe)
        if not recipe_path.is_absolute():
            recipe_path = repo_root / recipe
        if recipe_path.is_dir():
            for cand in ("recipe.yaml", "meta.yaml"):
                if (recipe_path / cand).exists():
                    recipe_path = recipe_path / cand
                    break
            else:
                return json.dumps({"error": f"No recipe.yaml or meta.yaml in {recipe_path}"})
        if not recipe_path.exists():
            return json.dumps({"error": f"Recipe not found: {recipe_path}"})

        variant = repo_root / ".ci_support" / f"{config}.yaml"
        if not variant.exists():
            return json.dumps({"error": f"Variant config not found: {variant}"})

        # conda-forge-pinning ships its conda_build_config.yaml inside the
        # local-recipes pixi env; pass it as an additional --variant-config so
        # ${{ python_min }} and the python matrix resolve like upstream CI.
        # See SKILL.md § Recipe Authoring Gotchas + v6.2.2 CHANGELOG entry.
        pinning_overlay = repo_root / ".pixi" / "envs" / "local-recipes" / "conda_build_config.yaml"

        cmd: List[str] = [
            "pixi", "run", "-e", "local-recipes",
            "rattler-build", "build",
            "--recipe", str(recipe_path),
            "--variant-config", str(variant),
        ]
        if pinning_overlay.exists():
            cmd.extend(["--variant-config", str(pinning_overlay)])
        cmd.extend(["--output-dir", str(repo_root / "build_artifacts" / config)])

        _active_build = subprocess.Popen(cmd, cwd=str(repo_root))
        invocation_label = f"native rattler-build (config={config}, recipe={recipe_path.parent.name})"

    else:  # docker
        if config is None:
            return json.dumps({"error": "mode='docker' requires an explicit config "
                                        "(e.g., 'linux64'). No auto-detection in Docker mode."})
        build_script = repo_root / "build-locally.py"
        if not build_script.exists():
            return json.dumps({"error": f"build-locally.py not found at {build_script}"})
        _active_build = subprocess.Popen([_PYTHON, str(build_script), config], cwd=str(repo_root))
        invocation_label = f"Docker build via build-locally.py (config={config})"

    BUILD_PID_FILE.write_text(str(_active_build.pid))

    started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    if ctx:
        await ctx.info(f"Build started: {invocation_label} (PID {_active_build.pid}). "
                       f"Poll get_build_summary() to check progress.")
    return json.dumps({
        "status": "Build triggered",
        "mode": mode,
        "config": config,
        "recipe": str(recipe_path) if recipe_path is not None else None,
        "pid": _active_build.pid,
        "started_at": started_at,
    })


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
def lookup_feedstock(pkg_name: str, no_cache: bool = False) -> str:
    """Look up an existing conda-forge/<pkg_name>-feedstock and return its parsed recipe.

    Returns a structured result indicating whether the feedstock exists, its
    recipe format (recipe.yaml / meta.yaml), the raw recipe text, and a parsed
    YAML dict (Jinja2 placeholders for v0 are stripped to bare tokens before
    parsing — values are not rendered, but the structure is). Used by
    `enrich_from_feedstock` and `get_feedstock_context`; can also be called
    directly when an agent wants to inspect feedstock metadata without
    applying any merges.

    Results cached locally for 1 hour. Returns exists=False (and no error)
    when the feedstock simply doesn't exist — that's the common case for new
    packages. v6.4.

    Args:
        pkg_name: Package name (e.g. 'numpy'). The feedstock repo name is
                  derived as conda-forge/<pkg_name>-feedstock.
        no_cache: Bypass the local 1h cache and force a fresh GitHub API lookup.
    """
    args = [pkg_name, "--no-raw"]
    if no_cache:
        args.append("--no-cache")
    result = _run_script(FEEDSTOCK_LOOKUP_SCRIPT, args)
    return json.dumps(result, indent=2)


@mcp.tool()
def enrich_from_feedstock(recipe_path: str, dry_run: bool = False) -> str:
    """Enrich a freshly-generated recipe with metadata from an existing conda-forge feedstock.

    Field-by-field merge policy (v6.4 implementation of items 3a + 3b):
      - extra.recipe-maintainers: union with feedstock's list, always include rxm7706
      - extra.recipe-maintainers-emeritus, extra.feedstock-name: carry over
      - about.homepage / repository / documentation: feedstock wins if grayskull empty
      - about.description: feedstock wins if longer (hand-curated paragraphs)
      - about.summary: grayskull always wins (freshest from PyPI)
      - about.license: must match — diverging licenses abort with explicit error
      - about.license_file: feedstock wins (paths often involve secondary sources)

    Never carries over: requirements.host/run/build (always from grayskull),
    source URLs/sha256, build script, tests.

    When the existing feedstock is meta.yaml v0 format, v0 about-field names
    (`home`, `dev_url`, `doc_url`) are translated to their v1 equivalents
    (`homepage`, `repository`, `documentation`) before merging.

    Always adds rxm7706 to maintainers — even when no feedstock exists. Idempotent.

    Args:
        recipe_path: Path to recipe.yaml to enrich. Must already be generated
                     (e.g. by generate_recipe_from_pypi).
        dry_run: If True, return what would change without writing.
    """
    args = [recipe_path]
    if dry_run:
        args.append("--dry-run")
    result = _run_script(FEEDSTOCK_ENRICH_SCRIPT, args)
    return json.dumps(result, indent=2)


@mcp.tool()
def get_feedstock_context(pkg_name: str, max_open: int = 50, max_closed: int = 10, no_cache: bool = False) -> str:
    """Surface open and recent-closed issues from an existing conda-forge feedstock as planning context.

    v6.4 implementation of item 3c. Non-blocking — returns issues for the agent
    to surface to the user. Never auto-applied.

    Returns a JSON dict with:
      - feedstock_exists: bool
      - open_issues: list of {number, title, labels, author, url, created_at, comments}
      - recent_closed_issues: same shape, recently closed
      - open_count, recent_closed_count: counts

    Useful before generating or updating a recipe to:
      - Spot known build failures the maintainer team has already documented
      - Find linked PRs that already attempted a fix
      - Avoid re-discovering known issues

    Returns feedstock_exists=False with empty issue lists when the feedstock
    doesn't exist (common for new packages). 30-min cache.

    Args:
        pkg_name: Package name (e.g. 'numpy').
        max_open: Cap on open issues fetched (default 50).
        max_closed: Cap on recent closed issues (default 10).
        no_cache: Bypass the local 30-min cache.
    """
    args = [pkg_name, "--max-open", str(max_open), "--max-closed", str(max_closed)]
    if no_cache:
        args.append("--no-cache")
    result = _run_script(FEEDSTOCK_CONTEXT_SCRIPT, args)
    return json.dumps(result, indent=2)


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

    Scans the log against 41 known error patterns across 13 categories:
    COMPILER, BUILD_TOOLS, LINKER, PYTHON, RATTLER_SCHEMA, RUST, NODE, SOURCE, SYSTEM,
    TEST_FAILURE, ENV_ISOLATION, MSVC, MACOS_SDK.

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

    Accepts a path to a recipe file (recipe.yaml/meta.yaml) or its containing
    directory; the optimizer auto-finds the recipe inside.

    Check codes:
      DEP-001  Dev dependency (pytest, ruff, etc.) found in run requirements.
      DEP-002  noarch:python recipe with Python upper-bound in run instead of run_constrained.
      PIN-001  Exact-version (==) pin in run requirements — blocks security updates.
      ABT-001  Missing license_file in about section.
      ABT-002  v0/meta.yaml about-field names (dev_url/doc_url/home/license_family) used in v1
               recipe — rattler-build silently ignores them; suggests v1 names.
      SCRIPT-001  'sudo' used in build.sh — builds must not require root.
      SCRIPT-002  'pip install --upgrade' in build.sh — breaks reproducibility.
      SEL-001  Recipe restricted to one platform; redundant if/then conditions may be removable.
      SEL-002  noarch:python recipe missing python_min context variable (CFEP-25).
      SEL-003  v0-style 'py < N' selector in v1 build.skip — silently ignored by rattler-build;
               suggests match(python, ...) form.
      STD-001  compiler() used without stdlib() — CRITICAL, causes CI rejection.
      STD-002  Both meta.yaml and recipe.yaml present — format mixing is rejected.
      SEC-001  Source URL without sha256 checksum.
      TEST-001  Missing tests section.
      MAINT-001  Missing recipe-maintainers in extra section.
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


@mcp.tool()
def migrate_to_v1(recipe_path: str) -> str:
    """Convert a meta.yaml (v0) recipe to the modern recipe.yaml (v1) format using feedrattler.

    feedrattler produces a recipe.yaml alongside the existing meta.yaml. The original
    meta.yaml is NOT deleted — review the generated recipe.yaml with validate_recipe and
    optimize_recipe, then remove meta.yaml manually once satisfied.

    Requires feedrattler on PATH (installed in the local-recipes pixi environment).

    Args:
        recipe_path: Path to a meta.yaml file or its parent directory.
    """
    rp = Path(recipe_path)
    meta_yaml = rp if rp.name == "meta.yaml" else rp / "meta.yaml"
    recipe_dir = meta_yaml.parent
    recipe_yaml = recipe_dir / "recipe.yaml"

    if not meta_yaml.exists():
        return json.dumps({
            "success": False,
            "error": f"No meta.yaml found at {meta_yaml}. This tool only converts meta.yaml (v0) recipes.",
        })

    if recipe_yaml.exists():
        return json.dumps({
            "success": False,
            "error": (
                f"recipe.yaml already exists at {recipe_yaml}. "
                "Remove it first if you want to regenerate from meta.yaml."
            ),
        })

    feedrattler_bin = shutil.which("feedrattler")
    if not feedrattler_bin:
        return json.dumps({
            "success": False,
            "error": "feedrattler not found on PATH. Ensure the local-recipes pixi environment is active.",
        })

    try:
        result = subprocess.run(
            [feedrattler_bin, str(recipe_dir)],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        return json.dumps({"success": False, "error": "feedrattler timed out after 60s."})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

    if recipe_yaml.exists():
        return json.dumps({
            "success": True,
            "message": (
                f"Converted {meta_yaml} → {recipe_yaml}. "
                "Run validate_recipe and optimize_recipe to verify quality. "
                "Remove meta.yaml only after review."
            ),
            "recipe_yaml": str(recipe_yaml),
            "meta_yaml_preserved": str(meta_yaml),
            "stdout": result.stdout,
            "stderr": result.stderr,
        }, indent=2)

    return json.dumps({
        "success": False,
        "error": "feedrattler ran but recipe.yaml was not created. Check stdout/stderr.",
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.returncode,
    }, indent=2)


# ── cf_atlas tool surface (v6.9 / v6.10 phases) ──────────────────────────────
# Each MCP tool below thin-wraps the corresponding canonical CLI in
# .claude/skills/conda-forge-expert/scripts/. The CLIs all accept --json.

ATLAS_STALENESS_SCRIPT     = SCRIPTS_DIR / "staleness_report.py"
ATLAS_FEEDSTOCK_HEALTH     = SCRIPTS_DIR / "feedstock_health.py"
ATLAS_WHODEPENDS_SCRIPT    = SCRIPTS_DIR / "whodepends.py"
ATLAS_BEHIND_UPSTREAM      = SCRIPTS_DIR / "behind_upstream.py"
ATLAS_CVE_WATCHER          = SCRIPTS_DIR / "cve_watcher.py"
ATLAS_VERSION_DOWNLOADS    = SCRIPTS_DIR / "version_downloads.py"
ATLAS_RELEASE_CADENCE      = SCRIPTS_DIR / "release_cadence.py"
ATLAS_FIND_ALTERNATIVE     = SCRIPTS_DIR / "find_alternative.py"
ATLAS_ADOPTION_STAGE       = SCRIPTS_DIR / "adoption_stage.py"
ATLAS_DETAIL_CF_ATLAS      = SCRIPTS_DIR / "detail_cf_atlas.py"
ATLAS_SCAN_PROJECT         = SCRIPTS_DIR / "scan_project.py"


@mcp.tool()
def staleness_report(
    maintainer: str | None = None,
    days: int = 0,
    limit: int = 25,
    by_risk: bool = False,
    has_vulns: bool = False,
    bot_stuck: bool = False,
    include_archived: bool = False,
) -> str:
    """List conda-forge feedstocks ordered by oldest latest_conda_upload.

    Optionally rank by Phase G CVE counts (`by_risk`), filter to feedstocks
    with non-zero Critical/High affecting current (`has_vulns`), or filter
    to feedstocks where the conda-forge bot has failed at least one
    version-update PR (`bot_stuck`). Pass `--maintainer` to scope to one
    handle's feedstocks.
    """
    args = ["--json", "--limit", str(limit), "--days", str(days)]
    if maintainer:
        args.extend(["--maintainer", maintainer])
    if by_risk:
        args.append("--by-risk")
    if has_vulns:
        args.append("--has-vulns")
    if bot_stuck:
        args.append("--bot-stuck")
    if include_archived:
        args.append("--all-status")
    return json.dumps(_run_script(ATLAS_STALENESS_SCRIPT, args), indent=2)


@mcp.tool()
def feedstock_health(
    maintainer: str | None = None,
    filter_kind: str = "stuck",
    limit: int = 25,
) -> str:
    """Surface feedstocks with conda-forge bot / build / PR / GitHub issues.

    `filter_kind` ∈ {'stuck' (Phase M errors > 0), 'bad' (cf-graph 'bad'
    flag), 'open-pr' (Phase M open bot PR), 'ci-red' (Phase N default
    branch failing), 'open-issues' (Phase N issues > 0), 'open-prs-human'
    (Phase N PRs > 0), 'all' (union)}.
    """
    args = ["--json", "--limit", str(limit), "--filter", filter_kind]
    if maintainer:
        args.extend(["--maintainer", maintainer])
    return json.dumps(_run_script(ATLAS_FEEDSTOCK_HEALTH, args), indent=2)


@mcp.tool()
def whodepends(
    name: str,
    reverse: bool = False,
    req_type: str | None = None,
    limit: int = 50,
) -> str:
    """cf_atlas Phase J dependency graph query.

    Forward (default): packages that <name> depends on. With reverse=True:
    packages that depend on <name> (blast-radius / bus-factor analysis).
    """
    args = ["--json", "--limit", str(limit), name]
    if reverse:
        args.append("--reverse")
    if req_type:
        args.extend(["--type", req_type])
    return json.dumps(_run_script(ATLAS_WHODEPENDS_SCRIPT, args), indent=2)


@mcp.tool()
def behind_upstream(
    maintainer: str | None = None,
    limit: int = 50,
) -> str:
    """List conda-forge feedstocks behind their upstream-of-record version
    (PyPI / GitHub / GitLab / Codeberg / npm / CRAN / CPAN / LuaRocks /
    crates.io / RubyGems / NuGet / Maven). Picks the right upstream
    automatically based on conda_source_registry per row."""
    args = ["--json", "--limit", str(limit)]
    if maintainer:
        args.extend(["--maintainer", maintainer])
    return json.dumps(_run_script(ATLAS_BEHIND_UPSTREAM, args), indent=2)


@mcp.tool()
def cve_watcher(
    maintainer: str | None = None,
    since_days: int = 7,
    severity: str = "C",
    only_increases: bool = False,
    limit: int = 25,
) -> str:
    """Diff cf_atlas vuln_history snapshots — surface CVE count changes
    between today and N days ago. severity ∈ {'C' (Critical), 'H' (High),
    'K' (KEV-listed), 'T' (Total)}. only_increases=True to filter to
    packages where the count went up."""
    args = [
        "--json", "--since-days", str(since_days), "--severity", severity,
        "--limit", str(limit),
    ]
    if maintainer:
        args.extend(["--maintainer", maintainer])
    if only_increases:
        args.append("--only-increases")
    return json.dumps(_run_script(ATLAS_CVE_WATCHER, args), indent=2)


@mcp.tool()
def version_downloads(
    name: str,
    limit: int = 30,
    by_downloads: bool = False,
) -> str:
    """Per-version download breakdown for one package (cf_atlas Phase I).
    Default sort: newest version first. by_downloads=True sorts by total
    downloads instead — surfaces which versions the user base actually
    runs."""
    args = ["--json", "--limit", str(limit), name]
    if by_downloads:
        args.append("--by-downloads")
    return json.dumps(_run_script(ATLAS_VERSION_DOWNLOADS, args), indent=2)


@mcp.tool()
def release_cadence(
    package: str | None = None,
    maintainer: str | None = None,
    limit: int = 30,
) -> str:
    """Release cadence trend classifier (Phase I). For each package or
    maintainer's set, classifies as accelerating / stable / decelerating /
    silent / one-version based on rolling 30/90/365-day release counts."""
    args = ["--json", "--limit", str(limit)]
    if package:
        args.extend(["--package", package])
    if maintainer:
        args.extend(["--maintainer", maintainer])
    return json.dumps(_run_script(ATLAS_RELEASE_CADENCE, args), indent=2)


@mcp.tool()
def find_alternative(name: str, limit: int = 10) -> str:
    """Suggest healthier conda-forge packages for an archived/abandoned
    one. Combines keyword/summary/dependent/maintainer Jaccard overlap
    with recency × downloads × non-archived filter."""
    args = ["--json", "--limit", str(limit), name]
    return json.dumps(_run_script(ATLAS_FIND_ALTERNATIVE, args), indent=2)


@mcp.tool()
def adoption_stage(
    package: str | None = None,
    maintainer: str | None = None,
    limit: int = 30,
) -> str:
    """Lifecycle stage classifier — bleeding-edge / stable / mature /
    declining / silent. Combines age + release cadence + total downloads.
    Use for triaging "is this still alive?" questions across a maintainer's
    portfolio or evaluating one specific package's maturity."""
    args = ["--json", "--limit", str(limit)]
    if package:
        args.extend(["--package", package])
    if maintainer:
        args.extend(["--maintainer", maintainer])
    return json.dumps(_run_script(ATLAS_ADOPTION_STAGE, args), indent=2)


@mcp.tool()
def package_health(name: str) -> str:
    """Full health card for one package — combines Phase B/E/F/G/H/J/K/M/N
    signals into a single rendered detail card. Includes downloads, vulns,
    upstream-version comparison, dependency reach, bot-PR status, GitHub
    CI/issues/PRs status, archived-feedstock detection, and channel
    storefront links. JSON output emits the raw record."""
    args = ["--json", name]
    return json.dumps(_run_script(ATLAS_DETAIL_CF_ATLAS, args), indent=2)


@mcp.tool()
def query_atlas(
    where: str | None = None,
    select: str = "conda_name, latest_conda_version, total_downloads, "
                  "vuln_critical_affecting_current, latest_status",
    order_by: str = "total_downloads DESC",
    limit: int = 25,
) -> str:
    """Generic cf_atlas SQLite query against the `packages` table.

    Defensive: only SELECT statements allowed; LIMIT is enforced. Use this
    when none of the higher-level tools (staleness_report, feedstock_health,
    behind_upstream, cve_watcher, etc.) match the question. The schema is
    documented in `cf_atlas.db` PRAGMA table_info(packages); side tables
    `dependencies`, `upstream_versions`, `vuln_history`, `vuln_history`,
    `package_version_downloads`, `package_version_vulns`,
    `upstream_versions_history` are also queryable via JOIN.
    """
    if any(kw in (where or "").upper() for kw in
           ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "ATTACH",
            "DETACH", "PRAGMA", "VACUUM")):
        return json.dumps({"error": "only SELECT-style WHERE clauses allowed"})
    if any(kw in select.upper() for kw in
           ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER")):
        return json.dumps({"error": "only column lists allowed in select"})
    import sqlite3 as _sql
    db_path = (
        Path(__file__).parent.parent
        / "data" / "conda-forge-expert" / "cf_atlas.db"
    )
    if not db_path.exists():
        return json.dumps({"error": f"cf_atlas.db missing at {db_path}"})
    sql = f"SELECT {select} FROM packages"
    if where:
        sql += f" WHERE {where}"
    sql += f" ORDER BY {order_by} LIMIT {min(int(limit), 1000)}"
    try:
        conn = _sql.connect(db_path)
        conn.row_factory = _sql.Row
        rows = [dict(r) for r in conn.execute(sql)]
        return json.dumps({"sql": sql, "rows": rows}, indent=2, default=str)
    except _sql.Error as e:
        return json.dumps({"error": f"SQL error: {e}", "sql": sql})


@mcp.tool()
def my_feedstocks(maintainer: str) -> str:
    """List all feedstocks where MAINTAINER is in the recipe-maintainers
    list. Returns name, version, downloads, status, archived flag — a
    portfolio-level overview. Use staleness_report / feedstock_health for
    deeper dives into specific signals."""
    return query_atlas(
        select=(
            "conda_name, feedstock_name, latest_conda_version, "
            "latest_conda_upload, total_downloads, latest_status, "
            "feedstock_archived, recipe_format, "
            "vuln_critical_affecting_current"
        ),
        where=(
            f"conda_name IS NOT NULL AND conda_name IN ("
            f"SELECT pm.conda_name FROM package_maintainers pm "
            f"JOIN maintainers m ON m.id = pm.maintainer_id "
            f"WHERE LOWER(m.handle) = LOWER('{maintainer}'))"
        ),
        order_by="total_downloads DESC",
        limit=1000,
    )


@mcp.tool()
def scan_project(
    project_path: str | None = None,
    image: str | None = None,
    sbom_in: str | None = None,
    conda_env: str | None = None,
    venv: str | None = None,
    helm_chart: str | None = None,
    kustomize: str | None = None,
    argo_app: str | None = None,
    flux_cr: str | None = None,
    license_check: bool = False,
    target_license: str | None = None,
    enrich_vulns_from_atlas: bool = False,
    brief: bool = True,
) -> str:
    """Vulnerability + license + atlas scan of a project, container image,
    SBOM, live env, or Kubernetes manifest. Exactly one input mode at a
    time: project_path / image / sbom_in / conda_env / venv / helm_chart /
    kustomize / argo_app / flux_cr.

    Output mode is JSON. license_check + target_license: produce a
    license-compatibility table instead of vuln scan. enrich_vulns_from_
    atlas: include cf_atlas Phase G counts as CycloneDX properties when
    emitting an SBOM (offline-safe; no vuln-db env required).
    """
    args: list[str] = ["--json"]
    if brief:
        args.append("--brief")
    if image:
        for img in image.split(","):
            args.extend(["--image", img.strip()])
    elif sbom_in:
        args.extend(["--sbom-in", sbom_in])
    elif conda_env:
        args.extend(["--conda-env", conda_env])
    elif venv:
        args.extend(["--venv", venv])
    elif helm_chart:
        args.extend(["--helm-chart", helm_chart])
    elif kustomize:
        args.extend(["--kustomize", kustomize])
    elif argo_app:
        args.extend(["--argo-app", argo_app])
    elif flux_cr:
        args.extend(["--flux-cr", flux_cr])
    elif project_path:
        args.append(project_path)
    if license_check:
        args.append("--license-check")
        if target_license:
            args.extend(["--target-license", target_license])
    if enrich_vulns_from_atlas:
        args.append("--enrich-vulns-from-atlas")
    return json.dumps(_run_script(ATLAS_SCAN_PROJECT, args, timeout=600),
                      indent=2)


if __name__ == "__main__":
    mcp.run()
