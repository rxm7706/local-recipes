"""Story 27.4: docs-site link/sidebar validators wired as pixi tasks and CI legs."""

from __future__ import annotations

import hashlib
import re
import tomllib
from pathlib import Path


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (
            candidate / "src" / "shared" / "packages" / "pyforge-herald"
        ).is_dir():
            return candidate
    raise AssertionError("could not locate repo root")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _parse_readme_checksums(readme: str) -> dict[str, str]:
    table: dict[str, str] = {}
    for line in readme.splitlines():
        match = re.match(r"^\| `([^`]+)` \| `([a-f0-9]{64})` \|", line)
        if match:
            table[match.group(1)] = match.group(2)
    return table


def test_docs_site_validate_pixi_tasks_registered() -> None:
    root = _repo_root()
    pixi = tomllib.loads((root / "pixi.toml").read_text(encoding="utf-8"))
    tasks = pixi["feature"]["site"]["tasks"]
    links = tasks["docs-site-validate-links"]
    sidebar = tasks["docs-site-validate-sidebar"]
    bundle = tasks["docs-site-validate"]
    assert links["cmd"] == "node docs-site/scripts/validate-doc-links.js"
    assert sidebar["cmd"] == "python docs-site/scripts/sidebar_from_map.py --check"
    assert sidebar["depends-on"] == ["docs-site-validate-sidebar-order"]
    assert bundle["depends-on"] == ["docs-site-validate-links", "docs-site-validate-sidebar"]


def test_docsite_check_runs_docs_site_validate() -> None:
    root = _repo_root()
    text = (root / ".github/workflows/docsite-check.yml").read_text(encoding="utf-8")
    assert "docs-site-validate" in text
    assert "pages-check" in text


def test_pr_preflight_carries_docs_site_validate_leg() -> None:
    root = _repo_root()
    pixi = tomllib.loads((root / "pixi.toml").read_text(encoding="utf-8"))
    preflight = pixi["feature"]["guild-tasks"]["tasks"]["pr-preflight"]
    legs = preflight["depends-on"]
    validate_legs = [
        leg for leg in legs if isinstance(leg, dict) and leg.get("task") == "docs-site-validate"
    ]
    assert validate_legs == [{"task": "docs-site-validate", "environment": "site"}]


def test_vendored_validators_match_readme_sha256() -> None:
    root = _repo_root()
    readme = (root / "docs-site" / "README.md").read_text(encoding="utf-8")
    expected = _parse_readme_checksums(readme)
    for name in ("scripts/validate-doc-links.js", "scripts/validate-sidebar-order.js"):
        assert name in expected
        path = root / "docs-site" / name
        assert _sha256(path) == expected[name], name
