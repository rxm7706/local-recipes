"""Unit tests for ``pyforge.marshal.seed.verbs.adopt`` (Story 10.6) -- covers
every row of the spec's I/O & Edge-Case Matrix: dry-run on a never-adopted
repo (``.marshal/plan.json`` written and printed, nothing else touched), the
FR-83/FR-84 sequence (a brownfield ``generated-derived``/``copied-managed``
path is claimed and overwritten on FIRST adopt; a SECOND ``adopt`` on the
unchanged, committed repo produces a truly empty plan and writes NOTHING at
all, not even a ``last_update`` timestamp refresh), the injectable ``confirm``
seam (accepted/declined/never touched by ``--yes`` or a dry-run -- never a
real blocking ``input()``), a dirty worktree refusing ``--apply`` but not
dry-run, hand-edited managed content refusing without ``--force`` and
succeeding with it, a preserved-and-recorded ``present-legacy`` artifact,
``--agents``'s idempotent union, ``--skip`` recorded into ``state.skips[]``
and protecting a hand-edited artifact from rung 6, the ``applies_to``
manifest filter (an ``init``-only entry never reaches the plan), a corrupt
state file propagating ``StateInvalid`` rather than being silently treated
as "never adopted" (the mutating-verb distinction from ``verbs/check.py``'s
own read-only downgrade), and the real ``_default_commit`` builder wired
against ``engine.copier.materialize`` -- a whole-file entry via an injected
``template_path``, and a hybrid-region entry via the REAL packaged region
fragments (``template_path=None``), which needs no such injection at all
(see ``verbs/adopt.py``'s own module docstring for why).

Manifest/git-repo builders mirror ``test_seed_verbs_check.py``'s
``_manifest``/``_referenced``/``_whole_file``/``_hybrid`` and
``_git``/``_init_git_repo``/``_commit_all`` real-git-repo convention (real
``git`` I/O against a ``tmp_path``, never mocked). A "hand-edited managed
content" scenario is seeded through a REAL prior ``run_adopt(..., apply=True,
yes=True, ...)`` call (``_adopt_hybrid_once``) rather than a hand-built
``SeedState``, so the recorded ``body_sha``/region span are always exactly
what a real adopt would have written. The ``commit`` double (``_fake_commit``)
writes a whole-file artifact with plain ``Path.write_text`` and a
hybrid-region artifact through the REAL ``regions.apply.insert_region``
primitive (never faked -- it is small, already exhaustively tested on its
own, and using it for real is what lets this file's own post-apply
``state.managed[]`` assertions mean something): P-01 constrains what
``seed/`` modules may call, not what a test's own caller-supplied callback
does, matching ``test_seed_apply_run.py``'s own stated convention for its
``_committer`` double.

Story 10.8 adds one more, at the end of this file: the REAL packaged
manifest's own ``dreams-readme`` entry (``docs/dreams/README.md``,
``copied-managed``) matches the manifest's own ``docs/dreams/*.md``
never-write glob, so ``run_adopt(..., apply=True)`` against a fresh repo
missing that file refused it UNCONDITIONALLY at ``check_preconditions``'s
rung 4 before this story's ``NeverWrite.exempt``/``writable_exemptions``
fix -- confirmed live and cited verbatim in the spec's own Problem
statement. That test skips every OTHER manifest entry (derived from the
loaded manifest itself, never hardcoded) so its only materialized
artifact, and its only exercised never-write decision, is ``dreams-readme``;
a minimal injected ``commit`` double supplies its content -- see that
test's own docstring for why an injected ``template_path`` (this file's
usual whole-file seam) is deliberately NOT used here."""

from __future__ import annotations

import subprocess
import tempfile
from importlib import resources
from pathlib import Path

import pytest

from pyforge.marshal.seed.errors import PreconditionFailure, StateInvalid
from pyforge.marshal.seed.fs import NeverWrite
from pyforge.marshal.seed.model.manifest import (
    AppliesTo,
    ArtifactClass,
    Manifest,
    ManifestEntry,
    Region,
    load_manifest,
)
from pyforge.marshal.seed.model.version import ModelVersion
from pyforge.marshal.seed.plan.build import _GIT_TIMEOUT_S as _BUILD_GIT_TIMEOUT_S
from pyforge.marshal.seed.plan.types import Action
from pyforge.marshal.seed.regions.apply import insert_region
from pyforge.marshal.seed.regions.markers import RegionFormat
from pyforge.marshal.seed.state import (
    ManagedArtifact,
    SeedState,
    read_state,
    write_state,
)
from pyforge.marshal.seed.verbs.adopt import _GIT_TIMEOUT_S, run_adopt

_VERSION = ModelVersion.parse("1.0.0")
_NO_NEVER_WRITE = NeverWrite(patterns=())


# --- manifest builders (mirrors test_seed_verbs_check.py) -------------------


def _manifest(*entries: ManifestEntry, model_version: ModelVersion = _VERSION) -> Manifest:
    return Manifest(model_version=model_version, never_write=(), entries=tuple(entries))


def _copied_managed(entry_id: str, path: str, *, applies_to: AppliesTo = AppliesTo.BOTH) -> ManifestEntry:
    return ManifestEntry(
        id=entry_id,
        artifact_class=ArtifactClass.COPIED_MANAGED,
        path=path,
        applies_to=applies_to,
        rationale="test",
    )


def _generated_derived(entry_id: str, path: str, *, applies_to: AppliesTo = AppliesTo.BOTH) -> ManifestEntry:
    return ManifestEntry(
        id=entry_id,
        artifact_class=ArtifactClass.GENERATED_DERIVED,
        path=path,
        applies_to=applies_to,
        rationale="test",
    )


