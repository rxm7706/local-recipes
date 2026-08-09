"""Unit tests for ``pyforge.doctor.sources.chain.gather_spec_surface`` (Story
6.6) -- covers every row of the spec's I/O & Edge-Case Matrix that belongs to
coverage/drift/blindness against REAL tmp git repositories (this module's
own ``git ls-files`` call needs a real repo, mirroring
``test_sources_ledger.py``'s own real-fixture discipline).

Every kind below was independently verified, during development, to actually
FIRE its own dedicated test: temporarily removing that finding's
``findings.append(...)``/``presumed.append(...)`` branch in
``sources/chain.py`` and re-running the single test made it fail. That
verification is not re-encoded as a permanent mutation here -- see the story
spec's own Tasks & Acceptance for the requirement.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from pyforge.doctor.models import DoctorStatus, Source
from pyforge.doctor.sources import chain

# Same git-env scrub as test_sources_ledger_independence.py's sibling ledger
# test file -- a contributor's own git config must not decide whether this
# suite passes (see that file's own docstring for the full rationale).
_LEAKY_GIT_VARS = (
    "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY",
    "GIT_CEILING_DIRECTORIES", "GIT_COMMON_DIR",
)


@pytest.fixture(autouse=True)
def _isolate_git_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in _LEAKY_GIT_VARS:
        monkeypatch.delenv(var, raising=False)


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True,
    )
    return result.stdout


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q", "--initial-branch=main")
    _git(repo, "config", "user.email", "doctor-test@example.com")
    _git(repo, "config", "user.name", "Doctor Test")
    _git(repo, "config", "commit.gpgsign", "false")
    _git(repo, "config", "core.hooksPath", "/dev/null")


def _add_commit(repo: Path, message: str = "commit") -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)


def _spec_dir(repo: Path, project: str, spec: str) -> Path:
    return (
        repo / "_bmad-output" / "projects" / project
        / "planning-artifacts" / "specs" / spec
    )


def _write_spec(
    repo: Path,
    project: str,
    spec: str,
    *,
    surface: list[str],
    drift: str | None = None,
    exclude: list[str] | None = None,
) -> Path:
    sd = _spec_dir(repo, project, spec)
    sd.mkdir(parents=True, exist_ok=True)
    lines = ["---", "surface:"]
    lines.extend(f"  - {g}" for g in surface)
    if exclude:
        lines.append("surface-drift-exclude:")
        lines.extend(f"  - {g}" for g in exclude)
    if drift:
        lines.append(f"surface-drift: {drift}")
    lines += ["---", "", "body"]
    (sd / "SPEC.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return sd


def _write_allowlist(repo: Path, entries: list[tuple[str, str]]) -> None:
    path = repo / "scripts" / "spec_surface_allowlist.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(f"{pattern}  # {reason}" for pattern, reason in entries) + "\n",
        encoding="utf-8",
    )


def _write_baseline(repo: Path, data: dict) -> None:
    path = repo / "scripts" / ".spec-surface-baseline.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n", encoding="utf-8")


# --- Governed / ungoverned -----------------------------------------------------


def test_ungoverned_tracked_file_reports_fail(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "loose.py").write_text("x = 1\n", encoding="utf-8")
    _write_allowlist(repo, [])
    _add_commit(repo)

    findings = chain.gather_spec_surface(repo)

    kinds = {f.check for f in findings}
    assert "ungoverned" in kinds
    finding = next(f for f in findings if f.check == "ungoverned")
    assert finding.source is Source.SPEC_SURFACE
    assert finding.status is DoctorStatus.FAIL
    assert finding.evidence["path"] == "loose.py"


def test_governed_file_is_not_reported_ungoverned(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_spec(repo, "pyforge-x", "spec-foo", surface=["governed.py"])
    (repo / "governed.py").write_text("x = 1\n", encoding="utf-8")
    _write_allowlist(repo, [])
    _add_commit(repo)

    findings = chain.gather_spec_surface(repo)

    # This fixture's own SPEC.md/allowlist are themselves ungoverned by
    # `governed.py`'s narrow surface -- irrelevant to what this test pins,
    # which is only that the ONE file the surface DOES claim is never
    # reported ungoverned.
    ungoverned_paths = {f.evidence["path"] for f in findings if f.check == "ungoverned"}
    assert "governed.py" not in ungoverned_paths


def test_allowlisted_file_is_not_reported_ungoverned(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "vendored.py").write_text("x = 1\n", encoding="utf-8")
    _write_allowlist(repo, [("vendored.py", "third-party, not ours")])
    _add_commit(repo)

    findings = chain.gather_spec_surface(repo)

    # The allowlist file itself is tracked and ungoverned in this minimal
    # fixture (irrelevant here) -- what this test pins is that the
    # EXPLICITLY allowlisted file is never reported ungoverned.
    ungoverned_paths = {f.evidence["path"] for f in findings if f.check == "ungoverned"}
    assert "vendored.py" not in ungoverned_paths


# --- Stale allowlist -------------------------------------------------------------


def test_stale_allowlist_entry_reports_fail(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_allowlist(repo, [("nowhere/**", "used to exist")])
    _add_commit(repo)

    findings = chain.gather_spec_surface(repo)

    kinds = {f.check for f in findings}
    assert "stale-allowlist" in kinds
    finding = next(f for f in findings if f.check == "stale-allowlist")
    assert finding.status is DoctorStatus.FAIL
    assert finding.evidence["path"] == "nowhere/**"


# --- Drift-blind (governed, no memlog at all) -----------------------------------


def test_governed_spec_with_no_memlog_reports_drift_blind(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_spec(repo, "pyforge-x", "spec-foo", surface=["governed.py"])
    (repo / "governed.py").write_text("x = 1\n", encoding="utf-8")
    _write_allowlist(repo, [])
    _add_commit(repo)  # no .memlog.md ever created

    findings = chain.gather_spec_surface(repo)

    kinds = {f.check for f in findings}
    assert "drift-blind" in kinds
    finding = next(f for f in findings if f.check == "drift-blind")
    assert finding.status is DoctorStatus.FAIL
    assert "pyforge-x/spec-foo" in finding.evidence["path"]


# --- Drift (content changed, memlog did not move) -------------------------------


def test_governed_file_changed_without_memlog_moving_reports_drift_fail(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    sd = _write_spec(repo, "pyforge-x", "spec-foo", surface=["governed.py"])
    (sd / ".memlog.md").write_text("initial entry\n", encoding="utf-8")
    (repo / "governed.py").write_text("x = 1\n", encoding="utf-8")
    _write_allowlist(repo, [])
    _add_commit(repo)

    # Stamp a baseline reflecting THIS state by hand (mirrors what
    # --write-baseline would have written -- this gather never mutates it,
    # Boundaries).
    import hashlib
    memlog_hash = hashlib.sha1((sd / ".memlog.md").read_bytes()).hexdigest()
    file_hash = hashlib.sha1((repo / "governed.py").read_bytes()).hexdigest()
    _write_baseline(repo, {
        "pyforge-x/spec-foo": {"memlog": memlog_hash, "files": {"governed.py": file_hash}},
    })

    (repo / "governed.py").write_text("x = 2\n", encoding="utf-8")  # drift, memlog untouched
    _add_commit(repo, "change governed.py without touching the memlog")

    findings = chain.gather_spec_surface(repo)

    kinds = {f.check for f in findings}
    assert "drift" in kinds
    finding = next(f for f in findings if f.check == "drift")
    assert finding.status is DoctorStatus.FAIL
    assert finding.evidence["path"] == "governed.py"


def test_governed_file_changed_after_memlog_moves_and_names_it_is_clean(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    sd = _write_spec(repo, "pyforge-x", "spec-foo", surface=["governed.py"])
    (sd / ".memlog.md").write_text("initial entry\n", encoding="utf-8")
    (repo / "governed.py").write_text("x = 1\n", encoding="utf-8")
    _write_allowlist(repo, [])
    _add_commit(repo)

    import hashlib
    memlog_hash = hashlib.sha1((sd / ".memlog.md").read_bytes()).hexdigest()
    file_hash = hashlib.sha1((repo / "governed.py").read_bytes()).hexdigest()
    _write_baseline(repo, {
        "pyforge-x/spec-foo": {"memlog": memlog_hash, "files": {"governed.py": file_hash}},
    })

    (repo / "governed.py").write_text("x = 2\n", encoding="utf-8")
    (sd / ".memlog.md").write_text(
        "initial entry\nreconciled governed.py on 2026-08-09\n", encoding="utf-8",
    )
    _add_commit(repo, "reconcile: move the memlog and name the changed file")

    findings = chain.gather_spec_surface(repo)

    assert not any(f.check in ("drift", "drift-presumed") for f in findings)


def test_governed_file_changed_after_memlog_moves_without_naming_it_reports_drift_presumed_warn(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    # `**` governs every tracked file (SPEC.md/allowlist included -- see
    # `test_fully_clean_surface_reports_ok`'s own comment) so this fixture is
    # genuinely otherwise-clean, isolating the drift-presumed/OK coexistence
    # this test pins. The memlog's OWN path is excluded from the drift hash
    # (`surface-drift-exclude:`) -- otherwise it would ALSO drift-presume
    # against itself every time it moves, muddying which path this test means
    # to pin.
    memlog_rel = "_bmad-output/projects/pyforge-x/planning-artifacts/specs/spec-foo/.memlog.md"
    sd = _write_spec(
        repo, "pyforge-x", "spec-foo", surface=["**"], exclude=[memlog_rel],
    )
    (sd / ".memlog.md").write_text("initial entry\n", encoding="utf-8")
    (repo / "governed.py").write_text("x = 1\n", encoding="utf-8")
    _write_allowlist(repo, [])
    _add_commit(repo)

    import hashlib
    spec_md_rel = str((sd / "SPEC.md").relative_to(repo))
    files = {
        rel: hashlib.sha1((repo / rel).read_bytes()).hexdigest()
        for rel in ("governed.py", spec_md_rel, "scripts/spec_surface_allowlist.txt")
    }
    memlog_hash = hashlib.sha1((sd / ".memlog.md").read_bytes()).hexdigest()
    _write_baseline(repo, {
        "pyforge-x/spec-foo": {"memlog": memlog_hash, "files": files},
    })

    (repo / "governed.py").write_text("x = 2\n", encoding="utf-8")
    (sd / ".memlog.md").write_text(
        "initial entry\nunrelated activity, never names the path\n", encoding="utf-8",
    )
    _add_commit(repo, "unrelated memlog note")

    findings = chain.gather_spec_surface(repo)

    kinds = {f.check for f in findings}
    assert "drift-presumed" in kinds
    presumed = next(f for f in findings if f.check == "drift-presumed")
    assert presumed.status is DoctorStatus.WARN
    assert presumed.evidence["path"] == "governed.py"
    # Non-gating: an otherwise-clean surface with ONLY a drift-presumed item
    # still reports the coverage/drift OK verdict alongside it (matches the
    # original script's own "OK" print regardless of a non-empty
    # DRIFT-PRESUMED section).
    assert any(f.status is DoctorStatus.OK for f in findings)


# --- No baseline ------------------------------------------------------------------


def test_no_baseline_at_all_reports_fail(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_spec(repo, "pyforge-x", "spec-foo", surface=["governed.py"], drift="exempt")
    (repo / "governed.py").write_text("x = 1\n", encoding="utf-8")
    _write_allowlist(repo, [])
    _add_commit(repo)  # no .spec-surface-baseline.json at all

    findings = chain.gather_spec_surface(repo)

    kinds = {f.check for f in findings}
    assert "no-baseline" in kinds
    finding = next(f for f in findings if f.check == "no-baseline")
    assert finding.status is DoctorStatus.FAIL


def test_baseline_missing_this_specs_entry_reports_fail(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_spec(repo, "pyforge-x", "spec-foo", surface=["governed.py"], drift="exempt")
    (repo / "governed.py").write_text("x = 1\n", encoding="utf-8")
    _write_allowlist(repo, [])
    _write_baseline(repo, {})  # baseline exists but knows nothing of this spec
    _add_commit(repo)

    findings = chain.gather_spec_surface(repo)

    finding = next(f for f in findings if f.check == "no-baseline")
    assert finding.evidence["path"] == "pyforge-x/spec-foo"


# --- git ls-files unavailable --------------------------------------------------


def test_non_repository_target_reports_spec_surface_unevaluable_warn(
    tmp_path: Path,
) -> None:
    plain_dir = tmp_path / "not-a-repo"
    plain_dir.mkdir()

    findings = chain.gather_spec_surface(plain_dir)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.SPEC_SURFACE
    assert finding.check == "spec-surface-unevaluable"
    assert finding.status is DoctorStatus.WARN


def test_non_utf8_tracked_filename_reports_spec_surface_unevaluable_warn(
    tmp_path: Path, monkeypatch,
) -> None:
    """``run_git`` decodes ``git ls-files`` with ``text=True``, so a tracked
    path containing a non-UTF-8 byte raises ``UnicodeDecodeError`` --
    ``sources/ledger.py``'s own ``_git`` wrapper already guards this exact
    exception class for the same underlying cause; ``_tracked_files`` must
    degrade to the WARN rather than let it escape past the outer
    ``degrade_on_exception`` and mask every real coverage/drift finding."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _add_commit(repo)

    def _raise(*_args, **_kwargs):
        raise UnicodeDecodeError("utf-8", b"\xe9", 0, 1, "invalid start byte")

    monkeypatch.setattr(chain, "run_git", _raise)

    findings = chain.gather_spec_surface(repo)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.SPEC_SURFACE
    assert finding.check == "spec-surface-unevaluable"
    assert finding.status is DoctorStatus.WARN


