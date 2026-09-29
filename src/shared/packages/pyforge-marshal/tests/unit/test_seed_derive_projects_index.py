"""Unit tests for ``pyforge.marshal.seed.derive.projects_index`` (Story
11.2) -- covers the spec's (amended) I/O & Edge-Case Matrix:
``derive_projects_table``'s N-projects rendering, prose preservation
(proven through the real ``regions.apply.insert_region`` mechanism on a
synthetic fixture), the zero-projects edge case, deterministic
slug-ordering, and per-column ``|``/newline escaping; ``ensure_symlinks``'s
symlinks-absent creation, idempotent re-run, empty-``active_slug``
rejection, and missing-target-directory rejection;
``resolve_active_project``'s precedence, whitespace-as-absent handling, and
malformed/empty-value rejection; ``detect_symlink_desync``'s all-agree
no-op, all-three-named-values HARD finding, the absolute-path-target
non-false-positive, and the unrecognized-target-shape non-false-negative;
and the never-write refusal (a deliberately malicious ``fs.symlink`` call
into the protected ``planning-artifacts`` tree).

**All tests operate on synthetic ``tmp_path``-rooted fixture repos --
never on this actual worktree's real ``_bmad-output/{planning,
implementation}-artifacts`` paths or ``_bmad/custom/.active-project``
marker**, matching every sibling ``test_seed_*.py`` file's own established
convention (see this story's own CRITICAL SAFETY CONSTRAINT)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pyforge.marshal.seed import fs
from pyforge.marshal.seed.derive import projects_index
from pyforge.marshal.seed.errors import NeverWriteViolation, PreconditionFailure
from pyforge.marshal.seed.model.version import ModelVersion
from pyforge.marshal.seed.regions.apply import InsertionOutcome, insert_region
from pyforge.marshal.seed.regions.markers import RegionFormat

_VERSION = ModelVersion.parse("1.0.0")
_NO_NEVER_WRITE = fs.NeverWrite(patterns=())


def _write_bmad_config(path: Path, *, slug: str, status: str = "active", description: str = "A project.") -> None:
    """A synthetic ``.bmad-config.toml`` fixture matching
    ``_bmad-output/PROJECTS.md``'s own "Adding a new project" convention.
    Values are written via ``json.dumps`` (not raw f-string interpolation)
    so a fixture value containing a literal ``"``/``|``/newline still
    round-trips through ``tomllib`` as a valid TOML basic string -- needed
    for the escaping tests below, which deliberately feed exactly those
    characters."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f'output_folder = "_bmad-output/projects/{path.parent.name}"\n\n'
        "[project]\n"
        f"slug = {json.dumps(slug)}\n"
        f"description = {json.dumps(description)}\n"
        f"status = {json.dumps(status)}\n",
        encoding="utf-8",
    )


def _make_artifact_symlink(repo_root: Path, name: str, slug: str) -> None:
    link_path = repo_root / "_bmad-output" / name
    link_path.parent.mkdir(parents=True, exist_ok=True)
    link_path.symlink_to(Path("projects") / slug / name)


def _make_project_dirs(repo_root: Path, slug: str) -> None:
    for name in ("planning-artifacts", "implementation-artifacts"):
        (repo_root / "_bmad-output" / "projects" / slug / name).mkdir(parents=True)


# --- derive_projects_table: N-projects rendering, I/O matrix row 1 ---------


def test_derive_projects_table_renders_one_row_per_project(tmp_path):
    projects_dir = tmp_path / "projects"
    _write_bmad_config(
        projects_dir / "pyforge-atlas" / ".bmad-config.toml",
        slug="pyforge-atlas",
        status="active",
        description="Atlas project.",
    )
    _write_bmad_config(
        projects_dir / "pyforge-marshal" / ".bmad-config.toml",
        slug="pyforge-marshal",
        status="active",
        description="Marshal project.",
    )
    _write_bmad_config(
        projects_dir / "pyforge-doctor" / ".bmad-config.toml",
        slug="pyforge-doctor",
        status="active",
        description="Doctor project.",
    )

    table = projects_index.derive_projects_table(projects_dir)

    lines = table.splitlines()
    data_rows = lines[2:]
    assert len(data_rows) == 3
    assert "pyforge-atlas" in table
    assert "Atlas project." in table
    assert "pyforge-marshal" in table
    assert "Marshal project." in table
    assert "pyforge-doctor" in table
    assert "Doctor project." in table


