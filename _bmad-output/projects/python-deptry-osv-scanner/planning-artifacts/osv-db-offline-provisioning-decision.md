---
title: 'OSV-DB offline provisioning — decision record (Story 1.4 spike)'
type: 'decision-record'
status: 'accepted'
created: '2026-07-14'
story: '1.4'
gates: ['1.5', '2.4']
does_not_gate: ['1.3']
downstream_owners: ['1.5', '2.4', '3.1', '5.1', '1.7']
evidence_env: 'osv-scanner 2.4.0 / osv-scalibr 0.4.5, pixi env `python-deptry-osv-scanner`'
---

# OSV-DB offline provisioning — decision record

This is the tracked output of the **Story 1.4 spike**. It resolves the offline
vulnerability-data open questions (architecture open-Q3/Q7/Q8b, Gap-analysis
#4) so that **Story 1.5** (the osv engine) and **Story 2.4** (stale-DB verdict
semantics) inherit settled decisions instead of research. It **gates 1.5 + 2.4**
and explicitly **does NOT gate 1.3** (deptry has no OSV surface).

Every recommendation below is grounded in one of: the live `osv-scanner scan
--help` (2.4.0), the **empirical proof test**
`tests/conformance/test_osv_offline_db_spike.py` + its deterministic fixture DB
builder, the **frozen** `VulnData{source, snapshot_at, max_age_ok}` fields in
`models.py` / `data/report-schema.json`, and the in-repo provisioning **pattern**
in `.claude/skills/conda-forge-expert/scripts/cve_manager.py`.

## Empirical findings (the spike's measured ground truth)

Reproduced against **osv-scanner 2.4.0 / osv-scalibr 0.4.5** in the
`python-deptry-osv-scanner` pixi env. The committed proof test asserts all of
this hermetically (`--offline`, in-repo JSON, no network, no download):

| Fact | Measured value |
|---|---|
| Offline DB layout osv-scanner loads | `<cache>/osv-scanner/<Ecosystem>/all.zip` — e.g. `.../osv-scanner/PyPI/all.zip`. Confirmed by reproducing the exact tree `osv-scanner --offline --download-offline-databases` writes AND by matching a seeded advisory against a hand-built zip. |
| Cache-dir selector | env var **`OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY`** (no `--local-db-path` flag exists in 2.4.0). |
| Zip internal structure | **flat** entries named `<advisory-id>.json` (e.g. `PDOS-FIXTURE-0001.json`); no manifest, no index, no signature file. A hand-built zip of readable OSV JSON is consumed directly. |
| Version matching | `affected[].versions: ["1.0.0"]` (an explicit list) matches **without** a `ranges` block. The fixture carries no `ranges` and still matches version-exact. |
| `-L` / `--lockfile` parser override | present in 2.4.0 as `-L <parser>:<path>` (repeatable). The pip-requirements parser id is **`requirements.txt`**. A file NOT named `requirements.txt` is parsed correctly when the parser is forced this way. |
| JSON output flag | `--output` is **DEPRECATED in 2.4.0 in favor of `--output-file`** (emits a stderr deprecation warning). The proof test + Story 1.5 use `--output-file`. `--format json` + `--output-file <path>` writes a pure JSON document to the file. |
| Observed exit codes | **0** = no vulnerabilities (clean); **1** = vulnerabilities found (expected non-error); **127** = DB-absent-offline cold start (see § 4); **128** = no package sources found in the manifest. |
| **DB-absent + `--offline`** (cold start) | exit **127**; stderr: `could not load db for PyPI ecosystem: unable to fetch OSV database: no offline version of the OSV database is available`; the JSON output file **is written** with **`results: []`** — a body the proof test asserts is **byte-for-byte identical to a real clean scan**. Only the **exit code (127)** honestly distinguishes it; the stderr text is INFO chatter, **not** a stable contract. A **missing** cache directory behaves identically to an empty one (both 127). |
| **No packages + `--offline`** | exit **128**; stderr `No package sources found, --help for usage information.`; **no output file is written** (distinct from the DB-absent 127 above). The architecture's no-packages → coverage-skipped path → `indeterminate`. |
| Determinism | the builder writes `all.zip` **stored uncompressed** (`ZIP_STORED`) with a fixed DOS-epoch mtime (`1980-01-01`) + fixed attrs → **twice-run byte-identical on any machine** (DEFLATE output is zlib-build-dependent, so compression is dropped for cross-platform reproducibility; the fixture is tiny). Asserted by the proof test. |

