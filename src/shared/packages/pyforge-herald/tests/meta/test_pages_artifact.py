"""Story 43.7 (spec-pyforge-herald CAP-61): ``pages-check`` is the one build check of the one generator.

``docs-site/scripts/pages.mts check`` judges an artifact: every path it must hold, the dashboard mount exactly the
build input's, the Kedro-Viz and Vizro mounts, the frozen legacy redirects, one CSP and one built-from line per page
(all naming one build), the machine-read documents, every local link, a non-empty body on every shelf page, one menu
on every navigable page, faces from the bundle, and -- through ``scripts/origin_check.py`` -- nothing loading from
another origin. These tests plant a small artifact that passes, then break it one way at a time; each finding must name
what broke. They need only node (and this interpreter, for the origin check), never docs-site's ``node_modules``.

It carries forward the checks of the retired assembler's tests (Stories 27.2, 31.1, 40.1, 42.1, 42.2, 43.2-43.5, 44.1)
that still describe the artifact, and the site URL rules of Stories 27.2, 31.1 and 42.3 (``pages.mts build``).
"""

from __future__ import annotations

import base64
import hashlib
import html
import json
import re
from pathlib import Path

import pytest
from pages_astro import DOCS_SITE, PAGES_MTS, REPO_ROOT, needs_node, pages_check, ts, write

SITE_URL = "https://rxm7706.github.io/local-recipes"
BASE = "/local-recipes/"
CSP = """<meta http-equiv="Content-Security-Policy" content="default-src 'self'">"""
LINE = '<p class="built-from" data-pages-built-from data-pagefind-ignore>Built from 0123456 · 2026-10-15 09:00 UTC</p>'
#: The menu every navigable page carries (label, site-root path), as the registry gives it with status off.
MENU = [
    ("Docs", ""),
    ("Overview", "herald/"),
    ("Dossier", "herald/dossier/"),
    ("Infographics", "herald/infographics/"),
    ("Decks", "herald/decks/"),
    ("Changes", "changes/"),
]
STATUS_MENU = [*MENU[:5], ("Status", "status/"), MENU[5]]
RSS = (
    '<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0">\n  <channel>\n    <title>PyForge changes</title>\n'
    "    <link>https://rxm7706.github.io/local-recipes/changes/</link>\n    <description>d</description>\n"
    "  </channel>\n</rss>\n"
)
LEGACY = json.loads((DOCS_SITE / "redirects.json").read_text(encoding="utf-8"))["legacy"]
READER_VIEWS = ("infographic-deck.html", "executive-summary.html")
DECKS = "herald/decks/index.html"
#: The decks index links its families (``herald/decks/<slug>/``); the plant's one is a legacy redirect's target.
FAMILY_LINK = '<a href="pyforge-atlas/index.html">Atlas</a>'

pytestmark = needs_node


def _menu(rel: str, menu: list[tuple[str, str]]) -> str:
    """The menu as page ``rel`` carries it: root-absolute under the base on a Starlight page, relative on a herald
    page (as the two shells write it)."""
    if rel.startswith("herald/"):
        up = "../" * rel.count("/")
        return "".join(f'<a data-pf-menu-link href="{up}{path}">{label}</a>' for label, path in menu)
    return "".join(f'<a data-pf-menu-link href="{BASE}{path}">{label}</a>' for label, path in menu)


def _page(rel: str, *, menu: list[tuple[str, str]] | None = MENU, body: str = "", shelf: bool = False) -> str:
    nav = _menu(rel, menu) if menu is not None else ""
    content = f'<div class="sl-markdown-content"><p>Shelf page body.</p>{body}</div>' if shelf else body
    return f"<!doctype html><html><head>{CSP}</head><body>{nav}<main>{content}</main>{LINE}</body></html>"


def _stub(rel: str, target: str) -> str:
    return (
        '<!DOCTYPE html><html><head><meta charset="utf-8"><title>Redirect</title>'
        f'<meta http-equiv="refresh" content="0; url={target}"></head>'
        f'<body><p><a href="{target}">Continue</a></p></body></html>'
    )


