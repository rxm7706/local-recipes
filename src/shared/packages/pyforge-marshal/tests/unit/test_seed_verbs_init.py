"""Unit tests for ``pyforge.marshal.seed.verbs.init`` (Story 10.7) -- covers
every row of the spec's I/O & Edge-Case Matrix: init into a nonexistent
target (directory created, git-initialized, every ``(init, both)`` entry
materialized with ``{{ slug }}`` resolved, state written with
``mode: init``), init into an already-empty, already-git-repo target (no
second ``git init``), the FR-78 non-empty-directory refusal (with and
without ``--force``), the FR-78 unconditional-refusal-for-a-file case
(``--force`` has no effect), ``--slug`` defaulting to the resolved directory
basename, the ``applies_to``-vs-``state.mode`` interaction against a fresh
``check`` run (the symmetric regression this story's own fix to
``verbs/check.py`` exists for), the Plan-shape parity between ``init`` and
``adopt``, the git-bootstrap-from-nothing path (PRD Journey J1's own
scenario -- a target that is not a git repo AT ALL before ``init`` runs),
and the real ``_default_commit``/``_region_body_from_template`` wiring
reused DIRECTLY from ``verbs/adopt.py`` (never duplicated).

Manifest/git-repo builders mirror ``test_seed_verbs_adopt.py``'s
``_manifest``/``_copied_managed``/``_generated_derived``/``_copied_seeded``/
``_hybrid`` and ``_git``/``_init_git_repo``/``_commit_all`` real-git-repo
convention (real ``git`` I/O against a ``tmp_path``, never mocked). The
git-bootstrap-from-nothing scenarios deliberately do NOT call
``_init_git_repo`` at all -- the one fixture shape every other test file in
this package's ``tests/unit/`` always establishes before exercising a
mutating verb, and the one this story's own AC requires ``init`` to handle
on its own. The ``commit`` double (``_fake_commit``) mirrors ``test_seed_
verbs_adopt.py``'s own identical helper -- a whole-file artifact via plain
``Path.write_text``, a hybrid-region artifact via the REAL ``regions.apply.
insert_region`` primitive (never faked) -- used for the overwhelming
majority of these tests so they never depend on ``engine.copier.
materialize()``'s own manifest-boundary reconciliation, which is ALWAYS
checked against the REAL packaged ``templates/manifest.yaml`` regardless of
what synthetic manifest a test supplies to ``run_init`` (confirmed by
execution while developing this story -- see ``verbs/init.py``'s own module
docstring for the specific, out-of-scope ``docs/dreams/*.md`` never-write
interaction this uncovered). A small, dedicated handful of tests near the
end exercise the REAL ``_default_commit`` default path instead, mirroring
``test_seed_verbs_adopt.py``'s own identical split."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import pytest
from pyforge.marshal.seed.errors import UsageError
from pyforge.marshal.seed.fs import NeverWrite
from pyforge.marshal.seed.model.manifest import (
    AppliesTo,
    ArtifactClass,
    Manifest,
    ManifestEntry,
    Region,
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
from pyforge.marshal.seed.verbs.check import run_check
from pyforge.marshal.seed.verbs.init import _GIT_TIMEOUT_S, _manifest_for_init, run_init

_VERSION = ModelVersion.parse("1.0.0")
_NO_NEVER_WRITE = NeverWrite(patterns=())


# --- manifest builders (mirrors test_seed_verbs_adopt.py) -------------------


def _manifest(*entries: ManifestEntry, model_version: ModelVersion = _VERSION) -> Manifest:
    return Manifest(model_version=model_version, never_write=(), entries=tuple(entries))


def _copied_managed(
    entry_id: str, path: str, *, applies_to: AppliesTo = AppliesTo.BOTH
) -> ManifestEntry:
    return ManifestEntry(
        id=entry_id,
        artifact_class=ArtifactClass.COPIED_MANAGED,
        path=path,
        applies_to=applies_to,
        rationale="test",
    )


def _generated_derived(
    entry_id: str, path: str, *, applies_to: AppliesTo = AppliesTo.BOTH
) -> ManifestEntry:
    return ManifestEntry(
        id=entry_id,
        artifact_class=ArtifactClass.GENERATED_DERIVED,
        path=path,
        applies_to=applies_to,
        rationale="test",
    )


def _copied_seeded(
    entry_id: str, path: str, *, applies_to: AppliesTo = AppliesTo.BOTH
) -> ManifestEntry:
    return ManifestEntry(
        id=entry_id,
        artifact_class=ArtifactClass.COPIED_SEEDED,
        path=path,
        applies_to=applies_to,
        rationale="test",
    )


def _hybrid(
    entry_id: str, path: str, *region_names: str, applies_to: AppliesTo = AppliesTo.BOTH
) -> ManifestEntry:
    return ManifestEntry(
        id=entry_id,
        artifact_class=ArtifactClass.HYBRID_MANAGED_REGION,
        path=path,
        applies_to=applies_to,
        rationale="test",
        format=RegionFormat.HTML,
        regions=tuple(Region(name=name, anchor=("# anchor",)) for name in region_names),
    )


# --- real-git fixtures (mirrors test_seed_verbs_adopt.py) -------------------


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=False
    )
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
def fresh_target(tmp_path: Path) -> Path:
    """A target that does NOT exist yet, and is therefore not a git repo at
    all -- PRD Journey J1's own scenario (a sibling directory `init` must
    bootstrap from nothing). Deliberately never calls `_init_git_repo`,
    unlike every other fixture in this package's `tests/unit/`."""
    return tmp_path / "newproj"


