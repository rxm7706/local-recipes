"""Story 23.1 / CAP-7: same board URL, role-sliced rows (canopy AD-20).

The host deliverable is the JSON fixture board at ``/stations/atlas/board/``
(Story 49.4, 2026-09-10). Atlas's package-local Vizro stack is intentionally
not mounted on the host URLconf — that boundary is asserted, not a gap.

This module must not ``import pyforge`` — isolation is asserted over HTTP
and AST, not by pulling factory packages into ``src/platform/tests/``.
"""

from __future__ import annotations

import ast
from http import HTTPStatus
from pathlib import Path

import pytest
from django.test import Client
from django.urls import resolve
from django_atlas_portal import board as atlas_board
from django_pyforge.roles import IDP_TOKEN_CLAIMS_SESSION_KEY
from django_pyforge.roles import prefixed_station
from django_pyforge.roles import prefixed_tenant

PLATFORM_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PLATFORM_ROOT.parents[1]
SHARED_PACKAGES = REPO_ROOT / "src" / "shared" / "packages"
BOARD_PATH = "/stations/atlas/board/"
_SECOND_STACK_TOP = frozenset({"vizro", "dash"})
_HOST_SCAN_ROOTS = (
    PLATFORM_ROOT / "config",
    PLATFORM_ROOT / "platformapp",
    SHARED_PACKAGES / "django-pyforge" / "src" / "django_pyforge",
    SHARED_PACKAGES / "django-atlas" / "src" / "django_atlas_portal",
    SHARED_PACKAGES / "django-doctor" / "src" / "django_doctor_portal",
    SHARED_PACKAGES / "django-herald" / "src" / "django_herald_portal",
    SHARED_PACKAGES / "django-marshal" / "src" / "django_marshal_portal",
    SHARED_PACKAGES / "django-mason" / "src" / "django_mason_portal",
    SHARED_PACKAGES / "django-scribe" / "src" / "django_scribe_portal",
    SHARED_PACKAGES / "django-steward" / "src" / "django_steward_portal",
    SHARED_PACKAGES / "django-warden" / "src" / "django_warden_fabric",
)


