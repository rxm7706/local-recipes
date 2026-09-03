"""Story 41.4 / CAP-12: a ``rediss://`` broker is verified, not just encrypted.

Red-team X-2 → directive R-14. Three acceptance criteria, each covered twice —
once against ``config.broker_tls`` directly (the composition unit) and once
against a real child process that loads the settings module (the boot the
operator actually gets):

1. production + ``rediss://`` → ``CERT_REQUIRED`` and the CA trust source at the
   configured bundle, for the broker *and* the result backend;
2. deployed + a verification-disabling policy → stage 1 refuses by name, and
   that refusal reaches the exit status of every entrypoint;
3. the laptop profile → ``CERT_NONE`` still works for a self-signed local Redis.

``COMPONENT_RUNTIME`` is deleted rather than set to a deployed value because
locality fails closed (absent == deployed), mirroring
``test_startup_required_settings.py``.
"""

from __future__ import annotations

import json
import os
import ssl
import subprocess
import sys
from pathlib import Path
from types import MappingProxyType
from types import ModuleType

import pytest
from django.core.exceptions import ImproperlyConfigured

from config import broker_tls
from config.locality import LOCAL
from config.locality import RUNTIME_ENV_VAR
from config.startup import refuse_unverified_broker_tls
from config.startup import run_stage_one

PLATFORM_ROOT = Path(__file__).resolve().parents[1]

TLS_BROKER_URL = "rediss://broker.platform.internal:6379/0"
PLAIN_BROKER_URL = "redis://broker.platform.internal:6379/0"

#: Paths that cannot resolve, used to blank a trust tier under test.
MISSING_BUNDLE = "/nonexistent/corporate-ca.pem"
MISSING_CA_DIR = "/nonexistent/certs.d"

#: Enough of a deployed env for ``config.settings.production`` to import.
DEPLOYED_REQUIRED_ENV = {
    "DJANGO_SETTINGS_MODULE": "config.settings.production",
    "DJANGO_SECRET_KEY": "story-41-4-test-secret-key-not-for-production-use",
    "DJANGO_ADMIN_URL": "secret-admin/",
    "MCP_HOST_SIDECAR_BASE_URL": "http://platform-mcp-host:8090",
    "COMPONENT_OIDC_ISSUER": "https://idp.invalid/realms/platform",
    "COMPONENT_OIDC_JWKS_URL": "https://idp.invalid/realms/platform/certs",
    "COMPONENT_OIDC_AUDIENCE": "platform-web",
}

#: Loads the settings module for real and reports the composed TLS posture.
SETTINGS_PROBE = (
    "import django, json;"
    "django.setup();"
    "from django.conf import settings;"
    "opts = settings.CELERY_BROKER_USE_SSL;"
    "print(json.dumps({"
    "'broker': None if opts is None else {"
    "'ssl_cert_reqs': int(opts['ssl_cert_reqs']),"
    "'ssl_ca_certs': opts.get('ssl_ca_certs'),"
    "'ssl_ca_path': opts.get('ssl_ca_path')},"
    "'backend_matches_broker': settings.CELERY_REDIS_BACKEND_USE_SSL == opts,"
    "}))"
)

#: Every env key a child process must not inherit from the developer/CI shell.
#: ``DJANGO_READ_DOT_ENV_FILE`` matters as much as the broker keys: with it on,
#: ``read_dot_env()`` re-supplies ``.env`` entries into the child, which could
#: hand back ``COMPONENT_RUNTIME`` or a broker URL and make a refusal test pass
#: for the wrong reason — or, worse, make its control pass for the wrong reason.
CONTROLLED_ENV_KEYS = (
    broker_tls.BROKER_URL_ENV_VAR,
    broker_tls.REDIS_URL_ENV_VAR,
    broker_tls.CERT_REQS_ENV_VAR,
    broker_tls.CA_BUNDLE_ENV_VAR,
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
    RUNTIME_ENV_VAR,
    "COMPONENT_PROCESS",
    "DJANGO_READ_DOT_ENV_FILE",
    *DEPLOYED_REQUIRED_ENV,
)

