"""Story 5.2 — first portal slice: one recall query via PortalClient."""

from __future__ import annotations

import ast
import importlib.util
import shutil
import sys
from http import HTTPStatus
from pathlib import Path

import pytest
from pyforge.testing_kit import changed_paths_since, diff_text_since

STATION = "scribe"
_HTTP_TOPLEVEL = frozenset({"httpx", "requests", "http.client"})
_CHROME_COPY = frozenset({"base.html", "switcher.html", "theme.css"})


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (candidate / "src" / "platform").is_dir():
            return candidate
    raise AssertionError("could not locate repo root")


def _portal_root(root: Path) -> Path:
    return root / "src" / "shared" / "packages" / f"django-{STATION}" / "src" / f"django_{STATION}_portal"


def _ensure_portal_import_path(root: Path) -> None:
    for rel in (
        "src/shared/packages/django-pyforge/src",
        f"src/shared/packages/django-{STATION}/src",
    ):
        path = str(root / rel)
        if path not in sys.path:
            sys.path.insert(0, path)


def _iter_py(tree: Path) -> list[Path]:
    return sorted(path for path in tree.rglob("*.py") if path.is_file())


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
            if module == "urllib" and any(alias.name == "request" for alias in node.names):
                found.append("from urllib import request")
            if module == "http" and any(alias.name == "client" for alias in node.names):
                found.append("from http import client")
    return found


def _pyforge_package_imports(tree: ast.AST) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(
                f"import {alias.name}"
                for alias in node.names
                if alias.name == "pyforge" or alias.name.startswith("pyforge.")
            )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "pyforge" or module.startswith("pyforge."):
                found.append(f"from {module} import ...")
    return found


def _load_submit_recall():
    path = _portal_root(_repo_root()) / "recall_submit.py"
    spec = importlib.util.spec_from_file_location("django_scribe_portal.recall_submit", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.submit_recall


def _load_client_fn(name: str):
    path = (
        _repo_root()
        / "src"
        / "shared"
        / "packages"
        / "django-pyforge"
        / "src"
        / "django_pyforge"
        / "assertion"
        / "client.py"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            ns: dict[str, object] = {"shutil": shutil}
            exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), ns)
            return ns[name]
    raise AssertionError(f"{name} not found")


def _load_parse_recall_cli():
    return _load_client_fn("parse_recall_cli")


def test_submit_recall_runs_portal_client_call_and_returns_cited_results() -> None:
    submit_recall = _load_submit_recall()
    seen: dict[str, object] = {}

    class _FakeClient:
        def call(
            self,
            station: str,
            job: str,
            payload: dict[str, object],
            *,
            sub: str,
            roles: list[str],
        ) -> dict[str, object]:
            seen["station"] = station
            seen["job"] = job
            seen["payload"] = payload
            seen["sub"] = sub
            seen["roles"] = roles
            return {
                "grounded": True,
                "text": "cited answer",
                "citation": "memory.md:12",
            }

    results = submit_recall(
        _FakeClient(),
        "what did we decide?",
        sub="alice",
        roles=["scribe"],
    )
    assert seen == {
        "station": "scribe",
        "job": "recall",
        "payload": {"query": "what did we decide?"},
        "sub": "alice",
        "roles": ["scribe"],
    }
    assert results["text"] == "cited answer"
    assert results["citation"] == "memory.md:12"
    results_html = (_portal_root(_repo_root()) / "templates" / "scribe_portal" / "results.html").read_text(
        encoding="utf-8"
    )
    rendered = results_html
    if results:
        rendered = rendered.replace("{{ results.text }}", str(results["text"]))
        rendered = rendered.replace("{{ results.citation }}", str(results["citation"]))
    assert "cited answer" in rendered
    assert "memory.md:12" in rendered
    assert 'id="scribe-recall-text"' in rendered
    assert 'id="scribe-recall-citation"' in rendered


def test_parse_recall_cli_extracts_citation() -> None:
    parse_recall_cli = _load_parse_recall_cli()
    cited = parse_recall_cli("the decision held\n[source: graph.json#n1]\n")
    assert cited == {
        "grounded": True,
        "text": "the decision held",
        "citation": "graph.json#n1",
    }
    empty = parse_recall_cli("")
    assert empty == {
        "grounded": False,
        "text": "no grounded answer found",
        "citation": None,
    }


def test_recall_cli_argv_mode_is_optional() -> None:
    recall_cli_argv = _load_client_fn("recall_cli_argv")
    bare = recall_cli_argv("what did we decide?")
    assert "--kind" not in bare
    assert "--mode" not in bare
    assert bare[-1] == "what did we decide?"
    planned = recall_cli_argv("what did we decide?", mode="planning")
    assert planned[-2:] == ["--mode", "planning"]
    assert "--kind" not in planned
    coded = recall_cli_argv("q", mode="code")
    assert coded[-2:] == ["--mode", "code"]


