"""pyforge.scribe.promote — the promotion boundary (FR-3/FR-4, AD-2, Story 1.3).

Scans a user-local Claude Code auto-memory directory (foreign input, never
written to by this module -- AD-2), classifies each entry, and drafts a
mechanical "team voice" rewrite for the entries worth promoting. Nothing
under `.claude/memory/` changes until the caller has shown the resulting
`PromotionProposal` to a human and gotten an explicit yes back —
`apply_promotion()` is the only function here that writes anything, and it
writes exclusively through `capture()` (capture.py's locked, no-clobber
write path), never directly.

Classification is strict priority order, first match wins:
  1. `promoted: true` (either frontmatter shape, any indentation)  -> already-promoted
  2. unparseable frontmatter, or a backtick-quoted path under one of the
     known repo prefixes that does not exist on disk               -> stale
  3. `description` contains a personal-tone keyword                -> personal
  4. everything else                                               -> team-relevant

The team-voice rewrite (`rewrite_team_voice()`) is pure regex/string
manipulation -- no LLM or network call (AD-6: `promote.py` is scoped under
AD-2 only; `LLMAdapter` belongs exclusively to `recall.py`, Wave 2). It is
deliberately narrow: first-person "I prefer"/"I want" framing, "(the) user
prefers" framing, and parenthetical asides that contain a bare git-short-hash
token are stripped; everything else -- paths, commands, backticked
identifiers, `**Why:**`/`**How to apply:**` labels -- is left untouched. An
imperfect mechanical rewrite is caught at the human confirm step, not
silently shipped.

Pointer-stub write-back and the idempotent-skip-on-reinvocation proof are
Story 1.4 — out of scope here. The source user-local file is never modified
by anything in this module.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pyforge.scribe.capture import _DESCRIPTION_MAX_LEN, CaptureResult, _truncate
from pyforge.scribe.capture import capture as capture_write
from pyforge.scribe.models import CAPTURE_TYPES, CaptureType, _unescape

Classification = Literal["team-relevant", "personal", "already-promoted", "stale"]

#: `description` substrings (case-insensitive) that mark an entry as personal
#: taste rather than a team-wide rule -- validated against the one worked
#: example in the epics AC + legacy spec ("a terseness/tone preference") and
#: this corpus's own `feedback_no_courtesy_comments.md` (description contains
#: "terse").
_PERSONAL_KEYWORDS: tuple[str, ...] = (
    "terse",
    "terseness",
    "tone",
    "verbosity",
    "communication style",
    "emoji",
)

#: Backtick-quoted paths are only checked for staleness when they start with
#: one of these repo-relative prefixes -- bounds false positives from
#: unrelated backticked text in prose.
_STALE_PATH_PREFIXES: tuple[str, ...] = (
    "src/",
    "recipes/",
    "docs/",
    ".claude/",
    "_bmad/",
    "_bmad-output/",
    "pixi.toml",
)

_BACKTICK_RE = re.compile(r"`([^`]+)`")
#: A parenthetical aside containing a bare 7-40 hex-char token (the concrete
#: shape this repo's own entries use, e.g. "(commit `31eb4e6bba`)") gets
#: dropped whole, including the whitespace immediately before it.
_HASH_PARENTHETICAL_RE = re.compile(r"\s*\([^()]*\b[0-9a-fA-F]{7,40}\b[^()]*\)")
_I_PREFER_RE = re.compile(r"\bI (?:prefer|want)\s+")
_USER_PREFERS_RE = re.compile(r"\b(?:the )?user prefers\s+", re.IGNORECASE)
_MULTI_SPACE_RE = re.compile(r"[ \t]{2,}")


@dataclass(frozen=True)
class ClassifiedEntry:
    """One user-local entry after classification (+ draft, if team-relevant)."""

    source_path: Path
    classification: Classification
    reason: str
    capture_type: CaptureType | None = None
    slug: str | None = None
    target_path: Path | None = None
    rewritten_text: str | None = None
    rewritten_description: str | None = None
    memory_index_line: str | None = None


@dataclass(frozen=True)
class PromotionProposal:
    """The full scan result -- every entry, classified, plus drafts for the
    team-relevant ones. Nothing here has been written to disk."""

    source_root: Path
    entries: tuple[ClassifiedEntry, ...]

    @property
    def promotable(self) -> tuple[ClassifiedEntry, ...]:
        return tuple(e for e in self.entries if e.classification == "team-relevant")


def default_user_local_root() -> Path:
    """Claude Code's per-project auto-memory dir for the current cwd.

    Empirically reverse-engineered from this repo's own
    `~/.claude/projects/` listing: every character in the absolute cwd path
    that is not `[A-Za-z0-9]` becomes a literal `-` (one-for-one, not
    collapsed) -- e.g. `/home/x/.bmad-loops/y` encodes to
    `-home-x--bmad-loops-y` (the `/` before `.bmad-loops` and the `.` both
    become `-`, landing as a doubled hyphen). `--source` is the escape
    hatch if this heuristic is ever wrong or Claude Code's scheme changes.
    """
    encoded = re.sub(r"[^A-Za-z0-9]", "-", str(Path.cwd()))
    return Path.home() / ".claude" / "projects" / encoded / "memory"


def classify_and_draft(source_root: Path, memory_root: Path, repo_root: Path) -> PromotionProposal:
    """Scan every `*.md` in `source_root`, classify it, and draft a
    team-voice rewrite for each `team-relevant` entry.

    Read-only: nothing is written anywhere, including under `memory_root`
    (only consulted to preview a collision-free slug/target path) and
    `source_root` itself. `repo_root` is only used for the stale-path
    existence check. Raises `ValueError` if `source_root` does not exist --
    before any read.
    """
    if not source_root.is_dir():
        raise ValueError(
            f"{source_root} does not exist -- pass --source to point at the correct "
            "user-local auto-memory directory"
        )

    claimed_slugs: dict[str, set[str]] = {t: set() for t in CAPTURE_TYPES}
    entries = tuple(
        _classify_one(path, memory_root, repo_root, claimed_slugs)
        for path in sorted(source_root.glob("*.md"))
    )
    return PromotionProposal(source_root=source_root, entries=entries)


def apply_promotion(memory_root: Path, proposal: PromotionProposal) -> list[CaptureResult]:
    """Write every `team-relevant` entry in `proposal` via `capture()` --
    the only write path (AD-2). The source user-local files are never
    touched here (pointer-stub write-back is Story 1.4)."""
    return [
        capture_write(
            memory_root,
            entry.capture_type,
            entry.rewritten_text,
            slug=entry.slug,
            description=entry.rewritten_description,
        )
        for entry in proposal.promotable
    ]


def rewrite_team_voice(text: str) -> str:
    """Mechanically rewrite one entry's text into team voice (FR-4, AD-6).

    No LLM/network call -- pure regex. Strips first-person "I prefer"/"I
    want" framing, drops "(the) user prefers" framing, and drops
    parenthetical asides containing a bare git-short-hash token (7-40 hex
    chars). Everything else -- paths, commands, backticked identifiers,
    `**Why:**`/`**How to apply:**` labels -- is left untouched.
    """
    result = _HASH_PARENTHETICAL_RE.sub("", text)
    result = _I_PREFER_RE.sub("", result)
    result = _USER_PREFERS_RE.sub("", result)
    result = _MULTI_SPACE_RE.sub(" ", result)
    return result.strip()


def _classify_one(
    path: Path,
    memory_root: Path,
    repo_root: Path,
    claimed_slugs: dict[str, set[str]],
) -> ClassifiedEntry:
    raw = path.read_text(encoding="utf-8")
    split = _split_frontmatter(raw)
    if split is None:
        return ClassifiedEntry(
            source_path=path,
            classification="stale",
            reason="malformed frontmatter: missing closing '---' delimiter",
        )
    frontmatter, body = split
    fields = _parse_frontmatter_fields(frontmatter)

    if fields.get("promoted", "").strip().lower() == "true":
        return ClassifiedEntry(
            source_path=path,
            classification="already-promoted",
            reason="already carries promoted: true",
        )

    capture_type = fields.get("type")
    if capture_type not in CAPTURE_TYPES:
        return ClassifiedEntry(
            source_path=path,
            classification="stale",
            reason=f"malformed frontmatter: missing or invalid type {capture_type!r}",
        )

    missing_path = _find_missing_repo_path(body, repo_root)
    if missing_path is not None:
        return ClassifiedEntry(
            source_path=path,
            classification="stale",
            reason=f"references missing path `{missing_path}`",
        )

    description = fields.get("description", "")
    matched_keyword = _matched_personal_keyword(description)
    if matched_keyword is not None:
        return ClassifiedEntry(
            source_path=path,
            classification="personal",
            reason=f"description matches personal-tone keyword {matched_keyword!r}",
        )

    slug_base = _derive_slug(path.stem, capture_type)
    type_dir = memory_root / capture_type
    slug = _preview_unique_slug(type_dir, slug_base, claimed_slugs[capture_type])
    rewritten_text = rewrite_team_voice(body)
    rewritten_description = _truncate(
        rewrite_team_voice(description or body), _DESCRIPTION_MAX_LEN
    )
    target_path = type_dir / f"{slug}.md"
    memory_index_line = f"- [{slug}]({capture_type}/{slug}.md) — {rewritten_description}"

    return ClassifiedEntry(
        source_path=path,
        classification="team-relevant",
        reason="passes the team-relevance test",
        capture_type=capture_type,
        slug=slug,
        target_path=target_path,
        rewritten_text=rewritten_text,
        rewritten_description=rewritten_description,
        memory_index_line=memory_index_line,
    )


def _split_frontmatter(content: str) -> tuple[str, str] | None:
    """Return `(frontmatter_body, body)`, or `None` if the `---` delimiters
    can't be located -- mirrors `parse_capture_file()`'s boundary-finding,
    but tolerates arbitrary extra keys and never raises."""
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    try:
        closing_idx = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return None
    frontmatter = "\n".join(lines[1:closing_idx])
    body = "\n".join(lines[closing_idx + 1 :]).strip("\n")
    return frontmatter, body


def _parse_frontmatter_fields(frontmatter: str) -> dict[str, str]:
    """Flatten a frontmatter block's keys, regardless of nesting depth.

    Real auto-memory files use both a flat `type: feedback` shape and a
    nested `metadata:\n  type: feedback` shape (any indentation). Since only
    leaf key names matter for classification (`type`, `promoted`,
    `description`) and none collide across nesting levels in practice, a
    per-line `key: value` scan with `.strip()`'d indentation is enough --
    no need for a real YAML parser (same lean-dep rationale as models.py).
    A bare nesting header line (e.g. `metadata:` with no value) is skipped;
    its children arrive as their own lines regardless of indent.
    """
    fields: dict[str, str] = {}
    for raw_line in frontmatter.splitlines():
        stripped = raw_line.strip()
        if not stripped or ":" not in stripped:
            continue
        key, _, value = stripped.partition(":")
        key = key.strip()
        value = value.strip()
        if not value:
            continue
        fields[key] = _unescape(value)
    return fields


def _matched_personal_keyword(description: str) -> str | None:
    lowered = description.lower()
    for keyword in _PERSONAL_KEYWORDS:
        if keyword in lowered:
            return keyword
    return None


def _find_missing_repo_path(body: str, repo_root: Path) -> str | None:
    """First backtick-quoted, known-prefix path in `body` that does not
    exist under `repo_root`, or `None` if every such reference resolves."""
    for match in _BACKTICK_RE.finditer(body):
        candidate = match.group(1)
        if not candidate.startswith(_STALE_PATH_PREFIXES):
            continue
        if any(ch in candidate for ch in " \t*?[]()"):
            continue  # not a literal single-path reference -- skip to bound false positives
        if not (repo_root / candidate).exists():
            return candidate
    return None


def _derive_slug(filename_stem: str, capture_type: str) -> str:
    """Source filename -> promoted slug (legacy spec Q9): drop the
    `<type>_` prefix if present, then `_` -> `-`."""
    stem = filename_stem.removeprefix(f"{capture_type}_")
    return stem.replace("_", "-")


def _preview_unique_slug(type_dir: Path, base_slug: str, claimed: set[str]) -> str:
    """Mirror `capture.py`'s `_unique_slug()` collision check for the
    proposal preview, additionally accounting for other team-relevant
    entries drafted earlier in the same batch that haven't been written to
    disk yet (so a plain `type_dir` existence check alone wouldn't see
    them) -- keeps the preview accurate even when two source entries in one
    scan would otherwise derive the same slug."""
    slug = base_slug
    suffix = 1
    while (type_dir / f"{slug}.md").exists() or slug in claimed:
        suffix += 1
        slug = f"{base_slug}-{suffix}"
    claimed.add(slug)
    return slug
