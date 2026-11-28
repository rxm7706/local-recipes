"""The package sources the guild image ships hold no secret-shaped line (steward Story 118.10,
spec-pyforge-steward CAP-129 and CAP-178).

The guild image's build gate (``scripts/container-gates secrets-scan``, run by the ``Containerfile``) scans ``/pyforge``
with ``steward keys audit --secrets``, and the ``guild-container`` jobs run only on a push to ``main``. So a shape added
to the pattern table, or a secret-shaped line added to a package's source, reds ``main`` with no pull request seeing
it: Story 118.9's ``hetzner-api-token`` shape matched six lines of django-pyforge's test keypair, and every push to
``main`` from PR #2425 on failed both ``guild-container`` jobs. This file scans, with the same table, every tracked file
under a package's ``src/`` (the image ships them; ``.dockerignore`` drops ``**/tests/``). It runs in the Detectors
workflow's scripts suite, which runs on every pull request.
"""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path, PurePosixPath

import pytest

keys = pytest.importorskip("pyforge.steward.keys")

ROOT = Path(__file__).resolve().parents[2]
PACKAGES = "src/shared/packages"
GOLDEN = "src/shared/packages/django-pyforge/src/django_pyforge/assertion/golden.py"


def shipped_package_sources() -> list[str]:
    """Every tracked file under `src/shared/packages/<package>/src/`, but those in a `tests` directory."""
    listing = subprocess.run(
        ["git", "ls-files", "-z", "--", PACKAGES], cwd=ROOT, capture_output=True, check=True
    ).stdout.decode("utf-8")
    shipped = []
    for rel in listing.split("\0"):
        parts = PurePosixPath(rel).parts
        if len(parts) > 5 and parts[4] == "src" and "tests" not in parts:
            shipped.append(rel)
    return shipped


def test_the_package_sources_the_guild_image_ships_scan_clean() -> None:
    shipped = shipped_package_sources()
    # The scope is the image's: the keypair module is shipped, and a test directory is not.
    assert GOLDEN in shipped
    assert not [rel for rel in shipped if "/tests/" in rel]
    findings = [finding.message for rel in shipped for finding in keys.scan_file_for_secrets(ROOT / rel)]
    assert findings == []


def test_the_keypair_wrapped_at_64_a_line_reds_the_scan() -> None:
    """The rule fires: the keypair's base64 at 64 a line, its PEM layout, holds six Hetzner-shaped lines."""
    spec = importlib.util.spec_from_file_location("golden_under_test", ROOT / GOLDEN)
    assert spec is not None and spec.loader is not None
    golden = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(golden)
    at_64 = golden._GOLDEN_PRIVATE_BODY + golden._GOLDEN_PUBLIC_BODY
    findings = keys.scan_text_for_secrets(at_64, "golden-at-64")
    assert [finding.pattern_name for finding in findings] == ["hetzner-api-token"] * 6
