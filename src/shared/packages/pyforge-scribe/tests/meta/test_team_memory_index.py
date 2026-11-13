"""Story 32.2 / spec-pyforge-scribe CAP-1 (amended 2026-11-10, FR-2) -- the team-memory index and its records agree.

`.claude/memory/MEMORY.md` is the index every session imports (root `CLAUDE.md`), and the record
files under `feedback/`, `project/` and `reference/` are what it indexes. Nothing held the two
together (audit SHOULD S7): a record could land with no index line, an index line could outlive its
record, a record could carry the flat `type:` of the architecture shorthand instead of the nested
`metadata.type` that `CaptureRecord.to_frontmatter` writes, and the index could grow past the 200
lines Claude Code reads. This guard fails naming the record, and four planted fixture trees prove it
fires on each.

Pruning stays a human decision (`.claude/memory/README.md` § When to prune): this module never
moves or deletes a record, it only says when the index and the files disagree.

The module reads the repository's `.claude/memory/`, so it is marked `live_tree`; the repository
root is resolved only inside the live test, so collecting the package half outside the repository
imports nothing from it.
"""

from __future__ import annotations

import posixpath
import re
from collections.abc import Callable
from pathlib import Path

import pytest

from pyforge.scribe.models import CAPTURE_TYPES, CaptureRecord, CaptureType, parse_capture_file

pytestmark = pytest.mark.live_tree

INDEX = "MEMORY.md"
#: Claude Code truncates an imported file past 200 lines, so the index stays under that many.
INDEX_LINE_LIMIT = 200
_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pixi.toml").is_file() and (candidate / ".claude" / "skills").is_dir():
            return candidate
    raise AssertionError("could not locate repo root (pixi.toml + .claude/skills)")


def index_findings(memory: Path) -> list[str]:
    """Every way the index and the records under `memory` disagree, one line each, naming the record."""
    lines = (memory / INDEX).read_text(encoding="utf-8").splitlines()
    findings: list[str] = []
    if len(lines) >= INDEX_LINE_LIMIT:
        findings.append(f"{INDEX} has {len(lines)} lines; it must stay under {INDEX_LINE_LIMIT}")

    records = {path.relative_to(memory).as_posix() for kind in CAPTURE_TYPES for path in (memory / kind).glob("*.md")}
    linked: dict[str, int] = {}
    for number, line in enumerate(lines, start=1):
        for target in _LINK.findall(line):
            linked.setdefault(posixpath.normpath(target), number)

    for target, number in sorted(linked.items()):
        if not (memory / target).is_file():
            findings.append(f"{INDEX} line {number} links {target}, which does not exist")
        elif target not in records:
            findings.append(
                f"{INDEX} line {number} links {target}, which is not a record under {', '.join(CAPTURE_TYPES)}"
            )
    for record in sorted(records - linked.keys()):
        findings.append(f"{record} has no line in {INDEX}")
    for record in sorted(records):
        try:
            parse_capture_file(memory / record)
        except ValueError as exc:
            findings.append(f"{record} does not parse with the nested metadata.type: {exc}")
    return findings


def test_live_team_memory_index_agrees_with_its_records() -> None:
    findings = index_findings(_repo_root() / ".claude" / "memory")
    assert not findings, "team-memory index and records disagree:\n" + "\n".join(findings)


# ---------------------------------------------------------------- fixture trees


_CLEAN: dict[CaptureType, str] = {"feedback": "a-rule", "project": "a-decision", "reference": "a-fact"}


def _record(kind: CaptureType, slug: str) -> str:
    body = f"The {slug} body."
    record = CaptureRecord(type=kind, name=slug, description=f"The {slug} description.", text=body)
    return record.to_frontmatter() + "\n" + body + "\n"


def _plant_clean_tree(root: Path) -> Path:
    memory = root / "memory"
    index = ["# Team Memory Index", ""]
    for kind, slug in _CLEAN.items():
        (memory / kind).mkdir(parents=True)
        (memory / kind / f"{slug}.md").write_text(_record(kind, slug), encoding="utf-8")
        index += [f"## {kind.title()}", "", f"- [{slug}]({kind}/{slug}.md) — The {slug} description.", ""]
    (memory / INDEX).write_text("\n".join(index) + "\n", encoding="utf-8")
    return memory


def _append_index_line(memory: Path, line: str) -> int:
    lines = (memory / INDEX).read_text(encoding="utf-8").splitlines()
    lines.append(line)
    (memory / INDEX).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(lines)


def _plant_unlinked_file(memory: Path) -> str:
    (memory / "feedback" / "orphan.md").write_text(_record("feedback", "orphan"), encoding="utf-8")
    return f"feedback/orphan.md has no line in {INDEX}"


def _plant_dangling_link(memory: Path) -> str:
    number = _append_index_line(memory, "- [gone](project/gone.md) — A record that left.")
    return f"{INDEX} line {number} links project/gone.md, which does not exist"


def _plant_flat_type_record(memory: Path) -> str:
    flat = '---\nname: "flat"\ndescription: "A flat type record."\ntype: project\n---\n\nThe flat body.\n'
    (memory / "project" / "flat.md").write_text(flat, encoding="utf-8")
    _append_index_line(memory, "- [flat](project/flat.md) — A flat type record.")
    return "project/flat.md does not parse with the nested metadata.type: invalid or missing metadata.type"


def _plant_200_line_index(memory: Path) -> str:
    lines = (memory / INDEX).read_text(encoding="utf-8").splitlines()
    lines += [""] * (INDEX_LINE_LIMIT - len(lines))
    (memory / INDEX).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return f"{INDEX} has {INDEX_LINE_LIMIT} lines; it must stay under {INDEX_LINE_LIMIT}"


def test_clean_fixture_tree_has_no_findings(tmp_path: Path) -> None:
    assert index_findings(_plant_clean_tree(tmp_path)) == []


def test_a_link_to_a_file_that_is_not_a_record_is_named(tmp_path: Path) -> None:
    memory = _plant_clean_tree(tmp_path)
    (memory / "README.md").write_text("# Team memory\n", encoding="utf-8")
    number = _append_index_line(memory, "- [readme](README.md) — The schema, not a record.")
    assert index_findings(memory) == [
        f"{INDEX} line {number} links README.md, which is not a record under {', '.join(CAPTURE_TYPES)}"
    ]


@pytest.mark.parametrize(
    "plant",
    [_plant_unlinked_file, _plant_dangling_link, _plant_flat_type_record, _plant_200_line_index],
    ids=["unlinked-file", "dangling-link", "flat-type-record", "200-line-index"],
)
def test_index_guard_names(plant: Callable[[Path], str], tmp_path: Path) -> None:
    memory = _plant_clean_tree(tmp_path)
    expected = plant(memory)
    findings = index_findings(memory)
    assert len(findings) == 1, findings
    assert findings[0].startswith(expected), findings
