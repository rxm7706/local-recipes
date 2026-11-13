"""Doctor Story 58.1 (spec-pyforge-doctor:CAP-97) -- the live-tree half of
``test_sources_hygiene.py``.

The two live-repo tests (zero false positives against warden; the five
orphans doctor Story 30.4 cited stay cited by their records -- until
2026-10-24 the second asserted a live true positive) run
``hygiene.gather`` against this repository's own root, so they run in the
station's live-tree half; every fixture test stays in
``test_sources_hygiene.py`` (the package half).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from test_sources_hygiene import _isolate_git_env  # noqa: F401 -- the module's autouse scrub

from pyforge.doctor.hygiene_definitions import HygieneFindingKind
from pyforge.doctor.sources import hygiene

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree


def _require_repo_root() -> Path:
    """This repository's root, resolved when a test runs (never at import time)."""
    root = Path(__file__).resolve().parents[6]
    assert (root / ".claude").is_dir(), f"{root} is not the local-recipes checkout root (no .claude/)"
    return root


# --- Row: zero false positives against warden (live) -----------------------


def test_live_repo_gather_reports_no_finding_naming_warden() -> None:
    repo_root = _require_repo_root()
    findings = hygiene.gather(repo_root)
    assert not any(f.evidence.get("station") == "warden" for f in findings)


# --- Row: the five cited orphans stay cited (live) --------------------------

_PLANNING = "_bmad-output/projects/{station}/planning-artifacts/"

#: The five live orphans doctor Story 30.4 cited (2026-10-24), each with the record that cites it.
#: Each file name is joined from two parts so this test's own text never holds the whole basename
#: (`gather()`'s orphan check greps the repo, this file included). The row reads the citing record
#: itself, because other text (the story spec, its evidence) also names these files and would keep
#: `gather()` quiet after a real citation is lost.
_STORY_30_4_CITED = (
    (
        _PLANNING.format(station="pyforge-herald") + "deckcraft-board-epics-displaced-2026-08-08",
        ".json",
        _PLANNING.format(station="pyforge-marshal") + "deferred-work-ledger.md",
    ),
    (
        _PLANNING.format(station="pyforge-marshal") + "change-history/sprint-change-proposal-2026-08-12",
        ".md",
        _PLANNING.format(station="pyforge-marshal") + "epics.md",
    ),
    (
        _PLANNING.format(station="pyforge-marshal")
        + "change-history/sprint-change-proposal-2026-09-01-drain-self-resolution",
        ".md",
        _PLANNING.format(station="pyforge-marshal") + "epics.md",
    ),
    (
        _PLANNING.format(station="pyforge-steward") + "sprint-change-proposal-2026-08-21",
        ".md",
        _PLANNING.format(station="pyforge-steward") + "epics.md",
    ),
    (
        _PLANNING.format(station="pyforge-steward") + "sprint-change-proposal-2026-08-26-mcp-host-cluster",
        ".md",
        _PLANNING.format(station="pyforge-steward") + "implementation-readiness-report-2026-08-26-mcp-host-cluster.md",
    ),
)


def test_live_repo_the_orphans_story_30_4_cited_stay_cited_by_their_records() -> None:
    """Until 2026-10-24 this row asserted a live true positive outside warden
    (herald's displaced Guildhall epics array, an orphan). Doctor Story 30.4
    cited that file and the other four live orphans from the records they
    belong to; this row guards those five citations, and only those, so an
    orphan added elsewhere stays a warn, not a red doctor suite. Detection on a
    non-warden station stays proven on a fixture:
    ``test_orphan_file_with_no_inbound_references_resolves_true_not_a_warn``
    (station ``pyforge-acme``) and the all-classes fixture above."""
    repo_root = _require_repo_root()
    cited = []
    for stem, ext, citing in _STORY_30_4_CITED:
        relpath = stem + ext
        cited.append(relpath)
        assert (repo_root / relpath).is_file(), f"{relpath} moved -- update this row"
        basename = relpath.rsplit("/", 1)[1]
        assert basename in (repo_root / citing).read_text(encoding="utf-8"), (
            f"{citing} no longer cites {basename} -- restore the citation or update this row"
        )
    findings = hygiene.gather(repo_root)
    reported = {f.evidence.get("path") for f in findings if f.check == HygieneFindingKind.ORPHAN_FILE.value}
    assert reported.isdisjoint(cited)
