"""Non-station chrome surfaces. Story 52.1 — mybmad is a consume sidecar.

Not station nine. Not ``/stations/mybmad/``. Not ``/console/``.
The process stays the ``mybmad`` launcher.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

MYBMAD_SCHEMA = "mybmad"
MYBMAD_SIDECAR_NAME = "mybmad"
MYBMAD_PUBLIC_URL_ENV = "MYBMAD_PUBLIC_URL"
MYBMAD_DEFAULT_PUBLIC_URL = "http://127.0.0.1:3000"
FORBIDDEN_MYBMAD_MOUNTS = frozenset({"/console/", "/stations/mybmad/"})


@dataclass(frozen=True)
class SidecarSurface:
    """A chrome tile that is not a PortalConfig / station."""

    name: str
    href: str
    kind: str = "sidecar"


def mybmad_public_url() -> str:
    """Browser URL of the sidecar process (launcher), never a Django mount."""
    raw = os.environ.get(MYBMAD_PUBLIC_URL_ENV, MYBMAD_DEFAULT_PUBLIC_URL).strip()
    return raw.rstrip("/") or MYBMAD_DEFAULT_PUBLIC_URL


def mybmad_sidecar() -> SidecarSurface:
    href = mybmad_public_url()
    if any(href.endswith(mount.rstrip("/")) or mount in href for mount in FORBIDDEN_MYBMAD_MOUNTS):
        raise ValueError("mybmad chrome href must not be /console/ or /stations/mybmad/")
    return SidecarSurface(name=MYBMAD_SIDECAR_NAME, href=href)
