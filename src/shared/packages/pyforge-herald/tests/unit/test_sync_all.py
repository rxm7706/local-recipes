"""``sync_all.sync_all`` -- Story 23.6 (``spec-design-sync-loop`` CAP-8,
plus CAP-3's sweep half): enumerate -> pull -> refresh -> derive -> push
-> prove -> publish, composed over hand-written fakes for every injected
seam (no network, no real ``pixi``/``npm``/``git`` subprocess for the
orchestration tests -- ``deck_pipeline.pull_*``/``push_exports`` are the
real functions, exercised over a fake ``DesignTransport``, exactly like
``test_deck_pipeline.py`` exercises them directly).
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

from pyforge.herald import stamps, state
from pyforge.herald import sync_all as sync_all_module
from pyforge.herald.deck_pipeline import (
    PROTOTYPE_ARTIFACT_KEY,
    STANDALONE_BUNDLE_ARTIFACT_KEY,
)
from pyforge.herald.errors import AuthError, HeraldError, TransportUnreachableError
from pyforge.herald.sync_all import (
    DeckSyncReport,
    GitLocalEditDetector,
    PixiDeckDeriver,
    PixiFactsRefresher,
    PixiSitePublisher,
    _run_bounded,
    sync_all,
)
from pyforge.herald.transport.base import FileRead, PlanHandle

_FIXED_NOW = datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)


def _now() -> datetime:
    return _FIXED_NOW


# --- fakes -----------------------------------------------------------------


class FakeSyncTransport:
    """A hand-written ``DesignTransport`` double covering exactly what
    ``pull_*``/``push_exports`` call: ``read_file`` (pull), ``finalize_plan``
    / ``write_files`` / ``fetch_rendered_bytes`` (push+prove), and
    ``list_files`` (``deck_pipeline.status``'s stale-mirror check, for the
    ``--dry-run`` preview only)."""

    def __init__(self, *, read_file_answers=None, plan=None, rendered_bytes=None):
        self.read_file_calls: list[dict] = []
        self.write_files_calls: list[dict] = []
        self.finalize_plan_calls: list[dict] = []
        self.fetch_rendered_bytes_calls: list[dict] = []
        self.list_files_calls: list[dict] = []
        self._read_file_answers = read_file_answers
        self._plan = plan or PlanHandle(plan_token="tok", base_etags={})
        self._rendered_bytes = dict(rendered_bytes or {})

    def read_file(self, **kwargs) -> FileRead:
        self.read_file_calls.append(kwargs)
        answers = self._read_file_answers
        if isinstance(answers, dict):
            return answers[kwargs["path"]]
        if isinstance(answers, list):
            assert answers, "FakeSyncTransport ran out of canned read_file answers"
            return answers.pop(0)
        return answers

    def finalize_plan(self, **kwargs):
        self.finalize_plan_calls.append(kwargs)
        return self._plan

    def write_files(self, **kwargs):
        self.write_files_calls.append(kwargs)
        return {}

    def fetch_rendered_bytes(self, *, project_id: str, path: str) -> bytes:
        self.fetch_rendered_bytes_calls.append({"project_id": project_id, "path": path})
        return self._rendered_bytes.get(path, b"")

    def list_files(self, **kwargs):
        self.list_files_calls.append(kwargs)
        return []

    def get_design_prompt(self, **kwargs):
        raise NotImplementedError("sync_all never calls get_design_prompt")

    def create_project(self, **kwargs):
        raise NotImplementedError("sync_all never calls create_project")

    def create_support_js(self, **kwargs):
        raise NotImplementedError("sync_all never calls create_support_js")

    def copy_files(self, **kwargs):
        raise NotImplementedError("sync_all never calls copy_files")

    def render_preview(self, **kwargs):
        raise NotImplementedError("sync_all never calls render_preview")


class FakeFactsRefresher:
    def __init__(self, *, overrode: int = 0, fails: HeraldError | None = None):
        self.calls: list[tuple[str, Path]] = []
        self._overrode = overrode
        self._fails = fails

    def refresh(self, *, slug: str, repo_root: Path) -> int:
        self.calls.append((slug, repo_root))
        if self._fails is not None:
            raise self._fails
        return self._overrode


class FakeDeriver:
    def __init__(self, *, changed: bool = False, fails: HeraldError | None = None):
        self.calls: list[tuple[str, Path]] = []
        self._changed = changed
        self._fails = fails

    def derive(self, *, slug: str, repo_root: Path) -> bool:
        self.calls.append((slug, repo_root))
        if self._fails is not None:
            raise self._fails
        return self._changed


class FakeSitePublisher:
    def __init__(self, *, fails: HeraldError | None = None):
        self.calls: list[Path] = []
        self._fails = fails

    def publish(self, *, repo_root: Path) -> None:
        self.calls.append(repo_root)
        if self._fails is not None:
            raise self._fails


class FakeEditDetector:
    def __init__(self, *, dirty_paths=()):
        self.calls: list[Path] = []
        self._dirty_paths = set(dirty_paths)

    def is_dirty(self, *, repo_root: Path, path: Path) -> bool:
        self.calls.append(path)
        return path in self._dirty_paths


class FakeProver:
    def __init__(self, *, fails: HeraldError | None = None):
        self.calls: list[Path] = []
        self._fails = fails

    def prove(self, deck_dir: Path) -> None:
        self.calls.append(deck_dir)
        if self._fails is not None:
            raise self._fails


def _seed_state(tmp_path: Path, slug: str, *, project_id="p-1", etags=None) -> None:
    state.write(
        tmp_path / state.DEFAULT_STATE_PATH,
        slug,
        state.DeckState(project_id=project_id, etags=dict(etags or {}), last_pull=None),
    )


def _make_deck_dir(tmp_path: Path, slug: str) -> Path:
    deck_dir = tmp_path / "presentations" / slug
    deck_dir.mkdir(parents=True, exist_ok=True)
    (deck_dir / "README.md").write_text(f"# {slug}\n", encoding="utf-8")
    return deck_dir


def _init_committed_git_repo(tmp_path: Path) -> None:
    """A git repo with one commit -- ``stamps.write_stamp`` (called by
    ``_write_proof``) needs a real ``HEAD`` to name as the proof report's
    tree ref."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init", "--allow-empty"], cwd=tmp_path, check=True)


