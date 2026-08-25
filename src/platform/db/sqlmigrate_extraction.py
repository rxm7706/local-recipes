"""CI gate: every first-party production migration has a Liquibase changeset (FR-23).

Canopy AD-9: ``sqlmigrate`` extraction is the check that a changeset exists
for every production migration. Changeset ids stay ``distribution:seq``
(this tree: ``python-agent-platform:N``). Story 27.2 owns the Job contract
and the :1/:2 changelog files; this module does not rewrite them.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Mapping

DB_ROOT = Path(__file__).resolve().parent
CHANGELOG_DIR = DB_ROOT / "changelog" / "changes"
MAP_PATH = DB_ROOT / "sqlmigrate-map.yaml"
CHANGESET_LINE = re.compile(r"^--changeset\s+(\S+)", re.MULTILINE)
CHANGESET_ID = re.compile(r"^([a-z0-9][a-z0-9.-]*):([1-9][0-9]*)$")
BEGIN_COMMIT = re.compile(r"^\s*(BEGIN|COMMIT)\s*;\s*$", re.IGNORECASE)
SQL_COMMENT = re.compile(r"^\s*--")
TEST_ONLY_APPS = frozenset(
    {"probe_portal", "workclass_probe"},
)
FIRST_PARTY_MARKERS = (
    "/src/platform/",
    "/src/shared/packages/django-",
)


@dataclass(frozen=True)
class Finding:
    """One failed migration → the changeset id CI must name."""

    migration: str
    changeset_id: str
    reason: str

    def line(self) -> str:
        return (
            f"missing changeset {self.changeset_id} "
            f"(migration {self.migration}: {self.reason})"
        )


def normalize_sql(sql: str) -> str:
    """Drop transaction wrappers and comments; collapse whitespace."""
    kept: list[str] = []
    for raw in sql.splitlines():
        line = raw.strip()
        if not line or BEGIN_COMMIT.match(line) or SQL_COMMENT.match(line):
            continue
        kept.append(line)
    return re.sub(r"\s+", " ", " ".join(kept)).strip().lower()


def statements_covered(extracted: str, changeset_sql: str) -> bool:
    """True when every extracted statement appears in the changeset body."""
    needle = normalize_sql(extracted)
    haystack = normalize_sql(changeset_sql)
    if not needle:
        return True
    return needle in haystack


def parse_changeset_index(changelog_dir: Path = CHANGELOG_DIR) -> dict[str, str]:
    """Map ``distribution:seq`` → file body for formatted SQL changesets."""
    index: dict[str, str] = {}
    for path in sorted(changelog_dir.glob("*.sql")):
        text = path.read_text(encoding="utf-8")
        match = CHANGESET_LINE.search(text)
        if match is None:
            continue
        changeset_id = match.group(1)
        if not CHANGESET_ID.match(changeset_id):
            continue
        index[changeset_id] = text
    return index


def load_map(path: Path = MAP_PATH) -> tuple[str, dict[str, int]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    distribution = str(data.get("distribution") or "python-agent-platform")
    raw = data.get("migrations") or {}
    mapping = {str(key): int(value) for key, value in raw.items()}
    return distribution, mapping


def expected_changeset_id(
    migration_key: str,
    mapping: Mapping[str, int],
    distribution: str,
    used_seqs: Iterable[int],
) -> str:
    if migration_key in mapping:
        return f"{distribution}:{mapping[migration_key]}"
    nxt = max(used_seqs, default=0) + 1
    return f"{distribution}:{nxt}"


def is_first_party_migration_module(module_file: str) -> bool:
    normalized = module_file.replace("\\", "/")
    return any(marker in normalized for marker in FIRST_PARTY_MARKERS)


def production_migration_keys() -> list[str]:
    """First-party production migrations from Django's loader (no test-only apps)."""
    from django.db import connection  # noqa: PLC0415
    from django.db.migrations.loader import MigrationLoader  # noqa: PLC0415

    loader = MigrationLoader(connection, ignore_no_migrations=True)
    keys: list[str] = []
    for app_label, name in sorted(loader.disk_migrations):
        if app_label in TEST_ONLY_APPS:
            continue
        migration = loader.disk_migrations[(app_label, name)]
        module = sys.modules.get(migration.__module__)
        filename = getattr(module, "__file__", "") or ""
        if not is_first_party_migration_module(filename):
            continue
        keys.append(f"{app_label}.{name}")
    return keys


def sqlmigrate_sql(app_label: str, name: str) -> str:
    from django.core.management import call_command  # noqa: PLC0415

    buffer = StringIO()
    call_command("sqlmigrate", app_label, name, stdout=buffer)
    return buffer.getvalue()


def check_extraction(
    migration_keys: Iterable[str],
    mapping: Mapping[str, int],
    distribution: str,
    changeset_index: Mapping[str, str],
    extracted_sql: Mapping[str, str],
) -> list[Finding]:
    used = list(mapping.values())
    for changeset_id in changeset_index:
        match = CHANGESET_ID.match(changeset_id)
        if match is not None:
            used.append(int(match.group(2)))
    findings: list[Finding] = []
    for key in migration_keys:
        changeset_id = expected_changeset_id(key, mapping, distribution, used)
        if key not in mapping:
            findings.append(
                Finding(key, changeset_id, "no sqlmigrate-map.yaml entry"),
            )
            continue
        body = changeset_index.get(changeset_id)
        if body is None:
            findings.append(
                Finding(key, changeset_id, "changeset id not in changelog"),
            )
            continue
        sql = extracted_sql.get(key, "")
        if not statements_covered(sql, body):
            findings.append(
                Finding(key, changeset_id, "sqlmigrate SQL not covered"),
            )
    return findings


def format_findings(findings: list[Finding]) -> str:
    lines = [
        "sqlmigrate extraction failed; missing changeset(s):",
        *(f"  {item.line()}" for item in findings),
    ]
    return "\n".join(lines) + "\n"


def run_live_check() -> int:
    distribution, mapping = load_map()
    index = parse_changeset_index()
    keys = production_migration_keys()
    extracted: dict[str, str] = {}
    for key in keys:
        app_label, name = key.split(".", 1)
        extracted[key] = sqlmigrate_sql(app_label, name)
    findings = check_extraction(keys, mapping, distribution, index, extracted)
    if findings:
        sys.stderr.write(format_findings(findings))
        return 1
    sys.stdout.write(
        f"sqlmigrate extraction ok ({len(keys)} first-party migrations)\n",
    )
    return 0


def _django_setup() -> None:
    os.environ.setdefault("COMPONENT_RUNTIME", "local")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")
    import django  # noqa: PLC0415

    django.setup()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail CI when a first-party migration lacks a Liquibase changeset.",
    )
    parser.parse_args(argv)
    _django_setup()
    return run_live_check()


if __name__ == "__main__":
    raise SystemExit(main())
