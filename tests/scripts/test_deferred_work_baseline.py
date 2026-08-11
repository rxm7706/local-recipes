"""Coverage for ``scripts/deferred_work_baseline.py``, the mutation-only
stamper that grandfathers the pre-existing anonymous-Tier-3-entry backlog
(Epic 7 Story 7.2) at a dated cut-off.

Mirrors ``.claude/skills/conda-forge-expert/tests/meta/test_spec_surface_check.py``'s
own S-13.1 scoped-baseline-stamping test shape (that file's
``test_scoped_stamp_leaves_every_other_spec_byte_identical``,
``test_scoped_stamp_merges_rather_than_rewrites``,
``test_unknown_spec_name_exits_two_and_names_the_known_set``,
``test_spec_given_without_write_baseline_is_a_usage_error``, and
``test_bare_invocation_redirects_to_the_doctor_source``) with ``--project``
in place of ``--spec`` and per-project deferred-work.md fixtures in place of
per-spec SPEC.md fixtures.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
STAMPER = REPO_ROOT / "scripts" / "deferred_work_baseline.py"

# One identified entry (its own `## DW-...` heading consumes exactly one
# `- source_spec:` bullet for free) followed by one ORPHANED bullet with no
# heading of its own -- the exact "interrupted two-step write" shape
# `step-04-review.md` names as the bug this whole epic exists to catch.
# Anonymous count: 1.
_ONE_ANON = """## DW-FU-1-1: identified entry
- source_spec: `spec-a.md`
  summary: identified summary
  evidence: identified evidence

- source_spec: `spec-b.md`
  summary: orphaned entry, no heading of its own
  evidence: this is the anonymous one
"""

# Two identified entries, each with its own heading consuming its own single
# bullet. Anonymous count: 0.
_ZERO_ANON = """## DW-FU-2-1: first identified entry
- source_spec: `spec-c.md`
  summary: summary one
  evidence: evidence one

## DW-FU-2-2: second identified entry
- source_spec: `spec-d.md`
  summary: summary two
  evidence: evidence two
