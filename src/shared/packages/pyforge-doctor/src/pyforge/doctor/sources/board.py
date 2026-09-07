"""The board-truthfulness gather filters -- Doctor's verdict on the fleet-
status console + its data feeds (Story 6.5, FR-15).

**Why this module exists, and why it is HERE rather than in ``pyforge.marshal``.**

Charter §6, ratified 2026-07-28: *"the Doctor holds the verdict on the Marshal's
conformance — the one station that would otherwise grade itself."* The Guildhall
board (``docs/dashboard/``) is Marshal's own console, and three read-only judges of
it grew up OUTSIDE Doctor as repo-root scripts: ``scripts/chain_completeness_check.py``
(does every station's plan match its record?), ``scripts/dashboard_drift_check.py``
(does the committed board still match the feeds that fed it?) and
``docs/dashboard/check_layout.py`` (does the board's console bar actually render
without overlapping or clipping?). Story 6.4 proved the ledger port pattern; this
module is the board's turn, porting all three verbatim in behavior.

**The independence rule, which is the entire point of this module:**

    This module reads the DURABLE ARTIFACTS -- tracked planning docs, the
    committed ``data.js``, and (for ``dashboard_drift``) the gitignored Tier-3
    feeds and their tracked twins -- and never imports ``pyforge.marshal`` (or
    any other station package).

Mirrors ``sources/ledger.py``'s and ``sources/marshal.py``'s own independence
rationale exactly: a board-truthfulness verdict assembled from Marshal's own code
would be Marshal's self-report wearing Doctor's badge.
``tests/unit/test_sources_board_independence.py`` pins it.

**Degrades, never crashes** -- the house rule for every Doctor source. Each of
the three gathers below documents its own specific "cannot evaluate" paths; see
each function's own docstring.

**Two independent ``data.js`` readers, deliberately not unified.** ``_board_lines``
(used by ``gather_chain_completeness``) and ``_load_data_js`` (used by
``gather_dashboard_drift``) parse the SAME committed file with two DIFFERENT
methods, because that is what their two respective source scripts already do --
a fixed-prefix strip in one, a regex search in the other. Consolidating them would
be a redesign this story's Boundaries explicitly rule out ("preserve, don't
redesign"); each stays exactly as strict or as lenient as its own original.
"""

from __future__ import annotations

import bisect
import functools
import http.server
import importlib.util
import json
import re
import socketserver
import sys
import threading
from pathlib import Path

from ..models import DoctorStatus, Finding, Source
from . import degrade_on_exception

__all__ = (
    "gather_chain_completeness",
    "gather_chain_layers_audit",
    "gather_check_layout",
    "gather_dashboard_drift",
)


# === gather_chain_completeness ==============================================
#
# Ported from scripts/chain_completeness_check.py -- see that script's own
# module docstring for the full three-invariant rationale (Marshal's
# 2/24-decomposed PRD, Doctor's orphan ledger key, Herald's 12/19-vs-47/47
# board) and the fourth (INV-D, a canonical epics doc that parses to zero
# stories, which would let INV-B trivially "pass" over an empty set).
# ``_story_keys_from_ledger`` from the original script is NOT ported: it is
# dead code there (defined, never called by ``check()`` or ``main()``) --
# porting an unused helper would be speculative, not a verbatim behavior port.

#: Spec statuses that represent work still owed -- identical to the original.
OPEN_SPEC_STATUSES = frozenset({"draft", "ready", "in-progress"})

#: Specs deliberately NOT decomposed, each with the reason it is exempt --
#: copied verbatim from scripts/chain_completeness_check.py so a station's
#: recorded exemption is not silently dropped by the port.
# NOTE (updated 2026-08-10): the former duplicate in `scripts/chain_completeness_check.py`
# is GONE — 6-9 landed (PR #394) and deleted the shim, so this dict is now the sole copy.
# An entry leaves this dict only when its Spec is decomposed into the owning station's
# epics AND the operator confirms dispatch (precedent: spec-deferred-work-visibility,
# de-registered 2026-08-10 on explicit operator confirmation of doctor Epic 7).
DEFERRED_SPECS: dict[str, str] = {
    "spec-agentic-sdlc-autonomy":
        "a standing position, explicitly 'not a deliverable' by its own text — "
        "there is nothing to decompose and an FR would manufacture one",
    "spec-artifact-chain-reconciliation":
        "executed serially in the operator's main session by its own SPEC constraint (the "
        "quick-dev shape) — decomposing it into marshal's PRD/epics would place audit "
        "stories on the very board that feeds bmad-loop dispatch, and the audit exists to "
        "PAUSE that loop until the chain is measured true. Its deliverables are the gate "
        "reports (traceability matrices) landing in each station's planning-artifacts, "
        "tracked and detector-checked there. Revisit if the audit becomes a standing "
        "practice (its own open question) — a recurring cadence would deserve board "
        "representation",
    "spec-chain-currency-sweep":
        "same structural class as spec-artifact-chain-reconciliation above: CAP-1 is "
        "explicitly titled '(SHIPPED)', and the actual procedure of record is its own "
        "companion CHAIN-CURRENCY-RUNBOOK.md, executed directly by an operator rather than "
        "dispatched as station epics/stories. Decomposing it into doctor's PRD/epics would "
        "manufacture stories for a runbook, not describe undone work. Revisit if the sweep "
        "becomes a station-dispatched recurring duty rather than an operator-run runbook",
    "spec-build-league-scorecard":
        "explicitly self-parked by its own SPEC.md: 'Parked contract... Do not implement a "
        "board until the operator drafts the measure set.' Unifying Strategy Q5 named the "
        "faces and defined no numbers; this Spec exists only so the chain has a link, not to "
        "describe undone work an epic could pick up today. De-register once the operator "
        "publishes the human/agent/team measure set CAP-1 needs",
    "spec-golden-path-conda-blind-spot":
        "a `draft` Spec seeded 2026-09-05 (PR #1063) so the Dream's chain link is durable; "
        "its five CAPs sit behind five open questions (selector grammar, provisioning route, "
        "budget, evidence shape, adoption trigger) that only the operator can answer, so "
        "decomposing it into warden epics now would manufacture stories from guesses. "
        "De-register once the open_questions are cleared and warden's epics carry CAP-1..5",
    "spec-intelligence-hub":
        "a `draft` Spec seeded 2026-09-05 so the Dream's chain link is durable (dream-chain "
        "INV-1); its five CAPs are the Dream's CANDIDATE shapes — none chosen. The 2026-09-06 "
        "research pass closed RB-1 (Frame Spec v0.2.0 is published) and RB-2 (nebari + nebi are on "
        "conda-forge; only nebari-infrastructure-core is absent); what remains — owner, Guard "
        "categories, Track shape, own Frames, and the two derived questions (package NIC / the "
        "frames client? author the first conformant Frame now?) — only the operator can answer, "
        "so decomposing it into steward epics now would manufacture stories from guesses. "
        "De-register once the operator picks the shape(s) and steward's epics carry the chosen CAPs",
    "spec-bmad-cursor-interactive-routing":
        "a `draft` Spec seeded 2026-09-07 so the Dream's chain link is durable (dream-chain "
        "INV-1); CAP-1 (a live probe of whether Cursor's interactive IDE chat can invoke a "
        "context-free subagent) gates every other CAP and has not run yet, so decomposing this "
        "into marshal epics now would manufacture stories ahead of an unanswered empirical "
        "question. De-register once CAP-1's probe result is recorded and the operator's CAP-2/ "
        "CAP-3 shape choice is settled",
}

_CHAIN_DATA_JS_PREFIX = "window.DASHBOARD_DATA = "

#: A ledger story key's leading id, in either shape -- verbatim from the original.
_LEDGER_ID = re.compile(r"^(\d+-\d+|[a-z]+\d+)-")

#: A top-level (column-0) ``## `` heading -- used two ways: (1) at PROSE-BUILD
#: TIME, to find each source file's own first heading so everything before it
#: (its preamble) can be stripped before concatenation (Round 4's fix); (2)
#: inside ``_cited_cap_ids_by_spec``, to find every heading position in the
#: already-stripped ``prose`` for the "cap a citation window at the second
#: heading past its anchor" rule. Three ``#``s (``### Story ...``) does NOT
#: match -- the third character must be a space, not another ``#``.
_HEADING_RE = re.compile(r"^## ", re.MULTILINE)

#: The ``## Capabilities`` section heading a SPEC.md declares its own CAP ids
#: under -- exact-string, case-sensitive, no trailing text. A SPEC.md using a
#: different heading convention (e.g. ``## Scope (capabilities)``) falls back
#: to zero declared ids, a real, KNOWN, deliberately-deferred gap (this
#: story's own Review Triage Log, review pass 1).
_CAP_SECTION_HEADING_RE = re.compile(r"^## Capabilities\s*$", re.MULTILINE)

#: One declared capability bullet: ``- **CAP-<N> — <title>.**``. Anchored at
#: column 0 so an indented sub-bullet (``  - **intent:** ...``) never matches.
_CAP_DECL_LINE_RE = re.compile(r"^-\s*\*\*CAP-(\d+)\b")

#: One CITED CAP-id token in project prose, in any of the four live shapes:
#: bare ``CAP-5``, inclusive range ``CAP-4..10``, prefixed range
#: ``CAP-4..CAP-10``, or slash-grouped ``CAP-1/2/3``. The leading AND
#: trailing ``\b`` (the trailing one added by review pass 1's hardening) keep
#: ``CAP-10x`` from being mistaken for a citation of CAP-10.
_CAP_CITATION_RE = re.compile(r"\bCAP-(\d+)(?:\.\.(?:CAP-)?(\d+)|((?:/\d+)+))?\b")

#: A range wider than this is treated as malformed (contributes no ids) --
#: no legitimate citation in this fleet has ever come close.
_CAP_MAX_RANGE_SPAN = 500


def _parse_declared_cap_ids(spec_md_text: str) -> set[int]:
    """The Spec's own declared ``CAP-N`` ids, scanned from its ``##
    Capabilities`` section. Returns an empty set when the heading is absent,
    present but empty, or present but carries no line matching the declared-
    bullet shape -- all three degrade identically to "this Spec declares no
    CAP ids", which is INV-A's own signal to fall back to the original
    bare-substring check (a Spec with nothing to check coverage against).
    Never raises: an unparseable line under the heading is silently skipped.
    """
    m = _CAP_SECTION_HEADING_RE.search(spec_md_text)
    if not m:
        return set()
    nxt = _HEADING_RE.search(spec_md_text, m.end())
    body = spec_md_text[m.end():nxt.start() if nxt else len(spec_md_text)]
    ids: set[int] = set()
    for line in body.splitlines():
        dm = _CAP_DECL_LINE_RE.match(line)
        if dm:
            ids.add(int(dm.group(1)))
    return ids


