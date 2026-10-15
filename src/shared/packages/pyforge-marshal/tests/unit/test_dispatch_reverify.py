"""Story 102.1 (spec-pyforge-marshal CAP-161): a re-landing reuses its verified verdict when only a merge of main moved
the branch.

The exemption is judged on real git: each scenario builds a scratch repository whose ``refs/remotes/origin/main``
plays ``origin/main``, a story branch verified at V, and the move to H the scenario names. The land-only path is
driven through ``_attempt_harness_done_cap4`` with the full verification replaced by a sentinel, so a test can tell
a reuse (the sentinel never runs) from a full verification (it does).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from pyforge.core.process import PosixProcess, ProcessResult

from pyforge.marshal.adapters.fs_local import LocalFs
from pyforge.marshal.cli import dispatch as dispatch_module
from pyforge.marshal.core import dispatch as dispatch_core
from pyforge.marshal.core import policy
from pyforge.marshal.core.dispatch_landing import DispatchLandingVerdict
from pyforge.marshal.core.dispatch_reverify import (
    BASIS_HEAD_UNCHANGED,
    BASIS_MERGE_OF_MAIN,
    MODE_FULL,
    MODE_REUSED,
    REASON_DIRTY_WORKTREE,
    REASON_GATE_SET_CHANGED,
    REASON_GIT_READ_FAILED,
    REASON_MERGE_CONFLICT_OUTSIDE_PLANNING,
    REASON_MERGE_NOT_OF_MAIN,
    REASON_MERGE_RESOLUTION_OUTSIDE_PLANNING,
    REASON_MERGE_STALE_AGAINST_MAIN,
    REASON_MERGE_TOUCHES_POLICY,
    REASON_MERGE_TOUCHES_STORY_FILE,
    REASON_NO_STORY_DIFF,
    REASON_NO_STORY_SPEC,
    REASON_NO_VERIFIED_VERDICT,
    REASON_NOT_ON_FIRST_PARENT_CHAIN,
    REASON_OCTOPUS_MERGE,
    REASON_RECHECK_FAILED,
    REASON_STORY_COMMIT,
    ChainCommit,
    ReuseFacts,
    gate_set_digest,
    is_planning_path,
    judge_verdict_reuse,
    latest_reusable_verdict,
)
from pyforge.marshal.core.identity import normalize
from pyforge.marshal.core.journal import JournalEntryId, Phase, build_entry, fold, prepare_for_write
from pyforge.marshal.core.model import Finding, Severity, build_envelope
from pyforge.marshal.core.refs import ORIGIN_MAIN
from pyforge.marshal.dispatch_land import DispatchLandingResult
from pyforge.marshal.dispatch_verification_journal import build_dispatch_verification_journal_entries
from pyforge.marshal.dispatch_verify import (
    REUSE_RECHECK_COMMANDS,
    STORY_STATUS_CHECK_COMMAND,
    attempt_verdict_reuse,
    gather_reuse_facts,
    run_reuse_recheck,
    verification_head_sha,
    verify_gate_set,
)

_SLUG = "pyforge-marshal"
_RUN_ID = "pyforge-marshal-20261015T120000000Z-102abcde"
_MEMLOG = "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/.memlog.md"
_BASELINE = "scripts/.spec-surface-baseline.json"
_STORY_FILE = "src/app/core.py"
_OTHER_FILE = "src/app/other.py"
#: The story's own tracked spec, written by the story's change (``dispatch_core.resolve_story_spec_path`` finds it).
_SPEC_REL = "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-102-1-the-story.md"
_POLICY_REL = "_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml"
#: A gate digest for the tests that drive ``attempt_verdict_reuse`` directly.
_TEST_DIGEST = "sha256:" + "d" * 64


# ---------------------------------------------------------------------------
# A scratch repository with an origin/main, a story branch and merges of main
# ---------------------------------------------------------------------------


def _numbered_lines() -> str:
    return "".join(f"line {n}\n" for n in range(1, 13))


class Scratch:
    """``trunk`` is main; ``refs/remotes/origin/main`` follows it on every ``main_commit``. The story branch is
    checked out in the one working tree, so ``repo`` is the dispatch worktree."""

    def __init__(self, root: Path) -> None:
        self.repo = root / "repo"
        self.repo.mkdir(parents=True)
        self.git("init", "-q", "-b", "trunk")
        self.git("config", "user.email", "reverify@test")
        self.git("config", "user.name", "reverify")
        self.git("config", "commit.gpgsign", "false")
        self.write(_STORY_FILE, _numbered_lines())
        self.write(_OTHER_FILE, "other\n")
        self.write(_MEMLOG, "---\ntopic: t\n---\n\n- (event) base\n")
        self.write(_BASELINE, '{"specs": {}}\n')
        # The scratch repository's own attribution-hook stub, which the narrow re-check loads from the worktree. It is
        # written into the scratch tree, never read from this repository's (the trigger map derives a read from a
        # string literal naming a tracked path, so the path is built from its segments).
        self.write(str(Path("scripts", "commit_msg_hook.py")), "def offending_lines(message):\n    return []\n")
        self.commit_all("base")
        self.sync_origin_main()
        self.git("checkout", "-q", "-b", "story")

    def git(self, *args: str, check: bool = True) -> str:
        result = subprocess.run(["git", *args], cwd=self.repo, capture_output=True, text=True)
        if check and result.returncode != 0:
            raise AssertionError(f"git {' '.join(args)} failed: {result.stdout}{result.stderr}")
        return result.stdout.strip()

    def write(self, rel: str, text: str) -> None:
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def append(self, rel: str, text: str) -> None:
        path = self.repo / rel
        path.write_text(path.read_text(encoding="utf-8") + text, encoding="utf-8")

    def replace_line(self, rel: str, old: str, new: str) -> None:
        path = self.repo / rel
        path.write_text(path.read_text(encoding="utf-8").replace(old, new, 1), encoding="utf-8")

    def commit_all(self, message: str) -> str:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)
        return self.head()

    def head(self) -> str:
        return self.git("rev-parse", "HEAD")

    def sync_origin_main(self) -> None:
        self.git("update-ref", ORIGIN_MAIN, "refs/heads/trunk")

    def story_verified(self, *, with_spec: bool = True) -> str:
        """The story's own change, committed: the head a full verification judged (V)."""
        self.replace_line(_STORY_FILE, "line 1\n", "line 1 (story)\n")
        self.append(_MEMLOG, "- (event) story\n")
        if with_spec:
            self.write(_SPEC_REL, "---\nstatus: in-review\n---\n")
        return self.commit_all("story change")

    def main_commit(self, edit, message: str = "main moves") -> str:
        self.git("checkout", "-q", "trunk")
        edit()
        sha = self.commit_all(message)
        self.sync_origin_main()
        self.git("checkout", "-q", "story")
        return sha

    def merge_main(self, *, resolve=None) -> str:
        """Merge ``origin/main`` into the story; ``resolve`` settles a conflicted merge before it is committed."""
        result = subprocess.run(
            ["git", "merge", "--no-ff", "--no-edit", "-m", "Merge origin/main", ORIGIN_MAIN],
            cwd=self.repo,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            assert resolve is not None, f"unexpected merge conflict: {result.stdout}{result.stderr}"
            resolve()
            self.git("add", "-A")
            self.git("commit", "-q", "--no-edit")
        return self.head()


@pytest.fixture
def scratch(tmp_path: Path) -> Scratch:
    return Scratch(tmp_path)


def _judge(scratch: Scratch, verified: str, *, story_spec_rel: str | None = None):
    facts = gather_reuse_facts(
        process=PosixProcess(),
        worktree=scratch.repo,
        verified_head=verified,
        current_head=scratch.head(),
        story_spec_rel=story_spec_rel,
    )
    return judge_verdict_reuse(facts)


# ---------------------------------------------------------------------------
# AC3: the exemption on real git
# ---------------------------------------------------------------------------


def test_a_clean_merge_of_main_that_leaves_the_story_files_alone_is_exempt(scratch: Scratch) -> None:
    verified = scratch.story_verified()
    scratch.main_commit(lambda: scratch.write(_OTHER_FILE, "other, moved on main\n"))
    merge = scratch.merge_main()

    decision = _judge(scratch, verified)

    assert decision.exempt, decision
    assert decision.basis == BASIS_MERGE_OF_MAIN
    assert decision.evidence["commits"][0]["sha"] == merge
    assert decision.evidence["commits"][0]["kind"] == "merge"


def test_a_planning_conflict_resolved_by_union_and_a_baseline_stamp_after_it_are_exempt(scratch: Scratch) -> None:
    verified = scratch.story_verified()
    scratch.main_commit(lambda: scratch.append(_MEMLOG, "- (event) main\n"))

    def _union() -> None:
        scratch.write(_MEMLOG, "---\ntopic: t\n---\n\n- (event) base\n- (event) main\n- (event) story\n")

    scratch.merge_main(resolve=_union)
    scratch.write(_BASELINE, '{"specs": {"x": "stamped"}}\n')
    stamp = scratch.commit_all("marshal: reconcile spec-surface drift")

    decision = _judge(scratch, verified)

    assert decision.exempt, decision
    assert decision.basis == BASIS_MERGE_OF_MAIN
    merge_record = decision.evidence["commits"][0]
    assert merge_record["planning_conflicts"] == [_MEMLOG]
    assert decision.evidence["commits"][1] == {"sha": stamp, "kind": "planning", "paths": [_BASELINE]}


def test_a_story_file_change_after_the_verified_head_re_verifies(scratch: Scratch) -> None:
    verified = scratch.story_verified()
    scratch.main_commit(lambda: scratch.write(_OTHER_FILE, "other, moved on main\n"))
    scratch.merge_main()
    scratch.replace_line(_STORY_FILE, "line 5\n", "line 5 (fixed after the merge)\n")
    scratch.commit_all("fix after the merge")

    decision = _judge(scratch, verified)

    assert not decision.exempt
    assert decision.reason == REASON_STORY_COMMIT
    assert _STORY_FILE in decision.detail


def test_a_content_conflict_in_code_re_verifies(scratch: Scratch) -> None:
    verified = scratch.story_verified()
    scratch.main_commit(lambda: scratch.replace_line(_STORY_FILE, "line 1\n", "line 1 (main)\n"))
    scratch.merge_main(
        resolve=lambda: scratch.write(_STORY_FILE, _numbered_lines().replace("line 1\n", "line 1 (both)\n"))
    )

    decision = _judge(scratch, verified)

    assert not decision.exempt
    assert decision.reason == REASON_MERGE_CONFLICT_OUTSIDE_PLANNING
    assert _STORY_FILE in decision.detail


def test_a_modify_delete_conflict_kept_as_the_story_s_file_re_verifies(scratch: Scratch) -> None:
    """The case only the replayed conflict check sees: main deleted the file the story changed, the merge kept the
    story's version, so neither the first-parent diff nor the tree diff names it."""
    verified = scratch.story_verified()
    scratch.main_commit(lambda: scratch.git("rm", "-q", _STORY_FILE))
    scratch.merge_main(resolve=lambda: scratch.git("add", _STORY_FILE))
    assert scratch.git("diff", "--name-only", f"{scratch.head()}^1", scratch.head()) == ""

    decision = _judge(scratch, verified)

    assert not decision.exempt
    assert decision.reason == REASON_MERGE_CONFLICT_OUTSIDE_PLANNING
    assert _STORY_FILE in decision.detail


def test_a_merge_in_which_main_changed_a_story_file_without_conflict_re_verifies(scratch: Scratch) -> None:
    verified = scratch.story_verified()
    scratch.main_commit(lambda: scratch.replace_line(_STORY_FILE, "line 12\n", "line 12 (main)\n"))
    scratch.merge_main()

    decision = _judge(scratch, verified)

    assert not decision.exempt
    assert decision.reason == REASON_MERGE_TOUCHES_STORY_FILE
    assert _STORY_FILE in decision.detail


def test_a_merge_carrying_a_hand_made_code_change_re_verifies(scratch: Scratch) -> None:
    verified = scratch.story_verified()
    scratch.main_commit(lambda: scratch.write(_OTHER_FILE, "other, moved on main\n"))
    scratch.merge_main()
    scratch.write("src/app/third.py", "slipped into the merge\n")
    scratch.git("add", "-A")
    scratch.git("commit", "-q", "--amend", "--no-edit")

    decision = _judge(scratch, verified)

    assert not decision.exempt
    assert decision.reason == REASON_MERGE_RESOLUTION_OUTSIDE_PLANNING
    assert "src/app/third.py" in decision.detail


def test_a_merge_of_a_branch_that_is_not_main_re_verifies(scratch: Scratch) -> None:
    verified = scratch.story_verified()
    scratch.git("checkout", "-q", "-b", "side", "trunk")
    scratch.write(_OTHER_FILE, "side branch\n")
    scratch.commit_all("side work")
    scratch.git("checkout", "-q", "story")
    scratch.git("merge", "--no-ff", "--no-edit", "-m", "Merge side", "side")

    decision = _judge(scratch, verified)

    assert not decision.exempt
    assert decision.reason == REASON_MERGE_NOT_OF_MAIN


def test_an_unmoved_head_reuses_its_own_verdict(scratch: Scratch) -> None:
    verified = scratch.story_verified()

    decision = _judge(scratch, verified)

    assert decision.exempt
    assert decision.basis == BASIS_HEAD_UNCHANGED


def test_a_verified_head_off_the_first_parent_chain_re_verifies(scratch: Scratch) -> None:
    """The story merged into main's line instead of main into the story: V is reached only through a second parent."""
    verified = scratch.story_verified()
    scratch.main_commit(lambda: scratch.write(_OTHER_FILE, "other, moved on main\n"))
    scratch.git("checkout", "-q", "-B", "story", "trunk")
    scratch.git("merge", "--no-ff", "--no-edit", "-m", "Merge story into a copy of main", verified)

    decision = _judge(scratch, verified)

    assert not decision.exempt
    assert decision.reason == REASON_NOT_ON_FIRST_PARENT_CHAIN


def test_a_policy_or_story_spec_change_is_never_a_planning_change(scratch: Scratch) -> None:
    spec_rel = _SPEC_REL
    verified = scratch.story_verified()
    scratch.write(_POLICY_REL, 'verify_commands = ["true"]\n')
    scratch.commit_all("policy edit")

    assert _judge(scratch, verified).reason == REASON_STORY_COMMIT

    reverified = scratch.head()
    scratch.write(spec_rel, "---\nstatus: done\n---\n")
    scratch.commit_all("spec edit")

    assert _judge(scratch, reverified, story_spec_rel=spec_rel).reason == REASON_STORY_COMMIT
    assert _judge(scratch, reverified).exempt  # any other story's spec is planning


@pytest.mark.parametrize(
    ("path", "planning"),
    [
        (_MEMLOG, True),
        ("docs/governance/spec-one-chain-per-station/.memlog.md", True),
        ("_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml", True),
        ("_bmad-output/projects/pyforge-steward/planning-artifacts/epics.md", True),
        ("_bmad-output/projects/pyforge-doctor/planning-artifacts/deferred-work-ledger.md", True),
        ("docs/dreams/pyforge-marshal.md", True),
        (".claude/memory/MEMORY.md", True),
        (_BASELINE, True),
        ("./docs/dreams/pyforge-marshal.md", True),
        ("_bmad-output/projects/pyforge-steward/planning-artifacts/marshal-policy.toml", False),
        ("_bmad-output/policy-defaults.toml", False),
        ("src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py", False),
        ("src/platform/config/flags.json", False),
        ("docs/how-to/pixi-tasks.md", False),
        ("docs/governance/ci-surfaces.yaml", False),
        ("pixi.toml", False),
    ],
)
def test_the_planning_path_rule(path: str, planning: bool) -> None:
    assert is_planning_path(path) is planning


def test_the_story_s_own_spec_is_not_planning() -> None:
    spec = "_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-102-1-x.md"
    assert is_planning_path(spec)
    assert not is_planning_path(spec, story_spec_rel=spec)


# ---------------------------------------------------------------------------
# The pure judge on shapes git rarely produces
# ---------------------------------------------------------------------------


def _facts(**overrides) -> ReuseFacts:
    values = {
        "verified_head": "v" * 40,
        "current_head": "h" * 40,
        "story_paths": (_STORY_FILE,),
        "chain": (),
    }
    values.update(overrides)
    return ReuseFacts(**values)


def test_an_empty_story_diff_re_verifies() -> None:
    assert judge_verdict_reuse(_facts(story_paths=())).reason == REASON_NO_STORY_DIFF


def test_an_octopus_merge_re_verifies() -> None:
    octopus = ChainCommit(sha="m" * 40, parents=("v" * 40, "a" * 40, "b" * 40), second_parent_on_main=True)
    assert judge_verdict_reuse(_facts(chain=(octopus,))).reason == REASON_OCTOPUS_MERGE


def test_a_moved_head_with_no_chain_re_verifies() -> None:
    assert judge_verdict_reuse(_facts(chain=None)).reason == REASON_NOT_ON_FIRST_PARENT_CHAIN
    assert judge_verdict_reuse(_facts(chain=())).reason == REASON_NOT_ON_FIRST_PARENT_CHAIN


def test_the_evidence_lists_are_bounded() -> None:
    paths = tuple(f"_bmad-output/projects/p/planning-artifacts/f{n}.md" for n in range(50))
    merge = ChainCommit(
        sha="m" * 40,
        parents=("v" * 40, "a" * 40),
        changed_paths=paths,
        second_parent_on_main=True,
        replay_conflicts=paths,
        resolution_paths=paths,
    )
    decision = judge_verdict_reuse(_facts(chain=(merge,)))
    assert decision.exempt
    record = decision.evidence["commits"][0]
    assert record["paths_from_main"] == 50
    assert len(record["planning_conflicts"]) == 20
    json.dumps(dict(decision.evidence))


# ---------------------------------------------------------------------------
# AC4: the candidate verdict
# ---------------------------------------------------------------------------


def _outcome(counter: int, payload: dict, *, writer: str = "dispatch-supervisor-1", run_id: str = _RUN_ID) -> list[str]:
    intent = build_entry(
        id=JournalEntryId(writer, counter),
        ts=f"2026-10-01T12:00:{counter:02d}.000Z",
        run_id=run_id,
        kind=dispatch_core.KIND_DISPATCH_VERIFICATION,
        phase=Phase.INTENT,
        payload={"verdict": payload.get("verdict")},
    )
    outcome = build_entry(
        id=JournalEntryId(writer, counter + 1),
        ts=f"2026-10-01T12:00:{counter:02d}.000Z",
        run_id=run_id,
        kind=dispatch_core.KIND_DISPATCH_VERIFICATION,
        phase=Phase.OUTCOME,
        intent_id=intent.id,
        payload=payload,
    )
    return [prepare_for_write(intent).line, prepare_for_write(outcome).line]


def _verified(head: str | None, **extra) -> dict:
    payload: dict = {
        "verdict": "verified",
        "ok": True,
        "scope_violation_advisories": [],
        "mode": MODE_FULL,
        "gate_digest": _TEST_DIGEST,
        **extra,
    }
    if head is not None:
        payload["head_sha"] = head
    return payload


def test_no_outcome_no_candidate() -> None:
    assert latest_reusable_verdict(fold([]), _RUN_ID) is None


def test_a_full_verified_outcome_with_its_head_is_the_candidate() -> None:
    advisory = {"code": "MRS-GATE-007", "path": "x.py"}
    lines = _outcome(0, _verified("a" * 40, scope_violation_advisories=[advisory]))
    candidate = latest_reusable_verdict(fold(lines), _RUN_ID)
    assert candidate is not None
    assert (candidate.writer_id, candidate.counter, candidate.head_sha) == ("dispatch-supervisor-1", 1, "a" * 40)
    assert candidate.scope_advisories == (advisory,)


def test_a_verdict_without_a_head_or_of_another_run_is_never_reused() -> None:
    assert latest_reusable_verdict(fold(_outcome(0, _verified(None))), _RUN_ID) is None
    assert latest_reusable_verdict(fold(_outcome(0, _verified("a" * 40), run_id="other")), _RUN_ID) is None


def test_a_later_refusal_hides_an_earlier_verified_verdict() -> None:
    lines = _outcome(0, _verified("a" * 40)) + _outcome(2, {"verdict": "refused", "ok": False})
    assert latest_reusable_verdict(fold(lines), _RUN_ID) is None


def test_a_reused_outcome_points_back_at_the_full_verdict_it_reused() -> None:
    reused = {
        "verdict": "verified",
        "ok": True,
        "mode": MODE_REUSED,
        "head_sha": "b" * 40,
        "reused_verification_id": {"writer_id": "dispatch-supervisor-1", "counter": 1},
        "reused_head_sha": "a" * 40,
    }
    lines = _outcome(0, _verified("a" * 40)) + _outcome(5, reused, writer="dispatch-land-7")
    candidate = latest_reusable_verdict(fold(lines), _RUN_ID)
    assert candidate is not None
    assert (candidate.writer_id, candidate.counter, candidate.head_sha) == ("dispatch-supervisor-1", 1, "a" * 40)


def test_a_reused_outcome_with_a_malformed_reference_is_never_reused() -> None:
    reused = {"verdict": "verified", "mode": MODE_REUSED, "reused_verification_id": {"writer_id": "w"}}
    assert latest_reusable_verdict(fold(_outcome(0, reused)), _RUN_ID) is None


# ---------------------------------------------------------------------------
# AC2: the head every verdict records, and the journal shape
# ---------------------------------------------------------------------------


class _GitVcs:
    """The two VCS reads the reuse makes, answered by real git in ``worktree``."""

    def worktree_head_sha(self, worktree: Path) -> str:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=worktree, capture_output=True, text=True, check=True
        ).stdout.strip()

    def has_uncommitted_changes(self, worktree: Path) -> bool:
        out = subprocess.run(["git", "status", "--porcelain"], cwd=worktree, capture_output=True, text=True, check=True)
        return bool(out.stdout.strip())

    def changed_files(self, _repo_root: Path, worktree: Path, *, base: str) -> tuple[str, ...]:
        diff = subprocess.run(
            ["git", "diff", "--name-only", f"{base}...HEAD"], cwd=worktree, capture_output=True, text=True, check=True
        )
        return tuple(sorted({line for line in diff.stdout.splitlines() if line}))


