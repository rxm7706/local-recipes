#!/usr/bin/env python3
"""Installs the checked-in nightly-compile trigger via a pluggable backend
(Story 8.1: spec-8-1-the-nightly-compile-gets-a-trigger-the-estate-owns-...).

WHY THIS EXISTS. `scribe graph compile --nightly` (Story 3.3) has always been
prompt-free and `flock -n`-safe, but the only documented trigger was an
opt-in, hand-typed `crontab -e` line -- nobody installed it, so the compile
never actually ran on a schedule. This script makes installing the trigger a
documented, repeatable ACT instead of a hand-typed cron line.

BACKENDS. Four, chosen via `--backend NAME` or `PYFORGE_SCRIBE_TRIGGER_BACKEND`
(default: `crontab`):

- `crontab` (DEFAULT) -- writes a plain user-crontab entry via the
  `python-crontab` package (conda-forge, pure Python). Needs only the
  system `crontab` CLI (from the distro's cron package, virtually always
  already installed and running) -- no `systemctl`/`loginctl` step at all,
  since standard cron fires regardless of login/linger state.
- `systemd` -- the original implementation: a systemd-user timer, requiring
  `systemctl --user enable --now` and (for full-logout persistence)
  `loginctl enable-linger`. Linux systemd-user only.
- `apscheduler` -- an in-process Python scheduler (conda-forge). Honest
  limitation: apscheduler is a library, not a service manager -- nothing
  here starts, restarts, or persists the runner process across logout or
  reboot. This backend writes the runner script and says so; it never
  claims persistence it cannot provide.
- `supercronic` -- writes a crontab-format job file for the `supercronic`
  binary to read. `supercronic` itself has NO conda-forge or PyPI package
  (verified: no conda-forge/supercronic-feedstock) -- it is a manual,
  out-of-pixi install (github.com/aptible/supercronic releases). This
  backend refuses cleanly if the binary isn't already on PATH, and -- like
  apscheduler -- does not itself supervise the process.

Only `crontab` and `systemd` are genuinely "install and forget": they
delegate to a host-managed service (cron, systemd-user) that starts and
restarts their job on its own. `apscheduler` and `supercronic` are
best-effort options for a host that already has its own process supervisor;
the installer's own printed output makes that gap explicit rather than
hiding it.

SCOPE. Linux only, all four backends. A macOS `launchd` backend is a
natural follow-up, deliberately out of scope here (see
docs/cli-runbooks.md's "Scope note": ONE default trigger mechanism, proven
to actually run, beats several half-verified ones).
"""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
_OPS_DIR = REPO_ROOT / "src" / "shared" / "packages" / "pyforge-scribe" / "ops" / "systemd"
_UNIT_NAME = "pyforge-scribe-nightly-compile"
SERVICE_TEMPLATE = _OPS_DIR / f"{_UNIT_NAME}.service.tmpl"
TIMER_UNIT = _OPS_DIR / f"{_UNIT_NAME}.timer"

#: Scribe's own external environment-variable contract (see
#: scripts/scribe_nightly_trigger.py) -- named here, never imported (AD-7).
_GRAPHSTORE_OWNER_ENV = "PYFORGE_GRAPHSTORE_OWNER"

#: Which backend installs the trigger. CLI `--backend NAME` overrides this
#: env var; both override the default.
_BACKEND_ENV = "PYFORGE_SCRIBE_TRIGGER_BACKEND"
_DEFAULT_BACKEND = "crontab"
_VALID_BACKENDS = ("apscheduler", "crontab", "supercronic", "systemd")

#: The nightly schedule, expressed once per backend's own format. Mirrors
#: ops/systemd/pyforge-scribe-nightly-compile.timer's `OnCalendar=*-*-* 02:30:00`.
_CRON_SCHEDULE = "30 2 * * *"
_CRON_COMMENT = "pyforge-scribe-nightly-compile"
_LOG_REL_PATH = Path(".cache") / "scribe-nightly-compile.log"


# --------------------------------------------------------------------------
# systemd backend (original implementation)
# --------------------------------------------------------------------------


def render_service_unit(
    repo_root: Path, pixi_bin: str, graphstore_owner: str | None = None
) -> str:
    """Pure rendering of the checked-in `.service.tmpl` -- no I/O.

    When `graphstore_owner` is set, bakes an
    `Environment=PYFORGE_GRAPHSTORE_OWNER=...` line into the rendered unit
    -- mirrors exactly how `pixi_bin` is already baked in as `PIXI_BIN`, so
    that a systemd-fired run (which does not inherit the installer's own
    interactive shell environment) can still see which GraphStore driver is
    configured.
    """
    graphstore_owner_line = (
        f"Environment={_GRAPHSTORE_OWNER_ENV}={graphstore_owner}\n"
        if graphstore_owner
        else ""
    )
    return SERVICE_TEMPLATE.read_text(encoding="utf-8").format(
        repo_root=repo_root,
        pixi_bin=pixi_bin,
        graphstore_owner_line=graphstore_owner_line,
    )


