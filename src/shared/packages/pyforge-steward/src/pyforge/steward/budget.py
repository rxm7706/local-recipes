"""Steward's `budget` duty-adapter module (AD-1/AD-6) — Epic 4's single
file, "one module per duty" shape, mirrors `provision.py`'s/`keys.py`'s own
precedent.

Epic 4 makes the "$1500/month locked" doctrine machine-readable,
*conservatively* — v1 declares and shows a ceiling, and honestly reports
that there is nothing to check it against, rather than fabricating a
pass/fail (AD-6, PRD D1, explicit non-goal: no Kubecost/OpenCost/
Infracost-class integration).

Story 4.1 slice: `.steward/budget.yaml` (FR-16) — `Ceiling`, `BudgetError`,
`CapParseError`, `parse_cap` (parses the `<amount><currency>/<period>`
shape, e.g. `1500usd/month`), `load_budget`/`save_budget`
(`yaml.safe_load`/`safe_dump` only, atomic temp-file + `os.replace` write —
mirrors `keys.py`'s `load_inventory`/`save_inventory` precedent), and
`set_ceiling`, which validates the cap string BEFORE touching the file at
all, so a malformed `--cap` value can never partially write or corrupt
`.steward/budget.yaml`. Wired as `steward budget set --cap <cap>`.

`BudgetDuty` is the `Duty`-conforming adapter `cli.py`'s `resolve_duty
("budget")` now returns, wiring `steward budget set`. Bare `steward budget`
(no verb) and `steward budget show`/`check` (not yet real verbs) all
degrade to `DutyResult(ok=True, ...)` naming the available verbs (AD-7,
`_BUDGET_VERBS` names only `set` so far) — `show`/`check` land in Stories
4.2/4.3.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import os
import re
import threading
from pathlib import Path

import yaml

from .interfaces import DutyResult

# ── Repo-root resolution (mirrors `provision.py`'s own walk-up precedent,
# keyed on `scripts/bmad-loop-worktree` — the one marker path that exists
# exactly once in this repo, at the true root) ─────────────────────────────

_BMAD_LOOP_WORKTREE_RELATIVE_PATH = Path("scripts/bmad-loop-worktree")
_BUDGET_RELATIVE_PATH = Path(".steward/budget.yaml")


def repo_root() -> Path:
    """Return the local-recipes checkout root.

    See `provision.py::repo_root`'s docstring for the full rationale — the
    identical walk-up search, duplicated here rather than imported cross-
    duty (each duty module resolves its own root; "one module per duty").
    """
    here = Path(__file__).resolve()
    for ancestor in here.parents:
        if (ancestor / _BMAD_LOOP_WORKTREE_RELATIVE_PATH).is_file():
            return ancestor
    raise RuntimeError(
        f"budget.py: could not locate {_BMAD_LOOP_WORKTREE_RELATIVE_PATH} "
        f"by walking up from {here} — this module must live inside a "
        "local-recipes checkout."
    )


def default_budget_path() -> Path:
    """`.steward/budget.yaml` at the repo root."""
    return repo_root() / _BUDGET_RELATIVE_PATH


# ── Cap parsing (FR-16, Story 4.1) ──────────────────────────────────────────

_CAP_PATTERN = re.compile(
    r"^(?P<amount>\d+(?:\.\d+)?)(?P<currency>[A-Za-z]{3})/(?P<period>[A-Za-z]+)$"
)


class CapParseError(ValueError):
    """A `--cap` value that does not match the `<amount><currency>/<period>`
    shape (e.g. `1500usd/month`), or whose amount is not a positive number."""


@dataclass(frozen=True)
class Ceiling:
    """One declared budget ceiling."""

    amount: float
    currency: str
    period: str
    declared_at: str


def parse_cap(cap: str) -> tuple[float, str, str]:
    """Parse a `--cap` value into `(amount, currency, period)`.

    Expects exactly `<amount><currency>/<period>` — a positive decimal
    amount, a 3-letter currency code, a `/`, then an alphabetic period
    (e.g. `1500usd/month`). `currency`/`period` are returned lowercased for
    stable storage.

    Raises `CapParseError` for a value that does not match this shape
    (missing unit, missing `/`, unparsable amount) or whose amount is not
    strictly positive (a zero/negative ceiling is not a value this doctrine
    can mean) — never a bare `ValueError`/`re.error`, so a caller can catch
    exactly this one class without also swallowing unrelated bugs.
    """
    match = _CAP_PATTERN.match(cap.strip())
    if not match:
        raise CapParseError(
            f"budget set: {cap!r} is not a valid cap — expected "
            "<amount><currency>/<period>, e.g. '1500usd/month'"
        )
    amount = float(match.group("amount"))
    if amount <= 0:
        raise CapParseError(
            f"budget set: {cap!r} has a non-positive amount ({amount}) — a "
            "budget ceiling must be a positive number"
        )
    return amount, match.group("currency").lower(), match.group("period").lower()


# ── `.steward/budget.yaml` read/write (FR-16) ───────────────────────────────
#
# The tracked, repo-root config location (ARCHITECTURE-SPINE.md's
# Consistency Conventions table) — mirrors `keys.py`'s
# `.steward/keys-inventory.yaml` precedent exactly: same directory
# convention, same `yaml.safe_load`/`safe_dump`-only discipline, same
# atomic temp-file + `os.replace` write (a reader observes either the
# fully-old or fully-new document, never a torn one).


class BudgetError(ValueError):
    """A malformed `.steward/budget.yaml` document."""


def load_budget(path: str | Path) -> tuple[Ceiling, ...]:
    """Load `.steward/budget.yaml`-shaped YAML from `path`.

    A missing file loads as `()` — mirrors `keys.py`'s `load_inventory`
    precedent (no ceiling ever declared is a normal, not an error, state).
    Raises `BudgetError` for a malformed document (not a mapping, or an
    entry missing a required field) — a corrupt budget file must never
    silently read as "no ceiling declared."
    """
    path = Path(path)
    if not path.is_file():
        return ()
    with path.open("r", encoding="utf-8") as f:
        document = yaml.safe_load(f) or {}
    if not isinstance(document, dict):
        raise BudgetError(
            f"{path}: top-level document must be a mapping, got "
            f"{type(document).__name__}"
        )
    ceilings: list[Ceiling] = []
    for raw in document.get("ceilings") or []:
        if not isinstance(raw, dict):
            raise BudgetError(f"{path}: each ceiling entry must be a mapping")
        try:
            ceilings.append(
                Ceiling(
                    amount=float(raw["amount"]),
                    currency=raw["currency"],
                    period=raw["period"],
                    declared_at=raw.get("declared_at"),
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise BudgetError(f"{path}: ceiling entry malformed: {exc}") from exc
    return tuple(ceilings)


def save_budget(path: str | Path, ceilings: tuple[Ceiling, ...]) -> None:
    """Write `ceilings` to `path` as `.steward/budget.yaml`-shaped YAML.

    Creates parent directories as needed. `yaml.safe_dump` only. Writes via
    a pid+thread-id-suffixed temp file then `os.replace` (never a direct
    `open("w")` on the real path) — mirrors `keys.py::save_inventory`'s
    identical rationale: a concurrent reader (e.g. `steward budget show`
    running at the same moment as a `set`) must never observe a partially
    written file.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    document = {
        "ceilings": [
            {
                "amount": c.amount,
                "currency": c.currency,
                "period": c.period,
                "declared_at": c.declared_at,
            }
            for c in ceilings
        ]
    }
    tmp_path = path.parent / f".{path.name}.pid{os.getpid()}.t{threading.get_native_id()}.tmp"
    with tmp_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(document, f, sort_keys=False)
    os.replace(tmp_path, path)


