#!/usr/bin/env python3
"""
CVE Database Manager for the conda-forge-expert skill.

This script downloads the full vulnerability database from osv.dev for specified
ecosystems (e.g., PyPI), processes the data, and creates a local, indexed
database for fast lookups by the vulnerability scanner.
"""
from __future__ import annotations

import argparse
import json
import zipfile
import os
import sys
import time
from pathlib import Path

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# Shared HTTP helpers from _http:
#  - atomic_writer: prevents corrupt JSON DB on mid-dump interrupt.
#  - fetch_to_file_resumable: streams the ~4 GB OSV `all.zip` to disk with
#    Range/resume so a dropped connection at 95% doesn't restart from byte 0.
sys.path.insert(0, str(Path(__file__).parent))
try:
    from _http import (  # type: ignore[import-not-found]
        atomic_writer as _atomic_writer,
        fetch_to_file_resumable as _fetch_to_file_resumable,
    )
except ImportError:
    _atomic_writer = None  # type: ignore[assignment]
    _fetch_to_file_resumable = None  # type: ignore[assignment]


def _get_data_dir() -> Path:
    """Get skill-scoped data directory: .claude/data/conda-forge-expert/"""
    return Path(__file__).parent.parent.parent.parent / "data" / "conda-forge-expert"


# The base directory for storing CVE data
DATABASE_DIR = _get_data_dir() / "cve"

# Air-gapped enterprise users can point OSV_VULNS_BUCKET_URL at a mirror
# of the osv-vulnerabilities GCS bucket (or a JFrog generic-HTTP remote
# proxying it). Trailing slash is stripped. The per-ecosystem `all.zip`
# path is appended to whatever base resolves.
_OSV_VULNS_BUCKET_DEFAULT = "https://osv-vulnerabilities.storage.googleapis.com"


def _osv_vulns_bucket_base() -> str:
    """Resolve the OSV bulk-vulnerabilities bucket: OSV_VULNS_BUCKET_URL env → public default."""
    return (os.environ.get("OSV_VULNS_BUCKET_URL") or _OSV_VULNS_BUCKET_DEFAULT).rstrip("/")


def _osv_ecosystem_zip_url(ecosystem: str) -> str:
    """Return `<bucket-base>/<ecosystem>/all.zip` for a given ecosystem."""
    return f"{_osv_vulns_bucket_base()}/{ecosystem}/all.zip"


# Ecosystem list (URL is computed at fetch time so env changes take effect).
ECOSYSTEMS_TO_FETCH = ("PyPI",)
# Future: ("PyPI", "npm", ...)

def fetch_and_unzip(url: str) -> list[tuple[str, dict]]:
    """Stream-download an OSV `all.zip` and yield its JSON contents.

    The zip is ~4 GB for PyPI. Previously this was loaded entirely into
    memory via `requests.get(...).content` then `zipfile.ZipFile(io.BytesIO(...))`
    — a dropped connection at 95% restarted from byte 0 and OOMed under
    memory-constrained containers. Now: stream-download to a `.part` sibling
    via `_http.fetch_to_file_resumable` (Range/resume + atomic rename),
    then decompress from the cached file.

    The downloaded zip is kept on disk under
    `<DATABASE_DIR>/_downloads/<basename>` so a later re-run within the
    TTL window finds it instantly. Re-download fires only when the
    indexed DB JSON ages past CVE_TTL_DAYS in `update_database()`.
    """
    download_dir = DATABASE_DIR / "_downloads"
    target_path = download_dir / Path(url).name  # e.g. "all.zip"

    print(f"  Downloading from {url}...")
    if _fetch_to_file_resumable is not None:
        try:
            target_path = _fetch_to_file_resumable(
                target_path, url,
                chunk_size=4 * 1024 * 1024,   # 4 MB chunks for a 4 GB artifact
                timeout=600,
                user_agent="conda-forge-expert/cve-manager",
            )
        except Exception as e:
            print(f"Error: Failed to download CVE database: {e}", file=sys.stderr)
            return []
    else:
        # Fallback for environments where _http.py isn't importable.
        if not REQUESTS_AVAILABLE:
            raise ImportError("Neither _http nor requests is available for download.")
        try:
            response = requests.get(url, timeout=300, stream=True)
            response.raise_for_status()
            download_dir.mkdir(parents=True, exist_ok=True)
            with open(target_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=4 * 1024 * 1024):
                    if chunk:
                        f.write(chunk)
        except requests.RequestException as e:
            print(f"Error: Failed to download CVE database: {e}", file=sys.stderr)
            return []

    try:
        with zipfile.ZipFile(target_path) as z:
            file_list = z.namelist()
            print(f"  Unzipping {len(file_list)} files (streamed from {target_path.stat().st_size:,} bytes on disk)...")
            for filename in file_list:
                if filename.endswith(".json"):
                    try:
                        with z.open(filename) as f:
                            yield filename, json.load(f)
                    except (json.JSONDecodeError, KeyError):
                        continue  # Skip malformed JSON files
    except zipfile.BadZipFile as e:
        # The .part-then-rename pattern means we should only see a valid
        # zip here. If we do see corruption, delete the cached file so
        # the next run does a clean re-download.
        print(f"Error: cached zip at {target_path} is corrupt ({e}); removing for next run", file=sys.stderr)
        target_path.unlink(missing_ok=True)
        return []

