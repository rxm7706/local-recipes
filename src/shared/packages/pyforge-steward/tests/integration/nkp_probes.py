"""The attended NKP probes' client (steward Story 118.6, spec-pyforge-steward CAP-177).

CAP-177's success names observables the attended kind runs of 2026-10-31 checked by hand with
untracked scratch scripts: the landing SPA signs in through Keycloak as the bootstrap admin
(Story 118.1 AC2), the hub signs in through Keycloak and a ``small-instance`` server spawns, and
the landing page lists the JupyterHub and Nebi cards as healthy (Story 118.2 AC2). This module is
what the three probes beside it share. It calls the cluster's own endpoints and ``nic`` (AD-1)
and reimplements neither.

Every credential is read at run time. The domain, the Keycloak URL and the bootstrap admin
password come from ``nic outputs --format json --show-secrets -f <config>``, and the provider
credentials a config declares come from ``.env`` through ``keys``, as ``deploy nic`` reads them.
A value that must not be printed is held as :class:`Secret`. Its ``repr`` and ``str`` are
``***``, and its value joins a process-wide registry in every form it can print in: raw,
URL-encoded and repr-escaped. Every token the token endpoint answers joins it too. :func:`redact`
scrubs those values from any text, and the directory's conftest applies it to every pytest report,
``pytest -l`` locals included. Nothing is written to disk.

When the cluster is absent, :class:`ClusterAbsent` is raised and the probes skip with its reason.
When the cluster answers and an observable is wrong, :class:`ProbeError` is raised and the probe
fails.
"""

from __future__ import annotations

import base64
import hashlib
import html
import http.client
import http.cookiejar
import json
import os
import re
import secrets
import shutil
import socket
import ssl
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from email.message import Message
from pathlib import Path
from typing import Any

import pytest
import yaml

from pyforge.steward.deploy_nic import DOTENV_RELATIVE, load_secret_env, operator_env_names

# Story 117.4 (spec-pyforge-steward:CAP-175): this module names the tracked NIC config (DEFAULT_CONFIG) and the
# directory's conftest hands the repo root to `connect`, so every module here is marked live_tree and the
# station-tests trigger map routes what they read to steward's live-tree half. Neither half collects
# tests/integration; pyforge-steward-nkp-probes does (Story 118.6).
pytestmark = pytest.mark.live_tree

DEFAULT_CONFIG = "src/platform/deploy/nic/my-nebari-local.yaml"
REALM = "nebari"  # NIC's realm bootstrap creates the `nebari` realm and its `admin` user
ADMIN_USER = "admin"
LANDING_CLIENT_ID = "nebari-system-nebari-landing-spa"  # the landing page's Keycloak client
SPAWN_PROFILE = "small-instance"
EXPECTED_CARDS = ("JupyterHub", "Nebi")
SPAWN_TIMEOUT_S = 300.0
HTTP_TIMEOUT_S = 30.0
NIC_TIMEOUT_S = 180.0
REACH_TIMEOUT_S = 5.0

_REGISTERED: set[str] = set()
_MIN_SECRET_LEN = 4  # never register a value so short that redacting it would mangle ordinary text


class ClusterAbsent(Exception):
    """No reachable cluster for the config: every probe skips with this reason."""


class ProbeError(Exception):
    """The cluster answered and an observable is wrong: the probe fails with this message."""


