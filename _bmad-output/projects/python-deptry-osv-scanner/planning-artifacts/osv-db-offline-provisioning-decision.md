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
| Observed exit codes | **0** = no vulnerabilities (clean); **1** = vulnerabilities found (expected non-error); **127** = engine could-not-load / DB error (see § 4 — **multiplexed**: DB-absent, **container**-corrupt/truncated zip, missing `-L` file, unknown parser id — but NOT a *content*-corrupt zip, which exits 0); **128** = no package sources found in the manifest. **`{0,1,127,128}` is the observed set, NOT a closed contract — 1.5 maps any unlisted code → `error`.** |
| **DB-absent + `--offline`** (cold start) | exit **127**; stderr: `could not load db for PyPI ecosystem: unable to fetch OSV database: no offline version of the OSV database is available`; the JSON output file **is written** with **`results: []`** — a body the proof test asserts is **byte-for-byte identical to a real clean scan**. Only the **exit code (127)** honestly distinguishes it; the stderr text is INFO chatter, **not** a stable contract. |
| **⚠ Present-but-EMPTY `all.zip`** (0-entry zip; partial download / mis-provisioned) | exit **0**, body **`results: []`** — **NEITHER exit code NOR body distinguishes it from a real clean scan.** The cardinal false-green (distinct from an empty *directory*, which → 127). A **non-emptiness** check (zip has ≥1 `<id>.json` entry) catches THIS one — but it is only a subset of the § 4 **content** pre-flight the next row shows is needed. |
| **⚠⚠ Present-but-CONTENT-CORRUPT `all.zip`** (valid zip container; entry is `{}` / malformed JSON / truncated / shape-invalid advisory) | exit **0**, body **`results: []`** on a **KNOWN-VULNERABLE** input — osv **loads** the zip and silently matches nothing. **Caught by NEITHER the exit code (0) NOR a namelist non-emptiness check** (the `<id>.json` entry IS present). Only a **content pre-flight** — parse each entry + validate the OSV advisory shape (§ 4) — catches it. **This refutes the earlier "present-but-corrupt zip → 127" claim: that 127 holds ONLY for *container* corruption** (measured: `{}`, `{ not json ]`, and a truncated advisory all → exit 0). |
| **Present-but-CONTAINER-CORRUPT `all.zip`** (damaged bytes / truncated central directory) | exit **127** — osv cannot open the archive. This IS the corruption class surfacing the exit code catches. Summary: empty cache **directory** → 127 (safe), container-corrupt zip → 127 (safe); empty *zip* → 0 and content-corrupt zip → 0 (dangerous, need the content pre-flight). |
| **No packages + `--offline`** | exit **128**; stderr `No package sources found, --help for usage information.`; **no output file is written** (distinct from the DB-absent 127 above). The architecture's no-packages → coverage-skipped path → `indeterminate`. |
| Determinism | the builder writes `all.zip` **stored uncompressed** (`ZIP_STORED`) with a fixed DOS-epoch mtime (`1980-01-01`) + fixed attrs → **twice-run byte-identical on the same interpreter** (DEFLATE output is zlib-build-dependent, so compression is dropped for reproducibility; the fixture is tiny). `zipfile`'s create/extract-version header bytes are not pinned, so cross-CPython-version byte-identity is intended but not tested (see Residual risks). Asserted by the proof test. |

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

**Recommendation:** define **stale = DB `snapshot_at` *strictly* older than
`now - db-max-age` (default 7 days)** — the boundary is a strict inequality
(exactly-at-max-age is NOT stale). `snapshot_at` source = the provisioning
timestamp (conda package build-date, or a recorded manifest timestamp for the
mirror path; NOT `datetime.now()` at scan). Two boundary rules Story 2.4 MUST
honor so staleness cannot become a false-green:
- **Unknown / absent provenance ⇒ `indeterminate`, never clean-eligible — but
  disambiguate "not consulted" from "consulted, provenance-less".** `max_age_ok`
  is `None` in **two** distinct states the frozen model both permit, and 2.4
  MUST NOT collapse them:
  - `source is None` (with `snapshot_at` and `max_age_ok` also None) = **the vuln
    axis was NOT consulted** — a hygiene-only / vuln-not-requested run;
    `VulnData(None, None, None)` is legal (verified in `models.__post_init__`:
    only a *concrete* `max_age_ok` requires provenance). This is **not** a
    staleness concern and must **NOT** force `indeterminate`.
  - `source` is **set** but `snapshot_at is None` = the axis WAS consulted
    against a **provenance-less DB** (the osv-native `--download-offline-databases`
    path — a primary v1 path, §§ 1/5/10 — carries no `snapshot_at`; the frozen
    schema then forces `max_age_ok=None`). THIS is the case that is **not
    clean-eligible** → route to `indeterminate`, never a confident clean.

  The rule is therefore "**`source` set AND `snapshot_at`/`max_age_ok` unknown ⇒
  `indeterminate`**", **not** a blanket "`max_age_ok is None ⇒ indeterminate`"
  (which would wrongly force every deptry-only scan to `indeterminate`).