def _format_cap_ids(ids: set[int] | list[int]) -> str:
    """Collapse a set/sequence of CAP ids into compact range notation, e.g.
    ``{4, 6, 7, 8, 9, 10}`` -> ``"CAP-4, CAP-6..10"``. The sole real call site
    always passes a sorted, duplicate-free sequence (``sorted(declared -
    cited)``), so no internal sort/dedupe guard is added (this story's own
    Review Triage Log, pass 1: rejected as hardening against a caller that
    does not exist)."""
    ordered = sorted(ids)
    if not ordered:
        return ""
    chunks: list[str] = []
    start = prev = ordered[0]
    for n in ordered[1:]:
        if n == prev + 1:
            prev = n
            continue
        chunks.append(f"CAP-{start}" if start == prev else f"CAP-{start}..{prev}")
        start = prev = n
    chunks.append(f"CAP-{start}" if start == prev else f"CAP-{start}..{prev}")
    return ", ".join(chunks)


def _expand_cap_token(m: re.Match) -> set[int]:
    """The ids one ``_CAP_CITATION_RE`` match cites: bare ``CAP-N``, inclusive
    range ``CAP-N..M``/``CAP-N..CAP-M``, or slash-grouped ``CAP-N/M/O``. A
    REVERSED range (``CAP-10..4``) or one wider than ``_CAP_MAX_RANGE_SPAN``
    contributes NO ids at all -- not even its own start id -- rather than
    silently inverting it or raising."""
    start = int(m.group(1))
    range_end, slash_group = m.group(2), m.group(3)
    if range_end is not None:
        end = int(range_end)
        if end < start or end - start > _CAP_MAX_RANGE_SPAN:
            return set()
        return set(range(start, end + 1))
    if slash_group:
        return {start, *(int(tok) for tok in slash_group.split("/") if tok)}
    return {start}


def _spec_slug_anchor_pattern(slugs: list[str]) -> re.Pattern | None:
    """One alternation regex matching ANY of a project's own Spec slugs,
    longest-first so a shorter slug that is a literal prefix of a longer one
    (e.g. ``spec-foo`` inside ``spec-foo-bar``) can never steal the match
    position out from under the longer, more specific slug it is a prefix
    of. ``None`` when the project has no Specs to anchor on at all."""
    if not slugs:
        return None
    ordered = sorted(set(slugs), key=len, reverse=True)
    return re.compile("|".join(re.escape(s) for s in ordered))


def _cited_cap_ids_by_spec(prose: str, slugs: list[str]) -> dict[str, set[int]]:
    """Every CAP-id citation in ``prose``, scoped to the Spec it actually
    belongs to -- never pooled flat across the whole project (Round 2's
    rejection: two Specs in the same project nearly always both number their
    own capabilities starting at CAP-1, so a flat pooled set silently
    "covers" one Spec's genuinely-undecomposed ids with a citation that
    belongs to a completely different Spec).

    THE WINDOW, per Spec occurrence (any-slug-occurrence anchoring, Round 2's
    design, unchanged since): each literal occurrence of a Spec's own slug
    text in ``prose`` opens one citation window. The window runs from that
    occurrence up to the NEARER of (a) the next occurrence of ANY Spec's own
    slug (this Spec's or a different one's -- the next anchor always ends the
    current window, so one Spec's citations can never bleed into the next
    Spec's section) or (b) the SECOND ``## `` heading position following the
    anchor (allowing a Spec's own citations to legitimately continue across
    exactly ONE un-anchored heading -- the real ``spec-deferred-work-
    visibility`` Epic 8 -> Epic 9 shape, where Epic 9's own blockquote cites
    further CAP ids without repeating the Spec's slug -- while still capping
    a runaway window two-plus headings later, the real Epic-14-to-Epic-16
    marshal shape that motivated the cap). The heading-cap lookup uses
    ``bisect`` over a sorted heading-position list rather than filtering the
    full list per anchor (an O(anchors x headings) scan Round 3 regressed to;
    fixed here while this code is already being rewritten).

    ROUND 4: this function used to ALSO exclude an anchor sitting before
    ``prose``'s own first heading (Round 3's narrow fix for a header-less-
    preamble anchor sweeping in an unrelated CAP id). That check is DELETED
    here, not extended -- Round 4 replaced it with per-FILE preamble
    stripping at prose-build time, in the caller
    (``_check_project_chain_completeness``), so no preamble text ever reaches
    this function's ``prose`` argument in the first place. This function goes
    back to reasoning about one already-clean string, exactly like Round 2's
    original design.
    """
    pattern = _spec_slug_anchor_pattern(slugs)
    if pattern is None:
        return {}
    anchors = [(m.start(), m.group(0)) for m in pattern.finditer(prose)]
    if not anchors:
        return {}
    headings = [m.start() for m in _HEADING_RE.finditer(prose)]
    end = len(prose)
    out: dict[str, set[int]] = {}
    for i, (pos, slug) in enumerate(anchors):
        next_anchor = anchors[i + 1][0] if i + 1 < len(anchors) else end
        h_idx = bisect.bisect_right(headings, pos)
        second_heading = headings[h_idx + 1] if h_idx + 1 < len(headings) else end
        window_end = min(next_anchor, second_heading)
        cited = out.setdefault(slug, set())
        for cm in _CAP_CITATION_RE.finditer(prose, pos, window_end):
            cited.update(_expand_cap_token(cm))
    return out


def _frontmatter(path: Path) -> dict[str, str]:
    """The frontmatter block's top-level ``key: value`` pairs, as raw strings.

    A tiny hand-rolled reader, NOT PyYAML -- this story's Surface excludes
    ``pixi.toml`` (mirrors ``sources/ledger.py``'s/``sources/marshal.py``'s own
    ``_parse_statuses``, adapted from an indented ``development_status:`` block
    to a top-level ``---``-fenced one). ``check()`` only ever reads two flat
    scalar keys off the result (``status``, ``epics_role``), so a nested
    list/mapping value (``surface:``, ``sources:``, ``open_questions:``) is a
    multi-line block this parser does not need to understand -- a value-less
    ``key:`` opening a list or a nested mapping, and every indented/``-``-
    prefixed continuation line under it, are simply skipped rather than parsed.

    The ONE value-less shape that is NOT skipped is a plain scalar written on
    the following line (``status:\\n  draft``): ``yaml.safe_load`` -- the parser
    this replaced -- decodes that to ``"draft"``, while storing the key as
    ``""`` (what this reader did before) fails the ``OPEN_SPEC_STATUSES``
    membership test and silently EXEMPTS an open, undecomposed Spec. That is
    the same false-negative class ``_scalar`` exists to close, reached through
    a different bit of YAML syntax; see ``_continuation_scalar``.

    Never raises: a missing file, an unreadable one, or a file with no
    frontmatter fence all degrade to ``{}``, mirroring the original script's
    own broad try/except. A thin file-reading wrapper around
    ``_frontmatter_from_text`` -- split out so a caller that has ALREADY read
    a SPEC.md's text for another purpose (INV-A's own CAP-id parsing) can
    reuse that one read instead of this function reading the same file a
    second time (Round 3 hardening, kept).
    """
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001 -- mirrors the original's own
        # `except Exception: return {}` (scripts/chain_completeness_check.py's
        # frontmatter()), so a non-UTF-8 SPEC.md degrades the same way here.
        return {}
    return _frontmatter_from_text(text)


def _frontmatter_from_text(text: str) -> dict[str, str]:
    """``_frontmatter``'s actual parsing logic, taking already-read text --
    see ``_frontmatter`` for the full behavioral contract and rationale."""
    if not text.startswith("---"):
        return {}
    out: dict[str, str] = {}
    in_block = False
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        if line.strip() == "---":
            if in_block:
                break
            in_block = True
            continue
        if not in_block:
            continue
        if not line or line[0].isspace() or line.startswith("-"):
            continue  # nested list/continuation line -- not a top-level key
        key, sep, value = line.partition(":")
        if not (sep and key.strip()):
            continue
        scalar = _scalar(value)
        if not scalar:
            scalar = _continuation_scalar(lines, idx)
            if scalar is None:
                continue  # a real block opener -- skipped, as documented above
        out[key.strip()] = scalar
    return out


def _continuation_scalar(lines: list[str], idx: int) -> str | None:
    """The scalar a value-less ``key:`` at ``lines[idx]`` carries on its next
    indented line, or ``None`` when that key really opens a block.

    ``None`` for a list (``- item``), a nested mapping (a line containing
    ``:``), or nothing at all -- exactly the shapes ``_frontmatter``'s two
    consumed keys never take, and which it has always skipped.
    """
    for nxt in lines[idx + 1:]:
        if not nxt.strip():
            continue
        if not nxt[0].isspace():
            return None  # the block was empty; this is the next top-level key
        body = nxt.strip()
        if body.startswith("-") or ":" in body:
            return None  # a list or a nested mapping, not a plain scalar
        return _scalar(body)
    return None


def _scalar(raw: str) -> str:
    """A frontmatter scalar's VALUE, with the two bits of YAML syntax that
    would otherwise silently change a status: an inline ``  # comment`` and
    surrounding quotes.

    The parser this replaced was ``yaml.safe_load``, which decoded both. Left
    raw, ``status: 'draft'`` reads as ``"'draft'"``, misses the
    ``OPEN_SPEC_STATUSES`` membership test, and silently EXEMPTS an open,
    undecomposed Spec -- a false negative in the one check whose whole purpose
    is making "we chose not to" distinguishable from "nobody noticed". Same
    hazard for ``epics_role: "canonical"``, where the miss skips INV-B/INV-D
    entirely. Latent today (no consumed file is quoted) but one line to close,
    and this repo demonstrably writes quoted statuses elsewhere.

    A QUOTED value is decoded first and its ``#`` left alone, because that is
    what YAML does: inside quotes ``#`` is data, not a comment. Stripping the
    comment first (as the first cut of this helper did) truncated
    ``"a # b"`` to ``"a`` -- a mis-decode of exactly the kind this helper
    exists to prevent, with a stray quote left on the front.
    """
    value = raw.strip()
    if value[:1] in ('"', "'"):
        quote = value[0]
        end = value.find(quote, 1)
        if end != -1:
            return value[1:end]  # anything past the closing quote is a comment
        return value  # unbalanced quote -- left alone, as YAML would reject it
    head, hash_, _ = value.partition(" #")
    if hash_:
        value = head.strip()
    return value


def _norm_id(token: str) -> str:
    """``2-1-scaffold-the-kedro`` and ``a1-scaffold-the-kedro`` share a tail --
    verbatim from the original."""
    return token.strip().lower().replace(".", "-")


