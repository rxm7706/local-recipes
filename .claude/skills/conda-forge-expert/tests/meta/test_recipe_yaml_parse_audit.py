"""Meta: every recipe.yaml under recipes/ must survive the full-parse audit (G92/G98).

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

The scan is recursive (v8.98.0): recipe groups such as ``recipes/pixi/*``,
``recipes/teradata/*`` and ``recipes/tolaria-app/vendored`` nest a recipe.yaml
one level deeper, and a ``*/recipe.yaml`` glob never read them.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[5]
RECIPES_DIR = REPO_ROOT / "recipes"

CFE_LIST_KEYS = ("cfe-forge-blocker-list", "cfe-forge-recipe-updates-needed")


def _recipe_files(recipes_dir: Path = RECIPES_DIR) -> list[Path]:
    return sorted(recipes_dir.rglob("recipe.yaml"))


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


class _DuplicateKey(Exception):
    pass


class _StrictLoader(yaml.SafeLoader):
    """PyYAML's SafeLoader silently keeps the LAST value of a duplicated mapping
    key, which is exactly how 31 half-migrated v0->v1 recipes (a v1 `skip:`
    expression followed by its v0 `skip: true  # [sel]` twin; an output whose
    `package:` lost its `- ` list marker and merged into the previous output)
    passed `test_all_recipe_yaml_parse` while ruamel, conda-smithy, and
    rattler-build all reject them (v8.86.2)."""


def _strict_construct_mapping(loader, node, deep=False):
    seen: dict = {}
    for key_node, _value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise _DuplicateKey(f"{key!r} at lines {seen[key]} and {key_node.start_mark.line + 1}")
        seen[key] = key_node.start_mark.line + 1
    return yaml.SafeLoader.construct_mapping(loader, node, deep)


_StrictLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _strict_construct_mapping
)


def test_no_duplicate_mapping_keys_anywhere() -> None:
    offenders = []
    for p in _recipe_files():
        try:
            yaml.load(p.read_text(encoding="utf-8"), Loader=_StrictLoader)
        except _DuplicateKey as exc:
            offenders.append(f"{p.relative_to(REPO_ROOT)}: duplicate key {exc}")
        except Exception:  # noqa: BLE001 -- parse failures belong to test_all_recipe_yaml_parse
            continue
    assert not offenders, (
        "duplicate mapping keys (PyYAML keeps the last value silently; ruamel, "
        "conda-smithy and rattler-build reject the file -- the v0->v1 half-migration "
        "class: a v1 `skip:` beside its v0 comment-selector twin, or an output "
        "missing its `- ` marker):\n" + "\n".join(offenders)
    )


def test_no_duplicate_cfe_identity_keys() -> None:
    offenders = []
    for p in _recipe_files():
        n = len(re.findall(r"^\s*cfe-conda-name:", p.read_text(encoding="utf-8"), re.M))
        if n > 1:
            offenders.append(f"{p.relative_to(REPO_ROOT)}: cfe-conda-name x{n}")
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
                    offenders.append(f"{p.relative_to(REPO_ROOT)}:{i + 1}")
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
                    offenders.append(f"{p.relative_to(REPO_ROOT)}:{i + 1}: {stripped.strip()!r}")
            # inline flow lists with an unquoted # are parse-fatal -> caught by
            # test_all_recipe_yaml_parse; no separate check needed here.
    assert not offenders, (
        "unquoted ' #' in cfe free-text list items — YAML silently truncates the "
        "value at the comment marker (G92 extension class b); double-quote the "
        "item:\n" + "\n".join(offenders)
    )


# --- G121: conda-recipe-manager SentinelType leaks (mason Story 22.1) ---------
#
# crm's v0->v1 conversion writes the repr of its internal sentinel,
# `<conda_recipe_manager.types.SentinelType object at 0x...>`, as a mapping key
# wherever a meta.yaml construct has no v1 translation, and exits 100, not an
# error. PyYAML reads the key as a plain string, so test_all_recipe_yaml_parse
# passes the file; rattler-build refuses it at parse time. Same predicate as
# validate_recipe_yaml's tree walk (Story 22.2): a non-string mapping key, or a
# key or WHOLE scalar that is a Python object repr. Prose that only mentions a
# repr inside a longer string is not flagged.

_OBJECT_REPR_RE = re.compile(r"^<[A-Za-z_][\w.]* object at 0x[0-9a-fA-F]+>$")

# One entry per known leak: (file, the parsed-tree location of the offending
# key), each naming the story that removes it. Keying on the location, not the
# file, means a second leak in an allowlisted file still reds. An entry whose leak
# is gone fails the test, so the allowlist cannot outlive its reason.
SENTINEL_ALLOWLIST: dict[tuple[str, str], str] = {
    ("recipes/ctng-compilers/recipe.yaml", "outputs[6].tests[0]"): (
        "mason Story 22.3: the repaired file hits rattler-build 0.76.1's "
        "'Cycle detected in recipe outputs'; split from Story 22.1 by operator "
        "ruling 2026-10-09"
    ),
    ("recipes/vc/recipe.yaml", "outputs[5].tests[0]"): (
        "mason Story 22.4: a faithful v1 port needs rattler-build to emit a named "
        "track_features entry (vc14); split from Story 22.1 by operator ruling "
        "2026-10-09"
    ),
}


def _sentinel_findings(tree: object, where: str = "") -> list[tuple[str, str]]:
    """(location, detail) for every non-string key and object-repr key or value."""
    found: list[tuple[str, str]] = []
    if isinstance(tree, dict):
        for key, value in tree.items():
            here = f"{where}.{key}" if where else str(key)
            if not isinstance(key, str):
                found.append((here, f"non-string key {key!r} ({type(key).__name__})"))
            elif _OBJECT_REPR_RE.match(key):
                found.append((where or "<root>", f"object-repr key {key!r}"))
            found.extend(_sentinel_findings(value, here))
    elif isinstance(tree, list):
        for i, item in enumerate(tree):
            found.extend(_sentinel_findings(item, f"{where}[{i}]"))
    elif isinstance(tree, str) and _OBJECT_REPR_RE.match(tree):
        found.append((where, f"object-repr value {tree!r}"))
    return found


def _scan_for_sentinels(paths: list[Path], root: Path) -> dict[str, list[tuple[str, str]]]:
    hits: dict[str, list[tuple[str, str]]] = {}
    for p in paths:
        try:
            tree = yaml.safe_load(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 -- parse failures belong to test_all_recipe_yaml_parse
            continue
        found = _sentinel_findings(tree)
        if found:
            hits[p.relative_to(root).as_posix()] = found
    return hits


def _triage(
    hits: dict[str, list[tuple[str, str]]],
    allowlist: dict[tuple[str, str], str],
) -> tuple[list[str], list[str]]:
    """(unexpected findings, stale allowlist entries)."""
    unexpected = [
        f"{f}: {where}: {detail}"
        for f, found in sorted(hits.items())
        for where, detail in found
        if (f, where) not in allowlist or not detail.startswith("object-repr key")
    ]
    seen = {(f, where) for f, found in hits.items() for where, detail in found}
    stale = [f"{f} @ {where}" for f, where in sorted(set(allowlist) - seen)]
    return unexpected, stale


def test_no_crm_sentinel_keys_in_recipe_yaml() -> None:
    unexpected, stale = _triage(_scan_for_sentinels(_recipe_files(), REPO_ROOT), SENTINEL_ALLOWLIST)
    assert not unexpected, (
        "conda-recipe-manager SentinelType leak or other object-repr / non-string "
        "key (G121); repair by hand against the sibling meta.yaml:\n" + "\n".join(unexpected)
    )
    assert not stale, (
        "allowlisted leak(s) no longer present; remove the entry:\n" + "\n".join(stale)
    )


_CLEAN = (
    "schema_version: 1\n"
    "package:\n  name: demo\n  version: '1.0'\n"
    "about:\n  description: prose naming <conda_recipe_manager.types.SentinelType object at 0x1> is fine\n"
)
_LEAK = (
    "tests:\n"
    "  - <conda_recipe_manager.types.SentinelType object at 0x7f00deadbeef>:\n"
    "      requirements:\n        run:\n          - pip\n"
)


def test_sentinel_scan_reds_a_planted_key(tmp_path: Path) -> None:
    recipes = tmp_path / "recipes"
    for rel, text in {
        "clean/recipe.yaml": _CLEAN,
        "planted/recipe.yaml": _CLEAN + _LEAK,
        "intkey/recipe.yaml": _CLEAN + "extra:\n  1: one\n",
        # a recipe group nests one level deeper (recipes/pixi/*, recipes/teradata/*)
        "group/nested/recipe.yaml": _CLEAN + _LEAK,
    }.items():
        (recipes / rel).parent.mkdir(parents=True)
        (recipes / rel).write_text(text)
    hits = _scan_for_sentinels(_recipe_files(recipes), tmp_path)
    assert set(hits) == {
        "recipes/planted/recipe.yaml",
        "recipes/intkey/recipe.yaml",
        "recipes/group/nested/recipe.yaml",
    }
    assert hits["recipes/planted/recipe.yaml"][0][0] == "tests[0]"
    assert hits["recipes/planted/recipe.yaml"][0][1].startswith("object-repr key")
    assert hits["recipes/group/nested/recipe.yaml"][0][0] == "tests[0]"
    assert hits["recipes/intkey/recipe.yaml"][0][1].startswith("non-string key")
    unexpected, stale = _triage(hits, {})
    assert len(unexpected) == 3 and not stale


def test_sentinel_allowlist_is_per_location() -> None:
    allow = {("recipes/x/recipe.yaml", "outputs[6].tests[0]"): "story"}
    key = "object-repr key '<conda_recipe_manager.types.SentinelType object at 0x1>'"
    # the allowlisted leak alone passes
    assert _triage({"recipes/x/recipe.yaml": [("outputs[6].tests[0]", key)]}, allow) == ([], [])
    # a second leak in the same file reds
    unexpected, _ = _triage(
        {"recipes/x/recipe.yaml": [("outputs[6].tests[0]", key), ("outputs[2].tests[0]", key)]}, allow
    )
    assert unexpected == [f"recipes/x/recipe.yaml: outputs[2].tests[0]: {key}"]
    # a non-string key at the allowlisted location is not covered by the entry
    unexpected, _ = _triage(
        {"recipes/x/recipe.yaml": [("outputs[6].tests[0]", "non-string key 1 (int)")]}, allow
    )
    assert len(unexpected) == 1
    # an entry whose leak is gone is stale
    assert _triage({}, allow) == ([], ["recipes/x/recipe.yaml @ outputs[6].tests[0]"])
