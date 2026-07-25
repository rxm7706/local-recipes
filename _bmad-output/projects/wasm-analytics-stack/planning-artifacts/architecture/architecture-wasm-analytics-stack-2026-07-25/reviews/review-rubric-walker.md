# Rubric Walker — Architecture Spine Review

**Spine:** `ARCHITECTURE-SPINE.md` (Wasm Analytics Stack, status: `final`, 2026-07-25)
**Sources cross-checked:** `prd.md` (17 FRs), `technical-python-in-wasm-analytics-research-2026-07-25.md`
**Deterministic pre-pass:** `lint_spine.py` → `{"ok": true, "total_findings": 0}` — no placeholders, no duplicate AD IDs, no missing Binds/Prevents/Rule, no unpinned Stack versions. All mechanical checks clean; everything below is a semantic finding.

**Overall verdict:** Solid, well-scoped spine with full PRD coverage and mostly-enforceable ADs, but it carries two internal Capability-Map/AD inconsistencies and at least one live architectural fork (sync vs. async validation) that a `status: final` document should not still be carrying.

---

## 1. Does it fix the real divergence points for the level below, and miss none?

Mostly yes — the 8 ADs cover the highest-value forks the technical research explicitly surfaced (WIT boundary shape, dependency denylist, no-WASI-for-DuckDB, gate hollowness, trace-ID uniqueness, securityContext parity, single-writer serialization, air-gap fetch). Three real misses:

- **Sync vs. async validation execution model is undecided.** FR-1's consequence says the upload "returns a tracking/trace ID the client can use to poll validation status" (PRD line 222-223) — implying an async job + polling model. UJ-1's narrative ("Marcus sees a precise, row-level error message within seconds") and the spine's Mermaid flow (`Invariants & Rules`, lines 49-65) both depict a flat synchronous pipeline with no queue, job store, or status endpoint. No AD, Consistency Convention, or Deferred entry resolves this. It is a genuine fork: the FastAPI-upload-handler story and the frontend-polling-UI story would independently guess opposite models. This should have been an AD (or at minimum an explicit Deferred/Open-Question entry) — it currently is neither.
- **The FR-3 partial-acceptance/queuing mechanism is architecturally silent.** FR-3's consequence ("valid rows... queued for ingestion (FR-4) independently of the rejected rows' resolution") implies server-side state that survives between a partial-failure upload and the user's corrective re-upload. Consistency Conventions (line 168) decides the *shape* of a validation-failure record (`{row_index, column, rule, message}`) but not *where valid rows live while rejected rows await correction*, nor how a corrective re-upload is correlated back to the original partial batch. Two builders could diverge: one ingests the valid subset immediately and treats resubmission as a wholly new upload; another holds a server-side staging buffer keyed by the original trace ID. Not covered by any AD, and not in Deferred.
- **AD-7's "sequenced pipeline trigger" names no concrete mechanism** (see § 2 below) — this is really an enforceability gap, but it doubles as a missed divergence point: PRD FR-5 itself says transform runs "on a defined schedule/trigger" (ambiguous between event-driven-per-upload and periodic-batch), and the spine never resolves which. A story building "trigger dbt after dlt" and a story building "nightly dbt schedule" would produce genuinely incompatible transform-stage designs.

Everything else — OIDC provider choice, exact file-size/latency budgets, named regulatory framework, operational SLA, CI trigger scope, data retention, `dbt Fusion`, browser dashboard — is correctly identified as non-divergent (implementation parameters or out-of-scope) and appropriately left to Deferred or the PRD's own Open Questions.

## 2. Is every AD's Rule enforceable and does it actually prevent its stated divergence?

Walked all 8:

