"""Story 77.1 (spec-pyforge-marshal CAP-282, dispatch half of the
``structure-graph`` layer): ``_seed_dispatch_structure_graph`` gives each new
dispatch worktree a codegraph index -- a copy of the primary checkout's base
index, then ``codegraph sync -q`` -- instead of the ``codegraph init -y`` per
worktree Story 28.31 measured at ~19 s and ~222 MiB.

Every row of the story's I/O matrix runs against a fake ``ProcessPort`` (which
records each argv, cwd and ceiling, and can create or fail the index) and a
fake ``FsPort`` over real bytes under ``tmp_path``. ``probe_instrument`` is
monkeypatched at the ``pyforge.marshal.cli.dispatch`` call site, the shape
``test_dispatch_output_layer.py`` uses for the same seam, so the whole matrix
runs without ``codegraph`` installed. The one real-binary test is
``tests/integration/test_dispatch_structure_graph_real.py``.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import pytest
from pyforge.core.process import ProcessError, ProcessResult
from test_dispatch import FakeBuildHarness, FakeFs, FakeProcess, FakeVcs, _init_git_repo

import pyforge.marshal.cli.dispatch as dispatch_module
from pyforge.marshal.adapters.fs_local import FsError
from pyforge.marshal.cli.dispatch import StructureGraphSeed, run_dispatch
from pyforge.marshal.core import dispatch as dispatch_core
from pyforge.marshal.core import policy
from pyforge.marshal.core.model import Severity
from pyforge.marshal.core.verdict import EXIT_OK
from pyforge.marshal.seed.detect.kit import InstrumentProbe
from pyforge.marshal.seed.verbs.kit import INDEX_TIMEOUT_S, SYNC_TIMEOUT_S

_ENABLED = {"structure-graph": {"enabled": True, "aggressiveness": "medium"}}
_BOOTSTRAP = "pixi run -e pyforge-guild marshal context bootstrap"
_DB = Path(".codegraph") / "codegraph.db"


class _Fs:
    """The ``FsPort`` slice the seed uses, over real files under ``tmp_path``."""

    def __init__(self, *, fail_copy_of: str | None = None) -> None:
        self.copies: list[tuple[Path, Path]] = []
        self._fail_copy_of = fail_copy_of

    def exists(self, path: Path) -> bool:
        return path.exists()

    def copy_file(self, src: Path, dst: Path) -> None:
        if self._fail_copy_of is not None and src.name == self._fail_copy_of:
            raise FsError(f"cannot copy {src} to {dst}: disk full")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        self.copies.append((src, dst))

    def remove_empty_dir(self, path: Path) -> bool:
        try:
            path.rmdir()
        except OSError:
            return False
        return True


class _Process:
    """A ``ProcessPort`` fake for ``codegraph``: records ``(argv, cwd,
    timeout_s)`` and, per verb, either runs a behavior or succeeds. The
    default ``init`` creates ``<cwd>/.codegraph/codegraph.db``, as the real
    verb does; the default ``sync`` leaves the index as it found it."""

    def __init__(self, *, sync=None, init=None) -> None:
        self.calls: list[tuple[list[str], Path, float | None]] = []
        self.db_present_at_call: list[bool] = []
        self._behaviors = {"sync": sync or self._ok, "init": init or self._create_index}

    @staticmethod
    def _ok(argv: list[str], cwd: Path) -> ProcessResult:
        return ProcessResult(returncode=0, stdout="", stderr="")

    @staticmethod
    def _create_index(argv: list[str], cwd: Path) -> ProcessResult:
        (cwd / _DB).parent.mkdir(parents=True, exist_ok=True)
        (cwd / _DB).write_bytes(b"built")
        return ProcessResult(returncode=0, stdout="", stderr="")

    def run(self, argv, *, cwd: Path, timeout_s: float | None = None) -> ProcessResult:
        argv = list(argv)
        self.calls.append((argv, cwd, timeout_s))
        self.db_present_at_call.append((cwd / _DB).exists())
        return self._behaviors[argv[1]](argv, cwd)

    @property
    def verbs(self) -> list[str]:
        return [argv[1] for argv, _cwd, _timeout in self.calls]


def _fail(returncode: int, stderr: str):
    return lambda argv, cwd: ProcessResult(returncode=returncode, stdout="", stderr=stderr)


def _timeout(ceiling: float):
    def behavior(argv: list[str], cwd: Path) -> ProcessResult:
        raise ProcessError(f"command timed out after {ceiling}s: {' '.join(argv)}")

    return behavior


@pytest.fixture(autouse=True)
def _codegraph_on_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dispatch_module, "probe_instrument", lambda item: InstrumentProbe(available=True))


def _primary(tmp_path: Path, *, base: bool = True) -> Path:
    repo = tmp_path / "primary"
    repo.mkdir()
    if base:
        index = repo / ".codegraph"
        index.mkdir()
        (index / "codegraph.db").write_bytes(b"base-db-bytes")
        (index / "codegraph.db-wal").write_bytes(b"base-wal")
        (index / "codegraph.db-shm").write_bytes(b"base-shm")
        (index / ".gitignore").write_text("*\n", encoding="utf-8")
        (index / "sub").mkdir()
        (index / "sub" / "nested.bin").write_bytes(b"nested")
    return repo


def _seed(
    tmp_path: Path,
    *,
    repo: Path,
    fs: _Fs | None = None,
    process: _Process | None = None,
    payload=_ENABLED,
) -> tuple[StructureGraphSeed, Path, _Fs, _Process]:
    worktree = tmp_path / "worktree"
    worktree.mkdir(exist_ok=True)
    fs = fs or _Fs()
    process = process or _Process()
    result = dispatch_module._seed_dispatch_structure_graph(
        fs=fs, process=process, worktree=worktree, repo_root=repo, context_payload=payload
    )
    return result, worktree, fs, process


def _snapshot(directory: Path) -> dict[str, tuple[int, int]]:
    return {
        str(path.relative_to(directory)): (path.stat().st_size, path.stat().st_mtime_ns)
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    }


# -- layer off ---------------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        {"structure-graph": {"enabled": False, "aggressiveness": "medium"}},
        {"structure-graph": {"enabled": "auto", "aggressiveness": "medium"}},
        {},
    ],
    ids=["disabled", "unresolved-auto", "absent"],
)
def test_layer_off_copies_and_runs_nothing(tmp_path: Path, payload) -> None:
    repo = _primary(tmp_path)

    result, worktree, fs, process = _seed(tmp_path, repo=repo, payload=payload)

    assert result == StructureGraphSeed()
    assert result.journal_payload() == {"applied": False, "mode": "skipped", "reason": None, "seconds": 0.0}
    assert result.findings == ()
    assert fs.copies == [] and process.calls == []
    assert not (worktree / ".codegraph").exists()


# -- base present -> copy, then sync -----------------------------------------


def test_base_present_copies_the_index_and_syncs_never_inits(tmp_path: Path) -> None:
    repo = _primary(tmp_path)

    result, worktree, fs, process = _seed(tmp_path, repo=repo)

    assert process.calls == [(["codegraph", "sync", "-q", str(worktree)], worktree, SYNC_TIMEOUT_S)]
    assert "init" not in process.verbs
    assert result.applied is True and result.mode == "sync" and result.reason is None
    assert result.findings == ()
    payload = result.journal_payload()
    assert set(payload) == {"applied", "mode", "reason", "seconds"}
    assert isinstance(payload["seconds"], float) and payload["seconds"] >= 0.0
    # The whole directory travels -- the db, its sqlite sidecars, a nested file -- as real bytes.
    for relative in ("codegraph.db", "codegraph.db-wal", "codegraph.db-shm", ".gitignore", "sub/nested.bin"):
        source, copied = repo / ".codegraph" / relative, worktree / ".codegraph" / relative
        assert copied.read_bytes() == source.read_bytes()
        assert not copied.is_symlink()
    # The copy is in place before the sync runs: the fake recorded the db at call time.
    assert process.db_present_at_call == [True]


def test_a_symlink_in_the_base_is_skipped_not_copied(tmp_path: Path) -> None:
    repo = _primary(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    (repo / ".codegraph" / "escape").symlink_to(outside)
    (repo / ".codegraph" / "escape-dir").symlink_to(tmp_path)

    result, worktree, fs, _process = _seed(tmp_path, repo=repo)

    assert result.mode == "sync"
    assert not (worktree / ".codegraph" / "escape").exists()
    assert not (worktree / ".codegraph" / "escape-dir").exists()
    assert all(source.name not in {"escape", "outside.txt"} for source, _dst in fs.copies)


def test_provisioning_never_changes_the_primary_checkouts_index(tmp_path: Path) -> None:
    repo = _primary(tmp_path)
    before = _snapshot(repo)

    _result, _worktree, _fs, _process = _seed(tmp_path, repo=repo)

    assert _snapshot(repo) == before  # same files, same size, same mtime_ns
    assert not any(str(path).startswith(str(repo)) for _src, path in _fs.copies)


def test_a_failed_provisioning_run_also_leaves_the_primary_untouched(tmp_path: Path) -> None:
    repo = _primary(tmp_path)
    before = _snapshot(repo)

    _seed(tmp_path, repo=repo, process=_Process(sync=_fail(1, "corrupt"), init=_fail(1, "boom")))

    assert _snapshot(repo) == before


# -- a re-dispatched worktree keeps its own index ----------------------------


def test_a_worktree_that_already_holds_an_index_is_synced_and_never_copied_over(tmp_path: Path) -> None:
    repo = _primary(tmp_path)
    worktree = tmp_path / "worktree"
    (worktree / ".codegraph").mkdir(parents=True)
    (worktree / _DB).write_bytes(b"the worktree's own index")

    result, worktree, fs, process = _seed(tmp_path, repo=repo)

    assert fs.copies == []
    assert process.verbs == ["sync"]
    assert (worktree / _DB).read_bytes() == b"the worktree's own index"
    assert result.applied is True and result.mode == "sync" and result.reason is None


def test_a_sync_timeout_on_an_existing_worktree_index_leaves_that_index_in_place(tmp_path: Path) -> None:
    repo = _primary(tmp_path)
    worktree = tmp_path / "worktree"
    (worktree / ".codegraph").mkdir(parents=True)
    (worktree / _DB).write_bytes(b"the worktree's own index")

    result, worktree, _fs, process = _seed(tmp_path, repo=repo, process=_Process(sync=_timeout(SYNC_TIMEOUT_S)))

    assert result.mode == "skipped" and result.reason == "timeout"
    assert (worktree / _DB).read_bytes() == b"the worktree's own index"
    assert process.verbs == ["sync"]
    [finding] = result.findings
    assert finding.code == "MRS-DISP-054"
    assert "existing codegraph index was left in place, unsynced (possibly stale)" in finding.message
    assert "runs without a codegraph index" not in finding.message


def test_a_sync_failure_on_an_existing_worktree_index_does_not_init_over_it(tmp_path: Path) -> None:
    """``codegraph init -y`` over an existing ``.codegraph/`` exits 0 having done
    nothing (measured 2026-09-29), so it would journal a build that never ran;
    and the index is the session's own to keep."""
    repo = _primary(tmp_path)
    worktree = tmp_path / "worktree"
    (worktree / ".codegraph").mkdir(parents=True)
    (worktree / _DB).write_bytes(b"the worktree's own index")

    result, worktree, _fs, process = _seed(tmp_path, repo=repo, process=_Process(sync=_fail(1, "db is locked")))

    assert process.verbs == ["sync"]
    assert result.applied is False and result.mode == "skipped"
    assert "db is locked" in (result.reason or "")
    assert [f.code for f in result.findings] == ["MRS-DISP-054"]
    assert "existing codegraph index was left in place, unsynced (possibly stale)" in result.findings[0].message
    assert "runs without a codegraph index" not in result.findings[0].message
    assert (worktree / _DB).read_bytes() == b"the worktree's own index"


