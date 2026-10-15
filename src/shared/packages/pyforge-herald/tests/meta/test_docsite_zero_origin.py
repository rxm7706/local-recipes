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


# --- Story 43.4: fonts and theme come from one design system; its review: one theme contract across Pages -------

DOCS_SITE = REPO_ROOT / "docs-site"
STYLES = DOCS_SITE / "src" / "styles"
HERALD_CSS = STYLES / "herald.css"
HERALD_FONTS_CSS = STYLES / "herald-fonts.css"
THEME_CSS = STYLES / "theme.css"
JINJA_CSS = REPO_ROOT / "docsite" / "assets" / "_dossier.css"
JINJA_CHROME_CSS = REPO_ROOT / "docsite" / "assets" / "_site-chrome.css"
HERALD_PAGES_TS = DOCS_SITE / "src" / "lib" / "herald-pages.ts"
NODE = shutil.which("node")

_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_RULE = re.compile(r"([^{}@;]+)\{([^{}]*)\}")
_DECLARATION = re.compile(r"(?:^|;)\s*([\w-]+)\s*:\s*([^;]+)")
_VAR = re.compile(r"var\(\s*(--[\w-]+)\s*(?:,\s*((?:[^()]|\([^()]*\))*))?\)")
_LITERAL_COLOUR = re.compile(r"#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch)\(|:\s*(?:white|black)\b")
_LIGHT, _DARK, _NO_SCRIPT = ":root", ":root[data-theme='dark']", ":root:not([data-theme])"


def _rules(css: str) -> list[tuple[str, dict[str, str]]]:
    """Each innermost rule as ``(selector, {property: value})``, whitespace and quote style normalized."""
    out = []
    for selector, body in _RULE.findall(_COMMENT.sub("", css)):
        declarations = {name.lower(): " ".join(value.split()) for name, value in _DECLARATION.findall(body)}
        out.append((" ".join(selector.replace('"', "'").split()), declarations))
    return out


def _tokens(css: str, selector: str) -> dict[str, str]:
    """The custom properties one selector's block defines."""
    blocks = [decl for sel, decl in _rules(css) if sel == selector]
    assert len(blocks) == 1, f"expected one {selector!r} block, found {len(blocks)}"
    return {name: value for name, value in blocks[0].items() if name.startswith("--")}


def _theme(dark: bool) -> dict[str, str]:
    """The site theme's variables as a page in that theme sees them: the light block, then the dark one over it."""
    css = THEME_CSS.read_text(encoding="utf-8")
    return {**_tokens(css, _LIGHT), **(_tokens(css, _DARK) if dark else {})}


def _resolve(value: str, scope: dict[str, str]) -> str:
    """``value`` with every ``var()`` replaced by its value in ``scope`` (or its fallback), recursively."""
    for _ in range(10):
        resolved = _VAR.sub(lambda m: scope.get(m.group(1), m.group(2) or m.group(0)), value)
        if resolved == value:
            return " ".join(resolved.split())
        value = resolved
    raise AssertionError(f"var() cycle in {value!r}")


def _family_list(value: str) -> tuple[str, ...]:
    return tuple(part.strip().strip("'\"") for part in value.split(","))


def _families(css: str, scope: dict[str, str]) -> dict[str, tuple[str, ...]]:
    """The font-family list each selector declares, resolved through ``scope``, quotes dropped."""
    return {
        selector: _family_list(_resolve(decl["font-family"], scope))
        for selector, decl in _rules(css)
        if "font-family" in decl
    }


