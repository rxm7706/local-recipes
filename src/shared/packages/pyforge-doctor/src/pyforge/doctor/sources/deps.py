"""The forward-dependency gather filter -- Doctor's verdict on the one defect
``bmad-loop``'s own picker is structurally blind to (Story 6.7, FR-15).

THE DEFECT THIS CATCHES
------------------------
``bmad-loop``'s picker (``next_actionable`` in ``bmad_loop.sprintstatus``,
called from ``engine.py``'s ``_pick_next``) is a strict file-order scan within
the current epic. It has no ``depends_on`` concept at all. It only ever checks
whether a story's status in ``sprint-status.yaml`` is actionable.

A station's ``epics.md``-family document can document a real per-story
dependency via a ``**Deps:** S-X.Y`` field under a ``### Story E.N: Title``
heading. When that dependency names a story from a LATER epic than the one
declaring it, the engine cannot tell -- it will dispatch the dependent story
the moment its own epic's earlier stories clear, and burn a real dev attempt
(plus review cycles) on work that structurally cannot complete yet.

Found live 2026-08-03 in pyforge-marshal: ``2-3`` (deps ``S-3.2``), ``2-7``
(deps ``S-4.1``), and ``8-5`` (deps ``S-10.2``). All three already documented
their forward dependency in prose; it just never reached the file the engine
reads. See ``docs/dreams/bmad-loop-forward-dependency-blindness.md``.

THE FIX (not this source's job -- this only reports a MISSING fix)
------------------------------------------------------------------
Set the forward-dependent story's status to the non-standard value ``blocked``
in the loop-home's live Tier-3 feed and promote it to the tracked twin via
``python3 scripts/promote_sprint_status.py``. Safe because
``bmad_loop.sprintstatus.load()`` does not validate ``status`` against its own
declared ``STORY_STATUSES`` enum -- any string is accepted, and the actionable
set naturally excludes anything that is not ``backlog``/``ready-for-dev``.
Same mechanism the pre-existing ``optional`` retrospective status relies on.

WHY THIS MODULE RESTATES THE HARNESS ENUM (AD-13)
--------------------------------------------------
``scripts/forward_dependency_check.py`` imported
``bmad_loop.sprintstatus.ACTIONABLE_STATUSES`` -- *derived, never restated*, so
the check could not drift from real engine behaviour. Re-homing the detector
into Doctor made that import a liability rather than a virtue:

* Doctor is a deliberately lean package (7 conda dependencies) whose contract
  is a five-second pre-flight (NFR-4, counter-metric SM-C1). ``bmad_loop`` is
  3.3 MB across 33 modules, git-pinned.
* AD-11's rule is about MACHINERY, not package names: a verdict assembled from
  the judged station's own machinery fails in exactly the case worth checking
  -- when that machinery is what broke. ``bmad_loop`` IS the machinery this
  source judges the blindness of.
* One check's dependency would have become the whole CLI's: a ``bmad-loop``
  resolution failure would take ``check``, ``monitor`` and ``diagnose`` down
  with it.

So the set is restated below, and the *invariant* moved from runtime import to
test-time equality -- see ``ACTIONABLE_STATUSES``' own comment. The practical
gain is measurable, not theoretical: CI runs detectors on plain ``setup-python``
with no pixi and no ``bmad_loop``, so the original script reports UNKNOWN
(``exit 2``) there. Dropping the import is what lets this check run in CI at all.

INDEPENDENCE
------------
This module imports no station package and no harness. Charter §6 is satisfied
structurally: the verdict keeps working when ``pyforge.marshal`` and
``bmad_loop`` are both absent, broken, or wrong. Asserted by
``tests/unit/test_sources_deps_independence.py``.

COVERAGE -- four classes, keyed on MACHINE-READABLE references
---------------------------------------------------------------
A station is ``measured`` only when every dependency declaration it makes is
machine-readable. Reporting is deliberately conservative, because this
detector's own bookkeeping was itself a false green until 2026-08-08: coverage
was gated on any ``**Deps:**`` *text* rather than a parseable *reference*, so
mason reported measured-and-clean with 0 of 30 declarations readable.

* ``measured``     -- every declaration resolved, or explicitly declared none.
* ``partial``      -- a real dependency stated in a grammar ``DEP_RE`` cannot
                      parse; the ratio is named, so a station can never read as
                      fully verified.
* ``no-dispatch``  -- the ledger positively shows 0 actionable stories, so
                      nothing can be dispatched early. A measured fact about
                      the LEDGER, never a parse-cleanliness claim.
* ``unmeasured``   -- no declaration and work remains, or the ledger is
                      unreadable. No data is not the same as no risk.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..models import DoctorStatus, Finding, Source

# The same set ``bmad_loop.sprintstatus`` declares, RESTATED rather than
# imported -- see this module's docstring and AD-13 for why.
#
# The invariant that the import used to buy is not dropped, it MOVED:
# ``.claude/skills/conda-forge-expert/tests/meta/test_actionable_statuses_conformance.py``
# imports the installed ``bmad_loop`` and asserts SET EQUALITY against the
# literal below, parsed out of this file with ``ast``. That test imports
# ``bmad_loop`` unconditionally and FAILS -- never skips -- when it is absent,
# which is the only reason this restatement is safe.
#
# Keep this a plain literal of ``str``. The conformance test reads it as an AST
# literal, so a computed value would defeat the comparison rather than trip it.
ACTIONABLE_STATUSES = frozenset({"backlog", "ready-for-dev"})

# `### Story 2.3: Title *(optional trailing note)*` -- the ONE canonical shape
# (EXEMPLAR-STANDARD INV-5), used by all 8 stations.
#
# This deliberately carries NO station-specific accommodation, and that is the
# point. On 2026-08-08 an alias-first branch was added to the origin script to
# see atlas's `### Story A1 (2.1):` headings -- making it the FOURTH codebase
# carrying a private guess at one station's shape. The branch was removed the
# same day once atlas's data was normalized instead: 38 headings, 32 ledger
# keys, 32 story-spec filenames and 32 board ids renamed in lockstep, so there
# is exactly one convention left to parse.
#
# A station that regresses to an unparseable heading is NOT silently clean:
# zero parsed stories means zero declarations, which reports UNMEASURED (or
# NO-DISPATCH when its ledger proves nothing is actionable) -- never MEASURED.
STORY_HEADING_RE = re.compile(
    r"^### Story (?P<pe>\d+)\.(?P<pn>\d+[a-z]?): ?"
    r"(?P<title>.*?)(?:\s*\*\(.*?\)\*)?\s*$",
    re.M,
)

# `**Deps:**` (marshal, mason's satellite) or `**Depends on:**` (atlas's field
# name), searched within the story's own block and NOT anchored to a line
# start: the field routinely shares a line with `**Type:**`/`**Effort:**`
# (`**Type:** feature • **Effort:** M • **Deps:** S-1.1, S-1.3`), so a
# line-boundary-anchored scan would never find it.
DEPS_FIELD_RE = re.compile(r"\*\*(?:Deps|Depends on):\*\* ?(.*?)(?:\s*•|\n|$)")

# `S-<epic>.<num>` for a story, `S-<epic>.*` for a whole-epic dependency, with
# an OPTIONAL `<station>:` prefix marking a cross-station reference.
#
# The epic-level form exists because real declarations legitimately depend on an
# entire epic ("Epic 3 complete"), and there was previously no machine-readable
# way to say so -- which pushed those declarations into prose, where this check
# could not see them at all.
#
# KNOWN LIMITATION -- an UNPREFIXED `S-<epic>.<num>` has no station qualifier,
# so a cross-station dependency written without the prefix is silently read as
# one of the DECLARING station's own epics. Live example: atlas 12.2's
# `**Deps:** Steward S-2.1` (space, no colon) parses as atlas's own epic 2.
# Harmless today only because 2 < 12 and atlas's epic 2 is shipped. Tracked as
# DW-FWDDEP-2026-08-08-1; fixing it means giving the field a station-qualified
# grammar, which is a contract change to every station's epics doc, not a regex
# tweak.
DEP_RE = re.compile(
    r"(?:(?P<station>[a-z][a-z0-9-]*):)?S-(?P<epic>\d+)\.(?P<num>\d+[a-z]?|\*)",
    re.I,
)

LEDGER_STORY_RE = re.compile(r"^  (\d+)-(\d+)([a-z]?)-\S+: (\S+)$", re.M)

# An explicit "no dependency" declaration, which is READABLE -- it resolves to
# the empty set rather than being unparseable. Covers marshal/doctor/steward's
# `—` and atlas/mason's prose-qualified forms (`none (runs manually, …)`).
# The lookahead is `(?![\w-])` and NOT `\b`: `\b` after a non-word character
# like `—` can never match at end-of-string, which silently misfiled steward's
# two `—` declarations as prose on the first attempt.
NO_DEP_RE = re.compile(r"^\s*(?:—|–|-|none|nothing|n/?a)(?![\w-])", re.I)


def find_epics_files(project_dir: Path) -> list[Path]:
    """Every epics-family doc that can carry a ``**Deps:**`` field."""
    pa = project_dir / "planning-artifacts"
    if not pa.is_dir():
        return []
    # The glob stays: it also matches chain-scoped epics (marshal's
    # epics-regenerable-factory.md, mason's epics-presenton-pixi-image.md). The
    # epics-with-stories.md exclusion was dropped 2026-09-07 with the file itself
    # (marshal Story 32.4, spec-fleet-consistency-standard CAP-3) -- it was a derived
    # summary carrying no Deps field, retired fleet-wide once an audit of all eight
    # confirmed nothing normative lived only there.
    return sorted(pa.glob("epics*.md"))


def story_deps(epics_file: Path) -> list[tuple[int, str, str, str]]:
    """``[(epic, num, title, deps_text)]`` for every structured story found.

    A story's Deps field must appear within its own block (up to the next
    ``### Story`` heading), searched anywhere in that text -- not anchored to a
    line start, since it routinely shares a line with Type/Effort.
    """
    text = epics_file.read_text(encoding="utf-8")
    headings = list(STORY_HEADING_RE.finditer(text))
    out: list[tuple[int, str, str, str]] = []
    for i, m in enumerate(headings):
        block_end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        block = text[m.end() : block_end]
        dm = DEPS_FIELD_RE.search(block)
        deps = dm.group(1).strip() if dm else ""
        out.append((int(m.group("pe")), m.group("pn"), (m.group("title") or "").strip(), deps))
    return out


def ledger_statuses(ledger_path: Path) -> dict[str, str]:
    """``{story_key: status}`` from a tracked sprint ledger, ``{}`` if absent."""
    if not ledger_path.is_file():
        return {}
    return {
        f"{ep}-{num}{suf}": status
        for ep, num, suf, status in LEDGER_STORY_RE.findall(ledger_path.read_text(encoding="utf-8"))
    }


def _dep_satisfied(ledger: dict[str, str], epic: str, num: str) -> bool:
    """Whether the dependency ``S-<epic>.<num>`` is already finished.

    ``num`` may be ``*`` (the grammar's whole-epic reference), which is
    satisfied only when EVERY story cataloged for that epic is done -- and
    never by an epic with no stories in the ledger at all, which would
    otherwise make an unreadable ledger look like a satisfied dependency.
    A story absent from the ledger is not done.

    The epic-prefix comparison also excludes the ledger's own ``epic-<n>``
    rollup rows, whose prefix is the literal ``epic`` and so never equals a
    numeric epic id.
    """
    if num == "*":
        stories = [st for key, st in ledger.items() if key.split("-", 1)[0] == epic]
        return bool(stories) and all(st == "done" for st in stories)
    return ledger.get(f"{epic}-{num}") == "done"


def _finding(status: DoctorStatus, check: str, message: str, **evidence) -> Finding:
    return Finding(
        source=Source.FORWARD_DEPENDENCY,
        check=check,
        status=status,
        message=message,
        evidence=evidence,
    )


def gather_forward_dependency(target: Path) -> tuple[Finding, ...]:
    """Doctor's verdict on forward-dependency blindness across every station.

    Reads only durable artifacts -- each project's tracked ``epics*.md`` and
    ``sprint-status-ledger.yaml`` under ``target``. Imports no station package
    and no harness (AD-11/AD-13). Degrades rather than raising: an unreadable
    epics doc or ledger downgrades that station to ``unmeasured``, which is a
    WARN, never a silent pass.
    """
    projects = target / "_bmad-output" / "projects"
    findings: list[Finding] = []
    unmeasured: list[str] = []
    no_dispatch: list[tuple[str, int]] = []
    partial: list[tuple[str, int, int, list[str]]] = []
    measured = 0

    if not projects.is_dir():
        return (
            _finding(
                DoctorStatus.WARN,
                "coverage",
                f"cannot evaluate: {projects} is not a directory — no station "
                "epics docs to read, so forward-dependency coverage is unknown, "
                "not clean.",
                projects_dir=str(projects),
            ),
        )

    for project_dir in sorted(projects.glob("pyforge-*")):
        slug = project_dir.name
        try:
            epics_files = find_epics_files(project_dir)
        except OSError as exc:
            unmeasured.append(slug)
            findings.append(
                _finding(
                    DoctorStatus.WARN,
                    "unmeasured",
                    f"{slug}: planning-artifacts unreadable ({exc.__class__.__name__}"
                    f": {exc}) — coverage unknown, not asserted clean.",
                    station=slug,
                )
            )
            continue
        if not epics_files:
            continue

        try:
            ledger = ledger_statuses(project_dir / "planning-artifacts" / "sprint-status-ledger.yaml")
            station_stories: list[tuple[int, str, str, str]] = []
            for ef in epics_files:
                station_stories.extend(story_deps(ef))
        except OSError as exc:
            unmeasured.append(slug)
            findings.append(
                _finding(
                    DoctorStatus.WARN,
                    "unmeasured",
                    f"{slug}: epics doc or ledger unreadable "
                    f"({exc.__class__.__name__}: {exc}) — coverage unknown, not "
                    "asserted clean.",
                    station=slug,
                )
            )
            continue

        # NO-DISPATCH is checked FIRST because it dominates every other class: a
        # station with nothing actionable cannot suffer this defect at all,
        # whatever grammar its Deps fields use. It is a measured claim about the
        # LEDGER -- never a claim that the Deps fields parsed clean. A ledger we
        # could not read stays UNMEASURED: no data is not the same as no risk.
        if ledger and not any(st in ACTIONABLE_STATUSES for st in ledger.values()):
            no_dispatch.append((slug, len(ledger)))
            continue

        declared = [d for _, _, _, d in station_stories if d]
        if not declared:
            unmeasured.append(slug)
            continue

        # Coverage is keyed on READABLE references, not on the presence of Deps
        # TEXT. The old gate (`any(deps)`) reported mason measured-and-clean with
        # 0 of 30 declarations parseable -- a false green in this check's own
        # bookkeeping, for months.
        prose = [d for d in declared if not DEP_RE.findall(d) and not NO_DEP_RE.match(d)]
        if prose:
            partial.append((slug, len(declared) - len(prose), len(declared), prose[:2]))
        else:
            measured += 1

        for epic, num, title, deps in station_stories:
            # Only SAME-station references can be forward: "a later epic" is an
            # ordering claim within one station's epics doc. A cross-station ref
            # is a real dependency the per-station picker also cannot see, but
            # that is a different defect and an explicit SPEC non-goal (no
            # general dependency graph) -- it must not be judged here.
            same_station = [(m.group("epic"), m.group("num")) for m in DEP_RE.finditer(deps) if not m.group("station")]
            # A forward reference only blocks while it is UNSATISFIED. Ordering
            # alone used to be the whole test, which meant a story could never
            # leave `blocked` once its later-epic dep actually landed: the
            # ledger had to keep asserting "blocked" about work that was ready,
            # or this check went red. Found live 2026-08-08 when doctor's S-6.1
            # completed and unblocked S-5.2 -- the first time in the fleet a
            # forward dep was satisfied rather than merely declared.
            forward = sorted({de for de, dn in same_station if int(de) > epic and not _dep_satisfied(ledger, de, dn)})
            if not forward:
                continue
            key = f"{epic}-{num}"
            status = ledger.get(key)
            if status in ACTIONABLE_STATUSES or status is None:
                findings.append(
                    _finding(
                        DoctorStatus.FAIL,
                        "forward-dep",
                        f"{slug}/{key} ({title[:50]!r}): deps={deps!r} names a "
                        f"later epic ({', '.join(forward)}), but ledger status is "
                        f"{status or 'MISSING FROM LEDGER'!r} (actionable). A plain "
                        "`bmad-loop run` would dispatch it prematurely. Set it to "
                        "`blocked` in the loop-home's live Tier-3 feed, then "
                        "`python3 scripts/promote_sprint_status.py`.",
                        station=slug,
                        story=key,
                        deps=deps,
                        forward_epics=forward,
                        ledger_status=status or "MISSING FROM LEDGER",
                    )
                )

    for slug, readable, total, examples in partial:
        findings.append(
            _finding(
                DoctorStatus.WARN,
                "partial",
                f"{slug}: only {readable} of {total} dependency declaration(s) are "
                "machine-readable — the rest state a real dependency in a grammar "
                "DEP_RE cannot parse, so they are NOT checked for forward-epic "
                "references. Rewrite as `S-<epic>.<num>` / `S-<epic>.*` / "
                "`<station>:S-<epic>.<num>`; prose may follow as trailing context.",
                station=slug,
                readable=readable,
                total=total,
                examples=[ex[:88] for ex in examples],
            )
        )

    # NO-DISPATCH is a measured fact about the ledger, not a problem -- but it
    # must still be REPORTED, or a station that cannot suffer this defect
    # becomes indistinguishable from one that was never looked at. The origin
    # script printed these as its own `○` class; dropping them here would lose
    # exactly the distinction the four-class breakdown exists to preserve.
    for slug, total in no_dispatch:
        findings.append(
            _finding(
                DoctorStatus.OK,
                "no-dispatch",
                f"{slug}: no structured **Deps:** field, but the tracked ledger "
                f"shows 0 of {total} stories actionable — nothing can be "
                "dispatched early. NOT a parse-cleanliness claim.",
                station=slug,
                ledger_stories=total,
            )
        )

    for slug in unmeasured:
        findings.append(
            _finding(
                DoctorStatus.WARN,
                "unmeasured",
                f"{slug}: epics doc has no structured **Deps:** field and work "
                "remains (or its ledger is unreadable) — coverage unknown, not "
                "asserted clean.",
                station=slug,
            )
        )

    # The coverage line is ALWAYS emitted, never only on a clean run. It is the
    # summary a caller reads to know how much of the fleet was actually
    # verified, and it is precisely when there ARE findings that "how much did
    # you measure?" matters most -- a red result over 2 measured stations means
    # something different from a red result over 8.
    findings.append(
        _finding(
            DoctorStatus.OK,
            "coverage",
            f"forward-dependency coverage: {measured} measured, {len(partial)} "
            f"partial, {len(no_dispatch)} no-dispatch, {len(unmeasured)} "
            "unmeasured — 'no-dispatch' and 'unmeasured' assert nothing about "
            "Deps parse-cleanliness.",
            measured=measured,
            partial=len(partial),
            no_dispatch=len(no_dispatch),
            unmeasured=len(unmeasured),
        )
    )
    return tuple(findings)
