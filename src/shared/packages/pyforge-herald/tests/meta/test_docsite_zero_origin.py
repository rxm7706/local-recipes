"""Story 31.3: the public docsite build loads no third-party font resources.

Story 43.4 (CAP-61): on the Astro path the faces come from @fontsource, the dossier's families and tokens match the
Jinja path's, and the theme follows the docs header's toggle -- the ``test_43_4_*`` tests."""

from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

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
    assert not findings, "\n".join(f"{f.path.relative_to(out)}: {f.origin}" for f in findings[:20])


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


# --- Story 43.4: fonts and theme come from one design system ---------------------------------------------------

DOCS_SITE = REPO_ROOT / "docs-site"
HERALD_CSS = DOCS_SITE / "src" / "styles" / "herald.css"
HERALD_FONTS_CSS = DOCS_SITE / "src" / "styles" / "herald-fonts.css"
JINJA_CSS = REPO_ROOT / "docsite" / "assets" / "_dossier.css"
JINJA_CHROME_CSS = REPO_ROOT / "docsite" / "assets" / "_site-chrome.css"
HERALD_PAGES_TS = DOCS_SITE / "src" / "lib" / "herald-pages.ts"
NODE = shutil.which("node")

_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_RULE = re.compile(r"([^{}@;]+)\{([^{}]*)\}")
_DECLARATION = re.compile(r"(?:^|;)\s*([\w-]+)\s*:\s*([^;]+)")


def _rules(css: str) -> list[tuple[str, dict[str, str]]]:
    """Each innermost rule as ``(selector, {property: value})``, whitespace and quote style normalized."""
    out = []
    for selector, body in _RULE.findall(_COMMENT.sub("", css)):
        declarations = {name.lower(): " ".join(value.split()) for name, value in _DECLARATION.findall(body)}
        out.append((" ".join(selector.replace('"', "'").split()), declarations))
    return out


def _families(css: str) -> dict[str, tuple[str, ...]]:
    """The font-family list each selector declares, quotes dropped."""
    return {
        selector: tuple(part.strip().strip("'\"") for part in decl["font-family"].split(","))
        for selector, decl in _rules(css)
        if "font-family" in decl
    }


def _tokens(css: str, selector: str) -> dict[str, str]:
    """The custom properties one selector's block defines."""
    blocks = [decl for sel, decl in _rules(css) if sel == selector]
    assert len(blocks) == 1, f"expected one {selector!r} block, found {len(blocks)}"
    return {name: value for name, value in blocks[0].items() if name.startswith("--")}


def test_43_4_ac2_the_astro_stylesheet_names_the_jinja_families() -> None:
    """AC2: the dossier's headings and body -- and every other rule of the Jinja stylesheets that names a family --
    resolve to the same font-family on the Astro path. The back-bar's rules are the reader pages' own inline style."""
    astro, jinja = _families(HERALD_CSS.read_text(encoding="utf-8")), _families(JINJA_CSS.read_text(encoding="utf-8"))
    assert astro["body"] == jinja["body"] == ("IBM Plex Sans", "system-ui", "-apple-system", "sans-serif")
    assert (
        astro["h1, h2, h3, h4"] == jinja["h1, h2, h3, h4"] == ("Big Shoulders Display", "IBM Plex Sans", "sans-serif")
    )
    chrome = _families(JINJA_CHROME_CSS.read_text(encoding="utf-8"))
    expected = {**jinja, **{sel: fam for sel, fam in chrome.items() if not sel.startswith(".ig-backbar")}}
    assert len(expected) > 20
    assert {sel: astro.get(sel) for sel in expected} == expected


def test_43_4_ac3_the_tokens_are_defined_light_and_under_starlights_dark_selector() -> None:
    """AC3: the shared stylesheet defines every dossier token under the light root and again under Starlight's
    ``[data-theme='dark']``, with the Jinja path's values, and the two blocks differ; there is no herald-only dark mode
    (no ``prefers-color-scheme`` block: the theme script resolves "auto" as Starlight's own does)."""
    css = HERALD_CSS.read_text(encoding="utf-8")
    jinja = JINJA_CSS.read_text(encoding="utf-8")
    light, dark = _tokens(css, ":root"), _tokens(css, ":root[data-theme='dark']")
    jinja_light, jinja_dark = _tokens(jinja, ":root"), _tokens(jinja, ":root[data-theme='dark']")
    assert len(jinja_light) > 30
    assert light == jinja_light
    assert dark == jinja_dark
    assert set(dark) == set(light) and dark != light
    assert "prefers-color-scheme" not in _COMMENT.sub("", css)


_THEME_PROBE = """
import { HERALD_CSP, THEME_SCRIPT } from %s;
process.stdout.write(JSON.stringify({ csp: HERALD_CSP, theme: THEME_SCRIPT }));
"""