def test_derive_projects_table_skips_a_project_directory_with_no_config_file(tmp_path):
    projects_dir = tmp_path / "projects"
    (projects_dir / "no-config-here").mkdir(parents=True)
    _write_bmad_config(
        projects_dir / "has-config" / ".bmad-config.toml",
        slug="has-config",
        status="active",
        description="Real project.",
    )

    table = projects_index.derive_projects_table(projects_dir)

    assert "has-config" in table
    assert "no-config-here" not in table


def test_derive_projects_table_sorts_deterministically_by_slug(tmp_path):
    """Sorted by the RESOLVED slug value, not by directory-iteration order
    -- the two fixture directories below are named to sort the OPPOSITE way
    their `[project].slug` fields do, so this would fail if sorting keyed
    on the directory name instead."""
    projects_dir = tmp_path / "projects"
    _write_bmad_config(
        projects_dir / "zzz-dir" / ".bmad-config.toml",
        slug="alpha-project",
        status="active",
        description="A.",
    )
    _write_bmad_config(
        projects_dir / "aaa-dir" / ".bmad-config.toml",
        slug="zeta-project",
        status="active",
        description="Z.",
    )

    table = projects_index.derive_projects_table(projects_dir)

    assert table.index("alpha-project") < table.index("zeta-project")


# --- derive_projects_table: zero-projects edge case, I/O matrix row 7 -----


def test_derive_projects_table_with_a_missing_projects_dir_is_header_only(tmp_path):
    table = projects_index.derive_projects_table(tmp_path / "does-not-exist")

    lines = table.splitlines()
    assert lines[0].startswith("| Slug")
    assert len(lines) == 2  # header + separator, zero data rows -- no crash


def test_derive_projects_table_with_an_empty_projects_dir_is_header_only(tmp_path):
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()

    table = projects_index.derive_projects_table(projects_dir)

    assert len(table.splitlines()) == 2


# --- derive_projects_table: per-column escaping (amended Tasks) -----------


def test_derive_projects_table_escapes_pipes_and_newlines_in_every_column(tmp_path):
    """Task (a)'s own requirement: EVERY column -- slug, status, AND
    description, not description alone -- must be escaped against both
    `|` and any newline/carriage-return character."""
    projects_dir = tmp_path / "projects"
    _write_bmad_config(
        projects_dir / "weird" / ".bmad-config.toml",
        slug="weird|slug",
        status="acti|ve\nstatus",
        description="line one\r\nline two | pipe",
    )

    table = projects_index.derive_projects_table(projects_dir)
    lines = table.splitlines()

    # A raw, un-escaped newline embedded in any cell would split this one
    # project's row into multiple lines -- header + separator + exactly ONE
    # data row proves every newline/CR was collapsed to a space before
    # rendering, not left to corrupt the table's row structure.
    assert len(lines) == 3
    data_row = lines[2]
    # Exactly 4 real (unescaped) column delimiters remain; every OTHER "|"
    # character in the row is part of an escaped "\|" sequence.
    assert data_row.count("|") - data_row.count("\\|") == 4
    assert "weird\\|slug" in data_row
    assert "acti\\|ve status" in data_row
    assert "line one line two \\| pipe" in data_row


# --- derive_projects_table: pass-2 review findings -------------------------


def test_derive_projects_table_escapes_a_literal_backtick_in_a_slug():
    """Review finding, pass 2: the slug column wraps its value in a
    markdown code span (`` `{slug}` ``); an unescaped backtick would break
    out of it."""
    assert projects_index._escape_cell("weird`slug") == "weird\\`slug"


def test_derive_projects_table_raises_on_two_directories_sharing_the_same_slug(tmp_path):
    projects_dir = tmp_path / "projects"
    _write_bmad_config(
        projects_dir / "dir-one" / ".bmad-config.toml",
        slug="shared-slug",
        status="active",
        description="First.",
    )
    _write_bmad_config(
        projects_dir / "dir-two" / ".bmad-config.toml",
        slug="shared-slug",
        status="active",
        description="Second.",
    )

    with pytest.raises(PreconditionFailure, match="shared-slug"):
        projects_index.derive_projects_table(projects_dir)


def test_derive_projects_table_treats_an_unlistable_projects_dir_as_header_only(tmp_path, monkeypatch):
    """A directory-listing failure (e.g. a permission error) degrades to
    the same header-only table as a missing directory -- never a crash
    (review finding, pass 2)."""
    projects_dir = tmp_path / "projects"
    projects_dir.mkdir()

    def _raise_permission_error(self):
        raise PermissionError("denied")

    monkeypatch.setattr(Path, "iterdir", _raise_permission_error)

    table = projects_index.derive_projects_table(projects_dir)

    assert len(table.splitlines()) == 2