def _digest_now(scratch: Scratch, project: dict) -> str:
    """The gate digest a full verification at the scratch's current head records under ``project``'s policy."""
    effective, _ = policy.compose(project_slug=_SLUG, project=project, flags={})
    changed = _GitVcs().changed_files(scratch.repo, scratch.repo, base=ORIGIN_MAIN)
    return gate_set_digest(verify_gate_set(effective, changed_files=changed))


def test_the_recorded_head_is_the_clean_head_and_none_on_a_dirty_tree(scratch: Scratch) -> None:
    verified = scratch.story_verified()
    assert verification_head_sha(_GitVcs(), scratch.repo) == verified
    scratch.write("untracked.txt", "dirt\n")
    assert verification_head_sha(_GitVcs(), scratch.repo) is None
    assert verification_head_sha(object(), scratch.repo) is None


def test_a_head_read_that_raises_records_no_head(tmp_path: Path) -> None:
    class _Raises:
        def has_uncommitted_changes(self, _w: Path) -> bool:
            return False

        def worktree_head_sha(self, _w: Path) -> str:
            raise OSError("no git here")

    assert verification_head_sha(_Raises(), tmp_path) is None


def _built(**kwargs):
    defaults = {
        "findings": (),
        "gate_envelope_verdict": "clean",
        "verify_data": {},
        "repo_root": Path("."),
        "effective": policy.compose(project_slug=_SLUG, project={}, flags={})[0],
        "run_id": _RUN_ID,
        "writer_id": "dispatch-land-1",
        "counter": 0,
        "ts": "2026-10-15T12:00:00.000Z",
    }
    defaults.update(kwargs)
    return build_dispatch_verification_journal_entries(**defaults)


