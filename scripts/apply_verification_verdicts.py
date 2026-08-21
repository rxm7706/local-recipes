"""Mutation-only: apply agent/human-judged verification verdicts to tracked
deferred-work-ledger.md entries (Story 11.4, CAP-4).

Stories 11.1-11.3 select due-for-verification entries, deprioritize
churn-free ones, and mechanically resolve one grep-recomputable claim shape
-- but the great majority of the fleet's live due entries carry no
mechanical verdict at all: either 11.3 escalated them, or their claim is not
grep-recomputable in the first place, and genuinely need a human or agent to
read the named code and judge. Nothing before this script let that judgment
land back on the ledger safely: writing a `verified:` line by hand is
error-prone (wrong vocabulary, a restated claim instead of real evidence, a
stray edit to an unrelated field), and Doctor itself must stay read-only
(NFR-1; `pyforge.doctor`'s `sources/` package is read-only by construction,
meta-test enforced).

This script closes that gap: given a `--verdicts-file` (a JSON array of
`{project, id, verdict, evidence}` objects, one or more projects in the same
file), it validates each named project's WHOLE batch in memory -- a closed
four-verdict vocabulary, non-empty evidence, no restating the entry's own
prose, the id actually exists -- and, only on a clean batch, appends one new
`verified: <date> — <verdict> — <evidence>` line to each named entry's span
in its project's tracked ledger. It never judges truth itself: a human or an
agent reading the code still decides the verdict and writes the evidence
text; this script is the safe, disciplined write path for that decision.

**Why this lives here, not in `pyforge.doctor`.** Same reasoning
`deferred_work_promote.py`'s own docstring already states: Doctor's
`sources/` package is deliberately READ-ONLY, so a `--fix` write path never
belongs there and never will.

Mirrors `deferred_work_promote.py`'s own established mutation-script shape
end to end (Story 8.3): lives in `scripts/`, duplicates rather than imports
its one regex dependency (`chain.py`'s own private `_ENTRY_RE` pattern
SHAPE, never the underscore-prefixed symbol), validates a whole batch in
memory before writing anything, writes atomically (`tempfile.mkstemp` +
`os.replace`) with a re-read-immediately-before-write race check, isolates
one project's failure from a sibling's clean run, and requires `--fix`
before anything is written at all.

**Never** mutates `status:`/`summary:`/`evidence:` or any OTHER FIELD'S
content -- a prior `verified:` line (an earlier re-verification) is never
removed or edited; re-verification history is additive. (Review finding,
docstring correction: the entry's own trailing whitespace/blank-line COUNT
within its span is normalized on write -- `rstrip()` + a fixed `"\n\n"`
before the new line -- since every real entry already ends with exactly one
blank line before the next heading; this never changes any field's text.)
**Never** touches `implementation-artifacts/deferred-work.md`
(Tier-3) -- tracked ledgers only. **Never** re-derives Story 11.1/11.2/11.3's
own due/churn/mechanical selection logic to restrict which entries are
eligible targets: any existing tracked entry id is a valid target, since a
human or agent calling this script already knows which entry it just
investigated.

Usage (plain `python`, no pixi task -- mirrors `deferred_work_promote.py`'s
own precedent):
        python scripts/apply_verification_verdicts.py --verdicts-file PATH --fix
"""
from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
import tempfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

TRACKED_REL = Path("planning-artifacts") / "deferred-work-ledger.md"

#: The closed CAP-4 verdict vocabulary (Boundaries) -- lowercase-hyphen,
#: reusing Story 11.3's own `mechanical_verdict` token style (`still-open`
#: is the literal same string in both layers). `escalate` is 11.3's own
#: internal mechanical-tier signal, never a terminal CAP-4 verdict, and is
#: deliberately NOT a member here.
_VERDICTS = frozenset({
    "still-open", "resolved", "moot-superseded", "pending-on-precondition",
})

#: Duplicated (not imported) from `chain.py`'s own private `_ENTRY_RE` --
#: reusing the pattern SHAPE per this story's Boundaries ("duplicating
#: `chain.py`'s own private `_ENTRY_RE` pattern SHAPE... never importing the
#: underscore-prefixed symbol"), mirroring `deferred_work_promote.py`'s own
#: established "reuse the approach, not the private symbol" precedent.
_ENTRY_RE = re.compile(r"^#{2,4}\s+(DW-[A-Za-z0-9][A-Za-z0-9-]*)", re.MULTILINE)

