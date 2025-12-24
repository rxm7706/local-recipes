#!/usr/bin/env python3
"""
Test recipes directly on all platforms without the CI workflow that removes recipes in main.

This script allows testing individual recipes or random samples using
rattler-build (for recipe.yaml) or conda-build (for meta.yaml).

Supports:
  - Windows: Native builds
  - macOS: Native builds (requires OSX_SDK_DIR)
  - Linux: Docker-based builds (requires Docker)

Usage:
    python test-recipes.py                         # Interactive mode
    python test-recipes.py --random 10             # Test 10 random recipes on current platform
    python test-recipes.py --random 10 --all       # Test on all platforms
    python test-recipes.py --recipe airflow        # Test specific recipe
    python test-recipes.py --recipe airflow --all  # Test on all platforms
    python test-recipes.py --list                  # List all recipes
    python test-recipes.py --dry-run --random 5    # Show what would be tested
"""

import argparse
import os
import random
import subprocess
import sys
import shutil
from pathlib import Path


PLATFORMS = {
    "win-64": {"name": "Windows 64-bit", "method": "native"},
    "linux-64": {"name": "Linux 64-bit", "method": "wsl_or_docker"},
    "osx-64": {"name": "macOS x86_64", "method": "native"},
    "osx-arm64": {"name": "macOS ARM64", "method": "native"},
}


def get_host_platform():
    """Get the current host platform identifier."""
    if sys.platform == "linux" or sys.platform == "linux2":
        return "linux-64"
    elif sys.platform == "darwin":
        import platform
        arch = "arm64" if platform.machine() == "arm64" else "64"
        return f"osx-{arch}"
    elif sys.platform == "win32":
        return "win-64"
    else:
        raise RuntimeError(f"Unsupported platform: {sys.platform}")


def get_recipes_dir():
    """Get the recipes directory path."""
    script_dir = Path(__file__).parent
    return script_dir / "recipes"


def get_script_dir():
    """Get the script directory path."""
    return Path(__file__).parent


def list_recipes():
    """List all recipe directories."""
    recipes_dir = get_recipes_dir()
    excluded = {".idea", "example", "example-new-recipe", "broken-recipes"}

    recipes = []
    for item in recipes_dir.iterdir():
        if item.is_dir() and item.name not in excluded:
            has_meta = (item / "meta.yaml").exists()
            has_recipe = (item / "recipe.yaml").exists()
            if has_meta or has_recipe:
                recipe_type = "recipe.yaml" if has_recipe else "meta.yaml"
                recipes.append((item.name, recipe_type))

    return sorted(recipes, key=lambda x: x[0])


def get_recipe_type(recipe_name):
    """Determine if recipe uses meta.yaml or recipe.yaml."""
    recipes_dir = get_recipes_dir()
    recipe_path = recipes_dir / recipe_name

    if (recipe_path / "recipe.yaml").exists():
        return "recipe.yaml"
    elif (recipe_path / "meta.yaml").exists():
        return "meta.yaml"
    return None


def check_docker():
    """Check if Docker is available."""
    return shutil.which("docker") is not None