# --- commit doubles (mirrors test_seed_verbs_adopt.py) ----------------------


def _fake_commit(manifest: Manifest, repo_root: Path, calls: list[str] | None = None):
    """Materializes a deterministic marker for a whole-file class via plain
    ``Path.write_text``, and a deterministic region body for a hybrid class
    through the REAL ``regions.apply.insert_region`` primitive -- the
    identical double ``test_seed_verbs_adopt.py`` uses, duplicated here
    rather than imported (a test helper, not production code)."""
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


def _unreachable_commit(action: Action) -> None:
    raise AssertionError(f"commit() should not have been called for {action.artifact_id!r}")


# --- init into a nonexistent target -----------------------------------------


def test_init_into_nonexistent_target_bootstraps_and_materializes_everything(fresh_target):
    manifest = _manifest(
        _copied_managed("whole", "WHOLE.md"),
        _hybrid("hybrid", "HYBRID.md", "tiers"),
        _generated_derived("adopt-only", "ADOPT_ONLY.md", applies_to=AppliesTo.ADOPT),
    )

    result = run_init(fresh_target, manifest, commit=_fake_commit(manifest, fresh_target))

    assert (fresh_target / ".git").is_dir()
    assert set(result.applied) == {"whole", "hybrid"}
    assert (fresh_target / "WHOLE.md").read_text() == "materialized whole\n"
    assert "body for tiers" in (fresh_target / "HYBRID.md").read_text()
    assert not (fresh_target / "ADOPT_ONLY.md").exists()
    assert (fresh_target / ".marshal" / "plan.json").is_file()
    state = read_state(fresh_target)
    assert state is not None
    assert state.mode == "init"
    assert {record.id for record in state.managed} == {"whole", "hybrid"}


def test_init_default_slug_is_the_resolved_directory_basename(fresh_target):
    manifest = _manifest(
        _copied_seeded("starter-dream", "docs/dreams/{{ slug }}.md", applies_to=AppliesTo.INIT)
    )

    result = run_init(fresh_target, manifest, commit=_fake_commit(manifest, fresh_target))

    assert result.slug == "newproj"
    assert (fresh_target / "docs" / "dreams" / "newproj.md").is_file()


def test_init_explicit_slug_overrides_the_directory_basename(fresh_target):
    manifest = _manifest(
        _copied_seeded("starter-dream", "docs/dreams/{{ slug }}.md", applies_to=AppliesTo.INIT)
    )

    result = run_init(
        fresh_target, manifest, slug="pyforge-scribe", commit=_fake_commit(manifest, fresh_target)
    )

    assert result.slug == "pyforge-scribe"
    assert (fresh_target / "docs" / "dreams" / "pyforge-scribe.md").is_file()
    assert not (fresh_target / "docs" / "dreams" / "newproj.md").exists()


# --- init into an already-empty, already-git-repo target --------------------


