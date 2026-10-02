"""Unit tests for ``marshal factory drain --plan`` (Story 65.1, CAP-274).

One test per Acceptance Criterion plus the I/O matrix rows. The plan is driven
through ``run_fleet_drain`` -- the handler the CLI reaches -- with the same
fakes ``test_dispatch_fleet.py`` uses, except that the recording variants here
FAIL LOUDLY on any write: the plan's whole contract is that it reads only.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pytest
from test_dispatch_fleet import (
    _FU_OTHER_SLUG,
    _FU_SLUG,
    _FU_STORY,
    FakeBuildHarness,
    FakeFs,
    FakeHarness,
    FakeProcess,
    FakeVcs,
    _FollowupVcs,
    _fu_ledger_rel,
    _fu_seed_station,
    _fu_spec,
    _fu_subject,
    _init_git_repo,
)

from pyforge.marshal.adapters.vcs_git import VcsCommandError
from pyforge.marshal.cli import dispatch as dispatch_cli
from pyforge.marshal.cli import drain_plan
from pyforge.marshal.cli.dispatch import (
    DispatchAttempt,
    add_factory_drain_subparser,
    execute_fleet_cycle,
    run_fleet_drain,
)
from pyforge.marshal.core import dispatch as dispatch_core
from pyforge.marshal.core import dispatch_fleet, policy, verdict
from pyforge.marshal.core.dispatch_fleet import FleetCampaignMode
from pyforge.marshal.core.identity import normalize, render_feed_key
from pyforge.marshal.core.model import Severity

_STEWARD = "pyforge-steward"

#: The autouse fixture replaces `_journal_dispatch_wave` with a tripwire; the
#: cycle-side wave tests need the real writer back.
_REAL_JOURNAL_DISPATCH_WAVE = dispatch_cli._journal_dispatch_wave

_K_KERNEL = "44-3-kernel"
_K_FOLD = "44-4-fold-the-packages"
_K_ESTATE = "44-5-move-the-estate"
_K_CFE = "44-6-cfe-comes-home"
_K_LAUNCH = "44-12-launch"

_STEWARD_EPICS = """\
## Epic 44: Launch the Foundry

### Story 44.3: The kernel

**Type:** feature • **Deps:** —

### Story 44.4: Fold the packages

**Type:** feature • **Effort:** L • **Deps:** S-44.3, S-44.12

**Parked 2026-09-13 (regenerate-not-fold):** do **not** dispatch. File-move story superseded.
Ledger stays `backlog`.

### Story 44.5: Move the estate

**Type:** feature • **Deps:** S-44.4

**Parked 2026-09-13 (regenerate-not-fold):** do **not** dispatch as a tree copy. Ledger stays `backlog`.

### Story 44.6: CFE comes home

**Type:** feature • **Deps:** S-44.5

**Parked 2026-09-13 (regenerate-not-fold):** do **not** dispatch as a cell move. Ledger stays `backlog`.

### Story 44.12: Launch

