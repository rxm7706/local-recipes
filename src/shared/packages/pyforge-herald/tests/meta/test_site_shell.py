"""The Pages site reads as one product (Stories 53.1 and 53.2, spec-pyforge-herald CAP-63; FR-15.1, FR-15.2).

One build of the tracked tree with ``pyforge.herald.site_shell`` on (``PYFORGE_SITE_SHELL=1``), the status pages and
the marketplace mount, read page by page: the one header, a ``<main>`` and a skip link on every page the site serves;
dark for a reader who stored no theme; a description behind every door; closed sidebar groups; and, with or without
the flag, tables that reflow on a phone, dates a person reads, and pages, frames and labels that name themselves. The
flag-off shells are what every other built-site module of this suite builds and pins.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest
import yaml
from pages_astro import DOCS_SITE, REPO_ROOT, astro_build, needs_astro, needs_node, pages_check, ts

# This module reads the live tree outside its package (docs-site/, docs/), so it runs in herald's live-tree half.
pytestmark = pytest.mark.live_tree

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
SHELL_ENV = {"PYFORGE_SITE_SHELL": "1", "PYFORGE_STATUS_PAGES": "1", "PYFORGE_MARKETPLACE_PAGES": "1"}
_CI = {"GITHUB_SHA": "0123456789abcdef0123", "GITHUB_RUN_ID": "111", "PAGES_BUILT_AT": "2026-10-15T09:00:00Z"}
#: Output the header is never asked of: the authored twins, the artifact build, the search bundle, upstream's app.
NO_SHELL = ("herald/twins/", "herald/artifact/", "dashboard/kedro-viz/", "pagefind/")
SITE_HEADER = DOCS_SITE / "src" / "lib" / "site-header.ts"
READER_TEXT = DOCS_SITE / "src" / "lib" / "reader-text.ts"
SHELL = DOCS_SITE / "src" / "lib" / "shell.ts"
ISO_TEXT = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d")
STORY_ID = re.compile(r"\b(?:Story|Epic)\s+\d+(?:\.\d+)?\b|\bCAP-\d+\b")


def _inputs(directory: Path) -> Path:
    sources = {
        "fleet-status.json": FIXTURES / "fleet-status-2026-10-14.json",
        "changes.json": FIXTURES / "changes-five-merges.json",
        "marshal-status.json": FIXTURES / "marshal-status-two-homes.json",
        "herald-progress.json": FIXTURES / "herald-progress-records.json",
    }
    directory.mkdir(parents=True, exist_ok=True)
    for name, source in sources.items():
        shutil.copyfile(source, directory / name)
    return directory


@pytest.fixture(scope="module")
def shell(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The tracked tree built with the site shell, the status pages and the marketplace on."""
    tmp = tmp_path_factory.mktemp("site-shell")
    out = tmp / "site"
    done = astro_build(out, status=True, tile=True, inputs=_inputs(tmp / "inputs"), extra_env={**_CI, **SHELL_ENV})
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-3000:]
    return out


def _pages(root: Path) -> dict[str, str]:
    """Every HTML page the site serves, by path: no redirect stub and nothing under ``NO_SHELL``."""
    pages: dict[str, str] = {}
    for file in sorted(root.rglob("*.html")):
        rel = file.relative_to(root).as_posix()
        if rel.startswith(NO_SHELL):
            continue
        text = file.read_text(encoding="utf-8")
        if re.search(r'<meta\s+http-equiv=["\']refresh["\']', text, re.I):
            continue
        pages[rel] = text
    return pages


def _sections() -> list[dict]:
    return yaml.safe_load((REPO_ROOT / "docs" / "map.yaml").read_text(encoding="utf-8"))["sections"]


# ------------------------------------------------------------------ Story 53.1: the one header


