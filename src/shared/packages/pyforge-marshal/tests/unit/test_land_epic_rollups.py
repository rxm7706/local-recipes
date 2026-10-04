"""Story 83.21: the landing finalize writes the epic roll-ups the sync writes.

``cli/land.py::_promote_sprint_ledger`` -- the one writer of the tracked ``sprint-status-ledger.yaml``
that ``marshal land`` and ``dispatch_land_finalize`` share -- synced the Tier-3 feed into the twin with
the sync's ``render`` and then advanced the landed story, but never applied the sync's own
``apply_epic_rollups``. A stale feed ``epic-N`` row therefore overwrote the roll-up: doctor 41.5's
landing (``b9869e5c6d``) moved ``epic-41`` from ``in-progress`` to ``backlog``, and three landings on
2026-10-03 dropped done epics to ``backlog``.

Every test here runs ``finalize_dispatch_land`` end to end against REAL git -- a bare ``origin``, the
primary clone, and (where the primary's own copy is stale) a second clone that moved ``origin/main``
first -- with the real ``_promote_sprint_ledger`` and the real ``GitVcs``. Only the steps around the
promotion are stubbed (the promotion scan, the primary's resync, the deferred-work intake). The oracle
for "what ``sprint-ledger-sync`` writes" is the sync module's own ``apply_epic_rollups`` + ``render``,
the two calls its ``main()`` makes before every write.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import types
from pathlib import Path

import pytest

from pyforge.marshal.cli import land as land_module
from pyforge.marshal.dispatch_land_finalize import __main__ as finalize_module
from pyforge.marshal.dispatch_land_finalize.__main__ import _FINALIZE_RESYNC_KIND, finalize_dispatch_land

_SLUG = "pyforge-marshal"
_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _ledger_rel(slug: str) -> str:
    return f"_bmad-output/projects/{slug}/planning-artifacts/sprint-status-ledger.yaml"


def _feed_rel(slug: str) -> str:
    return f"_bmad-output/projects/{slug}/implementation-artifacts/sprint-status.yaml"


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    return result.stdout


def _configure(repo: Path) -> None:
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "commit.gpgsign", "false")
    _git(repo, "config", "core.hooksPath", "/dev/null")  # never the machine's own pre-push hook


def _sync() -> object:
    """``scripts/promote_sprint_status.py`` -- the module ``sprint-ledger-sync`` runs."""
    module = land_module._load_promote_sprint_status_module()
    assert module is not None, "scripts/promote_sprint_status.py must load -- the ACs are stated in its terms"
    return module


def _sync_render(slug: str, statuses: dict[str, str]) -> str:
    """The twin text ``sprint-ledger-sync`` writes for ``statuses``: its roll-up, then its render."""
    sync = _sync()
    return sync.render(slug.removeprefix("pyforge-"), _feed_rel(slug), sync.apply_epic_rollups(dict(statuses)))


def _plain_render(slug: str, statuses: dict[str, str]) -> str:
    """The sync's render with NO roll-up -- a twin text that carries exactly ``statuses``."""
    return _sync().render(slug.removeprefix("pyforge-"), _feed_rel(slug), statuses)


def _feed_text(statuses: dict[str, str]) -> str:
    body = "".join(f"  {key}: {value}\n" for key, value in statuses.items())
    return f"generated: 2026-10-04T00:00:00Z\nproject: test\ndevelopment_status:\n{body}"


def _statuses(text: str) -> dict[str, str]:
    return land_module._parse_sprint_ledger_statuses(text)