# -- no base -> init, and a WARN naming the fix ------------------------------


def test_no_base_index_inits_in_the_worktree_and_names_bootstrap(tmp_path: Path) -> None:
    repo = _primary(tmp_path, base=False)

    result, worktree, fs, process = _seed(tmp_path, repo=repo)

    assert process.calls == [(["codegraph", "init", "-y", str(worktree)], worktree, INDEX_TIMEOUT_S)]
    assert fs.copies == []
    assert result.applied is True and result.mode == "init"
    assert result.reason is not None and "no base index" in result.reason
    [finding] = result.findings
    assert finding.code == "MRS-DISP-053" and finding.severity is Severity.WARN
    assert _BOOTSTRAP in finding.message
    assert (worktree / _DB).is_file()


def test_a_base_directory_without_a_db_counts_as_no_base(tmp_path: Path) -> None:
    repo = _primary(tmp_path, base=False)
    (repo / ".codegraph").mkdir()
    (repo / ".codegraph" / "stray.txt").write_text("not an index", encoding="utf-8")

    result, _worktree, fs, process = _seed(tmp_path, repo=repo)

    assert process.verbs == ["init"] and fs.copies == []
    assert result.mode == "init"


# -- no binary ----------------------------------------------------------------


def test_no_codegraph_binary_skips_with_a_named_warning_and_touches_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        dispatch_module,
        "probe_instrument",
        lambda item: InstrumentProbe(
            available=False, reason="codegraph is not installed here ('codegraph' is not on PATH)"
        ),
    )
    repo = _primary(tmp_path)

    result, worktree, fs, process = _seed(tmp_path, repo=repo)

    assert result.applied is False and result.mode == "skipped"
    assert result.reason is not None and "'codegraph' is not on PATH" in result.reason
    [finding] = result.findings
    assert finding.code == "MRS-DISP-054" and finding.severity is Severity.WARN
    assert "'codegraph' is not on PATH" in finding.message
    assert fs.copies == [] and process.calls == []
    assert not (worktree / ".codegraph").exists()


