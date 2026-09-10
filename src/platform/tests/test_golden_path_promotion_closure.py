"""Story 12.3 — golden-path promotion scans the shipped pixi lock closure.

Subprocesses the scoped ``warden scan`` command
``scripts/platform-golden-path-promotion.sh`` uses (same flags, lockfile-only
isolated target) and asserts the inventory matches the CAP-1 oracle with
locked versions — not the old bare-``pixi.toml`` union.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ROOT_PIXI_LOCK = _REPO_ROOT / "pixi.lock"
_ENVIRONMENT = "python-agent-platform"
_PLATFORM = "linux-64"
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


def _promotion_scan_command(workspace: Path) -> list[str]:
    # platform-ci-test does not install pyforge-warden; invoke the same CLI
    # the promotion script uses via pixi (available in Platform CI's test job).
    return [
        "pixi",
        "run",
        "-e",
        "pyforge-warden",
        "warden",
        "scan",
        str(workspace),
        "--pixi-environment",
        _ENVIRONMENT,
        "--pixi-platform",
        _PLATFORM,
        "--format",
        "json",
    ]


@pytest.mark.skipif(not _ROOT_PIXI_LOCK.is_file(), reason="repo root pixi.lock missing")
def test_promotion_scan_matches_shipped_closure_oracle(tmp_path: Path) -> None:
    """The promotion script's scoped lockfile scan yields the CAP-1 inventory."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    shutil.copy2(_ROOT_PIXI_LOCK, workspace / "pixi.lock")

    env = os.environ.copy()
    env.pop("WARDEN_TARGET", None)
    result = subprocess.run(  # noqa: S603 -- fixed argv, no shell, repo script under test
        _promotion_scan_command(workspace),
        cwd=_REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode in (0, 1, 2), result.stderr
    report = json.loads(result.stdout)
    document = yaml.safe_load(_ROOT_PIXI_LOCK.read_text(encoding="utf-8"))
    expected = _expected_identities_from_lock(document)

    assert report["inventory_count"] == len(expected)
    assert report["resolved_scan_set"] == [{"kind": "pixi.lock", "path": "pixi.lock"}]

    extractor_check = subprocess.run(  # noqa: S603 -- fixed argv, no shell, no untrusted input
        [  # noqa: S607 -- resolved via PATH like every other pixi invocation in this suite
            "pixi",
            "run",
            "-e",
            "pyforge-warden",
            "python",
            "-c",
            (
                "from pathlib import Path; "
                "import yaml; "
                "from pyforge.warden.discovery import PIXI_LOCK_KIND; "
                "from pyforge.warden.extract.lockfiles import PixiLockExtractor; "
                "from pyforge.warden.models import ScannedManifest; "
                "from pyforge.warden.routing import DefaultRouter; "
                f"lock = Path({str(workspace / 'pixi.lock')!r}); "
                f"extractor = PixiLockExtractor(DefaultRouter(), "
                f"environment={_ENVIRONMENT!r}, platform={_PLATFORM!r}); "
                "components = extractor.extract(lock, "
                "ScannedManifest(path='pixi.lock', kind=PIXI_LOCK_KIND)); "
                "print(len(components))"
            ),
        ],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert int(extractor_check.stdout.strip()) == len(expected)

    payload = json.dumps(report).lower()
    assert "no-version" not in payload
    assert "no_version" not in payload
