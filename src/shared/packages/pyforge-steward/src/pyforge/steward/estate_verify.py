"""``steward estate verify`` — prove a refreshed lock in a detached worktree (Story 100.4 / CAP-167)."""

from __future__ import annotations

import hashlib
import json
import shlex
import sys
import time
import tomllib
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Callable, Protocol

import yaml

from .estate import (
    EstateDeps,
    SubprocessRunner,
    _ensure_flag,
    _load_journal,
    _next_journal_path,
    _production_deps,
)
from .estate_realize import RealizeDeps, run_probe
from .interfaces import DutyResult
from .preflight import Lane, list_preflight_lanes
from .preflight_ci import select_lanes_for_paths
from .provision import load_pixi_environments

GUILD_SIZE_BOUND_MB = 2048
OTHER_PLATFORMS = ("osx-arm64", "win-64")
WORKTREE_REL = Path(".steward/estate-verify/worktree")
VERIFY_CHANGED_PATHS = ("pixi.toml", "pixi.lock")
CI_SURFACES_REL = Path("docs/governance/ci-surfaces.yaml")

DEFAULT_TIER: tuple[str, ...] = (
    "pyforge-guild",
    "pyforge-core",
    "pyforge-testing-kit",
    "pyforge-atlas",
    "pyforge-doctor",
    "pyforge-herald",
    "pyforge-marshal",
    "pyforge-mason",
    "pyforge-scribe",
    "pyforge-steward",
    "pyforge-warden",
    "platform-ci-test",
    "pyforge-foundry-full",
)

MANUAL_ROWS: tuple[tuple[str, str, str], ...] = (
    (
        "atlas-browser-gate",
        "CI=1 pixi run --frozen -e pyforge-atlas pyforge-atlas-test",
        "pyforge-atlas",
    ),
    (
        "herald-browser-check",
        "pixi run --frozen -e pyforge-herald pyforge-herald-browser-check",
        "pyforge-herald",
    ),
    (
        "scribe-postgres",
        "pixi run -e pyforge-guild scribe-pg-up && pixi run --frozen -e pyforge-scribe pyforge-scribe-test",
        "pyforge-scribe",
    ),
)


class _Completed(Protocol):
    args: list[str] | str
    returncode: int
    stdout: str
    stderr: str


@dataclass
class VerifyDeps:
    root: Path
    runner: SubprocessRunner
    head_sha: Callable[[], str] = field(default=lambda: "deadbeef")
    platform: Callable[[], str] = field(default=lambda: "linux-64")
    flag_on: Callable[[], bool] = field(default=lambda: True)
    enforce_require: bool = True
    ci_surfaces_path: Path | None = None
    pause_overrides: dict[str, tuple[str, str]] | None = None  # lane task -> (switch, since)


def _lock_sha(root: Path) -> str:
    path = root / "pixi.lock"
    if not path.is_file():
        return "missing"
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest[:16]


