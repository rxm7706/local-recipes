"""``herald deck sync-all`` -- Story 23.6 (``spec-design-sync-loop`` CAP-8,
plus CAP-3's "sweep" half): one command composing every existing kernel
verb -- enumerate, pull, refresh, derive, push, prove, publish -- into one
ordered per-deck run, for every registered deck or one ``--slug``.

**Never re-implements a kernel verb (Boundaries & Constraints).** Every
step below either calls an existing ``deck_pipeline`` function directly
(``pull_prototype``/``pull_marp_source``/``pull_standalone_bundle`` for
pull, ``push_exports(..., prove=True)`` for push+prove,
``select_exporter(...).export(...)`` for the export half of derive) or
shells the same pixi task an operator would run by hand for a step that
has no in-package function yet (``deck-facts --refresh`` for refresh,
``deck-trio`` for the trio half of derive, ``pixi run -e site site`` for
publish) -- mirroring ``deck_pipeline.PixiDeckExporter``'s own bounded-
subprocess pattern exactly. Every one of those shelled steps is an
injectable seam (``FactsRefresher``/``DeckDeriver``/``SitePublisher``,
mirroring ``DeckExporter``/``GitCommitter``'s pattern): a real
implementation subprocess-calls the pixi task; every test injects a fake.

**``facts.yaml`` is never pulled (Boundaries & Constraints).** ``refresh``
always re-derives it locally via ``deck-facts --refresh``, which reads only
TRACKED live repo sources (per its own pixi task description) -- never a
Design read.

**Pull's own internal re-derive is skipped, deliberately.** Each
``pull_*`` function already re-derives via its own ``exporter`` parameter
after landing a real change (see each one's docstring). Passed a
``_SkipExporter`` here instead of the default, so derivation happens
exactly once per sync -- via the ``derive`` step below, which runs AFTER
``refresh`` (which may itself rewrite the poster's data-fact literals) --
never twice, and never before a refresh that could invalidate the first
pass.

**Per-deck failure isolation.** One deck's own structural failure (a
broken subprocess call, a push conflict, a read-back mismatch, ...) is
caught and recorded on that deck's own ``DeckSyncReport.error`` rather than
aborting the run -- mirrors ``deck_pipeline._status_or_conflict``'s own
"one bad deck must not hide every other deck's valid report" isolation,
and ``herald scheduler run``'s advisory exit-0 convention: this command
REPORTS the fleet, it does not gate it. Only a structural problem outside
any one deck's own sync (an unknown ``--slug`` naming no deck directory at
all, an ``AuthError`` reaching Design) propagates as an ordinary
``HeraldError`` through ``dispatch`` (AD-6).

**``--dry-run`` (Boundaries & Constraints: "writes nothing").** Every
downstream step past pull's own read (``deck-facts --refresh``, ``deck-
trio``, ``deck-export``/``pptx-fill``, ``push_exports``, the site publish)
writes as a matter of course -- none of the scripts behind them has a
dry-run mode of its own to delegate to, and teaching each one a new flag
is outside this story's surface (``herald/cli.py``, ``pixi.toml``, the run
report, the runbook -- never ``scripts/deck_facts.py`` et al). So
``--dry-run`` never calls any of them: it previews only the pull step, via
``deck_pipeline.status`` (already 100% read-only), and reports whether a
live run would find that deck ``unchanged`` or would have something to
pull -- a deliberately narrower preview than a live run's full report, not
a simulation of every step.

**``proof_dir`` (Story 24.3, ``spec-pyforge-herald`` CAP-50).** An opt-in
seam: when given, every deck's ``DeckSyncReport`` from this run is also
serialized to ``<proof_dir>/<slug>/report-<timestamp>.json`` plus a
``stamps.write_stamp`` sidecar naming the current tree ref and Design
prototype etag -- the durable evidence a live idempotency proof (run
``sync-all`` twice against a real seeded deck) needs to point at. This
module stays env-var-free by design (every other optional seam here is
injected, never gated on an environment variable): the
``HERALD_LIVE_SYNC_PROOF=1`` gate that makes ``--proof-dir`` opt-in lives
in ``cli.py`` instead, consistent with the existing split between "what
the library does" and "what the CLI permits" (see ``_run_deck_status``'s
own ``--account`` refusal for the precedent).
"""

