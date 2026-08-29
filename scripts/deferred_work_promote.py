#!/usr/bin/env python3
"""Mutation-only: promote Tier-3 legacy deferred-work orphans AND
already-identified-but-untracked entries into the tracked ledger (Story
8.3, extended by Story 8.7).

Story 8.1 (`classify_tier3_entries`) classifies every legacy Tier-3 shape;
Story 8.2 (`mint_id_for_entry`) mints a collision-free id for any orphan.
Neither writes anything -- Doctor's `sources/` package is read-only by
construction (meta-test enforced). The live legacy backlog across the
fleet's 8 projects still has no way to actually reach the tracked ledger
except the by-hand process that has already produced real bugs (a
false-orphan content duplication, an overcount) during past audits.

This script closes that gap: for each target project, it sources every
orphan (`entry.id is None`) from `classify_tier3_entries(tier3_path)`,
mints each one's id via `mint_id_for_entry` (threading ONE running
`already_minted` set across the whole project's batch -- Story 8.2's own
proven discipline; skipping this reproduces the exact duplicate-mint bug
that story's review caught). Story 8.7 adds a second, structurally
different source to the SAME batch: entries that already carry a real
`DW-*` id in Tier-3 (`entry.id is not None`) but whose id is not yet a
`DW-` token anywhere in the tracked ledger -- no minting needed, the
entry's own `entry.id` is used verbatim. Both kinds are validated for id/
summary collisions in memory as ONE combined batch, and -- only on a clean
batch -- the tracked ledger is written once.

**Why this lives here, not in `pyforge.doctor`.** Doctor sources are
deliberately READ-ONLY gathers (Charter Sec.6 -- the producing station keeps
the operational guard; only Doctor holds the verdict), so
`classify_tier3_entries`/`mint_id_for_entry` never got a write path and
never will. This script IMPORTS those two pure functions (a read-only
import is not a write site -- only this script's own `write_text` call is)
rather than duplicating their algorithm, unlike `deferred_work_baseline.py`'s
own precedent of duplicating `chain.py`'s private parsing helpers: that
script duplicates so it can run with zero package install, but Story 8.1/
8.2's minting logic is exactly the kind of "must never drift from the
detector" code that duplication risks silently diverging from, and the
Code Map for this story calls for an import explicitly.

**Never** modifies the Tier-3 file itself (append-only by this repo's
established convention). Writes via a single `write_text` call per project,
only after every promotion in that project's batch has been computed and
validated in memory -- mirrors `spec_surface_check.py`'s own
`--write-baseline` atomicity pattern (logical atomicity via one terminal
write, not filesystem-level atomicity).

**Story 8.4:** immediately after a project's ledger write succeeds (only
when it actually promoted `N>0` orphans), this script re-stamps that SAME
project's grandfather baseline (`scripts/.deferred-work-baseline.json`) to
its current anonymous-entry count, by importing and calling
`deferred_work_baseline.stamp_projects` -- reusing that script's own
already-tested scoped-stamp/merge logic rather than a second
implementation. A project where nothing was promoted this run (no orphans,
or an aborted batch) never has its baseline touched. A baseline re-stamp
failure AFTER a successful ledger write is caught and reported as a
distinct warning appended to that project's own "promoted" outcome -- it
never rolls back or reclassifies the already-successful promotion.

Usage (plain `python`, no pixi task -- mirrors `deferred_work_baseline.py`'s
own precedent):
        python scripts/deferred_work_promote.py --fix [--project SLUG ...]
"""
from __future__ import annotations

import argparse
import os
import re
import stat
import sys
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# `pyforge.doctor` is a namespace package rooted under
# `src/shared/packages/pyforge-doctor/src` (with its sibling `pyforge-core`
# providing `pyforge.doctor.models`'s own dependencies) -- already
# importable with zero setup inside the `local-recipes`/`pyforge-doctor`
# pixi envs (their site-packages already map both), but not necessarily for
# a bare `python scripts/...` invocation outside either. Best-effort
# sys.path insertion, mirroring `scripts/bmad_drift_check.py`'s own
# precedent -- but REQUIRED rather than optional here: this script's entire
# job is built on `classify_tier3_entries`/`mint_id_for_entry`, so a failed
# import is left to raise loudly rather than degrade to a silent no-op.
for _pkg in ("pyforge-doctor", "pyforge-core"):
    _src = REPO_ROOT / "src" / "shared" / "packages" / _pkg / "src"
    if str(_src) not in sys.path:
        sys.path.insert(0, str(_src))

from pyforge.doctor.sources.chain import (  # noqa: E402
    LegacyEntry,
    classify_tier3_entries,
    mint_id_for_entry,
)

