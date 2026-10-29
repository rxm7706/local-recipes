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
        (  # loop 5, row 81: the default link_base is None, so a relative target is literal unless a folder is mounted
            "[steps](steps.md) and [docs](https://example.test/x)",
            '<p>[steps](steps.md) and <a href="https://example.test/x">docs</a></p>',
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
        # loop 4, row 68: tabs count as four columns (a tab-indented close is code, a tab-indented nested item nests);
        # a nested run of mixed markers takes one list per run; an item whose text opens a fence is that fence
        ("```\nx\n\t```\ny\n```\nafter", "<pre><code>x\n\t```\ny\n</code></pre>\n<p>after</p>"),
        ("- a\n\t- b\n- c", "<ul><li>a<ul><li>b</li></ul></li><li>c</li></ul>"),
        ("1. a\n  - x\n  2. y\n2. b", '<ol><li>a<ul><li>x</li></ul><ol start="2"><li>y</li></ol></li><li>b</li></ol>'),
        (
            "- ```bash\n  cmd\n  ```\n- next",
            '<pre><code class="language-bash">cmd\n</code></pre>\n<ul><li>next</li></ul>',
        ),
        ("\t```\nx\n\t```\nafter", "<pre><code>x\n</code></pre>\n<p>after</p>"),
        # loop 4, row 69: the fence language is an attribute, so its quotes and angle brackets are escaped
        (
            '```a"onmouseover="alert(1)\nx\n```',
            '<pre><code class="language-a&quot;onmouseover=&quot;alert(1)">x\n</code></pre>',
        ),
        ("```<b>&x\nx\n```", '<pre><code class="language-&lt;b&gt;&amp;x">x\n</code></pre>'),
        # loop 4, row 61: encoded dots are dots to the browser (a leading ./ names the same folder: the link_base test)
        (
            "[a](%2e%2e/x) [b](.%2e/x) [c](%2E%2E/x) [d](./steps.md)",
            "<p>[a](%2e%2e/x) [b](.%2e/x) [c](%2E%2E/x) [d](./steps.md)</p>",
        ),
        # loop 5, row 81: a ./ before a scheme is not a file; row 93: a nested marker before a fence opener
        (
            "[x](./javascript:alert%281%29) [y](./data:text/html,x)",
            "<p>[x](./javascript:alert%281%29) [y](./data:text/html,x)</p>",
        ),
        (
            "- - ```bash\n  cmd\n  ```\n## after",
            '<pre><code class="language-bash">cmd\n</code></pre>\n<h3>after</h3>',
        ),
        # loop 5, row 82: a tab inside a fence body or a code span is emitted as it is; a leading tab is four columns
        ("```make\nall:\n\tgcc a.c\n```", '<pre><code class="language-make">all:\n\tgcc a.c\n</code></pre>'),
        ("`a\tb` c\td", "<p><code>a\tb</code> c\td</p>"),
        (
            "- item\n  ```make\n  all:\n  \tgcc\n  ```",
            '<ul><li>item</li></ul>\n<pre><code class="language-make">all:\n\tgcc\n</code></pre>',
        ),
        ("\t```\n\t\tx\n\t```", "<pre><code>\tx\n</code></pre>"),
        # loop 6, row 99: a tab between a list marker and a fence opener reaches the next four-column stop
        ("-\t```sh\n\tcmd\n\t```\nafter", '<pre><code class="language-sh">cmd\n</code></pre>\n<p>after</p>'),
        ("1.\t```sh\n\tcmd\n\t```", '<pre><code class="language-sh">cmd\n</code></pre>'),
        # loop 6, row 100: a tab after spaces reaches the next stop, and a tab that crosses the fence's indent leaves
        # its remaining columns as spaces; tabs after leading spaces count on a structural line too
        ("  ```\n \tgcc\n  ```", "<pre><code>  gcc\n</code></pre>"),
        ("  ```\n\tx\n  ```", "<pre><code>  x\n</code></pre>"),
        ("  \t```\n  \tcmd\n  \t```", "<pre><code>cmd\n</code></pre>"),
    ],
)
def test_render_markdown(text: str, expected: str) -> None:
    assert render_markdown(text) == expected


