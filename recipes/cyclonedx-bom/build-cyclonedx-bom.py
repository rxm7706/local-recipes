from pathlib import Path
import sys
import os
import subprocess
import site

SRC_DIR = Path(os.environ["SRC_DIR"])
SRC = SRC_DIR / "src"
DIST = SRC_DIR / "dist"
SP_DIR = Path(site.getsitepackages()[0])

PIP_ARGS = [
    sys.executable,
    "-m",
    "pip",
    "install",
    ".",
    "-vv",
    "--no-deps",
    "--no-build-isolation",
    "--disable-pip-version-check",
]


def main() -> int:
    for path in SRC_DIR.rglob("*"):
        if path.is_symlink():
            print("... replacing symlink for", path)
            data = path.read_bytes()
            path.unlink()
            path.write_bytes(data)
    print(">>>", *PIP_ARGS)
    subprocess.check_call(PIP_ARGS, cwd=str(DIST))
    assert all(not (SP_DIR / p).exists() for p in ["LICENSE", "NOTICE"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
