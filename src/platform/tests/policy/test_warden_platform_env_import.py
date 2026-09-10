"""Warden engine importable in the platform image env (steward 48.11 / warden-B7).

``django_warden_fabric/tasks.py`` lazy-imports ``pyforge.warden.cli``; the
``python-agent-platform`` pixi feature (what ``src/platform/Containerfile``
installs) must declare ``pyforge-warden`` as a path dependency.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import Any

from tests.policy import readers

PLATFORM_ENV = "python-agent-platform"
_WARDEN_PATH = "src/shared/packages/pyforge-warden"


def _platform_deps(manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    pixi = manifest if manifest is not None else readers.pixi_manifest()
    feature = pixi.get("feature", {}).get("python-agent-platform", {})
    deps = feature.get("dependencies", {})
    assert isinstance(deps, dict), "python-agent-platform.dependencies must be a table"
    return deps


def test_python_agent_platform_declares_pyforge_warden_path_dep() -> None:
    deps = _platform_deps()
    warden = deps.get("pyforge-warden")
    assert isinstance(warden, dict), (
        "pixi.toml [feature.python-agent-platform.dependencies] must declare "
        "pyforge-warden as a path dependency (Story 48.11)"
    )
    assert warden.get("path") == _WARDEN_PATH, (
        f"pyforge-warden path must be {_WARDEN_PATH!r} (got {warden.get('path')!r})"
    )


def test_python_agent_platform_lock_includes_pyforge_warden() -> None:
    lock_text = readers.pixi_lock_text()
    header = f"  {PLATFORM_ENV}:"
    lines = lock_text.splitlines()
    start: int | None = None
    for index, line in enumerate(lines):
        if line == header:
            start = index
            break
    assert start is not None, f"pixi.lock has no environments.{PLATFORM_ENV} block"
    block: list[str] = []
    for line in lines[start + 1 :]:
        if line.startswith("  ") and not line.startswith("    ") and line.endswith(":"):
            break
        block.append(line)
    joined = "\n".join(block)
    assert "conda_source: pyforge-warden[" in joined, (
        f"pixi.lock environments.{PLATFORM_ENV} must resolve pyforge-warden "
        "(Story 48.11)"
    )


def test_python_agent_platform_imports_pyforge_warden_cli() -> None:
    pixi = shutil.which("pixi")
    assert pixi is not None, "pixi must be on PATH for the import oracle"
    proc = subprocess.run(  # noqa: S603 -- fixed argv, no shell
        [
            pixi,
            "run",
            "-e",
            PLATFORM_ENV,
            "python",
            "-c",
            "import pyforge.warden.cli",
        ],
        cwd=readers.REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, (
        "python-agent-platform must import pyforge.warden.cli "
        f"(exit {proc.returncode}): {proc.stderr or proc.stdout}"
    )