def _copied_seeded(entry_id: str, path: str, *, applies_to: AppliesTo = AppliesTo.BOTH) -> ManifestEntry:
    return ManifestEntry(
        id=entry_id,
        artifact_class=ArtifactClass.COPIED_SEEDED,
        path=path,
        applies_to=applies_to,
        rationale="test",
    )


def _hybrid(entry_id: str, path: str, *region_names: str, applies_to: AppliesTo = AppliesTo.BOTH) -> ManifestEntry:
    return ManifestEntry(
        id=entry_id,
        artifact_class=ArtifactClass.HYBRID_MANAGED_REGION,
        path=path,
        applies_to=applies_to,
        rationale="test",
        format=RegionFormat.HTML,
        regions=tuple(Region(name=name, anchor=("# anchor",)) for name in region_names),
    )


def _legacy(entry_id: str, path: str, *, legacy_of: str) -> ManifestEntry:
    return ManifestEntry(
        id=entry_id,
        artifact_class=ArtifactClass.COPIED_MANAGED,
        path=path,
        applies_to=AppliesTo.BOTH,
        rationale="test",
        legacy_of=legacy_of,
    )


# --- real-git fixtures (mirrors test_seed_verbs_check.py) -------------------


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


# --- confirm doubles (never a real blocking input(), per this story's AC) --


def _unreachable_confirm() -> bool:
    raise AssertionError("confirm() should not have been called")


# --- commit doubles ----------------------------------------------------


def _unreachable_commit(action: Action) -> None:
    raise AssertionError(f"commit() should not have been called for {action.artifact_id!r}")


def _fake_commit(manifest: Manifest, repo_root: Path, calls: list[str] | None = None):
    """A ``commit`` double that records every call (when ``calls`` is
    given), materializes a deterministic marker for a whole-file class via
    plain ``Path.write_text`` (P-01 constrains ``seed/`` modules, not a
    test's own double -- see the module docstring), and inserts a
    deterministic region body for a hybrid class through the REAL
    ``regions.apply.insert_region`` primitive."""
    entries_by_id = {entry.id: entry for entry in manifest.entries}

    def commit(action: Action) -> None:
        if calls is not None:
            calls.append(action.artifact_id)
        entry = entries_by_id[action.artifact_id]
        target = repo_root / action.target_path
        if entry.artifact_class is ArtifactClass.HYBRID_MANAGED_REGION:
            assert entry.format is not None
            for region_name, _matched_anchor in action.chosen_anchor:
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
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(f"materialized {action.artifact_id}\n", encoding="utf-8")

    return commit


# --- dry-run (no flags) on a never-adopted repo -----------------------------


def test_dry_run_on_never_adopted_repo_writes_plan_json_and_prints_it_no_other_writes(clean_repo):
    manifest = _manifest(
        _copied_managed("whole", "WHOLE.md"),
        _hybrid("hybrid", "HYBRID.md", "tiers"),
    )
    before = {path.name for path in clean_repo.iterdir()}

    result = run_adopt(clean_repo, manifest, confirm=_unreachable_confirm)

    assert result.applied is None
    assert result.declined is False
    assert {action.artifact_id for action in result.plan.actions} == {"whole", "hybrid"}
    plan_path = clean_repo / ".marshal" / "plan.json"
    assert plan_path.is_file()
    assert not (clean_repo / "WHOLE.md").exists()
    assert not (clean_repo / "HYBRID.md").exists()
    assert not (clean_repo / ".marshal" / "seed-state.yml").exists()
    after = {path.name for path in clean_repo.iterdir()}
    assert after - before == {".marshal"}


# --- --apply --yes on the same repo -----------------------------------------


def test_apply_yes_materializes_every_planned_artifact_and_writes_state_last(clean_repo):
    manifest = _manifest(
        _copied_managed("whole", "WHOLE.md"),
        _hybrid("hybrid", "HYBRID.md", "tiers"),
    )
    calls: list[str] = []

    result = run_adopt(
        clean_repo,
        manifest,
        apply=True,
        yes=True,
        confirm=_unreachable_confirm,
        commit=_fake_commit(manifest, clean_repo, calls),
    )

    assert result.declined is False
    assert set(result.applied) == {"whole", "hybrid"}
    assert (clean_repo / "WHOLE.md").read_text() == "materialized whole\n"
    assert "body for tiers" in (clean_repo / "HYBRID.md").read_text()
    state = read_state(clean_repo)
    assert state is not None
    assert state.mode == "adopt"
    assert {record.id for record in state.managed} == {"whole", "hybrid"}


