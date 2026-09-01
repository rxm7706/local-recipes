#!/usr/bin/env python3
"""
Build every **active** bmad-suite member into the local ``build_artifacts/``
channel (cheap → heavy), then ``recipes/bmad-suite``.

Members have no inter-package run dependencies; build order is fail-fast
(light skill payloads first, npm/dashboard compiles last) so an early failure
costs less time and the local channel accumulates artifacts for metapackage
test solvability (``native-build.sh`` auto-injects ``build_artifacts/<plat>/``).

Usage:
    python build_bmad_suite.py
    python build_bmad_suite.py --dry-run
    python build_bmad_suite.py --skip-existing
    python build_bmad_suite.py --continue-on-error
    python build_bmad_suite.py --members-only
"""
from __future__ import annotations

import argparse
import platform
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML is required") from exc

# Build-weight tiers — no inter-member deps; within-tier order matches manifest.
_TIER_LIGHT: tuple[str, ...] = (
    "bmad-builder",
    "bmad-creative-intelligence-suite",
    "bmad-method-wds-expansion",
    "bmad-utility-skills",
    "bmad-labs-skills",
    "bmad-module-template",
    "bmad-manticore",
)
_TIER_CORE: tuple[str, ...] = (
    "bmad-method",
    "bmad-loop",
)
_TIER_HEAVY: tuple[str, ...] = (
    "bmad-method-test-architecture-enterprise",
    "bmad-module-skill-forge",
    "bmad-dashboard",
    "mybmad-dashboard",
)

_METAPACKAGE = "bmad-suite"
_MANIFEST = ("recipes", "bmad-suite", "suite-members.yaml")
_NATIVE_BUILD = (
    ".claude",
    "scripts",
    "conda-forge-expert",
    "native-build.sh",
)


def _repo_root(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / Path(*_MANIFEST)).is_file():
            return parent
    raise SystemExit("Could not locate repo root (pass --repo-root)")


def _load_active_members(manifest: Path) -> list[str]:
    data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
    members = data.get("members") or []
    active: list[str] = []
    for entry in members:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if not name or entry.get("deprecated"):
            continue
        active.append(str(name))
    if not active:
        raise SystemExit(f"No active members in {manifest}")
    return active


def _tier_rank(name: str) -> tuple[int, int]:
    for tier, names in enumerate((_TIER_LIGHT, _TIER_CORE, _TIER_HEAVY)):
        if name in names:
            return tier, names.index(name)
    return 0, 999


def _build_order(active: list[str]) -> list[str]:
    return sorted(active, key=_tier_rank)


def _host_is_windows() -> bool:
    return platform.system().lower() == "windows" or sys.platform in {
        "win32",
        "cygwin",
    }


def _artifact_exists(repo_root: Path, package: str) -> bool:
    artifacts = repo_root / "build_artifacts"
    if not artifacts.is_dir():
        return False
    return any(artifacts.rglob(f"{package}-*.conda"))


def _run_build(
    repo_root: Path,
    recipe_rel: str,
    *,
    dry_run: bool,
) -> int:
    native = repo_root / Path(*_NATIVE_BUILD)
    if not native.is_file():
        raise SystemExit(f"native-build.sh not found: {native}")
    cmd = ["bash", str(native), recipe_rel]
    print(f"\n→ {' '.join(cmd)}", flush=True)
    if dry_run:
        return 0
    return subprocess.run(cmd, cwd=repo_root, check=False).returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build active bmad-suite members, then the metapackage.",
    )
    parser.add_argument("--repo-root", type=Path, default=None)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print build plan and commands without running rattler-build",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip members already present in build_artifacts/**/*.conda",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Keep building after a member failure (metapackage still attempted)",
    )
    parser.add_argument(
        "--members-only",
        action="store_true",
        help="Build members only; skip the bmad-suite metapackage",
    )
    args = parser.parse_args(argv)

    repo_root = _repo_root(args.repo_root)
    manifest = repo_root / Path(*_MANIFEST)
    active = _load_active_members(manifest)
    ordered = _build_order(active)

    if _host_is_windows():
        ordered = [n for n in ordered if n != "mybmad-dashboard"]
        print(
            "note: skipping mybmad-dashboard on Windows (recipe skip: win)",
            flush=True,
        )

    plan: list[str] = list(ordered)
    if not args.members_only:
        plan.append(_METAPACKAGE)

    print("bmad-suite local build plan (active members → metapackage):", flush=True)
    for i, name in enumerate(plan, start=1):
        tag = "metapackage" if name == _METAPACKAGE else "member"
        print(f"  {i:2}. {name} ({tag})", flush=True)

    failures: list[str] = []
    for name in plan:
        if args.skip_existing and _artifact_exists(repo_root, name):
            print(f"\n⊘ skip-existing: {name}", flush=True)
            continue

        recipe_rel = f"recipes/{name}"
        recipe_dir = repo_root / recipe_rel
        if not (recipe_dir / "recipe.yaml").is_file():
            msg = f"missing recipe: {recipe_dir / 'recipe.yaml'}"
            print(f"\n✗ {name}: {msg}", flush=True)
            failures.append(name)
            if not args.continue_on_error:
                return 1
            continue

        rc = _run_build(repo_root, recipe_rel, dry_run=args.dry_run)
        if rc != 0:
            print(f"\n✗ {name}: build failed (exit {rc})", flush=True)
            failures.append(name)
            if not args.continue_on_error:
                return rc

    if failures:
        print(
            f"\n✗ finished with {len(failures)} failure(s): {', '.join(failures)}",
            flush=True,
        )
        return 1

    print("\n✓ bmad-suite build chain complete", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