def _seams(**overrides):
    """Every write-capable seam defaulted to an inert fake, so a test that
    only cares about one behavior does not have to spell out the rest."""
    seams = {
        "facts_refresher": FakeFactsRefresher(),
        "deriver": FakeDeriver(),
        "site_publisher": FakeSitePublisher(),
        "edit_detector": FakeEditDetector(),
        "prover": FakeProver(),
        "now": _now,
    }
    seams.update(overrides)
    return seams


_UNCHANGED_PROTOTYPE = FileRead(path="x", etag="E1", body=None, unchanged=True)


# --- enumerate / skip / unknown-slug ----------------------------------------


def test_sync_all_skips_a_deck_directory_with_no_bridge_state(tmp_path: Path):
    _make_deck_dir(tmp_path, "pyforge-warden")

    report = sync_all(FakeSyncTransport(), slug="pyforge-warden", repo_root=tmp_path, **_seams())

    assert len(report.decks) == 1
    deck = report.decks[0]
    assert deck.skipped_reason is not None
    assert deck.unchanged is False
    assert deck.labels() == ("skipped",)
    assert report.published is False


def test_sync_all_reports_a_seeded_but_never_pulled_deck_distinctly(tmp_path: Path):
    """A freshly-seeded deck with an empty ``etags`` map has nothing to
    compare -- must not be indistinguishable from a genuinely fully-synced
    deck (review fix)."""
    _make_deck_dir(tmp_path, "pyforge-warden")
    _seed_state(tmp_path, "pyforge-warden")  # etags={} -- seeded, nothing tracked

    report = sync_all(FakeSyncTransport(), slug="pyforge-warden", repo_root=tmp_path, **_seams())

    deck = report.decks[0]
    assert deck.skipped_reason is not None
    assert deck.labels() == ("skipped",)


def test_sync_all_raises_for_a_slug_with_no_presentations_directory_at_all(
    tmp_path: Path,
):
    with pytest.raises(HeraldError, match="presentations/nope not found"):
        sync_all(FakeSyncTransport(), slug="nope", repo_root=tmp_path, **_seams())


def test_sync_all_enumerates_every_known_slug_when_no_slug_given(tmp_path: Path):
    _make_deck_dir(tmp_path, "pyforge-warden")
    _make_deck_dir(tmp_path, "pyforge-doctor")
    # A directory with no README.md is not a "known" deck -- must be absent
    # from the report (mirrors `deck_pipeline._known_slugs`'s own rule).
    (tmp_path / "presentations" / "not-a-deck").mkdir(parents=True)

    report = sync_all(FakeSyncTransport(), slug=None, repo_root=tmp_path, **_seams())

    assert {d.slug for d in report.decks} == {"pyforge-warden", "pyforge-doctor"}


# --- pull ------------------------------------------------------------------


def test_sync_all_reports_pulled_when_the_prototype_etag_moved(tmp_path: Path):
    _make_deck_dir(tmp_path, "pyforge-warden")
    _seed_state(tmp_path, "pyforge-warden", etags={PROTOTYPE_ARTIFACT_KEY: "E1"})
    transport = FakeSyncTransport(
        read_file_answers=FileRead(path="x", etag="E2", body="<html>new</html>", unchanged=False)
    )

    report = sync_all(transport, slug="pyforge-warden", repo_root=tmp_path, **_seams())

    deck = report.decks[0]
    assert deck.pulled == (PROTOTYPE_ARTIFACT_KEY,)
    assert deck.unchanged is False
    assert "pulled" in deck.labels()


def test_sync_all_reports_nothing_pulled_when_the_etag_did_not_move(tmp_path: Path):
    _make_deck_dir(tmp_path, "pyforge-warden")
    _seed_state(tmp_path, "pyforge-warden", etags={PROTOTYPE_ARTIFACT_KEY: "E1"})
    transport = FakeSyncTransport(read_file_answers=_UNCHANGED_PROTOTYPE)

    report = sync_all(transport, slug="pyforge-warden", repo_root=tmp_path, **_seams())

    deck = report.decks[0]
    assert deck.pulled == ()
    assert deck.unchanged is True
    assert deck.labels() == ("unchanged",)


# --- proof_dir (Story 24.3, spec-pyforge-herald CAP-50) --------------------


def _proof_report_files(deck_proof_dir: Path) -> list[Path]:
    """``report-*.json``, excluding the ``.stamp.json`` sidecars -- a bare
    ``glob("report-*.json")`` also matches ``report-<ts>.json.stamp.json``
    (its filename still ends in ``.json``)."""
    return sorted(p for p in deck_proof_dir.glob("report-*.json") if not p.name.endswith(".stamp.json"))


def test_sync_all_writes_a_proof_report_and_stamp_when_a_deck_changed(
    tmp_path: Path,
):
    _make_deck_dir(tmp_path, "pyforge-warden")
    _init_committed_git_repo(tmp_path)
    _seed_state(tmp_path, "pyforge-warden", etags={PROTOTYPE_ARTIFACT_KEY: "E1"})
    transport = FakeSyncTransport(
        read_file_answers=FileRead(path="x", etag="E2", body="<html>new</html>", unchanged=False)
    )
    proof_dir = tmp_path / "proof"

    report = sync_all(
        transport,
        slug="pyforge-warden",
        repo_root=tmp_path,
        proof_dir=proof_dir,
        **_seams(),
    )

    deck = report.decks[0]
    report_files = _proof_report_files(proof_dir / "pyforge-warden")
    assert len(report_files) == 1
    payload = json.loads(report_files[0].read_text(encoding="utf-8"))
    assert payload["slug"] == "pyforge-warden"
    assert payload["labels"] == list(deck.labels())
    assert payload["pulled"] == [PROTOTYPE_ARTIFACT_KEY]
    stamp = stamps.read_stamp(report_files[0])
    assert stamp is not None
    assert stamp.etag == "E2"


