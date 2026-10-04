"""Dispatch session landing eligibility (Story 22.4, FR-193 CAP-4).

Pure functions only: verification outcome and git facts judge whether a
dispatched story may land via existing Epic 4 machinery. Never land on
self-report without passing independent verification (Story 22.3).
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping
from enum import StrEnum

from . import promotion
from .dispatch_verification import DispatchVerificationVerdict
from .model import Severity


class DispatchLandingVerdict(StrEnum):
    """Landing outcome for a verified dispatch session (CAP-4)."""

    LANDED = "landed"
    REFUSED = "refused"
    ALREADY_LANDED = "already_landed"
    SKIPPED_UNVERIFIED = "skipped-unverified"


def may_attempt_dispatch_landing(
    verification_verdict: DispatchVerificationVerdict,
    *,
    story_merged_on_main: bool,
) -> bool:
    """True when independent verification passed and the story is not yet on main."""
    return verification_verdict == DispatchVerificationVerdict.VERIFIED and not story_merged_on_main


def refuse_unverified_landing(
    verification_verdict: DispatchVerificationVerdict,
) -> bool:
    """True when landing must be refused because verification did not pass."""
    return verification_verdict != DispatchVerificationVerdict.VERIFIED


def merge_subject_is_marshal_native(subject: str, template: str, project_slug: str) -> bool:
    """True when ``subject`` classifies marshal-native (FR-187 / Story 5.10)."""
    return bool(promotion.marshal_native_merged_keys((subject,), template, project_slug))


def landing_was_refused(landing_findings: tuple[Mapping[str, object], ...]) -> bool:
    """True when a dispatch landing's journaled findings include a refusal:
    an ERROR-severity finding. A WARN-only landing (MRS-DISP-047) is not a
    refusal (Story 56.1)."""
    return any(finding.get("severity") == Severity.ERROR for finding in landing_findings)


def landing_refusal_superseded(
    landing_findings: tuple[Mapping[str, object], ...],
    *,
    story_merged_on_main: bool,
) -> bool:
    """True when a dispatch landing was refused and its story has since
    landed on ``main`` by another route (Story 56.1, CAP-266).

    The refusal stays the journal's process fact (AD-5); this reports git's
    repository fact beside it (AD-33), never in place of it."""
    return story_merged_on_main and landing_was_refused(landing_findings)


# --- Story 28.20 (CAP-4): mechanical land-conflict union -----------------

_LEDGER_STATUS_RANK: dict[str, int] = {
    "done": 100,
    "in-progress": 50,
    "review": 50,
    "ready-for-dev": 40,
    "ready": 40,
    "backlog": 10,
    "blocked": 5,
}

SPRINT_LEDGER_BASENAME = "sprint-status-ledger.yaml"


def sprint_ledger_rel_path(project_slug: str) -> str:
    """Repo-relative path to a project's tracked sprint-status ledger."""
    return f"_bmad-output/projects/{project_slug}/planning-artifacts/{SPRINT_LEDGER_BASENAME}"


def ledger_status_precedence(left: str, right: str) -> str:
    """Return the higher-precedence ledger status (`done` beats `backlog`)."""
    left_rank = _LEDGER_STATUS_RANK.get(left.strip().lower(), 20)
    right_rank = _LEDGER_STATUS_RANK.get(right.strip().lower(), 20)
    return left if left_rank >= right_rank else right


def union_sprint_ledger_maps(*maps: dict[str, str]) -> dict[str, str]:
    """Union ledger key maps; ``done`` beats ``backlog`` on collisions."""
    merged: dict[str, str] = {}
    for status_map in maps:
        for key, status in status_map.items():
            if key in merged:
                merged[key] = ledger_status_precedence(merged[key], status)
            else:
                merged[key] = status
    return merged


