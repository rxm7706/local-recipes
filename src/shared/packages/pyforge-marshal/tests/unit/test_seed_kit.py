"""Story 28.3 -- Genesis seeds the token-economy kit
(SPEC-marshal-token-economy CAP-3/CAP-4).

Station-owned coverage for all four acceptance criteria, each named in the
test that would fail if it were violated:

* **AC 1** -- ``marshal seed check`` on a seeded home with layers declared
  verifies caveman-skill deployment, the CCR store dir, and a present+fresh
  codegraph index, *each as a distinct check*.
* **AC 2** -- the landed verdict and journal entries read as normal
  fully-articulated prose, never caveman-compressed. Proven structurally,
  not by inspecting an LLM's output: the deployed skill must carry Genesis's
  articulate carve-out region naming every contract surface, and a
  deployment without it is reported as incomplete.
* **AC 3** -- an unavailable instrument skips its layer with a named finding
  and the seed still applies (the other items land).
* **AC 4** -- a home with its layers off raises no token-economy findings at
  all.

The instruments themselves are never invoked. ``probe`` and ``index_builder``
are both injectable (and the write seam is an ``FsPort``), so the whole
matrix -- available, unavailable, failing -- is exercised without caveman,
codegraph or headroom installed. That is deliberate: the absence of an
instrument is precisely the case the spec requires to degrade, so a test
suite that needed one present could not cover its own primary scenario.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

import pytest
from pyforge.core.process import ProcessError, ProcessResult

from pyforge.marshal.adapters.fs_local import FsError, LocalFs
from pyforge.marshal.cli import seed as seed_cli
from pyforge.marshal.cli.main import _build_parser
from pyforge.marshal.core import policy
from pyforge.marshal.core.harness_profile import load_packaged_profiles
from pyforge.marshal.seed.detect.findings import FindingType, Severity
from pyforge.marshal.seed.detect.kit import (
    InstrumentProbe,
    KitStatus,
    item_present,
    kit_checks,
    kit_findings,
    layer_enabled,
    local_reads,
    probe_instrument,
    resolve_caveman_skill_source,
)
from pyforge.marshal.seed.model.kit import (
    ARTICULATE_REGION,
    ARTICULATE_SURFACES,
    CCR_STORE_RELPATH,
    KIT_ITEMS,
    KitItem,
    KitItemId,
    articulate_region_body,
    kit_item,
    kit_items_for_layer,
)
from pyforge.marshal.seed.model.manifest import (
    AppliesTo,
    ArtifactClass,
    Manifest,
    ManifestEntry,
)
from pyforge.marshal.seed.model.version import ModelVersion
from pyforge.marshal.seed.regions.markers import REGION_NAME_PATTERN, RegionFormat
from pyforge.marshal.seed.regions.parse import parse_regions
from pyforge.marshal.seed.verbs.check import run_check
from pyforge.marshal.seed.verbs.kit import (
    INDEX_TIMEOUT_S,
    SYNC_TIMEOUT_S,
    KitAction,
    build_codegraph_index,
    render_deployed_skill,
    run_kit,
    timeout_note,
)

_VERSION = ModelVersion.parse("1.0.0")

_UPSTREAM_SKILL = "---\nname: caveman\n---\n\nRespond terse like smart caveman.\n"


# --- helpers ---------------------------------------------------------------


def _manifest(*entries: ManifestEntry) -> Manifest:
    return Manifest(model_version=_VERSION, never_write=(), entries=tuple(entries))


def _whole_file(entry_id: str, path: str) -> ManifestEntry:
    return ManifestEntry(
        id=entry_id,
        artifact_class=ArtifactClass.COPIED_MANAGED,
        path=path,
        applies_to=AppliesTo.BOTH,
        rationale="test",
    )


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    return result


@pytest.fixture
def home(tmp_path: Path) -> Path:
    """A git-initialized stand-in for a provisioned loop home."""
    _git(tmp_path, "init", "-b", "main")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test")
    (tmp_path / "README.md").write_text("hello\n", encoding="utf-8")
    _git(tmp_path, "add", "README.md")
    _git(tmp_path, "commit", "-m", "initial")
    return tmp_path


@pytest.fixture
def skill_payload(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A stand-in for the packaged upstream ``skills/caveman/SKILL.md``."""
    root = tmp_path_factory.mktemp("caveman-installer")
    payload = root / "skills" / "caveman" / "SKILL.md"
    payload.parent.mkdir(parents=True)
    payload.write_text(_UPSTREAM_SKILL, encoding="utf-8")
    return payload


def _layers(**enabled: bool) -> dict[str, dict[str, object]]:
    """A ``resolve_context_layers``-shaped mapping with the named layers on.

    Built through the REAL composition site rather than hand-spelled, so a
    change to the resolved entry shape (a third key, a renamed layer) breaks
    these tests instead of leaving them asserting against a shape nothing
    produces."""
    declared = {layer.replace("_", "-"): {"enabled": value} for layer, value in enabled.items()}
    effective, _ = policy.compose(project_slug="pyforge-marshal", project={"context": declared}, flags={})
    return policy.resolve_context_layers(effective)


_ALL_ON = dict(wire=True, output=True, structure_graph=True)


def _available(_item: KitItem) -> InstrumentProbe:
    return InstrumentProbe(available=True)


def _payload_probe(payload: Path):
    def probe(item: KitItem) -> InstrumentProbe:
        if item.id is KitItemId.CAVEMAN_SKILL:
            return InstrumentProbe(available=True, payload=payload)
        return InstrumentProbe(available=True)

    return probe


