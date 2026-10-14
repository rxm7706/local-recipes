"""``steward estate`` — policy-driven pin refresh conductor (Story 100.2 / CAP-167).

Five verbs in v1: ``plan``, ``refresh``, ``reconcile``, ``verify``, ``status``. Every mutating step is a
subprocess (AD-1); this module never edits ``pixi.toml`` (AD-5). Returns
``DutyResult`` only (AD-8).
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import sys
import time
import tomllib
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable, Protocol

import yaml

from .bootstrap import repo_root
from .interfaces import DutyResult

ESTATE_FLAG_KEY = "pyforge.steward.estate_refresh"
EXIT_ESTATE_REFUSAL = 3
JOURNAL_DIR = Path(".steward/estate-refresh")
SCHEMA_RESOURCE = Path(__file__).resolve().parent / "data" / "estate-journal-schema.json"
_DUE_DAYS = 30
_BMAD_CORE = "bmad-method"


class _Completed(Protocol):
    args: list[str] | str
    returncode: int
    stdout: str
    stderr: str


SubprocessRunner = Callable[[list[str], Path], _Completed]


@dataclass
class EstateDeps:
    """Injectable seams for unit tests (AC6: no live pixi/git/network)."""

    root: Path
    runner: SubprocessRunner
    branch: Callable[[], str | None] = field(default=lambda: None)
    dirty: Callable[[], bool] = field(default=lambda: False)
    head_sha: Callable[[], str] = field(default=lambda: "deadbeef")
    platform: Callable[[], str] = field(default=lambda: "linux-64")
    flag_on: Callable[[], bool] = field(default=lambda: True)
    bmad_latest: Callable[[str], str | None] = field(default=lambda _pkg: None)
    now: Callable[[], datetime] = field(default=lambda: datetime.now(timezone.utc))
    enforce_require: bool = True


def _default_runner(argv: list[str], cwd: Path) -> _Completed:
    import subprocess

    return subprocess.run(  # noqa: S603
        argv,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )


def _git_branch(root: Path) -> str | None:
    import subprocess

    out = subprocess.run(  # noqa: S603
        ["git", "-C", str(root), "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode != 0:
        return None
    return out.stdout.strip()


def _git_head(root: Path) -> str:
    import subprocess

    out = subprocess.run(  # noqa: S603
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode != 0:
        return "unknown"
    return out.stdout.strip()


def _worktree_dirty(root: Path) -> bool:
    import subprocess

    out = subprocess.run(  # noqa: S603
        [
            "git",
            "-C",
            str(root),
            "-c",
            "status.showUntrackedFiles=normal",
            "status",
            "--porcelain",
            "--ignore-submodules=none",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode != 0:
        return True
    return bool((out.stdout or "").strip())


def _flag_enabled() -> bool:
    from pyforge.core.flags import read_boolean

    return read_boolean(ESTATE_FLAG_KEY, default=False)


def _production_deps(root: Path) -> EstateDeps:
    return EstateDeps(
        root=root,
        runner=_default_runner,
        branch=lambda: _git_branch(root),
        dirty=lambda: _worktree_dirty(root),
        head_sha=lambda: _git_head(root),
        platform=lambda: "linux-64",
        flag_on=_flag_enabled,
    )


def _refusal(summary: str) -> DutyResult:
    return DutyResult(
        ok=False,
        summary=summary,
        details={"exit_code": EXIT_ESTATE_REFUSAL},
    )


def _ensure_flag(deps: EstateDeps) -> DutyResult | None:
    """Gate every verb on ``pyforge.steward.estate_refresh`` (``read_boolean`` / ``require`` parity)."""
    from pyforge.core.flags import require

    if not deps.flag_on():
        return _refusal(f"estate: refused — flag {ESTATE_FLAG_KEY} is off")
    if deps.enforce_require:
        require(ESTATE_FLAG_KEY)
    return None


def _policy_path(root: Path) -> Path:
    return root / "docs" / "governance" / "pin-policy.yaml"


def _load_policy(root: Path) -> dict[str, Any]:
    path = _policy_path(root)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected mapping")
    return data


def _row_covers_feature(row_features: object, feature: str) -> bool:
    if row_features == "*":
        return True
    if isinstance(row_features, list):
        return feature in row_features or any(feature == f or feature.startswith(f + ".") for f in row_features)
    return False


def _held_by(policy: dict[str, Any], package: str, feature: str) -> str | None:
    holds = policy.get("holds") or []
    rows = [
        h
        for h in holds
        if isinstance(h, dict) and h.get("package") == package and _row_covers_feature(h.get("features"), feature)
    ]
    if not rows:
        return None
    row = rows[0]
    hold = row.get("hold", "")
    authority = row.get("authority", "")
    return f"{hold} ({authority})" if authority else str(hold)


def _render_upgrade_command(deps: EstateDeps) -> tuple[str, list[str]]:
    argv = [sys.executable, "scripts/pin_policy_check.py", "--render-command"]
    proc = deps.runner(argv, deps.root)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "render-command failed").strip())
    command = (proc.stdout or "").strip()
    return command, shlex.split(command)


_ARTIFACT_SUFFIXES = (".conda", ".tar.bz2")


def _artifact_version(side: object) -> str:
    """The version field of a conda artifact URL: ``<name>-<version>-<build><suffix>``.

    Names carry dashes (``gcc_linux-64``, ``clang-18``), so split from the right.
    """
    if not isinstance(side, dict):
        return ""
    if side.get("version"):
        return str(side["version"])
    base = str(side.get("conda") or "").rsplit("/", 1)[-1]
    for suffix in _ARTIFACT_SUFFIXES:
        if base.endswith(suffix):
            parts = base[: -len(suffix)].rsplit("-", 2)
            return parts[1] if len(parts) == 3 else ""  # noqa: PLR2004
    return ""


def _parse_environment_moves(environments: dict[str, Any]) -> list[dict[str, str]]:
    """pixi 0.8x shape: ``{"environment": {env: {platform: [{name, before, after, explicit}]}}}``.

    One row per (package, environment, from, to) for the packages the manifest declares
    (``explicit``); the platforms of one environment collapse into one row.
    """
    seen: set[tuple[str, str, str, str]] = set()
    moves: list[dict[str, str]] = []
    for env in sorted(environments):
        platforms = environments[env]
        if not isinstance(platforms, dict):
            continue
        for platform in sorted(platforms):
            items = platforms[platform]
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict) or not item.get("explicit"):
                    continue
                row = (
                    str(item.get("name") or ""),
                    env,
                    _artifact_version(item.get("before")),
                    _artifact_version(item.get("after")),
                )
                if not row[0] or row in seen:
                    continue
                seen.add(row)
                moves.append({"package": row[0], "feature": row[1], "from": row[2], "to": row[3]})
    return moves


def _parse_pixi_moves(payload: object) -> list[dict[str, str]]:
    """Normalize pixi upgrade --json (or --dry-run --json) into move rows."""
    moves: list[dict[str, str]] = []
    if isinstance(payload, dict) and isinstance(payload.get("environment"), dict):
        return _parse_environment_moves(payload["environment"])
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        items = payload.get("packages") or payload.get("updates") or payload.get("moves") or []
    else:
        return moves
    if not isinstance(items, list):
        return moves
    for item in items:
        if not isinstance(item, dict):
            continue
        package = str(item.get("package") or item.get("name") or "")
        feature = str(item.get("feature") or item.get("environment") or item.get("env") or "*")
        from_v = str(item.get("from") or item.get("old") or item.get("before") or "")
        to_v = str(item.get("to") or item.get("new") or item.get("after") or "")
        if package:
            moves.append({"package": package, "feature": feature, "from": from_v, "to": to_v})
    return moves


def _run_pixi_upgrade_json(
    deps: EstateDeps, command_argv: list[str], *, dry_run: bool
) -> tuple[list[dict], _Completed]:
    argv = list(command_argv)
    if dry_run and "--dry-run" not in argv and "upgrade" in argv:
        idx = argv.index("upgrade")
        argv = [*argv[: idx + 1], "--dry-run", *argv[idx + 1 :]]
    if "--json" not in argv:
        argv.append("--json")
    proc = deps.runner(argv, deps.root)
    moves: list[dict] = []
    text = (proc.stdout or "").strip()
    if text:
        try:
            moves = _parse_pixi_moves(json.loads(text))
        except json.JSONDecodeError:
            pass
    return moves, proc


def _journal_dir(root: Path) -> Path:
    return root / JOURNAL_DIR


def _list_journals(root: Path) -> list[Path]:
    directory = _journal_dir(root)
    if not directory.is_dir():
        return []
    return sorted(directory.glob("*.json"), key=_journal_order)


def _journal_order(path: Path) -> tuple[str, int]:
    """``2026-10-14.json`` is that day's first journal, ``2026-10-14-2.json`` its second.

    A plain name sort puts ``-2`` before the bare date (``-`` sorts before ``.``).
    """
    stem = path.stem
    day, seq = stem[:10], stem[11:]
    return day, int(seq) if seq.isdigit() else 1


def _days_since_last_journal(root: Path, *, now: datetime) -> int | None:
    journals = _list_journals(root)
    if not journals:
        return None
    last = journals[-1]
    stem = last.stem  # YYYY-MM-DD or YYYY-MM-DD-2
    day_part = stem.split("-")[:3]
    if len(day_part) < 3:  # noqa: PLR2004
        return None
    try:
        journal_day = date(int(day_part[0]), int(day_part[1]), int(day_part[2]))
    except ValueError:
        return None
    today = now.date()
    return (today - journal_day).days


def _is_due(root: Path, *, now: datetime) -> bool:
    days = _days_since_last_journal(root, now=now)
    return days is None or days > _DUE_DAYS


def _read_manifest_version(manifest_path: Path) -> str | None:
    if not manifest_path.is_file():
        return None
    data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return None
    inst = data.get("installation")
    if not isinstance(inst, dict):
        return None
    ver = inst.get("version")
    return str(ver) if ver is not None else None


def _bmad_floor_from_pixi(pixi_path: Path, package: str) -> str | None:
    if not pixi_path.is_file():
        return None
    data = tomllib.loads(pixi_path.read_text(encoding="utf-8"))
    pattern = re.compile(r">=\s*(\d+\.\d+\.\d+)")
    for _table, deps in _walk_dependency_tables(data):
        if not isinstance(deps, dict):
            continue
        spec = deps.get(package)
        if spec is None:
            continue
        spec_str = spec if isinstance(spec, str) else str(spec)
        m = pattern.search(spec_str)
        if m:
            return m.group(1)
    return None


def _walk_dependency_tables(node: object, path: list[str] | None = None):
    path = path or []
    if not isinstance(node, dict):
        return
    for key, value in node.items():
        here = [*path, str(key)]
        if str(key).endswith("dependencies") and isinstance(value, dict):
            yield ".".join(path), value
        elif isinstance(value, dict):
            yield from _walk_dependency_tables(value, here)


def _bmad_package_names(pixi_path: Path) -> list[str]:
    if not pixi_path.is_file():
        return [_BMAD_CORE]
    data = tomllib.loads(pixi_path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for _table, deps in _walk_dependency_tables(data):
        if not isinstance(deps, dict):
            continue
        for name in deps:
            if isinstance(name, str) and (name == _BMAD_CORE or name.startswith("bmad-")):
                names.add(name)
    names.add(_BMAD_CORE)
    return sorted(names)


def _bmad_table(deps: EstateDeps) -> list[dict[str, str]]:
    root = deps.root
    pixi_path = root / "pixi.toml"
    manifest_path = root / "_bmad" / "_config" / "manifest.yaml"
    installed = _read_manifest_version(manifest_path) or "unknown"
    rows: list[dict[str, str]] = []
    for package in _bmad_package_names(pixi_path):
        pinned = _bmad_floor_from_pixi(pixi_path, package) or "unknown"
        latest_val = deps.bmad_latest(package)
        latest = latest_val if latest_val is not None else "unknown"
        rows.append(
            {
                "package": package,
                "pinned": pinned,
                "installed": installed if package == _BMAD_CORE else pinned,
                "latest": latest,
            }
        )
    return rows


def _format_plan_text(moves: list[dict], bmad: list[dict], days: int | None) -> str:
    lines: list[str] = []
    for move in moves:
        held = move.get("held-by") or ""
        lines.append(f"{move['package']}\t{move['feature']}\t{move['from']}\t{move['to']}\t{held}")
    lines.append("--- bmad ---")
    for row in bmad:
        lines.append(f"{row['package']}\tpinned={row['pinned']}\tinstalled={row['installed']}\tlatest={row['latest']}")
    if days is None:
        lines.append("days since last journal: (none)")
    else:
        lines.append(f"days since last journal: {days}")
    return "\n".join(lines)


def run_plan(deps: EstateDeps, *, json_out: bool, due_only: bool) -> DutyResult:
    refused = _ensure_flag(deps)
    if refused is not None:
        return refused
    policy = _load_policy(deps.root)
    command, command_argv = _render_upgrade_command(deps)
    raw_moves, _proc = _run_pixi_upgrade_json(deps, command_argv, dry_run=True)
    moves = []
    for move in raw_moves:
        held = _held_by(policy, move["package"], move["feature"])
        moves.append({**move, "held-by": held})
    bmad = _bmad_table(deps)
    days = _days_since_last_journal(deps.root, now=deps.now())
    due = _is_due(deps.root, now=deps.now())
    if due_only:
        if due:
            return DutyResult(ok=False, summary="estate plan --due: refresh is overdue", details={"due": True})
        return DutyResult(ok=True, summary="estate plan --due: within cadence", details={"due": False})
    payload = {
        "kind": "plan",
        "moves": moves,
        "bmad": bmad,
        "days_since_last_journal": days,
        "due": due,
        "command": command,
    }
    if json_out:
        return DutyResult(ok=True, summary=json.dumps(payload, indent=2), details={"plan": payload})
    return DutyResult(ok=True, summary=_format_plan_text(moves, bmad, days), details={"plan": payload})


def _record_step(steps: list[dict], argv: list[str], proc: _Completed, started: float) -> None:
    steps.append(
        {
            "argv": list(argv),
            "exit": int(proc.returncode),
            "seconds": round(time.monotonic() - started, 3),
        }
    )


def _next_journal_path(root: Path, *, today: date) -> Path:
    directory = _journal_dir(root)
    directory.mkdir(parents=True, exist_ok=True)
    base = directory / f"{today.isoformat()}.json"
    if not base.exists():
        return base
    suffix = 2
    while True:
        candidate = directory / f"{today.isoformat()}-{suffix}.json"
        if not candidate.exists():
            return candidate
        suffix += 1


_MAX_CONVERGE_ROUNDS = 4


class _RefreshRefused(Exception):
    """A refresh step failed; ``run_refresh`` resets the pixi files and journals the refusal."""


def _lowered_floors(deps: EstateDeps, base_sha: str, steps: list[dict]) -> set[str]:
    argv = [sys.executable, "scripts/pin_policy_check.py", "--diff", base_sha, "--json"]
    started = time.monotonic()
    proc = deps.runner(argv, deps.root)
    _record_step(steps, argv, proc, started)
    if proc.returncode not in (0, 1):
        raise _RefreshRefused(f"pin policy diff could not run (exit {proc.returncode})")
    try:
        findings = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise _RefreshRefused("pin policy diff printed no JSON") from exc
    if not isinstance(findings, list):
        raise _RefreshRefused("pin policy diff printed no finding list")
    return {
        str(f["package"])
        for f in findings
        if isinstance(f, dict) and f.get("kind") == "lowered-floor" and f.get("package")
    }


def _reset_pixi_files(deps: EstateDeps, base_sha: str, steps: list[dict]) -> bool:
    argv = ["git", "checkout", base_sha, "--", "pixi.toml", "pixi.lock"]
    started = time.monotonic()
    proc = deps.runner(argv, deps.root)
    _record_step(steps, argv, proc, started)
    return proc.returncode == 0


def _converge_upgrade(
    deps: EstateDeps, command_argv: list[str], base_sha: str, steps: list[dict]
) -> tuple[list[dict], dict[str, Any]]:
    """Run ``pixi upgrade``; when it lowers a declared floor, exclude that package and rerun.

    ``latest-up`` lowers a floor only when it raised another package to a version the old
    floor cannot satisfy. ``pin_policy_restore`` would put the floor back and leave
    ``pixi lock`` unsolvable (Story 100.7: cron-descriptor against django-celery-beat, openai
    against litellm). Excluding the package that would be lowered keeps its declaration in the
    solve, so the upgrade picks a version of the other package that fits it. Each retry starts
    from the base ``pixi.toml`` and ``pixi.lock``. A failed upgrade or reset refuses.
    """
    excluded: list[str] = []
    moves: list[dict] = []
    for round_no in range(1, _MAX_CONVERGE_ROUNDS + 1):
        argv = [*command_argv, *(a for pkg in excluded for a in ("--exclude", pkg))]
        started = time.monotonic()
        moves, proc = _run_pixi_upgrade_json(deps, argv, dry_run=False)
        _record_step(steps, [*argv, "--json"], proc, started)
        if proc.returncode != 0:
            raise _RefreshRefused(f"pixi upgrade failed in round {round_no} (exit {proc.returncode})")
        new = sorted(_lowered_floors(deps, base_sha, steps) - set(excluded))
        if not new:
            return moves, {"rounds": round_no, "excluded": excluded, "converged": True, "unresolved": []}
        if round_no == _MAX_CONVERGE_ROUNDS:
            return moves, {"rounds": round_no, "excluded": excluded, "converged": False, "unresolved": new}
        if not _reset_pixi_files(deps, base_sha, steps):
            raise _RefreshRefused("could not reset pixi.toml and pixi.lock to the base commit")
        excluded.extend(new)
    raise AssertionError("unreachable")  # pragma: no cover


def _refresh_journal(
    deps: EstateDeps,
    base_sha: str,
    command: str,
    moves: list[dict],
    converge: dict[str, Any],
    losses: list[Any],
    transitive: bool,
    steps: list[dict],
    *,
    realize_due: list[str],
) -> dict[str, Any]:
    manifest_path = deps.root / "_bmad" / "_config" / "manifest.yaml"
    pixi_path = deps.root / "pixi.toml"
    return {
        "base_sha": base_sha,
        "result_sha": "",
        "platform": deps.platform(),
        "command": command,
        "moves": moves,
        "converge": converge,
        "losses_restored": losses,
        "fan_out": {"ok": False, "findings": []},
        "realize_due": realize_due,
        "transitive": transitive,
        "bmad": {
            "pinned": _bmad_floor_from_pixi(pixi_path, _BMAD_CORE) or "unknown",
            "installed": _read_manifest_version(manifest_path) or "unknown",
            "latest": deps.bmad_latest(_BMAD_CORE) or "unknown",
            "applied": False,
        },
        "steps": steps,
        "realize": {},
        "reconcile": {},
        "verify": {},
    }


def run_refresh(deps: EstateDeps, *, transitive: bool) -> DutyResult:
    refused = _ensure_flag(deps)
    if refused is not None:
        return refused
    if deps.dirty():
        return _refusal("estate refresh: refused — working tree is dirty")
    branch = deps.branch()
    if branch == "main":
        return _refusal("estate refresh: refused — branch is main")
    steps: list[dict] = []
    base_sha = deps.head_sha()
    command, command_argv = _render_upgrade_command(deps)
    moves: list[dict] = []
    converge: dict[str, Any] = {"rounds": 0, "excluded": [], "converged": False, "unresolved": []}
    losses: list[Any] = []
    try:
        moves, converge = _converge_upgrade(deps, command_argv, base_sha, steps)
        if converge["excluded"]:
            command = " ".join([command, *(f"--exclude {pkg}" for pkg in converge["excluded"])])

        if transitive:
            update_argv = ["pixi", "update"]
            started = time.monotonic()
            update_proc = deps.runner(update_argv, deps.root)
            _record_step(steps, update_argv, update_proc, started)
            if update_proc.returncode != 0:
                raise _RefreshRefused(f"pixi update failed (exit {update_proc.returncode})")

        diff_argv = [sys.executable, "scripts/pin_policy_check.py", "--diff", base_sha, "--json"]
        started = time.monotonic()
        diff_proc = deps.runner(diff_argv, deps.root)
        _record_step(steps, diff_argv, diff_proc, started)
        if diff_proc.returncode not in (0, 1):
            raise _RefreshRefused(f"pin policy diff could not run (exit {diff_proc.returncode})")
        if diff_proc.returncode != 0 and (diff_proc.stdout or "").strip():
            try:
                losses = json.loads(diff_proc.stdout)
            except json.JSONDecodeError:
                losses = [{"raw": diff_proc.stdout.strip()}]
            restore_argv = [sys.executable, "scripts/pin_policy_restore.py", "--from", base_sha]
            started = time.monotonic()
            restore_proc = deps.runner(restore_argv, deps.root)
            _record_step(steps, restore_argv, restore_proc, started)
            if restore_proc.returncode != 0:
                raise _RefreshRefused(f"pin policy restore refused (exit {restore_proc.returncode})")

        lock_argv = ["pixi", "lock"]
        started = time.monotonic()
        lock_proc = deps.runner(lock_argv, deps.root)
        _record_step(steps, lock_argv, lock_proc, started)
        if lock_proc.returncode != 0:
            raise _RefreshRefused(f"pixi lock failed (exit {lock_proc.returncode})")
    except _RefreshRefused as refusal:
        reset_ok = _reset_pixi_files(deps, base_sha, steps)
        journal = _refresh_journal(deps, base_sha, command, moves, converge, losses, transitive, steps, realize_due=[])
        journal["refused"] = str(refusal)
        journal_path = _next_journal_path(deps.root, today=deps.now().date())
        journal_path.write_text(json.dumps(journal, indent=2) + "\n", encoding="utf-8")
        tail = "" if reset_ok else "; pixi.toml/pixi.lock could NOT be reset to the base commit"
        return DutyResult(
            ok=False,
            summary=f"estate refresh: {refusal}{tail} (journal → {journal_path.relative_to(deps.root)})",
            details={"exit_code": EXIT_ESTATE_REFUSAL, "steps": steps, "journal_path": str(journal_path)},
        )

    fan_argv = [sys.executable, "scripts/pin_policy_check.py", "--fan-out", "--json"]
    started = time.monotonic()
    fan_proc = deps.runner(fan_argv, deps.root)
    _record_step(steps, fan_argv, fan_proc, started)
    fan_findings: list[Any] = []
    fan_ok = fan_proc.returncode == 0
    if (fan_proc.stdout or "").strip():
        try:
            parsed = json.loads(fan_proc.stdout)
            fan_findings = parsed if isinstance(parsed, list) else [parsed]
        except json.JSONDecodeError:
            fan_findings = [{"raw": fan_proc.stdout.strip()}]

    pixi_moved = any(m.get("package") == "pixi" for m in moves)
    if pixi_moved:
        bump_argv = [sys.executable, "scripts/bump_pixi_version.py"]
        started = time.monotonic()
        bump_proc = deps.runner(bump_argv, deps.root)
        _record_step(steps, bump_argv, bump_proc, started)

    from .estate_realize import compute_realize_due_for_refresh

    realize_due = compute_realize_due_for_refresh(deps.root, moves)
    journal = _refresh_journal(
        deps, base_sha, command, moves, converge, losses, transitive, steps, realize_due=realize_due
    )
    journal["fan_out"] = {"ok": fan_ok, "findings": fan_findings}
    today = deps.now().date()
    journal_path = _next_journal_path(deps.root, today=today)
    journal_path.write_text(json.dumps(journal, indent=2) + "\n", encoding="utf-8")

    summary_lines = [f"estate refresh: journal → {journal_path.relative_to(deps.root)}"]
    if realize_due:
        summary_lines.append("realize-due: " + ", ".join(realize_due))
    if not fan_ok:
        summary_lines.append("fan-out: FAIL")
        return DutyResult(
            ok=False,
            summary="\n".join(summary_lines),
            details={"journal_path": str(journal_path), "steps": steps},
        )
    return DutyResult(
        ok=True,
        summary="\n".join(summary_lines),
        details={"journal_path": str(journal_path), "steps": steps},
    )


def _load_journal(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_status(deps: EstateDeps, *, json_out: bool, show_all: bool) -> DutyResult:
    refused = _ensure_flag(deps)
    if refused is not None:
        return refused
    journals = _list_journals(deps.root)
    if not journals:
        return DutyResult(ok=True, summary="estate status: no journals yet")
    selected = journals if show_all else [journals[-1]]
    due = _is_due(deps.root, now=deps.now())
    lines: list[str] = []
    for path in selected:
        doc = _load_journal(path)
        lines.append(f"=== {path.name} ===")
        lines.append(f"base_sha={doc.get('base_sha')} moves={len(doc.get('moves') or [])}")
        lines.append(f"fan_out.ok={doc.get('fan_out', {}).get('ok')}")
        from .estate_verify import format_status_platforms

        plat_lines = format_status_platforms(doc)
        if plat_lines:
            lines.append("--- platforms (verify) ---")
            lines.extend(plat_lines)
    lines.append(f"due={'yes' if due else 'no'}")
    if json_out:
        payload = {"journals": [_load_journal(p) for p in selected], "due": due}
        return DutyResult(ok=True, summary=json.dumps(payload, indent=2), details=payload)
    return DutyResult(ok=True, summary="\n".join(lines), details={"due": due})


class EstateDuty:
    name = "estate"

    def run(self, ns: argparse.Namespace) -> DutyResult:
        root = repo_root()
        deps = getattr(ns, "_estate_deps", None) or _production_deps(root)
        verb = getattr(ns, "estate_verb", None)
        if verb == "plan":
            return run_plan(deps, json_out=bool(getattr(ns, "json", False)), due_only=bool(getattr(ns, "due", False)))
        if verb == "refresh":
            return run_refresh(deps, transitive=bool(getattr(ns, "transitive", False)))
        if verb == "reconcile":
            from .estate_reconcile import ReconcileDeps, production_reconcile_seams, run_reconcile

            rdeps = getattr(ns, "_reconcile_deps", None)
            if rdeps is None:
                seams = production_reconcile_seams(deps.runner)
                rdeps = ReconcileDeps(
                    root=deps.root,
                    runner=deps.runner,
                    branch=deps.branch,
                    dirty=deps.dirty,
                    head_sha=deps.head_sha,
                    platform=deps.platform,
                    flag_on=deps.flag_on,
                    bmad_latest=deps.bmad_latest,
                    now=deps.now,
                    enforce_require=deps.enforce_require,
                    memlog_append=seams.memlog_append,
                    git_add=seams.git_add,
                    stamp_spec=seams.stamp_spec,
                )
            journal_path = getattr(ns, "journal_path", None)
            return run_reconcile(rdeps, journal_path=journal_path)
        if verb == "status":
            return run_status(
                deps,
                json_out=bool(getattr(ns, "json", False)),
                show_all=bool(getattr(ns, "all", False)),
            )
        if verb == "verify":
            from .estate_verify import production_verify_deps, run_verify

            vdeps = getattr(ns, "_verify_deps", None)
            if vdeps is None:
                vdeps = production_verify_deps(root)
            return run_verify(
                vdeps,
                env_filter=getattr(ns, "env", None),
                lane_filter=getattr(ns, "lane", None),
                probe_filter=getattr(ns, "probe", None),
                all_envs=bool(getattr(ns, "all", False)),
                keep=bool(getattr(ns, "keep", False)),
                ignore_ci_pauses=bool(getattr(ns, "ignore_ci_pauses", False)),
                budget_minutes=getattr(ns, "budget_minutes", None),
            )
        if verb == "realize":
            from .estate_realize import production_realize_deps, run_realize

            rdeps = getattr(ns, "_realize_deps", None)
            if rdeps is None:
                rdeps = production_realize_deps(root)
            journal_arg = getattr(ns, "journal", None)
            return run_realize(
                rdeps,
                plan=bool(getattr(ns, "plan", False)),
                yes=bool(getattr(ns, "yes", False)),
                all_rows=bool(getattr(ns, "all", False)),
                journal_path=Path(journal_arg) if journal_arg else None,
            )
        return DutyResult(ok=False, summary="estate: need plan, refresh, reconcile, verify, realize, or status")
