"""``deck_qa`` -- the gate report schema and ``run()`` entrypoint (Story
14.1), plus the headless-render gate (Story 14.2). Covers every row of the
14.1 and 14.2 specs' I/O & Edge-Case Matrices.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from pyforge.herald import deck_qa
from pyforge.herald.errors import HeraldError


def _ok(context: deck_qa.GateContext) -> deck_qa.GateResult:
    return deck_qa.GateResult(status="ok")


def _with_finding(context: deck_qa.GateContext) -> deck_qa.GateResult:
    return deck_qa.GateResult(
        status="ok",
        findings=[deck_qa.Finding(slide_id="slide-1", message="off-slide text")],
    )


def _raises(context: deck_qa.GateContext) -> deck_qa.GateResult:
    raise RuntimeError("boom: gate exploded")


def test_zero_gates_prints_an_empty_gates_object(tmp_path: Path):
    report = deck_qa.run("x", tmp_path, gates={})
    assert report == deck_qa.DeckQaReport(slug="x", gates={})
    assert deck_qa.to_dict(report) == {"slug": "x", "gates": {}}


def test_two_gates_one_flags_both_keys_present(tmp_path: Path):
    report = deck_qa.run(
        "pyforge-warden", tmp_path, gates={"a": _ok, "b": _with_finding}
    )
    assert set(report.gates) == {"a", "b"}
    assert report.gates["a"].status == "ok"
    assert report.gates["a"].findings == []
    assert report.gates["b"].status == "ok"
    assert report.gates["b"].findings == [
        deck_qa.Finding(slide_id="slide-1", message="off-slide text")
    ]


def test_a_gate_that_raises_becomes_status_error_without_aborting_others(
    tmp_path: Path,
):
    report = deck_qa.run("x", tmp_path, gates={"boom": _raises, "fine": _ok})
    assert report.gates["boom"].status == "error"
    assert report.gates["boom"].error is not None
    assert "boom: gate exploded" in report.gates["boom"].error
    assert report.gates["boom"].findings == []
    assert report.gates["fine"].status == "ok"


def test_run_itself_never_raises_when_a_gate_raises(tmp_path: Path):
    # No pytest.raises wrapper -- the assertion IS that this call returns.
    report = deck_qa.run("x", tmp_path, gates={"boom": _raises})
    assert report.gates["boom"].status == "error"


def test_gate_context_carries_slug_and_repo_root(tmp_path: Path):
    seen = {}

    def _capture(context: deck_qa.GateContext) -> deck_qa.GateResult:
        seen["slug"] = context.slug
        seen["repo_root"] = context.repo_root
        return deck_qa.GateResult(status="ok")

    deck_qa.run("pyforge-warden", tmp_path, gates={"capture": _capture})

    assert seen["slug"] == "pyforge-warden"
    assert seen["repo_root"] == tmp_path


def test_round_trip_equality(tmp_path: Path):
    report = deck_qa.run(
        "pyforge-warden", tmp_path, gates={"a": _ok, "b": _with_finding, "c": _raises}
    )
    round_tripped = deck_qa.parse_report(json.loads(json.dumps(deck_qa.to_dict(report))))
    assert round_tripped == report


def test_round_trip_of_the_empty_report(tmp_path: Path):
    report = deck_qa.run("x", tmp_path, gates={})
    round_tripped = deck_qa.parse_report(json.loads(json.dumps(deck_qa.to_dict(report))))
    assert round_tripped == report


def test_parse_report_rejects_missing_gates_key():
    with pytest.raises(HeraldError, match="gates"):
        deck_qa.parse_report({"slug": "x"})


def test_parse_report_rejects_missing_slug_key():
    with pytest.raises(HeraldError, match="slug"):
        deck_qa.parse_report({"gates": {}})


def test_parse_report_rejects_an_unknown_top_level_key():
    with pytest.raises(HeraldError, match="bogus"):
        deck_qa.parse_report({"slug": "x", "gates": {}, "bogus": 1})


def test_parse_report_rejects_an_unknown_gate_level_key():
    with pytest.raises(HeraldError, match="bogus"):
        deck_qa.parse_report(
            {
                "slug": "x",
                "gates": {
                    "a": {
                        "status": "ok",
                        "findings": [],
                        "artifacts": [],
                        "error": None,
                        "bogus": 1,
                    }
                },
            }
        )


def test_parse_report_rejects_an_unknown_finding_level_key():
    with pytest.raises(HeraldError):
        deck_qa.parse_report(
            {
                "slug": "x",
                "gates": {
                    "a": {
                        "status": "ok",
                        "findings": [
                            {"slide_id": "s1", "message": "m", "bogus": 1}
                        ],
                        "artifacts": [],
                        "error": None,
                    }
                },
            }
        )


def test_parse_report_rejects_a_bad_status_value():
    with pytest.raises(HeraldError, match="status"):
        deck_qa.parse_report(
            {
                "slug": "x",
                "gates": {
                    "a": {
                        "status": "not-a-real-status",
                        "findings": [],
                        "artifacts": [],
                        "error": None,
                    }
                },
            }
        )


def test_parse_report_rejects_a_non_dict_top_level():
    with pytest.raises(HeraldError):
        deck_qa.parse_report(["not", "a", "dict"])


def test_parse_report_rejects_a_missing_gate_level_field():
    with pytest.raises(HeraldError, match="findings"):
        deck_qa.parse_report(
            {
                "slug": "x",
                "gates": {"a": {"status": "ok", "artifacts": [], "error": None}},
            }
        )


def test_parse_report_rejects_ok_status_with_a_non_null_error():
    with pytest.raises(HeraldError, match="status"):
        deck_qa.parse_report(
            {
                "slug": "x",
                "gates": {
                    "a": {
                        "status": "ok",
                        "findings": [],
                        "artifacts": [],
                        "error": "unexpected",
                    }
                },
            }
        )


def test_parse_report_rejects_error_status_with_a_null_error():
    with pytest.raises(HeraldError, match="status"):
        deck_qa.parse_report(
            {
                "slug": "x",
                "gates": {
                    "a": {
                        "status": "error",
                        "findings": [],
                        "artifacts": [],
                        "error": None,
                    }
                },
            }
        )


def test_a_gate_returning_none_becomes_status_error(tmp_path: Path):
    def _forgot_return(context: deck_qa.GateContext) -> deck_qa.GateResult:
        pass  # a gate forgetting its `return` -- yields None, no exception

    report = deck_qa.run("x", tmp_path, gates={"broken": _forgot_return})
    assert report.gates["broken"].status == "error"
    assert report.gates["broken"].error is not None


def test_a_gate_returning_a_bad_status_value_becomes_status_error(tmp_path: Path):
    def _bad_status(context: deck_qa.GateContext) -> deck_qa.GateResult:
        return deck_qa.GateResult(status="not-a-real-status")

    report = deck_qa.run("x", tmp_path, gates={"broken": _bad_status})
    assert report.gates["broken"].status == "error"
    assert report.gates["broken"].error is not None


def test_a_gate_violating_the_status_error_invariant_becomes_status_error(
    tmp_path: Path,
):
    def _inconsistent(context: deck_qa.GateContext) -> deck_qa.GateResult:
        # status "ok" but a non-null error -- self-contradictory.
        return deck_qa.GateResult(status="ok", error="oops")

    report = deck_qa.run("x", tmp_path, gates={"broken": _inconsistent})
    assert report.gates["broken"].status == "error"


def test_run_reads_default_gates_fresh_even_after_reassignment(
    tmp_path: Path, monkeypatch
):
    """The mutable-default-argument footgun this fix avoids: reassigning
    the module attribute (not mutating it in place) must still be picked
    up by a caller that never passes ``gates=`` explicitly."""
    monkeypatch.setattr(deck_qa, "DEFAULT_GATES", {"late": _ok})

    report = deck_qa.run("x", tmp_path)

    assert set(report.gates) == {"late"}


def test_third_gate_added_to_the_same_gates_mapping_needs_zero_production_changes(
    tmp_path: Path,
):
    """Proof, not a production-code change: build a 3-entry ``gates`` dict
    right here in the test and confirm the report gains a third top-level
    key with nothing else touched."""

    def _third(context: deck_qa.GateContext) -> deck_qa.GateResult:
        return deck_qa.GateResult(status="ok")

    gates = {"a": _ok, "b": _with_finding, "third": _third}

    report = deck_qa.run("x", tmp_path, gates=gates)

    assert set(report.gates) == {"a", "b", "third"}
    assert report.gates["third"].status == "ok"


# === render_gate (Story 14.2) ================================================

_SYNTHETIC_DIST_HTML = """<!doctype html>
<html>
<head><meta charset="utf-8"><title>test deck</title></head>
<body>
<div id="app"></div>
<script>
function render() {
  var hash = window.location.hash || "#/1";
  document.getElementById("app").textContent = "slide " + hash;
  document.title = "slide " + hash;
}
window.addEventListener("hashchange", render);
render();
</script>
</body>
</html>
"""


def _write_synthetic_deck(
    repo_root: Path,
    slug: str,
    manifest: list[dict],
    *,
    with_dist: bool = True,
    with_manifest: bool = True,
) -> None:
    """A minimal ``presentations/<slug>/{src/slides/manifest.json,dist/}``
    tree -- static HTML that reads ``location.hash``, no Node/npm/Vite
    build involved (per this story's spec: Code Map)."""
    deck_dir = repo_root / "presentations" / slug
    if with_manifest:
        slides_dir = deck_dir / "src" / "slides"
        slides_dir.mkdir(parents=True, exist_ok=True)
        (slides_dir / "manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )
    if with_dist:
        dist_dir = deck_dir / "dist"
        dist_dir.mkdir(parents=True, exist_ok=True)
        (dist_dir / "index.html").write_text(_SYNTHETIC_DIST_HTML, encoding="utf-8")


def test_render_gate_happy_path_one_png_per_slide_plus_contact_sheet(tmp_path: Path):
    manifest = [{"id": "cover"}, {"id": "problem"}, {"id": "close"}]
    _write_synthetic_deck(tmp_path, "demo-deck", manifest)
    context = deck_qa.GateContext(slug="demo-deck", repo_root=tmp_path)

    result = deck_qa.render_gate(context)

    assert result.status == "ok"
    assert result.findings == []
    assert len(result.artifacts) == 4  # 3 PNGs + 1 contact sheet
    assert all(isinstance(a, str) for a in result.artifacts)  # never a Path
    render_dir = tmp_path / ".herald" / "deck-qa" / "demo-deck" / "render"
    for slide_id in ("cover", "problem", "close"):
        png = render_dir / f"{slide_id}.png"
        assert png.is_file()
        assert str(png) in result.artifacts
    contact_sheet = render_dir / "contact-sheet.png"
    assert contact_sheet.is_file()
    assert str(contact_sheet) in result.artifacts
    # every artifact path round-trips through JSON exactly like the schema
    # promises (this story's spec: Boundaries & Constraints).
    json.dumps(deck_qa.to_dict(deck_qa.DeckQaReport(slug="x", gates={"render": result})))


def test_render_gate_recreates_the_render_dir_fresh_each_run(tmp_path: Path):
    """A stale PNG from a since-shrunk manifest must never linger looking
    current (this story's spec: Design Notes)."""
    manifest = [{"id": "cover"}]
    _write_synthetic_deck(tmp_path, "demo-deck", manifest)
    context = deck_qa.GateContext(slug="demo-deck", repo_root=tmp_path)
    render_dir = tmp_path / ".herald" / "deck-qa" / "demo-deck" / "render"
    render_dir.mkdir(parents=True)
    stale = render_dir / "stale-leftover.png"
    stale.write_bytes(b"not a real png")

    result = deck_qa.render_gate(context)

    assert result.status == "ok"
    assert not stale.exists()
    assert (render_dir / "cover.png").is_file()


class _FakePage:
    """A fake playwright ``Page``: ``goto`` is a no-op; ``screenshot`` raises
    for any slide id in ``fail_slide_ids``, else writes a real (tiny, valid)
    PNG so ``_build_contact_sheet`` -- which opens every captured PNG with
    Pillow -- has something real to composite."""

    def __init__(self, fail_slide_ids: set[str]) -> None:
        self._fail_slide_ids = fail_slide_ids

    def goto(self, url, wait_until=None, timeout=None):  # noqa: D102
        pass

    def screenshot(self, path=None, timeout=None):  # noqa: D102
        slide_id = Path(path).stem
        if slide_id in self._fail_slide_ids:
            raise RuntimeError(f"synthetic capture failure for {slide_id!r}")
        from PIL import Image

        Image.new("RGB", (4, 4), "white").save(path)

    def close(self):  # noqa: D102
        pass


class _FakeBrowser:
    def __init__(self, fail_slide_ids: set[str]) -> None:
        self._fail_slide_ids = fail_slide_ids

    def new_page(self, viewport=None):  # noqa: D102
        return _FakePage(self._fail_slide_ids)

    def close(self):  # noqa: D102
        pass


class _FakeChromium:
    def __init__(self, fail_slide_ids: set[str]) -> None:
        self._fail_slide_ids = fail_slide_ids

    def launch(self, **kwargs):  # noqa: D102
        return _FakeBrowser(self._fail_slide_ids)


class _FakeBrowserType:
    def __init__(self, fail_slide_ids: set[str]) -> None:
        self.chromium = _FakeChromium(fail_slide_ids)


class _FakePlaywrightCtx:
    def __init__(self, fail_slide_ids: set[str]) -> None:
        self._fail_slide_ids = fail_slide_ids

    def __enter__(self):
        return _FakeBrowserType(self._fail_slide_ids)

    def __exit__(self, *exc_info):
        return False


def _patch_fake_playwright(monkeypatch, fail_slide_ids: set[str]) -> None:
    """Replace ``playwright.sync_api.sync_playwright`` with a fully
    controlled fake browser/page for exactly one test's duration.

    Used only for the per-slide ISOLATION-LOGIC tests below (one/all slides
    fail): those exercise ``render_gate``'s own try/except loop, not
    playwright's real capture behavior -- the happy-path tests above already
    prove that end-to-end against a real headless Chromium. A fake makes
    "exactly this slide's capture raises" deterministic and fast rather than
    depending on an OS/browser-version-specific way to make a real
    screenshot fail."""
    monkeypatch.setattr(
        "playwright.sync_api.sync_playwright",
        lambda: _FakePlaywrightCtx(fail_slide_ids),
    )


def test_render_gate_one_slide_fails_others_still_capture(tmp_path: Path, monkeypatch):
    manifest = [{"id": "cover"}, {"id": "problem"}, {"id": "close"}]
    _write_synthetic_deck(tmp_path, "demo-deck", manifest)
    context = deck_qa.GateContext(slug="demo-deck", repo_root=tmp_path)
    _patch_fake_playwright(monkeypatch, {"problem"})

    result = deck_qa.render_gate(context)

    assert result.status == "ok"
    assert len(result.findings) == 1
    assert result.findings[0].slide_id == "problem"
    render_dir = tmp_path / ".herald" / "deck-qa" / "demo-deck" / "render"
    assert (render_dir / "cover.png").is_file()
    assert (render_dir / "close.png").is_file()
    assert not (render_dir / "problem.png").exists()
    # the two good slides' PNGs plus the contact sheet -- the failed slide
    # contributes no PNG of its own.
    assert len(result.artifacts) == 3


def test_render_gate_all_slides_fail_status_stays_ok_no_contact_sheet(
    tmp_path: Path, monkeypatch
):
    manifest = [{"id": "one"}, {"id": "two"}]
    _write_synthetic_deck(tmp_path, "demo-deck", manifest)
    context = deck_qa.GateContext(slug="demo-deck", repo_root=tmp_path)
    _patch_fake_playwright(monkeypatch, {"one", "two"})

    result = deck_qa.render_gate(context)

    assert result.status == "ok"
    assert result.artifacts == []
    assert len(result.findings) == 2
    assert {f.slide_id for f in result.findings} == {"one", "two"}


def test_render_gate_missing_dist_raises_and_run_isolates_it(tmp_path: Path):
    _write_synthetic_deck(
        tmp_path, "no-dist-deck", [{"id": "cover"}], with_dist=False
    )
    context = deck_qa.GateContext(slug="no-dist-deck", repo_root=tmp_path)

    with pytest.raises(Exception, match="does not exist"):
        deck_qa.render_gate(context)

    report = deck_qa.run(
        "no-dist-deck", tmp_path, gates={"render": deck_qa.render_gate}
    )
    assert report.gates["render"].status == "error"
    assert report.gates["render"].error is not None
    # zero effect on any other gate id (Story 14.1's own isolation contract).
    report2 = deck_qa.run(
        "no-dist-deck",
        tmp_path,
        gates={"render": deck_qa.render_gate, "fine": _ok},
    )
    assert report2.gates["fine"].status == "ok"


def test_render_gate_missing_manifest_raises(tmp_path: Path):
    _write_synthetic_deck(
        tmp_path, "no-manifest-deck", [], with_manifest=False, with_dist=True
    )
    context = deck_qa.GateContext(slug="no-manifest-deck", repo_root=tmp_path)

    with pytest.raises(Exception, match="does not exist"):
        deck_qa.render_gate(context)


def test_render_gate_no_usable_chromium_raises(tmp_path: Path, monkeypatch):
    manifest = [{"id": "cover"}]
    _write_synthetic_deck(tmp_path, "demo-deck", manifest)
    context = deck_qa.GateContext(slug="demo-deck", repo_root=tmp_path)

    class _FakeChromium:
        def launch(self, **kwargs):
            raise RuntimeError("no browser binary here")

    class _FakeBrowserType:
        chromium = _FakeChromium()

    class _FakePlaywrightCtx:
        def __enter__(self):
            return _FakeBrowserType()

        def __exit__(self, *exc_info):
            return False

    monkeypatch.setattr(
        "playwright.sync_api.sync_playwright", lambda: _FakePlaywrightCtx()
    )

    with pytest.raises(Exception, match="no usable chromium"):
        deck_qa.render_gate(context)


def test_render_gate_malformed_manifest_json_raises(tmp_path: Path):
    _write_synthetic_deck(tmp_path, "bad-json-deck", [{"id": "cover"}])
    manifest_path = (
        tmp_path / "presentations" / "bad-json-deck" / "src" / "slides" / "manifest.json"
    )
    manifest_path.write_text("{not valid json", encoding="utf-8")
    context = deck_qa.GateContext(slug="bad-json-deck", repo_root=tmp_path)

    with pytest.raises(Exception, match="cannot parse"):
        deck_qa.render_gate(context)


def test_render_gate_manifest_not_a_list_raises(tmp_path: Path):
    _write_synthetic_deck(tmp_path, "bad-shape-deck", [{"id": "cover"}])
    manifest_path = (
        tmp_path / "presentations" / "bad-shape-deck" / "src" / "slides" / "manifest.json"
    )
    manifest_path.write_text(json.dumps({"not": "a list"}), encoding="utf-8")
    context = deck_qa.GateContext(slug="bad-shape-deck", repo_root=tmp_path)

    with pytest.raises(Exception, match="must contain a JSON array"):
        deck_qa.render_gate(context)


def test_render_gate_unimportable_playwright_raises(tmp_path: Path, monkeypatch):
    manifest = [{"id": "cover"}]
    _write_synthetic_deck(tmp_path, "demo-deck", manifest)
    context = deck_qa.GateContext(slug="demo-deck", repo_root=tmp_path)
    # Simulates an installed-but-broken/absent playwright: sys.modules holding
    # `None` for a name makes Python's own import machinery raise ImportError
    # for it immediately, regardless of whether it was already cached.
    monkeypatch.setitem(sys.modules, "playwright.sync_api", None)

    with pytest.raises(Exception, match="playwright is not usable"):
        deck_qa.render_gate(context)


def test_render_gate_rejects_a_traversal_slug(tmp_path: Path):
    context = deck_qa.GateContext(slug="../escape", repo_root=tmp_path)

    with pytest.raises(Exception, match="invalid slug"):
        deck_qa.render_gate(context)


def test_render_gate_slide_id_with_path_separator_falls_back_to_positional(
    tmp_path: Path,
):
    manifest = [{"id": "../escape"}, {"id": "fine"}]
    _write_synthetic_deck(tmp_path, "demo-deck", manifest)
    context = deck_qa.GateContext(slug="demo-deck", repo_root=tmp_path)

    result = deck_qa.render_gate(context)

    assert result.status == "ok"
    render_dir = tmp_path / ".herald" / "deck-qa" / "demo-deck" / "render"
    assert (render_dir / "slide-1.png").is_file()  # positional fallback
    assert (render_dir / "fine.png").is_file()
    assert not (render_dir.parent / "escape.png").exists()  # never escaped render_dir


def test_render_gate_duplicate_ids_are_disambiguated(tmp_path: Path):
    manifest = [{"id": "same"}, {"id": "same"}, {"id": "contact-sheet"}]
    _write_synthetic_deck(tmp_path, "demo-deck", manifest)
    context = deck_qa.GateContext(slug="demo-deck", repo_root=tmp_path)

    result = deck_qa.render_gate(context)

    assert result.status == "ok"
    render_dir = tmp_path / ".herald" / "deck-qa" / "demo-deck" / "render"
    assert (render_dir / "same.png").is_file()
    assert (render_dir / "same-1.png").is_file()  # disambiguated, index 1
    assert (render_dir / "contact-sheet-2.png").is_file()  # reserved-name collision
    assert (render_dir / "contact-sheet.png").is_file()  # the real composite, untouched
    # every png accounted for, none silently overwritten
    assert len(result.artifacts) == 4  # 3 pngs + the real contact sheet


def test_render_gate_isolates_a_contact_sheet_build_failure(
    tmp_path: Path, monkeypatch
):
    manifest = [{"id": "cover"}, {"id": "close"}]
    _write_synthetic_deck(tmp_path, "demo-deck", manifest)
    context = deck_qa.GateContext(slug="demo-deck", repo_root=tmp_path)
    monkeypatch.setattr(
        deck_qa,
        "_build_contact_sheet",
        lambda png_paths, out_path: (_ for _ in ()).throw(RuntimeError("disk full")),
    )

    result = deck_qa.render_gate(context)

    assert result.status == "ok"  # not discarded by the contact-sheet failure
    assert len(result.artifacts) == 2  # both slide PNGs still reported
    assert any(f.slide_id == "contact-sheet" for f in result.findings)


def test_build_contact_sheet_skips_writing_when_no_pngs(tmp_path: Path):
    out_path = tmp_path / "contact-sheet.png"
    deck_qa._build_contact_sheet([], out_path)
    assert not out_path.exists()


def test_build_contact_sheet_composites_real_pngs(tmp_path: Path):
    from PIL import Image

    png_paths = []
    for i, color in enumerate(("red", "green", "blue")):
        p = tmp_path / f"slide-{i}.png"
        Image.new("RGB", (40, 20), color).save(p)
        png_paths.append(p)
    out_path = tmp_path / "contact-sheet.png"

    deck_qa._build_contact_sheet(png_paths, out_path)

    assert out_path.is_file()
    with Image.open(out_path) as sheet:
        assert sheet.width > 0
        assert sheet.height > 0


def test_slide_id_uses_manifest_id_when_present():
    assert deck_qa._slide_id({"id": "cover"}, 0) == "cover"


def test_slide_id_falls_back_to_position_when_id_missing_or_malformed():
    assert deck_qa._slide_id({}, 2) == "slide-3"
    assert deck_qa._slide_id("not-a-dict", 4) == "slide-5"
    assert deck_qa._slide_id({"id": ""}, 0) == "slide-1"
    assert deck_qa._slide_id({"id": 42}, 1) == "slide-2"


def test_serve_dist_dir_binds_an_ephemeral_loopback_port(tmp_path: Path):
    # Not a live HTTP request here: this suite's autouse `deny_network`
    # fixture (conftest.py) patches Python's own `socket` primitives for
    # every non-`live` test, which would deny a Python-side request to this
    # very server. The happy-path render_gate tests already prove the server
    # actually serves content -- Chromium is a separate process with its own
    # network stack, unaffected by that patch. This test only proves
    # `_serve_dist_dir` itself binds and tears down cleanly.
    httpd, port = deck_qa._serve_dist_dir(tmp_path)
    try:
        assert httpd.server_address[0] == "127.0.0.1"
        assert port > 0
        assert httpd.server_address[1] == port
    finally:
        deck_qa._suppress_close(httpd.shutdown)
        deck_qa._suppress_close(httpd.server_close)