# --- derive_projects_table: prose preservation, I/O matrix row 2 ----------


def test_derived_table_splices_into_hand_written_prose_without_touching_it(tmp_path):
    """The Boundaries' own claim: `PROJECTS.md`'s hand-written prose --
    everything outside the Projects table -- is byte-identical before and
    after a derive run. Proven through the REAL `regions.apply.
    insert_region` mechanism (never a hand-rolled string splice) on a
    synthetic fixture, mirroring `PROJECTS.md`'s own real `## Projects`
    heading."""
    projects_dir = tmp_path / "projects"
    _write_bmad_config(
        projects_dir / "acme" / ".bmad-config.toml",
        slug="acme",
        status="active",
        description="Acme project.",
    )

    target = tmp_path / "PROJECTS.md"
    prose_before = (
        "# BMAD Projects in this Repository\n\n"
        "Some hand-written prose that must survive byte-identical.\n\n"
        "## Projects\n\n"
        "(placeholder -- not yet a managed region)\n"
    )
    target.write_text(prose_before, encoding="utf-8")

    body = projects_index.derive_projects_table(projects_dir)
    result = insert_region(
        prose_before,
        target,
        "projects-table",
        ("## Projects",),
        body,
        model_version=_VERSION,
        fmt=RegionFormat.HTML,
        repo_root=tmp_path,
        never_write=_NO_NEVER_WRITE,
    )

    assert result.outcome == InsertionOutcome.INSERTED
    content = target.read_text(encoding="utf-8")
    assert content.startswith(
        "# BMAD Projects in this Repository\n\n"
        "Some hand-written prose that must survive byte-identical.\n\n"
        "## Projects\n"
    )
    assert "acme" in content
    assert "Acme project." in content


# --- ensure_symlinks: symlinks-absent creation, I/O matrix row 3 ----------


def test_ensure_symlinks_creates_both_when_absent(tmp_path):
    _make_project_dirs(tmp_path, "acme")

    projects_index.ensure_symlinks(tmp_path, "acme", never_write=_NO_NEVER_WRITE)

    planning_link = tmp_path / "_bmad-output" / "planning-artifacts"
    impl_link = tmp_path / "_bmad-output" / "implementation-artifacts"
    assert planning_link.readlink() == Path("projects/acme/planning-artifacts")
    assert impl_link.readlink() == Path("projects/acme/implementation-artifacts")


# --- ensure_symlinks: idempotent re-run, I/O matrix row 4 -----------------


def test_ensure_symlinks_second_call_is_a_true_no_op(tmp_path, monkeypatch):
    _make_project_dirs(tmp_path, "acme")
    projects_index.ensure_symlinks(tmp_path, "acme", never_write=_NO_NEVER_WRITE)

    def boom(*args, **kwargs):
        raise AssertionError("os.replace must not be called on an idempotent re-run")

    monkeypatch.setattr(fs.os, "replace", boom)

    projects_index.ensure_symlinks(tmp_path, "acme", never_write=_NO_NEVER_WRITE)  # no raise


# --- ensure_symlinks: validation gaps (amended Tasks) ---------------------


def test_ensure_symlinks_rejects_an_empty_active_slug(tmp_path):
    with pytest.raises(PreconditionFailure):
        projects_index.ensure_symlinks(tmp_path, "", never_write=_NO_NEVER_WRITE)


def test_ensure_symlinks_rejects_a_whitespace_only_active_slug(tmp_path):
    with pytest.raises(PreconditionFailure):
        projects_index.ensure_symlinks(tmp_path, "   ", never_write=_NO_NEVER_WRITE)


def test_ensure_symlinks_raises_when_the_target_directory_does_not_exist(tmp_path):
    with pytest.raises(PreconditionFailure, match="does not exist"):
        projects_index.ensure_symlinks(tmp_path, "acme", never_write=_NO_NEVER_WRITE)

    # Never a silently-created dangling symlink.
    assert not (tmp_path / "_bmad-output" / "planning-artifacts").exists()


