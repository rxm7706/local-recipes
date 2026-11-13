"""The writer-lock source -- the branch half of the chain-write guard ``spec-python-foundry-cutover:CAP-8``
names: a chain path this branch changes on a checkout that is not the root of record is a named FAIL
(``spec-pyforge-doctor:CAP-100``, Story 56.5). The session hook (steward Story 121.4, the
``chain-write-off-the-writer`` denial of ``.claude/hooks/pre-shell.py``) is the other half: it refuses an Edit or
Write in a session it sees, and a Bash write or another harness passes it. This source judges the branch in
``detectors-ci``, for every harness.

**The root of record, at the merge base.** The flag is read at ``git merge-base refs/remotes/origin/main HEAD``,
never at ``HEAD``: ``git show <base>:src/platform/config/flags.json`` and ``git show
<base>:src/platform/config/flag-overlays.json`` are copied into a temporary directory and handed to
``pyforge.core.cutover_root.root_of_record(<tmp>/flags.json)`` (``spec-pyforge-core:CAP-13``), which composes the
overlay for the current environment as every other reader does. ``steward cutover flip`` changes ``flags.json``
and stamps the Realization log of ``docs/dreams/pyforge-unifying-strategy.md`` in one change (``fnd:AD-24``), so the
branch that carries the flip is judged by the root of record it was branched under and passes the merge bar.
A ``default`` answer from ``root_of_record()`` proves no writer and is cannot-evaluate, never an OK.

**This root.** ``roots.this`` of ``docs/governance/guild-roster.json``, read as data, as the hook reads it.

**The chain paths.** The ``paths`` globs of the roster's ``session_denials`` entry ``chain-write-off-the-writer``
-- the one declared list both halves read -- matched with ``chain.py``'s ``_glob_to_re`` (the spec-surface
matcher: ``**`` spans path separators, ``*`` and ``?`` do not). The changed paths are this branch's own:
``git diff --name-only --no-renames <merge base> HEAD``, from the same commit the flag is read at, so a commit
``origin/main`` gained after the branch forked is never read as this branch's write, and a moved or deleted chain
file still names its old path.

**Verdicts.**

* the root of record equals ``roots.this``: one OK saying this checkout is the writer;
* they differ: one FAIL per changed path that matches a glob, naming the path, the root of record and this root;
  no changed path matches: one OK;
* a roster without ``roots.this`` or without that entry (or one whose entry declares no ``paths`` glob list), a
  flag tree absent at the merge base or one that raises ``CutoverRootError``, a ``default`` answer, or an
  unresolvable ``origin/main``: one cannot-evaluate WARN (``writer-lock-unevaluable``, evidence
  ``unevaluable: true``; ``spec-pyforge-doctor:AD-15``). Anything else raised inside ``_gather`` is folded into
  one WARN by the outer ``degrade_on_exception`` net.

A WARN never changes the exit code (``spec-pyforge-doctor:AD-2``); a chain write off the writer is a FAIL by
``spec-pyforge-doctor:CAP-100``'s own words, as a change under a frozen path is ``frozen-path-changed``'s.

**Read-only, independent, never the trigger.** The roster and the flag files are read as data; every git read
goes through ``cli_bridge.run_git`` (``spec-pyforge-doctor:AD-5``); no station package is imported
(``spec-pyforge-doctor:AD-1``, ``spec-pyforge-doctor:AD-11``). The one write is the two flag files copied into a
``tempfile.TemporaryDirectory``, removed when the read returns -- the tempfile-scoped path NFR-1 permits; nothing
in the judged tree is written. This source never decides when the flag flips: the operator flips it by hand.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from pyforge.core.cutover_root import LOCAL_DEV_RELATIVE, CutoverRootError, RootOfRecord, root_of_record
from pyforge.core.flags import OVERLAYS_FILE_NAME

from ..cli_bridge import CliBridgeError, run_git
from ..models import UNEVALUABLE_EVIDENCE_KEY, DoctorStatus, Finding, Source
from ..refs import ORIGIN_MAIN, display_ref
from . import degrade_on_exception
from .chain import _glob_to_re

__all__ = ("gather",)

_CHECK = "writer-lock"
#: ``spec-pyforge-doctor:AD-15``'s ``<source>-unevaluable`` check for a cannot-evaluate WARN.
_CHECK_UNEVALUABLE = f"{_CHECK}-unevaluable"

#: The roster, relative to the target: ``docs/governance/guild-roster.json``.
_ROSTER_PARTS: tuple[str, ...] = ("docs", "governance", "guild-roster.json")
_ROSTER_SHOWN = "/".join(_ROSTER_PARTS)
#: The ``session_denials`` entry whose ``paths`` both halves of the writer lock read (steward Story 121.4).
_DENIAL_ID = "chain-write-off-the-writer"

#: The flag tree and its overlay, as git names them at the merge base.
_FLAGS_SHOWN = LOCAL_DEV_RELATIVE.as_posix()
_OVERLAYS_SHOWN = LOCAL_DEV_RELATIVE.with_name(OVERLAYS_FILE_NAME).as_posix()

#: ``RootOfRecord.source`` when no flag tree was in reach: the default proves no writer.
_DEFAULT_SOURCE = "default"
_SHORT_SHA = 12


class _Unevaluable(Exception):
    """An input cannot be read -- one cannot-evaluate WARN, never an OK."""

    def __init__(self, message: str, **evidence: object) -> None:
        super().__init__(message)
        self.evidence = evidence


def _git(target: Path, *args: str) -> str | None:
    """``git`` stdout, or ``None`` on any failure -- ``sources/frozen_path.py``'s own wrapper. Routes through
    ``cli_bridge.run_git`` (``spec-pyforge-doctor:AD-5``: the sole subprocess site)."""
    try:
        return run_git(target, list(args))
    except CliBridgeError, UnicodeDecodeError:
        return None


def _roster(target: Path) -> tuple[str, tuple[str, ...]]:
    """``roots.this`` and the ``chain-write-off-the-writer`` entry's ``paths`` globs, read as data.

    RAISES ``_Unevaluable`` when the roster is missing or unreadable, declares no non-empty ``roots.this``, has
    no such entry, or the entry carries no non-empty list of non-empty glob strings.
    """
    path = target.joinpath(*_ROSTER_PARTS)
    if not path.is_file():
        raise _Unevaluable(f"{_ROSTER_SHOWN} is missing -- which root this checkout is cannot be told")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise _Unevaluable(f"{_ROSTER_SHOWN} cannot be read ({type(exc).__name__})") from exc
    if not isinstance(data, dict):
        raise _Unevaluable(f"{_ROSTER_SHOWN} is not an object (got {type(data).__name__})")

    roots = data.get("roots")
    this = roots.get("this") if isinstance(roots, dict) else None
    if not isinstance(this, str) or not this.strip():
        raise _Unevaluable(f"{_ROSTER_SHOWN} declares no roots.this -- which root this checkout is cannot be told")

    denials = data.get("session_denials")
    rows = denials if isinstance(denials, list) else []
    entry = next((row for row in rows if isinstance(row, dict) and row.get("id") == _DENIAL_ID), None)
    if entry is None:
        raise _Unevaluable(
            f"{_ROSTER_SHOWN} has no session_denials entry {_DENIAL_ID!r} -- the chain paths are not declared",
            this=this,
        )
    globs = entry.get("paths")
    if not isinstance(globs, list) or not globs or not all(isinstance(g, str) and g for g in globs):
        raise _Unevaluable(
            f"{_ROSTER_SHOWN} entry {_DENIAL_ID!r} declares no 'paths' glob list -- the chain paths are not declared",
            this=this,
        )
    return this, tuple(globs)


def _merge_base(target: Path) -> str:
    """``git merge-base refs/remotes/origin/main HEAD``; RAISES ``_Unevaluable`` when it cannot be resolved."""
    output = _git(target, "merge-base", ORIGIN_MAIN, "HEAD")
    base = output.strip() if output else ""
    if not base:
        shown = display_ref(ORIGIN_MAIN)
        raise _Unevaluable(
            f"no merge base of {shown} and HEAD -- {shown} cannot be resolved here",
            base=shown,
            head="HEAD",
        )
    return base


def _copy_out(path: Path, text: str) -> None:
    """Write ``text`` to ``path``, a new file inside the caller's ``tempfile.TemporaryDirectory`` -- the only
    write this module makes (NFR-1's tempfile-scoped path); ``O_EXCL`` refuses anything already there."""
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(text)


def _root_of_record_at(target: Path, base: str) -> RootOfRecord:
    """The root of record as the flag tree at ``base`` renders it (``spec-pyforge-core:CAP-13``).

    Both flag files are copied out of the merge base into a temporary directory -- the overlay beside the tree,
    where ``root_of_record`` composes it from -- and read there; never the working tree, never ``HEAD``.
    RAISES ``_Unevaluable`` when the tree is absent at ``base`` or raises ``CutoverRootError``.
    """
    short = base[:_SHORT_SHA]
    flags_text = _git(target, "show", f"{base}:{_FLAGS_SHOWN}")
    if flags_text is None:
        raise _Unevaluable(f"{_FLAGS_SHOWN} is absent at the merge base {short}", merge_base=base)
    overlays_text = _git(target, "show", f"{base}:{_OVERLAYS_SHOWN}")
    with tempfile.TemporaryDirectory(prefix="doctor-writer-lock-") as scratch:
        flags_path = Path(scratch) / LOCAL_DEV_RELATIVE.name
        _copy_out(flags_path, flags_text)
        if overlays_text is not None:
            _copy_out(flags_path.with_name(OVERLAYS_FILE_NAME), overlays_text)
        try:
            return root_of_record(flags_path)
        except CutoverRootError as exc:
            # The scratch directory is gone when the WARN is read: name the tree by its merge-base path instead.
            reason = str(exc).replace(scratch, f"{short}:{LOCAL_DEV_RELATIVE.parent.as_posix()}")
            raise _Unevaluable(
                f"the flag tree at the merge base {short} raises CutoverRootError: {reason}",
                merge_base=base,
            ) from exc


def _changed_paths(target: Path, base: str) -> list[str]:
    """The paths this branch changed: ``base`` (the merge base) to ``HEAD``, renames split into a delete and an
    add so a moved chain file names its old path too. ``core.quotePath=false`` keeps a non-ASCII path matchable
    (``sources/frozen_path.py``'s own reason). RAISES ``_Unevaluable`` on a git failure."""
    output = _git(target, "-c", "core.quotePath=false", "diff", "--name-only", "--no-renames", "-z", base, "HEAD")
    if output is None:
        raise _Unevaluable(f"could not diff the merge base {base[:_SHORT_SHA]}..HEAD", merge_base=base, head="HEAD")
    return sorted({part for part in output.split("\0") if part})


def _unevaluable(message: str, **evidence: object) -> Finding:
    return Finding(
        source=Source.WRITER_LOCK,
        check=_CHECK_UNEVALUABLE,
        status=DoctorStatus.WARN,
        message=f"{message} -- the writer lock cannot be evaluated",
        evidence={"roster": _ROSTER_SHOWN, **evidence, UNEVALUABLE_EVIDENCE_KEY: True},
    )


def _gather(target: Path) -> tuple[Finding, ...]:
    try:
        this, globs = _roster(target)
        base = _merge_base(target)
        record = _root_of_record_at(target, base)
    except _Unevaluable as exc:
        return (_unevaluable(str(exc), **exc.evidence),)

    short = base[:_SHORT_SHA]
    if record.source == _DEFAULT_SOURCE:
        # Never proof that this checkout is the writer (spec-pyforge-core:CAP-13's own `source` field).
        return (
            _unevaluable(
                f"root_of_record() answered only the default ({record.root}) at the merge base {short}",
                this=this,
                merge_base=base,
                root_of_record=record.root,
                root_source=record.source,
            ),
        )

    evidence: dict[str, object] = {
        "root_of_record": record.root,
        "forge_slug": record.forge_slug,
        "this": this,
        "merge_base": base,
    }
    if record.root == this:
        return (
            Finding(
                source=Source.WRITER_LOCK,
                check=_CHECK,
                status=DoctorStatus.OK,
                message=(
                    f"this checkout ({this}) is the writer: pyforge.cutover_root names {record.root} "
                    f"({record.forge_slug}) at the merge base {short} of {display_ref(ORIGIN_MAIN)} and HEAD"
                ),
                evidence=evidence,
            ),
        )

    try:
        changed = _changed_paths(target, base)
    except _Unevaluable as exc:
        return (_unevaluable(str(exc), this=this, root_of_record=record.root, **exc.evidence),)

    patterns = [(glob, _glob_to_re(glob)) for glob in globs]
    findings: list[Finding] = []
    for path in changed:
        glob = next((glob for glob, pattern in patterns if pattern.match(path)), None)
        if glob is None:
            continue
        findings.append(
            Finding(
                source=Source.WRITER_LOCK,
                check=_CHECK,
                status=DoctorStatus.FAIL,
                message=(
                    f"{path}: a chain path changed on a checkout that is not the writer -- the root of record is "
                    f"{record.root} ({record.forge_slug}), this root is {this}; write it on the root of record"
                ),
                evidence={**evidence, "path": path, "glob": glob},
            )
        )
    if findings:
        return tuple(findings)

    return (
        Finding(
            source=Source.WRITER_LOCK,
            check=_CHECK,
            status=DoctorStatus.OK,
            message=(
                f"this checkout ({this}) is not the writer ({record.root} is the root of record at the merge base "
                f"{short}) and none of the {len(changed)} changed path(s) is a chain path"
            ),
            evidence={**evidence, "changed": len(changed)},
        ),
    )


def gather(target: Path) -> tuple[Finding, ...]:
    """Judge whether this branch writes a chain path on a checkout that is not the root of record
    (``spec-pyforge-doctor:CAP-100``; the branch half of ``spec-python-foundry-cutover:CAP-8``).

    One OK when this checkout is the writer; otherwise one FAIL per changed chain path, or one OK when none
    changed; one cannot-evaluate WARN when the roster, the merge base or the flag tree at it cannot be read
    (``spec-pyforge-doctor:AD-15``). The outer ``degrade_on_exception`` net folds anything else into one WARN.
    """
    return degrade_on_exception(Source.WRITER_LOCK, _CHECK, lambda: _gather(target))
