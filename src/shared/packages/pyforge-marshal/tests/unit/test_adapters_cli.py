"""Unit tests for ``cli.adapters.run_adapters_sync`` (Story 6.2, FR-41,
AD-12/AD-36) against fake ``FsPort``/``HarnessPort`` doubles -- no real
filesystem, no real ``bmad_loop``."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from pyforge.marshal.adapters.fs_local import FsError
from pyforge.marshal.adapters.harness_bmadloop import HarnessError
from pyforge.marshal.cli import adapters as adapters_cli

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
        self.fail_write_text: Exception | None = None
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
        return self.texts.get(path)

    def write_text_atomic(self, path: Path, content: str) -> None:
        if self.fail_write_text:
            raise self.fail_write_text
        self.texts[path] = content


def _lexical_normalize(path: Path) -> Path:
    """Normalize ``..``/``.`` components without touching the real
    filesystem (``Path.resolve(strict=False)`` on an absolute, non-existent
    path is pure lexical normalization on every Python version this package
    targets)."""
    return path.resolve()


class FakeHarness:
    def __init__(self, skill_trees: dict[str, str] | None = None, fail: Exception | None = None) -> None:
        self._skill_trees = skill_trees or {}
        self._fail = fail

    def adapter_skill_trees(self, project: Path) -> dict[str, str]:
        if self._fail:
            raise self._fail
        return dict(self._skill_trees)


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
