"""``herald deck sync-all [--slug SLUG] [--dry-run]`` CLI wiring (Story
23.6): argument parsing, composing ``bridge.run`` + ``sync_all.sync_all``
over the V1-default ``McpTransport``, and routing the result through
``dispatch`` (AD-6).

``sync_all.sync_all`` itself is monkeypatched here -- its own behavior is
``test_sync_all.py``'s job. What's under test is the CLI's own
composition: which arguments it forwards (``--slug``/``--repo-root``/
``--dry-run``), what it prints per deck (one line per deck's ``labels()``,
plus an ``error:`` line when a deck failed, plus a trailing ``published``
line), and that a raised ``HeraldError`` reaches ``dispatch`` unchanged.
Mirrors ``test_cli_push.py``'s own shape exactly.
"""

from __future__ import annotations

from pyforge.herald import cli
from pyforge.herald import sync_all as sync_all_module
from pyforge.herald.errors import HeraldError
from pyforge.herald.sync_all import DeckSyncReport, SyncAllReport


def test_deck_sync_all_help_exits_zero():
    assert cli.main(["deck", "sync-all", "--help"]) == 0


def test_deck_sync_all_forwards_slug_repo_root_and_dry_run(monkeypatch, tmp_path):
    seen = {}

    def _fake_sync_all(transport, *, slug, repo_root, dry_run, proof_dir=None):
        seen["transport"] = transport
        seen["slug"] = slug
        seen["repo_root"] = repo_root
        seen["dry_run"] = dry_run
        return SyncAllReport(decks=(), published=False)

    monkeypatch.setattr(sync_all_module, "sync_all", _fake_sync_all)

    exit_code = cli.main(
        [
            "deck",
            "sync-all",
            "--slug",
            "pyforge-warden",
            "--repo-root",
            str(tmp_path),
            "--dry-run",
        ]
    )

    assert exit_code == 0
    assert seen["slug"] == "pyforge-warden"
    assert seen["repo_root"] == tmp_path
    assert seen["dry_run"] is True


def test_deck_sync_all_forwards_proof_dir_when_the_gate_is_satisfied(monkeypatch, tmp_path):
    """Story 24.3: with ``HERALD_LIVE_SYNC_PROOF=1`` set, ``--proof-dir`` is
    forwarded straight through to ``sync_all.sync_all`` as a keyword."""
    seen = {}

    def _fake_sync_all(transport, *, slug, repo_root, dry_run, proof_dir=None):
        seen["proof_dir"] = proof_dir
        return SyncAllReport(decks=(), published=False)

    monkeypatch.setattr(sync_all_module, "sync_all", _fake_sync_all)
    monkeypatch.setenv("HERALD_LIVE_SYNC_PROOF", "1")
    proof_dir = tmp_path / "proof"

    exit_code = cli.main(["deck", "sync-all", "--proof-dir", str(proof_dir)])

    assert exit_code == 0
    assert seen["proof_dir"] == proof_dir


def test_deck_sync_all_proof_dir_refused_without_the_gate_env_var(monkeypatch, capsys):
    """Story 24.3: ``--proof-dir`` with the gate env var unset is refused
    before any transport/Design call is made -- ``sync_all`` must never be
    reached."""

    def _fake_sync_all(transport, *, slug, repo_root, dry_run, proof_dir=None):
        raise AssertionError("sync_all must not be called when the gate refuses")

    monkeypatch.setattr(sync_all_module, "sync_all", _fake_sync_all)
    monkeypatch.delenv("HERALD_LIVE_SYNC_PROOF", raising=False)

    exit_code = cli.main(["deck", "sync-all", "--proof-dir", "/tmp/proof"])

    assert exit_code == 1
    assert "HERALD_LIVE_SYNC_PROOF" in capsys.readouterr().err