def _systemd_user_dir(*, home: Path) -> Path:
    return home / ".config" / "systemd" / "user"


def _check_linger(user: str, *, which=shutil.which, run=subprocess.run) -> None:
    """Best-effort advisory, never fatal to the install: a systemd-user
    timer only fires on its own while the invoking user has an active
    login session, unless `loginctl enable-linger` is set for them --
    `Persistent=true` only catches up a missed firing at the NEXT login, it
    does not fire while the user is fully logged out. Swallows any error
    from `loginctl` itself (unavailable, unreadable output, ...) -- this
    never fails the install."""
    if which("loginctl") is None:
        return
    try:
        result = run(
            ["loginctl", "show-user", user, "--property=Linger"],
            capture_output=True,
            text=True,
        )
    except OSError:
        return
    if getattr(result, "returncode", 1) != 0:
        return
    if "Linger=no" in (getattr(result, "stdout", "") or ""):
        print(
            "scribe-install-nightly-trigger: linger is not enabled for "
            f"{user!r} -- {_UNIT_NAME}.timer only fires while you have an "
            "active session; run `loginctl enable-linger $USER` so it also "
            "fires while fully logged out (see docs/cli-runbooks.md)",
            file=sys.stderr,
        )


def _install_systemd(*, home: Path, which=shutil.which, run=subprocess.run) -> int:
    if which("systemctl") is None:
        print(
            "scribe-install-nightly-trigger: `systemctl` is not on PATH -- "
            "the `systemd` backend targets Linux systemd-user only (see "
            "docs/cli-runbooks.md's Scope note); try the `crontab` backend "
            f"instead ({_BACKEND_ENV}=crontab, the default)",
            file=sys.stderr,
        )
        return 1

    pixi_bin = which("pixi")
    if pixi_bin is None:
        print("scribe-install-nightly-trigger: `pixi` is not on PATH", file=sys.stderr)
        return 1

    dest_dir = _systemd_user_dir(home=home)
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        rendered = render_service_unit(
            REPO_ROOT, pixi_bin, graphstore_owner=os.environ.get(_GRAPHSTORE_OWNER_ENV)
        )
        (dest_dir / f"{_UNIT_NAME}.service").write_text(rendered, encoding="utf-8")
        shutil.copyfile(TIMER_UNIT, dest_dir / f"{_UNIT_NAME}.timer")
    except OSError as exc:
        print(
            f"scribe-install-nightly-trigger: failed to write unit files to "
            f"{dest_dir}: {exc}",
            file=sys.stderr,
        )
        return 1

    try:
        reload = run(["systemctl", "--user", "daemon-reload"])
    except OSError as exc:
        print(
            f"scribe-install-nightly-trigger: `systemctl --user daemon-reload` "
            f"failed: {exc}",
            file=sys.stderr,
        )
        return 1
    if reload.returncode != 0:
        print("scribe-install-nightly-trigger: `systemctl --user daemon-reload` failed", file=sys.stderr)
        return 1

    try:
        enable = run(["systemctl", "--user", "enable", "--now", f"{_UNIT_NAME}.timer"])
    except OSError as exc:
        print(
            "scribe-install-nightly-trigger: `systemctl --user enable --now "
            f"{_UNIT_NAME}.timer` failed: {exc}",
            file=sys.stderr,
        )
        return 1
    if enable.returncode != 0:
        print(
            "scribe-install-nightly-trigger: `systemctl --user enable --now "
            f"{_UNIT_NAME}.timer` failed",
            file=sys.stderr,
        )
        return 1

    print(f"scribe-install-nightly-trigger: installed and enabled {_UNIT_NAME}.timer")
    print(f"  status:     systemctl --user status {_UNIT_NAME}.timer")
    print(f"  next run:   systemctl --user list-timers {_UNIT_NAME}.timer")
    print(f"  unit files: {dest_dir}")
    _check_linger(os.environ.get("USER", ""), which=which, run=run)
    return 0


# --------------------------------------------------------------------------
# crontab backend (DEFAULT)
# --------------------------------------------------------------------------


