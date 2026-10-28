"""Story 109.3, the review of 2026-10-28 (row 5): the card's minimal markdown renderer is a pure function."""

from __future__ import annotations

import pytest

from pyforge.steward.marketplace_pages import render_markdown


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("# Title", "<h2>Title</h2>"),
        ("## 1. Step", "<h3>1. Step</h3>"),
        ("###### deep", "<h6>deep</h6>"),  # never past h6
        ("one\ntwo\n\nthree", "<p>one two</p>\n<p>three</p>"),
        ("**Bold.** then `code`", "<p><strong>Bold.</strong> then <code>code</code></p>"),
        ("`**not bold**`", "<p><code>**not bold**</code></p>"),
        ("- a\n- b\n  continued\n- c", "<ul><li>a</li><li>b continued</li><li>c</li></ul>"),
        ("* star", "<ul><li>star</li></ul>"),
        ("```bash\necho <x>\n```", '<pre><code class="language-bash">echo &lt;x&gt;\n</code></pre>'),
        ("```\n# not a heading\n**not bold**\n```", "<pre><code># not a heading\n**not bold**\n</code></pre>"),
        ("```\nunterminated", "<pre><code>unterminated\n</code></pre>"),
        ("<b>raw</b> & [link](x)", "<p>&lt;b&gt;raw&lt;/b&gt; &amp; [link](x)</p>"),
        ("", ""),
        ("\n\n", ""),
    ],
)
def test_render_markdown(text: str, expected: str) -> None:
    assert render_markdown(text) == expected


def test_render_markdown_is_deterministic_and_closes_every_block() -> None:
    text = "# T\n\npara\n\n- item\n\n```sh\nx\n```\n\ntail **b**\n"
    first = render_markdown(text)
    assert first == render_markdown(text)
    assert first.count("<ul>") == first.count("</ul>") == 1
    assert first.count("<pre>") == first.count("</pre>") == 1
    assert first.endswith("<p>tail <strong>b</strong></p>")
