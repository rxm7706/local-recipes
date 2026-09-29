"""``deck_pipeline.status`` -- CAP-3 (Stories 3.1 and 3.2): the per-deck
etag-based sync classification, the "some seeded, some not" discovery
sweep, the read-only guarantee, and the stale-hand-mirror heuristic.

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

from pyforge.herald import registry, state
from pyforge.herald.deck_pipeline import (
    AccountProjectStatus,
    DeckStatus,
    _is_stale_mirror,
    account_status,
    status,
)
from pyforge.herald.errors import HeraldError, TransportCallError
from pyforge.herald.transport.base import FileRead, ListedFile, ProjectSummary


class FakeStatusTransport:
    """A hand-written ``DesignTransport`` double exercising only
    ``read_file``/``list_files``/``list_projects`` -- every other method
    raises, since ``status``/``account_status`` must never call a
    write-side transport method (FR-13)."""

    def __init__(
        self,
        *,
        read_answers=None,
        list_files_answer=None,
        list_files_fails=None,
        list_projects_answer=None,
    ):
        self.calls: list[tuple[str, dict]] = []
        # path -> FileRead | Exception | list of either, consumed per call.
        self._read_answers: dict = dict(read_answers or {})
        self._list_files_answer = list(list_files_answer or [])
        self._list_files_fails = list_files_fails
        self._list_projects_answer = list_projects_answer

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
            raise AssertionError(f"FakeStatusTransport has no canned answer for {path!r}")
        return answer

    def list_files(self, **kwargs) -> list[ListedFile]:
        self.calls.append(("list_files", kwargs))
        if self._list_files_fails is not None:
            raise self._list_files_fails
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

    def list_projects(self):
        self.calls.append(("list_projects", {}))
        if self._list_projects_answer is None:
            raise NotImplementedError("status never calls list_projects")
        return self._list_projects_answer

    def names(self) -> list[str]:
        return [name for name, _kwargs in self.calls]


def _make_deck_dir(tmp_path: Path, slug: str) -> Path:
    deck_dir = tmp_path / "presentations" / slug
    deck_dir.mkdir(parents=True)
    (deck_dir / "README.md").write_text(f"# {slug}\n", encoding="utf-8")
    return deck_dir


def _seed_state(tmp_path: Path, slug: str, *, project_id="p-1", etags=None, last_pull=None) -> None:
    state.write(
        tmp_path / state.DEFAULT_STATE_PATH,
        slug,
        state.DeckState(project_id=project_id, etags=dict(etags or {}), last_pull=last_pull),
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
        read_answers={"PyForge Warden.dc.html": FileRead(path="x", etag="E1", body=None, unchanged=True)}
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
        stale_mirror=False,
    )
    assert by_slug["pyforge-warden"] == DeckStatus(
        slug="pyforge-warden",
        linked=True,
        project_id="p-1",
        sync="unchanged",
        last_pull="2026-08-01T00:00:00+00:00",
        stale_mirror=False,
    )


def test_status_with_a_slug_reports_only_that_deck(tmp_path: Path):
    _make_deck_dir(tmp_path, "pyforge-doctor")
    _make_deck_dir(tmp_path, "pyforge-warden")
    _seed_state(tmp_path, "pyforge-warden", etags={"prototype": "E1"})
    transport = FakeStatusTransport(
        read_answers={"PyForge Warden.dc.html": FileRead(path="x", etag="E1", body=None, unchanged=True)}
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
            stale_mirror=False,
        )
    ]
    assert transport.calls == []


def test_status_classifies_changed_when_an_etag_no_longer_matches(tmp_path: Path):
    _seed_state(tmp_path, "pyforge-warden", etags={"prototype": "E1"})
    transport = FakeStatusTransport(
        read_answers={"PyForge Warden.dc.html": FileRead(path="x", etag="E2", body="<html/>", unchanged=False)}
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
    assert [name for name, _ in transport.calls] == ["list_files"]


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
            "PyForge Warden.dc.html": FileRead(path="x", etag="E2", body="<html/>", unchanged=False),
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
        read_answers={"PyForge Warden.dc.html": TransportCallError("read file: file not found")}
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


def test_status_multi_deck_isolates_one_slugs_malformed_entry(tmp_path: Path):
    """Regression: a single-slug request still raises plainly (the test
    above), but a no-slug multi-deck report must not let ONE bad entry
    abort the whole batch -- the report degrades that one deck to
    `sync="conflict"` and still returns every other deck's real status."""
    _seed_state(tmp_path, "pyforge-good", etags={"prototype": "E1"})
    _seed_state(tmp_path, "pyforge-bad", etags={"bogus-key": "E1"})
    transport = FakeStatusTransport(
        read_answers={"PyForge Good.dc.html": FileRead(path="x", etag="E1", body="<html/>", unchanged=True)}
    )

    results = {r.slug: r for r in status(transport, repo_root=tmp_path)}

    assert results["pyforge-good"].sync == "unchanged"
    assert results["pyforge-bad"].sync == "conflict"


