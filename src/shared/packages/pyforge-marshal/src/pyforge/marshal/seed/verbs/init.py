"""``marshal seed init``'s verb logic: the LAST verb in Epic 10, and the
final piece of ``resolve -> detect -> plan -> apply -> state-write`` this
package's three real verbs share (Story 10.7, FR-72..78, PRD Journey J1).

Until this module, ``cli/seed.py::run_init`` was Story 7.1's stub: it printed
"not yet implemented" and exited 0, so starting a brand-new project still
meant hand-wiring every tier artifact. This module bootstraps a target
directory (creating it and running ``git init`` if needed -- see
``_bootstrap_git_repo`` below) and then reuses the SAME shared pipeline
``verbs/adopt.py`` (Story 10.6) already established --
``detect.inventory.classify``, ``plan.build.build_plan``,
``verbs.preconditions.check_preconditions``, ``apply.run.run_apply``,
``state.store.write_state`` -- rather than re-deriving any of their rules.
Two of ``adopt.py``'s own helpers are reused DIRECTLY, by import, never
duplicated: ``_managed_artifact_after_apply`` (building a post-apply
``ManagedArtifact`` record) and ``_default_commit`` (the production
``commit`` callback wrapping ``engine.copier.materialize``, plus the region
path's ``_region_body_from_template`` it calls internally) -- see
``verbs/adopt.py``'s own module docstring for the full design of both; this
module does not re-explain them.

**The one genuine gap: bootstrapping git.** Every FR-72 through FR-78 line
is silent on ``git init``, but the shared pipeline this verb reuses
structurally REQUIRES some git repository to exist: ``build_plan``'s own
``RepoFingerprint`` derivation, ``check_preconditions``'s rung 1, and
``run_apply``'s ``fingerprint_drift`` all shell out to git. PRD Journey J1's
own scenario ("a maintainer spinning ``pyforge-scribe`` out ... runs
``marshal seed init ../pyforge-scribe``") targets a sibling directory that
does not yet exist as a repo at all. ``_bootstrap_git_repo`` runs a plain,
no-flags ``git init`` if ``path/.git`` is not already present, BEFORE
anything else touches git -- ``plan.build._git_head`` already degrades
gracefully to ``None`` on a zero-commit repo (its own docstring: "``None``
on a non-zero exit -- no commits yet, or ``repo_root`` is not a git repo at
all"), so an ``init`` target with no commits yet produces a valid, working
``RepoFingerprint``. No initial commit is required or created by this verb.

**No dry-run, no confirm prompt.** Unlike ``adopt``, ``init`` applies
DIRECTLY -- confirmed by PRD J1's own literal invocation (``marshal seed
init ../pyforge-scribe --slug pyforge-scribe --agents claude,cursor``, no
``--apply`` flag) versus J2's explicit "(dry-run by default)" parenthetical
for ``adopt``: the asymmetry is deliberate, not an omission. FR-78's
non-empty-directory refusal (``_refuse_if_unsuitable`` below) IS this verb's
safety gate, not a confirmation step. ``.marshal/plan.json`` is still
written unconditionally (FR-82's "machine-readable artifact" applies here
too, and the epics AC's own "init produces a plan artifact identical in
shape [to adopt's]" requires it) -- just never gated behind a separate
confirmation the way ``adopt --apply`` without ``--yes`` is.

**``_manifest_for_init`` does two things ``_manifest_for_adopt`` does not
need to: filter AND resolve.** Filter to ``applies_to in (AppliesTo.INIT,
AppliesTo.BOTH)``, mirroring ``_manifest_for_adopt``'s identical ``(ADOPT,
BOTH)`` pattern -- an ``adopt``-only entry (``specs-dir-legacy``: "a fresh
init never creates it") has no reason to ever reach ``classify``/
``build_plan`` here. Then substitute the literal ``{{ slug }}`` placeholder
in every entry's ``.path`` with the resolved slug value, BEFORE the manifest
ever reaches ``classify``/``build_plan`` -- confirmed necessary by direct
reading of ``verbs/adopt.py``'s own module docstring, "known, inherited
limitations" (3): "``classify()`` treats the placeholder as a literal path
segment, which is a PRE-EXISTING gap in ``detect.inventory``/``plan.build``
... not one [``adopt``] is scoped to close" -- naming ``init`` as the story
that must close it. Five packaged manifest entries carry ``{{ slug }}``
today (``starter-dream``, ``project-config``, ``specs-readme``,
``deck-scaffolding``, ``project-subtree``), but the substitution is applied
GENERALLY, over every filtered entry's ``.path`` (``str.replace`` is a no-op
where the placeholder is absent), so a future manifest addition needs no
code change here.

**``--slug`` resolution and where it flows.** Defaults to ``path``'s
resolved directory basename when omitted (FR-73). Used both for the path
substitution above AND passed as a ``slug`` key in the ``commit`` callback's
``answers=`` dict (alongside ``model_version``/``seed_model_version``/
``mode``/``agents``, mirroring ``adopt.py::_default_commit``'s existing
pattern), so whole-file CONTENT rendered through ``engine.copier.materialize``
can also reference ``{{ slug }}`` inside a file body, not only in its path.

**Reused from ``adopt.py`` beyond the two names above:``_repo_is_dirty_now``**
(also imported directly, not duplicated). ``write_plan`` -- called
unconditionally, exactly as ``adopt`` calls it before its own confirm/apply
split -- introduces ``.marshal/plan.json`` as a new UNTRACKED file, which
makes the repo genuinely dirty at the instant right before ``run_apply``'s
own ``fingerprint_drift`` re-checks it; but the ``Plan`` object built a few
lines earlier still carries the OLDER, pre-``write_plan`` ``dirty`` value.
``adopt.py`` hit and fixed this exact trap for its own ``--apply`` path (see
its own ``_repo_is_dirty_now`` docstring for the full "why unrestricted,
deliberately" argument, confirmed by execution); ``init`` always applies, so
it hits the identical trap on every single run, not merely the ``--apply``
one, and reuses the identical fix rather than re-deriving it: refresh ONLY
``plan.repo_fingerprint.dirty`` to the fresh, unrestricted current value
immediately before calling ``run_apply``. ``init`` does NOT need ``adopt``'s
companion ``_unexpected_dirt_since_plan_write`` check -- that guard exists
specifically to catch an OPERATOR dirtying the repo during ``adopt``'s
confirm PAUSE, a window ``init`` never opens (nothing runs between
``write_plan`` and the dirty refresh here).

**``check_preconditions`` still runs, mirroring ``adopt``'s own sequencing,
after the git bootstrap and before ``run_apply``.** On a freshly
``git init``'d, still-empty repo its six rungs are all trivially satisfied:
rung 1 (now a real git repo), rung 2 (an empty repo has nothing to report as
dirty), rungs 3-5 (still meaningful defensive checks, kept), rung 6
(``managed=()`` is always passed -- see below -- so it never fires). Called
with ``force=False`` UNCONDITIONALLY (never threaded from the CLI
``--force``): the CLI's ``--force`` bypasses ONLY ``_refuse_if_unsuitable``'s
FR-78 non-empty-directory refusal, and never reaches
``check_preconditions``'s own ``force=`` parameter, matching the Always
bullet's own words verbatim. A consequence worth stating rather than
silently accepting (a genuine edge this story's own AC text does not walk
through): rung 2 (the dirty-worktree check) is NOT bypassed for ``init``
the way ``adopt``'s own dry-run bypasses it, so a ``--force``'d run onto a
non-empty target that is NOT already a git repo will, after this module's
own bootstrap makes every pre-existing file newly untracked, refuse at rung
2 unless that target's content is committed first. This is the same
git-undo-safety (SC-05) every mutating verb in this package is built
around, applied uniformly rather than exempting ``init --force`` from it;
the packaged manifest's own I/O matrix row for ``--force`` on a non-empty
directory is satisfied by (and this story's own tests exercise) the
realistic case of an already-git-tracked, already-committed non-empty
skeleton -- a genuinely non-git, non-empty, ``--force``'d target is a
narrower gap this story does not further resolve, named here rather than
silently worked around.

**``state`` is never read.** Unlike ``adopt`` (which reads existing state to
union ``--agents`` and to seed rung 6's managed-record set), ``init`` never
calls ``read_state``: "there is no PRIOR state to union with on a fresh
bootstrap" (Always bullet). ``managed=()`` is passed to
``check_preconditions`` unconditionally, and ``--agents`` is recorded as its
own parsed tuple with no merge step (unlike ``adopt.py::_merge_agents``).

**State is written after a successful, NON-EMPTY apply, gated on
``plan.actions``** -- mirroring ``adopt.py``'s own "an empty plan skips the
state write entirely" gate (FR-84's idempotence read literally, one layer
up). ``mode: "init"`` (never ``"adopt"``), ``legacy[]`` populated from
``inventory.legacy`` for shape parity with ``adopt``'s own state (no
packaged manifest entry declares ``legacy_of`` today, but a ``--force``'d
run onto pre-existing content could still classify one ``present-legacy``
if a future manifest ever does), ``skips``/``migrations_applied``/
``opted_out`` all ``()`` -- ``init`` carries no ``--skip`` flag at all (this
story's own Never bullet) and there is no prior migration or opt-out
history to inherit.

**A confirmed, out-of-scope gap this story surfaces but does not close:
``verbs/check.py`` cannot verify a ``{{ slug }}``-templated entry.** Found
by direct execution while developing this story's own tests, named here
rather than silently worked around. ``run_check`` (Story 10.5, unmodified by
this story except its one narrow ``applies_to`` fix -- see ``verbs/check.py``'s
own module docstring) has no ``slug`` parameter and performs no path
substitution at all: it checks the manifest's RAW ``entry.path`` directly
against the filesystem (`detect.inventory.classify`'s own "an entry's own
declared path is always checked DIRECTLY" contract). For a
``starter-dream``-shaped entry, that RAW path is the literal string
``"docs/dreams/{{ slug }}.md"`` -- a file that can never exist on disk under
that literal name, since `_manifest_for_init` (above) is the ONLY thing in
this package that ever resolves the placeholder, and it resolves it into a
DIFFERENT `Manifest` object this verb builds and discards, never the one a
later `marshal seed check` invocation loads fresh from the packaged
manifest. So `check` reports EVERY ``{{ slug }}``-templated entry
`ARTIFACT_MISSING` unconditionally, on every repo, forever -- whether or not
`init` (or `adopt`) has ever run, and regardless of this story's own
`applies_to`-vs-`state.mode` fix (which only ever SUPPRESSES a finding, and
does not apply here: `starter-dream`'s own `applies_to: init` DOES match a
freshly `init`'d repo's `state.mode == "init"`). This is a genuinely
different gap from the one `_manifest_for_init` closes (that one is about
`classify`/`build_plan` treating the placeholder as literal for a MUTATING
verb's own run; this one is about a READ-ONLY verb with no slug input at
all), it predates this story (any `check` call against any repo carrying a
``{{ slug }}``-templated manifest entry already exhibits it, independent of
`init`), and closing it would mean giving `check` a `--slug`/`slug=`
parameter -- a real, but out-of-scope, follow-on for a future story. This
story's own tests that assert `check` comes back green after a real `init`
run therefore check against a manifest EXCLUDING the ``{{ slug }}``-templated
entries, and separately assert (by reading the filesystem directly) that
`init` materialized them correctly -- see ``tests/unit/test_seed_verbs_
init.py``'s own PRD-J1 test for the concrete shape of that split.

**Consuming Story 10.8's ``exempt=`` fix (this story's own follow-up work,
resolving the collision this story itself was originally blocked on).**
Verified live while this story was still in flight: the REAL packaged
manifest's own ``dreams-readme`` entry (``docs/dreams/README.md``,
``copied-managed``) matches the manifest's own ``docs/dreams/*.md``
never-write glob, so ``run_init`` refused it UNCONDITIONALLY at
``check_preconditions``'s rung 4 -- the same collision Story 10.8 found and
fixed for ``adopt`` (``NeverWrite.exempt`` -- an exact-path allow-list
checked BEFORE glob matching -- plus ``detect.inventory.writable_
exemptions``, which computes it). This story's own ``never_write =
fs.NeverWrite(...)`` construction, above, now consumes that fix identically
to ``verbs/adopt.py::run_adopt``'s own: ``exempt=writable_exemptions(
filtered_manifest, inventory)``. ``specs-readme`` (``_bmad-output/projects/
{{ slug }}/planning-artifacts/specs/README.md``, ``copied-seeded``,
``applies_to: init``) collides the identical way against the manifest's own
``**/planning-artifacts/**`` glob, and is resolved by the same fix -- it is
an ``init``-only entry ``adopt``'s own equivalent test never had reason to
exercise, since ``_manifest_for_adopt`` filters it out before ``classify``/
``build_plan`` ever see it.

**Import surface.** ``detect.inventory`` (``classify``, ``effective_never_
write``, ``writable_exemptions``), ``plan.build`` (``build_plan``, ``write_plan``,
``default_plan_path`` -- never modifies ``build_plan`` itself), ``plan.types``
(``Plan``), ``apply.run`` (``run_apply``, ``ApplyResult``, ``CommitAction``),
``verbs.preconditions`` (``check_preconditions``), ``state`` (``SeedState``,
``ManagedArtifact`` via ``adopt``'s own helper, ``LegacyArtifact``,
``write_state``, ``utc_timestamp``, ``seed_model_version``), ``model.manifest``
(``AppliesTo``, ``Manifest``, ``ManifestEntry``), ``errors`` (``PreconditionFailure``,
for the git-bootstrap failure path; ``UsageError``, for FR-78's own refusal),
``fs`` (the MODULE, matching ``adopt.py``'s own convention), and
``pyforge.core.process`` (``PosixProcess``/``ProcessError`` -- the git-init
seam). ``verbs.adopt`` for the three names reused directly (see above). No
``seed.cli`` import (the architecture's no-upward-imports rule)."""

