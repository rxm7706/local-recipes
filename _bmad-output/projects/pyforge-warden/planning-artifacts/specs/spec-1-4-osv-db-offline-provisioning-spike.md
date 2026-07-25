<!-- RECOVERED 2026-07-25 from a surviving bmad-loop run worktree (.bmad-loop/runs/20260718-101504-2c07/worktrees/6-2-license-axis-producer-gate-flags/_bmad-output/implementation-artifacts/spec-1-4-osv-db-offline-provisioning-spike.md); this is the ORIGINAL spec, not an epics.md regeneration. Promoted to tracked planning-artifacts/specs/ for durability. -->
---
title: 'Story 1.4: OSV-DB offline provisioning spike (decision + fixture DB)'
type: 'chore' # spike — decision record + hermetic test fixtures + one proof test; no production code
created: '2026-07-14'
status: 'in-review'
baseline_revision: 'fcf6fc9e475890d6ab36bed3d1d265536f1d7ab3'
final_revision: '5660b20901fd7ccf338626d71aeea791fda666a0'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/_bmad-output/projects/python-deptry-osv-scanner/planning-artifacts/architecture.md'
  - '{project-root}/_bmad-output/projects/python-deptry-osv-scanner/planning-artifacts/epics.md'
  - '{project-root}/_bmad-output/projects/python-deptry-osv-scanner/implementation-artifacts/epic-1-context.md'
warnings: [oversized]
---

<intent-contract>

## Intent

**Problem:** Story 1.5 must run `osv-scanner` **fully offline** against a provisioned OSV database, but the provisioning mechanism, staleness/trust semantics, cold-start UX, engine-version pinning, air-gap mirror path, and distribution channels are unresolved open research questions (architecture open-Q3/Q7/Q8b, Gap-analysis #4), and no hermetic vulnerability-data substrate exists for 1.5/2.5/CI to test against. Left buried in a delivery story, these either stall 1.5 or leak a network dependency into the test suite.

**Approach:** Run the spike. (1) **Empirically** pin down how `osv-scanner` 2.4.0 consumes a hermetic, hand-built offline DB (env `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY` → `<Ecosystem>/all.zip`; `--offline`; `-L <parser>:<path>`), producing a reusable **deterministic fixture-DB builder** + a **proof test** that detects a seeded advisory with zero network. (2) Write a **tracked decision record** resolving every AC1/AC3 question, with recommendations grounded in the codebase, the live `osv-scanner scan --help`, the frozen `VulnData` fields, and the in-repo `cve_manager.py` provisioning pattern. **No production engine code — that is Story 1.5.**

## Boundaries & Constraints

**Always:**
- **Spike, not delivery — touch ZERO production `src/python_deptry_osv_scanner/` modules.** Deliverables are a tracked decision record + test-only fixtures/harness + one proof test. `cli.py`, `engines.py` (incl. `_engine_env`), `models.py`, `verdict.py`, `inventory.py`, `interfaces.py`, `report.py`, `hygiene.py`, `data/*` are **untouched**.
- **Fully hermetic + offline.** The fixture DB is built from in-repo readable OSV JSON with **no network**; the proof test passes `--offline` to osv-scanner (an assertion, not a hope — NFR-S2) and must pass on an air-gapped machine. The Story-1.2 in-process socket-deny harness (`tests/conftest.py`) stays green; the osv **subprocess**'s no-egress guarantee comes from `--offline` + the fixture DB being the only advisory source (the subprocess is outside in-process socket patching — this is the architecture's "network confined to named engine subprocesses" model).
- **Decision record is tracked + downstream-consumable.** It lands in `planning-artifacts/` (git-tracked). `implementation-artifacts/` is **gitignored** and would not survive the loop squash-merge into 1.5/2.4's fresh worktrees. It explicitly records that it **gates 1.5 + 2.4, and NOT 1.3**.
- **Grounded, not invented.** Every decision cites evidence. The vuln provenance fields `VulnData{source, snapshot_at, max_age_ok}` **already exist frozen in the 1.1 schema** (`models.py`, `data/report-schema.json`) — the record documents how 1.5/2.4 **populate** them; it does not redefine them.
- **Deterministic fixture build.** The builder writes `all.zip` with a **fixed mtime** (no `datetime.now()`), so the substrate is reproducible; the proof test asserts on advisory-id / package / severity content, never on osv-scanner's volatile output bytes.
- **Valid OSV records.** New records validate against the OSV schema and carry a **CVSS v3.1 CRITICAL** severity vector (a positive fixture for 1.5/1.6). The fixture package name is **synthetic** (`pdos-vuln-fixture`) with an **explicit affected `versions` list** so matching is version-exact and never depends on real-world PyPI state.

