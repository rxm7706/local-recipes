"""Unit tests for ``pyforge.marshal.seed.verbs.check`` (Story 10.5) -- covers
every row of the spec's I/O & Edge-Case Matrix: the never-adopted repo (every
materializable entry reported absent, model-behind, no traceback), the fully
conformant adopted repo (zero findings), a hand-edited managed whole-file
(one HARD finding), DRIFT-only findings with and without ``--strict``, a
corrupt state file (one HARD ``state-invalid`` finding, the rest of the run
still proceeds against an absent-state view), ``--json``'s stable shape, and
the repo-behind-model-version row (naming both versions, its exit-code effect
gated by which severity this story chose for it -- DRIFT).

Plus: the ``PRESENT_LEGACY``/``ArtifactClass.REFERENCED`` short-circuits (AD-59
-- never inspected again), the correctness gap ``build_plan`` composition
closes (a fully-opted-out ``ABSENT`` hybrid entry must not report
``ARTIFACT_MISSING`` -- see ``verbs/check.py``'s own module docstring), the
write-blocking fixture (no ``fs.write``/``replace_span``/``remove`` call, no
``.marshal/`` created), and a ``<5s`` timed test against the real packaged
manifest (NFR-P1), following ``pyforge-warden``'s ``time.perf_counter()``
pattern as precedent.

Manifest/git-repo builders mirror ``test_seed_plan_build.py``'s
``_manifest``/``_referenced``/``_whole_file``/``_hybrid`` and
``test_seed_verbs_preconditions.py``'s ``_git``/``_init_git_repo``/
``_commit_all`` real-git-repo convention (real ``git`` I/O against a
``tmp_path``, never mocked); the ``SeedState`` builder mirrors
``test_seed_state_store.py``'s ``_sample_state`` shape.
"""

from __future__ import annotations

import ast
import inspect
import json
import subprocess
import time
from importlib import resources
from pathlib import Path

import pytest

from pyforge.marshal.seed import fs
from pyforge.marshal.seed.detect.findings import FindingType, Severity
from pyforge.marshal.seed.detect.hashes import hash_content
from pyforge.marshal.seed.model.manifest import (
    AppliesTo,
    ArtifactClass,
    Manifest,
    ManifestEntry,
    Region,
    load_manifest,
)
from pyforge.marshal.seed.model.version import ModelVersion
from pyforge.marshal.seed.regions.markers import (
    RegionFormat,
    region_sha,
    render_begin,
    render_end,
)
from pyforge.marshal.seed.state import (
    ManagedArtifact,
    RegionSpanRecord,
    SeedState,
    opt_out_key,
    write_state,
)
from pyforge.marshal.seed.verbs import check as check_module
from pyforge.marshal.seed.verbs.check import CheckReport, ModelVersionStatus, run_check

_VERSION = ModelVersion.parse("1.0.0")
_NO_NEVER_WRITE = fs.NeverWrite(patterns=())


# --- manifest builders (mirrors test_seed_plan_build.py) -------------------


def _manifest(*entries: ManifestEntry, model_version: ModelVersion = _VERSION) -> Manifest:
    return Manifest(model_version=model_version, never_write=(), entries=tuple(entries))


def _referenced(entry_id: str, path: str = "unused", pin: str = ">=1.0") -> ManifestEntry:
    return ManifestEntry(
        id=entry_id,
        artifact_class=ArtifactClass.REFERENCED,
        path=path,
        applies_to=AppliesTo.BOTH,
        rationale="test",
        pin=pin,
    )


def _whole_file(entry_id: str, path: str, *, legacy_of: str | None = None) -> ManifestEntry:
    return ManifestEntry(
        id=entry_id,
        artifact_class=ArtifactClass.COPIED_MANAGED,
        path=path,
        applies_to=AppliesTo.BOTH,
        rationale="test",
        legacy_of=legacy_of,
    )


