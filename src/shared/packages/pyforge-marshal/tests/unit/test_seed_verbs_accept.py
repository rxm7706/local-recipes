"""Unit tests for ``pyforge.marshal.seed.verbs.accept`` (Story 97.1) -- AC1-AC7.

``marshal seed accept <id>[#<region>]`` is the sanctioned re-record of an
intended edit to a tool-owned file or region. Every fixture here seeds its state
through a REAL ``run_adopt(..., apply=True)`` (never a hand-built
``SeedState``), so the recorded ``body_sha`` and region spans are exactly what a
real adopt writes, and the hash ``accept`` re-records is the one rung 6 and
``seed check`` compare with. ``git`` is real (a ``tmp_path`` repo with a
committer identity), never mocked.

Covers: the dry run (writes nothing, not even ``plan.json``); ``--apply``
(one ``write_state`` call, a journal entry per file/region, ``seed-state.yml``
the only changed path, and the next ``adopt`` no longer refusing); the whole
I/O matrix of refusals; a hybrid file's per-region accept (and ``body_sha``
following the first span); and the guard following the manifest's CURRENT
class (AC7) -- a record written while an entry was ``copied-managed`` no longer
refuses once the manifest says ``copied-seeded``, while ``copied-managed`` and
``hybrid-managed-region`` stay guarded.
"""

from __future__ import annotations

import dataclasses
import subprocess
from pathlib import Path

import pytest

from pyforge.marshal.seed.detect.hashes import hash_content
from pyforge.marshal.seed.errors import PreconditionFailure, StateInvalid, UsageError
from pyforge.marshal.seed.fs import NeverWrite
from pyforge.marshal.seed.model.manifest import (
    AppliesTo,
    ArtifactClass,
    Manifest,
    ManifestEntry,
    Region,
)
from pyforge.marshal.seed.model.version import ModelVersion
from pyforge.marshal.seed.plan.types import Action
from pyforge.marshal.seed.regions.apply import insert_region
from pyforge.marshal.seed.regions.markers import RegionFormat
from pyforge.marshal.seed.state import read_state, write_state
from pyforge.marshal.seed.verbs import accept as accept_module
from pyforge.marshal.seed.verbs.accept import render_accept_text, run_accept
from pyforge.marshal.seed.verbs.adopt import run_adopt
from pyforge.marshal.seed.verbs.check import run_check
from pyforge.marshal.seed.verbs.update import run_update

_VERSION = ModelVersion.parse("1.0.0")
_NO_NEVER_WRITE = NeverWrite(patterns=())

SWITCH = "scripts/bmad-switch"
REGISTRY = "scripts/detectors.py"
HYBRID = "HYBRID.md"
STATE_PATH = ".marshal/seed-state.yml"


# --- builders ---------------------------------------------------------------


def _entry(entry_id: str, artifact_class: ArtifactClass, path: str, **extra) -> ManifestEntry:
    return ManifestEntry(
        id=entry_id,
        artifact_class=artifact_class,
        path=path,
        applies_to=AppliesTo.BOTH,
        rationale="test",
        **extra,
    )


def _hybrid(entry_id: str, path: str, *region_names: str) -> ManifestEntry:
    return _entry(
        entry_id,
        ArtifactClass.HYBRID_MANAGED_REGION,
        path,
        format=RegionFormat.HTML,
        regions=tuple(Region(name=name, anchor=("# anchor",)) for name in region_names),
    )


def _entries(*, registry_class: ArtifactClass) -> tuple[ManifestEntry, ...]:
    return (
        _entry("bmad-switch", ArtifactClass.COPIED_MANAGED, SWITCH),
        _entry("detector-registry", registry_class, REGISTRY),
        _hybrid("hybrid", HYBRID, "alpha", "beta"),
        _entry("derived", ArtifactClass.GENERATED_DERIVED, "DERIVED.md"),
        _entry("dreams-dir", ArtifactClass.GENERATED_DERIVED, "docs/dreams/"),
        _entry("bmad-method", ArtifactClass.REFERENCED, "n/a", pin="1.0.0"),
        _entry("deferred", ArtifactClass.UNCLASSIFIED_DEFERRED, "DEFERRED.md"),
        _entry("custom-config", ArtifactClass.COPIED_SEEDED, "CONFIG.toml"),
    )