The exact offline invocation that works (argv + env), as the proof test runs it:

```
env OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY=<cache_root> NO_COLOR=1 \
  osv-scanner scan --offline --format json --output-file <tmp.json> \
    -L requirements.txt:<lockfile-path>
```

where `<cache_root>/osv-scanner/PyPI/all.zip` holds the OSV JSON records.

---

## 1. Mechanism — how the tool reads an offline DB

**Recommendation:** use osv-scanner **`--offline`** reading
`OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY` → per-ecosystem `<Ecosystem>/all.zip`
(matches architecture Gap-C "conda package `{ecosystem}/all.zip`"). **Reject
`--offline-vulnerabilities` alone**: it only disables the *vulnerability*
network calls and still egresses on transitive/dep resolution (Gap-C/open-Q7);
`--offline` disables **all** network and is the only NFR-S2-safe switch.
Production provisioning of the DB itself = a conda-packaged DB if/when one
exists, else osv-native `--download-offline-databases` (explicit opt-in), else
an air-gap mirror (§ 8).

**Evidence:** the empirical layout row above; `--help` shows `--offline` = "run
in offline mode, disabling any features requiring network access" vs
`--offline-vulnerabilities` = "checks for vulnerabilities using local databases
that are already cached" (narrower). **Owner:** Story 1.5 wires `--offline` into
the osv runner.

## 2. Staleness (feeds FR12)

**Recommendation:** define **stale = DB `snapshot_at` older than a configurable
`--db-max-age`, default 7 days**. `snapshot_at` source = the provisioning
timestamp (conda package build-date, or a recorded manifest timestamp for the
mirror path; NOT `datetime.now()` at scan). Stale → `VulnData(max_age_ok=False)`
→ **Story 2.4** degrades the verdict to at least `warn`/`indeterminate`, never a
confident `clean`. 1.4 only **defines** stale; it does not implement the
degrade.

**Evidence:** `VulnData{source, snapshot_at, max_age_ok}` already exist **frozen**
in `models.py` + `data/report-schema.json` (verified this story) — the record
documents how to *populate* them, it does not redefine them. **Owner:** the
threshold + `max_age_ok` computation is Story **2.4**; the config key
(`db-max-age`) lands via `config.py` when 2.4 needs it.

## 3. Trust anchor / authenticity (NFR-S8)

**Recommendation:** production DB trust rides on **channel integrity** — a
conda-packaged DB inherits conda's sha256 + (optionally) sigstore signing
(CEP-27); the mirror path (§ 8) carries a **sha256 manifest** mirroring
`cve_manager.py`'s checksum discipline. A swapped / empty / unverifiable DB must
**fail loud** (never a silent degrade to clean). The **fixture DB** is trusted
by in-repo provenance: it is built at test time from readable, reviewed JSON —
there is no binary blob committed.

**Evidence:** `cve_manager.py` already streams a checksummed per-ecosystem
`all.zip` with atomic writes; the empirical finding that a hand-built zip needs
**no signature/index** means authenticity is entirely the *provisioning
channel's* responsibility, not the loader's. **Owner:** Story 1.5 (fail-loud on
unverifiable/empty DB) + Story 5.1 (documents the channel trust model).

## 4. Cold-start UX + actionable nudge (persona P8)

**Recommendation:** with **no DB in offline mode**, vulnerability coverage is
**skipped → `indeterminate`** (exit 1), **never** a confident `clean`. Emit a
stderr **actionable nudge**, draft:

> No local OSV database found. Provision one (`osv-scanner
> --download-offline-databases`, a conda OSV-DB package, or point
> `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY` / `--db-path` at an existing cache).
> This gate never fetches vulnerability data silently.