- **Future-dated `snapshot_at`** (clock skew / bad mirror clock → negative age)
  is treated as **unknown provenance ⇒ `indeterminate`**, never "fresh."

Stale (or unknown-provenance, or future-dated) → `VulnData(max_age_ok=False|None)`
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

> No usable local OSV database found (absent, empty, or content-corrupt). Point
> `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY` (or the `--db-path` wrapper flag) at an
> existing offline cache, install a conda OSV-DB package, or — **on a connected
> machine only** — run `osv-scanner --download-offline-databases` to provision
> one. This gate never fetches vulnerability data silently.

The nudge leads with the **offline/air-gap-safe** remedies (existing cache /
conda package) because it fires precisely in offline mode; the network download
is listed last and explicitly connected-only, so it does not misdirect a
genuinely air-gapped operator. `--db-path` is *our wrapper* flag mapping to
`OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY`; the flag itself lands in Story 1.5/3.1
(the nudge should name it only once it exists, else name the env var alone).

**Evidence + the critical trap:** the DB-absent run exits **127**, but its JSON
body (`results: []`) is **byte-for-byte identical to a real clean scan** (the
proof test asserts this). A consumer keying on the JSON body alone would
**false-green** — and osv-scanner's own return code + stderr are **discarded**
by the current `_engine_env` seam (see the seam hand-off below), so a naive
verbatim reuse would read the cold start as clean.

**Disposition (deterministic pre-flight, NOT stderr parsing):** Story 1.5 must
detect an untrustworthy DB **before trusting the scan** with a deterministic
pre-flight. **The pre-flight is a CONTENT check, not an existence check and not a
mere namelist count** — an `os.path.exists(all.zip)` test AND a
"namelist-has-an-entry" test are both INSUFFICIENT and reopen the false-green
this record exists to close (see the **empty/content-corrupt-DB** hazard below).
The pre-flight MUST:

1. Resolve the on-disk path using osv's **exact case-sensitive ecosystem
   segment** — `PyPI` (not the lowercase `pypi` `Ecosystem` enum value): the
   layout is `<cache>/osv-scanner/PyPI/all.zip`. Interpolating the lowercase
   enum makes the pre-flight always miss a real DB (feature dead → permanent
   `indeterminate`); provisioning at lowercase to match the enum makes osv
   itself never load it. Keep a canonical enum→osv-dir map (`pypi` → `PyPI`).
2. Confirm the zip **exists, opens, AND contains ≥1 entry that PARSES as JSON
   and satisfies the minimal OSV advisory shape** — an `id` plus an `affected[]`
   entry targeting the ecosystem with a package name and a concrete
   `versions`/`ranges` spec. This is a **content** check: reuse the builder's
   `_entry_for_record` validator on the LOADED entries. osv-scanner's own loader
   does **NOT** validate advisory shape at load time — empirically it accepts
   `{}`, malformed JSON, and a truncated advisory and still exits **0** on a
   vulnerable input (measured) — so the wrapper must. A present-but-empty
   (0-entry) OR present-but-content-corrupt (`{}` / malformed / truncated /
   shape-invalid entry) `all.zip` FAILS this check.

Missing / empty / content-corrupt / unreadable DB → route to **`indeterminate`**
(coverage-skipped, exit 1) + emit the nudge, *without* trusting a scan result.
Do **not** branch security control-flow on the stderr string — it is INFO
chatter a 2.x patch can reword (not a stable contract). **The content pre-flight
and the exit code are BOTH required and complementary** (H2 correction,
revised) — they catch DISJOINT corruption classes:

