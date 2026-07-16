# Adversarial review — reshaped Warden spec (PR #62)

**Date:** 2026-07-15 · **Spec reviewed:** `docs/specs/pyforge-warden.md` @ `b11dd46` (branch
`claude/refine-local-plan-tily0h`, PR #62, 1,088 lines) + both Marp decks on that branch ·
**Method:** 6 parallel Fable-model subagents (schema closure · pins/distribution ·
provisioner/positioning · sizing/bloat · FR crosswalk · invariant attack), each grounded with
pre-verified `file:line` evidence and instructed to refute rather than confirm; verdicts
synthesized by the orchestrating session. Claims without `file:line` evidence were discarded.
**Ground rules honored:** the brief's "Known — do not re-report" list (two-engine PRD drift =
story 0.1; CFE retro owed; ecosystem stats = task #1; Marp formatter hazard) is not re-reported
as new; the out-of-scope list (0.1 reconciliation, readiness re-runs, stat restoration, memory
fix) was not executed. Spec citations are written `spec:<line>` and refer to the `b11dd46`
version; the decks were **not** edited by this review (the `head -8` formatter check is
therefore N/A — nothing to verify).

---

## 1 · Never-false-green trades (highest-value findings, ranked)

Ranked. Items T1–T7 are from the invariant-attack agent; T-a/T-b from the pins and positioning
agents. Each states the concrete inputs → green-outcome scenario.

1. **T1 — the KEV gate silently no-ops when the feed is absent or stale, under the DEFAULT
   policy.** The spec picked silent degradation and states it: FR-K1 spec:414-416 "Absent
   enrichment data → the slots stay null and the finding gates on CVSS as before (never a false
   clean)" (repeated OD10 spec:835-836) — and that parenthetical is **false for the gate case**.
   KEV-block is the v1 *default* (spec:142, :329-331) and offline is the *default* (spec:104-108).
   *Scenario:* default-offline runner, KEV never provisioned; a dep carries a HIGH-severity,
   KEV-listed CVE → `kev: null` → CVSS-high → `warn` → **exit 0**. Known-exploited vuln,
   advertised-default gate, green, zero signal. The OSV DB gets a content pre-flight
   (`VulnData.max_age_ok`, `models.py:187-205`); the KEV feed gets nothing — no max-age, no
   provenance, no absent-vs-not-listed distinction, no provisioning story (spec:862-866 names
   only the OSV DB). NFR-S2 governs only the *online* direction; nothing surfaces the
   offline-default *absence* of the feed.
2. **T2 — an all-`unknown` non-gating axis is invisible in status and exit code: a false green
   wearing a flag.** spec:341-343/:405-406 make v1 unknown license/currency "a reported
   `unknown`, not `indeterminate`"; per the shipped verdict model only fed rungs affect
   status/exit (`verdict.py:50-74`; Policy "feeds, never projects"), so the axis feeds nothing.
   *Scenario:* bare `pyproject.toml`, 40 uninstalled PyPI deps; hygiene + security clean →
   license 0/40 assessed → `clean`/exit 0; exit-code-only CI (the normal consumer) reads green.
   The honesty flag (`gating: false` + per-axis coverage, spec:684-688) has **no required
   consumer**: `--fail-under-coverage` appears nowhere in the spec and is default-OFF in
   prd.md:548, on a rationale (prd.md:525 "any coverage gap already exits non-zero via
   indeterminate") that D4 itself invalidated for non-gating axes. This trade also contradicts
   the spec's own frozen invariant three times — see § 4 item 1.
3. **T-a — the engine pins are unowned (live today, fleet-scale).** Every distribution gate hangs
   on "story 1.7's engine pins" (spec:151-152, :171, :510, :755-759, :1014) while epics.md story
   1.7 ("Typed errors & the no-scan guard", epics.md:205-215) contains **zero pinning work**, no
   other story owns editing `pixi.toml:32-33` (`deptry = "*"`, `osv-scanner = "*"`), and canonical
   NFR-C1 (prd.md:597) mandates a *range, not an exact pin* — contradicting the spec's "pins"
   language. As written, v1 JFrog publish could satisfy every extant story AC with the engines
   still `"*"` — the exact fleet-wide false-error (and, under silent output-schema drift,
   false-green) path the gate claims to prevent.
4. **T4 — the bundled LTS registry produces a *gated* stale-green at v1.1.** The registry is
   frozen at wheel-build time (spec:100-105, :434-438) with no max-age and no staleness
   annotation — currency provenance is `{source, snapshot_at}` only (spec:685), with no
   `max_age_ok` analogue, while NFR-S2 covers *fetched* feeds only (spec:472-487). *Scenario:*
   a package's EOL is announced after the wheel was built; an offline scan months later reports
   `supported` (cosmetic in v1) — and **v1.1 `--fail-on-eol`/`--require-lts` exits 0 on an EOL
   component** with no age signal anywhere.
5. **T-b — the v1.1 channel-provenance axis inherits the defect the provisioner refusal proves.**
   The refusal's premise — mirror-mode estates' `pixi.lock` records canonical
   `conda.anaconda.org` URLs; real routing lives in gitignored `.pixi/config.toml`
   (`docs/pixi-config-jfrog.example.toml:103-114`, `docs/enterprise-deployment.md:311-328`) —
   applies equally to the v1.1 read-only channel/index-provenance axis the same section schedules
   (spec:964, :511). Without a stated mechanism beyond the lock (e.g. reading pixi config layers
   as `detail-cf-atlas` does, `docs/enterprise-deployment.md:404-406`), that axis misreports in
   exactly the estates that care — false-red for the approved shop, and false-green in the
   inverse (a rogue channel routed through local config is invisible to the lock).
6. **T5 — the conda-beachhead *currency* claim is asserted, not specced.** spec:96-98 claims
   conda components carry "real license/currency verdicts in v1", but FR-C1 (spec:431-449) gives
   no mechanism by which a zero-data-estate edge machine computes `latest`/`lag`/EOL for conda
   components pre-build — the claim collapses to `unknown` on the flagship mode, invisibly per
   T2. (The *license* half is genuinely specced, FR-L1 spec:419-421 — though `about: license` is
   author-self-declared metadata presented as a "real verdict", unflagged.)
7. **T6 — the N/N-1 tier and the D10 ADD/UPDATE finding have no edge-mode data source.**
   "conda channel data" (spec:441-442, :821-822) has no stated offline source on a bare edge
   machine; the ADD/UPDATE finding is realizable only via fleet-mode machinery
   (`inventory-match`/`add-handoff`, spec:445-449, :822-829). Silent-omission risk in the mode
   the spec calls the differentiator.
8. **T3 — D3's "cheap; no schema amendment" premise is miscosted.** FR-K1 (spec:408-409) and the
   DoD (spec:993) promise `kev_date`, which exists nowhere in the package (`Finding` = kev/epss
   only, `models.py:225-231`) — an amendment, contradicting spec:132-135. Not itself a false
   green, but the load-bearing justification for T1's gate is wrong.
9. **T7 — KEV `null` is ambiguous** between "feed absent" and "assessed, not listed", and the
   report carries no per-feed KEV provenance (spec:414-416; generic vuln provenance covers the
   OSV source only, spec:920-923) — which blocks any downstream consumer from even *detecting*
   T1.

## 2 · Verdicts D1–D11

| Decision | Verdict | Basis |
|---|---|---|
| **D1** — reshape around deck Parts I–IV | **SOUND-BUT-COSTLY** | The bloat premise is **refuted**: the spec contains no control plane, no OSPO, no leader scorecards, no ~60-tool surface (0 grep hits each) — Parts III–IV stayed in the decks. Measured: ~77% v1-actionable contract, ~20% context/positioning, <1% vision rows (spec:86-88, :512-513). Precedence is explicit ("READ FIRST (WINS over the whole body)", spec:67, :74-76). The real cost is **supersession layering**: four stacked layers (body → callouts → OD brackets → Reconciliation note) with at least one stale bracket (spec:775 still says "KEV deferred" against D3) — exactly what story 0.1 must flatten. |
| **D2** — registry perimeter → v2 | **SOUND** | spec:86, :512, :840. No v1 feature silently requires the perimeter; the nearest candidate (v1.1 channel-provenance axis, spec:960-965) records its own weakness as accepted risk. |
| **D3** — KEV gate → v1 | **RECONSIDER** (as specified) | The gate itself is fine; its offline semantics and cost accounting are not. The brief's doubt is confirmed: the reversal answers prd.md:546-547's first clause (annotation-without-gate) while the second clause — the data-source cost — is incurred and unspecced (no cache location/lifecycle/age policy/provisioning story; spec:862-866 names only the OSV DB). Picked behavior is silent no-op offline (spec:414-416, :835-836) — see T1. And D3's "cheap; no schema amendment" (spec:840) is partly false: FR-K1's `kev_date` is an amendment (T3). Fix for SOUND: absent/stale KEV snapshot under a KEV-blocking policy → `indeterminate` (or a mandated typed warning + report-visible KEV provenance with `max_age_ok`), mirroring the OSV pre-flight; assign feed provisioning to a story; correct the amendment claim. |
| **D4/D5** — axes 1–4 v1; 3+4 as `gating: false` enrichment | **D5 SOUND · D4 RECONSIDER** | The v1/v1.1 gate *split* (D5) is sound. D4's *mechanism* is not: **yes — a non-gating axis that assessed 0 of 40 components is a false green wearing a flag** (T2: the axis feeds no rung, so it is invisible in status and exit code; the coverage flag has no required consumer). The claimed trilemma (gate / false green / `gating: false`) is **false** — the lattice already contains the escape: **`warn`** (exit 0, `verdict.py:42`, with `--warn-as-error` at :47, :98-99 giving strict shops the gate for free). Unknown-on-non-gating-axis feeding a `warn` rung preserves first-run adoption AND keeps the status channel honest; the spec never considers it (spec:90-95). Also: the spec freezes mutually exclusive unknown-semantics in three places (§ 4 item 1), and the conda-beachhead currency claim is unspecced (T5). Fix: route unknown to `warn` (or mandate a coverage banner + per-axis floor), reconcile spec:141/:808/:341-343. |
| **D6** — internal JFrog v1 / public v1.1 behind story 1.7 pins | **RECONSIDER** | The sequencing is fine; the guard is decorative. Story 1.7 as written delivers no pins (epics.md:205-215); no story owns `pixi.toml:32-33`; prd.md:597 (NFR-C1) requires a tested **range**, not a pin, and the osv-scanner range is a still-open item (prd.md:358, :619). Cheap fix: story 0.1 adds the pin/range AC to 1.7 or mints a story owning the run-deps + NFR-C1 range. Until then D6's condition can be "met" while the risk stands. |
| **D7** — TUI + IDE → vision | **SOUND** | spec:513, :840; consistent with prd.md:393's strictly-non-interactive contract; the v1 "polished local client" (spec:510, :844-870) has no TUI dependency. |
| **D8** — `scan --doctor` as a flag | **SOUND** | prd.md:396 freezes "one verb; no interactive subcommands; no prompts ever" — a flag is neither. All spec mentions (spec:115, :510, :840, :866-870) are non-interactive; spec:964 explicitly forecloses `doctor --fix`. `--warn-only` "already specced" confirmed (prd.md:400, :529 = FR23). Residual nit: `--doctor`'s exit-code/output contract against the frozen `{0,1,2,130}` enum is undefined — a 0.1 item, not a violation. |
| **D9/D10** — currency ladder + availability finding | **SOUND-BUT-COSTLY** | The ladder's *shape* is honest — terminal `unknown`, no smuggled staleness in the tiering itself. Three unspecified obligations: (1) the N/N-1 tier's "conda channel data" has no stated offline source on a bare edge machine (spec:441-442, :821-822) — T6; (2) nothing covers **bundled**-data age — the LTS registry is frozen at wheel-build time with no max-age/`max_age_ok` analogue (spec:100-105, :434-438, :685; NFR-S2 covers fetched feeds only, :472-487), which becomes a *gated* stale-green at v1.1 — T4; (3) the D10 ADD/UPDATE finding is realizable only in fleet mode (spec:445-449, :822-829) with no declared edge-mode source or edge-mode emission rule. Fixes: per-mode tier-availability matrix; bundled-registry `snapshot_at` + max-age (and a v1.1 gate precondition on registry freshness); declare ADD/UPDATE fleet-only or name its edge source. |
| **D11** — edge + fleet as "two modes, one identity" | **SOUND-BUT-COSTLY** | The identity mechanism that exists (one producer-agnostic schema + verdict lattice, spec:918-923) is real and cheap. Costs: (1) "two modes" has **no architectural referent inside Warden** — no mode flag, no fleet code path; the CLI additions are exhaustively listed (spec:114-119) and contain no selector; "fleet mode" resolves to *other tools* (`inventory-match --policy`, kedro FR-18 — spec:896, :898, :1036-1040), so "Warden owns edge and fleet" (spec:840) overstates: Warden owns edge + a schema. (2) "Zero data estate" is runtime-true but **provenance-false**: the bundled conda→pypi map is generated from atlas `export-purls` TSVs (spec:934-935) and the LTS registry from the CFE copy curated against atlas views (spec:436-439, :817-819) — edge mode is the estate, freeze-dried. (3) The currency lane re-implements inventory-match's lag/ADD-UPDATE bucketing (spec:444-449 vs `docs/specs/cyclonedx-universe-inventory.md:629-655`) against weaker sources, with the two producers' exit codes currently **inverted** (`{0,1,2}` vs `{0,2,1}`, spec:909-917; cyclonedx spec:964-972). |

## 3 · Findings F1–F7 — verified / refuted

| # | Claim | Verdict | Evidence |
|---|---|---|---|
| **F1** | OD7's `Axis` interface is a phantom; retiring it deletes work | **VERIFIED** (minor precision) | No `Axis` class/protocol exists anywhere — grep matches only `AxisCoverage` (`models.py:254`) and a comment (`interfaces.py:271`); axis is an open string end-to-end (`models.py:31-34`, `Finding.axis:226`, `StatusDriver.axis:213`); `Engine` = name+run (`interfaces.py:167-172`) behind the public `register_engine` seam (`engines.py:48-60`). Precision: "just a new Engine + axis string" undersells three non-interface touchpoints — the hard-coded `_REPORT_AXES` tuple (`report.py:57`; a new axis's coverage claim is **silently dropped** at `report.py:103-113` until edited), the closed finding-ID grammar (`models.py:43-47`), and `DefaultPolicy`'s indeterminate backstop (`interfaces.py:258-269`). |
| **F2** | KEV needs no schema amendment; axes 3+4 do (Finding subset-tested, Component exact-tested) | **VERIFIED-WITH-CORRECTION** | Subset test confirmed (`tests/unit/test_models.py:223-224`); exact-13 Component test confirmed (`test_models.py:195-212`); no `additionalProperties: false` anywhere in `report-schema.json` and additive JSON fields affirmatively pass (`tests/conformance/test_report_schema.py:237-242`). Corrections: "KEV = free" holds only for the bare `kev` boolean — FR-K1 (spec:408-416) also requires `kev_date` (exists **nowhere** in the package) and `epss {score, percentile}` (a **shape-breaking** change to the declared scalar `epss` slot, `models.py:230-231`, `report-schema.json:260-269`). And the Component amendment is more than the test: `_merge_group` (`inventory.py:349-371`) and `_fold_bare` (`inventory.py:415-478`) must define conservative C0 semantics for every new field. |
| **F3** | No Path A — the producer is closed, so axes 3+4 force one gated amendment | **VERIFIED-WITH-CORRECTION** | `ComplianceReport` has only `inventory_count: int` (`models.py:322-336`; schema:104-108); ID regex closed (`models.py:43-47`, schema `anyOf`:232-236). KEV gating needs no shape change (schema already declares `kev`/`epss` on findings). Correction: the absolute "CANNOT ride" is overstated — a **degraded smuggle path exists today**: the `indeterminate:<reason>:<pkg>` family is free-text and axis-free at both layers (`models.py:384-394`, `interfaces.py:29-31`), so `Finding(id="indeterminate:license-denied:<pkg>", axis="license")` + an `AxisCoverage(axis="license")` row constructs and validates now. What genuinely cannot ride: structured per-component data (`spdx_expression`, `lag`, `eol_date`) and positive per-component verdicts. The *conclusion* (one deliberate, gated amendment) stands; the mechanical premise is half-true. |
| **F4** | Live false-green: engines unpinned while pins are cited as the mitigation; 1.7 closes it | **VERIFIED-WITH-CORRECTION** | Unpinned confirmed (`pixi.toml:32-33`); pin-as-mitigation cited in ≥5 spec spots (spec:151-152, :171, :510, :755-759, :1014) + prd.md:177 + architecture.md:17,70. **Correction: story 1.7 does NOT close it** (see D6). Second correction: the spec's own risk register calls the hazard a fleet-wide false-*error* (spec:757-759); the false-green variant needs silent engine output-schema drift — either way the mitigation is unowned. |
| **F5** | The provisioner refusal is right | **REFUSAL-SOUND-BUT-INCOMPLETE** | Premises: mirror transparency TRUE for mirror-mode (`docs/pixi-config-jfrog.example.toml:103-114`) but **overgeneralized** — the same enterprise guide documents direct-channel estates whose committed manifests DO record internal URLs (`docs/enterprise-deployment.md:154-165`, air-gap `file:///` at :81-89), so lock-reading is *conditionally* viable, not hopeless. Routing-in-gitignored-config TRUE (:311-328). Verification-vs-provisioning logic sound for a 20k-existing-repo target; kedro spec already assigns scaffolding to nebi (`cfe-atlas-datapipeline-kedro-migration.md:33, :619-621`). Steelman (strongest): provisioning is the only point where channel provenance is *decidable*; it would discharge OD8/OD2 coverage gaps (spec:801-811, :735-741); the named delegation targets aren't fit today (nebi "alpha", spec:879-882). Incompleteness: the refusal never reconciles its premise with the v1.1 channel-provenance axis it schedules two paragraphs later (see T-b). |
| **F6** | "Zero forward dependencies" void; 6 edges, 2 backward edits; v1 = 28 stories; critical path 0.1→6.1→7.1→7.2→5.2a | **VERIFIED-WITH-CORRECTION** | First, the brief **misquotes** epics.md: line 75's actual text is "dependencies strictly backward (E1 → E2 → E3/E4 → E5)". The edge claim holds — ~6 reshape edges, of which 2 are backward edits into DONE artifacts: (1) 6.1 amends 1.1-frozen schema/model/fixtures (spec:123-135, :685-688 vs epics.md:85,88 "producers, never editors"; `models.py:38` can't even express `2.0.0`); (2) the "1.7 pins" work edits the 1.1-shipped `pixi.toml:32-33` and re-opens DONE 1.4's decision record (epics.md:179). A third edge invalidates a DONE AC's text: epics.md:128 "v1 never populates" KEV vs FR-K1 v1 (spec:83, :119-120, :142). Plus 0.1-before-everything, E2–E5→6.1 numbering inversion, and D8 re-deciding 5.1's open disposition (epics.md:396). **Corrections: the sizing numbers are refuted.** "28 stories" appears nowhere; the spec enumerates **22** (20 baseline + 0.1 + 6.1, spec:163, :522-524) with the axis-3/4 expansion explicitly *unsized* and delegated to 0.1 (spec:520, :524). The claimed critical path is fabricated beyond its first two nodes — **stories 7.1, 7.2, 5.2a do not exist** (grep; epics.md:81 purged letter-suffixed IDs). Honest statement: 22 enumerated (4 done + 18 remaining) + an unsized 0.1-delegated expansion. |
| **F7** | The FR-space crosswalk (b11dd46) is factually right | **VERIFIED-WITH-CORRECTION** | Every asserted crosswalk row confirmed both-sides (canonical rule verbatim at prd.md:484; FR2 row spec:302-303 vs prd.md:500; FR9 row spec:365-380 vs prd.md:509; waivers = FR24–26 at prd.md:531-534; kedro FR-15..18 at kedro:619/:623/:627/:631; the mixed-space sentence spec:327 correctly qualified). The two crosswalks (spec:278-282 vs prd.md:484-496) agree — the spec's is illustrative, not exhaustive, which is the gap. Corrections: **7 bare working-label FR references sit outside the note's scoped section and remain colliding** — spec:263 & :1049 `FR8` (should be canonical FR27), :577 `FR6` (→FR14), :700 `FR7` (→FR17), :767 `FR5` (→FR18), :771 `FR9`/`FR10` (→FR24/FR21), :982 `FR4/FR6`; and one content mislabel: spec:363 attributes CycloneDX *normalization* to kedro FR-17 when normalization is kedro **FR-13** (kedro:611-613; FR-17 merely extends it; prd.md:45 repeats the error). Cheap fix: one pointer line to prd.md:486's full map + the FR-13 correction. |