`--db-path` is *our wrapper* flag mapping to
`OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY`; the flag itself lands in Story 1.5/3.1.

**Evidence + the critical trap:** the DB-absent run exits **127**, but its JSON
body (`results: []`) is **byte-for-byte identical to a real clean scan** (the
proof test asserts this). A consumer keying on the JSON body alone would
**false-green** — and osv-scanner's own return code + stderr are **discarded**
by the current `_engine_env` seam (see the seam hand-off below), so a naive
verbatim reuse would read the cold start as clean.

**Disposition (deterministic pre-flight, NOT stderr parsing):** Story 1.5 must
detect the absent DB **before trusting the scan** with a deterministic
pre-flight — check `os.path.exists(<cache>/osv-scanner/<ecosystem>/all.zip)` for
each in-scope ecosystem (1.5 sets `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY`, so it
owns this path). Missing DB → route to **`indeterminate`** (coverage-skipped,
exit 1) + emit the nudge, *without* running osv or parsing its output at all.
Do **not** branch security control-flow on the stderr string — it is INFO
chatter a 2.x patch can reword (§ 6 pins `<3` precisely because flags/text shift
within 2.x); the surfaced exit **127** is a corroborating signal, not the
primary one. This reconciles the architecture conflict flagged below: a
DB-absent 127 is a *coverage gap* → `indeterminate`, not the blanket `127 →
error → exit 2` the architecture's pinned-engine table assumes; any **other**
127 (osv genuinely crashing with a DB present) stays a typed `error`. **Owner:**
Story 1.5 (pre-flight + mapping + nudge), Story 3.1 (`--db-path`).

## 5. Online opt-in disposition

**Recommendation:** **v1 = offline-only-everywhere** + trivial explicit
provisioning; **no silent network fetch ever** (NFR-S2). Any online-query mode
is an explicit, non-default flag and is **deferred beyond v1** (contract
documented, unbuilt). This resolves the PRD's "currently unowned" opt-in gap by
**scoping it out of the v1 default** rather than leaving it ambiguous.

**Evidence:** NFR-S2 (deny-by-default egress, enforced by the socket-deny
harness) is incompatible with a default online path; the empirical finding that
`--offline` + a provisioned DB fully covers the gate means online querying buys
nothing for v1. **Owner:** deferred (post-v1); documented here as out-of-scope so
1.5 does not build it.

## 6. Engine version ranges (NFR-C1) + detection

**Recommendation:** pin **`osv-scanner >=2.4.0,<3`** (the 2.x line embeds
scalibr and the exit-code/flag contract proven here; 3.x may move the exit codes
or rename flags — note `--output`→`--output-file` already shifted *within* 2.x)
and **`deptry >=0.25.1,<1`** (pre-1.0 minors can move DEP codes). Detection:
parse `<engine> --version` at run start; out-of-range → **fail loud** (a typed
error, not a silent best-effort) — note this requires capturing the engine's
**stdout**, which the current `_engine_env` discards, so it is a further seam
change beyond `extra_env` (see the hand-off below). **NOT applied to `pixi.toml`
in this story** —
a worktree re-solve is toxic per `deferred-work.md`; this is a documented
hand-off.

**Evidence:** the whole empirical contract here (layout, exit codes, `-L`,
`--output-file`) is measured on exactly 2.4.0 / scalibr 0.4.5, so the upper
bound `<3` is the tested-compatibility ceiling. **Owner:** Story 1.5/1.7 apply
the pins to `pixi.toml`/`pyproject.toml` + build the version-detection guard.

## 7. Provisioning-surface reuse