def test_deck_sync_all_proof_dir_refused_when_the_gate_env_var_is_not_1(monkeypatch, capsys):
    """Story 24.3: the gate checks for the exact string ``"1"`` -- any other
    value (e.g. left over from an unrelated ``0``/``true``) still refuses."""

    def _fake_sync_all(transport, *, slug, repo_root, dry_run, proof_dir=None):
        raise AssertionError("sync_all must not be called when the gate refuses")

    monkeypatch.setattr(sync_all_module, "sync_all", _fake_sync_all)
    monkeypatch.setenv("HERALD_LIVE_SYNC_PROOF", "true")

    exit_code = cli.main(["deck", "sync-all", "--proof-dir", "/tmp/proof"])

    assert exit_code == 1
    assert "HERALD_LIVE_SYNC_PROOF" in capsys.readouterr().err


def test_deck_sync_all_without_proof_dir_never_requires_the_gate(monkeypatch):
    """Regression guard: omitting ``--proof-dir`` entirely must behave
    identically to before this story, gate env var or not."""

    def _fake_sync_all(transport, *, slug, repo_root, dry_run, proof_dir=None):
        assert proof_dir is None
        return SyncAllReport(decks=(), published=False)

    monkeypatch.setattr(sync_all_module, "sync_all", _fake_sync_all)
    monkeypatch.delenv("HERALD_LIVE_SYNC_PROOF", raising=False)

    exit_code = cli.main(["deck", "sync-all"])

    assert exit_code == 0


def test_deck_sync_all_gate_env_var_set_but_proof_dir_omitted_is_the_ordinary_path(monkeypatch, tmp_path):
    """Story 24.3: ``HERALD_LIVE_SYNC_PROOF=1`` being set incidentally must
    not change the ordinary sync path when ``--proof-dir`` is not given --
    the gate only fires when ``--proof-dir`` is present."""
    seen = {}

    def _fake_sync_all(transport, *, slug, repo_root, dry_run, proof_dir=None):
        seen["proof_dir"] = proof_dir
        return SyncAllReport(decks=(), published=False)

    monkeypatch.setattr(sync_all_module, "sync_all", _fake_sync_all)
    monkeypatch.setenv("HERALD_LIVE_SYNC_PROOF", "1")
    monkeypatch.chdir(tmp_path)

    exit_code = cli.main(["deck", "sync-all"])

    assert exit_code == 0
    assert seen["proof_dir"] is None
    assert not (tmp_path / ".herald" / "sync-proof").exists()


def test_deck_sync_all_default_slug_is_none_and_dry_run_is_false(monkeypatch, tmp_path):
    seen = {}

    def _fake_sync_all(transport, *, slug, repo_root, dry_run, proof_dir=None):
        seen["slug"] = slug
        seen["dry_run"] = dry_run
        return SyncAllReport(decks=(), published=False)

    monkeypatch.setattr(sync_all_module, "sync_all", _fake_sync_all)
    monkeypatch.chdir(tmp_path)

    cli.main(["deck", "sync-all"])

    assert seen["slug"] is None
    assert seen["dry_run"] is False


def test_deck_sync_all_default_repo_root_is_cwd(monkeypatch, tmp_path):
    seen = {}

    def _fake_sync_all(transport, *, slug, repo_root, dry_run, proof_dir=None):
        seen["repo_root"] = repo_root
        return SyncAllReport(decks=(), published=False)

    monkeypatch.setattr(sync_all_module, "sync_all", _fake_sync_all)
    monkeypatch.chdir(tmp_path)

    cli.main(["deck", "sync-all"])

    assert seen["repo_root"] == tmp_path


