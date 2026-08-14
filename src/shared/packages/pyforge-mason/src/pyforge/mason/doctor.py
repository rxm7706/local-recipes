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

Story 3.6 extends `build_report` with `conda_forge_ship_ready`/
`conda_forge_ship_blockers` (FR-23, D-10): a structural PROXY for
`package.py::ship_conda_forge`'s own shipping preconditions, not an exact
restatement of them -- `mason doctor` takes no recipe-path argument (out
of this story's scope), so it can neither see precondition #1 (a recipe
path was given) nor check #2's exact `<cfe-root>/recipes/<name>/` equality
for any particular recipe. What it reports instead is the set of
conditions observable without a recipe: root unresolved is one blocker,
a root that cannot be expanded/resolved at all is a second, root resolved
but `<root>/recipes` not a directory is a third, and an incomplete import
floor is the fourth. Note the proxy is deliberately stricter in one
direction -- `ship_conda_forge` itself performs no `recipes/` existence
check (it resolves paths only, matching `recipe.py::submit()`'s own
no-existence-check precedent), so a `False` here does not by itself prove
a ship would fail.

The import-floor blocker (follow-up review pass, 2026-08-13) is not one of
D-10's two preconditions but gates the same path just as structurally:
`ship_conda_forge` delegates to `recipe.py::submit()`, and an incomplete
floor is already exactly why `unavailable_verbs` names `"recipe"` above.
Omitting it let one report answer the same question two ways --
`conda_forge_ship_ready=True` beside an `unavailable_verbs` naming the
verb the ship path runs through.

`resolved_root.root` is `.expanduser().resolve()`d again here before the
`recipes` check (review pass, 2026-08-13): `resolve_cfe_root`'s
flag/environment steps return an UN-resolved `Path` (e.g. a literal `~` or
a relative value), and comparing that directly against the filesystem
would misreport readiness for exactly the inputs `package.py::
ship_conda_forge` itself resolves against -- mirrors that function's own
identical resolution. The `is_dir()` check (and the resolution before it)
runs inside a `try`/`except (OSError, ValueError, RuntimeError)` (review
pass, 2026-08-13) so a pathological root value cannot break this
function's own "never raises" invariant: `RuntimeError` is in that tuple
because `Path.expanduser()` -- NOT an `OSError` subclass for this failure
-- raises it whenever a leading `~`/`~user` cannot be expanded (an unknown
user, or `HOME` unset), which a `--cfe-root`/`MASON_CFE_ROOT` value
reaches this function unvalidated. Each of those failures becomes its own
blocker rather than a crash, and each names its own cause: a root that
cannot be resolved says so (follow-up review pass, 2026-08-13 -- calling
it a missing `recipes/` directory named the wrong cause and implied an
impossible remedy), a permission-denied stat (`OSError`) is treated as
`not a directory` while keeping the RESOLVED spelling, and a `None` root
paired with a non-`not-found` step reports the root as unresolved.
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

    blockers: list[str] = []
    # `root is None` is checked alongside the step, not left to the step
    # alone: line 122 below still guards the same attribute that way, and
    # an `AttributeError` from a `None` root would escape the `except`
    # tuple entirely and break this function's own never-raises invariant.
    if resolved_root.step == STEP_NOT_FOUND or resolved_root.root is None:
        blockers.append("the CFE root is unresolved")
    else:
        # Resolution and the stat are guarded SEPARATELY, and report
        # DIFFERENT blockers. A root that cannot be expanded or resolved at
        # all is not a missing `recipes/` directory: reporting it as one
        # named a cause that was not the real one and implied a remedy --
        # create that directory -- impossible at a path that cannot exist.
        # A denied stat, by contrast, keeps the RESOLVED spelling rather
        # than falling back to the raw one, so a single input never prints
        # two spellings of the same path.
        try:
            recipes_dir = resolved_root.root.expanduser().resolve() / "recipes"
        except (OSError, ValueError, RuntimeError) as exc:
            blockers.append(f"the CFE root {resolved_root.root} cannot be resolved: {exc}")
        else:
            try:
                recipes_dir_is_present = recipes_dir.is_dir()
            except OSError:
                recipes_dir_is_present = False
            if not recipes_dir_is_present:
                blockers.append(f"{recipes_dir} is not a directory")

    # The import floor gates this target too: `package.py::ship_conda_forge`
    # delegates to `recipe.py::submit()`, and an incomplete floor is already
    # why `unavailable_verbs` above names `recipe`. Without this blocker one
    # report could claim `conda_forge_ship_ready=True` while, three fields
    # away, `unavailable_verbs` named the very verb the ship path runs
    # through -- a self-contradiction in the command whose whole job is to
    # let a user learn the boundary BEFORE attempting a release.
    if floor_result.missing:
        blockers.append(
            "the CFE import floor is incomplete, so the `recipe` verb this target "
            f"delegates to is unavailable: {', '.join(floor_result.missing)}",
        )

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
        conda_forge_ship_ready=not blockers,
        conda_forge_ship_blockers=tuple(blockers),
    )
