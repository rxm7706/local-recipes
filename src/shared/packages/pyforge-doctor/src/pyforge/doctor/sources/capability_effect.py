"""Capability effect check (Stories 21.9/21.10, ``spec-capability-effect-check``).

Story 21.9 (CAP-1): caller-outside-its-own-tests reach — not wired in this
module yet; ``gather_caller_reach`` is reserved for that story.

Story 21.10 (CAP-2): read an optional ``verified: <date> — <what/where>`` line
on each declared CAP in ``SPEC.md``, render it beside the capability, and
report a ``shipped``/``realized`` Spec whose CAP carries none. Read-only —
never authors a ``verified:`` line (doctor NFR-1).

``REGISTRY`` registration landed in Story 21.10; ``__main__`` dispatch,
``detectors``, and fleet-picture wiring landed in Story 21.11.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ..models import DoctorStatus, Finding, Source
from . import degrade_on_exception
from .board import _CAP_DECL_LINE_RE, _CAP_SECTION_HEADING_RE, _HEADING_RE

__all__ = (
    "CapabilityVerifiedRow",
    "TERMINAL_SPEC_STATUSES_FOR_VERIFIED",
    "gather",
    "gather_verified_line",
    "iter_capability_verified_rows",
    "missing_verified_findings",
    "render_verified_beside_cap",
)

# Spec frontmatter statuses for which a missing ``verified:`` line on a CAP
# is reportable (Story 21.10 I/O matrix).
TERMINAL_SPEC_STATUSES_FOR_VERIFIED = frozenset({"shipped", "realized"})

_CHECK_VERIFIED = "capability-effect-verified"

# ``**verified:**`` or plain ``verified:`` on an indented CAP sub-line.
_VERIFIED_LINE_RE = re.compile(
    r"^\s*(?:-\s*)?(?:\*\*)?verified:(?:\*\*)?\s*(.+)$",
    re.IGNORECASE,
)

_SPEC_STATUS_RE = re.compile(r"^status:\s*(\S+)\s*(?:#.*)?$", re.MULTILINE)


@dataclass(frozen=True)
class CapabilityVerifiedRow:
    """One declared CAP's verified-column state for rendering and findings."""

    project: str
    spec_slug: str
    cap_n: int
    spec_status: str | None
    verified_text: str | None

    @property
    def rendered(self) -> str:
        return render_verified_beside_cap(self.cap_n, self.verified_text)


def render_verified_beside_cap(cap_n: int, verified_text: str | None) -> str:
    """Mechanical realized-versus-verified column cell for one CAP."""
    if verified_text:
        return f"CAP-{cap_n} — verified: {verified_text}"
    return f"CAP-{cap_n} — (no verified line)"


def _parse_spec_frontmatter_status(text: str) -> str | None:
    if not text.startswith("---"):
        return None
    closing = text.find("\n---", 3)
    if closing == -1:
        return None
    frontmatter = text[3:closing]
    match = _SPEC_STATUS_RE.search(frontmatter)
    if not match:
        return None
    status = match.group(1).strip()
    if len(status) >= 2 and status[0] == status[-1] and status[0] in "\"'":
        status = status[1:-1]
    return status


def _capabilities_section_body(spec_md_text: str) -> str | None:
    match = _CAP_SECTION_HEADING_RE.search(spec_md_text)
    if not match:
        return None
    nxt = _HEADING_RE.search(spec_md_text, match.end())
    end = nxt.start() if nxt else len(spec_md_text)
    return spec_md_text[match.end() : end]


def _parse_verified_in_cap_block(block: str) -> str | None:
    """The CAP block's most recent ``verified:`` line, unparsed."""
    matches: list[str] = []
    for line in block.splitlines():
        match = _VERIFIED_LINE_RE.match(line)
        if match:
            matches.append(match.group(1).strip())
    return matches[-1] if matches else None