from __future__ import annotations

import dataclasses
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from pyforge.core.process import PosixProcess, ProcessError

from .. import fs
from ..apply.run import ApplyResult, CommitAction, run_apply
from ..detect.inventory import (
    Inventory,
    classify,
    effective_never_write,
    writable_exemptions,
)
from ..errors import PreconditionFailure, UsageError
from ..model.manifest import AppliesTo, Manifest, ManifestEntry
from ..plan.build import build_plan, default_plan_path, write_plan
from ..plan.types import Plan
from ..state import (
    LegacyArtifact,
    SeedState,
    seed_model_version,
    utc_timestamp,
    write_state,
)
from .adopt import _default_commit, _managed_artifact_after_apply, _repo_is_dirty_now
from .preconditions import check_preconditions

# Query-style-adjacent, but not a read-only probe: this IS the one git call
# this module ever writes with. Matches `adopt.py::_GIT_TIMEOUT_S`/
# `plan/build.py::_GIT_TIMEOUT_S`'s identical value for the identical class
# of concern (a hung `git` must fail fast rather than hang `init`
# indefinitely) -- pinned equal to both by an agreement test, the same
# convention `verbs/preconditions.py` already established for its own
# duplicated constant.
_GIT_TIMEOUT_S = 30.0


@dataclass(frozen=True)
class InitResult:
    """``run_init``'s whole return value -- a plain, inspectable shape,
    matching ``AdoptResult``'s own convention. ``applied`` is ``None`` for a
    ``dry_run`` (Story 12.5 / FR-124: mutating verbs accept ``--dry-run``) and
    a real tuple once apply runs (possibly ``()`` for a ``--force``'d target
    whose every filtered entry is already conformant). ``slug`` is the
    RESOLVED value (never ``None``, whether or not ``--slug`` was given)."""

    plan: Plan
    applied: tuple[str, ...] | None
    slug: str
    dry_run: bool = False


