"""Story 43.7 (spec-pyforge-herald CAP-61, AD-23): ``docsite/`` retires and one generator remains.

The tree half runs everywhere: ``docsite/`` is gone (AC1), nothing in the generator names it (AC2), the ``site*``
tasks are gone and ``pages-check`` is the one build check (AC4), the one-generator flag left the tree with no reader
(AC5), the bespoke Python under ``docs-site/`` is under 300 lines (AC6), ``AGENTS.md`` cites the dossier where it
lives (AC9). The built half needs docs-site installed (``pixi run -e site docs-site-install``) and skips naming it
otherwise: the tracked tree built with the status pages on holds every URL of AC7 and passes ``pages-check``, loads
no font or script from a CDN (AC8), gives every page one CSP (the CSP decision), carries the artifact build of the
dossier and the font licences, lists every gallery and family page in ``/llms.txt``, and a second build two days,
two runs and two commits later differs only in the built-from line (Story 43.5's proof over the whole artifact).
Story 43.5's measured-dossier tests moved here from the retired parity test.
"""

from __future__ import annotations

import base64
import difflib
import gzip
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
import yaml
from pages_astro import (
    DOCS_SITE,
    DOSSIER_REL,
    REPO_ROOT,
    astro_build,
    fixture_tree,
    needs_astro,
    needs_node,
    pages_check,
    station_packages,
    ts,
    write,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
REDIRECTS = json.loads((DOCS_SITE / "redirects.json").read_text(encoding="utf-8"))
SITE = yaml.safe_load((DOCS_SITE / "src" / "content" / "site.yml").read_text(encoding="utf-8"))
#: The ten families: one per gallery infographic under presentations/<slug>/ (site.yml's include list).
FAMILIES = sorted({glob.split("/")[1] for glob in SITE["infographics"]["include"]})
STATUS_ENV = {"PYFORGE_STATUS_PAGES": "1"}
_FLAG_KEY = "pyforge.herald." + "pages_one_generator"  # the retired key, never named whole outside tests
_BUILT_FROM_TEXT = re.compile(rb'(<p class="built-from" data-pages-built-from data-pagefind-ignore>)[^<]*(</p>)')


# --- the tree -----------------------------------------------------------------------------------------------------


def _tracked(*paths: str) -> list[str]:
    done = subprocess.run(
        ["git", "ls-files", "-z", "--", *paths], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    )
    return [rel for rel in done.stdout.split("\0") if rel and (REPO_ROOT / rel).is_file()]


def test_ac1_docsite_is_gone() -> None:
    assert not (REPO_ROOT / "docsite").exists()
    tracked = subprocess.run(["git", "ls-files", "docsite"], cwd=REPO_ROOT, capture_output=True, text=True, check=True)
    assert tracked.stdout == ""


def test_ac2_the_content_lives_beside_the_generator_and_nothing_names_docsite() -> None:
    assert (REPO_ROOT / DOSSIER_REL).is_file()
    loader = (DOCS_SITE / "src" / "loaders" / "dossier-loader.ts").read_text(encoding="utf-8")
    assert "docs-site/src/content/dossier/dossier.yml" in loader
    # AC2's grep, over what the tree tracks (a gitignored build input under src/content/ is steward's data)
    paths = _tracked("docs-site/src", "docs-site/scripts", "docs-site/astro.config.mjs")
    hits = [
        f"{rel}:{n}"
        for rel in paths
        if not (REPO_ROOT / rel).is_symlink()
        for n, line in enumerate((REPO_ROOT / rel).read_text(encoding="utf-8", errors="replace").splitlines(), 1)
        if "docsite/" in line
    ]
    assert hits == []


def test_ac4_the_site_tasks_are_gone_and_pages_check_is_the_one_build_check() -> None:
    text = (REPO_ROOT / "pixi.toml").read_text(encoding="utf-8")
    assert len(re.findall(r"tasks\.site\]|tasks\.site-check\]|tasks\.site-verify\]|tasks\.site-serve\]", text)) == 0
    tasks = tomllib.loads(text)["feature"]["site"]["tasks"]
    assert tasks["pages-build"]["cmd"] == "node docs-site/scripts/pages.mts build"
    assert tasks["pages-check"] == {
        "description": tasks["pages-check"]["description"],
        "cmd": "node docs-site/scripts/pages.mts check",
        "depends-on": ["pages-build"],
    }
    assert "docs-site-sidebar" not in tasks


def test_ac5_the_flag_left_the_tree_and_no_reader_names_it() -> None:
    flags = json.loads((REPO_ROOT / "src/platform/config/flags.json").read_text(encoding="utf-8"))["flags"]
    overlays = json.loads((REPO_ROOT / "src/platform/config/flag-overlays.json").read_text(encoding="utf-8"))
    assert _FLAG_KEY not in flags
    assert all(_FLAG_KEY not in values for values in overlays.values())
    herald_src = REPO_ROOT / "src/shared/packages/pyforge-herald/src"
    for rel in _tracked("src/shared/packages/pyforge-herald/src", "docs-site", ".github", "pixi.toml"):
        path = REPO_ROOT / rel
        if path.is_symlink() or rel.endswith(".md"):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        assert _FLAG_KEY not in text and "PAGES_ONE_GENERATOR" not in text and "pagesOneGenerator" not in text, rel
    assert not (herald_src / "pyforge/herald/pages_one_generator.py").exists()
    # the story spec's ``retires-flag:`` declaration is flag-gate-check's to judge (doctor Story 34.7)


def test_ac6_the_bespoke_python_under_docs_site_is_under_300_lines() -> None:
    files = [p for p in DOCS_SITE.rglob("*.py") if "node_modules" not in p.parts]
    total = sum(len(p.read_text(encoding="utf-8").splitlines()) for p in files)
    assert total < 300, {p.name: len(p.read_text(encoding="utf-8").splitlines()) for p in files}


def test_ac9_agents_md_cites_the_dossier_where_it_lives() -> None:
    agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert f"`{DOSSIER_REL}` § A→B" in agents
    assert "docsite/" not in agents


def test_the_flags_reach_the_build_through_one_export() -> None:
    workflow = (REPO_ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8")
    assert 'python -m pyforge.herald.pages_env >> "$GITHUB_ENV"' in workflow
    assert "--out docs-site/src/content/fleet-status.json" in workflow
    assert "site-verify" not in workflow


# --- the built artifact -------------------------------------------------------------------------------------------


def _inputs(directory: Path) -> Path:
    """Every build input a Guild step writes, from the herald fixtures (Stories 42.1, 43.6)."""
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


_CI = {"GITHUB_SHA": "0123456789abcdef0123", "GITHUB_RUN_ID": "111", "PAGES_BUILT_AT": "2026-10-15T09:00:00Z"}
#: Shifts node's clock two days ahead (Story 43.5's review): every ``Date`` the build makes, ``Date.now()`` included.
_TWO_DAYS_LATER = """
const offset = 2 * 24 * 3600 * 1000;
const RealDate = Date;
class ShiftedDate extends RealDate {
  constructor(...args) { super(...(args.length ? args : [RealDate.now() + offset])); }
  static now() { return RealDate.now() + offset; }
}
globalThis.Date = ShiftedDate;
"""


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The tracked tree built with the status pages and the CI tile on, every input present, under CI's variables."""
    tmp = tmp_path_factory.mktemp("one-generator")
    out = tmp / "site"
    done = astro_build(out, status=True, tile=True, inputs=_inputs(tmp / "inputs"), extra_env=_CI)
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-3000:]
    return out


def _ac7_urls() -> list[str]:
    urls = ["", "herald/", "herald/dossier/", "herald/infographics/", "herald/decks/"]
    urls += [f"herald/decks/{slug}/" for slug in FAMILIES]
    urls += [path.lstrip("/") for path in REDIRECTS["legacy"]]
    urls += ["status/", "status/ci/", "status/runs/", "changes/", "changes/rss.xml", "llms.txt", "llms-full.txt"]
    return [*urls, "facts.json"]


@needs_astro
def test_ac7_the_artifact_holds_every_url_and_passes_pages_check(built: Path) -> None:
    assert len(FAMILIES) == 10 and len(REDIRECTS["legacy"]) == 44
    missing = [url for url in _ac7_urls() if not ((built / url).is_file() or (built / url / "index.html").is_file())]
    assert missing == [], f"missing: {missing}"
    assert pages_check(built, env=STATUS_ENV, repo_root=REPO_ROOT) == []


@needs_astro
def test_ac8_nothing_loads_a_font_or_a_script_from_a_cdn(built: Path) -> None:
    offenders = [
        p.relative_to(built).as_posix()
        for p in built.rglob("*")
        if p.is_file() and re.search(rb"fonts\.googleapis|cdn\.", p.read_bytes())
    ]
    assert offenders == []


@needs_astro
def test_the_csp_decision_every_page_carries_one_policy(built: Path) -> None:
    """Story 43.7's CSP decision (the default, extended): every page the build renders carries one CSP meta -- the
    herald layouts' own, every Starlight page's written at build end with its inline scripts allowed by hash."""
    for rel in ("changes/index.html", "status/runs/index.html", "status/index.html", "index.html", "404.html"):
        html = (built / rel).read_text(encoding="utf-8")
        policy = re.findall(r'<meta http-equiv="Content-Security-Policy" content="([^"]+)">', html)
        assert len(policy) == 1, rel
        assert policy[0].startswith("default-src 'self'; script-src 'self' 'wasm-unsafe-eval'"), rel
        assert html.index("Content-Security-Policy") < html.index("<script"), rel
        for body in re.findall(r"<script\b(?![^>]*\bsrc=)[^>]*>([\s\S]*?)</script>", html):
            digest = ts(
                DOCS_SITE / "src" / "lib" / "artifact.ts",
                "return m.withCsp(inp.page);",
                page=f"<head></head><script>{body}</script>",
            )
            assert re.search(r"'sha256-[^']+'", digest).group(0) in policy[0], rel
    herald = (built / "herald" / "index.html").read_text(encoding="utf-8")
    assert herald.count("Content-Security-Policy") == 1 and "'unsafe-hashes'" in herald


@needs_astro
def test_the_status_pages_carry_the_built_from_line_and_no_stamp_of_their_own(built: Path) -> None:
    line = "Built from 0123456 · 2026-10-15 09:00 UTC · run 111"
    for rel in ("status/index.html", "status/ci/index.html", "status/runs/index.html", "changes/index.html"):
        html = (built / rel).read_text(encoding="utf-8")
        assert html.count("data-pages-built-from") == 1 and line in html, rel
        assert "Site rebuilt" not in html and not re.search(r"Built 20\d\d-\d\d-\d\d", html), rel
    board = (built / "status/index.html").read_text(encoding="utf-8")
    assert len(re.findall(r"<tr data-station=", board)) == 8
    guild = (built / "status/ci/index.html").read_text(encoding="utf-8")
    assert guild.count("data-surface=") == len(
        json.loads((DOCS_SITE / "src/content/ci-status.json").read_text())["rows"]
    )


@needs_astro
def test_the_artifact_build_of_the_dossier_is_one_self_contained_file(built: Path) -> None:
    artifact = (built / "herald/artifact/dossier.html").read_text(encoding="utf-8")
    assert artifact.startswith("<title>The PyForge Dossier</title>")
    for tag in ("<!doctype", "<html", "<head", "<body", "<script", "data-pages-built-from", "data-pf-menu-link"):
        assert tag not in artifact.lower(), tag
    assert artifact.count("data:font/woff2;base64,") >= 3
    assert re.findall(r"url\((?!data:)", artifact) == []
    assert '<section id="atlas"' in artifact and "Measured on" in artifact


@needs_astro
def test_the_font_licences_ship_with_the_faces(built: Path) -> None:
    for package in ("big-shoulders-display", "ibm-plex-sans", "ibm-plex-mono", "archivo"):
        text = (built / f"fonts/fontsource-{package}.LICENSE.txt").read_text(encoding="utf-8")
        assert "SIL Open Font License" in text, package
    assert "SIL Open Font License" in (built / "fonts/fontsource-variable-archivo.LICENSE.txt").read_text("utf-8")
    assert (built / "favicon.svg").read_text(encoding="utf-8").count(SITE["favicon"]) == 1


@needs_astro
def test_llms_txt_lists_every_gallery_and_family_page_with_its_text(built: Path) -> None:
    index = (built / "llms.txt").read_text(encoding="utf-8")
    full = (built / "llms-full.txt").read_text(encoding="utf-8")
    for slug in FAMILIES:
        assert f"/herald/decks/{slug}/)" in index, slug
        assert f"URL: https://rxm7706.github.io/local-recipes/herald/decks/{slug}/" in full, slug
    infographics = re.findall(
        r"\(https://rxm7706\.github\.io/local-recipes/herald/infographics/([\w-]+\.html)\)", index
    )
    assert len(infographics) == 10 and all((built / "herald/infographics" / name).is_file() for name in infographics)
    assert full.count("infographic, published from presentations/") == 10


@needs_astro
def test_43_5_two_builds_two_days_runs_and_commits_apart_differ_only_in_the_built_from_line(
    built: Path, tmp_path: Path
) -> None:
    """Story 43.5's proof over the whole artifact (its carry-in to 43.7): with the status pages on, the herald pages,
    the shelf, the status pages and the machine surfaces hold no date or commit of their own -- the build's time,
    run and commit live only in the built-from line, whose text steward's tree hash drops -- so a build of the same
    tree two days, two runs and two commits later is byte-identical once that text is dropped."""
    later = write(tmp_path / "later.mjs", _TWO_DAYS_LATER)
    second = tmp_path / "second"
    env = {
        "GITHUB_SHA": "fedcba9876543210fedc",
        "GITHUB_RUN_ID": "222",
        "PAGES_BUILT_AT": "2026-10-17T21:30:00Z",
        "NODE_OPTIONS": f"--import={later.as_uri()}",
    }
    done = astro_build(second, status=True, tile=True, inputs=_inputs(tmp_path / "inputs"), extra_env=env)
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-3000:]

    def tree(out: Path) -> dict[str, bytes]:
        return {
            p.relative_to(out).as_posix(): _BUILT_FROM_TEXT.sub(rb"\1\2", p.read_bytes())
            if p.suffix == ".html"
            else p.read_bytes()
            for p in sorted(out.rglob("*"))
            if p.is_file()
        }

    one, two = tree(built), tree(second)
    assert one.keys() == two.keys()
    assert [rel for rel in one if one[rel] != two[rel]] == []
    assert "Built from fedcba9 · 2026-10-17 21:30 UTC · run 222" in (second / "status/index.html").read_text("utf-8")