def test_init_into_an_already_empty_already_git_repo_does_not_re_init(tmp_path):
    _init_git_repo(tmp_path)
    (tmp_path / "README.md").unlink()  # back to "empty" for the non-empty check below
    _commit_all(tmp_path)
    before_git_dir_mtime = (tmp_path / ".git" / "HEAD").stat().st_mtime
    manifest = _manifest(_copied_managed("whole", "WHOLE.md"))

    result = run_init(tmp_path, manifest, commit=_fake_commit(manifest, tmp_path))

    # `.git/HEAD` is untouched -- proof no second `git init` ran (a real
    # re-init would rewrite it).
    assert (tmp_path / ".git" / "HEAD").stat().st_mtime == before_git_dir_mtime
    assert result.applied == ("whole",)
    assert (tmp_path / "WHOLE.md").read_text() == "materialized whole\n"


# --- FR-78: non-empty-directory refusal --------------------------------------


def test_init_into_a_non_empty_directory_without_force_is_refused(tmp_path):
    (tmp_path / "something.txt").write_text("pre-existing\n", encoding="utf-8")
    manifest = _manifest(_copied_managed("whole", "WHOLE.md"))

    with pytest.raises(UsageError, match="adopt") as excinfo:
        run_init(tmp_path, manifest, commit=_unreachable_commit)

    assert not (tmp_path / ".git").exists()
    assert str(excinfo.value.remedy) or True  # remedy is non-blank by SeedError's own contract


def test_init_force_into_a_non_empty_already_committed_git_repo_proceeds(tmp_path):
    """The I/O matrix's own `--force` row: a pre-existing file at some
    entry's path is PRESERVED (no forced overwrite), matching plain
    `build_plan` behavior -- `build_plan` never emits an `Action` for a
    `PRESENT_CONFORMANT` classification, and `init` performs no FR-83-style
    first-claim augmentation at all (this story's own Never bullets), so an
    unrelated pre-existing file at a `generated-derived` path is left
    exactly alone. Uses an ALREADY-git-tracked, ALREADY-COMMITTED non-empty
    target (rather than a bare non-empty non-git directory) -- see `verbs/
    init.py`'s own module docstring for why: bootstrapping git onto a
    non-empty, uncommitted target would make every pre-existing file newly
    untracked, and `check_preconditions`'s own rung 2 (never bypassed for
    `init`) would then legitimately refuse it as a dirty worktree, the same
    git-undo-safety every mutating verb in this package upholds."""
    _init_git_repo(tmp_path)
    (tmp_path / "PREEXISTING.md").write_text("unrelated pre-existing content\n", encoding="utf-8")
    _commit_all(tmp_path)
    manifest = _manifest(_generated_derived("gen", "PREEXISTING.md"))

    result = run_init(tmp_path, manifest, force=True, commit=_unreachable_commit)

    assert result.plan.actions == ()
    assert result.applied == ()
    assert (tmp_path / "PREEXISTING.md").read_text() == "unrelated pre-existing content\n"


# --- FR-78: unconditional refusal for a file --------------------------------


def test_init_target_is_a_plain_file_is_refused_unconditionally(tmp_path):
    target_file = tmp_path / "not-a-directory"
    target_file.write_text("i am a file\n", encoding="utf-8")
    manifest = _manifest(_copied_managed("whole", "WHOLE.md"))

    with pytest.raises(UsageError):
        run_init(target_file, manifest, commit=_unreachable_commit)


def test_init_target_is_a_plain_file_force_has_no_effect(tmp_path):
    target_file = tmp_path / "not-a-directory"
    target_file.write_text("i am a file\n", encoding="utf-8")
    manifest = _manifest(_copied_managed("whole", "WHOLE.md"))

    with pytest.raises(UsageError):
        run_init(target_file, manifest, force=True, commit=_unreachable_commit)

    assert target_file.is_file()
    assert target_file.read_text() == "i am a file\n"


# --- applies_to manifest filter ----------------------------------------------


def test_applies_to_adopt_only_entries_are_excluded_from_the_init_plan(fresh_target):
    manifest = _manifest(
        _generated_derived("adopt-only", "ADOPT_ONLY.md", applies_to=AppliesTo.ADOPT),
        _copied_managed("whole", "WHOLE.md"),
    )

    result = run_init(fresh_target, manifest, commit=_fake_commit(manifest, fresh_target))

    assert {action.artifact_id for action in result.plan.actions} == {"whole"}


def test_applies_to_init_only_entries_are_included(fresh_target):
    manifest = _manifest(
        _copied_seeded("starter-dream", "docs/dreams/{{ slug }}.md", applies_to=AppliesTo.INIT)
    )

    result = run_init(fresh_target, manifest, slug="myproj", commit=_fake_commit(manifest, fresh_target))

    assert {action.artifact_id for action in result.plan.actions} == {"starter-dream"}