"""


def _fixture_repo(tmp_path: Path) -> Path:
    """A miniature `_bmad-output/projects/` tree: two projects, each with a
    Tier-3 deferred-work.md -- ``proj-alpha`` (1 anonymous entry) and
    ``proj-beta`` (0 anonymous entries)."""
    for slug, body in (("proj-alpha", _ONE_ANON), ("proj-beta", _ZERO_ANON)):
        d = tmp_path / "_bmad-output" / "projects" / slug / "implementation-artifacts"
        d.mkdir(parents=True)
        (d / "deferred-work.md").write_text(body, encoding="utf-8")
    (tmp_path / "scripts").mkdir()
    return tmp_path


def _patched_stamper(repo: Path) -> Path:
    """A copy of the stamper script rooted at the fixture repo, not this one.

    ``str.replace`` returns its input UNCHANGED, with no error, when the
    target substring is not found -- if a future edit reformats the
    ``REPO_ROOT`` line even slightly, the "patched" copy would silently keep
    pointing at the REAL repo, and every test below would then run against
    (and overwrite) the actual committed ``scripts/.deferred-work-baseline.json``
    instead of the tmp_path fixture. Assert the substitution actually fired."""
    src = STAMPER.read_text(encoding="utf-8")
    marker = "REPO_ROOT = Path(__file__).resolve().parent.parent"
    assert marker in src, (
        "REPO_ROOT line not found in scripts/deferred_work_baseline.py -- "
        "update this test's substitution target, or every test below would "
        "silently run against the real repo instead of a fixture"
    )
    src = src.replace(marker, f"REPO_ROOT = Path({str(repo)!r})")
    dst = repo / "scripts" / "stamper.py"
    dst.write_text(src, encoding="utf-8")
    return dst


def _baseline(repo: Path) -> dict:
    return json.loads((repo / "scripts" / ".deferred-work-baseline.json").read_text())


# --- I/O matrix row: bare --write-baseline stamps every discovered project ---


def test_bare_write_baseline_stamps_every_discovered_project_with_live_counts(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    stamper = _patched_stamper(repo)

    r = subprocess.run([sys.executable, str(stamper), "--write-baseline"],
                       capture_output=True, text=True, cwd=repo)
    assert r.returncode == 0, r.stderr

    baseline = _baseline(repo)
    assert baseline == {"proj-alpha": 1, "proj-beta": 0}


# --- I/O matrix row: a project directory with no Tier-3 file is excluded ---


def test_project_dir_with_no_tier3_file_is_not_included(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    (repo / "_bmad-output" / "projects" / "proj-gamma").mkdir(parents=True)
    stamper = _patched_stamper(repo)

    r = subprocess.run([sys.executable, str(stamper), "--write-baseline"],
                       capture_output=True, text=True, cwd=repo)
    assert r.returncode == 0, r.stderr

    baseline = _baseline(repo)
    assert "proj-gamma" not in baseline
    assert set(baseline) == {"proj-alpha", "proj-beta"}


def test_bare_write_baseline_never_drops_a_previously_stamped_project_it_cannot_currently_see(
    tmp_path: Path,
):
    """Reproduces a live review finding: a bare re-run from a checkout/worktree
    where a project's gitignored Tier-3 scratch is not locally present (a
    partial clone, an un-backlinked worktree, an unreadable directory) must
    not silently regress the committed baseline by dropping that project's
    entry -- it must MERGE, exactly like the `--project`-scoped path already
    does, never fully rebuild from only what is visible right now."""
    repo = _fixture_repo(tmp_path)
    stamper = _patched_stamper(repo)
    subprocess.run([sys.executable, str(stamper), "--write-baseline"],
                   capture_output=True, text=True, cwd=repo, check=True)
    before = _baseline(repo)
    assert set(before) == {"proj-alpha", "proj-beta"}

    # proj-alpha's Tier-3 scratch is no longer locally discoverable (e.g. an
    # un-backlinked worktree, or simply deleted on this machine).
    alpha_dir = repo / "_bmad-output" / "projects" / "proj-alpha" / "implementation-artifacts"
    (alpha_dir / "deferred-work.md").unlink()

    r = subprocess.run([sys.executable, str(stamper), "--write-baseline"],
                       capture_output=True, text=True, cwd=repo)
    assert r.returncode == 0, r.stderr
    after = _baseline(repo)

    assert after["proj-alpha"] == before["proj-alpha"], (
        "a bare re-run silently dropped a previously-stamped project that "
        "simply isn't locally discoverable right now — the exact "
        "grandfather-protection regression this test guards against"
    )
    assert after["proj-beta"] == before["proj-beta"]


# --- scoped stamping (mirrors spec_surface_check.py's S-13.1) ---


def test_scoped_stamp_leaves_every_other_project_byte_identical(tmp_path: Path):
    """The whole point of scoped stamping: an all-or-nothing write would
    silently accept every OTHER project's growth as "always was this way.\""""
    repo = _fixture_repo(tmp_path)
    stamper = _patched_stamper(repo)

    subprocess.run([sys.executable, str(stamper), "--write-baseline"],
                   capture_output=True, text=True, cwd=repo, check=True)
    before = _baseline(repo)

    # Both projects' Tier-3 files grow a new anonymous entry.
    alpha_md = repo / "_bmad-output" / "projects" / "proj-alpha" / "implementation-artifacts" / "deferred-work.md"
    beta_md = repo / "_bmad-output" / "projects" / "proj-beta" / "implementation-artifacts" / "deferred-work.md"
    alpha_md.write_text(alpha_md.read_text() + "\n- source_spec: `spec-e.md`\n  summary: new\n  evidence: new\n",
                        encoding="utf-8")
    beta_md.write_text(beta_md.read_text() + "\n- source_spec: `spec-f.md`\n  summary: new\n  evidence: new\n",
                       encoding="utf-8")

    r = subprocess.run([sys.executable, str(stamper), "--write-baseline",
                        "--project", "proj-alpha"],
                       capture_output=True, text=True, cwd=repo)
    assert r.returncode == 0, r.stderr
    after = _baseline(repo)

    assert after["proj-alpha"] != before["proj-alpha"], "alpha not stamped"
    assert after["proj-alpha"] == 2
    assert after["proj-beta"] == before["proj-beta"], (
        "scoped stamp leaked into another project — the all-or-nothing defect")