def _hybrid(entry_id: str, path: str, *region_names: str) -> ManifestEntry:
    return ManifestEntry(
        id=entry_id,
        artifact_class=ArtifactClass.HYBRID_MANAGED_REGION,
        path=path,
        applies_to=AppliesTo.BOTH,
        rationale="test",
        format=RegionFormat.HTML,
        regions=tuple(Region(name=name, anchor=("# anchor",)) for name in region_names),
    )


def _hybrid_text(name: str, body: str, fmt: RegionFormat = RegionFormat.HTML) -> str:
    return "".join(
        f"{line}\n"
        for line in (
            "intro",
            render_begin(fmt, name, _VERSION, region_sha(body)),
            body.rstrip("\n"),
            render_end(fmt, name),
            "outro",
        )
    )


# --- real-git fixtures (mirrors test_seed_verbs_preconditions.py) ----------


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    return result


def _init_git_repo(repo: Path) -> None:
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "initial")


def _commit_all(repo: Path) -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "fixture")


@pytest.fixture
def clean_repo(tmp_path: Path) -> Path:
    _init_git_repo(tmp_path)
    return tmp_path


# --- state builder (mirrors test_seed_state_store.py::_sample_state) -------


def _state(**overrides) -> SeedState:
    fields: dict = {
        "model_version": _VERSION,
        "seed_model_version": "0.1.0",
        "adopted_at": "2026-08-14T09:15:00Z",
        "last_update": "2026-08-14T11:42:07Z",
        "mode": "init",
        "agents": ("claude-code",),
        "managed": (),
        "skips": (),
        "legacy": (),
        "migrations_applied": (),
        "opted_out": (),
    }
    fields.update(overrides)
    return SeedState(**fields)


def _write_state(repo: Path, state: SeedState) -> None:
    write_state(state, repo_root=repo, never_write=_NO_NEVER_WRITE)


# --- never-adopted repo ------------------------------------------------


def test_never_adopted_repo_reports_every_materializable_entry_absent(clean_repo):
    """Row 1 of the I/O matrix: no ``.marshal/seed-state.yml`` at all --
    every non-``referenced`` entry is ``ARTIFACT_MISSING`` (HARD), the
    referenced entry is never reported, model_version is ``model-behind``
    with no recorded state version, and nothing raises."""
    manifest = _manifest(
        _referenced("ref"),
        _whole_file("whole", "WHOLE.md"),
        _hybrid("hybrid", "HYBRID.md", "tiers"),
    )

    report = run_check(clean_repo, manifest)

    missing_paths = {
        finding.path for finding in report.by_severity(Severity.HARD) if finding.type is FindingType.ARTIFACT_MISSING
    }
    assert missing_paths == {"WHOLE.md", "HYBRID.md"}
    assert report.model_version_status is ModelVersionStatus.BEHIND
    assert report.state_model_version is None
    assert report.failing is True


def test_referenced_entries_are_never_reported_absent(clean_repo):
    manifest = _manifest(_referenced("ref", path="https://example.com/not-a-real-file"))

    report = run_check(clean_repo, manifest)

    assert not any(finding.type is FindingType.ARTIFACT_MISSING for finding in report.findings)


# --- fully conformant adopted repo --------------------------------------


def test_fully_conformant_adopted_repo_reports_zero_findings(clean_repo):
    whole_body = "owned by genesis\n"
    (clean_repo / "WHOLE.md").write_text(whole_body, encoding="utf-8")
    region_body = "line1\n"
    (clean_repo / "HYBRID.md").write_text(_hybrid_text("tiers", region_body), encoding="utf-8")
    _commit_all(clean_repo)

    manifest = _manifest(
        _whole_file("whole", "WHOLE.md"),
        _hybrid("hybrid", "HYBRID.md", "tiers"),
    )
    state = _state(
        managed=(
            ManagedArtifact(
                id="whole",
                path="WHOLE.md",
                artifact_class="copied-managed",
                body_sha=hash_content(whole_body),
                inserted_region_span=None,
            ),
            ManagedArtifact(
                id="hybrid",
                path="HYBRID.md",
                artifact_class="hybrid-managed-region",
                body_sha=hash_content(region_body),
                inserted_region_span=RegionSpanRecord(name="tiers", start=0, end=len(region_body)),
            ),
        )
    )
    _write_state(clean_repo, state)
    _commit_all(clean_repo)

    report = run_check(clean_repo, manifest)

    assert report.findings == ()
    assert report.model_version_status is ModelVersionStatus.CURRENT
    assert report.failing is False


