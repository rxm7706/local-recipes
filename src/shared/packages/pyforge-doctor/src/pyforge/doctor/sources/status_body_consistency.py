"""Status/body consistency gather (Stories 21.12–21.16, ``spec-status-body-consistency``).

Story 21.12 (CAP-1): under ``status: realized|shipped|done``, report body lines
that still read incomplete progress — ``N of M stories/capabilities``,
hyphenated ``N-of-M``, or bare ``N/M`` on a line that also names
stories/capabilities — with ``N < M``. Warn-only, read-only, fail-open.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from ..models import DoctorStatus, Finding, Source
from . import degrade_on_exception

__all__ = (
    "TERMINAL_STATUSES",
    "TierScanStats",
    "gather",
    "gather_progress_phrase",
    "iter_terminal_tier_documents",
    "scan_body_for_incomplete_progress",
)

TERMINAL_STATUSES = frozenset({"realized", "shipped", "done"})

_CHECK_PROGRESS = "status-body-progress-phrase"
_CHECK_UNPARSEABLE = "status-body-unparseable"

# ``3 of 9 stories`` / ``3 of 9 capabilities``
_PROGRESS_OF_RE = re.compile(
    r"\b(\d+)\s+of\s+(\d+)\s+(?:stories|capabilities)\b",
    re.IGNORECASE,
)

# ``3-of-9`` (same semantic family as the spaced form)
_HYPHEN_OF_RE = re.compile(
    r"\b(\d+)-of-(\d+)\b",
    re.IGNORECASE,
)

# ``3/9`` only when the line also names stories or capabilities
_SLASH_RE = re.compile(r"\b(\d+)/(\d+)\b")
_SLASH_CONTEXT_RE = re.compile(r"\b(?:stories?|capabilities?)\b", re.IGNORECASE)


@dataclass(frozen=True)
class TierScanStats:
    scanned_terminal: int = 0
    silent: int = 0
    fired: int = 0


@dataclass(frozen=True)
class ProgressMatch:
    line_no: int
    line_text: str
    n: int
    m: int
    matched: str


def _parse_frontmatter(text: str) -> tuple[dict[str, object], bool]:
    """Return ``(fields, unparseable)`` for a ``---``-fenced document."""
    if not text.startswith("---"):
        if "---" in text:
            return {}, True
        return {}, False
    try:
        parts = text.split("---", 2)
        if len(parts) < 3:
            return {}, True
        data = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return {}, True
    if data is None:
        return {}, False
    if not isinstance(data, dict):
        return {}, True
    return data, False


def _body_after_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return text
    marker = "\n---\n"
    idx = text.find(marker, 3)
    if idx == -1:
        return ""
    return text[idx + len(marker) :]


def _normalize_status(raw: object) -> str:
    if not isinstance(raw, str):
        return ""
    status = raw.strip()
    if len(status) >= 2 and status[0] == status[-1] and status[0] in "\"'":
        status = status[1:-1]
    return status.strip()


def _match_incomplete_progress_on_line(line: str) -> list[tuple[int, int, str]]:
    """Return ``(n, m, matched_phrase)`` for every incomplete-progress hit on ``line``."""
    hits: list[tuple[int, int, str]] = []
    for match in _PROGRESS_OF_RE.finditer(line):
        n, m = int(match.group(1)), int(match.group(2))
        if n < m:
            hits.append((n, m, match.group(0)))
    for match in _HYPHEN_OF_RE.finditer(line):
        n, m = int(match.group(1)), int(match.group(2))
        if n < m:
            hits.append((n, m, match.group(0)))
    if _SLASH_CONTEXT_RE.search(line):
        for match in _SLASH_RE.finditer(line):
            n, m = int(match.group(1)), int(match.group(2))
            if n < m:
                hits.append((n, m, match.group(0)))
    return hits


def scan_body_for_incomplete_progress(body: str) -> tuple[ProgressMatch, ...]:
    """Every body line whose text reads incomplete progress with ``N < M``."""
    out: list[ProgressMatch] = []
    for line_no, line in enumerate(body.splitlines(), start=1):
        for n, m, matched in _match_incomplete_progress_on_line(line):
            out.append(
                ProgressMatch(
                    line_no=line_no,
                    line_text=line.rstrip(),
                    n=n,
                    m=m,
                    matched=matched,
                )
            )
    return tuple(out)


def iter_terminal_tier_documents(target: Path) -> tuple[tuple[Path, str], ...]:
    """Dream ``*.md`` and ``SPEC.md`` paths whose frontmatter ``status`` is terminal."""
    docs: list[tuple[Path, str]] = []

    dreams_dir = target / "docs" / "dreams"
    if dreams_dir.is_dir():
        for path in sorted(dreams_dir.glob("*.md")):
            if path.name == "README.md":
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            fm, unparseable = _parse_frontmatter(text)
            if unparseable:
                docs.append((path, ""))
                continue
            status = _normalize_status(fm.get("status"))
            if status in TERMINAL_STATUSES:
                docs.append((path, status))

    spec_roots = (
        target / "_bmad-output" / "projects",
        target / "docs" / "governance",
    )
    for root in spec_roots:
        if not root.is_dir():
            continue
        if root.name == "projects":
            for project_dir in sorted(root.iterdir()):
                specs_dir = project_dir / "planning-artifacts" / "specs"
                if not specs_dir.is_dir():
                    continue
                for spec_dir in sorted(specs_dir.iterdir()):
                    spec_md = spec_dir / "SPEC.md"
                    if not spec_md.is_file():
                        continue
                    _append_spec_if_terminal(spec_md, docs)
        else:
            for spec_md in sorted(root.glob("**/SPEC.md")):
                _append_spec_if_terminal(spec_md, docs)

    return tuple(docs)


def _append_spec_if_terminal(spec_md: Path, docs: list[tuple[Path, str]]) -> None:
    try:
        text = spec_md.read_text(encoding="utf-8")
    except OSError:
        return
    fm, unparseable = _parse_frontmatter(text)
    if unparseable:
        docs.append((spec_md, ""))
        return
    status = _normalize_status(fm.get("status"))
    if status in TERMINAL_STATUSES:
        docs.append((spec_md, status))


def _rel_path(path: Path, target: Path) -> str:
    try:
        return path.relative_to(target).as_posix()
    except ValueError:
        return path.as_posix()


def _progress_phrase_message(*, rel: str, line_no: int, status: str, matched: str) -> str:
    return (
        f"{rel}:{line_no} reads {matched!r} under status: {status!r}"
    )


def gather_progress_phrase(target: Path) -> tuple[Finding, ...]:
    """CAP-1: incomplete progress phrases under terminal ``status:``."""
    findings: list[Finding] = []
    scanned_terminal = 0
    silent = 0
    fired = 0

    for path, status in iter_terminal_tier_documents(target):
        rel = _rel_path(path, target)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            findings.append(
                Finding(
                    source=Source.STATUS_BODY_CONSISTENCY,
                    check=_CHECK_UNPARSEABLE,
                    status=DoctorStatus.WARN,
                    message=(
                        f"{rel} could not be read — "
                        f"{exc.__class__.__name__}: {exc}"
                    ),
                    evidence={"path": rel},
                )
            )
            continue

        fm, unparseable = _parse_frontmatter(text)
        if unparseable:
            findings.append(
                Finding(
                    source=Source.STATUS_BODY_CONSISTENCY,
                    check=_CHECK_UNPARSEABLE,
                    status=DoctorStatus.WARN,
                    message=f"{rel} frontmatter is unparseable",
                    evidence={"path": rel},
                )
            )
            continue

        resolved_status = status or _normalize_status(fm.get("status"))
        if resolved_status not in TERMINAL_STATUSES:
            continue

        scanned_terminal += 1
        body = _body_after_frontmatter(text)
        matches = scan_body_for_incomplete_progress(body)
        if not matches:
            silent += 1
            continue

        for match in matches:
            fired += 1
            findings.append(
                Finding(
                    source=Source.STATUS_BODY_CONSISTENCY,
                    check=_CHECK_PROGRESS,
                    status=DoctorStatus.WARN,
                    message=_progress_phrase_message(
                        rel=rel,
                        line_no=match.line_no,
                        status=resolved_status,
                        matched=match.matched,
                    ),
                    evidence={
                        "path": rel,
                        "line": match.line_no,
                        "line_text": match.line_text,
                        "status": resolved_status,
                        "n": match.n,
                        "m": match.m,
                        "matched": match.matched,
                    },
                )
            )

    tier_stats = {
        "scanned_terminal": scanned_terminal,
        "silent": silent,
        "fired": fired,
    }
    if not findings:
        return (
            Finding(
                source=Source.STATUS_BODY_CONSISTENCY,
                check="status-body-consistency",
                status=DoctorStatus.OK,
                message=(
                    "no incomplete progress phrases under terminal status "
                    f"across {scanned_terminal} document(s)"
                ),
                evidence=tier_stats,
            ),
        )

    return tuple(
        Finding(
            source=f.source,
            check=f.check,
            status=f.status,
            message=f.message,
            evidence={**f.evidence, **tier_stats},
        )
        for f in findings
    )


def gather(target: Path) -> tuple[Finding, ...]:
    """Status/body consistency gather — progress-phrase pass today."""
    return degrade_on_exception(
        Source.STATUS_BODY_CONSISTENCY,
        "status-body-consistency",
        lambda: gather_progress_phrase(target),
    )
