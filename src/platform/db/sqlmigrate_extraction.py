"""CI gate: every first-party production migration has a Liquibase changeset (FR-23).

Canopy AD-9: ``sqlmigrate`` extraction is the check that a changeset exists
for every production migration. Changeset ids stay ``distribution:seq``.
Story 41.3 made the map per-distribution (red-team B-1): each distribution
owns its own sequence, so ``pyforge-scribe:N`` is numbered independently of
``python-agent-platform:N``. Story 27.2 owns the Job contract and the :1/:2
changelog files; this module does not rewrite them.
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
DEFAULT_DISTRIBUTION = "python-agent-platform"
TEST_ONLY_APPS = frozenset(
    {"probe_portal", "workclass_probe"},
)
FIRST_PARTY_MARKERS = (
    "/src/platform/",
    "/src/shared/packages/django-",
)


@dataclass(frozen=True)
class MigrationMap:
    """``sqlmigrate-map.yaml``: one changeset sequence per distribution.

    ``default`` is the distribution an unmapped first-party Django migration
    is numbered into, so the failure message names an id in the tree the
    migration actually belongs to (Story 41.3 / red-team B-1).
    """

    default: str
    distributions: Mapping[str, Mapping[str, int]]

    def lookup(self, migration_key: str) -> tuple[str, int] | None:
        """``(distribution, seq)`` for a mapped migration, else ``None``."""
        for distribution, migrations in self.distributions.items():
            seq = migrations.get(migration_key)
            if seq is not None:
                return distribution, seq
        return None


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


def expected_id_from_filename(
    path: Path,
    migration_map: MigrationMap,
) -> str | None:
    """``<distribution>:<seq>`` this repo's own naming convention
    (``<distribution>-<seq>-<slug>.sql``) assigns to ``path``, or ``None`` if
    its filename matches no known distribution prefix (never guessed).

    Distribution names themselves contain hyphens (``python-agent-platform``,
    ``pyforge-scribe``), so the split can't be a blind regex -- it walks the
    map's own ``distributions`` keys (longest first, in case one is ever a
    prefix of another) to find which one the filename starts with.
    """
    stem = path.stem
    for distribution in sorted(migration_map.distributions, key=len, reverse=True):
        prefix = f"{distribution}-"
        if not stem.startswith(prefix):
            continue
        match = re.match(r"^([1-9][0-9]*)-", stem[len(prefix) :])
        if match is not None:
            return f"{distribution}:{match.group(1)}"
    return None


def find_unexpected_changesets(
    migration_map: MigrationMap,
    changelog_dir: Path = CHANGELOG_DIR,
) -> list[str]:
    """Every changelog file must carry EXACTLY ONE ``--changeset`` line, and
    it must be the id this repo's own filename convention assigns it.

    Closes the Row 8 gap (2026-09-04): a hand-inserted second
    ``--changeset python-agent-platform:21-1`` header landed in
    ``python-agent-platform-21-...-run-state-tenant.sql`` and was invisible
    to this gate, because ``parse_changeset_index`` only ever inspects the
    FIRST ``--changeset`` line per file (via ``CHANGESET_LINE.search``) --
    but Liquibase itself parses every ``--changeset`` comment in a formatted
    SQL file as its own changeset boundary, so the extra header was a real,
    silently-accepted second changeset.

    Comparing against the file's OWN filename, not against
    ``sqlmigrate-map.yaml``'s ``migrations:`` dict, is deliberate: that dict
    only records changesets backed by a Django migration. Several real,
    legitimate changesets are not (``python-agent-platform:2`` is DML
    grants; ``:15``-``:19`` are third-party-app migrations; every
    ``pyforge-scribe`` id owns no migration at all, per that distribution's
    own ``migrations: {}`` comment) -- matching against ``migrations:``
    directly would false-positive on all of them. The filename is this
    repo's actual source of truth for which id a file owns.
    """
    bad: list[str] = []
    for path in sorted(changelog_dir.glob("*.sql")):
        expected = expected_id_from_filename(path, migration_map)
        if expected is None:
            continue
        found = CHANGESET_LINE.findall(path.read_text(encoding="utf-8"))
        if found != [expected]:
            bad.append(
                f"{path.name}: expected exactly one changeset "
                f"({expected!r}), found {found!r}",
            )
    return bad


def format_unexpected_changesets(bad: list[str]) -> str:
    lines = [
        "sqlmigrate extraction failed; unexpected changeset id(s):",
        *(f"  {item}" for item in bad),
    ]
    return "\n".join(lines) + "\n"


def load_map(path: Path = MAP_PATH) -> MigrationMap:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    default = str(data.get("default") or DEFAULT_DISTRIBUTION)
    distributions: dict[str, dict[str, int]] = {}
    for name, entry in (data.get("distributions") or {}).items():
        raw = (entry or {}).get("migrations") or {}
        distributions[str(name)] = {
            str(key): int(value) for key, value in raw.items()
        }
    if default not in distributions:
        msg = (
            f"sqlmigrate-map.yaml default distribution {default!r} has no "
            f"entry under distributions: (got {sorted(distributions)})"
        )
        raise ValueError(msg)
    return MigrationMap(default=default, distributions=distributions)


def used_sequences(
    migration_map: MigrationMap,
    changeset_index: Mapping[str, str],
) -> dict[str, set[int]]:
    """Seqs already spoken for, per distribution: the map plus the changelog."""
    used: dict[str, set[int]] = {
        name: set(migrations.values())
        for name, migrations in migration_map.distributions.items()
    }
    for changeset_id in changeset_index:
        match = CHANGESET_ID.match(changeset_id)
        if match is not None:
            used.setdefault(match.group(1), set()).add(int(match.group(2)))
    return used


def expected_changeset_id(
    migration_key: str,
    migration_map: MigrationMap,
    used_seqs: Mapping[str, Iterable[int]],
) -> str:
    entry = migration_map.lookup(migration_key)
    if entry is not None:
        distribution, seq = entry
        return f"{distribution}:{seq}"
    distribution = migration_map.default
    nxt = max(used_seqs.get(distribution, ()), default=0) + 1
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
    migration_map: MigrationMap,
    changeset_index: Mapping[str, str],
    extracted_sql: Mapping[str, str],
) -> list[Finding]:
    used = used_sequences(migration_map, changeset_index)
    findings: list[Finding] = []
    for key in migration_keys:
        changeset_id = expected_changeset_id(key, migration_map, used)
        if migration_map.lookup(key) is None:
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
    migration_map = load_map()
    unexpected = find_unexpected_changesets(migration_map)
    if unexpected:
        sys.stderr.write(format_unexpected_changesets(unexpected))
        return 1
    index = parse_changeset_index()
    keys = production_migration_keys()
    extracted: dict[str, str] = {}
    for key in keys:
        app_label, name = key.split(".", 1)
        extracted[key] = sqlmigrate_sql(app_label, name)
    findings = check_extraction(keys, migration_map, index, extracted)
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
