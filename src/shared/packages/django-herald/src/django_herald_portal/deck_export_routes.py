"""Wire deck-export API routes with portal session or bearer auth (Story 29.2)."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any

from django.conf import settings
from django.contrib.sessions.backends.db import SessionStore
from django_pyforge.assertion.crypto import verify_assertion
from django_pyforge.assertion.exceptions import AssertionRefusedError
from django_pyforge.assertion.schema import audience_for
from django_pyforge.roles import (
    IDP_TOKEN_CLAIMS_SESSION_KEY,
    parse_role_claims,
    role_names,
    roles_from_request,
    station_roles_from_parsed,
)

from django_herald_portal.models import DeckExport
from pyforge.herald.deck_exports import ExportRow
from pyforge.herald.deck_exports import attach_deck_export_routes


class AuthError(Exception):
    status_code = 401


class Unauthorized(AuthError):
    status_code = 401


class Forbidden(AuthError):
    status_code = 403


def resolve_herald_roles(headers: Mapping[str, str], cookies: Mapping[str, str]) -> frozenset[str]:
    """Bearer service assertion or portal browser session (``IDP_TOKEN_CLAIMS``)."""
    auth = headers.get("authorization") or headers.get("Authorization")
    if isinstance(auth, str) and auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        if token:
            try:
                claims = verify_assertion(token, audience=audience_for("herald"))
            except AssertionRefusedError as exc:
                raise Unauthorized(str(exc)) from exc
            roles_raw = claims.get("roles")
            parsed = parse_role_claims(role_names(roles_raw))
            return station_roles_from_parsed(parsed)

    cookie_name = getattr(settings, "SESSION_COOKIE_NAME", "sessionid")
    session_key = cookies.get(cookie_name)
    if not session_key:
        raise Unauthorized("identity required")
    store = SessionStore(session_key=session_key)
    claims = store.get(IDP_TOKEN_CLAIMS_SESSION_KEY)
    if not isinstance(claims, dict):
        raise Unauthorized("identity required")

    class _Req:
        idp_token_claims = claims

    return roles_from_request(_Req())  # type: ignore[arg-type]


def assert_herald_access(headers: Mapping[str, str], cookies: Mapping[str, str]) -> None:
    roles = resolve_herald_roles(headers, cookies)
    if "herald" not in roles:
        raise Forbidden("herald role required")


def list_deck_export_rows() -> list[ExportRow]:
    rows: list[ExportRow] = []
    for item in DeckExport.objects.all().order_by("slug", "kind", "-export_date"):
        rows.append(
            ExportRow(
                slug=item.slug,
                topic=item.topic,
                kind=item.kind,
                date=item.export_date.isoformat(),
                size=int(item.size),
                content_type=item.content_type,
                sha256=item.sha256,
                source_commit=item.source_commit,
                published_at=item.published_at.isoformat(),
            )
        )
    return rows


def open_deck_export_stream(sha256: str) -> tuple[ExportRow, Iterator[bytes]]:
    from pyforge.herald.deck_store import open_deck_store  # noqa: PLC0415

    try:
        item = DeckExport.objects.get(sha256=sha256)
    except DeckExport.DoesNotExist as exc:
        raise KeyError(sha256) from exc
    row = ExportRow(
        slug=item.slug,
        topic=item.topic,
        kind=item.kind,
        date=item.export_date.isoformat(),
        size=int(item.size),
        content_type=item.content_type,
        sha256=item.sha256,
        source_commit=item.source_commit,
        published_at=item.published_at.isoformat(),
    )
    store = open_deck_store()
    key = f"sha256/{sha256}"

    def _iter() -> Iterator[bytes]:
        try:
            yield from store.open_stream(key)
        except KeyError as exc:
            raise OSError(str(exc)) from exc

    return row, _iter()


def wire_deck_export_routes(app: Any) -> None:
    attach_deck_export_routes(
        app,
        gate=assert_herald_access,
        list_records=list_deck_export_rows,
        open_stream=open_deck_export_stream,
        auth_errors=(Unauthorized, Forbidden),
    )
