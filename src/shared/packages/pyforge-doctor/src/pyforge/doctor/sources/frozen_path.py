"""The frozen-path-changed source -- the branch half of the freeze ``fnd:AD-22``
states: a change under the frozen paths of a capability the ledger marks
``rebuilding`` is a named FAIL (``spec-pyforge-doctor:CAP-94``, Story 56.1;
first built by Story 20.3).

**The rule.** ``fnd:AD-22`` (the steward spine,
``_bmad-output/projects/pyforge-steward/planning-artifacts/architecture/
architecture-pyforge-steward-2026-07-25/ARCHITECTURE-SPINE.md``, as steward
Story 120.3 amends it): each capability row carries its own ``state`` and its
``frozen_paths``; a capability entering ``rebuilding`` freezes its
``frozen_paths`` in ``local-recipes`` at once, and the freeze is this source's
to judge, keyed by ledger state, never by the root-of-record flag.

**The subject.** ``docs/foundry/capability-ledger.yaml`` and nothing else: the
v1 ledger of ``spec-foundry-capability-ledger:CAP-1`` (schema
``pyforge.capability-ledger/v1``; the one definition is that Spec's
``modes.md`` § Schema v1, written by steward Story 120.2). Its rows carry
``id``, ``state`` (``planned`` | ``rebuilding`` | ``verified-in-foundry`` |
``cut``) and, on a rebuilding row, ``frozen_paths`` (each a repo-relative file
or directory). The frozen set is the constant ``{"rebuilding"}``: no header
key is read for it (the header's ``frozen_states`` holds the same constant),
the retired ``moving`` state freezes nothing, and the ``cells:`` list is never
read -- a cell is never frozen. The schema version is not checked, so a v0
ledger (rows with no ``state``) reads ``0 frozen of <N> rows`` until steward
Story 121.3 regenerates it. Story 20.3 probed a ``docs/foundry/manifest``
file that never existed, so every run answered OK over no subject at all (the
2026-11-10 cutover readiness audit, MUST 2); this module replaced that probe.

**Verdicts.**

* a path changed between ``refs/remotes/origin/main`` and ``HEAD`` that equals
  or sits under a rebuilding row's frozen path (``_is_frozen``): one FAIL per
  (row id, changed path), naming both;
* a rebuilding row with no ``frozen_paths`` (absent, not a list, or no
  non-empty string in it): one FAIL, because it guards nothing;
* no rebuilding row: one OK naming ``0 frozen of <N> rows``; rebuilding rows
  with nothing changed under them: one OK naming ``<k> frozen of <N> rows``;
* a missing, unreadable or unparseable ledger, one that is not a mapping or has
  no ``capabilities`` list, or an unresolvable ``origin/main``: one
  cannot-evaluate WARN (``frozen-path-changed-unevaluable``, evidence
  ``unevaluable: true``), never an OK (``spec-pyforge-doctor:AD-15``). Anything
  else raised inside ``_gather`` is folded into one WARN by the outer
  ``degrade_on_exception`` net.

**Why this source can FAIL.** "Advisory, never a second PR gate" means never
competing with Warden's own PR-approval mechanism, not a categorical ban on
FAIL: a change under a frozen path is a FAIL by ``spec-pyforge-doctor:CAP-94``'s
own words, like the ``ledger-regression`` and ``spec-surface`` sources. The
exit domain stays ``{0, 2, 130}`` (``spec-pyforge-doctor:AD-2``): a WARN never
changes the exit code.

**Read-only, one subprocess site, independent.** Reads the ledger as data and
runs ``git diff --name-only`` through ``cli_bridge.run_git`` only
(``spec-pyforge-doctor:AD-5``); writes nothing. Imports no station package and
never invokes ``steward cutover plan`` (``spec-pyforge-doctor:AD-1``,
``spec-pyforge-doctor:AD-11``).
"""

from __future__ import annotations

from pathlib import Path

import yaml

from ..cli_bridge import CliBridgeError, run_git
from ..models import UNEVALUABLE_EVIDENCE_KEY, DoctorStatus, Finding, Source
from ..refs import ORIGIN_MAIN, display_ref
from . import degrade_on_exception

__all__ = ("gather",)

#: The one subject, relative to the target: ``docs/foundry/capability-ledger.yaml``.
_LEDGER_PARTS: tuple[str, ...] = ("docs", "foundry", "capability-ledger.yaml")
_LEDGER_SHOWN = "/".join(_LEDGER_PARTS)