# Story 8.4: `deferred_work_baseline.py` lives alongside this script in
# `scripts/` -- a plain stdlib-only sibling module, not a package -- so
# importing its reusable `stamp_projects` needs its own directory on
# `sys.path`, same convention as the `pyforge.doctor` insertion above,
# scoped to just this one directory. Importing (not duplicating) it is the
# whole point of Story 8.4's Boundaries: "reuse... rather than
# reimplementing baseline JSON merge semantics."
#
# UNLIKE the `pyforge.doctor` import above, a failure here is NOT left to
# raise loudly: this sibling is an optional, best-effort re-stamp step, not
# this script's core job (promoting Tier-3 orphans still works fine without
# it). If the sibling is ever missing/unimportable -- e.g. this script
# copied standalone without it -- even a bare invocation or `--help` used to
# crash with a raw traceback before argument parsing ever ran (Review
# Triage Log 2026-08-15, item 3). Degrading `deferred_work_baseline` to
# `None` here lets the script still run normally; `_promote_project`'s own
# re-stamp call below reports a clear "baseline module unavailable" warning
# for that project instead of crashing, if/when it's actually reached.
_SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
try:
    import deferred_work_baseline  # noqa: E402
except ImportError as _baseline_import_exc:  # noqa: N816
    deferred_work_baseline = None
    _BASELINE_IMPORT_ERROR: ImportError | None = _baseline_import_exc
else:
    _BASELINE_IMPORT_ERROR = None

TIER3_REL = Path("implementation-artifacts") / "deferred-work.md"
TRACKED_REL = Path("planning-artifacts") / "deferred-work-ledger.md"


def _probe(p: Path) -> os.stat_result | None:
    """``p.stat()``, or ``None`` when ``p`` genuinely does not exist --
    RAISING when the answer cannot be determined (Review Triage Log
    2026-08-15, item 5). Duplicated in SHAPE from `chain.py`'s own private
    `_probe`/`_is_file` (not imported -- both are underscore-prefixed and
    absent from `chain.py`'s `__all__`), mirroring this script's own
    established "reuse the approach, not the private symbol" precedent.
    `Path.is_file()` swallows every
    `OSError` and answers `False` for an unreadable ANCESTOR directory,
    indistinguishable from a genuinely absent file -- so a permission-denied
    `tier3_path` used to read as "nothing to promote", a dangerous false
    negative for a mutation script's own input probe."""
    try:
        return p.stat()
    except (FileNotFoundError, NotADirectoryError):
        return None


def _is_file(p: Path) -> bool:
    """``p.is_file()`` that raises rather than lying -- see ``_probe``."""
    st = _probe(p)
    return st is not None and stat.S_ISREG(st.st_mode)


def _normalize_summary(summary: str) -> str:
    """Casefold + collapse-internal-whitespace form of a `summary:` value,
    used ONLY for the duplicate-detection comparison, never for what gets
    written -- catches the real-world "reworded/whitespace-normalized during
    a by-hand promotion pass" variant Blind Hunter named (Review Triage Log
    2026-08-15, item 8), without attempting full fuzzy/near-duplicate
    matching (explicitly out of scope -- real complexity increase, false-
    positive risk, not requested by this story's AC)."""
    return re.sub(r"\s+", " ", summary).strip().casefold()


@dataclass
class _Outcome:
    slug: str
    status: str  # "promoted" | "no-op" | "aborted"
    message: str
    # Story 8.4, Review Triage Log 2026-08-15, item 2: set when a
    # "promoted" outcome's baseline re-stamp failed -- the ledger write
    # itself still genuinely succeeded, so `status`/`message` stay
    # "promoted" (never rewritten to look like a failure), but `main()`
    # must still end the whole run non-zero so a caller checking only the
    # exit code (CI, cron) learns the manual fallback is needed.
    baseline_warning: bool = False


def _project_slug_map() -> dict[str, str]:
    """{short station name: directory name} for every directory under
    `_bmad-output/projects/` -- `--project` is scoped by the SHORT name
    (e.g. `--project doctor`, not `--project pyforge-doctor`), mirroring
    `sprint-ledger-sync`'s own `--project KEY` convention exactly per
    Boundaries ("Scope per --project the same way sprint-ledger-sync
    does"; `pyforge.doctor.sources.fleet_scan::PROJECT_SOURCES`'s keys are the
    same short form). A directory not shaped `pyforge-<name>` maps to
    itself -- defensive, not expected to trigger for the 8 real projects.

    Raises ``ValueError`` if two project directories would collide on the
    same short slug (e.g. `pyforge-mason` and a stray `mason` directory) --
    a dict comprehension would otherwise silently let the
    alphabetically-later one clobber the first, making the earlier project
    permanently unreachable via `--project` with no error (Review Triage
    Log 2026-08-15, item 9)."""
    projects_dir = REPO_ROOT / "_bmad-output" / "projects"
    if not projects_dir.is_dir():
        return {}
    slug_map: dict[str, str] = {}
    for p in sorted(projects_dir.iterdir()):
        if not p.is_dir():
            continue
        short = p.name.removeprefix("pyforge-")
        if short in slug_map:
            raise ValueError(
                f"project directories {slug_map[short]!r} and {p.name!r} "
                f"both map to the same --project short slug {short!r} -- "
                f"rename one of them, then re-run"
            )
        slug_map[short] = p.name
    return slug_map


