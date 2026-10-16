"""Story 43.2's model, judged by literal oracles (spec-pyforge-herald CAP-61 on CAP-35, CAP-53 and CAP-55; the 43.7
review, F2 and F3).

``docs-site/src/lib/herald-pages.ts`` reads the gallery, the deck families, their downloads and their stamps, and
refuses a second current export of a kind. Until Story 43.7 the parity test held it equal to the Jinja path; with that
path gone, these tests hold it to what the tree says, literally. They need only node (the module imports node builtins
and no ``node_modules``), so they run in every CI lane, the coverage leg too, which installs no docs-site:

* the tracked gallery's ten titles in their order, and its ten families;
* the fixture tree's override and ``order`` sort, its published names, a deck with no poster (no family), a family
  without an Executive Summary, the sidecar stamp and the ``unstamped`` content-hash stamp;
* two dated exports of one kind refused, naming both files (CAP-53);
* every tracked twin as ``populate-public`` writes it (``publishedTwin``) changed only in its font links -- the
  retired assembler's vendoring-only oracle, now over every real twin, not the fixture's five.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from pages_astro import DOCS_SITE, REPO_ROOT, fixture_tree, font_vendoring_only, needs_node, site_yml, ts

HERALD_PAGES_TS = DOCS_SITE / "src" / "lib" / "herald-pages.ts"

pytestmark = needs_node

_MODEL = """
try {
  const infographics = m.collectInfographics(inp.site, inp.root);
  return { infographics, families: m.collectFamilies(infographics, inp.root) };
} catch (exc) {
  if (!(exc instanceof m.MoreThanOneCurrentExport)) throw exc;
  return { refused: exc.name, files: exc.files, message: exc.message };
}
"""


def _model(root: Path) -> dict:
    result = ts(HERALD_PAGES_TS, _MODEL, site=site_yml(root), root=str(root))
    assert isinstance(result, dict) and "error" not in result, result
    return result


def test_the_tracked_gallery_lists_its_ten_infographics_in_order_and_ten_families() -> None:
    model = _model(REPO_ROOT)
    assert [(i["title"], i["outName"]) for i in model["infographics"]] == [
        ("PyForge Genesis", "pyforge-genesis.html"),
        ("PyForge Unifying Strategy", "pyforge-unifying-strategy.html"),
        ("Atlas", "atlas.html"),
        ("Doctor", "doctor.html"),
        ("Herald", "herald.html"),
        ("Marshal", "marshal.html"),
        ("Mason", "mason.html"),
        ("Scribe", "scribe.html"),
        ("Steward", "steward.html"),
        ("Warden", "warden.html"),
    ]
    families = model["families"]
    assert [f["slug"] for f in families] == [
        "pyforge-genesis",
        "pyforge-unifying-strategy",
        "pyforge-atlas",
        "pyforge-doctor",
        "pyforge-herald",
        "pyforge-marshal",
        "pyforge-mason",
        "pyforge-scribe",
        "pyforge-steward",
        "pyforge-warden",
    ]
    assert all([v["key"] for v in f["views"]] == ["infographic_deck", "executive_summary"] for f in families)


def test_the_fixture_tree_sorts_names_stamps_and_groups_as_the_tree_says(tmp_path: Path) -> None:
    root = fixture_tree(tmp_path)
    model = _model(root)
    # the overrides: Beta's order 10 (by file name) before Alpha's 20 (by path), Beta titled by its own <title>
    assert [(i["title"], i["outName"], i["order"]) for i in model["infographics"]] == [
        ("Beta & Co", "beta-co.html", 10),
        ("Alpha", "alpha.html", 20),
    ]
    assert [i["twin"] for i in model["infographics"]] == [
        "twins/infographics/beta-co.html",
        "twins/infographics/alpha.html",
    ]
    assert model["infographics"][1]["description"] == "The first fixture family."
    families = {f["slug"]: f for f in model["families"]}
    assert list(families) == ["fx-beta", "fx-alpha"]  # fx-gamma has a facts.yaml and no poster: no family
    alpha, beta = families["fx-alpha"], families["fx-beta"]
    assert [(v["key"], v["outName"], v["twin"]) for v in alpha["views"]] == [
        ("infographic_deck", "infographic-deck.html", "twins/decks/fx-alpha/infographic-deck.html"),
        ("executive_summary", "executive-summary.html", "twins/decks/fx-alpha/executive-summary.html"),
    ]
    assert [v["key"] for v in beta["views"]] == ["infographic_deck"]  # no Executive Summary
    assert beta["pptx"] == []
    # a sidecar's tree and etag, each cut to twelve characters
    assert alpha["views"][0]["stamp"] == {"tree": "0123456789ab", "etag": "etag-alpha-d"}
    assert [(d["name"], d["stamp"]) for d in alpha["pptx"]] == [
        ("fx-alpha-deck-2026-01-01.pptx", {"tree": "fedcba987654", "etag": "etag-alpha-p"}),
    ]
    # no sidecar: `unstamped` and the file's own content hash, never the build's commit
    for item in (*alpha["marp"], *beta["marp"], beta["views"][0], beta["poster"], alpha["views"][1]):
        digest = hashlib.sha256((root / item["source"]).read_bytes()).hexdigest()[:12]
        assert item["stamp"] == {"tree": "unstamped", "etag": digest}, item["source"]
    assert [d["name"] for d in alpha["marp"]] == ["fx-alpha-narration-2026-01-02.md", "fx-alpha-deck-2026-01-01.md"]


def test_two_dated_exports_of_one_kind_are_refused_naming_both(tmp_path: Path) -> None:
    model = _model(fixture_tree(tmp_path, second_pptx=True))
    assert model["refused"] == "MoreThanOneCurrentExport"
    assert model["files"] == [
        "presentations/fx-alpha/src/pptx/fx-alpha-deck-2026-01-01.pptx",
        "presentations/fx-alpha/src/pptx/fx-alpha-deck-2026-02-01.pptx",
    ]
    assert (
        "fx-alpha-deck-2026-01-01.pptx, presentations/fx-alpha/src/pptx/fx-alpha-deck-2026-02-01.pptx"
        in (model["message"])
    )


_TWINS = """
const infographics = m.collectInfographics(inp.site, inp.root);
const twins = [
  ...infographics.map((i) => [i.source, i.twin]),
  ...m.collectFamilies(infographics, inp.root).flatMap((f) => f.views.map((v) => [v.source, v.twin])),
];
return twins.map(([source, twin]) => [source, twin, m.publishedTwin(inp.root, source, twin)]);
"""


def test_every_tracked_twin_changes_only_its_font_links() -> None:
    """The vendoring-only oracle over every real twin (the 43.7 review, F3): ``publishedTwin`` -- what
    ``populate-public`` writes each twin with -- read against the tracked bytes by a line diff that knows nothing of
    the code: the only lines lost name a Google Fonts origin, the only line gained is the one vendored font link."""
    twins = ts(HERALD_PAGES_TS, _TWINS, site=site_yml(REPO_ROOT), root=str(REPO_ROOT))
    assert isinstance(twins, list) and len(twins) == 30, twins  # ten infographics, two views of each of ten families
    for source, twin, published in twins:
        raw = published.encode("utf-8")
        assert font_vendoring_only(raw, (REPO_ROOT / source).read_bytes()) == [], source
        assert b"fonts.googleapis.com" not in raw and b"fonts.gstatic.com" not in raw, source
        assert f'<link rel="stylesheet" href="{"../" * twin.count("/")}fonts.css">'.encode() in raw, source