#: Entrypoints that must surface a stage-1 refusal in their exit status.
#: ``config.asgi`` is deliberately absent: it imports ``langflow_integration``,
#: which needs the ``python-agent-platform`` env, not ``platform-ci-test``.
ENTRYPOINT_ARGV = {
    "manage.py": ["manage.py", "check"],
    "wsgi": ["-c", "import config.wsgi"],
    "celery_app": ["-c", "import config.celery_app"],
}


@pytest.fixture(autouse=True)
def _clean_broker_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Deployed locality and no inherited broker/TLS env from the test host."""
    for key in CONTROLLED_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


@pytest.fixture
def corporate_bundle(tmp_path: Path) -> Path:
    """A file that stands in for the corporate CA bundle (never parsed here)."""
    bundle = tmp_path / "corporate-ca.pem"
    bundle.write_text("-----BEGIN CERTIFICATE-----\n", encoding="utf-8")
    return bundle


@pytest.fixture
def explicit_bundle(tmp_path: Path) -> Path:
    """A second bundle, used to prove the OS trust store is consulted first."""
    bundle = tmp_path / "explicit-ca.pem"
    bundle.write_text("-----BEGIN CERTIFICATE-----\n", encoding="utf-8")
    return bundle


@pytest.fixture
def corporate_ca_dir(tmp_path: Path) -> Path:
    """A hashed CA directory — the other half of the OS trust store."""
    ca_dir = tmp_path / "certs.d"
    ca_dir.mkdir()
    hashed = ca_dir / "a1b2c3d4.0"
    hashed.write_text("-----BEGIN CERTIFICATE-----\n", encoding="utf-8")
    return ca_dir


def _child_env(overrides: dict[str, str]) -> dict[str, str]:
    """A child-process env with every broker/TLS key under this test's control."""
    env = dict(os.environ)
    for key in CONTROLLED_ENV_KEYS:
        env.pop(key, None)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(PLATFORM_ROOT), *(entry for entry in sys.path if entry)],
    )
    env.update(overrides)
    return env


