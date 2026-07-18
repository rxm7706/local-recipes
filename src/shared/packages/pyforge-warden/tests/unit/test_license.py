"""Unit tests — per-component SPDX license verdicts (Story 6.2): conda's
``about: license:`` re-read, pypi's ``importlib.metadata`` resolution (PEP
639 -> legacy ``License`` -> trove classifiers), SPDX normalization/
validation via ``license-expression``, verdict classification (allow/deny
list semantics), ``Finding``/id construction, and the hard ``license_rung``
warn-cap. Also covers ``LicenseEngine``'s thin coverage-and-``EngineResult``
wrapper.

``importlib.metadata.metadata`` is monkeypatched for the "installed" cases
(a fake ``email.message.Message``-shaped object) — never a real subprocess,
never a real network fetch; the "uninstalled" cases use a package name that
is (virtually) guaranteed absent from any real environment, exercising the
REAL ``importlib.metadata.PackageNotFoundError`` path.
"""

from __future__ import annotations

import importlib.metadata
from email.message import Message

import pytest

from pyforge.warden import license as license_module
from pyforge.warden.engines import LicenseEngine
from pyforge.warden.inventory import PypiIdentity, ResolvedInventory, merge_components
from pyforge.warden.license import (
    DEFAULT_LICENSE_POLICY,
    _classify_verdict,
    _normalize_tokens,
    _parse_spdx,
    license_findings,
    license_rung,
)
from pyforge.warden.models import (
    AXIS_LICENSE,
    Ecosystem,
    Finding,
    LicenseInfo,
    LicenseVerdict,
    ScannedManifest,
    Status,
    StatusDriver,
)

_UNINSTALLED = "totally-not-a-real-installed-package-xyz-987654321"

MANIFEST = ScannedManifest(path="pyproject.toml", kind="pyproject.toml")


def _fake_metadata(
    *,
    license_expression: str | None = None,
    license: str | None = None,
    classifiers: tuple[str, ...] = (),
) -> Message:
    """A minimal ``PackageMetadata``-shaped stand-in
    (``email.message.Message`` already satisfies the ``.get``/``.get_all``
    protocol ``importlib.metadata`` itself returns)."""
    msg = Message()
    if license_expression is not None:
        msg["License-Expression"] = license_expression
    if license is not None:
        msg["License"] = license
    for classifier in classifiers:
        msg["Classifier"] = classifier
    return msg


def _patch_metadata(monkeypatch: pytest.MonkeyPatch, meta: Message) -> None:
    monkeypatch.setattr(importlib.metadata, "metadata", lambda name: meta)


def make_inventory(*components) -> ResolvedInventory:
    return ResolvedInventory(
        components=merge_components(components), resolved_scan_set=(MANIFEST,)
    )


# --- I/O matrix row: conda resolvable, no flags -----------------------------


def test_conda_about_license_resolvable_is_allowed_no_finding(tmp_path, component_factory):
    (tmp_path / "recipe.yaml").write_text("about:\n  license: MIT\n", encoding="utf-8")
    component = component_factory(
        name="mypkg",
        version="1.0.0",
        ecosystem=Ecosystem.CONDA,
        provenance=(("recipe.yaml", "requirements.host"),),
    )
    assert license_findings([component], tmp_path) == ()


def test_conda_about_license_normalizes_via_license_expression(tmp_path, component_factory):
    # Lowercase input -> canonical SPDX id, proving normalization runs (not
    # a bare pass-through) — a denied verdict's Finding carries the
    # normalized form.
    (tmp_path / "recipe.yaml").write_text("about:\n  license: gpl-3.0-only\n", encoding="utf-8")
    component = component_factory(
        name="mypkg",
        version="1.0.0",
        ecosystem=Ecosystem.CONDA,
        provenance=(("recipe.yaml", "requirements.host"),),
    )
    (finding,) = license_findings([component], tmp_path, deny_licenses=("GPL-3.0-only",))
    assert finding.license.expression == "GPL-3.0-only"
    assert finding.license.family == "GPL3"
    assert finding.id == "license:GPL-3.0-only:mypkg@1.0.0"