from __future__ import annotations

import json
import re
import subprocess
import uuid
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from pyforge.core.atomic_write import atomic_write_text

from . import errors, state, stamps
from .deck_pipeline import (
    _EXPORT_ARTIFACT_PREFIX,
    PROTOTYPE_ARTIFACT_KEY,
    STANDALONE_BUNDLE_ARTIFACT_KEY,
    LocalProver,
    _discover_export_files,
    _known_slugs,
    _persona_from_slug,
    _remote_path_for_artifact,
    pull_marp_source,
    pull_prototype,
    pull_standalone_bundle,
    push_exports,
    select_exporter,
)

if TYPE_CHECKING:
    # Mirrors bridge.py's/watch.py's own TYPE_CHECKING-only import:
    # sync_all's own signature needs DesignTransport only as a type
    # annotation, passed straight through to deck_pipeline's own CAP
    # functions -- never touched directly, never isinstance-checked.
    from .transport.base import DesignTransport

_POSTER_SUFFIX = " Infographic standalone.html"
"""Mirrors ``scripts/deck_trio.py``'s own ``POSTER_SUFFIX`` -- duplicated,
not imported: that module lives under ``scripts/``, not this package, and
this package has no scripts -> package dependency anywhere else either
(``stamps.py``'s module docstring records the identical reasoning for its
own duplicated ``tree`` computation)."""

_SUMMARY_REFRESHED_RE = re.compile(r"^summary\s+\S+:\s+(\d+) refreshed", re.MULTILINE)
"""Matches ``scripts/deck_facts.py``'s own ``--refresh`` summary line
(``f"summary   {slug}: {n_refreshed} refreshed, {n_skipped} skipped"``)."""

_WROTE_MARKER = ": wrote "
"""Matches ``scripts/deck_trio.py``'s own ``_write_if_changed`` convention
(``f"{slug}: wrote {path}"`` vs. ``f"{slug}: unchanged {path}"``)."""

_SUBPROCESS_TIMEOUT = 300.0
_GIT_TIMEOUT = 30.0


def _default_now() -> datetime:
    return datetime.now(timezone.utc)


class _SkipExporter:
    """A ``DeckExporter`` that does nothing -- passed to every ``pull_*``
    call below so a pull's own built-in re-derive never runs (see the
    module docstring: derivation happens exactly once, in the explicit
    ``derive`` step, after ``refresh``)."""

    def export(self, *, slug: str, repo_root: Path) -> None:
        return None


_SKIP_EXPORTER = _SkipExporter()


# --- report shape -------------------------------------------------------


