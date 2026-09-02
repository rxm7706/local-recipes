"""Story 41.4 / CAP-12: a ``rediss://`` broker is verified, not just encrypted.

Red-team X-2 → directive R-14. Three acceptance criteria, each covered twice —
once against ``config.broker_tls`` directly (the composition unit) and once
against a real child process that loads the settings module and runs
``manage.py check`` (the boot the operator actually gets):

1. production + ``rediss://`` → ``CERT_REQUIRED`` and ``ssl_ca_certs`` at the
   configured bundle, for the broker *and* the result backend;
2. deployed + ``CERT_NONE`` requested → stage 1 refuses by name;
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

#: A path that cannot resolve, used to blank the OS trust-store tier.
MISSING_BUNDLE = "/nonexistent/corporate-ca.pem"

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
    "'ssl_ca_certs': opts.get('ssl_ca_certs')},"
    "'backend_matches_broker': settings.CELERY_REDIS_BACKEND_USE_SSL == opts,"
    "}))"
)

BROKER_ENV_KEYS = (
    broker_tls.BROKER_URL_ENV_VAR,
    broker_tls.REDIS_URL_ENV_VAR,
    broker_tls.CERT_REQS_ENV_VAR,
    broker_tls.CA_BUNDLE_ENV_VAR,
    "SSL_CERT_FILE",
)


@pytest.fixture(autouse=True)
def _clean_broker_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Deployed locality and no inherited broker/TLS env from the test host."""
    monkeypatch.delenv(RUNTIME_ENV_VAR, raising=False)
    for key in BROKER_ENV_KEYS:
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


def _child_env(overrides: dict[str, str]) -> dict[str, str]:
    """A child-process env with every broker/TLS key under this test's control."""
    env = dict(os.environ)
    for key in (*BROKER_ENV_KEYS, RUNTIME_ENV_VAR, *DEPLOYED_REQUIRED_ENV):
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
        argv,
        check=False,
        capture_output=True,
        text=True,
        timeout=300,
        cwd=PLATFORM_ROOT,
        env=_child_env(overrides),
    )


