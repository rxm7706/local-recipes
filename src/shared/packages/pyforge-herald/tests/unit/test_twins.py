"""Unit tests for ``pyforge.herald.twins`` (CAP-55 D5)."""

from __future__ import annotations

from pathlib import Path

import pytest

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


def test_twin_origin_error_message(tmp_path: Path):
    finding = twins.OriginFinding(
        path=tmp_path / "bad.html",
        origin="fonts.googleapis.com",
        reference="https://fonts.googleapis.com/css",
    )
    err = twins.TwinOriginError(finding)
    assert "fonts.googleapis.com" in str(err)
    assert "bad.html" in str(err)
