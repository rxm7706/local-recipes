"""Unit tests for ``pyforge.doctor.sources.bmad_method.gather`` (Story 10.1,
Epic 10/CAP-1; Story 10.2, Epic 10/CAP-2; Story 14.1, Epic 14/CAP-4's suite
pass; Story 15.1, Epic 15/DW-14-1-1's GitHub-releases fallback; Story 15.2,
Epic 15/spec-15-2's channel-vs-recipe and recipe-vs-upstream ambient
findings) -- covers every row of the specs' I/O & Edge-Case Matrices against
REAL tmp fixture trees (a written ``pixi.toml`` + ``_bmad/_config/
manifest.yaml``, plus ``.pixi/envs/*/conda-meta/`` filename markers for
CAP-4 and ``recipes/<name>/recipe.yaml`` fixtures for Story 15.1/15.2),
mirroring ``test_sources_chain_due_for_verification.py``'s own real-fixture
discipline.
The exceptions are ``test_gather_degrades_on_unexpected_exception``, which
deliberately monkeypatches ``_gather`` to force an exception shape no real
fixture can produce -- proving the outer ``degrade_on_exception`` safety net
itself, not the comparison logic (review finding: the prior wording claimed
"no mocks" unconditionally) -- and CAP-2/Story 15.1's own network-boundary
tests, which monkeypatch ``_fetch_latest_upstream_version``/
``urllib.request.urlopen`` rather than making a live registry/GitHub call.

The module-level ``_stub_upstream_fetch`` fixture below is ``autouse=True``
so every CAP-1 test above it keeps asserting ``len(findings) == 1``
unmodified, exactly as it did before CAP-2 existed (Boundaries) -- mirrors
this file's own ``test_gather_degrades_on_unexpected_exception`` monkeypatch
idiom, and ``test_sources_chain_due_for_verification.py``'s own
autouse-fixture-per-module convention. ``_stub_channel_fetch`` (Story 15.2,
review pass 2) mirrors it exactly for ``_fetch_channel_version``, so no
future test can accidentally make a live call to ``api.anaconda.org`` by
forgetting to stub it explicitly.
"""

from __future__ import annotations

import email.message
import http.client
import json
import tomllib
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

#: Same precedent as ``_real_fetch_latest_upstream_version`` above, captured
#: before ``_stub_channel_fetch`` (Story 15.2, review pass 2) patches the
#: module attribute of the same name -- the direct ``_fetch_channel_version``
#: unit tests exercise THIS real function object.
_real_fetch_channel_version = bmad_method._fetch_channel_version


@pytest.fixture(autouse=True)
def _stub_upstream_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bmad_method, "_fetch_latest_upstream_version", lambda **_: None)


@pytest.fixture(autouse=True)
def _stub_channel_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bmad_method, "_fetch_channel_version", lambda **_: None)


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


