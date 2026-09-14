#!/usr/bin/env python3
"""Detector: every architecture-decision citation resolves to exactly one spine.

The planning chain's premise is that the spec is the contract, so a citation
into that contract -- `AD-7`, and by extension the spines that define them --
has to name something real and name it unambiguously. This checks both halves,
fleet-wide, over every tracked planning artifact.

WHY THIS EXISTS (measured 2026-09-08, before any of it was fixed):

  * 11,198 bare `AD-n` citations across 935 files in eight projects.
  * ZERO of them are broken -- every one resolves to a defined AD somewhere in
    the fleet. The graph is healthy, and that is precisely why a bulk renumber
    is dangerous: it can only subtract correctness.
  * 172 resolve in a DIFFERENT project than the one citing them (doctor citing
    marshal's AD-22, and so on). Legitimate -- doctor judges marshal -- but
    written bare, so a reader cannot tell locally.
  * steward is the one project with more than one spine (eight), and their AD
    ranges overlap in 1..23, so a bare `AD-5` there is genuinely ambiguous
    between the station spine, Canopy, python-agent-platform and others. The
    spines say so themselves: spec-python-agent-platform's own spine warns
    "Unifying Strategy must not treat these as canopy AD-1..".

FIVE EXTRACTOR BUGS, RECORDED SO THE NEXT READER DOES NOT REPEAT THEM. Each
attempt at `_defined_ads` reported large phantom defects that were entirely
artifacts of an over-specific pattern:

  1. `#{2,4}` missed atlas's satellite ADs, written `##### AD-24` (five).
  2. Requiring an em-dash separator missed herald's `### AD-1: Title`.
  3. Requiring `AD-(\\d+)\\s*[sep]` missed herald's `### AD-11 (was AD-1):`.
  4. Treating warden's spine as malformed: it defines NO ADs at all, using
     named decisions (`### GAP A`) instead -- an absence, not a defect.
  5. Requiring the line to START with `#`/`**` missed python-agent-platform's
     `- **AD-16 — ...`, a definition inside a list item, which made AD-16 look
     like a gap in an otherwise contiguous 1..17. Admitting list items then
     over-matched bold PROSE (`- **AD-7/AD-8 scaled far past...**`), so the two
     forms are now split: a heading is a definition whatever follows the id; a
     bold run must carry the em dash to count as one.

Hence `_AD_DEF` anchors on the heading (or bold run) and the number and assumes
NOTHING about what follows. Verify the detector, not just the artifact.
"""

from __future__ import annotations

import collections
import datetime
import json
import pathlib
import re
import sys

DETECTOR = {"scope": "repo"}

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROJECTS = ROOT / "_bmad-output" / "projects"

#: Known-broken bare citations, recorded 2026-09-08 so the debt is visible and
#: BOUNDED without a false red. A ratchet, not an amnesty: anything new fails.
#:
#: These 151 are pre-existing imprecision, not damage -- a bare `AD-9` in warden
#: that means steward's suite spine. They resolve for a human who knows the
#: chain and for nobody else. Four attribution methods were measured against
#: labeled data before settling for a baseline: per-file keyword 47%, per-
#: citation context 45%, epic->chain 80% with systematic bias, and verbatim
#: title-run 100% precise but covering only 12 of the 151. The rest need
#: reading, so they are recorded rather than guessed at.
_BASELINE_PATH = ROOT / "scripts" / ".ad-citation-baseline.json"
_CAP_BASELINE_PATH = ROOT / "scripts" / ".cap-citation-baseline.json"


def _today() -> str:
    """The date a baseline is stamped with. Was two hard-coded literals
    ("2026-09-08" / "2026-09-10") until 2026-09-14, so every later re-stamp
    still claimed those dates (Story 43.1)."""
    return datetime.date.today().isoformat()

