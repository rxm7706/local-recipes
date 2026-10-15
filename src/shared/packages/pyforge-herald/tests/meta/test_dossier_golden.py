"""Story 43.1: golden parity of the dossier block renderers (AC2, AC3).

Until Story 43.7 this test rendered every block type through both generators, the Jinja macros and the Astro
renderer, and compared them. With the Jinja path deleted, the streams it rendered are frozen in
``tests/fixtures/dossier-block-goldens-2026-10-15.json`` (the Astro renderer gave the same that day), and the one
renderer, ``docs-site/src/lib/dossier-blocks.ts``, is held to them: a block that renders differently is a change to
review, never a silent drift.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[6]
DOCS_SITE = REPO_ROOT / "docs-site"
GOLDENS = json.loads(
    (Path(__file__).resolve().parents[1] / "fixtures" / "dossier-block-goldens-2026-10-15.json").read_text("utf-8")
)
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node is not on PATH")


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


def _render_ts(block: dict) -> str:
    payload = json.dumps(block)
    script = (
        f"import {{ renderBlock }} from './src/lib/dossier-blocks.ts';process.stdout.write(renderBlock({payload}));"
    )
    proc = subprocess.run(
        ["node", "--experimental-strip-types", "-e", script], cwd=DOCS_SITE, capture_output=True, text=True, check=False
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


@pytest.mark.parametrize("block_type", list(GOLDENS["fixtures"]))
def test_ac2_golden_per_block_type(block_type: str) -> None:
    assert _tokens(_render_ts(GOLDENS["fixtures"][block_type])) == GOLDENS["tokens"][block_type]


def test_ac2_fourteen_block_sequence() -> None:
    names = list(GOLDENS["fixtures"])
    assert len(names) == 14
    html = "".join(_render_ts(GOLDENS["fixtures"][name]) for name in names)
    assert _tokens(html) == [token for name in names for token in GOLDENS["tokens"][name]]


def test_ac3_inline_vocabulary() -> None:
    html = _render_ts(GOLDENS["inline"])
    assert "\x00" not in html
    assert _tokens(html) == GOLDENS["tokens"]["prose-inline-vocabulary"]
