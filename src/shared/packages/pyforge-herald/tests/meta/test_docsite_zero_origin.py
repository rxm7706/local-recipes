"""Story 31.3: the public site loads no third-party font resources.

Story 43.4 (CAP-61): the faces come from @fontsource, the dossier's families and tokens match the retired Jinja
path's (frozen in ``tests/fixtures/jinja-theme-2026-10-15.json`` when Story 43.7 deleted ``docsite/``), and the theme
follows the docs header's toggle -- the ``test_43_4_*`` tests. Story 43.7: the faces' OFL-1.1 licence text ships in
the artifact from each @fontsource package's own ``LICENSE`` (``scripts/populate-public.mts``).
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[6]
#: The retired Jinja path's families and tokens, frozen when Story 43.7 deleted it.
JINJA = json.loads(
    (Path(__file__).resolve().parents[1] / "fixtures" / "jinja-theme-2026-10-15.json").read_text("utf-8")
)


def test_ofl_licences_ship_from_each_fontsource_package() -> None:
    """Story 43.4's re-review (nit 6), carried by 43.7: the licence text comes from each package's own ``LICENSE``,
    never a hand-vendored copy, and the build serves it beside the faces."""
    script = (REPO_ROOT / "docs-site" / "scripts" / "populate-public.mts").read_text(encoding="utf-8")
    assert "fs.readFileSync(path.join(modules, pkg, 'LICENSE'))" in script
    packages = re.findall(
        r"'(@fontsource(?:-variable)?/[\w-]+)'", script.split("FONT_PACKAGES = [", 1)[1].split("]", 1)[0]
    )
    fonts = (REPO_ROOT / "docs-site" / "src" / "styles" / "herald-fonts.css").read_text(encoding="utf-8")
    assert sorted(packages) == sorted({"/".join(url.split("/")[:2]) for url in re.findall(r"url\('([^']+)'\)", fonts)})
    modules = REPO_ROOT / "docs-site" / "node_modules"
    for package in packages:
        licence = modules / package / "LICENSE"
        if licence.is_file():  # installed: the text is the OFL
            assert "SIL OPEN FONT LICENSE" in licence.read_text(encoding="utf-8").upper(), package


# --- Story 43.4: fonts and theme come from one design system; its review: one theme contract across Pages -------

DOCS_SITE = REPO_ROOT / "docs-site"
STYLES = DOCS_SITE / "src" / "styles"
HERALD_CSS = STYLES / "herald.css"
HERALD_FONTS_CSS = STYLES / "herald-fonts.css"
THEME_CSS = STYLES / "theme.css"
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
    site theme's variables, to exactly the retired Jinja path's font-family; every other rule of its stylesheets that
    named a family resolves to the same face first (the theme carries one mono fallback list)."""
    expected = JINJA["first_family"]
    for dark in (False, True):
        astro = _families(HERALD_CSS.read_text(encoding="utf-8"), _theme(dark))
        assert astro["body"] == tuple(JINJA["body"]) == ("IBM Plex Sans", "system-ui", "-apple-system", "sans-serif")
        heading = ("Big Shoulders Display", "IBM Plex Sans", "sans-serif")
        assert astro["h1, h2, h3, h4"] == tuple(JINJA["headings"]) == heading
        assert len(expected) > 20
        assert {sel: astro.get(sel, ("?",))[0] for sel in expected} == expected


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
    # and nothing else sets a theme at the top level (the second re-review's nit 5): the light block, the docs' heading
    # face and Story 43.5's built-from line are theme.css's only unconditional rules
    assert [selector for context, selector in _at_rules(css) if context == ()] == [
        _LIGHT,
        ":where(h1#_top), .sl-markdown-content :where(h1, h2, h3, h4):not(:where(.not-content *))",
        ".built-from",
    ]

    herald = HERALD_CSS.read_text(encoding="utf-8")
    tokens = _tokens(herald, _LIGHT)
    assert [sel for sel, _ in _rules(herald) if "data-theme" in sel] == []
    assert "prefers-color-scheme" not in _COMMENT.sub("", herald)
    jinja_light, jinja_dark = JINJA["tokens_light"], JINJA["tokens_dark"]
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
    r"""\bstyle\s*=\s*(?:"([^"]*)"|'([^']*)'|\{`([^`]*)`\}|\{\s*'([^']*)'\s*\}|\{\s*"([^"]*)"\s*\}|\{\{(.*?)\}\}|(\{[^}]*\}))""",
    re.DOTALL | re.IGNORECASE,
)
_TRUSTED_INTERPOLATION = re.compile(r"\$\{\s*(?:cssVar|cssTextTone)\([^()`{}]*\)\s*\}")
#: Story 43.4's second re-review: the presentation attributes that take a colour (SVG and legacy HTML), the legacy
#: ``<font face>``, SVG's ``font-family`` and the ``theme-color`` meta, read inside each tag of a non-CSS source, the
#: value double- or single-quoted, an Astro expression or unquoted (the third re-review).
_TAG = re.compile(r"<[a-zA-Z][\w:.-]*\b[^<>]*>")
_COLOUR_ATTRIBUTE = re.compile(
    r"""\s(fill|stroke|stop-color|flood-color|lighting-color|color|bgcolor|face|font-family|content)\s*=\s*"""
    r"""(?:"([^"]*)"|'([^']*)'|\{([^{}]*)\}|([^\s"'=<>`{}]+))""",
    re.IGNORECASE,
)
_TRUSTED_ATTRIBUTE = re.compile(r"\s*(?:cssVar|cssTextTone)\([^()`{}]*\)\s*")
#: ``@property --sl-*`` registers a theme variable (its ``initial-value`` sets it): theme.css's alone
_REGISTERED_THEME_VARIABLE = re.compile(r"@property\s+(--sl-[\w-]+)", re.IGNORECASE)
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