- **AD-1** (WIT boundary data shape) — enforceable in principle (a WIT interface file is reviewable, and its type system itself resists ambient buffer types), but unlike AD-2/AD-4 it names no mechanical check. Low risk given WIT diffs are inherently visible, but worth noting it's the only "shape" AD without a build-time or CI check backing it.
- **AD-2** (dependency denylist) — the four explicitly named packages (`numpy`, `pandas`, `pyarrow`, `pydantic`) are mechanically checkable by a static-import-scan. The Rule's trailing clause, **"or any other C-extension-backed or `componentize-py`-unproven package,"** is not mechanically checkable as written — a static scanner can enforce an explicit list, not an open-ended semantic category ("is this dependency's build closure C-extension-backed?"). As currently worded the Rule promises more than the described gate can deliver. Fix: either enumerate the denylist as a maintained file the scanner reads, or drop the open-ended clause and rely on review for anything not on the list.
- **AD-3** (no WASI for dlt/dbt-duckdb/DuckDB) — enforceable as a governance rule (ADR-amendment gate on any `wasm32-wasi` build-target declaration); appropriately process-level given it's a negative/rare-path constraint, not something worth automating pre-emptively.
- **AD-4** (non-hollow isolation gate) — well-specified and enforceable: it requires a concrete meta-test (widen capabilities → gate must fail) shipped from v1, matching PRD SM-2 exactly. Strongest AD in the set.
- **AD-5** (one trace-ID field) — fully enforceable: names the exact field (`upload_trace_id`), the exact propagation mechanism per stage (`dlt` load-package metadata, `dbt --vars`, OL parent-run facet). Testable via a single lineage-lookup assertion.
- **AD-6** (one securityContext, two consumers) — enforceable by construction if the described "generation step" exists (a CI diff-check between generated Helm values and Podman compose would trivially catch drift), but the Rule doesn't itself mandate that check — it only mandates the single source of truth. Reasonable; the structural precondition for automated drift-detection is there even if the check isn't spelled out.
- **AD-7** (DuckDB single-writer serialization) — **the weakest AD in the set.** The Rule states the invariant ("no scheduling path may invoke `dbt run` concurrently with an in-progress `dlt` load") but names no concrete mechanism: no lock, no atomic hand-off, no single invoking script/orchestrator, and — unlike AD-4 — no gate that would catch a violation before it corrupts the DuckDB file. Given DuckDB corruption is the stated failure mode and this AD is the primary defense against it, "sequenced pipeline trigger" is too vague to prevent two independently-built scheduling paths (e.g., a naive cron-triggered `dbt run` racing an in-flight `dlt` load) from violating it undetected. This also compounds with the § 1 finding about FR-5's undecided schedule-vs-event-trigger model — the ambiguity is in both what triggers transform and how concurrency is prevented.
- **AD-8** (air-gap-routable fetch) — enforceable in principle (a grep-for-known-public-URLs check, analogous to AD-2's scan, would catch violations) but, like AD-1, is stated as a review-time rule rather than a named build gate — inconsistent rigor next to AD-2/AD-4's explicit build-gate framing, for a constraint (air-gap posture) the repo treats as load-bearing elsewhere.

## 3. Is anything under Deferred incorrectly deferred (could let two units diverge incompatibly)?

Reviewed all 10 Deferred bullets. Nine are legitimate: OIDC provider, exact latency/size budget, named regulatory framework, operational SLA/RTO-RPO, CI trigger scope, data retention policy, Marquez's exact deployed image, `dbt Fusion` migration, browser dashboard — none of these produce an incompatible build artifact if two units guess differently; they're parameters, policy, or out-of-scope items.

One is a plausible miscall:

- **"`componentize-py`'s runtime-import restriction's effect on validation-rule configuration"** (mirrors PRD § 8 Q3) is deferred to "the story that first hits it," with no default steer. But this isn't a one-off — it's the shape of *every* FR-2/FR-3 story, since each new validation rule added to `apps/validate-component/` runs into the same build-time-only-import constraint the technical research documents (componentize-py issue #23). Deferring it per-story risks each rule-adding story inventing its own registration pattern (a hardcoded if/elif chain vs. a "pluggable" rule registry that inadvertently needs runtime dispatch, violating AD-1/AD-2's own constraints). A one-line default in an AD or Consistency Convention — e.g., "validation rules are statically enumerated Python functions in one module; no dynamic dispatch" — would have cost little and closed this off. Recommend upgrading this from Deferred to a 9th AD (or folding a one-sentence default into AD-2), rather than leaving it purely reactive.

## 4. Is named tech (Stack table) verified-current, not asserted from stale training-data memory?

Better than most specs, but uneven in depth. The table (lines 171-189) carries a dated methodology comment: *"Verified 2026-07-25 via PyPI JSON API + GitHub Releases API (WebSearch was unavailable this session...)"* — this is good practice (date + method + honest caveat about the degraded research mode), and `lint_spine.py`'s "unpinned Stack versions" check passes clean (every row has a concrete version).

However:
- Only **2 of 12 rows** trace to a citation actually present in the supplied source material: Wasmtime `47.0.1` and `componentize-py 0.25.0` both align with dated, sourced claims in the technical-research doc (wasmtime 47.0.0 released 2026-07-20 per its RELEASES.md; componentize-py releases through 0.25.0 on 2026-07-07, both § 1/§ 2 of the research report, with primary-source links in its Sources section).
- The remaining rows (Python, FastAPI, `dlt`, `dbt-core`, `dbt-duckdb`, DuckDB, `opentelemetry-sdk`, `openlineage-python`, Vector, Pixi) have **no per-row source or independent corroboration anywhere in the provided documents** — their only evidence is the single blanket comment covering all 12 heterogeneous packages at once.
- The **Marquez row is the exemplar the rest of the table should match**: it doesn't just assert a version, it explains *why* the number is ambiguous ("last tagged release 0.50.0 (2024-10-24); repo actively pushed 2026-07-23 — Marquez ships primarily via Docker/Maven, not GitHub release tags"), flags the risk, and explicitly punts the real answer to Deferred/implementation time. That's the verification standard the checklist is asking for; it's present in exactly one row out of twelve.

Recommend either per-row footnotes/links (like the research doc's Sources section) or, at minimum, acknowledging in the Stack section which rows got a direct check vs. which inherit the blanket claim only.

## 5. Does the spine cover the PRD's 17 FRs (Capability → Architecture Map)?

**Coverage is complete** — all of FR-1 through FR-17 appear exactly once across the seven Capability → Architecture Map rows (1 + 2 + 1 + 3 + 4 + 2 + 4 = 17). No FR is missing from the map.

However, the map's **"Governed by" column is internally inconsistent with the ADs' own `Binds:` declarations** in two places:

- **FR-1** row (line 235) lists only "Consistency Conventions (auth)" as governance — but **AD-1's own header explicitly states `Binds: FR-1, FR-2`** (line 74), and AD-1's Rule directly constrains FR-1's territory (the FastAPI upload endpoint must parse Excel bytes into rows *before* the WIT call — a requirement on the upload handler, not just the validate component). AD-1 is correctly cited on the FR-2/FR-3 row but dropped from FR-1's own row.
- **FR-17** row (line 241, bundled with FR-14/15/16) lists "AD-6, AD-8, Deployment & Environments" — but **AD-7's own header explicitly states `Binds: FR-4, FR-5, FR-17`** (line 142), and AD-7 is correctly cited on both the FR-4 row and the FR-5/6/7 row, yet is absent from FR-17's row despite being named in AD-7's own frontmatter as binding it.

Both are the same defect pattern: an AD's self-declared `Binds:` list is the more authoritative statement, and the Map silently drops it for one of the two-or-more FRs each AD binds. A builder cross-referencing "what governs FR-17 (storage)" via the Map alone — without independently re-reading every AD's Binds line — would miss AD-7's single-writer serialization constraint entirely, which is exactly the kind of miss that causes real DuckDB corruption.

A related, softer accuracy issue: the **FR-8/9/10/11 row cites only AD-5** as governance, but AD-5 is scoped to the trace-ID field (its own Binds line: `FR-8, FR-9, FR-10` — correctly excludes FR-11). FR-11's actual testable claim ("no pipeline container other than Vector sidecar holds external network egress") has no AD backing it at all — see § 6 below.

## 6. Is every structural dimension the "feature" altitude owns decided, deferred, or an open question?

The spine explicitly names the dimension the rubric warns is most often skipped — **Deployment & Environments is present as its own section** (lines 207-229), with a Mermaid diagram spanning local dev / Podman twin / OCP, and infra/provider strategy is decided (OpenShift + Restricted SCC + GitOps/Helm, Podman for the twin). **Operations** (SLA, on-call, RTO/RPO) is explicitly deferred with a named rationale, not silently missing. This is the correct outcome for the specific failure mode the checklist calls out — good.

One dimension-shaped gap remains:

- **Runtime network-egress enforcement for FR-11** is asserted ("no pipeline container process other than the Vector sidecar holds an external network egress path for telemetry") but never resolved into an architectural decision. There is no AD analogous to AD-4's isolation-gate pattern for this claim (e.g., a NetworkPolicy, an egress-scan gate), no Consistency Convention, and no Deferred/Open-Question entry acknowledging it's unresolved. It sits in a gap between "decided" and "explicitly deferred" — it's simply unaddressed. Given FR-11 is bundled into the same Capability-Map row as FR-8/9/10 (all under AD-5, which doesn't cover it — see § 5), this looks like it fell through a genuine seam between the observability ADs and the deployment/security ADs, rather than a deliberate scoping call.

No other whole dimension is silent: data/naming conventions, error-shape conventions, auth boundary, and storage-persistence contract (PVC, mount-path parity) are all decided in Consistency Conventions or Deployment & Environments.

*(Two items from the full BMAD reviewer-gate checklist not in this task's requested six are not applicable here: "ratifies rather than contradicts a brownfield codebase" — this is a greenfield project, no existing codebase to ratify against; "no new AD weakens an inherited parent-spine AD" — frontmatter `companions: []`, no parent spine.)*

---

## Summary of Findings (severity-tagged)

1. **High** — Sync-vs-async validation/upload execution model is a live, unresolved fork (FR-1's "poll validation status" vs. the spine's synchronous Mermaid flow); no AD, Convention, or Deferred entry addresses it. (§ 1)
2. **Medium-High** — Capability → Architecture Map omits AD-1 from FR-1's row and AD-7 from FR-17's row, despite both ADs' own `Binds:` lines explicitly naming those FRs — internally inconsistent with the ADs themselves, and the FR-17/AD-7 gap hides the single-writer serialization constraint from anyone building storage off the Map alone. (§ 5)
3. **Medium-High** — AD-7's Rule ("sequenced pipeline trigger") names no concrete enforcement mechanism and no gate (unlike AD-4's meta-test), despite protecting against DuckDB file corruption — the highest-consequence failure mode in the whole spine. Compounds with FR-5's undecided schedule-vs-event trigger model. (§ 2)
4. **Medium** — FR-3's partial-acceptance/queuing mechanism (where do valid rows live while rejected rows await correction, how does resubmission correlate back) is architecturally silent — decided nowhere. (§ 1)
5. **Medium** — FR-11's "Vector-only egress" claim has no backing AD, Convention, or Deferred entry; the Map incorrectly attributes its governance to AD-5, which doesn't address it. (§ 5, § 6)
6. **Medium** — Stack table's verification evidence is uneven: only 2 of 12 rows (Wasmtime, componentize-py) trace to citations actually present in the supplied research; the other 10 rest solely on one blanket comment. The Marquez row (explicit tag-staleness caveat) is the standard the rest should meet. (§ 4)
7. **Low-Medium** — AD-2's Rule's trailing "or any other C-extension-backed or componentize-py-unproven package" clause is not mechanically checkable by the described static-import-scan as written. (§ 2)
8. **Low** — Deferring the validation-rule-configuration pattern (componentize-py's build-time-import constraint) to "the story that first hits it" risks incompatible per-story rule-registration designs within one shared component; a one-line default would have closed this cheaply. (§ 3)