def test_43_4_ac2_the_herald_pages_resolve_the_jinja_families() -> None:
    """AC2, under the theme contract (operator ruling 2026-10-15): the dossier's body and headings resolve, through the
    site theme's variables, to exactly the Jinja path's font-family; every other rule of the Jinja stylesheets that
    names a family resolves to the same face first (the theme carries one mono fallback list). The back-bar's rules are
    the reader pages' own."""
    jinja = _families(JINJA_CSS.read_text(encoding="utf-8"), {})
    for dark in (False, True):
        astro = _families(HERALD_CSS.read_text(encoding="utf-8"), _theme(dark))
        assert astro["body"] == jinja["body"] == ("IBM Plex Sans", "system-ui", "-apple-system", "sans-serif")
        heading = ("Big Shoulders Display", "IBM Plex Sans", "sans-serif")
        assert astro["h1, h2, h3, h4"] == jinja["h1, h2, h3, h4"] == heading
        chrome = _families(JINJA_CHROME_CSS.read_text(encoding="utf-8"), {})
        expected = {**jinja, **{sel: fam for sel, fam in chrome.items() if not sel.startswith(".ig-backbar")}}
        assert len(expected) > 20
        assert {sel: astro.get(sel, ("?",))[0] for sel in expected} == {sel: fam[0] for sel, fam in expected.items()}


def test_43_4_ac3_the_theme_is_light_and_under_starlights_dark_selector() -> None:
    """AC3, under the theme contract: theme.css fills Starlight's variables light under ``:root`` and dark under
    ``[data-theme='dark']`` (the two differ), and the scripts-off fallback repeats the dark block exactly; herald.css
    defines the dossier's tokens once, from Starlight's variables only, so they take the dark values with no block of
    their own -- and the plain aliases resolve to the Jinja path's values in both themes."""
    css = THEME_CSS.read_text(encoding="utf-8")
    light, dark = _tokens(css, _LIGHT), _tokens(css, _DARK)
    assert {"--sl-font", "--sl-font-mono", "--sl-color-accent", "--sl-color-black", "--sl-color-white"} <= set(light)
    assert {f"--sl-color-gray-{n}" for n in range(1, 8)} <= set(dark) <= set(light)
    assert all(light[name] != value for name, value in dark.items()), "a dark value equals its light one"
    assert _tokens(css, _NO_SCRIPT) == dark

    herald = HERALD_CSS.read_text(encoding="utf-8")
    tokens = _tokens(herald, _LIGHT)
    assert [sel for sel, _ in _rules(herald) if "data-theme" in sel] == []
    assert "prefers-color-scheme" not in _COMMENT.sub("", herald)
    jinja = JINJA_CSS.read_text(encoding="utf-8")
    jinja_light, jinja_dark = _tokens(jinja, _LIGHT), _tokens(jinja, _DARK)
    assert set(tokens) == set(jinja_light) and len(tokens) > 30
    for name, value in tokens.items():
        assert "var(--sl-" in value and not _LITERAL_COLOUR.search(value), f"{name}: {value}"
    nearest = {"--rail-faint", "--code-bg", "--st-doctor", "--st-doctor-soft"}  # the theme's nearest, not equal
    exact = [n for n, value in tokens.items() if re.fullmatch(r"var\(--sl-[\w-]+\)", value) and n not in nearest]
    assert len(exact) == 24  # the other six -- three station accents, their softs -- are mixes of two
    for name in exact:
        assert _resolve(tokens[name], _theme(False)) == jinja_light[name], name
        assert _resolve(tokens[name], _theme(True)) == jinja_dark[name], name


_STYLE_SOURCES = ("styles/herald.css", "lib/herald-pages.ts", "layouts", "components/herald", "components/dossier")


def _style_text(path: Path) -> str:
    """The CSS a herald source declares: a stylesheet whole; else its ``<style>`` bodies and ``style`` attributes."""
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".css":
        return _COMMENT.sub("", text)
    bodies = re.findall(r"<style\b[^>]*>(.*?)</style>", text, re.DOTALL)
    attributes = re.findall(r"""\bstyle=(?:\{`([^`]*)`\}|"([^"]*)")""", text)
    return "\n".join([*bodies, *("".join(a) for a in attributes)])