def test_referenced_entries_report_dep_missing_at_drift(clean_repo):
    """Story 11.5: a referenced entry below floor yields ``referenced-dep-missing``
    (DRIFT), never ``artifact-missing`` (HARD)."""
    manifest = _manifest(_referenced("ref", pin=">=99.0.0"))

    report = run_check(clean_repo, manifest)

    assert not any(finding.type is FindingType.ARTIFACT_MISSING for finding in report.findings)
    dep_findings = [f for f in report.findings if f.type is FindingType.REFERENCED_DEP_MISSING]
    assert len(dep_findings) == 1
    assert dep_findings[0].severity is Severity.DRIFT
    assert dep_findings[0].path == "ref"


# --- hand-edited managed file --------------------------------------------


def test_hand_edited_managed_file_is_one_hard_finding(clean_repo):
    (clean_repo / "WHOLE.md").write_text("hand edited\n", encoding="utf-8")
    _commit_all(clean_repo)

    manifest = _manifest(_whole_file("whole", "WHOLE.md"))
    state = _state(
        managed=(
            ManagedArtifact(
                id="whole",
                path="WHOLE.md",
                artifact_class="copied-managed",
                body_sha=hash_content("original\n"),
                inserted_region_span=None,
            ),
        )
    )
    _write_state(clean_repo, state)
    _commit_all(clean_repo)

    report = run_check(clean_repo, manifest)

    hard = report.by_severity(Severity.HARD)
    assert len(hard) == 1
    assert hard[0].type is FindingType.MANAGED_FILE_MODIFIED
    assert hard[0].path == "WHOLE.md"
    assert report.failing is True


def test_hand_edited_hybrid_region_body_is_one_hard_finding(clean_repo):
    """Mirrors ``test_hand_edited_managed_file_is_one_hard_finding`` for the
    region-body primitive (review finding -- no test previously exercised
    ``check_managed_region``'s HARD-finding branch through ``run_check``)."""
    (clean_repo / "HYBRID.md").write_text(_hybrid_text("tiers", "hand edited\n"), encoding="utf-8")
    _commit_all(clean_repo)

    manifest = _manifest(_hybrid("hybrid", "HYBRID.md", "tiers"))
    state = _state(
        managed=(
            ManagedArtifact(
                id="hybrid",
                path="HYBRID.md",
                artifact_class="hybrid-managed-region",
                body_sha=hash_content("original\n"),
                inserted_region_span=RegionSpanRecord(name="tiers", start=0, end=1),
            ),
        )
    )
    _write_state(clean_repo, state)
    _commit_all(clean_repo)

    report = run_check(clean_repo, manifest)

    hard = [f for f in report.by_severity(Severity.HARD) if f.path == "HYBRID.md"]
    assert len(hard) == 1
    assert hard[0].type is FindingType.MANAGED_REGION_MODIFIED
    assert report.failing is True


def test_stale_record_span_is_not_hashed_against_a_reclassified_entrys_whole_file(clean_repo):
    """Review finding: the hash-check primitive must be selected by
    ``record.inserted_region_span``, never by the manifest entry's CURRENT
    ``artifact_class`` alone -- an entry's class can be reclassified across
    model versions while ``state.managed[]``'s record still describes what
    was actually recorded (module docstring). Here the manifest currently
    declares ``whole`` as a whole-file (``copied-managed``) entry, but its
    recorded claim is stale from when it was ``hybrid-managed-region``. The
    pre-fix code would have entered the ``elif`` whole-file branch (gated
    on the CURRENT class) and hashed the whole file against a body_sha that
    was recorded for a REGION, producing a near-guaranteed spurious
    ``managed-file-modified`` HARD finding. The fixed code selects on
    ``record.inserted_region_span`` first, finds ``entry.format is None``
    (a whole-file entry declares no region format), and correctly runs no
    hash check at all rather than compare across an incompatible shape."""
    (clean_repo / "WHOLE.md").write_text("current whole-file content, never hand-edited\n", encoding="utf-8")
    _commit_all(clean_repo)

    manifest = _manifest(_whole_file("whole", "WHOLE.md"))
    state = _state(
        managed=(
            ManagedArtifact(
                id="whole",
                path="WHOLE.md",
                artifact_class="hybrid-managed-region",
                body_sha=hash_content("a stale region body, unrelated to the whole file"),
                inserted_region_span=RegionSpanRecord(name="tiers", start=0, end=5),
            ),
        )
    )
    _write_state(clean_repo, state)
    _commit_all(clean_repo)

    report = run_check(clean_repo, manifest)

    whole_findings = [f for f in report.findings if f.path == "WHOLE.md"]
    assert whole_findings == []


