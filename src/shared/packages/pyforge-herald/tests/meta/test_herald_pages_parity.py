"""Story 43.2 (spec-pyforge-herald CAP-61): the overview, gallery and deck-family pages on both paths.

Two halves, both over the same tree on each side:

* **The model** runs wherever ``node`` does. ``docs-site/src/lib/herald-pages.ts`` (node builtins only,
  imported with node's type stripping, no ``node_modules``) against ``docsite/build.py``'s
  ``collect_infographics`` / ``collect_families``: the gallery's order, titles and published names, each
  family's views, downloads and stamps, and the one-current-export refusal (AC3, AC5).
* **The rendered pages** need docs-site's ``node_modules`` and generated menu
  (``pixi run -e site docs-site-install docs-site-sidebar``) and skip naming them otherwise. They build
  Astro with ``pyforge.herald.pages_one_generator`` on, over the tracked tree and over a fixture tree,
  render the Jinja path over the same tree, and compare what each page links and offers (AC1-AC6).
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath

import pytest
import yaml
from pyforge.testing_kit import make_flag_provider_fixture
from pyforge.testing_kit.flags import flag_states

REPO_ROOT = Path(__file__).resolve().parents[6]
DOCS_SITE = REPO_ROOT / "docs-site"
HERALD_PAGES_TS = DOCS_SITE / "src" / "lib" / "herald-pages.ts"
ASTRO_BIN = DOCS_SITE / "node_modules" / "astro" / "bin" / "astro.mjs"
_GENERATED = ("src/sidebar.generated.json", "src/topnav.generated.json")
_NODE = shutil.which("node")
_RENDER_READY = _NODE is not None and ASTRO_BIN.is_file() and all((DOCS_SITE / g).is_file() for g in _GENERATED)
needs_node = pytest.mark.skipif(_NODE is None, reason="node is not on PATH")
needs_astro = pytest.mark.skipif(
    not _RENDER_READY,
    reason="docs-site is not installed: pixi run -e site docs-site-install docs-site-sidebar",
)
_BACKBAR = 'class="ig-backbar"'
_FLAG = "pyforge.herald.pages_one_generator"
flag_provider = make_flag_provider_fixture()


# ------------------------------------------------------------------ the two paths' code


def _load_build() -> object:
    spec = importlib.util.spec_from_file_location("docsite_build_parity", REPO_ROOT / "docsite" / "build.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def build_mod(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PYFORGE_CI_SURFACES_TILE", "0")
    monkeypatch.setenv("PYFORGE_STATUS_PAGES", "0")
    monkeypatch.delenv("PYFORGE_PAGES_ONE_GENERATOR", raising=False)
    return _load_build()


_MODEL_SCRIPT = """
import { collectFamilies, collectInfographics, gitCommit, MoreThanOneCurrentExport } from %(lib)s;
const [site, root] = %(args)s;
try {
  const commit = gitCommit(root);
  const infographics = collectInfographics(site, root);
  process.stdout.write(JSON.stringify({ commit, infographics, families: collectFamilies(infographics, root, commit) }));
} catch (exc) {
  if (!(exc instanceof MoreThanOneCurrentExport)) throw exc;
  process.stdout.write(JSON.stringify({ error: exc.message, files: exc.files }));
}
"""


def _ts_model(site: dict, root: Path) -> dict:
    script = _MODEL_SCRIPT % {
        "lib": json.dumps(HERALD_PAGES_TS.as_uri()),
        "args": json.dumps([site, str(root)]),
    }
    done = subprocess.run(
        [_NODE or "node", "--experimental-strip-types", "--input-type=module", "-e", script],
        cwd=DOCS_SITE,
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


def _site_yml(root: Path) -> dict:
    return yaml.safe_load((root / "docsite" / "content" / "site.yml").read_text(encoding="utf-8"))


# ------------------------------------------------------------------ a fixture tree

_POSTER = """<!DOCTYPE html><html><head><meta charset="utf-8"><title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@400&amp;display=swap" rel="stylesheet">
</head><body><main><h1>{title}</h1><p>{body}</p></main></body></html>
"""


def _write(path: Path, text: str | bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(text, bytes):
        path.write_bytes(text)
    else:
        path.write_text(text, encoding="utf-8")
    return path


def _fixture_tree(root: Path, *, second_pptx: bool = False) -> Path:
    """Two families and a third deck with no poster: Alpha with every view, a stamped Infographic Deck and
    a stamped PPTX; Beta with no Executive Summary, no PPTX and no sidecar; Gamma with only a facts.yaml."""
    site = _site_yml(REPO_ROOT)
    site["infographics"] = {
        "include": [
            "presentations/fx-alpha/project/*Infographic standalone.html",
            "presentations/fx-beta/project/*Infographic standalone.html",
            "presentations/fx-gamma/project/*Infographic standalone.html",
        ],
        "exclude": [],
        "inject_backbar": True,
        "overrides": {
            "presentations/fx-alpha/project/Alpha Infographic standalone.html": {
                "title": "Alpha",
                "description": "The first fixture family.",
                "order": 20,
            },
            "Beta Infographic standalone.html": {"order": 10},
        },
    }
    content = root / "docsite" / "content"
    _write(content / "site.yml", yaml.safe_dump(site, sort_keys=False, allow_unicode=True))
    shutil.copy2(REPO_ROOT / "docsite" / "content" / "dossier.yml", content / "dossier.yml")

    alpha = root / "presentations" / "fx-alpha"
    _write(
        alpha / "project" / "Alpha Infographic standalone.html", _POSTER.format(title="Alpha poster", body="a" * 400)
    )
    deck = _write(
        alpha / "project" / "Alpha - Infographic Deck.dc.html", _POSTER.format(title="Alpha deck", body="d" * 300)
    )
    _write(Path(f"{deck}.stamp.json"), json.dumps({"tree": "0123456789abcdef", "etag": "etag-alpha-deck-1"}))
    _write(
        alpha / "project" / "Alpha - Executive Summary.dc.html", _POSTER.format(title="Alpha summary", body="e" * 200)
    )
    pptx = _write(alpha / "src" / "pptx" / "fx-alpha-deck-2026-01-01.pptx", b"PK\x03\x04alpha")
    _write(Path(f"{pptx}.stamp.json"), json.dumps({"tree": "fedcba9876543210", "etag": "etag-alpha-pptx"}))
    if second_pptx:
        _write(alpha / "src" / "pptx" / "fx-alpha-deck-2026-02-01.pptx", b"PK\x03\x04alpha-2")
    _write(alpha / "src" / "marp" / "fx-alpha-deck-2026-01-01.md", "# Alpha\n")
    _write(alpha / "src" / "marp" / "fx-alpha-narration-2026-01-02.md", "# Alpha narration\n")
    _write(
        alpha / "facts.yaml",
        "deck: fx-alpha\nderived_at: '2026-01-02T00:00:00Z'\nfacts:\n  - id: one\n    value: '1'\n",
    )

    beta = root / "presentations" / "fx-beta"
    _write(beta / "project" / "Beta Infographic standalone.html", _POSTER.format(title="Beta &amp; Co", body="b" * 400))
    _write(beta / "project" / "Beta - Infographic Deck.dc.html", _POSTER.format(title="Beta deck", body="d" * 300))
    _write(beta / "src" / "marp" / "fx-beta-2026-02-02.md", "# Beta\n")
    _write(beta / "facts.yaml", "deck: fx-beta\nfacts: []\n")

    _write(root / "presentations" / "fx-gamma" / "facts.yaml", "deck: fx-gamma\nfacts: []\n")
    return root


# ------------------------------------------------------------------ the model half (always, where node is)


def _py_gallery(igs: list[dict]) -> list[tuple]:
    return [(i["out_name"], i["title"], i["source"], i["order"], i["description"]) for i in igs]


def _ts_gallery(igs: list[dict]) -> list[tuple]:
    return [(i["outName"], i["title"], i["source"], i["order"], i["description"]) for i in igs]


def _py_families(fams: list[dict], root: Path) -> dict[str, dict]:
    def rel(path: Path) -> str:
        return path.relative_to(root).as_posix()

    out: dict[str, dict] = {}
    for fam in fams:
        views = {
            key: (rel(fam[key]["path"]), fam[key]["stamp"])
            for key in ("infographic_deck", "executive_summary")
            if fam[key] is not None
        }
        out[fam["slug"]] = {
            "title": fam["title"],
            "poster": (fam["poster"]["out_name"], fam["poster"]["stamp"]),
            "views": views,
            "pptx": [(d["name"], d["bytes"], d["stamp"]) for d in fam["pptx"]],
            "marp": [(d["name"], d["bytes"], d["stamp"]) for d in fam["marp"]],
        }
    return out


def _ts_families(fams: list[dict]) -> dict[str, dict]:
    return {
        fam["slug"]: {
            "title": fam["title"],
            "poster": (fam["poster"]["outName"], fam["poster"]["stamp"]),
            "views": {v["key"]: (v["source"], v["stamp"]) for v in fam["views"]},
            "pptx": [(d["name"], d["bytes"], d["stamp"]) for d in fam["pptx"]],
            "marp": [(d["name"], d["bytes"], d["stamp"]) for d in fam["marp"]],
        }
        for fam in fams
    }


def _assert_model_parity(build_mod, root: Path) -> dict:
    site = _site_yml(root)
    ts = _ts_model(site, root)
    assert "error" not in ts, ts.get("error")
    commit = build_mod.git_commit(root)
    assert ts["commit"] == commit
    igs = build_mod.collect_infographics(site, root)
    assert _ts_gallery(ts["infographics"]) == _py_gallery(igs), "the gallery differs between the paths"
    py_fams = _py_families(build_mod.collect_families(igs, root, commit), root)
    ts_fams = _ts_families(ts["families"])
    assert list(ts_fams) == list(py_fams), "the families differ between the paths"
    for slug, want in py_fams.items():
        got = json.loads(json.dumps(ts_fams[slug]))
        assert got == json.loads(json.dumps(want)), f"{slug}: the family differs between the paths"
    return ts


@needs_node
def test_ac3_the_model_matches_the_jinja_path_on_the_tracked_tree(build_mod) -> None:
    ts = _assert_model_parity(build_mod, REPO_ROOT)
    assert [i["title"] for i in ts["infographics"]] == [
        "PyForge Genesis",
        "PyForge Unifying Strategy",
        "Atlas",
        "Doctor",
        "Herald",
        "Marshal",
        "Mason",
        "Scribe",
        "Steward",
        "Warden",
    ]
    assert len(ts["families"]) == 10


@needs_node
def test_ac3_the_model_matches_the_jinja_path_on_a_fixture_tree(build_mod, tmp_path: Path) -> None:
    ts = _assert_model_parity(build_mod, _fixture_tree(tmp_path))
    assert [(i["title"], i["outName"]) for i in ts["infographics"]] == [
        ("Beta & Co", "beta-co.html"),
        ("Alpha", "alpha.html"),
    ]
    fams = {f["slug"]: f for f in ts["families"]}
    assert sorted(fams) == ["fx-alpha", "fx-beta"]  # fx-gamma has no poster: no family, as build.py
    assert [v["key"] for v in fams["fx-beta"]["views"]] == ["infographic_deck"]  # no Executive Summary
    assert fams["fx-alpha"]["views"][0]["stamp"] == {"tree": "0123456789ab", "etag": "etag-alpha-d"}
    beta_md = fams["fx-beta"]["marp"][0]
    digest = hashlib.sha256((tmp_path / beta_md["source"]).read_bytes()).hexdigest()[:12]
    assert beta_md["stamp"] == {"tree": "unknown", "etag": digest}  # no sidecar, no git: commit and hash


@needs_node
def test_ac5_two_dated_files_of_one_kind_are_refused_naming_both(tmp_path: Path) -> None:
    root = _fixture_tree(tmp_path, second_pptx=True)
    ts = _ts_model(_site_yml(root), root)
    assert ts.get("files") == [
        "presentations/fx-alpha/src/pptx/fx-alpha-deck-2026-01-01.pptx",
        "presentations/fx-alpha/src/pptx/fx-alpha-deck-2026-02-01.pptx",
    ]
    assert "fx-alpha-deck-2026-01-01.pptx" in ts["error"] and "fx-alpha-deck-2026-02-01.pptx" in ts["error"]


# ------------------------------------------------------------------ the rendered half


class _Page(HTMLParser):
    """What a herald page links and offers: its body's anchors (not the shared menu), its cards, its
    downloads and its preview frames."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []
        self.shots: list[tuple[str, str]] = []
        self.downloads: list[str] = []
        self.dl_meta: list[str] = []
        self.frames: list[dict[str, str]] = []
        self._shot: str | None = None
        self._capture: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: v or "" for k, v in attrs}
        if tag == "a" and "href" in a and "data-pf-menu-link" not in a and "site-brand" not in a.get("class", ""):
            self.hrefs.append(a["href"])
            if "shot" in a.get("class", "").split():
                self._shot = a["href"]
            if "download" in a:
                self._capture, self._text = "download", []
        elif tag == "h3" and self._shot is not None:
            self._capture, self._text = "shot", []
        elif tag == "span" and "dl-meta" in a.get("class", ""):
            self._capture, self._text = "meta", []
        elif tag == "iframe":
            self.frames.append(a)

    def handle_endtag(self, tag: str) -> None:
        text = " ".join("".join(self._text).split())
        if tag == "a" and self._capture == "download":
            self.downloads.append(text)
            self._capture = None
        elif tag == "h3" and self._capture == "shot":
            self.shots.append((self._shot or "", text))
            self._shot, self._capture = None, None
        elif tag == "span" and self._capture == "meta":
            self.dl_meta.append(text)
            self._capture = None
        if tag == "a":
            self._shot = None

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._text.append(data)


