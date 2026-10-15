"""Story 43.1: golden parity between Jinja macros and Astro block renderers (AC2, AC3)."""

from __future__ import annotations

import json
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader, StrictUndefined

REPO_ROOT = Path(__file__).resolve().parents[6]
TEMPLATES = REPO_ROOT / "docsite" / "templates"
DOCS_SITE = REPO_ROOT / "docs-site"


class _TokenParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tokens: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        self.tokens.append(tag)

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.tokens.append(text)


def _tokens(html: str) -> list[str]:
    parser = _TokenParser()
    parser.feed(html)
    return parser.tokens


def _jinja_env() -> Environment:
    sys.path.insert(0, str(REPO_ROOT / "docsite"))
    from build import md_inline  # noqa: E402

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        undefined=StrictUndefined,
        autoescape=False,
    )
    env.filters["md"] = md_inline
    return env


def _render_jinja(block: dict) -> str:
    env = _jinja_env()
    module = env.get_template("blocks.html.j2").module
    return module.render(block).strip()


def _render_ts(block: dict) -> str:
    payload = json.dumps(block)
    cmd = [
        "node",
        "--experimental-strip-types",
        "-e",
        (
            "import { renderBlock } from './src/lib/dossier-blocks.ts';"
            f"process.stdout.write(renderBlock({payload}));"
        ),
    ]
    proc = subprocess.run(
        cmd,
        cwd=DOCS_SITE,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


def _assert_same(html_a: str, html_b: str) -> None:
    assert _tokens(html_a) == _tokens(html_b)


BLOCK_FIXTURES: dict[str, dict] = {
    "lede": {"type": "lede", "md": "Lead **bold** line."},
    "prose": {"type": "prose", "body": ["One paragraph.", "Second *em* line."]},
    "h3": {"type": "h3", "num": "1", "text": "Heading text"},
    "table": {
        "type": "table",
        "headers": ["Col"],
        "rows": [{"cells": ["cell"], "mono": [True]}],
    },
    "callout": {"type": "callout", "label": "Note", "body": ["Body line."], "tone": ""},
    "finding": {
        "type": "finding",
        "label": "Find",
        "body": ["Detail."],
        "alarm": False,
        "accent": "",
    },
    "stats": {"type": "stats", "stats": [{"value": "1", "label": "One"}]},
    "quote": {"type": "quote", "md": "Quoted line."},
    "relations": {"type": "relations", "items": [{"glyph": "→", "md": "rel"}]},
    "lattice": {
        "type": "lattice",
        "rungs": [{"exit": "0", "name": "n", "desc": "d", "tone": "", "exit_tone": ""}],
        "note": "note",
    },
    "engines": {
        "type": "engines",
        "engines": [{"name": "E", "verb": "run", "body": ["p"]}],
    },
    "chips": {"type": "chips", "chips": ["alpha", "beta"]},
    "note": {"type": "note", "md": "Soft note."},
    "verify": {"type": "verify", "md": "Verify note."},
}


@pytest.mark.parametrize("block_type", list(BLOCK_FIXTURES.keys()))
def test_ac2_golden_per_block_type(block_type: str) -> None:
    block = BLOCK_FIXTURES[block_type]
    _assert_same(_render_jinja(block), _render_ts(block))


def test_ac2_fourteen_block_sequence() -> None:
    blocks = [BLOCK_FIXTURES[name] for name in BLOCK_FIXTURES]
    jinja_html = "".join(_render_jinja(b) for b in blocks)
    ts_html = "".join(_render_ts(b) for b in blocks)
    _assert_same(jinja_html, ts_html)


def test_ac3_inline_vocabulary() -> None:
    block = {
        "type": "prose",
        "body": [
            "Code `x`, **bold**, *em*, [link](https://example.com), arrow <<→>>, escape \\*",
            "`/stations/\\*/mcp`",
        ],
    }
    jinja_html = _render_jinja(block)
    ts_html = _render_ts(block)
    assert "\x00" not in jinja_html
    assert "\x00" not in ts_html
    _assert_same(jinja_html, ts_html)