- a **content-corrupt** zip (valid container; `{}` / malformed / truncated /
  shape-invalid entry) is *loaded* by osv and exits **0** with `results: []` on
  a vulnerable input (measured) → caught **ONLY** by the content pre-flight,
  **never** by the exit code or a namelist count;
- a **container-corrupt** zip (damaged bytes / truncated central directory) osv
  cannot open → exit **127** → caught by surfacing the exit code (seam change
  #3), which the pre-flight's `zipfile.open` also rejects.

Neither defense alone keeps every bad-DB state off the clean path; the earlier
"present-but-corrupt zip → 127, so surfacing the exit code is the load-bearing
defense" framing was **empirically wrong** — *content* corruption exits 0. This
reconciles the architecture conflict flagged below: a DB-absent / empty /
container-corrupt 127 is a *coverage gap* → `indeterminate`, not the blanket
`127 → error → exit 2` the architecture's pinned-engine table assumes; note
**127 is multiplexed** (osv emits it for DB-absent, container-corrupt zip, a
missing `-L` file, and an unknown parser id) so 1.5 maps **any 127 → the
coverage-skipped/error family after the content pre-flight has run**, and any
exit code **outside {0,1,127,128} → `error`** (never a content-read that could
bottom out at clean). **Owner:** Story 1.5 (content pre-flight + mapping +
nudge), Story 3.1 (`--db-path`).

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
scalibr and the whole exit-code/flag contract proven here is measured on exactly
2.4.0; 3.x may move the exit codes or rename flags. The `--output`→`--output-file`
change *within* 2.x is a deprecation-with-warning, **not** a break — `--output`
still works — so it is context, not evidence for the ceiling; the ceiling rests
on "the contract is measured only on 2.4.0") and **`deptry >=0.25.1,<1`**
(pre-1.0 minors can move DEP codes). Detection:
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

**Recommendation:** Story 1.5 writes its synthesized manifest to a secure temp
name and forces the parser with `-L requirements.txt:<path>` — the historic
"osv temp input must literally be named `requirements.txt`" constraint (noted in
the architecture pinned-engine table) is **removed**; forcing the parser makes
the file's **extension irrelevant** (verified for a `.txt`-suffixed
non-`requirements.txt` name; a no-extension / other-suffix name is expected to
behave identically but is not separately exercised). The exact parser id is
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
  same-interpreter byte-identity, fixed mtime, entries `<id>.json`; **fails
  loud** (always `ValueError`) on a non-directory or empty records dir, a
  case-variant `.JSON` record or a record nested under a subdirectory, a
  non-object/wrong-type record, or a record with no `PyPI` `affected` entry
  carrying a package name AND a concrete matchable spec (a non-empty `versions`
  string or a `ranges` entry with `events`) — never a silent empty, mis-shelved,
  or **unmatchable** DB. The builder guards the in-repo **fixture** only;
  validating an externally-provisioned DB (osv-native download / conda package /
  mirror) at load time is Story 1.5's **content pre-flight** (§ 4), since
  osv-scanner's loader accepts malformed advisory content and still exits 0);
- vulnerable / clean pins under `tests/fixtures/lockfiles/osv-{vulnerable,clean}/`;
- the proof test `tests/conformance/test_osv_offline_db_spike.py`.

Story 1.5 imports the same builder (by path — the fixtures dir is data, not a
package) to stand up its offline DB; new advisories are added by dropping a
readable JSON record beside `PDOS-FIXTURE-0001.json` and rebuilding.

**Evidence:** observed exit codes recorded above — vuln **1**, clean **0**,
db-absent **127**, container-corrupt **127**, present-but-empty **0**,
content-corrupt **0** (the last two are false-greens the content pre-flight
catches), no-packages **128** — all asserted by the test, along with the
builder's fail-loud guards and byte-identical output. **Owner:** Story 1.5
(reuse), 2.5 (more fixtures), CI (the loop verify gate already collects it).

## 12. Gating