def _refuse_if_unsuitable(path: Path, *, force: bool) -> None:
    """FR-78's own safety gate, checked BEFORE anything else touches the
    filesystem or git: refuse a target ``init`` should not overwrite.

    Three cases, in fixed order (mirroring FR-78's own text). (1) ``path``
    EXISTS and is NOT a directory (a plain file, or anything else that is
    not a directory) -- refused UNCONDITIONALLY, ``--force`` included: "
    ``--force`` cannot turn a file into a project root" (the story's own
    Always bullet). (2) ``path`` exists, IS a directory, and is NON-EMPTY --
    refused UNLESS ``force``, directing the operator to ``marshal seed
    adopt`` instead (the documented path for an existing repo). (3)
    Anything else -- ``path`` does not exist at all, or exists as an
    already-empty directory -- is NOT refused: an absent path is "treated
    identically to an already-existing EMPTY directory for the non-empty
    check" (Always bullet), so this function's own emptiness test never
    runs against it at all.

    A lone ``.git/`` entry does NOT count as "non-empty" (review-caliber
    finding, confirmed by the I/O matrix's own row 2: "an existing, empty
    directory (ALREADY a git repo)" -- a contradiction unless "empty" is
    read as "empty of everything except its own git bookkeeping", since a
    git repo always carries a ``.git/`` directory). Excluding it is what
    makes that row reachable at all: without it, EVERY already-git-repo
    target -- including one this verb bootstrapped on a PRIOR run -- would
    permanently refuse a second ``init`` even with nothing else in it.

    Raises ``UsageError`` (exit 2) for both refusal cases -- the story's own
    Always bullet names ``UsageError`` explicitly for case (1); this
    function treats case (2) the same way, since both describe a
    CALLER-SUPPLIED ``<path>`` argument that is unsuitable for ``init``, not
    a repo-state precondition in ``verbs.preconditions.check_preconditions``'s
    own ladder sense (that ladder is entirely about git/dirty/hand-edit
    gates, none of which are meaningful before a target directory even
    exists)."""
    if not path.exists():
        return
    if not path.is_dir():
        raise UsageError(
            f"init target {str(path)!r} exists and is not a directory",
            remedy=(
                "`marshal seed init` can only target a directory (or a path that does"
                " not exist yet) -- choose a different target, or remove the file first"
            ),
        )
    if force:
        return
    if any(entry.name != ".git" for entry in path.iterdir()):
        raise UsageError(
            f"init target {str(path)!r} is not empty",
            remedy=(
                "`marshal seed init` targets a fresh project -- run `marshal seed adopt`"
                " instead to layer the seed model onto an existing repository, or re-run"
                " with --force to proceed onto this non-empty directory anyway"
            ),
        )


