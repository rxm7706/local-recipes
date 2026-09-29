"""Story 33.2: GET /stations/steward/ renders provision --list via PortalClient."""

from __future__ import annotations

import ast
import sys
from http import HTTPStatus
from pathlib import Path

import pytest
from pyforge.testing_kit import changed_paths_since

_HTTP_TOPLEVEL = frozenset({"httpx", "requests", "http.client"})
_CHROME_COPY_NAMES = ("base.html", "switcher.html", "theme.css")


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (candidate / ".claude" / "skills").is_dir():
            return candidate
    raise AssertionError("could not locate repo root (pixi.toml + .claude/skills)")


def _ensure_portal_import_path(root: Path) -> None:
    for rel in (
        "src/shared/packages/django-pyforge/src",
        "src/shared/packages/django-steward/src",
    ):
        path = str(root / rel)
        if path not in sys.path:
            sys.path.insert(0, path)


def _portal_py_files(root: Path) -> list[Path]:
    portal = root / "src/shared/packages/django-steward/src/django_steward_portal"
    return sorted(path for path in portal.rglob("*.py") if path.is_file())


def _raw_http_imports(tree: ast.AST) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if (
                    top in _HTTP_TOPLEVEL
                    or alias.name in _HTTP_TOPLEVEL
                    or alias.name.startswith("http.client")
                    or alias.name == "urllib.request"
                ):
                    found.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            top = module.split(".")[0]
            if (
                top in _HTTP_TOPLEVEL
                or module in _HTTP_TOPLEVEL
                or module.startswith(("urllib.request", "http.client"))
            ):
                found.append(f"from {module} import ...")
            from_urllib = any(alias.name == "request" for alias in node.names)
            if module == "urllib" and from_urllib:
                found.append("from urllib import request")
    return found


def _imported_roots(tree: ast.AST) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def test_portal_home_uses_portal_client_only():
    root = _repo_root()
    views = (root / "src/shared/packages/django-steward/src/django_steward_portal/views.py").read_text(encoding="utf-8")
    tree = ast.parse(views)
    assert "PortalClient" in views
    assert "provision_list" in views
    assert "pyforge" not in _imported_roots(tree)
    assert not _raw_http_imports(tree)


def test_django_steward_has_no_raw_http():
    root = _repo_root()
    offenders: list[str] = []
    scanned = [
        *_portal_py_files(root),
        root / "src/shared/packages/django-pyforge/src/django_pyforge/assertion/client.py",
    ]
    for path in scanned:
        hits = _raw_http_imports(ast.parse(path.read_text(encoding="utf-8")))
        if hits:
            offenders.append(f"{path}: {hits}")
    assert offenders == []


def test_django_steward_has_no_chrome_copy():
    root = _repo_root()
    portal = root / "src/shared/packages/django-steward/src/django_steward_portal"
    offenders = [
        str(path.relative_to(root))
        for path in portal.rglob("*")
        if path.is_file()
        and (
            path.name in _CHROME_COPY_NAMES
            or "/templates/django_pyforge/" in path.as_posix()
            or "/static/django_pyforge/" in path.as_posix()
        )
    ]
    assert offenders == []
    home = (portal / "templates/steward_portal/home.html").read_text(encoding="utf-8")
    assert '{% extends "django_pyforge/base.html" %}' in home
    assert "steward-provision-list" in home
    assert "hx-" in home


def test_story_does_not_add_pyforge_under_src_platform():
    # AST-based only (below) -- a bare substring check on the whole diff text
    # false-positives on a `pyforge.*` string used as a subprocess argument
    # (e.g. an import-oracle test proving a package resolves in a DIFFERENT
    # pixi env, `subprocess.run([..., "-c", "import pyforge.warden.cli"])`),
    # which is not a real import in this file's own AST at all. The AST walk
    # already gives the real enforcement pap:AD-2 needs.
    root = _repo_root()
    changed = changed_paths_since(root, pathspec="src/platform")
    offenders: list[str] = []
    for rel in changed:
        path = root / rel
        if path.suffix != ".py" or not path.is_file():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        if "pyforge" in _imported_roots(tree):
            offenders.append(rel)
    assert not offenders


