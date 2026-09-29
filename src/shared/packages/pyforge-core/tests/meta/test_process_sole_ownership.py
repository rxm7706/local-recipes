"""Meta test -- the subprocess sole-ownership guard (Story 14.4,
SPEC-pyforge-core CAP-6/CAP-7).

Generalizes Doctor's own hardened ``_subprocess_violations`` AST detector
(``pyforge-doctor/tests/meta/test_cli_bridge_sole_subprocess.py``) from a
single-station, single-file-exemption scan to a FLEET-WIDE one: every
sibling station's ``src/pyforge`` tree (``sibling_station_dirs``/
``station_source_files``, the ``tests/meta/conftest.py`` convention from
14.2/14.3), minus a combined station-level + file-level exclusion set.

**Narrower than Doctor's detector in one deliberate way.** Doctor's
``cli_bridge.py`` is the ONLY module in its scanned package permitted to
touch ``subprocess`` for ANY reason, so its detector bans even a bare
``subprocess.TimeoutExpired`` TYPE reference. This guard's scan surface is
wider and includes a real, sanctioned case a blanket ban would break:
Marshal's ``adapters/vcs_git.py::_run`` (Story 1.4) delegates its actual
process launch to ``pyforge.core.process.PosixProcess().run(...)`` but keeps
``import subprocess`` for exactly one line -- ``add_worktree``'s
``isinstance(exc.__cause__, subprocess.TimeoutExpired)`` cleanup-guidance
branch (this story's own I/O matrix: "vcs_git.py's existing ... branch still
fires"). A blanket "any ``subprocess.*`` attribute access" ban would flag
that legitimate type reference as a second implementation. This detector
therefore flags the actual INVOCATION surface only -- a call (attribute or
bare-name, however imported/aliased) to ``subprocess.run``/``Popen``/
``call``/``check_call``/``check_output``, or the ``os.system``/``os.popen``/
spawn/exec/``posix_spawn`` family (which has no analogous legitimate
type-only reference, so it keeps Doctor's original "the import itself is
already a violation" strictness) -- never a bare ``subprocess.TimeoutExpired``
or other non-invocation attribute.

**Exclusion set, discovered by running this detector fleet-wide before
finalizing it (mirrors CAP-3's own ``_OUT_OF_SCOPE_STATIONS`` precedent,
Story 14.3, ``test_exception_root_sole_ownership.py``).** This story's own
Boundaries roster names three stations for a documented station-level
exclusion -- Doctor (``cli_bridge.py``, its own already-working sole-site
guard), Warden (``engines.py``, the fleet's own confirmed-conforming single
seam), Steward (``deploy.py``/``provision.py``/``keys.py``, CAP-6's
sanctioned raw-``CalledProcessError`` opt-out, pinned by 11 tests) -- plus
five file-level exclusions, each carrying its own inline comment naming
the capability gap: Marshal's ``adapters/harness_bmadloop.py`` (4 sanctioned
call sites -- interactive stdio passthrough, append-mode log),
``adapters/harness_bmadbuild.py`` (its one remaining raw site, a DETACHED
launch needing both a per-invocation custom env and file-redirected
stdout -- neither ``PosixProcess.run`` nor ``spawn_detached`` offers both
together; the file's OTHER, cleanly-migratable site,
``_authcheck_failure``, was migrated rather than folded into this
exemption), ``adapters/skill_invoke_harness.py`` (the identical
custom-env + file-redirect gap, synchronous rather than detached),
``cli/dispatch.py`` (one ``os.execvp`` call that REPLACES the process's own
image for ``marshal attach`` -- no ``ProcessPort`` method launches a child
AND replaces the caller, so there is no analog, not merely a missing
option), and Atlas's ``query_plane_boot.py`` (its one sanctioned
``duckdb-server`` launch site, needing the live ``Popen`` handle's
terminate/wait/kill lifecycle no ``ProcessPort`` method offers -- see the
Atlas paragraph below). Running
the detector's real-tree scan against every OTHER
sibling station before shipping this guard surfaced three more real,
pre-existing, un-migrated ``subprocess`` implementations this story's
Boundaries never named and does not touch: Herald's
``transport/agent_sdk_transport.py`` + ``deck_pipeline.py``, Mason's
``cfe.py`` + ``engines/__init__.py`` (governed by Mason's own narrower AD-3
CFE-caller guard, ``test_adapter_sole_caller.py`` -- which polices CFE-path
references, not general subprocess ownership, so it does not gate these call
sites either), and Scribe's ``compile.py``. None of the three is named
anywhere in CAP-6's success text (which names only Marshal for mandatory
migration) or this story's Boundaries -- exactly the same shape CAP-3's own
exclusion precedent describes ("every hit outside these two stations
corresponds exactly, 1:1, to a class in the Boundaries roster"). Excluded
here for the identical reason, each documented individually below, rather
than either shipping a guard that reds on day one over pre-existing code
this story never asked to touch, or silently narrowing the scan without a
record. A future story extending CAP-6 to any of the three removes its entry
from this set in the same change that migrates it.

Atlas is deliberately NOT excluded at the STATION level: its own ``tests/
catalog/test_no_inline_io.py`` (the A2 no-inline-IO denylist) already
independently bans every ``subprocess``/HTTP import package-wide, and every
file but one scans clean here, serving as this guard's real-tree
positive-coverage proof, the same role ``fs_local.py``'s clean scan plays
for the atomic-write guard. The one exception, ``query_plane_boot.py``, gets
its own file-level exemption below (fifth entry in ``_EXEMPT_RELATIVE_PATHS``):
atlas's OWN ``NO_INLINE_IO_EXEMPT`` already sanctions it as "the ONE
``duckdb-server`` launch site in the atlas surface" (governed by its own
``tests/singularity/test_one_duckdb_server_launch_site.py``), and its
``_shutdown`` helper needs the live ``Popen`` handle's
terminate/wait(timeout)/kill/wait sequence -- a capability neither
``PosixProcess.run`` (blocks to completion) nor ``spawn_detached`` (returns
a bare pid, no handle at all) offers.

The sixth file-level exemption (Story 52.1, CAP-6's "recorded as a
sanctioned, tested opt-out") is the testing-kit's ``branch_diff_guard.py``,
and its capability gap is the PACKAGE, not a missing ``ProcessPort`` option:
Q-26 (decided 2026-08-23, ``spec-19-2-the-shared-test-support-kit``'s Spec
Change Log) ships ``pyforge-testing-kit`` as its own stdlib leaf --
``pyproject.toml`` ``dependencies = []``, ``[package.run-dependencies]``
python only, "never a package run-dep" -- so every public function of that
file routing through ``pyforge.core.process`` would give the BUILT kit an
undeclared runtime dependency and it would cease to be the leaf Q-26 made
it; ``spec-pyforge-core``'s own Non-goals exclude the kit ("Not
``pyforge-testing-kit``") until its open Q2 decides whether the two are one
package; and ``tests/packaging/test_dependency_completeness.py`` skips the
``pyforge`` namespace entirely, so nothing else would catch a stray import.
The exemption is pinned to that premise below
(``test_branch_diff_guard_exemption_rests_on_the_kits_leaf_declaration``): it
self-retires the day the leaf declaration changes.

Scans SOURCE trees (reads files from disk), not installed packages -- same
convention as every other ``pyforge-core`` meta test.
"""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

