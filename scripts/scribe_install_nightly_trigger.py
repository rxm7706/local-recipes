#!/usr/bin/env python3
"""Installs the checked-in nightly-compile trigger as a systemd-user timer
(Story 8.1: spec-8-1-the-nightly-compile-gets-a-trigger-the-estate-owns-...).

WHY THIS EXISTS. `scribe graph compile --nightly` (Story 3.3) has always been
prompt-free and `flock -n`-safe, but the only documented trigger was an
opt-in, hand-typed `crontab -e` line -- nobody installed it, so the compile
never actually ran on a schedule. This script makes installing the trigger a
documented, repeatable ACT instead of a hand-typed cron line: it renders the
checked-in unit template
(`src/shared/packages/pyforge-scribe/ops/systemd/
pyforge-scribe-nightly-compile.service.tmpl`, `{repo_root}`/`{pixi_bin}`
substituted) alongside the static `.timer` unit into
`~/.config/systemd/user/`, then `systemctl --user daemon-reload` +
`enable --now` the timer. Idempotent: re-running re-renders the service file
and re-asserts enablement rather than failing on an already-installed
trigger.

SCOPE. Linux systemd-user only -- this repo's own operator machines. A
launchd equivalent for macOS is a natural follow-up, deliberately out of
scope here (see docs/cli-runbooks.md's "Scope note": ONE trigger mechanism,
proven to actually run, beats two half-verified ones).
"""
from __future__ import annotations

import os
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


def main(*, home: Path | None = None, which=shutil.which, run=subprocess.run) -> int:
    if which("systemctl") is None:
        print(
            "scribe-install-nightly-trigger: `systemctl` is not on PATH -- "
            "this installer targets Linux systemd-user only (see "
            "docs/cli-runbooks.md's Scope note); install the trigger by "
            "hand on other platforms",
            file=sys.stderr,
        )
        return 1

    pixi_bin = which("pixi")
    if pixi_bin is None:
        print("scribe-install-nightly-trigger: `pixi` is not on PATH", file=sys.stderr)
        return 1

    dest_dir = _systemd_user_dir(home=home if home is not None else Path.home())
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


if __name__ == "__main__":
    sys.exit(main())
