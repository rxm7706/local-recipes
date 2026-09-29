"""Unit tests for ``pyforge.marshal.seed.verbs.preconditions`` (Story 10.4)
-- covers every precondition row of the spec's I/O & Edge-Case Matrix
against a REAL ``tmp_path`` git repo (``git init``/``commit`` through the
same ``_git`` helper convention ``test_seed_plan_build.py`` and
``test_vcs_git.py`` already establish -- real git I/O, never mocked).

Each rung's own refusal, its exit code 3 and its non-blank remedy; the
ladder's fixed ORDER (a repo failing two rungs reports the earlier one);
``dry_run`` bypassing rung 2 and ONLY rung 2; ``force`` bypassing rung 6 and
ONLY rung 6; the git-absent row through an injected fake process that raises
``ProcessError``; multi-divergence reported in one message; an absent
managed path passing; plus an AGREEMENT test pinning ``_is_dirty`` to
``plan.build._repo_is_dirty`` and their shared git timeout.

A review pass adds the regressions for five defects this file did not
previously reach: "cannot verify" reported as "absent" when a managed
file's PARENT directory is unreadable, an unrecorded-but-present managed
region passing silently, a misspelled ``repo_root`` refused with a remedy
for the wrong problem, an action targeting the repo root itself clearing
every structural rung, and the two message/docstring claims that promised
more than the code delivers.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
from pyforge.core.process import PosixProcess, ProcessError, ProcessResult

from pyforge.marshal.seed.detect.hashes import hash_content
from pyforge.marshal.seed.detect.inventory import ArtifactState
from pyforge.marshal.seed.errors import PreconditionFailure
from pyforge.marshal.seed.fs import NeverWrite, _matches
from pyforge.marshal.seed.model.manifest import ArtifactClass
from pyforge.marshal.seed.model.version import ModelVersion
from pyforge.marshal.seed.plan.build import _GIT_TIMEOUT_S as _BUILD_GIT_TIMEOUT_S
from pyforge.marshal.seed.plan.build import _repo_is_dirty
from pyforge.marshal.seed.plan.types import Action, Plan, RepoFingerprint
from pyforge.marshal.seed.regions.markers import (
    RegionFormat,
    region_sha,
    render_begin,
    render_end,
)
from pyforge.marshal.seed.verbs import preconditions
from pyforge.marshal.seed.verbs.preconditions import (
    _GIT_TIMEOUT_S,
    ManagedRecord,
    _is_dirty,
    check_preconditions,
)
from pyforge.marshal.seed.verbs.skips import apply_skips, managed_after_skips

_VERSION = ModelVersion.parse("1.0.0")


# --- builders --------------------------------------------------------------


def _action(**overrides) -> Action:
    fields = {
        "artifact_id": "agents-md",
        "artifact_class": ArtifactClass.COPIED_MANAGED,
        "current_state": ArtifactState.ABSENT,
        "target_state": ArtifactState.PRESENT_CONFORMANT,
        "target_path": "AGENTS.md",
        "chosen_anchor": (),
        "rationale": "test",
    }
    fields.update(overrides)
    return Action(**fields)


def _fingerprint(**overrides) -> RepoFingerprint:
    fields = {"git_head": None, "dirty": False, "artifact_hashes": ()}
    fields.update(overrides)
    return RepoFingerprint(**fields)


def _plan(*actions: Action) -> Plan:
    return Plan(actions=tuple(actions), repo_fingerprint=_fingerprint())


def _check(plan: Plan, repo: Path, **overrides):
    """``check_preconditions`` with this file's defaults: an empty
    never-write set and no managed records, so each test names only the
    input its own row is about."""
    kwargs = {"repo_root": repo, "never_write": NeverWrite(patterns=()), "managed": ()}
    kwargs.update(overrides)
    return check_preconditions(plan, **kwargs)


# --- real-git fixtures -----------------------------------------------------


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Mirrors ``test_seed_plan_build.py``/``test_vcs_git.py``'s own
    real-git-repo test convention: real ``git`` I/O against a ``tmp_path``,
    never mocked."""
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


@pytest.fixture
def clean_repo(tmp_path: Path) -> Path:
    _init_git_repo(tmp_path)
    return tmp_path


def _commit_all(repo: Path) -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "fixture")


class _RaisingProcess:
    """A ``ProcessPort`` whose ``run`` always fails to launch -- the
    git-binary-absent row, without uninstalling git from the host."""

    def run(self, argv, *, cwd, timeout_s=None):  # noqa: ARG002 - port signature
        raise ProcessError(f"executable not found: {argv[0]!r}")


class _ScriptedProcess:
    """A ``ProcessPort`` returning a fixed ``returncode``/``stdout`` for
    every call -- used only for the rows a real repo cannot produce on
    demand (a ``git status`` that exits non-zero)."""

    def __init__(self, returncode: int, stdout: str = "") -> None:
        self._result = ProcessResult(returncode=returncode, stdout=stdout, stderr="")

    def run(self, argv, *, cwd, timeout_s=None):  # noqa: ARG002 - port signature
        if argv[:2] == ["git", "rev-parse"]:
            return ProcessResult(returncode=0, stdout=".git\n", stderr="")
        return self._result


# --- rung 1: not a git repo ------------------------------------------------


def test_a_non_git_target_is_refused(tmp_path):
    with pytest.raises(PreconditionFailure) as excinfo:
        _check(_plan(), tmp_path)

    assert excinfo.value.exit_code == 3
    assert "not-a-git-repo" in excinfo.value.message
    assert excinfo.value.remedy.strip()
    assert "git init" in excinfo.value.remedy


def test_a_non_git_target_is_refused_even_under_dry_run(tmp_path):
    """``dry_run`` bypasses rung 2 and ONLY rung 2 -- whether git exists is
    not a claim about whether reading is safe."""
    with pytest.raises(PreconditionFailure, match="not-a-git-repo"):
        _check(_plan(), tmp_path, dry_run=True)


def test_a_freshly_initialized_repo_with_no_commits_is_accepted(tmp_path):
    """``rev-parse --git-dir``, not ``rev-parse HEAD``: a repo with an
    unborn HEAD is still a git repo, and is the single most likely target of
    a first ``seed init``."""
    _git(tmp_path, "init", "-b", "main")
    assert _check(_plan(), tmp_path) is None


# --- git-probe failure -----------------------------------------------------


def test_a_process_error_from_the_git_probe_refuses_fail_closed(clean_repo):
    """A probe that cannot run is never allowed to degrade into a
    "clean"/"is a repo" answer."""
    with pytest.raises(PreconditionFailure) as excinfo:
        _check(_plan(), clean_repo, process=_RaisingProcess())

    assert excinfo.value.exit_code == 3
    assert "git-probe-failed" in excinfo.value.message
    assert "rev-parse --git-dir" in excinfo.value.message
    assert excinfo.value.remedy.strip()


def test_a_process_error_from_the_dirty_probe_also_refuses_fail_closed(clean_repo):
    """Rung 2's own wrap, reached only when `rev-parse` succeeds and
    `status` does not -- the rung-1 fake above short-circuits before this
    code ever runs."""

    class _StatusFails:
        def run(self, argv, *, cwd, timeout_s=None):  # noqa: ARG002 - port signature
            if argv[:2] == ["git", "rev-parse"]:
                return ProcessResult(returncode=0, stdout=".git\n", stderr="")
            raise ProcessError("boom")

    with pytest.raises(PreconditionFailure) as excinfo:
        _check(_plan(), clean_repo, process=_StatusFails())

    assert excinfo.value.exit_code == 3
    assert "git-probe-failed" in excinfo.value.message
    assert "status --porcelain" in excinfo.value.message


