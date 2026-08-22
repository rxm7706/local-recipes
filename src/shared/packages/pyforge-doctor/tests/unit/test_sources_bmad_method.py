"""Unit tests for ``pyforge.doctor.sources.bmad_method.gather`` (Story 10.1,
Epic 10/CAP-1; Story 10.2, Epic 10/CAP-2; Story 14.1, Epic 14/CAP-4's suite
pass) -- covers every row of the specs' I/O & Edge-Case Matrices against
REAL tmp fixture trees (a written ``pixi.toml`` +
``_bmad/_config/manifest.yaml``, plus ``.pixi/envs/*/conda-meta/`` filename
markers for CAP-4), mirroring
``test_sources_chain_due_for_verification.py``'s own real-fixture discipline.
The exceptions are ``test_gather_degrades_on_unexpected_exception``, which
deliberately monkeypatches ``_gather`` to force an exception shape no real
fixture can produce -- proving the outer ``degrade_on_exception`` safety net
itself, not the comparison logic (review finding: the prior wording claimed
"no mocks" unconditionally) -- and CAP-2's own network-boundary tests, which
monkeypatch ``_fetch_latest_upstream_version``/``urllib.request.urlopen``
rather than making a live registry call.

The module-level ``_stub_upstream_fetch`` fixture below is ``autouse=True``
so every CAP-1 test above it keeps asserting ``len(findings) == 1``
unmodified, exactly as it did before CAP-2 existed (Boundaries) -- mirrors
this file's own ``test_gather_degrades_on_unexpected_exception`` monkeypatch
idiom, and ``test_sources_chain_due_for_verification.py``'s own
autouse-fixture-per-module convention.
"""

from __future__ import annotations

import email.message
import http.client
import json
import urllib.error
from pathlib import Path

import pytest
from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import bmad_method

#: Captured before the autouse fixture below ever patches the module
#: attribute of the same name -- the direct ``_fetch_latest_upstream_
#: version`` unit tests exercise THIS real function object, not the
#: per-test stub the fixture installs (which would otherwise shadow it and
#: make every one of those tests observe the stub instead of the real
#: network-boundary logic under test).
_real_fetch_latest_upstream_version = bmad_method._fetch_latest_upstream_version


@pytest.fixture(autouse=True)
def _stub_upstream_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bmad_method, "_fetch_latest_upstream_version", lambda **_: None)


# --- fixture helpers ---------------------------------------------------------


def _write_pixi(target: Path, text: str) -> Path:
    path = target / "pixi.toml"
    path.write_text(text, encoding="utf-8")
    return path


def _write_manifest(target: Path, text: str) -> Path:
    path = target / "_bmad" / "_config" / "manifest.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


_PIXI_SINGLE = """
[feature.python.dependencies]
bmad-method = ">=6.11.0"
"""

_PIXI_TWO_TABLES_SAME_FLOOR = """
[feature.python.dependencies]
bmad-method = ">=6.11.0"

[feature.local-recipes.dependencies]
bmad-method = ">=6.11.0"
"""

_PIXI_TWO_TABLES_DIFFERENT_FLOORS = """
[feature.python.dependencies]
bmad-method = ">=6.11.0"

[feature.local-recipes.dependencies]
bmad-method = ">=6.12.0"
"""

_PIXI_NO_BMAD_METHOD = """
[feature.python.dependencies]
pixi = ">=1.0"
"""

_PIXI_UNPARSEABLE_EQUALS = """
[feature.python.dependencies]
bmad-method = "==6.11.0"
"""

_PIXI_UNPARSEABLE_STAR = """
[feature.python.dependencies]
bmad-method = "*"
"""

_MANIFEST_610 = "installation:\n  version: 6.10.0\n"
_MANIFEST_611 = "installation:\n  version: 6.11.0\n"
_MANIFEST_612 = "installation:\n  version: 6.12.0\n"
_MANIFEST_MALFORMED_SHAPE = "installation: not-a-mapping\n"
_MANIFEST_MISSING_VERSION_KEY = "installation:\n  installDate: 2026-01-01\n"
_MANIFEST_BAD_YAML = "installation: [unterminated\n"


# --- Real drift (today's live shape) -----------------------------------------


