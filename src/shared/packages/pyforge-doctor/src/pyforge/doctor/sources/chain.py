"""The chain-verdicts gather filters -- Doctor's verdict on the Dream-to-Code
chain every station shares (Story 6.6, FR-15).

**Why this module exists, and why it is HERE rather than in ``pyforge.marshal``.**

Charter §6, ratified 2026-07-28: *"the Doctor holds the verdict on the Marshal's
own conformance -- the one station that would otherwise grade itself."* Three
read-only judges of the chain every station's planning artifacts travel through
grew up OUTSIDE Doctor as repo-root scripts: ``scripts/dream_chain_check.py``
(does every Dream have a Spec, in its owner's project, using the sharded build
tree?), ``scripts/spec_surface_check.py`` (is every tracked file governed by a
spec surface or an allowlist entry, and has a governed file drifted out from
under its spec's contract?) and ``scripts/deferred_work_check.py`` (does every
Tier-3 deferred-work id have a durable, tracked twin?). Stories 6.4 and 6.5
proved the ledger and board port patterns; this module is the chain's turn,
porting all three verbatim in behavior.

``spec-regenerable-factory`` and ``spec-surface-drift-reconciliation`` are
Marshal Specs, and the deferred-work refile mechanism this module's third
gather guards belongs to bmad-loop, Marshal's own orchestrator -- so, like
Stories 6.4/6.5's own Marshal-produced artifacts, ``subject_station="marshal"``
for all three (``sources/__init__.py``'s ``REGISTRY``).

**The independence rule, which is the entire point of this module:**

    This module reads the DURABLE ARTIFACTS -- tracked Dreams, Specs, planning
    trees, ``git ls-files``, and the tracked deferred-work ledgers -- and never
    imports ``pyforge.marshal`` (or any other station package).

Mirrors ``sources/ledger.py``'s and ``sources/board.py``'s own independence
rationale exactly: a chain verdict assembled from Marshal's own code would be
Marshal's self-report wearing Doctor's badge, and would fail in exactly the
case that matters -- when Marshal's own machinery is what broke.
``tests/unit/test_sources_chain_independence.py`` pins it.

**Degrades, never crashes** -- the house rule for every Doctor source. Each of
the three gathers below is wrapped in ``sources.degrade_on_exception`` as an
outer safety net, ON TOP OF per-unit isolation inside each gather's own loop:
a per-Dream/per-Spec/per-project failure degrades to one WARN item WITHOUT
discarding every other unit's already-computed FAIL/OK finding -- the lesson
Stories 6.4 and 6.5 each needed three-plus review passes to converge on
(``sources/board.py``'s own module docstring), structured in here from the
first draft rather than rediscovered a fourth time (Design Notes).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path, PurePosixPath

import yaml

from ..cli_bridge import CliBridgeError, run_git
from ..models import DoctorStatus, Finding, Source
from . import degrade_on_exception

__all__ = (
    "gather_dream_chain",
    "gather_deferred_work",
    "gather_spec_surface",
    "gather_due_for_verification",
    "Tier3Shape",
    "LegacyEntry",
    "classify_tier3_entries",
    "mint_id_for_entry",
)


# === gather_dream_chain =======================================================
#
# Ported from scripts/dream_chain_check.py -- see that script's own module
# docstring for the full four-invariant rationale (INV-0 every Spec declares
# owner-dream, INV-1 every Dream has a Spec, INV-2 the chain follows the owner,
# INV-3 the 6.10 sharded planning tree).

#: The constitutive Dream (Charter §5): owned by `guild` and terminal there --
#: verbatim from the original (see its own comment for the 2026-08-02 merge
#: history this set survived).
CONSTITUTIVE = frozenset({"pyforge-charter"})

#: Sentinel `project` value for a Dream/Spec owned by `guild` -- verbatim.
GOVERNANCE_PROJECT = "docs/governance"

_SATELLITE_RE = re.compile(r"^#{2,3}\s+Satellite:\s*(.+?)\s*$", re.MULTILINE)
_NORMALIZE_RE = re.compile(r"[^a-z0-9 ]")


def _normalize_title(title: str) -> str:
    """Lowercased, punctuation-stripped -- verbatim from the original, so a
    Dream's own ``title:`` can be matched against a consolidating Spec's
    ``## Satellite: <Title>`` heading regardless of exact wording drift."""
    return _NORMALIZE_RE.sub("", title.lower()).strip()


def _frontmatter(path: Path) -> dict:
    """The frontmatter block, parsed with ``yaml.safe_load`` -- already the
    original's own parser (Boundaries), unlike ``sources/board.py``'s
    deliberately hand-rolled reader.

    Never raises: a missing file, an unreadable one, non-UTF-8 bytes, or
    unparseable YAML all degrade to ``{}``, mirroring the original's own
    ``except Exception: return {}``. One addition beyond the original: a
    frontmatter block that parses to something OTHER than a mapping (a bare
    scalar or a list -- valid YAML, wrong shape) also degrades to ``{}``
    rather than raising ``AttributeError`` on the first ``.get()`` call a
    caller makes -- the same "structurally wrong but valid" class
    ``sources/board.py``'s own ``_board_lines`` already guards against.
    """
    try:
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---"):
            return {}
        data = yaml.safe_load(text.split("---")[1])
    except Exception:  # noqa: BLE001 -- mirrors the original's own broad
        # except (scripts/dream_chain_check.py's frontmatter()).
        return {}
    return data if isinstance(data, dict) else {}


def _satellite_titles(path: Path) -> set[str]:
    """Titles named by a ``## Satellite: <Title>`` heading in a consolidating
    Spec's body -- verbatim from the original, widened from ``except OSError``
    to ``except Exception``: a non-UTF-8 byte raises ``UnicodeDecodeError`` (a
    ``ValueError``), which ``OSError`` alone would not catch, and this
    function must degrade rather than raise (Boundaries; the same class of
    narrow-catch defect ``sources/board.py``'s own docstring records having
    to close across three review passes)."""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001 -- see the docstring above.
        return set()
    return {
        norm
        for m in _SATELLITE_RE.finditer(text)
        if (norm := _normalize_title(m.group(1)))
    }


def _expected_project(owner: str) -> str:
    """Project for a Dream/Spec owner -- verbatim from the original.
    ``guild`` -> ``docs/governance`` (the constitutive home); every other
    owner -> ``pyforge-<owner>``."""
    return GOVERNANCE_PROJECT if owner == "guild" else f"pyforge-{owner}"


def _expected_spec_dir(owner: str, slug: str) -> str:
    """Full expected Spec directory for a Dream -- verbatim from the
    original. ``docs/governance/`` holds ``spec-<slug>/`` directly (no
    Smith-shaped ``planning-artifacts/specs/`` nesting); every other project
    does."""
    project = _expected_project(owner)
    if project == GOVERNANCE_PROJECT:
        return f"{GOVERNANCE_PROJECT}/spec-{slug}/"
    return f"{project}/planning-artifacts/specs/spec-{slug}/"


def _listdir(d: Path) -> list[Path]:
    """A directory's entries, sorted, RAISING on an unreadable directory.

    ``Path.glob`` swallows ``OSError`` mid-traversal and simply yields
    nothing, so an unreadable input directory is indistinguishable from an
    empty one -- and "empty" reads as a clean chain, i.e. a confident OK for
    a question that could not actually be asked (reproduced live during
    review: ``chmod 000 docs/dreams/`` turned a real ``dream-without-spec``
    FAIL into ``dream-chain ok``). ``iterdir`` raises instead, so every
    collection site below lists through here and lets the module's own
    per-unit isolation turn the failure into an honest WARN."""
    return sorted(d.iterdir())


def _probe(p: Path) -> os.stat_result | None:
    """``p.stat()``, or ``None`` when ``p`` genuinely does not exist --
    RAISING when the answer cannot be determined.

    ``Path.is_dir()``/``Path.is_file()`` swallow EVERY ``OSError`` and answer
    ``False``, so an unreadable input is indistinguishable from an absent one
    -- and absent reads as clean. That is the same false-clean class
    ``_listdir`` above closes for LISTING a directory, left open for the
    EXISTENCE PROBES that decide whether to list it at all. Reproduced live
    during review, three ways: ``chmod 000 docs/`` (the PARENT of
    ``docs/dreams/``) silently zeroed every Dream and a real
    ``dream-without-spec`` FAIL vanished with no WARN; ``chmod 000`` on a
    project's ``implementation-artifacts/`` turned two real deferred-work
    FAILs into a confident ``deferred-work ok``; and an unreadable
    ``planning-artifacts/specs/spec-<slug>/`` silently un-governed that
    spec's whole surface -- the exact silent-governance-loss defect
    ``_parse_surface``'s own docstring exists to prevent, one directory
    level up.

    ``stat`` needs no read permission on the target itself, only on its
    parent, so a ``chmod 000`` FILE still probes as a regular file (matching
    ``is_file()``); only an unreadable ANCESTOR raises, which is precisely
    the case that must not be answered ``False``."""
    try:
        return p.stat()
    except (FileNotFoundError, NotADirectoryError):
        return None


def _is_dir(p: Path) -> bool:
    """``p.is_dir()`` that raises rather than lying -- see ``_probe``."""
    st = _probe(p)
    return st is not None and stat.S_ISDIR(st.st_mode)


def _is_file(p: Path) -> bool:
    """``p.is_file()`` that raises rather than lying -- see ``_probe``."""
    st = _probe(p)
    return st is not None and stat.S_ISREG(st.st_mode)


def _collect_dreams(target: Path, findings: list[dict]) -> dict[str, dict]:
    """``{slug: {owner, status, title}}`` for every tracked Dream -- verbatim
    from the original's own ``collect()``, except every value is COERCED to
    ``str`` at this collection boundary.

    ``_frontmatter`` degrades a block that fails to PARSE, and its own
    ``isinstance(data, dict)`` guard degrades a block of the wrong TOP-LEVEL
    shape -- but neither catches a key that parses cleanly to the wrong VALUE
    shape. ``title:`` with no value is YAML ``null`` and ``title: 2026`` is an
    ``int``; both reach ``_normalize_title``'s ``.lower()`` in
    ``_check_dream_chain``'s satellite loop, which runs over ALREADY-COLLECTED
    in-memory data and therefore sits outside every per-unit try/except in
    this module. The ``AttributeError`` escapes to the outer
    ``degrade_on_exception`` and replaces every already-computed Dream/Spec
    FAIL with one vacuous WARN -- the identical failure class review found for
    Specs (``_collect_specs``) and the one this story's Design Notes said to
    structure out rather than rediscover. Coercing here fixes it for every
    downstream consumer at once, instead of guarding each use site.

    Note the coercion is a deliberate, documented DIVERGENCE from the
    original rather than a byte-verbatim port: PyYAML resolves an unquoted
    ``owner: no`` to ``False``, which the original preserved and this
    collection boundary renders ``""``. The values it changes are exactly the
    ones the original could not have used safely anyway.

    Unreadable ``docs/dreams/`` (or an unreadable ancestor of it) degrades to
    a WARN appended to the CALLER's ``findings`` list and an EMPTY dream set,
    never to a raise: ``_listdir``'s ``PermissionError`` used to escape this
    function entirely, past ``_check_dream_chain``, to the outer
    ``degrade_on_exception`` -- replacing every INV-3 finding (which does not
    read ``docs/dreams/`` at all) with one vacuous WARN. Reproduced live
    during review: four real FAILs collapsed to one."""
    dreams: dict[str, dict] = {}
    dreams_dir = target / "docs" / "dreams"
    try:
        if not _is_dir(dreams_dir):
            return dreams
        entries = _listdir(dreams_dir)
    except OSError as exc:
        findings.append(_unreadable_input(
            "INV-1", "docs/dreams",
            f"docs/dreams/ could not be read here — "
            f"{exc.__class__.__name__}: {exc}; no Dream is evaluable",
            "make docs/dreams/ readable, then re-check",
        ))
        return dreams
    for p in entries:
        if p.suffix != ".md" or p.name == "README.md":
            continue
        fm = _frontmatter(p)
        dreams[p.stem] = {
            "owner": str(fm.get("owner") or ""),
            "status": str(fm.get("status") or ""),
            "title": str(fm.get("title") or ""),
        }
    return dreams


def _spec_entry(sp: Path, project: str, target: Path) -> dict:
    """One Spec's collected fields -- verbatim from the original's own
    ``collect()`` (both the per-project and the governance loop build this
    same shape)."""
    fm = _frontmatter(sp)
    return {
        "project": project,
        "spec": sp.parent.name,
        "dream": (fm.get("owner-dream") or "").split("/")[-1].removesuffix(".md"),
        # `covers-dreams:` -- a consolidating Spec's explicit declaration that
        # it also satisfies INV-1 for OTHER Dreams whose whole chain was
        # folded in here (2026-08-02 satellite-consolidation convention).
        "covers": [
            (c or "").split("/")[-1].removesuffix(".md")
            for c in (fm.get("covers-dreams") or [])
        ],
        "satellite_titles": _satellite_titles(sp),
        "path": str(sp.relative_to(target)),
    }


def _collect_specs(target: Path, findings: list[dict]) -> list[dict]:
    """Every tracked Spec (project-owned + governance-owned) -- verbatim from
    the original's own ``collect()``, except each Spec is built inside its
    own try/except before being appended to the returned list.

    ``_frontmatter`` degrades a block that fails to PARSE, but not one that
    parses fine to the WRONG SHAPE -- ``owner-dream:`` written as a YAML list
    (a plausible typo next to the legitimately-list-shaped
    ``covers-dreams:``) parses cleanly and then raises ``AttributeError`` out
    of ``_spec_entry``'s own ``.split("/")`` call. Without per-spec isolation
    that escapes ALL the way out of this function, past ``_check_dream_chain``,
    to the outer ``degrade_on_exception`` -- replacing every already-collected
    Dream/Spec finding with one vacuous WARN (reproduced live during review).
    One bad Spec's malformed frontmatter now degrades to a WARN appended to
    the CALLER's ``findings`` list for THAT spec only, mirroring
    ``_sharded_findings``'s own per-project isolation.

    Every filesystem probe below goes through ``_is_dir``/``_is_file`` rather
    than ``Path``'s own, which answer ``False`` for an unreadable ancestor:
    an unreadable ``spec-<slug>/`` directory silently dropped the Spec and
    INV-1 then reported its Dream ``dream-without-spec`` -- a confidently
    wrong FAIL about a Spec that is right there, with no WARN. The two
    ``_listdir`` roots (the projects tree, ``docs/governance/``) are isolated
    for the same reason ``_collect_dreams`` is: an unreadable one must not
    discard every OTHER unit's already-computed finding."""
    specs: list[dict] = []
    projects_dir = target / "_bmad-output" / "projects"
    try:
        project_dirs = _listdir(projects_dir) if _is_dir(projects_dir) else []
    except OSError as exc:
        findings.append(_unreadable_input(
            "INV-0", "_bmad-output/projects",
            f"_bmad-output/projects/ could not be read here — "
            f"{exc.__class__.__name__}: {exc}; no Spec is evaluable",
            "make _bmad-output/projects/ readable, then re-check",
        ))
        project_dirs = []
    for pdir in project_dirs:
        specs_dir = pdir / "planning-artifacts" / "specs"
        try:
            if not _is_dir(specs_dir):
                continue
            spec_dirs = _listdir(specs_dir)
            readable = [sd for sd in spec_dirs if _is_file(sd / "SPEC.md")]
        except OSError as exc:
            # One project's unreadable specs/ directory must not silently
            # read as "this project has no Specs" (which INV-1 would then
            # report as every one of its Dreams being spec-less).
            findings.append(_unreadable_specs_dir(pdir.name, exc))
            continue
        for sd in readable:
            _append_spec_entry(sd / "SPEC.md", pdir.name, target, specs, findings)
    governance_dir = target / "docs" / "governance"
    try:
        gov_dirs = _listdir(governance_dir) if _is_dir(governance_dir) else []
        gov_specs = [sd / "SPEC.md" for sd in gov_dirs
                     if sd.name.startswith("spec-") and _is_file(sd / "SPEC.md")]
    except OSError as exc:
        findings.append(_unreadable_input(
            "INV-0", GOVERNANCE_PROJECT,
            f"docs/governance/ could not be read here — "
            f"{exc.__class__.__name__}: {exc}; no guild Spec is evaluable",
            "make docs/governance/ readable, then re-check",
        ))
        gov_specs = []
    for sp in gov_specs:
        _append_spec_entry(sp, GOVERNANCE_PROJECT, target, specs, findings)
    return specs