# --- a repo_root that is not there -----------------------------------------


def test_a_missing_repo_root_is_refused_naming_the_directory_not_a_missing_git(tmp_path):
    """``subprocess`` reports a non-existent ``cwd`` as
    ``FileNotFoundError``, which ``PosixProcess.run`` cannot tell apart from
    a missing executable -- so a merely MISSPELLED repo root used to be
    refused with "install git and make it resolvable on PATH", a remedy for
    the wrong problem and for the less likely of the two causes.
    ``fs._guard`` raises its own explicit error for exactly this
    misconfiguration; this is that check, one layer earlier."""
    missing = tmp_path / "typo-in-the-path"

    with pytest.raises(PreconditionFailure) as excinfo:
        _check(_plan(), missing)

    assert excinfo.value.exit_code == 3
    assert "repo-root-missing" in excinfo.value.message
    assert str(missing) in excinfo.value.message
    assert excinfo.value.remedy.strip()
    assert "install git" not in excinfo.value.remedy


def test_a_repo_root_that_is_a_file_is_refused_the_same_way(tmp_path):
    file_root = tmp_path / "plan.json"
    file_root.write_text("{}", encoding="utf-8")

    with pytest.raises(PreconditionFailure, match="repo-root-missing"):
        _check(_plan(), file_root)


def test_an_unresolvable_repo_root_is_refused_as_a_typed_failure_not_a_crash(tmp_path):
    """``Path.resolve()`` raises a bare ``ValueError`` -- not an ``OSError``
    -- for an embedded NUL, which would otherwise escape this module
    untyped, with no exit code and no remedy at all."""
    with pytest.raises(PreconditionFailure) as excinfo:
        _check(_plan(), Path(f"{tmp_path}/bad\x00root"))

    assert excinfo.value.exit_code == 3
    assert "repo-root-unusable" in excinfo.value.message
    assert excinfo.value.remedy.strip()


def test_the_missing_repo_root_check_precedes_the_not_a_git_repo_refusal(tmp_path):
    """It lives inside rung 1 (its first git probe), so the ladder's fixed
    order still holds -- nothing about a repo root that is not there can be
    reported later than "this is not a git repo"."""
    with pytest.raises(PreconditionFailure) as excinfo:
        _check(_plan(), tmp_path / "absent")

    assert "not-a-git-repo" not in excinfo.value.message


# --- rung 2: dirty worktree ------------------------------------------------


def test_a_dirty_worktree_is_refused(clean_repo):
    (clean_repo / "README.md").write_text("edited\n", encoding="utf-8")

    with pytest.raises(PreconditionFailure) as excinfo:
        _check(_plan(), clean_repo)

    assert excinfo.value.exit_code == 3
    assert "dirty-worktree" in excinfo.value.message
    assert excinfo.value.remedy.strip()


def test_an_untracked_file_counts_as_dirty(clean_repo):
    """``--untracked-files=normal``: an untracked file is a change ``git
    checkout .`` would not restore, so it is exactly what SC-05 cares
    about."""
    (clean_repo / "scratch.txt").write_text("x\n", encoding="utf-8")

    with pytest.raises(PreconditionFailure, match="dirty-worktree"):
        _check(_plan(), clean_repo)


def test_a_dirty_worktree_is_allowed_under_dry_run(clean_repo):
    """The ONE rung ``dry_run`` bypasses -- a read-only run cannot make an
    uncommitted change harder to recover."""
    (clean_repo / "README.md").write_text("edited\n", encoding="utf-8")

    assert _check(_plan(), clean_repo, dry_run=True) is None


def test_a_non_zero_git_status_is_treated_as_dirty(clean_repo):
    """Cannot confirm clean is not the same as clean -- the same
    conservative direction ``plan.build._repo_is_dirty`` already takes."""
    with pytest.raises(PreconditionFailure, match="dirty-worktree"):
        _check(_plan(), clean_repo, process=_ScriptedProcess(returncode=128))


def test_force_does_not_bypass_a_dirty_worktree(clean_repo):
    """``force`` bypasses rung 6 and ONLY rung 6: discarding a hand-edit is
    a statement about content, not about whether git can undo the run."""
    (clean_repo / "README.md").write_text("edited\n", encoding="utf-8")

    with pytest.raises(PreconditionFailure, match="dirty-worktree"):
        _check(_plan(), clean_repo, force=True)


# --- rung 3: containment ---------------------------------------------------


@pytest.mark.parametrize("escaping", ["../outside.md", "../../outside.md"])
def test_an_action_targeting_a_path_above_the_repo_root_is_refused(clean_repo, escaping):
    with pytest.raises(PreconditionFailure) as excinfo:
        _check(_plan(_action(artifact_id="escaper", target_path=escaping)), clean_repo)

    assert excinfo.value.exit_code == 3
    assert "target-escapes-repo" in excinfo.value.message
    assert "escaper" in excinfo.value.message
    assert escaping in excinfo.value.message
    assert excinfo.value.remedy.strip()


def test_an_action_targeting_an_absolute_path_is_refused(clean_repo):
    with pytest.raises(PreconditionFailure, match="target-escapes-repo"):
        _check(_plan(_action(artifact_id="abs", target_path="/etc/passwd")), clean_repo)


def test_an_unresolvable_target_path_is_refused_as_a_typed_failure_not_a_crash(clean_repo):
    """`Path.resolve()` raises a bare `ValueError` -- not an `OSError` -- for
    an embedded NUL, and `target_path` reaches this module from a
    `plan.json` that is only type-checked at load. An untyped crash would
    reach a CLI dispatcher with no `exit_code` and no remedy at all."""
    with pytest.raises(PreconditionFailure) as excinfo:
        _check(_plan(_action(artifact_id="nul", target_path="bad\x00path.md")), clean_repo)

    assert excinfo.value.exit_code == 3
    assert "target-escapes-repo" in excinfo.value.message
    assert excinfo.value.remedy.strip()


def test_containment_is_checked_before_the_never_write_set(clean_repo):
    """Rung 3 precedes rung 4 in the fixed order, so an escaping path that
    would ALSO match a never-write pattern reports the escape."""
    with pytest.raises(PreconditionFailure, match="target-escapes-repo"):
        _check(
            _plan(_action(artifact_id="e", target_path="../outside.md")),
            clean_repo,
            never_write=NeverWrite(patterns=("*",)),
        )


# --- rung 4: never-write ---------------------------------------------------


def test_an_action_targeting_a_never_write_path_is_refused(clean_repo):
    with pytest.raises(PreconditionFailure) as excinfo:
        _check(
            _plan(_action(artifact_id="dream", target_path="docs/dreams/x.md")),
            clean_repo,
            never_write=NeverWrite(patterns=("docs/dreams/*.md",)),
        )

    assert excinfo.value.exit_code == 3
    assert "never-write-target" in excinfo.value.message
    assert "dream" in excinfo.value.message
    assert "docs/dreams/x.md" in excinfo.value.message
    assert "docs/dreams/*.md" in excinfo.value.message
    assert excinfo.value.remedy.strip()