def _discover_projects(slug_map: dict[str, str]) -> list[str]:
    """Default `--fix` scope (no `--project` given): every short project
    name that actually has a Tier-3 file -- mirrors `sprint-ledger-sync`'s
    own default-everything-with-the-relevant-file convention, per
    Boundaries. A project dir with no Tier-3 file is simply excluded from
    the default scope (not an error -- see the I/O matrix's "Missing
    Tier-3 file" row)."""
    projects_dir = REPO_ROOT / "_bmad-output" / "projects"
    return [
        short for short, dirname in sorted(slug_map.items())
        if (projects_dir / dirname / TIER3_REL).is_file()
    ]


def _format_promoted_entry(new_id: str, entry: LegacyEntry, tier3_rel: str) -> str:
    """One promoted entry, matching the real shape already used by 3+
    tracked ledgers (verified against `pyforge-doctor`'s own
    `DW-FU-6-4`/`DW-FU-6-5` entries): a `### {id}: {summary}` header, a
    blank line, then a `- source_spec:` bulleted field block whose
    subsequent 2-space-indented lines are `summary:`/`evidence:`/
    `promoted:`/`status:` as plain continuation keys -- no new syntax.

    Field values are taken verbatim from the orphan's own `LegacyEntry.
    fields` (already continuation-joined by `classify_tier3_entries`) --
    this promotes the orphan's content unedited, exactly as every real
    promoted entry's own "this is a COPY, not a curation" convention
    requires (see e.g. `pyforge-mason`'s tracked ledger header note).

    Any field beyond `{source_spec, summary, evidence, status}` (e.g. a
    `resolution:` an orphan already carries -- 13 of 76 real orphans,
    live-confirmed 2026-08-15) is preserved VERBATIM, in the order it
    appears in the orphan's own `fields` dict (source order), placed after
    `evidence:` and before `promoted:`/`status:` -- dropping it would
    silently discard signal that the matter was already addressed (Review
    Triage Log 2026-08-15, item 3). `status:` defaults to `open` only when
    the orphan carries no `status:` field of its own; when it does, that
    value is used verbatim rather than force-overwritten -- an
    already-resolved item must not resurface as freshly open with no trace
    of why it was previously handled.

    `new_id` is `entry.id` itself, unchanged, for an already-identified
    entry (Story 8.7) -- the `promoted:` note's own wording distinguishes
    "no prior id" (orphan, Story 8.3) from "never previously copied" (had a
    real id all along, just missing its tracked twin) so a reader of the
    tracked ledger can tell the two provenances apart."""
    summary = entry.fields.get("summary", "").strip()
    source_spec = entry.fields.get("source_spec", "").strip()
    evidence = entry.fields.get("evidence", "").strip()
    status = entry.fields["status"].strip() if "status" in entry.fields else "open"
    today = date.today().isoformat()
    if entry.id is None:
        promoted = (
            f"{today} — promoted from Tier-3 {tier3_rel} "
            f"(legacy {entry.shape.value} entry, no prior id)"
        )
    else:
        promoted = (
            f"{today} — promoted from Tier-3 {tier3_rel} "
            f"(already-identified {entry.shape.value} entry, never previously "
            f"copied to the tracked ledger)"
        )
    extra_fields = "".join(
        f"  {key}: {value.strip()}\n"
        for key, value in entry.fields.items()
        if key not in {"source_spec", "summary", "evidence", "status"}
    )
    return (
        f"### {new_id}: {summary}\n"
        f"\n"
        f"- source_spec: {source_spec}\n"
        f"  summary: {summary}\n"
        f"  evidence: {evidence}\n"
        f"{extra_fields}"
        f"  promoted: {promoted}\n"
        f"  status: {status}\n"
    )