def test_conda_forge_expert_not_replaced():
    root = _repo_root()
    cfe = root / ".claude/skills/conda-forge-expert"
    assert (cfe / "SKILL.md").is_file()
    assert not (cfe / "metadata.json").exists()
    assert not (cfe / "active").exists()


def _sample_pixi_toml() -> str:
    return '[environments]\nlinux = ["linux", "python"]\n'


def test_portal_client_provision_list_matches_duty(tmp_path):
    pytest.importorskip("django")
    root = _repo_root()
    _ensure_portal_import_path(root)
    from django_pyforge.assertion.client import PortalClient

    from pyforge.steward.provision import load_pixi_environments

    (tmp_path / "pixi.toml").write_text(_sample_pixi_toml(), encoding="utf-8")
    client = PortalClient()
    listed = client.provision_list(cwd=tmp_path)
    assert listed == load_pixi_environments(cwd=tmp_path)
    assert listed == {"linux": ("linux", "python")}


def test_portal_client_provision_list_default_cwd_uses_repo_root(monkeypatch, tmp_path):
    pytest.importorskip("django")
    root = _repo_root()
    _ensure_portal_import_path(root)
    from django_pyforge.assertion.client import PortalClient

    import pyforge.steward.provision as provision
    from pyforge.steward.provision import load_pixi_environments

    (tmp_path / "pixi.toml").write_text(_sample_pixi_toml(), encoding="utf-8")
    monkeypatch.setattr(provision, "repo_root", lambda: tmp_path)
    listed = PortalClient().provision_list()
    assert listed == load_pixi_environments(cwd=tmp_path)
    assert listed == {"linux": ("linux", "python")}


def test_authenticated_steward_home_renders_provision_inventory(monkeypatch):
    pytest.importorskip("django")
    from django.conf import settings

    if not settings.configured:
        settings.configure(
            SECRET_KEY="33-2-portal-slice",
            USE_TZ=True,
            STATIC_URL="/static/",
            INSTALLED_APPS=["django.contrib.staticfiles"],
            CACHES={
                "default": {
                    "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                    "LOCATION": "pyforge-steward-dashboard-test",
                },
            },
        )
    import django

    django.setup()

    root = _repo_root()
    _ensure_portal_import_path(root)
    from django.template import Context, Engine
    from django.test import RequestFactory
    from django_pyforge.assertion.client import PortalClient
    from django_pyforge.roles import prefixed_station
    from django_steward_portal import views

    captured: dict[str, object] = {}
    engine = Engine(
        dirs=[
            str(root / "src/shared/packages/django-steward/src/django_steward_portal/templates"),
            str(root / "src/shared/packages/django-pyforge/src/django_pyforge/templates"),
        ],
        libraries={"static": "django.templatetags.static"},
        builtins=["django.templatetags.static"],
    )

    def real_render(request, template, context=None, **_kwargs):
        captured["template"] = template
        captured["context"] = context or {}
        from django.http import HttpResponse

        html = engine.get_template(template).render(Context(captured["context"]))
        return HttpResponse(html)

    monkeypatch.setattr(views, "render", real_render)
    monkeypatch.setattr(
        PortalClient,
        "provision_list",
        lambda self, **_kwargs: {"linux": ("linux",), "pyforge-steward": ("pyforge-steward",)},
    )

    forbidden = RequestFactory().get("/stations/steward/")
    forbidden.idp_roles = [prefixed_station("warden")]
    assert views.chrome_home(forbidden).status_code == HTTPStatus.FORBIDDEN

    request = RequestFactory().get("/stations/steward/")
    request.idp_roles = [prefixed_station("steward")]
    response = views.chrome_home(request)
    assert response.status_code == HTTPStatus.OK
    body = response.content.decode()
    assert captured["template"] == "steward_portal/home.html"
    assert 'id="steward-provision-list"' in body
    assert "hx-target" in body
    assert 'data-environment="linux"' in body
    assert 'data-environment="pyforge-steward"' in body
    names = [row["name"] for row in captured["context"]["environments"]]
    assert names == ["linux", "pyforge-steward"]