def test_state_is_not_written_when_apply_fails_mid_run(clean_repo):
    """State is written LAST, only after ``run_apply`` returns
    successfully -- a mid-run failure must leave no ``seed-state.yml`` at
    all, proving the write genuinely happens after every file write
    succeeds rather than merely being coded last in the source."""
    manifest = _manifest(_copied_managed("a", "A.md"), _copied_managed("b", "B.md"))

    def boom_commit(action: Action) -> None:
        if action.artifact_id == "b":
            raise RuntimeError("boom")
        (clean_repo / action.target_path).write_text("materialized\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="boom"):
        run_adopt(clean_repo, manifest, apply=True, yes=True, confirm=_unreachable_confirm, commit=boom_commit)

    assert not (clean_repo / ".marshal" / "seed-state.yml").exists()


# --- second adopt (dry-run) on the now-adopted, unchanged repo -------------


def test_second_dry_run_on_unchanged_adopted_repo_is_empty_but_still_writes_plan_json(clean_repo):
    manifest = _manifest(_copied_managed("whole", "WHOLE.md"), _hybrid("hybrid", "HYBRID.md", "tiers"))
    run_adopt(
        clean_repo,
        manifest,
        apply=True,
        yes=True,
        confirm=_unreachable_confirm,
        commit=_fake_commit(manifest, clean_repo),
    )
    _commit_all(clean_repo)

    result = run_adopt(clean_repo, manifest, confirm=_unreachable_confirm)

    assert result.plan.actions == ()
    assert (clean_repo / ".marshal" / "plan.json").is_file()


# --- second adopt --apply --yes on the unchanged repo -----------------------


def test_second_apply_yes_on_unchanged_repo_is_a_noop_state_not_rewritten(clean_repo):
    manifest = _manifest(_copied_managed("whole", "WHOLE.md"), _hybrid("hybrid", "HYBRID.md", "tiers"))
    run_adopt(
        clean_repo,
        manifest,
        apply=True,
        yes=True,
        confirm=_unreachable_confirm,
        commit=_fake_commit(manifest, clean_repo),
    )
    _commit_all(clean_repo)
    state_path = clean_repo / ".marshal" / "seed-state.yml"
    before_text = state_path.read_text(encoding="utf-8")

    result = run_adopt(
        clean_repo,
        manifest,
        apply=True,
        yes=True,
        confirm=_unreachable_confirm,
        commit=_unreachable_commit,
    )

    assert result.applied == ()
    assert result.plan.actions == ()
    assert state_path.read_text(encoding="utf-8") == before_text


# --- brownfield first-claim (FR-83) -----------------------------------------


def test_first_claim_overwrites_a_preexisting_unrelated_file_at_a_generated_derived_path(clean_repo):
    (clean_repo / "GENERATED.md").write_text("unrelated pre-existing content\n", encoding="utf-8")
    _commit_all(clean_repo)
    manifest = _manifest(_generated_derived("gen", "GENERATED.md"))

    result = run_adopt(
        clean_repo,
        manifest,
        apply=True,
        yes=True,
        confirm=_unreachable_confirm,
        commit=_fake_commit(manifest, clean_repo),
    )

    assert result.applied == ("gen",)
    assert (clean_repo / "GENERATED.md").read_text() == "materialized gen\n"
    state = read_state(clean_repo)
    assert {record.id for record in state.managed} == {"gen"}


def _state(**overrides) -> SeedState:
    fields: dict = {
        "model_version": _VERSION,
        "seed_model_version": "0.1.0",
        "adopted_at": "2026-08-21T09:00:00Z",
        "last_update": "2026-08-21T09:00:00Z",
        "mode": "adopt",
        "agents": (),
        "managed": (),
        "skips": (),
        "legacy": (),
        "migrations_applied": (),
        "opted_out": (),
    }
    fields.update(overrides)
    return SeedState(**fields)


def test_first_claim_reclaims_when_a_stale_record_names_a_different_path(clean_repo):
    """Review finding, mirroring ``verbs/check.py``'s own already-fixed
    identical trap (AD-55: id is the stable address, path can move): a
    ``state.managed`` record for id ``gen`` names a STALE path
    (``OLD.md``), but the manifest's current entry for that same id points
    at ``NEW.md``, where an unrelated file already exists (PRESENT_CONFORMANT).
    Trusting the id-only match would permanently orphan ``NEW.md`` -- no
    ``build_plan`` Action exists for a PRESENT_CONFORMANT entry, and the
    (buggy, pre-fix) augmentation would have skipped it as "already
    claimed" at a path that no longer describes anything real. The fixed
    augmentation re-claims it at the CURRENT path, and the stale
    old-path record is dropped (never two records survive for one id)."""
    (clean_repo / "NEW.md").write_text("unrelated content at the new path\n", encoding="utf-8")
    _commit_all(clean_repo)
    manifest = _manifest(_generated_derived("gen", "NEW.md"))
    write_state(
        _state(
            managed=(
                ManagedArtifact(
                    id="gen",
                    path="OLD.md",  # stale -- the manifest entry's path has since moved
                    artifact_class="generated-derived",
                    body_sha="deadbeef",
                    inserted_region_span=None,
                ),
            )
        ),
        repo_root=clean_repo,
        never_write=_NO_NEVER_WRITE,
    )
    _commit_all(clean_repo)

    result = run_adopt(
        clean_repo,
        manifest,
        apply=True,
        yes=True,
        confirm=_unreachable_confirm,
        commit=_fake_commit(manifest, clean_repo),
    )

    assert result.applied == ("gen",)
    assert (clean_repo / "NEW.md").read_text() == "materialized gen\n"
    state = read_state(clean_repo)
    # Exactly one record for id "gen", at the NEW path -- the stale
    # OLD.md record is gone, never two records surviving for one id.
    gen_records = [record for record in state.managed if record.id == "gen"]
    assert len(gen_records) == 1
    assert gen_records[0].path == "NEW.md"


def test_first_claim_never_fires_for_hybrid_or_copied_seeded_classes(clean_repo):
    """FR-83's scope is exactly ``copied-managed``/``generated-derived``
    (the epics AC's own two named classes) -- a PRESENT_CONFORMANT hybrid
    entry (every declared region already present) or copied-seeded entry
    must never be claimed."""
    (clean_repo / "HYBRID.md").write_text(
        "intro\n<!-- marshal-seed:begin region=tiers model-version=1.0.0 sha=00000000 -->\n"
        "body\n<!-- marshal-seed:end region=tiers -->\n",
        encoding="utf-8",
    )
    (clean_repo / "SEEDED.md").write_text("unrelated\n", encoding="utf-8")
    _commit_all(clean_repo)
    manifest = _manifest(
        _hybrid("hybrid", "HYBRID.md", "tiers"),
        _copied_seeded("seeded", "SEEDED.md"),
    )

    result = run_adopt(clean_repo, manifest, confirm=_unreachable_confirm)

    assert result.plan.actions == ()


# --- --apply without --yes, confirmation declined ---------------------------


def test_apply_without_yes_confirmation_declined_writes_nothing_beyond_plan_json(clean_repo):
    manifest = _manifest(_copied_managed("whole", "WHOLE.md"))

    result = run_adopt(clean_repo, manifest, apply=True, yes=False, confirm=lambda: False, commit=_unreachable_commit)

    assert result.declined is True
    assert result.applied is None
    assert (clean_repo / ".marshal" / "plan.json").is_file()
    assert not (clean_repo / "WHOLE.md").exists()
    assert not (clean_repo / ".marshal" / "seed-state.yml").exists()


def test_apply_without_yes_confirmation_accepted_applies(clean_repo):
    manifest = _manifest(_copied_managed("whole", "WHOLE.md"))
    calls: list[str] = []

    result = run_adopt(
        clean_repo,
        manifest,
        apply=True,
        yes=False,
        confirm=lambda: True,
        commit=_fake_commit(manifest, clean_repo, calls),
    )

    assert result.declined is False
    assert result.applied == ("whole",)
    assert calls == ["whole"]


def test_confirm_is_never_called_when_yes_is_given(clean_repo):
    manifest = _manifest(_copied_managed("whole", "WHOLE.md"))

    run_adopt(
        clean_repo,
        manifest,
        apply=True,
        yes=True,
        confirm=_unreachable_confirm,
        commit=_fake_commit(manifest, clean_repo),
    )


def test_confirm_is_never_called_on_a_dry_run(clean_repo):
    manifest = _manifest(_copied_managed("whole", "WHOLE.md"))

    run_adopt(clean_repo, manifest, confirm=_unreachable_confirm)


# --- dirty worktree ----------------------------------------------------


def test_dirty_worktree_with_apply_is_refused(clean_repo):
    (clean_repo / "untracked.txt").write_text("x\n", encoding="utf-8")
    manifest = _manifest(_copied_managed("whole", "WHOLE.md"))

    with pytest.raises(PreconditionFailure, match="dirty-worktree"):
        run_adopt(clean_repo, manifest, apply=True, yes=True, confirm=_unreachable_confirm, commit=_unreachable_commit)


def test_dirty_worktree_with_dry_run_still_succeeds_and_writes_plan_json(clean_repo):
    (clean_repo / "untracked.txt").write_text("x\n", encoding="utf-8")
    manifest = _manifest(_copied_managed("whole", "WHOLE.md"))

    result = run_adopt(clean_repo, manifest, confirm=_unreachable_confirm)

    assert (clean_repo / ".marshal" / "plan.json").is_file()
    assert {action.artifact_id for action in result.plan.actions} == {"whole"}


# --- _repo_is_dirty_now: excludes ONLY the self-inflicted plan.json write --


def test_operator_dirtying_the_repo_during_the_confirm_pause_is_still_caught(clean_repo):
    """Review finding: an earlier revision of ``_repo_is_dirty_now`` was a
    TAUTOLOGY -- it re-derived the SAME unrestricted ``git status`` signal
    ``apply.run.fingerprint_drift`` re-checks a few lines later, so the
    comparison could never disagree and the dirty-drift protection was
    silently defeated for the entire confirm-prompt window, not merely for
    the expected ``plan.json`` write it was written to correct for. The
    fixed design adds a SEPARATE, explicit check
    (``_unexpected_dirt_since_plan_write``) that excludes ONLY
    ``.marshal/`` (this run's own self-inflicted write) via a git pathspec
    and runs BEFORE ``run_apply`` -- so an operator's UNRELATED edit made
    while deciding whether to confirm -- simulated here by a ``confirm``
    double that dirties the repo before returning ``True`` -- is caught by
    THIS module's own clear, actionable ``dirty-worktree`` refusal, never
    silently absorbed (``fingerprint_drift``'s own ``dirty`` comparison
    cannot be made selective at all -- see ``_repo_is_dirty_now``'s own
    docstring for why -- so this dedicated check is what actually delivers
    the protection, not a restricted stamp on ``RepoFingerprint.dirty``)."""
    manifest = _manifest(_copied_managed("whole", "WHOLE.md"))

    def _confirm_and_dirty_the_repo() -> bool:
        (clean_repo / "operator-was-here.txt").write_text("unexpected edit\n", encoding="utf-8")
        return True

    with pytest.raises(PreconditionFailure, match="dirty-worktree"):
        run_adopt(
            clean_repo,
            manifest,
            apply=True,
            yes=False,
            confirm=_confirm_and_dirty_the_repo,
            commit=_unreachable_commit,
        )


def test_repo_is_dirty_now_wraps_a_launch_failure_as_precondition_failure(clean_repo, monkeypatch):
    """Review finding: ``PosixProcess.run`` raises ``ProcessError`` (never
    a bare exception) when the process could not even be launched (a
    missing ``git`` executable, or the call timing out) -- distinct from a
    non-zero exit, which it returns rather than raises. The pre-fix
    ``_repo_is_dirty_now`` let that ``ProcessError`` escape uncaught,
    landing on the generic, non-actionable CLI backstop instead of a
    targeted, remedied ``PreconditionFailure``."""
    from pyforge.core.process import ProcessError

    import pyforge.marshal.seed.verbs.adopt as adopt_module

    manifest = _manifest(_copied_managed("whole", "WHOLE.md"))

    class _BrokenGit:
        def run(self, *args, **kwargs):
            raise ProcessError("executable not found: 'git'")

    monkeypatch.setattr(adopt_module, "PosixProcess", _BrokenGit)

    with pytest.raises(PreconditionFailure, match="could not determine whether"):
        run_adopt(
            clean_repo,
            manifest,
            apply=True,
            yes=True,
            confirm=_unreachable_confirm,
            commit=_unreachable_commit,
        )


# --- hand-edited managed content on a re-adopt ------------------------------


def _adopt_hybrid_once(repo: Path, manifest: Manifest) -> None:
    run_adopt(repo, manifest, apply=True, yes=True, confirm=_unreachable_confirm, commit=_fake_commit(manifest, repo))
    _commit_all(repo)


def test_hand_edited_managed_content_on_reapply_is_refused_without_force(clean_repo):
    manifest = _manifest(_hybrid("hybrid", "HYBRID.md", "tiers"))
    _adopt_hybrid_once(clean_repo, manifest)

    # Mangle the managed region beyond recognition -- markers gone entirely.
    (clean_repo / "HYBRID.md").write_text("no markers here at all\n", encoding="utf-8")
    _commit_all(clean_repo)

    with pytest.raises(PreconditionFailure, match="managed-content-modified"):
        run_adopt(clean_repo, manifest, apply=True, yes=True, confirm=_unreachable_confirm, commit=_unreachable_commit)


def test_force_on_hand_edited_content_reinserts_the_managed_region(clean_repo):
    manifest = _manifest(_hybrid("hybrid", "HYBRID.md", "tiers"))
    _adopt_hybrid_once(clean_repo, manifest)

    (clean_repo / "HYBRID.md").write_text("no markers here at all\n", encoding="utf-8")
    _commit_all(clean_repo)

    result = run_adopt(
        clean_repo,
        manifest,
        apply=True,
        yes=True,
        force=True,
        confirm=_unreachable_confirm,
        commit=_fake_commit(manifest, clean_repo),
    )

    assert result.applied == ("hybrid",)
    assert "marshal-seed:begin region=tiers" in (clean_repo / "HYBRID.md").read_text()


# --- present-legacy artifacts ------------------------------------------


def test_present_legacy_artifact_is_recorded_and_never_touched(clean_repo):
    (clean_repo / "LEGACY.md").write_text("legacy content, unmanaged\n", encoding="utf-8")
    _commit_all(clean_repo)
    manifest = _manifest(_legacy("legacy", "LEGACY.md", legacy_of="successor"), _copied_managed("whole", "WHOLE.md"))
    before_legacy_text = (clean_repo / "LEGACY.md").read_text(encoding="utf-8")

    result = run_adopt(
        clean_repo,
        manifest,
        apply=True,
        yes=True,
        confirm=_unreachable_confirm,
        commit=_fake_commit(manifest, clean_repo),
    )

    assert result.applied == ("whole",)
    assert (clean_repo / "LEGACY.md").read_text(encoding="utf-8") == before_legacy_text
    state = read_state(clean_repo)
    assert [record.id for record in state.legacy] == ["legacy"]
    assert state.legacy[0].legacy_of == "successor"
    assert {record.id for record in state.managed} == {"whole"}


# --- --agents union ------------------------------------------------------


def test_agents_union_is_idempotent_and_never_drops_previous_agents(clean_repo):
    manifest = _manifest(_copied_managed("a", "A.md"), _copied_managed("b", "B.md"))
    run_adopt(
        clean_repo,
        manifest,
        apply=True,
        yes=True,
        agents=("claude", "cursor"),
        skip=("B.md",),
        confirm=_unreachable_confirm,
        commit=_fake_commit(manifest, clean_repo),
    )
    _commit_all(clean_repo)
    state_after_first = read_state(clean_repo)
    assert state_after_first.agents == ("claude", "cursor")

    # B.md was skipped on the first call, so it is still pending -- this
    # SECOND call's plan is genuinely non-empty, which is what lets the
    # state write (and therefore the agents union) actually happen.
    result = run_adopt(
        clean_repo,
        manifest,
        apply=True,
        yes=True,
        agents=("gemini",),
        confirm=_unreachable_confirm,
        commit=_fake_commit(manifest, clean_repo),
    )

    assert result.applied == ("b",)
    state_after_second = read_state(clean_repo)
    assert state_after_second.agents == ("claude", "cursor", "gemini")


# --- --skip ------------------------------------------------------------


def test_skip_glob_is_recorded_into_state_skips_and_the_artifact_is_left_alone(clean_repo):
    manifest = _manifest(_copied_managed("whole", "WHOLE.md"), _copied_managed("other", "OTHER.md"))

    result = run_adopt(
        clean_repo,
        manifest,
        apply=True,
        yes=True,
        skip=("OTHER.md",),
        confirm=_unreachable_confirm,
        commit=_fake_commit(manifest, clean_repo),
    )

    assert result.applied == ("whole",)
    assert not (clean_repo / "OTHER.md").exists()
    state = read_state(clean_repo)
    assert "OTHER.md" in state.skips
    assert {record.id for record in state.managed} == {"whole"}


def test_skip_protects_a_hand_edited_artifact_from_rung_6_refusal(clean_repo):
    manifest = _manifest(_hybrid("hybrid", "HYBRID.md", "tiers"))
    _adopt_hybrid_once(clean_repo, manifest)
    (clean_repo / "HYBRID.md").write_text("mangled beyond recognition\n", encoding="utf-8")
    _commit_all(clean_repo)

    # Without --skip, this run refuses at rung 6.
    with pytest.raises(PreconditionFailure, match="managed-content-modified"):
        run_adopt(clean_repo, manifest, apply=True, yes=True, confirm=_unreachable_confirm, commit=_unreachable_commit)

    # With --skip protecting it, the run proceeds -- there is nothing else
    # pending, so the plan is empty and nothing is applied, but critically
    # it does NOT refuse.
    result = run_adopt(
        clean_repo,
        manifest,
        apply=True,
        yes=True,
        skip=("HYBRID.md",),
        confirm=_unreachable_confirm,
        commit=_unreachable_commit,
    )
    assert result.declined is False


# --- applies_to manifest filter ------------------------------------------


def test_applies_to_init_only_entries_are_excluded_from_the_plan(clean_repo):
    manifest = _manifest(
        _copied_seeded("starter-dream", "docs/dreams/{{ slug }}.md", applies_to=AppliesTo.INIT),
        _copied_managed("whole", "WHOLE.md"),
    )

    result = run_adopt(clean_repo, manifest, confirm=_unreachable_confirm)

    assert {action.artifact_id for action in result.plan.actions} == {"whole"}


def test_applies_to_adopt_only_entries_are_included(clean_repo):
    manifest = _manifest(_generated_derived("adopt-only", "ADOPT_ONLY.md", applies_to=AppliesTo.ADOPT))

    result = run_adopt(clean_repo, manifest, confirm=_unreachable_confirm)

    assert {action.artifact_id for action in result.plan.actions} == {"adopt-only"}


# --- StateInvalid propagates, never downgraded ------------------------------


def test_state_invalid_propagates_rather_than_being_treated_as_never_adopted(clean_repo):
    """Unlike ``verbs/check.py`` (a read-only report, which downgrades a
    caught ``StateInvalid`` to a ``state=None`` view and keeps going),
    ``adopt`` is a MUTATING verb -- silently treating corrupted state as
    absent would let this run overwrite hand-edited managed content state
    itself can no longer attest to (SC-04). The exception must propagate
    unchanged."""
    state_dir = clean_repo / ".marshal"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "seed-state.yml").write_text("{}\n", encoding="utf-8")
    _commit_all(clean_repo)
    manifest = _manifest(_copied_managed("whole", "WHOLE.md"))

    with pytest.raises(StateInvalid):
        run_adopt(clean_repo, manifest, confirm=_unreachable_confirm)


