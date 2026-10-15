"""Story 27.2: unified GitHub Pages artifact (Starlight + herald + dashboard).

Story 42.2 (CAP-60): the Kedro-Viz mount is an artifact handoff that tolerates absence -- the
``test_42_2_*`` tests below build the real herald site around a fixture export, and around none.

Story 42.1 (CAP-60): the fleet board and guild status pages under ``/status/`` -- the ``test_42_1_*``
tests build the real herald site with ``pyforge.herald.status_pages`` on (a fixture input) and off.

Story 43.3 (CAP-61): with ``pyforge.herald.pages_one_generator`` on, the Astro build assembles the herald side
itself -- the ``test_43_3_*`` tests build it (where docs-site is installed, ``pages_astro``) and check the
frozen redirects, ``publicDir``, the search index, the small origin check and the CSP meta.

Story 43.4 (CAP-61): the ``test_43_4_*`` tests hold the herald pages and twins to one design system -- faces from
the @fontsource bundle under ``_astro/``, nothing under ``herald/assets/``, no inline theme."""

from __future__ import annotations

import base64
import gzip
import hashlib
import html
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from functools import partial
from pathlib import Path

import pytest
from pages_astro import (
    DOCS_SITE,
    NODE,
    REPO_ROOT,
    astro_build,
    fixture_tree,
    load_build,
    needs_astro,
    needs_node,
    write,
)
from pyforge.testing_kit import make_flag_provider_fixture
from pyforge.testing_kit.flags import flag_states


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


#: Story 42.1: with pyforge.herald.status_pages on, the one nav list gains Status after Decks.
_STATUS_ENTRY = ("Status", "status/", "../status/index.html")


def _menu(kedro_viz: bool, status: bool = False) -> list[tuple[str, str, str]]:
    menu = [entry for entry in _SHARED_MENU if kedro_viz or entry[0] != "Kedro-Viz"]
    if status:
        menu.insert(5, _STATUS_ENTRY)
    return menu