def test_chrome_home_post_renders_cited_recall_results() -> None:
    pytest.importorskip("django")
    from django.conf import settings

    if not settings.configured:
        settings.configure(
            SECRET_KEY="5-2-portal-slice",
            USE_TZ=True,
            STATIC_URL="/static/",
            INSTALLED_APPS=["django.contrib.staticfiles"],
        )
    import django

    django.setup()

    root = _repo_root()
    _ensure_portal_import_path(root)
    from django.template import Context, Engine
    from django.test import RequestFactory
    from django_pyforge.roles import prefixed_station
    from django_scribe_portal import views

    engine = Engine(
        dirs=[
            str(_portal_root(root) / "templates"),
            str(root / "src/shared/packages/django-pyforge/src/django_pyforge/templates"),
        ],
    )

    def real_render(request, template, context=None, **_kwargs):
        from django.http import HttpResponse

        html = engine.get_template(template).render(Context(context or {}))
        return HttpResponse(html)

    cited = {
        "grounded": True,
        "text": "cited answer",
        "citation": "memory.md:12",
    }

    def fake_submit(_client, query, *, sub, roles):
        assert query == "what did we decide?"
        assert sub
        assert roles
        return cited

    import django_scribe_portal.views as views_module

    original_render = views_module.render
    original_submit = views_module.submit_recall
    views_module.render = real_render
    views_module.submit_recall = fake_submit
    try:
        forbidden = RequestFactory().post("/stations/scribe/", {"query": "x"})
        forbidden.idp_roles = [prefixed_station("warden")]
        assert views.chrome_home(forbidden).status_code == HTTPStatus.FORBIDDEN

        request = RequestFactory().post(
            "/stations/scribe/",
            {"query": "what did we decide?"},
            HTTP_HX_REQUEST="true",
        )
        request.idp_roles = [prefixed_station("scribe")]
        response = views.chrome_home(request)
        assert response.status_code == HTTPStatus.OK
        body = response.content.decode()
        assert "cited answer" in body
        assert "memory.md:12" in body
        assert 'id="scribe-recall-text"' in body
        assert 'id="scribe-recall-citation"' in body
    finally:
        views_module.render = original_render
        views_module.submit_recall = original_submit


def test_portal_submits_recall_via_portal_client_only() -> None:
    root = _repo_root()
    views = (_portal_root(root) / "views.py").read_text(encoding="utf-8")
    tree = ast.parse(views)
    assert "PortalClient" in views
    assert "submit_recall" in views
    helper = ast.parse((_portal_root(root) / "recall_submit.py").read_text(encoding="utf-8"))
    assert any(isinstance(node, ast.Attribute) and node.attr == "call" for node in ast.walk(helper))
    assert '"recall"' in (views + (_portal_root(root) / "recall_submit.py").read_text(encoding="utf-8"))
    assert not _raw_http_imports(tree)
    assert not _pyforge_package_imports(tree)

    home = (_portal_root(root) / "templates" / "scribe_portal" / "home.html").read_text(
        encoding="utf-8",
    )
    results = (_portal_root(root) / "templates" / "scribe_portal" / "results.html").read_text(encoding="utf-8")
    assert 'name="query"' in home
    assert "scribe-recall-form" in home
    assert "hx-post" in home
    assert "scribe-recall-results" in home
    assert "scribe-recall-text" in results
    assert "scribe-recall-citation" in results
    assert "django_pyforge/base.html" in home


def test_portal_tree_has_no_raw_http_or_pyforge_or_chrome_copy() -> None:
    root = _repo_root()
    portal = _portal_root(root)
    offenders: list[str] = []
    for path in _iter_py(portal):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        offenders.extend(f"{path}: {hit}" for hit in _raw_http_imports(tree))
        offenders.extend(f"{path}: {hit}" for hit in _pyforge_package_imports(tree))
    for path in portal.rglob("*"):
        if path.is_file() and path.name in _CHROME_COPY:
            offenders.append(f"chrome copy: {path}")
    assert offenders == []


def test_portal_job_and_cursor_rule_inherit_default_recall() -> None:
    root = _repo_root()
    job = (
        root / "src" / "shared" / "packages" / "django-pyforge" / "src" / "django_pyforge" / "assertion" / "client.py"
    ).read_text(encoding="utf-8")
    assert '"--kind"' not in job and "'--kind'" not in job
    rule = (root / ".cursor" / "rules" / "scribe-recall.mdc").read_text(encoding="utf-8")
    assert "scribe recall" in rule
    assert "AGENTS.md" in rule


def test_src_platform_has_no_pyforge_import() -> None:
    root = _repo_root()
    changed = changed_paths_since(root, pathspec="src/platform")
    offenders: list[str] = []
    for rel in changed:
        path = root / rel
        if path.suffix != ".py" or not path.is_file():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        offenders.extend(f"{rel}: {hit}" for hit in _pyforge_package_imports(tree))
    patch = diff_text_since(root, pathspec="src/platform")
    assert "import pyforge" not in patch
    assert "from pyforge" not in patch
    assert not offenders, f"src/platform pyforge imports in this diff: {changed} {offenders}"
