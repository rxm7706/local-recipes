"""Story 9.4 — `ExportPolicy` construction-time validation, `authorize_export`'s
refusal/log/webhook paths, and `maybe_encrypt_export`'s optional-encryption
wrap of `keys.encrypt_file`.

Identities for the encryption round-trip are generated directly via the real
`age-keygen` binary in test setup, mirroring `tests/conformance/
test_keys_encrypt_decrypt.py`'s `_generate_identity` fixture pattern — never
through a Steward primitive.
"""

from __future__ import annotations

import json
import logging
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from pyforge.steward.dashboard.export import (
    ExportPolicy, ExportUnauthorizedError, authorize_export, maybe_encrypt_export,
)
from pyforge.steward.keys import decrypt_file

AGE_MAGIC = b"age-encryption.org/v1"
SECURITY_LOGGER = "pyforge.steward.dashboard.security"


def _generate_identity(tmp_path: Path, name: str) -> tuple[Path, str]:
    key_path = tmp_path / name
    result = subprocess.run(
        ["age-keygen", "-o", str(key_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    # Parse the "Public key: " line specifically — age-keygen may emit extra
    # stderr lines (e.g. a file-permissions warning) around it.
    pubkey = next(
        line for line in result.stderr.splitlines() if line.startswith("Public key: ")
    ).removeprefix("Public key: ")
    return key_path, pubkey


@pytest.fixture
def identity(tmp_path):
    return _generate_identity(tmp_path, "identity.txt")


@pytest.fixture
def other_identity(tmp_path):
    return _generate_identity(tmp_path, "other-identity.txt")


# ── ExportPolicy construction-time validation ───────────────────────────────


def test_export_policy_accepts_allowed_roles_only():
    policy = ExportPolicy(allowed_roles=("admin", "auditor"))
    assert policy.allowed_roles == ("admin", "auditor")
    assert policy.webhook_url is None
    assert policy.encryption_recipient is None


def test_export_policy_accepts_a_webhook_url_and_a_recipient():
    policy = ExportPolicy(
        allowed_roles=("admin",),
        webhook_url="https://example.test/hooks/export-refused",
        encryption_recipient="age1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq",
    )
    assert policy.webhook_url == "https://example.test/hooks/export-refused"
    assert policy.encryption_recipient.startswith("age1")


def test_export_policy_rejects_a_bare_string_for_allowed_roles():
    """A bare string is iterable, so truthiness alone would pass it -- it
    must be rejected by type, since iterating it later would silently
    produce one-character "roles" instead of the intended role names.
    """
    with pytest.raises(TypeError, match="allowed_roles"):
        ExportPolicy(allowed_roles="admin")


def test_export_policy_rejects_empty_allowed_roles():
    with pytest.raises(ValueError, match="allowed_roles"):
        ExportPolicy(allowed_roles=())


def test_export_policy_rejects_a_non_string_role_element():
    with pytest.raises(TypeError, match=r"allowed_roles\[0\]"):
        ExportPolicy(allowed_roles=(1, "admin"))


def test_export_policy_rejects_a_blank_role_element():
    with pytest.raises(ValueError, match=r"allowed_roles\[1\]"):
        ExportPolicy(allowed_roles=("admin", ""))


def test_export_policy_rejects_a_padded_role_element():
    with pytest.raises(ValueError, match=r"allowed_roles\[0\]"):
        ExportPolicy(allowed_roles=(" admin ",))


@pytest.mark.parametrize(
    "bad_url",
    [
        "not-a-url",
        "ftp://x",
        "http://",
        "https://",
        "https://@",
        "https://:1",
    ],
)
def test_export_policy_rejects_a_malformed_webhook_url(bad_url):
    """`https://@` and `https://:1` have a non-empty `netloc` (an empty
    userinfo/port marker) but no real host -- checking `.hostname`, not
    `.netloc`, is what this test pins (Edge Case Hunter, review pass 1).
    """
    with pytest.raises(ValueError, match="webhook_url"):
        ExportPolicy(allowed_roles=("admin",), webhook_url=bad_url)


def test_export_policy_rejects_a_non_string_webhook_url():
    with pytest.raises(TypeError, match="webhook_url"):
        ExportPolicy(allowed_roles=("admin",), webhook_url=123)


def test_export_policy_rejects_a_blank_encryption_recipient():
    with pytest.raises(ValueError, match="encryption_recipient"):
        ExportPolicy(allowed_roles=("admin",), encryption_recipient="")


def test_export_policy_rejects_a_padded_encryption_recipient():
    with pytest.raises(ValueError, match="encryption_recipient"):
        ExportPolicy(allowed_roles=("admin",), encryption_recipient="  key  ")


def test_export_policy_rejects_a_non_string_encryption_recipient():
    with pytest.raises(TypeError, match="encryption_recipient"):
        ExportPolicy(allowed_roles=("admin",), encryption_recipient=123)


# ── authorize_export ─────────────────────────────────────────────────────


def test_authorize_export_returns_none_for_an_authorized_role(monkeypatch, caplog):
    policy = ExportPolicy(allowed_roles=("admin", "auditor"))
    urlopen_calls = []
    monkeypatch.setattr(
        urllib.request, "urlopen", lambda *a, **k: urlopen_calls.append((a, k))
    )
    caplog.set_level(logging.WARNING, logger=SECURITY_LOGGER)

    result = authorize_export(identity="alice", role="admin", policy=policy)

    assert result is None
    assert caplog.records == []
    assert urlopen_calls == []


def test_authorize_export_raises_and_logs_for_an_unauthorized_role(monkeypatch, caplog):
    policy = ExportPolicy(allowed_roles=("admin",))
    urlopen_calls = []
    monkeypatch.setattr(
        urllib.request, "urlopen", lambda *a, **k: urlopen_calls.append((a, k))
    )
    caplog.set_level(logging.WARNING, logger=SECURITY_LOGGER)

    with pytest.raises(ExportUnauthorizedError, match="viewer"):
        authorize_export(identity="alice", role="viewer", policy=policy)

    assert len(caplog.records) == 1
    assert caplog.records[0].levelno == logging.WARNING
    message = caplog.records[0].getMessage()
    assert "alice" in message
    assert "viewer" in message
    # No webhook configured on this policy -- no POST attempted.
    assert urlopen_calls == []


def test_authorize_export_raises_and_logs_when_no_role_was_resolved(caplog):
    policy = ExportPolicy(allowed_roles=("admin",))
    caplog.set_level(logging.WARNING, logger=SECURITY_LOGGER)

    with pytest.raises(ExportUnauthorizedError, match="no role"):
        authorize_export(identity="alice", role=None, policy=policy)

    assert len(caplog.records) == 1
    assert "alice" in caplog.records[0].getMessage()


def test_authorize_export_never_discloses_allowed_roles_or_webhook_url():
    """Mirrors `UntrustedIngressError`'s precedent (Story 9.1): the exception
    message names only the refused role, never the policy's internals.
    """
    policy = ExportPolicy(
        allowed_roles=("admin", "auditor"),
        webhook_url="https://example.test/hooks/export-refused",
    )

    with pytest.raises(ExportUnauthorizedError) as excinfo:
        authorize_export(identity="eve", role="guest", policy=policy)

    message = str(excinfo.value)
    assert "admin" not in message
    assert "auditor" not in message
    assert "example.test" not in message


def test_authorize_export_posts_a_webhook_on_refusal(monkeypatch, caplog):
    policy = ExportPolicy(
        allowed_roles=("admin",),
        webhook_url="https://hooks.example.test/export-refused",
    )
    caplog.set_level(logging.WARNING, logger=SECURITY_LOGGER)
    calls = []

    def fake_urlopen(request, timeout=None):
        calls.append((request, timeout))
        return None

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(ExportUnauthorizedError):
        authorize_export(identity="eve", role="guest", policy=policy)

    assert len(calls) == 1
    request, timeout = calls[0]
    assert request.get_full_url() == "https://hooks.example.test/export-refused"
    assert timeout == 5
    assert request.get_header("Content-type") == "application/json"
    payload = json.loads(request.data.decode("utf-8"))
    assert payload["event"] == "export_refused"
    assert payload["identity"] == "eve"
    assert payload["role"] == "guest"
    assert "occurred_at" in payload
    # Exactly one WARNING for the security event -- the webhook succeeded,
    # so no secondary failure warning is logged.
    assert len(caplog.records) == 1


def test_authorize_export_webhook_failure_does_not_suppress_the_raise(monkeypatch, caplog):
    policy = ExportPolicy(
        allowed_roles=("admin",),
        webhook_url="https://hooks.example.test/export-refused",
    )
    caplog.set_level(logging.WARNING, logger=SECURITY_LOGGER)

    def failing_urlopen(request, timeout=None):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(urllib.request, "urlopen", failing_urlopen)

    with pytest.raises(ExportUnauthorizedError, match="guest"):
        authorize_export(identity="eve", role="guest", policy=policy)

    # Two WARNINGs: the security event, then the webhook-failure secondary.
    assert len(caplog.records) == 2
    assert all(record.levelno == logging.WARNING for record in caplog.records)


def test_authorize_export_makes_no_webhook_call_when_none_is_configured(monkeypatch):
    policy = ExportPolicy(allowed_roles=("admin",))
    calls = []
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: calls.append((a, k)))

    with pytest.raises(ExportUnauthorizedError):
        authorize_export(identity="eve", role="guest", policy=policy)

    assert calls == []


# ── maybe_encrypt_export ─────────────────────────────────────────────────


def test_maybe_encrypt_export_round_trips_via_real_age(tmp_path, identity):
    key_path, pubkey = identity
    policy = ExportPolicy(allowed_roles=("admin",), encryption_recipient=pubkey)
    plaintext = tmp_path / "export.csv"
    plaintext.write_bytes(b"synthetic export payload \x00\xff\n")
    output = tmp_path / "export.csv.age"

    result = maybe_encrypt_export(plaintext, policy, output=output)

    assert result == output
    ciphertext = output.read_bytes()
    assert ciphertext.startswith(AGE_MAGIC)
    assert b"synthetic export payload" not in ciphertext

    decrypted = tmp_path / "back.csv"
    decrypt_file(output, identity=key_path, output=decrypted)
    assert decrypted.read_bytes() == plaintext.read_bytes()


def test_maybe_encrypt_export_output_is_undecryptable_without_the_identity(
    tmp_path, identity, other_identity
):
    _key_path, pubkey = identity
    other_key_path, _pubkey = other_identity
    policy = ExportPolicy(allowed_roles=("admin",), encryption_recipient=pubkey)
    plaintext = tmp_path / "export.csv"
    plaintext.write_bytes(b"synthetic export payload")
    output = tmp_path / "export.csv.age"

    maybe_encrypt_export(plaintext, policy, output=output)

    with pytest.raises(subprocess.CalledProcessError):
        decrypt_file(output, identity=other_key_path, output=tmp_path / "back.csv")


def test_maybe_encrypt_export_returns_the_original_path_when_no_recipient_is_declared(
    monkeypatch, tmp_path
):
    policy = ExportPolicy(allowed_roles=("admin",))
    plaintext = tmp_path / "export.csv"
    plaintext.write_bytes(b"unencrypted export payload")
    output = tmp_path / "export.csv.age"

    def _unexpected_encrypt(*args, **kwargs):
        raise AssertionError("encrypt_file must not be called when no recipient is declared")

    monkeypatch.setattr("pyforge.steward.dashboard.export.encrypt_file", _unexpected_encrypt)

    result = maybe_encrypt_export(plaintext, policy, output=output)

    assert result == Path(plaintext)
    assert result.read_bytes() == b"unencrypted export payload"
    assert not output.exists()


def test_maybe_encrypt_export_rejects_output_equal_to_path(tmp_path, identity):
    """Edge Case Hunter, review pass 1: `output == path` would let `age`'s
    write to `output` race its own read of `path`, risking truncation of the
    only copy of the plaintext -- refused before `encrypt_file` is called.
    """
    _key_path, pubkey = identity
    policy = ExportPolicy(allowed_roles=("admin",), encryption_recipient=pubkey)
    plaintext = tmp_path / "export.csv"
    plaintext.write_bytes(b"synthetic export payload")

    with pytest.raises(ValueError, match="output"):
        maybe_encrypt_export(plaintext, policy, output=plaintext)

    assert plaintext.read_bytes() == b"synthetic export payload"
