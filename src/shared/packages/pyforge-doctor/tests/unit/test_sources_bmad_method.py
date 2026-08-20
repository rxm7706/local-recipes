"""Unit tests for ``pyforge.doctor.sources.bmad_method.gather`` (Story 10.1,
Epic 10/CAP-1; Story 10.2, Epic 10/CAP-2) -- covers every row of the spec's
I/O & Edge-Case Matrix against REAL tmp fixture trees (a written
``pixi.toml`` + ``_bmad/_config/manifest.yaml``), mirroring
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