def _parse_cap_blocks(section_body: str) -> list[tuple[int, str]]:
    blocks: list[tuple[int, str]] = []
    current_n: int | None = None
    current_lines: list[str] = []
    for line in section_body.splitlines(keepends=True):
        decl = _CAP_DECL_LINE_RE.match(line)
        if decl:
            if current_n is not None:
                blocks.append((current_n, "".join(current_lines)))
            current_n = int(decl.group(1))
            current_lines = [line]
        elif current_n is not None:
            current_lines.append(line)
    if current_n is not None:
        blocks.append((current_n, "".join(current_lines)))
    return blocks


def parse_spec_capability_verified_rows(
    *,
    project: str,
    spec_slug: str,
    spec_text: str,
) -> tuple[CapabilityVerifiedRow, ...]:
    """Parse every declared CAP's ``verified:`` line from one ``SPEC.md``."""
    spec_status = _parse_spec_frontmatter_status(spec_text)
    body = _capabilities_section_body(spec_text)
    if body is None:
        return ()
    rows: list[CapabilityVerifiedRow] = []
    for cap_n, block in _parse_cap_blocks(body):
        rows.append(
            CapabilityVerifiedRow(
                project=project,
                spec_slug=spec_slug,
                cap_n=cap_n,
                spec_status=spec_status,
                verified_text=_parse_verified_in_cap_block(block),
            )
        )
    return tuple(rows)


def iter_capability_verified_rows(target: Path) -> tuple[CapabilityVerifiedRow, ...]:
    """Walk every fleet ``SPEC.md`` and collect CAP verified rows."""
    projects_dir = target / "_bmad-output" / "projects"
    if not projects_dir.is_dir():
        return ()
    rows: list[CapabilityVerifiedRow] = []
    for project_dir in sorted(projects_dir.iterdir()):
        if not project_dir.is_dir():
            continue
        specs_dir = project_dir / "planning-artifacts" / "specs"
        if not specs_dir.is_dir():
            continue
        for spec_dir in sorted(specs_dir.iterdir()):
            if not spec_dir.is_dir() or not spec_dir.name.startswith("spec-"):
                continue
            spec_md = spec_dir / "SPEC.md"
            if not spec_md.is_file():
                continue
            try:
                text = spec_md.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            rows.extend(
                parse_spec_capability_verified_rows(
                    project=project_dir.name,
                    spec_slug=spec_dir.name,
                    spec_text=text,
                )
            )
    return tuple(rows)


def missing_verified_findings(
    rows: tuple[CapabilityVerifiedRow, ...],
    *,
    source: Source,
) -> tuple[Finding, ...]:
    """WARN findings for terminal-spec CAPs with no ``verified:`` line."""
    findings: list[Finding] = []
    for row in rows:
        if row.spec_status not in TERMINAL_SPEC_STATUSES_FOR_VERIFIED:
            continue
        if row.verified_text:
            continue
        spec_ref = f"{row.project}/{row.spec_slug}"
        findings.append(
            Finding(
                source=source,
                check=_CHECK_VERIFIED,
                status=DoctorStatus.WARN,
                message=(
                    f"{spec_ref} CAP-{row.cap_n} is in a "
                    f"{row.spec_status!r} Spec but carries no `verified:` line"
                ),
                evidence={
                    "project": row.project,
                    "spec_slug": row.spec_slug,
                    "cap_n": row.cap_n,
                    "spec_status": row.spec_status,
                    "rendered": row.rendered,
                },
            )
        )
    return tuple(findings)


def gather_verified_line(target: Path) -> tuple[Finding, ...]:
    """CAP-2: missing ``verified:`` lines on terminal-status Spec CAPs only."""
    return missing_verified_findings(
        iter_capability_verified_rows(target),
        source=Source.CAPABILITY_EFFECT,
    )


def gather(target: Path) -> tuple[Finding, ...]:
    """Capability-effect gather — verified-line pass today; caller reach in 21.9."""
    return degrade_on_exception(
        Source.CAPABILITY_EFFECT,
        "capability-effect",
        lambda: gather_verified_line(target),
    )
