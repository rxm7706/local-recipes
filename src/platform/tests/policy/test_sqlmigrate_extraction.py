"""Story 27.3 — sqlmigrate extraction fails CI when a changeset is missing (FR-23)."""

from __future__ import annotations

import re

import pytest

from db.sqlmigrate_extraction import check_extraction
from db.sqlmigrate_extraction import format_findings
from db.sqlmigrate_extraction import load_map
from db.sqlmigrate_extraction import parse_changeset_index
from db.sqlmigrate_extraction import production_migration_keys
from db.sqlmigrate_extraction import sqlmigrate_sql
from tests.policy import readers

SQLMIGRATE_STEP_RE = re.compile(
    r"^\s+-\s+name:\s*sqlmigrate extraction.*$"
    r"(?:\n^\s+.*$)*?"
    r"\n^\s+run:\s*(?P<command>.+?)\s*$",
    re.MULTILINE,
)


def test_missing_changeset_names_python_agent_platform_id() -> None:
    """Synthetic migration without a map entry reds and names the changeset."""
    findings = check_extraction(
        migration_keys=["users.0003_add_widget"],
        mapping={"users.0001_initial": 6},
        distribution="python-agent-platform",
        changeset_index={"python-agent-platform:6": "CREATE TABLE users_user ();"},
        extracted_sql={"users.0003_add_widget": "CREATE TABLE users_widget ();"},
    )
    assert findings, "unmapped migration must fail"
    message = format_findings(findings)
    assert "python-agent-platform:7" in message
    assert "users.0003_add_widget" in message


def test_matching_changeset_is_green() -> None:
    """sqlmigrate SQL covered by the mapped changeset passes."""
    sql = "CREATE TABLE users_widget (id integer);"
    findings = check_extraction(
        migration_keys=["users.0003_add_widget"],
        mapping={"users.0003_add_widget": 7},
        distribution="python-agent-platform",
        changeset_index={
            "python-agent-platform:7": (
                "--liquibase formatted sql\n"
                "--changeset python-agent-platform:7\n"
                f"{sql}\n"
            ),
        },
        extracted_sql={
            "users.0003_add_widget": (
                "BEGIN;\n-- Create model Widget\n"
                f"{sql}\nCOMMIT;\n"
            ),
        },
    )
    assert findings == []


def test_stale_sql_names_existing_changeset() -> None:
    """Mapped id present but SQL not covered → name that changeset."""
    findings = check_extraction(
        migration_keys=["users.0003_add_widget"],
        mapping={"users.0003_add_widget": 7},
        distribution="python-agent-platform",
        changeset_index={
            "python-agent-platform:7": (
                "--changeset python-agent-platform:7\nCREATE TABLE other ();\n"
            ),
        },
        extracted_sql={"users.0003_add_widget": "CREATE TABLE users_widget ();"},
    )
    assert len(findings) == 1
    assert findings[0].changeset_id == "python-agent-platform:7"
    assert "python-agent-platform:7" in format_findings(findings)


@pytest.mark.django_db
def test_live_first_party_tree_is_covered() -> None:
    """Production first-party migrations on this tree have covering changesets."""
    distribution, mapping = load_map()
    index = parse_changeset_index()
    keys = production_migration_keys()
    assert keys, "expected first-party production migrations"
    extracted = {}
    for key in keys:
        app_label, name = key.split(".", 1)
        extracted[key] = sqlmigrate_sql(app_label, name)
    findings = check_extraction(keys, mapping, distribution, index, extracted)
    assert not findings, format_findings(findings)


def test_platform_ci_sqlmigrate_step_invokes_extraction() -> None:
    """Named Platform CI step runs the extraction module (16.4 policy-lane pattern)."""
    text = readers.platform_ci_workflow_text()
    match = SQLMIGRATE_STEP_RE.search(text)
    assert match is not None, (
        "platform-ci.yml must contain a named sqlmigrate extraction step"
    )
    command = match.group("command")
    assert "db.sqlmigrate_extraction" in command, command