def check_wsl():
    """Check if WSL is available (Windows only)."""
    if sys.platform != "win32":
        return False
    try:
        result = subprocess.run(
            ["wsl", "--list", "--quiet"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0 and result.stdout.strip() != ""
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def check_rattler_build():
    """Check if rattler-build is available."""
    return shutil.which("rattler-build") is not None


def check_conda_build():
    """Check if conda-build is available."""
    return shutil.which("conda-build") is not None


def get_wsl_path(windows_path):
    """Convert Windows path to WSL path."""
    path = Path(windows_path).resolve()
    # Convert C:\path\to\file to /mnt/c/path/to/file
    drive = path.drive.lower().replace(":", "")
    rest = str(path)[len(path.drive):].replace("\\", "/")
    return f"/mnt/{drive}{rest}"


def build_with_rattler_native(recipe_name, platform, dry_run=False):
    """Build a recipe using rattler-build natively."""
    recipes_dir = get_recipes_dir()
    recipe_path = recipes_dir / recipe_name
    script_dir = get_script_dir()

    parts = platform.split("-")
    plat, arch = parts[0], parts[1]
    variant_config = script_dir / ".ci_support" / f"{plat}{arch}.yaml"

    cmd = [
        "rattler-build", "build",
        "--recipe", str(recipe_path / "recipe.yaml"),
        "--target-platform", platform,
        "-c", "conda-forge",
    ]

    if variant_config.exists():
        cmd.extend(["--variant-config", str(variant_config)])

    print(f"\n{'='*60}")
    print(f"[{platform}] Building {recipe_name} with rattler-build")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}\n")

    if dry_run:
        print("[DRY RUN] Would execute the command above")
        return True

    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Build failed for {recipe_name} on {platform}: {e}")
        return False


def build_with_conda_native(recipe_name, platform, dry_run=False):
    """Build a recipe using conda-build natively."""
    recipes_dir = get_recipes_dir()
    recipe_path = recipes_dir / recipe_name
    script_dir = get_script_dir()

    parts = platform.split("-")
    plat, arch = parts[0], parts[1]
    variant_config = script_dir / ".ci_support" / f"{plat}{arch}.yaml"

    cmd = [
        "conda-build",
        str(recipe_path),
        "-c", "conda-forge",
    ]

    if variant_config.exists():
        cmd.extend(["--variant-config-files", str(variant_config)])

    print(f"\n{'='*60}")
    print(f"[{platform}] Building {recipe_name} with conda-build")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}\n")

    if dry_run:
        print("[DRY RUN] Would execute the command above")
        return True

    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Build failed for {recipe_name} on {platform}: {e}")
        return False


