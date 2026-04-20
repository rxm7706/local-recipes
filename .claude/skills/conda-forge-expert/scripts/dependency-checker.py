#!/usr/bin/env python3
"""
Check if recipe dependencies exist on conda-forge or a configured enterprise mirror.

Architecture: batch-first via repodata.json
  Phase 1 — Extract all dependency names from the recipe (no I/O).
  Phase 2 — Fetch repodata once per (channel, subdir): tries current_repodata.json.bz2,
             current_repodata.json, repodata.json.bz2, repodata.json (first hit wins).
             Results held in memory for the process lifetime; optionally also persisted to
             disk (set CONDA_DEP_CACHE_DIR to enable, default TTL 3600 s).
  Phase 3 — Look up every dep in the merged in-memory index: O(1) per dep, zero extra I/O.

Air-gapped / JFrog Artifactory support:
  • --channel https://artifactory.corp/artifactory/api/conda/conda-forge-virtual
  • --channel file:///srv/conda-mirror/conda-forge  (fully offline local mirror)
  • JFROG_API_KEY or JFROG_TOKEN env vars for authentication
  • REQUESTS_CA_BUNDLE or CONDA_SSL_VERIFY=false for custom CAs / self-signed certs
  • CONDA_DEP_CACHE_DIR to pre-load an offline snapshot: copy repodata cache from a
    network-connected machine and set CONDA_DEP_CACHE_DIR on the air-gapped machine.

Auth env vars (checked in order, first match wins):
  JFROG_API_KEY / ARTIFACTORY_API_KEY  → X-JFrog-Art-Api header
  JFROG_TOKEN / ARTIFACTORY_TOKEN / CONDA_TOKEN  → Authorization: Bearer
  JFROG_USER + JFROG_PASSWORD  → Authorization: Basic

Usage:
    python dependency-checker.py recipes/my-package
    python dependency-checker.py recipes/my-package --suggest
    python dependency-checker.py recipes/my-package \\
        --channel https://artifactory.corp/artifactory/api/conda/conda-forge
    python dependency-checker.py recipes/my-package \\
        --channel file:///srv/conda-mirror/conda-forge
    python dependency-checker.py recipes/my-package --subdir linux-64 --subdir noarch
"""

from __future__ import annotations

import argparse
import base64
import bz2
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    yaml = None  # type: ignore[assignment]
    YAML_AVAILABLE = False

try:
    import zstandard  # type: ignore[import]
    ZSTD_AVAILABLE = True
except ImportError:
    zstandard = None  # type: ignore[assignment]
    ZSTD_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    requests = None  # type: ignore[assignment]
    REQUESTS_AVAILABLE = False

# ── Constants ─────────────────────────────────────────────────────────────────

# Subdirs to fetch when none are specified.  noarch covers pure-Python packages;
# linux-64 covers the majority of compiled packages on conda-forge.
DEFAULT_SUBDIRS: List[str] = ["noarch", "linux-64"]

# Candidate repodata filenames tried in preference order (smallest first).
# current_repodata.json only carries the latest build of each package, which is
# sufficient for an existence check and is 3-5× smaller than full repodata.json.
_REPODATA_CANDIDATES = [
    "current_repodata.json.bz2",
    "current_repodata.json",
    "repodata.json.bz2",
    "repodata.json",
]

# PyPI → conda-forge name overrides for common mismatches.
PYPI_CONDA_MAPPINGS: Dict[str, str] = {
    "pillow": "pillow",
    "pyyaml": "pyyaml",
    "scikit-learn": "scikit-learn",
    "scikit-image": "scikit-image",
    "opencv-python": "opencv",
    "opencv-python-headless": "opencv",
    "beautifulsoup4": "beautifulsoup4",
    "msgpack-python": "msgpack-python",
    "attrs": "attrs",
    "dateutil": "python-dateutil",
    "python-dateutil": "python-dateutil",
}

# Dependencies that are always available / managed by conda outside the recipe.
_SKIP_PACKAGES: Set[str] = {
    "python", "pip", "setuptools", "wheel", "compiler", "stdlib",
}

# ── Data classes ───────────────────────────────────────────────────────────────

@dataclass
class DependencyCheck:
    name: str
    found: bool
    channel: Optional[str] = None
    versions: List[str] = field(default_factory=list)
    suggestion: Optional[str] = None


# {normalized_name: (channel_label, versions_list)}
PackageIndex = Dict[str, Tuple[str, List[str]]]