# --- agreement test (mirrors test_seed_verbs_preconditions.py's own) -------


def test_git_timeout_agrees_with_plan_build(clean_repo):
    """``verbs/adopt.py``'s own git-probe timeout (used to refresh the
    fingerprint's ``dirty`` flag after ``write_plan``'s own known,
    expected side effect -- see ``_repo_is_dirty_now``'s docstring) is
    pinned to ``plan.build``'s identical constant, the same agreement
    ``verbs/preconditions.py`` already keeps against the same module."""
    assert _GIT_TIMEOUT_S == _BUILD_GIT_TIMEOUT_S


# --- _default_commit: the real engine.copier.materialize wiring ------------


def test_default_commit_materializes_a_whole_file_entry_via_a_custom_template(clean_repo):
    template_root = Path(tempfile.mkdtemp())
    (template_root / ".bmad-config.user.toml").write_text('[project]\nname = "test"\n', encoding="utf-8")
    manifest = _manifest(_copied_managed("cfg", ".bmad-config.user.toml"))

    result = run_adopt(
        clean_repo,
        manifest,
        apply=True,
        yes=True,
        confirm=_unreachable_confirm,
        template_path=template_root,
    )

    assert result.applied == ("cfg",)
    assert (clean_repo / ".bmad-config.user.toml").read_text(encoding="utf-8") == ('[project]\nname = "test"\n')