def _unreadable_input(inv: str, subject: str, detail: str, remedy: str) -> dict:
    """The WARN item for one whole input TREE that could not be read -- the
    root-level counterpart to ``_unreadable_specs_dir``/``_append_spec_entry``'s
    own per-unit WARNs. Isolated rather than left to raise so an unreadable
    ``docs/dreams/`` cannot discard the INV-3 findings that never touch it."""
    return {
        "inv": inv, "kind": "dream-chain-unevaluable", "subject": subject,
        "owner": "", "status": "", "remedy": remedy,
        "detail": detail, "warn": True,
    }


def _unreadable_specs_dir(project: str, exc: Exception) -> dict:
    """The WARN item for one project whose ``planning-artifacts/specs/``
    could not be read -- same shape as ``_append_spec_entry``'s own per-spec
    WARN, one level up. ``subject`` is the PROJECT, not the directory's own
    name: every project's specs dir is literally called ``specs``, so keying
    on that made two projects' WARNs indistinguishable to a machine
    consumer."""
    return {
        "inv": "INV-0", "kind": "dream-chain-unevaluable",
        "subject": project, "owner": "", "status": f"in {project}",
        "remedy": "make the project's planning-artifacts/specs/ readable, then re-check",
        "detail": (f"{project}: planning-artifacts/specs/ could not be read "
                   f"here — {exc.__class__.__name__}: {exc}"),
        "warn": True,
    }


def _append_spec_entry(
    sp: Path, project: str, target: Path, specs: list[dict], findings: list[dict]
) -> None:
    """Append one Spec's collected fields to the CALLER's ``specs`` list, or
    -- on any failure building it -- a WARN finding to the CALLER's
    ``findings`` list instead, never both and never neither. Split out so
    ``_collect_specs``'s two loops (project-owned, governance-owned) share
    one isolation site (see ``_collect_specs``'s own docstring for why this
    exists)."""
    try:
        specs.append(_spec_entry(sp, project, target))
    except Exception as exc:  # noqa: BLE001 -- one spec's malformed
        # owner-dream/covers-dreams value must not discard every other
        # already-collected Dream/Spec finding.
        findings.append({
            "inv": "INV-0", "kind": "dream-chain-unevaluable",
            "subject": sp.parent.name, "owner": "", "status": f"in {project}",
            "remedy": (
                "fix the malformed owner-dream/covers-dreams frontmatter "
                "value, then re-check"
            ),
            "detail": (f"{sp.parent.name} in {project}: could not be "
                       f"evaluated here — {exc.__class__.__name__}: {exc}"),
            "warn": True,
        })


def _check_project_sharded(pdir: Path, findings: list[dict]) -> None:
    """Append one project's INV-3 findings to the CALLER's ``findings`` list
    -- split out so its caller (``_sharded_findings``) can isolate one
    project's failure from the rest, mirroring ``sources/board.py``'s own
    ``_check_project_chain_completeness`` split (findings owned by the
    caller, appended in place, never returned from a local list a raise could
    discard). Logic is verbatim from the original's own ``check()``."""
    project = pdir.parent.name
    names = {p.name for p in pdir.iterdir()}
    if not _is_dir(pdir / "prds"):
        flat = "prd.md" in {n.lower() for n in names}
        status = "flat prd.md" if flat else "absent"
        remedy = "regenerate via bmad-prd into prds/prd-<slug>-<date>/"
        findings.append({
            "inv": "INV-3", "kind": "prd-not-sharded", "subject": project,
            "owner": "", "status": status, "remedy": remedy,
            "detail": f"{project}: PRD is {status}, not sharded — {remedy}",
        })
    if not _is_dir(pdir / "architecture"):
        flat = any(n.startswith("architecture") for n in names)
        status = "flat architecture.md" if flat else "absent"
        remedy = ("regenerate via bmad-architecture into "
                  "architecture/architecture-<slug>-<date>/")
        findings.append({
            "inv": "INV-3", "kind": "architecture-not-sharded", "subject": project,
            "owner": "", "status": status, "remedy": remedy,
            "detail": f"{project}: architecture is {status}, not sharded — {remedy}",
        })
    if "epics.md" not in names:
        remedy = "run bmad-create-epics-and-stories"
        findings.append({
            "inv": "INV-3", "kind": "epics-missing", "subject": project,
            "owner": "", "status": "absent", "remedy": remedy,
            "detail": f"{project}: epics.md is absent — {remedy}",
        })


def _sharded_findings(target: Path, findings: list[dict]) -> None:
    """Append every project's INV-3 findings to the CALLER's ``findings``
    list. Each project is evaluated inside its own try/except: one project's
    unreadable ``planning-artifacts`` directory must not discard another,
    ALREADY-COMPUTED project's real findings (mirrors
    ``sources/board.py``'s own ``_check_chain_completeness`` isolation,
    structured in from the first draft per this story's Design Notes rather
    than rediscovered across review passes).

    The projects-tree listing itself is isolated too: an unreadable
    ``_bmad-output/projects/`` must degrade to one named WARN, not raise past
    every already-appended INV-0/1/2 finding to the outer
    ``degrade_on_exception``. The per-project ``planning-artifacts`` probe
    moved INSIDE the try for the same reason ``_is_dir`` exists -- as
    ``Path.is_dir()`` it answered ``False`` for an unreadable one, silently
    skipping a project rather than naming it."""
    projects_dir = target / "_bmad-output" / "projects"
    try:
        project_dirs = _listdir(projects_dir) if _is_dir(projects_dir) else []
    except OSError as exc:
        findings.append(_unreadable_input(
            "INV-3", "_bmad-output/projects",
            f"_bmad-output/projects/ could not be read here — "
            f"{exc.__class__.__name__}: {exc}; the sharded planning tree is "
            f"not evaluable",
            "make _bmad-output/projects/ readable, then re-check",
        ))
        return
    for proj in project_dirs:
        pdir = proj / "planning-artifacts"
        try:
            if not _is_dir(pdir):
                continue
            _check_project_sharded(pdir, findings)
        except Exception as exc:  # noqa: BLE001 -- one project's unreadable
            # directory must not discard findings already appended for a
            # different project.
            findings.append({
                "inv": "INV-3", "kind": "dream-chain-unevaluable",
                "subject": pdir.parent.name, "owner": "", "status": "",
                "remedy": "fix the malformed/unreadable planning-artifacts dir, then re-check",
                "detail": (f"{pdir.parent.name}: could not be evaluated here — "
                           f"{exc.__class__.__name__}: {exc}"),
                "warn": True,
            })


def _check_dream_chain(
    target: Path, dreams: dict, specs: list[dict], findings: list[dict]
) -> list[dict]:
    """Port of the original script's own ``check()`` -- see this module's own
    header and the original's for the full INV-0/1/2/3 rationale. Findings
    are structured dicts here rather than printed lines; ``kind``/``remedy``
    text is unchanged from the original. Every branch below operates on
    already-collected in-memory data (``dreams``/``specs``), which cannot
    raise -- only ``_sharded_findings`` touches the filesystem again, and it
    isolates per-project on its own.

    ``findings`` is the CALLER's list (already seeded with any
    ``dream-chain-unevaluable`` entries ``_collect_specs`` appended) --
    appended to in place rather than replaced, so a spec that could not be
    collected stays visible alongside every invariant this function itself
    evaluates."""

    # INV-0 -- every Spec declares owner-dream. Without it the chain is not
    # traversable and INV-1/INV-2 cannot be measured.
    for s in specs:
        if not s["dream"]:
            slug = s["spec"].removeprefix("spec-")
            implied = slug if slug in dreams else ""
            remedy = (f"add `owner-dream: docs/dreams/{implied}.md`" if implied
                       else "add an owner-dream: key")
            findings.append({
                "inv": "INV-0", "kind": "spec-without-dream-link",
                "subject": s["spec"],
                "owner": dreams.get(implied, {}).get("owner", "") if implied else "",
                "status": f"in {s['project']}", "remedy": remedy,
                "detail": f"{s['spec']} in {s['project']} has no owner-dream link — {remedy}",
            })

    # A Spec covers a Dream if it DECLARES the link, or (fallback) its slug
    # matches -- keeps INV-1 honest while INV-0 is being closed.
    covered = {s["dream"] for s in specs if s["dream"]}
    covered |= {s["spec"].removeprefix("spec-") for s in specs
                if not s["dream"] and s["spec"].removeprefix("spec-") in dreams}
    # Satellite consolidation (2026-08-02): a Dream's whole chain folded into
    # ANOTHER Dream's Spec, verbatim -- either `covers-dreams:` (authoritative)
    # or a `## Satellite: <Title>` heading matching the Dream's own `title:`.
    for s in specs:
        covered |= set(s.get("covers", ()))
        if s.get("satellite_titles"):
            for slug, d in dreams.items():
                if _normalize_title(d.get("title", "")) in s["satellite_titles"]:
                    covered.add(slug)

    # INV-1 -- every Dream has a Spec
    for slug, d in sorted(dreams.items()):
        if slug not in covered:
            owner = d["owner"] or "(none)"
            status = d["status"] or "(none)"
            remedy = f"author a Spec under {_expected_spec_dir(d['owner'] or 'guild', slug)}"
            findings.append({
                "inv": "INV-1", "kind": "dream-without-spec", "subject": slug,
                "owner": owner, "status": status, "remedy": remedy,
                "detail": f"{slug} (owner={owner}) has no Spec — {remedy}",
            })

    # INV-2a -- a buildable Dream owned by `guild` has no station yet.
    for slug, d in sorted(dreams.items()):
        if d.get("owner") == "guild" and slug not in CONSTITUTIVE:
            remedy = "assign a station (guild is intake, not a terminal owner)"
            findings.append({
                "inv": "INV-2", "kind": "owner-unassigned", "subject": slug,
                "owner": "guild", "status": d.get("status", ""), "remedy": remedy,
                "detail": f"{slug} is owned by 'guild' — {remedy}",
            })

    # INV-2 -- the chain lives where its owner lives
    for s in specs:
        owner = dreams.get(s["dream"], {}).get("owner", "")
        if not owner:
            continue
        want = _expected_project(owner)
        if s["project"] != want:
            slug = s["spec"].removeprefix("spec-")
            remedy = f"move to {_expected_spec_dir(owner, slug)}"
            findings.append({
                "inv": "INV-2", "kind": "spec-location-mismatch", "subject": s["spec"],
                "owner": owner, "status": f"in {s['project']}", "remedy": remedy,
                "detail": (f"{s['spec']} lives in {s['project']} but owner {owner} "
                           f"expects {want} — {remedy}"),
            })

    # INV-3 -- sharded build tree (the one part of this check that still
    # touches the filesystem; isolated per-project on its own).
    _sharded_findings(target, findings)

    return findings


def gather_dream_chain(target: Path) -> tuple[Finding, ...]:
    """Judge whether every Dream has a Spec in its owner's project and every
    project uses the 6.10 sharded planning tree -- the library form of
    ``scripts/dream_chain_check.py``'s own ``main()``, minus the print/exit
    CLI surface. Every INV-0/1/2/3 violation becomes one FAIL ``Finding``; a
    clean chain degrades to a vacuous OK rather than raising.
    """
    return degrade_on_exception(
        Source.DREAM_CHAIN, "dream-chain", lambda: _gather_dream_chain(target)
    )


def _gather_dream_chain(target: Path) -> tuple[Finding, ...]:
    findings: list[dict] = []
    dreams = _collect_dreams(target, findings)
    specs = _collect_specs(target, findings)
    raw = _check_dream_chain(target, dreams, specs, findings)
    if not raw:
        # Nothing found AND neither input tree exists: `target` is not a
        # monorepo root (the original was anchored to its own REPO_ROOT; a
        # library gather takes whatever it is handed, and `doctor check`
        # defaults to "."). Claiming the confident OK below here would report
        # "every Dream has a Spec" for a target holding no Dreams at all --
        # a clean bill of health for a question never asked. Mirrors
        # `sources/ledger.py`'s own honest "cannot be evaluated" WARN.
        #
        # Tested on what was actually COLLECTED, not merely on whether the
        # two directories exist: `docs/dreams/` present-but-empty (or holding
        # only its README) alongside no projects tree passed the old
        # both-must-be-missing test and still produced the confident OK --
        # asserting "every project uses the sharded planning tree" about zero
        # projects.
        if not dreams and not specs and not _is_dir(
            target / "_bmad-output" / "projects"
        ):
            return (
                Finding(
                    source=Source.DREAM_CHAIN,
                    check="dream-chain-unevaluable",
                    status=DoctorStatus.WARN,
                    message=(
                        f"no Dreams, no Specs and no _bmad-output/projects/ "
                        f"under {target} — the Dream-to-Code chain cannot be "
                        f"evaluated here"
                    ),
                    evidence={"target": str(target)},
                ),
            )
        return (
            Finding(
                source=Source.DREAM_CHAIN,
                check="dream-chain",
                status=DoctorStatus.OK,
                message=(
                    "every Spec links a Dream, every Dream has a Spec in its "
                    "owner's project, and every project uses the sharded "
                    "planning tree"
                ),
                evidence={"dreams": len(dreams), "specs": len(specs)},
            ),
        )
    return tuple(
        Finding(
            source=Source.DREAM_CHAIN,
            check=item["kind"],
            status=DoctorStatus.WARN if item.get("warn") else DoctorStatus.FAIL,
            message=item["detail"],
            evidence={
                "inv": item["inv"],
                "subject": item["subject"],
                "owner": item.get("owner", ""),
                "status": item.get("status", ""),
                "remedy": item.get("remedy", ""),
            },
        )
        for item in raw
    )


# === gather_spec_surface =======================================================
#
# Ported from scripts/spec_surface_check.py -- see that script's own module
# docstring for the full coverage/drift/blindness rationale. The
# ``--write-baseline`` mutation path is deliberately NOT ported (Boundaries):
# this gather is read-only judgement only.

ALLOWLIST_REL = Path("scripts") / "spec_surface_allowlist.txt"
BASELINE_REL = Path("scripts") / ".spec-surface-baseline.json"