def _write_docs_pages(artifact: Path, base: str, *, kedro_viz: bool = True, status: bool = False) -> None:
    """The docs root and 404 with the top menu and the Herald sidebar links, as Starlight renders them."""
    menu = _menu(kedro_viz, status)
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
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    export: Path | None,
    *,
    empty_input: bool = False,
    status: bool = False,
    fleet_status: Path | None = None,
) -> Path:
    """pages-build around a synthetic docs shelf: the real herald build, the real mount and redirects.

    ``status`` sets pyforge.herald.status_pages (``PYFORGE_STATUS_PAGES``); ``fleet_status`` is the
    fleet board's build input (Story 42.1)."""
    monkeypatch.setenv("PYFORGE_PAGES_ONE_GENERATOR", "0")
    monkeypatch.setenv("PYFORGE_STATUS_PAGES", "1" if status else "0")
    assemble_pages = _load_assemble_pages()
    artifact = tmp_path / "site"
    artifact.mkdir()
    _write_docs_pages(artifact, _BASE, kedro_viz=export is not None, status=status)
    assemble_pages.assemble(
        artifact,
        repo_root=_repo_root(),
        dashboard_src=_dashboard_src(tmp_path, export, empty_input=empty_input),
        skip_docs_site_build=True,
        site_url=_SITE_URL,
        fleet_status=fleet_status,
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


# --- Story 42.1 (CAP-60): the fleet board and guild status pages render at build -----------------

_FLEET_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "fleet-status-2026-10-14.json"
_STATUS_LABELS = ["Docs", "Overview", "Dossier", "Infographics", "Decks", "Status"]


def test_42_1_ac6_the_flag_on_artifact_passes_pages_check(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    artifact = _assemble(tmp_path, monkeypatch, None, status=True, fleet_status=_FLEET_FIXTURE)
    assemble_pages = _load_assemble_pages()
    assemble_pages.check(artifact, site_url=_SITE_URL, fleet_status=_FLEET_FIXTURE)

    for page in ("status/index.html", "status/ci/index.html"):
        assert (artifact / page).is_file(), page
    # Every docs page and every herald shell page, the two status pages among them, carries Status.
    for page in (
        "index.html",
        "herald/index.html",
        "herald/decks/index.html",
        "status/index.html",
        "status/ci/index.html",
    ):
        assert _menu_labels(artifact / page) == _STATUS_LABELS, page
    board = (artifact / "status/index.html").read_text(encoding="utf-8")
    # site.yml's lane1.href is root-absolute (/console/) until the operator names Lane 1's URL; on the
    # Pages origin it would 404, so neither status page links it (42.1's re-review).
    assert "/console/" not in board
    assert not (artifact / "herald" / "status").exists()


def test_42_1_a_root_absolute_lane1_link_on_a_status_page_fails_pages_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """The assembler exempts the Lane 1 href only when it is an absolute URL: a ``/console/`` link put
    back on a status page resolves on the Pages origin and fails as a broken link."""
    artifact = _assemble(tmp_path, monkeypatch, None, status=True, fleet_status=_FLEET_FIXTURE)
    page = artifact / "status" / "index.html"
    page.write_text(
        page.read_text(encoding="utf-8").replace("</h1>", '</h1><a href="/console/">Live view on Lane 1</a>', 1),
        encoding="utf-8",
    )
    with pytest.raises(SystemExit) as exc:
        _load_assemble_pages().check(artifact, site_url=_SITE_URL, fleet_status=_FLEET_FIXTURE)
    assert exc.value.code == 1
    assert "status/index.html -> '/console/'" in capsys.readouterr().err


def test_42_1_an_absolute_lane1_url_on_the_status_pages_passes_pages_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The link the status pages carry once ``lane1.href`` names another host (rendered by
    ``status_pages.lane1_link``; the unit test renders it) passes ``pages-check``: a navigation link to
    another origin loads nothing (AD-21), and the href check never resolves it in the artifact."""
    lane1 = "https://lane1.example.internal/console/"
    artifact = _assemble(tmp_path, monkeypatch, None, status=True, fleet_status=_FLEET_FIXTURE)
    for rel in ("status/index.html", "status/ci/index.html"):
        page = artifact / rel
        page.write_text(
            page.read_text(encoding="utf-8").replace(
                "</time>", f'</time> &middot; <a href="{lane1}">Live view on Lane 1</a>', 1
            ),
            encoding="utf-8",
        )
        assert page.read_text(encoding="utf-8").count(f'href="{lane1}"') == 1, rel
    _load_assemble_pages().check(artifact, site_url=_SITE_URL, fleet_status=_FLEET_FIXTURE)


def test_42_1_ac6_a_status_page_without_its_menu_fails_pages_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    artifact = _assemble(tmp_path, monkeypatch, None, status=True, fleet_status=_FLEET_FIXTURE)
    page = artifact / "status" / "ci" / "index.html"
    page.write_text(page.read_text(encoding="utf-8").replace(">Status</a>", ">State</a>"), encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        _load_assemble_pages().check(artifact, site_url=_SITE_URL, fleet_status=_FLEET_FIXTURE)
    assert exc.value.code == 1
    assert "shared menu on status/ci/index.html" in capsys.readouterr().err


def _bad_fleet(tmp_path: Path, case: str) -> Path:
    path = tmp_path / "inputs" / "fleet-status.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    if case == "absent":
        return path
    if case == "not-json":
        path.write_text("{stations: [", encoding="utf-8")
        return path
    payload = json.loads(_FLEET_FIXTURE.read_text(encoding="utf-8"))
    if case == "no-stations":
        del payload["stations"]
    elif case == "stations-not-a-list":
        payload["stations"] = {}
    else:
        del payload["stations"][3][case.removeprefix("station-without-")]
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


_BAD_FLEET_CASES = {
    "absent": "fleet-status input missing",
    "not-json": "not valid JSON",
    "no-stations": "missing stations",
    "stations-not-a-list": "stations is not a list",
    "station-without-done": "station 3 (pyforge-marshal) missing done",
    "station-without-total": "station 3 (pyforge-marshal) missing total",
}


@pytest.mark.parametrize("case", sorted(_BAD_FLEET_CASES))
def test_42_1_ac5_pages_build_refuses_the_input_before_mounting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys, case: str
) -> None:
    fleet = _bad_fleet(tmp_path, case)
    with pytest.raises(SystemExit) as exc:
        _assemble(tmp_path, monkeypatch, None, status=True, fleet_status=fleet)
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert f"assemble_pages: {fleet}: {_BAD_FLEET_CASES[case]}" in err
    for mount in ("herald", "status", "dashboard"):
        assert not (tmp_path / "site" / mount).exists(), mount


def test_42_1_ac5_pages_check_alone_refuses_the_input(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    artifact = _assemble(tmp_path, monkeypatch, None, status=True, fleet_status=_FLEET_FIXTURE)
    fleet = _bad_fleet(tmp_path, "station-without-total")
    with pytest.raises(SystemExit) as exc:
        _load_assemble_pages().check(artifact, site_url=_SITE_URL, fleet_status=fleet)
    assert exc.value.code == 1
    assert f"{fleet}: station 3 (pyforge-marshal) missing total" in capsys.readouterr().err


@pytest.mark.parametrize("case", ["absent", "not-json", "valid"])
def test_42_1_ac7_flag_off_writes_no_status_path_and_opens_no_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    fleet = _FLEET_FIXTURE if case == "valid" else _bad_fleet(tmp_path, case)
    artifact = _assemble(tmp_path, monkeypatch, None, status=False, fleet_status=fleet)
    _load_assemble_pages().check(artifact, site_url=_SITE_URL, fleet_status=fleet)
    assert not (artifact / "status").exists()
    for page in ("index.html", "herald/index.html", "herald/dossier/index.html"):
        assert "Status" not in _menu_labels(artifact / page), page
    assert [raw for _, raw in _hrefs(artifact) if "status/" in raw] == []


def test_42_1_ac7_a_status_path_with_the_flag_off_fails_pages_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    artifact = _assemble(tmp_path, monkeypatch, None, status=False)
    (artifact / "status").mkdir()
    (artifact / "status" / "index.html").write_text("<html></html>", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        _load_assemble_pages().check(artifact, site_url=_SITE_URL)
    assert exc.value.code == 1
    assert "status/ exists in the artifact but pyforge.herald.status_pages is off" in capsys.readouterr().err


def test_42_1_the_status_mount_refuses_a_collision(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYFORGE_STATUS_PAGES", "1")
    monkeypatch.setenv("PYFORGE_PAGES_ONE_GENERATOR", "0")
    artifact = tmp_path / "site"
    (artifact / "status").mkdir(parents=True)
    with pytest.raises(SystemExit) as exc:
        _load_assemble_pages().assemble(
            artifact,
            repo_root=_repo_root(),
            dashboard_src=_dashboard_src(tmp_path, None),
            skip_docs_site_build=True,
            skip_herald_build=True,
            site_url=_SITE_URL,
            fleet_status=_FLEET_FIXTURE,
        )
    assert exc.value.code == 1


# --- Story 43.3: Astro assembles the artifact -------------------------------------------------------------

_FLAG = "pyforge.herald.pages_one_generator"
flag_provider = make_flag_provider_fixture()
_REDIRECTS = json.loads((DOCS_SITE / "redirects.json").read_text(encoding="utf-8"))


def _astro_artifact(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, root: Path | None = None) -> Path:
    """The flag-on artifact as the assembler leaves it: Astro's build, then the herald build's assets."""
    monkeypatch.setenv("PYFORGE_CI_SURFACES_TILE", "0")
    out = tmp_path / "site"
    done = astro_build(out, flag=True, root=root)
    assert done.returncode == 0, done.stdout[-3000:] + done.stderr[-3000:]
    build = load_build("docsite_build_43_3")
    build.CONTENT = (root or REPO_ROOT) / "docsite" / "content"
    build.build(out / "herald", root or REPO_ROOT, one_generator=True, status_pages=False)
    return out


def _origin_check():
    scripts = str(DOCS_SITE / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    import origin_check

    return origin_check


@needs_astro
def test_43_3_ac1_ac5_the_built_artifact(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    """AC1: every legacy path of redirects.json is a redirect landing on its target. AC5: every herald page
    carries one CSP meta, and the small origin check finds nothing off the configured origin."""
    artifact = _astro_artifact(tmp_path, monkeypatch)
    legacy = _REDIRECTS["legacy"]
    assert len(legacy) == 44
    refresh = re.compile(r"""http-equiv=["']refresh["'][^>]*url=([^"']+)["']""")
    for source, target in legacy.items():
        stub = artifact / source.lstrip("/")
        assert stub.is_file(), f"{source}: no redirect page"
        match = refresh.search(stub.read_text(encoding="utf-8"))
        assert match, f"{source}: not a redirect page"
        landed = (stub.parent / match.group(1)).resolve()
        assert landed == (artifact / target.lstrip("/")).resolve() and landed.is_file(), f"{source}: lands nowhere"
    assemble_pages = _load_assemble_pages()
    assemble_pages._check_legacy_redirects(artifact)
    assemble_pages._check_csp(artifact)
    pages = [p for p in (artifact / "herald").rglob("*.html") if "twins" not in p.parts and "artifact" not in p.parts]
    assert len(pages) > 40
    for built in pages:
        assert built.read_text(encoding="utf-8").count('http-equiv="Content-Security-Policy"') == 1, built
    # Story 43.3's review: the CSP names no host -- each source a keyword, a hash or data: -- and the hash it gives the
    # preview handler is the sha256 of the handler as the gallery renders it
    gallery = (artifact / "herald" / "infographics" / "index.html").read_text(encoding="utf-8")
    csp = html.unescape(re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', gallery).group(1))
    for directive in csp.split(";"):
        for source in directive.split()[1:]:
            assert source in ("'self'", "'none'", "'unsafe-inline'", "'unsafe-hashes'", "data:") or re.fullmatch(
                r"'sha256-[A-Za-z0-9+/]+=*'", source
            ), f"CSP source {source!r} names a host"
    onload = html.unescape(re.search(r'onload="([^"]+)"', gallery).group(1))
    digest = base64.b64encode(hashlib.sha256(onload.encode("utf-8")).digest()).decode("ascii")
    assert f"'sha256-{digest}'" in csp
    origin_check = _origin_check()
    assert origin_check.findings(artifact, origin_check.site_origin("http://localhost:3000")) == []
    (artifact / "herald" / "artifact" / "dossier.html").unlink()
    with pytest.raises(SystemExit):
        assemble_pages._check_legacy_redirects(artifact)
    assert "legacy redirect /artifact/dossier.html does not land on" in capsys.readouterr().err


@needs_node
def test_43_3_ac2_a_page_at_a_legacy_path_fails_the_build(tmp_path: Path) -> None:
    """AC2: the redirect writer refuses a path the build already holds, naming it (AD-21 rule 1)."""
    write(tmp_path / "out" / "dossier" / "index.html", "<html>a page</html>")
    lib = json.dumps((DOCS_SITE / "src" / "lib" / "redirects.ts").as_uri())
    out, legacy = json.dumps(str(tmp_path / "out")), json.dumps(_REDIRECTS["legacy"])
    script = (
        f"import {{ writeLegacyRedirects }} from {lib};"
        f"try {{ writeLegacyRedirects({out}, {legacy}); }}"
        "catch (exc) { process.stdout.write(String(exc.message)); process.exit(3); }"
    )
    done = subprocess.run(
        [NODE or "node", "--experimental-strip-types", "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 3, done.stderr
    assert "dossier/index.html" in done.stdout and "one owner" in done.stdout
    assert not (tmp_path / "out" / "decks").exists()  # nothing written when one path is taken


@needs_astro
def test_43_3_ac3_public_dir_serves_the_twins_downloads_and_exports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC3: docs-site/public/ holds exactly the twins, the downloads and the exports, each the artifact's copy
    byte for byte; a download or an export is its source byte for byte, a twin its source with only the
    font-link vendoring (Story 43.2's ruling)."""
    root = fixture_tree(tmp_path / "tree", exports=True)
    artifact = _astro_artifact(tmp_path, monkeypatch, root)
    public = DOCS_SITE / "public"
    files = sorted(p.relative_to(public).as_posix() for p in public.rglob("*") if p.is_file())
    project, src = "presentations/{}/project/{}", "presentations/{}/src/{}"
    twins = {
        "herald/twins/infographics/beta-co.html": project.format("fx-beta", "Beta Infographic standalone.html"),
        "herald/twins/infographics/alpha.html": project.format("fx-alpha", "Alpha Infographic standalone.html"),
        "herald/twins/decks/fx-alpha/infographic-deck.html": project.format(
            "fx-alpha", "Alpha - Infographic Deck.dc.html"
        ),
        "herald/twins/decks/fx-alpha/executive-summary.html": project.format(
            "fx-alpha", "Alpha - Executive Summary.dc.html"
        ),
        "herald/twins/decks/fx-beta/infographic-deck.html": project.format(
            "fx-beta", "Beta - Infographic Deck.dc.html"
        ),
    }
    copies = {
        "herald/decks/fx-alpha/downloads/fx-alpha-deck-2026-01-01.pptx": src.format(
            "fx-alpha", "pptx/fx-alpha-deck-2026-01-01.pptx"
        ),
        "herald/decks/fx-alpha/downloads/fx-alpha-deck-2026-01-01.md": src.format(
            "fx-alpha", "marp/fx-alpha-deck-2026-01-01.md"
        ),
        "herald/decks/fx-alpha/downloads/fx-alpha-narration-2026-01-02.md": src.format(
            "fx-alpha", "marp/fx-alpha-narration-2026-01-02.md"
        ),
        "herald/decks/fx-beta/downloads/fx-beta-2026-02-02.md": src.format("fx-beta", "marp/fx-beta-2026-02-02.md"),
    }
    for name in (
        "kedro-viz",
        "vizro",
        "fleet-board",
    ):  # the review: every entry of docs/dashboard/, not the exports only
        source = root / "docs" / "dashboard" / name
        for path in source.rglob("*"):
            if path.is_file():
                rel = path.relative_to(source).as_posix()
                copies[f"dashboard/{name}/{rel}"] = f"docs/dashboard/{name}/{rel}"
    assert files == sorted([*twins, *copies]), "docs-site/public/ holds a file the population script did not write"
    for rel in files:
        assert (artifact / rel).read_bytes() == (public / rel).read_bytes(), f"{rel}: the artifact's copy differs"
    for rel, source in copies.items():
        assert (public / rel).read_bytes() == (root / source).read_bytes(), f"{rel} is not {source}"
    build = load_build("docsite_build_43_3_ac3")
    for rel, source in twins.items():
        fonts = "../" * (rel.count("/") - 1) + "fonts.css"  # Story 43.4: the @fontsource faces
        want = build.rewrite_google_font_links((root / source).read_text(encoding="utf-8"), fonts).encode("utf-8")
        assert (public / rel).read_bytes() == want, f"{rel} is not {source} with its font links vendored"
    assert not (artifact / "dashboard" / "README.md").exists()


@needs_astro
def test_43_3_ac4_search_holds_a_dossier_page_and_a_family_page(tmp_path: Path) -> None:
    """AC4: the one Pagefind index holds the dossier (a section title: one herald hit) and each family page
    (its slug: one family-page hit)."""
    out = tmp_path / "site"
    done = astro_build(out, flag=True)
    assert done.returncode == 0, done.stderr[-3000:]
    fragments = []
    for path in (out / "pagefind" / "fragment").glob("*.pf_fragment"):
        raw = gzip.decompress(path.read_bytes())
        fragments.append(json.loads(raw[len(b"pagefind_dcd") :]))
    dossier = [f["url"] for f in fragments if "/herald/" in f["url"] and "Cross-fleet synthesis" in f["content"]]
    assert len(dossier) == 1 and dossier[0].endswith("/herald/dossier/"), dossier
    family = [f["url"] for f in fragments if "/herald/decks/" in f["url"] and "pyforge-herald" in f["content"]]
    assert len(family) == 1 and family[0].endswith("/herald/decks/pyforge-herald/"), family


def test_43_3_ac5_the_origin_check_is_small() -> None:
    """AC5's "under 40 lines" held until the second review (2026-10-15): reading the page with ``html.parser`` -- so
    attribute values decode, code samples load nothing and no attribute hides a later one -- with every line within
    120 columns takes 64 (the 43.3 change log; Story 43.7 measures the bespoke-Python budget). It does not grow."""
    assert len((DOCS_SITE / "scripts" / "origin_check.py").read_text(encoding="utf-8").splitlines()) <= 64


#: Story 31.1's non-loading snippets (``test_pages_site_url.py``), and an Expressive Code copy button's ``data-code``
#: naming an absolute fetch and @import -- text and attributes that load nothing.
_NON_LOADING = [
    '<a href="https://docs.python.org/3/">Python docs</a>',
    '<a href="https://github.com/rxm7706/local-recipes">repo</a>',
    '<area href="https://docs.python.org/3/" alt="docs">',
    '<link rel="canonical" href="https://docs.python.org/3/">',
    '<link rel="alternate" type="application/rss+xml" href="https://docs.python.org/3/feed.xml">',
    '<meta property="og:image" content="https://docs.python.org/3/og.png">',
    "<pre><code>fetch(&quot;https://platform.example/api&quot;)</code></pre>",
    '<div class="expressive-code"><button data-code="fetch(&#x22;https://api.example.com/x&#x22;)&#x7f;'
    '@import url(&#x27;https://fonts.googleapis.com/css2&#x27;);">Copy</button></div>',
    '<p><code>fetch("https://platform.example/api")</code></p>',
    "<script>let ready = true;</script><p>fetch(&quot;https://platform.example/api&quot;)</p>",
]


@pytest.mark.parametrize("snippet", _NON_LOADING)
def test_43_3_the_flag_on_origin_check_passes_what_loads_nothing(tmp_path: Path, snippet: str) -> None:
    """Story 43.3's second review: the flag-on check reads loads from loading attributes and from code a browser runs
    (script and style bodies, style attributes, .css and .js files), never from text or a data attribute, so a docs
    code sample or a copy button's ``data-code`` is not a load -- as the flag-off scanner already judged."""
    write(tmp_path / "how-to" / "x" / "index.html", f"<html><body>{snippet}</body></html>")
    _load_assemble_pages()._check_origins(tmp_path, _SITE_URL)


@pytest.mark.parametrize(
    ("rel", "body", "finding"),
    [
        (
            "herald/twins/infographics/x.html",
            '<link href="https://fonts.googleapis.com/css2?family=Archivo" rel="stylesheet">',
            "fonts.googleapis.com",
        ),
        ("herald/dossier/index.html", '<script src="https://cdn.example.com/a.js"></script>', "cdn.example.com"),
        ("dashboard/vizro/estate/index.html", '<img src="//cdn.plot.ly/x.png">', "cdn.plot.ly"),
        ("herald/assets/site.css", "@import url('https://fonts.googleapis.com/css2');", "fonts.googleapis.com"),
        ("_astro/app.js", 'fetch("https://api.example.com/x")', "api.example.com"),
        ("_astro/map.js", "icon.src = `https://cdn.jsdelivr.net/npm/maki/${p}.svg`", "cdn.jsdelivr.net"),
        # Story 43.3's review: each hole the old scanner caught and the first origin check missed, and two crashes
        ("_astro/xhr.js", 'x.open("GET", "https://api.example.com/x")', "api.example.com"),
        ("herald/index.html", '<svg><image href="https://img.example.com/i.png"/></svg>', "img.example.com"),
        ("herald/index.html", '<svg><image xlink:href="https://img.example.com/i.png"/></svg>', "img.example.com"),
        (
            "herald/index.html",
            '<img src="https://rxm7706.github.io/a.png" srcset="https://img.example.com/b.png 2x">',
            "img.example.com",
        ),
        (
            "herald/index.html",
            '<video poster="https://rxm7706.github.io/p.png" src="https://media.example.com/v.mp4"></video>',
            "media.example.com",
        ),
        (
            "herald/index.html",
            '<img srcset="https://rxm7706.github.io/a.png 1x, https://img.example.com/b.png 2x">',
            "img.example.com",
        ),
        ("herald/index.html", '<img src="https&#58;//img.example.com/a.png">', "img.example.com"),
        ("herald/index.html", '<script>fetch("https:\\/\\/api.example.com\\/x")</script>', "api.example.com"),
        ("herald/index.html", '<img/src="https://img.example.com/a.png">', "img.example.com"),
        ("herald/index.html", '<link rel="prerender" href="https://next.example.com/">', "next.example.com"),
        ("herald/index.html", '<img alt="a&gt;b" src="https://img.example.com/a.png">', "img.example.com"),
        ("herald/index.html", '<img src="https://[img.example.com/a.png">', "https://[img.example.com/a.png"),
        ("herald/index.html", '<img src="https://img.example.com:abc/a.png">', "img.example.com:abc"),
        ("herald/index.html", """<img data-x='a src="' src="https://img.example.com/x.png">""", "img.example.com"),
        ("herald/index.html", """<img alt=don't src="https://img.example.com/x.png">""", "img.example.com"),
        (
            "herald/index.html",
            '<div style="background:url(&quot;https://img.example.com/b.png&quot;)">',
            "img.example.com",
        ),
    ],
    ids=[
        "twin-font-link",
        "script",
        "protocol-relative",
        "css-import",
        "fetch",
        "dynamic-src",
        "xhr-open",
        "svg-image-href",
        "svg-image-xlink-href",
        "second-attribute",
        "poster-then-src",
        "second-srcset-candidate",
        "entity-encoded",
        "js-escaped-slashes",
        "img-slash-src",
        "rel-prerender",
        "gt-in-an-earlier-attribute",
        "malformed-host",
        "malformed-port",
        "quote-in-an-earlier-attribute",
        "apostrophe-in-an-unquoted-value",
        "style-attribute",
    ],
)
def test_43_3_ac5_pages_check_names_a_planted_load(tmp_path: Path, capsys, rel: str, body: str, finding: str) -> None:
    """A load from another origin anywhere outside the vendored paths exits 1 naming the file and the URL."""
    write(tmp_path / rel, f"<html><head>{body}</head></html>" if rel.endswith(".html") else body)
    write(tmp_path / "about" / "index.html", '<a href="https://github.com/rxm7706/local-recipes">a link</a>')
    with pytest.raises(SystemExit) as exc:
        _load_assemble_pages()._check_origins(tmp_path, _SITE_URL)
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert rel in err and finding in err
    assert "about/index.html" not in err  # a link is navigation, not a load


def test_43_3_ac5_the_vendored_bundles_are_exempt_by_name(tmp_path: Path, capsys) -> None:
    """The Kedro-Viz root and plotly.js -- the file, never the Vizro tree -- keep their own references."""
    write(tmp_path / "dashboard/kedro-viz/index.html", '<script src="https://cdn.example.com/kv.js"></script>')
    write(tmp_path / "dashboard/vizro/assets/plotly.min.js", 'fetch("https://cdn.plot.ly/un/world_110m.json")')
    assemble_pages = _load_assemble_pages()
    assemble_pages._check_origins(tmp_path, _SITE_URL)
    out = capsys.readouterr().out
    assert "exempt vendored root dashboard/kedro-viz/" in out
    assert "exempt vendored file dashboard/vizro/assets/plotly.min.js" in out
    write(tmp_path / "dashboard/vizro/assets/other.js", 'fetch("https://cdn.plot.ly/un/world_110m.json")')
    with pytest.raises(SystemExit):
        assemble_pages._check_origins(tmp_path, _SITE_URL)
    assert "dashboard/vizro/assets/other.js" in capsys.readouterr().err


@pytest.mark.parametrize(
    "rel",
    [
        "dashboard/vizro/assets/plotly.min.js.mjs",
        "dashboard/vizro/assets/plotly.min.js/x.js",
        "dashboard/vizro/assets/Plotly.min.js",
    ],
)
def test_43_3_ac5_a_sibling_of_the_exempt_file_is_judged(tmp_path: Path, capsys, rel: str) -> None:
    """Story 43.3's review: the exemption names one file exactly -- a path sharing its prefix, or its name in another
    case, is judged like any other."""
    write(tmp_path / rel, 'fetch("https://cdn.plot.ly/un/world_110m.json")')
    with pytest.raises(SystemExit):
        _load_assemble_pages()._check_origins(tmp_path, _SITE_URL)
    assert f"{rel}: loads 'https://cdn.plot.ly/un/world_110m.json'" in capsys.readouterr().err


def test_43_3_ac5_the_second_host_refuses_a_link_to_the_public_host(tmp_path: Path, capsys) -> None:
    write(tmp_path / "index.html", f'<a href="{_SITE_URL}/how-to/">how-to</a>')
    with pytest.raises(SystemExit):
        _load_assemble_pages()._check_origins(tmp_path, "https://pages.example.test/local-recipes")
    assert "on the other host https://rxm7706.github.io" in capsys.readouterr().err


def test_43_3_ac5_every_herald_page_carries_one_csp(tmp_path: Path, capsys) -> None:
    csp = '<meta http-equiv="Content-Security-Policy" content="default-src \'self\'">'
    write(tmp_path / "herald/index.html", f"<html><head>{csp}</head></html>")
    write(tmp_path / "herald/artifact/dossier.html", "<div>the artifact build, no head</div>")
    write(tmp_path / "herald/twins/infographics/x.html", "<html>a twin</html>")
    assemble_pages = _load_assemble_pages()
    assemble_pages._check_csp(tmp_path)
    write(tmp_path / "herald/decks/index.html", "<html><head></head></html>")
    with pytest.raises(SystemExit):
        assemble_pages._check_csp(tmp_path)
    assert "herald/decks/index.html carries 0 Content-Security-Policy meta(s)" in capsys.readouterr().err


@pytest.mark.parametrize("case", ["no-index", "no-manifest", "bad-manifest", "absent", "empty", "good"])
def test_43_3_the_vizro_mount_is_judged_when_present(tmp_path: Path, capsys, case: str) -> None:
    mount = tmp_path / "dashboard" / "vizro"
    if case != "absent":
        mount.mkdir(parents=True)
    if case in ("no-manifest", "bad-manifest", "good"):
        write(mount / "index.html", "<html>boards</html>")
    if case in ("no-index", "good"):
        write(mount / "manifest.json", "{}")
    if case == "bad-manifest":
        write(mount / "manifest.json", "[]")
    if case in ("absent", "empty", "good"):
        _load_assemble_pages()._check_vizro_mount(tmp_path)
        return
    with pytest.raises(SystemExit):
        _load_assemble_pages()._check_vizro_mount(tmp_path)
    assert "dashboard/vizro/ lacks index.html or a manifest.json object" in capsys.readouterr().err


@flag_states(_FLAG)
def test_43_3_the_assembler_hands_mounts_and_redirects_to_astro(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, flag_provider: dict[str, bool]
) -> None:
    """Off, the assembler writes the 44 legacy stubs and copies the dashboard input, as before; on, it writes
    neither -- the Astro build does, from docs-site/redirects.json and docs-site/public/ -- and refuses no
    mount Astro already holds."""
    on = flag_provider[_FLAG]
    monkeypatch.setenv("PYFORGE_PAGES_ONE_GENERATOR", "1" if on else "0")
    monkeypatch.setenv("PYFORGE_STATUS_PAGES", "0")
    monkeypatch.setenv("PYFORGE_CI_SURFACES_TILE", "0")
    artifact = tmp_path / "site"
    artifact.mkdir()
    export = _fixture_export(tmp_path / "export")
    if on:  # Astro served the export from docs-site/public/; the assembler judges what it mounted
        shutil.copytree(export, artifact / "dashboard" / "kedro-viz")
        write(artifact / "dashboard" / "kedro-viz" / "index.html", "<html>Astro served the export</html>")
    src = _dashboard_src(tmp_path, export)
    _load_assemble_pages().assemble(
        artifact, repo_root=_repo_root(), dashboard_src=src, skip_docs_site_build=True, site_url=_SITE_URL
    )
    stubs = [source for source in _REDIRECTS["legacy"] if (artifact / source.lstrip("/")).is_file()]
    if not on:
        assert sorted(stubs) == sorted(_REDIRECTS["legacy"])
        assert (artifact / "dashboard" / "kedro-viz" / "manifest.json").is_file()
        return
    assert stubs == []
    served = (artifact / "dashboard" / "kedro-viz" / "index.html").read_text(encoding="utf-8")
    assert served == "<html>Astro served the export</html>"
    assert sorted(p.name for p in (artifact / "herald").iterdir()) == [".nojekyll", "artifact", "assets"]
    assert (artifact / "dashboard" / "index.html").is_file()  # herald's pipelines page, still Jinja's


def _board_input(tmp_path: Path) -> Path:
    """``docs/dashboard/`` with its README, the Kedro-Viz export, an empty ``vizro/`` and one steward board."""
    src = _dashboard_src(tmp_path, _fixture_export(tmp_path / "export"))
    (src / "vizro").mkdir()
    write(src / "fleet-board" / "index.html", "<html>a deploy-static board</html>")
    (src / "empty-board" / "assets").mkdir(parents=True)  # holds no file: mounts nothing (the second review)
    write(src / ".vizro-staging" / "index.html", "<html>a gitignored staging leftover</html>")  # a dot-entry
    return src


@pytest.mark.parametrize(
    ("served", "finding"),
    [
        (("kedro-viz", "fleet-board"), None),
        (("kedro-viz", "fleet-board", "stray"), "collision at dashboard/: ['stray'] not in"),
        (("kedro-viz",), "entries not mounted at dashboard/: ['fleet-board']"),
        (("kedro-viz", "fleet-board", "vizro"), "collision at dashboard/: ['vizro'] not in"),
    ],
    ids=["as-mounted", "another-writer", "board-not-mounted", "absent-export-served"],
)
def test_43_3_the_flag_on_dashboard_is_the_input_and_nothing_else(
    tmp_path: Path, capsys, served: tuple[str, ...], finding: str | None
) -> None:
    """Story 43.3's review (AD-21 rule 1): with the flag on, ``dashboard/`` holds exactly what the tracked
    ``docs/dashboard/`` mounts -- every entry but the README, an export only when present -- and Astro only warns on a
    path two writers share, so an entry from anywhere else is a collision and a missing board a missing mount."""
    src = _board_input(tmp_path)
    artifact = tmp_path / "site"
    for name in served:
        write(artifact / "dashboard" / name / "index.html", "<html>served</html>")
    assemble_pages = _load_assemble_pages()
    if finding is None:
        assemble_pages._check_astro_dashboard(src, artifact)
        return
    with pytest.raises(SystemExit) as exc:
        assemble_pages._check_astro_dashboard(src, artifact)
    assert exc.value.code == 1
    assert finding in capsys.readouterr().err


@pytest.mark.parametrize(("planted", "refused"), [("status/runs/index.html", False), ("status/index.html", True)])
def test_43_3_assemble_with_both_flags_takes_only_astros_runs_page_under_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys, planted: str, refused: bool
) -> None:
    """The merged collision loop (lanes A and B; 43.3's second review): with both flags on, ``status/`` may pre-exist
    only as Astro's ``status/runs/`` (Story 43.6), beside which the herald build adds the board; anything else there
    is another writer and exits 1 before any mount."""
    monkeypatch.setenv("PYFORGE_PAGES_ONE_GENERATOR", "1")
    monkeypatch.setenv("PYFORGE_STATUS_PAGES", "1")
    artifact = tmp_path / "site"
    write(artifact / planted, "<html>a page</html>")
    run = partial(
        _load_assemble_pages().assemble,
        artifact,
        repo_root=_repo_root(),
        dashboard_src=_dashboard_src(tmp_path, None),
        skip_docs_site_build=True,
        skip_herald_build=True,
        site_url=_SITE_URL,
        fleet_status=_FLEET_FIXTURE,
    )
    if not refused:
        run()
        return
    with pytest.raises(SystemExit) as exc:
        run()
    assert exc.value.code == 1
    assert "collision at status/" in capsys.readouterr().err


def test_43_3_assemble_refuses_a_dashboard_it_did_not_expect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """With the flag on the assembler takes ``dashboard/`` as Astro's only when it is the input's mount: a pre-existing
    file there that the input does not hold exits 1 before the herald build runs (Story 43.3's review)."""
    monkeypatch.setenv("PYFORGE_PAGES_ONE_GENERATOR", "1")
    monkeypatch.setenv("PYFORGE_STATUS_PAGES", "0")
    src = _dashboard_src(tmp_path, None)
    artifact = tmp_path / "site"
    write(artifact / "dashboard" / "leftover.html", "<html>an earlier writer</html>")
    with pytest.raises(SystemExit) as exc:
        _load_assemble_pages().assemble(
            artifact, repo_root=_repo_root(), dashboard_src=src, skip_docs_site_build=True, site_url=_SITE_URL
        )
    assert exc.value.code == 1
    assert "collision at dashboard/: ['leftover.html']" in capsys.readouterr().err
    assert not (artifact / "herald").exists()


@needs_node
def test_43_3_a_route_over_a_public_file_fails_the_build(tmp_path: Path) -> None:
    """Story 43.3's review (AD-21 rule 1): Astro 7 only warns when a route emits a path ``public/`` serves and keeps the
    public file; the build-end hook refuses it, naming each path, and passes when no route output is a public file."""
    lib = json.dumps((DOCS_SITE / "src" / "lib" / "redirects.ts").as_uri())
    out = tmp_path / "out"
    written = ["herald/twins/infographics/atlas.html", "dashboard/kedro-viz/index.html"]
    routes = {
        "/herald/twins/[x]": [(out / "herald/twins/infographics/atlas.html").as_uri()],
        "/herald": [(out / "herald/index.html").as_uri()],
    }
    script = (
        f"import {{ refusePublicCollisions }} from {lib};"
        f"const assets = new Map(Object.entries({json.dumps(routes)}).map(([k, v]) => [k, v.map((u) => new URL(u))]));"
        f"try {{ refusePublicCollisions({json.dumps(str(out))}, {json.dumps(written)}, assets); process.exit(0); }}"
        "catch (exc) { process.stdout.write(String(exc.message)); process.exit(3); }"
    )
    run = [NODE or "node", "--experimental-strip-types", "--input-type=module", "-e"]
    done = subprocess.run([*run, script], capture_output=True, text=True, check=False)
    assert done.returncode == 3, done.stderr
    assert "herald/twins/infographics/atlas.html" in done.stdout and "one owner" in done.stdout
    assert "dashboard/kedro-viz" not in done.stdout
    clean = script.replace(json.dumps(written), json.dumps(written[1:]))
    done = subprocess.run([*run, clean], capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stdout + done.stderr


def test_43_3_pages_check_lands_every_legacy_redirect(tmp_path: Path, capsys) -> None:
    """AC1 in CI: ``_check_legacy_redirects`` on a synthetic tree -- every frozen legacy path a stub landing on its
    target passes; a stub pointing elsewhere exits 1 naming it (the built-artifact test needs docs-site installed)."""
    assemble_pages = _load_assemble_pages()
    for source, target in _REDIRECTS["legacy"].items():
        stub, landing = tmp_path / source.lstrip("/"), tmp_path / target.lstrip("/")
        write(landing, "<html>the herald page</html>")
        write(stub, assemble_pages.redirect_html(assemble_pages._relative_url(stub, landing)))
    assemble_pages._check_legacy_redirects(tmp_path)
    source = sorted(_REDIRECTS["legacy"])[0]
    write(tmp_path / source.lstrip("/"), assemble_pages.redirect_html("nowhere.html"))
    with pytest.raises(SystemExit) as exc:
        assemble_pages._check_legacy_redirects(tmp_path)
    assert exc.value.code == 1
    assert f"legacy redirect {source} does not land on" in capsys.readouterr().err


# --- Story 43.2 (independent review): the one-writer gate, the twin and reader-page exemptions, the parity check --

_ASTRO_META = '<meta name="generator" content="Astro v7.3.2">'


def test_43_2_one_writer_with_the_flag_on_refuses_a_jinja_page(tmp_path: Path, capsys) -> None:
    write(tmp_path / "herald/index.html", f"<html><head>{_ASTRO_META}</head></html>")
    write(tmp_path / "herald/artifact/dossier.html", "<div>the artifact build: Jinja's in both states</div>")
    write(tmp_path / "herald/twins/infographics/x.html", "<html>a copy, not a page</html>")
    assemble_pages = _load_assemble_pages()
    assemble_pages._check_one_writer(tmp_path, one_generator=True)
    write(tmp_path / "herald/decks/index.html", "<html><head></head></html>")
    with pytest.raises(SystemExit) as exc:
        assemble_pages._check_one_writer(tmp_path, one_generator=True)
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "herald/decks/index.html was written by the Jinja build but pyforge.herald.pages_one_generator is on" in err


def test_43_2_one_writer_with_the_flag_off_refuses_an_astro_page(tmp_path: Path, capsys) -> None:
    write(tmp_path / "herald/index.html", "<html><head></head></html>")
    assemble_pages = _load_assemble_pages()
    assemble_pages._check_one_writer(tmp_path, one_generator=False)
    write(tmp_path / "herald/infographics/index.html", f"<html><head>{_ASTRO_META}</head></html>")
    with pytest.raises(SystemExit) as exc:
        assemble_pages._check_one_writer(tmp_path, one_generator=False)
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "herald/infographics/index.html was written by Astro but pyforge.herald.pages_one_generator is off" in err


def test_43_2_a_twin_is_no_page_but_its_loads_are_judged(tmp_path: Path, capsys) -> None:
    """A twin under /herald/twins/ gets no legacy redirect, carries no menu and is not link-walked, but the origin
    checks read it."""
    assemble_pages = _load_assemble_pages()
    twin = "herald/twins/infographics/x.html"
    write(tmp_path / twin, '<html><head><script src="./support.js"></script></head><a href="nowhere.html">x</a></html>')
    write(tmp_path / "herald/index.html", "<html></html>")
    assert [p.name for p in assemble_pages._iter_herald_html(tmp_path)] == ["index.html"]
    assemble_pages._write_dossier_redirects(tmp_path)
    assert not (tmp_path / "twins").exists()
    assert not assemble_pages._carries_the_menu(twin, "")
    assert not assemble_pages._should_check_page_links(twin, "")
    assemble_pages._check_href_resolution(tmp_path, site_url=_SITE_URL)  # the broken link in the twin is not walked
    write(tmp_path / twin, '<html><head><link rel="stylesheet" href="https://fonts.googleapis.com/css2"></head></html>')
    findings, _ = assemble_pages.cross_origin_findings(tmp_path, _SITE_URL)
    assert any(twin in line and "fonts.googleapis.com" in line for line in findings)
    with pytest.raises(SystemExit):
        assemble_pages._check_origins(tmp_path, _SITE_URL)
    assert twin in capsys.readouterr().err


@pytest.mark.parametrize("rel", ["herald/infographics/atlas.html", "herald/decks/pyforge-atlas/infographic-deck.html"])
def test_43_2_a_reader_page_carries_no_menu_and_only_astros_is_link_walked(rel: str) -> None:
    assemble_pages = _load_assemble_pages()
    assert not assemble_pages._carries_the_menu(rel, "<html></html>")
    assert not assemble_pages._should_check_page_links(rel, "<html><body>a Jinja back-barred export</body></html>")
    assert assemble_pages._should_check_page_links(rel, f"<html><head>{_ASTRO_META}</head></html>")


_TRACKED_TWIN = (
    b'<!DOCTYPE html>\n<html>\n<head>\n<meta charset="utf-8">\n'
    b'<link rel="preconnect" href="https://fonts.googleapis.com">\n'
    b'<link href="https://fonts.googleapis.com/css2?family=Archivo" rel="stylesheet">\n'
    b"<title>T</title>\n</head>\n<body><p>body</p></body>\n</html>\n"
)
_VENDORED_TWIN = (
    _TRACKED_TWIN.replace(b"<head>\n", b'<head>\n<link rel="stylesheet" href="../../fonts.css">\n\n', 1)
    .replace(b'<link rel="preconnect" href="https://fonts.googleapis.com">\n', b"")
    .replace(b'<link href="https://fonts.googleapis.com/css2?family=Archivo" rel="stylesheet">\n', b"")
)


@pytest.mark.parametrize(
    ("published", "needle"),
    [
        (_VENDORED_TWIN, None),
        (_VENDORED_TWIN.replace(b"<p>body</p>", b"<p>edited</p>"), "gained"),
        (_VENDORED_TWIN.replace(b"<title>T</title>\n", b""), "lost"),
        (_VENDORED_TWIN.replace(b"\n", b"\r\n"), "lost"),
        (_VENDORED_TWIN.replace(b"<head>\n", b'<head>\n<div class="ig-backbar"></div>\n', 1), "gained"),
        (
            _VENDORED_TWIN.replace(b"<head>\n", b'<head>\n<link rel="stylesheet" href="../../fonts.css">\n', 1),
            "vendored font links, not one",
        ),
        (_VENDORED_TWIN.replace(b"../../fonts.css", b"../../assets/fonts/fonts.css"), "gained"),
    ],
    ids=["vendoring-only", "edited-body", "dropped-title", "crlf", "back-bar", "two-links", "jinja-fonts"],
)
def test_43_2_the_twin_diff_allows_only_the_font_vendoring(published: bytes, needle: str | None) -> None:
    changes = _load_assemble_pages()._font_vendoring_only(published, _TRACKED_TWIN)
    if needle is None:
        assert changes == []
    else:
        assert changes and any(needle in change for change in changes), changes


@needs_astro
def test_43_2_pages_check_compares_the_astro_pages_with_the_jinja_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """The parity ``pages-check`` runs with the flag on: green on the tracked tree; a dropped download, a
    reordered gallery and an edited twin each exit 1 naming the page or file."""
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    artifact = _astro_artifact(tmp_path, monkeypatch)
    assemble_pages = _load_assemble_pages()
    assemble_pages._check_herald_parity(artifact)
    assert "the Astro herald pages match the Jinja path (10 families, 30 twins)" in capsys.readouterr().out

    family = artifact / "herald/decks/pyforge-herald/index.html"
    text = family.read_text(encoding="utf-8")
    family.write_text(text.replace('href="downloads/pyforge-herald-deck-2026-09-15.md"', 'href="x.md"'), "utf-8")
    gallery = artifact / "herald/infographics/index.html"
    cards = gallery.read_text(encoding="utf-8")
    gallery.write_text(cards.replace("<h3>Atlas</h3>", "<h3>Atlas!</h3>"), encoding="utf-8")
    twin = artifact / "herald/twins/infographics/herald.html"
    twin.write_bytes(twin.read_bytes().replace(b"</body>", b"<p>edited</p></body>", 1))
    with pytest.raises(SystemExit) as exc:
        assemble_pages._check_herald_parity(artifact)
    assert exc.value.code == 1
    err = capsys.readouterr().err
    assert "herald/decks/pyforge-herald/index.html: the links differ" in err
    assert "herald/infographics/index.html: the ordered (href, title) cards differ" in err
    assert "herald/twins/infographics/herald.html: gained" in err


# --- Story 43.4: fonts and theme come from one design system; its review: one theme contract across Pages --------

_FACES = '@font-face{font-family:IBM Plex Sans;src:url(/local-recipes/_astro/plex.woff2)format("woff2")}'


def _design_system_fixture(root: Path) -> Path:
    """A flag-on artifact in miniature: a bundled stylesheet and face, a herald page, a twin and a reader page."""
    write(root / "_astro" / "plex.woff2", b"wOF2")
    write(root / "_astro" / "herald.css", _FACES + ":root{--paper:var(--sl-color-black)}")
    write(root / "herald" / "fonts.css", _FACES)
    write(root / "herald" / "theme.css", _FACES + ":root{--sl-color-black:#f1f3ef}")
    write(root / "herald" / "assets" / "site.css", "body{}")  # the Jinja path's, still built with the flag on
    write(root / "herald" / "artifact" / "dossier.html", "<style>:root{--paper:#fff}</style>")  # Jinja's, exempt
    head = '<link rel="stylesheet" href="/local-recipes/_astro/herald.css"><script>/* theme */</script>'
    write(root / "herald" / "dossier" / "index.html", f'<html><head>{head}</head><body style="color:var(--ink)">')
    write(
        root / "herald" / "infographics" / "x.html",
        '<html><head><link rel="stylesheet" href="../theme.css"><style>html,body{margin:0}</style></head></html>',
    )
    write(
        root / "herald" / "twins" / "infographics" / "x.html",
        '<html><head><link rel="stylesheet" href="../../fonts.css"><style>:root{--brand:#e63}</style></head></html>',
    )  # a Design export's own theme
    return root


@pytest.mark.parametrize(
    ("rel", "text", "finding"),
    [
        (None, None, None),
        (
            "herald/index.html",
            '<html><head><link rel="stylesheet" href="assets/site.css"></head></html>',
            "herald/index.html links 'assets/site.css' under herald/assets/",
        ),
        (
            "herald/index.html",
            "<html><head><link rel=stylesheet href=assets/site.css></head></html>",
            "herald/index.html links 'assets/site.css' under herald/assets/",
        ),
        (
            "herald/fonts.css",
            "@font-face{font-family:Archivo;src:url(assets/fonts/archivo.woff2)}",
            "herald/twins/infographics/x.html loads a face '/local-recipes/herald/assets/fonts/archivo.woff2' under",
        ),
        (
            "_astro/herald.css",
            "@font-face{font-family:X;src:url(data:font/woff2;base64,AAAA)}",
            "herald/dossier/index.html loads a face 'data:font/woff2;base64,AAAA' that is not a file under _astro/",
        ),
        (
            "herald/decks/index.html",
            "<html><head><style>@font-face{font-family:X;src:url(../assets/fonts/x.woff2)}</style></head></html>",
            "herald/decks/index.html loads a face '../assets/fonts/x.woff2' under herald/assets/",
        ),
        (
            "herald/decks/index.html",
            "<html><head><style>@import url(../assets/site.css);</style></head></html>",
            "herald/decks/index.html imports '../assets/site.css' under herald/assets/",
        ),
        (
            "_astro/herald.css",
            "@import url(/local-recipes/_astro/more.css);",
            "herald/dossier/index.html loads a face '/local-recipes/herald/assets/fonts/y.woff2' under",
        ),
        (
            "herald/decks/index.html",
            "<html><head><style>:root[data-theme='dark']{--paper:#000}</style></head></html>",
            "herald/decks/index.html carries an inline theme",
        ),
    ],
    ids=[
        "one-design-system",
        "jinja-stylesheet",
        "jinja-stylesheet-unquoted",
        "vendored-face",
        "inline-face",
        "face-in-a-style-body",
        "import-in-a-style-body",
        "face-one-import-down",
        "inline-theme",
    ],
)
def test_43_4_pages_check_holds_the_herald_pages_to_one_design_system(
    tmp_path: Path, capsys, rel: str | None, text: str | None, finding: str | None
) -> None:
    """AC1, AC3, AC4 in ``pages-check`` (flag on): every face a herald page or twin loads -- from a sheet it links,
    quoted or not, a ``<style>`` of its own, or a sheet either imports -- is a file under ``_astro/``, nothing links or
    imports ``herald/assets/``, and no herald page carries an inline theme; a twin keeps its own."""
    root = _design_system_fixture(tmp_path)
    write(root / "_astro" / "more.css", "@font-face{font-family:Y;src:url(../herald/assets/fonts/y.woff2)}")
    assemble_pages = _load_assemble_pages()
    if rel is None:
        assemble_pages._check_one_design_system(root, _SITE_URL)
        return
    write(root / rel, text or "")
    with pytest.raises(SystemExit) as exc:
        assemble_pages._check_one_design_system(root, _SITE_URL)
    assert exc.value.code == 1
    assert finding in capsys.readouterr().err


def _top_level_rules(css: str) -> list[tuple[str, str]]:
    """``(selector, body)`` of each rule outside every at-rule (Starlight's own theme sits in ``@layer`` blocks)."""
    rules, i = [], 0
    while (j := css.find("{", i)) >= 0:
        head, depth, k = css[i:j].split(";")[-1].strip(), 1, j + 1
        while depth and k < len(css):
            depth += {"{": 1, "}": -1}.get(css[k], 0)
            k += 1
        if not head.startswith("@"):
            rules.append((head, css[j + 1 : k - 1]))
        i = k
    return rules


def _page_theme(artifact: Path, page: Path) -> dict[str, dict[str, str]]:
    """The site theme's variables -- each ``--sl-*`` an unlayered ``:root`` or ``[data-theme=dark]`` rule sets -- in
    the stylesheets ``page`` links, light and dark."""
    light: dict[str, str] = {}
    dark: dict[str, str] = {}
    for href in re.findall(r'<link rel="stylesheet" href="([^"]+)"', page.read_text(encoding="utf-8")):
        sheet = (artifact / href.lstrip("/")) if href.startswith("/") else (page.parent / href)
        for selector, body in _top_level_rules(sheet.read_text(encoding="utf-8")):
            values = dict(re.findall(r"(--sl-[\w-]+)\s*:\s*([^;]+)", body))
            if selector == ":root":
                light.update(values)
            elif selector in (":root[data-theme=dark]", ":root[data-theme='dark']"):
                dark.update(values)
    return {"light": light, "dark": {**light, **dark}}


@needs_astro
def test_43_4_ac1_ac3_ac4_the_built_pages_share_one_theme(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    """The theme contract on the built artifact (operator ruling 2026-10-15): a docs shelf page and a herald page
    resolve the same Starlight font, accent and gray values in both themes, from theme.css; the herald-only rules never
    reach the shelf. AC1: every face a herald page, reader page or twin loads is an @fontsource woff2 under ``_astro/``,
    and the five families are there. AC3: each herald page runs the theme script, allowed by the CSP, before its
    stylesheet, and carries no inline theme. AC4: no page references a ``.woff2`` under ``herald/assets/``."""
    monkeypatch.setenv("SITE_URL", "http://localhost:3000")
    artifact = _astro_artifact(tmp_path, monkeypatch)
    assemble_pages = _load_assemble_pages()
    assemble_pages._check_one_design_system(artifact, "http://localhost:3000")

    shelf, dossier = artifact / "how-to" / "index.html", artifact / "herald" / "dossier" / "index.html"
    docs_theme, herald_theme = _page_theme(artifact, shelf), _page_theme(artifact, dossier)
    for mode in ("light", "dark"):
        names = [n for n in docs_theme[mode] if n.startswith(("--sl-font", "--sl-color-accent", "--sl-color-gray"))]
        names += ["--sl-color-white", "--sl-color-black"]
        assert len(names) > 12
        assert {n: docs_theme[mode][n] for n in names} == {n: herald_theme[mode].get(n) for n in names}, mode
    assert (
        docs_theme["light"]["--sl-color-accent"] == "#b06a13" and docs_theme["dark"]["--sl-color-accent"] == "#dd9a3f"
    )
    assert docs_theme["light"]["--sl-font"].startswith('"IBM Plex Sans"')
    shelf_css = "".join(
        (artifact / href.lstrip("/")).read_text(encoding="utf-8")
        for href in re.findall(r'<link rel="stylesheet" href="([^"]+)"', shelf.read_text(encoding="utf-8"))
    )
    assert "_astro/herald." not in shelf.read_text(encoding="utf-8")
    for herald_only in (".station-mark", ".site-nav-inner", ".hero-eyebrow", "text-transform:uppercase"):
        assert herald_only not in shelf_css, f"{herald_only} reached the docs"
    assert "font-family:IBM Plex Sans" in shelf_css.replace('"', "")  # the faces the theme intends

    families: set[str] = set()
    sheets = [
        artifact / "herald" / "fonts.css",
        artifact / "herald" / "theme.css",
        *(artifact / "_astro").glob("*.css"),
    ]
    for sheet in sheets:
        for face in re.findall(r"@font-face\{([^}]*)\}", sheet.read_text(encoding="utf-8")):
            families.add(re.search(r"font-family:\s*['\"]?([^;'\"]+)", face).group(1))
            for url in re.findall(r"url\(([^)]+)\)", face):
                assert url.startswith("/_astro/") and url.endswith(".woff2"), (sheet.name, url)
                assert (artifact / url.lstrip("/")).is_file(), (sheet.name, url)
    assert families == {"Big Shoulders Display", "IBM Plex Sans", "IBM Plex Mono", "Archivo", "Archivo Expanded"}
    assert not list((artifact / "_astro").glob("*.woff"))

    shells = [
        artifact / "herald" / rel for rel in ("index.html", "dossier/index.html", "decks/pyforge-herald/index.html")
    ]
    reader = artifact / "herald/infographics/atlas.html"
    for page in [*shells, reader]:
        text = page.read_text(encoding="utf-8")
        script = re.search(r"<script>(.*?)</script>", text).group(1)
        assert "starlight-theme" in script, page
        digest = base64.b64encode(hashlib.sha256(script.encode("utf-8")).digest()).decode("ascii")
        assert f"'sha256-{digest}'" in text, f"{page}: the CSP does not allow the theme script"
        assert text.index(script) < text.index('rel="stylesheet"'), page
    for page in shells:
        text = page.read_text(encoding="utf-8")
        assert re.findall(r'<link rel="stylesheet" href="([^"]+)"', text) == [
            re.search(r'href="(/_astro/herald\.[^"]+\.css)"', text).group(1)
        ], page
    for page in (artifact / "herald").rglob("*.html"):
        if "artifact" not in page.relative_to(artifact).parts:
            assert not re.search(r"assets/[^\"']*\.woff2", page.read_text(encoding="utf-8")), page
    twin = (artifact / "herald/twins/infographics/atlas.html").read_text(encoding="utf-8")
    assert '<link rel="stylesheet" href="../../fonts.css">' in twin
    assert '<link rel="stylesheet" href="../theme.css">' in reader.read_text(encoding="utf-8")
    dossier.write_text(
        dossier.read_text(encoding="utf-8").replace("</head>", "<style>:root{--paper:#000}</style></head>"), "utf-8"
    )
    with pytest.raises(SystemExit):
        assemble_pages._check_one_design_system(artifact, "http://localhost:3000")
    assert "herald/dossier/index.html carries an inline theme" in capsys.readouterr().err
