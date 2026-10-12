"""``marshal seed accept`` verb logic (Story 97.1, CAP-12/CAP-13/CAP-17).

Rung 6 of the precondition ladder refuses ``adopt`` and ``update`` when a
claimed file no longer hashes to the value state recorded, and nothing used to
record an edit the operator MEANT: ``--force`` skips rung 6 and records
nothing, and ``update --force`` recopies from a template that ships no payload
for any ``copied-managed`` file. This verb is the sanctioned writer of that
re-record -- and so the one thing that keeps ``SPEC.md:287``'s "state is never
hand-edited" true.

``accept <artifact-id>[#<region>]`` resolves the manifest entry and its state
record, hashes what is on disk with ``detect.hashes.hash_content`` (the whole
file for a whole-file record; each recorded region's body, parsed with the
entry's format, for a hybrid one -- the same functions rung 6 and ``seed
check`` compare with, so an accepted hash is the one the guard will see), and
plans the re-record: old hash to new hash, per file or region. Dry run by
default (FR-124); ``apply=True`` writes and needs a ``reason``.

**The one write.** Only ``.marshal/seed-state.yml``, and only through
``state.store.write_state`` (one atomic replace, P-08), called exactly once per
``apply`` that changes a hash. A dry run writes nothing at all -- not even
``.marshal/plan.json``, which ``adopt`` and ``update`` write on every run.
``tests/meta/test_accept_writes_only_through_the_state_store.py`` reads this
module's AST and fails on any other write primitive.

**The journal.** One ``Acceptance`` per re-recorded file or region, appended to
``SeedState.acceptances`` and written in the SAME replace as the new hash, so
the record and its journal cannot disagree. ``accepted_by`` is the git
committer identity (``git var GIT_COMMITTER_IDENT`` without its timestamp) and
``head`` is ``git rev-parse HEAD``.

**Its refusals** (each names the reason and the id):

* ``UsageError`` (exit 2): ``apply`` without a ``reason``, a malformed
  ``<id>#<region>`` query, an id the manifest does not declare.
* ``PreconditionFailure`` (exit 3): not a git repo, or (under ``apply``) a dirty
  worktree -- rungs 1-2 of the ladder, so the accepted bytes are committed
  bytes and git stays the undo; a directory entry or a class no guard reads
  (``generated-derived``, ``referenced``, ``unclassified-deferred``); an
  artifact state does not record; a repo-owned ``copied-seeded`` artifact
  (nothing to accept: it is not hash-guarded); a path a recorded skip matches;
  a path that escapes the repo, is absent, is a symlink or cannot be read; a
  hybrid file whose regions do not parse, a named region state does not record
  or the file no longer holds; a git identity or HEAD git cannot resolve.
* An unchanged hash is not a refusal: nothing is written and the result says
  so.

**Import surface.** ``detect.hashes``/``detect.skip_match``, ``errors``, ``fs``
(only ``NeverWrite``, the write guard ``write_state`` takes -- never a write),
``model.manifest``, ``regions``, ``state`` and ``verbs.preconditions``'s rungs
1-2, plus ``pyforge.core.process`` for the two git probes. No ``cli`` import.
"""

from __future__ import annotations

import dataclasses
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from stat import S_ISLNK, S_ISREG
from typing import Any

from pyforge.core.process import PosixProcess, ProcessError, ProcessPort

from .. import fs
from ..detect.hashes import hash_content, region_body_text
from ..detect.skip_match import _normalize_relative_posix, first_match
from ..errors import PreconditionFailure, UsageError
from ..model.manifest import ArtifactClass, Manifest, ManifestEntry
from ..regions.markers import MarkerError
from ..regions.parse import RegionParseError, parse_regions
from ..state import (
    Acceptance,
    ManagedArtifact,
    RegionSpanRecord,
    SeedState,
    read_state,
    utc_timestamp,
    write_state,
)
from .preconditions import check_git_rungs