def test_the_never_write_rung_is_not_bypassable_by_force(clean_repo):
    """AD-61's frozen guard: a guard with an override is a suggestion."""
    with pytest.raises(PreconditionFailure, match="never-write-target"):
        _check(
            _plan(_action(artifact_id="dream", target_path="docs/dreams/x.md")),
            clean_repo,
            never_write=NeverWrite(patterns=("docs/dreams/*.md",)),
            force=True,
        )


def test_the_never_write_rung_is_not_bypassable_by_dry_run(clean_repo):
    with pytest.raises(PreconditionFailure, match="never-write-target"):
        _check(
            _plan(_action(artifact_id="dream", target_path="docs/dreams/x.md")),
            clean_repo,
            never_write=NeverWrite(patterns=("docs/dreams/*.md",)),
            dry_run=True,
        )


def test_the_never_write_remedy_claims_only_the_guarantee_the_code_provides(clean_repo):
    """The remedy used to read "not overridable, by --force or otherwise",
    which overclaims: a symlinked ANCESTOR directory does route a write past
    the pattern, because rungs 3-5 resolve parent links exactly as
    ``fs._guard`` does. The real guarantee -- no FLAG overrides it -- is
    what the message must say."""
    with pytest.raises(PreconditionFailure) as excinfo:
        _check(
            _plan(_action(artifact_id="dream", target_path="docs/dreams/x.md")),
            clean_repo,
            never_write=NeverWrite(patterns=("docs/dreams/*.md",)),
        )

    assert "no flag overrides" in excinfo.value.remedy
    assert "--force" in excinfo.value.remedy
    assert "or otherwise" not in excinfo.value.remedy


def test_an_exempt_action_target_bypasses_a_matching_never_write_pattern(clean_repo):
    """Story 10.8's own rung-4 short-circuit: a manifest-declared writable
    artifact (``copied-managed``/``copied-seeded``) whose resolved path is
    also in ``never_write.exempt`` must clear rung 4 even though it matches
    a broader deny glob."""
    assert (
        _check(
            _plan(_action(artifact_id="dream", target_path="docs/dreams/README.md")),
            clean_repo,
            never_write=NeverWrite(
                patterns=("docs/dreams/*.md",),
                exempt=frozenset({"docs/dreams/README.md"}),
            ),
        )
        is None
    )


def test_a_non_exempt_action_in_the_same_plan_still_refuses(clean_repo):
    """The other half: exempting ONE artifact's target must not widen
    protection for a DIFFERENT action in the same plan that also matches the
    pattern."""
    with pytest.raises(PreconditionFailure, match="never-write-target"):
        _check(
            _plan(_action(artifact_id="other-dream", target_path="docs/dreams/other.md")),
            clean_repo,
            never_write=NeverWrite(
                patterns=("docs/dreams/*.md",),
                exempt=frozenset({"docs/dreams/README.md"}),
            ),
        )


# --- exempt agreement: rung 4 vs. fs._matches (review finding) -------------
#
# Rung 4's ``relative in never_write.exempt`` and ``fs._matches``'s own
# identical check are two independent short-circuits over the SAME
# ``NeverWrite.exempt`` field (fs.py is a module this story's Surface may
# not otherwise edit beyond the one field/check it already adds -- see
# fs.py's own docstring). ``skips.first_match``/``fs._matches`` already have
# a dedicated parametrized agreement test
# (``test_seed_verbs_skips.py::test_first_match_agrees_with_fs_matches_on_every_pattern_and_path``)
# because two independent implementations of "the same kind of rule" must
# never silently disagree; this is that same guard applied to the NEW
# exempt short-circuit, over a small table rather than a full cross-product
# (``check_preconditions`` needs a real ``Plan``/git repo per case, unlike
# ``first_match``/``_matches``' bare ``(pattern, path)`` signature, so a
# parametrized N-by-M table is disproportionate for one new field).
_EXEMPT_AGREEMENT_CASES = (
    ("docs/dreams/README.md", frozenset({"docs/dreams/README.md"})),
    ("docs/dreams/other.md", frozenset({"docs/dreams/README.md"})),
    ("docs/dreams/README.md", frozenset()),
)


@pytest.mark.parametrize(("target_path", "exempt"), _EXEMPT_AGREEMENT_CASES)
def test_rung_4_agrees_with_fs_matches_on_the_exempt_short_circuit(
    clean_repo, target_path: str, exempt: frozenset[str]
):
    never_write = NeverWrite(patterns=("docs/dreams/*.md",), exempt=exempt)
    fs_says_blocked = _matches(never_write, target_path) is not None

    if fs_says_blocked:
        with pytest.raises(PreconditionFailure, match="never-write-target"):
            _check(
                _plan(_action(artifact_id="dream", target_path=target_path)),
                clean_repo,
                never_write=never_write,
            )
    else:
        assert (
            _check(
                _plan(_action(artifact_id="dream", target_path=target_path)),
                clean_repo,
                never_write=never_write,
            )
            is None
        )


def test_a_never_write_pattern_that_matches_nothing_does_not_refuse(clean_repo):
    assert (
        _check(
            _plan(_action(artifact_id="a", target_path="AGENTS.md")),
            clean_repo,
            never_write=NeverWrite(patterns=("docs/dreams/*.md",)),
        )
        is None
    )


# --- rung 5: symlink -------------------------------------------------------


def test_an_action_targeting_an_existing_symlink_is_refused(clean_repo):
    (clean_repo / "real.md").write_text("real\n", encoding="utf-8")
    (clean_repo / "AGENTS.md").symlink_to("real.md")
    _commit_all(clean_repo)

    with pytest.raises(PreconditionFailure) as excinfo:
        _check(_plan(_action(artifact_id="agents-md", target_path="AGENTS.md")), clean_repo)

    assert excinfo.value.exit_code == 3
    assert "symlink-target" in excinfo.value.message
    assert "agents-md" in excinfo.value.message
    # The DECLARED path, not only the resolved one -- naming `real.md` twice
    # would leave a reader unable to tell which artifact path is the link.
    assert "AGENTS.md" in excinfo.value.message
    assert "real.md" in excinfo.value.message
    assert excinfo.value.remedy.strip()


def test_an_action_targeting_an_ordinary_file_is_not_refused_as_a_symlink(clean_repo):
    (clean_repo / "AGENTS.md").write_text("plain\n", encoding="utf-8")
    _commit_all(clean_repo)

    assert _check(_plan(_action(artifact_id="agents-md", target_path="AGENTS.md")), clean_repo) is None