def test_sync_all_second_proof_run_writes_a_distinctly_named_unchanged_report(
    tmp_path: Path,
):
    """The core AC: a second consecutive proof-run over an already-synced
    deck writes a second, distinctly-named ``unchanged`` report -- the
    first run's report file is left untouched."""
    _make_deck_dir(tmp_path, "pyforge-warden")
    _init_committed_git_repo(tmp_path)
    _seed_state(tmp_path, "pyforge-warden", etags={PROTOTYPE_ARTIFACT_KEY: "E1"})
    transport = FakeSyncTransport(read_file_answers=_UNCHANGED_PROTOTYPE)
    proof_dir = tmp_path / "proof"

    first = sync_all(
        transport,
        slug="pyforge-warden",
        repo_root=tmp_path,
        proof_dir=proof_dir,
        **_seams(),
    )
    first_files = _proof_report_files(proof_dir / "pyforge-warden")
    assert len(first_files) == 1
    first_contents = first_files[0].read_text(encoding="utf-8")
    first_stamp = stamps.read_stamp(first_files[0])
    assert first_stamp is not None

    second = sync_all(
        transport,
        slug="pyforge-warden",
        repo_root=tmp_path,
        proof_dir=proof_dir,
        **_seams(),
    )

    assert first.decks[0].labels() == ("unchanged",)
    assert second.decks[0].labels() == ("unchanged",)
    second_files = _proof_report_files(proof_dir / "pyforge-warden")
    assert len(second_files) == 2
    assert first_files[0].is_file()
    assert first_files[0].read_text(encoding="utf-8") == first_contents
    second_only = [p for p in second_files if p not in first_files]
    assert len(second_only) == 1
    second_payload = json.loads(second_only[0].read_text(encoding="utf-8"))
    assert second_payload["labels"] == ["unchanged"]


def test_sync_all_without_proof_dir_writes_nothing_under_sync_proof(tmp_path: Path):
    """Regression guard: ``proof_dir`` is ``None`` at every call site this
    story did not touch -- behavior must be identical to before it."""
    _make_deck_dir(tmp_path, "pyforge-warden")
    _seed_state(tmp_path, "pyforge-warden", etags={PROTOTYPE_ARTIFACT_KEY: "E1"})
    transport = FakeSyncTransport(read_file_answers=_UNCHANGED_PROTOTYPE)

    sync_all(transport, slug="pyforge-warden", repo_root=tmp_path, **_seams())

    assert not (tmp_path / ".herald" / "sync-proof").exists()


def test_sync_all_dry_run_with_proof_dir_still_writes_a_proof_report(tmp_path: Path):
    """The gate/write logic does not special-case ``dry_run`` -- a dry-run
    preview still gets its own proof report."""
    _make_deck_dir(tmp_path, "pyforge-warden")
    _init_committed_git_repo(tmp_path)
    _seed_state(tmp_path, "pyforge-warden", etags={PROTOTYPE_ARTIFACT_KEY: "E1"})
    transport = FakeSyncTransport(read_file_answers=_UNCHANGED_PROTOTYPE)
    proof_dir = tmp_path / "proof"

    report = sync_all(
        transport,
        slug="pyforge-warden",
        repo_root=tmp_path,
        dry_run=True,
        proof_dir=proof_dir,
        **_seams(),
    )

    deck = report.decks[0]
    assert deck.dry_run is True
    assert deck.labels() == ("unchanged",)
    report_files = _proof_report_files(proof_dir / "pyforge-warden")
    assert len(report_files) == 1
    payload = json.loads(report_files[0].read_text(encoding="utf-8"))
    assert payload["dry_run"] is True


def test_sync_all_never_pulls_an_export_tracked_key(tmp_path: Path):
    """``export:*`` keys are push-tracked, never pull-tracked -- pulling one
    would ``read_file`` a Design path that was never a pull artifact at
    all."""
    _make_deck_dir(tmp_path, "pyforge-warden")
    _seed_state(
        tmp_path,
        "pyforge-warden",
        etags={"export:pyforge-warden-infographic-standalone-2026-09-01.html": "h1"},
    )
    transport = FakeSyncTransport()

    sync_all(transport, slug="pyforge-warden", repo_root=tmp_path, **_seams())

    assert transport.read_file_calls == []


def test_sync_all_reports_pulled_for_a_marp_source_key(tmp_path: Path):
    _make_deck_dir(tmp_path, "pyforge-warden")
    _seed_state(tmp_path, "pyforge-warden", etags={"marp:deck": "E1"})
    transport = FakeSyncTransport(
        read_file_answers=FileRead(path="x", etag="E2", body="# new deck source", unchanged=False)
    )

    report = sync_all(transport, slug="pyforge-warden", repo_root=tmp_path, **_seams())

    deck = report.decks[0]
    assert deck.pulled == ("marp:deck",)
    assert "pulled" in deck.labels()
    written = tmp_path / "presentations" / "pyforge-warden" / "src" / "marp" / "pyforge-warden-deck-2026-09-18.md"
    assert written.read_text(encoding="utf-8") == "# new deck source"


# --- overwrote-local ---------------------------------------------------------


def test_sync_all_reports_overwrote_local_when_a_dirty_pulled_file_is_clobbered(
    tmp_path: Path,
):
    deck_dir = _make_deck_dir(tmp_path, "pyforge-warden")
    (deck_dir / "project").mkdir()
    prototype_path = deck_dir / "project" / "PyForge Warden.dc.html"
    prototype_path.write_text("<html>local edit</html>", encoding="utf-8")
    _seed_state(tmp_path, "pyforge-warden", etags={PROTOTYPE_ARTIFACT_KEY: "E1"})
    transport = FakeSyncTransport(
        read_file_answers=FileRead(path="x", etag="E2", body="<html>design edit</html>", unchanged=False)
    )

    report = sync_all(
        transport,
        slug="pyforge-warden",
        repo_root=tmp_path,
        **_seams(edit_detector=FakeEditDetector(dirty_paths=(prototype_path,))),
    )

    deck = report.decks[0]
    assert deck.overwrote_local == (PROTOTYPE_ARTIFACT_KEY,)
    assert "overwrote-local" in deck.labels()


