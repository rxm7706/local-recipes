#!/usr/bin/env python3
"""Nightly-compile trigger body (Story 8.1).

The ONE command the checked-in systemd-user timer
(`pyforge-scribe-nightly-compile.timer` / `.service.tmpl`, under
`src/shared/packages/pyforge-scribe/ops/systemd/`, installed by
`scripts/scribe_install_nightly_trigger.py`) invokes every night -- and the
pixi task (`pyforge-scribe-nightly-compile`) an operator can also run by
hand. This is the trigger's own definition, checked into git and reviewable
(spec-8-1's Boundaries & Constraints), replacing the former hand-typed
`crontab -e` line documented in docs/cli-runbooks.md.

WHAT IT DOES
------------
1. If the configured `GraphStore` driver is PostgreSQL -- the operator has
   set `PYFORGE_GRAPHSTORE_OWNER=steward` in the environment, per
   `pyforge.scribe.graph_store_plugins`'s own documented environment-variable
   contract (`graph_store.py`'s `PG_GRAPHSTORE_OWNER`) -- this ensures the
   local PostgreSQL+pgvector cluster is up by shelling out to
   `pixi run -e pyforge-scribe-pg scribe-pg-up`, the SAME idempotent command
   an operator runs by hand (`scripts/scribe_pg.py`). The owner/env-var
   NAMES are read here as an external CONTRACT only -- this script never
   imports `pyforge.scribe` internals (AD-7: "other components integrate
   with Scribe via [the CLI], never by importing internal modules
   directly"). If bringing the cluster up fails (binaries unavailable,
   `pixi` missing, the composed `pyforge-scribe-pg` environment cannot
   solve, ...), this refuses cleanly -- prints why to stderr and exits 0
   WITHOUT attempting the compile, rather than ever reporting a red
   scheduled run for a driver this machine cannot confirm live.
2. Otherwise -- the default `FlatFileGraphStore` path (nothing to check),
   or the PostgreSQL cluster is confirmed live -- invokes
   `scribe graph compile --nightly` and propagates its exit code UNCHANGED.
   A genuine compile failure must still surface; only the PostgreSQL
   preflight step gets the "never fail red" treatment.

Never builds new compile capability, bounding, or locking: Story 3.3 already
shipped `scribe graph compile --nightly`'s own `flock -n`-safe, prompt-free,
exit-0-on-overlap contract (`pyforge/scribe/cli.py` ~L285-301); this script
only triggers it.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

#: Scribe's own external environment-variable contract (documented in
#: `pyforge.scribe.graph_store_plugins`'s module docstring) -- named here,
#: never imported (AD-7).
_GRAPHSTORE_OWNER_ENV = "PYFORGE_GRAPHSTORE_OWNER"
_POSTGRES_OWNER = "steward"

_COMPILE_CMD: list[str] = ["scribe", "graph", "compile", "--nightly"]


def _run(cmd: list[str]) -> int:
    """The one subprocess choke point -- tests inject a fake here rather
    than monkeypatching `subprocess.run` globally.

    A stale/relocated `pixi` binary or an unresolvable `scribe` executable
    raises `FileNotFoundError`/`OSError`, not a nonzero return code --
    caught here so both call sites (the PostgreSQL preflight, which already
    treats any nonzero as "refuse cleanly"; and the compile invocation,
    which propagates the return code as this script's own exit code) get a
    clean stderr message and a nonzero code instead of a raw traceback."""
    try:
        return subprocess.run(cmd).returncode
    except OSError as exc:
        print(
            f"scribe-nightly-trigger: failed to run {cmd!r}: {exc}",
            file=sys.stderr,
        )
        return 1


def _ensure_postgres_ready(*, run=_run, which=shutil.which) -> bool:
    """True when the configured PostgreSQL GraphStore is confirmed live (or
    was just started by this call); False means "refuse cleanly, do not
    compile this run" -- never raises.

    `PIXI_BIN` (set by the rendered systemd unit to `pixi`'s resolved
    absolute path, since a systemd-user session's PATH is not guaranteed to
    include it) is preferred over a fresh `shutil.which("pixi")` lookup,
    which still covers a manual/pixi-task invocation where PATH is normal.
    """
    pixi_bin = os.environ.get("PIXI_BIN") or which("pixi")
    if pixi_bin is None:
        print(
            "scribe-nightly-trigger: PostgreSQL GraphStore configured "
            f"({_GRAPHSTORE_OWNER_ENV}={_POSTGRES_OWNER!r}) but `pixi` is "
            "not on PATH (and PIXI_BIN is unset) -- refusing to compile "
            "against an unconfirmed store this run",
            file=sys.stderr,
        )
        return False
    cmd = [pixi_bin, "run", "-e", "pyforge-scribe-pg", "scribe-pg-up"]
    if run(cmd) != 0:
        print(
            "scribe-nightly-trigger: `pixi run -e pyforge-scribe-pg "
            "scribe-pg-up` did not succeed -- refusing to compile against "
            "an unconfirmed PostgreSQL GraphStore this run (never fails red "
            "for this; see docs/cli-runbooks.md)",
            file=sys.stderr,
        )
        return False
    return True


def main(*, run=_run, which=shutil.which) -> int:
    owner = os.environ.get(_GRAPHSTORE_OWNER_ENV, "scribe")
    if owner == _POSTGRES_OWNER and not _ensure_postgres_ready(run=run, which=which):
        return 0
    return run(_COMPILE_CMD)


if __name__ == "__main__":
    sys.exit(main())