def test_a_full_outcome_carries_mode_full_and_its_head() -> None:
    payload = dict(_built(head_sha="c" * 40).outcome_entry.payload)
    assert payload["mode"] == MODE_FULL
    assert payload["head_sha"] == "c" * 40
    assert "reuse_declined" not in payload and "reused_verification_id" not in payload


def test_a_full_outcome_on_a_dirty_tree_carries_no_head() -> None:
    payload = dict(_built().outcome_entry.payload)
    assert payload["mode"] == MODE_FULL
    assert "head_sha" not in payload


def test_the_evidence_is_offloadable_with_the_advisories() -> None:
    assert "reuse_evidence" in _built().offload_fields


# ---------------------------------------------------------------------------
# AC5-AC7: the land-only path
# ---------------------------------------------------------------------------


class _Process:
    """``git`` runs for real; every other command (the narrow re-check's pixi tasks and the S-13.7 guard) is
    recorded and answers ``returncodes.get(<joined argv>, 0)``."""

    def __init__(self, returncodes: dict[str, int] | None = None) -> None:
        self.real = PosixProcess()
        self.returncodes = returncodes or {}
        self.commands: list[str] = []
        self.git_calls: list[list[str]] = []

    def run(self, argv, *, cwd: Path, timeout_s: float | None = None) -> ProcessResult:
        argv = list(argv)
        if argv and argv[0] == "git":
            self.git_calls.append(argv)
            return self.real.run(argv, cwd=cwd, timeout_s=timeout_s)
        joined = " ".join(argv)
        self.commands.append(joined)
        code = next((rc for key, rc in self.returncodes.items() if key in joined), 0)
        return ProcessResult(returncode=code, stdout="", stderr="red" if code else "")


