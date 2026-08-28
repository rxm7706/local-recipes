#!/usr/bin/env python3
"""
Check and validate license information in conda recipes.

Features:
- Validate SPDX license identifiers
- Check license_file exists in source
- Suggest SPDX corrections
- Detect common license files

Usage:
    python license-checker.py recipes/my-package
    python license-checker.py recipes/my-package --check-source
    python license-checker.py --list-spdx
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Optional

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


# Common SPDX license identifiers
SPDX_LICENSES = {
    # Permissive
    "MIT": "MIT",
    "Apache-2.0": "Apache-2.0",
    "BSD-2-Clause": "BSD-2-Clause",
    "BSD-3-Clause": "BSD-3-Clause",
    "ISC": "ISC",
    "Unlicense": "Unlicense",
    "CC0-1.0": "CC0-1.0",
    "WTFPL": "WTFPL",
    "Zlib": "Zlib",
    "BSL-1.0": "BSL-1.0",

    # Copyleft
    "GPL-2.0-only": "GPL-2.0-only",
    "GPL-2.0-or-later": "GPL-2.0-or-later",
    "GPL-3.0-only": "GPL-3.0-only",
    "GPL-3.0-or-later": "GPL-3.0-or-later",
    "LGPL-2.1-only": "LGPL-2.1-only",
    "LGPL-2.1-or-later": "LGPL-2.1-or-later",
    "LGPL-3.0-only": "LGPL-3.0-only",
    "LGPL-3.0-or-later": "LGPL-3.0-or-later",
    "AGPL-3.0-only": "AGPL-3.0-only",
    "MPL-2.0": "MPL-2.0",

    # Other
    "PSF-2.0": "PSF-2.0",
    "Python-2.0": "Python-2.0",
    "Artistic-2.0": "Artistic-2.0",
    "CDDL-1.0": "CDDL-1.0",
    "EPL-1.0": "EPL-1.0",
    "EPL-2.0": "EPL-2.0",
}

# Common non-SPDX to SPDX mappings
LICENSE_MAPPINGS = {
    # MIT variants
    "mit": "MIT",
    "mit license": "MIT",
    "mit licence": "MIT",
    "the mit license": "MIT",

    # Apache variants
    "apache": "Apache-2.0",
    "apache 2": "Apache-2.0",
    "apache 2.0": "Apache-2.0",
    "apache2": "Apache-2.0",
    "apache-2": "Apache-2.0",
    "apache license 2.0": "Apache-2.0",
    "apache software license": "Apache-2.0",
    "asl 2.0": "Apache-2.0",

    # BSD variants
    "bsd": "BSD-3-Clause",
    "bsd license": "BSD-3-Clause",
    "bsd-3": "BSD-3-Clause",
    "bsd 3-clause": "BSD-3-Clause",
    "bsd-2": "BSD-2-Clause",
    "bsd 2-clause": "BSD-2-Clause",
    "simplified bsd": "BSD-2-Clause",
    "new bsd": "BSD-3-Clause",

    # GPL variants
    "gpl": "GPL-3.0-or-later",
    "gplv2": "GPL-2.0-only",
    "gplv3": "GPL-3.0-only",
    "gpl-2": "GPL-2.0-only",
    "gpl-3": "GPL-3.0-only",
    "gpl v2": "GPL-2.0-only",
    "gpl v3": "GPL-3.0-only",
    "gnu gpl": "GPL-3.0-or-later",
    "gnu gpl v3": "GPL-3.0-only",

    # LGPL variants
    "lgpl": "LGPL-3.0-or-later",
    "lgplv2": "LGPL-2.1-only",
    "lgplv3": "LGPL-3.0-only",
    "lgpl-2.1": "LGPL-2.1-only",
    "lgpl-3.0": "LGPL-3.0-only",

    # Other
    "public domain": "CC0-1.0",
    "unlicense": "Unlicense",
    "isc": "ISC",
    "psf": "PSF-2.0",
    "python": "Python-2.0",
    "mpl": "MPL-2.0",
    "mpl 2.0": "MPL-2.0",
    "mpl-2": "MPL-2.0",
    "mozilla": "MPL-2.0",
}

# Common license file names
LICENSE_FILES = [
    "LICENSE",
    "LICENSE.txt",
    "LICENSE.md",
    "LICENSE.rst",
    "LICENCE",
    "LICENCE.txt",
    "COPYING",
    "COPYING.txt",
    "COPYRIGHT",
    "MIT-LICENSE",
    "MIT-LICENSE.txt",
    "Apache-2.0.txt",
]


def is_valid_spdx(license_id: str) -> bool:
    """Check if license is a valid SPDX identifier."""
    # Handle compound licenses (e.g., "MIT OR Apache-2.0")
    parts = re.split(r'\s+(?:AND|OR|WITH)\s+', license_id)
    for part in parts:
        part = part.strip('()')
        if part not in SPDX_LICENSES:
            return False
    return True


def suggest_spdx(license_str: str) -> Optional[str]:
    """Suggest SPDX identifier for non-standard license string."""
    normalized = license_str.lower().strip()

    # Direct mapping
    if normalized in LICENSE_MAPPINGS:
        return LICENSE_MAPPINGS[normalized]

    # Fuzzy matching
    for key, value in LICENSE_MAPPINGS.items():
        if key in normalized:
            return value

    return None


def extract_license_info(recipe_path: Path) -> tuple[Optional[str], Optional[str]]:
    """Extract license and license_file from recipe."""
    if recipe_path.is_dir():
        for name in ["recipe.yaml", "meta.yaml"]:
            if (recipe_path / name).exists():
                recipe_path = recipe_path / name
                break
        else:
            return None, None

    content = recipe_path.read_text()

    license_id = None
    license_file = None

    # Handle both formats
    if YAML_AVAILABLE:
        # Clean content for YAML parsing
        clean_content = re.sub(r'\$\{\{[^}]+\}\}', 'PLACEHOLDER', content)
        clean_content = re.sub(r'\{\{[^}]+\}\}', 'PLACEHOLDER', clean_content)

        try:
            data = yaml.safe_load(clean_content)
            about = data.get("about", {})
            license_id = about.get("license")
            license_file = about.get("license_file")
        except yaml.YAMLError:
            pass

    # Fallback to regex
    if license_id is None:
        match = re.search(r'^\s*license:\s*(.+)$', content, re.MULTILINE)
        if match:
            license_id = match.group(1).strip()

    if license_file is None:
        match = re.search(r'^\s*license_file:\s*(.+)$', content, re.MULTILINE)
        if match:
            license_file = match.group(1).strip()

    return license_id, license_file


def check_license_file_exists(source_dir: Path, license_file: str) -> bool:
    """Check if license file exists in source."""
    if not source_dir.exists():
        return False

    # Handle list of files
    if isinstance(license_file, list):
        files = license_file
    else:
        files = [license_file]

    for f in files:
        path = source_dir / f
        if path.exists():
            return True

    return False


def find_license_files(source_dir: Path) -> list[str]:
    """Find common license files in source directory."""
    found = []

    for name in LICENSE_FILES:
        if (source_dir / name).exists():
            found.append(name)

    # Also check common subdirs
    for subdir in ["", "docs", "doc", "licenses"]:
        dir_path = source_dir / subdir if subdir else source_dir
        if dir_path.exists():
            for f in dir_path.iterdir():
                if f.name.upper().startswith(("LICENSE", "LICENCE", "COPYING")):
                    rel_path = f.relative_to(source_dir)
                    if str(rel_path) not in found:
                        found.append(str(rel_path))

    return found


def main():
    parser = argparse.ArgumentParser(
        description="Check and validate license information in conda recipes"
    )
    parser.add_argument("recipe", type=Path, nargs="?",
                        help="Recipe path (directory or file)")
    parser.add_argument("--check-source", "-s", type=Path,
                        help="Source directory to check for license files")
    parser.add_argument("--list-spdx", action="store_true",
                        help="List common SPDX identifiers")
    parser.add_argument("--suggest", action="store_true",
                        help="Suggest corrections for invalid licenses")

    args = parser.parse_args()

    if args.list_spdx:
        print("Common SPDX License Identifiers:")
        print("=" * 40)
        for category, licenses in [
            ("Permissive", ["MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "Unlicense"]),
            ("Copyleft", ["GPL-3.0-only", "GPL-2.0-only", "LGPL-3.0-only", "MPL-2.0", "AGPL-3.0-only"]),
            ("Other", ["PSF-2.0", "Python-2.0", "CC0-1.0"]),
        ]:
            print(f"\n{category}:")
            for lic in licenses:
                print(f"  {lic}")
        return

    if not args.recipe:
        parser.print_help()
        return

    # Extract license info
    license_id, license_file = extract_license_info(args.recipe)

    print(f"Recipe: {args.recipe}")
    print("=" * 50)

    # Check license
    if license_id:
        print(f"License: {license_id}")

        if is_valid_spdx(license_id):
            print("  [OK] Valid SPDX identifier")
        else:
            print("  [WARN] Not a standard SPDX identifier")
            if args.suggest:
                suggestion = suggest_spdx(license_id)
                if suggestion:
                    print(f"  [SUGGEST] Use '{suggestion}' instead")
    else:
        print("License: NOT FOUND")
        print("  [ERROR] Recipe must specify a license")

    # Check license_file
    if license_file:
        print(f"License file: {license_file}")

        if args.check_source:
            if check_license_file_exists(args.check_source, license_file):
                print("  [OK] File exists in source")
            else:
                print("  [ERROR] File not found in source")

                # Suggest alternatives
                found = find_license_files(args.check_source)
                if found:
                    print(f"  [SUGGEST] Found these files: {', '.join(found)}")
    else:
        print("License file: NOT SPECIFIED")
        print("  [ERROR] Recipe must specify license_file")

        if args.check_source:
            found = find_license_files(args.check_source)
            if found:
                print(f"  [SUGGEST] Found these files: {', '.join(found)}")

    # Summary
    print("\n" + "=" * 50)
    errors = []
    if not license_id:
        errors.append("missing license")
    elif not is_valid_spdx(license_id):
        errors.append("invalid SPDX license")
    if not license_file:
        errors.append("missing license_file")

    if errors:
        print(f"[FAIL] Issues found: {', '.join(errors)}")
        sys.exit(1)
    else:
        print("[OK] License information is valid")


if __name__ == "__main__":
    main()
