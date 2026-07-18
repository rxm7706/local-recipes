"""Story H2 `kedro-test` gate — the three agno crews on a FIXTURE wiki (FR-22(b), AD-13/AD-22).

Proves each crew runs end-to-end offline: compile (raw → compiled), lint (violations reported),
Q&A (answer grounded in compiled content) — and, load-bearing, that CompileCrew propagates a
source staleness marker forward so republication never launders freshness."""

import json
from pathlib import Path

from pyforge.atlas.factory.crews import (
    STALE_BANNER_PREFIX,
    STALENESS_SUFFIX,
    CompileCrew,
    Grounding,
    LintCrew,
    QACrew,
    keyword_retriever,
    parse_frontmatter,
    serialize_frontmatter,
)
from pyforge.atlas.factory.wiki import scaffold_wiki


def _fixture_wiki(tmp_path: Path):
    layout = scaffold_wiki(tmp_path / "wiki")
    raw = layout.stage_dir("raw")
    (raw / "duckdb.md").write_text(
        "---\ntitle: DuckDB\n---\nDuckDB is the single compute engine for atlas.\n",
        encoding="utf-8",
    )
    (raw / "kedro.md").write_text(
        "# Kedro\nKedro resolves the pipeline DAG for the migration.\n", encoding="utf-8"
    )
    return layout


# --- frontmatter round-trip ------------------------------------------------------------


def test_frontmatter_round_trip_is_stable():
    meta = {"title": "X", "source": "raw/x.md", "stale": True}
    doc = serialize_frontmatter(meta, "body text\n")
    got_meta, got_body = parse_frontmatter(doc)
    assert got_meta == meta
    assert got_body == "body text\n"
    # byte-stable across two serializations (AD-21).
    assert serialize_frontmatter(meta, "body text\n") == doc


def test_parse_frontmatter_no_block_returns_whole_body():
    meta, body = parse_frontmatter("just a body\n")
    assert meta == {}
    assert body == "just a body\n"


# --- compile crew ----------------------------------------------------------------------


def test_compile_transforms_raw_to_compiled(tmp_path: Path):
    layout = _fixture_wiki(tmp_path)
    result = CompileCrew().run(layout)
    assert result.count == 2
    assert result.compiled == ["duckdb.md", "kedro.md"]
    for name in ("duckdb.md", "kedro.md"):
        out = layout.stage_path("compiled", name).read_text(encoding="utf-8")
        meta, _body = parse_frontmatter(out)
        assert meta["source"] == f"raw/{name}"
        assert meta["title"]  # title derived from frontmatter or the '# ' heading


def test_compile_derives_title_from_heading_when_no_frontmatter(tmp_path: Path):
    layout = _fixture_wiki(tmp_path)
    CompileCrew().run(layout)
    meta, _ = parse_frontmatter(
        layout.stage_path("compiled", "kedro.md").read_text(encoding="utf-8")
    )
    assert meta["title"] == "Kedro"


def test_compile_is_deterministic(tmp_path: Path):
    layout = _fixture_wiki(tmp_path)
    CompileCrew().run(layout)
    first = layout.stage_path("compiled", "duckdb.md").read_text(encoding="utf-8")
    CompileCrew().run(layout)  # recompile
    assert layout.stage_path("compiled", "duckdb.md").read_text(encoding="utf-8") == first


def test_compile_runs_the_injected_enricher(tmp_path: Path):
    layout = _fixture_wiki(tmp_path)
    CompileCrew(enricher=lambda title, body: body + f"\n<!-- enriched:{title} -->").run(layout)
    out = layout.stage_path("compiled", "duckdb.md").read_text(encoding="utf-8")
    assert "<!-- enriched:DuckDB -->" in out


# --- staleness propagation (AD-13/AD-22 — the load-bearing H2 invariant) ---------------


def test_compile_forwards_source_staleness(tmp_path: Path):
    layout = _fixture_wiki(tmp_path)
    raw_doc = layout.stage_dir("raw") / "duckdb.md"
    sidecar = raw_doc.with_name(raw_doc.name + STALENESS_SUFFIX)
    sidecar.write_text(
        json.dumps({"stale": True, "reason": "refresh skipped", "marked_at": 1000}),
        encoding="utf-8",
    )
    result = CompileCrew().run(layout)
    assert "duckdb.md" in result.stale_forwarded
    out = layout.stage_path("compiled", "duckdb.md").read_text(encoding="utf-8")
    meta, body = parse_frontmatter(out)
    # machine-readable marker forwarded...
    assert meta["stale"] is True
    assert meta["stale_reason"] == "refresh skipped"
    assert meta["stale_marked_at"] == 1000
    # ...AND the human-visible banner stamped (republication never launders freshness).
    assert body.startswith(STALE_BANNER_PREFIX)
    # a FRESH source stays fresh.
    assert "kedro.md" not in result.stale_forwarded
    kmeta, _ = parse_frontmatter(
        layout.stage_path("compiled", "kedro.md").read_text(encoding="utf-8")
    )
    assert "stale" not in kmeta