def test_sync_all_does_not_report_overwrote_local_when_the_pull_was_unchanged(
    tmp_path: Path,
):
    deck_dir = _make_deck_dir(tmp_path, "pyforge-warden")
    (deck_dir / "project").mkdir()
    prototype_path = deck_dir / "project" / "PyForge Warden.dc.html"
    prototype_path.write_text("<html>local edit</html>", encoding="utf-8")
    _seed_state(tmp_path, "pyforge-warden", etags={PROTOTYPE_ARTIFACT_KEY: "E1"})
    transport = FakeSyncTransport(read_file_answers=_UNCHANGED_PROTOTYPE)

    report = sync_all(
        transport,
        slug="pyforge-warden",
        repo_root=tmp_path,
        **_seams(edit_detector=FakeEditDetector(dirty_paths=(prototype_path,))),
    )

    assert report.decks[0].overwrote_local == ()


def test_sync_all_does_not_report_overwrote_local_for_a_clean_local_file(
    tmp_path: Path,
):
    deck_dir = _make_deck_dir(tmp_path, "pyforge-warden")
    (deck_dir / "project").mkdir()
    (deck_dir / "project" / "PyForge Warden.dc.html").write_text("x", encoding="utf-8")
    _seed_state(tmp_path, "pyforge-warden", etags={PROTOTYPE_ARTIFACT_KEY: "E1"})
    transport = FakeSyncTransport(
        read_file_answers=FileRead(path="x", etag="E2", body="<html>design edit</html>", unchanged=False)
    )

    report = sync_all(
        transport,
        slug="pyforge-warden",
        repo_root=tmp_path,
        **_seams(edit_detector=FakeEditDetector(dirty_paths=())),
    )

    assert report.decks[0].overwrote_local == ()


def test_sync_all_reports_overwrote_local_for_a_dirty_standalone_bundle_file(
    tmp_path: Path,
):
    deck_dir = _make_deck_dir(tmp_path, "pyforge-warden")
    (deck_dir / "src" / "marp").mkdir(parents=True)
    bundle_path = deck_dir / "src" / "marp" / "pyforge-warden-infographic-standalone-2026-09-18.html"
    bundle_path.write_text("<html>local edit</html>", encoding="utf-8")
    _seed_state(tmp_path, "pyforge-warden", etags={STANDALONE_BUNDLE_ARTIFACT_KEY: "E1"})
    filename = "pyforge-warden-infographic-standalone-2026-09-18.html"
    transport = FakeSyncTransport(
        read_file_answers=FileRead(path="x", etag="E2", body="<html>design edit</html>", unchanged=False),
        # The pulled bundle lands at the same path push's own export
        # discovery matches -- prove=True always runs, so its read-back
        # must agree or push_exports raises ReadBackMismatchError instead
        # of letting this test isolate the overwrote-local behavior alone.
        rendered_bytes={filename: b"<html>design edit</html>"},
    )

    report = sync_all(
        transport,
        slug="pyforge-warden",
        repo_root=tmp_path,
        **_seams(edit_detector=FakeEditDetector(dirty_paths=(bundle_path,))),
    )

    deck = report.decks[0]
    assert deck.error is None
    assert deck.overwrote_local == (STANDALONE_BUNDLE_ARTIFACT_KEY,)
    assert "overwrote-local" in deck.labels()


def test_sync_all_uses_one_frozen_now_for_the_whole_deck_sync(tmp_path: Path):
    """Review fix: ``now()`` is resolved exactly once per deck and reused
    for both the dirty-check path (``date_str``) and the actual pull/push
    write path -- a live ``now`` that ticks across a UTC-midnight boundary
    between calls must not make the two disagree on which dated file is in
    play."""
    deck_dir = _make_deck_dir(tmp_path, "pyforge-warden")
    (deck_dir / "src" / "marp").mkdir(parents=True)
    _seed_state(tmp_path, "pyforge-warden", etags={STANDALONE_BUNDLE_ARTIFACT_KEY: "E1"})
    filename = "pyforge-warden-infographic-standalone-2026-09-18.html"
    transport = FakeSyncTransport(
        read_file_answers=FileRead(path="x", etag="E2", body="<html>new</html>", unchanged=False),
        rendered_bytes={filename: b"<html>new</html>"},
    )
    ticking_values = iter(
        [
            datetime(2026, 9, 18, 23, 59, 59, tzinfo=timezone.utc),
            datetime(2026, 9, 19, 0, 0, 1, tzinfo=timezone.utc),
        ]
    )

    report = sync_all(
        transport,
        slug="pyforge-warden",
        repo_root=tmp_path,
        **_seams(now=lambda: next(ticking_values)),
    )

    deck = report.decks[0]
    assert deck.error is None
    assert deck.pulled == (STANDALONE_BUNDLE_ARTIFACT_KEY,)
    assert (deck_dir / "src" / "marp" / filename).is_file()
    # The second, later-dated `now()` value was never consumed -- proof
    # `now` was resolved exactly once for this deck's whole sync pass.
    assert list(ticking_values) == [datetime(2026, 9, 19, 0, 0, 1, tzinfo=timezone.utc)]


# --- refresh / derive / push composition + ordering -------------------------


def test_sync_all_calls_refresh_then_derive_after_pull_and_before_push(
    tmp_path: Path,
):
    _make_deck_dir(tmp_path, "pyforge-warden")
    _seed_state(tmp_path, "pyforge-warden", etags={PROTOTYPE_ARTIFACT_KEY: "E1"})
    order: list[str] = []

    class OrderedRefresher(FakeFactsRefresher):
        def refresh(self, *, slug, repo_root):
            order.append("refresh")
            return super().refresh(slug=slug, repo_root=repo_root)

    class OrderedDeriver(FakeDeriver):
        def derive(self, *, slug, repo_root):
            order.append("derive")
            return super().derive(slug=slug, repo_root=repo_root)

    class OrderedTransport(FakeSyncTransport):
        def write_files(self, **kwargs):
            order.append("push")
            return super().write_files(**kwargs)

    deck_dir = tmp_path / "presentations" / "pyforge-warden"
    (deck_dir / "src" / "marp").mkdir(parents=True)
    filename = "pyforge-warden-infographic-standalone-2026-09-18.html"
    (deck_dir / "src" / "marp" / filename).write_text("<html>v1</html>", encoding="utf-8")

    sync_all(
        OrderedTransport(
            read_file_answers=_UNCHANGED_PROTOTYPE,
            rendered_bytes={filename: b"<html>v1</html>"},
        ),
        slug="pyforge-warden",
        repo_root=tmp_path,
        **_seams(facts_refresher=OrderedRefresher(), deriver=OrderedDeriver()),
    )

    assert order == ["refresh", "derive", "push"]


