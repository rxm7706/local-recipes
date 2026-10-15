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
# Every CSS named colour (CSS Color 4, 148 names) and system colour, matched in any case; ``transparent``,
# ``currentColor`` and ``inherit`` are not a colour of their own and pass.
_NAMED_COLOURS = """
aliceblue antiquewhite aqua aquamarine azure beige bisque black blanchedalmond blue blueviolet brown burlywood
cadetblue chartreuse chocolate coral cornflowerblue cornsilk crimson cyan darkblue darkcyan darkgoldenrod darkgray
darkgreen darkgrey darkkhaki darkmagenta darkolivegreen darkorange darkorchid darkred darksalmon darkseagreen
darkslateblue darkslategray darkslategrey darkturquoise darkviolet deeppink deepskyblue dimgray dimgrey dodgerblue
firebrick floralwhite forestgreen fuchsia gainsboro ghostwhite gold goldenrod gray green greenyellow grey honeydew
hotpink indianred indigo ivory khaki lavender lavenderblush lawngreen lemonchiffon lightblue lightcoral lightcyan
lightgoldenrodyellow lightgray lightgreen lightgrey lightpink lightsalmon lightseagreen lightskyblue lightslategray
lightslategrey lightsteelblue lightyellow lime limegreen linen magenta maroon mediumaquamarine mediumblue
mediumorchid mediumpurple mediumseagreen mediumslateblue mediumspringgreen mediumturquoise mediumvioletred
midnightblue mintcream mistyrose moccasin navajowhite navy oldlace olive olivedrab orange orangered orchid
palegoldenrod palegreen paleturquoise palevioletred papayawhip peachpuff peru pink plum powderblue purple
rebeccapurple red rosybrown royalblue saddlebrown salmon sandybrown seagreen seashell sienna silver skyblue slateblue
slategray slategrey snow springgreen steelblue tan teal thistle tomato turquoise violet wheat white whitesmoke yellow
yellowgreen
accentcolor accentcolortext activetext buttonborder buttonface buttontext canvas canvastext field fieldtext graytext
highlight highlighttext linktext mark marktext selecteditem selecteditemtext visitedtext
""".split()
_LITERAL_COLOUR = re.compile(
    r"#[0-9a-f]{3,8}\b"
    r"|(?<![\w-])(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color|light-dark|device-cmyk)\("
    rf"|(?<![\w.#-])(?:{'|'.join(_NAMED_COLOURS)})(?![\w(-])",
    re.IGNORECASE,
)
_LIGHT, _DARK, _NO_SCRIPT = ":root", ":root[data-theme='dark']", ":root:not([data-theme])"


def _colour_literals(value: str) -> list[str]:
    """The literal colours in one declaration value: quoted strings and ``url()`` are not colours."""
    value = re.sub(r"url\([^)]*\)|'[^']*'|\"[^\"]*\"", "", value)
    return [m.group(0) for m in _LITERAL_COLOUR.finditer(value)]


def _at_rules(css: str) -> list[tuple[tuple[str, ...], str]]:
    """Each rule as ``(enclosing at-rule preludes, selector)``, innermost last; comments dropped."""
    css, out = _COMMENT.sub("", css), []

    def walk(text: str, context: tuple[str, ...]) -> None:
        i = 0
        while (j := text.find("{", i)) >= 0:
            head, depth, k = text[i:j].split(";")[-1].split("}")[-1].strip(), 1, j + 1
            while depth and k < len(text):
                depth += {"{": 1, "}": -1}.get(text[k], 0)
                k += 1
            if head.startswith("@media") or head.startswith("@supports") or head.startswith("@layer"):
                walk(text[j + 1 : k - 1], (*context, " ".join(head.split())))
            else:
                out.append((context, " ".join(head.replace('"', "'").split())))
            i = k

    walk(css, ())
    return out


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
    # Dark is a screen theme (the re-review): both dark blocks sit under a screen-only query, so in print Starlight's
    # print stylesheet and the light block keep the page light; the light block is at the top level, every medium.
    contexts = {selector: context for context, selector in _at_rules(css)}
    assert contexts[_LIGHT] == ()
    assert contexts[_DARK] == ("@media screen",)
    assert contexts[_NO_SCRIPT] == ("@media screen and (prefers-color-scheme: dark)",)
    assert all("print" not in at and at.startswith("@media screen") for at in (*contexts[_DARK], *contexts[_NO_SCRIPT]))

    herald = HERALD_CSS.read_text(encoding="utf-8")
    tokens = _tokens(herald, _LIGHT)
    assert [sel for sel, _ in _rules(herald) if "data-theme" in sel] == []
    assert "prefers-color-scheme" not in _COMMENT.sub("", herald)
    jinja = JINJA_CSS.read_text(encoding="utf-8")
    jinja_light, jinja_dark = _tokens(jinja, _LIGHT), _tokens(jinja, _DARK)
    assert set(tokens) == set(jinja_light) and len(tokens) > 30
    for name, value in tokens.items():
        assert "var(--sl-" in value and not _colour_literals(value), f"{name}: {value}"
    # the theme's nearest, not equal: --rail since the re-review (light gray-3 darkened to read AA, 5.25:1)
    nearest = {"--rail", "--rail-faint", "--code-bg", "--st-doctor", "--st-doctor-soft"}
    exact = [n for n, value in tokens.items() if re.fullmatch(r"var\(--sl-[\w-]+\)", value) and n not in nearest]
    assert len(exact) == 23  # the other six -- three station accents, their softs -- are mixes of two
    for name in exact:
        assert _resolve(tokens[name], _theme(False)) == jinja_light[name], name
        assert _resolve(tokens[name], _theme(True)) == jinja_dark[name], name


