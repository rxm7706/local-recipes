"""Token-economy-kit verification (Story 28.3, SPEC-marshal-token-economy
CAP-3/CAP-4) -- the read-only half.

AC 1 asks for three DISTINCT checks over a seeded loop home: caveman-skill
deployment, the CCR store directory, and a present+fresh codegraph index.
``kit_checks`` produces exactly one ``KitCheck`` per ``model/kit.py``
``KitItem``, in ``KIT_ITEMS`` order, and ``kit_findings`` turns the
non-conformant ones into ``Finding``s. Keeping the two separate is what lets
``marshal seed check`` render all three checks -- including the passing and
the deliberately-off ones -- while only the problems reach the severity
report. A check that produced nothing when it passed would leave an operator
unable to tell "verified, fine" from "never looked".

**Gating, and why "off" is a status rather than an omission.** AC 4 requires
that a home with its layers declared off raises NO token-economy findings:
"the kit is declared-off, not missing". A layer that resolves ``enabled=False``
therefore yields a ``KitStatus.OFF`` check and no finding at all -- the item's
files are never even probed. ``context_layers`` is the mapping
``core.policy.resolve_context_layers`` returns (all five layer names, each
``{"enabled": bool, "aggressiveness": str}``); an absent layer key is read as
off, so a caller that hands over a partial mapping degrades in the same
direction the policy default already does.

**Degradation, and why it is INFO.** The spec's constraint is "an unavailable
instrument (platform gap, pixi blocker) disables its layer with a named
finding, never blocks a run". An enabled layer whose instrument is not
installed is reported as ``kit-instrument-unavailable`` at INFO severity --
INFO never fails ``marshal seed check``, not even under ``--strict``
(``CheckReport.failing`` reads HARD always, DRIFT under strict, INFO never).
That is a deliberate severity choice, not an oversight: caveman and codegraph
are linux-64-only, and a mac operator must not be handed a red check for a
package that cannot exist on their machine. The message names the INSTRUMENT
(``caveman``, ``codegraph``, ``headroom-ai`` -- what an operator installs),
not only the probe binary.

**What "fresh" means for the codegraph index, stated as a bound.** The index
is fresh when its own mtime is at or after the repo's ``HEAD`` commit
timestamp. This is a deliberate, cheap, deterministic comparison -- the same
git-timestamp discipline SPEC-marshal-token-economy CAP-13 requires of the
graph-node staleness flag ("a git-timestamp comparison ... not a per-write
model call"), and it needs no walk of the working tree. Its bound, stated
rather than implied: UNCOMMITTED edits do not make the index stale by this
rule, and a rebase that rewrites HEAD's timestamp forward makes it stale even
if no file changed. Both are acceptable for an advisory freshness signal, and
neither can produce a false GREEN for the case that matters (new commits
landed, index not resynced). When git itself cannot answer -- not a repo, no
commits, no ``git`` on PATH, a timeout -- no staleness claim is made at all:
the check reports ``OK`` on presence alone, the same degrade-rather-than-guess
direction ``detect/optout.py`` and ``verbs/check.py`` already take.

**Reads go through a seam, and why that is not ceremony.** ``kit_checks``
takes an optional ``fs`` (``KitReads``, structurally satisfied by
``ports.FsPort``). ``seed/verbs/kit.py`` WRITES the kit through an
``FsPort``, and its post-apply verification calls back into this module: if
that verification read the raw filesystem instead of the port it wrote
through, then under ANY non-local port it would report the writes it had
just made as missing and emit DRIFT for them. The default is plain
``pathlib``, so a caller with nothing to declare keeps today's behavior;
the one raw read that survives is the codegraph index's mtime, because
``FsPort`` exposes no stat -- and where it cannot be read, freshness is
reported as not-evaluated rather than fabricated.

**Purity.** Read-only: ``shutil.which``, ``Path.stat``/``read_text``, and one
``git log -1`` subprocess -- exactly the latitude
``tests/meta/test_p03_detect_is_pure.py`` already grants
``referenced_dep_findings`` ("read-only ``Path.read_text`` / ``git``
subprocess probes ... are expected and in scope for detect's job"), and
``kit_checks`` is enrolled in that test's own call list so the claim is
enforced rather than asserted. No ``seed.fs`` import, no
``seed.apply``/``seed.engine`` import (the P-03 layer rule), and nothing
here writes.
"""

