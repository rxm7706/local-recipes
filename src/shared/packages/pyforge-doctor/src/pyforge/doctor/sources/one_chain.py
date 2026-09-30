"""One chain per station -- the two mechanism detectors (doctor Epic 25).

Outcome: the Guild's (``docs/governance/spec-one-chain-per-station/``, owner
Dream ``docs/dreams/one-chain-per-station.md``, ``owner: guild`` by the
Charter §5 shape of 2026-09-14). Mechanism: Doctor's, under §5's
outcome/mechanism rule -- the same relay as Epic 24.

Three gathers, all ``scope="repo"`` (tracked planning artifacts only, no
network, no station import):

* ``gather_chain_sprawl`` (Story 25.1, CAP-2) -- Dream-**append**-first is
  enforced, not asserted: a Dream file or Spec folder that was not present
  at the ruling SHA and carries no ``fold-exemption:`` from the closed list
  is a FAIL. The closed list is read from ``guild-roster.json``
  ``fold_exemptions`` (vocabulary-one-name-one-job CAP-2: one declared
  vocabulary source), never hard-coded here. The baseline
  (``docs/governance/chain-sprawl-baseline.json``) is a dated snapshot;
  *eventual consistency* (Spec Constraint) means a pre-ruling folder is
  never a finding, and a baseline write may only REMOVE entries (a fold that
  archived or absorbed something) -- adding is what the exemption is for.

* ``gather_fr_without_cap`` (Story 25.2, CAP-5) -- a product requirement
  minted after the rule date names its source capability (``FR-n <- CAP-m``,
  CHAIN-STANDARD § 2). The pre-rule FR population per station lives in
  ``docs/governance/fr-baseline.json`` and is never a finding; that baseline
  is regenerated only at a station's fold PR, when its PRD is re-derived
  FR <- CAP in full.

* ``gather_fold_complete`` (Story 36.1, CAP-11) -- a fold is complete before
  its file moves. Every ``archive/docs/dreams/*.md`` not in
  ``docs/governance/fold-complete-baseline.json`` has each of its long
  paragraphs in its station Dream (``docs/dreams/pyforge-<owner>.md``),
  whitespace-collapsed; a missing one is a FAIL naming the file and the count.
  Every ``docs/dreams/*.md`` still reading ``status: archived`` is ONE WARN
  with the count per station -- the migration's countdown, never a FAIL.
  Read-only: it moves no file and edits no Dream.

All degrade, never crash (the house rule), and all report a missing
baseline as WARN -- cannot-evaluate is never a FAIL and never a silent green.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from ..models import DoctorStatus, Finding, Source
from . import degrade_on_exception
from .chain import _dream_body_after_frontmatter, _frontmatter_parse

__all__ = (
    "CHAIN_SPRAWL_BASELINE_REL",
    "FOLD_COMPLETE_BASELINE_REL",
    "FR_BASELINE_REL",
    "enumerate_chain_units",
    "gather_chain_sprawl",
    "gather_fold_complete",
    "gather_fr_without_cap",
    "long_paragraphs",
    "prune_chain_sprawl_baseline",
    "snapshot_chain_sprawl_baseline",
    "snapshot_fr_baseline",
)

CHAIN_SPRAWL_BASELINE_REL = Path("docs") / "governance" / "chain-sprawl-baseline.json"
FR_BASELINE_REL = Path("docs") / "governance" / "fr-baseline.json"
FOLD_COMPLETE_BASELINE_REL = Path("docs") / "governance" / "fold-complete-baseline.json"
_ROSTER_REL = Path("docs") / "governance" / "guild-roster.json"
_DREAMS_REL = Path("docs") / "dreams"
_PROJECTS_REL = Path("_bmad-output") / "projects"
_GOVERNANCE_REL = Path("docs") / "governance"

_STATION_DREAM_RE = re.compile(r"^pyforge-[a-z]+\.md$")
_STATION_SPEC_RE = re.compile(r"^spec-pyforge-[a-z]+$")


# --------------------------------------------------------------------------
# shared readers
# --------------------------------------------------------------------------


def _read_json(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError, UnicodeDecodeError, json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _roster(target: Path) -> dict:
    return _read_json(target / _ROSTER_REL) or {}


def _fold_exemptions(target: Path) -> tuple[str, ...] | None:
    """The closed list, from the one declared source. ``None`` when the
    roster does not declare it -- the gather then WARNs rather than inventing
    a list."""
    values = _roster(target).get("fold_exemptions")
    if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
        return None
    return tuple(values)


def _stations(target: Path) -> tuple[str, ...]:
    values = _roster(target).get("stations")
    if isinstance(values, list):
        return tuple(str(v) for v in values)
    return ("herald", "marshal", "atlas", "warden", "mason", "doctor", "scribe", "steward")


# --------------------------------------------------------------------------
# Story 25.1 -- chain-sprawl
# --------------------------------------------------------------------------


def enumerate_chain_units(target: Path) -> tuple[dict[str, Path], dict[str, Path]]:
    """``(dreams, spec_folders)`` keyed by repo-relative POSIX path.

    Structurally excluded -- they ARE the chain, not sprawl: station Dreams
    ``pyforge-<s>.md``, station Spec folders ``spec-pyforge-<s>/``, and story
    spec FILES ``spec-<E>-<S>-<slug>.md`` (folders are enumerated, files are
    not). ``README.md`` and ``archive/`` under ``docs/dreams/`` are not
    Dreams.
    """
    stations = set(_stations(target))
    dreams: dict[str, Path] = {}
    ddir = target / _DREAMS_REL
    if ddir.is_dir():
        for p in sorted(ddir.glob("*.md")):
            if p.name == "README.md":
                continue
            if _STATION_DREAM_RE.match(p.name) and p.stem.removeprefix("pyforge-") in stations:
                continue
            dreams[p.relative_to(target).as_posix()] = p

    folders: dict[str, Path] = {}
    pdir = target / _PROJECTS_REL
    if pdir.is_dir():
        for spec_dir in sorted(pdir.glob("*/planning-artifacts/specs/spec-*")):
            if not spec_dir.is_dir():
                continue  # story specs are files -- the chain, not sprawl
            if _STATION_SPEC_RE.match(spec_dir.name):
                continue
            folders[spec_dir.relative_to(target).as_posix()] = spec_dir
    gdir = target / _GOVERNANCE_REL
    if gdir.is_dir():
        for spec_dir in sorted(gdir.glob("spec-*")):
            if spec_dir.is_dir():
                folders[spec_dir.relative_to(target).as_posix()] = spec_dir
    return dreams, folders


def snapshot_chain_sprawl_baseline(target: Path, *, ruling_sha: str) -> dict:
    """The dated snapshot shape. Written ONCE at the ruling SHA; afterwards
    only ``prune_chain_sprawl_baseline`` may touch it."""
    dreams, folders = enumerate_chain_units(target)
    return {
        "$comment": [
            "chain-sprawl-check baseline (doctor Story 25.1, spec-one-chain-per-station CAP-2).",
            "Every Dream file and Spec folder present at the ruling SHA. A path listed here is",
            "never a finding (eventual consistency: folded and unfolded stations both pass).",
            "This file only ever SHRINKS -- `python scripts/chain_sprawl_baseline.py --prune`",
            "removes entries a fold archived or absorbed. Adding an entry is what",
            "`fold-exemption:` is for; a hand-added path here is a governance act and a finding.",
        ],
        "ruling_sha": ruling_sha,
        "dreams": sorted(dreams),
        "spec_folders": sorted(folders),
    }


def prune_chain_sprawl_baseline(target: Path) -> tuple[dict | None, list[str]]:
    """Drop baseline entries that no longer exist on disk. Returns the new
    baseline (or ``None`` when unreadable) and the removed paths. Never adds."""
    path = target / CHAIN_SPRAWL_BASELINE_REL
    data = _read_json(path)
    if data is None:
        return None, []
    removed: list[str] = []
    for key in ("dreams", "spec_folders"):
        kept = []
        for rel in data.get(key, []):
            if (target / rel).exists():
                kept.append(rel)
            else:
                removed.append(rel)
        data[key] = sorted(kept)
    return data, removed


def gather_chain_sprawl(target: Path) -> tuple[Finding, ...]:
    """A new Dream or Spec folder without a declared exemption is a finding."""
    return degrade_on_exception(Source.CHAIN_SPRAWL, "chain-sprawl", lambda: _gather_chain_sprawl(target))


def _gather_chain_sprawl(target: Path) -> tuple[Finding, ...]:
    baseline = _read_json(target / CHAIN_SPRAWL_BASELINE_REL)
    if baseline is None:
        return (
            Finding(
                source=Source.CHAIN_SPRAWL,
                check="chain-sprawl-no-baseline",
                status=DoctorStatus.WARN,
                message=(
                    f"{CHAIN_SPRAWL_BASELINE_REL.as_posix()} is missing or unreadable — "
                    "sprawl cannot be measured against the ruling snapshot"
                ),
                evidence={"baseline": CHAIN_SPRAWL_BASELINE_REL.as_posix()},
            ),
        )
    exemptions = _fold_exemptions(target)
    if exemptions is None:
        return (
            Finding(
                source=Source.CHAIN_SPRAWL,
                check="chain-sprawl-no-vocabulary",
                status=DoctorStatus.WARN,
                message=(
                    f"{_ROSTER_REL.as_posix()} declares no `fold_exemptions` list — the "
                    "closed exemption vocabulary has no declared source"
                ),
                evidence={"roster": _ROSTER_REL.as_posix()},
            ),
        )

    known_dreams = set(baseline.get("dreams", []))
    known_folders = set(baseline.get("spec_folders", []))
    dreams, folders = enumerate_chain_units(target)
    stations = _stations(target)
    station_dreams = [f"docs/dreams/pyforge-{s}.md" for s in stations]

    findings: list[Finding] = []
    exempt: list[dict] = []
    unexempted: list[dict] = []

    def _judge(rel: str, fm_path: Path, kind: str) -> None:
        fm, unparseable = _frontmatter_parse(fm_path)
        value = fm.get("fold-exemption")
        item = {"path": rel, "kind": kind, "fold_exemption": value}
        if isinstance(value, str) and value in exemptions:
            exempt.append(item)
            return
        item["reason"] = (
            "frontmatter unparseable"
            if unparseable
            else ("no fold-exemption" if value is None else f"value not in {list(exemptions)}")
        )
        unexempted.append(item)

    for rel, p in dreams.items():
        if rel in known_dreams:
            continue
        _judge(rel, p, "dream")
    for rel, d in folders.items():
        if rel in known_folders:
            continue
        _judge(rel, d / "SPEC.md", "spec-folder")

    for item in unexempted:
        findings.append(
            Finding(
                source=Source.CHAIN_SPRAWL,
                check="chain-sprawl-unexempted",
                status=DoctorStatus.FAIL,
                message=(
                    f"{item['path']} is a new {item['kind']} with {item['reason']} — "
                    "Dream-append-first: make it a dated section of a station Dream "
                    "and a CAP on that station's Spec, or declare `fold-exemption:` "
                    f"from {list(exemptions)}"
                ),
                evidence={
                    **item,
                    "station_dreams": station_dreams,
                    "standard": "docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md",
                },
            )
        )
    for item in exempt:
        findings.append(
            Finding(
                source=Source.CHAIN_SPRAWL,
                check="chain-sprawl-exempt",
                status=DoctorStatus.OK,
                message=f"{item['path']} carries fold-exemption: {item['fold_exemption']}",
                evidence=item,
            )
        )
    if not findings:
        findings.append(
            Finding(
                source=Source.CHAIN_SPRAWL,
                check="chain-sprawl",
                status=DoctorStatus.OK,
                message=(
                    f"no new Dream or Spec folder since {baseline.get('ruling_sha', '?')} "
                    f"({len(dreams)} dreams, {len(folders)} spec folders measured)"
                ),
                evidence={
                    "ruling_sha": baseline.get("ruling_sha"),
                    "dreams": len(dreams),
                    "spec_folders": len(folders),
                },
            )
        )
    return tuple(findings)


# --------------------------------------------------------------------------
# Story 25.2 -- fr-without-cap
# --------------------------------------------------------------------------

_FR_ID_RE = re.compile(r"\b(N?FR-\d+)\b")
_FR_LINE_RE = re.compile(r"^\s*(?:#{1,6}\s*|[-*]\s*|\|\s*)?\**\s*(N?FR-\d+)\b")
_CAP_RE = re.compile(r"\bCAP-(\d+)\b")
_CLOSED_SPEC_STATUSES = frozenset({"archived", "absorbed", "superseded"})


def _prd_files(project_dir: Path) -> list[Path]:
    prds = project_dir / "planning-artifacts" / "prds"
    if not prds.is_dir():
        return []
    return sorted(p for p in prds.glob("*/*.md") if p.is_file())


def _fr_ids_with_citation(text: str) -> dict[str, bool]:
    """``{FR-n: cited}`` for every FR/NFR id that OPENS a line (a heading, a
    list item or a table row). ``cited`` is True when ``CAP-m`` appears on the
    same line or the first non-blank line after it."""
    lines = text.splitlines()
    out: dict[str, bool] = {}
    for i, line in enumerate(lines):
        m = _FR_LINE_RE.match(line)
        if m is None:
            continue
        fr = m.group(1)
        if fr in out:
            continue  # first definition wins; later mentions are references
        cited = bool(_CAP_RE.search(line))
        if not cited:
            for nxt in lines[i + 1 : i + 4]:
                if nxt.strip():
                    cited = bool(_CAP_RE.search(nxt))
                    break
        out[fr] = cited
    return out


def _fr_citations(text: str, fr: str) -> set[str]:
    """CAP ids cited on the defining line (or first body line) of ``fr``."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = _FR_LINE_RE.match(line)
        if m is None or m.group(1) != fr:
            continue
        caps = {f"CAP-{n}" for n in _CAP_RE.findall(line)}
        if not caps:
            for nxt in lines[i + 1 : i + 4]:
                if nxt.strip():
                    caps = {f"CAP-{n}" for n in _CAP_RE.findall(nxt)}
                    break
        return caps
    return set()


