"""Story 27.4 / FR-25 / canopy AD-9 — test databases still Django-migrate.

Governed production DDL (Liquibase, then ``migrate --fake``) must not capture
ephemeral test DBs. This module proves the carve-out without rewriting the
suite: live inspection of the test runner path, plus synthetic drift that
reds if settings or the runner are pointed at Liquibase or ``--fake``.
"""

from __future__ import annotations

import ast
import inspect
import re

import pytest
import pytest_django.fixtures as pytest_django_fixtures
from django.conf import settings
from django.db.backends.base.creation import BaseDatabaseCreation
from django.test.runner import DiscoverRunner

from tests.policy import readers

PLATFORM_ROOT = readers.PLATFORM_ROOT
TEST_SETTINGS = PLATFORM_ROOT / "config" / "settings" / "test.py"
CONTEST = PLATFORM_ROOT / "conftest.py"
COMPOSE = PLATFORM_ROOT / "compose" / "compose.yml"
LIQUIBASE_JOB = PLATFORM_ROOT / "deploy/charts/platform/templates/liquibase-job.yaml"
MIGRATE_JOB = PLATFORM_ROOT / "deploy/charts/platform/templates/migrate-job.yaml"

_FAKE_MIGRATE = re.compile(
    r"""(?:call_command\s*\(\s*["']migrate["'][\s\S]{0,400}fake\s*=\s*True)
        |(?:manage\.py["']?\s*,?\s*["']?migrate["']?[^\n]{0,80}--fake)
        |(?:migrate\s+--fake)""",
    re.VERBOSE,
)
_LIQUIBASE = re.compile(r"liquibase", re.IGNORECASE)


def _assert_source_is_real_django_migrate(source: str, *, label: str) -> None:
    """``create_test_db`` / runner setup must call migrate, not fake/Liquibase."""
    if _LIQUIBASE.search(source):
        pytest.fail(f"{label} pointed test DB creation at Liquibase")
    if _FAKE_MIGRATE.search(source):
        pytest.fail(f"{label} pointed test DB creation at migrate --fake")
    if not re.search(r"""call_command\s*\(\s*["']migrate["']""", source):
        pytest.fail(f"{label} no longer calls Django migrate")


def _assert_test_surface_is_not_governed_ddl(source: str, *, label: str) -> None:
    """Test settings / conftest / addopts must not opt into the production path."""
    if _LIQUIBASE.search(source):
        pytest.fail(f"{label} pointed the test runner at Liquibase")
    if _FAKE_MIGRATE.search(source) or re.search(r"migrate[^\n]*--fake", source):
        pytest.fail(f"{label} pointed the test runner at migrate --fake")


def _assert_pytest_addopts_keeps_migrations(addopts: str) -> None:
    _assert_test_surface_is_not_governed_ddl(addopts, label="pytest addopts")
    if re.search(r"(^|\s)--nomigrations(\s|$)", addopts):
        pytest.fail(
            "pytest addopts enables --nomigrations (test DBs would skip migrate)",
        )


def _assert_compose_uses_real_migrate(source: str) -> None:
    if "manage.py migrate" not in source:
        pytest.fail("compose local platform command no longer runs manage.py migrate")
    platform_cmd = source
    if "bash -c" in source:
        start = source.index("bash -c")
        platform_cmd = source[start : start + 400]
    if re.search(r"migrate\s+--fake", platform_cmd) or "--fake" in platform_cmd:
        pytest.fail("compose local migrate uses --fake (production Job leak)")


def _assert_production_jobs_stay_27_2(liquibase_yaml: str, migrate_yaml: str) -> None:
    if 'helm.sh/hook-weight: "-1"' not in liquibase_yaml:
        pytest.fail("liquibase Job hook-weight is no longer -1")
    if "db/liquibase_update.py" not in liquibase_yaml:
        pytest.fail("liquibase Job no longer runs db/liquibase_update.py")
    if "--fake" not in migrate_yaml:
        pytest.fail("Helm migrate Job dropped --fake (27.2 contract)")
    if "manage.py" not in migrate_yaml or "migrate" not in migrate_yaml:
        pytest.fail("Helm migrate Job no longer runs manage.py migrate")


def _declared_test_runner(source: str) -> str:
    module = ast.parse(source)
    for node in module.body:
        if isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if "TEST_RUNNER" in names and isinstance(node.value, ast.Constant):
                value = node.value.value
                if isinstance(value, str):
                    return value
    pytest.fail("TEST_RUNNER assignment missing from test settings")
    raise AssertionError  # pragma: no cover -- pytest.fail always raises


