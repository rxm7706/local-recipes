"""Tier-3 follow-up-deferral promotion (Story 4.13, FR-175) -- the pure
core ``cli/land.py``'s ``marshal land`` delegates to for turning bmad-loop's
own follow-up-review damping safety valve into a tracked, durable ledger
entry at the moment a story lands. Mirrors ``core/promotion.py``'s exact
pure/impure split (AD-4, that module's own precedent): no I/O, no
``pathlib``, no subprocess, no clock, no ``..adapters`` import -- every
impure edge (reading the Tier-3/tracked files, the advisory lock, the
commit, the journal write) lives entirely in ``cli/land.py``.

**What gets promoted.** When ``limits.max_followup_reviews`` is spent while
a review still recommends an independent follow-up, bmad-loop force-
converges and writes a block shaped exactly::

    ### DW-<n>: Follow-up review still recommended for <story> after the
    damping cap was spent
    origin: review-budget-followup
    source_spec: `spec-<story>.md`
    severity: low
    reason: ...
    status: open

into the gitignored ``implementation-artifacts/deferred-work.md`` (Tier-3).
This is the ONLY shape ``scripts/deferred_work_check.py`` can ever flag as
``tier3-only-deferral`` with a real id to collide -- the file's other,
anonymous ``- source_spec: ...`` bullets carry no id at all.

**The DW-6 parsing gotcha.** A field line is recognized ONLY at column 0
(``^(?:origin|source_spec|severity|reason|status):``, unanchored by
stripped leading whitespace) -- never "read N lines after the heading".
The live Tier-3 file's own ``DW-6`` block (``implementation-artifacts/
deferred-work.md``) has its ``status: open`` line separated from
``origin:``/``source_spec:``/``severity:``/``reason:`` by several
INDENTED (2+ space) anonymous bullets (``  summary:``, ``  evidence:``, even
a ``  status:``) belonging to unrelated, un-id'd findings that got appended
into the same file in between -- a naive "read the next 5 lines" parser
would collect the wrong values entirely. ``parse_followup_deferrals`` scans
forward from each ``### DW-<n>:`` heading to the next heading (or end of
text), collecting only column-0 field lines, and requires all five before
treating the block as a candidate.

**The promoted id.** ``DW-FU-<epic>-<seq><suffix>`` (``promoted_id``, via
``core.identity.render_filename_slug``) -- no numeric counter, the
convention already live across every prior promotion in this ledger and in
warden's/doctor's own ledgers (at most one ``review-budget-followup`` entry
has ever existed per story). The story key itself is parsed from the
block's own ``source_spec:`` field (backticks and the ``spec-``/``.md``
wrapping stripped, then ``core.identity.normalize`` -- mirrors ``cli/
deploy.py::_discover_candidates``'s identical ``raw_key = spec_path.stem
[len("spec-"):]`` -> ``identity.normalize(raw_key)`` pattern), never from
the heading's own free-text title.

**Idempotency.** ``deferrals_to_promote`` filters to candidates whose story
is in the landing set AND whose ``promoted_id`` does not already appear as
a COMPLETE token ANYWHERE in the tracked ledger's own text
(``_tracked_promoted_ids``) -- a GREEDY tokenizer, never a bare substring
test (review finding, 2026-08-10: ``"DW-FU-1-1" in text`` is a false
positive the moment the text also carries ``"DW-FU-1-10"``, and this exact
epic/seq collision already exists live -- story 1.10 alongside the
already-promoted ``DW-FU-1-1``). Mirrors
``scripts/deferred_work_check.py``'s own ``_DW_RE`` tokenize-then-compare
convention, scoped to the ``DW-FU-`` prefix. ``render_ledger_entry``'s
``promoted:`` line separately repeats the bare Tier-3 id (``DW-<n>``)
verbatim, giving that detector's OWN (differently-scoped) regex something
to find too."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .identity import MalformedStoryKeyError, StoryKey, normalize, render_filename_slug

_ORIGIN_VALUE = "review-budget-followup"

# A `### DW-<n>: <title>` heading -- the only Tier-3 shape this module
# recognizes as a promotion candidate at all (see module docstring).
_HEADING_RE = re.compile(r"^### (?P<tier3_id>DW-\d+): (?P<title>.+)$", re.MULTILINE)

# Any markdown heading, of any level -- the block-boundary marker a scan
# stops at (the next `### DW-<n>:` heading, or any other heading in the
# file). Searched starting AFTER the current heading's own line, so it never
# matches that same line.
_NEXT_HEADING_RE = re.compile(r"^#{1,6} ", re.MULTILINE)

# A field line anchored at column 0 (unstripped `^`) -- the DW-6 gotcha's
# own fix: an indented `  status:`/`  summary:`/`  evidence:` belonging to an
# unrelated anonymous bullet never matches this, only a real top-level field.
_FIELD_RE = re.compile(
    r"^(?P<field>origin|source_spec|severity|reason|status):[ \t]*(?P<value>.*)$",
    re.MULTILINE,
)
_REQUIRED_FIELDS = ("origin", "source_spec", "severity", "reason", "status")

# The idempotency check's own tokenizer (review finding, 2026-08-10):
# mirrors ``scripts/deferred_work_check.py``'s own ``_DW_RE`` convention --
# a GREEDY match over every id character, never a bare substring test. A
# plain ``promoted_id(...) in tracked_text`` is unsafe: one promoted id can
# be a literal string-PREFIX of another (``"DW-FU-1-1"`` is a substring of
# ``"DW-FU-1-10"``, and this repo already has both an epic/seq shape that
# collides this way -- story 1.10 alongside the already-promoted
# ``DW-FU-1-1`` -- and a growing epic 4 with 4-1.. 4-13). ``\b`` anchors the
# LEFT edge; the greedy ``[A-Za-z0-9-]+`` class consumes every further
# digit/letter/hyphen, so ``"DW-FU-1-10"`` always tokenizes as ONE complete
# token distinct from ``"DW-FU-1-1"``, never truncated at a shorter id's
# own length the way a substring search would be.
_PROMOTED_ID_TOKEN_RE = re.compile(r"\bDW-FU-[A-Za-z0-9-]+")


def _tracked_promoted_ids(tracked_text: str) -> frozenset[str]:
    """Every complete ``DW-FU-<story>`` token already present in
    ``tracked_text`` (``deferrals_to_promote``'s own idempotency source of
    truth) -- trailing separators stripped, mirroring
    ``scripts/deferred_work_check.py::_ids``'s identical ``rstrip("-")``
    (a token like this module's own rendered ``` `DW-FU-<story>` ``` prose
    literal never matches at all: ``<`` is not in the token's character
    class, so the regex simply does not match there -- nothing to strip in
    that case)."""
    return frozenset(match.group(0).rstrip("-") for match in _PROMOTED_ID_TOKEN_RE.finditer(tracked_text))


@dataclass(frozen=True)
class DeferralCandidate:
    """One Tier-3 ``review-budget-followup`` block, parsed (Story 4.13):
    ``tier3_id`` (the bare ``"DW-<n>"`` id, e.g. ``"DW-8"``), ``story_key``
    (parsed from the block's own ``source_spec:`` field), ``title`` (the
    heading's own free text after ``"DW-<n>: "`` -- reused verbatim as the
    promoted entry's own heading title and ``summary:`` field),
    ``source_spec`` (the bare filename, backticks stripped), ``severity``,
    ``reason`` (becomes the promoted entry's ``evidence:`` field verbatim),
    and ``status``."""

    tier3_id: str
    story_key: StoryKey
    title: str
    source_spec: str
    severity: str
    reason: str
    status: str


def parse_followup_deferrals(text: str) -> tuple[DeferralCandidate, ...]:
    """Every well-formed ``review-budget-followup`` block in ``text``
    (Story 4.13): scans each ``### DW-<n>: <title>`` heading forward to the
    next heading (or end of text -- see module docstring for the DW-6
    interleaved-anonymous-bullet shape this guards against), collects the
    five column-0 field lines it finds along the way, and yields a
    ``DeferralCandidate`` only when all five are present AND ``origin``
    equals ``"review-budget-followup"`` -- any other ``origin`` value (a
    hypothetical future Tier-3 shape) is silently ignored, never raised.
    A ``source_spec:`` field that does not parse to a story key
    (``core.identity.normalize``'s ``MalformedStoryKeyError``) likewise
    silently drops that one block rather than aborting the whole scan --
    consistent with this package's "a subject/entry that doesn't conform is
    skipped, never a hard failure" convention (``core/promotion.py``'s own
    ``merged_story_keys``)."""
    candidates: list[DeferralCandidate] = []
    for heading in _HEADING_RE.finditer(text):
        next_heading = _NEXT_HEADING_RE.search(text, heading.end())
        block_end = next_heading.start() if next_heading is not None else len(text)
        block = text[heading.end() : block_end]

        fields: dict[str, str] = {}
        for field_match in _FIELD_RE.finditer(block):
            name = field_match.group("field")
            if name not in fields:
                fields[name] = field_match.group("value").strip()

        if any(name not in fields for name in _REQUIRED_FIELDS):
            continue
        if fields["origin"] != _ORIGIN_VALUE:
            continue

        raw_key = fields["source_spec"].strip("`").strip()
        if raw_key.startswith("spec-"):
            raw_key = raw_key[len("spec-") :]
        if raw_key.endswith(".md"):
            raw_key = raw_key[: -len(".md")]
        try:
            story_key = normalize(raw_key)
        except MalformedStoryKeyError:
            continue

        candidates.append(
            DeferralCandidate(
                tier3_id=heading.group("tier3_id"),
                story_key=story_key,
                title=heading.group("title").strip(),
                source_spec=fields["source_spec"].strip("`").strip(),
                severity=fields["severity"],
                reason=fields["reason"],
                status=fields["status"],
            )
        )
    return tuple(candidates)


def promoted_id(story_key: StoryKey) -> str:
    """The ledger's own promoted-id form: ``DW-FU-<epic>-<seq><suffix>``, no
    numeric counter (see module docstring for why -- the convention already
    live across this ledger and warden's/doctor's own)."""
    return f"DW-FU-{render_filename_slug(story_key)}"


def render_ledger_entry(candidate: DeferralCandidate, *, promoted_date: str) -> str:
    """The tracked ledger's own entry text for ``candidate`` (Story 4.13):
    the exact ``### DW-FU-<story>: <title>`` heading plus bulleted
    ``source_spec:``/``summary:``/``evidence:``/``promoted:``/``severity:``/
    ``status:`` shape already established by every prior (hand-)promoted
    entry in this ledger (``DW-FU-1-1`` .. ``DW-FU-3-5``). ``summary:``
    repeats the heading's own title verbatim (matching every existing
    entry); ``evidence:`` is the Tier-3 block's own ``reason:`` field
    verbatim. The ``promoted:`` line deliberately repeats the bare Tier-3
    id (``candidate.tier3_id``) TWICE, in prose -- the same substring
    ``scripts/deferred_work_check.py`` looks for to confirm the Tier-3 id
    now has a tracked twin. Returns text ending in exactly one trailing
    newline; the caller decides blank-line separation from whatever
    precedes it in the ledger file."""
    new_id = promoted_id(candidate.story_key)
    lines = [
        f"### {new_id}: {candidate.title}",
        "",
        f"- source_spec: `{candidate.source_spec}`",
        f"  summary: {candidate.title}",
        f"  evidence: {candidate.reason}",
        (
            f"  promoted: {promoted_date} — promoted from Tier-3 "
            "`implementation-artifacts/deferred-work.md` "
            f"(id `{candidate.tier3_id}` there) under the ledger's "
            "`DW-FU-<story>` convention, so the next damped story cannot "
            f"collide with a generic `{candidate.tier3_id}`."
        ),
        f"  severity: {candidate.severity}",
        f"  status: {candidate.status}",
    ]
    return "\n".join(lines) + "\n"


def deferrals_to_promote(
    candidates: tuple[DeferralCandidate, ...],
    landing_keys: frozenset[StoryKey],
    tracked_text: str,
) -> tuple[DeferralCandidate, ...]:
    """Which of ``candidates`` should be promoted THIS run (Story 4.13):
    ``story_key in landing_keys`` (only a story confirmed landed this
    invocation is in scope -- never a merely-open one) AND
    ``promoted_id(story_key)`` does not already appear as a COMPLETE token
    in ``tracked_text`` (idempotent -- a re-run against an already-promoted
    ledger yields the empty tuple). Boundary-aware via ``_tracked_promoted_
    ids`` (review finding, 2026-08-10) -- never a bare ``in`` substring
    test, which would false-positive whenever one promoted id is a literal
    string-prefix of another (``"DW-FU-1-1"`` is a substring of
    ``"DW-FU-1-10"``). Order follows ``candidates``' own input order;
    callers that need a deterministic order should pass already-sorted
    candidates.

    A SECOND candidate that resolves to the SAME ``promoted_id`` as one
    already selected earlier in this same call is also skipped (review
    finding, 2026-08-10) -- the first, by ``candidates``' own input order,
    wins; never two ``### DW-FU-<story>:`` headings with the identical id
    in one write. The dropped one stays visible to
    ``scripts/deferred_work_check.py`` as its own un-promoted Tier-3 id
    (the same manual-promotion fallback this convention already relies on
    for the undocumented, never-yet-observed case of two distinct
    ``review-budget-followup`` deferrals for one story)."""
    tracked_ids = _tracked_promoted_ids(tracked_text)
    seen: set[str] = set()
    result: list[DeferralCandidate] = []
    for candidate in candidates:
        if candidate.story_key not in landing_keys:
            continue
        pid = promoted_id(candidate.story_key)
        if pid in tracked_ids or pid in seen:
            continue
        seen.add(pid)
        result.append(candidate)
    return tuple(result)
