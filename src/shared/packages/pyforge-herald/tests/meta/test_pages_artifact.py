"""Story 27.2: unified GitHub Pages artifact (Starlight + herald + dashboard).

Story 42.2 (CAP-60): the Kedro-Viz mount is an artifact handoff that tolerates absence -- the
``test_42_2_*`` tests below build the real herald site around a fixture export, and around none."""

from __future__ import annotations

import importlib.util
import json
import re
import shutil
import sys
from pathlib import Path

import pytest


def _load_assemble_pages():
    root = _repo_root()
    path = root / "docsite" / "tools" / "assemble_pages.py"
    spec = importlib.util.spec_from_file_location("assemble_pages_under_test", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (
            candidate / "src" / "shared" / "packages" / "pyforge-herald"
        ).is_dir():
            return candidate
    raise AssertionError("could not locate repo root")


# Story 40.1 (FR-8.6): pages-check requires herald's shared menu, exactly as docsite/content/site.yml
# lists it, on every docs page and every herald shell page; the docs root also links every herald
# target from its sidebar. (label, docs path from the site root, herald href from the /herald/ mount)
_SHARED_MENU = [
    ("Docs", "", "../"),
    ("Overview", "herald/", "index.html"),
    ("Dossier", "herald/dossier/", "dossier/index.html"),
    ("Infographics", "herald/infographics/", "infographics/index.html"),
    ("Decks", "herald/decks/", "decks/index.html"),
    ("Kedro-Viz", "dashboard/kedro-viz/", "../dashboard/kedro-viz/"),
]


def _menu(kedro_viz: bool) -> list[tuple[str, str, str]]:
    return [entry for entry in _SHARED_MENU if kedro_viz or entry[0] != "Kedro-Viz"]


def _write_docs_pages(artifact: Path, base: str, *, kedro_viz: bool = True) -> None:
    """The docs root and 404 with the top menu and the Herald sidebar links, as Starlight renders them."""
    menu = _menu(kedro_viz)
    top = "".join(f'<a data-pf-menu-link href="{base}{path}">{label}</a>' for label, path, _ in menu)
    sidebar = "".join(f'<a href="{base}{path}">{label}</a>' for label, path, _ in menu[1:])
    for rel in ("index.html", "404.html"):
        (artifact / rel).write_text(
            f"<html>{top}{sidebar}<main><div class='sl-markdown-content'><p>Shelf page body.</p></div></main></html>",
            encoding="utf-8",
        )


_MANIFEST = {
    "export_commit": "0123456789abcdef0123456789abcdef01234567",
    "export_date": "2026-10-15T09:23:50Z",
    "kedro_viz_version": "12.5.0",
}


def _write_mounted_export(artifact: Path) -> None:
    """A mounted export as pages-build leaves it: the bundle and its manifest under the mount, and
    herald's pipelines page (with the shared menu) in front of it -- no redirect."""
    mount = artifact / "dashboard" / "kedro-viz"
    mount.mkdir(parents=True)
    (mount / "index.html").write_text("<html></html>", encoding="utf-8")
    (mount / "manifest.json").write_text(json.dumps(_MANIFEST), encoding="utf-8")
    menu = "".join(
        f'<a data-pf-menu-link href="{"../herald/" + href if label != "Kedro-Viz" else "kedro-viz/"}">{label}</a>'
        for label, _, href in _SHARED_MENU
    )
    (artifact / "dashboard" / "index.html").write_text(f"<html>{menu}</html>", encoding="utf-8")


def _write_shared_menu(artifact: Path, base: str, *, herald_index_extra: str = "") -> None:
    """The docs root and 404 with the top menu and Herald sidebar links, and herald's four shell
    pages with the same menu as relative links."""
    _write_docs_pages(artifact, base)
    for sub in ("", "dossier/", "infographics/", "decks/"):
        rel = "../" if sub else ""
        menu = "".join(f'<a data-pf-menu-link href="{rel}{href}">{label}</a>' for label, _, href in _SHARED_MENU)
        page = artifact / "herald" / sub / "index.html"
        page.parent.mkdir(parents=True, exist_ok=True)
        extra = herald_index_extra if not sub else ""
        page.write_text(f"<html>{menu}{extra}</html>", encoding="utf-8")


def test_dashboard_yml_is_sole_deploy_pages_caller() -> None:
    root = _repo_root()
    workflows = root / ".github" / "workflows"
    deploy_hits: list[str] = []
    for path in sorted(workflows.glob("*.yml")):
        text = path.read_text(encoding="utf-8")
        if "actions/deploy-pages" in text or "deploy-pages@" in text:
            deploy_hits.append(path.name)
    assert deploy_hits == ["pages.yml"]


def test_dashboard_yml_uploads_unified_artifact() -> None:
    root = _repo_root()
    text = (root / ".github/workflows/pages.yml").read_text(encoding="utf-8")
    assert "path: docs-site/build/site" in text
    assert "concurrency:" in text
    assert "group: pages" in text
    assert re.search(r"push:\s*\n\s*branches:\s*\[main\]", text)
    assert "workflow_dispatch" in text


def test_pages_yml_runs_pages_check_with_path_filters() -> None:
    root = _repo_root()
    text = (root / ".github/workflows/pages.yml").read_text(encoding="utf-8")
    assert "pages-check" in text
    assert "docs/how-to/**" in text
    assert "docs-site/**" in text
    assert "pull_request:" in text


def test_assemble_writes_redirect_per_herald_html(tmp_path: Path) -> None:
    assemble_pages = _load_assemble_pages()
    artifact = tmp_path / "site"
    artifact.mkdir()
    _write_shared_menu(artifact, "/local-recipes/")
    _write_mounted_export(artifact)

    assemble_pages._write_dossier_redirects(artifact)
    assemble_pages._ensure_kedro_viz_redirect(artifact)
    redirect = artifact / "dossier" / "index.html"
    assert redirect.is_file()
    assert "herald/dossier" in redirect.read_text(encoding="utf-8")
    assemble_pages.check(artifact, site_url="https://rxm7706.github.io/local-recipes")


def test_assemble_refuses_mount_collision(tmp_path: Path) -> None:
    assemble_pages = _load_assemble_pages()
    artifact = tmp_path / "site"
    artifact.mkdir()
    (artifact / "index.html").write_text("<html></html>", encoding="utf-8")
    (artifact / "herald").mkdir()
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "docsite").mkdir()
    (repo / "docsite" / "build.py").write_text("", encoding="utf-8")
    (repo / "pixi.toml").write_text("", encoding="utf-8")
    (repo / "docs").mkdir()
    (repo / "docs" / "dashboard").mkdir()

    with pytest.raises(SystemExit) as exc:
        assemble_pages.assemble(
            artifact,
            repo_root=repo,
            skip_herald_build=True,
            skip_docs_site_build=True,
        )
    assert exc.value.code == 1


