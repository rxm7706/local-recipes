"""Story 27.2: unified GitHub Pages artifact (Starlight + herald + dashboard).

Story 42.2 (CAP-60): the Kedro-Viz mount is an artifact handoff that tolerates absence -- the
``test_42_2_*`` tests below build the real herald site around a fixture export, and around none.

Story 42.1 (CAP-60): the fleet board and guild status pages under ``/status/`` -- the ``test_42_1_*``
tests build the real herald site with ``pyforge.herald.status_pages`` on (a fixture input) and off.

Story 43.3 (CAP-61): with ``pyforge.herald.pages_one_generator`` on, the Astro build assembles the herald side
itself -- the ``test_43_3_*`` tests build it (where docs-site is installed, ``pages_astro``) and check the
frozen redirects, ``publicDir``, the search index, the small origin check and the CSP meta."""

from __future__ import annotations

import gzip
import importlib.util
import json
import re
import shutil
import subprocess
import sys
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
    assert board.count('href="/console/"') == 1  # the live view on Lane 1: another host, never resolved here
    assert not (artifact / "herald" / "status").exists()


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
    for name in ("kedro-viz", "vizro"):
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
        fonts = "../" * (rel.count("/") - 1) + "assets/fonts/fonts.css"
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
    assert len((DOCS_SITE / "scripts" / "origin_check.py").read_text(encoding="utf-8").splitlines()) < 40


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
    if on:
        write(artifact / "dashboard" / "kedro-viz" / "index.html", "<html>Astro served the export</html>")
    src = _dashboard_src(tmp_path, _fixture_export(tmp_path / "export"))
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