def _open_caps(project_dir: Path) -> tuple[set[str], list[str]]:
    """CAP ids declared by every OPEN Spec folder under the station (before
    its fold, any of them; after it, only ``spec-pyforge-<s>`` remains open).
    Returns ``(caps, folders_consulted)``."""
    caps: set[str] = set()
    consulted: list[str] = []
    specs = project_dir / "planning-artifacts" / "specs"
    if not specs.is_dir():
        return caps, consulted
    for spec_md in sorted(specs.glob("spec-*/SPEC.md")):
        fm, _ = _frontmatter_parse(spec_md)
        status = str(fm.get("status", "")).split()[0] if fm.get("status") else ""
        if status in _CLOSED_SPEC_STATUSES:
            continue
        try:
            text = spec_md.read_text(encoding="utf-8")
        except OSError, UnicodeDecodeError:
            continue
        consulted.append(spec_md.parent.name)
        caps.update(f"CAP-{n}" for n in _CAP_RE.findall(text))
    return caps, consulted


def snapshot_fr_baseline(
    target: Path, *, ruling_sha: str, only_project: str | None = None, existing: dict | None = None
) -> dict:
    """Per-station pre-rule FR population. With ``only_project`` set, every
    other station's entry is carried over from ``existing`` untouched -- a
    fold PR re-baselines its own station only."""
    projects: dict[str, list[str]] = {}
    if existing and isinstance(existing.get("projects"), dict):
        projects.update({k: list(v) for k, v in existing["projects"].items()})
    pdir = target / _PROJECTS_REL
    for project_dir in sorted(pdir.glob("pyforge-*")) if pdir.is_dir() else []:
        slug = project_dir.name
        if only_project and slug != only_project:
            continue
        ids: set[str] = set()
        for prd in _prd_files(project_dir):
            try:
                ids.update(_fr_ids_with_citation(prd.read_text(encoding="utf-8")))
            except OSError, UnicodeDecodeError:
                continue
        projects[slug] = sorted(ids, key=lambda s: (s.startswith("N"), int(s.split("-")[1])))
    return {
        "$comment": [
            "fr-without-cap baseline (doctor Story 25.2, spec-one-chain-per-station CAP-5).",
            "Every FR-n / NFR-n id per station PRD at the ruling SHA -- the pre-rule population,",
            "never a finding. Regenerated ONLY per station, at that station's fold PR, when its",
            "PRD is re-derived FR <- CAP in full:",
            "  python scripts/fr_baseline.py --project pyforge-<s>",
        ],
        "ruling_sha": ruling_sha,
        "projects": projects,
    }