# Query-style git calls (never a checkout/push) -- the same value every other
# seed verb uses for the same class of call, so a hung git fails fast.
_GIT_TIMEOUT_S = 30.0

# The classes no guard reads: rung 6 and `seed check` compare no hash for them,
# so there is nothing for `accept` to re-record.
_UNGUARDED_CLASSES = frozenset(
    {
        ArtifactClass.GENERATED_DERIVED,
        ArtifactClass.REFERENCED,
        ArtifactClass.UNCLASSIFIED_DEFERRED,
    }
)

# `git var GIT_COMMITTER_IDENT` prints `Name <email> <epoch> <tz>`; the identity
# is everything before the trailing timestamp.
_IDENT_RE = re.compile(r"^(?P<who>.+?)\s+\d+\s+[+-]\d{4}$")


@dataclass(frozen=True)
class AcceptChange:
    """One planned (or applied) re-record: a whole file (``region is None``) or
    one region, moving from ``previous_sha`` to ``accepted_sha``."""

    artifact_id: str
    region: str | None
    path: str
    previous_sha: str
    accepted_sha: str

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.artifact_id,
            "region": self.region,
            "path": self.path,
            "previous_sha": self.previous_sha,
            "accepted_sha": self.accepted_sha,
        }


@dataclass(frozen=True)
class AcceptResult:
    """``run_accept``'s whole return value.

    ``changes`` is empty when the recorded hash already matches the file
    (nothing to record). ``applied`` is ``True`` only when ``apply`` ran and
    state was written; ``acceptances`` are the journal entries that write
    appended (``()`` for a dry run or a no-op)."""

    artifact_id: str
    changes: tuple[AcceptChange, ...]
    applied: bool
    acceptances: tuple[Acceptance, ...] = ()

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "id": self.artifact_id,
            "status": "applied" if self.applied else ("dry-run" if self.changes else "nothing-to-record"),
            "changes": [change.to_json_dict() for change in self.changes],
            "applied": self.applied,
            "acceptances": [entry.to_json_dict() for entry in self.acceptances],
        }


def render_accept_text(result: AcceptResult) -> str:
    """The human report: one ``id (path): <recorded> -> <current>`` line per
    change, then a footer saying what happened."""
    if not result.changes:
        return f"accept: nothing to record; {result.artifact_id} already matches its recorded hash."
    lines = [
        f"{change.artifact_id}{'#' + change.region if change.region else ''} ({change.path}):"
        f" {change.previous_sha} -> {change.accepted_sha}"
        for change in result.changes
    ]
    if result.applied:
        lines.append(f"accept: recorded {len(result.changes)} change(s) in .marshal/seed-state.yml.")
    else:
        lines.append('accept: dry-run; re-run with --apply --reason "..." to record it.')
    return "\n".join(lines)


def _split_query(artifact: str) -> tuple[str, str | None]:
    """``"id"`` or ``"id#region"`` -> ``(id, region | None)``; a blank half is a
    ``UsageError`` (a manifest id never contains ``#``)."""
    if not isinstance(artifact, str) or not artifact.strip():
        raise UsageError(
            "accept needs an artifact id; got a blank one",
            remedy="pass a manifest artifact id, e.g. `marshal seed accept bmad-switch`",
        )
    artifact_id, separator, region = artifact.strip().partition("#")
    if not artifact_id or (separator and not region):
        raise UsageError(
            f"malformed accept target {artifact!r}: expected <artifact-id> or <artifact-id>#<region>",
            remedy="pass a manifest artifact id, optionally followed by #<region-name> for one region",
        )
    return artifact_id, (region if separator else None)


def _entry_for(manifest: Manifest, artifact_id: str) -> ManifestEntry:
    for entry in manifest.entries:
        if entry.id == artifact_id:
            return entry
    raise UsageError(
        f"unknown artifact id {artifact_id!r}: the manifest does not declare it",
        remedy="pass a manifest artifact id (`marshal seed explain <id>` shows one) -- accept takes an id, not a path",
    )


