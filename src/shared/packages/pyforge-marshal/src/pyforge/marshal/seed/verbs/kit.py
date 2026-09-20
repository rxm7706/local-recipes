"""``marshal seed kit`` -- Genesis provisions the per-loop-home
token-economy kit (Story 28.3, SPEC-marshal-token-economy CAP-3/CAP-4).

The mutating half of the story; ``seed/detect/kit.py`` is the read-only
half, and this module never re-implements its questions -- it CALLS
``kit_checks`` to decide what is already in place and acts only on what is
not. That is the same detect-then-act discipline ``verbs/check.py`` states
for itself ("no module in this package re-implements a sibling's
classification rule"), and it is what makes ``marshal seed kit`` idempotent
by construction: a second run finds every item ``OK`` and writes nothing.

**Three provisioning steps, one per declared layer.**

* ``ccr-store`` (layer ``wire``) -- create ``<home>/.marshal/wire``, the
  directory Story 28.2's packaged wrapper points ``HEADROOM_WORKSPACE_DIR``
  at. Genesis creates it rather than letting headroom create it lazily so a
  ``marshal seed check`` before the first wrapped launch can tell "the store
  is provisioned" from "the wrapper silently fell back to a user-global
  cache" -- Story 28.2's own low-severity deferral names that fallback as a
  real risk.
* ``caveman-skill`` (layer ``output``) -- write
  ``<home>/.claude/skills/caveman/SKILL.md`` from the packaged upstream
  payload, with Genesis's articulate carve-out appended as a
  ``marshal-seed`` managed region. The upstream installer cannot do this:
  its Claude Code mechanism is ``claude plugin install`` (user-global,
  marketplace, networked) plus ``npx skills add``, and its ``--config-dir``
  scopes hook files and ``settings.json`` only. A per-loop-home deployment
  has to be a file copy, and once it is a file copy the carve-out can be
  part of it.
* ``codegraph-index`` (layer ``structure-graph``) -- build the index when
  absent (``codegraph init -y``) or resync it when stale (``codegraph
  sync -q``), through an INJECTABLE runner so the seam is testable without
  the instrument and without minutes of real indexing. See
  ``build_codegraph_index`` for why the create verb is ``init`` and not the
  ``index`` the help text makes look interchangeable.

**Never a failure.** Every step is independent. An item whose instrument is
unavailable is SKIPPED with a named ``kit-instrument-unavailable`` finding
naming the instrument and why (AC 3: "the seed still applies, the layer is
skipped, and a named finding reports exactly which instrument and why"); an
item whose write or index build actually fails always yields a finding
carrying the failure text -- ``kit-item-missing`` when the item is still
absent, ``kit-item-stale`` when a partial artifact survived the failure and
now reads as present -- and the run continues to the next item. The
severity/type mapping is ``detect/kit.py``'s, never a second copy (see
``_result_findings``). ``run_kit`` raises nothing of its own -- it returns a
``KitResult``,
exactly as ``verbs/check.py`` returns a ``CheckReport``, and the CLI decides
what to print. There is no exit code in which this verb refuses.

**Why the write seam is ``ports.FsPort`` rather than ``seed/fs.py``.**
``seed/fs.py`` is the sole owner of writes to a MANIFEST artifact: its
``never_write`` guard exists to stop Genesis clobbering a path the model
declares off-limits, and its callers all carry a ``Manifest`` for that
reason. A kit item is not a manifest artifact -- nothing in
``templates/manifest.yaml`` declares one, ``adopt``/``update`` never
materialize one, and the relevant boundary is AD-11's ("marshal writes only
inside the loop home"), not the model's. ``FsPort`` is the seam that
boundary is already enforced through, which is what lets ``cli/init.py``'s
``run_preflight`` provision the kit with its OWN injected port and stay
observable to ``tests/meta/test_ad11_write_boundary.py``. ``_guarded_target``
below re-derives the containment that guard asserts, per write, so the
argument is structural here too and not merely inherited from the caller.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol

from pyforge.core.errors import PyforgeError
from pyforge.core.process import PosixProcess, ProcessError

from ...ports.fs import FsPort
from ..detect.findings import Finding, FindingType, Severity
from ..detect.kit import (
    InstrumentProbe,
    KitCheck,
    KitStatus,
    kit_checks,
    kit_findings,
    probe_instrument,
)
from ..model.kit import (
    ARTICULATE_REGION,
    KIT_ITEMS,
    KitItem,
    KitItemId,
    articulate_region_body,
)
from ..model.version import ModelVersion
from ..regions.markers import RegionFormat, region_sha, render_begin, render_end

__all__ = (
    "INDEX_TIMEOUT_S",
    "SYNC_TIMEOUT_S",
    "IndexBuilder",
    "KitAction",
    "KitOutcome",
    "KitResult",
    "build_codegraph_index",
    "render_deployed_skill",
    "run_kit",
    "timeout_note",
)

#: Ceiling on a single ``codegraph`` invocation. A first full index of a
#: large repo is genuinely slow, so this is generous; it exists so an
#: instrument that hangs degrades into a named finding instead of wedging a
#: loop home's provisioning forever.
INDEX_TIMEOUT_S = 900.0

#: The same ceiling for the much cheaper incremental resync.
SYNC_TIMEOUT_S = 300.0


def timeout_note() -> str:
    """One sentence naming the provisioning ceilings, for a CLI help string
    or a preflight line.

    Derived from the two constants rather than restated, so an operator can
    never read a number this module no longer enforces -- the whole reason
    the ceilings are exported at all."""
    return (
        "a first codegraph index build runs unattended and can take minutes"
        f" (ceiling {INDEX_TIMEOUT_S:.0f}s; an incremental resync {SYNC_TIMEOUT_S:.0f}s)"
    )


class IndexBuilder(Protocol):
    """What creates or refreshes the codegraph index.

    ``stale`` is part of the CONTRACT, not a caller-side detail: ``False``
    means create (no index exists), ``True`` means refresh. A builder that
    could not tell the two apart would make
    ``build_codegraph_index``'s own `init`-vs-`sync` split untestable
    through this seam."""

    def __call__(self, repo_root: Path, *, stale: bool) -> str | None: ...


class KitAction(StrEnum):
    """What ``run_kit`` did about one item.

    ``SKIPPED`` covers both non-actions that are FINE (the layer is off, the
    instrument is absent); ``FAILED`` covers a real attempt that did not
    work. ``PLANNED`` is the dry-run counterpart of ``APPLIED`` -- a dry run
    reports what it WOULD do rather than a status word that reads as though
    it happened."""

    APPLIED = "applied"
    PRESENT = "already-present"
    PLANNED = "planned"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True)
class KitOutcome:
    """One item's provisioning outcome, as plain JSON-serializable data."""

    item_id: str
    layer: str
    instrument: str
    path: str
    action: KitAction
    detail: str

    def to_json_dict(self) -> dict[str, str]:
        return {
            "item": self.item_id,
            "layer": self.layer,
            "instrument": self.instrument,
            "path": self.path,
            "action": self.action.value,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class KitResult:
    """``run_kit``'s whole return value -- never an exception.

    ``checks`` is the POST-apply verification (a second, independent
    ``kit_checks`` pass), so ``marshal seed kit --apply`` proves what it
    achieved with the same detector ``marshal seed check`` uses rather than
    asserting success from the fact that no write raised."""

    outcomes: tuple[KitOutcome, ...]
    checks: tuple[KitCheck, ...]
    findings: tuple[Finding, ...]
    applied: bool

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "applied": self.applied,
            "outcomes": [outcome.to_json_dict() for outcome in self.outcomes],
            "checks": [check.to_json_dict() for check in self.checks],
            "findings": [finding.to_json_dict() for finding in self.findings],
        }