def test_sync_all_reports_overrode_count_from_the_refresher(tmp_path: Path):
    _make_deck_dir(tmp_path, "pyforge-warden")
    _seed_state(tmp_path, "pyforge-warden", etags={PROTOTYPE_ARTIFACT_KEY: "E1"})

    report = sync_all(
        FakeSyncTransport(read_file_answers=_UNCHANGED_PROTOTYPE),
        slug="pyforge-warden",
        repo_root=tmp_path,
        **_seams(facts_refresher=FakeFactsRefresher(overrode=3)),
    )

    deck = report.decks[0]
    assert deck.overrode == 3
    assert "overrode" in deck.labels()
    assert deck.unchanged is False


def test_sync_all_reports_derived_from_the_deriver(tmp_path: Path):
    _make_deck_dir(tmp_path, "pyforge-warden")
    _seed_state(tmp_path, "pyforge-warden", etags={PROTOTYPE_ARTIFACT_KEY: "E1"})

    report = sync_all(
        FakeSyncTransport(read_file_answers=_UNCHANGED_PROTOTYPE),
        slug="pyforge-warden",
        repo_root=tmp_path,
        **_seams(deriver=FakeDeriver(changed=True)),
    )

    deck = report.decks[0]
    assert deck.derived is True
    assert "derived" in deck.labels()
    assert deck.unchanged is False


def test_sync_all_pushes_a_new_export_file_and_reports_it(tmp_path: Path):
    _make_deck_dir(tmp_path, "pyforge-warden")
    _seed_state(tmp_path, "pyforge-warden", etags={PROTOTYPE_ARTIFACT_KEY: "E1"})
    deck_dir = tmp_path / "presentations" / "pyforge-warden"
    (deck_dir / "src" / "marp").mkdir(parents=True)
    filename = "pyforge-warden-infographic-standalone-2026-09-18.html"
    (deck_dir / "src" / "marp" / filename).write_text("<html>v1</html>", encoding="utf-8")

    report = sync_all(
        FakeSyncTransport(
            read_file_answers=_UNCHANGED_PROTOTYPE,
            rendered_bytes={filename: b"<html>v1</html>"},
        ),
        slug="pyforge-warden",
        repo_root=tmp_path,
        **_seams(),
    )

    deck = report.decks[0]
    assert deck.pushed == (filename,)
    assert "pushed" in deck.labels()


def test_sync_all_prove_proves_a_pushed_file(tmp_path: Path):
    _make_deck_dir(tmp_path, "pyforge-warden")
    _seed_state(tmp_path, "pyforge-warden", etags={PROTOTYPE_ARTIFACT_KEY: "E1"})
    deck_dir = tmp_path / "presentations" / "pyforge-warden"
    (deck_dir / "src" / "marp").mkdir(parents=True)
    filename = "pyforge-warden-infographic-standalone-2026-09-18.html"
    (deck_dir / "src" / "marp" / filename).write_text("<html>v1</html>", encoding="utf-8")
    transport = FakeSyncTransport(
        read_file_answers=_UNCHANGED_PROTOTYPE,
        rendered_bytes={filename: b"<html>v1</html>"},
    )

    report = sync_all(transport, slug="pyforge-warden", repo_root=tmp_path, **_seams())

    deck = report.decks[0]
    assert deck.proven == (filename,)
    assert "proven" in deck.labels()


# --- publish -----------------------------------------------------------------


def test_sync_all_publishes_once_when_a_deck_changed_and_marks_it_published(
    tmp_path: Path,
):
    _make_deck_dir(tmp_path, "pyforge-warden")
    _seed_state(tmp_path, "pyforge-warden", etags={PROTOTYPE_ARTIFACT_KEY: "E1"})
    publisher = FakeSitePublisher()

    report = sync_all(
        FakeSyncTransport(read_file_answers=_UNCHANGED_PROTOTYPE),
        slug="pyforge-warden",
        repo_root=tmp_path,
        **_seams(deriver=FakeDeriver(changed=True), site_publisher=publisher),
    )

    assert publisher.calls == [tmp_path]
    assert report.published is True
    assert report.decks[0].published is True
    assert "published" in report.decks[0].labels()


def test_sync_all_does_not_publish_when_nothing_changed(tmp_path: Path):
    _make_deck_dir(tmp_path, "pyforge-warden")
    _seed_state(tmp_path, "pyforge-warden", etags={PROTOTYPE_ARTIFACT_KEY: "E1"})
    transport = FakeSyncTransport(read_file_answers=_UNCHANGED_PROTOTYPE)
    publisher = FakeSitePublisher()

    report = sync_all(
        transport,
        slug="pyforge-warden",
        repo_root=tmp_path,
        **_seams(site_publisher=publisher),
    )

    assert publisher.calls == []
    assert report.published is False
    assert report.decks[0].published is False


def test_sync_all_publishes_once_for_multiple_decks(tmp_path: Path):
    _make_deck_dir(tmp_path, "pyforge-warden")
    _make_deck_dir(tmp_path, "pyforge-doctor")
    _seed_state(tmp_path, "pyforge-warden", etags={PROTOTYPE_ARTIFACT_KEY: "E1"})
    _seed_state(tmp_path, "pyforge-doctor", etags={PROTOTYPE_ARTIFACT_KEY: "E1"})
    transport = FakeSyncTransport(read_file_answers=_UNCHANGED_PROTOTYPE)
    publisher = FakeSitePublisher()

    report = sync_all(
        transport,
        slug=None,
        repo_root=tmp_path,
        **_seams(deriver=FakeDeriver(changed=True), site_publisher=publisher),
    )

    assert publisher.calls == [tmp_path]
    by_slug = {d.slug: d for d in report.decks}
    assert by_slug["pyforge-warden"].published is True
    assert by_slug["pyforge-doctor"].published is True  # deriver marks both "derived"


# --- per-deck failure isolation ----------------------------------------------