def set_ceiling(path: str | Path, cap: str) -> Ceiling:
    """Parse `cap` and declare it as the SOLE ceiling at `path`.

    `set` REPLACES any prior declaration — `.steward/budget.yaml` records
    one doctrine ("the ceiling is $1500/month"), not a growing history of
    every value ever set (see this story's spec, "Design Notes"). `cap` is
    parsed and validated FIRST, entirely in memory, before `path` is opened
    for writing at all — a malformed `cap` therefore raises `CapParseError`
    with `path` completely untouched (missing, or unchanged if it already
    existed), never partially written or corrupted.
    """
    amount, currency, period = parse_cap(cap)
    now = datetime.now(timezone.utc).isoformat()
    ceiling = Ceiling(amount=amount, currency=currency, period=period, declared_at=now)
    save_budget(path, (ceiling,))
    return ceiling


# ── BudgetDuty (Duty-protocol adapter) ──────────────────────────────────────

_BUDGET_VERBS: tuple[str, ...] = ("set",)


class BudgetDuty:
    """The real `budget` duty — dispatches `set` (Story 4.1; `show`/`check`
    land in Stories 4.2/4.3).

    Bare `steward budget` (no verb) degrades to `DutyResult(ok=True, ...)`
    naming the available verbs (AD-7), matching `KeysDuty`'s/`ProvisionDuty`'s
    identical precedent. A malformed `--cap` is caught here as
    `CapParseError` (a `ValueError` subclass) — reported as a duty-level
    failure, never conflated with an internal crash (AD-8 — that boundary
    is `cli.main()`'s alone).
    """

    name = "budget"

    def run(self, ns: argparse.Namespace) -> DutyResult:
        verb = getattr(ns, "budget_verb", None)
        if verb not in _BUDGET_VERBS:
            return DutyResult(
                ok=True,
                summary=f"budget: available verbs are {', '.join(_BUDGET_VERBS)}",
            )
        try:
            path = default_budget_path()
            ceiling = set_ceiling(path, ns.cap)
            return DutyResult(
                ok=True,
                summary=(
                    f"budget set: ceiling declared — {ceiling.amount:g} "
                    f"{ceiling.currency}/{ceiling.period} (written to {path})"
                ),
            )
        except CapParseError as exc:
            return DutyResult(ok=False, summary=str(exc))
