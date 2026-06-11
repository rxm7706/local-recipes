#!/usr/bin/env python3
"""Check / apply upstream copilot-cli updates.

Multi-platform binary-repackage recipes don't fit the skill's generic
`update_recipe_from_github` tool: 5 conditional `source:` blocks per
target_platform + a secondary LICENSE.md source, all needing fresh sha256s
from upstream's signed `SHA256SUMS.txt`. This script handles that shape.

Usage:
    update.py --check          # Report current vs latest; exit 1 if outdated.
    update.py                  # Dry-run: print the changes that would apply.
    update.py --apply          # Update recipe.yaml in place.
    update.py --apply --build  # Apply, then rebuild and verify install (linux-64).

Notes:
    - Does NOT submit a PR. The recipe is unshippable under the upstream
      license (see DO_NOT_SUBMIT.md); this script is for local-channel
      maintenance only.
    - Warns loudly if LICENSE.md sha256 changes between releases — that
      could mean upstream relicensed, in which case DO_NOT_SUBMIT.md
      should be re-evaluated against the new terms.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import urllib.request

REPO = "github/copilot-cli"
RECIPE_DIR = pathlib.Path(__file__).resolve().parent
RECIPE_YAML = RECIPE_DIR / "recipe.yaml"
REPO_ROOT = RECIPE_DIR.parent.parent

# Maps recipe target_platform -> upstream release asset filename.
# Keep in sync with the `source:` blocks in recipe.yaml.
PLATFORM_ASSETS = {
    "linux-64":      "copilot-linux-x64.tar.gz",
    "linux-aarch64": "copilot-linux-arm64.tar.gz",
    "osx-arm64":     "copilot-darwin-arm64.tar.gz",
    "osx-64":        "copilot-darwin-x64.tar.gz",
    "win-64":        "copilot-win32-x64.zip",
}

LICENSE_URL = (
    "https://raw.githubusercontent.com/{repo}/refs/tags/v{version}/LICENSE.md"
)


def http_get(url: str) -> bytes:
    req = urllib.request.Request(
        url, headers={"User-Agent": "copilot-cli-recipe-updater"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def latest_release_tag() -> str:
    """Return the latest release tag, e.g. 'v1.0.61'."""
    try:
        return subprocess.check_output(
            ["gh", "release", "view", "--repo", REPO,
             "--json", "tagName", "-q", ".tagName"],
            text=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Public-repo API endpoint needs no auth.
        data = json.loads(
            http_get(f"https://api.github.com/repos/{REPO}/releases/latest")
        )
        return data["tag_name"]


def fetch_sha256sums(tag: str) -> dict[str, str]:
    body = http_get(
        f"https://github.com/{REPO}/releases/download/{tag}/SHA256SUMS.txt"
    ).decode()
    sums = {}
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        sha, fname = line.split(None, 1)
        sums[fname] = sha
    return sums


def fetch_license_sha(version: str) -> str:
    body = http_get(LICENSE_URL.format(repo=REPO, version=version))
    return hashlib.sha256(body).hexdigest()


def current_version(text: str) -> str:
    m = re.search(r'^\s*version:\s*"([^"]+)"', text, re.MULTILINE)
    if not m:
        sys.exit("ERROR: could not parse `context.version` from recipe.yaml")
    return m.group(1)


def current_license_sha(text: str) -> str | None:
    m = re.search(r"LICENSE\.md\s*\n\s*sha256:\s*([0-9a-f]{64})", text)
    return m.group(1) if m else None


def update_text(
    text: str,
    *,
    new_version: str,
    sha_map: dict[str, str],
    license_sha: str,
) -> tuple[str, list[tuple[str, str]]]:
    """Return (new_text, list_of_changes_for_logging)."""
    changes: list[tuple[str, str]] = []
    old_version = current_version(text)

    if new_version != old_version:
        text = re.sub(
            r'^(\s*version:\s*)"[^"]+"',
            rf'\g<1>"{new_version}"',
            text,
            count=1,
            flags=re.MULTILINE,
        )
        changes.append(("context.version", f"{old_version} -> {new_version}"))

    for target_platform, asset in PLATFORM_ASSETS.items():
        new_sha = sha_map.get(asset)
        if not new_sha:
            sys.exit(
                f"ERROR: {asset} not present in SHA256SUMS.txt — "
                "upstream release layout may have changed"
            )
        pat = re.compile(
            r"(url:\s*https://github\.com/"
            + re.escape(REPO)
            + r"/releases/download/v\$\{\{ version }}/"
            + re.escape(asset)
            + r"\s*\n\s*sha256:\s*)[0-9a-f]{64}"
        )
        text, n = pat.subn(rf"\g<1>{new_sha}", text)
        if n != 1:
            sys.exit(
                f"ERROR: could not locate sha256 line for {asset} "
                f"(matched {n} times)"
            )
        changes.append((f"source[{target_platform}].sha256", new_sha))

    lic_pat = re.compile(
        r"(url:\s*https://raw\.githubusercontent\.com/"
        + re.escape(REPO)
        + r"/refs/tags/v\$\{\{ version }}/LICENSE\.md\s*\n\s*sha256:\s*)"
        r"[0-9a-f]{64}"
    )
    text, n = lic_pat.subn(rf"\g<1>{license_sha}", text)
    if n != 1:
        sys.exit(
            f"ERROR: could not locate LICENSE.md sha256 line (matched {n} times)"
        )
    changes.append(("source[LICENSE.md].sha256", license_sha))

    return text, changes


def run_build_and_verify(version: str) -> int:
    rc = subprocess.call(
        ["pixi", "run", "-e", "local-recipes",
         "recipe-build", "recipes/copilot-cli"],
        cwd=REPO_ROOT,
    )
    if rc != 0:
        print("\nBuild failed.", file=sys.stderr)
        return rc

    channel = REPO_ROOT / "build_artifacts" / "linux64"
    rc = subprocess.call(
        ["pixi", "exec",
         "--channel", f"file://{channel}",
         "--channel", "conda-forge",
         "--spec", f"copilot-cli={version}",
         "--", "copilot", "--version"],
        cwd=REPO_ROOT,
    )
    if rc != 0:
        print("\nVerify install failed.", file=sys.stderr)
    return rc


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check", action="store_true",
        help="Report current vs latest; no changes (exit 1 if outdated).",
    )
    mode.add_argument(
        "--apply", action="store_true",
        help="Update recipe.yaml in place.",
    )
    parser.add_argument(
        "--build", action="store_true",
        help="After --apply, run recipe-build and verify install on linux-64.",
    )
    args = parser.parse_args()

    if args.build and not args.apply:
        parser.error("--build requires --apply")

    text = RECIPE_YAML.read_text()
    cur = current_version(text)
    latest_tag = latest_release_tag()
    latest = latest_tag.lstrip("v")

    print(f"Current: {cur}")
    print(f"Latest:  {latest}")

    if cur == latest:
        print("Recipe is up to date.")
        return 0

    if args.check:
        print("Update available.")
        return 1

    print(f"Fetching SHA256SUMS.txt for v{latest}...", file=sys.stderr)
    sums = fetch_sha256sums(latest_tag)
    print(f"Fetching LICENSE.md for v{latest}...", file=sys.stderr)
    new_lic_sha = fetch_license_sha(latest)

    old_lic_sha = current_license_sha(text)
    if old_lic_sha and old_lic_sha != new_lic_sha:
        print(
            "\n  WARNING: LICENSE.md sha256 CHANGED between current and latest.\n"
            "  Upstream may have relicensed. Re-read DO_NOT_SUBMIT.md and\n"
            "  diff the new LICENSE.md against the old one before applying.\n"
            f"    old: {old_lic_sha}\n"
            f"    new: {new_lic_sha}\n",
            file=sys.stderr,
        )

    new_text, changes = update_text(
        text, new_version=latest, sha_map=sums, license_sha=new_lic_sha,
    )

    if not args.apply:
        print()
        for field, value in changes:
            print(f"  {field}: {value}")
        print("\n(dry run — pass --apply to write changes)")
        return 0

    RECIPE_YAML.write_text(new_text)
    print(f"\nUpdated {RECIPE_YAML.name}: {cur} -> {latest}")

    if args.build:
        return run_build_and_verify(latest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