def test_tracked_files_is_fetched_once_and_reused(tmp_path: Path, monkeypatch) -> None:
    """``_gather_spec_surface`` must not re-fetch ``git ls-files`` inside
    ``_check_spec_surface`` -- a second, independent call could transiently
    fail after the first succeeded and get silently coalesced to an empty
    list, reporting a false-clean/spurious verdict instead of the correct
    unevaluable WARN. Regression: ``run_git`` is called exactly once per
    ``gather_spec_surface`` invocation."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _add_commit(repo)

    calls = []
    real = chain.run_git

    def _counting(target, args, **kwargs):
        calls.append(args)
        return real(target, args, **kwargs)

    monkeypatch.setattr(chain, "run_git", _counting)

    chain.gather_spec_surface(repo)

    ls_files_calls = [c for c in calls if c == ["ls-files"]]
    assert len(ls_files_calls) == 1, (
        f"git ls-files was called {len(ls_files_calls)} times, expected 1: {calls}"
    )


# --- Clean chain: one OK Finding -------------------------------------------------


def test_fully_clean_surface_reports_ok(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    # `**` governs every tracked file in this fixture repo -- including this
    # very SPEC.md, the allowlist, and the baseline -- so nothing here is
    # ungoverned (mirrors the real repo's own `_bmad-output/**` allowlist
    # entry achieving the same effect for its own SPEC.md files).
    _write_spec(repo, "pyforge-x", "spec-foo", surface=["**"], drift="exempt")
    (repo / "governed.py").write_text("x = 1\n", encoding="utf-8")
    _write_allowlist(repo, [])
    _write_baseline(repo, {"pyforge-x/spec-foo": {"memlog": "", "files": {}}})
    _add_commit(repo)

    findings = chain.gather_spec_surface(repo)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.source is Source.SPEC_SURFACE
    assert finding.check == "spec-surface"
    assert finding.status is DoctorStatus.OK


def test_empty_repo_reports_ok(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _add_commit(repo)  # no allowlist file, no baseline, no specs at all

    findings = chain.gather_spec_surface(repo)

    kinds = {f.check for f in findings}
    # README.md is tracked but ungoverned (no specs, no allowlist), and no
    # baseline exists -- both gate. This pins the "nothing configured yet"
    # shape rather than asserting a vacuous OK it would be wrong to claim.
    assert "ungoverned" in kinds
    assert "no-baseline" in kinds


# --- Per-spec isolation ---------------------------------------------------------


def test_one_unevaluable_spec_does_not_hide_another_specs_real_finding(
    tmp_path: Path, monkeypatch,
) -> None:
    """One spec's unreadable memlog/governed file must not discard a
    DIFFERENT spec's already-computed real finding -- isolation structured in
    from the first draft (Design Notes), mirroring
    ``sources/board.py``'s own per-project isolation tests."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_spec(repo, "pyforge-good", "spec-good", surface=["good.py"])
    (repo / "good.py").write_text("x = 1\n", encoding="utf-8")
    _write_spec(repo, "pyforge-bad", "spec-bad", surface=["bad.py"])
    (repo / "bad.py").write_text("x = 1\n", encoding="utf-8")
    _write_allowlist(repo, [])
    _add_commit(repo)  # neither spec has a .memlog.md -> both are drift-blind

    real = chain._sha1

    def _explode(path: Path):
        if path.name == "bad.py":
            raise RuntimeError("unanticipated shape")
        return real(path)

    monkeypatch.setattr(chain, "_sha1", _explode)

    findings = chain.gather_spec_surface(repo)

    by_check_path = {(f.check, f.evidence.get("path")) for f in findings}
    assert ("drift-blind", "pyforge-good/spec-good") in by_check_path, (
        f"one spec's failure hid another's real finding: {findings}"
    )
    warns = [f for f in findings if f.check == "spec-surface-unevaluable"]
    assert any(f.evidence.get("path") == "pyforge-bad/spec-bad" for f in warns)
