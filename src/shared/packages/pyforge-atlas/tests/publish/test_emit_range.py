"""``publish`` gate (Story G2, FR-14 / AD-2 / AD-21) — the emitted static-host layout is
consumed by a DuckDB Range client over a loopback host, proven to read only BYTE RANGES.

This is the load-bearing G2 proof, offline + deterministic. It does NOT push to a live host
(the GitHub Pages publish is the ATTENDED boundary event — DEFERRED, DW-G2). In-loop
everything is fixture-hosted on loopback.

What it proves (each an explicit assertion below, never a hollow pass):

  (a) **HTTP Range consumption** — a DuckDB httpfs client reading the emitted Parquet issues
      Range requests; the Range-capable loopback server answers with ``206 Partial Content``
      and serves STRICTLY FEWER bytes than the whole file (footer + row groups only). A
      whole-file ``200`` read of the Parquet would FAIL the gate.
  (b) **single authoritative layout** — the consumer discovers the chunk path FROM
      ``manifest.json`` (never hardcoded), and every served chunk matches the manifest's
      recorded sha256 / byte size (``verify_manifest``).
  (c) **host-agnostic (AD-2)** — the SAME emitted directory, served from two DIFFERENT
      loopback bases (different ports), yields the same correct result: no host is baked in.
  (d) **correct result over the range-served Parquet** — the D1 ``feedstock-health`` query
      (``ci_red = ci_status IN ('failure','error')``) returns the exact expected count.

The DuckDB ``httpfs`` extension is LOADed OFFLINE from the local extension cache (autoinstall
/ autoload DISABLED — the consumer path never runs a network INSTALL). If httpfs is not
provisioned, the gate SKIPS locally with the provisioning step named (a legitimate
not-provisioned skip, DISTINCT from the range-read-failed case, which always FAILS); under
CI / ``PUBLISH_RANGE_REQUIRED`` it FAILS instead, so a misconfigured CI cannot pass having
verified nothing. See DW-G2-2.
"""

from __future__ import annotations

import http.server
import json
import os
import socketserver
import threading
import urllib.request
from functools import partial
from pathlib import Path

import duckdb
import pandas as pd
import pytest

from pyforge.atlas.publish import (
    ManifestChecksumError,
    chunk_url,
    emit_static_site,
    load_manifest,
    verify_manifest,
)

# A synthetic feedstock-health dataset large enough that a Range read is meaningfully PARTIAL
# (the file is well past DuckDB's small-file whole-prefetch threshold, ~20 row groups). D1
# semantics preserved: ci_red = ci_status IN ('failure','error'). Pattern of 5: 3 red per 5.
# The feedstock_name column is DELIBERATELY WIDE so a query that projects only ci_status
# (the D1 query) skips that column's chunks entirely — projection pushdown over Range makes
# the partial-read dramatic and version-robust, not marginal.
_PATTERN = ["failure", "success", "error", "success", "failure"]
_N = 100_000
_ROW_GROUP_SIZE = 5_000
EXPECTED_RED = _N // 5 * 3  # 60_000


def _seed_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "feedstock_name": [f"feedstock-package-name-number-{i:06d}" for i in range(_N)],
            "ci_status": [_PATTERN[i % len(_PATTERN)] for i in range(_N)],
        }
    )