def test_installed_behind_declared_floor_reports_one_warn_naming_both_versions(
    tmp_path: Path,
) -> None:
    _write_pixi(tmp_path, _PIXI_SINGLE)
    _write_manifest(tmp_path, _MANIFEST_610)

    findings = bmad_method.gather(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.BMAD_METHOD_VERSION_DRIFT
    assert finding.status is DoctorStatus.WARN
    assert "6.10.0" in finding.message
    assert "6.11.0" in finding.message
    assert finding.evidence == {"installed": "6.10.0", "declared_floor": ">=6.11.0"}


# --- Agreement ----------------------------------------------------------------


def test_installed_equal_to_declared_floor_reports_one_ok(tmp_path: Path) -> None:
    _write_pixi(tmp_path, _PIXI_SINGLE)
    _write_manifest(tmp_path, _MANIFEST_611)

    findings = bmad_method.gather(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.BMAD_METHOD_VERSION_DRIFT
    assert finding.status is DoctorStatus.OK
    assert "6.11.0" in finding.message


def test_installed_ahead_of_declared_floor_reports_one_ok(tmp_path: Path) -> None:
    _write_pixi(tmp_path, _PIXI_SINGLE)
    _write_manifest(tmp_path, _MANIFEST_612)

    findings = bmad_method.gather(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK


# --- Multiple declarations ------------------------------------------------------


def test_two_tables_same_floor_treated_as_one_floor(tmp_path: Path) -> None:
    _write_pixi(tmp_path, _PIXI_TWO_TABLES_SAME_FLOOR)
    _write_manifest(tmp_path, _MANIFEST_611)

    findings = bmad_method.gather(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.OK
    assert findings[0].evidence["declared_floor"] == ">=6.11.0"


def test_two_tables_different_floors_uses_the_maximum(tmp_path: Path) -> None:
    _write_pixi(tmp_path, _PIXI_TWO_TABLES_DIFFERENT_FLOORS)
    _write_manifest(tmp_path, _MANIFEST_611)

    findings = bmad_method.gather(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    # installed 6.11.0 is behind the MAX floor (6.12.0), even though it
    # satisfies the lower of the two declared floors.
    assert finding.status is DoctorStatus.WARN
    assert finding.evidence["declared_floor"] == ">=6.12.0"


# --- pixi.toml missing bmad-method entirely --------------------------------------


def test_pixi_toml_missing_bmad_method_entirely_reports_one_warn(
    tmp_path: Path,
) -> None:
    _write_pixi(tmp_path, _PIXI_NO_BMAD_METHOD)
    _write_manifest(tmp_path, _MANIFEST_610)

    findings = bmad_method.gather(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.BMAD_METHOD_VERSION_DRIFT
    assert finding.status is DoctorStatus.WARN
    assert "could not be evaluated here" in finding.message


# --- pixi.toml / manifest.yaml missing or unreadable ------------------------------


def test_missing_pixi_toml_reports_one_warn(tmp_path: Path) -> None:
    _write_manifest(tmp_path, _MANIFEST_610)

    findings = bmad_method.gather(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.status is DoctorStatus.WARN
    assert "could not be evaluated here" in finding.message


def test_missing_manifest_yaml_reports_one_warn(tmp_path: Path) -> None:
    _write_pixi(tmp_path, _PIXI_SINGLE)

    findings = bmad_method.gather(tmp_path)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.status is DoctorStatus.WARN
    assert "could not be evaluated here" in finding.message


# --- Unparseable constraint form ---------------------------------------------------


def test_equals_constraint_form_reports_one_warn(tmp_path: Path) -> None:
    _write_pixi(tmp_path, _PIXI_UNPARSEABLE_EQUALS)
    _write_manifest(tmp_path, _MANIFEST_610)

    findings = bmad_method.gather(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.WARN


def test_star_constraint_form_reports_one_warn(tmp_path: Path) -> None:
    _write_pixi(tmp_path, _PIXI_UNPARSEABLE_STAR)
    _write_manifest(tmp_path, _MANIFEST_610)

    findings = bmad_method.gather(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.WARN


# --- manifest.yaml malformed / missing installation.version -----------------------


def test_manifest_installation_not_a_mapping_reports_one_warn(tmp_path: Path) -> None:
    _write_pixi(tmp_path, _PIXI_SINGLE)
    _write_manifest(tmp_path, _MANIFEST_MALFORMED_SHAPE)

    findings = bmad_method.gather(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.WARN


def test_manifest_missing_version_key_reports_one_warn(tmp_path: Path) -> None:
    _write_pixi(tmp_path, _PIXI_SINGLE)
    _write_manifest(tmp_path, _MANIFEST_MISSING_VERSION_KEY)

    findings = bmad_method.gather(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.WARN


def test_manifest_bad_yaml_reports_one_warn(tmp_path: Path) -> None:
    _write_pixi(tmp_path, _PIXI_SINGLE)
    _write_manifest(tmp_path, _MANIFEST_BAD_YAML)

    findings = bmad_method.gather(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.WARN


# --- never raises: degrade_on_exception safety net ---------------------------------


def test_gather_never_raises_on_a_completely_empty_target_directory(
    tmp_path: Path,
) -> None:
    # An empty target dir: neither pixi.toml nor manifest.yaml exists at all.
    findings = bmad_method.gather(tmp_path)
    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.WARN
    assert findings[0].source is Source.BMAD_METHOD_VERSION_DRIFT


def test_gather_degrades_on_unexpected_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(target: Path):
        raise RuntimeError("kaboom")

    monkeypatch.setattr(bmad_method, "_gather", _boom)

    findings = bmad_method.gather(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.WARN
    assert findings[0].source is Source.BMAD_METHOD_VERSION_DRIFT
    assert "RuntimeError" in findings[0].message


# --- upstream npm comparison (Story 10.2, Epic 10/CAP-2) -----------------------


def test_installed_behind_latest_upstream_reports_second_warn_naming_both_versions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_pixi(tmp_path, _PIXI_SINGLE)
    _write_manifest(tmp_path, _MANIFEST_610)
    monkeypatch.setattr(
        bmad_method, "_fetch_latest_upstream_version", lambda **_: (6, 12, 0)
    )

    findings = bmad_method.gather(tmp_path)

    assert len(findings) == 2
    upstream = findings[1]
    assert upstream.source is Source.BMAD_METHOD_VERSION_DRIFT
    assert upstream.check == "bmad-method-upstream-drift"
    assert upstream.status is DoctorStatus.WARN
    assert "6.10.0" in upstream.message
    assert "6.12.0" in upstream.message
    assert upstream.evidence == {"installed": "6.10.0", "latest_upstream": "6.12.0"}


def test_installed_meets_declared_floor_but_behind_latest_upstream_reports_ok_plus_warn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Proves the story's own Problem statement: CAP-1 can report ok (installed
    # meets pixi.toml's declared floor) while CAP-2 still reports drift
    # against the further-ahead actual latest upstream release.
    _write_pixi(tmp_path, _PIXI_SINGLE)
    _write_manifest(tmp_path, _MANIFEST_611)
    monkeypatch.setattr(
        bmad_method, "_fetch_latest_upstream_version", lambda **_: (6, 12, 0)
    )

    findings = bmad_method.gather(tmp_path)

    assert len(findings) == 2
    assert findings[0].check == "bmad-method-version-drift"
    assert findings[0].status is DoctorStatus.OK
    assert findings[1].check == "bmad-method-upstream-drift"
    assert findings[1].status is DoctorStatus.WARN


def test_installed_equal_to_latest_upstream_reports_second_ok(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_pixi(tmp_path, _PIXI_SINGLE)
    _write_manifest(tmp_path, _MANIFEST_611)
    monkeypatch.setattr(
        bmad_method, "_fetch_latest_upstream_version", lambda **_: (6, 11, 0)
    )

    findings = bmad_method.gather(tmp_path)

    assert len(findings) == 2
    assert findings[1].check == "bmad-method-upstream-drift"
    assert findings[1].status is DoctorStatus.OK


def test_installed_ahead_of_latest_upstream_reports_second_ok(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A pre-release/dev install ahead of the latest published release.
    _write_pixi(tmp_path, _PIXI_SINGLE)
    _write_manifest(tmp_path, _MANIFEST_612)
    monkeypatch.setattr(
        bmad_method, "_fetch_latest_upstream_version", lambda **_: (6, 11, 0)
    )

    findings = bmad_method.gather(tmp_path)

    assert len(findings) == 2
    assert findings[1].check == "bmad-method-upstream-drift"
    assert findings[1].status is DoctorStatus.OK


def test_upstream_fetch_failure_leaves_exactly_the_one_cap1_finding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_pixi(tmp_path, _PIXI_SINGLE)
    _write_manifest(tmp_path, _MANIFEST_610)
    monkeypatch.setattr(bmad_method, "_fetch_latest_upstream_version", lambda **_: None)

    findings = bmad_method.gather(tmp_path)

    assert len(findings) == 1
    assert findings[0].check == "bmad-method-version-drift"


def test_gather_exercises_the_real_fetch_helper_end_to_end(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Every other CAP-2 gather-level test stubs _fetch_latest_upstream_version
    # wholesale, and every direct _fetch_latest_upstream_version test bypasses
    # gather()/_gather() entirely -- neither exercises the seam between the
    # two halves with both sides real (review finding, Story 10.2). This one
    # restores the REAL _fetch_latest_upstream_version (undoing the autouse
    # stub above) and only stubs urlopen, one layer down.
    monkeypatch.setattr(
        bmad_method, "_fetch_latest_upstream_version", _real_fetch_latest_upstream_version
    )
    _stub_urlopen(
        monkeypatch,
        json.dumps({"name": "bmad-method", "version": "6.12.0"}).encode(),
    )
    _write_pixi(tmp_path, _PIXI_SINGLE)
    _write_manifest(tmp_path, _MANIFEST_610)

    findings = bmad_method.gather(tmp_path)

    assert len(findings) == 2
    assert findings[1].check == "bmad-method-upstream-drift"
    assert findings[1].evidence == {"installed": "6.10.0", "latest_upstream": "6.12.0"}


def test_broken_cap1_inputs_never_reach_the_fetch_helper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # I/O matrix: when CAP-1's own inputs are broken (missing pixi.toml),
    # degrade_on_exception fires before _gather ever reaches the fetch call
    # -- the network helper must not be invoked at all.
    _write_manifest(tmp_path, _MANIFEST_610)

    def _unreachable(**_):
        raise AssertionError("_fetch_latest_upstream_version must not be called")

    monkeypatch.setattr(bmad_method, "_fetch_latest_upstream_version", _unreachable)

    findings = bmad_method.gather(tmp_path)

    assert len(findings) == 1
    assert findings[0].status is DoctorStatus.WARN
    assert "could not be evaluated here" in findings[0].message


# --- _fetch_latest_upstream_version's own success/failure branches -------------


class _FakeUrlopenResponse:
    """A minimal stand-in for what ``urllib.request.urlopen`` returns as a
    context manager -- only ``read()`` is ever called on it."""

    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self) -> "_FakeUrlopenResponse":
        return self

    def __exit__(self, *exc_info: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


def _stub_urlopen(monkeypatch: pytest.MonkeyPatch, body: bytes) -> None:
    monkeypatch.setattr(
        bmad_method.urllib.request, "urlopen",
        lambda *args, **kwargs: _FakeUrlopenResponse(body),
    )


def test_fetch_latest_upstream_version_returns_parsed_tuple_on_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_urlopen(
        monkeypatch,
        json.dumps({"name": "bmad-method", "version": "6.12.0"}).encode(),
    )
    assert _real_fetch_latest_upstream_version() == (6, 12, 0)


def test_fetch_latest_upstream_version_folds_http_error_to_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise(*args, **kwargs):
        # A real urlopen-raised HTTPError always carries a populated headers
        # object, never `hdrs=None` (review finding, Story 10.2) -- an empty
        # `email.message.Message()` is the minimal real shape.
        raise urllib.error.HTTPError(
            "https://registry.npmjs.org", 500, "boom", email.message.Message(), None
        )

    monkeypatch.setattr(bmad_method.urllib.request, "urlopen", _raise)
    assert _real_fetch_latest_upstream_version() is None


def test_fetch_latest_upstream_version_folds_url_error_to_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise(*args, **kwargs):
        raise urllib.error.URLError("no route to host")

    monkeypatch.setattr(bmad_method.urllib.request, "urlopen", _raise)
    assert _real_fetch_latest_upstream_version() is None


def test_fetch_latest_upstream_version_folds_http_exception_to_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # http.client.HTTPException (e.g. BadStatusLine/IncompleteRead on a
    # malformed/truncated response) is NOT an OSError subclass, unlike
    # RemoteDisconnected -- review finding, Story 10.2: this failure mode
    # was not caught before and would have escaped to degrade_on_exception,
    # discarding CAP-1's own already-computed Finding too.
    def _raise(*args, **kwargs):
        raise http.client.BadStatusLine("garbage")

    monkeypatch.setattr(bmad_method.urllib.request, "urlopen", _raise)
    assert _real_fetch_latest_upstream_version() is None


def test_fetch_latest_upstream_version_folds_os_error_to_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise(*args, **kwargs):
        raise OSError("connection refused")

    monkeypatch.setattr(bmad_method.urllib.request, "urlopen", _raise)
    assert _real_fetch_latest_upstream_version() is None


def test_fetch_latest_upstream_version_folds_timeout_error_to_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise(*args, **kwargs):
        raise TimeoutError("timed out")

    monkeypatch.setattr(bmad_method.urllib.request, "urlopen", _raise)
    assert _real_fetch_latest_upstream_version() is None


def test_fetch_latest_upstream_version_folds_malformed_json_to_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_urlopen(monkeypatch, b"not json")
    assert _real_fetch_latest_upstream_version() is None


def test_fetch_latest_upstream_version_folds_missing_version_field_to_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_urlopen(monkeypatch, json.dumps({"name": "bmad-method"}).encode())
    assert _real_fetch_latest_upstream_version() is None


def test_fetch_latest_upstream_version_folds_unparseable_version_field_to_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_urlopen(
        monkeypatch,
        json.dumps({"name": "bmad-method", "version": "not-a-version"}).encode(),
    )
    assert _real_fetch_latest_upstream_version() is None


def test_fetch_latest_upstream_version_passes_through_a_custom_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, float] = {}

    def _urlopen(url: str, timeout: float | None = None):
        seen["timeout"] = timeout
        return _FakeUrlopenResponse(
            json.dumps({"name": "bmad-method", "version": "6.12.0"}).encode()
        )

    monkeypatch.setattr(bmad_method.urllib.request, "urlopen", _urlopen)
    _real_fetch_latest_upstream_version(timeout=1.5)
    assert seen["timeout"] == 1.5


# --- helper unit coverage ------------------------------------------------------


def test_parse_version_rejects_non_three_part_string() -> None:
    with pytest.raises(ValueError):
        bmad_method._parse_version("6.11")


def test_parse_version_rejects_non_digit_segment() -> None:
    with pytest.raises(ValueError):
        bmad_method._parse_version("6.x.0")


def test_parse_version_rejects_a_leading_minus_sign() -> None:
    # int("-1") succeeds, so a bare int() conversion would silently accept
    # this -- str.isdigit() is what actually rejects it (review finding).
    with pytest.raises(ValueError):
        bmad_method._parse_version("-1.2.3")


def test_declared_floors_raises_when_bmad_method_absent() -> None:
    with pytest.raises(ValueError):
        bmad_method._declared_floors({"dependencies": {}})


def test_declared_floors_reads_the_top_level_dependencies_table() -> None:
    # No fixture elsewhere in this file declares bmad-method OUTSIDE a
    # [feature.*.dependencies] table -- this exercises that first branch
    # directly (review finding: it was previously unexercised).
    data = {"dependencies": {"bmad-method": ">=6.11.0"}}
    assert bmad_method._declared_floors(data) == [(6, 11, 0)]


def test_declared_floors_picks_max_across_tables() -> None:
    data = {
        "feature": {
            "python": {"dependencies": {"bmad-method": ">=6.11.0"}},
            "local-recipes": {"dependencies": {"bmad-method": ">=6.12.0"}},
        }
    }
    assert bmad_method._declared_floors(data) == [(6, 11, 0), (6, 12, 0)]


def test_declared_floors_reads_top_level_target_scoped_tables() -> None:
    data = {
        "target": {
            "linux-64": {"dependencies": {"bmad-method": ">=6.11.0"}},
        }
    }
    assert bmad_method._declared_floors(data) == [(6, 11, 0)]


def test_declared_floors_reads_feature_target_scoped_tables() -> None:
    # pixi.toml has no bmad-method entry under a
    # [feature.*.target.*.dependencies] table today -- this proves the
    # walk would still see one if it existed (review finding: this shape
    # was previously invisible to _declared_floors entirely).
    data = {
        "feature": {
            "local-recipes": {
                "target": {
                    "win-64": {"dependencies": {"bmad-method": ">=6.13.0"}},
                },
            },
        },
    }
    assert bmad_method._declared_floors(data) == [(6, 13, 0)]


# --- suite upstream comparison (Story 14.1, CAP-4) ------------------------------


#: The one hyphen-rich suite name in the live pins -- exercises the
#: rsplit("-", 2) filename parse where the NAME itself contains hyphens.
_TEA = "bmad-method-test-architecture-enterprise"

# NOTE: this fixture is a RECONSTRUCTION, not a solver-consistent snapshot
# -- it pairs post-update pins (>=0.11.0) with pre-update installed versions
# (0.9.0), a state pixi's solver would never produce. That pairing is
# immaterial to behavior: the pins only DERIVE the watched set (floors are
# never compared by the suite pass), so only the key names matter here.
_PIXI_SUITE_PRE_UPDATE = """
[feature.python.dependencies]
bmad-method = ">=6.11.0"

[feature.local-recipes.dependencies]
bmad-method = ">=6.11.0"
bmad-loop = ">=0.11.0"
bmad-method-test-architecture-enterprise = ">=1.23.2"
"""

_PIXI_SUITE_THREE = """
[feature.python.dependencies]
bmad-method = ">=6.11.0"

[feature.local-recipes.dependencies]
bmad-builder = ">=2.2.1"
bmad-loop = ">=0.11.0"
bmad-method-test-architecture-enterprise = ">=1.23.2"
"""


def _write_conda_meta(target: Path, env: str, name: str, version: str) -> Path:
    """One ``.pixi/envs/<env>/conda-meta/<name>-<version>-<build>.json``
    marker -- the suite pass reads FILENAMES only, so the body stays an
    empty JSON object."""
    path = (
        target / ".pixi" / "envs" / env / "conda-meta"
        / f"{name}-{version}-h0000000_0.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}", encoding="utf-8")
    return path


def _stub_fetch_by_package(
    monkeypatch: pytest.MonkeyPatch,
    versions: dict[str, tuple[int, int, int] | None],
    calls: list[str] | None = None,
) -> None:
    """Per-package fetch stub: returns ``versions.get(package)`` (absent =>
    ``None``, npm's own fail-open shape) and optionally records each
    package queried -- proving WHICH fetches were issued, not just their
    outcomes."""

    def _fetch(
        *, package: str = bmad_method.DEPENDENCY_NAME, timeout: float | None = None
    ) -> tuple[int, int, int] | None:
        if calls is not None:
            calls.append(package)
        return versions.get(package)

    monkeypatch.setattr(bmad_method, "_fetch_latest_upstream_version", _fetch)


class _FakeClock:
    """Replaces ``bmad_method.time`` wholesale (only ``monotonic()`` is
    used there) so the deadline tests control the clock deterministically
    without touching the real ``time`` module."""

    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now


def test_2026_08_21_pre_update_fixture_names_bmad_loop_and_tea(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # THE fixture test: the live 2026-08-21 pre-update state that motivated
    # CAP-4 -- bmad-loop 0.9.0 vs upstream 0.11.0, TEA 1.19.1 vs 1.23.2 --
    # must produce exactly the two suite WARNs a human had to find by hand.
    _write_pixi(tmp_path, _PIXI_SUITE_PRE_UPDATE)
    _write_manifest(tmp_path, _MANIFEST_611)
    _write_conda_meta(tmp_path, "default", "bmad-loop", "0.9.0")
    _write_conda_meta(tmp_path, "default", _TEA, "1.19.1")
    _stub_fetch_by_package(
        monkeypatch,
        {
            "bmad-method": (6, 11, 0),
            "bmad-loop": (0, 11, 0),
            _TEA: (1, 23, 2),
        },
    )

    findings = bmad_method.gather(tmp_path)

    assert [f.check for f in findings] == [
        "bmad-method-version-drift",
        "bmad-method-upstream-drift",
        "bmad-suite-upstream-drift",
        "bmad-suite-upstream-drift",
    ]
    loop_finding, tea_finding = findings[2], findings[3]
    assert loop_finding.source is Source.BMAD_METHOD_VERSION_DRIFT
    assert loop_finding.status is DoctorStatus.WARN
    assert "bmad-loop 0.9.0" in loop_finding.message
    assert "0.11.0" in loop_finding.message
    assert loop_finding.evidence == {
        "package": "bmad-loop",
        "installed": "0.9.0",
        "latest_upstream": "0.11.0",
    }
    assert tea_finding.status is DoctorStatus.WARN
    assert f"{_TEA} 1.19.1" in tea_finding.message
    assert "1.23.2" in tea_finding.message
    assert tea_finding.evidence == {
        "package": _TEA,
        "installed": "1.19.1",
        "latest_upstream": "1.23.2",
    }


def test_all_suite_packages_current_reports_exactly_one_suite_ok_naming_count(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_pixi(tmp_path, _PIXI_SUITE_PRE_UPDATE)
    _write_manifest(tmp_path, _MANIFEST_611)
    _write_conda_meta(tmp_path, "default", "bmad-loop", "0.11.0")
    _write_conda_meta(tmp_path, "default", _TEA, "1.23.2")
    _stub_fetch_by_package(
        monkeypatch,
        {
            "bmad-method": (6, 11, 0),
            "bmad-loop": (0, 11, 0),
            _TEA: (1, 23, 2),
        },
    )

    findings = bmad_method.gather(tmp_path)

    suite = [f for f in findings if f.check == "bmad-suite-upstream-drift"]
    assert len(suite) == 1
    assert suite[0].status is DoctorStatus.OK
    assert "2 checked" in suite[0].message
    assert suite[0].evidence == {"packages_checked": 2, "packages_watched": 2}


def test_mixed_suite_one_behind_one_current_reports_only_the_warn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Mutation-proven gap (review finding): with two packages successfully
    # checked -- one behind, one current -- the suite slice must be EXACTLY
    # the one WARN naming the behind package, and NO suite OK finding may
    # accompany it (a guard bug confined to the mixed branch would swallow
    # the WARN behind an OK while every single-outcome test stays green).
    _write_pixi(tmp_path, _PIXI_SUITE_PRE_UPDATE)
    _write_manifest(tmp_path, _MANIFEST_611)
    _write_conda_meta(tmp_path, "default", "bmad-loop", "0.9.0")
    _write_conda_meta(tmp_path, "default", _TEA, "1.23.2")
    _stub_fetch_by_package(
        monkeypatch,
        {
            "bmad-loop": (0, 11, 0),
            _TEA: (1, 23, 2),
        },
    )

    findings = bmad_method.gather(tmp_path)

    suite = [f for f in findings if f.check == "bmad-suite-upstream-drift"]
    assert [f.status for f in suite] == [DoctorStatus.WARN]
    assert suite[0].evidence == {
        "package": "bmad-loop",
        "installed": "0.9.0",
        "latest_upstream": "0.11.0",
    }


def test_equal_release_triple_with_dev_suffix_counts_as_current(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Comparison is release-triple only: installed 1.2.2.dev0 vs upstream
    # 1.2.2 is CURRENT (warn-only signal, biased against false warns).
    _write_pixi(tmp_path, _PIXI_SUITE_PRE_UPDATE)
    _write_manifest(tmp_path, _MANIFEST_611)
    _write_conda_meta(tmp_path, "default", "bmad-loop", "1.2.2.dev0")
    _stub_fetch_by_package(monkeypatch, {"bmad-loop": (1, 2, 2)})

    findings = bmad_method.gather(tmp_path)

    suite = [f for f in findings if f.check == "bmad-suite-upstream-drift"]
    assert len(suite) == 1
    assert suite[0].status is DoctorStatus.OK
    assert suite[0].evidence == {"packages_checked": 1, "packages_watched": 2}


def test_every_fetch_failing_is_byte_identical_to_cap1_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # I/O matrix "registry unreachable": suite pins present, conda-meta
    # present, every fetch (core AND suite) folds to None -- output is
    # exactly today's CAP-1-only shape, no suite Finding, no error.
    _write_pixi(tmp_path, _PIXI_SUITE_PRE_UPDATE)
    _write_manifest(tmp_path, _MANIFEST_611)
    _write_conda_meta(tmp_path, "default", "bmad-loop", "0.9.0")
    _write_conda_meta(tmp_path, "default", _TEA, "1.19.1")
    _stub_fetch_by_package(monkeypatch, {})

    findings = bmad_method.gather(tmp_path)

    # Full-equality assertion (review finding: len/check/status alone was
    # weaker than this test's own "byte-identical" name).
    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.BMAD_METHOD_VERSION_DRIFT
    assert finding.check == "bmad-method-version-drift"
    assert finding.status is DoctorStatus.OK
    assert finding.message == (
        "installed bmad-method 6.11.0 meets pixi.toml's declared floor >=6.11.0"
    )
    assert finding.evidence == {"installed": "6.11.0", "declared_floor": ">=6.11.0"}


def test_one_package_missing_from_npm_is_skipped_others_compared(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # I/O matrix "404": TEA's fetch folds to None, bmad-loop's resolves --
    # per-package fail-open, so only bmad-loop is compared.
    _write_pixi(tmp_path, _PIXI_SUITE_PRE_UPDATE)
    _write_manifest(tmp_path, _MANIFEST_611)
    _write_conda_meta(tmp_path, "default", "bmad-loop", "0.9.0")
    _write_conda_meta(tmp_path, "default", _TEA, "1.19.1")
    _stub_fetch_by_package(monkeypatch, {"bmad-loop": (0, 11, 0)})

    findings = bmad_method.gather(tmp_path)

    suite = [f for f in findings if f.check == "bmad-suite-upstream-drift"]
    assert len(suite) == 1
    assert suite[0].status is DoctorStatus.WARN
    assert suite[0].evidence["package"] == "bmad-loop"


def test_suite_pass_still_runs_when_cap2_core_fetch_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The restructured early return: CAP-2's own fetch failing used to
    # return (drift_finding,) alone -- the suite pass is independent and
    # its findings must ride that return too.
    _write_pixi(tmp_path, _PIXI_SUITE_PRE_UPDATE)
    _write_manifest(tmp_path, _MANIFEST_611)
    _write_conda_meta(tmp_path, "default", "bmad-loop", "0.9.0")
    _stub_fetch_by_package(monkeypatch, {"bmad-loop": (0, 11, 0)})

    findings = bmad_method.gather(tmp_path)

    assert [f.check for f in findings] == [
        "bmad-method-version-drift",
        "bmad-suite-upstream-drift",
    ]
    assert findings[1].status is DoctorStatus.WARN


def test_no_pixi_envs_directory_issues_zero_suite_fetches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # I/O matrix "fresh clone/CI": pins present, no .pixi at all -- the
    # only fetch issued is CAP-2's own core query, never a suite one.
    _write_pixi(tmp_path, _PIXI_SUITE_PRE_UPDATE)
    _write_manifest(tmp_path, _MANIFEST_611)
    calls: list[str] = []
    _stub_fetch_by_package(monkeypatch, {}, calls=calls)

    findings = bmad_method.gather(tmp_path)

    assert calls == ["bmad-method"]
    assert len(findings) == 1
    assert findings[0].check == "bmad-method-version-drift"


def test_no_suite_pins_besides_the_core_yields_no_suite_finding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # I/O matrix: _PIXI_SINGLE pins only the core -- even with runtime
    # state for an UNPINNED bmad-* package present, the derived watched set
    # is empty and no suite fetch is issued (derive-don't-declare: the pins
    # are the contract, not whatever happens to be installed).
    _write_pixi(tmp_path, _PIXI_SINGLE)
    _write_manifest(tmp_path, _MANIFEST_611)
    _write_conda_meta(tmp_path, "default", "bmad-loop", "0.9.0")
    calls: list[str] = []
    _stub_fetch_by_package(monkeypatch, {"bmad-loop": (0, 11, 0)}, calls=calls)

    findings = bmad_method.gather(tmp_path)

    assert calls == ["bmad-method"]
    assert len(findings) == 1
    assert findings[0].check == "bmad-method-version-drift"


def test_unparseable_installed_version_skips_that_package_silently(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # I/O matrix "weird filename": bmad-loop-garbage-<build>.json parses to
    # no release triple -- that package is skipped (no fetch, no finding).
    _write_pixi(tmp_path, _PIXI_SUITE_PRE_UPDATE)
    _write_manifest(tmp_path, _MANIFEST_611)
    _write_conda_meta(tmp_path, "default", "bmad-loop", "garbage")
    calls: list[str] = []
    _stub_fetch_by_package(monkeypatch, {"bmad-loop": (0, 11, 0)}, calls=calls)

    findings = bmad_method.gather(tmp_path)

    assert calls == ["bmad-method"]
    assert [f.check for f in findings] == ["bmad-method-version-drift"]


def test_suite_deadline_exhausted_mid_loop_skips_the_remaining_packages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # I/O matrix "deadline exhausted": the first fetch consumes the whole
    # 5s budget -- findings appear only for the packages actually checked.
    _write_pixi(tmp_path, _PIXI_SUITE_PRE_UPDATE)
    _write_manifest(tmp_path, _MANIFEST_611)
    _write_conda_meta(tmp_path, "default", "bmad-loop", "0.9.0")
    _write_conda_meta(tmp_path, "default", _TEA, "1.19.1")

    clock = _FakeClock()
    monkeypatch.setattr(bmad_method, "time", clock)
    suite_calls: list[str] = []

    def _slow_fetch(
        *, package: str = bmad_method.DEPENDENCY_NAME, timeout: float | None = None
    ) -> tuple[int, int, int] | None:
        clock.now += 10.0  # every fetch blows straight past the 5s budget
        if package == "bmad-method":
            return None
        suite_calls.append(package)
        return {"bmad-loop": (0, 11, 0), _TEA: (1, 23, 2)}[package]

    monkeypatch.setattr(bmad_method, "_fetch_latest_upstream_version", _slow_fetch)

    findings = bmad_method.gather(tmp_path)

    # Sorted order: bmad-loop is checked first, TEA is skipped unbudgeted.
    assert suite_calls == ["bmad-loop"]
    suite = [f for f in findings if f.check == "bmad-suite-upstream-drift"]
    assert len(suite) == 1
    assert suite[0].evidence["package"] == "bmad-loop"


def test_suite_per_fetch_timeout_is_min_of_remaining_budget_and_ceiling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_pixi(tmp_path, _PIXI_SUITE_THREE)
    _write_manifest(tmp_path, _MANIFEST_611)
    _write_conda_meta(tmp_path, "default", "bmad-builder", "2.2.1")
    _write_conda_meta(tmp_path, "default", "bmad-loop", "0.11.0")
    _write_conda_meta(tmp_path, "default", _TEA, "1.23.2")

    clock = _FakeClock()
    monkeypatch.setattr(bmad_method, "time", clock)
    seen: list[tuple[str, float | None]] = []

    def _fetch(
        *, package: str = bmad_method.DEPENDENCY_NAME, timeout: float | None = None
    ) -> tuple[int, int, int] | None:
        if package != "bmad-method":
            seen.append((package, timeout))
            clock.now += 2.0  # each suite fetch consumes 2s of the 5s budget
        return None

    monkeypatch.setattr(bmad_method, "_fetch_latest_upstream_version", _fetch)

    bmad_method.gather(tmp_path)

    assert seen == [
        ("bmad-builder", 5.0),
        ("bmad-loop", 3.0),
        (_TEA, 1.0),
    ]


def test_suite_pass_internal_failure_never_degrades_cap1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The suite pass's own last-resort net: an unexpected exception inside
    # it folds to "adds nothing" -- it must never reach the outer
    # degrade_on_exception and collapse CAP-1's already-computed Finding.
    _write_pixi(tmp_path, _PIXI_SUITE_PRE_UPDATE)
    _write_manifest(tmp_path, _MANIFEST_611)

    def _boom(pixi_data: dict) -> tuple[str, ...]:
        raise RuntimeError("kaboom")

    monkeypatch.setattr(bmad_method, "_suite_packages", _boom)

    findings = bmad_method.gather(tmp_path)

    assert len(findings) == 1
    assert findings[0].check == "bmad-method-version-drift"
    assert findings[0].status is DoctorStatus.OK


# --- _parse_release_triple / _suite_packages / _installed_suite_versions --------


def test_parse_release_triple_parses_plain_and_suffixed_versions() -> None:
    assert bmad_method._parse_release_triple("0.11.0") == (0, 11, 0)
    assert bmad_method._parse_release_triple("1.2.2.dev0") == (1, 2, 2)
    assert bmad_method._parse_release_triple("3.1.0rc1") == (3, 1, 0)
    assert bmad_method._parse_release_triple(" 6.11.0 ") == (6, 11, 0)
    # A conda epoch prefix is tolerated and ignored for the triple (review
    # finding: rejecting it would permanently exempt the package).
    assert bmad_method._parse_release_triple("1!0.9.0") == (0, 9, 0)


def test_parse_release_triple_returns_none_on_garbage() -> None:
    assert bmad_method._parse_release_triple("garbage") is None
    assert bmad_method._parse_release_triple("1.2") is None
    assert bmad_method._parse_release_triple("v1.2.3") is None
    assert bmad_method._parse_release_triple("") is None


def test_suite_packages_derives_from_every_table_excluding_the_core() -> None:
    data = {
        "dependencies": {"bmad-zeta": ">=1.0"},
        "feature": {
            "python": {
                "dependencies": {
                    "bmad-method": ">=6.11.0",  # the core: excluded
                    "bmad-loop": ">=0.11.0",
                    "pixi": ">=1.0",  # not bmad-*: excluded
                }
            },
            "local-recipes": {
                "dependencies": {"bmad-loop": ">=0.11.0"},  # duplicate: deduped
                "target": {
                    "linux-64": {"dependencies": {"bmad-alpha": ">=0.1"}},
                },
            },
        },
        "target": {"osx-arm64": {"dependencies": {"bmad-beta": ">=0.2"}}},
    }
    assert bmad_method._suite_packages(data) == (
        "bmad-alpha", "bmad-beta", "bmad-loop", "bmad-zeta",
    )


def test_installed_suite_versions_parses_hyphen_rich_names_exactly(
    tmp_path: Path,
) -> None:
    # The filename grammar <name>-<version>-<build>.json is exact even when
    # the NAME contains hyphens (rsplit from the right: conda versions and
    # build strings cannot contain "-").
    _write_conda_meta(tmp_path, "default", _TEA, "1.19.1")
    _write_conda_meta(tmp_path, "default", "bmad-loop", "0.9.0")

    result = bmad_method._installed_suite_versions(tmp_path, (_TEA, "bmad-loop"))

    assert result == {
        _TEA: ((1, 19, 1), "1.19.1"),
        "bmad-loop": ((0, 9, 0), "0.9.0"),
    }


def test_installed_suite_versions_takes_the_newest_triple_across_envs(
    tmp_path: Path,
) -> None:
    _write_conda_meta(tmp_path, "stale-env", "bmad-loop", "0.9.0")
    _write_conda_meta(tmp_path, "fresh-env", "bmad-loop", "0.11.0")

    result = bmad_method._installed_suite_versions(tmp_path, ("bmad-loop",))

    assert result == {"bmad-loop": ((0, 11, 0), "0.11.0")}


def test_installed_suite_versions_returns_empty_without_envs_dir(
    tmp_path: Path,
) -> None:
    assert bmad_method._installed_suite_versions(tmp_path, ("bmad-loop",)) == {}


def test_installed_suite_versions_skips_unwatched_and_unparseable(
    tmp_path: Path,
) -> None:
    _write_conda_meta(tmp_path, "default", "bmad-loop", "garbage")
    _write_conda_meta(tmp_path, "default", "unrelated-package", "1.0.0")

    assert bmad_method._installed_suite_versions(tmp_path, ("bmad-loop",)) == {}


def test_installed_suite_versions_tolerates_real_conda_meta_noise(
    tmp_path: Path,
) -> None:
    # Realistic noise (review finding): every real conda-meta contains a
    # suffix-less `history` file, and .pixi/envs can hold stray
    # non-directory entries -- both must be skipped without error.
    _write_conda_meta(tmp_path, "default", "bmad-loop", "0.9.0")
    history = tmp_path / ".pixi" / "envs" / "default" / "conda-meta" / "history"
    history.write_text("==> 2026-08-21 <==\n", encoding="utf-8")
    stray = tmp_path / ".pixi" / "envs" / "stray-file"
    stray.write_text("not an env directory", encoding="utf-8")

    result = bmad_method._installed_suite_versions(tmp_path, ("bmad-loop",))

    assert result == {"bmad-loop": ((0, 9, 0), "0.9.0")}


# --- the generalized package kwarg's URL construction ---------------------------


def test_fetch_latest_upstream_version_builds_the_per_package_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, str] = {}

    def _urlopen(url: str, timeout: float | None = None) -> _FakeUrlopenResponse:
        seen["url"] = url
        return _FakeUrlopenResponse(
            json.dumps({"name": "bmad-loop", "version": "0.11.0"}).encode()
        )

    monkeypatch.setattr(bmad_method.urllib.request, "urlopen", _urlopen)
    assert _real_fetch_latest_upstream_version(package="bmad-loop") == (0, 11, 0)
    assert seen["url"] == "https://registry.npmjs.org/bmad-loop/latest"


def test_fetch_latest_upstream_version_defaults_to_the_core_package_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, str] = {}

    def _urlopen(url: str, timeout: float | None = None) -> _FakeUrlopenResponse:
        seen["url"] = url
        return _FakeUrlopenResponse(
            json.dumps({"name": "bmad-method", "version": "6.12.0"}).encode()
        )

    monkeypatch.setattr(bmad_method.urllib.request, "urlopen", _urlopen)
    assert _real_fetch_latest_upstream_version() == (6, 12, 0)
    assert seen["url"] == "https://registry.npmjs.org/bmad-method/latest"


def test_fetch_latest_upstream_version_is_lenient_for_suite_strict_for_core(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Symmetric parsing (review finding): a prerelease `latest` must not
    # silently vanish a SUITE package from the pass -- it parses leniently
    # to its leading release triple -- while the CORE package keeps
    # CAP-2's strict _parse_version path and folds the same body to None.
    _stub_urlopen(
        monkeypatch,
        json.dumps({"name": "x", "version": "0.12.0-rc.1"}).encode(),
    )
    assert _real_fetch_latest_upstream_version(package="bmad-loop") == (0, 12, 0)
    assert _real_fetch_latest_upstream_version() is None
