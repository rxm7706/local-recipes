"""Unit tests for ``pyforge.herald.twins`` (CAP-55 D5)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pyforge.core.errors import PyforgeError

from pyforge.herald import twins


def test_scan_allows_navigation_link_only(tmp_path: Path):
    html = tmp_path / "page.html"
    html.write_text(
        '<html><body><a href="https://github.com/org/repo">repo</a></body></html>',
        encoding="utf-8",
    )
    assert twins.scan_file(html) == []


def test_scan_finds_font_stylesheet_link(tmp_path: Path):
    html = tmp_path / "page.html"
    html.write_text(
        '<link href="https://fonts.googleapis.com/css?family=Archivo" rel="stylesheet">',
        encoding="utf-8",
    )
    findings = twins.scan_file(html)
    assert len(findings) == 1
    assert findings[0].origin == "fonts.googleapis.com"


def test_scan_finds_css_import(tmp_path: Path):
    html = tmp_path / "page.html"
    html.write_text(
        "<style>@import url('https://fonts.googleapis.com/css2?family=Archivo');</style>",
        encoding="utf-8",
    )
    findings = twins.scan_file(html)
    assert findings[0].origin == "fonts.googleapis.com"


def test_vendor_standalone_strips_twemoji_and_google(tmp_path: Path):
    html = tmp_path / "standalone.html"
    html.write_text(
        "<style>@import url('https://fonts.googleapis.com/css2?family=Archivo');</style>"
        '<img class="emoji" alt="↔" src="https://cdn.jsdelivr.net/gh/x/twemoji.svg"/>',
        encoding="utf-8",
    )
    twins.vendor_standalone_html(html)
    text = html.read_text(encoding="utf-8")
    assert "fonts.googleapis.com" not in text
    assert "jsdelivr.net" not in text
    assert "↔" in text


def test_scan_tree_over_dist_bundle(tmp_path: Path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text(
        '<html><head><link rel="stylesheet" href="./assets/app.css"></head><body></body></html>',
        encoding="utf-8",
    )
    assets = dist / "assets"
    assets.mkdir()
    (assets / "app.css").write_text("body { font-family: sans-serif; }", encoding="utf-8")
    assert twins.scan_tree(dist) == []


def test_twin_origin_error_message(tmp_path: Path):
    finding = twins.OriginFinding(
        path=tmp_path / "bad.html",
        origin="fonts.googleapis.com",
        reference="https://fonts.googleapis.com/css",
    )
    err = twins.TwinOriginError(finding)
    assert issubclass(twins.TwinOriginError, PyforgeError)
    assert "fonts.googleapis.com" in str(err)
    assert "bad.html" in str(err)


def test_scan_text_ignores_relative_and_duplicate_urls(tmp_path: Path):
    path = tmp_path / "page.html"
    html = (
        '<img src="/local.png">'
        '<img src="https://cdn.example.com/a.png">'
        '<img src="https://cdn.example.com/a.png">'
    )
    findings = twins.scan_text(html, path)
    assert len(findings) == 1
    assert findings[0].origin == "cdn.example.com"


def test_scan_tree_on_single_html_file(tmp_path: Path):
    single = tmp_path / "only.html"
    single.write_text("<html></html>", encoding="utf-8")
    assert twins.scan_tree(single) == []


def test_scan_tree_skips_non_web_suffixes(tmp_path: Path):
    (tmp_path / "note.txt").write_text("https://evil.example.com/x", encoding="utf-8")
    (tmp_path / "ok.html").write_text("<html></html>", encoding="utf-8")
    assert twins.scan_tree(tmp_path) == []


def test_vendor_standalone_twemoji_without_alt(tmp_path: Path):
    html = tmp_path / "standalone.html"
    html.write_text('<img class="emoji" src="https://cdn.jsdelivr.net/x.svg"/>', encoding="utf-8")
    twins.vendor_standalone_html(html)
    assert "jsdelivr.net" not in html.read_text(encoding="utf-8")


def test_current_standalone_twin_from_marp_glob(tmp_path: Path):
    slug = "demo-deck"
    marp = tmp_path / "presentations" / slug / "src" / "marp"
    marp.mkdir(parents=True)
    twin = marp / f"{slug}-infographic-standalone-2026-09-01.html"
    twin.write_text("<html></html>", encoding="utf-8")
    assert twins.current_standalone_twin(tmp_path, slug) == twin


def test_current_standalone_twin_none_when_missing(tmp_path: Path):
    assert twins.current_standalone_twin(tmp_path, "missing-slug") is None


def test_react_deck_dir_and_iterators(tmp_path: Path):
    deck = tmp_path / "presentations" / "react-deck"
    deck.mkdir(parents=True)
    (deck / "package.json").write_text("{}", encoding="utf-8")
    (deck / "index.html").write_text("<html></html>", encoding="utf-8")
    assert twins.react_deck_dir(tmp_path, "react-deck") == deck
    assert twins.react_deck_dir(tmp_path, "nope") is None
    assert twins.iter_react_deck_index_files(tmp_path) == [deck / "index.html"]
    assert twins.iter_standalone_twin_files(tmp_path) == []
    assert twins.iter_react_deck_index_files(tmp_path / "missing") == []


def test_bundle_manifest_paths(tmp_path: Path):
    dist = tmp_path / "dist"
    assets = dist / "assets"
    assets.mkdir(parents=True)
    (dist / "index.html").write_text("<html></html>", encoding="utf-8")
    (assets / "app.css").write_text("body{}", encoding="utf-8")
    mapping = twins.bundle_manifest_paths(dist)
    assert set(mapping) == {"index.html", "assets/app.css"}


def test_build_react_bundle_requires_npm(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    deck_dir = tmp_path / "deck"
    deck_dir.mkdir()
    (deck_dir / "package.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(twins, "_which", lambda _name: None)
    with pytest.raises(RuntimeError, match="npm not on PATH"):
        twins.build_react_bundle(deck_dir)


def test_build_react_bundle_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    deck_dir = tmp_path / "deck"
    deck_dir.mkdir()
    (deck_dir / "package.json").write_text("{}", encoding="utf-8")

    def fake_run(_cmd, cwd, check, capture_output, text):
        dist = Path(cwd) / "dist"
        dist.mkdir(exist_ok=True)
        (dist / "index.html").write_text("<html></html>", encoding="utf-8")

    monkeypatch.setattr(twins, "_which", lambda _name: "/usr/bin/npm")
    monkeypatch.setattr(twins.subprocess, "run", fake_run)
    assert twins.build_react_bundle(deck_dir) == deck_dir / "dist"


def test_build_react_bundle_missing_dist(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    deck_dir = tmp_path / "deck"
    deck_dir.mkdir()
    (deck_dir / "package.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(twins, "_which", lambda _name: "/usr/bin/npm")
    monkeypatch.setattr(twins.subprocess, "run", MagicMock())
    with pytest.raises(RuntimeError, match="missing after vite"):
        twins.build_react_bundle(deck_dir)


def test_current_standalone_twin_from_current_exports(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    slug = "from-exports"
    export = tmp_path / "presentations" / slug / "src" / "marp" / f"{slug}-infographic-standalone-2026-10-01.html"
    export.parent.mkdir(parents=True)
    export.write_text("<html></html>", encoding="utf-8")
    monkeypatch.setattr(
        twins.deck_versions,
        "current_exports",
        lambda _root, _topic: [export],
    )
    assert twins.current_standalone_twin(tmp_path, slug) == export