def _page(path: Path) -> _Page:
    page = _Page()
    page.feed(path.read_text(encoding="utf-8"))
    page.close()
    return page


def _astro(out: Path, *, flag: bool, root: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k not in ("HERALD_PAGES_REPO_ROOT", "PYTEST_ADDOPTS")}
    env.update({"PYFORGE_PAGES_ONE_GENERATOR": "1" if flag else "0", "PYFORGE_CI_SURFACES_TILE": "0"})
    env["PYFORGE_STATUS_PAGES"] = "0"
    if root is not None:
        env["HERALD_PAGES_REPO_ROOT"] = str(root)
    return subprocess.run(
        [_NODE or "node", str(ASTRO_BIN), "build", "--outDir", str(out)],
        cwd=DOCS_SITE,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _both_paths(build_mod, tmp: Path, root: Path) -> tuple[Path, Path]:
    """``(jinja, astro)``: the herald mount rendered by each path over ``root``. The Astro side is the
    assembled shape -- Astro's pages, then the herald build's twins and downloads beside them."""
    build_mod.CONTENT = root / "docsite" / "content"
    jinja = tmp / "jinja"
    build_mod.build(jinja, root, one_generator=False, status_pages=False)
    done = _astro(tmp / "astro", flag=True, root=root)
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-3000:]
    astro = tmp / "astro" / "herald"
    build_mod.build(astro, root, one_generator=True, status_pages=False)
    return jinja, astro


