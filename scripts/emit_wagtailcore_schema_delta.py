#!/usr/bin/env python3
"""Emit additive Liquibase SQL to bring CRC Wagtail 0001-squashed tables to 7.4.

Read-only against DATABASE_URL (introspects information_schema). Does not apply.
Not a first-party sqlmigrate-map entry — third-party Wagtail, same as :16/:18.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

PLATFORM = Path(__file__).resolve().parents[1] / "src" / "platform"
sys.path.insert(0, str(PLATFORM))
os.chdir(PLATFORM)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")

import django

django.setup()

from django.apps import apps
from django.db import connection


def _existing_tables() -> set[str]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            """
        )
        return {row[0] for row in cursor.fetchall()}


def _existing_columns(table: str) -> set[str]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            """,
            [table],
        )
        return {row[0] for row in cursor.fetchall()}


def _wagtail_models() -> list:
    models = []
    for config in apps.get_app_configs():
        if not config.name.startswith("wagtail"):
            continue
        for model in config.get_models():
            if model._meta.proxy or model._meta.auto_created:
                continue
            models.append(model)
    return models


def _stub_default(field):
    """Avoid live queries (Image.collection → Collection.get_first_root_node)."""
    if field.is_relation:
        return 1
    internal = field.get_internal_type()
    if internal in {"CharField", "TextField", "SlugField"}:
        return ""
    if internal in {"IntegerField", "PositiveIntegerField", "SmallIntegerField"}:
        return 0
    if internal == "BooleanField":
        return False
    if internal == "UUIDField":
        import uuid

        return uuid.UUID(int=0)
    return None


def main() -> int:
    tables = _existing_tables()
    editor = connection.schema_editor(collect_sql=True, atomic=False)
    models = _wagtail_models()
    with editor:
        for model in models:
            if model._meta.db_table not in tables:
                editor.create_model(model)
        for model in models:
            table = model._meta.db_table
            if table not in tables:
                continue
            have = _existing_columns(table)
            for field in model._meta.local_fields:
                if not field.column or field.column in have:
                    continue
                saved = field.default
                field.default = _stub_default(field)
                try:
                    editor.add_field(model, field)
                finally:
                    field.default = saved
            for field in model._meta.local_many_to_many:
                through = field.remote_field.through
                through_table = through._meta.db_table
                if through._meta.auto_created and through_table not in tables:
                    editor.create_model(through)
    sql_lines = list(editor.collected_sql)
    sys.stdout.write(
        "\n".join(
            f"{line};" if not str(line).rstrip().endswith(";") else str(line)
            for line in sql_lines
        )
    )
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