@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    reason="root bypasses the directory permission bit this test depends on",
)
def test_a_symlink_under_an_unreadable_parent_directory_is_refused(clean_repo):
    """The rung-5 twin of
    ``test_a_managed_file_under_an_unreadable_parent_directory_is_refused``
    (found in review). ``Path.is_symlink()`` swallows every ``OSError`` and
    answers ``False``, and "not a symlink" is this rung's one PASSING
    answer -- so under an unreadable PARENT (``EACCES``) a real symlink
    cleared rung 5 and the runner wrote THROUGH it, to a destination that
    can sit outside the repo entirely. That defeats SC-05: git cannot undo
    a write it never saw. ``lstat()`` inside a ``try`` distinguishes "not
    there" (pass, nothing to write over) from "cannot tell" (refuse).

    ``dry_run=True`` because ``git status`` cannot read the locked
    directory either -- it bypasses rung 2 and only rung 2, so rung 5 still
    runs."""
    parent = clean_repo / "locked"
    parent.mkdir()
    (parent / "real.md").write_text("real\n", encoding="utf-8")
    (parent / "AGENTS.md").symlink_to("real.md")
    _commit_all(clean_repo)

    parent.chmod(0o000)
    try:
        with pytest.raises(PreconditionFailure) as excinfo:
            _check(
                _plan(_action(artifact_id="agents-md", target_path="locked/AGENTS.md")),
                clean_repo,
                dry_run=True,
            )

        assert excinfo.value.exit_code == 3
        assert "symlink-target" in excinfo.value.message
        assert "cannot be stat'ed to rule out a symlink" in excinfo.value.message
        assert "agents-md" in excinfo.value.message
        assert "locked/AGENTS.md" in excinfo.value.message
        assert excinfo.value.remedy.strip()
    finally:
        # Restored unconditionally: a 0o000 directory left behind would
        # break pytest's own tmp_path teardown for every later test.
        parent.chmod(0o755)


def test_an_action_whose_target_does_not_exist_clears_the_symlink_rung(clean_repo):
    """The `FileNotFoundError` branch of rung 5's `lstat()`. An artifact that
    is simply ABSENT is the ordinary create case -- there is nothing on disk
    to be a symlink -- so it must pass, not be swept up by the fail-closed
    handling added for "cannot tell".

    No `_commit_all` here: the fixture's repo is already clean and this test
    writes nothing, and `git commit` with an empty index exits non-zero."""
    assert _check(_plan(_action(artifact_id="agents-md", target_path="AGENTS.md")), clean_repo) is None


def test_the_symlink_refusal_survives_a_link_that_vanishes_before_it_is_read(clean_repo, monkeypatch):
    """`lstat()` says "symlink" and `readlink()` reports the destination for
    the message, but the two are not atomic. If the link is removed in
    between, a raw `OSError` would escape the ladder and replace a
    `PreconditionFailure` (exit 3, with a remedy) with a crash -- so the
    destination degrades to a placeholder instead."""
    (clean_repo / "real.md").write_text("real\n", encoding="utf-8")
    (clean_repo / "AGENTS.md").symlink_to("real.md")
    _commit_all(clean_repo)

    def _vanished(self):
        raise FileNotFoundError(2, "No such file or directory")

    monkeypatch.setattr(Path, "readlink", _vanished)

    with pytest.raises(PreconditionFailure) as excinfo:
        _check(_plan(_action(artifact_id="agents-md", target_path="AGENTS.md")), clean_repo)

    assert excinfo.value.exit_code == 3
    assert "symlink-target" in excinfo.value.message
    assert "<unreadable>" in excinfo.value.message
    assert excinfo.value.remedy.strip()


def test_a_symlink_pointing_outside_the_repo_is_refused_by_the_earlier_containment_rung(clean_repo, tmp_path_factory):
    """Rung 3 resolves symlinks (as ``fs._guard`` does), so an escaping link
    is caught by containment before rung 5 ever looks -- the earlier rung
    wins, exactly as the fixed order requires."""
    outside = tmp_path_factory.mktemp("outside")
    (outside / "target.md").write_text("elsewhere\n", encoding="utf-8")
    (clean_repo / "AGENTS.md").symlink_to(outside / "target.md")
    _commit_all(clean_repo)

    with pytest.raises(PreconditionFailure, match="target-escapes-repo"):
        _check(_plan(_action(artifact_id="agents-md", target_path="AGENTS.md")), clean_repo)


# --- rung 3: the repo root is not a write target ---------------------------


@pytest.mark.parametrize("target_path", ["", ".", "./", "docs/.."])
def test_an_action_targeting_the_repo_root_itself_is_refused(clean_repo, target_path):
    """Every one of these normalizes to ``"."``, which is not ``None`` (rung
    3 cleared), matches no realistic never-write glob (rung 4 cleared) and
    is not a symlink (rung 5 cleared) -- so an action naming the whole repo
    used to reach the apply runner having passed every structural rung.
    ``Action.target_path`` is only ``_require_str``-checked at the
    ``plan.json`` boundary, so ``""`` is reachable from a hand-edited
    plan."""
    with pytest.raises(PreconditionFailure) as excinfo:
        _check(_plan(_action(artifact_id="rooted", target_path=target_path)), clean_repo)

    assert excinfo.value.exit_code == 3
    assert "target-is-repo-root" in excinfo.value.message
    assert "rooted" in excinfo.value.message
    assert excinfo.value.remedy.strip()


def test_a_repo_root_target_is_refused_even_with_an_empty_never_write_set_and_force(clean_repo):
    """Naming the rungs it used to slip past: no never-write pattern to
    catch it, nothing on disk to be a symlink, and ``--force`` (which
    bypasses rung 6 only) does not reach it either."""
    with pytest.raises(PreconditionFailure, match="target-is-repo-root"):
        _check(
            _plan(_action(artifact_id="rooted", target_path="")),
            clean_repo,
            never_write=NeverWrite(patterns=()),
            force=True,
        )


def test_an_ordinary_relative_target_is_not_mistaken_for_the_repo_root(clean_repo):
    assert _check(_plan(_action(artifact_id="a", target_path="docs/a.md")), clean_repo) is None


# --- rung 6: hand-edited managed content -----------------------------------


def _managed_file(repo: Path, path: str, text: str) -> None:
    (repo / path).write_text(text, encoding="utf-8")


def test_a_managed_file_whose_hash_matches_state_passes(clean_repo):
    _managed_file(clean_repo, "MANAGED.md", "owned by genesis\n")
    _commit_all(clean_repo)
    record = ManagedRecord(artifact_id="managed", path="MANAGED.md", body_sha=hash_content("owned by genesis\n"))

    assert _check(_plan(), clean_repo, managed=(record,)) is None


def test_a_hand_edited_managed_file_is_refused(clean_repo):
    _managed_file(clean_repo, "MANAGED.md", "hand edited\n")
    _commit_all(clean_repo)
    record = ManagedRecord(artifact_id="managed", path="MANAGED.md", body_sha=hash_content("owned by genesis\n"))

    with pytest.raises(PreconditionFailure) as excinfo:
        _check(_plan(), clean_repo, managed=(record,))

    assert excinfo.value.exit_code == 3
    assert "managed-content-modified" in excinfo.value.message
    assert "MANAGED.md" in excinfo.value.message
    assert hash_content("hand edited\n") in excinfo.value.message
    assert hash_content("owned by genesis\n") in excinfo.value.message
    assert excinfo.value.remedy.strip()


def test_a_managed_file_with_no_recorded_hash_is_refused(clean_repo):
    """``recorded_sha=None`` (adopted out-of-band) is a mismatch by
    ``detect.hashes``'s own documented design -- this story reports that
    rule, it does not soften it."""
    _managed_file(clean_repo, "MANAGED.md", "whatever\n")
    _commit_all(clean_repo)
    record = ManagedRecord(artifact_id="managed", path="MANAGED.md", body_sha=None)

    with pytest.raises(PreconditionFailure) as excinfo:
        _check(_plan(), clean_repo, managed=(record,))

    assert "no recorded hash in state" in excinfo.value.message


