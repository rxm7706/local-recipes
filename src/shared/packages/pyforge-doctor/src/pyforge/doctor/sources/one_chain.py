"""One chain per station -- the two mechanism detectors (doctor Epic 25).

Outcome: the Guild's (``docs/governance/spec-one-chain-per-station/``, owner
Dream ``docs/dreams/one-chain-per-station.md``, ``owner: guild`` by the
Charter §5 shape of 2026-09-14). Mechanism: Doctor's, under §5's
outcome/mechanism rule -- the same relay as Epic 24.

Three gathers, all ``scope="repo"`` (tracked planning artifacts only, no
network, no station import; ``fr-without-cap`` alone reads git, through
``cli_bridge.run_git``):

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

* ``gather_fr_without_cap`` (Story 25.2, CAP-5; Story 50.1, spec-pyforge-doctor
  CAP-92) -- a product requirement names its source capability and nothing
  else (``FR-n <- CAP-m``, CHAIN-STANDARD § 2 and § 6). A definition with no
  arrow and no cite is ``fr-without-cap`` unless its id is in
  ``docs/governance/fr-baseline.json`` ``projects`` -- the arrowless
  population at snapshot, which only shrinks. The arrow grammar adds
  ``fr-cites-non-capability`` (an arrow item that is not a CAP cite),
  ``fr-cap-unresolved`` (a cite no CAP *definition* line of the named Spec
  resolves -- never a closed Spec's), ``fr-id-unhyphenated``,
  ``fr-id-malformed`` (a definition-shaped token outside the family),
  ``fr-duplicate-id`` and ``fr-counted-run``; the baseline's ``findings`` map
  turns a known one into ``fr-baselined`` (OK) and a stale ``projects`` id or
  ``findings`` key is ``fr-baseline-stale`` (WARN). ``fr-arrow-no-title-overlap``
  is advisory, one WARN per station; an unreadable PRD is ``fr-prd-unreadable``
  (WARN), never a silent green. Story 50.2 enforces the shrink-only rule: a
  ``projects`` id or ``findings`` key added since the merge-base of ``HEAD``
  and ``refs/remotes/origin/main`` is ``fr-baseline-grown`` (FAIL) unless the
  file's ``forced`` list, written by ``scripts/fr_baseline.py`` alone, names
  it; a base that cannot be read is ``fr-baseline-base-unread`` (WARN).

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
from dataclasses import dataclass
from pathlib import Path

from ..cli_bridge import CliBridgeError, run_git
from ..models import DoctorStatus, Finding, Source
from ..refs import ORIGIN_MAIN, display_ref
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
    "prune_fr_baseline",
    "record_fr_additions",
    "snapshot_chain_sprawl_baseline",
    "snapshot_fr_baseline",
    "snapshot_fr_findings",
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
# Story 25.2 -- fr-without-cap; Story 50.1 (CAP-92) -- the arrow grammar
# --------------------------------------------------------------------------
#
# A requirement definition opens a line: a marker (heading, bullet, table
# cell or bold), an id-like token, then a definition separator -- or, for a
# heading and for a bold-opened id whose bold closes into a separator,
# whitespace and a title. It is a definition only when it is a heading, has
# a title or arrow description, or carries an arrow; a bare `- **FR-n** prose`
# mention is a reference whenever it appears. A column-0 or indented mention
# with no marker, a token followed by a range marker (`FR-8..FR-11`,
# `FR-66–FR-71`, `FR-1 to FR-3`) or carrying a lettered suffix
# (`FR9-was-KEV`), and anything inside a fenced code block are references.
# The sanctioned id family is `N?FR-[A-Z]?\d+(\.\d+)*`: a token without the
# hyphen is `fr-id-unhyphenated`, any other definition-shaped token is
# `fr-id-malformed`. The first definition wins; a second one is
# `fr-duplicate-id` unless it sits in a record section (a `## ` heading that
# opens `Currency reconciliation` / `Fold provenance` / `Test-tree
# convergence` / `Currency validation` / `Validation note`, or carries an ISO
# date beside a reconcile / provenance / convergence / validation / log
# word), where every line is a reference. Citations come from the defining
# line, else its first non-blank body line; an arrow (`←`) must carry CAP
# cites and nothing else; a `spec-<x>` prefix carries forward over the items
# of one arrow or parenthetical; a bare `CAP-m` resolves only against the
# station Spec's own CAP definition lines, a `spec-<x> CAP-m` cite against
# that Spec's, wherever it lives, never into a closed (archived / absorbed /
# superseded) Spec.

_FR_DEF_RE = re.compile(
    r"^[ \t]*(?P<marker>#{1,6}[ \t]+|[-*][ \t]+|\|[ \t]+|\*\*)(?P<bold>\*\*)?"
    r"(?P<id>N?FR(?:-[A-Z]?\d*|\d+)(?:\.\d+)*[A-Za-z0-9-]*)(?P<rest>.*)$"
)
_FR_ID_RE = re.compile(r"N?FR-[A-Z]?\d+(?:\.\d+)*")  # the family (CHAIN-STANDARD § 6)
_FR_ID_UNHYPHENATED_RE = re.compile(r"N?FR[A-Z]?\d+(?:\.\d+)*")
_FR_ID_SUFFIXED_RE = re.compile(r"N?FR-?[A-Z]?\d+(?:\.\d+)*-[A-Za-z]")  # `FR9-was-KEV`
_FR_SEPARATOR_RE = re.compile(r"^(?::|\*\*| —| -| ←| \*\(| \(| \||$)")
_FR_BOLD_TITLE_RE = re.compile(r"^(\s+[^*\n]+)\*\*(?=:| —| -| ←| \*\(| \(| \||$)")
_FR_REFERENCE_RE = re.compile(r"^\s*(?:\.\.|…|–\s*N?FR|(?:to|through|and)\s+N?FR\b)")
_CAP_DEF_RE = re.compile(r"^[ \t]*(?:#{1,6}[ \t]+|[-*][ \t]+\*\*|\*\*)CAP-(?P<n>\d+)(?P<rest>.*)$")
_CAP_SEPARATOR_RE = re.compile(r"^(?::|\*\*| —| -| ←| \(|$)")
_CAP_CITE_RE = re.compile(r"(?:`?(?P<spec>spec-[a-z0-9-]+)`?[ :])?CAP-(?P<a>\d+)(?:\s*(?:\.\.|–|-)\s*CAP-(?P<b>\d+))?")
_CAP_RE = re.compile(r"\bCAP-(\d+)\b")
_ARROW_END_RE = re.compile(r" — | – | - | \*\(| \(|: |\*\*| \|")
_ARROW_ITEM_SPLIT_RE = re.compile(r'(?:,|\band\b)(?=(?:[^"]*"[^"]*")*[^"]*$)')
_INTENT_SUCCESS_RE = re.compile(r"\*{1,2}\s*(intent|success)\s*:?\s*\*{1,2}\s*:?\s*(.*)", re.IGNORECASE)
_RECORD_PREFIX_RE = re.compile(
    r"^(?:Currency reconciliation|Fold provenance|Test-tree convergence|Currency validation|Validation note)"
)
_RECORD_DATED_RE = re.compile(r"\b(?:reconcil\w*|provenance|convergence|validation|log)\b", re.IGNORECASE)
_ISO_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_SECTION_NUMBER_RE = re.compile(r"^\d+(?:\.\d+)*\.?\s+")
_FENCE_RE = re.compile(r"^\s*(?:```|~~~)")
_HEADING_TITLE_RE = re.compile(r"\s+\S")
_WORD_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    "the a an and or of to in on for by with from is are be its it as at not no one every "
    "each that this all any into via than can has have was were will when where which".split()
)
_CLOSED_SPEC_STATUSES = frozenset({"archived", "absorbed", "superseded"})
_MIN_RUN = 4
_MAX_RANGE = 50  # a `CAP-a..CAP-b` wider than this cites its two endpoints only


def _prd_files(project_dir: Path) -> list[Path]:
    prds = project_dir / "planning-artifacts" / "prds"
    if not prds.is_dir():
        return []
    return sorted(p for p in prds.glob("*/prd.md") if p.is_file())


def _content_words(text: str) -> set[str]:
    out: set[str] = set()
    for word in _WORD_RE.findall(text.lower()):
        if len(word) >= 3 and word not in _STOPWORDS:
            out.add(word.rstrip("s"))
    return out


def _fr_sort_key(fr: str) -> tuple:
    m = re.match(r"(N?)FR-?([A-Z]?)(\d+(?:\.\d+)*)$", fr)
    if m is None:
        return (2, fr)  # a malformed token sorts last, by its text
    return (m.group(1) == "N", m.group(2), tuple(int(p) for p in m.group(3).split(".")))


def _id_kind(token: str) -> str:
    """``ok`` / ``unhyphenated`` / ``reference`` (an id with a lettered
    suffix, `FR9-was-KEV`) / ``malformed`` (any other id-like token)."""
    if _FR_ID_RE.fullmatch(token):
        return "ok"
    if _FR_ID_UNHYPHENATED_RE.fullmatch(token):
        return "unhyphenated"
    if _FR_ID_SUFFIXED_RE.match(token):
        return "reference"
    return "malformed"


@dataclass(frozen=True)
class _FrDef:
    fr: str
    line: int  # 1-based
    heading: bool
    kind: str  # `ok` / `unhyphenated` / `malformed` (see _id_kind)
    title: str  # the text between the separator and the arrow / closing bold
    text: str  # title, or the description after the arrow when the title is empty
    has_arrow: bool
    cites: tuple[tuple[str | None, int], ...]  # (spec folder or None for the station Spec, n)
    offending: tuple[str, ...]  # arrow items that are not CAP cites

    @property
    def cited(self) -> bool:
        return bool(self.cites)

    @property
    def arrowless(self) -> bool:
        """No ``←`` and no CAP cite at all -- the `fr-without-cap` shape."""
        return not self.has_arrow and not self.cites

    @property
    def integer_id(self) -> int | None:
        m = re.fullmatch(r"FR-(\d+)", self.fr)
        return int(m.group(1)) if m else None


def _parse_cites(text: str, spec: str | None = None) -> list[tuple[str | None, int]]:
    """Every CAP cite in ``text``; a ``spec-<x>`` prefix carries forward over
    the cites that follow it (``spec-x CAP-1, CAP-2`` names two of x's)."""
    cites: list[tuple[str | None, int]] = []
    for m in _CAP_CITE_RE.finditer(text):
        spec = m.group("spec") or spec
        a = int(m.group("a"))
        b = int(m.group("b")) if m.group("b") else a
        span = range(a, b + 1) if 0 <= b - a <= _MAX_RANGE else (a, b)
        cites.extend((spec, n) for n in span)
    return cites


def _parse_arrow(line: str) -> tuple[str, str]:
    """``(arrow_text, description)`` -- the text after ``←`` up to the first
    terminator, and whatever follows that terminator."""
    after = line.split("←", 1)[1]
    end = _ARROW_END_RE.search(after)
    if end is None:
        return after, ""
    return after[: end.start()], after[end.end() :]


def _arrow_items(arrow_text: str) -> tuple[list[tuple[str | None, int]], list[str]]:
    cites: list[tuple[str | None, int]] = []
    offending: list[str] = []
    spec: str | None = None
    for raw in _ARROW_ITEM_SPLIT_RE.split(arrow_text):
        item = raw.strip().strip("`").rstrip(".;)").strip()
        if not item:
            continue
        if _CAP_CITE_RE.fullmatch(item):
            cites.extend(_parse_cites(item, spec))
            spec = cites[-1][0]
        else:
            offending.append(item)
    return cites, offending


def _clean_title(text: str) -> str:
    text = re.split(r" ←|\*\*| \*\(|\(spec-", text, maxsplit=1)[0]
    return text.strip(" \t:—-*|").strip()


def _record_section(heading: str) -> bool:
    heading = _SECTION_NUMBER_RE.sub("", heading.strip())
    if _RECORD_PREFIX_RE.match(heading):
        return True
    return _ISO_DATE_RE.search(heading) is not None and _RECORD_DATED_RE.search(heading) is not None


def _fr_definitions(text: str) -> tuple[list[_FrDef], dict[str, list[int]]]:
    """The requirement definitions of one PRD in document order, and the
    duplicate definition lines (``{FR-n: [line, ...]}``) outside record
    sections. A line is a definition when it is a heading, carries a title
    or an arrow description, or carries an arrow -- first and later
    occurrences alike; reference lines are never returned."""
    lines = text.splitlines()
    defs: list[_FrDef] = []
    seen: set[str] = set()
    duplicates: dict[str, list[int]] = {}
    in_fence = False
    record = False
    for i, line in enumerate(lines):
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if line.startswith("## "):
            record = _record_section(line[3:])
        m = _FR_DEF_RE.match(line)
        if m is None:
            continue
        fr, rest = m.group("id"), m.group("rest")
        kind = _id_kind(fr)
        if kind == "reference" or _FR_REFERENCE_RE.match(rest):
            continue
        heading = m.group("marker").startswith("#")
        bold_opened = m.group("bold") is not None or m.group("marker") == "**"
        sep = _FR_SEPARATOR_RE.match(rest)
        if sep is not None:
            tail = rest[sep.end() :]
            if sep.group(0) == "**":
                # the bold closed on the id: a title follows only through a second separator
                tail = tail if _FR_SEPARATOR_RE.match(tail) and not tail.startswith(" ←") else ""
            elif tail.startswith("**"):
                tail = tail[2:].replace("**", "")  # `- **NFR-C1:** desc`: the bold closed on the separator
        elif heading and _HEADING_TITLE_RE.match(rest):
            tail = rest
        elif bold_opened and (bold := _FR_BOLD_TITLE_RE.match(rest)):
            tail = bold.group(1)  # `- **FR-n a title** — …`: the title sits inside the bold
        else:
            continue
        title = _clean_title(tail)
        cite_src = line
        if "←" not in line and not _CAP_RE.search(line):
            # else the first non-blank body line -- never the next definition or heading
            cite_src = next((nxt for nxt in lines[i + 1 : i + 4] if nxt.strip()), "")
            if _FR_DEF_RE.match(cite_src) or cite_src.lstrip().startswith("#"):
                cite_src = ""
            if "←" not in cite_src and not _CAP_RE.search(cite_src):
                cite_src = ""
        has_arrow = "←" in cite_src
        description = ""
        if has_arrow:
            arrow_text, description = _parse_arrow(cite_src)
            cites, offending = _arrow_items(arrow_text)
        else:
            cites, offending = _parse_cites(cite_src), []
        text_for_words = title or description.replace("**", "").strip(" \t:—-*")
        if not (heading or text_for_words or has_arrow):
            continue  # `- **FR-n** prose…`: a mention, first or later
        if fr in seen:
            if not record:
                duplicates.setdefault(fr, []).append(i + 1)
            continue  # first definition wins; later lines are references
        seen.add(fr)
        defs.append(
            _FrDef(
                fr=fr,
                line=i + 1,
                heading=heading,
                kind=kind,
                title=title,
                text=text_for_words,
                has_arrow=has_arrow,
                cites=tuple(cites),
                offending=tuple(offending),
            )
        )
    return defs, duplicates


@dataclass(frozen=True)
class _CapDef:
    title: str
    intent: str
    success: str


def _cap_definitions(text: str) -> dict[int, _CapDef]:
    """``{n: _CapDef}`` for every CAP that OPENS a line of a Spec (heading,
    bullet or bold), first definition winning; ``intent`` / ``success`` are
    read from the labelled lines of its block."""
    caps: dict[int, _CapDef] = {}
    current: int | None = None
    fields: dict[int, dict[str, str]] = {}
    in_fence = False
    for line in text.splitlines():
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = _CAP_DEF_RE.match(line)
        if m is not None:
            rest = m.group("rest")
            sep = _CAP_SEPARATOR_RE.match(rest)
            if sep is None and not (line.lstrip().startswith("#") and _HEADING_TITLE_RE.match(rest)):
                current = None
                continue
            n = int(m.group("n"))
            if n in caps:
                current = None
                continue
            caps[n] = _CapDef(title=_clean_title(rest[sep.end() :] if sep else rest), intent="", success="")
            current = n
            fields[n] = {}
        elif line.startswith("#"):
            current = None
            continue
        if current is None:
            continue
        for label, body in _INTENT_SUCCESS_RE.findall(line):
            fields[current].setdefault(label.lower(), body.strip())
    return {
        n: _CapDef(title=c.title, intent=fields[n].get("intent", ""), success=fields[n].get("success", ""))
        for n, c in caps.items()
    }


class _SpecIndex:
    """Lazily parsed CAP definitions per Spec folder. A cite from station
    ``pyforge-<s>`` finds ``spec-<x>`` under that station's own ``specs/``
    first, then ``docs/governance/``, then any other station's ``specs/``.
    A closed Spec (``_CLOSED_SPEC_STATUSES``) resolves nothing: its CAPs were
    reminted on the station Spec, and citing the absorbed one is wrong."""

    def __init__(self, target: Path) -> None:
        self._target = target
        self._paths: dict[tuple[str, str], Path | None] = {}
        self._caps: dict[Path, dict[int, _CapDef] | None] = {}  # None: unreadable
        self._closed: dict[Path, bool] = {}

    def path_for(self, slug: str, spec: str) -> Path | None:
        key = (slug, spec)
        if key not in self._paths:
            own = self._target / _PROJECTS_REL / slug / "planning-artifacts" / "specs" / spec / "SPEC.md"
            governance = self._target / _GOVERNANCE_REL / spec / "SPEC.md"
            others = sorted((self._target / _PROJECTS_REL).glob(f"*/planning-artifacts/specs/{spec}/SPEC.md"))
            self._paths[key] = next((p for p in (own, governance, *others) if p.is_file()), None)
        return self._paths[key]

    def caps(self, path: Path) -> dict[int, _CapDef] | None:
        if path not in self._caps:
            try:
                self._caps[path] = _cap_definitions(path.read_text(encoding="utf-8"))
            except OSError, UnicodeDecodeError:
                self._caps[path] = None
        return self._caps[path]

    def closed(self, path: Path) -> bool:
        if path not in self._closed:
            fm, _ = _frontmatter_parse(path)
            status = str(fm.get("status", "")).split()[0] if fm.get("status") else ""
            self._closed[path] = status in _CLOSED_SPEC_STATUSES
        return self._closed[path]

    def resolve(self, slug: str, cite: tuple[str | None, int]) -> tuple[_CapDef | None, str | None]:
        """``(definition, None)`` or ``(None, reason)`` with reason
        ``spec-not-found`` / ``spec-unreadable`` / ``spec-closed`` /
        ``cap-not-defined``."""
        spec, n = cite
        path = self.path_for(slug, spec or f"spec-{slug}")
        if path is None:
            return None, "spec-not-found"
        caps = self.caps(path)
        if caps is None:
            return None, "spec-unreadable"
        if self.closed(path):
            return None, "spec-closed"
        cap = caps.get(n)
        return (cap, None) if cap is not None else (None, "cap-not-defined")


def _cite_label(slug: str, cite: tuple[str | None, int]) -> str:
    spec, n = cite
    return f"CAP-{n}" if spec in (None, f"spec-{slug}") else f"{spec} CAP-{n}"


def _fr_fail(check: str, key: str, rel: str, message: str, **evidence: object) -> Finding:
    return Finding(
        source=Source.FR_WITHOUT_CAP,
        check=check,
        status=DoctorStatus.FAIL,
        message=f"{rel}: {message}",
        evidence={"key": key, "prd": rel, **evidence},
    )


def _counted_runs(defs: list[_FrDef], slug: str, specs: _SpecIndex) -> list[list[_FrDef]]:
    """Runs of >= ``_MIN_RUN`` consecutive FR-n definitions, each citing
    exactly one CAP of the station Spec at a constant offset, where no FR
    text shares a content word with its CAP's title."""
    runs: list[list[_FrDef]] = []
    run: list[_FrDef] = []
    last_n = offset = 0

    def _close() -> None:
        if len(run) >= _MIN_RUN:
            for d in run:
                cap, _ = specs.resolve(slug, d.cites[0])
                if cap is not None and _content_words(d.text) & _content_words(cap.title):
                    break
            else:
                runs.append(list(run))
        run.clear()

    for d in defs:
        n = d.integer_id
        if n is None or len(d.cites) != 1 or d.cites[0][0] not in (None, f"spec-{slug}"):
            _close()
            continue
        step = d.cites[0][1] - n
        if not (run and n == last_n + 1 and step == offset):
            _close()
            offset = step
        run.append(d)
        last_n = n
    _close()
    return runs


def _structural_findings(
    rel: str, slug: str, defs: list[_FrDef], duplicates: dict[str, list[int]], specs: _SpecIndex
) -> list[Finding]:
    """Every arrow-grammar FAIL of one PRD, each carrying its baseline
    ``key`` (``<check>:<FR-id or FR-a..FR-b>``)."""
    station = slug.removeprefix("pyforge-")
    out: list[Finding] = []
    for d in defs:
        if d.offending:
            out.append(
                _fr_fail(
                    "fr-cites-non-capability",
                    f"fr-cites-non-capability:{d.fr}",
                    rel,
                    f"{d.fr} (line {d.line}) cites {', '.join(repr(x) for x in d.offending)} on its arrow — "
                    "a requirement cites one or more defined CAPs (`← CAP-m` or `← spec-<x> CAP-m`) and "
                    "nothing else (CHAIN-STANDARD § 2, § 6)",
                    fr=d.fr,
                    line=d.line,
                    station=station,
                    offending=list(d.offending),
                )
            )
        unresolved: list[str] = []
        reasons: dict[str, str] = {}
        for cite in d.cites:
            cap, reason = specs.resolve(slug, cite)
            if cap is None and reason is not None:
                label = _cite_label(slug, cite)
                unresolved.append(label)
                reasons[label] = reason
        if unresolved:
            out.append(
                _fr_fail(
                    "fr-cap-unresolved",
                    f"fr-cap-unresolved:{d.fr}",
                    rel,
                    f"{d.fr} (line {d.line}) cites "
                    + ", ".join(f"{label} ({reasons[label]})" for label in unresolved)
                    + f" — a bare CAP-m resolves against spec-{slug}/SPEC.md's own definition lines, "
                    "a `spec-<x> CAP-m` cite against that Spec's (never a closed one)",
                    fr=d.fr,
                    line=d.line,
                    station=station,
                    unresolved=unresolved,
                    reasons=reasons,
                )
            )
        if d.kind == "unhyphenated":
            out.append(
                _fr_fail(
                    "fr-id-unhyphenated",
                    f"fr-id-unhyphenated:{d.fr}",
                    rel,
                    f"{d.fr} (line {d.line}) is defined without the hyphen — the family is `FR-n` / `NFR-n` "
                    "(CHAIN-STANDARD § 6)",
                    fr=d.fr,
                    line=d.line,
                    station=station,
                )
            )
        elif d.kind == "malformed":
            out.append(
                _fr_fail(
                    "fr-id-malformed",
                    f"fr-id-malformed:{d.fr}",
                    rel,
                    f"{d.fr} (line {d.line}) is defined under an id outside the family — one of "
                    "`FR-n`, `NFR-n`, `FR-n.m`, `NFR-Xn` (CHAIN-STANDARD § 6, § 12)",
                    fr=d.fr,
                    line=d.line,
                    station=station,
                )
            )
    first_line = {d.fr: d.line for d in defs}
    for fr, dup_lines in duplicates.items():
        out.append(
            _fr_fail(
                "fr-duplicate-id",
                f"fr-duplicate-id:{fr}",
                rel,
                f"{fr} is defined again at line{'s' if len(dup_lines) > 1 else ''} "
                f"{', '.join(map(str, dup_lines))} (first at line {first_line.get(fr, '?')}) — one id, one "
                "definition; a later mention is a reference, not a second definition",
                fr=fr,
                line=first_line.get(fr),
                duplicate_lines=dup_lines,
                station=station,
            )
        )
    for run in _counted_runs(defs, slug, specs):
        first, last = run[0], run[-1]
        fr_range = f"{first.fr}..{last.fr}"
        cap_range = f"CAP-{first.cites[0][1]}..CAP-{last.cites[0][1]}"
        out.append(
            _fr_fail(
                "fr-counted-run",
                f"fr-counted-run:{fr_range}",
                rel,
                f"{fr_range} (lines {first.line}–{last.line}) cite {cap_range} in lockstep and no FR shares a "
                "content word with its CAP's title — arrows are derived from the Spec, never counted onto it",
                fr_range=fr_range,
                cap_range=cap_range,
                frs=[d.fr for d in run],
                station=station,
            )
        )
    return out


def _no_title_overlap(defs: list[_FrDef], slug: str, specs: _SpecIndex) -> list[str]:
    """FR ids whose text shares no content word with the union of their
    cited CAPs' title, intent and success text (advisory)."""
    out: list[str] = []
    for d in defs:
        words = _content_words(d.text)
        if not words or not d.cites:
            continue
        cap_words: set[str] = set()
        resolved = False
        for cite in d.cites:
            cap, _ = specs.resolve(slug, cite)
            if cap is not None:
                resolved = True
                cap_words |= _content_words(f"{cap.title} {cap.intent} {cap.success}")
        if resolved and not (words & cap_words):
            out.append(d.fr)
    return out


@dataclass(frozen=True)
class _PrdMeasure:
    rel: str
    defs: list[_FrDef]
    structural: list[Finding]
    no_overlap: list[str]


def _measure_station(target: Path, project_dir: Path, specs: _SpecIndex) -> tuple[list[_PrdMeasure], list[str]]:
    """``(measures, unreadable)`` -- one measure per readable PRD, and the
    repo-relative paths of the PRDs that could not be read."""
    slug = project_dir.name
    out: list[_PrdMeasure] = []
    unreadable: list[str] = []
    for prd in _prd_files(project_dir):
        rel = prd.relative_to(target).as_posix()
        try:
            text = prd.read_text(encoding="utf-8")
        except OSError, UnicodeDecodeError:
            unreadable.append(rel)
            continue
        defs, duplicates = _fr_definitions(text)
        out.append(
            _PrdMeasure(
                rel=rel,
                defs=defs,
                structural=_structural_findings(rel, slug, defs, duplicates, specs),
                no_overlap=_no_title_overlap(defs, slug, specs),
            )
        )
    return out, unreadable


def _station_dirs(target: Path) -> list[Path]:
    pdir = target / _PROJECTS_REL
    return sorted(pdir.glob("pyforge-*")) if pdir.is_dir() else []


_FR_BASELINE_COMMENT = [
    "fr-without-cap baseline (doctor Stories 25.2 and 50.1, spec-one-chain-per-station CAP-5).",
    "`projects`: per station, the FR/NFR ids whose definition carried NO citation when snapshotted --",
    "a missing arrow on an id listed here is never a finding; an id with an arrow is enforced forever,",
    "so the list only shrinks (`--project pyforge-<s>` re-snapshots one station at its fold PR).",
    "`findings`: per station, the structural findings (`<check>:<FR-id>`) present at `findings_sha` --",
    "reported as fr-baselined, never FAIL. Either entry that stopped applying is WARN fr-baseline-stale",
    "until `--prune` (the only routine verb) removes it. `--snapshot-findings` is a one-time act: it is",
    "refused once `findings` exists, and `--force` is for a review that names each ADDED key in its PR.",
    "`owners`: hand-maintained -- the story that owns what each station still carries here.",
    "`forced`: written by scripts/fr_baseline.py alone -- each `projects` id or `findings` key it ADDED",
    "and the HEAD it ran at. A key added since the merge-base with origin/main that no `forced` record",
    "names is FAIL fr-baseline-grown (doctor Story 50.2): an `owners` row never admits one.",
]
_FR_BASELINE_CARRIED = ("rebaselined", "owners", "findings_sha", "findings", "forced")
_FR_RATCHETED = ("projects", "findings")  # the two maps that only shrink


def snapshot_fr_baseline(
    target: Path, *, ruling_sha: str, only_project: str | None = None, existing: dict | None = None
) -> dict:
    """Per-station arrowless FR population. With ``only_project`` set, every
    other station's entry is carried over from ``existing`` untouched -- a
    fold PR re-baselines its own station only. ``owners``, the ``findings``
    map and its SHA are carried over as they are."""
    projects: dict[str, list[str]] = {}
    if existing and isinstance(existing.get("projects"), dict):
        projects.update({k: list(v) for k, v in existing["projects"].items()})
    specs = _SpecIndex(target)
    for project_dir in _station_dirs(target):
        slug = project_dir.name
        if only_project and slug != only_project:
            continue
        measures, _unreadable = _measure_station(target, project_dir, specs)
        projects[slug] = sorted({d.fr for m in measures for d in m.defs if d.arrowless}, key=_fr_sort_key)
    data: dict = {"$comment": _FR_BASELINE_COMMENT, "ruling_sha": ruling_sha, "projects": projects}
    for key in _FR_BASELINE_CARRIED:
        if existing and key in existing:
            data[key] = existing[key]
    return data


def snapshot_fr_findings(target: Path) -> dict[str, list[str]]:
    """``{pyforge-<s>: [key, ...]}`` -- every structural finding firing now."""
    specs = _SpecIndex(target)
    out: dict[str, list[str]] = {}
    for project_dir in _station_dirs(target):
        measures, _unreadable = _measure_station(target, project_dir, specs)
        out[project_dir.name] = sorted({f.evidence["key"] for m in measures for f in m.structural})
    return out


def prune_fr_baseline(target: Path) -> tuple[dict | None, list[str]]:
    """Drop ``projects`` ids that are no longer arrowless definitions and
    ``findings`` keys that no longer fire. Returns the new baseline (or
    ``None`` when unreadable) and the removed entries. Never adds; a station
    with an unreadable PRD is left untouched."""
    data = _read_json(target / FR_BASELINE_REL)
    if data is None or not isinstance(data.get("projects"), dict):
        return None, []
    removed: list[str] = []
    specs = _SpecIndex(target)
    arrowless: dict[str, set[str]] = {}
    firing: dict[str, set[str]] = {}
    skipped: set[str] = set()
    for project_dir in _station_dirs(target):
        measures, unreadable = _measure_station(target, project_dir, specs)
        if unreadable:
            skipped.add(project_dir.name)
            continue
        arrowless[project_dir.name] = {d.fr for m in measures for d in m.defs if d.arrowless}
        firing[project_dir.name] = {f.evidence["key"] for m in measures for f in m.structural}
    for slug, ids in data["projects"].items():
        if slug in skipped:
            continue
        kept = [fr for fr in ids if fr in arrowless.get(slug, set())]
        removed.extend(f"{slug}: {fr}" for fr in ids if fr not in arrowless.get(slug, set()))
        data["projects"][slug] = kept
    if isinstance(data.get("findings"), dict):
        for slug, keys in data["findings"].items():
            if slug in skipped:
                continue
            kept = [k for k in keys if k in firing.get(slug, set())]
            removed.extend(f"{slug}: {k}" for k in keys if k not in firing.get(slug, set()))
            data["findings"][slug] = kept
    if "forced" in data:
        # A record that outlived its key would admit a later hand re-add of it (Story 50.2).
        present = set(_fr_baseline_growth({}, data))  # every key the pruned file holds
        records = _forced_records(data)
        removed.extend(
            f"{r['station']}: forced {r['kind']} {r['key']}"
            for r in records
            if (r["station"], r["kind"], r["key"]) not in present
        )
        data["forced"] = [r for r in records if (r["station"], r["kind"], r["key"]) in present]
    return data, removed


# Story 50.2 (spec-pyforge-doctor CAP-92, EGM audit DOC-M-D1) -- the ratchet is
# enforced against the merge-base, not asserted inside the script: a `projects`
# id or `findings` key added since `merge-base(HEAD, refs/remotes/origin/main)`
# is `fr-baseline-grown` (FAIL) unless the file's `forced` list -- written by
# `scripts/fr_baseline.py` alone, through `record_fr_additions` -- names it. An
# `owners` row never admits one: `owners` is edited by hand. A base that cannot
# be read is `fr-baseline-base-unread` (WARN), never a FAIL.


def _forced_records(data: dict) -> list[dict]:
    """The well-formed ``forced`` records of a baseline; a malformed one admits nothing."""
    raw = data.get("forced")
    if not isinstance(raw, list):
        return []
    return [
        r for r in raw if isinstance(r, dict) and all(isinstance(r.get(f), str) for f in ("station", "kind", "key"))
    ]


def _fr_baseline_growth(base: dict, head: dict) -> list[tuple[str, str, str]]:
    """``(station, kind, key)`` for every ``projects`` id or ``findings`` key in
    ``head`` that ``base`` lacks -- the one definition of growth, shared by
    ``fr-baseline-grown`` and :func:`record_fr_additions`. A removed key is never
    growth. Pure."""
    grown: list[tuple[str, str, str]] = []
    for kind in _FR_RATCHETED:
        raw_before, raw_after = base.get(kind), head.get(kind)
        before: dict = raw_before if isinstance(raw_before, dict) else {}
        after: dict = raw_after if isinstance(raw_after, dict) else {}
        for slug in sorted(after):
            keys = after[slug]
            if not isinstance(keys, list):
                continue
            prior = before.get(slug)
            prior_keys = {k for k in prior if isinstance(k, str)} if isinstance(prior, list) else set()
            grown.extend((slug, kind, key) for key in keys if isinstance(key, str) and key not in prior_keys)
    return grown


def record_fr_additions(previous: dict | None, data: dict, head: str) -> list[tuple[str, str, str]]:
    """Record, in ``data["forced"]``, each key ``data`` adds over ``previous`` (the
    file ``scripts/fr_baseline.py`` read) with the run's ``head`` -- the one escape
    ``fr-baseline-grown`` admits -- and drop a record whose key ``data`` no longer
    holds, so it cannot admit a later hand re-add. Returns the keys it recorded.
    No previous file, no record: nothing was added to one, and the detector warns
    that the base lacks it. Pure."""
    if previous is None:
        return []
    present = set(_fr_baseline_growth({}, data))  # every key `data` holds
    records = [r for r in _forced_records(data) if (r["station"], r["kind"], r["key"]) in present]
    have = {(r["station"], r["kind"], r["key"]) for r in records}
    added = [g for g in _fr_baseline_growth(previous, data) if g not in have]
    records.extend({"station": slug, "kind": kind, "key": key, "head": head} for slug, kind, key in added)
    if records or "forced" in data:
        data["forced"] = records
    return added


def _base_fr_baseline(target: Path) -> tuple[dict, str] | str:
    """``fr-baseline.json`` at ``merge-base(HEAD, refs/remotes/origin/main)`` and that
    sha, or the cause it cannot be read. Through ``cli_bridge.run_git`` alone (AD-5),
    by the full refname, never a fetch: a stale remote-tracking ref can only hide
    growth that is already on main. On main itself the merge-base is ``HEAD``."""
    rel = FR_BASELINE_REL.as_posix()
    if not (target / ".git").exists():
        return f"{target} is not the top of a git checkout"
    try:
        run_git(target, ["rev-parse", "--verify", "--quiet", f"{ORIGIN_MAIN}^{{commit}}"])
    except CliBridgeError:
        return f"no {ORIGIN_MAIN} in this checkout"
    try:
        sha = run_git(target, ["merge-base", "HEAD", ORIGIN_MAIN]).strip()
    except CliBridgeError as exc:
        return f"HEAD and {display_ref(ORIGIN_MAIN)} have no merge-base (a shallow clone or unrelated histories): {exc}"
    try:
        blob = run_git(target, ["show", f"{sha}:{rel}"])
    except CliBridgeError as exc:
        return f"{rel} is absent at the merge-base {sha[:10]}: {exc}"
    try:
        data = json.loads(blob)
    except json.JSONDecodeError as exc:
        return f"{rel} is not JSON at the merge-base {sha[:10]}: {exc}"
    if not isinstance(data, dict):
        return f"{rel} is not a JSON object at the merge-base {sha[:10]}"
    return data, sha


def _grown(slug: str, kind: str, key: str, merge_base: str) -> Finding:
    what = "`projects` id" if kind == "projects" else "`findings` key"
    return Finding(
        source=Source.FR_WITHOUT_CAP,
        check="fr-baseline-grown",
        status=DoctorStatus.FAIL,
        message=(
            f"{slug}: baseline {what} `{key}` was added since the merge-base {merge_base[:10]} with origin/main "
            "and no `forced` record names it — the baseline only shrinks: drop it, or add it with "
            "`python scripts/fr_baseline.py … --force` after a review that names it (an `owners` row never admits one)"
        ),
        evidence={"station": slug.removeprefix("pyforge-"), "kind": kind, "key": key, "merge_base": merge_base},
    )


def _base_unread(cause: str) -> Finding:
    return Finding(
        source=Source.FR_WITHOUT_CAP,
        check="fr-baseline-base-unread",
        status=DoctorStatus.WARN,
        message=(
            f"{FR_BASELINE_REL.as_posix()} was not compared with its merge-base with origin/main — {cause}; "
            "a hand-added baseline key cannot be told from one scripts/fr_baseline.py added"
        ),
        evidence={"baseline": FR_BASELINE_REL.as_posix(), "base": display_ref(ORIGIN_MAIN), "cause": cause},
    )


def gather_fr_without_cap(target: Path) -> tuple[Finding, ...]:
    """A product requirement names its source CAP, and nothing else."""
    return degrade_on_exception(Source.FR_WITHOUT_CAP, "fr-without-cap", lambda: _gather_fr_without_cap(target))


def _stale(slug: str, kind: str, key: str) -> Finding:
    what = "`projects` id" if kind == "projects" else "`findings` key"
    why = "now carries an arrow or is no longer defined" if kind == "projects" else "no longer fires"
    return Finding(
        source=Source.FR_WITHOUT_CAP,
        check="fr-baseline-stale",
        status=DoctorStatus.WARN,
        message=f"{slug}: baseline {what} `{key}` {why} — prune it (`python scripts/fr_baseline.py --prune`)",
        evidence={"station": slug.removeprefix("pyforge-"), "kind": kind, "key": key},
    )


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
    known_findings: dict[str, set[str]] = {}
    if isinstance(baseline.get("findings"), dict):
        known_findings = {k: set(v) for k, v in baseline["findings"].items() if isinstance(v, list)}
    findings: list[Finding] = []
    base = _base_fr_baseline(target)
    if isinstance(base, str):
        findings.append(_base_unread(base))
    else:
        base_data, merge_base = base
        forced = {(r["station"], r["kind"], r["key"]) for r in _forced_records(baseline)}
        for slug, kind, key in _fr_baseline_growth(base_data, baseline):
            if (slug, kind, key) in forced:
                continue
            # A grown key hides nothing: the finding it would have hidden still fires.
            (known if kind == "projects" else known_findings).get(slug, set()).discard(key)
            findings.append(_grown(slug, kind, key, merge_base))
    specs = _SpecIndex(target)
    counts: dict[str, dict[str, int]] = {}
    measured_new = 0
    no_overlap: dict[str, list[str]] = {}
    for project_dir in _station_dirs(target):
        slug = project_dir.name
        station = slug.removeprefix("pyforge-")
        base_ids = known.get(slug, set())
        spec_folder = f"{_PROJECTS_REL.as_posix()}/{slug}/planning-artifacts/specs/spec-{slug}/"
        fired: set[str] = set()
        arrowless_ids: set[str] = set()
        baselined: list[str] = []
        station_counts = {"definitions": 0, "cited": 0, "arrowless": 0, "new": 0}
        measures, unreadable = _measure_station(target, project_dir, specs)
        for rel in unreadable:
            findings.append(
                Finding(
                    source=Source.FR_WITHOUT_CAP,
                    check="fr-prd-unreadable",
                    status=DoctorStatus.WARN,
                    message=f"{rel} cannot be read — {station}'s requirements were not measured",
                    evidence={"prd": rel, "station": station},
                )
            )
        for m in measures:
            station_counts["definitions"] += len(m.defs)
            station_counts["cited"] += sum(d.cited for d in m.defs)
            station_counts["arrowless"] += sum(d.arrowless for d in m.defs)
            arrowless_ids.update(d.fr for d in m.defs if d.arrowless)
            for d in m.defs:
                if d.fr in base_ids:
                    continue
                measured_new += 1  # enforced: not in the arrowless population
                station_counts["new"] += 1
                if not d.arrowless:
                    continue
                findings.append(
                    Finding(
                        source=Source.FR_WITHOUT_CAP,
                        check="fr-without-cap",
                        status=DoctorStatus.FAIL,
                        message=(
                            f"{m.rel}: {d.fr} (line {d.line}) was minted after the rule date and cites no "
                            f"source capability — write `{d.fr} ← CAP-m` against "
                            f"{station}'s Spec (CHAIN-STANDARD § 2)"
                        ),
                        evidence={
                            "prd": m.rel,
                            "fr": d.fr,
                            "line": d.line,
                            "station": station,
                            "spec_folder": spec_folder,
                        },
                    )
                )
            for f in m.structural:
                key = f.evidence["key"]
                fired.add(key)
                station_counts[f.check] = station_counts.get(f.check, 0) + 1
                if key in known_findings.get(slug, set()):
                    baselined.append(key)
                else:
                    findings.append(f)
            if m.no_overlap:
                no_overlap.setdefault(slug, []).extend(m.no_overlap)
        counts[slug] = station_counts
        if baselined:
            findings.append(
                Finding(
                    source=Source.FR_WITHOUT_CAP,
                    check="fr-baselined",
                    status=DoctorStatus.OK,
                    message=(
                        f"{slug}: {len(baselined)} arrow-grammar finding(s) listed in "
                        f"{FR_BASELINE_REL.as_posix()} `findings` (not FAIL): {', '.join(sorted(baselined))}"
                    ),
                    evidence={"station": station, "keys": sorted(baselined)},
                )
            )
        if not unreadable:
            findings.extend(_stale(slug, "projects", fr) for fr in sorted(base_ids - arrowless_ids, key=_fr_sort_key))
            findings.extend(_stale(slug, "findings", key) for key in sorted(known_findings.get(slug, set()) - fired))
    total_no_overlap = sum(len(v) for v in no_overlap.values())
    for slug, frs in sorted(no_overlap.items()):
        findings.append(
            Finding(
                source=Source.FR_WITHOUT_CAP,
                check="fr-arrow-no-title-overlap",
                status=DoctorStatus.WARN,
                message=(
                    f"{slug}: {len(frs)} FR(s) share no content word with the CAP(s) they cite "
                    f"(title, intent and success text) — advisory, read each arrow: {', '.join(frs)}"
                ),
                evidence={"station": slug.removeprefix("pyforge-"), "frs": frs, "fleet_total": total_no_overlap},
            )
        )
    if not any(f.status is DoctorStatus.FAIL for f in findings):
        findings.append(
            Finding(
                source=Source.FR_WITHOUT_CAP,
                check="fr-without-cap",
                status=DoctorStatus.OK,
                message=(
                    f"every FR minted since {baseline.get('ruling_sha', '?')} cites a resolving CAP and "
                    f"nothing else ({measured_new} enforced of "
                    f"{sum(c['definitions'] for c in counts.values())} definition(s) measured)"
                ),
                evidence={
                    "ruling_sha": baseline.get("ruling_sha"),
                    "findings_sha": baseline.get("findings_sha"),
                    "new_frs": measured_new,
                    "counts": counts,
                },
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
