"""`DeploymentTopology` + `check_shareable_state` + `render_daphne_unit`/
`render_edge_config` + `steward deploy perimeter` — Story 9.5 (CAP-6, AD-5).

Covers every row of the story spec's I/O & Edge-Case Matrix, plus CLI verb
dispatch through `DeployDuty.run` -- mirrors `test_deploy_status.py`'s
conformance-tier shape (direct `DeployDuty().run(...)` / `main([...])`
invocation, no subprocess).
"""

from __future__ import annotations

import argparse

import pytest

from pyforge.steward.cli import EXIT_FAILED, EXIT_OK, main
from pyforge.steward.deploy import (
    DeployDuty,
    DeploymentTopology,
    UnshareableStateError,
    check_shareable_state,
    render_daphne_unit,
    render_edge_config,
)

_LOCMEM_CACHE = "django.core.cache.backends.locmem.LocMemCache"
_INMEMORY_CHANNEL_LAYER = "channels.layers.InMemoryChannelLayer"
_REDIS_CACHE = "django.core.cache.backends.redis.RedisCache"
_DJANGO_REDIS_CACHE = "django_redis.cache.RedisCache"
_REDIS_CHANNEL_LAYER = "channels_redis.core.RedisChannelLayer"


# ── DeploymentTopology construction (I/O matrix row: worker_count invalid) ──


@pytest.mark.parametrize("bad_worker_count", [0, -1, -4])
def test_worker_count_must_be_positive(bad_worker_count):
    with pytest.raises(ValueError, match="worker_count"):
        DeploymentTopology(
            worker_count=bad_worker_count,
            cache_backend=_LOCMEM_CACHE,
            channel_layer_backend=_INMEMORY_CHANNEL_LAYER,
        )


@pytest.mark.parametrize("bad_worker_count", ["4", 4.0, None, True])
def test_worker_count_must_be_an_int(bad_worker_count):
    with pytest.raises(TypeError, match="worker_count"):
        DeploymentTopology(
            worker_count=bad_worker_count,
            cache_backend=_LOCMEM_CACHE,
            channel_layer_backend=_INMEMORY_CHANNEL_LAYER,
        )


@pytest.mark.parametrize("field", ["cache_backend", "channel_layer_backend"])
def test_backend_fields_must_be_non_empty_strings(field):
    kwargs = {
        "worker_count": 1,
        "cache_backend": _LOCMEM_CACHE,
        "channel_layer_backend": _INMEMORY_CHANNEL_LAYER,
    }
    kwargs[field] = "   "
    with pytest.raises(ValueError, match=field):
        DeploymentTopology(**kwargs)


@pytest.mark.parametrize("field", ["cache_backend", "channel_layer_backend"])
def test_backend_fields_reject_non_string(field):
    kwargs = {
        "worker_count": 1,
        "cache_backend": _LOCMEM_CACHE,
        "channel_layer_backend": _INMEMORY_CHANNEL_LAYER,
    }
    kwargs[field] = 12345
    with pytest.raises(TypeError, match=field):
        DeploymentTopology(**kwargs)


@pytest.mark.parametrize("field", ["cache_backend", "channel_layer_backend"])
def test_backend_fields_reject_whitespace_padding(field):
    """A padded dotted class path passes the emptiness check but then
    silently mismatches `check_shareable_state`'s exact-match allowlist --
    rejected at construction instead, mirroring `declarations.py`'s
    established convention."""
    kwargs = {
        "worker_count": 1,
        "cache_backend": _LOCMEM_CACHE,
        "channel_layer_backend": _INMEMORY_CHANNEL_LAYER,
    }
    kwargs[field] = f" {kwargs[field]} "
    with pytest.raises(ValueError, match=field):
        DeploymentTopology(**kwargs)


def test_deployment_topology_is_frozen():
    topology = DeploymentTopology(
        worker_count=1, cache_backend=_LOCMEM_CACHE, channel_layer_backend=_INMEMORY_CHANNEL_LAYER
    )
    with pytest.raises(Exception):
        topology.worker_count = 2  # type: ignore[misc]


