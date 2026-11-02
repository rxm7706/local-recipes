"""Fleet inventory and scan helpers (Stories 16.1 / 16.2 / 16.5 / 16.7)."""

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
FLEET_FIX_PROPOSALS_FLAG = "pyforge.warden.fleet_fix_proposals"
FLEET_INVENTORY_FLAG = "pyforge.warden.fleet_inventory"
FLEET_PROJECT_ITEMS_FLAG = "pyforge.warden.fleet_project_items"

# Steward-provisioned credential names — passed via subprocess env only, never URLs/logs.
_GIT_CREDENTIAL_ENV_KEYS = (
    "GITHUB_TOKEN",
    "GH_TOKEN",
    "GH_ENTERPRISE_TOKEN",
    "GITHUB_ENTERPRISE_TOKEN",
)

_SECRET_IN_URL = re.compile(r"(https?://)[^/@]+@")

# Story 16.7: each ``git`` call a fleet clone makes is bounded, well inside the
# repo tasks' soft limit (240 s, ``FLEET_INVENTORY_SOFT_TIME_LIMIT_SECONDS``), so a
# hung clone fails as that repo's typed error and the scan still has time to run.
# Read at call time, so a test can shorten it.
FLEET_CLONE_TIMEOUT_SECONDS = 120.0

# Story 16.7: an approval of a proposal older than this is refused (a failed
# actuation, no clone, no forge call). The setting changes it; this is its default.
FLEET_APPROVAL_EXPIRY_SETTING = "WARDEN_FLEET_APPROVAL_EXPIRY_SECONDS"
FLEET_APPROVAL_EXPIRY_DEFAULT_SECONDS = 7 * 24 * 60 * 60


class FleetCloneError(Exception):
    """A fleet ``git`` call failed; the text is scrubbed and names no environment."""


class FleetCloneTimeoutError(FleetCloneError):
    """A fleet ``git`` call outlived ``FLEET_CLONE_TIMEOUT_SECONDS`` (Story 16.7)."""


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
    timeout: float | None = None,
) -> str:
    """Shallow-clone ``branch`` into ``dest`` (0700). Returns the resolved commit SHA.

    Each ``git`` call is bounded by ``timeout`` (default
    ``FLEET_CLONE_TIMEOUT_SECONDS``); a call that outlives it is killed and raises
    ``FleetCloneTimeoutError`` naming the bound (Story 16.7). A ``git`` failure is
    re-raised as ``FleetCloneError`` with no chained ``subprocess`` exception: a
    logged traceback renders frame locals, and ``subprocess.run``'s hold the
    credential-bearing environment."""
    bound = FLEET_CLONE_TIMEOUT_SECONDS if timeout is None else timeout
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
    try:
        subprocess.run(  # noqa: S603
            argv,
            check=True,
            env=git_clone_env(),
            capture_output=True,
            text=True,
            timeout=bound,
        )
        rev = subprocess.run(  # noqa: S603
            ["git", "-C", str(dest), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            env=git_clone_env(),
            timeout=bound,
        )
    except subprocess.TimeoutExpired:
        msg = f"git clone timed out after {bound:g} s ({scrub_url_for_log(clone_url)})"
        raise FleetCloneTimeoutError(msg) from None
    except subprocess.CalledProcessError as exc:
        detail = scrub_url_for_log((exc.stderr or "").strip())[-500:]
        msg = f"git exited {exc.returncode} ({scrub_url_for_log(clone_url)}): {detail}"
        raise FleetCloneError(msg) from None
    return rev.stdout.strip()


def mkdtemp_clone_dir(prefix: str = "warden-fleet-") -> Path:
    """Create a throwaway clone directory at mode 0700."""
    path = Path(tempfile.mkdtemp(prefix=prefix))
    path.chmod(0o700)
    return path


def remove_clone_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)
