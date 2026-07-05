"""Meta: every recipes/*/recipe.yaml must survive the full-parse audit (G92/G98).

The 2026-07-04/05 metadata-refresh session found NINE corrupted recipe files in
COMMITTED history that the duplicate-key grep audit was blind to: four stray
` []` fold-artifact lines (parse-fatal or a landmine for the next line-based
editor) and five unquoted-`#` flow-list values that YAML either refuses
(unterminated flow sequence) or silently truncates at the comment marker.
A tenth file (GetPyPiLatestVersion) carried v0 ``{{ PYTHON }}`` jinja in a v1
script list — also parse-fatal (G20).

This test makes the repo-wide clean state (898/898 at v8.68.x) permanent:

1. ``yaml.safe_load`` over every recipe.yaml — catches parse-fatal classes
   (stray tokens, v0 jinja at scalar start, unterminated flow sequences).
2. Duplicate ``cfe-conda-name`` keys — PyYAML silently keeps the LAST duplicate
   key, so the G92 fold-then-restamp corruption parses fine; only rattler-build's
   strict parser rejects it. Grep-level check per file.
3. Stray whitespace-only ``[]`` lines — legitimate only as a block value
   directly under a bare ``key:`` line; anywhere else it is a G92 fold artifact.
4. Unquoted `` #`` inside cfe free-text list items (blocker/updates lists) —
   parses fine in block form but YAML treats `` #`` as a comment start and
   silently truncates the stored value (G92 extension class b).

v0 jinja meta.yaml files are exempt by construction (only recipe.yaml is
scanned; meta.yaml is not YAML before rendering and is never safe_load'd).
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[5]
RECIPES_DIR = REPO_ROOT / "recipes"

CFE_LIST_KEYS = ("cfe-forge-blocker-list", "cfe-forge-recipe-updates-needed")


def _recipe_files() -> list[Path]:
    return sorted(RECIPES_DIR.glob("*/recipe.yaml"))


def test_recipes_dir_is_populated() -> None:
    assert len(_recipe_files()) > 500, "recipes/ glob came back suspiciously small"


def test_all_recipe_yaml_parse() -> None:
    failures = []
    for p in _recipe_files():
        try:
            yaml.safe_load(p.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 — collect every parse error
            failures.append(f"{p.relative_to(REPO_ROOT)}: {str(exc).splitlines()[0]}")
    assert not failures, "unparseable recipe.yaml (G92/G98/G20 class):\n" + "\n".join(failures)


def test_no_duplicate_cfe_identity_keys() -> None:
    offenders = []
    for p in _recipe_files():
        n = len(re.findall(r"^\s*cfe-conda-name:", p.read_text(encoding="utf-8"), re.M))
        if n > 1:
            offenders.append(f"{p.parent.name}: cfe-conda-name x{n}")
    assert not offenders, (
        "duplicate cfe keys (G92 fold-then-restamp; PyYAML hides these, "
        "rattler-build rejects them):\n" + "\n".join(offenders)
    )


def test_no_stray_empty_flow_list_lines() -> None:
    offenders = []
    for p in _recipe_files():
        lines = p.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            if re.match(r"^\s*\[\]\s*$", line):
                prev = lines[i - 1].rstrip() if i else ""
                if not prev.endswith(":"):
                    offenders.append(f"{p.parent.name}:{i + 1}")
    assert not offenders, (
        "stray ' []' fold-artifact lines (G92 extension class a):\n" + "\n".join(offenders)
    )


def test_no_unquoted_hash_in_cfe_list_items() -> None:
    offenders = []
    for p in _recipe_files():
        lines = p.read_text(encoding="utf-8").splitlines()
        in_block = False
        for i, line in enumerate(lines):
            stripped = line.rstrip()
            if re.match(rf"^\s*({'|'.join(CFE_LIST_KEYS)}):\s*$", stripped):
                in_block = True
                continue
            if in_block:
                if not re.match(r"^\s*- ", stripped):
                    in_block = False
                    continue
                item = stripped.split("- ", 1)[1]
                # quoted items are safe; unquoted items with ' #' truncate silently
                if not item.startswith(('"', "'")) and " #" in item:
                    offenders.append(f"{p.parent.name}:{i + 1}: {stripped.strip()!r}")
            # inline flow lists with an unquoted # are parse-fatal -> caught by
            # test_all_recipe_yaml_parse; no separate check needed here.
    assert not offenders, (
        "unquoted ' #' in cfe free-text list items — YAML silently truncates the "
        "value at the comment marker (G92 extension class b); double-quote the "
        "item:\n" + "\n".join(offenders)
    )
