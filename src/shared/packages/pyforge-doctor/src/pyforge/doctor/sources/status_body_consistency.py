"""Status/body consistency gather (Stories 21.12–21.16, ``spec-status-body-consistency``).

Story 21.12 (CAP-1): under ``status: realized|shipped|done``, report body lines
that still read incomplete progress — ``N of M stories/capabilities``,
hyphenated ``N-of-M``, or bare ``N/M`` on a line that also names
stories/capabilities — with ``N < M``. Warn-only, read-only, fail-open.

Story 21.13 (CAP-2): reconcile a Spec's declared ``open_questions`` frontmatter
against its companion ``.memlog.md``'s last unclosed ``(open)`` / ``(question)``
entry. Warn-only, read-only, fail-open — reports the contradiction, never
proposes closing text.
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
    "OpenQuestionMatch",
    "OpenQuestionsScanStats",
    "TierScanStats",
    "gather",
    "gather_open_questions_reconcile",
    "gather_progress_phrase",
    "iter_spec_documents",
    "iter_terminal_tier_documents",
    "last_unclosed_memlog_question",
    "open_questions_frontmatter_count",
    "scan_body_for_incomplete_progress",
)

TERMINAL_STATUSES = frozenset({"realized", "shipped", "done"})

_CHECK_PROGRESS = "status-body-progress-phrase"
_CHECK_OPEN_QUESTIONS = "status-body-open-questions"
_CHECK_UNPARSEABLE = "status-body-unparseable"

_MEMLOG_ENTRY_RE = re.compile(r"^-\s+\((\w+)")

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


@dataclass(frozen=True)
class OpenQuestionMatch:
    line_no: int
    line_text: str


@dataclass(frozen=True)
class OpenQuestionsScanStats:
    scanned_specs: int = 0
    silent: int = 0
    fired: int = 0


def _memlog_entry_tag(line: str) -> str | None:
    match = _MEMLOG_ENTRY_RE.match(line.strip())
    if not match:
        return None
    return match.group(1).lower()


def last_unclosed_memlog_question(memlog_text: str) -> OpenQuestionMatch | None:
    """The last ``(open)`` / ``(question)`` entry with no later ``(decision)``."""
    last_open: OpenQuestionMatch | None = None
    for line_no, line in enumerate(memlog_text.splitlines(), start=1):
        tag = _memlog_entry_tag(line)
        if tag is None:
            continue
        if tag in {"open", "question"}:
            last_open = OpenQuestionMatch(line_no=line_no, line_text=line.rstrip())
        elif tag == "decision":
            last_open = None
    return last_open


def _strip_yaml_comment(value: str) -> str:
    quote: str | None = None
    for index, char in enumerate(value):
        if quote:
            if char == quote:
                quote = None
        elif char in "\"'":
            quote = char
        elif char == "#" and (index == 0 or value[index - 1].isspace()):
            return value[:index].strip()
    return value.strip()


def open_questions_frontmatter_count(
    text: str,
) -> tuple[int, int | None, bool]:
    """Return ``(count, open_questions_line_no, unparseable)`` for a Spec body."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return 0, None, True
    end = next((index for index in range(1, len(lines)) if lines[index].strip() == "---"), -1)
    if end < 0:
        return 0, None, True

    fm, unparseable = _parse_frontmatter(text)
    if unparseable:
        return 0, None, True

    fm_lines = lines[1:end]
    key_idx = next(
        (index for index, line in enumerate(fm_lines) if line.startswith("open_questions:")),
        -1,
    )
    if key_idx < 0:
        return 0, None, False

    open_questions_line = key_idx + 2  # frontmatter body starts at file line 2
    raw = fm.get("open_questions")
    if raw is None:
        inline = _strip_yaml_comment(fm_lines[key_idx].split(":", 1)[1])
        if inline:
            if inline.startswith("[") and inline.endswith("]"):
                inner = inline[1:-1].strip()
                return (
                    0 if not inner else len([x for x in inner.split(",") if x.strip()]),
                    open_questions_line,
                    False,
                )
            return 0, open_questions_line, True
        count = 0
        indent: int | None = None
        for line in fm_lines[key_idx + 1 :]:
            if line.strip() and not line.startswith((" ", "\t")):
                break
            stripped = line.lstrip()
            if not stripped.startswith("- "):
                continue
            item_indent = len(line) - len(stripped)
            if indent is None:
                indent = item_indent
            if item_indent == indent:
                count += 1
        return count, open_questions_line, False

    if isinstance(raw, list):
        return len(raw), open_questions_line, False
    return 0, open_questions_line, True