# ── Config helpers ─────────────────────────────────────────────────────────────

def normalize_package_name(name: str) -> str:
    return name.lower().replace("_", "-")


def get_skill_config() -> dict:
    """Load from enterprise-config.yaml, then skill-config.yaml."""
    if not YAML_AVAILABLE:
        return {}
    assert yaml is not None
    config_dir = Path(__file__).parent.parent / "config"
    for fname in ("enterprise-config.yaml", "skill-config.yaml"):
        p = config_dir / fname
        if p.exists():
            try:
                with open(p) as fh:
                    return yaml.safe_load(fh) or {}
            except Exception:
                pass
    return {}


def get_configured_channels(override: Optional[str] = None) -> List[str]:
    """Return list of channel base URLs, highest priority first."""
    if override:
        return [override]
    env = os.environ.get("CONDA_CHANNEL_URL")
    if env:
        return [env]

    cfg = get_skill_config()
    features = cfg.get("features", {})
    if features.get("enable_enterprise") or features.get("enable_airgapped"):
        # enterprise-config.yaml layout
        primary = cfg.get("artifactory", {}).get("channels", {}).get("primary")
        if primary:
            return [primary]
        # skill-config.yaml layout
        ent = cfg.get("enterprise", {}).get("artifactory", {})
        url, repo = ent.get("url"), ent.get("conda_virtual_repo")
        if url and repo:
            return [f"{url.rstrip('/')}/api/conda/{repo}"]
        env_channels = cfg.get("environment", {}).get("channels", [])
        if env_channels:
            return env_channels

    return ["https://conda.anaconda.org/conda-forge"]

# ── Auth + SSL ─────────────────────────────────────────────────────────────────

def _auth_headers(url: str) -> Dict[str, str]:
    """Build authorization headers for the URL from environment variables."""
    _ = url  # reserved for future per-domain auth routing

    # JFrog native API key (preferred over Bearer on Artifactory)
    api_key = os.environ.get("JFROG_API_KEY") or os.environ.get("ARTIFACTORY_API_KEY")
    if api_key:
        return {"X-JFrog-Art-Api": api_key}

    # Bearer token (Artifactory access token, conda token)
    token = (
        os.environ.get("JFROG_TOKEN")
        or os.environ.get("ARTIFACTORY_TOKEN")
        or os.environ.get("CONDA_TOKEN")
    )
    if token:
        return {"Authorization": f"Bearer {token}"}

    # Basic auth (username + password for on-prem Artifactory)
    user = os.environ.get("JFROG_USER") or os.environ.get("ARTIFACTORY_USER")
    password = os.environ.get("JFROG_PASSWORD") or os.environ.get("ARTIFACTORY_PASSWORD")
    if user and password:
        creds = base64.b64encode(f"{user}:{password}".encode()).decode()
        return {"Authorization": f"Basic {creds}"}

    return {}


def _ssl_verify() -> bool | str:
    """Determine SSL verification from environment.  Returns True, False, or a CA path."""
    if os.environ.get("CONDA_SSL_VERIFY", "").lower() in ("false", "0", "no"):
        return False
    ca = os.environ.get("REQUESTS_CA_BUNDLE") or os.environ.get("SSL_CERT_FILE")
    return ca if ca else True

# ── Disk cache ─────────────────────────────────────────────────────────────────

def _cache_dir() -> Optional[Path]:
    d = os.environ.get("CONDA_DEP_CACHE_DIR")
    return Path(d) if d else None


def _cache_ttl() -> int:
    try:
        return int(os.environ.get("CONDA_DEP_CACHE_TTL", "3600"))
    except ValueError:
        return 3600


def _disk_get(cache_dir: Path, url: str) -> Optional[Dict[str, List[str]]]:
    """Return cached index for url, or None if absent / expired."""
    key = hashlib.md5(url.encode()).hexdigest()
    data_p = cache_dir / f"{key}.json"
    meta_p = cache_dir / f"{key}.meta"
    if not data_p.exists():
        return None
    ttl = _cache_ttl()
    if ttl > 0 and meta_p.exists():
        try:
            meta = json.loads(meta_p.read_text())
            if time.time() - meta.get("fetched_at", 0) > ttl:
                return None
        except Exception:
            return None
    try:
        return json.loads(data_p.read_text())  # type: ignore[return-value]
    except Exception:
        return None


