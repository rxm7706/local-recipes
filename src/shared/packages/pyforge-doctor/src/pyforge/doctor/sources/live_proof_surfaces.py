"""The live-proof-only-surface gather filter (Story 26.1, CAP-77's own
follow-up — ``spec-pyforge-doctor`` CAP-77's catalog finally gets a reader).

**Why this detector exists.** CAP-77's own catalog
(``../../../../../_bmad-output/projects/pyforge-doctor/planning-artifacts/
specs/spec-pyforge-doctor/live-proof-surfaces.md``, resolved at runtime via
``_CATALOG_RELATIVE`` below) names six fleet-wide surfaces where a dev/review
pass's own self-report is structurally not evidence — the only thing that
proves them is a real round-trip against something outside the repo (a
third-party API, a live browser, a service with its own auth and drift).
Motivating incident (2026-09-17/18): herald's ``mcp`` SDK transport broke
across two 2.x breaking renames (``streamablehttp_client`` ->
``streamable_http_client``, a different call signature;
``CallToolResult.isError`` -> ``.is_error``) — caught by neither review nor
the test suite nor a dev pass's own self-report, only a real live
push-then-read-back against Claude Design. Nothing read that catalog or
surfaced it to a reviewer until this module.

**Amendment (2026-09-20) — matching input is the catalog's OWN glob column,
never keyword-derived.** The first attempt at this story (run
``pyforge-doctor-20260919T233255320Z-8f2b958e``) fell back to a bare
case-insensitive substring match on generic English words pulled from the
catalog's ``Surface``/prose cells for the three rows with no natural
per-row path field (scribe's Postgres cluster, herald's ``deck sync-all``
idempotency, the cross-station ``guild-container`` row). Independently
reproduced by four review layers against the REAL tracked catalog and REAL
tracked repo paths: scribe's ``cluster`` token matched
``docs/how-to/ocp-cluster-bringup.md``; herald's ``deck`` token matched
``docs/how-to/presentation-deck.md``; the container row's ``docker`` token
matched ``recipes/docker/recipe.yaml`` — none of them a live-proof surface,
and tightening the heuristic (word-boundary matching) would not have fixed
it, since the offending words were already whole path segments. Routed
``intent_gap``: no bounded code fix closes this without reopening the
opposite failure mode (a sparse ``Surface`` column silently producing a
permanently-unmatchable row). The resolution (Unresolved Question 1, option
b): ``live-proof-surfaces.md`` itself grew a hand-authored ``Surface globs``
column (all eight rows, added 2026-09-20) — real ``pathlib``-style glob
patterns relative to the repo root. THIS module matches a changed path
against that column and nothing else — never a keyword pulled from the
prose, never a second glob list hardcoded here (the catalog stays the one
source of truth; adding or moving a surface means editing the catalog).

**Real glob semantics, not a keyword/substring/prefix guess.**
``_glob_to_re`` mirrors ``sources/chain.py``'s own ``_glob_to_re`` (the
spec-surface glob-matching precedent already used for an identical
"hand-authored repo-relative glob column" shape): ``**`` spans path
separators, ``*``/``?`` do not, and a pattern with no glob characters
matches exactly. A row's ``Surface globs`` cell with no backtick-quoted
token at all yields an empty tuple, and an empty tuple never matches
anything — a row is catalogued but not diff-matched until a real glob is
authored for it (Boundaries: "a row with an empty cell is never
diff-matched").

**Always WARN, never FAIL (AD-2, CAP-77's own constraint).** A touched
live-proof surface is an advisory nudge ("go prove this live before you
trust the self-report"), never a second PR gate — mirrors
``general_docs_consistency.py``/``docs_shelf.py``'s own warn-only
discipline, not ``frozen_path.py``'s FAIL-capable one.

**Verbatim quoting, no special-casing for the "no mechanism yet" row.** The
Boundaries clause says a finding's proof-step text is quoted verbatim from
the catalog, never re-derived or paraphrased — and atlas's Chromium/DuckDB/
WASM row's own "How to prove it live" cell already reads "No single
documented live-proof command as of this writing — named gap, not a
fabricated mechanism." Quoting that cell verbatim, the SAME way every other
row's cell is quoted, produces the honest "no mechanism documented" finding
with zero branching on which row it is — the catalog's own prose does the
work.

**Independence.** Reads only the tracked catalog file and ``git diff
--name-only`` (via ``cli_bridge.run_git``, AD-5's sole subprocess site) —
never imports ``pyforge.herald``/``pyforge.scribe``/``pyforge.atlas``/
``pyforge.warden`` or any other station package, and never imports
``bmad_loop``.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from ..cli_bridge import CliBridgeError, run_git
from ..models import DoctorStatus, Finding, Source
from . import degrade_on_exception

__all__ = ("CatalogRow", "gather", "parse_catalog")

#: CAP-77's own catalog -- the single source of truth (Boundaries: "adding a
#: new live-proof surface means editing live-proof-surfaces.md, not
#: hardcoding a second list in the source module").
_CATALOG_RELATIVE = Path(
    "_bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/live-proof-surfaces.md"
)

_CHECK = "live-proof-surface"

#: Station | Surface | Why a static/self-report pass misses it |
#: How to prove it live | Cost | Surface globs -- the catalog's own header.
_EXPECTED_COLUMNS = 6

_GLOB_TOKEN_RE = re.compile(r"`([^`]+)`")
_SEPARATOR_CELL_RE = re.compile(r":?-+:?")


@dataclass(frozen=True)
class CatalogRow:
    """One parsed row of ``live-proof-surfaces.md``'s table."""

    station: str
    surface: str
    how_to_prove: str
    cost: str
    surface_globs: tuple[str, ...]


