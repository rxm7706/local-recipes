#!/usr/bin/env python3
"""
install.py — Bootstrap the conda-forge-expert skill into a host repo.

Run once after dropping `.claude/skills/conda-forge-expert/` into a new
repo. Materializes the wrapper layer at `.claude/scripts/conda-forge-expert/`,
optionally copies the MCP server module, and offers to inject pixi tasks.
Idempotent — re-running on an already-installed skill is safe.

CLI:
  python install.py [--repo-root <path>] [--mcp] [--no-pixi-tasks] [--dry-run]

Defaults:
  --repo-root: auto-detect by walking up from this file (looking for `.git`
               or `pixi.toml`).
  --mcp:       false — pass to copy `conda_forge_server.py` into
               <repo>/.claude/tools/. Skill works without MCP for plain CLI use.
  --no-pixi-tasks: skip the pixi.toml task injection. Default behavior is to
               offer the injection but ask before writing.
  --dry-run:   print what would happen without writing anything.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent
SCRIPTS_DIR = SKILL_ROOT / "scripts"
MCP_SOURCE = SKILL_ROOT.parent.parent / "tools" / "conda_forge_server.py"


WRAPPER_TEMPLATE = '''#!/usr/bin/env python3
"""Wrapper. Canonical: skills/conda-forge-expert/scripts/{script_name}"""
import subprocess
import sys
from pathlib import Path

_SKILL_SCRIPT = (
    Path(__file__).parent.parent.parent
    / "skills" / "conda-forge-expert" / "scripts" / "{script_name}"
)

if __name__ == "__main__":
    sys.exit(subprocess.run([sys.executable, str(_SKILL_SCRIPT)] + sys.argv[1:]).returncode)
'''


def find_repo_root(start: Path) -> Path:
    """Walk up from `start` looking for `.git` or `pixi.toml` markers."""
    current = start.resolve()
    while current != current.parent:
        if (current / ".git").exists() or (current / "pixi.toml").exists():
            return current
        current = current.parent
    raise FileNotFoundError(
        "Could not auto-detect repo root. Pass --repo-root explicitly."
    )


def list_canonical_scripts(scripts_dir: Path) -> list[Path]:
    """Return the .py files in scripts/ that are user-facing CLIs.

    Excludes private modules (leading _), __pycache__ artifacts, and any
    underscore-prefixed helper modules.
    """
    out: list[Path] = []
    for p in sorted(scripts_dir.glob("*.py")):
        if p.name.startswith("_"):
            continue
        if p.stem.startswith("__"):
            continue
        out.append(p)
    return out


def materialize_wrappers(scripts_dir: Path, target_dir: Path,
                         dry_run: bool = False) -> tuple[int, int]:
    """Create thin subprocess wrappers in <repo>/.claude/scripts/conda-forge-expert/.

    Returns (created, skipped) counts.
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    created = skipped = 0
    for script in list_canonical_scripts(scripts_dir):
        wrapper_path = target_dir / script.name
        wrapper_body = WRAPPER_TEMPLATE.format(script_name=script.name)
        if wrapper_path.exists():
            existing = wrapper_path.read_text()
            if existing.strip() == wrapper_body.strip():
                skipped += 1
                continue
        if dry_run:
            print(f"  [dry-run] would write {wrapper_path}")
        else:
            wrapper_path.write_text(wrapper_body)
        created += 1
    return (created, skipped)


def copy_mcp_server(repo_root: Path, dry_run: bool = False) -> bool:
    """Copy conda_forge_server.py into <repo>/.claude/tools/."""
    if not MCP_SOURCE.exists():
        # Skill bundle was moved without the MCP server; that's fine
        print(f"  ⚠  MCP server source not found at {MCP_SOURCE}; "
              f"copy it manually if needed.")
        return False
    target = repo_root / ".claude" / "tools" / "conda_forge_server.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    if dry_run:
        print(f"  [dry-run] would copy MCP server to {target}")
        return True
    shutil.copy2(MCP_SOURCE, target)
    return True


