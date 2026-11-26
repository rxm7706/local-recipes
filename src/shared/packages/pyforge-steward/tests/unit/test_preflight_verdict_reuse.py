"""Story 117.17 (spec-pyforge-steward CAP-154, CAP-175): a push reuses the green verdict its tree already has.

``run_preflight(reuse=True)`` starts no lane when the journal holds a run with verdict ``ok`` that recorded this same
clean tree, base and environment and in which every lane this run selects passed. Anything else runs the lanes: a
dirty or untracked file, another tree, another base, a lane the earlier run did not pass, a red run, the opt-out.
Each test builds its own git repository, so nothing here reads the checkout.
"""

from __future__ import annotations

import json
import subprocess
import threading
from pathlib import Path

import pytest

from pyforge.steward import preflight

INV = "pyforge-guild"
_NOOP_INSTALL = lambda _env: 0  # noqa: E731
LANES = {"alpha": "pytest a -q", "beta": "pytest b -q"}


@pytest.fixture(autouse=True)
def _one_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    # The suite itself runs inside a preflight lane, whose variables must not reach the digest under test unevenly.
    monkeypatch.delenv("PYTEST_XDIST_AUTO_NUM_WORKERS", raising=False)
    monkeypatch.delenv(preflight.REUSE_ENV, raising=False)


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)
    return done.stdout.strip()


def _pixi(lanes: dict[str, str]) -> str:
    body = "\n".join(f'[feature.guild-tasks.tasks.{name}]\ncmd = "{cmd}"\n' for name, cmd in lanes.items())
    deps = ", ".join(f'"{name}"' for name in lanes)
    return f"[feature.guild-tasks.tasks.pr-preflight-lanes]\ndepends-on = [{deps}]\n\n{body}"


def _commit(repo: Path, message: str) -> None:
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", message)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A committed checkout with two lanes, the journal ignored, and the base ref the selection reads."""
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "work")
    (root / "pixi.toml").write_text(_pixi(LANES), encoding="utf-8")
    (root / ".gitignore").write_text(".steward/\n", encoding="utf-8")
    (root / "tracked.txt").write_text("one\n", encoding="utf-8")
    _commit(root, "first")
    _git(root, "update-ref", "refs/remotes/origin/main", "HEAD")
    return root


class Runs:
    """Counts the lanes a run starts; ``red`` names lanes that fail."""

    def __init__(self) -> None:
        self.started: list[str] = []
        self.red: set[str] = set()
        self._lock = threading.Lock()

    def __call__(self, ctx: preflight.LaneRunContext) -> int:
        with self._lock:
            self.started.append(ctx.lane.task)
        return 1 if ctx.lane.task in self.red else 0


def _run(repo: Path, runs: Runs, *, reuse: bool = True, keep_going: bool = False) -> int:
    return preflight.run_preflight(
        repo,
        invoking_env=INV,
        jobs=2,
        logical_cores=2,
        critical_path=False,
        keep_going=keep_going,
        install_environment=_NOOP_INSTALL,
        run_lane_ctx=runs,
        scratch_parent=repo.parent / "scratch",
        reuse=reuse,
    )


