#!/usr/bin/env python3
"""
Check if recipe dependencies exist on conda-forge or a configured enterprise mirror (Artifactory).

Usage:
    python dependency-checker.py recipes/my-package
    python dependency-checker.py recipes/my-package --verbose
    python dependency-checker.py recipes/my-package --suggest
    python dependency-checker.py recipes/my-package --channel https://artifactory.corp/api/conda/conda-forge-virtual
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


# Common PyPI to conda-forge name mappings
PYPI_CONDA_MAPPINGS = {
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

# Global cache for repodata to avoid re-downloading
REPODATA_CACHE = {}


@dataclass
class DependencyCheck:
    """Result of checking a dependency."""
    name: str
    found: bool
    channel: Optional[str] = None
    versions: list[str] = None
    suggestion: Optional[str] = None


def normalize_package_name(name: str) -> str:
    """Normalize package name for comparison."""
    return name.lower().replace("_", "-")


def get_skill_config() -> dict:
    """Load configuration from skill-config.yaml or enterprise-config.yaml."""
    if not YAML_AVAILABLE:
        return {}
    
    config_dir = Path(__file__).parent.parent / "config"
    
    # Check enterprise config first
    enterprise_config = config_dir / "enterprise-config.yaml"
    if enterprise_config.exists():
        try:
            with open(enterprise_config) as f:
                return yaml.safe_load(f)
        except Exception:
            pass

    # Fallback to standard config
    skill_config = config_dir / "skill-config.yaml"
    if skill_config.exists():
        try:
            with open(skill_config) as f:
                return yaml.safe_load(f)
        except Exception:
            pass
            
    return {}


def get_configured_channels(override_channel: Optional[str] = None) -> List[str]:
    """Get the base channel URLs to check, accounting for Enterprise/Artifactory setups."""
    if override_channel:
        return [override_channel]

    # Check environment variable first
    env_channel = os.environ.get("CONDA_CHANNEL_URL")
    if env_channel:
        return [env_channel]

    config = get_skill_config()
    
    # Check for enterprise config
    features = config.get("features", {})
    if features.get("enable_enterprise") or features.get("enable_airgapped"):
        
        # Check enterprise-config.yaml style
        artifactory = config.get("artifactory", {})
        channels = artifactory.get("channels", {})
        if channels.get("primary"):
            return [channels.get("primary")]
            
        # Check skill-config.yaml style
        ent_settings = config.get("enterprise", {}).get("artifactory", {})
        url = ent_settings.get("url")
        virtual_repo = ent_settings.get("conda_virtual_repo")
        
        if url and virtual_repo:
            base_url = url.rstrip("/")
            if "api/conda" not in base_url:
                 # Artifactory usually serves conda packages under api/conda or directly
                 return [f"{base_url}/api/conda/{virtual_repo}", f"{base_url}/{virtual_repo}"]
            return [f"{base_url}/{virtual_repo}"]

        # Check environment channels override
        env_channels = config.get("environment", {}).get("channels", [])
        if env_channels:
             return env_channels
             
    # Default to standard conda-forge
    return ["https://conda.anaconda.org/conda-forge"]


def get_repodata(channel_url: str) -> dict:
    """Fetch and cache repodata.json, parsing it into a lookup dictionary."""
    if channel_url in REPODATA_CACHE:
        return REPODATA_CACHE[channel_url]

    try:
        # Pass authentication if available (useful for Artifactory)
        headers = {}
        token = os.environ.get("ARTIFACTORY_TOKEN") or os.environ.get("CONDA_TOKEN")
        if token and ("artifactory" in channel_url or "internal" in channel_url):
            headers["Authorization"] = f"Bearer {token}"

        # In air-gapped/enterprise environments, SSL verify might fail due to custom CAs
        ssl_verify = os.environ.get("REQUESTS_CA_BUNDLE", True)
        if os.environ.get("CONDA_SSL_VERIFY", "").lower() in ("false", "0", "no"):
             ssl_verify = False

        response = requests.get(channel_url, headers=headers, timeout=30, verify=ssl_verify)
        response.raise_for_status()
        data = response.json()
        
        packages = {}
        
        # Parse standard packages
        for pkg_file, info in data.get("packages", {}).items():
            name = normalize_package_name(info.get("name", ""))
            if name:
                if name not in packages:
                    packages[name] = set()
                packages[name].add(info.get("version", ""))
                
        # Parse .conda packages
        for pkg_file, info in data.get("packages.conda", {}).items():
            name = normalize_package_name(info.get("name", ""))
            if name:
                if name not in packages:
                    packages[name] = set()
                packages[name].add(info.get("version", ""))
                
        REPODATA_CACHE[channel_url] = packages
        return packages
    except Exception as e:
        # If we fail to fetch, cache an empty dict so we don't retry endlessly
        REPODATA_CACHE[channel_url] = {}
        return {}


def check_conda_forge(package_name: str, channels: List[str]) -> DependencyCheck:
    """Check if package exists on configured channels (Anaconda API or Artifactory Repodata)."""
    if not REQUESTS_AVAILABLE:
        return DependencyCheck(name=package_name, found=False,
                               suggestion="Install requests to check online")

    normalized = normalize_package_name(package_name)
    
    # 1. Try Anaconda API first ONLY IF we are using standard conda-forge
    is_standard_forge = any("conda.anaconda.org/conda-forge" in c for c in channels)
    if is_standard_forge:
        url = f"https://api.anaconda.org/package/conda-forge/{normalized}"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return DependencyCheck(
                    name=package_name,
                    found=True,
                    channel="conda-forge",
                    versions=data.get("versions", [])
                )
        except Exception:
            pass # API blocked, timed out, or connection refused

    # 2. Fallback/Primary to repodata.json (Handles Artifactory and Air-gapped scenarios)
    for base_channel in channels:
        base_channel = base_channel.rstrip("/")
        
        # Standard subdirs
        for subdir in ["noarch", "linux-64"]:
            repodata_url = f"{base_channel}/{subdir}/repodata.json"
            
            # Use file protocol logic if it's a local mirror
            if repodata_url.startswith("file://"):
                try:
                    local_path = repodata_url.replace("file://", "")
                    with open(local_path) as f:
                        data = json.load(f)
                        packages = {}
                        for k, v in data.get("packages", {}).items():
                             name = normalize_package_name(v.get("name", ""))
                             if name: packages[name] = True
                        for k, v in data.get("packages.conda", {}).items():
                             name = normalize_package_name(v.get("name", ""))
                             if name: packages[name] = True
                        REPODATA_CACHE[repodata_url] = packages
                except Exception:
                    continue
            
            packages = get_repodata(repodata_url)
            
            if normalized in packages:
                return DependencyCheck(
                    name=package_name,
                    found=True,
                    channel=base_channel,
                    versions=list(packages[normalized]) if isinstance(packages[normalized], set) else []
                )

    # 3. Check if there's a known mapping
    mapped_name = PYPI_CONDA_MAPPINGS.get(normalized)
    if mapped_name and mapped_name != normalized:
        return DependencyCheck(
            name=package_name,
            found=False,
            suggestion=f"Try '{mapped_name}' instead of '{package_name}'"
        )

    return DependencyCheck(name=package_name, found=False)


def extract_package_name(dep_string: str) -> str:
    """Extract package name from a dependency string (e.g., 'numpy >=1.20')."""
    dep_string = dep_string.strip()
    match = re.match(r'^([a-zA-Z0-9_\-\.]+)', dep_string)
    if match:
        return match.group(1)
    return ""


def extract_dependencies_v1(recipe_path: Path) -> list[str]:
    """Extract dependencies from recipe.yaml."""
    if not YAML_AVAILABLE:
        print("Warning: PyYAML not available, using basic parsing")
        return extract_dependencies_basic(recipe_path)

    content = recipe_path.read_text()
    content = re.sub(r'\$\{\{[^}]+\}\}', 'PLACEHOLDER', content)

    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError:
        return extract_dependencies_basic(recipe_path)

    deps = set()
    requirements = data.get("requirements", {})

    for section in ["build", "host", "run"]:
        section_deps = requirements.get(section, [])
        if isinstance(section_deps, list):
            for dep in section_deps:
                if isinstance(dep, str):
                    name = extract_package_name(dep)
                    if name and name != "PLACEHOLDER" and not name.startswith("$"):
                        deps.add(name)
                elif isinstance(dep, dict):
                    for key in ["then", "else"]:
                        val = dep.get(key)
                        if isinstance(val, str):
                            name = extract_package_name(val)
                            if name and name != "PLACEHOLDER":
                                deps.add(name)
                        elif isinstance(val, list):
                            for v in val:
                                if isinstance(v, str):
                                    name = extract_package_name(v)
                                    if name and name != "PLACEHOLDER":
                                        deps.add(name)

    return sorted(deps)


def extract_dependencies_legacy(recipe_path: Path) -> list[str]:
    """Extract dependencies from meta.yaml."""
    content = recipe_path.read_text()
    deps = set()
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
                dep_line = stripped[2:].split("#")[0].strip()
                dep_line = re.sub(r'\{\{[^}]+\}\}', '', dep_line).strip()
                if dep_line:
                    name = extract_package_name(dep_line)
                    if name:
                        deps.add(name)

    return sorted(deps)


def extract_dependencies_basic(recipe_path: Path) -> list[str]:
    """Basic dependency extraction without YAML parser."""
    content = recipe_path.read_text()
    deps = set()

    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("- "):
            dep_line = stripped[2:].split("#")[0].strip()
            dep_line = re.sub(r'[\$\{].*?[\}]', '', dep_line).strip()
            dep_line = re.sub(r'\{\{.*?\}\}', '', dep_line).strip()
            if dep_line:
                name = extract_package_name(dep_line)
                if name and len(name) > 1 and not name.startswith(("if", "then", "else")):
                    deps.add(name)

    return sorted(deps)


def check_recipe(recipe_path: Path, verbose: bool = False, suggest: bool = False, channel: str = None) -> tuple[list, list]:
    """Check all dependencies in a recipe."""
    if recipe_path.is_dir():
        if (recipe_path / "recipe.yaml").exists():
            recipe_file = recipe_path / "recipe.yaml"
            is_v1 = True
        elif (recipe_path / "meta.yaml").exists():
            recipe_file = recipe_path / "meta.yaml"
            is_v1 = False
        else:
            raise FileNotFoundError(f"No recipe file in {recipe_path}")
    else:
        recipe_file = recipe_path
        is_v1 = recipe_file.name == "recipe.yaml"

    if is_v1:
        deps = extract_dependencies_v1(recipe_file)
    else:
        deps = extract_dependencies_legacy(recipe_file)

    skip_packages = {
        "python", "pip", "setuptools", "wheel",
        "compiler", "stdlib",  
    }
    deps = [d for d in deps if d.lower() not in skip_packages]

    channels = get_configured_channels(channel)
    
    if verbose:
        print(f"Found {len(deps)} dependencies to check")
        print(f"Using channels: {', '.join(channels)}")

    found = []
    missing = []

    for dep in deps:
        if verbose:
            print(f"Checking {dep}...", end=" ", flush=True)

        result = check_conda_forge(dep, channels)

        if result.found:
            found.append(result)
            if verbose:
                print(f"OK ({result.channel})")
        else:
            missing.append(result)
            if verbose:
                print("NOT FOUND")
                if suggest and result.suggestion:
                    print(f"  Suggestion: {result.suggestion}")

    return found, missing


def main():
    parser = argparse.ArgumentParser(
        description="Check if recipe dependencies exist on conda-forge or enterprise mirror"
    )
    parser.add_argument("recipe", type=Path,
                        help="Recipe path (directory or file)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Verbose output")
    parser.add_argument("--suggest", "-s", action="store_true",
                        help="Suggest fixes for missing dependencies")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")
    parser.add_argument("--channel", "-c", type=str,
                        help="Override channel URL (e.g., Artifactory URL)")

    args = parser.parse_args()

    try:
        found, missing = check_recipe(args.recipe, args.verbose, args.suggest, args.channel)

        if args.json:
            print(json.dumps({
                "found": [{"name": r.name, "channel": r.channel} for r in found],
                "missing": [{"name": r.name, "suggestion": r.suggestion} for r in missing]
            }, indent=2))
        else:
            print(f"\n{'='*50}")
            print(f"Dependencies found: {len(found)}")
            print(f"Dependencies missing: {len(missing)}")

            if missing:
                print(f"\nMissing packages:")
                for dep in missing:
                    msg = f"  - {dep.name}"
                    if dep.suggestion:
                        msg += f" ({dep.suggestion})"
                    print(msg)

            if missing:
                print(f"\n[FAIL] {len(missing)} dependencies not found in channels")
                sys.exit(1)
            else:
                print(f"\n[OK] All dependencies found")

    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()