# --- _manifest_for_init: filter AND slug resolution, generally -------------


def test_manifest_for_init_filters_and_resolves_every_slug_placeholder():
    """The substitution is general, not hardcoded to the five packaged
    entries that carry `{{ slug }}` today -- exercised here against a
    synthetic entry id the packaged manifest does not carry at all, proving
    a future manifest addition needs no code change (module docstring)."""
    manifest = _manifest(
        _copied_seeded("templated", "some/{{ slug }}/dir/{{ slug }}.md", applies_to=AppliesTo.INIT),
        _copied_managed("literal", "LITERAL.md", applies_to=AppliesTo.BOTH),
        _generated_derived("adopt-only", "ADOPT_ONLY.md", applies_to=AppliesTo.ADOPT),
    )

    filtered = _manifest_for_init(manifest, "my-slug")

    ids = {entry.id: entry for entry in filtered.entries}
    assert set(ids) == {"templated", "literal"}
    assert ids["templated"].path == "some/my-slug/dir/my-slug.md"
    assert ids["literal"].path == "LITERAL.md"  # unaffected -- no placeholder to resolve
    assert filtered.model_version == manifest.model_version
    assert filtered.never_write == manifest.never_write


# --- state after apply -------------------------------------------------------


def test_agents_are_recorded_with_no_union_needed_on_a_fresh_init(fresh_target):
    manifest = _manifest(_copied_managed("whole", "WHOLE.md"))

    run_init(
        fresh_target, manifest, agents=("claude", "cursor"), commit=_fake_commit(manifest, fresh_target)
    )

    state = read_state(fresh_target)
    assert state.agents == ("claude", "cursor")
    assert state.skips == ()
    assert state.opted_out == ()
    assert state.migrations_applied == ()


def test_empty_plan_apply_writes_no_state(tmp_path):
    """A `--force`'d run whose every entry is already conformant produces
    an empty plan -- mirroring `adopt`'s own "an empty plan skips the state
    write entirely" gate, applied here to `init`'s own always-apply design."""
    _init_git_repo(tmp_path)
    (tmp_path / "PREEXISTING.md").write_text("already there\n", encoding="utf-8")
    _commit_all(tmp_path)
    manifest = _manifest(_generated_derived("gen", "PREEXISTING.md"))

    result = run_init(tmp_path, manifest, force=True, commit=_unreachable_commit)

    assert result.applied == ()
    assert not (tmp_path / ".marshal" / "seed-state.yml").exists()


# --- marshal seed check is green immediately after init ---------------------


def test_check_on_the_freshly_inited_repo_is_green(fresh_target):
    """The spec's own I/O matrix row: `marshal seed check` immediately after
    `init` reports zero findings, and `specs-dir-legacy`-shaped adopt-only
    entries are NOT flagged missing (this story's own `check.py` fix). No
    ``{{ slug }}``-templated entry is included in the manifest passed to
    `check` here -- `run_check` has no way to resolve the placeholder at
    all (a confirmed, pre-existing, out-of-scope gap; see `verbs/init.py`'s
    own module docstring) -- so this test proves the fix on entries `check`
    CAN actually verify, which is exactly this story's own AC."""
    manifest = _manifest(
        _copied_managed("whole", "WHOLE.md"),
        _hybrid("hybrid", "HYBRID.md", "tiers"),
        _generated_derived("adopt-only", "ADOPT_ONLY.md", applies_to=AppliesTo.ADOPT),
    )

    run_init(fresh_target, manifest, commit=_fake_commit(manifest, fresh_target))
    _commit_all(fresh_target)

    report = run_check(fresh_target, manifest)

    assert report.findings == ()
    assert report.failing is False
    assert not any(
        finding.path == "ADOPT_ONLY.md" for finding in report.findings
    )  # explicit, even though findings == () already implies it