class Secret:
    """A value that never prints. ``reveal()`` is the one way to read it."""

    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        self._value = value
        register(value)

    def reveal(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return "Secret('***')"

    __str__ = __repr__

    def __format__(self, spec: str) -> str:
        return repr(self)


def register(value: str) -> None:
    """Add ``value`` to the values :func:`redact` scrubs (a value under four characters is not registered).

    Every form it can print in joins too: raw, URL-encoded (a form body or a query string, as ``pytest -l`` shows
    a local holding one) and repr-escaped (a quote or a backslash inside a local's repr)."""
    if len(value) >= _MIN_SECRET_LEN:
        _REGISTERED.update(
            {
                value,
                urllib.parse.quote_plus(value),
                urllib.parse.quote(value),
                urllib.parse.quote(value, safe=""),
                repr(value)[1:-1],
            }
        )


def redact(text: str) -> str:
    """``text`` with every registered secret value replaced by ``***``."""
    for value in sorted(_REGISTERED, key=len, reverse=True):
        text = text.replace(value, "***")
    return text


def scrub_report(report: Any) -> None:
    """Redact every registered secret from a pytest report's failure text and captured output."""
    if not _REGISTERED:
        return
    longrepr = getattr(report, "longrepr", None)
    if isinstance(longrepr, tuple) and len(longrepr) == 3:  # a skip: (path, lineno, reason)
        path, lineno, reason = longrepr
        report.longrepr = (path, lineno, redact(str(reason)))
    elif longrepr is not None:
        text = str(longrepr)
        if redact(text) != text:
            report.longrepr = redact(text)
    sections = getattr(report, "sections", None)
    if sections:
        report.sections = [(title, redact(content)) for title, content in sections]


def where(url: str) -> str:
    """``url`` without its query or fragment: an authorization code or a state never reaches a message."""
    return urllib.parse.urlsplit(url)._replace(query="", fragment="").geturl()


# ---------------------------------------------------------------------------
# nic: the kubeconfig gate and the outputs
# ---------------------------------------------------------------------------

Runner = Callable[[list[str], dict[str, str]], "subprocess.CompletedProcess[str]"]


def _run(argv: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        argv, env=env, capture_output=True, text=True, check=False, timeout=NIC_TIMEOUT_S
    )


def nic_binary(environ: Mapping[str, str]) -> str | None:
    """``nic`` from the pixi environment (``CONDA_PREFIX/bin/nic``), else from ``PATH``."""
    prefix = environ.get("CONDA_PREFIX")
    if prefix:
        candidate = Path(prefix) / "bin" / "nic"
        if candidate.is_file():
            return str(candidate)
    return shutil.which("nic", path=environ.get("PATH", ""))


def nic_error(proc: subprocess.CompletedProcess[str]) -> str:
    """The last line nic printed: its JSON log's ``error`` field when it logged one."""
    lines = [line for line in (proc.stderr or proc.stdout or "").splitlines() if line.strip()]
    if not lines:
        return f"exit {proc.returncode}, no output"
    last = lines[-1].strip()
    try:
        record = json.loads(last)
    except ValueError:
        return redact(last)
    if isinstance(record, dict):
        return redact(str(record.get("error") or record.get("msg") or last))
    return redact(last)


def api_server(kubeconfig: str) -> tuple[str, int]:
    """The current context's API server ``(host, port)``. Raises ValueError naming what is missing, never content."""
    try:
        document = yaml.safe_load(kubeconfig)
    except yaml.YAMLError:
        raise ValueError("nic kubeconfig did not print YAML") from None
    if not isinstance(document, dict):
        raise ValueError("nic kubeconfig did not print a kubeconfig mapping")
    clusters: dict[str, Mapping[str, Any]] = {}
    for entry in document.get("clusters") or []:
        if isinstance(entry, dict) and isinstance(entry.get("cluster"), dict):
            clusters[str(entry.get("name"))] = entry["cluster"]
    chosen: str | None = None
    for entry in document.get("contexts") or []:
        if isinstance(entry, dict) and entry.get("name") == document.get("current-context"):
            context = entry.get("context")
            chosen = str(context.get("cluster")) if isinstance(context, dict) else None
    cluster = clusters.get(chosen or "") or next(iter(clusters.values()), None)
    server = cluster.get("server") if cluster else None
    if not isinstance(server, str) or not server:
        raise ValueError("the kubeconfig names no cluster server")
    parts = urllib.parse.urlsplit(server)
    if not parts.hostname:
        raise ValueError(f"the kubeconfig's server {server!r} has no host")
    return parts.hostname, parts.port or (443 if parts.scheme == "https" else 80)


def unreachable(host: str, port: int, timeout: float = REACH_TIMEOUT_S) -> str | None:
    """None when ``host:port`` accepts a TCP connection, else why it did not."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return None
    except OSError as exc:
        return str(exc) or type(exc).__name__


@dataclass(frozen=True)
class NkpOutputs:
    """What ``nic outputs`` reports for the probes. The password is a :class:`Secret`."""

    domain: str
    keycloak_url: str
    admin_password: Secret

    @property
    def issuer(self) -> str:
        base = self.keycloak_url.rstrip("/")
        return base if "/realms/" in base else f"{base}/realms/{REALM}"

    @property
    def landing(self) -> str:
        return f"https://{self.domain}"

    @property
    def hub(self) -> str:
        return f"https://hub.{self.domain}"


def parse_outputs(text: str) -> NkpOutputs:
    """Read ``nic outputs --format json --show-secrets``. Every ``*password`` field becomes a registered Secret."""
    try:
        document = json.loads(text)
    except ValueError as exc:
        raise ProbeError(f"nic outputs did not print JSON ({type(exc).__name__})") from None
    if not isinstance(document, dict):
        raise ProbeError("nic outputs did not print a JSON object")
    for key, value in document.items():
        if key.endswith("password") and isinstance(value, str):
            register(value)
    required = ("domain", "keycloak_issuer_url", "keycloak_realm_admin_password")
    missing = [name for name in required if not isinstance(document.get(name), str) or not document.get(name)]
    if missing:
        hint = " (redacted: nic outputs needs --show-secrets)" if document.get("redacted") else ""
        raise ProbeError(f"nic outputs is missing {', '.join(missing)}{hint}")
    return NkpOutputs(
        domain=document["domain"],
        keycloak_url=document["keycloak_issuer_url"],
        admin_password=Secret(document["keycloak_realm_admin_password"]),
    )


def verifies_tls(config_document: Mapping[str, Any]) -> bool:
    """False only for a ``certificate.type: selfsigned`` config (the kind profile); a real certificate is verified."""
    certificate = config_document.get("certificate")
    return not (isinstance(certificate, dict) and certificate.get("type") == "selfsigned")


@dataclass(frozen=True)
class NkpCluster:
    config: Path
    outputs: NkpOutputs
    verify_tls: bool
    connect_to: str | None

    def browser(self) -> Browser:
        return Browser(verify_tls=self.verify_tls, connect_to=self.connect_to, domain=self.outputs.domain)


def connect(
    config: Path,
    *,
    root: Path,
    connect_to: str | None = None,
    nic: str | None = None,
    runner: Runner = _run,
    environ: Mapping[str, str] | None = None,
) -> NkpCluster:
    """Find the config's cluster and read its outputs; :class:`ClusterAbsent` when there is none to reach."""
    base_env = dict(os.environ if environ is None else environ)
    config_path = config if config.is_absolute() else root / config
    if not config_path.is_file():
        raise ClusterAbsent(f"config {config} does not exist")
    try:
        document = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        raise ProbeError(f"config {config} is not valid YAML") from None
    if not isinstance(document, dict):
        raise ProbeError(f"config {config} is not a YAML mapping")
    binary = nic or nic_binary(base_env)
    if not binary:
        raise ClusterAbsent("nic is not installed (CONDA_PREFIX/bin/nic or PATH); run under -e pyforge-steward")
    required = operator_env_names(document)
    secret_env, failure = load_secret_env(root, env_file=root / DOTENV_RELATIVE, required=required)
    if failure is not None or secret_env is None:
        raise ClusterAbsent(failure.summary if failure is not None else "the config's credentials did not resolve")
    for value in secret_env.values():
        register(value)
    child_env = {key: value for key, value in base_env.items() if key not in required}
    child_env.update(secret_env)
    try:
        kube = runner([binary, "kubeconfig", "-f", str(config_path)], child_env)
    except subprocess.TimeoutExpired:
        raise ClusterAbsent(f"no reachable kubeconfig: nic kubeconfig timed out after {NIC_TIMEOUT_S:.0f} s") from None
    if kube.returncode != 0:
        raise ClusterAbsent(f"no reachable kubeconfig: nic kubeconfig exited {kube.returncode}: {nic_error(kube)}")
    try:
        host, port = api_server(kube.stdout)
    except ValueError as exc:
        raise ClusterAbsent(f"no reachable kubeconfig: {exc}") from None
    why = unreachable(host, port)
    if why is not None:
        raise ClusterAbsent(f"no reachable kubeconfig: the API server {host}:{port} does not answer ({why})")
    try:
        out = runner([binary, "outputs", "--format", "json", "--show-secrets", "-f", str(config_path)], child_env)
    except subprocess.TimeoutExpired:
        raise ProbeError(f"nic outputs timed out after {NIC_TIMEOUT_S:.0f} s") from None
    if out.returncode != 0:
        raise ProbeError(f"nic outputs exited {out.returncode}: {nic_error(out)}")
    return NkpCluster(
        config=config,
        outputs=parse_outputs(out.stdout),
        verify_tls=verifies_tls(document),
        connect_to=connect_to,
    )


# ---------------------------------------------------------------------------
# HTTP: one cookie jar per sign-in, optional --connect-to, never a query string in a message
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Response:
    status: int
    url: str
    body: str
    headers: Message

    def json(self) -> Any:
        try:
            return json.loads(self.body)
        except ValueError:
            raise ProbeError(f"{where(self.url)} did not answer JSON (HTTP {self.status})") from None

    @property
    def location(self) -> str:
        return str(self.headers.get("Location") or "")


class _StopRedirect(urllib.request.HTTPRedirectHandler):
    """Follow redirects, except one whose target starts with ``stop_at``: it comes back as a 3xx Response."""

    stop_at: str | None = None

    def redirect_request(
        self, req: urllib.request.Request, fp: Any, code: int, msg: str, headers: http.client.HTTPMessage, newurl: str
    ) -> urllib.request.Request | None:
        if self.stop_at and newurl.startswith(self.stop_at):
            return None
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _https_handler(context: ssl.SSLContext, connect_to: str | None, domain: str | None) -> urllib.request.HTTPSHandler:
    """An HTTPS handler that sends a connection for ``domain`` or ``*.domain`` to ``connect_to`` (curl's
    ``--connect-to``), keeping the host name for SNI and the Host header: the rootless-kind gateway is reached
    through ``kubectl port-forward`` on 127.0.0.1."""

    class _Connection(http.client.HTTPSConnection):
        def __init__(self, host: str, **kwargs: Any) -> None:
            super().__init__(host, **kwargs)
            name = (self.host or "").lower()
            if connect_to and domain and (name == domain or name.endswith(f".{domain}")):
                target = connect_to

                def _create(address: tuple[str, int], *args: Any, **kw: Any) -> socket.socket:
                    return socket.create_connection((target, address[1]), *args, **kw)

                self._create_connection = _create  # type: ignore[assignment]

    class _Handler(urllib.request.HTTPSHandler):
        def https_open(self, req: urllib.request.Request) -> http.client.HTTPResponse:
            return self.do_open(_Connection, req, context=context)

    return _Handler(context=context)


def _form_body(form: Mapping[str, str | Secret]) -> bytes:
    """The urlencoded form body. A :class:`Secret` is revealed here alone, and this frame returns before anything
    can fail, so no frame a traceback shows holds the value raw (pprint splits a long string at its spaces)."""
    return urllib.parse.urlencode(
        {name: value.reveal() if isinstance(value, Secret) else value for name, value in form.items()}
    ).encode("utf-8")


class Browser:
    """A cookie-keeping HTTP client for one sign-in."""

    def __init__(
        self,
        *,
        verify_tls: bool = True,
        connect_to: str | None = None,
        domain: str | None = None,
        timeout: float = HTTP_TIMEOUT_S,
    ) -> None:
        self.jar = http.cookiejar.CookieJar()
        context = ssl.create_default_context()
        if not verify_tls:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        self._redirects = _StopRedirect()
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar),
            self._redirects,
            _https_handler(context, connect_to, domain),
        )
        self._timeout = timeout

    def cookie(self, name: str) -> str | None:
        for cookie in self.jar:
            if cookie.name == name and cookie.value:
                return cookie.value
        return None

    def request(
        self,
        method: str,
        url: str,
        *,
        form: Mapping[str, str | Secret] | None = None,
        headers: Mapping[str, str] | None = None,
        stop_at: str | None = None,
    ) -> Response:
        sent = dict(headers or {})
        if form is not None:
            sent.setdefault("Content-Type", "application/x-www-form-urlencoded")
        # The encoded body is built inside the call, never held in a local: pytest -l prints locals, and pprint
        # wraps a long bytes repr across lines where no registered form of a secret can match it.
        request = urllib.request.Request(  # noqa: S310
            url,
            data=_form_body(form) if form is not None else None,
            headers=sent,
            method=method,
        )
        self._redirects.stop_at = stop_at
        try:
            with self._opener.open(request, timeout=self._timeout) as answer:
                body = answer.read().decode("utf-8", errors="replace")
                return Response(answer.status, answer.geturl(), body, answer.headers)
        except urllib.error.HTTPError as err:
            body = err.read().decode("utf-8", errors="replace") if err.fp is not None else ""
            return Response(err.code, err.geturl() or url, body, err.headers)
        except (urllib.error.URLError, OSError, http.client.HTTPException) as err:
            # http.client.HTTPException too (a malformed answer): left to propagate, its traceback would show the
            # urllib frames' locals, whose request headers carry the session cookies.
            reason = getattr(err, "reason", err)
            raise ProbeError(
                f"{method} {where(url)} did not connect ({reason}); a gateway reached through kubectl "
                "port-forward needs --nkp-connect-to 127.0.0.1 (docs/how-to/host-nebari.md)"
            ) from None
        finally:
            self._redirects.stop_at = None


