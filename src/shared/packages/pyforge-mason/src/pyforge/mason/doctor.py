"""`mason doctor` -- self-diagnosis (FR-34).

`cli.py`'s `doctor` branch was Story 1.4's placeholder (`"not implemented yet"`)
-- nothing composed Stories 1.5-1.7's resolution/probe outcomes into a real
report, and nothing reported engine presence/version at all. This module is
that composition: `build_report` calls `resolve.py`'s two pure chains
(`resolve_cfe_root`, `resolve_cfe_interpreter`), lazily imports `cfe` to call
its non-raising `probe_import_floor`, and calls `engines.probe_known_engines()`
-- folding all of it into one frozen `DoctorReport`, never raising.

`cfe` is imported inside `build_report`'s body, not at module level, per
AD-6's text naming `doctor.py` alongside `package.py`/`environment.py` as
CFE-independent: `doctor.py` must import cleanly and must never fail because
CFE is unresolvable. `probe_import_floor` itself never raises (Story 1.6),
so this satisfies "must never fail" even though the import happens.
`tests/meta/test_capability_tiers.py` guards this file for exactly that: no
module-level `cfe` import, ever.

`build_report` always probes the import floor, regardless of whether
`resolve_cfe_root` found a root: interpreter selection (`resolve_cfe_
interpreter`) is a chain independent of the root chain, and "can the
selected interpreter import CFE's floor" is a question about that
interpreter, not about whether CFE's location on disk is known. Only
`ensure_import_floor`/`ensure_cfe_root` (the raising siblings of the
functions this module calls) are off-limits here -- see the spec's
Boundaries & Constraints.

`unavailable_verbs` names `"recipe"` when the CFE root is unresolved OR the
import floor has any gap -- either structurally blocks Epic 2's
not-yet-built `recipe.py`. `package`/`environment` are never listed: AD-6
already makes them CFE-independent, so no gap reported here can ever affect
them.

`DoctorReport.cfe_root` is a `str | None`, not `resolve.py`'s own `Path |
None` -- `cli.py` converts this report via `dataclasses.asdict(report)`
before handing the result to `render.write`, whose `render_json` passes it
straight to `json.dumps`, which cannot serialize a `Path`; converting once
here keeps that conversion out of `render.py`, which owns formatting, not
domain knowledge about what `resolve.py`'s outcomes look like.

Story 2.1 moves `DoctorReport` itself out of this module and into
`models.py` -- the architecture's one sanctioned pre-existing-shape move
(Consistency Conventions). It is re-exported below via `from .models import
DoctorReport`, so the pre-existing `from pyforge.mason.doctor import
DoctorReport` import (`tests/unit/test_cli.py`) keeps resolving unchanged,
and `build_report`'s composition logic is otherwise untouched.

Story 3.1's Engine protocol supersedes only `engines/__init__.py`'s
probe-only seed (see that module's docstring); this module's composition
shape is unaffected by that later story.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from . import __version__
from .engines import probe_known_engines
from .models import DoctorReport
from .resolve import STEP_NOT_FOUND, resolve_cfe_interpreter, resolve_cfe_root


def build_report(
    cfe_root_arg: str | None,
    cfe_python_arg: str | None,
    environ: Mapping[str, str],
    start_directory: Path,
) -> DoctorReport:
    """Build the full `DoctorReport`. Never raises (spec Always boundary).

    `cfe_root_arg`/`cfe_python_arg` are the raw `--cfe-root`/`--cfe-python`
    flag values (`str | None`), `environ` is a `Mapping[str, str]` (typically
    `os.environ`), and `start_directory` is the `Path` the CFE-root walk
    starts from -- the same three-plus-one shape `resolve.py`'s two chains
    already take, passed straight through.
    """
    resolved_root = resolve_cfe_root(cfe_root_arg, environ, start_directory)
    resolved_interpreter = resolve_cfe_interpreter(cfe_python_arg, environ)

    from . import cfe  # lazy -- AD-6, see module docstring

    floor_result = cfe.probe_import_floor(resolved_interpreter.path)

    unavailable_verbs: tuple[str, ...] = ()
    if resolved_root.step == STEP_NOT_FOUND or floor_result.missing:
        unavailable_verbs = ("recipe",)

    return DoctorReport(
        mason_version=__version__,
        cfe_root=str(resolved_root.root) if resolved_root.root is not None else None,
        cfe_root_step=resolved_root.step,
        cfe_interpreter=resolved_interpreter.path,
        cfe_interpreter_step=resolved_interpreter.step,
        cfe_import_floor_satisfied=not floor_result.missing,
        cfe_import_floor_missing=floor_result.missing,
        unavailable_verbs=unavailable_verbs,
        engines=probe_known_engines(),
    )