def three_way_ledger_statuses(
    base: Mapping[str, str],
    main: Mapping[str, str],
    branch: Mapping[str, str],
) -> dict[str, str]:
    """Story 59.1 review: resolve two ledger maps against their merge base, row by row. A row
    only one side changed (added, re-statused or removed) takes that side; a row both sides
    changed alike takes it; a row one side removed and the other re-statused is kept; a row both
    re-statused differently takes ``done`` if either side finished it (``done`` never regresses
    -- ``ledger-regression`` reds that, and ``promote_sprint_status`` ranks ``done`` strictly
    senior to ``blocked``), else ``blocked`` if either side set it (un-blocking is the
    operator's, never a mechanical merge's -- AGENTS.md), else ``ledger_status_precedence``.
    A two-way union resurrected retired rows and undid the base's own changes."""
    out: dict[str, str] = {}
    for key in sorted(set(base) | set(main) | set(branch)):
        was, ours, theirs = base.get(key), main.get(key), branch.get(key)
        if ours == theirs:
            value = ours
        elif ours == was:
            value = theirs
        elif theirs == was:
            value = ours
        elif ours is None or theirs is None:
            value = ours if ours is not None else theirs
        elif "done" in (ours, theirs):
            value = "done"
        elif "blocked" in (ours, theirs):
            value = "blocked"
        else:
            value = ledger_status_precedence(ours, theirs)
        if value is not None:
            out[key] = value
    return out


MEMLOG_BASENAME = ".memlog.md"
DEFERRED_WORK_BASENAME = "deferred-work-ledger.md"
TEAM_MEMORY_INDEX_REL = ".claude/memory/MEMORY.md"


def is_memlog_path(path: str) -> bool:
    """True when ``path`` is a Spec memlog: its basename is ``.memlog.md``, in any project --
    co-governor memlogs live under other projects, and an append-only union is safe wherever
    the file sits (Story 78.1, CAP-283)."""
    return path.replace("\\", "/").rsplit("/", 1)[-1] == MEMLOG_BASENAME


def is_deferred_work_path(path: str) -> bool:
    """True when ``path`` is a deferred-work ledger: its basename is ``deferred-work-ledger.md``."""
    return path.replace("\\", "/").rsplit("/", 1)[-1] == DEFERRED_WORK_BASENAME


def is_team_memory_index_path(path: str) -> bool:
    """True when ``path`` is the checked-in team-memory index (Story 83.11)."""
    return path.replace("\\", "/") == TEAM_MEMORY_INDEX_REL


def is_mechanical_conflict_path(
    path: str, *, ledger_rel: str | None = None, deferred_work_rel: str | None = None
) -> bool:
    """True when ``path`` is a known mechanical-only merge conflict: a Spec memlog (Story 78.1;
    the heal still escalates one that is not append-only), a sprint ledger, a deferred-work
    ledger (Story 83.3), or ``.claude/memory/MEMORY.md`` (Story 83.11). Given ``ledger_rel``
    (the landing project's own ledger), only that exact path is a mechanical ledger -- another
    project's ledger is not this landing's to resolve (Story 59.1). Similarly for
    ``deferred_work_rel`` - only the project's own deferred work ledger."""
    normalized = path.replace("\\", "/")
    if is_team_memory_index_path(normalized):
        return True
    if is_memlog_path(normalized):
        return True
    if ledger_rel is not None and normalized == ledger_rel:
        return True
    if deferred_work_rel is not None and normalized == deferred_work_rel:
        return True
    # Legacy fallback for when no specific paths provided
    if ledger_rel is None and deferred_work_rel is None:
        return (
            normalized.endswith(f"planning-artifacts/{SPRINT_LEDGER_BASENAME}")
            or normalized.endswith(SPRINT_LEDGER_BASENAME)
            or normalized.endswith(f"planning-artifacts/{DEFERRED_WORK_BASENAME}")
            or normalized.endswith(DEFERRED_WORK_BASENAME)
        )
    return False


def unknown_conflict_paths(
    paths: tuple[str, ...], *, ledger_rel: str | None = None, deferred_work_rel: str | None = None
) -> tuple[str, ...]:
    """Conflict paths that are not mechanical — must escalate, never merge."""
    return tuple(
        sorted(
            p
            for p in paths
            if not is_mechanical_conflict_path(p, ledger_rel=ledger_rel, deferred_work_rel=deferred_work_rel)
        )
    )


# --- Story 78.1 (CAP-283): append-only memlog union ------------------------

_FENCE = "---"


def _split_memlog(text: str) -> tuple[dict[str, str], list[str]] | None:
    """``_bmad/scripts/memlog.py``'s ``split``: the ``key: value`` frontmatter fields in source
    order, then the body's lines -- or ``None`` when ``text`` has no terminated ``---`` frontmatter.
    Mirrored, not imported: that script sits outside this package."""
    lines = text.splitlines()
    if not lines or lines[0] != _FENCE:
        return None
    end = next((i for i in range(1, len(lines)) if lines[i] == _FENCE), None)
    if end is None:
        return None
    fields: dict[str, str] = {}
    for line in lines[1:end]:
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    body = "\n".join(lines[end + 1 :]).lstrip("\n")
    return fields, body.rstrip("\n").splitlines()