#: Citations to a THIRD-PARTY tool's own documented ADs. These can never
#: resolve against a spine in this fleet, because the tool that defines them
#: has none here -- so counting them as broken is wrong, and baselining them
#: leaves them sitting as debt that no work can ever clear.
#:
#: Deliberately keyed by (path substring, id): narrow enough that it cannot
#: absolve an unrelated citation of the same number elsewhere, and greppable
#: so the exemption is visible from the citing file. An entry must name the
#: owning tool and why the id is external -- an unexplained exemption is
#: indistinguishable from a silenced finding.
_EXTERNAL_AD_CITATIONS: dict[str, dict[int, str]] = {
    # `eval-quality` is a bmad-suite CLI wielded BY steward, not a station of
    # this fleet; its ADs are its own documented contract. AD-21 is its exit
    # code 3 ("failed pre-flight"); AD-33 is its `witness-matched` /
    # `clean-control-false-positive` oracle vocabulary. Both are cited here as
    # that tool's behaviour, never as a claim about a pyforge spine.
    "pyforge-steward/planning-artifacts/specs/spec-45-2-the-reviewer-is-measured-against-a-planted-defect": {
        21: "eval-quality CLI's documented exit code 3 (failed pre-flight)",
    },
    "pyforge-steward/implementation-artifacts/spec-45-2-the-reviewer-is-measured-against-a-planted-defect": {
        21: "eval-quality CLI's documented exit code 3 -- the Tier-3 twin of the spec above",
    },
    "pyforge-steward/planning-artifacts/specs/spec-bmad-eval-quality/.memlog.md": {
        33: "eval-quality CLI's own witness-matched / clean-control oracle states",
    },
    # Project-scoped on purpose. A bare "planning-artifacts/deferred-work-ledger.md"
    # was tried first and matched EVERY station's ledger, so atlas citing the same
    # number would have been silently absolved -- the too-broad-pattern defect,
    # caught by this module's own over-match test rather than in review.
    "pyforge-steward/planning-artifacts/deferred-work-ledger.md": {
        21: "eval-quality CLI's documented exit code 3, quoted in DW-FU-45-2-2",
    },
}


def _is_external_citation(rel_path: str, ad_id: int) -> bool:
    """Is this citation a third-party tool's own AD, not a fleet spine's?"""
    for fragment, ids in _EXTERNAL_AD_CITATIONS.items():
        if fragment in rel_path and ad_id in ids:
            return True
    return False

#: An AD DEFINITION: a markdown heading (any depth) or a bold run, then the id.
#: Optionally inside a list item. Deliberately assumes nothing about the
#: separator or trailing text -- see the five bugs in the module docstring.
_AD_DEF = re.compile(
    r"^(?:"
    r"#{1,6}\s*(?P<hp>[a-z][\w-]*:)?AD-(?P<h>\d+)\b"          # a heading IS a definition
    r"|"
    r"(?:[-*+]\s+)?\*\*(?P<bp>[a-z][\w-]*:)?AD-(?P<b>\d+)\s*[—–]"  # bold form needs the em dash
    r")",
    re.M,
)

#: An AD CITATION, unprefixed. The lookbehind rejects `fnd:AD-1` / `pap:AD-1`
#: and hyphenated ids, so a prefixed (already unambiguous) citation is not
#: counted as bare.
_AD_CITE = re.compile(r"(?<![\w:-])AD-(\d+)")

#: A CAP DEFINITION: same heading/bold split as AD; qualified `fnd:CAP-1` is a
#: separate namespace from bare `CAP-1` (mirrors the 2026-09-08 AD fold).
_CAP_DEF = re.compile(
    r"^(?:"
    r"#{1,6}\s*(?P<hp>[a-z][\w-]*:)?CAP-(?P<h>\d+)\b"
    r"|"
    r"(?:[-*+]\s+)?\*\*(?P<bp>[a-z][\w-]*:)?CAP-(?P<b>\d+)\b"
    r")",
    re.M,
)

#: An unprefixed CAP citation. The lookbehind rejects `suite:CAP-1` / `fnd:CAP-1`.
_CAP_CITE = re.compile(r"(?<![\w:-])CAP-(\d+)")

#: Spines live under `planning-artifacts/architecture/<run>/`, and -- when a
#: Spec adopts one as a companion -- beside that Spec. Both are conformant:
#: `spec-python-agent-platform/SPEC.md` declares
#: `companions: [ARCHITECTURE-SPINE.md]`, which is bmad-spec's own convention.
_SPINE_GLOBS = (
    "planning-artifacts/architecture/*/ARCHITECTURE-SPINE.md",
    "planning-artifacts/specs/*/ARCHITECTURE-SPINE.md",
)


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _spines(project: pathlib.Path) -> list[pathlib.Path]:
    out: list[pathlib.Path] = []
    for glob in _SPINE_GLOBS:
        out.extend(sorted(project.glob(glob)))
    return out


def _capabilities_block(text: str) -> tuple[int, int] | None:
    """Return (start, end) line indices for a SPEC's ``## Capabilities`` block."""
    lines = text.splitlines()
    start: int | None = None
    for i, line in enumerate(lines):
        if re.match(r"^## Capabilities\b", line):
            start = i
            continue
        if start is not None and re.match(r"^## ", line):
            return start, i
    if start is not None:
        return start, len(lines)
    return None