def test_sync_all_isolates_one_decks_failure_from_the_rest(tmp_path: Path):
    _make_deck_dir(tmp_path, "pyforge-warden")
    _make_deck_dir(tmp_path, "pyforge-doctor")
    _seed_state(tmp_path, "pyforge-warden", etags={PROTOTYPE_ARTIFACT_KEY: "E1"})
    _seed_state(tmp_path, "pyforge-doctor", etags={PROTOTYPE_ARTIFACT_KEY: "E1"})

    class FlakyRefresher(FakeFactsRefresher):
        def refresh(self, *, slug, repo_root):
            if slug == "pyforge-warden":
                raise HeraldError("deck-facts --refresh failed: boom")
            return super().refresh(slug=slug, repo_root=repo_root)

    report = sync_all(
        FakeSyncTransport(read_file_answers=_UNCHANGED_PROTOTYPE),
        slug=None,
        repo_root=tmp_path,
        **_seams(facts_refresher=FlakyRefresher()),
    )

    by_slug = {d.slug: d for d in report.decks}
    assert by_slug["pyforge-warden"].error == "deck-facts --refresh failed: boom"
    assert by_slug["pyforge-warden"].labels() == ("failed",)
    assert by_slug["pyforge-doctor"].error is None
    assert by_slug["pyforge-doctor"].unchanged is True


def test_sync_all_preserves_pulled_facts_when_a_tail_step_fails(tmp_path: Path):
    """Review fix: a refresh/derive/push failure AFTER a real pull must not
    discard the pull facts already gathered (including a real
    overwrote-local warning) -- the deck's own report must still carry
    them alongside the error, not just the bare error."""
    deck_dir = _make_deck_dir(tmp_path, "pyforge-warden")
    (deck_dir / "project").mkdir()
    prototype_path = deck_dir / "project" / "PyForge Warden.dc.html"
    prototype_path.write_text("<html>local edit</html>", encoding="utf-8")
    _seed_state(tmp_path, "pyforge-warden", etags={PROTOTYPE_ARTIFACT_KEY: "E1"})
    transport = FakeSyncTransport(
        read_file_answers=FileRead(path="x", etag="E2", body="<html>design edit</html>", unchanged=False)
    )

    report = sync_all(
        transport,
        slug="pyforge-warden",
        repo_root=tmp_path,
        **_seams(
            edit_detector=FakeEditDetector(dirty_paths=(prototype_path,)),
            facts_refresher=FakeFactsRefresher(fails=HeraldError("deck-facts --refresh failed: boom")),
        ),
    )

    deck = report.decks[0]
    assert deck.pulled == (PROTOTYPE_ARTIFACT_KEY,)
    assert deck.overwrote_local == (PROTOTYPE_ARTIFACT_KEY,)
    assert deck.error == "deck-facts --refresh failed: boom"


def test_sync_all_auth_error_propagates_and_aborts_the_whole_run(tmp_path: Path):
    """Review fix: an ``AuthError`` reaching Design must not be isolated
    per-deck (module docstring) -- it means Design itself is unreachable,
    which halts the whole run rather than being swallowed as one deck's
    ``error``."""

    class UnauthorizedTransport(FakeSyncTransport):
        def read_file(self, **kwargs):
            self.read_file_calls.append(kwargs)
            raise AuthError("/design-login required")

    _make_deck_dir(tmp_path, "pyforge-warden")
    _make_deck_dir(tmp_path, "pyforge-doctor")
    _seed_state(tmp_path, "pyforge-warden", etags={PROTOTYPE_ARTIFACT_KEY: "E1"})
    _seed_state(tmp_path, "pyforge-doctor", etags={PROTOTYPE_ARTIFACT_KEY: "E1"})

    with pytest.raises(AuthError):
        sync_all(UnauthorizedTransport(), slug=None, repo_root=tmp_path, **_seams())


def test_sync_all_publish_failure_still_returns_every_decks_report(tmp_path: Path):
    """Review fix: a publish failure must not discard every already-
    gathered per-deck report."""
    _make_deck_dir(tmp_path, "pyforge-warden")
    _seed_state(tmp_path, "pyforge-warden", etags={PROTOTYPE_ARTIFACT_KEY: "E1"})
    transport = FakeSyncTransport(
        read_file_answers=FileRead(path="x", etag="E2", body="<html>new</html>", unchanged=False)
    )
    publisher = FakeSitePublisher(fails=HeraldError("site publish failed: template error"))

    report = sync_all(
        transport,
        slug="pyforge-warden",
        repo_root=tmp_path,
        **_seams(site_publisher=publisher),
    )

    assert len(report.decks) == 1
    assert report.decks[0].pulled == (PROTOTYPE_ARTIFACT_KEY,)
    assert report.published is False
    assert report.publish_error == "site publish failed: template error"


# --- --dry-run ---------------------------------------------------------------


def test_sync_all_dry_run_never_calls_any_write_capable_seam(tmp_path: Path):
    _make_deck_dir(tmp_path, "pyforge-warden")
    _seed_state(tmp_path, "pyforge-warden", etags={PROTOTYPE_ARTIFACT_KEY: "E1"})
    transport = FakeSyncTransport(read_file_answers=FileRead(path="x", etag="E2", body="new", unchanged=False))
    refresher = FakeFactsRefresher()
    deriver = FakeDeriver()
    publisher = FakeSitePublisher()

    report = sync_all(
        transport,
        slug="pyforge-warden",
        repo_root=tmp_path,
        dry_run=True,
        **_seams(facts_refresher=refresher, deriver=deriver, site_publisher=publisher),
    )

    assert refresher.calls == []
    assert deriver.calls == []
    assert publisher.calls == []
    assert transport.write_files_calls == []
    deck = report.decks[0]
    assert deck.dry_run is True
    assert deck.would_sync is True
    assert deck.unchanged is False
    assert deck.labels() == ("would-sync",)


def test_sync_all_dry_run_reports_unchanged_when_the_etag_did_not_move(tmp_path: Path):
    _make_deck_dir(tmp_path, "pyforge-warden")
    _seed_state(tmp_path, "pyforge-warden", etags={PROTOTYPE_ARTIFACT_KEY: "E1"})
    transport = FakeSyncTransport(read_file_answers=_UNCHANGED_PROTOTYPE)

    report = sync_all(transport, slug="pyforge-warden", repo_root=tmp_path, dry_run=True, **_seams())

    deck = report.decks[0]
    assert deck.would_sync is False
    assert deck.unchanged is True
    assert deck.labels() == ("unchanged",)