def test_meta_yaml_v0_about_license_also_resolves(tmp_path, component_factory):
    (tmp_path / "meta.yaml").write_text(
        "about:\n  license: BSD-3-Clause\n", encoding="utf-8"
    )
    component = component_factory(
        name="mypkg",
        version="1.0.0",
        ecosystem=Ecosystem.CONDA,
        provenance=(("meta.yaml", "requirements"),),
    )
    assert license_findings([component], tmp_path) == ()


def test_recipe_yaml_neutralize_pass_tolerates_a_jinja_comment(tmp_path, component_factory):
    """Proves the reused ``strip_jinja_comments``/``neutralize_bare_braces``
    helpers actually ran — a bare ``{# ... #}`` span would otherwise crash
    ``yaml.safe_load`` outright."""
    (tmp_path / "recipe.yaml").write_text(
        "{# a comment #}\nabout:\n  license: MIT\n", encoding="utf-8"
    )
    component = component_factory(
        name="mypkg",
        version="1.0.0",
        ecosystem=Ecosystem.CONDA,
        provenance=(("recipe.yaml", "requirements.host"),),
    )
    assert license_findings([component], tmp_path) == ()


# --- Fix 7 (review finding, 2026-07-18): v1 (recipe.yaml) wins a v0->v1 ------
# migration coexistence, never whichever manifest sorts first lexically.


@pytest.mark.parametrize(
    "provenance",
    [
        (("meta.yaml", "requirements"), ("recipe.yaml", "requirements.host")),
        (("recipe.yaml", "requirements.host"), ("meta.yaml", "requirements")),
    ],
    ids=["meta-first", "recipe-first"],
)
def test_conda_recipe_yaml_wins_over_meta_yaml_when_both_present(
    tmp_path, component_factory, provenance
):
    """A component carrying BOTH recipe.yaml (v1) and meta.yaml (v0)
    provenance with DIFFERENT about: license: values must resolve via
    recipe.yaml regardless of the provenance tuple's own order (never
    picked by lexicographic (manifest, section) sort accident — "meta.yaml"
    < "recipe.yaml" would otherwise pick the v0 file every time)."""
    (tmp_path / "recipe.yaml").write_text("about:\n  license: MIT\n", encoding="utf-8")
    (tmp_path / "meta.yaml").write_text(
        "about:\n  license: GPL-3.0-only\n", encoding="utf-8"
    )
    component = component_factory(
        name="mypkg",
        version="1.0.0",
        ecosystem=Ecosystem.CONDA,
        provenance=provenance,
    )
    # Denying GPL-3.0-only (meta.yaml's value) must NOT match -- meta.yaml
    # was not the source consulted.
    assert license_findings([component], tmp_path, deny_licenses=("GPL-3.0-only",)) == ()
    # Denying MIT (recipe.yaml's value) DOES match -- recipe.yaml (v1) is
    # the one actually re-read.
    (finding,) = license_findings([component], tmp_path, deny_licenses=("MIT",))
    assert finding.license.expression == "MIT"


# --- I/O matrix row: PyPI unresolvable, no flags ----------------------------


def test_pypi_uninstalled_is_unknown_with_warn_finding(tmp_path, component_factory):
    component = component_factory(name=_UNINSTALLED, version="1.0.0")
    (finding,) = license_findings([component], tmp_path)
    assert finding.id == f"license:unknown:{_UNINSTALLED}@1.0.0"
    assert finding.axis == AXIS_LICENSE
    assert finding.license == LicenseInfo(
        expression="unknown", family=None, verdict=LicenseVerdict.UNKNOWN
    )
    status, _driver = license_rung(finding)
    assert status is Status.WARN  # never a silent clean


def test_pypi_uninstalled_no_version_uses_unspecified_segment(tmp_path, component_factory):
    component = component_factory(name=_UNINSTALLED, version=None)
    (finding,) = license_findings([component], tmp_path)
    assert finding.id == f"license:unknown:{_UNINSTALLED}@unspecified"


