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


# --- Unreadable inputs must not silently un-govern ------------------------------


def test_unreadable_spec_md_warns_instead_of_reporting_its_files_ungoverned(
    tmp_path: Path,
) -> None:
    """An unreadable SPEC.md degrading to an EMPTY surface is
    indistinguishable from "this spec governs nothing", so every file it
    really owns is reported FAIL ``ungoverned`` ("no spec surface and no
    allowlist entry") -- confidently wrong rather than honestly unevaluable,
    and the exact silent-governance-loss defect the original script's own
    docstring records having fixed. Coverage is a GLOBAL computation over
    every surface, so one unknown surface suppresses the coverage half while
    the WARN names which spec went dark."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    sd = _write_spec(repo, "pyforge-x", "spec-foo", surface=["governed.py"])
    (repo / "governed.py").write_text("x = 1\n", encoding="utf-8")
    _write_allowlist(repo, [])
    _add_commit(repo)
    # Non-UTF-8 bytes: read_text(encoding="utf-8") raises UnicodeDecodeError,
    # the same class a permissions failure would take through OSError.
    (sd / "SPEC.md").write_bytes(b"---\nsurface:\n  - governed.py\n# caf\xe9\n---\n")

    findings = chain.gather_spec_surface(repo)

    warns = [f for f in findings if f.check == "spec-surface-unevaluable"]
    assert any(f.evidence["path"] == "pyforge-x/spec-foo" for f in warns), (
        f"an unreadable SPEC.md did not surface as unevaluable: {findings}"
    )
    assert all(f.status is DoctorStatus.WARN for f in warns)
    assert "ungoverned" not in {f.check for f in findings}, (
        f"coverage was reported despite an unknown surface: {findings}"
    )


def test_unreadable_allowlist_warns_instead_of_reporting_ungoverned(
    tmp_path: Path,
) -> None:
    """An allowlist that EXISTS but cannot be read must not degrade to "[]" --
    that would report every exempted file FAIL ``ungoverned``, a message that
    literally asserts "no allowlist entry", and turn every real entry into a
    ``stale-allowlist`` FAIL. An ABSENT allowlist is different and stays "[]"
    (genuinely nothing exempted) -- pinned by
    ``test_empty_repo_reports_ok`` above, which has no allowlist file."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "vendored.py").write_text("x = 1\n", encoding="utf-8")
    _write_allowlist(repo, [("vendored.py", "third-party, not ours")])
    _add_commit(repo)
    (repo / "scripts" / "spec_surface_allowlist.txt").write_bytes(b"caf\xe9\n")

    findings = chain.gather_spec_surface(repo)

    warns = [f for f in findings if f.check == "spec-surface-unevaluable"]
    assert any("spec_surface_allowlist.txt" in f.evidence["path"] for f in warns), (
        f"an unreadable allowlist did not surface as unevaluable: {findings}"
    )
    assert "ungoverned" not in {f.check for f in findings}
    assert "stale-allowlist" not in {f.check for f in findings}