**Type:** feature • **Deps:** —
"""

#: Steward's 2026-09-27 ledger: 44.3 and 44.12 done, 44.4-44.6 backlog.
_STEWARD_LEDGER = (
    (_K_KERNEL, "done"),
    (_K_LAUNCH, "done"),
    (_K_FOLD, "backlog"),
    (_K_ESTATE, "backlog"),
    (_K_CFE, "backlog"),
)

#: A spec whose `## Verification` declares no command: it binds trivially.
_BOUND_SPEC_BODY = "\n## Verification\n\n**Commands:**\n\n**Manual checks:**\n- none\n"
_UNBOUND_SPEC_BODY = "\n## Intent\n\nNo verification section at all.\n"


def _spec_text(surface: str, body: str, *, status: str = "backlog") -> str:
    return f'---\nstatus: {status}\nsurface: ["{surface}"]\n---\n{body}'


def _write_spec(repo: Path, slug: str, key: str, *, surface: str | None = None, body: str = _BOUND_SPEC_BODY) -> Path:
    specs = dispatch_core.planning_specs_dir(repo, slug)
    specs.mkdir(parents=True, exist_ok=True)
    path = specs / f"spec-{key}.md"
    path.write_text(_spec_text(surface or f"src/{key}/**", body), encoding="utf-8")
    return path


def _write_epics(repo: Path, slug: str, text: str) -> None:
    planning = repo / "_bmad-output" / "projects" / slug / "planning-artifacts"
    planning.mkdir(parents=True, exist_ok=True)
    (planning / "epics.md").write_text(text, encoding="utf-8")


def _write_queue_config(repo: Path, text: str) -> None:
    path = dispatch_fleet.queue_config_path(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _seed_steward(repo: Path, *, queue_config: str | None = None) -> None:
    """The 2026-09-27 replay: 44.4's spec has no `## Verification`, 44.4-44.6
    are parked in prose only, and the override list names only done keys."""
    _write_epics(repo, _STEWARD, _STEWARD_EPICS)
    _write_spec(repo, _STEWARD, _K_FOLD, body=_UNBOUND_SPEC_BODY)
    _write_queue_config(
        repo,
        queue_config
        if queue_config is not None
        else f"order_overrides:\n  {_STEWARD}: [{_K_KERNEL}, {_K_LAUNCH}]\nskip_policies: []\n",
    )


# --------------------------------------------------------------------------
# Recording fakes: the plan must READ only, so any write is a loud failure.
# --------------------------------------------------------------------------


class WriteRecorded(AssertionError):
    """A write the plan must never make."""


class RecordingFs(FakeFs):
    def __init__(self) -> None:
        super().__init__()
        self.writes: list[tuple[str, Path]] = []

    def _no_write(self, what: str, path: Path) -> None:
        self.writes.append((what, path))
        raise WriteRecorded(f"the plan wrote: {what} {path}")

    def acquire_advisory_lock(self, path, *, timeout_s):  # type: ignore[override]
        self._no_write("acquire_advisory_lock", path)

    def ensure_dir(self, path):  # type: ignore[override]
        self._no_write("ensure_dir", path)

    def create_dir_exclusive(self, path):  # type: ignore[override]
        self._no_write("create_dir_exclusive", path)

    def append_line(self, path, line, *, fsync):  # type: ignore[override]
        self._no_write("append_line", path)

    def write_text_atomic(self, path, content):  # type: ignore[override]
        self._no_write("write_text_atomic", path)

    def repoint_symlink_atomic(self, path, target):  # type: ignore[override]
        self._no_write("repoint_symlink_atomic", path)


class RecordingVcs(FakeVcs):
    def __init__(self, repo_root: Path) -> None:
        super().__init__(repo_root)
        self.writes: list[tuple[str, Path]] = []

    def add_worktree(self, repo_root, home, branch, *, base):  # type: ignore[override]
        self.writes.append(("add_worktree", home))
        raise WriteRecorded(f"the plan added a worktree at {home}")

    def worktree_unified_patch(self, worktree, *, baseline_sha):
        return ""


class ProbeBuildHarness(FakeBuildHarness):
    """Counts the harness binary + authcheck walk."""

    def __init__(self, *, present: bool = True) -> None:
        super().__init__(present=present)
        self.walks = 0
        self.preferences: list[tuple[str, ...]] = []  # what each walk was handed, in order

    def binary_present(self, preference=(), repo_root=None):
        self.walks += 1
        self.preferences.append(tuple(preference))
        return super().binary_present(preference, repo_root)


def _tree(repo: Path) -> list[str]:
    return sorted(str(p.relative_to(repo)) for p in repo.rglob("*") if ".git" not in p.parts)


@pytest.fixture(autouse=True)
def _plan_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """A git-initialised tmp repo, cwd there, no parent scope, and a
    `dispatch_once` / wave journal that fail the test if the plan calls them."""
    _init_git_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    # test_dispatch_fleet's helper leaks BMAD_ACTIVE_PROJECT into os.environ.
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)

    def _forbidden(*_args, **_kwargs):
        raise WriteRecorded("the plan reached a launch/journal writer")

    monkeypatch.setattr(dispatch_cli, "dispatch_once", _forbidden)
    monkeypatch.setattr(dispatch_cli, "_journal_dispatch_wave", _forbidden)


def _parse(*argv: str) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="marshal-factory")
    sub = parser.add_subparsers(dest="verb")
    add_factory_drain_subparser(sub)
    return parser.parse_args(["drain", *argv])


def _plan(
    tmp_path: Path,
    *argv: str,
    ledgers: dict[str, tuple[tuple[str, str], ...]],
    fs: FakeFs | None = None,
    vcs: FakeVcs | None = None,
    build_harness: FakeBuildHarness | None = None,
    process: FakeProcess | None = None,
    capsys: pytest.CaptureFixture[str],
    text: bool = False,
) -> tuple[int, dict, str]:
    """Run ``drain --plan ...``; returns ``(exit code, parsed JSON envelope, raw stdout)``."""
    # Station policies differ (marshal's own runs waves): every test that does
    # not ask for a wave plans a serial cycle, as `_cycle` in test_dispatch_fleet does.
    cap = () if "--max-in-flight" in argv else ("--max-in-flight", "1")
    args = _parse("--plan", *(() if text else ("--format", "json")), *cap, *argv)
    code = run_fleet_drain(
        args,
        fs=fs if fs is not None else RecordingFs(),
        vcs=vcs if vcs is not None else RecordingVcs(tmp_path),
        build_harness=build_harness if build_harness is not None else ProbeBuildHarness(),
        process=process if process is not None else FakeProcess(alive=False),
        harness=FakeHarness(ledgers),
    )
    out = capsys.readouterr().out
    return code, (json.loads(out) if not text else {}), out


def _findings(envelope: dict, code: str) -> list[dict]:
    return [f for f in envelope["findings"] if f["code"] == code]


def _station(envelope: dict, slug: str = _STEWARD) -> dict:
    rows = [row for row in envelope["data"]["stations"] if row["slug"] == slug]
    assert len(rows) == 1, envelope["data"]["stations"]
    return rows[0]


def _steward_plan(tmp_path: Path, capsys: pytest.CaptureFixture[str], *extra: str, **kwargs):
    return _plan(
        tmp_path,
        "--mode",
        "drain_to_zero",
        "--station",
        _STEWARD,
        *extra,
        ledgers={_STEWARD: _STEWARD_LEDGER},
        capsys=capsys,
        **kwargs,
    )


# --------------------------------------------------------------------------
# AC 1 -- steward's 2026-09-27 state
# --------------------------------------------------------------------------


def test_steward_replay_names_the_binding_refusal_the_park_the_parks_and_the_inert_override(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _seed_steward(tmp_path)
    code, envelope, _out = _steward_plan(tmp_path, capsys)

    row = _station(envelope)
    assert row["next_story"] == _K_FOLD
    assert row["would_dispatch"] is False
    assert row["outcome"] == "dispatch"

    next_findings = _findings(envelope, "MRS-DRAINPLAN-001")
    assert len(next_findings) == 2
    assert sum("MRS-GATE-010" in f["message"] for f in next_findings) == 1
    assert sum("prose-park" in f["message"] for f in next_findings) == 1
    assert all(_K_FOLD in f["message"] and _STEWARD in f["message"] for f in next_findings)

    queued = _findings(envelope, "MRS-DRAINPLAN-002")
    assert len(queued) == 2
    assert any(_K_ESTATE in f["message"] for f in queued)
    assert any(_K_CFE in f["message"] for f in queued)
    assert all(_K_FOLD not in f["message"] for f in queued)

    inert = _findings(envelope, "MRS-DRAINPLAN-003")
    assert len(inert) == 1
    assert _K_KERNEL in inert[0]["message"] and _K_LAUNCH in inert[0]["message"]

    assert code == 4 == verdict.exit_code_for(verdict.Verdict.ERROR)
    assert envelope["verdict"] == "error"


def test_the_station_payload_carries_the_promised_projection(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _seed_steward(tmp_path)
    _code, envelope, _out = _steward_plan(tmp_path, capsys)

    row = _station(envelope)
    for key in (
        "slug",
        "mode",
        "parallel_cap",
        "backlog",
        "outcome",
        "next_story",
        "would_dispatch",
        "refusals",
        "skipped",
        "deps",
        "env_checked",
    ):
        assert key in row
    assert row["mode"] == "drain_to_zero"
    assert row["parallel_cap"] == 1
    assert row["backlog"] == [_K_FOLD, _K_ESTATE, _K_CFE]
    assert row["env_checked"] is False
    assert {"story", "code", "reason"} <= set(row["refusals"][0])
    assert {r["code"] for r in row["refusals"]} == {"MRS-GATE-010", "prose-park"}
    assert row["deps"][_K_FOLD] == {"declared": ["44.3", "44.12"], "unmet": []}
    assert [p["story"] for p in row["prose_parks"]] == [_K_FOLD, _K_ESTATE, _K_CFE]
    assert envelope["data"]["plan"] is True


# --------------------------------------------------------------------------
# AC 2 -- no write of any kind
# --------------------------------------------------------------------------


def test_the_plan_writes_nothing_and_never_launches(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_steward(tmp_path)
    fs, vcs, process = RecordingFs(), RecordingVcs(tmp_path), FakeProcess(alive=False)
    build_harness = ProbeBuildHarness()
    before = _tree(tmp_path)

    code, _envelope, _out = _steward_plan(
        tmp_path, capsys, fs=fs, vcs=vcs, build_harness=build_harness, process=process
    )

    assert code == 4
    assert fs.writes == []  # no lock, no ensure_dir, no journal append, no file write
    assert fs.locks_acquired == [] and fs.locks_released == []
    assert vcs.writes == []  # no worktree added
    assert process.spawned == []  # no supervisor
    assert process.run_calls == []  # no probe
    assert build_harness.dispatched == [] and build_harness.walks == 0
    assert _tree(tmp_path) == before  # no directory created, no file written
    assert not dispatch_fleet.fleet_runs_dir(tmp_path).exists()
    # `dispatch_once` and `_journal_dispatch_wave` are monkeypatched to raise: reaching either fails the test.


def test_a_parallel_plan_journals_no_wave_either(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    slug = "pyforge-marshal"
    _write_spec(tmp_path, slug, "1-1-alpha", surface="src/a/**")
    _write_spec(tmp_path, slug, "1-2-beta", surface="src/b/**")
    before = _tree(tmp_path)
    fs = RecordingFs()

    code, envelope, _out = _plan(
        tmp_path,
        "--mode",
        "drain_to_zero",
        "--station",
        slug,
        "--max-in-flight",
        "2",
        ledgers={slug: (("1-1-alpha", "backlog"), ("1-2-beta", "backlog"))},
        fs=fs,
        capsys=capsys,
    )

    assert code == 0
    assert _station(envelope, slug)["stories"] == ["1-1-alpha", "1-2-beta"]
    assert fs.writes == []
    assert _tree(tmp_path) == before
    assert not dispatch_core.dispatch_runs_dir(tmp_path, slug).exists()


# --------------------------------------------------------------------------
# AC 3 -- a declared skip is a skip, in code
# --------------------------------------------------------------------------


def test_declared_skips_are_listed_and_never_next_and_never_named_by_a_finding(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    skips = "".join(
        f"  - station: {_STEWARD}\n    story: {key}\n    reason: 'parked in code: {key}'\n"
        for key in (_K_FOLD, _K_ESTATE, _K_CFE)
    )
    _seed_steward(tmp_path, queue_config=f"order_overrides: {{}}\nskip_policies:\n{skips}")
    code, envelope, _out = _steward_plan(tmp_path, capsys)

    row = _station(envelope)
    assert row["next_story"] is None
    assert row["outcome"] == "all-skipped"
    assert {s["story"]: s["reason"] for s in row["skipped"]} == {
        _K_FOLD: f"parked in code: {_K_FOLD}",
        _K_ESTATE: f"parked in code: {_K_ESTATE}",
        _K_CFE: f"parked in code: {_K_CFE}",
    }
    assert all(s["basis"] == "declared skip policy" for s in row["skipped"])
    for finding in envelope["findings"]:
        if finding["code"] in {"MRS-DRAINPLAN-001", "MRS-DRAINPLAN-002"}:
            assert not any(key in finding["message"] for key in (_K_FOLD, _K_ESTATE, _K_CFE))
    assert row["prose_parks"] == []
    assert code == 0


def test_a_skip_beyond_the_walk_is_still_listed_as_declared(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _seed_steward(
        tmp_path,
        queue_config=(
            f"order_overrides: {{}}\nskip_policies:\n  - station: {_STEWARD}\n    story: {_K_CFE}\n    reason: later\n"
        ),
    )
    _write_spec(tmp_path, _STEWARD, _K_FOLD)  # bound, so 44.4 would dispatch cleanly
    _code, envelope, _out = _steward_plan(tmp_path, capsys)

    row = _station(envelope)
    assert row["next_story"] == _K_FOLD
    assert [s["story"] for s in row["skipped"]] == [_K_CFE]


# --------------------------------------------------------------------------
# AC 4 -- the plan and the drain share one planner
# --------------------------------------------------------------------------


def _seed_shared_fleet(repo: Path) -> dict[str, tuple[tuple[str, str], ...]]:
    ledgers: dict[str, tuple[tuple[str, str], ...]] = {}
    for slug in ("pyforge-doctor", "pyforge-marshal", "pyforge-scribe"):
        keys = (f"1-1-{slug[8:11]}-alpha", f"1-2-{slug[8:11]}-beta", f"1-3-{slug[8:11]}-gamma")
        for index, key in enumerate(keys):
            _write_spec(repo, slug, key, surface=f"src/{slug}/{index}/**")
        ledgers[slug] = tuple((key, "backlog") for key in keys)
    ledgers["pyforge-scribe"] = (("1-0-scr-shipped", "done"),) + ledgers["pyforge-scribe"]
    return ledgers


def _record_launches(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    launches: list[tuple[str, str]] = []

    def _recording_dispatch_once(*, slug: str, story: str, **_kwargs):
        launches.append((slug, story))
        return DispatchAttempt(data={"session_pid": 7070, "story": story}, findings=())

    monkeypatch.setattr(dispatch_cli, "dispatch_once", _recording_dispatch_once)
    return launches


def _run_one_cycle(tmp_path: Path, ledgers, **kwargs):
    return execute_fleet_cycle(
        repo_root=tmp_path,
        mode=FleetCampaignMode.DRAIN_TO_ZERO,
        leave_remaining=1,
        campaign_blocked={},
        fs=FakeFs(),
        vcs=FakeVcs(tmp_path),
        build_harness=FakeBuildHarness(),
        process=FakeProcess(alive=False),
        harness=FakeHarness(ledgers),
        **kwargs,
    )


def test_serial_next_story_per_station_equals_what_the_cycle_hands_dispatch_once(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    ledgers = _seed_shared_fleet(tmp_path)
    code, envelope, _out = _plan(tmp_path, "--mode", "drain_to_zero", ledgers=ledgers, capsys=capsys)
    assert code == 0
    planned = {row["slug"]: row["next_story"] for row in envelope["data"]["stations"]}
    assert set(planned) == set(ledgers)

    launches = _record_launches(monkeypatch)
    _run_one_cycle(tmp_path, ledgers, policy_flags={"dispatch": {"max_parallel": 1}})

    assert sorted(launches) == sorted(planned.items())
    assert planned["pyforge-scribe"] == "1-1-scr-alpha"  # a done story is not the next one


def test_parallel_wave_members_equal_what_the_cycle_hands_dispatch_once(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    ledgers = _seed_shared_fleet(tmp_path)
    code, envelope, _out = _plan(
        tmp_path, "--mode", "drain_to_zero", "--max-in-flight", "2", ledgers=ledgers, capsys=capsys
    )
    assert code == 0
    planned = {row["slug"]: row["stories"] for row in envelope["data"]["stations"]}
    assert all(len(stories) == 2 for stories in planned.values())
    for row in envelope["data"]["stations"]:
        assert row["parallel_cap"] == 2
        assert row["wave"]["members"] == row["stories"]

    launches = _record_launches(monkeypatch)
    monkeypatch.setattr(dispatch_cli, "_journal_dispatch_wave", lambda *a, **k: None)
    _run_one_cycle(tmp_path, ledgers, max_in_flight=2)

    launched: dict[str, list[str]] = {}
    for slug, story in launches:
        launched.setdefault(slug, []).append(story)
    assert {slug: sorted(stories) for slug, stories in launched.items()} == {
        slug: sorted(stories) for slug, stories in planned.items()
    }


def test_the_extraction_keeps_the_cycles_own_ledger_error_path(tmp_path: Path) -> None:
    """`execute_fleet_cycle` still reports MRS-DRAIN-003 for an unreadable ledger."""
    _write_spec(tmp_path, "pyforge-marshal", "1-1-alpha")
    (tmp_path / "_bmad-output" / "projects" / "pyforge-doctor").mkdir(parents=True)
    report = _run_one_cycle(tmp_path, {"pyforge-marshal": (("1-1-alpha", "done"),)})
    assert any(f.code == "MRS-DRAIN-003" and "pyforge-doctor" in f.message for f in report.findings)


# --------------------------------------------------------------------------
# AC 5 -- already landed
# --------------------------------------------------------------------------


#: The 2026-09-18 doctor 27.4 fixture (test_promotion.py): a PR merged from a bare station branch.
_MINT_SUBJECT = "Merge pull request #1477 from rxm7706/doctor/27-4-mint"


class _MergedVcs(RecordingVcs):
    """`main` carries the station-branch PR merge; the spec's twin on it is stocked per test."""

    def commit_subjects(self, repo_root, ref):
        return (_MINT_SUBJECT,)