This record **gates Story 1.5** (osv engine: mechanism, `-L` parser id,
`--output-file`, bad-DB→`indeterminate` via a **content** pre-flight, the
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
- **Empty/incomplete/content-corrupt-DB fail-loud.** The architecture's Gap-C
  describes a DB-absent path but not the present-but-empty / content-corrupt /
  incomplete-DB false-green (exit 0 + empty body, which osv's loader does not
  reject). The correct-course should add, to `verdict.py`/`errors.py` and the
  Gap-C narrative, that the DB pre-flight is a **content** guard (≥1 entry that
  parses as a shape-valid OSV advisory — **NOT** a mere existence check or
  namelist count) and that a provenance-less DB routes to `indeterminate` — so
  the guard is an architectural invariant, not just a 1.5 implementation note.
- **128 internal inconsistency.** `architecture.md` maps `128 → typed errors` in
  the pinned-engine table while its Gap-C narrative maps `128 → coverage-skipped
  → indeterminate`. This record follows the Gap-C line (`128 → indeterminate`);
  the correct-course should resolve the architecture's own two conflicting lines.

**APPLIED 2026-07-14** via `bmad-correct-course`: all four items reconciled into
`architecture.md` (frontmatter exitCodes, the pinned-engine-contracts line, Gap-C
osv-exit-codes + withhold-reason temp-name, the Offline-DB content-pre-flight
invariant, and the security-invariants temp-name line — each carries a
`Story-1.4-reconciled` marker). This decision record remains the authoritative
source; architecture.md now agrees.

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
2. **DB content pre-flight** (§ 4) — the primary bad-DB detector. It needs no
   seam change (1.5 controls the cache path) but it is a **content** check (zip
   opens + ≥1 entry that parses as a shape-valid OSV advisory, resolved at osv's
   case-sensitive `PyPI` segment; reuse the builder's `_entry_for_record`), NOT
   a plain `os.path.exists` and NOT a mere namelist count. An existence check
   passes for a present-but-empty zip, and a namelist count passes for a
   present-but-content-corrupt zip — both reopen the cardinal false-green.
3. **Surface the exit code** (and, if version-detection per § 6 is wired, the
   engine's **stdout**) from `_engine_env` so osv's `1` / `127` / `128` are
   distinguishable content — today they are not observable through the seam.
   **This is REQUIRED, not optional**: a *container*-corrupt zip exits **127**
   (the pre-flight's `zipfile.open` rejects it too), and `1` / `128` must be
   distinguished from `0`. (2) and (3) catch DISJOINT corruption classes —
   *content*-corrupt → exit **0** (only (2) catches it), *container*-corrupt →
   **127** (both catch it) — so neither alone keeps every bad-DB state off the
   clean path (the earlier "corrupt zip → 127, so the exit code is the defense"
   framing was empirically wrong: content corruption exits 0).

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
- **Incomplete/corrupt-but-FRESH DB reads as clean.** A valid, in-date DB that
  is content-incomplete OR content-corrupt (empty 0-entry zip / trimmed /
  partial download / wrong-ecosystem shelved / a `{}` / malformed / truncated /
  shape-invalid advisory entry) produces `results: []` → clean — a false-green
  that **staleness-by-age cannot detect** (the DB is fresh) and that
  osv-scanner's own loader does not reject (it accepts malformed advisory
  content and still exits 0, measured). This is the risk class behind the § 4
  **content** pre-flight and the H1/H2/F1 review findings; a content pre-flight
  (≥1 entry that parses as a shape-valid OSV advisory — **NOT** a mere namelist
  count) is the only in-tool defense, and it is now a mandated 1.5 deliverable +
  a correct-course architectural invariant. A partial *manifest*
  parse (osv silently drops unparseable requirements lines; a mixed valid/malformed
  file scans only the valid subset and can exit 0) is the analogous input-side
  gap — Story 1.5/1.9 must surface dropped-line counts into coverage rather than
  trust a subset-clean.
- **Cross-machine determinism is asserted, not fully proven.** The builder's
  byte-identity is verified only same-interpreter twice-run; `zipfile`
  create/extract-version header bytes can shift across CPython versions. The
  "any machine / any Python" claim is a design intent bounded by the § 6 engine
  pin + the same-tree pixi env, not a cross-version-tested guarantee.