@pytest.mark.skipif(NODE is None, reason="node is not on PATH")
def test_43_4_ac3_the_theme_follows_the_docs_toggle_and_the_csp_allows_it() -> None:
    """AC3: the herald pages read the docs header's toggle from Starlight's own store (``starlight-theme``) and set
    Starlight's ``data-theme`` -- no second toggle or store -- and the CSP allows that one inline script by hash."""
    done = subprocess.run(
        [
            NODE or "node",
            "--experimental-strip-types",
            "--input-type=module",
            "-e",
            _THEME_PROBE % json.dumps(HERALD_PAGES_TS.as_uri()),
        ],
        cwd=DOCS_SITE,
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    probe = json.loads(done.stdout)
    theme = probe["theme"]
    assert "localStorage.getItem('starlight-theme')" in theme
    assert "document.documentElement.dataset.theme=" in theme and "prefers-color-scheme: light" in theme
    digest = base64.b64encode(hashlib.sha256(theme.encode("utf-8")).digest()).decode("ascii")
    assert f"'sha256-{digest}'" in probe["csp"]
    provider = DOCS_SITE / "node_modules/@astrojs/starlight/dist/components/ThemeProvider.astro"
    if provider.is_file():  # the store is Starlight's: its provider reads the same key
        assert "localStorage.getItem('starlight-theme')" in provider.read_text(encoding="utf-8")


def test_43_4_ac4_the_astro_path_names_no_vendored_font() -> None:
    """AC4: ``grep -rn "assets/fonts" docs-site/src`` finds nothing, and the herald faces are imported from the
    @fontsource packages ``package.json`` lists, never a URL or a file under ``docsite/``."""
    hits = [
        f"{path.relative_to(REPO_ROOT)}:{n}"
        for path in sorted((DOCS_SITE / "src").rglob("*"))
        if path.is_file() and not path.is_symlink() and "content" not in path.relative_to(DOCS_SITE / "src").parts[:1]
        for n, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1)
        if "assets/fonts" in line
    ]
    assert hits == []
    fonts = _COMMENT.sub("", HERALD_FONTS_CSS.read_text(encoding="utf-8"))
    imports = re.findall(r"@import\s+'([^']+)';", fonts)
    urls = re.findall(r"url\(\s*'([^']+)'\s*\)", fonts)
    packages = {spec.split("/")[0] + "/" + spec.split("/")[1] for spec in [*imports, *urls]}
    manifest = json.loads((DOCS_SITE / "package.json").read_text(encoding="utf-8"))["devDependencies"]
    assert packages == {
        "@fontsource/big-shoulders-display",
        "@fontsource/ibm-plex-sans",
        "@fontsource/ibm-plex-mono",
        "@fontsource/archivo",
        "@fontsource-variable/archivo",
    }
    assert packages <= set(manifest)
    lock = json.loads((DOCS_SITE / "package-lock.json").read_text(encoding="utf-8"))
    for package in packages:  # npm ci installs from the lock: each package resolved there
        entry = lock["packages"].get(f"node_modules/{package}", {})
        assert entry.get("resolved", "").startswith("https://registry.npmjs.org/") and entry.get("integrity"), package
    assert "@import './herald-fonts.css';" in HERALD_CSS.read_text(encoding="utf-8")


def _load_assemble_pages():
    spec = importlib.util.spec_from_file_location(
        "assemble_pages_43_4", REPO_ROOT / "docsite" / "tools" / "assemble_pages.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_43_4_ac5_a_google_fonts_link_on_a_herald_page_fails_pages_check(tmp_path: Path, capsys) -> None:
    """AC5: ``pages-check``'s origin check finds no font from another origin on the built faces, and a planted
    ``fonts.googleapis.com`` stylesheet link on a herald page exits 1 naming the page and the URL."""
    site_url = "https://rxm7706.github.io/local-recipes"
    page = tmp_path / "herald" / "dossier" / "index.html"
    page.parent.mkdir(parents=True)
    (tmp_path / "_astro").mkdir()
    (tmp_path / "_astro" / "herald.css").write_text(
        "@font-face{font-family:IBM Plex Sans;src:url(/local-recipes/_astro/plex.woff2)format('woff2')}",
        encoding="utf-8",
    )
    head = '<link rel="stylesheet" href="/local-recipes/_astro/herald.css">'
    page.write_text(f"<html><head>{head}</head><body><h1>Dossier</h1></body></html>", encoding="utf-8")
    assemble_pages = _load_assemble_pages()
    assemble_pages._check_origins(tmp_path, site_url)
    planted = '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans">'
    page.write_text(f"<html><head>{head}{planted}</head><body></body></html>", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        assemble_pages._check_origins(tmp_path, site_url)
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "herald/dossier/index.html" in err and "fonts.googleapis.com" in err
