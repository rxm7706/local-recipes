"""seed/engine/copier.py -- the single seam through which Genesis speaks to
Copier (Story 10.1, architecture A-04/AD-52/P-02).

P-02: "copier is imported nowhere in the codebase except this module" --
proven by ``tests/meta/test_p02_copier_sole_ownership.py``. Every other seed
module (state, plan, apply, ...) calls ``materialize()`` and never touches
``copier`` itself, its ``Worker`` internals, or any private ``copier._*``
submodule -- only the three public top-level entry points
(``copier.run_copy``/``run_update``/``run_recopy``) are ever invoked, and
only from here.

``materialize()`` NEVER targets the caller-supplied ``dst_path`` directly.
It always renders into an ephemeral staging location this module owns, then
reconciles the staged output against the packaged manifest's declared paths
before returning it as data -- nothing is "committed" to a live repo by
this module. Story 10.3's future apply runner reads the returned
``MaterializeResult`` and commits it through ``fs`` (Story 7.3).

Staging strategy is verb-dependent (Design Notes): ``COPY`` renders into a
brand-new, empty tmp directory. ``UPDATE``/``RECOPY`` need Copier's own
git-based diff-and-merge algorithm, which requires real commit history to
reason against -- so staging for those two verbs is a **local git clone of
``dst_path``** (``git clone --local``, cheap via hardlinks on a
same-filesystem tmp dir). Either way ``dst_path`` is only ever READ by this
module (to seed the clone); it is never opened for writing by this module
or by Copier.

On any failure (a Copier refusal, a manifest-boundary violation, a failed
git clone) the staging directory is removed before the exception
propagates -- "nothing is returned" (the I/O matrix's own wording) means
nothing survives either. On SUCCESS, the staging directory is deliberately
left on disk: ``MaterializeResult.staged_paths`` are absolute paths into
it, and this module has no way to know when a caller (Story 10.3's apply
runner) is done reading them -- cleanup ownership passes to that caller
once this function returns.

Every ``run_copy``/``run_update``/``run_recopy`` call passes
``answers_file=".marshal/.copier-answers.yml"`` explicitly (Spike-0's own
finding, reproduced again for this story): ``run_update`` does not
auto-discover it from the template and raises ``TypeError: Template not
found`` if omitted; ``run_recopy`` shares the same requirement (verified
empirically for this story -- it raises ``copier.errors.UserMessageError``
instead of ``TypeError``, but the fix is identical: pass ``answers_file=``
explicitly).

The "extracted answers" ``MaterializeResult.answers`` field comes from the
returned ``Worker``'s own public ``.answers.user`` attribute (an
``AnswersMap``) -- the actual values Copier resolved for this render, as
opposed to ``.answers.combined``, which also carries Jinja-context helper
callables (``now``, ``make_secret``, ...) that are not answers at all.
Reading this one attribute off the ``Worker`` that ``run_copy``/
``run_update``/``run_recopy`` themselves return is the one sanctioned
exception to "never touch a Worker attribute": Spike-0 itself relies on it
("returned a Worker whose ``.answers`` was populated and usable"), and
there is no other public channel to learn what Copier actually did. What
the Boundaries forbid is driving Copier through a manually-constructed
``Worker`` instance's own ``run_copy``/``run_update``/``run_recopy``
METHODS (which exist on ``Worker`` too) instead of the top-level module
functions -- never reading a plain public data attribute off the Worker
those top-level functions themselves hand back. (Verified empirically:
``run_recopy``'s returned ``Worker.answers`` stays empty regardless of
``data=`` -- an inherent quirk of Copier's own recopy implementation, not a
defect in this wrapper; ``MaterializeResult.answers`` simply reflects that.)

The manifest-boundary check reconciles staged output against the
**manifest** (``load_manifest``, Story 7.4/7.5), not a ``Plan`` (Story 9.6
doesn't exist yet and isn't this story's dependency) -- a first filter, not
the final word; Story 10.3's apply runner is expected to run a second,
stricter reconciliation against the actual computed ``Plan`` before
committing through ``fs``. A manifest entry's ``path`` may itself carry a
Jinja placeholder (e.g. ``docs/dreams/{{ slug }}.md``, ``presentations/{{
slug }}/``) describing where a real Genesis run renders it -- ``{{ ... }}``
segments translate to an ``fnmatch`` wildcard (``*``) here, and a trailing
``/`` (a directory placeholder) matches any file beneath it, so the real
packaged manifest's own slug-parameterized entries are usable allow-list
patterns, not just this story's own literal-path throwaway fixtures. Four
paths carry no manifest entry at all (a known deferred-work gap, Story 7.5
review + Spike-0 Finding 1): the answers file itself,
``.marshal/seed-state.yml``, ``.marshal/plan.json``, and
``.bmad-config.user.toml`` -- allow-listed here explicitly as the fixed
Genesis-owned set the Boundaries name.

For ``UPDATE``/``RECOPY``, the staging clone starts pre-populated with
``dst_path``'s ENTIRE tree, not just what Copier touches this render --
walking the whole clone would flag every pre-existing, untouched file
(README, source code, ...) as an "out-of-manifest write" on every real
update. Instead, this module diffs the clone's git working tree
(``git status --porcelain --untracked-files=all``) after the Copier call:
exactly the paths Copier added or modified. A pure deletion (``D``) names
no new path and is excluded -- removing a file materializes nothing to
boundary-check.
"""

