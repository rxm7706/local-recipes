"""Coverage for ``scripts/apply_verification_verdicts.py``, the
mutation-only writer that applies agent/human-judged CAP-4 verification
verdicts to tracked ``deferred-work-ledger.md`` entries (Story 11.4).

Mirrors ``test_deferred_work_promote.py``'s own pattern: a
``_patched_script`` fixture copies the real script into a ``tmp_path``,
string-replaces its ``REPO_ROOT = Path(__file__).resolve().parent.parent``
line with the tmp path (and ASSERTS the substitution actually fired), runs
it via ``subprocess.run([sys.executable, ...], check=False)``, and for
error/collision paths asserts non-zero exit AND that the target ledger
either doesn't exist or is byte-identical to a pre-run snapshot.

One simplification vs. the promoter's own test: this script duplicates
(rather than imports) its one regex dependency and never touches
``pyforge.doctor`` at all, so no ``sys.path``/package-import setup is
needed here."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "apply_verification_verdicts.py"

TRACKED_REL = Path("planning-artifacts") / "deferred-work-ledger.md"

# --- Fixture ledger entries -------------------------------------------------

_ENTRY_ALPHA = """## DW-1-1-1 — Fresh bmad-loop worktrees can't `pixi run`/`pixi lock`

- source_spec: `_bmad-output/implementation-artifacts/spec-1-1-fixture.md`
  summary: Fresh bmad-loop worktrees can't run pixi commands because a long worktree path panics pixi-build-python.
  evidence: Reproduced live in this worktree -- pixi-build-python panics on long paths.
  status: open
"""

_ENTRY_BETA = """## DW-1-1-2 — The `/dist/` and `/dist-conda/` lines are gitignored

- source_spec: `_bmad-output/implementation-artifacts/spec-1-1-fixture.md`
  summary: The /dist/ and /dist-conda/ lines in .gitignore silently drop build artifacts from tracking.
  evidence: Confirmed via git check-ignore against a real build output tree.
  status: open
"""

# A "review-budget-followup" shape entry -- flat, UNINDENTED fields (no
# bullet), a real live shape distinct from the bulleted one above (see
# `pyforge-marshal`'s/`pyforge-warden`'s own `DW-FU-*` entries).
_ENTRY_FLAT = """### DW-FU-1-1: Follow-up review still recommended after the damping cap was spent

origin: review-budget-followup
source_spec: `spec-1-1-fixture.md`
severity: low
reason: The follow-up-review damping cap was spent with the story finalized while the review pass still recommended an independent follow-up.
status: open
"""

# An entry that already carries one prior `verified:` line -- exercises the
# re-verification append path.
_ENTRY_WITH_PRIOR_VERIFIED = """## DW-1-1-3 — Three uncoordinated hatchling version constraints

- source_spec: `_bmad-output/implementation-artifacts/spec-1-1-fixture.md`
  summary: Three uncoordinated version constraints exist for the hatchling build backend.
  evidence: Pre-existing, faithfully mirrored across the package family.

  status: open

  verified: 2026-07-30 — CONFIRMED STILL OPEN — the constraints are unchanged.