def test_a_managed_artifact_absent_from_disk_is_not_a_divergence(clean_repo):
    """Nothing was hand-edited -- a deletion is something git already
    records and can already undo, and refusing it would block the ordinary
    re-materialize a seed run exists for."""
    record = ManagedRecord(artifact_id="managed", path="GONE.md", body_sha="deadbeef")

    assert _check(_plan(), clean_repo, managed=(record,)) is None


def test_a_managed_record_pointing_outside_the_repo_is_refused(clean_repo):
    record = ManagedRecord(artifact_id="managed", path="../outside.md", body_sha="deadbeef")

    with pytest.raises(PreconditionFailure) as excinfo:
        _check(_plan(), clean_repo, managed=(record,))

    assert "does not resolve to a location inside the repo root" in excinfo.value.message


def test_a_managed_path_that_cannot_be_read_is_refused(clean_repo):
    """Cannot verify must never be reported as verified -- a directory
    standing where a managed file should be fails closed."""
    (clean_repo / "MANAGED.md").mkdir()
    record = ManagedRecord(artifact_id="managed", path="MANAGED.md", body_sha="deadbeef")

    with pytest.raises(PreconditionFailure, match="cannot be read to verify"):
        _check(_plan(), clean_repo, managed=(record,))


@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    reason="root bypasses the directory permission bit this test depends on",
)
def test_a_managed_file_under_an_unreadable_parent_directory_is_refused(clean_repo):
    """``Path.is_symlink()``/``Path.exists()`` swallow every ``OSError`` and
    answer ``False``, so an unreadable PARENT directory (``EACCES``) made
    this record report as ABSENT -- and absence is the one PASSING answer
    (nothing was hand-edited). A hand-edited file underneath a locked
    directory therefore sailed through rung 6 in silence, reopening exactly
    the SC-04 hole rung 6 exists to close. ``lstat()`` inside a ``try``
    distinguishes "not there" from "cannot tell".

    ``dry_run=True`` because ``git status`` cannot read the locked directory
    either -- it bypasses rung 2 and only rung 2, so rung 6 still runs."""
    parent = clean_repo / "locked"
    parent.mkdir()
    (parent / "MANAGED.md").write_text("hand edited\n", encoding="utf-8")
    _commit_all(clean_repo)
    record = ManagedRecord(
        artifact_id="managed",
        path="locked/MANAGED.md",
        body_sha=hash_content("owned by genesis\n"),
    )

    parent.chmod(0o000)
    try:
        with pytest.raises(PreconditionFailure) as excinfo:
            _check(_plan(), clean_repo, managed=(record,), dry_run=True)

        assert excinfo.value.exit_code == 3
        assert "managed-content-modified" in excinfo.value.message
        assert "cannot be stat'ed to verify" in excinfo.value.message
        assert "locked/MANAGED.md" in excinfo.value.message
        assert excinfo.value.remedy.strip()
    finally:
        # Restored unconditionally: a 0o000 directory left behind would
        # break pytest's own tmp_path teardown for every later test.
        parent.chmod(0o755)


def test_a_managed_path_holding_non_utf8_bytes_is_refused(clean_repo):
    (clean_repo / "MANAGED.md").write_bytes(b"\xff\xfe not utf8\n")
    _commit_all(clean_repo)
    record = ManagedRecord(artifact_id="managed", path="MANAGED.md", body_sha="deadbeef")

    with pytest.raises(PreconditionFailure, match="cannot be read to verify"):
        _check(_plan(), clean_repo, managed=(record,))


def test_a_managed_path_replaced_by_a_dangling_symlink_is_refused(clean_repo):
    """`Path.exists()` follows symlinks, so a dangling link would otherwise
    report as "absent" and pass the absent-is-not-a-divergence carve-out --
    tool-owned content swapped for indirection, reported as nothing having
    happened. That is precisely the SC-04 silent pass rung 6 exists to
    close."""
    (clean_repo / "MANAGED.md").symlink_to("nonexistent-target.md")
    _commit_all(clean_repo)
    record = ManagedRecord(artifact_id="managed", path="MANAGED.md", body_sha=hash_content("genesis\n"))

    with pytest.raises(PreconditionFailure) as excinfo:
        _check(_plan(), clean_repo, managed=(record,))

    assert "is a symlink" in excinfo.value.message
    assert "nonexistent-target.md" in excinfo.value.message


def test_a_managed_path_replaced_by_a_symlink_to_matching_content_is_still_refused(clean_repo):
    """Even when the LINK TARGET holds byte-identical content: a later
    guarded write replaces the link with a regular file rather than writing
    through it, orphaning whatever the human pointed it at."""
    (clean_repo / "elsewhere.md").write_text("genesis\n", encoding="utf-8")
    (clean_repo / "MANAGED.md").symlink_to("elsewhere.md")
    _commit_all(clean_repo)
    record = ManagedRecord(artifact_id="managed", path="MANAGED.md", body_sha=hash_content("genesis\n"))

    with pytest.raises(PreconditionFailure, match="is a symlink"):
        _check(_plan(), clean_repo, managed=(record,))


def test_a_managed_record_with_an_unresolvable_path_is_refused(clean_repo):
    record = ManagedRecord(artifact_id="managed", path="bad\x00path.md", body_sha="deadbeef")

    with pytest.raises(PreconditionFailure) as excinfo:
        _check(_plan(), clean_repo, managed=(record,))

    assert excinfo.value.exit_code == 3
    assert "does not resolve to a location inside the repo root" in excinfo.value.message


def test_hand_edited_managed_content_is_bypassed_by_force(clean_repo):
    _managed_file(clean_repo, "MANAGED.md", "hand edited\n")
    _commit_all(clean_repo)
    record = ManagedRecord(artifact_id="managed", path="MANAGED.md", body_sha="deadbeef")

    assert _check(_plan(), clean_repo, managed=(record,), force=True) is None


def test_hand_edited_managed_content_is_still_refused_under_dry_run(clean_repo):
    """``dry_run`` bypasses rung 2 only -- reading is safe, but reporting a
    hand-edit as absent would still hide exactly what SC-04 exists to
    surface."""
    _managed_file(clean_repo, "MANAGED.md", "hand edited\n")
    _commit_all(clean_repo)
    record = ManagedRecord(artifact_id="managed", path="MANAGED.md", body_sha="deadbeef")

    with pytest.raises(PreconditionFailure, match="managed-content-modified"):
        _check(_plan(), clean_repo, managed=(record,), dry_run=True)


def test_every_divergence_is_reported_in_one_message(clean_repo):
    """A caller fixing them one refusal at a time would need one run per
    hand-edit to learn about them all."""
    _managed_file(clean_repo, "ONE.md", "edited one\n")
    _managed_file(clean_repo, "TWO.md", "edited two\n")
    _managed_file(clean_repo, "HYBRID.md", _hybrid_text("tiers", "hand edited body\n"))
    _commit_all(clean_repo)
    records = (
        ManagedRecord(artifact_id="one", path="ONE.md", body_sha="deadbeef"),
        ManagedRecord(artifact_id="two", path="TWO.md", body_sha="cafef00d"),
        ManagedRecord(
            artifact_id="hybrid",
            path="HYBRID.md",
            region_shas=(("tiers", "12345678"),),
            region_format=RegionFormat.HTML,
        ),
    )

    with pytest.raises(PreconditionFailure) as excinfo:
        _check(_plan(), clean_repo, managed=records)

    assert "3 divergence(s) across 3 managed artifact(s)" in excinfo.value.message
    assert "ONE.md" in excinfo.value.message
    assert "TWO.md" in excinfo.value.message
    assert "HYBRID.md#tiers" in excinfo.value.message


