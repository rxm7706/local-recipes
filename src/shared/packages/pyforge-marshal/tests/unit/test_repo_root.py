"""Story 82.1 (DW-FU-2-1-7): ``cli/config.py::repo_root()`` finds the real repository
under an installed package, and ``gate evaluate`` never passes having run nothing.

``repo_root()`` used to be ``Path(__file__).resolve().parents[8]``: right only for the editable
source layout. Under an installed package (the wheel, sdist or conda artifact the build tasks
produce) ``__file__`` sits in an environment prefix, the index lands inside the prefix, every
policy lookup missed, ``verify_commands`` composed to ``()`` and ``gate evaluate`` reported
``MRS-GATE-004`` (warn, exit 0) having run no gate. The one guard,
``test_conventional_project_policy_path_lands_on_the_repo_root``, can only ever run against the
editable tree -- so these tests build the installed layout by pointing ``config.__file__`` into a
fake environment prefix, beside a real tmp git checkout and a real linked worktree of it.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from pyforge.marshal.cli import config as config_module
from pyforge.marshal.cli.config import RepoRootUnresolvedError, repo_root
from pyforge.marshal.cli.main import main
from pyforge.marshal.core import findings, verdict
from pyforge.marshal.core.model import Verdict

_PROJECT = "acme"
_POLICY_RELPATH = Path("_bmad-output/projects") / _PROJECT / "planning-artifacts" / "marshal-policy.toml"
_MARKER = "only-in-the-main-checkout.txt"

# The spec's own example of a prefix with fewer than nine ancestors: eight parents, so the old
# `parents[8]` raised a bare IndexError. The path need not exist -- `resolve()` is non-strict.
_SHALLOW_PREFIX_FILE = "/usr/lib/python3.13/site-packages/pyforge/marshal/cli/config.py"


def _git(repo: Path, *args: str) -> None:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.fixture(autouse=True)
def _clean_git_env(monkeypatch):
    # A hook or an outer `git` invocation can export these; they would redirect every
    # `git -C <dir>` the adapter makes to somebody else's repository.
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)


@pytest.fixture
def checkout(tmp_path: Path) -> Path:
    """A real git checkout -- the 'main checkout' of the installed-layout tests."""
    repo = tmp_path / "checkout"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "initial")
    return repo


@pytest.fixture
def worktree(checkout: Path, tmp_path: Path) -> Path:
    """A linked worktree of ``checkout`` -- what a story worktree or loop home is."""
    path = tmp_path / "story-worktree"
    _git(checkout, "worktree", "add", "-b", "story", str(path))
    return path


@pytest.fixture
def installed(tmp_path: Path, monkeypatch) -> Path:
    """Point ``config.__file__`` into an environment prefix: no
    ``src/shared/packages/pyforge-marshal/`` anywhere above it. The prefix sits at
    ``tmp_path/env``, so the bare ``parents[8]`` lands on ``tmp_path.parent``."""
    module_file = (
        tmp_path / "env" / "lib" / "python3.14" / "site-packages" / "pyforge" / "marshal" / "cli" / "config.py"
    )
    monkeypatch.setattr(config_module, "__file__", str(module_file))
    return module_file


@pytest.fixture
def outside_any_repo(tmp_path: Path, monkeypatch) -> Path:
    """A cwd with no git repository above it: the ceiling stops git's upward search at
    ``tmp_path`` whatever the runner's temp root is nested in."""
    outside = tmp_path / "outside"
    outside.mkdir()
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    monkeypatch.chdir(outside)
    return outside


def _plant_project(checkout: Path, verify_commands: list[str]) -> None:
    """Untracked in the main checkout, so a linked worktree of it has neither the policy nor the
    marker -- only a root that IS the main checkout can find them."""
    policy = checkout / _POLICY_RELPATH
    policy.parent.mkdir(parents=True)
    rendered = ", ".join(json.dumps(command) for command in verify_commands)
    policy.write_text(f"verify_commands = [{rendered}]\n", encoding="utf-8")
    (checkout / _MARKER).write_text("marker\n", encoding="utf-8")


# --- AC1: installed layout inside a git checkout -> that checkout's git common root --------