def _seed_journal(scratch: Scratch, lines: list[str]) -> Path:
    run_dir = scratch.repo.parent / "runs" / _RUN_ID
    run_dir.mkdir(parents=True)
    (run_dir / "journal.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return run_dir


def _land_only(
    scratch: Scratch,
    run_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    project: dict,
    process: _Process | None = None,
):
    full_runs: list[dict] = []
    landed_with: list[object] = []

    def _full_verification(**kwargs):
        full_runs.append(kwargs)
        return build_envelope(command="dispatch verify", verdict="clean", data={"full": True})

    def _land(**kwargs):
        landed_with.append(kwargs["verification_verdict"])
        return DispatchLandingResult(verdict=DispatchLandingVerdict.LANDED), build_envelope(
            command="dispatch land", verdict="clean", data={}
        )

    monkeypatch.setattr(dispatch_module, "evaluate_dispatch_verification", _full_verification)
    monkeypatch.setattr(dispatch_module, "execute_dispatch_land", _land)
    effective, findings = policy.compose(project_slug=_SLUG, project=project, flags={})
    assert findings == ()
    proc = process if process is not None else _Process()
    verdict, _named, envelope = dispatch_module._attempt_harness_done_cap4(
        slug=_SLUG,
        story_key=normalize("102.1"),
        worktree=scratch.repo,
        repo_root=scratch.repo,
        effective_policy=effective,
        spec_text="",
        fs=LocalFs(),
        vcs=_GitVcs(),
        process=proc,
        latest_run_dir=run_dir,
    )
    lines = [json.loads(line) for line in (run_dir / "journal.jsonl").read_text(encoding="utf-8").splitlines() if line]
    outcomes = [
        line["payload"]
        for line in lines
        if line["kind"] == dispatch_core.KIND_DISPATCH_VERIFICATION and line["phase"] == "outcome"
    ]
    return verdict, envelope, full_runs, landed_with, outcomes, proc


_ON_CODE_CHANGE = {"dispatch": {"landing_reverify": "on-code-change"}}


def test_a_merge_only_move_reuses_the_verdict_and_lands_it_verified(
    scratch: Scratch, monkeypatch: pytest.MonkeyPatch
) -> None:
    verified = scratch.story_verified()
    advisory = {"code": "MRS-GATE-007", "path": "docs/x.md"}
    digest = _digest_now(scratch, _ON_CODE_CHANGE)
    run_dir = _seed_journal(
        scratch, _outcome(0, _verified(verified, scope_violation_advisories=[advisory], gate_digest=digest))
    )
    scratch.main_commit(lambda: scratch.write(_OTHER_FILE, "other, moved on main\n"))
    merge = scratch.merge_main()

    verdict, envelope, full_runs, landed_with, outcomes, proc = _land_only(
        scratch, run_dir, monkeypatch, project=_ON_CODE_CHANGE
    )

    assert full_runs == [], "the full verification ran"
    assert [str(v) for v in landed_with] == ["verified"]
    assert verdict == DispatchLandingVerdict.LANDED
    assert envelope.data["verification_mode"] == MODE_REUSED
    reused = outcomes[-1]
    assert reused["verdict"] == "verified" and reused["ok"] is True
    assert reused["mode"] == MODE_REUSED
    assert reused["head_sha"] == merge
    assert reused["reused_verification_id"] == {"writer_id": "dispatch-supervisor-1", "counter": 1}
    assert reused["reused_head_sha"] == verified
    assert reused["reuse_evidence"]["basis"] == BASIS_MERGE_OF_MAIN
    assert reused["scope_violation_advisories"] == [advisory]
    assert reused["gate_digest"] == digest
    for command in REUSE_RECHECK_COMMANDS[1:]:
        assert command in proc.commands
    assert any("spec_surface_reconcile.py" in command for command in proc.commands)


def test_a_red_narrow_re_check_declines_the_reuse_and_re_verifies_in_full(
    scratch: Scratch, monkeypatch: pytest.MonkeyPatch
) -> None:
    verified = scratch.story_verified()
    run_dir = _seed_journal(
        scratch, _outcome(0, _verified(verified, gate_digest=_digest_now(scratch, _ON_CODE_CHANGE)))
    )
    scratch.main_commit(lambda: scratch.write(_OTHER_FILE, "other, moved on main\n"))
    scratch.merge_main()

    _verdict, envelope, full_runs, landed_with, outcomes, _proc = _land_only(
        scratch, run_dir, monkeypatch, project=_ON_CODE_CHANGE, process=_Process({"story-status-check": 1})
    )

    assert len(full_runs) == 1
    assert envelope.data["verification_mode"] == MODE_FULL
    assert outcomes[-1]["mode"] == MODE_FULL
    assert outcomes[-1]["reuse_declined"]["reason"] == REASON_RECHECK_FAILED
    assert STORY_STATUS_CHECK_COMMAND in outcomes[-1]["reuse_declined"]["detail"]
    assert [str(v) for v in landed_with] == ["verified"]


def test_a_story_commit_declines_the_reuse_and_re_verifies_in_full(
    scratch: Scratch, monkeypatch: pytest.MonkeyPatch
) -> None:
    verified = scratch.story_verified()
    run_dir = _seed_journal(
        scratch, _outcome(0, _verified(verified, gate_digest=_digest_now(scratch, _ON_CODE_CHANGE)))
    )
    scratch.replace_line(_STORY_FILE, "line 5\n", "line 5 (fix)\n")
    head = scratch.commit_all("story fix")

    _verdict, _envelope, full_runs, _landed, outcomes, proc = _land_only(
        scratch, run_dir, monkeypatch, project=_ON_CODE_CHANGE
    )

    assert len(full_runs) == 1
    assert outcomes[-1]["reuse_declined"]["reason"] == REASON_STORY_COMMIT
    assert outcomes[-1]["head_sha"] == head
    assert proc.commands == [], "the narrow re-check ran on a declined reuse"


def test_no_prior_verified_verdict_re_verifies_in_full(scratch: Scratch, monkeypatch: pytest.MonkeyPatch) -> None:
    scratch.story_verified()
    run_dir = _seed_journal(scratch, _outcome(0, {"verdict": "refused", "ok": False}))

    _verdict, _envelope, full_runs, _landed, outcomes, _proc = _land_only(
        scratch, run_dir, monkeypatch, project=_ON_CODE_CHANGE
    )

    assert len(full_runs) == 1
    assert outcomes[-1]["reuse_declined"]["reason"] == REASON_NO_VERIFIED_VERDICT


@pytest.mark.parametrize("project", [{}, {"dispatch": {"landing_reverify": "always"}}])
def test_always_re_verifies_in_full_and_reads_no_reuse_fact(
    scratch: Scratch, monkeypatch: pytest.MonkeyPatch, project: dict
) -> None:
    """Even a move the exemption would pass re-verifies in full, with no reuse git read and no declined reason."""
    verified = scratch.story_verified()
    run_dir = _seed_journal(scratch, _outcome(0, _verified(verified)))
    scratch.main_commit(lambda: scratch.write(_OTHER_FILE, "other, moved on main\n"))
    merge = scratch.merge_main()

    _verdict, envelope, full_runs, _landed, outcomes, proc = _land_only(scratch, run_dir, monkeypatch, project=project)

    assert len(full_runs) == 1
    assert proc.git_calls == [] and proc.commands == []
    assert envelope.data["verification_mode"] == MODE_FULL
    assert outcomes[-1]["mode"] == MODE_FULL
    assert outcomes[-1]["head_sha"] == merge
    assert "reuse_declined" not in outcomes[-1]


# ---------------------------------------------------------------------------
# attempt_verdict_reuse's own declines
# ---------------------------------------------------------------------------


def test_a_dirty_worktree_declines(scratch: Scratch) -> None:
    verified = scratch.story_verified()
    scratch.write("untracked.txt", "dirt\n")
    reuse = attempt_verdict_reuse(
        folded=fold(_outcome(0, _verified(verified))),
        run_id=_RUN_ID,
        worktree=scratch.repo,
        repo_root=scratch.repo,
        story_spec_rel=None,
        process=PosixProcess(),
        vcs=_GitVcs(),
        current_gate_digest=_TEST_DIGEST,
    )
    assert not reuse.reused
    assert reuse.declined_payload()["reason"] == REASON_DIRTY_WORKTREE


def test_an_unknown_verified_head_is_a_git_read_failure(scratch: Scratch) -> None:
    scratch.story_verified()
    reuse = attempt_verdict_reuse(
        folded=fold(_outcome(0, _verified("0" * 40))),
        run_id=_RUN_ID,
        worktree=scratch.repo,
        repo_root=scratch.repo,
        story_spec_rel=None,
        process=PosixProcess(),
        vcs=_GitVcs(),
        current_gate_digest=_TEST_DIGEST,
    )
    assert not reuse.reused
    assert reuse.declined_payload()["reason"] == REASON_GIT_READ_FAILED


def test_an_exempt_reuse_with_a_green_injected_re_check_is_reused(scratch: Scratch) -> None:
    verified = scratch.story_verified()
    calls: list[dict] = []

    def _green(**kwargs):
        calls.append(kwargs)
        return (), {"commands": []}

    reuse = attempt_verdict_reuse(
        folded=fold(_outcome(0, _verified(verified))),
        run_id=_RUN_ID,
        worktree=scratch.repo,
        repo_root=scratch.repo,
        story_spec_rel=None,
        process=PosixProcess(),
        vcs=_GitVcs(),
        recheck=_green,
        current_gate_digest=_TEST_DIGEST,
    )
    assert reuse.reused
    assert reuse.declined_payload() is None
    assert reuse.current_head == verified
    assert len(calls) == 1


def test_the_narrow_re_check_runs_the_commit_checks_and_the_three_commands(scratch: Scratch) -> None:
    scratch.story_verified()
    process = _Process({"deferred-work-check": 2})

    findings, data = run_reuse_recheck(process=process, worktree=scratch.repo, repo_root=scratch.repo)

    assert data["commit_attribution_check"]["checked"] is True
    assert data["cfe_unsanctioned_commits_check"]["checked"] is True
    assert [report["command"] for report in data["commands"]] == list(REUSE_RECHECK_COMMANDS)
    assert [finding.code for finding in findings] == ["MRS-GATE-001"]
    assert "deferred-work-check" in findings[0].message


def test_a_red_finding_names_the_declined_detail() -> None:
    from pyforge.marshal.core.dispatch_reverify import ReuseDecision
    from pyforge.marshal.dispatch_verify import VerdictReuse

    red = Finding(code="MRS-GATE-001", severity=Severity.ERROR, message="verify command 'x' exited 1")
    reuse = VerdictReuse(decision=ReuseDecision(exempt=True, reason="exempt"), findings=(red,))
    assert reuse.declined_payload() == {"reason": REASON_RECHECK_FAILED, "detail": "MRS-GATE-001: " + red.message}


# ---------------------------------------------------------------------------
# AC2 on the supervisor's own verification
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("dirty", "expected"), [(False, "c" * 40), (True, None)])
def test_the_supervisor_journals_the_clean_head_its_verification_judged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, dirty: bool, expected: str | None
) -> None:
    import test_dispatch_supervisor_main_loop as loop

    from pyforge.marshal.dispatch_supervisor import __main__ as supervisor_main

    repo_root = loop._repo(tmp_path)
    worktree = loop._worktree(repo_root)
    loop._seed_spec(repo_root, worktree, primary=loop._READY_SPEC_TEXT)
    loop._patch_verification(monkeypatch, loop._clean_envelope)
    fs = loop.FakeFs()

    supervisor_main._run_and_journal_verification(
        fs=fs,
        vcs=loop.FakeVcs(head_sha="c" * 40, dirty=dirty),
        process=loop.FakeProcess(),
        run_dir=loop._run_dir(repo_root),
        run_id=loop._RUN_ID,
        writer_id="dispatch-supervisor-1",
        counter=0,
        repo_root=repo_root,
        slug=loop._SLUG,
        story_key=loop._STORY_KEY,
        worktree=worktree,
    )

    payload = json.loads(fs.appended[-1][1])["payload"]
    assert payload["verdict"] == "verified"
    assert payload["mode"] == MODE_FULL
    assert payload.get("head_sha") == expected


