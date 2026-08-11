"""Shared, behaviour-free data shapes returned across a layer boundary
(AD-8, Consistency Conventions: "Data shapes... `@dataclass(frozen=True)`
in `models.py`").

Story 2.1 creates this module. Two shapes land here today:

`CfeResult` is new -- the return type of every CAPTURE-mode invocation
`cfe.py` makes (AD-3, AD-4, FR-4). `DoctorReport` is not new: it moves here
verbatim (unchanged fields) from `doctor.py`, the architecture's one
sanctioned pre-existing-shape move (Consistency Conventions, "the one
landed divergence, `DoctorReport` in `doctor.py`, moves in with a
`doctor.py` re-export so no import or test churns"). `doctor.py` re-exports
it via `from .models import DoctorReport`, so the pre-existing `from
pyforge.mason.doctor import DoctorReport` import (`tests/unit/test_cli.py`)
keeps resolving unchanged.

This module is a dependency-direction *leaf*: nothing under `pyforge/mason/`
may import from it in a way that risks a cycle back through it, so `cli.py`,
`render.py`, and every use-case can import it freely. "Leaf" is about import
*direction*, not import *count* -- this module may still import `EngineStatus`
from `.engines` (itself a leaf with zero internal-package imports), because
that import points further outward, not back inward. Only `DoctorReport`
makes this move; `EngineStatus`, `ImportFloorResult`, `ResolvedCfeRoot`, and
`ResolvedCfeInterpreter` are deliberately left in their owning modules (spec
Never boundary) -- the architecture names `DoctorReport` alone as the
one landed divergence.

Later stories add `ShipReceipt`, `ShipTargetResult`, and `LockResult` here
(architecture Structural Seed) -- none of that exists yet.
"""

from __future__ import annotations

from dataclasses import dataclass

from .engines import EngineStatus


@dataclass(frozen=True)
class CfeResult:
    """The outcome of one CAPTURE-mode CFE invocation (AD-3, AD-4, FR-4).

    `returncode` is the child's raw exit code -- a non-zero value is data on
    this dataclass, never raised as an exception (AD-4): the caller decides
    what a given script's failure means, `cfe.py` only reports it. `stdout`
    and `stderr` are the child's full captured text, decoded with
    `encoding="utf-8", errors="replace"` (never a bare `text=True`, whose
    locale-derived default can silently mangle a valid UTF-8 body under
    `LC_ALL=C` -- the same rationale `run_streamed` documents for STREAM
    mode). `json_body` is the value `cfe._extract_json` parsed out of
    `stdout`, or `None` when no parseable JSON body was present at all --
    FR-4 says a parsed body is present "when one is present," so its absence
    is a normal outcome recorded here, not a reason to raise.
    """

    returncode: int
    stdout: str
    stderr: str
    json_body: object | None


@dataclass(frozen=True)
class DoctorReport:
    """`mason doctor`'s full self-diagnosis (FR-34): Mason's own version,
    the resolved CFE root and which chain step found it, the selected
    interpreter and which chain step selected it, the import-floor outcome,
    which verbs are unavailable as a consequence, and every known engine's
    presence/version."""

    mason_version: str
    cfe_root: str | None
    cfe_root_step: str
    cfe_interpreter: str
    cfe_interpreter_step: str
    cfe_import_floor_satisfied: bool
    cfe_import_floor_missing: tuple[str, ...]
    unavailable_verbs: tuple[str, ...]
    engines: tuple[EngineStatus, ...]