def test_record_at_a_stale_path_is_never_hashed_against_the_current_path(clean_repo):
    """Review finding, mirroring ``detect.optout._claims_region``'s
    already-fixed identical trap: AD-55 makes ``id``, not ``path``, the
    stable address, so a manifest entry's ``path`` can move while its
    ``id`` does not, and a stale record still names the OLD path. Comparing
    today's file at the CURRENT path against a claim describing a
    different, no-longer-current path is a false comparison -- the pre-fix
    ``managed_by_id`` lookup matched on ``id`` alone and would have hashed
    the (unrelated) current content against the stale record's body_sha,
    producing a spurious HARD finding purely from the id-only match
    (deliberately mismatched below to prove it). The fixed lookup drops a
    record whose ``path`` disagrees, falling through to "no record" (never
    a guess) exactly as ``_claims_region`` does."""
    (clean_repo / "WHOLE.md").write_text("current content, never hand-edited\n", encoding="utf-8")
    _commit_all(clean_repo)

    manifest = _manifest(_whole_file("whole", "WHOLE.md"))
    state = _state(
        managed=(
            ManagedArtifact(
                id="whole",
                path="OLD_WHOLE.md",  # stale -- the manifest entry's path has since moved
                artifact_class="copied-managed",
                body_sha=hash_content("stale content, unrelated to the current file"),
                inserted_region_span=None,
            ),
        )
    )
    _write_state(clean_repo, state)
    _commit_all(clean_repo)

    report = run_check(clean_repo, manifest)

    assert not any(f.type is FindingType.MANAGED_FILE_MODIFIED for f in report.findings)


# --- DRIFT-only findings, with/without --strict --------------------------


def _drift_only_setup(repo: Path) -> Manifest:
    (repo / "HYBRID.md").write_text("intro\nno region markers here\n", encoding="utf-8")
    _commit_all(repo)
    manifest = _manifest(_hybrid("hybrid", "HYBRID.md", "tiers"))
    _write_state(repo, _state())
    _commit_all(repo)
    return manifest


def test_drift_only_findings_do_not_fail_without_strict(clean_repo):
    manifest = _drift_only_setup(clean_repo)

    report = run_check(clean_repo, manifest, strict=False)

    assert [f.type for f in report.by_severity(Severity.DRIFT)] == [FindingType.MANAGED_REGION_MISSING]
    assert report.by_severity(Severity.HARD) == ()
    assert report.failing is False


def test_drift_only_findings_fail_under_strict(clean_repo):
    manifest = _drift_only_setup(clean_repo)

    report = run_check(clean_repo, manifest, strict=True)

    assert report.by_severity(Severity.HARD) == ()
    assert report.by_severity(Severity.DRIFT)
    assert report.failing is True


# --- corrupt state file ---------------------------------------------------