def test_discover_runner_still_owns_manage_py_test() -> None:
    """``manage.py test`` uses Django DiscoverRunner, not a Liquibase runner."""
    assert settings.TEST_RUNNER == "django.test.runner.DiscoverRunner"
    source = TEST_SETTINGS.read_text(encoding="utf-8")
    assert _declared_test_runner(source) == "django.test.runner.DiscoverRunner"
    assert DiscoverRunner.__module__ == "django.test.runner"
    _assert_test_surface_is_not_governed_ddl(source, label="config/settings/test.py")
    _assert_test_surface_is_not_governed_ddl(
        CONTEST.read_text(encoding="utf-8"),
        label="conftest.py",
    )


def test_create_test_db_calls_migrate_not_fake() -> None:
    """Django test DB creation still ``call_command('migrate')`` without fake."""
    source = inspect.getsource(BaseDatabaseCreation.create_test_db)
    _assert_source_is_real_django_migrate(source, label="create_test_db")
    for alias, db_settings in settings.DATABASES.items():
        migrate_flag = db_settings.get("TEST", {}).get("MIGRATE", True)
        assert migrate_flag is not False, (
            f"DATABASES[{alias!r}]['TEST']['MIGRATE'] is False — "
            "test DBs would skip Django migrate"
        )


def test_pytest_django_setup_databases_keeps_migrations() -> None:
    """pytest Django test DB creation still goes through ``setup_databases``."""
    source = inspect.getsource(pytest_django_fixtures.django_db_setup)
    if _LIQUIBASE.search(source):
        pytest.fail("pytest-django django_db_setup pointed test DBs at Liquibase")
    if _FAKE_MIGRATE.search(source):
        pytest.fail("pytest-django django_db_setup pointed test DBs at migrate --fake")
    assert "setup_databases" in source
    addopts = (
        readers.platform_pyproject()
        .get("tool", {})
        .get("pytest", {})
        .get("ini_options", {})
        .get("addopts", "")
    )
    if not isinstance(addopts, str):
        addopts = " ".join(addopts)
    _assert_pytest_addopts_keeps_migrations(addopts)
    assert "--ds=config.settings.test" in addopts


def test_compose_local_still_runs_real_migrate() -> None:
    """Local compose is not the Helm fake-after-Liquibase path."""
    _assert_compose_uses_real_migrate(COMPOSE.read_text(encoding="utf-8"))


def test_helm_jobs_remain_liquibase_then_fake_migrate() -> None:
    """Production path stays 27.2; this story must not rewrite the Jobs."""
    _assert_production_jobs_stay_27_2(
        LIQUIBASE_JOB.read_text(encoding="utf-8"),
        MIGRATE_JOB.read_text(encoding="utf-8"),
    )


def test_policy_reds_when_test_runner_points_at_liquibase() -> None:
    with pytest.raises(pytest.fail.Exception, match="Liquibase"):
        _assert_test_surface_is_not_governed_ddl(
            'TEST_RUNNER = "platform.runners.LiquibaseTestRunner"\n',
            label="synthetic test settings",
        )


def test_policy_reds_when_test_path_uses_fake_migrate() -> None:
    with pytest.raises(pytest.fail.Exception, match="--fake"):
        _assert_source_is_real_django_migrate(
            'call_command("migrate", fake=True, interactive=False)\n',
            label="synthetic create_test_db",
        )
    with pytest.raises(pytest.fail.Exception, match="--fake"):
        _assert_test_surface_is_not_governed_ddl(
            'args = ["python", "manage.py", "migrate", "--fake"]\n',
            label="synthetic test settings",
        )


def test_policy_reds_when_pytest_disables_migrations() -> None:
    with pytest.raises(pytest.fail.Exception, match="nomigrations"):
        _assert_pytest_addopts_keeps_migrations(
            "--ds=config.settings.test --nomigrations --reuse-db",
        )


def test_policy_reds_when_helm_drops_fake() -> None:
    liquibase = LIQUIBASE_JOB.read_text(encoding="utf-8")
    migrate = MIGRATE_JOB.read_text(encoding="utf-8").replace("--fake", "")
    with pytest.raises(pytest.fail.Exception, match="--fake"):
        _assert_production_jobs_stay_27_2(liquibase, migrate)