def _trigger_shell_command(
    repo_root: Path, pixi_bin: str, home: Path, *, graphstore_owner: str | None
) -> str:
    """The one shell command line the `crontab` and `supercronic` backends
    both schedule -- a `cd` into the repo (neither cron nor supercronic set
    a working directory), an optional inline `PYFORGE_GRAPHSTORE_OWNER=`
    prefix (the shell-command equivalent of how the systemd backend bakes
    it into the unit's `Environment=` line), then the same
    `pyforge-scribe-nightly-compile` task the systemd `.service` unit
    invokes, appending both streams to the same `~/.cache/scribe-nightly-
    compile.log` the runbook already documents checking."""
    owner_prefix = (
        f"{_GRAPHSTORE_OWNER_ENV}={shlex.quote(graphstore_owner)} " if graphstore_owner else ""
    )
    log_path = home / _LOG_REL_PATH
    return (
        f"cd {shlex.quote(str(repo_root))} && {owner_prefix}"
        f"{shlex.quote(pixi_bin)} run -e pyforge-scribe pyforge-scribe-nightly-compile "
        f">> {shlex.quote(str(log_path))} 2>&1"
    )


def _install_crontab(*, home: Path, which=shutil.which, cron_factory=None) -> int:
    if cron_factory is None:
        try:
            from crontab import CronTab as cron_factory  # noqa: N813
        except ImportError:
            print(
                "scribe-install-nightly-trigger: the `crontab` backend needs "
                "the `python-crontab` package (declared as a pyforge-scribe "
                "pixi dependency -- run `pixi install -e pyforge-scribe` if "
                "this is missing)",
                file=sys.stderr,
            )
            return 1

    pixi_bin = which("pixi")
    if pixi_bin is None:
        print("scribe-install-nightly-trigger: `pixi` is not on PATH", file=sys.stderr)
        return 1

    command = _trigger_shell_command(
        REPO_ROOT, pixi_bin, home, graphstore_owner=os.environ.get(_GRAPHSTORE_OWNER_ENV)
    )

    try:
        cron = cron_factory(user=True)
        cron.remove_all(comment=_CRON_COMMENT)
        job = cron.new(command=command, comment=_CRON_COMMENT)
        job.setall(_CRON_SCHEDULE)
        cron.write()
    except OSError as exc:
        print(
            f"scribe-install-nightly-trigger: failed to write the crontab "
            f"entry: {exc} -- the `crontab` backend needs the system "
            "`crontab` CLI on PATH (from your distro's cron package); "
            f"install it, or switch backends via {_BACKEND_ENV}="
            "systemd|apscheduler|supercronic",
            file=sys.stderr,
        )
        return 1

    print(f"scribe-install-nightly-trigger: installed crontab entry ({_CRON_SCHEDULE})")
    print("  view: crontab -l")
    print(f"  log:  {home / _LOG_REL_PATH}")
    print(
        "  standard cron fires regardless of login/linger state -- no "
        "loginctl step needed for this backend"
    )
    return 0


# --------------------------------------------------------------------------
# apscheduler backend (in-process; does not persist on its own)
# --------------------------------------------------------------------------

_APSCHEDULER_RUNNER_TEMPLATE = '''#!/usr/bin/env python3
"""Rendered by scripts/scribe_install_nightly_trigger.py's `apscheduler`
backend (Story 8.1). Blocks in the foreground, firing the same
pyforge-scribe-nightly-compile task the other backends schedule, at 02:30
daily -- mirrors ops/systemd/pyforge-scribe-nightly-compile.timer's own
OnCalendar=*-*-* 02:30:00.

UNLIKE the crontab/systemd/supercronic backends, apscheduler is an
in-process library, not a service manager: nothing here restarts this
process after a crash, logout, or reboot. Run it under your own supervisor
(a systemd-user service pointed at this file, tmux, nohup, ...) -- the
installer prints this same caveat and never claims persistence it cannot
provide.
"""
from __future__ import annotations

import os
import subprocess

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

_PIXI_BIN = "__PIXI_BIN__"
_REPO_ROOT = "__REPO_ROOT__"
__GRAPHSTORE_OWNER_LINE__

def _fire() -> None:
    subprocess.run(
        [_PIXI_BIN, "run", "-e", "pyforge-scribe", "pyforge-scribe-nightly-compile"],
        cwd=_REPO_ROOT,
    )


if __name__ == "__main__":
    scheduler = BlockingScheduler()
    scheduler.add_job(_fire, CronTrigger(hour=2, minute=30))
    print("pyforge-scribe nightly scheduler running -- Ctrl+C to stop")
    scheduler.start()
'''


def _render_apscheduler_runner(repo_root: Path, pixi_bin: str, graphstore_owner: str | None) -> str:
    owner_line = (
        f'os.environ.setdefault("{_GRAPHSTORE_OWNER_ENV}", {graphstore_owner!r})'
        if graphstore_owner
        else ""
    )
    return (
        _APSCHEDULER_RUNNER_TEMPLATE.replace("__PIXI_BIN__", pixi_bin)
        .replace("__REPO_ROOT__", str(repo_root))
        .replace("__GRAPHSTORE_OWNER_LINE__", owner_line)
    )