def test_scoped_stamp_merges_rather_than_rewrites(tmp_path: Path):
    """Building from the in-memory live state alone would silently DROP every
    project the invocation did not name."""
    repo = _fixture_repo(tmp_path)
    stamper = _patched_stamper(repo)
    subprocess.run([sys.executable, str(stamper), "--write-baseline"],
                   capture_output=True, text=True, cwd=repo, check=True)

    subprocess.run([sys.executable, str(stamper), "--write-baseline",
                    "--project", "proj-alpha"],
                   capture_output=True, text=True, cwd=repo, check=True)

    after = _baseline(repo)
    assert set(after) == {"proj-alpha", "proj-beta"}


def test_scoped_stamp_can_merge_into_a_baseline_that_does_not_exist_yet(tmp_path: Path):
    """`--project` before any bare stamp has ever run: merged = {} to start,
    not a crash on a missing file."""
    repo = _fixture_repo(tmp_path)
    stamper = _patched_stamper(repo)

    r = subprocess.run([sys.executable, str(stamper), "--write-baseline",
                        "--project", "proj-alpha"],
                       capture_output=True, text=True, cwd=repo)
    assert r.returncode == 0, r.stderr
    assert _baseline(repo) == {"proj-alpha": 1}


# --- error paths ---


def test_unknown_project_name_exits_two_and_names_the_known_set(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    stamper = _patched_stamper(repo)
    r = subprocess.run([sys.executable, str(stamper), "--write-baseline",
                        "--project", "proj-nope"],
                       capture_output=True, text=True, cwd=repo)
    assert r.returncode == 2
    assert "unknown project" in r.stderr
    assert "proj-alpha" in r.stderr and "proj-beta" in r.stderr
    assert not (repo / "scripts" / ".deferred-work-baseline.json").exists()


def test_project_given_without_write_baseline_is_a_usage_error(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    stamper = _patched_stamper(repo)
    r = subprocess.run([sys.executable, str(stamper), "--project", "proj-alpha"],
                       capture_output=True, text=True, cwd=repo)
    assert r.returncode == 2
    assert "--write-baseline" in r.stderr
    assert not (repo / "scripts" / ".deferred-work-baseline.json").exists()


def test_bare_invocation_explains_purpose_without_claiming_a_detector_reads_it(tmp_path: Path):
    """No flags at all must not silently do nothing -- and must not claim the
    detector already consumes this file, since Story 7.3 is what will."""
    repo = _fixture_repo(tmp_path)
    stamper = _patched_stamper(repo)
    r = subprocess.run([sys.executable, str(stamper)],
                       capture_output=True, text=True, cwd=repo)
    assert r.returncode == 2
    assert "--write-baseline" in r.stderr
    assert "No detector reads this file yet" in r.stderr
    assert not (repo / "scripts" / ".deferred-work-baseline.json").exists()


# --- I/O matrix row: a project with 0 anonymous entries still gets a stamped 0 ---


def test_project_with_zero_anonymous_entries_is_stamped_with_count_zero(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    stamper = _patched_stamper(repo)
    subprocess.run([sys.executable, str(stamper), "--write-baseline"],
                   capture_output=True, text=True, cwd=repo, check=True)
    baseline = _baseline(repo)
    assert baseline["proj-beta"] == 0
