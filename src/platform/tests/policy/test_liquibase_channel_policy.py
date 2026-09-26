"""Liquibase 5.0.4+ on the platform channel (steward 27.1, 27.5 / FR-21).

Pins belong on ``[feature.python-agent-platform]`` (the env the platform
image solves). ``platform-dev`` composes that feature. Helm Job / DML-only
app role is Story 27.2 and is out of scope here.

Story 27.5: the PostgreSQL JDBC driver is ``pgjdbc``; ``liquibase-postgresql``
is Liquibase's dialect extension from conda-forge. SelfExplainML's
``liquibase-postgresql`` 42.7.13 was the driver under that colliding name and
must never be locked again.
"""

from __future__ import annotations

import re
from typing import Any

import pytest
from packaging.version import Version

from tests.policy import readers

LIQUIBASE_SPEC = ">=5.0.4"
EXTENSION_SPEC = {"version": ">=5.0.4,<42", "channel": "conda-forge"}
JDBC_SPEC = ">=42.7.13"
LIQUIBASE_FLOOR = Version("5.0.4")
JDBC_FLOOR = Version("42.7.13")
RETIRED_DRIVER_FLOOR = Version("42")
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
    assert "pgjdbc" in deps, (
        "pixi.toml [feature.python-agent-platform.dependencies] must pin "
        "pgjdbc (vendored PostgreSQL JDBC driver; air-gap / FR-21)"
    )
    assert deps.get("pgjdbc") == JDBC_SPEC, (
        f"pgjdbc must be pinned {JDBC_SPEC!r} (got {deps.get('pgjdbc')!r})"
    )
    assert deps.get("liquibase-postgresql") == EXTENSION_SPEC, (
        "liquibase-postgresql must be the conda-forge dialect extension "
        f"{EXTENSION_SPEC!r}; SelfExplainML's 42.7.13 is the retired driver "
        f"build (got {deps.get('liquibase-postgresql')!r})"
    )


def _conda_pkg_version(url: str, package: str) -> str | None:
    """Version for ``package`` in a conda URL, matching the exact name."""
    pattern = re.compile(
        rf"/{re.escape(package)}-(?P<version>\d+(?:\.\d+)*)-[^/]+\.conda(?:\.bz2)?$",
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
    assert versions, f"pixi.lock {PLATFORM_ENV} must select liquibase {LIQUIBASE_SPEC}"
    for raw in versions:
        version = Version(raw)
        assert version >= LIQUIBASE_FLOOR, (
            f"liquibase {raw} is below {LIQUIBASE_SPEC}; "
            "5.0.2/5.0.3 SEARCH_PATH is a silent wrong-schema defect"
        )


def _assert_lock_jdbc_present(urls: list[str]) -> None:
    versions = _versions_for_package(urls, "pgjdbc")
    assert versions, (
        f"pixi.lock {PLATFORM_ENV} must include pgjdbc {JDBC_SPEC} "
        "(vendored JDBC; air-gap)"
    )
    for raw in versions:
        assert Version(raw) >= JDBC_FLOOR, f"pgjdbc {raw} is below {JDBC_SPEC}"


def _assert_lock_extension_from_conda_forge(urls: list[str]) -> None:
    locked = [url for url in urls if _conda_pkg_version(url, "liquibase-postgresql")]
    assert locked, (
        f"pixi.lock {PLATFORM_ENV} must include the liquibase-postgresql "
        "dialect extension"
    )
    for url in locked:
        raw = _conda_pkg_version(url, "liquibase-postgresql")
        assert raw is not None
        assert Version(raw) < RETIRED_DRIVER_FLOOR, (
            f"liquibase-postgresql {raw} is the retired SelfExplainML driver "
            "build, not the dialect extension; the driver is pgjdbc"
        )
        assert "/conda-forge/" in url, (
            f"liquibase-postgresql must come from conda-forge (got {url})"
        )


def test_python_agent_platform_declares_liquibase() -> None:
    """Happy path: liquibase >=5.0.4, the conda-forge extension and pgjdbc."""
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
    del drifted["pgjdbc"]
    with pytest.raises(AssertionError, match="pgjdbc"):
        _assert_liquibase_pins(drifted)


def test_extension_pin_admitting_the_retired_driver_reds() -> None:
    """Drift: the pre-27.5 `liquibase-postgresql >=42.7.13` spec must fail."""
    drifted = dict(_platform_deps())
    drifted["liquibase-postgresql"] = ">=42.7.13"
    with pytest.raises(AssertionError, match="liquibase-postgresql"):
        _assert_liquibase_pins(drifted)


def test_liquibase_spec_below_504_reds() -> None:
    """Drift: a liquibase floor that admits 5.0.3 must fail."""
    drifted = dict(_platform_deps())
    drifted["liquibase"] = ">=5.0.3"
    with pytest.raises(AssertionError, match="liquibase"):
        _assert_liquibase_pins(drifted)


def test_lock_selects_liquibase_504_extension_and_jdbc() -> None:
    """Happy path: lock URLs include liquibase >=5.0.4, the extension and pgjdbc."""
    urls = readers.pixi_env_conda_urls(PLATFORM_ENV)
    assert urls, f"pixi.lock {PLATFORM_ENV} package list is empty"
    _assert_lock_liquibase_floor(urls)
    _assert_lock_jdbc_present(urls)
    _assert_lock_extension_from_conda_forge(urls)


def test_lock_selecting_liquibase_503_reds() -> None:
    """Drift: a locked liquibase 5.0.3 URL must fail."""
    urls = [
        "https://conda.anaconda.org/SelfExplainML/linux-64/"
        "liquibase-5.0.3-h123_0.conda",
    ]
    with pytest.raises(AssertionError, match="5.0.3"):
        _assert_lock_liquibase_floor(urls)


def test_lock_selecting_the_retired_driver_build_reds() -> None:
    """Drift: a locked SelfExplainML liquibase-postgresql 42.7.13 must fail."""
    urls = [
        "https://conda.anaconda.org/SelfExplainML/noarch/"
        "liquibase-postgresql-42.7.13-h59285b8_0.conda",
    ]
    with pytest.raises(AssertionError, match="42.7.13"):
        _assert_lock_extension_from_conda_forge(urls)