def _defined_caps(project: pathlib.Path) -> set[int]:
    """Bare CAP ids defined in ``project`` (spines + SPEC capabilities blocks)."""
    ids: set[int] = set()
    for sp in _spines(project):
        for m in _CAP_DEF.finditer(_read(sp)):
            if m.group("hp") or m.group("bp"):
                continue
            ids.add(int(m.group("h") or m.group("b")))
    for spec in project.glob("planning-artifacts/specs/*/SPEC.md"):
        text = _read(spec)
        block = _capabilities_block(text)
        if block is None:
            continue
        start, end = block
        chunk = "\n".join(text.splitlines()[start:end])
        for m in _CAP_DEF.finditer(chunk):
            if m.group("hp") or m.group("bp"):
                continue
            ids.add(int(m.group("h") or m.group("b")))
    return ids


def _defined_ads(project: pathlib.Path) -> dict[pathlib.Path, set[int]]:
    """Per-spine BARE AD ids defined in ``project``.

    A qualified definition (`#### canopy:AD-7`) deliberately does NOT count: it
    lives in its own namespace and cannot collide with a bare `AD-7`. That is
    the whole mechanism behind steward's 2026-09-08 fold -- six satellite spines
    became `## Satellite:` sections whose ids stay qualified, so the bare
    namespace holds only the station's own AD-1..9 and a bare citation is
    unambiguous again, with not one reference rewritten.
    """
    out: dict[pathlib.Path, set[int]] = {}
    for sp in _spines(project):
        ids: set[int] = set()
        for m in _AD_DEF.finditer(_read(sp)):
            if m.group("hp") or m.group("bp"):
                continue  # qualified -- separate namespace
            ids.add(int(m.group("h") or m.group("b")))
        out[sp] = ids
    return out


