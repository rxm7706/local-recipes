"""Meta-test: `loop_home_staleness()` in fleet_picture.py.

Story 9.4 (`docs/dreams/bmad-loop-baseline-drift.md` incident, 2026-08-15): all
four active stations' loop homes were found 55-60 commits behind `origin/main`
with nobody noticing, which is how three stations independently rediscovered
the same already-fixed bug before their branches caught up. This function
live-fetches `origin main` for each `~/.bmad-loops/pyforge-<slug>` home and
reports any branch `threshold`+ commits behind, feeding one line per stale
home into `fleet_picture.py`'s ATTENTION block.

These tests build a real git repo with a real "origin" so the behaviour is
exercised through actual git plumbing rather than a mocked `git()` -- same
harness style as `test_unpushed_work_check.py`. Unlike that precedent,
`loop_home_staleness()` takes `loop_root` and `threshold` as explicit
parameters, so no source-text ROOT-rebinding is needed -- the module is
imported directly.
"""
import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
FLEET_PICTURE = REPO_ROOT / "scripts" / "fleet_picture.py"


def _load_fleet_picture():
    spec = importlib.util.spec_from_file_location(
        "fleet_picture_under_test", FLEET_PICTURE
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["fleet_picture_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


def _git(repo: Path, *args: str) -> str:
    p = subprocess.run(["git", "-C", str(repo), *args],
                       capture_output=True, text=True)
    return p.stdout.strip()


def _loop_home(tmp_path: Path, slug: str, branch: str) -> tuple[Path, Path, Path]:
    """Build a bare "origin" + a loop-home-shaped clone at
    `<tmp_path>/pyforge-<slug>/`, checked out on `branch`, with one commit
    pushed to establish the branch on origin. Returns (loop_root, home, origin)."""
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True)
    # A bare repo's HEAD defaults to whatever `init.defaultBranch` is (often
    # "master"), independent of the "main" branch we're about to push -- left
    # unset, `git clone` can't resolve remote HEAD and checks out nothing,
    # silently producing an orphan working tree with no shared history.
    subprocess.run(["git", "-C", str(origin), "symbolic-ref", "HEAD",
                    "refs/heads/main"], check=True)

    seed = tmp_path / "_seed"
    subprocess.run(["git", "init", "-q", "-b", "main", str(seed)], check=True)
    for k, v in (("user.email", "t@example.com"), ("user.name", "t")):
        subprocess.run(["git", "-C", str(seed), "config", k, v], check=True)
    (seed / "a.txt").write_text("1\n", encoding="utf-8")
    _git(seed, "add", "-A")
    _git(seed, "commit", "-qm", "base")
    _git(seed, "remote", "add", "origin", str(origin))
    _git(seed, "push", "-q", "origin", "main")

    loop_root = tmp_path / "loop_root"
    loop_root.mkdir()
    home = loop_root / f"pyforge-{slug}"
    subprocess.run(["git", "clone", "-q", str(origin), str(home)], check=True)
    for k, v in (("user.email", "t@example.com"), ("user.name", "t")):
        subprocess.run(["git", "-C", str(home), "config", k, v], check=True)
    _git(home, "checkout", "-qb", branch)
    (home / "b.txt").write_text("station work\n", encoding="utf-8")
    _git(home, "add", "-A")
    _git(home, "commit", "-qm", "station work")
    _git(home, "push", "-q", "origin", branch)
    return loop_root, home, origin


def _advance_origin_main(origin: Path, tmp_path: Path, n: int) -> None:
    """Push `n` additional commits directly to origin's `main`, via a second
    scratch work clone (the bare origin itself can't be checked out into)."""
    scratch = tmp_path / "_scratch"
    subprocess.run(["git", "clone", "-q", str(origin), str(scratch)], check=True)
    for k, v in (("user.email", "t@example.com"), ("user.name", "t")):
        subprocess.run(["git", "-C", str(scratch), "config", k, v], check=True)
    _git(scratch, "checkout", "-q", "main")
    for i in range(n):
        (scratch / f"c{i}.txt").write_text(f"{i}\n", encoding="utf-8")
        _git(scratch, "add", "-A")
        _git(scratch, "commit", "-qm", f"main advance {i}")
    _git(scratch, "push", "-q", "origin", "main")


def test_a_stale_loop_home_is_reported(tmp_path: Path):
    loop_root, _, origin = _loop_home(tmp_path, "teststation", "loop/pyforge-teststation")
    _advance_origin_main(origin, tmp_path, 3)

    mod = _load_fleet_picture()
    result = mod.loop_home_staleness(loop_root=loop_root, threshold=3)

    assert ("teststation", "loop/pyforge-teststation", 3) in result, result


def test_an_in_sync_home_stays_silent(tmp_path: Path):
    loop_root, _, _ = _loop_home(tmp_path, "synced", "loop/pyforge-synced")

    mod = _load_fleet_picture()
    result = mod.loop_home_staleness(loop_root=loop_root, threshold=3)

    assert not any(r[0] == "synced" for r in result), result


def test_a_home_below_threshold_stays_silent(tmp_path: Path):
    loop_root, _, origin = _loop_home(tmp_path, "almoststale", "loop/pyforge-almoststale")
    _advance_origin_main(origin, tmp_path, 2)

    mod = _load_fleet_picture()
    result = mod.loop_home_staleness(loop_root=loop_root, threshold=3)

    assert not any(r[0] == "almoststale" for r in result), result


def test_a_missing_loop_root_returns_empty_list(tmp_path: Path):
    mod = _load_fleet_picture()
    result = mod.loop_home_staleness(loop_root=tmp_path / "nope", threshold=3)
    assert result == []


def test_a_home_with_no_origin_remote_is_skipped_without_aborting_the_scan(tmp_path: Path):
    """A per-home git failure (here: no `origin` remote to fetch, e.g. a
    misconfigured or half-set-up home) must not crash the whole scan, and
    must not silently masquerade as `0 commits behind` -- it's absent from
    the result, same as any other skipped home, while a healthy sibling home
    in the same loop_root is still measured correctly."""
    loop_root, _, origin = _loop_home(tmp_path, "teststation", "loop/pyforge-teststation")
    _advance_origin_main(origin, tmp_path, 3)

    broken_home = loop_root / "pyforge-broken"
    subprocess.run(["git", "init", "-q", "-b", "loop/pyforge-broken", str(broken_home)],
                    check=True)
    for k, v in (("user.email", "t@example.com"), ("user.name", "t")):
        subprocess.run(["git", "-C", str(broken_home), "config", k, v], check=True)
    (broken_home / "x.txt").write_text("no remote\n", encoding="utf-8")
    _git(broken_home, "add", "-A")
    _git(broken_home, "commit", "-qm", "no origin configured at all")

    mod = _load_fleet_picture()
    result = mod.loop_home_staleness(loop_root=loop_root, threshold=3)

    assert not any(r[0] == "broken" for r in result), result
    assert ("teststation", "loop/pyforge-teststation", 3) in result, result