def test_two_diverging_regions_in_one_file_are_counted_as_one_artifact(clean_repo):
    """The divergence count and the ARTIFACT count are different numbers --
    one file with two hand-edited regions is two divergences, not two
    artifacts."""
    _managed_file(clean_repo, "HYBRID.md", _two_region_text())
    _commit_all(clean_repo)
    record = ManagedRecord(
        artifact_id="hybrid",
        path="HYBRID.md",
        region_shas=(("tiers", "11111111"), ("model-badge", "22222222")),
        region_format=RegionFormat.HTML,
    )

    with pytest.raises(PreconditionFailure) as excinfo:
        _check(_plan(), clean_repo, managed=(record,))

    assert "2 divergence(s) across 1 managed artifact(s)" in excinfo.value.message
    assert "HYBRID.md#tiers" in excinfo.value.message
    assert "HYBRID.md#model-badge" in excinfo.value.message


def test_rung_six_checks_records_the_plan_never_mentions(clean_repo):
    """``classify`` marks a present ``copied-managed`` artifact conformant
    whatever its bytes say, so a hand-edited managed FILE never appears in
    the plan at all -- a plan-driven check would silently pass exactly the
    case SC-04 exists to catch."""
    _managed_file(clean_repo, "MANAGED.md", "hand edited\n")
    _commit_all(clean_repo)
    record = ManagedRecord(artifact_id="managed", path="MANAGED.md", body_sha="deadbeef")

    empty_plan = _plan()
    assert empty_plan.actions == ()
    with pytest.raises(PreconditionFailure, match="managed-content-modified"):
        _check(empty_plan, clean_repo, managed=(record,))


# --- rung 6: regions -------------------------------------------------------


def _hybrid_text(name: str, body: str, fmt: RegionFormat = RegionFormat.HTML) -> str:
    return "".join(
        f"{line}\n"
        for line in (
            "intro",
            render_begin(fmt, name, _VERSION, region_sha(body)),
            body.rstrip("\n"),
            render_end(fmt, name),
            "outro",
        )
    )


def _two_region_text(fmt: RegionFormat = RegionFormat.HTML) -> str:
    """One file carrying two managed regions -- the shape that separates
    "how many divergences" from "how many artifacts"."""
    return _hybrid_text("tiers", "first body\n", fmt) + _hybrid_text("model-badge", "second body\n", fmt)


def test_a_managed_region_whose_body_hash_matches_state_passes(clean_repo):
    body = "managed body\n"
    _managed_file(clean_repo, "HYBRID.md", _hybrid_text("tiers", body))
    _commit_all(clean_repo)
    record = ManagedRecord(
        artifact_id="hybrid",
        path="HYBRID.md",
        region_shas=(("tiers", hash_content(body)),),
        region_format=RegionFormat.HTML,
    )

    assert _check(_plan(), clean_repo, managed=(record,)) is None


def test_a_hand_edited_managed_region_is_refused_naming_path_hash_region(clean_repo):
    _managed_file(clean_repo, "HYBRID.md", _hybrid_text("tiers", "hand edited\n"))
    _commit_all(clean_repo)
    record = ManagedRecord(
        artifact_id="hybrid",
        path="HYBRID.md",
        region_shas=(("tiers", hash_content("original\n")),),
        region_format=RegionFormat.HTML,
    )

    with pytest.raises(PreconditionFailure) as excinfo:
        _check(_plan(), clean_repo, managed=(record,))

    assert excinfo.value.exit_code == 3
    assert "HYBRID.md#tiers" in excinfo.value.message
    assert excinfo.value.remedy.strip()


def test_a_recorded_region_missing_from_the_file_is_refused(clean_repo):
    _managed_file(clean_repo, "HYBRID.md", _hybrid_text("tiers", "body\n"))
    _commit_all(clean_repo)
    record = ManagedRecord(
        artifact_id="hybrid",
        path="HYBRID.md",
        region_shas=(("model-badge", "12345678"),),
        region_format=RegionFormat.HTML,
    )

    with pytest.raises(PreconditionFailure) as excinfo:
        _check(_plan(), clean_repo, managed=(record,))

    assert "HYBRID.md#model-badge" in excinfo.value.message
    assert "missing" in excinfo.value.message


def test_a_managed_region_present_in_the_file_but_absent_from_state_is_refused(clean_repo):
    """The third branch of a three-way question the loop over
    ``record.region_shas`` could not ask (review finding): a syntactically
    valid ``marshal-seed`` region hand-INSERTED into a hybrid file, with no
    entry in state, was reported as conformant -- hand-authored content
    passing under the tool's own attestation. That is the region-level twin
    of the whole-file case ``detect.hashes`` explicitly closes by treating
    ``recorded_sha=None`` as a mismatch."""
    _managed_file(clean_repo, "HYBRID.md", _two_region_text())
    _commit_all(clean_repo)
    record = ManagedRecord(
        artifact_id="hybrid",
        path="HYBRID.md",
        region_shas=(("tiers", hash_content("first body\n")),),
        region_format=RegionFormat.HTML,
    )

    with pytest.raises(PreconditionFailure) as excinfo:
        _check(_plan(), clean_repo, managed=(record,))

    assert excinfo.value.exit_code == 3
    assert "HYBRID.md#model-badge" in excinfo.value.message
    assert "never recorded in state" in excinfo.value.message
    assert excinfo.value.remedy.strip()


def test_a_file_whose_regions_all_match_state_still_passes(clean_repo):
    """The non-vacuous other half: the unrecorded-region check must not
    refuse a file whose every managed region IS recorded."""
    _managed_file(clean_repo, "HYBRID.md", _two_region_text())
    _commit_all(clean_repo)
    record = ManagedRecord(
        artifact_id="hybrid",
        path="HYBRID.md",
        region_shas=(
            ("tiers", hash_content("first body\n")),
            ("model-badge", hash_content("second body\n")),
        ),
        region_format=RegionFormat.HTML,
    )

    assert _check(_plan(), clean_repo, managed=(record,)) is None


def test_an_unparseable_region_bearing_file_is_refused(clean_repo):
    """Unparseable markers are themselves an edit to tool-owned structure --
    a file whose regions cannot be located is a file whose regions cannot be
    confirmed intact."""
    fmt = RegionFormat.HTML
    unclosed = f"intro\n{render_begin(fmt, 'tiers', _VERSION, '12345678')}\nbody\n"
    _managed_file(clean_repo, "HYBRID.md", unclosed)
    _commit_all(clean_repo)
    record = ManagedRecord(
        artifact_id="hybrid",
        path="HYBRID.md",
        region_shas=(("tiers", "12345678"),),
        region_format=RegionFormat.HTML,
    )

    with pytest.raises(PreconditionFailure) as excinfo:
        _check(_plan(), clean_repo, managed=(record,))

    assert "cannot be parsed" in excinfo.value.message