import pytest
from conftest import PACKAGES_ROOT, parse_module, station_source_files

_parse = parse_module

_SUBPROCESS_INVOKE_METHODS = frozenset({"run", "Popen", "call", "check_call", "check_output"})

# Deliberately excluded (see module docstring): Doctor/Warden/Steward per
# this story's own Boundaries roster; Herald/Mason/Scribe discovered by
# running this detector fleet-wide before finalizing it -- real,
# pre-existing subprocess implementations this story's Boundaries never
# named and does not touch.
_OUT_OF_SCOPE_STATIONS = frozenset(
    {
        "pyforge-doctor",
        "pyforge-warden",
        "pyforge-steward",
        "pyforge-herald",
        "pyforge-mason",
        "pyforge-scribe",
    }
)

# Marshal's own sanctioned exceptions (this story's Always bullet):
# harness_bmadloop.py's 4 call sites (`attach`/`run_foreground`/`resume`'s
# Popen/`run_smoke`) each need a capability `pyforge.core.process` does not
# offer (interactive stdio passthrough, append-mode log). harness_bmadbuild.py
# and skill_invoke_harness.py each keep one raw site needing a per-invocation
# custom env (`BMAD_ACTIVE_PROJECT`) COMBINED WITH file-redirected stdout --
# `PosixProcess.run` never accepts an `env=` override (always inherits
# `os.environ` exactly, by design) and captures to strings, never a file;
# `spawn_detached` redirects to a file but likewise offers no `env=`
# override. Mutating process-global `os.environ` as a workaround would race
# a concurrent dispatch for a different project -- the class of bug the
# "never scripts/bmad-switch" convention exists to avoid. cli/dispatch.py's
# `marshal attach` keeps its one `os.execvp` call: it REPLACES this
# process's own image with `tail -F` so the user's terminal follows the
# live dispatch log directly -- `ProcessPort` launches and either waits or
# detaches a CHILD, never replaces the caller's own process, so there is no
# analog at all, not merely a missing option. Atlas's `query_plane_boot.py`
# keeps its one `subprocess.Popen`: see the module docstring above for its
# separate, live-handle-lifecycle reason. Mirrors Doctor's
# own `_EXEMPT_RELATIVE_PATHS` pattern, one level deeper (relative to
# PACKAGES_ROOT, not a single package's own root, since this guard's scan
# surface spans stations).
#
# Bounded (stated, not aspirational, matching test_leaf_constraint.py's own
# convention): each exemption is FILE-level, not scoped to its named call
# site(s) individually -- an unsanctioned `subprocess.*` call added anywhere
# else in one of these files would also go undetected. Matches Doctor's own
# `_EXEMPT_RELATIVE_PATHS` precedent, which has the identical file-level
# (not line-level) granularity.
_EXEMPT_RELATIVE_PATHS = frozenset(
    {
        Path("pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py"),
        Path("pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadbuild.py"),
        Path("pyforge-marshal/src/pyforge/marshal/adapters/skill_invoke_harness.py"),
        Path("pyforge-marshal/src/pyforge/marshal/cli/dispatch.py"),
        Path("pyforge-atlas/src/pyforge/atlas/query_plane_boot.py"),
        # Story 52.1 (CAP-6 sanctioned opt-out). Q-26 (2026-08-23) declares
        # `pyforge-testing-kit` a stdlib leaf: `pyproject.toml`
        # `dependencies = []`, `[package.run-dependencies]` python only,
        # "never a package run-dep". Routing this file's nine `git` calls
        # through `pyforge.core.process` would give the BUILT kit an
        # undeclared runtime dependency -- it cannot import
        # `pyforge.core.process` without ceasing to be that leaf.
        # `spec-pyforge-core`'s Non-goals exclude the kit until its open Q2
        # decides whether the two are one package, and
        # `tests/packaging/test_dependency_completeness.py` skips the
        # `pyforge` namespace, so nothing else would catch a stray import.
        # Pinned to its premise by
        # `test_branch_diff_guard_exemption_rests_on_the_kits_leaf_declaration`.
        Path("pyforge-testing-kit/src/pyforge/testing_kit/branch_diff_guard.py"),
    }
)