def _glob_to_re(pattern: str) -> re.Pattern:
    """Verbatim from the original: ``**`` spans path separators, ``*``/``?``
    do not; a pattern with no glob chars matches exactly."""
    out: list[str] = []
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if pattern[i:i + 2] == "**":
            out.append(".*")
            i += 2
        elif c == "*":
            out.append("[^/]*")
            i += 1
        elif c == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(c))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def _parse_surface(spec_md: Path) -> tuple[list[str], list[str], str]:
    """(``surface:`` globs, ``surface-drift-exclude:`` globs, drift mode)
    from a SPEC.md's frontmatter -- verbatim hand-rolled reader from the
    original (NOT ``yaml.safe_load``: preserve, don't redesign -- unlike
    ``gather_dream_chain``'s frontmatter, this parser's own comments explain
    why a comment/blank line inside a block sequence must not end the
    section, a real historical bug this port keeps fixed).

    RAISES on an unreadable/non-UTF-8 SPEC.md rather than degrading to an
    empty surface. An empty surface is indistinguishable from "this spec
    governs nothing", so degrading here silently UN-GOVERNS every file the
    spec really owns: each one is then reported FAIL ``ungoverned`` ("no spec
    surface and no allowlist entry") and each baselined one FAIL ``drift ...
    removed`` -- confidently wrong findings rather than an honest
    "unevaluable". That is the exact silent-governance-loss defect the
    original script's own module docstring records having fixed ("the checker
    reported the files as *removed* rather than erroring"). ``_check_spec_
    surface`` isolates this per-spec into a ``spec-surface-unevaluable`` WARN
    and suppresses the now-unsound COVERAGE findings, so the house
    "degrades, never crashes" rule (Boundaries) is still met -- one layer
    up, where the module can say WHICH spec went dark."""
    globs: list[str] = []
    excludes: list[str] = []
    drift = "memlog"
    text = spec_md.read_text(encoding="utf-8")
    in_fm = False
    section: str | None = None
    for line in text.splitlines():
        if line.strip() == "---":
            if in_fm:
                break
            in_fm = True
            continue
        if not in_fm:
            continue
        if section and line.startswith("  - "):
            (globs if section == "surface" else excludes).append(
                line[4:].split("#", 1)[0].strip())
            continue
        if section and (not line.strip() or line.lstrip().startswith("#")):
            continue
        section = None
        if line.startswith("surface:"):
            section = "surface"
        elif line.startswith("surface-drift-exclude:"):
            section = "exclude"
        elif line.startswith("surface-drift:"):
            drift = line.split(":", 1)[1].split("#", 1)[0].strip()
    return globs, excludes, drift