def iter_spec_documents(target: Path) -> tuple[Path, ...]:
    """Every ``SPEC.md`` under BMAD specs and governance."""
    docs: list[Path] = []
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
                    if spec_md.is_file():
                        docs.append(spec_md)
        else:
            for spec_md in sorted(root.glob("**/SPEC.md")):
                docs.append(spec_md)
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


def _open_questions_message(
    *,
    rel: str,
    spec_line: int,
    memlog_line: int,
) -> str:
    return (
        f"{rel}:{spec_line} declares open_questions: [] while "
        f"{rel.rsplit('/', 1)[0]}/.memlog.md:{memlog_line} carries an unclosed "
        f"(open) or (question) entry"
    )


def gather_open_questions_reconcile(target: Path) -> tuple[Finding, ...]:
    """CAP-2: ``open_questions`` frontmatter vs companion memlog."""
    findings: list[Finding] = []
    scanned_specs = 0
    silent = 0
    fired = 0

    for spec_md in iter_spec_documents(target):
        rel = _rel_path(spec_md, target)
        memlog = spec_md.parent / ".memlog.md"
        if not memlog.is_file():
            continue

        scanned_specs += 1
        try:
            spec_text = spec_md.read_text(encoding="utf-8")
            memlog_text = memlog.read_text(encoding="utf-8")
        except OSError as exc:
            findings.append(
                Finding(
                    source=Source.STATUS_BODY_CONSISTENCY,
                    check=_CHECK_UNPARSEABLE,
                    status=DoctorStatus.WARN,
                    message=(
                        f"{rel} or its companion memlog could not be read — "
                        f"{exc.__class__.__name__}: {exc}"
                    ),
                    evidence={"path": rel},
                )
            )
            continue

        oq_count, oq_line, oq_unparseable = open_questions_frontmatter_count(spec_text)
        if oq_unparseable:
            findings.append(
                Finding(
                    source=Source.STATUS_BODY_CONSISTENCY,
                    check=_CHECK_UNPARSEABLE,
                    status=DoctorStatus.WARN,
                    message=f"{rel} open_questions frontmatter is unparseable",
                    evidence={"path": rel},
                )
            )
            continue

        unclosed = last_unclosed_memlog_question(memlog_text)
        if unclosed is None:
            silent += 1
            continue

        if oq_count > 0:
            silent += 1
            continue

        fired += 1
        spec_line = oq_line or 1
        memlog_rel = _rel_path(memlog, target)
        findings.append(
            Finding(
                source=Source.STATUS_BODY_CONSISTENCY,
                check=_CHECK_OPEN_QUESTIONS,
                status=DoctorStatus.WARN,
                message=_open_questions_message(
                    rel=rel,
                    spec_line=spec_line,
                    memlog_line=unclosed.line_no,
                ),
                evidence={
                    "path": rel,
                    "spec_line": spec_line,
                    "memlog_path": memlog_rel,
                    "memlog_line": unclosed.line_no,
                    "memlog_line_text": unclosed.line_text,
                    "open_questions_count": oq_count,
                },
            )
        )

    tier_stats = {
        "scanned_specs": scanned_specs,
        "silent": silent,
        "fired": fired,
    }
    if not findings:
        return (
            Finding(
                source=Source.STATUS_BODY_CONSISTENCY,
                check="status-body-open-questions",
                status=DoctorStatus.OK,
                message=(
                    "no open_questions/memlog contradictions across "
                    f"{scanned_specs} spec(s) with companion memlogs"
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


def _gather_all(target: Path) -> tuple[Finding, ...]:
    cap1 = gather_progress_phrase(target)
    cap2 = gather_open_questions_reconcile(target)
    cap1_warns = [f for f in cap1 if f.status != DoctorStatus.OK]
    cap2_warns = [f for f in cap2 if f.status != DoctorStatus.OK]
    if cap1_warns or cap2_warns:
        return tuple(cap1_warns + cap2_warns)
    return (
        Finding(
            source=Source.STATUS_BODY_CONSISTENCY,
            check="status-body-consistency",
            status=DoctorStatus.OK,
            message="no status/body consistency findings",
            evidence={
                **cap1[0].evidence,
                **cap2[0].evidence,
            },
        ),
    )


def gather(target: Path) -> tuple[Finding, ...]:
    """Status/body consistency gather — CAP-1 progress phrases and CAP-2 open_questions."""
    return degrade_on_exception(
        Source.STATUS_BODY_CONSISTENCY,
        "status-body-consistency",
        lambda: _gather_all(target),
    )
