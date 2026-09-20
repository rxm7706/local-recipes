"""CLI wrapper tests (Story 13.3, CAP-3) — ``python -m pyforge.atlas.trending_candidates``.

Exercises ``main(argv)`` directly (mirrors ``tests/test_main_version.py``'s
``from pyforge.atlas.__main__ import main`` pattern): a real ``DataCatalog`` +
monkeypatched ``bootstrapped_session`` end-to-end for the ``--json`` happy path (its
output must match ``query.query_trending_candidates``'s own return, since both the CLI
and the MCP tool delegate to the SAME function), and a bad ``--tier`` value for the
CLI's ``ValueError`` -> stderr + exit 1 contract.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from pyforge.atlas.trending_candidates import query
from pyforge.atlas.trending_candidates.__main__ import main

_FIXTURE_DF = pd.DataFrame(
    [
        {
            "repo_full_name": "alice/libfoo",
            "repo_url": "https://github.com/alice/libfoo",
            "description": None,
            "language": "Python",
            "stars_total": 1200,
            "stars_today": 5,
            "forks_total": 1,
            "period": "weekly",
            "source": "html_scrape",
            "fetched_at": 1_700_000_000,
            "pypi_name": "libfoo",
            "tier": "1",
            "reason": "pure-python packaging shape, OSI-approved license MIT",
        }
    ]
)


def test_json_output_matches_query_trending_candidates(seed_catalog, capsys):
    seed_catalog(_FIXTURE_DF)

    exit_code = main(["--json"])
    captured = capsys.readouterr()

    expected = query.query_trending_candidates()

    assert exit_code == 0
    # The WHOLE of stdout must parse (follow-up review finding, Story 13.3). The
    # earlier version of this assertion took "the last non-empty line", which tolerated
    # exactly the defect that was live: kedro's rich handler sits on the ROOT logger
    # writing to STDOUT, and the old INFO-only `logging.disable` floor still let every
    # WARNING record through, straight into the middle of the envelope. Parsing only
    # the last line hid that `--json` output was not pipeable at all.
    assert json.loads(captured.out) == expected


def test_table_output_is_the_default_and_is_not_json(seed_catalog, capsys):
    seed_catalog(_FIXTURE_DF)

    exit_code = main([])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "alice/libfoo" in captured.out
    with pytest.raises(json.JSONDecodeError):
        json.loads(captured.out)


def test_bad_tier_exits_1_with_stderr_message():
    """No `seed_catalog` fixture: validation fails before any session/catalog touch."""
    exit_code = main(["--tier", "bogus"])

    assert exit_code == 1


def test_bad_tier_message_names_the_bad_value(capsys):
    exit_code = main(["--tier", "bogus"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out == ""
    assert "bogus" in captured.err
    # The exception TYPE is prefixed (follow-up review finding, Story 13.3): several
    # failures on this path carry a message that is meaningless alone -- a bootstrap
    # `KeyError` printed the bare line `'atlas'`.
    assert captured.err.startswith("ValueError: ")


def test_json_stdout_stays_parseable_when_a_warning_is_logged(seed_catalog, capsys):
    """Follow-up review finding, Story 13.3 (verified live): kedro's rich handler is on
    the ROOT logger and writes to STDOUT, and the root level is WARNING -- so the old
    `logging.disable(logging.INFO)` floor left every WARNING record free to print into
    the middle of the envelope, and `json.loads(stdout)` failed. Under `--json`, stdout
    carries the envelope and nothing else."""
    import logging

    seed_catalog(_FIXTURE_DF)

    class _StdoutHandler(logging.Handler):
        def emit(self, record):
            print(self.format(record))

    noisy = logging.getLogger("kedro.noisy_for_test")
    handler = _StdoutHandler()
    noisy.addHandler(handler)
    noisy.setLevel(logging.WARNING)
    try:
        # Emitted from inside the query, i.e. exactly where kedro's own warnings land.
        original = query.query_trending_candidates

        def _warn_then_query(**kwargs):
            noisy.warning("Credentials not found in your Kedro project config.")
            return original(**kwargs)

        import pyforge.atlas.trending_candidates.query as _qmod

        _qmod.query_trending_candidates = _warn_then_query
        try:
            exit_code = main(["--json"])
        finally:
            _qmod.query_trending_candidates = original
    finally:
        noisy.removeHandler(handler)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Credentials not found" not in captured.out
    json.loads(captured.out)  # the WHOLE of stdout, not just the last line


def test_json_restores_the_callers_own_logging_floor(seed_catalog):
    """Follow-up review finding, Story 13.3 (verified live): the `finally` reset
    `logging.disable` to NOTSET unconditionally, CLEARING a floor the calling process
    had deliberately set. `main()` is callable in-process, so it must restore what was
    there, not what it assumes was there."""
    import logging

    seed_catalog(_FIXTURE_DF)
    logging.disable(logging.WARNING)
    try:
        assert main(["--json"]) == 0
        assert logging.root.manager.disable == logging.WARNING
    finally:
        logging.disable(logging.NOTSET)


def test_table_shows_provenance_so_never_ingested_differs_from_no_match(seed_catalog, seed_parquet_catalog, capsys):
    """Follow-up review finding, Story 13.3 (verified live): table mode printed the
    rows alone, so "never ingested" and "your filters matched nothing" were both just
    `(no candidates)`, exit 0 -- and the staleness catalog.yml (this same story)
    promises the surface always shows was visible only under `--json`."""
    seed_parquet_catalog(None)  # declared entry, backing file absent = never ingested
    assert main([]) == 0
    never_ingested = capsys.readouterr().out

    seed_catalog(_FIXTURE_DF)
    assert main(["--min-stars", "999999"]) == 0  # present data, nothing matches
    no_match = capsys.readouterr().out

    assert "(no candidates)" in never_ingested and "(no candidates)" in no_match
    assert never_ingested != no_match
    assert "unavailable" in never_ingested
    assert "build_stamp=" in no_match and "shown=0" in no_match


def test_table_shows_the_build_stamp_for_a_real_parquet_dataset(seed_parquet_catalog, capsys):
    """The other half of the catalog.yml claim: when the table IS materialized, the
    default human path prints its build_stamp."""
    seed_parquet_catalog(_FIXTURE_DF)

    assert main([]) == 0
    out = capsys.readouterr().out

    assert "provenance=file-mtime" in out
    assert "build_stamp=none" not in out
    assert "alice/libfoo" in out


def test_a_closed_stdout_pipe_is_not_a_raw_traceback(seed_catalog, monkeypatch):
    """Follow-up review finding, Story 13.3 (verified live): the two print paths sat
    OUTSIDE the `except Exception` guard, in an outer `try` carrying only a `finally`,
    so a write failure escaped as a raw traceback — and the ordinary
    `trending-candidates -- --json | head` produced exactly that (`BrokenPipeError`),
    the one class of failure a CLI is most likely to meet."""
    seed_catalog(_FIXTURE_DF)

    class _ClosedPipe(io.StringIO):
        def write(self, text):
            if text.strip():
                raise BrokenPipeError(32, "Broken pipe")
            return 0

    for argv in (["--json"], []):
        monkeypatch.setattr(sys, "stdout", _ClosedPipe())
        # The handler's /dev/null detach runs only when `sys.stdout is sys.__stdout__`
        # (second follow-up review finding, Story 13.3), so a substituted stdout — this
        # one, pytest's, any in-process caller's — is never dup2()'d over.
        assert main(argv) == 1, argv


def test_a_buffered_broken_pipe_exits_1_and_spares_the_hosts_own_stdout_fd(seed_catalog, monkeypatch):
    """Two second-follow-up review findings at once, both verified live.

    1. The previous pass's broken-pipe fix was a NO-OP for the case it was written for.
       stdout is BLOCK-buffered whenever it is a pipe and no realistic envelope fills
       that buffer, so `print` returned cleanly and the BrokenPipeError only surfaced in
       the interpreter's SHUTDOWN flush — outside the guard — as "Exception ignored
       while flushing sys.stdout" and exit 120. `test_a_closed_stdout_pipe_...` above
       could not catch it: its `StringIO` raises inside `write`, i.e. only ever models
       the UNBUFFERED case. This uses a real, really-buffered pipe.
    2. The guard's `os.dup2` retargeted the descriptor for the WHOLE process and nothing
       undid it, so a host that called `main()` in-process came back with its own stdout
       pointed at /dev/null for good.
    """
    read_fd, write_fd = os.pipe()
    os.close(read_fd)  # no reader left: any write to this pipe raises BrokenPipeError
    host_stdout = os.fdopen(write_fd, "w")  # block-buffered, exactly like a real pipe
    monkeypatch.setattr(sys, "stdout", host_stdout)
    seed_catalog(_FIXTURE_DF)
    try:
        assert main(["--json"]) == 1
        assert stat.S_ISFIFO(os.fstat(write_fd).st_mode), "the host's stdout descriptor was retargeted at /dev/null"
    finally:
        with contextlib.suppress(OSError):
            host_stdout.close()


# Stubs the query seam so the probe stays a pure-stdlib CLI run: no kedro bootstrap, no
# catalog, no data — the only thing under test is what the interpreter does with a
# buffered stdout whose reader is gone.
_BROKEN_PIPE_PROBE = """
import sys, types
import pyforge.atlas.trending_candidates as pkg
stub = types.ModuleType("pyforge.atlas.trending_candidates.query")
stub.query_trending_candidates = lambda **kw: {"count": 0, "candidates": [], "filters": kw}
sys.modules[stub.__name__] = stub
pkg.query = stub
from pyforge.atlas.trending_candidates.__main__ import main
raise SystemExit(main(["--json"]))
"""


def test_a_real_interpreter_exit_on_a_broken_pipe_prints_nothing_to_stderr():
    """The user-visible half of the same finding, through a real process exit.

    `PYTHONUNBUFFERED=1` is exported by the ambient dev shell — not by `pixi.toml` and
    not by the Containerfile — and that is exactly what made the previous pass's live
    `--json | head` check appear to pass. This child runs with it explicitly UNSET, so
    stdout is block-buffered the way it is for every operator who does not export it.
    """
    env = {k: v for k, v in os.environ.items() if k != "PYTHONUNBUFFERED"}
    # `pyforge` is a namespace package (no `__file__`), so the src root is derived from
    # a real module inside it: src/pyforge/atlas/trending_candidates/query.py.
    src_root = str(Path(query.__file__).parents[3])
    env["PYTHONPATH"] = os.pathsep.join(filter(None, (src_root, env.get("PYTHONPATH"))))

    read_fd, write_fd = os.pipe()
    proc = subprocess.Popen(
        [sys.executable, "-c", _BROKEN_PIPE_PROBE],
        stdout=write_fd,
        stderr=subprocess.PIPE,
        env=env,
        text=True,
    )
    os.close(write_fd)
    os.close(read_fd)  # the child's writes now have no reader
    _, err = proc.communicate(timeout=120)

    assert proc.returncode == 1, f"rc={proc.returncode} stderr={err!r}"
    assert "Exception ignored" not in err, err
    assert "BrokenPipeError" not in err, err


def test_the_table_header_separates_never_ingested_from_filtered_out(seed_catalog, capsys):
    """Second follow-up review finding, Story 13.3. A `rows=N matched=0` table says "the
    data is here, your filters excluded all of it"; `shown=0` alone said nothing at all —
    so the CAP-1 fallback shape (EVERY row tagged period="all", which is what the dataset
    writes when the HTML scrape breaks across all three windows) answered the default
    `--period weekly` with the same `(no candidates)` as a healthy table nothing
    qualified in, under a fresh build_stamp saying all was well."""
    fallback_shaped = pd.DataFrame(
        [
            {**_FIXTURE_DF.iloc[0].to_dict(), "repo_full_name": name, "period": "all", "source": "search_api_fallback"}
            for name in ("alice/libfoo", "bob/rustcli")
        ]
    )
    seed_catalog(fallback_shaped)

    assert main([]) == 0
    out = capsys.readouterr().out

    assert "rows=2" in out and "matched=0" in out and "shown=0" in out
    assert "(no candidates)" in out


def test_a_multi_line_reason_stays_comment_prefixed(seed_parquet_catalog, capsys):
    """Follow-up review finding, Story 13.3 (verified live in a fresh worktree): a kedro
    `DatasetError` reason is multi-line, and the continuation lines printed with no `#`
    prefix, dropping an un-prefixed `[Errno 2] ...` line between header and rows."""
    seed_parquet_catalog(None)  # declared entry, backing file absent -> DatasetError

    assert main([]) == 0
    out = capsys.readouterr().out

    header, _, rows = out.partition("(no candidates)")
    assert "\n" in header.rstrip("\n"), "expected a multi-line degradation header"
    assert all(line.startswith("# ") for line in header.strip().splitlines())