def _blob_sha(text: str) -> str:
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def _estate(tmp_path: Path, slug: str, origin_twin: str, *, primary_twin: str | None = None) -> tuple[Path, Path]:
    """A bare ``origin`` and the primary clone, both holding ``origin_twin`` as the tracked ledger.

    With ``primary_twin``, the primary commits and pushes THAT text, and a second clone then moves
    ``origin/main`` to ``origin_twin`` without the primary fetching -- the primary's on-disk copy is
    behind ``origin/main``, as it is after any promotion published straight onto ``origin`` (CAP-5)."""
    origin = tmp_path / "origin.git"
    origin.mkdir()
    _git(origin, "init", "--bare", "-b", "main")
    primary = tmp_path / "primary"
    primary.mkdir()
    _git(primary, "init", "-b", "main")
    _configure(primary)
    (primary / ".gitignore").write_text("_bmad-output/projects/*/implementation-artifacts/\n", encoding="utf-8")
    ledger = primary / _ledger_rel(slug)
    ledger.parent.mkdir(parents=True)
    ledger.write_text(primary_twin if primary_twin is not None else origin_twin, encoding="utf-8")
    _git(primary, "add", ".gitignore", _ledger_rel(slug))
    _git(primary, "commit", "-m", "base")
    _git(primary, "remote", "add", "origin", str(origin))
    _git(primary, "push", "-u", "origin", "main")
    if primary_twin is not None:
        other = tmp_path / "other"
        _git(tmp_path, "clone", str(origin), str(other))
        _configure(other)
        (other / _ledger_rel(slug)).write_text(origin_twin, encoding="utf-8")
        _git(other, "commit", "-am", "sprint-ledger-sync: roll the epics up")
        _git(other, "push", "origin", "main")
    return origin, primary


def _write_feed(primary: Path, slug: str, text: str) -> None:
    feed = primary / _feed_rel(slug)
    feed.parent.mkdir(parents=True, exist_ok=True)
    feed.write_text(text, encoding="utf-8")


class _NoScan:
    findings: list = []
    plan = None


def _finalize(monkeypatch, primary: Path, slug: str, key: str) -> int:
    """``finalize_dispatch_land`` over the real promotion and real git; only the scan, the resync and the
    deferred-work intake are stubbed (none of them writes the sprint ledger)."""
    monkeypatch.setattr(finalize_module, "repo_root", lambda: primary)
    monkeypatch.setattr(finalize_module, "_scan_promotions", lambda *a, **k: _NoScan())
    monkeypatch.setattr(finalize_module, "_resync_home_branch", lambda *a, **k: True)
    monkeypatch.setattr(finalize_module, "_run_deferred_work_intake", lambda *a, **k: None)
    return finalize_dispatch_land(slug, key)


def _origin_text(origin: Path, slug: str, rev: str = "main") -> str:
    return _git(origin, "show", f"{rev}:{_ledger_rel(slug)}")


def _observation_findings(primary: Path, slug: str) -> list[dict]:
    runs = primary / "_bmad-output" / "projects" / slug / "implementation-artifacts" / "runs"
    [run_dir] = list(runs.iterdir())
    entries = [json.loads(line) for line in (run_dir / "journal.jsonl").read_text(encoding="utf-8").splitlines()]
    [observation] = [entry for entry in entries if entry["kind"] == _FINALIZE_RESYNC_KIND]
    return observation["payload"]["findings"]


def _assert_promotion_commit(origin: Path, parent_sha: str) -> str:
    """``origin/main`` moved by exactly one ledger promotion commit on top of ``parent_sha``; its sha."""
    assert _git(origin, "rev-parse", "main~1").strip() == parent_sha
    assert _git(origin, "log", "-1", "--format=%s", "main").startswith("marshal: promote sprint-status ledger")
    return _git(origin, "rev-parse", "main").strip()


# -- AC 1: a stale feed epic row is published as the sync's roll-up -------------------------------------------

_E9_IN_PROGRESS_TWIN = {
    "9-1-the-first-story": "review",
    "9-2-the-second-story": "in-progress",
    "epic-9": "in-progress",
}


def test_a_stale_backlog_feed_epic_row_is_published_as_the_syncs_in_progress_roll_up(
    tmp_path: Path, monkeypatch
) -> None:
    """AC 1: the feed's ``epic-9`` reads ``backlog`` while its stories read ``done`` (once 9.1 lands) and
    ``in-progress``. The twin ``epic-9`` reads ``in-progress`` -- and the whole published twin is byte for
    byte what ``sprint-ledger-sync`` writes for the same statuses."""
    origin, primary = _estate(tmp_path, _SLUG, _plain_render(_SLUG, _E9_IN_PROGRESS_TWIN))
    feed_statuses = {**_E9_IN_PROGRESS_TWIN, "epic-9": "backlog"}
    _write_feed(primary, _SLUG, _feed_text(feed_statuses))
    parent = _git(origin, "rev-parse", "main").strip()

    assert _finalize(monkeypatch, primary, _SLUG, "9.1") == 0

    _assert_promotion_commit(origin, parent)
    published = _origin_text(origin, _SLUG)
    assert _statuses(published) == {
        "9-1-the-first-story": "done",
        "9-2-the-second-story": "in-progress",
        "epic-9": "in-progress",
    }
    assert published == _sync_render(_SLUG, {**feed_statuses, "9-1-the-first-story": "done"})