def render_deployed_skill(upstream: str, model_version: ModelVersion) -> str:
    """The bytes Genesis deploys: the packaged upstream skill, then the
    articulate carve-out in a ``marshal-seed`` managed region.

    The upstream text is passed through UNCHANGED and the carve-out is
    APPENDED, never interleaved -- so an upstream version bump is a clean
    re-copy, and ``seed/detect/kit.py``'s region check is asking about
    Genesis's own content only. HTML comment markers because the file is
    Markdown (``RegionFormat.HTML``)."""
    body = articulate_region_body()
    begin = render_begin(RegionFormat.HTML, ARTICULATE_REGION, model_version, region_sha(body))
    end = render_end(RegionFormat.HTML, ARTICULATE_REGION)
    prefix = upstream if upstream.endswith("\n") else f"{upstream}\n"
    return f"{prefix}\n{begin}\n{body}\n{end}\n"


def build_codegraph_index(repo_root: Path, *, stale: bool, process: PosixProcess | None = None) -> str | None:
    """Build or resync the codegraph index in ``repo_root``. Returns
    ``None`` on success or a human-readable failure reason.

    ``codegraph init -y`` for a first build, ``codegraph sync -q`` for the
    cheap incremental path when an index exists but predates HEAD.

    ``init``, NOT ``index``, for the first build -- verified live rather
    than taken from the help text. ``codegraph index``'s own ``--help``
    says "Rebuild the full index from scratch (same result as a fresh
    init)", which reads as though it would serve here; run against a
    directory with no ``.codegraph/`` it exits 1 with ``Run "codegraph
    init" first``. ``init`` is the create verb and ``index`` is the rebuild
    verb. ``-y`` is init's documented non-interactive flag ("skip every
    prompt and take the defaults (for scripts / CI / container
    bootstraps)") -- load-bearing here, because provisioning runs
    unattended and a prompt would hang until the timeout. ``init`` has no
    quiet flag; ``sync``'s ``-q`` is documented "for git hooks", which is
    this call's shape exactly.

    ``process`` is an injectable ``PosixProcess`` (the same seam
    ``detect/kit.py::head_commit_timestamp`` takes) so the argv, the flags
    and the timeouts above are pinned by a test rather than only by this
    docstring -- the `init`-vs-`index` correction was found by running the
    real tool, and a "simplification" that reverted it must fail a test, not
    merely contradict a paragraph."""
    argv = ["codegraph", "sync", "-q", str(repo_root)] if stale else ["codegraph", "init", "-y", str(repo_root)]
    timeout = SYNC_TIMEOUT_S if stale else INDEX_TIMEOUT_S
    runner = process if process is not None else PosixProcess()
    try:
        result = runner.run(argv, cwd=repo_root, timeout_s=timeout)
    except ProcessError as exc:
        return f"{' '.join(argv)}: {exc}"
    if result.returncode != 0:
        tail = ((result.stderr or "") + (result.stdout or "")).strip().splitlines()
        last = tail[-1] if tail else "no output"
        return f"{' '.join(argv)} exited {result.returncode}: {last}"
    return None