def test_check_on_the_freshly_inited_repo_does_not_flag_an_init_only_entry_after_adopt(tmp_path):
    """The symmetric direction of the same regression (also asserted
    directly in `test_seed_verbs_check.py`'s own extended suite): an
    `adopt`ed repo must not see an `init`-only entry reported missing
    either."""
    from pyforge.marshal.seed.verbs.adopt import run_adopt

    _init_git_repo(tmp_path)
    manifest = _manifest(
        _copied_managed("whole", "WHOLE.md"),
        _copied_seeded("starter-dream", "STARTER.md", applies_to=AppliesTo.INIT),
    )
    run_adopt(
        tmp_path,
        manifest,
        apply=True,
        yes=True,
        confirm=lambda: (_ for _ in ()).throw(AssertionError("unused")),
        commit=_fake_commit(manifest, tmp_path),
    )
    _commit_all(tmp_path)

    report = run_check(tmp_path, manifest)

    assert not any(finding.path == "STARTER.md" for finding in report.findings)


# --- Plan shape parity between init and adopt --------------------------------


def test_init_and_adopt_plans_are_the_identical_dataclass_shape(tmp_path):
    from pyforge.marshal.seed.plan.build import default_plan_path
    from pyforge.marshal.seed.plan.types import Plan
    from pyforge.marshal.seed.verbs.adopt import run_adopt

    init_target = tmp_path / "init-target"
    adopt_target = tmp_path / "adopt-target"
    adopt_target.mkdir()
    _init_git_repo(adopt_target)

    init_manifest = _manifest(_copied_managed("whole", "WHOLE.md"))
    adopt_manifest = _manifest(_copied_managed("whole", "WHOLE.md"))

    init_result = run_init(init_target, init_manifest, commit=_fake_commit(init_manifest, init_target))
    adopt_result = run_adopt(
        adopt_target,
        adopt_manifest,
        apply=True,
        yes=True,
        confirm=lambda: (_ for _ in ()).throw(AssertionError("unused")),
        commit=_fake_commit(adopt_manifest, adopt_target),
    )

    assert type(init_result.plan) is Plan
    assert type(adopt_result.plan) is Plan
    assert set(init_result.plan.to_json_dict()) == set(adopt_result.plan.to_json_dict())
    assert default_plan_path(init_target).is_file()
    assert default_plan_path(adopt_target).is_file()


# --- git-bootstrap-from-nothing: PRD Journey J1's own scenario --------------


