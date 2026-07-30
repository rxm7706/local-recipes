"""Unit tests for query_atlas's SQL-fragment validation — AUD-CFE-005.

`select` / `order_by` / `where` are interpolated into the SQL string (they are
identifiers and clauses, so they cannot be bound as parameters). The finding was
that `order_by` was unvalidated entirely and the other two were guarded only by a
substring keyword scan.

These tests exercise `_validate_atlas_fragments` directly rather than
`query_atlas`, so they do not need a built `cf_atlas.db`.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SERVER = (
    Path(__file__).resolve().parents[4] / "tools" / "conda_forge_server.py"
)


@pytest.fixture(scope="module")
def server():
    spec = importlib.util.spec_from_file_location("cfe_mcp_server_under_test", SERVER)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["cfe_mcp_server_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


DEFAULT_SELECT = (
    "conda_name, latest_conda_version, total_downloads, "
    "vuln_critical_affecting_current, latest_status"
)


def check(server, select=DEFAULT_SELECT, order_by="total_downloads DESC", where=None):
    return server._validate_atlas_fragments(select, order_by, where)


class TestAccepted:
    def test_the_tools_own_defaults(self, server):
        assert check(server) is None

    @pytest.mark.parametrize(
        "select",
        [
            "*",
            "conda_name",
            "p.conda_name, p.latest_status",
            "conda_name AS name",
            "COUNT(*)",
            "COUNT(*) AS n",
            "COUNT(DISTINCT conda_name)",
            "MAX(total_downloads), MIN(total_downloads)",
            "COALESCE(feedstock_archived, 0) AS archived",
            "ROUND(vuln_max_epss_score, 2) AS epss",
            "LOWER(conda_name), UPPER(latest_status)",
        ],
    )
    def test_select_shapes(self, server, select):
        assert check(server, select=select) is None, select

    @pytest.mark.parametrize(
        "order_by",
        [
            "total_downloads DESC",
            "conda_name",
            "conda_name ASC, total_downloads DESC",
            "p.total_downloads DESC",
            "2 DESC",
            "total_downloads DESC NULLS LAST",
        ],
    )
    def test_order_by_shapes(self, server, order_by):
        assert check(server, order_by=order_by) is None, order_by

    @pytest.mark.parametrize(
        "where",
        [
            "latest_status = 'active'",
            "vuln_critical_affecting_current > 0 AND (feedstock_archived = 0 OR feedstock_archived IS NULL)",
            "conda_name LIKE 'tree-sitter-%'",
            # The docstring advertises side tables via subquery; keep it working.
            "conda_name IN (SELECT conda_name FROM dependencies WHERE depends_on = 'numpy')",
            "total_downloads BETWEEN 100 AND 200",
        ],
    )
    def test_where_keeps_documented_subquery_capability(self, server, where):
        assert check(server, where=where) is None, where

    def test_column_containing_a_keyword_substring_is_not_rejected(self, server):
        """The old substring scan false-positived on `updated_at` (contains UPDATE)."""
        assert check(server, select="updated_at, deleted_flag") is None
        assert check(server, order_by="updated_at DESC") is None
        assert check(server, where="updated_at > 0") is None


class TestRejected:
    @pytest.mark.parametrize("field", ["select", "order_by", "where"])
    def test_statement_separator(self, server, field):
        err = check(server, **{field: "conda_name; DROP TABLE packages"})
        assert err and "separator" in err

    @pytest.mark.parametrize("field", ["select", "order_by", "where"])
    def test_sql_comment(self, server, field):
        assert check(server, **{field: "conda_name -- rest"})
        assert check(server, **{field: "conda_name /* rest */"})

    @pytest.mark.parametrize("field", ["select", "order_by", "where"])
    def test_null_byte(self, server, field):
        err = check(server, **{field: "conda_name\0"})
        assert err and "null byte" in err

    @pytest.mark.parametrize(
        "keyword",
        ["ATTACH", "DETACH", "PRAGMA", "VACUUM", "DROP", "DELETE", "INSERT",
         "UPDATE", "ALTER", "CREATE", "REINDEX", "LOAD_EXTENSION"],
    )
    def test_write_and_ddl_keywords_in_where(self, server, keyword):
        err = check(server, where=f"1=1 {keyword} x")
        assert err and "disallowed SQL keyword" in err

    def test_keyword_match_is_case_insensitive(self, server):
        assert check(server, where="1=1 aTtAcH y")

    def test_order_by_subquery_rejected(self, server):
        """The headline gap: order_by was interpolated with no validation."""
        err = check(server, order_by="(SELECT conda_name FROM packages LIMIT 1)")
        assert err and "order_by must be" in err

    def test_order_by_arbitrary_expression_rejected(self, server):
        assert check(server, order_by="CASE WHEN 1 THEN 2 ELSE 3 END")

    def test_order_by_function_call_rejected(self, server):
        assert check(server, order_by="RANDOM()")

    def test_select_subquery_rejected(self, server):
        err = check(server, select="(SELECT sqlite_version())")
        assert err and "select must be" in err

    def test_select_union_smuggling_rejected(self, server):
        assert check(server, select="conda_name FROM sqlite_master UNION SELECT 1")

    def test_select_unknown_function_rejected(self, server):
        """Only the read-only helper allowlist is permitted."""
        assert check(server, select="readfile('/etc/passwd')")

    def test_select_nested_function_rejected(self, server):
        assert check(server, select="COUNT(readfile('/etc/passwd'))")

    def test_empty_select_rejected(self, server):
        assert check(server, select="")

    def test_empty_order_by_rejected(self, server):
        assert check(server, order_by="")
