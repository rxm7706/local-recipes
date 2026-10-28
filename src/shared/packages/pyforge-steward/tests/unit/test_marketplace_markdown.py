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
        ("<b>raw</b> & ![img](x.png)", '<p>&lt;b&gt;raw&lt;/b&gt; &amp; !<a href="x.png">img</a></p>'),
        # loop 2, row 25
        (
            "```bash title=x\necho hi\n```\nafter",
            '<pre><code class="language-bash">echo hi\n</code></pre>\n<p>after</p>',
        ),
        ("  ```\n  x\n  ```", "<pre><code>x\n</code></pre>"),
        ("~~~yaml\na: 1\n~~~", '<pre><code class="language-yaml">a: 1\n</code></pre>'),
        ("````\n```\ninner\n```\n````", "<pre><code>```\ninner\n```\n</code></pre>"),
        ("1. one\n2. two", "<ol><li>one</li><li>two</li></ol>"),
        ("1) one\n   more", "<ol><li>one more</li></ol>"),
        ("- a\n  - b\n  - c\n- d", "<ul><li>a<ul><li>b</li><li>c</li></ul></li><li>d</li></ul>"),
        ("- a\n\n1. b", "<ul><li>a</li></ul>\n<ol><li>b</li></ol>"),
        (
            "- item\n  ```sh\n  cmd\n  ```\n- next",
            '<ul><li>item</li></ul>\n<pre><code class="language-sh">cmd\n</code></pre>\n<ul><li>next</li></ul>',
        ),
        (
            "[steps](steps.md) and [docs](https://example.test/x)",
            '<p><a href="steps.md">steps</a> and <a href="https://example.test/x">docs</a></p>',
        ),
        ("[j](javascript:alert(1)) [d](data:text/html,x)", "<p>[j](javascript:alert(1)) [d](data:text/html,x)</p>"),
        ("`[not](a-link)`", "<p><code>[not](a-link)</code></p>"),
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


def test_heading_offset_demotes_every_heading_and_stops_at_h6() -> None:
    assert render_markdown("# a\n\n## b\n\n##### c", heading_offset=2) == "<h3>a</h3>\n<h4>b</h4>\n<h6>c</h6>"
