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
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import requests
import yaml
from requests.adapters import HTTPAdapter

CHUNK_SIZE = 1 << 20  # 1 MiB
HEARTBEAT_INTERVAL = 30.0  # seconds; CI logs stay alive during slow in-flight GETs
_THREAD_LOCAL = threading.local()


def _http_session() -> requests.Session:
    """One keep-alive session per worker thread (Session is not thread-safe)."""
    session = getattr(_THREAD_LOCAL, "session", None)
    if session is None:
        session = requests.Session()
        adapter = HTTPAdapter(pool_connections=1, pool_maxsize=1, max_retries=3)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        _THREAD_LOCAL.session = session
    return session


def _request_timeout(total_seconds: int) -> tuple[int, int]:
    """Split connect vs read so a dead TCP peer cannot stall a worker for the
    full read budget (CI mirror builds issue hundreds of parallel GETs)."""
    connect = min(30, total_seconds)
    return connect, total_seconds


def _positive_int(value: str) -> int:
    """argparse `type=` for `--workers`: rejects 0/negative before it ever
    reaches `ThreadPoolExecutor(max_workers=...)`, which raises its own
    unguarded `ValueError` for either."""
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError(f"must be >= 1, got {parsed}")
    return parsed


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
    if len(conda_entries) != len(env_packages):
        non_conda = [e for e in env_packages if "conda" not in e]
        non_conda_keys = sorted({k for e in non_conda for k in e})
        raise MirrorBuildError(
            f"pixi.lock's {environment!r}/{platform!r} package list has "
            f"{len(non_conda)} non-conda entry(ies) this script does not know how "
            f"to mirror (kind(s): {', '.join(non_conda_keys) or '<empty>'}) -- "
            "the mirror would be silently incomplete"
        )

    catalog = {e["conda"]: e for e in (lockfile.get("packages") or []) if "conda" in e}

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
    if dest_path.exists():
        try:
            already_valid = _sha256_of(dest_path) == target.sha256
        except OSError:
            # A stale directory at this path, a permission error, or
            # anything else that stops us READING it -- not proof the file
            # is invalid, but also not something worth failing over: fall
            # through and let the normal download-and-overwrite path below
            # sort it out (or surface a clearer error from there).
            already_valid = False
        if already_valid:
            return "skipped"

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = dest_path.with_name(dest_path.name + ".part")
    try:
        with _http_session().get(
            target.url, stream=True, timeout=_request_timeout(timeout)
        ) as response:
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


def _format_progress(completed: int, total: int, downloaded: int, skipped: int, failed: int) -> str:
    return (
        f"  ... {completed}/{total} ({downloaded} downloaded, "
        f"{skipped} skipped, {failed} failed)"
    )


def _progress_heartbeat(
    stop: threading.Event,
    progress: dict[str, int],
    lock: threading.Lock,
    *,
    interval: float = HEARTBEAT_INTERVAL,
) -> None:
    """Emit progress on a wall clock even when no worker has finished yet."""
    while not stop.wait(interval):
        with lock:
            completed = progress["completed"]
            total = progress["total"]
            downloaded = progress["downloaded"]
            skipped = progress["skipped"]
            failed = progress["failed"]
        if completed >= total:
            break
        print(_format_progress(completed, total, downloaded, skipped, failed), flush=True)


def build_mirror(
    targets: list[MirrorTarget], dest_root: Path, workers: int, timeout: int
) -> tuple[int, int]:
    """Download every target (skipping already-valid files). Raises
    MirrorBuildError -- naming every failed package, not just the first --
    if any target failed."""
    # Dedup by destination path: two targets with the same dest_relpath
    # (same channel/subdir/filename -- pixi.lock listing the identical URL
    # twice for one platform) would otherwise race two threads writing/
    # renaming the same `.part`/destination file. `dict` preserves the
    # first-seen target per path, which is fine -- a true duplicate has
    # the same url/sha256 by construction.
    deduped: dict[Path, MirrorTarget] = {}
    for target in targets:
        deduped.setdefault(target.dest_relpath, target)
    targets = list(deduped.values())

    total = len(targets)
    progress = {
        "completed": 0,
        "downloaded": 0,
        "skipped": 0,
        "failed": 0,
        "total": total,
    }
    progress_lock = threading.Lock()
    errors: list[str] = []
    stop_heartbeat = threading.Event()
    heartbeat = threading.Thread(
        target=_progress_heartbeat,
        args=(stop_heartbeat, progress, progress_lock),
        name="mirror-heartbeat",
        daemon=True,
    )
    heartbeat.start()

    try:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(_download_one, target, dest_root, timeout): target
                for target in targets
            }
            for future in as_completed(futures):
                try:
                    result = future.result()
                except MirrorBuildError as exc:
                    with progress_lock:
                        progress["completed"] += 1
                        progress["failed"] += 1
                        completed = progress["completed"]
                        downloaded = progress["downloaded"]
                        skipped = progress["skipped"]
                        failed = progress["failed"]
                    errors.append(str(exc))
                else:
                    with progress_lock:
                        progress["completed"] += 1
                        if result == "downloaded":
                            progress["downloaded"] += 1
                        else:
                            progress["skipped"] += 1
                        completed = progress["completed"]
                        downloaded = progress["downloaded"]
                        skipped = progress["skipped"]
                        failed = progress["failed"]
                # Count-based line on fast runs; the background heartbeat
                # covers wall-clock gaps while large packages are in flight.
                if completed % 20 == 0 or completed == total:
                    print(
                        _format_progress(completed, total, downloaded, skipped, failed),
                        flush=True,
                    )
    finally:
        stop_heartbeat.set()
        heartbeat.join(timeout=1.0)

    if errors:
        raise MirrorBuildError("\n".join(errors))

    return progress["downloaded"], progress["skipped"]


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
        "--workers", type=_positive_int, default=16, help="Concurrent downloads (default: 16)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Per-request read timeout in seconds (connect capped at 30; default: 120)",
    )
    args = parser.parse_args(argv)

    if not args.lockfile.exists():
        print(f"::error::lockfile not found: {args.lockfile}", file=sys.stderr)
        return 1

    try:
        with args.lockfile.open() as f:
            lockfile = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        print(f"::error::{args.lockfile} is not valid YAML: {exc}", file=sys.stderr)
        return 1

    try:
        targets = parse_mirror_targets(lockfile, args.environment, args.platform)
    except MirrorBuildError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1

    args.dest.mkdir(parents=True, exist_ok=True)
    print(
        f"Mirroring {len(targets)} packages from {args.environment}/{args.platform} "
        f"into {args.dest}",
        flush=True,
    )

    try:
        downloaded, skipped = build_mirror(targets, args.dest, args.workers, args.timeout)
    except MirrorBuildError as exc:
        print(f"::error::mirror build failed:\n{exc}", file=sys.stderr)
        return 1

    print(
        f"Mirror complete: {downloaded} downloaded, {skipped} already valid (skipped), "
        f"{len(targets)} total",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
