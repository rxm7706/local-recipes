"""The frozen-path-changed gather filter -- Doctor's verdict on whether a
capability entering ``rebuilding``/``moving`` had one of its own frozen
source paths touched by the working branch anyway (Story 20.3, Epic 20,
architecture spine AD-22).

**Why this detector exists.** AD-22 (``_bmad-output/projects/pyforge-steward/
planning-artifacts/architecture/architecture-python-foundry-cutover-2026-09-04/
ARCHITECTURE-SPINE.md:225``) says a capability entering ``rebuilding`` or
``moving`` freezes its source paths in ``local-recipes`` at once, and names a
``frozen-path-changed`` detector as the enforcement mechanism -- but nothing
had built it (``cutover-readiness.md`` G11: "never built"). Until the real
python-foundry cutover begins, no capability ledger exists at all
(``docs/foundry/`` is empty today), so this detector spends most of its life
reporting "nothing to check yet" -- but it must exist and be correct BEFORE
the first capability enters ``rebuilding``/``moving``, not be built reactively
after a frozen path is silently broken.

**The manifest schema is a documented synthesis, not a fixed contract.** The
architecture spine defines two only loosely related schemas -- a per-FILE
manifest row and a per-CAPABILITY row -- and neither, as literally written,
carries a path-list field a detector could diff against. This module reads
one YAML/JSON file at ``docs/foundry/manifest.{yaml,yml,json}`` (first found
wins) holding a ``capabilities:`` list, each entry carrying ``capability``,
``state``, and a ``frozen_paths`` list -- the minimal synthesis needed to
build something real (``[ASSUMPTION: schema]`` -- see the story spec's Design
Notes). If steward's own cutover work later lands a different concrete shape,
updating ``_find_manifest``/``_load_capabilities`` to match is that later
story's job, not a defect in this one.

**Read-only, one subprocess site.** Reads the capability ledger file and runs
``git diff --name-only`` only -- no writes, no git mutation, no other
subprocess (AD-5: ``cli_bridge`` is the sole subprocess site). ``_git``
mirrors ``sources/ledger.py``'s own wrapper exactly.

**Malformed ledger vs. absent ledger.** A found-but-malformed ledger
(unparseable YAML/JSON, not a mapping, missing/non-list ``capabilities``) is a
TRACKED-contract-file defect, not silent absence: ``_load_capabilities``
RAISES and is left uncaught inside ``_gather``, so the outer
``degrade_on_exception`` wrapper folds it into one generic WARN -- mirrors
``bmad_method.py``'s CAP-1/CAP-2 "raise on a tracked file, degrade at the
outer net" style, not Story 20.2's fail-open-per-layer style (a capability
ledger, once it exists, is a real contract file whose corruption is worth
flagging). An unresolvable git ref, or any other git failure, is instead a
WARN emitted directly by ``_gather`` -- mirrors ``sources/ledger.py``'s own
"unresolvable base ref... yields a WARN Finding" precedent for the identical
``origin/main..HEAD`` shape.

**Why this source can FAIL, unlike most of this epic's siblings.** Epic 20's
own framing paragraph says "HARD boundaries: every finding stays advisory --
warn at most," but this story's own Given/When/Then is explicit: "a change
under a frozen path is a fail naming the capability and the path." A more
specific, deliberately-worded AC governs over the general framing sentence --
this package already has extensive FAIL-capable precedent (``LEDGER_
REGRESSION``, ``SPEC_SURFACE``, ``PLATFORM_POLICY_SUITE``, ...) proving
"advisory, never a second PR gate" means never competing with Warden's own
PR-approval mechanism, not a categorical ban on FAIL.

**Independence.** Never imports ``pyforge.steward``/``pyforge.marshal`` or any
other station package, never invokes ``steward cutover plan``, never writes
to ``docs/foundry/**`` -- this source is structurally independent of the
mechanism it inspects, same rule every sibling source in this package
follows.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from ..cli_bridge import CliBridgeError, run_git
from ..models import DoctorStatus, Finding, Source
from . import degrade_on_exception

__all__ = ("gather",)

#: Probed in this order under ``docs/foundry/`` -- first existing file wins.
_MANIFEST_CANDIDATES: tuple[str, ...] = ("manifest.yaml", "manifest.yml", "manifest.json")

#: AD-22's own rule: only these two states freeze a capability's paths.
_FROZEN_STATES = frozenset({"rebuilding", "moving"})

_CHECK = "frozen-path-changed"


def _git(target: Path, *args: str) -> str | None:
    """``git`` stdout, or ``None`` on any failure -- mirrors
    ``sources/ledger.py``'s own ``_git`` wrapper exactly. Routes through
    ``cli_bridge.run_git`` (AD-5: the sole subprocess site)."""
    try:
        return run_git(target, list(args))
    except CliBridgeError, UnicodeDecodeError:
        return None


def _find_manifest(target: Path) -> Path | None:
    """The first existing ``docs/foundry/manifest.{yaml,yml,json}`` file, in
    that order, or ``None`` if none exists -- the dominant, expected outcome
    for every real invocation until cutover begins."""
    base = target / "docs" / "foundry"
    for name in _MANIFEST_CANDIDATES:
        candidate = base / name
        if candidate.is_file():
            return candidate
    return None


def _load_capabilities(path: Path) -> list[dict]:
    """Parse ``path`` (YAML or JSON, by extension) and return its
    ``capabilities`` list.

    RAISES ``ValueError``/``yaml.YAMLError``/``json.JSONDecodeError`` on
    anything that doesn't parse to ``{"capabilities": [...]}`` -- deliberately
    not caught here (Boundaries): a malformed tracked ledger propagates out of
    ``_gather`` to the outer ``degrade_on_exception`` net, which folds it into
    one generic WARN rather than this function inventing its own partial
    recovery.
    """
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        data = json.loads(text)
    else:
        data = yaml.safe_load(text)
    if not isinstance(data, dict) or not isinstance(data.get("capabilities"), list):
        raise ValueError(f"{path}: expected a mapping with a 'capabilities' list, got {data!r}")
    return data["capabilities"]


def _changed_paths(target: Path, *, base: str = "origin/main", head: str = "HEAD") -> set[str] | None:
    """The set of paths changed between ``base`` and ``head``, or ``None`` on
    any git failure (unresolvable ref, non-repo target, ...).

    ``-c core.quotepath=false`` disables git's default quoting/escaping of
    non-ASCII filenames in ``--name-only`` output (verified: a plain ``git
    diff --name-only`` prints ``"caf\\303\\251.py"`` for a real ``café.py``,
    only the real unescaped name with this flag) -- without it, a frozen
    path containing a non-ASCII character could never match a real changed
    path, silently missing a genuine violation."""
    output = _git(target, "-c", "core.quotepath=false", "diff", "--name-only", f"{base}..{head}")
    if output is None:
        return None
    return {line.strip() for line in output.splitlines() if line.strip()}


def _is_frozen(changed_path: str, frozen_prefix: str) -> bool:
    """Path-boundary-aware prefix match: ``changed_path`` falls under
    ``frozen_prefix`` only if it IS that prefix or sits under it as a real
    subdirectory/file -- ``src/foo`` must never falsely match
    ``src/foobar/x.py``. A trailing slash and a leading ``./`` on
    ``frozen_prefix`` are both normalized away first -- ``git diff
    --name-only`` output is always plain-relative with no leading ``./``, so
    a manifest entry authored with one would otherwise never match a real
    changed path."""
    prefix = frozen_prefix.rstrip("/").removeprefix("./")
    return changed_path == prefix or changed_path.startswith(f"{prefix}/")


def _gather(target: Path) -> tuple[Finding, ...]:
    manifest_path = _find_manifest(target)
    if manifest_path is None:
        return (
            Finding(
                source=Source.FROZEN_PATH_CHANGED,
                check=_CHECK,
                status=DoctorStatus.OK,
                message="no capability ledger found (pre-cutover)",
                evidence={"searched": [str((target / "docs" / "foundry" / name)) for name in _MANIFEST_CANDIDATES]},
            ),
        )

    # May raise (ValueError / yaml.YAMLError / json.JSONDecodeError) --
    # deliberately left uncaught here; the outer degrade_on_exception net
    # (wired by gather(), below) folds it into one generic WARN Finding.
    capabilities = _load_capabilities(manifest_path)
    manifest_evidence = str(manifest_path.relative_to(target))

    frozen_capabilities = [cap for cap in capabilities if isinstance(cap, dict) and cap.get("state") in _FROZEN_STATES]

    if not frozen_capabilities:
        count = len(capabilities)
        return (
            Finding(
                source=Source.FROZEN_PATH_CHANGED,
                check=_CHECK,
                status=DoctorStatus.OK,
                message=(
                    f"no capability is rebuilding/moving -- nothing frozen "
                    f"({count} capabilit{'y' if count == 1 else 'ies'} checked)"
                ),
                evidence={"manifest": manifest_evidence, "checked": count},
            ),
        )

    changed = _changed_paths(target)
    if changed is None:
        return (
            Finding(
                source=Source.FROZEN_PATH_CHANGED,
                check=_CHECK,
                status=DoctorStatus.WARN,
                message="could not diff origin/main..HEAD",
                evidence={
                    "manifest": manifest_evidence,
                    "frozen_capabilities": len(frozen_capabilities),
                },
            ),
        )

    violations: set[tuple[str, str]] = set()
    total_frozen_paths = 0
    for cap in frozen_capabilities:
        # `or`, not a `.get(..., default)` second arg: a `capability: null`
        # entry has the key PRESENT with value None, so `.get` would return
        # None (not the default), stringifying to the literal text "None".
        name = str(cap.get("capability") or "<unnamed>")
        frozen_paths = cap.get("frozen_paths")
        if not isinstance(frozen_paths, list):
            frozen_paths = []
        total_frozen_paths += len(frozen_paths)
        for changed_path in changed:
            if any(isinstance(prefix, str) and _is_frozen(changed_path, prefix) for prefix in frozen_paths):
                violations.add((name, changed_path))

    if not violations:
        return (
            Finding(
                source=Source.FROZEN_PATH_CHANGED,
                check=_CHECK,
                status=DoctorStatus.OK,
                message=(
                    f"{len(frozen_capabilities)} frozen capabilit"
                    f"{'y' if len(frozen_capabilities) == 1 else 'ies'} "
                    f"checked ({total_frozen_paths} frozen path(s)) -- no "
                    "changed path falls under a frozen prefix"
                ),
                evidence={
                    "manifest": manifest_evidence,
                    "checked_capabilities": len(frozen_capabilities),
                    "checked_frozen_paths": total_frozen_paths,
                },
            ),
        )

    findings: list[Finding] = []
    for name, changed_path in sorted(violations):
        findings.append(
            Finding(
                source=Source.FROZEN_PATH_CHANGED,
                check=_CHECK,
                status=DoctorStatus.FAIL,
                message=(f"{name}: change under a frozen path -- {changed_path}"),
                evidence={
                    "manifest": manifest_evidence,
                    "capability": name,
                    "path": changed_path,
                },
            )
        )
    return tuple(findings)


def gather(target: Path) -> tuple[Finding, ...]:
    """Judge whether ``origin/main..HEAD`` changed a path frozen by a
    capability currently ``rebuilding``/``moving`` in the tracked capability
    ledger (``docs/foundry/manifest.{yaml,yml,json}``).

    No ledger at all -- true for every real invocation until cutover begins
    -- is OK. A malformed ledger degrades to one generic WARN via the outer
    ``degrade_on_exception`` net; every other failure mode (no frozen
    capability, no violation, an unresolvable git ref) is handled directly by
    ``_gather``. A genuine violation is FAIL, one Finding per (capability,
    changed path) pair.
    """
    return degrade_on_exception(Source.FROZEN_PATH_CHANGED, _CHECK, lambda: _gather(target))
