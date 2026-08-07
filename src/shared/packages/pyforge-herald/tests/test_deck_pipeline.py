"""``deck_pipeline.seed`` -- CAP-1 (Story 1.6): the local-prove gate, the
state-based conflict check, the 8-step write sequence, and the dual
state.py/registry.py record.

Every transport call is against a hand-written ``FakeTransport`` (no
network, no adapter); every local-prove call is against a hand-written
``FakeProver`` (no real ``npm`` subprocess).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from pyforge.herald import state
from pyforge.herald.deck_pipeline import (
    PILOT_SUPPORT_SOURCE_PROJECT_ID,
    NpmLocalProver,
    SeedResult,
    _persona_from_slug,
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