# -- AC 2: the last open story promoted to done rolls its epic to done ----------------------------------------

_E9_LAST_OPEN_TWIN = {
    "9-1-the-first-story": "done",
    "9-2-the-second-story": "review",
    "epic-9": "in-progress",
}


def test_the_last_open_story_promoted_to_done_rolls_its_epic_to_done(tmp_path: Path, monkeypatch) -> None:
    """AC 2: 9.2 is the last open story of epic 9; once the finalize advances it, ``epic-9`` reads ``done``."""
    origin, primary = _estate(tmp_path, _SLUG, _plain_render(_SLUG, _E9_LAST_OPEN_TWIN))
    _write_feed(primary, _SLUG, _feed_text(_E9_LAST_OPEN_TWIN))
    parent = _git(origin, "rev-parse", "main").strip()

    assert _finalize(monkeypatch, primary, _SLUG, "9.2") == 0

    _assert_promotion_commit(origin, parent)
    published = _origin_text(origin, _SLUG)
    assert _statuses(published)["epic-9"] == "done"
    assert published == _sync_render(_SLUG, {**_E9_LAST_OPEN_TWIN, "9-2-the-second-story": "done"})


def test_with_no_feed_at_all_the_advancement_still_rolls_its_epic_up(tmp_path: Path, monkeypatch) -> None:
    """AC 2 on the other branch: no Tier-3 feed, so nothing is synced and the twin is advanced in place --
    the roll-up still runs over the final statuses, after the advancement."""
    origin, primary = _estate(tmp_path, _SLUG, _plain_render(_SLUG, _E9_LAST_OPEN_TWIN))
    parent = _git(origin, "rev-parse", "main").strip()

    assert _finalize(monkeypatch, primary, _SLUG, "9.2") == 0

    _assert_promotion_commit(origin, parent)
    assert _statuses(_origin_text(origin, _SLUG)) == {
        "9-1-the-first-story": "done",
        "9-2-the-second-story": "done",
        "epic-9": "done",
    }


# -- AC 3: a done epic keeps done over a stale feed row; the promotion commit regresses nothing ---------------

#: ``origin/main``: epic 9 finished and rolled up to ``done``; 10.1 is landing.
_AC3_ORIGIN_TWIN = {
    "9-1-the-first-story": "done",
    "9-2-the-second-story": "done",
    "epic-9": "done",
    "10-1-the-landing-story": "review",
    "epic-10": "in-progress",
}
#: The primary's own copy, from before 9.2's promotion and the roll-up reached ``origin/main`` -- so the
#: sync's refusal guard (which reads this copy) has no ``done`` epic to protect.
_AC3_PRIMARY_TWIN = {
    "9-1-the-first-story": "done",
    "9-2-the-second-story": "review",
    "epic-9": "in-progress",
    "10-1-the-landing-story": "backlog",
    "epic-10": "backlog",
}
#: The feed: every story current, every epic row stale.
_AC3_FEED = {
    "9-1-the-first-story": "done",
    "9-2-the-second-story": "done",
    "epic-9": "backlog",
    "10-1-the-landing-story": "review",
    "epic-10": "backlog",
}


def _ac3_finalize(tmp_path: Path, monkeypatch) -> tuple[Path, Path, str, str]:
    origin, primary = _estate(
        tmp_path,
        _SLUG,
        _plain_render(_SLUG, _AC3_ORIGIN_TWIN),
        primary_twin=_plain_render(_SLUG, _AC3_PRIMARY_TWIN),
    )
    _write_feed(primary, _SLUG, _feed_text(_AC3_FEED))
    parent = _git(origin, "rev-parse", "main").strip()
    assert _finalize(monkeypatch, primary, _SLUG, "10.1") == 0
    return origin, primary, parent, _assert_promotion_commit(origin, parent)


