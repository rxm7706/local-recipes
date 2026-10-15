"""Story 43.6 (spec-pyforge-herald CAP-61): agents and the changes feed read the site.

Two halves, as Story 43.2's parity test splits them:

* **The model** runs wherever ``node`` does: ``docs-site/src/lib/agent-surface.ts`` (node builtins only, imported
  with node's type stripping, no ``node_modules``) over the fixtures -- the input shapes and their refusals, the
  feed, the facts union, the latest progress record per station, the Lane 1 rule.
* **The built site** needs docs-site's ``node_modules`` and generated menu (``pixi run -e site docs-site-install
  docs-site-sidebar``) and skips naming them otherwise. It builds Astro into a scratch directory with the inputs
  present, partly present and absent, and with ``pyforge.herald.pages_one_generator`` on and off (AC1-AC7).
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

import pytest
import yaml
from pyforge.testing_kit import make_flag_provider_fixture
from pyforge.testing_kit.flags import flag_states

REPO_ROOT = Path(__file__).resolve().parents[6]
DOCS_SITE = REPO_ROOT / "docs-site"
SURFACE_TS = DOCS_SITE / "src" / "lib" / "agent-surface.ts"
ASTRO_BIN = DOCS_SITE / "node_modules" / "astro" / "bin" / "astro.mjs"
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
CHANGES = FIXTURES / "changes-five-merges.json"
MARSHAL = FIXTURES / "marshal-status-two-homes.json"
PROGRESS = FIXTURES / "herald-progress-records.json"
SITE_URL = "https://rxm7706.github.io/local-recipes"
_GENERATED = ("src/sidebar.generated.json", "src/topnav.generated.json")
_NODE = shutil.which("node")
_BUILD_READY = _NODE is not None and ASTRO_BIN.is_file() and all((DOCS_SITE / g).is_file() for g in _GENERATED)
needs_node = pytest.mark.skipif(_NODE is None, reason="node is not on PATH")
needs_astro = pytest.mark.skipif(
    not _BUILD_READY,
    reason="docs-site is not installed: pixi run -e site docs-site-install docs-site-sidebar",
)
_FLAG = "pyforge.herald.pages_one_generator"
flag_provider = make_flag_provider_fixture()

#: The five fixture merges, newest first (AC3, AC4).
_MERGES_NEWEST_FIRST = [
    ("2026-10-15T08:10:00+00:00", "pyforge-marshal", "Merge pyforge-marshal/102-1 into main"),
    ("2026-10-14T12:00:00+00:00", "pyforge-herald", "Merge pyforge-herald/42-1 into main <status & ci>"),
    ("2026-10-13T16:20:00+00:00", "pyforge-doctor", "Merge pyforge-doctor/48-1 into main"),
    ("2026-10-01T10:30:00+00:00", "pyforge-steward", "Merge pyforge-steward/102-2 into main"),
    ("2026-09-20T11:00:00+00:00", "pyforge-atlas", "Merge pyforge-atlas/30-1 into main"),
]
_AGENT_FILES = ("llms.txt", "llms-full.txt", "facts.json", "changes/index.html", "changes/rss.xml")
_RUNS = "status/runs/index.html"


# ------------------------------------------------------------------ the model, through node


def _ts(expression: str, **inputs: object) -> object:
    """Evaluate ``expression`` with the module imported as ``m`` and ``inputs`` bound as ``inp``; a thrown
    error comes back as ``{"error": name, "message": ...}``."""
    script = (
        f"import * as m from {json.dumps(SURFACE_TS.as_uri())};\n"
        f"const inp = {json.dumps(inputs)};\n"
        "try {\n"
        f"  const value = await (async () => {{ {expression} }})();\n"
        "  process.stdout.write(JSON.stringify({ value }));\n"
        "} catch (exc) {\n"
        "  process.stdout.write(JSON.stringify({ error: exc.name, message: exc.message }));\n"
        "}\n"
    )
    env = {k: v for k, v in os.environ.items() if k not in ("PYTEST_ADDOPTS", "PAGES_BUILD_INPUTS_DIR")}
    done = subprocess.run(
        [_NODE or "node", "--experimental-strip-types", "--no-warnings", "--input-type=module", "-e", script],
        cwd=DOCS_SITE,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def _refusal(result: object) -> str:
    assert isinstance(result, dict) and result.get("error") == "BuildInputShapeError", result
    return str(result["message"])


@needs_node
def test_changes_are_read_newest_first() -> None:
    result = _ts("return m.parseChanges(inp.text, 'changes.json')", text=CHANGES.read_text(encoding="utf-8"))
    changes = result["value"]
    assert [(m["date"], m["station"], m["subject"]) for m in changes["merges"]] == _MERGES_NEWEST_FIRST
    assert changes["generatedAt"] == "2026-10-15T09:00:00+00:00"
    assert changes["windowDays"] == 30  # noqa: PLR2004
    bare = _ts("return m.parseChanges('[]', 'changes.json')")["value"]
    assert bare == {"generatedAt": None, "windowDays": None, "merges": []}


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("{merges: [", "changes.json: not valid JSON"),
        ('{"merges": {}}', "neither a list of merges nor an object with a merges list"),
        ('[{"date": "2026-10-15", "station": "s"}]', "merge 0 has no string subject"),
        (
            '[{"date": "yesterday", "station": "s", "subject": "x"}]',
            'merge 0 date "yesterday" is not YYYY-MM-DD or an ISO date-time with an offset',
        ),
        # An offset-less date-time read in the build host's zone, and a non-ISO date (43.6's review, N1).
        ('[{"date": "2026-10-15T08:00:00", "station": "s", "subject": "x"}]', "merge 0 date"),
        ('[{"date": "Oct 1, 2026", "station": "s", "subject": "x"}]', "merge 0 date"),
        ('[{"date": "2026-10-15", "station": "s", "subject": " "}]', "merge 0 has an empty subject"),
        # Characters XML 1.0 forbids would publish a malformed feed (43.6's review, F2).
        ('[{"date": "2026-10-15", "station": "s", "subject": "red \\u001b[31m"}]', "merge 0 subject holds a control"),
        ('[{"date": "2026-10-15", "station": "s\\u000c", "subject": "x"}]', "merge 0 station holds a control"),
        ('[{"date": "2026-10-15", "station": "s", "subject": "x\\uffff"}]', "merge 0 subject holds a control"),
        ('[{"date": "2026-10-15", "station": "s", "subject": "x", "sha": "a b\\""}]', 'merge 0 sha "a b\\"" is not'),
        (
            '[{"date": "2026-10-15", "station": "s", "subject": "x", "sha": "abcdef1"},'
            ' {"date": "2026-10-14", "station": "s", "subject": "y", "sha": "abcdef1"}]',
            "merge 1 repeats merge 0's sha abcdef1",
        ),
    ],
)
@needs_node
def test_a_malformed_changes_input_names_the_file(text: str, message: str) -> None:
    assert message in _refusal(_ts("return m.parseChanges(inp.text, 'changes.json')", text=text))


def _rss(text: str) -> ET.Element:
    root = ET.fromstring(text)
    assert root.tag == "rss" and root.get("version") == "2.0"
    channels = root.findall("channel")
    assert len(channels) == 1
    return channels[0]


@needs_node
def test_a_date_only_merge_and_whitespace_controls_still_make_a_well_formed_feed() -> None:
    text = json.dumps([{"date": "2026-10-15", "station": "s", "subject": "tab\there & <b>"}])
    feed = _ts("return m.changesFeed(m.parseChanges(inp.text, 'c.json'), 'https://x/changes/')", text=text)["value"]
    item = _rss(feed).find("item")
    assert item is not None and item.findtext("title") == "tab\there & <b>"
    assert item.findtext("pubDate") == "Thu, 15 Oct 2026 00:00:00 GMT"  # a date is UTC midnight on every host


@needs_node
def test_the_feed_is_rss_2_with_the_same_items_in_the_same_order() -> None:
    """AC4 on the model: one channel, the five merges newest first, each with title, link and pubDate."""
    feed = _ts(
        "return m.changesFeed(m.parseChanges(inp.text, 'changes.json'), inp.page)",
        text=CHANGES.read_text(encoding="utf-8"),
        page=f"{SITE_URL}/changes/",
    )["value"]
    channel = _rss(feed)
    items = channel.findall("item")
    assert [item.findtext("title") for item in items] == [subject for _, _, subject in _MERGES_NEWEST_FIRST]
    for item in items:
        assert item.findtext("link", "").startswith(f"{SITE_URL}/changes/#merge-")
        assert re.fullmatch(r"\w{3}, \d{2} \w{3} \d{4} \d{2}:\d{2}:\d{2} GMT", item.findtext("pubDate", ""))
    empty = _rss(_ts("return m.changesFeed(null, inp.page)", page=f"{SITE_URL}/changes/")["value"])
    assert empty.findall("item") == [] and empty.findtext("link") == f"{SITE_URL}/changes/"


@needs_node
def test_the_runs_inputs_keep_only_what_the_page_shows() -> None:
    marshal = _ts("return m.parseMarshalStatus(inp.text, 'm.json')", text=MARSHAL.read_text(encoding="utf-8"))
    homes = marshal["value"]["homes"]
    assert [home["slug"] for home in homes] == ["pyforge-marshal", "pyforge-doctor"]
    assert set(homes[0]) == {
        "slug",
        "branch",
        "state",
        "currentStory",
        "elapsedSeconds",
        "budgetConsumed",
        "budgetConsumedUsd",
    }
    # Escalation artifacts and failed patches name Tier-3 paths: never read, never published.
    assert "implementation-artifacts" not in json.dumps(marshal) and "changes.patch" not in json.dumps(marshal)
    assert marshal["value"]["generatedAt"] == "2026-10-15T09:05:00+00:00"
    assert "no homes list" in _refusal(_ts("return m.parseMarshalStatus('{\"data\": {}}', 'm.json')"))
    assert "home 0 has no state" in _refusal(
        _ts('return m.parseMarshalStatus(\'{"homes": [{"slug": "a"}]}\', \'m.json\')')
    )


@needs_node
def test_progress_keeps_the_latest_record_per_station_in_every_input_shape() -> None:
    document = json.loads(PROGRESS.read_text(encoding="utf-8"))
    ndjson = "\n".join(json.dumps(record) for record in document["records"]) + "\n"
    for text in (PROGRESS.read_text(encoding="utf-8"), json.dumps(document["records"]), ndjson):
        latest = _ts("return m.parseHeraldProgress(inp.text, 'p.json')", text=text)["value"]["latest"]
        assert [(r["station"], r["date"]) for r in latest] == [
            ("pyforge-herald", "2026-10-14"),
            ("pyforge-steward", "2026-10-15"),
        ]
        assert latest[1]["shippedCapabilities"] == ["CAP-168", "CAP-169"]
    # 43.6's review (F1): one record is one line of `herald progress --json`, itself one JSON object.
    one = _ts("return m.parseHeraldProgress(inp.text, 'p.json')", text=json.dumps(document["records"][2]) + "\n")
    assert [(r["station"], r["date"]) for r in one["value"]["latest"]] == [("pyforge-herald", "2026-10-14")]
    assert one["value"]["generatedAt"] is None
    assert "p.json: line 2 is not valid JSON" in _refusal(
        _ts("return m.parseHeraldProgress(inp.text, 'p.json')", text='{"station": "a", "date": "d"}\n{oops\n')
    )


@needs_node
def test_facts_are_one_object_per_deck_and_a_file_without_deck_is_refused() -> None:
    entries = [
        {"file": "presentations/b/facts.yaml", "data": {"deck": "b", "persona": "B", "facts": [{"id": "x"}]}},
        {"file": "presentations/a/facts.yaml", "data": {"deck": "a", "facts": []}},
    ]
    document = _ts("return m.factsDocument(inp.entries)", entries=entries)["value"]
    assert list(document) == ["a", "b"]
    assert document["b"]["facts"] == [{"id": "x"}] and document["b"]["source"] == "presentations/b/facts.yaml"
    no_deck = [{"file": "presentations/c/facts.yaml", "data": {"facts": []}}]
    assert _refusal(_ts("return m.factsDocument(inp.entries)", entries=no_deck)) == (
        "presentations/c/facts.yaml: no deck slug"
    )
    twice = [*entries, {"file": "presentations/z/facts.yaml", "data": {"deck": "a", "facts": []}}]
    assert "is also presentations/a/facts.yaml" in _refusal(_ts("return m.factsDocument(inp.entries)", entries=twice))


@needs_node
def test_shelf_routes_and_the_lane1_rule() -> None:
    routes = _ts(
        "return inp.paths.map((p) => [m.shelfRoute(p), m.shelfId(p)])",
        paths=["how-to/README.md", "how-to/x.md", "reference/a/b.mdx"],
    )["value"]
    assert routes == [["how-to/", "how-to/index"], ["how-to/x/", "how-to/x"], ["reference/a/b/", "reference/a/b"]]
    links = _ts(
        "return inp.hrefs.map((href) => m.lane1Link({ label: 'Live view on Lane 1', href }))",
        hrefs=["/console/", "//lane1.example/console/", "console/", "https://lane1.example/console/"],
    )["value"]
    assert links == [None, None, None, {"href": "https://lane1.example/console/", "label": "Live view on Lane 1"}]


# ------------------------------------------------------------------ the built site


def _write_inputs(directory: Path, names: tuple[str, ...]) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    sources = {"changes.json": CHANGES, "marshal-status.json": MARSHAL, "herald-progress.json": PROGRESS}
    for name in names:
        if name == "malformed":
            for input_name in sources:
                (directory / input_name).write_text("{not json", encoding="utf-8")
        elif name == "empty-merges":
            (directory / "changes.json").write_text('{"generated_at": "t", "window_days": 30, "merges": []}', "utf-8")
        else:
            shutil.copyfile(sources[name], directory / name)
    return directory


def _astro(out: Path, *, flag: bool, inputs: Path) -> None:
    env = {k: v for k, v in os.environ.items() if k not in ("PYTEST_ADDOPTS",)}
    env.update(
        {
            "SITE_URL": SITE_URL,
            "PAGES_BUILD_INPUTS_DIR": str(inputs),
            "PYFORGE_PAGES_ONE_GENERATOR": "1" if flag else "0",
            "PYFORGE_STATUS_PAGES": "1",
            "PYFORGE_CI_SURFACES_TILE": "0",
        }
    )
    done = subprocess.run(
        [_NODE or "node", str(ASTRO_BIN), "build", "--outDir", str(out)],
        cwd=DOCS_SITE,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-3000:]


_BUILDS: dict[str, Path] = {}


@pytest.fixture(scope="module")
def build(tmp_path_factory: pytest.TempPathFactory):
    """``build(name)``: the site built once per module for each named case."""
    cases = {
        "full": (True, ("changes.json", "marshal-status.json", "herald-progress.json")),
        "one-missing": (True, ("changes.json", "marshal-status.json")),
        "none": (True, ()),
        # AC7's "no input is opened": the flag-off build reads malformed inputs, so a module-scope read would red.
        "off": (False, ("malformed",)),
        "no-merges": (True, ("empty-merges",)),
    }

    def _get(name: str) -> Path:
        if name not in _BUILDS:
            flag, names = cases[name]
            root = tmp_path_factory.mktemp(f"agent-{name}")
            _astro(root / "site", flag=flag, inputs=_write_inputs(root / "inputs", names))
            _BUILDS[name] = root / "site"
        return _BUILDS[name]

    yield _get
    _BUILDS.clear()


class _Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        self.chunks.append(data)


def _text(html: str) -> str:
    parser = _Text()
    parser.feed(html)
    return " ".join(" ".join(parser.chunks).split())


@flag_states("pyforge.herald.pages_one_generator")
@needs_astro
def test_ac7_the_surfaces_follow_the_flag(flag_provider: dict[str, bool], build) -> None:
    """On, every surface is emitted; off, none is and no input is read into the artifact."""
    site = build("full" if flag_provider[_FLAG] else "off")
    for rel in (*_AGENT_FILES, _RUNS):
        assert (site / rel).is_file() is flag_provider[_FLAG], rel
    if not flag_provider[_FLAG]:
        assert not (site / "changes").exists()
        assert not (site / "status").exists()


@needs_astro
def test_ac1_llms_lists_every_map_page_and_every_herald_page(build) -> None:
    site = build("full")
    llms = (site / "llms.txt").read_text(encoding="utf-8")
    document = yaml.safe_load((REPO_ROOT / "docs" / "map.yaml").read_text(encoding="utf-8"))
    herald = next(section for section in document["sections"] if section["key"] == "herald")["entries"]
    entries = re.findall(r"^- \[([^\]]+)\]\(([^)]+)\)", llms, re.M)
    sections = re.split(r"^## ", llms, flags=re.M)
    pages = [s for s in sections if s.startswith(("Docs\n", "Herald\n"))]
    page_entries = [line for s in pages for line in s.splitlines() if line.startswith("- [")]
    assert len(page_entries) == len(document["pages"]) + len(herald)
    docs_section = next(section for section in sections if section.startswith("Docs\n"))
    docs_urls = re.findall(r"^- \[[^\]]+\]\(([^)]+)\)", docs_section, re.M)
    assert len(docs_urls) == len(document["pages"])
    for url in docs_urls:  # every Docs entry is a page this build wrote, not a route recomputed here
        assert url.startswith(f"{SITE_URL}/"), url
        assert (site / url[len(SITE_URL) + 1 :] / "index.html").is_file(), url
    urls = {url for _, url in entries}
    for entry in herald:
        assert f"{SITE_URL}/{entry['href']}" in urls, entry["key"]
    assert llms.startswith("# PyForge\n\n> ")
    full = (site / "llms-full.txt").read_text(encoding="utf-8")
    assert full.count("\nURL: ") == len(page_entries)
    assert f"URL: {SITE_URL}/herald/dossier/" in full
    # The dossier's prose and a shelf page's text are there, not only their titles.
    assert "The PyForge Dossier" in full
    getting_started = (REPO_ROOT / "docs" / "tutorials" / "getting-started.md").read_text(encoding="utf-8")
    if getting_started.startswith("---"):  # the shelf loader keeps the body, not the frontmatter
        getting_started = getting_started.split("\n---", 1)[1]
    probe = next(line for line in getting_started.splitlines() if len(line) > 40 and not line.startswith("#"))
    assert probe.strip() in full


@needs_astro
def test_ac2_facts_json_is_one_object_per_facts_yaml(build) -> None:
    site = build("full")
    document = json.loads((site / "facts.json").read_text(encoding="utf-8"))
    files = sorted((REPO_ROOT / "presentations").glob("*/facts.yaml"))
    decks = {yaml.safe_load(f.read_text(encoding="utf-8"))["deck"]: f for f in files}
    assert sorted(document) == sorted(decks)
    for deck, path in decks.items():
        assert document[deck]["facts"] == yaml.safe_load(path.read_text(encoding="utf-8"))["facts"], deck


@needs_astro
def test_ac3_the_changes_page_lists_five_merges_newest_first(build) -> None:
    page = (build("full") / "changes" / "index.html").read_text(encoding="utf-8")
    items = re.findall(r'<li id="merge-[^"]+"[^>]*>(.*?)</li>', page, re.S)
    assert [_text(item) for item in items] == [f"{d} {s} {subject}" for d, s, subject in _MERGES_NEWEST_FIRST]
    assert "data-pf-menu-link" in page  # the shared menu, as every shelf page carries it
    assert 'href="rss.xml"' in page


@needs_astro
def test_ac4_the_feed_carries_the_same_items(build) -> None:
    channel = _rss((build("full") / "changes" / "rss.xml").read_text(encoding="utf-8"))
    items = channel.findall("item")
    assert [item.findtext("title") for item in items] == [subject for _, _, subject in _MERGES_NEWEST_FIRST]
    assert all(
        item.findtext("link", "").startswith(f"{SITE_URL}/changes/#") and item.findtext("pubDate") for item in items
    )


@needs_astro
def test_ac5_the_runs_page_shows_the_homes_and_the_latest_progress(build) -> None:
    page = (build("full") / "status" / "runs" / "index.html").read_text(encoding="utf-8")
    assert re.findall(r'<tr data-home="([^"]+)"', page) == ["pyforge-marshal", "pyforge-doctor"]
    assert re.findall(r'<tr data-station="([^"]+)"', page) == ["pyforge-herald", "pyforge-steward"]
    times = re.findall(r'Snapshot taken <time datetime="([^"]+)"', page)
    assert times == ["2026-10-15T09:05:00+00:00", "2026-10-15T09:06:00+00:00"]
    assert "implementation-artifacts" not in page and "changes.patch" not in page
    # site.yml's lane1.href is root-absolute (/console/), so the page carries no Lane 1 link (Story 42.1's rule).
    assert "/console/" not in page
    assert "data-pf-menu-link" in page


@needs_astro
def test_ac6_a_missing_input_is_one_line_and_the_build_passes(build) -> None:
    one = build("one-missing")
    runs = (one / "status" / "runs" / "index.html").read_text(encoding="utf-8")
    assert re.findall(r'data-input-absent="([^"]+)"', runs) == ["herald-progress.json"]
    assert re.findall(r'<tr data-home="', runs)  # the input that is there still renders
    assert 'data-input-absent="' not in (one / "changes" / "index.html").read_text(encoding="utf-8")
    none = build("none")
    absent = {
        rel: re.findall(r'data-input-absent="([^"]+)"', (none / rel).read_text(encoding="utf-8"))
        for rel in ("changes/index.html", _RUNS)
    }
    assert absent == {"changes/index.html": ["changes.json"], _RUNS: ["marshal-status.json", "herald-progress.json"]}
    assert _rss((none / "changes" / "rss.xml").read_text(encoding="utf-8")).findall("item") == []


@needs_astro
def test_an_empty_merge_list_says_so_and_the_feed_is_an_empty_channel(build) -> None:
    site = build("no-merges")
    page = (site / "changes" / "index.html").read_text(encoding="utf-8")
    assert 'class="changes-empty"' in page and "No merges to main in the last 30 days." in _text(page)
    assert 'data-input-absent="' not in page
    assert _rss((site / "changes" / "rss.xml").read_text(encoding="utf-8")).findall("item") == []


# ------------------------------------------------------------------ pages-check (the assembler)


def _assemble_pages():
    tools = REPO_ROOT / "docsite" / "tools"
    if str(tools) not in sys.path:
        sys.path.insert(0, str(tools))
    spec = importlib.util.spec_from_file_location("assemble_pages_agent_surface", tools / "assemble_pages.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _plant(root: Path, rels: tuple[str, ...]) -> Path:
    for rel in rels:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text("x", encoding="utf-8")
    return root


def test_ac7_pages_check_refuses_a_surface_with_the_flag_off(tmp_path: Path, capsys) -> None:
    ap = _assemble_pages()
    ap._check_agent_surface(tmp_path / "empty", one_generator=False, status_on=True)  # nothing there: passes
    for rel in (*_AGENT_FILES, _RUNS):
        site = _plant(tmp_path / rel.replace("/", "_"), (rel,))
        with pytest.raises(SystemExit) as exc:
            ap._check_agent_surface(site, one_generator=False, status_on=True)
        assert exc.value.code == 1
        err = capsys.readouterr().err
        assert rel in err and "pyforge.herald.pages_one_generator is off" in err


_RSS_OK = '<?xml version="1.0"?><rss version="2.0"><channel><title>t</title></channel></rss>'


def _plant_valid(root: Path, rels: tuple[str, ...]) -> Path:
    _plant(root, rels)
    if "changes/rss.xml" in rels:
        (root / "changes" / "rss.xml").write_text(_RSS_OK, encoding="utf-8")
    if "facts.json" in rels:
        (root / "facts.json").write_text("{}", encoding="utf-8")
    return root


@pytest.mark.parametrize(
    ("rel", "content", "message"),
    [
        ("changes/rss.xml", "<rss version='2.0'><channel><title>\x1b</title></channel></rss>", "not well-formed XML"),
        ("changes/rss.xml", "<feed/>", "not an RSS 2.0 document with one channel"),
        ("facts.json", "{decks:", "facts.json is not valid JSON"),
        ("facts.json", "[]", "facts.json is not a JSON object"),
    ],
)
def test_pages_check_parses_the_feed_and_facts_json(
    tmp_path: Path, capsys, rel: str, content: str, message: str
) -> None:
    """43.6's review (F2): a surface nothing parsed could publish malformed and green."""
    ap = _assemble_pages()
    site = _plant_valid(tmp_path / "site", _AGENT_FILES)
    (site / rel).write_text(content, encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        ap._check_agent_surface(site, one_generator=True, status_on=False)
    assert exc.value.code == 1
    assert message in capsys.readouterr().err


def test_the_runs_page_joins_the_shelf_link_walk(tmp_path: Path) -> None:
    """43.6's review (F4): ``status/`` is skipped by the shelf walk except Astro's runs page."""
    ap = _assemble_pages()
    container = '<div class="sl-markdown-content"><p>runs</p></div>'
    for rel in (_RUNS, "status/index.html", "status/ci/index.html", "herald/index.html"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(container, encoding="utf-8")
    walked = [page.relative_to(tmp_path).as_posix() for page in ap._iter_shelf_pages(tmp_path)]
    assert walked == [_RUNS]


def test_pages_check_requires_every_surface_with_the_flag_on(tmp_path: Path, capsys) -> None:
    ap = _assemble_pages()
    full = _plant_valid(tmp_path / "full", (*_AGENT_FILES, _RUNS))
    ap._check_agent_surface(full, one_generator=True, status_on=True)
    no_status = _plant_valid(tmp_path / "no-status", _AGENT_FILES)
    ap._check_agent_surface(no_status, one_generator=True, status_on=False)  # the runs page needs both flags
    for missing in (*_AGENT_FILES, _RUNS):
        site = _plant_valid(
            tmp_path / f"without-{missing.replace('/', '_')}", tuple(r for r in (*_AGENT_FILES, _RUNS) if r != missing)
        )
        with pytest.raises(SystemExit) as exc:
            ap._check_agent_surface(site, one_generator=True, status_on=True)
        assert exc.value.code == 1
        assert f"missing required path {missing}" in capsys.readouterr().err


def test_the_status_mount_takes_astros_runs_page_and_nothing_else(tmp_path: Path) -> None:
    ap = _assemble_pages()
    assert not ap._astro_runs_only(tmp_path / "none")
    assert ap._astro_runs_only(_plant(tmp_path / "runs", (_RUNS,)))
    assert not ap._astro_runs_only(_plant(tmp_path / "more", (_RUNS, "status/index.html")))