# ---------------------------------------------------------------------------
# A Range-capable loopback static host that RECORDS what it served, so the gate can
# assert Range/206 actually happened (Python's stock SimpleHTTPRequestHandler does NOT
# honor Range — this handler does, and logs it).
# ---------------------------------------------------------------------------
class _RangeServer:
    def __init__(self, directory: Path):
        self.directory = str(directory)
        self.codes: list[int] = []
        self.ranges: list[str] = []
        self.range_spans: list[tuple[int, int]] = []
        self.bytes_served = 0
        recorder = self

        class Handler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *a):  # keep test output quiet
                pass

            def _send_body(self, path: str):
                length = os.path.getsize(path)
                rng = self.headers.get("Range")
                if rng and rng.startswith("bytes="):
                    spec = rng[len("bytes=") :].split(",")[0]
                    start_s, _, end_s = spec.partition("-")
                    start = int(start_s) if start_s else 0
                    end = int(end_s) if end_s else length - 1
                    end = min(end, length - 1)  # clamp a request past EOF
                    if start > end or start >= length:
                        self.send_response(416)  # Range Not Satisfiable
                        self.send_header("Content-Range", f"bytes */{length}")
                        self.end_headers()
                        recorder.codes.append(416)
                        return
                    with open(path, "rb") as fh:
                        fh.seek(start)
                        data = fh.read(end - start + 1)
                    self.send_response(206)
                    self.send_header("Content-Range", f"bytes {start}-{end}/{length}")
                    self.send_header("Accept-Ranges", "bytes")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    recorder.codes.append(206)
                    recorder.ranges.append(rng)
                    recorder.range_spans.append((start, end))
                    recorder.bytes_served += len(data)
                else:
                    with open(path, "rb") as fh:
                        data = fh.read()
                    self.send_response(200)
                    self.send_header("Accept-Ranges", "bytes")
                    self.send_header("Content-Length", str(length))
                    self.end_headers()
                    self.wfile.write(data)
                    recorder.codes.append(200)
                    recorder.bytes_served += len(data)

            def do_HEAD(self):
                path = self.translate_path(self.path)
                if not os.path.isfile(path):
                    self.send_error(404)
                    return
                length = os.path.getsize(path)
                self.send_response(200)
                self.send_header("Content-Length", str(length))
                self.send_header("Accept-Ranges", "bytes")
                self.end_headers()

            def do_GET(self):
                path = self.translate_path(self.path)
                if not os.path.isfile(path):
                    self.send_error(404)
                    return
                self._send_body(path)

        self._httpd = socketserver.TCPServer(
            ("127.0.0.1", 0), partial(Handler, directory=self.directory)
        )
        self.port = self._httpd.server_address[1]
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)

    def __enter__(self) -> "_RangeServer":
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._httpd.shutdown()
        self._httpd.server_close()  # release the listening socket (Gemini #97 — no fd leak)
        self._thread.join(timeout=5)

    @property
    def base(self) -> str:
        return f"http://127.0.0.1:{self.port}"


def _publish_required() -> bool:
    return bool(os.environ.get("PUBLISH_RANGE_REQUIRED") or os.environ.get("CI"))


def _offline_httpfs_connection() -> "duckdb.DuckDBPyConnection":
    """A DuckDB connection with autoinstall/autoload DISABLED, httpfs LOADed from the local
    cache (OFFLINE). Skips (or fails when required) if httpfs is not provisioned — never a
    silent network INSTALL, never masquerading as a Range-verified pass."""
    con = duckdb.connect(
        config={
            "autoinstall_known_extensions": False,
            "autoload_known_extensions": False,
        }
    )
    try:
        con.execute("LOAD httpfs")
    except Exception as exc:  # duckdb.IOException / CatalogException
        reason = (
            "the DuckDB 'httpfs' extension is not provisioned in the local extension cache, "
            "so the Range client cannot LOAD it offline. Provision it once (attended, network): "
            "`INSTALL httpfs;` in a DuckDB session. Underlying error: "
            f"{type(exc).__name__}: {exc}"
        )
        con.close()
        if _publish_required():
            pytest.fail(f"PUBLISH_RANGE_REQUIRED but httpfs is unprovisioned: {reason}")
        pytest.skip(reason)
    return con


@pytest.fixture()
def emitted_site(tmp_path) -> Path:
    """Emit the layout as a single chunk with many row groups so Range reads are finely partial."""
    target = tmp_path / "site"
    emit_static_site(
        {"core_feedstock_health": _seed_df()},
        target,
        rows_per_chunk=_N,                   # one chunk (the D1 dataset), but...
        row_group_size=_ROW_GROUP_SIZE,      # ...many row groups -> partial Range reads are real
    )
    return target