@needs_astro
def test_53_1_every_served_page_holds_the_one_header_a_main_and_a_skip_link(shell: Path) -> None:
    pages = _pages(shell)
    assert {"index.html", "herald/index.html", "herald/dossier/index.html", "status/index.html"} <= set(pages)
    assert any(rel.startswith("marketplace/") for rel in pages), "the marketplace mount is in the build"
    assert any(re.fullmatch(r"herald/infographics/[^/]+\.html", rel) for rel in pages), "a reader page is in the build"
    for rel, text in pages.items():
        assert len(re.findall(r"\bdata-pf-header\b", text)) == 1, f"{rel}: not exactly one site header"
        assert len(re.findall(r"<main\b", text, re.I)) == 1, f"{rel}: not exactly one <main>"
        assert re.search(r'<a\b[^>]*href="#[^"]+"[^>]*>\s*Skip to content\s*</a>', text), f"{rel}: no skip link"
        assert "data-pf-theme" in text, f"{rel}: no theme toggle"
        assert "data-pf-search" in text or "<site-search" in text, f"{rel}: no search control"
        assert "pf-shell.js" in text, f"{rel}: the header's script is not loaded"
    assert (shell / "pf-shell.js").is_file()


@needs_astro
def test_53_1_every_page_carries_the_same_menu_grouped_by_section(shell: Path) -> None:
    menus = {}
    for rel, text in _pages(shell).items():
        header = text[text.index("data-pf-header") :]
        header = header[: header.index("pf-tools")]
        menus[rel] = re.findall(r"<a data-pf-menu-link [^>]*>([^<]+)</a>", header)
    labels = menus["index.html"]
    assert labels[0] == "Docs" and {"Overview", "Dossier", "Infographics", "Decks", "Status", "Changes"} <= set(labels)
    assert all(menu == labels for menu in menus.values()), "a page lists another menu"
    home = (shell / "index.html").read_text(encoding="utf-8")
    assert re.search(r'<li class="pf-group"><details[^>]*><summary>Herald</summary>', home), "Herald is not a group"


@needs_astro
def test_53_1_pages_check_passes_and_names_a_page_without_the_header(shell: Path, tmp_path: Path) -> None:
    env = {**SHELL_ENV, "SITE_URL": "https://rxm7706.github.io/local-recipes"}
    assert pages_check(shell, env=env, repo_root=REPO_ROOT) == []
    broken = tmp_path / "site"
    shutil.copytree(shell, broken)
    page = broken / "herald" / "decks" / "index.html"
    page.write_text(page.read_text(encoding="utf-8").replace("data-pf-header", "data-pf-gone"), encoding="utf-8")
    findings = pages_check(broken, env=env, repo_root=REPO_ROOT)
    assert any("herald/decks/index.html carries 0 site headers" in line for line in findings), findings


@needs_astro
def test_53_1_a_page_with_no_stored_theme_resolves_to_dark(shell: Path) -> None:
    for rel, text in _pages(shell).items():
        scripts = "".join(re.findall(r"<script\b(?![^>]*\bsrc=)[^>]*>(.*?)</script>", text, re.S))
        assert "prefers-color-scheme: light" not in scripts or "||'dark'" in scripts, f"{rel}: the system picks"
        assert "'dark'" in scripts, f"{rel}: no theme rule"
        assert "m.matches?'light':'dark'" not in scripts, f"{rel}: a reader with no stored theme gets the system's"


@needs_node
def test_53_1_the_theme_script_falls_back_to_dark_only_with_the_shell() -> None:
    on = ts(SITE_HEADER, "return m.themeScript(true)")
    off = ts(SITE_HEADER, "return m.themeScript(false)")
    assert isinstance(on, str) and isinstance(off, str)
    assert "(s()||'dark')" in on and "matches?'light':'dark'" not in on
    assert "(s()||(m.matches?'light':'dark'))" in off


@needs_astro
def test_53_1_every_door_says_what_is_behind_it(shell: Path) -> None:
    site = yaml.safe_load((DOCS_SITE / "src" / "content" / "site.yml").read_text(encoding="utf-8"))
    for section in _sections():
        assert str(site["doors"].get(section["key"], "")).strip(), f"site.yml doors has no line for {section['key']}"
    home = (shell / "index.html").read_text(encoding="utf-8")
    doors = re.findall(r"<div class=\"pf-door[^>]*data-pf-door=\"([^\"]*)\"[^>]*>(.*?)</div>", home, re.S)
    assert len(doors) >= 4, doors
    for path, body in doors:
        assert re.search(r"<p[^>]*data-pf-door-about[^>]*>[^<]{20,}</p>", body), f"the door to {path!r} says nothing"