def test_ensure_symlinks_names_which_link_already_changed_on_a_partial_failure(tmp_path, monkeypatch):
    """Review finding, pass 2: if the second `fs.symlink` call fails after
    the first succeeded, the caller must be told which one already
    changed -- never a bare, uncontextualized exception from the second
    call alone. This is a diagnostic only (never auto-repair, this
    module's own Never bullet) -- the first symlink is left as-is."""
    _make_project_dirs(tmp_path, "acme")
    real_symlink = fs.symlink
    calls: list[Path] = []

    def _flaky(link_path, target, **kwargs):
        calls.append(link_path)
        if len(calls) == 2:
            raise RuntimeError("disk full")
        return real_symlink(link_path, target, **kwargs)

    monkeypatch.setattr(projects_index.fs, "symlink", _flaky)

    with pytest.raises(PreconditionFailure, match="planning-artifacts"):
        projects_index.ensure_symlinks(tmp_path, "acme", never_write=_NO_NEVER_WRITE)

    # The first symlink genuinely landed; nothing rolled it back.
    assert (tmp_path / "_bmad-output" / "planning-artifacts").is_symlink()


# --- resolve_active_project: precedence -----------------------------------


def _write_marker(repo_root: Path, value: str) -> None:
    marker = repo_root / "_bmad" / "custom" / ".active-project"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(value, encoding="utf-8")


def test_resolve_active_project_project_param_wins_over_env_and_marker(tmp_path, monkeypatch):
    monkeypatch.setenv("BMAD_ACTIVE_PROJECT", "env-project")
    _write_marker(tmp_path, "marker-project\n")

    assert projects_index.resolve_active_project(tmp_path, project="cli-project") == "cli-project"


def test_resolve_active_project_env_wins_over_marker(tmp_path, monkeypatch):
    monkeypatch.setenv("BMAD_ACTIVE_PROJECT", "env-project")
    _write_marker(tmp_path, "marker-project\n")

    assert projects_index.resolve_active_project(tmp_path) == "env-project"


def test_resolve_active_project_falls_back_to_the_marker_file(tmp_path, monkeypatch):
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    _write_marker(tmp_path, "marker-project\n")

    assert projects_index.resolve_active_project(tmp_path) == "marker-project"


# --- resolve_active_project: whitespace-as-absent (amended Tasks) --------


def test_resolve_active_project_strips_whitespace_from_every_source(tmp_path, monkeypatch):
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)

    assert projects_index.resolve_active_project(tmp_path, project="  padded-project  ") == "padded-project"


def test_resolve_active_project_treats_a_whitespace_only_env_var_as_absent(tmp_path, monkeypatch):
    monkeypatch.setenv("BMAD_ACTIVE_PROJECT", "   ")
    _write_marker(tmp_path, "marker-project\n")

    assert projects_index.resolve_active_project(tmp_path) == "marker-project"


def test_resolve_active_project_treats_a_whitespace_only_marker_as_absent(tmp_path, monkeypatch):
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    _write_marker(tmp_path, "   \n")

    with pytest.raises(PreconditionFailure):
        projects_index.resolve_active_project(tmp_path)


def test_resolve_active_project_treats_a_non_utf8_marker_as_absent_not_a_crash(tmp_path, monkeypatch):
    """Review finding, pass 2: an earlier draft only caught `OSError` on
    the marker read, so a non-UTF-8 marker raised an uncaught
    `UnicodeDecodeError` instead of falling through like a missing one."""
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)
    marker = tmp_path / "_bmad" / "custom" / ".active-project"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_bytes(b"\xff\xfe not valid utf-8")

    with pytest.raises(PreconditionFailure, match="no source"):
        projects_index.resolve_active_project(tmp_path)


# --- resolve_active_project: malformed/empty resolved value --------------


def test_resolve_active_project_raises_when_every_source_is_absent(tmp_path, monkeypatch):
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)

    with pytest.raises(PreconditionFailure, match="no source"):
        projects_index.resolve_active_project(tmp_path)


def test_resolve_active_project_rejects_an_absolute_path_shaped_value(tmp_path, monkeypatch):
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)

    with pytest.raises(PreconditionFailure):
        projects_index.resolve_active_project(tmp_path, project="/etc/passwd")


def test_resolve_active_project_rejects_a_dot_dot_containing_value(tmp_path, monkeypatch):
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)

    with pytest.raises(PreconditionFailure):
        projects_index.resolve_active_project(tmp_path, project="../etc")


def test_resolve_active_project_rejects_an_uppercase_value(tmp_path, monkeypatch):
    monkeypatch.delenv("BMAD_ACTIVE_PROJECT", raising=False)

    with pytest.raises(PreconditionFailure):
        projects_index.resolve_active_project(tmp_path, project="Pyforge-Marshal")


