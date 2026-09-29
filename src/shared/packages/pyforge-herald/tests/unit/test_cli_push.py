"""``herald deck push <slug>`` CLI wiring (Story 5.1, extended by Story
23.6's ``--prove``): argument parsing, composing ``bridge.run`` +
``deck_pipeline.push_exports`` over the V1-default ``McpTransport``, and
routing the result through ``dispatch`` (AD-6).

``deck_pipeline.push_exports`` itself is monkeypatched here -- its own
behavior is ``test_deck_pipeline.py``'s job. What's under test is the CLI's
own composition: which arguments it forwards (including ``--prove``), what
it prints on success (the "nothing to push"/"pushed N" shapes, plus one
line per proven file), and that a raised ``HeraldError`` (including
``ExportConflictError``, Story 5.2, and ``ReadBackMismatchError``, Story
23.6) reaches ``dispatch`` unchanged. Mirrors ``test_cli_pull.py``'s own
shape exactly.
"""

from __future__ import annotations

from pathlib import Path

from pyforge.herald import cli, deck_pipeline
from pyforge.herald.errors import ExportConflictError, HeraldError, ReadBackMismatchError


def _fake_push_result(**overrides):
    defaults = {"slug": "pyforge-warden", "pushed": (), "skipped": (), "proven": ()}
    defaults.update(overrides)
    return deck_pipeline.ExportPushResult(**defaults)


def test_deck_push_help_exits_zero():
    assert cli.main(["deck", "push", "--help"]) == 0


def test_deck_push_missing_slug_is_a_usage_error():
    assert cli.main(["deck", "push"]) == 2


def test_deck_push_success_prints_the_pushed_and_skipped_counts_and_returns_0(monkeypatch, capsys, tmp_path: Path):
    seen = {}

    def _fake_push(transport, *, slug, repo_root, prove=False):
        seen["slug"] = slug
        seen["repo_root"] = repo_root
        seen["transport"] = transport
        seen["prove"] = prove
        return _fake_push_result(pushed=("a.html",), skipped=("b.html",))

    monkeypatch.setattr(deck_pipeline, "push_exports", _fake_push)

    exit_code = cli.main(["deck", "push", "pyforge-warden", "--repo-root", str(tmp_path)])

    assert exit_code == 0
    assert seen["slug"] == "pyforge-warden"
    assert seen["repo_root"] == tmp_path
    assert seen["prove"] is False
    out = capsys.readouterr().out
    assert "pyforge-warden" in out
    assert "1 file(s) pushed" in out
    assert "1 unchanged" in out


def test_deck_push_nothing_to_push_reports_that_and_returns_0(monkeypatch, capsys):
    def _fake_push(transport, *, slug, repo_root, prove=False):
        return _fake_push_result()

    monkeypatch.setattr(deck_pipeline, "push_exports", _fake_push)

    exit_code = cli.main(["deck", "push", "pyforge-warden"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "nothing to push" in out


def test_deck_push_default_repo_root_is_cwd(monkeypatch, tmp_path):
    seen = {}

    def _fake_push(transport, *, slug, repo_root, prove=False):
        seen["repo_root"] = repo_root
        return _fake_push_result()

    monkeypatch.setattr(deck_pipeline, "push_exports", _fake_push)
    monkeypatch.chdir(tmp_path)

    cli.main(["deck", "push", "pyforge-warden"])

    assert seen["repo_root"] == tmp_path


def test_deck_push_conflict_error_reaches_dispatch_and_returns_its_exit_code(monkeypatch, capsys):
    def _fake_push(transport, *, slug, repo_root, prove=False):
        raise ExportConflictError("conflict on a.html")

    monkeypatch.setattr(deck_pipeline, "push_exports", _fake_push)

    exit_code = cli.main(["deck", "push", "pyforge-warden"])

    assert exit_code == 3  # errors.exit_code_for(ExportConflictError) == 3
    err = capsys.readouterr().err
    assert "ExportConflictError" in err
    assert "conflict on a.html" in err


def test_deck_push_herald_error_propagates_through_dispatch(monkeypatch, capsys):
    def _fake_push(transport, *, slug, repo_root, prove=False):
        raise HeraldError("no bridge state recorded")

    monkeypatch.setattr(deck_pipeline, "push_exports", _fake_push)

    exit_code = cli.main(["deck", "push", "pyforge-warden"])

    assert exit_code == 1
    assert "no bridge state recorded" in capsys.readouterr().err


# --- Story 23.4: --prove ------------------------------------------------------


def test_deck_push_default_prove_is_false(monkeypatch):
    seen = {}

    def _fake_push(transport, *, slug, repo_root, prove=False):
        seen["prove"] = prove
        return _fake_push_result()

    monkeypatch.setattr(deck_pipeline, "push_exports", _fake_push)

    cli.main(["deck", "push", "pyforge-warden"])

    assert seen["prove"] is False


def test_deck_push_prove_flag_is_forwarded(monkeypatch):
    seen = {}

    def _fake_push(transport, *, slug, repo_root, prove=False):
        seen["prove"] = prove
        return _fake_push_result()

    monkeypatch.setattr(deck_pipeline, "push_exports", _fake_push)

    cli.main(["deck", "push", "pyforge-warden", "--prove"])

    assert seen["prove"] is True


def test_deck_push_prove_prints_one_line_per_proven_file(monkeypatch, capsys):
    def _fake_push(transport, *, slug, repo_root, prove=False):
        return _fake_push_result(
            pushed=("a.pptx", "b.pptx"),
            proven=("a.pptx", "b.pptx"),
        )

    monkeypatch.setattr(deck_pipeline, "push_exports", _fake_push)

    exit_code = cli.main(["deck", "push", "pyforge-warden", "--prove"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "a.pptx" in out
    assert "b.pptx" in out


def test_deck_push_no_prove_prints_no_proven_lines(monkeypatch, capsys):
    def _fake_push(transport, *, slug, repo_root, prove=False):
        return _fake_push_result(pushed=("a.html",))

    monkeypatch.setattr(deck_pipeline, "push_exports", _fake_push)

    cli.main(["deck", "push", "pyforge-warden"])

    out = capsys.readouterr().out
    assert "proved" not in out


def test_deck_push_read_back_mismatch_reaches_dispatch_and_returns_its_exit_code(monkeypatch, capsys):
    def _fake_push(transport, *, slug, repo_root, prove=False):
        raise ReadBackMismatchError("read-back mismatch for a.pptx")

    monkeypatch.setattr(deck_pipeline, "push_exports", _fake_push)

    exit_code = cli.main(["deck", "push", "pyforge-warden", "--prove"])

    assert exit_code == 1  # ReadBackMismatchError falls through to the default
    err = capsys.readouterr().err
    assert "ReadBackMismatchError" in err
    assert "a.pptx" in err
