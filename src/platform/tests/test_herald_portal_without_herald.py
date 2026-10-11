"""Story 37.1 — herald portal loads without pyforge.herald installed."""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

_PLATFORM_ROOT = Path(__file__).resolve().parents[1]

# Fresh pytest-django DB has no Wagtail page at /stations/ (404 with herald too).
_EXPECTED_STATIONS_STATUS = 404


def _database_url_for_child() -> str | None:
    from django.conf import settings

    db = settings.DATABASES["default"]
    engine = db.get("ENGINE", "")
    if "postgresql" not in engine:
        return None
    name = db.get("NAME")
    if not name:
        return None
    user = db.get("USER") or ""
    password = db.get("PASSWORD") or ""
    host = db.get("HOST") or ""
    port = db.get("PORT") or ""
    if host.startswith("/"):
        return f"postgres:///{name}?host={host}"
    auth = ""
    if user:
        auth = f"{user}:{password}@" if password else f"{user}@"
    host_part = host or "localhost"
    port_part = f":{port}" if port else ""
    return f"postgres://{auth}{host_part}{port_part}/{name}"


def _build_child_script(expected_stations_status: int) -> str:
    head = textwrap.dedent(
        f"""
        import django
        import logging
        import sys
        from django.core.management import call_command
        from django.test import Client
        from django.urls import clear_url_caches, resolve

        records: list[logging.LogRecord] = []

        class _CaptureHandler(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                records.append(record)

        cap = _CaptureHandler()
        cap.setLevel(logging.WARNING)
        logging.getLogger("django_herald_portal").addHandler(cap)
        logging.getLogger("django_herald_portal").setLevel(logging.WARNING)

        class _HeraldAbsentFinder:
            def find_spec(self, fullname, path, target=None):
                if fullname == "pyforge.herald" or fullname.startswith("pyforge.herald."):
                    raise ModuleNotFoundError(name=fullname)
                return None

        sys.meta_path.insert(0, _HeraldAbsentFinder())

        django.setup()
        from django.conf import settings

        if "testserver" not in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS = [*settings.ALLOWED_HOSTS, "testserver"]
        call_command("check")

        client = Client()
        assert client.get("/").status_code == 200
        assert client.get("/stations/").status_code == {expected_stations_status}
        assert client.get("/cms/").status_code == 302
        assert client.get("/stations/warden/").status_code == 403

        for path in (
            "/stations/herald/",
            "/stations/herald/decks/",
            "/stations/herald/decks/any-slug/view/",
        ):
            resp = client.get(path)
            assert resp.status_code == 404
            assert resp["Content-Type"].startswith("text/plain")
            body = resp.content.decode()
            assert "herald" in body
            assert "pyforge.herald" in body

        clear_url_caches()
        resolve("/stations/herald/")

        portal_warnings = [r for r in records if r.name == "django_herald_portal"]
        assert len(portal_warnings) == 1
        msg = portal_warnings[0].getMessage()
        assert "herald" in msg
        assert "pyforge.herald" in msg
        print("OK")
        """
    )
    return head


def _child_env() -> dict[str, str]:
    child_env = dict(os.environ)
    child_env["DJANGO_SETTINGS_MODULE"] = "config.settings.test"
    child_env.setdefault("COMPONENT_RUNTIME", "local")
    child_env["PYTHONPATH"] = os.pathsep.join(
        [str(_PLATFORM_ROOT), *(entry for entry in sys.path if entry)],
    )
    return child_env


def _run_child(
    expected_stations_status: int,
    *,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = _child_env()
    if extra_env:
        env.update(extra_env)
    argv = [sys.executable, "-c", _build_child_script(expected_stations_status)]
    return subprocess.run(  # noqa: S603
        argv,
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
        cwd=_PLATFORM_ROOT,
        env=env,
    )


@pytest.mark.django_db
def test_herald_portal_pages_without_herald():
    extra: dict[str, str] = {}
    db_url = _database_url_for_child()
    if db_url is not None:
        extra["DATABASE_URL"] = db_url
    proc = _run_child(_EXPECTED_STATIONS_STATUS, extra_env=extra)
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert "OK" in proc.stdout
    combined = proc.stdout + proc.stderr
    assert combined.count("herald is not installed on this host") >= 1
    assert combined.count("herald is not installed on this host") == combined.count(
        "herald is not installed on this host"
    )