def test_unreadable_staleness_sidecar_degrades_to_stale(tmp_path: Path):
    layout = _fixture_wiki(tmp_path)
    raw_doc = layout.stage_dir("raw") / "duckdb.md"
    raw_doc.with_name(raw_doc.name + STALENESS_SUFFIX).write_text("{not json", encoding="utf-8")
    result = CompileCrew().run(layout)
    # AD-13: degrade toward stale, never silently toward fresh.
    assert "duckdb.md" in result.stale_forwarded
    meta, _ = parse_frontmatter(
        layout.stage_path("compiled", "duckdb.md").read_text(encoding="utf-8")
    )
    assert meta["stale"] is True


def test_non_stale_sidecar_does_not_mark_stale(tmp_path: Path):
    layout = _fixture_wiki(tmp_path)
    raw_doc = layout.stage_dir("raw") / "duckdb.md"
    raw_doc.with_name(raw_doc.name + STALENESS_SUFFIX).write_text(
        json.dumps({"stale": False, "reason": "fresh"}), encoding="utf-8"
    )
    result = CompileCrew().run(layout)
    assert "duckdb.md" not in result.stale_forwarded


def test_compile_forwards_inline_frontmatter_staleness(tmp_path: Path):
    # MUST-FIX (review): a raw doc that declares itself stale in its OWN frontmatter (no sidecar)
    # must be forwarded as stale — never laundered to fresh by the frontmatter rebuild.
    layout = scaffold_wiki(tmp_path / "wiki")
    layout.stage_path("raw", "x.md").write_text(
        "---\ntitle: X\nstale: true\nstale_reason: refresh skipped upstream\n"
        "stale_marked_at: 42\n---\nbody\n",
        encoding="utf-8",
    )
    result = CompileCrew().run(layout)
    assert "x.md" in result.stale_forwarded
    meta, body = parse_frontmatter(layout.stage_path("compiled", "x.md").read_text("utf-8"))
    assert meta["stale"] is True
    assert meta["stale_reason"] == "refresh skipped upstream"
    assert meta["stale_marked_at"] == 42
    assert body.startswith(STALE_BANNER_PREFIX)
    # and the compiled page is NOT lint-laundered (banner present -> no violation).
    assert not LintCrew().run(layout).by_rule("laundered-staleness")


def test_compile_skips_malformed_raw_without_partial_abort(tmp_path: Path):
    # One malformed raw doc must not abort the loop or leave the good docs uncompiled.
    layout = _fixture_wiki(tmp_path)
    layout.stage_path("raw", "broken.md").write_text(
        "---\n: : not: valid: yaml\n---\nbody\n", encoding="utf-8"
    )
    result = CompileCrew().run(layout)
    # the two good fixture docs still compiled...
    assert set(result.compiled) == {"duckdb.md", "kedro.md"}
    # ...and the malformed one is recorded, not silently swallowed.
    assert any(name == "broken.md" for name, _reason in result.failed)


# --- lint crew -------------------------------------------------------------------------


def test_lint_clean_wiki_has_no_violations(tmp_path: Path):
    layout = _fixture_wiki(tmp_path)
    CompileCrew().run(layout)
    report = LintCrew().run(layout)
    assert report.ok, [v for v in report.violations]


def test_lint_reports_missing_frontmatter_and_empty_body(tmp_path: Path):
    layout = scaffold_wiki(tmp_path / "wiki")
    layout.stage_path("compiled", "bare.md").write_text("no frontmatter here\n", encoding="utf-8")
    layout.stage_path("compiled", "empty.md").write_text(
        "---\ntitle: Empty\n---\n", encoding="utf-8"
    )
    report = LintCrew().run(layout)
    assert report.by_rule("missing-frontmatter")
    assert report.by_rule("empty-body")


def test_lint_reports_broken_internal_link(tmp_path: Path):
    layout = scaffold_wiki(tmp_path / "wiki")
    layout.stage_path("compiled", "a.md").write_text(
        "---\ntitle: A\n---\nSee [B](missing.md) and [ext](https://x/y.md).\n", encoding="utf-8"
    )
    report = LintCrew().run(layout)
    broken = report.by_rule("broken-link")
    assert len(broken) == 1  # the external URL is skipped, only missing.md flagged
    assert "missing.md" in broken[0].detail


def test_lint_reports_malformed_page_without_crashing(tmp_path: Path):
    # MUST-FIX (review): a malformed compiled page must be REPORTED, not crash the pass and hide
    # other violations (lint is the AD-13 laundering safety net — it can't DoS on a bad page).
    layout = scaffold_wiki(tmp_path / "wiki")
    layout.stage_path("compiled", "bad.md").write_text(
        "---\n: : broken: yaml:\n---\nbody\n", encoding="utf-8"
    )
    layout.stage_path("compiled", "good.md").write_text(
        "---\ntitle: Good\n---\nSee [B](missing.md).\n", encoding="utf-8"
    )
    report = LintCrew().run(layout)  # must not raise
    assert report.by_rule("malformed-frontmatter")
    # the OTHER page's broken link is still surfaced (no DoS).
    assert report.by_rule("broken-link")