@dataclass(frozen=True)
class DeckSyncReport:
    """One deck's sync-all outcome. ``labels()`` is the human-readable
    vocabulary the epics AC names: ``pulled`` / ``overwrote-local`` /
    ``overrode`` / ``derived`` / ``pushed`` / ``published`` / ``unchanged``
    -- these are additive labels describing what happened this run, not a
    single mutually-exclusive status (a deck can be ``pulled, derived,
    pushed`` all at once); ``unchanged`` appears alone, only when nothing
    else applies."""

    slug: str
    dry_run: bool = False
    pulled: tuple[str, ...] = ()
    overwrote_local: tuple[str, ...] = ()
    overrode: int = 0
    derived: bool = False
    pushed: tuple[str, ...] = ()
    proven: tuple[str, ...] = ()
    published: bool = False
    would_sync: bool = False
    skipped_reason: str | None = None
    error: str | None = None

    @property
    def unchanged(self) -> bool:
        if self.skipped_reason is not None or self.error is not None:
            return False
        if self.dry_run:
            return not self.would_sync
        return not (
            self.pulled or self.overwrote_local or self.overrode or self.derived
            or self.pushed
        )

    def labels(self) -> tuple[str, ...]:
        if self.skipped_reason is not None:
            return ("skipped",)
        if self.error is not None:
            return ("failed",)
        if self.dry_run:
            return ("would-sync",) if self.would_sync else ("unchanged",)
        out: list[str] = []
        if self.pulled:
            out.append("pulled")
        if self.overwrote_local:
            out.append("overwrote-local")
        if self.overrode:
            out.append("overrode")
        if self.derived:
            out.append("derived")
        if self.pushed:
            out.append("pushed")
        if self.proven:
            out.append("proven")
        if self.published:
            out.append("published")
        return tuple(out) if out else ("unchanged",)


@dataclass(frozen=True)
class SyncAllReport:
    """The whole run: every targeted deck's own report, plus whether the
    shared dossier-site publish step ran this run. ``publish_error`` is set
    (instead of raising) when that shared step itself fails, so a caller
    still gets every deck's own report rather than losing all of them to
    one publish failure."""

    decks: tuple[DeckSyncReport, ...]
    published: bool
    publish_error: str | None = None


def _report_to_dict(report: DeckSyncReport) -> dict[str, object]:
    """Plain field-by-field dict of one deck's report, JSON keys matching
    ``DeckSyncReport``'s own field names so a human or a future script can
    read the report without a decoder ring. Includes the derived
    ``labels``/``unchanged`` values ``dataclasses.asdict`` would not
    compute."""
    return {
        "slug": report.slug,
        "labels": list(report.labels()),
        "unchanged": report.unchanged,
        "dry_run": report.dry_run,
        "pulled": list(report.pulled),
        "overwrote_local": list(report.overwrote_local),
        "overrode": report.overrode,
        "derived": report.derived,
        "pushed": list(report.pushed),
        "proven": list(report.proven),
        "published": report.published,
        "would_sync": report.would_sync,
        "skipped_reason": report.skipped_reason,
        "error": report.error,
    }


def _write_proof(
    report: DeckSyncReport,
    *,
    proof_dir: Path,
    repo_root: Path,
    now: Callable[[], datetime],
) -> None:
    """Write ``<proof_dir>/<slug>/report-<UTC timestamp>-<random>.json``
    (mirrors ``stamps.py``'s own ``json.dumps(..., indent=2,
    sort_keys=True)`` formatting exactly) plus its ``stamps.write_stamp``
    sidecar -- the durable evidence a live idempotency proof run needs
    (Story 24.3, ``spec-pyforge-herald`` CAP-50). ``now`` is the same
    injected seam every other clock read in this module uses, never a
    direct ``datetime.now`` call. A sub-second timestamp plus a random
    suffix keeps two runs in the same microsecond from silently
    overwriting each other's report (``atomic_write_text`` replaces on a
    filename collision). Raises ``errors.HeraldError`` naming the path
    that failed, mirroring ``stamps.write_stamp``'s own AD-6 discipline --
    never a raw ``OSError``/``ValueError`` leak."""
    deck_dir = proof_dir / report.slug
    timestamp = now().strftime("%Y%m%dT%H%M%S%fZ")
    report_path = deck_dir / f"report-{timestamp}-{uuid.uuid4().hex[:8]}.json"
    try:
        deck_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(
            report_path,
            json.dumps(_report_to_dict(report), indent=2, sort_keys=True) + "\n",
        )
    except (OSError, ValueError) as exc:
        raise errors.HeraldError(
            f"could not write proof report {report_path}: {exc}"
        ) from exc
    stamps.write_stamp(report_path, repo_root=repo_root, slug=report.slug)


