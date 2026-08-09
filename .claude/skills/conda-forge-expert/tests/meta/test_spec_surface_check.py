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