#: Any markdown heading, 1-6 `#`s -- a narrow, deliberate ADDITION beyond
#: `_ENTRY_RE` alone (this story's own implementation decision, per
#: Boundaries: "this story's own implementation decisions to make and
#: record"). See `_entry_spans`'s own docstring for why an entry's span must
#: be bounded by ANY heading, not merely the next `DW-` entry.
_HEADING_RE = re.compile(r"^#{1,6}\s", re.MULTILINE)

#: Matches a `summary:`/`evidence:`/`reason:` field line in either live
#: shape: the identified-bulleted format's 2-space bullet continuation
#: (`  summary: ...`) or the flat, unindented "review-budget-followup"
#: format (`reason: ...`, no `summary:`/`evidence:` at all) -- both occur
#: live across the fleet's tracked ledgers. `reason:` is the flat shape's
#: OWN narrative field (review finding, patch): without it, the
#: anti-restatement check in `_validate_project_batch` was structurally
#: inert for every flat-shape entry -- `fields` came back empty, so the
#: "evidence restates the entry's own prose" guard could never fire for an
#: entire documented, tested-as-valid entry shape.
_FIELD_RE = re.compile(r"^\s*(?:-\s+)?(summary|evidence|reason):\s*(.*)$")


def _probe(p: Path) -> os.stat_result | None:
    """``p.stat()``, or ``None`` when ``p`` genuinely does not exist --
    RAISING when the answer cannot be determined. Duplicated in SHAPE from
    `deferred_work_promote.py`'s own private `_probe` (itself duplicated
    from `chain.py`'s), not imported."""
    try:
        return p.stat()
    except (FileNotFoundError, NotADirectoryError):
        return None


def _is_file(p: Path) -> bool:
    """``p.is_file()`` that raises rather than lying -- see ``_probe``."""
    st = _probe(p)
    return st is not None and stat.S_ISREG(st.st_mode)


def _normalize(text: str) -> str:
    """Casefold + collapse-internal-whitespace form of a field's text,
    mirroring `deferred_work_promote.py`'s own `_normalize_summary` --
    used ONLY for the anti-restatement comparison, never for what gets
    written. This is intentionally a narrow, mechanical proxy for CAP-4's
    real requirement ("never a restatement of the entry's own prose"):
    exact-normalized-equality catches the sharpest failure mode (an agent
    literally echoing the claim back) without attempting fuzzy/semantic
    similarity (Boundaries -- Never)."""
    return re.sub(r"\s+", " ", text).strip().casefold()


def _entry_spans(text: str) -> dict[str, tuple[int, int, dict[str, str]]]:
    """``{id: (start, end, fields)}`` for every ID'd entry in a tracked
    ledger's raw text -- a boundary walk over `_ENTRY_RE` marks.

    ``end`` is bounded by the first markdown heading of ANY level
    (`_HEADING_RE`) strictly after the entry's own header line -- not
    merely the next `DW-` entry, unlike `chain.py`'s own `_verification()`
    boundary walk. A tracked ledger interleaves `DW-` entries with
    unrelated `## Deferred from: ...` section headings that own no field
    content of their own (confirmed live in pyforge-warden's and
    pyforge-doctor's own ledgers); stopping only at the next `DW-` mark
    would let a NEW `verified:` line land AFTER one of those unrelated
    headings instead of right after this entry's own content -- silently
    attributing the verdict to the wrong place in the document.
    `_verification()`'s wider span is fine for ITS OWN purpose (staleness
    detection over already-written text only ever reads inward, never
    writes), but this script INSERTS new content, so a tighter,
    heading-bounded span is required for correctness here.

    ``fields`` holds ``summary``/``evidence``/``reason`` (the three the
    anti-restatement check needs -- ``reason`` is the flat "review-budget-
    followup" shape's own narrative field, since that shape carries no
    ``summary:``/``evidence:`` at all), each the single physical line's text
    following its key. Continuation-line JOINING (a field's value wrapping
    across several physical lines) is deliberately NOT reproduced here,
    unlike `chain.py`'s own fuller `classify_tier3_entries`: every real
    `summary:`/`evidence:` value observed live across the fleet's tracked
    ledgers is one long physical line, and this is a narrow, mechanical
    anti-restatement proxy (Design Notes), not a full field parser."""
    marks = [(m.start(), m.group(1)) for m in _ENTRY_RE.finditer(text)]
    headings = [m.start() for m in _HEADING_RE.finditer(text)]
    spans: dict[str, tuple[int, int, dict[str, str]]] = {}
    for pos, ident in marks:
        end = next((h for h in headings if h > pos), len(text))
        fields: dict[str, str] = {}
        for line in text[pos:end].splitlines():
            m = _FIELD_RE.match(line)
            if m and m.group(1) not in fields:
                fields[m.group(1)] = m.group(2).strip()
        spans[ident] = (pos, end, fields)
    return spans