def _assert_rendered_parity(jinja: Path, astro: Path) -> None:
    gallery_j, gallery_a = _page(jinja / "infographics/index.html"), _page(astro / "infographics/index.html")
    assert gallery_a.shots == gallery_j.shots, "the gallery's ordered (href, title) list differs between the paths"
    assert gallery_a.frames and all(f.get("loading") == "lazy" for f in gallery_a.frames), "a preview is not lazy"
    for frame in gallery_a.frames:
        assert (astro / "infographics" / frame["src"]).resolve().is_file(), f"preview {frame['src']} is not a twin"

    assert set(_page(astro / "decks/index.html").hrefs) == set(_page(jinja / "decks/index.html").hrefs)
    slugs_j = sorted(p.parent.name for p in (jinja / "decks").glob("*/index.html"))
    slugs_a = sorted(p.parent.name for p in (astro / "decks").glob("*/index.html"))
    assert slugs_a == slugs_j, "the family pages differ between the paths"
    for slug in slugs_j:
        page_j, page_a = _page(jinja / "decks" / slug / "index.html"), _page(astro / "decks" / slug / "index.html")
        missing, extra = set(page_j.hrefs) - set(page_a.hrefs), set(page_a.hrefs) - set(page_j.hrefs)
        assert not missing and not extra, f"{slug}: hrefs only on the Jinja path {missing}, only on Astro {extra}"
        assert set(page_a.downloads) == set(page_j.downloads), (
            f"{slug}: downloads only on the Jinja path {set(page_j.downloads) - set(page_a.downloads)}, "
            f"only on Astro {set(page_a.downloads) - set(page_j.downloads)}"
        )
        assert sorted(page_a.dl_meta) == sorted(page_j.dl_meta), f"{slug}: a download's size or stamp differs"
        for href in page_a.hrefs:
            target = (astro / "decks" / slug / href.split("#", 1)[0]).resolve()
            assert target.is_file() or (target / "index.html").is_file(), f"{slug}: {href} does not resolve"