"""


def _ledger(*entries: str) -> str:
    return (
        "---\n"
        "doc_type: deferred-work-ledger\n"
        "project: pyforge-fixture\n"
        "status: promoted-verbatim\n"
        "---\n\n"
        "# pyforge-fixture — deferred-work ledger (TRACKED, fixture)\n\n"
        "# Deferred Work\n\n" + "\n".join(entries)
    )


def _write_tracked(project_dir: Path, body: str) -> Path:
    d = project_dir / TRACKED_REL
    d.parent.mkdir(parents=True, exist_ok=True)
    d.write_text(body, encoding="utf-8")
    return d


def _fixture_repo(tmp_path: Path) -> Path:
    """A miniature ``_bmad-output/projects/`` tree: ``pyforge-mason`` (three
    entries -- ``DW-1-1-1``, ``DW-1-1-2``, the flat ``DW-FU-1-1``, plus a
    ``## Deferred from: ...`` heading interposed between the first two, to
    exercise the heading-bounded span) and ``pyforge-doctor`` (one entry,
    ``DW-1-1-3``, already carrying a prior ``verified:`` line)."""
    projects = tmp_path / "_bmad-output" / "projects"
    mason = projects / "pyforge-mason"
    _write_tracked(
        mason,
        _ledger(_ENTRY_ALPHA)
        + "\n## Deferred from: code review of spec-9-9-fixture (fixture)\n\n"
        + _ENTRY_BETA
        + "\n" + _ENTRY_FLAT,
    )

    doctor = projects / "pyforge-doctor"
    _write_tracked(doctor, _ledger(_ENTRY_WITH_PRIOR_VERIFIED))

    (tmp_path / "scripts").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _patched_script(repo: Path) -> Path:
    """A copy of the real script rooted at the fixture repo, not this one.

    ``str.replace`` returns its input UNCHANGED, with no error, if the
    target substring is not found -- if a future edit reformats the
    ``REPO_ROOT`` line even slightly, the "patched" copy would silently
    keep pointing at the REAL repo, and every test below would then run
    against (and mutate) the actual committed ``_bmad-output/projects/``
    tree instead of the tmp_path fixture. Assert the substitution actually
    fired."""
    src = SCRIPT.read_text(encoding="utf-8")
    marker = "REPO_ROOT = Path(__file__).resolve().parent.parent"
    assert marker in src, (
        "REPO_ROOT line not found in scripts/apply_verification_verdicts.py "
        "-- update this test's substitution target, or every test below "
        "would silently run against the real repo instead of a fixture"
    )
    src = src.replace(marker, f"REPO_ROOT = Path({str(repo)!r})")
    dst = repo / "scripts" / "apply_verification_verdicts.py"
    dst.write_text(src, encoding="utf-8")
    return dst


def _write_verdicts(repo: Path, verdicts: list[dict]) -> Path:
    p = repo / "verdicts.json"
    p.write_text(json.dumps(verdicts), encoding="utf-8")
    return p


def _run(script: Path, repo: Path, *extra_args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script), "--fix", *extra_args],
        capture_output=True, text=True, cwd=repo, check=False,
    )


def _tracked_text(repo: Path, slug: str) -> str | None:
    p = repo / "_bmad-output" / "projects" / slug / TRACKED_REL
    return p.read_text(encoding="utf-8") if p.is_file() else None


def _verdict(
    project: str = "pyforge-mason", entry_id: str = "DW-1-1-1",
    verdict: str = "still-open",
    evidence: str = "Re-checked live: `foo.py:12` still shows the exact behavior.",
) -> dict:
    return {"project": project, "id": entry_id, "verdict": verdict, "evidence": evidence}


# --- I/O matrix row: valid verdict applied ----------------------------------


def test_valid_verdict_appends_one_new_verified_line_and_exits_zero(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    script = _patched_script(repo)
    before = _tracked_text(repo, "pyforge-mason")
    vfile = _write_verdicts(repo, [_verdict()])

    r = _run(script, repo, "--verdicts-file", str(vfile))
    assert r.returncode == 0, r.stderr
    assert "pyforge-mason: applied 1 verdict(s) -- DW-1-1-1" in r.stdout

    after = _tracked_text(repo, "pyforge-mason")
    assert after is not None and after != before
    assert (
        "  verified: " in after
        and " — still-open — Re-checked live: `foo.py:12`" in after
    )
    # Only ONE new verified line landed.
    assert after.count("verified:") == 1
    # No other field's text changed -- every original line is still present.
    for line in before.splitlines():
        assert line in after


def test_no_other_field_of_the_entry_changes(tmp_path: Path):
    """System AC: no other field of the target entry changes."""
    repo = _fixture_repo(tmp_path)
    script = _patched_script(repo)
    vfile = _write_verdicts(repo, [_verdict()])

    r = _run(script, repo, "--verdicts-file", str(vfile))
    assert r.returncode == 0, r.stderr

    after = _tracked_text(repo, "pyforge-mason")
    assert "summary: Fresh bmad-loop worktrees can't run pixi commands" in after
    assert "evidence: Reproduced live in this worktree" in after
    assert "status: open" in after


def test_verified_line_lands_after_the_entrys_own_content_not_past_an_interposed_heading(
    tmp_path: Path,
):
    """Heading-bounded span: DW-1-1-1 is immediately followed (in the raw
    file) by a `## Deferred from: ...` heading, then DW-1-1-2. The new
    `verified:` line must land right after DW-1-1-1's own content -- BEFORE
    the interposed heading -- never after it."""
    repo = _fixture_repo(tmp_path)
    script = _patched_script(repo)
    vfile = _write_verdicts(repo, [_verdict()])

    r = _run(script, repo, "--verdicts-file", str(vfile))
    assert r.returncode == 0, r.stderr

    after = _tracked_text(repo, "pyforge-mason")
    verified_pos = after.index("verified:")
    heading_pos = after.index("## Deferred from:")
    assert verified_pos < heading_pos, (
        "the new verified: line landed AFTER the interposed heading instead "
        "of right after DW-1-1-1's own content"
    )


def test_flat_unindented_field_shape_is_also_a_valid_target(tmp_path: Path):
    """The `review-budget-followup` shape (flat, unindented fields, no
    bullet) is a real live shape -- must be a valid target too, and the new
    `verified:` line is still written with the script's own canonical
    2-space indent regardless of the entry's own field style."""
    repo = _fixture_repo(tmp_path)
    script = _patched_script(repo)
    vfile = _write_verdicts(repo, [_verdict(entry_id="DW-FU-1-1", verdict="resolved")])

    r = _run(script, repo, "--verdicts-file", str(vfile))
    assert r.returncode == 0, r.stderr

    after = _tracked_text(repo, "pyforge-mason")
    assert "  verified: " in after and " — resolved — " in after


