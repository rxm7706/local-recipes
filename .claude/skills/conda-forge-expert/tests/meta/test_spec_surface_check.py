"""Meta-test: the repo-wide spec-surface detector stays green, and its
surviving mutation-only residual script still stamps baselines correctly.

spec-regenerable-factory CAP-3: every tracked file is governed by a spec
surface manifest or explicitly allowlisted, and no governed file drifted
without its spec's contract (memlog / sentinel) moving. This mirrors how
test_bmad_artifacts_in_sync.py enforces bmad-drift-check integrity.

Story 6.9: `scripts/spec_surface_check.py`'s read-only VERDICT retired into
`pyforge.doctor.sources.chain::gather_spec_surface` (ported verbatim in
behavior, Story 6.6) — `test_spec_surface_check_green` now exercises
`gather_spec_surface` directly (in-process) instead of running the origin
script's own coverage/drift report.

Review pass 1 (2026-08-10) corrected this file's own premise: the script
itself is NOT deleted. `--write-baseline`/`--spec NAME` is mutation
capability Doctor's read-only port deliberately never got (Charter §6),
and it is live-depended-on today (SYNC-RUNBOOK.md Step 3, CLAUDE.md's
Sync-loop section, and `spec-surface-drift-reconciliation`'s own, active
CAP-1 success criterion) — so `scripts/spec_surface_check.py` survives as
a reduced, mutation-only residual (no `DETECTOR` marker; the coverage/
drift computation is gone). The S-13.1 scoped-baseline-stamping tests
below exercise THAT surviving mechanism directly, restored from this
file's own history (they were removed in the first review pass on the
now-false premise that the script -- and therefore `--write-baseline`
entirely -- was gone for good).

S-13.2 (per-file reconciliation: drift / drift-presumed) and S-13.5
(drift-blind) stay NOT re-created here: those are READ-time verdict
semantics that moved to `gather_spec_surface` for good (the residual
script computes no findings at all any more), and their behavioral
coverage already lives at
`src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_spec_surface.py`
-- duplicating it here would be redundant, not migrated.
"""
from __future__ import annotations

import fcntl
import importlib.util
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[5]
CHECKER = REPO_ROOT / "scripts" / "spec_surface_check.py"

try:
    from pyforge.doctor.models import DoctorStatus
    from pyforge.doctor.sources import chain as spec_surface_chain
except ImportError:
    spec_surface_chain = None  # type: ignore[assignment]


@pytest.mark.skipif(
    spec_surface_chain is None,
    reason="pyforge.doctor not present (skill used standalone)",
)
def test_spec_surface_check_green():
    findings = spec_surface_chain.gather_spec_surface(REPO_ROOT)
    gating = [f for f in findings if f.status is DoctorStatus.FAIL]
    assert not gating, (
        "spec-surface reports findings — a tracked file is ungoverned "
        "or governed code drifted without its spec moving. Reconcile per "
        "the finding (update the spec / bmad-spec re-derive, then "
        "--write-baseline; or add a reason-tagged allowlist entry):\n"
        + "\n".join(f"[{f.check}] {f.message}" for f in gating)
    )


# --- S-13.1: scoped baseline stamping (the residual script's own mechanism) --


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
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    return tmp_path, _json


def _patched_checker(repo: Path) -> Path:
    """A copy of the residual script rooted at the fixture repo, not this one."""
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


def test_spec_given_without_write_baseline_is_a_usage_error(tmp_path: Path):
    """`--spec` only means anything alongside `--write-baseline` -- silently
    ignoring it (the origin script's own behavior) would be a footgun now
    that this script does nothing else with a bare invocation."""
    repo, _ = _fixture_repo(tmp_path)
    checker = _patched_checker(repo)
    r = subprocess.run([sys.executable, str(checker), "--spec", "proj/spec-alpha"],
                       capture_output=True, text=True, cwd=repo)
    assert r.returncode == 2
    assert "--write-baseline" in r.stderr


def test_bare_invocation_redirects_to_the_doctor_source(tmp_path: Path):
    """No flags at all must not silently do nothing -- it must say where the
    verdict actually lives now."""
    repo, _ = _fixture_repo(tmp_path)
    checker = _patched_checker(repo)
    r = subprocess.run([sys.executable, str(checker)],
                       capture_output=True, text=True, cwd=repo)
    assert r.returncode == 2
    assert "pyforge.doctor.sources spec-surface" in r.stderr


# --- S-12.5: the --write-baseline read-modify-write race is closed (DW-13-5-2/-3) ---