def _assert_twins_wrapped_never_edited(build_mod, astro: Path, root: Path, infographics: list[dict]) -> None:
    """AC4: each twin is the tracked file with only Story 31.3's font-link vendoring, carries no back-bar,
    and its reader's page carries the back-bar and frames it."""
    readers: list[tuple[Path, Path, Path]] = []  # (reader page, twin, tracked source)
    for ig in infographics:
        readers.append((astro / "infographics" / ig["outName"], astro / ig["twin"], root / ig["source"]))
    for fam in build_mod.collect_families(build_mod.collect_infographics(_site_yml(root), root), root, ""):
        for key, name in (
            ("infographic_deck", "infographic-deck.html"),
            ("executive_summary", "executive-summary.html"),
        ):
            if fam[key] is not None:
                twin = astro / "twins" / "decks" / fam["slug"] / name
                readers.append((astro / "decks" / fam["slug"] / name, twin, fam[key]["path"]))
    assert readers
    for reader, twin, source in readers:
        rel = twin.relative_to(astro).as_posix()
        fonts = "../" * rel.count("/") + "assets/fonts/fonts.css"
        want = build_mod.rewrite_google_font_links(source.read_text(encoding="utf-8", errors="replace"), fonts)
        got = twin.read_bytes()
        assert hashlib.sha256(got).hexdigest() == hashlib.sha256(want.encode("utf-8")).hexdigest(), (
            f"{rel} is not its tracked file {source.relative_to(root).as_posix()} (font-link vendoring aside)"
        )
        assert _BACKBAR.encode() not in got, f"{rel} carries the back-bar"
        assert b"fonts.googleapis.com" not in got, f"{rel} names fonts.googleapis.com"
        page = reader.read_text(encoding="utf-8")
        assert _BACKBAR in page, f"{reader.relative_to(astro).as_posix()} has no back-bar"
        frames = _page(reader).frames
        assert len(frames) == 1, reader
        assert (reader.parent / frames[0]["src"]).resolve() == twin.resolve(), f"{reader} does not frame {rel}"