def _manifest(*, registry_class: ArtifactClass = ArtifactClass.COPIED_SEEDED) -> Manifest:
    return Manifest(model_version=_VERSION, never_write=(), entries=_entries(registry_class=registry_class))


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    return result.stdout


def _commit_all(repo: Path) -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "fixture")


def _fake_commit(manifest: Manifest, repo_root: Path):
    """Materialize each claimed artifact: plain text for a whole file, the REAL
    ``insert_region`` primitive for a hybrid one (the adopt-test convention)."""
    entries_by_id = {entry.id: entry for entry in manifest.entries}

    def commit(action: Action) -> None:
        entry = entries_by_id[action.artifact_id]
        target = repo_root / action.target_path
        if entry.artifact_class is ArtifactClass.HYBRID_MANAGED_REGION:
            assert entry.format is not None
            for region_name, _anchor in action.chosen_anchor:
                region = next(r for r in entry.regions if r.name == region_name)
                text = target.read_text(encoding="utf-8") if target.is_file() else None
                insert_region(
                    text,
                    target,
                    region_name,
                    region.anchor,
                    f"body for {region_name}\n",
                    model_version=manifest.model_version,
                    fmt=entry.format,
                    repo_root=repo_root,
                    never_write=_NO_NEVER_WRITE,
                )
        elif entry.is_directory:
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f"materialized {action.artifact_id}\n", encoding="utf-8")

    return commit


def _unreachable_confirm() -> bool:
    raise AssertionError("confirm() should not have been called")


def _unreachable_commit(action: Action) -> None:
    raise AssertionError(f"commit() should not have been called for {action.artifact_id!r}")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A committed git repo with a committer identity and ``plan.json`` ignored
    (adopt writes it on every run; an ignored plan keeps the worktree clean)."""
    _git(tmp_path, "init", "-b", "main")
    _git(tmp_path, "config", "user.email", "tester@example.com")
    _git(tmp_path, "config", "user.name", "Test Er")
    (tmp_path / ".gitignore").write_text(".marshal/plan.json\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("hello\n", encoding="utf-8")
    _commit_all(tmp_path)
    return tmp_path


@pytest.fixture
def adopted(repo: Path) -> Path:
    """``repo`` adopted while ``detector-registry`` was still ``copied-managed``
    (the pre-97.1 state every adopting repo already carries), then committed."""
    legacy = _manifest(registry_class=ArtifactClass.COPIED_MANAGED)
    run_adopt(
        repo,
        legacy,
        apply=True,
        yes=True,
        confirm=_unreachable_confirm,
        commit=_fake_commit(legacy, repo),
    )
    _commit_all(repo)
    return repo


def _edit(repo: Path, relative: str, text: str) -> None:
    (repo / relative).write_text(text, encoding="utf-8")
    _commit_all(repo)


def _edit_region(repo: Path, region: str) -> str:
    """Hand-edit one managed region's body, markers intact; return its new hash."""
    target = repo / HYBRID
    text = target.read_text(encoding="utf-8")
    assert f"body for {region}\n" in text
    new_text = text.replace(f"body for {region}\n", f"intended edit of {region}\nwith two lines\n")
    target.write_text(new_text, encoding="utf-8")
    _commit_all(repo)
    return hash_content(f"intended edit of {region}\nwith two lines\n")