def gather_fr_without_cap(target: Path) -> tuple[Finding, ...]:
    """A product requirement minted after the rule date names its source CAP."""
    return degrade_on_exception(Source.FR_WITHOUT_CAP, "fr-without-cap", lambda: _gather_fr_without_cap(target))


def _gather_fr_without_cap(target: Path) -> tuple[Finding, ...]:
    baseline = _read_json(target / FR_BASELINE_REL)
    if baseline is None or not isinstance(baseline.get("projects"), dict):
        return (
            Finding(
                source=Source.FR_WITHOUT_CAP,
                check="fr-without-cap-no-baseline",
                status=DoctorStatus.WARN,
                message=(
                    f"{FR_BASELINE_REL.as_posix()} is missing or unreadable — new FRs "
                    "cannot be told from the pre-rule population"
                ),
                evidence={"baseline": FR_BASELINE_REL.as_posix()},
            ),
        )
    known: dict[str, set[str]] = {k: set(v) for k, v in baseline["projects"].items() if isinstance(v, list)}
    findings: list[Finding] = []
    measured_new = 0
    pdir = target / _PROJECTS_REL
    for project_dir in sorted(pdir.glob("pyforge-*")) if pdir.is_dir() else []:
        slug = project_dir.name
        station = slug.removeprefix("pyforge-")
        base_ids = known.get(slug, set())
        caps: set[str] | None = None
        consulted: list[str] = []
        for prd in _prd_files(project_dir):
            try:
                text = prd.read_text(encoding="utf-8")
            except OSError, UnicodeDecodeError:
                continue
            rel = prd.relative_to(target).as_posix()
            for fr, cited in _fr_ids_with_citation(text).items():
                if fr in base_ids:
                    continue
                measured_new += 1
                spec_folder = f"{_PROJECTS_REL.as_posix()}/{slug}/planning-artifacts/specs/spec-{slug}/"
                if not cited:
                    findings.append(
                        Finding(
                            source=Source.FR_WITHOUT_CAP,
                            check="fr-without-cap",
                            status=DoctorStatus.FAIL,
                            message=(
                                f"{rel}: {fr} was minted after the rule date and cites no "
                                f"source capability — write `{fr} ← CAP-m` against "
                                f"{station}'s Spec (CHAIN-STANDARD § 2)"
                            ),
                            evidence={
                                "prd": rel,
                                "fr": fr,
                                "station": station,
                                "spec_folder": spec_folder,
                            },
                        )
                    )
                    continue
                if caps is None:
                    caps, consulted = _open_caps(project_dir)
                missing = sorted(c for c in _fr_citations(text, fr) if c not in caps)
                if missing:
                    findings.append(
                        Finding(
                            source=Source.FR_WITHOUT_CAP,
                            check="fr-cap-unresolved",
                            status=DoctorStatus.FAIL,
                            message=(
                                f"{rel}: {fr} cites {', '.join(missing)}, which no open Spec "
                                f"under {slug} declares ({len(consulted)} folder(s) consulted)"
                            ),
                            evidence={
                                "prd": rel,
                                "fr": fr,
                                "station": station,
                                "unresolved": missing,
                                "consulted": consulted,
                            },
                        )
                    )
    if not findings:
        findings.append(
            Finding(
                source=Source.FR_WITHOUT_CAP,
                check="fr-without-cap",
                status=DoctorStatus.OK,
                message=(
                    f"every FR minted since {baseline.get('ruling_sha', '?')} cites a "
                    f"resolving CAP ({measured_new} new FR(s) measured)"
                ),
                evidence={"ruling_sha": baseline.get("ruling_sha"), "new_frs": measured_new},
            )
        )
    return tuple(findings)


