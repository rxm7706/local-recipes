"""Integration oracle — scoped ``pixi.lock`` extraction vs env package list (Story 12.2)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from pyforge.warden.discovery import PIXI_LOCK_KIND
from pyforge.warden.extract.lockfiles import PixiLockExtractor
from pyforge.warden.models import ScannedManifest
from pyforge.warden.routing import DefaultRouter

_REPO_ROOT = Path(__file__).resolve().parents[6]
_ROOT_PIXI_LOCK = _REPO_ROOT / "pixi.lock"
_ENVIRONMENT = "python-agent-platform"
_PLATFORM = "linux-64"
_MANIFEST = ScannedManifest(path="pixi.lock", kind=PIXI_LOCK_KIND)
_CONDA_BASENAME_RE = re.compile(r"^(.+)-([^-]+)-[^-]+\.(?:conda|tar\.bz2)$")
_CONDA_SOURCE_RE = re.compile(r"^([^\[]+)\[([^\]]+)\]\s*@\s*.+$")


def _expected_identities_from_lock(document: object) -> set[tuple[str, str | None]]:
    assert isinstance(document, dict)
    env_block = document["environments"][_ENVIRONMENT]
    entries = env_block["packages"][_PLATFORM]
    identities: set[tuple[str, str | None]] = set()
    for entry in entries:
        assert isinstance(entry, dict)
        if "conda" in entry:
            url = entry["conda"]
            basename = url.rsplit("/", 1)[-1]
            match = _CONDA_BASENAME_RE.match(basename)
            assert match is not None, url
            identities.add((match.group(1), match.group(2)))
        elif "conda_source" in entry:
            value = entry["conda_source"]
            match = _CONDA_SOURCE_RE.match(value)
            assert match is not None, value
            identities.add((match.group(1), match.group(2)))
        elif "pypi" in entry:
            name = entry.get("name")
            version = entry.get("version")
            if name:
                identities.add((name, version))
    return identities


@pytest.mark.skipif(
    not _ROOT_PIXI_LOCK.is_file(),
    reason="repo root pixi.lock not present in this checkout",
)
def test_root_pixi_lock_python_agent_platform_linux64_matches_env_list():
    document = yaml.safe_load(_ROOT_PIXI_LOCK.read_text(encoding="utf-8"))
    expected = _expected_identities_from_lock(document)
    extractor = PixiLockExtractor(DefaultRouter(), environment=_ENVIRONMENT, platform=_PLATFORM)
    components = extractor.extract(_ROOT_PIXI_LOCK, _MANIFEST)
    actual = {(c.name, c.version) for c in components}
    assert actual == expected
    assert len(actual) == len(expected)
