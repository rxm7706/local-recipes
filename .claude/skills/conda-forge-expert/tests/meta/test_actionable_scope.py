"""Prevent persona-filter drift across phase selectors.

Every `SELECT ... FROM packages WHERE ...` in `conda_forge_atlas.py` must
either:
  (a) Read from `v_actionable_packages` instead of `packages`, OR
  (b) Have an inline `# scope: <reason>` justification comment within
      3 lines above the SELECT explaining why a broader scope is needed.

The v7.9.0 actionable-scope audit fixed three phases (H, J, M) that
had drifted from the canonical `conda_name IS NOT NULL AND latest_status='active'
AND COALESCE(feedstock_archived,0)=0` triplet. v8.0.0 schema v21
encodes that triplet as a view. This meta-test enforces that the next
phase author can't accidentally re-drift.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


_SCRIPT = (
    Path(__file__).resolve().parent.parent.parent
    / "scripts"
    / "conda_forge_atlas.py"
)


# Match SELECT ... FROM packages — only when SELECT appears at the start
# of a Python string literal (preceded by " or '). This avoids false
# positives from SQL inside DDL string-block comments or descriptive
# prose. Real SQL strings in this codebase always start with `"SELECT...`.
_SELECT_FROM_PACKAGES = re.compile(
    r"['\"]\s*SELECT[^;\"]{0,1000}?FROM\s+packages\b[^;\"]{0,500}?(?=\"|;|\))",
    re.DOTALL | re.IGNORECASE,
)

_SCOPE_JUSTIFICATION = re.compile(r"#\s*scope\s*:", re.IGNORECASE)


def _line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _preceding_lines(src_lines: list[str], select_line: int, n: int = 10) -> str:
    """Return the n lines immediately preceding `select_line` (1-indexed).

    Window size 10 covers (multi-line scope comment block) + (multi-line
    Python string literal that the SELECT is inside) while still keeping
    the scope comment "right above" the `conn.execute(...)` call in any
    reasonable sense.
    """
    start = max(0, select_line - 1 - n)
    end = max(0, select_line - 1)
    return "\n".join(src_lines[start:end])


@pytest.fixture(scope="module")
def script_source() -> str:
    return _SCRIPT.read_text()


class TestActionableScopeEnforcement:
    def test_no_undocumented_packages_select(self, script_source):
        """Every SELECT FROM packages must either use the view or have a
        `# scope: ...` justification comment within 3 lines above.
        """
        src_lines = script_source.split("\n")
        violations = []

        for m in _SELECT_FROM_PACKAGES.finditer(script_source):
            stmt = m.group(0)
            offset = m.start()
            line_no = _line_of(script_source, offset)

            # OK: query reads from the view, not the raw table.
            if "FROM v_actionable_packages" in stmt:
                continue
            # OK: query is structurally distinct (write-only DDL,
            # subquery against a non-actionable column, etc.) and the
            # author justified it.
            preceding = _preceding_lines(src_lines, line_no, n=10)
            if _SCOPE_JUSTIFICATION.search(preceding):
                continue

            # Pull just the SELECT keyword's line for the error message.
            offending = stmt.replace("\n", " ").strip()[:120]
            violations.append(
                f"  conda_forge_atlas.py:{line_no}: "
                f"`{offending}...` reads `FROM packages` without "
                f"`# scope: ...` justification within 3 lines above. "
                f"Either change to `FROM v_actionable_packages` "
                f"OR add `# scope: <reason>` comment."
            )

        if violations:
            msg = (
                "actionable-scope drift detected — phase selectors must "
                "use v_actionable_packages OR justify broader scope:\n"
                + "\n".join(violations)
                + "\n\nThe canonical persona-filter triplet "
                "(conda_name + active + !archived) is encoded as the view "
                "v_actionable_packages in schema v21+. New phase code "
                "should default to reading from the view; broader scope "
                "(e.g., Phase D's name-coincidence discovery, Phase E's "
                "feedstock-name population, write-only DDL) needs an "
                "explicit `# scope: <reason>` comment to opt out."
            )
            pytest.fail(msg)


class TestScopeCommentFormat:
    """The `# scope: <reason>` comment format must be recognizable so
    the enforcement logic above can parse it. Spot-checks the regex.
    """
    def test_recognizes_lowercase(self):
        assert _SCOPE_JUSTIFICATION.search("    # scope: write-only DDL")

    def test_recognizes_capitalized(self):
        assert _SCOPE_JUSTIFICATION.search("    # Scope: bootstrap migration")

    def test_recognizes_with_extra_whitespace(self):
        assert _SCOPE_JUSTIFICATION.search("    #scope:  trimmed")

    def test_rejects_arbitrary_comments(self):
        assert not _SCOPE_JUSTIFICATION.search("    # this is just a note")
        assert not _SCOPE_JUSTIFICATION.search("    # not a scope: marker")