def test_a_region_bearing_record_with_an_unimplemented_format_is_refused(clean_repo):
    """``slashstar`` is a registered but unimplemented format -- its
    ``NotImplementedError`` is divergence, never a silent pass."""
    _managed_file(clean_repo, "HYBRID.c", "/* nothing managed here */\n")
    _commit_all(clean_repo)
    record = ManagedRecord(
        artifact_id="hybrid",
        path="HYBRID.c",
        region_shas=(("tiers", "12345678"),),
        region_format=RegionFormat.SLASHSTAR,
    )

    with pytest.raises(PreconditionFailure, match="cannot be parsed"):
        _check(_plan(), clean_repo, managed=(record,))


def test_a_region_bearing_managed_record_requires_a_region_format():
    """Without a marker grammar a region-bearing record could not be parsed
    at all -- and a silently unparsed record would pass rung 6 by doing
    nothing, the exact silent-pass rung 6 exists to close."""
    with pytest.raises(ValueError, match="region_format"):
        ManagedRecord(artifact_id="hybrid", path="HYBRID.md", region_shas=(("tiers", "12345678"),))


def test_a_whole_file_managed_record_needs_no_region_format():
    record = ManagedRecord(artifact_id="managed", path="MANAGED.md", body_sha="deadbeef")
    assert record.region_shas == ()
    assert record.region_format is None


# --- ladder order ----------------------------------------------------------


def test_the_ladder_reports_the_earliest_failing_rung_when_two_fail(tmp_path):
    """A non-git target whose plan also names a never-write path fails rungs
    1 AND 4 -- the message must be the earlier one, deterministically."""
    with pytest.raises(PreconditionFailure, match="not-a-git-repo"):
        _check(
            _plan(_action(artifact_id="dream", target_path="docs/dreams/x.md")),
            tmp_path,
            never_write=NeverWrite(patterns=("docs/dreams/*.md",)),
        )


def test_a_dirty_worktree_is_reported_before_a_never_write_target(clean_repo):
    (clean_repo / "README.md").write_text("edited\n", encoding="utf-8")

    with pytest.raises(PreconditionFailure, match="dirty-worktree"):
        _check(
            _plan(_action(artifact_id="dream", target_path="docs/dreams/x.md")),
            clean_repo,
            never_write=NeverWrite(patterns=("docs/dreams/*.md",)),
        )


def test_a_never_write_target_is_reported_before_a_hand_edited_managed_file(clean_repo):
    _managed_file(clean_repo, "MANAGED.md", "hand edited\n")
    _commit_all(clean_repo)

    with pytest.raises(PreconditionFailure, match="never-write-target"):
        _check(
            _plan(_action(artifact_id="dream", target_path="docs/dreams/x.md")),
            clean_repo,
            never_write=NeverWrite(patterns=("docs/dreams/*.md",)),
            managed=(ManagedRecord(artifact_id="m", path="MANAGED.md", body_sha="deadbeef"),),
        )


def test_containment_is_reported_before_a_symlink_even_on_a_later_sorted_action(clean_repo):
    """The regression this ladder's three-pass shape exists for: with rungs
    3-5 nested inside ONE pass over the actions, the alphabetically-first
    action's rung-5 failure would be reported ahead of a later action's
    rung-3 failure, making the message depend on artifact-id ordering
    rather than on the ladder. Rung 3 must win regardless of which action
    carries it."""
    (clean_repo / "real.md").write_text("real\n", encoding="utf-8")
    (clean_repo / "AGENTS.md").symlink_to("real.md")
    _commit_all(clean_repo)
    plan = _plan(
        _action(artifact_id="aaa-symlink", target_path="AGENTS.md"),
        _action(artifact_id="zzz-escaper", target_path="../outside.md"),
    )

    with pytest.raises(PreconditionFailure) as excinfo:
        _check(plan, clean_repo)

    assert "target-escapes-repo" in excinfo.value.message
    assert "zzz-escaper" in excinfo.value.message


def test_never_write_is_reported_before_a_symlink_on_an_earlier_sorted_action(clean_repo):
    """The same regression at the rung-4/rung-5 boundary."""
    (clean_repo / "real.md").write_text("real\n", encoding="utf-8")
    (clean_repo / "AGENTS.md").symlink_to("real.md")
    _commit_all(clean_repo)
    plan = _plan(
        _action(artifact_id="aaa-symlink", target_path="AGENTS.md"),
        _action(artifact_id="zzz-dream", target_path="docs/dreams/x.md"),
    )

    with pytest.raises(PreconditionFailure) as excinfo:
        _check(plan, clean_repo, never_write=NeverWrite(patterns=("docs/dreams/*.md",)))

    assert "never-write-target" in excinfo.value.message
    assert "zzz-dream" in excinfo.value.message


def test_the_first_of_several_matching_never_write_patterns_is_reported(clean_repo):
    with pytest.raises(PreconditionFailure) as excinfo:
        _check(
            _plan(_action(artifact_id="dream", target_path="docs/dreams/x.md")),
            clean_repo,
            never_write=NeverWrite(patterns=("docs/*", "docs/dreams/*.md", "*")),
        )

    assert "'docs/*'" in excinfo.value.message


def test_a_symlink_target_is_reported_before_a_hand_edited_managed_file(clean_repo):
    (clean_repo / "real.md").write_text("real\n", encoding="utf-8")
    (clean_repo / "AGENTS.md").symlink_to("real.md")
    _managed_file(clean_repo, "MANAGED.md", "hand edited\n")
    _commit_all(clean_repo)

    with pytest.raises(PreconditionFailure, match="symlink-target"):
        _check(
            _plan(_action(artifact_id="agents-md", target_path="AGENTS.md")),
            clean_repo,
            managed=(ManagedRecord(artifact_id="m", path="MANAGED.md", body_sha="deadbeef"),),
        )


# --- all clear -------------------------------------------------------------


def test_a_clean_repo_a_coherent_plan_and_matching_hashes_returns_none(clean_repo):
    _managed_file(clean_repo, "MANAGED.md", "owned\n")
    _commit_all(clean_repo)
    plan = _plan(_action(artifact_id="agents-md", target_path="AGENTS.md"))
    record = ManagedRecord(artifact_id="managed", path="MANAGED.md", body_sha=hash_content("owned\n"))

    assert _check(plan, clean_repo, managed=(record,)) is None


def test_check_preconditions_writes_nothing(clean_repo):
    """Its entire surface is read-and-refuse: a clean run must leave the
    worktree exactly as it found it."""
    before = sorted(path.name for path in clean_repo.iterdir())
    _check(_plan(_action(artifact_id="agents-md", target_path="AGENTS.md")), clean_repo)

    assert sorted(path.name for path in clean_repo.iterdir()) == before
    assert _git(clean_repo, "status", "--porcelain").stdout == ""


def test_check_preconditions_writes_nothing_on_the_refusal_path_that_reads_files(clean_repo):
    """Rung 6 is the only rung that opens a file, so it is the only one that
    could plausibly leave a trace -- proving the REFUSAL path is read-only
    too, not just the clean return."""
    _managed_file(clean_repo, "MANAGED.md", "hand edited\n")
    _commit_all(clean_repo)
    before = sorted(path.name for path in clean_repo.iterdir())
    record = ManagedRecord(artifact_id="managed", path="MANAGED.md", body_sha="deadbeef")

    with pytest.raises(PreconditionFailure):
        _check(_plan(), clean_repo, managed=(record,))

    assert sorted(path.name for path in clean_repo.iterdir()) == before
    assert _git(clean_repo, "status", "--porcelain").stdout == ""