@dataclass(frozen=True)
class _BatchValidation:
    """Per-entry outcome of validating a project's full to-be-appended
    batch -- PURE, no I/O. ``problems`` non-empty means ABORT the whole
    batch, no write at all (unchanged from before this story).
    ``already_tracked`` names indices into ``minted`` whose normalized
    summary already exists in the tracked ledger under a DIFFERENT,
    independently-minted id -- these are silently EXCLUDED from the write
    (never re-promoted, never counted as a problem), closing DW-FU-8-4
    (2026-08-28): before this split, a project promoted once could never
    promote a genuinely NEW orphan added later, because every subsequent
    ``--fix`` run's batch always ALSO contained the OLD, already-promoted
    orphan (Tier-3 is append-only, so its bullet is unchanged and still
    classifies as an orphan), which always re-collided against its own
    tracked twin, which always aborted the WHOLE batch, forever -- live-
    confirmed against all 8 real fleet projects at landing. An orphan
    whose collision is anything else (a genuinely new, ambiguous
    duplicate) still hard-aborts, per this dataclass's own ``problems``
    field -- this split narrows the ONE specific case DW-FU-8-4 named,
    not a general loosening of the collision guard."""

    problems: tuple[str, ...]
    already_tracked: frozenset[int]


def _validate_batch(
    minted: list[tuple[LegacyEntry, str]],
    tracked_ids: set[str],
    tracked_summaries: set[str],
) -> _BatchValidation:
    """Validate `minted` (a project's full to-be-appended batch) -- PURE,
    no I/O. See `_BatchValidation`'s own docstring for the problems/
    already_tracked split.

    Checks, per this story's Boundaries: (a)/(b) no two entries in the
    batch share an id, and no batch id already exists as a `DW-` token in
    the tracked ledger -- both should be structurally impossible given
    `already_minted` threading through `mint_id_for_entry` (each call sees
    every id minted so far in this batch AND every id already in
    `tier3_path`/`tracked_path`), so these two checks are defense-in-depth,
    not the primary guard; (c) no two entries share the same `summary`
    text WITHIN the batch -- a genuine copy-pasted Tier-3 duplicate,
    ambiguous which (if either) is legitimate, still hard-aborts (DW-FU-8-4
    itself: "still hard-abort on a genuinely NEW collision"); (d) a
    `summary` matching the TRACKED ledger's existing entries -- an orphan
    whose content was already promoted by some other path without Tier-3
    ever growing a header for it (confirmed live in the real fleet
    backlog) -- routes to `already_tracked`, not `problems`.

    `summary` comparison is NORMALIZED (casefold + collapse internal
    whitespace, `_normalize_summary`) rather than byte-exact -- catches a
    summary lightly reworded/whitespace-normalized during a by-hand
    promotion pass (Review Triage Log 2026-08-15, item 8); `tracked_ids`/
    `tracked_summaries` must already be pre-normalized by the caller.
    Full fuzzy/near-duplicate matching is explicitly out of scope.

    A blank/whitespace-only `summary` is always treated as a validation
    FAILURE (blocks that entry's promotion) rather than silently exempted
    from dedup -- exempting it let two blank-summary orphans promote as if
    they were distinct findings, defeating the collision guard entirely
    (Review Triage Log 2026-08-15, item 7). Deliberately NOT routed to
    `already_tracked`: a blank summary cannot be content-matched against
    anything, tracked or otherwise, so there is no signal to skip it
    safely -- it stays a hard problem, unchanged."""
    problems: list[str] = []
    already_tracked: set[int] = set()
    seen_ids: dict[str, LegacyEntry] = {}
    seen_summaries: dict[str, LegacyEntry] = {}
    for idx, (entry, new_id) in enumerate(minted):
        if new_id in seen_ids:
            problems.append(
                f"duplicate id {new_id!r} within this batch "
                f"(Tier-3 lines {seen_ids[new_id].start_line} and {entry.start_line})"
            )
        else:
            seen_ids[new_id] = entry
        if new_id in tracked_ids:
            problems.append(
                f"minted id {new_id!r} (Tier-3 line {entry.start_line}) already "
                f"exists in the tracked ledger"
            )
        summary = entry.fields.get("summary", "").strip()
        if not summary:
            problems.append(
                f"blank/whitespace-only summary at Tier-3 line {entry.start_line} "
                f"-- cannot validate for duplicates, refusing to promote"
            )
            continue
        norm_summary = _normalize_summary(summary)
        if norm_summary in seen_summaries:
            problems.append(
                f"duplicate summary text within this batch (Tier-3 lines "
                f"{seen_summaries[norm_summary].start_line} and {entry.start_line}): "
                f"{summary[:80]!r}"
            )
        else:
            seen_summaries[norm_summary] = entry
        if norm_summary in tracked_summaries:
            already_tracked.add(idx)
    return _BatchValidation(tuple(problems), frozenset(already_tracked))