# ── check_shareable_state (I/O matrix rows 1-4) ─────────────────────────────


def test_single_worker_in_process_backends_pass():
    """Row: single worker, in-process backends -- passes, no refusal."""
    topology = DeploymentTopology(
        worker_count=1, cache_backend=_LOCMEM_CACHE, channel_layer_backend=_INMEMORY_CHANNEL_LAYER
    )
    check_shareable_state(topology)  # must not raise


def test_multi_worker_redis_backed_both_pass():
    """Row: multi-worker, Redis-backed both -- passes."""
    topology = DeploymentTopology(
        worker_count=4, cache_backend=_REDIS_CACHE, channel_layer_backend=_REDIS_CHANNEL_LAYER
    )
    check_shareable_state(topology)  # must not raise


def test_multi_worker_django_redis_cache_variant_is_refused():
    """`django_redis.cache.RedisCache` (the third-party `django-redis`
    package) is NOT allowlisted -- review pass found it previously
    allowlisted with no corresponding dependency anywhere in the
    `[dashboard]` extra or pixi.toml, so a pass here gave false confidence
    about a backend the extra cannot actually satisfy. Only Django's own
    built-in Redis backend is allowlisted (see `_SHAREABLE_CACHE_BACKENDS`'s
    comment): its `redis` client is already satisfied transitively via
    `channels_redis`, which the extra does install."""
    topology = DeploymentTopology(
        worker_count=2, cache_backend=_DJANGO_REDIS_CACHE, channel_layer_backend=_REDIS_CHANNEL_LAYER
    )
    with pytest.raises(UnshareableStateError, match="cache_backend"):
        check_shareable_state(topology)


def test_multi_worker_in_process_cache_raises_naming_cache_backend():
    """Row: multi-worker, in-process cache -- raises naming the unshareable backend."""
    topology = DeploymentTopology(
        worker_count=4, cache_backend=_LOCMEM_CACHE, channel_layer_backend=_REDIS_CHANNEL_LAYER
    )
    with pytest.raises(UnshareableStateError, match="cache_backend"):
        check_shareable_state(topology)


def test_multi_worker_in_process_channel_layer_raises_naming_channel_layer_backend():
    """Row: multi-worker, in-process channel layer -- raises naming the unshareable backend."""
    topology = DeploymentTopology(
        worker_count=4, cache_backend=_REDIS_CACHE, channel_layer_backend=_INMEMORY_CHANNEL_LAYER
    )
    with pytest.raises(UnshareableStateError, match="channel_layer_backend"):
        check_shareable_state(topology)


def test_multi_worker_both_in_process_names_cache_first():
    """When BOTH backends are unshareable, the refusal names exactly one
    field (cache, checked first) -- never merges both into one message."""
    topology = DeploymentTopology(
        worker_count=2, cache_backend=_LOCMEM_CACHE, channel_layer_backend=_INMEMORY_CHANNEL_LAYER
    )
    with pytest.raises(UnshareableStateError, match="cache_backend") as excinfo:
        check_shareable_state(topology)
    assert "channel_layer_backend" not in str(excinfo.value)


def test_single_worker_passes_with_any_backend_string():
    """AD-5's own text: worker_count == 1 accepts ANY backend, including a
    nonsense one -- the allowlist only applies once workers > 1."""
    topology = DeploymentTopology(
        worker_count=1, cache_backend="literally.anything", channel_layer_backend="also.anything"
    )
    check_shareable_state(topology)  # must not raise


# ── render_daphne_unit / render_edge_config ─────────────────────────────────


def test_render_daphne_unit_is_a_template_unit_naming_every_worker_port():
    topology = DeploymentTopology(
        worker_count=3, cache_backend=_REDIS_CACHE, channel_layer_backend=_REDIS_CHANNEL_LAYER
    )
    unit_text = render_daphne_unit(topology, base_port=9001)

    assert "%i" in unit_text
    assert "--proxy-headers" in unit_text
    for port in (9001, 9002, 9003):
        assert f"pyforge-steward-dashboard@{port}.service" in unit_text
    assert "ExecStart=daphne" in unit_text