# --------------------------------------------------------------------------
# Story 36.1 -- fold-complete
# --------------------------------------------------------------------------

_ARCHIVE_DREAMS_REL = Path("archive") / "docs" / "dreams"
_HEADING_LINE_RE = re.compile(r"^#{1,6}(?:\s|$)")
_OWNER_RE = re.compile(r"[a-z][a-z0-9-]*")  # used with fullmatch: `$` would let "mason\n" through
_MIN_PARAGRAPH_CHARS = 80  # a paragraph is "long" when it is LONGER than this
_EXCERPTS_SHOWN = 3
_EXCERPT_CHARS = 80


def _collapse(text: str) -> str:
    return " ".join(text.split())


def long_paragraphs(text: str) -> list[str]:
    """The paragraphs of a Dream's body that a fold must carry, in order.

    The frontmatter block is left out (``_dream_body_after_frontmatter``, the
    same line-anchored scan ``_frontmatter_parse`` bounds it with). A blank
    line ends a paragraph, and so does a heading line (``#{1,6}`` then a
    space), which is itself dropped: a satellite whose headings were demoted
    one level when pasted still matches, and so does a paragraph that abuts a
    heading with no blank line. Whitespace runs collapse to one space, and
    only a paragraph longer than 80 characters is kept.
    """
    out: list[str] = []
    current: list[str] = []

    def _flush() -> None:
        if current:
            paragraph = _collapse(" ".join(current))
            if len(paragraph) > _MIN_PARAGRAPH_CHARS:
                out.append(paragraph)
            current.clear()

    for line in _dream_body_after_frontmatter(text).splitlines():
        if not line.strip() or _HEADING_LINE_RE.match(line):
            _flush()
            continue
        current.append(line)
    _flush()
    return out