def _read_tracked(tracked_path: Path) -> tuple[bool, str]:
    """`(existed, text)` for `tracked_path` right now -- `_is_file`-gated
    (Review Triage Log 2026-08-15, item 5), so a permission-denied
    ancestor RAISES rather than silently reading as "does not exist yet".
    Shared by the initial snapshot and the pre-write re-check (item 1) so
    both ask the identical question the identical way."""
    existed = _is_file(tracked_path)
    text = tracked_path.read_text(encoding="utf-8") if existed else ""
    return existed, text


def _describe_counts(minted: list[tuple[LegacyEntry, str]], *, qualifier: str = "") -> str:
    """`"N orphan(s)"` / `"M already-identified entr(y|ies)"` / both joined
    with `" + "` -- the shared count phrase used by the "promoted", "no
    write -- already reached the tracked ledger", and "skipped" messages
    (Story 8.7), built from a `(entry, id)` list so it works identically
    whether called on `to_write` (the promoted subset), `minted` (the full
    batch), or the already-tracked-skipped subset. Orphan-only input
    renders EXACTLY as before Story 8.7 (`"N orphan(s)"`, no ` + ` suffix)
    -- existing callers/tests that only ever see all-orphan batches see
    byte-identical messages. `qualifier`, if given, is inserted before each
    count noun (e.g. `qualifier="already-tracked "` ->
    `"N already-tracked orphan(s)"`, matching the pre-Story-8.7 "skipped"
    message's own wording exactly for an orphan-only skip)."""
    orphan_n = sum(1 for entry, _ in minted if entry.id is None)
    identified_n = len(minted) - orphan_n
    parts = []
    if orphan_n:
        parts.append(f"{orphan_n} {qualifier}orphan(s)")
    if identified_n:
        parts.append(f"{identified_n} {qualifier}already-identified entr{'y' if identified_n == 1 else 'ies'}")
    return " + ".join(parts)