# ---------------------------------------------------------------------------
# Keycloak: the sign-in form and the auth-code + PKCE flow
# ---------------------------------------------------------------------------

_FORM_ACTION = re.compile(r"<form\b[^>]*\baction=\"([^\"]+)\"", re.IGNORECASE)
_KC_ERROR = re.compile(r"id=\"input-error[^\"]*\"[^>]*>\s*([^<]+?)\s*<", re.IGNORECASE)
_TITLE = re.compile(r"<title>\s*([^<]*?)\s*</title>", re.IGNORECASE)


def _page_note(page: Response) -> str:
    error = _KC_ERROR.search(page.body)
    if error:
        return html.unescape(error.group(1))
    title = _TITLE.search(page.body)
    return html.unescape(title.group(1)) if title else "no title"


def submit_keycloak_login(
    browser: Browser, page: Response, *, username: str, password: Secret, stop_at: str | None = None
) -> Response:
    """POST the bootstrap admin into the Keycloak sign-in form ``page`` shows; the answer after its redirects."""
    actions = [html.unescape(match) for match in _FORM_ACTION.findall(page.body)]
    action = next((candidate for candidate in actions if "login-actions" in candidate), None)
    if page.status != 200 or action is None:
        raise ProbeError(
            f"expected the Keycloak sign-in form at {where(page.url)}, got HTTP {page.status} ({_page_note(page)})"
        )
    target = urllib.parse.urljoin(page.url, action)
    answer = browser.request(
        "POST",
        target,
        form={"username": username, "password": password, "credentialId": ""},
        stop_at=stop_at,
    )
    if answer.status == 200 and "login-actions" in answer.url:
        raise ProbeError(f"Keycloak did not sign in {username!r} at {where(answer.url)}: {_page_note(answer)}")
    return answer