from __future__ import annotations

import shutil
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable, Protocol

from pyforge.core.process import PosixProcess, ProcessError

from ..model.kit import (
    ARTICULATE_REGION,
    KIT_ITEMS,
    KitItem,
    KitItemId,
    articulate_region_body,
)
from ..regions.markers import MarkerError, RegionFormat, region_sha
from ..regions.parse import RegionParseError, parse_regions
from .findings import Finding, FindingType, Severity
from .hashes import region_body_text

__all__ = (
    "InstrumentProbe",
    "KitCheck",
    "KitReads",
    "KitStatus",
    "head_commit_timestamp",
    "item_present",
    "kit_checks",
    "kit_findings",
    "layer_enabled",
    "local_reads",
    "probe_instrument",
    "resolve_caveman_skill_source",
)

_GIT_TIMEOUT_S = 5.0


class KitReads(Protocol):
    """The three read operations this module needs to see a loop home.

    Structurally satisfied by ``ports.FsPort`` (and therefore by
    ``adapters.LocalFs`` and by any test double standing in for it), which
    is the point: ``seed/verbs/kit.py`` WRITES through an ``FsPort``, and a
    verification that read the raw filesystem instead would report the
    writes it just made as missing whenever the port is anything but the
    local one -- exactly the broken round-trip a fake-port test would then
    sit on top of while looking green. Declared as a narrow ``Protocol``
    rather than importing ``FsPort`` so ``detect/`` keeps depending on
    nothing but what it actually calls."""

    def exists(self, path: Path) -> bool: ...

    def is_dir(self, path: Path) -> bool: ...

    def read_text(self, path: Path) -> str | None: ...


class _LocalReads:
    """The default ``KitReads``: plain ``pathlib`` reads, degrading to
    "not there" / ``None`` on any I/O error, matching ``adapters.LocalFs``'s
    own suppress-``OSError``-to-``False`` convention for the same three
    operations."""

    def exists(self, path: Path) -> bool:
        try:
            return path.exists()
        except OSError:
            return False

    def is_dir(self, path: Path) -> bool:
        try:
            return path.is_dir()
        except OSError:
            return False

    def read_text(self, path: Path) -> str | None:
        try:
            return path.read_text(encoding="utf-8")
        except OSError, UnicodeDecodeError:
            return None


def local_reads() -> KitReads:
    """A fresh default ``KitReads``. A function, not a module constant, so
    no caller can accidentally share (or monkeypatch) one instance across
    unrelated checks."""
    return _LocalReads()


def item_present(item: KitItem, target: Path, fs: KitReads) -> bool:
    """Whether ``item`` is materialized at ``target``, keyed off the item's
    own ``is_dir`` rather than a per-item branch -- a directory item is
    present when the path IS a directory, a file item when it exists and is
    not one."""
    if item.is_dir:
        return fs.is_dir(target)
    return fs.exists(target) and not fs.is_dir(target)


class KitStatus(StrEnum):
    """One kit item's disposition. Kebab-case wire values, matching
    ``ArtifactState``/``FindingType``'s convention.

    ``OFF`` and ``OK`` are the two silent outcomes (no finding); the other
    three each map to exactly one ``FindingType`` in ``kit_findings``."""

    OFF = "layer-off"
    OK = "ok"
    MISSING = "missing"
    STALE = "stale"
    UNAVAILABLE = "instrument-unavailable"