# --- injectable seams (mirroring DeckExporter/GitCommitter) -------------


@runtime_checkable
class FactsRefresher(Protocol):
    def refresh(self, *, slug: str, repo_root: Path) -> int:
        """Run ``deck-facts <slug> --refresh``; return the count of literals
        overridden this run (0 == no-op). Raise ``errors.HeraldError``
        naming what failed; never partially apply."""
        ...


@runtime_checkable
class DeckDeriver(Protocol):
    def derive(self, *, slug: str, repo_root: Path) -> bool:
        """Regenerate the deck's derived artifact set (``deck-trio`` +
        ``deck-export``/``pptx-fill``); return whether any derived artifact's
        bytes actually changed. Raise ``errors.HeraldError`` naming what
        failed."""
        ...


@runtime_checkable
class SitePublisher(Protocol):
    def publish(self, *, repo_root: Path) -> None:
        """Rebuild the dossier site (every deck's family page). Raise
        ``errors.HeraldError`` naming what failed; return normally on
        success."""
        ...


@runtime_checkable
class LocalEditDetector(Protocol):
    def is_dirty(self, *, repo_root: Path, path: Path) -> bool:
        """Whether ``path`` carries an uncommitted local edit right now.
        Raise ``errors.HeraldError`` naming what failed."""
        ...


def _run_bounded(
    cmd: list[str], *, cwd: Path, timeout: float, what: str
) -> subprocess.CompletedProcess[str]:
    """Shared bounded-subprocess wrapper -- mirrors
    ``deck_pipeline.PixiDeckExporter``'s own shape exactly (capture output,
    bounded timeout, never ``check=True``, a tail of stderr/stdout on a
    non-zero exit)."""
    try:
        completed = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired as exc:
        raise errors.HeraldError(
            f"{what} failed: {' '.join(cmd)!r} in {cwd} exceeded {timeout}s ({exc})"
        ) from exc
    except OSError as exc:
        raise errors.HeraldError(
            f"{what} failed: could not run {' '.join(cmd)!r} in {cwd} ({exc})"
        ) from exc
    if completed.returncode != 0:
        tail = (completed.stderr or completed.stdout or "").strip()[-2000:]
        raise errors.HeraldError(
            f"{what} failed: {' '.join(cmd)!r} in {cwd} exited "
            f"{completed.returncode}: {tail}"
        )
    return completed


class PixiFactsRefresher:
    """The real ``FactsRefresher``: ``pixi run -e pyforge-guild deck-facts
    <slug> --refresh``, one bounded subprocess call. Never invoked by this
    package's own tests (every ``sync_all`` test injects a fake)."""

    def __init__(self, *, timeout: float = _SUBPROCESS_TIMEOUT) -> None:
        self._timeout = timeout

    def refresh(self, *, slug: str, repo_root: Path) -> int:
        completed = _run_bounded(
            ["pixi", "run", "-e", "pyforge-guild", "deck-facts", slug, "--refresh"],
            cwd=repo_root,
            timeout=self._timeout,
            what="deck-facts --refresh",
        )
        match = _SUMMARY_REFRESHED_RE.search(completed.stdout)
        return int(match.group(1)) if match else 0