def test_corrupt_state_file_emits_one_state_invalid_finding_and_continues(clean_repo):
    marshal_dir = clean_repo / ".marshal"
    marshal_dir.mkdir()
    (marshal_dir / "seed-state.yml").write_text("not: [valid, yaml\n", encoding="utf-8")
    _commit_all(clean_repo)

    manifest = _manifest(_whole_file("whole", "WHOLE.md"))

    report = run_check(clean_repo, manifest)

    invalid = [f for f in report.findings if f.type is FindingType.STATE_INVALID]
    assert len(invalid) == 1
    assert invalid[0].severity is Severity.HARD
    # The rest of the run still proceeds against an absent-state view: the
    # manifest's one materializable entry is absent, and a never-recorded
    # model_version is model-behind.
    assert {f.type for f in report.findings} == {
        FindingType.STATE_INVALID,
        FindingType.ARTIFACT_MISSING,
        FindingType.MODEL_BEHIND,
    }
    assert report.state_model_version is None
    assert report.failing is True


def test_corrupt_state_file_with_a_present_hybrid_entry_degrades_cleanly(clean_repo):
    """Review finding: the corrupt-state degrade path
    (``state = None`` after a caught ``StateInvalid``) was previously only
    exercised against a whole-file entry. A hybrid entry's ``classify_regions``/
    ``region_findings`` call already accepts ``state=None`` by design (module
    docstring), and with no ``.marshal/seed-state.yml`` to have recorded a
    claim, ``managed_by_id`` is empty -- so a PRESENT, un-opted-out region
    produces no region finding at all and no hash check runs (nothing
    recorded to compare against), exactly the "silence, not a finding" rule
    for a present entry with no record."""
    marshal_dir = clean_repo / ".marshal"
    marshal_dir.mkdir()
    (marshal_dir / "seed-state.yml").write_text("not: [valid, yaml\n", encoding="utf-8")
    (clean_repo / "HYBRID.md").write_text(_hybrid_text("tiers", "line1\n"), encoding="utf-8")
    _commit_all(clean_repo)

    manifest = _manifest(_hybrid("hybrid", "HYBRID.md", "tiers"))

    report = run_check(clean_repo, manifest)

    assert {f.type for f in report.findings} == {FindingType.STATE_INVALID, FindingType.MODEL_BEHIND}
    invalid = [f for f in report.findings if f.type is FindingType.STATE_INVALID]
    assert invalid[0].severity is Severity.HARD
    assert report.state_model_version is None


# --- --json ---------------------------------------------------------------


def test_json_report_has_a_stable_field_order(clean_repo):
    manifest = _manifest(_whole_file("whole", "WHOLE.md"))

    report = run_check(clean_repo, manifest)
    payload = report.to_json_dict()
    rendered = json.dumps(payload)  # must not raise
    parsed = json.loads(rendered)

    # Story 28.3 adds "kit" between "model_version" and "failing" -- the
    # three token-economy checks, empty here because this call supplied no
    # `context_layers` at all.
    assert list(parsed.keys()) == ["strict", "findings", "model_version", "kit", "failing"]
    assert parsed["kit"] == []
    assert len(parsed["findings"]) >= 1
    for finding in parsed["findings"]:
        assert list(finding.keys()) == ["severity", "type", "path", "message", "remedy"]
    assert set(parsed["model_version"].keys()) == {"manifest", "state", "status"}
    assert parsed["failing"] is True


# --- repo behind model version ---------------------------------------------


def test_repo_behind_model_version_names_both_versions(clean_repo):
    manifest = _manifest(model_version=ModelVersion.parse("1.1.0"))
    _write_state(clean_repo, _state(model_version=ModelVersion.parse("1.0.0")))
    _commit_all(clean_repo)

    report = run_check(clean_repo, manifest, strict=False)

    behind = [f for f in report.findings if f.type is FindingType.MODEL_BEHIND]
    assert len(behind) == 1
    assert behind[0].severity is Severity.DRIFT
    assert "1.0.0" in behind[0].message
    assert "1.1.0" in behind[0].message
    assert report.model_version_status is ModelVersionStatus.BEHIND
    # MODEL_BEHIND is the sole DRIFT source here (no other findings): its
    # effect on the exit code is gated purely by --strict.
    assert report.failing is False

    strict_report = run_check(clean_repo, manifest, strict=True)
    assert strict_report.failing is True


