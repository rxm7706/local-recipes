"""Meta-test: the repo-wide spec-surface detector stays green.

spec-regenerable-factory CAP-3: every tracked file is governed by a spec
surface manifest or explicitly allowlisted, and no governed file drifted
without its spec's contract (memlog / sentinel) moving. This mirrors how
test_bmad_artifacts_in_sync.py enforces bmad-drift-check integrity.
"""
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
CHECKER = REPO_ROOT / "scripts" / "spec_surface_check.py"


def test_spec_surface_check_green():
    result = subprocess.run(
        [sys.executable, str(CHECKER)], capture_output=True, text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, (
        "spec_surface_check reports findings — a tracked file is ungoverned "
        "or governed code drifted without its spec moving. Reconcile per the "
        "checker output (update the spec / bmad-spec re-derive, then "
        "--write-baseline; or add a reason-tagged allowlist entry):\n"
        + result.stdout + result.stderr
    )


# --- S-13.1: scoped baseline stamping ---------------------------------------


def _fixture_repo(tmp_path: Path, memlog_body: str = "- (note) initial\n"):
    """A miniature governed repo: two specs, one governed file each."""
    import json as _json

    for slug, governed in (("spec-alpha", "a.py"), ("spec-beta", "b.py")):
        d = (tmp_path / "_bmad-output" / "projects" / "proj"
             / "planning-artifacts" / "specs" / slug)
        d.mkdir(parents=True)
        (d / "SPEC.md").write_text(
            f"---\nsurface:\n  - {governed}\n---\n# {slug}\n", encoding="utf-8")
        (d / ".memlog.md").write_text(memlog_body, encoding="utf-8")
        (tmp_path / governed).write_text("x = 1\n", encoding="utf-8")

    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "spec_surface_allowlist.txt").write_text(
        "**   # everything else\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    return tmp_path, _json


def _patched_checker(repo: Path) -> Path:
    """A copy of the checker rooted at the fixture repo, not this one."""
    src = CHECKER.read_text(encoding="utf-8")
    src = src.replace('REPO_ROOT = Path(__file__).resolve().parent.parent',
                      f'REPO_ROOT = Path({str(repo)!r})')
    dst = repo / "scripts" / "checker.py"
    dst.write_text(src, encoding="utf-8")
    return dst


def test_scoped_stamp_leaves_every_other_spec_byte_identical(tmp_path: Path):
    """S-13.1's whole point. Stamping all specs in one write made the sanctioned
    fix for one `[no-baseline]` accept every OTHER spec's pending drift — so the
    honest move was to leave the red standing, and it stood for weeks."""
    repo, _json = _fixture_repo(tmp_path)
    checker = _patched_checker(repo)

    subprocess.run([sys.executable, str(checker), "--write-baseline"],
                   capture_output=True, text=True, cwd=repo, check=True)
    baseline = repo / "scripts" / ".spec-surface-baseline.json"
    before = _json.loads(baseline.read_text())

    # Both governed files drift.
    (repo / "a.py").write_text("x = 2\n", encoding="utf-8")
    (repo / "b.py").write_text("y = 2\n", encoding="utf-8")

    r = subprocess.run([sys.executable, str(checker), "--write-baseline",
                        "--spec", "proj/spec-alpha"],
                       capture_output=True, text=True, cwd=repo)
    assert r.returncode == 0, r.stderr
    after = _json.loads(baseline.read_text())

    assert after["proj/spec-alpha"] != before["proj/spec-alpha"], "alpha not stamped"
    assert after["proj/spec-beta"] == before["proj/spec-beta"], (
        "scoped stamp leaked into another spec — the all-or-nothing defect")


def test_scoped_stamp_merges_rather_than_rewrites(tmp_path: Path):
    """Building from the in-memory `current` alone would silently DROP every spec
    the invocation did not name."""
    repo, _json = _fixture_repo(tmp_path)
    checker = _patched_checker(repo)
    subprocess.run([sys.executable, str(checker), "--write-baseline"],
                   capture_output=True, text=True, cwd=repo, check=True)

    subprocess.run([sys.executable, str(checker), "--write-baseline",
                    "--spec", "proj/spec-alpha"],
                   capture_output=True, text=True, cwd=repo, check=True)

    after = _json.loads((repo / "scripts" / ".spec-surface-baseline.json").read_text())
    assert set(after) == {"proj/spec-alpha", "proj/spec-beta"}


def test_unknown_spec_name_exits_two_and_names_the_known_set(tmp_path: Path):
    repo, _ = _fixture_repo(tmp_path)
    checker = _patched_checker(repo)
    r = subprocess.run([sys.executable, str(checker), "--write-baseline",
                        "--spec", "proj/spec-nope"],
                       capture_output=True, text=True, cwd=repo)
    assert r.returncode == 2
    assert "unknown spec" in r.stderr and "proj/spec-alpha" in r.stderr


# --- S-13.2: per-file reconciliation ----------------------------------------


def test_an_unrelated_memlog_entry_no_longer_launders_pending_drift(tmp_path: Path):
    """Replays the LIVE incident (DW-SURFACE-2026-08-08-1): appending one
    unrelated note took findings 63 -> 61, clearing two detectors nobody had
    reconciled. The memlog must reconcile only the paths it NAMES."""
    repo, _ = _fixture_repo(tmp_path)
    checker = _patched_checker(repo)
    subprocess.run([sys.executable, str(checker), "--write-baseline"],
                   capture_output=True, text=True, cwd=repo, check=True)

    (repo / "a.py").write_text("x = 2\n", encoding="utf-8")          # real drift
    memlog = (repo / "_bmad-output" / "projects" / "proj" / "planning-artifacts"
              / "specs" / "spec-alpha" / ".memlog.md")
    memlog.write_text("- (note) initial\n- (note) something unrelated\n",
                      encoding="utf-8")

    r = subprocess.run([sys.executable, str(checker)],
                       capture_output=True, text=True, cwd=repo)
    assert "DRIFT-PRESUMED" in r.stdout, (
        "an unrelated memlog entry silently cleared real drift — the laundering "
        "defect is back:\n" + r.stdout)
    assert "a.py" in r.stdout


def test_a_memlog_that_names_the_path_reconciles_it(tmp_path: Path):
    repo, _ = _fixture_repo(tmp_path)
    checker = _patched_checker(repo)
    subprocess.run([sys.executable, str(checker), "--write-baseline"],
                   capture_output=True, text=True, cwd=repo, check=True)

    (repo / "a.py").write_text("x = 2\n", encoding="utf-8")
    memlog = (repo / "_bmad-output" / "projects" / "proj" / "planning-artifacts"
              / "specs" / "spec-alpha" / ".memlog.md")
    memlog.write_text("- (change) reconciled a.py for the new behaviour\n",
                      encoding="utf-8")

    r = subprocess.run([sys.executable, str(checker)],
                       capture_output=True, text=True, cwd=repo)
    assert "a.py" not in r.stdout.split("DRIFT-PRESUMED")[-1], (
        "a memlog naming the path should reconcile it:\n" + r.stdout)


def test_drift_presumed_never_gates(tmp_path: Path):
    """Informational by contract. A gating variant would just be the same
    unclearable red in a new shape — most memlog entries predate any naming
    convention."""
    repo, _ = _fixture_repo(tmp_path)
    checker = _patched_checker(repo)
    subprocess.run([sys.executable, str(checker), "--write-baseline"],
                   capture_output=True, text=True, cwd=repo, check=True)

    (repo / "a.py").write_text("x = 2\n", encoding="utf-8")
    memlog = (repo / "_bmad-output" / "projects" / "proj" / "planning-artifacts"
              / "specs" / "spec-alpha" / ".memlog.md")
    memlog.write_text("- (note) unrelated\n- (note) also unrelated\n",
                      encoding="utf-8")

    r = subprocess.run([sys.executable, str(checker)],
                       capture_output=True, text=True, cwd=repo)
    assert "DRIFT-PRESUMED" in r.stdout
    assert r.returncode == 0, (
        "drift-presumed must not gate — it is unproven, not wrong:\n" + r.stdout)


# --- S-13.5: a governed surface with no contract behind it -------------------


def _add_spec(repo: Path, slug: str, surface: str, *, memlog: bool,
              drift: str | None = None, governed: str | None = None) -> Path:
    """A third spec in the fixture, optionally without a memlog."""
    d = (repo / "_bmad-output" / "projects" / "proj" / "planning-artifacts"
         / "specs" / slug)
    d.mkdir(parents=True)
    fm = f"---\nsurface:\n  - {surface}\n"
    if drift:
        fm += f"surface-drift: {drift}\n"
    (d / "SPEC.md").write_text(fm + f"---\n# {slug}\n", encoding="utf-8")
    if memlog:
        (d / ".memlog.md").write_text("- (note) initial\n", encoding="utf-8")
    if governed:
        (repo / governed).write_text("g = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    return d


def test_a_governed_spec_with_no_memlog_is_drift_blind(tmp_path: Path):
    """The whole of S-13.5. contract_hash() returns "" for such a spec and
    "" != "" is never true, so `spec_moved` is permanently False: every governed
    change reports a hard [drift] whose printed remedy ("reconcile the spec") is
    unreachable, there being no contract to move. Two Specs shipped this way two
    days apart and nothing reported the condition."""
    repo, _ = _fixture_repo(tmp_path)
    checker = _patched_checker(repo)
    (repo / "_bmad-output" / "projects" / "proj" / "planning-artifacts"
     / "specs" / "spec-alpha" / ".memlog.md").unlink()
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)

    r = subprocess.run([sys.executable, str(checker)],
                       capture_output=True, text=True, cwd=repo)
    assert "[drift-blind] proj/spec-alpha" in r.stdout, (
        "a governed spec with no memlog passed silently — it is drift-blind and "
        "nothing said so:\n" + r.stdout)
    assert r.returncode == 1, (
        "[drift-blind] must GATE, unlike [drift-presumed]: it is a structurally "
        "impossible reconciliation, not merely an unproven one, and it clears by "
        "creating one file:\n" + r.stdout)


def test_restoring_the_memlog_re_greens_the_gate(tmp_path: Path):
    """The other half of the mutation: the finding must be clearable by exactly
    the act it asks for, or it is the unclearable red in a new shape."""
    repo, _ = _fixture_repo(tmp_path)
    checker = _patched_checker(repo)
    memlog = (repo / "_bmad-output" / "projects" / "proj" / "planning-artifacts"
              / "specs" / "spec-alpha" / ".memlog.md")
    memlog.unlink()
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    assert subprocess.run([sys.executable, str(checker)], capture_output=True,
                          text=True, cwd=repo).returncode == 1

    memlog.write_text("- (note) restored\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    r = subprocess.run([sys.executable, str(checker), "--write-baseline"],
                       capture_output=True, text=True, cwd=repo)
    assert "[drift-blind]" not in r.stdout, r.stdout


def test_a_spec_governing_zero_files_is_not_drift_blind(tmp_path: Path):
    """A surface matching nothing cannot drift, so it cannot be blind. Eleven
    such specs exist in this repo and must stay silent — otherwise the finding is
    noise, and a noisy gate is one nobody reads."""
    repo, _ = _fixture_repo(tmp_path)
    _add_spec(repo, "spec-empty", "nothing-matches-this/**", memlog=False)
    checker = _patched_checker(repo)

    r = subprocess.run([sys.executable, str(checker), "--write-baseline"],
                       capture_output=True, text=True, cwd=repo)
    assert "[drift-blind]" not in r.stdout, r.stdout


def test_exempt_and_sentinel_specs_are_not_drift_blind(tmp_path: Path):
    """`exempt` records no file hashes at all, and `sentinel:<path>` supplies a
    second hash that CAN move. Neither contract can go blind, and both are
    declared and printed rather than implicit."""
    repo, _ = _fixture_repo(tmp_path)
    _add_spec(repo, "spec-exempt", "e.py", memlog=False,
              drift="exempt", governed="e.py")
    (repo / "SENTINEL.md").write_text("v1\n", encoding="utf-8")
    _add_spec(repo, "spec-sentinel", "s.py", memlog=False,
              drift="sentinel:SENTINEL.md", governed="s.py")
    checker = _patched_checker(repo)

    r = subprocess.run([sys.executable, str(checker), "--write-baseline"],
                       capture_output=True, text=True, cwd=repo)
    assert "[drift-blind]" not in r.stdout, r.stdout


def test_the_checker_never_creates_the_memlog_it_checks_for(tmp_path: Path):
    """A self-clearing finding is not a finding — and writing the file would
    author a decision record nobody decided."""
    repo, _ = _fixture_repo(tmp_path)
    checker = _patched_checker(repo)
    memlog = (repo / "_bmad-output" / "projects" / "proj" / "planning-artifacts"
              / "specs" / "spec-alpha" / ".memlog.md")
    memlog.unlink()
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)

    subprocess.run([sys.executable, str(checker)],
                   capture_output=True, text=True, cwd=repo)
    assert not memlog.exists(), "the checker wrote the memlog it checks for"