def test_default_commit_materializes_a_hybrid_region_via_the_real_packaged_fragments(clean_repo):
    """No ``template_path`` injection needed here (``template_path=None``,
    the production default) -- the packaged ``seed/templates/files/
    tiers.md.j2`` fragment is read directly, never routed through
    ``engine.copier.materialize`` at all (see ``verbs/adopt.py``'s own
    module docstring)."""
    (clean_repo / "CLAUDE.md").write_text("# My project\n\nSome existing repo-specific guidance.\n", encoding="utf-8")
    _commit_all(clean_repo)
    manifest = _manifest(
        ManifestEntry(
            id="claude-md-test",
            artifact_class=ArtifactClass.HYBRID_MANAGED_REGION,
            path="CLAUDE.md",
            applies_to=AppliesTo.BOTH,
            rationale="test",
            format=RegionFormat.HTML,
            regions=(Region(name="tiers", anchor=("### Spec-driven, framework-neutral layout",)),),
        )
    )

    result = run_adopt(clean_repo, manifest, apply=True, yes=True, confirm=_unreachable_confirm)

    assert result.applied == ("claude-md-test",)
    content = (clean_repo / "CLAUDE.md").read_text(encoding="utf-8")
    assert "Some existing repo-specific guidance." in content
    assert "marshal-seed:begin region=tiers" in content
    assert "Build More Architect Dreams" in content  # real fragment content, not a fake body