def _story_ids_from_epics(path: Path) -> list[set[str]]:
    """One id-SET per story -- every id a ``### Story`` heading declares for
    it. Verbatim from the original (see its own docstring for the
    now-retired dual-id rationale)."""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001 -- NOT `except OSError`: a non-UTF-8 byte
        # raises UnicodeDecodeError, which is a ValueError, so the narrower
        # catch let it escape into the per-project handler and discard that
        # project's OWN already-computed INV-A findings (reproduced live).
        return []
    out: list[set[str]] = []
    for m in re.finditer(r"^###\s+Story\s+(\d+\.\d+[a-z]?)", text, re.MULTILINE):
        out.append({_norm_id(m.group(1))})
    return out


def _ledger_rows(path: Path) -> dict[str, str]:
    """Every ``key: value`` under ``development_status:``, epic rollups
    included -- verbatim from the original (deliberately shape-agnostic; see
    its own docstring for why this counts rows rather than parsing ids)."""
    out: dict[str, str] = {}
    in_block = False
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001 -- see _story_ids_from_epics: a non-UTF-8
        # ledger raises UnicodeDecodeError (a ValueError), not an OSError.
        return out
    for raw in text.splitlines():
        if raw.startswith("development_status:"):
            in_block = True
            continue
        if not in_block:
            continue
        if raw and not raw.startswith((" ", "\t")):
            break
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition(":")
        if sep:
            out[key.strip()] = value.strip()
    return out


def _ledger_story_ids(rows: dict[str, str]) -> tuple[set[str], set[str]]:
    """``(recognised ids, unrecognised keys)`` -- verbatim from the original."""
    ids, unknown = set(), set()
    for key in rows:
        m = _LEDGER_ID.match(key)
        (ids.add(_norm_id(m.group(1))) if m else unknown.add(key))
    return ids, unknown


def _canonical_epics(project_dir: Path) -> Path | None:
    """The one epics doc declaring ``epics_role: canonical``; falls back to
    ``epics.md`` for a project predating the convention -- verbatim from the
    original, using this module's own ``_frontmatter`` in place of PyYAML."""
    pa = project_dir / "planning-artifacts"
    for candidate in sorted(pa.glob("epics*.md")):
        if _frontmatter(candidate).get("epics_role") == "canonical":
            return candidate
    fallback = pa / "epics.md"
    return fallback if fallback.is_file() else None


def _board_lines(data_js: Path) -> dict[str, tuple[int, int]] | None:
    """``{station: (done, total)}`` from ``data.js``, or ``None`` when it
    cannot be read -- verbatim from the original (a fixed-prefix strip, not
    the regex ``gather_dashboard_drift`` uses; see this module's own
    docstring for why the two stay separate)."""
    try:
        text = data_js.read_text(encoding="utf-8")
        if not text.startswith(_CHAIN_DATA_JS_PREFIX):
            return None
        data = json.loads(text[len(_CHAIN_DATA_JS_PREFIX):].rstrip().rstrip(";"))
    except Exception:  # noqa: BLE001 -- "cannot read the generated board" is
        # the one thing this function promises to degrade on, mirroring the
        # original script's own broad except.
        return None
    projects = data.get("projects") if isinstance(data, dict) else None
    if not isinstance(projects, dict):
        # A structurally-wrong-but-valid-JSON board (`projects` a list, a
        # string, or absent) is "cannot read the generated board" -- the one
        # thing this function promises to degrade on -- NOT an AttributeError
        # raised from outside the caller's per-project try. INV-C treats None
        # and {} identically (`board is not None and station in board`), so
        # this only changes which failure mode a broken file produces.
        return None
    out: dict[str, tuple[int, int]] = {}
    for key, proj in projects.items():
        # PER-STATION isolation, as a try rather than a growing wall of
        # isinstance guards. `board` is computed OUTSIDE `_check_chain_
        # completeness`'s own per-project try, so ANY shape this function
        # fails to anticipate escapes all the way to the whole-gather
        # `degrade_on_exception` and collapses EVERY project's real FAIL into
        # one vacuous WARN (exit 2 -> exit 0). Two review passes each closed
        # one more nested access by hand (`projects` a list; a non-dict epic)
        # and each time a third shape was still open -- `{"stories": 7}`, a
        # TRUTHY non-iterable, was reproduced live doing exactly that. Guard
        # the whole per-station read once: an unreadable station line is
        # simply absent from the result, which is already how INV-C spells
        # "cannot compare this station" (`station in board`).
        try:
            line = _station_board_line(proj)
        except Exception:  # noqa: BLE001, S112 -- see the block comment above;
            # one station's malformed board line must not take down the rest.
            continue
        if line is not None:
            out[key] = line
    return out


def _station_board_line(proj: object) -> tuple[int, int] | None:
    """One station's ``(done, total)``, ``None`` for a station the original
    deliberately SKIPS, or a raised ``ValueError`` for a line this reader
    cannot interpret.

    THE THREE STATES ARE KEPT APART ON PURPOSE, because collapsing any two of
    them produces a wrong INV-C verdict in one direction or the other:

    * ``None`` -- a well-formed ``"epics": []``. The original guards this with
      its own ``if not epics: continue``; recording ``(0, 0)`` instead fired a
      false ``board-diverges-from-ledger`` on input the original handled
      cleanly.
    * ``ValueError`` -- a shape this reader cannot make sense of (a non-mapping
      station or epic, a non-list ``stories``, a non-list story slot). The
      previous cut FILTERED those entries out of the comprehension instead,
      which quietly produced ``(0, 0)`` and fired the same false FAIL, this
      time with a fabricated count: ``{"epics": [None]}`` against a 2-row
      ledger reported *"board 0/0 vs ledger 1/2"*. Raising routes it to the
      caller's per-station skip, which is already how INV-C spells "cannot
      compare this station".
    * ``(done, total)`` -- a line that was actually read.

    A FALSY ``stories`` (``None``, ``[]``, ``0``) stays an empty list, matching
    the original's own ``e.get("stories") or []``; an EMPTY story slot ``[]``
    still counts toward the total (``len(s) > 1`` already guards the
    done-count), which a previous pass established as a real false negative
    when dropped.
    """
    if not isinstance(proj, dict):
        raise ValueError(f"station entry is {type(proj).__name__}, not a mapping")
    epics = proj.get("epics")
    if not epics:
        return None
    if not isinstance(epics, (list, tuple)):
        raise ValueError(f"'epics' is {type(epics).__name__}, not a list")
    stories: list = []
    for epic in epics:
        if not isinstance(epic, dict):
            raise ValueError(f"epic entry is {type(epic).__name__}, not a mapping")
        raw = epic.get("stories") or ()
        if not isinstance(raw, (list, tuple)):
            raise ValueError(f"'stories' is {type(raw).__name__}, not a list")
        for story in raw:
            if not isinstance(story, (list, tuple)):
                raise ValueError(f"story entry is {type(story).__name__}, not a list")
            stories.append(story)
    done = sum(1 for s in stories if len(s) > 1 and s[1] == "done")
    return done, len(stories)


def _check_chain_completeness(
    target: Path, board: dict[str, tuple[int, int]] | None
) -> list[dict]:
    """Port of the original script's own ``check()`` -- see this module's own
    header and the original's for the full INV-A/B/C/D rationale. Findings
    are structured dicts here rather than printed lines; ``kind``/``detail``/
    ``remedy`` text is unchanged from the original.

    Each project is evaluated inside its own try/except
    (``_check_project_chain_completeness``): one project's malformed input
    (a non-UTF-8 file, an unparseable ledger) must not suppress another,
    ALREADY-COMPUTED project's real FAIL findings -- the same multi-project
    independence discipline ``sources/ledger.py``'s own ``_check`` already
    established ("a regression in one project's ledger must not suppress or
    merge with a regression in another"). Wrapping only the whole function in
    ``degrade_on_exception`` (as the first cut of this port did) does not give
    that guarantee: a single bad project anywhere converts every OTHER
    project's real findings into one vacuous WARN, silently turning a real
    compliance violation into an exit-0 "all clear" -- confirmed by adversarial
    review and reproduced live (non-UTF-8 byte in one project's SPEC.md hid a
    genuine ``spec-not-decomposed`` FAIL in an unrelated, well-formed project).

    ``findings`` is owned HERE and appended to in place by the per-project
    helper, not returned by it. With the helper accumulating into a local list
    and returning it at the end, a raise part-way through discarded that
    project's OWN already-computed FAILs -- so a non-UTF-8 ledger in the very
    project that owned a real ``spec-not-decomposed`` violation still turned
    exit 2 into exit 0 (reproduced live). The per-project isolation protected
    every project except the one that failed.
    """
    projects_dir = target / "_bmad-output" / "projects"
    findings: list[dict] = []
    if not projects_dir.is_dir():
        return findings

    for project_dir in sorted(projects_dir.iterdir()):
        if not (project_dir / "planning-artifacts").is_dir():
            continue
        project = project_dir.name
        try:
            _check_project_chain_completeness(project_dir, board, findings)
        except Exception as exc:  # noqa: BLE001 -- one project's failure must
            # not discard every other project's already-computed findings.
            findings.append({
                # NOT "INV-A": this catch wraps the whole INV-A/B/C/D
                # evaluation, so stamping one invariant would point an
                # operator (or an --inv filter) at Spec decomposition when the
                # broken input was, say, the ledger INV-B reads.
                "inv": "", "kind": "chain-completeness-unevaluable",
                "project": project, "subject": project, "status": "",
                "detail": (f"could not be evaluated here — "
                           f"{exc.__class__.__name__}: {exc}"),
                "remedy": "fix the malformed/unreadable input, then re-check",
                "warn": True,
            })
    return findings