class PixiDeckDeriver:
    """The real ``DeckDeriver``: ``deck-trio --head --deck`` (only when the
    deck has a poster at ``project/*Infographic standalone.html`` --
    ``deck-trio`` itself refuses on a missing poster, so this is skipped
    rather than treated as a failure for a deck that has not adopted one
    yet) followed by ``select_exporter(...).export(...)`` -- the identical
    call ``pull_*``'s own built-in re-derive makes, reused rather than
    duplicated. ``changed`` is true when ``deck-trio`` reported writing a
    file (its own ``": wrote "`` convention) or the discovered export set's
    filename/hash fingerprint moved. Never invoked by this package's own
    tests (every ``sync_all`` test injects a fake, including for
    ``exporter_factory`` -- a bare monkeypatch of this module's own
    ``subprocess`` would not reach ``select_exporter(...).export(...)``'s
    OWN subprocess call, which lives in ``deck_pipeline``'s module
    namespace, not this one)."""

    def __init__(
        self,
        *,
        timeout: float = _SUBPROCESS_TIMEOUT,
        exporter_factory: Callable[[str, Path], object] | None = None,
    ) -> None:
        self._timeout = timeout
        self._exporter_factory = exporter_factory or select_exporter

    def derive(self, *, slug: str, repo_root: Path) -> bool:
        deck_dir = repo_root / "presentations" / slug
        before = self._export_fingerprint(deck_dir, slug)
        trio_changed = False
        project_dir = deck_dir / "project"
        has_poster = project_dir.is_dir() and any(
            project_dir.glob(f"*{_POSTER_SUFFIX}")
        )
        if has_poster:
            completed = _run_bounded(
                ["pixi", "run", "-e", "pyforge-guild", "deck-trio", slug,
                 "--head", "--deck"],
                cwd=repo_root,
                timeout=self._timeout,
                what="deck-trio",
            )
            trio_changed = _WROTE_MARKER in completed.stdout
        self._exporter_factory(slug, repo_root).export(slug=slug, repo_root=repo_root)
        after = self._export_fingerprint(deck_dir, slug)
        return trio_changed or before != after

    @staticmethod
    def _export_fingerprint(deck_dir: Path, slug: str) -> tuple[tuple[str, str], ...]:
        return tuple(
            sorted(
                (candidate.filename, candidate.local_hash)
                for candidate in _discover_export_files(deck_dir, slug)
            )
        )


class PixiSitePublisher:
    """The real ``SitePublisher``: ``pixi run -e site site``, one bounded
    subprocess call -- rebuilds every deck's family page in one pass
    (``docsite/build.py`` has no per-slug scope). Never invoked by this
    package's own tests (every ``sync_all`` test injects a fake)."""

    def __init__(self, *, timeout: float = _SUBPROCESS_TIMEOUT) -> None:
        self._timeout = timeout

    def publish(self, *, repo_root: Path) -> None:
        _run_bounded(
            ["pixi", "run", "-e", "site", "site"],
            cwd=repo_root,
            timeout=self._timeout,
            what="site publish",
        )


class GitLocalEditDetector:
    """The real ``LocalEditDetector``: ``git status --porcelain -- <path>``
    -- non-empty output means an uncommitted local edit exists. Never
    invoked by this package's own tests (every ``sync_all`` test injects a
    fake)."""

    def __init__(self, *, timeout: float = _GIT_TIMEOUT) -> None:
        self._timeout = timeout

    def is_dirty(self, *, repo_root: Path, path: Path) -> bool:
        completed = _run_bounded(
            ["git", "status", "--porcelain", "--", str(path)],
            cwd=repo_root,
            timeout=self._timeout,
            what="local-edit check",
        )
        return bool(completed.stdout.strip())


# --- the loop -------------------------------------------------------------


def _local_path_for_pull(
    deck_dir: Path, slug: str, artifact_key: str, *, persona: str, date_str: str
) -> Path:
    """The exact local path each ``pull_*`` function itself lands
    ``artifact_key`` at -- duplicated here (not exported by
    ``deck_pipeline``) purely so the dirty-check below can run BEFORE the
    pull call that would overwrite it. ``date_str`` must be derived from
    the same ``now`` passed to the ``pull_*`` call for the two to agree."""
    if artifact_key == PROTOTYPE_ARTIFACT_KEY:
        return deck_dir / "project" / f"PyForge {persona}.dc.html"
    if artifact_key == STANDALONE_BUNDLE_ARTIFACT_KEY:
        return (
            deck_dir / "src" / "marp"
            / f"{slug}-infographic-standalone-{date_str}.html"
        )
    if artifact_key.startswith("marp:"):
        kind = artifact_key.removeprefix("marp:")
        return deck_dir / "src" / "marp" / f"{slug}-{kind}-{date_str}.md"
    raise errors.HeraldError(
        f"cannot sync {slug!r}: unrecognized tracked artifact key "
        f"{artifact_key!r}"
    )