# -- failure ladder ------------------------------------------------------------


def test_a_failed_sync_of_the_copied_base_falls_back_to_init_once_over_a_cleared_index(tmp_path: Path) -> None:
    repo = _primary(tmp_path)

    result, worktree, _fs, process = _seed(
        tmp_path, repo=repo, process=_Process(sync=_fail(1, "database disk image is malformed"))
    )

    assert process.verbs == ["sync", "init"]
    # `codegraph init -y` no-ops over an existing `.codegraph/`, so the copied index is gone by then.
    assert process.db_present_at_call == [True, False]
    assert result.applied is True and result.mode == "init"
    assert result.reason is not None and "database disk image is malformed" in result.reason
    [finding] = result.findings
    assert finding.code == "MRS-DISP-053" and finding.severity is Severity.WARN
    assert "database disk image is malformed" in finding.message and _BOOTSTRAP in finding.message
    assert (worktree / _DB).read_bytes() == b"built"
    assert not (worktree / ".codegraph" / "codegraph.db-wal").exists()


def test_a_sync_timeout_ends_in_skipped_with_no_init_fallback_and_no_index_left(tmp_path: Path) -> None:
    repo = _primary(tmp_path)

    result, worktree, _fs, process = _seed(tmp_path, repo=repo, process=_Process(sync=_timeout(SYNC_TIMEOUT_S)))

    assert process.verbs == ["sync"]  # init's 900 s ceiling never stacks on a timed-out sync
    assert result.applied is False and result.mode == "skipped" and result.reason == "timeout"
    [finding] = result.findings
    assert finding.code == "MRS-DISP-054" and "timed out" in finding.message
    assert "runs without a codegraph index" in finding.message
    assert not (worktree / ".codegraph").exists()  # the session must not open on a half-synced index


