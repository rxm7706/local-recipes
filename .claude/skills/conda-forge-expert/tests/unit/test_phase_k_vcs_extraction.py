"""Unit tests for Phase K's `_extract_vcs_repo` URL parser.

Regression cases originate from the 2026-05-12 `atlas-phase K` run, which
surfaced `InvalidURL` errors on a handful of ropensci-style feedstocks
whose `about.dev_url` / `about.repository` fields held multi-URL strings
(comma-joined, space-joined, or with a parenthetical annotation). The
pre-fix regex accepted whitespace and commas in the captured repo group,
so a value like `'https://github.com/eheinzen/arsenal, https://example/'`
captured `repo='arsenal, https:'`.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"


def _load(name: str):
    path = _SCRIPTS_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    if str(_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_DIR))
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def atlas_mod():
    return _load("conda_forge_atlas")


# Positive cases — clean single-URL inputs that must keep working.

@pytest.mark.parametrize("url, expected", [
    ("https://github.com/conda-forge/numpy-feedstock",
     ("github", "conda-forge", "numpy-feedstock")),
    ("https://github.com/prefix-dev/pixi",
     ("github", "prefix-dev", "pixi")),
    ("https://codeberg.org/forgejo/forgejo",
     ("codeberg", "forgejo", "forgejo")),
    ("https://gitlab.com/gitlab-org/gitlab",
     ("gitlab", "gitlab-org/gitlab", "gitlab")),
    ("https://gitlab.com/fdroid/fdroidclient",
     ("gitlab", "fdroid/fdroidclient", "fdroidclient")),
])
def test_extract_vcs_repo_clean(atlas_mod, url, expected):
    assert atlas_mod._extract_vcs_repo(url) == expected


# Regression cases — recipe fields holding multi-URL strings or
# annotations. The parser must capture only the first clean repo and
# stop at the first whitespace / comma / paren.

@pytest.mark.parametrize("url, expected", [
    # Comma-joined URLs (r-arsenal pattern)
    ("https://github.com/eheinzen/arsenal, https://example.org/",
     ("github", "eheinzen", "arsenal")),
    # Space-joined URLs (r-azureauth pattern)
    ("https://github.com/Azure/AzureAuth https://other-url",
     ("github", "Azure", "AzureAuth")),
    # Parenthetical annotation (r-aricode pattern)
    ("https://github.com/jchiquet/aricode (dev version)",
     ("github", "jchiquet", "aricode")),
    # Codeberg with parenthetical
    ("https://codeberg.org/forgejo/forgejo (mirror)",
     ("codeberg", "forgejo", "forgejo")),
])
def test_extract_vcs_repo_multi_url_inputs(atlas_mod, url, expected):
    assert atlas_mod._extract_vcs_repo(url) == expected


# Inputs where the *owner* itself is malformed should yield None rather
# than a bogus capture. r-ascii's `'https://github.com/ascii/, http:'`
# is the canonical case — the path after `ascii/` has no real repo.

@pytest.mark.parametrize("url", [
    "https://github.com/ascii/, http:",
    "https://github.com/ascii/ http:",
    "https://github.com/owner/, other",
])
def test_extract_vcs_repo_empty_repo_segment_yields_none(atlas_mod, url):
    assert atlas_mod._extract_vcs_repo(url) is None


# Iteration over multiple URL candidates still picks the first valid one.

def test_extract_vcs_repo_multi_arg_first_match_wins(atlas_mod):
    result = atlas_mod._extract_vcs_repo(
        None,
        "not-a-url-at-all",
        "https://github.com/prefix-dev/pixi",
        "https://github.com/should-not-reach/here",
    )
    assert result == ("github", "prefix-dev", "pixi")


def test_extract_vcs_repo_no_match_returns_none(atlas_mod):
    assert atlas_mod._extract_vcs_repo(
        None,
        "",
        "https://example.com/not-a-vcs-host",
    ) is None
