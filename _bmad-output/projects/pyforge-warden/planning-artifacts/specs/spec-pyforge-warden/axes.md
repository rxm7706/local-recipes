# The axes of trust — four live, two vision

Companion to `SPEC.md`. The kernel's Constraints declare the six-axis identity and which
axes are built; this file is the per-axis catalog: what each assesses, from what data,
with what verdict vocabulary, and under what default gating posture.

An axis is one assessment lane over the resolved inventory. Axes register behind the
existing engine seam with an axis string — there is no separate axis protocol. The one
hard seam is the report's registered-axis tuple: a coverage claim for an unregistered
axis is a hard error, never a silent drop.

---

## Live axes (registered, reporting, gating in v1)

### Axis 1 — Hygiene

| | |
|---|---|
| **Engine** | `deptry` (conda run-dep, tested version range) |
| **Assesses** | unused · missing · transitive · misplaced-dev · stdlib-dependency (DEP001–DEP005) |
| **Input** | source-tree AST + import→distribution mapping; versions ~irrelevant |
| **Severity** | deptry emits **none** — the rules are uniform violations, so the hygiene→status table is *our* policy artifact and lives in the config loader |
| **Default posture** | **gates.** DEP001 (missing dependency) blocks by default, gated on conda↔PyPI name-mapping confidence — block on a high-confidence mapping, `warn` on an ambiguous one, so a mapping miss never becomes a false-red disable-driver. DEP002–005 → `warn` (false-positive-prone on conda recipes that legitimately carry deps deptry cannot see). An unknown DEP code → `indeterminate`. |
| **Join** | per-code, not uniform: DEP001 is on the *module* axis so it carries no component ref by construction; DEP002–004 are on the *declared-dep-name* axis and join to a component by name. Hygiene findings are therefore not 1:1 with the inventory. |

### Axis 2 — Security

| | |
|---|---|
| **Engine** | `osv-scanner` (conda run-dep, tested version range) + joined feeds |
| **Assesses** | known vulnerabilities — advisory ID, affected/fixed version, CVSS severity |
| **Enrichment** | **CISA KEV** (`kev`, `kev_date`) and **FIRST EPSS** (`epss {score, percentile}`), each a cached feed carrying its own provenance `{source, snapshot_at, max_age_ok}`. Enrichment happens at exactly one position — inside the vuln producer, **before** policy dedup. |
| **Default posture** | **gates.** Blocks on CVSS-critical **and** any KEV-listed advisory on a pinned version. `--min-epss <0..1>` adds an EPSS threshold. |
| **Feed-absence semantics** | with no KEV/EPSS policy in effect, null slots gate on CVSS as before. Under an active policy, an absent or stale snapshot → `indeterminate` — the gate never silently no-ops. `kev: null` (feed absent) stays distinguishable from "assessed, not KEV-listed". |
| **Matchability** | osv has no conda ecosystem, so `vuln_matchable = pypi_identity is not None AND version resolved to ==X.Y.Z` (see `extraction-contract.md`). For a mapped-but-unversioned dep, the **name-level tier** asks instead: does this package carry any known critical CVE across *any* version? → `indeterminate: carries known critical CVEs — pin/lock to prove immunity`. A ranked worry-list and a lock-nudge, not a dead coverage number. |

### Axis 3 — License

| | |
|---|---|
| **Engine** | `license-expression` (SPDX normalizer) |
| **Assesses** | every resolved component's license, normalized to an SPDX expression |
| **Input** | (a) the conda recipe's `about: license:` (+ `license_family`) — resolving **pre-build**; (b) installed-distribution metadata via `importlib.metadata` (PEP 639 `License-Expression`, legacy `License`, trove classifiers). **No source scanning.** |
| **Verdict** | `allowed \| denied \| unknown` |
| **Default posture** | **flag-activated.** Unconfigured the axis reports `gating: false` and its verdicts surface on the visible `warn` rung. `--allow-licenses <SPDX,…>` / `--deny-licenses <SPDX,…>` activate the gate: denied → `policy-violation`, unknown → `indeterminate`. |
| **Honest gap** | a bare uninstalled PyPI manifest yields `unknown` — a coverage gap and a lock-nudge, not a guess. |

### Axis 4 — Currency

| | |
|---|---|
| **Engine** | tiered lookup, no external engine |
| **Assesses** | currency/supportability of every resolved component **and the Python runtime** |
| **Input (tiered)** | bundled LTS registry (via `importlib.resources`) → endoflife.date (cached feed) → N/N-1 from conda channel data → `unknown` |
| **Emits** | `latest`, `lag`, `eol_date` + verdict `supported \| eol \| unknown` |
| **Default posture** | **flag-activated**, and **freshness-preconditioned**: `--max-lag <n>` / `--require-lts` / `--fail-on-eol` activate the gate, but a stale bundled registry → `indeterminate`, never a pass. Unconfigured → `warn` (never a silent clean). |
| **Mode split** | edge mode (no estate at runtime) = bundled registry + local caches, with N/N-1 degrading to a **visible** `unknown` when channel data is absent. The availability-at-N/N-1 finding is fleet-mode only; edge omits it with a coverage note. |
| **Provenance** | verdicts derived from bundled data carry a build-time `snapshot_at` + `max_age_ok` — a stale registry can never silently report `supported`. |

## Vision axes (named, unbuilt)

| Axis | Would assess | Candidate signals |
|---|---|---|
| **Axis 5 — Provenance** | package source verification, signature validation, authorship | Sigstore / SLSA attestation, PEP 740 trusted publishing, in-toto / GUAC |
| **Axis 6 — Maintenance** | abandonment and upstream health | OpenSSF Scorecard, `criticality_score`, sustainability / give-back signals |

Both sit in the vision bucket with no owner and no trigger. The Charter's six-axis Warden
identity is the **destination**; the shipped surface is four.

## The two-mode policy rule (cross-axis)

| Axis policy flags | `gating` | An `unknown` / `denied` / `eol` verdict |
|---|---|---|
| unconfigured | `false` | feeds a **`warn`** rung, driver naming the axis — status `warn` (not `clean`), exit 0. `--warn-as-error` escalates for strict shops. |
| configured | `true` | escalates per that axis's mapping: denied/eol → `policy-violation`, unknown → `indeterminate` |

The `gating` bool has a **single writer** — the config loader computes it from the parsed
flags; producers and the report only read it. Axis producers never feed a rung above
`warn`; escalation is owned in exactly one place.