## 4 · Surviving self-contradictions & spec↔deck disagreements

**Internal to the spec:**
1. **Three-way contradiction on the spec's own frozen invariant (unknown-semantics).**
   spec:141 — callout #3, "FROZEN — do not regress", *inside the winning Reconciliation note* —
   says "Unproven license/currency … route to `indeterminate` → non-zero, **never** a silent 0";
   spec:341-343/:405-406 say v1 unknown license/currency is "a reported `unknown`, not
   `indeterminate`" (silent 0); OD8 spec:808-809 still carries the pre-D4 semantic
   ("`unknown` → `indeterminate` … never a silent `allowed`"). Three mutually exclusive
   behaviors, two of them inside sections that claim precedence. NFR4 (spec:469-471, "a
   partial-coverage run never masquerades as a complete clean") is violated by the middle one
   in the exit-code channel. This is the root of T2.
2. **spec:775 vs spec:142/:840/:408-416** — OD6's supersession bracket still says "v1 default
   blocks on CVSS-critical only (KEV deferred)", flatly contradicting D3's KEV-in-v1. Only the
   precedence rule rescues it; a dev agent reading OD6 in isolation ships the wrong gate.
3. **FR-L1 findings vs § Report architecture sections** (spec:422-425 vs :678-688) — per-component
   license *findings* and top-level `license`/`currency` *sections* are two different amendment
   shapes; story 6.1's wording matches only the sections variant. 0.1 must pick one. (Related
   unresolved: if unknown-license emits a report `Finding`, the shipped C0c backstop
   (`interfaces.py:258-269`) would drag it to `indeterminate` — colliding with spec:341-343's
   exemption; if it doesn't, "finding" at spec:422 means something the schema doesn't define.)
