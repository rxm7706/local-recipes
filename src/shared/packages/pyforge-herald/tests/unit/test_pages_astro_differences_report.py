"""Story 62.1 (spec-pyforge-steward:CAP-175): two built trees that differ say how.

``pages_astro.differences_report`` is the assertion message of the two-builds test in ``test_one_generator.py``. On
2026-11-27 that test failed once on CI naming only ``pagefind/pagefind-entry.json``, and nothing said how it differed;
the report names every differing path and shows the first few differences.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "meta"))
from pages_astro import differences_report  # noqa: E402 -- the shared Pages helpers

# pages_astro reads docs-site/ at import (the install's state), so this module runs in herald's live-tree half.
pytestmark = pytest.mark.live_tree


def test_a_text_file_that_differs_shows_its_changed_line() -> None:
    entry = '{"version":"1.5.2","languages":{"en":{"hash":"en_1","page_count":%d}}}'
    one = {"pagefind/pagefind-entry.json": (entry % 108).encode(), "index.html": b"<p>same</p>"}
    two = {"pagefind/pagefind-entry.json": (entry % 107).encode(), "index.html": b"<p>same</p>"}
    report = differences_report(one, two)
    assert report.splitlines()[0] == "1 file(s) differ: ['pagefind/pagefind-entry.json']"
    assert "--- first/pagefind/pagefind-entry.json" in report
    assert "+++ second/pagefind/pagefind-entry.json" in report
    assert '-{"version":"1.5.2","languages":{"en":{"hash":"en_1","page_count":108}}}' in report
    assert '+{"version":"1.5.2","languages":{"en":{"hash":"en_1","page_count":107}}}' in report
    assert "index.html" not in report


def test_a_binary_file_shows_each_side_s_size_and_hash() -> None:
    report = differences_report({"wasm.en.pagefind": b"\xff\x00\x01"}, {"wasm.en.pagefind": b"\xff\x00"})
    assert "--- wasm.en.pagefind: binary" in report
    assert "  first: 3 bytes, sha256 " in report
    assert "  second: 2 bytes, sha256 " in report


def test_it_names_every_differing_path_and_shows_the_first_few() -> None:
    one = {f"f{n}.txt": f"a{n}\n".encode() for n in range(5)}
    two = {f"f{n}.txt": f"b{n}\n".encode() for n in range(5)}
    report = differences_report(one, two, files=2)
    assert report.splitlines()[0] == "5 file(s) differ: ['f0.txt', 'f1.txt', 'f2.txt', 'f3.txt', 'f4.txt']"
    assert "--- first/f1.txt" in report
    assert "--- first/f2.txt" not in report


def test_a_long_diff_is_cut_and_says_how_much_is_left() -> None:
    one = {"page.html": "\n".join(f"a{n}" for n in range(100)).encode()}
    two = {"page.html": "\n".join(f"b{n}" for n in range(100)).encode()}
    report = differences_report(one, two, lines=10)
    assert report.splitlines()[-1].startswith("... ")
    assert report.splitlines()[-1].endswith(" more diff lines")
    assert len(report.splitlines()) == 1 + 10 + 1


def test_identical_trees_report_nothing_differs() -> None:
    assert differences_report({"a": b"1"}, {"a": b"1"}) == "0 file(s) differ: []"