def _unavailable(*ids: KitItemId):
    def probe(item: KitItem) -> InstrumentProbe:
        if item.id in ids:
            return InstrumentProbe(
                available=False,
                reason=f"{item.instrument} is not installed here (test)",
            )
        return InstrumentProbe(available=True)

    return probe


class _RecordingFs(LocalFs):
    """A real ``LocalFs`` that records every write it is asked to make, so a
    dry run can be proven to have written NOTHING rather than merely to have
    produced no visible change."""

    def __init__(self) -> None:
        self.writes: list[Path] = []

    def ensure_dir(self, path: Path) -> None:
        self.writes.append(path)
        super().ensure_dir(path)

    def write_text_atomic(self, path: Path, content: str) -> None:
        self.writes.append(path)
        super().write_text_atomic(path, content)


class _RefusingFs(LocalFs):
    """Every write fails -- the "a real attempt did not work" branch."""

    def ensure_dir(self, path: Path) -> None:
        raise FsError(f"cannot create directory {path}: refused by test")

    def write_text_atomic(self, path: Path, content: str) -> None:
        raise FsError(f"cannot write {path}: refused by test")


# --- model: the closed vocabulary ------------------------------------------


def test_every_kit_item_names_a_real_context_layer():
    """``seed/model/kit.py`` keeps ``layer`` a plain ``str`` to stay a
    dependency-free leaf; this is the binding that makes that safe. A layer
    renamed in ``core/policy.py`` must not silently orphan a kit item."""
    for item in KIT_ITEMS:
        assert item.layer in policy.CONTEXT_LAYER_NAMES, item


def test_ccr_store_relpath_matches_the_packaged_claude_wrapper():
    """Story 28.2's own still-open review finding, closed here: the CCR
    store path is declared in two places (the packaged wrapper TOML and this
    kit item) and nothing bound them, so relocating the store would have
    left the kit provisioning and checking a directory nothing uses."""
    wrapper = load_packaged_profiles()["claude"].wrapper
    assert wrapper is not None
    assert CCR_STORE_RELPATH == wrapper.store_relpath


def test_every_kit_item_id_has_exactly_one_entry():
    assert {item.id for item in KIT_ITEMS} == set(KitItemId)
    assert len(KIT_ITEMS) == len(KitItemId)
    for member in KitItemId:
        assert kit_item(member).id is member


def test_kit_item_lookup_rejects_an_unknown_id():
    with pytest.raises(ValueError):
        kit_item("not-a-kit-item")


def test_kit_items_for_layer_partitions_the_kit():
    assert kit_items_for_layer("output") == (kit_item(KitItemId.CAVEMAN_SKILL),)
    assert kit_items_for_layer("wire") == (kit_item(KitItemId.CCR_STORE),)
    assert kit_items_for_layer("planning-graph") == ()


def test_item_present_is_keyed_off_is_dir_not_a_per_item_branch(tmp_path):
    """`KitItem.is_dir` is read, not decorative: presence is answered from
    DATA for all three items."""
    store = kit_item(KitItemId.CCR_STORE)
    skill = kit_item(KitItemId.CAVEMAN_SKILL)
    reads = local_reads()

    (tmp_path / "as-dir").mkdir()
    (tmp_path / "as-file").write_text("x", encoding="utf-8")

    assert item_present(store, tmp_path / "as-dir", reads) is True
    assert item_present(store, tmp_path / "as-file", reads) is False
    assert item_present(skill, tmp_path / "as-file", reads) is True
    assert item_present(skill, tmp_path / "as-dir", reads) is False
    assert item_present(skill, tmp_path / "absent", reads) is False


def test_every_kit_item_declares_a_summary_a_report_can_use(home):
    """`KitItem.summary` is read by the dry-run outcome, so `marshal seed
    kit` explains what it would provision rather than only naming a path."""
    result = run_kit(home, _layers(**_ALL_ON), _VERSION, fs=LocalFs(), probe=_available)

    for item in KIT_ITEMS:
        assert item.summary
        outcome = next(o for o in result.outcomes if o.item_id == item.id.value)
        assert item.summary in outcome.detail


def test_articulate_region_name_is_marker_safe():
    assert REGION_NAME_PATTERN.fullmatch(ARTICULATE_REGION) is not None


# --- AC 2: verdicts, journals and escalation context stay articulate -------


def test_articulate_carve_out_names_every_contract_surface():
    """AC 2, structurally: the deployed skill's carve-out must name the
    verdict, the journal, escalation context and the story contract. If a
    surface is added to ``ARTICULATE_SURFACES`` and the body stops rendering
    it, this fails."""
    body = articulate_region_body()
    for surface in ARTICULATE_SURFACES:
        assert surface in body
    lowered = body.lower()
    for keyword in ("verdict", "journal", "escalation", "acceptance criteria"):
        assert keyword in lowered


def test_articulate_surfaces_cover_the_specs_never_compress_list():
    """The spec's "Never compress the contract" names story specs,
    acceptance criteria, gate verdicts and escalation context; AC 2 adds
    journals. All five must be reachable from the declared list."""
    joined = " ".join(ARTICULATE_SURFACES).lower()
    for keyword in ("verdict", "journal", "escalation", "spec", "acceptance criteria"):
        assert keyword in joined


def test_deployed_skill_preserves_upstream_bytes_and_appends_the_region():
    rendered = render_deployed_skill(_UPSTREAM_SKILL, _VERSION)

    assert rendered.startswith(_UPSTREAM_SKILL)
    spans = parse_regions(rendered, RegionFormat.HTML)
    assert [span.name for span in spans] == [ARTICULATE_REGION]
    body = rendered[spans[0].body_span[0] : spans[0].body_span[1]]
    assert articulate_region_body() in body