def _load_pixi_document(root: Path) -> dict[str, Any]:
    data = tomllib.loads((root / "pixi.toml").read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _env_platforms(document: dict[str, Any], env_name: str) -> frozenset[str] | None:
    raw = document.get("environments", {}).get(env_name)
    if isinstance(raw, dict):
        plats = raw.get("platforms")
        if isinstance(plats, list):
            return frozenset(str(p) for p in plats)
    return None


def _env_supported(document: dict[str, Any], env_name: str, platform: str) -> bool:
    plats = _env_platforms(document, env_name)
    if plats is None:
        return True
    return platform in plats


def _environment_holding_task(pixi_data: dict[str, Any], task: str, *, root: Path) -> str | None:
    """Resolve which ``[environments]`` row composes the feature that owns ``task``."""
    owning_features: set[str] = set()
    for feat_name, feat in pixi_data.get("feature", {}).items():
        tasks = feat.get("tasks") if isinstance(feat, dict) else None
        if isinstance(tasks, dict) and task in tasks:
            owning_features.add(str(feat_name))
    if not owning_features:
        return None
    for env_name, env_feats in load_pixi_environments(cwd=root).items():
        if owning_features.intersection(env_feats):
            return env_name
    return None


def _tier_environments_from_root(root: Path, *, all_envs: bool) -> list[str]:
    all_names = sorted(load_pixi_environments(cwd=root))
    if all_envs:
        return all_names
    known = set(all_names)
    return [e for e in DEFAULT_TIER if e in known]


def _du_sm_mb(runner: SubprocessRunner, path: Path, cwd: Path) -> int | None:
    proc = runner(["du", "-sm", str(path)], cwd)
    if proc.returncode != 0:
        return None
    line = (proc.stdout or "").strip().split()
    if not line:
        return None
    try:
        return int(line[0])
    except ValueError:
        return None


def _load_ci_pauses(deps: VerifyDeps) -> dict[str, tuple[str, str]]:
    if deps.pause_overrides is not None:
        return dict(deps.pause_overrides)
    path = deps.ci_surfaces_path if deps.ci_surfaces_path is not None else deps.root / CI_SURFACES_REL
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {}
    pauses: dict[str, tuple[str, str]] = {}
    for row in data.get("surfaces") or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("state") or "") != "paused":
            continue
        switch = str(row.get("switch") or "")
        since = str(row.get("paused_since") or "")
        twin = str(row.get("local_twin") or "")
        job = str(row.get("job") or "")
        lane_key = twin.split()[0] if twin else job
        if lane_key:
            pauses[lane_key] = (switch, since)
    return pauses


def _remove_worktree(deps: VerifyDeps, wt: Path) -> None:
    if not wt.exists():
        return
    deps.runner(["git", "worktree", "remove", "--force", str(wt)], deps.root)


def _add_detached_worktree(deps: VerifyDeps, tip: str) -> tuple[Path, _Completed]:
    wt = deps.root / WORKTREE_REL
    wt.parent.mkdir(parents=True, exist_ok=True)
    if wt.exists():
        _remove_worktree(deps, wt)
    argv = ["git", "worktree", "add", "--detach", str(wt), tip]
    proc = deps.runner(argv, deps.root)
    return wt, proc


def _run_timed(
    deps: VerifyDeps,
    argv: list[str],
    cwd: Path,
    *,
    budget_seconds: float | None,
    started: float,
) -> tuple[_Completed | _FakeCompleted, float, str | None]:
    if budget_seconds is not None and (time.monotonic() - started) >= budget_seconds:
        return _FakeCompleted(argv, 124), 0.0, "timed-out"
    t0 = time.monotonic()
    proc = deps.runner(argv, cwd)
    elapsed = time.monotonic() - t0
    if budget_seconds is not None and elapsed > budget_seconds:
        return proc, elapsed, "timed-out"
    return proc, elapsed, None


@dataclass
class _FakeCompleted:
    args: list[str]
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""


_TAIL_LINES = 15


def _output_tail(proc: object) -> str:
    """The last lines a red step printed, so a journal row says why it failed."""
    text = "\n".join(
        part for part in (getattr(proc, "stdout", "") or "", getattr(proc, "stderr", "") or "") if part.strip()
    )
    return "\n".join(text.strip().splitlines()[-_TAIL_LINES:])


def _row_verdict(exit_code: int, *, special: str | None = None) -> str:
    if special:
        return special
    return "ok" if exit_code == 0 else "red"


def _platform_status(
    *,
    run_platform: str,
    lock_check_ok: bool,
    lock_sha: str,
) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    out[run_platform] = {
        "lock_sha": lock_sha,
        "verdict": "confirmed" if lock_check_ok else "unsolved",
    }
    for plat in OTHER_PLATFORMS:
        out[plat] = {
            "lock_sha": lock_sha,
            "verdict": "lock-solved" if lock_check_ok else "unsolved",
        }
    return out


