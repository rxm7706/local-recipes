"""Tests for `scripts/container-gates`'s `volumes-roundtrip` subcommand
(Story 7.4, "State outlives the container").

Real, non-mocked: every test subprocess-invokes the real `container-gates`
script, which itself subprocess-invokes the real `docker` CLI (`docker run`,
`docker volume rm`) -- no mocking of either layer. That means these tests
need a real `docker` binary on PATH plus the `ubuntu:24.04` image already
cached locally (confirmed via `docker images`; the story's Design Notes
explain why `ubuntu:24.04` and not the full guild image -- it's the guild
image's own runtime base, and building the whole guild image just to
unit-test the write/destroy/recreate/read mechanism would make routine test
runs slow and network-dependent):

    pixi run -e pyforge-steward pytest tests/scripts/test_container_volumes_roundtrip.py -q
    pixi run -e pyforge-steward pyforge-steward-container-volumes-test

Mirrors the story spec's I/O & Edge-Case Matrix, one test per row.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTAINER_GATES = REPO_ROOT / "scripts" / "container-gates"

# Already cached locally per the story's Design Notes -- no network pull
# needed to run this suite.
IMAGE = "ubuntu:24.04"
_DOCKER_TIMEOUT = 60
_VOLUME_PREFIX = "container-gates-roundtrip-"


def _image_cached() -> bool:
    """`docker image inspect` never pulls -- unlike `docker run`, which
    pulls-if-missing by default. Checking this explicitly (not just that
    `docker` is on PATH) is what actually keeps this suite's "no network
    pull needed" claim true on a docker-equipped host that doesn't happen to
    have `ubuntu:24.04` cached."""
    if shutil.which("docker") is None:
        return False
    result = subprocess.run(
        ["docker", "image", "inspect", IMAGE],
        capture_output=True,
        text=True,
        timeout=_DOCKER_TIMEOUT,
    )
    return result.returncode == 0


pytestmark = pytest.mark.skipif(
    not _image_cached(),
    reason=f"docker not on PATH, or {IMAGE} not cached locally -- run via "
    "`pixi run -e pyforge-steward pytest ...`",
)


def _run(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CONTAINER_GATES), *args],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )


def test_single_mount_round_trips_cleanly():
    """Matrix row 1: one mount, marker written, container replaced, same
    token read back."""
    proc = _run("volumes-roundtrip", "--image", IMAGE, "--mount", "/data")

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "/data: OK" in proc.stdout


def test_multiple_mounts_all_round_trip():
    """Matrix row 2: every one of several `--mount` flags round-trips
    independently; exit 0 only because ALL passed."""
    proc = _run(
        "volumes-roundtrip",
        "--image",
        IMAGE,
        "--mount",
        "/data",
        "--mount",
        "/opt",
        "--mount",
        "/srv",
    )

    assert proc.returncode == 0, proc.stdout + proc.stderr
    for mount in ("/data", "/opt", "/srv"):
        assert f"{mount}: OK" in proc.stdout


def test_nonexistent_image_fails_cleanly():
    """Matrix row 3: `docker run` fails on the write step against an image
    that doesn't exist -- clean stderr naming the image, exit 1, never a raw
    docker CLI traceback (no Python `Traceback` in the output)."""
    proc = _run("volumes-roundtrip", "--image", "does-not-exist:latest", "--mount", "/data")

    assert proc.returncode != 0
    assert "does-not-exist:latest" in proc.stderr
    assert "Traceback" not in proc.stderr


def test_docker_missing_from_path_fails_cleanly_not_with_a_traceback():
    """Matrix row 4: `docker` absent from PATH must be a clean gate failure,
    not an unhandled `FileNotFoundError` traceback -- exercises the real
    PATH-lookup failure by giving the CHILD `container-gates` process an
    environment with no `docker` reachable, rather than mocking
    `subprocess.run` (mirrors `test_container_gates.py`'s equivalent test for
    `secrets-scan`/`steward`)."""
    proc = _run(
        "volumes-roundtrip",
        "--image",
        IMAGE,
        "--mount",
        "/data",
        env={"PATH": "/nonexistent-empty-bin"},
    )

    assert proc.returncode != 0
    assert "`docker` not found on PATH" in proc.stderr
    assert "Traceback" not in proc.stderr


def test_multiple_mounts_one_fails_others_still_attempted():
    """Matrix row 5: three `--mount`s, one against a path that can never be
    a valid volume-mount target because it already exists as a regular FILE
    in the base image (`/etc/hostname`) -- `docker run` itself refuses to
    bind a volume there ("not a directory"), which is a clean, real,
    non-simulated way to make exactly one mount's write step fail. All
    three must still be attempted (no short-circuit); overall exit is
    non-zero because at least one mount failed."""
    proc = _run(
        "volumes-roundtrip",
        "--image",
        IMAGE,
        "--mount",
        "/data",
        "--mount",
        "/etc/hostname",
        "--mount",
        "/other",
    )

    assert proc.returncode != 0
    combined = proc.stdout + proc.stderr
    assert "/data: OK" in combined       # proves /data was actually attempted and passed
    assert "/other: OK" in combined      # proves /other was still attempted after /etc/hostname failed
    assert "/etc/hostname" in combined   # proves the failing mount's own diagnostic was printed
    assert "Traceback" not in proc.stderr


def test_different_volumes_never_share_content():
    """Matrix row 6: "read-back mismatch (simulated volume-not-reused bug)"
    -- a second container attached to a DIFFERENT volume than the first must
    never read back the first volume's token.

    `container-gates volumes-roundtrip` has no public flag to force its own
    read step onto a volume other than the one its own write step used (by
    design -- AD-2 delegation-purity means the tool only exposes
    `--image`/`--mount`, nothing volume-shaped), so this row can't be
    reproduced through the CLI's own surface. Instead this test proves the
    underlying assumption `_roundtrip_mount` depends on directly, with the
    same raw `docker run`/`docker volume` primitives `container-gates` uses
    internally: writing a token into volume A and then reading from a
    genuinely different, freshly-created volume B returns no marker at all
    (empty stdout, non-zero exit -- `cat: ... No such file or directory`),
    never the token written to A. Given that, the exact "read step failed"
    branch already present in `_roundtrip_mount` (nonzero returncode from
    the read `docker run`) is what would fire on a real volume-not-reused
    bug -- confirmed live here, not assumed, matching this repo's Containerfile/
    container-gates evidentiary convention."""
    token = uuid.uuid4().hex
    volume_a = f"cg-roundtrip-test-a-{uuid.uuid4().hex}"
    volume_b = f"cg-roundtrip-test-b-{uuid.uuid4().hex}"
    try:
        write = subprocess.run(
            [
                "docker", "run", "--rm", "-v", f"{volume_a}:/data", IMAGE,
                "sh", "-c", f"echo {token} > /data/marker",
            ],
            capture_output=True,
            text=True,
            timeout=_DOCKER_TIMEOUT,
        )
        assert write.returncode == 0, write.stdout + write.stderr

        read_wrong_volume = subprocess.run(
            [
                "docker", "run", "--rm", "-v", f"{volume_b}:/data", IMAGE,
                "sh", "-c", "cat /data/marker",
            ],
            capture_output=True,
            text=True,
            timeout=_DOCKER_TIMEOUT,
        )

        assert read_wrong_volume.returncode != 0
        assert token not in read_wrong_volume.stdout
    finally:
        subprocess.run(
            ["docker", "volume", "rm", volume_a, volume_b],
            capture_output=True,
            text=True,
            timeout=_DOCKER_TIMEOUT,
        )


def test_independent_invocations_for_the_same_mount_never_interfere():
    """Complements matrix row 6 from the tool's own black-box surface: two
    fully separate `volumes-roundtrip` invocations against the SAME
    `--mount` path each get their own fresh uuid-suffixed volume (per
    `_roundtrip_mount`), so back-to-back runs never see each other's marker
    -- both must independently report a clean round trip."""
    first = _run("volumes-roundtrip", "--image", IMAGE, "--mount", "/data")
    second = _run("volumes-roundtrip", "--image", IMAGE, "--mount", "/data")

    assert first.returncode == 0, first.stdout + first.stderr
    assert second.returncode == 0, second.stdout + second.stderr


def _our_volumes() -> set[str]:
    """Volumes matching `_VOLUME_PREFIX` only -- not the full `docker volume
    ls` output, which would make this check vulnerable to false pass/fail
    from unrelated concurrent docker activity on a shared host (this repo
    routinely runs several bmad-loop worktrees against the same docker
    daemon)."""
    return set(
        subprocess.run(
            ["docker", "volume", "ls", "-q", "--filter", f"name={_VOLUME_PREFIX}"],
            capture_output=True,
            text=True,
            timeout=_DOCKER_TIMEOUT,
        ).stdout.splitlines()
    )


def test_no_volume_is_leaked_after_a_run():
    """The docker volume created for a mount is always removed in `finally`
    -- verified live by diffing this suite's OWN volumes before/after a real
    run, not merely by reading the source for a `finally` block."""
    before = _our_volumes()

    proc = _run("volumes-roundtrip", "--image", IMAGE, "--mount", "/data")
    assert proc.returncode == 0, proc.stdout + proc.stderr

    after = _our_volumes()

    assert after - before == set()


def test_two_of_three_mounts_fail_still_all_attempted():
    """Extends matrix row 5 to TWO simultaneous failures: `/data` (must
    pass), `/etc/hostname` and `/etc/hosts` (both pre-existing regular
    files in the base image, so both must fail) -- the "never short-circuit,
    aggregate across every mount" claim is only meaningfully proven once
    more than one mount fails in the same invocation."""
    proc = _run(
        "volumes-roundtrip",
        "--image",
        IMAGE,
        "--mount",
        "/data",
        "--mount",
        "/etc/hostname",
        "--mount",
        "/etc/hosts",
    )

    assert proc.returncode != 0
    combined = proc.stdout + proc.stderr
    assert "/data: OK" in combined
    assert "/etc/hostname" in combined
    assert "/etc/hosts" in combined
    assert "Traceback" not in proc.stderr
