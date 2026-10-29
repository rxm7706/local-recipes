"""Steward Story 109.3, its review of 2026-10-28 (rows 6, 8 and 9): the marketplace mount is a pure function the build
calls under the exported flag.

``docs-site/src/lib/marketplace.ts`` decides what ``populate-public`` writes under ``marketplace/``: every file of the
generated ``site/``, ``marketplace.json`` rewritten to the deploying host, and of each skill folder only the shipped
files. The build reads the flag as ``PYFORGE_MARKETPLACE_PAGES`` through ``src/lib/flags.ts``, the one reader; the
TypeScript reader of the flag tree that defaulted every deploy to ``dev`` is gone. Needs only node.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from pages_astro import DOCS_SITE, needs_node, ts, write

MARKETPLACE_TS = DOCS_SITE / "src" / "lib" / "marketplace.ts"
FLAGS_TS = DOCS_SITE / "src" / "lib" / "flags.ts"
POPULATE = DOCS_SITE / "scripts" / "populate-public.mts"
PAGES = DOCS_SITE / "scripts" / "pages.mts"
PUBLIC_GIT = "https://github.com/rxm7706/local-recipes.git"
MOUNT = "return m.marketplaceMount(inp.dir, inp.env).map((f) => [f.rel, f.data.toString('utf8')]);"

pytestmark = needs_node


def plant(root: Path) -> Path:
    write(root / "site/index.html", "<p>index</p>")
    write(root / "site/listings.json", "{}\n")
    write(root / "site/marketplace.json", f'{{"url": "{PUBLIC_GIT}"}}\n')
    write(root / "site/skills/mason/environment.html", "<p>card</p>")
    skill = root / "skills/mason/environment"
    write(skill / "SKILL.md", "# skill\n")
    write(skill / "steps.md", "# steps\n")
    write(skill / "listing.yaml", "id: mason/environment\n")
    write(skill / "references/recreate.md", "# ref\n")
    write(skill / "references/deep/more.md", "# more\n")
    write(skill / ".DS_Store", "x")
    write(skill / "__pycache__/x.pyc", "x")
    write(skill / "notes.txt", "a stray file")
    write(skill / "references/.hidden", "x")
    write(root / "skills/README.md", "not a skill folder\n")
    write(root / "README.md", "not mounted\n")
    write(root / "index.yaml", "not mounted\n")
    # loop 2, row 23: a symlink (file or directory, dangling or not) never mounts; a folder outside the slug
    # grammar never mounts
    write(root.parent / "outside.txt", "secret\n")
    (skill / "references" / "link.md").symlink_to(root.parent / "outside.txt")
    (skill / "references" / "dangling.md").symlink_to(root.parent / "missing.txt")
    (skill / "references" / "linked-dir").symlink_to(root.parent)
    write(root / "skills/Mason/Env/SKILL.md", "# bad case\n")
    write(root / "skills/.hidden/slug/SKILL.md", "# dot scope\n")
    write(root / "skills/mason/environment.bak/SKILL.md", "# bad slug\n")
    # loop 3, row 48: a references/ file outside the text suffixes never mounts
    (skill / "references" / "pic.png").write_bytes(b"\x89PNG")
    write(skill / "references" / "tool.whl", "x")
    return root


def test_the_mount_is_the_site_plus_the_shipped_skill_files_in_order(tmp_path: Path) -> None:
    root = plant(tmp_path / "marketplace")
    mounted = ts(MARKETPLACE_TS, MOUNT, dir=str(root), env={})
    assert [rel for rel, _ in mounted] == [
        "index.html",
        "listings.json",
        "marketplace.json",
        "skills/mason/environment.html",
        "skills/mason/environment/SKILL.md",
        "skills/mason/environment/listing.yaml",
        "skills/mason/environment/references/deep/more.md",
        "skills/mason/environment/references/recreate.md",
        "skills/mason/environment/steps.md",
    ]
    assert dict(mounted)["skills/mason/environment/SKILL.md"] == "# skill\n"
    assert dict(mounted)["marketplace.json"] == f'{{"url": "{PUBLIC_GIT}"}}\n'  # no host named: no rewrite


def test_an_absent_or_empty_tree_mounts_nothing(tmp_path: Path) -> None:
    assert ts(MARKETPLACE_TS, MOUNT, dir=str(tmp_path / "missing"), env={}) == []
    (tmp_path / "empty" / "site").mkdir(parents=True)
    assert ts(MARKETPLACE_TS, MOUNT, dir=str(tmp_path / "empty"), env={}) == []


@pytest.mark.parametrize(
    ("env", "url"),
    [
        (
            {"GITHUB_SERVER_URL": "https://ghe.example", "GITHUB_REPOSITORY": "org/local-recipes"},
            "https://ghe.example/org/local-recipes.git",
        ),
        (
            {"GITHUB_SERVER_URL": "https://ghe.example/", "GITHUB_REPOSITORY": "org/local-recipes"},
            "https://ghe.example/org/local-recipes.git",
        ),
        ({"GITHUB_SERVER_URL": "https://github.com", "GITHUB_REPOSITORY": "rxm7706/local-recipes"}, PUBLIC_GIT),
        ({"GITHUB_SERVER_URL": "https://ghe.example"}, PUBLIC_GIT),  # no repository: unchanged
        ({"GITHUB_REPOSITORY": "org/local-recipes"}, PUBLIC_GIT),  # no server: unchanged
    ],
)
def test_marketplace_json_is_rewritten_to_the_deploying_host(tmp_path: Path, env: dict, url: str) -> None:
    root = plant(tmp_path / "marketplace")
    mounted = dict(ts(MARKETPLACE_TS, MOUNT, dir=str(root), env=env))
    assert mounted["marketplace.json"] == f'{{"url": "{url}"}}\n'
    # the cards and the skill files are never rewritten
    assert mounted["skills/mason/environment.html"] == "<p>card</p>"
    rewritten = ts(
        MARKETPLACE_TS,
        "return m.rewriteMarketplaceGitUrl(inp.text, inp.env);",
        text=f"a {PUBLIC_GIT} b {PUBLIC_GIT}",
        env=env,
    )
    assert rewritten == f"a {url} b {url}"


@pytest.mark.parametrize(
    ("rel", "shipped"),
    [
        ("SKILL.md", True),
        ("steps.md", True),
        ("listing.yaml", True),
        ("references/a.md", True),
        ("references/deep/b.md", True),
        ("references/a.txt", True),
        ("references/a.yaml", True),
        ("references/a.yml", True),
        ("references/a.json", True),
        ("references/A.MD", True),  # the suffix is matched case-insensitively, as the validator does
        ("references/pic.png", False),  # loop 3, row 48: the validator's text-suffix rule
        ("references/tool.whl", False),
        ("references/deep/script.sh", False),
        ("references/noext", False),
        ("notes.txt", False),
        (".DS_Store", False),
        ("references/.hidden", False),
        ("references/", False),
        ("__pycache__/x.pyc", False),
        ("skill.md", False),
        ("", False),
    ],
)
def test_only_the_shipped_skill_files_are_mounted(rel: str, shipped: bool) -> None:
    assert ts(MARKETPLACE_TS, "return m.isShippedSkillFile(inp.rel);", rel=rel) is shipped


def test_the_build_reads_the_flag_through_flags_ts_and_the_tree_reader_is_gone() -> None:
    """The second reader (``scripts/marketplace-pages.mts``, which parsed ``flags.json`` in TypeScript and read
    ``dev`` when ``PYFORGE_ENVIRONMENT`` was unset) is deleted; the mount and the check read the exported variable."""
    assert not (DOCS_SITE / "scripts" / "marketplace-pages.mts").exists()
    flags = FLAGS_TS.read_text(encoding="utf-8")
    assert "export function marketplacePages(): boolean {\n  return envFlagOn('PYFORGE_MARKETPLACE_PAGES');" in flags
    populate = POPULATE.read_text(encoding="utf-8")
    assert "import { marketplacePages } from '../src/lib/flags.ts';" in populate
    assert re.search(r"if \(marketplacePages\(\)\) \{\s*for \(const file of marketplaceMount\(", populate)
    assert "flags.json" not in populate and "flag-overlays.json" not in populate
    pages = PAGES.read_text(encoding="utf-8")
    assert "const marketplaceOn = envFlagOn('PYFORGE_MARKETPLACE_PAGES', env);" in pages
    assert "marketplaceManifestFindings(read('marketplace/marketplace.json'), has)" in pages
    assert "flags.json" not in pages
    for source in (DOCS_SITE / "src" / "lib").glob("*.ts"):
        text = source.read_text(encoding="utf-8")
        assert "src/platform/config/flags.json" not in text, source.name


def test_the_mounts_allowlist_and_slug_grammar_are_the_validators() -> None:
    """Loop 2, row 23; loop 3, row 48: one allowlist, one slug grammar, one suffix set, two caps and one kind map,
    shared with ``pyforge.steward.marketplace_pages``."""
    ts_text = MARKETPLACE_TS.read_text(encoding="utf-8")
    py = (DOCS_SITE.parent / "src/shared/packages/pyforge-steward/src/pyforge/steward/marketplace_pages.py").read_text(
        encoding="utf-8"
    )
    ts_files = re.search(r"SKILL_FILES: readonly string\[\] = \[([^\]]+)\]", ts_text).group(1)
    py_files = re.search(r"SKILL_FILES = \(([^)]+)\)", py).group(1)
    assert [n.strip().strip("'") for n in ts_files.split(",")] == [n.strip().strip('"') for n in py_files.split(",")]
    assert re.search(r"export const SLUG = /\^\[a-z0-9\]\[a-z0-9-\]\*\$/;", ts_text)
    assert 'SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")' in py
    assert "SLUG.match(" not in py  # loop 3, row 57: matched whole, as the TypeScript regex is
    assert (
        re.search(r"export const SKILL_REFERENCES_DIR = 'references';", ts_text)
        and 'REFERENCES_DIR = "references"' in py
    )
    assert (
        "export const SCHEMA_ID = 'pyforge.bmad-marketplace/v1';" in ts_text
        and 'SCHEMA_ID = "pyforge.bmad-marketplace/v1"' in py
    )
    ts_suffixes = re.search(r"SHIPPED_TEXT_SUFFIXES: readonly string\[\] = \[([^\]]+)\]", ts_text).group(1)
    py_suffixes = re.search(r"SHIPPED_TEXT_SUFFIXES = frozenset\(\{([^}]+)\}\)", py).group(1)
    assert sorted(n.strip().strip("'") for n in ts_suffixes.split(",")) == sorted(
        n.strip().strip('"') for n in py_suffixes.split(",")
    )
    assert "export const MAX_SHIPPED_FILE_BYTES = 1048576;" in ts_text and "MAX_SHIPPED_FILE_BYTES = 1_048_576" in py
    assert (
        "export const MAX_SHIPPED_FOLDER_BYTES = 4194304;" in ts_text
        and "MAX_SHIPPED_FOLDER_BYTES = 4 * 1_048_576" in py
    )
    assert (
        "KIND_DIRS: Readonly<Record<string, string>> = { skill: 'skills', module: 'modules', agent: 'agents', bundle: 'bundles' };"
        in ts_text
    )
    assert (
        'KIND_DIRS: dict[str, str] = {"skill": "skills", "module": "modules", "agent": "agents", "bundle": "bundles"}'
        in py
    )


def test_the_mount_fails_the_build_on_a_file_or_folder_over_its_cap(tmp_path: Path) -> None:
    """Loop 3, row 48: the validator's caps hold at the mount too; a breach throws, naming it, rather than ships."""
    root = plant(tmp_path / "marketplace")
    skill = root / "skills/mason/environment"
    (skill / "references" / "big.md").write_bytes(b"x" * (1_048_576 + 1))
    thrown = ts(MARKETPLACE_TS, MOUNT, dir=str(root), env={})
    assert (
        isinstance(thrown, dict) and "skills/mason/environment/references/big.md is 1048577 bytes" in thrown["message"]
    )
    (skill / "references" / "big.md").unlink()
    for n in range(5):
        (skill / "references" / f"{n}.md").write_bytes(b"x" * (1_048_576 - 1))
    thrown = ts(MARKETPLACE_TS, MOUNT, dir=str(root), env={})
    assert isinstance(thrown, dict) and "skills/mason/environment ships over 4194304 bytes" in thrown["message"]
