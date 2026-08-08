"""``herald deck pull <slug>`` CLI wiring (Story 2.1): argument parsing,
composing ``bridge.run`` + ``deck_pipeline.pull_prototype`` over the
V1-default ``McpTransport``, and routing the result through ``dispatch``
(AD-6).

``deck_pipeline.pull_prototype`` itself is monkeypatched here -- its own
behavior is ``test_deck_pipeline.py``'s job. What's under test is the CLI's
own composition: which transport it builds, which arguments it forwards,
what it prints on success (both the "unchanged" and the "pulled" shapes),
and that a raised ``HeraldError`` reaches ``dispatch`` unchanged. Mirrors
``test_cli_seed.py``'s own shape exactly.
"""

from __future__ import annotations

from pathlib import Path

from pyforge.herald import cli, deck_pipeline
from pyforge.herald.errors import HeraldError


def _fake_pull_result(**overrides):
    defaults = {
        "slug": "pyforge-warden",
        "artifact": "prototype",
        "local_path": Path(
            "presentations/pyforge-warden/project/PyForge Warden.dc.html"
        ),
        "unchanged": False,
        "etag": "E2",
        "committed": False,
    }
    defaults.update(overrides)
    return deck_pipeline.PullResult(**defaults)


def test_deck_pull_help_exits_zero():
    assert cli.main(["deck", "pull", "--help"]) == 0


def test_deck_pull_missing_slug_is_a_usage_error():
    assert cli.main(["deck", "pull"]) == 2


def test_deck_pull_success_prints_the_local_path_and_returns_0(
    monkeypatch, capsys, tmp_path: Path
):
    seen = {}

    def _fake_pull(transport, *, slug, repo_root, commit):
        seen["slug"] = slug
        seen["repo_root"] = repo_root
        seen["transport"] = transport
        seen["commit"] = commit
        return _fake_pull_result()

    monkeypatch.setattr(deck_pipeline, "pull_prototype", _fake_pull)

    exit_code = cli.main(
        ["deck", "pull", "pyforge-warden", "--repo-root", str(tmp_path)]
    )

    assert exit_code == 0
    assert seen["slug"] == "pyforge-warden"
    assert seen["repo_root"] == tmp_path
    assert seen["commit"] is False
    out = capsys.readouterr().out
    assert "pyforge-warden" in out
    assert "PyForge Warden.dc.html" in out