#: ``fnd:AD-22``: the one freezing state. A constant -- never read from the ledger's header.
_FROZEN_STATES = frozenset({"rebuilding"})

_CHECK = "frozen-path-changed"
#: ``spec-pyforge-doctor:AD-15``'s ``<source>-unevaluable`` check for a cannot-evaluate WARN.
_CHECK_UNEVALUABLE = f"{_CHECK}-unevaluable"


class _Unevaluable(Exception):
    """The ledger exists but cannot be read as a ledger -- a cannot-evaluate WARN, never an OK."""


def _git(target: Path, *args: str) -> str | None:
    """``git`` stdout, or ``None`` on any failure -- mirrors
    ``sources/ledger.py``'s own ``_git`` wrapper exactly. Routes through
    ``cli_bridge.run_git`` (``spec-pyforge-doctor:AD-5``: the sole subprocess site)."""
    try:
        return run_git(target, list(args))
    except CliBridgeError, UnicodeDecodeError:
        return None


def _ledger_path(target: Path) -> Path:
    """``<target>/docs/foundry/capability-ledger.yaml`` -- the only file this source reads."""
    return target.joinpath(*_LEDGER_PARTS)


def _load_rows(path: Path) -> list[object]:
    """The ledger's ``capabilities`` list, read as data.

    RAISES ``_Unevaluable`` when the file cannot be read, does not parse as
    YAML, or does not parse to a mapping holding a ``capabilities`` list --
    each is one cannot-evaluate WARN in ``_gather``. The header and ``cells:``
    are never looked at.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise _Unevaluable(f"cannot be read ({type(exc).__name__})") from exc
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise _Unevaluable(f"does not parse as YAML ({type(exc).__name__})") from exc
    if not isinstance(data, dict):
        raise _Unevaluable(f"is not a mapping (got {type(data).__name__})")
    rows = data.get("capabilities")
    if not isinstance(rows, list):
        raise _Unevaluable("has no `capabilities` list")
    return rows


def _changed_paths(target: Path, *, base: str = ORIGIN_MAIN, head: str = "HEAD") -> set[str] | None:
    """The set of paths changed between ``base`` and ``head``, or ``None`` on
    any git failure (unresolvable ref, non-repo target, ...).

    ``-c core.quotepath=false`` disables git's default quoting/escaping of
    non-ASCII filenames in ``--name-only`` output (verified: a plain ``git
    diff --name-only`` prints ``"caf\\303\\251.py"`` for a real ``café.py``,
    only the real unescaped name with this flag) -- without it, a frozen
    path containing a non-ASCII character could never match a real changed
    path, silently missing a genuine violation."""
    output = _git(
        target,
        "-c",
        "core.quotePath=false",
        "diff",
        "--name-only",
        "-z",
        f"{base}..{head}",
    )
    if output is None:
        return None
    return {part for part in output.split("\0") if part}


def _is_frozen(changed_path: str, frozen_prefix: str) -> bool:
    """Path-boundary-aware prefix match: ``changed_path`` falls under
    ``frozen_prefix`` only if it IS that prefix or sits under it as a real
    subdirectory/file -- ``src/foo`` must never falsely match
    ``src/foobar/x.py``. A trailing slash and a leading ``./`` on
    ``frozen_prefix`` are both normalized away first -- ``git diff
    --name-only`` output is always plain-relative with no leading ``./``, so
    a ledger entry authored with one would otherwise never match a real
    changed path."""
    prefix = frozen_prefix.rstrip("/").removeprefix("./")
    return changed_path == prefix or changed_path.startswith(f"{prefix}/")


def _is_rebuilding(row: dict) -> bool:
    """Whether the row's ``state`` is in the constant frozen set. A non-string
    ``state`` (a list, a mapping) freezes nothing and never crashes the lookup."""
    state = row.get("state")
    return isinstance(state, str) and state in _FROZEN_STATES


def _row_id(row: dict) -> str:
    # `or`, not a `.get(..., default)` second arg: an `id: null` row has the
    # key PRESENT with value None, which would stringify to the text "None".
    return str(row.get("id") or "<no id>")


def _frozen_paths(row: dict) -> list[str]:
    """The row's usable frozen paths: the non-empty strings of its ``frozen_paths``
    list. Anything else in the list is skipped; a value that is not a list is none."""
    paths = row.get("frozen_paths")
    if not isinstance(paths, list):
        return []
    return [path for path in paths if isinstance(path, str) and path.strip()]


def _unevaluable(message: str, **evidence: object) -> Finding:
    return Finding(
        source=Source.FROZEN_PATH_CHANGED,
        check=_CHECK_UNEVALUABLE,
        status=DoctorStatus.WARN,
        message=f"{message} -- frozen paths cannot be evaluated",
        evidence={"ledger": _LEDGER_SHOWN, **evidence, UNEVALUABLE_EVIDENCE_KEY: True},
    )


def _gather(target: Path) -> tuple[Finding, ...]:
    ledger = _ledger_path(target)
    if not ledger.is_file():
        return (_unevaluable(f"capability ledger {_LEDGER_SHOWN} is missing"),)
    try:
        rows = _load_rows(ledger)
    except _Unevaluable as exc:
        return (_unevaluable(f"capability ledger {_LEDGER_SHOWN} {exc}"),)

    total = len(rows)
    # A row that is not a mapping is counted in <N> and freezes nothing.
    rebuilding = [row for row in rows if isinstance(row, dict) and _is_rebuilding(row)]
    if not rebuilding:
        return (
            Finding(
                source=Source.FROZEN_PATH_CHANGED,
                check=_CHECK,
                status=DoctorStatus.OK,
                message=f"0 frozen of {total} rows in {_LEDGER_SHOWN}",
                evidence={"ledger": _LEDGER_SHOWN, "rows": total, "frozen": 0},
            ),
        )

    findings: list[Finding] = []
    guarded: list[tuple[str, list[str]]] = []
    for row in rebuilding:
        row_id = _row_id(row)
        paths = _frozen_paths(row)
        if paths:
            guarded.append((row_id, paths))
            continue
        findings.append(
            Finding(
                source=Source.FROZEN_PATH_CHANGED,
                check=_CHECK,
                status=DoctorStatus.FAIL,
                message=f"{row_id}: rebuilding with no frozen_paths -- it guards nothing",
                evidence={"ledger": _LEDGER_SHOWN, "id": row_id},
            )
        )

    if not guarded:
        return tuple(findings)

    changed = _changed_paths(target)
    if changed is None:
        base = display_ref(ORIGIN_MAIN)
        findings.append(
            _unevaluable(
                f"could not diff {base}..HEAD for {len(guarded)} frozen row(s)",
                base=base,
                head="HEAD",
            )
        )
        return tuple(findings)

    violations = sorted(
        {
            (row_id, changed_path)
            for row_id, paths in guarded
            for changed_path in changed
            if any(_is_frozen(changed_path, prefix) for prefix in paths)
        }
    )
    for row_id, changed_path in violations:
        findings.append(
            Finding(
                source=Source.FROZEN_PATH_CHANGED,
                check=_CHECK,
                status=DoctorStatus.FAIL,
                message=f"{row_id}: change under a frozen path -- {changed_path}",
                evidence={"ledger": _LEDGER_SHOWN, "id": row_id, "path": changed_path},
            )
        )
    if findings:
        return tuple(findings)

    frozen_path_count = sum(len(paths) for _, paths in guarded)
    return (
        Finding(
            source=Source.FROZEN_PATH_CHANGED,
            check=_CHECK,
            status=DoctorStatus.OK,
            message=(
                f"{len(rebuilding)} frozen of {total} rows in {_LEDGER_SHOWN} "
                f"({frozen_path_count} frozen path(s)) -- no changed path falls under one"
            ),
            evidence={
                "ledger": _LEDGER_SHOWN,
                "rows": total,
                "frozen": len(rebuilding),
                "frozen_paths": frozen_path_count,
            },
        ),
    )


def gather(target: Path) -> tuple[Finding, ...]:
    """Judge whether ``origin/main..HEAD`` changed a path frozen by a row the
    capability ledger (``docs/foundry/capability-ledger.yaml``) marks
    ``rebuilding`` (``spec-pyforge-doctor:CAP-94``, ``fnd:AD-22``).

    A FAIL per (row id, changed path) and per rebuilding row with no frozen
    paths; one OK naming ``<k> frozen of <N> rows`` otherwise; one
    cannot-evaluate WARN when the ledger or the diff cannot be read
    (``spec-pyforge-doctor:AD-15``). The outer ``degrade_on_exception`` net
    folds anything else raised into one WARN.
    """
    return degrade_on_exception(Source.FROZEN_PATH_CHANGED, _CHECK, lambda: _gather(target))
