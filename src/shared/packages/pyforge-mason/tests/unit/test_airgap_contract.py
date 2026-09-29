"""Shape tests for mason Story 9.2 air-gap distribution contract socket."""

from __future__ import annotations

import pytest

from pyforge.mason.airgap_contract import (
    AIRGAP_CONTRACT,
    SUPPORTED_DISTRIBUTABLES,
    DistributableBackend,
    register_distributable,
    validate_backend_shape,
)


def test_contract_names_the_three_required_keys():
    assert set(AIRGAP_CONTRACT) == {
        "mirrored_channel_set",
        "pixi_bootstrap_path",
        "verification_hooks",
    }
    assert all(isinstance(v, str) and v.strip() for v in AIRGAP_CONTRACT.values())


def test_registry_starts_empty():
    assert SUPPORTED_DISTRIBUTABLES == {}


def test_valid_backend_passes_shape_validation():
    backend = DistributableBackend(
        name="example-offline",
        mirrored_channel_set=("https://mirror.example/conda-forge",),
        pixi_bootstrap_path="/opt/pixi/bin/pixi",
        verification_hooks=("pixi --version", "pixi install -e build"),
    )
    validate_backend_shape(backend)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"name": ""},
        {"mirrored_channel_set": ()},
        {"pixi_bootstrap_path": "  "},
        {"verification_hooks": ()},
    ],
)
def test_invalid_backends_fail_shape_validation(kwargs):
    base = dict(
        name="ok",
        mirrored_channel_set=("https://mirror.example/conda-forge",),
        pixi_bootstrap_path="/opt/pixi/bin/pixi",
        verification_hooks=("pixi --version",),
    )
    base.update(kwargs)
    with pytest.raises(ValueError):
        validate_backend_shape(DistributableBackend(**base))


def test_register_then_reject_duplicate(monkeypatch):
    # Isolate: copy registry for this test.
    monkeypatch.setattr(
        "pyforge.mason.airgap_contract.SUPPORTED_DISTRIBUTABLES",
        {},
        raising=True,
    )
    from pyforge.mason import airgap_contract as mod

    backend = DistributableBackend(
        name="vendor-a",
        mirrored_channel_set=("file:///mirrors/conda-forge",),
        pixi_bootstrap_path="./bootstrap/pixi",
        verification_hooks=("pixi install -e local-recipes",),
    )
    register_distributable(backend)
    assert "vendor-a" in mod.SUPPORTED_DISTRIBUTABLES
    with pytest.raises(ValueError, match="already registered"):
        register_distributable(backend)
