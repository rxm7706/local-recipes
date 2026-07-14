---
marp: true
paginate: true
size: 16:9
title: PyForge-Warden — never false-green
style: |
  section { background:#f3f2f2; color:#201e1d; font-family:'Archivo',Arial,Helvetica,sans-serif; font-size:26px; }
  h1 { letter-spacing:-0.03em; color:#201e1d; }
  h2,h3 { letter-spacing:-0.02em; color:#201e1d; }
  strong { color:#c22a10; }
  a { color:#c22a10; }
  code { background:#eae9e9; color:#c22a10; padding:0 .3em; }
  section.lead { background:#ec3013; color:#f3f2f2; }
  section.lead h1, section.lead h2, section.lead h3, section.lead strong, section.lead code { color:#f3f2f2; }
  section.lead code { background:rgba(255,255,255,.15); }
  hr { border:none; border-top:3px solid #201e1d; margin:.35em 0; }
  table { font-size:.72em; border-collapse:collapse; }
  th { background:#201e1d; color:#f3f2f2; text-align:left; }
  th,td { border:1px solid #d3d0cf; padding:6px 10px; }
  pre { background:#1a1918; color:#e8e6e4; font-size:.62em; }
---

<!-- _class: lead -->

PYFORGE-WARDEN · Dependency-trust gate · BMAD Tech Spec `pyforge-warden`

# never false-green

A CI dependency-trust gate for **both Python ecosystems** — PyPI applications and the conda / conda-forge world of scientific, analytics & ML/AI computing.

Brand **PyForge-Warden** · dist `pyforge-warden` · import `pyforge.warden` · CLI `warden`

<!-- The thesis in three words: never false-green. A green check must mean the dependencies were actually assessed and found safe. PyForge-Warden is a CI gate for BOTH Python ecosystems: pip/PyPI apps and the conda/conda-forge scientific and ML/AI world. -->

---

<!-- _class: lead -->

## ACT I

# The green check that lies

An exit-code gate can pass while your dependencies are unassessed, unparsed, or unsafe. That's the failure PyForge-Warden exists to end.

<!-- Act I frames the problem. The danger isn't a red X — it's a green check that never actually looked. -->

---

## 01 · Exit 0 is not a promise

A gate reduces to one number. **0 merges, non-zero blocks.** But exit 0 quietly conflates two very different states:

- **exit 0 — assessed & clean** — the tool looked hard and found nothing.
- **exit 0 — never looked** — the tool found nothing because it couldn't check.

Traditional gates can't tell these apart. PyForge-Warden refuses to collapse them — an unproven result is **never** reported as clean.

<!-- Exit 0 conflates 'I checked and it's clean' with 'I didn't really check.' A scanner that finds nothing returns 0 whether it looked or not. -->

---

## 02 · False-green #1 — the empty database

A vulnerability scanner is only as honest as its database. If the OSV feed is **missing, empty, corrupt, or stale**, a naïve scanner queries it, gets zero hits, and reports *clean*.

`db.records = 0` → naïve scanner: `verdict: clean ✓` → PyForge-Warden: **`verdict: indeterminate`**

PyForge-Warden **content-pre-flights the database** — record count, freshness, and integrity — before it trusts a single result. No proof of assessment, no green.

<!-- If the OSV database failed to download, is empty, or stale, a naive scanner gets zero hits and reports clean — a green check that means the opposite of safe. -->

---

## 03 · False-green #2 — the unassessable dependency

The stock engines don't parse conda & pixi manifests. A naïve pipeline **silently skips what it can't read** — and silence scores as clean.

| Manifest | Naïve pipeline |
| --- | --- |
| `pyproject.toml` | seen |
| `requirements.txt` | seen |
| `environment.yml` | **skipped** |
| `meta.yaml` | **skipped** |
| `pixi.toml` | **skipped** |

A conda-heavy ML repo passes while most of its graph was **never seen**. PyForge-Warden marks what it can't resolve `indeterminate`, not clean.

<!-- deptry and osv-scanner don't parse conda meta.yaml/recipe.yaml/environment.yml/pixi.toml. A conda-heavy ML repo scans 'clean' while most deps were never seen. -->

---

## 04 · Two ecosystems, one blind spot

**Ecosystem 1 · PyPI — Application Python**
~850K packages · open upload · any license
**20%** of footprint — ~400 shipped apps ≈ 2–3K libraries

**Ecosystem 2 · conda-forge — Scientific & Data Python**
~30K feedstocks · curated · FOSS-only
**80%** of footprint — ~1% of apps ≈ 7–8K libraries

<!-- Python is two ecosystems. Applications are 20% of footprint; the ML/AI/data stack is a tiny slice of apps but 80% of distinct libraries. PyForge-Warden covers both. -->

---

<!-- _class: lead -->

## ACT II

# The frozen contract

One report schema. One verdict lattice. One exit enum. Honesty encoded as a data structure.

<!-- PyForge-Warden's answer to false-green is a single, frozen, machine-readable contract. Nothing downstream has to guess. -->

---

## 05 · One report, one schema

Every engine and axis merges into one **ComplianceReport**, schema-validated against a committed contract.

- Producer-agnostic — the source of truth, not the log
- Carries **coverage** & **provenance** per axis
- Versioned schema — the contract can't silently drift

```json
{
  "schema_version": "1.0.0",
  "verdict": "policy-violation",
  "exit_code": 1,
  "axes": { "hygiene": "clean", "security": "policy-violation", "license": "indeterminate" },
  "coverage": { "manifests": 6, "resolved": 312 }
}
```

<!-- Everything flows into one artifact, validated against a committed JSON Schema. The human summary is just a rendering of it. -->

---

## 06 · The verdict lattice — highest wins

| Verdict | Result |
| --- | --- |
| `error` | exit 2 · operational |
| `policy-violation` | exit 1 · blocks |
| `indeterminate` | exit 1 · unproven |
| — pass line — | |
| `warn` | exit 0 |
| `bypassed` | exit 0 · waiver |
| `clean` | exit 0 |
| `not-applicable` | exit 0 |

The whole design turns on one placement: **`indeterminate` sits above the pass line.** An unproven axis fails the gate — it never slides down to clean.

<!-- Seven rungs, highest wins. indeterminate sits ABOVE the pass line — an unproven result blocks, never slides to clean. -->

---

## 07 · A frozen exit enum & typed errors

**0** success · clean / warn  |  **1** policy-violation / indeterminate  |  **2** operational error  |  **130** interrupted (SIGINT)

Four values, no drift — CI wires against these forever. Every operational failure is a **typed error with a named owner**:

`unparsable-manifest` · `engine-unavailable` · `engine-crash` · `internal-error`

<!-- The exit enum is frozen. Every operational failure is a typed error with a named owner, so a failure routes to whoever can fix it. -->

---

<!-- _class: lead -->

## ACT III

# The engines, orchestrated

Pluggable engines behind one report — six manifests read natively, isolated behind a hardened seam, across three supply-chain rings.

<!-- PyForge-Warden orchestrates deptry and osv-scanner behind one report, reads six manifest formats natively, isolates each engine, and scans at three concentric rings. -->

---

## 08 · deptry — the hygiene axis `v1`

AST import analysis over the source tree, cross-checked against declared dependencies. Honors your existing `[tool.deptry]` config.

| Code | Meaning |
| --- | --- |
| `DEP001` | missing — imported, not declared |
| `DEP002` | unused — declared, not imported |
| `DEP003` | transitive — used, not declared |
| `DEP004` | misplaced dev dependency |
| `DEP005` | duplicate declaration |

<!-- Axis 1, hygiene, ships in v1 with deptry — AST import analysis emitting DEP001–005, honoring existing tool.deptry ignore config. -->

---

## 09 · osv-scanner — the security axis `v1`

Google's OSV database checked against the resolved dependency set. The database is a **declared conda / pixi dependency** — never a runtime `curl`.

- **Provisioned** — DB ships as a pinned, declared dependency; reproducible & offline.
- **Pre-flighted** — record count, freshness & integrity verified **before** any result is trusted.
- **Fails honest** — a bad DB yields `indeterminate`, not a false clean.

<!-- Axis 2 ships in v1 with osv-scanner. The DB is a declared dependency (never a runtime curl) and PyForge-Warden pre-flights it before trusting a result. That's the fix for false-green #1. -->

---

## 10 · The hardened subprocess seam

Engines are external binaries. PyForge-Warden runs each behind a strict seam so a misbehaving engine can't corrupt a verdict.

- no shell — explicit **argv**
- timeouts + resource caps
- captured stdout / stderr
- **unavailable ≠ crash ≠ clean**

Each maps to a distinct typed error and `exit 2` — never a silent pass.

<!-- PyForge-Warden isolates each engine behind a hardened subprocess seam. A misbehaving engine becomes a typed error and exit 2 — never a silent pass. -->

---

## 11 · Six manifest formats — read natively

The manifest engine is the wedge — no engine parses conda / pixi. No untrusted input is executed: `yaml.safe_load` only.

| Manifest | Notes | Parser |
| --- | --- | --- |
| `pyproject.toml` | PEP 621 · Poetry · PDM | tomllib |
| `pixi.toml` | deps · pypi-deps · features | tomllib |
| `requirements.txt` | one requirement per line | line-parse |
| `environment.yml` | deps + nested pip: | safe_load |
| `meta.yaml` v0 | jinja + `# [selector]` | neutralize → safe_load |
| `recipe.yaml` v1 | requirements: run: | safe_load |

<!-- Neither stock engine parses conda/pixi. PyForge-Warden reads all six formats; meta.yaml v0 needs jinja/selector neutralization. safe_load only — no untrusted input executed. -->

---

## 12 · Three rings — scan the whole supply chain

The further out PyForge-Warden scans, the more it **prevents** rather than reports.

- **Public upstream** *(vision)* — scan PyPI & conda-forge: malicious, typosquat, name-squat & stale feedstocks. → *blocklists*
- **Registry perimeter** *(v1.x)* — block / allow lists on Artifactory / JFrog; a census of everything that enters. → *clean pulls*
- **Consumption edge** *(today)* — scan repos, desktops & CI: the axes on what apps actually pull.

<!-- PyForge-Warden runs at three depths. Edge is today; registry perimeter (JFrog blocklists) is v1.x and the star; public upstream scanning is the vision. -->

---

<!-- _class: lead -->

## ACT IV

# Offline by default

Deny-by-default egress, deterministic runs, a pre-flighted database. Trust that survives the air gap.

<!-- Enterprise Python often runs where the internet doesn't reach. PyForge-Warden is built for that. -->

---

## 13 · Deny-by-default egress

A scan makes **no network calls**. Database and engines are provisioned ahead of time as declared dependencies.

| | |
| --- | --- |
| network egress | **DENY** |
| OSV database | LOCAL |
| engines | DECLARED |
| online enrichment | **OPT-IN** |

Any online behavior is opt-in and explicit — never silent. Safe by construction in regulated and air-gapped estates.

<!-- PyForge-Warden makes no network calls during a scan by default. Any online behavior is opt-in and explicit, never silent. -->

---

## 14 · Deterministic & pre-flighted

**Determinism — same inputs, same verdict**
Pinned engines + pinned database. Reproducible on any machine, on any day — including one with no internet.

**Pre-flight — verify before you trust**
Record count, freshness & integrity checked first. A scan becomes **evidence you can defend** in an audit.

<!-- Determinism plus the pre-flight turn a scan into evidence you can defend in an audit. -->

---

## 15 · First contact — at your terminal

```console
$ warden scan . --warn-only
PyForge-Warden 1.0  ·  offline  ·  OSV db 2026-07-10 (312,004 records ✓)
discovered 6 manifests · resolved 312 packages
✓ hygiene     clean
✗ security    1 critical — numpy 1.22.0 · GHSA-xxxx
? license     2 unknown — indeterminate
verdict policy-violation — reported, not enforced (--warn-only)
exit 0
```

Adoption starts at a terminal, not a pipeline — see it work on your own machine before you ever touch CI.

<!-- warden scan . --warn-only runs locally, shows real findings, and exits 0 so nobody is blocked on day one. This is the on-ramp. -->

---

<!-- _class: lead -->

## ACT V

# From a gate to governance

Six axes of dependency trust, pluggable behind one report — hygiene & security today, four more on the roadmap.

<!-- The same contract extends across six axes. Engines are pluggable, so new signals slot in behind the same report and lattice. -->

---

## 16 · Six axes of dependency trust

| Axis | Question | Engine | Maturity |
| --- | --- | --- | --- |
| 1 · Hygiene | Is it used? | deptry | **v1** |
| 2 · Security | Is it vulnerable? | osv-scanner + KEV/EPSS | **v1** |
| 3 · License | Is it allowed? | license-expression | v1.x |
| 4 · Currency | Is it patchable? | endoflife.date | v1.x |
| 5 · Provenance | Is it authentic? | Sigstore / SLSA | vision |
| 6 · Maintenance | Is it maintained? | OpenSSF Scorecard | vision |

<!-- Six axes, each a different question. Hygiene + security ship v1; license + currency complete the v1.x gate; provenance + maintenance are the vision. -->

---

## 17 · KEV + EPSS — prioritize by exploitability `v1.x`

Not every CVE matters equally. PyForge-Warden enriches each finding so the gate blocks on **what's actually dangerous** — not theoretical noise.

- **CISA KEV — exploited in the wild** — the known-exploited catalog; a boolean that outranks a raw severity score.
- **FIRST EPSS — probability it will be** — a 0–1 exploit-prediction score for triage; gate with `--min-epss`.

`--fail-on-kev` · `--min-epss 0.5` — block on real-world risk, warn on the rest.

<!-- v1.x enriches the security axis. KEV = exploited now; EPSS = probability it will be. Together they block on what's actually dangerous. -->

---

## 18 · License & currency complete the gate `v1.x`

**Axis 3 · License — is it allowed?**
SPDX from PyPI metadata + conda `about: license`, normalized via **license-expression**. Gate on allow / deny lists.
`--allow-licenses` · `--deny-licenses`

**Axis 4 · Currency — is it patchable?**
**endoflife.date** + version-lag flag EOL & stale deps — and the Python runtime against LTS / N / N-1. Only current things get patched.
`--max-lag` · `--require-lts` · `--fail-on-eol`

<!-- License: read SPDX via license-expression, gate on allow/deny — unreadable is indeterminate. Currency: endoflife.date + version-lag flag EOL and out-of-date deps. -->

---

<!-- _class: lead -->

## ACT VI

# One command, one honest gate

The same command you ran locally becomes the merge gate — fleet-wide, and it never lies.

<!-- Everything reduces to one command with one trustworthy exit code. Wire it into CI and the same honest verdict runs fleet-wide. -->

---

## 19 · The gate, in CI

```text
warden / dependency-gate                       ✗ failing
✓ hygiene — clean
✗ security — 1 critical · KEV-listed
    numpy 1.22.0 · GHSA-xxxx · EPSS 0.83
✓ license — clean
verdict policy-violation · exit 1
↳ report artifact: compliance-report.json
```

Exit 1 **blocks the merge** — and the check shows exactly why, with the report attached. Green is **earned** — lock the environment, file an **expiring waiver** with a reason, or fix the finding. Never faked.

<!-- The same command as a CI check. Blocks the merge with exit 1 on a KEV-listed critical. Green is earned — never faked. -->

---

<!-- _class: lead -->

The honest-adoption posture

# A green check should mean it was *actually checked*.

No empty database, no skipped manifest, no false green.

A bare `recipe.yaml` scan exits non-zero by design — until you lock, waive, or run `--warn-only`. That's the lock-nudge working, not a bug.

PyForge-Warden · pyforge-warden · pyforge.warden · docs/specs/pyforge-warden.md

<!-- The close: a green check means it was actually checked. A bare recipe.yaml scan exits non-zero by design until you lock, waive, or warn-only. -->

---

## Appendix · Who PyForge-Warden serves

- **CISO — provable risk posture:** exploitability-prioritized findings (KEV/EPSS) and audit-grade, reproducible evidence.
- **Chief Dev Experience — a gate devs trust:** runs locally first, one command, no false alarms — so it doesn't cry wolf.
- **CIO — standardized & offline:** one gate fleet-wide, deterministic and air-gap-ready for regulated estates.
- **Chief Data & Analytics — the ML footprint, covered:** conda / conda-forge coverage — the 80% of libraries stock tools never see.

<!-- Executive personas: CISO, Chief Developer Experience Officer, CIO, Chief Data & Analytics Officer. -->