def test_render_edge_config_sets_tls_and_network_policy():
    topology = DeploymentTopology(
        worker_count=2, cache_backend=_REDIS_CACHE, channel_layer_backend=_REDIS_CHANNEL_LAYER
    )
    edge_text = render_edge_config(
        topology,
        trusted_addresses=("10.0.0.1", "10.0.0.2"),
        tls_cert="/etc/tls/dashboard.crt",
        tls_key="/etc/tls/dashboard.key",
        base_port=9001,
    )

    assert "ssl_certificate /etc/tls/dashboard.crt;" in edge_text
    assert "ssl_certificate_key /etc/tls/dashboard.key;" in edge_text
    assert "allow 10.0.0.1;" in edge_text
    assert "allow 10.0.0.2;" in edge_text
    assert "deny all;" in edge_text
    assert "server 127.0.0.1:9001;" in edge_text
    assert "server 127.0.0.1:9002;" in edge_text
    # Overwrite, never append -- see render_edge_config's docstring.
    assert "proxy_set_header X-Forwarded-For $remote_addr;" in edge_text
    assert "proxy_add_x_forwarded_for" not in edge_text


def test_render_edge_config_rejects_empty_trusted_addresses():
    topology = DeploymentTopology(
        worker_count=1, cache_backend=_LOCMEM_CACHE, channel_layer_backend=_INMEMORY_CHANNEL_LAYER
    )
    with pytest.raises(ValueError, match="trusted_addresses"):
        render_edge_config(
            topology, trusted_addresses=(), tls_cert="/etc/tls/dashboard.crt", tls_key="/etc/tls/dashboard.key"
        )


def test_render_edge_config_uses_conditional_connection_upgrade():
    """Review pass: a hardcoded `Connection: upgrade` forced every plain
    HTTP request through the upgrade-connection header, not only real
    WebSocket upgrades -- the standard `map` idiom fixes this."""
    topology = DeploymentTopology(
        worker_count=1, cache_backend=_LOCMEM_CACHE, channel_layer_backend=_INMEMORY_CHANNEL_LAYER
    )
    edge_text = render_edge_config(
        topology, trusted_addresses=("10.0.0.1",), tls_cert="/etc/tls/dashboard.crt", tls_key="/etc/tls/dashboard.key"
    )
    assert "map $http_upgrade $connection_upgrade" in edge_text
    assert "proxy_set_header Connection $connection_upgrade;" in edge_text
    assert 'Connection "upgrade"' not in edge_text


def test_render_edge_config_sets_websocket_idle_timeouts():
    """Review pass: nginx's ~60s default idle timeout silently drops the
    long-lived Channels WebSocket connections this pattern exists to carry."""
    topology = DeploymentTopology(
        worker_count=1, cache_backend=_LOCMEM_CACHE, channel_layer_backend=_INMEMORY_CHANNEL_LAYER
    )
    edge_text = render_edge_config(
        topology, trusted_addresses=("10.0.0.1",), tls_cert="/etc/tls/dashboard.crt", tls_key="/etc/tls/dashboard.key"
    )
    assert "proxy_read_timeout 86400;" in edge_text
    assert "proxy_send_timeout 86400;" in edge_text


@pytest.mark.parametrize(
    "kwargs",
    [
        {"trusted_addresses": ("10.0.0.1; extra_directive on",)},
        {"trusted_addresses": ("10.0.0.1\ninjected {}",)},
        {"trusted_addresses": (" 10.0.0.1",)},
        {"tls_cert": "/etc/tls/dashboard.crt;\nextra_directive on"},
        {"tls_key": "/etc/tls/key with spaces.key"},
        {"server_name": "example.com; extra"},
        {"tls_cert": "/etc/tls/dashboard.crt#comment"},
        {"server_name": "$hostname.example.com"},
    ],
)
def test_render_edge_config_rejects_unsafe_interpolated_values(kwargs):
    """Review pass: `render_edge_config` previously validated only
    emptiness, so a crafted trusted-address/TLS-path/server-name value
    could inject an arbitrary extra nginx directive into the rendered
    security perimeter. `#` (same-line nginx comment) and `$` (nginx
    variable interpolation) were absent from the original character set --
    follow-up review pass."""
    topology = DeploymentTopology(
        worker_count=1, cache_backend=_LOCMEM_CACHE, channel_layer_backend=_INMEMORY_CHANNEL_LAYER
    )
    base_kwargs = {
        "trusted_addresses": ("10.0.0.1",),
        "tls_cert": "/etc/tls/dashboard.crt",
        "tls_key": "/etc/tls/dashboard.key",
    }
    base_kwargs.update(kwargs)
    with pytest.raises(ValueError):
        render_edge_config(topology, **base_kwargs)


