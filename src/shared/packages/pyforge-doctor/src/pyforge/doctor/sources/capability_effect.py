"""Capability effect check (Stories 21.9/21.10, ``spec-capability-effect-check``).

Story 21.9 (CAP-1): caller-outside-its-own-tests reach — joins on
``(spec-slug, CAP-N)`` via ``board.py``'s parsers, resolves code from the
citing story's ``Surface:`` line in ``epics.md``, and scans for whole-word
references outside the defining module and outside tests.

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

from ..checks.env_hygiene import _PRUNED_DIR_NAMES
from ..cli_bridge import CliBridgeError, run_git
from ..models import DoctorStatus, Finding, Source
from . import degrade_on_exception
from .board import (
    _CAP_CITATION_RE,
    _CAP_DECL_LINE_RE,
    _CAP_SECTION_HEADING_RE,
    _HEADING_RE,
    _canonical_epics,
    _cited_cap_ids_by_spec,
    _expand_cap_token,
    _parse_declared_cap_ids,
)
from .deps import STORY_HEADING_RE

__all__ = (
    "TERMINAL_SPEC_STATUSES_FOR_VERIFIED",
    "CapabilityVerifiedRow",
    "gather",
    "gather_caller_reach",
    "gather_verified_line",
    "iter_capability_verified_rows",
    "missing_verified_findings",
    "render_verified_beside_cap",
)

# Spec frontmatter statuses for which a missing ``verified:`` line on a CAP
# is reportable (Story 21.10 I/O matrix).
TERMINAL_SPEC_STATUSES_FOR_VERIFIED = frozenset({"shipped", "realized"})

_CHECK_VERIFIED = "capability-effect-verified"
_CHECK_NO_CALLER = "capability-effect-no-caller"
_CHECK_DOCUMENT_SURFACE = "capability-effect-document-surface"
_CHECK_UNREADABLE_EPICS = "capability-effect-unreadable-epics"
_CHECK_ABSENT_SURFACE = "capability-effect-absent-surface-path"
_CHECK_NO_SURFACE = "capability-effect-no-surface-line"

_SURFACE_LINE_RE = re.compile(r"^\*\*Surface:\*\*\s*(.+)$", re.MULTILINE)
_SURFACE_SYMBOL_RE = re.compile(r"`([A-Za-z_][A-Za-z0-9_]*)`")
_DECLARATION_RE_TEMPLATE = r"^\s*(?:async\s+def|def|class)\s+{}\b"
_DOCUMENT_SURFACE_SUFFIXES = (
    ".md",
    ".yaml",
    ".yml",
    ".toml",
    ".json",
    ".html",
    ".dc.html",
)

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
            except OSError, UnicodeDecodeError:
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
                    f"{spec_ref} CAP-{row.cap_n} is in a {row.spec_status!r} Spec but carries no `verified:` line"
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


def _is_test_path(path: Path) -> bool:
    parts = path.parts
    if "tests" in parts:
        return True
    name = path.name
    return name.startswith("test_") or name.endswith("_test.py")


def _is_code_reference_path(rel: str) -> bool:
    """Only Python modules count as call sites — not epics/spec prose mentions."""
    return rel.endswith(".py")


def _clean_surface_fragment(fragment: str) -> str:
    return fragment.strip().strip("`")


def _is_document_surface_fragment(fragment: str) -> bool:
    stripped = _clean_surface_fragment(fragment)
    lowered = stripped.lower()
    if lowered.startswith(("docs/", "_bmad-output/")):
        return True
    if any(lowered.endswith(suffix) for suffix in _DOCUMENT_SURFACE_SUFFIXES):
        return True
    return ".claude/skills/" in lowered and not lowered.endswith(".py")


def _strip_surface_annotation(fragment: str) -> str:
    """Drop parenthetical symbol/line annotations from one surface fragment."""
    return re.sub(r"\([^)]*\)", "", fragment).strip()


def _surface_path_token(fragment: str) -> str:
    token = _clean_surface_fragment(_strip_surface_annotation(fragment))
    token = re.sub(r":\d+.*$", "", token).strip()
    # `path.py::symbol_name` (pytest-style module::symbol addressing) names a
    # path plus a symbol, not a literal path ending in "::symbol_name" — drop
    # the suffix so the path half resolves. The digit-suffix strip above
    # doesn't catch this: `::identifier` has no digit immediately after the
    # colon.
    token = re.sub(r"::[A-Za-z_][A-Za-z0-9_]*$", "", token).strip()
    return token.strip("`")


def _named_symbols_in_fragment(fragment: str) -> set[str]:
    paren = re.search(r"\(([^)]*)\)", fragment)
    if not paren:
        return set()
    return set(_SURFACE_SYMBOL_RE.findall(paren.group(1)))


def _split_surface_fragments(surface: str) -> list[str]:
    fragments: list[str] = []
    depth = 0
    start = 0
    for idx, char in enumerate(surface):
        if char in "({":
            depth += 1
        elif char in ")}":
            depth = max(depth - 1, 0)
        elif char == "," and depth == 0:
            piece = surface[start:idx].strip()
            if piece:
                fragments.append(piece)
            start = idx + 1
    tail = surface[start:].strip()
    if tail:
        fragments.append(tail)
    return fragments


def _resolve_surface_paths(target: Path, fragment: str, *, project: str) -> list[Path]:
    token = _surface_path_token(fragment)
    if not token:
        return []
    if "**" in token or "*" in token:
        try:
            return sorted(p for p in target.glob(token) if p.exists())
        except OSError:
            return []
    candidates = [target / token]
    if project.startswith("pyforge-"):
        station = project.removeprefix("pyforge-")
        pkg_root = target / "src" / "shared" / "packages" / project / "src" / "pyforge" / station
        candidates.append(pkg_root / token)
        # Package root (not the nested src/pyforge/<station> tree) — covers a
        # Surface fragment written relative to the package itself, most often
        # its own tests/ dir (a sibling of src/, never reachable via pkg_root).
        package_root = target / "src" / "shared" / "packages" / project
        candidates.append(package_root / token)
        # The project's own BMAD planning-artifacts root — covers a Surface
        # fragment naming one of the project's own specs/epics by its
        # planning-artifacts-relative path.
        planning_root = target / "_bmad-output" / "projects" / project / "planning-artifacts"
        candidates.append(planning_root / token)
        # Same, but for a fragment naming a sibling spec by its
        # `<spec-slug>/SPEC.md` shorthand (omitting the `specs/` directory).
        candidates.append(planning_root / "specs" / token)
    for path in candidates:
        # A directory is a legitimate Surface target (e.g. a package to
        # delete, or a docs subtree) — `is_file()` alone made every directory
        # fragment a permanent false positive.
        if path.exists():
            return [path]
    return []


def _build_python_corpus(target: Path) -> dict[str, list[str]]:
    """Rel path -> source lines for bounded whole-word caller scans."""
    corpus: dict[str, list[str]] = {}
    for root in (target / "src", target / "scripts", target / ".claude" / "skills"):
        if not root.is_dir():
            continue
        try:
            paths = root.rglob("*.py")
        except OSError:
            continue
        for path in paths:
            if "__pycache__" in path.parts:
                continue
            rel = path.relative_to(target).as_posix()
            try:
                corpus[rel] = path.read_text(encoding="utf-8").splitlines()
            except OSError, UnicodeDecodeError:
                continue
    return corpus


def _external_reference_count_in_corpus(
    corpus: dict[str, list[str]],
    *,
    symbol: str,
    defining_rel_paths: set[str],
) -> int:
    decl_re = re.compile(_DECLARATION_RE_TEMPLATE.format(re.escape(symbol)))
    symbol_re = re.compile(rf"\b{re.escape(symbol)}\b")
    count = 0
    for rel, lines in corpus.items():
        if not _is_code_reference_path(rel):
            continue
        if rel in defining_rel_paths:
            for line in lines:
                if decl_re.match(line):
                    count += len(symbol_re.findall(line)) - 1
            continue
        if _is_test_path(Path(rel)):
            continue
        for line in lines:
            if decl_re.match(line):
                count += len(symbol_re.findall(line)) - 1
                continue
            if symbol_re.search(line):
                count += 1
    return count


def _git_grep_symbol_lines(
    target: Path,
    symbol: str,
    *,
    grep_cache: dict[str, list[tuple[str, str]] | None],
) -> list[tuple[str, str]] | None:
    """``[(repo-relative path, line content), ...]`` via ``run_git`` (AD-5)."""
    if symbol in grep_cache:
        return grep_cache[symbol]
    prune_pathspecs = [f":(exclude,glob)**/{name}/**" for name in sorted(_PRUNED_DIR_NAMES)]
    try:
        out = run_git(
            target,
            [
                "grep",
                "-n",
                "-w",
                "-I",
                "--untracked",
                "--no-exclude-standard",
                "--",
                symbol,
                ":(exclude,glob)**/deferred-work-ledger.md",
                *prune_pathspecs,
            ],
            ok_exit_codes=frozenset({0, 1}),
        )
    except CliBridgeError, UnicodeDecodeError:
        grep_cache[symbol] = None
        return None
    hits: list[tuple[str, str]] = []
    for line in out.splitlines():
        file_part, _, rest = line.partition(":")
        _, _, content = rest.partition(":")
        hits.append((file_part.strip(), content))
    grep_cache[symbol] = hits
    return hits


def _external_reference_count(
    target: Path,
    *,
    symbol: str,
    defining_rel_paths: set[str],
    grep_cache: dict[str, list[tuple[str, str]] | None],
    corpus_holder: list[dict[str, list[str]] | None],
) -> int:
    """Whole-word reference count outside defining modules and outside tests."""
    hits = _git_grep_symbol_lines(target, symbol, grep_cache=grep_cache)
    if hits is None:
        if corpus_holder[0] is None:
            corpus_holder[0] = _build_python_corpus(target)
        return _external_reference_count_in_corpus(
            corpus_holder[0],
            symbol=symbol,
            defining_rel_paths=defining_rel_paths,
        )
    decl_re = re.compile(_DECLARATION_RE_TEMPLATE.format(re.escape(symbol)))
    symbol_re = re.compile(rf"\b{re.escape(symbol)}\b")
    count = 0
    for rel, content in hits:
        if not _is_code_reference_path(rel):
            continue
        if rel in defining_rel_paths:
            if decl_re.match(content):
                count += len(symbol_re.findall(content)) - 1
            continue
        if _is_test_path(Path(rel)):
            continue
        if decl_re.match(content):
            count += len(symbol_re.findall(content)) - 1
            continue
        count += 1
    return count


def _caps_cited_on_spec_line(line: str, slug: str) -> set[int]:
    bare = slug.removeprefix("spec-")
    if slug not in line and bare not in line:
        return set()
    caps: set[int] = set()
    for match in _CAP_CITATION_RE.finditer(line):
        caps.update(_expand_cap_token(match))
    return caps


def _story_surface_by_cap(
    epics_text: str,
    spec_slugs: list[str],
) -> dict[tuple[str, int], str | None]:
    """Map ``(spec-slug, CAP-N)`` to the citing story's ``Surface:`` line."""
    headings = list(STORY_HEADING_RE.finditer(epics_text))
    if not headings:
        return {}
    out: dict[tuple[str, int], str | None] = {}
    for idx, match in enumerate(headings):
        block_end = headings[idx + 1].start() if idx + 1 < len(headings) else len(epics_text)
        block = epics_text[match.start() : block_end]
        surface_match = _SURFACE_LINE_RE.search(block)
        surface = surface_match.group(1).strip() if surface_match else None
        cited_caps: dict[str, set[int]] = {slug: set() for slug in spec_slugs}
        for line in block.splitlines():
            for slug in spec_slugs:
                cited_caps[slug].update(_caps_cited_on_spec_line(line, slug))
        for slug, caps in cited_caps.items():
            for cap_n in caps:
                key = (slug, cap_n)
                if surface is not None:
                    out[key] = surface
                elif key not in out:
                    out[key] = None
    return out