def _feedstock_chunk_relpath(site: Path) -> str:
    """The chunk path DISCOVERED FROM the manifest (single owner) — never hardcoded here."""
    manifest = load_manifest(site)
    chunks = manifest["datasets"]["core_feedstock_health"]["chunks"]
    assert len(chunks) == 1, chunks
    return chunks[0]["path"]


def _query_red(con: "duckdb.DuckDBPyConnection", url: str) -> int:
    """The D1 feedstock-health count. Projects ONLY ci_status, so over Range the client skips
    the wide feedstock_name column chunks (projection pushdown) — reading only what it needs."""
    row = con.execute(
        "SELECT count(*) FILTER (WHERE ci_status IN ('failure','error')) "
        f"FROM read_parquet('{url}')"
    ).fetchone()
    return int(row[0])


# ---------------------------------------------------------------------------
# (a)+(b)+(d): Range consumption of the emitted, manifest-described layout.
# ---------------------------------------------------------------------------
def test_emitted_layout_consumed_via_http_range(emitted_site):
    site = emitted_site
    manifest = verify_manifest(site)  # (b) served chunks match manifest checksums
    rel = _feedstock_chunk_relpath(site)  # (b) path discovered FROM the manifest
    total_bytes = (site / rel).stat().st_size

    con = _offline_httpfs_connection()
    try:
        with _RangeServer(site) as server:
            url = chunk_url(server.base, rel)  # host-agnostic composition
            red = _query_red(con, url)

            # (d) correct client-side result over the range-served Parquet.
            assert red == EXPECTED_RED, f"ci_red={red}, expected {EXPECTED_RED}"

            # (a) THE load-bearing proof: consumption was via HTTP Range, NOT a whole-file GET.
            assert 206 in server.codes, f"no 206 Partial Content served; codes={server.codes}"
            assert len(server.ranges) > 1, (
                f"expected multiple Range reads (footer + row groups), got {server.ranges}"
            )
            assert 200 not in server.codes, (
                "the Parquet was fetched WHOLE (a 200) — Range not honored; "
                f"codes={server.codes}"
            )
            # Every Range response is a STRICT sub-range (none is the whole file in one shot)...
            lengths = [e - s + 1 for (s, e) in server.range_spans]
            assert all(length < total_bytes for length in lengths), (
                f"a Range response returned the whole file: lengths={lengths} of {total_bytes}"
            )
            # ...and at least one read SEEKS into the file (footer / random-access, start > 0):
            # the client reads byte ranges, it does not stream from byte 0.
            assert any(s > 0 for (s, _e) in server.range_spans), (
                f"no random-access Range read (all started at byte 0): {server.range_spans}"
            )
            # ...and in aggregate it reads FAR less than the whole file (projection pushdown
            # skips the wide feedstock_name column) — reads only what the query needs.
            assert server.bytes_served < total_bytes // 2, (
                "client read too much to be a genuine Range consumer: "
                f"served {server.bytes_served} of {total_bytes} bytes"
            )
    finally:
        con.close()

    # sanity: the manifest is the single layout owner (schema + row_count recorded there).
    ds = manifest["datasets"]["core_feedstock_health"]
    assert ds["row_count"] == _N
    assert [c[0] for c in ds["schema"]] == ["feedstock_name", "ci_status"]


# ---------------------------------------------------------------------------
# (c): host-agnostic — same emitted dir, two different bases, same result.
# ---------------------------------------------------------------------------
def test_host_agnostic_same_dir_two_bases(emitted_site):
    site = emitted_site
    rel = _feedstock_chunk_relpath(site)
    con = _offline_httpfs_connection()
    try:
        results = []
        for _ in range(2):
            with _RangeServer(site) as server:  # a fresh port each time = a different "host"
                results.append(_query_red(con, chunk_url(server.base, rel)))
        assert results == [EXPECTED_RED, EXPECTED_RED], results
    finally:
        con.close()


def test_chunk_url_is_host_agnostic_and_slash_tolerant():
    rel = "core_feedstock_health/core_feedstock_health-0000.parquet"
    assert chunk_url("https://u.github.io/repo", rel) == f"https://u.github.io/repo/{rel}"
    # a mirror base WITH a trailing slash composes identically (AD-2 substitution).
    assert chunk_url("https://mirror.example/prefix/", rel) == chunk_url(
        "https://mirror.example/prefix", rel
    )
    # an empty base -> same-origin relative path (no host baked in).
    assert chunk_url("", rel) == rel


