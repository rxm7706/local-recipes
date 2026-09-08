"""``herald deck seed <slug>`` CLI wiring (Story 1.6): argument parsing,
composing ``bridge.run`` + ``deck_pipeline.seed`` over the V1-default
``McpTransport``, and routing the result through ``dispatch`` (AD-6).

``deck_pipeline.seed`` itself is monkeypatched here -- its own behavior is
``test_deck_pipeline.py``'s job. What's under test is the CLI's own
composition: which transport it builds, which arguments it forwards, what it
prints on success, and that a raised ``HeraldError`` reaches ``dispatch``
unchanged.
"""

from __future__ import annotations

from pathlib import Path

from pyforge.herald import cli, deck_pipeline
from pyforge.herald.errors import SeedConflictError
from pyforge.herald.transport.base import ProjectRef


def _fake_seed_result(project_id="p-new", url="https://claude.ai/design/p/p-new"):
    return deck_pipeline.SeedResult(
        project=ProjectRef(project_id=project_id, url=url),
        persona="Warden",
        prototype_filename="PyForge Warden.dc.html",
    )


def test_deck_seed_help_exits_zero():
    assert cli.main(["deck", "seed", "--help"]) == 0


def test_deck_seed_missing_slug_is_a_usage_error():
    assert cli.main(["deck", "seed"]) == 2


def test_deck_seed_success_prints_the_project_url_and_returns_0(
    monkeypatch, capsys, tmp_path: Path
):
    seen = {}

    def _fake_seed(transport, *, slug, repo_root, support_source_project_id):
        seen["slug"] = slug
        seen["repo_root"] = repo_root
        seen["support_source_project_id"] = support_source_project_id
        seen["transport"] = transport
        return _fake_seed_result()

    monkeypatch.setattr(deck_pipeline, "seed", _fake_seed)

    exit_code = cli.main(
        ["deck", "seed", "pyforge-warden", "--repo-root", str(tmp_path)]
    )

    assert exit_code == 0
    assert seen["slug"] == "pyforge-warden"
    assert seen["repo_root"] == tmp_path
    assert (
        seen["support_source_project_id"]
        == deck_pipeline.PILOT_SUPPORT_SOURCE_PROJECT_ID
    )
    out = capsys.readouterr().out
    assert "pyforge-warden" in out
    assert "https://claude.ai/design/p/p-new" in out


def test_deck_seed_defaults_repo_root_to_cwd(monkeypatch, tmp_path: Path):
    seen = {}

    def _fake_seed(transport, *, slug, repo_root, support_source_project_id):
        seen["repo_root"] = repo_root
        return _fake_seed_result()

    monkeypatch.setattr(deck_pipeline, "seed", _fake_seed)
    monkeypatch.chdir(tmp_path)

    cli.main(["deck", "seed", "pyforge-warden"])

    assert seen["repo_root"] == tmp_path


def test_deck_seed_forwards_an_explicit_support_source_project(monkeypatch):
    seen = {}

    def _fake_seed(transport, *, slug, repo_root, support_source_project_id):
        seen["support_source_project_id"] = support_source_project_id
        return _fake_seed_result()

    monkeypatch.setattr(deck_pipeline, "seed", _fake_seed)

    cli.main(
        [
            "deck",
            "seed",
            "pyforge-warden",
            "--support-source-project",
            "custom-id",
        ]
    )

    assert seen["support_source_project_id"] == "custom-id"


def test_deck_seed_herald_error_reaches_dispatch_and_maps_to_its_exit_code(
    monkeypatch, capsys
):
    def _fake_seed(transport, *, slug, repo_root, support_source_project_id):
        raise SeedConflictError(f"{slug!r} is already seeded")

    monkeypatch.setattr(deck_pipeline, "seed", _fake_seed)

    exit_code = cli.main(["deck", "seed", "pyforge-warden"])

    assert exit_code == 3  # SeedConflictError -> 3, per errors.exit_code_for
    err = capsys.readouterr().err
    assert "SeedConflictError" in err
    assert "already seeded" in err