@needs_astro
def test_42_2_with_the_exports_present_the_mounts_their_redirect_and_their_sections_appear(tmp_path: Path) -> None:
    root = fixture_tree(tmp_path / "tree", exports=True)
    out = tmp_path / "site"
    done = astro_build(out, root=root)
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-3000:]
    for rel in ("dashboard/kedro-viz/index.html", "dashboard/vizro/index.html", "dashboard/fleet-board/index.html"):
        assert (out / rel).is_file(), rel
    assert not (out / "dashboard/.vizro-staging").exists() and not (out / "dashboard/index.html").exists()
    assert "url=/local-recipes/dashboard/kedro-viz/" in (out / "kedro-viz/index.html").read_text(encoding="utf-8")
    menu = re.findall(r"data-pf-menu-link[^>]*>\s*([^<]*?)\s*<", (out / "index.html").read_text(encoding="utf-8"))
    assert menu == ["Docs", "Overview", "Dossier", "Infographics", "Decks", "Kedro-Viz", "Dashboards", "Changes"]
    findings = pages_check(out, repo_root=root)
    assert findings and all(line.startswith("legacy redirect ") for line in findings), (
        findings
    )  # the fixture's 2 families


# --- Story 43.5: every number is measured (moved from the retired parity test) ------------------------------------