def build_with_docker(recipe_name, recipe_type, platform, dry_run=False, linux_version="alma9"):
    """Build a recipe using Docker for Linux.

    Args:
        recipe_name: Name of the recipe to build
        recipe_type: Either "recipe.yaml" or "meta.yaml"
        platform: Target platform (linux-64, linux-aarch64)
        dry_run: If True, only print what would be done
        linux_version: Linux base image version (alma9, alma8, cos7)
    """
    script_dir = get_script_dir()
    recipes_dir = get_recipes_dir()
    recipe_path = recipes_dir / recipe_name

    parts = platform.split("-")
    plat, arch = parts[0], parts[1]

    # Docker image for conda-forge builds (quay.io registry)
    if arch == "aarch64":
        docker_image = f"quay.io/condaforge/linux-anvil-aarch64:{linux_version}"
    else:
        docker_image = f"quay.io/condaforge/linux-anvil-x86_64:{linux_version}"

    # Determine build command
    if recipe_type == "recipe.yaml":
        build_cmd = (
            f"rattler-build build "
            f"--recipe /recipe/recipe.yaml "
            f"--target-platform {platform} "
            f"-c conda-forge"
        )
    else:
        build_cmd = f"conda-build /recipe -c conda-forge"

    docker_cmd = [
        "docker", "run", "--rm",
        "-v", f"{recipe_path}:/recipe:ro",
        "-v", f"{script_dir / '.ci_support'}:/ci_support:ro",
        docker_image,
        "bash", "-c",
        f"micromamba install -y -n base rattler-build conda-build && {build_cmd}"
    ]

    print(f"\n{'='*60}")
    print(f"[{platform}] Building {recipe_name} with Docker")
    print(f"Image: {docker_image}")
    print(f"Command: {' '.join(docker_cmd[:6])}...")
    print(f"{'='*60}\n")

    if dry_run:
        print("[DRY RUN] Would execute Docker command")
        return True

    try:
        subprocess.run(docker_cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Build failed for {recipe_name} on {platform}: {e}")
        return False


def build_with_wsl(recipe_name, recipe_type, platform, dry_run=False):
    """Build a recipe using WSL for Linux builds from Windows.

    Note: Only recipe.yaml (rattler-build) works reliably with WSL when the
    project is on the Windows filesystem. For meta.yaml, use Docker instead.
    """
    if recipe_type != "recipe.yaml":
        # meta.yaml with conda-build doesn't work well with WSL + Windows filesystem
        # Fall back to Docker
        print(f"Note: meta.yaml recipes require Docker on WSL (conda-build compatibility issue)")
        return None  # Signal to use Docker fallback

    script_dir = get_script_dir()
    recipes_dir = get_recipes_dir()
    recipe_path = recipes_dir / recipe_name

    # Convert paths to WSL format
    wsl_recipe_path = get_wsl_path(recipe_path)
    wsl_script_dir = get_wsl_path(script_dir)

    parts = platform.split("-")
    plat, arch = parts[0], parts[1]
    variant_config = f"{wsl_script_dir}/.ci_support/{plat}{arch}.yaml"

    # Use pixi to run rattler-build (handles path translation better)
    # Detect pixi location in WSL - check common locations
    build_cmd = (
        f"cd {wsl_script_dir} && "
        f"PIXI_PATH=$(command -v pixi || echo $HOME/.pixi/bin/pixi) && "
        f"$PIXI_PATH run -e build "
        f"rattler-build build "
        f"--recipe {wsl_recipe_path}/recipe.yaml "
        f"--target-platform {platform} "
        f"-c conda-forge "
        f"--variant-config {variant_config}"
    )

    wsl_cmd = ["wsl", "bash", "-c", build_cmd]

    print(f"\n{'='*60}")
    print(f"[{platform}] Building {recipe_name} with WSL (pixi + rattler-build)")
    print(f"Recipe path: {wsl_recipe_path}")
    print(f"{'='*60}\n")

    if dry_run:
        print("[DRY RUN] Would execute WSL command")
        print(f"  wsl bash -c \"cd {wsl_script_dir} && pixi run -e build rattler-build build ...\"")
        return True

    try:
        subprocess.run(wsl_cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Build failed for {recipe_name} on {platform}: {e}")
        return False


def build_recipe(recipe_name, platform, dry_run=False):
    """Build a single recipe on the specified platform."""
    recipe_type = get_recipe_type(recipe_name)
    host_platform = get_host_platform()

    if recipe_type is None:
        print(f"Recipe {recipe_name} not found or has no recipe file")
        return False

    platform_info = PLATFORMS.get(platform)
    if not platform_info:
        print(f"Unknown platform: {platform}")
        return False

    # Determine build method
    if platform.startswith("linux"):
        # Linux: native if on Linux, otherwise WSL or Docker
        if host_platform.startswith("linux"):
            # Native Linux build
            if recipe_type == "recipe.yaml":
                return build_with_rattler_native(recipe_name, platform, dry_run)
            else:
                return build_with_conda_native(recipe_name, platform, dry_run)
        elif check_wsl():
            # WSL build from Windows (preferred for recipe.yaml)
            result = build_with_wsl(recipe_name, recipe_type, platform, dry_run)
            if result is not None:
                return result
            # WSL returned None, try Docker fallback for meta.yaml
            if check_docker():
                return build_with_docker(recipe_name, recipe_type, platform, dry_run)
            else:
                print(f"Docker required for meta.yaml builds on WSL but not found")
                return False
        elif check_docker():
            # Docker build from non-Linux host
            return build_with_docker(recipe_name, recipe_type, platform, dry_run)
        else:
            print(f"WSL or Docker required for Linux builds but neither found")
            return False

    elif platform.startswith("osx"):
        # macOS requires native macOS host
        if not host_platform.startswith("osx"):
            print(f"Cannot build {platform} on {host_platform} - macOS host required")
            return False

        # Check for SDK
        if not os.environ.get("OSX_SDK_DIR"):
            print(f"Warning: OSX_SDK_DIR not set. macOS builds may fail.")

        if recipe_type == "recipe.yaml":
            return build_with_rattler_native(recipe_name, platform, dry_run)
        else:
            return build_with_conda_native(recipe_name, platform, dry_run)

    elif platform.startswith("win"):
        # Windows requires native Windows host
        if not host_platform.startswith("win"):
            print(f"Cannot build {platform} on {host_platform} - Windows host required")
            return False

        if recipe_type == "recipe.yaml":
            return build_with_rattler_native(recipe_name, platform, dry_run)
        else:
            return build_with_conda_native(recipe_name, platform, dry_run)

    return False


def get_available_platforms():
    """Get platforms available for building on this host."""
    host = get_host_platform()
    available = []

    for platform, info in PLATFORMS.items():
        if platform.startswith("linux"):
            # Linux available via WSL, Docker, or native
            if host.startswith("linux") or check_wsl() or check_docker():
                available.append(platform)
        elif platform.startswith("osx"):
            # macOS only from macOS host (no virtualization allowed)
            if host.startswith("osx"):
                available.append(platform)
        elif platform.startswith("win"):
            # Windows only from Windows host
            if host.startswith("win"):
                available.append(platform)

    return available


def main():
    parser = argparse.ArgumentParser(
        description="Test recipes on all platforms",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--recipe", "-r",
        nargs="+",
        help="Specific recipe(s) to test"
    )
    parser.add_argument(
        "--random", "-n",
        type=int,
        metavar="N",
        help="Test N random recipes"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List all available recipes"
    )
    parser.add_argument(
        "--dry-run", "-d",
        action="store_true",
        help="Show what would be tested without actually building"
    )
    parser.add_argument(
        "--platform", "-p",
        nargs="+",
        choices=list(PLATFORMS.keys()),
        help="Target platform(s) (default: current platform)"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Test on all available platforms"
    )
    parser.add_argument(
        "--filter", "-f",
        help="Filter recipes by name pattern (e.g., 'air*')"
    )
    parser.add_argument(
        "--type", "-t",
        choices=["meta.yaml", "recipe.yaml"],
        help="Only test recipes of a specific type"
    )
    parser.add_argument(
        "--stop-on-error", "-s",
        action="store_true",
        help="Stop on first build error"
    )
    parser.add_argument(
        "--check", "-c",
        action="store_true",
        help="Check available build tools and platforms"
    )

    args = parser.parse_args()

    # Check mode
    if args.check:
        print("Build Tool Availability:")
        print(f"  rattler-build: {'YES' if check_rattler_build() else 'NO'}")
        print(f"  conda-build:   {'YES' if check_conda_build() else 'NO'}")
        print(f"  wsl:           {'YES' if check_wsl() else 'NO'}")
        print(f"  docker:        {'YES' if check_docker() else 'NO'}")
        print()
        print(f"Host platform: {get_host_platform()}")
        print()
        print("Available build platforms:")
        for p in get_available_platforms():
            method = "native"
            if p.startswith("linux"):
                if check_wsl():
                    method = "via WSL"
                elif check_docker():
                    method = "via Docker"
            print(f"  - {p} ({PLATFORMS[p]['name']}) [{method}]")
        print()
        print("Note: macOS builds require a Mac computer (no virtualization)")
        return

    # Determine platforms
    host_platform = get_host_platform()
    available_platforms = get_available_platforms()

    if args.all:
        target_platforms = available_platforms
    elif args.platform:
        target_platforms = args.platform
        # Validate platforms are available
        for p in target_platforms:
            if p not in available_platforms:
                print(f"Warning: {p} not available on this host")
    else:
        target_platforms = [host_platform]

    print(f"Host platform: {host_platform}")
    print(f"Target platforms: {', '.join(target_platforms)}")

    # List recipes mode
    if args.list:
        recipes = list_recipes()
        print(f"\nFound {len(recipes)} recipes:\n")

        meta_count = sum(1 for _, t in recipes if t == "meta.yaml")
        recipe_count = sum(1 for _, t in recipes if t == "recipe.yaml")

        print(f"  meta.yaml:   {meta_count}")
        print(f"  recipe.yaml: {recipe_count}")
        print()

        for name, rtype in recipes:
            print(f"  {name:40} [{rtype}]")
        return

    # Get list of recipes to test
    all_recipes = list_recipes()

    # Apply filters
    if args.filter:
        import fnmatch
        all_recipes = [(n, t) for n, t in all_recipes if fnmatch.fnmatch(n, args.filter)]

    if args.type:
        all_recipes = [(n, t) for n, t in all_recipes if t == args.type]

    # Determine which recipes to build
    if args.recipe:
        recipes_to_test = [(r, get_recipe_type(r)) for r in args.recipe]
        recipes_to_test = [(n, t) for n, t in recipes_to_test if t is not None]
    elif args.random:
        count = min(args.random, len(all_recipes))
        recipes_to_test = random.sample(all_recipes, count)
    else:
        # Interactive mode
        print(f"\nFound {len(all_recipes)} recipes.")
        print("Options:")
        print("  1. Test all recipes")
        print("  2. Test random sample")
        print("  3. Enter specific recipe name")
        print("  4. Exit")

        try:
            choice = input("\nChoice [1-4]: ").strip()
        except KeyboardInterrupt:
            print("\nExiting.")
            return

        if choice == "1":
            recipes_to_test = all_recipes
        elif choice == "2":
            try:
                n = int(input("How many random recipes? ").strip())
                n = min(n, len(all_recipes))
                recipes_to_test = random.sample(all_recipes, n)
            except (ValueError, KeyboardInterrupt):
                print("\nExiting.")
                return
        elif choice == "3":
            try:
                name = input("Recipe name: ").strip()
                rtype = get_recipe_type(name)
                if rtype:
                    recipes_to_test = [(name, rtype)]
                else:
                    print(f"Recipe '{name}' not found")
                    return
            except KeyboardInterrupt:
                print("\nExiting.")
                return
        else:
            print("Exiting.")
            return

    if not recipes_to_test:
        print("No recipes to test.")
        return

    # Summary
    total_builds = len(recipes_to_test) * len(target_platforms)
    print(f"\nTest Plan:")
    print(f"  Recipes:   {len(recipes_to_test)}")
    print(f"  Platforms: {len(target_platforms)}")
    print(f"  Total builds: {total_builds}")
    print(f"\nRecipes:")
    for name, rtype in recipes_to_test:
        print(f"  - {name} [{rtype}]")
    print(f"\nPlatforms:")
    for p in target_platforms:
        print(f"  - {p}")

    if not args.dry_run:
        try:
            confirm = input("\nProceed? [y/N]: ").strip().lower()
            if confirm != "y":
                print("Aborted.")
                return
        except KeyboardInterrupt:
            print("\nAborted.")
            return

    # Build recipes on each platform
    results = {}
    for platform in target_platforms:
        results[platform] = {"success": [], "failed": [], "skipped": []}

    for name, rtype in recipes_to_test:
        for platform in target_platforms:
            if platform not in available_platforms:
                results[platform]["skipped"].append(name)
                continue

            success = build_recipe(name, platform, args.dry_run)

            if success:
                results[platform]["success"].append(name)
            else:
                results[platform]["failed"].append(name)
                if args.stop_on_error:
                    print(f"\nStopping due to --stop-on-error flag")
                    break
        else:
            continue
        break  # Break outer loop if inner loop broke

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    any_failed = False
    for platform in target_platforms:
        r = results[platform]
        print(f"\n{platform}:")
        print(f"  Success: {len(r['success'])}")
        print(f"  Failed:  {len(r['failed'])}")
        print(f"  Skipped: {len(r['skipped'])}")

        if r["failed"]:
            any_failed = True
            print(f"  Failed recipes:")
            for name in r["failed"]:
                print(f"    - {name}")

    # Exit with error code if any failed
    if any_failed and not args.dry_run:
        sys.exit(1)


if __name__ == "__main__":
    main()