def test_gather_degrades_on_unexpected_exception(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
    monkeypatch.setattr(bmad_method, "_fetch_latest_upstream_version", lambda **_: (6, 12, 0))

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
    monkeypatch.setattr(bmad_method, "_fetch_latest_upstream_version", lambda **_: (6, 12, 0))

    findings = bmad_method.gather(tmp_path)

    assert len(findings) == 2
    assert findings[0].check == "bmad-method-version-drift"
    assert findings[0].status is DoctorStatus.OK
    assert findings[1].check == "bmad-method-upstream-drift"
    assert findings[1].status is DoctorStatus.WARN


def test_installed_equal_to_latest_upstream_reports_second_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_pixi(tmp_path, _PIXI_SINGLE)
    _write_manifest(tmp_path, _MANIFEST_611)
    monkeypatch.setattr(bmad_method, "_fetch_latest_upstream_version", lambda **_: (6, 11, 0))

    findings = bmad_method.gather(tmp_path)

    assert len(findings) == 2
    assert findings[1].check == "bmad-method-upstream-drift"
    assert findings[1].status is DoctorStatus.OK


def test_installed_ahead_of_latest_upstream_reports_second_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # A pre-release/dev install ahead of the latest published release.
    _write_pixi(tmp_path, _PIXI_SINGLE)
    _write_manifest(tmp_path, _MANIFEST_612)
    monkeypatch.setattr(bmad_method, "_fetch_latest_upstream_version", lambda **_: (6, 11, 0))

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


def test_gather_exercises_the_real_fetch_helper_end_to_end(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Every other CAP-2 gather-level test stubs _fetch_latest_upstream_version
    # wholesale, and every direct _fetch_latest_upstream_version test bypasses
    # gather()/_gather() entirely -- neither exercises the seam between the
    # two halves with both sides real (review finding, Story 10.2). This one
    # restores the REAL _fetch_latest_upstream_version (undoing the autouse
    # stub above) and only stubs urlopen, one layer down.
    monkeypatch.setattr(bmad_method, "_fetch_latest_upstream_version", _real_fetch_latest_upstream_version)
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


def test_broken_cap1_inputs_never_reach_the_fetch_helper(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
        bmad_method.urllib.request,
        "urlopen",
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
        raise urllib.error.HTTPError("https://registry.npmjs.org", 500, "boom", email.message.Message(), None)

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
        return _FakeUrlopenResponse(json.dumps({"name": "bmad-method", "version": "6.12.0"}).encode())

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
    path = target / ".pixi" / "envs" / env / "conda-meta" / f"{name}-{version}-h0000000_0.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}", encoding="utf-8")
    return path


def _stub_fetch_by_package(
    monkeypatch: pytest.MonkeyPatch,
    versions: dict[str, tuple[int, int, int] | None],
    calls: list[str] | None = None,
) -> None:
    """Per-package fetch stub for CAP-2's npm seam AND Story 19.1's
    ``_resolve_upstream_latest`` -- both return ``versions.get(package)``
    (absent -> ``None``) and optionally record each package queried."""

    def _fetch(
        *, package: str = bmad_method.DEPENDENCY_NAME, timeout: float | None = None
    ) -> tuple[int, int, int] | None:
        if calls is not None:
            calls.append(package)
        return versions.get(package)

    def _resolve(
        package: str,
        target: Path,
        *,
        timeout: float | None = None,
    ) -> tuple[int, int, int] | None:
        if calls is not None:
            calls.append(package)
        return versions.get(package)

    monkeypatch.setattr(bmad_method, "_fetch_latest_upstream_version", _fetch)
    monkeypatch.setattr(bmad_method, "_resolve_upstream_latest", _resolve)


class _FakeClock:
    """Replaces ``bmad_method.time`` wholesale (only ``monotonic()`` is
    used there) so the deadline tests control the clock deterministically
    without touching the real ``time`` module."""

    def __init__(self) -> None:
        self.now = 0.0

    def monotonic(self) -> float:
        return self.now


def test_2026_08_21_pre_update_fixture_names_bmad_loop_and_tea(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
        "probe_class": "tag",
        "installed": "0.9.0",
        "latest_upstream": "0.11.0",
    }
    assert tea_finding.status is DoctorStatus.WARN
    assert f"{_TEA} 1.19.1" in tea_finding.message
    assert "1.23.2" in tea_finding.message
    assert tea_finding.evidence == {
        "package": _TEA,
        "probe_class": "tag",
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
        "probe_class": "tag",
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


def test_every_fetch_failing_is_byte_identical_to_cap1_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
    assert finding.message == ("installed bmad-method 6.11.0 meets pixi.toml's declared floor >=6.11.0")
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


def test_suite_pass_still_runs_when_cap2_core_fetch_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_no_pixi_envs_directory_issues_zero_suite_fetches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # I/O matrix "fresh clone/CI": pins present, no .pixi at all -- the
    # only fetch issued is CAP-2's own core query, never a suite one.
    _write_pixi(tmp_path, _PIXI_SUITE_PRE_UPDATE)
    _write_manifest(tmp_path, _MANIFEST_611)
    calls: list[str] = []
    _stub_fetch_by_package(monkeypatch, {}, calls=calls)

    findings = bmad_method.gather(tmp_path)

    assert set(calls) <= {"bmad-method"}
    assert calls.count("bmad-method") >= 1
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

    assert set(calls) <= {"bmad-method"}
    assert calls.count("bmad-method") >= 1
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

    assert set(calls) <= {"bmad-method"}
    assert [f.check for f in findings] == ["bmad-method-version-drift"]


def test_suite_deadline_exhausted_mid_loop_skips_the_remaining_packages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # I/O matrix "deadline exhausted": the first resolve consumes the whole
    # (Story 19.1-bumped) 15s budget -- findings appear only for the
    # packages actually checked.
    _write_pixi(tmp_path, _PIXI_SUITE_PRE_UPDATE)
    _write_manifest(tmp_path, _MANIFEST_611)
    _write_conda_meta(tmp_path, "default", "bmad-loop", "0.9.0")
    _write_conda_meta(tmp_path, "default", _TEA, "1.19.1")

    clock = _FakeClock()
    monkeypatch.setattr(bmad_method, "time", clock)
    suite_calls: list[str] = []

    def _slow_resolve(
        package: str,
        target: Path,
        *,
        timeout: float | None = None,
    ) -> tuple[int, int, int] | None:
        if package == "bmad-method":
            return None
        clock.now += 15.0
        suite_calls.append(package)
        return {"bmad-loop": (0, 11, 0), _TEA: (1, 23, 2)}[package]

    monkeypatch.setattr(bmad_method, "_fetch_latest_upstream_version", lambda **_: None)
    monkeypatch.setattr(bmad_method, "_resolve_upstream_latest", _slow_resolve)

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

    def _resolve(
        package: str,
        target: Path,
        *,
        timeout: float | None = None,
    ) -> tuple[int, int, int] | None:
        if package != "bmad-method":
            seen.append((package, timeout))
            # Story 19.1 bumped the shared budget 10.0 -> 15.0; 6.0s/resolve
            # demonstrates both branches of min(remaining, ceiling):
            # the first two calls are capped by the 5.0s ceiling (remaining
            # is still above it), the third is capped by the smaller
            # remaining budget itself (15 - 6 - 6 = 3).
            clock.now += 6.0
        return None

    monkeypatch.setattr(bmad_method, "_fetch_latest_upstream_version", lambda **_: None)
    monkeypatch.setattr(bmad_method, "_resolve_upstream_latest", _resolve)

    bmad_method.gather(tmp_path)

    assert seen == [
        ("bmad-builder", 5.0),
        ("bmad-loop", 5.0),
        (_TEA, 3.0),
    ]


def test_suite_pass_internal_failure_never_degrades_cap1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
        "bmad-alpha",
        "bmad-beta",
        "bmad-loop",
        "bmad-zeta",
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
        return _FakeUrlopenResponse(json.dumps({"name": "bmad-loop", "version": "0.11.0"}).encode())

    monkeypatch.setattr(bmad_method.urllib.request, "urlopen", _urlopen)
    assert _real_fetch_latest_upstream_version(package="bmad-loop") == (0, 11, 0)
    assert seen["url"] == "https://registry.npmjs.org/bmad-loop/latest"


def test_fetch_latest_upstream_version_defaults_to_the_core_package_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, str] = {}

    def _urlopen(url: str, timeout: float | None = None) -> _FakeUrlopenResponse:
        seen["url"] = url
        return _FakeUrlopenResponse(json.dumps({"name": "bmad-method", "version": "6.12.0"}).encode())

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


# --- GitHub-releases fallback for npm-invisible packages (Story 15.1, DW-14-1-1) ---


def _write_recipe_yaml(target: Path, package: str, text: str) -> Path:
    path = target / "recipes" / package / "recipe.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


#: The real 2026-08-21 shape of ``recipes/bmad-loop/recipe.yaml``'s
#: ``extra`` block (DW-14-1-1's own fixture reference) -- see this file's
#: module docstring/Code Map: tests write their own tmp-scoped copy rather
#: than reading the real tracked file.
_RECIPE_GITHUB_BMAD_LOOP = """
extra:
  recipe-maintainers:
    - rxm7706
  cfe-upstream-registry: github
  cfe-upstream-name: bmad-code-org/bmad-loop
"""

_RECIPE_NON_GITHUB = """
extra:
  recipe-maintainers:
    - rxm7706
  cfe-upstream-registry: npm
  cfe-upstream-name: bmad-method
"""

_RECIPE_MALFORMED_YAML = "extra: [unterminated\n"

_RECIPE_MISSING_EXTRA = """
package:
  name: bmad-loop
"""


# --- _github_owner_repo ----------------------------------------------------------


def test_github_owner_repo_returns_the_mapping_on_a_github_hit(tmp_path: Path) -> None:
    _write_recipe_yaml(tmp_path, "bmad-loop", _RECIPE_GITHUB_BMAD_LOOP)
    assert bmad_method._github_owner_repo(tmp_path, "bmad-loop") == "bmad-code-org/bmad-loop"


def test_github_owner_repo_returns_none_for_a_non_github_registry(
    tmp_path: Path,
) -> None:
    _write_recipe_yaml(tmp_path, "bmad-method", _RECIPE_NON_GITHUB)
    assert bmad_method._github_owner_repo(tmp_path, "bmad-method") is None


def test_github_owner_repo_returns_none_when_recipe_yaml_is_missing(
    tmp_path: Path,
) -> None:
    assert bmad_method._github_owner_repo(tmp_path, "bmad-loop") is None


def test_github_owner_repo_returns_none_on_malformed_yaml(tmp_path: Path) -> None:
    _write_recipe_yaml(tmp_path, "bmad-loop", _RECIPE_MALFORMED_YAML)
    assert bmad_method._github_owner_repo(tmp_path, "bmad-loop") is None


def test_github_owner_repo_returns_none_when_extra_block_is_missing(
    tmp_path: Path,
) -> None:
    _write_recipe_yaml(tmp_path, "bmad-loop", _RECIPE_MISSING_EXTRA)
    assert bmad_method._github_owner_repo(tmp_path, "bmad-loop") is None


# --- _source_kind (Story 20.1) ----------------------------------------------------


_RECIPE_COMMIT_PINNED = """
context:
  version: "0.2.0.dev0"
  commit: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa

extra:
  cfe-upstream-registry: github
  cfe-upstream-name: bmad-code-org/bmad-eval-quality
  cfe-source-kind: github-commit
"""

_RECIPE_NPM_REGISTRY = """
extra:
  cfe-upstream-registry: npm
  cfe-upstream-name: bmad-module-skill-forge
  cfe-source-kind: npm-registry
"""


def test_source_kind_returns_the_value_on_a_hit(tmp_path: Path) -> None:
    _write_recipe_yaml(tmp_path, "bmad-eval-quality", _RECIPE_COMMIT_PINNED)
    assert bmad_method._source_kind(tmp_path, "bmad-eval-quality") == "github-commit"


def test_source_kind_returns_none_when_recipe_yaml_is_missing(tmp_path: Path) -> None:
    assert bmad_method._source_kind(tmp_path, "bmad-eval-quality") is None


def test_source_kind_returns_none_on_malformed_yaml(tmp_path: Path) -> None:
    _write_recipe_yaml(tmp_path, "bmad-eval-quality", _RECIPE_MALFORMED_YAML)
    assert bmad_method._source_kind(tmp_path, "bmad-eval-quality") is None


def test_source_kind_returns_none_when_extra_block_is_missing(tmp_path: Path) -> None:
    _write_recipe_yaml(tmp_path, "bmad-eval-quality", _RECIPE_MISSING_EXTRA)
    assert bmad_method._source_kind(tmp_path, "bmad-eval-quality") is None


# --- _probe_class (Story 20.1) ------------------------------------------------------


def test_probe_class_github_commit_source_kind_is_commit_pinned() -> None:
    assert bmad_method._probe_class("github-commit", "github") == "commit-pinned"


def test_probe_class_npm_registry_by_registry_field() -> None:
    assert bmad_method._probe_class(None, "npm") == "npm"


def test_probe_class_npm_registry_by_source_kind_field() -> None:
    assert bmad_method._probe_class("npm-registry", None) == "npm"


def test_probe_class_pypi_registry() -> None:
    assert bmad_method._probe_class(None, "pypi") == "pypi"


def test_probe_class_defaults_to_tag() -> None:
    assert bmad_method._probe_class(None, "github") == "tag"
    assert bmad_method._probe_class(None, None) == "tag"
    assert bmad_method._probe_class("github-tag", "github") == "tag"


def test_probe_class_commit_pinned_takes_priority_over_npm_registry() -> None:
    # A package with BOTH a github-commit source_kind AND an npm registry
    # (no real roster member hits this today) must still resolve to
    # "commit-pinned" -- that check runs FIRST (Boundaries: the fallback
    # ordering is load-bearing).
    assert bmad_method._probe_class("github-commit", "npm") == "commit-pinned"


# --- _recipe_pinned_commit (Story 20.1) ---------------------------------------------


_RECIPE_PINNED_COMMIT_MISSING_COMMIT = """
context:
  version: "0.2.0.dev0"
"""

_RECIPE_PINNED_COMMIT_MISSING_VERSION = """
context:
  commit: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
"""


def test_recipe_pinned_commit_returns_the_raw_dev0_string_and_full_sha_on_a_hit(
    tmp_path: Path,
) -> None:
    _write_recipe_yaml(tmp_path, "bmad-eval-quality", _RECIPE_COMMIT_PINNED)
    assert bmad_method._recipe_pinned_commit(tmp_path, "bmad-eval-quality") == (
        "0.2.0.dev0",
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    )


def test_recipe_pinned_commit_returns_none_when_context_commit_is_missing(
    tmp_path: Path,
) -> None:
    _write_recipe_yaml(tmp_path, "bmad-eval-quality", _RECIPE_PINNED_COMMIT_MISSING_COMMIT)
    assert bmad_method._recipe_pinned_commit(tmp_path, "bmad-eval-quality") is None


def test_recipe_pinned_commit_returns_none_when_context_version_is_missing(
    tmp_path: Path,
) -> None:
    _write_recipe_yaml(tmp_path, "bmad-eval-quality", _RECIPE_PINNED_COMMIT_MISSING_VERSION)
    assert bmad_method._recipe_pinned_commit(tmp_path, "bmad-eval-quality") is None


def test_recipe_pinned_commit_returns_none_when_recipe_yaml_is_missing(
    tmp_path: Path,
) -> None:
    assert bmad_method._recipe_pinned_commit(tmp_path, "bmad-eval-quality") is None


def test_recipe_pinned_commit_returns_none_on_malformed_yaml(tmp_path: Path) -> None:
    _write_recipe_yaml(tmp_path, "bmad-eval-quality", _RECIPE_CONTEXT_MALFORMED_YAML)
    assert bmad_method._recipe_pinned_commit(tmp_path, "bmad-eval-quality") is None


# --- _fetch_default_branch_head_sha (Story 20.1) ------------------------------------


def test_fetch_default_branch_head_sha_returns_the_sha_on_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_urlopen(monkeypatch, json.dumps([{"sha": "b" * 40}]).encode())
    assert bmad_method._fetch_default_branch_head_sha(owner_repo="bmad-code-org/bmad-eval-quality") == "b" * 40


def test_fetch_default_branch_head_sha_builds_the_commits_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, str] = {}

    def _urlopen(url: str, timeout: float | None = None) -> _FakeUrlopenResponse:
        seen["url"] = url
        return _FakeUrlopenResponse(json.dumps([{"sha": "b" * 40}]).encode())

    monkeypatch.setattr(bmad_method.urllib.request, "urlopen", _urlopen)
    bmad_method._fetch_default_branch_head_sha(owner_repo="bmad-code-org/bmad-eval-quality")
    assert seen["url"] == ("https://api.github.com/repos/bmad-code-org/bmad-eval-quality/commits?per_page=1")


@pytest.mark.parametrize(
    "exc",
    [
        urllib.error.HTTPError("https://api.github.com", 404, "Not Found", email.message.Message(), None),
        urllib.error.URLError("no route to host"),
        http.client.BadStatusLine("garbage"),
        OSError("connection refused"),
        TimeoutError("timed out"),
    ],
)
def test_fetch_default_branch_head_sha_folds_every_network_failure_mode_to_none(
    monkeypatch: pytest.MonkeyPatch, exc: BaseException
) -> None:
    def _raise(*args, **kwargs):
        raise exc

    monkeypatch.setattr(bmad_method.urllib.request, "urlopen", _raise)
    assert bmad_method._fetch_default_branch_head_sha(owner_repo="bmad-code-org/bmad-eval-quality") is None


def test_fetch_default_branch_head_sha_folds_malformed_json_to_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_urlopen(monkeypatch, b"not json")
    assert bmad_method._fetch_default_branch_head_sha(owner_repo="bmad-code-org/bmad-eval-quality") is None


def test_fetch_default_branch_head_sha_folds_empty_array_to_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_urlopen(monkeypatch, json.dumps([]).encode())
    assert bmad_method._fetch_default_branch_head_sha(owner_repo="bmad-code-org/bmad-eval-quality") is None


def test_fetch_default_branch_head_sha_folds_missing_sha_key_to_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_urlopen(monkeypatch, json.dumps([{"commit": "no sha field here"}]).encode())
    assert bmad_method._fetch_default_branch_head_sha(owner_repo="bmad-code-org/bmad-eval-quality") is None


def test_fetch_default_branch_head_sha_passes_through_a_custom_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, float] = {}

    def _urlopen(url: str, timeout: float | None = None):
        seen["timeout"] = timeout
        return _FakeUrlopenResponse(json.dumps([{"sha": "b" * 40}]).encode())

    monkeypatch.setattr(bmad_method.urllib.request, "urlopen", _urlopen)
    bmad_method._fetch_default_branch_head_sha(owner_repo="bmad-code-org/bmad-eval-quality", timeout=1.5)
    assert seen["timeout"] == 1.5


