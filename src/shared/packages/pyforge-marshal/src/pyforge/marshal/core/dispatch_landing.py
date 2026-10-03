"""Dispatch session landing eligibility (Story 22.4, FR-193 CAP-4).

Pure functions only: verification outcome and git facts judge whether a
dispatched story may land via existing Epic 4 machinery. Never land on
self-report without passing independent verification (Story 22.3).
"""

from __future__ import annotations

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


def is_memlog_path(path: str) -> bool:
    """True when ``path`` is a Spec memlog: its basename is ``.memlog.md``, in any project --
    co-governor memlogs live under other projects, and an append-only union is safe wherever
    the file sits (Story 78.1, CAP-283)."""
    return path.replace("\\", "/").rsplit("/", 1)[-1] == MEMLOG_BASENAME


def is_deferred_work_path(path: str) -> bool:
    """True when ``path`` is a deferred-work ledger: its basename is ``deferred-work-ledger.md``."""
    return path.replace("\\", "/").rsplit("/", 1)[-1] == DEFERRED_WORK_BASENAME


def is_mechanical_conflict_path(
    path: str, *, ledger_rel: str | None = None, deferred_work_rel: str | None = None
) -> bool:
    """True when ``path`` is a known mechanical-only merge conflict: a Spec memlog (Story 78.1;
    the heal still escalates one that is not append-only), a sprint ledger, or a deferred-work
    ledger (Story 83.3). Given ``ledger_rel`` (the landing project's own ledger), only that exact
    path is a mechanical ledger -- another project's ledger is not this landing's to resolve
    (Story 59.1). Similarly for ``deferred_work_rel`` - only the project's own deferred work ledger."""
    normalized = path.replace("\\", "/")
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


# --- Story 83.3: deferred-work ledger union ----------------------------------

_DW_HEADER = "### DW-"


def _opaque_dw_blocks(text: str) -> tuple[str, list[str]]:
    """Split ledger text into preamble (before the first ``### DW-``) and opaque blocks.

    Each block is the full text from one ``### DW-`` header through the line before the next
    header. No validation or normalization — mixed entry formats stay byte-identical.
    """
    first = text.find(_DW_HEADER)
    if first == -1:
        return text, []
    preamble = text[:first]
    rest = text[first:]
    blocks: list[str] = []
    start = 0
    while start < len(rest):
        boundary = rest.find("\n" + _DW_HEADER, start + len(_DW_HEADER))
        if boundary == -1:
            blocks.append(rest[start:])
            break
        blocks.append(rest[start:boundary])
        start = boundary + 1
    return preamble, blocks


def _suffix_from_first_block(full: str, blocks: list[str], index: int) -> str:
    """Return ``full`` from the start of ``blocks[index]`` through EOF (empty when none)."""
    if index >= len(blocks):
        return ""
    pos = full.find(blocks[index])
    if pos < 0:
        return ""
    return full[pos:]


def union_deferred_work_texts(base: str, main: str, branch: str) -> str | None:
    """Story 83.3: the union of two append-only edits of one deferred-work-ledger.md, or None
    when either side is not append-only.

    Each ``### DW-`` section is an opaque block compared byte for byte. A side is append-only
    when its block list starts with the merge-base blocks unchanged, then adds whole blocks at
    the end. The result is the merge-base file verbatim, then main's appended tail, then branch
    blocks main did not already append (counter dedup, same as ``union_memlog_texts``).
    """
    _, base_blocks = _opaque_dw_blocks(base)
    _, main_blocks = _opaque_dw_blocks(main)
    _, branch_blocks = _opaque_dw_blocks(branch)

    base_count = len(base_blocks)
    if (
        len(main_blocks) < base_count
        or len(branch_blocks) < base_count
        or main_blocks[:base_count] != base_blocks
        or branch_blocks[:base_count] != base_blocks
    ):
        return None

    main_new = main_blocks[base_count:]
    branch_new = branch_blocks[base_count:]

    main_new_count = Counter(main_new)
    branch_only: list[str] = []
    for block in branch_new:
        if main_new_count[block] > 0:
            main_new_count[block] -= 1
        else:
            branch_only.append(block)

    result = base.rstrip("\n")
    if main_new:
        main_tail = _suffix_from_first_block(main, main_blocks, base_count)
        if not main_tail:
            return None
        result += main_tail.rstrip("\n")
    elif branch_new:
        branch_tail = _suffix_from_first_block(branch, branch_blocks, base_count)
        if not branch_tail:
            return None
        result += branch_tail.rstrip("\n")
    if branch_only and main_new:
        cursor = 0
        if base_count:
            last_shared = branch_blocks[base_count - 1]
            pos = branch.find(last_shared)
            cursor = pos + len(last_shared) if pos >= 0 else 0
        extra = ""
        for block in branch_only:
            pos = branch.find(block, cursor)
            if pos < 0:
                return None
            extra += branch[cursor:pos] + block
            cursor = pos + len(block)
        result += extra.rstrip("\n")

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