def test_deployed_skill_tolerates_an_upstream_without_a_trailing_newline():
    rendered = render_deployed_skill("no trailing newline", _VERSION)

    assert rendered.startswith("no trailing newline\n")
    assert [span.name for span in parse_regions(rendered, RegionFormat.HTML)] == [ARTICULATE_REGION]


# --- AC 4: layers off raise nothing ----------------------------------------


def test_layers_off_produce_three_checks_and_zero_findings(home):
    """AC 4: "the kit is declared-off, not missing"."""
    checks = kit_checks(home, _layers())

    assert len(checks) == 3
    assert {check.status for check in checks} == {KitStatus.OFF}
    assert kit_findings(checks) == ()


def test_layers_off_never_touch_the_filesystem(home):
    """An off layer must not even probe -- a probe that ran would be an
    instrument call for a layer nobody enabled."""

    def exploding_probe(item: KitItem) -> InstrumentProbe:  # pragma: no cover
        raise AssertionError(f"probed {item.id} for a layer that is off")

    checks = kit_checks(home, _layers(), probe=exploding_probe)
    assert {check.status for check in checks} == {KitStatus.OFF}


def test_absent_or_partial_context_mapping_reads_as_off(home):
    assert layer_enabled(None, "wire") is False
    assert layer_enabled({}, "wire") is False
    assert layer_enabled({"wire": "yes"}, "wire") is False
    assert layer_enabled({"wire": {}}, "wire") is False
    assert layer_enabled({"wire": {"enabled": True}}, "wire") is True
    assert kit_findings(kit_checks(home, None)) == ()


def test_unresolved_auto_reads_as_off(home):
    """Story 46.4: this probe has no harness-profile seam to resolve the
    repo-default ``"auto"`` tri-state against, so it must not fall into
    ``bool("auto") is True`` and probe wire for every harness."""
    assert layer_enabled({"wire": {"enabled": "auto"}}, "wire") is False


# --- AC 1: three distinct checks -------------------------------------------


def test_three_distinct_checks_one_per_kit_item(home):
    checks = kit_checks(home, _layers(**_ALL_ON), probe=_available)

    assert [check.item_id for check in checks] == [
        "caveman-skill",
        "ccr-store",
        "codegraph-index",
    ]
    assert [check.layer for check in checks] == ["output", "wire", "structure-graph"]
    assert len({check.item_id for check in checks}) == 3


def test_nothing_provisioned_reports_each_item_missing(home):
    checks = kit_checks(home, _layers(**_ALL_ON), probe=_available)

    assert {check.status for check in checks} == {KitStatus.MISSING}
    findings = kit_findings(checks)
    assert len(findings) == 3
    assert {finding.type for finding in findings} == {FindingType.KIT_ITEM_MISSING}
    assert {finding.severity for finding in findings} == {Severity.DRIFT}


def test_a_deployed_skill_with_an_emptied_carve_out_is_not_conformant(home, skill_payload):
    """Marker presence is not the guarantee -- the BODY is. A region emptied
    between two intact markers leaves nothing telling the session to keep
    verdicts articulated, so it must not read `ok`."""
    deployed = render_deployed_skill(_UPSTREAM_SKILL, _VERSION)
    spans = parse_regions(deployed, RegionFormat.HTML)
    gutted = deployed[: spans[0].body_span[0]] + "\n" + deployed[spans[0].body_span[1] :]
    # Markers survive the gutting -- that is the whole point of the case.
    assert [span.name for span in parse_regions(gutted, RegionFormat.HTML)] == [ARTICULATE_REGION]
    skill = home / ".claude" / "skills" / "caveman" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text(gutted, encoding="utf-8")

    checks = kit_checks(home, _layers(output=True), probe=_payload_probe(skill_payload))
    caveman = next(check for check in checks if check.item_id == "caveman-skill")

    assert caveman.status is KitStatus.MISSING
    assert "no longer matches" in caveman.detail


def test_non_ascii_upstream_content_before_the_region_is_still_conformant(home, tmp_path_factory):
    """Regression (live incident, 2026-09-10): ``RegionSpan.body_span`` is a
    BYTE offset (``regions/parse.py``'s own documented contract), but
    ``_carve_out_state`` used to slice the `str` directly with it
    (``text[start:end]``) instead of byte-slicing
    (``detect/hashes.py::region_body_text``). Any non-ASCII content in the
    upstream skill BEFORE the region -- exactly what the real packaged
    caveman SKILL.md carries -- desynced byte and character offsets enough
    that a freshly, correctly-deployed carve-out read as `no longer
    matches`, and `run_kit` silently re-applied it on every single
    preflight forever. A pure-ASCII upstream (this file's own
    `_UPSTREAM_SKILL` fixture) can never reproduce this -- byte and
    character offsets coincide for ASCII text -- so this test uses its own
    non-ASCII upstream body instead."""
    upstream = "---\nname: caveman\n---\n\nRespond tersely, caveman-style — no fluff ✅.\n"
    root = tmp_path_factory.mktemp("caveman-installer-unicode")
    payload = root / "skills" / "caveman" / "SKILL.md"
    payload.parent.mkdir(parents=True)
    payload.write_text(upstream, encoding="utf-8")
    deployed = render_deployed_skill(upstream, _VERSION)
    skill = home / ".claude" / "skills" / "caveman" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text(deployed, encoding="utf-8")

    checks = kit_checks(home, _layers(output=True), probe=_payload_probe(payload))
    caveman = next(check for check in checks if check.item_id == "caveman-skill")

    assert caveman.status is KitStatus.OK, caveman.detail