def _guarded_target(repo_root: Path, relpath: str) -> Path:
    """``repo_root / relpath``, refused if it does not stay inside
    ``repo_root``.

    Every ``relpath`` here is a module constant, so this cannot fire today
    -- it is the structural half of this module's AD-11 argument (see the
    module docstring): the containment ``tests/meta/test_ad11_write_boundary.py``
    asserts about the CALLER is re-derived here, per write, so a future kit
    item with an escaping path fails loudly instead of writing outside the
    loop home."""
    root = repo_root.resolve()
    target = (root / relpath).resolve()
    if target != root and root not in target.parents:
        raise ValueError(f"kit path {relpath!r} resolves outside the loop home {str(root)!r}")
    return repo_root / relpath


def _skip(item: KitItem, detail: str) -> KitOutcome:
    return KitOutcome(
        item_id=item.id.value,
        layer=item.layer,
        instrument=item.instrument,
        path=item.relpath,
        action=KitAction.SKIPPED,
        detail=detail,
    )


def _apply_ccr_store(item: KitItem, repo_root: Path, *, fs: FsPort) -> tuple[KitAction, str]:
    target = _guarded_target(repo_root, item.relpath)
    fs.ensure_dir(target)
    return KitAction.APPLIED, f"created the CCR store directory at {item.relpath}"


def _apply_caveman_skill(
    item: KitItem,
    repo_root: Path,
    probe: InstrumentProbe,
    model_version: ModelVersion,
    *,
    fs: FsPort,
) -> tuple[KitAction, str]:
    if probe.payload is None:
        # Unreachable through `probe_instrument` (an available caveman
        # probe always carries its payload); guarded anyway so an injected
        # probe cannot turn a missing payload into an AttributeError.
        return KitAction.FAILED, "the caveman skill payload was not resolved"
    upstream = probe.payload.read_text(encoding="utf-8")
    target = _guarded_target(repo_root, item.relpath)
    fs.ensure_dir(target.parent)
    fs.write_text_atomic(target, render_deployed_skill(upstream, model_version))
    return KitAction.APPLIED, (f"deployed the caveman skill to {item.relpath} with the {ARTICULATE_REGION!r} carve-out")


