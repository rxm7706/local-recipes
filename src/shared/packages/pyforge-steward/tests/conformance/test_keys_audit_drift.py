"""Drift-detection primitive (FR-4) — proven both ways (Story 1.2).

`keys.scan_file` must flag the fixture reproducing the pre-fix unconditional-
injection shape, and must stay clean against the real, already-fixed
`.claude/skills/conda-forge-expert/scripts/_http.py`. Story 1.6 wires this
into a `steward keys audit --drift` verb; this story only proves the
primitive itself.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.steward.keys import DriftFinding, locate_http_module, scan_file, scan_source

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "ungated_jfrog_auth.py"


def test_fixture_reproducing_the_pre_fix_shape_yields_exactly_one_finding():
    findings = scan_file(FIXTURE_PATH)

    assert len(findings) == 1
    finding = findings[0]
    assert isinstance(finding, DriftFinding)
    assert finding.function == "build_request_headers"
    assert finding.line > 0


def test_the_real_fixed_http_py_is_clean():
    # locate_http_module() is the same marker-walk keys.py itself uses to
    # find the delegate target — reused here instead of a hardcoded relative
    # path so this test tracks wherever the module actually resolved to.
    assert scan_file(locate_http_module()) == []


def test_malformed_source_raises_syntax_error_rather_than_being_swallowed():
    with pytest.raises(SyntaxError):
        scan_source("not valid python(")


def test_pep263_encoding_cookie_file_is_scanned_not_unicode_errored(tmp_path):
    # scan_file honors a PEP 263 coding cookie via tokenize.open — a plain
    # utf-8 read of this latin-1 file would raise UnicodeDecodeError. The
    # embedded ungated assignment proves the file was actually scanned.
    source = (
        b"# -*- coding: latin-1 -*-\n"
        b"# caf\xe9\n"
        b"import os\n"
        b"\n"
        b"\n"
        b"def attach(url):\n"
        b"    headers = {}\n"
        b'    headers["X-Api"] = os.environ["SYNTHETIC_KEY"]\n'
        b"    return headers\n"
    )
    path = tmp_path / "latin1_fixture.py"
    path.write_bytes(source)

    findings = scan_file(path)

    assert len(findings) == 1
    assert findings[0].function == "attach"
