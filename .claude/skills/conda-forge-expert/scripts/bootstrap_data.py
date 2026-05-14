#!/usr/bin/env python3
"""
bootstrap_data.py — Single command to download / refresh ALL data the
conda-forge-expert skill (and the atlas) needs to operate. Runs the
full chain in dependency order, surfaces progress, and accepts a
`--fresh` flag for a hard reset.

What it does (in order):
  1. mapping cache       — PyPI ↔ conda name mapping (parselmouth → pypi_conda_map.json)
  2. CVE DB              — OSV.dev legacy DB (used by scan_for_vulnerabilities)
  3. vdb (multi-source)  — AppThreat vdb (~2.5 GB; used by Phase G + scan-project --vdb)
  4. cf_atlas            — conda repodata + feedstock-outputs + parselmouth + PyPI Simple
  5. cf_atlas Phase E    — cf-graph-countyfair node_attrs (~150 MB tarball)
  6. cf_atlas Phase J/K/L/M — dep graph + VCS upstream + extra registries + bot health
  7. cf_atlas Phase G/G' — vdb risk summary (latest version + per-version with PHASE_GP_ENABLED)
  8. cf_atlas Phase H    — PyPI current version (with yanked detection)
  9. cf_atlas Phase N    — live GitHub data (CI / issues / PRs) — only if --gh and gh auth present

CLI:
  bootstrap-data [--profile maintainer|admin|consumer]
                 [--fresh | --resume | --status] [--no-vdb] [--no-cf-atlas]
                 [--phase-h-source auto|pypi-json|cf-graph]
                 [--gh] [--maintainer HANDLE] [--dry-run]

  --profile MODE      : preset bundle of env-var defaults.
                         * maintainer — daily, scoped to one maintainer's
                           feedstocks; enables Phase E + Phase N (gh user
                           auto-detected) + PHASE_L_SOURCES auto-restricted
                           to populated registries in scope.
                         * admin — weekly, channel-wide; enables Phase E +
                           channel-wide Phase N + full Phase L.
                         * consumer — air-gap-friendly; Phase F via s3-parquet,
                           Phase H via cf-graph, no Phase N, no Phase D
                           universe upsert.
                         Explicit env vars and CLI flags win. Set
                         BUILD_CF_ATLAS_QUIET=1 to silence the no-profile
                         advisory printed at end-of-run.

  --fresh             : wipe `.claude/data/conda-forge-expert/` first (hard reset).
                         Preserves `cache/parquet/` (immutable historical S3
                         download cache, ~1.4 GB) by default; pair with
                         `--reset-cache` to nuke that too.
                         Defaults Phase H to the cf-graph offline source for a
                         fast (~1-2 min) cold start; falls back to pypi-json
                         on subsequent runs.
  --reset-cache       : with --fresh, also delete cache/parquet/.
  --yes / -y          : skip the 5-second confirmation countdown on --fresh.

Per-step timeouts (seconds) can be overridden via env vars
(set to a positive integer; unset/0 uses the default):
  BOOTSTRAP_MAPPING_CACHE_TIMEOUT  default 300
  BOOTSTRAP_CVE_DB_TIMEOUT         default 600
  BOOTSTRAP_VDB_TIMEOUT            default 3600
  BOOTSTRAP_CF_ATLAS_TIMEOUT       default 7200  (cold --fresh can take 50+ min)
  BOOTSTRAP_PHASE_GP_TIMEOUT       default 3600
  BOOTSTRAP_PHASE_N_TIMEOUT        default 3600
  --status            : print phase_state checkpoint table + per-phase
                         freshness summary, then exit (no execution).
  --resume            : default bootstrap is already resume-friendly because
                         every TTL-gated phase (F/G/G'/H/K/L) skips rows
                         it processed within its TTL, and Phases B/D/N now
                         write phase_state cursors. --resume is equivalent
                         to the default minus the --fresh option; the flag
                         exists for clarity in scripted workflows and
                         prints a status table on entry.
  --no-vdb            : skip the 2.5 GB vdb refresh (saves ~5–10 min).
  --no-cf-atlas       : skip the atlas rebuild (saves ~30 min cold + Phase F).
  --phase-h-source    : auto (default; cf-graph on --fresh else pypi-json),
                         pypi-json (real-time, with yanked detection), or
                         cf-graph (offline bulk from Phase E's tarball).
  --gh                : run Phase N (live GitHub data); requires `gh auth login`.
  --maintainer        : with --gh, scope Phase N to one maintainer.
  --dry-run           : print the steps without executing.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

DATA_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "data" / "conda-forge-expert"
)
REPO_ROOT = Path(__file__).resolve().parents[5]


# Per-step timeouts (seconds). Defaults sized for cold `--fresh` runs:
# cf-atlas alone can take 50+ min when Phase F+K+L each spend 20-30 min on
# network-bound fetches. Override any of these via env var if your environment
# is faster / slower than typical. Use `0` (or unset) to use the default.
_DEFAULT_TIMEOUTS: dict[str, int] = {
    "mapping_cache":  300,     # parselmouth refresh — usually <10s
    "cve_db":         600,     # OSV.dev download — usually ~10s
    "vdb":           3600,     # AppThreat refresh — usually 5-10 min, slack for cold
    "cf_atlas":      7200,     # cold --fresh worst-case: F~25 + K~30 + L~20 + others
    "phase_gp":      3600,     # per-version vuln scoring — can be 5-30 min
    "phase_n":       3600,     # live GitHub — channel-wide can be 30+ min
}


def _timeout_for(step: str) -> int:
    """Return effective timeout for `step` honouring `BOOTSTRAP_<STEP>_TIMEOUT` env."""
    env_key = f"BOOTSTRAP_{step.upper()}_TIMEOUT"
    raw = os.environ.get(env_key, "").strip()
    if raw:
        try:
            override = int(raw)
            if override > 0:
                return override
        except ValueError:
            print(f"  warning: ignoring invalid {env_key}={raw!r}")
    return _DEFAULT_TIMEOUTS[step]


# v8.0.0 — Persona profiles. `--profile <name>` injects a bundle of env-var
# defaults that select the right phase mix for each operator persona.
# Explicit env vars and explicit CLI flags always win (setdefault semantics).
#
# - maintainer: a feedstock maintainer running daily on their own scope.
#   Wants Phase E + Phase N with auto-detected gh user. Phase F/H auto-source.
# - admin: a channel-wide operator (mark-broken, archive sweeps). Wants
#   channel-wide Phase N (no PHASE_N_MAINTAINER). Weekly cadence.
# - consumer: air-gap-friendly read-only build. Wants Phase F via s3-parquet
#   and Phase H via cf-graph; no Phase N; no Phase D universe upsert.
PROFILES: dict[str, dict[str, str]] = {
    "maintainer": {
        "PHASE_E_ENABLED": "1",     # cf-graph cache (default-on for maintainer)
        "PHASE_N_ENABLED": "1",     # live GitHub data (auto-scoped)
        "PHASE_F_SOURCE":  "auto",  # atlas accepts "auto" (probe API → S3 fallback)
        # PHASE_H_SOURCE intentionally NOT set: "auto" is a bootstrap-data
        # CLI concept (resolves to cf-graph on --fresh, else pypi-json), but
        # the atlas itself only accepts "pypi-json" or "cf-graph". Leaving
        # it unset lets the atlas use its default ("pypi-json") and lets
        # bootstrap-data Step 4 resolve `--phase-h-source` via env_overrides
        # without leaking "auto" through `os.environ` to other subprocesses.
        # PHASE_N_MAINTAINER set dynamically from `gh api user`
        # PHASE_L_SOURCES set dynamically from populated registry columns
    },
    "admin": {
        "PHASE_E_ENABLED": "1",
        "PHASE_N_ENABLED": "1",     # channel-wide (no PHASE_N_MAINTAINER)
        "PHASE_F_SOURCE":  "auto",
        # PHASE_H_SOURCE intentionally unset — see maintainer profile note.
    },
    "consumer": {
        "PHASE_E_ENABLED": "1",
        "PHASE_N_ENABLED": "",       # opt-in stays opt-in
        "PHASE_F_SOURCE":  "s3-parquet",
        "PHASE_H_SOURCE":  "cf-graph",  # concrete atlas value (offline bulk)
        "PHASE_D_UNIVERSE_DISABLED": "1",
    },
}


def _auto_detect_gh_user(timeout: int = 5) -> str | None:
    """Return the authenticated GitHub login via `gh api user --jq .login`.

    Returns None on missing-gh / unauth / timeout — caller prints a warning
    and proceeds with channel-wide Phase N (slower but correct). Never
    raises; this is a best-effort enrichment.
    """
    try:
        result = subprocess.run(
            ["gh", "api", "user", "--jq", ".login"],
            capture_output=True, text=True, timeout=timeout,
        )
    except FileNotFoundError:
        return None
    except subprocess.TimeoutExpired:
        return None
    if result.returncode != 0:
        return None
    login = result.stdout.strip()
    return login or None


# Columns in `packages` that mark which extra registry a feedstock tracks.
# Order matches `_PHASE_L_RESOLVERS` in conda_forge_atlas.py for consistency.
# `maven_coord` is a special-case column (group:artifact pair, not a name).
_PHASE_L_NAME_COLUMNS: dict[str, str] = {
    "npm":      "npm_name",
    "cran":     "cran_name",
    "cpan":     "cpan_name",
    "luarocks": "luarocks_name",
    "maven":    "maven_coord",
}


def _auto_detect_phase_l_sources(
    maintainer: str | None,
    db_path: Path | None = None,
) -> str | None:
    """Return a comma-separated PHASE_L_SOURCES restriction or None.

    Queries `v_actionable_packages` (schema v21+) for which `<source>_name`
    columns are populated. If `maintainer` is provided, the scope is
    further restricted to that maintainer's packages via the
    `package_maintainers` junction.

    Returns None when the DB is missing, the view is unavailable, or
    every registry is empty in scope — in those cases the caller should
    leave PHASE_L_SOURCES unset (Phase L runs against all 8 resolvers
    by default).
    """
    path = db_path or (DATA_DIR / "cf_atlas.db")
    if not path.exists():
        return None
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=2)
    except sqlite3.OperationalError:
        return None
    try:
        # Confirm the view exists; cold DBs at v20 or earlier won't have it.
        have_view = bool(list(conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='view' "
            "AND name='v_actionable_packages'"
        )))
        if not have_view:
            return None
        populated: list[str] = []
        for source, col in _PHASE_L_NAME_COLUMNS.items():
            if maintainer:
                # `package_maintainers(conda_name, maintainer_id)` joins to
                # `maintainers(id, handle)` — the handle is on the latter.
                sql = (
                    f"SELECT 1 FROM v_actionable_packages p "
                    f"JOIN package_maintainers pm ON pm.conda_name = p.conda_name "
                    f"JOIN maintainers m ON m.id = pm.maintainer_id "
                    f"WHERE p.{col} IS NOT NULL AND LOWER(m.handle) = LOWER(?) "
                    f"LIMIT 1"
                )
                params: tuple = (maintainer,)
            else:
                sql = f"SELECT 1 FROM v_actionable_packages WHERE {col} IS NOT NULL LIMIT 1"
                params = ()
            try:
                hit = conn.execute(sql, params).fetchone()
            except sqlite3.OperationalError:
                hit = None
            if hit:
                populated.append(source)
    finally:
        conn.close()
    if not populated:
        return None
    return ",".join(populated)


def _resolve_profile_env(
    profile: str | None,
    db_path: Path | None = None,
) -> tuple[dict[str, str], list[str]]:
    """Compute the env-var dict implied by `--profile`.

    Returns a `(env_defaults, warnings)` pair. Caller merges `env_defaults`
    via `dict.setdefault` so explicit user env vars win. `warnings` carries
    advisory lines to print before phase dispatch (e.g., gh auto-detect
    failure).
    """
    if profile is None:
        return {}, []
    if profile not in PROFILES:
        raise ValueError(f"unknown --profile {profile!r}; "
                         f"choose from {sorted(PROFILES)}")
    env = dict(PROFILES[profile])
    warnings: list[str] = []
    if profile == "maintainer":
        # If the operator already set PHASE_N_MAINTAINER in env, honor that.
        existing = os.environ.get("PHASE_N_MAINTAINER", "").strip()
        if existing:
            env.setdefault("PHASE_N_MAINTAINER", existing)
            user = existing
        else:
            user = _auto_detect_gh_user()
            if user:
                env["PHASE_N_MAINTAINER"] = user
            else:
                warnings.append(
                    "--profile maintainer: `gh api user` auto-detection failed; "
                    "Phase N will run channel-wide (slower but correct). "
                    "Set PHASE_N_MAINTAINER=<handle> or run `gh auth login` to scope it."
                )
        # Restrict PHASE_L_SOURCES to populated registries in scope.
        if not os.environ.get("PHASE_L_SOURCES"):
            sources = _auto_detect_phase_l_sources(user, db_path=db_path)
            if sources:
                env["PHASE_L_SOURCES"] = sources
    return env, warnings


def _run(label: str, cmd: list[str], env_overrides: dict | None = None,
         dry_run: bool = False, timeout: int = 1800) -> bool:
    """Run a step with banner output. Returns True on success."""
    bar = "─" * 70
    print(f"\n{bar}")
    print(f"  → {label}")
    print(f"  $ {' '.join(cmd)}")
    if env_overrides:
        for k, v in env_overrides.items():
            print(f"    env {k}={v}")
    print(bar)
    if dry_run:
        print(f"  [dry-run] would execute the above")
        return True
    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)
    t0 = time.monotonic()
    try:
        rc = subprocess.run(cmd, env=env, timeout=timeout).returncode
    except subprocess.TimeoutExpired:
        print(f"  ⚠ {label} timed out after {timeout}s — continuing")
        return False
    elapsed = time.monotonic() - t0
    ok = rc == 0
    print(f"  {'✓' if ok else '✗'} {label} ({elapsed:.1f}s, rc={rc})")
    return ok


# Paths preserved across --fresh by default. The S3 parquet files at
# cache/parquet/<YYYY-MM>.parquet are immutable historical data (current
# month is always re-fetched by `_parquet_cache.ensure_month`); re-downloading
# them costs ~30 min for no benefit. Override with --fresh --reset-cache to
# delete everything unconditionally.
_PRESERVED_RELATIVE_PATHS = ("cache/parquet",)


def _move_preserved_aside(stash_dir: Path) -> list[tuple[Path, Path]]:
    """Move preserved subdirectories to a stash before deletion. Returns the
    list of `(stashed_path, original_path)` pairs so callers can restore.
    """
    moved: list[tuple[Path, Path]] = []
    for rel in _PRESERVED_RELATIVE_PATHS:
        src = DATA_DIR / rel
        if not src.exists():
            continue
        dest = stash_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))
        moved.append((dest, src))
    return moved


def _restore_preserved(moved: list[tuple[Path, Path]]) -> None:
    """Move stashed subdirectories back into the freshly-recreated DATA_DIR."""
    for stashed, original in moved:
        original.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(stashed), str(original))


def _confirm_destructive(label: str, size_mb: float, assume_yes: bool) -> bool:
    """Block on a 5-second countdown unless `--yes`. Returns False if aborted.

    Quiet by default if `assume_yes` is True (CI, scripts). Interactive callers
    see the countdown and can Ctrl+C to abort. Non-TTY callers (pipes, redirect
    stdin) also see the countdown for visibility; they cannot Ctrl+C as easily
    but the kill signal still works.
    """
    if assume_yes:
        return True
    print(f"  ⚠  {label} will delete ~{size_mb:.1f} MB from {DATA_DIR}")
    print(f"     Press Ctrl+C within 5 seconds to abort; or pass --yes to skip this prompt.")
    try:
        for remaining in range(5, 0, -1):
            print(f"     starting in {remaining}s...", end="\r", flush=True)
            time.sleep(1)
        print("     proceeding...                ")
        return True
    except KeyboardInterrupt:
        print("\n  ✗ Aborted by user (Ctrl+C).")
        return False


def hard_reset(
    dry_run: bool = False,
    reset_cache: bool = False,
    assume_yes: bool = False,
) -> bool:
    """Delete the data dir and recreate it.

    By default, paths listed in `_PRESERVED_RELATIVE_PATHS` (the S3 parquet
    cache) survive the reset — they're immutable historical data and the
    re-download cost is meaningful (~30 min, ~1.4 GB). Pass `reset_cache=True`
    to wipe everything unconditionally.

    Unless `assume_yes` is True or `dry_run` is True, prompts with a 5-second
    countdown that the caller can Ctrl+C to abort. Returns True on success or
    dry-run, False if the user aborted.
    """
    if not DATA_DIR.exists():
        print(f"  Data dir does not exist; nothing to reset: {DATA_DIR}")
        return True
    label = "HARD RESET (reset-cache)" if reset_cache else "HARD RESET"
    size_mb = sum(
        f.stat().st_size for f in DATA_DIR.rglob("*") if f.is_file()
    ) / 1e6
    if dry_run:
        preserved_note = "" if reset_cache else " (preserves cache/parquet)"
        print(f"  ⚠  {label}: would delete {DATA_DIR}")
        print(f"  [dry-run] would delete ~{size_mb:.1f} MB{preserved_note}")
        return True
    if not _confirm_destructive(label, size_mb, assume_yes):
        return False
    print(f"  ⚠  {label}: deleting {DATA_DIR}")
    stash = DATA_DIR.parent / f".{DATA_DIR.name}.stash"
    if stash.exists():
        shutil.rmtree(stash)
    stash.mkdir(parents=True)
    moved: list[tuple[Path, Path]] = []
    try:
        if not reset_cache:
            moved = _move_preserved_aside(stash)
        shutil.rmtree(DATA_DIR)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        _restore_preserved(moved)
    finally:
        if stash.exists():
            shutil.rmtree(stash, ignore_errors=True)
    preserved_note = "" if reset_cache else f" (preserved {len(moved)} path(s))"
    print(f"  ✓ Data dir reset.{preserved_note}")
    return True


def print_status() -> int:
    """Print the cf_atlas DB's phase_state checkpoint table + a per-phase
    freshness summary. Returns 0 on success, 2 if the DB is missing."""
    import datetime as _dt
    import sqlite3

    db_path = DATA_DIR / "cf_atlas.db"
    if not db_path.exists():
        print(f"  No DB at {db_path} — run `bootstrap-data --fresh` to build.")
        return 2
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    print("─" * 70)
    print("  phase_state checkpoints")
    print("─" * 70)
    try:
        rows = list(conn.execute(
            "SELECT phase_name, status, items_completed, items_total, "
            "last_completed_cursor, run_started_at, run_completed_at, last_error "
            "FROM phase_state ORDER BY phase_name"
        ))
    except sqlite3.OperationalError:
        print("  phase_state table missing (DB predates v7.7; rebuild via --fresh)")
        return 0
    if not rows:
        print("  (no checkpoints recorded yet)")
    else:
        print(f"  {'Phase':<6} {'Status':<13} {'Progress':>15}  {'Cursor':<40} {'Last run'}")
        for r in rows:
            ts = r["run_completed_at"] or r["run_started_at"]
            when = _dt.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") if ts else "-"
            progress = (f"{r['items_completed'] or 0:>6,}/"
                        f"{r['items_total'] or 0:<6,}")
            cursor = (r["last_completed_cursor"] or "-")[:40]
            print(f"  {r['phase_name']:<6} {r['status']:<13} {progress:>15}  "
                  f"{cursor:<40} {when}")
            if r["last_error"]:
                print(f"         last_error: {r['last_error']}")

    # Per-phase TTL freshness — how many rows still need processing
    print()
    print("─" * 70)
    print("  TTL-gated phase eligibility (rows ready for next run)")
    print("─" * 70)
    ttl_columns = [
        ("F (downloads)",      "downloads_fetched_at",       7,
         "downloads_last_error"),
        ("G (vdb summary)",    "vdb_scanned_at",             7,
         "vdb_last_error"),
        ("H (pypi version)",   "pypi_version_fetched_at",    7,
         "pypi_version_last_error"),
        ("K (vcs upstream)",   "github_version_fetched_at",  7,
         "github_version_last_error"),
    ]
    import time as _time
    now = int(_time.time())
    for label, col, default_ttl_days, err_col in ttl_columns:
        cutoff = now - default_ttl_days * 86400
        try:
            stale = conn.execute(
                f"SELECT COUNT(*) FROM packages "
                f"WHERE COALESCE({col}, 0) < ? "
                f"  AND ({err_col} IS NULL OR length({err_col}) = 0)",
                (cutoff,),
            ).fetchone()[0]
            errors = conn.execute(
                f"SELECT COUNT(*) FROM packages WHERE {err_col} IS NOT NULL "
                f"AND length({err_col}) > 0"
            ).fetchone()[0]
            print(f"  {label:<22} {stale:>7,} stale,  {errors:>7,} with last_error")
        except sqlite3.OperationalError as e:
            print(f"  {label:<22} (column missing: {e})")

    conn.close()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bootstrap / refresh all conda-forge-expert data in one command."
    )
    parser.add_argument("--profile",
                        choices=sorted(PROFILES.keys()),
                        default=None,
                        help="Persona-aware preset bundle of env-var defaults "
                             "(maintainer / admin / consumer). Explicit env "
                             "vars and CLI flags always win. See module "
                             "docstring or `reference/atlas-phases-overview.md` "
                             "for the full profile reference.")
    parser.add_argument("--fresh", action="store_true",
                        help="Wipe .claude/data/conda-forge-expert/ first "
                             "(preserves cache/parquet by default; pair with "
                             "--reset-cache to nuke that too)")
    parser.add_argument("--reset-cache", action="store_true", dest="reset_cache",
                        help="With --fresh, also delete cache/parquet (the "
                             "S3 download cache; ~1.4 GB, ~30 min to re-fetch)")
    parser.add_argument("--yes", "-y", action="store_true", dest="assume_yes",
                        help="Skip the 5-second confirmation countdown on "
                             "--fresh. Use in CI / scripts.")
    parser.add_argument("--status", action="store_true",
                        help="Print the phase_state checkpoint table and "
                             "per-phase freshness summary; exit without "
                             "running anything.")
    parser.add_argument("--resume", action="store_true",
                        help="Print the status table on entry, then run the "
                             "standard bootstrap (already resume-friendly "
                             "via TTL gates + phase_state cursors).")
    parser.add_argument("--no-vdb", action="store_true", dest="no_vdb",
                        help="Skip the vdb refresh (saves 5-10 min + 2.5 GB on disk)")
    parser.add_argument("--no-cf-atlas", action="store_true", dest="no_cf_atlas",
                        help="Skip the cf_atlas rebuild")
    parser.add_argument("--no-cve-db", action="store_true", dest="no_cve_db",
                        help="Skip the legacy OSV.dev CVE DB refresh")
    parser.add_argument("--no-mapping", action="store_true", dest="no_mapping",
                        help="Skip the parselmouth name-mapping refresh")
    parser.add_argument("--gh", action="store_true",
                        help="Run Phase N (live GitHub data); requires gh auth")
    parser.add_argument("--maintainer", default=None,
                        help="With --gh, scope Phase N to one maintainer "
                             "(recommended unless you want a 6-hour run)")
    parser.add_argument("--with-per-version-vulns", action="store_true",
                        dest="with_pgp",
                        help="Run Phase G' (per-version vuln scoring; needs vuln-db env)")
    parser.add_argument("--phase-h-source",
                        choices=["auto", "pypi-json", "cf-graph"],
                        default="auto",
                        help="Phase H source. 'auto' uses cf-graph on --fresh "
                             "(fast cold-start, no network for Phase H) and "
                             "pypi-json otherwise. Override to force one path.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print steps without executing")
    args = parser.parse_args()

    print("═" * 70)
    print("  conda-forge-expert · bootstrap-data")
    print(f"  Data dir:  {DATA_DIR}")
    print(f"  Repo:      {REPO_ROOT}")
    print(f"  Mode:      {'dry-run' if args.dry_run else 'live'}")
    print(f"  Profile:   {args.profile or '(none — see end-of-run advisory)'}")
    print("═" * 70)

    # Resolve --profile into a dict of env-var defaults. Apply via
    # `os.environ.setdefault` so explicit user-set env vars always win.
    # Profile may also imply args.gh / args.maintainer / args.phase_h_source
    # when those aren't already set.
    profile_env, profile_warnings = _resolve_profile_env(args.profile)
    for warn in profile_warnings:
        print(f"  ⚠  {warn}")
    for key, value in profile_env.items():
        os.environ.setdefault(key, value)
    if args.profile in ("maintainer", "admin") and not args.gh:
        args.gh = True
    if args.profile == "maintainer" and not args.maintainer:
        # The profile's PHASE_N_MAINTAINER (auto-detected or env-supplied) is
        # the recommended scope; lift it onto args.maintainer for the Phase N
        # command line.
        detected = os.environ.get("PHASE_N_MAINTAINER", "").strip()
        if detected:
            args.maintainer = detected
    if args.profile == "consumer" and args.phase_h_source == "auto":
        # Consumer profile pins Phase H to cf-graph (air-gap friendly).
        args.phase_h_source = "cf-graph"

    # --status: print the status table and exit. Mutually exclusive with
    # --fresh in spirit (you ask for one or the other) but we don't enforce
    # it as a hard error — let users combine them if they want.
    if args.status:
        return print_status()

    # --resume: print status on entry, then continue with the normal bootstrap.
    # This is mostly a UX signal — TTL gates + phase_state already make
    # repeated runs cheap.
    if args.resume:
        print_status()
        if args.fresh:
            print("  warning: --resume + --fresh both set; --fresh takes precedence.")

    if args.fresh:
        if not hard_reset(
            args.dry_run,
            reset_cache=args.reset_cache,
            assume_yes=args.assume_yes,
        ):
            return 130  # standard SIGINT-style abort code
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    results: list[tuple[str, bool]] = []

    # Step 1 — mapping cache (parselmouth)
    if not args.no_mapping:
        ok = _run("Refresh PyPI↔conda mapping cache",
                  ["pixi", "run", "-e", "local-recipes",
                   "update-mapping-cache"],
                  dry_run=args.dry_run, timeout=_timeout_for("mapping_cache"))
        results.append(("mapping-cache", ok))

    # Step 2 — legacy OSV CVE DB
    if not args.no_cve_db:
        ok = _run("Refresh OSV.dev CVE DB (legacy, used by scan_for_vulnerabilities)",
                  ["pixi", "run", "-e", "local-recipes", "update-cve-db"],
                  dry_run=args.dry_run, timeout=_timeout_for("cve_db"))
        results.append(("cve-db", ok))

    # Step 3 — vdb (heavy)
    if not args.no_vdb:
        ok = _run("Refresh vdb (AppThreat multi-source vulnerability DB; ~2.5 GB)",
                  ["pixi", "run", "-e", "vuln-db", "vdb-refresh"],
                  dry_run=args.dry_run, timeout=_timeout_for("vdb"))
        results.append(("vdb-refresh", ok))

    # Step 4 — cf_atlas full build with all default + cf-graph + Phase L
    if not args.no_cf_atlas:
        cmd = ["pixi", "run", "-e", "local-recipes", "build-cf-atlas"]
        env = {"PHASE_E_ENABLED": "1"}  # pull cf-graph
        # Phase H source dispatch. cf-graph is fast + offline but lags pypi.org
        # by hours; the auto policy picks cf-graph only on --fresh (where
        # speed-of-cold-start matters and a few hours of lag is acceptable
        # because the DB is brand new anyway).
        if args.phase_h_source == "auto":
            phase_h = "cf-graph" if args.fresh else "pypi-json"
        else:
            phase_h = args.phase_h_source
        env["PHASE_H_SOURCE"] = phase_h
        ok = _run(f"Build cf_atlas (B/B.5/B.6/C/C.5/D/E/E.5/F/G/H[{phase_h}]/J/K/L/M)",
                  cmd, env_overrides=env, dry_run=args.dry_run,
                  timeout=_timeout_for("cf_atlas"))
        results.append(("cf-atlas-build", ok))

    # Step 5 — Phase G' per-version vuln scoring (opt-in)
    if args.with_pgp and not args.no_vdb:
        cmd = ["pixi", "run", "-e", "vuln-db", "build-cf-atlas"]
        env = {"PHASE_GP_ENABLED": "1"}
        ok = _run("Phase G' — per-version vuln scoring (vuln-db env)",
                  cmd, env_overrides=env, dry_run=args.dry_run,
                  timeout=_timeout_for("phase_gp"))
        results.append(("phase-gp", ok))

    # Step 6 — Phase N (live GitHub data) — opt-in via --gh.
    #
    # When a profile injects `PHASE_N_ENABLED=1` into `os.environ` and Step 4
    # ran, the cf-atlas subprocess already executed Phase N (via env
    # inheritance). Re-invoking build-cf-atlas here would redo every phase
    # and crash on the inherited `PHASE_H_SOURCE` (bootstrap-data CLI's
    # "auto" is not an atlas-valid value). Skip the redundant invocation.
    phase_n_ran_in_step4 = (
        not args.no_cf_atlas
        and bool(os.environ.get("PHASE_N_ENABLED", "").strip())
    )
    if args.gh and phase_n_ran_in_step4:
        print()
        print("  ⓘ Phase N already ran inside the cf_atlas build step "
              "(PHASE_N_ENABLED was in env via --profile). Skipping the "
              "redundant Phase N invocation.")
    elif args.gh:
        cmd = ["pixi", "run", "-e", "local-recipes", "build-cf-atlas"]
        env = {"PHASE_N_ENABLED": "1"}
        if args.maintainer:
            env["PHASE_N_MAINTAINER"] = args.maintainer
        ok = _run("Phase N — live GitHub data (CI / issues / PRs)",
                  cmd, env_overrides=env, dry_run=args.dry_run,
                  timeout=_timeout_for("phase_n"))
        results.append(("phase-n", ok))

    print("\n" + "═" * 70)
    print("  Bootstrap summary")
    print("═" * 70)
    for label, ok in results:
        marker = "✓" if ok else "✗"
        print(f"  {marker} {label}")
    failed = [l for l, ok in results if not ok]
    _print_no_profile_advisory(args.profile)
    if failed:
        print(f"\n  {len(failed)} step(s) failed: {failed}")
        return 1
    print(f"\n  All {len(results)} step(s) completed successfully.")
    return 0


def _print_no_profile_advisory(profile: str | None) -> None:
    """Print the v8.0.0 advisory recommending `--profile maintainer` when
    the operator ran without `--profile`. Opt out via BUILD_CF_ATLAS_QUIET=1.
    The advisory is the MAJOR-bump signal for the v7.x → v8.0.0 default-
    behavior shift; no invocation breaks, but the documented default flipped.
    """
    if profile is not None:
        return
    if os.environ.get("BUILD_CF_ATLAS_QUIET", "").strip():
        return
    print()
    print("  ⓘ No --profile specified. Consider `--profile maintainer` for")
    print("    the default maintainer-scoped atlas (enables Phase E + Phase N")
    print("    with auto-scoping). See `reference/atlas-phases-overview.md`")
    print("    for the full profile reference. Set BUILD_CF_ATLAS_QUIET=1")
    print("    to silence this advisory.")


if __name__ == "__main__":
    sys.exit(main())