def _load_verdicts(path: Path) -> list[dict[str, str]]:
    """Parse ``path`` as a JSON array of ``{project, id, verdict, evidence}``
    objects (all four keys required, all string-valued) -- STRUCTURAL
    validation only (shape), never verdict-vocabulary or evidence-content
    checks (those are a per-project BATCH concern, `_validate_project_batch`'s
    own job: an invalid TOKEN aborts only its own project's write, while a
    malformed FILE cannot be attributed to any project at all).

    Raises ``ValueError`` on any structural problem -- the caller (`main`)
    turns that into a top-level usage error, exit 2, matching the I/O
    matrix's "a malformed file is a top-level usage error, not a
    per-project batch failure" contract."""
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"could not read {path}: {exc}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(data, list):
        raise ValueError(  # noqa: TRY004 -- one exception TYPE for every
            # structural problem in this function, deliberately, so `main()`
            # has exactly one type to catch for "malformed input file".
            f"{path} must contain a JSON array, got {type(data).__name__}"
        )
    required = ("project", "id", "verdict", "evidence")
    items: list[dict[str, str]] = []
    for i, obj in enumerate(data):
        if not isinstance(obj, dict):
            raise ValueError(f"{path}[{i}] is not a JSON object")  # noqa: TRY004
        missing = [k for k in required if k not in obj]
        if missing:
            raise ValueError(
                f"{path}[{i}] is missing required key(s): {', '.join(missing)}"
            )
        not_str = [k for k in required if not isinstance(obj[k], str)]
        if not_str:
            raise ValueError(
                f"{path}[{i}] has non-string value(s) for: {', '.join(not_str)}"
            )
        items.append({k: obj[k] for k in required})
    return items


def _validate_project_batch(
    entries_by_id: dict[str, tuple[int, int, dict[str, str]]],
    items: list[dict[str, str]],
) -> list[str]:
    """Every problem found in one project's whole to-be-applied batch, or
    ``[]`` for a clean batch -- PURE, no I/O (Boundaries: validate the WHOLE
    batch in memory before writing anything for that project).

    Checks: verdict-vocabulary membership, non-empty single-line evidence,
    the id actually exists in ``entries_by_id``, the evidence does not
    normalize identical to that entry's own ``summary:``/``evidence:``/
    ``reason:`` field text, and no id repeats within this batch (the same
    entry cannot receive two different verdicts in one run -- ambiguous
    which should win)."""
    problems: list[str] = []
    seen: dict[str, int] = {}
    for i, item in enumerate(items):
        entry_id = item["id"]
        if entry_id in seen:
            problems.append(
                f"duplicate id {entry_id!r} appears at both position "
                f"{seen[entry_id]} and {i} in the verdicts file"
            )
        else:
            seen[entry_id] = i

        if item["verdict"] not in _VERDICTS:
            problems.append(
                f"{entry_id}: invalid verdict {item['verdict']!r} -- must be "
                f"one of {', '.join(sorted(_VERDICTS))}"
            )

        evidence = item["evidence"].strip()
        if not evidence:
            problems.append(f"{entry_id}: evidence is empty (or whitespace-only)")
        elif "\n" in evidence or "\r" in evidence:
            # Review finding, patch: every real `summary:`/`evidence:` value
            # is one physical line (`_entry_spans`'s own docstring), and
            # `_format_verified_line` only `.strip()`s (trims edges) rather
            # than rejecting an embedded newline -- an unstripped multi-line
            # evidence string would silently write a stray, unindented line
            # into the ledger that matches no `_FIELD_RE`/`_ENTRY_RE`
            # pattern, breaking the one-physical-line-per-field invariant
            # every reader of this file (including this script's own
            # `_entry_spans`) already assumes.
            problems.append(
                f"{entry_id}: evidence must be a single physical line "
                f"(contains an embedded newline)"
            )

        if entry_id not in entries_by_id:
            problems.append(f"{entry_id}: no such entry in the tracked ledger")
            continue

        if evidence:
            norm_evidence = _normalize(evidence)
            _, _, fields = entries_by_id[entry_id]
            for key in ("summary", "evidence", "reason"):
                existing = fields.get(key, "")
                if existing and norm_evidence == _normalize(existing):
                    problems.append(
                        f"{entry_id}: evidence restates the entry's own "
                        f"{key}: field verbatim (normalized) -- not real evidence"
                    )
    return problems