from __future__ import annotations

import re
import shutil
import tempfile
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import StrEnum
from fnmatch import fnmatchcase
from importlib import resources
from pathlib import Path
from typing import Any

import copier
from packaging.specifiers import SpecifierSet
from pyforge.core.errors import PyforgeError
from pyforge.core.process import PosixProcess, ProcessError

from ..model.manifest import ArtifactClass, Manifest, load_manifest

# NFR-C2: range-pinned, not exact-pinned -- the one source of truth the
# pixi.toml / pyproject.toml pins mirror. Kept in sync by
# tests/meta/test_engine_version_range_sync.py (Story 12.1).
COPIER_VERSION_RANGE = SpecifierSet(">=9.17,<10")

# The one path every run_copy/run_update/run_recopy call configures
# explicitly (Spike-0 Finding 2) -- also the answers file's own entry in
# the fixed Genesis-owned allow-list below.
_ANSWERS_FILE = ".marshal/.copier-answers.yml"

# Fixed Genesis-owned paths with no manifest entry -- a known deferred-work
# gap (Story 7.5 review, Spike-0 Finding 1): the answers file only comes
# into existence because Genesis's own templates ship the literal
# ``{{ _copier_conf.answers_file }}.jinja`` file; nothing in
# ``manifest.yaml`` names any of these four paths.
_GENESIS_OWNED_PATHS: tuple[str, ...] = (
    ".marshal/seed-state.yml",
    _ANSWERS_FILE,
    ".marshal/plan.json",
    ".bmad-config.user.toml",
)

# Only these four classes are ever materialized (Boundaries) -- referenced
# entries have no rendered path at all, and unclassified-deferred is a V1
# escape hatch Genesis deliberately never writes into.
_MATERIALIZED_CLASSES = frozenset(
    {
        ArtifactClass.COPIED_MANAGED,
        ArtifactClass.COPIED_SEEDED,
        ArtifactClass.GENERATED_DERIVED,
        ArtifactClass.HYBRID_MANAGED_REGION,
    }
)

_JINJA_PLACEHOLDER_RE = re.compile(r"\{\{[^}]*\}\}")

_GIT_TIMEOUT_S = 30.0


class MaterializeVerb(StrEnum):
    """Which Copier operation ``materialize()`` performs."""

    COPY = "copy"
    UPDATE = "update"
    RECOPY = "recopy"


class CopierEngineError(PyforgeError, Exception):
    """Raised for any ``materialize()`` failure that is not a
    manifest-boundary violation: a ``RECOPY`` call missing
    ``request.confirm``, a failed staging clone, or any exception
    ``copier.run_copy``/``run_update``/``run_recopy`` itself raises
    (wrapped via ``raise ... from err`` so the underlying ``copier``
    exception type never reaches the caller directly)."""


class TemplateBoundaryError(CopierEngineError):
    """Raised when the staged output contains a path outside the
    manifest's allow-list, or matching one of its ``never_write`` globs.
    Names every offending path; nothing is returned when this is raised."""


