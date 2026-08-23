"""Air-gap distribution contract socket (mason Story 9.2).

Ships the CONTRACT and an empty backend registry so any external installer
(Miniforge/constructor or vendor) can register and validate as a SEPARATE
deliverable. Never builds a distributable here.

Mirrors steward ``provision.py``'s ``_SUPPORTED_MODULES`` one-entry-at-a-time
registry precedent — this registry starts EMPTY by design.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

__all__ = (
    "AIRGAP_CONTRACT",
    "SUPPORTED_DISTRIBUTABLES",
    "DistributableBackend",
    "register_distributable",
    "validate_backend_shape",
)

#: Documented contract any air-gap distributable must satisfy.
#: Kept as a frozen mapping so tests can assert keys without re-parsing prose.
AIRGAP_CONTRACT: Mapping[str, str] = {
    "mirrored_channel_set": (
        "A documented, pinned set of conda/pixi channels the offline tree "
        "mirrors (exact channel URLs + any auth shape)."
    ),
    "pixi_bootstrap_path": (
        "A reproducible path from a bare machine to a working pixi "
        "installation that can resolve this repo's environments without "
        "public-network egress."
    ),
    "verification_hooks": (
        "Post-install checks (channel reachability, pixi env materialize, "
        "optional smoke import) that prove the mirror is usable."
    ),
}


@dataclass(frozen=True)
class DistributableBackend:
    """One registered installer backend satisfying ``AIRGAP_CONTRACT``."""

    name: str
    mirrored_channel_set: tuple[str, ...]
    pixi_bootstrap_path: str
    verification_hooks: tuple[str, ...]


#: Empty by design (Story 9.2). External installers register later.
SUPPORTED_DISTRIBUTABLES: dict[str, DistributableBackend] = {}


def validate_backend_shape(backend: DistributableBackend) -> None:
    """Raise ``ValueError`` if ``backend`` does not satisfy the contract shape."""
    if not backend.name or not backend.name.strip():
        raise ValueError("backend.name must be a non-empty string")
    if not backend.mirrored_channel_set:
        raise ValueError("backend.mirrored_channel_set must be non-empty")
    if not all(isinstance(c, str) and c.strip() for c in backend.mirrored_channel_set):
        raise ValueError("mirrored_channel_set entries must be non-empty strings")
    if not backend.pixi_bootstrap_path or not backend.pixi_bootstrap_path.strip():
        raise ValueError("backend.pixi_bootstrap_path must be a non-empty string")
    if not backend.verification_hooks:
        raise ValueError("backend.verification_hooks must be non-empty")
    if not all(isinstance(h, str) and h.strip() for h in backend.verification_hooks):
        raise ValueError("verification_hooks entries must be non-empty strings")
    required = set(AIRGAP_CONTRACT)
    provided = {
        "mirrored_channel_set",
        "pixi_bootstrap_path",
        "verification_hooks",
    }
    missing = required - provided
    if missing:
        raise ValueError(f"backend missing contract keys: {sorted(missing)}")


def register_distributable(backend: DistributableBackend) -> None:
    """Validate and register a backend. Refuses duplicate names."""
    validate_backend_shape(backend)
    if backend.name in SUPPORTED_DISTRIBUTABLES:
        raise ValueError(f"distributable {backend.name!r} is already registered")
    SUPPORTED_DISTRIBUTABLES[backend.name] = backend