def _page_stats(html: str) -> dict[str, list[tuple[str, str]]]:
    def text(fragment: str) -> str:
        return " ".join(re.sub(r"<[^>]+>", "", fragment).replace("&amp;", "&").split())

    hero = re.findall(
        r'<span class="n"[^>]*>(.*?)</span>\s*<span class="l"[^>]*>(.*?)</span>', html.split("<section", 1)[0], re.S
    )
    out = {"": [(text(v), text(lab)) for v, lab in hero]}
    for sid, body in re.findall(r'<section id="([^"]+)"[^>]*>(.*?)</section>', html, re.S):
        out[sid] = [
            (text(v), text(lab))
            for v, lab in re.findall(r'<div class="s"><b>(.*?)</b><span>(.*?)</span></div>', body, re.S)
        ]
    return out


@needs_astro
def test_43_5_the_dossier_shows_what_the_measurer_counted_and_every_page_its_build(tmp_path: Path) -> None:
    root = fixture_tree(tmp_path / "tree")
    counts = station_packages(root)
    done = astro_build(tmp_path / "astro", root=root, extra_env=_CI)
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-3000:]
    html = (tmp_path / "astro/herald/dossier/index.html").read_text(encoding="utf-8")
    doc = yaml.safe_load((root / DOSSIER_REL).read_text(encoding="utf-8"))
    shown = _page_stats(html)
    total = sum(c["src_lines"] for c in counts.values())
    assert shown[""][[s.get("check") for s in doc["stats"]].index("fleet_src_lines")][0] == f"~{round(total / 1000)}K"
    checked = 0
    for section in doc["sections"]:
        stats = [st for b in section["blocks"] if b["type"] == "stats" for st in b["stats"]]
        for stat, (value, label) in zip(stats, shown[section["id"]], strict=True):
            if stat.get("check") == "src_lines":
                want = counts[section["id"]]
                assert (value, label.split("·")[-1].strip()[:3]) == (f"{want['src_lines']:,}", f"{want['src_files']} f")
                checked += 1
            elif stat.get("check") == "test_lines":
                assert value == f"{counts[section['id']]['test_lines']:,}"
                checked += 1
    assert checked >= 10
    assert html.count('<p class="measured-on">') == len(doc["sections"])
    line = '<p class="built-from" data-pages-built-from data-pagefind-ignore>Built from 0123456 · 2026-10-15 09:00 UTC · run 111</p>'
    for rel in (
        "herald/dossier/index.html",
        "herald/index.html",
        "herald/infographics/alpha.html",
        "how-to/index.html",
    ):
        assert (tmp_path / "astro" / rel).read_text(encoding="utf-8").count(line) == 1, rel


