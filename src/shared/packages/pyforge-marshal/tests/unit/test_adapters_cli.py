"""Unit tests for ``cli.adapters.run_adapters_sync`` (Story 6.2, FR-41,
AD-12/AD-36) against fake ``FsPort``/``HarnessPort`` doubles -- no real
filesystem, no real ``bmad_loop``."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from pyforge.marshal.adapters.fs_local import FsError
from pyforge.marshal.adapters.harness_bmadloop import HarnessError
from pyforge.marshal.cli import adapters as adapters_cli
from pyforge.marshal.ports.fs import AdvisoryLock
from pyforge.marshal.ports.harness import AdapterProbe

_HOME = Path("/fake/home/pyforge-marshal")
_CANONICAL = _HOME / ".claude" / "skills"
_MANIFEST = _HOME / ".bmad-loop" / "skill-projection.json"


class FakeFs:
    """Minimal in-memory ``FsPort`` double covering exactly what
    ``run_adapters_sync`` calls: ``is_dir``, ``exists``,
    ``read_symlink_target``, ``repoint_symlink_atomic``, ``remove_symlink``,
    ``ensure_dir``, ``resolve_path``, ``read_text``, ``write_text_atomic``."""

    def __init__(
        self,
        *,
        dirs: set[Path] | None = None,
        files: set[Path] | None = None,
        symlinks: dict[Path, Path] | None = None,
        texts: dict[Path, str] | None = None,
        dangling: set[Path] | None = None,
    ) -> None:
        self.dirs: set[Path] = set(dirs or set())
        self.files: set[Path] = set(files or set())
        self.symlinks: dict[Path, Path] = dict(symlinks or {})
        self.texts: dict[Path, str] = dict(texts or {})
        self.fail_repoint: dict[Path, Exception] = {}
        self.fail_remove: dict[Path, Exception] = {}
        self.fail_read_symlink: dict[Path, Exception] = {}
        self.fail_read_text: dict[Path, Exception] = {}
        self.fail_write_text: Exception | None = None
        self.fail_acquire_lock: Exception | None = None
        # Real `Path.exists()` FOLLOWS a symlink and reports False for a
        # dangling one, even though the link itself is present
        # (`is_symlink()` is True). This fake otherwise treats "is a
        # registered symlink key" as "exists", which cannot express that
        # distinction -- `dangling` is an explicit opt-in so a test can
        # model a broken link without changing every other test's implicit
        # "the symlink's target is real" assumption.
        self.dangling: set[Path] = set(dangling or set())

    def is_dir(self, path: Path) -> bool:
        return path in self.dirs

    def exists(self, path: Path) -> bool:
        if path in self.dangling:
            return False
        return path in self.dirs or path in self.files or path in self.symlinks

    def read_symlink_target(self, path: Path) -> Path | None:
        if path in self.fail_read_symlink:
            raise self.fail_read_symlink[path]
        return self.symlinks.get(path)

    def repoint_symlink_atomic(self, path: Path, target: Path) -> None:
        if path in self.fail_repoint:
            raise self.fail_repoint[path]
        if path in self.files:
            raise FsError(f"{path} is a real file/directory, not a symlink")
        self.symlinks[path] = target

    def remove_symlink(self, path: Path) -> bool:
        if path in self.fail_remove:
            raise self.fail_remove[path]
        if path not in self.symlinks:
            if path in self.files or path in self.dirs:
                raise FsError(f"{path} is a real file/directory, not a symlink")
            return False
        del self.symlinks[path]
        return True

    def ensure_dir(self, path: Path) -> None:
        self.dirs.add(path)

    def resolve_path(self, path: Path) -> Path:
        if path in self.symlinks:
            target = self.symlinks[path]
            resolved = target if target.is_absolute() else (path.parent / target)
            return _lexical_normalize(resolved)
        return _lexical_normalize(path)

    def read_text(self, path: Path) -> str | None:
        if path in self.fail_read_text:
            raise self.fail_read_text[path]
        return self.texts.get(path)

    def write_text_atomic(self, path: Path, content: str) -> None:
        if self.fail_write_text:
            raise self.fail_write_text
        self.texts[path] = content

    def write_redacted_atomic(self, path: Path, payload) -> None:
        """``RecordPort``'s fake -- Story 6.4. Stores the ALREADY-redacted
        ``payload.text`` (mirrors ``LocalFs.write_redacted_atomic``'s own
        "delegates entirely to write_text_atomic" shape)."""
        if self.fail_write_text:
            raise self.fail_write_text
        self.texts[path] = payload.text

    def acquire_advisory_lock(self, path: Path, *, timeout_s: float) -> AdvisoryLock:
        """A trivial in-memory fake -- Story 6.4's review fix. This
        double is exercised single-threaded, so no real mutual exclusion
        is needed; it only needs to satisfy the Protocol shape
        ``run_adapters_probe`` now calls. ``fail_acquire_lock`` lets a test
        simulate lock contention."""
        if self.fail_acquire_lock:
            raise self.fail_acquire_lock
        return AdvisoryLock(path=path, handle=object())

    def release_advisory_lock(self, lock: AdvisoryLock) -> None:
        pass


def _lexical_normalize(path: Path) -> Path:
    """Normalize ``..``/``.`` components without touching the real
    filesystem (``Path.resolve(strict=False)`` on an absolute, non-existent
    path is pure lexical normalization on every Python version this package
    targets)."""
    return path.resolve()


class FakeHarness:
    def __init__(
        self,
        skill_trees: dict[str, str] | None = None,
        fail: Exception | None = None,
        probe=None,
        probe_fail: Exception | None = None,
        smoke=None,
        smoke_fail: Exception | None = None,
        harness_version: str | None = "0.9.0",
    ) -> None:
        self._skill_trees = skill_trees or {}
        self._fail = fail
        self._probe = probe
        self._probe_fail = probe_fail
        self._smoke = smoke
        self._smoke_fail = smoke_fail
        self._harness_version = harness_version
        self.run_smoke_calls: list[dict] = []

    def adapter_skill_trees(self, project: Path) -> dict[str, str]:
        if self._fail:
            raise self._fail
        return dict(self._skill_trees)

    def adapter_probe(self, adapter_name: str, project: Path):
        if self._probe_fail:
            raise self._probe_fail
        return self._probe

    def harness_version(self) -> str | None:
        return self._harness_version

    def run_smoke(self, project: Path, *, adapter_name: str, story: str, timeout_s: float, log_path: Path):
        self.run_smoke_calls.append(
            {
                "project": project,
                "adapter_name": adapter_name,
                "story": story,
                "timeout_s": timeout_s,
                "log_path": log_path,
            }
        )
        if self._smoke_fail:
            raise self._smoke_fail
        return self._smoke


def _args(slug: str = "pyforge-marshal", fmt: str = "json") -> argparse.Namespace:
    return argparse.Namespace(slug=slug, format=fmt)


def _run(fs: FakeFs, harness: FakeHarness, slug: str = "pyforge-marshal") -> dict:
    code = adapters_cli.run_adapters_sync(_args(slug), fs=fs, harness=harness)
    return code


@pytest.fixture(autouse=True)
def _patch_home(monkeypatch):
    monkeypatch.setattr(adapters_cli, "_home_path", lambda slug: _HOME)


def _envelope_from(capsys) -> dict:
    out = capsys.readouterr().out
    return json.loads(out)


def test_malformed_slug_returns_error_finding(capsys):
    fs = FakeFs()
    harness = FakeHarness()
    code = adapters_cli.run_adapters_sync(_args(slug="../evil"), fs=fs, harness=harness)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-ADP-001" in codes
    assert code != 0


def test_home_not_provisioned_returns_error_finding(capsys):
    fs = FakeFs(dirs=set())  # _HOME itself absent
    harness = FakeHarness()
    _run(fs, harness)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-ADP-002" in codes


def test_canonical_missing_reports_error_but_still_proceeds(capsys):
    fs = FakeFs(dirs={_HOME})  # canonical NOT in dirs
    harness = FakeHarness({"codex": ".agents/skills"})
    _run(fs, harness)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-ADP-003" in codes
    assert envelope["data"]["projections"] == []


def test_first_sync_creates_symlink_for_non_canonical_tree(capsys):
    fs = FakeFs(dirs={_HOME, _CANONICAL})
    harness = FakeHarness({"codex": ".agents/skills", "claude": ".claude/skills"})
    _run(fs, harness)
    envelope = _envelope_from(capsys)
    assert envelope["findings"] == []
    projections = envelope["data"]["projections"]
    assert len(projections) == 1
    assert projections[0]["tree"] == ".agents/skills"
    assert projections[0]["action"] == "created"
    assert projections[0]["adapters"] == ["codex"]
    assert projections[0]["mechanism"] == "symlink"
    assert (_HOME / ".agents" / "skills") in fs.symlinks
    # manifest written
    assert _MANIFEST in fs.texts
    manifest = json.loads(fs.texts[_MANIFEST])
    assert ".agents/skills" in manifest["projected"]


def test_resync_with_nothing_changed_is_a_no_op(capsys):
    fs = FakeFs(dirs={_HOME, _CANONICAL})
    harness = FakeHarness({"codex": ".agents/skills"})
    _run(fs, harness)
    capsys.readouterr()  # discard the first run's own envelope
    first_manifest = fs.texts[_MANIFEST]
    fs.texts.clear()  # simulate: nothing else touches the manifest write path
    fs.texts[_MANIFEST] = first_manifest

    _run(fs, harness)
    envelope = _envelope_from(capsys)
    assert envelope["findings"] == []
    projections = envelope["data"]["projections"]
    assert projections[0]["action"] == "unchanged"
    # manifest content unchanged -> not rewritten again with a NEW value,
    # but write_text_atomic may still be called with identical content;
    # what matters is the reported action and that no finding fired.


def test_source_change_removes_old_tree_and_creates_new_one(capsys):
    old_tree = _HOME / ".other" / "skills"
    fs = FakeFs(
        dirs={_HOME, _CANONICAL},
        symlinks={old_tree: Path("../.claude/skills")},
        texts={
            _MANIFEST: json.dumps(
                {
                    "canonical": ".claude/skills",
                    "projected": {".other/skills": {"mechanism": "symlink", "target": "../.claude/skills"}},
                }
            )
        },
    )
    harness = FakeHarness({"codex": ".agents/skills"})
    _run(fs, harness)
    envelope = _envelope_from(capsys)
    assert envelope["findings"] == []
    actions = {p["tree"]: p["action"] for p in envelope["data"]["projections"]}
    assert actions[".agents/skills"] == "created"
    assert actions[".other/skills"] == "removed"
    assert old_tree not in fs.symlinks
    manifest = json.loads(fs.texts[_MANIFEST])
    assert ".other/skills" not in manifest["projected"]
    assert ".agents/skills" in manifest["projected"]


def test_create_conflict_real_file_at_tree_path_is_refused(capsys):
    tree_path = _HOME / ".agents" / "skills"
    fs = FakeFs(dirs={_HOME, _CANONICAL, tree_path})
    harness = FakeHarness({"codex": ".agents/skills"})
    _run(fs, harness)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-ADP-007" in codes
    projections = envelope["data"]["projections"]
    assert projections[0]["action"] == "conflict"


def test_remove_conflict_hand_repointed_symlink_is_kept(capsys):
    stale_tree = _HOME / ".other" / "skills"
    fs = FakeFs(
        dirs={_HOME, _CANONICAL},
        symlinks={stale_tree: Path("/somewhere/else")},
        texts={
            _MANIFEST: json.dumps(
                {"canonical": ".claude/skills", "projected": {".other/skills": {"mechanism": "symlink"}}}
            )
        },
    )
    harness = FakeHarness({})  # no adapter declares .other/skills any more
    _run(fs, harness)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-ADP-007" in codes
    projections = {p["tree"]: p["action"] for p in envelope["data"]["projections"]}
    assert projections[".other/skills"] == "conflict-kept"
    assert stale_tree in fs.symlinks  # untouched
    manifest = json.loads(fs.texts[_MANIFEST])
    assert ".other/skills" in manifest["projected"]  # still tracked, re-flagged next run


def test_dangling_stale_symlink_is_removed_not_silently_untracked(capsys):
    """Review finding (Blind Hunter): a dangling (broken) projected
    symlink -- e.g. left behind after the canonical tree it pointed at was
    deleted/renamed -- must be REMOVED, not silently dropped from the
    manifest while the broken link itself stays on disk forever. The old
    code used `fs.exists(tree_path)` (which FOLLOWS a symlink) to decide
    "already absent"; for a dangling link that is always False, so it took
    the wrong branch, popped the tree from the manifest, and never called
    `remove_symlink` -- an unrecoverable leak, since a tree no longer in
    the manifest is never revisited by a future run either."""
    stale_tree = _HOME / ".other" / "skills"
    fs = FakeFs(
        dirs={_HOME},  # note: no _CANONICAL -- it was deleted
        symlinks={stale_tree: Path("../.claude/skills")},
        dangling={stale_tree},
        texts={
            _MANIFEST: json.dumps(
                {"canonical": ".claude/skills", "projected": {".other/skills": {"mechanism": "symlink"}}}
            )
        },
    )
    harness = FakeHarness({})  # no adapter declares .other/skills any more
    _run(fs, harness)
    envelope = _envelope_from(capsys)
    projections = {p["tree"]: p["action"] for p in envelope["data"]["projections"]}
    assert projections[".other/skills"] == "removed"
    assert stale_tree not in fs.symlinks  # actually removed from disk, not just untracked
    manifest = json.loads(fs.texts[_MANIFEST])
    assert ".other/skills" not in manifest["projected"]


def test_absolute_skill_tree_is_refused_never_projected_outside_home(capsys):
    """Review finding (Blind Hunter): an adapter-declared (including a
    project-local profile overlay's) `skill_tree` was never confined to
    the loop home -- `home / Path(rel)` for an ABSOLUTE `rel` discards
    `home` entirely (`Path.__truediv__`'s own documented semantics), so a
    malicious/misconfigured overlay could make `sync` write a symlink
    anywhere the process can reach."""
    fs = FakeFs(dirs={_HOME, _CANONICAL})
    harness = FakeHarness({"evil": "/etc/cron.d/evil"})
    _run(fs, harness)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-ADP-011" in codes
    assert envelope["data"]["projections"] == []
    assert Path("/etc/cron.d/evil") not in fs.symlinks


def test_escaping_relative_skill_tree_is_refused_never_projected_outside_home(capsys):
    """Same class of finding as the absolute-path case, via `..` instead."""
    fs = FakeFs(dirs={_HOME, _CANONICAL})
    harness = FakeHarness({"evil": "../../../../etc/cron.d/evil"})
    _run(fs, harness)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-ADP-011" in codes
    assert envelope["data"]["projections"] == []


def test_adapter_enumeration_failure_reports_unevaluable_finding(capsys):
    fs = FakeFs(dirs={_HOME, _CANONICAL})
    harness = FakeHarness(fail=HarnessError("bmad_loop is not importable"))
    _run(fs, harness)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-ADP-004" in codes
    assert "projections" not in envelope["data"]


def test_unsupported_platform_takes_no_filesystem_action(capsys, monkeypatch):
    monkeypatch.setattr(adapters_cli.os, "name", "nt")
    fs = FakeFs(dirs={_HOME, _CANONICAL})
    harness = FakeHarness({"codex": ".agents/skills"})
    _run(fs, harness)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-ADP-005" in codes
    assert fs.symlinks == {}
    projections = envelope["data"]["projections"]
    assert projections[0]["action"] == "skipped-unsupported-platform"


def test_malformed_manifest_degrades_to_nothing_previously_projected(capsys):
    fs = FakeFs(dirs={_HOME, _CANONICAL}, texts={_MANIFEST: "{not json"})
    harness = FakeHarness({"codex": ".agents/skills"})
    _run(fs, harness)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-ADP-009" in codes
    projections = envelope["data"]["projections"]
    assert projections[0]["action"] == "created"


def test_per_tree_write_failure_is_isolated(capsys):
    tree_path = _HOME / ".agents" / "skills"
    fs = FakeFs(dirs={_HOME, _CANONICAL})
    fs.fail_repoint[tree_path] = FsError("permission denied")
    harness = FakeHarness({"codex": ".agents/skills"})
    _run(fs, harness)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-ADP-006" in codes
    projections = envelope["data"]["projections"]
    assert projections[0]["action"] == "failed"


def test_manifest_write_failure_degrades_without_blocking(capsys):
    fs = FakeFs(dirs={_HOME, _CANONICAL})
    fs.fail_write_text = FsError("disk full")
    harness = FakeHarness({"codex": ".agents/skills"})
    _run(fs, harness)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-ADP-010" in codes
    # the live symlink was still created despite the manifest write failing
    assert (_HOME / ".agents" / "skills") in fs.symlinks


def test_text_format_renders_without_crashing(capsys):
    fs = FakeFs(dirs={_HOME, _CANONICAL})
    harness = FakeHarness({"codex": ".agents/skills"})
    adapters_cli.run_adapters_sync(_args(fmt="text"), fs=fs, harness=harness)
    out = capsys.readouterr().out
    assert "adapters sync" in out


# --- Story 6.3: `marshal adapters conform` / `gather_conformance_findings` --


def _run_conform(fs: FakeFs, harness: FakeHarness, slug: str = "pyforge-marshal") -> int:
    return adapters_cli.run_adapters_conform(_args(slug), fs=fs, harness=harness)


def test_conform_nothing_desired_reports_no_findings(capsys):
    fs = FakeFs(dirs={_HOME, _CANONICAL})
    harness = FakeHarness({})
    _run_conform(fs, harness)
    envelope = _envelope_from(capsys)
    assert envelope["findings"] == []
    assert envelope["data"]["checks"] == []
    assert envelope["data"]["unevaluated_trees"] == []


def test_conform_after_sync_reports_confirmed_no_findings(capsys):
    fs = FakeFs(dirs={_HOME, _CANONICAL})
    harness = FakeHarness({"codex": ".agents/skills"})
    adapters_cli.run_adapters_sync(_args(fmt="json"), fs=fs, harness=harness)
    capsys.readouterr()  # discard sync's own envelope

    _run_conform(fs, harness)
    envelope = _envelope_from(capsys)
    assert envelope["findings"] == []
    checks = envelope["data"]["checks"]
    assert len(checks) == 1
    assert checks[0]["tree"] == ".agents/skills"
    assert checks[0]["status"] == "link-target-confirmed"


def test_conform_added_never_synced_reports_drift(capsys):
    fs = FakeFs(dirs={_HOME, _CANONICAL})
    harness = FakeHarness({"codex": ".agents/skills"})
    _run_conform(fs, harness)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-CONFORM-001" in codes
    checks = envelope["data"]["checks"]
    assert checks[0]["status"] == "added"


def test_gather_conformance_findings_never_synced_is_not_drift_when_asked(capsys):
    """Review finding (Edge Case Hunter, Story 6.4): `run_preflight`'s own
    unconditional call wires `treat_never_synced_as_drift=False` --
    otherwise a perfectly ordinary freshly-configured, not-yet-synced
    project (an "added" tree, never previously projected) failed preflight
    at ERROR on every routine invocation, a basic onboarding regression.
    `run_adapters_conform` (exercised by the sibling test just above) keeps
    the stricter default -- this proves the OTHER caller's own behavior
    directly against `gather_conformance_findings` rather than only via
    `cli/init.py`'s own integration-level wiring."""
    fs = FakeFs(dirs={_HOME, _CANONICAL})
    harness = FakeHarness({"codex": ".agents/skills"})
    data, findings = adapters_cli.gather_conformance_findings(
        _HOME, fs=fs, harness=harness, treat_never_synced_as_drift=False
    )
    codes = {f.code for f in findings}
    assert "MRS-CONFORM-001" not in codes
    # The full truth is still reported in `data` -- only the FINDING
    # (which drives verdict/exit-code) is suppressed for this shape.
    assert data["checks"][0]["status"] == "added"


def test_conform_removed_deleted_out_of_band_reports_drift(capsys):
    fs = FakeFs(
        dirs={_HOME, _CANONICAL},
        texts={
            _MANIFEST: json.dumps(
                {"canonical": ".claude/skills", "projected": {".agents/skills": {"mechanism": "symlink"}}}
            )
        },
    )
    harness = FakeHarness({"codex": ".agents/skills"})
    _run_conform(fs, harness)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-CONFORM-001" in codes
    checks = envelope["data"]["checks"]
    assert checks[0]["status"] == "removed"


def test_conform_modified_retargeted_reports_drift(capsys):
    tree_path = _HOME / ".agents" / "skills"
    fs = FakeFs(
        dirs={_HOME, _CANONICAL},
        symlinks={tree_path: Path("/somewhere/else")},
        texts={
            _MANIFEST: json.dumps(
                {"canonical": ".claude/skills", "projected": {".agents/skills": {"mechanism": "symlink"}}}
            )
        },
    )
    harness = FakeHarness({"codex": ".agents/skills"})
    _run_conform(fs, harness)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-CONFORM-001" in codes
    checks = envelope["data"]["checks"]
    assert checks[0]["status"] == "modified"


def test_conform_modified_real_content_reports_drift(capsys):
    tree_path = _HOME / ".agents" / "skills"
    fs = FakeFs(
        dirs={_HOME, _CANONICAL, tree_path},
        texts={
            _MANIFEST: json.dumps(
                {"canonical": ".claude/skills", "projected": {".agents/skills": {"mechanism": "symlink"}}}
            )
        },
    )
    harness = FakeHarness({"codex": ".agents/skills"})
    _run_conform(fs, harness)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-CONFORM-001" in codes
    checks = envelope["data"]["checks"]
    assert checks[0]["status"] == "modified"


def test_conform_canonical_missing_reports_error_but_still_checks(capsys):
    fs = FakeFs(dirs={_HOME})  # canonical NOT in dirs; something IS desired
    harness = FakeHarness({"codex": ".agents/skills"})
    _run_conform(fs, harness)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-ADP-003" in codes
    assert "MRS-CONFORM-001" in codes  # never-synced tree still reported as drift


def test_conform_adapter_enumeration_failure_reports_unevaluable(capsys):
    fs = FakeFs(dirs={_HOME, _CANONICAL})
    harness = FakeHarness(fail=HarnessError("bmad_loop is not importable"))
    _run_conform(fs, harness)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-ADP-004" in codes


def test_conform_unsupported_platform_reports_unevaluable_never_confirmed(capsys, monkeypatch):
    monkeypatch.setattr(adapters_cli.os, "name", "nt")
    fs = FakeFs(dirs={_HOME, _CANONICAL})
    harness = FakeHarness({"codex": ".agents/skills"})
    _run_conform(fs, harness)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-ADP-005" in codes
    assert envelope["data"]["checks"] == []
    assert ".agents/skills" in envelope["data"]["unevaluated_trees"]


def test_conform_unsupported_platform_still_reports_a_previously_projected_only_tree(
    capsys, monkeypatch
):
    """Review finding (Edge Case Hunter): `plan.unsupported_trees` alone is
    scoped to the CURRENTLY DESIRED set (Story 6.2's own `plan_projection`
    contract) -- a tree that is previously-projected but no longer desired
    by any configured adapter would silently vanish from both the
    MRS-ADP-005 finding and `unevaluated_trees` if that were the only
    source consulted, reporting structurally the same as "nothing to
    check" even though a real, previously-projected tree's live symlink
    state was never read or compared. No adapter declares `.agents/skills`
    any more (a deconfigured adapter), yet the manifest still tracks it."""
    monkeypatch.setattr(adapters_cli.os, "name", "nt")
    fs = FakeFs(
        dirs={_HOME, _CANONICAL},
        texts={
            _MANIFEST: json.dumps(
                {"canonical": ".claude/skills", "projected": {".agents/skills": {"mechanism": "symlink"}}}
            )
        },
    )
    harness = FakeHarness({})  # no adapter declares anything any more
    _run_conform(fs, harness)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-ADP-005" in codes
    assert envelope["data"]["checks"] == []
    assert ".agents/skills" in envelope["data"]["unevaluated_trees"]


def test_conform_unreadable_symlink_state_degrades_to_a_finding_never_crashes(capsys):
    """Review finding (Blind Hunter): unlike every other `FsError`-raising
    call in this module, `read_symlink_target` was unguarded here -- an
    unsearchable ancestor directory (a real, documented `LocalFs` failure
    mode on this package's own Python 3.12 floor) would have propagated a
    raw `FsError` straight out of `gather_conformance_findings`. Since that
    function now runs UNCONDITIONALLY as part of `marshal preflight`, an
    unguarded I/O failure here would crash the whole preflight command
    instead of degrading to a finding."""
    tree_path = _HOME / ".agents" / "skills"
    fs = FakeFs(dirs={_HOME, _CANONICAL})
    fs.fail_read_symlink[tree_path] = FsError("permission denied: unsearchable ancestor")
    harness = FakeHarness({"codex": ".agents/skills"})
    exit_code = _run_conform(fs, harness)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-ADP-012" in codes
    assert ".agents/skills" in envelope["data"]["unevaluated_trees"]
    assert envelope["data"]["checks"] == []
    assert exit_code != 0  # a real, reported error -- never a silent pass


def test_conform_malformed_manifest_degrades_gracefully(capsys):
    fs = FakeFs(dirs={_HOME, _CANONICAL}, texts={_MANIFEST: "{not json"})
    harness = FakeHarness({"codex": ".agents/skills"})
    _run_conform(fs, harness)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-ADP-009" in codes
    assert "MRS-CONFORM-001" in codes  # treated as never-synced -> added


def test_conform_confinement_refusal_reused(capsys):
    fs = FakeFs(dirs={_HOME, _CANONICAL})
    harness = FakeHarness({"evil": "/etc/cron.d/evil"})
    _run_conform(fs, harness)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-ADP-011" in codes
    assert envelope["data"]["checks"] == []


def test_conform_malformed_slug_returns_error_finding(capsys):
    fs = FakeFs()
    harness = FakeHarness()
    adapters_cli.run_adapters_conform(_args(slug="../evil"), fs=fs, harness=harness)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-ADP-001" in codes


def test_conform_home_not_provisioned_returns_error_finding(capsys):
    fs = FakeFs(dirs=set())
    harness = FakeHarness()
    _run_conform(fs, harness)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-ADP-002" in codes


def test_conform_text_format_renders_without_crashing(capsys):
    fs = FakeFs(dirs={_HOME, _CANONICAL})
    harness = FakeHarness({"codex": ".agents/skills"})
    adapters_cli.run_adapters_conform(_args(fmt="text"), fs=fs, harness=harness)
    out = capsys.readouterr().out
    assert "adapters conform" in out
    assert ".agents/skills" in out


# --- Story 6.4: `marshal adapters probe` ------------------------------------

_PROBE_STATE_PATH = Path("/fake/state/pyforge-marshal") / "adapter-probes.json"


def _probe_args(slug: str = "pyforge-marshal", fmt: str = "json", adapter: str = "claude") -> argparse.Namespace:
    return argparse.Namespace(slug=slug, format=fmt, adapter=adapter)


def _available_probe(adapter: str = "claude") -> AdapterProbe:
    return AdapterProbe(
        adapter=adapter,
        binary=adapter,
        binary_present=True,
        binary_version="1.0.0",
        capabilities={"hookless": False},
        probe_output='{"schema_version": 2}',
        probe_note=None,
    )


def _unavailable_probe(adapter: str = "codex") -> AdapterProbe:
    return AdapterProbe(
        adapter=adapter,
        binary=adapter,
        binary_present=False,
        binary_version=None,
        capabilities={"hookless": False},
        probe_output=None,
        probe_note="binary not found on PATH",
    )


@pytest.fixture(autouse=True)
def _patch_machine_state_dir(monkeypatch):
    monkeypatch.setattr(adapters_cli, "_machine_state_dir", lambda: _PROBE_STATE_PATH.parent)


def _run_probe(fs: FakeFs, harness: FakeHarness, slug: str = "pyforge-marshal", adapter: str = "claude") -> int:
    return adapters_cli.run_adapters_probe(_probe_args(slug, adapter=adapter), fs=fs, harness=harness, record=fs)


def test_probe_available_adapter_reports_available_no_findings(capsys):
    fs = FakeFs(dirs={_HOME})
    harness = FakeHarness(probe=_available_probe())
    code = _run_probe(fs, harness)
    envelope = _envelope_from(capsys)
    assert envelope["findings"] == []
    assert envelope["data"]["probe"]["status"] == "available"
    assert envelope["data"]["probe"]["binary_version"] == "1.0.0"
    assert code == 0


def test_probe_unavailable_adapter_reports_unavailable_and_exits_zero(capsys):
    fs = FakeFs(dirs={_HOME})
    harness = FakeHarness(probe=_unavailable_probe())
    code = _run_probe(fs, harness, adapter="codex")
    envelope = _envelope_from(capsys)
    assert envelope["findings"] == []
    assert envelope["data"]["probe"]["status"] == "unavailable"
    assert code == 0


def test_probe_writes_the_redacted_record_to_the_machine_scoped_path(capsys):
    fs = FakeFs(dirs={_HOME})
    harness = FakeHarness(probe=_available_probe())
    _run_probe(fs, harness)
    _envelope_from(capsys)
    assert _PROBE_STATE_PATH in fs.texts
    written = json.loads(fs.texts[_PROBE_STATE_PATH])
    assert written["claude"]["status"] == "available"


def test_probe_write_is_never_a_bare_write_text_atomic(capsys):
    """AD-34: the write MUST go through ``RecordPort.write_redacted_atomic``,
    never ``FsPort.write_text_atomic`` -- both are the SAME fake object
    here, but only the redacted path is exercised (``write_text_atomic``
    would also satisfy this fake, so this test asserts the RECORD's shape
    is valid JSON produced by ``to_redacted``, not merely present)."""
    fs = FakeFs(dirs={_HOME})
    harness = FakeHarness(probe=_available_probe())
    _run_probe(fs, harness)
    _envelope_from(capsys)
    # to_redacted's own json.dumps(sort_keys=True) shape -- keys sorted.
    raw = fs.texts[_PROBE_STATE_PATH]
    assert list(json.loads(raw).keys()) == sorted(json.loads(raw).keys())


def test_probe_merges_into_an_existing_record_preserving_other_adapters(capsys):
    fs = FakeFs(
        dirs={_HOME},
        texts={_PROBE_STATE_PATH: json.dumps({"codex": {"status": "unavailable"}})},
    )
    harness = FakeHarness(probe=_available_probe())
    _run_probe(fs, harness)
    _envelope_from(capsys)
    written = json.loads(fs.texts[_PROBE_STATE_PATH])
    assert written["codex"]["status"] == "unavailable"
    assert written["claude"]["status"] == "available"


def test_probe_malformed_existing_record_degrades_to_empty_with_warn(capsys):
    fs = FakeFs(dirs={_HOME}, texts={_PROBE_STATE_PATH: "{not json"})
    harness = FakeHarness(probe=_available_probe())
    _run_probe(fs, harness)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-ADP-016" in codes
    written = json.loads(fs.texts[_PROBE_STATE_PATH])
    assert written["claude"]["status"] == "available"


def test_probe_unknown_adapter_reports_error_finding(capsys):
    fs = FakeFs(dirs={_HOME})
    harness = FakeHarness(probe_fail=HarnessError("unknown adapter"))
    code = _run_probe(fs, harness)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-ADP-014" in codes
    assert code != 0


def test_probe_missing_adapter_flag_reports_error_finding_no_touch(capsys):
    fs = FakeFs(dirs={_HOME})
    harness = FakeHarness(probe=_available_probe())
    adapters_cli.run_adapters_probe(_probe_args(adapter=""), fs=fs, harness=harness, record=fs)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-ADP-013" in codes
    assert _PROBE_STATE_PATH not in fs.texts


def test_probe_malformed_slug_returns_error_finding(capsys):
    fs = FakeFs()
    harness = FakeHarness(probe=_available_probe())
    adapters_cli.run_adapters_probe(_probe_args(slug="../evil"), fs=fs, harness=harness, record=fs)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-ADP-001" in codes


def test_probe_home_not_provisioned_returns_error_finding(capsys):
    fs = FakeFs(dirs=set())
    harness = FakeHarness(probe=_available_probe())
    _run_probe(fs, harness)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-ADP-002" in codes


def test_probe_write_failure_reports_error_finding_but_still_reports_the_observation(capsys):
    fs = FakeFs(dirs={_HOME})
    fs.fail_write_text = FsError("disk full")
    harness = FakeHarness(probe=_available_probe())
    _run_probe(fs, harness)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-ADP-015" in codes
    assert envelope["data"]["probe"]["status"] == "available"


def test_probe_lock_contention_reports_error_finding_writes_nothing(capsys):
    """Review finding (Blind Hunter): two concurrent `marshal adapters
    probe` invocations for DIFFERENT adapters share the read-merge-write
    cycle against `adapter-probes.json` -- without a lock, the second
    writer silently clobbers the first's already-succeeded observation.
    Guarded by the same injectable `FsPort.acquire_advisory_lock` pair
    `cli/deploy.py::run_promote` established; a contended lock reports
    MRS-ADP-015 and performs no write, rather than racing anyway."""
    fs = FakeFs(dirs={_HOME})
    fs.fail_acquire_lock = FsError("simulated: another process holds this lock")
    harness = FakeHarness(probe=_available_probe())
    _run_probe(fs, harness)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-ADP-015" in codes
    assert _PROBE_STATE_PATH not in fs.texts


def test_probe_text_format_renders_without_crashing(capsys):
    fs = FakeFs(dirs={_HOME})
    harness = FakeHarness(probe=_available_probe())
    adapters_cli.run_adapters_probe(_probe_args(fmt="text"), fs=fs, harness=harness, record=fs)
    out = capsys.readouterr().out
    assert "adapters probe" in out
    assert "available" in out



# --- Story 6.5: `marshal adapters smoke` ------------------------------------
#
# `_provision_smoke_home` calls `write_policy_toml` DIRECTLY (the same real,
# non-FsPort disk I/O `cli/spin.py`'s own `_resolve_model_tiering` already
# uses, mirroring that module's own test convention) -- so `home` here is a
# genuine directory under pytest's `tmp_path` sandbox, never a purely
# in-memory fake path. `FakeFs` still stands in for every OTHER write this
# command makes (the ephemeral marker, the synthetic sprint-status.yaml/spec,
# the machine-scoped smoke record).

from pyforge.marshal.adapters.vcs_git import VcsCommandError
from pyforge.marshal.ports.harness import SmokeRunResult

_SMOKE_REPO_ROOT = Path("/fake/repo")
_SMOKE_STATE_PATH = Path("/fake/state/pyforge-marshal") / "adapter-smoke.json"
_SMOKE_SLUG = "_smoke-claude-cafefeed"
_SMOKE_BRANCH = f"loop/{_SMOKE_SLUG}"


class FakeSmokeVcs:
    """Minimal in-memory ``VcsPort`` double covering exactly what
    ``run_adapters_smoke`` calls: ``repo_common_root``, ``add_worktree``,
    ``worktree_head_sha``, ``remove_worktree``, ``delete_branch``."""

    def __init__(self, *, head_shas: list[str] | None = None) -> None:
        self.repo_root = _SMOKE_REPO_ROOT
        self.calls: list[str] = []
        self.add_worktree_calls: list[tuple] = []
        self.remove_worktree_calls: list[tuple] = []
        self.delete_branch_calls: list[tuple] = []
        self.fail_repo_common_root: Exception | None = None
        self.fail_add_worktree: Exception | None = None
        self.fail_remove_worktree: Exception | None = None
        self.fail_delete_branch: Exception | None = None
        self.fail_worktree_head_sha: Exception | None = None
        # How many of the NEXT `worktree_head_sha` calls raise
        # `fail_worktree_head_sha` before succeeding normally -- `-1` (the
        # default) means "raise on every call, forever"; a positive count
        # simulates a transient failure that clears itself after N calls.
        self.fail_worktree_head_sha_times = -1
        # Popped in call order; the SAME sha twice (the default) means "no
        # commit advanced" -- a test wanting `commit_made=True` supplies two
        # distinct shas.
        self._head_shas = list(head_shas) if head_shas is not None else ["sha-a", "sha-a"]
        self._head_index = 0

    def repo_common_root(self, start: Path) -> Path:
        self.calls.append("repo_common_root")
        if self.fail_repo_common_root:
            raise self.fail_repo_common_root
        return self.repo_root

    def add_worktree(self, repo_root: Path, home: Path, branch: str, *, base: str) -> None:
        self.calls.append("add_worktree")
        self.add_worktree_calls.append((repo_root, home, branch, base))
        if self.fail_add_worktree:
            raise self.fail_add_worktree
        home.mkdir(parents=True, exist_ok=True)

    def worktree_head_sha(self, worktree_path: Path) -> str:
        self.calls.append("worktree_head_sha")
        if self.fail_worktree_head_sha is not None and self.fail_worktree_head_sha_times != 0:
            if self.fail_worktree_head_sha_times > 0:
                self.fail_worktree_head_sha_times -= 1
            raise self.fail_worktree_head_sha
        index = min(self._head_index, len(self._head_shas) - 1)
        self._head_index += 1
        return self._head_shas[index]

    def remove_worktree(self, repo_root: Path, home: Path, *, force: bool = False) -> None:
        self.calls.append("remove_worktree")
        self.remove_worktree_calls.append((repo_root, home, force))
        if self.fail_remove_worktree:
            raise self.fail_remove_worktree

    def delete_branch(self, repo_root: Path, branch: str, *, force: bool = False) -> None:
        self.calls.append("delete_branch")
        self.delete_branch_calls.append((repo_root, branch, force))
        if self.fail_delete_branch:
            raise self.fail_delete_branch


@pytest.fixture(autouse=True)
def _patch_smoke_home_root_and_token(tmp_path, monkeypatch):
    """Makes the ephemeral smoke home's path fully deterministic (a real
    directory under ``tmp_path``, since ``write_policy_toml`` performs real
    disk I/O -- see this section's own header comment) -- ``run_adapters_
    smoke`` otherwise mints a random 8-hex-char suffix per invocation."""
    monkeypatch.setattr(adapters_cli, "_loop_home_root", lambda: tmp_path / "loop-homes")
    monkeypatch.setattr(adapters_cli.secrets, "token_hex", lambda n: "cafefeed")
    monkeypatch.setattr(adapters_cli, "_machine_state_dir", lambda: _SMOKE_STATE_PATH.parent)


def _smoke_home(tmp_path: Path) -> Path:
    return tmp_path / "loop-homes" / _SMOKE_SLUG


def _smoke_args(fmt: str = "json", adapter: str = "claude", timeout_seconds: float = 900.0) -> argparse.Namespace:
    return argparse.Namespace(adapter=adapter, format=fmt, timeout_seconds=timeout_seconds)


def _pass_smoke(adapter: str = "claude") -> SmokeRunResult:
    return SmokeRunResult(
        adapter=adapter, binary=adapter, binary_present=True, launched=True, returncode=0, timed_out=False
    )


def _pass_fs(tmp_path: Path, *, texts: dict[Path, str] | None = None) -> FakeFs:
    """A `FakeFs` whose `SMOKE.md` already carries the marker line -- the
    file-changed evidence `evaluate_smoke` now requires (alongside
    `commit_made` and a clean `returncode`) before it reports PASS (review
    finding: `commit_made` alone used to be sufficient corroboration)."""
    seeded = {_smoke_home(tmp_path) / "SMOKE.md": "marshal-conformance-smoke: ok\n"}
    if texts:
        seeded.update(texts)
    return FakeFs(texts=seeded)


def _unavailable_smoke(adapter: str = "codex") -> SmokeRunResult:
    return SmokeRunResult(
        adapter=adapter, binary=adapter, binary_present=False, launched=False, returncode=None, timed_out=False
    )


def _run_smoke(
    fs: FakeFs,
    harness: FakeHarness,
    vcs: FakeSmokeVcs,
    *,
    adapter: str = "claude",
    fmt: str = "json",
) -> int:
    return adapters_cli.run_adapters_smoke(
        _smoke_args(fmt=fmt, adapter=adapter), fs=fs, harness=harness, vcs=vcs, record=fs
    )


def test_smoke_pass_when_commit_advances_no_findings_teardown_runs(capsys, tmp_path):
    fs = _pass_fs(tmp_path)
    harness = FakeHarness(smoke=_pass_smoke())
    vcs = FakeSmokeVcs(head_shas=["sha-1", "sha-2"])
    code = _run_smoke(fs, harness, vcs)
    envelope = _envelope_from(capsys)
    assert envelope["findings"] == []
    assert envelope["data"]["smoke"]["status"] == "pass"
    assert envelope["data"]["smoke"]["failing_stage"] is None
    assert code == 0
    home = _smoke_home(tmp_path)
    # teardown ALWAYS runs, even on a clean pass
    assert vcs.remove_worktree_calls == [(_SMOKE_REPO_ROOT, home, True)]
    assert vcs.delete_branch_calls == [(_SMOKE_REPO_ROOT, _SMOKE_BRANCH, True)]
    # the machine-scoped record was written
    written = json.loads(fs.texts[_SMOKE_STATE_PATH])
    assert written["claude"]["status"] == "pass"


def test_smoke_unavailable_adapter_reports_unavailable_and_exits_zero(capsys):
    fs = FakeFs()
    harness = FakeHarness(smoke=_unavailable_smoke())
    vcs = FakeSmokeVcs()
    code = _run_smoke(fs, harness, vcs, adapter="codex")
    envelope = _envelope_from(capsys)
    assert envelope["findings"] == []
    assert envelope["data"]["smoke"]["status"] == "unavailable"
    assert code == 0
    assert vcs.remove_worktree_calls  # teardown still runs


def test_smoke_fail_no_change_no_commit_names_change_stage(capsys):
    fs = FakeFs()
    harness = FakeHarness(smoke=_pass_smoke())  # binary present, launched, but no evidence
    vcs = FakeSmokeVcs()  # same sha twice -> no commit
    code = _run_smoke(fs, harness, vcs)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-SMOKE-003" in codes
    assert envelope["data"]["smoke"]["status"] == "fail"
    assert envelope["data"]["smoke"]["failing_stage"] == "change"
    assert code != 0


def test_smoke_fail_change_without_commit_names_verify_stage(capsys, tmp_path):
    target = _smoke_home(tmp_path) / "SMOKE.md"
    fs = FakeFs(texts={target: "marshal-conformance-smoke: ok\n"})
    harness = FakeHarness(smoke=_pass_smoke())
    vcs = FakeSmokeVcs()  # same sha twice -> no commit
    code = _run_smoke(fs, harness, vcs)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-SMOKE-003" in codes
    assert envelope["data"]["smoke"]["failing_stage"] == "verify"
    assert code != 0


def test_smoke_unknown_adapter_reports_unevaluable_finding_teardown_still_runs(capsys):
    fs = FakeFs()
    harness = FakeHarness(smoke_fail=HarnessError("unknown adapter"))
    vcs = FakeSmokeVcs()
    code = _run_smoke(fs, harness, vcs)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-SMOKE-001" in codes
    assert code != 0
    assert vcs.remove_worktree_calls  # teardown still runs despite the raised HarnessError


def test_smoke_missing_adapter_flag_reports_unevaluable_no_provisioning_touch(capsys):
    fs = FakeFs()
    harness = FakeHarness(smoke=_pass_smoke())
    vcs = FakeSmokeVcs()
    code = adapters_cli.run_adapters_smoke(_smoke_args(adapter=""), fs=fs, harness=harness, vcs=vcs, record=fs)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-SMOKE-005" in codes
    assert code != 0
    assert vcs.calls == []  # no git touch at all


def test_smoke_provisioning_failure_reports_error_finding(capsys):
    fs = FakeFs()
    harness = FakeHarness(smoke=_pass_smoke())
    vcs = FakeSmokeVcs()
    vcs.fail_add_worktree = VcsCommandError("simulated: cannot create worktree")
    code = _run_smoke(fs, harness, vcs)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-SMOKE-002" in codes
    assert code != 0
    # never reached the harness at all
    assert harness.run_smoke_calls == []


def test_smoke_add_worktree_failure_attempts_best_effort_teardown(capsys):
    """Review finding: `GitVcs.add_worktree`'s own docstring documents that
    a timeout can leave a REGISTERED, partial worktree/branch behind even
    though it raised -- an ephemeral smoke home promises to leave no
    residue (AD-37), so `_add_smoke_worktree` must attempt cleanup of any
    partial state before re-raising, not just when a LATER step fails."""
    fs = FakeFs()
    harness = FakeHarness(smoke=_pass_smoke())
    vcs = FakeSmokeVcs()
    vcs.fail_add_worktree = VcsCommandError("simulated: timed out mid-checkout")
    code = _run_smoke(fs, harness, vcs)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-SMOKE-002" in codes
    assert code != 0
    # best-effort teardown was attempted even though provisioning itself failed
    assert vcs.remove_worktree_calls
    assert vcs.delete_branch_calls


def test_smoke_transient_pre_sha_read_failure_is_retried_and_still_detects_a_commit(capsys, tmp_path):
    """Review finding: a single transient `worktree_head_sha` read failure
    before the harness ran used to permanently pin `pre_sha` to `None`,
    making `commit_made` unconditionally `False` for the rest of the run --
    misreporting a genuine PASS as FAIL. One retry must recover from a
    failure that clears itself."""
    fs = _pass_fs(tmp_path)
    harness = FakeHarness(smoke=_pass_smoke())
    vcs = FakeSmokeVcs(head_shas=["sha-1", "sha-2"])
    vcs.fail_worktree_head_sha = VcsCommandError("simulated: transient read failure")
    vcs.fail_worktree_head_sha_times = 1  # fails once (the pre-run read), then recovers
    code = _run_smoke(fs, harness, vcs)
    envelope = _envelope_from(capsys)
    assert envelope["findings"] == []
    assert envelope["data"]["smoke"]["status"] == "pass"
    assert code == 0


def test_smoke_scaffold_materialization_failure_after_worktree_created_still_tears_down(capsys):
    """Regression (self-caught during implementation): scaffold
    materialization (marker/sprint-status/spec/policy writes) happens AFTER
    the git worktree already exists -- a failure there must still trigger
    teardown, or the worktree/branch leaks as residue, directly
    contradicting the AC's own "leaves no residue afterwards"."""
    fs = FakeFs()
    fs.fail_write_text = FsError("simulated: disk full mid-scaffold")
    harness = FakeHarness(smoke=_pass_smoke())
    vcs = FakeSmokeVcs()
    code = _run_smoke(fs, harness, vcs)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-SMOKE-002" in codes
    assert code != 0
    # the harness was never called (scaffold never completed)...
    assert harness.run_smoke_calls == []
    # ...but the worktree/branch it already created WAS torn down
    assert vcs.remove_worktree_calls
    assert vcs.delete_branch_calls


def test_smoke_teardown_failure_reports_warn_never_overrides_pass_verdict(capsys, tmp_path):
    fs = _pass_fs(tmp_path)
    harness = FakeHarness(smoke=_pass_smoke())
    vcs = FakeSmokeVcs(head_shas=["sha-1", "sha-2"])
    vcs.fail_remove_worktree = VcsCommandError("simulated: worktree busy")
    code = _run_smoke(fs, harness, vcs)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-SMOKE-004" in codes
    assert envelope["data"]["smoke"]["status"] == "pass"
    assert code == 0  # a WARN-only finding set still folds to the exit-0 rung


def test_smoke_write_failure_reports_error_but_still_reports_the_observation(capsys, tmp_path):
    fs = _pass_fs(tmp_path)
    harness = FakeHarness(smoke=_pass_smoke())
    vcs = FakeSmokeVcs(head_shas=["sha-1", "sha-2"])

    real_write_redacted_atomic = fs.write_redacted_atomic

    def _fail_only_state_write(path, payload):
        if path == _SMOKE_STATE_PATH:
            raise FsError("disk full")
        return real_write_redacted_atomic(path, payload)

    fs.write_redacted_atomic = _fail_only_state_write  # type: ignore[method-assign]
    code = _run_smoke(fs, harness, vcs)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-SMOKE-006" in codes
    assert envelope["data"]["smoke"]["status"] == "pass"


def test_smoke_lock_contention_reports_error_finding_writes_nothing(capsys):
    fs = FakeFs()
    fs.fail_acquire_lock = FsError("simulated: another process holds this lock")
    harness = FakeHarness(smoke=_pass_smoke())
    vcs = FakeSmokeVcs(head_shas=["sha-1", "sha-2"])
    _run_smoke(fs, harness, vcs)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-SMOKE-006" in codes
    assert _SMOKE_STATE_PATH not in fs.texts


def test_smoke_malformed_existing_record_degrades_to_empty_with_warn(capsys, tmp_path):
    fs = _pass_fs(tmp_path, texts={_SMOKE_STATE_PATH: "{not json"})
    harness = FakeHarness(smoke=_pass_smoke())
    vcs = FakeSmokeVcs(head_shas=["sha-1", "sha-2"])
    _run_smoke(fs, harness, vcs)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-SMOKE-007" in codes
    written = json.loads(fs.texts[_SMOKE_STATE_PATH])
    assert written["claude"]["status"] == "pass"


def test_smoke_merges_into_existing_record_preserving_other_adapters(capsys, tmp_path):
    fs = _pass_fs(tmp_path, texts={_SMOKE_STATE_PATH: json.dumps({"codex": {"status": "unavailable"}})})
    harness = FakeHarness(smoke=_pass_smoke())
    vcs = FakeSmokeVcs(head_shas=["sha-1", "sha-2"])
    _run_smoke(fs, harness, vcs)
    _envelope_from(capsys)
    written = json.loads(fs.texts[_SMOKE_STATE_PATH])
    assert written["codex"]["status"] == "unavailable"
    assert written["claude"]["status"] == "pass"


def test_smoke_forces_the_configured_adapter_into_the_rendered_policy(capsys, tmp_path):
    fs = FakeFs()
    harness = FakeHarness(smoke=_pass_smoke())
    vcs = FakeSmokeVcs(head_shas=["sha-1", "sha-2"])
    _run_smoke(fs, harness, vcs)
    _envelope_from(capsys)
    rendered = (_smoke_home(tmp_path) / ".bmad-loop" / "policy.toml").read_text(encoding="utf-8")
    assert 'name = "claude"' in rendered


def test_smoke_writes_ephemeral_marker(capsys, tmp_path):
    fs = FakeFs()
    harness = FakeHarness(smoke=_pass_smoke())
    vcs = FakeSmokeVcs(head_shas=["sha-1", "sha-2"])
    _run_smoke(fs, harness, vcs)
    _envelope_from(capsys)
    assert (_smoke_home(tmp_path) / ".marshal-ephemeral") in fs.texts


def test_smoke_writes_synthetic_scaffold_via_fs(capsys, tmp_path):
    fs = FakeFs()
    harness = FakeHarness(smoke=_pass_smoke())
    vcs = FakeSmokeVcs(head_shas=["sha-1", "sha-2"])
    _run_smoke(fs, harness, vcs)
    _envelope_from(capsys)
    impl_dir = _smoke_home(tmp_path) / "_bmad-output" / "implementation-artifacts"
    assert impl_dir / "sprint-status.yaml" in fs.texts
    assert "ready-for-dev" in fs.texts[impl_dir / "sprint-status.yaml"]
    assert impl_dir / "spec-1-1-marshal-conformance-smoke.md" in fs.texts


def test_smoke_text_format_renders_without_crashing(capsys):
    fs = FakeFs()
    harness = FakeHarness(smoke=_unavailable_smoke())
    vcs = FakeSmokeVcs()
    _run_smoke(fs, harness, vcs, adapter="codex", fmt="text")
    out = capsys.readouterr().out
    assert "adapters smoke" in out
    assert "unavailable" in out


def test_smoke_written_record_carries_harness_version_and_recorded_at(capsys, tmp_path):
    """Story 6.6 (FR-45): the smoke's own machine-scoped record now carries
    the two facts `run_adapters_matrix` later accumulates -- only ever
    truthfully known at smoke time."""
    fs = _pass_fs(tmp_path)
    harness = FakeHarness(smoke=_pass_smoke(), harness_version="0.9.0")
    vcs = FakeSmokeVcs(head_shas=["sha-1", "sha-2"])
    _run_smoke(fs, harness, vcs)
    _envelope_from(capsys)
    written = json.loads(fs.texts[_SMOKE_STATE_PATH])
    assert written["claude"]["harness_version"] == "0.9.0"
    assert written["claude"]["recorded_at"] is not None


# =====================================================================
# ``marshal adapters matrix`` (Story 6.6, FR-45/SM-6/AD-31/AD-37).
# =====================================================================

_MATRIX_ROOT = Path("/fake/repo")
_MATRIX_NOW = datetime(2026, 8, 7, tzinfo=timezone.utc)


def _matrix_args(slug: str = "pyforge-marshal", fmt: str = "json", stale_after_days: int = 30) -> argparse.Namespace:
    return argparse.Namespace(slug=slug, format=fmt, stale_after_days=stale_after_days)


@pytest.fixture
def _patch_matrix(monkeypatch):
    monkeypatch.setattr(adapters_cli, "_machine_state_dir", lambda: _PROBE_STATE_PATH.parent)
    monkeypatch.setattr(adapters_cli, "repo_root", lambda: _MATRIX_ROOT)
    monkeypatch.setattr(adapters_cli.socket, "gethostname", lambda: "host1")
    monkeypatch.setattr(adapters_cli, "_now_utc", lambda: _MATRIX_NOW)


def _matrix_path(slug: str = "pyforge-marshal") -> Path:
    return (
        _MATRIX_ROOT
        / "_bmad-output"
        / "projects"
        / slug
        / "planning-artifacts"
        / "conformance"
        / "matrix"
        / "host1.md"
    )


def test_matrix_malformed_slug_returns_error_finding(capsys, _patch_matrix):
    fs = FakeFs()
    code = adapters_cli.run_adapters_matrix(_matrix_args(slug="../evil"), fs=fs)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-ADP-001" in codes
    assert code != 0


def test_matrix_fresh_host_writes_empty_matrix(capsys, _patch_matrix):
    fs = FakeFs()
    code = adapters_cli.run_adapters_matrix(_matrix_args(), fs=fs)
    envelope = _envelope_from(capsys)
    assert envelope["findings"] == []
    assert envelope["data"]["rows"] == []
    assert code == 0
    assert _matrix_path() in fs.texts
    assert "host1" in fs.texts[_matrix_path()]


def test_matrix_reports_pass_fail_unavailable_not_attempted(capsys, _patch_matrix):
    fs = FakeFs(
        texts={
            _PROBE_STATE_PATH: json.dumps(
                {
                    "claude": {"binary_version": "1.0.0"},
                    "codex": {"binary_version": "2.0.0"},
                    "never-smoked": {"binary_version": "9.9.9"},
                }
            ),
            _SMOKE_STATE_PATH: json.dumps(
                {
                    "claude": {
                        "status": "pass",
                        "failing_stage": None,
                        "harness_version": "0.9.0",
                        "recorded_at": "2026-08-06T00:00:00+00:00",
                    },
                    "codex": {
                        "status": "unavailable",
                        "failing_stage": None,
                        "harness_version": None,
                        "recorded_at": "2026-08-06T00:00:00+00:00",
                    },
                    "gemini": {
                        "status": "fail",
                        "failing_stage": "verify",
                        "harness_version": "0.9.0",
                        "recorded_at": "2026-08-06T00:00:00+00:00",
                    },
                }
            ),
        }
    )
    code = adapters_cli.run_adapters_matrix(_matrix_args(), fs=fs)
    envelope = _envelope_from(capsys)
    assert envelope["findings"] == []
    assert code == 0
    rows = {row["adapter"]: row for row in envelope["data"]["rows"]}
    assert rows["claude"]["status"] == "pass"
    assert rows["claude"]["adapter_version"] == "1.0.0"
    assert rows["codex"]["status"] == "unavailable"
    assert rows["gemini"]["status"] == "fail"
    assert rows["gemini"]["failing_stage"] == "verify"
    assert rows["never-smoked"]["status"] == "not-attempted"
    written = fs.texts[_matrix_path()]
    for adapter in ("claude", "codex", "gemini", "never-smoked"):
        assert adapter in written


def test_matrix_marks_stale_rows(capsys, _patch_matrix):
    fs = FakeFs(
        texts={
            _SMOKE_STATE_PATH: json.dumps(
                {"claude": {"status": "pass", "recorded_at": "2020-01-01T00:00:00+00:00"}}
            )
        }
    )
    code = adapters_cli.run_adapters_matrix(_matrix_args(stale_after_days=30), fs=fs)
    envelope = _envelope_from(capsys)
    assert code == 0
    rows = {row["adapter"]: row for row in envelope["data"]["rows"]}
    assert rows["claude"]["stale"] is True


def test_matrix_malformed_probe_state_reports_matrix_001_and_still_uses_smoke_state(capsys, _patch_matrix):
    fs = FakeFs(
        texts={
            _PROBE_STATE_PATH: "{not json",
            _SMOKE_STATE_PATH: json.dumps({"claude": {"status": "pass", "recorded_at": "2026-08-06T00:00:00+00:00"}}),
        }
    )
    code = adapters_cli.run_adapters_matrix(_matrix_args(), fs=fs)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-MATRIX-001" in codes
    rows = {row["adapter"]: row for row in envelope["data"]["rows"]}
    assert rows["claude"]["status"] == "pass"
    assert code == 0


def test_matrix_write_failure_reports_error_but_still_reports_rows(capsys, _patch_matrix):
    fs = FakeFs(
        texts={_SMOKE_STATE_PATH: json.dumps({"claude": {"status": "pass", "recorded_at": "2026-08-06T00:00:00+00:00"}})}
    )
    fs.fail_write_text = FsError("disk full")
    code = adapters_cli.run_adapters_matrix(_matrix_args(), fs=fs)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-MATRIX-002" in codes
    assert code != 0
    rows = {row["adapter"]: row for row in envelope["data"]["rows"]}
    assert rows["claude"]["status"] == "pass"
    assert _matrix_path() not in fs.texts


def test_matrix_text_format_renders_without_crashing(capsys, _patch_matrix):
    fs = FakeFs(
        texts={_SMOKE_STATE_PATH: json.dumps({"claude": {"status": "pass", "recorded_at": "2026-08-06T00:00:00+00:00"}})}
    )
    adapters_cli.run_adapters_matrix(_matrix_args(fmt="text"), fs=fs)
    out = capsys.readouterr().out
    assert "adapters matrix" in out
    assert "claude" in out


def test_matrix_written_content_matches_render_matrix_markdown(capsys, _patch_matrix):
    from pyforge.marshal.core.conformance import build_matrix_row, render_matrix_markdown

    fs = FakeFs(
        texts={_SMOKE_STATE_PATH: json.dumps({"claude": {"status": "pass", "recorded_at": "2026-08-06T00:00:00+00:00"}})}
    )
    adapters_cli.run_adapters_matrix(_matrix_args(), fs=fs)
    envelope = _envelope_from(capsys)
    written = fs.texts[_matrix_path()]
    row = build_matrix_row(
        "claude",
        smoke_record={"status": "pass", "recorded_at": "2026-08-06T00:00:00+00:00"},
        probe_record=None,
        now=_MATRIX_NOW,
        stale_after_days=30,
    )
    # Structural equivalence, not byte-identity (generated_at is a live
    # clock read this test cannot pin) -- same rows, same table shape.
    expected = render_matrix_markdown([row], hostname="host1", generated_at="ignored")
    assert written.splitlines()[4:] == expected.splitlines()[4:]
    assert envelope["data"]["hostname"] == "host1"


# =====================================================================
# ``marshal adapters entry-files`` (Story 6.7, FR-46/C-3/AD-11).
# =====================================================================

_ENTRY_ROOT = Path("/fake/entry-repo")


def _entry_args(fmt: str = "json") -> argparse.Namespace:
    return argparse.Namespace(format=fmt)


@pytest.fixture
def _patch_entry_files(monkeypatch):
    monkeypatch.setattr(adapters_cli, "repo_root", lambda: _ENTRY_ROOT)


def _consistent_entry_texts() -> dict[Path, str]:
    from pyforge.marshal.core.conformance import ENTRY_FILE_FAMILY

    texts: dict[Path, str] = {_ENTRY_ROOT / ENTRY_FILE_FAMILY[0]: "the hub, AGENTS.md\n"}
    for path in ENTRY_FILE_FAMILY[1:]:
        texts[_ENTRY_ROOT / path] = f"see AGENTS.md for the full rules\n"
    return texts


def test_entry_files_all_consistent_reports_no_finding(capsys, _patch_entry_files):
    fs = FakeFs(texts=_consistent_entry_texts())
    code = adapters_cli.run_adapters_entry_files(_entry_args(), fs=fs)
    envelope = _envelope_from(capsys)
    assert envelope["findings"] == []
    assert envelope["data"]["divergences"] == []
    assert code == 0


def test_entry_files_missing_satellite_reports_mrs_entry_001(capsys, _patch_entry_files):
    texts = _consistent_entry_texts()
    del texts[_ENTRY_ROOT / ".cursor/rules/specs.mdc"]
    fs = FakeFs(texts=texts)
    code = adapters_cli.run_adapters_entry_files(_entry_args(), fs=fs)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-ENTRY-001" in codes
    assert code == 0  # WARN exits 0 -- a detect-only advisory, never blocking
    divergences = {d["path"]: d for d in envelope["data"]["divergences"]}
    assert ".cursor/rules/specs.mdc" in divergences
    assert divergences[".cursor/rules/specs.mdc"]["cross_contaminating"] is False


def test_entry_files_missing_hub_names_claude_as_cross_contaminating(capsys, _patch_entry_files):
    from pyforge.marshal.core.conformance import ENTRY_FILE_FAMILY

    texts = _consistent_entry_texts()
    del texts[_ENTRY_ROOT / ENTRY_FILE_FAMILY[0]]
    fs = FakeFs(texts=texts)
    adapters_cli.run_adapters_entry_files(_entry_args(), fs=fs)
    envelope = _envelope_from(capsys)
    divergences = {d["path"]: d for d in envelope["data"]["divergences"]}
    assert divergences[ENTRY_FILE_FAMILY[0]]["cross_contaminating"] is True
    assert "claude" in divergences[ENTRY_FILE_FAMILY[0]]["affected_tools"]


def test_entry_files_drifted_satellite_no_longer_mentioning_hub(capsys, _patch_entry_files):
    texts = _consistent_entry_texts()
    texts[_ENTRY_ROOT / "CLAUDE.md"] = "totally standalone content, no cross-reference\n"
    fs = FakeFs(texts=texts)
    adapters_cli.run_adapters_entry_files(_entry_args(), fs=fs)
    envelope = _envelope_from(capsys)
    divergences = {d["path"]: d for d in envelope["data"]["divergences"]}
    assert "CLAUDE.md" in divergences
    assert "no longer references" in divergences["CLAUDE.md"]["detail"]


def test_entry_files_never_writes(capsys, _patch_entry_files):
    """A detect-only command -- no mutator call ever fires, regardless of
    how many divergences are found."""
    texts = _consistent_entry_texts()
    del texts[_ENTRY_ROOT / "GEMINI.md"]
    fs = FakeFs(texts=texts)
    adapters_cli.run_adapters_entry_files(_entry_args(), fs=fs)
    _envelope_from(capsys)
    assert fs.symlinks == {}
    # write_text_atomic's own store is `texts` -- assert it holds ONLY the
    # seeded family-member content, never a new/rewritten entry.
    assert set(fs.texts.keys()) == set(texts.keys())


def test_entry_files_unreadable_family_member_degrades_to_absent_never_crashes(capsys, _patch_entry_files):
    """Self-review finding: `fs.read_text` can raise `FsError` for a real
    read failure (permission error, path naming a directory) -- distinct
    from its `None` 'does not exist' return. An unguarded call would crash
    this detect-only command entirely; it must degrade to the same
    'absent' shape instead."""
    texts = _consistent_entry_texts()
    fs = FakeFs(texts=texts)
    fs.fail_read_text = {_ENTRY_ROOT / "GEMINI.md": FsError("permission denied")}
    code = adapters_cli.run_adapters_entry_files(_entry_args(), fs=fs)
    envelope = _envelope_from(capsys)
    codes = {f["code"] for f in envelope["findings"]}
    assert "MRS-ENTRY-001" in codes
    divergences = {d["path"]: d for d in envelope["data"]["divergences"]}
    assert "GEMINI.md" in divergences
    assert code == 0


def test_entry_files_text_format_renders_without_crashing(capsys, _patch_entry_files):
    texts = _consistent_entry_texts()
    del texts[_ENTRY_ROOT / "GEMINI.md"]
    fs = FakeFs(texts=texts)
    adapters_cli.run_adapters_entry_files(_entry_args(fmt="text"), fs=fs)
    out = capsys.readouterr().out
    assert "adapters entry-files" in out
    assert "GEMINI.md" in out