def test_sync_all_dry_run_skips_export_tracked_keys(tmp_path: Path):
    """Review fix: an ``export:*`` key is push-tracked, never pull-tracked,
    and has no remote path to compare -- ``--dry-run`` must not attempt one
    (it used to delegate to ``deck_pipeline.status``, which raised for
    exactly this key and reported ``failed`` instead of ``unchanged``)."""
    _make_deck_dir(tmp_path, "pyforge-warden")
    _seed_state(
        tmp_path,
        "pyforge-warden",
        etags={
            PROTOTYPE_ARTIFACT_KEY: "E1",
            "export:pyforge-warden-infographic-standalone-2026-09-01.html": "h1",
        },
    )
    transport = FakeSyncTransport(read_file_answers=_UNCHANGED_PROTOTYPE)

    report = sync_all(transport, slug="pyforge-warden", repo_root=tmp_path, dry_run=True, **_seams())

    deck = report.decks[0]
    assert deck.error is None
    assert deck.would_sync is False
    assert len(transport.read_file_calls) == 1
    assert transport.read_file_calls[0]["path"] == "PyForge Warden.dc.html"


def test_sync_all_dry_run_reports_a_conflict_as_failed_not_would_sync(tmp_path: Path):
    """Review fix: a transport conflict (Design unreachable, or the tracked
    file gone) is not a confirmed pending change -- must not be folded
    into ``would_sync``, and must not be reported ``unchanged`` either."""

    class ConflictTransport(FakeSyncTransport):
        def read_file(self, **kwargs):
            self.read_file_calls.append(kwargs)
            raise TransportUnreachableError("could not reach Design")

    _make_deck_dir(tmp_path, "pyforge-warden")
    _seed_state(tmp_path, "pyforge-warden", etags={PROTOTYPE_ARTIFACT_KEY: "E1"})

    report = sync_all(
        ConflictTransport(),
        slug="pyforge-warden",
        repo_root=tmp_path,
        dry_run=True,
        **_seams(),
    )

    deck = report.decks[0]
    assert deck.would_sync is False
    assert deck.unchanged is False
    assert deck.error is not None
    assert deck.labels() == ("failed",)


def test_sync_all_dry_run_still_reports_an_unseeded_deck_as_skipped(tmp_path: Path):
    _make_deck_dir(tmp_path, "pyforge-warden")

    report = sync_all(
        FakeSyncTransport(),
        slug="pyforge-warden",
        repo_root=tmp_path,
        dry_run=True,
        **_seams(),
    )

    assert report.decks[0].skipped_reason is not None


# --- idempotent second run ----------------------------------------------------


def test_sync_all_second_run_reports_unchanged_with_zero_write_calls(tmp_path: Path):
    """The core AC: once every tracked etag is already current, nothing new
    to refresh/derive/push exists, a second run is a pure no-op report."""
    _make_deck_dir(tmp_path, "pyforge-warden")
    _seed_state(tmp_path, "pyforge-warden", etags={PROTOTYPE_ARTIFACT_KEY: "E1"})
    transport = FakeSyncTransport(read_file_answers=_UNCHANGED_PROTOTYPE)
    refresher = FakeFactsRefresher(overrode=0)
    deriver = FakeDeriver(changed=False)
    publisher = FakeSitePublisher()

    report = sync_all(
        transport,
        slug="pyforge-warden",
        repo_root=tmp_path,
        **_seams(facts_refresher=refresher, deriver=deriver, site_publisher=publisher),
    )

    deck = report.decks[0]
    assert deck.unchanged is True
    assert deck.labels() == ("unchanged",)
    assert transport.write_files_calls == []
    assert publisher.calls == []


# --- labels() vocabulary -------------------------------------------------------


def test_deck_sync_report_labels_combine_additively():
    report = DeckSyncReport(
        slug="pyforge-warden",
        pulled=("prototype",),
        overwrote_local=("prototype",),
        overrode=1,
        derived=True,
        pushed=("a.html",),
        proven=("a.html",),
        published=True,
    )
    assert report.labels() == (
        "pulled",
        "overwrote-local",
        "overrode",
        "derived",
        "pushed",
        "proven",
        "published",
    )


def test_deck_sync_report_skipped_label_takes_priority_over_error():
    """Not a reachable combination in practice (``_sync_one_deck`` returns
    ``skipped_reason`` before it could ever also set ``.error``) -- pins
    ``labels()``'s own declared precedence for the hypothetical case."""
    report = DeckSyncReport(slug="x", skipped_reason="not seeded", error="boom")
    assert report.labels() == ("skipped",)


# --- _run_bounded (shared subprocess wrapper) ---------------------------------


def test_run_bounded_raises_on_nonzero_exit_with_a_tail(tmp_path: Path):
    with pytest.raises(HeraldError, match="exited 1"):
        _run_bounded(
            ["python", "-c", "import sys; print('boom', file=sys.stderr); sys.exit(1)"],
            cwd=tmp_path,
            timeout=30,
            what="test step",
        )


def test_run_bounded_raises_on_missing_executable(tmp_path: Path):
    with pytest.raises(HeraldError, match="could not run"):
        _run_bounded(
            ["definitely-not-a-real-binary-xyz123"],
            cwd=tmp_path,
            timeout=30,
            what="test step",
        )


def test_run_bounded_raises_on_timeout(tmp_path: Path):
    with pytest.raises(HeraldError, match="exceeded"):
        _run_bounded(
            ["python", "-c", "import time; time.sleep(5)"],
            cwd=tmp_path,
            timeout=0.05,
            what="test step",
        )


def test_run_bounded_returns_the_completed_process_on_success(tmp_path: Path):
    completed = _run_bounded(["python", "-c", "print('ok')"], cwd=tmp_path, timeout=30, what="test step")
    assert completed.stdout.strip() == "ok"


# --- real seam: GitLocalEditDetector (real git, mirrors SubprocessGitCommitter's
# own directly-tested convention) -----------------------------------------------


