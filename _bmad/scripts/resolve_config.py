#!/usr/bin/env python3
"""
Resolve BMad's central config using up-to-six-layer TOML merge with optional
per-project overlay.

Reads from the following layers (highest priority last):
  1. {project-root}/_bmad/config.toml                                  (installer team)
  2. {project-root}/_bmad/config.user.toml                             (installer user)
  3. {project-root}/_bmad/custom/config.toml                           (custom team — global, all projects)
  4. {project-root}/_bmad/custom/config.user.toml                      (custom user — global, all projects)
  5. {project-root}/_bmad-output/projects/<slug>/.bmad-config.toml     (project team — committed) [if active project resolves]
  6. {project-root}/_bmad-output/projects/<slug>/.bmad-config.user.toml (project user — gitignored)  [if active project resolves]

Active-project resolution (only matters for layers 5–6):
  a. --project <slug>                              (per-call CLI override; highest priority)
  b. BMAD_ACTIVE_PROJECT environment variable
  c. {project-root}/_bmad/custom/.active-project   (single-line slug marker file, gitignored)
  d. None — layers 5 and 6 are skipped; only the four global layers resolve.

Outputs merged JSON to stdout. Errors go to stderr.

Requires Python 3.11+ (uses stdlib `tomllib`). No `uv`, no `pip install`,
no virtualenv — plain `python3` is sufficient.

  python3 resolve_config.py --project-root /abs/path/to/project
  python3 resolve_config.py --project-root ... --key core
  python3 resolve_config.py --project-root ... --key agents
  python3 resolve_config.py --project-root ... --project presenton-pixi-image
  python3 resolve_config.py --project-root ... --project local-recipes --key output_folder

Merge rules (same as resolve_customization.py):
  - Scalars: override wins
  - Tables: deep merge
  - Arrays of tables where every item shares `code` or `id`: merge by that key
  - All other arrays: append
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:
    sys.stderr.write(
        "error: Python 3.11+ is required (stdlib `tomllib` not found).\n"
    )
    sys.exit(3)


_MISSING = object()
_KEYED_MERGE_FIELDS = ("code", "id")
_SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def load_toml(file_path: Path, required: bool = False) -> dict:
    if not file_path.exists():
        if required:
            sys.stderr.write(f"error: required config file not found: {file_path}\n")
            sys.exit(1)
        return {}
    try:
        with file_path.open("rb") as f:
            parsed = tomllib.load(f)
        if not isinstance(parsed, dict):
            return {}
        return parsed
    except tomllib.TOMLDecodeError as error:
        level = "error" if required else "warning"
        sys.stderr.write(f"{level}: failed to parse {file_path}: {error}\n")
        if required:
            sys.exit(1)
        return {}
    except OSError as error:
        level = "error" if required else "warning"
        sys.stderr.write(f"{level}: failed to read {file_path}: {error}\n")
        if required:
            sys.exit(1)
        return {}


def _detect_keyed_merge_field(items):
    if not items or not all(isinstance(item, dict) for item in items):
        return None
    for candidate in _KEYED_MERGE_FIELDS:
        if all(item.get(candidate) is not None for item in items):
            return candidate
    return None


def _merge_by_key(base, override, key_name):
    result = []
    index_by_key = {}
    for item in base:
        if not isinstance(item, dict):
            continue
        if item.get(key_name) is not None:
            index_by_key[item[key_name]] = len(result)
        result.append(dict(item))
    for item in override:
        if not isinstance(item, dict):
            result.append(item)
            continue
        key = item.get(key_name)
        if key is not None and key in index_by_key:
            result[index_by_key[key]] = dict(item)
        else:
            if key is not None:
                index_by_key[key] = len(result)
            result.append(dict(item))
    return result


def _merge_arrays(base, override):
    base_arr = base if isinstance(base, list) else []
    override_arr = override if isinstance(override, list) else []
    keyed_field = _detect_keyed_merge_field(base_arr + override_arr)
    if keyed_field:
        return _merge_by_key(base_arr, override_arr, keyed_field)
    return base_arr + override_arr


def deep_merge(base, override):
    if isinstance(base, dict) and isinstance(override, dict):
        result = dict(base)
        for key, over_val in override.items():
            if key in result:
                result[key] = deep_merge(result[key], over_val)
            else:
                result[key] = over_val
        return result
    if isinstance(base, list) and isinstance(override, list):
        return _merge_arrays(base, override)
    return override


def extract_key(data, dotted_key: str):
    parts = dotted_key.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return _MISSING
    return current


def resolve_active_project(project_root: Path, cli_project: str | None) -> str | None:
    """
    Resolve the active project slug using the documented precedence:
      1. --project flag (cli_project)
      2. BMAD_ACTIVE_PROJECT env var
      3. _bmad/custom/.active-project marker file
      4. None
    Validates slug format (lowercase alphanumeric + hyphens/underscores).
    Returns the slug, or None if no active project is set.
    """
    candidates = [
        ("--project flag", cli_project),
        ("BMAD_ACTIVE_PROJECT env", os.environ.get("BMAD_ACTIVE_PROJECT")),
    ]
    marker_path = project_root / "_bmad" / "custom" / ".active-project"
    if marker_path.exists():
        try:
            marker_value = marker_path.read_text(encoding="utf-8").strip()
            candidates.append((f"{marker_path}", marker_value or None))
        except OSError as error:
            sys.stderr.write(f"warning: failed to read {marker_path}: {error}\n")

    for source, value in candidates:
        if not value:
            continue
        if not _SLUG_PATTERN.match(value):
            sys.stderr.write(
                f"error: invalid project slug from {source}: {value!r} "
                f"(expected lowercase alphanumeric + hyphens/underscores)\n"
            )
            sys.exit(2)
        return value
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Resolve BMad central config using up-to-six-layer TOML merge with optional per-project overlay.",
    )
    parser.add_argument(
        "--project-root", "-p", required=True,
        help="Absolute path to the project root (contains _bmad/)",
    )
    parser.add_argument(
        "--key", "-k", action="append", default=[],
        help="Dotted field path to resolve (repeatable). Omit for full dump.",
    )
    parser.add_argument(
        "--project",
        help="Active project slug — overrides BMAD_ACTIVE_PROJECT env and .active-project marker for this call.",
    )
    parser.add_argument(
        "--show-active-project", action="store_true",
        help="Print the resolved active project slug to stderr (debug).",
    )
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    bmad_dir = project_root / "_bmad"

    base_team = load_toml(bmad_dir / "config.toml", required=True)
    base_user = load_toml(bmad_dir / "config.user.toml")
    custom_team = load_toml(bmad_dir / "custom" / "config.toml")
    custom_user = load_toml(bmad_dir / "custom" / "config.user.toml")

    merged = deep_merge(base_team, base_user)
    merged = deep_merge(merged, custom_team)
    merged = deep_merge(merged, custom_user)

    active_project = resolve_active_project(project_root, args.project)
    if args.show_active_project:
        sys.stderr.write(f"active_project: {active_project or '(none)'}\n")

    if active_project:
        project_dir = project_root / "_bmad-output" / "projects" / active_project
        project_team = load_toml(project_dir / ".bmad-config.toml")
        project_user = load_toml(project_dir / ".bmad-config.user.toml")
        merged = deep_merge(merged, project_team)
        merged = deep_merge(merged, project_user)
        # Surface active project for downstream consumers.
        if isinstance(merged, dict):
            merged.setdefault("active_project", active_project)

    if args.key:
        output = {}
        for key in args.key:
            value = extract_key(merged, key)
            if value is not _MISSING:
                output[key] = value
    else:
        output = merged

    sys.stdout.write(json.dumps(output, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
