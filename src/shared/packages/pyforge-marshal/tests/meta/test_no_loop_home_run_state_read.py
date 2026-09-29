"""Story 33.12 CAP-4 — forbid untagged loop-home run-state reads outside the publisher."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pyforge.marshal

_PACKAGE_FILE = pyforge.marshal.__file__
if _PACKAGE_FILE is None:
    raise ValueError("installed package has no __file__")
MARSHAL_SRC = Path(_PACKAGE_FILE).resolve().parent
DOCTOR_MARSHAL = MARSHAL_SRC.parents[3] / "pyforge-doctor" / "src" / "pyforge" / "doctor" / "sources" / "marshal.py"
PUBLISHER_ADAPTER = MARSHAL_SRC / "adapters" / "publisher_host.py"
CAP4_TAG = "CAP-4: loop-home FILE read"
_FORBIDDEN = (
    re.compile(r"\.bmad-loops"),
    re.compile(r"\.bmad-loop/runs"),
    re.compile(r"state\.json"),
    re.compile(r"journal\.jsonl"),
)


def _docstring_lines(source: str) -> set[int]:
    tree = ast.parse(source)
    lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if hasattr(node, "lineno") and hasattr(node, "end_lineno"):
                end = node.end_lineno or node.lineno
                lines.update(range(node.lineno, end + 1))
    return lines


def _tagged_lines(lines: list[str]) -> set[int]:
    tagged: set[int] = set()
    for index, line in enumerate(lines):
        if CAP4_TAG in line:
            tagged.add(index + 1)
            if index + 1 < len(lines):
                tagged.add(index + 2)
    return tagged


def _scan_file(path: Path) -> list[str]:
    if path.resolve() == PUBLISHER_ADAPTER.resolve():
        return []
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()
    doc_lines = _docstring_lines(source)
    tagged = _tagged_lines(lines)
    offenders: list[str] = []
    for line_no, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if line_no in doc_lines:
            continue
        if line_no in tagged:
            continue
        if "help=" in line or "Help(" in line:
            continue
        for pattern in _FORBIDDEN:
            if pattern.search(line):
                rel = path
                offenders.append(f"{rel}:{line_no}: {stripped}")
                break
    return offenders


def _marshal_sources() -> list[Path]:
    return sorted(MARSHAL_SRC.rglob("*.py"))


def test_no_untagged_loop_home_run_state_reads_in_marshal_src() -> None:
    offenders: list[str] = []
    for path in _marshal_sources():
        offenders.extend(_scan_file(path))
    assert offenders == []


def test_doctor_marshal_story_status_fallback_is_tagged() -> None:
    offenders = _scan_file(DOCTOR_MARSHAL)
    assert offenders == []


def test_forbidden_patterns_match_run_state_glob_line() -> None:
    line = 'for state in sorted(home.glob(".bmad-loop/runs/*/state.json")):'
    assert any(pattern.search(line) for pattern in _FORBIDDEN)