def _bootstrap_git_repo(path: Path) -> None:
    """Create ``path`` if it does not exist yet, then run a plain, no-flags
    ``git init`` if ``path/.git`` is not already present -- the one genuine
    gap the epics AC's own FR-72..78 text is silent on, resolved here (see
    the module docstring's opening section).

    ``path.mkdir(parents=True, exist_ok=True)`` runs UNCONDITIONALLY, even
    when ``path`` already exists (a no-op then) -- so this function alone
    turns "does not exist" and "already exists, empty" into the identical
    starting point for everything downstream, matching
    ``_refuse_if_unsuitable``'s own "treated identically" rule.

    No initial commit is created (module docstring): ``plan.build._git_head``
    already degrades gracefully to ``None`` on a zero-commit repo, and
    ``fingerprint_drift``'s later re-check agrees for the identical reason,
    since nothing is committed in between.

    Raises ``PreconditionFailure`` (exit 3) if ``git`` could not even be
    launched, or exited non-zero -- a bootstrap failure is exactly the class
    of "seed will not write where git cannot undo it" refusal
    ``verbs.preconditions`` already raises for a target that never became a
    repo at all."""
    path.mkdir(parents=True, exist_ok=True)
    if (path / ".git").exists():
        return
    try:
        result = PosixProcess().run(["git", "init"], cwd=path, timeout_s=_GIT_TIMEOUT_S)
    except ProcessError as exc:
        raise PreconditionFailure(
            f"could not run 'git init' in {path}: {exc}",
            remedy="ensure git is installed and on PATH, then re-run `marshal seed init`",
        ) from exc
    if result.returncode != 0:
        detail = " ".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
        raise PreconditionFailure(
            f"'git init' failed in {path}: {detail}",
            remedy=(
                "ensure the target directory is writable and git is correctly installed,"
                " then re-run `marshal seed init`"
            ),
        )


