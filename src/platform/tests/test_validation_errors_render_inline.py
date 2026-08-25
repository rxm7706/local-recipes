"""Steward 25.3: 422 arrays render as inline Django form errors (canopy AD-15)."""

from __future__ import annotations

import ast
from http import HTTPStatus
from pathlib import Path

from django.forms.forms import NON_FIELD_ERRORS
from django.template.loader import render_to_string
from django.test import RequestFactory
from django_pyforge.form_errors import PydanticFormErrorBridge
from django_pyforge.form_errors import toast_http_422
from django_pyforge.forms import VersionForm
from django_pyforge.probe_portal.views import REJECTED_422
from django_pyforge.probe_portal.views import chrome_form

PLATFORM_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PLATFORM_ROOT.parents[1]
BRIDGE_MODULE = (
    REPO_ROOT
    / "src"
    / "shared"
    / "packages"
    / "django-pyforge"
    / "src"
    / "django_pyforge"
    / "form_errors.py"
)


FORM_PATH = "/stations/chrome-probe/form/"
VERSION_MSG = "version is not a valid PEP 440 string"


def test_rejected_submission_renders_errors_inline() -> None:
    request = RequestFactory().post(FORM_PATH, data={"version": "not-pep440"})
    request.idp_roles = ["chrome-probe"]
    response = chrome_form(request)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    body = response.content.decode()
    assert 'id="pyforge-originating-form"' in body
    assert 'id="id_version"' in body
    assert "errorlist" in body
    assert VERSION_MSG in body
    assert 'aria-invalid="true"' in body
    assert 'class="error"' in body
    assert "toast" not in body.lower()


def test_bridge_maps_loc_body_version_to_validation_error_dict() -> None:
    form = VersionForm(data={"version": "not-pep440"})
    error = PydanticFormErrorBridge().apply(form, REJECTED_422)
    assert VERSION_MSG in error.message_dict["version"]
    assert VERSION_MSG in form.errors["version"]


def test_opaque_toast_does_not_put_errors_on_the_field() -> None:
    blob = toast_http_422(REJECTED_422)
    assert "detail" in blob
    form = VersionForm(data={"version": "not-pep440"})
    form.full_clean()
    html = render_to_string(
        "django_pyforge/htmx_form.html",
        {"form": form},
        request=RequestFactory().get(FORM_PATH),
    )
    assert VERSION_MSG not in html
    assert "errorlist" not in html
    assert "id_version" in html


def test_non_array_detail_lands_on_non_field_errors() -> None:
    form = VersionForm(data={"version": "x"})
    error = PydanticFormErrorBridge().apply(form, {"detail": "opaque failure"})
    assert NON_FIELD_ERRORS in error.error_dict
    assert "version" not in error.error_dict


def test_removing_bridge_makes_the_test_fail() -> None:
    tree = ast.parse(BRIDGE_MODULE.read_text(encoding="utf-8"))
    bridge = None
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "PydanticFormErrorBridge":
            bridge = node
    assert bridge is not None, "PydanticFormErrorBridge is the inline 422 mapper"
    dumped = ast.dump(bridge)
    assert "detail" in dumped
    assert "loc" in dumped
    assert "ValidationError" in dumped
    apply_fn = None
    for item in bridge.body:
        if isinstance(item, ast.FunctionDef) and item.name == "apply":
            apply_fn = item
    assert apply_fn is not None, "apply must attach errors onto the bound form"
    assert any(
        isinstance(node, ast.Call) and getattr(node.func, "attr", None) == "add_error"
        for node in ast.walk(apply_fn)
    ), "stubbed apply() without add_error is the toast trap"

    form = VersionForm(data={"version": "not-pep440"})
    form.full_clean()
    assert "version" not in form.errors
    PydanticFormErrorBridge().apply(form, REJECTED_422)
    assert VERSION_MSG in form.errors["version"]