@needs_astro
def test_53_1_sidebar_groups_other_than_the_current_pages_start_closed(shell: Path) -> None:
    page = (shell / "how-to" / "pixi-tasks" / "index.html").read_text(encoding="utf-8")
    sidebar = page[page.index('class="sidebar-content') :]
    sidebar = sidebar[: sidebar.index("</nav>")]
    groups = re.findall(r"<details\b([^>]*)>\s*<summary[^>]*>.*?<span[^>]*>([^<]+)</span>", sidebar, re.S)
    state = {label.strip(): " open" in attrs or attrs.strip().startswith("open") for attrs, label in groups}
    assert state.get("How-to") is True, state
    assert [label for label, is_open in state.items() if is_open] == ["How-to"], state


@needs_node
def test_53_1_a_mounted_page_gets_the_header_once_and_keeps_its_own_main() -> None:
    sections = json.dumps(_sections())
    plain = "<!doctype html><html><head><title>t</title></head><body><h1>Boards</h1></body></html>"
    once = ts(
        SHELL,
        f"return m.withShell(inp.html, 'dashboard/vizro/a/index.html', 'dashboard/vizro/', {sections})",
        html=plain,
    )
    assert isinstance(once, str)
    assert once.count("data-pf-header") == 1 and '<main id="pf-main" class="pf-mounted"><h1>Boards</h1></main>' in once
    assert 'href="../../../herald/theme.css"' in once and 'src="../../../pf-shell.js"' in once
    assert 'href="../../../dashboard/vizro/" aria-current="true"' in once  # a page under the section, not the section
    again = ts(
        SHELL,
        f"return m.withShell(inp.html, 'dashboard/vizro/a/index.html', 'dashboard/vizro/', {sections})",
        html=once,
    )
    assert again is None, "a page that has the header is left as it is"
    own = plain.replace("<h1>Boards</h1>", "<main><h1>Boards</h1></main>")
    kept = ts(SHELL, f"return m.withShell(inp.html, 'marketplace/index.html', 'marketplace/', {sections})", html=own)
    assert isinstance(kept, str) and len(re.findall(r"<main\b", kept)) == 1 and '<div id="pf-main"' in kept


