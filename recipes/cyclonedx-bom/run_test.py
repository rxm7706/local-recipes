import sys
from subprocess import call
from pathlib import Path

FAIL_UNDER = "55"
COV = ["coverage"]
RUN = ["run", "--source=cyclonedx_py", "--branch", "-m"]
PYTEST = ["pytest", "-vv", "--color=yes", "--tb=long"]
REPORT = ["report", "--show-missing", "--skip-covered", f"--fail-under={FAIL_UNDER}"]
UNLINK = ["src/tests/integration/test_cli_environment.py"]
SKIPS = [
    "simple",
    "data_file_filter",
    "data_os_filter",
    # https://github.com/conda-forge/cyclonedx-bom-feedstock/pull/45
    "cli_poetry",
]


SKIP_OR = " or ".join(SKIPS)
K = ["-k", f"not ({SKIP_OR})"]


if __name__ == "__main__":
    [Path(p).unlink() for p in UNLINK]
    sys.exit(
        # run the tests
        call([*COV, *RUN, *PYTEST, *K])
        # maybe run coverage
        or call([*COV, *REPORT])
    )