**Block If:**
- osv-scanner 2.4.0 cannot be made to consume ANY hermetic, hand-built `all.zip` offline (e.g. the offline loader requires a signed index/manifest not reproducible in-repo) after a **bounded iteration on zip layout** — the hermetic-fixture-DB deliverable is then infeasible as scoped and needs human re-scoping (vendor a trimmed real-DB slice, or a different offline mechanism). HALT `blocked` with the observed loader requirement + the layouts tried.
- The pinned `osv-scanner` (>=2.4.0) is absent from the `python-deptry-osv-scanner` env / not on PATH, so the empirical proof cannot run. HALT `blocked` (do not fabricate the evidence).

**Never:**
- No `OsvEngine`, no `vuln.py`, no wiring osv into `cli.main(["scan", …])`, no osv-output→`ResolvedInventory` mapping — **Story 1.5**.
- No stale-DB verdict-degrade implementation (populating `max_age_ok` into a live verdict) — **Story 2.4**; 1.4 only **defines** "stale."
- No edits to frozen 1.1 artifacts; no new `Status` / `ErrorKind` / `WithholdReason` members.
- No changes to `pixi.toml` / `pixi.lock` / `pyproject.toml` (the NFR-C1 range-tightening is a documented recommendation + 1.5 hand-off — a worktree re-solve is toxic per `deferred-work.md`).
- No extension of `_engine_env()` (the needed `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY` / extra-env threading is recorded as a **1.5 hand-off**; the proof test controls the subprocess env locally).
- No real-DB download / bespoke downloader / any network in tests; **no committed binary `all.zip` blob** (build it at test time from readable JSON).

## I/O & Edge-Case Matrix