def test_installed_layout_returns_the_git_common_root_of_the_invocation_directory(installed, checkout, monkeypatch):
    monkeypatch.chdir(checkout)
    assert repo_root().resolve() == checkout.resolve()


def test_installed_layout_resolves_a_subdirectory_to_the_checkout_root(installed, checkout, monkeypatch):
    nested = checkout / "a" / "b"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)
    assert repo_root().resolve() == checkout.resolve()


def test_installed_layout_resolves_a_linked_worktree_to_the_main_checkout(installed, checkout, worktree, monkeypatch):
    """Every worktree and loop home resolves to the ONE main checkout -- the answer the editable
    install gives today."""
    monkeypatch.chdir(worktree)
    assert repo_root().resolve() == checkout.resolve()
    assert repo_root().resolve() != worktree.resolve()


def test_installed_layout_is_not_cached_across_invocation_directories(installed, checkout, tmp_path, monkeypatch):
    """A cache would pin the first caller's repository."""
    other = tmp_path / "other"
    other.mkdir()
    _git(other, "init", "-b", "main")
    monkeypatch.chdir(checkout)
    first = repo_root().resolve()
    monkeypatch.chdir(other)
    assert repo_root().resolve() == other.resolve()
    assert first == checkout.resolve()


# --- AC2: `gate evaluate` from a worktree runs the project's real verify_commands ----------


@pytest.mark.parametrize(
    ("command", "verdict_name", "exit_code", "returncode"),
    [
        (f"test -f {_MARKER}", "clean", 0, 0),
        (f"test -f missing-{_MARKER}", "gate-failed", 3, 1),
    ],
)
def test_gate_evaluate_under_an_installed_package_runs_the_real_commands_from_the_main_checkout(
    installed, checkout, worktree, monkeypatch, capsys, command, verdict_name, exit_code, returncode
):
    _plant_project(checkout, [command])
    monkeypatch.chdir(worktree)

    rc = main(["gate", "evaluate", "--project", _PROJECT, "--format", "json"])

    payload = json.loads(capsys.readouterr().out)
    assert rc == exit_code
    assert payload["verdict"] == verdict_name
    codes = [finding["code"] for finding in payload["findings"]]
    assert "MRS-GATE-004" not in codes
    assert Path(payload["data"]["root"]).resolve() == checkout.resolve()
    assert Path(payload["data"]["policy_source"]).resolve() == (checkout / _POLICY_RELPATH).resolve()
    (report,) = payload["data"]["commands"]
    # `cwd` was the main checkout: the marker exists nowhere else, the worktree included.
    assert (report["command"], report["returncode"]) == (command, returncode)


# --- AC3: installed layout outside any repository -> one could-not-evaluate finding --------


def test_gate_evaluate_outside_any_repository_is_one_could_not_evaluate_finding(installed, outside_any_repo, capsys):
    rc = main(["gate", "evaluate", "--project", _PROJECT, "--format", "json"])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert rc == verdict.exit_code_for(Verdict.UNEVALUABLE)
    assert rc != 0
    assert payload["verdict"] == "unevaluable"
    assert [finding["code"] for finding in payload["findings"]] == ["MRS-GATE-016"]
    assert payload["data"]["root"] is None
    assert payload["data"]["policy_source"] is None
    assert payload["data"]["commands"] == []
    assert payload["data"]["scope"] == "root-unresolved"
    assert "Traceback" not in captured.err


def test_gate_evaluate_outside_any_repository_text_format_says_unresolved(installed, outside_any_repo, capsys):
    rc = main(["gate", "evaluate", "--project", _PROJECT])

    out = capsys.readouterr().out
    assert rc != 0
    assert "root: (unresolved)" in out
    assert "MRS-GATE-016" in out
    assert "MRS-GATE-004" not in out


def test_gate_evaluate_runs_nothing_when_the_root_is_unresolved(installed, outside_any_repo, monkeypatch, capsys):
    from pyforge.marshal.cli import gate as gate_module

    spawned: list[object] = []

    class _Recorder:
        def run(self, argv, **kwargs):
            spawned.append(argv)
            raise AssertionError("no verify command may run without a resolved root")

    monkeypatch.setattr(gate_module, "PosixProcess", _Recorder)

    assert main(["gate", "evaluate", "--project", _PROJECT, "--format", "json"]) != 0
    assert spawned == []
    capsys.readouterr()