def test_an_init_timeout_ends_in_skipped_and_discards_the_partial_index(tmp_path: Path) -> None:
    repo = _primary(tmp_path, base=False)

    def partial_then_timeout(argv: list[str], cwd: Path) -> ProcessResult:
        (cwd / _DB).parent.mkdir(parents=True, exist_ok=True)
        (cwd / _DB).write_bytes(b"partial")
        raise ProcessError(f"command timed out after {INDEX_TIMEOUT_S}s: {' '.join(argv)}")

    result, worktree, _fs, process = _seed(tmp_path, repo=repo, process=_Process(init=partial_then_timeout))

    assert process.verbs == ["init"]
    assert result.mode == "skipped" and result.reason == "timeout"
    assert [f.code for f in result.findings] == ["MRS-DISP-054"]
    assert not (worktree / ".codegraph").exists()


def test_a_timeout_of_the_fallback_init_is_also_skipped_with_reason_timeout(tmp_path: Path) -> None:
    repo = _primary(tmp_path)

    result, worktree, _fs, process = _seed(
        tmp_path,
        repo=repo,
        process=_Process(sync=_fail(1, "malformed"), init=_timeout(INDEX_TIMEOUT_S)),
    )

    assert process.verbs == ["sync", "init"]
    assert result.mode == "skipped" and result.reason == "timeout"
    assert [f.code for f in result.findings] == ["MRS-DISP-054"]
    assert "malformed" in result.findings[0].message  # the sync failure is not lost
    assert not (worktree / ".codegraph").exists()


