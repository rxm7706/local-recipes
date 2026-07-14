"""OSV-DB offline provisioning spike — the empirical proof test (Story 1.4).

This is a SPIKE proof, not the osv engine (that is Story 1.5). It touches ZERO
production ``python_deptry_osv_scanner`` code: a **spike-local** subprocess
helper drives the real ``osv-scanner`` binary directly (NOT ``cli.main`` and
NOT ``engines._engine_env``), against a hermetic offline database built at test
time from the readable in-repo OSV JSON under ``fixtures/osv-db/`` by
``fixtures/osv_db_builder.build_offline_db``.

What it proves (the § I/O & Edge-Case Matrix of the story spec):
  a. a vulnerable pin, run ``--offline``, detects the seeded advisory
     (osv exit 1; JSON names ``PDOS-FIXTURE-0001`` + ``pdos-vuln-fixture`` +
     the CVSS-v3.1-CRITICAL vector on that vulnerability) with ZERO network;
  b. a clean pin (``==2.0.0``, outside the affected ``versions``) → osv exit 0,
     no findings — offline precision;
  c. a lockfile NOT named ``requirements.txt`` is still parsed when the parser
     is forced with ``-L <parser>:<path>`` (the temp-name constraint is
     removable; the exact parser id is ``requirements.txt``);
  d. the DB-absent + ``--offline`` cold start is NOT silently a real clean: the
     output file IS written and its bytes are **byte-for-byte identical** to a
     real clean scan (asserted here), yet it exits **127** with a distinct
     "no offline database" stderr signal — the false-green trap. A consumer
     keying on the JSON body alone would false-green; Story 1.5 must instead
     detect the absent DB deterministically (a cache-file pre-flight, see the
     decision record § 4) and route to ``indeterminate``, never ``clean``;
  e. a manifest with no packages exits **128** and writes **no output file** —
     the architecture's no-packages → coverage-skipped path (distinct from d);
  f. the builder is twice-run byte-identical (fixed mtime; stored uncompressed;
     no wall clock) and names each entry by advisory id.

Hermeticity: ``--offline`` is the no-egress guarantee for the osv subprocess
(it is outside the in-process socket-deny harness in ``conftest.py``, by the
architecture's "network confined to named engine subprocesses" model); the
only advisory source is the in-repo fixture DB pointed at by
``OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY``. This test trusts ``--offline`` for the
zero-egress property (it does not run the subprocess in a network namespace) —
see the decision record's hermeticity residual-risk note.

If ``osv-scanner`` is absent this test HARD-FAILS (never skips), matching the
Story-1.3 provisioned-engine convention: the engines are conda run-deps, so a
missing binary is a broken environment, not an excused test.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

# --- locations -------------------------------------------------------------

TESTS_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = TESTS_ROOT / "fixtures"
OSV_RECORDS_DIR = FIXTURES / "osv-db" / "pypi"
LOCKFILE_VULNERABLE = FIXTURES / "lockfiles" / "osv-vulnerable" / "requirements.txt"
LOCKFILE_CLEAN = FIXTURES / "lockfiles" / "osv-clean" / "requirements.txt"

# The empirically-verified osv-scanner (2.4.0) pip-requirements parser id used
# with ``-L <parser>:<path>`` — recorded in the decision record § 9.
OSV_PIP_PARSER_ID = "requirements.txt"

# Fixture facts (assert on content, never on osv-scanner's volatile bytes).
FIXTURE_ADVISORY_ID = "PDOS-FIXTURE-0001"
FIXTURE_PACKAGE = "pdos-vuln-fixture"
FIXTURE_CVSS_VECTOR = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"

def _osv_scanner_bin() -> str:
    """Return the ``osv-scanner`` path, HARD-FAILING (never skipping) if it is
    not on PATH — the engine is a provisioned conda run-dep (NFR-C1)."""
    binary = shutil.which("osv-scanner")
    if binary is None:
        pytest.fail(
            "osv-scanner is not on PATH — the vulnerability engine is a "
            "provisioned conda run-dep; a missing binary is a broken "
            "environment, not an excused (skipped) test. Run this suite via "
            "`pixi run -e python-deptry-osv-scanner python-deptry-osv-scanner-test`."
        )
    return binary


def _load_builder():
    """Import ``fixtures/osv_db_builder`` by path (the fixtures dir is data,
    not an importable package) — the same helper Story 1.5 reuses."""
    module_path = FIXTURES / "osv_db_builder.py"
    spec = importlib.util.spec_from_file_location("osv_db_builder", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class OsvRun:
    """One osv-scanner subprocess result: its exit code, the raw output-file
    text (``None`` when no file was written), the parsed JSON document
    (``None`` when the file was absent or unparseable), and captured stderr."""

    def __init__(
        self,
        exit_code: int,
        raw_output: str | None,
        document: dict | None,
        stderr: str,
    ) -> None:
        self.exit_code = exit_code
        self.raw_output = raw_output
        self.document = document
        self.stderr = stderr

    def _packages(self) -> list[dict]:
        doc = self.document or {}
        return [
            pkg
            for result in doc.get("results", [])
            for pkg in result.get("packages", [])
        ]

    def vulnerabilities(self) -> list[dict]:
        return [vuln for pkg in self._packages() for vuln in pkg.get("vulnerabilities", [])]

    def vulnerability_ids(self) -> list[str]:
        return [vuln["id"] for vuln in self.vulnerabilities()]

    def package_names(self) -> list[str]:
        return [pkg["package"]["name"] for pkg in self._packages()]

    def vulnerability(self, advisory_id: str) -> dict | None:
        for vuln in self.vulnerabilities():
            if vuln.get("id") == advisory_id:
                return vuln
        return None


def _run_osv_offline(
    tmp_path: Path,
    cache_root: Path,
    lockfile: Path,
    *,
    parser_id: str = OSV_PIP_PARSER_ID,
) -> OsvRun:
    """The spike-local runner: invoke ``osv-scanner`` directly (argv list, no
    shell, stdin from /dev/null), fully offline, forcing the pip parser with
    ``-L <parser>:<path>`` and writing pure JSON to a temp file.

    This deliberately mirrors — but does NOT import — the ``_engine_env``
    machine-output-to-temp-file pattern Story 1.5 will reuse.
    """
    output_file = tmp_path / "osv-output.json"
    if output_file.exists():
        output_file.unlink()
    argv = [
        _osv_scanner_bin(),
        "scan",
        "--offline",  # NFR-S2: the no-egress guarantee for the subprocess.
        "--format",
        "json",
        "--output-file",  # 2.4.0 renamed --output -> --output-file (§ 9).
        str(output_file),
        "-L",
        f"{parser_id}:{lockfile}",
    ]
    env = os.environ.copy()
    # Pin the DB source to the hermetic fixture cache (overrides osv-scanner's
    # default per-user cache so no developer's real DB can leak in).
    env["OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY"] = str(cache_root)
    env["NO_COLOR"] = "1"
    try:
        completed = subprocess.run(
            argv,
            cwd=str(tmp_path),
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,  # exit code is content, never a raise.
        )
    except subprocess.TimeoutExpired:  # pragma: no cover - safety net
        pytest.fail("osv-scanner exceeded the 120s bound (should be sub-second offline)")

    raw_output: str | None = None
    document: dict | None = None
    if output_file.exists():
        raw_output = output_file.read_text(encoding="utf-8")
        if raw_output.strip():
            try:
                document = json.loads(raw_output)
            except json.JSONDecodeError:
                # Surface as a clean assertion failure downstream, not a raise.
                document = None
    return OsvRun(completed.returncode, raw_output, document, completed.stderr)


@pytest.fixture
def offline_cache(tmp_path) -> Path:
    """Build the hermetic offline OSV DB into a tmp cache and hand back the
    cache root (the ``OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY`` value)."""
    builder = _load_builder()
    cache_root = tmp_path / "cache"
    return builder.build_offline_db(OSV_RECORDS_DIR, cache_root)


# --- (a) vulnerable pin, offline -> detects the seeded advisory --------------


def test_vulnerable_pin_detects_seeded_advisory_offline(tmp_path, offline_cache):
    run = _run_osv_offline(tmp_path, offline_cache, LOCKFILE_VULNERABLE)

    assert run.exit_code == 1, run.stderr  # osv: vulns-found
    assert FIXTURE_ADVISORY_ID in run.vulnerability_ids()
    assert FIXTURE_PACKAGE in run.package_names()
    # The CVSS-v3.1 CRITICAL vector is carried ON THE MATCHED vulnerability
    # (scoped to our advisory, not merely present somewhere in the document).
    matched = run.vulnerability(FIXTURE_ADVISORY_ID)
    assert matched is not None
    assert FIXTURE_CVSS_VECTOR in json.dumps(matched)


# --- (b) clean pin, offline -> exit 0, no findings ---------------------------


def test_clean_pin_is_clean_offline(tmp_path, offline_cache):
    run = _run_osv_offline(tmp_path, offline_cache, LOCKFILE_CLEAN)

    assert run.exit_code == 0, run.stderr  # osv: no-vulns
    assert run.vulnerability_ids() == []
    assert run.document is not None
    assert run.document.get("results", []) == []


# --- (c) a non-`requirements.txt` name is parsed via -L parser:path ----------


def test_non_requirements_txt_name_is_parsed_via_parser_override(
    tmp_path, offline_cache
):
    # Copy the vulnerable pins to a file whose name is NOT requirements.txt.
    oddly_named = tmp_path / "pdos-osv-vuln-abc123.txt"
    oddly_named.write_text(
        LOCKFILE_VULNERABLE.read_text(encoding="utf-8"), encoding="utf-8"
    )
    run = _run_osv_offline(
        tmp_path, offline_cache, oddly_named, parser_id=OSV_PIP_PARSER_ID
    )

    # The parser override removes the "input must be named requirements.txt"
    # constraint — the arbitrarily-named file is still parsed and matched.
    assert run.exit_code == 1, run.stderr
    assert FIXTURE_ADVISORY_ID in run.vulnerability_ids()


# --- (d) DB absent + offline -> a cold-start signal, NEVER a silent clean ----


def test_db_absent_offline_is_not_silently_a_clean_scan(tmp_path, offline_cache):
    """The cold-start false-green trap. With no local DB, osv-scanner still
    WRITES an output file whose bytes are identical to a real clean scan, yet
    it exits 127. A consumer keying only on the JSON body would false-green;
    the exit code is the honest distinguisher. Story 1.5 detects the absent DB
    with a deterministic cache-file pre-flight (decision record § 4) and maps
    it to ``indeterminate``."""
    empty_cache = tmp_path / "empty-cache"
    empty_cache.mkdir()  # exists, but holds no osv-scanner/<eco>/all.zip

    absent = _run_osv_offline(tmp_path, empty_cache, LOCKFILE_VULNERABLE)
    # A genuine clean scan of the SAME vulnerable pin against the REAL db would
    # be impossible (it is vulnerable), so compare against the true clean run.
    clean = _run_osv_offline(tmp_path, offline_cache, LOCKFILE_CLEAN)

    # The cold-start exit is the general-error code (127), explicitly NOT 0 and
    # NOT the same as a real clean scan — the exit code is the honest signal.
    assert absent.exit_code == 127, absent.stderr
    assert absent.exit_code != 0
    assert absent.exit_code != clean.exit_code
    # An output file IS written on the DB-absent path (not merely skipped)...
    assert absent.raw_output is not None
    assert clean.raw_output is not None
    # ...and it is BYTE-FOR-BYTE identical to the clean scan's output — this is
    # the trap the record documents: the JSON body cannot distinguish the two.
    assert absent.raw_output == clean.raw_output
    assert absent.document is not None and absent.document.get("results") == []
    # NB: we deliberately do NOT assert on osv's stderr text — the decision
    # record labels it volatile INFO chatter a 2.x patch can reword, and Story
    # 1.5 must not branch on it. The exit code (127) above is the only contract
    # anchor for this row (follow-up review L1).


# --- (e) no packages in the manifest -> exit 128, no output file -------------


def test_no_packages_manifest_exits_128_with_no_output(tmp_path, offline_cache):
    """The architecture's no-packages path (distinct from DB-absent). A
    manifest osv finds no package sources in exits 128 and writes NO output
    file at all — coverage skipped, which Story 1.5 routes to
    ``indeterminate`` (never a confident clean)."""
    empty_manifest = tmp_path / "requirements.txt"
    empty_manifest.write_text("\n", encoding="utf-8")

    run = _run_osv_offline(tmp_path, offline_cache, empty_manifest)

    assert run.exit_code == 128, run.stderr
    assert run.raw_output is None  # no output file written on 128
    assert run.document is None


# --- (f) builder determinism + naming ----------------------------------------


def test_builder_is_twice_run_byte_identical(tmp_path):
    builder = _load_builder()
    root_one = builder.build_offline_db(OSV_RECORDS_DIR, tmp_path / "one")
    root_two = builder.build_offline_db(OSV_RECORDS_DIR, tmp_path / "two")
    zip_one = (root_one / "osv-scanner" / "PyPI" / "all.zip").read_bytes()
    zip_two = (root_two / "osv-scanner" / "PyPI" / "all.zip").read_bytes()
    assert zip_one == zip_two  # fixed mtime + fixed attrs + stored -> reproducible


def test_builder_entries_are_each_named_by_advisory_id(tmp_path):
    import zipfile

    builder = _load_builder()
    root = builder.build_offline_db(OSV_RECORDS_DIR, tmp_path / "db")
    with zipfile.ZipFile(root / "osv-scanner" / "PyPI" / "all.zip") as zf:
        names = zf.namelist()
    # The seeded advisory is present, and EVERY entry follows the <id>.json flat
    # naming contract — asserted as membership/pattern, not one-element equality,
    # so adding advisories (Story 2.5) does not break this test.
    assert f"{FIXTURE_ADVISORY_ID}.json" in names
    assert all(name.endswith(".json") and "/" not in name for name in names)


def test_builder_refuses_empty_records_dir(tmp_path):
    """An empty records dir must fail loud — an empty all.zip reads as a clean
    scan (the false-green this project exists to prevent)."""
    builder = _load_builder()
    empty_records = tmp_path / "no-records"
    empty_records.mkdir()
    with pytest.raises(ValueError, match="no OSV records"):
        builder.build_offline_db(empty_records, tmp_path / "db")


# --- (g) follow-up Opus review: the empty/hollow-DB false-green (H1) ----------


def test_present_but_empty_db_false_greens_and_a_nonemptiness_preflight_catches_it(
    tmp_path,
):
    """H1 (the cardinal false-green the inline review missed): the BUILDER
    refuses to make an empty DB, but an EXTERNAL provisioner (a partial download
    or a mis-populated cache) can leave a present-but-empty ``all.zip``. Against
    it, osv-scanner exits **0** with ``results: []`` on a VULNERABLE input —
    NEITHER the exit code NOR the body distinguishes it from a real clean scan.
    This pins the hazard empirically and proves the ONLY defense the decision
    record now mandates for Story 1.5: a **non-emptiness pre-flight** (the zip
    opens AND has >=1 ``<id>.json`` entry), resolved at osv's case-sensitive
    ``PyPI`` segment."""
    import zipfile

    # Externally provision a present-but-EMPTY DB (bypass the builder's guard).
    db_dir = tmp_path / "cache" / "osv-scanner" / "PyPI"
    db_dir.mkdir(parents=True)
    empty_zip = db_dir / "all.zip"
    with zipfile.ZipFile(empty_zip, "w"):
        pass  # a valid zip with zero entries

    run = _run_osv_offline(tmp_path, tmp_path / "cache", LOCKFILE_VULNERABLE)

    # The false-green: a KNOWN-vulnerable pin reads as clean/exit-0 — the exit
    # code and the body are both indistinguishable from a real clean scan.
    assert run.exit_code == 0, run.stderr
    assert run.vulnerability_ids() == []
    assert run.document is not None and run.document.get("results") == []

    # The mandated Story-1.5 defense: a non-emptiness pre-flight catches it,
    # where a plain os.path.exists() (the pre-review disposition) would NOT.
    assert empty_zip.exists()  # an existence check PASSES — insufficient
    with zipfile.ZipFile(empty_zip) as zf:
        advisory_entries = [n for n in zf.namelist() if n.endswith(".json")]
    assert advisory_entries == []  # the non-emptiness pre-flight fires here


def test_osv_requires_case_sensitive_PyPI_dir(tmp_path):
    """M1: osv-scanner's on-disk ecosystem segment is case-sensitive ``PyPI``,
    NOT the lowercase ``pypi`` Ecosystem enum value. A DB provisioned at
    lowercase is never loaded — Story 1.5's pre-flight must resolve the osv
    casing, not interpolate the enum."""
    builder = _load_builder()
    # Build a real DB, then relocate all.zip to a LOWERCASE `pypi/` dir.
    root = builder.build_offline_db(OSV_RECORDS_DIR, tmp_path / "cache")
    good = root / "osv-scanner" / "PyPI" / "all.zip"
    lower_dir = root / "osv-scanner" / "pypi"
    lower_dir.mkdir()
    good.rename(lower_dir / "all.zip")
    (root / "osv-scanner" / "PyPI").rmdir()

    run = _run_osv_offline(tmp_path, root, LOCKFILE_VULNERABLE)
    # osv does NOT find the lowercase DB → cold-start 127 (never a match), which
    # is why 1.5 must provision + pre-flight at the exact `PyPI` casing.
    assert run.exit_code == 127, run.stderr


# --- (h) follow-up Opus review: builder fail-loud hardening (M5/M6/L5) --------


def test_builder_non_object_json_raises_valueerror_not_attributeerror(tmp_path):
    """M5: a record whose top level is a JSON array/string/number is MALFORMED
    (ValueError), never an AttributeError from ``.get`` on a non-dict."""
    builder = _load_builder()
    records = tmp_path / "records"
    records.mkdir()
    (records / "bad.json").write_text('["not", "an", "object"]', encoding="utf-8")
    with pytest.raises(ValueError, match="top level"):
        builder.build_offline_db(records, tmp_path / "db")


def test_builder_rejects_unmatchable_record(tmp_path):
    """M6/L4: a record with a valid id + PyPI ecosystem but no matchable spec
    (no ``versions``/``ranges``) would be shelved yet never match — a silent
    false-clean coverage hole. It must fail loud."""
    builder = _load_builder()
    records = tmp_path / "records"
    records.mkdir()
    (records / "PDOS-UNMATCHABLE.json").write_text(
        json.dumps(
            {
                "id": "PDOS-UNMATCHABLE",
                "affected": [{"package": {"ecosystem": "PyPI", "name": "foo"}}],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="concrete version spec"):
        builder.build_offline_db(records, tmp_path / "db")


def test_builder_rejects_case_variant_json_extension(tmp_path):
    """L5: a record dropped as ``.JSON`` would be silently skipped by the
    case-sensitive glob — a partial-drop coverage hole. Fail loud."""
    builder = _load_builder()
    records = tmp_path / "records"
    records.mkdir()
    # A valid record the exact glob WOULD pick up...
    shutil.copy(OSV_RECORDS_DIR / f"{FIXTURE_ADVISORY_ID}.json", records / f"{FIXTURE_ADVISORY_ID}.json")
    # ...plus a case-variant one it would silently skip.
    (records / "PDOS-0002.JSON").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="non-canonical .json"):
        builder.build_offline_db(records, tmp_path / "db")
