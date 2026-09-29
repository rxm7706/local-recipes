"""Unit tests for ``pyforge.marshal.seed.apply.run`` (Story 10.3) -- covers
the spec's I/O & Edge-Case Matrix row for row: the empty plan, the happy
path's call order, all five stale-plan refusals (HEAD moved, dirty flipped,
an actioned file edited, an absent artifact that appeared, an orphan hashed
id) plus the deliberate "an empty plan is still refused when stale"
ordering, fault injection at action indices 0/1/2, an interrupt mid-run,
a pre-seeded state file left byte-identical, a rollback that itself fails,
an unreadable snapshot, and a never-write target.

Imports the ``run`` module itself (not just its functions) so the
rollback-routing test can monkeypatch ``run.fs.write``/``run.fs.remove``
and count them -- ``test_seed_fs.py``'s own ``monkeypatch.setattr(fs,
"atomic_write_bytes", ...)`` idiom, applied one layer up.

Plans are constructed DIRECTLY (``Plan(...)``/``Action(...)``) rather than
through ``build_plan``: ``run_apply``'s contract is over an arbitrary
``Plan``, and direct construction is what lets a test make exactly one
fingerprint field stale, or hand the runner a deliberately unsorted action
tuple. ``_fresh_plan`` below keeps those plans honest by recording what
``build_plan`` itself would have recorded against the same repo.

The ``commit`` doubles here write with plain ``Path.write_text``: P-01
constrains what ``seed/`` modules may call, not what a test's own
caller-supplied callback does, and using an unguarded write is exactly what
makes the rollback tests meaningful (the runner's OWN writes are the ones
proven to route through ``fs``).
"""

from __future__ import annotations

import ast
import dataclasses
import subprocess
from pathlib import Path

import pytest
from pyforge.core.process import ProcessError

from pyforge.marshal.seed import fs
from pyforge.marshal.seed.apply import run
from pyforge.marshal.seed.apply.run import ApplyResult, run_apply
from pyforge.marshal.seed.detect.hashes import hash_content
from pyforge.marshal.seed.detect.inventory import ArtifactState
from pyforge.marshal.seed.errors import (
    InternalError,
    NeverWriteViolation,
    PreconditionFailure,
)
from pyforge.marshal.seed.fs import NeverWrite
from pyforge.marshal.seed.model.manifest import ArtifactClass
from pyforge.marshal.seed.plan.types import Action, Plan, RepoFingerprint

_OPEN = NeverWrite(())


def _action(artifact_id: str, target_path: str, **overrides) -> Action:
    fields = {
        "artifact_id": artifact_id,
        "artifact_class": ArtifactClass.COPIED_MANAGED,
        "current_state": ArtifactState.ABSENT,
        "target_state": ArtifactState.PRESENT_CONFORMANT,
        "target_path": target_path,
        "chosen_anchor": (),
        "rationale": f"{target_path!r} is absent; materialize it as copied-managed",
    }
    fields.update(overrides)
    return Action(**fields)


def _text_of(path: Path) -> str:
    """Mirrors ``plan.build``'s own absent/non-file/unreadable/non-UTF-8 ->
    ``""`` degradation, so a fingerprint built here is what ``build_plan``
    would have recorded for the same target."""
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError, UnicodeDecodeError:
        return ""


def _fresh_plan(repo_root: Path, *actions: Action, **fingerprint_overrides) -> Plan:
    """A ``Plan`` whose fingerprint is exactly what ``build_plan`` would
    record against ``repo_root`` right now -- so ``fingerprint_drift``
    reports ``()`` and the runner proceeds.

    A bare ``tmp_path`` is not a git repo, so ``git_head``/``dirty`` degrade
    to ``None``/``True`` (pinned by ``test_seed_plan_build.py``'s own
    non-git-target test). ``fingerprint_overrides`` is how a test makes
    exactly ONE field stale without disturbing the others.

    Each action's ``current_state`` is corrected to match what is actually
    on disk right now, exactly as ``classify`` would have reported it. Not
    cosmetic (review-pass finding, caught by the new existence check): a
    fixture that pre-creates a target while leaving ``_action``'s default
    ``ABSENT`` in place describes a repo state that cannot exist, and
    ``fingerprint_drift`` now correctly refuses such a plan as stale. Fixing
    it here rather than at every call site is what makes this helper's
    "exactly what ``build_plan`` would record" claim true of the ACTIONS as
    well as the fingerprint.

    One bound on that claim, stated rather than implied (second review pass):
    the correction is faithful for the two fields ``fingerprint_drift``
    actually reads (``artifact_id``/``target_path``, plus ``current_state``),
    but the resulting Action is not one ``build_plan`` could emit in full --
    ``_action`` defaults ``artifact_class`` to ``COPIED_MANAGED``, and only a
    ``hybrid-managed-region`` entry ever reaches ``PRESENT_DIVERGENT``. That
    combination is harmless HERE because ``run_apply`` never branches on
    ``artifact_class`` (it is the whole point of the ``commit`` callback), so
    no test below depends on it -- but a future assertion that does read
    ``artifact_class`` must not treat these fixtures as producer-faithful."""
    actions = tuple(
        dataclasses.replace(
            action,
            current_state=(
                ArtifactState.PRESENT_DIVERGENT if (repo_root / action.target_path).is_file() else ArtifactState.ABSENT
            ),
        )
        for action in actions
    )
    fields = {
        "git_head": None,
        "dirty": True,
        "artifact_hashes": tuple(
            sorted((action.artifact_id, hash_content(_text_of(repo_root / action.target_path))) for action in actions)
        ),
    }
    fields.update(fingerprint_overrides)
    return Plan(actions=actions, repo_fingerprint=RepoFingerprint(**fields))


