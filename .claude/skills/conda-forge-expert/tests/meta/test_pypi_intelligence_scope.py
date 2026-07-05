"""Prevent version-truth drift onto raw `pypi_intelligence` reads.

Schema v29 (cyclonedx-universe-inventory Wave A / S2, D3) ships the
`v_pypi_intelligence_valid` ORPHAN_RULE view: `pypi_intelligence` rows with
no `pypi_universe` counterpart (deleted/renamed PyPI projects — 93,390 at
2026-07-05) are never version truth. Consumers reading enrichment columns
for version-comparison purposes must read FROM the view.

Enforcement mirrors `test_actionable_scope.py`: every
`SELECT ... FROM pypi_intelligence` in the skill's `scripts/*.py` must
either read `FROM v_pypi_intelligence_valid` OR carry an inline
`# scope: <reason>` justification comment within the preceding lines
(producer-side phase stats and the orphan probe itself are the legitimate
raw readers).

Known coverage limits (shared with the model test, deliberately kept
identical to it): the string-literal-anchored regex cannot see a SELECT
whose `FROM pypi_intelligence` sits in a LATER adjacent string fragment
(`"SELECT x "  "FROM pypi_intelligence"`) or behind an f-string table
variable. All current raw reads carry `# scope:` comments regardless;
an AST-based scanner is tracked as deferred work.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"

# Same string-literal-anchored shape as test_actionable_scope.py: only match
# SELECTs that open a Python string literal, so DDL inside SCHEMA_DDL (the
# view definition itself) and prose comments don't false-positive.
_SELECT_FROM_PI = re.compile(
    r"['\"]\s*SELECT[^;\"]{0,1000}?FROM\s+pypi_intelligence\b[^;\"]{0,500}?(?=\"|;|\))",
    re.DOTALL | re.IGNORECASE,
)

_SCOPE_JUSTIFICATION = re.compile(r"#\s*scope\s*:", re.IGNORECASE)


def _line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _preceding_lines(src_lines: list[str], select_line: int, n: int = 10) -> str:
    start = max(0, select_line - 1 - n)
    end = max(0, select_line - 1)
    return "\n".join(src_lines[start:end])


@pytest.mark.meta
def test_no_undocumented_pypi_intelligence_select():
    violations = []
    for script in sorted(_SCRIPTS_DIR.glob("*.py")):
        source = script.read_text()
        src_lines = source.split("\n")
        for m in _SELECT_FROM_PI.finditer(source):
            stmt = m.group(0)
            line_no = _line_of(source, m.start())
            if "FROM v_pypi_intelligence_valid" in stmt:
                continue
            if _SCOPE_JUSTIFICATION.search(_preceding_lines(src_lines, line_no)):
                continue
            offending = stmt.replace("\n", " ").strip()[:120]
            violations.append(
                f"  {script.name}:{line_no}: `{offending}...` reads "
                f"`FROM pypi_intelligence` without a `# scope: ...` "
                f"justification. Version-truth consumers must read "
                f"`FROM v_pypi_intelligence_valid` (schema v29 ORPHAN_RULE); "
                f"producer-side/raw reads need `# scope: <reason>`."
            )
    if violations:
        pytest.fail(
            "pypi_intelligence version-truth drift detected:\n"
            + "\n".join(violations)
        )


class TestScopeCommentFormat:
    def test_recognizes_scope_comment(self):
        assert _SCOPE_JUSTIFICATION.search("    # scope: producer-side stats")

    def test_rejects_arbitrary_comments(self):
        assert not _SCOPE_JUSTIFICATION.search("    # just a note")