def gather_fold_complete(target: Path) -> tuple[Finding, ...]:
    """An archived Dream's long paragraphs are all in its station Dream."""
    return degrade_on_exception(Source.FOLD_COMPLETE, "fold-complete", lambda: _gather_fold_complete(target))


def _fold_fail(check: str, rel: str, message: str, **evidence: object) -> Finding:
    return Finding(
        source=Source.FOLD_COMPLETE,
        check=check,
        status=DoctorStatus.FAIL,
        message=f"{rel}: {message}",
        evidence={"path": rel, **evidence},
    )


def _gather_fold_complete(target: Path) -> tuple[Finding, ...]:
    baseline = _read_json(target / FOLD_COMPLETE_BASELINE_REL)
    if baseline is None or not isinstance(baseline.get("paths"), list):
        return (
            Finding(
                source=Source.FOLD_COMPLETE,
                check="fold-complete-no-baseline",
                status=DoctorStatus.WARN,
                message=(
                    f"{FOLD_COMPLETE_BASELINE_REL.as_posix()} is missing or unreadable — "
                    "the files under archive/docs/dreams/ that are not folds cannot be told "
                    "from the folds"
                ),
                evidence={"baseline": FOLD_COMPLETE_BASELINE_REL.as_posix()},
            ),
        )
    baselined = {p for p in baseline["paths"] if isinstance(p, str)}

    findings: list[Finding] = []
    complete: list[str] = []
    skipped: list[str] = []
    station_texts: dict[str, str | None] = {}  # owner -> collapsed station Dream, None when absent
    adir = target / _ARCHIVE_DREAMS_REL
    for path in sorted(adir.glob("*.md")) if adir.is_dir() else []:
        rel = path.relative_to(target).as_posix()
        if rel in baselined:
            skipped.append(rel)  # not a fold of a station Dream: never opened
            findings.append(
                Finding(
                    source=Source.FOLD_COMPLETE,
                    check="fold-complete-baselined",
                    status=DoctorStatus.OK,
                    message=(
                        f"{rel} is listed in {FOLD_COMPLETE_BASELINE_REL.as_posix()} "
                        "(not a fold of a station Dream) -- not read"
                    ),
                    evidence={"path": rel},
                )
            )
            continue
        fields, _unparseable = _frontmatter_parse(path)
        owner = fields.get("owner")
        if not isinstance(owner, str) or not _OWNER_RE.fullmatch(owner):
            findings.append(
                _fold_fail(
                    "fold-complete-no-owner",
                    rel,
                    "no readable `owner:` in its frontmatter (missing, unparseable, or not a "
                    "station slug) — the station Dream it folds into cannot be named",
                )
            )
            continue
        station_rel = f"{_DREAMS_REL.as_posix()}/pyforge-{owner}.md"
        if owner not in station_texts:
            try:
                station_texts[owner] = _collapse((target / station_rel).read_text(encoding="utf-8"))
            except OSError, UnicodeDecodeError:
                station_texts[owner] = None
        station_text = station_texts[owner]
        if station_text is None:
            findings.append(
                _fold_fail(
                    "fold-complete-no-station-dream",
                    rel,
                    f"owner `{owner}` names {station_rel}, which is missing or unreadable",
                    owner=owner,
                    station_dream=station_rel,
                )
            )
            continue
        paragraphs = long_paragraphs(path.read_text(encoding="utf-8"))
        missing = [p for p in paragraphs if p not in station_text]
        if missing:
            count = len(missing)
            findings.append(
                _fold_fail(
                    "fold-complete-incomplete",
                    rel,
                    f"{count} paragraph{'' if count == 1 else 's'} missing from {station_rel} "
                    f"(of {len(paragraphs)} long) — paste the body in, verbatim, under a dated "
                    "section before the file moves",
                    owner=owner,
                    station_dream=station_rel,
                    missing=count,
                    paragraphs=len(paragraphs),
                    missing_excerpts=[p[:_EXCERPT_CHARS] for p in missing[:_EXCERPTS_SHOWN]],
                )
            )
            continue
        complete.append(rel)
        findings.append(
            Finding(
                source=Source.FOLD_COMPLETE,
                check="fold-complete-ok",
                status=DoctorStatus.OK,
                message=f"{rel}: all {len(paragraphs)} long paragraph(s) are in {station_rel}",
                evidence={
                    "path": rel,
                    "owner": owner,
                    "station_dream": station_rel,
                    "paragraphs": len(paragraphs),
                },
            )
        )

    findings.append(
        Finding(
            source=Source.FOLD_COMPLETE,
            check="fold-complete",
            status=DoctorStatus.OK,
            message=(
                f"{len(complete)} archived Dream(s) folded into their station Dream, "
                f"{len(skipped)} baselined (not read)"
            ),
            evidence={"complete": complete, "baselined": skipped},
        )
    )

    live_finding = _archived_in_live_tree(target)
    if live_finding is not None:
        findings.append(live_finding)
    return tuple(findings)