def test_pypi_empty_identity_name_degrades_to_unknown_never_crashes(
    tmp_path, component_factory
):
    """Fix 4 (review finding, 2026-07-18):
    ``importlib.metadata.metadata("")`` raises ``ValueError``, NOT
    ``PackageNotFoundError`` (verified live) — an empty ``pypi_identity.
    name`` must degrade to unknown, never crash the engine."""
    component = component_factory(
        name="whatever",
        version="1.0.0",
        pypi_identity=PypiIdentity(name="", version=None),
    )
    (finding,) = license_findings([component], tmp_path)
    assert finding.license.verdict is LicenseVerdict.UNKNOWN


# --- I/O matrix row: PyPI installed, resolvable -----------------------------


def test_pypi_installed_resolves_via_pep639_license_expression(
    monkeypatch, tmp_path, component_factory
):
    _patch_metadata(monkeypatch, _fake_metadata(license_expression="MIT"))
    component = component_factory(name="fake-pkg", version="1.0.0")
    assert license_findings([component], tmp_path) == ()


def test_pypi_installed_falls_back_to_legacy_license_field(
    monkeypatch, tmp_path, component_factory
):
    _patch_metadata(monkeypatch, _fake_metadata(license="Apache-2.0"))
    component = component_factory(name="fake-pkg", version="1.0.0")
    assert license_findings([component], tmp_path) == ()


def test_pypi_installed_falls_back_to_trove_classifiers(
    monkeypatch, tmp_path, component_factory
):
    _patch_metadata(
        monkeypatch,
        _fake_metadata(classifiers=("License :: OSI Approved :: MIT License",)),
    )
    component = component_factory(name="fake-pkg", version="1.0.0")
    assert license_findings([component], tmp_path) == ()


def test_pypi_generic_bsd_classifier_alone_is_unknown(
    monkeypatch, tmp_path, component_factory
):
    """Fix 6a (review finding, 2026-07-18): the generic 'License :: OSI
    Approved :: BSD License' classifier does not disambiguate
    BSD-2-Clause/BSD-3-Clause/0BSD/etc -- it must degrade to unknown, never
    a confident (and possibly wrong) guess like the former "BSD-3-Clause"
    mapping."""
    _patch_metadata(
        monkeypatch,
        _fake_metadata(classifiers=("License :: OSI Approved :: BSD License",)),
    )
    component = component_factory(name="fake-pkg", version="1.0.0")
    (finding,) = license_findings([component], tmp_path)
    assert finding.license.verdict is LicenseVerdict.UNKNOWN


def test_pypi_conflicting_classifiers_degrade_to_unknown_not_first_pick(
    monkeypatch, tmp_path, component_factory
):
    """Fix 6b: two classifiers mapping to DIFFERENT SPDX ids must degrade
    to unknown, never silently pick whichever classifier was listed
    first."""
    _patch_metadata(
        monkeypatch,
        _fake_metadata(
            classifiers=(
                "License :: OSI Approved :: MIT License",
                "License :: OSI Approved :: Apache Software License",
            )
        ),
    )
    component = component_factory(name="fake-pkg", version="1.0.0")
    (finding,) = license_findings([component], tmp_path)
    assert finding.license.verdict is LicenseVerdict.UNKNOWN


def test_pypi_installed_prefers_pep639_over_legacy_and_classifiers(
    monkeypatch, tmp_path, component_factory
):
    """The fallback order is PEP 639 -> legacy -> classifiers — a
    conflicting legacy/classifier value must never win when License-
    Expression is present."""
    _patch_metadata(
        monkeypatch,
        _fake_metadata(
            license_expression="MIT",
            license="totally not a real license string",
            classifiers=("License :: OSI Approved :: Apache Software License",),
        ),
    )
    component = component_factory(name="fake-pkg", version="1.0.0")
    assert license_findings([component], tmp_path) == ()