def _render_memlog(fields: Mapping[str, str], body: list[str]) -> str:
    """``_bmad/scripts/memlog.py``'s ``render``: fence, fields, fence, a blank line, the body,
    one trailing newline."""
    frontmatter = "\n".join(f"{key}: {value}" for key, value in fields.items())
    return f"{_FENCE}\n{frontmatter}\n{_FENCE}\n\n" + "\n".join(body).rstrip("\n") + "\n"


def _union_memlog_fields(
    base: Mapping[str, str], main: Mapping[str, str], branch: Mapping[str, str]
) -> dict[str, str] | None:
    """Three-way merge of memlog frontmatter fields, in ``main``'s order: a field only one side
    changed takes that side's value (a removal is a change), ``updated`` takes the later stamp
    (ISO text compares correctly), and any other field both sides changed differently is
    ``None``. A field only the branch added lands before ``updated``, which ``memlog.py`` keeps
    last."""
    order = list(main)
    for key in branch:
        if key not in main:
            order.insert(order.index("updated") if "updated" in order else len(order), key)
    merged: dict[str, str] = {}
    for key in order:
        was, ours, theirs = base.get(key), main.get(key), branch.get(key)
        if key == "updated":
            value: str | None = max(stamp for stamp in (ours, theirs) if stamp is not None)
        elif ours == theirs or theirs == was:
            value = ours
        elif ours == was:
            value = theirs
        else:
            return None
        if value is not None:
            merged[key] = value
    return merged


def union_memlog_texts(base: str, main: str, branch: str) -> str | None:
    """Story 78.1 (CAP-283): the union of two append-only edits of one ``.memlog.md``, or ``None``
    when either side is not append-only or the frontmatter cannot be merged (the heal then
    escalates the path by name).

    Each text is parsed the way ``memlog.py`` writes it. A side is append-only when its body
    starts with the base body, line for line -- a rewritten, dropped or reordered line is not.
    The result body is ``main``'s, then each line the branch appended after the base, in order,
    skipping one line per identical line ``main`` appended (so an entry both sides appended
    appears once, in ``main``'s position, while an entry repeated on purpose is never dropped).
    Frontmatter is ``_union_memlog_fields``. Rendered in ``memlog.py``'s shape."""
    base_parts, main_parts, branch_parts = _split_memlog(base), _split_memlog(main), _split_memlog(branch)
    if base_parts is None or main_parts is None or branch_parts is None:
        return None
    base_fields, base_body = base_parts
    main_fields, main_body = main_parts
    branch_fields, branch_body = branch_parts
    kept = len(base_body)
    if main_body[:kept] != base_body or branch_body[:kept] != base_body:
        return None
    fields = _union_memlog_fields(base_fields, main_fields, branch_fields)
    if fields is None:
        return None
    already_on_main = Counter(main_body[kept:])
    appended: list[str] = []
    for line in branch_body[kept:]:
        if already_on_main[line] > 0:
            already_on_main[line] -= 1
        else:
            appended.append(line)
    return _render_memlog(fields, main_body + appended)


def _rstrip_blank_tail(lines: list[str]) -> list[str]:
    """Drop trailing empty lines -- ``scribe capture`` rebuilds section bodies without them."""
    end = len(lines)
    while end > 0 and not lines[end - 1].strip():
        end -= 1
    return lines[:end]


def _union_appended_line_lists(base_body: list[str], main_body: list[str], branch_body: list[str]) -> list[str] | None:
    """Append-only union of three line lists (memlog body or a MEMORY.md section body)."""
    base_body = _rstrip_blank_tail(base_body)
    main_body = _rstrip_blank_tail(main_body)
    branch_body = _rstrip_blank_tail(branch_body)
    kept = len(base_body)
    if main_body[:kept] != base_body or branch_body[:kept] != base_body:
        return None
    already_on_main = Counter(main_body[kept:])
    appended: list[str] = []
    for line in branch_body[kept:]:
        if already_on_main[line] > 0:
            already_on_main[line] -= 1
        else:
            appended.append(line)
    return main_body + appended


