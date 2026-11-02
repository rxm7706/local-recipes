"""Offline checks of the attended NKP probes' client (steward Story 118.6, spec-pyforge-steward CAP-177).

These tests need no cluster, so they run wherever the probes run. They cover AC2 (no stored secret): the bootstrap
admin password ``nic outputs --show-secrets`` prints never reaches the probe module's output. That output is its
reprs, its error messages, the stdout and stderr of a sign-in against a stand-in Keycloak, and the report pytest
prints for a failing probe. They also cover AC3 (safe anywhere): with no config, no ``nic``, no cluster or an API
server that does not answer, the probes skip, name the reason and never ask for secrets.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import urllib.parse
from collections.abc import Iterator
from email.message import Message
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import nkp_probes
import pytest

# Story 117.4 (spec-pyforge-steward:CAP-175): the directory's conftest hands the repo root to nkp_probes.connect,
# so every module here is marked live_tree and the station-tests trigger map routes what they read to steward's
# live-tree half. Neither half collects tests/integration; pyforge-steward-nkp-probes does (Story 118.6).
pytestmark = pytest.mark.live_tree

SENTINEL = "s3ntinel-Passw0rd-118-6-never-printed"
OTHER = "argocd-s3ntinel-also-never-printed"
# Spaces, URL-reserved characters, both quotes and a backslash, so its URL-encoded and repr-escaped forms all differ;
# long enough that pprint (pytest -l without truncation) splits a string holding it at its spaces.
RESERVED = "p@ss w0rd!/Xy9&=+%'\\\" and a passphrase long enough that pprint splits it at its spaces -118-6"
HERE = Path(__file__).resolve().parent
PACKAGE_SRC = HERE.parents[1] / "src"


def _printed_forms(value: str) -> dict[str, str]:
    """Every form ``value`` can print in: raw, in a form body or a query, and inside a Python repr."""
    return {
        "raw": value,
        "quote_plus": urllib.parse.quote_plus(value),
        "quote": urllib.parse.quote(value),
        "quote-safe-none": urllib.parse.quote(value, safe=""),
        "repr": repr(value)[1:-1],
    }


def _outputs_json(**overrides: Any) -> str:
    document: dict[str, Any] = {
        "domain": "nebari.local",
        "keycloak_issuer_url": "https://keycloak.nebari.local",
        "gateway_address": "192.168.1.100",
        "keycloak_admin_password": "kc-master-s3ntinel",
        "keycloak_realm_admin_password": SENTINEL,
        "argocd_admin_password": OTHER,
    }
    document.update(overrides)
    return json.dumps(document)


# ---------------------------------------------------------------------------
# AC2: a secret never prints
# ---------------------------------------------------------------------------


def test_a_secret_never_prints_its_value() -> None:
    secret = nkp_probes.Secret(SENTINEL)
    outputs = nkp_probes.NkpOutputs(
        domain="nebari.local", keycloak_url="https://keycloak.nebari.local", admin_password=secret
    )
    signin = nkp_probes.SignIn(claims={"preferred_username": "admin"}, access_token=nkp_probes.Secret("tok-xyz-123"))
    rendered = " | ".join(
        [repr(secret), str(secret), f"{secret}", f"{secret!r}", f"{secret:>40}", repr(outputs), str(outputs)]
        + [repr(signin)]
    )
    assert SENTINEL not in rendered
    assert "tok-xyz-123" not in rendered
    assert secret.reveal() == SENTINEL
    assert nkp_probes.redact(f"x {SENTINEL} y") == "x *** y"


def test_outputs_give_the_domain_the_issuer_and_the_realm_admin_and_every_password_joins_the_scrub() -> None:
    outputs = nkp_probes.parse_outputs(_outputs_json())
    assert outputs.domain == "nebari.local"
    assert outputs.issuer == "https://keycloak.nebari.local/realms/nebari"
    assert outputs.landing == "https://nebari.local"
    assert outputs.hub == "https://hub.nebari.local"
    assert outputs.admin_password.reveal() == SENTINEL
    assert nkp_probes.redact(f"{OTHER} kc-master-s3ntinel") == "*** ***"


def test_redacted_outputs_are_refused_by_field_name_without_a_value() -> None:
    with pytest.raises(nkp_probes.ProbeError) as raised:
        nkp_probes.parse_outputs(
            _outputs_json(keycloak_realm_admin_password=None, redacted=["keycloak_realm_admin_password"])
        )
    message = str(raised.value)
    assert "keycloak_realm_admin_password" in message
    assert "--show-secrets" in message
    assert OTHER not in message


def test_outputs_that_are_not_json_are_refused_without_echoing_them() -> None:
    with pytest.raises(nkp_probes.ProbeError) as raised:
        nkp_probes.parse_outputs(f"Keycloak realm admin password  {SENTINEL}")
    assert SENTINEL not in str(raised.value)


def test_a_pytest_report_is_scrubbed_of_every_registered_secret() -> None:
    nkp_probes.register(SENTINEL)
    failed = SimpleNamespace(
        longrepr=f"ProbeError: boom {SENTINEL}", sections=[("Captured stdout call", f"echo {SENTINEL}\n")]
    )
    nkp_probes.scrub_report(failed)
    assert failed.longrepr == "ProbeError: boom ***"
    assert failed.sections == [("Captured stdout call", "echo ***\n")]
    skipped = SimpleNamespace(longrepr=("x.py", 3, f"Skipped: {SENTINEL}"), sections=[])
    nkp_probes.scrub_report(skipped)
    assert skipped.longrepr == ("x.py", 3, "Skipped: ***")


def test_a_registered_secret_is_scrubbed_in_every_form_it_can_print_in() -> None:
    nkp_probes.register(RESERVED)
    for name, form in _printed_forms(RESERVED).items():
        assert nkp_probes.redact(f"<{form}>") == "<***>", f"the {name} form is not scrubbed"


def _pytest_over(tmp_path: Path, source: str, *options: str) -> str:
    """Run a real pytest, under ``-l``, on the test file ``source`` beside copies of this directory's conftest and
    ``nkp_probes``. Returns everything it printed, after asserting that the one test failed."""
    layout = tmp_path / "src" / "shared" / "packages" / "pyforge-steward" / "tests" / "integration"
    layout.mkdir(parents=True)
    shutil.copy(HERE / "conftest.py", layout / "conftest.py")
    shutil.copy(HERE / "nkp_probes.py", layout / "nkp_probes.py")
    (layout / "test_leak.py").write_text(source, encoding="utf-8")
    env = {key: value for key, value in os.environ.items() if key != "PYTEST_ADDOPTS"}
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(PACKAGE_SRC), env.get("PYTHONPATH", "")]))
    run = subprocess.run(
        [sys.executable, "-m", "pytest", str(layout), "-q", "-rA", "-p", "no:cacheprovider", "--tb=long", "-l"]
        + list(options),
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    printed = run.stdout + run.stderr
    assert run.returncode == 1, f"exit {run.returncode}, not the one failed test ({len(printed)} characters printed)"
    return printed


def _leaked(printed: str, *values: str, fragment: int = 0) -> list[str]:
    """The forms of ``values`` that ``printed`` carries, named by index and form, never by value. With ``fragment``,
    any run of that many characters from a form counts: a value split across lines still leaks."""
    leaks: list[str] = []
    for index, value in enumerate(values):
        for name, form in _printed_forms(value).items():
            size = fragment or len(form)
            if any(form[start : start + size] in printed for start in range(len(form) - size + 1)):
                leaks.append(f"value {index} ({name})")
    return leaks


def test_a_failing_probe_s_pytest_output_never_carries_the_password(tmp_path: Path) -> None:
    """The directory's conftest, run by a real pytest: a probe that prints the password and fails with it in its
    message leaves only ``***`` in everything pytest prints."""
    printed = _pytest_over(
        tmp_path,
        "import nkp_probes\n\n\n"
        "def test_leak():\n"
        "    password = nkp_probes.parse_outputs(" + repr(_outputs_json()) + ").admin_password\n"
        "    print('captured', password.reveal())\n"
        "    raise nkp_probes.ProbeError(f'boom {password.reveal()}')\n",
    )
    assert "boom ***" in printed
    assert "captured ***" in printed
    assert SENTINEL not in printed, "the password reached pytest's output"


# ``-vvv`` under ``-q`` turns off pytest's truncation of locals, so they print through pprint instead of saferepr.
_LOCALS_RENDERINGS = pytest.mark.parametrize("verbosity", [(), ("-vvv",)], ids=["truncated", "untruncated"])


@_LOCALS_RENDERINGS
def test_a_credential_post_that_fails_never_prints_the_password_in_any_form(
    tmp_path: Path, verbosity: tuple[str, ...]
) -> None:
    """A password with URL-reserved characters, and the Keycloak credential POST failing inside ``Browser.request``
    (nothing listens on the form's action), under ``-l``: no raw, URL-encoded or repr-escaped form of the password,
    whole or in a ten-character piece, reaches pytest's output."""
    action = f"http://127.0.0.1:{_closed_port()}/realms/nebari/login-actions/authenticate?session_code=s"
    page = '<form id="kc-form-login" action="' + action + '" method="post"></form>'
    printed = _pytest_over(
        tmp_path,
        "from email.message import Message\n\n"
        "import nkp_probes\n\n"
        f"PASSWORD = {RESERVED!r}\n"
        f"PAGE = {page!r}\n\n\n"
        "def test_leak():\n"
        "    page = nkp_probes.Response(200, 'http://127.0.0.1/realms/nebari/protocol/openid-connect/auth', PAGE, "
        "Message())\n"
        "    password = nkp_probes.Secret(PASSWORD)\n"
        "    nkp_probes.submit_keycloak_login(nkp_probes.Browser(), page, username='admin', password=password)\n",
        *verbosity,
    )
    assert "did not connect" in printed, "the failure is inside the credential POST"
    leaks = _leaked(printed, RESERVED, fragment=10)
    assert not leaks, f"the password reached pytest's output: {leaks}"


@_LOCALS_RENDERINGS
def test_a_token_response_that_fails_its_check_never_prints_a_token(tmp_path: Path, verbosity: tuple[str, ...]) -> None:
    """The token endpoint answers an access, a refresh and an ID token, and the access token's claims do not parse,
    under ``-l``: no token, and not the access token's signature on its own, reaches pytest's output."""
    signature = "s1gnature-118-6-never-printed"
    tokens = {
        "access_token": f"eyJhbGciOiJub25lIn0.{_b64url(b'not json')}.{signature}",
        "refresh_token": "r3fresh-t0ken-118-6-never-printed",
        "id_token": "1d-t0ken-118-6-never-printed",
        "token_type": "Bearer",
    }
    printed = _pytest_over(
        tmp_path,
        "import json\n"
        "import urllib.parse\n"
        "from email.message import Message\n\n"
        "import nkp_probes\n\n"
        f"TOKENS = {tokens!r}\n\n\n"
        "class StandInKeycloak:\n"
        "    def request(self, method, url, **kwargs):\n"
        "        if url.endswith('/.well-known/openid-configuration'):\n"
        "            endpoints = {'authorization_endpoint': 'https://kc.test/auth', "
        "'token_endpoint': 'https://kc.test/token'}\n"
        "            return nkp_probes.Response(200, url, json.dumps(endpoints), Message())\n"
        "        if url.startswith('https://kc.test/auth?'):\n"
        "            state = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)['state'][0]\n"
        "            headers = Message()\n"
        "            headers['Location'] = 'https://landing.test/?' + urllib.parse.urlencode("
        "{'state': state, 'code': 'c0de'})\n"
        "            return nkp_probes.Response(302, url, '', headers)\n"
        "        return nkp_probes.Response(200, url, json.dumps(TOKENS), Message())\n\n\n"
        "def test_leak():\n"
        "    nkp_probes.keycloak_pkce_signin(\n"
        "        StandInKeycloak(), issuer='https://kc.test/realms/nebari', client_id='c', "
        "redirect_uri='https://landing.test/',\n"
        "        username='admin', password=nkp_probes.Secret('pw-118-6-x'),\n"
        "    )\n",
        *verbosity,
    )
    assert "payload is not JSON" in printed, "the failure is the token's claims check"
    leaks = _leaked(printed, tokens["access_token"], tokens["refresh_token"], tokens["id_token"], signature)
    assert not leaks, f"a token reached pytest's output: {leaks}"


# ---------------------------------------------------------------------------
# AC2: the sign-in sends the password to Keycloak alone
# ---------------------------------------------------------------------------


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


class _KeycloakServer(ThreadingHTTPServer):
    def __init__(self, password: str) -> None:
        super().__init__(("127.0.0.1", 0), _FakeKeycloak)
        self.password = password
        self.pending: dict[str, str] = {}
        self.passwords: list[str | None] = []
        self.landed = False

    @property
    def base(self) -> str:
        return f"http://127.0.0.1:{self.server_address[1]}"


class _FakeKeycloak(BaseHTTPRequestHandler):
    """Realm ``nebari``'s discovery, sign-in form, sign-in POST and token endpoint, enough for one PKCE flow."""

    server: _KeycloakServer

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _send(
        self, status: int, body: str = "", *, ctype: str = "text/html", headers: tuple[tuple[str, str], ...] = ()
    ):
        raw = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        for name, value in headers:
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        url = urllib.parse.urlsplit(self.path)
        realm = "/realms/nebari"
        if url.path == f"{realm}/.well-known/openid-configuration":
            endpoints = {
                "authorization_endpoint": f"{self.server.base}{realm}/protocol/openid-connect/auth",
                "token_endpoint": f"{self.server.base}{realm}/protocol/openid-connect/token",
            }
            self._send(200, json.dumps(endpoints), ctype="application/json")
        elif url.path == f"{realm}/protocol/openid-connect/auth":
            self.server.pending = {key: values[0] for key, values in urllib.parse.parse_qs(url.query).items()}
            form = (
                "<html><head><title>Sign in to Nebari</title></head><body>"
                '<form id="kc-form-login" action="/realms/nebari/login-actions/authenticate?session_code=s&amp;'
                'execution=e&amp;client_id=c&amp;tab_id=t" method="post"></form></body></html>'
            )
            self._send(200, form, headers=(("Set-Cookie", "AUTH_SESSION_ID=abc; Path=/"),))
        else:
            self.server.landed = True
            self._send(200, "<title>landing</title>")

    def do_POST(self) -> None:
        url = urllib.parse.urlsplit(self.path)
        length = int(self.headers.get("Content-Length") or 0)
        query = urllib.parse.parse_qs(self.rfile.read(length).decode("utf-8"), keep_blank_values=True)
        form = {key: values[0] for key, values in query.items()}
        pending = self.server.pending
        if url.path.endswith("/login-actions/authenticate"):
            self.server.passwords.append(form.get("password"))
            signed_in = form.get("password") == self.server.password
            if signed_in and "AUTH_SESSION_ID=abc" in (self.headers.get("Cookie") or ""):
                back = urllib.parse.urlencode({"state": pending["state"], "code": "the-code", "session_state": "x"})
                self._send(302, headers=(("Location", f"{pending['redirect_uri']}?{back}"),))
            else:
                self._send(
                    200,
                    '<title>Sign in to Nebari</title><span id="input-error" class="x">Invalid username or password.'
                    '</span><form action="/realms/nebari/login-actions/authenticate?x=1"></form>',
                )
        elif url.path.endswith("/protocol/openid-connect/token"):
            verifier = form.get("code_verifier", "")
            challenge = _b64url(hashlib.sha256(verifier.encode("ascii")).digest())
            if (
                form.get("code") == "the-code"
                and challenge == pending.get("code_challenge")
                and form.get("redirect_uri") == pending.get("redirect_uri")
            ):
                payload = _b64url(json.dumps({"preferred_username": "admin"}).encode("utf-8"))
                token = {"access_token": f"eyJhbGciOiJub25lIn0.{payload}.signature"}
                self._send(200, json.dumps(token), ctype="application/json")
            else:
                self._send(400, json.dumps({"error": "invalid_grant"}), ctype="application/json")
        else:
            self._send(404)


@pytest.fixture
def keycloak() -> Iterator[_KeycloakServer]:
    server = _KeycloakServer(SENTINEL)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()


def _signin(keycloak: _KeycloakServer, password: str) -> nkp_probes.SignIn:
    return nkp_probes.keycloak_pkce_signin(
        nkp_probes.Browser(),
        issuer=f"{keycloak.base}/realms/nebari",
        client_id=nkp_probes.LANDING_CLIENT_ID,
        redirect_uri=f"{keycloak.base}/",
        username=nkp_probes.ADMIN_USER,
        password=nkp_probes.Secret(password),
    )


def test_the_pkce_sign_in_sends_the_password_to_keycloak_alone(
    keycloak: _KeycloakServer, capfd: pytest.CaptureFixture[str]
) -> None:
    signin = _signin(keycloak, SENTINEL)
    assert signin.claims["preferred_username"] == "admin"
    assert keycloak.passwords == [SENTINEL]
    assert keycloak.pending["code_challenge_method"] == "S256"
    assert keycloak.pending["client_id"] == "nebari-system-nebari-landing-spa"
    assert not keycloak.landed, "the redirect is read, never followed into the SPA"
    out, err = capfd.readouterr()
    assert SENTINEL not in out + err + repr(signin)


def test_a_refused_sign_in_names_keycloak_s_message_without_the_password(
    keycloak: _KeycloakServer, capfd: pytest.CaptureFixture[str]
) -> None:
    wrong = f"wr0ng-{SENTINEL}"
    with pytest.raises(nkp_probes.ProbeError) as raised:
        _signin(keycloak, wrong)
    message = str(raised.value)
    assert "Invalid username or password." in message
    out, err = capfd.readouterr()
    assert wrong not in message + out + err


def test_an_answer_that_is_not_http_fails_as_a_probe_error() -> None:
    """A malformed answer is a ProbeError raised from ``Browser.request``, never http.client's own exception: that one
    would carry urllib's frames into the traceback, and their request headers hold the session cookies."""
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()

        def answer() -> None:
            connection, _ = listener.accept()
            with connection:
                connection.recv(65536)
                connection.sendall(b"NOT-HTTP\r\n\r\n")

        thread = threading.Thread(target=answer, daemon=True)
        thread.start()
        with pytest.raises(nkp_probes.ProbeError):
            nkp_probes.Browser(timeout=5).request("GET", f"http://127.0.0.1:{listener.getsockname()[1]}/")
        thread.join(5)


# ---------------------------------------------------------------------------
# AC3: no cluster, no secrets asked for, a reason named
# ---------------------------------------------------------------------------


class _Runner:
    def __init__(self, *answers: subprocess.CompletedProcess[str]) -> None:
        self.answers = list(answers)
        self.calls: list[list[str]] = []

    def __call__(self, argv: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
        self.calls.append(argv)
        return self.answers.pop(0)


def _done(returncode: int = 0, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


def _config(tmp_path: Path, text: str = "domain: nebari.local\ncertificate:\n  type: selfsigned\n") -> Path:
    path = tmp_path / "my-nebari.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def _kubeconfig(port: int) -> str:
    return (
        "apiVersion: v1\nkind: Config\ncurrent-context: kind-my-nebari-local\n"
        f"clusters:\n- name: kind-my-nebari-local\n  cluster:\n    server: https://127.0.0.1:{port}\n"
        "contexts:\n- name: kind-my-nebari-local\n  context:\n    cluster: kind-my-nebari-local\n    user: u\n"
        "users:\n- name: u\n  user:\n    client-key-data: bm90LWEta2V5\n"
    )


def _closed_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def test_a_missing_config_skips(tmp_path: Path) -> None:
    runner = _Runner()
    with pytest.raises(nkp_probes.ClusterAbsent, match="does not exist"):
        nkp_probes.connect(Path("absent.yaml"), root=tmp_path, nic="/fake/nic", runner=runner)
    assert runner.calls == []


def test_without_nic_the_probes_skip(tmp_path: Path) -> None:
    runner = _Runner()
    with pytest.raises(nkp_probes.ClusterAbsent, match="nic is not installed"):
        nkp_probes.connect(_config(tmp_path), root=tmp_path, runner=runner, environ={"PATH": str(tmp_path)})
    assert runner.calls == []


def test_a_config_whose_credentials_do_not_resolve_skips_naming_them(tmp_path: Path) -> None:
    config = _config(
        tmp_path, "domain: example.org\nrepository:\n  git:\n    auth:\n      token:\n        env: GIT_TOKEN\n"
    )
    runner = _Runner()
    with pytest.raises(nkp_probes.ClusterAbsent, match="GIT_TOKEN"):
        nkp_probes.connect(config, root=tmp_path, nic="/fake/nic", runner=runner)
    assert runner.calls == []


def test_when_nic_finds_no_cluster_the_probes_skip_with_nic_s_error(tmp_path: Path) -> None:
    config = _config(tmp_path)
    error = json.dumps(
        {"level": "ERROR", "error": "get kubeconfig: could not locate any control plane nodes for cluster named 'x'"}
    )
    runner = _Runner(_done(1, stderr=f'{{"level":"INFO","msg":"Configuration validated"}}\n{error}\n'))
    with pytest.raises(nkp_probes.ClusterAbsent) as raised:
        nkp_probes.connect(config, root=tmp_path, nic="/fake/nic", runner=runner)
    assert "no reachable kubeconfig" in str(raised.value)
    assert "could not locate any control plane nodes" in str(raised.value)
    assert runner.calls == [["/fake/nic", "kubeconfig", "-f", str(config)]], "outputs is never asked for"


def test_an_api_server_that_does_not_answer_skips(tmp_path: Path) -> None:
    port = _closed_port()
    runner = _Runner(_done(0, stdout=_kubeconfig(port)))
    with pytest.raises(nkp_probes.ClusterAbsent, match=f"127.0.0.1:{port} does not answer"):
        nkp_probes.connect(_config(tmp_path), root=tmp_path, nic="/fake/nic", runner=runner)
    assert len(runner.calls) == 1, "outputs is never asked for"


def test_a_kubeconfig_that_is_not_yaml_skips_without_echoing_it(tmp_path: Path) -> None:
    runner = _Runner(_done(0, stdout="client-key-data: [unclosed\n  - bm90LWEta2V5"))
    with pytest.raises(nkp_probes.ClusterAbsent) as raised:
        nkp_probes.connect(_config(tmp_path), root=tmp_path, nic="/fake/nic", runner=runner)
    assert "bm90LWEta2V5" not in str(raised.value)


def test_a_reachable_cluster_reads_its_outputs_with_show_secrets_from_the_config(tmp_path: Path) -> None:
    config = _config(tmp_path)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        runner = _Runner(_done(0, stdout=_kubeconfig(listener.getsockname()[1])), _done(0, stdout=_outputs_json()))
        cluster = nkp_probes.connect(config, root=tmp_path, nic="/fake/nic", runner=runner, connect_to="127.0.0.1")
    assert runner.calls[1] == ["/fake/nic", "outputs", "--format", "json", "--show-secrets", "-f", str(config)]
    assert cluster.outputs.domain == "nebari.local"
    assert cluster.verify_tls is False, "the kind profile's selfsigned certificate is not verified"
    assert cluster.connect_to == "127.0.0.1"
    assert SENTINEL not in repr(cluster)


def test_a_real_certificate_is_verified() -> None:
    assert nkp_probes.verifies_tls({"certificate": {"type": "lets-encrypt"}}) is True
    assert nkp_probes.verifies_tls({}) is True
    assert nkp_probes.verifies_tls({"certificate": {"type": "selfsigned"}}) is False


# ---------------------------------------------------------------------------
# The spawn and the cards, against stand-ins
# ---------------------------------------------------------------------------


class _FakeHub:
    """Answers ``GET /hub/api/user`` with each scripted user model in turn (the last one repeats)."""

    def __init__(self, *users: dict[str, Any]) -> None:
        self.users = list(users)
        self.calls: list[tuple[str, str, dict[str, str], dict[str, str]]] = []

    def cookie(self, name: str) -> str | None:
        return "xsrf-value" if name == "_xsrf" else None

    def request(self, method: str, url: str, **kwargs: Any) -> nkp_probes.Response:
        path = urllib.parse.urlsplit(url).path
        self.calls.append((method, path, dict(kwargs.get("form") or {}), dict(kwargs.get("headers") or {})))
        body = json.dumps(self.users.pop(0) if len(self.users) > 1 else self.users[0]) if method == "GET" else ""
        return nkp_probes.Response(202 if method == "DELETE" else 200, url, body, Message())


_OUTPUTS = nkp_probes.NkpOutputs(
    domain="nebari.local", keycloak_url="https://keycloak.nebari.local", admin_password=nkp_probes.Secret("pw-xyz-9")
)


def test_the_spawn_posts_the_profile_waits_for_ready_and_stops_the_server() -> None:
    hub = _FakeHub(
        {"name": "admin", "servers": {}},
        {"name": "admin", "servers": {"": {"ready": False, "pending": "spawn"}}},
        {
            "name": "admin",
            "servers": {"": {"ready": True, "pending": None, "user_options": {"profile": "small-instance"}}},
        },
    )
    server = nkp_probes.spawn_and_stop(hub, _OUTPUTS, sleep=lambda _seconds: None)  # type: ignore[arg-type]
    assert server["ready"] is True
    posts = [call for call in hub.calls if call[0] == "POST"]
    assert posts == [("POST", "/hub/spawn", {"profile": "small-instance", "_xsrf": "xsrf-value"}, posts[0][3])]
    assert posts[0][3]["X-XSRFToken"] == "xsrf-value"
    assert hub.calls[-1][:2] == ("DELETE", "/hub/api/users/admin/server")


def test_the_spawn_refuses_a_server_the_admin_already_runs() -> None:
    hub = _FakeHub({"name": "admin", "servers": {"": {"ready": True, "pending": None}}})
    with pytest.raises(nkp_probes.ProbeError, match="already has a default server"):
        nkp_probes.spawn_and_stop(hub, _OUTPUTS, sleep=lambda _seconds: None)  # type: ignore[arg-type]
    assert [call[0] for call in hub.calls] == ["GET"], "nothing is spawned or stopped"


def test_a_spawn_that_dies_before_ready_fails_and_is_still_stopped() -> None:
    hub = _FakeHub(
        {"name": "admin", "servers": {}},
        {"name": "admin", "servers": {"": {"ready": False, "pending": "spawn"}}},
        {"name": "admin", "servers": {}},
    )
    with pytest.raises(nkp_probes.ProbeError, match="stopped before it was ready"):
        nkp_probes.spawn_and_stop(hub, _OUTPUTS, sleep=lambda _seconds: None)  # type: ignore[arg-type]
    assert hub.calls[-1][:2] == ("DELETE", "/hub/api/users/admin/server")


def test_the_default_server_reads_the_servers_map_or_the_older_fields() -> None:
    assert nkp_probes.default_server({"servers": {}}) is None
    assert nkp_probes.default_server({"servers": {"": {"ready": True}}}) == {"ready": True}
    assert nkp_probes.default_server({"server": "/user/admin/", "pending": None}) == {"ready": True, "pending": None}
    assert nkp_probes.default_server({"server": None, "pending": None}) is None


def test_the_card_check_reads_both_answer_shapes() -> None:
    wrapped = {
        "services": [
            {"displayName": "JupyterHub", "url": "https://hub.nebari.local", "health": {"status": "healthy"}},
            {"displayName": "Nebi", "url": "https://nebi.nebari.local", "health": {"status": "unhealthy"}},
        ]
    }
    assert nkp_probes.card_problems(nkp_probes.parse_cards(wrapped)) == ["Nebi: unhealthy"]
    bare = [{"name": "jupyterhub", "status": "healthy"}, {"name": "Nebi", "status": "healthy"}]
    assert nkp_probes.card_problems(nkp_probes.parse_cards(bare)) == []
    assert nkp_probes.card_problems([]) == ["JupyterHub: no card", "Nebi: no card"]