def _refuse(reason: str, artifact_id: str, message: str, remedy: str) -> PreconditionFailure:
    return PreconditionFailure(f"accept-{reason}: {artifact_id!r}: {message}", remedy=remedy)


def _managed_record(state: SeedState | None, entry: ManifestEntry) -> ManagedArtifact:
    """The state record for ``entry``, after the class refusals (a directory or
    an unguarded class is refused BEFORE the record is looked up, because most
    such entries are never recorded at all, and "no guard reads this class" is
    the more useful answer than "not claimed")."""
    artifact_id = entry.id
    if entry.is_directory or entry.artifact_class in _UNGUARDED_CLASSES:
        kind = "a directory entry" if entry.is_directory else f"class {entry.artifact_class.value!r}"
        raise _refuse(
            "unguarded-class",
            artifact_id,
            f"is {kind}, which no hash guard reads, so there is nothing to accept",
            "accept applies to `copied-managed` files and `hybrid-managed-region` regions; "
            "`marshal seed update` recomputes a derived artifact",
        )
    record = (
        next((candidate for candidate in state.managed if candidate.id == artifact_id), None)
        if state is not None
        else None
    )
    if record is None:
        raise _refuse(
            "not-claimed",
            artifact_id,
            "is not recorded in .marshal/seed-state.yml, so there is no hash to re-record",
            "run `marshal seed adopt` to claim it first",
        )
    if entry.artifact_class is ArtifactClass.COPIED_SEEDED:
        raise _refuse(
            "repo-owned",
            artifact_id,
            "is `copied-seeded`: repo-owned, never hash-guarded, so there is nothing to accept",
            "edit it freely -- the guard follows the manifest's current class",
        )
    return record


def _read_target(repo_root: Path, artifact_id: str, relative: str) -> str:
    """The UTF-8 text at ``repo_root / relative``, refusing a path that escapes
    the repo, is absent, is a symlink or other non-regular file, or cannot be
    read."""
    target = repo_root / relative
    try:
        root = repo_root.resolve()
        resolved = target.resolve()
    except (OSError, RuntimeError, ValueError) as exc:
        raise _refuse(
            "escapes-repo",
            artifact_id,
            f"{relative} cannot be resolved to a location inside the repo ({exc})",
            "fix the path or the symlink it resolves through, then re-run",
        ) from exc
    if not resolved.is_relative_to(root):
        raise _refuse(
            "escapes-repo",
            artifact_id,
            f"{relative} resolves to {resolved}, outside the repo root; refusing to read it",
            "point the path back inside the repository, then re-run",
        )
    try:
        mode = target.lstat().st_mode
    except FileNotFoundError as exc:
        raise _refuse(
            "absent",
            artifact_id,
            f"{relative} is absent, so there is nothing to hash",
            "restore the file (`git checkout`) or run `marshal seed update` to re-materialize it",
        ) from exc
    except OSError as exc:
        raise _refuse(
            "unreadable",
            artifact_id,
            f"{relative} cannot be stat'ed ({exc})",
            "make the file readable, then re-run",
        ) from exc
    if S_ISLNK(mode) or not S_ISREG(mode):
        raise _refuse(
            "not-a-file",
            artifact_id,
            f"{relative} is a symlink or not a regular file; its content cannot be attested",
            "replace it with a regular file, then re-run",
        )
    try:
        return target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise _refuse(
            "unreadable",
            artifact_id,
            f"{relative} cannot be read as UTF-8 ({exc})",
            "make the file readable text, then re-run",
        ) from exc


def _plan_whole_file(record: ManagedArtifact, text: str) -> tuple[AcceptChange, ...]:
    current = hash_content(text)
    if current == record.body_sha:
        return ()
    return (AcceptChange(record.id, None, record.path, record.body_sha, current),)