def test_worker_ports_reject_overflow_past_valid_port_range():
    """Review pass: `DeploymentTopology.worker_count` only checked `> 0`, so
    a large count silently produced an out-of-range port with no error."""
    topology = DeploymentTopology(
        worker_count=10, cache_backend=_REDIS_CACHE, channel_layer_backend=_REDIS_CHANNEL_LAYER
    )
    with pytest.raises(ValueError, match="65535"):
        render_daphne_unit(topology, base_port=65530)


def test_daphne_and_edge_manifests_agree_on_worker_ports():
    """The two rendered manifests must never independently drift on how many
    workers/ports there are -- both derive from the same `_worker_ports`."""
    topology = DeploymentTopology(
        worker_count=5, cache_backend=_REDIS_CACHE, channel_layer_backend=_REDIS_CHANNEL_LAYER
    )
    unit_text = render_daphne_unit(topology, base_port=8100)
    edge_text = render_edge_config(
        topology,
        trusted_addresses=("10.0.0.1",),
        tls_cert="/etc/tls/dashboard.crt",
        tls_key="/etc/tls/dashboard.key",
        base_port=8100,
    )
    for port in range(8100, 8105):
        assert f"@{port}.service" in unit_text
        assert f"127.0.0.1:{port};" in edge_text


# ── `steward deploy perimeter` verb (I/O matrix rows 6-8) ───────────────────


def test_perimeter_refusal_names_the_offending_declaration_and_writes_nothing(tmp_path):
    """Row: perimeter verb, refusal -- DutyResult(ok=False, ...) naming the
    missing/incompatible declaration; no manifest written."""
    duty = DeployDuty()
    output_dir = tmp_path / "manifests"
    ns = argparse.Namespace(
        deploy_verb="perimeter",
        workers=4,
        cache_backend=_LOCMEM_CACHE,
        channel_layer_backend=_REDIS_CHANNEL_LAYER,
        trusted_address=["10.0.0.1"],
        tls_cert=str(tmp_path / "cert.pem"),
        tls_key=str(tmp_path / "key.pem"),
        output_dir=str(output_dir),
    )

    result = duty.run(ns)

    assert result.ok is False
    assert "cache_backend" in result.summary
    assert not output_dir.exists()


def test_perimeter_with_output_dir_renders_both_manifests(tmp_path):
    """Row: perimeter verb, --output-dir on success -- daphne unit + nginx
    config rendered to the directory."""
    duty = DeployDuty()
    output_dir = tmp_path / "manifests"
    ns = argparse.Namespace(
        deploy_verb="perimeter",
        workers=2,
        cache_backend=_REDIS_CACHE,
        channel_layer_backend=_REDIS_CHANNEL_LAYER,
        trusted_address=["10.0.0.1", "10.0.0.2"],
        tls_cert="/etc/tls/dashboard.crt",
        tls_key="/etc/tls/dashboard.key",
        output_dir=str(output_dir),
    )

    result = duty.run(ns)

    assert result.ok is True
    unit_path = output_dir / "pyforge-steward-dashboard@.service"
    edge_path = output_dir / "pyforge-steward-dashboard.nginx.conf"
    assert unit_path.is_file()
    assert edge_path.is_file()
    assert "ExecStart=daphne" in unit_path.read_text()
    assert "ssl_certificate /etc/tls/dashboard.crt;" in edge_path.read_text()