def test_a_done_epic_keeps_done_over_a_stale_feed_row_and_the_promotion_commit_regresses_nothing(
    tmp_path: Path, monkeypatch
) -> None:
    """AC 3 (the 2026-10-03 shape: ``1be676d263``, ``fd328844d6``, ``cc137c9faa``): ``epic-9`` is done on
    ``origin/main`` with every story done, the feed row reads ``backlog``, and the primary's stale copy
    lets the feed sync through. The twin keeps ``epic-9: done`` (and 10.1's epic rolls to ``done``); no key
    of the promotion commit's parent that reads ``done`` reads anything else after it -- the rule
    ``ledger-regression`` judges, read here through the sync's own ``regressions``."""
    origin, _primary, parent, commit = _ac3_finalize(tmp_path, monkeypatch)

    before = _statuses(_origin_text(origin, _SLUG, parent))
    after = _statuses(_origin_text(origin, _SLUG, commit))
    assert after["epic-9"] == "done"
    assert after["epic-10"] == "done"
    assert after["10-1-the-landing-story"] == "done"
    assert _sync().regressions(before, after) == []


def test_ledger_regression_reports_ok_over_the_ac3_promotion_commit(tmp_path: Path, monkeypatch) -> None:
    """AC 3, through the ``ledger-regression`` detector itself (doctor's ``sources.ledger.gather``) over the
    promotion commit's own range. Runs where ``pyforge-doctor`` is installed (the guild env); the
    rule-level twin above runs everywhere."""
    ledger_source = pytest.importorskip("pyforge.doctor.sources.ledger")
    models = pytest.importorskip("pyforge.doctor.models")
    _origin, primary, parent, commit = _ac3_finalize(tmp_path, monkeypatch)
    _git(primary, "fetch", "origin", "main")

    [finding] = ledger_source.gather(primary, base=parent, head=commit)

    assert finding.status == models.DoctorStatus.OK, finding.message
    assert finding.evidence["ledgers_compared"] == 1


# -- AC 4: the promotion module cannot be loaded ---------------------------------------------------------------


def _without_rollup() -> object:
    """The real sync module minus ``apply_epic_rollups`` -- an older script that predates Story 28.24."""
    sync = _sync()
    return types.SimpleNamespace(**{k: v for k, v in vars(sync).items() if k != "apply_epic_rollups"})


def _raising_load(monkeypatch, tmp_path: Path) -> None:
    """Make the REAL loader exec a script that raises -- it must answer ``None``, never crash the finalize."""
    broken = tmp_path / "broken_promote_sprint_status.py"
    broken.write_text("raise RuntimeError('half-written script')\n", encoding="utf-8")
    real = importlib.util.spec_from_file_location

    def _redirect(name, location, *args, **kwargs):
        if name == "_promote_sprint_status_land":
            return real(name, broken)
        return real(name, location, *args, **kwargs)

    monkeypatch.setattr(importlib.util, "spec_from_file_location", _redirect)


@pytest.mark.parametrize("shape", ["missing", "no-rollup", "raises-on-load"])
def test_an_unloadable_promotion_module_writes_no_uncomputed_epic_row_and_journals_a_warn(
    tmp_path: Path, monkeypatch, shape: str
) -> None:
    """AC 4: with no usable ``apply_epic_rollups`` (the script missing, an older script without it, or one
    that raises while it loads) the finalize still advances 9.1 -- but the feed is not synced, so its stale
    ``epic-9: backlog`` and its feed-only row never reach the twin; ``epic-9`` stays the twin's own
    ``in-progress``. An ``MRS-LAND-011`` WARN naming the missing roll-up is on the finalize's journal."""
    origin, primary = _estate(tmp_path, _SLUG, _plain_render(_SLUG, _E9_IN_PROGRESS_TWIN))
    _write_feed(
        primary,
        _SLUG,
        _feed_text({**_E9_IN_PROGRESS_TWIN, "epic-9": "backlog", "9-3-a-feed-only-story": "backlog"}),
    )
    if shape == "missing":
        monkeypatch.setattr(land_module, "_load_promote_sprint_status_module", lambda: None)
    elif shape == "no-rollup":
        stub = _without_rollup()
        monkeypatch.setattr(land_module, "_load_promote_sprint_status_module", lambda: stub)
    else:
        _raising_load(monkeypatch, tmp_path)
        assert land_module._load_promote_sprint_status_module() is None
    parent = _git(origin, "rev-parse", "main").strip()

    assert _finalize(monkeypatch, primary, _SLUG, "9.1") == 0

    _assert_promotion_commit(origin, parent)
    assert _statuses(_origin_text(origin, _SLUG)) == {
        "9-1-the-first-story": "done",
        "9-2-the-second-story": "in-progress",
        "epic-9": "in-progress",
    }
    warns = [f for f in _observation_findings(primary, _SLUG) if f["code"] == "MRS-LAND-011"]
    assert [f["severity"] for f in warns] == ["warn"]
    assert "apply_epic_rollups could not be loaded" in warns[0]["message"]
    assert "the Tier-3 feed was not synced" in warns[0]["message"]


