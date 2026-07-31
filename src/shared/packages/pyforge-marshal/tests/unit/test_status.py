"""Unit tests for ``pyforge.marshal.core.status`` (Story 1.6, FR-4/FR-8,
AD-4) -- ``evaluate_homes``'s pure isolation-check logic driven entirely by
plain ``HomeFacts``/``MainCheckoutFacts`` objects (no ports, no I/O; that
lives in ``cli/init.py::run_homes`` and its own tests). Covers every row of
the spec's I/O & Edge-Case Matrix.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.marshal.core import status
from pyforge.marshal.core.model import Severity

_CANONICAL = Path("/repo/_bmad-output/projects/acme/implementation-artifacts")


def _home(
    *,
    path: Path = Path("/loop-homes/acme"),
    branch: str = "loop/acme",
    marker: str | None = None,
    symlink: Path | None = None,
    tier3_local: Path | None = None,
    tier3_canonical: Path = _CANONICAL,
    link_occupied: bool = False,
    tier3_canonical_is_dir: bool = True,
) -> status.HomeFacts:
    return status.HomeFacts(
        path=path,
        branch=branch,
        marker_text=marker,
        symlink_target=symlink,
        tier3_local_realpath=tier3_local,
        tier3_canonical_realpath=tier3_canonical,
        link_occupied=link_occupied,
        tier3_canonical_is_dir=tier3_canonical_is_dir,
    )


def _main(
    *,
    path: Path = Path("/repo"),
    branch: str | None = "main",
    marker: str | None = None,
    symlink: Path | None = None,
    link_occupied: bool = False,
) -> status.MainCheckoutFacts:
    return status.MainCheckoutFacts(
        path=path,
        branch=branch,
        marker_text=marker,
        symlink_target=symlink,
        link_occupied=link_occupied,
    )


_CLEAN_MAIN = _main()


# --- HomeFacts invariant ---------------------------------------------------------


def test_home_facts_rejects_a_non_loop_branch():
    with pytest.raises(ValueError, match="loop/"):
        status.HomeFacts(
            path=Path("/x"),
            branch="main",
            marker_text=None,
            symlink_target=None,
            tier3_local_realpath=None,
            tier3_canonical_realpath=Path("/y"),
        )


# --- two clean homes: exit-0, no findings -----------------------------------------


def test_two_clean_homes_are_not_desynced():
    acme_canonical = Path("/repo/_bmad-output/projects/acme/implementation-artifacts")
    beta_canonical = Path("/repo/_bmad-output/projects/beta/implementation-artifacts")
    acme = _home(
        path=Path("/loop-homes/acme"),
        branch="loop/acme",
        marker="acme\n",
        symlink=Path("projects/acme/planning-artifacts"),
        tier3_local=acme_canonical,
        tier3_canonical=acme_canonical,
    )
    beta = _home(
        path=Path("/loop-homes/beta"),
        branch="loop/beta",
        marker="beta\n",
        symlink=Path("projects/beta/planning-artifacts"),
        tier3_local=beta_canonical,
        tier3_canonical=beta_canonical,
    )
    result = status.evaluate_homes((acme, beta), _CLEAN_MAIN)
    assert result.findings == ()
    assert [row["desynced"] for row in result.homes] == [False, False]
    assert result.main_checkout["desynced"] is False
    assert [row["slug"] for row in result.homes] == ["acme", "beta"]
    assert [row["active_project"] for row in result.homes] == ["acme", "beta"]


# --- marker/symlink desync: MRS-HOMES-001 -----------------------------------------


def test_home_marker_symlink_desync_reports_mrs_homes_001():
    home = _home(
        marker="other-project\n",
        symlink=Path("projects/yet-another/planning-artifacts"),
        tier3_local=_CANONICAL,
    )
    result = status.evaluate_homes((home,), _CLEAN_MAIN)
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.code == "MRS-HOMES-001"
    assert finding.severity is Severity.ERROR
    assert str(home.path) in finding.path
    assert "other-project" in finding.message
    assert "yet-another" in finding.message
    assert result.homes[0]["desynced"] is True


# --- the blind spot: agrees with itself but not its own branch --------------------


def test_home_agrees_with_itself_but_not_branch_reports_mrs_homes_001():
    """Closes the deferred-work blind spot: MRS-INIT-003's own two-way check
    would treat this as clean (marker == symlink), but the home's directory
    is keyed by loop/bar, not the foo both agree on."""
    home = _home(
        branch="loop/bar",
        marker="foo\n",
        symlink=Path("projects/foo/planning-artifacts"),
        tier3_local=_CANONICAL,
    )
    result = status.evaluate_homes((home,), _CLEAN_MAIN)
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.code == "MRS-HOMES-001"
    assert "foo" in finding.message
    assert "bar" in finding.message
    row = result.homes[0]
    assert row["slug"] == "bar"  # branch-derived, never the marker/symlink value
    assert row["active_project"] == "foo"
    assert row["desynced"] is True


def test_marker_alone_present_and_matching_branch_is_not_a_violation():
    """A legitimately partial provision (interrupted before the symlink
    step) always agrees with the branch by construction -- not a violation."""
    home = _home(marker="acme\n", symlink=None, tier3_local=None)
    result = status.evaluate_homes((home,), _CLEAN_MAIN)
    assert result.findings == ()
    row = result.homes[0]
    assert row["active_project"] == "acme"
    assert row["desynced"] is False


def test_marker_alone_present_and_disagreeing_with_branch_is_a_violation():
    """Unlike MRS-INIT-003's own two-way rule (which requires BOTH marker
    and symlink present before comparing), the branch is ALWAYS known, so a
    single divergent field is itself real evidence of tampering."""
    home = _home(branch="loop/acme", marker="rogue\n", symlink=None, tier3_local=None)
    result = status.evaluate_homes((home,), _CLEAN_MAIN)
    assert len(result.findings) == 1
    assert result.findings[0].code == "MRS-HOMES-001"
    assert "rogue" in result.findings[0].message
    assert result.homes[0]["desynced"] is True


def test_unrecognized_symlink_shape_is_a_violation():
    """Ported from cli/init.py's own MRS-INIT-003: a symlink target that
    EXISTS but doesn't parse as projects/<slug>/planning-artifacts is
    evidence of hand configuration, reported on its own."""
    home = _home(marker=None, symlink=Path("/somewhere/else"), tier3_local=None)
    result = status.evaluate_homes((home,), _CLEAN_MAIN)
    assert len(result.findings) == 1
    assert result.findings[0].code == "MRS-HOMES-001"
    assert "unrecognized" in result.findings[0].message


def test_occupied_planning_artifacts_is_a_violation():
    """A real (non-symlink) occupant at the planning-artifacts path is one
    step further gone than an unrecognized symlink target -- previously it
    read as benign absence (review finding)."""
    home = _home(marker="acme\n", symlink=None, link_occupied=True, tier3_local=None)
    result = status.evaluate_homes((home,), _CLEAN_MAIN)
    assert len(result.findings) == 1
    assert result.findings[0].code == "MRS-HOMES-001"
    assert "occupied" in result.findings[0].message
    assert result.homes[0]["desynced"] is True


def test_all_three_slugs_disagreeing_names_every_pair():
    """The multi-corruption case (review finding): with marker, symlink,
    and branch all pairwise disagreeing, the finding must name EVERY
    disagreeing value, not just the first pair."""
    home = _home(
        branch="loop/zeta",
        marker="alpha\n",
        symlink=Path("projects/beta/planning-artifacts"),
        tier3_local=None,
    )
    result = status.evaluate_homes((home,), _CLEAN_MAIN)
    assert len(result.findings) == 1
    message = result.findings[0].message
    assert "alpha" in message
    assert "beta" in message
    assert "zeta" in message


# --- Tier-3 realpath mismatch: MRS-HOMES-002 --------------------------------------


def test_tier3_realpath_mismatch_reports_mrs_homes_002():
    home = _home(
        marker="acme\n",
        symlink=Path("projects/acme/planning-artifacts"),
        tier3_local=Path("/somewhere/else"),
        tier3_canonical=_CANONICAL,
    )
    result = status.evaluate_homes((home,), _CLEAN_MAIN)
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.code == "MRS-HOMES-002"
    assert "/somewhere/else" in finding.message
    assert str(_CANONICAL) in finding.message
    assert result.homes[0]["desynced"] is True


def test_tier3_and_slug_mismatch_both_fire_independently():
    home = _home(
        marker="other\n",
        symlink=Path("projects/yet-another/planning-artifacts"),
        tier3_local=Path("/somewhere/else"),
        tier3_canonical=_CANONICAL,
    )
    result = status.evaluate_homes((home,), _CLEAN_MAIN)
    codes = [finding.code for finding in result.findings]
    assert codes == ["MRS-HOMES-001", "MRS-HOMES-002"]
    assert result.homes[0]["desynced"] is True


def test_unprovisioned_tier3_backlink_is_not_a_violation():
    home = _home(marker="acme\n", symlink=Path("projects/acme/planning-artifacts"), tier3_local=None)
    result = status.evaluate_homes((home,), _CLEAN_MAIN)
    assert result.findings == ()
    assert result.homes[0]["desynced"] is False


def test_backlink_dangling_at_the_canonical_path_is_a_violation():
    """The backlink resolves to the RIGHT path, but the canonical store
    itself is gone (review finding: previously blessed as clean) -- marshal
    init's own convergence check has always required is_dir(canonical)."""
    home = _home(
        marker="acme\n",
        symlink=Path("projects/acme/planning-artifacts"),
        tier3_local=_CANONICAL,
        tier3_canonical=_CANONICAL,
        tier3_canonical_is_dir=False,
    )
    result = status.evaluate_homes((home,), _CLEAN_MAIN)
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.code == "MRS-HOMES-002"
    assert "does not exist" in finding.message
    assert result.homes[0]["desynced"] is True