def _format_verified_line(verdict: str, evidence: str, today: date) -> str:
    """One new `verified:` line -- 2-space indent, em-dash (`—`) separators,
    matching the real ledger format already in use (Boundaries)."""
    return f"  verified: {today.isoformat()} — {verdict} — {evidence.strip()}\n"


def _apply_verdicts_to_text(
    text: str,
    entries_by_id: dict[str, tuple[int, int, dict[str, str]]],
    items: list[dict[str, str]],
    today: date,
) -> str:
    """``text`` with one new `verified:` line appended at the end of each
    ``items`` entry's own span (Boundaries: after any existing content,
    never touching a prior `verified:` line or any other field).

    Applied in DECREASING span-start order so each not-yet-processed
    entry's precomputed ``(start, end)`` offsets (from ``entries_by_id``,
    computed once against the ORIGINAL text) stay valid: a splice at
    ``[start, end)`` only ever changes text at or after its own ``start``,
    and every remaining entry lies strictly to its LEFT."""
    ordered = sorted(items, key=lambda it: entries_by_id[it["id"]][0], reverse=True)
    for item in ordered:
        start, end, _ = entries_by_id[item["id"]]
        stripped = text[start:end].rstrip()
        verified_line = _format_verified_line(item["verdict"], item["evidence"], today)
        gap = "\n" if text[end:] else ""
        text = text[:start] + stripped + "\n\n" + verified_line + gap + text[end:]
    return text


@dataclass
class _Outcome:
    project: str
    status: str  # "applied" | "aborted"
    message: str


def _read_tracked(path: Path) -> tuple[bool, str]:
    """``(existed, text)`` for ``path`` right now -- `_is_file`-gated so a
    permission-denied ancestor RAISES rather than silently reading as "does
    not exist yet". Shared by the initial snapshot and the pre-write race
    re-check, mirroring `deferred_work_promote.py`'s own `_read_tracked`
    precedent."""
    existed = _is_file(path)
    text = path.read_text(encoding="utf-8") if existed else ""
    return existed, text


def _known_projects() -> frozenset[str]:
    """Every real directory name under ``_bmad-output/projects/`` right
    now -- mirrors `deferred_work_promote.py`'s own `_project_slug_map`
    precedent of validating a caller-supplied project identifier against
    the ACTUAL discovered project set, rather than trusting it verbatim."""
    projects_dir = REPO_ROOT / "_bmad-output" / "projects"
    if not projects_dir.is_dir():
        return frozenset()
    return frozenset(p.name for p in projects_dir.iterdir() if p.is_dir())