def test_repo_current_or_ahead_of_model_version_reports_no_model_behind_finding(clean_repo):
    manifest = _manifest(model_version=ModelVersion.parse("1.0.0"))
    _write_state(clean_repo, _state(model_version=ModelVersion.parse("1.1.0")))
    _commit_all(clean_repo)

    report = run_check(clean_repo, manifest)

    assert not any(f.type is FindingType.MODEL_BEHIND for f in report.findings)
    assert report.model_version_status is ModelVersionStatus.AHEAD


# --- PRESENT_LEGACY short-circuit ------------------------------------------


def test_present_legacy_entry_reports_only_the_legacy_finding(clean_repo):
    """AD-59: a recognized legacy artifact is never inspected again -- the
    recorded ``body_sha`` below is deliberately WRONG, to prove it is never
    consulted (no ``managed-file-modified`` finding for it)."""
    (clean_repo / "OLD.md").write_text("still here, never checked\n", encoding="utf-8")
    _commit_all(clean_repo)

    manifest = _manifest(
        _whole_file("old", "OLD.md", legacy_of="new"),
        _whole_file("new", "NEW.md"),
    )
    state = _state(
        managed=(
            ManagedArtifact(
                id="old",
                path="OLD.md",
                artifact_class="copied-managed",
                body_sha="deadbeef",
                inserted_region_span=None,
            ),
        )
    )
    _write_state(clean_repo, state)
    _commit_all(clean_repo)

    report = run_check(clean_repo, manifest)

    old_findings = [f for f in report.findings if f.path == "OLD.md"]
    assert [f.type for f in old_findings] == [FindingType.LEGACY_PRESENT]
    assert old_findings[0].severity is Severity.INFO
    new_findings = [f for f in report.findings if f.path == "NEW.md"]
    assert [f.type for f in new_findings] == [FindingType.ARTIFACT_MISSING]


# --- the build_plan-derived ARTIFACT_MISSING gate --------------------------


def test_a_fully_opted_out_absent_hybrid_entry_is_not_reported_missing(clean_repo):
    """The correctness gap ``build_plan`` composition closes (see
    ``verbs/check.py``'s own module docstring): the whole file is gone, but
    every one of its declared regions is permanently opted out, so
    ``build_plan`` produces no ``Action`` for it and `check` must not report
    a HARD, exit-blocking ``ARTIFACT_MISSING`` for something `seed update`
    would materialize nothing for."""
    manifest = _manifest(_hybrid("hybrid", "HYBRID.md", "tiers"))
    _write_state(clean_repo, _state(opted_out=(opt_out_key("hybrid", "tiers"),)))
    _commit_all(clean_repo)

    report = run_check(clean_repo, manifest)

    assert not any(f.type is FindingType.ARTIFACT_MISSING for f in report.findings)


def test_an_absent_whole_file_entry_is_always_reported_regardless_of_opt_outs(clean_repo):
    """Opt-out is a region-scoped mechanism (FR-112) -- a whole-file class
    entry has no ``_pendency`` at all, so `build_plan` never suppresses its
    Action and this gate is a no-op for it."""
    manifest = _manifest(_whole_file("whole", "WHOLE.md"))
    _write_state(clean_repo, _state())
    _commit_all(clean_repo)

    report = run_check(clean_repo, manifest)

    assert any(f.type is FindingType.ARTIFACT_MISSING for f in report.findings)


# --- Story 10.7: the applies_to-vs-state.mode ARTIFACT_MISSING fix ---------