def test_deck_sync_all_prints_one_line_per_deck_with_its_labels(monkeypatch, capsys):
    def _fake_sync_all(transport, *, slug, repo_root, dry_run, proof_dir=None):
        return SyncAllReport(
            decks=(
                DeckSyncReport(slug="pyforge-warden", pulled=("prototype",)),
                DeckSyncReport(slug="pyforge-doctor"),
            ),
            published=False,
        )

    monkeypatch.setattr(sync_all_module, "sync_all", _fake_sync_all)

    exit_code = cli.main(["deck", "sync-all"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "pyforge-warden: pulled" in out
    assert "pyforge-doctor: unchanged" in out


def test_deck_sync_all_prints_a_message_when_no_decks_are_found(monkeypatch, capsys):
    """Review fix: an empty ``SyncAllReport`` (e.g. ``--repo-root``/cwd has
    no ``presentations/`` dir) must not print nothing at exit 0 --
    indistinguishable from "everything already synced"."""

    def _fake_sync_all(transport, *, slug, repo_root, dry_run, proof_dir=None):
        return SyncAllReport(decks=(), published=False)

    monkeypatch.setattr(sync_all_module, "sync_all", _fake_sync_all)

    exit_code = cli.main(["deck", "sync-all"])

    assert exit_code == 0
    assert capsys.readouterr().out.strip() == "no registered decks found"


def test_deck_sync_all_prints_the_error_line_for_a_failed_deck(monkeypatch, capsys):
    def _fake_sync_all(transport, *, slug, repo_root, dry_run, proof_dir=None):
        return SyncAllReport(
            decks=(DeckSyncReport(slug="pyforge-warden", error="deck-facts --refresh failed: boom"),),
            published=False,
        )

    monkeypatch.setattr(sync_all_module, "sync_all", _fake_sync_all)

    exit_code = cli.main(["deck", "sync-all"])

    assert exit_code == 0  # per-deck failure is reported, never gates the run
    out = capsys.readouterr().out
    assert "pyforge-warden: failed" in out
    assert "error: deck-facts --refresh failed: boom" in out


def test_deck_sync_all_prints_a_published_line_when_the_site_was_rebuilt(monkeypatch, capsys):
    def _fake_sync_all(transport, *, slug, repo_root, dry_run, proof_dir=None):
        return SyncAllReport(
            decks=(DeckSyncReport(slug="pyforge-warden", pushed=("a.html",), published=True),),
            published=True,
        )

    monkeypatch.setattr(sync_all_module, "sync_all", _fake_sync_all)

    cli.main(["deck", "sync-all"])

    out = capsys.readouterr().out
    assert "published: dossier site rebuilt" in out


def test_deck_sync_all_no_published_line_when_nothing_changed(monkeypatch, capsys):
    def _fake_sync_all(transport, *, slug, repo_root, dry_run, proof_dir=None):
        return SyncAllReport(decks=(DeckSyncReport(slug="pyforge-warden"),), published=False)

    monkeypatch.setattr(sync_all_module, "sync_all", _fake_sync_all)

    cli.main(["deck", "sync-all"])

    out = capsys.readouterr().out
    assert "published" not in out


def test_deck_sync_all_prints_the_publish_error_when_publish_failed(monkeypatch, capsys):
    def _fake_sync_all(transport, *, slug, repo_root, dry_run, proof_dir=None):
        return SyncAllReport(
            decks=(DeckSyncReport(slug="pyforge-warden", pushed=("a.html",)),),
            published=False,
            publish_error="site publish failed: template error",
        )

    monkeypatch.setattr(sync_all_module, "sync_all", _fake_sync_all)

    exit_code = cli.main(["deck", "sync-all"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "publish failed: site publish failed: template error" in out
    assert "published: dossier site rebuilt" not in out


def test_deck_sync_all_herald_error_propagates_through_dispatch(monkeypatch, capsys):
    def _fake_sync_all(transport, *, slug, repo_root, dry_run, proof_dir=None):
        raise HeraldError("presentations/nope not found")

    monkeypatch.setattr(sync_all_module, "sync_all", _fake_sync_all)

    exit_code = cli.main(["deck", "sync-all", "--slug", "nope"])

    assert exit_code == 1
    assert "presentations/nope not found" in capsys.readouterr().err