def test_non_object_baseline_entry_does_not_hide_other_specs_findings(
    tmp_path: Path,
) -> None:
    """A baseline entry that is valid JSON but not an OBJECT (a stray string
    from a hand-edit) reaches ``b.get("memlog")``; unguarded, the
    ``AttributeError`` escapes to ``degrade_on_exception`` and discards every
    OTHER spec's already-computed finding behind one vacuous WARN."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_spec(repo, "pyforge-x", "spec-foo", surface=["governed.py"])
    (repo / "governed.py").write_text("x = 1\n", encoding="utf-8")
    _write_spec(repo, "pyforge-y", "spec-bar", surface=["other.py"])
    (repo / "other.py").write_text("y = 1\n", encoding="utf-8")
    _write_allowlist(repo, [("**", "everything, to keep this test on drift")])
    _write_baseline(repo, {"pyforge-x/spec-foo": "not-an-object"})
    _add_commit(repo)

    findings = chain.gather_spec_surface(repo)

    checks = {f.check for f in findings}
    assert "drift-blind" in checks, (
        f"a malformed baseline entry collapsed every real finding: {findings}"
    )
    # The malformed entry is treated as "no usable baseline for this spec".
    no_baseline = {f.evidence["path"] for f in findings if f.check == "no-baseline"}
    assert "pyforge-x/spec-foo" in no_baseline


# --- surface-drift modes ---------------------------------------------------------


def test_sentinel_drift_mode_moves_the_contract_hash_with_the_sentinel_file(
    tmp_path: Path,
) -> None:
    """``surface-drift: sentinel:<path>`` measures the contract against a
    named file instead of (only) the memlog. Changing the governed file after
    the sentinel moved is reconciled; changing it without the sentinel moving
    is ``drift``."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_spec(
        repo, "pyforge-x", "spec-foo",
        surface=["governed.py"], drift="sentinel:contract.json",
    )
    (repo / "contract.json").write_text('{"v": 1}\n', encoding="utf-8")
    (repo / "governed.py").write_text("x = 1\n", encoding="utf-8")
    _write_allowlist(repo, [("**", "everything, to keep this test on drift")])
    _add_commit(repo)

    before = chain._check_spec_surface(repo, chain._tracked_files(repo))
    state, _ = chain._spec_current_state(
        repo, *_specs_and_governed(repo)
    )
    _write_baseline(repo, state)
    _add_commit(repo)

    # Governed file changes, sentinel does not -> drift.
    (repo / "governed.py").write_text("x = 2\n", encoding="utf-8")
    _add_commit(repo)
    drifted = chain.gather_spec_surface(repo)
    assert "drift" in {f.check for f in drifted}, (
        f"sentinel mode did not gate an unreconciled change: {drifted}"
    )

    # Sentinel moves too -> the contract hash moves, so the change is not
    # `drift` any more (it becomes the non-gating `drift-presumed` unless the
    # sentinel names the path, which a JSON sentinel does not).
    (repo / "contract.json").write_text('{"v": 2}\n', encoding="utf-8")
    _add_commit(repo)
    reconciled = chain.gather_spec_surface(repo)
    assert "drift" not in {f.check for f in reconciled}, (
        f"the sentinel moved but drift still gated: {reconciled}"
    )
    assert before is not None  # the pre-baseline call ran without raising


def test_exempt_drift_mode_silences_drift_blind(tmp_path: Path) -> None:
    """``surface-drift: exempt`` opts a spec out of drift entirely, so a
    governed surface with no ``.memlog.md`` is NOT ``drift-blind``."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_spec(repo, "pyforge-x", "spec-foo", surface=["governed.py"], drift="exempt")
    (repo / "governed.py").write_text("x = 1\n", encoding="utf-8")
    _write_allowlist(repo, [("**", "everything, to keep this test on drift")])
    _add_commit(repo)  # no .memlog.md anywhere

    findings = chain.gather_spec_surface(repo)

    blind = {f.evidence["path"] for f in findings if f.check == "drift-blind"}
    assert "pyforge-x/spec-foo" not in blind, (
        f"an exempt spec was reported drift-blind: {findings}"
    )


def test_spec_governing_no_files_is_not_drift_blind(tmp_path: Path) -> None:
    """``drift-blind`` is about a governed surface with no contract behind it.
    A spec whose surface matches ZERO tracked files has nothing to reconcile,
    so a missing memlog is not yet a finding."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_spec(repo, "pyforge-x", "spec-foo", surface=["nothing/matches/this.py"])
    _write_allowlist(repo, [("**", "everything, to keep this test on drift")])
    _add_commit(repo)  # no .memlog.md, and the surface governs nothing

    findings = chain.gather_spec_surface(repo)

    # Asserted as an EXACT check set, not just "drift-blind is absent":
    # dropping the `governed.get(name)` condition makes the branch fire and
    # then raise `KeyError` on `governed[name]`, which `degrade_on_exception`
    # turns into a lone `spec-surface` WARN -- also a run with no drift-blind
    # in it, which the weaker assertion would have called a pass.
    assert {f.check for f in findings} == {"no-baseline"}, (
        f"a spec governing zero files did not produce the clean shape: {findings}"
    )


