"""Unit tests for ``pyforge.doctor.sources`` (Story 6.2) -- covers every row
of the spec's I/O & Edge-Case Matrix: ``SourceRegistration`` construction
(well-formed, missing subject, missing owner, invalid scope) and the
registry <-> ``Source`` coherence test, mirroring ``checks/registry.py``'s
own ``test_every_cataloged_category_is_dispatchable_by_gather_one``
tripwire -- a ``Source`` with no registry entry, or a registry entry with no
matching ``Source``, must fail loudly rather than pass silently.

Story 6.3 adds ``scope_for`` (the canonical per-source scope lookup) and
``degrade_on_exception`` (the reusable "cannot evaluate here" wrapper for a
future ``scope="runtime"`` source's own gather) -- covering the spec's
remaining two I/O matrix rows.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pyforge.doctor import sources
from pyforge.doctor.models import DoctorStatus, Finding, Source
from pyforge.doctor.score import Grade, grade
from pyforge.doctor.sources import (
    REGISTRY,
    SourceRegistration,
    degrade_on_exception,
    list_sources,
    locate_checkout_script,
    scope_for,
)

# --- SourceRegistration construction ------------------------------------------


def test_well_formed_registration_constructs():
    registration = SourceRegistration(
        source=Source.MARSHAL_DURABILITY,
        scope="repo",
        subject_station="marshal",
        owning_station="doctor",
    )
    assert registration.source is Source.MARSHAL_DURABILITY
    assert registration.scope == "repo"
    assert registration.subject_station == "marshal"
    assert registration.owning_station == "doctor"


def test_non_source_value_raises_value_error():
    with pytest.raises(ValueError, match="source"):
        SourceRegistration(
            source="marshal-durability",  # a plain str, not a Source member
            scope="repo",
            subject_station="marshal",
            owning_station="doctor",
        )


def test_empty_subject_station_raises_value_error():
    with pytest.raises(ValueError, match="subject_station"):
        SourceRegistration(
            source=Source.MARSHAL_DURABILITY,
            scope="repo",
            subject_station="",
            owning_station="doctor",
        )


def test_whitespace_only_subject_station_raises_value_error():
    with pytest.raises(ValueError, match="subject_station"):
        SourceRegistration(
            source=Source.MARSHAL_DURABILITY,
            scope="repo",
            subject_station="   ",
            owning_station="doctor",
        )


def test_whitespace_only_owning_station_raises_value_error():
    with pytest.raises(ValueError, match="owning_station"):
        SourceRegistration(
            source=Source.MARSHAL_DURABILITY,
            scope="repo",
            subject_station="marshal",
            owning_station="\t",
        )


def test_none_subject_station_raises_value_error():
    with pytest.raises(ValueError, match="subject_station"):
        SourceRegistration(
            source=Source.MARSHAL_DURABILITY,
            scope="repo",
            subject_station=None,
            owning_station="doctor",
        )


def test_empty_owning_station_raises_value_error():
    with pytest.raises(ValueError, match="owning_station"):
        SourceRegistration(
            source=Source.MARSHAL_DURABILITY,
            scope="repo",
            subject_station="marshal",
            owning_station="",
        )


def test_none_owning_station_raises_value_error():
    with pytest.raises(ValueError, match="owning_station"):
        SourceRegistration(
            source=Source.MARSHAL_DURABILITY,
            scope="repo",
            subject_station="marshal",
            owning_station=None,
        )


def test_invalid_scope_raises_value_error():
    with pytest.raises(ValueError, match="scope"):
        SourceRegistration(
            source=Source.MARSHAL_DURABILITY,
            scope="hostile",
            subject_station="marshal",
            owning_station="doctor",
        )


# --- REGISTRY <-> Source coherence --------------------------------------------


def test_every_source_member_has_exactly_one_registry_entry():
    # Two-directional set-equality: a Source with no REGISTRY entry, or a
    # REGISTRY entry with no matching Source, fails this test -- never a
    # silent one-directional subset pass (Epic 6's own stated discipline).
    source_values = {member.value for member in Source}
    registry_values = [registration.source.value for registration in REGISTRY]

    assert set(registry_values) == source_values
    assert len(registry_values) == len(set(registry_values)), (
        "REGISTRY must carry exactly one entry per Source member, no duplicates"
    )


def test_every_registry_entry_has_valid_subject_owner_and_scope():
    for registration in REGISTRY:
        assert registration.subject_station
        assert registration.owning_station
        assert registration.scope in {"repo", "runtime"}


def test_list_sources_returns_the_registry():
    assert list_sources() == REGISTRY


# --- to_json_dict --------------------------------------------------------------


def test_to_json_dict_matches_the_four_declared_fields():
    registration = SourceRegistration(
        source=Source.MARSHAL_DURABILITY,
        scope="repo",
        subject_station="marshal",
        owning_station="doctor",
    )
    assert registration.to_json_dict() == {
        "source": "marshal-durability",
        "scope": "repo",
        "subject_station": "marshal",
        "owning_station": "doctor",
    }


# --- scope_for (Story 6.3) ----------------------------------------------------


def test_scope_for_resolves_a_known_sources_registered_scope():
    assert scope_for(Source.MARSHAL_DURABILITY) == "repo"
    assert scope_for(Source.WARDEN_DOCTOR) == "repo"


def test_scope_for_raises_value_error_for_a_value_with_no_registry_entry():
    # A plain str equal-by-value to a real Source (StrEnum equality would
    # admit it) but not the same registered member -- the misuse path
    # SourceRegistration's own __post_init__ isinstance check guards on
    # construction; scope_for must fail the same way, not silently resolve
    # it via `==` to the matching member.
    with pytest.raises(ValueError, match="REGISTRY entry"):
        scope_for("marshal-durability")  # type: ignore[arg-type]


# --- degrade_on_exception (Story 6.3) -----------------------------------------


def test_degrade_on_exception_passes_through_a_successful_gather_unchanged():
    findings = (
        Finding(
            source=Source.MARSHAL_DURABILITY,
            check="ledger-regression",
            status=DoctorStatus.OK,
            message="8 tracked ledger(s) hold",
            evidence={"ledgers": 8},
        ),
    )

    result = degrade_on_exception(Source.MARSHAL_DURABILITY, "ledger-regression", lambda: findings)

    assert result == findings


def test_degrade_on_exception_converts_a_raised_exception_into_one_warn_finding():
    def _boom() -> tuple[Finding, ...]:
        raise RuntimeError("tmux socket unreachable")

    result = degrade_on_exception(Source.MARSHAL_DURABILITY, "dashboard-drift", _boom)

    assert len(result) == 1
    finding = result[0]
    assert finding.source is Source.MARSHAL_DURABILITY
    assert finding.check == "dashboard-drift"
    assert finding.status is DoctorStatus.WARN
    assert "RuntimeError" in finding.message
    assert "tmux socket unreachable" in finding.message


def test_degrade_on_exception_lets_a_base_exception_propagate_uncaught():
    # Deliberately confirms the documented Exception-only catch boundary --
    # a KeyboardInterrupt/SystemExit raised inside gather must still
    # propagate, mirroring main()'s own three-tier handler ordering.
    def _boom() -> tuple[Finding, ...]:
        raise KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        degrade_on_exception(Source.MARSHAL_DURABILITY, "dashboard-drift", _boom)


# --- locate_checkout_script (Story 40.1, DW-FU-6-5-9) ---------------------------
#
# The one locator both script loaders (board's fleet_scan, factory's pixi_env_matrix) share:
# Doctor's OWN checkout, found by walking up from this package's own file -- never the tree
# a caller asks Doctor to judge.

_CHECKOUT_FLEET_SCAN = next(
    (a / "scripts" / "fleet_scan.py" for a in Path(__file__).resolve().parents if (a / "scripts" / "fleet_scan.py").is_file()),
    None,
)
_needs_checkout = pytest.mark.skipif(_CHECKOUT_FLEET_SCAN is None, reason="not run from inside a checkout")


@_needs_checkout
def test_locate_checkout_script_finds_the_script_above_the_package() -> None:
    found = locate_checkout_script("fleet_scan.py")

    assert found == _CHECKOUT_FLEET_SCAN
    assert found.parent.name == "scripts"
    assert Path(sources.__file__).resolve().is_relative_to(found.parent.parent)


@_needs_checkout
def test_locate_checkout_script_ignores_the_working_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "fleet_scan.py").write_text("raise SystemExit('judged tree')\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert locate_checkout_script("fleet_scan.py") == _CHECKOUT_FLEET_SCAN


def test_locate_checkout_script_raises_an_oserror_naming_a_missing_file() -> None:
    with pytest.raises(FileNotFoundError, match=r"scripts/no-such-script-40-1\.py not found above") as excinfo:
        locate_checkout_script("no-such-script-40-1.py")

    assert isinstance(excinfo.value, OSError)


def test_locate_checkout_script_outside_any_checkout_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # An installed wheel: nothing above the package holds a scripts/ directory.
    installed = tmp_path / "site-packages" / "pyforge" / "doctor" / "sources" / "__init__.py"
    monkeypatch.setattr(sources, "__file__", str(installed))

    with pytest.raises(FileNotFoundError, match=r"scripts/fleet_scan\.py not found above"):
        locate_checkout_script("fleet_scan.py")


def test_a_real_degrade_on_exception_warn_grades_its_axis_incomplete() -> None:
    """The evidence key `score` keys on is the one `degrade_on_exception` really writes
    (`score` cannot import `sources`, so nothing else ties the two literals together)."""

    def _boom() -> tuple[Finding, ...]:
        raise OSError("scripts/fleet_scan.py not found")

    degraded = degrade_on_exception(Source.CHAIN_LAYERS_AUDIT, "chain-layers-audit", _boom)

    result = grade(degraded)
    assert result.grade is Grade.INCOMPLETE
    assert [axis.grade for axis in result.axis_scores] == [Grade.INCOMPLETE]