def _init_git_repo(repo_root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=repo_root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_root, check=True)


def test_git_local_edit_detector_reports_false_for_a_committed_clean_file(
    tmp_path: Path,
):
    _init_git_repo(tmp_path)
    path = tmp_path / "file.txt"
    path.write_text("v1", encoding="utf-8")
    subprocess.run(["git", "add", "file.txt"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "initial"], cwd=tmp_path, check=True)

    assert GitLocalEditDetector().is_dirty(repo_root=tmp_path, path=path) is False


def test_git_local_edit_detector_reports_true_for_a_modified_tracked_file(
    tmp_path: Path,
):
    _init_git_repo(tmp_path)
    path = tmp_path / "file.txt"
    path.write_text("v1", encoding="utf-8")
    subprocess.run(["git", "add", "file.txt"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "initial"], cwd=tmp_path, check=True)
    path.write_text("v2 -- uncommitted", encoding="utf-8")

    assert GitLocalEditDetector().is_dirty(repo_root=tmp_path, path=path) is True


def test_git_local_edit_detector_reports_true_for_an_untracked_file(tmp_path: Path):
    _init_git_repo(tmp_path)
    path = tmp_path / "new.txt"
    path.write_text("never committed", encoding="utf-8")

    assert GitLocalEditDetector().is_dirty(repo_root=tmp_path, path=path) is True


# --- real seam logic: PixiFactsRefresher / PixiDeckDeriver / PixiSitePublisher
# (subprocess.run monkeypatched -- these parse real subprocess output shapes,
# never invoke a real pixi/npm process) -----------------------------------------


class _FakeCompleted:
    def __init__(self, *, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_pixi_facts_refresher_parses_the_refreshed_count(monkeypatch):
    def fake_run(cmd, **kwargs):
        return _FakeCompleted(
            stdout="pyforge-warden: wrote presentations/pyforge-warden/facts.yaml (5 facts)\n"
            "summary   pyforge-warden: 2 refreshed, 1 skipped\n"
        )

    monkeypatch.setattr(sync_all_module.subprocess, "run", fake_run)

    assert PixiFactsRefresher().refresh(slug="pyforge-warden", repo_root=Path(".")) == 2


def test_pixi_facts_refresher_returns_zero_when_the_summary_line_is_absent(
    monkeypatch,
):
    monkeypatch.setattr(sync_all_module.subprocess, "run", lambda cmd, **kw: _FakeCompleted(stdout=""))

    assert PixiFactsRefresher().refresh(slug="pyforge-warden", repo_root=Path(".")) == 0


def test_pixi_facts_refresher_raises_on_a_nonzero_exit(monkeypatch):
    monkeypatch.setattr(
        sync_all_module.subprocess,
        "run",
        lambda cmd, **kw: _FakeCompleted(returncode=1, stderr="boom"),
    )

    with pytest.raises(HeraldError, match="deck-facts --refresh failed"):
        PixiFactsRefresher().refresh(slug="pyforge-warden", repo_root=Path("."))


class _NoopExporter:
    """A ``DeckExporter`` double that touches nothing -- injected via
    ``PixiDeckDeriver(exporter_factory=...)`` so these tests never reach
    ``select_exporter``'s own real ``PixiDeckExporter``/``PptxTemplateExporter``,
    which would shell a REAL ``pixi``/subprocess call in ``deck_pipeline``'s
    own module namespace (a separate ``subprocess`` binding this file's
    ``sync_all_module.subprocess`` monkeypatch cannot reach)."""

    def export(self, *, slug: str, repo_root: Path) -> None:
        return None


def test_pixi_deck_deriver_skips_deck_trio_when_no_poster_is_present(monkeypatch, tmp_path: Path):
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return _FakeCompleted(stdout="")

    monkeypatch.setattr(sync_all_module.subprocess, "run", fake_run)

    changed = PixiDeckDeriver(exporter_factory=lambda slug, repo_root: _NoopExporter()).derive(
        slug="pyforge-warden", repo_root=tmp_path
    )

    assert changed is False
    assert all("deck-trio" not in c for c in calls)


def test_pixi_deck_deriver_calls_deck_trio_when_a_poster_is_present(monkeypatch, tmp_path: Path):
    project_dir = tmp_path / "presentations" / "pyforge-warden" / "project"
    project_dir.mkdir(parents=True)
    (project_dir / "PyForge Warden Infographic standalone.html").write_text("x", encoding="utf-8")
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return _FakeCompleted(stdout="pyforge-warden: wrote project/foo.dc.html\n")

    monkeypatch.setattr(sync_all_module.subprocess, "run", fake_run)

    changed = PixiDeckDeriver(exporter_factory=lambda slug, repo_root: _NoopExporter()).derive(
        slug="pyforge-warden", repo_root=tmp_path
    )

    assert changed is True
    assert any("deck-trio" in c for c in calls)


def test_pixi_deck_deriver_detects_a_changed_export_fingerprint(tmp_path: Path):
    marp_dir = tmp_path / "presentations" / "pyforge-warden" / "src" / "marp"
    marp_dir.mkdir(parents=True)
    export_path = marp_dir / "pyforge-warden-infographic-standalone-2026-09-18.html"
    export_path.write_text("<html>v1</html>", encoding="utf-8")

    class _RewritingExporter:
        def export(self, *, slug: str, repo_root: Path) -> None:
            # Simulate `deck-export` rewriting the export file.
            export_path.write_text("<html>v2</html>", encoding="utf-8")

    changed = PixiDeckDeriver(exporter_factory=lambda slug, repo_root: _RewritingExporter()).derive(
        slug="pyforge-warden", repo_root=tmp_path
    )

    assert changed is True


def test_pixi_site_publisher_raises_on_a_nonzero_exit(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        sync_all_module.subprocess,
        "run",
        lambda cmd, **kw: _FakeCompleted(returncode=1, stderr="template error"),
    )

    with pytest.raises(HeraldError, match="site publish failed"):
        PixiSitePublisher().publish(repo_root=tmp_path)


def test_pixi_site_publisher_succeeds_silently(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(sync_all_module.subprocess, "run", lambda cmd, **kw: _FakeCompleted())

    PixiSitePublisher().publish(repo_root=tmp_path)  # must not raise