def _disk_set(cache_dir: Path, url: str, data: Dict[str, List[str]]) -> None:
    """Persist index to disk cache. Best-effort — never raises."""
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        key = hashlib.md5(url.encode()).hexdigest()
        (cache_dir / f"{key}.json").write_text(json.dumps(data))
        (cache_dir / f"{key}.meta").write_text(
            json.dumps({"url": url, "fetched_at": time.time()})
        )
    except Exception:
        pass

# ── Fetch + decompress ─────────────────────────────────────────────────────────

def _fetch_timeout() -> int:
    try:
        return int(os.environ.get("CONDA_DEP_FETCH_TIMEOUT", "120"))
    except ValueError:
        return 120


def _fetch_bytes(url: str, headers: Dict[str, str], verify: bool | str) -> bytes:
    """Return raw bytes for url.  Handles file://, https://, and http://."""
    if url.startswith("file://"):
        # Strip "file://" — works on both Unix (/absolute) and Windows (//host/share)
        return Path(url[7:]).read_bytes()

    timeout = _fetch_timeout()
    if REQUESTS_AVAILABLE:
        assert requests is not None
        resp = requests.get(url, headers=headers, verify=verify, timeout=timeout, stream=True)
        resp.raise_for_status()
        return resp.content

    # urllib fallback (no extra dependency)
    from urllib.request import Request as _Req, urlopen as _open
    from urllib.error import HTTPError as _HTTPError
    req = _Req(url, headers=headers)
    try:
        ctx = None
        if verify is False:
            import ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        with _open(req, timeout=timeout, context=ctx) as r:
            return r.read()
    except _HTTPError as exc:
        raise exc


def _decompress(data: bytes, url: str) -> bytes:
    """Decompress bz2 or zst data based on the URL suffix."""
    if url.endswith(".bz2"):
        return bz2.decompress(data)
    if url.endswith(".zst"):
        if ZSTD_AVAILABLE:
            assert zstandard is not None
            return zstandard.ZstdDecompressor().decompress(data)
        raise RuntimeError("Install zstandard to decompress .zst repodata")
    return data

# ── Repodata index ─────────────────────────────────────────────────────────────

# Per-process memory cache: url → {normalized_name: sorted_versions}
_MEMORY_CACHE: Dict[str, Dict[str, List[str]]] = {}


def _fetch_repodata(
    channel_url: str,
    subdir: str,
    headers: Dict[str, str],
    verify: bool | str,
) -> Dict[str, List[str]]:
    """
    Fetch and parse the package index for one (channel, subdir) pair.

    Tries candidate filenames in preference order; first successful response wins.
    Results are cached in _MEMORY_CACHE and, when CONDA_DEP_CACHE_DIR is set, on disk.
    Returns {normalized_package_name: sorted_version_list}.
    """
    disk = _cache_dir()
    base = channel_url.rstrip("/")

    for filename in _REPODATA_CANDIDATES:
        url = f"{base}/{subdir}/{filename}"

        # Memory cache hit
        if url in _MEMORY_CACHE:
            return _MEMORY_CACHE[url]

        # Disk cache hit
        if disk:
            cached = _disk_get(disk, url)
            if cached is not None:
                _MEMORY_CACHE[url] = cached
                return cached

        try:
            raw = _fetch_bytes(url, headers, verify)
            data = json.loads(_decompress(raw, url))
        except Exception:
            continue  # 404, auth failure, or decompression error → try next variant

        # Parse both .tar.bz2 and .conda package entries
        acc: Dict[str, Set[str]] = {}
        for section in ("packages", "packages.conda"):
            for _, info in data.get(section, {}).items():
                name = normalize_package_name(info.get("name", ""))
                version = info.get("version", "")
                if name:
                    acc.setdefault(name, set()).add(version)

        result: Dict[str, List[str]] = {k: sorted(v) for k, v in acc.items()}
        _MEMORY_CACHE[url] = result
        if disk:
            _disk_set(disk, url, result)
        return result

    # All candidates failed — cache an empty result to prevent repeated retries.
    sentinel = f"{base}/{subdir}/repodata.json"
    _MEMORY_CACHE[sentinel] = {}
    return {}


def build_package_index(channels: List[str], subdirs: List[str]) -> PackageIndex:
    """
    Pre-fetch repodata for all (channel, subdir) pairs and merge into a single index.
    First channel that has a package wins (channels list is priority-ordered).
    """
    index: PackageIndex = {}
    verify = _ssl_verify()

    for channel_url in channels:
        headers = _auth_headers(channel_url)
        label = _channel_label(channel_url)
        for subdir in subdirs:
            packages = _fetch_repodata(channel_url, subdir, headers, verify)
            for name, versions in packages.items():
                if name not in index:
                    index[name] = (label, versions)

    return index