def _plan_doctor_27_4(tmp_path: Path, capsys: pytest.CaptureFixture[str], *, spec_on_main: str):
    slug = "pyforge-doctor"
    spec = _write_spec(tmp_path, slug, "27-4-mint")
    vcs = _MergedVcs(tmp_path)
    vcs.remote_ledger_texts[spec.relative_to(tmp_path).as_posix()] = spec_on_main
    return slug, _plan(
        tmp_path,
        "--mode",
        "drain_to_zero",
        "--station",
        slug,
        ledgers={slug: (("27-4-mint", "backlog"),)},
        vcs=vcs,
        capsys=capsys,
    )


def test_a_story_corroborated_merged_on_main_reads_already_landed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    slug, (code, envelope, _out) = _plan_doctor_27_4(tmp_path, capsys, spec_on_main="---\nstatus: done\n---\n")

    hits = _findings(envelope, "MRS-DRAINPLAN-001")
    assert [("already-landed" in f["message"]) for f in hits] == [True]
    assert code == 4
    assert _station(envelope, slug)["would_dispatch"] is False


def test_a_merge_the_spec_does_not_corroborate_is_not_already_landed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A mint/fallout PR merge is not a landing: the spec on main must read `done`."""
    slug, (code, envelope, _out) = _plan_doctor_27_4(tmp_path, capsys, spec_on_main="---\nstatus: ready\n---\n")

    assert code == 0
    assert _station(envelope, slug)["would_dispatch"] is True


# --------------------------------------------------------------------------
# AC 6 -- Deps readiness, in both modes
# --------------------------------------------------------------------------

_DEPS_EPICS = """\
## Epic 44: Launch

### Story 44.3: The kernel

**Deps:** —

### Story 44.4: Fold the packages

**Deps:** S-44.3
"""


def _seed_unmet_deps(repo: Path) -> dict[str, tuple[tuple[str, str], ...]]:
    _write_epics(repo, _STEWARD, _DEPS_EPICS)
    _write_spec(repo, _STEWARD, _K_KERNEL, surface="src/kernel/**")
    _write_spec(repo, _STEWARD, _K_FOLD, surface="src/fold/**")
    # A live override puts 44.4 first, ahead of its unmet dep 44.3.
    _write_queue_config(repo, f"order_overrides:\n  {_STEWARD}: [{_K_FOLD}]\nskip_policies: []\n")
    return {_STEWARD: ((_K_KERNEL, "backlog"), (_K_FOLD, "backlog"))}


def test_serial_mode_warns_the_unmet_deps_do_not_gate(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    ledgers = _seed_unmet_deps(tmp_path)
    code, envelope, _out = _plan(
        tmp_path, "--mode", "drain_to_zero", "--station", _STEWARD, ledgers=ledgers, capsys=capsys
    )

    row = _station(envelope)
    assert row["next_story"] == _K_FOLD
    assert row["stories"] == [_K_FOLD]  # serial mode dispatches it anyway
    warn = _findings(envelope, "MRS-DRAINPLAN-004")
    assert len(warn) == 1
    assert "serial" in warn[0]["message"] and "44.3" in warn[0]["message"]
    assert row["deps"][_K_FOLD]["unmet"] == ["44.3"]
    assert row["held"] == []
    assert code == 0  # WARN never changes the exit


def test_parallel_mode_holds_the_story_and_names_the_mode(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    ledgers = _seed_unmet_deps(tmp_path)
    code, envelope, _out = _plan(
        tmp_path,
        "--mode",
        "drain_to_zero",
        "--station",
        _STEWARD,
        "--max-in-flight",
        "2",
        ledgers=ledgers,
        capsys=capsys,
    )

    row = _station(envelope)
    assert row["next_story"] == _K_FOLD  # the queue head ...
    assert _K_FOLD not in row["stories"]  # ... but the wave holds it
    assert row["stories"] == [_K_KERNEL]
    assert [h["story"] for h in row["held"]] == [_K_FOLD]
    assert "44.3" in row["held"][0]["reason"]
    warn = _findings(envelope, "MRS-DRAINPLAN-004")
    assert len(warn) == 1
    assert "parallel" in warn[0]["message"] and "holds" in warn[0]["message"]
    assert code == 0


# --------------------------------------------------------------------------
# AC 7 -- shell syntax and merge subject
# --------------------------------------------------------------------------


def _with_policy_flags(monkeypatch: pytest.MonkeyPatch, **flags: object) -> None:
    real = dispatch_cli._compose_policy

    def _compose(slug, *, flags=None, _extra=flags):
        return real(slug, flags={**(flags or {}), **_extra})

    monkeypatch.setattr(dispatch_cli, "_compose_policy", _compose)


def test_a_verify_command_with_bare_shell_syntax_is_gate_003(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    slug = "pyforge-marshal"
    _write_spec(tmp_path, slug, "22-7-fleet")
    _with_policy_flags(monkeypatch, verify_commands=["pixi run a && pixi run b"])
    code, envelope, _out = _plan(
        tmp_path,
        "--mode",
        "drain_to_zero",
        "--station",
        slug,
        ledgers={slug: (("22-7-fleet", "backlog"),)},
        capsys=capsys,
    )

    hits = [f for f in _findings(envelope, "MRS-DRAINPLAN-001") if "MRS-GATE-003" in f["message"]]
    assert len(hits) == 1
    assert "'&'" in hits[0]["message"]
    assert code == 4


def test_a_merge_subject_template_that_is_not_marshal_native_is_disp_019(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    slug = "pyforge-marshal"
    _write_spec(tmp_path, slug, "22-7-fleet")
    _with_policy_flags(monkeypatch, merge_subject_template="Merge to main")  # no {key}: cannot render
    code, envelope, _out = _plan(
        tmp_path,
        "--mode",
        "drain_to_zero",
        "--station",
        slug,
        ledgers={slug: (("22-7-fleet", "backlog"),)},
        capsys=capsys,
    )

    hits = [f for f in _findings(envelope, "MRS-DRAINPLAN-001") if "MRS-DISP-019" in f["message"]]
    assert len(hits) == 1
    assert code == 4


def test_a_declared_command_outside_verify_commands_is_gate_011(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    slug = "pyforge-marshal"
    _write_spec(
        tmp_path,
        slug,
        "22-7-fleet",
        body="\n## Verification\n\n**Commands:**\n- `pixi run --frozen -e nowhere never-declared-test` -- expected: pass\n",
    )
    code, envelope, _out = _plan(
        tmp_path,
        "--mode",
        "drain_to_zero",
        "--station",
        slug,
        ledgers={slug: (("22-7-fleet", "backlog"),)},
        capsys=capsys,
    )
    hits = [f for f in _findings(envelope, "MRS-DRAINPLAN-001") if "MRS-GATE-011" in f["message"]]
    assert len(hits) == 1 and "never-declared-test" in hits[0]["message"]
    assert code == 4


def test_a_declared_lint_types_command_binds_clean_through_the_derived_widening(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Story 79.2: ``_StationReads.verify_commands`` is the third caller of
    ``_verify_commands_with_surface_guard`` -- its widened tuple carries the
    derived ``lint-types`` lane, so a spec that declares it is NOT a
    MRS-GATE-011 (the station's own ``verify_commands`` never list it), while
    a genuinely undeclared command still is."""
    slug = "pyforge-marshal"
    _write_spec(
        tmp_path,
        slug,
        "22-7-fleet",
        body="\n## Verification\n\n**Commands:**\n- `pixi run --frozen -e pyforge-guild lint-types` -- expected: pass\n",
    )
    code, envelope, _out = _plan(
        tmp_path,
        "--mode",
        "drain_to_zero",
        "--station",
        slug,
        ledgers={slug: (("22-7-fleet", "backlog"),)},
        capsys=capsys,
    )
    assert [f for f in _findings(envelope, "MRS-DRAINPLAN-001") if "MRS-GATE-011" in f["message"]] == []
    assert "MRS-GATE-011" not in _out
    assert code == 0


# --------------------------------------------------------------------------
# AC 8 -- the environment is probed only behind --check-env
# --------------------------------------------------------------------------


def test_without_check_env_no_harness_authcheck_or_session_probe_runs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    slug = "pyforge-marshal"
    _write_spec(tmp_path, slug, "22-7-fleet")
    build_harness, process = ProbeBuildHarness(present=False), FakeProcess(alive=False)
    code, envelope, _out = _plan(
        tmp_path,
        "--mode",
        "drain_to_zero",
        "--station",
        slug,
        ledgers={slug: (("22-7-fleet", "backlog"),)},
        build_harness=build_harness,
        process=process,
        capsys=capsys,
    )
    assert build_harness.walks == 0
    assert process.run_calls == []
    assert _station(envelope, slug)["env_checked"] is False
    assert "env" not in _station(envelope, slug)
    assert code == 0  # a missing harness is invisible without --check-env


