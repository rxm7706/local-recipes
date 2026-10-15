"""Story 44.1: pages-check judges every shelf page's body and the links inside it.

Until 2026-10-14 every Starlight shelf page rendered an empty body (the shelf loader stored the
markdown but never rendered it), and pages-check walked links on herald pages only, so a dead
link or an empty page on the docs shelf passed. These cases drive ``_check_shelf_pages`` on a
fixture artifact.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SITE_URL = "https://rxm7706.github.io/local-recipes"


def _repo_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "pixi.toml").is_file() and (candidate / "docsite" / "tools").is_dir():
            return candidate
    raise AssertionError("could not locate repo root")


def _assemble_pages():
    path = _repo_root() / "docsite" / "tools" / "assemble_pages.py"
    spec = importlib.util.spec_from_file_location("assemble_pages_shelf_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path.remove(str(path.parent))
    return mod


def _page(body: str, *, footer: str = '<a href="/local-recipes/">Previous Home page</a>') -> str:
    """A Starlight-shaped page: the markdown container, then the pagination footer inside <main>,
    as the real build renders it (the footer's words must never count as body)."""
    return (
        '<html><body><main><div class="content-panel"><div class="sl-markdown-content astro-x">'
        f"{body}</div></div><footer>{footer}</footer></main></body></html>"
    )


def _artifact(tmp_path: Path, pages: dict[str, str]) -> Path:
    root = tmp_path / "site"
    for rel, text in pages.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    return root


def test_a_shelf_with_bodies_and_resolving_links_passes(tmp_path: Path) -> None:
    root = _artifact(
        tmp_path,
        {
            "index.html": _page('<p>Home <a href="/local-recipes/how-to/">How-to</a> <a href="herald/">Herald</a></p>'),
            "how-to/index.html": _page(
                '<p>Guides <a href="/local-recipes/#top">top</a> <a href="https://github.com/x">ext</a></p>'
            ),
            "herald/index.html": "<html>herald pages are judged elsewhere</html>",
        },
    )
    _assemble_pages()._check_shelf_pages(root, SITE_URL)


def test_an_empty_shelf_body_fails_even_with_a_footer(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = _artifact(tmp_path, {"index.html": _page(" "), "how-to/index.html": _page("<p>ok</p>")})
    with pytest.raises(SystemExit):
        _assemble_pages()._check_shelf_pages(root, SITE_URL)
    assert "empty shelf page body: index.html" in capsys.readouterr().err


def test_a_broken_shelf_link_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = _artifact(tmp_path, {"index.html": _page('<p><a href="/local-recipes/MAP/">map</a></p>')})
    with pytest.raises(SystemExit):
        _assemble_pages()._check_shelf_pages(root, SITE_URL)
    assert "broken shelf link: index.html -> '/local-recipes/MAP/'" in capsys.readouterr().err


def test_a_shelf_link_missing_the_base_path_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = _artifact(
        tmp_path, {"index.html": _page('<p><a href="/how-to/">how-to</a></p>'), "how-to/index.html": _page("<p>x</p>")}
    )
    with pytest.raises(SystemExit):
        _assemble_pages()._check_shelf_pages(root, SITE_URL)
    assert "outside the base path" in capsys.readouterr().err


def test_no_shelf_page_at_all_fails(tmp_path: Path) -> None:
    root = _artifact(tmp_path, {"index.html": "<html>no markdown container</html>"})
    with pytest.raises(SystemExit):
        _assemble_pages()._check_shelf_pages(root, SITE_URL)


def test_the_link_plugins_are_wired_and_two_are_vendored() -> None:
    root = _repo_root() / "docs-site"
    config = (root / "astro.config.mjs").read_text(encoding="utf-8")
    for name in ("rehypeShelfLinks", "rehypeMarkdownLinks", "rehypeBasePaths"):
        assert f"[{name}" in config, name
    assert config.index("[rehypeShelfLinks") < config.index("[rehypeMarkdownLinks") < config.index("[rehypeBasePaths")
    readme = (root / "README.md").read_text(encoding="utf-8")
    for vendored in ("src/rehype-markdown-links.js", "src/rehype-base-paths.js"):
        assert f"`{vendored}`" in readme, vendored
    loader = (root / "src" / "loaders" / "shelf-docs-loader.ts").read_text(encoding="utf-8")
    assert "rendered: await renderMarkdown(" in loader


def test_nested_divs_in_the_body_do_not_end_it_early(tmp_path: Path) -> None:
    body = '<div class="expressive-code"><div><pre>code</pre></div></div><p>after the code block</p>'
    root = _artifact(tmp_path, {"index.html": _page(body, footer="")})
    _assemble_pages()._check_shelf_pages(root, SITE_URL)


def test_a_relative_link_on_the_404_page_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = _artifact(
        tmp_path,
        {
            "index.html": _page("<p>home</p>"),
            "how-to/index.html": _page("<p>x</p>"),
            "404.html": _page('<p><a href="how-to/">how-to</a></p>'),
        },
    )
    with pytest.raises(SystemExit):
        _assemble_pages()._check_shelf_pages(root, SITE_URL)
    assert "relative link on the 404 page" in capsys.readouterr().err


def test_a_link_escaping_the_artifact_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "outside.html").write_text("x", encoding="utf-8")
    root = _artifact(tmp_path, {"how-to/x/index.html": _page('<p><a href="../../../outside.html">out</a></p>')})
    with pytest.raises(SystemExit):
        _assemble_pages()._check_shelf_pages(root, SITE_URL)
    assert "escapes the artifact" in capsys.readouterr().err


def test_a_percent_encoded_link_resolves(tmp_path: Path) -> None:
    root = _artifact(
        tmp_path,
        {
            "index.html": _page('<p><a href="/local-recipes/how-to/my%20notes/">notes</a></p>'),
            "how-to/my notes/index.html": _page("<p>n</p>"),
        },
    )
    _assemble_pages()._check_shelf_pages(root, SITE_URL)


def test_a_broken_image_in_a_body_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = _artifact(
        tmp_path, {"index.html": _page('<p>A figure: <img src="/local-recipes/img/missing.png" alt="x"></p>')}
    )
    with pytest.raises(SystemExit):
        _assemble_pages()._check_shelf_pages(root, SITE_URL)
    assert "broken shelf link" in capsys.readouterr().err


def test_check_runs_the_shelf_check() -> None:
    import inspect

    assert "_check_shelf_pages(artifact_root, site_url)" in inspect.getsource(_assemble_pages().check)