def _channel_label(url: str) -> str:
    """Short human-readable label for a channel URL."""
    if "conda.anaconda.org/conda-forge" in url:
        return "conda-forge"
    if url.startswith("file://"):
        return f"local:{url[7:]}"
    # For Artifactory URLs use the last non-empty path segment (virtual repo name)
    parts = [p for p in url.rstrip("/").split("/") if p]
    return parts[-1] if parts else url

# ── Batch dependency check ─────────────────────────────────────────────────────

def batch_check_deps(
    deps: List[str],
    index: PackageIndex,
    suggest: bool,
) -> Tuple[List[DependencyCheck], List[DependencyCheck]]:
    """Look up all deps in the pre-built index.  Zero network calls."""
    found: List[DependencyCheck] = []
    missing: List[DependencyCheck] = []

    for dep in deps:
        normalized = normalize_package_name(dep)
        if normalized in index:
            label, versions = index[normalized]
            found.append(DependencyCheck(
                name=dep,
                found=True,
                channel=label,
                versions=versions[:5],  # cap to keep output compact
            ))
        else:
            suggestion: Optional[str] = None
            if suggest:
                mapped = PYPI_CONDA_MAPPINGS.get(normalized)
                if mapped and mapped != normalized:
                    in_channel = normalize_package_name(mapped) in index
                    suggestion = (
                        f"Try '{mapped}' instead of '{dep}'"
                        + (" (confirmed in channel)" if in_channel else "")
                    )
            missing.append(DependencyCheck(name=dep, found=False, suggestion=suggestion))

    return found, missing

# ── Recipe dep extraction ──────────────────────────────────────────────────────

def extract_package_name(dep_string: str) -> str:
    dep_string = dep_string.strip()
    m = re.match(r'^([a-zA-Z0-9_\-\.]+)', dep_string)
    return m.group(1) if m else ""


def extract_dependencies_v1(recipe_path: Path) -> List[str]:
    """Extract dep names from recipe.yaml (v1 format)."""
    if not YAML_AVAILABLE:
        return extract_dependencies_basic(recipe_path)
    assert yaml is not None

    content = re.sub(r'\$\{\{[^}]+\}\}', 'PLACEHOLDER', recipe_path.read_text())
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError:
        return extract_dependencies_basic(recipe_path)

    deps: Set[str] = set()
    for section in ("build", "host", "run"):
        for dep in (data.get("requirements", {}) or {}).get(section, []) or []:
            if isinstance(dep, str):
                name = extract_package_name(dep)
                if name and name != "PLACEHOLDER" and not name.startswith("$"):
                    deps.add(name)
            elif isinstance(dep, dict):
                for key in ("then", "else"):
                    val = dep.get(key)
                    items: List[str] = (
                        [val] if isinstance(val, str)
                        else (val if isinstance(val, list) else [])
                    )
                    for item in items:
                        name = extract_package_name(str(item))
                        if name and name != "PLACEHOLDER":
                            deps.add(name)
    return sorted(deps)


def extract_dependencies_legacy(recipe_path: Path) -> List[str]:
    """Extract dep names from meta.yaml (legacy Jinja2 format)."""
    content = recipe_path.read_text()
    deps: Set[str] = set()
    in_requirements = False

    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("requirements:"):
            in_requirements = True
            continue
        if in_requirements:
            if stripped and not stripped.startswith("#") and not stripped.startswith("-"):
                if not line.startswith(" "):
                    break
            if stripped.startswith("- "):
                dep_line = re.sub(r'\{\{[^}]+\}\}', '', stripped[2:].split("#")[0]).strip()
                if dep_line:
                    name = extract_package_name(dep_line)
                    if name:
                        deps.add(name)

    return sorted(deps)


def extract_dependencies_basic(recipe_path: Path) -> List[str]:
    """Best-effort extraction without a YAML parser."""
    content = recipe_path.read_text()
    deps: Set[str] = set()

    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("- "):
            dep_line = re.sub(r'[\$\{].*?[\}]', '', stripped[2:].split("#")[0]).strip()
            dep_line = re.sub(r'\{\{.*?\}\}', '', dep_line).strip()
            if dep_line:
                name = extract_package_name(dep_line)
                if name and len(name) > 1 and name not in ("if", "then", "else"):
                    deps.add(name)

    return sorted(deps)

