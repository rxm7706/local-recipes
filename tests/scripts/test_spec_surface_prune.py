"""Doctor Story 58.3 (spec-pyforge-doctor CAP-59, the ``--prune`` clause).

``scripts/spec_surface_check.py --prune`` removes, under the stamp's own lock,
the baseline entries of Specs discovery no longer finds. A scoped stamp of a
gone Spec exits 2 (``unknown spec(s)``) and a full stamp is forbidden, so
before this verb nothing sanctioned could drop a dead key.

The cases: a dead key is removed and printed; every live key stays
byte-identical; zero discovered Specs over a non-empty baseline exits 1 and
leaves the file untouched; a corrupt baseline exits 1 untouched; ``--prune``
with ``--spec`` (or ``--write-baseline`` or ``--accept``) is a usage error,
exit 2; a second prune removes nothing.

Stdlib only (the ``pyforge-ci`` scripts lane): the script is loaded by path
and its ``REPO_ROOT`` and ``BASELINE`` are monkeypatched to ``tmp_path``. The
prune reads discovery only, never ``git ls-files``, so the fixture needs no
git repository. Marshal's ``tests/meta/test_spec_surface_stamp.py`` and CFE's
``tests/meta/test_spec_surface_check.py`` keep testing the stamp.
"""

from __future__ import annotations

import fcntl
import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "spec_surface_check.py"

#: Discovery finds these three. ``spec-dark`` declares a ``surface:`` nothing can
#: be read from, so no stamp would write it, but the Spec exists: its key is live.
LIVE = ("proj/spec-alpha", "proj/spec-beta", "proj/spec-dark")
#: Discovery finds neither: a whole project gone, and a folded Spec folder that
#: kept its ``.memlog.md`` but lost its ``SPEC.md``.
DEAD = ("gone/spec-folded", "proj/spec-retired")


def _spec_dir(root: Path, project: str, slug: str) -> Path:
    return root / "_bmad-output" / "projects" / project / "planning-artifacts" / "specs" / slug


def _canonical(data: dict) -> str:
    """The exact text ``_write_baseline`` writes."""
    return json.dumps(data, indent=1, sort_keys=True) + "\n"


def _entry(seed: int) -> dict:
    """A baseline entry whose hashes match nothing on disk, so an entry the
    prune recomputed instead of carrying over would show."""
    return {"memlog": f"{seed:040x}", "files": {f"src/m{seed}.py": f"{seed + 100:040x}"}}


def _baseline_data() -> dict:
    data = {name: _entry(i) for i, name in enumerate(LIVE + DEAD, start=1)}
    # An entry of a shape no stamp writes today is still a live Spec's entry:
    # the prune removes keys only, it never rewrites what a key holds.
    data["proj/spec-beta"]["legacy"] = ["kept", "as", "read"]
    return data


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    for slug, surface in (
        ("spec-alpha", "surface:\n  - a.py\n"),
        ("spec-beta", "surface:\n  - b.py\n"),
        ("spec-dark", "surface:\n"),
    ):
        directory = _spec_dir(tmp_path, "proj", slug)
        directory.mkdir(parents=True)
        (directory / "SPEC.md").write_text(f"---\n{surface}---\n# {slug}\n", encoding="utf-8")
        (directory / ".memlog.md").write_text("- (note) initial\n", encoding="utf-8")
    retired = _spec_dir(tmp_path, "proj", "spec-retired")
    retired.mkdir(parents=True)
    (retired / ".memlog.md").write_text("- (note) folded\n", encoding="utf-8")
    (tmp_path / "scripts").mkdir()
    return tmp_path


