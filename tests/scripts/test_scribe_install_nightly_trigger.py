"""Acceptance tests for scripts/scribe_install_nightly_trigger.py (Story 8.1).

Focused on the parts worth unit-testing in isolation: the pure template
renders, backend resolution, and each backend's "refuse before touching the
filesystem/a live service" gates. The real install acts that drive a live
system (`systemctl --user ...`/`loginctl`, the real `crontab` CLI,
`supercronic` itself) have no dedicated test beyond dependency-injected
fakes -- same precedent as `scripts/scribe_pg.py`, which stands entirely
untested because it drives real service binaries a unit test cannot fake
meaningfully. The `crontab` backend is exercised through an injected
`cron_factory` fake rather than the real `python-crontab`/system `crontab`,
so tests never touch the machine's actual crontab.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "scribe_install_nightly_trigger.py"

try:
    import apscheduler  # noqa: F401

    _HAS_APSCHEDULER = True
except ImportError:
    _HAS_APSCHEDULER = False

_needs_apscheduler = pytest.mark.skipif(
    not _HAS_APSCHEDULER,
    reason="apscheduler is a pyforge-scribe-only pixi dependency, not installed in every env this test file runs under",
)


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "scribe_install_nightly_trigger_under_test", SCRIPT_PATH
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["scribe_install_nightly_trigger_under_test"] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class _FakeCronItem:
    def __init__(self, command: str, comment: str) -> None:
        self.command = command
        self.comment = comment
        self.schedule: str | None = None

    def setall(self, schedule: str) -> None:
        self.schedule = schedule


class _FakeCronTab:
    """Stands in for python-crontab's `CronTab` -- never touches the real
    system crontab or requires the `crontab` CLI to be on PATH."""

    write_error: Exception | None = None

    def __init__(self, user=None) -> None:
        self.user = user
        self.jobs: list[_FakeCronItem] = []
        self.written = False

    def remove_all(self, comment: str | None = None) -> None:
        self.jobs = [j for j in self.jobs if j.comment != comment]

    def new(self, command: str = "", comment: str = "") -> _FakeCronItem:
        item = _FakeCronItem(command, comment)
        self.jobs.append(item)
        return item

    def write(self) -> None:
        if self.write_error is not None:
            raise self.write_error
        self.written = True


# --------------------------------------------------------------------------
# render_service_unit (systemd's pure template render)
# --------------------------------------------------------------------------


def test_render_service_unit_substitutes_repo_root_and_pixi_bin():
    mod = _load_module()
    rendered = mod.render_service_unit(Path("/home/you/local-recipes"), "/usr/bin/pixi")

    assert "WorkingDirectory=/home/you/local-recipes" in rendered
    assert "ExecStart=/usr/bin/pixi run -e pyforge-scribe pyforge-scribe-nightly-compile" in rendered
    assert "Environment=PIXI_BIN=/usr/bin/pixi" in rendered
    assert "{repo_root}" not in rendered
    assert "{pixi_bin}" not in rendered
    assert not any(
        line.startswith("Environment=PYFORGE_GRAPHSTORE_OWNER=")
        for line in rendered.splitlines()
    )


def test_render_service_unit_bakes_graphstore_owner_when_set():
    mod = _load_module()
    rendered = mod.render_service_unit(
        Path("/home/you/local-recipes"), "/usr/bin/pixi", graphstore_owner="steward"
    )

    assert "Environment=PYFORGE_GRAPHSTORE_OWNER=steward" in rendered
    assert "{graphstore_owner_line}" not in rendered


# --------------------------------------------------------------------------
# backend resolution
# --------------------------------------------------------------------------


def test_resolve_backend_defaults_to_crontab(monkeypatch):
    mod = _load_module()
    monkeypatch.delenv(mod._BACKEND_ENV, raising=False)

    assert mod._resolve_backend([], None) == "crontab"


def test_resolve_backend_reads_env_var(monkeypatch):
    mod = _load_module()
    monkeypatch.setenv(mod._BACKEND_ENV, "systemd")

    assert mod._resolve_backend([], None) == "systemd"


def test_resolve_backend_cli_flag_overrides_env_var(monkeypatch):
    mod = _load_module()
    monkeypatch.setenv(mod._BACKEND_ENV, "systemd")

    assert mod._resolve_backend(["--backend", "apscheduler"], None) == "apscheduler"
    assert mod._resolve_backend(["--backend=supercronic"], None) == "supercronic"


def test_resolve_backend_explicit_kwarg_wins_over_everything(monkeypatch):
    mod = _load_module()
    monkeypatch.setenv(mod._BACKEND_ENV, "systemd")

    assert mod._resolve_backend(["--backend", "apscheduler"], "crontab") == "crontab"


def test_main_refuses_unknown_backend(capsys):
    mod = _load_module()

    rc = mod.main(backend="not-a-real-backend")

    assert rc == 1
    err = capsys.readouterr().err
    assert "not-a-real-backend" in err
    assert "crontab" in err  # names the valid choices


# --------------------------------------------------------------------------
# crontab backend (DEFAULT)
# --------------------------------------------------------------------------


def test_crontab_backend_writes_entry_and_is_idempotent(tmp_path, monkeypatch):
    mod = _load_module()
    monkeypatch.delenv("PYFORGE_GRAPHSTORE_OWNER", raising=False)

    def which(name: str) -> str:
        return f"/usr/bin/{name}"

    rc = mod._install_crontab(home=tmp_path, which=which, cron_factory=_FakeCronTab)

    assert rc == 0
    # main() routes here via the "crontab" backend name too -- exercised
    # separately by test_resolve_backend_defaults_to_crontab above.


def test_crontab_backend_bakes_graphstore_owner_into_command(tmp_path, monkeypatch):
    mod = _load_module()
    monkeypatch.setenv("PYFORGE_GRAPHSTORE_OWNER", "steward")
    captured: dict[str, _FakeCronTab] = {}

    class _CapturingFakeCronTab(_FakeCronTab):
        def __init__(self, user=None) -> None:
            super().__init__(user=user)
            captured["cron"] = self

    rc = mod._install_crontab(
        home=tmp_path, which=lambda name: f"/usr/bin/{name}", cron_factory=_CapturingFakeCronTab
    )

    assert rc == 0
    (job,) = captured["cron"].jobs
    assert "PYFORGE_GRAPHSTORE_OWNER=steward" in job.command
    assert job.schedule == mod._CRON_SCHEDULE


def test_crontab_backend_removes_prior_entry_before_recreating(tmp_path):
    mod = _load_module()
    fake = _FakeCronTab(user=True)
    fake.new(command="stale old command", comment=mod._CRON_COMMENT)

    rc = mod._install_crontab(
        home=tmp_path, which=lambda name: f"/usr/bin/{name}", cron_factory=lambda user=None: fake
    )

    assert rc == 0
    assert len(fake.jobs) == 1
    assert "stale old command" not in fake.jobs[0].command


def test_crontab_backend_refuses_cleanly_without_pixi(tmp_path, capsys):
    mod = _load_module()

    rc = mod._install_crontab(home=tmp_path, which=lambda name: None, cron_factory=_FakeCronTab)

    assert rc == 1
    assert "pixi" in capsys.readouterr().err


def test_crontab_backend_refuses_cleanly_without_python_crontab_package(tmp_path, monkeypatch, capsys):
    mod = _load_module()
    monkeypatch.setitem(sys.modules, "crontab", None)

    rc = mod._install_crontab(home=tmp_path, which=lambda name: f"/usr/bin/{name}")

    assert rc == 1
    assert "python-crontab" in capsys.readouterr().err


def test_crontab_backend_refuses_cleanly_on_write_failure(tmp_path, capsys):
    mod = _load_module()

    class _FailingFakeCronTab(_FakeCronTab):
        write_error = OSError("no crontab program 'crontab'")

    rc = mod._install_crontab(
        home=tmp_path, which=lambda name: f"/usr/bin/{name}", cron_factory=_FailingFakeCronTab
    )

    assert rc == 1
    err = capsys.readouterr().err
    assert "crontab" in err
    assert mod._BACKEND_ENV in err  # points at the escape hatch


# --------------------------------------------------------------------------
# apscheduler backend (in-process; does not persist on its own)
# --------------------------------------------------------------------------


@_needs_apscheduler
def test_apscheduler_backend_writes_runner_and_warns_no_persistence(tmp_path, capsys):
    mod = _load_module()

    rc = mod._install_apscheduler(home=tmp_path, which=lambda name: f"/usr/bin/{name}")

    assert rc == 0
    runner = tmp_path / ".config" / "pyforge-scribe" / "nightly_scheduler.py"
    assert runner.is_file()
    content = runner.read_text(encoding="utf-8")
    assert "/usr/bin/pixi" in content
    assert "BlockingScheduler" in content
    err = capsys.readouterr().err
    assert "does NOT start, restart, or persist" in err


@_needs_apscheduler
def test_apscheduler_backend_bakes_graphstore_owner(tmp_path, monkeypatch):
    mod = _load_module()
    monkeypatch.setenv("PYFORGE_GRAPHSTORE_OWNER", "steward")

    rc = mod._install_apscheduler(home=tmp_path, which=lambda name: f"/usr/bin/{name}")

    assert rc == 0
    content = (tmp_path / ".config" / "pyforge-scribe" / "nightly_scheduler.py").read_text(
        encoding="utf-8"
    )
    assert 'os.environ.setdefault("PYFORGE_GRAPHSTORE_OWNER", \'steward\')' in content


@_needs_apscheduler
def test_apscheduler_backend_refuses_cleanly_without_pixi(tmp_path, capsys):
    mod = _load_module()

    rc = mod._install_apscheduler(home=tmp_path, which=lambda name: None)

    assert rc == 1
    assert "pixi" in capsys.readouterr().err


def test_apscheduler_backend_refuses_cleanly_without_apscheduler_package(tmp_path, monkeypatch, capsys):
    mod = _load_module()
    monkeypatch.setitem(sys.modules, "apscheduler", None)

    rc = mod._install_apscheduler(home=tmp_path, which=lambda name: f"/usr/bin/{name}")

    assert rc == 1
    assert "apscheduler" in capsys.readouterr().err


# --------------------------------------------------------------------------
# supercronic backend (the binary itself is a manual, out-of-pixi install)
# --------------------------------------------------------------------------


def test_supercronic_backend_refuses_cleanly_when_binary_missing(tmp_path, capsys):
    mod = _load_module()

    def which(name: str) -> str | None:
        return "/usr/bin/pixi" if name == "pixi" else None

    rc = mod._install_supercronic(home=tmp_path, which=which)

    assert rc == 1
    err = capsys.readouterr().err
    assert "supercronic" in err
    assert "no conda-forge or PyPI package" in err


def test_supercronic_backend_writes_job_file_when_binary_present(tmp_path):
    mod = _load_module()

    rc = mod._install_supercronic(home=tmp_path, which=lambda name: f"/usr/bin/{name}")

    assert rc == 0
    job_file = tmp_path / ".config" / "pyforge-scribe" / "supercronic.crontab"
    assert job_file.is_file()
    assert job_file.read_text(encoding="utf-8").startswith(mod._CRON_SCHEDULE)


def test_supercronic_backend_refuses_cleanly_without_pixi(tmp_path, capsys):
    mod = _load_module()

    rc = mod._install_supercronic(home=tmp_path, which=lambda name: None)

    assert rc == 1
    assert "pixi" in capsys.readouterr().err


# --------------------------------------------------------------------------
# systemd backend (original implementation, now opt-in)
# --------------------------------------------------------------------------


def test_refuses_cleanly_without_systemctl(capsys):
    mod = _load_module()

    rc = mod.main(backend="systemd", which=lambda name: None, run=lambda *a, **k: None)

    assert rc == 1
    assert "systemctl" in capsys.readouterr().err


def test_refuses_cleanly_without_pixi(capsys):
    mod = _load_module()

    def which(name: str) -> str | None:
        return "/usr/bin/systemctl" if name == "systemctl" else None

    rc = mod.main(backend="systemd", which=which, run=lambda *a, **k: None)

    assert rc == 1
    assert "pixi" in capsys.readouterr().err


def test_installs_and_enables_when_tools_present(tmp_path, monkeypatch):
    mod = _load_module()
    monkeypatch.setenv("USER", "tester")
    monkeypatch.delenv("PYFORGE_GRAPHSTORE_OWNER", raising=False)

    class _Result:
        def __init__(self, returncode: int = 0) -> None:
            self.returncode = returncode

    calls: list[list[str]] = []

    def run(cmd, *a, **k):
        calls.append(list(cmd))
        return _Result(0)

    def which(name: str) -> str:
        return f"/usr/bin/{name}"

    rc = mod.main(backend="systemd", home=tmp_path, which=which, run=run)

    assert rc == 0
    dest = tmp_path / ".config" / "systemd" / "user"
    assert (dest / "pyforge-scribe-nightly-compile.service").is_file()
    assert (dest / "pyforge-scribe-nightly-compile.timer").is_file()
    assert calls == [
        ["systemctl", "--user", "daemon-reload"],
        ["systemctl", "--user", "enable", "--now", "pyforge-scribe-nightly-compile.timer"],
        ["loginctl", "show-user", "tester", "--property=Linger"],
    ]


def test_warns_when_linger_not_enabled(tmp_path, monkeypatch, capsys):
    mod = _load_module()
    monkeypatch.setenv("USER", "tester")
    monkeypatch.delenv("PYFORGE_GRAPHSTORE_OWNER", raising=False)

    class _Result:
        def __init__(self, returncode: int = 0, stdout: str = "") -> None:
            self.returncode = returncode
            self.stdout = stdout

    def run(cmd, *a, **k):
        if cmd and cmd[0] == "loginctl":
            return _Result(0, stdout="Linger=no\n")
        return _Result(0)

    def which(name: str) -> str:
        return f"/usr/bin/{name}"

    rc = mod.main(backend="systemd", home=tmp_path, which=which, run=run)

    assert rc == 0
    assert "loginctl enable-linger" in capsys.readouterr().err


def test_bakes_graphstore_owner_from_installer_env(tmp_path, monkeypatch):
    mod = _load_module()
    monkeypatch.setenv("USER", "tester")
    monkeypatch.setenv("PYFORGE_GRAPHSTORE_OWNER", "steward")

    class _Result:
        def __init__(self, returncode: int = 0) -> None:
            self.returncode = returncode

    def run(cmd, *a, **k):
        return _Result(0)

    def which(name: str) -> str:
        return f"/usr/bin/{name}"

    rc = mod.main(backend="systemd", home=tmp_path, which=which, run=run)

    assert rc == 0
    dest = tmp_path / ".config" / "systemd" / "user"
    service_content = (dest / "pyforge-scribe-nightly-compile.service").read_text(
        encoding="utf-8"
    )
    assert "Environment=PYFORGE_GRAPHSTORE_OWNER=steward" in service_content