def test_assemble_refuses_redirect_collision(tmp_path: Path) -> None:
    assemble_pages = _load_assemble_pages()
    artifact = tmp_path / "site"
    artifact.mkdir()
    (artifact / "index.html").write_text("<html></html>", encoding="utf-8")
    (artifact / "404.html").write_text("<html></html>", encoding="utf-8")
    herald = artifact / "herald"
    (herald / "dossier").mkdir(parents=True)
    (herald / "dossier" / "index.html").write_text("<html></html>", encoding="utf-8")
    (herald / "index.html").write_text("<html></html>", encoding="utf-8")
    (artifact / "dossier").mkdir()
    (artifact / "dossier" / "index.html").write_text("existing", encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        assemble_pages._write_dossier_redirects(artifact)
    assert exc.value.code == 1


def test_check_fails_on_missing_herald_page(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assemble_pages = _load_assemble_pages()
    artifact = tmp_path / "site"
    artifact.mkdir()
    (artifact / "index.html").write_text("<html></html>", encoding="utf-8")
    (artifact / "404.html").write_text("<html></html>", encoding="utf-8")
    herald = artifact / "herald"
    herald.mkdir()
    (herald / "index.html").write_text("<html></html>", encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        assemble_pages.check(artifact)
    assert exc.value.code == 1
    assert "missing required path herald/dossier/index.html" in capsys.readouterr().err


def test_check_fails_on_a_mount_without_its_redirect(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Story 42.2: a missing mount is a normal build, but a mount without its /kedro-viz/ redirect is not."""
    assemble_pages = _load_assemble_pages()
    artifact = tmp_path / "site"
    artifact.mkdir()
    _write_shared_menu(artifact, "/local-recipes/")
    _write_mounted_export(artifact)
    assemble_pages._write_dossier_redirects(artifact)

    with pytest.raises(SystemExit) as exc:
        assemble_pages.check(artifact, site_url="https://rxm7706.github.io/local-recipes")
    assert exc.value.code == 1
    assert "missing required path kedro-viz/index.html" in capsys.readouterr().err


# --- Story 42.2 (CAP-60): the Kedro-Viz mount is an artifact handoff that tolerates absence ---------

_SITE_URL = "https://rxm7706.github.io/local-recipes"
_BASE = "/local-recipes/"
#: A third-party reference inside the vendored bundle (Kedro-Viz loads Google Fonts): exempt by name.
_BUNDLE_INDEX = (
    '<html><head><link href="https://fonts.googleapis.com/css2?family=Inter" rel="stylesheet"></head>'
    '<body><div id="root"></div></body></html>'
)


def _fixture_export(root: Path, *, manifest: object = _MANIFEST) -> Path:
    """An export as atlas's viz-publish-stage leaves it (atlas Story 30.1): the bundle and its manifest.

    ``manifest`` is the JSON object to write, a raw string to write verbatim, or ``None`` for none."""
    root.mkdir(parents=True)
    (root / "index.html").write_text(_BUNDLE_INDEX, encoding="utf-8")
    (root / "api").mkdir()
    (root / "api" / "deploy-viz-metadata").write_text('{"timestamp": "unset", "version": "12.5.0"}', encoding="utf-8")
    if isinstance(manifest, str):
        (root / "manifest.json").write_text(manifest, encoding="utf-8")
    elif manifest is not None:
        (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root


def _dashboard_src(tmp_path: Path, export: Path | None, *, empty_input: bool = False) -> Path:
    """The build input tree, ``docs/dashboard/`` (its tracked README, and the export when present;
    ``empty_input`` leaves an empty ``kedro-viz/``, as a download step that found nothing might)."""
    src = tmp_path / "docs-dashboard"
    src.mkdir()
    (src / "README.md").write_text("# docs/dashboard\n", encoding="utf-8")
    if export is not None:
        shutil.copytree(export, src / "kedro-viz")
    elif empty_input:
        (src / "kedro-viz").mkdir()
    return src


def _assemble(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, export: Path | None, *, empty_input: bool = False
) -> Path:
    """pages-build around a synthetic docs shelf: the real herald build, the real mount and redirects."""
    monkeypatch.setenv("PYFORGE_PAGES_ONE_GENERATOR", "0")
    assemble_pages = _load_assemble_pages()
    artifact = tmp_path / "site"
    artifact.mkdir()
    _write_docs_pages(artifact, _BASE, kedro_viz=export is not None)
    assemble_pages.assemble(
        artifact,
        repo_root=_repo_root(),
        dashboard_src=_dashboard_src(tmp_path, export, empty_input=empty_input),
        skip_docs_site_build=True,
        site_url=_SITE_URL,
    )
    return artifact


def _menu_labels(page: Path) -> list[str]:
    return [label for _, label in _load_assemble_pages()._MENU_LINK.findall(page.read_text(encoding="utf-8"))]


def _hrefs(artifact: Path) -> list[tuple[str, str]]:
    href = re.compile(r"""(?:href|src)\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
    return [
        (page.relative_to(artifact).as_posix(), raw)
        for page in sorted(artifact.rglob("*.html"))
        for raw in href.findall(page.read_text(encoding="utf-8", errors="replace"))
    ]


def test_42_2_ac1_with_the_export(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    artifact = _assemble(tmp_path, monkeypatch, _fixture_export(tmp_path / "export"))
    _load_assemble_pages().check(artifact, site_url=_SITE_URL)

    assert (artifact / "dashboard/kedro-viz/index.html").read_text(encoding="utf-8") == _BUNDLE_INDEX
    redirect = (artifact / "kedro-viz/index.html").read_text(encoding="utf-8")
    assert 'url=../dashboard/kedro-viz/index.html"' in redirect
    for page in ("herald/index.html", "dashboard/index.html"):
        text = (artifact / page).read_text(encoding="utf-8")
        assert _MANIFEST["export_commit"] in text, page
        assert _MANIFEST["export_date"] in text, page
        assert _MANIFEST["export_commit"][:12] in text and "2026-10-15" in text, page
        assert "kedro-viz 12.5.0" in text, page
    # AC3: the shell pages, the pipelines page among them, carry the menu with Kedro-Viz.
    for page in ("herald/index.html", "herald/decks/index.html", "dashboard/index.html"):
        assert _menu_labels(artifact / page)[-1] == "Kedro-Viz", page
    # AC5: the bundle's own Google Fonts reference is exempt by name, and reported.
    assert "exempt vendored root dashboard/kedro-viz/ (AD-21 rule 5:" in capsys.readouterr().out


@pytest.mark.parametrize("empty_dir", [False, True], ids=["no-input-dir", "empty-input-dir"])
def test_42_2_ac2_without_the_export(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, empty_dir: bool) -> None:
    artifact = _assemble(tmp_path, monkeypatch, None, empty_input=empty_dir)
    _load_assemble_pages().check(artifact, site_url=_SITE_URL)

    assert not (artifact / "dashboard").exists()
    assert not (artifact / "kedro-viz").exists()
    linked = [(page, raw) for page, raw in _hrefs(artifact) if "kedro-viz" in raw]
    assert linked == []
    herald_index = (artifact / "herald/index.html").read_text(encoding="utf-8")
    assert "Kedro-Viz" not in herald_index and "kv-provenance" not in herald_index
    # AC3: the same pages render the menu without it.
    for page in ("index.html", "herald/index.html", "herald/dossier/index.html"):
        assert "Kedro-Viz" not in _menu_labels(artifact / page), page


def test_42_2_ac2_the_link_walk_refuses_a_leftover_link(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """The mutation the Spec names: a hardcoded Kedro-Viz link left in a page, built without the export."""
    artifact = _assemble(tmp_path, monkeypatch, None)
    page = artifact / "herald" / "decks" / "index.html"
    page.write_text(
        page.read_text(encoding="utf-8").replace("</body>", '<a href="../../dashboard/kedro-viz/">graph</a></body>'),
        encoding="utf-8",
    )
    with pytest.raises(SystemExit) as exc:
        _load_assemble_pages().check(artifact, site_url=_SITE_URL)
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "link to the absent Kedro-Viz mount: herald/decks/index.html -> '../../dashboard/kedro-viz/'" in err


def test_42_2_ac2_a_redirect_without_a_mount_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    assemble_pages = _load_assemble_pages()
    artifact = _assemble(tmp_path, monkeypatch, None)
    (artifact / "kedro-viz").mkdir()
    (artifact / "kedro-viz" / "index.html").write_text(
        assemble_pages.redirect_html("../dashboard/kedro-viz/"), encoding="utf-8"
    )
    with pytest.raises(SystemExit) as exc:
        assemble_pages.check(artifact, site_url=_SITE_URL)
    assert exc.value.code == 1
    assert "kedro-viz/ exists in the artifact but no Kedro-Viz export is mounted" in capsys.readouterr().err


_BAD_MANIFESTS = {
    "manifest-absent": None,
    "not-json": "{export_commit: nope",
    "lacks-commit": {"export_date": "2026-10-15T09:23:50Z", "kedro_viz_version": "12.5.0"},
    "lacks-date": {"export_commit": "0123456789abcdef0123456789abcdef01234567"},
}


@pytest.mark.parametrize("case", sorted(_BAD_MANIFESTS))
def test_42_2_ac4_the_build_refuses_a_malformed_export(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys, case: str
) -> None:
    """pages-build stops on the build input, naming its manifest, before anything is mounted."""
    export = _fixture_export(tmp_path / "export", manifest=_BAD_MANIFESTS[case])
    with pytest.raises(SystemExit) as exc:
        _assemble(tmp_path, monkeypatch, export)
    assert exc.value.code == 1
    assert "docs-dashboard/kedro-viz/manifest.json" in capsys.readouterr().err
    assert not (tmp_path / "site" / "dashboard").exists()


@pytest.mark.parametrize("case", sorted(_BAD_MANIFESTS))
def test_42_2_ac4_pages_check_refuses_a_malformed_mount(tmp_path: Path, capsys, case: str) -> None:
    """pages-check alone (the --check pass over a built artifact) names the mounted manifest."""
    assemble_pages = _load_assemble_pages()
    artifact = tmp_path / "site"
    artifact.mkdir()
    _write_shared_menu(artifact, _BASE)
    _write_mounted_export(artifact)
    assemble_pages._write_dossier_redirects(artifact)
    assemble_pages._ensure_kedro_viz_redirect(artifact)
    manifest = artifact / "dashboard" / "kedro-viz" / "manifest.json"
    bad = _BAD_MANIFESTS[case]
    if bad is None:
        manifest.unlink()
    else:
        manifest.write_text(bad if isinstance(bad, str) else json.dumps(bad), encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        assemble_pages.check(artifact, site_url=_SITE_URL)
    assert exc.value.code == 1
    assert "dashboard/kedro-viz/manifest.json" in capsys.readouterr().err


def test_42_2_ac4_extra_manifest_keys_change_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    export = _fixture_export(tmp_path / "export", manifest={**_MANIFEST, "producer_run": "12345", "new": [1]})
    artifact = _assemble(tmp_path, monkeypatch, export)
    _load_assemble_pages().check(artifact, site_url=_SITE_URL)
    assert _MANIFEST["export_commit"] in (artifact / "dashboard/index.html").read_text(encoding="utf-8")


def test_42_2_ac5_a_third_party_reference_on_the_pipelines_page_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    artifact = _assemble(tmp_path, monkeypatch, _fixture_export(tmp_path / "export"))
    page = artifact / "dashboard" / "index.html"
    page.write_text(
        page.read_text(encoding="utf-8").replace("</body>", '<script src="https://cdn.example/x.js"></script></body>'),
        encoding="utf-8",
    )
    with pytest.raises(SystemExit) as exc:
        _load_assemble_pages().check(artifact, site_url=_SITE_URL)
    assert exc.value.code == 1
    assert "cross-origin script: dashboard/index.html -> 'https://cdn.example/x.js'" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("target", "ok"),
    [
        ("../dashboard/kedro-viz/index.html", True),
        ("/local-recipes/dashboard/kedro-viz/", True),
        ("/dashboard/kedro-viz/", False),  # the stub live until 2026-10-15: off the project site
        ("https://example.com/dashboard/kedro-viz/", False),
    ],
)
def test_42_2_the_kedro_viz_redirect_stays_under_the_base_path(tmp_path: Path, capsys, target: str, ok: bool) -> None:
    assemble_pages = _load_assemble_pages()
    artifact = tmp_path / "site"
    artifact.mkdir()
    _write_shared_menu(artifact, _BASE)
    _write_mounted_export(artifact)
    assemble_pages._write_dossier_redirects(artifact)
    (artifact / "kedro-viz").mkdir()
    (artifact / "kedro-viz" / "index.html").write_text(
        f'<!doctype html><meta http-equiv="refresh" content="0;url={target}">', encoding="utf-8"
    )
    if ok:
        assemble_pages.check(artifact, site_url=_SITE_URL)
        return
    with pytest.raises(SystemExit) as exc:
        assemble_pages.check(artifact, site_url=_SITE_URL)
    assert exc.value.code == 1
    assert f"kedro-viz/index.html redirects to {target!r}" in capsys.readouterr().err
