"""Two-state test for the identity-carrying station client's kill switch.

steward Story 114.8: ``spec-feature-flag-governance`` CAP-7 on
``spec-pyforge-unifying-strategy`` CAP-6. ``pyforge.steward.station_client_identity``
is read through ``django_pyforge.flags.evaluate_boolean`` at the one seam every
station call crosses (``StationHttpClient.emit_and_build``). Two flagd FILE trees,
one per state, drive the in-process FILE provider the host uses
(``configure_file_provider``): ON builds the client as before; OFF refuses with
``StationClientError`` naming the flag, and no portal falls back to a raw HTTP
request.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

pytest.importorskip("openfeature")

from django_pyforge import station_client
from django_pyforge.flags import configure_file_provider
from django_pyforge.flags import wait_until_ready
from django_pyforge.station_client import STATION_CLIENT_IDENTITY_FLAG_KEY
from django_pyforge.station_client import StationHttpClient
from openfeature import api

if TYPE_CHECKING:
    from pathlib import Path

# The host never imports pyforge.* (pap:AD-2): the client's types reach this test
# through the django_pyforge seam that already carries them.
PyForgeStationClient = station_client.PyForgeStationClient
StationClientError = station_client.StationClientError

_KEY = "pyforge.steward.station_client_identity"
_FLAG_ENV_KEYS = ("FLAGD_OFFLINE_FLAG_SOURCE_PATH", "PYFORGE_FLAGS_PATH")


@pytest.fixture(autouse=True)
def _isolate_the_provider(monkeypatch: pytest.MonkeyPatch):
    """`configure_file_provider` sets a process-wide provider and two env keys.

    Both go back after each test: the provider is cleared (``test_stations_index``'s
    ``_clear_flag_providers`` shape) so a later module's ``StationHttpClient`` call
    never reads this file's OFF tree, and monkeypatch restores the env keys.
    """
    for name in _FLAG_ENV_KEYS:
        monkeypatch.delenv(name, raising=False)
    yield
    api.clear_providers()


class _FakePortal:
    def __init__(self) -> None:
        self.emitted: list[tuple[str, str, tuple[str, ...]]] = []

    def emit(
        self,
        sub: str,
        roles: list[str],
        station: str,
        *,
        private_pem: str | None = None,
    ) -> str:
        self.emitted.append((sub, station, tuple(roles)))
        return f"assertion:{sub}:{station}:{','.join(roles)}"


def _station_client_flagd_tree(default_variant: str) -> bytes:
    return json.dumps(
        {
            "flags": {
                _KEY: {
                    "state": "ENABLED",
                    "variants": {"on": True, "off": False},
                    "defaultVariant": default_variant,
                }
            }
        }
    ).encode("utf-8")


def _provider_on(tree: Path) -> None:
    configure_file_provider(tree)
    wait_until_ready()


def test_the_key_is_the_one_the_client_reads() -> None:
    assert STATION_CLIENT_IDENTITY_FLAG_KEY == _KEY


def test_on_builds_the_identity_carrying_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    on_tree = tmp_path / "flags.json"
    on_tree.write_bytes(_station_client_flagd_tree("on"))
    _provider_on(on_tree)
    portal = _FakePortal()
    client = StationHttpClient(portal_client=portal).emit_and_build(
        station="atlas",
        sub="alice",
        roles=["atlas:viewer"],
        base_url="http://stations.invalid",
    )
    assert isinstance(client, PyForgeStationClient)
    assert portal.emitted == [("alice", "atlas", ("atlas:viewer",))]


def test_off_refuses_every_station_call_naming_the_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    off_tree = tmp_path / "flags.json"
    off_tree.write_bytes(_station_client_flagd_tree("off"))
    _provider_on(off_tree)
    portal = _FakePortal()
    with pytest.raises(StationClientError, match=f"flag {_KEY} is off"):
        StationHttpClient(portal_client=portal).emit_and_build(
            station="atlas",
            sub="alice",
            roles=["atlas:viewer"],
            base_url="http://stations.invalid",
        )
    assert portal.emitted == []  # refused before any assertion is minted
    with pytest.raises(StationClientError, match=f"flag {_KEY} is off"):
        StationHttpClient(portal_client=_FakePortal()).post(
            "/scan",
            station="atlas",
            sub="alice",
            roles=["atlas:viewer"],
            base_url="http://stations.invalid",
        )
