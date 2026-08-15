#!/usr/bin/env python3
"""Mutation-only: stamp the deferred-work anonymous-entry grandfather baseline.

Epic 7 ("deferred-work visibility") is teaching Doctor's deferred-work
detector (``pyforge.doctor.sources.chain::gather_deferred_work``) to see
anonymous ``- source_spec:`` bullets on the gitignored Tier-3 file, not just
the tracked ledger (Story 7.3). Turning that check on cold would red every
pre-existing anonymous entry across the fleet at once -- measured live at
authoring time: marshal 207, doctor 72, steward 71, atlas 54, warden 41,
herald 33, mason 22, scribe 6. This script stamps each project's CURRENT
count of anonymous Tier-3 entries into a committed baseline at a dated
cut-off, so Story 7.3's eventual comparison can treat "existed at the
cut-off" as grandfathered and red only on a genuinely NEW anonymous entry.

Story 7.3's detector (``pyforge.doctor.sources.chain::_load_deferred_work_
baseline``) reads the file this script stamps, comparing each project's
live anonymous-Tier-3-entry count against the count stamped here to decide
what counts as pre-existing vs. genuinely new. This story still only
produces the data file -- it computes/emits no Doctor finding itself
(mirrors ``scripts/spec_surface_check.py``'s own split between the read-only
Doctor-source verdict and this kind of mutation-only residual, Story 6.9).
Since Story 8.4, ``scripts/deferred_work_promote.py --fix`` also calls this
script's own ``stamp_projects`` automatically for each project it
successfully promotes -- running ``--write-baseline`` by hand is for a
standalone/out-of-band re-stamp, not the only way this file gets written.

Duplicates (never imports) ``pyforge.doctor.sources.chain``'s
``_ENTRY_RE``/``_ANON_RE``/``_anonymous()`` -- every ``scripts/*.py`` file
must run standalone with plain ``python``, no package install required,
exactly the reason ``spec_surface_check.py`` already duplicates its own
algorithm instead of importing ``pyforge.doctor``.

Usage (plain `python`, no pixi task -- mirrors `spec_surface_check.py`'s own
precedent):
        python scripts/deferred_work_baseline.py --write-baseline [--project SLUG ...]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from collections.abc import Iterable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TIER3_REL = Path("implementation-artifacts") / "deferred-work.md"
BASELINE = REPO_ROOT / "scripts" / ".deferred-work-baseline.json"

# Verbatim shape from chain.py:_ENTRY_RE / _ANON_RE / _anonymous -- see this
# script's own module docstring for why this is a duplicate, not an import.
_ENTRY_RE = re.compile(r"^#{2,4}\s+(DW-[A-Za-z0-9][A-Za-z0-9-]*)", re.M)
_ANON_RE = re.compile(r"^-\s+source_spec:", re.M)


def _anonymous(path: Path) -> list[int]:
    """Line numbers of entries with no ``## DW-<id>`` heading of their own --
    duplicated verbatim (in shape) from ``chain.py::_anonymous`` so the
    stamped count matches exactly what that function would report.

    A genuinely MISSING file contributes no entries. Anything else unreadable
    (e.g. an ancestor directory with no search permission) raises rather than
    being silently counted as zero -- ``path.is_file()`` itself swallows that
    case and lies ``False``, the exact "confidently wrong" class chain.py's
    own ``_is_file()``/``_probe()`` exist to avoid (see this repo's
    ``pyforge.doctor.sources.chain`` module docstrings)."""
    try:
        path.stat()
    except FileNotFoundError:
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    out: list[int] = []
    field_taken = False
    in_entry = False
    for n, ln in enumerate(lines, 1):
        if _ENTRY_RE.match(ln):
            field_taken, in_entry = False, True
        elif re.match(r"^#{1,6}\s", ln):
            field_taken, in_entry = False, False
        elif _ANON_RE.match(ln):
            if in_entry and not field_taken:
                field_taken = True
            else:
                out.append(n)
    return out


def _live_state() -> dict[str, int]:
    """Every discovered project's CURRENT anonymous-Tier-3-entry count -- the
    ground truth ``--write-baseline`` merges into the committed file. A
    project is "discovered" only when its Tier-3 file
    (``implementation-artifacts/deferred-work.md``) actually exists; a
    project directory with no Tier-3 file yet contributes no entry."""
    projects_dir = REPO_ROOT / "_bmad-output" / "projects"
    out: dict[str, int] = {}
    if not projects_dir.is_dir():
        return out
    for proj in sorted(p for p in projects_dir.iterdir() if p.is_dir()):
        t3_path = proj / TIER3_REL
        try:
            t3_path.stat()
        except FileNotFoundError:
            continue
        out[proj.name] = len(_anonymous(t3_path))
    return out


def _anonymous_count_for(slug: str) -> int | None:
    """CURRENT anonymous-Tier-3-entry count for exactly ONE named project, or
    ``None`` if that project's Tier-3 file doesn't exist yet. The targeted,
    single-project counterpart to ``_live_state()``'s full-fleet scan
    (Story 8.4, Review Triage Log 2026-08-15, item 7): ``stamp_projects``
    uses this per named slug so a single successful ``--fix`` promotion
    doesn't pay for parsing every OTHER project's Tier-3 file (200+ entries
    for marshal alone) just to read the one count it actually needs."""
    t3_path = REPO_ROOT / "_bmad-output" / "projects" / slug / TIER3_REL
    try:
        t3_path.stat()
    except FileNotFoundError:
        return None
    return len(_anonymous(t3_path))


def _known_project_slugs() -> set[str]:
    """Every discovered project's directory name whose Tier-3 file exists --
    an EXISTENCE-only scan (no Tier-3 file CONTENT read, unlike
    ``_live_state()``'s ``_anonymous()`` call per project) used solely to
    build a helpful "known" list for ``stamp_projects``'s unknown-project
    error message. Only reached on that rare error path -- a clean
    ``stamp_projects`` call never calls this."""
    projects_dir = REPO_ROOT / "_bmad-output" / "projects"
    if not projects_dir.is_dir():
        return set()
    return {
        p.name for p in projects_dir.iterdir()
        if p.is_dir() and (p / TIER3_REL).is_file()
    }


def _read_baseline() -> tuple[str | None, dict[str, int]]:
    """``(raw_text, parsed_dict)`` for the CURRENT on-disk baseline --
    ``raw_text`` is ``None`` only when the file genuinely does not exist yet
    (``parsed_dict`` is then ``{}``). Any other read failure (e.g. a
    permission error) or parse failure (corrupted JSON) is re-raised with a
    message that names this specifically as a READ failure -- distinct from
    a WRITE failure -- so a caller's warning text isn't misleading about
    which action actually broke (Review Triage Log 2026-08-15, item 5).
    Called twice by ``stamp_projects`` (once to seed the merge, once
    immediately before the terminal write) so both ask the identical
    question the identical way -- mirrors
    ``deferred_work_promote.py::_read_tracked``'s own snapshot/re-check
    pattern (item 4)."""
    try:
        raw = BASELINE.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None, {}
    except OSError as exc:
        raise type(exc)(
            f"could not read existing baseline (may be corrupted from a "
            f"prior run): {exc}"
        ) from exc
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"could not read existing baseline (may be corrupted from a "
            f"prior run): {exc}"
        ) from exc
    return raw, parsed


def _write_baseline_atomic(merged: dict[str, int]) -> None:
    """Atomic terminal write -- ``tempfile.mkstemp`` + ``os.replace``,
    mirroring ``deferred_work_promote.py::_promote_project``'s own
    ledger-write precedent (Review Triage Log 2026-08-15, item 1): a plain
    ``write_text`` truncates the destination before writing, so a crash
    mid-write (OOM/SIGKILL/disk-full) could leave this ONE committed file
    -- shared by every tracked project's grandfather protection, not just
    the one being stamped -- corrupted. Writing to a sibling temp file
    first and ``os.replace``-ing it in means the baseline is either fully
    the old content or fully the new content, never a partial write."""
    try:
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=str(BASELINE.parent), prefix=BASELINE.name + ".")
    except OSError as exc:
        raise type(exc)(f"could not write: {exc}") from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(merged, indent=1, sort_keys=True) + "\n")
        os.replace(tmp_name, BASELINE)
    except OSError as exc:
        Path(tmp_name).unlink(missing_ok=True)
        raise type(exc)(f"could not write: {exc}") from exc
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


def stamp_projects(slugs: Iterable[str]) -> dict[str, int]:
    """Scoped ``--write-baseline --project SLUG ...`` stamp, factored out
    (Story 8.4) so both this script's own CLI path AND
    ``deferred_work_promote.py`` (which re-stamps a project's baseline
    immediately after a successful promotion, importing this function
    rather than reimplementing it) share ONE stamping implementation.

    Reads each named project's CURRENT ``_anonymous()`` count via a
    targeted per-slug lookup (``_anonymous_count_for`` -- never pays for
    ``_live_state()``'s full-fleet parse of every OTHER project's Tier-3
    file), MERGES it into the existing committed baseline (never rebuilding
    it -- see ``main()``'s own bare-invocation comment for why a rebuild
    would be unsafe), re-checks the on-disk baseline immediately before the
    terminal write and aborts on drift, writes once atomically, and returns
    ``{slug: newly-stamped count}`` for the named slugs only.

    Returns ``{}`` immediately for an empty ``slugs`` iterable, without
    touching the baseline file at all.

    Raises ``ValueError`` (never prints/exits itself -- this is a library
    function, importable from another script) naming the unknown slug(s)
    and the full known set when any named slug has no Tier-3 file, or when
    the existing baseline's content can't be parsed as JSON. Raises
    ``OSError`` (or a subclass, e.g. ``PermissionError``) when reading or
    writing the baseline file itself fails for a reason other than "does
    not exist yet", including a concurrent writer changing the file during
    this call's own read-merge-write window.

    This refactor is BEHAVIOR-PRESERVING for known-good inputs, mirroring
    the pre-refactor CLI's own error text for the unknown-project case
    exactly. It is NOT byte-identical in one edge case, though -- and is
    incidentally more robust there: an unknown project name checked against
    an already-corrupted existing baseline used to crash with an uncaught
    ``JSONDecodeError`` in the pre-refactor inline code (which parsed
    ``existing`` before validating project names); this refactor validates
    names FIRST, so it now cleanly raises the same "unknown project"
    ``ValueError`` in that combination instead (Review Triage Log
    2026-08-15, item 9)."""
    names = sorted(set(slugs))
    if not names:
        return {}

    # Targeted per-slug lookups, not `_live_state()`'s full-fleet scan --
    # this function's only real caller (`deferred_work_promote.py`) names
    # exactly ONE just-promoted project per call. `_live_state()` itself is
    # reserved for `main()`'s bare CLI all-projects path below, which
    # genuinely needs every project's count.
    #
    # Same "no concurrent mutation of `_bmad-output/projects/` mid-run"
    # assumption `main()`'s own bare-invocation comment documents
    # explicitly nearby: a project directory appearing or disappearing
    # between this lookup and the write below is not guarded against here,
    # matching that existing, accepted precedent.
    current = {name: _anonymous_count_for(name) for name in names}
    unknown = sorted(name for name, count in current.items() if count is None)
    if unknown:
        raise ValueError(
            f"unknown project(s): {', '.join(unknown)}\n"
            f"known: {', '.join(sorted(_known_project_slugs()))}"
        )

    existing_raw, existing = _read_baseline()
    # MERGE, never rewrite: building from `current` alone would silently
    # drop every project this invocation did not name.
    merged = dict(existing)
    for name in names:
        merged[name] = current[name]

    # Re-read-and-compare immediately before the terminal write -- the same
    # race-guard discipline `deferred_work_promote.py::_promote_project`
    # already applies to its own ledger write: abort rather than silently
    # clobber a concurrent writer's change landed in the read-merge-write
    # window above. True cross-process locking is out of scope; this
    # narrows the race window to the write call itself.
    race_raw, _race_parsed = _read_baseline()
    if race_raw != existing_raw:
        raise OSError(
            "baseline changed during this run -- re-run (concurrent write detected)"
        )

    _write_baseline_atomic(merged)
    return dict(current)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write-baseline", action="store_true",
                    help="stamp the anonymous-Tier-3-entry grandfather baseline")
    ap.add_argument("--project", action="append", metavar="SLUG", default=None,
                    help=("limit --write-baseline to this project (repeatable). "
                          "WITHOUT it the stamp covers EVERY discovered project, "
                          "which accepts every other project's growth as "
                          "\"always was this way.\""))
    args = ap.parse_args()

    if args.project and not args.write_baseline:
        ap.error("--project only makes sense with --write-baseline")

    if not args.write_baseline:
        print(
            "this script stamps scripts/.deferred-work-baseline.json, the count "
            "of pre-existing anonymous Tier-3 `- source_spec:` entries per "
            "project at a dated cut-off, so Story 7.3's detector "
            "(pyforge.doctor.sources.chain::_load_deferred_work_baseline) can "
            "grandfather them instead of redding on day one. "
            "scripts/deferred_work_promote.py --fix also calls this "
            "automatically for each project it successfully promotes. Pass "
            "--write-baseline [--project SLUG ...] for a manual/standalone "
            "re-stamp.",
            file=sys.stderr,
        )
        return 2

    # SCOPED stamping, mirroring spec_surface_check.py's own S-13.1
    # rationale: an all-or-nothing stamp would silently accept every OTHER
    # project's growth as "always was this way." Factored into
    # `stamp_projects` (Story 8.4) so `deferred_work_promote.py` can reuse
    # the identical MERGE-never-rebuild logic rather than a second copy.
    if args.project:
        try:
            stamped = stamp_projects(args.project)
        except (ValueError, OSError) as exc:
            print(str(exc), file=sys.stderr)
            return 2
        scope = f"{len(stamped)} project(s): {', '.join(sorted(stamped))}"
        print(f"baseline stamped: {BASELINE.relative_to(REPO_ROOT)} — {scope}")
        return 0

    # MERGE here too, never a full rebuild: `_live_state()` only sees
    # projects whose gitignored Tier-3 scratch happens to be present
    # (readable) on THIS machine/checkout right now -- a partial clone,
    # a worktree that hasn't backlinked every project, or one unreadable
    # directory all silently shrink `current` below the full fleet.
    # Reproduced live during review: a bare run from a checkout with
    # only 1 of 8 projects' Tier-3 scratch present collapsed an 8-entry
    # committed baseline down to 1, discarding grandfather protection
    # for the other 7. A previously-stamped project this run cannot
    # currently see is left untouched, never dropped; only a project
    # this run CAN see gets its count refreshed.
    current = _live_state()
    existing = (json.loads(BASELINE.read_text(encoding="utf-8"))
                if BASELINE.exists() else {})
    merged = {**existing, **current}
    scope = (f"{len(current)} project(s) discovered locally "
             f"({len(merged)} total after merge)")
    BASELINE.write_text(json.dumps(merged, indent=1, sort_keys=True) + "\n",
                        encoding="utf-8")
    print(f"baseline stamped: {BASELINE.relative_to(REPO_ROOT)} — {scope}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