@needs_astro
def test_ac1_to_ac4_the_tracked_tree_renders_alike_on_both_paths(build_mod, tmp_path: Path) -> None:
    jinja, astro = _both_paths(build_mod, tmp_path, REPO_ROOT)
    _assert_rendered_parity(jinja, astro)
    assert len(_page(astro / "infographics/index.html").shots) == 10
    assert len(list((astro / "decks").glob("*/index.html"))) == 10
    for page in (astro / "index.html", astro / "infographics/index.html", astro / "decks/index.html"):
        assert '<meta name="generator" content="Astro' in page.read_text(encoding="utf-8"), page
    ts = _ts_model(_site_yml(REPO_ROOT), REPO_ROOT)
    _assert_twins_wrapped_never_edited(build_mod, astro, REPO_ROOT, ts["infographics"])


@needs_astro
def test_ac2_ac3_a_fixture_tree_renders_alike_on_both_paths(build_mod, tmp_path: Path) -> None:
    root = _fixture_tree(tmp_path / "tree")
    jinja, astro = _both_paths(build_mod, tmp_path, root)
    _assert_rendered_parity(jinja, astro)
    assert _page(astro / "infographics/index.html").shots == [("beta-co.html", "Beta & Co"), ("alpha.html", "Alpha")]
    assert not (astro / "decks" / "fx-gamma").exists()  # facts.yaml and no poster: no page, as build.py
    beta = _page(astro / "decks/fx-beta/index.html")
    assert "executive-summary.html" not in beta.hrefs and "infographic-deck.html" in beta.hrefs
    alpha = (astro / "decks/fx-alpha/index.html").read_text(encoding="utf-8")
    assert "etag etag-alpha-p" in alpha and "tree fedcba987654" in alpha  # the sidecars' stamps
    assert "facts.yaml" in alpha
    ts = _ts_model(_site_yml(root), root)
    _assert_twins_wrapped_never_edited(build_mod, astro, root, ts["infographics"])


