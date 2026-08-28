#!/usr/bin/env python3
"""
Migrate feedstocks from meta.yaml to recipe.yaml format.

Usage:
    python feedstock-migrator.py recipes/my-package
    python feedstock-migrator.py recipes/my-package --dry-run
    python feedstock-migrator.py recipes/my-package --backup
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


@dataclass
class MigrationResult:
    """Result of migration."""
    success: bool
    input_file: Path
    output_file: Optional[Path] = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def convert_jinja_syntax(content: str) -> str:
    """Convert Jinja2 {{ }} to ${{ }} syntax."""
    # Convert {{ var }} to ${{ var }}
    content = re.sub(r'\{\{([^}]+)\}\}', r'${{ \1 }}', content)
    return content


def convert_selectors(content: str) -> list[str]:
    """Convert # [selector] comments to if/then blocks."""
    lines = content.split('\n')
    converted = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check for selector comment
        selector_match = re.search(r'#\s*\[([^\]]+)\]', line)

        if selector_match:
            selector = selector_match.group(1).strip()
            # Remove the selector comment
            clean_line = re.sub(r'\s*#\s*\[[^\]]+\]', '', line)

            # Get indentation
            indent = len(line) - len(line.lstrip())
            base_indent = ' ' * indent

            # Check if it's a skip line
            if 'skip:' in clean_line:
                # Convert to skip list item
                converted.append(f"{base_indent}skip:")
                converted.append(f"{base_indent}  - {selector}")
            elif clean_line.strip().startswith('- '):
                # It's a list item - convert to if/then
                item = clean_line.strip()[2:].strip()
                converted.append(f"{base_indent}- if: {selector}")
                converted.append(f"{base_indent}  then: {item}")
            else:
                # Other lines - just keep with comment removed
                converted.append(clean_line)
        else:
            converted.append(line)

        i += 1

    return converted


def convert_set_statements(content: str) -> tuple[dict, str]:
    """Extract {% set %} statements into context section."""
    context = {}

    # Find all set statements
    set_pattern = r'\{%\s*set\s+(\w+)\s*=\s*(.+?)\s*%\}'

    for match in re.finditer(set_pattern, content):
        var_name = match.group(1)
        var_value = match.group(2).strip()

        # Clean up the value
        if var_value.startswith('"') and var_value.endswith('"'):
            var_value = var_value[1:-1]
        elif var_value.startswith("'") and var_value.endswith("'"):
            var_value = var_value[1:-1]

        context[var_name] = var_value

    # Remove set statements from content
    content = re.sub(set_pattern + r'\n?', '', content)

    return context, content


def convert_test_section(content: str) -> str:
    """Convert test: to tests: list format."""
    # This is a simplified conversion
    content = re.sub(r'^test:\s*$', 'tests:', content, flags=re.MULTILINE)
    return content


def convert_about_fields(content: str) -> str:
    """Convert about section field names."""
    replacements = [
        (r'\bhome:', 'homepage:'),
        (r'\bdoc_url:', 'documentation:'),
        (r'\bdev_url:', 'repository:'),
    ]

    for old, new in replacements:
        content = re.sub(old, new, content)

    return content


def convert_pin_syntax(content: str) -> str:
    """Convert pin function syntax."""
    # max_pin -> upper_bound
    content = re.sub(r"max_pin\s*=\s*'([^']+)'", r'upper_bound="\1"', content)
    content = re.sub(r'max_pin\s*=\s*"([^"]+)"', r'upper_bound="\1"', content)

    # min_pin -> lower_bound
    content = re.sub(r"min_pin\s*=\s*'([^']+)'", r'lower_bound="\1"', content)
    content = re.sub(r'min_pin\s*=\s*"([^"]+)"', r'lower_bound="\1"', content)

    # exact=True -> exact=true
    content = re.sub(r'exact\s*=\s*True', 'exact=true', content)

    return content