def run_verify(
    deps: VerifyDeps,
    *,
    env_filter: str | None,
    lane_filter: str | None,
    probe_filter: str | None,
    all_envs: bool,
    keep: bool,
    ignore_ci_pauses: bool,
    budget_minutes: float | None,
) -> DutyResult:
    estate = EstateDeps(
        root=deps.root,
        runner=deps.runner,
        head_sha=deps.head_sha,
        platform=deps.platform,
        flag_on=deps.flag_on,
        enforce_require=deps.enforce_require,
    )
    refused = _ensure_flag(estate)
    if refused is not None:
        return refused

    run_platform = deps.platform()
    document = _load_pixi_document(deps.root)
    budget_seconds = budget_minutes * 60.0 if budget_minutes is not None else None
    rows: list[dict[str, Any]] = []
    any_red = False
    prev_guild_mb: int | None = None

    tip = deps.head_sha()
    wt, wt_proc = _add_detached_worktree(deps, tip)
    rows.append(
        {
            "kind": "worktree",
            "platform": run_platform,
            "verdict": _row_verdict(wt_proc.returncode),
            "exit": wt_proc.returncode,
            "seconds": 0.0,
            "argv": list(wt_proc.args) if isinstance(wt_proc.args, list) else [str(wt_proc.args)],
        }
    )
    if wt_proc.returncode != 0:
        any_red = True
        return _finish_verify(
            deps,
            rows=rows,
            any_red=True,
            run_platform=run_platform,
            lock_check_ok=False,
            keep=keep,
            wt=wt,
            summary="estate verify: git worktree add failed",
        )

    lock_argv = ["pixi", "lock", "--check"]
    lock_proc = deps.runner(lock_argv, wt)
    lock_check_ok = lock_proc.returncode == 0
    lock_sha = _lock_sha(deps.root)
    rows.append(
        {
            "kind": "lock-check",
            "platform": run_platform,
            "verdict": "ok" if lock_check_ok else "red",
            "exit": lock_proc.returncode,
            "seconds": 0.0,
            "argv": lock_argv,
        }
    )
    if not lock_check_ok:
        any_red = True

    for plat in OTHER_PLATFORMS:
        rows.append(
            {
                "kind": "platform",
                "name": plat,
                "platform": plat,
                "verdict": "lock-solved" if lock_check_ok else "unsolved",
                "exit": 0,
                "seconds": 0.0,
            }
        )

    scoped = bool(env_filter or lane_filter or probe_filter)
    run_full = not scoped

    env_names = _tier_environments_from_root(deps.root, all_envs=all_envs)
    if env_filter:
        env_names = [e for e in env_names if e == env_filter]
    elif not run_full:
        env_names = []

    install_started = time.monotonic()
    for env_name in env_names:
        if not _env_supported(document, env_name, run_platform):
            rows.append(
                {
                    "kind": "environment",
                    "name": env_name,
                    "platform": run_platform,
                    "verdict": "lock-solved",
                    "exit": 0,
                    "seconds": 0.0,
                    "size_delta_mb": None,
                }
            )
            continue
        argv = ["pixi", "install", "--frozen", "-e", env_name]
        proc, seconds, special = _run_timed(deps, argv, wt, budget_seconds=budget_seconds, started=install_started)
        verdict = _row_verdict(proc.returncode, special=special)
        if verdict != "ok":
            any_red = True
        size_delta: int | None = None
        if env_name == "pyforge-guild":
            # The env, not .pixi: .pixi/bld holds pixi-build's cache for the path-dependency
            # packages (about 1 GB), which is not the install footprint CAP-5 bounds.
            guild_mb = _du_sm_mb(deps.runner, wt / ".pixi" / "envs" / "pyforge-guild", wt)
            if guild_mb is not None:
                if prev_guild_mb is not None:
                    size_delta = guild_mb - prev_guild_mb
                prev_guild_mb = guild_mb
                rows.append(
                    {
                        "kind": "guild-bound",
                        "platform": run_platform,
                        "verdict": "ok" if guild_mb <= GUILD_SIZE_BOUND_MB else "red",
                        "exit": 0 if guild_mb <= GUILD_SIZE_BOUND_MB else 1,
                        "seconds": 0.0,
                        "size_mb": guild_mb,
                        "bound_mb": GUILD_SIZE_BOUND_MB,
                    }
                )
                if guild_mb > GUILD_SIZE_BOUND_MB:
                    any_red = True
        rows.append(
            {
                "kind": "environment",
                "name": env_name,
                "platform": run_platform,
                "verdict": verdict,
                "exit": proc.returncode,
                "seconds": round(seconds, 3),
                "size_delta_mb": size_delta,
                "argv": argv,
                "output_tail": _output_tail(proc) if proc.returncode != 0 else None,
            }
        )

    pixi_data = document
    pauses = _load_ci_pauses(deps)
    if run_full or lane_filter:
        try:
            # pr-preflight runs from -e pyforge-guild (the pre-push hook); a lane with no
            # explicit env runs there, not in the pyforge-steward env verify runs from.
            lanes = list_preflight_lanes(pixi_data, invoking_env="pyforge-guild")
        except Exception:  # noqa: BLE001
            lanes = []
        selection = select_lanes_for_paths(deps.root, lanes, pixi_data, VERIFY_CHANGED_PATHS)
    else:
        selection = None

    if selection is not None:
        for lane_verdict in selection.verdicts:
            if not lane_verdict.selected:
                continue
            lane = Lane(lane_verdict.task, lane_verdict.environment, ())
            if lane_filter and lane.task != lane_filter:
                continue
            pause = pauses.get(lane.task)
            if pause and not ignore_ci_pauses:
                switch, since = pause
                rows.append(
                    {
                        "kind": "lane",
                        "name": lane.task,
                        "environment": lane.environment,
                        "platform": run_platform,
                        "verdict": f"skipped: paused in CI ({switch} since {since})",
                        "exit": 0,
                        "seconds": 0.0,
                    }
                )
                continue
            argv = [
                "pixi",
                "run",
                "--frozen",
                "--skip-deps",
                "-e",
                lane.environment,
                lane.task,
            ]
            proc, seconds, special = _run_timed(deps, argv, wt, budget_seconds=budget_seconds, started=install_started)
            verdict_s = _row_verdict(proc.returncode, special=special)
            if verdict_s not in ("ok", "lock-solved"):
                any_red = True
            rows.append(
                {
                    "kind": "lane",
                    "name": lane.task,
                    "environment": lane.environment,
                    "platform": run_platform,
                    "verdict": verdict_s,
                    "exit": proc.returncode,
                    "seconds": round(seconds, 3),
                    "argv": argv,
                    "output_tail": _output_tail(proc) if proc.returncode != 0 else None,
                }
            )

    if run_full and (lane_filter is None or lane_filter == "sbom-laptop-gate"):
        argv = ["pixi", "run", "--frozen", "-e", "pyforge-foundry-full", "sbom-laptop-gate"]
        proc, seconds, special = _run_timed(deps, argv, wt, budget_seconds=budget_seconds, started=install_started)
        verdict_s = _row_verdict(proc.returncode, special=special)
        if verdict_s != "ok":
            any_red = True
        rows.append(
            {
                "kind": "lane",
                "name": "sbom-laptop-gate",
                "environment": "pyforge-foundry-full",
                "platform": run_platform,
                "verdict": verdict_s,
                "exit": proc.returncode,
                "seconds": round(seconds, 3),
                "argv": argv,
                "output_tail": _output_tail(proc) if proc.returncode != 0 else None,
            }
        )

    if run_full and (lane_filter is None or lane_filter == "verify-env"):
        verify_env = _environment_holding_task(pixi_data, "verify-env", root=deps.root)
        if verify_env is not None:
            argv = ["pixi", "run", "--frozen", "-e", verify_env, "verify-env"]
            proc, seconds, special = _run_timed(deps, argv, wt, budget_seconds=budget_seconds, started=install_started)
            verdict_s = _row_verdict(proc.returncode, special=special)
            if verdict_s != "ok":
                any_red = True
            rows.append(
                {
                    "kind": "lane",
                    "name": "verify-env",
                    "environment": verify_env,
                    "platform": run_platform,
                    "verdict": verdict_s,
                    "exit": proc.returncode,
                    "seconds": round(seconds, 3),
                    "argv": argv,
                    "output_tail": _output_tail(proc) if proc.returncode != 0 else None,
                }
            )

    if run_full and (lane_filter is None or lane_filter == "pin-fan-out"):
        argv = [sys.executable, "scripts/pin_policy_check.py", "--fan-out", "--json"]
        proc, seconds, special = _run_timed(deps, argv, wt, budget_seconds=budget_seconds, started=install_started)
        verdict_s = _row_verdict(proc.returncode, special=special)
        if verdict_s != "ok":
            any_red = True
        rows.append(
            {
                "kind": "lane",
                "name": "pin-fan-out",
                "environment": "pyforge-guild",
                "platform": run_platform,
                "verdict": verdict_s,
                "exit": proc.returncode,
                "seconds": round(seconds, 3),
                "argv": argv,
                "output_tail": _output_tail(proc) if proc.returncode != 0 else None,
            }
        )

    if run_full and lane_filter is None:
        for name, command, plat in MANUAL_ROWS:
            rows.append(
                {
                    "kind": "lane",
                    "name": name,
                    "platform": plat,
                    "verdict": "manual",
                    "command": command,
                    "exit": None,
                    "seconds": 0.0,
                }
            )

    realize = RealizeDeps(
        root=wt,
        runner=deps.runner,
        flag_on=deps.flag_on,
        enforce_require=False,
        platform=deps.platform,
    )
    register_path = deps.root / "docs/governance/realization-register.yaml"
    register: dict[str, Any] = {}
    if register_path.is_file():
        register = yaml.safe_load(register_path.read_text(encoding="utf-8")) or {}
    by_pkg = {str(r["package"]): r for r in (register.get("rows") or []) if isinstance(r, dict) and r.get("package")}
    tests_seen: set[str] = set()
    if not run_full and not probe_filter:
        by_pkg = {}
    for pkg, row in sorted(by_pkg.items()):
        if probe_filter and pkg != probe_filter:
            continue
        state = run_probe(realize, row, package=pkg)
        if state in ("stale", "missing"):
            any_red = True
        rows.append(
            {
                "kind": "probe",
                "name": pkg,
                "platform": run_platform,
                "verdict": state,
                "exit": 0 if state == "live" else 1,
                "seconds": 0.0,
            }
        )
        tests = row.get("test") or []
        if isinstance(tests, str):
            tests = [tests]
        for test_name in tests:
            t = str(test_name)
            if t in tests_seen:
                continue
            tests_seen.add(t)
            if lane_filter and t != lane_filter:
                continue
            argv = ["pixi", "run", "--frozen", "-e", str(row.get("env") or "pyforge-guild"), *shlex.split(t)]
            proc, seconds, special = _run_timed(deps, argv, wt, budget_seconds=budget_seconds, started=install_started)
            verdict_s = _row_verdict(proc.returncode, special=special)
            if verdict_s != "ok":
                any_red = True
            rows.append(
                {
                    "kind": "register-test",
                    "name": t,
                    "package": pkg,
                    "platform": run_platform,
                    "verdict": verdict_s,
                    "exit": proc.returncode,
                    "seconds": round(seconds, 3),
                    "argv": argv,
                    "output_tail": _output_tail(proc) if proc.returncode != 0 else None,
                }
            )

    platform_block = _platform_status(
        run_platform=run_platform,
        lock_check_ok=lock_check_ok,
        lock_sha=lock_sha,
    )
    summary = "estate verify: " + ("FAIL" if any_red else "ok")
    if keep:
        summary += f"; worktree kept at {wt.relative_to(deps.root)}"
    return _finish_verify(
        deps,
        rows=rows,
        any_red=any_red,
        run_platform=run_platform,
        lock_check_ok=lock_check_ok,
        keep=keep,
        wt=wt,
        summary=summary,
        platform_block=platform_block,
        lock_sha=lock_sha,
    )