def test_43_4_no_herald_stylesheet_names_a_font_or_colour_of_its_own() -> None:
    """The theme contract (operator ruling 2026-10-15): outside theme.css and the faces it imports, no herald stylesheet,
    inline style or reader page declares a literal font family or colour -- each is one of Starlight's variables, or a
    token derived from them -- so replacing theme.css re-themes every page."""
    sources = [
        path
        for rel in _STYLE_SOURCES
        for path in ([DOCS_SITE / "src" / rel] if "." in rel else sorted((DOCS_SITE / "src" / rel).rglob("*")))
        if path.is_file() and (not path.name.endswith(".astro") or "Herald" in path.name or "layouts" not in path.parts)
    ]
    assert len(sources) > 10
    findings = []
    for path in sources:
        css = _style_text(path)
        findings += [f"{path.name}: colour {m.group(0)!r}" for m in _LITERAL_COLOUR.finditer(css)]
        families = re.findall(r"font-family\s*:\s*([^;}`\n]+)", css)
        findings += [f"{path.name}: font-family {value.strip()!r}" for value in families if "var(--sl-" not in value]
    assert findings == []


_THEME_PROBE = """
import { HERALD_CSP, THEME_SCRIPT } from %s;
process.stdout.write(JSON.stringify({ csp: HERALD_CSP, theme: THEME_SCRIPT }));
"""


@pytest.mark.skipif(NODE is None, reason="node is not on PATH")
def test_43_4_ac3_the_theme_follows_the_docs_toggle_and_the_csp_allows_it() -> None:
    """AC3: the herald pages read the docs header's toggle from Starlight's own store (``starlight-theme``) and set
    Starlight's ``data-theme`` -- no second toggle or store -- again on a system-scheme change and a back-forward-cache
    restore, in an IIFE that leaves no global; the CSP allows that one inline script by hash."""
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
    assert theme.startswith("(()=>{") and theme.endswith("})()") and "var " not in theme
    assert "localStorage.getItem('starlight-theme')" in theme
    assert "r.dataset.theme=" in theme and "prefers-color-scheme: light" in theme
    assert "addEventListener('change',a)" in theme and "addEventListener('pageshow',a)" in theme
    digest = base64.b64encode(hashlib.sha256(theme.encode("utf-8")).digest()).decode("ascii")
    assert f"'sha256-{digest}'" in probe["csp"]
    provider = DOCS_SITE / "node_modules/@astrojs/starlight/dist/components/ThemeProvider.astro"
    if provider.is_file():  # the store is Starlight's: its provider reads the same key
        assert "localStorage.getItem('starlight-theme')" in provider.read_text(encoding="utf-8")


def test_43_4_ac4_the_astro_path_names_no_vendored_font() -> None:
    """AC4: ``grep -rn "assets/fonts" docs-site/src`` finds nothing, and every face is a woff2 file of an @fontsource
    package ``package.json`` lists (resolved in the lock), imported by theme.css, which herald.css imports."""
    hits = [
        f"{path.relative_to(REPO_ROOT)}:{n}"
        for path in sorted((DOCS_SITE / "src").rglob("*"))
        if path.is_file() and not path.is_symlink() and "content" not in path.relative_to(DOCS_SITE / "src").parts[:1]
        for n, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1)
        if "assets/fonts" in line
    ]
    assert hits == []
    fonts = _COMMENT.sub("", HERALD_FONTS_CSS.read_text(encoding="utf-8"))
    urls = re.findall(r"url\(\s*'([^']+)'\s*\)", fonts)
    assert len(urls) == 19 and all(url.endswith(".woff2") and "/files/" in url for url in urls)
    assert "@import" not in fonts
    packages = {"/".join(url.split("/")[:2]) for url in urls}
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
    assert "@import './herald-fonts.css';" in THEME_CSS.read_text(encoding="utf-8")
    assert "@import './theme.css';" in HERALD_CSS.read_text(encoding="utf-8")


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
