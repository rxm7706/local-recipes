"""The fleet-hygiene gather filter -- production evidence for Story 9.1's
five ``hygiene_definitions`` predicates (Story 9.2, CAP-8).

**Why this module exists.** Story 9.1 landed five pure classification
predicates (``is_dead_test_scaffolding``, ``is_hollow_sprint_status``,
``is_orphan_file``, ``is_readme_placeholder``, ``is_stale_dream_status``) with
zero production callers -- nothing gathered evidence for them across the
fleet, so CAP-8's own promise (reproduce warden's five finding classes,
zero false positives against the already-clean ``pyforge-warden``, surface
at least one true positive on a never-audited station) was unproven. This
module is that caller: it walks every station under ``_bmad-output/projects/``
(derived via ``iterdir()``, never hand-listed), gathers each class's evidence
via plain filesystem/YAML reads plus one ``git grep`` call for the orphan-file
class's inbound-reference check, and hands the evidence to
``hygiene_definitions``'s own predicates -- classification is EXCLUSIVELY
theirs, never reimplemented here.

**Why ``subject_station="fleet"``, not one station.** This sweep's real
subject is every station's own planning artifacts at once (doctor included,
self-judging alongside the rest), so naming any single station in
``sources/__init__.py``'s ``REGISTRY`` would misrepresent what it judges --
see that module's own row comment and the story spec's Design Notes for the
full rationale (``CHAIN_COMPLETENESS``'s ``subject_station="marshal"``
precedent, which also walks all 8 projects, does not apply: what THAT source
judges really is Marshal-owned, but no single station owns "every station's
own hygiene"). Every ``Finding.evidence["station"]`` still carries the real
specific station a given instance was found in.

**Degrades, never crashes** -- the house rule for every Doctor source.
Isolation runs at two granularities, matching the two failure shapes the
story spec's own I/O matrix names:

* PER-STATION (mirrors ``sources/board.py``'s own per-project isolation): one
  station's unreadable/undecodable file (a bad README, a malformed ledger, an
  unparseable Dream) degrades the WHOLE station to one WARN ``Finding``,
  never discarding the other 7 stations' already-computed findings. Findings
  already appended for THAT station before the failure are kept too, because
  each per-station check appends directly into the caller's shared list
  rather than building a local one and returning it at the end -- the same
  reason ``board.py``'s own per-project helper does the same.
* PER-CANDIDATE, orphan-file only: a ``git grep`` call that raises
  ``CliBridgeError`` (exit >=2, or git itself unavailable) degrades only THAT
  candidate to one WARN, leaving every other candidate in the same station,
  and every other station, unaffected -- the story spec's own I/O matrix
  names this as a narrower isolation than the per-station default.

**No ``doctor check``/``monitor`` CLI or dispatch wiring in this story**
(mirrors ``Source.ADOPTION``'s own "registered, not yet dispatched"
precedent, named explicitly as this story's own Never clause) -- Story 9.1's
own Never clause named this plausibly Story 9.2's job, but no acceptance
criterion here requires it.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath

import yaml

from ..cli_bridge import CliBridgeError, run_git
from ..hygiene_definitions import (
    HygieneFindingKind,
    is_dead_test_scaffolding,
    is_hollow_sprint_status,
    is_orphan_file,
    is_readme_placeholder,
    is_stale_dream_status,
)
from ..models import DoctorStatus, Finding, Source

__all__ = ("gather",)

#: The three marker shapes that flag a station's ``tests/`` tree as a
#: dead-test-scaffolding CANDIDATE (Boundaries + I/O matrix: "no marker dir ->
#: no candidate considered, not even a clean pass"). ``pytest.ini``/
#: ``playwright.config.ts`` are checked at the station root even without a
#: ``tests/`` directory existing alongside them -- a test-runner config with
#: no real test tree at all is itself the shape this class names.
_TEST_MARKER_FILES = ("pytest.ini", "playwright.config.ts")

#: The one non-ledger Tier-3 filename this class judges -- deliberately NOT
#: ``sprint-status-ledger.yaml`` (the tracked, per-story twin every station
#: carries); see the module docstring for the shape distinction.
_SPRINT_STATUS_FILENAME = "sprint-status.yaml"

_LEDGER_RELPATH = "planning-artifacts/sprint-status-ledger.yaml"


def gather(target: Path) -> tuple[Finding, ...]:
    """Walk every station under ``target/_bmad-output/projects/`` and judge
    each of Story 9.1's five hygiene classes -- the library form CAP-8's
    acceptance criteria exercise directly.

    Aggregation mirrors ``sources/ledger.py::gather``: zero findings across
    the whole sweep returns exactly one ``Finding(status=OK)``; any positives
    return one ``Finding`` per instance only, no baseline-OK noise for a
    clean station x class pair.
    """
    projects_dir = target / "_bmad-output" / "projects"
    findings: list[Finding] = []
    stations_evaluated = 0
    if projects_dir.is_dir():
        for project_dir in sorted(projects_dir.iterdir()):
            if not (project_dir / "planning-artifacts").is_dir():
                continue
            stations_evaluated += 1
            station = project_dir.name.removeprefix("pyforge-")
            try:
                _evaluate_station(target, project_dir, findings)
            except Exception as exc:  # noqa: BLE001 -- one station's
                # unreadable/undecodable file must not discard the other
                # stations' already-computed findings (mirrors
                # board.py's own per-project isolation).
                findings.append(
                    Finding(
                        source=Source.BMAD_OUTPUT_HYGIENE,
                        check="station-unevaluable",
                        status=DoctorStatus.WARN,
                        message=(f"{station}: could not be evaluated here — {exc.__class__.__name__}: {exc}"),
                        evidence={"station": station},
                    )
                )

    if not findings:
        return (
            Finding(
                source=Source.BMAD_OUTPUT_HYGIENE,
                check="bmad-output-hygiene",
                status=DoctorStatus.OK,
                message=(
                    "no dead test scaffolding, hollow sprint status, orphan "
                    "file, README placeholder, or stale Dream status found "
                    "across the fleet's own planning artifacts"
                ),
                evidence={"stations": stations_evaluated},
            ),
        )
    return tuple(findings)


def _evaluate_station(target: Path, project_dir: Path, findings: list[Finding]) -> None:
    """Append one station's hygiene findings to the CALLER's ``findings``
    list -- appended directly, not built locally and returned, so a raise
    part-way through does not discard the findings this station has already
    produced (mirrors ``board.py``'s own per-project helper)."""
    station = project_dir.name.removeprefix("pyforge-")

    _check_dead_test_scaffolding(project_dir, station, findings)
    _check_hollow_sprint_status(project_dir, station, findings)
    _check_readme_placeholder(project_dir, station, findings)
    _check_stale_dream_status(target, project_dir, station, findings)
    _check_orphan_files(target, project_dir, station, findings)


def _check_dead_test_scaffolding(project_dir: Path, station: str, findings: list[Finding]) -> None:
    tests_dir = project_dir / "tests"
    # Computed once and reused for both the has-a-candidate check and the
    # marker-only evidence path below -- avoids re-scanning the filesystem a
    # second time and the `next()`-on-a-possibly-empty-iterator risk that
    # re-deriving it later would carry.
    matched_markers = [name for name in _TEST_MARKER_FILES if (project_dir / name).is_file()]
    if not tests_dir.is_dir() and not matched_markers:
        return
    if tests_dir.is_dir():
        relpaths = [str(path.relative_to(tests_dir)) for path in sorted(tests_dir.rglob("*")) if path.is_file()]
        evidence_path = "tests"
        reason = "tests/ scaffolding holds no real test_*.py file"
    else:
        relpaths = []
        evidence_path = matched_markers[0]
        reason = f"{evidence_path} exists with no real tests/ tree behind it"
    if not is_dead_test_scaffolding(relpaths):
        return
    findings.append(
        Finding(
            source=Source.BMAD_OUTPUT_HYGIENE,
            check=HygieneFindingKind.DEAD_TEST_SCAFFOLDING.value,
            status=DoctorStatus.WARN,
            message=f"{station}: {reason}",
            evidence={
                "station": station,
                "file_count": len(relpaths),
                "path": evidence_path,
            },
        )
    )


def _check_hollow_sprint_status(project_dir: Path, station: str, findings: list[Finding]) -> None:
    sprint_status = project_dir / "planning-artifacts" / _SPRINT_STATUS_FILENAME
    if not sprint_status.is_file():
        return
    parsed = yaml.safe_load(sprint_status.read_text(encoding="utf-8"))
    if not is_hollow_sprint_status(parsed):
        return
    findings.append(
        Finding(
            source=Source.BMAD_OUTPUT_HYGIENE,
            check=HygieneFindingKind.HOLLOW_SPRINT_STATUS.value,
            status=DoctorStatus.WARN,
            message=(f"{station}: {_SPRINT_STATUS_FILENAME} declares zero epics, zero stories, and 0% completion"),
            evidence={
                "station": station,
                "path": f"planning-artifacts/{_SPRINT_STATUS_FILENAME}",
            },
        )
    )


def _check_readme_placeholder(project_dir: Path, station: str, findings: list[Finding]) -> None:
    readme = project_dir / "README.md"
    if not readme.is_file():
        return
    content = readme.read_text(encoding="utf-8")
    if not is_readme_placeholder(content):
        return
    findings.append(
        Finding(
            source=Source.BMAD_OUTPUT_HYGIENE,
            check=HygieneFindingKind.README_PLACEHOLDER.value,
            status=DoctorStatus.WARN,
            message=f"{station}: README.md still carries the unfilled template stub",
            evidence={"station": station, "path": "README.md"},
        )
    )


def _dream_frontmatter_status(dream_path: Path) -> str | None:
    """The ``status:`` value from a Dream's ``---``-fenced frontmatter, or
    ``None`` when absent/unparseable.

    A small, LOCAL frontmatter reader (line-anchored ``---`` fences,
    ``yaml.safe_load`` the block between them) -- by this package's own
    convention, each ``sources/*.py`` module writes its own rather than
    importing a sibling module's private helper (e.g.
    ``board.py::_frontmatter``). The fence lines must be EXACTLY ``---``
    (stripped) on their own line -- a blind ``text.split("---", 2)`` would
    mis-split on a literal ``---`` substring inside an earlier field's own
    value (e.g. a ``notes:`` line quoting em-dash-style prose), silently
    truncating before the real closing fence and losing ``status`` with no
    error. Reading the file is NOT guarded here -- an unreadable/undecodable
    Dream propagates to ``gather``'s own per-station catch, same as every
    other file this module reads -- but a MALFORMED yaml block degrades to
    ``None`` (skip this candidate) rather than crashing the whole station,
    since a Dream's frontmatter being unparseable is not evidence about that
    station's real completion state.
    """
    lines = dream_path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    closing = next(
        (index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"),
        None,
    )
    if closing is None:
        return None
    try:
        data = yaml.safe_load("\n".join(lines[1:closing]))
    except yaml.YAMLError:
        return None
    if not isinstance(data, dict):
        return None
    status = data.get("status")
    return status if isinstance(status, str) else None


def _ledger_all_done(project_dir: Path) -> bool:
    """``True`` iff the station's tracked ``sprint-status-ledger.yaml``
    exists, carries at least one ``development_status`` entry, and every
    value in that mapping is exactly ``"done"``.

    An ABSENT or EMPTY ``development_status`` returns ``False``, not a
    vacuous ``True`` -- a station with no recorded stories yet has not
    demonstrated "all done," so it must never read as stale alongside a
    Dream still at ``status: specified``.
    """
    ledger_path = project_dir / _LEDGER_RELPATH
    if not ledger_path.is_file():
        return False
    data = yaml.safe_load(ledger_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return False
    statuses = data.get("development_status")
    if not isinstance(statuses, dict) or not statuses:
        return False
    return all(value == "done" for value in statuses.values())


def _check_stale_dream_status(target: Path, project_dir: Path, station: str, findings: list[Finding]) -> None:
    dream_path = target / "docs" / "dreams" / f"{project_dir.name}.md"
    if not dream_path.is_file():
        return
    dream_status = _dream_frontmatter_status(dream_path)
    if dream_status is None:
        return
    all_done = _ledger_all_done(project_dir)
    if not is_stale_dream_status(dream_status, all_done):
        return
    findings.append(
        Finding(
            source=Source.BMAD_OUTPUT_HYGIENE,
            check=HygieneFindingKind.STALE_DREAM_STATUS.value,
            status=DoctorStatus.WARN,
            message=(f"{station}: Dream status is still 'specified' while every tracked story is done"),
            evidence={
                "station": station,
                "path": f"docs/dreams/{project_dir.name}.md",
            },
        )
    )


def _orphan_file_candidates(project_dir: Path) -> list[Path]:
    """Every candidate file at exactly the two locations the Boundaries
    name: direct files at the project root (never recursing into a sibling
    dir like atlas's ``spec-archive/``), and every file recursively under
    ``planning-artifacts/`` -- excludes the gitignored
    ``implementation-artifacts/`` outright by never globbing it."""
    candidates = [path for path in sorted(project_dir.iterdir()) if path.is_file()]
    planning_artifacts = project_dir / "planning-artifacts"
    if planning_artifacts.is_dir():
        candidates.extend(path for path in sorted(planning_artifacts.rglob("*")) if path.is_file())
    return candidates


def _has_inbound_references(target: Path, repo_relpath: str) -> bool:
    """``True`` iff some OTHER tracked file in the repo contains the
    candidate's basename.

    Design Notes' exact protocol: search the candidate's basename (not the
    full relpath) via ``git grep -l --fixed-strings -e <basename>`` from the
    repo root, then drop the candidate's own repo-relative path from the
    match list before deciding -- a file's own content mentioning its own
    filename must not count as an inbound reference.

    ``ok_exit_codes={0, 1}`` tolerates ``git grep``'s documented exit 1
    ("no match") as a clean empty result rather than a raised error; exit
    >=2 (or git itself unavailable) still raises ``CliBridgeError``, which
    THIS function does not catch -- the caller degrades that one candidate
    to a WARN, per-candidate, not per-station.
    """
    basename = PurePosixPath(repo_relpath).name
    output = run_git(
        target,
        ["grep", "-l", "--fixed-strings", "-e", basename],
        ok_exit_codes=frozenset({0, 1}),
    )
    matches = [line for line in output.splitlines() if line.strip()]
    others = [match for match in matches if match != repo_relpath]
    return bool(others)


def _check_orphan_files(target: Path, project_dir: Path, station: str, findings: list[Finding]) -> None:
    for candidate in _orphan_file_candidates(project_dir):
        relpath = str(candidate.relative_to(project_dir))
        # Cheap pre-filter (Never clause): a conventional name/directory is
        # never orphaned regardless of references, so `has_inbound_
        # references=False`'s `if has_inbound_references: return False`
        # branch never fires here -- this correctly asks "is this candidate
        # non-conventional at all," without re-deriving hygiene_definitions'
        # own private constant sets, and without a `git grep` call for the
        # common case (a file under `specs/`, `prds/`, etc.).
        if not is_orphan_file(relpath, has_inbound_references=False):
            continue
        repo_relpath = str(candidate.relative_to(target))
        try:
            has_refs = _has_inbound_references(target, repo_relpath)
        except CliBridgeError as exc:
            findings.append(
                Finding(
                    source=Source.BMAD_OUTPUT_HYGIENE,
                    check="orphan-file-unevaluable",
                    status=DoctorStatus.WARN,
                    message=(f"{station}: {relpath} — inbound-reference check could not be evaluated here — {exc}"),
                    evidence={"station": station, "path": relpath},
                )
            )
            continue
        if not is_orphan_file(relpath, has_inbound_references=has_refs):
            continue
        findings.append(
            Finding(
                source=Source.BMAD_OUTPUT_HYGIENE,
                check=HygieneFindingKind.ORPHAN_FILE.value,
                status=DoctorStatus.WARN,
                message=(f"{station}: {relpath} is unreferenced and its name/location is non-conventional"),
                evidence={"station": station, "path": relpath},
            )
        )
