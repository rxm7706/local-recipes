"""Story 18.3 / 40.1: RS256 service assertions and verified IdP bearers."""

from __future__ import annotations

import ast
import base64
import importlib.util
import json
import re
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from http import HTTPStatus
from pathlib import Path

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.conf import settings
from django.http import HttpRequest
from django.http import HttpResponse
from django.test import RequestFactory
from django.test import override_settings
from django.urls import reverse
from django_pyforge.assertion.client import PortalClient
from django_pyforge.assertion.crypto import mint_assertion
from django_pyforge.assertion.crypto import verify_assertion
from django_pyforge.assertion.exceptions import AssertionRefusedError
from django_pyforge.assertion.exceptions import ExpiredAssertionError
from django_pyforge.assertion.exceptions import WrongAudienceError
from django_pyforge.assertion.golden import GOLDEN_PRIVATE_PEM
from django_pyforge.assertion.golden import GOLDEN_PUBLIC_PEM
from django_pyforge.assertion.identity import verify_idp_bearer
from django_pyforge.assertion.jwks import reset_jwks_cache
from django_pyforge.assertion.middleware import AssertionMiddleware
from django_pyforge.assertion.schema import DELEGATED_BY
from django_pyforge.assertion.schema import MAX_TTL_SECONDS
from django_pyforge.assertion.schema import audience_for
from django_pyforge.assertion.views import mint
from django_pyforge.roles import prefixed_station
from jwt.algorithms import RSAAlgorithm

PLATFORM_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PLATFORM_ROOT.parents[1]
CHROME_ASSERTION = (
    REPO_ROOT
    / "src"
    / "shared"
    / "packages"
    / "django-pyforge"
    / "src"
    / "django_pyforge"
    / "assertion"
)
CORE_ASSERTION = (
    REPO_ROOT
    / "src"
    / "shared"
    / "packages"
    / "pyforge-core"
    / "src"
    / "pyforge"
    / "core"
    / "assertion.py"
)
_SHARED = REPO_ROOT / "src" / "shared" / "packages"
PORTAL_TREES = (
    _SHARED / "django-warden" / "src" / "django_warden_fabric",
    _SHARED / "django-atlas" / "src" / "django_atlas_portal",
    _SHARED / "django-doctor" / "src" / "django_doctor_portal",
    _SHARED / "django-herald" / "src" / "django_herald_portal",
    _SHARED / "django-marshal" / "src" / "django_marshal_portal",
    _SHARED / "django-mason" / "src" / "django_mason_portal",
    _SHARED / "django-scribe" / "src" / "django_scribe_portal",
    _SHARED / "django-steward" / "src" / "django_steward_portal",
    _SHARED / "django-pyforge" / "src" / "django_pyforge" / "probe_portal",
    _SHARED / "django-pyforge" / "src" / "django_pyforge" / "workclass_probe",
)
_BANNED_SECRET = re.compile(
    r"hmac|HS256|PYFORGE_INTERNAL_HS256|INTERNAL_HS256",
    re.IGNORECASE,
)
_HTTP_TOPLEVEL = frozenset({"httpx", "requests", "http.client"})
_BANNED_B64 = re.compile(r"\b(urlsafe_b64decode|b64decode)\b")
_STATION = "warden"
_SUB = "idp-user-alice"
_ROLES = [prefixed_station("warden")]
_TEST_ISSUER = "https://test.invalid/realms/platform"
_TEST_AUDIENCE = "platform-web"


@pytest.fixture
def idp_test_keys(tmp_path: Path) -> dict[str, object]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    kid = "test-idp-signing-key"
    jwk = RSAAlgorithm.to_jwk(public_key, as_dict=True)
    jwk.update({"kid": kid, "use": "sig", "alg": "RS256"})
    jwks_path = tmp_path / "jwks.json"
    jwks_path.write_text(json.dumps({"keys": [jwk]}), encoding="utf-8")
    return {
        "kid": kid,
        "private_pem": private_pem,
        "jwks_url": jwks_path.as_uri(),
        "jwks_path": jwks_path,
    }