def _manifest_for_init(manifest: Manifest, slug: str) -> Manifest:
    """``manifest``, scoped to the entries this verb ever touches AND with
    every entry's ``{{ slug }}`` path placeholder resolved -- the two things
    ``_manifest_for_adopt`` does not need to do (module docstring's own
    review-caliber finding, resolved here).

    FILTER: ``applies_to in (INIT, BOTH)``, mirroring ``_manifest_for_
    adopt``'s identical ``(ADOPT, BOTH)`` pattern -- an ``adopt``-only entry
    (e.g. ``specs-dir-legacy``, "a fresh init never creates it") has no
    reason to ever reach ``classify``/``build_plan`` here.

    RESOLVE: every entry's ``.path`` has the literal string ``"{{ slug }}"``
    substituted with ``slug``, via ``dataclasses.replace`` -- BEFORE the
    manifest ever reaches ``classify``/``build_plan``, which both treat the
    placeholder as an ordinary, literal path segment (a pre-existing gap in
    ``detect.inventory``/``plan.build``, confirmed by reading ``verbs/
    adopt.py``'s own module docstring, which names ``init`` -- this story --
    as the one that closes it). ``str.replace`` is a no-op for any entry
    whose path carries no placeholder, so this runs unconditionally over
    every filtered entry rather than a hardcoded list of the five entries
    that carry one in the packaged manifest today -- a future manifest
    addition needs no code change here."""
    entries = tuple(
        dataclasses.replace(entry, path=entry.path.replace("{{ slug }}", slug))
        for entry in manifest.entries
        if entry.applies_to in (AppliesTo.INIT, AppliesTo.BOTH)
    )
    return Manifest(model_version=manifest.model_version, never_write=manifest.never_write, entries=entries)