_THEME_SOURCES = {"styles/theme.css", "styles/herald-fonts.css"}  # the theme and the faces it imports
_STYLE_ATTRIBUTE = re.compile(
    r"""\bstyle=(?:"([^"]*)"|'([^']*)'|\{`([^`]*)`\}|\{\s*'([^']*)'\s*\}|\{\s*"([^"]*)"\s*\}|\{\{(.*?)\}\}|(\{[^}]*\}))""",
    re.DOTALL,
)
_TRUSTED_INTERPOLATION = re.compile(r"\$\{\s*(?:cssVar|cssTextTone)\([^`{}]*\)\s*\}")
_FONT_KEYWORDS = frozenset(
    "normal italic oblique bold bolder lighter small-caps ultra-condensed extra-condensed condensed semi-condensed "
    "semi-expanded expanded extra-expanded ultra-expanded xx-small x-small small medium large x-large xx-large "
    "xxx-large smaller larger".split()
)
_GLOBAL_KEYWORDS = frozenset({"inherit", "initial", "unset", "revert", "revert-layer"})


def _scanned_sources(src: Path) -> list[Path]:
    """Every file under ``docs-site/src`` but the theme, its faces and the docs content (the shelf's markdown)."""
    return sorted(
        path
        for path in src.rglob("*")
        if path.is_file()
        and path.relative_to(src).parts[0] != "content"
        and path.relative_to(src).as_posix() not in _THEME_SOURCES
    )


def _top_level_split(value: str) -> list[str]:
    parts, depth, current = [], 0, ""
    for char in value:
        depth += {"(": 1, ")": -1}.get(char, 0)
        if char == "," and depth == 0:
            parts.append(current.strip())
            current = ""
        else:
            current += char
    return [*parts, current.strip()]


def _theme_font(entry: str) -> bool:
    """``var(--sl-…)``, whose fallback (if any) is itself one or a list of them."""
    match = re.fullmatch(r"var\(\s*--sl-[\w-]+\s*(?:,(.*))?\)", entry.strip(), re.DOTALL)
    return bool(match) and (match.group(1) is None or all(_theme_font(e) for e in _top_level_split(match.group(1))))


def _font_findings(prop: str, value: str) -> list[str]:
    value = " ".join(value.split())
    if value.lower() in _GLOBAL_KEYWORDS:
        return []
    if prop == "font-family":
        return [f"font-family {value!r}"] if not all(_theme_font(e) for e in _top_level_split(value)) else []
    families = re.findall(r"var\(\s*--sl-(?:[^()]|\([^()]*\))*\)", value)  # the shorthand's family list
    rest = re.sub(r"var\(\s*--sl-(?:[^()]|\([^()]*\))*\)", " ", value).replace("/", " ").replace(",", " ")
    literal = [t for t in rest.split() if t.lower() not in _FONT_KEYWORDS and not re.fullmatch(r"[\d.]+[a-z%]*", t)]
    return [f"font {value!r}"] if literal or not families else []