def _check_project_chain_completeness(
    project_dir: Path,
    board: dict[str, tuple[int, int]] | None,
    findings: list[dict],
) -> None:
    """Append one project's INV-A/B/C/D findings to the CALLER's ``findings``
    list -- split out of ``_check_chain_completeness`` so its caller can
    isolate one project's failure from the rest (see that function's own
    docstring for why the list is the caller's rather than a local return
    value)."""
    project = project_dir.name
    station = project.removeprefix("pyforge-")
    pa = project_dir / "planning-artifacts"

    # ---- INV-A: every open Spec is decomposed ---------------------------------
    #
    # TWO prose strings, deliberately different, each required by a KEEP
    # instruction that survived every round:
    #
    #  * `raw_prose` -- the exact ORIGINAL concatenation (glob order as-is, no
    #    separator). Only the zero-declared-CAP-ids fallback below reads this
    #    one, and it must match the pre-this-story behavior byte-for-byte
    #    (Round 1: a Spec with nothing to check coverage against has the
    #    bare-substring test as its only signal, unchanged).
    #  * `prose` -- the SAME files, glob-sorted (Round 3, kept, for
    #    deterministic anchor/window positions) and, per file, sliced to
    #    start at THAT FILE'S OWN first `## ` heading -- discarding
    #    everything before it (Round 4's fix, replacing Round 3's whole-blob,
    #    first-file-only exclusion, which only ever protected whichever file
    #    happened to sort first). A file with no `## ` heading anywhere is
    #    kept whole, unchanged -- there is no signal to slice against. The
    #    pieces are then `"\n\n"`-joined so no token can span a file
    #    boundary. Only the CAP-id coverage path below reads this one.
    raw_prose = ""
    for doc in list(pa.glob("prds/*/prd.md")) + list(pa.glob("epics*.md")):
        try:
            raw_prose += doc.read_text(encoding="utf-8")
        except Exception:  # noqa: BLE001, S112 -- a non-UTF-8/unreadable
            # prose doc must not abort this project's whole INV-A/B/C/D
            # evaluation; nothing here needs a log line, only degradation.
            continue

    stripped_parts: list[str] = []
    for doc in sorted(pa.glob("prds/*/prd.md")) + sorted(pa.glob("epics*.md")):
        try:
            text = doc.read_text(encoding="utf-8")
        except Exception:  # noqa: BLE001, S112 -- see raw_prose's own loop.
            continue
        heading = _HEADING_RE.search(text)
        stripped_parts.append(text[heading.start():] if heading else text)
    prose = "\n\n".join(stripped_parts)

    spec_paths = sorted(pa.glob("specs/spec-*/SPEC.md"))
    all_slugs = [p.parent.name for p in spec_paths]
    cited_by_spec = _cited_cap_ids_by_spec(prose, all_slugs)

    for spec_md in spec_paths:
        slug = spec_md.parent.name
        try:
            spec_text = spec_md.read_text(encoding="utf-8")
        except Exception:  # noqa: BLE001 -- an unreadable/non-UTF-8 SPEC.md
            # degrades to "no frontmatter, no declared CAP ids" here rather
            # than aborting this project's whole INV-A/B/C/D pass.
            spec_text = ""
        status = str(_frontmatter_from_text(spec_text).get("status", "")).strip()
        if status not in OPEN_SPEC_STATUSES or slug in DEFERRED_SPECS:
            continue

        declared = _parse_declared_cap_ids(spec_text)
        if not declared:
            # Zero-CAP fallback: BYTE-IDENTICAL to the pre-this-story check,
            # against the FULL, unstripped `raw_prose` (Round 1's own
            # requirement -- see the block comment above).
            bare = slug.removeprefix("spec-")
            if bare not in raw_prose and slug not in raw_prose:
                findings.append({
                    "inv": "INV-A", "kind": "spec-not-decomposed",
                    "project": project, "subject": slug, "status": status,
                    "detail": (f"{station} owns an open Spec ({status}) that no FR or "
                               f"epic references — the station can render 100% while "
                               f"owing it"),
                    "remedy": (f"decompose {slug} into {project}'s PRD + epics, or add "
                               f"it to DEFERRED_SPECS with the reason"),
                })
            continue

        uncovered = sorted(declared - cited_by_spec.get(slug, set()))
        if uncovered:
            missing = _format_cap_ids(uncovered)
            findings.append({
                "inv": "INV-A", "kind": "spec-not-decomposed",
                "project": project, "subject": slug, "status": status,
                "detail": (f"{station} owns an open Spec ({status}) with {missing} "
                           f"uncovered by any epic or FR — the station can render "
                           f"100% while owing them"),
                "remedy": (f"decompose {missing} of {slug} into {project}'s PRD + "
                           f"epics, or add {slug} to DEFERRED_SPECS with the reason "
                           f"(DEFERRED_SPECS remains available as a whole-Spec escape "
                           f"hatch)"),
            })

    # ---- INV-B: epics.md set == ledger set ------------------------------------
    epics_md = _canonical_epics(project_dir)
    ledger = pa / "sprint-status-ledger.yaml"
    rows = _ledger_rows(ledger) if ledger.is_file() else {}
    story_rows = {k: v for k, v in rows.items() if not k.startswith("epic-")}
    led, unparsed = _ledger_story_ids(story_rows)

    if epics_md and unparsed:
        findings.append({
            "inv": "INV-B", "kind": "unparseable-ledger-key",
            "project": project, "subject": f"{len(unparsed)} key(s)",
            "status": ", ".join(sorted(unparsed)[:6]),
            "detail": ("no recognisable story id — reported rather than dropped, "
                       "because silently skipping a key is how a detector claims a "
                       "clean set it never compared"),
            "remedy": "rename to <epic>-<seq>-… or <wave><n>-…, or retire the key",
        })
    if epics_md and story_rows and not _story_ids_from_epics(epics_md):
        findings.append({
            "inv": "INV-D", "kind": "canonical-epics-declares-no-stories",
            "project": project, "subject": epics_md.name,
            "status": f"0 `### Story` headings vs {len(story_rows)} ledger key(s)",
            "detail": ("the canonical epics doc declares NO stories in the shape every "
                       "other station uses, so INV-B has nothing to compare and would "
                       "silently pass — an empty set trivially matches nothing"),
            "remedy": ("rewrite as `## Epic N: Title` + `### Story <id>: Title`, "
                       "covering every ledger story"),
        })
    if epics_md and story_rows:
        ep_sets = _story_ids_from_epics(epics_md)
        ep_all = {i for s in ep_sets for i in s}
        if ep_sets and led:
            only_epics = sorted(next(iter(sorted(s))) for s in ep_sets if not (s & led))
            only_ledger = sorted(led - ep_all)
            if only_epics:
                findings.append({
                    "inv": "INV-B", "kind": "story-without-ledger-key",
                    "project": project, "subject": f"{len(only_epics)} story(ies)",
                    "status": ", ".join(only_epics[:10]),
                    "detail": ("in epics.md with no ledger key — the board's percentage "
                               "is computed over a set that excludes them"),
                    "remedy": f"add them to {project}'s Tier-3 feed, then sprint-ledger-sync",
                })
            if only_ledger:
                findings.append({
                    "inv": "INV-B", "kind": "ledger-key-without-story",
                    "project": project, "subject": f"{len(only_ledger)} key(s)",
                    "status": ", ".join(only_ledger[:10]),
                    "detail": "in the ledger with no epics.md story — an untraceable row",
                    "remedy": f"add the story to {epics_md.name}, or retire the key",
                })

    # ---- INV-C: board line == ledger ------------------------------------------
    if board is not None and station in board and story_rows:
        b_done, b_total = board[station]
        l_done = sum(1 for v in story_rows.values() if v == "done")
        if (b_total, b_done) != (len(story_rows), l_done):
            findings.append({
                "inv": "INV-C", "kind": "board-diverges-from-ledger",
                "project": project, "subject": station,
                "status": f"board {b_done}/{b_total} vs ledger {l_done}/{len(story_rows)}",
                "detail": ("the Guildhall renders a different story set than the "
                           "durable record; scan_projects only UPGRADES a curated "
                           "line, so this cannot self-heal"),
                "remedy": "rebuild the station's data.js epics array from its ledger",
            })


def gather_chain_completeness(target: Path) -> tuple[Finding, ...]:
    """Judge whether every station's plan is decomposed and its epics, ledger
    and board agree -- the library form of
    ``scripts/chain_completeness_check.py``'s own ``main()``, minus the
    print/exit CLI surface. Every INV-A/B/C/D violation becomes one FAIL
    ``Finding``; an unreadable/absent ``_bmad-output/projects`` degrades to a
    vacuous OK rather than raising.
    """
    return degrade_on_exception(
        Source.CHAIN_COMPLETENESS,
        "chain-completeness",
        lambda: _gather_chain_completeness(target),
    )


# === gather_chain_layers_audit ===============================================
#
# Story 17.3 / FR-150 residual + FR-152 — read-only layer-presence report for
# ONE named project. Story 21.1 / FR-192 CAP-3 extends this with coherence,
# staleness, and orphan-freedom checkpoints (pass/fail per checkpoint), seeded
# from docs/dashboard/generate.py's FLEET_STAGES / scan_fleet / _chain_audit_verdict
# and dream_chain_orphan_index — never a second derivation or cached table.
# Distinct from INV-A..D (gather_chain_completeness) and from dreams-hygiene
# (--dreams). Invoked as:
#   python -m pyforge.doctor.sources chain-completeness --layers --project <slug>

_CHAIN_AUDIT_CHECKPOINTS = (
    ("layers", "chain-audit-checkpoint-layers"),
    ("coherence", "chain-audit-checkpoint-coherence"),
    ("staleness", "chain-audit-checkpoint-staleness"),
    ("orphans", "chain-audit-checkpoint-orphans"),
)


def _checkpoint_finding(
    project: str,
    name: str,
    check: str,
    passed: bool,
    detail: dict,
) -> Finding:
    return Finding(
        source=Source.CHAIN_LAYERS_AUDIT,
        check=check,
        status=DoctorStatus.OK if passed else DoctorStatus.FAIL,
        message=(
            f"project {project}: {name} checkpoint pass"
            if passed
            else f"project {project}: {name} checkpoint fail"
        ),
        evidence={
            "kind": check,
            "project": project,
            "checkpoint": name,
            "pass": passed,
            **detail,
        },
    )


def gather_chain_layers_audit(
    target: Path, project: str
) -> tuple[Finding, ...]:
    """CAP-3 chain audit for ``project`` (Stories 17.3 + 21.1).

    Read-only; pass/fail per checkpoint (layers, coherence, staleness,
    orphans). Does not reimplement INV-A..D or dreams-hygiene.
    ``project`` is the BMAD project slug (e.g. ``pyforge-marshal``).
    """
    return degrade_on_exception(
        Source.CHAIN_LAYERS_AUDIT,
        "chain-layers-audit",
        lambda: _gather_chain_layers_audit(target, project),
    )