def test_pypi_installed_unresolvable_metadata_degrades_to_unknown(
    monkeypatch, tmp_path, component_factory
):
    # The classic setuptools placeholder — not a real SPDX id.
    _patch_metadata(monkeypatch, _fake_metadata(license="UNKNOWN"))
    component = component_factory(name="fake-pkg", version="1.0.0")
    (finding,) = license_findings([component], tmp_path)
    assert finding.license.verdict is LicenseVerdict.UNKNOWN


def test_pypi_installed_full_license_text_never_parsed_as_an_expression(
    monkeypatch, tmp_path, component_factory
):
    """A legacy ``License`` field commonly carries the FULL LICENSE TEXT —
    never attempt to feed that to the SPDX parser as a short expression."""
    long_text = "MIT License\n\n" + ("Permission is hereby granted, " * 20)
    _patch_metadata(monkeypatch, _fake_metadata(license=long_text))
    component = component_factory(name="fake-pkg", version="1.0.0")
    (finding,) = license_findings([component], tmp_path)
    assert finding.license.verdict is LicenseVerdict.UNKNOWN


# --- I/O matrix row: deny-list match -----------------------------------------


def test_deny_list_match_is_denied_at_warn(tmp_path, component_factory):
    (tmp_path / "recipe.yaml").write_text(
        "about:\n  license: GPL-3.0-only\n", encoding="utf-8"
    )
    component = component_factory(
        name="mypkg",
        version="1.0.0",
        ecosystem=Ecosystem.CONDA,
        provenance=(("recipe.yaml", "requirements.host"),),
    )
    (finding,) = license_findings([component], tmp_path, deny_licenses=("GPL-3.0-only",))
    assert finding.license.verdict is LicenseVerdict.DENIED
    status, _driver = license_rung(finding)
    assert status is Status.WARN  # never higher this story


def test_conda_with_exception_license_denied_via_deny_licenses(tmp_path, component_factory):
    """Fix 1 (review finding, 2026-07-18): a SPDX ``WITH``-exception
    expression is ``isliteral`` but its symbol is a
    ``LicenseWithExceptionSymbol``, which has NO ``.key`` attribute — a
    bare ``parsed.key`` access crashed the whole engine on this real
    conda-forge license shape (verified live against
    license-expression==30.4.4). Both the resolution AND the
    ``--deny-licenses`` matching path must survive it with a sane verdict."""
    (tmp_path / "recipe.yaml").write_text(
        "about:\n  license: GPL-2.0-only WITH Classpath-exception-2.0\n",
        encoding="utf-8",
    )
    component = component_factory(
        name="mypkg",
        version="1.0.0",
        ecosystem=Ecosystem.CONDA,
        provenance=(("recipe.yaml", "requirements.host"),),
    )
    (finding,) = license_findings(
        [component],
        tmp_path,
        deny_licenses=("GPL-2.0-only WITH Classpath-exception-2.0",),
    )
    assert finding.license.verdict is LicenseVerdict.DENIED
    assert finding.license.expression == "GPL-2.0-only WITH Classpath-exception-2.0"
    assert finding.license.family is None


# --- I/O matrix row: allow-list, non-member ---------------------------------


def test_allow_list_non_member_is_denied(tmp_path, component_factory):
    (tmp_path / "recipe.yaml").write_text(
        "about:\n  license: Apache-2.0\n", encoding="utf-8"
    )
    component = component_factory(
        name="mypkg",
        version="1.0.0",
        ecosystem=Ecosystem.CONDA,
        provenance=(("recipe.yaml", "requirements.host"),),
    )
    (finding,) = license_findings([component], tmp_path, allow_licenses=("MIT",))
    assert finding.license.verdict is LicenseVerdict.DENIED


def test_allow_list_member_is_allowed_no_finding(tmp_path, component_factory):
    (tmp_path / "recipe.yaml").write_text("about:\n  license: MIT\n", encoding="utf-8")
    component = component_factory(
        name="mypkg",
        version="1.0.0",
        ecosystem=Ecosystem.CONDA,
        provenance=(("recipe.yaml", "requirements.host"),),
    )
    assert license_findings([component], tmp_path, allow_licenses=("MIT",)) == ()


