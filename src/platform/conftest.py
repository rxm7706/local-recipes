"""Platform-root pytest hooks.

CAP-3 / steward 16.2: unit and CI tests are a local runtime. setdefault so a
developer shell that already exported COMPONENT_RUNTIME=local is untouched, and
so deployed-only startup refusals do not fire under ``--ds=config.settings.test``.
"""

from __future__ import annotations

import fcntl
import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

if TYPE_CHECKING:
    from collections.abc import Iterator

import pytest
import structlog

_STRUCTLOG_CONFIG_KEYS = (
    "processors",
    "wrapper_class",
    "context_class",
    "logger_factory",
    "cache_logger_on_first_use",
)


def _copy_structlog_config() -> dict[str, Any]:
    cfg = structlog.get_config()
    return {**cfg, "processors": list(cfg["processors"])}


def _structlog_config_diff_keys(
    baseline: dict[str, Any],
    current: dict[str, Any],
) -> list[str]:
    differing: list[str] = []
    for key in _STRUCTLOG_CONFIG_KEYS:
        if key not in baseline or key not in current:
            differing.append(key)
            continue
        if key == "processors":
            if list(baseline[key]) != list(current[key]):
                differing.append(key)
        elif baseline[key] != current[key]:
            differing.append(key)
    return differing


_structlog_session_baseline: dict[str, Any] | None = None

os.environ.setdefault("COMPONENT_RUNTIME", "local")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")
# Story 78.1: Langflow auto-login is forced off, so the mounted app only starts
# with a superuser password from the environment (a deployed boot gets it from a
# Secret). A throwaway for the lanes that boot Langflow -- a harness value, never
# a settings default; the stage-1 refusal tests delete it to prove the absence.
os.environ.setdefault("LANGFLOW_SUPERUSER_PASSWORD", "pytest-throwaway-langflow-pw")


@pytest.fixture(autouse=True)
def _isolate_caches():
    """Start every test with an empty cache.

    The test settings use LocMemCache, which lives for the whole pytest
    process — unlike the database, nothing rolls it back between tests. Story
    42.2 put per-subject rate-limit buckets in that cache, so without this a
    subject's spend would accumulate across every test that used it and the
    suite's outcome would depend on collection order. Clearing is the fix that
    keeps the real limiter in the path rather than stubbing it out.
    """
    from django.core.cache import caches  # noqa: PLC0415

    for alias in caches:
        caches[alias].clear()

    import django_atlas_portal.mcp_asgi as atlas_mcp  # noqa: PLC0415
    import django_doctor_portal.mcp_asgi as doctor_mcp  # noqa: PLC0415
    import django_herald_portal.mcp_asgi as herald_mcp  # noqa: PLC0415
    import django_marshal_portal.mcp_asgi as marshal_mcp  # noqa: PLC0415
    import django_mason_portal.mcp_asgi as mason_mcp  # noqa: PLC0415
    import django_scribe_portal.mcp_asgi as scribe_mcp  # noqa: PLC0415
    import django_steward_portal.mcp_asgi as steward_mcp  # noqa: PLC0415
    import django_warden_fabric.mcp_asgi as warden_mcp  # noqa: PLC0415
    from django_pyforge import supervisor  # noqa: PLC0415

    atlas_mcp._APP = None  # noqa: SLF001
    warden_mcp._SERVER = None  # noqa: SLF001
    _cache_mods = (
        doctor_mcp,
        herald_mcp,
        marshal_mcp,
        mason_mcp,
        scribe_mcp,
        steward_mcp,
    )
    for mod in _cache_mods:
        mod._CACHE.clear()  # noqa: SLF001
    supervisor._runners.clear()  # noqa: SLF001


@pytest.fixture(autouse=True)
def _guard_structlog_configuration(request: pytest.FixtureRequest) -> Iterator[None]:
    """Fail tests that leave structlog configured differently from session baseline."""
    global _structlog_session_baseline  # noqa: PLW0603
    if _structlog_session_baseline is None:
        _structlog_session_baseline = _copy_structlog_config()
    yield
    current = structlog.get_config()
    differing = _structlog_config_diff_keys(_structlog_session_baseline, current)
    if not differing:
        return
    baseline = _structlog_session_baseline
    structlog.configure(**{**baseline, "processors": list(baseline["processors"])})
    pytest.fail(
        f"structlog configuration leak in {request.node.nodeid}; "
        f"differing keys: {', '.join(differing)}"
    )


@pytest.fixture(autouse=True)
def real_gh_attempts(monkeypatch):
    """No test may run the operator's ``gh`` (Story 16.1); see ``tests/gh_guard.py``."""
    from tests.gh_guard import refuse_real_gh  # noqa: PLC0415

    yield from refuse_real_gh(monkeypatch)


_REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def pyforge_warden_env(tmp_path_factory: pytest.TempPathFactory) -> None:
    """Install the ``pyforge-warden`` environment once, before a test runs it.

    Steward Story 117.23. The first ``pixi run -e pyforge-warden`` of a checkout
    builds the environment's path packages (pyforge-core, pyforge-testing-kit,
    pyforge-warden) and reinstalls them. Two of them at once let one process
    uninstall ``pyforge-warden`` while the other is running it, which exits 1
    with no output (Platform CI's test shard 2, PR #2409). xdist workers share
    the parent of the base temporary directory, so an exclusive lock there makes
    one worker install while the others wait; ``pixi install`` of an installed
    environment returns at once.
    """
    lock_path = tmp_path_factory.getbasetemp().parent / "pyforge-warden-install.lock"
    with lock_path.open("w", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        done = subprocess.run(
            ["pixi", "install", "-e", "pyforge-warden"],  # noqa: S607 -- resolved via PATH like every other pixi invocation in this suite
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    if done.returncode != 0:
        pytest.fail(
            f"pixi install -e pyforge-warden exited {done.returncode}:\n"
            f"{done.stderr[-4000:]}"
        )
