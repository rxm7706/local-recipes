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
import re
from pathlib import Path

import yaml

from ..cli_bridge import CliBridgeError, run_git
from ..models import DoctorStatus, Finding, Source
from . import degrade_on_exception

__all__ = ("gather_dream_chain", "gather_deferred_work", "gather_spec_surface")


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


def _collect_dreams(target: Path) -> dict[str, dict]:
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
    downstream consumer at once, instead of guarding each use site."""
    dreams: dict[str, dict] = {}
    dreams_dir = target / "docs" / "dreams"
    if not dreams_dir.is_dir():
        return dreams
    for p in _listdir(dreams_dir):
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
    ``_sharded_findings``'s own per-project isolation."""
    specs: list[dict] = []
    projects_dir = target / "_bmad-output" / "projects"
    if projects_dir.is_dir():
        for pdir in _listdir(projects_dir):
            specs_dir = pdir / "planning-artifacts" / "specs"
            if not specs_dir.is_dir():
                continue
            try:
                spec_dirs = _listdir(specs_dir)
            except OSError as exc:
                # One project's unreadable specs/ directory must not silently
                # read as "this project has no Specs" (which INV-1 would then
                # report as every one of its Dreams being spec-less).
                findings.append(_unreadable_specs_dir(pdir.name, specs_dir, exc))
                continue
            for sd in spec_dirs:
                sp = sd / "SPEC.md"
                if sp.is_file():
                    _append_spec_entry(sp, pdir.name, target, specs, findings)
    governance_dir = target / "docs" / "governance"
    if governance_dir.is_dir():
        for sd in _listdir(governance_dir):
            sp = sd / "SPEC.md"
            if sd.name.startswith("spec-") and sp.is_file():
                _append_spec_entry(sp, GOVERNANCE_PROJECT, target, specs, findings)
    return specs