def test_a_hand_edited_carve_out_body_is_not_conformant(home, skill_payload):
    deployed = render_deployed_skill(_UPSTREAM_SKILL, _VERSION)
    tampered = deployed.replace("escalation context handed to a human", "escalation context (optional)")
    assert tampered != deployed
    skill = home / ".claude" / "skills" / "caveman" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text(tampered, encoding="utf-8")

    checks = kit_checks(home, _layers(output=True), probe=_payload_probe(skill_payload))

    assert next(c for c in checks if c.item_id == "caveman-skill").status is KitStatus.MISSING


def test_a_fully_provisioned_home_is_green(home, skill_payload):
    (home / ".marshal" / "wire").mkdir(parents=True)
    skill = home / ".claude" / "skills" / "caveman" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text(render_deployed_skill(_UPSTREAM_SKILL, _VERSION), encoding="utf-8")
    index = home / ".codegraph" / "codegraph.db"
    index.parent.mkdir(parents=True)
    index.write_bytes(b"index")

    checks = kit_checks(home, _layers(**_ALL_ON), probe=_payload_probe(skill_payload))

    assert {check.status for check in checks} == {KitStatus.OK}, checks
    assert kit_findings(checks) == ()


def test_a_deployed_skill_without_the_carve_out_is_not_conformant(home, skill_payload):
    """AC 2 again, from the check side: an operator (or a future upstream
    installer) that dropped the raw skill in place gets told the carve-out
    is missing, not that the kit is fine."""
    skill = home / ".claude" / "skills" / "caveman" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text(_UPSTREAM_SKILL, encoding="utf-8")

    checks = kit_checks(home, _layers(output=True), probe=_payload_probe(skill_payload))
    caveman = next(check for check in checks if check.item_id == "caveman-skill")

    assert caveman.status is KitStatus.MISSING
    assert ARTICULATE_REGION in caveman.detail
    assert "articulated" in caveman.detail


def test_ccr_store_must_be_a_directory(home):
    store = home / ".marshal" / "wire"
    store.parent.mkdir(parents=True)
    store.write_text("not a directory", encoding="utf-8")

    checks = kit_checks(home, _layers(wire=True), probe=_available)
    store_check = next(check for check in checks if check.item_id == "ccr-store")

    assert store_check.status is KitStatus.MISSING


# --- AC 1: "present AND FRESH" ---------------------------------------------


def test_an_index_older_than_head_is_stale(home):
    index = home / ".codegraph" / "codegraph.db"
    index.parent.mkdir(parents=True)
    index.write_bytes(b"index")
    os.utime(index, (0, 0))

    checks = kit_checks(home, _layers(structure_graph=True), probe=_available)
    index_check = next(check for check in checks if check.item_id == "codegraph-index")

    assert index_check.status is KitStatus.STALE
    findings = kit_findings(checks)
    assert [finding.type for finding in findings] == [FindingType.KIT_ITEM_STALE]
    assert findings[0].severity is Severity.DRIFT


def test_an_index_at_or_after_head_is_fresh(home):
    index = home / ".codegraph" / "codegraph.db"
    index.parent.mkdir(parents=True)
    index.write_bytes(b"index")

    checks = kit_checks(home, _layers(structure_graph=True), probe=_available)
    index_check = next(check for check in checks if check.item_id == "codegraph-index")

    assert index_check.status is KitStatus.OK
    assert kit_findings(checks) == ()


def test_no_staleness_claim_when_git_cannot_answer(tmp_path):
    """A non-repo directory: presence alone is reported, and the detail says
    so rather than implying freshness was verified."""
    index = tmp_path / ".codegraph" / "codegraph.db"
    index.parent.mkdir(parents=True)
    index.write_bytes(b"index")
    os.utime(index, (0, 0))

    checks = kit_checks(tmp_path, _layers(structure_graph=True), probe=_available)
    index_check = next(check for check in checks if check.item_id == "codegraph-index")

    assert index_check.status is KitStatus.OK
    assert "freshness not evaluated" in index_check.detail


# --- AC 3: graceful degradation, named -------------------------------------


def test_an_unavailable_instrument_is_named_at_info_severity(home):
    checks = kit_checks(home, _layers(**_ALL_ON), probe=_unavailable(KitItemId.CODEGRAPH_INDEX))
    findings = kit_findings(checks)

    degraded = [f for f in findings if f.type is FindingType.KIT_INSTRUMENT_UNAVAILABLE]
    assert len(degraded) == 1
    assert degraded[0].severity is Severity.INFO
    # "exactly which instrument and why" -- the operator-facing package
    # name, not only the probe binary.
    assert "codegraph" in degraded[0].message
    assert "not installed here" in degraded[0].message


def test_no_kit_finding_is_ever_hard(home):
    """The spec's "never blocks a run", made structural: HARD is the only
    severity that fails ``marshal seed check`` unconditionally."""
    for probe in (_available, _unavailable(*list(KitItemId))):
        findings = kit_findings(kit_checks(home, _layers(**_ALL_ON), probe=probe))
        assert findings
        assert all(finding.severity is not Severity.HARD for finding in findings)


def test_probe_reports_a_missing_binary_and_a_missing_payload_differently():
    caveman = kit_item(KitItemId.CAVEMAN_SKILL)

    absent = probe_instrument(caveman, which=lambda _name: None)
    assert absent.available is False
    assert "not on PATH" in absent.reason

    # Binary present, payload not where the packaged layout puts it.
    present_but_broken = probe_instrument(caveman, which=lambda _name: "/nonexistent/bin/caveman-install")
    assert present_but_broken.available is False
    assert "packaged skill payload" in present_but_broken.reason