def _finish_verify(
    deps: VerifyDeps,
    *,
    rows: list[dict[str, Any]],
    any_red: bool,
    run_platform: str,
    lock_check_ok: bool,
    keep: bool,
    wt: Path,
    summary: str,
    platform_block: dict[str, dict[str, str]] | None = None,
    lock_sha: str = "",
) -> DutyResult:
    if not keep:
        _remove_worktree(deps, wt)
    verify_block = {
        "platforms": platform_block
        or _platform_status(run_platform=run_platform, lock_check_ok=lock_check_ok, lock_sha=lock_sha),
        "rows": rows,
    }
    from .estate import _list_journals

    journals = _list_journals(deps.root)
    if journals:
        # The verify block belongs to the refresh it verifies: the latest journal.
        journal_path = journals[-1]
        try:
            journal = json.loads(journal_path.read_text(encoding="utf-8"))
        except OSError, json.JSONDecodeError:
            journal = None
        if isinstance(journal, dict):
            journal["verify"] = verify_block
            journal_path.write_text(json.dumps(journal, indent=2) + "\n", encoding="utf-8")
            return DutyResult(
                ok=not any_red,
                summary=f"{summary}\njournal → {journal_path.relative_to(deps.root)}",
                details={"journal_path": str(journal_path), "verify": verify_block},
            )
    journal_path = _next_journal_path(deps.root, today=date.today())
    journal = {
        "base_sha": deps.head_sha(),
        "result_sha": deps.head_sha(),
        "platform": run_platform,
        "command": "estate verify",
        "moves": [],
        "losses_restored": [],
        "fan_out": {"ok": True, "findings": []},
        "realize_due": [],
        "transitive": False,
        "bmad": {"pinned": "unknown", "installed": "unknown", "latest": "unknown", "applied": False},
        "steps": [],
        "realize": {},
        "reconcile": {},
        "verify": verify_block,
    }
    journal_path.write_text(json.dumps(journal, indent=2) + "\n", encoding="utf-8")
    return DutyResult(
        ok=not any_red,
        summary=f"{summary}\njournal → {journal_path.relative_to(deps.root)}",
        details={"journal_path": str(journal_path), "verify": verify_block},
    )