def test_an_empty_plan_still_runs_rungs_one_two_and_six(clean_repo):
    """Rungs 3-5 iterate nothing for an empty plan, but the other three
    still apply -- an empty plan is not a licence to skip the checks."""
    (clean_repo / "README.md").write_text("edited\n", encoding="utf-8")

    with pytest.raises(PreconditionFailure, match="dirty-worktree"):
        _check(_plan(), clean_repo)


def test_skipped_artifacts_are_not_walked_by_the_structural_rungs(clean_repo):
    """A skipped artifact is not going to be written, so nothing about its
    path can make this run unsafe -- a never-write pattern matching only a
    SKIPPED entry must not refuse."""
    plan = apply_skips(
        _plan(_action(artifact_id="dream", target_path="docs/dreams/x.md")),
        ("docs/dreams/*.md",),
    )
    assert plan.actions == ()
    assert len(plan.skipped) == 1

    assert _check(plan, clean_repo, never_write=NeverWrite(patterns=("docs/dreams/*.md",))) is None


# --- the skip <-> rung-6 seam ----------------------------------------------


def test_rung_six_refuses_a_skipped_artifacts_hand_edit_unless_the_caller_filters(clean_repo):
    """Both halves of the contract in one test. Rung 6 checks EVERY record
    it is handed -- it must not second-guess its own input -- so a hand-edit
    on a skipped artifact still refuses when the caller passes the record
    anyway; and the refusal's only offered remedy is ``--force``, which
    would discard every hand-edit including this one. ``managed_after_skips``
    is the affordance that makes ``--skip`` able to protect it instead."""
    _managed_file(clean_repo, "MANAGED.md", "hand edited\n")
    _commit_all(clean_repo)
    record = ManagedRecord(artifact_id="managed", path="MANAGED.md", body_sha="deadbeef")
    plan = apply_skips(
        _plan(_action(artifact_id="managed", target_path="MANAGED.md")),
        ("MANAGED.md",),
    )
    assert [entry.artifact_id for entry in plan.skipped] == ["managed"]

    with pytest.raises(PreconditionFailure, match="managed-content-modified"):
        _check(plan, clean_repo, managed=(record,))

    assert _check(plan, clean_repo, managed=managed_after_skips((record,), plan)) is None


def test_a_skip_pattern_copied_out_of_a_never_write_refusal_actually_skips(clean_repo):
    """Rung 4 reports the RESOLVED repo-relative path, so an operator reads
    ``resolved: 'AGENTS.md'`` out of the refusal and passes it to
    ``--skip``. Skip matching is lexical and saw the raw ``./AGENTS.md``, so
    that copy used to match nothing and the operator got silence (review
    finding)."""
    plan = _plan(_action(artifact_id="agents-md", target_path="./AGENTS.md"))
    never_write = NeverWrite(patterns=("AGENTS.md",))

    with pytest.raises(PreconditionFailure) as excinfo:
        _check(plan, clean_repo, never_write=never_write)
    assert "resolved: 'AGENTS.md'" in excinfo.value.message

    skipped = apply_skips(plan, ("AGENTS.md",))
    assert skipped.actions == ()
    assert _check(skipped, clean_repo, never_write=never_write) is None


# --- documented bounds ------------------------------------------------------


def test_the_module_docstring_states_forces_real_bound():
    """The docstring said ``force`` "says nothing about containment", but
    ``_read_managed_text`` performs the only containment check that ever
    sees a ``ManagedRecord`` path and ``if force: return`` short-circuits
    before it. A stale rationale is a defect in this codebase."""
    # Whitespace-flattened: the claim spans a line break, and this test is
    # about the claim, not about where the paragraph happens to wrap.
    doc = " ".join((preconditions.__doc__ or "").split())

    assert "says nothing about containment" not in doc
    assert "NO rung validates a managed record's path" in doc


def test_force_leaves_a_managed_records_own_path_unchecked(clean_repo):
    """The documented bound, proven rather than asserted. The force
    semantics themselves are fixed by the contract (rung 6 and only rung 6)
    -- this pins what that actually costs, so the docstring cannot drift
    away from it again."""
    record = ManagedRecord(artifact_id="managed", path="../outside.md", body_sha="deadbeef")

    assert _check(_plan(), clean_repo, managed=(record,), force=True) is None


def test_the_plan_named_paths_are_still_fully_checked_under_force(clean_repo):
    """The other half of the same bound: what ``force`` does NOT cost."""
    with pytest.raises(PreconditionFailure, match="target-escapes-repo"):
        _check(
            _plan(_action(artifact_id="escaper", target_path="../outside.md")),
            clean_repo,
            force=True,
        )


def test_the_module_docstring_points_a_caller_at_the_skip_seam():
    doc = preconditions.__doc__ or ""
    assert "managed_after_skips" in doc
    assert "managed_after_skips" in (check_preconditions.__doc__ or "")


# --- _is_dirty / plan.build._repo_is_dirty agreement ------------------------


def test_is_dirty_agrees_with_plan_build_repo_is_dirty_on_a_clean_repo(clean_repo):
    """``plan/build.py`` is modified on an unmerged sibling branch, so its
    ``_repo_is_dirty`` could not be hoisted into a shared home or imported
    from as a private by shipped code. The duplicate is deliberate; this
    test is the guard that keeps the two answering identically."""
    process = PosixProcess()
    assert _is_dirty(process, clean_repo) is _repo_is_dirty(process, clean_repo) is False


def test_is_dirty_agrees_with_plan_build_repo_is_dirty_on_a_dirty_repo(clean_repo):
    (clean_repo / "README.md").write_text("edited\n", encoding="utf-8")
    process = PosixProcess()

    assert _is_dirty(process, clean_repo) is _repo_is_dirty(process, clean_repo) is True


def test_is_dirty_agrees_with_plan_build_repo_is_dirty_on_an_untracked_file(clean_repo):
    (clean_repo / "scratch.txt").write_text("x\n", encoding="utf-8")
    process = PosixProcess()

    assert _is_dirty(process, clean_repo) is _repo_is_dirty(process, clean_repo) is True


def test_is_dirty_agrees_with_plan_build_repo_is_dirty_on_a_non_git_target(tmp_path):
    """Both treat "cannot confirm clean" as dirty -- the conservative
    direction, and the one place a divergence would be silent rather than
    loud."""
    process = PosixProcess()
    assert _is_dirty(process, tmp_path) is _repo_is_dirty(process, tmp_path) is True


def test_the_git_timeout_agrees_with_plan_builds_own():
    """The other half of the same duplication: identical command, identical
    class of call, identical timeout -- and nothing pinned the number, so
    the two could drift apart silently (review finding). Importing the
    private from ``plan/build.py`` is deliberate HERE and only here: the
    shipped module must not import it (that file is modified on an unmerged
    sibling branch), but a test may read it to prove the two agree."""
    assert _GIT_TIMEOUT_S == _BUILD_GIT_TIMEOUT_S