def test_a_failed_init_ends_in_skipped_with_the_exit_reason(tmp_path: Path) -> None:
    repo = _primary(tmp_path, base=False)

    result, worktree, _fs, process = _seed(tmp_path, repo=repo, process=_Process(init=_fail(2, "out of memory")))

    assert process.verbs == ["init"]
    assert result.applied is False and result.mode == "skipped"
    assert result.reason is not None and "exited 2" in result.reason and "out of memory" in result.reason
    assert [f.code for f in result.findings] == ["MRS-DISP-054"]
    assert not (worktree / ".codegraph").exists()


def test_both_verbs_failing_reports_both_reasons(tmp_path: Path) -> None:
    repo = _primary(tmp_path)

    result, _worktree, _fs, process = _seed(
        tmp_path, repo=repo, process=_Process(sync=_fail(1, "sync boom"), init=_fail(2, "init boom"))
    )

    assert process.verbs == ["sync", "init"]
    assert result.mode == "skipped"
    assert result.reason is not None and "init boom" in result.reason and "sync boom" in result.reason


def test_a_build_that_exits_zero_without_an_index_is_not_reported_as_applied(tmp_path: Path) -> None:
    repo = _primary(tmp_path, base=False)

    result, _worktree, _fs, _process = _seed(tmp_path, repo=repo, process=_Process(init=_Process._ok))

    assert result.applied is False and result.mode == "skipped"
    assert result.reason is not None and "does not exist" in result.reason
    assert [f.code for f in result.findings] == ["MRS-DISP-054"]


def test_a_copy_failure_ends_in_skipped_with_the_os_reason_and_leaves_no_partial_copy(tmp_path: Path) -> None:
    repo = _primary(tmp_path)

    result, worktree, fs, process = _seed(tmp_path, repo=repo, fs=_Fs(fail_copy_of="codegraph.db-wal"))

    assert fs.copies  # some files went before the failure
    assert process.calls == []
    assert result.applied is False and result.mode == "skipped"
    assert result.reason is not None and "disk full" in result.reason
    [finding] = result.findings
    assert finding.code == "MRS-DISP-054" and "disk full" in finding.message
    assert not (worktree / ".codegraph").exists()


def test_the_seed_never_raises_on_an_unreadable_base(tmp_path: Path) -> None:
    repo = _primary(tmp_path)

    class _ExplodingFs(_Fs):
        def copy_file(self, src: Path, dst: Path) -> None:
            raise OSError("permission denied")

    result, _worktree, _fs, process = _seed(tmp_path, repo=repo, fs=_ExplodingFs())

    assert result.mode == "skipped" and "permission denied" in (result.reason or "")
    assert process.calls == []


# -- payload spelling ------------------------------------------------------------


def test_the_payload_is_a_fresh_plain_dict_per_call() -> None:
    seed = StructureGraphSeed(applied=True, mode="sync", seconds=4.16)

    first, second = seed.journal_payload(), seed.journal_payload()

    assert first == second == {"applied": True, "mode": "sync", "reason": None, "seconds": 4.16}
    assert first is not second
    json.dumps(first)


def test_the_new_warn_codes_are_registered_and_never_change_the_exit_code() -> None:
    from pyforge.marshal.core import findings as findings_module
    from pyforge.marshal.core import verdict

    for code in ("MRS-DISP-053", "MRS-DISP-054"):
        assert code in findings_module.REGISTERED_CODES
        assert verdict.classify(code) is verdict.Verdict.WARN


# -- dispatch_once: the journal and the envelope -----------------------------------


class _DispatchFs(FakeFs):
    """``test_dispatch``'s ``FakeFs`` plus the two ``FsPort`` operations the seed uses."""

    def copy_file(self, src: Path, dst: Path) -> None:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    def remove_empty_dir(self, path: Path) -> bool:
        try:
            path.rmdir()
        except OSError:
            return False
        return True