def test_53_1_the_shell_names_no_colour_and_no_face_of_its_own() -> None:
    css = (DOCS_SITE / "src" / "styles" / "shell.css").read_text(encoding="utf-8")
    rules = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(", rules), "a colour literal in shell.css"
    assert not re.search(r"--sl-[a-z0-9-]+\s*:", rules), "shell.css sets a theme variable"
    for family in re.findall(r"font(?:-family)?\s*:\s*([^;]+);", rules):
        assert family.strip() == "inherit" or family.strip().startswith("var(--sl-font"), family


# ------------------------------------------------------------------ Story 53.2: phone width, and pages that name themselves


@needs_astro
def test_53_2_the_status_tables_reflow_on_a_phone(shell: Path) -> None:
    css = re.sub(r"/\*.*?\*/", "", (DOCS_SITE / "src" / "styles" / "shell.css").read_text(encoding="utf-8"), flags=re.S)
    phone = "".join(re.findall(r"@media \(max-width: 49\.99rem\) \{(.*?)\n\}", css, re.S))
    assert "table.status-table tr" in phone and "display: block" in phone, "no phone layout for the status tables"
    assert "content: attr(data-label)" in phone, "a cell loses its column's name on a phone"
    for rel, columns in (("status/index.html", 7), ("status/ci/index.html", 7)):
        page = (shell / rel).read_text(encoding="utf-8")
        table = page[page.index('<table class="status-table') :]
        table = table[: table.index("</table>")]
        heads = re.findall(r"<th>([^<]+)</th>", table[: table.index("</thead>")])
        assert len(heads) == columns, heads
        rows = re.findall(r"<tr\b[^>]*>(.*?)</tr>", table[table.index("<tbody") :], re.S)
        assert rows, rel
        for row in rows:
            assert len(re.findall(r'<th scope="row"', row)) == 1, f"{rel}: a row has no heading cell"
            assert re.findall(r'<td data-label="([^"]+)"', row) == heads[1:], f"{rel}: a cell is unlabelled"


@needs_astro
def test_53_2_a_printed_time_is_a_date_a_person_reads(shell: Path) -> None:
    seen = 0
    for rel, text in _pages(shell).items():
        if rel.startswith(("marketplace/", "dashboard/")):
            continue  # another station's markup (steward Story 130.2, atlas Story 49.1)
        for attrs, shown in re.findall(r"<time\b([^>]*)>([^<]*)</time>", text):
            seen += 1
            assert "datetime=" in attrs, f"{rel}: a <time> with no datetime"
            assert not ISO_TEXT.search(shown), f"{rel}: prints {shown!r}"
    assert seen >= 3, "the status, CI and changes pages each print a time"


@needs_node
@pytest.mark.parametrize(
    ("iso", "shown"),
    [
        ("2026-11-21T10:35:33-06:00", "21 Nov 2026, 10:35 UTC-06:00"),
        ("2026-11-13T09:18:26.260843+00:00", "13 Nov 2026, 09:18 UTC"),
        ("2026-10-15T09:00:00Z", "15 Oct 2026, 09:00 UTC"),
        ("2026-10-05", "5 Oct 2026"),
        ("not a date", "not a date"),
    ],
)
def test_53_2_readable_date_reads_the_string_never_the_hosts_zone(iso: str, shown: str) -> None:
    assert ts(READER_TEXT, "return m.readableDate(inp.iso)", iso=iso) == shown


@needs_node
@pytest.mark.parametrize(
    ("title", "shown"),
    [
        ("PostgreSQL restore runbook (steward Story 41.1)", "PostgreSQL restore runbook"),
        ("OpenShift Local cluster bring-up (Story 12.4 / CAP-1)", "OpenShift Local cluster bring-up"),
        ("Host Nebari (NKP on kind)", "Host Nebari (NKP on kind)"),
        ("Pixi tasks", "Pixi tasks"),
    ],
)
def test_53_2_reader_title_drops_only_the_story_a_page_was_filed_under(title: str, shown: str) -> None:
    assert ts(READER_TEXT, "return m.readerTitle(inp.title)", title=title) == shown


@needs_astro
def test_53_2_no_sidebar_label_prints_a_story_id(shell: Path) -> None:
    page = (shell / "how-to" / "pixi-tasks" / "index.html").read_text(encoding="utf-8")
    sidebar = page[page.index('class="sidebar-content') :]
    sidebar = sidebar[: sidebar.index("</nav>")]
    labels = [label.strip() for label in re.findall(r"<span[^>]*>([^<]+)</span>", sidebar)]
    assert len(labels) > 50, len(labels)
    assert not [label for label in labels if STORY_ID.search(label)]


@needs_astro
def test_53_2_every_gallery_frame_has_a_title(shell: Path) -> None:
    frames = 0
    for rel in ("herald/infographics/index.html", "herald/decks/index.html"):
        for attrs in re.findall(r"<iframe\b([^>]*)>", (shell / rel).read_text(encoding="utf-8")):
            frames += 1
            assert re.search(r'\btitle="[^"]+"', attrs), f"{rel}: a frame with no title"
    assert frames >= 10, frames


@needs_astro
def test_53_2_every_page_has_one_h1_and_herald_s_pages_a_description(shell: Path) -> None:
    for rel, text in _pages(shell).items():
        assert len(re.findall(r"<h1\b", text, re.I)) == 1, f"{rel}: not exactly one h1"
        if rel.startswith(("marketplace/", "dashboard/")):
            continue  # the description is the mounting station's (steward Story 130.2)
        assert re.search(r'<meta name="description" content="[^"]+', text), f"{rel}: no description"


@needs_node
def test_53_2_first_paragraph_skips_what_is_not_prose_and_cuts_at_a_word() -> None:
    body = "| a | b |\n|---|---|\n\n```bash\npixi run x\n```\n\nRun the **gate** with [`pixi`](https://pixi.sh) first.\n\nMore."
    assert ts(READER_TEXT, "return m.firstParagraph(inp.body)", body=body) == "Run the gate with pixi first."
    long = ts(READER_TEXT, "return m.firstParagraph(inp.body, 60)", body="word " * 40)
    assert isinstance(long, str) and len(long) <= 60 and long.endswith("…") and not long[:-1].endswith(" ")  # noqa: PLR2004
    assert ts(READER_TEXT, "return m.firstParagraph(inp.body)", body="- a list\n- only") == ""


@needs_node
def test_53_1_the_header_marks_the_page_itself_and_the_section_above_a_deeper_page() -> None:
    sections = json.dumps(_sections())
    call = f"return m.siteHeaderHtml({sections}, {{ toRoot: '../', pagePath: inp.page }})"
    here = ts(SITE_HEADER, call, page="status/")
    deeper = ts(SITE_HEADER, call, page="status/ci/")
    assert isinstance(here, str) and isinstance(deeper, str)
    assert 'href="../status/" aria-current="page"' in here
    assert 'href="../status/" aria-current="true"' in deeper and 'aria-current="page"' not in deeper


@needs_node
def test_53_1_enter_in_the_search_box_submits_no_form_and_a_result_is_never_set_as_html() -> None:
    header = ts(SITE_HEADER, f"return m.siteHeaderHtml({json.dumps(_sections())}, {{ toRoot: '', pagePath: '' }})")
    assert isinstance(header, str)
    dialog = header[header.index("<dialog") : header.index("</dialog>")]
    form = dialog[dialog.index("<form") : dialog.index("</form>")]
    assert "<input" in dialog and "<input" not in form, "the search box sits in the form its Close button submits"
    script = ts(SITE_HEADER, "return m.SHELL_SCRIPT_SOURCE")
    assert isinstance(script, str)
    assert "x.excerpt+" not in script and "+x.excerpt" not in script, "an excerpt is concatenated into HTML"
    assert "t.innerHTML=x.excerpt" in script and "textContent" in script  # parsed inert, rebuilt as text and <mark>


@needs_node
def test_53_1_with_shell_cuts_at_the_last_body_close_of_the_page_as_written() -> None:
    sections = json.dumps(_sections())
    odd = "<!doctype html><html><head><title>t</title></head><BODY class=x><p>İstanbul</p><script>var s='</body>';</script></BODY></html>"
    out = ts(SHELL, f"return m.withShell(inp.html, 'marketplace/index.html', 'marketplace/', {sections})", html=odd)
    assert isinstance(out, str)
    assert out.endswith("<script>var s='</body>';</script></main></BODY></html>"), out[-120:]
    assert out.count("data-pf-header") == 1 and "<p>İstanbul</p>" in out


@needs_astro
def test_53_2_no_status_badge_prints_a_story_id(shell: Path) -> None:
    badges = 0
    for rel in ("status/index.html", "status/ci/index.html", "status/runs/index.html"):
        page = (shell / rel).read_text(encoding="utf-8")
        for text in re.findall(r'<span class="sl-badge[^"]*"[^>]*>([^<]*)</span>', page):
            badges += 1
            assert not STORY_ID.search(text), f"{rel}: a badge prints {text!r}"
    assert badges > 10, badges  # noqa: PLR2004


@needs_astro
def test_53_2_a_reader_page_has_its_h1_with_the_shell_off_too(tmp_path: Path) -> None:
    out = tmp_path / "site"
    done = astro_build(out, status=True, tile=True, inputs=_inputs(tmp_path / "inputs"), extra_env=_CI)
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-3000:]
    readers = sorted((out / "herald" / "infographics").glob("*.html"))
    readers = [page for page in readers if page.name != "index.html"]
    assert readers
    for page in readers:
        text = page.read_text(encoding="utf-8")
        assert "data-pf-header" not in text, f"{page.name}: the header reached a build with the flag off"
        assert len(re.findall(r"<h1\b", text)) == 1, f"{page.name}: not exactly one h1"
    assert not (out / "pf-shell.js").exists()
