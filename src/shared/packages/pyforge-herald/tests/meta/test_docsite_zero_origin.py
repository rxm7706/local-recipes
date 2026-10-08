"""Story 31.3: the public docsite build loads no third-party font resources."""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path

from pyforge.herald import twins

REPO_ROOT = Path(__file__).resolve().parents[6]
BUILD = REPO_ROOT / "docsite" / "build.py"
README = REPO_ROOT / "docsite" / "README.md"
FONTS_DIR = REPO_ROOT / "docsite" / "assets" / "fonts"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def _parse_readme_checksums(readme: str) -> dict[str, str]:
    table: dict[str, str] = {}
    for line in readme.splitlines():
        match = re.match(r"^\| `assets/fonts/([^`]+)` \| .+ \| .+ \| `([a-f0-9]{64})` \|", line)
        if match:
            table[match.group(1)] = match.group(2)
    return table


def test_docsite_build_has_zero_external_origins(tmp_path: Path) -> None:
    out = tmp_path / "site"
    proc = subprocess.run(
        [sys.executable, str(BUILD), "--out", str(out)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout

    html_pages = list(out.rglob("*.html"))
    assert len(html_pages) >= 45, f"expected at least 45 HTML pages, got {len(html_pages)}"

    findings = twins.scan_tree(out)
    assert not findings, "\n".join(
        f"{f.path.relative_to(out)}: {f.origin}" for f in findings[:20]
    )


def test_vendored_font_files_match_readme_sha256() -> None:
    readme = README.read_text(encoding="utf-8")
    expected = _parse_readme_checksums(readme)
    assert expected, "docsite/README.md must list vendored font sha256 rows"
    for name, want in expected.items():
        path = FONTS_DIR / name
        assert path.is_file(), name
        assert _sha256(path) == want, name


def test_every_font_file_in_readme_table() -> None:
    readme = README.read_text(encoding="utf-8")
    expected = _parse_readme_checksums(readme)
    on_disk = {p.name for p in FONTS_DIR.iterdir() if p.is_file()}
    missing = on_disk - set(expected)
    assert not missing, f"README missing rows for: {sorted(missing)}"


def test_ofl_sidecars_present() -> None:
    for name in (
        "OFL-big-shoulders-display.txt",
        "OFL-ibm-plex-sans.txt",
        "OFL-ibm-plex-mono.txt",
        "OFL-archivo.txt",
        "OFL-archivo-expanded.txt",
    ):
        path = FONTS_DIR / name
        assert path.is_file() and path.stat().st_size > 100, name
        assert "SIL OPEN FONT LICENSE" in path.read_text(encoding="utf-8").upper()