def test_an_adopt_only_entry_is_not_reported_missing_on_an_init_mode_repo(clean_repo):
    """The exact confirmed defect Story 10.7's own spec names, via
    `specs-dir-legacy`'s own real shape: an `applies_to: adopt` entry, absent
    from a freshly `init`'d repo (`state.mode == "init"`), must NOT be
    reported `ARTIFACT_MISSING` -- "a fresh init never creates it" is not a
    conformance problem, it is the manifest's own documented rationale for
    why the entry is `adopt`-only in the first place. Without the fix, this
    entry's `ABSENT` classification (nothing was ever written for it) still
    lands in `plan.actions` (`build_plan` has no `applies_to` awareness of
    its own), so the pre-fix gate (`entry_id in actioned_ids` alone) would
    have flagged it."""
    adopt_only_entry = ManifestEntry(
        id="specs-dir-legacy",
        artifact_class=ArtifactClass.GENERATED_DERIVED,
        path="docs/specs/",
        applies_to=AppliesTo.ADOPT,
        rationale="legacy Tier-1 skeleton; a fresh init never creates it",
    )
    manifest = _manifest(adopt_only_entry)
    _write_state(clean_repo, _state(mode="init"))
    _commit_all(clean_repo)

    report = run_check(clean_repo, manifest)

    assert not any(f.type is FindingType.ARTIFACT_MISSING for f in report.findings)
    assert report.findings == ()


def test_an_init_only_entry_is_not_reported_missing_on_an_adopt_mode_repo(clean_repo):
    """The symmetric direction: `starter-dream`/`specs-readme`-shaped
    `applies_to: init` entries must not be reported `ARTIFACT_MISSING` on a
    repo that was `adopt`ed (never `init`ed) -- `state.mode == "adopt"`."""
    init_only_entry = ManifestEntry(
        id="starter-dream",
        artifact_class=ArtifactClass.COPIED_SEEDED,
        path="docs/dreams/example.md",
        applies_to=AppliesTo.INIT,
        rationale="it is the repo's content from the moment it is written",
    )
    manifest = _manifest(init_only_entry)
    _write_state(clean_repo, _state(mode="adopt"))
    _commit_all(clean_repo)

    report = run_check(clean_repo, manifest)

    assert not any(f.type is FindingType.ARTIFACT_MISSING for f in report.findings)
    assert report.findings == ()


def test_applies_to_both_entries_are_always_reported_missing_regardless_of_mode(clean_repo):
    """The fix's own carve-out: an `applies_to: both` entry participates in
    every mode, so it is never exempted by this gate -- confirmed for both
    `state.mode` values."""
    manifest = _manifest(_whole_file("whole", "WHOLE.md"))

    _write_state(clean_repo, _state(mode="init"))
    _commit_all(clean_repo)
    init_report = run_check(clean_repo, manifest)
    assert any(f.type is FindingType.ARTIFACT_MISSING for f in init_report.findings)

    _write_state(clean_repo, _state(mode="adopt"))
    _commit_all(clean_repo)
    adopt_report = run_check(clean_repo, manifest)
    assert any(f.type is FindingType.ARTIFACT_MISSING for f in adopt_report.findings)


# --- write-blocking fixture -------------------------------------------------


def test_check_module_never_references_a_write_capable_primitive():
    """A static guard alongside the runtime one below: this module must not
    IMPORT ``seed.fs`` at all, and must not CALL ``write_plan``, matching
    ``tests/meta/test_p07_no_hash_comparison_in_apply.py``'s "ban it at the
    source" style for the identical class of concern (FR-88). Walks the AST
    rather than substring-matching the raw source (found in review): this
    module's own docstring names ``write_plan``/``fs.write`` in PROSE
    explaining why they are never called, and a bare substring scan matches
    that prose too."""
    tree = ast.parse(inspect.getsource(check_module))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert node.module != "fs" and not (node.module or "").endswith(".fs")
            assert all(alias.name != "fs" for alias in node.names)
        if isinstance(node, ast.Import):
            assert all(not alias.name.endswith("fs") for alias in node.names)
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                assert func.id != "write_plan"
            if isinstance(func, ast.Attribute):
                assert not (isinstance(func.value, ast.Name) and func.value.id == "fs")