def test_skill_source_resolves_from_the_installer_binary_layout(tmp_path):
    """The documented conda layout: ``<root>/bin/install.js`` beside
    ``<root>/skills/caveman/SKILL.md``."""
    root = tmp_path / "caveman-installer"
    (root / "bin").mkdir(parents=True)
    binary = root / "bin" / "install.js"
    binary.write_text("#!/usr/bin/env node\n", encoding="utf-8")
    payload = root / "skills" / "caveman" / "SKILL.md"
    payload.parent.mkdir(parents=True)
    payload.write_text(_UPSTREAM_SKILL, encoding="utf-8")

    assert resolve_caveman_skill_source(lambda _name: str(binary)) == payload
    assert resolve_caveman_skill_source(lambda _name: None) is None


# --- the apply verb --------------------------------------------------------


def test_dry_run_writes_nothing_and_reports_what_it_would_do(home, skill_payload):
    fs = _RecordingFs()

    result = run_kit(
        home,
        _layers(**_ALL_ON),
        _VERSION,
        fs=fs,
        apply=False,
        probe=_payload_probe(skill_payload),
        index_builder=lambda _root, **_kw: pytest.fail("dry run built an index"),
    )

    assert fs.writes == []
    assert {outcome.action for outcome in result.outcomes} == {KitAction.PLANNED}
    assert result.applied is False
    assert not (home / ".marshal" / "wire").exists()


def test_apply_provisions_every_declared_item(home, skill_payload):
    built: list[Path] = []

    result = run_kit(
        home,
        _layers(**_ALL_ON),
        _VERSION,
        fs=LocalFs(),
        apply=True,
        probe=_payload_probe(skill_payload),
        index_builder=lambda root, *, stale: built.append((root, stale)) or _touch_index(root, stale=stale),
    )

    assert built == [(home, False)]
    assert (home / ".marshal" / "wire").is_dir()
    skill = home / ".claude" / "skills" / "caveman" / "SKILL.md"
    assert skill.is_file()
    assert _UPSTREAM_SKILL in skill.read_text(encoding="utf-8")
    assert [span.name for span in parse_regions(skill.read_text(encoding="utf-8"), RegionFormat.HTML)] == [
        ARTICULATE_REGION
    ]
    assert {outcome.action for outcome in result.outcomes} == {KitAction.APPLIED}
    # The post-apply verification is the same detector `seed check` uses.
    assert {check.status for check in result.checks} == {KitStatus.OK}
    assert result.findings == ()


def _touch_index(root: Path, *, stale: bool) -> None:
    """Stand-in for a real ``codegraph init``/``sync`` run. Accepts the
    ``stale`` keyword the ``IndexBuilder`` protocol declares, so a test
    double cannot silently diverge from what production is called with."""
    index = root / ".codegraph" / "codegraph.db"
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_bytes(b"index")
    return None


def test_apply_is_idempotent(home, skill_payload):
    kwargs = dict(
        fs=LocalFs(),
        apply=True,
        probe=_payload_probe(skill_payload),
        index_builder=_touch_index,
    )
    run_kit(home, _layers(**_ALL_ON), _VERSION, **kwargs)

    fs = _RecordingFs()
    second = run_kit(
        home,
        _layers(**_ALL_ON),
        _VERSION,
        fs=fs,
        apply=True,
        probe=_payload_probe(skill_payload),
        index_builder=lambda _root, **_kw: pytest.fail("re-indexed an up-to-date home"),
    )

    assert fs.writes == []
    assert {outcome.action for outcome in second.outcomes} == {KitAction.PRESENT}
    assert second.findings == ()


def test_an_unavailable_instrument_skips_its_layer_and_the_rest_still_applies(home, skill_payload):
    """AC 3, the whole sentence: the seed still applies, the layer is
    skipped, and a named finding reports exactly which instrument and why."""
    result = run_kit(
        home,
        _layers(**_ALL_ON),
        _VERSION,
        fs=LocalFs(),
        apply=True,
        probe=_unavailable(KitItemId.CAVEMAN_SKILL),
        index_builder=_touch_index,
    )

    by_item = {outcome.item_id: outcome for outcome in result.outcomes}
    assert by_item["caveman-skill"].action is KitAction.SKIPPED
    assert "caveman is not installed here" in by_item["caveman-skill"].detail
    # ... and the seed still applied everything else.
    assert by_item["ccr-store"].action is KitAction.APPLIED
    assert by_item["codegraph-index"].action is KitAction.APPLIED
    assert (home / ".marshal" / "wire").is_dir()

    assert [finding.type for finding in result.findings] == [FindingType.KIT_INSTRUMENT_UNAVAILABLE]
    assert result.findings[0].severity is Severity.INFO
    assert "caveman" in result.findings[0].message


def test_a_failed_write_is_reported_not_raised(home, skill_payload):
    result = run_kit(
        home,
        _layers(wire=True),
        _VERSION,
        fs=_RefusingFs(),
        apply=True,
        probe=_payload_probe(skill_payload),
    )

    store = next(outcome for outcome in result.outcomes if outcome.item_id == "ccr-store")
    assert store.action is KitAction.FAILED
    assert "refused by test" in store.detail
    finding = next(f for f in result.findings if f.type is FindingType.KIT_ITEM_MISSING)
    assert "the provisioning step failed" in finding.message
    assert "refused by test" in finding.message
    assert finding.severity is Severity.DRIFT


def test_a_failed_index_build_is_reported_not_raised(home):
    result = run_kit(
        home,
        _layers(structure_graph=True),
        _VERSION,
        fs=LocalFs(),
        apply=True,
        probe=_available,
        index_builder=lambda _root, **_kw: "codegraph init exited 1: kernel missing",
    )

    index = next(o for o in result.outcomes if o.item_id == "codegraph-index")
    assert index.action is KitAction.FAILED
    assert "kernel missing" in index.detail
    assert {f.type for f in result.findings} == {FindingType.KIT_ITEM_MISSING}