def test_check_env_reports_a_missing_harness_as_disp_003(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    slug = "pyforge-marshal"
    _write_spec(tmp_path, slug, "22-7-fleet")
    build_harness, process = ProbeBuildHarness(present=False), FakeProcess(alive=False)
    code, envelope, _out = _plan(
        tmp_path,
        "--mode",
        "drain_to_zero",
        "--station",
        slug,
        "--harness",
        "cursor,claude",
        "--check-env",
        ledgers={slug: (("22-7-fleet", "backlog"),)},
        build_harness=build_harness,
        process=process,
        capsys=capsys,
    )

    assert build_harness.walks == 1
    assert len(process.run_calls) == 1  # the session-precondition probe, once
    row = _station(envelope, slug)
    assert row["env_checked"] is True
    hits = [f for f in _findings(envelope, "MRS-DRAINPLAN-001") if "MRS-DISP-003" in f["message"]]
    assert len(hits) == 1
    assert len(_findings(envelope, "MRS-DISP-027")) == 2  # the walk's own skipped-candidate WARNs, relayed
    assert code == 4


def test_check_env_with_a_present_harness_is_clean(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    slug = "pyforge-marshal"
    _write_spec(tmp_path, slug, "22-7-fleet")
    code, envelope, _out = _plan(
        tmp_path,
        "--mode",
        "drain_to_zero",
        "--station",
        slug,
        "--check-env",
        ledgers={slug: (("22-7-fleet", "backlog"),)},
        capsys=capsys,
    )
    assert code == 0
    assert _station(envelope, slug)["env"]["harness_profile"]
    assert envelope["data"]["session_check"] == "ok"


# --------------------------------------------------------------------------
# AC 9 -- an unreadable ledger is never a clean plan
# --------------------------------------------------------------------------


def test_an_unreadable_ledger_is_drainplan_005_and_exits_unevaluable(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    slug = "pyforge-marshal"
    _write_spec(tmp_path, slug, "22-7-fleet")
    (tmp_path / "_bmad-output" / "projects" / "pyforge-doctor").mkdir(parents=True)
    code, envelope, _out = _plan(
        tmp_path,
        "--mode",
        "drain_to_zero",
        ledgers={slug: (("22-7-fleet", "backlog"),)},  # pyforge-doctor's ledger cannot be read
        capsys=capsys,
    )

    unreadable = _findings(envelope, "MRS-DRAINPLAN-005")
    assert len(unreadable) == 1 and "pyforge-doctor" in unreadable[0]["message"]
    assert _station(envelope, "pyforge-doctor")["outcome"] == "unevaluable"
    assert _station(envelope, "pyforge-doctor")["would_dispatch"] is False
    assert _station(envelope, slug)["would_dispatch"] is True  # one station never stops the others
    assert code == 1
    assert envelope["verdict"] == "unevaluable"


def test_an_error_elsewhere_outranks_an_unreadable_ledger(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _seed_steward(tmp_path)
    (tmp_path / "_bmad-output" / "projects" / "pyforge-doctor").mkdir(parents=True)
    code, envelope, _out = _plan(
        tmp_path, "--mode", "drain_to_zero", ledgers={_STEWARD: _STEWARD_LEDGER}, capsys=capsys
    )
    assert _findings(envelope, "MRS-DRAINPLAN-005") and _findings(envelope, "MRS-DRAINPLAN-001")
    assert code == 4


def test_a_git_read_that_fails_is_drainplan_005_never_a_clean_plan(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    slug = "pyforge-marshal"
    _write_spec(tmp_path, slug, "22-7-fleet")

    class _BrokenVcs(RecordingVcs):
        def commit_subjects(self, repo_root, ref):
            raise VcsCommandError("cannot read origin/main")

    code, envelope, _out = _plan(
        tmp_path,
        "--mode",
        "drain_to_zero",
        "--station",
        slug,
        ledgers={slug: (("22-7-fleet", "backlog"),)},
        vcs=_BrokenVcs(tmp_path),
        capsys=capsys,
    )
    hits = _findings(envelope, "MRS-DRAINPLAN-005")
    assert len(hits) == 1 and "cannot read origin/main" in hits[0]["message"]
    assert code == 1


# --------------------------------------------------------------------------
# AC 10 -- launch-only flags are a usage error
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "flags",
    [
        ("--once",),
        ("--campaign", "fleet-run-1"),
        ("--max-cycles", "3"),
        ("--max-cycles", "0"),
        ("--tick-seconds", "5"),
        ("--once", "--tick-seconds", "60"),
    ],
)
def test_plan_with_a_launch_only_flag_is_a_usage_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], flags: tuple[str, ...]
) -> None:
    args = _parse("--plan", "--mode", "drain_to_zero", *flags)
    code = run_fleet_drain(
        args,
        fs=RecordingFs(),
        vcs=RecordingVcs(tmp_path),
        build_harness=ProbeBuildHarness(),
        process=FakeProcess(alive=False),
        harness=FakeHarness({}),
    )
    captured = capsys.readouterr()
    assert code == verdict.EXIT_USAGE == 2
    assert flags[0] in captured.err
    assert captured.out == ""


def test_the_usage_error_holds_through_the_real_cli_entry_point(tmp_path: Path) -> None:
    from pyforge.marshal.cli.main import main

    assert main(["factory", "drain", "--plan", "--mode", "drain_to_zero", "--once"]) == 2


@pytest.mark.parametrize("flag", ["--all-stories", "--check-env"])
def test_a_plan_modifier_without_plan_is_a_usage_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], flag: str
) -> None:
    args = _parse("--mode", "drain_to_zero", flag)
    code = run_fleet_drain(
        args,
        fs=RecordingFs(),
        vcs=RecordingVcs(tmp_path),
        build_harness=ProbeBuildHarness(),
        process=FakeProcess(alive=False),
        harness=FakeHarness({}),
    )
    assert code == 2
    assert flag in capsys.readouterr().err


def test_a_drain_without_plan_still_parses_the_launch_flags_to_their_defaults() -> None:
    args = _parse("--mode", "drain_to_zero")
    assert not hasattr(args, "max_cycles") and not hasattr(args, "tick_seconds")
    assert args.plan is False and args.all_stories is False and args.check_env is False
    assert getattr(args, "max_cycles", 0) == 0
    assert getattr(args, "tick_seconds", dispatch_cli._FLEET_TICK_SECONDS) == dispatch_cli._FLEET_TICK_SECONDS
    explicit = _parse("--mode", "drain_to_zero", "--max-cycles", "3", "--tick-seconds", "9")
    assert (explicit.max_cycles, explicit.tick_seconds) == (3, 9)


# --------------------------------------------------------------------------
# AC 11 -- the codes
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("code", "tier"),
    [
        ("MRS-DRAINPLAN-001", verdict.Verdict.ERROR),
        ("MRS-DRAINPLAN-002", verdict.Verdict.WARN),
        ("MRS-DRAINPLAN-003", verdict.Verdict.WARN),
        ("MRS-DRAINPLAN-004", verdict.Verdict.WARN),
        ("MRS-DRAINPLAN-005", verdict.Verdict.UNEVALUABLE),
    ],
)
def test_the_drainplan_codes_classify_at_the_promised_tiers(code: str, tier: verdict.Verdict) -> None:
    assert verdict.classify(code) is tier


# --------------------------------------------------------------------------
# I/O matrix rows not covered above
# --------------------------------------------------------------------------