def _gather_chain_layers_audit(
    target: Path, project: str
) -> tuple[Finding, ...]:
    try:
        gen = _load_dashboard_generate(target)
    except Exception as exc:  # noqa: BLE001 -- unevaluable, never crash
        return (
            Finding(
                source=Source.CHAIN_LAYERS_AUDIT,
                check="chain-layers-audit-unevaluable",
                status=DoctorStatus.WARN,
                message=(
                    f"fleet_scan failed to load — "
                    f"chain layer audit cannot be evaluated ({exc})"
                ),
                evidence={
                    "kind": "chain-layers-audit-unevaluable",
                    "project": project,
                    "detail": str(exc),
                    "subject": "pyforge.doctor.sources.fleet_scan",
                },
            ),
        )

    # Point generate.py's REPO_ROOT at *this* target so _resolve/_stage_globs
    # seed the live or fixture tree without forking their glob tables
    # (FR-152: never silently audit another checkout).
    saved_root = getattr(gen, "REPO_ROOT", None)
    saved_dreams = getattr(gen, "DREAMS_DIR", None)
    saved_pixi = getattr(gen, "_PIXI_TASKS", None)
    root = target.resolve()
    try:
        gen.REPO_ROOT = root
        gen.DREAMS_DIR = root / "docs" / "dreams"
        if hasattr(gen, "_PIXI_TASKS"):
            gen._PIXI_TASKS = None
        stages = tuple(gen.FLEET_STAGES)
        na = set(gen.FLEET_NA.get(project, set()))
        if project not in getattr(gen, "FLEET_UX", set()):
            na |= {"ux"}
        # Primary chain: slug == project (station's own chain). Only that
        # project's globs are resolved — sibling project trees are never
        # walked (FR-152).
        globs = gen._stage_globs(project, project, primary=True)
        layers: dict[str, bool] = {}
        files: dict[str, list[str]] = {}
        for st in stages:
            if st == "verify":
                # generate.py: not a file — a declared pixi gate. Prefer the
                # same candidates; when pixi.toml is absent (fixtures), treat
                # as absent rather than inventing a second rule.
                try:
                    tasks = gen._pixi_tasks()
                except Exception:  # noqa: BLE001
                    tasks = set()
                candidates = [
                    f"{project}-test",
                    f"{project.removeprefix('pyforge-')}-test",
                ] + list(getattr(gen, "FLEET_VERIFY_ALIAS", {}).get(project, ()))
                gate = next((t for t in candidates if t in tasks), "")
                layers[st] = bool(gate)
                files[st] = [gate] if gate else []
                continue
            found = gen._resolve(globs.get(st, []))
            files[st] = found
            layers[st] = bool(found)
    finally:
        if saved_root is not None:
            gen.REPO_ROOT = saved_root
        if saved_dreams is not None:
            gen.DREAMS_DIR = saved_dreams
        if hasattr(gen, "_PIXI_TASKS"):
            gen._PIXI_TASKS = saved_pixi

    # A project with no planning-artifacts tree at all is unevaluable —
    # distinguishes "all layers missing on a real station" from "typo slug".
    pa = root / "_bmad-output" / "projects" / project / "planning-artifacts"
    if not pa.is_dir():
        return (
            Finding(
                source=Source.CHAIN_LAYERS_AUDIT,
                check="chain-layers-audit-unevaluable",
                status=DoctorStatus.WARN,
                message=(
                    f"project {project!r} has no planning-artifacts tree — "
                    "chain layer audit cannot be evaluated"
                ),
                evidence={
                    "kind": "chain-layers-audit-unevaluable",
                    "project": project,
                    "detail": "planning-artifacts missing",
                    "subject": str(
                        Path("_bmad-output")
                        / "projects"
                        / project
                        / "planning-artifacts"
                    ),
                },
            ),
        )

    applicable = [s for s in stages if s not in na]
    present = [s for s in applicable if layers[s]]
    missing = [s for s in applicable if not layers[s]]

    # CAP-3 coherence/staleness: reuse scan_fleet's live row for this project.
    fleet = gen.scan_fleet({}, None)
    fleet_row = next(
        (
            r
            for r in fleet.get("rows", [])
            if r.get("project") == project and r.get("slug") == project
        ),
        None,
    )
    if fleet_row is None:
        fleet_row = next(
            (r for r in fleet.get("rows", []) if r.get("project") == project),
            None,
        )
    if fleet_row is None:
        return (
            Finding(
                source=Source.CHAIN_LAYERS_AUDIT,
                check="chain-layers-audit-unevaluable",
                status=DoctorStatus.WARN,
                message=(
                    f"project {project!r} has no fleet chain row — "
                    "CAP-3 audit cannot be evaluated"
                ),
                evidence={
                    "kind": "chain-layers-audit-unevaluable",
                    "project": project,
                    "detail": "no fleet row",
                },
            ),
        )

    from . import chain as chain_sources

    orphan_kinds = chain_sources.dream_chain_orphan_index(root).get(project, [])
    chain_audit = gen._chain_audit_verdict(fleet_row, orphan_kinds)

    findings: list[Finding] = []
    for cp_name, check in _CHAIN_AUDIT_CHECKPOINTS:
        cp = chain_audit["checkpoints"][cp_name]
        findings.append(
            _checkpoint_finding(
                project,
                cp_name,
                check,
                cp["pass"],
                {k: v for k, v in cp.items() if k != "pass"},
            )
        )

    verdict_pass = chain_audit["verdict"] == "pass"
    findings.append(
        Finding(
            source=Source.CHAIN_LAYERS_AUDIT,
            check="chain-audit-verdict",
            status=DoctorStatus.OK if verdict_pass else DoctorStatus.FAIL,
            message=(
                f"project {project}: CAP-3 chain audit pass"
                if verdict_pass
                else f"project {project}: CAP-3 chain audit fail"
            ),
            evidence={
                "kind": "chain-audit-verdict",
                "project": project,
                "verdict": chain_audit["verdict"],
                "checkpoints": chain_audit["checkpoints"],
                "layers": layers,
                "files": files,
                "na": sorted(na),
                "present": present,
                "missing": missing,
                "stages": list(stages),
            },
        )
    )

    # Layer-presence summary retained for 17.3 continuity (warn-only detail).
    findings.append(
        Finding(
            source=Source.CHAIN_LAYERS_AUDIT,
            check="chain-layers-audit",
            status=DoctorStatus.OK if not missing else DoctorStatus.WARN,
            message=(
                f"project {project}: {len(present)}/{len(applicable)} chain layers "
                f"present"
                + (f"; missing: {', '.join(missing)}" if missing else "")
            ),
            evidence={
                "kind": "chain-layers-audit",
                "project": project,
                "layers": layers,
                "files": files,
                "na": sorted(na),
                "present": present,
                "missing": missing,
                "stages": list(stages),
                "chainAudit": chain_audit,
            },
        )
    )
    return tuple(findings)


def _gather_chain_completeness(target: Path) -> tuple[Finding, ...]:
    # Derived ONCE here rather than inside `_check_chain_completeness`, so the
    # OK Finding below can say whether INV-C was actually evaluated. It cannot
    # be recomputed there and here independently for the same reason
    # `_gather_dashboard_drift` derives `projects` once: two copies can
    # silently disagree the moment either is edited.
    board = _board_lines(target / "docs" / "dashboard" / "data.js")
    raw = _check_chain_completeness(target, board)
    if not raw:
        projects_dir = target / "_bmad-output" / "projects"
        n = (
            len([p for p in projects_dir.iterdir() if (p / "planning-artifacts").is_dir()])
            if projects_dir.is_dir()
            else 0
        )
        # NEVER ASSERT AN INVARIANT THAT WAS NOT EVALUATED. An unreadable or
        # structurally-wrong `data.js` makes `_board_lines` return None, which
        # is the spec's own "INV-C silently skipped; INV-A/B/D unaffected" row
        # -- but the message still claimed "...and board agree" over a board
        # this gather had never read, and nothing in `evidence` let a consumer
        # tell the two apart. The sibling `_board_projects` refuses exactly
        # this coercion for `gather_dashboard_drift`, so the same bytes
        # produced a confident OK here and an honest WARN there.
        return (
            Finding(
                source=Source.CHAIN_COMPLETENESS,
                check="chain-completeness",
                status=DoctorStatus.OK,
                message=(
                    "every open Spec is decomposed, and epics, ledger and board agree"
                    if board is not None
                    else "every open Spec is decomposed and epics and ledger agree; "
                         "INV-C (Guildhall data.js) is retired, so INV-C was NOT "
                         "evaluated"
                ),
                evidence={"projects": n, "board_read": board is not None},
            ),
        )
    return tuple(
        Finding(
            source=Source.CHAIN_COMPLETENESS,
            check=item["kind"],
            status=DoctorStatus.WARN if item.get("warn") else DoctorStatus.FAIL,
            message=f"{item['project']}: {item['detail']}",
            evidence={
                "inv": item["inv"],
                "project": item["project"],
                "subject": item["subject"],
                "status": item["status"],
                "remedy": item["remedy"],
            },
        )
        for item in raw
    )


# === gather_dashboard_drift (scope="repo", FR-7 reintroduction gate) ========
#
# Ported from scripts/dashboard_drift_check.py -- see that script's own module
# docstring for the full three-way rationale (stale-done, missing-story,
# twin-stale/twin-missing/twin-ahead) and why this check is LOCAL-ONLY: it
# reads each project's gitignored Tier-3 `sprint-status.yaml`, invisible to CI.

_DRIFT_STORY_HEADING = re.compile(r"^###\s+Story\s+([0-9]+\.[0-9]+[a-z]?)\s*[:—-]")
_DRIFT_DONE = frozenset({"done"})


