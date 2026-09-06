#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# ///
"""Resolve BMad's central TOML layers to JSON.

REPO-CUSTOM (local-recipes multi-project pattern): on top of the four
installer-managed central layers, an optional per-project overlay adds
layers 5-6 (highest priority last):

  1. {project-root}/_bmad/config.toml                                   (installer team)
  2. {project-root}/_bmad/config.user.toml                              (installer user)
  3. {project-root}/_bmad/custom/config.toml                            (custom team — global)
  4. {project-root}/_bmad/custom/config.user.toml                       (custom user — global)
  5. {project-root}/_bmad-output/projects/<slug>/.bmad-config.toml      (project team)  [if active project resolves]
  6. {project-root}/_bmad-output/projects/<slug>/.bmad-config.user.toml (project user)  [if active project resolves]

Active-project resolution (only matters for layers 5-6):
  a. --project <slug>                              (per-call CLI override; highest priority)
  b. BMAD_ACTIVE_PROJECT environment variable
  c. {project-root}/_bmad/custom/.active-project   (single-line slug marker file, gitignored)
  d. None — layers 5 and 6 are skipped; only the four global layers resolve.

If the installer regenerates this script, re-apply the multi-project
extension (see CLAUDE.md § Multi-Project Pattern and the previous version
in git history).
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

# Installed scripts are consumer files, not a location for interpreter caches.
sys.dont_write_bytecode = True

try:
    from config_utils import ConfigError, load_central_config, load_toml, structural_merge
except ModuleNotFoundError as error:
    if error.name != "tomllib":
        raise
    sys.stderr.write("error: Python 3.11+ is required (stdlib `tomllib` not found).\n")
    raise SystemExit(3) from None


_MISSING = object()

_SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def write_json_stdout(output) -> None:
    """Pin stdout to UTF-8 — a Windows cp1252 default cannot encode emoji icons."""
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8")
    sys.stdout.write(json.dumps(output, indent=2, ensure_ascii=False) + "\n")


def extract_key(data, dotted_key: str):
    current = data
    for part in dotted_key.split("."):
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Resolve BMad central config using up-to-six-layer TOML merge "
            "with optional per-project overlay."
        )
    )
    parser.add_argument(
        "--project-root",
        "-p",
        required=True,
        help="Absolute project root containing _bmad/",
    )
    parser.add_argument(
        "--key",
        "-k",
        action="append",
        default=[],
        help="Dotted field path to resolve (repeatable). Omit for full dump.",
    )
    parser.add_argument(
        "--project",
        help=(
            "Active project slug — overrides BMAD_ACTIVE_PROJECT env and the "
            ".active-project marker for this call."
        ),
    )
    parser.add_argument(
        "--show-active-project",
        action="store_true",
        help="Print the resolved active project slug to stderr (debug).",
    )
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()

    try:
        merged = load_central_config(project_root)

        active_project = resolve_active_project(project_root, args.project)
        if args.show_active_project:
            sys.stderr.write(f"active_project: {active_project or '(none)'}\n")

        if active_project:
            project_dir = project_root / "_bmad-output" / "projects" / active_project
            merged = structural_merge(
                merged, load_toml(project_dir / ".bmad-config.toml")
            )
            merged = structural_merge(
                merged, load_toml(project_dir / ".bmad-config.user.toml")
            )
            # Surface the active project for downstream consumers.
            if isinstance(merged, dict):
                merged.setdefault("active_project", active_project)
    except ConfigError as error:
        sys.stderr.write(f"error: {error}\n")
        return 1

    output = merged
    if args.key:
        output = {}
        for key in args.key:
            value = extract_key(merged, key)
            if value is not _MISSING:
                output[key] = value
    write_json_stdout(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