# --- I/O matrix row: both flags, overlapping match --------------------------


def test_both_flags_overlapping_match_deny_wins(tmp_path, component_factory):
    (tmp_path / "recipe.yaml").write_text("about:\n  license: MIT\n", encoding="utf-8")
    component = component_factory(
        name="mypkg",
        version="1.0.0",
        ecosystem=Ecosystem.CONDA,
        provenance=(("recipe.yaml", "requirements.host"),),
    )
    (finding,) = license_findings(
        [component], tmp_path, allow_licenses=("MIT",), deny_licenses=("MIT",)
    )
    assert finding.license.verdict is LicenseVerdict.DENIED


# --- Fix 2 (review finding, 2026-07-18): compound (AND/OR) expression -------
# semantics — order-independent symbol-set matching, never a naive
# str() == str() whole-expression comparison.


def test_deny_list_order_independent_compound_match(
    monkeypatch, tmp_path, component_factory
):
    """``license_expression`` preserves syntactic operand order rather
    than canonicalizing it, so a deny entry and a resolved expression
    naming the SAME two licenses in a DIFFERENT order must still match —
    a naive ``str() == str()`` comparison misses this (verified live
    against real installed ``packaging`` metadata, which resolves to the
    compound ``"Apache-2.0 OR BSD-2-Clause"``)."""
    _patch_metadata(monkeypatch, _fake_metadata(license_expression="Apache-2.0 OR MIT"))
    component = component_factory(name="fake-pkg", version="1.0.0")
    (finding,) = license_findings(
        [component], tmp_path, deny_licenses=("MIT OR Apache-2.0",)
    )
    assert finding.license.verdict is LicenseVerdict.DENIED


def test_allow_list_or_decomposition_all_branches_covered(
    monkeypatch, tmp_path, component_factory
):
    """OR-decomposition allow-list case: a dual-licensed resolved
    expression is ``allowed`` when EVERY one of its OR'd branches is
    individually on the allow-list, even though the compound string
    itself was never listed verbatim (the previous whole-string
    comparison denied this unconditionally)."""
    _patch_metadata(monkeypatch, _fake_metadata(license_expression="MIT OR Apache-2.0"))
    component = component_factory(name="fake-pkg", version="1.0.0")
    assert (
        license_findings([component], tmp_path, allow_licenses=("MIT", "Apache-2.0"))
        == ()
    )


def test_allow_list_or_decomposition_partial_coverage_is_denied(
    monkeypatch, tmp_path, component_factory
):
    """The conservative half of the same rule: only ONE of the two OR'd
    branches being allow-listed is NOT enough — the unlisted branch is an
    unreviewed license, so the whole expression is ``denied``, never a
    permissive "any branch allowed is enough" reading."""
    _patch_metadata(monkeypatch, _fake_metadata(license_expression="MIT OR Apache-2.0"))
    component = component_factory(name="fake-pkg", version="1.0.0")
    (finding,) = license_findings([component], tmp_path, allow_licenses=("MIT",))
    assert finding.license.verdict is LicenseVerdict.DENIED


def test_deny_list_and_expression_any_symbol_denies(
    monkeypatch, tmp_path, component_factory
):
    """AND-expression case: every symbol of an AND expression carries its
    own obligation (the component genuinely carries ALL of them), so a
    deny match on ANY of them denies the whole expression — the same
    any-symbol rule an OR expression gets."""
    _patch_metadata(
        monkeypatch, _fake_metadata(license_expression="MIT AND GPL-3.0-only")
    )
    component = component_factory(name="fake-pkg", version="1.0.0")
    (finding,) = license_findings([component], tmp_path, deny_licenses=("GPL-3.0-only",))
    assert finding.license.verdict is LicenseVerdict.DENIED


# --- I/O matrix row: malformed conda manifest -------------------------------