def _install_apscheduler(*, home: Path, which=shutil.which) -> int:
    try:
        import apscheduler  # noqa: F401
    except ImportError:
        print(
            "scribe-install-nightly-trigger: the `apscheduler` backend "
            "needs the `apscheduler` package (declared as a pyforge-scribe "
            "pixi dependency -- run `pixi install -e pyforge-scribe` if "
            "this is missing)",
            file=sys.stderr,
        )
        return 1

    pixi_bin = which("pixi")
    if pixi_bin is None:
        print("scribe-install-nightly-trigger: `pixi` is not on PATH", file=sys.stderr)
        return 1

    dest_dir = home / ".config" / "pyforge-scribe"
    runner_path = dest_dir / "nightly_scheduler.py"
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        runner_path.write_text(
            _render_apscheduler_runner(
                REPO_ROOT, pixi_bin, os.environ.get(_GRAPHSTORE_OWNER_ENV)
            ),
            encoding="utf-8",
        )
    except OSError as exc:
        print(
            f"scribe-install-nightly-trigger: failed to write {runner_path}: {exc}",
            file=sys.stderr,
        )
        return 1

    print(f"scribe-install-nightly-trigger: wrote the apscheduler runner to {runner_path}")
    print(
        "  WARNING: apscheduler is in-process only -- this does NOT start, "
        "restart, or persist the runner across logout/reboot on its own. "
        f"Launch it yourself and keep it alive: {pixi_bin} run -e "
        f"pyforge-scribe python {runner_path}",
        file=sys.stderr,
    )
    return 0


# --------------------------------------------------------------------------
# supercronic backend (the binary itself is a manual, out-of-pixi install)
# --------------------------------------------------------------------------


def _install_supercronic(*, home: Path, which=shutil.which) -> int:
    pixi_bin = which("pixi")
    if pixi_bin is None:
        print("scribe-install-nightly-trigger: `pixi` is not on PATH", file=sys.stderr)
        return 1
    if which("supercronic") is None:
        print(
            "scribe-install-nightly-trigger: `supercronic` is not on PATH "
            "-- it has no conda-forge or PyPI package (verified: no "
            "conda-forge/supercronic-feedstock), so it is a manual, "
            "out-of-pixi install (github.com/aptible/supercronic releases) "
            f"before this backend can run. Switch backends via {_BACKEND_ENV}"
            "=crontab|systemd|apscheduler if you'd rather not install it by "
            "hand.",
            file=sys.stderr,
        )
        return 1

    dest_dir = home / ".config" / "pyforge-scribe"
    crontab_path = dest_dir / "supercronic.crontab"
    command = _trigger_shell_command(
        REPO_ROOT, pixi_bin, home, graphstore_owner=os.environ.get(_GRAPHSTORE_OWNER_ENV)
    )
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        crontab_path.write_text(f"{_CRON_SCHEDULE} {command}\n", encoding="utf-8")
    except OSError as exc:
        print(
            f"scribe-install-nightly-trigger: failed to write {crontab_path}: {exc}",
            file=sys.stderr,
        )
        return 1

    print(f"scribe-install-nightly-trigger: wrote the supercronic job file to {crontab_path}")
    print(
        "  NOTE: supercronic only runs jobs while its own process is "
        "running -- nothing here starts or supervises it. Launch it "
        f"yourself and keep it alive: supercronic {crontab_path}",
        file=sys.stderr,
    )
    return 0


# --------------------------------------------------------------------------
# dispatcher
# --------------------------------------------------------------------------


def _resolve_backend(argv: list[str] | None, backend: str | None) -> str:
    if backend is not None:
        return backend
    args = sys.argv[1:] if argv is None else argv
    for i, arg in enumerate(args):
        if arg == "--backend" and i + 1 < len(args):
            return args[i + 1]
        if arg.startswith("--backend="):
            return arg.split("=", 1)[1]
    return os.environ.get(_BACKEND_ENV) or _DEFAULT_BACKEND


def main(
    *,
    argv: list[str] | None = None,
    home: Path | None = None,
    which=shutil.which,
    run=subprocess.run,
    backend: str | None = None,
) -> int:
    resolved = _resolve_backend(argv, backend)
    home = home if home is not None else Path.home()

    if resolved == "crontab":
        return _install_crontab(home=home, which=which)
    if resolved == "systemd":
        return _install_systemd(home=home, which=which, run=run)
    if resolved == "apscheduler":
        return _install_apscheduler(home=home, which=which)
    if resolved == "supercronic":
        return _install_supercronic(home=home, which=which)

    print(
        f"scribe-install-nightly-trigger: unknown backend {resolved!r} -- "
        f"choose one of: {', '.join(_VALID_BACKENDS)} (set via --backend or "
        f"{_BACKEND_ENV})",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