def test_projects_table_region_is_derived_from_real_bmad_config_toml_files_via_run_adopt(clean_repo, real_manifest):
    """The bad_spec loopback's own root-cause regression (spec's own Spec
    Change Log): the prior implementation pass shipped a static
    ``templates/files/projects-table.md.j2`` placeholder that would have
    shipped, silently and unconditionally, as ``PROJECTS.md``'s real table
    content through this exact, pre-existing, unmodified
    ``_default_commit``/``HYBRID_MANAGED_REGION`` dispatch --
    ``derive.projects_index.derive_projects_table`` was fully implemented
    and unit-tested but completely UNREACHABLE from any real code path.
    This test proves the wiring end to end, against the REAL packaged
    manifest (mirroring ``test_dreams_readme_materializes_against_the_real_
    manifest_previously_refused_unconditionally``'s own skip-everything-
    except-one-entry pattern): a real ``run_adopt`` call derives
    ``projects-table``'s body from real ``.bmad-config.toml`` fixture
    files -- not a static fragment -- while the hand-written prose
    elsewhere in ``PROJECTS.md`` survives untouched."""
    (clean_repo / "_bmad-output").mkdir()
    (clean_repo / "_bmad-output" / "PROJECTS.md").write_text(
        "# BMAD Projects in this Repository\n\nSome hand-written prose that must survive untouched.\n\n## Projects\n",
        encoding="utf-8",
    )
    for slug, description in (
        ("pyforge-atlas", "Atlas project description."),
        ("pyforge-marshal", "Marshal project description."),
    ):
        config = clean_repo / "_bmad-output" / "projects" / slug / ".bmad-config.toml"
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(
            f'output_folder = "_bmad-output/projects/{slug}"\n\n'
            "[project]\n"
            f'slug = "{slug}"\n'
            f'description = "{description}"\n'
            'status = "active"\n',
            encoding="utf-8",
        )
    _commit_all(clean_repo)

    skip = tuple(entry.path for entry in real_manifest.entries if entry.id != "projects-index")

    result = run_adopt(
        clean_repo,
        real_manifest,
        apply=True,
        yes=True,
        confirm=_unreachable_confirm,
        skip=skip,
    )

    assert result.applied == ("projects-index",)
    content = (clean_repo / "_bmad-output" / "PROJECTS.md").read_text(encoding="utf-8")
    assert "Some hand-written prose that must survive untouched." in content
    assert "marshal-seed:begin region=projects-table" in content
    assert "pyforge-atlas" in content
    assert "Atlas project description." in content
    assert "pyforge-marshal" in content
    assert "Marshal project description." in content