def test_non_string_license_value_degrades_to_unknown_never_crashes(
    tmp_path, component_factory
):
    (tmp_path / "recipe.yaml").write_text(
        "about:\n  license:\n    - MIT\n    - Apache-2.0\n", encoding="utf-8"
    )
    component = component_factory(
        name="mypkg",
        version="1.0.0",
        ecosystem=Ecosystem.CONDA,
        provenance=(("recipe.yaml", "requirements.host"),),
    )
    (finding,) = license_findings([component], tmp_path)
    assert finding.license.verdict is LicenseVerdict.UNKNOWN


def test_malformed_yaml_degrades_to_unknown_never_crashes(tmp_path, component_factory):
    (tmp_path / "recipe.yaml").write_text("about: [unterminated\n", encoding="utf-8")
    component = component_factory(
        name="mypkg",
        version="1.0.0",
        ecosystem=Ecosystem.CONDA,
        provenance=(("recipe.yaml", "requirements.host"),),
    )
    (finding,) = license_findings([component], tmp_path)
    assert finding.license.verdict is LicenseVerdict.UNKNOWN


def test_manifest_invalid_utf8_degrades_to_unknown_never_crashes(
    tmp_path, component_factory
):
    """Fix 3 (review finding, 2026-07-18): ``UnicodeDecodeError`` is a
    ``ValueError`` subclass, NOT an ``OSError`` subclass — a manifest
    containing invalid UTF-8 bytes escaped the ``except OSError`` clause
    uncaught and crashed the engine. Must degrade to unknown instead."""
    (tmp_path / "recipe.yaml").write_bytes(b"about:\n  license: MIT \xff\xfe\n")
    component = component_factory(
        name="mypkg",
        version="1.0.0",
        ecosystem=Ecosystem.CONDA,
        provenance=(("recipe.yaml", "requirements.host"),),
    )
    (finding,) = license_findings([component], tmp_path)
    assert finding.license.verdict is LicenseVerdict.UNKNOWN


def test_unreadable_manifest_degrades_to_unknown_never_crashes(tmp_path, component_factory):
    component = component_factory(
        name="mypkg",
        version="1.0.0",
        ecosystem=Ecosystem.CONDA,
        provenance=(("recipe.yaml", "requirements.host"),),
    )
    # recipe.yaml is never written under tmp_path.
    (finding,) = license_findings([component], tmp_path)
    assert finding.license.verdict is LicenseVerdict.UNKNOWN


# --- I/O matrix row: no about: section at all -------------------------------


def test_no_about_section_is_unknown(tmp_path, component_factory):
    (tmp_path / "recipe.yaml").write_text("package:\n  name: mypkg\n", encoding="utf-8")
    component = component_factory(
        name="mypkg",
        version="1.0.0",
        ecosystem=Ecosystem.CONDA,
        provenance=(("recipe.yaml", "requirements.host"),),
    )
    (finding,) = license_findings([component], tmp_path)
    assert finding.license.verdict is LicenseVerdict.UNKNOWN


# --- coverage: every component gets a real attempt (allowed included) ------


def test_deps_assessed_equals_deps_total_regardless_of_verdict_mix(
    tmp_path, component_factory
):
    (tmp_path / "recipe.yaml").write_text("about:\n  license: MIT\n", encoding="utf-8")
    allowed = component_factory(
        name="allowed-pkg",
        version="1.0.0",
        ecosystem=Ecosystem.CONDA,
        provenance=(("recipe.yaml", "requirements.host"),),
    )
    unknown = component_factory(name=_UNINSTALLED, version="1.0.0")
    inventory = make_inventory(allowed, unknown)
    engine = LicenseEngine()
    result = engine.run(tmp_path, inventory)
    (coverage,) = result.coverage
    assert coverage.axis == AXIS_LICENSE
    assert coverage.deps_total == 2
    assert coverage.deps_assessed == 2
    # Only the unresolvable component surfaces a finding — never a silent
    # clean for it, never a spurious finding for the resolvable one.
    assert len(result.findings) == 1
    assert result.findings[0].subject == _UNINSTALLED