def _is_separator_row(cells: list[str]) -> bool:
    """A markdown table's own ``|---|---|...|`` divider row -- every cell is
    made of nothing but dashes (optionally colon-bounded for alignment)."""
    return bool(cells) and all(_SEPARATOR_CELL_RE.fullmatch(cell) for cell in cells)


def parse_catalog(text: str) -> tuple[CatalogRow, ...]:
    """Parse ``live-proof-surfaces.md``'s own markdown table into
    ``CatalogRow``\\ s.

    RAISES ``ValueError`` on a structurally broken table (no header found,
    or a data row with other than ``_EXPECTED_COLUMNS`` cells) -- left
    uncaught here, deliberately: ``gather()``'s outer ``degrade_on_exception``
    net folds it into one generic WARN naming the parse failure (the I/O &
    Edge-Case Matrix's own "malformed/unparseable catalog" row), rather than
    this function inventing a partial recovery.

    A row's ``Surface globs`` cell is read as every backtick-quoted token in
    it, in order -- an empty cell (no backtick token at all) yields an empty
    tuple, never diff-matched (Boundaries).
    """
    rows: list[CatalogRow] = []
    header_seen = False
    for line in text.splitlines():
        stripped = line.strip()
        if not (stripped.startswith("|") and stripped.endswith("|")):
            if not stripped:
                continue  # a blank line inside/around the table never ends it
            if header_seen:
                break  # a genuine non-blank, non-table line ends the scan
            continue
        cells = [cell.strip() for cell in stripped[1:-1].split("|")]
        if not header_seen:
            if cells and cells[0].lower() == "station":
                header_seen = True
            continue
        if _is_separator_row(cells):
            continue
        if len(cells) != _EXPECTED_COLUMNS:
            raise ValueError(
                f"live-proof-surfaces.md: expected {_EXPECTED_COLUMNS} columns, got {len(cells)}: {stripped!r}"
            )
        rows.append(
            CatalogRow(
                station=cells[0],
                surface=cells[1],
                how_to_prove=cells[3],
                cost=cells[4],
                surface_globs=tuple(_GLOB_TOKEN_RE.findall(cells[5])),
            )
        )
    if not header_seen:
        raise ValueError("live-proof-surfaces.md: no table header found")
    return tuple(rows)


def _glob_to_re(pattern: str) -> re.Pattern:
    """Mirrors ``sources/chain.py``'s own ``_glob_to_re`` exactly (the
    spec-surface glob-matching precedent for an identical hand-authored,
    repo-relative glob column): ``**`` spans path separators, ``*``/``?`` do
    not; a pattern with no glob characters matches exactly."""
    out: list[str] = []
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if pattern[i : i + 2] == "**":
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