def test_perimeter_without_output_dir_is_validation_only_and_writes_nothing(tmp_path):
    """Row: perimeter verb, no --output-dir -- validation-only
    DutyResult(ok=True, ...); nothing written."""
    duty = DeployDuty()
    output_dir = tmp_path / "manifests"
    ns = argparse.Namespace(
        deploy_verb="perimeter",
        workers=1,
        cache_backend=_LOCMEM_CACHE,
        channel_layer_backend=_INMEMORY_CHANNEL_LAYER,
        trusted_address=None,
        tls_cert=None,
        tls_key=None,
        output_dir=None,
    )

    result = duty.run(ns)

    assert result.ok is True
    assert not output_dir.exists()


def test_perimeter_with_output_dir_but_no_trusted_address_refuses(tmp_path):
    """--output-dir demands a declared trusted ingress -- an edge config
    with no allowlist would enforce nothing while looking complete."""
    duty = DeployDuty()
    output_dir = tmp_path / "manifests"
    ns = argparse.Namespace(
        deploy_verb="perimeter",
        workers=1,
        cache_backend=_LOCMEM_CACHE,
        channel_layer_backend=_INMEMORY_CHANNEL_LAYER,
        trusted_address=None,
        tls_cert="/etc/tls/dashboard.crt",
        tls_key="/etc/tls/dashboard.key",
        output_dir=str(output_dir),
    )

    result = duty.run(ns)

    assert result.ok is False
    assert "--trusted-address" in result.summary
    assert not output_dir.exists()


def test_perimeter_with_output_dir_but_no_tls_refuses(tmp_path):
    duty = DeployDuty()
    output_dir = tmp_path / "manifests"
    ns = argparse.Namespace(
        deploy_verb="perimeter",
        workers=1,
        cache_backend=_LOCMEM_CACHE,
        channel_layer_backend=_INMEMORY_CHANNEL_LAYER,
        trusted_address=["10.0.0.1"],
        tls_cert=None,
        tls_key=None,
        output_dir=str(output_dir),
    )

    result = duty.run(ns)

    assert result.ok is False
    assert "--tls-cert" in result.summary
    assert "--tls-key" in result.summary
    assert not output_dir.exists()


def test_perimeter_output_dir_write_failure_is_a_named_refusal_not_a_crash(tmp_path):
    """Row: `_run_perimeter`'s documented `OSError` path (an unwritable
    `--output-dir`) -- a FILE already at the target path makes
    `output_path.mkdir()` raise, exercising the refusal the docstring
    promises rather than an uncaught crash. Review pass: this path had zero
    test coverage."""
    blocked_path = tmp_path / "manifests"
    blocked_path.write_text("not a directory", encoding="utf-8")
    duty = DeployDuty()
    ns = argparse.Namespace(
        deploy_verb="perimeter",
        workers=1,
        cache_backend=_REDIS_CACHE,
        channel_layer_backend=_REDIS_CHANNEL_LAYER,
        trusted_address=["10.0.0.1"],
        tls_cert="/etc/tls/dashboard.crt",
        tls_key="/etc/tls/dashboard.key",
        output_dir=str(blocked_path),
    )

    result = duty.run(ns)

    assert result.ok is False
    assert "could not write" in result.summary


def test_perimeter_manifest_rename_failure_is_a_named_refusal_not_a_crash(tmp_path):
    """Follow-up review pass: the final `rename()` calls previously sat
    OUTSIDE the OSError guard -- a rename failure (here: a directory already
    occupying the nginx-config's target filename) escaped uncaught instead
    of returning the named refusal `_run_perimeter`'s own docstring
    promises. Writes succeed (they target the distinct `.tmp` names); only
    the second `rename()` -- onto an existing directory -- fails."""
    output_dir = tmp_path / "manifests"
    output_dir.mkdir()
    (output_dir / "pyforge-steward-dashboard.nginx.conf").mkdir()
    duty = DeployDuty()
    ns = argparse.Namespace(
        deploy_verb="perimeter",
        workers=1,
        cache_backend=_REDIS_CACHE,
        channel_layer_backend=_REDIS_CHANNEL_LAYER,
        trusted_address=["10.0.0.1"],
        tls_cert="/etc/tls/dashboard.crt",
        tls_key="/etc/tls/dashboard.key",
        output_dir=str(output_dir),
    )

    result = duty.run(ns)

    assert result.ok is False
    assert "could not finalize" in result.summary
    # The unit's own temp file is cleaned up rather than left as litter.
    assert not (output_dir / "pyforge-steward-dashboard@.service.tmp").exists()