# ── Top-level entry point ──────────────────────────────────────────────────────

def check_recipe(
    recipe_path: Path,
    verbose: bool = False,
    suggest: bool = False,
    channel: Optional[str] = None,
    subdirs: Optional[List[str]] = None,
) -> Tuple[List[DependencyCheck], List[DependencyCheck]]:
    """
    Full pipeline: extract deps → build repodata index → batch lookup.
    Returns (found, missing).
    """
    # 1. Resolve recipe file
    if recipe_path.is_dir():
        for name in ("recipe.yaml", "meta.yaml"):
            candidate = recipe_path / name
            if candidate.exists():
                recipe_file = candidate
                is_v1 = name == "recipe.yaml"
                break
        else:
            raise FileNotFoundError(f"No recipe file in {recipe_path}")
    else:
        recipe_file = recipe_path
        is_v1 = recipe_file.name == "recipe.yaml"

    # 2. Extract deps
    raw_deps = extract_dependencies_v1(recipe_file) if is_v1 else extract_dependencies_legacy(recipe_file)
    deps = [d for d in raw_deps if d.lower() not in _SKIP_PACKAGES]
    if not deps:
        return [], []

    # 3. Resolve channels + subdirs
    channels = get_configured_channels(channel)
    active_subdirs = subdirs or DEFAULT_SUBDIRS

    if verbose:
        print(f"Found {len(deps)} dependenc{'y' if len(deps) == 1 else 'ies'} to check")
        print(f"Channels: {', '.join(channels)}")
        print(f"Subdirs:  {', '.join(active_subdirs)}")
        disk = _cache_dir()
        print(f"Disk cache: {disk or 'disabled (set CONDA_DEP_CACHE_DIR to enable)'}")
        print("Building package index (fetching repodata)...", flush=True)

    # 4. Batch phase: fetch repodata once per (channel, subdir), then build index
    index = build_package_index(channels, active_subdirs)

    if verbose:
        print(f"Index built: {len(index):,} packages across {len(channels)} channel(s)")

    # 5. Lookup phase: O(1) per dep, zero network calls
    return batch_check_deps(deps, index, suggest)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check if recipe dependencies exist on conda-forge or enterprise mirror",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Auth env vars:  JFROG_API_KEY, JFROG_TOKEN, CONDA_TOKEN,\n"
            "                JFROG_USER + JFROG_PASSWORD\n"
            "SSL env vars:   REQUESTS_CA_BUNDLE, CONDA_SSL_VERIFY=false\n"
            "Cache env vars: CONDA_DEP_CACHE_DIR (path), CONDA_DEP_CACHE_TTL (seconds)\n"
            "Fetch env var:  CONDA_DEP_FETCH_TIMEOUT (seconds, default 120)"
        ),
    )
    parser.add_argument("recipe", type=Path, help="Recipe path (directory or file)")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--suggest", "-s", action="store_true",
                        help="Suggest conda-forge name for missing PyPI-named deps")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--channel", "-c", type=str,
                        help="Override channel URL (Artifactory or file:// local mirror)")
    parser.add_argument("--subdir", action="append", dest="subdirs", metavar="SUBDIR",
                        help=f"Subdir to check (repeatable; default: {', '.join(DEFAULT_SUBDIRS)})")

    args = parser.parse_args()

    try:
        found, missing = check_recipe(
            args.recipe,
            verbose=args.verbose,
            suggest=args.suggest,
            channel=args.channel,
            subdirs=args.subdirs,
        )
    except FileNotFoundError as exc:
        out = {"found": [], "missing": [], "error": str(exc)}
        print(json.dumps(out, indent=2) if args.json else f"Error: {exc}")
        sys.exit(1)

    if args.json:
        print(json.dumps({
            "found":   [{"name": r.name, "channel": r.channel} for r in found],
            "missing": [{"name": r.name, "suggestion": r.suggestion} for r in missing],
        }, indent=2))
    else:
        print(f"\n{'='*50}")
        print(f"Dependencies found:   {len(found)}")
        print(f"Dependencies missing: {len(missing)}")
        if missing:
            print("\nMissing packages:")
            for dep in missing:
                line = f"  - {dep.name}"
                if dep.suggestion:
                    line += f"  ({dep.suggestion})"
                print(line)
        print()
        if not missing:
            print("[OK] All dependencies found")
        else:
            print(f"[FAIL] {len(missing)} dependenc{'y' if len(missing) == 1 else 'ies'} not found in channels")

    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()
