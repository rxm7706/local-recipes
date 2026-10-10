"""Story 87.1 — platform host boots when pyforge-herald is absent."""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from http import HTTPStatus
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_PLATFORM_ROOT = Path(__file__).resolve().parents[1]

_CHILD_SCRIPT = textwrap.dedent(
    '''
    import asyncio
    import sys
    from http import HTTPStatus
    from unittest.mock import MagicMock

    class _HeraldAbsentFinder:
        def find_spec(self, fullname, path, target=None):
            if fullname == "pyforge.herald" or fullname.startswith("pyforge.herald."):
                raise ModuleNotFoundError(name=fullname)
            return None

    sys.meta_path.insert(0, _HeraldAbsentFinder())

    _langflow_asgi_app = MagicMock()
    _langflow_pkg = MagicMock()
    _langflow_pkg.main.create_app.return_value = _langflow_asgi_app
    sys.modules.setdefault("langflow", _langflow_pkg)
    sys.modules.setdefault("langflow.main", _langflow_pkg.main)

    import config.asgi  # noqa: F401
    import config.station_api as station_api_mod
    from config.optional_components import absent_reason

    stations = [s for s, _v, _a in station_api_mod.iter_station_apps()]
    assert "warden" in stations
    assert "herald" not in stations

    reason = absent_reason("herald")
    assert reason is not None
    assert "herald" in reason
    assert "pyforge.herald" in reason

    from httpx import ASGITransport, AsyncClient
    from config.asgi import application

    async def _request(method, path, **kwargs):
        transport = ASGITransport(app=application)
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.request(method, path, **kwargs)

    async def _run():
        for path in (
            "/stations/herald/api/v1/health",
            "/stations/herald/api/v1/openapi.json",
        ):
            resp = await _request("GET", path)
            assert resp.status_code == HTTPStatus.NOT_FOUND
            assert resp.json() == {"detail": reason}

        post = await _request(
            "POST",
            "/stations/herald/api/v1/webhooks/on-ship",
            json={},
        )
        assert post.status_code == HTTPStatus.NOT_FOUND
        assert post.json() == {"detail": reason}

        unknown = await _request("GET", "/stations/unknown/api/v1/health")
        assert unknown.status_code == HTTPStatus.NOT_FOUND
        assert unknown.json() == {"detail": "Not Found"}

        warden = await _request("GET", "/stations/warden/api/v1/health")
        assert warden.status_code == HTTPStatus.OK
        assert warden.json() == {"status": "ok", "station": "warden"}

    asyncio.run(_run())
    print("OK")
    '''
)


def _child_env() -> dict[str, str]:
    child_env = dict(os.environ)
    child_env["DJANGO_SETTINGS_MODULE"] = "config.settings.test"
    child_env.setdefault("COMPONENT_RUNTIME", "local")
    child_env["PYTHONPATH"] = os.pathsep.join(
        [str(_PLATFORM_ROOT), *(entry for entry in sys.path if entry)],
    )
    return child_env


def _run_fresh_interpreter(*, capture_log: bool = False) -> subprocess.CompletedProcess[str]:
    argv = [sys.executable, "-c", _CHILD_SCRIPT]
    return subprocess.run(  # noqa: S603
        argv,
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
        cwd=_PLATFORM_ROOT,
        env=_child_env(),
    )


def test_host_imports_without_herald_and_herald_paths_return_reason():
    proc = _run_fresh_interpreter()
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert "OK" in proc.stdout
    combined = proc.stdout + proc.stderr
    assert "herald" in combined
    assert "pyforge.herald" in combined
    assert combined.count("herald is not installed on this host") == 1


def test_import_optional_propagates_unrelated_module_not_found(tmp_path: Path) -> None:
    pkg = tmp_path / "throwaway_pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("import missing_dep_xyz\n", encoding="utf-8")
    sys.path.insert(0, str(tmp_path))
    try:
        from config.optional_components import import_optional

        with pytest.raises(ModuleNotFoundError, match="missing_dep_xyz"):
            import_optional(
                "throwaway_pkg",
                component="throwaway",
                provided_by="throwaway_pkg",
                remedy="n/a",
            )
    finally:
        sys.path.remove(str(tmp_path))
        sys.modules.pop("throwaway_pkg", None)


def test_import_optional_records_reason_for_missing_parent() -> None:
    from config.optional_components import absent_reason
    from config.optional_components import import_optional

    mod = import_optional(
        "no_such_pkg_87_1.submod",
        component="probe_missing_parent_87_1",
        provided_by="no_such_pkg_87_1",
        remedy="install probe",
    )
    assert mod is None
    reason = absent_reason("probe_missing_parent_87_1")
    assert reason is not None
    assert "no_such_pkg_87_1" in reason


def test_import_optional_logs_once_per_process(caplog: pytest.LogCaptureFixture) -> None:
    from config.optional_components import import_optional

    caplog.set_level("WARNING", logger="config.optional_components")
    component = "log_once_87_1"
    for _ in range(2):
        import_optional(
            "absent_pkg_87_1.child",
            component=component,
            provided_by="absent_pkg_87_1",
            remedy="install twice",
        )
    warnings = [
        r
        for r in caplog.records
        if r.name == "config.optional_components"
        and r.levelname == "WARNING"
        and component in r.getMessage()
    ]
    assert len(warnings) == 1