def test_perimeter_invalid_worker_count_is_a_named_refusal_not_a_crash(tmp_path):
    duty = DeployDuty()
    ns = argparse.Namespace(
        deploy_verb="perimeter",
        workers=0,
        cache_backend=_LOCMEM_CACHE,
        channel_layer_backend=_INMEMORY_CHANNEL_LAYER,
        trusted_address=None,
        tls_cert=None,
        tls_key=None,
        output_dir=None,
    )

    result = duty.run(ns)

    assert result.ok is False
    assert "worker_count" in result.summary


def test_perimeter_validation_only_mode_also_rejects_a_worker_count_past_the_port_range():
    """Follow-up review pass: without `--output-dir`, `_run_perimeter`
    previously reported `ok=True` 'topology valid' for a worker_count whose
    ports would overflow past 65535 -- a verdict that was not durable, since
    adding `--output-dir` later would then fail. Validating the same port
    range up front makes both branches agree on what 'valid' means."""
    duty = DeployDuty()
    ns = argparse.Namespace(
        deploy_verb="perimeter",
        workers=60000,
        cache_backend=_REDIS_CACHE,
        channel_layer_backend=_REDIS_CHANNEL_LAYER,
        trusted_address=None,
        tls_cert=None,
        tls_key=None,
        output_dir=None,
    )

    result = duty.run(ns)

    assert result.ok is False
    assert "65535" in result.summary


def test_perimeter_incomplete_namespace_is_a_named_refusal_not_a_crash():
    """Review pass: `ns.workers`/`.cache_backend`/`.channel_layer_backend`
    were accessed directly (unlike the `getattr`-guarded optional fields),
    so a `Namespace` missing them raised an uncaught `AttributeError`,
    contradicting this function's own "never an uncaught crash" docstring
    guarantee."""
    duty = DeployDuty()
    ns = argparse.Namespace(deploy_verb="perimeter")

    result = duty.run(ns)

    assert result.ok is False
    assert "refused" in result.summary


# ── CLI round-trip (`main([...])`) ──────────────────────────────────────────


def test_perimeter_via_cli_validation_only_succeeds():
    rc = main(["deploy", "perimeter"])
    assert rc == EXIT_OK


def test_perimeter_via_cli_multi_worker_default_backends_refuses():
    """Defaults are the single-worker-safe in-process backends -- bumping
    --workers without also declaring shareable backends is exactly the
    misconfiguration AD-5 exists to catch."""
    rc = main(["deploy", "perimeter", "--workers", "4"])
    assert rc == EXIT_FAILED


def test_perimeter_via_cli_renders_manifests_to_output_dir(tmp_path):
    output_dir = tmp_path / "manifests"
    rc = main(
        [
            "deploy",
            "perimeter",
            "--workers",
            "2",
            "--cache-backend",
            _REDIS_CACHE,
            "--channel-layer-backend",
            _REDIS_CHANNEL_LAYER,
            "--trusted-address",
            "10.0.0.1",
            "--trusted-address",
            "10.0.0.2",
            "--tls-cert",
            "/etc/tls/dashboard.crt",
            "--tls-key",
            "/etc/tls/dashboard.key",
            "--output-dir",
            str(output_dir),
        ]
    )

    assert rc == EXIT_OK
    assert (output_dir / "pyforge-steward-dashboard@.service").is_file()
    assert (output_dir / "pyforge-steward-dashboard.nginx.conf").is_file()


def test_bare_deploy_still_names_perimeter_among_available_verbs():
    duty = DeployDuty()
    result = duty.run(argparse.Namespace())
    assert result.ok is True
    assert "perimeter" in result.summary