# ---------------------------------------------------------------------------
# Determinism (AD-21): two emits of the same input are byte-identical.
# ---------------------------------------------------------------------------
def test_manifest_and_chunks_byte_stable_across_two_emits(tmp_path):
    df = _seed_df()
    a, b = tmp_path / "a", tmp_path / "b"
    ma = emit_static_site({"core_feedstock_health": df}, a, rows_per_chunk=_N, row_group_size=200)
    mb = emit_static_site({"core_feedstock_health": df}, b, rows_per_chunk=_N, row_group_size=200)
    assert ma == mb
    assert (a / "manifest.json").read_bytes() == (b / "manifest.json").read_bytes()
    rel = ma["datasets"]["core_feedstock_health"]["chunks"][0]["path"]
    assert (a / rel).read_bytes() == (b / rel).read_bytes()


# ---------------------------------------------------------------------------
# Edge cases (Reviewer B territory), all offline / no server needed.
# ---------------------------------------------------------------------------
def test_empty_dataset_emits_schema_only_chunk(tmp_path):
    empty = pd.DataFrame({"feedstock_name": pd.Series([], dtype="string"),
                          "ci_status": pd.Series([], dtype="string")})
    m = emit_static_site({"core_feedstock_health": empty}, tmp_path / "s")
    ds = m["datasets"]["core_feedstock_health"]
    assert ds["row_count"] == 0
    assert len(ds["chunks"]) == 1 and ds["chunks"][0]["rows"] == 0
    # schema is still recorded (a schema-only chunk), and verify passes.
    assert [c[0] for c in ds["schema"]] == ["feedstock_name", "ci_status"]
    verify_manifest(tmp_path / "s")


def test_multichunk_split_when_rows_exceed_chunk(tmp_path):
    m = emit_static_site({"core_feedstock_health": _seed_df()}, tmp_path / "s",
                         rows_per_chunk=40_000, row_group_size=_ROW_GROUP_SIZE)
    chunks = m["datasets"]["core_feedstock_health"]["chunks"]
    assert [c["rows"] for c in chunks] == [40_000, 40_000, 20_000]  # 100_000 rows / 40_000
    assert sum(c["rows"] for c in chunks) == _N
    # chunk paths are zero-padded + ordered (stable, single-owner naming).
    assert [c["path"].rsplit("/", 1)[1] for c in chunks] == [
        "core_feedstock_health-0000.parquet",
        "core_feedstock_health-0001.parquet",
        "core_feedstock_health-0002.parquet",
    ]
    verify_manifest(tmp_path / "s")


def test_count_star_reads_footer_only_over_range(emitted_site):
    """``count(*)`` is answered from the Parquet FOOTER metadata alone — the clearest
    "reads only a byte subrange" proof: a single Range read of the tail, not the data."""
    site = emitted_site
    rel = _feedstock_chunk_relpath(site)
    total_bytes = (site / rel).stat().st_size
    con = _offline_httpfs_connection()
    try:
        with _RangeServer(site) as server:
            n = con.execute(
                f"SELECT count(*) FROM read_parquet('{chunk_url(server.base, rel)}')"
            ).fetchone()[0]
            assert n == _N
            assert 200 not in server.codes and 206 in server.codes
            assert server.bytes_served < total_bytes // 10, (
                f"count(*) should read ~footer only; served {server.bytes_served} of {total_bytes}"
            )
    finally:
        con.close()


