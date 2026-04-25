#!/usr/bin/env python3
"""
Mirror conda channels for air-gapped environments.

Usage:
    python mirror-channels.py --source conda-forge --dest /path/to/mirror --packages numpy pandas
    python mirror-channels.py --source conda-forge --dest /path/to/mirror --packages-file packages.txt
    python mirror-channels.py --verify /path/to/mirror
    python mirror-channels.py --cleanup /path/to/mirror --keep-versions 2
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


SUBDIRS = ["linux-64", "linux-aarch64", "osx-64", "osx-arm64", "win-64", "noarch"]

CHANNEL_URLS = {
    "conda-forge": "https://conda.anaconda.org/conda-forge",
    "defaults": "https://repo.anaconda.com/pkgs/main",
}


@dataclass
class Package:
    """Represents a conda package."""
    name: str
    version: str
    build: str
    subdir: str
    filename: str
    url: str
    sha256: str
    size: int
    depends: list[str]


def get_repodata(channel_url: str, subdir: str) -> dict:
    """Fetch and parse repodata.json for a channel subdir."""
    url = f"{channel_url}/{subdir}/repodata.json"
    print(f"Fetching repodata: {url}")

    response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.json()


def parse_packages(repodata: dict, channel_url: str, subdir: str) -> list[Package]:
    """Parse packages from repodata."""
    packages = []

    # Handle both .conda and .tar.bz2 formats
    for pkg_dict in [repodata.get("packages", {}), repodata.get("packages.conda", {})]:
        for filename, info in pkg_dict.items():
            packages.append(Package(
                name=info["name"],
                version=info["version"],
                build=info["build"],
                subdir=subdir,
                filename=filename,
                url=f"{channel_url}/{subdir}/{filename}",
                sha256=info.get("sha256", ""),
                size=info.get("size", 0),
                depends=info.get("depends", [])
            ))

    return packages


def resolve_dependencies(
    packages: list[Package],
    wanted: set[str],
    all_packages: dict[str, list[Package]]
) -> set[str]:
    """Resolve package dependencies recursively."""
    resolved = set()
    to_process = list(wanted)

    while to_process:
        name = to_process.pop()
        if name in resolved:
            continue
        resolved.add(name)

        # Find package in available packages
        for pkg_list in all_packages.values():
            for pkg in pkg_list:
                if pkg.name == name:
                    # Add dependencies
                    for dep in pkg.depends:
                        dep_name = dep.split()[0]  # Remove version spec
                        if dep_name not in resolved:
                            to_process.append(dep_name)
                    break

    return resolved


def download_package(pkg: Package, dest_dir: Path, verify: bool = True) -> bool:
    """Download a single package."""
    subdir_path = dest_dir / pkg.subdir
    subdir_path.mkdir(parents=True, exist_ok=True)

    dest_file = subdir_path / pkg.filename

    # Skip if already exists and verified
    if dest_file.exists():
        if verify and pkg.sha256:
            with open(dest_file, "rb") as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            if file_hash == pkg.sha256:
                return True
        elif not verify:
            return True

    # Download
    try:
        response = requests.get(pkg.url, stream=True, timeout=300)
        response.raise_for_status()

        with open(dest_file, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # Verify hash
        if verify and pkg.sha256:
            with open(dest_file, "rb") as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
            if file_hash != pkg.sha256:
                print(f"Hash mismatch for {pkg.filename}")
                dest_file.unlink()
                return False

        return True

    except Exception as e:
        print(f"Failed to download {pkg.filename}: {e}")
        return False


def index_channel(dest_dir: Path) -> bool:
    """Create repodata.json for mirrored channel."""
    try:
        # Try conda-index
        subprocess.run(
            ["conda-index", str(dest_dir)],
            check=True,
            capture_output=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # Fallback: create minimal repodata manually
    for subdir in SUBDIRS:
        subdir_path = dest_dir / subdir
        if not subdir_path.exists():
            continue

        packages = {}
        packages_conda = {}

        for pkg_file in subdir_path.glob("*.tar.bz2"):
            packages[pkg_file.name] = {"name": pkg_file.stem.rsplit("-", 2)[0]}

        for pkg_file in subdir_path.glob("*.conda"):
            packages_conda[pkg_file.name] = {"name": pkg_file.stem.rsplit("-", 2)[0]}

        repodata = {
            "packages": packages,
            "packages.conda": packages_conda,
        }

        with open(subdir_path / "repodata.json", "w") as f:
            json.dump(repodata, f)

    return True


def verify_mirror(dest_dir: Path) -> tuple[int, int]:
    """Verify integrity of mirrored packages."""
    valid = 0
    invalid = 0

    for subdir in SUBDIRS:
        subdir_path = dest_dir / subdir
        if not subdir_path.exists():
            continue

        repodata_path = subdir_path / "repodata.json"
        if not repodata_path.exists():
            continue

        with open(repodata_path) as f:
            repodata = json.load(f)

        for pkg_dict in [repodata.get("packages", {}), repodata.get("packages.conda", {})]:
            for filename, info in pkg_dict.items():
                pkg_path = subdir_path / filename
                if not pkg_path.exists():
                    print(f"Missing: {filename}")
                    invalid += 1
                    continue

                if "sha256" in info:
                    with open(pkg_path, "rb") as f:
                        file_hash = hashlib.sha256(f.read()).hexdigest()
                    if file_hash != info["sha256"]:
                        print(f"Hash mismatch: {filename}")
                        invalid += 1
                        continue

                valid += 1

    return valid, invalid


def cleanup_old_versions(dest_dir: Path, keep_versions: int = 2) -> int:
    """Remove old package versions, keeping only the N most recent."""
    removed = 0

    for subdir in SUBDIRS:
        subdir_path = dest_dir / subdir
        if not subdir_path.exists():
            continue

        # Group packages by name
        packages_by_name: dict[str, list[Path]] = {}

        for pkg_file in list(subdir_path.glob("*.conda")) + list(subdir_path.glob("*.tar.bz2")):
            # Parse name from filename: name-version-build.conda
            parts = pkg_file.stem.rsplit("-", 2)
            if len(parts) >= 2:
                name = parts[0]
                packages_by_name.setdefault(name, []).append(pkg_file)

        # Remove old versions
        for name, files in packages_by_name.items():
            # Sort by modification time, newest first
            files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

            for old_file in files[keep_versions:]:
                print(f"Removing: {old_file.name}")
                old_file.unlink()
                removed += 1

    return removed


def mirror_channel(
    source: str,
    dest: Path,
    packages: Optional[list[str]] = None,
    subdirs: Optional[list[str]] = None,
    workers: int = 4,
    resolve_deps: bool = True
) -> tuple[int, int]:
    """Mirror packages from a conda channel."""
    if not REQUESTS_AVAILABLE:
        print("Error: requests library required. Install with: pip install requests")
        return 0, 0

    channel_url = CHANNEL_URLS.get(source, source)
    subdirs = subdirs or SUBDIRS

    # Collect all packages
    all_packages: dict[str, list[Package]] = {}
    wanted_packages: set[str] = set(packages) if packages else set()

    for subdir in subdirs:
        try:
            repodata = get_repodata(channel_url, subdir)
            all_packages[subdir] = parse_packages(repodata, channel_url, subdir)

            # If no specific packages requested, mirror all
            if not packages:
                wanted_packages.update(pkg.name for pkg in all_packages[subdir])
        except Exception as e:
            print(f"Failed to fetch {subdir}: {e}")
            continue

    # Resolve dependencies
    if resolve_deps and packages:
        print("Resolving dependencies...")
        wanted_packages = resolve_dependencies(
            [], wanted_packages, all_packages
        )
        print(f"Total packages to mirror: {len(wanted_packages)}")

    # Filter packages to download
    to_download = []
    for subdir, pkg_list in all_packages.items():
        for pkg in pkg_list:
            if pkg.name in wanted_packages:
                to_download.append(pkg)

    # Download packages
    success = 0
    failed = 0

    print(f"Downloading {len(to_download)} packages...")

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(download_package, pkg, dest): pkg
            for pkg in to_download
        }

        for future in as_completed(futures):
            pkg = futures[future]
            try:
                if future.result():
                    success += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"Error downloading {pkg.filename}: {e}")
                failed += 1

            # Progress
            total = success + failed
            if total % 100 == 0:
                print(f"Progress: {total}/{len(to_download)}")

    # Index the mirror
    print("Indexing mirror...")
    index_channel(dest)

    return success, failed


def main():
    parser = argparse.ArgumentParser(
        description="Mirror conda channels for air-gapped environments"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command")

    # Mirror command
    mirror_parser = subparsers.add_parser("mirror", help="Mirror packages")
    mirror_parser.add_argument("--source", "-s", default="conda-forge",
                               help="Source channel name or URL")
    mirror_parser.add_argument("--dest", "-d", required=True, type=Path,
                               help="Destination directory")
    mirror_parser.add_argument("--packages", "-p", nargs="+",
                               help="Packages to mirror")
    mirror_parser.add_argument("--packages-file", "-f", type=Path,
                               help="File with package list (one per line)")
    mirror_parser.add_argument("--subdirs", nargs="+", default=SUBDIRS,
                               help="Subdirs to mirror")
    mirror_parser.add_argument("--workers", "-w", type=int, default=4,
                               help="Download workers")
    mirror_parser.add_argument("--no-deps", action="store_true",
                               help="Don't resolve dependencies")

    # Verify command
    verify_parser = subparsers.add_parser("verify", help="Verify mirror integrity")
    verify_parser.add_argument("path", type=Path, help="Mirror path")

    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Remove old versions")
    cleanup_parser.add_argument("path", type=Path, help="Mirror path")
    cleanup_parser.add_argument("--keep-versions", "-k", type=int, default=2,
                                help="Versions to keep per package")

    # Index command
    index_parser = subparsers.add_parser("index", help="Reindex mirror")
    index_parser.add_argument("path", type=Path, help="Mirror path")

    args = parser.parse_args()

    if args.command == "mirror":
        packages = args.packages or []
        if args.packages_file and args.packages_file.exists():
            packages.extend(
                line.strip() for line in args.packages_file.read_text().splitlines()
                if line.strip() and not line.startswith("#")
            )

        success, failed = mirror_channel(
            args.source,
            args.dest,
            packages=packages if packages else None,
            subdirs=args.subdirs,
            workers=args.workers,
            resolve_deps=not args.no_deps
        )
        print(f"Mirrored: {success} success, {failed} failed")
        sys.exit(1 if failed else 0)

    elif args.command == "verify":
        valid, invalid = verify_mirror(args.path)
        print(f"Verified: {valid} valid, {invalid} invalid")
        sys.exit(1 if invalid else 0)

    elif args.command == "cleanup":
        removed = cleanup_old_versions(args.path, args.keep_versions)
        print(f"Removed {removed} old packages")

    elif args.command == "index":
        if index_channel(args.path):
            print("Indexed successfully")
        else:
            print("Indexing failed")
            sys.exit(1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