def _row_match(row: CatalogRow, changed_paths: Sequence[str]) -> tuple[str, ...]:
    """Every path in ``changed_paths`` (in its own given order) that matches
    ANY of ``row.surface_globs`` under real glob semantics (``_glob_to_re``)
    -- never a keyword, substring, or fuzzy match of any kind (Boundaries).
    A row with no ``surface_globs`` (an empty catalog cell) always returns
    ``()``: it is catalogued but never diff-matched."""
    if not row.surface_globs:
        return ()
    patterns = [_glob_to_re(glob) for glob in row.surface_globs]
    return tuple(path for path in changed_paths if any(pattern.match(path) for pattern in patterns))


def _git(target: Path, *args: str) -> str | None:
    """``git`` stdout, or ``None`` on any failure -- mirrors
    ``sources/frozen_path.py``'s/``sources/ledger.py``'s own ``_git``
    wrapper. Routes through ``cli_bridge.run_git`` (AD-5: the sole
    subprocess site)."""
    try:
        return run_git(target, list(args))
    except CliBridgeError, UnicodeDecodeError:
        return None


def _changed_paths(target: Path, *, base: str = "origin/main", head: str = "HEAD") -> list[str] | None:
    """The sorted, de-duplicated list of paths changed between ``base`` and
    ``head``, or ``None`` on any git failure (unresolvable ref, non-repo
    target, ...). Sorted for a deterministic match order -- unlike
    ``sources/frozen_path.py``'s own ``_changed_paths`` (a ``set[str]``,
    order-independent by construction there), this module reports the FIRST
    matching changed path per row in its evidence, so a stable order matters
    here.

    ``-c core.quotepath=false`` disables git's default quoting/escaping of
    non-ASCII filenames in ``--name-only`` output, same rationale as
    ``frozen_path.py``'s identical flag."""
    output = _git(target, "-c", "core.quotepath=false", "diff", "--name-only", f"{base}..{head}")
    if output is None:
        return None
    return sorted({line.strip() for line in output.splitlines() if line.strip()})


def _gather(target: Path) -> tuple[Finding, ...]:
    catalog_path = target / _CATALOG_RELATIVE
    # May raise (OSError / ValueError) -- deliberately left uncaught here;
    # the outer degrade_on_exception net (wired by gather(), below) folds it
    # into one generic WARN Finding naming the failure.
    text = catalog_path.read_text(encoding="utf-8")
    rows = parse_catalog(text)

    changed = _changed_paths(target)
    if changed is None:
        return (
            Finding(
                source=Source.LIVE_PROOF_SURFACE,
                check=_CHECK,
                status=DoctorStatus.WARN,
                message="could not diff origin/main..HEAD",
                evidence={"catalog": _CATALOG_RELATIVE.as_posix()},
            ),
        )

    findings: list[Finding] = []
    for row in rows:
        matched = _row_match(row, changed)
        if not matched:
            continue
        findings.append(
            Finding(
                source=Source.LIVE_PROOF_SURFACE,
                check=_CHECK,
                status=DoctorStatus.WARN,
                message=(
                    f"{row.station}/{row.surface}: {matched[0]} touches a "
                    f"live-proof-only surface (CAP-77) -- {row.how_to_prove}"
                ),
                evidence={
                    "catalog": _CATALOG_RELATIVE.as_posix(),
                    "station": row.station,
                    "surface": row.surface,
                    "changed_paths": list(matched),
                    "how_to_prove": row.how_to_prove,
                    "cost": row.cost,
                },
            )
        )
    return tuple(findings)


def gather(target: Path) -> tuple[Finding, ...]:
    """Live-proof-only surface gather -- CAP-77 / Story 26.1.

    Reads ``live-proof-surfaces.md``'s ``Surface globs`` column (the ONLY
    matching input) and reports one advisory WARN per catalogued surface a
    changed path (``origin/main..HEAD``) matches, quoting that row's own
    "how to prove it live" cell verbatim. A row with an empty globs cell
    never fires. Zero matches -> zero findings, no synthetic OK summary
    (the I/O & Edge-Case Matrix's own "no changed path matches any
    catalogued surface" row). An unreadable/malformed catalog or an
    unresolvable git ref degrades to one generic WARN -- never a crash,
    never FAIL (AD-2: always ``warn``, never a second PR gate).
    """
    return degrade_on_exception(Source.LIVE_PROOF_SURFACE, _CHECK, lambda: _gather(target))