def test_license_engine_threads_allow_deny_licenses(tmp_path, component_factory):
    (tmp_path / "recipe.yaml").write_text(
        "about:\n  license: GPL-3.0-only\n", encoding="utf-8"
    )
    component = component_factory(
        name="mypkg",
        version="1.0.0",
        ecosystem=Ecosystem.CONDA,
        provenance=(("recipe.yaml", "requirements.host"),),
    )
    inventory = make_inventory(component)
    engine = LicenseEngine(deny_licenses=("GPL-3.0-only",))
    result = engine.run(tmp_path, inventory)
    (finding,) = result.findings
    assert finding.license.verdict is LicenseVerdict.DENIED


# --- manifest caching: one read per distinct Provenance.manifest path ------


def test_conda_manifest_is_read_at_most_once_per_manifest(
    tmp_path, component_factory, monkeypatch
):
    (tmp_path / "recipe.yaml").write_text("about:\n  license: MIT\n", encoding="utf-8")
    calls: list[object] = []
    original = license_module._read_about_license

    def counting(path):
        calls.append(path)
        return original(path)

    monkeypatch.setattr(license_module, "_read_about_license", counting)
    components = [
        component_factory(
            name=f"pkg{i}",
            version="1.0.0",
            ecosystem=Ecosystem.CONDA,
            provenance=(("recipe.yaml", "requirements.host"),),
        )
        for i in range(3)
    ]
    assert license_findings(components, tmp_path) == ()
    assert len(calls) == 1


# --- license_rung: the hard warn-cap -----------------------------------------


def test_license_rung_is_always_warn_for_denied():
    finding = Finding(
        id="license:GPL-3.0-only:foo@1.0.0",
        axis=AXIS_LICENSE,
        message="denied",
        subject="foo",
        severity=None,
        license=LicenseInfo(
            expression="GPL-3.0-only", family="GPL3", verdict=LicenseVerdict.DENIED
        ),
    )
    status, driver = license_rung(finding)
    assert status is Status.WARN
    assert driver == StatusDriver(axis=AXIS_LICENSE, finding_id=finding.id)


def test_license_rung_is_always_warn_for_unknown():
    finding = Finding(
        id="license:unknown:foo@1.0.0",
        axis=AXIS_LICENSE,
        message="unresolvable",
        subject="foo",
        severity=None,
        license=LicenseInfo(expression="unknown", family=None, verdict=LicenseVerdict.UNKNOWN),
    )
    status, driver = license_rung(finding)
    assert status is Status.WARN
    assert driver == StatusDriver(axis=AXIS_LICENSE, finding_id=finding.id)


def test_default_license_policy_is_unused_but_declared():
    """DEFAULT_LICENSE_POLICY is reserved data (Story 6.5) -- declared,
    immutable, and never consulted by license_rung this story."""
    assert DEFAULT_LICENSE_POLICY == {
        LicenseVerdict.DENIED: Status.WARN,
        LicenseVerdict.UNKNOWN: Status.WARN,
    }
    with pytest.raises(TypeError):
        DEFAULT_LICENSE_POLICY[LicenseVerdict.DENIED] = Status.POLICY_VIOLATION


# --- _parse_spdx: normalization + family ------------------------------------


@pytest.mark.parametrize(
    "raw,expected_expression,expected_family",
    [
        ("mit", "MIT", "MIT"),
        ("MIT", "MIT", "MIT"),
        ("gpl-3.0-only", "GPL-3.0-only", "GPL3"),
        ("Apache-2.0", "Apache-2.0", "Apache"),
    ],
)
def test_parse_spdx_normalizes_and_assigns_family(raw, expected_expression, expected_family):
    result = _parse_spdx(raw)
    assert result == (expected_expression, expected_family)


def test_parse_spdx_compound_expression_has_no_family():
    result = _parse_spdx("MIT OR Apache-2.0")
    assert result is not None
    expression, family = result
    assert "MIT" in expression and "Apache-2.0" in expression
    assert family is None


