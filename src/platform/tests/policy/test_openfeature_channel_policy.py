"""OpenFeature + cachebox 5.x on the platform channel (steward 26.3 / FR-33).

Pins belong on ``[feature.python-agent-platform]`` (the env the platform
image solves). ``platform-dev`` composes that feature. FILE provider /
``flags.json`` is Story 26.4 and is out of scope here.
"""

from __future__ import annotations

import re
from typing import Any

import pytest
from packaging.version import Version

from tests.policy import readers

OPENFEATURE_PACKAGES = (
    "openfeature-sdk",
    "openfeature-flagd-api",
    "openfeature-flagd-core",
    "openfeature-provider-flagd",
)
CACHEBOX_SPEC = ">=5.2.3,<6"
PROVIDER_SPEC = ">=0.5.0,<0.5.1"
PLATFORM_ENV = "python-agent-platform"
_CONDA_VERSION_RE = re.compile(
    r"/(?P<name>[^/]+)-(?P<version>\d+(?:\.\d+)*)-[^/]+\.conda(?:\.bz2)?$",
)


def _platform_deps(manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    pixi = manifest if manifest is not None else readers.pixi_manifest()
    feature = pixi.get("feature", {}).get("python-agent-platform", {})
    deps = feature.get("dependencies", {})
    assert isinstance(deps, dict), "python-agent-platform.dependencies must be a table"
    return deps


def _assert_openfeature_and_cachebox_pins(deps: dict[str, Any]) -> None:
    for name in OPENFEATURE_PACKAGES:
        assert name in deps, (
            f"pixi.toml [feature.python-agent-platform.dependencies] must pin "
            f"{name} (steward 26.3 / FR-33)"
        )
    assert deps.get("cachebox") == CACHEBOX_SPEC, (
        "cachebox must be pinned "
        f"{CACHEBOX_SPEC!r} so conda-forge 6.x is not selected "
        f"(got {deps.get('cachebox')!r})"
    )
    assert deps.get("openfeature-provider-flagd") == PROVIDER_SPEC, (
        "openfeature-provider-flagd must be pinned "
        f"{PROVIDER_SPEC!r} so SelfExplainML 0.5.2 (protobuf 7) is not selected "
        f"(got {deps.get('openfeature-provider-flagd')!r})"
    )


def _conda_pkg_version(url: str, package: str) -> str | None:
    match = _CONDA_VERSION_RE.search(url)
    if match is None:
        return None
    if match.group("name") != package:
        return None
    return match.group("version")


def _versions_for_package(urls: list[str], package: str) -> list[str]:
    found: list[str] = []
    for url in urls:
        version = _conda_pkg_version(url, package)
        if version is not None:
            found.append(version)
    return found


def _assert_lock_cachebox_is_5x(urls: list[str]) -> None:
    versions = _versions_for_package(urls, "cachebox")
    assert versions, (
        f"pixi.lock {PLATFORM_ENV} must select cachebox "
        f"{CACHEBOX_SPEC} (conda-forge 5.2.3)"
    )
    for raw in versions:
        version = Version(raw)
        assert version >= Version("5.1") and version < Version("6"), (
            f"cachebox {raw} is outside {CACHEBOX_SPEC}; do not select 6.x"
        )


def _assert_lock_openfeature_present(urls: list[str]) -> None:
    for name in OPENFEATURE_PACKAGES:
        versions = _versions_for_package(urls, name)
        assert versions, (
            f"pixi.lock {PLATFORM_ENV} must include {name} "
            "(SelfExplainML OpenFeature builds)"
        )


def _assert_lock_provider_is_050(urls: list[str]) -> None:
    versions = _versions_for_package(urls, "openfeature-provider-flagd")
    assert versions, (
        f"pixi.lock {PLATFORM_ENV} must select openfeature-provider-flagd "
        f"{PROVIDER_SPEC} (SelfExplainML 0.5.0; 0.5.2 is protobuf 7)"
    )
    for raw in versions:
        version = Version(raw)
        assert version >= Version("0.5.0") and version < Version("0.5.1"), (
            f"openfeature-provider-flagd {raw} is outside {PROVIDER_SPEC}; "
            "do not select 0.5.2"
        )


def test_python_agent_platform_declares_openfeature_and_cachebox() -> None:
    """Happy path: four OpenFeature pins plus cachebox >=5.1,<6."""
    _assert_openfeature_and_cachebox_pins(_platform_deps())


def test_removing_an_openfeature_pin_reds() -> None:
    """Drift: dropping any OpenFeature pin must fail."""
    drifted = dict(_platform_deps())
    del drifted["openfeature-sdk"]
    with pytest.raises(AssertionError, match="openfeature-sdk"):
        _assert_openfeature_and_cachebox_pins(drifted)


def test_cachebox_spec_allowing_6_reds() -> None:
    """Drift: a cachebox spec that admits 6.x must fail."""
    drifted = dict(_platform_deps())
    drifted["cachebox"] = ">=5.1,<7"
    with pytest.raises(AssertionError, match="cachebox"):
        _assert_openfeature_and_cachebox_pins(drifted)


def test_provider_spec_allowing_052_reds() -> None:
    """Drift: a provider spec that admits 0.5.2 must fail."""
    drifted = dict(_platform_deps())
    drifted["openfeature-provider-flagd"] = ">=0.5.2"
    with pytest.raises(AssertionError, match="openfeature-provider-flagd"):
        _assert_openfeature_and_cachebox_pins(drifted)


def test_lock_selects_openfeature_and_cachebox_5() -> None:
    """Happy path: lock URLs include OpenFeature 0.5.0 and cachebox 5.x only."""
    urls = readers.pixi_env_conda_urls(PLATFORM_ENV)
    assert urls, f"pixi.lock {PLATFORM_ENV} package list is empty"
    _assert_lock_openfeature_present(urls)
    _assert_lock_cachebox_is_5x(urls)
    _assert_lock_provider_is_050(urls)


def test_lock_selecting_cachebox_6_reds() -> None:
    """Drift: a locked cachebox 6.x URL must fail."""
    urls = [
        "https://conda.anaconda.org/conda-forge/linux-64/cachebox-6.2.5-py312h123_0.conda",
    ]
    with pytest.raises(AssertionError, match="6.2.5"):
        _assert_lock_cachebox_is_5x(urls)


def test_lock_selecting_provider_052_reds() -> None:
    """Drift: a locked provider 0.5.2 URL must fail."""
    urls = [
        "https://conda.anaconda.org/SelfExplainML/noarch/"
        "openfeature-provider-flagd-0.5.2-pyh59285b8_1.conda",
    ]
    with pytest.raises(AssertionError, match="0.5.2"):
        _assert_lock_provider_is_050(urls)