def _load_foreign_module(path: Path, mod_name: str):
    """``exec_module`` an arbitrary ``target``-relative Python file and return
    it -- the body behind ``_load_dashboard_generate``, the same
    ``importlib.util.spec_from_file_location`` dynamic load the original
    ``dashboard_drift_check.py`` already used (Boundaries: preserve, don't
    redesign).

    Sole caller since Story 6.9: ``gather_check_layout`` used to share this
    helper via its own ``_load_check_layout`` (dynamically loading
    ``check_layout.py`` to reuse its assertions), but that origin file is
    now deleted and its logic ported into this module as permanent code
    (``_check_layout_geometry``/``_layout_chip_rows``/the ``_LAYOUT_*``
    constants) -- there is nothing left for it to dynamically load. This
    helper's own hardening was originally consolidated from two near-copies
    that had already drifted (only one had the ``sys.path``/``sys.modules``
    guards below); kept as ONE helper rather than trimmed back to inline
    code, since a future gather reusing another station's script the same
    way ``gather_dashboard_drift`` reuses ``generate.py`` would need it again.

    Three things this adds over a bare ``exec_module``, each guarding the
    Doctor PROCESS from a file it does not own:

    * ``sys.path`` is snapshotted and restored. ``generate.py`` does an
      unguarded ``sys.path.insert(0, REPO_ROOT/"scripts")`` at import time --
      harmless in the one-shot script this was ported from, but here it
      permanently prepends an ARBITRARY ``target``'s ``scripts/`` to Doctor's
      import path and grows it on every call, so a later import inside Doctor
      could resolve against a foreign tree.
    * A half-initialised module is not left behind in ``sys.modules`` when
      ``exec_module`` raises.
    * ``SystemExit`` is converted to a plain ``Exception``. A foreign file is
      free to call ``sys.exit()`` at import; ``SystemExit`` is a
      ``BaseException``, so ``degrade_on_exception`` -- which documents that
      it deliberately never catches one -- would let it escape the gather and
      break ``gather_dashboard_drift``'s own "never a raised exception"
      contract. This is the same conversion ``_load_data_js`` already makes
      for the same reason; the loader had been left out. ``KeyboardInterrupt``
      is NOT converted.
    """
    if not path.is_file():
        raise FileNotFoundError(f"{path} not found")
    spec = importlib.util.spec_from_file_location(mod_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load a module spec for {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    saved_path = list(sys.path)
    try:
        spec.loader.exec_module(mod)
    except SystemExit as exc:
        sys.modules.pop(mod_name, None)
        raise RuntimeError(f"{path} called sys.exit({exc.code!r}) at import") from exc
    except BaseException:
        sys.modules.pop(mod_name, None)
        raise
    finally:
        sys.path[:] = saved_path
    return mod


def _load_dashboard_generate(target: Path):
    """Import ``target/scripts/fleet_scan.py`` (parsers extracted from the
    retired Guildhall generator) and point it at ``target``.
    """
    gen = _load_foreign_module(
        target / "scripts" / "fleet_scan.py",
        "_doctor_board_fleet_scan",
    )
    root = target.resolve()
    gen.REPO_ROOT = root
    if hasattr(gen, "DREAMS_DIR"):
        gen.DREAMS_DIR = root / "docs" / "dreams"
    if hasattr(gen, "_PIXI_TASKS"):
        gen._PIXI_TASKS = None
    return gen


def _load_data_js(target: Path) -> dict:
    """Port of ``dashboard_drift_check.py``'s own ``_load_data_js`` -- with
    one deliberate change. The original ``raise SystemExit(...)`` on an
    unparseable ``data.js`` is replaced with a plain ``ValueError``:
    ``SystemExit`` is a ``BaseException``, not an ``Exception``, so
    ``sources.degrade_on_exception`` (which ``gather_dashboard_drift`` wraps
    itself in) would never catch it, and it would escape this library call
    exactly like the CLI script's own ``exit`` was never meant to (Boundaries:
    "the gather itself must not raise it").
    """
    data_js = target / "docs" / "dashboard" / "data.js"
    text = data_js.read_text(encoding="utf-8")
    m = re.search(r"window\.DASHBOARD_DATA\s*=\s*(\{.*?\});?\s*$", text, re.DOTALL)
    if not m:
        raise ValueError(f"cannot parse {data_js}")
    return json.loads(m.group(1))


def _drift_epics_md_ids(path: Path) -> list[tuple[str, str | None]]:
    """Every story heading in an epics.md as ``(id, None)`` -- verbatim from
    the original (the second tuple slot is a retired dual-id accommodation;
    see the original's own docstring)."""
    out: list[tuple[str, str | None]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001 -- an unreadable/non-UTF-8 epics.md is
        # "nothing to compare", not a reason to discard the twin findings this
        # station's caller has ALREADY computed (reproduced live: one 0xe9 byte
        # turned a real `twin-missing` FAIL into a WARN, exit 2 -> exit 0).
        return out
    for line in text.splitlines():
        m = _DRIFT_STORY_HEADING.match(line)
        if m:
            out.append((m.group(1), None))
    return out


def _board_projects(data: dict, target: Path) -> dict:
    """``data.js``'s ``projects`` mapping, or a raised ``ValueError`` when the
    file does not actually carry one.

    An ABSENT ``projects`` key is an empty board -- the original script's
    ``data.get("projects", {})`` reads it exactly that way, and an empty board
    legitimately produces no findings. A key that is PRESENT but not a mapping
    (``null``, a list, a string) is something else entirely: the original
    crashed on it, and coercing it to ``{}`` instead made
    ``gather_dashboard_drift`` return a confident OK -- *"the committed data.js
    matches the feeds"* -- over a board it had never read. Trading a loud crash
    for a false green is the single worst outcome available to a detector whose
    whole purpose is catching a board that lies, so this raises instead:
    ``gather_dashboard_drift``'s own ``degrade_on_exception`` turns it into the
    honest WARN, exactly as it already does for an unparseable ``data.js``.
    """
    if "projects" not in data:
        return {}
    projects = data["projects"]
    if not isinstance(projects, dict):
        raise ValueError(
            f"cannot read the board in {target / 'docs' / 'dashboard' / 'data.js'}: "
            f"'projects' is {type(projects).__name__}, not a mapping"
        )
    return projects


def _check_dashboard_drift(target: Path, gen, projects: dict) -> list[dict]:
    """Port of ``dashboard_drift_check.py``'s own ``main()`` body -- the three
    checks (tracked twin vs. Tier-3 feed, committed baseline vs. feed,
    epics.md vs. board), producing structured dicts instead of printed lines.
    ``kind``/message text is unchanged from the original.

    ``findings`` is the CALLER's list, appended to in place by the per-station
    helper -- see ``_check_chain_completeness``'s own docstring for why: a
    helper that accumulates locally and returns at the end throws away its own
    station's already-computed FAILs the moment anything downstream raises."""
    findings: list[dict] = []

    for key, proj in sorted(projects.items()):
        try:
            _check_project_dashboard_drift(target, gen, key, proj, findings)
        except (Exception, SystemExit) as exc:  # noqa: BLE001 -- one station's
            # malformed data.js entry or feed must not discard every other
            # station's already-computed drift findings (mirrors
            # _check_chain_completeness's own per-project isolation).
            # SystemExit is in the tuple because this body CALLS functions off
            # a dynamically exec'd, Marshal-owned file, which is free to
            # sys.exit() at call time as well as at import; KeyboardInterrupt
            # is deliberately left out.
            findings.append({
                "kind": "dashboard-drift-unevaluable", "project": key,
                "detail": (f"{key}: could not be evaluated here — "
                           f"{exc.__class__.__name__}: {exc}"),
                "warn": True,
            })
    return findings


def _check_project_dashboard_drift(
    target: Path, gen, key: str, proj: object, findings: list[dict]
) -> None:
    """Append one station's drift findings to the CALLER's ``findings`` list --
    split out of ``_check_dashboard_drift`` so its caller can isolate one
    station's failure from the rest (and so a late raise cannot discard the
    findings this station has already produced)."""
    if not isinstance(proj, dict):
        return  # a malformed data.js entry has no epics to compare
    all_stories = [
        s for e in proj.get("epics", []) or []
        if isinstance(e, dict)
        for s in e.get("stories", []) or []
        if isinstance(s, (list, tuple)) and s
    ]
    # `stories` is the (id, status) unpacking set -- it needs >= 2 elements.
    # `board_ids` is a pure MEMBERSHIP set and needs only s[0], so it must be
    # built from the unfiltered list: filtering a 1-element `["1.1"]` out of
    # board_ids made a story that IS on the board look absent, emitting a
    # false `missing-story` FAIL.
    stories = [s for s in all_stories if len(s) >= 2]
    board_ids = {s[0] for s in all_stories}

    # --- twin vs the Tier-3 feed --------------------------------------
    rel_feed = gen.PROJECT_SOURCES.get(key)
    slug_ = gen._KEY_SLUG_OVERRIDE.get(key, f"pyforge-{key}")
    twin = (target / "_bmad-output" / "projects" / slug_
            / "planning-artifacts" / "sprint-status-ledger.yaml")
    feed_p = target / rel_feed if rel_feed else None
    if feed_p and feed_p.is_file() and twin.is_file():
        feed_map = gen.parse_sprint_status(feed_p)
        twin_map = gen.parse_sprint_status(twin)
        drifted = sorted(
            k for k in set(feed_map) | set(twin_map)
            if feed_map.get(k) != twin_map.get(k)
        )
        if drifted:
            shown = ", ".join(drifted[:4]) + ("…" if len(drifted) > 4 else "")
            regressing = sorted(
                k for k in drifted
                if twin_map.get(k) == "done" and feed_map.get(k) != "done"
            )
            if regressing:
                rshown = ", ".join(regressing[:4]) + ("…" if len(regressing) > 4 else "")
                findings.append({
                    "kind": "twin-ahead", "project": key,
                    "detail": (
                        f"{key}: the Tier-3 feed is BEHIND the tracked "
                        f"ledger — it would un-finish {len(regressing)} story(ies) "
                        f"({rshown}). **Do NOT run sprint-ledger-sync**: the twin is "
                        f"the durable record and the feed is the lossy one. Repair the "
                        f"feed from the twin (`sprint-ledger-sync --repair-feed "
                        f"--project {key}`), then re-check."
                    ),
                })
            else:
                findings.append({
                    "kind": "twin-stale", "project": key,
                    "detail": (
                        f"{key}: the tracked sprint-status ledger disagrees "
                        f"with the Tier-3 feed on {len(drifted)} story(ies) ({shown}), "
                        f"none of them un-finishing a story. CI reads the TWIN, so the "
                        f"deploy would render the stale set: run `pixi run -e "
                        f"local-recipes sprint-ledger-sync --project {key}` and commit."
                    ),
                })
    elif feed_p and feed_p.is_file() and not twin.is_file():
        findings.append({
            "kind": "twin-missing", "project": key,
            "detail": (
                f"{key}: has a Tier-3 sprint feed but no tracked "
                f"ledger at {twin.relative_to(target)} — CI cannot see this "
                f"project's completions and will fall back to commit archaeology. "
                f"Run `pixi run -e local-recipes sprint-ledger-sync`."
            ),
        })

    # --- committed baseline vs the local feed ---------------------------
    rel = gen.PROJECT_SOURCES.get(key)
    feed_path = target / rel if rel else None
    if feed_path and feed_path.is_file():
        sprint = gen.parse_sprint_status(feed_path)
        for sid, status, *_rest in stories:
            feed = gen.dashboard_id_to_status(sid, sprint)
            if feed is None:
                continue
            if feed in _DRIFT_DONE and status not in _DRIFT_DONE:
                findings.append({
                    "kind": "stale-done", "project": key,
                    "detail": (
                        f"{key}:{sid} is '{feed}' in the sprint feed but "
                        f"'{status}' on the board — the committed baseline is behind. "
                        f"`--source git` never downgrades, so this will NOT self-heal "
                        f"at deploy: story status lives on Lane 1 /console/ "
                        f"(Guildhall data.js retired)."
                    ),
                })

    # --- no epics.md story is missing from the board --------------------
    slug = gen._KEY_SLUG_OVERRIDE.get(key, f"pyforge-{key}")
    epics_md = (target / "_bmad-output" / "projects" / slug
                / "planning-artifacts" / "epics.md")
    if not epics_md.is_file() or key in getattr(gen, "_DERIVE_EXCLUDE", set()):
        return
    heading_ids = _drift_epics_md_ids(epics_md)
    if not heading_ids:
        return
    for lead, alt in heading_ids:
        if lead in board_ids or (alt and alt in board_ids):
            continue
        shown = f"{lead}" + (f" ({alt})" if alt else "")
        findings.append({
            "kind": "missing-story", "project": key,
            "detail": (
                f"{key}: epics.md has Story {shown} but no story with "
                f"that id is on the board. If this line's story list is hand-authored "
                f"(scan_projects warns when it cannot parse the headings), add it to "
                f"data.js by hand."
            ),
        })


def _no_system_exit(fn):
    """Run ``fn``, converting a ``SystemExit`` it raises into a plain
    ``RuntimeError`` so ``degrade_on_exception`` can see it.

    Both ``gather_dashboard_drift`` and ``gather_check_layout`` CALL functions
    off a dynamically ``exec_module``'d file owned by another station, and such
    a file is free to ``sys.exit()`` from inside a function, not only at import
    time. ``_load_foreign_module`` already makes this conversion for the import
    itself; without the same guard at the call sites a ``SystemExit`` (a
    ``BaseException``, which ``degrade_on_exception`` documents that it
    deliberately never catches) escaped both gathers and broke their own
    "never a raised exception" contract. ``KeyboardInterrupt`` is NOT
    converted.
    """
    try:
        return fn()
    except SystemExit as exc:
        raise RuntimeError(
            f"a dynamically loaded file called sys.exit({exc.code!r}) at call time"
        ) from exc


_RETIRED_CONSOLE_FILES = (
    Path("docs/dashboard/generate.py"),
    Path("docs/dashboard/data.js"),
    Path("docs/dashboard/check_render.js"),
    Path("scripts/dashboard_watch.py"),
)
_RETIRED_CONSOLE_TASKS = (
    "dashboard-gen",
    "dashboard-watch",
    "dashboard-check",
    "dashboard-drift-check",
)


def gather_dashboard_drift(target: Path) -> tuple[Finding, ...]:
    """FR-7 reintroduction gate: the Guildhall generator and its four pixi
    tasks must stay gone. Kedro-Viz is out of scope.
    """
    return degrade_on_exception(
        Source.DASHBOARD_DRIFT,
        "dashboard-drift",
        lambda: _gather_dashboard_drift(target),
    )


def _gather_dashboard_drift(target: Path) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    for rel in _RETIRED_CONSOLE_FILES:
        path = target / rel
        if path.is_file():
            findings.append(
                Finding(
                    source=Source.DASHBOARD_DRIFT,
                    check="dashboard-drift",
                    status=DoctorStatus.FAIL,
                    message=f"retired Guildhall path reintroduced: {rel.as_posix()}",
                    evidence={"kind": "retired-console-reintroduced", "path": rel.as_posix()},
                )
            )
    pixi = target / "pixi.toml"
    if pixi.is_file():
        text = pixi.read_text(encoding="utf-8")
        for task in _RETIRED_CONSOLE_TASKS:
            needle = f"[feature.local-recipes.tasks.{task}]"
            if needle in text:
                findings.append(
                    Finding(
                        source=Source.DASHBOARD_DRIFT,
                        check="dashboard-drift",
                        status=DoctorStatus.FAIL,
                        message=f"retired pixi task reintroduced: {task}",
                        evidence={"kind": "retired-console-task", "task": task},
                    )
                )
    if findings:
        return tuple(findings)
    return (
        Finding(
            source=Source.DASHBOARD_DRIFT,
            check="dashboard-drift",
            status=DoctorStatus.OK,
            message=(
                "Guildhall generator, data.js, and the four dashboard pixi "
                "tasks stay gone"
            ),
            evidence={"retired": True},
        ),
    )


# === gather_check_layout =====================================================
#
# Ported from docs/dashboard/check_layout.py -- see that script's own module
# docstring for the full "why measure geometry, not just execution" rationale
# and the two live incidents (a broken status chip surviving three green
# gates; the running chip's own fix trading one visual bug for another).
#
# Story 6.9 FIX (2026-08-09): this section used to REUSE the origin script's
# ``check()``/``_rows()``/probe constants via a dynamic ``exec_module`` of
# ``target/docs/dashboard/check_layout.py`` (``_load_check_layout``, ported
# from the same ``_load_foreign_module`` ``_load_dashboard_generate`` still
# uses below). That was fine while the origin file existed alongside its
# port; Story 6.9 deletes it -- and a dynamic load of a file that is gone
# does not degrade occasionally, it fails EVERY time, in EVERY environment,
# permanently: the port would move home only to stop functioning the moment
# its own story landed. The assertions therefore move in as real, permanent
# code below (``_check_layout_geometry``/``_layout_chip_rows``, verbatim in
# behavior from the origin's own ``check()``/``_rows()``, prefixed to fit
# this module's existing ``_check_<subject>`` naming convention rather than
# colliding with it) -- no exec, no dependency on a file that may not exist.
# The browser/HTTP orchestration below (``_run_check_layout``) is unchanged
# in shape; only the names it reaches for moved from a loaded module's
# attributes to this module's own.

_LAYOUT_CHECK = "console-bar-layout"

# --- ported verbatim from docs/dashboard/check_layout.py's own module-level
# constants (see that script's history, recoverable via
# `git show HEAD~1:docs/dashboard/check_layout.py` after this story's
# deletion commit) -- values and comments carried unchanged.

# Widths above the 720px collapse breakpoint, where the three-column grid is
# live and all four assertions apply; plus one below it, where stacking is the
# designed behaviour and only no-overlap/in-bounds are meaningful.
_LAYOUT_WIDE = (1600, 1400, 1200, 1000, 820)
_LAYOUT_NARROW = (700,)
_LAYOUT_BREAKPOINT = 720
_LAYOUT_CENTRE_TOL = 2.0   # px; sub-pixel layout means exact 0 is not a fair
# demand -- carried verbatim; unused in the origin too (dead there already,
# not a porting artifact).

# Chips inside the status row. `#chip-gen` deliberately excluded -- it lives in
# `.cbrow` now, and treating it as a row member made the gate report a phantom
# "bar wrapped to 2 rows" (the two elements are in different containers, at the
# same one-line bar height of 34px).
_LAYOUT_CHIPS = ("#chip-ship", "#chip-run")
_LAYOUT_EDGE_TOL = 14.0   # px; the bar's own 12px padding plus a sub-pixel allowance

# Font sizes in px applied to `.cchip`. 11 is the design size; the rest simulate
# a wider font face or a zoomed browser, which is how the operator hits at 11px
# what a runner does not. Above 11 the bar is EXPECTED to grow taller as the
# outer chips wrap -- that is the correct degradation -- so the one-row assertion
# is scoped to the design size only. Centring and non-overlap must hold at ALL
# sizes; they are the invariants.
_LAYOUT_PRESSURES = (11, 14, 17, 20, 24)
_LAYOUT_DESIGN_SIZE = 11

_LAYOUT_APPLY = """(fs) => {
  document.querySelectorAll('.cchip').forEach(e => { e.style.fontSize = fs + 'px'; });
}"""

_LAYOUT_PROBE = """() => {
  const bar = document.querySelector('.cbstatus');
  if (!bar) return null;
  const bb = bar.getBoundingClientRect();
  const box = el => { const b = el.getBoundingClientRect();
    return {l:b.left, r:b.right, t:b.top, b:b.bottom, cx:(b.left+b.right)/2}; };
  const out = {bar:{l:bb.left, r:bb.right, cx:(bb.left+bb.right)/2, h:bb.height}, chips:{}};
  for (const s of %s) {
    const el = document.querySelector(s);
    if (!el) continue;
    const c = box(el);
    const txt = el.querySelector('.ctext');
    c.need = txt ? txt.getBoundingClientRect().width : 0;   // intrinsic label width
    c.have = el.clientWidth;                                 // room the chip actually has
    out.chips[s] = c;
  }
  return out;
}""" % list(_LAYOUT_CHIPS)


class _LayoutQuietHandler(http.server.SimpleHTTPRequestHandler):
    """SimpleHTTPRequestHandler logs every GET to stderr, which buries the one
    line a detector is supposed to emit. A gate's output is its whole product.

    Ported verbatim from the origin's own ``_QuietHandler``; renamed only to
    keep this module's ``_Layout*``/``_layout_*`` prefix consistent now that
    it lives beside ``board.py``'s other sources."""

    def log_message(self, *_args):  # noqa: D102
        pass


def _serve_layout_dir(directory: Path):
    """Serve ``directory`` over an ephemeral loopback port -- ported verbatim
    from the origin's own ``_serve()`` (renamed only for this module's
    prefix convention), so the run is hermetic rather than depending on
    whichever server the operator happens to have open."""
    handler = functools.partial(_LayoutQuietHandler, directory=str(directory))
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


def _layout_chip_rows(chips: dict) -> list[list[str]]:
    """Group chips into visual rows by vertical overlap -- ported verbatim
    from the origin's own ``_rows()`` (renamed only for this module's
    prefix convention; body unchanged)."""
    rows: list[list[str]] = []
    for name in sorted(chips, key=lambda n: chips[n]["t"]):
        c = chips[name]
        for row in rows:
            o = chips[row[0]]
            if c["t"] < o["b"] and o["t"] < c["b"]:
                row.append(name)
                break
        else:
            rows.append([name])
    return rows


def _check_layout_geometry(width: int, m: dict, scenario: str = "live") -> list[str]:
    """The five geometry assertions (edges/no-overlap/one-row/in-bounds/
    not-clipped) -- ported verbatim from the origin's own ``check()``
    (renamed to ``_check_layout_geometry`` to match this module's existing
    ``_check_chain_completeness``/``_check_dashboard_drift`` naming
    convention for "the pure assertion logic behind a gather"; body and
    every message string unchanged)."""
    bar, chips = m["bar"], m["chips"]
    found: list[str] = []
    at = f"w={width} [{scenario}]"
    missing = [c for c in _LAYOUT_CHIPS if c not in chips]
    if missing:
        found.append(f"{at}: chip(s) absent from the DOM: {', '.join(missing)}")
        return found

    rows = _layout_chip_rows(chips)

    # (2) no two chips sharing a row may overlap horizontally
    for row in rows:
        ordered = sorted(row, key=lambda n: chips[n]["l"])
        for a, b in zip(ordered, ordered[1:]):
            gap = chips[b]["l"] - chips[a]["r"]
            if gap < 0:
                found.append(f"{at}: {a} and {b} share a row and OVERLAP by {-gap:.1f}px")

    # (5) no chip is clipping its own label
    for name, c in chips.items():
        if c.get("need", 0) > c.get("have", 0) + 1.0:
            found.append(
                f"{at}: {name} is CLIPPED — label needs {c['need']:.0f}px, chip has "
                f"{c['have']:.0f}px; the text is rendering outside its own box")

    # (4) nothing escapes the bar
    for name, c in chips.items():
        if c["l"] < bar["l"] - 0.5 or c["r"] > bar["r"] + 0.5:
            found.append(
                f"{at}: {name} escapes the bar "
                f"(chip {c['l']:.0f}–{c['r']:.0f} vs bar {bar['l']:.0f}–{bar['r']:.0f})")

    if width > _LAYOUT_BREAKPOINT:
        # (3) one row above the breakpoint -- only at the design font size, since
        # wrapping under font pressure is the intended degradation, not a fault.
        if scenario == f"{_LAYOUT_DESIGN_SIZE}px" and len(rows) != 1:
            found.append(
                f"{at}: bar wrapped to {len(rows)} rows above the {_LAYOUT_BREAKPOINT}px "
                f"breakpoint (height {bar['h']:.0f}px) — a chip is folding when it should not")
        # (1) ship flush left, running flush right
        dl = chips["#chip-ship"]["l"] - bar["l"]
        dr = bar["r"] - chips["#chip-run"]["r"]
        if dl > _LAYOUT_EDGE_TOL:
            found.append(f"{at}: last-shipped chip is {dl:.1f}px from the bar's left edge "
                         f"(tolerance {_LAYOUT_EDGE_TOL}px) — it is not left-flush")
        if dr > _LAYOUT_EDGE_TOL:
            found.append(f"{at}: running chip is {dr:.1f}px from the bar's right edge "
                         f"(tolerance {_LAYOUT_EDGE_TOL}px) — it is not right-flush")
    return found


def _suppress_close(close) -> None:
    """Run a cleanup callable, swallowing anything it raises.

    Used only in ``_run_check_layout``'s ``finally`` blocks: a browser or
    socket that fails to shut down is not a layout verdict, and letting it
    propagate replaced every already-collected finding with one vacuous WARN.
    """
    try:
        close()
    except Exception:  # noqa: BLE001, S110 -- see the docstring; a failed
        # teardown must never be able to change what this gather reports.
        pass


def _layout_warn(message: str, target: Path) -> tuple[Finding, ...]:
    return (
        Finding(
            source=Source.CHECK_LAYOUT,
            check=_LAYOUT_CHECK,
            status=DoctorStatus.WARN,
            message=message,
            evidence={"target": str(target)},
        ),
    )


def gather_check_layout(target: Path) -> tuple[Finding, ...]:
    """Judge whether the Guildhall console bar's status chips actually
    render without overlapping, clipping, or escaping the bar -- the library
    form of ``docs/dashboard/check_layout.py``'s own ``main()``, minus the
    print/exit CLI surface.

    NEVER CLAIMS GREEN IT DID NOT MEASURE, mirroring the original's own
    contract (its docstring: "a detector that cannot run reports unknown,
    never green"). A missing ``data.js``, an unimportable ``playwright``, no
    launchable chromium, or a bar that never rendered at any width all
    degrade to exactly ONE WARN ``Finding`` -- never a FAIL, never a raised
    exception. An INDIVIDUAL width that could not be measured while others
    were adds one WARN ``Finding`` of its own and leaves the measured
    widths' real verdict intact (see ``_run_check_layout`` for why
    cannot-measure must not be reported as a layout FAIL). ``playwright``
    stays an optional, try/except-guarded import here: this package's pixi
    env does not install it (Boundaries).

    Story 6.9: no longer gates on loading ``check_layout.py`` -- the
    assertions are permanent code in this module now (see the section header
    above), so there is nothing left to fail to load.
    """
    retired = target / "docs" / "dashboard" / "data.js"
    generator = target / "docs" / "dashboard" / "generate.py"
    if retired.is_file() or generator.is_file():
        return (
            Finding(
                source=Source.CHECK_LAYOUT,
                check=_LAYOUT_CHECK,
                status=DoctorStatus.FAIL,
                message="retired Guildhall console blob reintroduced",
                evidence={
                    "data_js": retired.is_file(),
                    "generate_py": generator.is_file(),
                },
            ),
        )
    return (
        Finding(
            source=Source.CHECK_LAYOUT,
            check=_LAYOUT_CHECK,
            status=DoctorStatus.OK,
            message="Guildhall layout gate retired with the generator; Kedro-Viz is not measured",
            evidence={"retired": True},
        ),
    )


def _run_check_layout(target: Path, sync_playwright) -> tuple[Finding, ...]:
    """The NEW orchestration: launch a browser, serve ``target/docs/dashboard/``
    over ``_serve_layout_dir``, measure the console bar at every width x
    font-pressure combination the origin script defined, and hand each
    width's probe result to ``_check_layout_geometry``. Every explicit
    ``exit 2`` branch the original had (no usable chromium, the bar never
    rendering) becomes a WARN ``Finding`` here instead of a process exit.

    "COULD NOT MEASURE" AND "MEASURED, AND IT IS BROKEN" ARE DIFFERENT
    VERDICTS, and this function keeps them apart in two separate lists. A
    ``networkidle`` goto with a 20s timeout makes a single width's flake the
    EXPECTED failure mode, and ``exit_code_for`` maps FAIL to exit 2 while WARN
    leaves it at 0 -- so folding an unmeasurable width in with the real layout
    findings reported a transient browser hiccup as a broken console bar and
    turned the gate red on a clean board (reproduced live). That also
    contradicts this module's own two siblings, which both spell
    cannot-evaluate ``warn`` (``chain-completeness-unevaluable``,
    ``dashboard-drift-unevaluable``). The ``.cbstatus not found`` line stays a
    FAIL, because that one IS the original's own finding text for a bar that
    loaded and did not render.
    """
    # `target/docs/dashboard`, NOT the origin script's own `HERE`
    # (`Path(__file__).resolve().parent`) -- that resolved to wherever
    # check_layout.py physically lived, which was only the same directory as
    # the board this gather was ASKED about when the file happened to sit
    # beside it (a symlinked/shared `check_layout.py` measured a DIFFERENT
    # repo's dashboard, reproduced live before this was ported). The origin
    # script had no `target` parameter and so could not hit this; serving
    # `target`'s own directory is the fix, and it is unconditional now that
    # there is no loaded module's `HERE` to prefer by mistake.
    httpd, port = _serve_layout_dir(target / "docs" / "dashboard")
    url = f"http://127.0.0.1:{port}/index.html"
    raw_findings: list[str] = []
    unmeasured: list[str] = []
    measured = 0
    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(channel="chrome")
            except Exception:  # noqa: BLE001 -- fall back to the bundled chromium
                try:
                    browser = p.chromium.launch()
                except Exception as exc:  # noqa: BLE001 -- no usable browser at all
                    return _layout_warn(
                        f"no usable chromium ({type(exc).__name__}) — cannot measure layout",
                        target,
                    )
            try:
                for width in (*_LAYOUT_WIDE, *_LAYOUT_NARROW):
                    # Per-width isolation: without this guard one late failure
                    # unwound the whole loop and discarded every
                    # already-measured FAIL, reporting a genuinely broken bar
                    # as "could not evaluate" -- the same finding-masking class
                    # fixed per-project in _check_chain_completeness.
                    try:
                        page = browser.new_page(viewport={"width": width, "height": 900})
                        try:
                            page.goto(url, wait_until="networkidle", timeout=20000)
                            page.wait_for_timeout(250)
                            for fs in _LAYOUT_PRESSURES:
                                name = f"{fs}px"
                                page.evaluate(_LAYOUT_APPLY, fs)
                                page.wait_for_timeout(60)
                                m = page.evaluate(_LAYOUT_PROBE)
                                if not m:
                                    raw_findings.append(
                                        f"w={width} [{name}]: .cbstatus not found — "
                                        f"the bar did not render"
                                    )
                                    continue
                                # AFTER _check_layout_geometry(), not before.
                                # `measured` gates the OK message's "console
                                # bar edges held, no overlap" -- so counting a
                                # probe whose assertions never actually RAN
                                # asserted a clean grid over an evaluation
                                # that failed. An assertion pass raising at
                                # every width produced a confident OK
                                # alongside the per-width WARNs.
                                raw_findings += _check_layout_geometry(width, m, name)
                                measured += 1
                        finally:
                            # A page that fails to CLOSE is not a failed
                            # measurement. Left bare, a raising `page.close()`
                            # put a fully-measured width into `unmeasured` --
                            # so the gather emitted a spurious cannot-measure
                            # WARN alongside an OK reading "6 measurement(s):
                            # 3 width(s) x 2 steps; 3 width(s) could not be
                            # measured", counting every width in both lists.
                            # Its two sibling teardowns below were already
                            # suppressed for exactly this reason.
                            _suppress_close(page.close)
                    except (Exception, SystemExit) as exc:  # noqa: BLE001 --
                        # SystemExit: kept as defense-in-depth against
                        # playwright's own internals (a third-party library
                        # this function calls into, not code this module
                        # owns) rather than -- as before Story 6.9's fix --
                        # against a dynamically exec'd `check_layout.py`
                        # that no longer exists; KeyboardInterrupt stays out.
                        unmeasured.append(
                            f"w={width}: could not be measured — "
                            f"{exc.__class__.__name__}: {exc}"
                        )
                        continue
            finally:
                # Cleanup must not be able to DESTROY the verdict. Raising out
                # of these two `finally` blocks put every already-collected
                # FAIL back behind one whole-gather WARN -- the masking hole
                # the per-width guard above closes, reopened one frame up, and
                # reproduced live with a browser that dies on close.
                _suppress_close(browser.close)
    finally:
        # shutdown() only stops serve_forever's loop; without server_close()
        # the listening socket stays open, leaking one fd (and one held
        # ephemeral port) per call. Harmless in the one-shot CLI this was
        # ported from, unbounded in a long-lived library caller.
        _suppress_close(httpd.shutdown)
        _suppress_close(httpd.server_close)

    warns = tuple(_layout_warn(text, target)[0] for text in unmeasured)

    if not measured:
        # Nothing measured anywhere is the original's own UNKNOWN (its
        # `exit 2`), so WARN is right -- but the collected reasons ARE the
        # diagnosis. Returning only "the bar never rendered at any width"
        # discarded every one of them AND asserted a cause never observed:
        # when the page failed to LOAD, whether the bar would have rendered is
        # exactly what is unknown.
        detail = "; ".join([*unmeasured, *raw_findings]) or (
            "the bar never rendered at any width"
        )
        return _layout_warn(detail, target)

    if not raw_findings:
        message = (
            f"console bar edges held, no overlap — {measured} measurement(s): "
            f"{len(_LAYOUT_WIDE) + len(_LAYOUT_NARROW)} width(s) x "
            f"{len(_LAYOUT_PRESSURES)} font-pressure step(s)"
        )
        if unmeasured:
            # Never claim a clean grid that was not measured (this gather's
            # own headline contract).
            message += f"; {len(unmeasured)} width(s) could not be measured"
        return (
            *warns,
            Finding(
                source=Source.CHECK_LAYOUT,
                check=_LAYOUT_CHECK,
                status=DoctorStatus.OK,
                message=message,
                evidence={"measured": measured},
            ),
        )
    return (
        *warns,
        *(
            Finding(
                source=Source.CHECK_LAYOUT,
                check=_LAYOUT_CHECK,
                status=DoctorStatus.FAIL,
                message=finding_text,
                evidence={"measured": measured},
            )
            for finding_text in raw_findings
        ),
    )