def _pull_one(
    transport: DesignTransport,
    *,
    slug: str,
    repo_root: Path,
    state_path: Path,
    artifact_key: str,
    deck_dir: Path,
    persona: str,
    date_str: str,
    edit_detector: LocalEditDetector,
    prover: LocalProver | None,
    now: Callable[[], datetime],
) -> tuple[bool, bool]:
    """Pull one tracked artifact. Returns ``(changed, overwrote_local)``:
    ``changed`` is ``not result.unchanged``; ``overwrote_local`` is true
    only when the local file existed, carried an uncommitted edit, AND the
    pull actually changed it (a dirty file the pull left untouched -- the
    etag hadn't moved -- was never overwritten, so it is not reported)."""
    local_path = _local_path_for_pull(
        deck_dir, slug, artifact_key, persona=persona, date_str=date_str
    )
    was_dirty = local_path.is_file() and edit_detector.is_dirty(
        repo_root=repo_root, path=local_path
    )
    if artifact_key == PROTOTYPE_ARTIFACT_KEY:
        result = pull_prototype(
            transport, slug=slug, repo_root=repo_root, state_path=state_path,
            prover=prover, exporter=_SKIP_EXPORTER, now=now,
        )
    elif artifact_key == STANDALONE_BUNDLE_ARTIFACT_KEY:
        result = pull_standalone_bundle(
            transport, slug=slug, repo_root=repo_root, state_path=state_path,
            exporter=_SKIP_EXPORTER, now=now,
        )
    else:
        kind = artifact_key.removeprefix("marp:")
        result = pull_marp_source(
            transport, slug=slug, repo_root=repo_root, state_path=state_path,
            kind=kind, exporter=_SKIP_EXPORTER, now=now,
        )
    changed = not result.unchanged
    return changed, (changed and was_dirty)


def _dry_run_preview(
    transport: DesignTransport, *, slug: str, existing: state.DeckState
) -> DeckSyncReport:
    """Read-only preview of the pull step only (module docstring). Compares
    only pull-tracked keys, skipping ``_EXPORT_ARTIFACT_PREFIX`` ones the
    same way ``_sync_one_deck``'s real-run loop does -- unlike
    ``deck_pipeline.status``, which walks every tracked key including
    ``export:*`` ones and raises via ``_remote_path_for_artifact`` for any
    of them (an ``export:*`` key is push-tracked, never pull-tracked, so it
    has no remote path to compare at all).

    A transport failure or a since-deleted remote file
    (``errors.TransportError``) is reported as a conflict (``error=...``,
    ``labels() == ("failed",)``) rather than folded into ``would_sync``: a
    conflict is not a confirmed pending change, and calling it
    ``unchanged`` would be equally misleading."""
    saw_conflict = False
    saw_change = False
    for artifact_key, etag in sorted(existing.etags.items()):
        if artifact_key.startswith(_EXPORT_ARTIFACT_PREFIX):
            continue  # push-tracked, not pull-tracked
        remote_path = _remote_path_for_artifact(slug, artifact_key)
        try:
            file_read = transport.read_file(
                project_id=existing.project_id, path=remote_path, if_none_match=etag
            )
        except errors.TransportError:
            saw_conflict = True
            continue
        if not file_read.unchanged:
            saw_change = True
    if saw_conflict:
        return DeckSyncReport(
            slug=slug, dry_run=True,
            error="dry-run: could not compare against Design (conflict)",
        )
    return DeckSyncReport(slug=slug, dry_run=True, would_sync=saw_change)