# --- _fetch_latest_github_release --------------------------------------------------


def _stub_github_urlopen(
    monkeypatch: pytest.MonkeyPatch,
    *,
    releases: bytes | BaseException | None = None,
    tags: bytes | BaseException | None = None,
) -> None:
    """Dispatches by URL shape: anything containing ``/releases/latest``
    is answered with ``releases``, anything ending ``/tags`` with
    ``tags``. A value that IS an exception instance is raised instead of
    returned, so callers can simulate an HTTPError/URLError/etc. at
    either endpoint. Calling an unstubbed (``None``) endpoint raises --
    proving, for the 404-skips-tags tests, that ``/tags`` was never
    queried at all."""

    def _urlopen(url: str, timeout: float | None = None):
        if "/releases/latest" in url:
            response = releases
        elif url.endswith("/tags"):
            response = tags
        else:
            raise AssertionError(f"unexpected URL: {url}")
        if isinstance(response, BaseException):
            raise response
        if response is None:
            raise AssertionError(f"unstubbed endpoint called: {url}")
        return _FakeUrlopenResponse(response)

    monkeypatch.setattr(bmad_method.urllib.request, "urlopen", _urlopen)


def test_fetch_latest_github_release_returns_parsed_triple_on_a_releases_hit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_github_urlopen(monkeypatch, releases=json.dumps({"tag_name": "0.11.0"}).encode())
    assert bmad_method._fetch_latest_github_release(owner_repo="bmad-code-org/bmad-loop") == (0, 11, 0)


