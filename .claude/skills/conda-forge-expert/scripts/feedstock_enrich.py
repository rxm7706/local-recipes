#!/usr/bin/env python3
"""Enrich a freshly-generated recipe with metadata from the existing conda-forge feedstock.

v6.4 implementation of items 3a (maintainer carry-over) and 3b (curated metadata
carry-over). Designed to run as a post-processor after grayskull / npm /
generate_recipe_from_pypi has produced a recipe.yaml — never as a generator
itself.

Field-by-field merge policy (verified against prefix-dev/recipe-format $defs.About;
v0/v1 field names follow `reference_v0_v1_about_fields` memory entry):

| Field                                | Policy                                     |
|--------------------------------------|--------------------------------------------|
| extra.recipe-maintainers             | Union (feedstock + rxm7706, dedup)         |
| extra.recipe-maintainers-emeritus    | Carry over (preserve historical record)    |
| extra.feedstock-name                 | Carry over (identity)                      |
| about.homepage                       | Feedstock wins if grayskull empty          |
| about.repository                     | Feedstock wins if grayskull empty/wrong    |
| about.documentation                  | Feedstock wins always (grayskull rarely emits) |
| about.summary                        | Grayskull wins (freshest from PyPI)        |
| about.description                    | Feedstock wins if longer (hand-curated)    |
| about.license                        | Match — diverge = abort with explicit error |
| about.license_file                   | Feedstock wins (paths + secondary sources resolved) |

Never carried over: requirements.host/run/build (per D3 — grayskull always wins;
upstream-driven and freshness matters), source URLs/sha256, build script, tests.

CLI:
    feedstock_enrich.py <recipe-path>            # apply merges, write back
    feedstock_enrich.py <recipe-path> --dry-run  # report what would change

Always adds rxm7706 to maintainers even when no feedstock exists (idempotent).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

# Re-use the lookup primitive — sibling script imported at runtime.
sys.path.insert(0, str(Path(__file__).parent))
from feedstock_lookup import feedstock_lookup  # type: ignore[import-not-found]  # noqa: E402

DEFAULT_MAINTAINER = "rxm7706"

# Map v0 (meta.yaml) about-field names → v1 (recipe.yaml) names so we can
# translate when the existing feedstock is meta.yaml format and the
# fresh recipe is v1. Aligns with skill memory `reference_v0_v1_about_fields`.
_V0_TO_V1_ABOUT = {
    "home": "homepage",
    "dev_url": "repository",
    "doc_url": "documentation",
    "doc_source_url": "documentation",
}


def _normalize_about(about: dict) -> dict:
    """Return a copy of `about` with v0 field names rewritten to v1 names.

    No-op for already-v1 dicts (the v1 names are simply absent from the
    translation map).
    """
    if not isinstance(about, dict):
        return {}
    out = {}
    for key, value in about.items():
        out[_V0_TO_V1_ABOUT.get(key, key)] = value
    # license_family was removed in v1 — drop it silently.
    out.pop("license_family", None)
    return out


def _load_recipe(path: Path) -> Any:
    """Load a recipe.yaml file using ruamel.yaml in round-trip mode so comments
    and ordering survive the write-back."""
    from ruamel.yaml import YAML

    yaml = YAML(typ="rt")  # round-trip preserves comments
    yaml.preserve_quotes = True
    return yaml.load(path.read_text())


def _save_recipe(path: Path, data: Any) -> None:
    from ruamel.yaml import YAML

    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    with path.open("w") as fh:
        yaml.dump(data, fh)


def _merge_maintainers(generated: list, feedstock: list) -> tuple[list, list]:
    """Return (final_list, additions). final_list is the union with rxm7706
    appended last; additions is what was new beyond `generated` (for reporting)."""
    # Normalize to lowercased strings for dedup but preserve original case for output.
    seen = {str(m).lower() for m in (generated or [])}
    final = list(generated or [])
    additions: list = []
    for name in feedstock or []:
        if str(name).lower() not in seen:
            final.append(name)
            additions.append(name)
            seen.add(str(name).lower())
    if DEFAULT_MAINTAINER.lower() not in seen:
        final.append(DEFAULT_MAINTAINER)
        additions.append(DEFAULT_MAINTAINER)
    return final, additions


def _is_empty(value: Any) -> bool:
    return value is None or value == "" or value == []


def _enrich_about(generated_about: dict, feedstock_about: dict) -> tuple[dict, list[str], Optional[str]]:
    """Apply the field-by-field about merge. Returns (merged_about, change_log, abort_reason).

    abort_reason is non-None when the licenses diverge — caller should surface
    this to the user rather than silently picking one.
    """
    merged = dict(generated_about or {})
    feedstock_v1 = _normalize_about(feedstock_about)
    changes: list[str] = []

    # License divergence is a hard abort
    g_license = (generated_about or {}).get("license")
    f_license = feedstock_v1.get("license")
    if g_license and f_license and g_license != f_license:
        return merged, changes, (
            f"license diverges: generated='{g_license}' vs feedstock='{f_license}'. "
            "Human review required — license changes have legal implications."
        )

    # Feedstock-wins-when-empty fields
    for field in ("homepage", "repository", "documentation"):
        if _is_empty(merged.get(field)) and feedstock_v1.get(field):
            merged[field] = feedstock_v1[field]
            changes.append(f"about.{field} ← feedstock ({feedstock_v1[field]!r})")

    # Description: feedstock wins if longer (hand-curated paragraphs)
    g_desc = merged.get("description") or ""
    f_desc = feedstock_v1.get("description") or ""
    if len(str(f_desc)) > len(str(g_desc)):
        merged["description"] = f_desc
        changes.append(f"about.description ← feedstock (longer: {len(str(f_desc))} > {len(str(g_desc))} chars)")

    # license_file: feedstock wins (paths often resolved with secondary sources,
    # like the cocoindex sdist-missing-LICENSE pattern)
    if feedstock_v1.get("license_file") and feedstock_v1.get("license_file") != merged.get("license_file"):
        merged["license_file"] = feedstock_v1["license_file"]
        changes.append(f"about.license_file ← feedstock ({feedstock_v1['license_file']!r})")

    return merged, changes, None


def enrich_recipe(recipe_path: Path, *, dry_run: bool = False) -> dict:
    """Apply feedstock-aware enrichment to a recipe file.

    Returns a structured report dict (JSON-serializable). When dry_run=True,
    no write happens — the report shows what would change.
    """
    if not recipe_path.exists():
        return {"success": False, "error": f"Recipe not found: {recipe_path}"}

    data = _load_recipe(recipe_path)
    if not isinstance(data, dict):
        return {"success": False, "error": f"Recipe at {recipe_path} did not parse as a YAML mapping"}

    pkg_name = data.get("context", {}).get("name") or data.get("package", {}).get("name")
    if not pkg_name:
        return {"success": False, "error": "Could not infer package name from recipe context/package"}
    pkg_name = str(pkg_name).strip().lower()

    lookup = feedstock_lookup(pkg_name)
    report: dict[str, Any] = {
        "success": True,
        "pkg_name": pkg_name,
        "feedstock_exists": lookup.exists,
        "feedstock_repo": lookup.feedstock_repo,
        "feedstock_format": lookup.format,
        "feedstock_cached": lookup.cached,
        "changes": [],
        "abort_reason": None,
        "dry_run": dry_run,
    }

    # Always ensure DEFAULT_MAINTAINER is in extra.recipe-maintainers, even
    # when no feedstock exists. This is the idempotent "always add rxm7706" path.
    extra = data.setdefault("extra", {})
    current_maintainers = list(extra.get("recipe-maintainers") or [])
    feedstock_maintainers: list = []
    feedstock_emeritus: list = []
    feedstock_name: Optional[str] = None

    if lookup.exists and lookup.parsed is not None:
        f_extra = (lookup.parsed or {}).get("extra") or {}
        feedstock_maintainers = list(f_extra.get("recipe-maintainers") or [])
        feedstock_emeritus = list(f_extra.get("recipe-maintainers-emeritus") or [])
        feedstock_name = f_extra.get("feedstock-name")

    final_maint, additions = _merge_maintainers(current_maintainers, feedstock_maintainers)
    if final_maint != current_maintainers:
        extra["recipe-maintainers"] = final_maint
        report["changes"].append(
            f"extra.recipe-maintainers += {additions} (now {final_maint})"
        )

    # Carry over emeritus if feedstock has it and the generated recipe doesn't
    if feedstock_emeritus and not extra.get("recipe-maintainers-emeritus"):
        extra["recipe-maintainers-emeritus"] = feedstock_emeritus
        report["changes"].append(
            f"extra.recipe-maintainers-emeritus ← feedstock ({feedstock_emeritus!r})"
        )

    # Carry over feedstock-name if non-default
    if feedstock_name and feedstock_name != pkg_name and not extra.get("feedstock-name"):
        extra["feedstock-name"] = feedstock_name
        report["changes"].append(f"extra.feedstock-name ← feedstock ({feedstock_name!r})")

    # About-field merge (only when a feedstock parse succeeded)
    if lookup.exists and lookup.parsed is not None:
        f_about = (lookup.parsed or {}).get("about") or {}
        g_about = data.get("about") or {}
        merged_about, about_changes, abort_reason = _enrich_about(g_about, f_about)
        if abort_reason:
            report["abort_reason"] = abort_reason
            report["success"] = False
            # Don't write the recipe — abort lets the human resolve the conflict
            return report
        if about_changes:
            data["about"] = merged_about
            report["changes"].extend(about_changes)

    if not dry_run and report["changes"]:
        _save_recipe(recipe_path, data)
        report["wrote"] = str(recipe_path)
    elif dry_run:
        report["wrote"] = None

    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Enrich a recipe with metadata from the existing conda-forge feedstock"
    )
    parser.add_argument("recipe_path", type=Path, help="Path to recipe.yaml")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report changes without writing the recipe back",
    )
    args = parser.parse_args()

    report = enrich_recipe(args.recipe_path, dry_run=args.dry_run)
    print(json.dumps(report, indent=2, default=str))
    return 0 if report.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
