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

**One ``data.js`` reader remains.** ``_board_lines`` (used by
``gather_chain_completeness``) parses the committed file with a fixed-prefix strip.
It once had a sibling, ``_load_data_js``, which read the same file by regex for
``gather_dashboard_drift``; the two were deliberately NOT unified because that is
what their respective source scripts each did. *(2026-09-14: the sibling and the
whole retired-Guildhall helper island it belonged to were deleted -- provably
unreachable once the console retired. This note is kept because the reasoning still
governs ``_board_lines``: consolidating readers would
be a redesign this story's Boundaries explicitly rule out ("preserve, don't
redesign"); each stays exactly as strict or as lenient as its own original.
"""

from __future__ import annotations

import bisect
import http.server
import importlib.util
import json
import re
import sys
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

#: FALLBACK when `guild-roster.json`'s `spec_statuses`/`spec_statuses_terminal`
#: is unavailable -- today's value, not a parallel source of truth (Story
#: 59.2; mirrors `chain.py`'s own `_CONSTITUTIVE_FALLBACK`). Live INV-A calls
#: derive the same value fresh from `guild-roster.json` via
#: `_spec_status_groups` -- spec statuses that represent work still owed.
OPEN_SPEC_STATUSES = frozenset({"draft", "ready", "in-progress"})

#: FALLBACK (Story 59.2 -- see `OPEN_SPEC_STATUSES`'s own note) for the
#: terminal statuses that STILL owe a decomposition, and why `shipped` is the
#: only one (2026-09-14). INV-A originally skipped every non-OPEN status on the
#: reasoning that terminal work owes nothing -- true of the work, false of the
#: story trail. A `shipped` Spec whose CAPs were delivered with no epic and no
#: ledger row leaves the station under-reporting what it shipped, and the
#: dev/review loop, the retro triggers and the realization gate all key off
#: that trail. Found live by a fleet-wide audit: ten `shipped` Specs across
#: atlas/marshal/steward had zero epic anywhere (e.g.
#: spec-platform-image-one-pixi-env, whose three CAPs shipped 2026-08-25 and
#: were re-verified live 2026-09-11 -- retroactive Epic 57 documents them now).
#: The other four terminal statuses stay exempt for real reasons: `absorbed`
#: CAPs live in the absorbing chain's epic, `archived`/`superseded` were
#: abandoned rather than delivered, and `extension-point` is a standing seam,
#: not a deliverable. Precedent for the remedy: retroactive Epics 38/39/57.
DELIVERED_SPEC_STATUSES = frozenset({"shipped"})

#: FALLBACK (Story 59.2): every status INV-A inspects when degraded -- still-
#: owed work plus delivered-but-untracked.
DECOMPOSITION_OWED_STATUSES = OPEN_SPEC_STATUSES | DELIVERED_SPEC_STATUSES

#: `guild-roster.json`'s repo-relative path -- the CAP-1 declaration Story
#: 59.1 landed (mirrors `chain.py::_GUILD_ROSTER_REL`).
_GUILD_ROSTER_REL = Path("docs") / "governance" / "guild-roster.json"


def _spec_status_groups(target: Path) -> tuple[frozenset[str], frozenset[str], dict | None]:
    """INV-A's live open/delivered Spec-status sets, read fresh from
    ``guild-roster.json`` at ``target`` -- never cached at import time
    (``target`` is a runtime parameter; mirrors ``factory.py::_roster`` /
    ``chain.py::_load_dream_roster``, the house pattern for this package).

    ``open = spec_statuses - spec_statuses_terminal - {"extension-point"}``;
    ``delivered = spec_statuses_terminal - spec_statuses_ended_acts`` (yields
    exactly ``{"shipped"}`` for the declared values -- see
    ``DELIVERED_SPEC_STATUSES``'s own docstring for why only ``shipped``
    counts).

    On any read/parse/shape failure, degrades to ``OPEN_SPEC_STATUSES`` /
    ``DELIVERED_SPEC_STATUSES`` (never a crash) and returns a WARN
    finding-precursor dict -- the same shape ``_check_chain_completeness``'s
    own per-project degrade already uses -- for the caller to append to its
    own ``findings`` rather than degrading silently (Story 59.2, mirrors
    ``chain.py::_load_constitutive``).
    """
    rel = _GUILD_ROSTER_REL.as_posix()
    try:
        data = json.loads((target / _GUILD_ROSTER_REL).read_text(encoding="utf-8"))
        raw_spec_statuses = data["spec_statuses"]
        raw_terminal = data["spec_statuses_terminal"]
        raw_ended_acts = data["spec_statuses_ended_acts"]
        if not all(isinstance(v, list) for v in (raw_spec_statuses, raw_terminal, raw_ended_acts)):
            raise TypeError("spec_statuses/spec_statuses_terminal/spec_statuses_ended_acts must be lists")
        spec_statuses = frozenset(str(s) for s in raw_spec_statuses)
        terminal = frozenset(str(s) for s in raw_terminal)
        ended_acts = frozenset(str(s) for s in raw_ended_acts)
    except Exception as exc:  # noqa: BLE001 -- degrade, never crash (house rule)
        return (
            OPEN_SPEC_STATUSES,
            DELIVERED_SPEC_STATUSES,
            {
                "inv": "",
                "kind": "spec-status-roster-degraded",
                "project": "",
                "subject": rel,
                "status": "",
                "detail": (
                    f"{rel} could not be read for INV-A's Spec-status vocabulary "
                    f"({exc.__class__.__name__}: {exc}) — falling back to "
                    f"OPEN_SPEC_STATUSES/DELIVERED_SPEC_STATUSES"
                ),
                "remedy": f"restore {rel} so INV-A reads the live declaration",
                "warn": True,
            },
        )
    return (
        spec_statuses - terminal - {"extension-point"},
        terminal - ended_acts,
        None,
    )


#: Specs deliberately NOT decomposed, each with the reason it is exempt --
#: copied verbatim from scripts/chain_completeness_check.py so a station's
#: recorded exemption is not silently dropped by the port.
# NOTE (updated 2026-08-10): the former duplicate in `scripts/chain_completeness_check.py`
# is GONE — 6-9 landed (PR #394) and deleted the shim, so this dict is now the sole copy.
# Invariant: every slug here names a Spec whose `status:` is in OPEN_SPEC_STATUSES
# (`draft`, `ready`, `in-progress`). When a Spec reaches a terminal status, `:716`'s
# first clause exempts it anyway, so a DEFERRED_SPECS entry is never the only thing
# standing between a terminal Spec and a finding — remove stale entries rather than
# leaving them inert. An entry also leaves when its Spec is decomposed into the owning
# station's epics AND the operator confirms dispatch (precedent: spec-deferred-work-visibility,
# de-registered 2026-08-10 on explicit operator confirmation of doctor Epic 7).
DEFERRED_SPECS: dict[str, str] = {
    # `spec-agentic-sdlc-autonomy` was registered here as a standing non-deliverable.
    # De-registered 2026-09-18: Spec status is now `absorbed` (folded); an inert
    # DEFERRED_SPECS entry fails Story 21.1's live-status reconciliation.
    # `spec-build-league-scorecard` was registered here while Q5 had no numbers.
    # De-registered 2026-09-15: operator published eight already-counted
    # signals with on/off/archived config; Spec `ready`; steward Epic 62
    # (62.1–62.3) is the dispatch home. Do not invent weights.
    # `spec-work-passports-dated-extracts` was registered here 2026-09-14 as a
    # `draft` seed whose six open questions blocked decompose. De-registered
    # 2026-09-15: operator approved Q1–6; Spec `ready`; steward Epic 61
    # (61.1–61.5) is the dispatch home. Do not treat Epic 8 as this product.
    # `spec-coverage-gate-independence` was registered here 2026-09-14 (morning) as a `draft`
    # seed whose five open questions were unanswerable design decisions. De-registered the
    # same day: the operator ruled its home the Guild (Charter §5 amendment), so the Spec moved
    # to docs/governance/spec-coverage-gate-independence/ -- outside `pa.glob("specs/spec-*")`
    # above, exactly like spec-pyforge-charter -- and the mechanism stories live in doctor's
    # epics.md (Epic 24), where INV-A can see them.
    # `spec-golden-path-conda-blind-spot` was registered here 2026-09-05 while five
    # open questions gated CAP-1..5. De-registered 2026-09-16 (fleet-inbox-disposition):
    # those questions were answered 2026-09-09; warden Epic 12 cites CAP-1..5 and is
    # done. Do not mint Epic 13. Record:
    # `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-inbox-disposition-2026-09-16.md`.
    # `spec-bmad-cursor-interactive-routing` was registered here 2026-09-07 while
    # CAP-1 (live Cursor-chat subagent probe) had not run. De-registered
    # 2026-09-15: probe PASS on Cursor Agent + Task; CAP-2 committed; CAP-3
    # residual for no-Task surfaces; CAP-4 verified; marshal Epic 45 (45.1–45.3)
    # is the dispatch home. Do not treat this as full Ask-panel / all-skills
    # parity, and do not ship CAP-3a without its own evidence.
    "spec-pyforge-charter": "a constitutive Spec whose CAP-1/4/5/6/8 are document-integrity properties "
    "no story can pick up; CAP-3 mechanism shipped as doctor 21.4; CAP-7/AUT-3 "
    "wait on the Guildhall referent — do not mint a Charter epic",
    # `spec-token-economy-claude-session-path` was registered here 2026-09-16
    # (morning) as a `draft` seed whose three open questions were answered in its
    # memlog. De-registered the same day: the operator ruled no satellite Specs,
    # so the Spec folded into `spec-marshal-token-economy` as CAP-19..CAP-24
    # (status `superseded` — terminal, not owed) and marshal Epic 46 (46.1–46.10)
    # is the dispatch home. The folder stays as the decision record.
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
    body = spec_md_text[m.end() : nxt.start() if nxt else len(spec_md_text)]
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
    for nxt in lines[idx + 1 :]:
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


def _epic_numbers_from_epics(path: Path) -> set[int]:
    """Every ``N`` declared by a ``## Epic N`` heading.

    INV-B's story arm drops every ``epic-*`` key before comparing
    (``story_rows`` below), so until 2026-09-14 nothing checked that an
    ``epic-N`` ledger row had a heading, or the reverse. That is not
    bookkeeping: ``scripts/fleet_picture.py`` derives the fleet's headline
    epic counts from those same ledger keys, so a drifted key silently
    misreports fleet progress. Two live orphans when this landed —
    ``pyforge-steward`` ``epic-18`` and ``pyforge-marshal`` ``epic-29``,
    both with their stories present and correctly keyed but no ``## Epic N``
    heading, so the stories rendered under the preceding epic.

    Same read-failure contract as ``_story_ids_from_epics``: a broad
    ``except`` returning empty, so a non-UTF-8 byte cannot discard this
    project's own already-computed INV-A findings.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001 -- see _story_ids_from_epics
        return set()
    return {int(m.group(1)) for m in re.finditer(r"^##\s+Epic\s+(\d+)", text, re.MULTILINE)}


def _ledger_epic_numbers(rows: dict[str, str]) -> set[int]:
    """Every ``N`` from an ``epic-N`` key. ``epic-N-retrospective`` is
    deliberately NOT counted separately -- it is paired to its own
    ``epic-N`` and would double-report the same drift."""
    out: set[int] = set()
    for key in rows:
        m = re.fullmatch(r"epic-(\d+)", key)
        if m:
            out.add(int(m.group(1)))
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
        data = json.loads(text[len(_CHAIN_DATA_JS_PREFIX) :].rstrip().rstrip(";"))
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


def _check_chain_completeness(target: Path, board: dict[str, tuple[int, int]] | None) -> list[dict]:
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
            findings.append(
                {
                    # NOT "INV-A": this catch wraps the whole INV-A/B/C/D
                    # evaluation, so stamping one invariant would point an
                    # operator (or an --inv filter) at Spec decomposition when the
                    # broken input was, say, the ledger INV-B reads.
                    "inv": "",
                    "kind": "chain-completeness-unevaluable",
                    "project": project,
                    "subject": project,
                    "status": "",
                    "detail": (f"could not be evaluated here — {exc.__class__.__name__}: {exc}"),
                    "remedy": "fix the malformed/unreadable input, then re-check",
                    "warn": True,
                }
            )
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
        stripped_parts.append(text[heading.start() :] if heading else text)
    prose = "\n\n".join(stripped_parts)

    spec_paths = sorted(pa.glob("specs/spec-*/SPEC.md"))
    all_slugs = [p.parent.name for p in spec_paths]
    cited_by_spec = _cited_cap_ids_by_spec(prose, all_slugs)

    # Story 59.2: the live Spec-status vocabulary, read fresh from
    # `guild-roster.json` -- only when there is at least one Spec to classify
    # against it (`project_dir.parents[2]` is `target`: project_dir is
    # `target/_bmad-output/projects/<name>`). Gated on `spec_paths` rather
    # than called unconditionally so a project with zero Specs (pure
    # INV-B/C/D input) never pays for -- or risks degrading on -- a roster
    # read it has no use for.
    if spec_paths:
        open_statuses, delivered_statuses, roster_warning = _spec_status_groups(project_dir.parents[2])
        if roster_warning is not None:
            findings.append({**roster_warning, "project": project})
        decomposition_owed_statuses = open_statuses | delivered_statuses
    else:
        delivered_statuses = DELIVERED_SPEC_STATUSES
        decomposition_owed_statuses = DECOMPOSITION_OWED_STATUSES

    for spec_md in spec_paths:
        slug = spec_md.parent.name
        try:
            spec_text = spec_md.read_text(encoding="utf-8")
        except Exception:  # noqa: BLE001 -- an unreadable/non-UTF-8 SPEC.md
            # degrades to "no frontmatter, no declared CAP ids" here rather
            # than aborting this project's whole INV-A/B/C/D pass.
            spec_text = ""
        fm = _frontmatter_from_text(spec_text)
        if slug in DEFERRED_SPECS:
            continue
        if "status" not in fm:
            findings.append(
                {
                    "inv": "INV-A",
                    "kind": "spec-status-missing",
                    "project": project,
                    "subject": slug,
                    "status": "",
                    "detail": f"Spec {slug!r} has no status: in frontmatter",
                    "remedy": (f"add a status: line to {slug}, or add the slug to DEFERRED_SPECS with the reason"),
                }
            )
            continue
        status = str(fm.get("status", "")).strip()
        if status not in decomposition_owed_statuses:
            continue
        delivered = status in delivered_statuses

        declared = _parse_declared_cap_ids(spec_text)
        if delivered:
            # A delivered Spec is held to the WHOLE-SPEC standard only: does any
            # epic or FR reference it at all? Not the per-CAP citation standard
            # the OPEN branch below applies. Running per-CAP here flagged 34
            # Specs on first run against 12 real ones (2026-09-14) -- epics
            # written before the cite-every-CAP-id convention name the Spec or
            # its Dream without enumerating `CAP-n`, so per-CAP would report a
            # documentation-style gap as a missing story trail. Zero reference
            # is the unambiguous signal: the CAPs shipped and nothing records
            # who delivered them.
            bare = slug.removeprefix("spec-")
            owner_dream = str(fm.get("owner-dream", "")).strip()
            dream_stem = Path(owner_dream).stem if owner_dream else ""
            referenced = (
                slug in raw_prose
                or bare in raw_prose
                # an epic may claim a Spec by its Dream path instead of its slug
                # (Epic 51 <- platform-datastores-consumed-not-self-hosted), so
                # matching only `spec-<slug>` reports a false positive.
                or (bool(owner_dream) and owner_dream in raw_prose)
                or (bool(dream_stem) and f"{dream_stem}.md" in raw_prose)
            )
            if not referenced:
                findings.append(
                    {
                        "inv": "INV-A",
                        "kind": "delivered-spec-not-decomposed",
                        "project": project,
                        "subject": slug,
                        "status": status,
                        "detail": (
                            f"{station} shipped {slug} ({status}) and no FR or epic "
                            f"references it — its CAPs were delivered with no story "
                            f"trail, so the ledger under-reports what shipped"
                        ),
                        "remedy": (
                            f"mint a RETROACTIVE epic for {slug} in {project}'s "
                            f"epics.md documenting what already exists (stories at "
                            f"done, precedent: Epics 38/39/57) plus its ledger keys "
                            f"— never DEFERRED_SPECS, which is for undone work"
                        ),
                    }
                )
            continue

        if not declared:
            # Zero-CAP fallback: BYTE-IDENTICAL to the pre-this-story check,
            # against the FULL, unstripped `raw_prose` (Round 1's own
            # requirement -- see the block comment above).
            bare = slug.removeprefix("spec-")
            if bare not in raw_prose and slug not in raw_prose:
                findings.append(
                    {
                        "inv": "INV-A",
                        "kind": "spec-not-decomposed",
                        "project": project,
                        "subject": slug,
                        "status": status,
                        "detail": (
                            f"{station} owns an open Spec ({status}) that no FR or "
                            f"epic references — the station can render 100% while "
                            f"owing it"
                        ),
                        "remedy": (
                            f"decompose {slug} into {project}'s PRD + epics, or add "
                            f"it to DEFERRED_SPECS with the reason"
                        ),
                    }
                )
            continue

        uncovered = sorted(declared - cited_by_spec.get(slug, set()))
        if uncovered:
            missing = _format_cap_ids(uncovered)
            findings.append(
                {
                    "inv": "INV-A",
                    "kind": "spec-not-decomposed",
                    "project": project,
                    "subject": slug,
                    "status": status,
                    "detail": (
                        f"{station} owns an open Spec ({status}) with {missing} "
                        f"uncovered by any epic or FR — the station can render "
                        f"100% while owing them"
                    ),
                    "remedy": (
                        f"decompose {missing} of {slug} into {project}'s PRD + "
                        f"epics, or add {slug} to DEFERRED_SPECS with the reason "
                        f"(DEFERRED_SPECS remains available as a whole-Spec escape "
                        f"hatch)"
                    ),
                }
            )

    # ---- INV-B: epics.md set == ledger set ------------------------------------
    epics_md = _canonical_epics(project_dir)
    ledger = pa / "sprint-status-ledger.yaml"
    rows = _ledger_rows(ledger) if ledger.is_file() else {}
    story_rows = {k: v for k, v in rows.items() if not k.startswith("epic-")}
    led, unparsed = _ledger_story_ids(story_rows)

    if epics_md and unparsed:
        findings.append(
            {
                "inv": "INV-B",
                "kind": "unparseable-ledger-key",
                "project": project,
                "subject": f"{len(unparsed)} key(s)",
                "status": ", ".join(sorted(unparsed)[:6]),
                "detail": (
                    "no recognisable story id — reported rather than dropped, "
                    "because silently skipping a key is how a detector claims a "
                    "clean set it never compared"
                ),
                "remedy": "rename to <epic>-<seq>-… or <wave><n>-…, or retire the key",
            }
        )
    if epics_md and story_rows and not _story_ids_from_epics(epics_md):
        findings.append(
            {
                "inv": "INV-D",
                "kind": "canonical-epics-declares-no-stories",
                "project": project,
                "subject": epics_md.name,
                "status": f"0 `### Story` headings vs {len(story_rows)} ledger key(s)",
                "detail": (
                    "the canonical epics doc declares NO stories in the shape every "
                    "other station uses, so INV-B has nothing to compare and would "
                    "silently pass — an empty set trivially matches nothing"
                ),
                "remedy": ("rewrite as `## Epic N: Title` + `### Story <id>: Title`, covering every ledger story"),
            }
        )
    if epics_md and story_rows:
        ep_sets = _story_ids_from_epics(epics_md)
        ep_all = {i for s in ep_sets for i in s}
        if ep_sets and led:
            only_epics = sorted(next(iter(sorted(s))) for s in ep_sets if not (s & led))
            only_ledger = sorted(led - ep_all)
            if only_epics:
                findings.append(
                    {
                        "inv": "INV-B",
                        "kind": "story-without-ledger-key",
                        "project": project,
                        "subject": f"{len(only_epics)} story(ies)",
                        "status": ", ".join(only_epics[:10]),
                        "detail": (
                            "in epics.md with no ledger key — the board's percentage "
                            "is computed over a set that excludes them"
                        ),
                        "remedy": f"add them to {project}'s Tier-3 feed, then sprint-ledger-sync",
                    }
                )
            if only_ledger:
                findings.append(
                    {
                        "inv": "INV-B",
                        "kind": "ledger-key-without-story",
                        "project": project,
                        "subject": f"{len(only_ledger)} key(s)",
                        "status": ", ".join(only_ledger[:10]),
                        "detail": "in the ledger with no epics.md story — an untraceable row",
                        "remedy": f"add the story to {epics_md.name}, or retire the key",
                    }
                )

    # ---- INV-B (epic arm): `## Epic N` headings == `epic-N` ledger keys ------
    # Added 2026-09-14. The story arm above compares `### Story` ids only; every
    # `epic-*` key is dropped before it runs, so an epic row with no heading (or
    # a heading with no row) was unreachable by any detector while
    # `fleet_picture.py` counted the fleet's epics from those very keys.
    if epics_md and rows:
        ep_headings = _epic_numbers_from_epics(epics_md)
        ep_keys = _ledger_epic_numbers(rows)
        if ep_headings or ep_keys:
            heading_no_key = sorted(ep_headings - ep_keys)
            key_no_heading = sorted(ep_keys - ep_headings)
            if heading_no_key:
                findings.append(
                    {
                        "inv": "INV-B",
                        "kind": "epic-heading-without-ledger-key",
                        "project": project,
                        "subject": f"{len(heading_no_key)} epic(s)",
                        "status": ", ".join(f"Epic {n}" for n in heading_no_key[:10]),
                        "detail": (
                            f"{', '.join(f'Epic {n}' for n in heading_no_key[:10])} "
                            f"declared in {epics_md.name} with no `epic-N` ledger key — "
                            f"fleet-picture counts epics from the ledger, so this epic "
                            f"is invisible to the board"
                        ),
                        "remedy": "add the epic-N key to the ledger, or retire the heading",
                    }
                )
            if key_no_heading:
                findings.append(
                    {
                        "inv": "INV-B",
                        "kind": "ledger-epic-key-without-heading",
                        "project": project,
                        "subject": f"{len(key_no_heading)} key(s)",
                        "status": ", ".join(f"epic-{n}" for n in key_no_heading[:10]),
                        "detail": (
                            f"{', '.join(f'epic-{n}' for n in key_no_heading[:10])} "
                            f"in the ledger with no `## Epic N` heading in "
                            f"{epics_md.name} — its stories render under the preceding "
                            f"epic, and the board over-counts"
                        ),
                        "remedy": (
                            "write the missing `## Epic N:` heading above that epic's own stories, or retire the key"
                        ),
                    }
                )

    # ---- INV-C: board line == ledger ------------------------------------------
    if board is not None and station in board and story_rows:
        b_done, b_total = board[station]
        l_done = sum(1 for v in story_rows.values() if v == "done")
        if (b_total, b_done) != (len(story_rows), l_done):
            findings.append(
                {
                    "inv": "INV-C",
                    "kind": "board-diverges-from-ledger",
                    "project": project,
                    "subject": station,
                    "status": f"board {b_done}/{b_total} vs ledger {l_done}/{len(story_rows)}",
                    "detail": (
                        "the Guildhall renders a different story set than the "
                        "durable record; scan_projects only UPGRADES a curated "
                        "line, so this cannot self-heal"
                    ),
                    "remedy": "rebuild the station's data.js epics array from its ledger",
                }
            )


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
            f"project {project}: {name} checkpoint pass" if passed else f"project {project}: {name} checkpoint fail"
        ),
        evidence={
            "kind": check,
            "project": project,
            "checkpoint": name,
            "pass": passed,
            **detail,
        },
    )