def _run_probe(overrides: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """Load settings in a child process; return the completed probe run."""
    return _run_child([sys.executable, "-c", SETTINGS_PROBE], overrides)


def _run_manage_check(overrides: dict[str, str]) -> subprocess.CompletedProcess[str]:
    """Run the real ``manage.py check`` boot in a child process."""
    return _run_child([sys.executable, "manage.py", "check"], overrides)


def _deployed_env(**overrides: str) -> dict[str, str]:
    return {**DEPLOYED_REQUIRED_ENV, **overrides}


# --- AC1: production + rediss:// is verified against the configured bundle ---


def test_tls_broker_composes_cert_required_and_the_bundle(
    monkeypatch: pytest.MonkeyPatch,
    corporate_bundle: Path,
) -> None:
    monkeypatch.setenv("SSL_CERT_FILE", str(corporate_bundle))

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
    monkeypatch.setenv(broker_tls.CA_BUNDLE_ENV_VAR, str(explicit_bundle))

    assert broker_tls.resolve_ca_bundle() == str(corporate_bundle)


def test_explicit_bundle_is_the_second_tier(
    monkeypatch: pytest.MonkeyPatch,
    explicit_bundle: Path,
) -> None:
    monkeypatch.setenv("SSL_CERT_FILE", MISSING_BUNDLE)
    monkeypatch.setenv(broker_tls.CA_BUNDLE_ENV_VAR, str(explicit_bundle))

    assert broker_tls.resolve_ca_bundle() == str(explicit_bundle)


def test_unreadable_bundle_paths_resolve_to_no_bundle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SSL_CERT_FILE", MISSING_BUNDLE)
    monkeypatch.setenv(broker_tls.CA_BUNDLE_ENV_VAR, MISSING_BUNDLE)

    assert broker_tls.resolve_ca_bundle() is None


def test_plain_broker_has_no_ssl_options() -> None:
    assert broker_tls.broker_use_ssl(PLAIN_BROKER_URL) is None


def test_production_settings_verify_a_rediss_broker(
    corporate_bundle: Path,
) -> None:
    """AC1, end to end: the composed setting a deployed worker actually gets."""
    result = _run_probe(
        _deployed_env(
            REDIS_BROKER_URL=TLS_BROKER_URL,
            SSL_CERT_FILE=str(corporate_bundle),
        ),
    )

    assert result.returncode == 0, result.stderr
    composed = json.loads(result.stdout)
    assert composed["broker"] == {
        "ssl_cert_reqs": int(ssl.CERT_REQUIRED),
        "ssl_ca_certs": str(corporate_bundle),
    }
    assert composed["backend_matches_broker"] is True


# --- AC2: deployed + CERT_NONE requested → stage 1 refuses ---


def test_stage_one_refuses_cert_none_when_deployed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(broker_tls.CERT_REQS_ENV_VAR, broker_tls.UNVERIFIED)

    with pytest.raises(ImproperlyConfigured) as refused:
        refuse_unverified_broker_tls()

    message = str(refused.value)
    assert broker_tls.CERT_REQS_ENV_VAR in message
    assert f"{RUNTIME_ENV_VAR}={LOCAL}" in message


def test_stage_one_refuses_an_unrecognised_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(broker_tls.CERT_REQS_ENV_VAR, "optional")

    with pytest.raises(ImproperlyConfigured) as refused:
        refuse_unverified_broker_tls()

    message = str(refused.value)
    assert broker_tls.CERT_REQS_ENV_VAR in message
    assert "optional" in message
    assert broker_tls.VERIFIED in message


def test_stage_one_refuses_a_tls_broker_with_no_bundle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(broker_tls.BROKER_URL_ENV_VAR, TLS_BROKER_URL)
    monkeypatch.setenv("SSL_CERT_FILE", MISSING_BUNDLE)

    with pytest.raises(ImproperlyConfigured) as refused:
        refuse_unverified_broker_tls()

    message = str(refused.value)
    assert broker_tls.BROKER_URL_ENV_VAR in message
    assert broker_tls.CA_BUNDLE_ENV_VAR in message


def test_stage_one_accepts_a_verified_tls_broker(
    monkeypatch: pytest.MonkeyPatch,
    corporate_bundle: Path,
) -> None:
    monkeypatch.setenv(broker_tls.BROKER_URL_ENV_VAR, TLS_BROKER_URL)
    monkeypatch.setenv("SSL_CERT_FILE", str(corporate_bundle))

    refuse_unverified_broker_tls()


def test_stage_one_accepts_a_plain_broker_with_no_bundle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A non-TLS broker has no certificate to verify — not this check's business."""
    monkeypatch.setenv(broker_tls.BROKER_URL_ENV_VAR, PLAIN_BROKER_URL)
    monkeypatch.setenv("SSL_CERT_FILE", MISSING_BUNDLE)

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
        run_stage_one(sys.modules[__name__])

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


def test_manage_py_check_refuses_cert_none_when_deployed(
    corporate_bundle: Path,
) -> None:
    """AC2, end to end: the deployed boot stops with a named refusal."""
    result = _run_manage_check(
        _deployed_env(
            REDIS_BROKER_URL=TLS_BROKER_URL,
            SSL_CERT_FILE=str(corporate_bundle),
            COMPONENT_BROKER_SSL_CERT_REQS=broker_tls.UNVERIFIED,
        ),
    )

    assert result.returncode != 0, result.stdout
    assert broker_tls.CERT_REQS_ENV_VAR in result.stderr
    assert "ImproperlyConfigured" in result.stderr


def test_manage_py_check_passes_with_a_verified_broker(
    corporate_bundle: Path,
) -> None:
    """Control for the refusal above: same env minus the CERT_NONE request."""
    result = _run_manage_check(
        _deployed_env(
            REDIS_BROKER_URL=TLS_BROKER_URL,
            SSL_CERT_FILE=str(corporate_bundle),
        ),
    )

    assert result.returncode == 0, result.stderr


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

    options = broker_tls.broker_use_ssl(TLS_BROKER_URL)

    assert options is not None
    assert options["ssl_cert_reqs"] == ssl.CERT_REQUIRED


def test_stage_one_skips_the_broker_condition_when_local(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(RUNTIME_ENV_VAR, LOCAL)
    monkeypatch.setenv(broker_tls.CERT_REQS_ENV_VAR, broker_tls.UNVERIFIED)
    monkeypatch.setenv(broker_tls.BROKER_URL_ENV_VAR, TLS_BROKER_URL)
    monkeypatch.setenv("SSL_CERT_FILE", MISSING_BUNDLE)

    refuse_unverified_broker_tls()


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
    }


# --- Regression: base settings must not re-hardcode CERT_NONE ---


def test_base_settings_delegate_broker_tls_to_the_helper() -> None:
    source = (PLATFORM_ROOT / "config/settings/base.py").read_text(encoding="utf-8")

    assert "broker_use_ssl(REDIS_BROKER_URL)" in source
    assert "ssl.CERT_NONE" not in source


def test_entrypoints_load_settings_before_instrumenting() -> None:
    """Regression: the OTel Django instrumentor swallows stage-1 refusals.

    ``DjangoInstrumentor().instrument()`` catches ``ImproperlyConfigured`` from
    ``settings.MIDDLEWARE`` and answers it with ``settings.configure()``, which
    pins Django's empty defaults for the rest of the process. Every entrypoint
    funnels through ``configure_observability``, so the settings load has to
    happen there and it has to happen first.
    """
    source = (PLATFORM_ROOT / "config/observability/__init__.py").read_text(
        encoding="utf-8",
    )

    assert "load_django_settings()\n    return configure_telemetry" in source


def test_required_settings_refusal_also_reaches_the_exit_code() -> None:
    """The same swallow hid the shipped ``DJANGO_SECRET_KEY`` refusal.

    Lives with the broker tests because it guards the identical fix; the
    required-settings contract itself is ``test_startup_required_settings.py``.
    """
    env = _deployed_env(REDIS_BROKER_URL=PLAIN_BROKER_URL)
    del env["DJANGO_SECRET_KEY"]

    result = _run_manage_check(env)

    assert result.returncode != 0, result.stdout
    assert "DJANGO_SECRET_KEY" in result.stderr