def main() -> int:
    if not PROJECTS.is_dir():
        print(f"[ad-citation] cannot run: {PROJECTS} is not a directory", file=sys.stderr)
        return 2

    projects = sorted(p for p in PROJECTS.glob("pyforge-*") if p.is_dir())
    if not projects:
        print("[ad-citation] cannot run: no pyforge-* projects found", file=sys.stderr)
        return 2

    defined: dict[str, set[int]] = {}
    defined_caps: dict[str, set[int]] = {}
    per_spine: dict[str, dict[pathlib.Path, set[int]]] = {}
    for proj in projects:
        slug = proj.name
        per_spine[slug] = _defined_ads(proj)
        defined[slug] = set().union(*per_spine[slug].values()) if per_spine[slug] else set()
        defined_caps[slug] = _defined_caps(proj)

    unresolvable: list[str] = []
    cap_unresolvable: list[str] = []
    cross_project = 0
    ambiguous: list[str] = []
    misnamed: list[str] = []
    external = 0
    malformed: list[str] = []

    # --- FAIL: a spine folder that does not name its own project ------------
    #
    # THE ROOT CAUSE, not a symptom. `bmad-architecture`'s run_folder_pattern
    # is `architecture-{project_name}-{date}` and upstream is explicit that the
    # default "fits the common case (one spine per project, at the altitude
    # above epics)". Every one of steward's extra spines exists because that
    # skill was run with `project_name` overridden to a CHAIN slug. Nothing
    # stopped it, which is how one project reached eight spines while the other
    # seven held at one. Checking the folder name is what stops the ninth.
    #
    # A spine beside a SPEC.md that declares it in `companions:` is exempt --
    # that is bmad-spec's own adopted-companion convention, not drift.
    for proj in projects:
        for spine in _spines(proj):
            if spine.parent.parent.name != "architecture":
                spec = spine.parent / "SPEC.md"
                if spec.is_file() and "ARCHITECTURE-SPINE.md" in _read(spec):
                    continue  # declared Spec companion
            if not spine.parent.name.startswith(f"architecture-{proj.name}-"):
                misnamed.append(
                    f"{proj.name}: {spine.parent.name} does not match "
                    f"architecture-{proj.name}-<date> -- a spine folder names its "
                    f"PROJECT, never a chain"
                )

    # --- FAIL: an AD definition not written in the canonical form -----------
    #
    # Normalizing the form is safe (it changes no id, so no citation can
    # break), but without a check it silently drifts back. Four separate
    # heading shapes existed before 2026-09-08.
    for proj in projects:
        for spine in _spines(proj):
            for m in re.finditer(r"^(#{1,6}\s*AD-\d+)(.{0,12})", _read(spine), re.M):
                if not re.match(r"\s*—", m.group(2)):
                    malformed.append(
                        f"{proj.name}: {spine.parent.name} has "
                        f"`{(m.group(1) + m.group(2)).strip()}` -- AD headings read `AD-<n> — <Title>`"
                    )

    # --- FAIL: a bare citation that does not resolve IN ITS OWN PROJECT -----
    #
    # Resolving fleet-wide was a FALSE GREEN and it hid a real regression. When
    # steward's six satellite spines were folded and their ids qualified, 677
    # bare citations in steward stopped resolving locally -- and this check
    # still passed them, because AD-10..AD-23 happen to exist in atlas and
    # marshal. A number matching in an unrelated project is a coincidence, not
    # a reference.
    #
    # So the rule is: a BARE `AD-n` must resolve inside its own project. A
    # citation that means another project's decision has to say so
    # (`suite:AD-9`), which is exactly what the qualified form is for.
    for proj in projects:
        slug = proj.name
        for path in sorted(proj.rglob("*.md")):
            if "/architecture/" in str(path):
                continue  # a spine citing its own ids is definitional, not a citation
            for raw in _AD_CITE.findall(_read(path)):
                n = int(raw)
                if n in defined[slug]:
                    continue
                if _is_external_citation(str(path.relative_to(ROOT)), n):
                    external += 1
                    continue
                unresolvable.append(
                    f"{slug}: {path.relative_to(ROOT)} cites bare AD-{n}, which this "
                    f"project does not define -- qualify it (`<spine>:AD-{n}`) or fix the id"
                )

    # --- FAIL: a bare CAP citation that does not resolve IN ITS OWN PROJECT -
    for proj in projects:
        slug = proj.name
        for path in sorted(proj.rglob("*.md")):
            if "/architecture/" in str(path):
                continue
            text = _read(path)
            skip_lines: set[int] = set()
            if path.name == "SPEC.md" and (block := _capabilities_block(text)):
                start, end = block
                skip_lines.update(range(start, end))
            for line_no, line in enumerate(text.splitlines()):
                if line_no in skip_lines:
                    continue
                for raw in _CAP_CITE.findall(line):
                    n = int(raw)
                    if n in defined_caps[slug]:
                        continue
                    cap_unresolvable.append(
                        f"{slug}: {path.relative_to(ROOT)} cites bare CAP-{n}, which this "
                        f"project does not define -- qualify it (`<spine>:CAP-{n}`) or fix the id"
                    )

    # --- WARN: one project, several spines, overlapping id ranges -----------
    for slug, spine_map in per_spine.items():
        if len(spine_map) < 2:
            continue
        seen: dict[int, list[str]] = collections.defaultdict(list)
        for sp, ads in spine_map.items():
            for n in ads:
                seen[n].append(sp.parent.name)
        overlapped = {n: owners for n, owners in seen.items() if len(owners) > 1}
        if overlapped:
            lo, hi = min(overlapped), max(overlapped)
            ambiguous.append(
                f"{slug}: {len(spine_map)} spines share AD ids {lo}..{hi} "
                f"({len(overlapped)} colliding ids) -- a bare `AD-n` here cannot be "
                f"resolved without reading the citing file's subject"
            )

    for line in unresolvable[:15]:
        print(f"[ad-citation] broken: {line}")
    if len(unresolvable) > 15:
        print(f"[ad-citation] broken: ... and {len(unresolvable) - 15} more")
    for line in cap_unresolvable[:15]:
        print(f"[cap-citation] broken: {line}")
    if len(cap_unresolvable) > 15:
        print(f"[cap-citation] broken: ... and {len(cap_unresolvable) - 15} more")
    for line in misnamed:
        print(f"[ad-citation] misnamed-spine: {line}")
    for line in malformed:
        print(f"[ad-citation] malformed-heading: {line}")
    for line in ambiguous:
        print(f"[ad-citation] ambiguous: {line}")

    total_defined = sum(len(v) for v in defined.values())
    total_caps = sum(len(v) for v in defined_caps.values())
    print(
        f"[ad-citation] {total_defined} AD(s) defined across "
        f"{sum(len(v) for v in per_spine.values())} spine(s) in {len(projects)} project(s); "
        f"{cross_project} qualified cross-project citation(s); "
        f"{external} external-tool citation(s)"
    )
    print(
        f"[cap-citation] {total_caps} bare CAP(s) defined across "
        f"{len(projects)} project(s); {len(set(cap_unresolvable))} distinct broken citation(s)"
    )

    # One ratchet over every FAIL class. `unresolvable` is deduplicated first:
    # the same file citing the same id five times is ONE issue to fix, and
    # counting occurrences would make the baseline shrink or grow on edits that
    # change nothing.
    findings = sorted(set(unresolvable) | set(misnamed) | set(malformed))
    cap_findings = sorted(set(cap_unresolvable))

    if "--write-cap-baseline" in sys.argv:
        _CAP_BASELINE_PATH.write_text(
            json.dumps({"recorded": _today(), "known": cap_findings}, indent=1) + "\n",
            encoding="utf-8",
        )
        print(f"[cap-citation] baseline written: {len(cap_findings)} known issue(s)")
        return 0

    if "--write-baseline" in sys.argv:
        _BASELINE_PATH.write_text(
            json.dumps({"recorded": _today(), "known": findings}, indent=1) + "\n",
            encoding="utf-8",
        )
        print(f"[ad-citation] baseline written: {len(findings)} known issue(s)")
        return 0

    baseline: set[str] = set()
    if _BASELINE_PATH.is_file():
        try:
            baseline = set(json.loads(_BASELINE_PATH.read_text(encoding="utf-8")).get("known", []))
        except (OSError, ValueError):
            print(f"[ad-citation] cannot run: {_BASELINE_PATH.name} is unreadable", file=sys.stderr)
            return 2

    cap_baseline: set[str] = set()
    if _CAP_BASELINE_PATH.is_file():
        try:
            cap_baseline = set(
                json.loads(_CAP_BASELINE_PATH.read_text(encoding="utf-8")).get("known", [])
            )
        except (OSError, ValueError):
            print(
                f"[cap-citation] cannot run: {_CAP_BASELINE_PATH.name} is unreadable",
                file=sys.stderr,
            )
            return 2

    new = [f for f in findings if f not in baseline]
    cap_new = [f for f in cap_findings if f not in cap_baseline]
    healed = sorted(baseline - set(findings))
    cap_healed = sorted(cap_baseline - set(cap_findings))
    if baseline:
        print(
            f"[ad-citation] {len(findings)} distinct issue(s) "
            f"({len(unresolvable)} citation occurrence(s)); {len(baseline)} baselined"
            + (f", {len(healed)} since fixed" if healed else "")
        )
    if cap_baseline:
        print(
            f"[cap-citation] {len(cap_findings)} distinct issue(s) "
            f"({len(cap_unresolvable)} citation occurrence(s)); {len(cap_baseline)} baselined"
            + (f", {len(cap_healed)} since fixed" if cap_healed else "")
        )
    exit_code = 0
    # Every NEW row is printed -- the NEW set IS the actionable set, and a
    # detector that exits 1 must show what it exits on. Until 2026-09-14 both
    # loops sliced `[:10]` beneath a headline carrying the full count, so a red
    # with 61 NEW findings was read from the printed rows and recorded as 14
    # (Story 43.1 / DW-AD-CITATION-2026-09-14-2): the "head truncates findings
    # out of view" class CLAUDE.md warns about for pipes, built into the
    # detector. The baselined set stays a count -- it is known debt, not the
    # action list.
    if new:
        print(f"[ad-citation] {len(new)} NEW issue(s), not in the baseline:")
        for line in new:
            print(f"[ad-citation]   NEW: {line}")
        exit_code = 1
    if cap_new:
        print(f"[cap-citation] {len(cap_new)} NEW issue(s), not in the baseline:")
        for line in cap_new:
            print(f"[cap-citation]   NEW: {line}")
        exit_code = 1
    if exit_code:
        return exit_code
    if findings:
        # Known debt: reported every run, bounded by the baseline, never a
        # false green. Re-stamp with --write-baseline only when it SHRINKS.
        print("[ad-citation] ok: no new issues; the baselined set is unchanged or smaller")
    elif ambiguous:
        print("[ad-citation] ok: every citation resolves; ambiguity above is advisory")
    else:
        print("[ad-citation] ok: every AD citation resolves to exactly one spine")
    if cap_findings:
        print("[cap-citation] ok: no new issues; the baselined set is unchanged or smaller")
    else:
        print("[cap-citation] ok: every CAP citation resolves in its project")
    return 0


if __name__ == "__main__":
    sys.exit(main())