@dataclass(frozen=True)
class SignIn:
    claims: dict[str, Any]
    access_token: Secret


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def token_claims(token: str) -> dict[str, Any]:
    """A JWT's payload, unverified (the token came over the TLS connection the probe opened)."""
    if token.count(".") != 2:
        raise ProbeError("the access token is not a JWT")
    claims_segment = token.split(".")[1]  # the claims alone: the signature never sits in a local pytest -l prints
    padded = claims_segment + "=" * (-len(claims_segment) % 4)
    try:
        claims = json.loads(base64.urlsafe_b64decode(padded))
    except ValueError:
        raise ProbeError("the access token's payload is not JSON") from None
    if not isinstance(claims, dict):
        raise ProbeError("the access token's payload is not a JSON object")
    return claims


def keycloak_pkce_signin(
    browser: Browser, *, issuer: str, client_id: str, redirect_uri: str, username: str, password: Secret
) -> SignIn:
    """Sign ``username`` in to ``client_id`` with the authorization-code flow and PKCE (S256)."""
    discovery = browser.request("GET", f"{issuer}/.well-known/openid-configuration")
    if discovery.status != 200:
        raise ProbeError(f"Keycloak discovery at {where(discovery.url)} answered HTTP {discovery.status}")
    meta = discovery.json()
    authorize, token_endpoint = meta.get("authorization_endpoint"), meta.get("token_endpoint")
    if not isinstance(authorize, str) or not isinstance(token_endpoint, str):
        raise ProbeError(f"Keycloak discovery at {where(discovery.url)} names no authorization or token endpoint")
    verifier = secrets.token_urlsafe(64)
    state = secrets.token_urlsafe(16)
    query = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "response_type": "code",
            "scope": "openid profile email",
            "redirect_uri": redirect_uri,
            "state": state,
            "code_challenge": _b64url(hashlib.sha256(verifier.encode("ascii")).digest()),
            "code_challenge_method": "S256",
        }
    )
    page = browser.request("GET", f"{authorize}?{query}", stop_at=redirect_uri)
    if not (300 <= page.status < 400 and page.location.startswith(redirect_uri)):
        page = submit_keycloak_login(browser, page, username=username, password=password, stop_at=redirect_uri)
    if not (300 <= page.status < 400 and page.location.startswith(redirect_uri)):
        raise ProbeError(f"Keycloak did not redirect to {redirect_uri} (HTTP {page.status} at {where(page.url)})")
    params = urllib.parse.parse_qs(urllib.parse.urlsplit(page.location).query)
    if "error" in params:
        detail = params.get("error_description", params["error"])[0]
        raise ProbeError(f"Keycloak answered error={params['error'][0]}: {detail}")
    if params.get("state", [""])[0] != state:
        raise ProbeError("Keycloak's redirect carries a state this sign-in did not send")
    code = params.get("code", [""])[0]
    if not code:
        raise ProbeError(f"Keycloak's redirect to {redirect_uri} carries no authorization code")
    exchange = browser.request(
        "POST",
        token_endpoint,
        form={
            "grant_type": "authorization_code",
            "client_id": client_id,
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": verifier,
        },
        headers={"Accept": "application/json"},
    )
    payload = exchange.json()
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key.endswith("token") and isinstance(value, str):
                register(value)  # the access, refresh and ID tokens: none prints if a check below fails
    if exchange.status != 200 or not isinstance(payload, dict) or not isinstance(payload.get("access_token"), str):
        error = payload.get("error") if isinstance(payload, dict) else None
        raise ProbeError(f"the token endpoint answered HTTP {exchange.status} ({error or 'no access token'})")
    access_token = Secret(payload["access_token"])
    return SignIn(claims=token_claims(access_token.reveal()), access_token=access_token)


