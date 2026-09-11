"""Story 49.14: CAP-10 BS-4/BS-8 production callers (not test-only)."""

from __future__ import annotations

import ast
import time
from datetime import UTC
from unittest.mock import patch
from datetime import datetime
from pathlib import Path

import pytest
from django.test import override_settings
from django_pyforge.assertion import crypto
from django_pyforge.assertion.golden import GOLDEN_PRIVATE_PEM
from django_pyforge.assertion.golden import GOLDEN_PUBLIC_PEM
from django_pyforge.circuits import FAIL_FAST_SECONDS
from django_pyforge.circuits import FAIL_MAX
from django_pyforge.circuits import CircuitBreaker
from django_pyforge.circuits import CircuitState
from django_pyforge.station_client import StationClientDegraded
from django_pyforge.station_client import StationHttpClient

from django_pyforge.roles import prefixed_station

_SHARED = Path(__file__).resolve().parents[2] / "shared" / "packages"
STATION_CLIENT = (
    _SHARED / "django-pyforge" / "src" / "django_pyforge" / "station_client.py"
)
MASON_APPS = _SHARED / "django-mason" / "src" / "django_mason_portal" / "apps.py"
MASON_BOOT = _SHARED / "django-mason" / "src" / "django_mason_portal" / "boot_reconcile.py"
SURPLUS = 20


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_station_client_imports_and_uses_circuit_breaker() -> None:
    source = _source(STATION_CLIENT)
    assert "django_pyforge.circuits" in source
    assert "station_outbound_breaker" in source
    assert "_guarded_transport" in source


def test_mason_ready_invokes_boot_reconcile(monkeypatch) -> None:
    from django.apps import apps

    calls: list[bool] = []

    def _record() -> None:
        calls.append(True)

    monkeypatch.setattr(
        "django_mason_portal.boot_reconcile.run_mason_boot_reconcile",
        _record,
    )
    apps.get_app_config("mason_portal").ready()
    assert calls == [True]


def test_mason_boot_reconcile_is_production_caller() -> None:
    apps_source = _source(MASON_APPS)
    boot_source = _source(MASON_BOOT)
    assert "run_mason_boot_reconcile" in apps_source
    assert "reconcile_boot" in boot_source
    assert "DjangoPgIndexStore" in boot_source


@override_settings(
    PYFORGE_ASSERTION_PRIVATE_KEY=GOLDEN_PRIVATE_PEM,
    PYFORGE_ASSERTION_PUBLIC_KEY=GOLDEN_PUBLIC_PEM,
)
def test_station_client_trips_breaker_and_degrades(monkeypatch) -> None:
    class _FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 9, 10, 12, 0, tzinfo=tz or UTC)

    monkeypatch.setattr(crypto, "datetime", _FrozenDatetime)
    breaker = CircuitBreaker(fail_max=FAIL_MAX, reset_timeout=3600)
    monkeypatch.setattr(
        "django_pyforge.station_client.station_outbound_breaker",
        breaker,
    )

    def failing_transport(
        method: str,
        url: str,
        headers: dict[str, str],
        body: bytes | None,
    ) -> bytes:
        msg = "outbound down"
        raise RuntimeError(msg)

    client = StationHttpClient()
    for _ in range(SURPLUS):
        with pytest.raises((RuntimeError, StationClientDegraded)):
            client.post(
                "/compliance/check",
                payload={"recipe_name": "numpy"},
                station="warden",
                sub="cli-user",
                roles=[prefixed_station("warden")],
                base_url="http://testserver",
                private_pem=GOLDEN_PRIVATE_PEM,
                transport=failing_transport,
            )
    assert breaker.state is CircuitState.OPEN

    def slow_transport(
        method: str,
        url: str,
        headers: dict[str, str],
        body: bytes | None,
    ) -> bytes:
        time.sleep(FAIL_FAST_SECONDS * 8)
        return b"{}"

    started = time.perf_counter()
    with pytest.raises(StationClientDegraded):
        client.post(
            "/compliance/check",
            payload={"recipe_name": "numpy"},
            station="warden",
            sub="cli-user",
            roles=[prefixed_station("warden")],
            base_url="http://testserver",
            private_pem=GOLDEN_PRIVATE_PEM,
            transport=slow_transport,
        )
    elapsed = time.perf_counter() - started
    assert elapsed < FAIL_FAST_SECONDS


def test_station_remote_default_path_uses_breaker(monkeypatch) -> None:
    from django_pyforge.station_client import _resolve_transport

    breaker = CircuitBreaker(fail_max=FAIL_MAX, reset_timeout=3600)
    monkeypatch.setattr(
        "django_pyforge.station_client.station_outbound_breaker",
        breaker,
    )
    monkeypatch.setattr(
        "django_pyforge.station_port.is_station_remote",
        lambda: True,
    )
    monkeypatch.setattr(
        "django_pyforge.station_port.default_transport",
        lambda: None,
    )

    def failing_transport(
        method: str,
        url: str,
        headers: dict[str, str],
        body: bytes | None,
    ) -> bytes:
        msg = "remote outbound down"
        raise RuntimeError(msg)

    with patch(
        "django_pyforge.station_client._urllib_transport",
        return_value=failing_transport,
    ):
        transport = _resolve_transport(None)
        assert transport is not None
        for _ in range(SURPLUS):
            with pytest.raises((RuntimeError, StationClientDegraded)):
                transport("POST", "http://testserver/x", {}, b"{}")
    assert breaker.state is CircuitState.OPEN


def test_station_client_breaker_module_is_shared_singleton() -> None:
    tree = ast.parse(_source(STATION_CLIENT))
    names = {
        target.id
        for node in tree.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }
    assert "station_outbound_breaker" in names
