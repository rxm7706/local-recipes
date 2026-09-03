"""Story 42.5: prefixed role namespaces and the tenant claim."""

from __future__ import annotations

import pytest
from django.test import RequestFactory
from django.test import override_settings
from django_pyforge.assertion.crypto import mint_assertion
from django_pyforge.events import EXT_TENANT
from django_pyforge.events import STREAM
from django_pyforge.events import MemoryRedis
from django_pyforge.events.fabric import parse_cloudevent
from django_pyforge.models import RunState
from django_pyforge.roles import IDP_TOKEN_CLAIMS_SESSION_KEY
from django_pyforge.roles import legacy_bare_roles_enabled
from django_pyforge.roles import parse_role_claims
from django_pyforge.roles import prefixed_station
from django_pyforge.roles import prefixed_tenant
from django_pyforge.roles import roles_from_request
from django_pyforge.roles import station_granted
from django_pyforge.supervisor import publish_start


def test_bare_station_slug_is_refused_by_default() -> None:
    parsed = parse_role_claims(["atlas"])
    assert parsed.stations == frozenset()
    assert not station_granted("atlas", ["atlas"])


@override_settings(DJANGO_PYFORGE_LEGACY_BARE_ROLES=True)
def test_legacy_bare_station_slug_is_accepted_with_deprecation(caplog) -> None:
    caplog.set_level("WARNING")
    parsed = parse_role_claims(["atlas"])
    assert parsed.stations == frozenset({"atlas"})
    assert station_granted("atlas", ["atlas"])
    assert any("legacy_bare_station" in record.message for record in caplog.records)


def test_prefixed_station_and_tenant_parse() -> None:
    parsed = parse_role_claims(
        [
            prefixed_station("atlas"),
            prefixed_tenant("east"),
            "pyforge:admin",
        ],
    )
    assert parsed.stations == frozenset({"atlas"})
    assert parsed.tenants == frozenset({"east"})
    assert parsed.is_admin is True


def test_roles_from_request_returns_station_slugs() -> None:
    request = RequestFactory().get("/stations/atlas/board/")
    request.session = {
        IDP_TOKEN_CLAIMS_SESSION_KEY: {
            "groups": [prefixed_station("atlas"), prefixed_tenant("east")],
        },
    }
    assert roles_from_request(request) == frozenset({"atlas"})


@pytest.mark.django_db
def test_publish_start_sets_tenant_and_emits_cloudevent(monkeypatch) -> None:
    from django_pyforge.events.fabric import EventFabric

    broker = MemoryRedis()
    monkeypatch.setattr(
        "django_pyforge.supervisor.connect_event_broker",
        lambda _broker, _cache: EventFabric(broker),
    )
    monkeypatch.setattr(
        "django.conf.settings.REDIS_BROKER_URL",
        "redis://broker.test/0",
        raising=False,
    )
    monkeypatch.setattr(
        "django.conf.settings.REDIS_CACHE_URL",
        "redis://cache.test/1",
        raising=False,
    )
    monkeypatch.setattr(
        "django_pyforge.tasks.enqueue_supervised_run",
        lambda *args, **kwargs: None,
    )

    assertion = mint_assertion(
        sub="tenant-agent",
        roles=[prefixed_station("atlas"), prefixed_tenant("east")],
        station="atlas",
    )
    publish_start(station="atlas", assertion=assertion)

    run = RunState.objects.get()
    assert run.tenant == "east"

    rows = broker.xrange(STREAM, "-", "+")
    assert len(rows) == 1
    event = parse_cloudevent(dict(rows[0][1]))
    assert event is not None
    assert event["type"] == "run.started"
    assert event[EXT_TENANT] == "east"
    assert event["data"]["subject"] == "tenant-agent"


def test_legacy_flag_defaults_off() -> None:
    assert legacy_bare_roles_enabled() is False