def _plan_regions(
    record: ManagedArtifact, entry: ManifestEntry, text: str, region: str | None
) -> tuple[tuple[AcceptChange, ...], dict[str, RegionSpanRecord]]:
    """The re-records for a hybrid record, plus the new ``RegionSpanRecord`` per
    changed region -- built from the file as it is, exactly as ``adopt``'s
    ``_hybrid_record`` builds one (start, end and body hash)."""
    artifact_id = record.id
    recorded = {span.name: span for span in record.inserted_region_spans}
    if region is not None and region not in recorded:
        raise _refuse(
            "region-not-recorded",
            artifact_id,
            f"region {region!r} is not recorded in state (recorded: {sorted(recorded)})",
            "name one of the recorded regions, or omit #<region> to re-record every one",
        )
    if entry.format is None:
        raise _refuse(
            "unparseable",
            artifact_id,
            "its manifest entry declares no region format, so its regions cannot be located",
            "run `marshal seed update` to reconcile the record with the manifest",
        )
    try:
        spans = {span.name: span for span in parse_regions(text, entry.format)}
    except (RegionParseError, MarkerError, NotImplementedError) as exc:
        raise _refuse(
            "unparseable",
            artifact_id,
            f"{record.path}: managed regions cannot be parsed ({exc})",
            "repair the marker lines (`git diff` shows the edit), then re-run",
        ) from exc
    targets = (region,) if region is not None else tuple(recorded)
    changes: list[AcceptChange] = []
    replacements: dict[str, RegionSpanRecord] = {}
    for name in targets:
        span = spans.get(name)
        if span is None:
            raise _refuse(
                "region-missing",
                artifact_id,
                f"{record.path}#{name}: the recorded region is missing from the file (deleting markers is an opt-out, not an edit)",
                "restore the region's markers, or run `marshal seed update`",
            )
        new_sha = hash_content(region_body_text(text, span))
        if new_sha == recorded[name].body_sha:
            continue
        changes.append(AcceptChange(artifact_id, name, record.path, recorded[name].body_sha, new_sha))
        replacements[name] = RegionSpanRecord(
            name=name, start=span.body_span[0], end=span.body_span[1], body_sha=new_sha
        )
    return tuple(changes), replacements


def _git_line(process: ProcessPort, repo_root: Path, artifact_id: str, argv: Sequence[str], what: str) -> str:
    try:
        result = process.run(["git", *argv], cwd=repo_root, timeout_s=_GIT_TIMEOUT_S)
    except ProcessError as exc:
        raise _refuse(
            "no-identity" if what == "committer identity" else "no-head",
            artifact_id,
            f"git could not be run to resolve the {what}: {exc}",
            "install git and make it resolvable on PATH, then re-run",
        ) from exc
    line = result.stdout.strip()
    if result.returncode != 0 or not line:
        raise _refuse(
            "no-identity" if what == "committer identity" else "no-head",
            artifact_id,
            f"git resolves no {what} here",
            "configure `git config user.name` and `user.email` (and commit once), then re-run"
            if what == "committer identity"
            else "make a commit so HEAD exists, then re-run",
        )
    return line


def _committer(process: ProcessPort, repo_root: Path, artifact_id: str) -> str:
    raw = _git_line(process, repo_root, artifact_id, ["var", "GIT_COMMITTER_IDENT"], "committer identity")
    match = _IDENT_RE.match(raw)
    if match is None:
        raise _refuse(
            "no-identity",
            artifact_id,
            f"git printed an unrecognised committer identity {raw!r}",
            "configure `git config user.name` and `user.email`, then re-run",
        )
    return match.group("who")