def _build_state_after_init(
    *,
    plan: Plan,
    inventory: Inventory,
    entries_by_id: dict[str, ManifestEntry],
    repo_root: Path,
    agents: tuple[str, ...],
    manifest: Manifest,
) -> SeedState:
    """The ``SeedState`` ``run_init`` writes after a successful, NON-EMPTY
    apply -- see the module docstring's own "State is written" section for
    the gate that keeps this function unreachable for an empty plan.

    ``managed[]`` is built one record per applied ``Action`` via
    ``adopt.py::_managed_artifact_after_apply``, reused DIRECTLY (import,
    never duplicate) -- there is no "carried over" half the way ``adopt``'s
    own ``_build_state_after_apply`` has, since ``init`` never reads a prior
    state to carry anything over FROM. ``legacy[]`` mirrors ``inventory.
    legacy`` for shape parity with ``adopt``'s own state (see the module
    docstring)."""
    managed = tuple(
        sorted(
            (
                _managed_artifact_after_apply(action, entries_by_id[action.artifact_id], repo_root)
                for action in plan.actions
            ),
            key=lambda record: record.id,
        )
    )
    legacy = tuple(
        LegacyArtifact(id=record.entry_id, path=record.path, legacy_of=record.legacy_of) for record in inventory.legacy
    )
    now = utc_timestamp()
    return SeedState(
        model_version=manifest.model_version,
        seed_model_version=seed_model_version(),
        adopted_at=now,
        last_update=now,
        mode="init",
        agents=agents,
        managed=managed,
        skips=(),
        legacy=legacy,
        migrations_applied=(),
        opted_out=(),
    )