def test_a_rollup_that_reverts_the_only_feed_change_publishes_nothing(tmp_path: Path, monkeypatch) -> None:
    """The feed differs from the twin only by a stale epic row and the landed key already reads ``done``:
    rolled up, the text equals ``origin/main``'s, so nothing is published (an empty commit would fail)."""
    twin = {"9-1-the-first-story": "done", "9-2-the-second-story": "backlog", "epic-9": "in-progress"}
    origin, primary = _estate(tmp_path, _SLUG, _plain_render(_SLUG, twin))
    _write_feed(primary, _SLUG, _feed_text({**twin, "epic-9": "backlog"}))
    parent = _git(origin, "rev-parse", "main").strip()

    assert _finalize(monkeypatch, primary, _SLUG, "9.1") == 0

    assert _git(origin, "rev-parse", "main").strip() == parent
    assert [f for f in _observation_findings(primary, "pyforge-marshal") if f["code"] == "MRS-LAND-011"] == []


# -- AC 5: the doctor 41.5 replay -------------------------------------------------------------------------------

_DOCTOR = "pyforge-doctor"
_DOCTOR_41_5 = "41-5-a-new-story-reopens-its-done-epic-without-reading-as-a-ledger-regression"
#: The tracked twin at ``b9869e5c6d^``, verbatim -- its git blob id is pinned below.
_DOCTOR_BEFORE = (_FIXTURES / "doctor_ledger_before_b9869e5c6d.yaml").read_text(encoding="utf-8")
_DOCTOR_BEFORE_BLOB = "99d425d8ed51144f8c19748a6913d29c483827a6"
#: The tracked twin ``b9869e5c6d`` wrote: 41-5 ``done`` and ``epic-41`` dropped to ``backlog``.
_DOCTOR_B9869E5C6D_BLOB = "430d290a42be37a46b18940717d25d4a549a09b6"


def _doctor_feed_statuses() -> dict[str, str]:
    """``b9869e5c6d``'s feed: the twin's statuses with the stale ``epic-41: backlog`` row it copied."""
    statuses = dict(_statuses(_DOCTOR_BEFORE))
    assert statuses["epic-41"] == "in-progress"
    statuses["epic-41"] = "backlog"
    return statuses


def test_the_replayed_inputs_reproduce_b9869e5c6d_without_the_roll_up() -> None:
    """The replay is faithful: the fixture is the twin at ``b9869e5c6d^`` (blob id), and the unfixed
    promotion -- the sync's render of the feed, then the advancement, no roll-up -- yields exactly the
    bytes ``b9869e5c6d`` published."""
    assert _blob_sha(_DOCTOR_BEFORE) == _DOCTOR_BEFORE_BLOB
    unfixed, matched = land_module.render_ledger_advancements(
        _plain_render(_DOCTOR, _doctor_feed_statuses()), frozenset({_DOCTOR_41_5})
    )
    assert matched == {_DOCTOR_41_5}
    assert _blob_sha(unfixed) == _DOCTOR_B9869E5C6D_BLOB


def test_the_doctor_41_5_replay_publishes_epic_41_in_progress(tmp_path: Path, monkeypatch) -> None:
    """AC 5: the replayed inputs of ``b9869e5c6d`` (doctor 41.5) through the fixed finalize -- ``epic-41``
    reads ``in-progress`` (41.1 and 41.5 done, 41.2-41.4 backlog), and the only row that moved is 41-5."""
    origin, primary = _estate(tmp_path, _DOCTOR, _DOCTOR_BEFORE)
    _write_feed(primary, _DOCTOR, _feed_text(_doctor_feed_statuses()))
    parent = _git(origin, "rev-parse", "main").strip()

    assert _finalize(monkeypatch, primary, _DOCTOR, "41.5") == 0

    _assert_promotion_commit(origin, parent)
    published = _origin_text(origin, _DOCTOR)
    assert _statuses(published)["epic-41"] == "in-progress"
    assert published == _DOCTOR_BEFORE.replace(f"  {_DOCTOR_41_5}: backlog\n", f"  {_DOCTOR_41_5}: done\n")
