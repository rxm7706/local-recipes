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
        (
            "<b>raw</b> & ![img](x.png)",
            "<p>&lt;b&gt;raw&lt;/b&gt; &amp; ![img](x.png)</p>",
        ),  # loop 3, row 47: images stay literal
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
        # loop 3, row 46: the info-string grammar is CommonMark's (first word, cut at , or {), any indent opens,
        # a backtick fence's info holds no backtick, a deeper-indented backtick line inside the fence is code
        ("```c#\nx\n```\nafter", '<pre><code class="language-c#">x\n</code></pre>\n<p>after</p>'),
        ("```{r}\nx\n```\nafter", "<pre><code>x\n</code></pre>\n<p>after</p>"),
        ("```python,linenos\nx\n```\nafter", '<pre><code class="language-python">x\n</code></pre>\n<p>after</p>'),
        ("```bash:1\nx\n```\nafter", '<pre><code class="language-bash:1">x\n</code></pre>\n<p>after</p>'),
        ("```bash{.cls}\nx\n```\nafter", '<pre><code class="language-bash">x\n</code></pre>\n<p>after</p>'),
        ("    ```\n    x\n    ```\nafter", "<pre><code>x\n</code></pre>\n<p>after</p>"),
        ("~~~ `tick`\nx\n~~~\nafter", '<pre><code class="language-`tick`">x\n</code></pre>\n<p>after</p>'),
        ("```x`y\nz", "<p>``<code>x</code>y z</p>"),  # not a fence: a backtick in a backtick fence's info string
        ("```\nx\n      ```\ny\n```\nafter", "<pre><code>x\n      ```\ny\n</code></pre>\n<p>after</p>"),
        ("   ```\nx\n   ```\nafter", "<pre><code>x\n</code></pre>\n<p>after</p>"),
        # loop 3, row 47: //host and /rooted targets, a traversing path and an image stay literal; a fragment passes
        (
            "[a](//evil.example/p) [b](/root) [e](../x) [f](#frag)",
            '<p>[a](//evil.example/p) [b](/root) [e](../x) <a href="#frag">f</a></p>',
        ),
        ("[h](HTTPS://e.test/x) [m](mailto:x@y)", '<p><a href="HTTPS://e.test/x">h</a> [m](mailto:x@y)</p>'),
        # row 47: nested lists keep their own tag, an <ol> carries start, a four-digit marker is a paragraph
        ("- a\n  1. one\n  2. two\n- b", "<ul><li>a<ol><li>one</li><li>two</li></ol></li><li>b</li></ul>"),
        ("1. a\n   - x\n   - y\n2. b", "<ol><li>a<ul><li>x</li><li>y</li></ul></li><li>b</li></ol>"),
        ("3. three\n4. four", '<ol start="3"><li>three</li><li>four</li></ol>'),
        ("- a\n  5. five", '<ul><li>a<ol start="5"><li>five</li></ol></li></ul>'),
        ("2026. The year", "<p>2026. The year</p>"),
        ("10. ten", '<ol start="10"><li>ten</li></ol>'),
    ],
)
def test_render_markdown(text: str, expected: str) -> None:
    assert render_markdown(text) == expected


def test_a_relative_link_is_prefixed_with_the_link_base_and_nothing_else_is() -> None:
    """Loop 3, row 47: the card sits beside the mounted skill folder, so a runbook's relative link points into it."""
    text = "[s](steps.md) [r](references/x.md#top) [h](https://e.test/x) [f](#frag) [a](/abs) [p](//h/x) [t](../up)"
    assert render_markdown(text, link_base="environment/") == (
        '<p><a href="environment/steps.md">s</a> <a href="environment/references/x.md#top">r</a> '
        '<a href="https://e.test/x">h</a> <a href="#frag">f</a> [a](/abs) [p](//h/x) [t](../up)</p>'
    )


def test_skip_leading_h1_drops_only_a_first_line_h1() -> None:
    """Loop 3, row 55: the runbook's title is the card's h1 already; its steps sit one level under Steps."""
    assert render_markdown("# Title\n\n## 1. Step\n\ntext", skip_leading_h1=True) == "<h3>1. Step</h3>\n<p>text</p>"
    assert render_markdown("\n\n# Title\n\n## 1. Step", skip_leading_h1=True) == "<h3>1. Step</h3>"
    assert render_markdown("intro\n\n# Title", skip_leading_h1=True) == "<p>intro</p>\n<h2>Title</h2>"
    assert render_markdown("## Not an h1", skip_leading_h1=True) == "<h3>Not an h1</h3>"
    assert render_markdown("# Title\n\n## Step", skip_leading_h1=False) == "<h2>Title</h2>\n<h3>Step</h3>"


def test_render_markdown_is_deterministic_and_closes_every_block() -> None:
    text = "# T\n\npara\n\n- item\n\n```sh\nx\n```\n\ntail **b**\n"
    first = render_markdown(text)
    assert first == render_markdown(text)
    assert first.count("<ul>") == first.count("</ul>") == 1
    assert first.count("<pre>") == first.count("</pre>") == 1
    assert first.endswith("<p>tail <strong>b</strong></p>")


def test_heading_offset_demotes_every_heading_and_stops_at_h6() -> None:
    assert render_markdown("# a\n\n## b\n\n##### c", heading_offset=2) == "<h3>a</h3>\n<h4>b</h4>\n<h6>c</h6>"