def _archived_in_live_tree(target: Path) -> Finding | None:
    """ONE WARN counting the Dreams in ``docs/dreams/`` that still read
    ``status: archived``, per station -- the migration's countdown. A Dream
    whose frontmatter cannot be read has no status to count; it is reported
    beside the count so the countdown never silently undercounts."""
    ddir = target / _DREAMS_REL
    by_station: dict[str, int] = {}
    unreadable = 0
    for path in sorted(ddir.glob("*.md")) if ddir.is_dir() else []:
        fields, unparseable = _frontmatter_parse(path)
        if unparseable:
            unreadable += 1
            continue
        status = fields.get("status")
        if not isinstance(status, str) or status.strip() != "archived":
            continue
        owner = fields.get("owner")
        station = owner if isinstance(owner, str) and owner else "unknown"
        by_station[station] = by_station.get(station, 0) + 1
    total = sum(by_station.values())
    if total == 0 and unreadable == 0:
        return None
    per_station = ", ".join(f"{station} {n}" for station, n in sorted(by_station.items())) or "none"
    tail = f"; {unreadable} more have unreadable frontmatter (status unknown)" if unreadable else ""
    return Finding(
        source=Source.FOLD_COMPLETE,
        check="fold-complete-archived-in-live-tree",
        status=DoctorStatus.WARN,
        message=(
            f"{total} Dream(s) in docs/dreams/ still read `status: archived` ({per_station}){tail} — "
            "each moves to archive/docs/dreams/ once its body is in its station Dream "
            "(spec-one-chain-per-station CAP-11)"
        ),
        evidence={
            "total": total,
            "by_station": dict(sorted(by_station.items())),
            "unreadable_frontmatter": unreadable,
        },
    )