def test_a_region_named_projects_table_on_a_different_entry_id_is_not_hijacked(clean_repo):
    """Review finding, pass 2: the ``projects-table`` dispatch keys on
    BOTH ``region_name == "projects-table"`` AND ``entry.id ==
    "projects-index"`` -- region names are a namespace shared across
    manifest entries by this package's own design, so a DIFFERENT entry
    that happens to reuse "projects-table" as one of its own region names
    must still read its own static fragment, never the live project
    index."""
    template_root = Path(tempfile.mkdtemp())
    (template_root / "files").mkdir(parents=True)
    (template_root / "files" / "projects-table.md.j2").write_text("STATIC-FRAGMENT-NOT-DERIVED\n", encoding="utf-8")
    (clean_repo / "OTHER.md").write_text("# anchor\n\nExisting prose.\n", encoding="utf-8")
    _commit_all(clean_repo)
    manifest = _manifest(_hybrid("other-entry", "OTHER.md", "projects-table"))

    result = run_adopt(
        clean_repo,
        manifest,
        apply=True,
        yes=True,
        confirm=_unreachable_confirm,
        template_path=template_root,
    )

    assert result.applied == ("other-entry",)
    content = (clean_repo / "OTHER.md").read_text(encoding="utf-8")
    assert "STATIC-FRAGMENT-NOT-DERIVED" in content


def test_default_commit_calls_materialize_once_for_two_whole_file_actions(clean_repo, monkeypatch):
    """The lazy-materialize-once-per-run design (module docstring): two
    whole-file actions in one plan must trigger exactly one ``engine.
    materialize`` call, not two. Uses two REAL packaged-manifest
    ``copied-managed`` paths (``scripts/bmad-switch``/``scripts/bmad-loop-
    worktree``) so the staged output clears ``materialize()``'s own
    manifest-boundary reconciliation, which is always checked against the
    packaged manifest regardless of the ``template_path`` injected here
    (module docstring's "known limitations" (1))."""
    import pyforge.marshal.seed.verbs.adopt as adopt_module

    template_root = Path(tempfile.mkdtemp())
    (template_root / "scripts").mkdir()
    (template_root / "scripts" / "bmad-switch").write_text("content a\n", encoding="utf-8")
    (template_root / "scripts" / "bmad-loop-worktree").write_text("content b\n", encoding="utf-8")
    manifest = _manifest(
        _copied_managed("a", "scripts/bmad-switch"), _copied_managed("b", "scripts/bmad-loop-worktree")
    )

    calls = {"count": 0}
    real_materialize = adopt_module.materialize

    def counting_materialize(request):
        calls["count"] += 1
        return real_materialize(request)

    monkeypatch.setattr(adopt_module, "materialize", counting_materialize)

    result = run_adopt(
        clean_repo,
        manifest,
        apply=True,
        yes=True,
        confirm=_unreachable_confirm,
        template_path=template_root,
    )

    assert set(result.applied) == {"a", "b"}
    assert calls["count"] == 1


# --- _region_body_from_template: ambiguity + Jinja-injection guards --------


def test_region_body_from_template_raises_on_ambiguous_fragment_match(clean_repo):
    """Review finding: two fragments sharing the same region-name stem
    (``tiers.md.j2`` and ``tiers.txt.j2``) must refuse loudly rather than
    silently pick whichever sorts first -- matching this package's own
    "ambiguity is refused loudly, never silently resolved" convention."""
    from pyforge.marshal.seed.errors import InternalError
    from pyforge.marshal.seed.verbs.adopt import _region_body_from_template

    template_root = Path(tempfile.mkdtemp())
    (template_root / "files").mkdir()
    (template_root / "files" / "tiers.md.j2").write_text("body a\n", encoding="utf-8")
    (template_root / "files" / "tiers.txt.j2").write_text("body b\n", encoding="utf-8")

    with pytest.raises(InternalError, match="tiers"):
        _region_body_from_template(template_root, "tiers")


