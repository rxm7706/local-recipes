---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - src/shared/packages/pyforge-warden/src/pyforge/warden/ (shipped code, read directly)
  - _bmad-output/projects/pyforge-warden/planning-artifacts/retros/ (all 8 tracked epic retros)
  - _bmad-output/projects/pyforge-warden/planning-artifacts/deferred-work-ledger.md (verified 2026-07-30 pass)
  - _bmad-output/projects/pyforge-warden/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-warden/planning-artifacts/marshal-policy.toml
  - docs/dreams/pyforge-warden.md
research_type: 'technical'
research_topic: 'pyforge-warden as-shipped technical state: four-axis engine architecture, the conda/pixi manifest-resolution bridge, recurring bug patterns mined from the 8 epic retros + the verified deferred-work ledger, and the concrete post-v1 technical-debt map'
research_goals: 'Close the gap the 2026-07-25 research pair left open: no technical-*.md existed. Ground "what is actually fragile" in the retros and the 2026-07-30-verified ledger rather than guessing; name the real recurring bug families; identify which shipped patterns (the sole-subprocess seam, the sole-ownership verdict module, the differential oracle) are generalizable factory infrastructure.'
user_name: 'Rxm7706'
date: '2026-08-08'
web_research_enabled: true
source_verification: true
scope_note: 'Warden is fully shipped (31/31 stories, 6/6 epics, PR #110 merged 2026-07-25; ~1,936 fast tests + slow corpus/oracle suite green at close). This is a post-ship technical audit, not pre-build research. The only code change to the package since ship is the 2026-08 audit-remediation commit 864558e02d — the shipped surface is otherwise exactly what the retros describe.'
---

# Research Report: Technical Research — Warden Dependency Gate, As Actually Shipped

**Date:** 2026-08-08
**Author:** Rxm7706
**Research Type:** Technical (post-ship state + debt map)

---

## 1. The shipped architecture, measured from the code

Package: `src/shared/packages/pyforge-warden/src/pyforge/warden/` — ~11,700 lines across 20 modules, with the mass concentrated where the retros said the work was:

| Module | Lines | Role |
|---|---|---|
| `cli.py` | 1,879 | orchestration: discovery → extract → 4-axis engine fan-out (`ThreadPoolExecutor`, 5.2) → policy → report |
| `engines.py` | 1,880 | **the sole subprocess-capable module** — `_engine_env()` seam + registry `[NullEngine, DeptryEngine, OsvEngine, LicenseEngine, CurrencyEngine]` + `run_doctor_checks` (5.1) |
| `vuln.py` | 1,244 | OSV parse, severity gate, KEV/EPSS enrichment, `_extract_fixed_version` |
| `config.py` | 1,031 | 3.1 ConfigLoader, two-mode policy (6.5) |
| `models.py` | 908 | the frozen `ComplianceReport` (schema 1.1.0) + `Finding.__post_init__` id-family validation |
| `waiver.py` | 873 | expiring waivers (3.2) + baseline/grandfathering as a second producer over the same engine (6.8) |
| `currency.py` / `license.py` | 869 / 797 | the two no-subprocess axes (6.3 / 6.2) |
| `report.py` | 818 | renderers incl. remediation lines (5.1) |
| `verdict.py` | 140 | **sole owner** of the 7-rung lattice + exit projection `{0,1,2,130}`, enforced by `tests/meta/test_verdict_sole_ownership.py` |
| `routing.py` | 96 | the FR2 seam: 17 `(manifest_kind, section) → Ecosystem` pairs; unknown pairs fail loud |
| `mapping.py` | 51 | plumbing for the bundled ~12K-entry `conda_pypi_map.json` (generated from the CFE atlas `export-purls` TSV) |
| `discovery.py` | 244 | recursive bounded discovery; **fails closed** on symlinked dirs, TOCTOU ENOTDIR, dangling symlinks, non-regular files |

Three deliberate concentrations of authority are the architecture's load-bearing walls, and each is machine-enforced, not just documented:

1. **Verdict sole-ownership** — every module *feeds* rungs; only `verdict.py` *projects* to exit codes (`test_verdict_sole_ownership.py`). The one sanctioned flag exception (`--allow-empty` downgrading exactly the D2(c) `EMPTY_EXTRACTION_DRIVER_ID` indeterminate to exit 0, status untouched) lives there too, keyed on id **equality**, never prefix.
2. **Subprocess sole-siting** — `engines.py` is the only module allowed to spawn; `_engine_env()` normalizes every call (argv list, tempfile output outside the scanned tree, `NO_COLOR=1`, `stdin=DEVNULL`, bounded timeout, typed `ErrorRecord`). 6.6 added exactly one narrowly-scoped second call site (`_check_engine_version` `--version` pre-flight) with a recorded reason it can't ride the seam.
3. **The frozen trio** — `report-schema.json` / `models.py` / `verdict.py` were frozen at 6.1 (schema 1.1.0) and every one of Epic 6's 8 later gates was scope-checked to a zero diff against them (Epic 6 retro). All came back clean.