@dataclass(frozen=True)
class MaterializeRequest:
    """The Genesis-internal request ``materialize()`` accepts -- callers
    never construct or pass a ``copier`` object of any kind.

    ``template_path`` -- ``None`` resolves to the in-package
    ``seed/templates/`` directory; an explicit path or URL overrides it.
    Only used for ``COPY``: ``UPDATE``/``RECOPY`` resolve their template
    from ``dst_path``'s own cloned answers file, matching Copier's own
    ``run_update``/``run_recopy`` signatures (neither takes a
    ``src_path``).

    ``data`` -- answers supplied to Copier's ``data=`` (never read from an
    existing answers file -- AD-52; the answers file itself is opaque to
    this module).

    ``unsafe`` -- maps directly to Copier's own ``unsafe=``; ``False`` is
    Copier's own safe default.

    ``confirm`` -- required ``True`` for ``verb=RECOPY`` (FR-101's
    explicit confirmation); ignored for ``COPY``/``UPDATE``.
    """

    verb: MaterializeVerb
    dst_path: Path
    template_path: Path | str | None = None
    data: Mapping[str, Any] = field(default_factory=dict)
    unsafe: bool = False
    confirm: bool = False


@dataclass(frozen=True)
class MaterializeResult:
    """The staged tree, as data. ``staged_paths`` are absolute paths into a
    staging directory this module deliberately leaves on disk on success
    (see the module docstring) -- Story 10.3's apply runner reads them and
    owns cleanup from here. ``answers`` is Copier's own resolved answers
    for this render (``Worker.answers.user``, never ``.combined``)."""

    staged_paths: tuple[Path, ...]
    answers: Mapping[str, Any]


@contextmanager
def _template_source(template_path: Path | str | None) -> Iterator[str]:
    """Yield the ``src_path`` string ``copier.run_copy`` should use: the
    caller's own override if given, else the in-package
    ``seed/templates/`` directory resolved via ``importlib.resources``
    (mirrors ``test_seed_templates_manifest.py``'s own ``resources.as_file``
    idiom)."""
    if template_path is not None:
        yield str(template_path)
        return
    template_root = resources.files("pyforge.marshal.seed.templates")
    with resources.as_file(template_root) as real_path:
        yield str(real_path)


def _git_clone_local(dst_path: Path, stage_path: Path) -> None:
    """Seed ``stage_path`` with a local git clone of ``dst_path`` -- cheap
    via hardlinks, and gives Copier's own git-based diff-and-merge
    algorithm real commit history to reason against for
    ``UPDATE``/``RECOPY``. ``dst_path`` is only ever READ here; nothing is
    written to it."""
    try:
        result = PosixProcess().run(
            ["git", "clone", "--local", "--quiet", str(dst_path), str(stage_path)],
            cwd=Path.cwd(),
            timeout_s=_GIT_TIMEOUT_S,
        )
    except ProcessError as exc:
        raise CopierEngineError(
            f"could not stage {dst_path} for update/recopy via a local git clone: {exc.__cause__ or exc}"
        ) from exc
    if result.returncode != 0:
        raise CopierEngineError(f"could not stage {dst_path} for update/recopy via a local git clone: {result.stderr}")


def _git_changed_paths(stage_path: Path) -> list[str]:
    """Every path ``git status --porcelain --untracked-files=all`` reports
    as added/modified/renamed inside ``stage_path`` -- exactly what Copier's
    ``UPDATE``/``RECOPY`` call wrote, as opposed to every pre-existing,
    untouched file the clone also carries. A pure deletion (``D``) names no
    new path and is excluded. Best-effort (like this package's other
    AST/text scanners): does not handle filenames containing a literal
    `` -> `` substring or requiring shell quoting -- real Genesis-managed
    paths never do."""
    try:
        result = PosixProcess().run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=stage_path,
            timeout_s=_GIT_TIMEOUT_S,
        )
    except ProcessError as exc:
        raise CopierEngineError(f"could not read staged changes in {stage_path}: {exc.__cause__ or exc}") from exc
    if result.returncode != 0:
        raise CopierEngineError(f"could not read staged changes in {stage_path}: {result.stderr}")
    changed: list[str] = []
    for line in result.stdout.splitlines():
        if len(line) < 4:
            continue
        code, path = line[:2], line[3:]
        if "D" in code:
            continue
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        changed.append(path)
    return changed