def test_another_consumer_of_an_unresolved_root_exits_unevaluable_without_a_traceback(
    installed, outside_any_repo, capsys
):
    """`main()` never raises: a consumer other than `gate evaluate` (here `marshal config`) is
    relayed as one stderr line carrying the registered code, and the UNEVALUABLE exit."""
    rc = main(["config", "--project", _PROJECT])

    captured = capsys.readouterr()
    assert rc == verdict.exit_code_for(Verdict.UNEVALUABLE)
    assert "MRS-GATE-016" in captured.err
    assert len(captured.err.strip().splitlines()) == 1
    assert "Traceback" not in captured.err


def test_main_survives_a_closed_stderr_when_relaying_an_unresolved_root(installed, outside_any_repo, monkeypatch):
    class _ClosedStderr:
        def write(self, _text):
            raise OSError("stderr closed")

        def flush(self):
            raise OSError("stderr closed")

    monkeypatch.setattr("sys.stderr", _ClosedStderr())

    assert main(["config", "--project", _PROJECT]) == verdict.exit_code_for(Verdict.UNEVALUABLE)


# --- AC4: a prefix with fewer than nine ancestors never raises IndexError -------------------


def test_a_prefix_with_fewer_than_nine_ancestors_resolves_via_git_without_an_index_error(monkeypatch, checkout):
    monkeypatch.setattr(config_module, "__file__", _SHALLOW_PREFIX_FILE)
    assert len(Path(_SHALLOW_PREFIX_FILE).parents) == 8  # the bare index 8 is one past the end
    monkeypatch.chdir(checkout)

    assert repo_root().resolve() == checkout.resolve()


def test_a_prefix_with_fewer_than_nine_ancestors_outside_a_repo_is_the_typed_error(monkeypatch, outside_any_repo):
    monkeypatch.setattr(config_module, "__file__", _SHALLOW_PREFIX_FILE)

    with pytest.raises(RepoRootUnresolvedError) as excinfo:
        repo_root()
    assert not isinstance(excinfo.value, IndexError)
    assert excinfo.value.finding.code == "MRS-GATE-016"


def test_an_unreadable_editable_probe_falls_through_to_the_git_root(tmp_path, checkout, monkeypatch):
    """The `__file__` candidate cannot be probed (an unsearchable ancestor raises `PermissionError`
    from `Path.is_dir()` on older pathlib): it is not the repository, so the git root answers."""
    prefix = tmp_path / "prefix"
    module_file = prefix / "a" / "b" / "c" / "d" / "e" / "f" / "g" / "h" / "config.py"
    monkeypatch.setattr(config_module, "__file__", str(module_file))
    monkeypatch.chdir(checkout)
    real_is_dir = Path.is_dir

    def is_dir(self):
        if self.name == "pyforge-marshal":
            raise PermissionError(13, "Permission denied", str(self))
        return real_is_dir(self)

    monkeypatch.setattr(Path, "is_dir", is_dir)

    assert repo_root().resolve() == checkout.resolve()


def test_a_missing_git_executable_is_the_typed_error_not_a_raw_one(installed, checkout, monkeypatch):
    monkeypatch.chdir(checkout)
    monkeypatch.setenv("PATH", "")

    with pytest.raises(RepoRootUnresolvedError):
        repo_root()


def test_a_deleted_invocation_directory_is_the_typed_error(installed, tmp_path, monkeypatch):
    gone = tmp_path / "gone"
    gone.mkdir()
    monkeypatch.chdir(gone)
    gone.rmdir()

    with pytest.raises(RepoRootUnresolvedError):
        repo_root()


# --- AC5: the editable source layout keeps today's root ------------------------------------


def test_the_editable_layout_returns_the_same_root_as_the_bare_index():
    root = repo_root()

    assert root == Path(config_module.__file__).resolve().parents[8]
    assert (root / "src" / "shared" / "packages" / "pyforge-marshal").is_dir()


