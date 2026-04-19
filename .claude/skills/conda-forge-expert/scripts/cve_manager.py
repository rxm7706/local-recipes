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
import io
import sys
from pathlib import Path

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# The base directory for storing CVE data, relative to the .claude directory
DATABASE_DIR = Path(__file__).parent.parent.parent / "data" / "cve"
ECOSYSTEMS_TO_FETCH = {
    "PyPI": "https://osv-vulnerabilities.storage.googleapis.com/PyPI/all.zip",
    # "npm": "https://osv-vulnerabilities.storage.googleapis.com/npm/all.zip", # Example for future expansion
}

def fetch_and_unzip(url: str) -> list[tuple[str, dict]]:
    """Downloads a zip archive from a URL and yields its JSON contents."""
    if not REQUESTS_AVAILABLE:
        raise ImportError("The 'requests' library is required to download the CVE database.")

    print(f"  Downloading from {url}...")
    try:
        response = requests.get(url, stream=True, timeout=300) # 5-minute timeout for large files
        response.raise_for_status()
        
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            file_list = z.namelist()
            print(f"  Unzipping {len(file_list)} files in memory...")
            for filename in file_list:
                if filename.endswith('.json'):
                    try:
                        yield filename, json.loads(z.read(filename))
                    except (json.JSONDecodeError, KeyError):
                        continue # Skip malformed JSON files
    except requests.RequestException as e:
        print(f"Error: Failed to download CVE database: {e}", file=sys.stderr)
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

    for ecosystem, url in ECOSYSTEMS_TO_FETCH.items():
        db_path = DATABASE_DIR / f"{ecosystem.lower()}_cve_db.json"
        
        if db_path.exists() and not force:
            print(f"Database for {ecosystem} already exists. Use --force to update.")
            continue
            
        print(f"Updating database for {ecosystem}...")
        
        vulnerabilities = list(fetch_and_unzip(url))
        if not vulnerabilities:
            print(f"Could not fetch data for {ecosystem}. Skipping.", file=sys.stderr)
            continue
            
        indexed_db = process_vulnerabilities(ecosystem, vulnerabilities)
        
        print(f"  Saving indexed database to {db_path}...")
        with open(db_path, "w") as f:
            json.dump(indexed_db, f) # No indent for smaller file size
            
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