# ---------------------------------------------------------------------------
# Review fixes (PR #2238, 2026-10-15)
# ---------------------------------------------------------------------------


def test_a_merge_of_main_that_changes_a_station_policy_re_verifies(scratch: Scratch) -> None:
    """Review fix 1 (probe 5): a merge whose first-parent diff touches a ``marshal-policy.toml`` may move the very
    verify commands the verdict ran, so it is never exempt."""
    scratch.git("checkout", "-q", "trunk")
    scratch.write(_POLICY_REL, 'verify_commands = ["pytest"]\n')
    scratch.commit_all("policy on main")
    scratch.sync_origin_main()
    scratch.git("checkout", "-q", "story")
    scratch.merge_main()
    verified = scratch.story_verified()
    scratch.main_commit(lambda: scratch.write(_POLICY_REL, 'verify_commands = ["pytest", "a-new-gate"]\n'))
    scratch.merge_main()

    decision = _judge(scratch, verified, story_spec_rel=_SPEC_REL)

    assert not decision.exempt
    assert decision.reason == REASON_MERGE_TOUCHES_POLICY
    assert _POLICY_REL in decision.detail


def test_a_changed_gate_set_declines_the_reuse_and_re_verifies_in_full(
    scratch: Scratch, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review fix 1: the land-only policy is composed from the primary checkout, so a gate added between V and the
    re-land changes the gate set a fresh verification would run. The digest moves, and the reuse declines."""
    verified = scratch.story_verified()
    run_dir = _seed_journal(
        scratch, _outcome(0, _verified(verified, gate_digest=_digest_now(scratch, _ON_CODE_CHANGE)))
    )
    scratch.main_commit(lambda: scratch.write(_OTHER_FILE, "other, moved on main\n"))
    scratch.merge_main()
    widened = {
        **_ON_CODE_CHANGE,
        "verify_commands": ["pixi run --frozen -e pyforge-marshal pyforge-marshal-test", "new-gate"],
    }

    _verdict, envelope, full_runs, _landed, outcomes, proc = _land_only(scratch, run_dir, monkeypatch, project=widened)

    assert len(full_runs) == 1
    assert envelope.data["verification_mode"] == MODE_FULL
    assert outcomes[-1]["reuse_declined"]["reason"] == REASON_GATE_SET_CHANGED
    assert proc.git_calls == [], "a changed gate set declines before any reuse git read"


def test_a_verdict_without_a_gate_digest_is_never_reused(scratch: Scratch) -> None:
    verified = scratch.story_verified()
    payload = _verified(verified)
    del payload["gate_digest"]
    for lines, current in ((_outcome(0, payload), _TEST_DIGEST), (_outcome(0, _verified(verified)), None)):
        reuse = attempt_verdict_reuse(
            folded=fold(lines),
            run_id=_RUN_ID,
            worktree=scratch.repo,
            repo_root=scratch.repo,
            story_spec_rel=_SPEC_REL,
            process=PosixProcess(),
            vcs=_GitVcs(),
            current_gate_digest=current,
        )
        assert reuse.declined_payload()["reason"] == REASON_GATE_SET_CHANGED


def test_the_gate_digest_is_stable_and_moves_with_the_gate_set() -> None:
    assert gate_set_digest(["a  b", "c"]) == gate_set_digest(["a b", "c"])
    assert gate_set_digest(["a", "c"]) != gate_set_digest(["c", "a"])
    assert gate_set_digest(["a"]) != gate_set_digest(["a", "b"])
    effective, _ = policy.compose(project_slug=_SLUG, project={"verify_commands": ["x-gate"]}, flags={})
    gates = verify_gate_set(effective, changed_files=("src/shared/packages/pyforge-marshal/src/pyforge/marshal/x.py",))
    assert gates[0] == "x-gate"
    assert any("pyforge-marshal-coverage-gate" in command for command in gates)
    assert verify_gate_set(effective, changed_files=()) != gates


def test_a_full_verification_journals_the_digest_of_the_gates_it_ran(scratch: Scratch) -> None:
    """Review fix 1: ``evaluate_dispatch_verification`` records the digest of exactly the gate set it ran, and the
    OUTCOME carries it."""
    from pyforge.marshal.dispatch_verify import evaluate_dispatch_verification

    scratch.story_verified()
    effective, _ = policy.compose(project_slug=_SLUG, project={"verify_commands": ["x-gate"]}, flags={})
    process = _Process()
    envelope = evaluate_dispatch_verification(
        project_slug=_SLUG,
        story_key=normalize("102.1"),
        worktree=scratch.repo,
        repo_root=scratch.repo,
        effective=effective,
        spec_text=None,
        process=process,
        vcs=_GitVcs(),
    )
    changed = _GitVcs().changed_files(scratch.repo, scratch.repo, base=ORIGIN_MAIN)
    assert envelope.data["gate_digest"] == gate_set_digest(verify_gate_set(effective, changed_files=changed))
    assert "x-gate" in process.commands
    payload = dict(_built(verify_data=dict(envelope.data)).outcome_entry.payload)
    assert payload["gate_digest"] == envelope.data["gate_digest"]


def test_a_merge_of_a_main_commit_main_later_reverted_re_verifies(scratch: Scratch) -> None:
    """Review fix 2 (probe 6): the merged commit is on main's first-parent line, but main reverted it, so the path it
    brought no longer reads current main's content."""
    verified = scratch.story_verified()
    bad = scratch.main_commit(lambda: scratch.write(_OTHER_FILE, "bad, later reverted\n"), "bad")
    scratch.main_commit(lambda: scratch.write(_OTHER_FILE, "other\n"), "Revert bad")
    scratch.git("merge", "--no-ff", "--no-edit", "-m", "Merge an old main commit", bad)

    decision = _judge(scratch, verified, story_spec_rel=_SPEC_REL)

    assert not decision.exempt
    assert decision.reason == REASON_MERGE_STALE_AGAINST_MAIN
    assert _OTHER_FILE in decision.detail


def test_a_path_main_moved_again_after_the_merge_re_verifies(scratch: Scratch) -> None:
    """Review fix 2, the conservative side: main changed a path the merge brought once more after the merge, so the
    branch no longer holds the tree main would land."""
    verified = scratch.story_verified()
    scratch.main_commit(lambda: scratch.write(_OTHER_FILE, "other, moved on main\n"))
    scratch.merge_main()
    scratch.main_commit(lambda: scratch.write(_OTHER_FILE, "other, moved again\n"))

    decision = _judge(scratch, verified, story_spec_rel=_SPEC_REL)

    assert decision.reason == REASON_MERGE_STALE_AGAINST_MAIN


def test_a_merge_of_a_commit_off_main_s_first_parent_line_re_verifies(scratch: Scratch) -> None:
    """Review fix 2 (nit 3): a commit inside a branch main merged is an ancestor of main, but main was never in that
    state. Only a first-parent commit of main is a merge of main."""
    verified = scratch.story_verified()
    scratch.git("checkout", "-q", "-b", "feature", "trunk")
    scratch.write(_OTHER_FILE, "half a feature\n")
    half = scratch.commit_all("feature, part one")
    scratch.write("src/app/feature.py", "part two\n")
    scratch.commit_all("feature, part two")
    scratch.git("checkout", "-q", "trunk")
    scratch.git("merge", "--no-ff", "--no-edit", "-m", "Merge feature", "feature")
    scratch.sync_origin_main()
    scratch.git("checkout", "-q", "story")
    scratch.git("merge", "--no-ff", "--no-edit", "-m", "Merge half a feature", half)

    decision = _judge(scratch, verified, story_spec_rel=_SPEC_REL)

    assert not decision.exempt
    assert decision.reason == REASON_MERGE_NOT_OF_MAIN


def test_a_conftest_under_a_nested_planning_artifacts_directory_re_verifies(scratch: Scratch) -> None:
    """Review fix 4 (probe 7)."""
    verified = scratch.story_verified()
    scratch.write("_bmad-output/projects/x/tests/planning-artifacts/conftest.py", "raise SystemExit\n")
    scratch.commit_all("planning?")

    decision = _judge(scratch, verified, story_spec_rel=_SPEC_REL)

    assert decision.reason == REASON_STORY_COMMIT


@pytest.mark.parametrize(
    ("path", "planning"),
    [
        ("_bmad-output/projects/x/tests/planning-artifacts/conftest.py", False),
        ("_bmad-output/projects/x/tests/planning-artifacts/notes.md", False),
        ("_bmad-output/projects/x/planning-artifacts/sub/conftest.py", False),
        ("_bmad-output/projects/x/planning-artifacts/sub/notes.md", True),
        ("_bmad-output/projects/planning-artifacts/notes.md", False),
        ("src/shared/packages/pyforge-x/src/pyforge/x/.memlog.md", False),
        ("src/shared/packages/pyforge-x/deferred-work-ledger.md", False),
        ("docs/governance/spec-x/.memlog.md", True),
        ("docs/governance/ci-surfaces.yaml", False),
        ("docs/dreams/../../src/app/core.py", False),
        ("docs/dreams//pyforge-marshal.md", False),
        ("docs/dreams", False),
        ("docs/dreams/helper.py", False),
        (".claude/memory/feedback/x.md", True),
    ],
)
def test_the_planning_rule_is_anchored(path: str, planning: bool) -> None:
    assert is_planning_path(path) is planning


def _reused_payload(*, counter: int = 1, head: str = "a" * 40) -> dict:
    return {
        "verdict": "verified",
        "ok": True,
        "mode": MODE_REUSED,
        "head_sha": "b" * 40,
        "reused_verification_id": {"writer_id": "dispatch-supervisor-1", "counter": counter},
        "reused_head_sha": head,
    }


@pytest.mark.parametrize(
    ("base_payload", "reused"),
    [
        (None, _reused_payload()),
        ({"verdict": "refused", "ok": False, "mode": MODE_FULL, "head_sha": "a" * 40}, _reused_payload()),
        ({**_reused_payload(), "head_sha": "a" * 40}, _reused_payload()),
        (_verified("c" * 40), _reused_payload()),
        (_verified("a" * 40), _reused_payload(counter=9)),
    ],
    ids=["base-missing", "base-refused", "base-is-a-reuse", "base-head-differs", "base-id-differs"],
)
def test_a_reuse_whose_base_does_not_hold_up_is_never_a_candidate(base_payload, reused) -> None:
    """Review fix 5: the base a reused OUTCOME names must be present, verified, a full verification, and judge the
    head the reuse names."""
    lines = _outcome(0, base_payload) if base_payload is not None else []
    lines += _outcome(5, reused, writer="dispatch-land-7")
    assert latest_reusable_verdict(fold(lines), _RUN_ID) is None


def test_a_reuse_with_a_sound_base_carries_the_base_s_gate_digest() -> None:
    lines = _outcome(0, _verified("a" * 40, gate_digest="sha256:base")) + _outcome(
        5, _reused_payload(), writer="dispatch-land-7"
    )
    candidate = latest_reusable_verdict(fold(lines), _RUN_ID)
    assert candidate is not None
    assert candidate.gate_digest == "sha256:base"


def test_a_story_without_a_tracked_spec_declines_and_re_verifies_in_full(
    scratch: Scratch, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Review fix 6: with no tracked spec the story's own spec cannot be told from planning, so reuse fails closed."""
    verified = scratch.story_verified(with_spec=False)
    run_dir = _seed_journal(
        scratch, _outcome(0, _verified(verified, gate_digest=_digest_now(scratch, _ON_CODE_CHANGE)))
    )
    scratch.main_commit(lambda: scratch.write(_OTHER_FILE, "other, moved on main\n"))
    scratch.merge_main()

    _verdict, _envelope, full_runs, _landed, outcomes, proc = _land_only(
        scratch, run_dir, monkeypatch, project=_ON_CODE_CHANGE
    )

    assert len(full_runs) == 1
    assert outcomes[-1]["reuse_declined"]["reason"] == REASON_NO_STORY_SPEC
    assert proc.git_calls == []