class _WriteSpy:
    """Counts calls to ``write_state`` as ``accept`` reaches it, delegating to the real one."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.calls: list[dict] = []
        real = accept_module.write_state

        def spy(state, *, repo_root, never_write):
            self.calls.append({"state": state, "repo_root": repo_root})
            return real(state, repo_root=repo_root, never_write=never_write)

        monkeypatch.setattr(accept_module, "write_state", spy)


def _record(repo: Path, artifact_id: str):
    state = read_state(repo)
    assert state is not None
    return next(record for record in state.managed if record.id == artifact_id)


# --- AC1: dry run -------------------------------------------------------------


def test_dry_run_reports_the_rerecord_and_writes_nothing(adopted, monkeypatch):
    spy = _WriteSpy(monkeypatch)
    _edit(adopted, SWITCH, "an intended edit\n")
    state_bytes = (adopted / STATE_PATH).read_bytes()
    recorded = _record(adopted, "bmad-switch").body_sha

    result = run_accept(adopted, _manifest(), "bmad-switch")

    assert result.applied is False
    assert [(c.artifact_id, c.region, c.path) for c in result.changes] == [("bmad-switch", None, SWITCH)]
    assert result.changes[0].previous_sha == recorded
    assert result.changes[0].accepted_sha == hash_content("an intended edit\n")
    assert result.acceptances == ()
    assert result.to_json_dict()["status"] == "dry-run"
    assert spy.calls == []
    assert (adopted / STATE_PATH).read_bytes() == state_bytes
    assert _git(adopted, "status", "--porcelain") == ""
    text = render_accept_text(result)
    assert f"{recorded} -> {hash_content('an intended edit' + chr(10))}" in text
    assert "--apply" in text


def test_dry_run_tolerates_a_dirty_worktree_but_apply_does_not(adopted):
    _edit(adopted, SWITCH, "an intended edit\n")
    (adopted / "scratch.txt").write_text("uncommitted\n", encoding="utf-8")

    assert run_accept(adopted, _manifest(), "bmad-switch").changes
    with pytest.raises(PreconditionFailure) as raised:
        run_accept(adopted, _manifest(), "bmad-switch", apply=True, reason="why")
    assert "dirty" in str(raised.value) or "clean" in str(raised.value)
    assert _record(adopted, "bmad-switch").body_sha != hash_content("an intended edit\n")


# --- AC2: apply ---------------------------------------------------------------


def test_apply_records_the_new_hash_and_one_journal_entry(adopted, monkeypatch):
    spy = _WriteSpy(monkeypatch)
    _edit(adopted, SWITCH, "an intended edit\n")
    previous = _record(adopted, "bmad-switch").body_sha
    head = _git(adopted, "rev-parse", "HEAD").strip()

    result = run_accept(adopted, _manifest(), "bmad-switch", apply=True, reason="  keep the local patch  ")

    assert result.applied is True
    assert len(spy.calls) == 1  # exactly one write_state per applying run
    assert spy.calls[0]["repo_root"] == adopted
    state = read_state(adopted)
    assert state is not None
    assert _record(adopted, "bmad-switch").body_sha == hash_content("an intended edit\n")
    assert len(state.acceptances) == 1
    entry = state.acceptances[0]
    assert (entry.id, entry.region, entry.path) == ("bmad-switch", None, SWITCH)
    assert (entry.previous_sha, entry.accepted_sha) == (previous, hash_content("an intended edit\n"))
    assert entry.accepted_by == "Test Er <tester@example.com>"
    assert entry.head == head
    assert entry.reason == "keep the local patch"
    assert result.acceptances == (entry,)
    assert result.to_json_dict()["status"] == "applied"
    # the only changed path is the state file
    assert _git(adopted, "status", "--porcelain").splitlines() == [f" M {STATE_PATH}"]


def test_the_next_adopt_no_longer_refuses_the_accepted_edit(adopted):
    _edit(adopted, SWITCH, "an intended edit\n")
    legacy = _manifest(registry_class=ArtifactClass.COPIED_MANAGED)
    with pytest.raises(PreconditionFailure, match="managed-content-modified"):
        run_adopt(adopted, legacy, apply=True, yes=True, confirm=_unreachable_confirm, commit=_unreachable_commit)

    run_accept(adopted, legacy, "bmad-switch", apply=True, reason="intended")
    _commit_all(adopted)

    run_adopt(adopted, legacy, apply=True, yes=True, confirm=_unreachable_confirm, commit=_unreachable_commit)
    assert (adopted / SWITCH).read_text(encoding="utf-8") == "an intended edit\n"


def test_acceptances_accumulate_and_survive_a_later_adopt(adopted):
    _edit(adopted, SWITCH, "first edit\n")
    run_accept(adopted, _manifest(), "bmad-switch", apply=True, reason="first")
    _commit_all(adopted)
    _edit(adopted, SWITCH, "second edit\n")
    run_accept(adopted, _manifest(), "bmad-switch", apply=True, reason="second")
    _commit_all(adopted)

    state = read_state(adopted)
    assert state is not None
    assert [entry.reason for entry in state.acceptances] == ["first", "second"]
    assert state.acceptances[1].previous_sha == state.acceptances[0].accepted_sha

    # a later adopt that changes state (a new entry is claimed) carries the journal along
    manifest = _manifest()
    manifest = dataclasses.replace(
        manifest, entries=(*manifest.entries, _entry("extra", ArtifactClass.COPIED_MANAGED, "scripts/extra"))
    )
    run_adopt(adopted, manifest, apply=True, yes=True, confirm=_unreachable_confirm, commit=_fake_commit(manifest, adopted))
    after = read_state(adopted)
    assert after is not None
    assert after.acceptances == state.acceptances
    assert {record.id for record in after.managed} >= {"bmad-switch", "extra"}


def test_an_unchanged_file_is_nothing_to_record_even_under_apply(adopted, monkeypatch):
    spy = _WriteSpy(monkeypatch)
    state_bytes = (adopted / STATE_PATH).read_bytes()

    result = run_accept(adopted, _manifest(), "bmad-switch", apply=True, reason="nothing changed")

    assert result.changes == ()
    assert result.applied is False
    assert result.to_json_dict()["status"] == "nothing-to-record"
    assert spy.calls == []
    assert (adopted / STATE_PATH).read_bytes() == state_bytes
    assert "nothing to record" in render_accept_text(result)


# --- AC2: hybrid regions --------------------------------------------------------


def test_a_hybrid_region_is_accepted_alone_and_body_sha_follows_the_first_span(adopted):
    new_beta = _edit_region(adopted, "beta")
    before = _record(adopted, "hybrid")
    alpha_before = next(s for s in before.inserted_region_spans if s.name == "alpha")

    result = run_accept(adopted, _manifest(), "hybrid#beta", apply=True, reason="beta is ours now")

    assert [(c.artifact_id, c.region) for c in result.changes] == [("hybrid", "beta")]
    after = _record(adopted, "hybrid")
    spans = {span.name: span for span in after.inserted_region_spans}
    assert spans["beta"].body_sha == new_beta
    assert spans["alpha"] == alpha_before  # the untouched region's record is byte-for-byte unchanged
    assert after.body_sha == after.inserted_region_spans[0].body_sha  # ManagedArtifact's hybrid invariant
    state = read_state(adopted)
    assert state is not None
    assert [(a.id, a.region) for a in state.acceptances] == [("hybrid", "beta")]


def test_a_hybrid_without_a_region_suffix_accepts_every_changed_region(adopted):
    new_alpha = _edit_region(adopted, "alpha")
    new_beta = _edit_region(adopted, "beta")

    result = run_accept(adopted, _manifest(), "hybrid", apply=True, reason="both regions are ours")

    assert sorted(c.region for c in result.changes) == ["alpha", "beta"]
    after = _record(adopted, "hybrid")
    assert {s.name: s.body_sha for s in after.inserted_region_spans} == {"alpha": new_alpha, "beta": new_beta}
    assert after.body_sha == after.inserted_region_spans[0].body_sha
    state = read_state(adopted)
    assert state is not None
    assert len(state.acceptances) == 2
    # and the guard now agrees: seed check names no modified region
    _commit_all(adopted)
    report = run_check(adopted, _manifest())
    assert not [f for f in report.findings if f.type.value == "managed-region-modified"]


def test_accepting_one_region_leaves_the_other_edit_guarded(adopted):
    _edit_region(adopted, "alpha")
    _edit_region(adopted, "beta")
    run_accept(adopted, _manifest(), "hybrid#alpha", apply=True, reason="only alpha")
    _commit_all(adopted)

    report = run_check(adopted, _manifest())
    modified = [f for f in report.findings if f.type.value == "managed-region-modified"]
    assert len(modified) == 1
    assert "beta" in modified[0].message


@pytest.mark.parametrize(
    ("target", "needle"),
    [("hybrid#gamma", "gamma"), ("bmad-switch#alpha", "whole-file")],
)
def test_a_region_the_record_does_not_hold_is_refused(adopted, target, needle):
    _edit(adopted, SWITCH, "edit\n")
    with pytest.raises(PreconditionFailure) as raised:
        run_accept(adopted, _manifest(), target, apply=True, reason="why")
    assert needle in str(raised.value)


def test_a_deleted_region_is_refused_not_accepted(adopted):
    (adopted / HYBRID).write_text("no markers any more\n", encoding="utf-8")
    _commit_all(adopted)
    with pytest.raises(PreconditionFailure) as raised:
        run_accept(adopted, _manifest(), "hybrid#alpha", apply=True, reason="why")
    assert "accept-region-missing" in str(raised.value) or "accept-unparseable" in str(raised.value)


# --- AC3: the I/O matrix of usage errors -----------------------------------------


def test_apply_without_a_reason_is_a_usage_error_and_writes_nothing(adopted, monkeypatch):
    spy = _WriteSpy(monkeypatch)
    _edit(adopted, SWITCH, "edit\n")
    for reason in (None, "", "   "):
        with pytest.raises(UsageError, match="--reason"):
            run_accept(adopted, _manifest(), "bmad-switch", apply=True, reason=reason)
    assert spy.calls == []


@pytest.mark.parametrize("target", ["", "   ", "#alpha", "hybrid#", "nope", "scripts/bmad-switch"])
def test_a_malformed_or_unknown_target_is_a_usage_error(adopted, target):
    with pytest.raises(UsageError):
        run_accept(adopted, _manifest(), target)


def test_an_unknown_id_is_named_in_the_error(adopted):
    with pytest.raises(UsageError, match="unknown artifact id 'nope'"):
        run_accept(adopted, _manifest(), "nope")


# --- AC3: precondition refusals -----------------------------------------------------


@pytest.mark.parametrize("target", ["derived", "dreams-dir", "bmad-method", "deferred"])
def test_a_directory_or_unguarded_class_is_refused(adopted, target):
    with pytest.raises(PreconditionFailure) as raised:
        run_accept(adopted, _manifest(), target)
    message = str(raised.value)
    assert "accept-unguarded-class" in message
    assert target in message
    assert "no hash guard reads" in message


def test_a_repo_owned_seeded_artifact_is_refused_as_repo_owned(adopted):
    """``detector-registry`` is recorded (it was copied-managed when adopted) but
    the manifest now says copied-seeded -- nothing to accept."""
    _edit(adopted, REGISTRY, "# the repo's own detectors\n")
    with pytest.raises(PreconditionFailure) as raised:
        run_accept(adopted, _manifest(), "detector-registry", apply=True, reason="why")
    assert "accept-repo-owned" in str(raised.value)
    assert "repo-owned" in str(raised.value)


def test_an_unclaimed_seeded_artifact_is_refused_as_not_claimed(adopted):
    """``unclaimed`` is declared by the manifest but was never adopted, so state
    holds no record of it: "not claimed" outranks "repo-owned"."""
    manifest = _manifest()
    manifest = dataclasses.replace(
        manifest, entries=(*manifest.entries, _entry("unclaimed", ArtifactClass.COPIED_SEEDED, "UNCLAIMED.md"))
    )
    with pytest.raises(PreconditionFailure) as raised:
        run_accept(adopted, manifest, "unclaimed")
    assert "accept-not-claimed" in str(raised.value)
    assert "not recorded" in str(raised.value)


def test_a_never_adopted_repo_is_refused_as_not_claimed(repo):
    with pytest.raises(PreconditionFailure, match="accept-not-claimed"):
        run_accept(repo, _manifest(), "bmad-switch")


def test_a_directory_that_is_not_a_git_repo_is_refused(tmp_path):
    with pytest.raises(PreconditionFailure):
        run_accept(tmp_path, _manifest(), "bmad-switch")


def test_a_path_a_recorded_skip_matches_is_refused(adopted):
    state = read_state(adopted)
    assert state is not None
    write_state(dataclasses.replace(state, skips=("scripts/*",)), repo_root=adopted, never_write=_NO_NEVER_WRITE)
    _edit(adopted, SWITCH, "an intended edit\n")
    with pytest.raises(PreconditionFailure, match="accept-skipped"):
        run_accept(adopted, _manifest(), "bmad-switch")


def test_an_absent_file_is_refused(adopted):
    (adopted / SWITCH).unlink()
    _commit_all(adopted)
    with pytest.raises(PreconditionFailure, match="accept-absent"):
        run_accept(adopted, _manifest(), "bmad-switch")


def test_a_symlink_is_refused(adopted):
    (adopted / SWITCH).unlink()
    (adopted / SWITCH).symlink_to(adopted / "README.md")
    _commit_all(adopted)
    with pytest.raises(PreconditionFailure) as raised:
        run_accept(adopted, _manifest(), "bmad-switch")
    assert "accept-not-a-file" in str(raised.value) or "accept-escapes-repo" in str(raised.value)


def test_a_corrupt_state_is_state_invalid_never_treated_as_absent(adopted):
    (adopted / STATE_PATH).write_text("this: is: not: valid\n", encoding="utf-8")
    with pytest.raises(StateInvalid):
        run_accept(adopted, _manifest(), "bmad-switch")


# --- AC4: the write is the state store's, once ---------------------------------------


def test_a_refused_apply_never_reaches_write_state(adopted, monkeypatch):
    spy = _WriteSpy(monkeypatch)
    for target in ("derived", "custom-config", "detector-registry"):
        with pytest.raises(PreconditionFailure):
            run_accept(adopted, _manifest(), target, apply=True, reason="why")
    assert spy.calls == []


def test_apply_changes_no_file_but_the_state_file(adopted):
    _edit(adopted, SWITCH, "an intended edit\n")
    _edit_region(adopted, "alpha")
    before = {
        path.relative_to(adopted).as_posix(): path.read_bytes()
        for path in adopted.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(adopted).parts
    }

    run_accept(adopted, _manifest(), "bmad-switch", apply=True, reason="why")
    _commit_all(adopted)  # accept needs a clean worktree to apply; the state file is its own one change
    run_accept(adopted, _manifest(), "hybrid#alpha", apply=True, reason="why")

    after = {
        path.relative_to(adopted).as_posix(): path.read_bytes()
        for path in adopted.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(adopted).parts
    }
    changed = {name for name in before if before[name] != after.get(name)}
    assert changed == {STATE_PATH}
    assert set(after) == set(before)  # in particular, no .marshal/plan.json appeared


# --- AC7: the guard follows the manifest's CURRENT class -------------------------------


def test_a_copied_seeded_whole_file_is_no_longer_hash_guarded(adopted):
    """The record was written while ``detector-registry`` was copied-managed;
    the manifest's current class is copied-seeded, so rung 6 and ``seed check``
    both leave the edit alone."""
    _edit(adopted, REGISTRY, "# the repo's own detectors\n")
    legacy = _manifest(registry_class=ArtifactClass.COPIED_MANAGED)
    seeded = _manifest(registry_class=ArtifactClass.COPIED_SEEDED)

    # under the legacy class the same state still refuses (the guard reads the manifest, not the record)
    with pytest.raises(PreconditionFailure, match="managed-content-modified"):
        run_adopt(adopted, legacy, apply=True, yes=True, confirm=_unreachable_confirm, commit=_unreachable_commit)
    assert [f for f in run_check(adopted, legacy).findings if f.type.value == "managed-file-modified"]

    run_adopt(adopted, seeded, apply=True, yes=True, confirm=_unreachable_confirm, commit=_unreachable_commit)
    regenerated: list[str] = []
    materialize = _fake_commit(seeded, adopted)

    def recording_commit(action: Action) -> None:
        regenerated.append(action.artifact_id)
        materialize(action)

    run_update(adopted, seeded, run=True, yes=True, confirm=_unreachable_confirm, commit=recording_commit)
    assert "detector-registry" not in regenerated  # a repo-owned file is never regenerated
    assert not [f for f in run_check(adopted, seeded).findings if f.type.value == "managed-file-modified"]
    assert (adopted / REGISTRY).read_text(encoding="utf-8") == "# the repo's own detectors\n"


def test_a_copied_managed_whole_file_stays_guarded(adopted):
    _edit(adopted, SWITCH, "an intended edit\n")
    seeded = _manifest()
    with pytest.raises(PreconditionFailure, match="managed-content-modified"):
        run_adopt(adopted, seeded, apply=True, yes=True, confirm=_unreachable_confirm, commit=_unreachable_commit)
    with pytest.raises(PreconditionFailure, match="managed-content-modified"):
        run_update(adopted, seeded, run=True, yes=True, confirm=_unreachable_confirm, commit=_unreachable_commit)
    findings = run_check(adopted, seeded).findings
    assert [f for f in findings if f.type.value == "managed-file-modified" and f.path == SWITCH]


def test_a_hybrid_managed_region_stays_guarded(adopted):
    _edit_region(adopted, "alpha")
    seeded = _manifest()
    with pytest.raises(PreconditionFailure, match="managed-content-modified"):
        run_adopt(adopted, seeded, apply=True, yes=True, confirm=_unreachable_confirm, commit=_unreachable_commit)
    findings = run_check(adopted, seeded).findings
    assert [f for f in findings if f.type.value == "managed-region-modified"]