def _sync_one_deck(
    transport: DesignTransport,
    *,
    slug: str,
    repo_root: Path,
    state_path: Path,
    dry_run: bool,
    facts_refresher: FactsRefresher,
    deriver: DeckDeriver,
    edit_detector: LocalEditDetector,
    prover: LocalProver | None,
    now: Callable[[], datetime],
) -> DeckSyncReport:
    existing = state.read(state_path, slug)
    if existing is None:
        return DeckSyncReport(
            slug=slug, dry_run=dry_run,
            skipped_reason="not seeded -- run 'herald deck seed' first",
        )
    if not existing.etags:
        # A freshly seeded deck with nothing pulled/pushed yet -- distinct
        # from a genuinely fully-synced "unchanged" deck (there is nothing
        # here to compare against, pull-tracked or otherwise).
        return DeckSyncReport(
            slug=slug, dry_run=dry_run,
            skipped_reason=(
                "seeded but nothing pulled yet -- run 'herald deck pull' first"
            ),
        )

    if dry_run:
        return _dry_run_preview(transport, slug=slug, existing=existing)

    deck_dir = repo_root / "presentations" / slug
    persona = _persona_from_slug(slug)
    # Resolved exactly once for this deck's whole sync pass: `pull_*`
    # themselves call `now()` again internally for the actual write path,
    # so passing the live `now` through here (rather than a callable
    # frozen to this one value) could disagree across a UTC-midnight
    # boundary with the value the dirty-check below already used to build
    # `date_str` -- inspecting the wrong dated file.
    frozen_now = now()

    def _frozen_now() -> datetime:
        return frozen_now

    date_str = frozen_now.strftime("%Y-%m-%d")

    pulled: list[str] = []
    overwrote_local: list[str] = []
    for artifact_key in sorted(existing.etags):
        if artifact_key.startswith(_EXPORT_ARTIFACT_PREFIX):
            continue  # push-tracked, not pull-tracked
        changed, overwrote = _pull_one(
            transport, slug=slug, repo_root=repo_root, state_path=state_path,
            artifact_key=artifact_key, deck_dir=deck_dir, persona=persona,
            date_str=date_str, edit_detector=edit_detector, prover=prover,
            now=_frozen_now,
        )
        if changed:
            pulled.append(artifact_key)
        if overwrote:
            overwrote_local.append(artifact_key)

    # A refresh/derive/push failure here must not discard the pull facts
    # already gathered above (including a real `overwrote-local` warning)
    # -- the outer per-deck catch in `sync_all` would otherwise replace the
    # whole report with a bare error. `AuthError` still propagates (module
    # docstring): it means Design itself is unreachable, which halts the
    # whole run, not just this deck.
    try:
        overrode = facts_refresher.refresh(slug=slug, repo_root=repo_root)
        derived = deriver.derive(slug=slug, repo_root=repo_root)
        push_result = push_exports(
            transport, slug=slug, repo_root=repo_root, state_path=state_path,
            prove=True, now=_frozen_now,
        )
    except errors.AuthError:
        raise
    except errors.HeraldError as exc:
        return DeckSyncReport(
            slug=slug,
            pulled=tuple(pulled),
            overwrote_local=tuple(overwrote_local),
            error=str(exc),
        )

    return DeckSyncReport(
        slug=slug,
        pulled=tuple(pulled),
        overwrote_local=tuple(overwrote_local),
        overrode=overrode,
        derived=derived,
        pushed=push_result.pushed,
        proven=push_result.proven,
    )