def test_deck_pull_unchanged_reports_unchanged_and_returns_0(monkeypatch, capsys):
    def _fake_pull(transport, *, slug, repo_root, commit):
        return _fake_pull_result(unchanged=True, local_path=None)

    monkeypatch.setattr(deck_pipeline, "pull_prototype", _fake_pull)

    exit_code = cli.main(["deck", "pull", "pyforge-warden"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "unchanged" in out


def test_deck_pull_defaults_repo_root_to_cwd(monkeypatch, tmp_path: Path):
    seen = {}

    def _fake_pull(transport, *, slug, repo_root, commit):
        seen["repo_root"] = repo_root
        return _fake_pull_result()

    monkeypatch.setattr(deck_pipeline, "pull_prototype", _fake_pull)
    monkeypatch.chdir(tmp_path)

    cli.main(["deck", "pull", "pyforge-warden"])

    assert seen["repo_root"] == tmp_path


def test_deck_pull_herald_error_reaches_dispatch_and_maps_to_its_exit_code(
    monkeypatch, capsys
):
    def _fake_pull(transport, *, slug, repo_root, commit):
        raise HeraldError("no bridge state recorded")

    monkeypatch.setattr(deck_pipeline, "pull_prototype", _fake_pull)

    exit_code = cli.main(["deck", "pull", "pyforge-warden"])

    assert exit_code == 1  # bare HeraldError -> 1, per errors.exit_code_for
    err = capsys.readouterr().err
    assert "HeraldError" in err
    assert "no bridge state recorded" in err


def test_deck_pull_commit_flag_defaults_to_false(monkeypatch):
    seen = {}

    def _fake_pull(transport, *, slug, repo_root, commit):
        seen["commit"] = commit
        return _fake_pull_result()

    monkeypatch.setattr(deck_pipeline, "pull_prototype", _fake_pull)
    cli.main(["deck", "pull", "pyforge-warden"])
    assert seen["commit"] is False


def test_deck_pull_commit_flag_forwards_true(monkeypatch):
    seen = {}

    def _fake_pull(transport, *, slug, repo_root, commit):
        seen["commit"] = commit
        return _fake_pull_result(committed=True)

    monkeypatch.setattr(deck_pipeline, "pull_prototype", _fake_pull)
    cli.main(["deck", "pull", "pyforge-warden", "--commit"])
    assert seen["commit"] is True


def test_deck_pull_commit_flag_reports_committed_in_stdout(monkeypatch, capsys):
    def _fake_pull(transport, *, slug, repo_root, commit):
        return _fake_pull_result(committed=commit)

    monkeypatch.setattr(deck_pipeline, "pull_prototype", _fake_pull)
    cli.main(["deck", "pull", "pyforge-warden", "--commit"])
    out = capsys.readouterr().out
    assert "committed" in out


def test_deck_pull_without_commit_flag_does_not_mention_committed_in_stdout(
    monkeypatch, capsys
):
    def _fake_pull(transport, *, slug, repo_root, commit):
        return _fake_pull_result(committed=commit)

    monkeypatch.setattr(deck_pipeline, "pull_prototype", _fake_pull)
    cli.main(["deck", "pull", "pyforge-warden"])
    out = capsys.readouterr().out
    assert "committed" not in out


# --- --target dispatch (Story 2.3) -------------------------------------------


def test_deck_pull_target_defaults_to_prototype(monkeypatch):
    seen = {}

    def _fake_pull_prototype(transport, *, slug, repo_root, commit):
        seen["called"] = "prototype"
        return _fake_pull_result()

    def _fake_pull_marp(*args, **kwargs):
        raise AssertionError("pull_marp_source must not run for --target prototype")

    monkeypatch.setattr(deck_pipeline, "pull_prototype", _fake_pull_prototype)
    monkeypatch.setattr(deck_pipeline, "pull_marp_source", _fake_pull_marp)

    cli.main(["deck", "pull", "pyforge-warden"])

    assert seen["called"] == "prototype"


def test_deck_pull_target_marp_deck_dispatches_to_pull_marp_source(monkeypatch):
    seen = {}

    def _fake_pull_prototype(*args, **kwargs):
        raise AssertionError("pull_prototype must not run for --target marp-deck")

    def _fake_pull_marp(transport, *, slug, repo_root, kind, commit):
        seen["slug"] = slug
        seen["kind"] = kind
        seen["commit"] = commit
        return _fake_pull_result(artifact="marp:deck")

    monkeypatch.setattr(deck_pipeline, "pull_prototype", _fake_pull_prototype)
    monkeypatch.setattr(deck_pipeline, "pull_marp_source", _fake_pull_marp)

    exit_code = cli.main(["deck", "pull", "pyforge-warden", "--target", "marp-deck"])

    assert exit_code == 0
    assert seen == {"slug": "pyforge-warden", "kind": "deck", "commit": False}


def test_deck_pull_target_marp_executive_summary_derives_the_right_kind(monkeypatch):
    seen = {}

    def _fake_pull_marp(transport, *, slug, repo_root, kind, commit):
        seen["kind"] = kind
        return _fake_pull_result(artifact=f"marp:{kind}")

    monkeypatch.setattr(deck_pipeline, "pull_marp_source", _fake_pull_marp)

    cli.main(["deck", "pull", "pyforge-warden", "--target", "marp-executive-summary"])

    assert seen["kind"] == "executive-summary"


def test_deck_pull_target_rejects_an_unknown_choice():
    assert cli.main(["deck", "pull", "pyforge-warden", "--target", "bogus"]) == 2


def test_deck_pull_target_standalone_dispatches_to_pull_standalone_bundle(
    monkeypatch,
):
    seen = {}

    def _fake_pull_prototype(*args, **kwargs):
        raise AssertionError("pull_prototype must not run for --target standalone")

    def _fake_pull_marp(*args, **kwargs):
        raise AssertionError("pull_marp_source must not run for --target standalone")

    def _fake_pull_standalone(transport, *, slug, repo_root, commit):
        seen["slug"] = slug
        seen["commit"] = commit
        return _fake_pull_result(artifact="standalone-bundle")

    monkeypatch.setattr(deck_pipeline, "pull_prototype", _fake_pull_prototype)
    monkeypatch.setattr(deck_pipeline, "pull_marp_source", _fake_pull_marp)
    monkeypatch.setattr(deck_pipeline, "pull_standalone_bundle", _fake_pull_standalone)

    exit_code = cli.main(["deck", "pull", "pyforge-warden", "--target", "standalone"])

    assert exit_code == 0
    assert seen == {"slug": "pyforge-warden", "commit": False}