def _css_bodies(css: str) -> list[str]:
    """Each block's own text with its nested blocks cut out (CSS nesting: ``.a { color: red; .b { ... } }`` reads
    ``color: red``). Every block counts, an at-rule's too: a grouping rule nested in a style rule holds declarations
    (``.a { @media screen { color: red } }``, ``@supports``, ``@container``, ``@layer``, ``@starting-style``, and a
    top-level ``@scope``), while one that holds only rules (a top-level ``@media``) has no text of its own once they
    are cut out (the third re-review: a filter on the prelude dropped the nested case)."""
    frames: list[tuple[str, list[str]]] = [("", [])]
    out, buf = [], ""
    for char in _COMMENT.sub("", css):
        if char == "{":
            head, _, prelude = buf.rpartition(";")
            frames[-1][1].append(f"{head};" if head else "")
            frames.append((prelude.strip(), []))
            buf = ""
        elif char == "}" and len(frames) > 1:
            _prelude, own = frames.pop()
            own.append(buf)
            out.append("".join(own))
            buf = ""
        else:
            buf += char
    return out


def _attribute_findings(text: str) -> list[str]:
    """The colours and faces a non-CSS source's tags name outside CSS: a colour attribute (``fill``, ``stroke``, ...,
    ``color``, ``bgcolor``), the ``theme-color`` meta's ``content`` and any ``<font face>``; an attribute bound to an
    expression other than ``cssVar()`` / ``cssTextTone()`` is unreadable, so a finding too."""
    findings = []
    for tag in _TAG.findall(text):
        theme_meta = re.match(r"<meta\b", tag, re.IGNORECASE) and re.search(
            r"""\bname\s*=\s*["']?theme-color""", tag, re.I
        )
        for name, double, single, expression, bare in _COLOUR_ATTRIBUTE.findall(f" {tag[1:]}"):
            name = name.lower()
            if name == "content" and not theme_meta:
                continue
            value = double or single or bare
            if expression and not _TRUSTED_ATTRIBUTE.fullmatch(expression):
                findings.append(f"an attribute the guard cannot read, {name}={{{expression}}}")
            elif name == "face" and value.strip():
                findings.append(f"font face {value!r}")
            elif name == "font-family":
                findings += _font_findings("font-family", value)
            else:
                findings += [f"colour {c!r} in the {name} attribute" for c in _colour_literals(value)]
    return findings