def process_vulnerabilities(ecosystem: str, vulnerabilities: list[tuple[str, dict]]) -> dict:
    """
    Processes raw vulnerability data into an indexed format.
    The final format maps: package_name -> list of vulnerability entries.
    """
    db = {}
    print(f"  Processing {len(vulnerabilities)} vulnerabilities for {ecosystem}...")
    
    for filename, cve_data in vulnerabilities:
        if cve_data.get("withdrawn"):
            continue

        affected_packages = cve_data.get("affected", [])
        for affected in affected_packages:
            pkg_info = affected.get("package", {})
            package_name = pkg_info.get("name")
            
            if not package_name:
                continue

            # Normalize package name for consistent lookups
            normalized_name = package_name.lower().replace("_", "-")

            if normalized_name not in db:
                db[normalized_name] = []

            # Extract key information for the summary
            summary = {
                "id": cve_data.get("id"),
                "summary": cve_data.get("summary", "No summary available."),
                "details": cve_data.get("details", ""),
                "published": cve_data.get("published"),
                "modified": cve_data.get("modified"),
                "affected_versions": [v for r in affected.get("ranges", []) for v in r.get("events", [])],
                "aliases": cve_data.get("aliases", []),
            }
            db[normalized_name].append(summary)
            
    return db

def update_database(force: bool = False):
    """
    Main function to update the local CVE database for all configured ecosystems.
    """
    print("Starting CVE database update...")
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)

    for ecosystem in ECOSYSTEMS_TO_FETCH:
        # URL resolved at fetch time so OSV_VULNS_BUCKET_URL changes take effect
        # without re-importing the module.
        url = _osv_ecosystem_zip_url(ecosystem)
        db_path = DATABASE_DIR / f"{ecosystem.lower()}_cve_db.json"

        CVE_TTL_DAYS = 7
        if db_path.exists() and not force:
            age_days = (time.time() - db_path.stat().st_mtime) / 86400
            if age_days < CVE_TTL_DAYS:
                print(f"Database for {ecosystem} is {age_days:.1f} days old (TTL={CVE_TTL_DAYS}d). Use --force to refresh.")
                continue
            print(f"Database for {ecosystem} is {age_days:.1f} days old — refreshing.")

        print(f"Updating database for {ecosystem}...")

        vulnerabilities = list(fetch_and_unzip(url))
        if not vulnerabilities:
            print(f"Could not fetch data for {ecosystem}. Skipping.", file=sys.stderr)
            continue
            
        indexed_db = process_vulnerabilities(ecosystem, vulnerabilities)
        
        print(f"  Saving indexed database to {db_path}...")
        # Atomic write: a SIGINT or OOM mid-dump previously left a truncated
        # JSON file that broke vulnerability scans until manually cleaned up.
        # atomic_writer writes to a .tmp sibling, fsyncs, then renames into
        # place — interrupt leaves the prior DB intact.
        if _atomic_writer is not None:
            with _atomic_writer(db_path, "w") as f:
                json.dump(indexed_db, f)
        else:
            with open(db_path, "w") as f:
                json.dump(indexed_db, f)
            
        print(f"Successfully updated {ecosystem} database with {len(indexed_db)} packages.")

    print("CVE database update complete.")

def main():
    parser = argparse.ArgumentParser(description="Build and maintain a local CVE database from osv.dev.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force update the database even if it already exists."
    )
    args = parser.parse_args()

    if not REQUESTS_AVAILABLE:
        print("Error: The 'requests' library is required for this script.", file=sys.stderr)
        print("Please install it via your package manager (e.g., 'pixi add requests').", file=sys.stderr)
        sys.exit(1)

    try:
        update_database(force=args.force)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