def test_verify_manifest_detects_corruption(emitted_site):
    site = emitted_site
    rel = _feedstock_chunk_relpath(site)
    # corrupt one byte of a chunk -> checksum mismatch must be caught (no silent wrong answer).
    data = bytearray((site / rel).read_bytes())
    data[len(data) // 2] ^= 0xFF
    (site / rel).write_bytes(bytes(data))
    with pytest.raises(ManifestChecksumError):
        verify_manifest(site)


def test_verify_manifest_rejects_path_traversal(emitted_site):
    # AUD-ATLAS-019: chunk paths must stay under the site root.
    site = emitted_site
    manifest = json.loads((site / "manifest.json").read_text(encoding="utf-8"))
    name = next(iter(manifest["datasets"]))
    manifest["datasets"][name]["chunks"][0]["path"] = "../etc/passwd"
    (site / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ManifestChecksumError, match="unsafe chunk path|escapes"):
        verify_manifest(site)


def test_non_range_client_still_gets_whole_file(emitted_site):
    """A plain (non-Range) GET falls back to a 200 whole-file response — the layout is a plain
    static site, so a dumb client still works (it just doesn't get the Range optimization)."""
    site = emitted_site
    rel = _feedstock_chunk_relpath(site)
    with _RangeServer(site) as server:
        with urllib.request.urlopen(f"{server.base}/{rel}") as resp:  # no Range header
            body = resp.read()
            assert resp.status == 200
    assert body == (site / rel).read_bytes()
    assert 200 in server.codes and 206 not in server.codes


def test_range_past_eof_is_clamped_not_crashing(emitted_site):
    """A Range whose end runs past EOF is clamped to the last byte (206), and a start past EOF
    is a clean 416 — neither crashes the static host."""
    site = emitted_site
    rel = _feedstock_chunk_relpath(site)
    size = (site / rel).stat().st_size
    with _RangeServer(site) as server:
        # end past EOF -> clamped 206
        req = urllib.request.Request(f"{server.base}/{rel}",
                                     headers={"Range": f"bytes=0-{size + 10_000}"})
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 206
            assert len(resp.read()) == size
        # start past EOF -> 416
        req2 = urllib.request.Request(f"{server.base}/{rel}",
                                      headers={"Range": f"bytes={size + 5}-{size + 10}"})
        try:
            urllib.request.urlopen(req2)
            got = 200
        except urllib.error.HTTPError as e:
            got = e.code
        assert got == 416, got


def test_traversal_dataset_name_is_rejected_before_any_deletion(tmp_path):
    """Reviewer-B MUST-FIX: a dataset name is joined onto target_dir and its dir is rmtree'd on
    re-emit — an unsanitized '../x' / 'a/b' / leading-slash name would delete a directory OUTSIDE
    target_dir. All must be rejected BEFORE any filesystem mutation."""
    target = tmp_path / "site"
    sibling = tmp_path / "precious"
    sibling.mkdir()
    (sibling / "important.txt").write_text("keep me", encoding="utf-8")

    for bad in ("../precious", "..", "a/b", "/abs", "foo\\bar", "."):
        with pytest.raises(ValueError, match="unsafe dataset name|non-empty"):
            emit_static_site({bad: pd.DataFrame({"x": [1]})}, target)
    assert (sibling / "important.txt").read_text(encoding="utf-8") == "keep me"  # never touched


def test_late_failure_does_not_destroy_a_prior_good_site(tmp_path):
    """Reviewer-B SHOULD-FIX: all names+types validate UP FRONT, so a bad type on a LATER dataset
    can't leave the site half-rewritten against a stale manifest — the first dataset's dir is
    never rmtree'd because validation fails before any mutation."""
    target = tmp_path / "site"
    emit_static_site({"core_feedstock_health": pd.DataFrame({"x": [1, 2, 3]})}, target, rows_per_chunk=2)
    good_chunks = sorted((target / "core_feedstock_health").glob("*.parquet"))
    assert len(good_chunks) == 2

    # a re-emit whose SECOND dataset has a bad type must raise BEFORE touching the first dataset.
    with pytest.raises(TypeError):
        emit_static_site(
            {"core_feedstock_health": pd.DataFrame({"x": [9]}), "zz": [1, 2, 3]}, target, rows_per_chunk=2
        )
    # the prior good site is intact (still 2 chunks + a coherent manifest).
    assert sorted((target / "core_feedstock_health").glob("*.parquet")) == good_chunks
    verify_manifest(target)  # still coherent — not corrupted against a stale manifest