4. **spec:131 cites `validate_report.py` — the file does not exist** (glob over the package;
   runtime self-validation lives at `report.py:130-143`). The 6.1 task list edits a phantom.
5. **The provisioner-refusal paragraph vs the v1.1 channel-provenance axis** (spec:954-967 vs
   :964, :511) — the refusal's transparency premise indicts the axis it schedules (T-b).

**Spec ↔ planning artifacts (beyond the known two-engine drift):**
6. **DEP001 gate default** — spec FR5 "high/med/low + **all hygiene** warn" (spec:330-331, :142)
   vs epics.md:38 + story 1.6 AC (epics.md:201) "**DEP001 blocks by default**". Obeying the
   winning note demotes DEP001 and silently regresses a roundtable decision.
7. **"Story 1.7 pins"** — the spec's repeated gate condition names a story whose epics.md content
   (typed errors, epics.md:205-215) contains no pins, while NFR-C1 (prd.md:597) says range-not-pin.
8. **Exit-code inversion** with the schema's second producer: Warden `{0,1,2}` vs
   `inventory-match --policy` `{0,2,1}` (spec:909-917; `cyclonedx-universe-inventory.md:964-972`)
   — acknowledged in the spec as deferred debt, still a live cross-producer trap.

**Spec ↔ deck ↔ infographic:** the three canonical axis tables **agree** on the axis set and
gating split (spec:80-88 ↔ deck:327-334 ↔ infographic:80-89: axes 1+2 gate v1 incl. KEV; 3+4
enrich v1 / gate v1.1; EPSS v1.1; perimeter v2; 5+6 vision). The disagreements are in examples
and status columns:
9. **deck:129** (slide 05 JSON) shows `"license": "indeterminate"` feeding the verdict — v1.1
   semantics; contradicts spec:341-343/:405-406 (v1 unknown license never produces
   `indeterminate`). Same defect at **deck:302** (a `Warden 1.0` run rendering
   `license 2 unknown — indeterminate`) — the deck sells v1.1 behavior as the v1 product story,
   which is direct evidence T2's invisibility contradicts the product narrative.