**The manifest-resolution bridge** — the part deptry and osv-scanner cannot do natively — is the `discovery.py` → `extract/` → `routing.py` → `inventory.py` → `hygiene._synthesize_deptry_frontdoor` / OSV-input-synthesis chain: 9 manifest kinds (`pyproject.toml`, `pixi.lock`, `conda-lock.yml`, `recipe.yaml`, `meta.yaml`, `environment.yml`, `environment.yaml`, `pixi.toml` + sections), non-rendering extraction validated against a **rendering differential oracle** (2.2, ratcheted 2.3, matured to a ~2,000-recipe corpus in 5.2), and an unconditional synthesized `name[==version]` front-door handed to deptry (safe because deptry's own documented pyproject-precedence rule makes it a no-op for native scans).

Validation teeth that are real, not decorative (5.2): the fast suite (~1,936), the slow corpus/differential-oracle suite, an **strace egress counter** wrapping the whole `warden scan` process tree in `-f -e trace=network` across the full corpus asserting 0 network syscalls, and a dogfood self-scan that composes `bypassed`/exit 0 against the committed `.warden-baseline.yaml`.

## 2. Recurring bug patterns — mined from the 8 retros + the verified ledger

The deferred-work ledger was promoted verbatim to tracked on 2026-07-29 and given a by-hand verification pass on 2026-07-30 (`deferred-work-ledger.md`), so every "still open" below is a checked fact with a file:line citation in the ledger, not a stale note. Clustering the ~30 open entries plus the retros' pre-merge catches, four genuine *families* recur:

### Family A — name/version identity normalization at ecosystem boundaries (the deepest one)

The single most repeated defect shape across the whole effort is a normalization rule valid in one namespace applied in another, or an equivalence left unexercised:

- **DW-5-1-8 (open, confirmed at `cli.py:1277`):** PEP-503 canonicalization applied unconditionally to every component name — semantically valid only for PyPI; conda separator-twins (`importlib-metadata` vs `importlib_metadata` are *distinct* conda-forge packages) collapse to one key, so a remediation line can name the other package's manifest location. Found independently by both third-pass reviewers.
- **DW-1-4-1 first bullet (open — the 2026-07-30 pass corrected a wrong `done`):** PEP-503/PEP-440 equivalence matching against the offline OSV DB is *still unexercised* — zero test hits for `pdos_vuln_fixture`; only the literal pin `pdos-vuln-fixture==1.0.0` is proven. A differently-spelled-but-equivalent package silently missing a real CVE remains an untested path.
- **1.1-era deferral (open):** PEP-440-equal spellings (`2.31` vs `2.31.0`) split component identity, double-count inventory, and fork finding ids across runs (`inventory.py:94`).
- **DW-6-3-7 (open):** `currency:`/`license:` finding ids carry no ecosystem discriminator, so a conda and a PyPI package with the same name@version share one finding id.
- Pre-merge catch of the same shape: **6.3's alias-collision silent-misroute** (Epic 6 retro).

*Why it recurs:* Warden's whole wedge is straddling two namespaces with different identity rules, but identity handling is spread across `inventory.py`, `mapping.py`, `report._canonical_subject_key`, and `cli.py`'s `manifest_locations` build rather than owned by one module the way verdicts and subprocesses are. **Opportunity: an "identity sole-ownership" module + meta-test, the third wall to match the two that exist.** DW-1-4-1's unexercised-normalization test is the cheapest first move and directly de-risks a silent CVE miss.

### Family B — remediation/advice correctness (the verdict is safe; the advice is the false-statement hotspot)

The lattice never false-greened in any recorded incident, but the *human-facing advice layer* produced (or nearly produced) wrong statements repeatedly:

- **Caught pre-merge (5.1, adversarial review):** cross-package fixed-version attribution — `_extract_fixed_version` read `fixed` events from every `affected[]` entry, so a multi-package advisory could emit a wrong "upgrade to ≥X". Fixed with tests; the retros call this class "Warden's cardinal false-green risk".
- **DW-5-1-6 (open, `vuln.py:744-750`):** first-vs-MAX fixed event — for multi-branch backport advisories (Django-style) the remediation can advise an upgrade bound the user's installed version already satisfies. Blocked on a spec-level decision because "take the FIRST" is written into the 5.1 intent contract.
- **DW-5-1-7 (open, `cli.py:1268-1282`):** manifest-location clause unions provenance across all same-named components version-blind, steering the operator to a manifest declaring only the non-vulnerable version.

*Why it recurs:* the machine contract got the frozen-schema + sole-ownership treatment; the advice strings did not — they're assembled in `cli.py`/`report.py` from re-parsed finding ids (DW-5-1-3: recovering the advisory id by re-splitting the finding id) rather than from structured fields. **Opportunity: a structured `Remediation` object (advisory id, fixed-version selection rule, version-keyed locations) instead of string assembly — one contained refactor retiring DW-5-1-3/6/7/8 together.**

### Family C — shared constants and calendar time bombs

- **DW-6-3-5 / DW-6-7-2 (open):** the endoflife.date and EPSS caches both reuse `feeds.DEFAULT_FEED_MAX_AGE_DAYS` (7 days, tuned for KEV) — wrong freshness semantics for a daily-republished feed (EPSS) and a slow-moving one (EOL).
- **DW-5-2-7 (open):** all 19 committed `.warden-baseline.yaml` entries expire **simultaneously at 2027-07-24T00:00:00Z**; on that date the default-suite dogfood test and pixi task go red by calendar with no code change — an unattended loop would triage it as a regression. Expiry-forcing-re-review is 6.8's intended design; the single shared cliff is the defect.
- **DW-5-2-6 (open, `.warden-baseline.yaml:38`):** the `currency:unknown:!python-runtime@3.14.6` baseline id hardcodes the interpreter patch version — any Python bump silently un-matches it.
- Same shape, caught earlier: DW-6-7-4's quadruplicated atomic-write double-close (fixed 2026-07-30) and DW-6-7-5's tripled conformance-helper trio (open).

*Why it recurs:* copy-adaptation of a working pattern (the KEV feed shape, the first baseline entry) without re-deriving the constant for the new context. Cheap fixes; the baseline-cliff one has a hard deadline and should be staggered well before 2027-07.

### Family D — the gate that doesn't gate itself (validation-wiring gaps)

- **DW-5-2-5 (open, verified against `.github/workflows/`):** *nothing* ever executes `pyforge-warden-test-corpus-oracle` — and 5.2's whole-module slow-marking moved the 4 pre-existing precision differential-oracle tests (2.2/2.3) out of the default gate with it. An extractor change that breaks render-parity now merges green and surfaces only when someone remembers the slow task. For a tool whose central claim is honest coverage, its own strongest honesty check is currently unscheduled.
- **DW-6-5-2 (open):** `warn-as-error` exit projection leaves no trace in the persisted report — the report says warn/`exit 0`-shaped while the process exited 1.
- **DW-6-8-3 (open):** an EXPIRED suppression is invisible in the machine-readable contract (`suppressions[]` omits it; only the human renderer mentions it).
- **A3 (Epic 5&6 retro, open):** `license.py` (6.2) landed at the 3-review-cycle cap ("did not converge", 20+ fixes) — the recorded follow-up review of this compliance-critical axis has sat unactioned since 2026-07-24 (DW-FU entries confirm no review artifact exists).
- Longstanding small one: `DEFAULT_HYGIENE_POLICY`/`DEFAULT_VULN_SEVERITY_POLICY` module-level dicts still mutable (Epic 3 retro action item, operator-deferred since 2026-07-17).

*Why it matters most:* Families A–C are ordinary debt; Family D is *meta-debt* — gaps in Warden's ability to notice its own regressions. DW-5-2-5 (wire the slow suite into a scheduled runner) is the highest-leverage single item in this report.

## 3. Smaller confirmed items (verbatim from the verified ledger)

- **DW-5-2-1:** the 5.2 `ThreadPoolExecutor` fan-out (`cli.py:1345`) hardcodes `shutdown(wait=True)` — SIGINT now waits for every in-flight engine subprocess; conflicts in spirit with the explicit exit-130 contract.
- **DW-6-3-9:** any producer-side duplicate finding-id collision turns the whole scan into `error`/exit-2 (fail-closed-hard where fail-closed-soft may be better fleet behavior).
- **DW-6-8-5:** `load_waivers` uses plain `yaml.safe_load` — duplicate keys silently keep the last entry.
- **DW-6-3-6:** both currency resolvers parse and drop the `lts` boolean.
- Deptry forward-compat: an unrecognized record *shape* escalates the whole scan to `error` (vs unknown DEP *code* → `indeterminate`); bounded today only by the 0.25.1 conda pin.
- **DW-CROSS-CUTTING-1 (open):** `pixi-build-python` 0.8.3 path-length panic still pinned in `pixi.lock`; mitigated fleet-wide by short loop roots + `--frozen` verify (`marshal-policy.toml` `verify_commands` already carries `--frozen` — DW-1-1-1 closed by exactly that).

## 4. Watch items created by upstream motion since ship

- **osv-scanner v2.5.0 (released 2026-08-07)** migrated scanning/filtering/matching **end-to-end onto OSV-Scalibr** (`--experimental-plugins`). Warden's 6.6 engine version-range pin + `--version` pre-flight is exactly the right defense, but the next in-range osv-scanner bump is now a *pipeline replacement*, not a point release — the deferred "unrecognized record shape → error" fail-closed-hard behavior (§3) is the specific seam a Scalibr-era output-shape drift would hit fleet-wide. Re-run the conformance suite against 2.5.x deliberately before any pin widening; details in the market refresh.
- **deptry** now lives at `osprey-oss/deptry` (still v0.25.1, 2026-03-18 — no release in ~5 months); `architecture.md`'s `fpgmaas/deptry` citation remains stale (DW-6-8-1 adjacent, low urgency).

## 5. What generalizes to the factory (cross-station note)

Written blind to Marshal's concurrent unification research, as directed — from Warden's side, three shipped patterns are proven candidates for shared infra:

1. **`engines.py`'s `_engine_env()` subprocess-normalization seam** — argv-list-only, temp-file output outside the scanned tree, typed `ErrorRecord` taxonomy, bounded timeout, exit-code-as-content-vs-operational discrimination. This is the same problem class as Marshal's AD-5-style subprocess guards; Warden's version is the most battle-tested in the fleet (every deptry/osv call for 31 stories plus the strace-verified corpus).
2. **The sole-ownership + meta-test discipline** — Marshal's `core/verdict.py` already independently re-implemented a 6-rung lattice + exit projection *citing Warden's as precedent* (its own docstring), and Doctor's `checks/registry.py` carries a deliberately-static mirror of `run_doctor_checks`' check catalog with a drift meta-test. The pattern is factory convention now; what's shared is the *discipline*, not (yet) code — see the domain refresh § cross-station for whether that's the right stopping point.
3. **The differential-oracle + egress-counter validation pattern** (non-rendering fast path checked against a rendering oracle; strace over the process tree) — directly reusable by any station that shells out or re-implements a parser.

## 6. Prioritized debt map (this report's synthesis)

| Priority | Item | Why |
|---|---|---|
| P0 | Wire `pyforge-warden-test-corpus-oracle` into a scheduled runner (DW-5-2-5) | the strongest honesty check is currently never executed by anything |
| P0 | Stagger `.warden-baseline.yaml` expiries before the 2027-07-24 cliff (DW-5-2-7, with 5-2-6) | deterministic future red-day, cheap now |
| P1 | Exercise PEP-503/440 normalization vs the offline OSV DB (DW-1-4-1 bullet 1) | the one untested silent-CVE-miss path |
| P1 | The 6.2 `license.py` follow-up review (A3) | compliance-critical axis that landed at the review cap |
| P1 | Structured `Remediation` object retiring DW-5-1-3/6/7/8 | the false-advice family, one contained refactor |
| P2 | Feed-specific max-age constants (DW-6-3-5, DW-6-7-2); expired-suppression visibility (DW-6-8-3); warn-as-error trace (DW-6-5-2) | honesty-of-the-report items below the verdict layer |
| P2 | Freeze default policy dicts; `yaml` dup-key guard; SIGINT fan-out shutdown | small hardening, all ledger-cited |
| Watch | osv-scanner 2.5.x Scalibr migration; deptry org/citation; pixi-build-python panic | upstream, defended by 6.6 pins |

## Sources

- Shipped code read directly 2026-08-08: `src/shared/packages/pyforge-warden/src/pyforge/warden/{verdict,engines,routing,mapping,discovery,cli,vuln,models,waiver}.py` and tests
- `_bmad-output/projects/pyforge-warden/planning-artifacts/retros/` — all 8 tracked epic retros (1&2 combined 2026-07-17; per-epic 1–6 + 5&6 closeout, 2026-07-25)
- `_bmad-output/projects/pyforge-warden/planning-artifacts/deferred-work-ledger.md` — promoted 2026-07-29, per-entry verification pass 2026-07-30 (every "open/confirmed" above cites its verified entry)
- `gh api repos/google/osv-scanner/releases/latest` (2026-08-08) — v2.5.0 Scalibr migration; `gh api repos/osprey-oss/deptry` (2026-08-08)
- [OSV-Scalibr supported inventory types](https://github.com/google/osv-scalibr/blob/main/docs/supported_inventory_types.md) (fetched 2026-08-08)
- Cross-station code: `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/verdict.py`, `src/shared/packages/pyforge-doctor/src/pyforge/doctor/checks/registry.py` (read 2026-08-08)
