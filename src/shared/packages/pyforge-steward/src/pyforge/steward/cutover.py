"""Cutover plan and flip (spec-python-foundry-cutover fnd:CAP-8, fnd:CAP-9; Stories 44.12 and 121.2).

``steward cutover plan`` generates and validates the capability ledger, ``docs/foundry/capability-ledger.yaml``:
``--regenerate`` and ``--append`` are the generator's two write modes (``cutover_ledger``, Story 121.1) and ``--check``,
the default, is its validator (``cutover_ledger_check``, Story 121.6), which writes nothing and fails on a broken rule.
The two write modes sit behind the kill switch ``pyforge.steward.cutover_ledger_write`` (default on); ``--check`` is
never gated. ``steward cutover flip`` sets ``pyforge.cutover_root``, the root of record and writer lock: it is refused
while a Marshal loop runs and stamps the Realization log. Copying trees into foundry is retired (operator ruling 2,
2026-11-10): the ledger row decides each capability's mode, never a file list.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from datetime import date
from pathlib import Path

from pyforge.core import flags as core_flags
from pyforge.core.atomic_write import atomic_write_text
from pyforge.core.cutover_root import (
    CUTOVER_FLAG,
    CUTOVER_VARIANTS,
    DEFAULT_CUTOVER_ROOT,
    CutoverRootError,
    read_cutover_root,
    resolve_flags_path,
)

from .cutover_ledger import DEFAULT_LEDGER, CutoverLedgerError, LedgerReport
from .cutover_ledger import append as append_ledger
from .cutover_ledger import regenerate as regenerate_ledger
from .cutover_ledger_check import CheckReport, Issue
from .cutover_ledger_check import check as check_ledger
from .interfaces import DutyResult

_CUTOVER_VERBS: tuple[str, ...] = ("plan", "flip")
REALIZATION_LOG = Path("docs/dreams/pyforge-unifying-strategy.md")
CUTOVER_FLAG_STORY = "44-12-cutover-flag-and-replay-harness"

# fnd:CAP-9: the kill switch over the ledger's two write modes, read with `read_boolean` before either writes.
LEDGER_WRITE_FLAG = "pyforge.steward.cutover_ledger_write"
PLAN_CHECK = "check"
_PLAN_WRITERS: dict[str, Callable[[Path, Path], LedgerReport]] = {
    "regenerate": regenerate_ledger,
    "append": append_ledger,
}


def _repo_root(start: Path | None = None) -> Path:
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        if (candidate / ".git").exists():
            return candidate
    return here


def _count(n: int, noun: str) -> str:
    return f"{n} {noun}" if n == 1 else f"{n} {noun}s"


def _issue_rows(issues: tuple[Issue, ...]) -> list[dict[str, str]]:
    return [{"code": code, "id": item, "message": message} for code, item, message in issues]


def _issue_lines(kind: str, issues: tuple[Issue, ...]) -> list[str]:
    return [f"  {kind} {code} {item}: {message}" for code, item, message in issues]


def _plan_result(ok: bool, lines: list[str], payload: dict[str, object], as_json: bool) -> DutyResult:
    if as_json:
        # A failed --check still hands its JSON report to stdout, where a machine reader looks for it.
        return DutyResult(
            ok=ok,
            summary=json.dumps(payload, indent=2),
            details={**payload, "summary_stream": "stdout"},
        )
    return DutyResult(ok=ok, summary="\n".join(lines), details=payload)


def _checked(report: CheckReport, ledger: Path, as_json: bool) -> DutyResult:
    payload: dict[str, object] = {
        "mode": PLAN_CHECK,
        "ledger": str(ledger),
        "ok": report.ok,
        "findings": _issue_rows(report.findings),
        "warnings": _issue_rows(report.warnings),
    }
    head = (
        f"cutover plan --check: {ledger}: "
        f"{_count(len(report.findings), 'finding')}, {_count(len(report.warnings), 'warning')}"
    )
    lines = [head, *_issue_lines("finding", report.findings), *_issue_lines("warning", report.warnings)]
    return _plan_result(report.ok, lines, payload, as_json)


def _written(mode: str, report: LedgerReport, ledger: Path, as_json: bool) -> DutyResult:
    payload: dict[str, object] = {"mode": mode, "ledger": str(ledger), **report.as_dict()}
    state = "written" if report.changed else "unchanged"
    head = (
        f"cutover plan --{mode}: {ledger}: {state}; "
        f"{len(report.added)} added, {len(report.dropped)} dropped, {len(report.remoded)} remoded"
    )
    lines = [head, *(f"  {code} {item}" for code, item in report.events)]
    return _plan_result(True, lines, payload, as_json)


def plan(ns: argparse.Namespace, root: Path) -> DutyResult:
    """``steward cutover plan``: ``--check`` (the default) judges the ledger and writes nothing; ``--regenerate`` and
    ``--append`` write it unless the kill switch ``pyforge.steward.cutover_ledger_write`` reads off.

    ``--ledger`` names another ledger file (relative to the working directory); the default is the repository's.
    A broken rule fails the result, so the process exits 1; an OFF switch or an unknown mode asks for steward's usage
    code and writes nothing.
    """
    from .cli import EXIT_USAGE  # function-local: cli resolves this duty lazily

    mode = str(getattr(ns, "plan_mode", None) or PLAN_CHECK)
    raw = getattr(ns, "ledger", None)
    ledger = Path(raw).absolute() if raw else root / DEFAULT_LEDGER
    as_json = bool(getattr(ns, "json", False))
    if mode == PLAN_CHECK:
        return _checked(check_ledger(root, ledger), ledger, as_json)
    writer = _PLAN_WRITERS.get(mode)
    if writer is None:
        return DutyResult(
            ok=False,
            summary=f"cutover plan: unknown mode {mode!r}; pass --regenerate, --append or --check",
            details={"exit_code": EXIT_USAGE},
        )
    if not core_flags.read_boolean(LEDGER_WRITE_FLAG, default=True):
        return DutyResult(
            ok=False,
            summary=(
                f"cutover plan --{mode}: refused, the kill switch {LEDGER_WRITE_FLAG} is off; "
                "nothing was written (plan --check still runs)"
            ),
            details={"exit_code": EXIT_USAGE, "mode": mode, "ledger": str(ledger)},
        )
    return _written(mode, writer(root, ledger), ledger, as_json)


def loops_running(home: Path | None = None) -> bool:
    base = home or (Path.home() / ".bmad-loops")
    if not base.is_dir():
        return False
    for state in base.rglob("state.json"):
        try:
            data = json.loads(state.read_text(encoding="utf-8"))
        except OSError, json.JSONDecodeError:
            continue
        status = str(data.get("status") or data.get("state") or "").lower()
        if status in {"running", "in_progress", "active", "live"}:
            return True
    return False


def flip_root(
    flags_path: Path,
    target: str,
    realization: Path,
    *,
    loop_home: Path | None = None,
) -> None:
    if target not in CUTOVER_VARIANTS:
        raise CutoverRootError(f"unknown cutover_root variant {target!r}")
    if loops_running(loop_home):
        raise CutoverRootError("flip refused: a Marshal loop is running")
    payload = json.loads(flags_path.read_text(encoding="utf-8"))
    flags = payload.setdefault("flags", {})
    entry = flags.setdefault(
        CUTOVER_FLAG,
        {
            "state": "ENABLED",
            "variants": {k: k for k in CUTOVER_VARIANTS},
            "defaultVariant": DEFAULT_CUTOVER_ROOT,
            # Story 76.2: every flag carries its clock. A string flag has no ON variant, so
            # `on_everywhere` and `cleanup_by` stay empty and no clock runs.
            "metadata": {
                "owner": "steward",
                "story": CUTOVER_FLAG_STORY,
                "created": date.today().isoformat(),
                "on_everywhere": "",
                "cleanup_by": "",
            },
        },
    )
    entry["defaultVariant"] = target
    # Story 76.1: an overlay that names the flag would mask the tree's variant, so a flip sets the
    # target in every environment that names it -- one root everywhere, as before. Read and
    # composed (every entry of every environment validated) before either file is written.
    overlays_path = core_flags.overlays_path_for(flags_path)
    overlays: dict[str, object] | None = None
    if overlays_path is not None:
        try:
            overlays = core_flags.load_overlays(overlays_path)
            for entries in overlays.values():
                if isinstance(entries, dict) and CUTOVER_FLAG in entries:
                    entries[CUTOVER_FLAG] = target
            core_flags.compose(payload, overlays, core_flags.DEFAULT_ENVIRONMENT)
        except core_flags.FlagConfigError as exc:
            raise CutoverRootError(f"flip refused: {exc}") from exc
    atomic_write_text(flags_path, json.dumps(payload, indent=2) + "\n")
    if overlays_path is not None and overlays is not None:
        atomic_write_text(overlays_path, json.dumps(overlays, indent=2) + "\n")
    if realization.is_file():
        stamp = f"\n- **cutover flip** — `pyforge.cutover_root` → `{target}`\n"
        realization.write_text(realization.read_text(encoding="utf-8") + stamp, encoding="utf-8")


class CutoverDuty:
    name = "cutover"

    def run(self, ns: argparse.Namespace) -> DutyResult:
        verb = getattr(ns, "cutover_verb", None)
        if verb not in _CUTOVER_VERBS:
            return DutyResult(ok=False, summary="cutover: need plan or flip")
        root = _repo_root()
        try:
            if verb == "plan":
                return plan(ns, root)
            target = str(getattr(ns, "to", "") or "")
            flags = resolve_flags_path(getattr(ns, "flags", None))
            if flags is None:
                return DutyResult(ok=False, summary="cutover flip: no flags.json")
            flip_root(flags, target, root / REALIZATION_LOG)
            return DutyResult(
                ok=True,
                summary=f"cutover flip → {read_cutover_root(flags)}",
            )
        except (CutoverRootError, CutoverLedgerError, OSError, json.JSONDecodeError) as exc:
            return DutyResult(ok=False, summary=f"cutover: {exc}")