def _promote_project(slug: str, project_dir: Path) -> _Outcome:
    """Compute and (on a clean batch) write one project's promotion --
    classify -> split into orphans (mint a fresh id) and already-identified-
    but-untracked entries (Story 8.7: use `entry.id` verbatim, nothing to
    mint) -> combine into ONE batch -> in-memory collision validation ->
    re-check-then-write on success. Never touches `tier3_path`. A genuine
    `problems` collision (duplicate id, blank summary, a genuinely new
    duplicate summary) still aborts with NO write at all for this project
    (the tracked ledger, if any, is left byte-identical to its pre-run
    state). An `already_tracked` collision (DW-FU-8-4: an entry whose
    content already reached the tracked ledger by another path, under a
    different id) is excluded from the write instead -- the REST of a
    clean batch still promotes."""
    tier3_path = project_dir / TIER3_REL
    tracked_path = project_dir / TRACKED_REL

    if not _is_file(tier3_path):
        return _Outcome(slug, "no-op", f"{slug}: no Tier-3 file at {TIER3_REL.as_posix()} -- nothing to promote")

    entries = classify_tier3_entries(tier3_path)

    # Snapshot taken BEFORE minting/validation -- the window this story's
    # own review found a real, confirmed data-loss race in (Review Triage
    # Log 2026-08-15, item 1): a concurrent writer's change landing in this
    # window used to be silently destroyed by the terminal write below with
    # no symptom. Re-checked immediately before that write. Moved ahead of
    # the orphans/identified split (Story 8.7): `tracked_header_ids` is now
    # needed to even DETERMINE which already-identified entries are
    # untracked, not just to validate the batch afterward.
    tracked_existed, tracked_text = _read_tracked(tracked_path)
    tracked_entries = classify_tier3_entries(tracked_path) if tracked_existed else ()
    # Real `### DW-*:` headers only -- see the `_validate_batch` call below
    # for why a loose token match (this script's own pre-Story-8.7
    # `_dw_tokens`, removed: `mint_id_for_entry`'s own `_collect_dw_tokens`
    # already performs the equivalent loose check at mint time for orphans,
    # making a second loose check here redundant everywhere it was still
    # called) is the wrong direction for an already-fixed identified id
    # (Story 8.7 review finding).
    tracked_header_ids = {e.id for e in tracked_entries if e.id is not None}
    tracked_summaries = {
        _normalize_summary(s) for e in tracked_entries
        if (s := e.fields.get("summary", "").strip())
    }

    orphans = [e for e in entries if e.id is None]
    # Story 8.7: an entry that already carries a real id in Tier-3 but whose
    # id has never reached the tracked ledger as a `DW-` token -- a
    # structurally different gap from an orphan (nothing to mint, the id is
    # already fixed), `deferred_work_promote.py`'s original scope (Story
    # 8.1-8.4) never touched these at all.
    #
    # Deliberately checked against `tracked_header_ids` (real `### DW-*:`
    # headers only, from `classify_tier3_entries(tracked_path)`), NOT the
    # loose `tracked_ids` token harvest `_validate_batch` uses below --
    # live-confirmed HIGH-adjacent risk during this story's own adversarial
    # review: `tracked_ids` matches ANY `DW-` shaped substring anywhere in
    # the tracked file's raw text, including a plain prose MENTION inside an
    # unrelated entry's own `promoted:`/summary text (a `PoC` reproduced this
    # end to end: an id merely referenced in someone else's text was silently
    # classified "already tracked" and permanently skipped, exit 0, no
    # warning -- precisely the "silently never promoted" failure class this
    # capability exists to close). A real header is unambiguous identity;
    # a loose token is not. `_validate_batch`'s own separate `tracked_ids`
    # duplicate-id defense-in-depth check is intentionally left as the loose
    # match -- being OVER-cautious about refusing to mint/reuse an id that
    # merely LOOKS taken is the safe direction there, unlike here.
    #
    # EXCLUDES any entry with a blank/whitespace-only `summary:` field --
    # live-confirmed HIGH bug during this story's own adversarial review,
    # widened during a follow-up fleet-wide dry check that found it was NOT
    # limited to one origin. `Tier3Shape.IDENTIFIED_PLAIN` (a `### DW-<id>:`
    # header with plain, non-bulleted `origin:`/`source_spec:`/`severity:`/
    # `reason:`/`status:` fields) never populates `summary:` at all -- the
    # real text lives only in the header TITLE, which `classify_tier3_
    # entries` never captures. Two live, independently-emitted sub-shapes
    # confirmed on the real fleet: bmad-loop's `_harvest_spec_deferrals`
    # damping output (`origin: spec-deferred <fingerprint>` -- atlas 7,
    # scribe 4) and its separate "follow-up review still recommended after
    # the damping cap was spent" output (`origin: review-budget-followup` --
    # doctor 4, marshal 9, mason 3, steward 2, warden 2). `_validate_batch`'s
    # blank-summary guard hard-aborts the WHOLE project batch on just one
    # such entry, not merely excludes it -- confirmed live for BOTH shapes:
    # every one of doctor/marshal/mason/steward/warden's `--fix` runs would
    # have aborted outright (blocking 76/234/25/93/41 real orphans
    # respectively), not just atlas/scribe. Both sub-shapes also have their
    # OWN dedicated reconciliation (fingerprint-matching for the harvest
    # case, `scripts/deferred_work_intake.py`; content/history-based for the
    # follow-up-review case) that this generic id/summary-matching promoter
    # cannot safely replicate -- e.g. 6 of atlas's 7 harvest entries are
    # already promoted elsewhere under a DIFFERENT id, invisible to this
    # script, so promoting them here under their bare `DW-<n>` id would
    # create a duplicate. Left for those dedicated mechanisms, not this
    # generic promoter, regardless of which specific `origin:` value (if
    # any) the entry carries.
    identified_untracked = [
        e for e in entries
        if e.id is not None
        and e.id not in tracked_header_ids
        and e.fields.get("summary", "").strip()
    ]
    if not orphans and not identified_untracked:
        return _Outcome(
            slug, "no-op",
            f"{slug}: nothing to promote (0 orphans, 0 already-identified-but-"
            f"untracked, of {len(entries)} Tier-3 entries)",
        )

    already_minted: set[str] = set()
    minted: list[tuple[LegacyEntry, str]] = []
    for entry in orphans:
        try:
            new_id = mint_id_for_entry(entry, slug, tier3_path, tracked_path, already_minted)
        except ValueError as exc:
            return _Outcome(
                slug, "aborted",
                f"{slug}: ABORTED, no write -- could not mint an id for the orphan "
                f"at {TIER3_REL.as_posix()}:{entry.start_line} -- {exc}",
            )
        already_minted.add(new_id)
        minted.append((entry, new_id))
    # Already-identified entries need no minting -- fold them into the SAME
    # batch (their own `entry.id`, verbatim) so `_validate_batch` and the
    # write below treat both kinds uniformly, one combined append.
    minted.extend((entry, entry.id) for entry in identified_untracked)

    # Story 8.7: `tracked_header_ids` (strict, real headers), NOT the loose
    # `tracked_ids` -- an already-identified entry's `new_id` is its OWN
    # fixed `entry.id`, never freshly minted, so a loose prose MENTION of
    # that same string elsewhere in the tracked ledger must not read as "id
    # already exists" and hard-abort the entry that is precisely trying to
    # give that mention a real header for the first time (the same bug
    # class `identified_untracked`'s own membership check above was fixed
    # for -- reproduced live in review when this call still passed the loose
    # `tracked_ids`). Orphans lose nothing switching to the strict set here:
    # `mint_id_for_entry`'s own `_collect_dw_tokens` already checked the
    # SAME loose universe (both `tier3_path` and `tracked_path`) at mint
    # time, so this call's own duplicate-id check was already unreachable
    # defense-in-depth for orphans specifically (confirmed in review).
    validation = _validate_batch(minted, tracked_header_ids, tracked_summaries)
    if validation.problems:
        detail = "; ".join(validation.problems)
        return _Outcome(
            slug, "aborted",
            f"{slug}: ABORTED, no write -- {len(validation.problems)} collision(s): {detail}",
        )

    # DW-FU-8-4: entries already reached the tracked ledger by another path
    # are excluded here, never written again -- see `_BatchValidation`'s own
    # docstring. If EVERY entry in this batch is already-tracked, there is
    # nothing left to write; report that plainly rather than writing an
    # empty diff (and skip the race-check/write/baseline-restamp steps
    # below entirely, since nothing changes).
    to_write = [
        (entry, new_id) for idx, (entry, new_id) in enumerate(minted)
        if idx not in validation.already_tracked
    ]
    if not to_write:
        already_ids = ", ".join(new_id for _, new_id in minted)
        return _Outcome(
            slug, "no-op",
            f"{slug}: no write -- all {_describe_counts(minted)} already reached the "
            f"tracked ledger by another path, none re-promoted: {already_ids}",
        )

    # A `tracked_path` that already resolves to a DIRECTORY gets a friendly,
    # explicit refusal here rather than relying solely on the generic
    # per-project exception boundary in `main()` to catch the `os.replace`
    # `IsADirectoryError` a few lines down (Review Triage Log 2026-08-15,
    # item 10).
    if tracked_path.exists() and not tracked_path.is_file():
        return _Outcome(
            slug, "aborted",
            f"{slug}: ABORTED, no write -- {TRACKED_REL.as_posix()} already "
            f"exists but is a directory, not a file -- remove or rename it, "
            f"then re-run",
        )

    # Re-read-and-compare immediately before the terminal write (item 1):
    # if the tracked file changed since the snapshot above -- including
    # "did not exist, now does" -- ABORT rather than silently overwrite a
    # concurrent writer's change. True cross-process locking is out of
    # scope; this narrows the race window to the write call itself.
    race_existed, race_text = _read_tracked(tracked_path)
    if race_existed != tracked_existed or race_text != tracked_text:
        return _Outcome(
            slug, "aborted",
            f"{slug}: ABORTED, no write -- tracked ledger at "
            f"{TRACKED_REL.as_posix()} changed during this run "
            f"(concurrent write detected) -- re-run",
        )

    tier3_rel_str = TIER3_REL.as_posix()
    blocks = [_format_promoted_entry(new_id, entry, tier3_rel_str) for entry, new_id in to_write]
    new_blocks_text = "\n".join(blocks)
    if tracked_text:
        prefix = tracked_text if tracked_text.endswith("\n") else tracked_text + "\n"
        if not prefix.endswith("\n\n"):
            prefix += "\n"
        new_text = prefix + new_blocks_text
    else:
        new_text = new_blocks_text

    # Atomic write -- `tempfile.mkstemp` + `os.replace`, mirroring
    # `scripts/seed_claude_consent.py`'s own precedent (Review Triage Log
    # 2026-08-15, item 2): a plain `write_text` truncates the destination
    # before writing, so a crash mid-write (OOM/SIGKILL/disk-full) could
    # leave a durable, non-regenerable tracked ledger corrupted. Writing to
    # a sibling temp file first and `os.replace`-ing it in means the
    # tracked ledger is either fully the old content or fully the new
    # content, never a partial write.
    tracked_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(tracked_path.parent), prefix=tracked_path.name + ".")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(new_text)
        os.replace(tmp_name, tracked_path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise
    ids_str = ", ".join(new_id for _, new_id in to_write)
    message = f"{slug}: promoted {_describe_counts(to_write)} -- {ids_str}"
    if validation.already_tracked:
        skipped = [minted[idx] for idx in sorted(validation.already_tracked)]
        message += (
            f" (skipped {_describe_counts(skipped, qualifier='already-tracked ')}, "
            f"not re-promoted)"
        )

    # Story 8.4: re-stamp THIS project's grandfather baseline to its
    # current anonymous-entry count, now that the promotion above landed
    # (promoted_count > 0, ledger write already succeeded). `project_dir.
    # name` (e.g. "pyforge-mason"), not the short `slug` ("mason") -- that
    # is the key `deferred_work_baseline.py`'s own `_live_state()` uses. A
    # failure here must NOT roll back or reclassify the already-successful
    # ledger write -- caught and reported as a distinct, separately-labeled
    # warning naming the manual fallback instead (Boundaries "Block If"),
    # and `main()` still ends the overall run non-zero for it (item 2)
    # even though this project's own `status` stays "promoted".
    #
    # Story 8.7: the trigger stays "at least one ORPHAN actually landed in
    # `to_write`" -- unchanged from Story 8.4's own original "promoted_count
    # > 0 orphans" wording -- not merely "to_write is non-empty". The
    # baseline exists solely to grandfather `_anonymous()`'s own orphan
    # count for `tier3-entry-unidentified`; a run that promotes ONLY
    # already-identified entries (0 orphans) changes nothing that count
    # depends on, so re-stamping would be a needless write at best and, if
    # this project's baseline had never been stamped before, would silently
    # establish one for backlog this run never actually reviewed.
    baseline_warning = False
    orphan_written = sum(1 for entry, _ in to_write if entry.id is None)
    if orphan_written > 0:
        try:
            if deferred_work_baseline is None:
                # The sibling module itself failed to import (item 3) -- never
                # reached the actual stamp call, so name that specifically
                # rather than an opaque AttributeError on `None`.
                raise RuntimeError(
                    f"baseline module unavailable: {_BASELINE_IMPORT_ERROR}"
                )
            deferred_work_baseline.stamp_projects([project_dir.name])
        except Exception as exc:  # noqa: BLE001 -- see the docstring above:
            # this must degrade to a warning, never abort or unwind the
            # already-successful promotion.
            baseline_warning = True
            message += (
                f"; WARNING: baseline re-stamp failed -- "
                f"{exc.__class__.__name__}: {exc} -- run `python "
                f"scripts/deferred_work_baseline.py --write-baseline --project "
                f"{project_dir.name}` by hand"
            )
    return _Outcome(slug, "promoted", message, baseline_warning=baseline_warning)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fix", action="store_true",
                    help="promote every target project's Tier-3 orphans AND already-identified-"
                         "but-untracked entries into its tracked ledger")
    ap.add_argument("--project", action="append", metavar="SLUG", default=None,
                    help=("limit --fix to this project (repeatable). WITHOUT it, every "
                          "project under _bmad-output/projects/ with a Tier-3 file is "
                          "processed."))
    args = ap.parse_args()

    if args.project and not args.fix:
        ap.error("--project only makes sense with --fix")

    if not args.fix:
        print(
            "this script promotes Tier-3 legacy deferred-work orphans (Story 8.1/8.2's "
            "classify_tier3_entries/mint_id_for_entry) AND already-identified-but-"
            "untracked entries (Story 8.7: a real DW-* id already exists in Tier-3, "
            "just never copied to the tracked ledger) into their project's tracked "
            "ledger -- never Tier-3 itself. A successful promotion also re-stamps "
            "that project's grandfather baseline (scripts/.deferred-work-baseline.json) "
            "via deferred_work_baseline.py's stamp_projects (Story 8.4), but only when "
            "at least one orphan was freshly promoted. Nothing is "
            "written without --fix. Pass --fix [--project SLUG ...].",
            file=sys.stderr,
        )
        return 2

    try:
        slug_map = _project_slug_map()
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.project:
        unknown = sorted(set(args.project) - set(slug_map))
        if unknown:
            print(f"unknown project(s): {', '.join(unknown)}\n"
                  f"known: {', '.join(sorted(slug_map))}", file=sys.stderr)
            return 2
        targets = sorted(set(args.project))
    else:
        targets = _discover_projects(slug_map)

    if not targets:
        print("no project under _bmad-output/projects/ has a Tier-3 file -- nothing to do")
        return 0

    projects_dir = REPO_ROOT / "_bmad-output" / "projects"
    exit_code = 0
    for slug in targets:
        try:
            outcome = _promote_project(slug, projects_dir / slug_map[slug])
        except Exception as exc:  # noqa: BLE001 -- a crash promoting one
            # project (an I/O error, an unreadable ancestor -- see
            # `_is_file`) must not abort the whole multi-project run
            # (Review Triage Log 2026-08-15, item 4): report it as THIS
            # project's own failure and continue to the next one, matching
            # the "one project's collision must not block a sibling's
            # clean promotion" AC.
            print(f"{slug}: ABORTED, no write -- unexpected "
                  f"{exc.__class__.__name__}: {exc}")
            exit_code = 1
            continue
        print(outcome.message)
        if outcome.status == "aborted":
            exit_code = 1
        # Story 8.4, Review Triage Log 2026-08-15, item 2: a baseline
        # re-stamp warning must also make the OVERALL run non-zero, even
        # though every ledger write succeeded and this project's own
        # `status` correctly stays "promoted" -- a caller checking only the
        # exit code (CI, cron) must still learn the manual fallback command
        # is needed.
        if outcome.baseline_warning:
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