def _declaration_lists(path: Path) -> tuple[list[str], list[str]]:
    """The CSS a source declares, as declaration lists: a stylesheet's rule bodies; else each ``<style>`` body's and
    each ``style`` attribute's (double- or single-quoted, a template literal, a string expression or an Astro object).
    Template interpolations are trusted only through ``cssVar()`` / ``cssTextTone()``, which take a theme token alone;
    any other interpolation, and a ``style={expression}``, is a finding of its own: the guard cannot read it."""
    text = path.read_text(encoding="utf-8", errors="replace")
    sheets = [text] if path.suffix == ".css" else re.findall(r"<style\b[^>]*>(.*?)</style>", text, re.DOTALL)
    lists = [body for sheet in sheets for body in re.findall(r"\{([^{}]*)\}", _COMMENT.sub("", sheet))]
    unreadable: list[str] = []
    for match in _STYLE_ATTRIBUTE.finditer(text):
        *strings, astro_object, expression = match.groups()
        if expression is not None:
            unreadable.append(f"style={expression}")
        elif astro_object is not None:
            declarations = []
            for entry in _top_level_split(astro_object):
                if not entry:
                    continue
                key, _, raw = entry.partition(":")
                literal = re.fullmatch(r"""\s*(?:'([^']*)'|"([^"]*)"|`([^`$]*)`|([\d.]+))\s*""", raw)
                if literal is None:
                    unreadable.append(f"style={{{{{entry.strip()}}}}}")
                    continue
                prop = re.sub(r"[A-Z]", lambda m: "-" + m.group(0).lower(), key.strip().strip("'\""))
                declarations.append(f"{prop}: {next(v for v in literal.groups() if v is not None)}")
            lists.append("; ".join(declarations))
        else:
            value = next(v for v in strings if v is not None)
            value = _TRUSTED_INTERPOLATION.sub("var(--sl-interpolated)", value)
            if "${" in value:
                unreadable.append(f"style={value!r}")
            lists.append(value)
    return lists, unreadable


def _literal_findings(src: Path) -> list[str]:
    """Each literal colour or font family the sources under ``src`` declare outside the theme."""
    findings = []
    for path in _scanned_sources(src):
        lists, unreadable = _declaration_lists(path)
        rel = path.relative_to(src).as_posix()
        findings += [f"{rel}: a style the guard cannot read, {what}" for what in unreadable]
        for declarations in lists:
            for declaration in declarations.split(";"):
                prop, colon, value = declaration.partition(":")
                prop = prop.strip().lower()
                if not colon or not re.fullmatch(r"-{0,2}[\w-]+", prop):
                    continue
                findings += [f"{rel}: colour {c!r} in {prop}" for c in _colour_literals(value)]
                if prop in ("font", "font-family"):
                    findings += [f"{rel}: {f}" for f in _font_findings(prop, value)]
    return findings


def test_43_4_no_source_names_a_font_or_colour_outside_the_theme() -> None:
    """The theme contract (operator ruling 2026-10-15; the re-review's should-fix 2): outside theme.css, the faces it
    imports and the docs content, no file under ``docs-site/src`` -- herald CSS, layouts, components, pages, endpoint
    output, libraries -- declares a literal colour (hex, a colour function, a CSS named or system colour in any case)
    or a literal font in ``font-family`` or the ``font`` shorthand: each is one of Starlight's variables, or a token
    derived from them, so replacing theme.css re-themes every page."""
    sources = _scanned_sources(DOCS_SITE / "src")
    assert len(sources) > 40 and any(p.suffix == ".astro" for p in sources) and any(p.suffix == ".ts" for p in sources)
    assert _literal_findings(DOCS_SITE / "src") == []