def _collect_staged_files(stage_path: Path) -> list[Path]:
    """Every file under ``stage_path``, sorted for determinism -- valid
    only for ``COPY``, where staging starts empty so every present file is
    something Copier just wrote. ``.git/`` entries are excluded (clone
    plumbing, never a materialized artifact) though ``COPY`` staging is
    never itself a git repo."""
    return sorted(
        candidate
        for candidate in stage_path.rglob("*")
        if candidate.is_file() and ".git" not in candidate.relative_to(stage_path).parts
    )


def _entry_allow_pattern(path: str) -> str:
    """A manifest entry's ``path`` may carry a Jinja placeholder (e.g.
    ``docs/dreams/{{ slug }}.md``) describing where a real run renders it
    -- ``{{ ... }}`` becomes an ``fnmatch`` wildcard, and a trailing ``/``
    (a directory placeholder) matches any file beneath it."""
    pattern = _JINJA_PLACEHOLDER_RE.sub("*", path)
    if pattern.endswith("/"):
        pattern += "*"
    return pattern


def _load_packaged_manifest() -> Manifest:
    manifest_ref = resources.files("pyforge.marshal.seed.templates") / "manifest.yaml"
    with resources.as_file(manifest_ref) as manifest_path:
        return load_manifest(manifest_path)


def _check_manifest_boundary(relative_paths: Sequence[str]) -> None:
    manifest = _load_packaged_manifest()
    allow_patterns = (
        tuple(
            _entry_allow_pattern(entry.path)
            for entry in manifest.entries
            if entry.artifact_class in _MATERIALIZED_CLASSES
        )
        + _GENESIS_OWNED_PATHS
    )
    deny_patterns = manifest.never_write

    offenders = sorted(
        path
        for path in relative_paths
        if not any(fnmatchcase(path, pattern) for pattern in allow_patterns)
        or any(fnmatchcase(path, pattern) for pattern in deny_patterns)
    )
    if offenders:
        raise TemplateBoundaryError(
            "materialize() staged path(s) outside the manifest boundary: " + ", ".join(offenders)
        )


def _stage_and_render(request: MaterializeRequest, stage_path: Path) -> Mapping[str, Any]:
    render_kwargs: dict[str, Any] = {
        "data": dict(request.data),
        "answers_file": _ANSWERS_FILE,
        "unsafe": request.unsafe,
        "defaults": True,
        "overwrite": True,
        "quiet": True,
    }
    try:
        if request.verb is MaterializeVerb.COPY:
            stage_path.mkdir(parents=True)
            with _template_source(request.template_path) as src_path:
                worker = copier.run_copy(src_path, stage_path, **render_kwargs)
        else:
            _git_clone_local(request.dst_path, stage_path)
            if request.verb is MaterializeVerb.UPDATE:
                worker = copier.run_update(stage_path, **render_kwargs)
            else:
                worker = copier.run_recopy(stage_path, **render_kwargs)
    except CopierEngineError:
        raise
    except Exception as err:
        raise CopierEngineError(f"copier {request.verb.value} failed: {err}") from err
    # `.answers.user`, never `.combined` -- see the module docstring.
    return dict(worker.answers.user)


def materialize(request: MaterializeRequest) -> MaterializeResult:
    """Render ``request`` into an ephemeral staging location and reconcile
    it against the packaged manifest. Never touches ``request.dst_path``
    for writing; see the module docstring for the full contract."""
    if request.verb is MaterializeVerb.RECOPY and not request.confirm:
        raise CopierEngineError(
            "materialize(verb=RECOPY) requires request.confirm=True (FR-101's explicit "
            "confirmation) -- refusing before invoking Copier"
        )

    stage_root = Path(tempfile.mkdtemp(prefix="marshal-seed-stage-"))
    stage_path = stage_root / "stage"
    try:
        answers = _stage_and_render(request, stage_path)
        if request.verb is MaterializeVerb.COPY:
            staged_files = _collect_staged_files(stage_path)
        else:
            staged_files = sorted(stage_path / relative for relative in _git_changed_paths(stage_path))
        relative_paths = [candidate.relative_to(stage_path).as_posix() for candidate in staged_files]
        _check_manifest_boundary(relative_paths)
    except Exception:
        shutil.rmtree(stage_root, ignore_errors=True)
        raise

    return MaterializeResult(staged_paths=tuple(staged_files), answers=answers)
