"""dispatch_land_finalize must pass CAP-5 ``base=`` into ledger promote."""

from __future__ import annotations

from pathlib import Path

from pyforge.marshal.dispatch_land_finalize.__main__ import finalize_dispatch_land


def test_finalize_passes_base_main_to_isolated_promote(
    tmp_path: Path, monkeypatch
) -> None:
    seen: dict[str, object] = {}

    class _Scan:
        findings: list = []
        plan = None

    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__.repo_root",
        lambda: tmp_path,
    )
    # Story 51.9: `LocalFs` is left unstubbed (real class, real `tmp_path`)
    # because the new `_resync_home_branch` + `deploy_run.write(...)`
    # observation write now exercises real fs operations; `GitVcs` stays a
    # bare `object()` stub since `_resync_home_branch` itself is
    # monkeypatched to a no-op below.
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__.GitVcs",
        lambda: object(),
    )
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._scan_promotions",
        lambda *args, **kwargs: _Scan(),
    )

    def _capture(*args, **kwargs):
        seen["args"] = args
        seen["kwargs"] = kwargs
        return ()

    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._promote_sprint_ledger",
        _capture,
    )
    # Story 51.9: a bare `object()`-stubbed `GitVcs` has no `resolve_ref`/
    # `worktree_head_sha` -- an unstubbed `_resync_home_branch` call would
    # raise `AttributeError` and break this test, which isn't exercising
    # the resync behavior at all.
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._resync_home_branch",
        lambda *args, **kwargs: True,
    )

    assert finalize_dispatch_land("pyforge-steward", "42.5") == 0
    assert seen["kwargs"]["base"] == "main"


def test_finalize_forwards_worktree_to_scan_promotions(
    tmp_path: Path, monkeypatch
) -> None:
    """Story 51.2: the landing record follows the session's write, not the
    primary's directory. When a worktree is given, ``finalize_dispatch_land``
    must thread it into ``_scan_promotions`` so a spec written into the
    dispatch worktree's own Tier-3 dir is still discoverable before
    teardown."""
    seen: dict[str, object] = {}

    class _Scan:
        findings: list = []
        plan = None

    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__.repo_root",
        lambda: tmp_path,
    )
    # Story 51.9: `LocalFs` is left unstubbed (real class, real `tmp_path`)
    # because the new `_resync_home_branch` + `deploy_run.write(...)`
    # observation write now exercises real fs operations; `GitVcs` stays a
    # bare `object()` stub since `_resync_home_branch` itself is
    # monkeypatched to a no-op below.
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__.GitVcs",
        lambda: object(),
    )

    def _capture_scan(*args, **kwargs):
        seen["scan_kwargs"] = kwargs
        return _Scan()

    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._scan_promotions",
        _capture_scan,
    )
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._promote_sprint_ledger",
        lambda *args, **kwargs: (),
    )
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._resync_home_branch",
        lambda *args, **kwargs: True,
    )

    worktree = tmp_path / "some-worktree"
    assert finalize_dispatch_land("pyforge-steward", "42.5", worktree) == 0
    assert seen["scan_kwargs"]["worktree"] == worktree


def test_finalize_defaults_worktree_to_none(tmp_path: Path, monkeypatch) -> None:
    """Omitting ``worktree`` must still thread a literal ``None`` into
    ``_scan_promotions`` (byte-identical to pre-51.2 behavior)."""
    seen: dict[str, object] = {}

    class _Scan:
        findings: list = []
        plan = None

    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__.repo_root",
        lambda: tmp_path,
    )
    # Story 51.9: `LocalFs` is left unstubbed (real class, real `tmp_path`)
    # because the new `_resync_home_branch` + `deploy_run.write(...)`
    # observation write now exercises real fs operations; `GitVcs` stays a
    # bare `object()` stub since `_resync_home_branch` itself is
    # monkeypatched to a no-op below.
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__.GitVcs",
        lambda: object(),
    )

    def _capture_scan(*args, **kwargs):
        seen["scan_kwargs"] = kwargs
        return _Scan()

    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._scan_promotions",
        _capture_scan,
    )
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._promote_sprint_ledger",
        lambda *args, **kwargs: (),
    )
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._resync_home_branch",
        lambda *args, **kwargs: True,
    )

    assert finalize_dispatch_land("pyforge-steward", "42.5") == 0
    assert seen["scan_kwargs"]["worktree"] is None


def test_finalize_resyncs_the_primary_after_ledger_promotion(
    tmp_path: Path, monkeypatch
) -> None:
    """Story 51.9 (re-mint of 51.3): `_promote_sprint_ledger` never touches
    the primary checkout's own working tree (CAP-5), so nothing else picked
    up that promotion either. `dispatch_land_finalize` must reuse
    `_resync_home_branch` VERBATIM, immediately after the ledger promotion,
    to fast-forward the primary checkout (``root``) onto `origin/main`'s
    tip whenever it is safely a clean `main` at its own tip."""
    seen: dict[str, object] = {}

    class _Scan:
        findings: list = []
        plan = None

    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__.repo_root",
        lambda: tmp_path,
    )
    # Story 51.9: `LocalFs` is left unstubbed (real class, real `tmp_path`)
    # because the new `_resync_home_branch` + `deploy_run.write(...)`
    # observation write now exercises real fs operations; `GitVcs` stays a
    # bare `object()` stub since `_resync_home_branch` itself is
    # monkeypatched to a no-op below.
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__.GitVcs",
        lambda: object(),
    )
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._scan_promotions",
        lambda *args, **kwargs: _Scan(),
    )
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._promote_sprint_ledger",
        lambda *args, **kwargs: (),
    )

    def _capture_resync(*args, **kwargs):
        seen["resync_args"] = args
        return True

    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__._resync_home_branch",
        _capture_resync,
    )

    assert finalize_dispatch_land("pyforge-steward", "42.5") == 0
    assert "resync_args" in seen
    (
        _vcs,
        resync_enabled,
        merge_strategy,
        git_repo_root,
        home,
        base,
        head_branch,
        _findings,
    ) = seen["resync_args"]
    assert resync_enabled is True
    assert merge_strategy == "merge"
    assert git_repo_root == tmp_path
    assert home == tmp_path
    assert base == "main"
    assert head_branch == "main"