10. **deck:385** (slide 19 CI view) renders `EPSS 0.83` on a finding — EPSS surfaces v1.1
    (spec:679, :834); also internally inconsistent with deck:345 (EPSS listed v1.1).
11. **infographic:161** — consumption edge "(today) … the **six axes**" (and present-tense "six
    axes" at infographic:33) vs spec:80-88 (v1 = four) and deck:247 ("the four axes").
12. **infographic:319** — CISA KEV status "**Candidate**", contradicting spec:120/:840 (v1 gate)
    and the infographic's own :83/:131. Same column defect: **infographic:321-322**
    (`license-expression`, conda `about:` + `importlib.metadata` = "Candidate" vs spec FR-L1 v1,
    :417-425) and **infographic:324** (`endoflife.date` = "Planned" vs a v1 currency-ladder tier,
    spec:85, :439-441).
13. **Infographic:183 `coverage-flagged`** — names a Path B outcome that is not one of the 7
    frozen Status rungs (`models.py:53-66`) and appears nowhere in the spec.
14. **Infographic:43 "5 epics · 20 stories"** — stale against the spec's 22 enumerated + 0.1-owned
    expansion (spec:522-524).
15. **Infographic:133 typed errors** — lists 4 of the code's 9 `ErrorKind` tokens and uses
    "engine-crash", which is spec prose (spec:389) but not a code token
    (`engine-execution-failed`, `models.py:69-80`).

## 5 · What's missing

**Infographic → spec gaps (features the deck promises that no spec owns):**

| Infographic item | Where | Spec status |
|---|---|---|
| Automated fix PRs (v1.1 "NOW") | infographic:216 | 0 hits. Backlog's "Auto-fix mode" (spec:1053) is a different feature and excluded per NFR3 |
| Baseline & grandfathering (v1.1 "NOW") | infographic:216 | Probably = spec:511 "**corpus ratchet**" — a term the spec never defines; prd.md:547 defers the baseline ratchet to Growth. Naming mismatch + tier disagreement + undefined |
| Vendor-support backlog (v2) | infographic:226 | Absent from the v2 row (spec:512) |
| Typosquat / name-squat detection | infographic:159, :231 | Vision row (spec:513) has only generic "malicious-package detection" |
| Alternate-library suggestions | infographic:232 | 0 hits (spec:1041 "alternate hygiene backends" is different) |
| Public-upstream ring → blocklists | infographic:159-163 | Deck-pointer only (spec:518); no upstream-scan feature or blocklist output specced |
| Standards: SARIF · OpenVEX/CSAF · `vers` · PEP 740 · in-toto/GUAC | infographic:339 | All 0 hits; PRD defers SARIF post-v1 (prd.md:547). The deck presents them as standards Warden "speaks" — overpromise |

The entire Part IV (control plane ~40 capabilities, OSPO section, 8 leader scorecards, ~40-tool
integration surface incl. Basilisk/uv/VulnerableCode/EUVD/Trivy/Grype/pip-audit/Capslock/
osv-scalibr/cdxgen/Syft/ORT/ClearlyDefined/Repology/GuardDog/Renovate/Allstar/Dependency-Track/
DefectDojo and the SCA-consumer list) has **zero spec presence**. This refutes D1's bloat premise
— but it also means the infographic is the only artifact recording those commitments; any that
are real intent are unowned.

**Unstated obligations / unverified claims / unsized stories:**
- No story owns replacing `pixi.toml:32-33`'s `"*"` with NFR-C1 ranges (D6/F4) — the single
  cheapest high-value fix for story 0.1.
- `scan --doctor` has no exit-code/output contract against the frozen `{0,1,2,130}` enum (D8 nit).
- FR-K1's `kev_date` field exists nowhere in the package; its `epss {score, percentile}` object
  contradicts the shipped scalar slot — story 6.1's amendment list names neither (F2).
- `validate_report.py` (spec:131) is a phantom edit target (contradiction #3).
- The conda-beachhead license claim and the axis-3/4 story expansion are 0.1-delegated and
  unsized (F6); the honest v1 count today is 22 enumerated stories, not 20 or 28.
- **KEV feed lifecycle is entirely unowned**: no cache location, lifecycle, age policy, or
  provisioning story (spec:862-866 covers OSV only); no absent-vs-stale distinction; no per-feed
  KEV provenance in the report (spec:920-923 covers the OSV source only) — T1/T7.
- **Bundled-data age is a policy hole**: NFR-S2 covers fetched feeds only; the bundled LTS
  registry and conda→pypi map carry `snapshot_at` at best and no `max_age_ok` analogue
  (spec:685 vs `models.py:187-205`) — T4.
- **No per-mode data-source matrix for the currency ladder**: which tiers are live in edge vs
  fleet mode, and what the ADD/UPDATE finding emits (or omits) in edge mode, is unstated — T6.
- **`--fail-under-coverage` never made it into the spec** (grep: zero hits) despite prd.md:548
  shipping it v1 (default OFF) — and its default-OFF rationale (prd.md:525) was invalidated by
  D4 for non-gating axes. It is the natural required-consumer for T2's coverage honesty.

**Brief defects found while verifying (meta):** the brief misquotes epics.md:75; its "28 stories"
figure and its 0.1→6.1→7.1→7.2→5.2a critical path are unsupported by any artifact (stories
7.1/7.2/5.2a do not exist).

---

*CFE note: this review touched no `recipes/` or engine code; the CFE Rules 1&2 retro obligation
remains attached to the implementation effort and is correctly recorded at spec:985-989 — the
"no CHANGELOG entries" claim was verified literally true (grep of the CFE CHANGELOG: zero hits
for deptry / osv-scanner).*
