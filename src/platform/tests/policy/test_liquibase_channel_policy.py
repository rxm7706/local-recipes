"""Liquibase 5.0.4+ on the platform channel (steward 27.1 / FR-21).

Pins belong on ``[feature.python-agent-platform]`` (the env the platform
image solves). ``platform-dev`` composes that feature. Helm Job / DML-only
app role is Story 27.2 and is out of scope here.
"""

from __future__ import annotations

import re
from typing import Any

import pytest
from packaging.version import Version

from tests.policy import readers

LIQUIBASE_SPEC = ">=5.0.4"
JDBC_SPEC = ">=42.7.13"
LIQUIBASE_FLOOR = Version("5.0.4")
PLATFORM_ENV = "python-agent-platform"


def _platform_deps(manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    pixi = manifest if manifest is not None else readers.pixi_manifest()
    feature = pixi.get("feature", {}).get("python-agent-platform", {})
    deps = feature.get("dependencies", {})
    assert isinstance(deps, dict), "python-agent-platform.dependencies must be a table"
    return deps


def _assert_liquibase_pins(deps: dict[str, Any]) -> None:
    assert "liquibase" in deps, (
        "pixi.toml [feature.python-agent-platform.dependencies] must pin "
        "liquibase (steward 27.1 / FR-21)"
    )
    assert deps.get("liquibase") == LIQUIBASE_SPEC, (
        "liquibase must be pinned "
        f"{LIQUIBASE_SPEC!r} so 5.0.2/5.0.3 SEARCH_PATH defects are excluded "
        f"(got {deps.get('liquibase')!r})"
    )
    assert "liquibase-postgresql" in deps, (
        "pixi.toml [feature.python-agent-platform.dependencies] must pin "
        "liquibase-postgresql (vendored PostgreSQL JDBC; air-gap / FR-21)"
    )
    assert deps.get("liquibase-postgresql") == JDBC_SPEC, (
        "liquibase-postgresql must be pinned "
        f"{JDBC_SPEC!r} to the published JDBC floor "
        f"(got {deps.get('liquibase-postgresql')!r})"
    )


def _conda_pkg_version(url: str, package: str) -> str | None:
    """Version for ``package`` in a conda URL, matching the exact name."""
    pattern = re.compile(
        rf"/{re.escape(package)}-(?P<version>\d+(?:\.\d+)*)-[^/]+\.conda(?:\.bz2)?$"
    )
    match = pattern.search(url)
    if match is None:
        return None
    return match.group("version")


def _versions_for_package(urls: list[str], package: str) -> list[str]:
    found: list[str] = []
    for url in urls:
        version = _conda_pkg_version(url, package)
        if version is not None:
            found.append(version)
    return found


def _assert_lock_liquibase_floor(urls: list[str]) -> None:
    versions = _versions_for_package(urls, "liquibase")
    assert versions, (
        f"pixi.lock {PLATFORM_ENV} must select liquibase "
        f"{LIQUIBASE_SPEC} (SelfExplainML 5.0.4+)"
    )
    for raw in versions:
        version = Version(raw)
        assert version >= LIQUIBASE_FLOOR, (
            f"liquibase {raw} is below {LIQUIBASE_SPEC}; "
            "5.0.2/5.0.3 SEARCH_PATH is a silent wrong-schema defect"
        )


def _assert_lock_jdbc_present(urls: list[str]) -> None:
    versions = _versions_for_package(urls, "liquibase-postgresql")
    assert versions, (
        f"pixi.lock {PLATFORM_ENV} must include liquibase-postgresql "
        f"{JDBC_SPEC} (vendored JDBC; air-gap)"
    )
    for raw in versions:
        version = Version(raw)
        assert version >= Version("42.7.13"), (
            f"liquibase-postgresql {raw} is below {JDBC_SPEC}"
        )


def test_python_agent_platform_declares_liquibase() -> None:
    """Happy path: liquibase >=5.0.4 plus vendored JDBC pin."""
    _assert_liquibase_pins(_platform_deps())


def test_removing_liquibase_pin_reds() -> None:
    """Drift: dropping the liquibase pin must fail."""
    drifted = dict(_platform_deps())
    del drifted["liquibase"]
    with pytest.raises(AssertionError, match="liquibase"):
        _assert_liquibase_pins(drifted)


def test_removing_jdbc_pin_reds() -> None:
    """Drift: dropping the vendored JDBC pin must fail."""
    drifted = dict(_platform_deps())
    del drifted["liquibase-postgresql"]
    with pytest.raises(AssertionError, match="liquibase-postgresql"):
        _assert_liquibase_pins(drifted)


def test_liquibase_spec_below_504_reds() -> None:
    """Drift: a liquibase floor that admits 5.0.3 must fail."""
    drifted = dict(_platform_deps())
    drifted["liquibase"] = ">=5.0.3"
    with pytest.raises(AssertionError, match="liquibase"):
        _assert_liquibase_pins(drifted)


def test_lock_selects_liquibase_504_and_jdbc() -> None:
    """Happy path: lock URLs include liquibase >=5.0.4 and JDBC."""
    urls = readers.pixi_env_conda_urls(PLATFORM_ENV)
    assert urls, f"pixi.lock {PLATFORM_ENV} package list is empty"
    _assert_lock_liquibase_floor(urls)
    _assert_lock_jdbc_present(urls)


def test_lock_selecting_liquibase_503_reds() -> None:
    """Drift: a locked liquibase 5.0.3 URL must fail."""
    urls = [
        "https://conda.anaconda.org/SelfExplainML/linux-64/"
        "liquibase-5.0.3-h123_0.conda"
    ]
    with pytest.raises(AssertionError, match="5.0.3"):
        _assert_lock_liquibase_floor(urls)