def _epics_prose_for_caps(epics_text: str) -> str:
    heading = _HEADING_RE.search(epics_text)
    return epics_text[heading.start() :] if heading else epics_text


def _caller_reach_findings_for_project(
    target: Path,
    *,
    project: str,
    project_dir: Path,
    grep_cache: dict[str, list[tuple[str, str]] | None],
    corpus_holder: list[dict[str, list[str]] | None],
    source: Source,
) -> tuple[Finding, ...]:
    pa = project_dir / "planning-artifacts"
    epics_path = _canonical_epics(project_dir)
    if epics_path is None:
        fallback = pa / "epics.md"
        if fallback.exists() and not fallback.is_file():
            return (
                Finding(
                    source=source,
                    check=_CHECK_UNREADABLE_EPICS,
                    status=DoctorStatus.WARN,
                    message=(
                        f"{project} epics.md is unreadable — capability caller reach cannot evaluate (not a file)"
                    ),
                    evidence={
                        "project": project,
                        "path": str(fallback),
                        "reason": "not a file",
                    },
                ),
            )
        return ()
    try:
        epics_text = epics_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return (
            Finding(
                source=source,
                check=_CHECK_UNREADABLE_EPICS,
                status=DoctorStatus.WARN,
                message=(f"{project} epics.md is unreadable — capability caller reach cannot evaluate ({exc})"),
                evidence={
                    "project": project,
                    "path": str(epics_path),
                    "reason": str(exc),
                },
            ),
        )

    spec_paths = sorted(pa.glob("specs/spec-*/SPEC.md"))
    spec_slugs = [p.parent.name for p in spec_paths]
    prose = _epics_prose_for_caps(epics_text)
    cited_by_spec = _cited_cap_ids_by_spec(prose, spec_slugs)
    surface_by_cap = _story_surface_by_cap(epics_text, spec_slugs)

    findings: list[Finding] = []
    for spec_md in spec_paths:
        slug = spec_md.parent.name
        try:
            spec_text = spec_md.read_text(encoding="utf-8")
        except OSError, UnicodeDecodeError:
            continue
        declared = _parse_declared_cap_ids(spec_text)
        cited = cited_by_spec.get(slug, set())
        for cap_n in sorted(declared & cited):
            spec_ref = f"{project}/{slug}"
            surface = surface_by_cap.get((slug, cap_n))
            if surface is None:
                findings.append(
                    Finding(
                        source=source,
                        check=_CHECK_NO_SURFACE,
                        status=DoctorStatus.WARN,
                        message=(
                            f"{spec_ref} CAP-{cap_n} is cited in epics but its citing story carries no Surface: line"
                        ),
                        evidence={
                            "project": project,
                            "spec_slug": slug,
                            "cap_n": cap_n,
                        },
                    )
                )
                continue

            fragments = _split_surface_fragments(surface)
            if not fragments:
                findings.append(
                    Finding(
                        source=source,
                        check=_CHECK_NO_SURFACE,
                        status=DoctorStatus.WARN,
                        message=(f"{spec_ref} CAP-{cap_n} has an empty Surface: line in epics"),
                        evidence={
                            "project": project,
                            "spec_slug": slug,
                            "cap_n": cap_n,
                        },
                    )
                )
                continue

            code_fragments = [
                frag
                for frag in fragments
                # Check the annotation-stripped fragment, not the raw one — a
                # doc file followed by a `(...)` annotation (e.g.
                # `` `install-matrix.md` (caveat retired) ``) doesn't END in
                # a document suffix until the annotation is removed, so the
                # raw-fragment check let it fall through as a "code" path.
                if not _is_document_surface_fragment(_strip_surface_annotation(frag))
            ]
            if not code_fragments:
                findings.append(
                    Finding(
                        source=source,
                        check=_CHECK_DOCUMENT_SURFACE,
                        status=DoctorStatus.WARN,
                        message=(
                            f"{spec_ref} CAP-{cap_n}: not applicable, document surface "
                            f"(no code module to scan for callers)"
                        ),
                        evidence={
                            "project": project,
                            "spec_slug": slug,
                            "cap_n": cap_n,
                            "surface": surface,
                        },
                    )
                )
                continue

            missing_paths: list[str] = []
            symbol_to_defining: dict[str, set[str]] = {}
            for fragment in code_fragments:
                paths = _resolve_surface_paths(target, fragment, project=project)
                if not paths:
                    token = _surface_path_token(fragment)
                    if token and "**" not in token and "*" not in token:
                        missing_paths.append(token)
                    continue
                named = _named_symbols_in_fragment(fragment)
                if not named:
                    # Whole-module surface fragments without a named symbol are
                    # intentionally skipped — CAP-1 targets declared success-
                    # criterion symbols (see spec-risk-tiered-review-depth's
                    # ``classify_review_tier`` / ``resolve_review_cycles``), not
                    # every ``def`` in a multi-thousand-line module.
                    continue
                for path in paths:
                    rel = path.relative_to(target).as_posix()
                    for symbol in named:
                        symbol_to_defining.setdefault(symbol, set()).add(rel)

            for missing in missing_paths:
                findings.append(
                    Finding(
                        source=source,
                        check=_CHECK_ABSENT_SURFACE,
                        status=DoctorStatus.WARN,
                        message=(f"{spec_ref} CAP-{cap_n} Surface: names absent path {missing!r}"),
                        evidence={
                            "project": project,
                            "spec_slug": slug,
                            "cap_n": cap_n,
                            "missing_path": missing,
                            "surface": surface,
                        },
                    )
                )

            for symbol, defining_paths in sorted(symbol_to_defining.items()):
                external = _external_reference_count(
                    target,
                    symbol=symbol,
                    defining_rel_paths=defining_paths,
                    grep_cache=grep_cache,
                    corpus_holder=corpus_holder,
                )
                if external > 0:
                    continue
                defining_display = ", ".join(sorted(defining_paths))
                findings.append(
                    Finding(
                        source=source,
                        check=_CHECK_NO_CALLER,
                        status=DoctorStatus.WARN,
                        message=(
                            f"{spec_ref} CAP-{cap_n}: `{symbol}` has no caller outside "
                            f"its own module and outside tests (bounded whole-word "
                            f"textual scan, not a call graph) — defined in "
                            f"{defining_display}"
                        ),
                        evidence={
                            "project": project,
                            "spec_slug": slug,
                            "cap_n": cap_n,
                            "symbol": symbol,
                            "defining_paths": defining_display,
                            "scan": "whole-word-textual",
                        },
                    )
                )
    return tuple(findings)


def gather_caller_reach(target: Path) -> tuple[Finding, ...]:
    """CAP-1: report symbols on cited CAP surfaces with no external callers."""
    projects_dir = target / "_bmad-output" / "projects"
    if not projects_dir.is_dir():
        return ()
    grep_cache: dict[str, list[tuple[str, str]] | None] = {}
    corpus_holder: list[dict[str, list[str]] | None] = [None]
    findings: list[Finding] = []
    for project_dir in sorted(projects_dir.iterdir()):
        if not project_dir.is_dir():
            continue
        findings.extend(
            _caller_reach_findings_for_project(
                target,
                project=project_dir.name,
                project_dir=project_dir,
                grep_cache=grep_cache,
                corpus_holder=corpus_holder,
                source=Source.CAPABILITY_EFFECT,
            )
        )
    return tuple(findings)


def gather(target: Path) -> tuple[Finding, ...]:
    """Capability-effect gather — verified-line pass plus caller reach (CAP-1/2)."""

    def _run() -> tuple[Finding, ...]:
        return gather_verified_line(target) + gather_caller_reach(target)

    return degrade_on_exception(
        Source.CAPABILITY_EFFECT,
        "capability-effect",
        _run,
    )