def landing_signin(cluster: NkpCluster) -> SignIn:
    """The landing SPA's own sign-in (Story 118.1 AC2): its Keycloak client, its redirect URI, the bootstrap admin."""
    outputs = cluster.outputs
    return keycloak_pkce_signin(
        cluster.browser(),
        issuer=outputs.issuer,
        client_id=LANDING_CLIENT_ID,
        redirect_uri=f"{outputs.landing}/",
        username=ADMIN_USER,
        password=outputs.admin_password,
    )


# ---------------------------------------------------------------------------
# JupyterHub: the OAuth sign-in, the spawn
# ---------------------------------------------------------------------------


def _hub_headers(browser: Browser) -> dict[str, str]:
    headers = {"Accept": "application/json"}
    xsrf = browser.cookie("_xsrf")
    if xsrf:
        headers["X-XSRFToken"] = xsrf
    return headers


def hub_user(browser: Browser, hub: str) -> dict[str, Any]:
    answer = browser.request("GET", f"{hub}/hub/api/user", headers=_hub_headers(browser))
    if answer.status != 200:
        raise ProbeError(f"GET {hub}/hub/api/user answered HTTP {answer.status}")
    model = answer.json()
    if not isinstance(model, dict):
        raise ProbeError(f"GET {hub}/hub/api/user did not answer a user model")
    return model