def test_apply_with_every_layer_off_writes_nothing_and_finds_nothing(home):
    fs = _RecordingFs()

    result = run_kit(home, _layers(), _VERSION, fs=fs, apply=True)

    assert fs.writes == []
    assert {outcome.action for outcome in result.outcomes} == {KitAction.SKIPPED}
    assert result.findings == ()


def test_a_stale_index_asks_the_builder_to_REFRESH_not_create(home):
    """The `stale` flag reaches the builder. Asserted on what the builder was
    TOLD, not on the outcome string -- that string is derived from the check
    status in the same function, so it would read "resynced" even for a
    builder that could not tell create from refresh."""
    index = home / ".codegraph" / "codegraph.db"
    index.parent.mkdir(parents=True)
    index.write_bytes(b"index")
    os.utime(index, (0, 0))
    calls: list[tuple[Path, bool]] = []

    def builder(root: Path, *, stale: bool) -> None:
        calls.append((root, stale))
        return None

    result = run_kit(
        home,
        _layers(structure_graph=True),
        _VERSION,
        fs=LocalFs(),
        apply=True,
        probe=_available,
        index_builder=builder,
    )

    assert calls == [(home, True)]
    outcome = next(o for o in result.outcomes if o.item_id == "codegraph-index")
    assert outcome.action is KitAction.APPLIED
    assert "resynced" in outcome.detail
    assert result.findings == ()


def test_an_absent_index_asks_the_builder_to_CREATE(home):
    calls: list[tuple[Path, bool]] = []

    def builder(root: Path, *, stale: bool) -> None:
        calls.append((root, stale))
        _touch_index(root, stale=stale)
        return None

    run_kit(
        home,
        _layers(structure_graph=True),
        _VERSION,
        fs=LocalFs(),
        apply=True,
        probe=_available,
        index_builder=builder,
    )

    assert calls == [(home, False)]


def test_a_successful_sync_stamps_the_index_so_drift_cannot_become_permanent(home):
    """`codegraph sync` with nothing to resync succeeds WITHOUT touching the
    db. Without the post-step stamp the index keeps its pre-HEAD mtime, the
    re-check keeps reporting `stale`, and every subsequent run re-syncs and
    re-reports DRIFT forever."""
    index = home / ".codegraph" / "codegraph.db"
    index.parent.mkdir(parents=True)
    index.write_bytes(b"index")
    os.utime(index, (0, 0))

    result = run_kit(
        home,
        _layers(structure_graph=True),
        _VERSION,
        fs=LocalFs(),
        apply=True,
        probe=_available,
        # A no-op builder: succeeds, changes nothing -- the exact shape of a
        # sync with nothing to do.
        index_builder=lambda _root, *, stale: None,
    )

    assert [check.status for check in result.checks if check.item_id == "codegraph-index"] == [KitStatus.OK]
    assert result.findings == ()


def test_a_failed_step_is_reported_even_when_the_recheck_reads_ok(home):
    """A build killed at the timeout can leave a partial `codegraph.db` with
    a fresh mtime -- present and fresh to the detector. Without an
    always-report rule the failure would exist only as a `KitOutcome` and the
    operator would be told the kit is green."""

    def partial_then_fail(root: Path, *, stale: bool) -> str:
        _touch_index(root, stale=stale)
        return "codegraph init timed out after 900.0s"

    result = run_kit(
        home,
        _layers(structure_graph=True),
        _VERSION,
        fs=LocalFs(),
        apply=True,
        probe=_available,
        index_builder=partial_then_fail,
    )

    assert [c.status for c in result.checks if c.item_id == "codegraph-index"] == [KitStatus.OK]
    assert [f.type for f in result.findings] == [FindingType.KIT_ITEM_STALE]
    assert "timed out" in result.findings[0].message
    assert "may be partial" in result.findings[0].message


# --- the real index builder's argv, flags and ceilings ---------------------