def test_run_check_never_writes(clean_repo, monkeypatch):
    def _boom(*args, **kwargs):
        raise AssertionError("run_check must never call a write primitive")

    monkeypatch.setattr(fs, "write", _boom)
    monkeypatch.setattr(fs, "replace_span", _boom)
    monkeypatch.setattr(fs, "remove", _boom)

    (clean_repo / "WHOLE.md").write_text("hello\n", encoding="utf-8")
    (clean_repo / "HYBRID.md").write_text(_hybrid_text("tiers", "body\n"), encoding="utf-8")
    _commit_all(clean_repo)
    before = sorted(path.relative_to(clean_repo).as_posix() for path in clean_repo.rglob("*") if path.is_file())

    manifest = _manifest(
        _whole_file("whole", "WHOLE.md"),
        _hybrid("hybrid", "HYBRID.md", "tiers"),
    )

    report = run_check(clean_repo, manifest, strict=True)

    assert report.findings  # the guard above was actually exercised
    assert not (clean_repo / ".marshal").exists()
    after = sorted(path.relative_to(clean_repo).as_posix() for path in clean_repo.rglob("*") if path.is_file())
    assert after == before
    assert _git(clean_repo, "status", "--porcelain").stdout == ""


# --- NFR-P1: < 5s on a local-recipes-sized repo -----------------------------


@pytest.fixture(scope="module")
def real_manifest() -> Manifest:
    manifest_ref = resources.files("pyforge.marshal.seed.templates") / "manifest.yaml"
    with resources.as_file(manifest_ref) as manifest_path:
        return load_manifest(manifest_path)


_PERF_FIXTURE_GITIGNORE = """\
__pycache__/
*.pyc
.pytest_cache/
.ruff_cache/
.mypy_cache/
*.egg-info/
build/
dist/
.venv/
node_modules/
.DS_Store
*.log
.env
.marshal/
_bmad-output/projects/*/implementation-artifacts/
"""


def test_run_check_completes_within_the_nfr_p1_budget(real_manifest, tmp_path):
    """Follows ``pyforge-warden``'s ``time.perf_counter()`` pattern
    (this story's own Code Map precedent): a representative tree stands in
    for a `local-recipes`-sized repo's walk cost, against the REAL
    40+-entry packaged manifest rather than a synthetic one.

    Strengthened (review finding): the original fixture was 400 flat files
    across 20 sibling directories with no ``.gitignore`` at all -- measurably
    cheaper to walk/classify than the real target repo (thousands of files,
    deep nesting, a root ``.gitignore`` with dozens of patterns each
    requiring a per-path match in ``detect.inventory``'s walker). This
    fixture nests three directory levels deep (``dirI/subJ/leafK/``, ~1200
    files total) and ships a representative multi-pattern ``.gitignore`` so
    the walker actually exercises its ignore-matching cost, not just a flat
    directory scan."""
    _init_git_repo(tmp_path)
    (tmp_path / ".gitignore").write_text(_PERF_FIXTURE_GITIGNORE, encoding="utf-8")
    for i in range(12):
        for j in range(10):
            leaf = tmp_path / f"dir{i}" / f"sub{j}" / "leaf"
            leaf.mkdir(parents=True, exist_ok=True)
            for k in range(10):
                (leaf / f"file{k}.txt").write_text("x\n", encoding="utf-8")
    _commit_all(tmp_path)

    started = time.perf_counter()
    run_check(tmp_path, real_manifest)
    elapsed = time.perf_counter() - started

    assert elapsed < 5.0, f"run_check took {elapsed:.2f}s, over the NFR-P1 5s budget"


# --- CheckReport.to_json_dict as a plain query --------------------------


def test_by_severity_partitions_findings_correctly(clean_repo):
    manifest = _manifest(_whole_file("whole", "WHOLE.md"))

    report = run_check(clean_repo, manifest)

    assert report.by_severity(Severity.HARD) == tuple(f for f in report.findings if f.severity is Severity.HARD)
    assert report.by_severity(Severity.INFO) == ()


def test_check_report_is_a_plain_frozen_dataclass():
    """``CheckReport`` is a value object, not a mutable accumulator -- a
    caller must never be able to hand-edit a report after the fact."""
    report = CheckReport(
        findings=(),
        strict=False,
        manifest_model_version="1.0.0",
        state_model_version=None,
        model_version_status=ModelVersionStatus.CURRENT,
    )
    with pytest.raises(AttributeError):
        report.findings = (object(),)  # type: ignore[misc]
