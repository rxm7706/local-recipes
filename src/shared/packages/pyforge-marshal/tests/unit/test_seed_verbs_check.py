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
    ManifestError,
    Region,
    RequiredIn,
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


def test_an_escaping_entry_is_one_hard_finding_and_is_never_read(clean_repo, monkeypatch):
    """Story 82.11 (DW-10-3-9): an entry whose path resolves outside the repo
    (an in-repo symlink pointing out) is no longer ``absent`` -- ``check``
    reports it as HARD ``target-escapes-repo`` naming the entry and where it
    resolves, and never reads the escaped location."""
    outside = clean_repo.parent / f"{clean_repo.name}-outside"
    outside.mkdir()
    secret = outside / "secret.md"
    secret.write_text("outside the repo\n", encoding="utf-8")
    (clean_repo / "ESCAPER.md").symlink_to(secret)
    manifest = _manifest(_whole_file("bad", "ESCAPER.md"), _whole_file("good", "GOOD.md"))
    read_paths: list[Path] = []
    real_read = check_module._read_text_or_blank

    def spy(target: Path) -> str:
        read_paths.append(target)
        return real_read(target)

    monkeypatch.setattr(check_module, "_read_text_or_blank", spy)

    report = run_check(clean_repo, manifest)

    escapes = [finding for finding in report.findings if finding.type is FindingType.TARGET_ESCAPES_REPO]
    assert [(finding.severity, finding.path) for finding in escapes] == [(Severity.HARD, "ESCAPER.md")]
    assert "bad:" in escapes[0].message
    assert str(secret.resolve()) in escapes[0].message
    # Not ALSO "missing": the entry is not absent, it is not ours to read.
    missing = {f.path for f in report.findings if f.type is FindingType.ARTIFACT_MISSING}
    assert missing == {"GOOD.md"}
    assert clean_repo / "ESCAPER.md" not in read_paths
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
                inserted_region_spans=(),
            ),
            ManagedArtifact(
                id="hybrid",
                path="HYBRID.md",
                artifact_class="hybrid-managed-region",
                body_sha=hash_content(region_body),
                inserted_region_spans=(
                    RegionSpanRecord(name="tiers", start=0, end=len(region_body), body_sha=hash_content(region_body)),
                ),
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
                inserted_region_spans=(),
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
                inserted_region_spans=(
                    RegionSpanRecord(name="tiers", start=0, end=1, body_sha=hash_content("original\n")),
                ),
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
    ``record.inserted_region_spans``, never by the manifest entry's CURRENT
    ``artifact_class`` alone -- an entry's class can be reclassified across
    model versions while ``state.managed[]``'s record still describes what
    was actually recorded (module docstring). Here the manifest currently
    declares ``whole`` as a whole-file (``copied-managed``) entry, but its
    recorded claim is stale from when it was ``hybrid-managed-region``. The
    pre-fix code would have entered the ``elif`` whole-file branch (gated
    on the CURRENT class) and hashed the whole file against a body_sha that
    was recorded for a REGION, producing a near-guaranteed spurious
    ``managed-file-modified`` HARD finding. The fixed code selects on
    ``record.inserted_region_spans`` first, finds ``entry.format is None``
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
                inserted_region_spans=(
                    RegionSpanRecord(
                        name="tiers",
                        start=0,
                        end=5,
                        body_sha=hash_content("a stale region body, unrelated to the whole file"),
                    ),
                ),
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
                inserted_region_spans=(),
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
                inserted_region_spans=(),
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


# --- Story 70.1: the paths the manifest means, never its placeholders -------

#: The five packaged `{{ slug }}` entries (`templates/manifest.yaml`), with
#: their packaged ids, classes and paths -- built here rather than read from
#: the packaged manifest so each scenario's shape is legible from the fixture.
_TEMPLATED = (
    ("starter-dream", ArtifactClass.COPIED_SEEDED, "docs/dreams/{{ slug }}.md"),
    ("project-config", ArtifactClass.COPIED_SEEDED, "_bmad-output/projects/{{ slug }}/.bmad-config.toml"),
    (
        "specs-readme",
        ArtifactClass.COPIED_SEEDED,
        "_bmad-output/projects/{{ slug }}/planning-artifacts/specs/README.md",
    ),
    ("deck-scaffolding", ArtifactClass.COPIED_SEEDED, "presentations/{{ slug }}/"),
    ("project-subtree", ArtifactClass.GENERATED_DERIVED, "_bmad-output/projects/{{ slug }}/"),
)


def _templated_entries() -> tuple[ManifestEntry, ...]:
    return tuple(
        ManifestEntry(id=entry_id, artifact_class=cls, path=path, applies_to=AppliesTo.BOTH, rationale="test")
        for entry_id, cls, path in _TEMPLATED
    )


def _lay_out_demo_project(repo: Path, *, without: str | None = None) -> None:
    """Every rendered path of the five templated entries for the slug
    `demo`, except `without`."""
    for _entry_id, _cls, path in _TEMPLATED:
        rendered = path.replace("{{ slug }}", "demo")
        if rendered == without:
            continue
        target = repo / rendered
        if rendered.endswith("/"):
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f"{rendered}\n", encoding="utf-8")


