#!/usr/bin/env python3
"""
Build a local, file-based conda channel mirror straight from `pixi.lock`.

Story 12.3 (spec-12-3-air-gap-parity-is-a-failing-check, AD-13/CAP-6): the
`air-gap-parity` CI job proves `pixi install --frozen -e platform-dev`
resolves from a FRESH cache using only a local mirror, with all
non-private-network egress blocked. This script builds that mirror BEFORE
the block goes up (network still on). It reads the target
environment/platform's exact package set directly out of `pixi.lock` --
never a live repodata fetch, unlike `scripts/mirror-channels.py`, which
resolves by package NAME against a channel's live `repodata.json` and can
pull a different build than what any one lockfile pinned -- so the mirror
this script produces is byte-for-byte what `pixi.lock` already resolved,
with no re-solve involved.

pixi.lock (schema v7) stores each locked package twice: once per
environment/platform as a bare `{conda: <url>}` pointer, and once in the
flat top-level `packages:` catalog carrying the full record (sha256, md5,
depends, ...). This script cross-references the two to get the sha256 a
per-environment entry omits.

Each package is downloaded into `<dest>/<channel>/<subdir>/<filename>`,
where `<channel>` is the last path segment of the package's host channel
URL (`conda-forge` or `SelfExplainML` for this workspace) and `<subdir>`
is its platform subdir (`linux-64`, `noarch`, ...) -- the exact shape
`.pixi/config.toml`'s `[mirrors]` table maps a channel URL onto
(`docs/reference/pixi-config-jfrog.example.toml` is the schema reference:
`{"<original-channel-url>" = ["<mirror-url>", ...]}`, here rewritten to
`file://<dest>/<channel>`).

Idempotent: a destination file that already matches its lockfile sha256 is
skipped, not re-downloaded, so re-running this script locally during a
network-available dry run does not re-fetch everything each time.

Usage:
    python scripts/build-pixi-mirror.py \\
        --lockfile pixi.lock --environment platform-dev --platform linux-64 \\
        --dest ci-airgap-mirror
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import requests
import yaml

CHUNK_SIZE = 1 << 20  # 1 MiB


class MirrorBuildError(RuntimeError):
    """Any condition that should halt the mirror build: schema drift in
    `pixi.lock` (no resolvable entries, a missing sha256), or a failed
    download/verification. All are hard failures -- this mirror is built
    while egress is still on, so a failure here is a real problem worth
    stopping the job for, never a warning to paper over."""


@dataclass(frozen=True)
class MirrorTarget:
    """One package's mirror-relative destination, derived from its
    pixi.lock URL."""

    url: str
    sha256: str
    channel: str
    subdir: str
    filename: str

    @property
    def dest_relpath(self) -> Path:
        return Path(self.channel) / self.subdir / self.filename


def parse_mirror_targets(
    lockfile: dict, environment: str, platform: str
) -> list[MirrorTarget]:
    """Resolve `environment`'s `platform` package set to MirrorTargets,
    cross-referencing pixi.lock's flat top-level `packages:` catalog for
    the sha256 each environment-scoped entry omits."""
    try:
        env_packages = lockfile["environments"][environment]["packages"][platform]
    except (KeyError, TypeError) as exc:
        raise MirrorBuildError(
            f"pixi.lock has no resolvable entries for environment={environment!r} "
            f"platform={platform!r} ({exc})"
        ) from exc

    conda_entries = [e for e in env_packages if "conda" in e]
    if not conda_entries:
        raise MirrorBuildError(
            f"pixi.lock's {environment!r}/{platform!r} package list is empty "
            "or has no conda-kind entries"
        )

    catalog = {e["conda"]: e for e in lockfile.get("packages", []) if "conda" in e}

    targets: list[MirrorTarget] = []
    for entry in conda_entries:
        url = entry["conda"]
        catalog_entry = catalog.get(url)
        if catalog_entry is None:
            raise MirrorBuildError(
                f"{url} is referenced by {environment}/{platform} but is missing "
                "from pixi.lock's top-level packages: catalog"
            )
        sha256 = catalog_entry.get("sha256")
        if not sha256:
            raise MirrorBuildError(
                f"{url} has no sha256 in pixi.lock -- cannot verify a mirrored download"
            )

        # https://conda.anaconda.org/<channel>/<subdir>/<filename>
        parts = urlparse(url).path.strip("/").split("/")
        if len(parts) < 3:
            raise MirrorBuildError(
                f"{url} does not look like a conda package URL "
                "(expected <channel>/<subdir>/<filename>)"
            )
        channel, subdir, filename = parts[-3], parts[-2], parts[-1]

        targets.append(
            MirrorTarget(
                url=url, sha256=sha256, channel=channel, subdir=subdir, filename=filename
            )
        )

    return targets


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download_one(target: MirrorTarget, dest_root: Path, timeout: int) -> str:
    """Download+verify one target into `dest_root`. Returns "downloaded" or
    "skipped" (already present and sha256-valid). Raises MirrorBuildError
    on any download or verification failure."""
    dest_path = dest_root / target.dest_relpath
    if dest_path.exists() and _sha256_of(dest_path) == target.sha256:
        return "skipped"

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = dest_path.with_name(dest_path.name + ".part")
    try:
        with requests.get(target.url, stream=True, timeout=timeout) as response:
            response.raise_for_status()
            with tmp_path.open("wb") as f:
                for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                    f.write(chunk)
    except requests.RequestException as exc:
        tmp_path.unlink(missing_ok=True)
        raise MirrorBuildError(f"download failed for {target.url}: {exc}") from exc

    actual = _sha256_of(tmp_path)
    if actual != target.sha256:
        tmp_path.unlink(missing_ok=True)
        raise MirrorBuildError(
            f"sha256 mismatch for {target.url}: expected {target.sha256}, got {actual}"
        )

    tmp_path.replace(dest_path)
    return "downloaded"


def build_mirror(
    targets: list[MirrorTarget], dest_root: Path, workers: int, timeout: int
) -> tuple[int, int]:
    """Download every target (skipping already-valid files). Raises
    MirrorBuildError -- naming every failed package, not just the first --
    if any target failed."""
    downloaded = 0
    skipped = 0
    errors: list[str] = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(_download_one, target, dest_root, timeout): target
            for target in targets
        }
        for future in as_completed(futures):
            try:
                result = future.result()
            except MirrorBuildError as exc:
                errors.append(str(exc))
                continue
            if result == "downloaded":
                downloaded += 1
            else:
                skipped += 1

    if errors:
        raise MirrorBuildError("\n".join(errors))

    return downloaded, skipped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a local file-based conda channel mirror from pixi.lock."
    )
    parser.add_argument("--lockfile", required=True, type=Path, help="Path to pixi.lock")
    parser.add_argument(
        "--environment", required=True, help="pixi environment name, e.g. platform-dev"
    )
    parser.add_argument("--platform", required=True, help="pixi platform, e.g. linux-64")
    parser.add_argument("--dest", required=True, type=Path, help="Mirror destination directory")
    parser.add_argument(
        "--workers", type=int, default=8, help="Concurrent downloads (default: 8)"
    )
    parser.add_argument(
        "--timeout", type=int, default=300, help="Per-request timeout in seconds (default: 300)"
    )
    args = parser.parse_args(argv)

    if not args.lockfile.exists():
        print(f"::error::lockfile not found: {args.lockfile}", file=sys.stderr)
        return 1

    with args.lockfile.open() as f:
        lockfile = yaml.safe_load(f)

    try:
        targets = parse_mirror_targets(lockfile, args.environment, args.platform)
    except MirrorBuildError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1

    args.dest.mkdir(parents=True, exist_ok=True)
    print(
        f"Mirroring {len(targets)} packages from {args.environment}/{args.platform} "
        f"into {args.dest}"
    )

    try:
        downloaded, skipped = build_mirror(targets, args.dest, args.workers, args.timeout)
    except MirrorBuildError as exc:
        print(f"::error::mirror build failed:\n{exc}", file=sys.stderr)
        return 1

    print(
        f"Mirror complete: {downloaded} downloaded, {skipped} already valid (skipped), "
        f"{len(targets)} total"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