def test_the_editable_root_is_not_replaced_by_the_invocation_directory(tmp_path, checkout, monkeypatch):
    """The reason `repo_root()` avoids CWD: `marshal config` runs from loop homes and worktrees, so
    when the `__file__` root IS the repository the invocation directory must not matter."""
    source_root = tmp_path / "source-repo"
    (source_root / "src" / "shared" / "packages" / "pyforge-marshal").mkdir(parents=True)
    module_file = (
        source_root / "src" / "shared" / "packages" / "pyforge-marshal" / "src" / "pyforge" / "marshal" / "cli"
    ) / "config.py"
    monkeypatch.setattr(config_module, "__file__", str(module_file))
    monkeypatch.chdir(checkout)  # a different git repository entirely

    assert repo_root() == source_root.resolve()


def test_a_source_looking_ancestor_without_the_package_tree_is_not_the_repository(tmp_path, checkout, monkeypatch):
    """`parents[8]` exists but carries no `src/shared/packages/pyforge-marshal/`: that is an
    environment prefix, not the repository."""
    prefix = tmp_path / "prefix"
    prefix.mkdir()
    module_file = prefix / "a" / "b" / "c" / "d" / "e" / "f" / "g" / "h" / "config.py"
    monkeypatch.setattr(config_module, "__file__", str(module_file))
    assert Path(module_file).parents[8] == prefix
    monkeypatch.chdir(checkout)

    assert repo_root().resolve() == checkout.resolve()


# --- AC6: mutation -- the bare index misses the same layout -------------------------------


def test_the_bare_parent_index_misses_the_installed_layout(installed, checkout, worktree, monkeypatch):
    """The old body, run against the layout every installed-layout test above uses, lands on
    something that is not the checkout -- so restoring it makes those tests fail."""
    monkeypatch.chdir(worktree)
    bare = Path(config_module.__file__).resolve().parents[8]

    assert bare != checkout.resolve()
    assert not (bare / "src" / "shared" / "packages" / "pyforge-marshal").is_dir()
    assert repo_root().resolve() == checkout.resolve()


def test_gate_evaluate_with_the_bare_index_is_the_false_green_this_story_closes(
    installed, checkout, worktree, monkeypatch, capsys
):
    """What the old `repo_root()` did under this layout, kept as the regression's own witness:
    the project's real policy is missed, nothing runs, and the verdict is MRS-GATE-004 / exit 0."""
    from pyforge.marshal.cli import gate as gate_module

    _plant_project(checkout, [f"test -f missing-{_MARKER}"])
    monkeypatch.chdir(worktree)
    bare_root = Path(config_module.__file__).resolve().parents[8]
    monkeypatch.setattr(config_module, "repo_root", lambda: bare_root)
    monkeypatch.setattr(gate_module, "repo_root", lambda: bare_root)

    rc = main(["gate", "evaluate", "--project", _PROJECT, "--format", "json"])

    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert payload["verdict"] == "warn"
    assert "MRS-GATE-004" in [finding["code"] for finding in payload["findings"]]
    assert payload["data"]["commands"] == []


# --- registry ------------------------------------------------------------------------------


def test_mrs_gate_016_is_registered_once_and_unevaluable():
    import inspect
    import re

    assert "MRS-GATE-016" in findings.REGISTERED_CODES
    assert verdict.classify("MRS-GATE-016") is Verdict.UNEVALUABLE
    assert len(re.findall(r'^\s+"MRS-GATE-016",\s*$', inspect.getsource(findings), re.MULTILINE)) == 1
    assert len(re.findall(r'^\s+"MRS-GATE-016":', inspect.getsource(verdict), re.MULTILINE)) == 1


def test_the_typed_error_is_a_pyforge_error_carrying_its_finding():
    from pyforge.core.errors import PyforgeError

    error = RepoRootUnresolvedError("no repository")

    assert isinstance(error, PyforgeError)
    assert isinstance(error, Exception)
    assert error.finding.code == "MRS-GATE-016"
    assert error.finding.message == "no repository"
