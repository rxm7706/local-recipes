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

# One entry per file that may still carry a leak, each naming the story that
# removes it. An entry whose file no longer offends fails the test, so the
# allowlist cannot outlive its reason.
SENTINEL_ALLOWLIST: dict[str, str] = {
    "recipes/ctng-compilers/recipe.yaml": (
        "mason Story 22.3: the repaired file hits rattler-build 0.76.1's "
        "'Cycle detected in recipe outputs'; split from Story 22.1 by operator "
        "ruling 2026-10-09"
    ),
}


def _sentinel_findings(tree: object, where: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(tree, dict):
        for key, value in tree.items():
            here = f"{where}.{key}" if where else str(key)
            if not isinstance(key, str):
                found.append(f"{here}: non-string key {key!r} ({type(key).__name__})")
            elif _OBJECT_REPR_RE.match(key):
                found.append(f"{where or '<root>'}: object-repr key {key!r}")
            found.extend(_sentinel_findings(value, here))
    elif isinstance(tree, list):
        for i, item in enumerate(tree):
            found.extend(_sentinel_findings(item, f"{where}[{i}]"))
    elif isinstance(tree, str) and _OBJECT_REPR_RE.match(tree):
        found.append(f"{where}: object-repr value {tree!r}")
    return found


def _scan_for_sentinels(paths: list[Path], root: Path) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    for p in paths:
        try:
            tree = yaml.safe_load(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 -- parse failures belong to test_all_recipe_yaml_parse
            continue
        found = _sentinel_findings(tree)
        if found:
            hits[p.relative_to(root).as_posix()] = found
    return hits


def test_no_crm_sentinel_keys_in_recipe_yaml() -> None:
    hits = _scan_for_sentinels(_recipe_files(), REPO_ROOT)
    unexpected = {f: v for f, v in hits.items() if f not in SENTINEL_ALLOWLIST}
    stale = sorted(set(SENTINEL_ALLOWLIST) - set(hits))
    assert not unexpected, (
        "conda-recipe-manager SentinelType leak or other object-repr / non-string "
        "key (G121); repair by hand against the sibling meta.yaml:\n"
        + "\n".join(f"{f}: {'; '.join(v)}" for f, v in sorted(unexpected.items()))
    )
    assert not stale, (
        "allowlisted file(s) no longer carry a leak; remove the entry:\n" + "\n".join(stale)
    )


def test_sentinel_scan_reds_a_planted_key(tmp_path: Path) -> None:
    clean = (
        "schema_version: 1\n"
        "package:\n  name: demo\n  version: '1.0'\n"
        "about:\n  description: prose naming <conda_recipe_manager.types.SentinelType object at 0x1> is fine\n"
    )
    planted = clean + (
        "tests:\n"
        "  - <conda_recipe_manager.types.SentinelType object at 0x7f00deadbeef>:\n"
        "      requirements:\n        run:\n          - pip\n"
    )
    (tmp_path / "recipes" / "clean").mkdir(parents=True)
    (tmp_path / "recipes" / "planted").mkdir(parents=True)
    (tmp_path / "recipes" / "clean" / "recipe.yaml").write_text(clean)
    (tmp_path / "recipes" / "planted" / "recipe.yaml").write_text(planted)
    (tmp_path / "recipes" / "intkey").mkdir(parents=True)
    (tmp_path / "recipes" / "intkey" / "recipe.yaml").write_text(clean + "extra:\n  1: one\n")
    hits = _scan_for_sentinels(sorted((tmp_path / "recipes").glob("*/recipe.yaml")), tmp_path)
    assert set(hits) == {"recipes/planted/recipe.yaml", "recipes/intkey/recipe.yaml"}
    assert "object-repr key" in hits["recipes/planted/recipe.yaml"][0]
    assert "non-string key" in hits["recipes/intkey/recipe.yaml"][0]