def test_creating_a_memlog_without_stamping_downgrades_real_drift(tmp_path: Path):
    """Why the memlog and the scoped stamp are ONE change. A new memlog moves the
    contract hash off "", so the next comparison sees spec_moved=True and pending
    drift falls from gating [drift] to informational [drift-presumed] — trading a
    false green for a quiet one. This test pins that mechanism so the constraint
    is enforced by evidence rather than by a comment."""
    repo, _ = _fixture_repo(tmp_path)
    checker = _patched_checker(repo)
    memlog = (repo / "_bmad-output" / "projects" / "proj" / "planning-artifacts"
              / "specs" / "spec-alpha" / ".memlog.md")
    memlog.unlink()
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run([sys.executable, str(checker), "--write-baseline"],
                   capture_output=True, text=True, cwd=repo)

    (repo / "a.py").write_text("x = 2\n", encoding="utf-8")   # real, pending drift
    before = subprocess.run([sys.executable, str(checker)],
                            capture_output=True, text=True, cwd=repo)
    assert "[drift] proj/spec-alpha: a.py" in before.stdout, before.stdout

    # Names no governed path — matching is literal substring, so even the word
    # "a.py" inside an otherwise-unrelated sentence would reconcile it.
    memlog.write_text("- (note) an entry about something else entirely\n",
                      encoding="utf-8")
    after = subprocess.run([sys.executable, str(checker)],
                           capture_output=True, text=True, cwd=repo)
    assert "[drift] proj/spec-alpha: a.py" not in after.stdout
    assert "DRIFT-PRESUMED" in after.stdout and after.returncode == 0, (
        "expected the drift to have been downgraded to informational — if this "
        "no longer holds, the same-change stamp requirement needs revisiting:\n"
        + after.stdout)
