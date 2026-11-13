"""Story 58.2 (spec-pyforge-doctor:CAP-97) -- the live-tree half of ``test_checks_env_hygiene.py``.

Three tests read the repository itself: the real CFE scripts golden fixture (``_http.py`` and its directory), the
discovery walk over the whole checkout, and ``dependency-checker.py``'s guarded returns. Every test that builds its
own tree stays in the package half (``test_checks_env_hygiene.py``).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from pyforge.doctor.checks import env_hygiene
from pyforge.doctor.checks.env_hygiene import CHECK_NAME, SCAN_INCOMPLETE_CHECK_NAME, gather

# Story 117.4 (spec-pyforge-steward:CAP-175): this module reads the live tree outside its package, so it runs in the
# station's live-tree half (pyforge-<station>-live-test) and fires on what it reads, not on every edit of the package.
pytestmark = pytest.mark.live_tree

# The discovery walk asks git which directories it ignores (Story 38.4), so a hook-set GIT_DIR/GIT_WORK_TREE or a
# contributor's own git configuration would change what it calls ignored: the same scrub as
# test_checks_env_hygiene.py's own `_isolate_git_env` (that module's comment names every input it neutralises).
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


def _repo_root() -> Path:
    """Six levels up from tests/unit/<this file> is the repository root -- mirrors pyforge-warden's
    tests/unit/test_currency.py::test_bundled_registry_matches_the_cfe_canonical_source_when_present.
    Computed per call, never at import (the live-tree split guard)."""
    return Path(__file__).resolve().parents[6]


def _cfe_scripts_dir() -> Path:
    return _repo_root() / ".claude" / "skills" / "conda-forge-expert" / "scripts"


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
    # such an injection is covered by the synthetic positive cases in
    # test_checks_env_hygiene.py, which do not depend on another package
    # shipping a real bug -- except
    # for two now-KNOWN, pre-existing findings elsewhere in this same
    # directory that DW-FU-1-4's intermediate-variable fix newly surfaces
    # (see `_KNOWN_PRE_EXISTING` below); everything else in the directory
    # must stay clean.
    http_py_dir = _cfe_scripts_dir()
    # The live half runs only where the tree exists: an absent golden fixture is a failure, never a silent skip.
    assert http_py_dir.is_dir(), f"CFE scripts golden fixture {http_py_dir} is missing from the checkout"

    # An absence assertion cannot tell "scanned real code, found nothing"
    # apart from "scanned nothing at all": `gather()` over an empty directory
    # also returns []. So pin the precondition first -- if `http_py_dir` ever
    # resolves somewhere else, or the walker stops matching these files, this
    # test must red rather than pass vacuously.
    scanned = {p.name for p in http_py_dir.glob("*.py")}
    assert {"_http.py", "inventory_channel.py"} <= scanned, (
        f"golden-fixture directory {http_py_dir} no longer holds the files "
        f"this guard is about -- got {sorted(scanned)[:10]}"
    )

    result = gather(http_py_dir)

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


# --- discovery-walk pruning (Story 6.1) ----------------------------------


def test_discovery_walk_reaches_this_packages_own_source(tmp_path: Path):
    """The regression this pruning exists to prevent.

    Before Story 6.1 the walk spent its whole entry cap inside
    ``build_artifacts/`` -- which sorts before ``docs``/``recipes``/
    ``scripts``/``src`` -- and reached ZERO first-party files: all 609 under
    ``src/`` and ``scripts/`` went unscanned, including this scanner's own
    module. A pass here proves the scan actually covers the repo it claims
    to, so a future prune-list addition cannot silently re-truncate it.
    """
    repo_root = _repo_root()
    # The live half runs only where the tree exists: a checkout without .claude/ is a failure, never a silent skip.
    assert (repo_root / ".claude").is_dir(), f"{repo_root} carries no .claude directory: not the repository checkout"

    files, _incomplete = env_hygiene._discover_python_files(repo_root)
    discovered = set(files)

    assert Path(env_hygiene.__file__).resolve() in discovered
    # ...and nothing from the build-output tree that motivated the prune.
    assert not [f for f in discovered if "build_artifacts" in f.parts]


# --- returned header dicts (DW-FU-1-4) ------------------------------------


def test_gather_real_dependency_checker_auth_headers_stays_clean() -> None:
    # The real file whose returned dicts kept this shape out of v1: its
    # guard clause must suppress them now that returns are checked.
    script = _cfe_scripts_dir() / "dependency-checker.py"
    # The live half runs only where the tree exists: an absent script is a failure, never a silent skip.
    assert script.is_file(), f"{script} is missing from the checkout"

    assert env_hygiene._scan_file(script) == []