def test_lint_broken_link_resolves_subdir_paths(tmp_path: Path):
    # SHOULD-FIX (review): leaf-only matching false-negated a wrong-subdir link. A link to
    # guides/duckdb.md must be flagged even when a TOP-LEVEL duckdb.md exists.
    layout = scaffold_wiki(tmp_path / "wiki")
    layout.stage_path("compiled", "duckdb.md").write_text(
        "---\ntitle: DuckDB\n---\ntop level\n", encoding="utf-8"
    )
    layout.stage_path("compiled", "index.md").write_text(
        "---\ntitle: Index\n---\nSee [d](guides/duckdb.md).\n", encoding="utf-8"
    )
    report = LintCrew().run(layout)
    broken = report.by_rule("broken-link")
    assert len(broken) == 1 and "guides/duckdb.md" in broken[0].detail


def test_lint_broken_link_accepts_real_subdir_target(tmp_path: Path):
    # reciprocal: a link to a page that really exists in a subdir must NOT be flagged.
    layout = scaffold_wiki(tmp_path / "wiki")
    (layout.stage_dir("compiled") / "guides").mkdir()
    layout.stage_path("compiled", "guides/real.md").write_text(
        "---\ntitle: Real\n---\nreal page\n", encoding="utf-8"
    )
    layout.stage_path("compiled", "index.md").write_text(
        "---\ntitle: Index\n---\nSee [r](guides/real.md).\n", encoding="utf-8"
    )
    assert not LintCrew().run(layout).by_rule("broken-link")


def test_lint_catches_laundered_staleness(tmp_path: Path):
    # A page whose frontmatter says stale but whose body dropped the banner = laundered freshness.
    layout = scaffold_wiki(tmp_path / "wiki")
    layout.stage_path("compiled", "laundered.md").write_text(
        "---\nstale: true\ntitle: Laundered\n---\nlooks fresh but is not\n", encoding="utf-8"
    )
    report = LintCrew().run(layout)
    assert report.by_rule("laundered-staleness")


def test_lint_accepts_properly_bannered_stale_page(tmp_path: Path):
    layout = _fixture_wiki(tmp_path)
    raw_doc = layout.stage_dir("raw") / "duckdb.md"
    raw_doc.with_name(raw_doc.name + STALENESS_SUFFIX).write_text(
        json.dumps({"stale": True, "reason": "skipped"}), encoding="utf-8"
    )
    CompileCrew().run(layout)  # compiler stamps the banner
    report = LintCrew().run(layout)
    assert not report.by_rule("laundered-staleness")


# --- Q&A crew --------------------------------------------------------------------------


def test_qa_answers_grounded_in_compiled_content(tmp_path: Path):
    layout = _fixture_wiki(tmp_path)
    CompileCrew().run(layout)
    ans = QACrew().run(layout, "what is the compute engine?")
    assert ans.grounded
    assert ans.grounding[0].doc == "duckdb.md"  # the doc mentioning 'compute engine'
    assert "duckdb.md" in ans.answer or "DuckDB" in ans.answer


def test_qa_ungrounded_question_yields_no_grounding(tmp_path: Path):
    layout = _fixture_wiki(tmp_path)
    CompileCrew().run(layout)
    ans = QACrew().run(layout, "zzzznonexistentterm")
    assert not ans.grounded
    assert ans.grounding == []


def test_qa_skips_malformed_page_and_still_answers(tmp_path: Path):
    # MUST-FIX (review): a malformed compiled page must not crash the answer — QA grounds on the
    # good pages and skips the unparseable one.
    layout = _fixture_wiki(tmp_path)
    CompileCrew().run(layout)
    layout.stage_path("compiled", "broken.md").write_text(
        "---\n: : broken:\n---\nx\n", encoding="utf-8"
    )
    ans = QACrew().run(layout, "what is the compute engine?")  # must not raise
    assert ans.grounded
    assert ans.grounding[0].doc == "duckdb.md"


def test_qa_uses_injected_retriever_and_synthesizer(tmp_path: Path):
    layout = _fixture_wiki(tmp_path)
    CompileCrew().run(layout)
    sentinel = [Grounding(doc="kedro.md", snippet="injected", score=9.0)]
    ans = QACrew(
        retriever=lambda q, docs: sentinel,
        synthesizer=lambda q, g: f"SYNTH[{g[0].doc}]",
    ).run(layout, "anything")
    assert ans.grounding == sentinel
    assert ans.answer == "SYNTH[kedro.md]"


def test_keyword_retriever_ranks_by_overlap_deterministically():
    docs = [
        ("a.md", "duckdb engine"),  # 2 of the 3 query terms
        ("b.md", "kedro pipeline"),  # none
        ("c.md", "duckdb engine vector similarity"),  # all 3 query terms
    ]
    got = keyword_retriever("duckdb vector engine", docs)
    assert [g.doc for g in got] == ["c.md", "a.md"]  # c has more overlap; b (zero) is dropped
    assert got[0].score == 3.0 and got[1].score == 2.0