def test_surface_drift_exclude_keeps_a_governed_file_out_of_the_drift_hash(
    tmp_path: Path,
) -> None:
    """``surface-drift-exclude:`` names governed-but-regenerate-at-will files.
    They stay governed (never ``ungoverned``) but changing one must not
    produce ``drift``. The exclusion is an EXACT-path match, verbatim from the
    original's own ``f not in s["exclude"]``."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    sd = _write_spec(
        repo, "pyforge-x", "spec-foo",
        surface=["governed.py", "generated.lock"], exclude=["generated.lock"],
    )
    (sd / ".memlog.md").write_text("# memlog\n", encoding="utf-8")
    (repo / "governed.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "generated.lock").write_text("v1\n", encoding="utf-8")
    _write_allowlist(repo, [("**", "everything, to keep this test on drift")])
    _add_commit(repo)

    state, _ = chain._spec_current_state(repo, *_specs_and_governed(repo))
    assert "generated.lock" not in state["pyforge-x/spec-foo"]["files"], (
        "the excluded path was hashed into the drift state"
    )
    _write_baseline(repo, state)
    _add_commit(repo)

    (repo / "generated.lock").write_text("v2\n", encoding="utf-8")
    _add_commit(repo)

    findings = chain.gather_spec_surface(repo)

    assert "drift" not in {f.check for f in findings}, (
        f"an excluded path gated on drift: {findings}"
    )
    assert "generated.lock" not in {
        f.evidence["path"] for f in findings if f.check == "ungoverned"
    }


def _specs_and_governed(repo: Path) -> tuple[dict, dict]:
    """(specs, governed) for ``_spec_current_state``, rebuilt the same way
    ``_check_spec_surface`` does -- lets a test write a REAL baseline from the
    module's own hashing rather than hand-rolling sha1s that would drift."""
    specs: dict[str, dict] = {}
    for spec_md in sorted(repo.glob(chain.SPEC_GLOB)):
        project = spec_md.relative_to(repo).parts[2]
        name = f"{project}/{spec_md.parent.name}"
        globs, excludes, drift = chain._parse_surface(spec_md)
        specs[name] = {
            "globs": globs, "drift": drift, "exclude": set(excludes),
            "res": [chain._glob_to_re(g) for g in globs],
            "memlog": spec_md.parent / ".memlog.md",
        }
    files = chain._tracked_files(repo) or []
    governed, _, _ = chain._governed_and_ungoverned(files, specs, [])
    return specs, governed


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


# --- Unreadable inputs must not silently un-govern or silently un-gate ----------


def test_unlistable_specs_dir_is_unevaluable_not_silently_ungoverned(
    tmp_path: Path,
) -> None:
    """``Path.glob`` swallows ``OSError``, so an unreadable
    ``planning-artifacts/specs/`` used to read as "this project governs
    nothing" -- un-governing every file it really owns. It must name the
    project in a WARN instead."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    _write_spec(repo, "pyforge-dark", "spec-dark", surface=["owned.py"])
    (repo / "owned.py").write_text("x = 1\n", encoding="utf-8")
    _write_allowlist(repo, [])
    _add_commit(repo)
    dark = repo / "_bmad-output" / "projects" / "pyforge-dark" / "planning-artifacts" / "specs"
    dark.chmod(0o000)
    try:
        findings = chain.gather_spec_surface(repo)
    finally:
        dark.chmod(0o755)

    warns = [f for f in findings if f.check == "spec-surface-unevaluable"]
    assert any("pyforge-dark" in f.message for f in warns), (
        f"an unlistable specs/ dir went unreported: {findings}"
    )
    assert not any(
        f.check == "ungoverned" and f.evidence.get("path") == "owned.py"
        for f in findings
    ), f"a governed file was silently un-governed: {findings}"


def test_unreadable_spec_does_not_suppress_stale_allowlist(tmp_path: Path) -> None:
    """An unknown surface can only ever INFLATE an allowlist pattern's hit
    count (the dark spec claims nothing), so a pattern still at zero hits is
    genuinely stale and must keep gating. Suppressing coverage wholesale let
    one unreadable SPEC.md discard it."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    dark = _write_spec(repo, "pyforge-dark", "spec-dark", surface=["owned.py"])
    (repo / "owned.py").write_text("x = 1\n", encoding="utf-8")
    _write_allowlist(repo, [("gone/**", "matches nothing")])
    _add_commit(repo)
    (dark / "SPEC.md").write_bytes(b"---\nsurface:\n  - \xff\xfe\n---\n")

    findings = chain.gather_spec_surface(repo)

    by_check = {f.check for f in findings}
    assert "spec-surface-unevaluable" in by_check
    assert any(
        f.check == "stale-allowlist" and f.evidence.get("path") == "gone/**"
        for f in findings
    ), f"an unrelated spec's unreadable SPEC.md discarded a real FAIL: {findings}"


