"""pdl:CAP-1 / steward 56.1 — local leaf on platform-dev only.

``config.settings.local`` always installs ``debug_toolbar``. The pin
belongs on ``[feature.platform-dev]``, never on the image feature
``python-agent-platform``.
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.policy import readers

TOOLBAR = "django-debug-toolbar"
TOOLBAR_SPEC = ">=8.0.0"
DEV_FEATURE = "platform-dev"
IMAGE_FEATURE = "python-agent-platform"


def _feature_deps(feature: str, manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    pixi = manifest if manifest is not None else readers.pixi_manifest()
    table = pixi.get("feature", {}).get(feature, {})
    deps = table.get("dependencies", {})
    assert isinstance(deps, dict), f"{feature}.dependencies must be a table"
    return deps


def _assert_toolbar_on_platform_dev(deps: dict[str, Any]) -> None:
    assert TOOLBAR in deps, (
        "pixi.toml [feature.platform-dev.dependencies] must pin "
        f"{TOOLBAR} (steward 56.1 / pdl:CAP-1)"
    )
    assert deps.get(TOOLBAR) == TOOLBAR_SPEC, (
        f"{TOOLBAR} must be pinned {TOOLBAR_SPEC!r} "
        f"(got {deps.get(TOOLBAR)!r})"
    )


def _assert_toolbar_absent_from_image(deps: dict[str, Any]) -> None:
    assert TOOLBAR not in deps, (
        "pixi.toml [feature.python-agent-platform.dependencies] must not "
        f"pin {TOOLBAR} (image solve; toolbar is local-leaf only)"
    )


def test_platform_dev_declares_debug_toolbar() -> None:
    _assert_toolbar_on_platform_dev(_feature_deps(DEV_FEATURE))


def test_python_agent_platform_omits_debug_toolbar() -> None:
    _assert_toolbar_absent_from_image(_feature_deps(IMAGE_FEATURE))


def test_removing_platform_dev_toolbar_pin_reds() -> None:
    drifted = dict(_feature_deps(DEV_FEATURE))
    drifted.pop(TOOLBAR, None)
    with pytest.raises(AssertionError, match="platform-dev"):
        _assert_toolbar_on_platform_dev(drifted)


def test_image_feature_gaining_toolbar_reds() -> None:
    drifted = dict(_feature_deps(IMAGE_FEATURE))
    drifted[TOOLBAR] = TOOLBAR_SPEC
    with pytest.raises(AssertionError, match="python-agent-platform"):
        _assert_toolbar_absent_from_image(drifted)


def test_lock_platform_dev_selects_debug_toolbar() -> None:
    urls = readers.pixi_env_conda_urls(DEV_FEATURE)
    assert urls, f"pixi.lock {DEV_FEATURE} package list is empty"
    assert any(f"/{TOOLBAR}-" in url for url in urls), (
        f"pixi.lock {DEV_FEATURE} must select {TOOLBAR}"
    )


def test_lock_image_env_omits_debug_toolbar() -> None:
    urls = readers.pixi_env_conda_urls(IMAGE_FEATURE)
    assert urls, f"pixi.lock {IMAGE_FEATURE} package list is empty"
    assert not any(f"/{TOOLBAR}-" in url for url in urls), (
        f"pixi.lock {IMAGE_FEATURE} must not select {TOOLBAR}"
    )
