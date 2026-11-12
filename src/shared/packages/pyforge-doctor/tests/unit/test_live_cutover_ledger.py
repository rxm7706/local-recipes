"""Story 57.3 (spec-pyforge-doctor:CAP-94, spec-pyforge-doctor:CAP-95, spec-pyforge-doctor:CAP-100): the live
proof that the two ledger detectors and the writer lock read the regenerated ledger and the roster.

Every other test of these three sources builds its own tree and runs in the package half
(``test_sources_frozen_path.py``, ``test_capability_ledger.py``, ``test_sources_writer_lock.py``). This module runs
them once on this repository, after control-plane Stories 121.3 and 121.4 and core-kit Story 117.2 (steward Story
121.7 regenerated the ledger from the swept Specs):

* ``frozen-path-changed`` reports ``0 frozen of N rows``, N being ``len(capabilities)`` of
  ``docs/foundry/capability-ledger.yaml``;
* ``capability-ledger`` reports no FAIL;
* ``writer-lock`` reports that this checkout is the writer;
* ``extract_caps`` returns, for each row of the heading-forms table in
  ``spec-foundry-capability-ledger/extract.md`` (the one fixture both extractors are held to), the heading that
  file's normalisation gives the row's example.

It hands the repository root to three gathers, so steward's ``ROOT_HANDOFF_INPUTS`` declares it (the Story 57.3
spec records the inputs). The root is found inside a fixture, never at import.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from pyforge.doctor.models import DoctorStatus
from pyforge.doctor.sources import capability_ledger, frozen_path, writer_lock
from pyforge.doctor.sources.capability_ledger import extract_caps

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree

_LEDGER = ("docs", "foundry", "capability-ledger.yaml")
_EXTRACT = (
    "_bmad-output",
    "projects",
    "pyforge-steward",
    "planning-artifacts",
    "specs",
    "spec-foundry-capability-ledger",
    "extract.md",
)
# extract.md § Heading forms: one bold capability number, its title inside the bold after a dash, or outside it.
_INSIDE = re.compile(r"^\s*[-*]\s+\*\*(?:[a-z]+:)?CAP-\d+\s*[—–-]\s*(?P<title>.+?)\*\*")
_OUTSIDE = re.compile(r"^\s*[-*]\s+\*\*(?:[a-z]+:)?CAP-\d+\*\*\s*[—–-]\s*(?P<title>.+)$")


@pytest.fixture(scope="module")
def repo() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "pixi.toml").is_file() and (candidate / "_bmad-output").is_dir():
            return candidate
    raise AssertionError("this module runs inside a checkout: no pixi.toml beside _bmad-output/ above it")


def _normalise(title: str) -> str:
    # extract.md § Heading forms: strip whitespace, then a trailing `.`, then a trailing `*`, then whitespace again.
    return title.strip().rstrip(".").rstrip("*").strip()


def _heading_form_examples(text: str) -> list[str]:
    """The Example cell of each row of extract.md's § Heading forms table, its first code span."""
    section = text.split("## Heading forms", 1)[1].split("\n## ", 1)[0]
    rows = [line for line in section.splitlines() if line.startswith("|")]
    header = [cell.strip() for cell in rows[0].strip("|").split("|")]
    column = header.index("Example")
    examples = []
    for row in rows[2:]:
        cell = [cell.strip() for cell in row.strip("|").split("|")][column]
        span = re.search(r"`([^`]+)`", cell)
        assert span is not None, f"a heading-forms row has no code span in its Example cell: {row!r}"
        examples.append(span.group(1))
    return examples


def test_frozen_path_changed_reads_every_row_of_the_regenerated_ledger(repo: Path) -> None:
    rows = yaml.safe_load(repo.joinpath(*_LEDGER).read_text(encoding="utf-8"))["capabilities"]
    findings = frozen_path.gather(repo)
    assert [f.status for f in findings] == [DoctorStatus.OK], [f.message for f in findings]
    assert f"0 frozen of {len(rows)} rows" in findings[0].message


def test_capability_ledger_reports_no_fail_on_the_regenerated_ledger(repo: Path) -> None:
    findings = capability_ledger.gather(repo)
    assert findings
    assert [f.message for f in findings if f.status is DoctorStatus.FAIL] == []


def test_writer_lock_reports_this_checkout_is_the_writer(repo: Path) -> None:
    findings = writer_lock.gather(repo)
    assert [f.status for f in findings] == [DoctorStatus.OK], [f.message for f in findings]
    assert "is the writer" in findings[0].message
    assert findings[0].evidence["root_of_record"] == findings[0].evidence["this"]


def test_extract_caps_reads_every_row_of_the_heading_forms_table(repo: Path) -> None:
    examples = _heading_form_examples(repo.joinpath(*_EXTRACT).read_text(encoding="utf-8"))
    assert len(examples) == 3, examples
    for example in examples:
        # The table spells one form with the placeholder number `n`; it is read as a number.
        line = re.sub(r"\bCAP-n\b", "CAP-1", example)
        hit = _INSIDE.match(line) or _OUTSIDE.match(line)
        assert hit is not None, f"the example is no heading form extract.md names: {example!r}"
        caps = extract_caps(line)
        assert [cap.heading for cap in caps] == [_normalise(hit.group("title"))], (example, caps)