def test_region_body_from_template_raises_on_jinja_syntax_in_fragment(clean_repo):
    """Review finding: this module's whole justification for reading region
    bodies directly, bypassing ``engine.copier.materialize`` entirely,
    rests on a point-in-time audit that today's packaged fragments contain
    no Jinja syntax. A fragment that DOES contain ``{{`` must be refused
    loudly rather than spliced verbatim, un-rendered, into a real repo
    file."""
    from pyforge.marshal.seed.errors import InternalError
    from pyforge.marshal.seed.verbs.adopt import _region_body_from_template

    template_root = Path(tempfile.mkdtemp())
    (template_root / "files").mkdir()
    (template_root / "files" / "tiers.md.j2").write_text("hello {{ mode }}\n", encoding="utf-8")

    with pytest.raises(InternalError, match="Jinja"):
        _region_body_from_template(template_root, "tiers")


def test_staged_bytes_for_raises_on_ambiguous_tail_match(tmp_path):
    """Review finding, the whole-file sibling of the region-fragment
    ambiguity guard above: two staged paths whose relative paths both TAIL
    the same ``target_path`` must refuse loudly rather than silently
    writing whichever sorts first to the real repo."""
    from pyforge.marshal.seed.errors import InternalError
    from pyforge.marshal.seed.verbs.adopt import _staged_bytes_for

    stage_a = tmp_path / "stage_a" / "scripts" / "bmad-switch"
    stage_a.parent.mkdir(parents=True)
    stage_a.write_text("content a\n", encoding="utf-8")
    stage_b = tmp_path / "stage_b" / "scripts" / "bmad-switch"
    stage_b.parent.mkdir(parents=True)
    stage_b.write_text("content b\n", encoding="utf-8")

    with pytest.raises(InternalError, match="scripts/bmad-switch"):
        _staged_bytes_for([stage_a, stage_b], "scripts/bmad-switch")


def test_region_body_from_template_reads_a_single_unambiguous_static_fragment(clean_repo):
    """The non-error path still works exactly as before for a single,
    static (no ``{{``) fragment -- the two guards above must not reject the
    ordinary case."""
    from pyforge.marshal.seed.verbs.adopt import _region_body_from_template

    template_root = Path(tempfile.mkdtemp())
    (template_root / "files").mkdir()
    (template_root / "files" / "tiers.md.j2").write_text("static body\n", encoding="utf-8")

    assert _region_body_from_template(template_root, "tiers") == "static body\n"


# --- real-manifest regression: dreams-readme's own never-write collision ---
# (Story 10.8) -- see the module docstring's own closing paragraph.


@pytest.fixture(scope="module")
def real_manifest() -> Manifest:
    """The REAL packaged manifest (``seed/templates/manifest.yaml``), loaded
    through ``importlib.resources`` -- mirrors ``test_seed_verbs_check.py``'s
    own ``real_manifest`` fixture (Story 10.5's NFR-P1 test)."""
    manifest_ref = resources.files("pyforge.marshal.seed.templates") / "manifest.yaml"
    with resources.as_file(manifest_ref) as manifest_path:
        return load_manifest(manifest_path)


def test_dreams_readme_materializes_against_the_real_manifest_previously_refused_unconditionally(
    clean_repo, real_manifest
):
    """The literal, confirmed-live regression this story fixes: before
    ``NeverWrite.exempt``/``writable_exemptions``, ``dreams-readme``
    (``docs/dreams/README.md``, ``copied-managed``) matched the REAL
    manifest's own ``docs/dreams/*.md`` never-write glob, so
    ``marshal seed adopt --apply`` refused it UNCONDITIONALLY at
    ``check_preconditions``'s rung 4 -- the spec's own Problem statement,
    verbatim.

    Every OTHER entry is skipped -- derived from ``real_manifest.entries``
    itself, never a hardcoded list, so a future manifest addition never
    silently drops out of this skip set -- keeping this test's only
    materialized artifact, and its only exercised never-write decision,
    ``dreams-readme`` alone. A minimal ``commit`` double (mirroring this
    file's own ``_fake_commit`` whole-file branch) supplies its content
    instead of an injected ``template_path``: the packaged template tree
    ships no whole-file content yet for any ``copied-managed`` entry
    (module docstring's own note), and staging synthetic content for
    ``docs/dreams/README.md`` through the real ``engine.copier.materialize``
    trips a SEPARATE, pre-existing manifest-boundary check
    (``engine/copier.py::_check_manifest_boundary``) that independently
    denies against ``manifest.never_write`` with no exempt concept of its
    own -- a real but unrelated gap outside this story's scope (only
    reachable once whole-file content actually ships for a never-write-glob
    -matched path, which it does not today). This test's own regression
    target is ``check_preconditions``'s rung 4, reached and cleared before
    ``commit`` ever runs, so bypassing ``materialize()`` here changes
    nothing about what is actually proved."""
    skip = tuple(entry.path for entry in real_manifest.entries if entry.id != "dreams-readme")

    def commit(action: Action) -> None:
        target = clean_repo / action.target_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# Dreams\n\nTier-0 contract.\n", encoding="utf-8")

    result = run_adopt(
        clean_repo,
        real_manifest,
        apply=True,
        yes=True,
        confirm=_unreachable_confirm,
        skip=skip,
        commit=commit,
    )

    assert result.applied == ("dreams-readme",)
    assert (clean_repo / "docs" / "dreams" / "README.md").read_text(encoding="utf-8") == (
        "# Dreams\n\nTier-0 contract.\n"
    )