def _iter_py(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    return sorted(path for path in root.rglob("*.py") if path.is_file())


def _import_modules(tree: ast.AST) -> list[str]:
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.append(node.module)
    return found


def _client_with_roles(*roles: str) -> Client:
    client = Client()
    session = client.session
    session[IDP_TOKEN_CLAIMS_SESSION_KEY] = {"groups": list(roles)}
    session.save()
    return client


def _board_roles(*extra: str) -> tuple[str, ...]:
    """Station + tenant prefixed roles for the atlas board fixture."""
    return (prefixed_station("atlas"), *extra)


@pytest.mark.django_db
def test_two_roles_same_url_return_disjoint_rows() -> None:
    east = _client_with_roles(*_board_roles(prefixed_tenant("east")))
    west = _client_with_roles(*_board_roles(prefixed_tenant("west")))
    east_response = east.get(BOARD_PATH)
    west_response = west.get(BOARD_PATH)
    assert east_response.status_code == HTTPStatus.OK
    assert west_response.status_code == HTTPStatus.OK
    assert east_response["Cache-Control"] == "no-store"
    assert west_response["Cache-Control"] == "no-store"
    east_rows = east_response.json()["rows"]
    west_rows = west_response.json()["rows"]
    assert {row["tenant"] for row in east_rows} == {"east"}
    assert {row["tenant"] for row in west_rows} == {"west"}
    assert len(east_rows) > len(west_rows)
    east_ids = {row["id"] for row in east_rows}
    west_ids = {row["id"] for row in west_rows}
    assert east_ids.isdisjoint(west_ids)
    east_body = east_response.content.decode()
    west_body = west_response.content.decode()
    assert "west-a" not in east_body
    assert "east-a" not in west_body
    match = resolve(BOARD_PATH)
    assert match.func.__name__ == "board_view"


@pytest.mark.django_db
def test_board_filter_then_search_never_searches_master(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order: list[str] = []
    real_get = atlas_board.get_master_dataset
    real_filter = atlas_board.filter_by_role
    real_search = atlas_board.search

    def wrapped_get(*args: object, **kwargs: object) -> object:
        order.append("get_master_dataset")
        return real_get(*args, **kwargs)

    def wrapped_filter(*args: object, **kwargs: object) -> object:
        order.append("filter_by_role")
        return real_filter(*args, **kwargs)

    def wrapped_search(frame: object, predicate: object) -> object:
        order.append("search")
        if type(frame).__name__ != "RoleFilteredRows":
            msg = "search() requires a RoleFilteredRows, got master"
            raise TypeError(msg)
        return real_search(frame, predicate)

    monkeypatch.setattr(atlas_board, "get_master_dataset", wrapped_get)
    monkeypatch.setattr(atlas_board, "filter_by_role", wrapped_filter)
    monkeypatch.setattr(atlas_board, "search", wrapped_search)

    response = _client_with_roles(*_board_roles(prefixed_tenant("east"))).get(
        BOARD_PATH
    )
    assert response.status_code == HTTPStatus.OK
    assert order == ["get_master_dataset", "filter_by_role", "search"]


@pytest.mark.django_db
def test_search_rejects_unfiltered_master() -> None:
    def keep_all(_row: object) -> bool:
        return True

    master = atlas_board.fetch_master_dataset()
    with pytest.raises(TypeError, match="RoleFilteredRows"):
        atlas_board.search(master, keep_all)


@pytest.mark.django_db
def test_atlas_only_token_returns_empty_rows() -> None:
    response = _client_with_roles(prefixed_station("atlas")).get(BOARD_PATH)
    assert response.status_code == HTTPStatus.OK
    assert response["Cache-Control"] == "no-store"
    assert response.json() == {"rows": []}


@pytest.mark.django_db
def test_multiple_row_roles_fail_closed() -> None:
    response = _client_with_roles(
        *_board_roles(prefixed_tenant("east"), prefixed_tenant("west")),
    ).get(BOARD_PATH)
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"rows": []}


@pytest.mark.django_db
def test_query_and_body_cannot_widen_rows() -> None:
    client = _client_with_roles(*_board_roles(prefixed_tenant("east")))
    crafted = client.get(BOARD_PATH, {"tenant": "west", "role": "west"})
    assert crafted.status_code == HTTPStatus.OK
    rows = crafted.json()["rows"]
    assert {row["tenant"] for row in rows} == {"east"}
    assert all(row["tenant"] != "west" for row in rows)
    posted = client.post(
        BOARD_PATH,
        data='{"tenant":"west","role":"west"}',
        content_type="application/json",
    )
    assert posted.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    assert b"west-a" not in posted.content


@pytest.mark.django_db
def test_board_url_without_atlas_station_role_is_forbidden() -> None:
    anon = Client().get(BOARD_PATH)
    assert anon.status_code == HTTPStatus.FORBIDDEN
    assert b'"rows"' not in anon.content
    row_only = _client_with_roles(prefixed_tenant("east")).get(BOARD_PATH)
    assert row_only.status_code == HTTPStatus.FORBIDDEN
    assert b'"rows"' not in row_only.content


def test_host_chrome_portals_have_no_second_row_filter_stack() -> None:
    offenders: list[str] = []
    for root in _HOST_SCAN_ROOTS:
        for path in _iter_py(root):
            if path.resolve() == Path(__file__).resolve():
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for module in _import_modules(tree):
                top = module.split(".")[0]
                if top in _SECOND_STACK_TOP:
                    offenders.append(f"{path}: {module}")
                if module == "pyforge.atlas.dashboard" or module.startswith(
                    "pyforge.atlas.dashboard.",
                ):
                    offenders.append(f"{path}: {module}")
    assert offenders == []


def test_this_file_does_not_import_pyforge() -> None:
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    hits = [
        module
        for module in _import_modules(tree)
        if module == "pyforge" or module.startswith("pyforge.")
    ]
    assert hits == []


def test_atlas_vizro_cli_is_not_mounted_on_host_urlconf() -> None:
    """Fixture-grade CAP-7: Vizro stays package-local; steward filtering drives the host board."""
    urlconf = (PLATFORM_ROOT / "config" / "urls.py").read_text(encoding="utf-8")
    assert "vizro" not in urlconf.lower()
    assert "pyforge.atlas.dashboard" not in urlconf
    assert "atlas.dashboard" not in urlconf
    board_source = (
        SHARED_PACKAGES / "django-atlas" / "src" / "django_atlas_portal" / "board.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(board_source)
    imported = _import_modules(tree)
    assert not any("DashboardIdentity" in name for name in imported)
    assert not any(mod == "vizro" or mod.startswith("vizro.") for mod in imported)
    assert not any("pyforge.atlas" in mod for mod in imported)
    assert "pyforge.steward.dashboard.filtering" in imported
    assert "pyforge.steward.dashboard.declarations" in imported
    assert "filter_by_role" in board_source
    assert "AccessDeclaration" in board_source