def sync_all(
    transport: DesignTransport,
    *,
    slug: str | None = None,
    repo_root: Path,
    dry_run: bool = False,
    state_path: Path | None = None,
    facts_refresher: FactsRefresher | None = None,
    deriver: DeckDeriver | None = None,
    site_publisher: SitePublisher | None = None,
    edit_detector: LocalEditDetector | None = None,
    proof_dir: Path | None = None,
    prover: LocalProver | None = None,
    now: Callable[[], datetime] | None = None,
) -> SyncAllReport:
    """CAP-8 + CAP-3's sweep half (Story 23.6): enumerate -> pull -> refresh
    -> derive -> push -> prove -> publish, in order, for every registered
    deck (``slug is None``) or just ``slug``.

    A deck directory that does not exist under ``presentations/`` at all is
    a ``HeraldError`` (a usage problem, mirroring ``deck_facts.py``'s own
    ``presentations/<slug> not found`` refusal) -- there is nothing to
    report for it. A deck directory that exists but has never been seeded
    is reported ``skipped_reason=...`` rather than raised: "every
    registered deck" legitimately includes an unseeded twin (Story 23.2's
    own three fresh twins, on their very first run before anyone seeds
    them).

    ``publish`` runs at most once per call, after every targeted deck has
    been attempted, and only when at least one deck actually changed
    something (a fully-idempotent second run publishes nothing, matching
    the "zero writes" AC without hand-wiring a special case for it) -- the
    site build has no per-slug scope, so every deck that changed this run
    is marked ``published`` together."""
    resolved_state_path = (
        repo_root / state.DEFAULT_STATE_PATH if state_path is None else state_path
    )
    resolved_facts_refresher = facts_refresher or PixiFactsRefresher()
    resolved_deriver = deriver or PixiDeckDeriver()
    resolved_site_publisher = site_publisher or PixiSitePublisher()
    resolved_edit_detector = edit_detector or GitLocalEditDetector()
    resolved_now = now or _default_now

    if slug is not None:
        if not (repo_root / "presentations" / slug).is_dir():
            raise errors.HeraldError(
                f"cannot sync-all: presentations/{slug} not found"
            )
        targets = [slug]
    else:
        targets = _known_slugs(repo_root, resolved_state_path)

    reports: list[DeckSyncReport] = []
    for one in targets:
        try:
            reports.append(
                _sync_one_deck(
                    transport, slug=one, repo_root=repo_root,
                    state_path=resolved_state_path, dry_run=dry_run,
                    facts_refresher=resolved_facts_refresher, deriver=resolved_deriver,
                    edit_detector=resolved_edit_detector, prover=prover, now=resolved_now,
                )
            )
        except errors.AuthError:
            # Design itself is unreachable -- halts the whole run, not just
            # this deck (module docstring).
            raise
        except errors.HeraldError as exc:
            reports.append(DeckSyncReport(slug=one, dry_run=dry_run, error=str(exc)))

    any_change = any(
        r.error is None and r.skipped_reason is None and not r.unchanged
        for r in reports
    )
    published = False
    publish_error: str | None = None
    if any_change and not dry_run:
        try:
            resolved_site_publisher.publish(repo_root=repo_root)
        except errors.HeraldError as exc:
            # A publish failure must not discard every deck's own
            # already-gathered report -- the caller still needs to see what
            # each deck did before the shared publish step broke.
            publish_error = str(exc)
        else:
            published = True
            reports = [
                replace(r, published=True)
                if r.error is None and r.skipped_reason is None and not r.unchanged
                else r
                for r in reports
            ]

    if proof_dir is not None:
        # Per-deck isolation, mirroring the main sync loop above (module
        # docstring): one report's proof-write failure must not discard
        # every other already-synced deck's own valid report.
        proof_errors: list[str] = []
        for report in reports:
            try:
                _write_proof(
                    report, proof_dir=proof_dir, repo_root=repo_root, now=resolved_now
                )
            except errors.HeraldError as exc:
                proof_errors.append(str(exc))
        if proof_errors:
            raise errors.HeraldError(
                "could not write proof report(s): " + "; ".join(proof_errors)
            )

    return SyncAllReport(
        decks=tuple(reports), published=published, publish_error=publish_error
    )
