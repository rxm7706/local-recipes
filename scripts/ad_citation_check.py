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
     like a gap in an otherwise contiguous 1..17.

Hence `_AD_DEF` anchors on the heading (or bold run) and the number and assumes
NOTHING about what follows. Verify the detector, not just the artifact.
"""

from __future__ import annotations

import collections
import pathlib
import re
import sys

DETECTOR = {"scope": "repo"}

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROJECTS = ROOT / "_bmad-output" / "projects"

#: An AD DEFINITION: a markdown heading (any depth) or a bold run, then the id.
#: Optionally inside a list item. Deliberately assumes nothing about the
#: separator or trailing text -- see the five bugs in the module docstring.
_AD_DEF = re.compile(r"^(?:[-*+]\s+)?(?:#{1,6}\s*|\*\*)AD-(\d+)\b", re.M)

#: An AD CITATION, unprefixed. The lookbehind rejects `fnd:AD-1` / `pap:AD-1`
#: and hyphenated ids, so a prefixed (already unambiguous) citation is not
#: counted as bare.
_AD_CITE = re.compile(r"(?<![\w:-])AD-(\d+)")

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


def _defined_ads(project: pathlib.Path) -> dict[pathlib.Path, set[int]]:
    """Per-spine AD ids defined in ``project``."""
    return {sp: {int(n) for n in _AD_DEF.findall(_read(sp))} for sp in _spines(project)}


def main() -> int:
    if not PROJECTS.is_dir():
        print(f"[ad-citation] cannot run: {PROJECTS} is not a directory", file=sys.stderr)
        return 2

    projects = sorted(p for p in PROJECTS.glob("pyforge-*") if p.is_dir())
    if not projects:
        print("[ad-citation] cannot run: no pyforge-* projects found", file=sys.stderr)
        return 2

    defined: dict[str, set[int]] = {}
    per_spine: dict[str, dict[pathlib.Path, set[int]]] = {}
    for proj in projects:
        slug = proj.name
        per_spine[slug] = _defined_ads(proj)
        defined[slug] = set().union(*per_spine[slug].values()) if per_spine[slug] else set()

    unresolvable: list[str] = []
    cross_project = 0
    ambiguous: list[str] = []
    misnamed: list[str] = []
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

    # --- FAIL: a citation that names no AD anywhere in the fleet ------------
    for proj in projects:
        slug = proj.name
        for path in sorted(proj.rglob("*.md")):
            if "/architecture/" in str(path):
                continue  # a spine citing its own ids is definitional, not a citation
            for raw in _AD_CITE.findall(_read(path)):
                n = int(raw)
                if n in defined[slug]:
                    continue
                if any(n in ads for ads in defined.values()):
                    cross_project += 1
                    continue
                unresolvable.append(f"{slug}: {path.relative_to(ROOT)} cites AD-{n}, defined nowhere in the fleet")

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

    for line in unresolvable:
        print(f"[ad-citation] broken: {line}")
    for line in misnamed:
        print(f"[ad-citation] misnamed-spine: {line}")
    for line in malformed:
        print(f"[ad-citation] malformed-heading: {line}")
    for line in ambiguous:
        print(f"[ad-citation] ambiguous: {line}")

    total_defined = sum(len(v) for v in defined.values())
    print(
        f"[ad-citation] {total_defined} AD(s) defined across "
        f"{sum(len(v) for v in per_spine.values())} spine(s) in {len(projects)} project(s); "
        f"{cross_project} cross-project citation(s) resolved"
    )

    if unresolvable or misnamed or malformed:
        return 1
    if ambiguous:
        # Ambiguity is real but is a consolidation task, not a broken link --
        # reported every run, never a red gate, matching how `warn` findings
        # behave elsewhere in the detector suite.
        print("[ad-citation] ok: every citation resolves; ambiguity above is advisory")
        return 0
    print("[ad-citation] ok: every AD citation resolves to exactly one spine")
    return 0


if __name__ == "__main__":
    sys.exit(main())
