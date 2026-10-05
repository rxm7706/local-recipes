"""Story 27.1: structural oracle for the in-place Starlight docs shelf."""

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


def test_docs_site_symlink_targets_repo_docs() -> None:
    root = _repo_root()
    link = root / "docs-site" / "src" / "content" / "docs"
    assert link.is_symlink()
    target = link.resolve()
    assert target == (root / "docs").resolve()
    assert (target / "map.yaml").is_file()


def test_nodejs_pin_matches_feature_python() -> None:
    root = _repo_root()
    pixi = tomllib.loads((root / "pixi.toml").read_text(encoding="utf-8"))
    site_node = pixi["feature"]["site"]["dependencies"]["nodejs"]
    python_node = pixi["feature"]["python"]["dependencies"]["nodejs"]
    assert site_node == python_node


def test_docs_site_pixi_tasks() -> None:
    root = _repo_root()
    pixi = tomllib.loads((root / "pixi.toml").read_text(encoding="utf-8"))
    install = pixi["feature"]["site"]["tasks"]["docs-site-install"]
    build = pixi["feature"]["site"]["tasks"]["docs-site-build"]
    assert install["cmd"] == "npm ci"
    assert install["cwd"] == "docs-site"
    assert build["cmd"] == "npm run build"
    assert build["cwd"] == "docs-site"
    assert build["depends-on"] == ["docs-site-install"]


def test_nvmrc_major_within_nodejs_pin() -> None:
    root = _repo_root()
    major = int((root / "docs-site" / ".nvmrc").read_text(encoding="utf-8").strip())
    pixi = tomllib.loads((root / "pixi.toml").read_text(encoding="utf-8"))
    pin: str = pixi["feature"]["python"]["dependencies"]["nodejs"]
    assert pin.startswith(">=")
    floor = int(pin.split(",")[0].removeprefix(">=").split(".")[0])
    assert major >= floor


def test_landing_and_404_pages_exist() -> None:
    root = _repo_root()
    assert (root / "docs" / "index.md").is_file()
    assert (root / "docs" / "404.md").is_file()


def test_vendored_files_match_readme_sha256() -> None:
    root = _repo_root()
    readme = (root / "docs-site" / "README.md").read_text(encoding="utf-8")
    expected = _parse_readme_checksums(readme)
    assert expected, "docs-site/README.md must list vendored sha256 rows"
    for rel, want in expected.items():
        path = root / "docs-site" / rel
        assert path.is_file(), rel
        assert _sha256(path) == want, rel


def test_gitignore_excludes_docs_site_artifacts() -> None:
    root = _repo_root()
    ignore = (root / ".gitignore").read_text(encoding="utf-8")
    for line in ("docs-site/node_modules/", "docs-site/build/", "docs-site/.astro/"):
        assert line in ignore