def gather_chain_layers_audit(target: Path, project: str) -> tuple[Finding, ...]:
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


def _gather_chain_layers_audit(target: Path, project: str) -> tuple[Finding, ...]:
    try:
        gen = _load_dashboard_generate(target)
    except Exception as exc:  # noqa: BLE001 -- unevaluable, never crash
        return (
            Finding(
                source=Source.CHAIN_LAYERS_AUDIT,
                check="chain-layers-audit-unevaluable",
                status=DoctorStatus.WARN,
                message=(f"fleet_scan failed to load — chain layer audit cannot be evaluated ({exc})"),
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
                message=(f"project {project!r} has no planning-artifacts tree — chain layer audit cannot be evaluated"),
                evidence={
                    "kind": "chain-layers-audit-unevaluable",
                    "project": project,
                    "detail": "planning-artifacts missing",
                    "subject": str(Path("_bmad-output") / "projects" / project / "planning-artifacts"),
                },
            ),
        )

    applicable = [s for s in stages if s not in na]
    present = [s for s in applicable if layers[s]]
    missing = [s for s in applicable if not layers[s]]

    # CAP-3 coherence/staleness: reuse scan_fleet's live row for this project.
    fleet = gen.scan_fleet({}, None)
    fleet_row = next(
        (r for r in fleet.get("rows", []) if r.get("project") == project and r.get("slug") == project),
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
                message=(f"project {project!r} has no fleet chain row — CAP-3 audit cannot be evaluated"),
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
                f"present" + (f"; missing: {', '.join(missing)}" if missing else "")
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
        # tell the two apart. A since-deleted sibling, `_board_projects`,
        # refused exactly this coercion for `gather_dashboard_drift`, so the
        # same bytes produced a confident OK here and an honest WARN there --
        # which is why this guard exists and must stay.
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
    ``check_layout.py`` to reuse its assertions), but that origin file was
    deleted and its logic ported into this module as permanent code -- and
    that ported code was itself deleted on 2026-09-14, once the retired
    console made it unreachable. There is nothing left for it to load. This
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
      contract. The since-deleted ``_load_data_js`` made the same conversion
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