def _apply_codegraph_index(
    item: KitItem,
    repo_root: Path,
    *,
    stale: bool,
    index_builder: IndexBuilder,
) -> tuple[KitAction, str]:
    """Create or refresh the index, then stamp it.

    ``stale`` is passed THROUGH to the builder, never merely used to word
    the outcome: create and refresh are different commands (`codegraph init`
    vs `codegraph sync`), so a builder that could not tell them apart would
    make the distinction untestable -- the injected-builder test would be
    asserting on a string this function derived from the check status it
    already had, proving nothing about what ran.

    The mtime stamp closes a real permanent-DRIFT bug: `codegraph sync` with
    nothing to resync succeeds WITHOUT touching the db, so the index keeps
    an mtime older than HEAD, `kit_checks` keeps reporting `stale`, and every
    subsequent preflight re-runs sync and re-reports DRIFT forever. After a
    successful step the index IS current by definition, so its mtime is set
    to now. Best-effort: a port whose files are not on this filesystem has
    nothing to stamp, and failing to stamp must never turn a successful
    provisioning step into a failed one."""
    error = index_builder(repo_root, stale=stale)
    if error is not None:
        return KitAction.FAILED, error
    try:
        os.utime(repo_root / item.relpath, None)
    except OSError:
        pass
    verb = "resynced" if stale else "built"
    return KitAction.APPLIED, f"{verb} the codegraph index at {item.relpath}"


def run_kit(
    repo_root: Path,
    context_layers: Mapping[str, Mapping[str, Any]] | None,
    model_version: ModelVersion,
    *,
    fs: FsPort,
    apply: bool = False,
    probe: Callable[[KitItem], InstrumentProbe] = probe_instrument,
    index_builder: IndexBuilder = build_codegraph_index,
    process: PosixProcess | None = None,
) -> KitResult:
    """Provision (or, by default, plan) the token-economy kit in
    ``repo_root``.

    Explicit inputs only: ``context_layers`` is the caller's already-resolved
    ``core.policy.resolve_context_layers`` mapping (this module never reads a
    policy file -- ``cli/seed.py`` and ``cli/init.py`` each do their own
    boundary I/O and hand the answer over, the same seam ``verbs/check.py``
    uses for its ``manifest``), ``model_version`` is the bundled manifest's,
    and ``fs`` is an ``FsPort``.

    ``apply=False`` (the default, matching ``adopt``'s own dry-run-first
    posture) computes and reports every step without a single write.

    Order of operations: one ``kit_checks`` pass FIRST, so nothing is
    re-derived and an already-provisioned item is never rewritten; then the
    per-item actions; then a SECOND ``kit_checks`` pass whose findings are
    the ones returned. Reporting post-apply findings rather than pre-apply
    ones is what makes ``--apply`` honest: an item this run just provisioned
    stops being reported as missing, and an item whose apply silently did not
    take still is.

    BOTH ``kit_checks`` passes are handed the same ``fs`` this function
    writes through, and the same ``process`` seam -- otherwise the
    verification would read a filesystem the writes never reached (any
    non-local port) and report its own successful applies as missing, and
    every check would shell out to a real ``git`` no test could pin."""
    before = {
        check.item_id: check for check in kit_checks(repo_root, context_layers, probe=probe, process=process, fs=fs)
    }
    outcomes: list[KitOutcome] = []

    for item in KIT_ITEMS:
        check = before[item.id.value]

        if check.status is KitStatus.OFF:
            outcomes.append(_skip(item, check.detail))
            continue
        if check.status is KitStatus.UNAVAILABLE:
            outcomes.append(_skip(item, check.detail))
            continue
        if check.status is KitStatus.OK:
            outcomes.append(
                KitOutcome(
                    item_id=item.id.value,
                    layer=item.layer,
                    instrument=item.instrument,
                    path=item.relpath,
                    action=KitAction.PRESENT,
                    detail=check.detail,
                )
            )
            continue

        # MISSING or STALE -- a real action is owed.
        if not apply:
            verb = "refresh" if check.status is KitStatus.STALE else "provision"
            outcomes.append(
                KitOutcome(
                    item_id=item.id.value,
                    layer=item.layer,
                    instrument=item.instrument,
                    path=item.relpath,
                    action=KitAction.PLANNED,
                    detail=(f"would {verb} {item.relpath} ({item.summary}): {check.detail}"),
                )
            )
            continue

        # Re-probed rather than carried over from `kit_checks` above: the
        # check only needed an availability verdict, while the apply also
        # needs the resolved payload path an `InstrumentProbe` carries. One
        # `shutil.which` per item that actually owes an action.
        instrument = probe(item)

        try:
            if item.id is KitItemId.CCR_STORE:
                action, detail = _apply_ccr_store(item, repo_root, fs=fs)
            elif item.id is KitItemId.CAVEMAN_SKILL:
                action, detail = _apply_caveman_skill(item, repo_root, instrument, model_version, fs=fs)
            else:
                action, detail = _apply_codegraph_index(
                    item,
                    repo_root,
                    stale=check.status is KitStatus.STALE,
                    index_builder=index_builder,
                )
        except (OSError, UnicodeDecodeError, ValueError, PyforgeError) as exc:
            # Deliberately NOT a bare `except Exception` -- `tests/meta/
            # test_seed_no_bare_exception.py`'s sibling convention, and these
            # four families are every failure a write/read/containment step
            # here can actually have. `PyforgeError` is listed explicitly
            # and is load-bearing: `adapters/fs_local.FsError` derives from
            # `PyforgeError`/`Exception`, NOT from `OSError`, so without it
            # a refused `FsPort` write would escape this verb as a raise --
            # breaking the "never a failure" contract two paragraphs of the
            # module docstring rest on. Verified by
            # `test_a_failed_write_is_reported_not_raised`.
            action, detail = KitAction.FAILED, f"{type(exc).__name__}: {exc}"

        outcomes.append(
            KitOutcome(
                item_id=item.id.value,
                layer=item.layer,
                instrument=item.instrument,
                path=item.relpath,
                action=action,
                detail=detail,
            )
        )

    after = (
        kit_checks(repo_root, context_layers, probe=probe, process=process, fs=fs) if apply else tuple(before.values())
    )
    findings = _result_findings(after, outcomes)
    return KitResult(
        outcomes=tuple(outcomes),
        checks=tuple(after),
        findings=findings,
        applied=apply,
    )