@pytest.mark.parametrize("raw", [None, "", "   ", "not-a-real-spdx-id", "(((", "x" * 500])
def test_parse_spdx_unresolvable_inputs_are_none(raw):
    assert _parse_spdx(raw) is None


def test_parse_spdx_unrecognized_id_is_none():
    assert _parse_spdx("TotallyMadeUpLicenseName") is None


def test_parse_spdx_with_exception_expression_does_not_crash():
    """Fix 1 (review finding, 2026-07-18): a ``WITH``-exception expression
    is ``isliteral=True`` but its symbol is a
    ``LicenseWithExceptionSymbol``, which carries NO ``.key`` attribute
    (only a plain ``LicenseSymbol`` does) — a bare ``parsed.key`` access
    crashed here (verified live against license-expression==30.4.4).
    Degrades to ``family=None``, never raises."""
    result = _parse_spdx("GPL-2.0-only WITH Classpath-exception-2.0")
    assert result == ("GPL-2.0-only WITH Classpath-exception-2.0", None)


def test_parse_spdx_apache_with_llvm_exception_does_not_crash():
    """A second real-world WITH expression (the punch list's other named
    example), proving the fix is not narrowly specific to GPL/Classpath."""
    result = _parse_spdx("Apache-2.0 WITH LLVM-exception")
    assert result == ("Apache-2.0 WITH LLVM-exception", None)


# --- _classify_verdict / _normalize_tokens ----------------------------------


def test_classify_verdict_no_flags_resolvable_is_allowed():
    resolution = ("MIT", "MIT")
    assert (
        _classify_verdict(resolution, allow=frozenset(), deny=frozenset())
        is LicenseVerdict.ALLOWED
    )


def test_classify_verdict_unresolvable_is_unknown_regardless_of_flags():
    assert (
        _classify_verdict(None, allow=frozenset({"MIT"}), deny=frozenset({"MIT"}))
        is LicenseVerdict.UNKNOWN
    )


def test_classify_verdict_deny_matches_any_symbol_of_a_compound_expression():
    """Fix 2: symbol-set matching, not whole-string equality — a deny
    token matching just ONE of a compound resolved expression's symbols
    denies the whole expression."""
    resolution = ("Apache-2.0 OR MIT", None)
    assert (
        _classify_verdict(resolution, allow=frozenset(), deny=frozenset({"MIT"}))
        is LicenseVerdict.DENIED
    )


def test_classify_verdict_allow_requires_every_symbol_of_a_compound_expression():
    """Fix 2: the conservative allow-list rule — one covered symbol is not
    enough (denied); every symbol covered IS enough (allowed)."""
    resolution = ("Apache-2.0 OR MIT", None)
    assert (
        _classify_verdict(resolution, allow=frozenset({"MIT"}), deny=frozenset())
        is LicenseVerdict.DENIED
    )
    assert (
        _classify_verdict(
            resolution, allow=frozenset({"MIT", "Apache-2.0"}), deny=frozenset()
        )
        is LicenseVerdict.ALLOWED
    )


def test_normalize_tokens_matches_case_insensitively():
    tokens = _normalize_tokens(("gpl-3.0-only",))
    assert tokens == frozenset({"GPL-3.0-only"})


def test_normalize_tokens_decomposes_a_compound_entry_into_symbols():
    """Fix 2: a compound configured entry contributes each of its own
    OR/AND operands as an independent token, never the whole compound
    string as one opaque token."""
    assert _normalize_tokens(("MIT OR Apache-2.0",)) == frozenset({"MIT", "Apache-2.0"})


def test_normalize_tokens_keeps_an_unparsable_entry_as_its_own_stripped_text():
    tokens = _normalize_tokens((" not-a-real-spdx-id ",))
    assert tokens == frozenset({"not-a-real-spdx-id"})


def test_normalize_tokens_drops_blank_entries():
    assert _normalize_tokens(("", "   ", "MIT")) == frozenset({"MIT"})