# --- the one surviving retired-Guildhall reader -------------------------------
#
# ``_load_dashboard_generate`` imports ``docs/dashboard/generate.py``, which is
# gone -- and ``retired-console-check`` FAILS CI if it returns. So this body can
# only execute in a state the estate forbids, and its sole caller
# (``_gather_chain_layers_audit``) catches the failure and degrades to an
# honest unevaluable Finding, which IS covered.
#
# It keeps ``# pragma: no cover`` for that reason, not for convenience: it is
# reachable code whose reachable path is closed by policy rather than by
# structure, so a test could only assert the failure branch its caller already
# covers. Everything ELSE that carried this pragma on 2026-09-14 -- the layout
# orchestration island and the dashboard-drift helper island, 494 lines across
# ten functions and ten constants -- had no live caller at all and was deleted
# outright the same day (DW-DASHBOARD-DEAD-CODE-1). That deletion moved this
# module from 72% to 95% on real code, with findings byte-identical before and
# after.
#
# Worth recording, because the ledger entry had it wrong: deleting that code
# was NOT "a behaviour change to two registered detector sources plus their
# taxonomy and schema entries". An AST call-graph pass showed the islands were
# private orphans -- both gathers, their DISPATCH entries, their ``Source``
# members and ``report-schema.json`` were untouched. The scope was over-stated
# when the entry was written, which is why it had been deferred as needing its
# own Dream when it was in fact hygiene.