def test_the_empty_link_base_resolves_a_relative_target_beside_the_page() -> None:
    """Loop 4, row 61 under ``link_base=""``: a leading ``./`` names the same folder; loop 5, row 81: a ``./`` before
    a scheme stays literal under every base; row 93: an angle-bracket destination is unwrapped."""
    assert render_markdown("[s](steps.md) [d](./steps.md) [e](././x.md)", link_base="") == (
        '<p><a href="steps.md">s</a> <a href="steps.md">d</a> <a href="x.md">e</a></p>'
    )
    for base in ("", "e/"):
        assert render_markdown(
            "[x](./javascript:alert%281%29) [y](./data:text/html,x) [z](./https://e.test/x)", link_base=base
        ) == ("<p>[x](./javascript:alert%281%29) [y](./data:text/html,x) [z](./https://e.test/x)</p>")
    assert render_markdown("[a](<steps.md>) [b](<https://e.test/x>) [c](<>) [d](<../up>)", link_base="e/") == (
        '<p><a href="e/steps.md">a</a> <a href="https://e.test/x">b</a> [c](&lt;&gt;) [d](&lt;../up&gt;)</p>'
    )
    # loop 6, row 107: a half-bracketed or nested <destination> is no file name, and stays literal under every base
    for base in (None, "", "e/"):
        assert render_markdown("[a](<steps.md) [c](<a>b) [d](<./javascript:alert(1)>)", link_base=base) == (
            "<p>[a](&lt;steps.md) [c](&lt;a&gt;b) [d](&lt;./javascript:alert(1)&gt;)</p>"
        )
    # loop 7, row 117: a destination that does not start with `<` is a plain one, where CommonMark admits `<` and `>`
    # (micromark renders each of these a link; 080ce9f012 did too)
    for base in (None, "", "e/"):
        assert render_markdown("[x](https://e.test/?q=<a>) [q](https://e.test/a->b)", link_base=base) == (
            '<p><a href="https://e.test/?q=&lt;a&gt;">x</a> <a href="https://e.test/a-&gt;b">q</a></p>'
        )
    assert render_markdown("[r](a<b.md) [b](steps.md>)", link_base="e/") == (
        '<p><a href="e/a&lt;b.md">r</a> <a href="e/steps.md&gt;">b</a></p>'
    )
    assert render_markdown("[r](a<b.md) [b](steps.md>)") == "<p>[r](a&lt;b.md) [b](steps.md&gt;)</p>"


def test_a_non_skill_card_leaves_relative_links_literal() -> None:
    """Loop 4, row 58: with no mounted folder beside the card (``link_base=None``), a relative target is text; loop
    5, row 81: that is the default."""
    expected = '<p>[s](steps.md) <a href="https://e.test/x">h</a> <a href="#top">f</a></p>'
    assert render_markdown("[s](steps.md) [h](https://e.test/x) [f](#top)", link_base=None) == expected
    assert render_markdown("[s](steps.md) [h](https://e.test/x) [f](#top)") == expected


def test_a_relative_link_is_prefixed_with_the_link_base_and_nothing_else_is() -> None:
    """Loop 3, row 47: the card sits beside the mounted skill folder, so a runbook's relative link points into it."""
    text = "[s](steps.md) [r](references/x.md#top) [h](https://e.test/x) [f](#frag) [a](/abs) [p](//h/x) [t](../up)"
    assert render_markdown(text, link_base="environment/") == (
        '<p><a href="environment/steps.md">s</a> <a href="environment/references/x.md#top">r</a> '
        '<a href="https://e.test/x">h</a> <a href="#frag">f</a> [a](/abs) [p](//h/x) [t](../up)</p>'
    )


def test_skip_leading_h1_drops_only_a_first_line_h1() -> None:
    """Loop 3, row 55: the runbook's title is the card's h1 already; its steps sit one level under Steps. Loop 4,
    row 67: a tab-separated, indented or empty level-1 heading is the title too."""
    assert render_markdown("# Title\n\n## 1. Step\n\ntext", skip_leading_h1=True) == "<h3>1. Step</h3>\n<p>text</p>"
    assert render_markdown("#\tTitle\n\n## Step", skip_leading_h1=True) == "<h3>Step</h3>"
    assert render_markdown("   # Title\n\n## Step", skip_leading_h1=True) == "<h3>Step</h3>"
    assert render_markdown("# \n\n## Step", skip_leading_h1=True) == "<h3>Step</h3>"
    assert render_markdown("#Title\n\n## Step", skip_leading_h1=True) == "<p>#Title</p>\n<h3>Step</h3>"
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