def test_status_list_files_failure_is_reported_as_conflict_not_a_crash(
    tmp_path: Path,
):
    """Regression: the stale-mirror `list_files` call had no exception
    handling, unlike the `read_file` comparison loop three lines above it
    -- a transport failure reaching Design for the stale-mirror check
    crashed the whole status report (and, for a no-slug call, every other
    deck's report too) instead of degrading gracefully like every other
    transport failure in this function."""
    _seed_state(tmp_path, "pyforge-warden", etags={"prototype": "E1"})
    transport = FakeStatusTransport(
        read_answers={"PyForge Warden.dc.html": FileRead(path="x", etag="E1", body="<html/>", unchanged=True)},
        list_files_fails=TransportCallError("list_files: network blip"),
    )

    [result] = status(transport, slug="pyforge-warden", repo_root=tmp_path)

    assert result.sync == "conflict"
    assert result.stale_mirror is False


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
            "warden-executive-summary.md": FileRead(path="x", etag="M1", body=None, unchanged=True),
            "Warden Infographic standalone.html": FileRead(path="x", etag="S1", body=None, unchanged=True),
        }
    )
    [result] = status(transport, slug="pyforge-warden", repo_root=tmp_path)
    assert result.sync == "unchanged"
    read_paths = {kwargs["path"] for name, kwargs in transport.calls if name == "read_file"}
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
        read_answers={"PyForge Warden.dc.html": FileRead(path="x", etag="E1", body=None, unchanged=True)}
    )

    status(transport, repo_root=tmp_path)

    after = state_path.read_bytes()
    assert before == after
    assert set(transport.names()) <= {"read_file", "list_files"}


def test_status_on_an_entirely_unseeded_repo_creates_no_state_file(tmp_path: Path):
    _make_deck_dir(tmp_path, "pyforge-doctor")
    transport = FakeStatusTransport()
    status(transport, repo_root=tmp_path)
    assert not (tmp_path / ".herald").exists()


# --- Story 3.2: stale-hand-mirror detection (FR-12) ---------------------------


def _normal_bridge_project_files() -> list[ListedFile]:
    """A correctly-shaped bridge project: the runtime pair, one prototype,
    three Marp sources, one standalone bundle -- all flat, project-root
    filenames, none nested."""
    return [
        ListedFile(path="support.js", etag="E1"),
        ListedFile(path="deck-stage.js", etag="E2"),
        ListedFile(path="PyForge Warden.dc.html", etag="E3"),
        ListedFile(path="warden-deck.md", etag="E4"),
        ListedFile(path="warden-executive-summary.md", etag="E5"),
        ListedFile(path="warden-infographic.md", etag="E6"),
        ListedFile(path="Warden Infographic standalone.html", etag="E7"),
    ]


def _hand_mirrored_repo_files() -> list[ListedFile]:
    """The cautionary "Local recipes repository connection" fixture
    (``bridge-protocol.md`` § Pilot evidence): dozens of files reproducing
    a repo app-tree's own directory structure."""
    nested = [
        "src/pyforge/atlas/__init__.py",
        "src/pyforge/atlas/cli.py",
        "src/pyforge/atlas/db.py",
        "src/pyforge/atlas/phases/phase_b.py",
        "src/pyforge/atlas/phases/phase_c.py",
        ".claude/skills/conda-forge-expert/SKILL.md",
        "docs/dreams/design-code-bridge.md",
        "docs/specs/presentation-deck.md",
    ]
    flat = ["pixi.toml", "README.md", "CLAUDE.md", "conda-forge.yml", "AGENTS.md"]
    files = [ListedFile(path=p, etag=f"E{i}") for i, p in enumerate(nested + flat)]
    # Pad out well past the file-count threshold with more nested paths --
    # a real hand-mirrored copy of an app tree runs to hundreds of files.
    files += [ListedFile(path=f"src/pyforge/atlas/extra_{i}.py", etag=f"X{i}") for i in range(10)]
    return files


def test_is_stale_mirror_flags_the_hand_mirrored_repo_fixture():
    assert _is_stale_mirror(_hand_mirrored_repo_files()) is True


def test_is_stale_mirror_does_not_flag_a_normal_bridge_project():
    assert _is_stale_mirror(_normal_bridge_project_files()) is False


