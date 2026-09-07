"""Meta: no bare retired BMAD v6 skill ID survives on the swept live surfaces.

The 2026-08-21/22 upgrade to BMAD 6.11.0 retired 20 v6 skill names. Each
survives today only as a deprecated forwarder shim, and upstream's
`v6-shims/README.md` commits to exactly one breakage: "Removal rides the v7
cut -- never a 6.x minor". The 2026-08-22 alignment inventory
(`_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/
spec-bmad-611-era-alignment/alignment-inventory.md`, findings #2 and #3)
found the retired names still living in exactly the places that hurt:

  * `seed/templates/files/dream-first-workflow.md.j2` told every NEW station
    Marshal drives the build via `bmad-dev-auto` -- an instruction that
    becomes a dead skill reference on the day the shims disappear, shipped
    to repos that never contained the old name in the first place.
  * six planning artifacts plus AGENTS.md named retired skills in live
    (non-historical) instruction text, e.g. steward's backlog guidance
    "prefer bmad-quick-dev" for stories not yet run.

Story 25.1 (spec-bmad-611-era-alignment CAP-1) swept those surfaces: live
dispatch-instruction text was renamed to the 6.11 name outright; historical
or narrative text keeps its recorded name plus a gloss (shipped history is
never rewritten). This test is the regression guard between now and the v7
cut: a bare reintroduction reds the suite while a properly glossed historical
mention stays green.

THE ONE ALLOW RULE (mechanical, line-based -- deliberately a single rule so
it cannot accumulate case law): an occurrence of a retired ID is allowed iff
its own line also carries an allow marker -- the version "6.11" (anchored:
not inside "v8.6.11" or "16.11" or "6.111") or one of the whole words
retired / forwarder(s) / shim(s) / deprecated, case-insensitively. See
ALLOW_MARKER_RE below for the exact pattern. That covers every legitimate
survivor: a gloss ("the retired 6.x name of `bmad-build-auto`"), a rename
record ("6.11: `bmad-prd`"), and prose about the shim/forwarder mechanism
itself. Marker literals that parsers depend on (e.g. the Tier-3
"bmad-dev-auto step-04" ledger marker described in doctor's epics) are kept
verbatim and carry a gloss on the same line, so they pass under the same
rule. Same-line-ness is the point: a marker on an adjacent line allows
nothing.

ID matching is case-insensitive (the allow rule already is; `BMAD-Dev-Auto`
must not escape) and boundary-guarded on both sides: a left boundary
``(?<![A-Za-z0-9_-])`` so `x-bmad-quick-dev` does not false-fire, and a
right boundary ``(?![A-Za-z0-9_])`` that deliberately ADMITS a trailing
hyphen so a compound like `bmad-dev-auto-driven` still fires the base ID.
The longest-first ordered alternation keeps `bmad-editorial-review-prose` /
`-structure` matching as their own listed IDs rather than double-firing the
shorter `bmad-editorial-review`.

Two scope exclusions are deliberate, not gaps: per-user auto-memory under
~/.claude is outside the repo and owned by the fleet session that dispatched
this story (its remit, per the story spec's Never list); and code surfaces
are excluded because the `[dev] skill = "bmad-dev-auto"` adapter
discriminator is Spec-mandated to survive -- bmad-loop resolves the invoked
skill on disk, so that literal is load-bearing, not a stale instruction.

The scan scope is an include-list (not a repo walk): the seed templates every
new station inherits, the fleet's planning epics/PRDs, and the two cross-tool
entry points. A shrunken or empty resolution of that list is itself a failure
(glob rot must be loud, never a silent no-op), with a per-glob floor so one
surface cannot collapse behind another's growth.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

# .claude/skills/<skill>/tests/meta/<file> -> repo root.
SKILL_DIR = Path(__file__).resolve().parent.parent.parent
REPO_ROOT = SKILL_DIR.parents[2]

# The published 20-shim v6.11.0 list (upstream v6-shims/README.md; installer
# prompt #2746 counts 20) plus one 6.12.0 addition (bmad-checkpoint-preview,
# renamed to bmad-walkthrough) -- 21 guarded ids total. These are the only IDs
# guarded -- still-live skills that merely LOOK similar (bmad-review,
# bmad-prd, bmad-sprint-planning, bmad-create-epics-and-stories) are not in
# this tuple.
RETIRED_SKILL_IDS = (
    "bmad-quick-dev",
    "bmad-dev-auto",
    "bmad-create-story",
    "bmad-dev-story",
    "bmad-create-prd",
    "bmad-edit-prd",
    "bmad-validate-prd",
    "bmad-create-architecture",
    "bmad-market-research",
    "bmad-domain-research",
    "bmad-technical-research",
    "bmad-sprint-status",
    "bmad-document-project",
    # 2026-09-06: 6.12.0 ships this id as neither a new `skill_renames` entry
    # nor a `removals` entry -- it still ships a live `lifecycle: shim` skill
    # directory under the package's plan/ tree. It is NOT orphaned; it stays
    # guarded here on its own pre-existing (6.11) merit.
    "bmad-generate-project-context",
    "bmad-review-adversarial-general",
    "bmad-review-edge-case-hunter",
    "bmad-review-verification-gap",
    "bmad-editorial-review",
    "bmad-editorial-review-prose",
    "bmad-editorial-review-structure",
    # 2026-09-06: BMAD-METHOD 6.12.0 renamed this shim to `bmad-walkthrough`
    # (bmad_core_releases/6.12.0.yaml skill_renames). 21st guarded id.
    "bmad-checkpoint-preview",
)

# Longest-first so the reported match is the most specific retired ID.
# Boundaries: see the module docstring -- left blocks `x-bmad-quick-dev`,
# right admits a trailing hyphen so `bmad-dev-auto-driven` fires the base ID.
RETIRED_ID_RE = re.compile(
    r"(?<![A-Za-z0-9_-])("
    + "|".join(
        re.escape(i) for i in sorted(RETIRED_SKILL_IDS, key=len, reverse=True)
    )
    + r")(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

# The ONE mechanical allow rule (see module docstring): anchored "6.11" or a
# whole-word retired/forwarder(s)/shim(s)/deprecated, case-insensitive.
ALLOW_MARKER_RE = re.compile(
    r"(?<![\d.])6\.11(?!\d)|\b(?:retired|forwarders?|shims?|deprecated)\b",
    re.IGNORECASE,
)

# Include-list scan scope with per-glob rot floors. Relative to REPO_ROOT.
# Floors sit below the live counts (2026-08-22: 8 epics.md, 1 PRD.md,
# 11 template files, 1 AGENTS.md, 1 CLAUDE.md) so ordinary churn passes,
# but a collapsed surface reds even if another surface grows.
# `**/*` (not bare `**`): pre-3.13 pathlib `**` matches directories only;
# `**/*` matches files at all depths on every supported Python.
SCAN_GLOB_FLOORS = {
    "_bmad-output/projects/*/planning-artifacts/epics.md": 6,
    "_bmad-output/projects/*/planning-artifacts/PRD.md": 1,
    "src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/templates/**/*": 8,
    "AGENTS.md": 1,
    "CLAUDE.md": 1,
}
SCAN_GLOBS = tuple(SCAN_GLOB_FLOORS)

# Non-text artifacts that may appear under a **/* glob.
SKIP_DIR_NAMES = {"__pycache__"}
SKIP_SUFFIXES = {".pyc"}


def resolve_scan_set(root: Path) -> dict[str, list[Path]]:
    """Resolve SCAN_GLOBS to concrete files, keyed by the glob that found them."""
    resolved: dict[str, list[Path]] = {}
    for pattern in SCAN_GLOBS:
        files = sorted(
            p
            for p in root.glob(pattern)
            if p.is_file()
            and p.suffix not in SKIP_SUFFIXES
            and not (SKIP_DIR_NAMES & set(p.relative_to(root).parts))
        )
        resolved[pattern] = files
    return resolved


def scan_lines(lines: list[str]) -> list[tuple[int, str]]:
    """Return (1-based line number, retired id) for every disallowed occurrence."""
    violations: list[tuple[int, str]] = []
    for lineno, line in enumerate(lines, start=1):
        # One allow-rule check per line; a marked line needs no ID scan.
        if ALLOW_MARKER_RE.search(line):
            continue
        for match in RETIRED_ID_RE.finditer(line):
            violations.append((lineno, match.group(1)))
    return violations


def scan_file(path: Path) -> list[tuple[int, str]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return scan_lines(text.splitlines())


# Steward's CAP-1 pre-flight release catalog -- see Design Notes: this is a
# NARROWER set than RETIRED_SKILL_IDS (it only tracks steward's rename/legacy
# bookkeeping), so the consistency check below is one-directional (catalog
# subset-of guard), never full derivation.
BMAD_CORE_RELEASES_GLOB = (
    "src/shared/packages/pyforge-steward/src/pyforge/steward/data/"
    "bmad_core_releases/*.yaml"
)


def _catalog_files(root: Path) -> list[Path]:
    return sorted(root.glob(BMAD_CORE_RELEASES_GLOB))


def _collect_unguarded_catalog_renames(
    catalog_paths: list[Path], guarded_ids: tuple[str, ...]
) -> list[str]:
    """Return "from-id (source.yaml)" for every skill_renames[].from not guarded."""
    unguarded: list[str] = []
    for path in catalog_paths:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for rename in data.get("skill_renames") or []:
            from_id = rename["from"]
            if from_id not in guarded_ids:
                unguarded.append(f"{from_id} ({path.name})")
    return unguarded


def _assert_catalog_renames_guarded(
    catalog_paths: list[Path], guarded_ids: tuple[str, ...] = RETIRED_SKILL_IDS
) -> None:
    """One-directional subset check: every catalog rename id is guarded.

    Shared by the real-catalog test and its fixture-based red-on-plant proof
    so both exercise the identical assertion logic.
    """
    unguarded = _collect_unguarded_catalog_renames(catalog_paths, guarded_ids)
    assert not unguarded, (
        "bmad_core_releases catalog skill_renames[].from ids missing from "
        f"RETIRED_SKILL_IDS: {unguarded} -- add each to the guard tuple with "
        "a dated comment."
    )


@pytest.mark.meta
def test_scan_set_resolves_and_has_not_rotted():
    """Every include-glob must clear its own floor; rot fails loudly per surface."""
    resolved = resolve_scan_set(REPO_ROOT)
    empty = [pattern for pattern, files in resolved.items() if not files]
    assert not empty, (
        "scan globs resolved to NO files -- the guard would silently scan "
        f"nothing for: {empty}. Fix the glob or the moved surface."
    )
    shrunken = {
        pattern: (len(files), SCAN_GLOB_FLOORS[pattern])
        for pattern, files in resolved.items()
        if len(files) < SCAN_GLOB_FLOORS[pattern]
    }
    assert not shrunken, (
        "scan surfaces shrank below their rot floors (found, floor): "
        f"{shrunken} -- glob rot or a mass move; re-point SCAN_GLOB_FLOORS "
        "at the live surfaces instead of letting the guard degrade into a "
        "no-op."
    )


@pytest.mark.meta
def test_live_tree_has_no_bare_retired_skill_ids():
    """The swept surfaces stay swept: zero unglossed retired-ID occurrences."""
    violations: list[str] = []
    for files in resolve_scan_set(REPO_ROOT).values():
        for path in files:
            for lineno, retired_id in scan_file(path):
                rel = path.relative_to(REPO_ROOT)
                violations.append(f"{rel}:{lineno}: {retired_id}")
    assert not violations, (
        "bare retired BMAD v6 skill IDs found on live surfaces (they become "
        "broken instructions at the v7 shim removal):\n  "
        + "\n  ".join(sorted(set(violations)))
        + "\n\nIf the text is a live instruction, rename it to the 6.11 skill "
        "name. If it is historical/narrative, keep the recorded name and add "
        "a gloss on the SAME line (any of: 6.11 / retired / forwarder / shim "
        "/ deprecated). Gloss exemplar: `bmad-dev-auto` (the retired 6.x "
        "name of `bmad-build-auto`)."
    )


@pytest.mark.meta
def test_catalog_renames_are_guarded():
    """Every bmad_core_releases/*.yaml skill_renames[].from id is guarded.

    One-directional subset check (catalog subset-of RETIRED_SKILL_IDS), not
    full derivation -- see the module's Design Notes counterpart in the
    story spec: 8 pre-existing guarded ids (the bmad-review-*/
    bmad-editorial-review-* trio, bmad-create-story, bmad-dev-story) never
    appear in either catalog file, so replacing the tuple with the catalog's
    contents would silently drop their coverage.
    """
    catalog_paths = _catalog_files(REPO_ROOT)
    assert catalog_paths, (
        "no bmad_core_releases/*.yaml catalogs found -- glob rot, or the "
        "catalog directory moved"
    )
    _assert_catalog_renames_guarded(catalog_paths)


@pytest.mark.meta
def test_catalog_renames_are_guarded_reds_on_planted_gap(tmp_path):
    """A planted catalog rename absent from RETIRED_SKILL_IDS fails, by name."""
    fixture = tmp_path / "9.9.9.yaml"
    fixture.write_text(
        'version: "9.9.9"\n'
        "skill_renames:\n"
        "  - from: bmad-not-a-real-guarded-id\n"
        "    to: bmad-something-else\n",
        encoding="utf-8",
    )
    with pytest.raises(AssertionError, match="bmad-not-a-real-guarded-id"):
        _assert_catalog_renames_guarded([fixture])


@pytest.mark.meta
def test_planted_bare_id_is_detected(tmp_path):
    """Red-on-plant proof, in a fixture -- the repo tree is never dirtied.

    Includes the 21st (6.12) guarded id alongside two pre-existing (6.11)
    ones -- the scanner is fully generic over RETIRED_SKILL_IDS, so one
    fixture proves detection for old and new ids alike.
    """
    planted = tmp_path / "planted.md"
    planted.write_text(
        "Some ordinary line.\n"
        "bmad-dev-auto\n"
        "Marshal drives stories via `bmad-quick-dev` when hand-picked.\n"
        "bmad-checkpoint-preview\n",
        encoding="utf-8",
    )
    violations = scan_file(planted)
    assert violations == [
        (2, "bmad-dev-auto"),
        (3, "bmad-quick-dev"),
        (4, "bmad-checkpoint-preview"),
    ], (
        "scanner failed to report the planted bare retired IDs as "
        f"file:line violations; got {violations!r}"
    )
    # The reporting shape the live-tree test emits names file AND line.
    rendered = [f"{planted.name}:{lineno}: {rid}" for lineno, rid in violations]
    assert "planted.md:2: bmad-dev-auto" in rendered
    assert "planted.md:4: bmad-checkpoint-preview" in rendered


@pytest.mark.meta
def test_glossed_mentions_are_allowed(tmp_path):
    """Each allow marker, on the same line as a retired ID, suppresses it."""
    glossed = tmp_path / "glossed.md"
    glossed.write_text(
        "`bmad-dev-auto` (the retired 6.x name of `bmad-build-auto`)\n"
        "`bmad-quick-dev` was renamed in 6.11 to `bmad-build`.\n"
        "`bmad-create-prd` survives only as a deprecated thin wrapper.\n"
        "`bmad-document-project` is a forwarder to bmad-project-context.\n"
        "the `bmad-edit-prd` shim rides until the v7 cut\n"
        "`bmad-validate-prd` and the other shims ride until v7\n",
        encoding="utf-8",
    )
    assert scan_file(glossed) == [], (
        "glossed historical mentions must be allowed by the one line-based "
        "allow rule (6.11|retired|forwarder|shim|deprecated)"
    )


@pytest.mark.meta
def test_adjacent_line_marker_does_not_allow(tmp_path):
    """Same-line-ness is the rule: a marker one line away suppresses nothing."""
    adjacent = tmp_path / "adjacent.md"
    adjacent.write_text(
        "renamed in 6.11:\n"
        "bmad-dev-auto\n",
        encoding="utf-8",
    )
    assert scan_file(adjacent) == [(2, "bmad-dev-auto")], (
        "a bare retired ID must be reported even when the previous line "
        "carries an allow marker -- the rule is line-based on purpose"
    )


@pytest.mark.meta
def test_anchored_allow_markers_reject_lookalikes(tmp_path):
    """`v8.6.11`, `16.11`, `6.111`, and `shimmer` are NOT allow markers."""
    lookalike = tmp_path / "lookalike.md"
    lookalike.write_text(
        "bmad-dev-auto arrived in v8.6.11 of something\n"
        "bmad-quick-dev at 16.11 o'clock\n"
        "bmad-edit-prd build 6.111 nightly\n"
        "bmad-create-prd has a shimmer to it\n"
        "bmad-dev-auto really was retired in 6.11\n",
        encoding="utf-8",
    )
    assert scan_file(lookalike) == [
        (1, "bmad-dev-auto"),
        (2, "bmad-quick-dev"),
        (3, "bmad-edit-prd"),
        (4, "bmad-create-prd"),
    ], "lookalike markers must not suppress bare retired IDs; real 6.11 must"


@pytest.mark.meta
def test_id_boundaries_and_case():
    """Boundary + case behavior of RETIRED_ID_RE, pinned."""
    # Variants match as themselves; the bare ID fires exactly once.
    hits = [m.group(1) for m in RETIRED_ID_RE.finditer("bmad-editorial-review-prose")]
    assert hits == ["bmad-editorial-review-prose"]
    hits = [
        m.group(1) for m in RETIRED_ID_RE.finditer("bmad-editorial-review-structure")
    ]
    assert hits == ["bmad-editorial-review-structure"]
    hits = [m.group(1) for m in RETIRED_ID_RE.finditer("run bmad-editorial-review now")]
    assert hits == ["bmad-editorial-review"]
    # Case-insensitive: an uppercase form is still detected.
    hits = [m.group(1) for m in RETIRED_ID_RE.finditer("Run BMAD-Dev-Auto today")]
    assert hits == ["BMAD-Dev-Auto"]
    # Left boundary: a hyphen-prefixed compound is NOT the retired ID.
    assert not RETIRED_ID_RE.search("x-bmad-quick-dev")
    # Right boundary admits a trailing hyphen: compounds fire the base ID.
    hits = [m.group(1) for m in RETIRED_ID_RE.finditer("a bmad-dev-auto-driven flow")]
    assert hits == ["bmad-dev-auto"]
    # ...but a plain alphanumeric continuation is not a match.
    assert not RETIRED_ID_RE.search("bmad-dev-autopilot")