def plant(root: Path, *, status: bool = False, menu: list[tuple[str, str]] | None = None) -> Path:
    """A small artifact that passes ``pages-check``: the required pages, the agent files, the frozen redirects and
    their targets, the site URL marker."""
    menu = menu or (STATUS_MENU if status else MENU)
    write(root / ".pages-build-site-url", f"{SITE_URL}\n")
    for rel in ("index.html", "404.html", "changes/index.html"):
        write(root / rel, _page(rel, menu=menu, shelf=True))
    for rel in ("herald/index.html", "herald/dossier/index.html", "herald/infographics/index.html"):
        write(root / rel, _page(rel, menu=menu))
    write(root / DECKS, _page(DECKS, menu=menu, body=FAMILY_LINK))  # its family page is a legacy target below
    write(root / "herald/artifact/dossier.html", "<title>The PyForge Dossier</title>\n<p>body</p>\n")
    for rel, text in (("llms.txt", "# PyForge\n"), ("llms-full.txt", "# PyForge\n"), ("facts.json", "{}\n")):
        write(root / rel, text)
    write(root / "changes/rss.xml", RSS)
    if status:
        for rel in ("status/index.html", "status/ci/index.html", "status/runs/index.html"):
            write(root / rel, _page(rel, menu=menu, shelf=True))
    for source, target in LEGACY.items():
        src, dst = source.lstrip("/"), target.lstrip("/")
        target_file = root / dst
        if not target_file.exists():
            reader = dst.startswith("herald/infographics/") or dst.rsplit("/", 1)[-1] in READER_VIEWS
            write(target_file, _page(dst, menu=None if reader else menu))
        relative = "../" * src.count("/") + dst
        write(root / src, _stub(src, relative))
    return root


@pytest.fixture
def site(tmp_path: Path) -> Path:
    return plant(tmp_path / "site")


def _one(findings: list[str], needle: str) -> None:
    assert any(needle in line for line in findings), findings


# --- the one Pages workflow (Story 27.2; steward's duct since Epic 102) --------------------------------------------


def test_pages_yml_is_the_sole_deploy_pages_caller() -> None:
    hits = [
        path.name
        for path in sorted((REPO_ROOT / ".github" / "workflows").glob("*.yml"))
        if "deploy-pages@" in path.read_text(encoding="utf-8")
    ]
    assert hits == ["pages.yml"]