def run_init(
    path: Path,
    manifest: Manifest,
    *,
    slug: str | None = None,
    agents: Sequence[str] = (),
    force: bool = False,
    dry_run: bool = False,
    template_path: Path | str | None = None,
    commit: CommitAction | None = None,
) -> InitResult:
    """Bootstrap ``path`` (creating it and running ``git init`` if needed),
    then compose ``resolve -> detect -> plan -> preconditions -> apply ->
    state-write`` against it -- writing ``.marshal/plan.json``
    unconditionally and ``.marshal/seed-state.yml`` only after a successful,
    non-empty apply (skipped entirely when ``dry_run=True``; Story 12.5 /
    FR-124). See the module docstring for the full ordering rationale.

    Unlike ``adopt``, there is no ``confirm`` parameter: a non-dry-run
    ``init`` always executes. ``template_path``/``commit`` are the identical
    test-injection seams ``adopt.py::run_adopt`` already establishes.

    Raises whatever ``check_preconditions``/``run_apply`` raise, unchanged --
    this function adds no ``try``/``except`` of its own (mirroring
    ``run_adopt``'s identical stance)."""
    _refuse_if_unsuitable(path, force=force)
    resolved_slug = slug if slug is not None else path.resolve().name
    _bootstrap_git_repo(path)

    filtered_manifest = _manifest_for_init(manifest, resolved_slug)
    inventory = classify(filtered_manifest, path)
    plan = build_plan(filtered_manifest, inventory, opted_out=frozenset())

    never_write = fs.NeverWrite(
        patterns=tuple(sorted(effective_never_write(filtered_manifest, inventory))),
        exempt=writable_exemptions(filtered_manifest, inventory),
    )
    # `force=False` UNCONDITIONALLY -- the CLI `--force` bypasses ONLY
    # `_refuse_if_unsuitable`'s FR-78 refusal above, never rung 6's own
    # bypass (module docstring: `state` is always absent on a fresh `init`
    # target, so rung 6 never fires regardless, and `managed=()` reflects
    # that -- `init` never reads a prior state to seed it from).
    check_preconditions(
        plan,
        repo_root=path,
        never_write=never_write,
        managed=(),
        force=False,
        dry_run=dry_run,
    )

    write_plan(plan, default_plan_path(path))

    if dry_run:
        return InitResult(plan=plan, applied=None, slug=resolved_slug, dry_run=True)

    entries_by_id = {entry.id: entry for entry in filtered_manifest.entries}
    parsed_agents = tuple(agents)

    effective_commit = commit
    if effective_commit is None:
        effective_commit = _default_commit(
            repo_root=path,
            never_write=never_write,
            entries_by_id=entries_by_id,
            model_version=filtered_manifest.model_version,
            answers={
                "model_version": str(filtered_manifest.model_version),
                "seed_model_version": seed_model_version(),
                "mode": "init",
                "agents": list(parsed_agents),
                "slug": resolved_slug,
            },
            template_path=template_path,
        )

    # Refresh ONLY the fingerprint's `dirty` flag, to account for
    # `write_plan` above having just introduced `.marshal/plan.json` as an
    # untracked file -- see the module docstring's own section on why this
    # MUST be the true, unrestricted current value (the identical trap
    # `adopt.py::_repo_is_dirty_now` already solved for its own `--apply`
    # path; `init` reuses that fix directly rather than re-deriving it).
    apply_plan = dataclasses.replace(
        plan,
        repo_fingerprint=dataclasses.replace(plan.repo_fingerprint, dirty=_repo_is_dirty_now(path)),
    )

    result: ApplyResult = run_apply(apply_plan, repo_root=path, never_write=never_write, commit=effective_commit)

    if plan.actions:
        new_state = _build_state_after_init(
            plan=plan,
            inventory=inventory,
            entries_by_id=entries_by_id,
            repo_root=path,
            agents=parsed_agents,
            manifest=filtered_manifest,
        )
        write_state(new_state, repo_root=path, never_write=never_write)

    return InitResult(plan=plan, applied=result.applied, slug=resolved_slug, dry_run=False)