def test_missing_canonical_store_without_a_backlink_is_not_a_violation():
    """The dangling-backlink check only applies when a backlink exists --
    an unprovisioned home whose canonical store also doesn't exist yet is
    still just 'never provisioned'."""
    home = _home(marker="acme\n", symlink=Path("projects/acme/planning-artifacts"), tier3_local=None, tier3_canonical_is_dir=False)
    result = status.evaluate_homes((home,), _CLEAN_MAIN)
    assert result.findings == ()
    assert result.homes[0]["desynced"] is False


# --- main checkout: two-way check, same code --------------------------------------


def test_main_checkout_desync_reports_mrs_homes_001_naming_main():
    main = _main(marker="other\n", symlink=Path("projects/elsewhere/planning-artifacts"))
    home = _home(marker="acme\n", symlink=Path("projects/acme/planning-artifacts"), tier3_local=_CANONICAL)
    result = status.evaluate_homes((home,), main)
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.code == "MRS-HOMES-001"
    assert str(main.path) in finding.path
    assert "main checkout" in finding.message
    assert result.main_checkout["desynced"] is True
    assert result.homes[0]["desynced"] is False  # unaffected


def test_main_checkout_untouched_is_self_consistent():
    """'Untouched' == both absent, matching the spec's own framing: there is
    no stored baseline, only self-consistency at invocation time."""
    result = status.evaluate_homes((), _CLEAN_MAIN)
    assert result.findings == ()
    assert result.main_checkout == {
        "path": str(_CLEAN_MAIN.path),
        "branch": "main",
        "slug": None,
        "active_project": None,
        "desynced": False,
    }


