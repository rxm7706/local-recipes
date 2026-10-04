"""Unit tests for ``pyforge.doctor.checks.env_hygiene`` (Story 1.4, FR-3) --
covers the story spec's I/O & Edge-Case Matrix: the direct positive case,
the real ``_http.py`` golden fixture, the host-scoped negative case, the
no-match empty-tuple case, and ``gather_one``'s filter-equivalence. It also
covers the discovery walk's pruning: by directory name (Story 6.1) and of
git-ignored directories (Story 38.4)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from pyforge.doctor.checks import env_hygiene
from pyforge.doctor.checks.env_hygiene import (
    CHECK_NAME,
    SCAN_INCOMPLETE_CHECK_NAME,
    gather,
)
from pyforge.doctor.checks.registry import gather_one
from pyforge.doctor.cli_bridge import CliBridgeError
from pyforge.doctor.models import DoctorStatus, Finding, Source

# Six levels up from tests/unit/<this file> lands at the monorepo root --
# mirrors pyforge-warden's tests/unit/test_currency.py::
# test_bundled_registry_matches_the_cfe_canonical_source_when_present.
_REPO_ROOT = Path(__file__).resolve().parents[6]
_HTTP_PY_DIR = _REPO_ROOT / ".claude" / "skills" / "conda-forge-expert" / "scripts"

# The discovery walk now asks git which directories it ignores (Story 38.4,
# via `cli_bridge.run_git`, which does `env = dict(os.environ)` at call time).
# A hook-set GIT_DIR/GIT_WORK_TREE would retarget that call at the wrong
# repository, and a contributor's own git configuration would change what git
# calls ignored. The fixture below neutralises exactly these inputs: the six
# repository-retargeting variables, the global and system git config
# (GIT_CONFIG_GLOBAL / GIT_CONFIG_NOSYSTEM, so a `core.excludesFile` set there
# is not read), and the default global ignore file
# (`$XDG_CONFIG_HOME/git/ignore`, else `~/.config/git/ignore`), which
# GIT_CONFIG_GLOBAL does NOT stop git reading -- XDG_CONFIG_HOME is pointed at
# the null device so that file is never found. It does not touch the repo's own
# `.git/info/exclude` (a fresh `git init` carries only git's stock template).
# Same autouse-fixture-on-os.environ shape as test_sources_frozen_path.py's own
# `_isolate_git_env`.
_LEAKY_GIT_VARS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_CEILING_DIRECTORIES",
    "GIT_COMMON_DIR",
)


@pytest.fixture(autouse=True)
def _isolate_git_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in _LEAKY_GIT_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("XDG_CONFIG_HOME", os.devnull)


def _write(tmp_path: Path, name: str, source: str) -> None:
    (tmp_path / name).write_text(source, encoding="utf-8")


# --- gather -------------------------------------------------------------


def test_gather_returns_empty_tuple_for_a_file_with_no_matching_pattern(
    tmp_path: Path,
):
    _write(tmp_path, "benign.py", "x = 1\ny = {'a': 1}\n")
    assert gather(tmp_path) == ()


def test_gather_direct_unconditional_injection_returns_one_warn_finding(
    tmp_path: Path,
):
    _write(
        tmp_path,
        "direct.py",
        'import os\n\ndef handler():\n    if os.environ.get("X"):\n        headers["Y"] = os.environ["X"]\n',
    )

    result = gather(tmp_path)

    assert len(result) == 1
    finding = result[0]
    assert isinstance(finding, Finding)
    assert finding.source is Source.ENV_HYGIENE
    assert finding.check == CHECK_NAME
    assert finding.status is DoctorStatus.WARN
    assert finding.evidence["line"] == 5
    assert finding.evidence["var_name"] == "X"
    assert finding.evidence["file"] == str(tmp_path / "direct.py")


def test_gather_host_scoped_guard_suppresses_the_finding(tmp_path: Path):
    _write(
        tmp_path,
        "guarded.py",
        "import os\n"
        "\n"
        "def handler(host):\n"
        '    if host == "internal.example.com":\n'
        '        headers["Authorization"] = os.environ.get("T")\n',
    )

    assert gather(tmp_path) == ()


def test_gather_else_branch_of_a_host_scoped_if_is_still_flagged(
    tmp_path: Path,
):
    # Review finding: the host guard on the TRUE branch must not leak into
    # the else/failed-elif branch, where the test being FALSE is exactly
    # the "not this host" case the check exists to catch.
    _write(
        tmp_path,
        "else_branch.py",
        "import os\n"
        "\n"
        "def handler(host):\n"
        '    if host == "safe.example.com":\n'
        "        pass\n"
        "    else:\n"
        '        headers["Authorization"] = os.environ.get("TOKEN")\n',
    )

    result = gather(tmp_path)

    assert len(result) == 1
    assert result[0].evidence["var_name"] == "TOKEN"
    assert result[0].evidence["line"] == 7


def test_gather_substring_host_token_does_not_falsely_suppress(
    tmp_path: Path,
):
    # Review finding: "ghost_mode" contains the substring "host" but is not
    # a host-scoping guard -- token-exact matching must not treat it as one.
    _write(
        tmp_path,
        "ghost.py",
        "import os\n"
        "\n"
        "def handler(ghost_mode):\n"
        "    if ghost_mode:\n"
        '        headers["Authorization"] = os.environ.get("TOKEN")\n',
    )

    result = gather(tmp_path)

    assert len(result) == 1
    assert result[0].evidence["var_name"] == "TOKEN"


def test_gather_env_var_used_only_as_ternary_condition_is_not_flagged(
    tmp_path: Path,
):
    # Review finding: an env-read that decides BETWEEN two unrelated
    # values (never itself becoming the header value) is not "fed" into
    # the assignment.
    _write(
        tmp_path,
        "ternary_condition.py",
        "import os\n"
        "\n"
        "def handler():\n"
        '    headers["Content-Type"] = (\n'
        '        "application/json" if os.environ.get("DEBUG") else "text/plain"\n'
        "    )\n",
    )

    assert gather(tmp_path) == ()


def test_gather_env_var_as_ternary_value_is_still_flagged(tmp_path: Path):
    # Complement of the above: when the env-read IS one of the ternary's
    # own value branches, it genuinely feeds the header and must be
    # flagged.
    _write(
        tmp_path,
        "ternary_value.py",
        "import os\n"
        "\n"
        "def handler(flag):\n"
        '    headers["Authorization"] = (\n'
        '        os.environ.get("TOKEN") if flag else "default"\n'
        "    )\n",
    )

    result = gather(tmp_path)

    assert len(result) == 1
    assert result[0].evidence["var_name"] == "TOKEN"


def test_gather_aliased_os_import_is_still_detected(tmp_path: Path):
    # Review finding: `import os as o` previously evaded the scanner
    # entirely (hard-coded literal name "os").
    _write(
        tmp_path,
        "aliased_os.py",
        'import os as o\n\ndef handler():\n    if o.environ.get("X"):\n        headers["Y"] = o.environ["X"]\n',
    )

    result = gather(tmp_path)

    assert len(result) == 1
    assert result[0].evidence["var_name"] == "X"


def test_gather_from_os_import_environ_is_still_detected(tmp_path: Path):
    # Review finding: `from os import environ` previously evaded the
    # scanner entirely.
    _write(
        tmp_path,
        "from_import.py",
        'from os import environ\n\ndef handler():\n    if environ.get("X"):\n        headers["Y"] = environ["X"]\n',
    )

    result = gather(tmp_path)

    assert len(result) == 1
    assert result[0].evidence["var_name"] == "X"


def test_gather_aug_assign_credential_injection_is_detected(tmp_path: Path):
    # Review finding: `headers["X"] += ...` (AugAssign) was previously
    # invisible -- only plain Assign was visited.
    _write(
        tmp_path,
        "aug_assign.py",
        "import os\n"
        "\n"
        "def handler():\n"
        '    headers["Authorization"] = ""\n'
        '    headers["Authorization"] += os.environ.get("TOKEN")\n',
    )

    result = gather(tmp_path)

    assert len(result) == 1
    assert result[0].evidence["var_name"] == "TOKEN"
    assert result[0].evidence["line"] == 5


def test_gather_chained_assignment_with_a_header_target_is_detected(
    tmp_path: Path,
):
    # Review finding: `headers["X"] = other["Y"] = env-read` previously
    # required exactly one target.
    _write(
        tmp_path,
        "chained.py",
        'import os\n\ndef handler():\n    other["Y"] = headers["X"] = os.environ.get("TOKEN")\n',
    )

    result = gather(tmp_path)

    assert len(result) == 1
    assert result[0].evidence["var_name"] == "TOKEN"


def test_gather_golden_fixture_finds_no_injection_in_the_real_cfe_scripts():
    # The real CFE scripts -- read-only, never copied into a synthetic string
    # (spec's context-file instruction).
    #
    # This assertion is inverted from its original form, and deliberately so.
    # The fixture was `_http.py`'s live, unconditional `JFROG_API_KEY`
    # injection: the very bug FR-3 was written to catch. The conda-forge-expert
    # Rule-2 retro (Story 5.5, CFE v8.82.x) host-gated that injection and its
    # copy in `inventory_channel.py`, so the detector correctly reports nothing
    # for THOSE TWO FILES -- verified by A/B: scanning the pre-retro revision
    # still yields both findings (`_http.py:215`, `inventory_channel.py:116`),
    # the post-retro tree yields none.
    #
    # Asserting the absence keeps the same property the original had (the
    # detector runs against real, unmodified code rather than a synthetic
    # string) and converts it into a live regression guard that the leak class
    # stays closed for those two files specifically. That the detector FINDS
    # such an injection is covered by the synthetic positive cases above,
    # which do not depend on another package shipping a real bug -- except
    # for two now-KNOWN, pre-existing findings elsewhere in this same
    # directory that DW-FU-1-4's intermediate-variable fix newly surfaces
    # (see `_KNOWN_PRE_EXISTING` below); everything else in the directory
    # must stay clean.
    if not _HTTP_PY_DIR.is_dir():
        pytest.skip("CFE scripts golden fixture not present (non-monorepo context)")

    # An absence assertion cannot tell "scanned real code, found nothing"
    # apart from "scanned nothing at all": `gather()` over an empty directory
    # also returns []. So pin the precondition first -- if `_HTTP_PY_DIR` ever
    # resolves somewhere else, or the walker stops matching these files, this
    # test must red rather than pass vacuously.
    scanned = {p.name for p in _HTTP_PY_DIR.glob("*.py")}
    assert {"_http.py", "inventory_channel.py"} <= scanned, (
        f"golden-fixture directory {_HTTP_PY_DIR} no longer holds the files "
        f"this guard is about -- got {sorted(scanned)[:10]}"
    )

    result = gather(_HTTP_PY_DIR)

    # A scan that bailed out reports it rather than returning a clean []; that
    # state must not read as "no leak found" either.
    incomplete = [f for f in result if f.check == SCAN_INCOMPLETE_CHECK_NAME]
    assert incomplete == [], f"scan did not complete: {incomplete}"

    unconditional = [f for f in result if f.check == CHECK_NAME]
    seen = {(Path(f.evidence["file"]).name, f.evidence["line"], f.evidence["var_name"]) for f in unconditional}

    # DW-FU-1-4 follow-up (2026-09-07): closing the intermediate-variable v1
    # gap (`name = os.environ.get(...); headers[...] = name`) makes this
    # detector correctly see two PRE-EXISTING, previously-invisible
    # host-scoping gaps live in this same scripts directory --
    # `github_version_checker.py`'s `token = os.environ.get("GITHUB_TOKEN")
    # or os.environ.get("GH_TOKEN")` feeding `headers["Authorization"]` with
    # no host check, and `scan_project.py`'s `tok =
    # os.environ.get("OCI_REGISTRY_TOKEN")` feeding `headers["Authorization"]`
    # against a registry host derived from the caller's own image ref -- the
    # SAME leak class `_http.py`'s own fix closed, now correctly surfaced by
    # the more complete detector rather than a regression it introduces.
    # Fixing those two scripts is conda-forge-expert's own surface, not
    # pyforge-doctor's (out of this fix's scope) -- pinned here BY NAME so a
    # THIRD, different finding anywhere else in the directory still reds
    # this test rather than silently passing.
    _KNOWN_PRE_EXISTING = {
        ("github_version_checker.py", 68, "GITHUB_TOKEN"),
        ("scan_project.py", 1898, "OCI_REGISTRY_TOKEN"),
    }
    assert seen <= _KNOWN_PRE_EXISTING, (
        "the real CFE scripts must contain no NEW unconditional credential "
        "injection beyond the known, pre-existing findings -- got "
        f"{seen - _KNOWN_PRE_EXISTING}"
    )
    assert not any(Path(f.evidence["file"]).name in {"_http.py", "inventory_channel.py"} for f in unconditional), (
        "the original golden-fixture files must stay clean"
    )


# --- gather_one filter-equivalence ---------------------------------------


def test_gather_one_env_matches_the_filtered_gather_result(tmp_path: Path):
    _write(
        tmp_path,
        "direct.py",
        'import os\n\ndef handler():\n    if os.environ.get("X"):\n        headers["Y"] = os.environ["X"]\n',
    )

    expected = tuple(f for f in gather(tmp_path) if f.check == CHECK_NAME)

    assert gather_one("env", CHECK_NAME, tmp_path) == expected
    assert len(expected) == 1


def test_gather_one_env_returns_every_matching_file(tmp_path: Path):
    # DW-FU-1-5 (a): a first-match filter surfaced only one of several files
    # matching the same check name.
    for name in ("a.py", "b.py", "c.py"):
        _write(tmp_path, name, 'import os\n\ndef handler():\n    headers["Y"] = os.environ["X"]\n')

    result = gather_one("env", CHECK_NAME, tmp_path)

    assert sorted(Path(f.evidence["file"]).name for f in result) == ["a.py", "b.py", "c.py"]


def test_gather_one_env_returns_empty_for_a_target_with_no_matches(
    tmp_path: Path,
):
    _write(tmp_path, "benign.py", "x = 1\n")

    assert gather_one("env", CHECK_NAME, tmp_path) == ()


# --- discovery-walk pruning (Story 6.1) ----------------------------------


@pytest.mark.parametrize(
    "pruned",
    ["build_artifacts", "build", "dist", ".tox", ".pytest_cache", "site-packages"],
)
def test_discover_python_files_prunes_build_output_and_tool_caches(tmp_path: Path, pruned: str):
    # Story 6.1: the profile attributed 6.43s of `doctor check`'s 7.7s scan
    # to this monorepo's gitignored build_artifacts/ (extracted THIRD-PARTY
    # conda sources), which also exhausted the entry cap before the walk
    # reached any first-party file. These directories are build output, not
    # a project's own scannable source.
    (tmp_path / pruned).mkdir()
    _write(tmp_path, f"{pruned}/vendored.py", "x = 1\n")
    _write(tmp_path, "mine.py", "y = 2\n")

    files, incomplete = env_hygiene._discover_python_files(tmp_path)

    assert [f.name for f in files] == ["mine.py"]
    assert incomplete is False


def test_discovery_walk_reaches_this_packages_own_source(tmp_path: Path):
    """The regression this pruning exists to prevent.

    Before Story 6.1 the walk spent its whole entry cap inside
    ``build_artifacts/`` -- which sorts before ``docs``/``recipes``/
    ``scripts``/``src`` -- and reached ZERO first-party files: all 609 under
    ``src/`` and ``scripts/`` went unscanned, including this scanner's own
    module. A pass here proves the scan actually covers the repo it claims
    to, so a future prune-list addition cannot silently re-truncate it.
    """
    if not (_REPO_ROOT / ".claude").is_dir():
        pytest.skip("not running inside the local-recipes monorepo checkout")

    files, _incomplete = env_hygiene._discover_python_files(_REPO_ROOT)
    discovered = set(files)

    assert Path(env_hygiene.__file__).resolve() in discovered
    # ...and nothing from the build-output tree that motivated the prune.
    assert not [f for f in discovered if "build_artifacts" in f.parts]


# --- discovery-walk incompleteness signal --------------------------------


def test_discover_python_files_onerror_marks_incomplete(monkeypatch, tmp_path: Path):
    # Review finding: an unreadable subdirectory previously vanished from
    # the scan with zero signal (os.walk's default onerror=None silently
    # drops it). Drives the walk through a fake os.walk so this is
    # portable -- real filesystem permission tests are environment-
    # fragile (e.g. root bypasses permissions).
    def _fake_walk(_target, onerror=None, **_kwargs):
        onerror(OSError("simulated permission denied"))
        return iter(())

    monkeypatch.setattr(env_hygiene.os, "walk", _fake_walk)

    files, incomplete = env_hygiene._discover_python_files(tmp_path)

    assert files == []
    assert incomplete is True


def test_discover_python_files_entry_cap_marks_incomplete(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(env_hygiene, "_DISCOVERY_ENTRY_CAP", 2)
    for i in range(5):
        _write(tmp_path, f"f{i}.py", "x = 1\n")

    _files, incomplete = env_hygiene._discover_python_files(tmp_path)

    assert incomplete is True


def test_gather_appends_one_warn_finding_when_scan_is_incomplete(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(env_hygiene, "_DISCOVERY_ENTRY_CAP", 1)
    _write(tmp_path, "a.py", "x = 1\n")
    _write(tmp_path, "b.py", "y = 2\n")

    result = gather(tmp_path)

    incomplete_findings = [f for f in result if "INCOMPLETE" in f.message]
    assert len(incomplete_findings) == 1
    assert incomplete_findings[0].status is DoctorStatus.WARN
    # Review finding: the sentinel's check name is deliberately DISTINCT
    # from CHECK_NAME (and never cataloged), mirroring sources/warden.py's
    # "pyforge-warden" degradation sentinel -- reusing CHECK_NAME let
    # gather_one conflate the incompleteness signal with a real match.
    assert incomplete_findings[0].check == SCAN_INCOMPLETE_CHECK_NAME
    assert incomplete_findings[0].check != CHECK_NAME


def test_gather_no_incomplete_finding_when_scan_completes_normally(
    tmp_path: Path,
):
    _write(tmp_path, "benign.py", "x = 1\n")

    result = gather(tmp_path)

    assert not any("INCOMPLETE" in f.message for f in result)


def test_gather_one_env_can_address_the_incomplete_sentinel_by_name(monkeypatch, tmp_path: Path):
    # Mirrors engines' addressable-sentinel contract: the sentinel's own
    # (never-cataloged) name IS reachable through gather_one's filter,
    # and a real CHECK_NAME finding is returned unshadowed alongside it.
    monkeypatch.setattr(env_hygiene, "_DISCOVERY_ENTRY_CAP", 1)
    _write(
        tmp_path,
        "a_direct.py",
        'import os\n\ndef handler():\n    headers["Y"] = os.environ["X"]\n',
    )
    _write(tmp_path, "b.py", "y = 2\n")

    (sentinel,) = gather_one("env", SCAN_INCOMPLETE_CHECK_NAME, tmp_path)

    assert "INCOMPLETE" in sentinel.message
    # a_direct.py sorts first and is collected before the cap trips, so the
    # real finding coexists with the sentinel. DW-FU-1-5 (b): a named lookup
    # carries the incompleteness signal alongside it, never drops it.
    named = gather_one("env", CHECK_NAME, tmp_path)
    assert [f.check for f in named] == [CHECK_NAME, SCAN_INCOMPLETE_CHECK_NAME]
    assert "INCOMPLETE" not in named[0].message


def test_gather_on_a_single_file_target_warns_not_a_directory(tmp_path: Path):
    # DW-FU-1-5-3: a non-directory target used to return () -- "0 findings",
    # exit 0, a false green. It now says nothing was scanned (and never the
    # misleading "could not read some subdirectory" message os.walk's
    # onerror would produce).
    file_target = tmp_path / "single.py"
    file_target.write_text('import os\nheaders["Y"] = os.environ["X"]\n', encoding="utf-8")

    (finding,) = gather(file_target)

    assert finding.check == SCAN_INCOMPLETE_CHECK_NAME
    assert finding.status is DoctorStatus.WARN
    assert "not a directory" in finding.message
    assert "subdirectory" not in finding.message
    assert finding.evidence == {"target": str(file_target), "reason": "not-a-directory"}


# --- discovery-walk git-ignore pruning (Story 38.4) ----------------------
#
# On the primary checkout the walk spent its whole entry cap inside the
# untracked, gitignored `.cursor/cdao-p15-noarch-build`, `var/scribe-pg` and
# `var/platform-local` and reported INCOMPLETE (DW-OPS-2026-10-01-3). In a git
# work tree the walk now asks git ONCE which directories it ignores and never
# enters them. Every test below drives a REAL throwaway git repository (never a
# mocked git), and uses `scratch_local` -- a name `_PRUNED_DIR_NAMES` does not
# carry -- so only the git-driven prune can explain a directory being skipped.


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)


def _init_repo(repo: Path, *, gitignore: str = "scratch_local/\n") -> Path:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q", "--initial-branch=main")
    (repo / ".gitignore").write_text(gitignore, encoding="utf-8")
    return repo


def _put(root: Path, rel: str, source: str = "x = 1\n") -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def _relative_files(root: Path, files: list[Path]) -> list[str]:
    return sorted(f.relative_to(root).as_posix() for f in files)


def _spy_walk(monkeypatch: pytest.MonkeyPatch) -> list[Path]:
    """Record every directory ``os.walk`` actually yields (the ones the walk
    ENTERS) -- a pruned directory never appears here."""
    real_walk = os.walk
    entered: list[Path] = []

    def _spy(top, **kwargs):
        for dirpath, dirnames, filenames in real_walk(top, **kwargs):
            entered.append(Path(dirpath))
            yield dirpath, dirnames, filenames

    monkeypatch.setattr(env_hygiene.os, "walk", _spy)
    return entered


def test_discover_python_files_does_not_enter_a_git_ignored_directory(monkeypatch, tmp_path: Path):
    repo = _init_repo(tmp_path)
    _put(repo, "mine.py")
    _put(repo, "scratch_local/junk.py")
    _put(repo, "scratch_local/deep/more.py")
    entered = _spy_walk(monkeypatch)

    files, incomplete = env_hygiene._discover_python_files(repo)

    assert _relative_files(repo, files) == ["mine.py"]
    assert incomplete is False
    assert repo / "scratch_local" not in entered
    assert repo / "scratch_local" / "deep" not in entered


def test_git_ignored_dirs_lists_only_ignored_directory_entries(tmp_path: Path):
    repo = _init_repo(tmp_path, gitignore="scratch_local/\n*.log\n")
    _put(repo, "scratch_local/junk.py")
    _put(repo, "noise.log", "not python\n")  # an ignored FILE: never a prune entry
    _put(repo, "fresh_pkg/new.py")  # untracked but NOT ignored: never a prune entry

    assert env_hygiene._git_ignored_dirs(repo) == frozenset({os.path.abspath(repo / "scratch_local")})


def test_the_git_prune_is_what_skips_an_ignored_directory(monkeypatch, tmp_path: Path):
    # Mutation check: with the pruning removed (the git call reporting nothing
    # ignored) the very same tree walks the ignored directory, so the test
    # above fails if and only if the prune is gone.
    repo = _init_repo(tmp_path)
    _put(repo, "mine.py")
    _put(repo, "scratch_local/junk.py")
    monkeypatch.setattr(env_hygiene, "_git_ignored_dirs", lambda _target: frozenset())

    files, _incomplete = env_hygiene._discover_python_files(repo)

    assert _relative_files(repo, files) == ["mine.py", "scratch_local/junk.py"]


def test_discover_python_files_still_scans_a_tracked_file_under_an_ignored_directory(tmp_path: Path):
    # `.cursor/` is gitignored in this repo yet holds tracked files: git omits
    # such a directory from the wholly-ignored listing, so it is walked and the
    # tracked file is scanned. Only its genuinely ignored child directory goes.
    repo = _init_repo(tmp_path, gitignore="vendor/\n")
    _put(repo, "vendor/keep.py")
    _git(repo, "add", "-f", "vendor/keep.py")
    _put(repo, "vendor/junk.py")  # ignored FILE in a mixed directory: directories only are pruned
    _put(repo, "vendor/cache/blob.py")  # wholly ignored child directory

    files, incomplete = env_hygiene._discover_python_files(repo)

    assert _relative_files(repo, files) == ["vendor/junk.py", "vendor/keep.py"]
    assert incomplete is False


def test_discover_python_files_walks_a_plain_directory_as_before(monkeypatch, tmp_path: Path):
    # Not a git work tree: no ceiling above tmp_path may leak a parent repo in.
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))
    _put(tmp_path, ".gitignore", "scratch_local/\n")  # inert: there is no repository to read it
    _put(tmp_path, "mine.py")
    _put(tmp_path, "scratch_local/junk.py")
    _put(tmp_path, "build/vendored.py")  # the by-name prune still applies

    assert env_hygiene._git_ignored_dirs(tmp_path) == frozenset()
    files, incomplete = env_hygiene._discover_python_files(tmp_path)

    assert _relative_files(tmp_path, files) == ["mine.py", "scratch_local/junk.py"]
    assert incomplete is False


def test_discover_python_files_walks_unchanged_when_git_fails(monkeypatch, tmp_path: Path):
    repo = _init_repo(tmp_path)
    _put(repo, "mine.py")
    _put(repo, "scratch_local/junk.py")

    def _git_down(*_args, **_kwargs):
        raise CliBridgeError("git failed to launch")

    monkeypatch.setattr(env_hygiene, "run_git", _git_down)

    files, incomplete = env_hygiene._discover_python_files(repo)

    assert _relative_files(repo, files) == ["mine.py", "scratch_local/junk.py"]
    assert incomplete is False


def test_discover_python_files_walks_unchanged_when_the_target_is_inside_an_ignored_directory(tmp_path: Path):
    # git exits 128 (fatal) when run from inside an ignored directory; the
    # walk then falls back to today's behaviour rather than failing.
    repo = _init_repo(tmp_path)
    _put(repo, "scratch_local/junk.py")
    _put(repo, "scratch_local/deep/more.py")

    files, incomplete = env_hygiene._discover_python_files(repo / "scratch_local")

    assert _relative_files(repo / "scratch_local", files) == ["deep/more.py", "junk.py"]
    assert incomplete is False


def test_discover_python_files_walks_unchanged_when_git_prints_a_non_utf8_path(tmp_path: Path):
    # git prints a path verbatim under `-z`, so an ignored file named
    # `bad\xff.log` makes the listing non-UTF-8. `run_git` raises
    # CliBridgeError for that, `_git_ignored_dirs` returns nothing, and the walk
    # is the unpruned walk it was before Story 38.4 -- never an exception (the
    # old walk tolerated such names; `doctor check --env` once exited 2 on one).
    repo = _init_repo(tmp_path, gitignore="scratch_local/\n*.log\n")
    _put(repo, "mine.py")
    _put(repo, "scratch_local/junk.py")
    try:
        with open(os.path.join(os.fsencode(repo), b"bad\xff.log"), "wb") as handle:
            handle.write(b"x\n")
    except (OSError, UnicodeError) as exc:
        pytest.skip(f"this filesystem refuses a non-UTF-8 file name: {exc!r}")

    files, incomplete = env_hygiene._discover_python_files(repo)

    assert _relative_files(repo, files) == ["mine.py", "scratch_local/junk.py"]
    assert incomplete is False


def test_discover_python_files_prunes_for_a_subdirectory_target(tmp_path: Path):
    # git reports paths relative to its cwd (the target), so a target below
    # the repository root must still line up with the walk's own paths.
    repo = _init_repo(tmp_path)
    _put(repo, "pkg/mine.py")
    _put(repo, "pkg/scratch_local/junk.py")

    files, _incomplete = env_hygiene._discover_python_files(repo / "pkg")

    assert _relative_files(repo / "pkg", files) == ["mine.py"]


def test_discover_python_files_prunes_for_a_relative_target(monkeypatch, tmp_path: Path):
    repo = _init_repo(tmp_path)
    _put(repo, "mine.py")
    _put(repo, "scratch_local/junk.py")
    monkeypatch.chdir(repo)

    files, _incomplete = env_hygiene._discover_python_files(Path("."))

    assert sorted(f.name for f in files) == ["mine.py"]


def test_discovery_asks_git_exactly_once_per_run(monkeypatch, tmp_path: Path):
    repo = _init_repo(tmp_path)
    for rel in ("a/one.py", "a/b/two.py", "a/b/c/three.py", "d/four.py", "scratch_local/junk.py"):
        _put(repo, rel)
    real_run_git = env_hygiene.run_git
    calls: list[list[str]] = []

    def _counting(cwd, args, **kwargs):
        calls.append(list(args))
        return real_run_git(cwd, args, **kwargs)

    monkeypatch.setattr(env_hygiene, "run_git", _counting)

    gather(repo)

    assert len(calls) == 1
    assert calls[0][0] == "ls-files"


def test_discover_python_files_still_reports_incomplete_for_a_tracked_tree_over_the_cap(monkeypatch, tmp_path: Path):
    # The cap and its incomplete report stay for a truly huge TRACKED tree --
    # the prune lifts the cap only from what git ignores, never from source.
    monkeypatch.setattr(env_hygiene, "_DISCOVERY_ENTRY_CAP", 5)
    repo = _init_repo(tmp_path)
    for i in range(8):
        _put(repo, f"src/f{i}.py")
    _git(repo, "add", "-A")

    _files, incomplete = env_hygiene._discover_python_files(repo)

    assert incomplete is True


def test_gather_completes_when_the_only_bulk_is_a_git_ignored_directory(monkeypatch, tmp_path: Path):
    # The primary checkout's shape in miniature: far more ignored entries than
    # the cap, a handful of tracked files. Pruned before counting, the ignored
    # bulk costs no entries, so the scan is COMPLETE -- and a leaky file inside
    # the ignored directory is (correctly) never reported.
    monkeypatch.setattr(env_hygiene, "_DISCOVERY_ENTRY_CAP", 5)
    repo = _init_repo(tmp_path)
    _put(repo, "mine.py")
    _put(repo, "other.py")
    _put(repo, "scratch_local/leak.py", 'import os\nheaders["Y"] = os.environ["X"]\n')
    for i in range(30):
        _put(repo, f"scratch_local/pg/f{i}.py")

    result = gather(repo)

    assert result == ()
    assert not any(f.check == SCAN_INCOMPLETE_CHECK_NAME for f in result)


def test_gather_on_a_nonexistent_target_warns_not_a_directory(tmp_path: Path):
    (finding,) = gather(tmp_path / "does-not-exist")

    assert finding.check == SCAN_INCOMPLETE_CHECK_NAME
    assert "not a directory" in finding.message


# --- degrade-never-crash on pathological-but-parseable input --------------


def test_gather_skips_a_file_whose_ast_blows_the_recursion_limit(
    tmp_path: Path,
):
    # Review finding: a parseable file with a pathologically deep
    # expression tree (e.g. a machine-generated multi-thousand-term
    # concatenation) raised RecursionError out of the visitor walk,
    # crashing the whole doctor run -- the analysis now lives inside the
    # same degrade-never-crash net as parsing.
    deep = "headers['X'] = " + "'a' + " * 5000 + "'a'\n"
    _write(tmp_path, "deep.py", deep)
    _write(
        tmp_path,
        "normal.py",
        'import os\n\ndef handler():\n    headers["Y"] = os.environ["X"]\n',
    )

    result = gather(tmp_path)  # must not raise

    # The pathological file is skipped; the scan still reports the
    # ordinary file's real finding.
    assert [f.evidence["var_name"] for f in result] == ["X"]


# --- guard polarity (negated host tests) ----------------------------------


def test_gather_negated_host_guard_true_branch_is_still_flagged(
    tmp_path: Path,
):
    # Review finding: `if host != safe: headers[...] = env` -- the exact
    # inverse-condition leak -- was suppressed because the test merely
    # REFERENCES a host-like name; a pure-negation test's TRUE branch is
    # the "not this host" case and must not inherit the guard.
    _write(
        tmp_path,
        "negated.py",
        "import os\n"
        "\n"
        "def handler(host):\n"
        '    if host != "internal.example.com":\n'
        '        headers["Authorization"] = os.environ.get("TOKEN")\n',
    )

    result = gather(tmp_path)

    assert len(result) == 1
    assert result[0].evidence["var_name"] == "TOKEN"


def test_gather_negated_host_guard_else_branch_is_suppressed(
    tmp_path: Path,
):
    # Complement: the else branch of `if host != safe:` runs precisely
    # when host == safe -- that assignment IS host-scoped.
    _write(
        tmp_path,
        "negated_else.py",
        "import os\n"
        "\n"
        "def handler(host):\n"
        '    if host != "internal.example.com":\n'
        "        pass\n"
        "    else:\n"
        '        headers["Authorization"] = os.environ.get("TOKEN")\n',
    )

    assert gather(tmp_path) == ()


def test_gather_not_in_host_guard_true_branch_is_still_flagged(
    tmp_path: Path,
):
    _write(
        tmp_path,
        "not_in.py",
        "import os\n"
        "\n"
        "def handler(host, allowed_hosts):\n"
        "    if host not in allowed_hosts:\n"
        '        headers["Authorization"] = os.environ.get("TOKEN")\n',
    )

    result = gather(tmp_path)

    assert len(result) == 1


def test_gather_camel_case_host_guard_suppresses(tmp_path: Path):
    # Review finding: token-splitting on "_" alone missed camelCase host
    # guards like `serverHost`.
    _write(
        tmp_path,
        "camel.py",
        "import os\n"
        "\n"
        "def handler(serverHost):\n"
        '    if serverHost == "internal.example.com":\n'
        '        headers["Authorization"] = os.environ.get("TOKEN")\n',
    )

    assert gather(tmp_path) == ()


def test_gather_elif_host_guard_suppresses(tmp_path: Path):
    # elif branches are nested If nodes in orelse -- the elif's own test
    # must guard its own body (module-docstring contract, previously
    # untested).
    _write(
        tmp_path,
        "elif_guard.py",
        "import os\n"
        "\n"
        "def handler(debug, host):\n"
        "    if debug:\n"
        "        pass\n"
        '    elif host == "internal.example.com":\n'
        '        headers["Authorization"] = os.environ.get("TOKEN")\n',
    )

    assert gather(tmp_path) == ()


def test_gather_outer_function_host_guard_does_not_leak_into_nested_def(
    tmp_path: Path,
):
    # The guard stack resets at function boundaries (module-docstring
    # contract, previously untested): a host guard around a nested `def`
    # does not scope the assignments inside that def.
    _write(
        tmp_path,
        "nested_def.py",
        "import os\n"
        "\n"
        "def outer(host):\n"
        '    if host == "internal.example.com":\n'
        "        def attach():\n"
        '            headers["Authorization"] = os.environ.get("TOKEN")\n'
        "        return attach\n",
    )

    result = gather(tmp_path)

    assert len(result) == 1
    assert result[0].evidence["var_name"] == "TOKEN"


# --- env-read shapes (previously untested or invisible) -------------------


def test_gather_os_getenv_call_is_detected(tmp_path: Path):
    # The os.getenv path existed but had zero coverage (review finding).
    _write(
        tmp_path,
        "getenv.py",
        'import os\n\ndef handler():\n    headers["Authorization"] = os.getenv("TOKEN")\n',
    )

    result = gather(tmp_path)

    assert len(result) == 1
    assert result[0].evidence["var_name"] == "TOKEN"


def test_gather_from_os_import_getenv_is_detected(tmp_path: Path):
    _write(
        tmp_path,
        "from_getenv.py",
        'from os import getenv\n\ndef handler():\n    headers["Authorization"] = getenv("TOKEN")\n',
    )

    result = gather(tmp_path)

    assert len(result) == 1
    assert result[0].evidence["var_name"] == "TOKEN"


def test_gather_star_import_environ_is_detected(tmp_path: Path):
    # Review finding: `from os import *` binds environ/getenv under their
    # own names and previously evaded the scanner entirely.
    _write(
        tmp_path,
        "star.py",
        'from os import *\n\ndef handler():\n    headers["Authorization"] = environ["TOKEN"]\n',
    )

    result = gather(tmp_path)

    assert len(result) == 1
    assert result[0].evidence["var_name"] == "TOKEN"


def test_gather_ann_assign_credential_injection_is_detected(tmp_path: Path):
    # Review finding: `headers["X"]: str = env-read` (AnnAssign) is legal
    # Python and was previously invisible.
    _write(
        tmp_path,
        "ann_assign.py",
        'import os\n\ndef handler():\n    headers["Authorization"]: str = os.environ.get("TOKEN")\n',
    )

    result = gather(tmp_path)

    assert len(result) == 1
    assert result[0].evidence["var_name"] == "TOKEN"


def test_gather_tuple_unpacking_header_target_is_detected(tmp_path: Path):
    # Review finding: `headers["A"], x = env-read, 1` was invisible --
    # only top-level targets were inspected.
    _write(
        tmp_path,
        "tuple_target.py",
        'import os\n\ndef handler():\n    headers["Authorization"], x = os.environ.get("TOKEN"), 1\n',
    )

    result = gather(tmp_path)

    assert len(result) == 1
    assert result[0].evidence["var_name"] == "TOKEN"


def test_gather_tuple_unpacking_pairs_positionally_no_false_positive(
    tmp_path: Path,
):
    # The positional complement: the env-read feeds x, not the header
    # element, so no finding.
    _write(
        tmp_path,
        "tuple_positional.py",
        'import os\n\ndef handler():\n    headers["Content-Type"], x = "text/plain", os.environ.get("D")\n',
    )

    assert gather(tmp_path) == ()


def test_gather_walrus_in_ternary_test_is_still_detected(tmp_path: Path):
    # Review finding: a walrus inside the (otherwise skipped) ternary test
    # BINDS the env value into the returned branch -- value-carrying.
    _write(
        tmp_path,
        "walrus.py",
        "import os\n"
        "\n"
        "def handler():\n"
        '    headers["Authorization"] = (\n'
        '        t if (t := os.environ.get("TOKEN")) else "default"\n'
        "    )\n",
    )

    result = gather(tmp_path)

    assert len(result) == 1
    assert result[0].evidence["var_name"] == "TOKEN"


def test_gather_env_read_in_comprehension_filter_is_not_flagged(
    tmp_path: Path,
):
    # Review finding: a comprehension's `if` filter decides WHICH values
    # are included -- same non-value-carrying rationale as a ternary's
    # test (previously a false positive with a misleading message).
    _write(
        tmp_path,
        "comp_filter.py",
        "import os\n"
        "\n"
        "def handler(values):\n"
        '    headers["Accept"] = ",".join(\n'
        '        v for v in values if os.environ.get("DEBUG")\n'
        "    )\n",
    )

    assert gather(tmp_path) == ()


def test_gather_env_read_in_comprehension_iter_is_still_flagged(
    tmp_path: Path,
):
    # Complement: the iterated source genuinely feeds the produced values.
    _write(
        tmp_path,
        "comp_iter.py",
        "import os\n"
        "\n"
        "def handler():\n"
        '    headers["Accept"] = ",".join(\n'
        '        c for c in os.environ.get("ACCEPT", "")\n'
        "    )\n",
    )

    result = gather(tmp_path)

    assert len(result) == 1
    assert result[0].evidence["var_name"] == "ACCEPT"


# --- DW-FU-1-4 follow-up: intermediate-variable / dict-literal tracking ---


def test_gather_intermediate_variable_credential_injection_is_detected(
    tmp_path: Path,
):
    # DW-FU-1-4's own reported miss, reproduced verbatim: `token =
    # os.environ.get(...)` then `headers["X"] = token` was invisible under
    # the v1 direct-expression-only boundary (real repo shape: this exact
    # pattern in `scan_project.py`'s `tok = os.environ.get(...)` feeding
    # `headers["Authorization"]`).
    _write(
        tmp_path,
        "intermediate_var.py",
        'import os\n\ndef handler():\n    token = os.environ.get("X")\n    headers["Authorization"] = token\n',
    )

    result = gather(tmp_path)

    assert len(result) == 1
    assert result[0].evidence["var_name"] == "X"
    assert result[0].evidence["line"] == 5


def test_gather_intermediate_variable_reassigned_to_non_credential_not_flagged(
    tmp_path: Path,
):
    # A tracked var later reassigned to something that is NOT
    # credential-bearing must stop being treated as one (best-effort, not
    # full dataflow -- see `_track_credential_var`'s docstring).
    _write(
        tmp_path,
        "reassigned.py",
        "import os\n"
        "\n"
        "def handler():\n"
        '    token = os.environ.get("X")\n'
        '    token = "static-default"\n'
        '    headers["Authorization"] = token\n',
    )

    assert gather(tmp_path) == ()


def test_gather_intermediate_variable_still_respects_host_guard(
    tmp_path: Path,
):
    # The intermediate-variable extension must still honor the existing
    # enclosing host-scope guard model, not bypass it.
    _write(
        tmp_path,
        "guarded_intermediate.py",
        "import os\n"
        "\n"
        "def handler(host):\n"
        '    token = os.environ.get("X")\n'
        '    if host == "internal.example.com":\n'
        '        headers["Authorization"] = token\n',
    )

    assert gather(tmp_path) == ()


def test_gather_dict_literal_assigned_to_header_name_is_detected(
    tmp_path: Path,
):
    # DW-FU-1-4's other reported miss, reproduced verbatim: a dict LITERAL
    # assigned to a bare header-shaped name (real repo shape:
    # `gemini_server.py`'s `headers = {"x-goog-api-key": ...}`) was
    # invisible -- only a `headers[...]` Subscript target was recognized.
    _write(
        tmp_path,
        "dict_literal.py",
        'import os\n\ndef handler():\n    headers = {"x-goog-api-key": os.environ.get("KEY")}\n',
    )

    result = gather(tmp_path)

    assert len(result) == 1
    assert result[0].evidence["var_name"] == "KEY"
    assert result[0].evidence["line"] == 4


def test_gather_dict_literal_with_intermediate_variable_is_detected(
    tmp_path: Path,
):
    # The two DW-FU-1-4 gaps compose: an intermediate variable embedded in
    # a dict literal assigned to a bare header-shaped name.
    _write(
        tmp_path,
        "dict_literal_var.py",
        'import os\n\ndef handler():\n    key = os.environ.get("KEY")\n    headers = {"x-goog-api-key": key}\n',
    )

    result = gather(tmp_path)

    assert len(result) == 1
    assert result[0].evidence["var_name"] == "KEY"


def test_gather_dict_literal_assigned_to_non_header_name_not_flagged(
    tmp_path: Path,
):
    # The dict-literal widening is scoped to a header-shaped bare NAME
    # target -- an unrelated name assigned a dict literal must not match.
    _write(
        tmp_path,
        "unrelated_dict.py",
        'import os\n\ndef handler():\n    config = {"key": os.environ.get("KEY")}\n',
    )

    assert gather(tmp_path) == ()


def test_gather_dict_literal_host_guard_still_suppresses(tmp_path: Path):
    _write(
        tmp_path,
        "guarded_dict_literal.py",
        "import os\n"
        "\n"
        "def handler(host):\n"
        '    if host == "internal.example.com":\n'
        '        headers = {"Authorization": os.environ.get("TOKEN")}\n',
    )

    assert gather(tmp_path) == ()
