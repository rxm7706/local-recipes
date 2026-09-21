"""``SubstratePublisherPort`` -- Story 46.1 (spec-pyforge-marshal CAP-192,
folded from spec-marshal-token-economy CAP-22): publish/fetch the
substrate artifacts (the structure-graph codegraph index, the
derived-context/planning-graph scribe index) as GitHub Release assets, so
a bare clone can bootstrap them without recomputing from scratch.

A Protocol definition only (AD-11): implemented solely by
``adapters.substrate_release.py::GhSubstrateRelease``, a thin wrapper
around the ``gh release`` CLI -- never a raw HTTP/REST client, matching
``ports/forge.py``'s own established practice for every other GitHub
interaction in this package. GitHub Releases, not same-run Actions
artifacts: a release asset is fetchable from any machine at any later
time, which a workflow-run artifact is not (it is scoped to the run that
produced it and expires).

Both directions degrade the same way as every other adapter in this
package: a failure returns an ``ok=False`` outcome with a human
``reason``, never an exception -- the caller (``core/substrate_bootstrap.py``)
turns that into a named, loud WARN finding and falls back to a local
rebuild; nothing here blocks a run.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class FetchOutcome:
    """What one ``fetch_latest`` invocation produced.

    ``ok`` is true ONLY when a release was found and its assets downloaded
    into ``dest_dir`` -- every other shape (``gh`` unresolved, no such
    release/tag, a download failure) is ``ok=False`` with ``reason``
    naming what happened. ``asset_paths`` lists exactly what landed in
    ``dest_dir``, by filename."""

    ok: bool
    asset_paths: tuple[Path, ...] = ()
    reason: str | None = None
    argv: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class PublishOutcome:
    """What one ``publish`` invocation produced. ``ok=False`` with
    ``reason`` for any ``gh`` failure -- never an exception."""

    ok: bool
    reason: str | None = None
    argv: tuple[str, ...] = field(default_factory=tuple)


class SubstratePublisherPort(Protocol):
    def fetch_latest(self, *, repo: str, tag: str, dest_dir: Path) -> FetchOutcome:
        """Download every asset of the release tagged ``tag`` on ``repo``
        into ``dest_dir``. Never raises."""
        ...

    def publish(self, *, repo: str, tag: str, files: tuple[Path, ...], title: str, notes: str) -> PublishOutcome:
        """Publish ``files`` as the release tagged ``tag`` on ``repo`` --
        creating the release if ``tag`` does not exist yet, or replacing
        its assets (``--clobber``) if it does, so a rolling tag (e.g.
        ``substrate-latest``) stays idempotent and re-entrant across
        nightly runs. Never raises."""
        ...