def _journal(repo: Path) -> list[dict]:
    path = repo / preflight.JOURNAL_RELATIVE
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_a_second_run_of_the_same_clean_tree_starts_no_lane(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runs = Runs()
    assert _run(repo, runs) == preflight.EXIT_OK
    assert sorted(runs.started) == ["alpha", "beta"]
    first = [r for r in _journal(repo) if "lanes" in r][-1]
    assert first["tree"]["clean"] is True and first["tree"]["tree_sha"] == _git(repo, "rev-parse", "HEAD^{tree}")
    capsys.readouterr()

    assert _run(repo, runs) == preflight.EXIT_OK
    assert sorted(runs.started) == ["alpha", "beta"], "the second run must start no lane"
    reuse = _journal(repo)[-1]
    assert reuse["phase"] == "reuse" and reuse["verdict"] == "ok"
    assert reuse["reused_run_id"] == first["run_id"]
    assert reuse["lanes_covered"] == [f"alpha@{INV}", f"beta@{INV}"]
    assert "lanes" not in reuse, "a reuse record must never read as a run that judged lanes"
    err = capsys.readouterr().err
    assert first["run_id"] in err and f"{preflight.REUSE_ENV}=0" in err


def test_reuse_is_off_unless_the_caller_asks(repo: Path) -> None:
    runs = Runs()
    assert _run(repo, runs, reuse=False) == preflight.EXIT_OK
    assert _run(repo, runs, reuse=False) == preflight.EXIT_OK
    assert len(runs.started) == 4


@pytest.mark.parametrize("change", ["tracked-edit", "staged-edit", "untracked-file"])
def test_a_tree_that_is_not_clean_runs_its_lanes(repo: Path, change: str) -> None:
    runs = Runs()
    assert _run(repo, runs) == preflight.EXIT_OK
    if change == "untracked-file":
        (repo / "new.txt").write_text("x\n", encoding="utf-8")
    else:
        (repo / "tracked.txt").write_text("two\n", encoding="utf-8")
        if change == "staged-edit":
            _git(repo, "add", "tracked.txt")
    assert _run(repo, runs) == preflight.EXIT_OK
    assert len(runs.started) == 4
    assert [r for r in _journal(repo) if "lanes" in r][-1]["tree"] is None, "a dirty tree journals no state to reuse"
    # ...and a third run cannot reuse the dirty run either.
    assert _run(repo, runs) == preflight.EXIT_OK
    assert len(runs.started) == 6


def test_another_commit_runs_its_lanes(repo: Path) -> None:
    runs = Runs()
    assert _run(repo, runs) == preflight.EXIT_OK
    (repo / "tracked.txt").write_text("two\n", encoding="utf-8")
    _commit(repo, "second")
    assert _run(repo, runs) == preflight.EXIT_OK
    assert len(runs.started) == 4


def test_a_base_that_moved_runs_its_lanes(repo: Path) -> None:
    runs = Runs()
    assert _run(repo, runs) == preflight.EXIT_OK
    first = _git(repo, "rev-parse", "HEAD")
    (repo / "tracked.txt").write_text("two\n", encoding="utf-8")
    _commit(repo, "second")
    _git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
    assert _run(repo, runs) == preflight.EXIT_OK  # green on the new tree against the new base
    assert len(runs.started) == 4
    _git(repo, "update-ref", "refs/remotes/origin/main", first)
    assert _run(repo, runs) == preflight.EXIT_OK
    assert len(runs.started) == 6, "the same tree against another base was never judged"


def test_a_red_run_is_never_reused(repo: Path) -> None:
    runs = Runs()
    runs.red = {"beta"}
    assert _run(repo, runs, keep_going=True) == preflight.EXIT_LANE_RED
    runs.red = set()
    assert _run(repo, runs) == preflight.EXIT_OK
    assert len(runs.started) == 4


def test_a_run_that_did_not_pass_every_selected_lane_is_not_enough(repo: Path) -> None:
    """A narrower earlier run (here: one lane of two) covers nothing wider; the wider run then covers the narrower."""
    runs = Runs()
    assert _run(repo, runs) == preflight.EXIT_OK
    path = repo / preflight.JOURNAL_RELATIVE
    records = _journal(repo)
    for record in records:
        if "lanes" in record:
            record["lanes"] = [lane for lane in record["lanes"] if lane["task"] == "alpha"]
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    assert _run(repo, runs) == preflight.EXIT_OK
    assert len(runs.started) == 4, "beta was not judged by the earlier run"

    state = preflight.tree_state(repo)
    one_lane = [preflight.Lane("alpha", INV)]
    assert preflight.reusable_run(path, state, one_lane) is not None, "a run of both lanes covers a run of one"


def test_a_reuse_record_is_never_the_proof_of_another_reuse(repo: Path) -> None:
    runs = Runs()
    assert _run(repo, runs) == preflight.EXIT_OK
    assert _run(repo, runs) == preflight.EXIT_OK  # reused
    path = repo / preflight.JOURNAL_RELATIVE
    only_reuse = [r for r in _journal(repo) if r.get("phase") == "reuse"]
    assert len(only_reuse) == 1
    path.write_text("\n".join(json.dumps(r) for r in only_reuse) + "\n", encoding="utf-8")
    assert _run(repo, runs) == preflight.EXIT_OK
    assert len(runs.started) == 4, "with only a reuse record left, the lanes run"


def test_an_environment_variable_a_lane_can_read_is_part_of_the_state(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runs = Runs()
    assert _run(repo, runs) == preflight.EXIT_OK
    monkeypatch.setenv("PYFORGE_FLAGS_PATH", "/somewhere/else.json")
    assert _run(repo, runs) == preflight.EXIT_OK
    assert len(runs.started) == 4
    # Every pytest lane inherits PYTEST_ADDOPTS, and it can deselect tests: a run under other options is another state.
    assert _run(repo, runs) == preflight.EXIT_OK
    assert len(runs.started) == 4, "the same variables: the second run of this state is reused"
    monkeypatch.setenv("PYTEST_ADDOPTS", "--splits 2 --group 1")
    assert _run(repo, runs) == preflight.EXIT_OK
    assert len(runs.started) == 6
    # The scope and the opt-out choose which lanes run, not what a lane sees: they are not part of the state.
    before = preflight.tree_state(repo)
    monkeypatch.setenv(preflight.SCOPE_ENV, "touched")
    monkeypatch.setenv(preflight.REUSE_ENV, "1")
    assert preflight.tree_state(repo) == before


def test_a_tree_that_moves_while_the_lanes_run_journals_no_state(repo: Path) -> None:
    class Editing(Runs):
        def __call__(self, ctx: preflight.LaneRunContext) -> int:
            (repo / "tracked.txt").write_text("edited during the run\n", encoding="utf-8")
            return super().__call__(ctx)

    runs = Editing()
    assert _run(repo, runs) == preflight.EXIT_OK
    assert [r for r in _journal(repo) if "lanes" in r][-1]["tree"] is None


def test_outside_a_git_checkout_nothing_is_reused(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    (plain / "pixi.toml").write_text(_pixi(LANES), encoding="utf-8")
    assert preflight.tree_state(plain) is None
    runs = Runs()
    assert _run(plain, runs) == preflight.EXIT_OK
    assert _run(plain, runs) == preflight.EXIT_OK
    assert len(runs.started) == 4
    assert all(r["tree"] is None for r in _journal(plain) if "lanes" in r)


def test_the_opt_out_reads_zero_only(monkeypatch: pytest.MonkeyPatch) -> None:
    assert preflight.reuse_enabled() is True
    monkeypatch.setenv(preflight.REUSE_ENV, "0")
    assert preflight.reuse_enabled() is False
    monkeypatch.setenv(preflight.REUSE_ENV, " 0 ")
    assert preflight.reuse_enabled() is False
    monkeypatch.setenv(preflight.REUSE_ENV, "1")
    assert preflight.reuse_enabled() is True


def test_main_passes_the_opt_out_to_the_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    seen: dict[str, object] = {}

    def fake_run(repo_root: Path, **kwargs: object) -> int:
        seen.update(kwargs)
        return preflight.EXIT_OK

    monkeypatch.setattr(preflight, "run_preflight", fake_run)
    monkeypatch.setenv("PIXI_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv(preflight.SCOPE_ENV, "full")
    assert preflight.main([]) == preflight.EXIT_OK
    assert seen["reuse"] is True
    monkeypatch.setenv(preflight.REUSE_ENV, "0")
    assert preflight.main([]) == preflight.EXIT_OK
    assert seen["reuse"] is False


def test_another_commit_of_the_same_tree_runs_its_lanes(repo: Path) -> None:
    """Some detectors judge history (commit subjects, per-commit diffs): a reworded commit keeps the tree and is
    another state."""
    runs = Runs()
    assert _run(repo, runs) == preflight.EXIT_OK
    tree = _git(repo, "rev-parse", "HEAD^{tree}")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "--amend", "-m", "reworded")
    assert _git(repo, "rev-parse", "HEAD^{tree}") == tree
    assert _run(repo, runs) == preflight.EXIT_OK
    assert len(runs.started) == 4


def test_another_day_runs_its_lanes(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Some detectors judge a date (a flag past its clock): yesterday's green is not today's."""
    runs = Runs()
    monkeypatch.setattr(preflight, "_today", lambda: "2026-11-26")
    assert _run(repo, runs) == preflight.EXIT_OK
    monkeypatch.setattr(preflight, "_today", lambda: "2026-11-27")
    assert _run(repo, runs) == preflight.EXIT_OK
    assert len(runs.started) == 4


def test_a_later_red_run_of_the_same_state_takes_the_green_back(repo: Path) -> None:
    runs = Runs()
    assert _run(repo, runs) == preflight.EXIT_OK
    runs.red = {"beta"}
    assert _run(repo, runs, reuse=False, keep_going=True) == preflight.EXIT_LANE_RED
    runs.red = set()
    started = len(runs.started)
    assert _run(repo, runs) == preflight.EXIT_OK
    assert len(runs.started) == started + 2, "the newest word on this state was red, so the lanes run"
    assert _run(repo, runs) == preflight.EXIT_OK
    assert len(runs.started) == started + 2, "and that green run is reused again"


def test_a_green_run_older_than_the_limit_is_not_reused(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from datetime import UTC, datetime, timedelta

    runs = Runs()
    assert _run(repo, runs) == preflight.EXIT_OK
    state = preflight.tree_state(repo)
    lanes = [preflight.Lane("alpha", INV), preflight.Lane("beta", INV)]
    path = repo / preflight.JOURNAL_RELATIVE
    now = datetime.now(tz=UTC)
    assert preflight.reusable_run(path, state, lanes, now=now) is not None
    late = now + timedelta(seconds=preflight.REUSE_MAX_AGE_SECONDS + 120)
    assert preflight.reusable_run(path, state, lanes, now=late) is None
    # A record whose start cannot be read has no age and is never reused.
    records = _journal(repo)
    for record in records:
        record["started_at"] = "not a time"
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    assert preflight.reusable_run(path, state, lanes, now=now) is None
    monkeypatch.setattr(preflight, "REUSE_MAX_AGE_SECONDS", 1800.0)
    assert _run(repo, runs) == preflight.EXIT_OK
    assert len(runs.started) == 4


def test_a_lane_that_another_lane_judges_in_full_is_covered_by_it(repo: Path) -> None:
    """A touched run's fast-core detectors each run inside detectors-ci: a green full run covers them, and only when
    the caller names that lane as their stand-in."""
    runs = Runs()
    assert _run(repo, runs) == preflight.EXIT_OK
    state = preflight.tree_state(repo)
    path = repo / preflight.JOURNAL_RELATIVE
    wanted = [preflight.Lane("alpha", INV), preflight.Lane("spec-surface-check", INV)]
    assert preflight.reusable_run(path, state, wanted) is None
    stands_for = {("spec-surface-check", INV): ("beta", INV)}
    assert preflight.reusable_run(path, state, wanted, stands_for=stands_for) is not None
    assert preflight.reusable_run(path, state, wanted, stands_for={("spec-surface-check", INV): ("gone", INV)}) is None


def test_whether_a_github_token_is_set_is_part_of_the_state_and_its_value_is_not(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    without = preflight.tree_state(repo)
    monkeypatch.setenv("GH_TOKEN", "one")
    with_one = preflight.tree_state(repo)
    monkeypatch.setenv("GH_TOKEN", "two")
    assert preflight.tree_state(repo) == with_one
    assert without is not None and with_one is not None and without.env_digest != with_one.env_digest
    assert "one" not in json.dumps(with_one.to_journal())


def test_a_reuse_record_lists_what_the_run_leaves_to_ci(repo: Path) -> None:
    from pyforge.steward import preflight_verify

    runs = Runs()
    assert _run(repo, runs) == preflight.EXIT_OK
    assert _run(repo, runs) == preflight.EXIT_OK
    path = repo / preflight.JOURNAL_RELATIVE
    records = _journal(repo)
    reuse = records[-1]
    assert reuse["phase"] == "reuse" and reuse["deferred"] == []
    # A touched run that reused a verdict still owes its deferred lanes: verify-deferred lists it.
    reuse["deferred"] = [{"lane": "left", "environment": INV, "reason": "CI arbitrates"}]
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    owed, warnings = preflight_verify.deferred_runs(path, None)
    assert [entry.lanes for entry in owed] == [f"left@{INV}"]
    assert warnings == []