@pytest.fixture
def checker(repo: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """The script loaded by path, its ``REPO_ROOT`` and ``BASELINE`` pointed at ``repo``."""
    spec = importlib.util.spec_from_file_location(f"spec_surface_check_prune_{repo.name}", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "REPO_ROOT", repo)
    monkeypatch.setattr(module, "BASELINE", repo / "scripts" / ".spec-surface-baseline.json")
    return module


def _baseline(module: ModuleType) -> Path:
    return module.BASELINE


def _seed(module: ModuleType, text: str | None = None) -> bytes:
    path = _baseline(module)
    path.write_text(_canonical(_baseline_data()) if text is None else text, encoding="utf-8")
    return path.read_bytes()


def _run(module: ModuleType, monkeypatch: pytest.MonkeyPatch, *argv: str) -> int:
    monkeypatch.setattr(sys, "argv", ["spec_surface_check.py", *argv])
    return module.main()


def test_a_dead_key_is_removed_and_printed(
    checker: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _seed(checker)

    assert _run(checker, monkeypatch, "--prune") == 0

    after = json.loads(_baseline(checker).read_text(encoding="utf-8"))
    assert sorted(after) == sorted(LIVE)
    out = capsys.readouterr().out
    assert "prune: removed 2 entries from scripts/.spec-surface-baseline.json:" in out
    for name in DEAD:
        assert f"  - {name}\n" in out
    for name in LIVE:
        assert name not in out


def test_every_live_key_stays_byte_identical(checker: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    _seed(checker)
    before = _baseline_data()

    assert _run(checker, monkeypatch, "--prune") == 0

    text = _baseline(checker).read_text(encoding="utf-8")
    assert text == _canonical({name: before[name] for name in LIVE})
    after = json.loads(text)
    for name in LIVE:
        assert json.dumps(after[name], sort_keys=True) == json.dumps(before[name], sort_keys=True), name


def test_zero_discovered_specs_over_a_non_empty_baseline_exits_1_and_leaves_the_file_untouched(
    repo: Path, checker: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    before = _seed(checker)
    mtime = _baseline(checker).stat().st_mtime_ns
    shutil.rmtree(repo / "_bmad-output")

    assert _run(checker, monkeypatch, "--prune") == 1

    assert _baseline(checker).read_bytes() == before
    assert _baseline(checker).stat().st_mtime_ns == mtime
    err = capsys.readouterr().err
    assert "refusing to prune: discovery found zero Specs" in err
    assert "baseline untouched" in err


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("{not json\n", id="not-json"),
        pytest.param('["proj/spec-alpha"]\n', id="json-list"),
    ],
)
def test_a_corrupt_baseline_exits_1_untouched(
    checker: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], text: str
) -> None:
    before = _seed(checker, text)

    assert _run(checker, monkeypatch, "--prune") == 1

    assert _baseline(checker).read_bytes() == before
    err = capsys.readouterr().err
    assert "scripts/.spec-surface-baseline.json" in err
    assert "nothing written" in err


@pytest.mark.parametrize(
    "argv",
    [
        pytest.param(["--prune", "--spec", "proj/spec-alpha"], id="with-spec"),
        pytest.param(["--prune", "--write-baseline"], id="with-write-baseline"),
        pytest.param(["--prune", "--write-baseline", "--spec", "proj/spec-alpha"], id="with-scoped-stamp"),
        pytest.param(["--prune", "--accept", "a.py"], id="with-accept"),
    ],
)
def test_prune_with_spec_write_baseline_or_accept_is_a_usage_error(
    checker: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], argv: list[str]
) -> None:
    before = _seed(checker)

    with pytest.raises(SystemExit) as exited:
        _run(checker, monkeypatch, *argv)

    assert exited.value.code == 2
    assert "--prune is exclusive with --write-baseline, --spec and --accept" in capsys.readouterr().err
    assert _baseline(checker).read_bytes() == before


def test_a_second_prune_removes_nothing(
    checker: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _seed(checker)
    assert _run(checker, monkeypatch, "--prune") == 0
    capsys.readouterr()
    pruned = _baseline(checker).read_bytes()
    mtime = _baseline(checker).stat().st_mtime_ns

    assert _run(checker, monkeypatch, "--prune") == 0

    assert capsys.readouterr().out == "prune: nothing to remove from scripts/.spec-surface-baseline.json\n"
    assert _baseline(checker).read_bytes() == pruned
    assert _baseline(checker).stat().st_mtime_ns == mtime


def test_a_missing_baseline_is_nothing_to_remove_and_creates_no_file(
    checker: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _run(checker, monkeypatch, "--prune") == 0

    assert not _baseline(checker).exists()
    assert "nothing to remove" in capsys.readouterr().out


def _lock_is_held(module: ModuleType) -> bool:
    """Whether some open file description holds the baseline's sidecar flock:
    a fresh descriptor's non-blocking exclusive flock fails exactly then."""
    fd = os.open(module.BASELINE.with_name(module.BASELINE.name + ".lock"), os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return True
    else:
        fcntl.flock(fd, fcntl.LOCK_UN)
        return False
    finally:
        os.close(fd)


def test_the_prune_reads_and_writes_under_the_stamps_lock(checker: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    _seed(checker)
    seen: list[tuple[str, bool]] = []
    real_read, real_write = checker._read_baseline, checker._write_baseline

    def read() -> dict:
        seen.append(("read", _lock_is_held(checker)))
        return real_read()

    def write(merged: dict) -> None:
        seen.append(("write", _lock_is_held(checker)))
        real_write(merged)

    monkeypatch.setattr(checker, "_read_baseline", read)
    monkeypatch.setattr(checker, "_write_baseline", write)
    assert not _lock_is_held(checker)

    assert _run(checker, monkeypatch, "--prune") == 0

    assert seen == [("read", True), ("write", True)]
    assert not _lock_is_held(checker)