def _result_findings(checks: tuple[KitCheck, ...], outcomes: list[KitOutcome]) -> tuple[Finding, ...]:
    """The findings ``run_kit`` reports: ``kit_findings``'s own verdict on
    the post-apply state, with the failure text of any step that genuinely
    tried and could not folded in.

    **The severity/type mapping is not re-derived here.** ``detect/kit.py``
    declares ``_FINDING_FOR_STATUS`` "the one place a ``KitStatus`` becomes a
    ``(Severity, FindingType)`` pair", and this module's own docstring says
    it "never re-implements its questions -- it CALLS ``kit_checks``". A
    second hand-rolled copy of that table (and of the
    ``[layer] item: detail`` message shape) is exactly how ``marshal seed
    kit --dry-run`` and ``marshal seed check`` come to disagree about the
    severity of identical state with no test failing. So ``kit_findings`` is
    called and its output is AMENDED via ``dataclasses.replace``, which
    preserves the ``(severity, type, remedy)`` triple it chose.

    ``kit_findings`` emits exactly one finding per non-silent check, in
    check order, so ``zip(..., strict=True)`` pairs them without a lookup --
    and fails loudly rather than mispairing if that ever stops being true.

    **A failed step ALWAYS produces a finding**, even when the re-check now
    reads ``OK``. That case is real, not theoretical: a ``codegraph init``
    killed at the timeout can leave a partial ``codegraph.db`` with a fresh
    mtime, which the detector correctly reads as present-and-fresh -- so
    without this branch the only record of the failure would be a
    ``KitOutcome`` nothing surfaces as a finding, and the operator would be
    told the kit is green. It reports as ``kit-item-stale`` (DRIFT): the
    artifact is there, but what produced it did not finish, so its content
    cannot be trusted and the remedy is the same re-run."""
    failure_by_item = {outcome.item_id: outcome.detail for outcome in outcomes if outcome.action is KitAction.FAILED}
    reportable = tuple(
        check for check in checks if check.status is not KitStatus.OFF and check.status is not KitStatus.OK
    )
    findings: list[Finding] = []
    for check, finding in zip(reportable, kit_findings(checks), strict=True):
        failure = failure_by_item.pop(check.item_id, None)
        if failure is None:
            findings.append(finding)
            continue
        findings.append(
            replace(
                finding,
                message=f"{finding.message}; the provisioning step failed: {failure}",
            )
        )

    # Whatever is LEFT in `failure_by_item` failed while its own re-check
    # came back silent (OK/OFF) -- see the docstring's partial-artifact case.
    by_item = {check.item_id: check for check in checks}
    for item_id, failure in failure_by_item.items():
        check = by_item[item_id]
        findings.append(
            Finding.new(
                Severity.DRIFT,
                FindingType.KIT_ITEM_STALE,
                check.path,
                f"[{check.layer}] {item_id}: the provisioning step failed"
                f" ({failure}), so what is on disk at {check.path} may be"
                " partial even though it now reads as present",
            )
        )
    return tuple(findings)