def test_suppressed_coverage_is_reported_not_silent(tmp_path: Path) -> None:
    """``ungoverned`` genuinely IS unsound under an unknown surface -- but
    dropping it without saying so turns "coverage could not be evaluated"
    into a report indistinguishable from "coverage is clean"."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    dark = _write_spec(repo, "pyforge-dark", "spec-dark", surface=["owned.py"])
    (repo / "owned.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "NOBODY_OWNS_THIS.py").write_text("x = 1\n", encoding="utf-8")
    _write_allowlist(repo, [])
    _add_commit(repo)
    (dark / "SPEC.md").write_bytes(b"---\nsurface:\n  - \xff\xfe\n---\n")

    findings = chain.gather_spec_surface(repo)

    assert any(
        f.check == "spec-surface-unevaluable" and "coverage suppressed" in f.message
        for f in findings
    ), f"coverage was suppressed silently: {[f.message for f in findings]}"


def test_present_but_unreadable_governed_file_is_unevaluable_not_removed(
    tmp_path: Path,
) -> None:
    """Dropping a PRESENT-but-unreadable governed file from the hash state is
    indistinguishable from the file being deleted, so the baseline diff
    reported it FAIL ``drift ... removed`` -- a confidently wrong finding
    about a file that is still right there."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    sd = _write_spec(repo, "pyforge-x", "spec-x", surface=["governed.py"])
    (sd / ".memlog.md").write_text("memlog\n", encoding="utf-8")
    governed = repo / "governed.py"
    governed.write_text("x = 1\n", encoding="utf-8")
    _write_allowlist(repo, [])
    _add_commit(repo)
    specs, gov = _specs_and_governed(repo)
    _write_baseline(repo, {
        n: {
            "memlog": chain._contract_hash(repo, s),
            "files": {f: chain._sha1(repo / f) for f in gov.get(n, [])},
        }
        for n, s in specs.items()
    })
    _add_commit(repo, "baseline")
    governed.chmod(0o000)
    try:
        findings = chain.gather_spec_surface(repo)
    finally:
        governed.chmod(0o644)

    assert not any("removed" in f.message for f in findings), (
        f"a present-but-unreadable file was reported removed: {findings}"
    )
    assert any(
        f.check == "spec-surface-unevaluable" and "pyforge-x/spec-x" in f.message
        for f in findings
    ), f"the unreadable governed file went unreported: {findings}"


def test_unreadable_memlog_is_unevaluable_not_downgraded_drift(tmp_path: Path) -> None:
    """A PRESENT-but-unreadable memlog collapsed the contract hash to ``""``,
    which never equals the baseline -- so ``spec_moved`` was unconditionally
    True and every gating ``drift`` FAIL silently became a non-gating
    ``drift-presumed`` WARN."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    sd = _write_spec(repo, "pyforge-x", "spec-x", surface=["governed.py"])
    memlog = sd / ".memlog.md"
    memlog.write_text("memlog\n", encoding="utf-8")
    governed = repo / "governed.py"
    governed.write_text("x = 1\n", encoding="utf-8")
    _write_allowlist(repo, [])
    _add_commit(repo)
    specs, gov = _specs_and_governed(repo)
    _write_baseline(repo, {
        n: {
            "memlog": chain._contract_hash(repo, s),
            "files": {f: chain._sha1(repo / f) for f in gov.get(n, [])},
        }
        for n, s in specs.items()
    })
    _add_commit(repo, "baseline")
    governed.write_text("x = 2  # real, unreconciled drift\n", encoding="utf-8")
    _add_commit(repo, "drift")
    memlog.chmod(0o000)
    try:
        findings = chain.gather_spec_surface(repo)
    finally:
        memlog.chmod(0o644)

    checks = {f.check for f in findings}
    assert "drift-presumed" not in checks, (
        f"a gating drift FAIL was silently downgraded: {findings}"
    )
    assert not any(f.status is DoctorStatus.OK for f in findings)
    assert "spec-surface-unevaluable" in checks


def test_baseline_entry_with_wrong_shaped_memlog_falls_back_to_no_baseline(
    tmp_path: Path,
) -> None:
    """A hand-edited baseline entry missing ``memlog`` (or carrying a
    list/null) compares unequal to every real contract hash, so ``spec_moved``
    was unconditionally True and real ``drift`` FAILs degraded to
    ``drift-presumed`` WARNs. Treat the entry as unusable instead -- the same
    shape guard the sibling ``files`` key already had."""
    repo = tmp_path / "repo"
    _init_repo(repo)
    sd = _write_spec(repo, "pyforge-x", "spec-x", surface=["governed.py"])
    (sd / ".memlog.md").write_text("memlog\n", encoding="utf-8")
    (repo / "governed.py").write_text("x = 1\n", encoding="utf-8")
    _write_allowlist(repo, [])
    _write_baseline(repo, {"pyforge-x/spec-x": {"files": {"governed.py": "deadbeef"}}})
    _add_commit(repo)

    findings = chain.gather_spec_surface(repo)

    by_check = {f.check for f in findings}
    assert "no-baseline" in by_check, (
        f"a wrong-shaped baseline entry was treated as usable: {findings}"
    )
    assert "drift-presumed" not in by_check