def hub_signin(browser: Browser, outputs: NkpOutputs) -> dict[str, Any]:
    """``https://hub.<domain>`` signs the bootstrap admin in through Keycloak; the hub's user model after."""
    hub = outputs.hub
    page = browser.request("GET", f"{hub}/hub/oauth_login?next=%2Fhub%2Fhome")
    landed = submit_keycloak_login(browser, page, username=ADMIN_USER, password=outputs.admin_password)
    if landed.status != 200 or urllib.parse.urlsplit(landed.url).hostname != f"hub.{outputs.domain}":
        raise ProbeError(f"the hub's OAuth sign-in ended at HTTP {landed.status} on {where(landed.url)}")
    if browser.cookie("_xsrf") is None:
        browser.request("GET", f"{hub}/hub/home")
    return hub_user(browser, hub)


def default_server(user: Mapping[str, Any]) -> dict[str, Any] | None:
    """The user's default server (``servers[""]``), or what ``server``/``pending`` say when the model has no
    ``servers``; None when there is none."""
    servers = user.get("servers")
    if isinstance(servers, dict):
        server = servers.get("")
        return server if isinstance(server, dict) else None
    if user.get("server") or user.get("pending"):
        return {"ready": bool(user.get("server")) and not user.get("pending"), "pending": user.get("pending")}
    return None