**Recommendation:** **do NOT couple** to the conda-forge-expert skill's
`update-cve-db` / `cve_manager.py` (different package + subsystem; it builds a
~4 GB indexed atlas DB, not osv-scanner's `all.zip` cache). **Adopt its
pattern**: per-ecosystem `all.zip`, a mirror env override (§ 8), resumable +
checksummed fetch, atomic writes. v1 DB provisioning = osv-native
`--download-offline-databases` (opt-in) / a conda DB package / a mirror — **no
bespoke downloader** in this tool.

**Evidence:** `cve_manager.py` head confirms it targets
`.claude/data/conda-forge-expert/cve/` with its own indexing and a 4 GB PyPI
zip — a distinct artifact from osv-scanner's own cache; reuse is *pattern-level*
only. **Owner:** Story 1.5 (choose the v1 provisioning path), Story 5.1 (docs).

## 8. Mirror override env (air-gap / JFrog)

**Recommendation:** reuse the repo-convention **`OSV_VULNS_BUCKET_URL`**
semantics (URL form `<bucket-base>/<ecosystem>/all.zip`, trailing slash
stripped) as the air-gap / JFrog mirror override for the DB fetch, with the
`_http.py` JFrog / `.netrc` / truststore auth discipline. Documented here;
wiring is downstream (v1 may satisfy air-gap purely via a pre-provisioned cache
dir + `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY`, deferring an active mirror fetch).

**Evidence:** `cve_manager.py` `_osv_vulns_bucket_base()` /
`_osv_ecosystem_zip_url()` already implement exactly this env → `<eco>/all.zip`
resolution against the public osv bucket default. **Owner:** Story 1.5 (if an
active fetch ships) / 5.1 (air-gap docs). **Watch:** the known
`_http.py JFROG_API_KEY unconditional injection` cross-resolver leak (auto-memory)
applies to any fetch that reuses `_http.make_request`.

## 9. `-L <parser>:<path>` override — removes the temp-name constraint

**Recommendation:** Story 1.5 writes its synthesized manifest to **any** secure
temp name and forces the parser with `-L requirements.txt:<path>` — the historic
"osv temp input must literally be named `requirements.txt`" constraint (noted in
the architecture pinned-engine table) is **removed**. The exact parser id is
**`requirements.txt`**.

**Evidence:** the proof test's non-`requirements.txt`-name row: a file named
`pdos-osv-vuln-abc123.txt` passed via `-L requirements.txt:<path>` is parsed and
matches the seeded advisory (exit 1). **Owner:** Story 1.5.

## 10. Distribution channels

**Recommendation:**
- **`pixi global install`** — connected workstations/CI; the **primary** channel.
- **pixi-pack / pixi-unpack** — the **recommended air-gap channel**: a single
  self-contained archive bundling scanner + engines + (optionally) the DB.
- **nebi push/pull** (OCI registries) — **alpha; a candidate only, NOT the
  recommended primary path** for a security gate (maturity risk).

**Evidence:** these are the three env-distribution mechanisms named in the Story
1.4 ACs (added 2026-07-12); the security-gate criticality is why nebi is
demoted. **Owner:** Story **5.1** (packaging + distribution docs).

## 11. Hermetic fixture DB (the produced substrate)

**Recommendation:** the substrate this spike produces IS the offline
vulnerability-data fixture that **Story 1.5 / 2.5 / CI** consume:
- readable OSV records under `tests/fixtures/osv-db/pypi/` (currently the one
  synthetic CRITICAL advisory `PDOS-FIXTURE-0001` affecting
  `pdos-vuln-fixture==1.0.0`);
- the deterministic builder `tests/fixtures/osv_db_builder.py`
  (`build_offline_db(records_dir, cache_root) -> cache_root`, writing
  `<cache_root>/osv-scanner/PyPI/all.zip` **stored uncompressed** for
  cross-machine byte-identity, fixed mtime, entries `<id>.json`; **fails loud**
  on an empty records dir / malformed / mis-targeted record — never a silent
  empty DB);
- vulnerable / clean pins under `tests/fixtures/lockfiles/osv-{vulnerable,clean}/`;
- the proof test `tests/conformance/test_osv_offline_db_spike.py`.

Story 1.5 imports the same builder (by path — the fixtures dir is data, not a
package) to stand up its offline DB; new advisories are added by dropping a
readable JSON record beside `PDOS-FIXTURE-0001.json` and rebuilding.

**Evidence:** observed exit codes recorded above — vuln **1**, clean **0**,
db-absent **127**, no-packages **128** — all asserted by the test, along with
the builder's empty-records-dir fail-loud and byte-identical output. **Owner:**
Story 1.5 (reuse), 2.5 (more fixtures), CI (the loop verify gate already collects it).

## 12. Gating

This record **gates Story 1.5** (osv engine: mechanism, `-L` parser id,
`--output-file`, DB-absent→`indeterminate` via a cache pre-flight, the
three-part `_engine_env` seam hand-off) and **Story 2.4** (stale-DB verdict
degrade via `max_age_ok`). It **does NOT gate Story 1.3** (deptry has no OSV
surface). Secondary hand-offs: **1.7** (pin application + version guard), **3.1**
(`--db-path` flag), **5.1** (distribution + air-gap docs), and a
**`bmad-correct-course` on `architecture.md`** (next section).

---

## Architecture reconciliation required (correct-course inputs)

Two decisions settled here **override** statements still standing in
`architecture.md`; a `bmad-correct-course` should update the architecture so the
two tracked planning artifacts agree (this spike does **not** edit
`architecture.md`):

- **127 semantics.** The pinned-engine table maps `127 → engine-error → exit 2`.
  The measured DB-absent cold start is a `127` that is a *coverage gap*, routed
  to `indeterminate` (§ 4). The blanket `127 → error` needs the DB-absent
  carve-out (detected by the deterministic cache pre-flight, not by the exit
  code alone).
- **`requirements.txt` temp-name constraint.** The architecture still mandates
  that osv's temp input be named literally `requirements.txt`. The `-L
  <parser>:<path>` override (§ 9) **removes** that constraint; the line should be
  updated.

**Owner:** a `bmad-correct-course` on `architecture.md` (or Story 1.5 folds the
reconciliation into its architecture-touch). Filed here so it is not lost.

## The Story-1.5 seam hand-off (three changes, not one)

The argv shape, temp-file output, and exit-code-is-content posture are proven
here and reused — but `engines._engine_env()` as it stands is **not** sufficient
for osv unchanged. It sets `NO_COLOR=1` / `stdin=DEVNULL` / argv-only, routes the
child's **stdout and stderr to `DEVNULL`**, and **discards the return code** (it
returns `(machine-output-text, None)`), reading only the temp output file.
Because the DB-absent cold start writes a clean-looking file (above), reusing the
seam verbatim would **false-green** the cold start. Story 1.5's real hand-off is
therefore **three** changes:

1. **Inject env** — thread `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY` (an optional
   `extra_env` on `_engine_env`, or an osv-specific wrapper).
2. **DB pre-flight** (§ 4) — the primary cold-start detector; it needs no seam
   change (a plain `os.path.exists` on the cache path 1.5 controls) and is what
   keeps the cold start off the clean path regardless of (3).
3. **Surface the exit code** (and, if version-detection per § 6 is wired, the
   engine's **stdout**) from `_engine_env` so osv's `1` / `127` / `128` are
   distinguishable content — today they are not observable through the seam.

This spike deliberately did **not** extend `_engine_env` (production code is
frozen for 1.4); the three changes are Story 1.5's to make. **Do not** read the
earlier "only `extra_env`" framing as the whole job — taken literally it
undercounts the work and reintroduces the cold-start false-green.

## Residual risks

- **Egress is trusted, not observed.** The proof test proves offline *behavior*
  by passing `--offline` and pointing at the fixture DB, but it does **not**
  observe the subprocess's network (the in-process socket-deny harness cannot
  patch a child process). A future osv-scanner that egressed under `--offline`
  would pass silently. Hardening: run the engine subprocess in a network
  namespace (or with an egress counter) at corpus scale — **owned by Story 5.2**
  (also filed in `deferred-work.md`). Today's mitigation is the § 6 pinned
  engine-version range.
- **`--offline-vulnerabilities` egress claim is from `--help`, not measured.**
  § 1 rejects `--offline-vulnerabilities` on `--help` semantics; the proof test
  only exercises full `--offline`. Bounded by the § 6 version pin.
- **Version-exact matching only.** The fixture proves matching for the literal
  pin `pdos-vuln-fixture==1.0.0`; PEP-503 name-normalization and PEP-440
  version-equivalence matching are Story 1.5 / 2.1 concerns (filed in
  `deferred-work.md`).