def test_a_clean_station_would_dispatch_and_exits_zero(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    slug = "pyforge-marshal"
    _write_spec(tmp_path, slug, "22-7-fleet")
    code, envelope, _out = _plan(
        tmp_path,
        "--mode",
        "drain_to_zero",
        "--station",
        slug,
        ledgers={slug: (("22-7-fleet", "backlog"),)},
        capsys=capsys,
    )
    row = _station(envelope, slug)
    assert row["would_dispatch"] is True and row["refusals"] == []
    assert not [f for f in envelope["findings"] if f["severity"] == "error"]
    assert code == 0 and envelope["verdict"] == "clean"


def test_a_missing_tracked_spec_is_disp_005(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    slug = "pyforge-marshal"
    (tmp_path / "_bmad-output" / "projects" / slug).mkdir(parents=True)
    code, envelope, _out = _plan(
        tmp_path,
        "--mode",
        "drain_to_zero",
        "--station",
        slug,
        ledgers={slug: (("22-7-fleet", "backlog"),)},
        capsys=capsys,
    )
    hits = _findings(envelope, "MRS-DRAINPLAN-001")
    assert [("MRS-DISP-005" in f["message"]) for f in hits] == [True]
    assert code == 4


def test_a_parent_scope_naming_another_project_is_disp_041(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    slug = "pyforge-marshal"
    _write_spec(tmp_path, slug, "22-7-fleet")
    monkeypatch.setenv("BMAD_ACTIVE_PROJECT", "pyforge-steward")
    code, envelope, _out = _plan(
        tmp_path,
        "--mode",
        "drain_to_zero",
        "--station",
        slug,
        ledgers={slug: (("22-7-fleet", "backlog"),)},
        capsys=capsys,
    )
    assert [("MRS-DISP-041" in f["message"]) for f in _findings(envelope, "MRS-DRAINPLAN-001")] == [True]
    assert code == 4


def test_a_legacy_dispatch_branch_that_cannot_be_attributed_is_disp_030(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    slug = "pyforge-marshal"
    _write_spec(tmp_path, slug, "22-7-fleet")
    legacy = dispatch_core.legacy_dispatch_worktree_branch("22.7")

    class _LegacyVcs(RecordingVcs):
        def branch_exists(self, _repo_root, branch):
            return branch == legacy

    code, envelope, _out = _plan(
        tmp_path,
        "--mode",
        "drain_to_zero",
        "--station",
        slug,
        ledgers={slug: (("22-7-fleet", "backlog"),)},
        vcs=_LegacyVcs(tmp_path),
        capsys=capsys,
    )
    assert [("MRS-DISP-030" in f["message"]) for f in _findings(envelope, "MRS-DRAINPLAN-001")] == [True]
    assert code == 4


def _seed_worktree_spec(repo: Path, slug: str, key: str, story: str, *, status: str, followup: str = "false") -> Path:
    """A dispatch worktree that already exists, carrying its own copy of the spec."""
    spec = _write_spec(repo, slug, key)
    worktree = dispatch_core.dispatch_worktree_path(repo, slug, render_feed_key(normalize(story)))
    dest = worktree / spec.relative_to(repo)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        f'---\nstatus: {status}\nfollowup_review_recommended: {followup}\nsurface: ["src/x/**"]\n---\n'
        f"{_BOUND_SPEC_BODY}\nBlocking condition: waiting on mason 13.x\n",
        encoding="utf-8",
    )
    return worktree


def test_a_worktree_spec_left_blocked_is_disp_045(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    slug = "pyforge-marshal"
    _seed_worktree_spec(tmp_path, slug, "22-7-fleet", "22.7", status="blocked")
    code, envelope, _out = _plan(
        tmp_path,
        "--mode",
        "drain_to_zero",
        "--station",
        slug,
        ledgers={slug: (("22-7-fleet", "backlog"),)},
        capsys=capsys,
    )
    hits = _findings(envelope, "MRS-DRAINPLAN-001")
    assert [("MRS-DISP-045" in f["message"]) for f in hits] == [True]
    assert "waiting on mason 13.x" in hits[0]["message"]
    assert code == 4


def test_a_worktree_spec_done_is_land_only_not_a_refusal(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    slug = "pyforge-marshal"
    _seed_worktree_spec(tmp_path, slug, "22-7-fleet", "22.7", status="done")
    code, envelope, _out = _plan(
        tmp_path,
        "--mode",
        "drain_to_zero",
        "--station",
        slug,
        ledgers={slug: (("22-7-fleet", "backlog"),)},
        capsys=capsys,
    )
    row = _station(envelope, slug)
    assert row["land_only"] == ["22-7-fleet"]
    assert row["refusals"] == []
    assert not _findings(envelope, "MRS-DRAINPLAN-001")
    assert code == 0


def test_leftover_worktree_wip_is_disp_036(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    slug = "pyforge-marshal"
    worktree = _seed_worktree_spec(tmp_path, slug, "22-7-fleet", "22.7", status="ready-for-dev")
    vcs = RecordingVcs(tmp_path)
    vcs.progressed_worktrees.add(str(worktree))
    code, envelope, _out = _plan(
        tmp_path,
        "--mode",
        "drain_to_zero",
        "--station",
        slug,
        ledgers={slug: (("22-7-fleet", "backlog"),)},
        vcs=vcs,
        capsys=capsys,
    )
    hits = _findings(envelope, "MRS-DRAINPLAN-001")
    assert [("MRS-DISP-036" in f["message"]) for f in hits] == [True]
    assert code == 4


def test_leftover_wip_with_an_unfinalized_run_is_disp_039(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    slug = "pyforge-marshal"
    worktree = _seed_worktree_spec(tmp_path, slug, "22-7-fleet", "22.7", status="ready-for-dev")
    vcs = RecordingVcs(tmp_path)
    vcs.progressed_worktrees.add(str(worktree))
    from pyforge.marshal.core.journal import JournalEntryId, Phase, build_entry, prepare_for_write

    run_dir = dispatch_core.dispatch_run_dir(tmp_path, slug, "pyforge-marshal-20260930T000000000Z-abcd1234")
    run_dir.mkdir(parents=True)
    intent = prepare_for_write(
        build_entry(
            id=JournalEntryId("w", 0),
            ts="2026-09-30T00:00:00.000Z",
            run_id=run_dir.name,
            kind=dispatch_core.KIND_DISPATCH_LAUNCH,
            phase=Phase.INTENT,
            payload={"story_key": "22.7", "worktree_path": str(worktree), "baseline_head_sha": "aaa111"},
        )
    ).line
    (run_dir / "journal.jsonl").write_text(intent + "\n", encoding="utf-8")

    code, envelope, _out = _plan(
        tmp_path,
        "--mode",
        "drain_to_zero",
        "--station",
        slug,
        ledgers={slug: (("22-7-fleet", "backlog"),)},
        vcs=vcs,
        capsys=capsys,
    )
    hits = _findings(envelope, "MRS-DRAINPLAN-001")
    assert [("MRS-DISP-039" in f["message"]) for f in hits] == [True]
    assert code == 4


def test_all_stories_evaluates_every_queued_story_as_a_002(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _seed_steward(tmp_path)
    _write_spec(tmp_path, _STEWARD, _K_ESTATE, body=_UNBOUND_SPEC_BODY)  # unbound too, once evaluated
    code, envelope, _out = _steward_plan(tmp_path, capsys, "--all-stories")

    queued = _findings(envelope, "MRS-DRAINPLAN-002")
    estate = [f for f in queued if _K_ESTATE in f["message"]]
    assert any("MRS-GATE-010" in f["message"] for f in estate)  # the full evaluation reached 44.5
    assert any("prose-park" in f["message"] for f in estate)
    cfe = [f["message"] for f in queued if _K_CFE in f["message"]]
    assert len(cfe) == 2  # no tracked spec (MRS-DISP-005) and its park, once each
    assert any("MRS-DISP-005" in m for m in cfe) and any("prose-park" in m for m in cfe)
    assert _K_FOLD not in "".join(f["message"] for f in queued)
    assert envelope["data"]["all_stories"] is True
    assert code == 4


def test_the_next_story_alone_is_evaluated_without_all_stories(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _seed_steward(tmp_path)
    _write_spec(tmp_path, _STEWARD, _K_ESTATE, body=_UNBOUND_SPEC_BODY)
    _code, envelope, _out = _steward_plan(tmp_path, capsys)
    assert [e["story"] for e in _station(envelope)["evaluated"]] == [_K_FOLD]
    assert not any("MRS-GATE-010" in f["message"] and _K_ESTATE in f["message"] for f in envelope["findings"])


def test_a_prose_park_in_the_tracked_spec_is_found(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    slug = "pyforge-marshal"
    _write_spec(tmp_path, slug, "22-7-fleet")
    _write_spec(tmp_path, slug, "22-8-later")
    (dispatch_core.planning_specs_dir(tmp_path, slug) / "spec-22-8-later.md").write_text(
        _spec_text("src/x/**", _BOUND_SPEC_BODY + "\nParked 2026-09-01: do not dispatch until 22.7 lands.\n"),
        encoding="utf-8",
    )
    code, envelope, _out = _plan(
        tmp_path,
        "--mode",
        "drain_to_zero",
        "--station",
        slug,
        ledgers={slug: (("22-7-fleet", "backlog"), ("22-8-later", "backlog"))},
        capsys=capsys,
    )
    parks = _findings(envelope, "MRS-DRAINPLAN-002")
    assert len(parks) == 1 and "22-8-later" in parks[0]["message"] and "tracked spec" in parks[0]["message"]
    assert code == 0  # a park beyond the next story is only a warning


def test_a_line_only_in_the_spec_s_intent_contract_is_not_a_prose_park(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Story 81.2: 73.2's own Never bullet ("Do not dispatch a follow-up ...") is the feature's rule, not a hold."""
    slug = "pyforge-marshal"
    _write_spec(tmp_path, slug, "22-7-fleet")
    _write_spec(tmp_path, slug, "22-8-later")
    contract = (
        "\n<intent-contract>\n\n**Never:**\n- Do not dispatch a follow-up whose row is closed or absent.\n\n"
        "</intent-contract>\n"
    )
    (dispatch_core.planning_specs_dir(tmp_path, slug) / "spec-22-8-later.md").write_text(
        _spec_text("src/x/**", contract + _BOUND_SPEC_BODY),
        encoding="utf-8",
    )
    code, envelope, _out = _plan(
        tmp_path,
        "--mode",
        "drain_to_zero",
        "--station",
        slug,
        ledgers={slug: (("22-7-fleet", "backlog"), ("22-8-later", "backlog"))},
        capsys=capsys,
    )
    assert not _findings(envelope, "MRS-DRAINPLAN-002")
    assert code == 0


def test_a_prose_park_is_reported_but_never_honoured(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The parked story is still the next story -- the plan reports, the declared skip parks."""
    _seed_steward(tmp_path)
    _write_spec(tmp_path, _STEWARD, _K_FOLD)  # binds, so the park is the only refusal
    code, envelope, _out = _steward_plan(tmp_path, capsys)
    row = _station(envelope)
    assert row["next_story"] == _K_FOLD
    assert [r["code"] for r in row["refusals"]] == ["prose-park"]
    assert code == 4


def test_an_unknown_station_is_reported_like_the_drain_reports_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _seed_steward(tmp_path)
    code, envelope, _out = _plan(tmp_path, "--mode", "drain_to_zero", "--station", "nowhere", ledgers={}, capsys=capsys)
    assert _findings(envelope, "MRS-DRAIN-013")
    assert envelope["data"]["stations"] == []
    assert code == 4


def test_a_missing_mode_is_refused_like_the_drain_refuses_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    args = _parse("--plan", "--format", "json")
    code = run_fleet_drain(
        args,
        fs=RecordingFs(),
        vcs=RecordingVcs(tmp_path),
        build_harness=ProbeBuildHarness(),
        process=FakeProcess(alive=False),
        harness=FakeHarness({}),
    )
    assert code == 4
    assert "MRS-DRAIN-001" in capsys.readouterr().out


def test_an_explicit_story_sequence_is_planned_like_the_drain_drains_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _seed_steward(tmp_path)
    _write_spec(tmp_path, _STEWARD, _K_ESTATE)
    _write_spec(tmp_path, _STEWARD, _K_CFE)
    code, envelope, _out = _steward_plan(tmp_path, capsys, "--stories", f"{_K_CFE},{_K_ESTATE}")
    row = _station(envelope)
    assert row["backlog"] == [_K_CFE, _K_ESTATE]
    assert row["next_story"] == _K_CFE
    assert not _findings(envelope, "MRS-DRAINPLAN-003")  # overrides do not apply to an explicit sequence
    assert code == 4  # 44.6 is still parked only in prose


def test_the_text_form_names_the_station_the_refusal_and_the_verdict(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _seed_steward(tmp_path)
    code, _envelope, out = _steward_plan(tmp_path, capsys, text=True)
    assert code == 4
    assert "verdict: error" in out
    assert _STEWARD in out and f"next={_K_FOLD}" in out and "would_dispatch=no" in out
    assert f"refuses {_K_FOLD}: MRS-GATE-010" in out
    assert "finding MRS-DRAINPLAN-001" in out and "finding MRS-DRAINPLAN-003" in out


# --------------------------------------------------------------------------
# Review round: every wave member is graded, the 005 row, --check-env, the wave
# --------------------------------------------------------------------------

_PARALLEL_LEDGER = (("1-1-alpha", "backlog"), ("1-2-beta", "backlog"))


def test_a_refusal_on_the_second_wave_member_is_as_fatal_as_the_first(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Every wave member is handed to `dispatch_once`: beta's missing `## Verification` is a 001, not a 002."""
    slug = "pyforge-marshal"
    _write_spec(tmp_path, slug, "1-1-alpha", surface="src/a/**")
    _write_spec(tmp_path, slug, "1-2-beta", surface="src/b/**", body=_UNBOUND_SPEC_BODY)
    code, envelope, _out = _plan(
        tmp_path,
        "--mode",
        "drain_to_zero",
        "--station",
        slug,
        "--max-in-flight",
        "2",
        ledgers={slug: _PARALLEL_LEDGER},
        capsys=capsys,
    )

    row = _station(envelope, slug)
    assert row["stories"] == ["1-1-alpha", "1-2-beta"]
    assert row["next_story"] == "1-1-alpha"  # the queue head is unchanged
    hits = _findings(envelope, "MRS-DRAINPLAN-001")
    assert len(hits) == 1
    assert "1-2-beta" in hits[0]["message"] and "MRS-GATE-010" in hits[0]["message"]
    assert not _findings(envelope, "MRS-DRAINPLAN-002")
    assert row["would_dispatch"] is False
    assert code == 4


def test_a_held_head_outside_the_wave_stays_a_warning(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A story the wave holds out is NOT handed to `dispatch_once`, so its refusals are 002 WARNs."""
    ledgers = _seed_unmet_deps(tmp_path)
    _write_spec(tmp_path, _STEWARD, _K_FOLD, surface="src/fold/**", body=_UNBOUND_SPEC_BODY)
    code, envelope, _out = _plan(
        tmp_path,
        "--mode",
        "drain_to_zero",
        "--station",
        _STEWARD,
        "--max-in-flight",
        "2",
        ledgers=ledgers,
        capsys=capsys,
    )

    row = _station(envelope)
    assert row["stories"] == [_K_KERNEL] and [h["story"] for h in row["held"]] == [_K_FOLD]
    assert not _findings(envelope, "MRS-DRAINPLAN-001")
    held_warns = [f for f in _findings(envelope, "MRS-DRAINPLAN-002") if _K_FOLD in f["message"]]
    assert len(held_warns) == 1 and "MRS-GATE-010" in held_warns[0]["message"]
    assert row["would_dispatch"] is True  # the wave member itself is clean
    assert code == 0


_STATION_ROW_KEYS = (
    "slug",
    "mode",
    "parallel_cap",
    "backlog",
    "outcome",
    "next_story",
    "stories",
    "wave",
    "held",
    "followups",
    "would_dispatch",
    "land_only",
    "refusals",
    "prose_parks",
    "skipped",
    "deps",
    "evaluated",
    "env_checked",
)


def test_an_unevaluable_row_carries_every_key_a_computed_row_carries(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    slug = "pyforge-marshal"
    _write_spec(tmp_path, slug, "22-7-fleet")
    (tmp_path / "_bmad-output" / "projects" / "pyforge-doctor").mkdir(parents=True)
    _code, envelope, _out = _plan(
        tmp_path,
        "--mode",
        "drain_to_zero",
        ledgers={slug: (("22-7-fleet", "backlog"),)},  # pyforge-doctor's ledger cannot be read
        capsys=capsys,
    )

    good, bad = _station(envelope, slug), _station(envelope, "pyforge-doctor")
    assert set(_STATION_ROW_KEYS) <= set(good)
    assert set(good) <= set(bad)  # a consumer indexing a row never KeyErrors on a failure row
    assert bad["outcome"] == "unevaluable" and bad["backlog"] == []
    assert bad["parallel_cap"] is None and bad["wave"] is None
    assert bad["held"] == bad["land_only"] == bad["prose_parks"] == bad["evaluated"] == []
    assert bad["would_dispatch"] is False and bad["env_checked"] is False


def test_the_station_row_skeleton_is_the_one_source_of_both_rows() -> None:
    mode = FleetCampaignMode.DRAIN_TO_ZERO
    skeleton = drain_plan._station_row("pyforge-x", mode, parallel_cap=None, backlog=(), env_checked=False)
    failed, _finding = drain_plan._unevaluable("pyforge-x", mode, "boom")
    assert set(skeleton) == set(_STATION_ROW_KEYS)
    assert set(failed) == set(skeleton) | {"detail"}


# -- --check-env: the harness preference and the session probe ---------------

_CURSOR_LEAD_TIER_MAP = {"medium": {"dev": {"harness": "cursor", "model": "composer-2.5-fast"}}}


def _pin_project_policy(monkeypatch: pytest.MonkeyPatch, **project: object) -> None:
    """Compose every station's policy from ``project`` alone (plus the plan's own flags)."""

    def _compose(slug, *, flags=None):
        effective, _findings_ = policy.compose(project_slug=slug, project=project, flags=dict(flags or {}))
        return effective

    monkeypatch.setattr(dispatch_cli, "_compose_policy", _compose)


def _check_env_preference(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], *extra: str
) -> tuple[list[str], list[tuple[str, ...]]]:
    """Plan ``pyforge-marshal --check-env``; returns ``(env["preference"], the lists binary_present was handed)``."""
    slug = "pyforge-marshal"
    build_harness = ProbeBuildHarness()
    code, envelope, _out = _plan(
        tmp_path,
        "--mode",
        "drain_to_zero",
        "--station",
        slug,
        "--check-env",
        *extra,
        ledgers={slug: (("22-7-fleet", "backlog"),)},
        build_harness=build_harness,
        capsys=capsys,
    )
    assert code == 0
    return _station(envelope, slug)["env"]["preference"], build_harness.preferences


def test_check_env_walks_the_tier_maps_harness_first_without_a_harness_flag(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_spec(tmp_path, "pyforge-marshal", "22-7-fleet")
    _pin_project_policy(monkeypatch, harness_preference=["claude", "cursor"], model_tier_map=_CURSOR_LEAD_TIER_MAP)
    preference, walked = _check_env_preference(tmp_path, capsys)
    assert preference == ["cursor", "claude"]
    assert walked == [("cursor", "claude")]


def test_check_env_lets_an_explicit_harness_flag_outrank_the_tier_lead(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_spec(tmp_path, "pyforge-marshal", "22-7-fleet")
    _pin_project_policy(monkeypatch, harness_preference=["claude", "cursor"], model_tier_map=_CURSOR_LEAD_TIER_MAP)
    preference, walked = _check_env_preference(tmp_path, capsys, "--harness", "claude,gemini")
    assert preference == ["claude", "gemini"]  # cursor, the tier lead the flag does not name, contributes nothing
    assert walked == [("claude", "gemini")]


def _seed_failed_run(repo: Path, slug: str, story_feed: str, session_log: str) -> None:
    """A finished, `failed` dispatch run of ``story_feed`` whose session log is ``session_log``."""
    from pyforge.marshal.core.journal import JournalEntryId, Phase, build_entry, prepare_for_write

    run_id = f"{slug}-20260901T000000000Z-abcd1234"
    run_dir = dispatch_core.dispatch_run_dir(repo, slug, run_id)
    run_dir.mkdir(parents=True)
    intent = build_entry(
        id=JournalEntryId("w", 0),
        ts="2026-09-01T00:00:00.000Z",
        run_id=run_id,
        kind=dispatch_core.KIND_DISPATCH_LAUNCH,
        phase=Phase.INTENT,
        payload={"story_key": story_feed},
    )
    completion_intent = build_entry(
        id=JournalEntryId("w", 2),
        ts="2026-09-01T00:01:00.000Z",
        run_id=run_id,
        kind=dispatch_core.KIND_DISPATCH_COMPLETION,
        phase=Phase.INTENT,
        payload={"verdict": "failed"},
    )
    completion_outcome = build_entry(
        id=JournalEntryId("w", 3),
        ts="2026-09-01T00:01:01.000Z",
        run_id=run_id,
        kind=dispatch_core.KIND_DISPATCH_COMPLETION,
        phase=Phase.OUTCOME,
        intent_id=JournalEntryId("w", 2),
        payload={"verdict": "failed", "ok": True},
    )
    lines = [prepare_for_write(entry).line for entry in (intent, completion_intent, completion_outcome)]
    (run_dir / "journal.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (run_dir / "session.log").write_text(session_log, encoding="utf-8")


def test_check_env_drops_the_profile_a_transient_failed_session_log_excludes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    slug = "pyforge-marshal"
    _write_spec(tmp_path, slug, "22-7-fleet")
    _seed_failed_run(tmp_path, slug, "22.7", "You have hit your usage limit for this month.")
    _pin_project_policy(monkeypatch, harness_preference=["claude", "cursor"])
    preference, walked = _check_env_preference(tmp_path, capsys)
    assert preference == ["cursor"]  # claude hit its quota last time: the walk starts past it
    assert walked == [("cursor",)]


def test_check_env_session_probe_that_is_not_ok_is_a_warn_and_never_changes_the_exit(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    slug = "pyforge-marshal"
    _write_spec(tmp_path, slug, "22-7-fleet")
    process = FakeProcess(alive=False, session_check_returncode=1)
    code, envelope, _out = _plan(
        tmp_path,
        "--mode",
        "drain_to_zero",
        "--station",
        slug,
        "--check-env",
        ledgers={slug: (("22-7-fleet", "backlog"),)},
        process=process,
        capsys=capsys,
    )

    hits = _findings(envelope, "MRS-DISP-049")
    assert len(hits) == 1 and hits[0]["severity"] == "warn"
    assert envelope["data"]["session_check"] == hits[0]["message"] != "ok"
    assert len(process.run_calls) == 1
    assert code == 0


# -- the wave: its id, its refusals, why a story is held ----------------------


def test_each_cycle_mints_its_own_wave_id_journals_it_and_names_it_in_the_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    slug = "pyforge-marshal"
    keys = ("1-1-alpha", "1-2-beta", "1-3-gamma")
    for index, key in enumerate(keys):
        _write_spec(tmp_path, slug, key, surface=f"src/{index}/**")
    ledgers = {slug: tuple((key, "backlog") for key in keys)}
    _record_launches(monkeypatch)
    monkeypatch.setattr(dispatch_cli, "_journal_dispatch_wave", _REAL_JOURNAL_DISPATCH_WAVE)

    reports = [_run_one_cycle(tmp_path, ledgers, station=slug, max_in_flight=2) for _ in range(2)]

    wave_ids: list[str] = []
    for report in reports:
        (result,) = report.results
        match = re.match(r"wave (\S+): ", result.detail or "")
        assert match is not None, result.detail
        wave_id = match.group(1)
        wave_ids.append(wave_id)
        refused = [f for f in report.findings if f.code == "MRS-DRAIN-016"]
        assert len(refused) == 1  # cap 2: gamma is left out
        assert wave_id in refused[0].message and "1-3-gamma" in refused[0].message
    assert wave_ids[0] != wave_ids[1]
    waves_dir = dispatch_core.dispatch_runs_dir(tmp_path, slug) / "waves"
    assert sorted(path.name for path in waves_dir.iterdir()) == sorted(wave_ids)
    for wave_id in wave_ids:
        assert wave_id in (waves_dir / wave_id / "journal.jsonl").read_text(encoding="utf-8")


def test_a_wave_plan_reports_what_the_wave_refused_and_why(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    slug = "pyforge-marshal"
    # A wave compares EFFECTIVE surfaces (the spec's, narrowed to the station's derived policy surface): use
    # paths inside it, with the repo's own marshal-policy out of the picture.
    _pin_project_policy(monkeypatch)
    inside = "src/shared/packages/pyforge-marshal/**"
    _write_spec(tmp_path, slug, "1-1-alpha", surface=inside)
    _write_spec(tmp_path, slug, "1-2-beta", surface=inside)  # overlaps alpha
    code, envelope, _out = _plan(
        tmp_path,
        "--mode",
        "drain_to_zero",
        "--station",
        slug,
        "--max-in-flight",
        "2",
        ledgers={slug: _PARALLEL_LEDGER},
        capsys=capsys,
    )

    row = _station(envelope, slug)
    assert row["stories"] == ["1-1-alpha"]
    assert row["wave"]["members"] == ["1-1-alpha"]
    assert row["wave"]["refused"] == [{"story": "1-2-beta", "reason": "surface-overlap", "overlap_with": "1-1-alpha"}]
    assert row["held"] == [{"story": "1-2-beta", "reason": "refused from the wave: surface-overlap"}]
    assert code == 0


def test_held_reason_names_unmet_deps_then_the_wave_rule_then_falls_back(tmp_path: Path) -> None:
    """The plan cannot reach the fallback (a head no rule refused is always a wave member), so it is pinned here."""
    refused = dispatch_fleet.WaveRefused(story="1-3-gamma", reason="cap")
    wave = dispatch_fleet.WaveBatch(wave_id="w", members=("1-2-beta",), refused=(refused,), max_parallel=2)
    cycle = dispatch_cli.StationCyclePlan(slug="pyforge-marshal", ledger_path=tmp_path / "ledger.yaml", wave=wave)
    reads = drain_plan._StationReads(
        repo_root=tmp_path, slug="pyforge-marshal", cycle=cycle, fs=FakeFs(), vcs=FakeVcs(tmp_path)
    )

    assert drain_plan._held_reason(reads, "1-3-gamma", {}) == "refused from the wave: cap"
    assert drain_plan._held_reason(reads, "1-1-alpha", {}) == "not selected for this wave"
    unmet = drain_plan._held_reason(reads, "44-4-fold", {"44.4": (normalize("44.3"),)})
    assert unmet == "declared Deps not all done: 44.3"


# -- Story 81.1: a wave that holds every story is `held`, never a traceback ----


def _seed_held_wave(repo: Path) -> dict[str, tuple[tuple[str, str], ...]]:
    """44.4 is the only backlog story and its Dep 44.3 is not done: the queue walk answers DISPATCH, the wave admits none."""
    _write_epics(repo, _STEWARD, _DEPS_EPICS)
    _write_spec(repo, _STEWARD, _K_FOLD, surface="src/fold/**")
    return {_STEWARD: ((_K_FOLD, "backlog"),)}


def test_a_cycle_whose_wave_holds_every_story_reports_held_instead_of_crashing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ledgers = _seed_held_wave(tmp_path)

    report = _run_one_cycle(tmp_path, ledgers, station=_STEWARD, max_in_flight=2)

    (result,) = report.results
    assert result.status is dispatch_fleet.StationCycleStatus.HELD
    assert result.story == _K_FOLD and result.remaining == 1
    (warn,) = [f for f in report.findings if f.code == "MRS-DRAIN-016"]
    assert warn.severity is Severity.WARN
    assert _K_FOLD in warn.message
    # Nothing is in flight and nothing launches: ticking again cannot move it, so the campaign is complete.
    assert report.complete is True
    assert report.data["unresolved"] == [{"station": _STEWARD, "status": "held", "remaining": 1}]

    # The plan reads the same state as `held`, in the same words.
    _code, envelope, _out = _plan(
        tmp_path,
        "--mode",
        "drain_to_zero",
        "--station",
        _STEWARD,
        "--max-in-flight",
        "2",
        ledgers=ledgers,
        capsys=capsys,
    )
    row = _station(envelope)
    assert row["outcome"] == "held"
    (held,) = row["held"]
    assert held["story"] == _K_FOLD and held["reason"] == "declared Deps not all done: 44.3"
    assert warn.message.endswith(held["reason"]) and result.detail == f"{_K_FOLD}: {held['reason']}"


def test_dispatch_stories_on_a_held_wave_reports_the_held_stories(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ledgers = _seed_held_wave(tmp_path)
    process = FakeProcess(alive=False)
    args = argparse.Namespace(slug=_STEWARD, story=None, stories=_K_FOLD, format="json", harness=None, max_in_flight=2)

    code = dispatch_cli.run_dispatch(
        args,
        fs=FakeFs(),
        vcs=FakeVcs(tmp_path),
        build_harness=FakeBuildHarness(),
        process=process,
        harness=FakeHarness(ledgers),
    )

    envelope = json.loads(capsys.readouterr().out)
    (row,) = envelope["data"]["stations"]
    assert row["status"] == "held" and row["story"] == _K_FOLD
    assert envelope["data"]["complete"] is True
    assert process.spawned == []  # a held station is terminal: no campaign supervisor to poll it
    held = _findings(envelope, "MRS-DRAIN-016")
    assert len(held) == 1 and "44.3" in held[0]["message"]
    assert code == 0  # WARN never changes the exit


def test_dispatch_stories_on_a_held_wave_says_why_in_text_mode(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The operator's surface is the text report, not the envelope: the held story and its Dep must be on it."""
    ledgers = _seed_held_wave(tmp_path)
    args = argparse.Namespace(slug=_STEWARD, story=None, stories=_K_FOLD, format="text", harness=None, max_in_flight=2)

    code = dispatch_cli.run_dispatch(
        args,
        fs=FakeFs(),
        vcs=FakeVcs(tmp_path),
        build_harness=FakeBuildHarness(),
        process=FakeProcess(alive=False),
        harness=FakeHarness(ledgers),
    )

    out = capsys.readouterr().out
    assert "held" in out and _K_FOLD in out and "declared Deps not all done: 44.3" in out
    assert "ValueError" not in out and code == 0


def test_a_wave_that_refuses_its_only_story_reports_held_and_names_it_once(
    tmp_path: Path,
) -> None:
    """The refusal loop already names a story the wave itself refused; the held block must not name it again."""
    _write_epics(tmp_path, _STEWARD, _DEPS_EPICS)
    specs = dispatch_core.planning_specs_dir(tmp_path, _STEWARD)
    specs.mkdir(parents=True, exist_ok=True)
    # A multi-line `surface:` block is unsupported, so the wave never fans the story out (CAP-5).
    block_surface = "---\nstatus: backlog\nsurface:\n  - src/kernel/**\n---\n" + _BOUND_SPEC_BODY
    (specs / f"spec-{_K_KERNEL}.md").write_text(block_surface, encoding="utf-8")

    report = _run_one_cycle(tmp_path, {_STEWARD: ((_K_KERNEL, "backlog"),)}, station=_STEWARD, max_in_flight=2)

    (result,) = report.results
    assert result.status is dispatch_fleet.StationCycleStatus.HELD
    assert result.detail == f"{_K_KERNEL}: refused from the wave: unknown-surface"
    (warn,) = [f for f in report.findings if f.code == "MRS-DRAIN-016"]
    assert "refused" in warn.message and "unknown-surface" in warn.message


def test_wave_held_stories_is_empty_without_a_wave(tmp_path: Path) -> None:
    cycle = dispatch_cli.StationCyclePlan(slug=_STEWARD, ledger_path=tmp_path / "ledger.yaml")
    assert dispatch_cli.wave_held_stories(cycle) == ()


def test_a_wave_that_admits_a_story_still_reports_dispatched(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ledgers = _seed_unmet_deps(tmp_path)  # the head (44.4) is held by 44.3, but the wave admits 44.3 itself
    launches = _record_launches(monkeypatch)
    monkeypatch.setattr(dispatch_cli, "_journal_dispatch_wave", lambda *a, **k: None)

    report = _run_one_cycle(tmp_path, ledgers, station=_STEWARD, max_in_flight=2)

    (result,) = report.results
    assert result.status is dispatch_fleet.StationCycleStatus.DISPATCHED
    assert launches == [(_STEWARD, _K_KERNEL)]
    assert not [f for f in report.findings if f.code == "MRS-DRAIN-016"]


# -- a verify command the gate cannot even tokenize ---------------------------


def test_a_verify_command_with_an_unbalanced_quote_is_gate_003_cannot_parse(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    slug = "pyforge-marshal"
    _write_spec(tmp_path, slug, "22-7-fleet")
    _with_policy_flags(monkeypatch, verify_commands=["pixi run 'never closed"])
    code, envelope, _out = _plan(
        tmp_path,
        "--mode",
        "drain_to_zero",
        "--station",
        slug,
        ledgers={slug: (("22-7-fleet", "backlog"),)},
        capsys=capsys,
    )

    hits = [f for f in _findings(envelope, "MRS-DRAINPLAN-001") if "MRS-GATE-003" in f["message"]]
    assert len(hits) == 1
    assert "cannot parse verify command" in hits[0]["message"] and "never closed" in hits[0]["message"]
    assert code == 4


# --------------------------------------------------------------------------
# Story 73.2 (CAP-281) -- the follow-up reviews a drain would queue
# --------------------------------------------------------------------------


class _FollowupPlanVcs(RecordingVcs, _FollowupVcs):
    """The plan's write-forbidding vcs, with what a follow-up plan reads at ``origin/main``."""


def _pin_repository_layers(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, cap: int | None = None) -> None:
    """The drain reads the repository's policy layers from the real checkout; pin them so the cap is Marshal's
    default (2) -- or ``cap`` set as `_bmad-output/policy-defaults.toml` would."""
    defaults: dict[str, object] = {} if cap is None else {"dispatch": {"max_followup_reviews_per_campaign": cap}}
    monkeypatch.setattr(dispatch_cli, "read_repo_policy_defaults", lambda: (defaults, None))
    monkeypatch.setattr(dispatch_cli, "conventional_project_policy_path", lambda slug: tmp_path / f"{slug}-none.toml")


def _seed_followup_station(tmp_path: Path, vcs: _FollowupPlanVcs, entries) -> tuple[tuple[str, str], ...]:
    """``_fu_seed_station``, with the primary's tracked specs bound (a `## Verification` section) so the plan's
    own launch checks (MRS-GATE-010) have nothing to say about them."""
    statuses = _fu_seed_station(tmp_path, vcs, _FU_SLUG, entries)
    for story, _text, _row in entries:
        path = dispatch_core.planning_specs_dir(tmp_path, _FU_SLUG) / f"spec-{story}.md"
        path.write_text(_fu_spec() + _BOUND_SPEC_BODY, encoding="utf-8")
    return statuses


def _plan_followups(tmp_path: Path, capsys: pytest.CaptureFixture[str], vcs: _FollowupPlanVcs, ledgers, *extra: str):
    return _plan(
        tmp_path,
        "--mode",
        "drain_to_zero",
        "--station",
        _FU_SLUG,
        *extra,
        ledgers={_FU_SLUG: ledgers},
        vcs=vcs,
        capsys=capsys,
    )


def test_the_plan_lists_the_follow_up_review_of_an_open_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _pin_repository_layers(monkeypatch, tmp_path)
    vcs = _FollowupPlanVcs(tmp_path)
    ledgers = _seed_followup_station(tmp_path, vcs, [(_FU_STORY, _fu_spec(), "open")])
    # The story's first landing is on origin/main -- which does NOT make its follow-up "already landed".
    vcs.subjects = (_fu_subject(_FU_SLUG, _FU_STORY),)

    code, envelope, _out = _plan_followups(tmp_path, capsys, vcs, ledgers)

    row = _station(envelope, _FU_SLUG)
    assert row["followups"] == [_FU_STORY]
    assert row["backlog"] == [_FU_STORY]
    assert row["next_story"] == _FU_STORY
    assert row["outcome"] == "dispatch" and row["stories"] == [_FU_STORY]
    assert row["would_dispatch"] is True and row["refusals"] == []
    assert not _findings(envelope, "MRS-DRAINPLAN-001")
    assert code == 0


def test_the_plan_text_names_the_follow_up_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _pin_repository_layers(monkeypatch, tmp_path)
    vcs = _FollowupPlanVcs(tmp_path)
    ledgers = _seed_followup_station(tmp_path, vcs, [(_FU_STORY, _fu_spec(), "open")])

    _code, _envelope, out = _plan(
        tmp_path,
        "--mode",
        "drain_to_zero",
        "--station",
        _FU_SLUG,
        ledgers={_FU_SLUG: ledgers},
        vcs=vcs,
        capsys=capsys,
        text=True,
    )
    assert f"follow-up review {_FU_STORY}" in out


def test_the_plan_names_a_stale_row_and_how_many_follow_ups_wait(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _pin_repository_layers(monkeypatch, tmp_path, cap=1)
    vcs = _FollowupPlanVcs(tmp_path)
    ledgers = _seed_followup_station(
        tmp_path,
        vcs,
        [
            ("60-1-oldest", _fu_spec(), "open"),
            ("60-2-newest", _fu_spec(), "open"),
            ("60-3-middle", _fu_spec(), "open"),
            ("60-4-turned-false", _fu_spec(flag=False), "open"),
        ],
    )
    vcs.subjects = (
        _fu_subject(_FU_SLUG, "60-2-newest"),
        _fu_subject(_FU_SLUG, "60-3-middle"),
        _fu_subject(_FU_SLUG, "60-1-oldest"),
    )

    code, envelope, _out = _plan_followups(tmp_path, capsys, vcs, ledgers)

    row = _station(envelope, _FU_SLUG)
    assert row["followups"] == ["60-2-newest"]  # the cap (1), newest landing first
    (stale,) = _findings(envelope, "MRS-DRAIN-018")
    assert "DW-FRR-60-4" in stale["message"] and "followup_review_recommended" in stale["message"]
    (waiting,) = _findings(envelope, "MRS-DRAIN-019")
    assert "2 follow-up review(s) wait for a later campaign" in waiting["message"]
    assert "is 1" in waiting["message"]
    assert code == 0  # both are advisory: exit 0


def test_the_plan_with_no_follow_up_rows_is_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _pin_repository_layers(monkeypatch, tmp_path)
    vcs = _FollowupPlanVcs(tmp_path)
    _write_spec(tmp_path, _FU_SLUG, "52-1-implementable")

    _code, envelope, _out = _plan_followups(tmp_path, capsys, vcs, (("52-1-implementable", "backlog"),))

    row = _station(envelope, _FU_SLUG)
    assert row["followups"] == [] and row["backlog"] == ["52-1-implementable"]
    assert not _findings(envelope, "MRS-DRAIN-018") and not _findings(envelope, "MRS-DRAIN-019")


def test_the_plan_never_lists_a_follow_up_under_stories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _pin_repository_layers(monkeypatch, tmp_path)
    vcs = _FollowupPlanVcs(tmp_path)
    statuses = _seed_followup_station(tmp_path, vcs, [(_FU_STORY, _fu_spec(), "open")])
    _write_spec(tmp_path, _FU_SLUG, "52-1-implementable")

    _code, envelope, _out = _plan_followups(
        tmp_path, capsys, vcs, (("52-1-implementable", "backlog"), *statuses), "--stories", "52-1-implementable"
    )

    row = _station(envelope, _FU_SLUG)
    assert row["followups"] == [] and row["backlog"] == ["52-1-implementable"]
    assert not _findings(envelope, "MRS-DRAIN-019")


def test_the_plan_reads_but_never_writes_for_a_follow_up(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _pin_repository_layers(monkeypatch, tmp_path)
    vcs = _FollowupPlanVcs(tmp_path)
    ledgers = _seed_followup_station(tmp_path, vcs, [(_FU_STORY, _fu_spec(), "open")])
    before = _tree(tmp_path)

    _plan_followups(tmp_path, capsys, vcs, ledgers)

    assert _tree(tmp_path) == before
    assert vcs.writes == [] and _fu_ledger_rel(_FU_SLUG) in {path for _ref, path in vcs.reads}
    # CAP-274: a plan reaches no remote and writes no ref either -- unlike the drain, it never fetches, so it
    # reads origin/main as this checkout holds it.
    assert vcs.fetched == []


def test_the_plan_names_an_unreadable_deferred_work_ledger_and_still_plans_the_station(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _pin_repository_layers(monkeypatch, tmp_path)
    vcs = _FollowupPlanVcs(tmp_path)
    ledgers = _seed_followup_station(tmp_path, vcs, [(_FU_STORY, _fu_spec(), "open")])
    vcs.unreadable.add(_fu_ledger_rel(_FU_SLUG))

    _code, envelope, _out = _plan_followups(tmp_path, capsys, vcs, ledgers)

    (warning,) = _findings(envelope, "MRS-DRAIN-018")
    assert _fu_ledger_rel(_FU_SLUG) in warning["message"]
    row = _station(envelope, _FU_SLUG)
    assert row["followups"] == [] and row["outcome"] == "drained"


def test_the_plan_row_carries_the_followups_key_on_an_unevaluable_station_too(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _pin_repository_layers(monkeypatch, tmp_path)
    (tmp_path / "_bmad-output" / "projects" / _FU_OTHER_SLUG).mkdir(parents=True)
    vcs = _FollowupPlanVcs(tmp_path)
    ledgers = _seed_followup_station(tmp_path, vcs, [(_FU_STORY, _fu_spec(), "open")])

    _code, envelope, _out = _plan(
        tmp_path,
        "--mode",
        "drain_to_zero",
        ledgers={_FU_SLUG: ledgers},  # pyforge-doctor's ledger cannot be read
        vcs=vcs,
        capsys=capsys,
    )
    assert _station(envelope, _FU_OTHER_SLUG)["followups"] == []
    assert _station(envelope, _FU_SLUG)["followups"] == [_FU_STORY]
