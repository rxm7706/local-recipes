"""Story 31.1: the Pages artifact builds for the deploying host (CAP-56).

Story 42.3 (CAP-60): ``actions/configure-pages`` is authoritative on every host, so the build takes
``PAGES_HOST_BASE_URL`` (joined with ``PAGES_HOST_BASE_PATH``; an empty base path is a root-hosted site) whenever a
base URL is set and the public github.io URL otherwise, with no flag. Since Story 43.7 the resolver is
``docs-site/scripts/pages.mts`` (``resolveSiteUrl``, run by ``pages-build``); the second-host flag, its reader
(``pyforge/herald/pages_host.py``) and its workflow exporter are gone. This file is the absence test, so it names the
retired key outright; 42.3's AC5 grep excludes it by path (42.3's review). ``pages-check``'s host rules (a load from
another origin, a link to the public host from a second host) are ``test_pages_artifact.py``'s.
"""

from __future__ import annotations

import json
import re

import pytest
from pages_astro import DOCS_SITE, PAGES_MTS, REPO_ROOT, needs_node, ts

#: The retired key (AC4). AC5's tracked-file grep excludes this file by path.
RETIRED_FLAG = "pyforge.herald.pages_second_host"


def test_no_flag_read_in_the_generator_and_the_reader_is_gone() -> None:
    """AC3: nothing in the one generator reads a host flag, or any flag but through ``src/lib/flags.ts``."""
    pattern = re.compile("pages_second_host|PYFORGE_PAGES_APPLY_HOST|read_boolean")
    hits = [
        f"{path.relative_to(REPO_ROOT)}:{number}"
        for top in (DOCS_SITE / "src", DOCS_SITE / "scripts")
        for path in sorted(top.rglob("*"))
        if path.is_file() and "content" not in path.relative_to(DOCS_SITE).parts
        for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1)
        if pattern.search(line)
    ]
    assert hits == []
    assert not (REPO_ROOT / "src/shared/packages/pyforge-herald/src/pyforge/herald/pages_host.py").exists()


def test_the_retired_key_is_gone_from_the_tree_and_every_overlay() -> None:
    """AC4."""
    tree = json.loads((REPO_ROOT / "src/platform/config/flags.json").read_text(encoding="utf-8"))
    assert RETIRED_FLAG not in tree["flags"]
    overlays = json.loads((REPO_ROOT / "src/platform/config/flag-overlays.json").read_text(encoding="utf-8"))
    for environment, values in overlays.items():
        assert RETIRED_FLAG not in values, environment
    inventory = (REPO_ROOT / "docs/governance/flag-inventory/pyforge-herald.md").read_text(encoding="utf-8")
    assert "pages_second_host" not in inventory


@needs_node
@pytest.mark.parametrize(
    ("env", "expected"),
    [
        ({}, "https://rxm7706.github.io/local-recipes"),
        ({"GITHUB_REPOSITORY": "acme/site"}, "https://acme.github.io/site"),
        ({"PAGES_HOST_BASE_URL": "https://ghe.example.com/pages/acme/site"}, "https://ghe.example.com/pages/acme/site"),
        ({"PAGES_HOST_BASE_URL": "https://docs.example.com", "PAGES_HOST_BASE_PATH": ""}, "https://docs.example.com"),
        ({"PAGES_HOST_BASE_URL": "https://docs.example.com", "PAGES_HOST_BASE_PATH": "/"}, "https://docs.example.com"),
        (
            {"PAGES_HOST_BASE_URL": "https://ghe.example.com", "PAGES_HOST_BASE_PATH": "/pages/acme/site/"},
            "https://ghe.example.com/pages/acme/site",
        ),
        (
            {"PAGES_HOST_BASE_URL": "https://acme.github.io/site", "PAGES_HOST_BASE_PATH": "/site"},
            "https://acme.github.io/site",
        ),
        ({"PAGES_HOST_BASE_PATH": "/ignored"}, "https://rxm7706.github.io/local-recipes"),
    ],
)
def test_42_3_configure_pages_decides_the_site_url(env: dict[str, str], expected: str) -> None:
    assert ts(PAGES_MTS, "return m.resolveSiteUrl(inp.env);", env=env) == expected


def test_flags_json_carries_ci_surfaces_tile() -> None:
    tree = json.loads((REPO_ROOT / "src/platform/config/flags.json").read_text(encoding="utf-8"))
    flag = tree["flags"]["pyforge.herald.ci_surfaces_tile"]
    assert flag["defaultVariant"] == "off"
    assert flag["metadata"]["story"].startswith("39-1-")