def spawn_and_stop(
    browser: Browser,
    outputs: NkpOutputs,
    *,
    profile: str = SPAWN_PROFILE,
    timeout: float = SPAWN_TIMEOUT_S,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Spawn the signed-in user's default server with ``profile``, wait until the hub reports it ready, stop it.

    Refuses when the user already runs a default server: the probe stops only the server it started."""
    hub = outputs.hub
    user = hub_user(browser, hub)
    name = str(user.get("name") or ADMIN_USER)
    running = default_server(user)
    if running is not None:
        raise ProbeError(
            f"{name} already has a default server (ready={running.get('ready')}, pending={running.get('pending')}); "
            f"stop it from {hub}/hub/home and run the probe again"
        )
    xsrf = browser.cookie("_xsrf") or ""
    try:
        posted = browser.request(
            "POST", f"{hub}/hub/spawn", form={"profile": profile, "_xsrf": xsrf}, headers=_hub_headers(browser)
        )
        if posted.status >= 400:
            raise ProbeError(f"POST {hub}/hub/spawn profile={profile} answered HTTP {posted.status}")
        deadline = clock() + timeout
        seen = False
        while True:
            server = default_server(hub_user(browser, hub))
            if server is not None and server.get("ready"):
                return server
            if server is None and seen:
                raise ProbeError(f"the {profile} server stopped before it was ready")
            seen = seen or server is not None
            if clock() >= deadline:
                state = "absent" if server is None else f"pending={server.get('pending')}"
                raise ProbeError(f"the {profile} server was not ready after {timeout:.0f} s ({state})")
            sleep(2.0)
    finally:
        try:
            browser.request("DELETE", f"{hub}/hub/api/users/{name}/server", headers=_hub_headers(browser))
        except ProbeError:
            pass  # the stop is best effort; the probe's own verdict stands


# ---------------------------------------------------------------------------
# The landing page's cards
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Card:
    name: str
    url: str
    health: str


def parse_cards(payload: Any) -> list[Card]:
    """``GET /api/v1/services``: ``{"services": [...]}`` or a bare list; each card's ``displayName`` (else ``name``)
    and ``health.status`` (else ``status``)."""
    items = payload.get("services") if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        raise ProbeError("the landing API did not answer a service list")
    cards: list[Card] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        health = item.get("health")
        status = health.get("status") if isinstance(health, dict) else item.get("status")
        cards.append(
            Card(
                name=str(item.get("displayName") or item.get("name") or ""),
                url=str(item.get("url") or ""),
                health=str(status or "unknown"),
            )
        )
    return cards


def card_problems(cards: list[Card], expected: tuple[str, ...] = EXPECTED_CARDS) -> list[str]:
    """One line per expected card that is missing or not ``healthy``; empty when every one is."""
    problems: list[str] = []
    for want in expected:
        matches = [card for card in cards if card.name.casefold() == want.casefold()]
        if not matches:
            problems.append(f"{want}: no card")
        elif not any(card.health == "healthy" for card in matches):
            problems.append(f"{want}: {', '.join(card.health for card in matches)}")
    return problems


def landing_cards(browser: Browser, outputs: NkpOutputs, token: Secret) -> list[Card]:
    """The landing page's cards as the signed-in admin sees them (the SPA's bearer token)."""
    answer = browser.request(
        "GET",
        f"{outputs.landing}/api/v1/services",
        headers={"Authorization": f"Bearer {token.reveal()}", "Accept": "application/json"},
    )
    if answer.status != 200:
        raise ProbeError(f"GET {outputs.landing}/api/v1/services answered HTTP {answer.status}")
    return parse_cards(answer.json())
