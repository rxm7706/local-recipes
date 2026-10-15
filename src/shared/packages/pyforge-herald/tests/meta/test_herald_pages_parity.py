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
import subprocess
import sys
from pathlib import Path, PurePosixPath

import pytest
from pages_astro import (
    DOCS_SITE,
    NODE,
    astro_build,
    fixture_tree,
    load_build,
    needs_astro,
    needs_node,
    page,
    site_yml,
    write,
)
from pyforge.testing_kit import make_flag_provider_fixture
from pyforge.testing_kit.flags import flag_states

REPO_ROOT = Path(__file__).resolve().parents[6]
HERALD_PAGES_TS = DOCS_SITE / "src" / "lib" / "herald-pages.ts"
_BACKBAR = 'class="ig-backbar"'
_FLAG = "pyforge.herald.pages_one_generator"
flag_provider = make_flag_provider_fixture()


@pytest.fixture
def build_mod(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PYFORGE_CI_SURFACES_TILE", "0")
    monkeypatch.setenv("PYFORGE_STATUS_PAGES", "0")
    monkeypatch.delenv("PYFORGE_PAGES_ONE_GENERATOR", raising=False)
    # Both paths stamp an unsidecarred export with GITHUB_SHA's first seven before git; Actions sets it.
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    return load_build("docsite_build_parity")


def _load_assemble_pages():
    spec = importlib.util.spec_from_file_location(
        "assemble_pages_parity", REPO_ROOT / "docsite" / "tools" / "assemble_pages.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


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
        [NODE or "node", "--experimental-strip-types", "--input-type=module", "-e", script],
        cwd=DOCS_SITE,
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


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
    site = site_yml(root)
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
def test_ac3_the_model_matches_the_jinja_path_on_afixture_tree(build_mod, tmp_path: Path) -> None:
    ts = _assert_model_parity(build_mod, fixture_tree(tmp_path))
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
def test_ac5_two_dated_files_of_one_kind_are_refused_naming_both(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    root = fixture_tree(tmp_path, second_pptx=True)
    ts = _ts_model(site_yml(root), root)
    assert ts.get("files") == [
        "presentations/fx-alpha/src/pptx/fx-alpha-deck-2026-01-01.pptx",
        "presentations/fx-alpha/src/pptx/fx-alpha-deck-2026-02-01.pptx",
    ]
    assert "fx-alpha-deck-2026-01-01.pptx" in ts["error"] and "fx-alpha-deck-2026-02-01.pptx" in ts["error"]


# ------------------------------------------------------------------ the rendered half


def _both_paths(build_mod, tmp: Path, root: Path) -> tuple[Path, Path]:
    """``(jinja, astro)``: the herald mount rendered by each path over ``root``. The Astro side is the
    assembled shape -- Astro's pages, twins and downloads, then the herald build's assets beside them."""
    build_mod.CONTENT = root / "docsite" / "content"
    jinja = tmp / "jinja"
    build_mod.build(jinja, root, one_generator=False, status_pages=False)
    done = astro_build(tmp / "astro", flag=True, root=root)
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-3000:]
    astro = tmp / "astro" / "herald"
    build_mod.build(astro, root, one_generator=True, status_pages=False)
    return jinja, astro


def _assert_rendered_parity(jinja: Path, astro: Path) -> None:
    gallery_j, gallery_a = page(jinja / "infographics/index.html"), page(astro / "infographics/index.html")
    assert gallery_a.shots == gallery_j.shots, "the gallery's ordered (href, title) list differs between the paths"
    assert gallery_a.frames and all(f.get("loading") == "lazy" for f in gallery_a.frames), "a preview is not lazy"
    for frame in gallery_a.frames:
        assert (astro / "infographics" / frame["src"]).resolve().is_file(), f"preview {frame['src']} is not a twin"

    assert set(page(astro / "decks/index.html").hrefs) == set(page(jinja / "decks/index.html").hrefs)
    slugs_j = sorted(p.parent.name for p in (jinja / "decks").glob("*/index.html"))
    slugs_a = sorted(p.parent.name for p in (astro / "decks").glob("*/index.html"))
    assert slugs_a == slugs_j, "the family pages differ between the paths"
    for slug in slugs_j:
        page_j, page_a = page(jinja / "decks" / slug / "index.html"), page(astro / "decks" / slug / "index.html")
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
    for fam in build_mod.collect_families(build_mod.collect_infographics(site_yml(root), root), root, ""):
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
        fonts = "../" * rel.count("/") + "fonts.css"  # Story 43.4: the @fontsource faces
        want = build_mod.rewrite_google_font_links(source.read_text(encoding="utf-8", errors="replace"), fonts)
        got = twin.read_bytes()
        assert hashlib.sha256(got).hexdigest() == hashlib.sha256(want.encode("utf-8")).hexdigest(), (
            f"{rel} is not its tracked file {source.relative_to(root).as_posix()} (font-link vendoring aside)"
        )
        changes = _load_assemble_pages()._font_vendoring_only(got, source.read_bytes())  # an independent line diff
        assert changes == [], f"{rel}: {changes}"
        assert _BACKBAR.encode() not in got, f"{rel} carries the back-bar"
        assert b"fonts.googleapis.com" not in got, f"{rel} names fonts.googleapis.com"
        text = reader.read_text(encoding="utf-8")
        assert _BACKBAR in text, f"{reader.relative_to(astro).as_posix()} has no back-bar"
        frames = page(reader).frames
        assert len(frames) == 1, reader
        assert (reader.parent / frames[0]["src"]).resolve() == twin.resolve(), f"{reader} does not frame {rel}"


@needs_astro
def test_ac1_to_ac4_the_tracked_tree_renders_alike_on_both_paths(build_mod, tmp_path: Path) -> None:
    jinja, astro = _both_paths(build_mod, tmp_path, REPO_ROOT)
    _assert_rendered_parity(jinja, astro)
    assert len(page(astro / "infographics/index.html").shots) == 10
    assert len(list((astro / "decks").glob("*/index.html"))) == 10
    for built in (astro / "index.html", astro / "infographics/index.html", astro / "decks/index.html"):
        assert '<meta name="generator" content="Astro' in built.read_text(encoding="utf-8"), built
    ts = _ts_model(site_yml(REPO_ROOT), REPO_ROOT)
    _assert_twins_wrapped_never_edited(build_mod, astro, REPO_ROOT, ts["infographics"])


@needs_astro
def test_ac2_ac3_a_fixture_tree_renders_alike_on_both_paths(build_mod, tmp_path: Path) -> None:
    root = fixture_tree(tmp_path / "tree")
    jinja, astro = _both_paths(build_mod, tmp_path, root)
    _assert_rendered_parity(jinja, astro)
    assert page(astro / "infographics/index.html").shots == [("beta-co.html", "Beta & Co"), ("alpha.html", "Alpha")]
    assert not (astro / "decks" / "fx-gamma").exists()  # facts.yaml and no poster: no page, as build.py
    beta = page(astro / "decks/fx-beta/index.html")
    assert "executive-summary.html" not in beta.hrefs and "infographic-deck.html" in beta.hrefs
    alpha = (astro / "decks/fx-alpha/index.html").read_text(encoding="utf-8")
    assert "etag etag-alpha-p" in alpha and "tree fedcba987654" in alpha  # the sidecars' stamps
    assert "facts.yaml" in alpha
    ts = _ts_model(site_yml(root), root)
    _assert_twins_wrapped_never_edited(build_mod, astro, root, ts["infographics"])


@needs_astro
def test_ac5_the_build_fails_naming_both_dated_files(tmp_path: Path) -> None:
    root = fixture_tree(tmp_path / "tree", second_pptx=True)
    done = astro_build(tmp_path / "astro", flag=True, root=root)
    assert done.returncode != 0
    log = done.stdout + done.stderr
    assert "fx-alpha-deck-2026-01-01.pptx" in log and "fx-alpha-deck-2026-02-01.pptx" in log


@needs_astro
def test_ac6_flag_off_astro_emits_none_of_the_three_page_kinds(tmp_path: Path) -> None:
    done = astro_build(tmp_path / "astro", flag=False)
    assert done.returncode == 0, done.stderr[-3000:]
    herald = tmp_path / "astro" / "herald"
    emitted = sorted(PurePosixPath(p.relative_to(herald).as_posix()) for p in herald.rglob("*") if p.is_file())
    assert not [p for p in emitted if p.parts[0] in ("infographics", "decks") or str(p) == "index.html"], emitted


@flag_states(_FLAG)
def test_ac6_the_flag_selects_what_the_jinja_build_writes(
    build_mod, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, flag_provider: dict[str, bool]
) -> None:
    """On, the herald build writes only the assets and the artifact build -- Astro writes the pages and, since
    Story 43.3, serves the twins and downloads from docs-site/public/ -- and never deletes an Astro page beside
    them; off, it writes every page, view and download as before and no twin."""
    on = flag_provider[_FLAG]
    monkeypatch.setenv("PYFORGE_PAGES_ONE_GENERATOR", "1" if on else "0")  # as the Guild step exports it
    out = tmp_path / "herald"
    astro_page = write(out / "index.html", "<html>Astro's overview</html>")
    result = build_mod.build(out, REPO_ROOT, status_pages=False)
    assert result["one_generator"] is on
    assert build_mod.check(out, result) == 0
    if not on:
        assert astro_page.read_text(encoding="utf-8") != "<html>Astro's overview</html>"  # the Jinja overview
        assert not (out / "twins").exists()
        first = result["infographics"][0]["out_name"]
        assert _BACKBAR in (out / "infographics" / first).read_text(encoding="utf-8")
        assert list((out / "decks").glob("*/downloads/*"))
        return
    assert astro_page.read_text(encoding="utf-8") == "<html>Astro's overview</html>"  # never deleted
    assert sorted(p.name for p in out.iterdir()) == [".nojekyll", "artifact", "assets", "index.html"]


_VENDOR_SCRIPT = """
import fs from 'node:fs';
import { vendorFontLinks } from %(lib)s;
const jobs = %(jobs)s;
process.stdout.write(JSON.stringify(jobs.map(([file, href]) => vendorFontLinks(fs.readFileSync(file, 'utf8'), href))));
"""


@needs_node
def test_ac4_the_vendoring_changes_only_font_links_on_every_tracked_twin(build_mod) -> None:
    """AC4 as amended (Story 43.2's ruling), in the always-run half: the Astro side's ``vendorFontLinks`` -- what
    ``populate-public.ts`` writes each twin with -- over every tracked twin, read against the tracked bytes by
    ``assemble_pages._font_vendoring_only``, a line diff that knows nothing of either implementation: the only lines
    lost name a Google Fonts origin, the only lines gained are one vendored font link and blank lines."""
    igs = build_mod.collect_infographics(site_yml(REPO_ROOT), REPO_ROOT)
    jobs = [(str(ig["path"]), "../../fonts.css") for ig in igs]
    for fam in build_mod.collect_families(igs, REPO_ROOT, ""):
        for key in ("infographic_deck", "executive_summary"):
            if fam[key] is not None:
                jobs.append((str(fam[key]["path"]), "../../../fonts.css"))
    assert len(jobs) > len(igs), "no family view to read"
    script = _VENDOR_SCRIPT % {"lib": json.dumps(HERALD_PAGES_TS.as_uri()), "jobs": json.dumps(jobs)}
    done = subprocess.run(
        [NODE or "node", "--experimental-strip-types", "--input-type=module", "-e", script],
        cwd=DOCS_SITE,
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    assemble_pages = _load_assemble_pages()
    for (file, _), published in zip(jobs, json.loads(done.stdout), strict=True):
        raw = published.encode("utf-8")
        assert assemble_pages._font_vendoring_only(raw, Path(file).read_bytes()) == [], file
        assert b"fonts.googleapis.com" not in raw and b"fonts.gstatic.com" not in raw, file
