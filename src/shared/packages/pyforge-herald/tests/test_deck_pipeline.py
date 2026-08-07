"""``deck_pipeline.seed`` -- CAP-1 (Story 1.6): the local-prove gate, the
state-based conflict check, the 8-step write sequence, and the dual
state.py/registry.py record.

Every transport call is against a hand-written ``FakeTransport`` (no
network, no adapter); every local-prove call is against a hand-written
``FakeProver`` (no real ``npm`` subprocess).
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pyforge.herald import state
from pyforge.herald.deck_pipeline import (
    PILOT_SUPPORT_SOURCE_PROJECT_ID,
    PROTOTYPE_ARTIFACT_KEY,
    NpmLocalProver,
    PullResult,
    SeedResult,
    _persona_from_slug,
    pull_marp_source,
    pull_prototype,
    seed,
)
from pyforge.herald.errors import HeraldError, SeedConflictError
from pyforge.herald.registry import read as read_registry
from pyforge.herald.registry import register
from pyforge.herald.transport.base import FileRead, PlanHandle, PreviewRef, ProjectRef


class FakeTransport:
    """A hand-written ``DesignTransport`` double recording every call, in
    order, as ``(method, kwargs)``."""

    def __init__(
        self, *, prompt="PROMPT", project=None, plan=None, fails: dict | None = None
    ):
        self.calls: list[tuple[str, dict]] = []
        self._prompt = prompt
        self._project = project or ProjectRef(
            project_id="p-new", url="https://claude.ai/design/p/p-new"
        )
        self._plan = plan or PlanHandle(
            plan_token="tok", base_etags={"support.js": "0", "deck-stage.js": "0"}
        )
        # Keyed by method name -- raises that exception INSTEAD OF the
        # normal canned return, after still recording the call.
        self._fails: dict = dict(fails or {})

    def get_design_prompt(self, **kwargs):
        self.calls.append(("get_design_prompt", kwargs))
        if "get_design_prompt" in self._fails:
            raise self._fails["get_design_prompt"]
        return self._prompt

    def create_project(self, **kwargs):
        self.calls.append(("create_project", kwargs))
        if "create_project" in self._fails:
            raise self._fails["create_project"]
        return self._project

    def finalize_plan(self, **kwargs):
        self.calls.append(("finalize_plan", kwargs))
        if "finalize_plan" in self._fails:
            raise self._fails["finalize_plan"]
        return self._plan

    def create_support_js(self, **kwargs):
        self.calls.append(("create_support_js", kwargs))
        return {}

    def copy_files(self, **kwargs):
        self.calls.append(("copy_files", kwargs))
        return {}

    def write_files(self, **kwargs):
        self.calls.append(("write_files", kwargs))
        return {}

    def read_file(self, **kwargs) -> FileRead:
        raise NotImplementedError("seed never reads")

    def render_preview(self, **kwargs) -> PreviewRef:
        raise NotImplementedError("seed never previews")

    def names(self) -> list[str]:
        return [name for name, _kwargs in self.calls]


class FakeProver:
    def __init__(self, *, fails: HeraldError | None = None):
        self.calls: list[Path] = []
        self._fails = fails

    def prove(self, deck_dir: Path) -> None:
        self.calls.append(deck_dir)
        if self._fails is not None:
            raise self._fails


def _make_deck(tmp_path: Path, slug: str, persona: str | None = None) -> Path:
    persona = persona or _persona_from_slug(slug)
    deck_dir = tmp_path / "presentations" / slug
    project_dir = deck_dir / "project"
    project_dir.mkdir(parents=True)
    (project_dir / f"PyForge {persona}.dc.html").write_text(
        "<html>proto</html>", encoding="utf-8"
    )
    (deck_dir / "README.md").write_text(f"# {slug}\n\nBody.\n", encoding="utf-8")
    return deck_dir


# --- _persona_from_slug ------------------------------------------------------


@pytest.mark.parametrize(
    ("slug", "persona"),
    [
        ("pyforge-warden", "Warden"),
        ("pyforge-cli-anything-hub", "Cli Anything Hub"),
        ("standalone", "Standalone"),
    ],
)
def test_persona_from_slug(slug, persona):
    assert _persona_from_slug(slug) == persona


# --- the happy path ----------------------------------------------------------


def test_seed_happy_path_calls_every_step_in_order(tmp_path: Path):
    deck_dir = _make_deck(tmp_path, "pyforge-warden")
    transport = FakeTransport()
    prover = FakeProver()

    result = seed(transport, slug="pyforge-warden", repo_root=tmp_path, prover=prover)

    assert isinstance(result, SeedResult)
    assert result.persona == "Warden"
    assert result.prototype_filename == "PyForge Warden.dc.html"
    assert result.project.project_id == "p-new"
    assert prover.calls == [deck_dir]
    assert transport.names() == [
        "get_design_prompt",
        "create_project",
        "finalize_plan",
        "create_support_js",
        "copy_files",
        "write_files",
    ]


def test_seed_create_project_uses_the_persona_naming_convention(tmp_path: Path):
    _make_deck(tmp_path, "pyforge-doctor")
    transport = FakeTransport()
    seed(transport, slug="pyforge-doctor", repo_root=tmp_path, prover=FakeProver())
    _name, kwargs = transport.calls[1]
    assert kwargs["name"] == "PyForge Doctor deck"


def test_seed_finalize_plan_declares_all_three_write_paths(tmp_path: Path):
    _make_deck(tmp_path, "pyforge-warden")
    transport = FakeTransport()
    seed(transport, slug="pyforge-warden", repo_root=tmp_path, prover=FakeProver())
    _name, kwargs = transport.calls[2]
    assert set(kwargs["writes"]) == {
        "support.js",
        "deck-stage.js",
        "PyForge Warden.dc.html",
    }


def test_seed_create_support_js_uses_the_returned_base_etag(tmp_path: Path):
    _make_deck(tmp_path, "pyforge-warden")
    plan = PlanHandle(plan_token="tok", base_etags={"support.js": "E9"})
    transport = FakeTransport(plan=plan)
    seed(transport, slug="pyforge-warden", repo_root=tmp_path, prover=FakeProver())
    _name, kwargs = transport.calls[3]
    assert kwargs["if_match"] == "E9"
    assert kwargs["plan_token"] == "tok"


def test_seed_create_support_js_falls_back_to_fresh_etag(tmp_path: Path):
    _make_deck(tmp_path, "pyforge-warden")
    plan = PlanHandle(plan_token="tok", base_etags={})
    transport = FakeTransport(plan=plan)
    seed(transport, slug="pyforge-warden", repo_root=tmp_path, prover=FakeProver())
    _name, kwargs = transport.calls[3]
    assert kwargs["if_match"] == "0"


def test_seed_copy_files_uses_the_default_pilot_source_project(tmp_path: Path):
    _make_deck(tmp_path, "pyforge-warden")
    transport = FakeTransport()
    seed(transport, slug="pyforge-warden", repo_root=tmp_path, prover=FakeProver())
    _name, kwargs = transport.calls[4]
    entry = kwargs["files"][0]
    assert entry["src_project_id"] == PILOT_SUPPORT_SOURCE_PROJECT_ID
    assert entry["src_path"] == "deck-stage.js"


def test_seed_copy_files_honours_an_explicit_source_project_override(tmp_path: Path):
    _make_deck(tmp_path, "pyforge-warden")
    transport = FakeTransport()
    seed(
        transport,
        slug="pyforge-warden",
        repo_root=tmp_path,
        prover=FakeProver(),
        support_source_project_id="custom-project-id",
    )
    _name, kwargs = transport.calls[4]
    assert kwargs["files"][0]["src_project_id"] == "custom-project-id"


def test_seed_write_files_carries_the_exact_local_prototype_bytes(tmp_path: Path):
    deck_dir = _make_deck(tmp_path, "pyforge-warden")
    on_disk = (deck_dir / "project" / "PyForge Warden.dc.html").read_text(
        encoding="utf-8"
    )
    transport = FakeTransport()
    seed(transport, slug="pyforge-warden", repo_root=tmp_path, prover=FakeProver())
    _name, kwargs = transport.calls[5]
    entry = kwargs["files"][0]
    assert entry["path"] == "PyForge Warden.dc.html"
    assert entry["data"] == on_disk


def test_seed_records_state(tmp_path: Path):
    _make_deck(tmp_path, "pyforge-warden")
    transport = FakeTransport()
    seed(transport, slug="pyforge-warden", repo_root=tmp_path, prover=FakeProver())
    recorded = state.read(tmp_path / state.DEFAULT_STATE_PATH, "pyforge-warden")
    assert recorded == state.DeckState(project_id="p-new", etags={}, last_pull=None)


def test_seed_registers_the_readme_design_project_section(tmp_path: Path):
    deck_dir = _make_deck(tmp_path, "pyforge-warden")
    transport = FakeTransport()
    seed(transport, slug="pyforge-warden", repo_root=tmp_path, prover=FakeProver())
    registered = read_registry(deck_dir / "README.md")
    assert registered.project_id == "p-new"
    assert registered.project_name == "PyForge Warden deck"
    assert registered.file_url == "https://claude.ai/design/p/p-new"


def test_seed_records_state_immediately_so_a_mid_pipeline_failure_never_duplicates_the_project(
    tmp_path: Path,
):
    """Review finding (Blind Hunter): `state.write` used to happen only
    after EVERY transport call succeeded. A failure anywhere between
    `create_project` and the final `state.write`/`registry.register` left
    the already-created remote project untracked by state.py's own
    conflict gate -- a retry's `existing_state is not None` check passed
    cleanly and `create_project` ran AGAIN, producing a second, orphaned
    duplicate project for the same slug. `state.write` now happens
    immediately after `create_project` succeeds, so this exact retry
    refuses instead."""
    _make_deck(tmp_path, "pyforge-warden")
    failing_transport = FakeTransport(
        fails={"finalize_plan": RuntimeError("simulated: etag conflict")}
    )
    with pytest.raises(RuntimeError, match="etag conflict"):
        seed(
            failing_transport,
            slug="pyforge-warden",
            repo_root=tmp_path,
            prover=FakeProver(),
        )
    # The project WAS created (that call succeeded) and state.py already
    # knows about it, even though the overall seed() call raised.
    assert "create_project" in failing_transport.names()
    recorded = state.read(tmp_path / state.DEFAULT_STATE_PATH, "pyforge-warden")
    assert recorded == state.DeckState(project_id="p-new", etags={}, last_pull=None)

    # A retry must refuse -- never call create_project a second time.
    retry_transport = FakeTransport()
    with pytest.raises(SeedConflictError, match="already seeded"):
        seed(
            retry_transport,
            slug="pyforge-warden",
            repo_root=tmp_path,
            prover=FakeProver(),
        )
    assert retry_transport.calls == []


def test_seed_refuses_a_missing_readme_before_any_transport_call(tmp_path: Path):
    """Review finding (Edge Case Hunter): `registry.register` (called at
    the very end of a successful run) refuses against a missing
    `readme_path` -- "this module never fabricates a whole README from
    nothing" -- but nothing checked for that up front. The old sequence let
    a real project get created and `state.write` succeed, then failed on
    `registry.register`, leaving a slug permanently marked seeded in
    state.py with no way to complete registration short of manual
    intervention. Now refuses before touching the local prover or any
    transport call at all."""
    deck_dir = tmp_path / "presentations" / "pyforge-warden"
    (deck_dir / "project").mkdir(parents=True)
    (deck_dir / "project" / "PyForge Warden.dc.html").write_text(
        "<html>proto</html>", encoding="utf-8"
    )
    # Deliberately NO README.md.
    transport = FakeTransport()
    prover = FakeProver()
    with pytest.raises(HeraldError, match="no README.md"):
        seed(transport, slug="pyforge-warden", repo_root=tmp_path, prover=prover)
    assert prover.calls == []
    assert transport.calls == []
    assert state.read(tmp_path / state.DEFAULT_STATE_PATH, "pyforge-warden") is None


# --- refusals and their "writes nothing" guarantee ---------------------------


def test_seed_refuses_a_missing_deck_directory(tmp_path: Path):
    transport = FakeTransport()
    with pytest.raises(HeraldError, match="no deck directory"):
        seed(transport, slug="pyforge-nope", repo_root=tmp_path, prover=FakeProver())
    assert transport.calls == []


def test_seed_refuses_when_already_seeded_before_any_call(tmp_path: Path):
    _make_deck(tmp_path, "pyforge-warden")
    state_path = tmp_path / state.DEFAULT_STATE_PATH
    state.write(
        state_path,
        "pyforge-warden",
        state.DeckState(project_id="already-there", etags={}, last_pull=None),
    )
    transport = FakeTransport()
    prover = FakeProver()
    with pytest.raises(SeedConflictError, match="already seeded"):
        seed(transport, slug="pyforge-warden", repo_root=tmp_path, prover=prover)
    assert transport.calls == []
    assert prover.calls == []


def test_seed_refuses_via_the_registry_bootstrap_fallback_when_no_state_entry(
    tmp_path: Path,
):
    """The four pilot decks were seeded by hand before state.py existed: no
    state entry, only a well-formed README section. Re-seeding one through
    this CLI must not silently create a second Design project."""
    deck_dir = _make_deck(tmp_path, "pyforge-warden")
    register(
        readme_path=deck_dir / "README.md",
        project_name="PyForge Warden deck",
        project_id="existing-project-id",
        file_url="https://claude.ai/design/p/existing-project-id",
    )
    transport = FakeTransport()
    prover = FakeProver()
    with pytest.raises(SeedConflictError, match="existing-project-id"):
        seed(transport, slug="pyforge-warden", repo_root=tmp_path, prover=prover)
    assert transport.calls == []
    assert prover.calls == []


def test_seed_refuses_a_malformed_registry_section_rather_than_treating_it_as_unseeded(
    tmp_path: Path,
):
    """A README carrying the heading with a body that doesn't match the
    canonical two-line shape (DW-1-5-1: true of all 13 pre-existing decks)
    is corruption, not 'nothing registered yet' -- must still refuse."""
    deck_dir = _make_deck(tmp_path, "pyforge-warden")
    (deck_dir / "README.md").write_text(
        "# pyforge-warden\n\n"
        "## Design project (the bridge's far end)\n\n"
        'Prototype lives in Claude Design project **"PyForge Warden deck"** '
        "(`existing-project-id`):\n"
        "https://claude.ai/design/p/existing-project-id\n"
        'Pull it into this deck with the MCP bridge ("pull warden") -- see\n'
        "`docs/specs/presentation-deck.md` § *The MCP bridge*.\n",
        encoding="utf-8",
    )
    transport = FakeTransport()
    prover = FakeProver()
    with pytest.raises(SeedConflictError, match="malformed"):
        seed(transport, slug="pyforge-warden", repo_root=tmp_path, prover=prover)
    assert transport.calls == []
    assert prover.calls == []


def test_seed_refuses_a_missing_local_prototype_before_proving(tmp_path: Path):
    deck_dir = tmp_path / "presentations" / "pyforge-warden"
    (deck_dir / "project").mkdir(parents=True)
    (deck_dir / "README.md").write_text("# pyforge-warden\n", encoding="utf-8")
    transport = FakeTransport()
    prover = FakeProver()
    with pytest.raises(HeraldError, match="no local prototype"):
        seed(transport, slug="pyforge-warden", repo_root=tmp_path, prover=prover)
    assert prover.calls == []
    assert transport.calls == []


def test_seed_propagates_a_prove_failure_before_any_transport_call(tmp_path: Path):
    _make_deck(tmp_path, "pyforge-warden")
    transport = FakeTransport()
    prover = FakeProver(fails=HeraldError("npm run extract exited 1"))
    with pytest.raises(HeraldError, match="npm run extract"):
        seed(transport, slug="pyforge-warden", repo_root=tmp_path, prover=prover)
    assert transport.calls == []


def test_seed_refuses_an_empty_design_prompt_before_creating_a_project(
    tmp_path: Path,
):
    _make_deck(tmp_path, "pyforge-warden")
    transport = FakeTransport(prompt="")
    with pytest.raises(HeraldError, match="empty design-system prompt"):
        seed(transport, slug="pyforge-warden", repo_root=tmp_path, prover=FakeProver())
    assert transport.names() == ["get_design_prompt"]


# --- NpmLocalProver's own error-mapping, subprocess.run patched out --------


def test_npm_local_prover_runs_extract_then_build(monkeypatch, tmp_path: Path):
    calls: list[list[str]] = []

    class _Completed:
        returncode = 0
        stdout = ""
        stderr = ""

    def _run(args, **kwargs):
        calls.append(args)
        return _Completed()

    monkeypatch.setattr(subprocess, "run", _run)
    NpmLocalProver().prove(tmp_path)
    assert calls == [["npm", "run", "extract"], ["npm", "run", "build"]]


def test_npm_local_prover_maps_nonzero_exit_to_a_herald_error(
    monkeypatch, tmp_path: Path
):
    class _Completed:
        returncode = 1
        stdout = ""
        stderr = "slide count mismatch"

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Completed())
    with pytest.raises(HeraldError, match="slide count mismatch"):
        NpmLocalProver().prove(tmp_path)


def test_npm_local_prover_maps_a_launch_oserror_to_a_herald_error(
    monkeypatch, tmp_path: Path
):
    def _raise(*args, **kwargs):
        raise FileNotFoundError("no such file: npm")

    monkeypatch.setattr(subprocess, "run", _raise)
    with pytest.raises(HeraldError, match="could not run"):
        NpmLocalProver().prove(tmp_path)


def test_npm_local_prover_maps_a_timeout_to_a_herald_error(monkeypatch, tmp_path: Path):
    def _raise(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="npm", timeout=1)

    monkeypatch.setattr(subprocess, "run", _raise)
    with pytest.raises(HeraldError, match="exceeded"):
        NpmLocalProver(timeout=1).prove(tmp_path)


# --- CAP-2: pull_prototype (Story 2.1) ---------------------------------------


class FakePullTransport:
    """A hand-written ``DesignTransport`` double exercising only
    ``read_file`` -- every other method raises, since ``pull_prototype``
    never calls them."""

    def __init__(self, *, answers=None):
        self.calls: list[dict] = []
        # Consumed one per call (a list), or a single canned FileRead reused
        # for every call.
        self._answers = answers

    def read_file(self, **kwargs) -> FileRead:
        self.calls.append(kwargs)
        answer = self._answers
        if isinstance(answer, list):
            assert answer, "FakePullTransport ran out of canned read_file answers"
            return answer.pop(0)
        return answer

    def get_design_prompt(self, **kwargs):
        raise NotImplementedError("pull_prototype never calls get_design_prompt")

    def create_project(self, **kwargs):
        raise NotImplementedError("pull_prototype never calls create_project")

    def finalize_plan(self, **kwargs):
        raise NotImplementedError("pull_prototype never calls finalize_plan")

    def create_support_js(self, **kwargs):
        raise NotImplementedError("pull_prototype never calls create_support_js")

    def copy_files(self, **kwargs):
        raise NotImplementedError("pull_prototype never calls copy_files")

    def write_files(self, **kwargs):
        raise NotImplementedError("pull_prototype never calls write_files")

    def render_preview(self, **kwargs) -> PreviewRef:
        raise NotImplementedError("pull_prototype never calls render_preview")


class FakeExporter:
    def __init__(self, *, fails: HeraldError | None = None):
        self.calls: list[tuple[str, Path]] = []
        self._fails = fails

    def export(self, *, slug: str, repo_root: Path) -> None:
        self.calls.append((slug, repo_root))
        if self._fails is not None:
            raise self._fails


class FakeCommitter:
    def __init__(self, *, fails: HeraldError | None = None):
        self.calls: list[dict] = []
        self._fails = fails

    def commit(self, *, repo_root: Path, paths: list[Path], message: str) -> None:
        self.calls.append(
            {"repo_root": repo_root, "paths": list(paths), "message": message}
        )
        if self._fails is not None:
            raise self._fails


_FIXED_NOW = datetime(2026, 8, 7, 12, 0, 0, tzinfo=timezone.utc)


def _seed_state(tmp_path: Path, slug: str, *, project_id="p-1", etags=None) -> None:
    state.write(
        tmp_path / state.DEFAULT_STATE_PATH,
        slug,
        state.DeckState(project_id=project_id, etags=dict(etags or {}), last_pull=None),
    )


def test_pull_prototype_short_circuits_on_unchanged_and_skips_every_downstream_step(
    tmp_path: Path,
):
    _seed_state(tmp_path, "pyforge-warden", etags={PROTOTYPE_ARTIFACT_KEY: "E1"})
    transport = FakePullTransport(
        answers=FileRead(path="x", etag="E1", body=None, unchanged=True)
    )
    prover = FakeProver()
    exporter = FakeExporter()

    result = pull_prototype(
        transport,
        slug="pyforge-warden",
        repo_root=tmp_path,
        prover=prover,
        exporter=exporter,
        now=lambda: _FIXED_NOW,
    )

    assert result == PullResult(
        slug="pyforge-warden",
        artifact=PROTOTYPE_ARTIFACT_KEY,
        local_path=None,
        unchanged=True,
        etag="E1",
        committed=False,
    )
    # Nothing downstream of the etag check ran.
    assert prover.calls == []
    assert exporter.calls == []
    assert not (tmp_path / "presentations" / "pyforge-warden" / "project").exists()
    # state.py is untouched -- last_pull stays None, proving no re-write happened.
    recorded = state.read(tmp_path / state.DEFAULT_STATE_PATH, "pyforge-warden")
    assert recorded.last_pull is None


def test_pull_prototype_if_none_match_uses_the_last_seen_etag(tmp_path: Path):
    _seed_state(tmp_path, "pyforge-warden", etags={PROTOTYPE_ARTIFACT_KEY: "E1"})
    transport = FakePullTransport(
        answers=FileRead(path="x", etag="E1", body=None, unchanged=True)
    )
    pull_prototype(
        transport,
        slug="pyforge-warden",
        repo_root=tmp_path,
        prover=FakeProver(),
        exporter=FakeExporter(),
        now=lambda: _FIXED_NOW,
    )
    assert transport.calls[0]["if_none_match"] == "E1"
    assert transport.calls[0]["project_id"] == "p-1"
    assert transport.calls[0]["path"] == "PyForge Warden.dc.html"


def test_pull_prototype_writes_the_decoded_body_and_re_derives(tmp_path: Path):
    _seed_state(tmp_path, "pyforge-warden")
    transport = FakePullTransport(
        answers=FileRead(
            path="x", etag="E2", body="<html>edited & saved</html>", unchanged=False
        )
    )
    prover = FakeProver()
    exporter = FakeExporter()

    result = pull_prototype(
        transport,
        slug="pyforge-warden",
        repo_root=tmp_path,
        prover=prover,
        exporter=exporter,
        now=lambda: _FIXED_NOW,
    )

    local_path = (
        tmp_path
        / "presentations"
        / "pyforge-warden"
        / "project"
        / "PyForge Warden.dc.html"
    )
    assert result.local_path == local_path
    assert result.unchanged is False
    assert result.etag == "E2"
    assert local_path.read_text(encoding="utf-8") == "<html>edited & saved</html>"
    assert prover.calls == [tmp_path / "presentations" / "pyforge-warden"]
    assert exporter.calls == [("pyforge-warden", tmp_path)]
    recorded = state.read(tmp_path / state.DEFAULT_STATE_PATH, "pyforge-warden")
    assert recorded.etags[PROTOTYPE_ARTIFACT_KEY] == "E2"
    assert recorded.last_pull == _FIXED_NOW.isoformat()


def test_pull_prototype_body_is_not_re_decoded(tmp_path: Path):
    """`FileRead.body` is already entity-decoded by
    `transport.base.parse_read_response` -- `pull_prototype` must use it
    verbatim. A body containing a literal `&amp;` (e.g. the file's own prior
    content already had one) must survive unchanged, not be decoded a
    second time into `&`."""
    _seed_state(tmp_path, "pyforge-warden")
    transport = FakePullTransport(
        answers=FileRead(
            path="x", etag="E3", body="already &amp; decoded once", unchanged=False
        )
    )
    pull_prototype(
        transport,
        slug="pyforge-warden",
        repo_root=tmp_path,
        prover=FakeProver(),
        exporter=FakeExporter(),
        now=lambda: _FIXED_NOW,
    )
    local_path = (
        tmp_path
        / "presentations"
        / "pyforge-warden"
        / "project"
        / "PyForge Warden.dc.html"
    )
    assert local_path.read_text(encoding="utf-8") == "already &amp; decoded once"


def test_pull_prototype_refuses_a_truncated_answer_before_writing(tmp_path: Path):
    _seed_state(tmp_path, "pyforge-warden")
    transport = FakePullTransport(
        answers=FileRead(
            path="x",
            etag="E4",
            body="partial",
            unchanged=False,
            first_line=1,
            last_line=5,
            total_lines=20,
        )
    )
    prover = FakeProver()
    exporter = FakeExporter()
    with pytest.raises(HeraldError, match="truncated"):
        pull_prototype(
            transport,
            slug="pyforge-warden",
            repo_root=tmp_path,
            prover=prover,
            exporter=exporter,
            now=lambda: _FIXED_NOW,
        )
    assert prover.calls == []
    assert exporter.calls == []
    assert not (tmp_path / "presentations" / "pyforge-warden" / "project").exists()


def test_pull_prototype_refuses_a_changed_answer_with_no_body(tmp_path: Path):
    _seed_state(tmp_path, "pyforge-warden")
    transport = FakePullTransport(
        answers=FileRead(path="x", etag="E5", body=None, unchanged=False)
    )
    with pytest.raises(HeraldError, match="no body"):
        pull_prototype(
            transport,
            slug="pyforge-warden",
            repo_root=tmp_path,
            prover=FakeProver(),
            exporter=FakeExporter(),
            now=lambda: _FIXED_NOW,
        )


def test_pull_prototype_refuses_when_not_seeded(tmp_path: Path):
    transport = FakePullTransport(answers=None)
    with pytest.raises(HeraldError, match="herald deck seed"):
        pull_prototype(
            transport,
            slug="pyforge-warden",
            repo_root=tmp_path,
            prover=FakeProver(),
            exporter=FakeExporter(),
        )
    assert transport.calls == []


def test_pull_prototype_propagates_an_export_failure_after_the_write_lands(
    tmp_path: Path,
):
    _seed_state(tmp_path, "pyforge-warden")
    transport = FakePullTransport(
        answers=FileRead(path="x", etag="E6", body="<html>x</html>", unchanged=False)
    )
    exporter = FakeExporter(fails=HeraldError("deck-export exited 1"))
    with pytest.raises(HeraldError, match="deck-export exited 1"):
        pull_prototype(
            transport,
            slug="pyforge-warden",
            repo_root=tmp_path,
            prover=FakeProver(),
            exporter=exporter,
            now=lambda: _FIXED_NOW,
        )
    # The write and state update already happened before export ran.
    local_path = (
        tmp_path
        / "presentations"
        / "pyforge-warden"
        / "project"
        / "PyForge Warden.dc.html"
    )
    assert local_path.read_text(encoding="utf-8") == "<html>x</html>"
    recorded = state.read(tmp_path / state.DEFAULT_STATE_PATH, "pyforge-warden")
    assert recorded.etags[PROTOTYPE_ARTIFACT_KEY] == "E6"


# --- CAP-2: --commit (Story 2.2) ---------------------------------------------


def test_pull_prototype_without_commit_never_calls_the_committer(tmp_path: Path):
    _seed_state(tmp_path, "pyforge-warden")
    transport = FakePullTransport(
        answers=FileRead(path="x", etag="E7", body="<html>x</html>", unchanged=False)
    )
    committer = FakeCommitter()
    result = pull_prototype(
        transport,
        slug="pyforge-warden",
        repo_root=tmp_path,
        prover=FakeProver(),
        exporter=FakeExporter(),
        committer=committer,
        now=lambda: _FIXED_NOW,
    )
    assert committer.calls == []
    assert result.committed is False


def test_pull_prototype_commit_true_stages_and_commits_after_a_real_change(
    tmp_path: Path,
):
    _seed_state(tmp_path, "pyforge-warden")
    transport = FakePullTransport(
        answers=FileRead(path="x", etag="E8", body="<html>x</html>", unchanged=False)
    )
    committer = FakeCommitter()
    result = pull_prototype(
        transport,
        slug="pyforge-warden",
        repo_root=tmp_path,
        commit=True,
        prover=FakeProver(),
        exporter=FakeExporter(),
        committer=committer,
        now=lambda: _FIXED_NOW,
    )
    assert result.committed is True
    assert len(committer.calls) == 1
    call = committer.calls[0]
    assert call["repo_root"] == tmp_path
    assert tmp_path / "presentations" / "pyforge-warden" in call["paths"]
    assert tmp_path / state.DEFAULT_STATE_PATH in call["paths"]
    assert "pyforge-warden" in call["message"]


def test_pull_prototype_commit_true_never_commits_an_unchanged_pull(tmp_path: Path):
    _seed_state(tmp_path, "pyforge-warden", etags={PROTOTYPE_ARTIFACT_KEY: "E1"})
    transport = FakePullTransport(
        answers=FileRead(path="x", etag="E1", body=None, unchanged=True)
    )
    committer = FakeCommitter()
    result = pull_prototype(
        transport,
        slug="pyforge-warden",
        repo_root=tmp_path,
        commit=True,
        prover=FakeProver(),
        exporter=FakeExporter(),
        committer=committer,
        now=lambda: _FIXED_NOW,
    )
    assert committer.calls == []
    assert result.committed is False
    assert result.unchanged is True


def test_pull_prototype_propagates_a_commit_failure(tmp_path: Path):
    _seed_state(tmp_path, "pyforge-warden")
    transport = FakePullTransport(
        answers=FileRead(path="x", etag="E9", body="<html>x</html>", unchanged=False)
    )
    committer = FakeCommitter(fails=HeraldError("git commit failed: nothing to commit"))
    with pytest.raises(HeraldError, match="nothing to commit"):
        pull_prototype(
            transport,
            slug="pyforge-warden",
            repo_root=tmp_path,
            commit=True,
            prover=FakeProver(),
            exporter=FakeExporter(),
            committer=committer,
            now=lambda: _FIXED_NOW,
        )
    # The write and state update already landed before the commit failed --
    # not rolled back (see the story spec's Design Notes).
    local_path = (
        tmp_path
        / "presentations"
        / "pyforge-warden"
        / "project"
        / "PyForge Warden.dc.html"
    )
    assert local_path.read_text(encoding="utf-8") == "<html>x</html>"


# --- CAP-2: pull_marp_source (Story 2.3) -------------------------------------


def test_pull_marp_source_short_circuits_on_unchanged(tmp_path: Path):
    _seed_state(tmp_path, "pyforge-warden", etags={"marp:deck": "M1"})
    transport = FakePullTransport(
        answers=FileRead(path="x", etag="M1", body=None, unchanged=True)
    )
    exporter = FakeExporter()
    result = pull_marp_source(
        transport,
        slug="pyforge-warden",
        repo_root=tmp_path,
        kind="deck",
        exporter=exporter,
        now=lambda: _FIXED_NOW,
    )
    assert result == PullResult(
        slug="pyforge-warden",
        artifact="marp:deck",
        local_path=None,
        unchanged=True,
        etag="M1",
        committed=False,
    )
    assert exporter.calls == []
    assert not (tmp_path / "presentations" / "pyforge-warden" / "src").exists()


def test_pull_marp_source_uses_the_short_name_remote_path(tmp_path: Path):
    _seed_state(tmp_path, "pyforge-warden")
    transport = FakePullTransport(
        answers=FileRead(path="x", etag="M2", body="# Deck", unchanged=False)
    )
    pull_marp_source(
        transport,
        slug="pyforge-warden",
        repo_root=tmp_path,
        kind="executive-summary",
        exporter=FakeExporter(),
        now=lambda: _FIXED_NOW,
    )
    assert transport.calls[0]["path"] == "warden-executive-summary.md"


def test_pull_marp_source_lands_at_the_dated_src_marp_path_and_calls_no_prover(
    tmp_path: Path,
):
    _seed_state(tmp_path, "pyforge-warden")
    transport = FakePullTransport(
        answers=FileRead(path="x", etag="M3", body="# Infographic", unchanged=False)
    )
    exporter = FakeExporter()

    result = pull_marp_source(
        transport,
        slug="pyforge-warden",
        repo_root=tmp_path,
        kind="infographic",
        exporter=exporter,
        now=lambda: _FIXED_NOW,
    )

    local_path = (
        tmp_path
        / "presentations"
        / "pyforge-warden"
        / "src"
        / "marp"
        / "pyforge-warden-infographic-2026-08-07.md"
    )
    assert result.local_path == local_path
    assert result.artifact == "marp:infographic"
    assert local_path.read_text(encoding="utf-8") == "# Infographic"
    assert exporter.calls == [("pyforge-warden", tmp_path)]
    recorded = state.read(tmp_path / state.DEFAULT_STATE_PATH, "pyforge-warden")
    assert recorded.etags["marp:infographic"] == "M3"


def test_pull_marp_source_refuses_an_unknown_kind(tmp_path: Path):
    _seed_state(tmp_path, "pyforge-warden")
    transport = FakePullTransport(answers=None)
    with pytest.raises(HeraldError, match="unknown Marp source kind"):
        pull_marp_source(
            transport,
            slug="pyforge-warden",
            repo_root=tmp_path,
            kind="cover",
            exporter=FakeExporter(),
        )
    assert transport.calls == []


def test_pull_marp_source_refuses_when_not_seeded(tmp_path: Path):
    transport = FakePullTransport(answers=None)
    with pytest.raises(HeraldError, match="herald deck seed"):
        pull_marp_source(
            transport,
            slug="pyforge-warden",
            repo_root=tmp_path,
            kind="deck",
            exporter=FakeExporter(),
        )
    assert transport.calls == []


def test_pull_marp_source_commit_true_stages_after_a_real_change(tmp_path: Path):
    _seed_state(tmp_path, "pyforge-warden")
    transport = FakePullTransport(
        answers=FileRead(path="x", etag="M4", body="# Deck", unchanged=False)
    )
    committer = FakeCommitter()
    result = pull_marp_source(
        transport,
        slug="pyforge-warden",
        repo_root=tmp_path,
        kind="deck",
        commit=True,
        exporter=FakeExporter(),
        committer=committer,
        now=lambda: _FIXED_NOW,
    )
    assert result.committed is True
    assert len(committer.calls) == 1
    assert "marp:deck" in committer.calls[0]["message"]


def test_pull_marp_source_commit_true_never_commits_an_unchanged_pull(tmp_path: Path):
    _seed_state(tmp_path, "pyforge-warden", etags={"marp:deck": "M1"})
    transport = FakePullTransport(
        answers=FileRead(path="x", etag="M1", body=None, unchanged=True)
    )
    committer = FakeCommitter()
    result = pull_marp_source(
        transport,
        slug="pyforge-warden",
        repo_root=tmp_path,
        kind="deck",
        commit=True,
        exporter=FakeExporter(),
        committer=committer,
        now=lambda: _FIXED_NOW,
    )
    assert committer.calls == []
    assert result.committed is False