_GUARD_MUTATIONS = [  # (file under docs-site/src, the text to find, its replacement) -- the re-review's probes
    ("styles/herald.css", "a { color: var(--sl-color-text-accent); }", "a { color: red; }"),
    ("styles/herald.css", "border-bottom: 3px solid var(--ink); }", "border-bottom: 3px solid white; }"),
    ("styles/herald.css", "a { color: var(--sl-color-text-accent); }", "a { color: White; }"),
    ("styles/herald.css", "outline: 2px solid var(--focus);", "outline: 2px solid navy;"),
    ("styles/herald.css", "55%, var(--sl-color-blue));", "55%, teal);"),
    ("styles/herald.css", "font-size: 17px; line-height", "font: 17px/1.65 Georgia, serif; line-height"),
    (
        "styles/herald.css",
        "code, .mono { font-family: var(--sl-font-mono);",
        'code, .mono { font-family: var(--sl-font-mono), "Comic Sans MS";',
    ),
    (
        "styles/herald.css",
        "code, .mono { font-family: var(--sl-font-mono);",
        "code, .mono { font-family: var(--sl-font-mono, Courier);",
    ),
    ("pages/herald/[...index].astro", '<div class="station-rail">', '<div class="station-rail" style={`color:#c00`}>'),
    (
        "pages/herald/[...index].astro",
        '<div class="station-rail">',
        "<div class=\"station-rail\" style={{ color: 'rebeccapurple' }}>",
    ),
    (
        "pages/herald/[...index].astro",
        '<div class="station-rail">',
        "<div class=\"station-rail\" style={{ fontFamily: 'Arial' }}>",
    ),
    (
        "pages/herald/[...index].astro",
        '<div class="station-rail">',
        "<div class=\"station-rail\" style='background:#c00'>",
    ),
    ("pages/herald/[...index].astro", '<div class="station-rail">', '<div class="station-rail" style={railStyle}>'),
    ("lib/dossier-blocks.ts", '`<div class="chips">', '`<div class="chips" style="background:#c00">'),
    ("lib/dossier-blocks.ts", '`<div class="chips">', '`<div class="chips" style="color:${block.colour}">'),
    ("lib/herald-pages.ts", "font-family:var(--sl-font-mono);", "font-family:monospace;"),
    ("components/SiteTitle.astro", "color: var(--sl-color-gray-2);", "color: GrayText;"),
    (
        "lib/md-inline.ts",
        "export function cssVar",
        "const S = '<style>.x{color:hsl(0 0% 0%)}</style>';\nexport function cssVar",
    ),
]


@pytest.mark.parametrize(("rel", "find", "plant"), _GUARD_MUTATIONS)
def test_43_4_each_literal_the_re_review_planted_fails_the_guard(
    tmp_path: Path, rel: str, find: str, plant: str
) -> None:
    """Each mutation the re-review showed passing the old guard -- a named colour in any case or inside a derived
    token's ``color-mix()``, the ``font`` shorthand, a literal family after a theme variable or as its fallback, a
    style in a page, a library or an endpoint, an Astro object or single-quoted style, an unreadable style
    expression -- now fails it, planted in a copy of the sources."""
    src = tmp_path / "src"
    for path in _scanned_sources(DOCS_SITE / "src"):
        target = src / path.relative_to(DOCS_SITE / "src")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    assert _literal_findings(src) == []
    text = (src / rel).read_text(encoding="utf-8")
    assert find in text, (rel, find)
    (src / rel).write_text(text.replace(find, plant, 1), encoding="utf-8")
    findings = _literal_findings(src)
    assert findings and all(f.startswith(f"{rel}: ") for f in findings), findings


_CSS_VAR_PROBE = """
import { cssTextTone, cssVar } from %s;
const out = {};
for (const value of ['--amber', '--st-marshal', '', undefined, '#c00', 'red', 'var(--amber)', '--x;color:red']) {
  try { out[String(value)] = cssVar(value); } catch (error) { out[String(value)] = 'throws: ' + error.message; }
}
out.tone = cssTextTone('--st-marshal');
out.noTone = cssTextTone(undefined);
process.stdout.write(JSON.stringify(out));
"""


@pytest.mark.skipif(NODE is None, reason="node is not on PATH")
def test_43_4_css_var_takes_a_theme_token_alone() -> None:
    """The re-review's nit 3: a value from dossier.yml / site.yml reaches an inline ``style=`` only through
    ``cssVar()`` (or ``cssTextTone()``, built on it), which takes a ``--custom-property`` name alone and fails the build
    on anything else -- so a literal colour in the YAML cannot pass the theme contract that the source guard reads."""
    done = subprocess.run(
        [
            NODE or "node",
            "--experimental-strip-types",
            "--input-type=module",
            "-e",
            _CSS_VAR_PROBE % json.dumps((DOCS_SITE / "src" / "lib" / "md-inline.ts").as_uri()),
        ],
        cwd=DOCS_SITE,
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    out = json.loads(done.stdout)
    assert out["--amber"] == "var(--amber)" and out["--st-marshal"] == "var(--st-marshal)"
    assert out[""] == "" and out["undefined"] == "" and out["noTone"] == ""
    for literal in ("#c00", "red", "var(--amber)", "--x;color:red"):
        assert out[literal].startswith("throws: cssVar:") and "is not a theme token" in out[literal], literal
    assert out["tone"] == "color-mix(in srgb, var(--st-marshal) 75%, var(--ink))"


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
