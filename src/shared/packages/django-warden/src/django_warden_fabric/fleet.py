"""Fleet inventory and scan helpers (Stories 16.1 / 16.2)."""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

FLEET_SCAN_FLAG = "pyforge.warden.fleet_scan"

# Steward-provisioned credential names — passed via subprocess env only, never URLs/logs.
_GIT_CREDENTIAL_ENV_KEYS = (
    "GITHUB_TOKEN",
    "GH_TOKEN",
    "GH_ENTERPRISE_TOKEN",
    "GITHUB_ENTERPRISE_TOKEN",
)

_SECRET_IN_URL = re.compile(r"(https?://)[^/@]+@")


def scrub_url_for_log(url: str) -> str:
    """Remove embedded credentials from a URL before logging."""
    return _SECRET_IN_URL.sub(r"\1", url)


def git_clone_env() -> dict[str, str]:
    """Environment for ``git clone`` — credentials from Steward, never in argv."""
    return os.environ.copy()


def shallow_clone(
    *,
    clone_url: str,
    branch: str,
    dest: Path,
) -> str:
    """Shallow-clone ``branch`` into ``dest`` (0700). Returns the resolved commit SHA."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.mkdir(mode=0o700, exist_ok=True)
    argv = [
        "git",
        "clone",
        "--depth",
        "1",
        "--branch",
        branch,
        clone_url,
        str(dest),
    ]
    logger.info(
        "fleet clone branch=%s url=%s dest=%s",
        branch,
        scrub_url_for_log(clone_url),
        dest,
    )
    subprocess.run(  # noqa: S603
        argv,
        check=True,
        env=git_clone_env(),
        capture_output=True,
        text=True,
    )
    rev = subprocess.run(  # noqa: S603
        ["git", "-C", str(dest), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        env=git_clone_env(),
    )
    return rev.stdout.strip()


def mkdtemp_clone_dir(prefix: str = "warden-fleet-") -> Path:
    """Create a throwaway clone directory at mode 0700."""
    path = Path(tempfile.mkdtemp(prefix=prefix))
    path.chmod(0o700)
    return path


def remove_clone_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)