def test_pages_yml_builds_checks_and_uploads_the_one_artifact() -> None:
    text = (REPO_ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8")
    assert "pixi run --frozen -e site pages-check" in text
    assert "path: docs-site/build/site" in text
    assert "group: pages" in text
    assert re.search(r"push:\s*\n\s*branches:\s*\[main\]", text)
    for path in ("docs/how-to/**", "docs-site/**", "presentations/**"):
        assert f"'{path}'" in text
    assert "docsite" not in text.replace("docsite-check.yml", "")  # Story 43.7: one generator, docs-site/


# --- the planted artifact passes, and every finding names what broke ---------------------------------------------


def test_a_complete_artifact_passes(site: Path) -> None:
    assert pages_check(site) == []


def test_with_the_status_pages_flag_the_three_status_pages_pass(tmp_path: Path) -> None:
    root = plant(tmp_path / "site", status=True)
    assert pages_check(root, env={"PYFORGE_STATUS_PAGES": "1"}) == []


@pytest.mark.parametrize(
    "rel",
    [
        "index.html",
        "404.html",
        "herald/index.html",
        "herald/dossier/index.html",
        "herald/infographics/index.html",
        "herald/decks/index.html",
        "herald/artifact/dossier.html",
        "llms.txt",
        "llms-full.txt",
        "facts.json",
        "changes/index.html",
        "changes/rss.xml",
    ],
)
def test_ac7_every_required_path_is_named_when_missing(site: Path, rel: str) -> None:
    (site / rel).unlink()
    _one(pages_check(site, origins=False), f"missing required path {rel}")


def test_the_status_pages_follow_their_flag(tmp_path: Path) -> None:
    root = plant(tmp_path / "site", status=True)
    _one(pages_check(root, origins=False), "status/ exists in the artifact but pyforge.herald.status_pages is off")
    off = plant(tmp_path / "off")
    _one(pages_check(off, env={"PYFORGE_STATUS_PAGES": "1"}, origins=False), "missing required path status/index.html")


def test_the_dashboard_is_exactly_the_build_inputs_mount(site: Path, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    write(repo / "docs/dashboard/README.md", "# never mounted\n")
    write(repo / "docs/dashboard/fleet-board/index.html", "<p>board</p>\n")
    write(repo / "docs/dashboard/.vizro-old/index.html", "<p>a staging leftover: never mounted</p>\n")
    (repo / "docs/dashboard/vizro").mkdir()  # an export holding no file is absent
    _one(
        pages_check(site, repo_root=repo, origins=False),
        "docs/dashboard/ entries not mounted at dashboard/: fleet-board",
    )
    write(site / "dashboard/fleet-board/index.html", "<p>board</p>\n")
    assert pages_check(site, repo_root=repo, origins=False) == []
    write(site / "dashboard/index.html", _page("dashboard/index.html"))  # a page no input mounts: another writer
    _one(pages_check(site, repo_root=repo, origins=False), "collision at dashboard/: index.html")


def _mount_kedro_viz(site: Path, repo: Path, manifest: object, stub_target: str | None) -> None:
    for root in (site / "dashboard", repo / "docs" / "dashboard"):
        write(root / "kedro-viz/index.html", "<p>graph</p>\n")
        write(root / "kedro-viz/manifest.json", manifest if isinstance(manifest, str) else json.dumps(manifest))
    if stub_target is not None:
        write(site / "kedro-viz/index.html", _stub("kedro-viz/index.html", stub_target))


_GOOD_MANIFEST = {"export_commit": "0123456789abcdef", "export_date": "2026-10-15T09:23:50Z"}


@pytest.mark.parametrize(
    ("manifest", "stub", "finding"),
    [
        (_GOOD_MANIFEST, f"{BASE}dashboard/kedro-viz/", None),
        (_GOOD_MANIFEST, "../dashboard/kedro-viz/", None),
        (_GOOD_MANIFEST, "/dashboard/kedro-viz/", "kedro-viz/index.html does not redirect to dashboard/kedro-viz/"),
        (_GOOD_MANIFEST, None, "kedro-viz/index.html does not redirect to dashboard/kedro-viz/"),
        ({"export_commit": "0123"}, f"{BASE}dashboard/kedro-viz/", "lacks index.html or a manifest.json naming"),
        ("not json", f"{BASE}dashboard/kedro-viz/", "lacks index.html or a manifest.json naming"),
    ],
    ids=["base-absolute", "relative", "outside-the-base", "no-stub", "no-date", "not-json"],
)
def test_42_2_a_mounted_kedro_viz_export_needs_its_manifest_and_its_redirect(
    site: Path, tmp_path: Path, manifest: object, stub: str | None, finding: str | None
) -> None:
    repo = tmp_path / "repo"
    _mount_kedro_viz(site, repo, manifest, stub)
    findings = pages_check(site, repo_root=repo, origins=False)
    if finding is None:
        assert findings == []
    else:
        _one(findings, finding)


def test_42_2_no_kedro_viz_path_without_the_mount(site: Path) -> None:
    write(site / "kedro-viz/index.html", _stub("kedro-viz/index.html", "../dashboard/kedro-viz/"))
    findings = pages_check(site, origins=False)
    _one(findings, "kedro-viz/ exists in the artifact but no Kedro-Viz export is mounted")
    write(site / "herald/index.html", _page("herald/index.html", body='<a href="../dashboard/kedro-viz/">graph</a>'))
    _one(pages_check(site, origins=False), 'broken link: herald/index.html -> "../dashboard/kedro-viz/"')


@pytest.mark.parametrize("case", ["no-index", "no-manifest", "array-manifest", "good"])
def test_43_3_a_mounted_vizro_export_is_judged(site: Path, tmp_path: Path, case: str) -> None:
    repo = tmp_path / "repo"
    for root in (site / "dashboard" / "vizro", repo / "docs" / "dashboard" / "vizro"):
        if case != "no-index":
            write(root / "index.html", "<p>boards</p>\n")
        else:
            write(root / "estate/index.html", "<p>one board</p>\n")
        if case != "no-manifest":
            write(root / "manifest.json", "[]" if case == "array-manifest" else "{}")
    findings = pages_check(site, repo_root=repo, origins=False)
    if case == "good":
        assert findings == []
    else:
        _one(findings, "dashboard/vizro/ lacks index.html or a manifest.json object")


def test_43_3_every_legacy_redirect_lands_on_its_target(site: Path) -> None:
    write(site / "dossier/index.html", _stub("dossier/index.html", "../herald/decks/index.html"))
    _one(
        pages_check(site, origins=False),
        "legacy redirect /dossier/index.html does not land on /herald/dossier/index.html",
    )
    (site / "dossier/index.html").unlink()
    _one(pages_check(site, origins=False), "legacy redirect /dossier/index.html does not land on")


@pytest.mark.parametrize(
    ("feed", "facts", "finding"),
    [
        ('<rss version="2.0"><channel><title>a & b</title></channel></rss>', "{}", "changes/rss.xml is not"),
        ('<rss version="2.0"><channel><title>a&nbsp;b</title></channel></rss>', "{}", "changes/rss.xml is not"),
        ('<rss version="2.0"><channel><link href="a<b"/></channel></rss>', "{}", "changes/rss.xml is not"),
        ('<rss version="2.0"><channel><link href="a&b"/></channel></rss>', "{}", "changes/rss.xml is not"),
        ('<rss version="2.0"><channel></channel><channel></channel></rss>', "{}", "changes/rss.xml is not"),
        ("<feed><entry/></feed>", "{}", "changes/rss.xml is not"),
        ('<rss version="2.0"><channel><item></channel></rss>', "{}", "changes/rss.xml is not"),
        (RSS, "[]", "facts.json is not a JSON object"),
        (RSS, "{", "facts.json is not a JSON object"),
    ],
    ids=[
        "bare-ampersand",
        "html-entity",
        "lt-in-attribute",
        "ampersand-in-attribute",
        "two-channels",
        "atom",
        "unclosed",
        "array-facts",
        "broken-facts",
    ],
)
def test_43_6_the_machine_read_documents_parse(site: Path, feed: str, facts: str, finding: str) -> None:
    write(site / "changes/rss.xml", feed)
    write(site / "facts.json", facts)
    _one(pages_check(site, origins=False), finding)


def test_43_6_xml_s_five_entities_and_character_references_pass(site: Path) -> None:
    title = "a &amp; b &lt;c&gt; &quot;d&quot; &apos;e&apos; &#233; &#xE9;"
    write(site / "changes/rss.xml", RSS.replace("PyForge changes", title))
    assert pages_check(site, origins=False) == []


# --- every page: one CSP, one built-from line, one build ---------------------------------------------------------


@pytest.mark.parametrize("csp", ["", CSP + CSP])
def test_43_7_every_page_carries_one_csp(site: Path, csp: str) -> None:
    text = (site / "changes/index.html").read_text(encoding="utf-8").replace(CSP, csp)
    write(site / "changes/index.html", text)
    count = text.count("Content-Security-Policy")
    _one(pages_check(site, origins=False), f"changes/index.html carries {count} Content-Security-Policy metas, not one")


def _sha(text: str) -> str:
    return "'sha256-" + base64.b64encode(hashlib.sha256(text.encode("utf-8")).digest()).decode("ascii") + "'"


_SCRIPT = "document.documentElement.dataset.theme='dark'"
_HANDLER = "this.parentElement.classList.add('is-loaded')"


@pytest.mark.parametrize(
    ("rel", "policy", "body", "finding"),
    [
        ("herald/index.html", "default-src 'self'", f"<script>{_SCRIPT}</script>", "an inline <script> its CSP blocks"),
        (
            "changes/index.html",
            "default-src 'self'",
            f'<img onload="{_HANDLER}" src="x.png">',
            "an inline onload= handler",
        ),
        (
            "herald/decks/index.html",
            f"default-src 'self'; script-src 'self' {_sha(_HANDLER)}",
            f'<img onload="{_HANDLER}">',
            "an inline onload= handler its CSP blocks",
        ),  # a handler's hash needs 'unsafe-hashes'
        (
            "index.html",
            f"default-src 'self'; script-src 'self' 'unsafe-inline' {_sha('other()')}",
            f"<script>{_SCRIPT}</script>",
            "an inline <script> its CSP blocks",
        ),  # a hash in the list makes the browser ignore 'unsafe-inline'
        (
            "herald/dossier/index.html",
            f"default-src 'self'; script-src 'self' {_sha(_SCRIPT)}",
            "<script>other()</script>",
            f"({_sha('other()')} is not in its script-src)",
        ),
    ],
    ids=["herald-inline-script", "shelf-handler", "hash-without-unsafe-hashes", "unsafe-inline-ignored", "other-hash"],
)
def test_43_7_every_inline_script_and_handler_is_allowed_by_the_pages_own_csp(
    site: Path, rel: str, policy: str, body: str, finding: str
) -> None:
    """The CSP decision, enforced (the 43.7 review, F1): a page's inline scripts and ``on*=`` handlers each run under
    its own policy -- by hash, a handler's with ``'unsafe-hashes'`` -- or ``pages-check`` names the page."""
    meta = f'<meta http-equiv="Content-Security-Policy" content="{html.escape(policy)}">'
    page = _page(rel, body=body, shelf=not rel.startswith("herald/")).replace(CSP, meta)
    write(site / rel, page)
    findings = pages_check(site, origins=False)
    assert any(line.startswith(f"{rel} carries ") and finding in line for line in findings), findings


@pytest.mark.parametrize(
    ("policy", "body"),
    [
        (f"default-src 'self'; script-src 'self' {_sha(_SCRIPT)}", f"<script>{_SCRIPT}</script>"),
        (
            f"default-src 'self'; script-src 'self' 'unsafe-hashes' {_sha(_HANDLER)}",
            f'<img onload="{html.escape(_HANDLER)}" src="x.png">',
        ),
        ("default-src 'self'; script-src 'self' 'unsafe-inline'", f'<script>{_SCRIPT}</script><b onclick="go()">x</b>'),
        ("default-src 'self'", '<script type="application/ld+json">{"a": 1}</script><script src="x.js"></script>'),
    ],
    ids=["hashed-script", "hashed-handler", "unsafe-inline", "data-block-and-external"],
)
def test_43_7_allowed_scripts_and_data_blocks_pass(site: Path, policy: str, body: str) -> None:
    write(site / "changes/x.png", b"\x89PNG")
    write(site / "changes/x.js", "/* self */")
    meta = f'<meta http-equiv="Content-Security-Policy" content="{html.escape(policy)}">'
    write(site / "changes/index.html", _page("changes/index.html", body=body, shelf=True).replace(CSP, meta))
    assert pages_check(site, origins=False) == []


def test_43_7_stubs_twins_the_artifact_build_and_mounts_carry_no_csp_or_line(site: Path, tmp_path: Path) -> None:
    write(site / "herald/twins/infographics/alpha.html", "<html><body><p>a Design export</p></body></html>")
    write(site / "herald/artifact/dossier.html", "<title>t</title><p>no head, no line</p>")
    repo = tmp_path / "repo"
    for root in (site / "dashboard", repo / "docs" / "dashboard"):
        write(root / "fleet-board/index.html", "<html><p>steward's board</p></html>")
    assert pages_check(site, repo_root=repo, origins=False) == []


@pytest.mark.parametrize(
    ("rel", "edit", "finding"),
    [
        ("herald/index.html", lambda t: t.replace(LINE, ""), "herald/index.html carries 0 built-from lines, not one"),
        ("index.html", lambda t: t.replace(LINE, LINE + LINE), "index.html carries 2 built-from lines, not one"),
        (
            "status/ci/index.html",
            lambda t: t.replace("09:00 UTC", "10:00 UTC"),
            "the pages name 2 builds",
        ),
        ("herald/decks/pyforge-atlas/index.html", lambda t: t.replace(LINE, ""), "carries 0 built-from lines"),
    ],
    ids=["no-line", "two-lines", "two-builds", "family-page"],
)
def test_43_5_every_page_carries_one_line_naming_one_build(tmp_path: Path, rel: str, edit, finding: str) -> None:
    root = plant(tmp_path / "site", status=True)
    write(root / rel, edit((root / rel).read_text(encoding="utf-8")))
    _one(pages_check(root, env={"PYFORGE_STATUS_PAGES": "1"}, origins=False), finding)


def test_43_7_the_line_is_matched_as_built_from_ts_writes_it() -> None:
    """``pages-check`` and steward's tree hash read the element byte for byte (``BUILT_FROM_OPEN``): the check builds
    its pattern from the generator's own constant, and steward's ``BUILT_FROM_TEXT`` holds the same literal."""
    open_tag = ts(DOCS_SITE / "src" / "lib" / "built-from.ts", "return m.BUILT_FROM_OPEN;")
    assert open_tag == '<p class="built-from" data-pages-built-from data-pagefind-ignore>'
    assert "BUILT_FROM_OPEN" in PAGES_MTS.read_text(encoding="utf-8")
    steward = (REPO_ROOT / "src/shared/packages/pyforge-steward/src/pyforge/steward/pages.py").read_text(
        encoding="utf-8"
    )
    assert f"rb'({open_tag})[^<]*(</p>)'" in steward


def test_steward_writes_the_fleet_board_input_where_the_build_reads_it() -> None:
    """Steward's ``pages.FLEET_STATUS_REL`` (``steward pages build``'s output) is the file the generator reads: Story
    43.6's inputs directory (``agent-surface.ts``'s ``INPUTS_DIR_REL``) and the board's input name (``status.ts``'s
    ``FLEET_STATUS_INPUT``); the 43.7 review found only the workflow's ``--out`` pinned from both sides."""
    inputs = ts(DOCS_SITE / "src" / "lib" / "agent-surface.ts", "return m.INPUTS_DIR_REL;")
    name = ts(DOCS_SITE / "src" / "lib" / "status.ts", "return m.FLEET_STATUS_INPUT;")
    steward = (REPO_ROOT / "src/shared/packages/pyforge-steward/src/pyforge/steward/pages.py").read_text("utf-8")
    assert f'FLEET_STATUS_REL = "{inputs}/{name}"' in steward
    assert f"--out {inputs}/{name}" in (REPO_ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8")


# --- every link, every shelf body, one menu -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("rel", "href", "problem"),
    [
        ("herald/index.html", "dossier/missing.html", "resolves to nothing"),
        ("herald/index.html", "../../../etc/passwd", "escapes the artifact"),
        ("index.html", "/elsewhere/page/", "outside the base path /local-recipes/"),
        ("404.html", "tutorials/", "relative on the 404 page"),
        ("changes/index.html", "rss-missing.xml", "resolves to nothing"),
    ],
)
def test_44_1_every_local_link_resolves(site: Path, rel: str, href: str, problem: str) -> None:
    shelf = not rel.startswith("herald/")
    write(site / rel, _page(rel, body=f'<a href="{href}">x</a>', shelf=shelf))
    _one(pages_check(site, origins=False), f"broken link: {rel} -> {json.dumps(href)} ({problem}")


@pytest.mark.parametrize(
    "body",
    [
        '<a href="https://example.com/page">another site</a>',
        '<a href="#top">a fragment</a>',
        '<a href="mailto:x@example.com">mail</a>',
        f'<a href="{BASE}herald/decks/">base-absolute</a>',
        '<a href="../herald/dossier/index.html#sec">with a fragment</a>',
        '<img src="data:image/png;base64,AAAA" alt="">',
    ],
)
def test_44_1_links_that_name_no_file_of_the_artifact_pass(site: Path, body: str) -> None:
    write(site / "changes/index.html", _page("changes/index.html", body=body, shelf=True))
    assert pages_check(site, origins=False) == []


def test_44_1_a_percent_encoded_link_and_a_srcset_resolve(site: Path) -> None:
    write(site / "herald/decks/pyforge-atlas/downloads/A Deck.pptx", b"PK")
    body = '<a href="pyforge-atlas/downloads/A%20Deck.pptx">dl</a><img srcset="missing.png 1x, other.png 2x" alt="">'
    write(site / "herald/decks/index.html", _page("herald/decks/index.html", body=body))
    findings = pages_check(site, origins=False)
    assert [f for f in findings if "A%20Deck" in f] == []
    _one(findings, 'broken link: herald/decks/index.html -> "missing.png"')


def test_a_malformed_percent_encoding_is_named_not_a_crash(site: Path) -> None:
    write(site / "changes/index.html", _page("changes/index.html", body='<a href="a%zz.html">x</a>', shelf=True))
    _one(
        pages_check(site, origins=False), 'broken link: changes/index.html -> "a%zz.html" (malformed percent-encoding)'
    )


def test_an_artifact_with_no_shelf_page_fails(site: Path) -> None:
    """The retired ``_check_shelf_pages``' first refusal, restored (the 43.7 review, nit 5)."""
    for rel in ("index.html", "404.html", "changes/index.html"):
        write(site / rel, _page(rel))
    _one(pages_check(site, origins=False), "no shelf page found")


@pytest.mark.parametrize("href", ["#", "#top", "", "https://example.com/elsewhere/"])
def test_a_menu_link_must_land_on_a_file_of_the_artifact(site: Path, href: str) -> None:
    """The retired ``_menu_target`` refusal, restored (the 43.7 review, nit 5): an empty, fragment-only or off-site
    menu link points at no page of the site, though the labels match the docs root's."""
    text = _page("changes/index.html", shelf=True).replace(f'href="{BASE}changes/"', f'href="{href}"', 1)
    write(site / "changes/index.html", text)
    _one(
        pages_check(site, origins=False),
        f"menu link lands on no file of the artifact: changes/index.html -> {json.dumps(href)}",
    )


def test_the_family_pages_the_decks_index_links_are_required(site: Path) -> None:
    """AC7 in CI (the 43.7 review, nit 6): ``pages-check`` requires every family page the decks index links, and a
    decks index that links none."""
    body = FAMILY_LINK + f'<a href="{BASE}herald/decks/pyforge-zz/">Z</a><a href="pyforge-atlas/downloads/a.md">dl</a>'
    write(site / DECKS, _page(DECKS, body=body))
    _one(pages_check(site, origins=False), "missing required path herald/decks/pyforge-zz/index.html")
    write(site / DECKS, _page(DECKS))
    _one(pages_check(site, origins=False), "herald/decks/index.html links no family page")


@pytest.mark.parametrize(
    ("body", "empty"),
    [
        ("", True),
        ("<div><div><p>Nested words.</p></div></div>", False),
    ],
    ids=["empty", "nested"],
)
def test_44_1_every_shelf_page_renders_a_body(site: Path, body: str, empty: bool) -> None:
    text = f"<!doctype html><html><head>{CSP}</head><body>{_menu('index.html', MENU)}"
    text += f'<div class="sl-markdown-content">{body}</div><footer><a href="{BASE}">Previous page</a></footer>{LINE}'
    write(site / "index.html", text + "</body></html>")
    findings = pages_check(site, origins=False)
    assert ("empty shelf page body: index.html" in findings) is empty, findings


@pytest.mark.parametrize(
    "rel", ["herald/dossier/index.html", "changes/index.html", "herald/decks/pyforge-atlas/index.html"]
)
def test_40_1_every_navigable_page_carries_the_docs_roots_menu(site: Path, rel: str) -> None:
    shelf = not rel.startswith("herald/")
    write(site / rel, _page(rel, menu=MENU[:-1], shelf=shelf))
    _one(pages_check(site, origins=False), f"the menu on {rel} reads")


def test_43_2_a_reader_page_carries_no_menu(site: Path) -> None:
    rel = "herald/infographics/atlas.html"
    assert not (site / rel).read_text(encoding="utf-8").count("data-pf-menu-link")
    assert pages_check(site, origins=False) == []


def test_43_4_a_herald_page_carries_no_inline_theme(site: Path) -> None:
    write(site / "herald/index.html", _page("herald/index.html", body="<style>:root{--sl-color-black:#000}</style>"))
    _one(pages_check(site, origins=False), "herald/index.html carries an inline theme")


def test_43_4_every_face_is_a_file_under_the_bundle(site: Path) -> None:
    write(site / "_astro/plex.woff2", b"wOF2")
    write(site / "_astro/site.css", f"@font-face{{font-family:X;src:url({BASE}_astro/plex.woff2) format('woff2')}}")
    assert pages_check(site, origins=False) == []
    write(site / "herald/fonts/plex.woff2", b"wOF2")
    write(site / "_astro/site.css", "@font-face{font-family:X;src:url(../herald/fonts/plex.woff2)}")
    _one(
        pages_check(site, origins=False),
        '_astro/site.css loads a face "../herald/fonts/plex.woff2" that is not a file under _astro/',
    )


# --- nothing loads from another origin (scripts/origin_check.py) --------------------------------------------------


@pytest.mark.parametrize(
    ("rel", "body", "url"),
    [
        ("herald/index.html", '<script src="https://cdn.example.com/a.js"></script>', "https://cdn.example.com/a.js"),
        (
            "changes/index.html",
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2">',
            "fonts.googleapis.com",
        ),
        ("index.html", "<style>@import url('https://fonts.googleapis.com/x');</style>", "fonts.googleapis.com"),
    ],
)
def test_31_1_a_load_from_another_origin_fails(site: Path, rel: str, body: str, url: str) -> None:
    write(site / rel, _page(rel, body=body, shelf=not rel.startswith("herald/")))
    findings = pages_check(site)
    assert any(rel in line and url in line and "another origin" in line for line in findings), findings


def test_43_3_the_vendored_paths_are_exempt_by_name_and_their_siblings_judged(site: Path, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    for root in (site / "dashboard", repo / "docs" / "dashboard"):
        write(root / "kedro-viz/index.html", '<script src="https://cdn.example.com/k.js"></script>')
        write(root / "kedro-viz/manifest.json", json.dumps(_GOOD_MANIFEST))
        write(root / "vizro/index.html", "<p>boards</p>")
        write(root / "vizro/manifest.json", "{}")
        write(root / "vizro/assets/plotly.min.js", "fetch('https://cdn.plot.ly/world_110m.json');")
    write(site / "kedro-viz/index.html", _stub("kedro-viz/index.html", "../dashboard/kedro-viz/"))
    assert pages_check(site, repo_root=repo) == []
    for root in (site / "dashboard", repo / "docs" / "dashboard"):
        write(root / "vizro/assets/other.js", "fetch('https://cdn.plot.ly/world_110m.json');")
    _one(pages_check(site, repo_root=repo), "dashboard/vizro/assets/other.js: loads")


def test_43_3_on_a_second_host_a_link_to_the_public_host_fails(site: Path) -> None:
    write(site / ".pages-build-site-url", "https://pages.example.com/docs\n")
    for rel in [p.relative_to(site).as_posix() for p in site.rglob("*.html")]:
        write(site / rel, (site / rel).read_text(encoding="utf-8").replace(BASE, "/docs/"))
    text = (site / "index.html").read_text(encoding="utf-8")
    write(site / "index.html", text.replace("<main>", f'<main><a href="{SITE_URL}/herald/">public</a>'))
    assert pages_check(site, origins=False) == []  # the link names no file of this artifact
    _one(pages_check(site), "links 'https://rxm7706.github.io/local-recipes/herald/' on the other host")


# --- pages-build: the site URL and the one build time --------------------------------------------------------------

_BUILT_AT = """
return inp.times.map((t) => {
  try {
    return m.builtFromText({ GITHUB_SHA: '0123456789abcdef', GITHUB_RUN_ID: '7', PAGES_BUILT_AT: t });
  } catch (exc) {
    return `refused: ${exc.message}`;
  }
});
"""


@pytest.mark.parametrize(
    ("built_at", "line"),
    [
        ("2026-10-15T09:00:00Z", "Built from 0123456 · 2026-10-15 09:00 UTC · run 7"),
        ("2026-10-15T14:30:59.123+05:30", "Built from 0123456 · 2026-10-15 09:00 UTC · run 7"),
        ("2024-02-29T00:00:00Z", "Built from 0123456 · 2024-02-29 00:00 UTC · run 7"),
        (" 2026-10-15T09:00:00Z\n", "Built from 0123456 · 2026-10-15 09:00 UTC · run 7"),
        ("2026-02-30T00:00:00Z", None),
        ("2026-02-29T00:00:00Z", None),
        ("2026-13-01T00:00:00Z", None),
        ("0000-01-01T00:00:00Z", None),
        ("﻿2026-10-15T09:00:00Z", None),
        ("2026-10-15T09:00:00", None),
        ("2026-10-15t09:00:00z", None),
        ("2026-10-15", None),
    ],
    ids=[
        "utc",
        "offset",
        "leap-day",
        "whitespace",
        "feb-30",
        "feb-29-common-year",
        "month-13",
        "year-0000",
        "bom",
        "naive",
        "lower-case",
        "date-only",
    ],
)
def test_43_5_the_build_time_is_a_real_iso_instant_with_an_offset(built_at: str, line: str | None) -> None:
    """``PAGES_BUILT_AT`` as the retired Python twin read it (``datetime.fromisoformat``, Story 43.5; the re-review's
    nit 3): ``Date`` alone rolls February 30 into March, reads year 0000 and trims a byte-order mark away."""
    [said] = ts(DOCS_SITE / "src" / "lib" / "built-from.ts", _BUILT_AT, times=[built_at])
    if line is None:
        assert said.startswith("refused: PAGES_BUILT_AT is not an ISO 8601 time with an offset"), said
    else:
        assert said == line


def test_43_5_the_build_time_is_set_once_in_the_builds_own_environment() -> None:
    """Story 43.5's carry-in: ``PAGES_BUILT_AT`` is made once and handed to the build's environment, never written into
    this process's (an in-process caller leaks nothing)."""
    source = PAGES_MTS.read_text(encoding="utf-8")
    assert re.search(r"env: \{ \.\.\.env, SITE_URL: siteUrl, PAGES_BUILT_AT: builtAt \}", source)
    assert not re.search(r"process\.env(\.\w+|\[[^\]]+\])\s*=", source)
    assert not re.search(r"process\.env(\.\w+|\[[^\]]+\])\s*=", (DOCS_SITE / "astro.config.mjs").read_text("utf-8"))


def test_44_1_the_link_plugins_are_wired_and_two_are_vendored() -> None:
    config = (DOCS_SITE / "astro.config.mjs").read_text(encoding="utf-8")
    for name in ("rehypeShelfLinks", "rehypeMarkdownLinks", "rehypeBasePaths"):
        assert f"[{name}" in config, name
    assert config.index("[rehypeShelfLinks") < config.index("[rehypeMarkdownLinks") < config.index("[rehypeBasePaths")
    readme = (DOCS_SITE / "README.md").read_text(encoding="utf-8")
    for vendored in ("src/rehype-markdown-links.js", "src/rehype-base-paths.js"):
        assert f"`{vendored}`" in readme, vendored
    loader = (DOCS_SITE / "src" / "loaders" / "shelf-docs-loader.ts").read_text(encoding="utf-8")
    assert "rendered: await renderMarkdown(" in loader


def test_43_3_the_origin_check_stays_small() -> None:
    """AC5's "under 40 lines" held until 43.3's second review (html.parser, so attribute values decode and code samples
    load nothing: 64 lines); Story 43.7 gave it a command line, ``pages.mts`` running it (73). It counts toward the
    bespoke-Python budget under ``docs-site/`` (AD-23, under 300) and does not grow."""
    assert len((DOCS_SITE / "scripts" / "origin_check.py").read_text(encoding="utf-8").splitlines()) <= 73
