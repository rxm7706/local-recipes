"""pyforge.scribe.models — the `CaptureRecord` model + its on-disk frontmatter shape.

`CaptureRecord` is the internal, Pydantic representation of one immutable
team-memory capture (AD-1). `to_frontmatter()`/`from_frontmatter()` isolate
the translation to and from `.claude/memory/<type>/*.md`'s on-disk YAML
frontmatter in exactly this one place, so a future upstream schema change
touches one module instead of every caller.

The on-disk shape is `name` / `description` / `metadata.type` — the CURRENT
live Claude Code auto-memory frontmatter shape (`type` nested under a
`metadata:` key), verified against on-disk auto-memory entries such as
`feedback_python_test_convention.md` and `project_pyforge_warden.md`, not
the architecture doc's flatter `name`/`description`/`type` shorthand (see
the spec's Design Notes). Only `name`/`description`/`metadata.type` round-
trip through the frontmatter in Wave 1 — `id`, `supersedes`, `captured_at`,
and `source` exist on the model for the epic's later waves (compile/recall,
promotion) but are not yet persisted to disk.

No YAML library dependency is introduced for this (AD-6, lean-dep
doctrine) — the on-disk shape is small and fixed, so a hand-written
serializer/parser is simpler than pulling in a general-purpose parser for
three keys.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field

CaptureType = Literal["feedback", "project", "reference"]

#: Ordered so callers can render/validate against a stable list.
CAPTURE_TYPES: tuple[CaptureType, ...] = ("feedback", "project", "reference")


class CaptureRecord(BaseModel):
    """One immutable, append-only team-memory capture (AD-1)."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    type: CaptureType
    name: str
    description: str
    text: str
    supersedes: Optional[str] = None
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "scribe capture"

    def to_frontmatter(self) -> str:
        """Serialize to the on-disk `.claude/memory/<type>/*.md` frontmatter block.

        Both `name` and `description` are quoted/escaped: an unquoted YAML
        scalar that happens to look like a bool/int/null/date (e.g. a slug
        derived from text like ``"404"`` or ``"2026-07-25"``) would silently
        parse back as that type instead of `str` for any standards-compliant
        reader -- quoting both fields the same way closes that class of bug.

        `supersedes` (Wave 2, Story 2.3) is emitted as an additive extra
        line ONLY when set -- a record without it round-trips byte-for-byte
        identical to Wave 1's original shape (AD-9: Wave 2 must not force a
        breaking rewrite of the Wave 1 file contract).
        """
        lines = [
            "---",
            f'name: "{_escape(self.name)}"',
            f'description: "{_escape(self.description)}"',
            "metadata:",
            f"  type: {self.type}",
        ]
        if self.supersedes is not None:
            lines.append(f'supersedes: "{_escape(self.supersedes)}"')
        lines.append("---")
        return "\n".join(lines) + "\n"

    @classmethod
    def from_frontmatter(cls, frontmatter: str, *, text: str = "") -> "CaptureRecord":
        """Parse a `to_frontmatter()`-shaped block back into a `CaptureRecord`.

        Understands exactly the shape this module writes (`name`,
        `description`, `metadata.type`, optional `supersedes`) — the
        isolated swap point the spec calls for, not a general-purpose YAML
        parser. Prefer `parse_capture_file()` when reading a whole file from
        disk: it locates this block's boundaries correctly even when the
        captured body itself contains a bare `---` line.
        """
        name = ""
        description = ""
        capture_type: Optional[str] = None
        supersedes: Optional[str] = None
        in_metadata = False
        for line in frontmatter.splitlines():
            if line.strip() in ("", "---"):
                continue
            if line.startswith("metadata:"):
                in_metadata = True
                continue
            if in_metadata and line.startswith("  type:"):
                capture_type = line.split(":", 1)[1].strip()
                continue
            if line.startswith("name:"):
                name = _unescape(line.split(":", 1)[1].strip())
                in_metadata = False
            elif line.startswith("description:"):
                description = _unescape(line.split(":", 1)[1].strip())
                in_metadata = False
            elif line.startswith("supersedes:"):
                raw = line.split(":", 1)[1].strip()
                supersedes = _unescape(raw) if raw else None
                in_metadata = False

        if capture_type not in CAPTURE_TYPES:
            raise ValueError(f"invalid or missing metadata.type in frontmatter: {capture_type!r}")

        return cls(type=capture_type, name=name, description=description, text=text, supersedes=supersedes)


#: What kind of real-tool surface a compiled `GraphNode` was read from
#: (Story 2.2's named input surfaces, plus Story 3.2's transcript surface,
#: plus Story 6.1's optional graphify `compile_surface` extra).
GraphNodeKind = Literal["memory", "memlog", "commit", "doc", "transcript", "code"]


class GraphNode(BaseModel):
    """One compiled knowledge-graph fact (Story 2.1/2.2, AD-1/AD-5).

    Bi-temporal-lite (Story 2.3, AD-4): `valid_from`/`valid_until` track
    when this node was/is in effect; `valid_until is None` means the node is
    currently active. Supersession NEVER deletes a node -- it sets
    `valid_until` + `superseded_by` on the prior node via
    `GraphStore.invalidate_edge()`, so a superseded fact stays queryable and
    traceable (`query_by_citation()`), just no longer current.

    `citation` is always verified resolvable before `recall.py` surfaces a
    node: a repo-relative file path or `"commit:<sha>"` for a git-history
    node point at a real repo artifact, while `"<jsonl filename>:L<line>"`
    for a transcript node is format-checked only, never re-resolved against
    a live file, since a session transcript is per-user/local and can be
    pruned or rotated outside Scribe's control (AD-8, Story 3.2).

    `stale` (Story 6.3, CAP-13) is a git-timestamp-only signal, orthogonal to
    `is_current`: `compile_graph()` sets it on a CURRENT node (Story 2.3's
    supersession already handles the non-current case) whose citation's
    source file has a git commit postdating this node's own `valid_from`,
    with no `supersedes:` edge naming it. It is never set by an LLM call or
    any judgment beyond that comparison. `recall.py` treats a stale node the
    same as an unresolvable citation -- excluded from candidacy, so a
    consumer never sees it served as if it were current.
    """

    id: str
    kind: GraphNodeKind
    title: str
    text: str
    citation: str
    valid_from: datetime
    valid_until: Optional[datetime] = None
    superseded_by: Optional[str] = None
    stale: bool = False

    @property
    def is_current(self) -> bool:
        return self.valid_until is None


def parse_capture_file(path: Path) -> "CaptureRecord":
    """Parse a whole `.claude/memory/<type>/*.md` file written by `to_frontmatter()`.

    Splits on exactly the first two lines that are `---` alone, so a bare
    `---` line inside the captured body (e.g. a markdown horizontal rule)
    is left untouched instead of being mistaken for the frontmatter
    boundary -- unlike a naive whole-string `str.split("---")`.
    """
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"{path} does not start with a frontmatter '---' delimiter")
    try:
        closing_idx = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration as exc:
        raise ValueError(f"{path} frontmatter has no closing '---' delimiter") from exc

    frontmatter = "\n".join(lines[: closing_idx + 1]) + "\n"
    body = "\n".join(lines[closing_idx + 1 :]).strip("\n")
    return CaptureRecord.from_frontmatter(frontmatter, text=body)


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _unescape(value: str) -> str:
    if len(value) >= 2 and value.startswith('"') and value.endswith('"'):
        value = value[1:-1]
    return value.replace('\\"', '"').replace("\\\\", "\\")
