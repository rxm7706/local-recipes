"""Story-spec frontmatter duplicate-key gather (Story 42.1, CAP-81 / CAP-86).

Reads every tracked story spec
(``git ls-files`` matching ``_bmad-output/projects/*/planning-artifacts/specs/spec-*.md``),
bounds each frontmatter block with the same CAP-81 fence reader as
``chain._frontmatter_parse_text``, and loads the block with a
``yaml.SafeLoader`` subclass that records repeated mapping keys at any depth.

Each duplicated key is one FAIL ``frontmatter-duplicate-key`` finding. An
unbounded or unloadable block is one WARN ``frontmatter-unreadable`` -- never
a silent pass.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml
from yaml.nodes import MappingNode, ScalarNode

from ..cli_bridge import CliBridgeError, run_git
from ..models import DoctorStatus, Finding, Source
from . import chain, degrade_on_exception

__all__ = ("gather",)

_CHECK_DUPLICATE = "frontmatter-duplicate-key"
_CHECK_UNREADABLE = "frontmatter-unreadable"
_STORY_SPEC_RE = re.compile(
    r"^_bmad-output/projects/[^/]+/planning-artifacts/specs/spec-.*\.md$"
)


@dataclass(frozen=True)
class _KeyOccurrence:
    line: int
    value: str


@dataclass(frozen=True)
class _DuplicateKey:
    dotted_path: str
    occurrences: tuple[_KeyOccurrence, ...]


def _format_yaml_value(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return value
    return yaml.safe_dump(value, default_flow_style=True).strip()


def _yaml_block_start_line(text: str) -> int | None:
    """1-based line number of the first YAML line inside the opening fence."""
    prefix_len = len(text) - len(chain._skip_leading_banner(text))
    open_line = text[:prefix_len].count("\n") + 1
    skipped_lines = chain._skip_leading_banner(text).splitlines()
    if not skipped_lines or not chain._is_fence(skipped_lines[0]):
        return None
    return open_line + 1


def _compose_frontmatter_block(block_text: str) -> yaml.nodes.Node | None:
    try:
        return yaml.compose(block_text)
    except yaml.YAMLError:
        return None


class _OccurrenceLoader(yaml.SafeLoader):
    """Constructs YAML while ``_scan_mapping`` walks the node tree."""


def _scan_mapping(
    loader: yaml.SafeLoader,
    node: MappingNode,
    prefix: tuple[str, ...],
    yaml_start_line: int,
    out: list[_DuplicateKey],
) -> None:
    groups: dict[str, list[tuple[int, yaml.nodes.Node]]] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=False)
        key_name = str(key)
        line = yaml_start_line + key_node.start_mark.line
        groups.setdefault(key_name, []).append((line, value_node))

    for key_name, entries in groups.items():
        dotted = ".".join((*prefix, key_name)) if prefix else key_name
        if len(entries) > 1:
            occs = tuple(
                _KeyOccurrence(
                    line=line,
                    value=_format_yaml_value(loader.construct_object(vn, deep=False)),
                )
                for line, vn in entries
            )
            out.append(_DuplicateKey(dotted_path=dotted, occurrences=occs))
        for _line, value_node in entries:
            if isinstance(value_node, MappingNode):
                _scan_mapping(loader, value_node, (*prefix, key_name), yaml_start_line, out)
            elif isinstance(value_node, yaml.SequenceNode):
                for item in value_node.value:
                    if isinstance(item, MappingNode):
                        _scan_mapping(loader, item, prefix, yaml_start_line, out)


def _find_duplicate_keys(block_text: str, yaml_start_line: int) -> list[_DuplicateKey] | None:
    root = _compose_frontmatter_block(block_text)
    if root is None:
        return None
    if not isinstance(root, MappingNode):
        return None
    loader = _OccurrenceLoader(block_text)
    duplicates: list[_DuplicateKey] = []
    _scan_mapping(loader, root, (), yaml_start_line, duplicates)
    return duplicates


def _blame_commit_time(target: Path, rel: str, line: int) -> int | None:
    try:
        out = run_git(
            target,
            [
                "blame",
                "-L",
                f"{line},{line}",
                "--porcelain",
                "--",
                rel,
            ],
        )
    except (CliBridgeError, UnicodeDecodeError):
        return None
    for row in out.splitlines():
        if row.startswith("author-time "):
            try:
                return int(row.split()[1])
            except (IndexError, ValueError):
                return None
    return None


def _keep_line(occurrences: tuple[_KeyOccurrence, ...], target: Path, rel: str) -> int:
    scored = []
    for occ in occurrences:
        ts = _blame_commit_time(target, rel, occ.line)
        scored.append((ts if ts is not None else -1, occ.line))
    scored.sort()
    return scored[-1][1]


def _duplicate_message(
    rel: str,
    dup: _DuplicateKey,
    *,
    keep_line: int,
) -> str:
    parts = [
        f"{rel}: frontmatter key {dup.dotted_path!r} appears "
        f"{len(dup.occurrences)} times"
    ]
    for occ in dup.occurrences:
        parts.append(f"line {occ.line}={occ.value!r}")
    delete_lines = [str(occ.line) for occ in dup.occurrences if occ.line != keep_line]
    parts.append(
        f"keep line {keep_line} (last in git blame) and delete line(s) {', '.join(delete_lines)}"
    )
    return "; ".join(parts)


def _iter_tracked_story_specs(target: Path) -> tuple[str, ...]:
    tracked = chain._tracked_files(target)
    if tracked is None:
        return ()
    return tuple(sorted(path for path in tracked if _STORY_SPEC_RE.match(path)))


def _gather_all(target: Path) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    for rel in _iter_tracked_story_specs(target):
        path = target / rel
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            findings.append(
                Finding(
                    source=Source.FRONTMATTER_DUPLICATE_KEYS,
                    check=_CHECK_UNREADABLE,
                    status=DoctorStatus.WARN,
                    message=f"{rel}: cannot read story spec ({exc})",
                    evidence={"path": rel},
                )
            )
            continue

        lines = chain._fenced_lines(text)
        split = chain._split_fenced_block(lines)
        if split is None:
            continue  # no frontmatter block

        block_lines, _body, closed = split
        if not closed:
            findings.append(
                Finding(
                    source=Source.FRONTMATTER_DUPLICATE_KEYS,
                    check=_CHECK_UNREADABLE,
                    status=DoctorStatus.WARN,
                    message=f"{rel}: frontmatter fence never closes",
                    evidence={"path": rel},
                )
            )
            continue

        yaml_start = _yaml_block_start_line(text)
        if yaml_start is None:
            findings.append(
                Finding(
                    source=Source.FRONTMATTER_DUPLICATE_KEYS,
                    check=_CHECK_UNREADABLE,
                    status=DoctorStatus.WARN,
                    message=f"{rel}: frontmatter block could not be bounded",
                    evidence={"path": rel},
                )
            )
            continue

        block_text = "\n".join(block_lines) + "\n"
        duplicates = _find_duplicate_keys(block_text, yaml_start)
        if duplicates is None:
            findings.append(
                Finding(
                    source=Source.FRONTMATTER_DUPLICATE_KEYS,
                    check=_CHECK_UNREADABLE,
                    status=DoctorStatus.WARN,
                    message=f"{rel}: frontmatter block does not load as YAML",
                    evidence={"path": rel},
                )
            )
            continue

        for dup in duplicates:
            keep = _keep_line(dup.occurrences, target, rel)
            findings.append(
                Finding(
                    source=Source.FRONTMATTER_DUPLICATE_KEYS,
                    check=_CHECK_DUPLICATE,
                    status=DoctorStatus.FAIL,
                    message=_duplicate_message(rel, dup, keep_line=keep),
                    evidence={
                        "path": rel,
                        "key": dup.dotted_path,
                        "lines": [occ.line for occ in dup.occurrences],
                        "values": [occ.value for occ in dup.occurrences],
                        "keep_line": keep,
                    },
                )
            )

    if findings:
        return tuple(findings)

    return (
        Finding(
            source=Source.FRONTMATTER_DUPLICATE_KEYS,
            check=_CHECK_DUPLICATE,
            status=DoctorStatus.OK,
            message="every tracked story spec carries each frontmatter key once",
            evidence={"story_spec_count": len(_iter_tracked_story_specs(target))},
        ),
    )


def gather(target: Path) -> tuple[Finding, ...]:
    """Duplicate frontmatter keys in tracked story specs (Story 42.1)."""
    return degrade_on_exception(
        Source.FRONTMATTER_DUPLICATE_KEYS,
        _CHECK_DUPLICATE,
        lambda: _gather_all(target),
    )