*(These are the proof test's scenarios — a spike-local subprocess helper invokes osv-scanner directly; it does NOT go through `cli.main` or `_engine_env`.)*

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Vulnerable pin, offline | fixture DB built into a tmp cache; lockfile pins `pdos-vuln-fixture==1.0.0`; osv run `--offline` + `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY=<tmp>` + `-L <parser>:<tmp-nonstandard-path>` + `--format json --output-file <tmp>` | osv **exit 1** (vulns-found); JSON names the seeded advisory `PDOS-FIXTURE-0001` + package `pdos-vuln-fixture` + the CVSS-critical severity; zero network | — |
| Clean pin, offline | same DB; lockfile pins `pdos-vuln-fixture==2.0.0` (outside the affected `versions`) | osv **exit 0**; no findings — proves precision + correct offline clean | — |
| Non-`requirements.txt` temp name | input file named `pdos-osv-*.txt`, passed via `-L <parser>:<path>` | osv parses it → the `requirements.txt` temp-name constraint is **removed**; the exact parser id is recorded in the decision record | if the first guessed parser id is wrong, iterate to the correct id and record it |
| DB absent, offline | `--offline` against an empty/absent cache dir, vulnerable lockfile | osv reports **no vulnerabilities / a no-local-db signal** (observe exact exit/output) — this documents the cold-start signal 1.5 maps to `indeterminate`, **never** confident-clean | record exact exit/output; assert it is **not** silently equivalent to a real clean-with-DB run |
| Determinism | builder run twice over the same records | **byte-identical** `all.zip` (fixed mtime) | — |

</intent-contract>

## Code Map

- `_bmad-output/projects/python-deptry-osv-scanner/planning-artifacts/osv-db-offline-provisioning-decision.md` -- NEW (git-**tracked**): the decision record; AC1+AC2+AC3 resolutions (§ Design Notes lists all 12 sections). Consumed by Story 1.5 + Story 2.4.
- `src/shared/packages/python-deptry-osv-scanner/tests/fixtures/osv-db/pypi/PDOS-FIXTURE-0001.json` -- NEW: readable, OSV-schema-valid advisory; CVSS v3.1 CRITICAL; affects `pdos-vuln-fixture` explicit `versions: ["1.0.0"]`.
- `src/.../tests/fixtures/osv_db_builder.py` -- NEW: deterministic `build_offline_db(records_dir, cache_root) -> cache_root` writing `<cache_root>/osv-scanner/PyPI/all.zip` (fixed mtime, entries named `<id>.json`); importable helper reusable by Story 1.5.
- `src/.../tests/fixtures/lockfiles/osv-vulnerable/requirements.txt` (`pdos-vuln-fixture==1.0.0`) + `src/.../tests/fixtures/lockfiles/osv-clean/requirements.txt` (`pdos-vuln-fixture==2.0.0`) -- NEW: the pinned inputs.
- `src/.../tests/conformance/test_osv_offline_db_spike.py` -- NEW: the proof test (I/O matrix). A **spike-local** subprocess helper runs osv-scanner (JSON→temp file, cache-dir env, `-L <parser>:<path>`, `--offline`). Hard-fails (no skip) if osv-scanner is absent, matching the 1.3 provisioned-engine convention.
- `src/.../tests/conftest.py` -- READ-ONLY reference (the socket-deny harness, lines ~83–210). Optionally expose an `osv_fixture_db` fixture wrapping the builder **only if** it keeps the test cleaner — additive, no edits to existing fixtures.
- `.claude/skills/conda-forge-expert/scripts/cve_manager.py` -- READ-ONLY reference: the in-repo per-ecosystem `all.zip` + `OSV_VULNS_BUCKET_URL` mirror-aware provisioning **pattern** the decision record borrows (not couples to).

## Tasks & Acceptance

**Execution:**
- [x] `tests/fixtures/osv-db/pypi/PDOS-FIXTURE-0001.json` -- author an OSV-schema-valid advisory: `id:"PDOS-FIXTURE-0001"`, fixed `modified`/`published` (e.g. `2026-01-01T00:00:00Z`), `affected:[{package:{ecosystem:"PyPI",name:"pdos-vuln-fixture"}, versions:["1.0.0"]}]`, `severity:[{type:"CVSS_V3",score:"CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"}]`, `summary`+`details`. Add a `ranges` block only if the empirical run shows osv-scanner needs it to match; add a 2nd record only if needed to prove clean-precision.
- [x] `tests/fixtures/lockfiles/osv-vulnerable/requirements.txt` + `tests/fixtures/lockfiles/osv-clean/requirements.txt` -- the vulnerable (`==1.0.0`) and clean (`==2.0.0`) pins.
- [x] `tests/fixtures/osv_db_builder.py` -- deterministic `all.zip` builder (fixed mtime; `<cache>/osv-scanner/PyPI/all.zip` layout; zip entries `<id>.json`); importable, side-effect-free helper.
- [x] `tests/conformance/test_osv_offline_db_spike.py` -- implement the I/O matrix: build DB → run osv-scanner `--offline` via the spike-local helper → assert vulnerable-detect / clean / temp-name-override / DB-absent-signal / builder-determinism. Empirically determine + record the exact `-L` parser id and the DB-absent exit/output. Hard-fail if osv-scanner absent.
- [x] `planning-artifacts/osv-db-offline-provisioning-decision.md` -- the decision record; all 12 sections in § Design Notes, each with a grounded **recommendation + evidence + downstream owner** (1.5 / 2.4 / 3.1 / 5.1) for anything not built in 1.4. State the 1.5+2.4 gating and the not-1.3 exclusion explicitly.

**Acceptance Criteria:**

*(Story 1.4 ACs from `epics.md`, preserved verbatim — the contract of record.)*

**Given** the offline-first constraint (NFR-S2/S8), **When** the spike concludes, **Then** a **decision record** documents the chosen mechanism (bundled-conda-DB vs `--offline` + a provisioned local DB), how "stale" is defined (feeds FR12), and the trust-anchor/authenticity check (NFR-S8). **And** a **hermetic fixture DB** the conformance harness can consume offline is produced.

**Given** the decision, **When** downstream stories consume it, **Then** it explicitly gates **1.5** (osv engine) and **2.4** (stale-DB semantics) — and **not** 1.3 (deptry has no OSV surface).

**Given** a workstation cold start (no DB provisioned — persona P8), **When** the spike decides the provisioning UX, **Then** the decision record also covers (added 2026-07-12): the fail-loud + **actionable-nudge** message (how to provision / `--db-path`); whether an explicit **online opt-in** query mode ships in v1 (the PRD's "opt-in, never silent" path — currently unowned) or v1 is offline-only-everywhere with trivial provisioning; the concrete **engine version ranges** to pin (NFR-C1) + the version-detection mechanism; reuse of the in-repo **`update-cve-db`** offline-OSV provisioning surface vs a new downloader; an env-var **mirror override** for the DB fetch (JFrog/air-gap discipline); and verification of osv's `--lockfile=<parser>:<path>` override (may remove the `requirements.txt` temp-name constraint). The decision record also names the **env distribution channels**: `pixi global install` (online) · **pixi-pack/unpack** (air-gapped single-archive bundle — scanner + engines + DB) · **nebi push/pull** for nebi-adopted teams (OCI registries; alpha — a candidate, not the recommended primary path for a security gate) (added 2026-07-12).

*(Standing per-story gates, inherited from 1.1/1.2/1.3: because 1.4 changes **no** production `src/` module, all prior 1.1/1.2/1.3 suites, the `verdict.py` sole-ownership guard, the no-execution AST guard, and the socket-deny harness stay green trivially; false-green = 0 on the spike's fixtures; the fixture-DB builder is twice-run byte-identical.)*

## Design Notes

**Decision-record spine (12 sections — grounded recommendations the implementer expands into prose + evidence):**

1. **Mechanism** — osv-scanner **`--offline`** reading `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY` → per-ecosystem `<Ecosystem>/all.zip` (matches architecture Gap-C "conda package `{ecosystem}/all.zip`"). **Reject `--offline-vulnerabilities` alone** — it egresses on transitive resolution (Gap-C/open-Q7). Production provisioning = conda-packaged DB if/when one exists, else osv-native `--download-offline-databases` (explicit opt-in), else air-gap mirror.
2. **Staleness (feeds FR12)** — stale = DB `snapshot_at` older than `--db-max-age` (**default 7 d**, configurable); snapshot source = provisioning timestamp (package build-date / recorded manifest). Stale → `VulnData(max_age_ok=False)` → **Story 2.4** degrades verdict to ≥`warn`/`indeterminate`, never confident `clean`. Fields already frozen.
3. **Trust anchor (NFR-S8)** — production: conda/channel integrity (sha256, optional sigstore CEP-27); mirror path: a sha256 manifest (mirroring `cve_manager.py`); swapped/empty/unverifiable DB → **fail-loud**. Fixture DB trusted by in-repo provenance.
4. **Cold-start UX + nudge** — no DB in offline mode → vuln coverage **skipped → `indeterminate`** (exit 1, never confident-clean; architecture state-machine L433) with a stderr **actionable nudge**. Draft it, e.g.: *"No local OSV database found. Provision one (`osv-scanner --download-offline-databases`, a conda DB package, or point `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY`/`--db-path` at an existing cache). This gate never fetches silently."* `--db-path` = our wrapper flag → `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY`; flag itself lands in 1.5/3.1.
5. **Online opt-in disposition** — **v1 = offline-only-everywhere** + trivial explicit provisioning; **no silent fetch** (NFR-S2). Any online query is an explicit non-default flag, **deferred beyond v1** (contract documented, unbuilt). This resolves the PRD's "currently unowned" opt-in gap by scoping it out of the v1 default.
6. **Engine version ranges (NFR-C1) + detection** — recommend `osv-scanner >=2.4.0,<3` (2.x embeds scalibr; 3.x may break the exit-code/flag contract) and `deptry >=0.25.1,<1` (pre-1.0 minors can move DEP codes). Detection: parse `<engine> --version` at run; out-of-range → fail-loud. **Not applied to `pixi.toml` here** (worktree re-solve toxic); hand-off to 1.5/1.7.
7. **Provisioning-surface reuse** — **do NOT couple** to the conda-forge-expert skill's `update-cve-db`/`cve_manager.py` (different package/subsystem, ~4 GB atlas DB); **adopt its pattern** (per-ecosystem `all.zip`, mirror env, resumable+checksum). v1 provisioning = osv-native `--download-offline-databases` (opt-in) / conda package / mirror — **no bespoke downloader**.
8. **Mirror override env (air-gap/JFrog)** — reuse **`OSV_VULNS_BUCKET_URL`** semantics (repo convention; URL form `<bucket>/<ecosystem>/all.zip`) + `_http.py` JFrog/.netrc auth discipline. Documented; wiring downstream.
9. **`-L <parser>:<path>` override** — **verified present in 2.4.0**; removes the `requirements.txt` temp-name constraint → 1.5 writes the synthesized manifest to any temp name + passes `-L <parser>:<path>`. Record the **exact parser id** from the empirical run (candidate: `requirements.txt`).
10. **Distribution channels** — `pixi global install` (connected, primary); **pixi-pack/unpack** (air-gap single archive: scanner+engines+DB — recommended air-gap channel); **nebi push/pull** (OCI; **alpha — candidate only, NOT recommended primary** for a security gate). Docs owned by Story 5.1.
11. **Hermetic fixture DB** — the produced substrate (readable OSV JSON + deterministic builder → `PyPI/all.zip`) + the proof-test evidence (observed exit codes for vuln / clean / db-absent). Names it as the offline substrate 1.5/2.5/CI consume.
12. **Gating** — explicitly gates **1.5** + **2.4**; **not 1.3**.

**Why zero production edits:** the osv *runner* + input synthesis live in `engines.py`/`vuln.py` = Story 1.5 (architecture Epic→structure table). A spike that proves the substrate and records the mechanism, without wiring the live engine, keeps the risky empirical work (does a hand-built offline DB even work?) off the delivery path. The 1.5 seam hand-off is **three** changes, not one (the decision record § "The Story-1.5 seam hand-off" is authoritative): (1) thread `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY` via an optional `extra_env` on `_engine_env`; (2) a deterministic DB-presence **pre-flight** (no seam change) as the primary cold-start detector — because `_engine_env` discards stdout/stderr **and** the return code, a verbatim reuse would false-green the DB-absent 127; (3) surface the exit code (and stdout, if version-detection ships). The spike does not touch `_engine_env`.

**osv-scanner offline invocation (from live `--help`, 2.4.0 → scalibr 0.4.5):** cache via env `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY` (no `--local-db-path` flag exists); layout `<cache>/osv-scanner/PyPI/all.zip` of `<id>.json` OSV records; `--offline` disables all network; `-L <parser>:<path>` forces the lockfile parser; `--format json --output-file <file>` keeps JSON pure (`--output` is deprecated in 2.4.0; matches the `_engine_env` temp-file pattern 1.5 reuses).

## Verification

**Commands:**
- `pixi run --frozen -e python-deptry-osv-scanner python-deptry-osv-scanner-test` -- expected: **all prior 1.1/1.2/1.3 suites still pass unchanged** (zero production `src/` edits) **plus** `test_osv_offline_db_spike.py` green — osv-scanner detects the seeded advisory **offline** (exit 1), clean pin → exit 0, `-L` temp-name override parses a non-`requirements.txt` file, the DB-absent path is not silently clean, and the builder is twice-run byte-identical. Hard-fails if osv-scanner is absent. (`--frozen` mandatory in the loop worktree — `deferred-work.md`.)
- Sole-ownership / no-execution / socket-deny meta-guards stay green (trivially — no production edits).

**Manual checks:**
- `planning-artifacts/osv-db-offline-provisioning-decision.md` exists, is git-**tracked** (`git status` shows it as a new tracked file, not under the gitignored `implementation-artifacts/`), covers all 12 § Design-Notes sections with a grounded recommendation + evidence + downstream owner each, and states the "gates 1.5 + 2.4, not 1.3" disposition.
- The proof test's recorded findings (exact `-L` parser id; DB-absent exit/output) are written into the decision record, not left only in test comments.

## Review Triage Log

### 2026-07-14 — Review pass (Blind Hunter + Edge Case Hunter, Opus)
Both reviewers confirmed the fixtures/builder/proof-test are sound and the empirical facts check out; the risk concentrated in the **decision record** (the artifact that gates 1.5). All findings routed to `patch` — the intent-contract is correct and the code needed only hardening, so no re-derivation. The two `high` patches corrected a genuine **false-green cold-start** the record would otherwise have shipped to Story 1.5.
- intent_gap: 0
- bad_spec: 0
- patch: 14: (high 2, medium 6, low 6)
- defer: 2
- reject: 5
- addressed_findings:
  - `[high]` `[patch]` Decision-record "single hand-off = only `extra_env`" was wrong and would false-green the DB-absent cold start: `_engine_env` routes child stdout/stderr to `DEVNULL` and discards the return code, so a verbatim reuse reads the clean-looking DB-absent output as `clean`. Rewrote § "The Story-1.5 seam hand-off" to **three** changes (extra_env + deterministic DB pre-flight + surface exit code/stdout); corrected the spec Design-Notes framing too.
  - `[high]` `[patch]` § 4 mitigation branched security control-flow on osv's fragile stderr string (which the seam DEVNULLs anyway). Rewrote § 4 to make a deterministic `os.path.exists(<cache>/…/all.zip)` **pre-flight** the primary DB-absent detector; exit 127 corroborates, stderr advisory-only.
  - `[medium]` `[patch]` Decision record silently overrode the architecture's `127→error/exit 2` and the `requirements.txt` temp-name mandate without reconciling. Added an **"Architecture reconciliation required"** section flagging both for a `bmad-correct-course` on `architecture.md`.
  - `[medium]` `[patch]` Exit **128** (no-packages) was claimed-settled but unmeasured; measured it (128, **no output file written**), added the table row + a `test_no_packages_manifest_exits_128_with_no_output` test.
  - `[medium]` `[patch]` `test_builder_entry…` asserted exact one-element `namelist()` equality — breaks when Story 2.5 adds an advisory (the record's own documented growth path). Changed to membership + `<id>.json` pattern.
  - `[medium]` `[patch]` Builder used `ZIP_DEFLATED` level 9 → not byte-portable across zlib builds while the record sells cross-machine byte-identity. Switched to `ZIP_STORED`; scoped the determinism claims.
  - `[medium]` `[patch]` "byte-identical to a clean scan" was under-proven — the DB-absent test compared only the `results` sublist and `(absent.document or {})` masked the file-not-written case. Test now asserts the output file **is** written and is **byte-for-byte identical** (`absent.raw_output == clean.raw_output`), substantiating the record's claim.
  - `[medium]` `[patch]` Empty `records_dir` silently produced an empty `all.zip` → osv reports clean (a build-time false-green — the exact class the spike exists to prevent). Builder now raises `ValueError`; added `test_builder_refuses_empty_records_dir`.
  - `[low]` `[patch]` Removed the fragile `assert "all.zip" in run.stderr` (detection already proves DB load); scoped the CVSS-vector assertion to the **matched** vulnerability object rather than `in json.dumps(whole document)`.
  - `[low]` `[patch]` Builder hardened with fail-loud guards: malformed JSON, missing/non-string `id`, path-traversal-unsafe `id`, and record-ecosystem mismatch all raise instead of silently corrupting/hollowing the DB; tidied a no-op attr mask.
  - `[low]` `[patch]` Runner guards: `json.JSONDecodeError` → `None` (clean assertion failure, not a raise) and `TimeoutExpired` → `pytest.fail`.
  - `[low]` `[patch]` Softened § 1's `--offline-vulnerabilities` rejection wording (attributed to `--help`, not the proof test) and noted version-detection needs stdout capture (a further seam change); added a **Residual risks** section (egress trusted-not-observed; version-exact matching only).
  - `[defer]` Egress is trusted via `--offline`, not observed (the socket-deny harness can't patch a subprocess) → network-namespace/egress-counter harness owned by Story 5.2 (filed in `deferred-work.md`).
  - `[defer]` PEP-503 name-normalization / PEP-440 version-equivalence matching against the offline DB unexercised (synthetic exact fixture) → Story 1.5/2.1 (filed in `deferred-work.md`).
  - `[reject]` (5) untracked-in-git (committed at finalize, by design); missing-vs-empty cache dir (empirically identical — both 127); `1.0` vs `1.0.0` version-equivalence doc (osv semantics, out of spike scope); `*.JSON`/nested record glob (curated-fixture convention); relative-`-L`-path "root /" stderr cosmetic (benign, 0 dirs visited).

### 2026-07-14 — Follow-up review pass (Blind Hunter + Edge Case Hunter, Opus)
The follow-up caught a **CRITICAL empirically-confirmed false-green the cycle-1 patch had itself introduced**: the record's "present-but-corrupt zip → 127" claim (the basis for its § 4 "exit code is load-bearing" argument) is only true for *container* corruption. I re-ran `osv-scanner 2.4.0` directly: a valid zip whose `<id>.json` entry is content-corrupt (`{}` / malformed JSON / truncated / no-`affected`) is **loaded** and exits **0** with `results: []` on a KNOWN-VULNERABLE input — the namelist non-emptiness pre-flight passes and the exit code is 0, so **neither** mandated defense catches it. Story 1.5 built per the cycle-1 record would have shipped a vulnerable-reads-as-clean gate. Rewrote § 4 to a **content** pre-flight (parse each entry + validate the OSV advisory shape, reusing the builder's `_entry_for_record`), corrected the empirical table / seam #3 / residual-risk / architecture-reconciliation, and added conformance tests that pin the exit-0 false-green and the container-corrupt-127 contrast. All findings routed to `patch` — the intent-contract is correct; the deliverables needed grounding in fresh measurement, not re-derivation. New defers: 0 (the two prior-cycle defers stand; EC1/EC8 rejected — the builder's matchability guard already fails loud for a case-mismatched ecosystem, and rebuild-overwrite is intended idempotent behavior for a tmp-dir test helper).
- intent_gap: 0
- bad_spec: 0
- patch: 11: (high 1, medium 3, low 7)
- defer: 0
- reject: 2
- addressed_findings:
  - `[high]` `[patch]` **F1/F2** — content-corrupt DB false-green (empirically confirmed): a valid zip with a `{}`/malformed/truncated/no-`affected` entry → osv exit **0** on a vulnerable input, caught by NEITHER the exit code (0, not the 127 the record claimed) NOR a namelist non-emptiness check. Rewrote the empirical table (split content- vs container-corruption), § 4 pre-flight (now a **content** parse+shape check reusing `_entry_for_record`), the H2 correction (both pre-flight AND exit code required, disjoint classes), seam hand-off #3, residual-risk, and the architecture-reconciliation bullet. Added `test_present_but_content_corrupt_db_...` (×3 corruption classes) + `test_container_corrupt_db_exits_127_...`.
  - `[medium]` `[patch]` **F6** — § 2 `max_age_ok=None` was overloaded: `VulnData(None,None,None)` is legal for a vuln-axis-not-consulted (hygiene-only) run, so the blanket "None → indeterminate" rule handed to Story 2.4 would wrongly force every deptry-only scan to `indeterminate`. Disambiguated: `source is None` (not consulted, orthogonal) vs `source` set + `snapshot_at` None (consulted, provenance-less → `indeterminate`).
  - `[medium]` `[patch]` **F4/EC6** — `test_osv_requires_case_sensitive_PyPI_dir` would `FileExistsError`/fail on a case-insensitive filesystem (macOS/Windows default), contradicting the record's "any machine" / air-gap-cross-platform framing. Added a runtime case-insensitivity probe → `pytest.skip`.
  - `[medium]` `[patch]` **F5/EC7** — the DB-absent test asserted raw byte-equality across two different lockfiles (fragile if a future osv echoes a path/timestamp). Made the **semantic** invariant load-bearing (`results == []` on both + exit codes differ); kept byte-identity as a version-bound secondary observation; softened the record's "byte-for-byte identical" headline accordingly.
  - `[low]` `[patch]` **F3/EC2** — builder matchability guard now requires a **concrete** spec (a non-empty `versions` string / a `ranges` entry with `events`), rejecting `versions:[""]`/`[123]`/`ranges:[{}]`; scoped the "never a silent unmatchable DB" claim honestly to the in-repo fixture (external-DB validation is the 1.5 content pre-flight).
  - `[low]` `[patch]` **EC5** — the builder silently skipped `.json` records nested under a subdirectory while its comment CLAIMED to guard that case; added an `rglob` nested-record fail-loud and corrected the comment.
  - `[low]` `[patch]` **EC3** — a non-existent / non-directory `records_dir` raised a bare `FileNotFoundError`/`NotADirectoryError` instead of the module's contracted `ValueError`; added an `is_dir()` fail-loud guard.
  - `[low]` `[patch]` **F7** — softened the builder docstring's "byte-identical on any machine" to same-interpreter (matching residual-risk #5; `zipfile` create/extract-version header bytes are not pinned).
  - `[low]` `[patch]` **F8** — § 6 mischaracterized the `--output`→`--output-file` deprecation-with-warning as a within-2.x breaking change; reworded so the `<3` ceiling rests on "measured only on 2.4.0."
  - `[low]` `[patch]` **F9/F10** — dropped the tautological `absent.exit_code != 0` (made the `!= clean` cross-check load-bearing via an explicit `clean == 0`); fixed the "general-error code (127)" comment (127 = DB-load-failure, not shell general error).
  - `[low]` `[patch]` **F11** — narrowed § 9's "any secure temp name" to the tested claim (extension irrelevant when the parser is forced; verified for `.txt`).
  - `[reject]` (2) EC1 builder ecosystem-case param (the matchability guard already fails loud for a case-mismatched ecosystem vs the `PyPI` fixture; correct default); EC8 rebuild silently overwrites `all.zip` (intended idempotent behavior of a deterministic tmp-dir test helper — the determinism test relies on it).
  - Added unit tests for the three new builder guards: `test_builder_rejects_non_directory_records_dir`, `test_builder_rejects_record_nested_under_subdirectory`, `test_builder_rejects_non_concrete_version_spec`.

## Auto Run Result

Status: done

**Change:** Ran the Story 1.4 spike (OSV-DB offline provisioning) and, across two review cycles, produced (a) a git-**tracked decision record** (`planning-artifacts/osv-db-offline-provisioning-decision.md`) that **gates Story 1.5 + 2.4** (not 1.3) and resolves all AC1/AC3 questions — mechanism (`--offline` + `OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY` → `<eco>/all.zip`), staleness (`--db-max-age` 7d → `max_age_ok`, with the not-consulted-vs-provenance-less disambiguation), trust anchor (channel integrity + checksum), cold-start UX + nudge, online-opt-in disposition (offline-only v1), engine version ranges (`osv-scanner >=2.4.0,<3` / `deptry >=0.25.1,<1`), provisioning reuse (pattern from `cve_manager.py`, no bespoke downloader), mirror env (`OSV_VULNS_BUCKET_URL`), the `-L <parser>:<path>` override (removes the `requirements.txt` temp-name constraint), and distribution channels — all grounded in the live `osv-scanner 2.4.0 --help` + the proof test; and (b) a **hermetic fixture OSV DB** (readable OSV JSON + a deterministic `ZIP_STORED` builder + vulnerable/clean lockfiles + an offline proof test) the conformance suite consumes with zero network. **Zero production `src/` code** — the osv engine is Story 1.5; the record hands 1.5 a corrected **three-part `_engine_env` seam** contract (extra_env + a deterministic DB **content** pre-flight + surface exit code/stdout).

**Files changed (all new/tracked, test-only + the planning artifact):**
- `planning-artifacts/osv-db-offline-provisioning-decision.md` — the decision record (12 sections + empirical table + architecture-reconciliation + residual-risks).
- `tests/fixtures/osv-db/pypi/PDOS-FIXTURE-0001.json` — synthetic OSV-schema-valid CRITICAL advisory (`pdos-vuln-fixture==1.0.0`).
- `tests/fixtures/osv_db_builder.py` — deterministic, fail-loud `build_offline_db` (ZIP_STORED, fixed mtime, `<id>.json` entries; guards: non-dir/empty records-dir, case-variant + nested `.json`, malformed/unsafe/unmatchable records, non-concrete version spec).
- `tests/fixtures/lockfiles/osv-{vulnerable,clean}/requirements.txt` — the pinned inputs.
- `tests/conformance/test_osv_offline_db_spike.py` — 20 offline proof tests (detect / clean / `-L` override / DB-absent-127 semantic+byte-identity / no-packages-128 / determinism / entry-naming / empty-records + non-dir + nested + non-concrete fail-loud / present-but-empty false-green / **content-corrupt ×3 false-green + content pre-flight** / container-corrupt-127 / case-sensitive-PyPI).

**Review — cycle 1 (Blind Hunter + Edge Case Hunter, Opus):** intent_gap 0, bad_spec 0, patch 14 (high 2, medium 6, low 6), defer 2, reject 5. Corrected a false-green cold-start the record would have handed 1.5 (the seam discards exit code + stderr) and replaced a fragile stderr-string branch with a deterministic cache pre-flight.

**Review — cycle 2 / follow-up (Blind Hunter + Edge Case Hunter, Opus):** intent_gap 0, bad_spec 0, patch 11 (high 1, medium 3, low 7), defer 0, reject 2. The high patch fixed a **CRITICAL empirically-confirmed false-green the cycle-1 fix itself introduced**: the record's "present-but-corrupt zip → 127" claim holds only for *container* corruption; a valid zip with a **content-corrupt** `<id>.json` entry (`{}`/malformed/truncated/no-`affected`) is loaded by osv and exits **0** with `results:[]` on a vulnerable input — caught by neither the exit code nor a namelist non-emptiness check. Rewrote § 4 to mandate a **content** pre-flight (parse + OSV-shape validate, reusing the builder's `_entry_for_record`) and added tests pinning the exit-0 false-green + the container-corrupt-127 contrast. Also disambiguated the `max_age_ok=None` rule for Story 2.4, guarded the case-sensitivity test against case-insensitive filesystems, made the DB-absent proof's semantic invariant load-bearing, and hardened three more builder edge cases. No new defers (the two prior-cycle defers stand).

**Verification:** `pixi run --frozen -e python-deptry-osv-scanner python-deptry-osv-scanner-test` → **449 passed** (prior 1.1/1.2/1.3 suites + meta-guards unchanged + the spike suite, now 20 tests), re-run after the follow-up patches. `git status` confirms zero production `src/python_deptry_osv_scanner/` and zero `pixi.toml`/`pixi.lock`/`pyproject.toml` changes. Exit codes empirically re-measured this pass: vuln 1, clean 0, DB-absent 127, container-corrupt 127, present-but-empty 0, **content-corrupt 0**, no-packages 128.

**Residual risks:** (1) offline-ness is trusted via `--offline`, not observed at the network layer (subprocess is outside the in-process socket-deny harness) — 5.2 hardening. (2) matching proven only for the exact synthetic pin; PEP-503/PEP-440 normalization is Story 1.5/2.1. (3) NFR-C1 version pins are recommended in the record but not applied to `pixi.toml` (worktree re-solve toxic) — Story 1.5/1.7 hand-off. (4) the content pre-flight's pragmatic bar is "≥1 shape-valid advisory"; a DB with 1 valid + N corrupt entries would pass it — full per-entry validation is a heavier 1.5/2.4 option. **Follow-up review recommended** (`followup_review_recommended: true`): this pass made a material, security-relevant correction to the § 4 defense that gates Story 1.5, and the two-cycle pattern of §-4 false-greens warrants one more independent adversarial look at whether the content pre-flight fully closes the class.