def maybe_inject_pixi_tasks(repo_root: Path, dry_run: bool = False) -> bool:
    """Append cf-atlas pixi tasks to host pixi.toml if not already present.

    Idempotent — checks for the marker comment first.
    """
    pixi_path = repo_root / "pixi.toml"
    marker = "# === conda-forge-expert atlas tasks (managed by install.py) ==="
    if not pixi_path.exists():
        print(f"  No pixi.toml at {pixi_path}; skipping task injection.")
        return False
    existing = pixi_path.read_text()
    if marker in existing:
        return False  # already injected
    block = f"""

{marker}
[feature.local-recipes.tasks.build-cf-atlas]
description = "Build cf_atlas — cross-channel package map (offline-safe)"
cmd = "python .claude/scripts/conda-forge-expert/conda_forge_atlas.py build"

[feature.local-recipes.tasks.detail-cf-atlas]
description = "Per-package detail card with full v7.0 enrichment"
cmd = "python .claude/scripts/conda-forge-expert/detail_cf_atlas.py"

[feature.local-recipes.tasks.staleness-report]
description = "Stalest active feedstocks with --by-risk / --has-vulns / --bot-stuck filters"
cmd = "python .claude/scripts/conda-forge-expert/staleness_report.py"

[feature.local-recipes.tasks.feedstock-health]
description = "Feedstocks with stuck bots / failing CI / open issues / open PRs"
cmd = "python .claude/scripts/conda-forge-expert/feedstock_health.py"

[feature.local-recipes.tasks.whodepends]
description = "Phase J dependency graph queries (forward + reverse)"
cmd = "python .claude/scripts/conda-forge-expert/whodepends.py"

[feature.local-recipes.tasks.behind-upstream]
description = "Multi-source upstream-of-record comparison (PyPI/GitHub/GitLab/npm/CRAN/CPAN/Maven/...)"
cmd = "python .claude/scripts/conda-forge-expert/behind_upstream.py"

[feature.local-recipes.tasks.cve-watcher]
description = "Diff Phase G snapshots — what CVE counts changed since N days ago"
cmd = "python .claude/scripts/conda-forge-expert/cve_watcher.py"

[feature.local-recipes.tasks.version-downloads]
description = "Per-version download breakdown (Phase I)"
cmd = "python .claude/scripts/conda-forge-expert/version_downloads.py"

[feature.local-recipes.tasks.release-cadence]
description = "Release cadence trend classifier (accelerating/stable/decelerating/silent)"
cmd = "python .claude/scripts/conda-forge-expert/release_cadence.py"

[feature.local-recipes.tasks.find-alternative]
description = "Suggest healthier alternatives for archived/abandoned packages"
cmd = "python .claude/scripts/conda-forge-expert/find_alternative.py"

[feature.local-recipes.tasks.adoption-stage]
description = "Lifecycle stage classifier (bleeding-edge/stable/mature/declining/silent)"
cmd = "python .claude/scripts/conda-forge-expert/adoption_stage.py"
"""
    if dry_run:
        print(f"  [dry-run] would append {len(block.splitlines())} lines to {pixi_path}")
        return True
    pixi_path.write_text(existing.rstrip() + block)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1] if __doc__ else "")
    parser.add_argument("--repo-root", default=None,
                        help="Host repo root (auto-detect by default)")
    parser.add_argument("--mcp", action="store_true",
                        help="Also copy the MCP server module")
    parser.add_argument("--no-pixi-tasks", action="store_true", dest="no_pixi",
                        help="Skip the pixi.toml task injection")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would happen without writing")
    args = parser.parse_args()

    repo_root = (Path(args.repo_root).resolve() if args.repo_root
                 else find_repo_root(SKILL_ROOT))
    print(f"  Repo root:    {repo_root}")
    print(f"  Skill bundle: {SKILL_ROOT}")
    print(f"  Mode:         {'dry-run' if args.dry_run else 'live'}")
    print()

    print("→ Materializing CLI wrappers")
    target_wrappers = repo_root / ".claude" / "scripts" / "conda-forge-expert"
    created, skipped = materialize_wrappers(SCRIPTS_DIR, target_wrappers, args.dry_run)
    print(f"  {created} wrappers written, {skipped} already present.")
    print()

    if args.mcp:
        print("→ Copying MCP server")
        if copy_mcp_server(repo_root, args.dry_run):
            print(f"  conda_forge_server.py → {repo_root}/.claude/tools/")
        print()

    if not args.no_pixi:
        print("→ Injecting pixi tasks")
        if maybe_inject_pixi_tasks(repo_root, args.dry_run):
            print(f"  Tasks block appended to {repo_root}/pixi.toml")
        else:
            print("  (already present or pixi.toml missing — skipped)")
        print()

    # Optional-tools probe
    print("→ Optional tool probe")
    for tool in ("gh", "git", "rattler-build", "syft", "trivy", "kubectl",
                 "helm", "kustomize"):
        path = shutil.which(tool)
        marker = "✓" if path else "○"
        print(f"  {marker} {tool}{(' → ' + path) if path else ' (not installed)'}")
    print()

    print("Install complete. See INDEX.md for task → tool navigation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