# --- detect_symlink_desync: agreement / disagreement, I/O matrix row 5 ---


def test_detect_symlink_desync_returns_none_when_both_symlinks_agree_with_the_marker(tmp_path):
    _make_artifact_symlink(tmp_path, "planning-artifacts", "acme")
    _make_artifact_symlink(tmp_path, "implementation-artifacts", "acme")

    assert projects_index.detect_symlink_desync(tmp_path, "acme") is None


def test_detect_symlink_desync_names_all_three_disagreeing_values(tmp_path):
    _make_artifact_symlink(tmp_path, "planning-artifacts", "other-project")
    _make_artifact_symlink(tmp_path, "implementation-artifacts", "acme")

    result = projects_index.detect_symlink_desync(tmp_path, "acme")

    assert result == projects_index.SymlinkDesync(
        marker_project="acme",
        planning_artifacts_project="other-project",
        implementation_artifacts_project="acme",
    )


# --- detect_symlink_desync: absolute-path target, amended Tasks ----------


def test_detect_symlink_desync_does_not_false_positive_on_a_legitimate_absolute_path_target(
    tmp_path,
):
    """An absolute-path symlink target that legitimately resolves to the
    correct project must NOT be reported as desync."""
    planning_link = tmp_path / "_bmad-output" / "planning-artifacts"
    planning_link.parent.mkdir(parents=True)
    absolute_target = tmp_path / "_bmad-output" / "projects" / "acme" / "planning-artifacts"
    planning_link.symlink_to(absolute_target)
    _make_artifact_symlink(tmp_path, "implementation-artifacts", "acme")

    assert projects_index.detect_symlink_desync(tmp_path, "acme") is None


# --- detect_symlink_desync: unrecognized target shape, amended Tasks -----


def test_detect_symlink_desync_treats_an_unparseable_target_shape_as_disagreement(tmp_path):
    planning_link = tmp_path / "_bmad-output" / "planning-artifacts"
    planning_link.parent.mkdir(parents=True)
    planning_link.symlink_to(Path("some/other/shape"))
    _make_artifact_symlink(tmp_path, "implementation-artifacts", "acme")

    result = projects_index.detect_symlink_desync(tmp_path, "acme")

    assert result is not None
    assert "unrecognized-target-shape" in result.planning_artifacts_project


def test_detect_symlink_desync_rejects_a_target_whose_final_segment_is_the_wrong_artifact_name(
    tmp_path,
):
    """`projects/<slug>/wrong-name` -- the final segment does not match the
    artifact being checked (`planning-artifacts`) -- must be reported as
    unrecognized, never silently misread as naming a real slug."""
    planning_link = tmp_path / "_bmad-output" / "planning-artifacts"
    planning_link.parent.mkdir(parents=True)
    planning_link.symlink_to(Path("projects/acme/wrong-name"))
    _make_artifact_symlink(tmp_path, "implementation-artifacts", "acme")

    result = projects_index.detect_symlink_desync(tmp_path, "acme")

    assert result is not None
    assert "unrecognized-target-shape" in result.planning_artifacts_project


def test_detect_symlink_desync_treats_an_absent_symlink_as_disagreement(tmp_path):
    _make_artifact_symlink(tmp_path, "implementation-artifacts", "acme")
    # planning-artifacts deliberately never created.

    result = projects_index.detect_symlink_desync(tmp_path, "acme")

    assert result is not None
    assert "absent-or-not-a-symlink" in result.planning_artifacts_project


# --- never-write refusal, I/O matrix row 6 --------------------------------


def test_fs_symlink_refuses_a_malicious_call_into_the_protected_planning_artifacts_tree(tmp_path):
    """The Always bullet's own proof: `**/planning-artifacts/**` (the
    manifest's existing never-write pattern) already covers a deliberately
    malicious call attempting to derive INTO
    `projects/<slug>/planning-artifacts/**` -- no new pattern is needed,
    but the guard must actually fire when this module's own real primitive
    (`fs.symlink`) is asked to write there."""
    never_write = fs.NeverWrite(("**/planning-artifacts/**",))
    malicious_link = tmp_path / "_bmad-output" / "projects" / "acme" / "planning-artifacts" / "evil-link"

    with pytest.raises(NeverWriteViolation):
        fs.symlink(malicious_link, Path("elsewhere"), repo_root=tmp_path, never_write=never_write)

    assert not malicious_link.exists()