def _parse_team_memory_index(text: str) -> tuple[list[str], list[tuple[str, list[str]]]] | None:
    """Preamble lines before the first ``## `` heading, then ordered ``(heading, body lines)``."""
    lines = text.splitlines()
    first_h2 = next((i for i, line in enumerate(lines) if line.startswith("## ")), len(lines))
    preamble = lines[:first_h2]
    sections: list[tuple[str, list[str]]] = []
    index = first_h2
    while index < len(lines):
        line = lines[index]
        if not line.startswith("## "):
            return None
        heading = line[3:].strip()
        index += 1
        body: list[str] = []
        while index < len(lines) and not lines[index].startswith("## "):
            body.append(lines[index])
            index += 1
        sections.append((heading, body))
    return preamble, sections


def _render_team_memory_index(preamble: list[str], sections: list[tuple[str, list[str]]]) -> str:
    parts: list[str] = []
    if preamble:
        parts.append("\n".join(_rstrip_blank_tail(preamble)))
    for heading, body in sections:
        content = _rstrip_blank_tail(body)
        block = f"## {heading}\n"
        if content:
            block += "\n" + "\n".join(content)
        parts.append(block)
    return "\n".join(parts).rstrip("\n") + "\n"


def _h2_line_indices(lines: list[str]) -> list[int]:
    return [index for index, line in enumerate(lines) if line.startswith("## ")]


def _insert_after_last_nonblank(lines: list[str], start: int, end: int, inserted: list[str]) -> None:
    """Insert ``inserted`` after the last non-blank line in ``lines[start:end]`` (Story 83.13)."""
    if not inserted:
        return
    last_nonblank = start - 1
    for index in range(start, end):
        if lines[index].strip():
            last_nonblank = index
    lines[last_nonblank + 1 : last_nonblank + 1] = inserted


def _reconstruct_team_memory_index_from_main(
    main: str,
    *,
    branch_only_preamble: list[str],
    branch_only_sections: list[list[str]],
) -> str:
    """Keep ``main`` byte-for-byte except branch-only appended lines (Story 83.13)."""
    if not branch_only_preamble and not any(branch_only_sections):
        return main
    lines = main.split("\n")
    h2s = _h2_line_indices(lines)
    for section_index in range(len(h2s) - 1, -1, -1):
        inserted = branch_only_sections[section_index] if section_index < len(branch_only_sections) else []
        if not inserted:
            continue
        h2_index = h2s[section_index]
        body_start = h2_index + 1
        body_end = h2s[section_index + 1] if section_index + 1 < len(h2s) else len(lines)
        _insert_after_last_nonblank(lines, body_start, body_end, inserted)
    h2s = _h2_line_indices(lines)
    preamble_end = h2s[0] if h2s else len(lines)
    _insert_after_last_nonblank(lines, 0, preamble_end, branch_only_preamble)
    trailing_newline = main.endswith("\n")
    result = "\n".join(lines)
    if trailing_newline and not result.endswith("\n"):
        result += "\n"
    return result


def union_team_memory_index_texts(base: str, main: str, branch: str) -> str | None:
    """Story 83.11: union two append-only edits of ``.claude/memory/MEMORY.md``, or ``None`` when
    either side edited, removed, or reordered an existing line or section.

    Each ``## `` section is unioned like a memlog body: base lines survive byte-for-byte, then
    main's appended lines, then branch-only lines (deduped against main). Lines are opaque text."""
    base_parts = _parse_team_memory_index(base)
    main_parts = _parse_team_memory_index(main)
    branch_parts = _parse_team_memory_index(branch)
    if base_parts is None or main_parts is None or branch_parts is None:
        return None
    base_pre, base_secs = base_parts
    main_pre, main_secs = main_parts
    branch_pre, branch_secs = branch_parts
    base_headings = [heading for heading, _ in base_secs]
    if [heading for heading, _ in main_secs] != base_headings:
        return None
    if [heading for heading, _ in branch_secs] != base_headings:
        return None
    preamble = _union_appended_line_lists(
        _rstrip_blank_tail(base_pre), _rstrip_blank_tail(main_pre), _rstrip_blank_tail(branch_pre)
    )
    if preamble is None:
        return None
    main_pre_stripped = _rstrip_blank_tail(main_pre)
    branch_only_preamble = preamble[len(main_pre_stripped) :]
    branch_only_sections: list[list[str]] = []
    for (_, base_body), (_, main_body), (_, branch_body) in zip(base_secs, main_secs, branch_secs):
        merged_body = _union_appended_line_lists(base_body, main_body, branch_body)
        if merged_body is None:
            return None
        main_body_stripped = _rstrip_blank_tail(main_body)
        branch_only_sections.append(merged_body[len(main_body_stripped) :])
    return _reconstruct_team_memory_index_from_main(
        main,
        branch_only_preamble=branch_only_preamble,
        branch_only_sections=branch_only_sections,
    )