def _declaration_lists(path: Path) -> tuple[list[str], list[str]]:
    """The CSS a source declares, as declaration lists: a stylesheet's rule bodies; else each ``<style>`` body's and
    each ``style`` attribute's (double- or single-quoted, a template literal, a string expression or an Astro object;
    ``style`` in any case, spaces around ``=`` allowed). Template interpolations are trusted only as a whole
    ``${cssVar(...)}`` / ``${cssTextTone(...)}``, which take a theme token alone; any other interpolation, and a
    ``style={expression}``, is a finding of its own: the guard cannot read it. Out of its reach, named so nobody
    reads more into it: a style string built by concatenation or held in a variable, ``el.style`` /
    ``setAttribute('style', ...)`` in a script, ``<style set:html>``, an escaped quote (``style=\\"...\\"`` inside
    a TS string), CSS escapes (``\\72 ed``), an SVG data URI inside ``url()``, a ``{`` or ``}`` inside a CSS string
    ahead of a declaration, and a computed key in an Astro style object (``{{ ['color']: ... }}``). In a tag's
    attributes (``_attribute_findings``): a ``>`` or ``<`` inside an earlier attribute's expression (it ends the tag
    early), a spread (``{...{ fill: ... }}``), attributes with no space between them, SVG animation values
    (``<animate to>``, ``<set to>``, ``from``, ``values``) and legacy ``<body text link vlink alink>``."""
    text = path.read_text(encoding="utf-8", errors="replace")
    sheets = [text] if path.suffix == ".css" else re.findall(r"<style\b[^>]*>(.*?)</style>", text, re.DOTALL | re.I)
    unreadable: list[str] = [
        f"a <style> body with an interpolation, {sheet[:60]!r}" for sheet in sheets if "${" in sheet
    ]
    lists = [body for sheet in sheets if "${" not in sheet for body in _css_bodies(sheet)]
    # an @property registration of a theme variable is a write of it (its initial-value), read as one
    lists += [
        f"{name}: registered"
        for sheet in sheets
        for name in _REGISTERED_THEME_VARIABLE.findall(_COMMENT.sub("", sheet))
    ]
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
    """Each literal colour or font family the sources under ``src`` declare outside the theme, and each theme
    variable (``--sl-*``) they set: theme.css is the contract's only writer."""
    findings = []
    for path in _scanned_sources(src):
        lists, unreadable = _declaration_lists(path)
        rel = path.relative_to(src).as_posix()
        findings += [f"{rel}: a style the guard cannot read, {what}" for what in unreadable]
        if path.suffix != ".css":
            findings += [f"{rel}: {what}" for what in _attribute_findings(path.read_text("utf-8", errors="replace"))]
        for declarations in lists:
            for declaration in declarations.split(";"):
                prop, colon, value = declaration.partition(":")
                prop = prop.strip().lower()
                if not colon or not re.fullmatch(r"-{0,2}[\w-]+", prop):
                    continue
                if prop.startswith("--sl-"):
                    findings.append(f"{rel}: sets the theme variable {prop} (theme.css is its only writer)")
                findings += [f"{rel}: colour {c!r} in {prop}" for c in _colour_literals(value)]
                if prop in ("font", "font-family"):
                    findings += [f"{rel}: {f}" for f in _font_findings(prop, value)]
    return findings