def production_verify_deps(root: Path) -> VerifyDeps:
    base = _production_deps(root)
    return VerifyDeps(
        root=root,
        runner=base.runner,
        head_sha=base.head_sha,
        platform=base.platform,
        flag_on=base.flag_on,
        enforce_require=base.enforce_require,
    )


def format_status_platforms(journal: dict[str, Any]) -> list[str]:
    verify = journal.get("verify") or {}
    platforms = verify.get("platforms") or {}
    lines: list[str] = []
    for plat in sorted(platforms):
        entry = platforms[plat]
        if not isinstance(entry, dict):
            continue
        lines.append(f"{plat}: lock_sha={entry.get('lock_sha')} verdict={entry.get('verdict')}")
    return lines


def load_latest_verify_platforms(root: Path) -> dict[str, dict[str, str]]:
    from .estate import _list_journals

    journals = _list_journals(root)
    for path in reversed(journals):
        doc = _load_journal(path)
        verify = doc.get("verify") or {}
        plats = verify.get("platforms")
        if isinstance(plats, dict) and plats:
            out: dict[str, dict[str, str]] = {}
            for key, val in plats.items():
                if isinstance(val, dict):
                    out[str(key)] = {str(k): str(v) for k, v in val.items()}
            if out:
                return out
    return {}