def _load_checker_module(checker: Path):
    """Import the patched checker copy in-process. Unique module name per
    call (derived from the tmp path) so parallel tests never collide in
    sys.modules."""
    name = f"spec_surface_checker_{checker.parent.parent.name}_{id(checker)}"
    spec = importlib.util.spec_from_file_location(name, checker)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_concurrent_scoped_stamps_neither_write_lost(tmp_path: Path):
    """The race itself, forced deterministically. A 2-party barrier gates
    `_read_baseline` inside `_stamp_baseline`'s critical section: on the
    UNLOCKED pre-fix shape both threads read the stale baseline concurrently,
    the barrier releases instantly, each merges into its own stale copy, and
    the last write clobbers the first -- the final both-entries-updated
    assertion catches exactly that lost write. Under the lock the second
    reader can never reach the barrier while the first thread holds the
    flock, so the barrier BREAKS after its bounded wait (safe direction:
    waiting longer only proves serialization harder), the BrokenBarrierError
    is swallowed, and the fully serialized threads land BOTH writes."""
    repo, _ = _fixture_repo(tmp_path)
    checker = _patched_checker(repo)
    subprocess.run([sys.executable, str(checker), "--write-baseline"],
                   capture_output=True, text=True, cwd=repo, check=True)

    # Both governed files drift, so both scoped stamps must change an entry.
    (repo / "a.py").write_text("x = 2\n", encoding="utf-8")
    (repo / "b.py").write_text("y = 2\n", encoding="utf-8")

    mod = _load_checker_module(checker)
    current = mod._live_state()  # computed once -- identical input for both

    gate = threading.Barrier(2)
    real_read = mod._read_baseline

    def gated_read():
        data = real_read()
        try:
            gate.wait(timeout=5)
        except threading.BrokenBarrierError:
            pass
        return data

    mod._read_baseline = gated_read
    threads = [
        threading.Thread(target=mod._stamp_baseline,
                         args=(["proj/spec-alpha"], current)),
        threading.Thread(target=mod._stamp_baseline,
                         args=(["proj/spec-beta"], current)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert not any(t.is_alive() for t in threads), "stamp threads never finished"

    after = json.loads(
        (repo / "scripts" / ".spec-surface-baseline.json").read_text())
    assert after["proj/spec-alpha"] == current["proj/spec-alpha"], (
        "alpha's stamp was silently lost -- the DW-13-5-2/-3 clobber")
    assert after["proj/spec-beta"] == current["proj/spec-beta"], (
        "beta's stamp was silently lost -- the DW-13-5-2/-3 clobber")


def test_write_baseline_blocks_while_lock_held(tmp_path: Path):
    """Cross-process serialization: while another process holds the sidecar
    flock, the CLI must block (no timeout machinery, by design) and proceed
    to a correct stamp only after release."""
    repo, _ = _fixture_repo(tmp_path)
    checker = _patched_checker(repo)
    subprocess.run([sys.executable, str(checker), "--write-baseline"],
                   capture_output=True, text=True, cwd=repo, check=True)
    baseline = repo / "scripts" / ".spec-surface-baseline.json"
    (repo / "a.py").write_text("x = 2\n", encoding="utf-8")
    stale = baseline.read_bytes()

    # The test itself plays the concurrent holder.
    fd = os.open(repo / "scripts" / ".spec-surface-baseline.json.lock",
                 os.O_CREAT | os.O_RDWR, 0o644)
    fcntl.flock(fd, fcntl.LOCK_EX)
    proc = subprocess.Popen(
        [sys.executable, str(checker), "--write-baseline",
         "--spec", "proj/spec-alpha"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=repo)
    try:
        # Safe-direction premise: the unblocked CLI completes in well under
        # 2s on this two-spec fixture (sub-second in practice), so "still
        # running after 2s" can only mean it is blocked on the flock.
        time.sleep(2.0)
        assert proc.poll() is None, "CLI completed despite the held flock"
        assert baseline.read_bytes() == stale, "baseline mutated under the lock"
        os.close(fd)  # release -- the blocked CLI may now proceed
        fd = -1
        assert proc.wait(timeout=30) == 0, proc.stderr.read()
    finally:
        if fd != -1:
            os.close(fd)
        if proc.poll() is None:
            proc.kill()  # never leak a blocked subprocess on a failed assert
            proc.wait(timeout=10)

    after = json.loads(baseline.read_text())
    assert after["proj/spec-alpha"] != json.loads(stale)["proj/spec-alpha"], (
        "post-release stamp did not land")


def test_stamp_is_atomic_and_leaves_no_residue(tmp_path: Path):
    """After a scoped stamp: no `.tmp` left behind (os.replace consumed it),
    the baseline parses as JSON (never torn), and the sidecar lockfile is
    still there -- deliberately never unlinked (unlink-while-others-wait
    recreates the race); it is gitignored instead."""
    repo, _ = _fixture_repo(tmp_path)
    checker = _patched_checker(repo)
    subprocess.run([sys.executable, str(checker), "--write-baseline"],
                   capture_output=True, text=True, cwd=repo, check=True)
    (repo / "a.py").write_text("x = 2\n", encoding="utf-8")
    subprocess.run([sys.executable, str(checker), "--write-baseline",
                    "--spec", "proj/spec-alpha"],
                   capture_output=True, text=True, cwd=repo, check=True)

    scripts = repo / "scripts"
    assert not (scripts / ".spec-surface-baseline.json.tmp").exists()
    json.loads((scripts / ".spec-surface-baseline.json").read_text())
    assert (scripts / ".spec-surface-baseline.json.lock").exists()
