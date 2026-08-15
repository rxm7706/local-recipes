"""seed/state -- Genesis's tool-owned state document (Story 10.2).

Re-exports ``store.py``'s public API so callers write
``from pyforge.marshal.seed.state import read_state`` rather than reaching
into the submodule directly (mirroring ``seed/engine/__init__.py``).
``store.py`` remains the only module that reads or writes
``.marshal/seed-state.yml``, and the packaged ``schema.json`` beside it is
that file's wire contract.
"""

from __future__ import annotations

from .store import (
    STATE_KEYS,
    LegacyArtifact,
    ManagedArtifact,
    RegionSpanRecord,
    SeedState,
    copier_data,
    read_state,
    seed_model_version,
    state_path,
    utc_timestamp,
    write_state,
)

__all__ = [
    "STATE_KEYS",
    "LegacyArtifact",
    "ManagedArtifact",
    "RegionSpanRecord",
    "SeedState",
    "copier_data",
    "read_state",
    "seed_model_version",
    "state_path",
    "utc_timestamp",
    "write_state",
]