@needs_astro
def test_ac5_the_build_fails_naming_both_dated_files(tmp_path: Path) -> None:
    root = _fixture_tree(tmp_path / "tree", second_pptx=True)
    done = _astro(tmp_path / "astro", flag=True, root=root)
    assert done.returncode != 0
    log = done.stdout + done.stderr
    assert "fx-alpha-deck-2026-01-01.pptx" in log and "fx-alpha-deck-2026-02-01.pptx" in log


@needs_astro
def test_ac6_flag_off_astro_emits_none_of_the_three_page_kinds(tmp_path: Path) -> None:
    done = _astro(tmp_path / "astro", flag=False)
    assert done.returncode == 0, done.stderr[-3000:]
    herald = tmp_path / "astro" / "herald"
    emitted = sorted(PurePosixPath(p.relative_to(herald).as_posix()) for p in herald.rglob("*") if p.is_file())
    assert not [p for p in emitted if p.parts[0] in ("infographics", "decks") or str(p) == "index.html"], emitted


@flag_states(_FLAG)
def test_ac6_the_flag_selects_what_the_jinja_build_writes(
    build_mod, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, flag_provider: dict[str, bool]
) -> None:
    """On, the herald build writes only the twins, the downloads, the assets and the artifact build, and never
    deletes an Astro page beside them; off, it writes every page as before and no twin."""
    on = flag_provider[_FLAG]
    monkeypatch.setenv("PYFORGE_PAGES_ONE_GENERATOR", "1" if on else "0")  # as the Guild step exports it
    out = tmp_path / "herald"
    astro_page = _write(out / "index.html", "<html>Astro's overview</html>")
    result = build_mod.build(out, REPO_ROOT, status_pages=False)
    assert result["one_generator"] is on
    assert build_mod.check(out, result) == 0
    first = result["infographics"][0]
    if not on:
        assert astro_page.read_text(encoding="utf-8") != "<html>Astro's overview</html>"  # the Jinja overview
        assert not (out / "twins").exists()
        assert _BACKBAR in (out / "infographics" / first["out_name"]).read_text(encoding="utf-8")
        return
    assert astro_page.read_text(encoding="utf-8") == "<html>Astro's overview</html>"  # never deleted
    assert sorted(p.name for p in out.iterdir()) == [".nojekyll", "artifact", "assets", "decks", "index.html", "twins"]
    assert not list((out / "decks").glob("*/index.html")) and not (out / "infographics").exists()
    twin = out / first["twin"]
    twin.write_text(twin.read_text(encoding="utf-8") + '<div class="ig-backbar"></div>', encoding="utf-8")
    assert build_mod.check(out, result) == 1  # a twin that carries the back-bar is refused