class _DispatchProcess(FakeProcess):
    """``FakeProcess`` that also answers ``codegraph``: ``sync`` succeeds, ``init`` creates the index."""

    def __init__(self) -> None:
        super().__init__()
        self.codegraph_calls: list[list[str]] = []

    def run(self, argv, *, cwd: Path, timeout_s: float | None = None) -> ProcessResult:
        if argv and argv[0] == "codegraph":
            self.codegraph_calls.append(list(argv))
            if argv[1] == "init":
                (cwd / _DB).parent.mkdir(parents=True, exist_ok=True)
                (cwd / _DB).write_bytes(b"built")
            return ProcessResult(returncode=0, stdout="", stderr="")
        return super().run(argv, cwd=cwd, timeout_s=timeout_s)


def _dispatch_with_layer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
    *,
    layer: dict[str, object] | None,
    base: bool,
    harness: FakeBuildHarness | None = None,
) -> tuple[dict[str, object], list[dict[str, object]], _DispatchProcess, Path]:
    slug = "pyforge-marshal"
    _init_git_repo(tmp_path, scope_slug=slug)
    story = "77-1-dispatch-seeds-the-worktree-index"
    specs = dispatch_core.planning_specs_dir(tmp_path, slug)
    specs.mkdir(parents=True)
    (specs / f"spec-{story}.md").write_text("---\n---\n# spec\n", encoding="utf-8")
    if base:
        (tmp_path / ".codegraph").mkdir()
        (tmp_path / ".codegraph" / "codegraph.db").write_bytes(b"base-db-bytes")
    project = {"context": {"structure-graph": layer}} if layer is not None else {}
    effective, _ = policy.compose(project_slug=slug, project=project, flags={})
    monkeypatch.setattr(dispatch_module, "_compose_policy", lambda _slug, flags=None: effective)
    fs, process = _DispatchFs(), _DispatchProcess()
    args = argparse.Namespace(slug=slug, story=story, format="json")
    monkeypatch.chdir(tmp_path)
    code = run_dispatch(
        args,
        fs=fs,
        vcs=FakeVcs(tmp_path),
        build_harness=harness or FakeBuildHarness(),
        process=process,
    )
    assert code == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    launched = [
        json.loads(line)["payload"]
        for _path, line, _fsync in fs.appended
        if "dispatch-launch" in line and '"session_pid"' in line
    ]
    return payload, launched, process, Path(payload["data"]["worktree_path"])


_ON = {"enabled": True, "aggressiveness": "medium"}
_OFF = {"enabled": False, "aggressiveness": "medium"}


def test_dispatch_journals_and_echoes_a_synced_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    payload, launched, process, worktree = _dispatch_with_layer(tmp_path, monkeypatch, capsys, layer=_ON, base=True)

    assert process.codegraph_calls == [["codegraph", "sync", "-q", str(worktree)]]
    echoed = payload["data"]["structure_graph"]
    assert (echoed["applied"], echoed["mode"], echoed["reason"]) == (True, "sync", None)
    assert set(echoed) == set(StructureGraphSeed().journal_payload())
    [outcome] = launched
    assert outcome["structure_graph"] == echoed
    assert outcome["wire"] is not None  # beside `wire`, which is untouched
    assert [f for f in payload["findings"] if f["code"] in {"MRS-DISP-053", "MRS-DISP-054"}] == []
    assert (worktree / _DB).read_bytes() == b"base-db-bytes"


def test_dispatch_with_no_base_index_inits_and_warns_with_the_bootstrap_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    payload, launched, process, worktree = _dispatch_with_layer(tmp_path, monkeypatch, capsys, layer=_ON, base=False)

    assert process.codegraph_calls == [["codegraph", "init", "-y", str(worktree)]]
    assert payload["data"]["structure_graph"]["mode"] == "init"
    assert launched[0]["structure_graph"]["mode"] == "init"
    [warn] = [f for f in payload["findings"] if f["code"] == "MRS-DISP-053"]
    assert warn["severity"] == "warn" and _BOOTSTRAP in warn["message"]


def test_dispatch_proceeds_when_codegraph_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    monkeypatch.setattr(
        dispatch_module,
        "probe_instrument",
        lambda item: InstrumentProbe(
            available=False, reason="codegraph is not installed here ('codegraph' is not on PATH)"
        ),
    )

    payload, launched, process, _worktree = _dispatch_with_layer(tmp_path, monkeypatch, capsys, layer=_ON, base=True)

    assert process.codegraph_calls == []
    assert payload["data"]["session_pid"] is not None  # the dispatch launched
    echoed = payload["data"]["structure_graph"]
    assert (echoed["applied"], echoed["mode"]) == (False, "skipped")
    assert "'codegraph' is not on PATH" in echoed["reason"]
    assert launched[0]["structure_graph"] == echoed
    [warn] = [f for f in payload["findings"] if f["code"] == "MRS-DISP-054"]
    assert warn["severity"] == "warn"