def _unreadable_specs_dir(project: str, specs_dir: Path, exc: Exception) -> dict:
    """The WARN item for one project whose ``planning-artifacts/specs/``
    could not be listed -- same shape as ``_append_spec_entry``'s own
    per-spec WARN, one level up."""
    return {
        "inv": "INV-0", "kind": "dream-chain-unevaluable",
        "subject": specs_dir.name, "owner": "", "status": f"in {project}",
        "remedy": "make the project's planning-artifacts/specs/ readable, then re-check",
        "detail": (f"{project}: planning-artifacts/specs/ could not be listed "
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
    if not (pdir / "prds").is_dir():
        flat = "prd.md" in {n.lower() for n in names}
        status = "flat prd.md" if flat else "absent"
        remedy = "regenerate via bmad-prd into prds/prd-<slug>-<date>/"
        findings.append({
            "inv": "INV-3", "kind": "prd-not-sharded", "subject": project,
            "owner": "", "status": status, "remedy": remedy,
            "detail": f"{project}: PRD is {status}, not sharded — {remedy}",
        })
    if not (pdir / "architecture").is_dir():
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
    than rediscovered across review passes)."""
    projects_dir = target / "_bmad-output" / "projects"
    if not projects_dir.is_dir():
        return
    for proj in _listdir(projects_dir):
        pdir = proj / "planning-artifacts"
        if not pdir.is_dir():
            continue
        try:
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
    dreams = _collect_dreams(target)
    findings: list[dict] = []
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
        if not dreams and not specs and not (
            target / "_bmad-output" / "projects"
        ).is_dir():
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

SPEC_GLOB = "_bmad-output/projects/*/planning-artifacts/specs/spec-*/SPEC.md"
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
) -> tuple[dict[str, dict], list[dict]]:
    """Every spec's current ``{memlog, files}`` hash state, plus a WARN item
    for any spec that could not be evaluated. One spec's unreadable memlog or
    governed file must not discard another, ALREADY-COMPUTED spec's hash
    state -- the same per-unit isolation discipline
    ``sources/board.py``/``_sharded_findings`` above already apply, though the
    unit here is a spec rather than a project."""
    current: dict[str, dict] = {}
    warns: list[dict] = []
    for name, s in specs.items():
        try:
            files: dict[str, str] = {}
            if s["drift"] != "exempt":
                for f in sorted(governed.get(name, [])):
                    if f in s["exclude"]:
                        continue
                    sha = _sha1(target / f)
                    if sha is not None:
                        files[f] = sha
                    elif (target / f).exists():
                        # Dropping a PRESENT-but-unreadable governed file from
                        # the state is indistinguishable from the file being
                        # deleted -- the baseline diff then reports it FAIL
                        # `drift ... removed`, a confidently wrong finding
                        # about a file that is still right there. Only a file
                        # that is genuinely GONE may drop out silently (that
                        # `removed` is the true answer).
                        _unhashable(target / f)
            current[name] = {"memlog": _contract_hash(target, s), "files": files}
        except Exception as exc:  # noqa: BLE001 -- one spec's unreadable
            # input must not discard another spec's already-computed state.
            warns.append({
                "kind": "spec-surface-unevaluable", "path": name,
                "detail": (f"{name}: could not be evaluated here — "
                           f"{exc.__class__.__name__}: {exc}"),
                "warn": True,
            })
    return current, warns


def _drift_findings(
    target: Path, specs: dict[str, dict], current: dict[str, dict]
) -> tuple[list[dict], list[dict]]:
    """(gating findings, presumed-but-non-gating findings) from comparing
    ``current`` against the committed baseline -- verbatim logic from the
    original's own ``main()`` body (S-13.1/S-13.2/S-13.5 rationale lives in
    that script's own module docstring)."""
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
        for f in sorted(set(b_files) | set(cur["files"])):
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

    Listed through ``_listdir`` rather than ``target.glob(SPEC_GLOB)``: glob
    swallows ``OSError`` mid-traversal, so an unlistable
    ``planning-artifacts/specs/`` would read as "this project governs
    nothing" and un-govern every file it owns -- the same silent-
    governance-loss defect ``_parse_surface``'s own docstring refuses to
    reintroduce, one directory level up."""
    specs: dict[str, dict] = {}
    unsound: list[dict] = []
    projects_dir = target / "_bmad-output" / "projects"
    if not projects_dir.is_dir():
        return specs, unsound
    for proj in _listdir(projects_dir):
        specs_dir = proj / "planning-artifacts" / "specs"
        if not specs_dir.is_dir():
            continue
        try:
            spec_dirs = _listdir(specs_dir)
        except OSError as exc:
            unsound.append({
                "kind": "spec-surface-unevaluable",
                "path": f"{proj.name}/planning-artifacts/specs",
                "detail": (f"{proj.name}: planning-artifacts/specs/ could not "
                           f"be listed here — {exc.__class__.__name__}: {exc}; "
                           f"its surfaces are unknown, so coverage is not "
                           f"evaluable"),
                "warn": True,
            })
            continue
        for sd in spec_dirs:
            spec_md = sd / "SPEC.md"
            if not sd.name.startswith("spec-") or not spec_md.is_file():
                continue
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
            "kind": "spec-surface-unevaluable", "path": str(ALLOWLIST_REL),
            "detail": (f"{ALLOWLIST_REL} exists but could not be read here — "
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

    current, current_warns = _spec_current_state(target, specs, governed)
    findings.extend(current_warns)
    drift_findings, presumed = _drift_findings(target, specs, current)
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

TIER3_REL = Path("implementation-artifacts") / "deferred-work.md"
TRACKED_REL = Path("planning-artifacts") / "deferred-work-ledger.md"

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
    if not path.is_file():
        return set()
    text = path.read_text(encoding="utf-8", errors="replace")
    return {m.group(0).rstrip("-") for m in _DW_RE.finditer(text)}


def _entries(path: Path) -> list[tuple[str, bool]]:
    """``(id, has_status)`` for every ID'd entry in a tracked ledger --
    verbatim from the original."""
    if not path.is_file():
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
    if not path.is_file():
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


def _check_project_deferred_work(target: Path, proj: Path, findings: list[dict]) -> None:
    """Append one project's deferred-work findings to the CALLER's
    ``findings`` list -- verbatim logic from the original's own ``scan()``
    body, split out so its caller can isolate one project's failure from the
    rest (mirrors ``_check_project_sharded`` above and
    ``sources/board.py``'s own per-project split)."""
    t3_path = proj / TIER3_REL
    tracked_path = proj / TRACKED_REL
    if not t3_path.is_file():
        return

    # FILE-level check: an ID-only comparison silently passes a project with
    # NO tracked ledger at all whose Tier-3 entries happen not to use `DW-`
    # ids (verbatim rationale from the original).
    size = t3_path.stat().st_size
    if not tracked_path.is_file() and size >= _SUBSTANTIVE_BYTES:
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
    structured in from the first draft (Design Notes)."""
    findings: list[dict] = []
    projects_dir = target / "_bmad-output" / "projects"
    if not projects_dir.is_dir():
        return findings
    for proj in sorted(p for p in projects_dir.iterdir() if p.is_dir()):
        try:
            _check_project_deferred_work(target, proj, findings)
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
    original's own ``main()`` print branches."""
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
    if kind == "tier3-only-deferral":
        hint = ""
        if item.get("generic_id"):
            hint = ("  — a generic id: bmad-loop's own damping output. Rename it "
                    "to the ledger's DW-<story>-<n> convention on promotion, or "
                    "the next damped story collides with it.")
        return (f"{item['project']}/{item['id']}: present in {item['tier3']} "
                f"but NOT in {item['tracked']}{hint}")
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
        if not projects_dir.is_dir():
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