@pytest.fixture(autouse=True)
def _idp_verifier_settings(
    idp_test_keys: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import django
    from django.conf import settings

    if not settings.configured:
        django.setup()
    reset_jwks_cache()
    monkeypatch.setattr(settings, "OIDC_JWKS_URL", idp_test_keys["jwks_url"], raising=False)
    monkeypatch.setattr(settings, "OIDC_ISSUER", _TEST_ISSUER, raising=False)
    monkeypatch.setattr(settings, "OIDC_AUDIENCE", _TEST_AUDIENCE, raising=False)
    monkeypatch.setattr(settings, "OIDC_ALGORITHMS", ["RS256"], raising=False)
    monkeypatch.setattr(settings, "OIDC_LEEWAY_SECONDS", 0.0, raising=False)
    monkeypatch.setattr(settings, "DJANGO_PYFORGE_GROUP_CLAIM", "groups", raising=False)
    yield
    reset_jwks_cache()


def _load_core_assertion():
    spec = importlib.util.spec_from_file_location(
        "_story_18_3_core_assertion",
        CORE_ASSERTION,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _idp_bearer(
    sub: str,
    roles: list[str],
    *,
    private_pem: bytes,
    kid: str,
    issuer: str = _TEST_ISSUER,
    audience: str | list[str] = _TEST_AUDIENCE,
    iat: int | None = None,
    exp: int | None = None,
    extra_claims: dict[str, object] | None = None,
    token_headers: dict[str, str] | None = None,
) -> str:
    now = int(datetime.now(tz=UTC).timestamp())
    claims: dict[str, object] = {
        "sub": sub,
        "groups": roles,
        "iss": issuer,
        "aud": audience,
        "iat": iat if iat is not None else now,
        "exp": exp if exp is not None else now + 300,
    }
    if extra_claims:
        claims.update(extra_claims)
    headers = {"kid": kid, "alg": "RS256"}
    if token_headers:
        headers.update(token_headers)
    return jwt.encode(claims, private_pem, algorithm="RS256", headers=headers)


def _unsigned_idp_bearer(sub: str, roles: list[str]) -> str:
    def segment(data: dict[str, object]) -> str:
        raw = json.dumps(data, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")

    return f"{segment({'typ': 'JWT'})}.{segment({'sub': sub, 'groups': roles})}.sig"


def _mint_request(bearer: str, station: str = _STATION) -> HttpResponse:
    request = RequestFactory().post(
        "/assertion/mint/",
        data=json.dumps({"station": station}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {bearer}",
    )
    return mint(request)


def _in_process_transport(url: str, headers: dict[str, str], body: bytes) -> bytes:
    del url
    station = json.loads(body.decode("utf-8"))["station"]
    bearer = headers["Authorization"].removeprefix("Bearer ").strip()
    sub, roles = verify_idp_bearer(bearer)
    token = mint_assertion(
        sub=sub,
        roles=roles,
        station=station,
        private_pem=GOLDEN_PRIVATE_PEM,
    )
    return json.dumps({"assertion": token}).encode("utf-8")


def _assert_service_claims(claims: dict[str, object], *, station: str) -> None:
    assert claims["sub"] == _SUB
    assert claims["roles"] == _ROLES
    assert claims["aud"] == audience_for(station)
    assert claims["delegated_by"] == DELEGATED_BY
    assert int(claims["exp"]) - int(claims["iat"]) <= MAX_TTL_SECONDS


def test_portal_and_host_mint_clients_pass_the_same_verifier(
    idp_test_keys: dict[str, object],
) -> None:
    expected_aud = audience_for(_STATION)
    portal_token = PortalClient().emit(
        _SUB,
        _ROLES,
        _STATION,
        private_pem=GOLDEN_PRIVATE_PEM,
    )
    portal_claims = verify_assertion(
        portal_token,
        audience=expected_aud,
        public_pem=GOLDEN_PUBLIC_PEM,
    )
    _assert_service_claims(portal_claims, station=_STATION)

    core = _load_core_assertion()
    client = core.HostMintClient(
        "https://host.example/assertion/mint/",
        transport=_in_process_transport,
    )
    minted = client.emit(
        idp_bearer=_idp_bearer(
            _SUB,
            _ROLES,
            private_pem=idp_test_keys["private_pem"],
            kid=idp_test_keys["kid"],
        ),
        station=_STATION,
    )
    minted_claims = verify_assertion(
        minted,
        audience=expected_aud,
        public_pem=GOLDEN_PUBLIC_PEM,
    )
    _assert_service_claims(minted_claims, station=_STATION)
    assert core.ALG == "RS256"
    assert core.DELEGATED_BY == DELEGATED_BY


def test_bad_signature_is_refused() -> None:
    token = PortalClient().emit(_SUB, _ROLES, _STATION, private_pem=GOLDEN_PRIVATE_PEM)
    flipped = token[:-6] + ("AAAAAA" if token[-6:] != "AAAAAA" else "BBBBBB")
    with pytest.raises(AssertionRefusedError):
        verify_assertion(
            flipped,
            audience=audience_for(_STATION),
            public_pem=GOLDEN_PUBLIC_PEM,
        )


def test_wrong_audience_is_refused() -> None:
    token = PortalClient().emit(_SUB, _ROLES, "other", private_pem=GOLDEN_PRIVATE_PEM)
    with pytest.raises(WrongAudienceError):
        verify_assertion(
            token,
            audience=audience_for(_STATION),
            public_pem=GOLDEN_PUBLIC_PEM,
        )


def test_expired_assertion_is_refused() -> None:
    stale = datetime.now(tz=UTC) - timedelta(seconds=MAX_TTL_SECONDS + 5)
    token = mint_assertion(
        sub=_SUB,
        roles=_ROLES,
        station=_STATION,
        private_pem=GOLDEN_PRIVATE_PEM,
        iat=int(stale.timestamp()),
    )
    with pytest.raises(ExpiredAssertionError):
        verify_assertion(
            token,
            audience=audience_for(_STATION),
            public_pem=GOLDEN_PUBLIC_PEM,
        )


def _middleware_response(**headers: str) -> HttpResponse:
    request = RequestFactory().get("/stations/warden/", **headers)

    def inner(_req: HttpRequest) -> HttpResponse:
        return HttpResponse("ok")

    return AssertionMiddleware(inner)(request)


@pytest.mark.parametrize(
    "header",
    ["HTTP_X_FORWARDED_USER", "HTTP_X_REMOTE_USER", "HTTP_REMOTE_USER"],
)
def test_identity_header_without_assertion_is_refused(header: str) -> None:
    response = _middleware_response(**{header: "spoofed"})
    assert response.status_code in {HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN}


def test_identity_header_with_valid_assertion_passes() -> None:
    token = PortalClient().emit(_SUB, _ROLES, _STATION, private_pem=GOLDEN_PRIVATE_PEM)
    response = _middleware_response(
        HTTP_X_FORWARDED_USER="spoofed",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert response.status_code == HTTPStatus.OK
    assert response.content == b"ok"


@pytest.mark.parametrize(
    "bearer",
    ["not-a-jwt", "a.b.c", ""],
)
def test_identity_header_with_invalid_assertion_is_refused(bearer: str) -> None:
    response = _middleware_response(
        HTTP_X_FORWARDED_USER="spoofed",
        HTTP_AUTHORIZATION=f"Bearer {bearer}" if bearer else "Bearer ",
    )
    assert response.status_code in {HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN}


def test_identity_header_with_expired_assertion_is_refused() -> None:
    stale = datetime.now(tz=UTC) - timedelta(seconds=MAX_TTL_SECONDS + 5)
    token = mint_assertion(
        sub=_SUB,
        roles=_ROLES,
        station=_STATION,
        private_pem=GOLDEN_PRIVATE_PEM,
        iat=int(stale.timestamp()),
    )
    response = _middleware_response(
        HTTP_X_FORWARDED_USER="spoofed",
        HTTP_AUTHORIZATION=f"Bearer {token}",
    )
    assert response.status_code in {HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN}


def _iter_source(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    return sorted(path for path in root.rglob("*.py") if path.is_file())


def _secret_hits(tree: ast.AST | None, text: str) -> list[str]:
    del tree
    return [match.group(0) for match in _BANNED_SECRET.finditer(text)]


def test_hmac_and_laptop_secrets_are_absent() -> None:
    offenders: list[str] = []
    for root in (CHROME_ASSERTION, CORE_ASSERTION, *PORTAL_TREES):
        for path in _iter_source(root):
            text = path.read_text(encoding="utf-8")
            hits = _secret_hits(ast.parse(text), text)
            if hits:
                offenders.append(f"{path}: {hits}")
    assert offenders == []
    assert _secret_hits(None, "import hmac\n") == ["hmac"]
    assert _secret_hits(None, 'alg = "HS256"\n') == ["HS256"]
    laptop = "PYFORGE_INTERNAL_HS256=secret\n"
    assert _secret_hits(None, laptop) == ["PYFORGE_INTERNAL_HS256"]


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


def test_portal_raw_http_to_a_service_is_review_blocking() -> None:
    offenders: list[str] = []
    for root in PORTAL_TREES:
        for path in _iter_source(root):
            hits = _raw_http_imports(ast.parse(path.read_text(encoding="utf-8")))
            if hits:
                offenders.append(f"{path}: {hits}")
    assert offenders == []
    assert _raw_http_imports(ast.parse("import httpx\n"))
    assert _raw_http_imports(ast.parse("import requests\n"))
    assert _raw_http_imports(ast.parse("import urllib.request\n"))
    assert _raw_http_imports(ast.parse("from urllib.request import urlopen\n"))
    assert _raw_http_imports(ast.parse("import http.client\n"))


def test_cli_client_authenticates_to_the_host_and_does_not_sign(
    idp_test_keys: dict[str, object],
) -> None:
    crypto = {"jwt", "cryptography"}

    def _is_crypto_import(node: ast.AST) -> bool:
        if isinstance(node, ast.Import):
            return any(alias.name.split(".")[0] in crypto for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            return (node.module or "").split(".")[0] in crypto
        return False

    source = CORE_ASSERTION.read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert "urllib.request" in source
    assert not any(_is_crypto_import(node) for node in ast.walk(tree))
    seen: dict[str, object] = {}

    def transport(url: str, headers: dict[str, str], body: bytes) -> bytes:
        seen["url"] = url
        seen["headers"] = headers
        seen["body"] = body
        return _in_process_transport(url, headers, body)

    mint_url = "https://host.example/assertion/mint/"
    core = _load_core_assertion()
    token = core.HostMintClient(mint_url, transport=transport).emit(
        idp_bearer=_idp_bearer(
            _SUB,
            _ROLES,
            private_pem=idp_test_keys["private_pem"],
            kid=idp_test_keys["kid"],
        ),
        station=_STATION,
    )
    assert seen["url"] == mint_url
    headers = seen["headers"]
    assert isinstance(headers, dict)
    assert headers["Authorization"].startswith("Bearer ")
    verify_assertion(
        token,
        audience=audience_for(_STATION),
        public_pem=GOLDEN_PUBLIC_PEM,
    )


def test_host_wires_mint_url_and_middleware_after_token_roles() -> None:
    assert reverse("django-pyforge-assertion-mint") == "/assertion/mint/"
    roles_mw = "django_pyforge.middleware.TokenRolesMiddleware"
    assertion_mw = "django_pyforge.assertion.middleware.AssertionMiddleware"
    stacked = settings.MIDDLEWARE.index(roles_mw) + 1
    assert settings.MIDDLEWARE.index(assertion_mw) == stacked


def test_golden_vector_is_not_the_oidc_persona_mint() -> None:
    golden = (CHROME_ASSERTION / "golden.py").read_text(encoding="utf-8")
    assert "local_dev" not in golden
    assert "mint_token" not in golden
    assert GOLDEN_PRIVATE_PEM.startswith("-----BEGIN")
    assert GOLDEN_PRIVATE_PEM.splitlines()[0].endswith("KEY-----")
    assert GOLDEN_PUBLIC_PEM.startswith("-----BEGIN PUBLIC KEY-----")


def test_host_mint_view_emits_a_verifiable_assertion(
    idp_test_keys: dict[str, object],
) -> None:
    response = _mint_request(
        _idp_bearer(
            _SUB,
            _ROLES,
            private_pem=idp_test_keys["private_pem"],
            kid=idp_test_keys["kid"],
        ),
    )
    assert response.status_code == HTTPStatus.OK
    token = json.loads(response.content)["assertion"]
    claims = verify_assertion(
        token,
        audience=audience_for(_STATION),
        public_pem=GOLDEN_PUBLIC_PEM,
    )
    _assert_service_claims(claims, station=_STATION)


def test_unsigned_bearer_is_refused() -> None:
    response = _mint_request(_unsigned_idp_bearer(_SUB, _ROLES))
    assert response.status_code == HTTPStatus.UNAUTHORIZED


def test_bearer_signed_with_wrong_key_is_refused(
    idp_test_keys: dict[str, object],
) -> None:
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other_pem = other.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    bearer = _idp_bearer(
        _SUB,
        _ROLES,
        private_pem=other_pem,
        kid=idp_test_keys["kid"],
    )
    assert _mint_request(bearer).status_code == HTTPStatus.UNAUTHORIZED


def test_idp_bearer_alg_none_is_refused(idp_test_keys: dict[str, object]) -> None:
    now = int(datetime.now(tz=UTC).timestamp())
    header = base64.urlsafe_b64encode(
        json.dumps({"alg": "none", "kid": idp_test_keys["kid"]}, separators=(",", ":")).encode(
            "utf-8",
        ),
    ).rstrip(b"=").decode("ascii")
    payload = base64.urlsafe_b64encode(
        json.dumps(
            {
                "sub": _SUB,
                "groups": _ROLES,
                "iss": _TEST_ISSUER,
                "aud": _TEST_AUDIENCE,
                "iat": now,
                "exp": now + 300,
            },
            separators=(",", ":"),
        ).encode("utf-8"),
    ).rstrip(b"=").decode("ascii")
    bearer = f"{header}.{payload}."
    assert _mint_request(bearer).status_code == HTTPStatus.UNAUTHORIZED


def test_idp_bearer_hs256_is_refused() -> None:
    bearer = jwt.encode(
        {
            "sub": _SUB,
            "groups": _ROLES,
            "iss": _TEST_ISSUER,
            "aud": _TEST_AUDIENCE,
            "iat": int(datetime.now(tz=UTC).timestamp()),
            "exp": int(datetime.now(tz=UTC).timestamp()) + 300,
        },
        "not-a-laptop-secret-in-source-trees",
        algorithm="HS256",
        headers={"kid": "ignored"},
    )
    assert _mint_request(bearer).status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.parametrize(
    "issuer",
    ["https://wrong.invalid/realms/platform"],
)
def test_idp_bearer_wrong_issuer_is_refused(
    idp_test_keys: dict[str, object],
    issuer: str,
) -> None:
    bearer = _idp_bearer(
        _SUB,
        _ROLES,
        private_pem=idp_test_keys["private_pem"],
        kid=idp_test_keys["kid"],
        issuer=issuer,
    )
    assert _mint_request(bearer).status_code == HTTPStatus.UNAUTHORIZED


def test_idp_bearer_wrong_audience_is_refused(
    idp_test_keys: dict[str, object],
) -> None:
    bearer = _idp_bearer(
        _SUB,
        _ROLES,
        private_pem=idp_test_keys["private_pem"],
        kid=idp_test_keys["kid"],
        audience="wrong-audience",
    )
    assert _mint_request(bearer).status_code == HTTPStatus.UNAUTHORIZED


def test_idp_bearer_expired_is_refused(idp_test_keys: dict[str, object]) -> None:
    stale = int((datetime.now(tz=UTC) - timedelta(minutes=10)).timestamp())
    bearer = _idp_bearer(
        _SUB,
        _ROLES,
        private_pem=idp_test_keys["private_pem"],
        kid=idp_test_keys["kid"],
        iat=stale,
        exp=stale + 60,
    )
    assert _mint_request(bearer).status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.parametrize(
    "omit_claim",
    ["exp", "iat", "sub", "iss", "aud"],
)
def test_idp_bearer_missing_required_claim_is_refused(
    idp_test_keys: dict[str, object],
    omit_claim: str,
) -> None:
    now = int(datetime.now(tz=UTC).timestamp())
    claims = {
        "sub": _SUB,
        "groups": _ROLES,
        "iss": _TEST_ISSUER,
        "aud": _TEST_AUDIENCE,
        "iat": now,
        "exp": now + 300,
    }
    claims.pop(omit_claim)
    bearer = jwt.encode(
        claims,
        idp_test_keys["private_pem"],
        algorithm="RS256",
        headers={"kid": idp_test_keys["kid"], "alg": "RS256"},
    )
    assert _mint_request(bearer).status_code == HTTPStatus.UNAUTHORIZED


def test_unknown_kid_refreshes_once(
    idp_test_keys: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from django_pyforge.assertion import jwks as jwks_mod

    reset_jwks_cache()
    fetch_count = 0
    original_fetch = jwks_mod.JWKSKeySet._fetch_document

    def counting_fetch(self: jwks_mod.JWKSKeySet) -> dict[str, object]:
        nonlocal fetch_count
        fetch_count += 1
        return original_fetch(self)

    monkeypatch.setattr(jwks_mod.JWKSKeySet, "_fetch_document", counting_fetch)

    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other_pem = other.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    token_one = jwt.encode(
        {
            "sub": _SUB,
            "groups": _ROLES,
            "iss": _TEST_ISSUER,
            "aud": _TEST_AUDIENCE,
            "iat": int(datetime.now(tz=UTC).timestamp()),
            "exp": int(datetime.now(tz=UTC).timestamp()) + 300,
        },
        other_pem,
        algorithm="RS256",
        headers={"kid": "unknown-kid-one", "alg": "RS256"},
    )
    token_two = jwt.encode(
        {
            "sub": _SUB,
            "groups": _ROLES,
            "iss": _TEST_ISSUER,
            "aud": _TEST_AUDIENCE,
            "iat": int(datetime.now(tz=UTC).timestamp()),
            "exp": int(datetime.now(tz=UTC).timestamp()) + 300,
        },
        other_pem,
        algorithm="RS256",
        headers={"kid": "unknown-kid-two", "alg": "RS256"},
    )

    assert _mint_request(token_one).status_code == HTTPStatus.UNAUTHORIZED
    assert fetch_count == 2
    assert _mint_request(token_two).status_code == HTTPStatus.UNAUTHORIZED
    assert fetch_count == 2


def test_station_not_in_roles_returns_403(idp_test_keys: dict[str, object]) -> None:
    bearer = _idp_bearer(
        _SUB,
        ["pyforge:station:steward"],
        private_pem=idp_test_keys["private_pem"],
        kid=idp_test_keys["kid"],
    )
    assert _mint_request(bearer, station="warden").status_code == HTTPStatus.FORBIDDEN


def test_flags_station_not_in_roles_returns_403(
    idp_test_keys: dict[str, object],
) -> None:
    bearer = _idp_bearer(
        _SUB,
        ["pyforge:station:warden"],
        private_pem=idp_test_keys["private_pem"],
        kid=idp_test_keys["kid"],
    )
    assert _mint_request(bearer, station="flags").status_code == HTTPStatus.FORBIDDEN


@override_settings(OIDC_JWKS_URL="")
def test_unconfigured_verifier_returns_503() -> None:
    reset_jwks_cache()
    response = _mint_request(_unsigned_idp_bearer(_SUB, _ROLES))
    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE


def test_idp_bearer_is_never_base64_decoded_outside_verifier() -> None:
    offenders: list[str] = []
    for path in _iter_source(CHROME_ASSERTION):
        text = path.read_text(encoding="utf-8")
        if path.name == "identity.py":
            if _BANNED_B64.search(text):
                offenders.append(f"{path}: identity must not base64-decode bearer")
            continue
        if _BANNED_B64.search(text):
            offenders.append(f"{path}: contains bearer base64 decode")
    assert offenders == []


def test_idp_bearer_missing_group_claim_is_refused(
    idp_test_keys: dict[str, object],
) -> None:
    now = int(datetime.now(tz=UTC).timestamp())
    bearer = jwt.encode(
        {
            "sub": _SUB,
            "iss": _TEST_ISSUER,
            "aud": _TEST_AUDIENCE,
            "iat": now,
            "exp": now + 300,
        },
        idp_test_keys["private_pem"],
        algorithm="RS256",
        headers={"kid": idp_test_keys["kid"], "alg": "RS256"},
    )
    assert _mint_request(bearer).status_code == HTTPStatus.UNAUTHORIZED


def test_hs256_token_is_refused() -> None:
    token = jwt.encode(
        {
            "sub": _SUB,
            "roles": _ROLES,
            "aud": audience_for(_STATION),
            "iat": int(datetime.now(tz=UTC).timestamp()),
            "exp": int(datetime.now(tz=UTC).timestamp()) + 60,
            "delegated_by": DELEGATED_BY,
        },
        "not-a-laptop-secret-in-source-trees",
        algorithm="HS256",
    )
    with pytest.raises(AssertionRefusedError):
        verify_assertion(
            token,
            audience=audience_for(_STATION),
            public_pem=GOLDEN_PUBLIC_PEM,
        )