def test_is_stale_mirror_requires_both_file_count_and_nesting():
    """File count alone (many flat files) must not flag -- a future story
    giving a deck many more tracked Marp sources is still a normal bridge
    project, not a hand mirror."""
    many_flat = [ListedFile(path=f"warden-note-{i}.md", etag=f"E{i}") for i in range(20)]
    assert _is_stale_mirror(many_flat) is False

    few_nested = [
        ListedFile(path="support.js", etag="E1"),
        ListedFile(path="src/one.py", etag="E2"),
        ListedFile(path="src/two.py", etag="E3"),
    ]
    assert _is_stale_mirror(few_nested) is False


def test_status_stale_mirror_true_for_the_hand_mirrored_fixture(tmp_path: Path):
    _seed_state(tmp_path, "pyforge-doctor", etags={})
    transport = FakeStatusTransport(list_files_answer=_hand_mirrored_repo_files())
    [result] = status(transport, slug="pyforge-doctor", repo_root=tmp_path)
    assert result.stale_mirror is True


def test_status_stale_mirror_false_for_a_normal_bridge_project(tmp_path: Path):
    _seed_state(tmp_path, "pyforge-warden", etags={})
    transport = FakeStatusTransport(list_files_answer=_normal_bridge_project_files())
    [result] = status(transport, slug="pyforge-warden", repo_root=tmp_path)
    assert result.stale_mirror is False


def test_status_never_flags_stale_mirror_for_an_unlinked_deck(tmp_path: Path):
    _make_deck_dir(tmp_path, "pyforge-doctor")
    transport = FakeStatusTransport()
    [result] = status(transport, slug="pyforge-doctor", repo_root=tmp_path)
    assert result.linked is False
    assert result.stale_mirror is False
    assert transport.calls == []


# --- Story 23.1: account_status (CAP-1) --------------------------------------


def _register_local_twin(tmp_path: Path, slug: str, project_id: str) -> None:
    deck_dir = _make_deck_dir(tmp_path, slug)
    registry.register(
        deck_dir / "README.md",
        f"PyForge {slug.title()} deck",
        project_id,
        f"https://claude.ai/design/p/{project_id}",
    )