def _load_allowlist(path: Path) -> list[tuple[str, str]] | None:
    """``[(pattern, reason)]`` from ``scripts/spec_surface_allowlist.txt``, or
    ``None`` when the file exists but could not be READ -- verbatim parsing
    from the original, with the two failure modes the original never had to
    tell apart deliberately split:

    * **absent** -> ``[]``. The original assumes the file always exists
      in-repo; a library call against an arbitrary target must not, and "no
      allowlist" genuinely means "nothing explicitly exempted".
    * **present but unreadable** (permissions, non-UTF-8) -> ``None``. An
      empty list here would be a LIE with teeth: every allowlisted file is
      then reported FAIL ``ungoverned`` -- whose message literally asserts
      "no allowlist entry" -- and every real entry silently becomes a
      ``stale-allowlist`` FAIL. ``_check_spec_surface`` turns this into a
      ``spec-surface-unevaluable`` WARN and suppresses the unsound coverage
      findings, the same treatment an unreadable SPEC.md surface gets."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    except (OSError, UnicodeDecodeError):
        return None
    entries: list[tuple[str, str]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        pattern, _, reason = line.partition("#")
        entries.append((pattern.strip(), reason.strip() or "(no reason given)"))
    return entries


def _sha1(path: Path) -> str | None:
    """A file's sha1 hex digest, or ``None`` on any read failure -- verbatim
    hashing from the original, but returning ``None`` instead of letting
    ``OSError`` escape: a governed file that vanishes or becomes unreadable
    between listing and hashing must degrade this ONE file's comparison, not
    the whole gather."""
    try:
        return hashlib.sha1(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _memlog_text(memlog: Path) -> str:
    """The memlog's raw text, for per-file reconciliation claims (S-13.2) --
    verbatim from the original (``errors="replace"`` already tolerates
    non-UTF-8 bytes without raising)."""
    if not memlog.is_file():
        return ""
    try:
        return memlog.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _contract_hash(target: Path, s: dict) -> str:
    """The memlog (+ optional sentinel) hash a spec's drift is measured
    against -- verbatim logic from the original's own ``contract_hash()``,
    using the ``_sha1`` above that degrades to ``None`` rather than raising."""
    h = ""
    if s["memlog"].exists():
        # PRESENT but unhashable is not the same as ABSENT. Collapsing it to
        # "" (the absent hash) makes the contract hash unconditionally differ
        # from the baseline, so `spec_moved` is always True and every gating
        # `drift` FAIL silently becomes a non-gating `drift-presumed` WARN --
        # the run then reports OK. Raise instead; `_spec_current_state`'s own
        # per-spec try/except turns it into a named unevaluable WARN.
        h = _sha1(s["memlog"]) or _unhashable(s["memlog"])
    if s["drift"].startswith("sentinel:"):
        sentinel = target / s["drift"].split(":", 1)[1].strip()
        if sentinel.is_file():
            # Same distinction as the memlog above: an unreadable sentinel is
            # not a missing one.
            h += "+" + (_sha1(sentinel) or _unhashable(sentinel))
        else:
            h += "+missing"
    return h


def _unhashable(path: Path) -> str:
    """Raise for a file that exists but could not be read -- the honest
    alternative to substituting a hash that silently means something else.
    Never returns (typed ``str`` so it composes with ``or`` above)."""
    raise OSError(f"{path.name} is present but could not be read")


def _tracked_files(target: Path) -> list[str] | None:
    """``git ls-files`` output, or ``None`` when git is unavailable --
    routes through ``cli_bridge.run_git`` (AD-5: the sole subprocess site),
    unlike the original's own direct ``subprocess.run`` call.

    ``UnicodeDecodeError`` is caught alongside ``CliBridgeError`` because
    ``run_git`` decodes with ``text=True`` -- a tracked path containing a
    non-UTF-8 byte would otherwise raise straight out of this function and
    past the outer ``degrade_on_exception``'s per-call boundary, mirroring
    the exact gap ``sources/ledger.py``'s own ``_git`` wrapper already
    guards against for the same underlying cause."""
    try:
        out = run_git(target, ["ls-files"])
    except (CliBridgeError, UnicodeDecodeError):
        return None
    return [line for line in out.splitlines() if line]


def _governed_and_ungoverned(
    files: list[str], specs: dict[str, dict], allow: list[tuple[str, str]]
) -> tuple[dict[str, list[str]], list[str], dict[str, int]]:
    """(spec -> governed files, ungoverned files, allowlist-pattern hit
    counts) -- verbatim comparison logic from the original's own ``main()``
    body. Pure string/regex matching over already-collected data; cannot
    raise."""
    allow_res = [(_glob_to_re(p), p, r) for p, r in allow]
    governed: dict[str, list[str]] = {}
    ungoverned: list[str] = []
    allow_hits: dict[str, int] = {p: 0 for p, _ in allow}
    for f in files:
        owners = [n for n, s in specs.items() if any(r.match(f) for r in s["res"])]
        if owners:
            for n in owners:
                governed.setdefault(n, []).append(f)
            continue
        for rx, pat, _ in allow_res:
            if rx.match(f):
                allow_hits[pat] += 1
                break
        else:
            ungoverned.append(f)
    return governed, ungoverned, allow_hits


def _spec_current_state(
    target: Path, specs: dict[str, dict], governed: dict[str, list[str]]
) -> tuple[dict[str, dict], list[dict], dict[str, set[str]]]:
    """Every spec's current ``{memlog, files}`` hash state, a WARN item for
    anything that could not be evaluated, and the per-spec set of governed
    paths to EXCLUDE from the baseline diff because they could not be hashed.

    Two nested units, isolated separately -- the distinction matters:

    * **Per SPEC** (the outer try) for the contract hash. An unreadable
      ``.memlog.md`` or sentinel makes the whole spec's drift unmeasurable,
      because every one of its files is compared against that one hash.
    * **Per FILE** (the inner try) for the governed files themselves. One
      unreadable file makes exactly ONE file's comparison unsound. Wrapping
      the whole file loop in the per-spec try instead -- the shape review
      found here -- meant one ``chmod 000`` file discarded every OTHER
      governed file's already-computed drift FAIL and replaced the lot with a
      single non-gating WARN, so the run reported exit 0. Reproduced live
      during review: three gating ``drift`` FAILs collapsed into one WARN.
      This is the same "the fix for a false-clean over-suppressed real
      findings" class the previous pass closed for coverage, one level down.

    The unhashable path is returned in ``skipped`` rather than merely omitted
    from ``files``: omitting it alone would make the baseline diff report it
    ``drift ... removed``, the confidently-wrong finding this branch exists
    to avoid.
    """
    current: dict[str, dict] = {}
    warns: list[dict] = []
    skipped: dict[str, set[str]] = {}
    for name, s in specs.items():
        try:
            files: dict[str, str] = {}
            skip: set[str] = set()
            if s["drift"] != "exempt":
                for f in sorted(governed.get(name, [])):
                    if f in s["exclude"]:
                        continue
                    try:
                        sha = _sha1(target / f)
                        if sha is not None:
                            files[f] = sha
                        elif _is_file(target / f):
                            # Dropping a PRESENT-but-unreadable governed file
                            # from the state is indistinguishable from the
                            # file being deleted -- the baseline diff then
                            # reports it FAIL `drift ... removed`, a
                            # confidently wrong finding about a file that is
                            # still right there. Only a file that is
                            # genuinely GONE may drop out silently (that
                            # `removed` is the true answer).
                            #
                            # `_is_file`, not `exists()`: `exists()` follows a
                            # symlink, so a tracked symlink-to-a-DIRECTORY (or
                            # a gitlink) inside a governed surface hashed to
                            # None, probed True, and permanently took the
                            # whole spec dark. The original skipped exactly
                            # these paths -- `(REPO_ROOT / f).is_file()` --
                            # and this repo tracks one today
                            # (`.claude/skills/cf-atlas-legacy/active`).
                            _unhashable(target / f)
                    except OSError as exc:
                        skip.add(f)
                        warns.append({
                            "kind": "spec-surface-unevaluable", "path": f,
                            "detail": (f"{name}: {f} could not be hashed here "
                                       f"— {exc.__class__.__name__}: {exc}; "
                                       f"its drift alone is not evaluable"),
                            "warn": True,
                        })
            current[name] = {"memlog": _contract_hash(target, s), "files": files}
            if skip:
                skipped[name] = skip
        except Exception as exc:  # noqa: BLE001 -- one spec's unreadable
            # contract (memlog/sentinel) must not discard another spec's
            # already-computed state.
            warns.append({
                "kind": "spec-surface-unevaluable", "path": name,
                "detail": (f"{name}: could not be evaluated here — "
                           f"{exc.__class__.__name__}: {exc}"),
                "warn": True,
            })
    return current, warns, skipped


def _drift_findings(
    target: Path, specs: dict[str, dict], current: dict[str, dict],
    skipped: dict[str, set[str]] | None = None,
) -> tuple[list[dict], list[dict]]:
    """(gating findings, presumed-but-non-gating findings) from comparing
    ``current`` against the committed baseline -- verbatim logic from the
    original's own ``main()`` body (S-13.1/S-13.2/S-13.5 rationale lives in
    that script's own module docstring).

    ``skipped`` names the governed paths ``_spec_current_state`` could not
    hash, per spec. They are dropped from BOTH sides of the comparison: they
    are absent from ``cur["files"]`` but still present in the baseline, so
    without this they would each be reported ``drift ... removed`` -- a
    confidently wrong claim about a file that is still on disk, already
    carrying its own honest WARN."""
    findings: list[dict] = []
    presumed: list[dict] = []
    baseline_path = target / BASELINE_REL
    if not baseline_path.is_file():
        findings.append({
            "kind": "no-baseline", "path": "",
            "detail": "baseline missing: run --write-baseline",
        })
        return findings, presumed
    try:
        base = json.loads(baseline_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 -- an unreadable/malformed baseline is
        # "no baseline to compare against", not a crash (Boundaries).
        findings.append({
            "kind": "no-baseline", "path": "",
            "detail": f"{baseline_path.relative_to(target)} is unreadable: run --write-baseline",
        })
        return findings, presumed

    for name, cur in current.items():
        b = base.get(name) if isinstance(base, dict) else None
        # A baseline entry that is valid JSON but not an OBJECT (a stray
        # string/list/number from a hand-edit) must be treated as "no usable
        # baseline for this spec", not handed to `.get()` -- the same
        # wrong-shape-but-valid class the `isinstance(base, dict)` guard above
        # and the `b.get("files")` guard below already cover. Unguarded, the
        # AttributeError escapes to `degrade_on_exception` and discards every
        # OTHER spec's already-computed coverage/drift finding.
        # ... and `memlog`'s own value has the same wrong-shape exposure the
        # `files` guard below already covers: a hand-edited entry missing the
        # key, or carrying a list/null, compares unequal to every real
        # contract hash, so `spec_moved` is unconditionally True and every
        # gating `drift` FAIL silently degrades to a `drift-presumed` WARN.
        # The original indexed `b["memlog"]` and raised loudly instead.
        if not isinstance(b, dict) or not isinstance(b.get("memlog"), str):
            b = None
        if b is None:
            findings.append({
                "kind": "no-baseline", "path": name,
                "detail": f"{name}: run --write-baseline --spec {name}",
            })
            continue
        spec_moved = b.get("memlog") != cur["memlog"]
        named = _memlog_text(specs[name]["memlog"]) if spec_moved else ""
        b_files = b.get("files", {}) if isinstance(b.get("files"), dict) else {}
        skip = (skipped or {}).get(name, frozenset())
        for f in sorted((set(b_files) | set(cur["files"])) - set(skip)):
            old, new = b_files.get(f), cur["files"].get(f)
            if old == new:
                continue
            what = "changed" if old and new else ("added" if new else "removed")
            if not spec_moved:
                findings.append({
                    "kind": "drift", "path": f,
                    "detail": (f"{name}: {f} {what} but the spec's memlog did "
                               f"not move — reconcile the spec, then "
                               f"--write-baseline --spec {name}"),
                })
            elif f not in named:
                presumed.append({
                    "kind": "drift-presumed", "path": f,
                    "detail": (f"{name}: {f} {what}; the memlog moved but does "
                               f"not name this path — confirm it was "
                               f"reconciled, then --write-baseline --spec {name}"),
                })
    return findings, presumed


def _collect_surfaces(target: Path) -> tuple[dict[str, dict], list[dict]]:
    """(spec -> parsed surface state, WARN items for the specs that went
    dark). Split out of ``_check_spec_surface`` so the caller can tell an
    unknown SURFACE from an unknown EXEMPTION list.

    Listed through ``_listdir`` rather than the original's own
    ``_bmad-output/projects/*/planning-artifacts/specs/spec-*/SPEC.md`` glob:
    glob swallows ``OSError`` mid-traversal, so an unlistable
    ``planning-artifacts/specs/`` would read as "this project governs
    nothing" and un-govern every file it owns -- the same silent-
    governance-loss defect ``_parse_surface``'s own docstring refuses to
    reintroduce, one directory level up.

    Probed through ``_is_dir``/``_is_file`` for the same reason, one level up
    AGAIN: ``Path``'s own answer ``False`` for an unreadable ANCESTOR, so an
    unreadable ``spec-<slug>/`` or ``planning-artifacts/`` silently dropped
    the spec and every file it governs was then reported FAIL ``ungoverned``
    (or, when those files happen to be allowlisted, vanished into a confident
    OK) with no WARN naming what went dark. Reproduced live during review at
    both levels."""
    specs: dict[str, dict] = {}
    unsound: list[dict] = []
    projects_dir = target / "_bmad-output" / "projects"
    try:
        project_dirs = _listdir(projects_dir) if _is_dir(projects_dir) else []
    except OSError as exc:
        unsound.append({
            "kind": "spec-surface-unevaluable", "path": "_bmad-output/projects",
            "detail": (f"_bmad-output/projects/ could not be read here — "
                       f"{exc.__class__.__name__}: {exc}; every surface is "
                       f"unknown, so coverage is not evaluable"),
            "warn": True,
        })
        return specs, unsound
    for proj in project_dirs:
        specs_dir = proj / "planning-artifacts" / "specs"
        try:
            if not _is_dir(specs_dir):
                continue
            spec_dirs = [
                sd for sd in _listdir(specs_dir)
                if sd.name.startswith("spec-") and _is_file(sd / "SPEC.md")
            ]
        except OSError as exc:
            unsound.append({
                "kind": "spec-surface-unevaluable",
                "path": f"{proj.name}/planning-artifacts/specs",
                "detail": (f"{proj.name}: planning-artifacts/specs/ could not "
                           f"be read here — {exc.__class__.__name__}: {exc}; "
                           f"its surfaces are unknown, so coverage is not "
                           f"evaluable"),
                "warn": True,
            })
            continue
        for sd in spec_dirs:
            spec_md = sd / "SPEC.md"
            # Key by <project>/<spec-dir>, never the bare dir name -- the same
            # slug can legitimately exist in two projects, and a bare-name key
            # would silently drop one surface (verbatim rationale from the
            # original).
            name = f"{proj.name}/{sd.name}"
            try:
                globs, excludes, drift = _parse_surface(spec_md)
            except Exception as exc:  # noqa: BLE001 -- one spec's unreadable
                # SPEC.md must degrade to a named WARN, never to a silently
                # empty surface (see `_parse_surface`'s own docstring).
                unsound.append({
                    "kind": "spec-surface-unevaluable", "path": name,
                    "detail": (f"{name}: SPEC.md could not be read here — "
                               f"{exc.__class__.__name__}: {exc}; its surface "
                               f"is unknown, so coverage is not evaluable"),
                    "warn": True,
                })
                continue
            specs[name] = {
                "globs": globs, "drift": drift, "exclude": set(excludes),
                "res": [_glob_to_re(g) for g in globs],
                "memlog": spec_md.parent / ".memlog.md",
            }
    return specs, unsound


def _check_spec_surface(
    target: Path, files: list[str]
) -> tuple[list[dict], list[dict]]:
    """(gating findings, presumed-but-non-gating findings) -- the full
    coverage + blindness + drift check, minus ``git ls-files`` (``files`` is
    the caller's ALREADY-RESOLVED listing, passed in rather than re-fetched:
    a second, independent ``run_git`` call here could transiently fail after
    the caller's own succeeded, and re-fetching would silently coalesce that
    failure to an empty list via ``or []`` instead of surfacing the correct
    unevaluable WARN -- the caller's single successful fetch is the only one
    this gather is allowed to trust)."""
    specs, unsound = _collect_surfaces(target)
    surface_unknown = bool(unsound)

    allow = _load_allowlist(target / ALLOWLIST_REL)
    allowlist_unknown = allow is None
    if allow is None:
        unsound.append({
            # `.as_posix()`, not `str()`: every other `path` in this source is
            # a forward-slash `git ls-files` path, and `str(Path(...))` would
            # render this one with backslashes on Windows.
            "kind": "spec-surface-unevaluable", "path": ALLOWLIST_REL.as_posix(),
            "detail": (f"{ALLOWLIST_REL.as_posix()} exists but could not be read here — "
                       f"the exemptions are unknown, so coverage is not "
                       f"evaluable"),
            "warn": True,
        })
        allow = []
    governed, ungoverned, allow_hits = _governed_and_ungoverned(files, specs, allow)

    findings: list[dict] = list(unsound)
    # Coverage ("is every tracked file governed?") is a GLOBAL computation
    # over every surface plus the allowlist -- unlike drift, which is
    # per-spec -- so an unknown surface or unknown exemption set does make
    # part of it unsound. But the two halves are NOT equally unsound, and
    # suppressing both wholesale (the shape review found here) lets ONE
    # unreadable SPEC.md discard every unrelated file's real coverage FAIL:
    #
    # * `ungoverned` IS unsound under an unknown surface -- a file the dark
    #   spec really owns would be reported "no spec surface".
    # * `stale-allowlist` is NOT. An unknown surface can only ADD candidates
    #   to the allowlist matching loop (the dark spec claims nothing), so it
    #   can only ever INFLATE a pattern's hit count. A pattern at zero hits
    #   here is therefore still at zero with every surface known -- no false
    #   positive is possible, only a missed one. It stays live.
    if not (surface_unknown or allowlist_unknown):
        for f in ungoverned:
            findings.append({
                "kind": "ungoverned", "path": f,
                "detail": f"{f}: no spec surface and no allowlist entry",
            })
    elif ungoverned:
        # Never suppress silently: a WARN nobody can see is how "we could not
        # evaluate coverage" gets mistaken for "coverage is clean".
        findings.append({
            "kind": "spec-surface-unevaluable", "path": "",
            "detail": (f"coverage suppressed: {len(ungoverned)} candidate "
                       f"ungoverned file(s) not reported because a surface or "
                       f"the exemption list could not be read (see the "
                       f"spec-surface-unevaluable finding(s) naming it)"),
            "warn": True,
        })
    if not allowlist_unknown:
        for pat, n in allow_hits.items():
            if n == 0:
                findings.append({
                    "kind": "stale-allowlist", "path": pat,
                    "detail": f"{pat!r} matches nothing — remove or fix",
                })

    # S-13.5 -- a governed surface with no contract behind it (see the
    # original's own module docstring for the full "structurally impossible
    # reconciliation" rationale).
    for name, s in sorted(specs.items()):
        if (s["drift"] == "memlog" and governed.get(name)
                and not s["memlog"].is_file()):
            findings.append({
                "kind": "drift-blind", "path": name,
                "detail": (
                    f"{name}: governs {len(governed[name])} file(s) with no "
                    f"{s['memlog'].relative_to(target)} — the contract hash is "
                    f"empty, so it can never move and no governed change is "
                    f"reconcilable. Create the memlog, then --write-baseline "
                    f"--spec {name} in the SAME change"
                ),
            })

    current, current_warns, skipped = _spec_current_state(target, specs, governed)
    findings.extend(current_warns)
    drift_findings, presumed = _drift_findings(target, specs, current, skipped)
    findings.extend(drift_findings)

    return findings, presumed


def gather_spec_surface(target: Path) -> tuple[Finding, ...]:
    """Judge whether every tracked file is governed by a spec surface or an
    allowlist entry, and whether a governed file's content has drifted out
    from under its spec's contract -- the library form of
    ``scripts/spec_surface_check.py``'s own ``main()``, minus the
    print/exit CLI surface AND minus ``--write-baseline`` (Boundaries: this
    gather is read-only judgement only).

    ``drift-presumed`` findings are WARN and non-gating (matching the
    original's own "informational" framing) -- they are still returned, but
    a run with drift-presumed items and nothing else still reports the
    coverage/drift OK verdict, exactly as the original prints "OK" while
    still surfacing its own DRIFT-PRESUMED section.
    """
    return degrade_on_exception(
        Source.SPEC_SURFACE, "spec-surface", lambda: _gather_spec_surface(target)
    )


def _gather_spec_surface(target: Path) -> tuple[Finding, ...]:
    # NOTE: deliberately NO "target is not a monorepo root" guard here, unlike
    # `_gather_dream_chain`/`_gather_deferred_work`. Review proposed one (a
    # run from a subdirectory reports every file in that subtree FAIL
    # `ungoverned`), but the two cases are not symmetric: those guards
    # replace a false OK -- a SILENT wrong answer -- whereas one here would
    # replace a false FAIL, which is loud and self-evident, with a WARN that
    # also silences the legitimate "this repo governs nothing yet" FAIL an
    # unconfigured root should report (an empty repo and a subdirectory are
    # indistinguishable from the filesystem alone). Trading a loud wrong
    # answer for a quiet one is the defect class this module exists to avoid.
    files = _tracked_files(target)
    if files is None:
        return (
            Finding(
                source=Source.SPEC_SURFACE,
                check="spec-surface-unevaluable",
                status=DoctorStatus.WARN,
                message=(
                    f"git is unavailable or {target} is not a repository — "
                    f"spec surface cannot be evaluated"
                ),
                evidence={"target": str(target)},
            ),
        )

    raw, presumed = _check_spec_surface(target, files)
    presumed_findings = tuple(
        Finding(
            source=Source.SPEC_SURFACE,
            check=item["kind"],
            status=DoctorStatus.WARN,
            message=item["detail"],
            evidence={"path": item["path"]},
        )
        for item in presumed
    )

    if not raw:
        return (
            *presumed_findings,
            Finding(
                source=Source.SPEC_SURFACE,
                check="spec-surface",
                status=DoctorStatus.OK,
                message="every tracked file governed or allowlisted; no drift",
                evidence={"files": len(files)},
            ),
        )
    return (
        *presumed_findings,
        *(
            Finding(
                source=Source.SPEC_SURFACE,
                check=item["kind"],
                status=DoctorStatus.WARN if item.get("warn") else DoctorStatus.FAIL,
                message=item["detail"],
                evidence={"path": item["path"]},
            )
            for item in raw
        ),
    )


# === gather_deferred_work ======================================================
#
# Ported from scripts/deferred_work_check.py -- see that script's own module
# docstring for the full "why this exists" rationale (bmad-loop's damping
# safety valve writes only to gitignored Tier-3 scratch by default).
#
# Story 7.3 extends the port beyond the original: `_anonymous()` used to run
# only against the TRACKED ledger. It now also runs against the Tier-3 file
# itself, sliced against the grandfather baseline `scripts/deferred_work_
# baseline.py` stamps (Story 7.2) so the pre-existing backlog does not red
# every landing pass on day one -- see spec-deferred-work-visibility's CAP-2/
# CAP-3 and this story's own Design Notes.

TIER3_REL = Path("implementation-artifacts") / "deferred-work.md"
TRACKED_REL = Path("planning-artifacts") / "deferred-work-ledger.md"

#: The committed anonymous-Tier-3-entry grandfather baseline (Story 7.2,
#: ``scripts/deferred_work_baseline.py --write-baseline``) -- a flat
#: ``{project_slug: count}`` JSON sibling of ``BASELINE_REL`` above, read-only
#: here (Boundaries: this story consumes it, never stamps or rewrites it).
DEFERRED_WORK_BASELINE_REL = Path("scripts") / ".deferred-work-baseline.json"

#: A Tier-3 ledger below this is boilerplate -- verbatim from the original.
_SUBSTANTIVE_BYTES = 2048

_DW_RE = re.compile(r"\bDW-[A-Za-z0-9][A-Za-z0-9-]*")
_GENERIC_RE = re.compile(r"^DW-\d+$")
_ENTRY_RE = re.compile(r"^#{2,4}\s+(DW-[A-Za-z0-9][A-Za-z0-9-]*)", re.M)
_ANON_RE = re.compile(r"^-\s+source_spec:", re.M)
_STATUS_RE = re.compile(r"^\s*status:", re.M)


def _ids(path: Path) -> set[str]:
    """Every ``DW-*`` id mentioned in ``path`` -- verbatim from the
    original. ``errors="replace"`` already tolerates non-UTF-8 bytes."""
    if not _is_file(path):
        return set()
    text = path.read_text(encoding="utf-8", errors="replace")
    return {m.group(0).rstrip("-") for m in _DW_RE.finditer(text)}


def _entries(path: Path) -> list[tuple[str, bool]]:
    """``(id, has_status)`` for every ID'd entry in a tracked ledger --
    verbatim from the original."""
    if not _is_file(path):
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    marks = [(m.start(), m.group(1)) for m in _ENTRY_RE.finditer(text)]
    out = []
    for i, (pos, ident) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        out.append((ident, bool(_STATUS_RE.search(text[pos:end]))))
    return out


def _anonymous(path: Path) -> list[int]:
    """Line numbers of entries with no ``## DW-<id>`` heading of their own --
    verbatim from the original (see its own docstring for the positional
    ``- source_spec:`` disambiguation rule)."""
    if not _is_file(path):
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


# --- Story 8.1: classify_tier3_entries -----------------------------------------
#
# Additive to, and independent of, `_anonymous()`/`_entries()`/`_ids()` above --
# none of the three is touched. `_anonymous()` only answers "is this line
# anonymous" for the detector's own count; it cannot classify an entry's SHAPE
# or extract its content, which Story 8.2/8.3 need to mint an id and promote an
# entry verbatim. `_anonymous()` also mishandles a live class of entry: a
# `### DW-<n>:` header whose own body uses plain (non-bulleted)
# `origin:`/`source_spec:`/`severity:`/`status:` keys never satisfies `_ANON_RE`
# (`^-\s+source_spec:`), so its in-entry/field-taken state never advances past
# that header -- and then wrongly treats the NEXT, topically unrelated,
# headerless `- source_spec:` bullet anywhere later in the file as "already
# claimed" by that header, silently dropping a real orphan from the anonymous
# count. Verified live across all 8 projects (this story's own Intent): 38 such
# headers exist, 25 swallow a real, unrelated orphan this way (corrected live
# measurement, via `classify_tier3_entries` itself -- see `DW-FU-8-1`'s own
# evidence) -- marshal's 9
# `### DW-<n>:` headers are a clean, fully-reproducing example (each one
# swallows the next headerless bullet in the file). `classify_tier3_entries`
# below does NOT repeat that bug: a header's claim on its own field block ends
# the moment that block ends (a blank line, a heading, or a sibling bulleted
# line), and nothing later in the file can be attributed back to it.
#
# `_anonymous()`'s own swallow bug is NOT fixed here (Never clause) -- logged
# instead as a deferred-work entry for a future story.

# `## Deferred from: ...` is the majority spelling live, but `## Deferred:
# <title> (<date>)` (no "from") also occurs (warden's tracked ledger, line
# 488) -- both spellings own a scope the same way.
_LEGACY_HEADER_RE = re.compile(r"^#{1,6}\s+Deferred(?:\s+from)?:")
_HEADING_RE = re.compile(r"^#{1,6}\s")
#: Any top-level bulleted line -- shared by every consumer below that needs
#: to recognize "a sibling bulleted field starts here, stop accumulating the
#: current one" (previously three separate inline ``re.match(r"^-\s", ...)``
#: calls).
_BULLET_START_RE = re.compile(r"^-\s")
#: Derives its prefix from `_ANON_RE.pattern` rather than hand-duplicating
#: the same `^-\s+source_spec:` text -- the two must never drift apart, since
#: `_anonymous()`'s own positional disambiguation (module banner above) and
#: this module's LEGACY_FLAT/LEGACY_HEADER detection both key off "is this
#: bullet a `source_spec:` entry-marker", the one field the Boundaries text
#: names as what makes a bullet a real entry (a bullet with no `source_spec:`
#: is freeform prose, never an entry).
_SOURCE_SPEC_BULLET_RE = re.compile(_ANON_RE.pattern + r"\s*(.*)$")
#: Any bulleted `- <key>: value` line, for `_consume_identified_entry`'s own
#: shape check (Story 8.1 patch: an `IDENTIFIED_*` header's first bulleted
#: field need not be `source_spec:` -- marshal's real shape leads with
#: `origin:` on other headers -- so this must not be hardcoded to one key).
_BULLETED_FIELD_RE = re.compile(_BULLET_START_RE.pattern + r"([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$")
_PLAIN_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$")

#: The closed deferred-work field-key vocabulary a bulleted field block's
#: OWN indented (no-dash) lines are allowed to start a fresh field with --
#: `.claude/skills/bmad-loop-sweep/deferred-work-format.md`'s documented set
#: (`origin`/`location`/`severity`/`reason`/`status`/`resolution`/`decision`/
#: `seen-again`) plus the fields load-bearing elsewhere in this module
#: (`source_spec`/`summary`/`evidence`) plus the verification-annotation
#: fields observed live across the fleet's tracked ledgers (`promoted`/
#: `found_by`/`raised`/`verified`). A generic ``[A-Za-z_]+:`` match
#: over-matches: real deferred-work prose regularly uses a colon as
#: mid-sentence punctuation ("Not pursued in this story: making ...", "the
#: real extractor: `extract-slides.mjs`...", "Not fixed here: the ...
#: signature...") -- each byte-identical in shape AND indentation to a
#: genuine field line (confirmed against the live corpus: every one of these
#: occurs exactly once fleet-wide as an accident of prose, while every name
#: below recurs dozens to hundreds of times as an actual field) -- so only a
#: closed vocabulary disambiguates a continuation line from a fresh field.
_KNOWN_FIELD_KEYS = (
    "source_spec", "summary", "evidence", "origin", "location", "severity",
    "reason", "status", "resolution", "decision", "seen-again", "promoted",
    "found_by", "raised", "verified",
)
_CONT_KEY_RE = re.compile(
    r"^\s{2,}(" + "|".join(re.escape(k) for k in _KNOWN_FIELD_KEYS) + r"):\s*(.*)$"
)


class Tier3Shape(StrEnum):
    """The four structural shapes a Tier-3 (or tracked-ledger) deferred-work
    entry takes across the fleet's 8 projects, verified live this session
    (Story 8.1): ``IDENTIFIED_BULLETED`` (CAP-1's current ``### DW-<id>:``
    header + an immediate bulleted ``- source_spec:`` field),
    ``IDENTIFIED_PLAIN`` (a ``### DW-<n>:`` header with no bulleted field of
    its own -- dominantly pure freeform prose, ``fields={}`` -- 28 of the
    fleet's 38 live headers of this shape, 100% of atlas's; the
    "review-budget-followup" shape with plain, non-bulleted
    ``source_spec:``/etc. keys is a real but minority case),
    ``LEGACY_FLAT`` (a headerless ``- source_spec:`` bullet -- no owning
    ``##``/``###`` ``DW-`` heading anywhere above it), and ``LEGACY_HEADER``
    (a non-DW ``## Deferred from: ...`` heading immediately owning a
    bulleted ``- source_spec:`` field).

    The epics.md AC text describes the fourth shape as "a headed entry with
    more than one `- source_spec:` bullet stacked under it" -- live
    verification across all 8 projects found the real mechanics narrower and
    different (this story's own Design Notes): no genuine
    one-header/multiple-related-bullets shape exists anywhere in the fleet.
    """

    IDENTIFIED_BULLETED = "identified-bulleted"
    IDENTIFIED_PLAIN = "identified-plain"
    LEGACY_FLAT = "legacy-flat"
    LEGACY_HEADER = "legacy-header"


@dataclass(frozen=True)
class LegacyEntry:
    """One entry ``classify_tier3_entries`` read out of a Tier-3 (or tracked
    ledger) file -- additive to, and independent of, ``_anonymous()``/
    ``_entries()``/``_ids()`` above (this story's Never clause: this type
    and its reader change no existing finding, mint nothing, write
    nothing).

    ``id`` is the real ``DW-*`` id for an ``IDENTIFIED_*`` shape, else
    ``None`` for a ``LEGACY_*`` shape (Boundaries). ``fields`` holds every
    ``key: value`` pair the entry carries, with wrapped continuation lines
    already joined into a single string per key -- see
    ``classify_tier3_entries``'s own docstring.
    """

    shape: Tier3Shape
    id: str | None
    start_line: int
    end_line: int
    fields: dict[str, str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "shape", Tier3Shape(self.shape))
        # Same defensive-copy rationale as `models.Finding.evidence` -- a
        # frozen dataclass only blocks attribute reassignment, not mutation
        # of a referenced mutable dict a caller still holds.
        object.__setattr__(self, "fields", dict(self.fields))


def classify_tier3_entries(path: Path) -> tuple[LegacyEntry, ...]:
    """Every real deferred-work entry in ``path``, one ``LegacyEntry`` each,
    classified into the four live ``Tier3Shape``\\ s (Story 8.1). Feeds
    Story 8.2/8.3's future minting/promotion work; itself a pure read with
    no side effects -- Doctor's ``sources/`` package is read-only by
    construction (Design Notes), so a future ``--fix`` script can safely
    import or duplicate this function without inheriting a write site.

    Reuses ``_ENTRY_RE``'s ``DW-`` heading match and the same
    ``- source_spec:`` bulleted-field convention ``_ANON_RE`` matches
    (``_SOURCE_SPEC_BULLET_RE`` derives its prefix from ``_ANON_RE.pattern``
    directly, so the two cannot drift apart), but tracks full entry spans
    and field text rather than re-deriving ``_anonymous()``'s own positional
    counting logic -- and, unlike ``_anonymous()``, does NOT mistake the
    next unrelated headerless bullet for an ``IDENTIFIED_PLAIN`` header's
    own field: a header's claim on its own field block ends the moment that
    block ends (a blank line, a heading, or a sibling bulleted line), never
    later in the file. An ``IDENTIFIED_*`` header's own field search scans
    FORWARD past blank lines and non-field content (e.g. an interposed
    ``<!-- ... -->`` comment) up to the next heading, rather than giving up
    after one line -- otherwise the header's real content, past the
    interposed lines, misreads as a separate, unrelated orphan (the
    marshal ``DW-1-2-1``/``DW-1-10-7`` bug; see ``_consume_identified_entry``).

    A bullet with no ``source_spec:`` field of its own -- freeform prose,
    e.g. warden's plain markdown bullets under a ``## Deferred from:``
    heading -- is not an entry and is skipped entirely: never returned, and
    never allowed to end an in-progress ``LEGACY_HEADER`` scope (a heading
    may own several such bulleted entries in a row, interleaved with
    freeform prose bullets that are simply skipped).

    ``summary:``/``evidence:`` (and every other) field value joins wrapped
    continuation lines -- a line is a continuation iff it is non-blank, not
    a heading, not a sibling ``- <key>:`` bullet, and does not itself open
    one of ``_KNOWN_FIELD_KEYS``'s known field names (see that constant's
    own docstring for why a generic ``word:`` match over-matches real
    prose).

    ``errors="replace"`` tolerates non-UTF-8 bytes, same as every other
    reader in this module; a missing file, or one that vanishes between the
    existence check and the read (TOCTOU), degrades to ``()``, never
    raises.
    """
    if not _is_file(path):
        return ()
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        # Mirrors `_memlog_text`'s own is_file-then-guarded-read pattern
        # above: `_is_file` can be stale by the time we get here, and a file
        # deleted in between must degrade to "no entries", never raise.
        return ()
    n = len(lines)
    entries: list[LegacyEntry] = []
    # "legacy" while inside a `## Deferred from: ...` heading's span (several
    # separate bulleted entries may live under ONE such heading, each its own
    # LEGACY_HEADER -- see warden's real file); None otherwise -- no owning
    # heading in effect, the LEGACY_FLAT default. A DW- header's own claim
    # never sets `scope`; it is consumed entirely, at most once, by
    # `_consume_identified_entry`, and anything after that claim ends reverts
    # to None -- exactly the fix for `_anonymous()`'s swallow bug (module
    # banner above).
    scope: str | None = None
    i = 0
    while i < n:
        line = lines[i]
        lineno = i + 1

        dw_match = _ENTRY_RE.match(line)
        if dw_match:
            i = _consume_identified_entry(lines, i + 1, dw_match.group(1), lineno, entries)
            scope = None
            continue

        if _LEGACY_HEADER_RE.match(line):
            scope = "legacy"
            i += 1
            continue

        if _HEADING_RE.match(line):
            scope = None
            i += 1
            continue

        bullet_match = _SOURCE_SPEC_BULLET_RE.match(line)
        if bullet_match:
            shape = Tier3Shape.LEGACY_HEADER if scope == "legacy" else Tier3Shape.LEGACY_FLAT
            i = _consume_bulleted_field_block(
                lines, i, "source_spec", bullet_match.group(1), None, shape, lineno, entries,
            )
            continue

        i += 1

    return tuple(entries)


def _consume_identified_entry(
    lines: list[str],
    i: int,
    entry_id: str,
    header_lineno: int,
    entries: list[LegacyEntry],
) -> int:
    """Resolve and consume ONE ``### DW-<id>:`` header's own field block --
    ``IDENTIFIED_BULLETED`` if the first field-shaped line found is a
    bulleted ``- <key>: value`` (any key -- marshal's real shape leads with
    ``origin:``, not ``source_spec:``), ``IDENTIFIED_PLAIN`` if it is a
    plain ``key: value`` line, else an empty ``IDENTIFIED_PLAIN`` entry when
    no recognizable field is found before the next heading or EOF.

    The search window scans FORWARD past blank lines and non-field content
    (e.g. an interposed ``<!-- id assigned ... -->`` HTML comment -- a real
    live convention from the 2026-07-30 verification campaign) up to the
    next heading, rather than giving up after the first non-blank line: a
    header that gives up too early misreads its OWN real content, sitting
    past the interposed lines, as a separate, unrelated ``LEGACY_FLAT``
    orphan (the marshal ``DW-1-2-1``/``DW-1-10-7`` bug, Story 8.1 review
    patch). Returns the index of the first line NOT consumed, so the
    caller's own scan resumes there -- once this returns, the header's
    claim is over for good."""
    n = len(lines)
    j = i
    while j < n:
        line = lines[j]
        if not line.strip():
            j += 1
            continue
        if _HEADING_RE.match(line):
            break
        bullet_match = _BULLETED_FIELD_RE.match(line)
        if bullet_match:
            return _consume_bulleted_field_block(
                lines, j, bullet_match.group(1), bullet_match.group(2),
                entry_id, Tier3Shape.IDENTIFIED_BULLETED, header_lineno, entries,
            )
        if _PLAIN_KEY_RE.match(line):
            return _consume_plain_field_block(lines, j, entry_id, header_lineno, entries)
        j += 1
    entries.append(
        LegacyEntry(Tier3Shape.IDENTIFIED_PLAIN, entry_id, header_lineno, header_lineno, {}),
    )
    return j


def _consume_bulleted_field_block(
    lines: list[str],
    i: int,
    first_key: str,
    first_value: str,
    entry_id: str | None,
    shape: Tier3Shape,
    start_lineno: int,
    entries: list[LegacyEntry],
) -> int:
    """Consume one bulleted entry's own field block -- its own first
    ``- <key>: value`` line (any key, not hardcoded to ``source_spec:`` --
    an ``IDENTIFIED_*`` header's own first bulleted field need not lead with
    it) plus every subsequent line that opens one of ``_KNOWN_FIELD_KEYS``'s
    known field names (a fresh key) or wraps the CURRENT key's value --
    stopping at the first blank line, heading, or sibling bulleted line.

    A line is a continuation of the current key iff it is non-blank, not a
    heading, not a sibling bulleted line, and does not itself open a KNOWN
    field key -- deliberately NOT any indented ``word:``-shaped line: a
    generic match over-matches real prose that uses a colon as mid-sentence
    punctuation (e.g. "Not pursued in this story: ..."), which silently
    truncated ``summary``/``evidence`` and misattributed the remainder to a
    spurious key (Story 8.1 review patch; see ``_KNOWN_FIELD_KEYS``'s own
    docstring for the live examples). Returns the index of the first line
    NOT consumed."""
    n = len(lines)
    fields: dict[str, str] = {first_key: first_value.strip()}
    current_key = first_key
    end_lineno = i + 1
    i += 1
    while i < n:
        line = lines[i]
        if not line.strip() or _HEADING_RE.match(line) or _BULLET_START_RE.match(line):
            break
        cont_match = _CONT_KEY_RE.match(line)
        if cont_match:
            current_key = cont_match.group(1)
            fields[current_key] = cont_match.group(2).strip()
        else:
            fields[current_key] = f"{fields[current_key]} {line.strip()}".strip()
        end_lineno = i + 1
        i += 1
    entries.append(LegacyEntry(shape, entry_id, start_lineno, end_lineno, fields))
    return i


def _consume_plain_field_block(
    lines: list[str],
    i: int,
    entry_id: str,
    header_lineno: int,
    entries: list[LegacyEntry],
) -> int:
    """Consume an ``IDENTIFIED_PLAIN`` header's own plain (non-bulleted)
    ``key: value`` lines -- stopping at the first blank line, heading, or
    bulleted line (the marshal ``DW-1`` case: its plain field block ends at
    the blank line right after ``status: open``, so the unrelated headerless
    bullet that follows it is never absorbed into it). Returns the index of
    the first line NOT consumed."""
    n = len(lines)
    fields: dict[str, str] = {}
    current_key: str | None = None
    end_lineno = header_lineno
    while i < n:
        line = lines[i]
        if not line.strip() or _HEADING_RE.match(line) or _BULLET_START_RE.match(line):
            break
        m = _PLAIN_KEY_RE.match(line)
        if m:
            current_key = m.group(1)
            fields[current_key] = m.group(2).strip()
        else:
            # `current_key` is always set here (never `None`): the caller
            # only enters this function after confirming the FIRST line
            # already matches `_PLAIN_KEY_RE` (`_consume_identified_entry`),
            # so the loop's very first iteration always takes the `if m:`
            # branch above before any continuation line is possible.
            fields[current_key] = f"{fields[current_key]} {line.strip()}".strip()
        end_lineno = i + 1
        i += 1
    entries.append(
        LegacyEntry(Tier3Shape.IDENTIFIED_PLAIN, entry_id, header_lineno, end_lineno, fields),
    )
    return i


# --- Story 8.2: mint_id_for_entry ------------------------------------------
#
# Ports `.claude/skills/bmad-dev-auto/step-04-review.md`'s "Minting the id"
# prose (lines ~81-98) into reusable, testable code -- that procedure has so
# far only ever been followed BY HAND, one finding at a time, by an LLM
# agent mid-review-pass, and has already produced three real near-miss
# duplicate-mint incidents (Intent). Pure computation: reads `tier3_path`/
# `tracked_path` to collect existing ids, never writes to either -- Story
# 8.3's future `--fix` mode owns the append.
#
# `station` is an explicit caller-supplied parameter, never resolved from
# `_bmad/scripts/resolve_config.py` or the active-project marker the way
# step-04-review.md's own step 1 does -- see this story's Design Notes for
# why: a library function meant to be called in a loop over all 8 projects
# cannot trust ambient per-worktree state that only ever names ONE active
# project at a time.

#: Two leading numeric groups plus an optional single trailing letter
#: (`<digits>-<digits><letter>?`) -- step-04-review.md step 2, verbatim.
#: `re.match` anchors at position 0 and does not require consuming the rest
#: of the string, so trailing text after the second group (a title slug, a
#: glued extra character) is accepted and discarded, matching the prose's
#: own `spec-2-1-3-way-merge-....md` -> `2-1` (not `2-1-3`) example.
_STORY_KEY_RE = re.compile(r"^(\d+-\d+[A-Za-z]?)")

#: step-04-review.md step 2's sanitize step: everything outside this set
#: becomes `-`.
_SANITIZE_RE = re.compile(r"[^A-Za-z0-9-]+")

#: Generic container stems step-04-review.md step 2 names by name: durable
#: story specs live at `planning-artifacts/specs/spec-<slug>/SPEC.md`, whose
#: stem is the constant `SPEC` -- using it directly would collapse every
#: spec in the fleet onto the same story key. Matched case-insensitively
#: (Review Triage Log 2026-08-15, item 6) -- `Spec.md`/`Readme.md`/
#: `INDEX.md` are the same generic container under a different casing, not
#: a distinct story key.
_GENERIC_STEMS = frozenset({"spec", "readme", "index"})

#: The whole remainder after a base id must be exactly one plain integer to
#: count toward that base's suffix -- step-04-review.md step 3's own
#: `DW-1-10-1` vs base `DW-1-1` example (remainder `0-1`, not a plain
#: integer, counts for nothing).
_PLAIN_INT_RE = re.compile(r"^[0-9]+$")

#: A backtick-quoted span -- the fleet's real `source_spec` values wrap the
#: path in a markdown code span (`` `path.md` ``). Extracting this span
#: FIRST, via search rather than an ends-with-backtick string check, isolates
#: just the filename even when trailing prose follows the closing backtick
#: (Review Triage Log 2026-08-15, item 5c -- confirmed live in pyforge-atlas's
#: real tracked ledger, 19 lines fleet-wide, e.g. `` `cfe-atlas-datapipeline-
#: kedro-migration.md` (Story E1, FR-11) ``, where the original `raw[0] ==
#: "`" and raw[-1] == "`"` check fails because the string does not END in a
#: backtick).
_BACKTICK_SPAN_RE = re.compile(r"`([^`]*)`")


def _strip_spec_prefix(name: str) -> str:
    """Strip a leading ``spec-`` if present -- step-04-review.md step 2's
    own first move, applied identically to a filename stem and to a parent
    directory name (both are named "stripped the same way" in the prose)."""
    return name.removeprefix("spec-")


def _sanitize_story_key(raw: str) -> str:
    """step-04-review.md step 2's sanitize step, verbatim: replace every
    character outside ``[A-Za-z0-9-]`` with ``-``, collapse runs of ``-``,
    and trim leading/trailing ``-`` -- so the id stays a single parseable
    token that no consumer's ``rstrip("-")`` can fold onto a different id."""
    collapsed = re.sub(r"-+", "-", _SANITIZE_RE.sub("-", raw))
    return collapsed.strip("-")


def _derive_story_key(source_spec: str) -> str:
    """Port of step-04-review.md step 2's ``{story}`` derivation rule,
    applied to a ``LegacyEntry.fields["source_spec"]`` value rather than to
    ``{spec_file}`` directly (this story's own scope, Intent) -- the fleet's
    real ledgers wrap that field in a markdown code span (`` `path.md` ``),
    which is stripped before the value is parsed as a path.

    Strips a leading ``spec-`` from the filename stem, then matches exactly
    two leading numeric groups plus an optional single trailing letter
    (``<digits>-<digits><letter>?``); falls back to the whole stem, or (when
    the stem is empty or one of ``_GENERIC_STEMS``) the parent directory
    name, when no such key matches. Sanitized to ``[A-Za-z0-9-]`` either
    way. Raises ``ValueError`` if every avenue still leaves an empty key --
    an empty ``{story}`` would mint an id with nothing after its prefix, the
    same phantom-id failure this function exists to prevent.

    Backtick handling (Review Triage Log 2026-08-15, item 5) is resolved by
    isolating the backtick-quoted span BEFORE any filename/prefix logic
    runs, rather than a plain ``raw[0] == "`" and raw[-1] == "`"`` string
    check: (a) a lone leading or trailing backtick with no matching pair is
    stripped rather than left to corrupt the stem, (b) a trailing backtick
    glued immediately after ``.md`` no longer defeats the ``.md``-suffix
    check (the un-stripped backtick used to make ``filename.lower().
    endswith(".md")`` false), and (c) trailing prose after a backtick-quoted
    filename (real live shape, e.g. `` `name.md` (Story E1, FR-11) ``) no
    longer reaches the derivation at all -- only the quoted span does.
    """
    raw = source_spec.strip()
    if not raw:
        raise ValueError(
            f"empty source_spec after stripping markdown/whitespace: {source_spec!r}"
        )
    span_match = _BACKTICK_SPAN_RE.search(raw)
    if span_match:
        raw = span_match.group(1).strip()
    elif "`" in raw:
        # A single stray backtick, leading or trailing, with no matching
        # pair -- strip it defensively rather than let it corrupt the
        # filename/prefix logic below.
        raw = raw.strip("`").strip()
    if not raw:
        raise ValueError(
            f"empty source_spec after stripping markdown/whitespace: {source_spec!r}"
        )

    path = PurePosixPath(raw.replace("\\", "/"))
    filename = path.name
    stem = filename[:-3] if filename.lower().endswith(".md") else filename
    name_for_match = _strip_spec_prefix(stem)

    match = _STORY_KEY_RE.match(name_for_match)
    if match:
        # `_STORY_KEY_RE`'s capture group is `\d+-\d+[A-Za-z]?` -- already
        # restricted to `[A-Za-z0-9-]` and never starts or ends with `-`, so
        # `_sanitize_story_key` is a no-op here and can never empty it
        # (Review Triage Log 2026-08-15, item 8: the prior `if story:` guard
        # after this call was unreachable).
        return _sanitize_story_key(match.group(1))

    candidate = name_for_match
    if not candidate or candidate.lower() in _GENERIC_STEMS:
        candidate = _strip_spec_prefix(path.parent.name)

    story = _sanitize_story_key(candidate)
    if not story:
        # Sanitizing emptied it -- step-04-review.md's own final fallback:
        # the parent directory name, sanitized the same way.
        story = _sanitize_story_key(_strip_spec_prefix(path.parent.name))
    if not story:
        raise ValueError(
            f"could not derive a non-empty story key from source_spec: {source_spec!r}"
        )
    return story


def _collect_dw_tokens(tier3_path: Path, tracked_path: Path) -> set[str]:
    """Every ``DW-`` token collected from BOTH ``tier3_path`` and
    ``tracked_path`` -- reuses ``_ids()`` (this module's own harvest, "reuse,
    don't reimplement" per this story's Boundaries), never a second
    tokenizer.

    A missing file contributes nothing (``_ids()`` already degrades that
    way). A file that EXISTS but fails to read -- permissions, an unreadable
    ancestor directory -- raises, rather than silently degrading to "this
    file contributes nothing" (Review Triage Log 2026-08-15, item 1): a
    silent empty contribution here can MASK an already-minted id, producing
    exactly the duplicate-mint failure this whole function exists to
    prevent -- the same masking-prevention philosophy ``_probe``/``_is_file``
    already enforce elsewhere in this module (3 documented prior incidents
    of exactly this pattern), and mirroring ``_load_deferred_work_baseline``'s
    own "visible on failure" precedent (there, a named finding; here, since
    this is a pure computation with no findings list to append to, a raised
    ``OSError`` the caller cannot silently ignore). Only ``OSError`` is
    caught and re-raised this way -- a programmer/type error is never
    mistaken for a read failure and must propagate as itself."""
    tokens: set[str] = set()
    for path in (tier3_path, tracked_path):
        try:
            tokens |= _ids(path)
        except OSError as exc:
            raise OSError(
                f"{path} exists but could not be read while collecting "
                "existing DW- ids for minting -- refusing to silently treat "
                "it as contributing zero ids, which could mask an existing "
                f"id and produce a duplicate mint: {exc}"
            ) from exc
    return tokens


def _next_free_suffix(base_id: str, collected: set[str]) -> int | None:
    """step-04-review.md step 3's whole-remainder-must-be-a-plain-integer
    counting rule: a collected id counts toward ``base_id``'s suffix only
    when it IS ``base_id`` (counts as ``1``), or is ``base_id`` followed by
    ``-`` and a remainder that is one plain integer and nothing else --
    judged against the WHOLE remainder, never just its last segment, so
    e.g. ``DW-1-10-1`` never counts toward base ``DW-1-1`` (its remainder
    would be ``0-1``, not a plain integer). Comparison is numeric, never
    lexicographic.

    Returns ``None`` when nothing counts at all -- neither the bare base id
    nor any qualifying suffix was collected -- meaning the base id itself is
    free to mint bare (the caller's call for non-mason stations). Otherwise
    returns one past the highest counting suffix."""
    highest: int | None = 1 if base_id in collected else None
    prefix = base_id + "-"
    for token in collected:
        if not token.startswith(prefix):
            continue
        remainder = token[len(prefix):]
        if _PLAIN_INT_RE.match(remainder):
            n = int(remainder)
            if highest is None or n > highest:
                highest = n
    return None if highest is None else highest + 1


#: The fleet's 8 real stations (one per `_bmad-output/projects/pyforge-*/`
#: directory) -- no existing canonical enum/list of station slugs was found
#: anywhere in this package or `models.py` to reuse (checked per Review
#: Triage Log 2026-08-15, item 3), so this is a minimal, deliberately local
#: set rather than a hand-rolled shape-only check.
_KNOWN_STATIONS = frozenset({
    "atlas", "doctor", "herald", "marshal", "mason", "scribe", "steward", "warden",
})


def _normalize_station(station: str) -> str:
    """Normalize a caller-supplied ``station`` defensively: strip
    surrounding whitespace, lowercase, and drop an optional leading
    ``pyforge-`` package-naming prefix (e.g. ``pyforge-mason`` ->
    ``mason``) -- so common variants of the same station resolve
    identically rather than an unnormalized literal comparison silently
    mismatching and taking the wrong branch (Review Triage Log 2026-08-15,
    item 3: ``"pyforge-mason"``, ``"Mason"``, or a garbage/empty value all
    used to silently fall through to the FU-prefixed branch, corrupting
    mason's id shape with no symptom).

    Raises ``ValueError`` naming the original value when it still does not
    match the known 8-station set after normalization -- a loud failure
    instead of a silently-wrong id shape."""
    normalized = station.strip().lower().removeprefix("pyforge-")
    if normalized not in _KNOWN_STATIONS:
        raise ValueError(
            f"unrecognized station {station!r}; expected one of "
            f"{sorted(_KNOWN_STATIONS)}"
        )
    return normalized


def mint_id_for_entry(
    entry: LegacyEntry,
    station: str,
    tier3_path: Path,
    tracked_path: Path,
    already_minted: set[str] | None = None,
) -> str:
    """Mint the next free ``DW-`` id for ``entry`` per station convention
    (Story 8.2) -- the reusable, testable form of step-04-review.md's
    "Minting the id" prose. Pure computation: reads ``tier3_path``/
    ``tracked_path`` to collect existing ids via ``_collect_dw_tokens``,
    never writes to either (that's Story 8.3).

    Raises ``ValueError`` if ``entry.id`` is already set -- minting a fresh
    id for an entry that already carries one would produce a redundant,
    orphaned id rather than reusing the entry's real identity (Review
    Triage Log 2026-08-15, item 4).

    Derives ``{story}`` from ``entry.fields["source_spec"]`` via
    ``_derive_story_key``, raising ``ValueError`` if that field is missing
    or blank -- there is no key to derive a story from, and minting an id
    with an empty story segment would be exactly the anonymous-entry
    failure this whole mechanism exists to eliminate.

    ``station`` is normalized/validated via ``_normalize_station`` before
    the mason/non-mason branch below (Review Triage Log 2026-08-15, item 3).
    ``station == "mason"`` (after normalization) always mints a suffixed
    ``DW-{story}-<n>`` (never bare, mason's own real convention -- see
    ``DW-1-10-1``'s ``promoted:`` note in its tracked ledger). Every other
    known station mints bare ``DW-FU-{story}`` unless that bare id or a
    ``DW-FU-{story}-...`` id was already collected, in which case
    ``DW-FU-{story}-<n>`` one past the highest counting suffix.

    ``already_minted`` is an optional accumulator of ids minted earlier in
    the SAME in-progress batch that have not yet been written to either
    ledger file (Review Triage Log 2026-08-15, item 2 -- the HIGH-severity
    batch-minting collision: calling this function repeatedly for entries
    that share a derived story key, with no way to see each other's
    not-yet-written mints, produced 24x duplication of a single id
    live-verified against the real fleet ledgers). When supplied, its
    contents are folded into the collected-id set exactly as if they had
    already been read from ``tier3_path``/``tracked_path`` -- a caller doing
    bulk minting passes one shared ``set[str]``, adding each returned id to
    it after every call, and never collides within one batch."""
    if entry.id is not None:
        raise ValueError(
            f"entry at line {entry.start_line} already carries id "
            f"{entry.id!r} -- cannot mint a redundant id for an "
            "already-identified entry"
        )
    source_spec = entry.fields.get("source_spec")
    if source_spec is None or not source_spec.strip():
        raise ValueError(
            f"entry at line {entry.start_line} carries no source_spec field -- "
            "cannot derive a story key to mint an id from"
        )
    station_norm = _normalize_station(station)
    story = _derive_story_key(source_spec)
    collected = _collect_dw_tokens(tier3_path, tracked_path)
    if already_minted:
        collected = collected | already_minted

    if station_norm == "mason":
        base_id = f"DW-{story}"
        n = _next_free_suffix(base_id, collected)
        return f"{base_id}-{1 if n is None else n}"

    base_id = f"DW-FU-{story}"
    n = _next_free_suffix(base_id, collected)
    return base_id if n is None else f"{base_id}-{n}"


def _load_deferred_work_baseline(
    target: Path,
) -> tuple[dict[str, int] | None, dict | None]:
    """The committed anonymous-Tier-3-entry grandfather baseline (Story 7.2),
    or ``(None, <finding>)`` when it is missing, unreadable, or not the
    expected ``{project_slug: count}`` shape -- mirrors ``_drift_findings``'s
    own load-and-degrade shape (chain.py:985-1000, Design Notes): loaded ONCE
    here, before ``_deferred_work_findings``'s per-project loop, degrading to
    exactly ONE named finding on failure rather than raising.

    Silently treating a missing/malformed baseline as "every project's count
    is 0" would flood every pre-existing anonymous Tier-3 entry across the
    fleet as a fresh FAIL on the very next landing pass -- the exact
    regression Story 7.2's baseline exists to prevent (Boundaries), so a
    caller that gets ``None`` back here must skip the Tier-3-anonymous check
    entirely, not guess."""
    baseline_path = target / DEFERRED_WORK_BASELINE_REL
    rel = DEFERRED_WORK_BASELINE_REL.as_posix()
    try:
        found = _is_file(baseline_path)
    except Exception:  # noqa: BLE001 -- an unreadable ancestor directory
        # (`_is_file` raises rather than lying, per this module's own
        # `_probe` convention) must degrade the same as a missing file, not
        # propagate past this function and discard every project's
        # already-computed findings via the outer `degrade_on_exception`.
        found = None
    if not found:
        return None, {
            "kind": "no-deferred-work-baseline",
            "detail": (f"{rel} missing: run "
                       f"scripts/deferred_work_baseline.py --write-baseline"),
        }
    try:
        data = json.loads(baseline_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 -- an unreadable/malformed baseline is
        # "no baseline to compare against", not a crash (Boundaries).
        return None, {
            "kind": "no-deferred-work-baseline",
            "detail": (f"{rel} is unreadable: run "
                       f"scripts/deferred_work_baseline.py --write-baseline"),
        }
    if not isinstance(data, dict) or not all(
        isinstance(k, str) and isinstance(v, int) and not isinstance(v, bool)
        and v >= 0
        for k, v in data.items()
    ):
        return None, {
            "kind": "no-deferred-work-baseline",
            "detail": (f"{rel} is not the expected {{project: count}} shape: "
                       f"run scripts/deferred_work_baseline.py "
                       f"--write-baseline"),
        }
    return data, None


def _check_project_deferred_work(
    target: Path, proj: Path, findings: list[dict], baseline: dict[str, int] | None,
) -> None:
    """Append one project's deferred-work findings to the CALLER's
    ``findings`` list -- verbatim logic from the original's own ``scan()``
    body, split out so its caller can isolate one project's failure from the
    rest (mirrors ``_check_project_sharded`` above and
    ``sources/board.py``'s own per-project split).

    Both ledger probes go through ``_is_file``, which raises rather than
    answering ``False`` for an unreadable ancestor -- ``Path.is_file()`` made
    an unreadable ``implementation-artifacts/`` read as "this project defers
    nothing" (two real FAILs became a confident ``deferred-work ok``,
    reproduced live during review) and an unreadable ``planning-artifacts/``
    read as "the tracked ledger does not exist", asserting the WHOLE record
    was gitignored about a project whose ledger is right there. The caller's
    per-project try/except turns both into a named WARN.

    ``baseline`` is the anonymous-Tier-3-entry grandfather baseline (Story
    7.3), already loaded ONCE by ``_deferred_work_findings`` before its
    per-project loop -- ``None`` when it could not be loaded, in which case
    that caller already appended its own ``no-deferred-work-baseline``
    finding and this function's job is simply to skip the Tier-3-anonymous
    check for this project (never to guess count 0)."""
    t3_path = proj / TIER3_REL
    tracked_path = proj / TRACKED_REL
    if not _is_file(t3_path):
        return

    # FILE-level check: an ID-only comparison silently passes a project with
    # NO tracked ledger at all whose Tier-3 entries happen not to use `DW-`
    # ids (verbatim rationale from the original).
    size = t3_path.stat().st_size
    if not _is_file(tracked_path) and size >= _SUBSTANTIVE_BYTES:
        findings.append({
            "kind": "no-tracked-ledger", "project": proj.name, "id": "",
            "tier3": str(t3_path.relative_to(target)),
            "tracked": str(tracked_path.relative_to(target)),
            "tier3_bytes": size, "generic_id": False,
        })

    for entry_id, has_status in _entries(tracked_path):
        if has_status:
            continue
        findings.append({
            "kind": "ledger-entry-unstatused", "project": proj.name, "id": entry_id,
            "tier3": str(t3_path.relative_to(target)),
            "tracked": str(tracked_path.relative_to(target)),
            "generic_id": False,
        })
    for n in _anonymous(tracked_path):
        findings.append({
            "kind": "ledger-entry-unidentified", "project": proj.name, "id": f"line {n}",
            "tier3": str(t3_path.relative_to(target)),
            "tracked": str(tracked_path.relative_to(target)),
            "generic_id": False,
        })

    # Tier-3-anonymous check (Story 7.3, CAP-2/CAP-3): a POSITIONAL slice,
    # not a lookup -- `_anonymous()` returns Tier-3 anonymous entries' line
    # numbers in file order, and the file's append-only discipline makes
    # "beyond the stamped count" equivalent to "new" (Design Notes). Skipped
    # entirely when the baseline could not be loaded, never treated as
    # count 0.
    if baseline is not None:
        count = baseline.get(proj.name, 0)
        for n in _anonymous(t3_path)[count:]:
            findings.append({
                "kind": "tier3-entry-unidentified", "project": proj.name,
                "id": f"line {n}",
                "tier3": str(t3_path.relative_to(target)),
                "tracked": str(tracked_path.relative_to(target)),
                "generic_id": False,
            })

    t3 = _ids(t3_path)
    if not t3:
        return
    tracked = _ids(tracked_path)
    for dw in sorted(t3 - tracked):
        findings.append({
            "kind": "tier3-only-deferral", "project": proj.name, "id": dw,
            "tier3": str(t3_path.relative_to(target)),
            "tracked": str(tracked_path.relative_to(target)),
            "generic_id": bool(_GENERIC_RE.match(dw)),
        })


def _deferred_work_findings(target: Path) -> list[dict]:
    """Every project's deferred-work findings. Each project is evaluated
    inside its own try/except: one project's unreadable Tier-3/tracked
    ledger must not discard another, ALREADY-COMPUTED project's real
    findings -- the same isolation discipline as ``_sharded_findings`` above,
    structured in from the first draft (Design Notes).

    The Tier-3-anonymous grandfather baseline (Story 7.3) is loaded ONCE
    here, before the per-project loop, mirroring ``_drift_findings``'s own
    shape (Design Notes): a missing/malformed baseline appends exactly ONE
    ``no-deferred-work-baseline`` finding and every project below is then
    passed ``baseline=None``, which skips its own Tier-3-anonymous check
    rather than guessing count 0."""
    findings: list[dict] = []
    projects_dir = target / "_bmad-output" / "projects"
    if not _is_dir(projects_dir):
        return findings
    baseline, baseline_finding = _load_deferred_work_baseline(target)
    if baseline_finding is not None:
        findings.append(baseline_finding)
    for proj in sorted(p for p in projects_dir.iterdir() if p.is_dir()):
        try:
            _check_project_deferred_work(target, proj, findings, baseline)
        except Exception as exc:  # noqa: BLE001 -- one project's unreadable
            # ledger must not discard findings already appended for a
            # different project.
            findings.append({
                "kind": "deferred-work-unevaluable", "project": proj.name, "id": "",
                "detail": (f"{proj.name}: could not be evaluated here — "
                           f"{exc.__class__.__name__}: {exc}"),
                "warn": True,
            })
    return findings


def _deferred_work_message(item: dict) -> str:
    """Human-readable message text per finding kind -- verbatim from the
    original's own ``main()`` print branches (plus the two Story 7.3
    branches, ``tier3-entry-unidentified``/``no-deferred-work-baseline``,
    which have no origin script to be verbatim from)."""
    kind = item["kind"]
    if kind == "no-tracked-ledger":
        return (f"{item['project']}: {item['tier3']} holds "
                f"{item['tier3_bytes'] / 1024:.0f} KB of deferred work and "
                f"{item['tracked']} does not exist — the WHOLE record is gitignored.")
    if kind == "ledger-entry-unstatused":
        return (f"{item['project']}/{item['id']}: no `status:` line in "
                f"{item['tracked']} — it cannot be counted as open or closed.")
    if kind == "ledger-entry-unidentified":
        return (f"{item['project']} {item['id']} of {item['tracked']}: an entry "
                f"with no `## DW-<scope>-<n>` heading — it cannot be cited, "
                f"deduped, or individually closed.")
    if kind == "tier3-entry-unidentified":
        return (f"{item['project']} {item['id']} of {item['tier3']}: an entry "
                f"with no `## DW-<scope>-<n>` heading, beyond the grandfathered "
                f"baseline count — it cannot be cited, deduped, or individually "
                f"closed.")
    if kind == "tier3-only-deferral":
        hint = ""
        if item.get("generic_id"):
            hint = ("  — a generic id: bmad-loop's own damping output. Rename it "
                    "to the ledger's DW-<story>-<n> convention on promotion, or "
                    "the next damped story collides with it.")
        return (f"{item['project']}/{item['id']}: present in {item['tier3']} "
                f"but NOT in {item['tracked']}{hint}")
    if kind == "no-deferred-work-baseline":
        return item["detail"]
    return item.get("detail", f"{item['project']}: {kind}")


def gather_deferred_work(target: Path) -> tuple[Finding, ...]:
    """Judge whether every Tier-3 (gitignored) deferred-work id has a
    durable, tracked twin -- the library form of
    ``scripts/deferred_work_check.py``'s own ``main()``, minus the
    print/exit CLI surface. Every violation becomes one FAIL ``Finding``; no
    Tier-3 ledgers at all (or all fully promoted) degrades to a vacuous OK
    rather than raising.
    """
    return degrade_on_exception(
        Source.DEFERRED_WORK, "deferred-work", lambda: _gather_deferred_work(target)
    )


def _gather_deferred_work(target: Path) -> tuple[Finding, ...]:
    raw = _deferred_work_findings(target)
    if not raw:
        projects_dir = target / "_bmad-output" / "projects"
        # No projects tree at all: `target` is not a monorepo root (same
        # reasoning as `_gather_dream_chain`'s own guard above -- the
        # original was anchored to its own REPO_ROOT). "Every Tier-3
        # deferral has a tracked twin" is a true-but-vacuous claim about
        # zero deferrals, and reads as a clean bill of health.
        if not _is_dir(projects_dir):
            return (
                Finding(
                    source=Source.DEFERRED_WORK,
                    check="deferred-work-unevaluable",
                    status=DoctorStatus.WARN,
                    message=(
                        f"_bmad-output/projects/ does not exist under "
                        f"{target} — deferred-work durability cannot be "
                        f"evaluated here"
                    ),
                    evidence={"target": str(target)},
                ),
            )
        scanned = [
            p.name for p in projects_dir.iterdir()
            if p.is_dir() and (p / TIER3_REL).is_file()
        ]
        return (
            Finding(
                source=Source.DEFERRED_WORK,
                check="deferred-work",
                status=DoctorStatus.OK,
                message="every Tier-3 deferral has a tracked twin",
                evidence={"projects_scanned": len(scanned)},
            ),
        )
    return tuple(
        Finding(
            source=Source.DEFERRED_WORK,
            check=item["kind"],
            status=DoctorStatus.WARN if item.get("warn") else DoctorStatus.FAIL,
            message=_deferred_work_message(item),
            evidence={
                k: v for k, v in item.items()
                if k not in ("kind", "warn")
            },
        )
        for item in raw
    )


# === gather_due_for_verification ===============================================
#
# Epic 11/CAP-1 (Story 11.1). Tracked `deferred-work-ledger.md` entries are
# claims about code truth AT AUTHORING TIME; nothing previously batched
# "which entries have never been re-checked, or were re-checked too long
# ago" without hand-enumerating ~400+ entries across the fleet's 8 projects.
# This selector answers that, per project, mirroring `gather_deferred_work`'s
# shape end to end (Code Map) -- but it INFORMS rather than gates: status is
# always WARN, never FAIL (Boundaries), and every ID'd entry is considered
# regardless of its `status:` (closed/done entries are not exempt -- the
# 2026-07-30 precedent found regressions among them too).

#: Resolved (Design Notes): no fleet precedent judges "code-claim
#: re-verification cadence" directly (checked warden's
#: `DEFAULT_FEED_MAX_AGE_DAYS=7`, `DB_MAX_AGE_DAYS=7`,
#: `_REGISTRY_MAX_AGE_DAYS=180`, `waiver_default_expiry_days=14` -- none
#: fits) -- roughly double the closest human-judgment analog
#: (`waiver_default_expiry_days=14`), rounded to a full month, since
#: re-verifying 400+ entries fleet-wide is heavier than one waiver review.
#: A named constant so it can be retuned later without touching any call
#: site (review finding, patch: the prior comment's "double 14" read as
#: 28, not 30 -- corrected to "roughly double, rounded to a month").
DUE_FOR_VERIFICATION_STALENESS_DAYS = 30

_VERIFIED_RE = re.compile(r"^\s*verified:\s*(.+)$", re.M)


def _verification(path: Path) -> list[tuple[str, str | None]]:
    """``(id, raw_verified_text)`` for every ID'd entry in a tracked ledger --
    duplicates ``_entries()``'s own ~10-line boundary-walk shape rather than
    extracting a shared primitive from a function documented as "verbatim
    from the original" (Design Notes: `_entries()` stays untouched).
    ``raw_verified_text`` is the entry's own MOST RECENT ``verified:`` line,
    unparsed (``None`` when the entry carries no such line at all) -- date
    PARSING happens one layer up (`_parse_verified_date`), so a malformed
    date degrades to "never-verified" rather than raising here.

    Takes the LAST ``verified:`` line in the entry's span, not the first:
    reconciliation appends a fresh ``verified:`` line rather than replacing
    the old one (review finding, patch), so the first match would pin
    staleness to an entry's OLDEST re-check forever, even after a genuinely
    fresh re-verification landed right below it."""
    if not _is_file(path):
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    marks = [(m.start(), m.group(1)) for m in _ENTRY_RE.finditer(text)]
    out = []
    for i, (pos, ident) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        matches = list(_VERIFIED_RE.finditer(text[pos:end]))
        out.append((ident, matches[-1].group(1).strip() if matches else None))
    return out


def _parse_verified_date(raw: str) -> date | None:
    """The leading ``YYYY-MM-DD`` token of a raw ``verified:`` line's value,
    or ``None`` when it cannot be parsed as one -- a malformed date must fail
    toward re-checking ("never-verified"), never raise (I/O matrix)."""
    token = raw.strip().split(maxsplit=1)[0] if raw.strip() else ""
    try:
        return date.fromisoformat(token)
    except ValueError:
        return None


# --- Story 11.2: churn-based cost filtering ------------------------------------
#
# A due entry is a claim about code truth AT AUTHORING TIME (module banner
# above); most of the ~400+ due entries fleet-wide name code that has not
# moved SINCE that claim was made, so the next story's (11.3) expensive
# mechanical/agent re-verification would be spending budget on entries
# nothing could have invalidated. This section computes -- but never acts
# on -- that signal: which due entries have zero git commits, anywhere in
# this repo, to any of their own ledger-cited code paths since the entry's
# churn window opened. It tags the SAME 11.1 finding with an ADDITIVE
# `skip_reason: "no-churn"` evidence key; it never adds, removes, or
# reshapes a Finding (Boundaries).

#: A backtick-quoted token that names a code path: a bare word (an id, a
#: flag, a function name) is ambiguous prose, but a `.`-extension or a `/`
#: path separator is not -- optionally followed by a `:<LINE>` locator
#: (`foo.py:10`), captured OUTSIDE the path group and discarded, since git
#: operates on files, never on lines within one. Matching only WITHIN
#: backticks (never bare prose) mirrors how every ledger entry already
#: cites code today. Over-matching (e.g. a dotted version string) is safe
#: by design: an extracted token that is not a real path simply fails to
#: resolve in `_churn_since`'s own step 1 and falls back to "not skipped"
#: -- the same fail-safe direction as every other edge case here
#: (Boundaries), so this pattern does not need to be exhaustively precise.
_PATH_TOKEN_RE = re.compile(
    r"`([\w][\w./-]*(?:\.[A-Za-z0-9]+|/[\w.-]+))(?::\d+)?`"
)

#: Any physical line carrying a `source_spec:` field, bulleted (`-
#: source_spec: ...`) or plain (`source_spec: ...`) -- both shapes occur
#: live (`Tier3Shape`'s own docstring above). `_entry_named_paths` strips
#: these lines before extracting path tokens: `source_spec:` names WHERE
#: the entry came from, not the code under its claim, so a `.md` spec path
#: living there must never become a churn-check candidate (Boundaries).
_SOURCE_SPEC_LINE_RE = re.compile(r"^.*\bsource_spec:.*$", re.M)


def _entry_named_paths(path: Path) -> list[tuple[str, list[str]]]:
    """``(id, [paths])`` for every ID'd entry in a tracked ledger --
    duplicates ``_verification()``'s own boundary-walk shape rather than
    extracting a shared primitive (Design Notes: neither `_entries()` nor
    `_verification()` is touched by this story).

    ``paths`` are the entry's own body's `_PATH_TOKEN_RE` matches, in
    first-seen order with duplicates removed, computed AFTER stripping any
    `source_spec:` line from the body (`_SOURCE_SPEC_LINE_RE`) so that
    field's own path-shaped value is never a candidate. The strip removes
    the WHOLE physical line, not just the field's value (review finding:
    documented precisely, since the ledger format's one-field-per-line
    convention means no real entry co-locates a legitimate code citation
    on the same line as `source_spec:` -- narrowing the strip to just the
    value would add regex complexity for a case that does not occur)."""
    if not _is_file(path):
        return []
    text = path.read_text(encoding="utf-8", errors="replace")
    marks = [(m.start(), m.group(1)) for m in _ENTRY_RE.finditer(text)]
    out = []
    for i, (pos, ident) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
        body = _SOURCE_SPEC_LINE_RE.sub("", text[pos:end])
        seen: list[str] = []
        for m in _PATH_TOKEN_RE.finditer(body):
            token = m.group(1)
            if token not in seen:
                seen.append(token)
        out.append((ident, seen))
    return out


def _authored_date(target: Path, tracked_path: Path, entry_id: str) -> date | None:
    """The date ``entry_id`` was first introduced into ``tracked_path``'s
    own git history -- the "since authoring" churn-window start for a
    never-verified entry, which carries no ``verified:`` date of its own.

    The ``-G`` pickaxe pattern anchors the id's right boundary with
    ``[^A-Za-z0-9-]`` (any character NOT in the id charset, ``_ENTRY_RE``'s
    own ``[A-Za-z0-9-]``) rather than searching for the bare id via ``-S``:
    verified live (Boundaries) that a plain substring search for a SHORTER
    id collides with any LONGER id sharing the same prefix (``DW-1-1-1`` is
    a left-anchor prefix of ``DW-1-1-10``) and silently returns the WRONG,
    earlier introduction date -- the longer id's own commit, not the
    entry's own. The id charset contains no regex metacharacters (Design
    Notes), so ``entry_id`` needs no escaping before interpolation.

    ``--reverse`` + first line gives the EARLIEST matching commit -- the
    entry's own introduction, not a later edit. ``--follow`` is a no-op
    unless git detects ``tracked_path`` was renamed somewhere in its
    history, in which case it lets the search see the pre-rename history
    too -- safe to always pass, and closes an otherwise-real gap: without
    it, a ledger rename would truncate the search to only post-rename
    history and could resolve too LATE a date, narrowing the churn window
    and masking real earlier churn (review finding, patch). Returns
    ``None`` -- never raises -- on any git failure, an empty match (the
    ledger was never committed, or genuinely has no commit whose diff
    introduced this id's literal text), or an unparseable date, so the
    caller fails toward "not skipped" (I/O matrix)."""
    rel = str(tracked_path.relative_to(target))
    try:
        out = run_git(
            target,
            [
                "log", "--reverse", "--follow", "--format=%ad", "--date=short",
                "-G", f"{entry_id}[^A-Za-z0-9-]",
                "--", rel,
            ],
        )
    except (CliBridgeError, UnicodeDecodeError):
        return None
    first = out.splitlines()[0].strip() if out.strip() else ""
    if not first:
        return None
    try:
        return date.fromisoformat(first)
    except ValueError:
        return None


def _churn_since(target: Path, rel_paths: list[str], since: date) -> bool:
    """``True`` only when EVERY path in ``rel_paths`` is both tracked in
    this repo's history (step 1) and untouched since ``since`` (step 2) --
    the two-step algorithm the Boundaries section spells out, short-
    circuiting to ``False`` on the first disqualifying path so an entry
    citing several paths does not pay for git calls on the rest once one
    has already blocked the skip.

    Step 1, ``git log --oneline -1 -- <path>``: empty means the path has
    NO history in this repo at all -- a typo, an external package, or a
    cross-repo reference -- and must NOT read as churn-free (I/O matrix:
    "path never tracked here"). Step 2, ``git log --oneline -1 --since
    <date> -- <path>``: non-empty means at least one commit landed inside
    the window, i.e. the path DID change -- ``-1`` here too, since only
    existence-inside-the-window is asked, never the full matching set (a
    frequently-touched path would otherwise pay for git to enumerate every
    matching commit just to answer a yes/no question, working against the
    story's own cost-bound purpose -- review finding, patch).

    A ``run_git`` failure for ANY path -- ``CliBridgeError`` or
    ``UnicodeDecodeError`` -- degrades the WHOLE check to ``False`` (not
    churn-free), indistinguishable by design from a path with no tracked
    history, never raised past this function."""
    for rel in rel_paths:
        try:
            tracked = run_git(target, ["log", "--oneline", "-1", "--", rel])
        except (CliBridgeError, UnicodeDecodeError):
            return False
        if not tracked.strip():
            return False
        try:
            since_out = run_git(
                target,
                [
                    "log", "--oneline", "-1", "--since", since.isoformat(),
                    "--", rel,
                ],
            )
        except (CliBridgeError, UnicodeDecodeError):
            return False
        if since_out.strip():
            return False
    return True


def _attach_churn_skip(
    target: Path, item: dict, paths: list[str], since: date | None,
) -> None:
    """Mutate ``item`` IN PLACE, adding ``skip_reason``/
    ``churn_checked_paths`` when every one of ``paths`` is confirmed
    churn-free since ``since`` -- ADDITIVE only, ``item`` is otherwise left
    exactly as 11.1 built it (Boundaries: the SAME finding, never a new or
    removed one).

    ``since is None`` (an unresolvable never-verified authoring date) or
    ``not paths`` (nothing extractable) both fail toward "not skipped"
    WITHOUT attempting a git call at all -- the zero-path and unresolvable-
    date I/O matrix rows, and a real cost saving: most due entries cite no
    path at all, and every avoided git call matters at ~400+ entries
    fleet-wide.

    Any OTHER exception here -- a hiccup this function's own callees did
    not already catch internally -- still degrades to "not skipped" for
    THIS entry alone: it must never propagate to the project-level
    try/except in ``_due_for_verification_findings``, which exists to
    isolate a whole project's unreadable LEDGER, not a routine per-entry
    git-call failure (Boundaries)."""
    if since is None or not paths:
        return
    try:
        churn_free = _churn_since(target, paths, since)
    except Exception:  # noqa: BLE001 -- see docstring: isolate per-entry.
        return
    if churn_free:
        item["skip_reason"] = "no-churn"
        item["churn_checked_paths"] = list(paths)


def _check_project_due_for_verification(
    target: Path, proj: Path, findings: list[dict], today: date,
) -> None:
    """Append one project's due-for-verification findings to the CALLER's
    ``findings`` list -- mirrors ``_check_project_deferred_work``'s own
    per-project shape (Design Notes/Code Map); one project's unreadable
    ledger is isolated by this function's own CALLER, not here.

    Story 11.2: each finding this appends is additionally offered to
    ``_attach_churn_skip``, using the SAME already-parsed ``verified:``
    date as the churn window's start for a stale entry, or
    ``_authored_date``'s proxy for a never-verified one -- computed only
    when the entry has at least one extracted path, so an entry with
    nothing to check never pays for a git call it cannot use.

    Paired with ``zip``, POSITIONALLY, not via an id-keyed dict: both
    ``_verification()`` and ``_entry_named_paths()`` walk the SAME
    ``_ENTRY_RE`` marks over the SAME file text, so they produce entries in
    identical order and count -- but a ledger with a duplicate (malformed,
    invariant-violating) id would silently collapse to one dict entry,
    pairing an EARLIER duplicate's finding with a LATER duplicate's paths
    (review finding, patch). Positional pairing is correct regardless of
    whether ids repeat."""
    tracked_path = proj / TRACKED_REL
    paths_by_entry = _entry_named_paths(tracked_path)
    for (entry_id, raw_verified), (_, paths) in zip(
        _verification(tracked_path), paths_by_entry, strict=True,
    ):
        parsed = _parse_verified_date(raw_verified) if raw_verified else None
        if parsed is None:
            item = {
                "kind": "due-for-verification", "reason": "never-verified",
                "project": proj.name, "id": entry_id,
                "tracked": str(tracked_path.relative_to(target)),
            }
            since = _authored_date(target, tracked_path, entry_id) if paths else None
            _attach_churn_skip(target, item, paths, since)
            findings.append(item)
            continue
        days_stale = (today - parsed).days
        if days_stale > DUE_FOR_VERIFICATION_STALENESS_DAYS:
            item = {
                "kind": "due-for-verification", "reason": "stale",
                "project": proj.name, "id": entry_id,
                "tracked": str(tracked_path.relative_to(target)),
                "days_stale": days_stale,
            }
            _attach_churn_skip(target, item, paths, parsed)
            findings.append(item)


def _due_for_verification_findings(
    target: Path, *, today: date | None = None,
) -> list[dict]:
    """Every project's due-for-verification findings. Each project is
    evaluated inside its own try/except: one project's unreadable tracked
    ledger must not discard another, ALREADY-COMPUTED project's real
    findings -- the same isolation discipline as ``_deferred_work_findings``
    above (Design Notes).

    ``today`` is the injectable "as of" date (Boundaries) -- ``None``
    resolves to ``date.today()`` HERE, at the one call boundary, so every
    inner helper stays deterministic and every test can pass a fixed date
    rather than depending on wall-clock time."""
    as_of = today if today is not None else date.today()
    findings: list[dict] = []
    projects_dir = target / "_bmad-output" / "projects"
    if not _is_dir(projects_dir):
        return findings
    for proj in sorted(p for p in projects_dir.iterdir() if p.is_dir()):
        try:
            _check_project_due_for_verification(target, proj, findings, as_of)
        except Exception as exc:  # noqa: BLE001 -- one project's unreadable
            # ledger must not discard findings already appended for a
            # different project.
            findings.append({
                "kind": "due-for-verification-unevaluable",
                "project": proj.name, "id": "",
                "detail": (f"{proj.name}: could not be evaluated here — "
                           f"{exc.__class__.__name__}: {exc}"),
                "warn": True,
            })
    return findings


def _due_for_verification_message(item: dict) -> str:
    """Human-readable message text per finding.

    Story 11.2: when ``_attach_churn_skip`` tagged this item, the message
    additionally reports the skip decision -- spelling the literal
    ``skip_reason: no-churn`` value (Design Notes: the epic's own wording
    names the VALUE, not the evidence key) so a human scanning WARN output
    can tell a "no churn, deprioritized" entry apart from one still fully
    due, without opening the evidence dict."""
    kind = item["kind"]
    if kind == "due-for-verification":
        if item["reason"] == "never-verified":
            message = (f"{item['project']}/{item['id']}: no `verified:` line "
                        f"in {item['tracked']} — never re-checked against live "
                        f"code.")
        else:
            message = (f"{item['project']}/{item['id']}: last verified "
                        f"{item['days_stale']} days ago in {item['tracked']} "
                        f"(> {DUE_FOR_VERIFICATION_STALENESS_DAYS}-day threshold) — "
                        f"due for re-check.")
        if item.get("skip_reason") == "no-churn":
            message += (
                " Named code path(s) have no commits since then — "
                "skip_reason: no-churn (deprioritized, not resolved)."
            )
        return message
    return item.get("detail", f"{item['project']}: {kind}")


def gather_due_for_verification(target: Path) -> tuple[Finding, ...]:
    """Batch every tracked ledger entry due for re-verification, per
    project -- the library form the story's own Intent names, mirroring
    ``gather_deferred_work``'s DISPATCH-facing wrapper shape end to end.
    Status is always WARN, never FAIL -- this selector informs, it never
    gates (Boundaries). No due entries anywhere degrades to a vacuous OK
    rather than an empty tuple (I/O matrix), mirroring
    ``gather_deferred_work``'s own vacuous-OK shape.
    """
    return degrade_on_exception(
        Source.DUE_FOR_VERIFICATION, "due-for-verification",
        lambda: _gather_due_for_verification(target),
    )


def _gather_due_for_verification(target: Path) -> tuple[Finding, ...]:
    raw = _due_for_verification_findings(target)
    if not raw:
        projects_dir = target / "_bmad-output" / "projects"
        # No projects tree at all: `target` is not a monorepo root -- same
        # reasoning as `_gather_deferred_work`'s own guard above.
        if not _is_dir(projects_dir):
            return (
                Finding(
                    source=Source.DUE_FOR_VERIFICATION,
                    check="due-for-verification-unevaluable",
                    status=DoctorStatus.WARN,
                    message=(
                        f"_bmad-output/projects/ does not exist under "
                        f"{target} — due-for-verification cannot be "
                        f"evaluated here"
                    ),
                    evidence={"target": str(target)},
                ),
            )
        scanned = [
            p.name for p in projects_dir.iterdir()
            if p.is_dir() and (p / TRACKED_REL).is_file()
        ]
        return (
            Finding(
                source=Source.DUE_FOR_VERIFICATION,
                check="due-for-verification",
                status=DoctorStatus.OK,
                message="no tracked ledger entry is due for re-verification",
                evidence={"projects_scanned": len(scanned)},
            ),
        )
    return tuple(
        Finding(
            source=Source.DUE_FOR_VERIFICATION,
            check=item["kind"],
            status=DoctorStatus.WARN,
            message=_due_for_verification_message(item),
            evidence={
                k: v for k, v in item.items()
                if k not in ("kind", "warn")
            },
        )
        for item in raw
    )