def test_43_4_no_source_names_a_font_or_colour_outside_the_theme() -> None:
    """The theme contract (operator ruling 2026-10-15; the re-review's should-fix 2): outside theme.css, the faces it
    imports and the docs content, no file under ``docs-site/src`` -- herald CSS, layouts, components, pages, endpoint
    output, libraries -- declares a literal colour (hex, a colour function, a CSS named or system colour in any case)
    or a literal font in ``font-family`` or the ``font`` shorthand, sets a theme variable (``--sl-*``), or names a
    colour or face in a tag's attributes (SVG ``fill`` / ``stroke`` ..., ``<font>``, the ``theme-color`` meta): each
    is one of Starlight's variables, or a token derived from them, so replacing theme.css re-themes every page. What
    stays out of its reach is named in ``_declaration_lists``."""
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
    # the second re-review's probes: a theme variable set outside theme.css, a nested rule's sibling declaration,
    # colour attributes, <font>, the theme-color meta, a widened trusted interpolation and the attribute's spelling
    (
        "styles/herald.css",
        "* { box-sizing: border-box; }",
        '* { box-sizing: border-box; }\nbody { --sl-font: "Comic Sans MS"; }',
    ),
    (
        "styles/herald.css",
        "* { box-sizing: border-box; }",
        "* { box-sizing: border-box; }\n.x { --sl-font-x: Georgia; font-family: var(--sl-font-x); }",
    ),
    ("lib/dossier-blocks.ts", '`<div class="chips">', '`<div class="chips" style="--sl-font: Georgia">'),
    (
        "styles/herald.css",
        "* { box-sizing: border-box; }",
        "* { box-sizing: border-box; }\n.a { color: red; .b { margin: 0; } }",
    ),
    (
        "components/SiteTitle.astro",
        "  .pf-top-menu {\n",
        "  .pf-x { color: tomato; & a { margin: 0; } }\n  .pf-top-menu {\n",
    ),
    (
        "pages/herald/[...index].astro",
        '<div class="station-rail">',
        '<div class="station-rail"><svg><rect fill="#c00" /></svg>',
    ),
    ("lib/dossier-blocks.ts", '`<div class="chips">', '`<div class="chips"><svg><path stroke="red"/></svg>'),
    ("layouts/HeraldLayout.astro", "<body>", '<body><font color="red">x</font>'),
    ("layouts/HeraldLayout.astro", "<body>", '<body><font face="Comic Sans MS">x</font>'),
    (
        "layouts/HeraldLayout.astro",
        '<meta charset="utf-8" />',
        '<meta charset="utf-8" /><meta name="theme-color" content="#c00" />',
    ),
    (
        "pages/herald/[...index].astro",
        '<div class="station-rail">',
        '<div class="station-rail"><svg fill={railColour} />',
    ),
    (
        "lib/dossier-blocks.ts",
        'style="color:${cssTextTone(accent)}"',
        "style=\"color:${cssTextTone(accent) || ('#c00')}\"",
    ),
    ("pages/herald/[...index].astro", '<div class="station-rail">', '<div class="station-rail" STYLE="color:red">'),
    ("pages/herald/[...index].astro", '<div class="station-rail">', '<div class="station-rail" style = "color: red">'),
    # the third re-review's probes: a group rule nested in a style rule (CSS nesting gives its block declarations), a
    # top-level @scope, unquoted attribute values, SVG's font-family attribute and an @property theme variable
    (
        "styles/herald.css",
        "* { box-sizing: border-box; }",
        "* { box-sizing: border-box; }\n.a { @media screen { color: red; } }",
    ),
    (
        "styles/herald.css",
        "* { box-sizing: border-box; }",
        "* { box-sizing: border-box; }\n.a { @layer x { font-family: Georgia; } }",
    ),
    (
        "styles/herald.css",
        "* { box-sizing: border-box; }",
        "* { box-sizing: border-box; }\n.a { @starting-style { background: red; } }",
    ),
    (
        "styles/herald.css",
        "* { box-sizing: border-box; }",
        "* { box-sizing: border-box; }\n@scope (.a) { color: red; }",
    ),
    (
        "components/SiteTitle.astro",
        "  .pf-top-menu {\n",
        "  .pf-x { @supports (display: grid) { color: #c00; } }\n  .pf-top-menu {\n",
    ),
    (
        "pages/herald/[...index].astro",
        '<div class="station-rail">',
        '<div class="station-rail"><svg><rect fill=#c00 /></svg>',
    ),
    ("lib/dossier-blocks.ts", '`<div class="chips">', '`<div class="chips"><svg><path stroke=red></path></svg>'),
    (
        "layouts/HeraldLayout.astro",
        '<meta charset="utf-8" />',
        '<meta charset="utf-8" /><meta name=theme-color content=#c00 />',
    ),
    (
        "pages/herald/[...index].astro",
        '<div class="station-rail">',
        '<div class="station-rail"><svg><text font-family="Comic Sans MS">x</text></svg>',
    ),
    (
        "styles/herald.css",
        "* { box-sizing: border-box; }",
        "* { box-sizing: border-box; }\n@property --sl-font-x { syntax: '*'; inherits: true; initial-value: Georgia; }"
        "\n.x { font-family: var(--sl-font-x); }",
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


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not on PATH")
def test_43_4_ac5_a_google_fonts_link_on_a_herald_page_fails_pages_check(tmp_path: Path) -> None:
    """AC5: ``pages-check``'s origin check (``scripts/origin_check.py``, run by ``scripts/pages.mts``) passes the built
    faces, and a planted ``fonts.googleapis.com`` stylesheet link on a herald page is named with the page and the
    URL."""
    page = tmp_path / "herald" / "dossier" / "index.html"
    page.parent.mkdir(parents=True)
    (tmp_path / "_astro").mkdir()
    (tmp_path / "_astro" / "herald.css").write_text(
        "@font-face{font-family:IBM Plex Sans;src:url(/local-recipes/_astro/plex.woff2)format('woff2')}",
        encoding="utf-8",
    )
    head = '<link rel="stylesheet" href="/local-recipes/_astro/herald.css">'
    page.write_text(f"<html><head>{head}</head><body><h1>Dossier</h1></body></html>", encoding="utf-8")
    origin = [sys.executable, str(DOCS_SITE / "scripts" / "origin_check.py"), str(tmp_path)]
    hosts = ["https://rxm7706.github.io", "https://rxm7706.github.io"]
    assert subprocess.run([*origin, *hosts], capture_output=True, text=True, check=False).returncode == 0
    planted = '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans">'
    page.write_text(f"<html><head>{head}{planted}</head><body></body></html>", encoding="utf-8")
    done = subprocess.run([*origin, *hosts], capture_output=True, text=True, check=False)
    assert done.returncode == 1
    assert "herald/dossier/index.html" in done.stderr and "fonts.googleapis.com" in done.stderr
