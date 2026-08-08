"""``deck_pipeline.status`` -- CAP-3 (Story 3.1): the per-deck etag-based
sync classification, the "some seeded, some not" discovery sweep, and the
read-only guarantee.

Every transport call is against a hand-written ``FakeStatusTransport``
implementing only ``read_file``/``list_files`` -- every other
``DesignTransport`` method raises, so an accidental write-side call fails
the test loudly rather than passing silently (the same technique
``FakePullTransport`` in ``test_deck_pipeline.py`` already uses for
``pull_prototype``).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.herald import state
from pyforge.herald.deck_pipeline import DeckStatus, status
from pyforge.herald.errors import HeraldError, TransportCallError
from pyforge.herald.transport.base import FileRead, ListedFile


class FakeStatusTransport:
    """A hand-written ``DesignTransport`` double exercising only
    ``read_file``/``list_files`` -- every other method raises, since
    ``status`` must never call a write-side transport method (FR-13)."""

    def __init__(self, *, read_answers=None, list_files_answer=None):
        self.calls: list[tuple[str, dict]] = []
        # path -> FileRead | Exception | list of either, consumed per call.
        self._read_answers: dict = dict(read_answers or {})
        self._list_files_answer = list(list_files_answer or [])

    def read_file(self, **kwargs) -> FileRead:
        self.calls.append(("read_file", kwargs))
        path = kwargs["path"]
        answer = self._read_answers.get(path)
        if isinstance(answer, list):
            assert answer, f"FakeStatusTransport ran out of answers for {path!r}"
            answer = answer.pop(0)
        if isinstance(answer, Exception):
            raise answer
        if answer is None:
            raise AssertionError(
                f"FakeStatusTransport has no canned answer for {path!r}"
            )
        return answer

    def list_files(self, **kwargs) -> list[ListedFile]:
        self.calls.append(("list_files", kwargs))
        return self._list_files_answer

    def get_design_prompt(self, **kwargs):
        raise NotImplementedError("status never calls get_design_prompt")

    def create_project(self, **kwargs):
        raise NotImplementedError("status never calls create_project")

    def finalize_plan(self, **kwargs):
        raise NotImplementedError("status never calls finalize_plan")

    def create_support_js(self, **kwargs):
        raise NotImplementedError("status never calls create_support_js")

    def copy_files(self, **kwargs):
        raise NotImplementedError("status never calls copy_files")

    def write_files(self, **kwargs):
        raise NotImplementedError("status never calls write_files")

    def render_preview(self, **kwargs):
        raise NotImplementedError("status never calls render_preview")

    def names(self) -> list[str]:
        return [name for name, _kwargs in self.calls]


def _make_deck_dir(tmp_path: Path, slug: str) -> Path:
    deck_dir = tmp_path / "presentations" / slug
    deck_dir.mkdir(parents=True)
    (deck_dir / "README.md").write_text(f"# {slug}\n", encoding="utf-8")
    return deck_dir


def _seed_state(
    tmp_path: Path, slug: str, *, project_id="p-1", etags=None, last_pull=None
) -> None:
    state.write(
        tmp_path / state.DEFAULT_STATE_PATH,
        slug,
        state.DeckState(
            project_id=project_id, etags=dict(etags or {}), last_pull=last_pull
        ),
    )


# --- Story 3.1: discovery + sync classification ------------------------------


def test_status_no_slug_reports_every_known_deck_linked_and_unlinked(tmp_path: Path):
    _make_deck_dir(tmp_path, "pyforge-doctor")  # never seeded
    _make_deck_dir(tmp_path, "pyforge-warden")
    _seed_state(
        tmp_path,
        "pyforge-warden",
        etags={"prototype": "E1"},
        last_pull="2026-08-01T00:00:00+00:00",
    )
    transport = FakeStatusTransport(
        read_answers={
            "PyForge Warden.dc.html": FileRead(
                path="x", etag="E1", body=None, unchanged=True
            )
        }
    )

    results = status(transport, repo_root=tmp_path)

    by_slug = {r.slug: r for r in results}
    assert set(by_slug) == {"pyforge-doctor", "pyforge-warden"}
    assert by_slug["pyforge-doctor"] == DeckStatus(
        slug="pyforge-doctor",
        linked=False,
        project_id=None,
        sync=None,
        last_pull=None,
    )
    assert by_slug["pyforge-warden"] == DeckStatus(
        slug="pyforge-warden",
        linked=True,
        project_id="p-1",
        sync="unchanged",
        last_pull="2026-08-01T00:00:00+00:00",
    )


def test_status_with_a_slug_reports_only_that_deck(tmp_path: Path):
    _make_deck_dir(tmp_path, "pyforge-doctor")
    _make_deck_dir(tmp_path, "pyforge-warden")
    _seed_state(tmp_path, "pyforge-warden", etags={"prototype": "E1"})
    transport = FakeStatusTransport(
        read_answers={
            "PyForge Warden.dc.html": FileRead(
                path="x", etag="E1", body=None, unchanged=True
            )
        }
    )

    results = status(transport, slug="pyforge-warden", repo_root=tmp_path)

    assert [r.slug for r in results] == ["pyforge-warden"]


def test_status_an_unknown_slug_returns_a_single_unlinked_result_no_error(
    tmp_path: Path,
):
    transport = FakeStatusTransport()
    results = status(transport, slug="pyforge-nope", repo_root=tmp_path)
    assert results == [
        DeckStatus(
            slug="pyforge-nope",
            linked=False,
            project_id=None,
            sync=None,
            last_pull=None,
        )
    ]
    assert transport.calls == []


def test_status_classifies_changed_when_an_etag_no_longer_matches(tmp_path: Path):
    _seed_state(tmp_path, "pyforge-warden", etags={"prototype": "E1"})
    transport = FakeStatusTransport(
        read_answers={
            "PyForge Warden.dc.html": FileRead(
                path="x", etag="E2", body="<html/>", unchanged=False
            )
        }
    )
    [result] = status(transport, slug="pyforge-warden", repo_root=tmp_path)
    assert result.sync == "changed"


def test_status_classifies_unchanged_when_never_pulled_yet(tmp_path: Path):
    """A seeded deck with no tracked artifacts yet (``etags == {}``) has
    nothing to compare -- reports "unchanged" rather than "changed" or
    raising, and makes no ``read_file`` call at all."""
    _seed_state(tmp_path, "pyforge-warden", etags={})
    transport = FakeStatusTransport()
    [result] = status(transport, slug="pyforge-warden", repo_root=tmp_path)
    assert result.sync == "unchanged"
    assert transport.calls == []


def test_status_conflict_takes_precedence_over_changed(tmp_path: Path):
    """A failed comparison on one tracked artifact must not be masked by a
    clean "changed" answer on another -- an operator cannot safely decide
    whether to pull without first resolving the failed comparison."""
    _seed_state(
        tmp_path,
        "pyforge-warden",
        etags={"prototype": "E1", "marp:deck": "M1"},
    )
    transport = FakeStatusTransport(
        read_answers={
            "PyForge Warden.dc.html": FileRead(
                path="x", etag="E2", body="<html/>", unchanged=False
            ),
            "warden-deck.md": TransportCallError("read file: file not found"),
        }
    )
    [result] = status(transport, slug="pyforge-warden", repo_root=tmp_path)
    assert result.sync == "conflict"


def test_status_reports_conflict_when_the_tracked_file_is_gone_server_side(
    tmp_path: Path,
):
    _seed_state(tmp_path, "pyforge-warden", etags={"prototype": "E1"})
    transport = FakeStatusTransport(
        read_answers={
            "PyForge Warden.dc.html": TransportCallError("read file: file not found")
        }
    )
    [result] = status(transport, slug="pyforge-warden", repo_root=tmp_path)
    assert result.sync == "conflict"


def test_status_raises_for_an_unrecognized_tracked_artifact_key(tmp_path: Path):
    """A hand-edited or future-schema state file naming an artifact key this
    version does not recognize is a structural failure (AD-6), not a
    silent skip."""
    _seed_state(tmp_path, "pyforge-warden", etags={"bogus-key": "E1"})
    transport = FakeStatusTransport()
    with pytest.raises(HeraldError, match="bogus-key"):
        status(transport, slug="pyforge-warden", repo_root=tmp_path)


def test_status_uses_the_short_name_marp_path_and_persona_standalone_path(
    tmp_path: Path,
):
    _seed_state(
        tmp_path,
        "pyforge-warden",
        etags={
            "marp:executive-summary": "M1",
            "standalone-bundle": "S1",
        },
    )
    transport = FakeStatusTransport(
        read_answers={
            "warden-executive-summary.md": FileRead(
                path="x", etag="M1", body=None, unchanged=True
            ),
            "Warden Infographic standalone.html": FileRead(
                path="x", etag="S1", body=None, unchanged=True
            ),
        }
    )
    [result] = status(transport, slug="pyforge-warden", repo_root=tmp_path)
    assert result.sync == "unchanged"
    read_paths = {
        kwargs["path"] for name, kwargs in transport.calls if name == "read_file"
    }
    assert read_paths == {
        "warden-executive-summary.md",
        "Warden Infographic standalone.html",
    }


# --- Story 3.1: zero-write guarantee (FR-13, NFR-08) -------------------------


def test_status_never_writes_a_file_on_either_surface(tmp_path: Path):
    """Asserted two ways: (1) ``FakeStatusTransport``'s every write-side
    method raises on any call, so an accidental call fails the test loudly;
    (2) ``.herald/bridge-state.json``'s bytes are byte-identical before and
    after, proving ``state.write`` was never called either."""
    _make_deck_dir(tmp_path, "pyforge-doctor")
    _make_deck_dir(tmp_path, "pyforge-warden")
    _seed_state(tmp_path, "pyforge-warden", etags={"prototype": "E1"})
    state_path = tmp_path / state.DEFAULT_STATE_PATH
    before = state_path.read_bytes()
    transport = FakeStatusTransport(
        read_answers={
            "PyForge Warden.dc.html": FileRead(
                path="x", etag="E1", body=None, unchanged=True
            )
        }
    )

    status(transport, repo_root=tmp_path)

    after = state_path.read_bytes()
    assert before == after
    assert set(transport.names()) <= {"read_file"}


def test_status_on_an_entirely_unseeded_repo_creates_no_state_file(tmp_path: Path):
    _make_deck_dir(tmp_path, "pyforge-doctor")
    transport = FakeStatusTransport()
    status(transport, repo_root=tmp_path)
    assert not (tmp_path / ".herald").exists()