# --- I/O matrix row: invalid verdict token ----------------------------------


def test_invalid_verdict_token_aborts_the_whole_project_batch(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    script = _patched_script(repo)
    before = _tracked_text(repo, "pyforge-mason")
    vfile = _write_verdicts(repo, [_verdict(verdict="escalate")])

    r = _run(script, repo, "--verdicts-file", str(vfile))
    assert r.returncode != 0
    assert "ABORTED" in r.stdout
    assert "invalid verdict 'escalate'" in r.stdout
    assert "DW-1-1-1" in r.stdout

    assert _tracked_text(repo, "pyforge-mason") == before


# --- I/O matrix row: evidence restates the entry's own prose ---------------


def test_evidence_restating_the_summary_field_aborts_with_no_write(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    script = _patched_script(repo)
    before = _tracked_text(repo, "pyforge-mason")
    restated = (
        "fresh bmad-loop worktrees can't run    pixi commands because a "
        "LONG worktree path panics pixi-build-python."
    )
    vfile = _write_verdicts(repo, [_verdict(evidence=restated)])

    r = _run(script, repo, "--verdicts-file", str(vfile))
    assert r.returncode != 0
    assert "ABORTED" in r.stdout
    assert "restates the entry's own summary:" in r.stdout

    assert _tracked_text(repo, "pyforge-mason") == before


def test_evidence_restating_the_evidence_field_aborts_with_no_write(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    script = _patched_script(repo)
    before = _tracked_text(repo, "pyforge-mason")
    restated = "Reproduced live in this worktree -- pixi-build-python panics on long paths."
    vfile = _write_verdicts(repo, [_verdict(evidence=restated)])

    r = _run(script, repo, "--verdicts-file", str(vfile))
    assert r.returncode != 0
    assert "restates the entry's own evidence:" in r.stdout

    assert _tracked_text(repo, "pyforge-mason") == before


# --- I/O matrix row: empty evidence -----------------------------------------


def test_empty_evidence_aborts_with_no_write(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    script = _patched_script(repo)
    before = _tracked_text(repo, "pyforge-mason")
    vfile = _write_verdicts(repo, [_verdict(evidence="   ")])

    r = _run(script, repo, "--verdicts-file", str(vfile))
    assert r.returncode != 0
    assert "ABORTED" in r.stdout
    assert "evidence is empty" in r.stdout

    assert _tracked_text(repo, "pyforge-mason") == before


# --- I/O matrix row: unknown entry id ---------------------------------------


def test_unknown_entry_id_aborts_that_project_only_sibling_still_writes(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    script = _patched_script(repo)
    mason_before = _tracked_text(repo, "pyforge-mason")
    vfile = _write_verdicts(repo, [
        _verdict(entry_id="DW-9-9-9"),
        _verdict(project="pyforge-doctor", entry_id="DW-1-1-3", verdict="resolved",
                  evidence="Both constraints were consolidated in a single follow-up PR."),
    ])

    r = _run(script, repo, "--verdicts-file", str(vfile))
    assert r.returncode != 0, "the unknown id must surface in the overall exit code"
    assert "pyforge-mason: ABORTED" in r.stdout
    assert "DW-9-9-9" in r.stdout and "no such entry" in r.stdout
    assert "pyforge-doctor: applied 1 verdict(s)" in r.stdout

    assert _tracked_text(repo, "pyforge-mason") == mason_before
    doctor_after = _tracked_text(repo, "pyforge-doctor")
    assert doctor_after is not None and "resolved" in doctor_after


# --- I/O matrix row: duplicate (project, id) in one input file -------------


def test_duplicate_project_id_pair_aborts_and_names_both_occurrences(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    script = _patched_script(repo)
    before = _tracked_text(repo, "pyforge-mason")
    vfile = _write_verdicts(repo, [
        _verdict(verdict="still-open"),
        _verdict(verdict="resolved", evidence="A different, later evidence string entirely."),
    ])

    r = _run(script, repo, "--verdicts-file", str(vfile))
    assert r.returncode != 0
    assert "ABORTED" in r.stdout
    assert "duplicate id 'DW-1-1-1'" in r.stdout
    assert "position 0 and 1" in r.stdout

    assert _tracked_text(repo, "pyforge-mason") == before


# --- I/O matrix row: re-verification ----------------------------------------


def test_reverification_appends_after_the_last_verified_line_prior_lines_untouched(
    tmp_path: Path,
):
    repo = _fixture_repo(tmp_path)
    script = _patched_script(repo)
    before = _tracked_text(repo, "pyforge-doctor")
    assert before.count("verified:") == 1
    vfile = _write_verdicts(repo, [
        _verdict(project="pyforge-doctor", entry_id="DW-1-1-3", verdict="resolved",
                  evidence="Confirmed fixed by the shared pyproject.toml constraint added today."),
    ])

    r = _run(script, repo, "--verdicts-file", str(vfile))
    assert r.returncode == 0, r.stderr

    after = _tracked_text(repo, "pyforge-doctor")
    assert after.count("verified:") == 2
    # The prior verified: line is byte-identical, still present in full.
    prior_line = next(ln for ln in before.splitlines() if ln.strip().startswith("verified:"))
    assert prior_line in after
    # The new line comes AFTER the prior one.
    assert after.index(prior_line) < after.rindex("verified:")
    assert " — resolved — Confirmed fixed by the shared pyproject.toml" in after


# --- I/O matrix row: concurrent ledger change mid-run -----------------------


def test_concurrent_ledger_change_is_detected_and_aborts_without_losing_it(tmp_path: Path):
    """Reproduces the race `deferred_work_promote.py`'s own review found:
    the script reads the tracked ledger once (its snapshot), validates, and
    must re-check immediately before the terminal write. Instrumented by
    replacing the fixture's tracked ledger on disk with different content
    BEFORE invoking the subprocess -- simulating "changed between two
    separate runs/processes" is equivalent in effect to "changed mid-run"
    for this script's own single-read-then-write shape, and is the
    reproducible variant available from outside the process."""
    repo = _fixture_repo(tmp_path)
    script = _patched_script(repo)
    tracked_path = repo / "_bmad-output" / "projects" / "pyforge-mason" / TRACKED_REL
    original = tracked_path.read_text(encoding="utf-8")
    vfile = _write_verdicts(repo, [_verdict()])

    # Simulate a concurrent writer having already landed a change by the
    # time the race re-check (immediately before the write) runs: patch the
    # script so `_read_tracked` returns different content on its SECOND
    # call only (the race re-check), not its first (the snapshot) --
    # verifies the two-read shape rather than merely "the file happens to
    # differ before the process even starts."
    src = script.read_text(encoding="utf-8")
    marker = "def _apply_project("
    assert marker in src
    injected = (
        "_read_tracked_call_count = {\"n\": 0}\n"
        "_real_read_tracked = _read_tracked\n"
        "def _read_tracked(path):  # noqa: ANN001, ANN201\n"
        "    _read_tracked_call_count[\"n\"] += 1\n"
        "    if _read_tracked_call_count[\"n\"] == 2:\n"
        "        return True, _real_read_tracked(path)[1] + \"\\nCONCURRENT CHANGE\\n\"\n"
        "    return _real_read_tracked(path)\n\n\n"
        + marker
    )
    script.write_text(src.replace(marker, injected, 1), encoding="utf-8")

    r = _run(script, repo, "--verdicts-file", str(vfile))
    assert r.returncode != 0
    assert "pyforge-mason: ABORTED" in r.stdout
    assert "changed during this run" in r.stdout
    assert "concurrent" in r.stdout.lower()

    # The real on-disk content (never touched by the injected shim, which
    # only changes what the SECOND in-process read returns) is untouched.
    assert tracked_path.read_text(encoding="utf-8") == original


# --- I/O matrix row: No --fix -----------------------------------------------


def test_bare_invocation_explains_purpose_and_does_not_write(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    script = _patched_script(repo)
    mason_before = _tracked_text(repo, "pyforge-mason")
    doctor_before = _tracked_text(repo, "pyforge-doctor")
    vfile = _write_verdicts(repo, [_verdict()])

    r = subprocess.run(
        [sys.executable, str(script), "--verdicts-file", str(vfile)],
        capture_output=True, text=True, cwd=repo, check=False,
    )
    assert r.returncode == 2
    assert "--fix" in r.stderr
    # Review finding, patch: the prior `A or B` form let either substring
    # alone satisfy the test, so a near-empty stderr containing just one of
    # the two words would pass -- both must actually be present, matching
    # what the purpose text (main()'s own docstring-length explanation)
    # genuinely promises: the closed vocabulary AND the `verified:` line
    # shape it produces.
    assert "verified:" in r.stderr
    assert "verdict" in r.stderr
    assert "still-open" in r.stderr  # names the closed vocabulary, not just its shape

    assert _tracked_text(repo, "pyforge-mason") == mason_before
    assert _tracked_text(repo, "pyforge-doctor") == doctor_before


def test_completely_bare_invocation_is_also_a_usage_error(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    script = _patched_script(repo)

    r = subprocess.run(
        [sys.executable, str(script)], capture_output=True, text=True, cwd=repo, check=False,
    )
    assert r.returncode == 2
    assert "--fix" in r.stderr


# --- System AC: two-project batch, one invalid one clean --------------------


def test_two_project_batch_one_invalid_one_clean_writes_only_the_clean_one(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    script = _patched_script(repo)
    mason_before = _tracked_text(repo, "pyforge-mason")
    vfile = _write_verdicts(repo, [
        _verdict(project="pyforge-mason", entry_id="DW-1-1-1", verdict="not-a-real-verdict"),
        _verdict(project="pyforge-doctor", entry_id="DW-1-1-3", verdict="moot-superseded",
                  evidence="Superseded by the shared pyproject.toml fix landed in PR #999."),
    ])

    r = _run(script, repo, "--verdicts-file", str(vfile))
    assert r.returncode != 0
    assert "pyforge-mason: ABORTED" in r.stdout
    assert "pyforge-doctor: applied 1 verdict(s)" in r.stdout

    assert _tracked_text(repo, "pyforge-mason") == mason_before
    doctor_after = _tracked_text(repo, "pyforge-doctor")
    assert doctor_after is not None
    assert " — moot-superseded — Superseded by the shared pyproject.toml" in doctor_after


# --- Additional coverage: malformed input, missing flags, unknown project ---


def test_malformed_json_is_a_top_level_usage_error_not_a_project_failure(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    script = _patched_script(repo)
    mason_before = _tracked_text(repo, "pyforge-mason")
    vfile = repo / "verdicts.json"
    vfile.write_text("{ not valid json", encoding="utf-8")

    r = _run(script, repo, "--verdicts-file", str(vfile))
    assert r.returncode == 2
    assert "not valid JSON" in r.stderr

    assert _tracked_text(repo, "pyforge-mason") == mason_before


def test_verdicts_file_not_a_json_array_is_a_usage_error(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    script = _patched_script(repo)
    vfile = repo / "verdicts.json"
    vfile.write_text(json.dumps({"project": "pyforge-mason"}), encoding="utf-8")

    r = _run(script, repo, "--verdicts-file", str(vfile))
    assert r.returncode == 2
    assert "must contain a JSON array" in r.stderr


def test_verdicts_file_object_missing_a_required_key_is_a_usage_error(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    script = _patched_script(repo)
    vfile = repo / "verdicts.json"
    vfile.write_text(
        json.dumps([{"project": "pyforge-mason", "id": "DW-1-1-1", "verdict": "still-open"}]),
        encoding="utf-8",
    )

    r = _run(script, repo, "--verdicts-file", str(vfile))
    assert r.returncode == 2
    assert "missing required key" in r.stderr and "evidence" in r.stderr


def test_fix_without_verdicts_file_is_a_usage_error(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    script = _patched_script(repo)

    r = subprocess.run(
        [sys.executable, str(script), "--fix"],
        capture_output=True, text=True, cwd=repo, check=False,
    )
    assert r.returncode == 2
    assert "--verdicts-file" in r.stderr


def test_empty_verdicts_list_is_a_clean_noop(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    script = _patched_script(repo)
    mason_before = _tracked_text(repo, "pyforge-mason")
    vfile = _write_verdicts(repo, [])

    r = _run(script, repo, "--verdicts-file", str(vfile))
    assert r.returncode == 0, r.stderr
    assert "nothing to apply" in r.stdout

    assert _tracked_text(repo, "pyforge-mason") == mason_before


def test_project_with_no_tracked_ledger_aborts_with_no_write(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    script = _patched_script(repo)
    (repo / "_bmad-output" / "projects" / "pyforge-warden").mkdir(parents=True)
    vfile = _write_verdicts(repo, [_verdict(project="pyforge-warden", entry_id="DW-1-1-1")])

    r = _run(script, repo, "--verdicts-file", str(vfile))
    assert r.returncode != 0
    assert "pyforge-warden: ABORTED" in r.stdout
    assert "no tracked ledger" in r.stdout
    assert _tracked_text(repo, "pyforge-warden") is None


# --- Atomic write: no stray temp file left behind ---------------------------


def test_atomic_write_leaves_no_stray_temp_file_and_correct_content(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    script = _patched_script(repo)
    vfile = _write_verdicts(repo, [_verdict()])

    r = _run(script, repo, "--verdicts-file", str(vfile))
    assert r.returncode == 0, r.stderr

    tracked_dir = repo / "_bmad-output" / "projects" / "pyforge-mason" / TRACKED_REL.parent
    names = sorted(p.name for p in tracked_dir.iterdir())
    assert names == [TRACKED_REL.name], names


# --- Multiple verdicts for different entries within one clean project batch -


def test_multiple_verdicts_in_one_project_batch_each_land_at_their_own_entry(tmp_path: Path):
    repo = _fixture_repo(tmp_path)
    script = _patched_script(repo)
    vfile = _write_verdicts(repo, [
        _verdict(entry_id="DW-1-1-1", verdict="still-open",
                  evidence="Re-checked: the panic is still reproducible at `tools.rs:461`."),
        _verdict(entry_id="DW-1-1-2", verdict="resolved",
                  evidence="The .gitignore lines were removed in a follow-up commit."),
    ])

    r = _run(script, repo, "--verdicts-file", str(vfile))
    assert r.returncode == 0, r.stderr
    assert "applied 2 verdict(s) -- DW-1-1-1, DW-1-1-2" in r.stdout

    after = _tracked_text(repo, "pyforge-mason")
    assert after.count("verified:") == 2
    alpha_span = after[after.index("DW-1-1-1"):after.index("DW-1-1-2")]
    beta_span = after[after.index("DW-1-1-2"):]
    assert " — still-open — Re-checked: the panic" in alpha_span
    assert " — resolved — The .gitignore lines" in beta_span


# --- Review pass: unknown/malicious project value never escapes the tree ---


def test_unknown_project_slug_aborts_with_no_write(tmp_path: Path):
    """A `project` value that is not a real discovered directory (typo,
    made-up slug) must abort, never silently create/probe an unexpected
    path."""
    repo = _fixture_repo(tmp_path)
    script = _patched_script(repo)
    vfile = _write_verdicts(repo, [_verdict(project="pyforge-not-a-real-project")])

    r = _run(script, repo, "--verdicts-file", str(vfile))
    assert r.returncode != 0
    assert "unknown project" in r.stdout


def test_absolute_project_value_cannot_escape_the_projects_tree(tmp_path: Path):
    """Review finding (Blind Hunter + Edge Case Hunter, same finding):
    `Path.__truediv__` silently discards everything to its left when the
    right operand is absolute, so an absolute `project` string used to
    resolve `tracked_path` entirely outside `_bmad-output/projects/`.
    Plants a real ledger at the traversal target to prove it is genuinely
    unreachable, not merely absent."""
    repo = _fixture_repo(tmp_path)
    script = _patched_script(repo)
    escape_target = tmp_path / "escaped"
    _write_tracked(escape_target, _ledger(_ENTRY_ALPHA))
    vfile = _write_verdicts(repo, [_verdict(project=str(escape_target))])

    r = _run(script, repo, "--verdicts-file", str(vfile))
    assert r.returncode != 0
    assert "unknown project" in r.stdout
    # The planted ledger outside _bmad-output/projects/ is untouched.
    assert "verified:" not in (escape_target / TRACKED_REL).read_text(encoding="utf-8")


def test_empty_project_value_aborts_rather_than_dropping_the_path_segment(tmp_path: Path):
    """`Path(...) / ''` silently drops an empty path component -- must be
    rejected as an unknown project, not resolve to a different (wrong)
    path one level up."""
    repo = _fixture_repo(tmp_path)
    script = _patched_script(repo)
    vfile = _write_verdicts(repo, [_verdict(project="")])

    r = _run(script, repo, "--verdicts-file", str(vfile))
    assert r.returncode != 0
    assert "unknown project" in r.stdout


# --- Review pass: anti-restatement check for the flat DW-FU-* shape --------


def test_flat_shape_evidence_restating_its_own_reason_field_aborts(tmp_path: Path):
    """Review finding (Blind Hunter + Edge Case Hunter, same finding): the
    flat `review-budget-followup` shape carries a `reason:` field, not
    `summary:`/`evidence:` -- the anti-restatement check was structurally
    inert for this entire documented, tested-as-valid shape until
    `_FIELD_RE`/`_validate_project_batch` were extended to also check
    `reason:`."""
    repo = _fixture_repo(tmp_path)
    script = _patched_script(repo)
    before = _tracked_text(repo, "pyforge-mason")
    restated = (
        "The follow-up-review damping cap was spent with the story "
        "finalized while the review pass still recommended an "
        "independent follow-up."
    )
    vfile = _write_verdicts(repo, [
        _verdict(entry_id="DW-FU-1-1", verdict="resolved", evidence=restated),
    ])

    r = _run(script, repo, "--verdicts-file", str(vfile))
    assert r.returncode != 0
    assert "restates the entry's own reason:" in r.stdout

    assert _tracked_text(repo, "pyforge-mason") == before


# --- Review pass: embedded newline in evidence is rejected -----------------


def test_evidence_with_an_embedded_newline_aborts_with_no_write(tmp_path: Path):
    """Review finding (Blind Hunter + Edge Case Hunter, same finding): every
    real `summary:`/`evidence:` value is one physical line
    (`_entry_spans`'s own docstring assumption); an unrejected embedded
    newline in the applied evidence would write a stray, unindented line
    into the ledger matching no `_FIELD_RE`/`_ENTRY_RE` pattern."""
    repo = _fixture_repo(tmp_path)
    script = _patched_script(repo)
    before = _tracked_text(repo, "pyforge-mason")
    vfile = _write_verdicts(repo, [
        _verdict(evidence="Line one of the evidence.\nLine two of the evidence."),
    ])

    r = _run(script, repo, "--verdicts-file", str(vfile))
    assert r.returncode != 0
    assert "ABORTED" in r.stdout
    assert "single physical line" in r.stdout

    assert _tracked_text(repo, "pyforge-mason") == before


# --- Review pass: full closed-vocabulary coverage ---------------------------


def test_pending_on_precondition_verdict_is_accepted(tmp_path: Path):
    """The 4th and last closed-vocabulary member (`pending-on-precondition`)
    had zero test coverage (Edge Case Hunter)."""
    repo = _fixture_repo(tmp_path)
    script = _patched_script(repo)
    vfile = _write_verdicts(repo, [
        _verdict(verdict="pending-on-precondition",
                  evidence="Genuinely undecidable until Story 12.3 lands."),
    ])

    r = _run(script, repo, "--verdicts-file", str(vfile))
    assert r.returncode == 0, r.stderr

    after = _tracked_text(repo, "pyforge-mason")
    assert " — pending-on-precondition — Genuinely undecidable" in after


# --- Review pass: blank-line/spacing structure is genuinely preserved ------


def test_blank_line_spacing_around_the_target_entry_is_unchanged(tmp_path: Path):
    """Strengthens the existing `for line in before.splitlines(): assert
    line in after` assertion (Blind Hunter): that check is near-a-no-op for
    blank lines, since `"" in after` is trivially true for any non-empty
    string. This test instead asserts the exact line-by-line SEQUENCE
    around the target entry, so a spacing/structure regression would fail
    it even though the weaker membership check would not."""
    repo = _fixture_repo(tmp_path)
    script = _patched_script(repo)
    vfile = _write_verdicts(repo, [_verdict()])

    r = _run(script, repo, "--verdicts-file", str(vfile))
    assert r.returncode == 0, r.stderr

    after = _tracked_text(repo, "pyforge-mason")
    lines = after.splitlines()
    verified_idx = next(i for i, ln in enumerate(lines) if "verified:" in ln)
    # Exactly one blank line separates the entry's last original field line
    # (`  status: open`) from the new `verified:` line, and exactly one
    # blank line separates the `verified:` line from the next heading.
    assert lines[verified_idx - 1] == ""
    assert lines[verified_idx - 2].strip() == "status: open"
    assert lines[verified_idx + 1] == ""
    assert lines[verified_idx + 2].startswith("## Deferred from:")