@dataclass(frozen=True)
class KitCheck:
    """One of AC 1's three distinct checks, as plain JSON-serializable
    data. ``detail`` always says something -- including for ``OK`` and
    ``OFF`` -- so a report never has to explain a bare status word."""

    item_id: str
    layer: str
    instrument: str
    path: str
    status: KitStatus
    detail: str

    def to_json_dict(self) -> dict[str, str]:
        return {
            "item": self.item_id,
            "layer": self.layer,
            "instrument": self.instrument,
            "path": self.path,
            "status": self.status.value,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class InstrumentProbe:
    """Whether an item's instrument is usable on THIS machine.

    ``reason`` is filled only when ``available`` is ``False`` and is written
    to be pasted straight into a finding message. ``payload`` carries the
    resolved source bytes an apply step will need (today: the packaged
    caveman ``SKILL.md``), so the probe is performed once and both the check
    and the apply read the same answer instead of each resolving it."""

    available: bool
    reason: str = ""
    payload: Path | None = None


def resolve_caveman_skill_source(
    which: Callable[[str], str | None] | None = None,
) -> Path | None:
    """The packaged upstream caveman ``SKILL.md``, or ``None``.

    The conda package installs ``caveman-install`` as a symlink to
    ``<prefix>/lib/node_modules/caveman-installer/bin/install.js`` (the
    recipe's own ``npm install -g`` layout, asserted by its packaged tests),
    so the skill payload is ``<installer root>/skills/caveman/SKILL.md``.
    Resolved from the binary rather than from a hardcoded prefix so it works
    in a pixi env, a conda env, and a plain global npm install alike.

    ``which`` is injected so a test can prove both the found and the
    not-found path without installing node. It defaults to ``None`` and is
    resolved to ``shutil.which`` INSIDE the call rather than bound as a
    default argument at import time -- a default-argument binding would
    capture the function object once and make ``monkeypatch.setattr(
    "shutil.which", ...)`` silently ineffective here, which is exactly the
    kind of test that passes while proving nothing."""
    resolver = which if which is not None else shutil.which
    binary = resolver("caveman-install")
    if binary is None:
        return None
    try:
        installer_root = Path(binary).resolve(strict=True).parents[1]
    except OSError, IndexError:
        return None
    candidate = installer_root / "skills" / "caveman" / "SKILL.md"
    return candidate if candidate.is_file() else None


def probe_instrument(item: KitItem, *, which: Callable[[str], str | None] | None = None) -> InstrumentProbe:
    """Whether ``item``'s instrument is installed here, and -- for the
    caveman skill -- where its deployable payload lives.

    Two distinct unavailability shapes are reported separately because they
    have different remedies: the binary is not on ``PATH`` at all (install
    the package), versus the binary is there but the payload it should have
    shipped is not (a broken or unexpected install layout).

    ``which`` resolves at call time, never as a default argument -- see
    ``resolve_caveman_skill_source``'s own note for why."""
    resolver = which if which is not None else shutil.which
    if resolver(item.probe_binary) is None:
        return InstrumentProbe(
            available=False,
            reason=(f"{item.instrument} is not installed here ({item.probe_binary!r} is not on PATH)"),
        )
    if item.id is not KitItemId.CAVEMAN_SKILL:
        return InstrumentProbe(available=True)
    payload = resolve_caveman_skill_source(resolver)
    if payload is None:
        return InstrumentProbe(
            available=False,
            reason=(
                f"{item.instrument} is installed but its packaged skill payload "
                "(skills/caveman/SKILL.md) was not found beside caveman-install"
            ),
        )
    return InstrumentProbe(available=True, payload=payload)


def layer_enabled(context_layers: Mapping[str, Mapping[str, Any]] | None, layer: str) -> bool:
    """Whether ``layer`` is declared on. A ``None`` mapping, an absent
    layer, or a non-mapping entry all read as OFF -- the same direction
    ``core.policy.resolve_context_layers`` composes an absent ``[context]``
    block in, so a partial or missing mapping can never turn a layer ON by
    accident. Story 46.4: this probe has no harness-profile seam to resolve
    the repo-default ``"auto"`` tri-state against, so an unresolved
    ``"auto"`` also reads as OFF here rather than the ``bool("auto")``
    truthiness accident that would otherwise always read it as ON."""
    if not context_layers:
        return False
    entry = context_layers.get(layer)
    if not isinstance(entry, Mapping):
        return False
    enabled = entry.get("enabled", False)
    if isinstance(enabled, str):
        return False
    return bool(enabled)


def head_commit_timestamp(repo_root: Path, *, process: PosixProcess | None = None) -> int | None:
    """``HEAD``'s committer timestamp as a POSIX int, or ``None`` when git
    cannot answer (not a repo, no commits, no ``git``, a timeout, or
    unparseable output). ``None`` means "make no staleness claim", never
    "fresh" and never "stale"."""
    runner = process if process is not None else PosixProcess()
    try:
        result = runner.run(["git", "log", "-1", "--format=%ct"], cwd=repo_root, timeout_s=_GIT_TIMEOUT_S)
    except ProcessError:
        return None
    if result.returncode != 0:
        return None
    text = (result.stdout or "").strip()
    try:
        return int(text)
    except ValueError:
        return None


def _carve_out_state(text: str) -> str | None:
    """``None`` when the deployed skill carries Genesis's articulate
    carve-out INTACT; otherwise a clause naming what is wrong with it.

    Marker presence alone is not enough. The carve-out is the whole of
    AC 2's guarantee -- emptying or editing the body between two intact
    markers would leave nothing telling the session to keep verdicts,
    journals and escalation context articulated, while a
    markers-present-only check reported ``ok`` and Genesis never
    redeployed it. So the body is compared against
    ``region_sha(articulate_region_body())``: the same truncated-sha the
    ``begin`` marker carries, recomputed from the CURRENT expected body
    rather than trusted from the marker line (a hand-edit that rewrote both
    the body and the marker's own sha would otherwise still pass).

    An unparseable file (mismatched markers, a marker-grammar violation)
    reports the same way a missing region does -- the carve-out cannot be
    relied on either way, which is the point of checking for it."""
    try:
        spans = parse_regions(text, RegionFormat.HTML)
    except RegionParseError, MarkerError, NotImplementedError:
        return f"carries no parseable {ARTICULATE_REGION!r} managed region"
    span = next((candidate for candidate in spans if candidate.name == ARTICULATE_REGION), None)
    if span is None:
        return f"carries no {ARTICULATE_REGION!r} managed region"
    body = region_body_text(text, span)
    if region_sha(body.strip("\n")) != region_sha(articulate_region_body()):
        return (
            f"carries a {ARTICULATE_REGION!r} region whose body no longer matches the"
            " carve-out Genesis deploys (hand-edited, or written by an older model"
            " version)"
        )
    return None


def _caveman_check(item: KitItem, target: Path, fs: KitReads) -> tuple[KitStatus, str]:
    text = fs.read_text(target) if item_present(item, target, fs) else None
    if text is None:
        return KitStatus.MISSING, (f"the {item.instrument} skill is not deployed at {item.relpath}")
    problem = _carve_out_state(text)
    if problem is not None:
        return KitStatus.MISSING, (
            f"{item.relpath} exists but {problem} -- without it nothing tells the"
            " session to keep verdicts, journals and escalation context fully"
            " articulated"
        )
    return KitStatus.OK, (f"deployed at {item.relpath} with the {ARTICULATE_REGION!r} carve-out")


def _codegraph_check(
    item: KitItem,
    repo_root: Path,
    target: Path,
    *,
    fs: KitReads,
    process: PosixProcess | None,
) -> tuple[KitStatus, str]:
    if not item_present(item, target, fs):
        return KitStatus.MISSING, f"no codegraph index at {item.relpath}"
    head_ts = head_commit_timestamp(repo_root, process=process)
    if head_ts is None:
        return KitStatus.OK, (
            f"index present at {item.relpath}; freshness not evaluated (git could not report HEAD's timestamp)"
        )
    try:
        # The one raw read left in this module: `KitReads`/`FsPort` exposes
        # no stat, and freshness needs an mtime. A port whose files are not
        # on this filesystem therefore reports presence-only, which is the
        # honest answer -- never a fabricated "fresh".
        index_mtime = int(target.stat().st_mtime)
    except OSError:
        return KitStatus.OK, (f"index present at {item.relpath}; freshness not evaluated (its mtime could not be read)")
    if index_mtime < head_ts:
        return KitStatus.STALE, (
            f"the codegraph index at {item.relpath} predates HEAD (index mtime {index_mtime}, HEAD committed {head_ts})"
        )
    return KitStatus.OK, f"index present and at or after HEAD at {item.relpath}"


def kit_checks(
    repo_root: Path,
    context_layers: Mapping[str, Mapping[str, Any]] | None,
    *,
    probe: Callable[[KitItem], InstrumentProbe] = probe_instrument,
    process: PosixProcess | None = None,
    fs: KitReads | None = None,
) -> tuple[KitCheck, ...]:
    """One ``KitCheck`` per ``KIT_ITEMS`` entry, in declaration order.

    Order of questions per item, and why: layer first (an off layer is never
    probed and never touches disk -- AC 4), instrument second (an item whose
    instrument cannot exist here is reported as such rather than as a
    missing artifact the operator could "fix"), artifact last.

    ``fs`` is the read seam (``KitReads``; ``ports.FsPort`` satisfies it
    structurally) and defaults to plain ``pathlib``. A caller that WROTE
    through a port must pass that same port here, or this function will
    report the writes it just made as missing."""
    reads = fs if fs is not None else local_reads()
    checks: list[KitCheck] = []
    for item in KIT_ITEMS:
        if not layer_enabled(context_layers, item.layer):
            checks.append(
                KitCheck(
                    item_id=item.id.value,
                    layer=item.layer,
                    instrument=item.instrument,
                    path=item.relpath,
                    status=KitStatus.OFF,
                    detail=f"the {item.layer!r} context layer is declared off",
                )
            )
            continue

        instrument = probe(item)
        if not instrument.available:
            checks.append(
                KitCheck(
                    item_id=item.id.value,
                    layer=item.layer,
                    instrument=item.instrument,
                    path=item.relpath,
                    status=KitStatus.UNAVAILABLE,
                    detail=instrument.reason,
                )
            )
            continue

        target = repo_root / item.relpath
        if item.id is KitItemId.CAVEMAN_SKILL:
            status, detail = _caveman_check(item, target, reads)
        elif item.id is KitItemId.CODEGRAPH_INDEX:
            status, detail = _codegraph_check(item, repo_root, target, fs=reads, process=process)
        elif item_present(item, target, reads):
            status, detail = KitStatus.OK, f"store directory present at {item.relpath}"
        else:
            status, detail = (
                KitStatus.MISSING,
                (
                    f"no CCR store directory at {item.relpath} -- the wire wrapper has"
                    " nowhere loop-home-scoped to keep retrievable originals"
                ),
            )
        checks.append(
            KitCheck(
                item_id=item.id.value,
                layer=item.layer,
                instrument=item.instrument,
                path=item.relpath,
                status=status,
                detail=detail,
            )
        )
    return tuple(checks)


#: The one place a ``KitStatus`` becomes a ``(Severity, FindingType)`` pair.
#: ``OFF``/``OK`` are absent by construction: they raise nothing, and a
#: lookup miss below is what keeps that true without a second condition.
_FINDING_FOR_STATUS: dict[KitStatus, tuple[Severity, FindingType]] = {
    KitStatus.MISSING: (Severity.DRIFT, FindingType.KIT_ITEM_MISSING),
    KitStatus.STALE: (Severity.DRIFT, FindingType.KIT_ITEM_STALE),
    KitStatus.UNAVAILABLE: (Severity.INFO, FindingType.KIT_INSTRUMENT_UNAVAILABLE),
}


def kit_findings(checks: tuple[KitCheck, ...]) -> tuple[Finding, ...]:
    """The subset of ``checks`` that is worth reporting, as ``Finding``s.

    Never HARD: no kit finding may fail ``marshal seed check`` outright (the
    spec's "never blocks a run"). ``MISSING``/``STALE`` are DRIFT -- a real,
    fixable gap in a layer the operator asked for -- and ``UNAVAILABLE`` is
    INFO, which not even ``--strict`` fails on."""
    findings: list[Finding] = []
    for check in checks:
        pair = _FINDING_FOR_STATUS.get(check.status)
        if pair is None:
            continue
        severity, finding_type = pair
        findings.append(
            Finding.new(
                severity,
                finding_type,
                check.path,
                f"[{check.layer}] {check.item_id}: {check.detail}",
            )
        )
    return tuple(findings)