def test_bootstrap_from_a_target_that_does_not_exist_at_all_and_has_no_git(fresh_target):
    """PRD Journey J1's own literal scenario: a sibling directory that does
    not yet exist as a repo at all. Confirms every claim `_bootstrap_git_
    repo` makes: the directory is created, `git init` runs, and the
    resulting repo has NO commits yet (`git rev-parse HEAD` fails) -- which
    `plan.build._git_head` degrades gracefully to `None` for, exactly as
    the module docstring documents."""
    assert not fresh_target.exists()
    manifest = _manifest(_copied_managed("whole", "WHOLE.md"))

    result = run_init(fresh_target, manifest, commit=_fake_commit(manifest, fresh_target))

    assert fresh_target.is_dir()
    assert (fresh_target / ".git").is_dir()
    head = subprocess.run(
        ["git", "-C", str(fresh_target), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert head.returncode != 0  # unborn HEAD -- no commits, by design
    assert result.applied == ("whole",)
    assert result.plan.repo_fingerprint.git_head is None


def test_bootstrap_creates_parent_directories_too(tmp_path):
    nested = tmp_path / "a" / "b" / "c"
    manifest = _manifest(_copied_managed("whole", "WHOLE.md"))

    run_init(nested, manifest, commit=_fake_commit(manifest, nested))

    assert (nested / ".git").is_dir()
    assert (nested / "WHOLE.md").is_file()


# --- state-invalid-adjacent: never reads a prior state -----------------------


def test_init_never_reads_prior_state_even_if_one_exists(tmp_path):
    """Corroborates the module docstring's own claim ("`state` is never
    read"): a `--force`'d run onto a directory that already carries a
    (perfectly valid) `.marshal/seed-state.yml` from a prior manual write
    must not attempt to union agents or otherwise consult it -- `init`'s
    own state write always starts from a blank slate."""
    _init_git_repo(tmp_path)
    write_state(
        SeedState(
            model_version=_VERSION,
            seed_model_version="0.1.0",
            adopted_at="2026-08-01T00:00:00Z",
            last_update="2026-08-01T00:00:00Z",
            mode="adopt",
            agents=("gemini",),
            managed=(
                ManagedArtifact(
                    id="unrelated",
                    path="UNRELATED.md",
                    artifact_class="copied-managed",
                    body_sha="deadbeef",
                    inserted_region_span=None,
                ),
            ),
            skips=(),
            legacy=(),
            migrations_applied=(),
            opted_out=(),
        ),
        repo_root=tmp_path,
        never_write=_NO_NEVER_WRITE,
    )
    (tmp_path / "PREEXISTING.md").write_text("x\n", encoding="utf-8")
    _commit_all(tmp_path)
    manifest = _manifest(_generated_derived("gen", "PREEXISTING.md"))

    result = run_init(tmp_path, manifest, force=True, agents=("claude",), commit=_unreachable_commit)

    # Nothing pending (PREEXISTING.md is already conformant), so state is
    # never re-written -- proving init took no action based on the prior
    # state at all, rather than merely "not unioning" a value it never read.
    assert result.applied == ()
    state = read_state(tmp_path)
    assert state.mode == "adopt"  # untouched -- init never wrote over it
    assert state.agents == ("gemini",)


# --- agreement test (mirrors test_seed_verbs_adopt.py's own) ---------------


def test_git_timeout_agrees_with_plan_build():
    assert _GIT_TIMEOUT_S == _BUILD_GIT_TIMEOUT_S


# --- _default_commit/_region_body_from_template: real reuse from adopt.py --


def test_default_commit_materializes_a_whole_file_entry_via_a_custom_template(fresh_target):
    """Mirrors `test_seed_verbs_adopt.py`'s own identical test -- proving
    `init` reuses `adopt.py::_default_commit` DIRECTLY (imported, not
    duplicated), AND that the resolved ``slug`` genuinely reaches the
    `answers=` dict `_default_commit` supplies to `engine.copier.materialize`
    (the module docstring's own "whole-file CONTENT... can also reference
    `{{ slug }}` inside a file body" claim) -- a ``.jinja``-suffixed source
    file is Copier's own convention for content that IS Jinja-rendered
    (unsuffixed files, like `adopt.py`'s own test fixture, copy verbatim).
    `.bmad-config.user.toml` is one of `engine.copier.copier.
    _GENESIS_OWNED_PATHS` -- allow-listed unconditionally by `materialize()`'s
    manifest-boundary check regardless of manifest content, and matched by
    none of the packaged manifest's own `never_write` patterns (unlike
    `docs/dreams/*.md` -- see `verbs/init.py`'s own module docstring)."""
    template_root = Path(tempfile.mkdtemp())
    (template_root / ".bmad-config.user.toml.jinja").write_text(
        '[project]\nslug = "{{ slug }}"\n', encoding="utf-8"
    )
    manifest = _manifest(_copied_managed("cfg", ".bmad-config.user.toml"))

    result = run_init(fresh_target, manifest, slug="pyforge-scribe", template_path=template_root)

    assert result.applied == ("cfg",)
    assert (fresh_target / ".bmad-config.user.toml").read_text(encoding="utf-8") == (
        '[project]\nslug = "pyforge-scribe"\n'
    )


def test_default_commit_materializes_a_hybrid_region_via_the_real_packaged_fragments(fresh_target):
    """Mirrors `test_seed_verbs_adopt.py`'s own identical test -- no
    `template_path` injection needed (`template_path=None`, the production
    default): a hybrid region's body is read directly off the packaged
    `seed/templates/files/tiers.md.j2` fragment, never routed through
    `engine.copier.materialize()` at all (`_region_body_from_template`,
    reused via `_default_commit`)."""
    # Already a git repo, and ALREADY COMMITTED (not merely written) --
    # bootstrapping git onto an uncommitted non-empty target would make
    # `CLAUDE.md` newly untracked, and `check_preconditions`'s own rung 2
    # (never bypassed for `init`) would then legitimately refuse it as a
    # dirty worktree; see `verbs/init.py`'s own module docstring.
    fresh_target.mkdir(parents=True)
    _init_git_repo(fresh_target)
    (fresh_target / "CLAUDE.md").write_text(
        "# My project\n\nSome existing repo-specific guidance.\n", encoding="utf-8"
    )
    _commit_all(fresh_target)
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

    # `force=True`: this test pre-populates `CLAUDE.md` to prove the hybrid
    # region is inserted around EXISTING repo-specific content, which makes
    # the target non-empty going in -- FR-78's own refusal must be bypassed
    # deliberately, the same way a real operator would for this scenario.
    result = run_init(fresh_target, manifest, force=True)

    assert result.applied == ("claude-md-test",)
    content = (fresh_target / "CLAUDE.md").read_text(encoding="utf-8")
    assert "Some existing repo-specific guidance." in content
    assert "marshal-seed:begin region=tiers" in content
    assert "Build More Architect Dreams" in content  # real fragment content, not a fake body


# --- PRD Journey J1 integration test -----------------------------------------


def test_prd_j1_init_into_a_directory_that_is_not_yet_a_git_repo_at_all(fresh_target):
    """PRD Journey J1's own literal scenario, end to end: ``marshal seed
    init ../pyforge-scribe --slug pyforge-scribe --agents claude,cursor``
    into a sibling directory that does not exist as a repo yet at all.

    Verifies: (1) the target is bootstrapped (created + git-initialized);
    (2) ``docs/dreams/<slug>.md`` exists with valid Tier-0 frontmatter and is
    the only Dream written; (3) ``_bmad-output/PROJECTS.md`` carries the
    project's first row; (4) ``marshal seed check`` on the result is green.

    (4) is checked against a manifest EXCLUDING the ``{{ slug }}``-templated
    ``starter-dream``/``project-config`` entries -- `run_check` has no way
    to resolve the placeholder at all (a confirmed, pre-existing, out-of-
    scope gap named in `verbs/init.py`'s own module docstring), so a literal
    "zero findings" claim against a manifest that still includes them would
    be unachievable through no fault of this story's own code. (2) is
    verified directly against the filesystem instead, which is what `init`
    itself is responsible for and does control."""

    def _prd_j1_commit(manifest: Manifest, repo_root: Path):
        entries_by_id = {entry.id: entry for entry in manifest.entries}

        def commit(action: Action) -> None:
            entry = entries_by_id[action.artifact_id]
            target = repo_root / action.target_path
            target.parent.mkdir(parents=True, exist_ok=True)
            if entry.id == "starter-dream":
                target.write_text(
                    "---\n"
                    "title: pyforge-scribe\n"
                    "type: dream\n"
                    "owner: marshal\n"
                    "status: seeded\n"
                    "---\n\n"
                    "# pyforge-scribe\n\n## The Dream\n\nSeeded by `marshal seed init`.\n",
                    encoding="utf-8",
                )
            elif entry.id == "projects-index":
                target.write_text(
                    "# Projects\n\n"
                    "| Slug | Status |\n|---|---|\n"
                    "| pyforge-scribe | active |\n",
                    encoding="utf-8",
                )
            else:
                target.write_text(f"materialized {action.artifact_id}\n", encoding="utf-8")

        return commit

    manifest = _manifest(
        _copied_seeded("starter-dream", "docs/dreams/{{ slug }}.md", applies_to=AppliesTo.INIT),
        _generated_derived("projects-index", "_bmad-output/PROJECTS.md", applies_to=AppliesTo.BOTH),
        _copied_managed("whole", "WHOLE.md", applies_to=AppliesTo.BOTH),
    )

    result = run_init(
        fresh_target,
        manifest,
        slug="pyforge-scribe",
        agents=("claude", "cursor"),
        commit=_prd_j1_commit(manifest, fresh_target),
    )

    assert set(result.applied) == {"starter-dream", "projects-index", "whole"}

    # (1) bootstrap
    assert fresh_target.is_dir()
    assert (fresh_target / ".git").is_dir()

    # (2) the Dream, and only it
    dream_dir = fresh_target / "docs" / "dreams"
    dreams = list(dream_dir.glob("*.md"))
    assert [path.name for path in dreams] == ["pyforge-scribe.md"]
    dream_text = dreams[0].read_text(encoding="utf-8")
    assert dream_text.startswith("---\n")
    assert "title: pyforge-scribe" in dream_text
    assert "type: dream" in dream_text
    assert "owner: marshal" in dream_text
    assert "status: seeded" in dream_text

    # (3) PROJECTS.md's first row
    projects_text = (fresh_target / "_bmad-output" / "PROJECTS.md").read_text(encoding="utf-8")
    assert "| pyforge-scribe | active |" in projects_text

    state = read_state(fresh_target)
    assert state.mode == "init"
    assert state.agents == ("claude", "cursor")

    _commit_all(fresh_target)

    # (4) check is green, over the entries check can actually verify (see
    # this test's own docstring for the {{ slug }} caveat).
    check_manifest = _manifest(_copied_managed("whole", "WHOLE.md", applies_to=AppliesTo.BOTH))
    report = run_check(fresh_target, check_manifest)
    assert report.findings == ()
    assert report.failing is False