def test_a_slug_judges_every_templated_entry_at_the_path_it_renders_to(clean_repo):
    """AC: with the slug `demo` and every rendered path present, no finding's
    path carries `{{` and none of the five templated entries is
    `artifact-missing`. Removing the rendering from `run_check` reports
    `docs/dreams/{{ slug }}.md` missing here (mutation)."""
    _lay_out_demo_project(clean_repo)

    report = run_check(clean_repo, _manifest(*_templated_entries()), slug="demo")

    assert not [finding.path for finding in report.findings if "{{" in finding.path]
    assert not [finding for finding in report.findings if finding.type is FindingType.ARTIFACT_MISSING]
    assert not [finding for finding in report.findings if finding.type is FindingType.SLUG_UNRESOLVED]
    assert report.failing is False


def test_an_absent_rendered_path_is_hard_missing_at_that_path(clean_repo):
    """AC: the same fixture without `docs/dreams/demo.md` -- a truly absent
    rendered path stays HARD, named at the rendered path."""
    _lay_out_demo_project(clean_repo, without="docs/dreams/demo.md")

    report = run_check(clean_repo, _manifest(*_templated_entries()), slug="demo")

    missing = [finding for finding in report.findings if finding.type is FindingType.ARTIFACT_MISSING]
    assert [(finding.severity, finding.path) for finding in missing] == [(Severity.HARD, "docs/dreams/demo.md")]
    assert report.failing is True


@pytest.mark.parametrize("slug", [None, ""])
def test_no_slug_leaves_each_templated_entry_unjudged_with_one_info_finding(clean_repo, monkeypatch, slug):
    """AC: with no slug (`None`, or the empty string the CLI passes when
    nothing resolves) each templated entry yields one INFO `slug-unresolved`
    finding naming it, whose remedy names `--project`; none is classified or
    planned at a literal placeholder path; `failing` is untouched by them."""
    classified_paths: list[str] = []
    real_classify = check_module.classify

    def spy(manifest, repo_root):
        classified_paths.extend(entry.path for entry in manifest.entries)
        return real_classify(manifest, repo_root)

    monkeypatch.setattr(check_module, "classify", spy)
    manifest = _manifest(*_templated_entries(), _whole_file("whole", "WHOLE.md"))
    (clean_repo / "WHOLE.md").write_text("hello\n", encoding="utf-8")

    report = run_check(clean_repo, manifest, slug=slug)

    unresolved = [finding for finding in report.findings if finding.type is FindingType.SLUG_UNRESOLVED]
    assert [(finding.severity, finding.path) for finding in unresolved] == [
        (Severity.INFO, path) for _entry_id, _cls, path in _TEMPLATED
    ]
    for finding, (entry_id, _cls, _path) in zip(unresolved, _TEMPLATED, strict=True):
        assert repr(entry_id) in finding.message
        assert "--project" in finding.remedy
    assert classified_paths == ["WHOLE.md"]
    assert not [finding for finding in report.findings if finding.type is FindingType.ARTIFACT_MISSING]
    assert report.failing is False


def test_a_slug_that_renders_two_owners_of_one_path_raises_manifest_error(clean_repo):
    """Story 86.1's note: the one-owner rule is re-run on the rendered
    manifest `check` judges, so two entries rendering to one path refuse --
    `cli/seed.py` reports it as a usage error naming the slug."""
    manifest = _manifest(
        _whole_file("literal-doc", "docs/demo.md"),
        ManifestEntry(
            id="templated-doc",
            artifact_class=ArtifactClass.COPIED_SEEDED,
            path="docs/{{ slug }}.md",
            applies_to=AppliesTo.BOTH,
            rationale="test",
        ),
    )

    with pytest.raises(ManifestError, match=r"^templated-doc: path 'docs/demo.md' is also declared by 'literal-doc'"):
        run_check(clean_repo, manifest, slug="demo")


@pytest.mark.parametrize("mode", [None, "adopt", "init"])
def test_an_unclassified_deferred_glob_with_no_literal_match_is_never_missing(clean_repo, mode):
    """AC: `.claude/skills/**` names no literal file, so it classifies
    `ABSENT` and `build_plan` plans it -- but the class has no contract, so it
    is never `artifact-missing`, adopted or not."""
    if mode is not None:
        _write_state(clean_repo, _state(mode=mode))
    manifest = _manifest(
        ManifestEntry(
            id="claude-skills",
            artifact_class=ArtifactClass.UNCLASSIFIED_DEFERRED,
            path=".claude/skills/**",
            applies_to=AppliesTo.BOTH,
            rationale="test",
        ),
        _whole_file("whole", "WHOLE.md"),
    )

    report = run_check(clean_repo, manifest)

    missing = {finding.path for finding in report.findings if finding.type is FindingType.ARTIFACT_MISSING}
    assert missing == {"WHOLE.md"}