def _apply_project(
    project: str, items: list[dict[str, str]], today: date,
) -> _Outcome:
    """Compute and (on a clean batch) write one project's verdicts --
    snapshot -> validate -> re-check-then-write on success, mirroring
    `deferred_work_promote.py`'s own `_promote_project` shape. On any
    problem, aborts with NO write at all for this project.

    ``project`` is validated against `_known_projects()` BEFORE it ever
    reaches a path join (review finding, patch): `Path.__truediv__` silently
    discards everything to its left when the right operand is absolute
    (confirmed empirically -- `Path('/a') / '/etc/passwd_dir'` ==
    `Path('/etc/passwd_dir')`), so an absolute or `..`-laden `project`
    string from the verdicts file could otherwise resolve `tracked_path`
    entirely outside `_bmad-output/projects/`. This is the one check
    `deferred_work_promote.py`'s own `_project_slug_map`/`unknown
    project(s):` precedent already has and this script had dropped despite
    the spec's own "mirrors `deferred_work_promote.py`'s established shape
    end to end" Design Notes -- restored here. An empty/whitespace-only
    `project` value is caught by the same check (it can never match a real
    discovered directory name)."""
    if project not in _known_projects():
        return _Outcome(
            project, "aborted",
            f"{project!r}: ABORTED, no write -- unknown project (not a real "
            f"directory under _bmad-output/projects/)",
        )
    tracked_path = REPO_ROOT / "_bmad-output" / "projects" / project / TRACKED_REL

    tracked_existed, tracked_text = _read_tracked(tracked_path)
    if not tracked_existed:
        return _Outcome(
            project, "aborted",
            f"{project}: ABORTED, no write -- no tracked ledger at "
            f"{TRACKED_REL.as_posix()} for this project",
        )

    entries_by_id = _entry_spans(tracked_text)
    problems = _validate_project_batch(entries_by_id, items)
    if problems:
        detail = "; ".join(problems)
        return _Outcome(
            project, "aborted",
            f"{project}: ABORTED, no write -- {len(problems)} problem(s): {detail}",
        )

    # Re-read-and-compare immediately before the terminal write: if the
    # tracked file changed since the snapshot above -- including "did not
    # exist, now does" -- ABORT rather than silently overwrite a concurrent
    # writer's change (Boundaries).
    race_existed, race_text = _read_tracked(tracked_path)
    if race_existed != tracked_existed or race_text != tracked_text:
        return _Outcome(
            project, "aborted",
            f"{project}: ABORTED, no write -- tracked ledger at "
            f"{TRACKED_REL.as_posix()} changed during this run "
            f"(concurrent write detected) -- re-run",
        )

    new_text = _apply_verdicts_to_text(tracked_text, entries_by_id, items, today)

    # Atomic write -- `tempfile.mkstemp` + `os.replace`, matching
    # `deferred_work_promote.py`'s own precedent: the tracked ledger is
    # either fully the old content or fully the new content, never a
    # partial write.
    fd, tmp_name = tempfile.mkstemp(
        dir=str(tracked_path.parent), prefix=tracked_path.name + ".",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(new_text)
        os.replace(tmp_name, tracked_path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise

    ids_str = ", ".join(item["id"] for item in items)
    return _Outcome(
        project, "applied",
        f"{project}: applied {len(items)} verdict(s) -- {ids_str}",
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--verdicts-file", metavar="PATH", type=Path, default=None,
        help="JSON array of {project, id, verdict, evidence} objects to apply",
    )
    ap.add_argument(
        "--fix", action="store_true",
        help="apply every clean project's batch of verdicts to its tracked ledger",
    )
    args = ap.parse_args()

    if not args.fix:
        print(
            "this script appends agent/human-judged verification verdicts "
            "(CAP-4's closed vocabulary: still-open / resolved / "
            "moot-superseded / pending-on-precondition) as a new `verified:` "
            "line onto a tracked deferred-work-ledger.md entry -- never any "
            "other field, and never a judgment of its own (a human or agent "
            "supplies the verdict and evidence; this script only writes it "
            "safely). Nothing is written without --fix. Pass "
            "--verdicts-file PATH --fix.",
            file=sys.stderr,
        )
        return 2

    if args.verdicts_file is None:
        print("--verdicts-file PATH is required with --fix", file=sys.stderr)
        return 2

    try:
        items = _load_verdicts(args.verdicts_file)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if not items:
        print("--verdicts-file names no verdicts -- nothing to apply")
        return 0

    by_project: dict[str, list[dict[str, str]]] = {}
    for item in items:
        by_project.setdefault(item["project"], []).append(item)

    # The caller never supplies the date (Boundaries) -- stamped here, once,
    # at the one call boundary, mirroring `chain.py`'s own established
    # `today: date | None = None` pattern.
    today = date.today()  # noqa: DTZ011 -- see the comment above
    exit_code = 0
    for project in sorted(by_project):
        try:
            outcome = _apply_project(project, by_project[project], today)
        except Exception as exc:  # noqa: BLE001 -- one project's crash must
            # not abort a sibling's clean run (Boundaries), mirroring
            # `deferred_work_promote.py`'s own per-project isolation in main().
            print(f"{project}: ABORTED, no write -- unexpected "
                  f"{exc.__class__.__name__}: {exc}")
            exit_code = 1
            continue
        print(outcome.message)
        if outcome.status == "aborted":
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