def test_main_checkout_marker_alone_present_is_not_a_violation():
    """The main checkout has no branch-derived third leg -- a single
    present field is a benign partial state, exactly MRS-INIT-003's own
    two-way rule."""
    main = _main(marker="acme\n", symlink=None)
    result = status.evaluate_homes((), main)
    assert result.findings == ()
    assert result.main_checkout["desynced"] is False


def test_main_checkout_occupied_planning_artifacts_is_a_violation():
    """Same occupancy rule as a home's (review finding): a real directory
    materialized at the main checkout's planning-artifacts path is named,
    never read as 'symlink absent'."""
    main = _main(marker=None, symlink=None, link_occupied=True)
    result = status.evaluate_homes((), main)
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.code == "MRS-HOMES-001"
    assert "main checkout" in finding.message
    assert "occupied" in finding.message
    assert result.main_checkout["desynced"] is True


# --- zero/one home -----------------------------------------------------------------


def test_zero_homes_reports_empty_homes_and_the_main_checkout():
    result = status.evaluate_homes((), _CLEAN_MAIN)
    assert result.homes == ()
    assert result.main_checkout["path"] == str(_CLEAN_MAIN.path)


def test_one_home_reports_a_single_row():
    home = _home(marker="acme\n", symlink=Path("projects/acme/planning-artifacts"), tier3_local=_CANONICAL)
    result = status.evaluate_homes((home,), _CLEAN_MAIN)
    assert len(result.homes) == 1
    assert result.findings == ()


# --- finding ordering: homes (in order), then main checkout -----------------------


def test_findings_are_ordered_homes_then_main_checkout():
    desynced_home = _home(
        path=Path("/loop-homes/acme"),
        branch="loop/acme",
        marker="other\n",
        symlink=Path("projects/yet-another/planning-artifacts"),
        tier3_local=_CANONICAL,
    )
    desynced_main = _main(marker="x\n", symlink=Path("projects/y/planning-artifacts"))
    result = status.evaluate_homes((desynced_home,), desynced_main)
    assert [f.path for f in result.findings] == [
        str(desynced_home.path),
        str(desynced_main.path),
    ]


# --- drift guard: this module's private slug-parsing helpers must stay -----
# byte-identical to cli/init.py's own copies (this module's docstring
# explains WHY they are duplicated rather than imported -- core/ never
# imports from cli/). A silent divergence between the two would make
# `marshal homes` and `marshal init` disagree about what counts as a valid
# symlink/marker shape (review finding: no test previously proved this).


def test_slug_from_marker_matches_cli_init_copy():
    from pyforge.marshal.cli import init as init_cli

    for value in (None, "", "  ", "acme", "  acme  \n", "acme\n"):
        assert status._slug_from_marker(value) == init_cli._slug_from_marker(value)


def test_slug_from_symlink_target_matches_cli_init_copy():
    from pyforge.marshal.cli import init as init_cli

    for target in (
        None,
        Path("projects/acme/planning-artifacts"),
        Path("/absolute/projects/acme/planning-artifacts"),
        Path("projects/acme/other-artifacts"),
        Path("wrong/depth"),
        Path("projects/acme/nested/planning-artifacts"),
    ):
        assert status._slug_from_symlink_target(
            target
        ) == init_cli._slug_from_symlink_target(target)