class _RecordingProcess:
    """Records what `build_codegraph_index` would actually run."""

    def __init__(self, returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.calls: list[tuple[list[str], Path, float | None]] = []
        self._result = ProcessResult(returncode=returncode, stdout=stdout, stderr=stderr)

    def run(self, argv, *, cwd, timeout_s=None):
        self.calls.append((list(argv), cwd, timeout_s))
        return self._result


def test_a_first_build_runs_codegraph_init_not_index(tmp_path):
    """The vendor-behaviour correction, pinned. `codegraph index --help`
    reads as though it would serve for a first build ("same result as a
    fresh init"); run against a directory with no `.codegraph/` it exits 1
    with `Run "codegraph init" first`. A "simplification" back to `index`
    must fail here, not merely contradict a docstring."""
    process = _RecordingProcess()

    assert build_codegraph_index(tmp_path, stale=False, process=process) is None

    argv, cwd, timeout = process.calls[0]
    assert argv == ["codegraph", "init", "-y", str(tmp_path)]
    assert cwd == tmp_path
    assert timeout == INDEX_TIMEOUT_S


def test_a_refresh_runs_codegraph_sync_quietly(tmp_path):
    process = _RecordingProcess()

    assert build_codegraph_index(tmp_path, stale=True, process=process) is None

    argv, _cwd, timeout = process.calls[0]
    assert argv == ["codegraph", "sync", "-q", str(tmp_path)]
    assert timeout == SYNC_TIMEOUT_S


def test_a_nonzero_exit_becomes_a_reason_naming_the_command_and_its_last_line(tmp_path):
    process = _RecordingProcess(returncode=1, stderr='noise\nRun "codegraph init" first\n')

    reason = build_codegraph_index(tmp_path, stale=False, process=process)

    assert reason is not None
    assert "codegraph init -y" in reason
    assert "exited 1" in reason
    assert 'Run "codegraph init" first' in reason


def test_a_process_failure_becomes_a_reason_never_a_raise(tmp_path):
    class _Boom:
        def run(self, argv, *, cwd, timeout_s=None):
            raise ProcessError("command timed out after 900.0s: codegraph init")

    reason = build_codegraph_index(tmp_path, stale=False, process=_Boom())

    assert reason is not None
    assert "timed out" in reason


def test_the_timeout_note_is_derived_from_the_constants_not_restated():
    note = timeout_note()

    assert f"{INDEX_TIMEOUT_S:.0f}s" in note
    assert f"{SYNC_TIMEOUT_S:.0f}s" in note


# --- the verification observes the port the writes went through ------------


class _PortOnlyFs:
    """An `FsPort`-shaped double whose files exist ONLY in memory -- the
    shape of any non-local port. `run_kit` must verify through it, or it
    reports its own successful applies as missing."""

    def __init__(self) -> None:
        self.dirs: set[Path] = set()
        self.texts: dict[Path, str] = {}

    def ensure_dir(self, path: Path) -> None:
        self.dirs.add(path)

    def write_text_atomic(self, path: Path, content: str) -> None:
        self.texts[path] = content

    def exists(self, path: Path) -> bool:
        return path in self.dirs or path in self.texts

    def is_dir(self, path: Path) -> bool:
        return path in self.dirs

    def read_text(self, path: Path) -> str | None:
        return self.texts.get(path)


def test_post_apply_verification_reads_the_same_port_the_writes_went_through(home, skill_payload):
    fs = _PortOnlyFs()

    result = run_kit(
        home,
        _layers(wire=True, output=True),
        _VERSION,
        fs=fs,
        apply=True,
        probe=_payload_probe(skill_payload),
    )

    assert {o.action for o in result.outcomes if o.action is not KitAction.SKIPPED} == {KitAction.APPLIED}
    # Nothing landed on the real filesystem -- so a raw-Path verification
    # would report both applies as MISSING and emit DRIFT for them.
    assert not (home / ".marshal" / "wire").exists()
    assert {c.status for c in result.checks if c.status is not KitStatus.OFF} == {KitStatus.OK}
    assert result.findings == ()


# --- integration with `marshal seed check` ---------------------------------


def test_run_check_without_context_layers_is_byte_identical(home):
    """Every pre-28.3 caller: no kit section, no kit findings."""
    report = run_check(home, _manifest(_whole_file("whole", "WHOLE.md")))

    assert report.kit == ()
    assert all(not finding.type.value.startswith("kit-") for finding in report.findings)


def test_run_check_with_layers_off_reports_three_checks_and_no_kit_findings(home):
    report = run_check(home, _manifest(_whole_file("whole", "WHOLE.md")), context_layers=_layers())

    assert len(report.kit) == 3
    assert {check.status for check in report.kit} == {KitStatus.OFF}
    assert all(not finding.type.value.startswith("kit-") for finding in report.findings)


def test_run_check_surfaces_kit_drift_but_never_fails_on_it_unstrict(home, monkeypatch):
    # Availability is DECIDED here, never inherited from the machine: with a
    # bare PATH (CI installs only the `pyforge-marshal` env, which declares
    # none of the three instruments; macOS cannot install two of them at all)
    # this would otherwise report `instrument-unavailable` instead of the
    # missing-item drift the test is about.
    monkeypatch.setattr("shutil.which", lambda _name: "/usr/bin/headroom")

    report = run_check(
        home,
        _manifest(),
        context_layers=_layers(wire=True),
    )

    kit_only = [f for f in report.findings if f.type.value.startswith("kit-")]
    assert [f.type for f in kit_only] == [FindingType.KIT_ITEM_MISSING]
    assert report.by_severity(Severity.HARD) == ()
    assert report.failing is False


def test_an_unavailable_instrument_never_fails_check_even_under_strict(home, monkeypatch):
    """An unavailable instrument is INFO, and INFO is the one severity
    ``CheckReport.failing`` ignores in BOTH modes -- so this finding cannot
    contribute to a red check even under ``--strict``. Asserted on the
    finding's own severity rather than on ``report.failing``: a
    never-adopted repo is already DRIFT ``model-behind``, so the aggregate
    verdict here is red for a reason that has nothing to do with the kit,
    and asserting on it would prove nothing."""
    monkeypatch.setattr("shutil.which", lambda _name: None)

    report = run_check(home, _manifest(), strict=True, context_layers=_layers(output=True))

    kit_only = [f for f in report.findings if f.type.value.startswith("kit-")]
    assert [f.type for f in kit_only] == [FindingType.KIT_INSTRUMENT_UNAVAILABLE]
    assert [f.severity for f in kit_only] == [Severity.INFO]
    assert not set(kit_only) & set(report.by_severity(Severity.DRIFT))
    assert not set(kit_only) & set(report.by_severity(Severity.HARD))


def test_check_json_payload_carries_the_kit_section(home):
    report = run_check(home, _manifest(), context_layers=_layers())
    payload = json.loads(json.dumps(report.to_json_dict()))

    assert [entry["item"] for entry in payload["kit"]] == [
        "caveman-skill",
        "ccr-store",
        "codegraph-index",
    ]
    for entry in payload["kit"]:
        assert set(entry) == {"item", "layer", "instrument", "path", "status", "detail"}


# --- the CLI verb ----------------------------------------------------------


def _kit_args(root: Path, **overrides: object) -> argparse.Namespace:
    base = dict(
        repo_root=str(root),
        apply=False,
        project=None,
        dry_run=False,
        json=False,
        quiet=False,
    )
    base.update(overrides)
    return argparse.Namespace(**base)


def test_cli_kit_exits_zero_even_when_nothing_could_be_provisioned(home, monkeypatch, capsys):
    """This story's own Never bullet: never block a seed on a missing
    optional instrument."""
    monkeypatch.setattr("shutil.which", lambda _name: None)
    monkeypatch.setenv("BMAD_ACTIVE_PROJECT", "pyforge-marshal")
    _declare_layers(home, "pyforge-marshal", wire=True, output=True)

    exit_code = seed_cli.run_kit(_kit_args(home, apply=True), manifest=_manifest())

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "token-economy kit" in out


def test_cli_kit_json_envelope_is_schema_stable(home, capsys):
    exit_code = seed_cli.run_kit(_kit_args(home, json=True), manifest=_manifest())

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["verb"] == "kit"
    assert payload["ok"] is True
    assert set(payload["result"]) == {"applied", "outcomes", "checks", "findings"}


def test_cli_kit_refuses_dry_run_and_apply_together(home, capsys):
    exit_code = seed_cli.run_kit(_kit_args(home, apply=True, dry_run=True), manifest=_manifest())

    assert exit_code == 2
    assert "mutually exclusive" in capsys.readouterr().out


def test_cli_kit_routes_through_the_real_parser(home):
    """Nothing else in this file goes through `_build_parser`, so dropping
    `set_defaults(handler=run_kit)` or `_add_json_quiet_flags(kit_parser)`
    would break the CLI with every hand-built-Namespace test still green."""
    parser = _build_parser()

    args = parser.parse_args(["seed", "kit", "--repo-root", str(home), "--apply", "--json", "--quiet"])

    assert args.handler is seed_cli.run_kit
    assert args.seed_command == "kit"
    assert (args.repo_root, args.apply, args.json, args.quiet) == (str(home), True, True, True)
    assert args.dry_run is False
    assert args.project is None
    assert parser.parse_args(["seed", "kit"]).apply is False


def test_cli_kit_help_states_the_provisioning_ceiling(capsys):
    """P16: the 900s bound must be readable by an operator, not only by a
    reader of `verbs/kit.py`."""
    parser = _build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["seed", "kit", "--help"])

    out = capsys.readouterr().out
    assert f"{INDEX_TIMEOUT_S:.0f}s" in out