def migrate_recipe(
    input_path: Path,
    output_path: Optional[Path] = None,
    dry_run: bool = False,
    backup: bool = True
) -> MigrationResult:
    """Migrate a meta.yaml to recipe.yaml."""
    result = MigrationResult(success=False, input_file=input_path)

    # Find input file
    if input_path.is_dir():
        meta_yaml = input_path / "meta.yaml"
        if not meta_yaml.exists():
            result.errors.append(f"No meta.yaml found in {input_path}")
            return result
        input_file = meta_yaml
        output_file = output_path or (input_path / "recipe.yaml")
    else:
        input_file = input_path
        output_file = output_path or input_path.with_name("recipe.yaml")

    result.output_file = output_file

    # Read input
    try:
        content = input_file.read_text(encoding='utf-8')
    except Exception as e:
        result.errors.append(f"Failed to read {input_file}: {e}")
        return result

    # Extract context from {% set %} statements
    context, content = convert_set_statements(content)

    # Convert Jinja syntax
    content = convert_jinja_syntax(content)

    # Convert selectors
    lines = convert_selectors(content)
    content = '\n'.join(lines)

    # Convert pin syntax
    content = convert_pin_syntax(content)

    # Convert about fields
    content = convert_about_fields(content)

    # Convert test section
    content = convert_test_section(content)

    # Build context section
    context_yaml = "context:\n"
    for key, value in context.items():
        if isinstance(value, str) and not value.replace('.', '').isdigit():
            context_yaml += f'  {key}: "{value}"\n'
        else:
            context_yaml += f"  {key}: {value}\n"

    # Build final recipe
    final_content = f"""# yaml-language-server: $schema=https://raw.githubusercontent.com/prefix-dev/recipe-format/main/schema.json
schema_version: 1

{context_yaml}
{content}"""

    # Clean up multiple blank lines
    final_content = re.sub(r'\n{3,}', '\n\n', final_content)

    if dry_run:
        print("=" * 60)
        print("DRY RUN - Would generate:")
        print("=" * 60)
        print(final_content[:2000])
        if len(final_content) > 2000:
            print(f"... ({len(final_content)} total characters)")
        result.success = True
        return result

    # Backup original
    if backup and output_file.exists():
        backup_file = output_file.with_suffix('.yaml.bak')
        shutil.copy(output_file, backup_file)
        result.warnings.append(f"Backup created: {backup_file}")

    # Write output
    try:
        output_file.write_text(final_content, encoding='utf-8')
        result.success = True
    except Exception as e:
        result.errors.append(f"Failed to write {output_file}: {e}")
        return result

    # Add warnings for manual review needed
    result.warnings.extend([
        "Manual review needed for:",
        "  - Complex Jinja conditionals ({% if %})",
        "  - Selector logic in if/then blocks",
        "  - Test section structure",
        "  - Multi-output recipes",
    ])

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Migrate meta.yaml to recipe.yaml format"
    )
    parser.add_argument("recipe", type=Path,
                        help="Recipe path (directory with meta.yaml or file)")
    parser.add_argument("--output", "-o", type=Path,
                        help="Output file path")
    parser.add_argument("--dry-run", "-n", action="store_true",
                        help="Show what would be generated without writing")
    parser.add_argument("--backup", "-b", action="store_true", default=True,
                        help="Backup existing recipe.yaml")
    parser.add_argument("--no-backup", action="store_false", dest="backup",
                        help="Don't backup existing files")

    args = parser.parse_args()

    result = migrate_recipe(
        args.recipe,
        args.output,
        dry_run=args.dry_run,
        backup=args.backup
    )

    if result.warnings:
        print("\nWarnings:")
        for warning in result.warnings:
            print(f"  {warning}")

    if result.errors:
        print("\nErrors:")
        for error in result.errors:
            print(f"  {error}")
        sys.exit(1)

    if result.success:
        if not args.dry_run:
            print(f"\nMigration complete: {result.output_file}")
            print("\nNext steps:")
            print("  1. Review the generated recipe.yaml")
            print("  2. Fix any conversion issues manually")
            print("  3. Run: conda-smithy recipe-lint")
            print("  4. Test build: rattler-build build -r recipe.yaml -c conda-forge")
    else:
        print("\nMigration failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