def _is_os_shell_out_name(name: str) -> bool:
    return name in ("system", "popen") or name.startswith(("spawn", "exec", "posix_spawn"))


def _scannable_files() -> list[Path]:
    return [
        path
        for path in station_source_files(exclude=_OUT_OF_SCOPE_STATIONS)
        if path.relative_to(PACKAGES_ROOT) not in _EXEMPT_RELATIVE_PATHS
    ]


def _subprocess_module_aliases(tree: ast.Module) -> frozenset[str]:
    """Local names bound to the ``subprocess`` module itself: ``import
    subprocess`` -> ``{"subprocess"}``, ``import subprocess as sp`` -> adds
    ``"sp"``."""
    names = {"subprocess"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "subprocess" and alias.asname:
                    names.add(alias.asname)
    return frozenset(names)


def _subprocess_bare_invoke_names(tree: ast.Module) -> frozenset[str]:
    """Local names bound to a subprocess INVOCATION entry point via ``from
    subprocess import run [as x]``/``Popen [as x]``/etc. -- a bare-name call
    site that never spells ``subprocess.`` at the call at all. Deliberately
    scoped to ``_SUBPROCESS_INVOKE_METHODS`` only: ``from subprocess import
    TimeoutExpired`` is a legitimate type-only import (see module docstring)
    and is never collected here."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "subprocess":
            for alias in node.names:
                if alias.name in _SUBPROCESS_INVOKE_METHODS:
                    names.add(alias.asname or alias.name)
    return frozenset(names)


def _os_aliases(tree: ast.Module) -> frozenset[str]:
    names = {"os"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "os" and alias.asname:
                    names.add(alias.asname)
    return frozenset(names)


def _os_bare_shell_out_names(tree: ast.Module) -> frozenset[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "os":
            for alias in node.names:
                if _is_os_shell_out_name(alias.name):
                    names.add(alias.asname or alias.name)
    return frozenset(names)


def _subprocess_violations(tree: ast.Module) -> list[int]:
    subprocess_names = _subprocess_module_aliases(tree)
    subprocess_bare = _subprocess_bare_invoke_names(tree)
    os_names = _os_aliases(tree)
    os_bare = _os_bare_shell_out_names(tree)

    violations: set[int] = set()

    # `from os import system [as x]` etc.: the IMPORT itself is already a
    # violation -- unlike subprocess's invocation methods, no legitimate
    # type-only import of an os shell-out NAME exists (there is no
    # `os.system`-the-exception-type to reference).
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "os":
            for alias in node.names:
                if _is_os_shell_out_name(alias.name):
                    violations.add(node.lineno)

    # `subprocess.run(...)`/`.Popen(...)`/... and `os.system(...)`/`.popen(...)`/
    # spawn*/exec*/posix_spawn* -- any attribute ACCESS naming one of these
    # (called or merely referenced), never a bare `subprocess.TimeoutExpired`
    # or other non-invocation attribute.
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)):
            continue
        if (node.value.id in subprocess_names and node.attr in _SUBPROCESS_INVOKE_METHODS) or (
            node.value.id in os_names and _is_os_shell_out_name(node.attr)
        ):
            violations.add(node.lineno)

    # Bare-name CALLS bound via `from subprocess import run [as x]` / `from
    # os import system [as x]` -- a call site that never spells the owning
    # module at the call at all.
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and (node.func.id in subprocess_bare or node.func.id in os_bare)
        ):
            violations.add(node.lineno)

    return sorted(violations)


def test_scan_surface_is_not_empty():
    files = _scannable_files()
    assert files, "subprocess sole-ownership guard found no sibling station source files to scan"


def test_harness_bmadloop_is_excluded_from_the_scan():
    excluded = PACKAGES_ROOT / "pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py"
    assert excluded.is_file(), f"expected {excluded} to exist"
    assert excluded not in _scannable_files()


def test_harness_bmadbuild_is_excluded_from_the_scan():
    excluded = PACKAGES_ROOT / "pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadbuild.py"
    assert excluded.is_file(), f"expected {excluded} to exist"
    assert excluded not in _scannable_files()


def test_skill_invoke_harness_is_excluded_from_the_scan():
    excluded = PACKAGES_ROOT / "pyforge-marshal/src/pyforge/marshal/adapters/skill_invoke_harness.py"
    assert excluded.is_file(), f"expected {excluded} to exist"
    assert excluded not in _scannable_files()


def test_cli_dispatch_is_excluded_from_the_scan():
    excluded = PACKAGES_ROOT / "pyforge-marshal/src/pyforge/marshal/cli/dispatch.py"
    assert excluded.is_file(), f"expected {excluded} to exist"
    assert excluded not in _scannable_files()


def test_query_plane_boot_is_excluded_from_the_scan():
    excluded = PACKAGES_ROOT / "pyforge-atlas/src/pyforge/atlas/query_plane_boot.py"
    assert excluded.is_file(), f"expected {excluded} to exist"
    assert excluded not in _scannable_files()


_BRANCH_DIFF_GUARD = Path("pyforge-testing-kit/src/pyforge/testing_kit/branch_diff_guard.py")


def test_branch_diff_guard_is_excluded_from_the_scan():
    excluded = PACKAGES_ROOT / _BRANCH_DIFF_GUARD
    assert excluded.is_file(), f"expected {excluded} to exist"
    assert excluded not in _scannable_files()


def test_branch_diff_guard_would_fire_if_it_were_not_excluded():
    """Non-vacuous proof the Story 52.1 file-level exemption is doing real
    work (the same shape as the Doctor/Herald station-level proofs below):
    ``branch_diff_guard.py`` really does invoke ``subprocess`` -- exactly
    nine ``run``/``check_output`` git call sites -- so without its entry in
    ``_EXEMPT_RELATIVE_PATHS`` this file would be a real violation, not an
    accidentally-unused permission. The count is pinned so a tenth raw site
    (or a partial migration) is a visible change, not a silent one."""
    guard_path = PACKAGES_ROOT / _BRANCH_DIFF_GUARD
    assert guard_path.is_file(), f"expected {guard_path} to exist"
    assert len(_subprocess_violations(_parse(guard_path))) == 9


def test_branch_diff_guard_exemption_rests_on_the_kits_leaf_declaration():
    """PREMISE pin: the exemption exists ONLY because Q-26 declares
    ``pyforge-testing-kit`` a stdlib leaf (``[project] dependencies = []``).
    The day that declaration changes -- the kit grows a ``pyforge-core``
    dependency, or Q2 folds it into this package -- this test reds, and the
    right move is to migrate ``branch_diff_guard.py``'s git calls onto
    ``PosixProcess.run`` and delete the exemption in the same change, not to
    loosen this pin."""
    pyproject = PACKAGES_ROOT / "pyforge-testing-kit" / "pyproject.toml"
    assert pyproject.is_file(), f"expected {pyproject} to exist"
    with pyproject.open("rb") as handle:
        declared = tomllib.load(handle)["project"]["dependencies"]
    assert declared == [], (
        f"pyforge-testing-kit now declares runtime dependencies {declared!r} -- "
        f"the Q-26 stdlib-leaf premise behind branch_diff_guard.py's exemption "
        f"no longer holds; migrate its git calls to PosixProcess.run and remove "
        f"the exemption"
    )


def test_out_of_scope_stations_matches_the_documented_six():
    assert _OUT_OF_SCOPE_STATIONS == frozenset(
        {
            "pyforge-doctor",
            "pyforge-warden",
            "pyforge-steward",
            "pyforge-herald",
            "pyforge-mason",
            "pyforge-scribe",
        }
    ), "widening or narrowing this set is a real scope change -- update the module docstring's rationale alongside it"


@pytest.mark.parametrize("module_path", _scannable_files(), ids=lambda p: str(p.relative_to(PACKAGES_ROOT)))
def test_no_second_subprocess_implementation(module_path: Path):
    violations = _subprocess_violations(_parse(module_path))
    assert not violations, (
        f"{module_path} invokes a subprocess directly at line(s) {violations} -- "
        f"a second subprocess implementation outside pyforge-core (CAP-7: the "
        f"floor stays a floor; delegate to pyforge.core.process.PosixProcess "
        f"instead)"
    )


# --- non-vacuous proof: the guard is alive, not vacuous ----------------------


def test_guard_fires_on_synthetic_subprocess_run():
    synthetic = "import subprocess\nsubprocess.run(['echo', 'hi'])\n"
    assert _subprocess_violations(ast.parse(synthetic)) == [2]


def test_guard_fires_on_every_subprocess_invoke_method():
    synthetic = "\n".join(
        f"import subprocess\nsubprocess.{method}(['echo'])" for method in sorted(_SUBPROCESS_INVOKE_METHODS)
    )
    violations = _subprocess_violations(ast.parse(synthetic))
    assert len(violations) == len(_SUBPROCESS_INVOKE_METHODS)


def test_guard_fires_on_an_aliased_subprocess_import():
    synthetic = "import subprocess as sp\nsp.Popen(['echo'])\n"
    assert _subprocess_violations(ast.parse(synthetic)) == [2]


def test_guard_fires_on_a_bare_imported_subprocess_call():
    synthetic = "from subprocess import run\nrun(['echo'])\n"
    assert _subprocess_violations(ast.parse(synthetic)) == [2]
    aliased = "from subprocess import check_output as co\nco(['echo'])\n"
    assert _subprocess_violations(ast.parse(aliased)) == [2]


def test_guard_fires_on_synthetic_os_system_or_popen_shell_out():
    system_call = "import os\nos.system('echo hi')\n"
    assert _subprocess_violations(ast.parse(system_call)) == [2]
    popen_call = "import os\nos.popen('echo hi')\n"
    assert _subprocess_violations(ast.parse(popen_call)) == [2]


def test_guard_fires_on_synthetic_from_os_import_shell_out():
    from_system = "from os import system\n"
    assert _subprocess_violations(ast.parse(from_system)) == [1]
    from_popen_aliased = "from os import popen as p\n"
    assert _subprocess_violations(ast.parse(from_popen_aliased)) == [1]


def test_guard_fires_on_synthetic_aliased_os_and_spawn_exec_family():
    aliased = "import os as _o\n_o.system('echo hi')\n"
    assert _subprocess_violations(ast.parse(aliased)) == [2]
    execv = "import os\nos.execv('/bin/echo', ['echo'])\n"
    assert _subprocess_violations(ast.parse(execv)) == [2]
    spawn = "import os\nos.posix_spawn('/bin/echo', [], {})\n"
    assert _subprocess_violations(ast.parse(spawn)) == [2]


def test_guard_does_not_fire_on_benign_os_use():
    benign = "import os\nos.getcwd()\nfrom os import path\n"
    assert _subprocess_violations(ast.parse(benign)) == []


def test_guard_does_not_fire_on_a_bare_subprocess_type_reference():
    """The deliberate narrowing this guard's own module docstring explains:
    a bare ``subprocess.TimeoutExpired`` isinstance-classification reference
    -- Marshal's own ``vcs_git.py::add_worktree`` real shape -- must NOT be
    flagged, unlike Doctor's blanket "any subprocess.* attribute" ban."""
    synthetic = (
        "import subprocess\n"
        "def handle(exc):\n"
        "    if isinstance(exc.__cause__, subprocess.TimeoutExpired):\n"
        "        return True\n"
        "    return False\n"
    )
    assert _subprocess_violations(ast.parse(synthetic)) == []


def test_guard_does_not_fire_on_a_bare_subprocess_import_with_no_use():
    assert _subprocess_violations(ast.parse("import subprocess\n")) == []


def test_guard_does_not_fire_on_vcs_gits_real_body():
    """Non-vacuous proof (negative), against the REAL post-migration source:
    ``vcs_git.py`` keeps ``import subprocess`` solely for its
    ``isinstance(exc.__cause__, subprocess.TimeoutExpired)`` cleanup-guidance
    branch -- it must scan clean."""
    vcs_git_path = PACKAGES_ROOT / "pyforge-marshal/src/pyforge/marshal/adapters/vcs_git.py"
    assert vcs_git_path.is_file(), f"expected {vcs_git_path} to exist"
    assert _subprocess_violations(_parse(vcs_git_path)) == []


def test_guard_would_fire_on_doctors_cli_bridge_if_it_were_not_excluded():
    """Non-vacuous proof the station-level exclusion is doing real work
    (mirrors ``test_cli_bridge_itself_calls_subprocess``'s own
    non-vacuous-permission proof in Doctor's own test file): Doctor's
    ``cli_bridge.py`` really does call ``subprocess`` -- if this guard's
    exclusion set did not carve Doctor out, this file would be a real
    violation, not an accidentally-unused permission."""
    cli_bridge_path = PACKAGES_ROOT / "pyforge-doctor/src/pyforge/doctor/cli_bridge.py"
    assert cli_bridge_path.is_file(), f"expected {cli_bridge_path} to exist"
    assert _subprocess_violations(_parse(cli_bridge_path)) != []


def test_guard_would_fire_on_heralds_deck_pipeline_if_it_were_not_excluded():
    """Same non-vacuous proof for one of the three exclusions this story's
    own fleet-wide run discovered (module docstring)."""
    deck_pipeline_path = PACKAGES_ROOT / "pyforge-herald/src/pyforge/herald/deck_pipeline.py"
    assert deck_pipeline_path.is_file(), f"expected {deck_pipeline_path} to exist"
    assert _subprocess_violations(_parse(deck_pipeline_path)) != []