def test_dispatch_with_the_layer_off_copies_and_runs_nothing_and_says_applied_false(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    payload, launched, process, worktree = _dispatch_with_layer(tmp_path, monkeypatch, capsys, layer=_OFF, base=True)

    off = {"applied": False, "mode": "skipped", "reason": None, "seconds": 0.0}
    assert process.codegraph_calls == []
    assert not (worktree / ".codegraph").exists()
    assert payload["data"]["structure_graph"] == off
    assert launched[0]["structure_graph"] == off
    assert [f for f in payload["findings"] if f["code"] in {"MRS-DISP-053", "MRS-DISP-054"}] == []


def test_dispatch_states_the_structure_graph_disposition_even_when_the_launch_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """Like ``wire``: a refusal that returns before any launch result still carries the key."""
    from pyforge.marshal.adapters.harness_bmadbuild import BuildHarnessError
    from pyforge.marshal.ports.build_harness import DispatchLaunchResult

    class _FailingHarness(FakeBuildHarness):
        def dispatch(self, worktree: Path, **kwargs) -> DispatchLaunchResult:
            raise BuildHarnessError("cannot launch session harness: boom")

    slug = "pyforge-marshal"
    _init_git_repo(tmp_path, scope_slug=slug)
    story = "77-1-dispatch-seeds-the-worktree-index"
    specs = dispatch_core.planning_specs_dir(tmp_path, slug)
    specs.mkdir(parents=True)
    (specs / f"spec-{story}.md").write_text("---\n---\n# spec\n", encoding="utf-8")
    (tmp_path / ".codegraph").mkdir()
    (tmp_path / ".codegraph" / "codegraph.db").write_bytes(b"base")
    effective, _ = policy.compose(project_slug=slug, project={"context": {"structure-graph": _ON}}, flags={})
    monkeypatch.setattr(dispatch_module, "_compose_policy", lambda _slug, flags=None: effective)
    monkeypatch.chdir(tmp_path)

    code = run_dispatch(
        argparse.Namespace(slug=slug, story=story, format="json"),
        fs=_DispatchFs(),
        vcs=FakeVcs(tmp_path),
        build_harness=_FailingHarness(),
        process=_DispatchProcess(),
    )

    assert code != EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert [f for f in payload["findings"] if f["code"] == "MRS-DISP-008"]
    assert payload["data"]["structure_graph"]["mode"] == "sync"


def test_a_refusal_after_the_policy_composes_still_states_the_disposition_as_off(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    """The harness refusal (MRS-DISP-003) comes after the off-shape seed and
    before the worktree seed: the key is present and reads off even though the
    layer is enabled and a base index exists -- nothing was provisioned."""
    slug = "pyforge-marshal"
    _init_git_repo(tmp_path, scope_slug=slug)
    story = "77-1-dispatch-seeds-the-worktree-index"
    specs = dispatch_core.planning_specs_dir(tmp_path, slug)
    specs.mkdir(parents=True)
    (specs / f"spec-{story}.md").write_text("---\n---\n# spec\n", encoding="utf-8")
    (tmp_path / ".codegraph").mkdir()
    (tmp_path / ".codegraph" / "codegraph.db").write_bytes(b"base")
    effective, _ = policy.compose(project_slug=slug, project={"context": {"structure-graph": _ON}}, flags={})
    monkeypatch.setattr(dispatch_module, "_compose_policy", lambda _slug, flags=None: effective)
    monkeypatch.chdir(tmp_path)
    vcs, process = FakeVcs(tmp_path), _DispatchProcess()

    code = run_dispatch(
        argparse.Namespace(slug=slug, story=story, format="json"),
        fs=_DispatchFs(),
        vcs=vcs,
        build_harness=FakeBuildHarness(present=False),
        process=process,
    )

    assert code != EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert [f["code"] for f in payload["findings"] if f["code"] == "MRS-DISP-003"] == ["MRS-DISP-003"]
    assert vcs.added == [] and process.codegraph_calls == []  # refused before any worktree existed
    assert payload["data"]["structure_graph"] == StructureGraphSeed().journal_payload()
