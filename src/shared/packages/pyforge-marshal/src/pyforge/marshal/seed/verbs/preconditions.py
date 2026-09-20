"""The refusal ladder every mutating verb climbs before it writes anything
(Story 10.4, FR-86, SC-04, SC-05).

`errors.PreconditionFailure` (exit 3) has existed since Story 7.2 with zero
raise sites; its own docstring names this module's three cases ("a dirty
worktree, a target that is not a git repo, or hand-edited managed content")
and says the module that checks them is a `seed/verbs/` story's surface.
This is that module. Until it existed, nothing refused a mutating run
outside a git repo, on a dirty worktree, or over a hand-edited managed
artifact -- so SC-04 ("no hand-edit is silently discarded") and SC-05 ("git
remains a complete undo") were both unmitigated.

`check_preconditions` is a CALLER-SIDE gate: a verb calls it BEFORE it
calls the apply runner, never from inside one. That placement is load-
bearing twice over. It is where the "precondition evaluated before the
first commit" remedy belongs -- once the runner has begun committing, a
refusal is a rollback, not a refusal. And `tests/meta/
test_p07_no_hash_comparison_in_apply.py` bans `hashlib` and every spelling
of a `detect.hashes` import anywhere under `seed/apply/**`, with no
allow-list: apply TRUSTS the plan (P-07), so the rung that hashes managed
content structurally cannot live there.

**The ladder, in fixed order, refusing at the first failure.**

1. `repo_root` is not a git repo.
2. The worktree is dirty.
3. An action's target escapes `repo_root`.
4. An action's target matches a `never_write` pattern.
5. An action's target exists and is a symlink.
6. Managed content on disk diverges from what state recorded.

The order is not cosmetic -- the AC pins it, so a repo failing two rungs
reports the EARLIER one and the message is deterministic rather than
dependent on iteration accidents. Rungs 1-2 establish that git can serve as
the undo, which is what makes everything after it recoverable; 3-5 are
cheap structural checks over paths already in memory; 6 is the only rung
that opens and hashes a file, so it runs last and only once everything
cheaper has passed.

**Which bypass applies to which rung, and why each is narrow.**
`dry_run=True` bypasses rung 2 ONLY: "reading is always safe" is a claim
about the worktree's cleanliness, not about whether git exists at all or
whether the plan is even coherent, so a dry run still refuses a non-repo,
an escaping path, a never-write target, and a symlink. `force=True`
bypasses rung 6 ONLY -- it is the operator's explicit "yes, discard my
hand-edit". Its real bound, stated rather than implied (found in review):
because `force` returns before rung 6 runs AT ALL, and because
`_read_managed_text` is the only code path in this module that ever looks
at a `ManagedRecord`'s own path, under `--force` NO rung validates a
managed record's path -- not its containment, not whether it is a symlink.
Every path the PLAN names is still fully checked, by rungs 3-5, which
`force` does not touch; the unchecked surface is exactly the caller-
supplied record set, whose paths this run is not going to write through
anyway. Rung 4, `never_write`, is bypassable by NEITHER FLAG: it is
the frozen guard (AD-61), and a guard with an override is a suggestion.

**Stated bounds, not aspirations.** Rungs 3-5 evaluate a target the same
way `fs._guard` does -- `Path.resolve()` on both sides, match the resolved
repo-relative string -- so this gate and the write primitive behind it
can never disagree about the same path. That deliberately inherits
`fs.py`'s own documented bound: resolution follows PARENT symlinks, so a
symlinked ancestor (`docs/dreams -> real/`) is evaluated at its
destination, and rung 5's `lstat()` inspects the LEAF only. Matching
the unresolved path instead would close that shape here while opening a
disagreement with `fs.py`, which is the worse trade -- a guard that
answers differently from the primitive it guards is a guard nobody can
reason about. Narrowing it for real means narrowing `fs._guard`, which is
that module's story, not this one's.

**Why rung 6 iterates the caller's state records, not the plan's actions.**
`detect.inventory.classify` marks a present `copied-managed` artifact
`PRESENT_CONFORMANT` whatever its bytes say -- content divergence is
deferred to `detect.hashes` by P-07 -- and `plan.build.build_plan` only
emits actions for `ABSENT`/`PRESENT_DIVERGENT`. So a hand-edited managed
FILE never appears in the plan at all, and a plan-driven check would
silently pass exactly the case SC-04 exists to catch. Iterating the
records asks the right question: for every artifact Genesis claims to own,
is it still what Genesis left there? It also reports ALL divergences in one
message rather than the first -- a caller fixing them one refusal at a time
would need six runs to learn about six hand-edits.

**The consequence for `--skip`, which the caller owns.** Because rung 6
walks the caller's `managed` sequence rather than the plan, it is the one
rung a skip does not reach on its own: rungs 3-5 walk `plan.actions`, which
`skips.apply_skips` has already emptied of every skipped artifact, but
nothing this module does can tell that a record was skipped. A skipped
artifact should therefore NOT be supplied to `managed` -- filter it out
with `skips.managed_after_skips(managed, plan)` first. Otherwise `--skip`
cannot protect a hand-edit at all: the artifact stays refused by rung 6,
and the refusal's only offered remedy is `--force`, which discards every
hand-edit in the repo including the one the operator was protecting. The
filtering lives on the caller's side deliberately -- rung 6's contract is
that it checks every record it is handed.

**Import surface.** This module reads `plan.types`, `fs.NeverWrite`,
`detect.hashes`, `regions.parse`/`regions.markers`, `errors`, and the
`skips.first_match` glob semantic, plus `pyforge.core.process` for the git
seam. It imports NOTHING from `seed.state` (`ManagedRecord` and the
`never_write` set are INPUTS, supplied by whoever loaded state -- this
module holds no competing state model), nothing from `seed.apply`,
`seed.engine`, or `copier`, and it performs no write of any kind: its
entire surface is read-and-refuse.

Git is probed through the injected `pyforge.core.process` port rather than
`adapters.vcs_git.GitVcs` -- `seed/` sits below `adapters/` in the module
dependency chain, and `plan/build.py` already made exactly this choice for
exactly these two read-only calls.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from stat import S_ISLNK

from pyforge.core.process import PosixProcess, ProcessError, ProcessPort

from ..detect.hashes import check_managed_file, check_managed_region
from ..errors import PreconditionFailure
from ..fs import NeverWrite
from ..plan.types import Action, Plan
from ..regions.markers import MarkerError, RegionFormat
from ..regions.parse import RegionParseError, parse_regions
from .skips import first_match

# Query-style git calls (never a checkout/push) -- the identical value
# `plan/build.py::_GIT_TIMEOUT_S` uses for the identical class of call, so a
# hung `git` fails fast instead of blocking a verb indefinitely
# (`PosixProcess.run` defaults to no timeout at all). The duplication is
# deliberate (that file is unmergeable-from here) and PINNED: the
# `_is_dirty` agreement test in `tests/unit/test_seed_verbs_preconditions.py`
# asserts the two constants are equal, so they cannot drift apart silently.
_GIT_TIMEOUT_S = 30.0


@dataclass(frozen=True)
class ManagedRecord:
    """What state recorded about ONE artifact Genesis owns -- rung 6's
    input, and the only shape this module accepts for it.

    Deliberately a local, minimal carrier rather than a `seed.state` import:
    the state store is a sibling story's surface, and this module must not
    hold a competing model of it. A caller loads state and hands these in.

    `body_sha` is the recorded whole-file hash; `region_shas` is one
    `(region_name, recorded_sha)` pair per managed region. A record with a
    non-empty `region_shas` is REGION-BEARING (only its regions are checked,
    never a whole-file hash -- every byte outside a managed region in a
    hybrid file is human-owned by definition, so hashing the whole file
    would report a divergence for exactly the edits the hybrid class exists
    to permit); a record with an empty `region_shas` is a WHOLE-FILE record.
    The manifest makes that split exact: `regions` is non-empty iff the
    entry is `hybrid-managed-region`.

    A recorded sha of `None` on either field means "present on disk but
    never recorded" -- `detect.hashes` treats that as a mismatch by its own
    documented design (an artifact adopted out-of-band is structurally
    indistinguishable from a managed one, and accepting it would let
    hand-authored content pass permanently under the tool's attestation).
    This module does not soften that rule; it only reports it.

    `__post_init__` requires a `region_format` for a region-bearing record:
    without one there is no marker grammar to parse the file with, and a
    silently unparsed region-bearing record would pass rung 6 by doing
    nothing -- the same silent-pass failure mode rung 6 exists to close.
    A caller-contract violation on a constructed shape, so a plain
    `ValueError`, matching `fs.NeverWrite.__post_init__`'s own stance for
    the same class of problem."""

    artifact_id: str
    path: str
    body_sha: str | None = None
    region_shas: tuple[tuple[str, str | None], ...] = ()
    region_format: RegionFormat | None = None

    def __post_init__(self) -> None:
        if self.region_shas and self.region_format is None:
            raise ValueError(
                f"ManagedRecord {self.artifact_id!r} declares regions"
                f" {[name for name, _sha in self.region_shas]!r} but no region_format:"
                " a region-bearing record cannot be parsed without its marker grammar"
            )


@dataclass(frozen=True)
class _Divergence:
    """One rung-6 finding, kept as data until every record has been checked
    so all of them can be reported in a single refusal."""

    artifact_id: str
    detail: str


def _require_existing_repo_root(repo_root: Path) -> None:
    """Refuse a `repo_root` that does not resolve to an existing directory,
    BEFORE any git probe is attempted.

    Order matters here, not just precision (found in review): `subprocess`
    reports a non-existent `cwd` as `FileNotFoundError`, which
    `PosixProcess.run` cannot tell apart from a missing executable, so both
    arrive as the same `ProcessError`. Without this check a merely
    MISSPELLED `--repo-root` was refused with "install git and make it
    resolvable on PATH" -- a remedy for the wrong problem entirely, and for
    the likelier of the two causes. `fs._guard` raises its own explicit
    error for exactly this misconfiguration and calls it a recurring
    failure mode in this codebase; this is that check, one layer earlier.

    Runs from inside rung 1 (its first git probe) so the ladder's fixed
    order still holds: nothing about a repo root that is not there can be
    reported later than "this is not a git repo"."""
    try:
        resolved = repo_root.resolve()
        exists = resolved.is_dir()
    except (OSError, ValueError) as exc:
        raise PreconditionFailure(
            f"repo-root-unusable: {repo_root} cannot be resolved to a directory ({exc})",
            remedy=(
                "pass a repo root that names a real directory -- seed refuses to probe a path it cannot even resolve"
            ),
        ) from exc
    if not exists:
        raise PreconditionFailure(
            f"repo-root-missing: {repo_root} does not resolve to an existing directory ({resolved})",
            remedy=(
                "check the spelling of the repo root path and re-run -- a repo root"
                " that is not there is a misconfiguration, not a missing git"
            ),
        )


def _run_git(process: ProcessPort, repo_root: Path, argv: Sequence[str]) -> tuple[int, str]:
    """`(returncode, stdout)` for one read-only git query, translating a
    `ProcessError` (git absent, a launch failure, a timeout) into a
    `PreconditionFailure` naming the probe that could not run.

    Checks `repo_root` first (see `_require_existing_repo_root`), so the
    `ProcessError` branch below is left reporting only what it can actually
    diagnose -- a `git` that could not be launched -- rather than absorbing
    a missing working directory under the same message.

    Fail-closed by construction: a probe that cannot run is never allowed to
    degrade into a "clean"/"is a repo" answer. A missing `git` is not a
    reason to proceed with a mutating run -- it is precisely the reason the
    undo SC-05 promises would not exist."""
    _require_existing_repo_root(repo_root)
    try:
        result = process.run(["git", *argv], cwd=repo_root, timeout_s=_GIT_TIMEOUT_S)
    except ProcessError as exc:
        raise PreconditionFailure(
            f"git-probe-failed: could not run 'git {' '.join(argv)}' in {repo_root}: {exc}",
            remedy=(
                "install git and make it resolvable on PATH, then re-run --"
                " seed refuses to mutate a repo whose history it cannot verify"
            ),
        ) from exc
    return result.returncode, result.stdout


def _is_git_repo(process: ProcessPort, repo_root: Path) -> bool:
    """Rung 1's probe: `git rev-parse --git-dir` exits zero.

    `--git-dir` rather than `HEAD`: a freshly `git init`-ed repo with no
    commits yet IS a git repo (its `HEAD` is unborn, so `rev-parse HEAD`
    exits non-zero), and refusing to seed one would refuse the single most
    likely target of `seed init`."""
    returncode, _stdout = _run_git(process, repo_root, ["rev-parse", "--git-dir"])
    return returncode == 0


def _is_dirty(process: ProcessPort, repo_root: Path) -> bool:
    """Rung 2's probe: `True` iff `git status --porcelain
    --untracked-files=normal` produces any output, OR exits non-zero
    (cannot confirm clean -- the conservative direction).

    Byte-for-byte the same command and the same non-zero-means-dirty rule as
    `plan.build._repo_is_dirty`, which this story may not edit or import
    from (its file is being modified on an unmerged sibling branch). The two
    are pinned to each other by an agreement test in
    `tests/unit/test_seed_verbs_preconditions.py` rather than by a shared
    helper -- stated as a chosen trade with a guard on it."""
    returncode, stdout = _run_git(process, repo_root, ["status", "--porcelain", "--untracked-files=normal"])
    if returncode != 0:
        return True
    return bool(stdout)


def _relative_within(repo_root: Path, target_path: str) -> str | None:
    """`target_path` as a repo-root-relative POSIX string, or `None` if it
    escapes `repo_root`.

    Resolves both sides with `Path.resolve()` -- non-strict, symlink-
    following -- exactly as `fs._guard` does, so the relative string this
    returns is the SAME string `fs.write` would later evaluate its
    never-write patterns against. Any other derivation here would let rung 4
    clear a path `fs.py` would then refuse (or, worse, the reverse).

    An absolute `target_path` is handled by `Path.__truediv__`'s own
    semantics: `repo_root / "/etc/passwd"` is `/etc/passwd`, which does not
    resolve under `repo_root`, so it reports as an escape like any other.

    A path that cannot be RESOLVED at all reports as `None` too, rather than
    escaping this module as an untyped crash (found in review):
    `Path.resolve()` raises a bare `ValueError` -- not an `OSError` -- for an
    embedded NUL byte, and `target_path` reaches here from a `plan.json`
    that is only type-checked, never charset-checked, at its load boundary.
    "Cannot be resolved" and "resolves outside the root" earn the same
    refusal because they license the same conclusion: this module cannot
    prove the write would land inside the repo."""
    try:
        resolved_root = repo_root.resolve()
        resolved = (repo_root / target_path).resolve()
        return resolved.relative_to(resolved_root).as_posix()
    except OSError, ValueError:
        return None


def _link_target(path: Path) -> str:
    """`path`'s link destination for a refusal message, or `<unreadable>`.

    `readlink()` is called only after an `lstat()` has already said "this is
    a symlink", but the two are not atomic: the link can be removed in
    between, and an unreadable parent can fail the read outright. A refusal
    message is not worth replacing a `PreconditionFailure` (exit 3, with a
    remedy) with a raw `OSError` escaping the ladder, so the destination
    degrades to a placeholder rather than the refusal degrading to a crash."""
    try:
        return str(path.readlink())
    except OSError:
        return "<unreadable>"


def _read_managed_text(repo_root: Path, record: ManagedRecord) -> str | _Divergence | None:
    """The text of `record`'s target: `None` when the artifact is simply
    absent (nothing was hand-edited, so rung 6 passes for it), a
    `_Divergence` when the path cannot be trusted or read, otherwise the
    decoded content.

    An absent path is deliberately NOT a divergence: state naming an
    artifact that is gone describes a deletion, which git already records
    and can already undo -- it is not the "hand-edit silently discarded"
    case SC-04 exists to catch, and refusing it would block the ordinary
    re-materialize a `seed` run is for.

    Everything else fails CLOSED. A path escaping `repo_root`, a symlink, a
    directory, a permission error, or non-UTF-8 bytes all mean this module
    cannot verify the content -- and "cannot verify" must never be reported
    as "verified", which is the exact silent-pass shape rung 6 exists to
    close.

    The symlink test runs BEFORE the absence test, and that order is
    load-bearing (found in review): a managed file replaced by a DANGLING
    link must not report as "absent" and pass -- tool-owned content swapped
    for indirection, reported as nothing having happened. Rung 5 cannot
    cover this case either, since it walks `plan.actions` and a hand-edited
    managed file never appears in the plan at all (see the module
    docstring). A single `lstat()` decides both questions, which is what
    keeps that order true: it does not follow the final link, so a dangling
    link stat's successfully and is classified as a symlink.

    Absence is inferred from `lstat` raising `FileNotFoundError`, never from
    `Path.exists()`/`Path.is_symlink()` (found in review). Those two swallow
    every `OSError` and answer `False`, so an unreadable PARENT directory
    (`EACCES`, reproduced with `chmod 000` on the parent) or a symlink loop
    in the path (`ELOOP`) reported as "absent" -- and absence is this
    function's one PASSING answer, so a hand-edited file underneath an
    unreadable directory sailed through rung 6 in silence. Any `OSError`
    other than "not found" is now a divergence: this module could not
    verify, and "cannot verify" must never be reported as "verified"."""
    relative = _relative_within(repo_root, record.path)
    if relative is None:
        return _Divergence(
            record.artifact_id,
            f"{record.path}: does not resolve to a location inside the repo root; refusing to read it",
        )
    target = repo_root / record.path
    try:
        stat_result = target.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        return _Divergence(
            record.artifact_id,
            f"{record.path}: cannot be stat'ed to verify it ({exc})",
        )
    if S_ISLNK(stat_result.st_mode):
        return _Divergence(
            record.artifact_id,
            f"{record.path}: is a symlink (to {_link_target(target)}), not the regular"
            " file state recorded; its content cannot be attested",
        )
    try:
        return target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return _Divergence(
            record.artifact_id,
            f"{record.path}: cannot be read to verify its content ({exc})",
        )


def _region_divergences(record: ManagedRecord, text: str) -> list[_Divergence]:
    """Rung 6 for one region-bearing record: every recorded region whose
    body no longer hashes to its recorded sha, every recorded region the
    file no longer contains at all, and every managed region the file
    contains that state never recorded.

    A parse failure (`RegionParseError`/`MarkerError`/`NotImplementedError`
    -- mangled, nested, or unclosed markers, or a format with no
    implementation) IS divergence, not a pass: unparseable markers are
    themselves an edit to tool-owned structure, and a file whose regions
    cannot be located is a file whose regions cannot be confirmed intact.
    A recorded region that is simply gone is divergence for the same
    reason -- somebody deleted a managed block.

    The three-way split matters (found in review): iterating
    `record.region_shas` alone answers only two of the three questions, so a
    syntactically valid `marshal-seed:begin/end` region hand-INSERTED into a
    hybrid file, with no entry in state, was reported as conformant --
    hand-authored content passing under the tool's own attestation, which is
    the region-level twin of the whole-file case `detect.hashes` explicitly
    closes by treating `recorded_sha=None` as a mismatch. Comparing by
    region NAME is exact here because the manifest gives each artifact one
    path, so every managed region in that file belongs to this record."""
    # `__post_init__` guarantees a region-bearing record carries a format --
    # narrows for the type checker, matching `plan.build._chosen_anchor`'s
    # own identical assertion against `ManifestEntry.format`.
    assert record.region_format is not None
    try:
        spans = parse_regions(text, record.region_format)
    except (RegionParseError, MarkerError, NotImplementedError) as exc:
        return [
            _Divergence(
                record.artifact_id,
                f"{record.path}: managed regions cannot be parsed ({exc})",
            )
        ]
    spans_by_name = {span.name: span for span in spans}
    divergences: list[_Divergence] = []
    for name, recorded_sha in record.region_shas:
        span = spans_by_name.get(name)
        if span is None:
            divergences.append(
                _Divergence(
                    record.artifact_id,
                    f"{record.path}#{name}: recorded managed region is missing from the file",
                )
            )
            continue
        finding = check_managed_region(record.path, text, span, recorded_sha)
        if finding is not None:
            divergences.append(_Divergence(record.artifact_id, finding.message))
    recorded_names = {name for name, _sha in record.region_shas}
    for span in spans:
        if span.name not in recorded_names:
            divergences.append(
                _Divergence(
                    record.artifact_id,
                    f"{record.path}#{span.name}: a managed region is present in the"
                    " file but was never recorded in state; seed did not write it",
                )
            )
    return divergences


def _managed_divergences(repo_root: Path, managed: Sequence[ManagedRecord]) -> list[_Divergence]:
    """Every divergence across every supplied record, in the caller's own
    record order -- `check_managed_file`/`check_managed_region` are the sole
    deciders for a content comparison; this function only routes each record
    to the right one and collects what comes back."""
    divergences: list[_Divergence] = []
    for record in managed:
        text = _read_managed_text(repo_root, record)
        if text is None:
            continue
        if isinstance(text, _Divergence):
            divergences.append(text)
            continue
        if record.region_shas:
            divergences.extend(_region_divergences(record, text))
            continue
        finding = check_managed_file(record.path, text, record.body_sha)
        if finding is not None:
            divergences.append(_Divergence(record.artifact_id, finding.message))
    return divergences


def check_preconditions(
    plan: Plan,
    *,
    repo_root: Path,
    never_write: NeverWrite,
    managed: Sequence[ManagedRecord] = (),
    force: bool = False,
    dry_run: bool = False,
    process: ProcessPort | None = None,
) -> None:
    """Refuse this run, or return `None` having written nothing.

    Consumes only what it is handed: it never loads a `Manifest`, never
    reads `.marshal/seed-state.yml`, never calls `classify`/`build_plan`,
    and never writes. `never_write` and `managed` are INPUTS -- whoever
    loaded state supplies them.

    Evaluates the six rungs documented at module level in that fixed order
    and raises `PreconditionFailure` (exit 3, always with a non-blank
    `remedy`) at the FIRST one that fails, naming the offending artifact id
    and -- where a region is at fault -- `path#region`.

    **Pass `managed` through `skips.managed_after_skips(managed, plan)` if
    this run has skips.** Rung 6 checks EVERY record in `managed`, by
    contract, and cannot tell that one of them was skipped -- so a record
    for a skipped artifact refuses the run, and the refusal offers only
    `--force`, which discards every hand-edit in the repo including the one
    the operator skipped to protect. Rungs 3-5 need no such care: they walk
    `plan.actions`, from which `apply_skips` already removed the skipped
    artifacts. Filtering is the caller's job precisely because rung 6's
    "check everything you are handed" contract is what makes it trustworthy
    -- this function does not second-guess its own input.

    `process` defaults to a real `PosixProcess`; it is a parameter so a test
    can inject a fake that raises `ProcessError` for the git-absent row
    without uninstalling git."""
    probe = process if process is not None else PosixProcess()

    # --- rung 1: is this a git repo at all -------------------------------
    # Runs even under `dry_run`: whether git exists is not a claim about
    # whether reading is safe, and every later rung's remedy assumes a
    # history to fall back on.
    if not _is_git_repo(probe, repo_root):
        raise PreconditionFailure(
            f"not-a-git-repo: {repo_root} is not inside a git working tree",
            remedy=(
                "run 'git init' in the target repo, or re-run from inside the repo"
                " you meant to seed -- seed will not write where git cannot undo it"
            ),
        )

    # --- rung 2: is the worktree clean -----------------------------------
    # The ONLY rung `dry_run` bypasses: a read-only run cannot make an
    # uncommitted change harder to recover, so demanding a clean worktree
    # before merely looking would be a refusal with no risk behind it.
    if not dry_run and _is_dirty(probe, repo_root):
        raise PreconditionFailure(
            f"dirty-worktree: {repo_root} has uncommitted changes",
            remedy=(
                "commit or stash your changes first -- seed relies on a clean"
                " worktree so 'git checkout .' remains a complete undo of this run"
            ),
        )

    # --- rungs 3-5: per-action structural checks -------------------------
    # THREE separate passes over `plan.actions`, one per rung -- never one
    # pass with all three rungs nested inside it. With a single pass, a plan
    # whose first-by-id action fails rung 5 and whose last fails rung 3
    # would report rung 5, making the reported rung depend on artifact-id
    # ordering rather than on the ladder (found in review). The AC requires
    # the EARLIEST failing rung, which is only true if each rung is
    # exhausted across every action before the next rung is consulted.
    #
    # `plan.skipped` is deliberately not walked by any of the three: a
    # skipped artifact is not going to be written, so nothing about its path
    # can make this run unsafe.
    contained: list[tuple[Action, str]] = []
    for action in plan.actions:
        relative = _relative_within(repo_root, action.target_path)
        if relative is None:
            raise PreconditionFailure(
                f"target-escapes-repo: action {action.artifact_id!r} targets"
                f" {action.target_path!r}, which does not resolve to a location"
                f" inside {repo_root}",
                remedy=(
                    "correct the manifest entry's path to a repo-relative location,"
                    f" or skip this artifact with --skip {action.target_path!r}"
                ),
            )
        # The repo root itself is not a write target (found in review).
        # `_relative_within` maps both `""` and `"."` to `"."`, which is not
        # `None` (rung 3 clears), matches no realistic never-write glob
        # (rung 4 clears) and is not a symlink (rung 5 clears) -- so an
        # action naming the whole repo reached the apply runner having
        # passed every structural rung. `Action.target_path` is only
        # `_require_str`-checked at the `plan.json` boundary, so `""` is
        # reachable from a hand-edited plan. Refused as part of the
        # containment rung, whose question this is: a target that IS the
        # root is no more contained by it than one above it.
        if relative in {".", ""}:
            raise PreconditionFailure(
                f"target-is-repo-root: action {action.artifact_id!r} targets"
                f" {action.target_path!r}, which resolves to the repo root"
                f" {repo_root} itself rather than to a file inside it",
                remedy=(
                    "give the manifest entry a real repo-relative file path --"
                    " an empty or '.' target names the whole repo, which seed"
                    " will not write to"
                ),
            )
        contained.append((action, relative))

    for action, relative in contained:
        # `relative in never_write.exempt` is rung 4's OWN short-circuit
        # (Story 10.8), evaluated before `first_match` ever runs for this
        # action -- a manifest-declared writable artifact (`copied-managed`/
        # `copied-seeded`) can match a broader deny glob that must otherwise
        # keep refusing every other path under it (`fs.NeverWrite`'s own
        # docstring: `docs/dreams/README.md` under `docs/dreams/*.md`).
        # `fs._matches` carries the identical short-circuit, ahead of its own
        # pattern loop, for the same reason: rung 4 must re-derive the same
        # never-write decision `fs._guard` will make on the eventual write,
        # exactly as it already does for the pattern loop below (see the
        # module docstring's "Stated bounds, not aspirations" paragraph).
        if relative in never_write.exempt:
            continue
        matched = first_match(never_write.patterns, relative)
        if matched is not None:
            raise PreconditionFailure(
                f"never-write-target: action {action.artifact_id!r} targets"
                f" {action.target_path!r} (resolved: {relative!r}), which matches"
                f" never-write pattern {matched!r}",
                # States the guarantee this rung actually provides -- no flag
                # overrides it -- rather than the stronger "not overridable,
                # by --force or otherwise" it used to claim (found in
                # review). A symlinked ancestor directory still routes a
                # write past the pattern, because rungs 3-5 resolve parent
                # links exactly as `fs._guard` does (see the module
                # docstring's stated bounds); promising more protection than
                # `fs.py` delivers would be the wrong kind of reassurance in
                # the one message an operator reads about it.
                remedy=(
                    "no flag overrides the never-write set -- not --force, not"
                    " --dry-run; remove this artifact from the manifest, or"
                    " change its path"
                ),
            )

    for action, relative in contained:
        target = repo_root / action.target_path
        # `Path.is_symlink()` swallows every `OSError` and answers False, so
        # an unreadable PARENT directory (`EACCES`) or a symlink loop
        # (`ELOOP`) made a real symlink report as "not a symlink" -- and
        # "not a symlink" is this rung's one PASSING answer, so the link
        # sailed through and the runner wrote THROUGH it, to a destination
        # that may sit outside the repo entirely (defeating SC-05, since git
        # cannot undo a write it never saw). `_read_managed_text` was given
        # exactly this `lstat()`-in-a-`try` treatment for rung 6 in the first
        # review pass; rung 5 is the same hazard one function away, and
        # "cannot verify" must never be reported as "verified" here either.
        try:
            mode = target.lstat().st_mode
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise PreconditionFailure(
                f"symlink-target: action {action.artifact_id!r} targets"
                f" {action.target_path!r} (resolved: {relative!r}), which cannot be"
                f" stat'ed to rule out a symlink ({exc})",
                remedy=(
                    "make the target and every parent directory readable so seed can"
                    " verify what it would write over, or leave this artifact alone"
                    f" with --skip {action.target_path!r}"
                ),
            ) from exc
        if S_ISLNK(mode):
            raise PreconditionFailure(
                f"symlink-target: action {action.artifact_id!r} targets"
                f" {action.target_path!r} (resolved: {relative!r}), which is a symlink"
                f" to {_link_target(target)}",
                remedy=(
                    "replace the symlink with a regular file if seed should own it,"
                    f" or leave it alone with --skip {action.target_path!r}"
                ),
            )

    # --- rung 6: has managed content been hand-edited --------------------
    # The only rung that opens a file, so it runs last -- and the only one
    # `--force` bypasses, since discarding a hand-edit is a decision an
    # operator is entitled to make explicitly, unlike containment.
    if force:
        return
    divergences = _managed_divergences(repo_root, managed)
    if divergences:
        detail = "; ".join(f"{divergence.artifact_id}: {divergence.detail}" for divergence in divergences)
        # Counts BOTH numbers rather than conflating them: one region-bearing
        # artifact with two hand-edited regions produces two divergences, and
        # reporting that as "2 managed artifacts" would be wrong (found in
        # review).
        artifact_count = len({divergence.artifact_id for divergence in divergences})
        raise PreconditionFailure(
            f"managed-content-modified: {len(divergences)} divergence(s) across"
            f" {artifact_count} managed artifact(s) -- {detail}",
            remedy=(
                "revert the hand-edits (git checkout the listed paths), move your"
                " changes outside the managed regions, or re-run with --force to"
                " discard them deliberately"
            ),
        )