@needs_astro
@pytest.mark.parametrize(
    ("edit", "named"),
    [
        ("drop-measured", 'dossier section "herald" has no measured: date'),
        ("unknown-check", "unknown check 'moons' in section 'atlas'"),
    ],
)
def test_43_5_the_build_refuses_a_section_without_a_date_and_an_unknown_check(
    tmp_path: Path, edit: str, named: str
) -> None:
    root = fixture_tree(tmp_path / "tree")
    dossier = root / DOSSIER_REL
    doc = yaml.safe_load(dossier.read_text(encoding="utf-8"))
    sections = {section["id"]: section for section in doc["sections"]}
    if edit == "drop-measured":
        del sections["herald"]["measured"]
    else:
        next(b for b in sections["atlas"]["blocks"] if b["type"] == "stats")["stats"][0]["check"] = "moons"
    dossier.write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8")
    done = astro_build(tmp_path / "astro", root=root)
    assert done.returncode != 0
    assert named in done.stdout + done.stderr


def test_the_measurer_moved_beside_the_generator() -> None:
    loader = (DOCS_SITE / "src/loaders/dossier-loader.ts").read_text(encoding="utf-8")
    assert "path.join(REPO_ROOT, 'docs-site/scripts/verify_claims.py')" in loader
    done = subprocess.run(
        [sys.executable, str(DOCS_SITE / "scripts/verify_claims.py"), "--emit", "-"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    emitted = json.loads(done.stdout)
    assert (
        {"src_lines", "fleet_src_lines"}
        <= set(emitted)
        <= {"src_lines", "test_lines", "python_floor", "fleet_src_lines"}
    )


# --- carried from the retired assembler's built tests (Stories 43.3, 43.4) ------------------------------------------

_BASE = "/local-recipes/"


def _file(site: Path, page: Path, href: str) -> Path:
    return site / href[len(_BASE) :] if href.startswith(_BASE) else page.parent / href


@needs_astro
def test_43_3_ac1_ac5_every_legacy_path_lands_and_the_csp_names_no_host(built: Path) -> None:
    refresh = re.compile(r"""http-equiv=["']refresh["'][^>]*url=([^"']+)["']""")
    for source, target in REDIRECTS["legacy"].items():
        stub = built / source.lstrip("/")
        match = refresh.search(stub.read_text(encoding="utf-8"))
        assert match, f"{source}: not a redirect page"
        landed = (stub.parent / match.group(1)).resolve()
        assert landed == (built / target.lstrip("/")).resolve() and landed.is_file(), f"{source}: lands nowhere"
    gallery = (built / "herald" / "infographics" / "index.html").read_text(encoding="utf-8")
    csp = html.unescape(re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', gallery).group(1))
    for directive in csp.split(";"):
        for source in directive.split()[1:]:
            assert source in ("'self'", "'none'", "'unsafe-inline'", "'unsafe-hashes'", "data:") or re.fullmatch(
                r"'sha256-[A-Za-z0-9+/]+=*'", source
            ), f"CSP source {source!r} names a host"
    onload = html.unescape(re.search(r'onload="([^"]+)"', gallery).group(1))
    digest = base64.b64encode(hashlib.sha256(onload.encode("utf-8")).digest()).decode("ascii")
    assert f"'sha256-{digest}'" in csp


@needs_node
def test_43_3_ac2_a_page_at_a_legacy_path_fails_the_build(tmp_path: Path) -> None:
    """AC2: the redirect writer refuses a path the build already holds, naming it (AD-21 rule 1)."""
    write(tmp_path / "out" / "dossier" / "index.html", "<html>a page</html>")
    result = ts(
        DOCS_SITE / "src" / "lib" / "redirects.ts",
        "return m.writeLegacyRedirects(inp.out, inp.legacy);",
        out=str(tmp_path / "out"),
        legacy=REDIRECTS["legacy"],
    )
    assert "dossier/index.html" in result["message"] and "one owner" in result["message"]
    assert not (tmp_path / "out" / "decks").exists()  # nothing written when one path is taken


@needs_astro
def test_43_3_ac4_search_holds_a_dossier_page_and_a_family_page(built: Path) -> None:
    fragments = []
    for path in (built / "pagefind" / "fragment").glob("*.pf_fragment"):
        raw = gzip.decompress(path.read_bytes())
        fragments.append(json.loads(raw[len(b"pagefind_dcd") :]))
    dossier = [f["url"] for f in fragments if "/herald/" in f["url"] and "Cross-fleet synthesis" in f["content"]]
    assert len(dossier) == 1 and dossier[0].endswith("/herald/dossier/"), dossier
    family = [f["url"] for f in fragments if "/herald/decks/" in f["url"] and "pyforge-herald" in f["content"]]
    assert len(family) == 1 and family[0].endswith("/herald/decks/pyforge-herald/"), family


def _font_vendoring_only(published: bytes, tracked: bytes) -> list[str]:
    """What a twin changed beyond Story 31.3's font-link vendoring, read on raw bytes line by line and independently
    of the code that wrote it: a lost line naming no Google Fonts origin, a gained line other than the one vendored
    link, or more than one vendored link (the retired assembler's check, kept as this test's oracle)."""
    vendored = re.compile(rb'<link rel="stylesheet" href="(?:\.\./)+fonts\.css">')
    google = (b"fonts.googleapis.com", b"fonts.gstatic.com")
    changes: list[str] = []
    links = 0
    a, b = tracked.splitlines(keepends=True), published.splitlines(keepends=True)
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        changes += [f"lost {line!r}" for line in a[i1:i2] if not any(o in line for o in google)]
        for line in b[j1:j2]:
            if vendored.fullmatch(line.strip()):
                links += 1
            elif line.strip():
                changes.append(f"gained {line!r}")
    return [*changes, *([f"gained {links} vendored font links, not one"] if links > 1 else [])]


@needs_astro
def test_43_3_ac3_public_serves_the_twins_downloads_exports_and_licences(tmp_path: Path) -> None:
    """AC3: ``docs-site/public/`` holds exactly the twins, the downloads, every entry of ``docs/dashboard/`` but its
    README, the font licences and the favicon -- each the artifact's copy byte for byte; a download or an export is its
    source byte for byte, a twin its source with only the font-link vendoring (Story 43.2's ruling)."""
    root = fixture_tree(tmp_path / "tree", exports=True)
    out = tmp_path / "site"
    done = astro_build(out, root=root)
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-3000:]
    public = DOCS_SITE / "public"
    files = sorted(p.relative_to(public).as_posix() for p in public.rglob("*") if p.is_file())
    project = "presentations/{}/project/{}"
    twins = {
        "herald/twins/infographics/beta-co.html": project.format("fx-beta", "Beta Infographic standalone.html"),
        "herald/twins/infographics/alpha.html": project.format("fx-alpha", "Alpha Infographic standalone.html"),
        "herald/twins/decks/fx-alpha/infographic-deck.html": project.format(
            "fx-alpha", "Alpha - Infographic Deck.dc.html"
        ),
        "herald/twins/decks/fx-alpha/executive-summary.html": project.format(
            "fx-alpha", "Alpha - Executive Summary.dc.html"
        ),
        "herald/twins/decks/fx-beta/infographic-deck.html": project.format(
            "fx-beta", "Beta - Infographic Deck.dc.html"
        ),
    }
    copies = {
        f"herald/decks/{slug}/downloads/{name}": f"presentations/{slug}/src/{kind}/{name}"
        for slug, kind, name in (
            ("fx-alpha", "pptx", "fx-alpha-deck-2026-01-01.pptx"),
            ("fx-alpha", "marp", "fx-alpha-deck-2026-01-01.md"),
            ("fx-alpha", "marp", "fx-alpha-narration-2026-01-02.md"),
            ("fx-beta", "marp", "fx-beta-2026-02-02.md"),
        )
    }
    for name in ("kedro-viz", "vizro", "fleet-board"):  # every entry of docs/dashboard/, not the exports only
        for path in (root / "docs" / "dashboard" / name).rglob("*"):
            if path.is_file():
                rel = path.relative_to(root / "docs" / "dashboard").as_posix()
                copies[f"dashboard/{rel}"] = f"docs/dashboard/{rel}"
    licences = [
        f"fonts/{p}.LICENSE.txt"
        for p in (
            "fontsource-big-shoulders-display",
            "fontsource-ibm-plex-sans",
            "fontsource-ibm-plex-mono",
            "fontsource-archivo",
            "fontsource-variable-archivo",
        )
    ]
    assert files == sorted([*twins, *copies, *licences, "favicon.svg"])
    for rel in files:
        assert (out / rel).read_bytes() == (public / rel).read_bytes(), f"{rel}: the artifact's copy differs"
    for rel, source in copies.items():
        assert (public / rel).read_bytes() == (root / source).read_bytes(), f"{rel} is not {source}"
    for rel, source in twins.items():
        assert _font_vendoring_only((public / rel).read_bytes(), (root / source).read_bytes()) == [], rel
    assert not (out / "dashboard" / "README.md").exists()


def _top_level_rules(css: str, medium: str = "screen") -> list[tuple[str, str]]:
    """``(selector, body)`` of each rule outside every at-rule but a bare ``@media <medium>`` query."""
    rules, i = [], 0
    while (j := css.find("{", i)) >= 0:
        head, depth, k = css[i:j].split(";")[-1].split("}")[-1].strip(), 1, j + 1
        while depth and k < len(css):
            depth += {"{": 1, "}": -1}.get(css[k], 0)
            k += 1
        if not head.startswith("@"):
            rules.append((head, css[j + 1 : k - 1]))
        elif re.fullmatch(rf"@media\s+(?:only\s+)?{medium}", head):
            rules += _top_level_rules(css[j + 1 : k - 1], medium)
        i = k
    return rules


def _page_theme(site: Path, page: Path, medium: str = "screen") -> dict[str, dict[str, str]]:
    """The site theme's variables -- each ``--sl-*`` an unlayered ``:root`` or ``[data-theme=dark]`` rule sets -- in
    the stylesheets ``page`` links for ``medium``, light and dark."""
    light: dict[str, str] = {}
    dark: dict[str, str] = {}
    for link in re.findall(r'<link rel="stylesheet" href="[^"]+"[^>]*>', page.read_text(encoding="utf-8")):
        href = re.search(r'href="([^"]+)"', link).group(1)
        media = re.search(r'\bmedia="([^"]+)"', link)
        if media and media.group(1) not in ("all", medium):
            continue
        for selector, body in _top_level_rules(_file(site, page, href).read_text(encoding="utf-8"), medium):
            values = dict(re.findall(r"(--sl-[\w-]+)\s*:\s*([^;}]+)", body))
            if selector == ":root":
                light.update(values)
            elif selector in (":root[data-theme=dark]", ":root[data-theme='dark']"):
                dark.update(values)
    return {"light": light, "dark": {**light, **dark}}


@needs_astro
def test_43_4_the_built_pages_share_one_theme(built: Path) -> None:
    """The theme contract on the built artifact (operator ruling 2026-10-15): a docs page and a herald page resolve the
    same Starlight font, accent and gray values in both themes; print reads light; the herald-only rules never reach the
    shelf; every face is an @fontsource woff2 under ``_astro/`` and the five families are there; each herald page runs
    the theme script, allowed by its CSP, before its stylesheet."""
    shelf, dossier = built / "how-to" / "index.html", built / "herald" / "dossier" / "index.html"
    docs_theme, herald_theme = _page_theme(built, shelf), _page_theme(built, dossier)
    for mode in ("light", "dark"):
        names = [n for n in docs_theme[mode] if n.startswith(("--sl-font", "--sl-color-accent", "--sl-color-gray"))]
        names += ["--sl-color-white", "--sl-color-black", "--sl-color-text-accent"]
        assert len(names) > 12
        assert {n: docs_theme[mode][n] for n in names} == {n: herald_theme[mode].get(n) for n in names}, mode
    assert (
        docs_theme["light"]["--sl-color-accent"] == "#b06a13" and docs_theme["dark"]["--sl-color-accent"] == "#dd9a3f"
    )
    for page in (shelf, dossier):
        printed = _page_theme(built, page, "print")
        assert printed["dark"] == printed["light"], page
    shelf_html = shelf.read_text(encoding="utf-8")
    shelf_css = "".join(
        _file(built, shelf, href).read_text(encoding="utf-8")
        for href in re.findall(r'<link rel="stylesheet" href="([^"]+)"', shelf_html)
    )
    assert "_astro/herald." not in shelf_html
    for herald_only in (".station-mark", ".site-nav-inner", ".hero-eyebrow", "text-transform:uppercase"):
        assert herald_only not in shelf_css, f"{herald_only} reached the docs"
    families: set[str] = set()
    for sheet in [built / "herald" / "fonts.css", built / "herald" / "theme.css", *(built / "_astro").glob("*.css")]:
        for face in re.findall(r"@font-face\{([^}]*)\}", sheet.read_text(encoding="utf-8")):
            families.add(re.search(r"font-family:\s*['\"]?([^;'\"]+)", face).group(1))
            for url in re.findall(r"url\(([^)]+)\)", face):
                assert url.startswith(f"{_BASE}_astro/") and url.endswith(".woff2"), (sheet.name, url)
                assert (built / url[len(_BASE) :]).is_file(), (sheet.name, url)
    assert families == {"Big Shoulders Display", "IBM Plex Sans", "IBM Plex Mono", "Archivo", "Archivo Expanded"}
    reader = built / "herald/infographics/atlas.html"
    for page in [built / "herald/index.html", dossier, built / "herald/decks/pyforge-herald/index.html", reader]:
        text = page.read_text(encoding="utf-8")
        script = re.search(r"<script>(.*?)</script>", text).group(1)
        assert "starlight-theme" in script, page
        digest = base64.b64encode(hashlib.sha256(script.encode("utf-8")).digest()).decode("ascii")
        assert f"'sha256-{digest}'" in text and text.index(script) < text.index('rel="stylesheet"'), page
    assert '<link rel="stylesheet" href="../../fonts.css">' in (
        built / "herald/twins/infographics/atlas.html"
    ).read_text("utf-8")
    assert '<link rel="stylesheet" href="../theme.css">' in reader.read_text(encoding="utf-8")