def _committer(repo_root: Path, calls: list[str], *, fail_at=None, failure=None):
    """A ``commit`` double that records every call and materializes a marker
    file at the action's target.

    When ``fail_at`` is set, the failing call still WRITES before it raises
    -- a half-materialized target is the realistic failure and forces
    rollback to undo the failing action's own write too, not merely its
    predecessors'."""
    boom = failure if failure is not None else RuntimeError("commit exploded")

    def commit(action: Action) -> None:
        calls.append(action.artifact_id)
        target = repo_root / action.target_path
        # `atomic_write_bytes` creates parents for the runner's own restore
        # writes; a realistic `commit` double must do the same so a NESTED
        # target path is exercisable at all.
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"materialized {action.artifact_id}\n", encoding="utf-8")
        if fail_at is not None and len(calls) - 1 == fail_at:
            raise boom

    return commit


def _never_called(action: Action) -> None:
    raise AssertionError(f"commit must not be called, got {action.artifact_id!r}")


def _tree(root: Path) -> dict[str, bytes]:
    """Every regular file under ``root``, by repo-relative path -- the
    "zero net change on disk" oracle the rollback rows assert against.

    Bounds, stated rather than implied (review finding: this helper was
    described as a zero-net-change oracle while being blind to three
    residues this runner genuinely leaves). It observes CONTENT and PATHS
    only, so it cannot see: a restored file's permission bits (an executable
    target comes back at the umask default), a directory left behind by a
    rolled-back action or by ``atomic_write_bytes``'s ``mkdir(parents=True)``
    (it collects only ``is_file()`` entries), or a symlink converted into a
    regular file. All three are documented bounds of ``run_apply`` itself
    with deferred-work entries of their own, not gaps in these tests -- but a
    reader must not mistake a green assertion here for their absence."""
    return {str(path.relative_to(root)): path.read_bytes() for path in sorted(root.rglob("*")) if path.is_file()}


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Mirrors ``test_seed_plan_build.py``'s own real-git-repo convention:
    real ``git`` I/O against a ``tmp_path``, never mocked."""
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    return result


def _init_git_repo(repo: Path) -> None:
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "initial")


# --- empty plan: I/O Matrix row 1 -------------------------------------------


def test_an_empty_fresh_plan_commits_nothing_writes_nothing_and_returns_no_ids(tmp_path):
    plan = _fresh_plan(tmp_path)
    calls: list[str] = []

    result = run_apply(plan, repo_root=tmp_path, never_write=_OPEN, commit=_committer(tmp_path, calls))

    assert result == ApplyResult(applied=())
    assert calls == []
    # Nothing at all -- not even `.marshal/`: the runner writes no plan, no
    # state, and no bookkeeping of its own.
    assert list(tmp_path.iterdir()) == []


# --- happy path: I/O Matrix row 2 -------------------------------------------


def test_commit_is_called_once_per_action_in_plan_order_and_result_lists_the_same_ids(tmp_path):
    actions = (_action("a", "a.txt"), _action("b", "b.txt"), _action("c", "c.txt"))
    plan = _fresh_plan(tmp_path, *actions)
    calls: list[str] = []

    result = run_apply(plan, repo_root=tmp_path, never_write=_OPEN, commit=_committer(tmp_path, calls))

    assert calls == ["a", "b", "c"]
    assert result.applied == ("a", "b", "c")
    assert (tmp_path / "b.txt").read_text(encoding="utf-8") == "materialized b\n"


def test_actions_execute_in_plan_order_never_re_sorted_and_never_filtered(tmp_path):
    # Deliberately NOT sorted by artifact_id: `build_plan` always sorts, and
    # `Plan.from_json_dict` rejects an unsorted tuple -- but direct
    # construction does not, and the runner's own contract is "plan.actions
    # order, unmodified", which only an unsorted plan can actually prove.
    actions = (_action("c", "c.txt"), _action("a", "a.txt"), _action("b", "b.txt"))
    plan = _fresh_plan(tmp_path, *actions)
    calls: list[str] = []

    result = run_apply(plan, repo_root=tmp_path, never_write=_OPEN, commit=_committer(tmp_path, calls))

    assert calls == ["c", "a", "b"]
    assert result.applied == ("c", "a", "b")


def test_apply_result_is_frozen(tmp_path):
    result = run_apply(_fresh_plan(tmp_path), repo_root=tmp_path, never_write=_OPEN, commit=_never_called)
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.applied = ("x",)


# --- stale plan: I/O Matrix rows 3-7 ----------------------------------------


def test_a_plan_built_before_a_new_commit_is_refused_naming_stale_plan_and_git_head(tmp_path):
    _init_git_repo(tmp_path)
    head = _git(tmp_path, "rev-parse", "HEAD").stdout.strip()
    plan = _fresh_plan(tmp_path, git_head=head, dirty=False)
    # Fresh first: the same empty plan applies cleanly, so the refusal below
    # is attributable to the new commit and nothing else.
    assert run_apply(plan, repo_root=tmp_path, never_write=_OPEN, commit=_never_called) == ApplyResult(applied=())

    _git(tmp_path, "commit", "--allow-empty", "-m", "second")

    with pytest.raises(PreconditionFailure) as excinfo:
        run_apply(plan, repo_root=tmp_path, never_write=_OPEN, commit=_never_called)

    # Also the "stale, empty plan is refused rather than treated as a no-op"
    # row: refusing wins over short-circuiting, deliberately.
    assert "stale-plan" in str(excinfo.value)
    assert "git_head" in str(excinfo.value)
    assert excinfo.value.exit_code == 3
    assert excinfo.value.remedy.strip()


def test_a_plan_built_against_a_clean_worktree_is_refused_once_the_worktree_is_dirty(tmp_path):
    _init_git_repo(tmp_path)
    head = _git(tmp_path, "rev-parse", "HEAD").stdout.strip()
    plan = _fresh_plan(tmp_path, git_head=head, dirty=False)

    (tmp_path / "untracked.txt").write_text("dirties the worktree\n", encoding="utf-8")

    with pytest.raises(PreconditionFailure) as excinfo:
        run_apply(plan, repo_root=tmp_path, never_write=_OPEN, commit=_never_called)

    assert "stale-plan" in str(excinfo.value)
    assert "dirty" in str(excinfo.value)


def test_a_plan_whose_actioned_file_was_hand_edited_is_refused_naming_the_artifact_id(tmp_path):
    (tmp_path / "CLAUDE.md").write_text("original\n", encoding="utf-8")
    plan = _fresh_plan(tmp_path, _action("claude-md", "CLAUDE.md", current_state=ArtifactState.PRESENT_DIVERGENT))
    (tmp_path / "CLAUDE.md").write_text("hand-edited since the plan\n", encoding="utf-8")
    # Captured AFTER the hand-edit, so the comparison below can be the full
    # content-and-path one every sibling rollback test uses (review finding:
    # this assertion was `set(_tree(...)) == set(before)`, which compares
    # only FILENAMES -- a runner that rewrote the contents of every
    # pre-existing file before refusing would have passed it unchanged).
    before = _tree(tmp_path)
    calls: list[str] = []

    with pytest.raises(PreconditionFailure) as excinfo:
        run_apply(plan, repo_root=tmp_path, never_write=_OPEN, commit=_committer(tmp_path, calls))

    assert "stale-plan" in str(excinfo.value)
    assert "claude-md" in str(excinfo.value)
    assert calls == []
    # The refusal is not a write path: only the test's own hand-edit is on
    # disk, nothing the runner did.
    assert _tree(tmp_path) == before


def test_a_plan_whose_absent_artifact_has_since_appeared_is_refused(tmp_path):
    # AR-5's sharpest case: `build_plan` hashed `""` for an ABSENT artifact
    # without reading anything, so a verifier reusing that same state gate
    # would match forever and let apply clobber the file that appeared.
    plan = _fresh_plan(tmp_path, _action("seeded", "seeded.txt"))
    (tmp_path / "seeded.txt").write_text("appeared out of nowhere\n", encoding="utf-8")
    calls: list[str] = []

    with pytest.raises(PreconditionFailure) as excinfo:
        run_apply(plan, repo_root=tmp_path, never_write=_OPEN, commit=_committer(tmp_path, calls))

    assert "stale-plan" in str(excinfo.value)
    assert "seeded" in str(excinfo.value)
    assert calls == []
    assert (tmp_path / "seeded.txt").read_text(encoding="utf-8") == "appeared out of nowhere\n"


def test_a_plan_hashing_an_id_no_action_carries_is_refused_before_any_write(tmp_path):
    plan = _fresh_plan(tmp_path, _action("a", "a.txt"))
    tampered = Plan(
        actions=plan.actions,
        repo_fingerprint=RepoFingerprint(
            git_head=plan.repo_fingerprint.git_head,
            dirty=plan.repo_fingerprint.dirty,
            artifact_hashes=plan.repo_fingerprint.artifact_hashes + (("ghost", "deadbeef"),),
        ),
    )
    calls: list[str] = []

    with pytest.raises(PreconditionFailure) as excinfo:
        run_apply(tampered, repo_root=tmp_path, never_write=_OPEN, commit=_committer(tmp_path, calls))

    assert "stale-plan" in str(excinfo.value)
    assert "ghost" in str(excinfo.value)
    assert calls == []
    assert list(tmp_path.iterdir()) == []


# --- fault injection at three action indices: I/O Matrix rows 8-10 ----------


@pytest.mark.parametrize("fail_at", [0, 1, 2])
def test_a_commit_failure_at_any_action_index_leaves_zero_net_change_on_disk(tmp_path, fail_at):
    # A mix of pre-existing and absent targets, so BOTH restore paths run in
    # the same transaction: `bytes` -> rewritten, `None` -> removed again.
    (tmp_path / "a.txt").write_text("original a\n", encoding="utf-8")
    (tmp_path / "c.txt").write_text("original c\n", encoding="utf-8")
    actions = (_action("a", "a.txt"), _action("b", "b.txt"), _action("c", "c.txt"))
    plan = _fresh_plan(tmp_path, *actions)
    before = _tree(tmp_path)
    calls: list[str] = []
    boom = RuntimeError(f"commit exploded at {fail_at}")

    with pytest.raises(RuntimeError) as excinfo:
        run_apply(
            plan,
            repo_root=tmp_path,
            never_write=_OPEN,
            commit=_committer(tmp_path, calls, fail_at=fail_at, failure=boom),
        )

    # The exception the caller sees is the one `commit` raised -- the same
    # object, not a rollback artifact wrapping it.
    assert excinfo.value is boom
    assert calls == ["a", "b", "c"][: fail_at + 1]
    assert _tree(tmp_path) == before


def test_a_failure_at_the_last_action_reverts_the_earlier_two_in_reverse_order(tmp_path):
    # Two actions naming the SAME target_path: a forward restore would write
    # the earlier snapshot first and the later one -- itself already
    # post-first-write content -- second, leaving that intermediate state as
    # the final result. Reverse order is what makes the pre-run bytes win.
    (tmp_path / "shared.txt").write_text("original\n", encoding="utf-8")
    actions = (
        _action("a", "shared.txt"),
        _action("b", "shared.txt"),
        _action("c", "c.txt"),
    )
    plan = _fresh_plan(tmp_path, *actions)
    calls: list[str] = []

    with pytest.raises(RuntimeError):
        run_apply(
            plan,
            repo_root=tmp_path,
            never_write=_OPEN,
            commit=_committer(tmp_path, calls, fail_at=2),
        )

    assert calls == ["a", "b", "c"]
    assert (tmp_path / "shared.txt").read_text(encoding="utf-8") == "original\n"
    assert not (tmp_path / "c.txt").exists()


# --- interrupt mid-run: I/O Matrix row 11 -----------------------------------


def test_a_keyboard_interrupt_mid_run_reverts_completed_writes_and_propagates(tmp_path):
    (tmp_path / "a.txt").write_text("original a\n", encoding="utf-8")
    actions = (_action("a", "a.txt"), _action("b", "b.txt"))
    plan = _fresh_plan(tmp_path, *actions)
    before = _tree(tmp_path)
    calls: list[str] = []
    interrupt = KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt) as excinfo:
        run_apply(
            plan,
            repo_root=tmp_path,
            never_write=_OPEN,
            commit=_committer(tmp_path, calls, fail_at=1, failure=interrupt),
        )

    assert excinfo.value is interrupt
    assert _tree(tmp_path) == before


# --- state untouched: I/O Matrix row 12 -------------------------------------


def test_a_pre_existing_seed_state_file_is_byte_identical_after_a_failed_run(tmp_path):
    state_path = tmp_path / ".marshal" / "seed-state.yml"
    state_path.parent.mkdir()
    state_path.write_bytes(b"model_version: 1.0.0\nartifacts: []\n")
    original_state = state_path.read_bytes()

    plan = _fresh_plan(tmp_path, _action("a", "a.txt"), _action("b", "b.txt"))
    calls: list[str] = []

    with pytest.raises(RuntimeError):
        run_apply(
            plan,
            repo_root=tmp_path,
            never_write=_OPEN,
            commit=_committer(tmp_path, calls, fail_at=1),
        )

    assert state_path.read_bytes() == original_state


# --- rollback itself fails: I/O Matrix row 13 -------------------------------


def test_an_unrestorable_path_raises_internal_error_naming_it_and_still_restores_the_rest(
    tmp_path,
):
    # `protected.txt` is never-write, but this test's `commit` writes with
    # plain `write_text`, so only the RUNNER's own restore is blocked --
    # exactly the "never_write now matches the target" row.
    (tmp_path / "a.txt").write_text("original a\n", encoding="utf-8")
    (tmp_path / "protected.txt").write_text("original protected\n", encoding="utf-8")
    actions = (
        _action("a", "a.txt"),
        _action("b", "protected.txt"),
        _action("c", "c.txt"),
    )
    plan = _fresh_plan(tmp_path, *actions)
    calls: list[str] = []
    boom = RuntimeError("commit exploded at 2")

    with pytest.raises(InternalError) as excinfo:
        run_apply(
            plan,
            repo_root=tmp_path,
            never_write=NeverWrite(("protected.txt",)),
            commit=_committer(tmp_path, calls, fail_at=2, failure=boom),
        )

    assert excinfo.value.exit_code == 10
    assert excinfo.value.remedy.strip()
    # Names BOTH the original failure and every unrestorable path.
    assert "commit exploded at 2" in str(excinfo.value)
    assert "protected.txt" in str(excinfo.value)
    assert excinfo.value.__cause__ is boom
    # Every OTHER restore still ran: `protected.txt` is the only residue.
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "original a\n"
    assert not (tmp_path / "c.txt").exists()
    assert (tmp_path / "protected.txt").read_text(encoding="utf-8") == "materialized b\n"


# --- unreadable snapshot: I/O Matrix row 14 ---------------------------------


def test_an_unreadable_snapshot_propagates_its_oserror_and_that_action_never_runs(tmp_path, monkeypatch):
    (tmp_path / "a.txt").write_text("original a\n", encoding="utf-8")
    (tmp_path / "b.txt").write_text("original b\n", encoding="utf-8")
    plan = _fresh_plan(tmp_path, _action("a", "a.txt"), _action("b", "b.txt"))
    before = _tree(tmp_path)
    calls: list[str] = []

    real_read_bytes = Path.read_bytes

    def flaky_read_bytes(self):
        if self.name == "b.txt":
            raise OSError("snapshot unreadable")
        return real_read_bytes(self)

    monkeypatch.setattr(Path, "read_bytes", flaky_read_bytes)

    with pytest.raises(OSError, match="snapshot unreadable"):
        run_apply(plan, repo_root=tmp_path, never_write=_OPEN, commit=_committer(tmp_path, calls))

    # `b`'s commit never ran (its snapshot failed first), and `a` was rolled
    # back -- the OSError reaches the caller unwrapped, per `fs.py`'s own
    # "never wraps a generic OSError" line.
    assert calls == ["a"]
    monkeypatch.undo()
    assert _tree(tmp_path) == before


# --- never-write target: I/O Matrix row 15 ----------------------------------


def test_a_commit_that_honors_fs_on_a_never_write_target_unwinds_the_prior_actions(tmp_path):
    (tmp_path / "a.txt").write_text("original a\n", encoding="utf-8")
    never_write = NeverWrite(("docs/dreams/*.md",))
    actions = (_action("a", "a.txt"), _action("dream", "docs/dreams/x.md"))
    plan = _fresh_plan(tmp_path, *actions)
    before = _tree(tmp_path)
    calls: list[str] = []

    def commit(action: Action) -> None:
        calls.append(action.artifact_id)
        fs.write(
            tmp_path / action.target_path,
            b"materialized\n",
            repo_root=tmp_path,
            never_write=never_write,
        )

    with pytest.raises(NeverWriteViolation) as excinfo:
        run_apply(plan, repo_root=tmp_path, never_write=never_write, commit=commit)

    assert excinfo.value.exit_code == 4
    assert calls == ["a", "dream"]
    assert _tree(tmp_path) == before


# --- P-01: every rollback byte goes through fs ------------------------------


def test_every_rollback_write_and_removal_routes_through_the_fs_guard(tmp_path, monkeypatch):
    (tmp_path / "a.txt").write_text("original a\n", encoding="utf-8")
    actions = (_action("a", "a.txt"), _action("b", "b.txt"), _action("c", "c.txt"))
    plan = _fresh_plan(tmp_path, *actions)
    calls: list[str] = []
    writes: list[Path] = []
    removes: list[Path] = []
    real_write, real_remove = fs.write, fs.remove

    def spy_write(path, data, *, repo_root, never_write):
        writes.append(path)
        real_write(path, data, repo_root=repo_root, never_write=never_write)

    def spy_remove(path, *, repo_root, never_write):
        removes.append(path)
        real_remove(path, repo_root=repo_root, never_write=never_write)

    monkeypatch.setattr(run.fs, "write", spy_write)
    monkeypatch.setattr(run.fs, "remove", spy_remove)

    with pytest.raises(RuntimeError):
        run_apply(
            plan,
            repo_root=tmp_path,
            never_write=_OPEN,
            commit=_committer(tmp_path, calls, fail_at=2),
        )

    # Reverse order, and exactly one guarded call per snapshot: `c`/`b` were
    # absent before their action ran (removed again), `a` existed (rewritten).
    assert removes == [tmp_path / "c.txt", tmp_path / "b.txt"]
    assert writes == [tmp_path / "a.txt"]


def test_no_fs_call_at_all_when_a_run_succeeds(tmp_path, monkeypatch):
    """The runner writes nothing of its own on the happy path -- every byte
    on disk after a successful run came from `commit`."""
    plan = _fresh_plan(tmp_path, _action("a", "a.txt"))
    touched: list[str] = []
    monkeypatch.setattr(run.fs, "write", lambda *a, **k: touched.append("write"))
    monkeypatch.setattr(run.fs, "remove", lambda *a, **k: touched.append("remove"))

    run_apply(plan, repo_root=tmp_path, never_write=_OPEN, commit=_committer(tmp_path, []))

    assert touched == []


# --- review-pass additions: containment, taxonomy, nested targets -----------


@pytest.mark.parametrize(
    "escaping",
    ["/etc/cron.d/genesis", "../outside.txt", "sub/../../outside.txt"],
    ids=["absolute", "parent-traversal", "traversal-via-subdir"],
)
def test_an_action_whose_target_escapes_repo_root_is_refused_before_any_write(tmp_path, escaping):
    """Review finding, verified by execution: ``Path('/repo') / '/etc/x'``
    discards the left operand entirely, and ``.marshal/plan.json`` is
    explicitly untrusted, hand-editable input (``plan/types.py``'s own
    from_json_dict boundary). Without a containment check the runner
    snapshots and rewrites arbitrary host paths -- and ``fs``'s never-write
    guard cannot save it, because for a path outside ``repo_root`` the guard
    falls back to the absolute POSIX string, which no repo-relative pattern
    can ever match. ``detect/inventory.py`` guards exactly this with
    ``_resolve_within_repo``; apply had no equivalent.

    Built through ``_fresh_plan`` rather than a hand-rolled ``Plan``: the
    earlier fixture paired one action with ``artifact_hashes=()``, which
    ``fingerprint_drift`` independently refuses ("carried by an Action but
    absent from the plan's fingerprint"), so the test passed only because
    containment happens to run first and would have kept passing if the
    containment check were deleted outright (second review pass). A fingerprint
    that is otherwise FRESH is what makes this an isolation of containment."""
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("do not touch\n", encoding="utf-8")
    plan = _fresh_plan(repo, _action("escaper", escaping))

    with pytest.raises(PreconditionFailure) as excinfo:
        run_apply(plan, repo_root=repo, never_write=_OPEN, commit=_never_called)

    assert "escaping-target" in str(excinfo.value)
    assert excinfo.value.exit_code == 3
    assert excinfo.value.remedy
    assert outside.read_text(encoding="utf-8") == "do not touch\n"


def test_a_process_error_while_verifying_freshness_becomes_a_precondition_failure(tmp_path, monkeypatch):
    """Review finding: ``fingerprint_drift`` shells out through
    ``PosixProcess.run``, which raises ``ProcessError`` -- a ``pyforge.core``
    type with no ``exit_code`` and no ``remedy`` -- when ``git`` is missing
    from PATH or ``repo_root`` does not exist. Left untranslated it escapes
    the closed six-leaf taxonomy entirely, handing an operator a traceback
    where ``PreconditionFailure``'s own docstring promises exit 3."""

    def boom(plan, repo_root):
        raise ProcessError("executable not found: 'git'")

    monkeypatch.setattr(run, "fingerprint_drift", boom)
    plan = _fresh_plan(tmp_path, _action("a", "a.txt"))

    with pytest.raises(PreconditionFailure) as excinfo:
        run_apply(plan, repo_root=tmp_path, never_write=_OPEN, commit=_never_called)

    assert excinfo.value.exit_code == 3
    assert excinfo.value.remedy
    assert isinstance(excinfo.value.__cause__, ProcessError)


def test_a_nested_target_is_restored_on_rollback(tmp_path):
    """Every other fault-injection target here is flat (``a.txt``), but real
    manifest artifacts are nested (``.github/workflows/detectors.yml``).
    The restored FILE must come back byte-identical; the directories
    ``commit``/``atomic_write_bytes`` created along the way are a documented,
    deferred bound of the runner and are deliberately NOT asserted absent."""
    nested = tmp_path / "docs" / "deep" / "kept.md"
    nested.parent.mkdir(parents=True)
    nested.write_text("pre-existing\n", encoding="utf-8")
    plan = _fresh_plan(
        tmp_path,
        _action("kept", "docs/deep/kept.md", current_state=ArtifactState.PRESENT_DIVERGENT),
        _action("new", "docs/fresh/new.md"),
    )
    calls: list[str] = []

    with pytest.raises(RuntimeError):
        run_apply(
            plan,
            repo_root=tmp_path,
            never_write=_OPEN,
            commit=_committer(tmp_path, calls, fail_at=1),
        )

    assert calls == ["kept", "new"]
    assert nested.read_text(encoding="utf-8") == "pre-existing\n"
    assert not (tmp_path / "docs" / "fresh" / "new.md").exists()


# --- structural guarantees (P-04/P-07, and Story 10.2's merge) --------------


def _imported_names(module_path: Path) -> set[str]:
    """Every dotted name ``module_path`` imports, in both ``import X`` and
    ``from X import Y`` form. The relative-import LEVEL (the leading dots)
    is dropped deliberately: the caller only splits these into path
    segments, and ``from ..detect import hashes`` must be caught by the same
    segment set as ``import pyforge.marshal.seed.detect.hashes``."""
    names: set[str] = set()
    for node in ast.walk(ast.parse(module_path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names.add(module)
            names.update(f"{module}.{alias.name}" if module else alias.name for alias in node.names)
    return names


@pytest.mark.parametrize(
    "banned",
    ["state", "engine", "detect", "hashes", "hashlib", "copier", "manifest", "inventory"],
)
def test_run_module_imports_nothing_from_the_surfaces_p04_and_p07_exclude(banned):
    """``test_p07_no_hash_comparison_in_apply.py`` already bans ``hashlib``/
    ``detect.hashes`` structurally; this widens the same claim to every
    surface this story's Never list names -- most importantly ``seed.state``,
    so the guarantee survives Story 10.2 merging its own ``seed/state/``
    module in beside this one.

    Bound, stated because the earlier wording overclaimed it (review
    finding): this is a DIRECT-import scan of ``run.py``'s own source, not a
    dependency-closure check -- exactly the bound the P-07 meta test states
    for itself. ``run.py`` imports ``..plan.build``, which does import
    ``detect.hashes``, ``detect.inventory``, ``model.manifest`` and
    ``hashlib``, so those surfaces ARE reachable at runtime; that is the
    deliberate arrangement ``run.py``'s own module docstring argues for at
    length, not something this test disproves. What it does prove is that
    no future edit can add such an import to ``run.py`` ITSELF unnoticed --
    and it will keep passing if ``plan/build.py`` someday imports
    ``seed.state``, which this assertion cannot see."""
    module_path = Path(run.__file__)
    segments = {segment for name in _imported_names(module_path) for segment in name.split(".") if segment}
    assert banned not in segments, f"seed/apply/run.py imports {banned!r}"


def test_the_apply_package_front_door_re_exports_the_runner():
    from pyforge.marshal.seed import apply

    assert apply.__all__ == ["ApplyResult", "CommitAction", "run_apply"]
    assert apply.run_apply is run_apply
    assert apply.ApplyResult is ApplyResult


# --- second review pass: containment that binds, taxonomy, agreement --------


def test_a_traversal_that_normalizes_back_inside_is_refused_and_destroys_nothing(tmp_path):
    """Review finding, verified by execution before the fix: the containment
    check resolved the path, but the snapshot and rollback loops re-derived the
    RAW ``repo_root / action.target_path``, so the guard did not bind the path
    it was guarding.

    ``'sub/../b.txt'`` resolves to ``<repo>/b.txt``, which IS inside the repo,
    so the old check passed it. The raw path then stat'd as absent (no ``sub``
    directory), snapshotting ``None``; ``commit``'s ``mkdir(parents=True)``
    created ``sub``; and from then on the same raw path resolved onto the real
    ``b.txt``, which rollback deleted as "a file that was not there before".
    A pre-existing, unrelated, in-repo file, destroyed by a rolled-back run --
    NFR-R1's exact prohibition.

    Refusing non-normalized targets outright is what closes it: no legitimate
    ``build_plan`` artifact path is absolute or traverses upward."""
    (tmp_path / "b.txt").write_text("precious\n", encoding="utf-8")
    before = _tree(tmp_path)
    plan = _fresh_plan(tmp_path, _action("sneaky", "sub/../b.txt"))

    with pytest.raises(PreconditionFailure) as excinfo:
        run_apply(plan, repo_root=tmp_path, never_write=_OPEN, commit=_never_called)

    assert "escaping-target" in str(excinfo.value)
    assert excinfo.value.exit_code == 3
    assert excinfo.value.remedy
    assert _tree(tmp_path) == before
    assert (tmp_path / "b.txt").read_text(encoding="utf-8") == "precious\n"


def test_rollback_refuses_a_target_a_commit_redirected_outside_the_repo(tmp_path):
    """Review finding, verified by execution before the fix: a real host file
    outside ``repo_root`` was deleted by rollback.

    ``run_apply``'s containment check runs once, before any ``commit``, so it
    can only see the tree as it was THEN. Action 0 targets ``sub/x.txt`` while
    ``sub`` does not exist -- contained, and snapshotted ``None``. Its
    ``commit`` then materializes ``sub`` as a SYMLINK to a directory outside the
    repo and writes through it. Action 1 fails. Rollback sees ``is_file()`` True
    at the raw path and, before the fix, called ``fs.remove`` -- unlinking the
    host's file. ``fs``'s never-write guard cannot intervene, because a path
    outside ``repo_root`` falls back to an absolute POSIX string that no
    repo-relative pattern matches.

    The fix re-checks containment at restore time and reports the path as
    unrestorable instead of touching it: the run still ends loudly in
    ``InternalError``, but nothing outside the repo is written or removed."""
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "x.txt").write_text("host file\n", encoding="utf-8")

    def commit(action: Action) -> None:
        if action.artifact_id == "a":
            (repo / "sub").symlink_to(outside, target_is_directory=True)
            (repo / "sub" / "x.txt").write_text("clobbered\n", encoding="utf-8")
            return
        raise RuntimeError("commit exploded")

    plan = _fresh_plan(repo, _action("a", "sub/x.txt"), _action("b", "b.txt"))

    with pytest.raises(InternalError) as excinfo:
        run_apply(plan, repo_root=repo, never_write=_OPEN, commit=commit)

    assert excinfo.value.exit_code == 10
    assert excinfo.value.remedy
    assert "no longer resolves inside" in str(excinfo.value)
    assert (outside / "x.txt").exists(), "rollback deleted a file outside repo_root"


@pytest.mark.parametrize("target_path", [".", "", "sub/.."], ids=["dot", "empty", "up"])
def test_a_target_that_is_the_repo_root_itself_is_refused(tmp_path, target_path):
    """Review finding: the old guard read ``resolved != resolved_root and
    resolved_root not in resolved.parents``, so a target resolving to the repo
    root itself short-circuited to ACCEPTED and the run returned success with
    ``commit`` handed the root directory. The repo root is not an artifact."""
    plan = _fresh_plan(tmp_path, _action("rooty", target_path))

    with pytest.raises(PreconditionFailure) as excinfo:
        run_apply(plan, repo_root=tmp_path, never_write=_OPEN, commit=_never_called)

    assert "escaping-target" in str(excinfo.value)
    assert excinfo.value.exit_code == 3


def test_a_target_path_that_cannot_be_resolved_becomes_a_precondition_failure(tmp_path):
    """Review finding, verified by execution: ``Plan.from_json_dict`` type-checks
    ``target_path`` as ``str`` and nothing more, so an embedded NUL reached
    ``Path.resolve()`` and raised a raw ``ValueError`` -- escaping the closed
    six-leaf ``SeedError`` taxonomy exactly as the untranslated ``ProcessError``
    did, on the very line added to guard untrusted plans."""
    plan = _fresh_plan(tmp_path, _action("nul", "a\x00b.txt"))

    with pytest.raises(PreconditionFailure) as excinfo:
        run_apply(plan, repo_root=tmp_path, never_write=_OPEN, commit=_never_called)

    assert "unusable-target" in str(excinfo.value)
    assert excinfo.value.exit_code == 3
    assert excinfo.value.remedy
    assert isinstance(excinfo.value.__cause__, (OSError, ValueError))


def test_a_process_error_from_the_real_freshness_check_becomes_a_precondition_failure(
    tmp_path,
):
    """The sibling test above monkeypatches ``run.fingerprint_drift``, so it
    would keep passing if the real call stopped raising ``ProcessError``
    (review finding). This one drives the REAL function: a ``repo_root`` that
    does not exist makes ``PosixProcess.run`` fail to spawn ``git``."""
    plan = _fresh_plan(tmp_path, _action("a", "a.txt"))

    with pytest.raises(PreconditionFailure) as excinfo:
        run_apply(
            plan,
            repo_root=tmp_path / "does-not-exist",
            never_write=_OPEN,
            commit=_never_called,
        )

    assert excinfo.value.exit_code == 3
    assert excinfo.value.remedy
    assert isinstance(excinfo.value.__cause__, ProcessError)