def _load_dashboard_generate(target: Path):  # pragma: no cover -- retired Guildhall console; see _RETIRED_CONSOLE_FILES
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
        raise RuntimeError(f"a dynamically loaded file called sys.exit({exc.code!r}) at call time") from exc


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
            message=("Guildhall generator, data.js, and the four dashboard pixi tasks stay gone"),
            evidence={"retired": True},
        ),
    )


# === gather_check_layout =====================================================
#
# This section once held a full browser-driven layout gate, ported from
# docs/dashboard/check_layout.py: it launched chromium over a served
# docs/dashboard/, measured the Guildhall console bar at five widths x five
# font-pressures, and kept "could not measure" and "measured, and it is broken"
# on deliberately separate verdicts. See that origin script's own module
# docstring, and this file's git history, for the rationale and the two live
# incidents behind it (a broken status chip surviving three green gates; the
# fix for it trading one visual bug for another).
#
# DELETED 2026-09-14 (DW-DASHBOARD-DEAD-CODE-1). The Guildhall console retired;
# docs/dashboard/{generate.py,data.js,index.html} are gone and
# `retired-console-check` FAILS CI if any returns. `gather_check_layout` below
# had already been reduced to a pure retirement assertion -- FAIL if a retired
# path reappears, OK otherwise -- and an AST call-graph pass proved the whole
# orchestration island beneath it (`_run_check_layout`, `_serve_layout_dir`,
# `_check_layout_geometry`, `_layout_chip_rows`, `_suppress_close` and the ten
# `_LAYOUT_*` probe constants) had NO live caller at all: `_run_check_layout`
# was called by nothing, and everything else only by it. The same pass found a
# second orphan island on the dashboard-drift side (`_check_dashboard_drift` ->
# `_check_project_dashboard_drift` -> `_drift_epics_md_ids`, plus `_load_data_js`
# and `_board_projects`), deleted with it -- 494 lines, zero behaviour change,
# verified by byte-comparing this module's `--json` findings before and after.
#
# Nothing registered was touched: both gathers, their DISPATCH entries, their
# `Source` members and `report-schema.json` are unchanged. Only `_LAYOUT_CHECK`
# survives here, because the live gather still emits it as the check name.
#
# If the console is ever revived, this is a rewrite against whatever replaces
# it, not a revert -- the deleted code measured a bar that no longer exists.