def test_fetch_latest_github_release_falls_back_to_tags_on_a_404(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_github_urlopen(
        monkeypatch,
        releases=urllib.error.HTTPError("https://api.github.com", 404, "Not Found", email.message.Message(), None),
        tags=json.dumps([{"name": "v0.10.0"}, {"name": "v0.11.0"}]).encode(),
    )
    assert bmad_method._fetch_latest_github_release(owner_repo="bmad-code-org/bmad-loop") == (0, 11, 0)


def test_fetch_latest_github_release_a_non_404_http_error_skips_tags_entirely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # `tags` deliberately left unstubbed (None) -- _stub_github_urlopen's
    # own AssertionError proves /tags is never queried on a non-404.
    _stub_github_urlopen(
        monkeypatch,
        releases=urllib.error.HTTPError("https://api.github.com", 500, "boom", email.message.Message(), None),
    )
    assert bmad_method._fetch_latest_github_release(owner_repo="bmad-code-org/bmad-loop") is None


def test_fetch_latest_github_release_strips_one_leading_v_or_capital_v(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_github_urlopen(monkeypatch, releases=json.dumps({"tag_name": "V0.11.0"}).encode())
    assert bmad_method._fetch_latest_github_release(owner_repo="bmad-code-org/bmad-loop") == (0, 11, 0)


def test_fetch_latest_github_release_empty_tags_list_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_github_urlopen(
        monkeypatch,
        releases=urllib.error.HTTPError("https://api.github.com", 404, "Not Found", email.message.Message(), None),
        tags=json.dumps([]).encode(),
    )
    assert bmad_method._fetch_latest_github_release(owner_repo="bmad-labs/skills") is None


def test_fetch_latest_github_release_unparseable_tags_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_github_urlopen(
        monkeypatch,
        releases=urllib.error.HTTPError("https://api.github.com", 404, "Not Found", email.message.Message(), None),
        tags=json.dumps([{"name": "garbage"}, {"name": "also-garbage"}]).encode(),
    )
    assert bmad_method._fetch_latest_github_release(owner_repo="bmad-labs/skills") is None


@pytest.mark.parametrize(
    "exc",
    [
        urllib.error.URLError("no route to host"),
        http.client.BadStatusLine("garbage"),
        OSError("connection refused"),
        TimeoutError("timed out"),
    ],
)
def test_fetch_latest_github_release_folds_every_network_failure_mode_to_none(
    monkeypatch: pytest.MonkeyPatch, exc: BaseException
) -> None:
    def _raise(*args, **kwargs):
        raise exc

    monkeypatch.setattr(bmad_method.urllib.request, "urlopen", _raise)
    assert bmad_method._fetch_latest_github_release(owner_repo="bmad-code-org/bmad-loop") is None


def test_fetch_latest_github_release_folds_malformed_json_to_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_github_urlopen(monkeypatch, releases=b"not json")
    assert bmad_method._fetch_latest_github_release(owner_repo="bmad-code-org/bmad-loop") is None


def test_fetch_latest_github_release_folds_missing_tag_name_field_to_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_github_urlopen(monkeypatch, releases=json.dumps({"name": "not-tag-name"}).encode())
    assert bmad_method._fetch_latest_github_release(owner_repo="bmad-code-org/bmad-loop") is None


def test_fetch_latest_github_release_one_malformed_tag_entry_does_not_discard_the_rest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Review finding (Edge Case Hunter): a single tag entry missing "name"
    # used to raise KeyError inside the parsing comprehension, which
    # propagated to the outer except and discarded every OTHER
    # otherwise-valid parsed tag alongside it. It must now skip only
    # itself.
    _stub_github_urlopen(
        monkeypatch,
        releases=urllib.error.HTTPError("https://api.github.com", 404, "Not Found", email.message.Message(), None),
        tags=json.dumps([{"name": "v0.10.0"}, {"no_name_field": True}, {"name": "v0.11.0"}]).encode(),
    )
    assert bmad_method._fetch_latest_github_release(owner_repo="bmad-code-org/bmad-loop") == (0, 11, 0)


def test_fetch_latest_github_release_bounds_the_tags_call_to_the_remaining_deadline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Review finding (Edge Case Hunter + Verification Gap): reusing the
    # SAME full timeout for both the releases/latest call and the /tags
    # fallback could double one package's worst-case duration against the
    # caller's shared per-package budget. The /tags call must receive
    # only what remains of the original timeout, not the full value again.
    clock_values = iter([0.0, 4.0])  # 4s elapsed during the releases/latest call
    monkeypatch.setattr(bmad_method.time, "monotonic", lambda: next(clock_values, 4.0))
    seen: dict[str, float] = {}

    def _urlopen(url: str, timeout: float | None = None):
        if "/releases/latest" in url:
            raise urllib.error.HTTPError("https://api.github.com", 404, "Not Found", email.message.Message(), None)
        seen["timeout"] = timeout
        return _FakeUrlopenResponse(json.dumps([{"name": "v0.11.0"}]).encode())

    monkeypatch.setattr(bmad_method.urllib.request, "urlopen", _urlopen)
    result = bmad_method._fetch_latest_github_release(owner_repo="bmad-code-org/bmad-loop", timeout=5.0)
    assert result == (0, 11, 0)
    assert seen["timeout"] == pytest.approx(1.0)  # 5.0 - 4.0 elapsed, not 5.0 again


def test_fetch_latest_github_release_skips_tags_entirely_once_deadline_is_exhausted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock_values = iter([0.0, 5.0])  # the full 5.0s timeout already elapsed
    monkeypatch.setattr(bmad_method.time, "monotonic", lambda: next(clock_values, 5.0))

    def _urlopen(url: str, timeout: float | None = None):
        if "/releases/latest" in url:
            raise urllib.error.HTTPError("https://api.github.com", 404, "Not Found", email.message.Message(), None)
        raise AssertionError("/tags must not be called once the deadline is exhausted")

    monkeypatch.setattr(bmad_method.urllib.request, "urlopen", _urlopen)
    assert bmad_method._fetch_latest_github_release(owner_repo="bmad-code-org/bmad-loop", timeout=5.0) is None


def test_github_owner_repo_folds_an_unrepresentable_path_to_none(
    tmp_path: Path,
) -> None:
    # Review finding (Edge Case Hunter): an embedded NUL byte in the
    # package name raises ValueError when building/reading the path, not
    # OSError -- this function's own docstring promises "never raises"
    # unconditionally, so ValueError must fold to None too.
    assert bmad_method._github_owner_repo(tmp_path, "bmad-\x00loop") is None


# --- THE DW-14-1-1 fixture: bmad-loop unblinded via GitHub ------------------------


def test_dw_14_1_1_bmad_loop_npm_invisible_resolves_via_github(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # THE fixture named by DW-14-1-1: bmad-loop 404s on npm (as it does
    # live) but its recipes/bmad-loop/recipe.yaml carries a real github
    # mapping -- the fallback must resolve it and produce the SAME WARN
    # shape CAP-4's own npm-sourced WARN already produces.
    _write_pixi(tmp_path, _PIXI_SUITE_PRE_UPDATE)
    _write_manifest(tmp_path, _MANIFEST_611)
    _write_conda_meta(tmp_path, "default", "bmad-loop", "0.9.0")
    _write_recipe_yaml(tmp_path, "bmad-loop", _RECIPE_GITHUB_BMAD_LOOP)
    _stub_fetch_by_package(monkeypatch, {"bmad-method": (6, 11, 0), "bmad-loop": (0, 11, 0)})

    findings = bmad_method.gather(tmp_path)

    suite = [f for f in findings if f.check == "bmad-suite-upstream-drift"]
    assert len(suite) == 1
    finding = suite[0]
    assert finding.source is Source.BMAD_METHOD_VERSION_DRIFT
    assert finding.status is DoctorStatus.WARN
    assert "bmad-loop 0.9.0" in finding.message
    assert "0.11.0" in finding.message
    assert finding.evidence == {
        "package": "bmad-loop",
        "probe_class": "tag",
        "installed": "0.9.0",
        "latest_upstream": "0.11.0",
    }


# --- integration: when the fallback fires (and does not) -------------------------


def test_github_primary_skips_npm_when_registry_is_github(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Story 19.1: github-canonical packages query GitHub only -- never npm,
    # even when a stale npm stub would have looked "current".
    _write_pixi(tmp_path, _PIXI_SUITE_PRE_UPDATE)
    _write_manifest(tmp_path, _MANIFEST_611)
    _write_conda_meta(tmp_path, "default", "bmad-loop", "0.11.0")
    _write_recipe_yaml(tmp_path, "bmad-loop", _RECIPE_GITHUB_BMAD_LOOP)
    calls: list[str] = []
    _stub_fetch_by_package(
        monkeypatch,
        {"bmad-method": (6, 11, 0), "bmad-loop": (0, 11, 0)},
        calls=calls,
    )

    findings = bmad_method.gather(tmp_path)

    suite = [f for f in findings if f.check == "bmad-suite-upstream-drift"]
    assert len(suite) == 1
    assert suite[0].status is DoctorStatus.OK
    assert "bmad-loop" in calls
    assert calls.count("bmad-loop") == 1


def test_github_not_queried_when_no_recipe_yaml_mapping_exists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # bmad-loop is npm-invisible AND has no recipes/bmad-loop/recipe.yaml
    # anywhere under this fixture root -- the fallback must not fire, and
    # bmad-loop stays unchecked exactly as it did before this story.
    _write_pixi(tmp_path, _PIXI_SUITE_PRE_UPDATE)
    _write_manifest(tmp_path, _MANIFEST_611)
    _write_conda_meta(tmp_path, "default", "bmad-loop", "0.9.0")
    _stub_fetch_by_package(monkeypatch, {"bmad-method": (6, 11, 0)})

    def _unreachable(**_):
        raise AssertionError("_fetch_latest_github_release must not be called")

    monkeypatch.setattr(bmad_method, "_fetch_latest_github_release", _unreachable)

    findings = bmad_method.gather(tmp_path)

    assert [f.check for f in findings] == [
        "bmad-method-version-drift",
        "bmad-method-upstream-drift",
    ]


def test_github_resolve_skipped_when_shared_budget_already_exhausted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Story 19.1: a slow github-primary resolve consumes the whole shared
    # 15s budget -- remaining packages are skipped unbudgeted.
    _write_pixi(tmp_path, _PIXI_SUITE_PRE_UPDATE)
    _write_manifest(tmp_path, _MANIFEST_611)
    _write_conda_meta(tmp_path, "default", "bmad-loop", "0.9.0")
    _write_conda_meta(tmp_path, "default", _TEA, "1.19.1")
    _write_recipe_yaml(tmp_path, "bmad-loop", _RECIPE_GITHUB_BMAD_LOOP)

    clock = _FakeClock()
    monkeypatch.setattr(bmad_method, "time", clock)
    resolve_calls: list[str] = []

    def _slow_resolve(
        package: str,
        target: Path,
        *,
        timeout: float | None = None,
    ) -> tuple[int, int, int] | None:
        resolve_calls.append(package)
        if package == "bmad-method":
            return (6, 11, 0)
        clock.now += 15.0
        return (0, 11, 0) if package == "bmad-loop" else None

    monkeypatch.setattr(
        bmad_method,
        "_fetch_latest_upstream_version",
        lambda **_: (6, 11, 0),
    )
    monkeypatch.setattr(bmad_method, "_resolve_upstream_latest", _slow_resolve)

    findings = bmad_method.gather(tmp_path)

    assert resolve_calls == ["bmad-loop", "bmad-method"]
    suite = [f for f in findings if f.check == "bmad-suite-upstream-drift"]
    assert len(suite) == 1
    assert suite[0].status is DoctorStatus.WARN
    assert suite[0].evidence["package"] == "bmad-loop"


def test_packages_checked_rises_when_npm_invisible_package_resolves_via_github(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # bmad-loop is npm-invisible and resolves only via GitHub; TEA resolves
    # via npm directly -- both current -- packages_checked must count BOTH,
    # rising from the pre-story "1 checked of 2 watched" shape.
    _write_pixi(tmp_path, _PIXI_SUITE_PRE_UPDATE)
    _write_manifest(tmp_path, _MANIFEST_611)
    _write_conda_meta(tmp_path, "default", "bmad-loop", "0.11.0")
    _write_conda_meta(tmp_path, "default", _TEA, "1.23.2")
    _write_recipe_yaml(tmp_path, "bmad-loop", _RECIPE_GITHUB_BMAD_LOOP)
    _stub_fetch_by_package(
        monkeypatch,
        {"bmad-method": (6, 11, 0), "bmad-loop": (0, 11, 0), _TEA: (1, 23, 2)},
    )

    findings = bmad_method.gather(tmp_path)

    suite = [f for f in findings if f.check == "bmad-suite-upstream-drift"]
    assert len(suite) == 1
    assert suite[0].status is DoctorStatus.OK
    assert "2 checked" in suite[0].message
    assert suite[0].evidence == {"packages_checked": 2, "packages_watched": 2}


# --- channel and recipe staleness (Story 15.2, spec-15-2) -----------------------


_RECIPE_CONTEXT_611 = """
context:
  name: bmad-method
  version: "6.11.0"
"""

_RECIPE_CONTEXT_610 = """
context:
  name: bmad-method
  version: "6.10.0"
"""

_RECIPE_CONTEXT_MISSING_VERSION = """
context:
  name: bmad-method
"""

_RECIPE_CONTEXT_MISSING_ENTIRELY = """
package:
  name: bmad-method
"""

_RECIPE_CONTEXT_MALFORMED_YAML = "context: [unterminated\n"

_RECIPE_CONTEXT_NON_STRING_VERSION = """
context:
  name: bmad-method
  version: true
"""


# --- _recipe_version --------------------------------------------------------------


def test_recipe_version_returns_parsed_triple_on_a_hit(tmp_path: Path) -> None:
    _write_recipe_yaml(tmp_path, "bmad-method", _RECIPE_CONTEXT_611)
    assert bmad_method._recipe_version(tmp_path, "bmad-method") == (6, 11, 0)


def test_recipe_version_returns_none_when_recipe_yaml_is_missing(
    tmp_path: Path,
) -> None:
    assert bmad_method._recipe_version(tmp_path, "bmad-method") is None


def test_recipe_version_returns_none_when_context_block_is_missing(
    tmp_path: Path,
) -> None:
    _write_recipe_yaml(tmp_path, "bmad-method", _RECIPE_CONTEXT_MISSING_ENTIRELY)
    assert bmad_method._recipe_version(tmp_path, "bmad-method") is None


def test_recipe_version_returns_none_when_version_key_is_missing(
    tmp_path: Path,
) -> None:
    _write_recipe_yaml(tmp_path, "bmad-method", _RECIPE_CONTEXT_MISSING_VERSION)
    assert bmad_method._recipe_version(tmp_path, "bmad-method") is None


def test_recipe_version_returns_none_on_malformed_yaml(tmp_path: Path) -> None:
    _write_recipe_yaml(tmp_path, "bmad-method", _RECIPE_CONTEXT_MALFORMED_YAML)
    assert bmad_method._recipe_version(tmp_path, "bmad-method") is None


def test_recipe_version_returns_none_on_a_non_string_unparseable_version(
    tmp_path: Path,
) -> None:
    _write_recipe_yaml(tmp_path, "bmad-method", _RECIPE_CONTEXT_NON_STRING_VERSION)
    assert bmad_method._recipe_version(tmp_path, "bmad-method") is None


# --- _fetch_channel_version --------------------------------------------------------


def test_fetch_channel_version_returns_parsed_tuple_on_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_urlopen(monkeypatch, json.dumps({"latest_version": "6.3.0"}).encode())
    assert _real_fetch_channel_version(package="bmad-method") == (6, 3, 0)


def test_fetch_channel_version_builds_the_channel_and_package_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, str] = {}

    def _urlopen(url: str, timeout: float | None = None) -> _FakeUrlopenResponse:
        seen["url"] = url
        return _FakeUrlopenResponse(json.dumps({"latest_version": "6.3.0"}).encode())

    monkeypatch.setattr(bmad_method.urllib.request, "urlopen", _urlopen)
    _real_fetch_channel_version(package="bmad-method")
    assert seen["url"] == "https://api.anaconda.org/package/SelfExplainML/bmad-method"


def test_fetch_channel_version_folds_http_404_to_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise(*args, **kwargs):
        raise urllib.error.HTTPError("https://api.anaconda.org", 404, "Not Found", email.message.Message(), None)

    monkeypatch.setattr(bmad_method.urllib.request, "urlopen", _raise)
    assert _real_fetch_channel_version(package="bmad-loop") is None


def test_fetch_channel_version_folds_malformed_json_to_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_urlopen(monkeypatch, b"not json")
    assert _real_fetch_channel_version(package="bmad-method") is None


def test_fetch_channel_version_folds_missing_latest_version_field_to_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_urlopen(monkeypatch, json.dumps({"name": "bmad-method"}).encode())
    assert _real_fetch_channel_version(package="bmad-method") is None


def test_fetch_channel_version_is_lenient_for_a_prerelease_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _stub_urlopen(monkeypatch, json.dumps({"latest_version": "0.12.0-rc.1"}).encode())
    assert _real_fetch_channel_version(package="bmad-loop") == (0, 12, 0)


@pytest.mark.parametrize(
    "exc",
    [
        urllib.error.URLError("no route to host"),
        http.client.BadStatusLine("garbage"),
        OSError("connection refused"),
        TimeoutError("timed out"),
    ],
)
def test_fetch_channel_version_folds_every_network_failure_mode_to_none(
    monkeypatch: pytest.MonkeyPatch, exc: BaseException
) -> None:
    def _raise(*args, **kwargs):
        raise exc

    monkeypatch.setattr(bmad_method.urllib.request, "urlopen", _raise)
    assert _real_fetch_channel_version(package="bmad-method") is None


def test_fetch_channel_version_passes_through_a_custom_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, float] = {}

    def _urlopen(url: str, timeout: float | None = None):
        seen["timeout"] = timeout
        return _FakeUrlopenResponse(json.dumps({"latest_version": "6.3.0"}).encode())

    monkeypatch.setattr(bmad_method.urllib.request, "urlopen", _urlopen)
    _real_fetch_channel_version(package="bmad-method", timeout=1.5)
    assert seen["timeout"] == 1.5


# --- THE 6.3.0-relic fixture: CORE channel-drift -----------------------------------


def test_the_6_3_0_relic_fixture_fires_channel_drift_warn(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # THE fixture named by the story: the channel served a stale
    # bmad-method 6.3.0 for four months while the tracked recipe had
    # already moved to 6.11.0, with no ambient signal until this check.
    _write_pixi(tmp_path, _PIXI_SINGLE)
    _write_manifest(tmp_path, _MANIFEST_611)
    _write_recipe_yaml(tmp_path, "bmad-method", _RECIPE_CONTEXT_611)
    _stub_fetch_by_package(monkeypatch, {"bmad-method": (6, 11, 0)})
    monkeypatch.setattr(bmad_method, "_fetch_channel_version", lambda **_: (6, 3, 0))

    findings = bmad_method.gather(tmp_path)

    channel = [f for f in findings if f.check == "bmad-channel-drift"]
    assert len(channel) == 1
    finding = channel[0]
    assert finding.source is Source.BMAD_METHOD_VERSION_DRIFT
    assert finding.status is DoctorStatus.WARN
    assert "bmad-method" in finding.message
    assert "6.3.0" in finding.message
    assert "6.11.0" in finding.message
    assert finding.evidence == {
        "package": "bmad-method",
        "channel_version": "6.3.0",
        "recipe_version": "6.11.0",
    }
    # No recipe-upstream-drift alongside it: the recipe matches upstream.
    assert not [f for f in findings if f.check == "bmad-recipe-upstream-drift"]


# --- recipe-vs-upstream drift -------------------------------------------------------


def test_recipe_behind_upstream_fires_recipe_upstream_drift_warn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_pixi(tmp_path, _PIXI_SINGLE)
    _write_manifest(tmp_path, _MANIFEST_611)
    _write_recipe_yaml(tmp_path, "bmad-method", _RECIPE_CONTEXT_610)
    _stub_fetch_by_package(monkeypatch, {"bmad-method": (6, 11, 0)})
    monkeypatch.setattr(bmad_method, "_fetch_channel_version", lambda **_: (6, 10, 0))

    findings = bmad_method.gather(tmp_path)

    recipe_drift = [f for f in findings if f.check == "bmad-recipe-upstream-drift"]
    assert len(recipe_drift) == 1
    finding = recipe_drift[0]
    assert finding.status is DoctorStatus.WARN
    assert "bmad-method" in finding.message
    assert "6.10.0" in finding.message
    assert "6.11.0" in finding.message
    assert finding.evidence == {
        "package": "bmad-method",
        "recipe_version": "6.10.0",
        "latest_upstream": "6.11.0",
    }
    # Channel matches the recipe exactly -- no channel-drift alongside it.
    assert not [f for f in findings if f.check == "bmad-channel-drift"]


def test_core_both_new_findings_fire_simultaneously(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Both new checks can fire together at the CORE call site: channel
    # behind recipe AND recipe behind upstream in the same gather() call --
    # only tested for a suite package before this (review pass 2, low).
    _write_pixi(tmp_path, _PIXI_SINGLE)
    _write_manifest(tmp_path, _MANIFEST_611)
    _write_recipe_yaml(tmp_path, "bmad-method", 'context:\n  name: bmad-method\n  version: "6.10.0"\n')
    _stub_fetch_by_package(monkeypatch, {"bmad-method": (6, 11, 0)})
    monkeypatch.setattr(bmad_method, "_fetch_channel_version", lambda **_: (6, 9, 0))

    findings = bmad_method.gather(tmp_path)

    channel = [f for f in findings if f.check == "bmad-channel-drift"]
    recipe_drift = [f for f in findings if f.check == "bmad-recipe-upstream-drift"]
    assert len(channel) == 1
    assert channel[0].evidence == {
        "package": "bmad-method",
        "channel_version": "6.9.0",
        "recipe_version": "6.10.0",
    }
    assert len(recipe_drift) == 1
    assert recipe_drift[0].evidence == {
        "package": "bmad-method",
        "recipe_version": "6.10.0",
        "latest_upstream": "6.11.0",
    }


def test_channel_recipe_upstream_all_agree_fires_neither_new_finding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_pixi(tmp_path, _PIXI_SINGLE)
    _write_manifest(tmp_path, _MANIFEST_611)
    _write_recipe_yaml(tmp_path, "bmad-method", _RECIPE_CONTEXT_611)
    _stub_fetch_by_package(monkeypatch, {"bmad-method": (6, 11, 0)})
    monkeypatch.setattr(bmad_method, "_fetch_channel_version", lambda **_: (6, 11, 0))

    findings = bmad_method.gather(tmp_path)

    assert not [f for f in findings if f.check in ("bmad-channel-drift", "bmad-recipe-upstream-drift")]


# --- fail-open edge cases ------------------------------------------------------------


def test_missing_recipe_yaml_skips_both_new_findings_without_a_channel_fetch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_pixi(tmp_path, _PIXI_SINGLE)
    _write_manifest(tmp_path, _MANIFEST_611)
    _stub_fetch_by_package(monkeypatch, {"bmad-method": (6, 12, 0)})

    def _unreachable(**_):
        raise AssertionError("_fetch_channel_version must not be called")

    monkeypatch.setattr(bmad_method, "_fetch_channel_version", _unreachable)

    findings = bmad_method.gather(tmp_path)

    assert not [f for f in findings if f.check in ("bmad-channel-drift", "bmad-recipe-upstream-drift")]


def test_channel_404_skips_only_channel_drift(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_pixi(tmp_path, _PIXI_SINGLE)
    _write_manifest(tmp_path, _MANIFEST_611)
    _write_recipe_yaml(tmp_path, "bmad-method", _RECIPE_CONTEXT_610)
    _stub_fetch_by_package(monkeypatch, {"bmad-method": (6, 11, 0)})
    # Restore the REAL _fetch_channel_version (undoing the autouse stub) so
    # this test exercises the actual urlopen-404 fold-to-None path, not just
    # the autouse default -- mirrors test_gather_exercises_the_real_fetch_
    # helper_end_to_end's own idiom for the npm/GitHub seam.
    monkeypatch.setattr(bmad_method, "_fetch_channel_version", _real_fetch_channel_version)

    def _raise(*args, **kwargs):
        raise urllib.error.HTTPError("https://api.anaconda.org", 404, "Not Found", email.message.Message(), None)

    monkeypatch.setattr(bmad_method.urllib.request, "urlopen", _raise)

    findings = bmad_method.gather(tmp_path)

    assert not [f for f in findings if f.check == "bmad-channel-drift"]
    recipe_drift = [f for f in findings if f.check == "bmad-recipe-upstream-drift"]
    assert len(recipe_drift) == 1


def test_upstream_unresolved_skips_both_new_findings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Autouse fixture already stubs _fetch_latest_upstream_version to
    # return None for every package -- CAP-2's own early return means the
    # CORE-level new checks are never attempted.
    _write_pixi(tmp_path, _PIXI_SINGLE)
    _write_manifest(tmp_path, _MANIFEST_611)
    _write_recipe_yaml(tmp_path, "bmad-method", _RECIPE_CONTEXT_611)

    def _unreachable(**_):
        raise AssertionError("_fetch_channel_version must not be called")

    monkeypatch.setattr(bmad_method, "_fetch_channel_version", _unreachable)

    findings = bmad_method.gather(tmp_path)

    assert [f.check for f in findings] == ["bmad-method-version-drift"]


def test_suite_package_with_unresolved_upstream_skips_both_new_findings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A suite package whose upstream resolves to None (npm miss AND no
    # GitHub fallback mapping) must skip both new checks too -- only tested
    # at the CORE call site before this
    # (test_upstream_unresolved_skips_both_new_findings, review pass 2, low).
    _write_pixi(tmp_path, _PIXI_SUITE_PRE_UPDATE)
    _write_manifest(tmp_path, _MANIFEST_611)
    _write_conda_meta(tmp_path, "default", "bmad-loop", "0.9.0")
    _write_recipe_yaml(tmp_path, "bmad-loop", 'context:\n  name: bmad-loop\n  version: "0.9.0"\n')
    # bmad-loop is absent from this dict -- npm misses; no `extra` block in
    # the recipe.yaml above means the GitHub fallback misses too, so
    # `latest` stays None for bmad-loop and the package is skipped before
    # `checked += 1` is ever reached.
    _stub_fetch_by_package(monkeypatch, {"bmad-method": (6, 11, 0)})

    def _unreachable(**_):
        raise AssertionError("_fetch_channel_version must not be called")

    monkeypatch.setattr(bmad_method, "_fetch_channel_version", _unreachable)

    findings = bmad_method.gather(tmp_path)

    assert not [f for f in findings if f.check in ("bmad-channel-drift", "bmad-recipe-upstream-drift")]
    # bmad-loop is never "checked" either -- no suite-upstream-drift
    # Finding at all, matching the pre-15.2 "unresolved" shape.
    assert [f.check for f in findings] == [
        "bmad-method-version-drift",
        "bmad-method-upstream-drift",
    ]


def test_channel_fetch_offline_degrades_silently_rest_of_gather_unaffected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_pixi(tmp_path, _PIXI_SUITE_PRE_UPDATE)
    _write_manifest(tmp_path, _MANIFEST_611)
    _write_recipe_yaml(tmp_path, "bmad-method", _RECIPE_CONTEXT_611)
    _write_conda_meta(tmp_path, "default", "bmad-loop", "0.9.0")
    _stub_fetch_by_package(monkeypatch, {"bmad-method": (6, 11, 0), "bmad-loop": (0, 11, 0)})
    # Restore the REAL _fetch_channel_version (undoing the autouse stub) so
    # this test exercises the actual urlopen-URLError fold-to-None path.
    monkeypatch.setattr(bmad_method, "_fetch_channel_version", _real_fetch_channel_version)

    def _raise(*args, **kwargs):
        raise urllib.error.URLError("no route to host")

    monkeypatch.setattr(bmad_method.urllib.request, "urlopen", _raise)

    findings = bmad_method.gather(tmp_path)

    assert not [f for f in findings if f.check == "bmad-channel-drift"]
    assert [f.check for f in findings] == [
        "bmad-method-version-drift",
        "bmad-method-upstream-drift",
        "bmad-suite-upstream-drift",
    ]
    assert findings[2].status is DoctorStatus.WARN


# --- suite-side wiring (call site (b) in _gather_suite_findings) ------------------


def test_suite_package_channel_and_recipe_drift_both_fire(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Wiring point (b): the suite loop's per-package call reuses that
    # iteration's own already-resolved `latest`, exactly like the CORE call
    # site -- a suite package can fire both new checks too, not just CORE.
    _write_pixi(tmp_path, _PIXI_SUITE_PRE_UPDATE)
    _write_manifest(tmp_path, _MANIFEST_611)
    _write_conda_meta(tmp_path, "default", "bmad-loop", "0.11.0")
    _write_recipe_yaml(tmp_path, "bmad-loop", 'context:\n  name: bmad-loop\n  version: "0.10.0"\n')
    _stub_fetch_by_package(monkeypatch, {"bmad-method": (6, 11, 0), "bmad-loop": (0, 11, 0)})
    monkeypatch.setattr(bmad_method, "_fetch_channel_version", lambda **_: (0, 9, 0))

    findings = bmad_method.gather(tmp_path)

    channel = [f for f in findings if f.check == "bmad-channel-drift"]
    recipe_drift = [f for f in findings if f.check == "bmad-recipe-upstream-drift"]
    assert len(channel) == 1
    assert channel[0].evidence["package"] == "bmad-loop"
    assert len(recipe_drift) == 1
    assert recipe_drift[0].evidence["package"] == "bmad-loop"
    # bmad-loop's own installed version (0.11.0) matches its resolved
    # upstream latest (0.11.0) exactly -- its OWN axis is clean, so the
    # pre-existing bmad-suite-upstream-drift OK/summary Finding must still
    # fire ALONGSIDE the two new WARNs (review pass 2, HIGH regression:
    # this used to be silently swallowed -- see the dedicated regression
    # test below for the isolated repro).
    suite = [f for f in findings if f.check == "bmad-suite-upstream-drift"]
    assert len(suite) == 1
    assert suite[0].status is DoctorStatus.OK
    assert suite[0].evidence == {"packages_checked": 1, "packages_watched": 2}


def test_clean_suite_upstream_axis_still_fires_ok_alongside_a_new_warn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # THE review-pass-2 HIGH regression, isolated: bmad-loop installed
    # EXACTLY at its resolved upstream latest (a genuinely clean
    # suite-upstream-drift axis) while its recipe.yaml is one version
    # behind that same upstream (a drifting recipe-upstream-drift axis).
    # Before the fix, appending the new finding into the SAME
    # `warn_findings` list that gates the WARN-vs-OK branch made
    # `warn_findings` non-empty from the new finding ALONE, so the
    # `bmad-suite-upstream-drift` OK/summary Finding was silently dropped
    # entirely (neither WARN nor OK) -- confirmed by direct repro during
    # review pass 2.
    _write_pixi(tmp_path, _PIXI_SUITE_PRE_UPDATE)
    _write_manifest(tmp_path, _MANIFEST_611)
    _write_conda_meta(tmp_path, "default", "bmad-loop", "0.11.0")
    _write_recipe_yaml(tmp_path, "bmad-loop", 'context:\n  name: bmad-loop\n  version: "0.10.0"\n')
    _stub_fetch_by_package(monkeypatch, {"bmad-method": (6, 11, 0), "bmad-loop": (0, 11, 0)})
    # Channel matches the recipe exactly -- only ONE new finding
    # (bmad-recipe-upstream-drift) fires, isolating the regression from
    # the "both new findings fire" scenario the test above already covers.
    monkeypatch.setattr(bmad_method, "_fetch_channel_version", lambda **_: (0, 10, 0))

    findings = bmad_method.gather(tmp_path)

    recipe_drift = [f for f in findings if f.check == "bmad-recipe-upstream-drift"]
    assert len(recipe_drift) == 1
    assert not [f for f in findings if f.check == "bmad-channel-drift"]

    suite = [f for f in findings if f.check == "bmad-suite-upstream-drift"]
    assert len(suite) == 1
    assert suite[0].status is DoctorStatus.OK
    assert suite[0].evidence == {"packages_checked": 1, "packages_watched": 2}


def test_suite_channel_fetch_draws_from_the_same_shared_budget(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # The budget-repair scenario itself (Spec Change Log): the new
    # per-package channel fetch shares the SAME _SUITE_FETCH_TOTAL_BUDGET_
    # SECONDS deadline as the pre-existing npm/GitHub upstream check -- a
    # slow channel fetch for an early package can still exhaust the (now
    # doubled) pool before a later package gets its own upstream check.
    _write_pixi(tmp_path, _PIXI_SUITE_THREE)
    _write_manifest(tmp_path, _MANIFEST_611)
    _write_conda_meta(tmp_path, "default", "bmad-builder", "2.2.1")
    _write_conda_meta(tmp_path, "default", "bmad-loop", "0.11.0")
    _write_conda_meta(tmp_path, "default", _TEA, "1.23.2")
    _write_recipe_yaml(
        tmp_path,
        "bmad-builder",
        'context:\n  name: bmad-builder\n  version: "2.2.1"\n',
    )

    clock = _FakeClock()
    monkeypatch.setattr(bmad_method, "time", clock)
    npm_calls: list[str] = []

    def _resolve(
        package: str,
        target: Path,
        *,
        timeout: float | None = None,
    ) -> tuple[int, int, int] | None:
        if package != "bmad-method":
            npm_calls.append(package)
        return {
            "bmad-builder": (2, 2, 1),
            "bmad-loop": (0, 11, 0),
            _TEA: (1, 23, 2),
        }.get(package)

    def _slow_channel_fetch(*, package: str, timeout: float | None = None) -> tuple[int, int, int] | None:
        clock.now += 15.0  # exhausts the (Story 19.1-bumped) 15.0s shared budget alone
        return (2, 2, 1)

    monkeypatch.setattr(bmad_method, "_fetch_latest_upstream_version", lambda **_: (6, 11, 0))
    monkeypatch.setattr(bmad_method, "_resolve_upstream_latest", _resolve)
    monkeypatch.setattr(bmad_method, "_fetch_channel_version", _slow_channel_fetch)

    findings = bmad_method.gather(tmp_path)

    # bmad-builder is checked (and its slow channel fetch runs); the shared
    # budget is exhausted afterward, so neither bmad-loop nor TEA get their
    # own npm/GitHub upstream check at all.
    assert npm_calls == ["bmad-builder"]
    suite = [f for f in findings if f.check == "bmad-suite-upstream-drift"]
    assert len(suite) == 1
    assert suite[0].status is DoctorStatus.OK
    assert suite[0].evidence == {"packages_checked": 1, "packages_watched": 3}


# --- Story 19.1: manifest watched set + registry-aware upstream -----------------


_SUITE_MANIFEST_TWO = """
members:
  - name: bmad-loop
  - name: mybmad-dashboard
  - name: bmad-autopilot
    deprecated: true
"""

_RECIPE_GITHUB_BUILDER = """
context:
  name: bmad-builder
  version: "2.2.1"
extra:
  cfe-upstream-registry: github
  cfe-upstream-name: bmad-code-org/bmad-builder
"""

_RECIPE_GITHUB_DASHBOARD = """
context:
  name: mybmad-dashboard
  version: "1.0.0"
extra:
  cfe-upstream-registry: github
  cfe-upstream-name: bmad-code-org/bmad-method-ui
"""


def _write_suite_manifest(target: Path, text: str) -> Path:
    path = target / "recipes" / "bmad-suite" / "suite-members.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_manifest_union_includes_mybmad_dashboard_without_pixi_pin(
    tmp_path: Path,
) -> None:
    _write_pixi(tmp_path, _PIXI_SINGLE)
    _write_suite_manifest(tmp_path, _SUITE_MANIFEST_TWO)
    _write_recipe_yaml(tmp_path, "bmad-loop", _RECIPE_GITHUB_BMAD_LOOP)
    _write_recipe_yaml(tmp_path, "mybmad-dashboard", _RECIPE_GITHUB_DASHBOARD)

    watched = bmad_method._suite_packages(
        tomllib.loads((tmp_path / "pixi.toml").read_text(encoding="utf-8")),
        tmp_path,
    )

    assert "mybmad-dashboard" in watched
    assert "bmad-loop" in watched
    assert "bmad-autopilot" not in watched


def test_manifest_absent_falls_back_to_pixi_bmad_pins_only() -> None:
    data = {
        "feature": {
            "local-recipes": {
                "dependencies": {
                    "bmad-method": ">=6.11.0",
                    "bmad-loop": ">=0.11.0",
                    "bmad-method-test-architecture-enterprise": ">=1.23.2",
                }
            }
        }
    }
    assert bmad_method._suite_packages(data, None) == (
        "bmad-loop",
        "bmad-method-test-architecture-enterprise",
    )


def test_builder_github_primary_ignores_stale_npm_for_recipe_upstream_drift(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_pixi(
        tmp_path,
        """
[feature.python.dependencies]
bmad-method = ">=6.11.0"

[feature.local-recipes.dependencies]
bmad-builder = ">=2.2.1"
""",
    )
    _write_manifest(tmp_path, _MANIFEST_611)
    _write_conda_meta(tmp_path, "default", "bmad-builder", "2.2.1")
    _write_recipe_yaml(tmp_path, "bmad-builder", _RECIPE_GITHUB_BUILDER)

    def _resolve(
        package: str,
        target: Path,
        *,
        timeout: float | None = None,
    ) -> tuple[int, int, int] | None:
        return {
            "bmad-method": (6, 11, 0),
            "bmad-builder": (2, 2, 2),
        }.get(package)

    monkeypatch.setattr(bmad_method, "_fetch_latest_upstream_version", lambda **_: (6, 11, 0))
    monkeypatch.setattr(bmad_method, "_resolve_upstream_latest", _resolve)

    findings = bmad_method.gather(tmp_path)

    recipe = [f for f in findings if f.check == "bmad-recipe-upstream-drift"]
    assert len(recipe) == 1
    assert recipe[0].evidence["package"] == "bmad-builder"
    assert recipe[0].evidence["latest_upstream"] == "2.2.2"


def test_unknown_registry_takes_max_of_npm_and_github(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_pixi(
        tmp_path,
        """
[feature.local-recipes.dependencies]
bmad-loop = ">=0.11.0"
""",
    )
    _write_manifest(tmp_path, _MANIFEST_611)
    _write_conda_meta(tmp_path, "default", "bmad-loop", "0.10.0")

    npm_calls = 0
    github_calls = 0

    def _npm(**kwargs):
        nonlocal npm_calls
        npm_calls += 1
        return (0, 10, 0)

    def _github(**kwargs):
        nonlocal github_calls
        github_calls += 1
        return (0, 11, 0)

    monkeypatch.setattr(bmad_method, "_fetch_latest_upstream_version", _npm)
    monkeypatch.setattr(bmad_method, "_fetch_latest_github_release", _github)
    monkeypatch.setattr(bmad_method, "_github_owner_repo", lambda *_: "org/repo")
    monkeypatch.setattr(bmad_method, "_fetch_pypi_latest_version", lambda **_: None)

    latest = bmad_method._resolve_upstream_latest("bmad-loop", tmp_path)

    assert latest == (0, 11, 0)
    assert npm_calls == 1
    assert github_calls == 1


# --- Story 20.1: probe-class-aware suite gather-level scenarios --------------------


_PIXI_SUITE_NPM_ONLY = """
[feature.python.dependencies]
bmad-method = ">=6.11.0"

[feature.local-recipes.dependencies]
bmad-module-skill-forge = ">=2.1.0"
"""

_PIXI_SUITE_COMMIT_PINNED_ONLY = """
[feature.python.dependencies]
bmad-method = ">=6.11.0"

[feature.local-recipes.dependencies]
bmad-eval-quality = ">=0.2.0"
"""

_RECIPE_COMMIT_PINNED_MISSING_COMMIT = """
context:
  version: "0.2.0.dev0"

extra:
  cfe-upstream-registry: github
  cfe-upstream-name: bmad-code-org/bmad-eval-quality
  cfe-source-kind: github-commit
"""

_RECIPE_COMMIT_PINNED_MISSING_GITHUB_MAPPING = """
context:
  version: "0.2.0.dev0"
  commit: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa

extra:
  cfe-source-kind: github-commit
"""


def test_npm_class_suite_package_warn_names_probe_class_npm(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_pixi(tmp_path, _PIXI_SUITE_NPM_ONLY)
    _write_manifest(tmp_path, _MANIFEST_611)
    _write_conda_meta(tmp_path, "default", "bmad-module-skill-forge", "2.1.0")
    _write_recipe_yaml(tmp_path, "bmad-module-skill-forge", _RECIPE_NPM_REGISTRY)
    _stub_fetch_by_package(
        monkeypatch,
        {"bmad-method": (6, 11, 0), "bmad-module-skill-forge": (2, 2, 0)},
    )

    findings = bmad_method.gather(tmp_path)

    suite = [f for f in findings if f.check == "bmad-suite-upstream-drift"]
    assert len(suite) == 1
    finding = suite[0]
    assert finding.status is DoctorStatus.WARN
    assert finding.evidence == {
        "package": "bmad-module-skill-forge",
        "probe_class": "npm",
        "installed": "2.1.0",
        "latest_upstream": "2.2.0",
    }


def test_commit_pinned_warn_encodes_the_full_version_at_sha_message_and_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # THE Matrix fixture: context.version "0.2.0.dev0", context.commit
    # aaaa...(40 hex), stubbed HEAD sha bbbb...(40 hex) differs.
    _write_pixi(tmp_path, _PIXI_SUITE_COMMIT_PINNED_ONLY)
    _write_manifest(tmp_path, _MANIFEST_611)
    _write_conda_meta(tmp_path, "default", "bmad-eval-quality", "0.2.0.dev0")
    _write_recipe_yaml(tmp_path, "bmad-eval-quality", _RECIPE_COMMIT_PINNED)
    _stub_fetch_by_package(monkeypatch, {"bmad-method": (6, 11, 0)})
    monkeypatch.setattr(bmad_method, "_fetch_default_branch_head_sha", lambda **_: "b" * 40)

    findings = bmad_method.gather(tmp_path)

    suite = [f for f in findings if f.check == "bmad-suite-upstream-drift"]
    assert len(suite) == 1
    finding = suite[0]
    assert finding.status is DoctorStatus.WARN
    assert finding.message == (
        "bmad-eval-quality 0.2.0.dev0 @ aaaaaaaaaaaa is behind the default-branch HEAD bbbbbbbbbbbb"
    )
    assert finding.evidence == {
        "package": "bmad-eval-quality",
        "probe_class": "commit-pinned",
        "installed": "0.2.0.dev0 @ aaaaaaaaaaaa",
        "latest_upstream": "bbbbbbbbbbbb",
    }


def test_commit_pinned_branch_never_falls_through_to_the_tag_npm_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Review finding: every other commit-pinned test's `_stub_fetch_by_
    # package` simply omits the package from `versions`, so
    # `_resolve_upstream_latest` would return None regardless of whether it
    # was ever CALLED -- none of them prove the commit-pinned branch's
    # `continue` actually blocks fallthrough. Here `_resolve_upstream_latest`
    # is stubbed to return a resolvable (but WRONG) triple for
    # bmad-eval-quality -- if the tag/npm path were ever reached for this
    # package, it would produce a second/different Finding instead of being
    # skipped entirely.
    _write_pixi(tmp_path, _PIXI_SUITE_COMMIT_PINNED_ONLY)
    _write_manifest(tmp_path, _MANIFEST_611)
    _write_conda_meta(tmp_path, "default", "bmad-eval-quality", "0.2.0.dev0")
    _write_recipe_yaml(tmp_path, "bmad-eval-quality", _RECIPE_COMMIT_PINNED)
    calls: list[str] = []
    _stub_fetch_by_package(
        monkeypatch,
        {"bmad-method": (6, 11, 0), "bmad-eval-quality": (99, 0, 0)},
        calls=calls,
    )
    monkeypatch.setattr(bmad_method, "_fetch_default_branch_head_sha", lambda **_: "b" * 40)

    findings = bmad_method.gather(tmp_path)

    assert "bmad-eval-quality" not in calls
    suite = [f for f in findings if f.check == "bmad-suite-upstream-drift"]
    assert len(suite) == 1
    assert suite[0].evidence["probe_class"] == "commit-pinned"


def test_commit_pinned_current_no_warn_but_still_counted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_pixi(tmp_path, _PIXI_SUITE_COMMIT_PINNED_ONLY)
    _write_manifest(tmp_path, _MANIFEST_611)
    _write_conda_meta(tmp_path, "default", "bmad-eval-quality", "0.2.0.dev0")
    _write_recipe_yaml(tmp_path, "bmad-eval-quality", _RECIPE_COMMIT_PINNED)
    _stub_fetch_by_package(monkeypatch, {"bmad-method": (6, 11, 0)})
    monkeypatch.setattr(
        bmad_method,
        "_fetch_default_branch_head_sha",
        lambda **_: "a" * 40,  # matches the pinned commit exactly
    )

    findings = bmad_method.gather(tmp_path)

    suite = [f for f in findings if f.check == "bmad-suite-upstream-drift"]
    assert len(suite) == 1
    assert suite[0].status is DoctorStatus.OK
    assert suite[0].evidence == {"packages_checked": 1, "packages_watched": 1}


def test_commit_pinned_missing_recipe_commit_is_unchecked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_pixi(tmp_path, _PIXI_SUITE_COMMIT_PINNED_ONLY)
    _write_manifest(tmp_path, _MANIFEST_611)
    _write_conda_meta(tmp_path, "default", "bmad-eval-quality", "0.2.0.dev0")
    _write_recipe_yaml(tmp_path, "bmad-eval-quality", _RECIPE_COMMIT_PINNED_MISSING_COMMIT)
    _stub_fetch_by_package(monkeypatch, {"bmad-method": (6, 11, 0)})

    def _unreachable(**_):
        raise AssertionError("_fetch_default_branch_head_sha must not be called")

    monkeypatch.setattr(bmad_method, "_fetch_default_branch_head_sha", _unreachable)

    findings = bmad_method.gather(tmp_path)

    assert [f.check for f in findings] == [
        "bmad-method-version-drift",
        "bmad-method-upstream-drift",
    ]


def test_commit_pinned_missing_github_mapping_is_unchecked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_pixi(tmp_path, _PIXI_SUITE_COMMIT_PINNED_ONLY)
    _write_manifest(tmp_path, _MANIFEST_611)
    _write_conda_meta(tmp_path, "default", "bmad-eval-quality", "0.2.0.dev0")
    _write_recipe_yaml(tmp_path, "bmad-eval-quality", _RECIPE_COMMIT_PINNED_MISSING_GITHUB_MAPPING)
    _stub_fetch_by_package(monkeypatch, {"bmad-method": (6, 11, 0)})

    def _unreachable(**_):
        raise AssertionError("_fetch_default_branch_head_sha must not be called")

    monkeypatch.setattr(bmad_method, "_fetch_default_branch_head_sha", _unreachable)

    findings = bmad_method.gather(tmp_path)

    assert [f.check for f in findings] == [
        "bmad-method-version-drift",
        "bmad-method-upstream-drift",
    ]


def test_commit_pinned_head_fetch_failure_is_unchecked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_pixi(tmp_path, _PIXI_SUITE_COMMIT_PINNED_ONLY)
    _write_manifest(tmp_path, _MANIFEST_611)
    _write_conda_meta(tmp_path, "default", "bmad-eval-quality", "0.2.0.dev0")
    _write_recipe_yaml(tmp_path, "bmad-eval-quality", _RECIPE_COMMIT_PINNED)
    _stub_fetch_by_package(monkeypatch, {"bmad-method": (6, 11, 0)})
    monkeypatch.setattr(bmad_method, "_fetch_default_branch_head_sha", lambda **_: None)

    findings = bmad_method.gather(tmp_path)

    assert [f.check for f in findings] == [
        "bmad-method-version-drift",
        "bmad-method-upstream-drift",
    ]


# --- Story 20.1: the real-roster registry-class mix, all current -------------------


def test_full_roster_probe_class_mix_all_current_reports_12_checked_of_12(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Mirrors recipes/bmad-suite/suite-members.yaml's real registry-class
    # mix: 4 github-tag, 7 github-commit, 1 npm-registry (12 non-core
    # members) -- the aggregate evidence must read exactly 12/12. The
    # core's own separate bmad-method-upstream-drift Finding accounts for
    # the roster's 13th entry (Design Notes: "Why 12, not 13").
    tag_names = (
        "bmad-loop",
        "bmad-method-test-architecture-enterprise",
        "bmad-builder",
        "bmad-creative-intelligence-suite",
    )
    commit_names = (
        "bmad-eval-quality",
        "bmad-utility-skills",
        "bmad-labs-skills",
        "bmad-module-template",
        "bmad-manticore",
        "bmad-dashboard",
        "mybmad-dashboard",
    )
    npm_names = ("bmad-module-skill-forge",)
    all_names = (*tag_names, *commit_names, *npm_names)

    pixi_lines = [
        "[feature.python.dependencies]",
        'bmad-method = ">=6.11.0"',
        "",
        "[feature.local-recipes.dependencies]",
    ]
    for name in all_names:
        pixi_lines.append(f'{name} = ">=1.0.0"')
    _write_pixi(tmp_path, "\n".join(pixi_lines))
    _write_manifest(tmp_path, _MANIFEST_611)
    # mybmad-dashboard doesn't start with the "bmad-" prefix the pixi-only
    # derivation requires (real repo precedent, Story 19.1) -- it only joins
    # the watched set via the tracked suite-members.yaml manifest, unioned
    # with the pixi-derived names. Listing every name here mirrors the real
    # manifest's own union-not-replace relationship with pixi.toml.
    _write_suite_manifest(
        tmp_path,
        "members:\n" + "".join(f"  - name: {name}\n" for name in all_names),
    )

    fetch_versions: dict[str, tuple[int, int, int]] = {"bmad-method": (6, 11, 0)}
    for name in tag_names:
        _write_conda_meta(tmp_path, "default", name, "1.0.0")
        _write_recipe_yaml(
            tmp_path,
            name,
            f"""
extra:
  cfe-upstream-registry: github
  cfe-upstream-name: bmad-code-org/{name}
  cfe-source-kind: github-tag
""",
        )
        fetch_versions[name] = (1, 0, 0)
    for name in npm_names:
        _write_conda_meta(tmp_path, "default", name, "1.0.0")
        _write_recipe_yaml(
            tmp_path,
            name,
            f"""
extra:
  cfe-upstream-registry: npm
  cfe-upstream-name: {name}
  cfe-source-kind: npm-registry
""",
        )
        fetch_versions[name] = (1, 0, 0)

    pinned_commit = "c" * 40
    for name in commit_names:
        _write_conda_meta(tmp_path, "default", name, "1.0.0.dev0")
        _write_recipe_yaml(
            tmp_path,
            name,
            f"""
context:
  version: "1.0.0.dev0"
  commit: {pinned_commit}

extra:
  cfe-upstream-registry: github
  cfe-upstream-name: bmad-code-org/{name}
  cfe-source-kind: github-commit
""",
        )

    _stub_fetch_by_package(monkeypatch, fetch_versions)
    monkeypatch.setattr(bmad_method, "_fetch_default_branch_head_sha", lambda **_: pinned_commit)

    findings = bmad_method.gather(tmp_path)

    suite = [f for f in findings if f.check == "bmad-suite-upstream-drift"]
    assert len(suite) == 1
    assert suite[0].status is DoctorStatus.OK
    assert suite[0].evidence == {"packages_checked": 12, "packages_watched": 12}