def _write_exclusions(tmp_path: Path, rows: dict[str, str]) -> None:
    presentations_dir = tmp_path / "presentations"
    presentations_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# presentations/",
        "",
        "## Excluded projects (never twinned)",
        "",
        "| Project | Reason |",
        "|---|---|",
        *[f"| {name} | {reason} |" for name, reason in rows.items()],
        "",
    ]
    (presentations_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")


def test_account_status_classifies_a_linked_presentation(tmp_path: Path):
    _register_local_twin(tmp_path, "pyforge-warden", "p-1")
    transport = FakeStatusTransport(
        list_projects_answer=[
            ProjectSummary(
                project_id="p-1",
                name="PyForge Warden deck",
                url="https://claude.ai/design/p/p-1",
            )
        ]
    )

    [result] = account_status(transport, repo_root=tmp_path)

    assert result == AccountProjectStatus(
        project_id="p-1",
        name="PyForge Warden deck",
        url="https://claude.ai/design/p/p-1",
        status="linked",
        slug="pyforge-warden",
        reason=None,
    )


def test_account_status_classifies_an_untwinned_presentation(tmp_path: Path):
    transport = FakeStatusTransport(
        list_projects_answer=[
            ProjectSummary(
                project_id="p-9",
                name="PyForge six-quarter roadmap",
                url="https://claude.ai/design/p/p-9",
            )
        ]
    )

    [result] = account_status(transport, repo_root=tmp_path)

    assert result.status == "untwinned"
    assert result.slug is None
    assert result.reason is None


def test_account_status_classifies_a_known_design_system_as_mirrored(
    tmp_path: Path,
):
    transport = FakeStatusTransport(
        list_projects_answer=[
            ProjectSummary(
                project_id="p-modernist",
                name="Modernist",
                url="https://claude.ai/design/p/p-modernist",
            )
        ]
    )

    [result] = account_status(transport, repo_root=tmp_path)

    assert result.status == "mirrored"
    assert result.slug is None


def test_account_status_classifies_an_excluded_project_with_its_reason(
    tmp_path: Path,
):
    _write_exclusions(
        tmp_path,
        {"REMOVED-PyForge Unifying Strategy": "ad-hoc duplicate, retired"},
    )
    transport = FakeStatusTransport(
        list_projects_answer=[
            ProjectSummary(
                project_id="p-removed",
                name="REMOVED-PyForge Unifying Strategy",
                url="https://claude.ai/design/p/p-removed",
            )
        ]
    )

    [result] = account_status(transport, repo_root=tmp_path)

    assert result.status == "excluded"
    assert result.reason == "ad-hoc duplicate, retired"
    assert result.slug is None


def test_account_status_exclusion_is_exact_name_never_a_heuristic(tmp_path: Path):
    """A name merely resembling an excluded one (a heuristic match) must
    not be excluded -- only an exact match against the recorded table
    counts (the story's own Never boundary)."""
    _write_exclusions(
        tmp_path,
        {"REMOVED-PyForge Unifying Strategy": "ad-hoc duplicate, retired"},
    )
    transport = FakeStatusTransport(
        list_projects_answer=[
            ProjectSummary(
                project_id="p-similar",
                name="REMOVED-PyForge Unifying Strategy Deck",
                url="https://claude.ai/design/p/p-similar",
            )
        ]
    )

    [result] = account_status(transport, repo_root=tmp_path)

    assert result.status == "untwinned"


def test_account_status_reports_no_project_absent(tmp_path: Path):
    """CAP-1's own success signal: every project the account returns
    appears in the report, whatever its classification."""
    _register_local_twin(tmp_path, "pyforge-warden", "p-1")
    _write_exclusions(tmp_path, {"Local recipes repository connection": "stale hand-mirrored copy"})
    transport = FakeStatusTransport(
        list_projects_answer=[
            ProjectSummary(
                project_id="p-1",
                name="PyForge Warden deck",
                url="https://claude.ai/design/p/p-1",
            ),
            ProjectSummary(
                project_id="p-2",
                name="Modernist",
                url="https://claude.ai/design/p/p-2",
            ),
            ProjectSummary(
                project_id="p-3",
                name="Local recipes repository connection",
                url="https://claude.ai/design/p/p-3",
            ),
            ProjectSummary(
                project_id="p-4",
                name="LLM Knowledge Bases",
                url="https://claude.ai/design/p/p-4",
            ),
        ]
    )

    results = account_status(transport, repo_root=tmp_path)

    assert [r.status for r in results] == [
        "linked",
        "mirrored",
        "excluded",
        "untwinned",
    ]
    assert {r.project_id for r in results} == {"p-1", "p-2", "p-3", "p-4"}


def test_account_status_is_read_only(tmp_path: Path):
    """Never calls a write-side transport method and never touches
    ``state.py`` (mirrors CAP-3's identical FR-13/NFR-08 guarantee)."""
    _register_local_twin(tmp_path, "pyforge-warden", "p-1")
    transport = FakeStatusTransport(list_projects_answer=[])

    account_status(transport, repo_root=tmp_path)

    assert transport.names() == ["list_projects"]
    assert not (tmp_path / ".herald").exists()


def test_account_status_on_no_local_presentations_dir_reports_untwinned(
    tmp_path: Path,
):
    transport = FakeStatusTransport(
        list_projects_answer=[ProjectSummary(project_id="p-1", name="Some Deck", url="https://claude.ai/design/p/p-1")]
    )

    [result] = account_status(transport, repo_root=tmp_path)

    assert result.status == "untwinned"


def _register_malformed_twin(tmp_path: Path, slug: str) -> Path:
    """A local deck whose README's own § *Design project* section has the
    wrong body-line count (one line, not the canonical two) -- the shape
    ``registry.read`` raises ``errors.HeraldError`` on."""
    deck_dir = _make_deck_dir(tmp_path, slug)
    (deck_dir / "README.md").write_text(
        f"# {slug}\n\n## Design project (the bridge's far end)\nonly one line, not the canonical two\n",
        encoding="utf-8",
    )
    return deck_dir


def test_account_status_isolates_one_slugs_malformed_registry_section(
    tmp_path: Path,
):
    """Regression: a single malformed local README (``registry.read``
    raises) must not crash the whole ``--account`` report -- mirrors
    ``status()``'s own proven guarantee
    (``test_status_multi_deck_isolates_one_slugs_malformed_entry``)."""
    _register_local_twin(tmp_path, "pyforge-warden", "p-1")
    _register_malformed_twin(tmp_path, "pyforge-bad")
    transport = FakeStatusTransport(
        list_projects_answer=[
            ProjectSummary(
                project_id="p-1",
                name="PyForge Warden deck",
                url="https://claude.ai/design/p/p-1",
            )
        ]
    )

    [result] = account_status(transport, repo_root=tmp_path)

    assert result.status == "linked"
    assert result.slug == "pyforge-warden"


def test_account_status_raises_on_duplicate_registered_project_id(tmp_path: Path):
    """Two local decks registered against the same Design project id must
    not silently let the later-sorted slug win -- that would misattribute
    ``AccountProjectStatus.slug`` with no error."""
    _register_local_twin(tmp_path, "pyforge-aaa", "p-dup")
    _register_local_twin(tmp_path, "pyforge-bbb", "p-dup")
    transport = FakeStatusTransport(list_projects_answer=[])

    with pytest.raises(HeraldError) as exc_info:
        account_status(transport, repo_root=tmp_path)

    message = str(exc_info.value)
    assert "pyforge-aaa" in message
    assert "pyforge-bbb" in message
    assert "p-dup" in message
