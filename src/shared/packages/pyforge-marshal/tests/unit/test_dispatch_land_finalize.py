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
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__.LocalFs",
        lambda: object(),
    )
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
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__.LocalFs",
        lambda: object(),
    )
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
    monkeypatch.setattr(
        "pyforge.marshal.dispatch_land_finalize.__main__.LocalFs",
        lambda: object(),
    )
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