# --- Story 83.3: deferred-work ledger union ----------------------------------

_DW_ENTRY_START = re.compile(r"^(?:## DW-|### DW-)", re.MULTILINE)


def _opaque_dw_blocks(text: str) -> tuple[str, list[str]]:
    """Split ledger text into preamble and opaque DW entry blocks.

    Entries begin at a line starting with ``## DW-`` (legacy) or ``### DW-``. Each block is
    byte-identical text from one header through the character before the next header.
    """
    matches = list(_DW_ENTRY_START.finditer(text))
    if not matches:
        return text, []
    preamble = text[: matches[0].start()]
    blocks: list[str] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        blocks.append(text[start:end])
    return preamble, blocks


def _dw_blocks_from_append_tail(tail: str) -> list[str] | None:
    """Opaque ``## DW-`` / ``### DW-`` blocks parsed from an append-only suffix, or ``None`` when
    the suffix carries text before its first entry header (lines appended to the base's last entry),
    which no whole-block union may drop."""
    text = tail.lstrip("\n")
    if not text:
        return []
    preamble, blocks = _opaque_dw_blocks(text)
    if preamble.strip():
        return None
    return blocks


def _append_branch_only_blocks(result: str, branch_only: list[str]) -> str:
    """Append blocks main did not already add, separated by one blank line each."""
    for block in branch_only:
        if not result.endswith("\n\n"):
            result += "\n" if result.endswith("\n") else "\n\n"
        result += block.lstrip("\n")
    return result


def _append_only_tail(base: str, side: str) -> str | None:
    """Suffix ``side`` added after unchanged ``base``, or ``None`` if ``side`` edited ``base``."""
    if side == base:
        return ""
    if side.startswith(base):
        return side[len(base) :]
    core = base.rstrip("\n")
    if side.startswith(core):
        return side[len(core) :]
    return None


def union_deferred_work_texts(base: str, main: str, branch: str) -> str | None:
    """Story 83.3: the union of two append-only edits of one deferred-work-ledger.md, or None
    when either side is not append-only.

    Each ``## DW-`` / ``### DW-`` section is an opaque block. A side is append-only when its
    full text still starts with the merge-base text (trailing newlines on the base may be
    stripped before the append). The result is the merge-base file verbatim, then main's tail,
    then branch-only blocks (counter dedup).
    """
    main_tail = _append_only_tail(base, main)
    branch_tail = _append_only_tail(base, branch)
    if main_tail is None or branch_tail is None:
        return None

    result = base
    if main_tail:
        if not main_tail.strip():
            return None
        result += main_tail

    branch_after_main = _append_only_tail(main, branch)
    if branch_after_main is not None:
        if branch_after_main.strip():
            result += branch_after_main
    elif not main_tail and branch_tail:
        if not branch_tail.strip():
            return None
        result += branch_tail
    elif main_tail and branch_tail:
        main_new = _dw_blocks_from_append_tail(main_tail)
        branch_new = _dw_blocks_from_append_tail(branch_tail)
        if main_new is None or branch_new is None:
            return None
        main_new_count = Counter(main_new)
        branch_only: list[str] = []
        for block in branch_new:
            if main_new_count[block] > 0:
                main_new_count[block] -= 1
            else:
                branch_only.append(block)
        if branch_only:
            result = _append_branch_only_blocks(result, branch_only)

    if not result.endswith("\n"):
        result += "\n"
    return result


# --- Story 51.11 (CAP-258): blocked-twin promotion --------------------------


def blocked_twin_promotion_text(*, primary_text: str | None, worktree_text: str) -> str | None:
    """Text to write onto the primary's tracked copy of a story spec when a
    dispatch worktree halts ``blocked`` with its commit uncommitted (Story
    51.11), or ``None`` when no write is needed.

    The promoted twin is byte-identical to the worktree's own blocked spec
    — the same story's tracked spec at two physical paths (Story 51.7's
    dispatch-branch/primary split) — never independently reconstructed.
    Returns ``None`` when the primary copy is unreadable (``primary_text``
    is ``None``: nothing to overwrite) or already carries this exact text
    (idempotent — a re-run promotes nothing a second time).
    """
    if primary_text is None or primary_text == worktree_text:
        return None
    return worktree_text
