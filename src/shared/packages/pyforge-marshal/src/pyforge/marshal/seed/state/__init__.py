"""seed/state -- Genesis's tool-owned state document (Story 10.2).

Re-exports ``store.py``'s public API so callers write
``from pyforge.marshal.seed.state import read_state`` rather than reaching
into the submodule directly (mirroring ``seed/engine/__init__.py``).
``store.py`` remains the only module that reads or writes
``.marshal/seed-state.yml``, and the packaged ``schema.json`` beside it is
that file's wire contract.

Story 8.5 adds the five opt-out helpers (``opt_out_key``,
``opt_out_key_or_none``, ``is_opted_out``, ``record_opt_out``,
``clear_opt_out``) to that same surface -- pure functions over the
already-shipped ``opted_out`` key, no twelfth key and no schema change -- so
``detect``/``plan`` reach them by the same ``from ...seed.state import ...``
spelling as everything else here. ``opt_out_key_or_none`` is exported
alongside the raising ``opt_out_key`` on purpose: ``plan/build.py`` needs the
"inadmissible key means not-opted-out" answer rather than the raise, and a
consumer that cannot reach it re-implements it (which is what ``build.py``
had done, with its own ``try``/``except ValueError``).
"""

from __future__ import annotations

from .store import (
    STATE_KEYS,
    LegacyArtifact,
    ManagedArtifact,
    RegionSpanRecord,
    SeedState,
    clear_opt_out,
    copier_data,
    is_opted_out,
    opt_out_key,
    opt_out_key_or_none,
    read_state,
    record_opt_out,
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
    "clear_opt_out",
    "copier_data",
    "is_opted_out",
    "opt_out_key",
    "opt_out_key_or_none",
    "read_state",
    "record_opt_out",
    "seed_model_version",
    "state_path",
    "utc_timestamp",
    "write_state",
]