def _state_after(
    state: SeedState, record: ManagedArtifact, replacements: dict[str, RegionSpanRecord], accepted_sha: str
) -> SeedState:
    """``state`` with ``record`` re-recorded (whole file: ``accepted_sha`` as the
    new ``body_sha``; hybrid: each replaced span, ``accepted_sha`` unused, and
    ``body_sha`` following the first span)."""
    if record.inserted_region_spans:
        spans = tuple(replacements.get(span.name, span) for span in record.inserted_region_spans)
        new_record = dataclasses.replace(record, body_sha=spans[0].body_sha, inserted_region_spans=spans)
    else:
        new_record = dataclasses.replace(record, body_sha=accepted_sha)
    return dataclasses.replace(
        state,
        managed=tuple(new_record if candidate.id == record.id else candidate for candidate in state.managed),
    )


def run_accept(
    repo_root: Path,
    manifest: Manifest,
    artifact: str,
    *,
    apply: bool = False,
    reason: str | None = None,
    process: ProcessPort | None = None,
) -> AcceptResult:
    """Plan -- and under ``apply``, record -- the re-record of ``artifact``
    (``<id>`` or ``<id>#<region>``) against ``repo_root``.

    See the module docstring for the refusals and the one write. Raises
    whatever ``read_state`` raises (a corrupt state is ``StateInvalid``, never
    treated as absent: accepting over state this tool cannot read would
    launder it)."""
    artifact_id, region = _split_query(artifact)
    if apply and (reason is None or not reason.strip()):
        raise UsageError(
            "--apply needs --reason: the journal records why an edit was accepted",
            remedy='pass --reason "<why this edit is intended>"',
        )
    entry = _entry_for(manifest, artifact_id)
    probe = process if process is not None else PosixProcess()
    state = read_state(repo_root)
    # Rungs 1-2 of the ladder: a git repo, and (under --apply) a clean worktree,
    # so the accepted bytes are committed bytes and git stays the undo.
    check_git_rungs(repo_root, dry_run=not apply, process=probe)
    record = _managed_record(state, entry)
    assert state is not None  # `_managed_record` refuses when state is absent
    matched_skip = first_match(state.skips, _normalize_relative_posix(record.path)) if state.skips else None
    if matched_skip is not None:
        raise _refuse(
            "skipped",
            artifact_id,
            f"{record.path} matches recorded skip {matched_skip!r}, so the tool does not manage it",
            "remove the skip from state if it should be managed again",
        )
    text = _read_target(repo_root, artifact_id, record.path)
    if record.inserted_region_spans:
        changes, replacements = _plan_regions(record, entry, text, region)
    else:
        if region is not None:
            raise _refuse(
                "region-not-recorded",
                artifact_id,
                f"is a whole-file record; it has no region {region!r}",
                f"drop the #{region} suffix to re-record the whole file",
            )
        changes, replacements = _plan_whole_file(record, text), {}
    if not changes or not apply:
        return AcceptResult(artifact_id=artifact_id, changes=changes, applied=False)

    # Identity and HEAD are resolved BEFORE the write, so a repo git cannot
    # describe is refused with nothing changed.
    who = _committer(probe, repo_root, artifact_id)
    head = _git_line(probe, repo_root, artifact_id, ["rev-parse", "HEAD"], "HEAD commit")
    assert reason is not None
    now = utc_timestamp()
    journal = tuple(
        Acceptance(
            id=change.artifact_id,
            region=change.region,
            path=change.path,
            previous_sha=change.previous_sha,
            accepted_sha=change.accepted_sha,
            accepted_at=now,
            accepted_by=who,
            head=head,
            reason=reason.strip(),
        )
        for change in changes
    )
    new_state = _state_after(state, record, replacements, changes[0].accepted_sha)
    new_state = dataclasses.replace(new_state, acceptances=(*new_state.acceptances, *journal), last_update=now)
    write_state(
        new_state,
        repo_root=repo_root,
        never_write=fs.NeverWrite(patterns=tuple(sorted(manifest.never_write))),
    )
    return AcceptResult(artifact_id=artifact_id, changes=changes, applied=True, acceptances=journal)