def _run_child(
    argv: list[str],
    overrides: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    """Run *argv* under a controlled env from the platform root."""
    return subprocess.run(  # noqa: S603 -- fixed argv, no shell, no untrusted input
        [sys.executable, *argv],
        check=False,
        capture_output=True,
        text=True,
        timeout=300,
        cwd=PLATFORM_ROOT,
        env=_child_env(overrides),
    )


def _run_probe(overrides: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """Load settings in a child process; return the completed probe run."""
    return _run_child(["-c", SETTINGS_PROBE], overrides)


def _deployed_env(**overrides: str) -> dict[str, str]:
    return {**DEPLOYED_REQUIRED_ENV, **overrides}


def _with_extra_policy(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    mode: ssl.VerifyMode,
) -> None:
    """Add a policy rung to the declared table for the duration of one test."""
    monkeypatch.setattr(
        broker_tls,
        "CERT_REQS_BY_NAME",
        MappingProxyType({**broker_tls.CERT_REQS_BY_NAME, name: mode}),
    )


def _settings_stub(broker_url: str | None) -> ModuleType:
    """A stand-in leaf settings module carrying only ``CELERY_BROKER_URL``."""
    module = ModuleType("config.settings.production")
    if broker_url is not None:
        module.CELERY_BROKER_URL = broker_url
    return module


# --- AC1: production + rediss:// is verified against the configured trust ---


def test_tls_broker_composes_cert_required_and_the_bundle(
    monkeypatch: pytest.MonkeyPatch,
    corporate_bundle: Path,
) -> None:
    monkeypatch.setenv("SSL_CERT_FILE", str(corporate_bundle))
    monkeypatch.setenv("SSL_CERT_DIR", MISSING_CA_DIR)

    options = broker_tls.broker_use_ssl(TLS_BROKER_URL)

    assert options == {
        "ssl_cert_reqs": ssl.CERT_REQUIRED,
        "ssl_ca_certs": str(corporate_bundle),
    }


def test_os_trust_store_is_consulted_before_the_explicit_bundle(
    monkeypatch: pytest.MonkeyPatch,
    corporate_bundle: Path,
    explicit_bundle: Path,
) -> None:
    monkeypatch.setenv("SSL_CERT_FILE", str(corporate_bundle))
    monkeypatch.setenv("SSL_CERT_DIR", MISSING_CA_DIR)
    monkeypatch.setenv(broker_tls.CA_BUNDLE_ENV_VAR, str(explicit_bundle))

    assert broker_tls.resolve_ca_trust() == broker_tls.CaTrust(
        cafile=str(corporate_bundle),
    )


def test_explicit_bundle_is_the_second_tier(
    monkeypatch: pytest.MonkeyPatch,
    explicit_bundle: Path,
) -> None:
    monkeypatch.setenv("SSL_CERT_FILE", MISSING_BUNDLE)
    monkeypatch.setenv("SSL_CERT_DIR", MISSING_CA_DIR)
    monkeypatch.setenv(broker_tls.CA_BUNDLE_ENV_VAR, str(explicit_bundle))

    assert broker_tls.resolve_ca_trust() == broker_tls.CaTrust(
        cafile=str(explicit_bundle),
    )


def test_hashed_ca_directory_is_part_of_the_os_tier(
    monkeypatch: pytest.MonkeyPatch,
    corporate_ca_dir: Path,
) -> None:
    """A host with SSL_CERT_DIR and no bundled cert.pem is correctly configured.

    ``update-ca-certificates``-style installs land here, so refusing it would
    reject a component whose operator did install the corporate CA properly.
    """
    monkeypatch.setenv("SSL_CERT_FILE", MISSING_BUNDLE)
    monkeypatch.setenv("SSL_CERT_DIR", str(corporate_ca_dir))

    assert broker_tls.resolve_ca_trust() == broker_tls.CaTrust(
        capath=str(corporate_ca_dir),
    )


def test_capath_only_composes_ssl_ca_path(
    monkeypatch: pytest.MonkeyPatch,
    corporate_ca_dir: Path,
) -> None:
    """redis-py 8.1 takes ``ssl_ca_path`` and feeds it to ``load_verify_locations``."""
    monkeypatch.setenv("SSL_CERT_FILE", MISSING_BUNDLE)
    monkeypatch.setenv("SSL_CERT_DIR", str(corporate_ca_dir))

    assert broker_tls.broker_use_ssl(TLS_BROKER_URL) == {
        "ssl_cert_reqs": ssl.CERT_REQUIRED,
        "ssl_ca_path": str(corporate_ca_dir),
    }


def test_both_os_halves_compose_together(
    monkeypatch: pytest.MonkeyPatch,
    corporate_bundle: Path,
    corporate_ca_dir: Path,
) -> None:
    monkeypatch.setenv("SSL_CERT_FILE", str(corporate_bundle))
    monkeypatch.setenv("SSL_CERT_DIR", str(corporate_ca_dir))

    assert broker_tls.broker_use_ssl(TLS_BROKER_URL) == {
        "ssl_cert_reqs": ssl.CERT_REQUIRED,
        "ssl_ca_certs": str(corporate_bundle),
        "ssl_ca_path": str(corporate_ca_dir),
    }


def test_redis_py_accepts_the_kwargs_we_compose(
    monkeypatch: pytest.MonkeyPatch,
    corporate_bundle: Path,
    corporate_ca_dir: Path,
) -> None:
    """The composed mapping must be constructor-valid for redis-py's SSLConnection.

    kombu merges ``broker_use_ssl`` into the connection kwargs verbatim
    (``connparams.update(conninfo.ssl)``), as does celery's Redis result backend
    for ``redis_backend_use_ssl`` — so an unsupported key here is a runtime
    TypeError at first connect, not a config warning.
    """
    redis_connection = pytest.importorskip("redis.connection")
    monkeypatch.setenv("SSL_CERT_FILE", str(corporate_bundle))
    monkeypatch.setenv("SSL_CERT_DIR", str(corporate_ca_dir))

    options = broker_tls.broker_use_ssl(TLS_BROKER_URL)

    assert options is not None
    connection = redis_connection.SSLConnection(**options)
    assert connection.ca_certs == str(corporate_bundle)
    assert connection.ca_path == str(corporate_ca_dir)


def test_unreadable_paths_resolve_to_no_trust(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SSL_CERT_FILE", MISSING_BUNDLE)
    monkeypatch.setenv("SSL_CERT_DIR", MISSING_CA_DIR)
    monkeypatch.setenv(broker_tls.CA_BUNDLE_ENV_VAR, MISSING_BUNDLE)

    assert not broker_tls.resolve_ca_trust()


@pytest.mark.skipif(
    os.geteuid() == 0,
    reason="root bypasses the read permission bit this asserts on",
)
def test_existing_but_unreadable_bundle_is_not_trusted(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Existence is not readability — a chmod-000 bundle fails at first connect."""
    bundle = tmp_path / "unreadable-ca.pem"
    bundle.write_text("-----BEGIN CERTIFICATE-----\n", encoding="utf-8")
    bundle.chmod(0o000)
    monkeypatch.setenv("SSL_CERT_FILE", str(bundle))
    monkeypatch.setenv("SSL_CERT_DIR", MISSING_CA_DIR)

    assert not broker_tls.resolve_ca_trust()


def test_plain_broker_has_no_ssl_options() -> None:
    assert broker_tls.broker_use_ssl(PLAIN_BROKER_URL) is None


@pytest.mark.parametrize(
    "url",
    [
        "rediss://broker:6379/0",
        "REDISS://broker:6379/0",
        "Rediss://broker:6379/0",
    ],
    ids=["lower", "upper", "mixed"],
)
def test_tls_scheme_is_case_insensitive(
    monkeypatch: pytest.MonkeyPatch,
    corporate_bundle: Path,
    url: str,
) -> None:
    """urlparse/kombu/celery normalise the scheme, so this site must too.

    An uppercase ``REDISS://`` reaches kombu's ``rediss`` transport either way;
    composing no options for it produces exactly the warning that names the
    hole this story closes ("Secure redis scheme specified (rediss) with no ssl
    options, defaulting to insecure SSL behaviour").
    """
    monkeypatch.setenv("SSL_CERT_FILE", str(corporate_bundle))
    monkeypatch.setenv("SSL_CERT_DIR", MISSING_CA_DIR)

    assert broker_tls.is_tls_broker(url) is True
    assert broker_tls.broker_use_ssl(url) == {
        "ssl_cert_reqs": ssl.CERT_REQUIRED,
        "ssl_ca_certs": str(corporate_bundle),
    }


def test_production_settings_verify_a_rediss_broker(
    corporate_bundle: Path,
) -> None:
    """AC1, end to end: the composed setting a deployed worker actually gets."""
    result = _run_probe(
        _deployed_env(
            REDIS_BROKER_URL=TLS_BROKER_URL,
            SSL_CERT_FILE=str(corporate_bundle),
            SSL_CERT_DIR=MISSING_CA_DIR,
        ),
    )

    assert result.returncode == 0, result.stderr
    composed = json.loads(result.stdout)
    assert composed["broker"] == {
        "ssl_cert_reqs": int(ssl.CERT_REQUIRED),
        "ssl_ca_certs": str(corporate_bundle),
        "ssl_ca_path": None,
    }
    assert composed["backend_matches_broker"] is True


# --- The broker URL stage 1 checks is the one Celery connects with ---


def test_broker_url_prefers_the_composed_setting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """django-environ's FileAwareMapping can disagree with a raw os.environ read."""
    monkeypatch.setenv(broker_tls.BROKER_URL_ENV_VAR, PLAIN_BROKER_URL)

    assert (
        broker_tls.broker_url_from_settings(_settings_stub(TLS_BROKER_URL))
        == TLS_BROKER_URL
    )


def test_broker_url_falls_back_to_env_without_a_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(broker_tls.BROKER_URL_ENV_VAR, TLS_BROKER_URL)

    assert broker_tls.broker_url_from_settings(None) == TLS_BROKER_URL
    assert broker_tls.broker_url_from_settings(_settings_stub(None)) == TLS_BROKER_URL


def test_stage_one_reads_the_composed_url_not_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A plain env URL must not excuse a composed TLS one with no trust source."""
    monkeypatch.setenv(broker_tls.BROKER_URL_ENV_VAR, PLAIN_BROKER_URL)
    monkeypatch.setenv("SSL_CERT_FILE", MISSING_BUNDLE)
    monkeypatch.setenv("SSL_CERT_DIR", MISSING_CA_DIR)

    with pytest.raises(ImproperlyConfigured) as refused:
        refuse_unverified_broker_tls(_settings_stub(TLS_BROKER_URL))

    assert broker_tls.CA_BUNDLE_ENV_VAR in str(refused.value)


# --- The REDIS_URL-only shape (compose.yml sets no REDIS_BROKER_URL) ---


def test_redis_url_alone_drives_the_posture(
    monkeypatch: pytest.MonkeyPatch,
    corporate_bundle: Path,
) -> None:
    monkeypatch.setenv(broker_tls.REDIS_URL_ENV_VAR, TLS_BROKER_URL)
    monkeypatch.setenv("SSL_CERT_FILE", str(corporate_bundle))
    monkeypatch.setenv("SSL_CERT_DIR", MISSING_CA_DIR)

    assert broker_tls.broker_url_from_env() == TLS_BROKER_URL
    assert broker_tls.broker_use_ssl(broker_tls.broker_url_from_env()) == {
        "ssl_cert_reqs": ssl.CERT_REQUIRED,
        "ssl_ca_certs": str(corporate_bundle),
    }
    refuse_unverified_broker_tls()


def test_stage_one_sees_a_tls_redis_url_with_no_trust(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(broker_tls.REDIS_URL_ENV_VAR, TLS_BROKER_URL)
    monkeypatch.setenv("SSL_CERT_FILE", MISSING_BUNDLE)
    monkeypatch.setenv("SSL_CERT_DIR", MISSING_CA_DIR)

    with pytest.raises(ImproperlyConfigured) as refused:
        refuse_unverified_broker_tls()

    assert broker_tls.REDIS_URL_ENV_VAR in str(refused.value)


def test_production_settings_verify_a_redis_url_only_broker(
    corporate_bundle: Path,
) -> None:
    """End to end for the compose.yml shape: REDIS_URL, no REDIS_BROKER_URL."""
    result = _run_probe(
        _deployed_env(
            REDIS_URL=TLS_BROKER_URL,
            SSL_CERT_FILE=str(corporate_bundle),
            SSL_CERT_DIR=MISSING_CA_DIR,
        ),
    )

    assert result.returncode == 0, result.stderr
    composed = json.loads(result.stdout)
    assert composed["broker"]["ssl_cert_reqs"] == int(ssl.CERT_REQUIRED)
    assert composed["broker"]["ssl_ca_certs"] == str(corporate_bundle)


# --- AC2: deployed + verification disabled → stage 1 refuses ---


def test_stage_one_refuses_cert_none_when_deployed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(broker_tls.CERT_REQS_ENV_VAR, broker_tls.UNVERIFIED)

    with pytest.raises(ImproperlyConfigured) as refused:
        refuse_unverified_broker_tls()

    message = str(refused.value)
    assert broker_tls.CERT_REQS_ENV_VAR in message
    assert f"{RUNTIME_ENV_VAR}={LOCAL}" in message


def test_stage_one_refuses_any_policy_weaker_than_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Drift guard: the deployed refusal branches on the mode, not the name.

    A weaker rung added to ``CERT_REQS_BY_NAME`` later must be refused when
    deployed without anyone remembering to extend stage 1.
    """
    _with_extra_policy(monkeypatch, "optional", ssl.CERT_OPTIONAL)
    monkeypatch.setenv(broker_tls.CERT_REQS_ENV_VAR, "optional")

    with pytest.raises(ImproperlyConfigured) as refused:
        refuse_unverified_broker_tls()

    assert "optional" in str(refused.value)


def test_recognised_policy_maps_through_the_declared_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Composition reads the table's values, so keys and outcomes cannot drift."""
    _with_extra_policy(monkeypatch, "optional", ssl.CERT_OPTIONAL)
    monkeypatch.setenv(RUNTIME_ENV_VAR, LOCAL)
    monkeypatch.setenv(broker_tls.CERT_REQS_ENV_VAR, "optional")

    assert broker_tls.resolve_cert_reqs() == ssl.CERT_OPTIONAL


def test_stage_one_refuses_an_unrecognised_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(broker_tls.CERT_REQS_ENV_VAR, "nonee")

    with pytest.raises(ImproperlyConfigured) as refused:
        refuse_unverified_broker_tls()

    message = str(refused.value)
    assert broker_tls.CERT_REQS_ENV_VAR in message
    assert "nonee" in message
    assert broker_tls.VERIFIED in message


def test_deployed_unrecognised_policy_still_reaches_stage_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Composition must not pre-empt the stage-1 refusal when deployed.

    ``resolve_cert_reqs`` raises for an unrecognised value only when local; if
    it raised while deployed too, settings import would fail first and stage
    one's own named refusal would be dead code.
    """
    monkeypatch.setenv(broker_tls.CERT_REQS_ENV_VAR, "nonee")

    assert broker_tls.resolve_cert_reqs() == ssl.CERT_REQUIRED


def test_stage_one_refuses_a_tls_broker_with_no_trust(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(broker_tls.BROKER_URL_ENV_VAR, TLS_BROKER_URL)
    monkeypatch.setenv("SSL_CERT_FILE", MISSING_BUNDLE)
    monkeypatch.setenv("SSL_CERT_DIR", MISSING_CA_DIR)

    with pytest.raises(ImproperlyConfigured) as refused:
        refuse_unverified_broker_tls()

    message = str(refused.value)
    assert broker_tls.BROKER_URL_ENV_VAR in message
    assert broker_tls.CA_BUNDLE_ENV_VAR in message


def test_stage_one_accepts_a_tls_broker_trusted_by_capath_alone(
    monkeypatch: pytest.MonkeyPatch,
    corporate_ca_dir: Path,
) -> None:
    """The capath half must satisfy the gate, or the refusal is a false positive."""
    monkeypatch.setenv(broker_tls.BROKER_URL_ENV_VAR, TLS_BROKER_URL)
    monkeypatch.setenv("SSL_CERT_FILE", MISSING_BUNDLE)
    monkeypatch.setenv("SSL_CERT_DIR", str(corporate_ca_dir))

    refuse_unverified_broker_tls()


def test_stage_one_accepts_a_verified_tls_broker(
    monkeypatch: pytest.MonkeyPatch,
    corporate_bundle: Path,
) -> None:
    monkeypatch.setenv(broker_tls.BROKER_URL_ENV_VAR, TLS_BROKER_URL)
    monkeypatch.setenv("SSL_CERT_FILE", str(corporate_bundle))
    monkeypatch.setenv("SSL_CERT_DIR", MISSING_CA_DIR)

    refuse_unverified_broker_tls()


def test_stage_one_accepts_a_plain_broker_with_no_trust(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A non-TLS broker has no certificate to verify — not this check's business."""
    monkeypatch.setenv(broker_tls.BROKER_URL_ENV_VAR, PLAIN_BROKER_URL)
    monkeypatch.setenv("SSL_CERT_FILE", MISSING_BUNDLE)
    monkeypatch.setenv("SSL_CERT_DIR", MISSING_CA_DIR)

    refuse_unverified_broker_tls()


def test_broker_condition_is_wired_into_run_stage_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The refusal must fire through the real stage-1 entry point, not only alone."""
    for key, value in DEPLOYED_REQUIRED_ENV.items():
        if key != "DJANGO_SETTINGS_MODULE":
            monkeypatch.setenv(key, value)
    monkeypatch.setenv(broker_tls.CERT_REQS_ENV_VAR, broker_tls.UNVERIFIED)

    with pytest.raises(ImproperlyConfigured) as refused:
        run_stage_one(_settings_stub(TLS_BROKER_URL))

    assert broker_tls.CERT_REQS_ENV_VAR in str(refused.value)


def test_deployed_cert_none_request_never_composes_cert_none(
    monkeypatch: pytest.MonkeyPatch,
    corporate_bundle: Path,
) -> None:
    """Fail closed: composition itself refuses to emit CERT_NONE when deployed."""
    monkeypatch.setenv(broker_tls.CERT_REQS_ENV_VAR, broker_tls.UNVERIFIED)
    monkeypatch.setenv("SSL_CERT_FILE", str(corporate_bundle))

    options = broker_tls.broker_use_ssl(TLS_BROKER_URL)

    assert options is not None
    assert options["ssl_cert_reqs"] == ssl.CERT_REQUIRED


@pytest.mark.parametrize(
    "entrypoint",
    sorted(ENTRYPOINT_ARGV),
    ids=sorted(ENTRYPOINT_ARGV),
)
def test_every_entrypoint_surfaces_the_refusal(
    corporate_bundle: Path,
    entrypoint: str,
) -> None:
    """AC2, end to end: a deployed boot stops, at every process entrypoint.

    Behavioural replacement for a source-substring assertion: this fails if
    `wsgi.py`, `celery_app.py` or `manage.py` stops calling
    ``configure_observability()``, which is the regression that actually
    matters. (``config.asgi`` is excluded — it needs the langflow env.)
    """
    result = _run_child(
        ENTRYPOINT_ARGV[entrypoint],
        _deployed_env(
            REDIS_BROKER_URL=TLS_BROKER_URL,
            SSL_CERT_FILE=str(corporate_bundle),
            SSL_CERT_DIR=MISSING_CA_DIR,
            COMPONENT_BROKER_SSL_CERT_REQS=broker_tls.UNVERIFIED,
        ),
    )

    assert result.returncode != 0, result.stdout
    assert broker_tls.CERT_REQS_ENV_VAR in result.stderr
    assert "ImproperlyConfigured" in result.stderr


@pytest.mark.parametrize(
    "entrypoint",
    sorted(ENTRYPOINT_ARGV),
    ids=sorted(ENTRYPOINT_ARGV),
)
def test_every_entrypoint_boots_when_the_broker_is_verified(
    corporate_bundle: Path,
    entrypoint: str,
) -> None:
    """Control for the refusals above: same env minus the CERT_NONE request."""
    result = _run_child(
        ENTRYPOINT_ARGV[entrypoint],
        _deployed_env(
            REDIS_BROKER_URL=TLS_BROKER_URL,
            SSL_CERT_FILE=str(corporate_bundle),
            SSL_CERT_DIR=MISSING_CA_DIR,
        ),
    )

    assert result.returncode == 0, result.stderr


def test_required_settings_refusal_also_reaches_the_exit_code() -> None:
    """The same swallow hid the shipped ``DJANGO_SECRET_KEY`` refusal.

    Lives with the broker tests because it guards the identical fix; the
    required-settings contract itself is ``test_startup_required_settings.py``.
    """
    env = _deployed_env(REDIS_BROKER_URL=PLAIN_BROKER_URL)
    del env["DJANGO_SECRET_KEY"]

    result = _run_child(ENTRYPOINT_ARGV["manage.py"], env)

    assert result.returncode != 0, result.stdout
    assert "DJANGO_SECRET_KEY" in result.stderr


# --- AC3: the laptop profile keeps CERT_NONE for a self-signed local Redis ---


def test_local_profile_honours_cert_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(RUNTIME_ENV_VAR, LOCAL)
    monkeypatch.setenv(broker_tls.CERT_REQS_ENV_VAR, broker_tls.UNVERIFIED)

    assert broker_tls.broker_use_ssl(TLS_BROKER_URL) == {
        "ssl_cert_reqs": ssl.CERT_NONE,
    }


def test_local_profile_still_defaults_to_verified(
    monkeypatch: pytest.MonkeyPatch,
    corporate_bundle: Path,
) -> None:
    """``CERT_NONE`` is opt-in even locally — the default never stops verifying."""
    monkeypatch.setenv(RUNTIME_ENV_VAR, LOCAL)
    monkeypatch.setenv("SSL_CERT_FILE", str(corporate_bundle))
    monkeypatch.setenv("SSL_CERT_DIR", MISSING_CA_DIR)

    options = broker_tls.broker_use_ssl(TLS_BROKER_URL)

    assert options is not None
    assert options["ssl_cert_reqs"] == ssl.CERT_REQUIRED


def test_local_profile_names_an_unrecognised_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No stage 1 runs locally, so a typo must be named at settings import.

    Otherwise ``…=nonee`` silently upgrades to ``CERT_REQUIRED`` and the
    self-signed-Redis workflow fails with an opaque TLS error instead.
    """
    monkeypatch.setenv(RUNTIME_ENV_VAR, LOCAL)
    monkeypatch.setenv(broker_tls.CERT_REQS_ENV_VAR, "nonee")

    with pytest.raises(ImproperlyConfigured) as refused:
        broker_tls.broker_use_ssl(TLS_BROKER_URL)

    message = str(refused.value)
    assert broker_tls.CERT_REQS_ENV_VAR in message
    assert "nonee" in message


def test_local_plain_broker_is_not_blocked_by_an_inert_typo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The local naming is scoped to where the policy actually changes behaviour.

    Deliberately not symmetric with stage 1, which refuses an unrecognised
    value whatever the scheme: a `redis://localhost` laptop must not be blocked
    from booting over a value that has no effect there.
    """
    monkeypatch.setenv(RUNTIME_ENV_VAR, LOCAL)
    monkeypatch.setenv(broker_tls.CERT_REQS_ENV_VAR, "nonee")

    assert broker_tls.broker_use_ssl(PLAIN_BROKER_URL) is None


def test_stage_one_skips_the_broker_condition_when_local(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(RUNTIME_ENV_VAR, LOCAL)
    monkeypatch.setenv(broker_tls.CERT_REQS_ENV_VAR, broker_tls.UNVERIFIED)
    monkeypatch.setenv(broker_tls.BROKER_URL_ENV_VAR, TLS_BROKER_URL)
    monkeypatch.setenv("SSL_CERT_FILE", MISSING_BUNDLE)
    monkeypatch.setenv("SSL_CERT_DIR", MISSING_CA_DIR)

    refuse_unverified_broker_tls(_settings_stub(TLS_BROKER_URL))


def test_laptop_settings_keep_cert_none_for_a_self_signed_redis() -> None:
    """AC3, end to end: the local leaf boots with verification off, by request."""
    result = _run_probe(
        {
            "DJANGO_SETTINGS_MODULE": "config.settings.local",
            RUNTIME_ENV_VAR: LOCAL,
            "REDIS_BROKER_URL": TLS_BROKER_URL,
            "COMPONENT_BROKER_SSL_CERT_REQS": broker_tls.UNVERIFIED,
        },
    )

    assert result.returncode == 0, result.stderr
    composed = json.loads(result.stdout)
    assert composed["broker"] == {
        "ssl_cert_reqs": int(ssl.CERT_NONE),
        "ssl_ca_certs": None,
        "ssl_ca_path": None,
    }
