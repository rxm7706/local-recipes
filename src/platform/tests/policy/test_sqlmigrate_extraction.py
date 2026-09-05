"""sqlmigrate extraction fails CI when a changeset is missing (Story 27.3 / FR-23).

Story 41.3 made the map per-distribution: a station's sequence is its own
(red-team B-1).
"""

from __future__ import annotations

import re

import pytest

from db.sqlmigrate_extraction import MigrationMap
from db.sqlmigrate_extraction import check_extraction
from db.sqlmigrate_extraction import find_unexpected_changesets
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


def _platform_map(migrations: dict[str, int]) -> MigrationMap:
    return MigrationMap(
        default="python-agent-platform",
        distributions={"python-agent-platform": migrations},
    )


def test_missing_changeset_names_python_agent_platform_id() -> None:
    """Synthetic migration without a map entry reds and names the changeset."""
    findings = check_extraction(
        migration_keys=["users.0003_add_widget"],
        migration_map=_platform_map({"users.0001_initial": 6}),
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
        migration_map=_platform_map({"users.0003_add_widget": 7}),
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
        migration_map=_platform_map({"users.0003_add_widget": 7}),
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


def test_sequences_are_owned_per_distribution() -> None:
    """A station's high seq does not push the default distribution's next id."""
    migration_map = MigrationMap(
        default="python-agent-platform",
        distributions={
            "python-agent-platform": {"users.0001_initial": 6},
            "pyforge-scribe": {},
        },
    )
    findings = check_extraction(
        migration_keys=["users.0003_add_widget"],
        migration_map=migration_map,
        changeset_index={
            "python-agent-platform:6": "CREATE TABLE users_user ();",
            # Scribe is at :40 -- the platform's next id is still :7, not :41.
            "pyforge-scribe:40": "--changeset pyforge-scribe:40\nCREATE SCHEMA s;",
        },
        extracted_sql={"users.0003_add_widget": "CREATE TABLE users_widget ();"},
    )
    assert [item.changeset_id for item in findings] == ["python-agent-platform:7"]


def test_map_declares_both_distributions() -> None:
    """The shipped map is per-distribution and registers scribe (Story 41.3)."""
    migration_map = load_map()
    assert migration_map.default == "python-agent-platform"
    assert set(migration_map.distributions) >= {
        "python-agent-platform",
        "pyforge-scribe",
    }
    assert migration_map.lookup("users.0001_initial") == ("python-agent-platform", 6)
    assert migration_map.lookup("users.9999_absent") is None


@pytest.mark.django_db
def test_live_first_party_tree_is_covered() -> None:
    """Production first-party migrations on this tree have covering changesets."""
    migration_map = load_map()
    index = parse_changeset_index()
    keys = production_migration_keys()
    assert keys, "expected first-party production migrations"
    extracted = {}
    for key in keys:
        app_label, name = key.split(".", 1)
        extracted[key] = sqlmigrate_sql(app_label, name)
    findings = check_extraction(keys, migration_map, index, extracted)
    assert not findings, format_findings(findings)


def test_hand_inserted_second_changeset_header_is_caught(tmp_path) -> None:
    """Row 8 (2026-09-04): a second `--changeset` header hand-inserted into an
    existing file must fail loud, even though it doesn't match CHANGESET_ID's
    shape and `parse_changeset_index` would never see it (first-match only)."""
    changelog = tmp_path / "changes"
    changelog.mkdir()
    name = "python-agent-platform-21-django-pyforge-0005-run-state-tenant.sql"
    path = changelog / name
    path.write_text(
        "--liquibase formatted sql\n"
        "--changeset python-agent-platform:21\n"
        "ALTER TABLE run_state ADD COLUMN tenant text;\n"
        "--changeset python-agent-platform:21-1\n"
        "COMMENT ON COLUMN run_state.tenant IS 'x';\n",
    )
    migration_map = _platform_map({"django_pyforge.0005_run_state_tenant": 21})
    bad = find_unexpected_changesets(migration_map, changelog_dir=changelog)
    assert len(bad) == 1
    assert path.name in bad[0]
    assert "python-agent-platform:21-1" in bad[0]


def test_single_correct_changeset_header_is_clean(tmp_path) -> None:
    """The common case -- one file, one header matching its own filename."""
    changelog = tmp_path / "changes"
    changelog.mkdir()
    name = "python-agent-platform-21-django-pyforge-0005-run-state-tenant.sql"
    (changelog / name).write_text(
        "--changeset python-agent-platform:21\n"
        "ALTER TABLE run_state ADD COLUMN tenant text;\n",
    )
    migration_map = _platform_map({"django_pyforge.0005_run_state_tenant": 21})
    assert find_unexpected_changesets(migration_map, changelog_dir=changelog) == []


def test_unmapped_but_legit_named_changeset_is_not_a_false_positive(tmp_path) -> None:
    """A changeset with no `migrations:` entry (DML grants, third-party, or a
    scribe infra changeset) is legitimate as long as its header matches its
    own filename -- `sqlmigrate-map.yaml`'s `migrations:` dict deliberately
    does not enumerate these (see e.g. `pyforge-scribe`'s `migrations: {}`),
    so validation must not compare against it directly."""
    changelog = tmp_path / "changes"
    changelog.mkdir()
    (changelog / "python-agent-platform-2-app-role-grants.sql").write_text(
        "--changeset python-agent-platform:2\nGRANT ALL ON SCHEMA app TO app_role;\n",
    )
    migration_map = MigrationMap(
        default="python-agent-platform",
        distributions={"python-agent-platform": {}, "pyforge-scribe": {}},
    )
    assert find_unexpected_changesets(migration_map, changelog_dir=changelog) == []


def test_live_changelog_has_no_unexpected_changesets() -> None:
    """The real changelog tree on this checkout is clean (the gate this repo
    actually runs) -- no Django/DB needed, pure filesystem + YAML."""
    migration_map = load_map()
    assert find_unexpected_changesets(migration_map) == []


def test_platform_ci_sqlmigrate_step_invokes_extraction() -> None:
    """Named Platform CI step runs the extraction module (16.4 policy-lane pattern)."""
    text = readers.platform_ci_workflow_text()
    match = SQLMIGRATE_STEP_RE.search(text)
    assert match is not None, (
        "platform-ci.yml must contain a named sqlmigrate extraction step"
    )
    command = match.group("command")
    assert "db.sqlmigrate_extraction" in command, command
