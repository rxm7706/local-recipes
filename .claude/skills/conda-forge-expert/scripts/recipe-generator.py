#!/usr/bin/env python3
"""
Generate conda-forge recipes from various sources.

Supports:
- PyPI packages
- GitHub repositories
- Local source directories
- Templates

Usage:
    python recipe-generator.py pypi requests
    python recipe-generator.py github owner/repo
    python recipe-generator.py template python-noarch --name mypackage
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

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


@dataclass
class PackageInfo:
    """Package metadata."""
    name: str
    version: str
    summary: str = ""
    description: str = ""
    homepage: str = ""
    license: str = ""
    license_file: str = "LICENSE"
    source_url: str = ""
    sha256: str = ""
    dependencies: list[str] = field(default_factory=list)
    entry_points: list[str] = field(default_factory=list)
    python_requires: str = ">=3.10"
    author: str = ""


def fetch_pypi_info(package_name: str, version: Optional[str] = None) -> PackageInfo:
    """Fetch package info from PyPI."""
    if not REQUESTS_AVAILABLE:
        raise ImportError("requests library required: pip install requests")

    url = f"https://pypi.org/pypi/{package_name}/json"
    if version:
        url = f"https://pypi.org/pypi/{package_name}/{version}/json"

    response = requests.get(url, timeout=30)
    response.raise_for_status()
    data = response.json()

    info = data["info"]
    version = version or info["version"]

    # Find source distribution
    source_url = ""
    sha256 = ""
    for release in data["releases"].get(version, []):
        if release["packagetype"] == "sdist":
            source_url = release["url"]
            sha256 = release["digests"]["sha256"]
            break

    # Parse dependencies
    dependencies = []
    requires_dist = info.get("requires_dist") or []
    for req in requires_dist:
        # Skip optional/extra dependencies
        if "extra ==" in req or ";" in req:
            continue
        # Extract package name
        match = re.match(r"^([a-zA-Z0-9_-]+)", req)
        if match:
            dependencies.append(match.group(1).lower())

    # Parse python_requires
    python_requires = info.get("requires_python", ">=3.10") or ">=3.10"

    # Parse entry points from project_urls or classifiers
    entry_points = []

    return PackageInfo(
        name=info["name"],
        version=version,
        summary=info.get("summary", ""),
        description=info.get("description", "")[:500],
        homepage=info.get("home_page") or info.get("project_url") or "",
        license=info.get("license", ""),
        source_url=source_url,
        sha256=sha256,
        dependencies=dependencies,
        python_requires=python_requires,
        author=info.get("author", ""),
    )


def generate_recipe_yaml(info: PackageInfo, output_dir: Path) -> Path:
    """Generate recipe.yaml (v1 format)."""
    # Parse python_min from python_requires
    match = re.search(r">=\s*(\d+\.\d+)", info.python_requires)
    python_min = match.group(1) if match else "3.10"

    recipe = f'''# yaml-language-server: $schema=https://raw.githubusercontent.com/prefix-dev/recipe-format/main/schema.json
schema_version: 1

context:
  name: {info.name}
  version: "{info.version}"
  python_min: "{python_min}"

package:
  name: ${{{{ name | lower }}}}
  version: ${{{{ version }}}}

source:
  url: {info.source_url or f"https://pypi.org/packages/source/{info.name[0]}/{info.name}/{info.name}-{info.version}.tar.gz"}
  sha256: {info.sha256 or "REPLACE_SHA256"}

build:
  number: 0
  noarch: python
  script: ${{{{ PYTHON }}}} -m pip install . -vv --no-deps --no-build-isolation

requirements:
  host:
    - python ${{{{ python_min }}}}.*
    - pip
    - hatchling
  run:
    - python >=${{{{ python_min }}}}
'''

    # Add dependencies
    for dep in info.dependencies[:10]:  # Limit to avoid huge lists
        recipe += f"    - {dep}\n"

    recipe += f'''
tests:
  - python:
      imports:
        - {info.name.replace("-", "_").lower()}
      pip_check: true

about:
  homepage: {info.homepage or "REPLACE_HOMEPAGE"}
  license: {info.license or "REPLACE_LICENSE"}
  license_file: {info.license_file}
  summary: {info.summary or "REPLACE_SUMMARY"}

extra:
  recipe-maintainers:
    - REPLACE_MAINTAINER
'''

    # Write recipe
    output_dir.mkdir(parents=True, exist_ok=True)
    recipe_path = output_dir / "recipe.yaml"
    recipe_path.write_text(recipe)

    return recipe_path


def generate_meta_yaml(info: PackageInfo, output_dir: Path) -> Path:
    """Generate meta.yaml (legacy format)."""
    # Parse python_min
    match = re.search(r">=\s*(\d+\.\d+)", info.python_requires)
    python_min = match.group(1) if match else "3.10"

    recipe = f'''{{% set name = "{info.name}" %}}
{{% set version = "{info.version}" %}}

package:
  name: {{{{ name|lower }}}}
  version: {{{{ version }}}}

source:
  url: {info.source_url or f"https://pypi.org/packages/source/{{{{ name[0] }}}}/{{{{ name }}}}/{{{{ name }}}}-{{{{ version }}}}.tar.gz"}
  sha256: {info.sha256 or "REPLACE_SHA256"}

build:
  number: 0
  noarch: python
  script: {{{{ PYTHON }}}} -m pip install . -vv --no-deps --no-build-isolation

requirements:
  host:
    - python {{{{ python_min }}}}
    - pip
    - hatchling
  run:
    - python >={{{{ python_min }}}}
'''

    for dep in info.dependencies[:10]:
        recipe += f"    - {dep}\n"

    recipe += f'''
test:
  imports:
    - {info.name.replace("-", "_").lower()}
  commands:
    - pip check
  requires:
    - pip

about:
  home: {info.homepage or "REPLACE_HOMEPAGE"}
  license: {info.license or "REPLACE_LICENSE"}
  license_file: {info.license_file}
  summary: {info.summary or "REPLACE_SUMMARY"}

extra:
  recipe-maintainers:
    - REPLACE_MAINTAINER
'''

    output_dir.mkdir(parents=True, exist_ok=True)
    recipe_path = output_dir / "meta.yaml"
    recipe_path.write_text(recipe)

    return recipe_path


def copy_template(template_name: str, output_dir: Path, **replacements) -> Path:
    """Copy and customize a template."""
    # Find template
    skill_dir = Path(__file__).parent.parent
    templates_dir = skill_dir / "templates"

    # Map template names to files
    template_map = {
        "python-noarch": "python/noarch-recipe.yaml",
        "python-compiled": "python/compiled-recipe.yaml",
        "python-maturin": "python/maturin-recipe.yaml",
        "rust-cli": "rust/cli-recipe.yaml",
        "go-pure": "go/pure-recipe.yaml",
        "go-cgo": "go/cgo-recipe.yaml",
        "c-cmake": "c-cpp/cmake-recipe.yaml",
    }

    template_path = templates_dir / template_map.get(template_name, f"{template_name}.yaml")

    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_name}")

    content = template_path.read_text()

    # Apply replacements
    for key, value in replacements.items():
        content = content.replace(f"REPLACE_{key.upper()}", str(value))

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "recipe.yaml"
    output_path.write_text(content)

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Generate conda-forge recipes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s pypi requests
  %(prog)s pypi numpy==1.26.0
  %(prog)s template python-noarch --name mypackage --version 1.0.0
  %(prog)s github owner/repo --version v1.0.0
        """
    )

    subparsers = parser.add_subparsers(dest="source", required=True)

    # PyPI source
    pypi_parser = subparsers.add_parser("pypi", help="Generate from PyPI")
    pypi_parser.add_argument("package", help="Package name (optionally with version: pkg==1.0)")
    pypi_parser.add_argument("--output", "-o", type=Path, default=None,
                             help="Output directory")
    pypi_parser.add_argument("--format", choices=["v1", "legacy"], default="v1",
                             help="Recipe format")

    # Template source
    tmpl_parser = subparsers.add_parser("template", help="Generate from template")
    tmpl_parser.add_argument("template", help="Template name (e.g., python-noarch)")
    tmpl_parser.add_argument("--name", required=True, help="Package name")
    tmpl_parser.add_argument("--version", default="1.0.0", help="Package version")
    tmpl_parser.add_argument("--output", "-o", type=Path, default=None,
                             help="Output directory")
    tmpl_parser.add_argument("--maintainer", default="MAINTAINER",
                             help="GitHub username")

    # GitHub source
    gh_parser = subparsers.add_parser("github", help="Generate from GitHub repo")
    gh_parser.add_argument("repo", help="Repository (owner/name)")
    gh_parser.add_argument("--version", "-v", help="Version/tag")
    gh_parser.add_argument("--output", "-o", type=Path, default=None,
                             help="Output directory")

    args = parser.parse_args()

    try:
        if args.source == "pypi":
            # Parse package name and version
            if "==" in args.package:
                name, version = args.package.split("==")
            else:
                name, version = args.package, None

            print(f"Fetching info for {name}...")
            info = fetch_pypi_info(name, version)

            output_dir = args.output or Path(f"recipes/{info.name}")

            if args.format == "v1":
                path = generate_recipe_yaml(info, output_dir)
            else:
                path = generate_meta_yaml(info, output_dir)

            print(f"Generated: {path}")

        elif args.source == "template":
            output_dir = args.output or Path(f"recipes/{args.name}")

            path = copy_template(
                args.template,
                output_dir,
                name=args.name,
                version=args.version,
                maintainer=args.maintainer,
            )
            print(f"Generated from template: {path}")

        elif args.source == "github":
            # Fetch GitHub release info
            if not REQUESTS_AVAILABLE:
                print("Error: requests library required")
                sys.exit(1)

            owner, name = args.repo.split("/")
            version = args.version

            if not version:
                # Get latest release
                url = f"https://api.github.com/repos/{owner}/{name}/releases/latest"
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    version = response.json().get("tag_name", "1.0.0")
                else:
                    version = "1.0.0"

            output_dir = args.output or Path(f"recipes/{name}")

            info = PackageInfo(
                name=name,
                version=version.lstrip("v"),
                homepage=f"https://github.com/{owner}/{name}",
                source_url=f"https://github.com/{owner}/{name}/archive/refs/tags/{version}.tar.gz",
            )

            path = generate_recipe_yaml(info, output_dir)
            print(f"Generated: {path}")
            print("Note: SHA256 and license need to be filled in manually")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