def _loop_policy_entry() -> ManifestEntry:
    return ManifestEntry(
        id="bmad-loop-policy",
        artifact_class=ArtifactClass.GENERATED_DERIVED,
        path=".bmad-loop/policy.toml",
        applies_to=AppliesTo.BOTH,
        rationale="test",
        required_in=RequiredIn.LOOP_HOME,
    )


def test_a_loop_home_only_entry_is_not_owed_by_a_target_known_not_to_be_a_loop_home(clean_repo):
    """AC (amended 2026-09-28): `in_loop_home=False` -- an absent
    `required_in: loop-home` entry yields no finding. Removing the scope gate
    reports `.bmad-loop/policy.toml` missing here (mutation)."""
    report = run_check(clean_repo, _manifest(_loop_policy_entry()), in_loop_home=False)

    assert not [finding for finding in report.findings if finding.path == ".bmad-loop/policy.toml"]
    assert report.failing is False


@pytest.mark.parametrize("in_loop_home", [True, None, "omitted"])
def test_a_loop_home_or_an_unreadable_target_still_owes_a_loop_home_only_entry(clean_repo, in_loop_home):
    """AC: in a loop home (`True`), or where the branch could not be read
    (`None`, also the default), the absent entry is HARD `artifact-missing`
    as before -- an unreadable target never passes on the scope."""
    kwargs = {} if in_loop_home == "omitted" else {"in_loop_home": in_loop_home}

    report = run_check(clean_repo, _manifest(_loop_policy_entry()), **kwargs)

    missing = [finding for finding in report.findings if finding.type is FindingType.ARTIFACT_MISSING]
    assert [(finding.severity, finding.path) for finding in missing] == [(Severity.HARD, ".bmad-loop/policy.toml")]
    assert report.failing is True


def test_the_loop_home_scope_never_hides_an_unscoped_entry(clean_repo):
    """The scope is the entry's, never a test of the target: off a loop home
    an entry with no `required_in` is still owed."""
    report = run_check(clean_repo, _manifest(_whole_file("whole", "WHOLE.md")), in_loop_home=False)

    assert [finding.path for finding in report.findings if finding.type is FindingType.ARTIFACT_MISSING] == ["WHOLE.md"]


# --- Story 70.2: recorded skips in check ------------------------------------


def test_a_recorded_skip_suppresses_artifact_missing_for_an_absent_entry(clean_repo):
    """Story 70.2: ``state.skips`` matching an absent entry yields INFO
    ``artifact-skipped``, not HARD ``artifact-missing``, and ``failing`` stays false."""
    manifest = _manifest(_whole_file("whole", "WHOLE.md"), _whole_file("other", "OTHER.md"))
    _write_state(
        clean_repo,
        _state(
            skips=("OTHER.md",),
            managed=(
                ManagedArtifact(
                    id="whole",
                    path="WHOLE.md",
                    artifact_class="copied-managed",
                    body_sha=hash_content("ok\n"),
                    inserted_region_spans=(),
                ),
            ),
        ),
    )
    (clean_repo / "WHOLE.md").write_text("ok\n", encoding="utf-8")

    report = run_check(clean_repo, manifest)

    skipped = [f for f in report.findings if f.type is FindingType.ARTIFACT_SKIPPED]
    assert len(skipped) == 1
    assert skipped[0].path == "OTHER.md"
    assert skipped[0].severity is Severity.INFO
    assert not [f for f in report.findings if f.type is FindingType.ARTIFACT_MISSING and f.path == "OTHER.md"]
    assert report.failing is False


def test_removing_the_recorded_skip_restores_artifact_missing(clean_repo):
    """Mutation guard: without ``state.skips`` the same absent entry is HARD missing."""
    manifest = _manifest(_whole_file("other", "OTHER.md"))
    _write_state(clean_repo, _state(skips=("OTHER.md",)))
    report_with = run_check(clean_repo, manifest)
    assert [f.type for f in report_with.findings if f.path == "OTHER.md"] == [FindingType.ARTIFACT_SKIPPED]

    _write_state(clean_repo, _state(skips=()))
    report_without = run_check(clean_repo, manifest)
    assert [
        (f.severity, f.type) for f in report_without.findings if f.path == "OTHER.md"
    ] == [(Severity.HARD, FindingType.ARTIFACT_MISSING)]


def test_refused_ambient_slug_yields_slug_unresolved_naming_source(clean_repo):
    """Story 70.2 L2: a slug from the environment that refuses to render is
    INFO ``slug-unresolved`` naming the slug and its source -- not exit 2."""
    manifest = _manifest(
        ManifestEntry(
            id="templated-doc",
            artifact_class=ArtifactClass.COPIED_SEEDED,
            path="docs/{{ slug }}.md",
            applies_to=AppliesTo.BOTH,
            rationale="test",
        )
    )
    report = run_check(
        clean_repo,
        manifest,
        slug=None,
        refused_slug="../escape",
        refused_slug_source="BMAD_ACTIVE_PROJECT",
    )
    unresolved = [f for f in report.findings if f.type is FindingType.SLUG_UNRESOLVED]
    assert len(unresolved) == 1
    assert "../escape" in unresolved[0].message
    assert "BMAD_ACTIVE_PROJECT" in unresolved[0].message
    assert report.failing is False