def test_cli_check_text_report_renders_the_three_kit_checks(home, capsys):
    """AC 1's operator-facing surface: deleting the kit section from
    `_render_check_report_text` must fail a test, not pass silently."""
    _declare_layers(home, "pyforge-marshal", wire=True)
    args = argparse.Namespace(repo_root=str(home), strict=False, project="pyforge-marshal", json=False, quiet=False)

    seed_cli.run_check(args, manifest=_manifest())

    out = capsys.readouterr().out
    assert "token-economy kit (3 check(s)):" in out
    for item_id in ("caveman-skill", "ccr-store", "codegraph-index"):
        assert item_id in out


def test_cli_kit_bad_repo_root_is_a_usage_error(tmp_path, capsys):
    exit_code = seed_cli.run_kit(_kit_args(tmp_path / "nope"), manifest=_manifest())

    assert exit_code == 2
    capsys.readouterr()


# --- policy resolution at the CLI boundary ---------------------------------


def _declare_layers(root: Path, slug: str, **enabled: bool) -> None:
    body = "\n".join(
        f'[context."{layer.replace("_", "-")}"]\nenabled = {str(value).lower()}' for layer, value in enabled.items()
    )
    path = root / "_bmad-output" / "projects" / slug / "planning-artifacts"
    path.mkdir(parents=True, exist_ok=True)
    (path / "marshal-policy.toml").write_text(body + "\n", encoding="utf-8")


def test_context_layers_come_from_the_target_repo_not_the_install_location(home, monkeypatch):
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    _declare_layers(home, "pyforge-marshal", wire=True)
    (home / "_bmad" / "custom").mkdir(parents=True)
    (home / "_bmad" / "custom" / ".active-project").write_text("pyforge-marshal\n", encoding="utf-8")

    layers = seed_cli.resolve_context_layers(home, None)

    assert layers["wire"]["enabled"] is True
    assert layers["output"]["enabled"] is False


def test_explicit_project_flag_beats_the_environment(home, monkeypatch):
    monkeypatch.setenv("BMAD_ACTIVE_PROJECT", "pyforge-atlas")
    _declare_layers(home, "pyforge-marshal", output=True)

    assert seed_cli.resolve_context_layers(home, "pyforge-marshal")["output"]["enabled"] is True
    assert seed_cli.resolve_context_layers(home, None)["output"]["enabled"] is False


def test_repo_defaults_layer_is_read_from_the_target_repo(home, monkeypatch):
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    (home / "_bmad-output").mkdir(parents=True, exist_ok=True)
    (home / "_bmad-output" / "policy-defaults.toml").write_text(
        '[context."structure-graph"]\nenabled = true\n', encoding="utf-8"
    )

    layers = seed_cli.resolve_context_layers(home, None)

    assert layers["structure-graph"]["enabled"] is True


def test_unreadable_or_malformed_policy_degrades_to_every_layer_off(home, monkeypatch):
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    (home / "_bmad-output").mkdir(parents=True, exist_ok=True)
    (home / "_bmad-output" / "policy-defaults.toml").write_text("this is not = = toml\n", encoding="utf-8")

    layers = seed_cli.resolve_context_layers(home, None)

    assert all(entry["enabled"] is False for entry in layers.values())


def test_no_project_resolves_to_every_layer_off(home, monkeypatch):
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)

    layers = seed_cli.resolve_context_layers(home, None)

    assert set(layers) == set(policy.CONTEXT_LAYER_NAMES)
    assert all(entry["enabled"] is False for entry in layers.values())