_LAYOUT_CHECK = "console-bar-layout"

# --- ported verbatim from docs/dashboard/check_layout.py's own module-level
# constants (see that script's history, recoverable via
# `git show HEAD~1:docs/dashboard/check_layout.py` after this story's
# deletion commit) -- values and comments carried unchanged.

# Widths above the 720px collapse breakpoint, where the three-column grid is
# live and all four assertions apply; plus one below it, where stacking is the
# designed behaviour and only no-overlap/in-bounds are meaningful.
# demand -- carried verbatim; unused in the origin too (dead there already,
# not a porting artifact).

# Chips inside the status row. `#chip-gen` deliberately excluded -- it lives in
# `.cbrow` now, and treating it as a row member made the gate report a phantom
# "bar wrapped to 2 rows" (the two elements are in different containers, at the
# same one-line bar height of 34px).

# Font sizes in px applied to `.cchip`. 11 is the design size; the rest simulate
# a wider font face or a zoomed browser, which is how the operator hits at 11px
# what a runner does not. Above 11 the bar is EXPECTED to grow taller as the
# outer chips wrap -- that is the correct degradation -- so the one-row assertion
# is scoped to the design size only. Centring and non-overlap must hold at ALL
# sizes; they are the invariants.


class _LayoutQuietHandler(http.server.SimpleHTTPRequestHandler):
    """SimpleHTTPRequestHandler logs every GET to stderr, which buries the one
    line a detector is supposed to emit. A gate's output is its whole product.

    Ported verbatim from the origin's own ``_QuietHandler``; renamed only to
    keep this module's ``_Layout*``/``_layout_*`` prefix consistent now that
    it lives beside ``board.py``'s other sources."""

    def log_message(self, *_args):  # noqa: D102
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
