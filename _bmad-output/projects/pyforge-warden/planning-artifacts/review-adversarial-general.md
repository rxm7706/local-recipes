# Adversarial Review — pyforge-warden PRD (Reviewer Gate)

**Reviewed:** `_bmad-output/projects/pyforge-warden/planning-artifacts/prd.md` (post-24-gap-fix state, 2026-07-16)
**Against:** `docs/specs/pyforge-warden.md` (sole source of truth; D12 2026-07-16)
**Reviewer:** adversarial-general
**Date:** 2026-07-16

**Verdict: NOT CLEAN.** The 24-gap fix pass patched the headline surfaces (Exec Summary, FR block, CLI section, D12 callouts) but left live, unmarked contradictions in exactly the places a dev team reads to build and test: Technical Success still ships the pre-D3 KEV deferral as live text, the Architecture-open-questions section still tells the architect to decide — and recommends *reversing* — an owner-confirmed gate default that FR18 states as binding, and the D12 re-tier edited a list's preamble while leaving the retired item ("EPSS") sitting at the end of that same list. Two of these produce *different exit-code state machines* depending on which paragraph the reader trusts. 16 findings: 2 critical, 3 high, 5 medium, 6 low.

Method note: deliberately-marked history (the frontmatter `prioritizedRefinements` block, the `🚩 SUPERSEDED by D3+D12` domain callout, the FR-crosswalk-covered working labels) is **not** re-reported except where a marked block is load-bearing for live text.

---

## CRITICAL

### C1 — Technical Success still ships the reversed KEV deferral as live, unmarked text — and cites a section that now says the opposite

- **Location:** § Success Criteria → Technical Success, "Honest contract + severity gate" bullet (~line 144).
- **Quote:** "**severity-tiered exit 0/1/2** (default block on **critical CVE**; the KEV tier is **deferred post-v1**, KEV surfaced as an annotation only — see § Domain-Specific Requirements)"
- **Why it burns:** This is the *success criteria* — the section QA writes acceptance tests from. It states the pre-D3 world (KEV deferred, annotation-only) with no superseded marker, while FR18/FR36, the Exec Summary ("with the CISA-KEV + EPSS gates"), the D12 header callout, and the spec (D3 2026-07-15, D12 2026-07-16) all make `--fail-on-kev` part of the **v1 default gate**. Worse: the parenthetical says "see § Domain-Specific Requirements" — and that section (Severity taxonomy, ~line 343: "CISA KEV gates in v1 (`--fail-on-kev`, FR36)") now asserts the exact opposite, so the cross-reference launders a dead decision as if the target section backed it. A team splitting work by section builds two different default gates and both have a PRD sentence to point at.
- **Fix:** Rewrite the bullet to the D12 state: "default block on critical CVE **and** any CISA-KEV-listed advisory (`--fail-on-kev` in the FR18 default); `--min-epss` optional (FR36)." Delete the deferral parenthetical entirely — do not mark it superseded in place; success criteria must carry zero dead text.
- **Aggravator (see L5):** frontmatter `v1_must` line 39 carries the same "(KEV tier deferred post-v1 — see § Domain-Specific Requirements)" pointer. It *is* covered by the replan-note "historical intake labels" marker, but the pointer into a live section that says the reverse compounds C1's trap.

### C2 — Gap A is simultaneously "owner-decided and binding" (FR18) and "open, blocking, architect must decide" — with the open-question recommending the OPPOSITE outcome

- **Location:** § Architecture Open Questions (consolidated) → "Open — architect must decide (blocking items first)", item 1 (~line 646); vs § Functional Requirements FR18 (~line 539); vs the 2026-07-11 reconciliation callout #3 (~line 80, marked "authoritative").
- **Quote (open question):** "**[Gap A — sharpest] deptry-severity → verdict-lattice mapping.** … decide whether a hygiene finding can reach `policy-violation`/exit-1 or is capped at `warn`. … *Recommended default for the architect to confirm: hygiene is a **separate `warn`-axis**, not an input to the severity gate.*"
- **Quote (FR18, binding):** "the **hygiene axis is separate** — **DEP001 (missing dependency) blocks by default** (gated on conda↔pypi name-mapping confidence: high-confidence → block, ambiguous → `warn`), DEP002–005 → `warn`."
- **Why it burns:** The spec records this as **owner-confirmed 2026-07-15** ("DEP001 missing-dependency blocks by default … owner-confirmed 2026-07-15, aligning this spec to epics story 1.6"). FR18 states it as canonical and binding. Yet the consolidated open-questions section — the explicit hand-off contract to the architecture phase, whose own preamble separates "resolved, do not relitigate" from "genuinely open" — still ranks this the *sharpest blocking open decision* and recommends the architect confirm **hygiene capped at `warn`**, i.e. DEP001 never blocks. The section itself says "the two models yield **different exit-code state machines**." An architect following the PRD's hand-off list will re-decide (and per the recommendation, reverse) an owner decision, and FR20's verdict composition — the product's spine — sits directly on top of it. This is a decision stated twice with different outcomes, in the two sections most likely to be read by different people.
- **Fix:** Move Gap A out of "Open — architect must decide" into "Resolved v1 assumptions (recorded — do not relitigate)" with the FR18/owner-confirmed wording; delete the "recommended default" sentence. If any residue is genuinely open (e.g., the exact confidence-tier thresholds for the DEP001 block), state *only that residue* as the open question.

---

## HIGH

### H1 — EPSS still sits in the deferred list whose own preamble says EPSS left the list

- **Location:** § Project Scoping → "Nice-to-Have / Deferred to post-v1" (~line 484).
- **Quote:** "**Nice-to-Have / Deferred to post-v1** *(as re-tiered by D12 — KEV, **EPSS**, the axis gates, baseline & grandfathering, and fix PRs **moved INTO v1 and left this list**):* SARIF output … · better conda↔PyPI reconciliation · **EPSS**."
- **Why it burns:** The D12 fix edited the parenthetical but not the list body — the sentence announces EPSS's departure and then the list closes with "· EPSS". This is a contradiction *introduced by* the gap-fix pass, inside a single sentence-plus-list unit. A scoping/sprint-planning reader scanning the bullet list (not the italic preamble) de-scopes `--min-epss` and story 6.7 out of v1, in direct contradiction of FR36, D12, the Release map, and the spec's v1 DoD ("`--fail-on-kev` and `--min-epss` block").
- **Fix:** Delete the trailing "· EPSS" token. Then re-audit the whole list against the D12 preamble (the rest checks out: SARIF, cf_atlas promotion, P6/J7, waiver-at-scale, per-section severity, coverage-floor default, deprecation machinery, SBOM freeze, alternate backends, fleet parallelism, name reconciliation).

### H2 — Stale vulnerability DB: the PRD specifies three mutually exclusive outcomes (warn/exit-0 vs. ambiguous "degrade" vs. fail-loud/non-zero) and C0 makes one of them a mandatory test failure

- **Location:** § Domain-Specific Requirements → Technical Constraints (~line 348) vs FR12 (~line 529) vs NFR-S8 (~line 612) vs C0 (~line 595).
- **Quotes:**
  - Domain: "a **staleness warning is mandatory in offline mode** (warn if the DB is older than a configurable N days). This is what converts a stale-DB false-green into a loud **`warn`**." — `warn` is exit **0** in the frozen lattice.
  - FR12: "detect a **stale** vulnerability database … and **degrade the verdict / emit a typed staleness signal**" — degrade *to what rung* is unstated.
  - NFR-S8: "a stale/empty/swapped/unverifiable DB → **fail-loud, never green**" — non-zero.
  - C0: "an enumerated adversarial-fixture corpus → **0 fixtures emit exit-0**, covering: **stale**/empty/swapped DB …"
- **Why it burns:** These cannot all be implemented. If a stale DB yields `warn` (exit 0) per the Domain section, the C0 stale-DB fixture *must* fail its own acceptance metric ("0 fixtures emit exit-0"). NFR-S9 shows the post-triad intent for the bundled twin (stale + gated → `indeterminate`), and the 2026-07-12 correction pass fixed the analogous offline-DB-unreachable cell ("skipped routes to `indeterminate` → exit 1") — but missed this Domain paragraph, which still carries the pre-`indeterminate` "loud warn" answer. Untestable as written; the team that implements the Domain sentence ships a false-green the NFR suite is required to catch.
- **Fix:** Rewrite the Domain constraint to the triad-era rule and pin FR12's rung: stale DB **under an active vuln gate → `indeterminate` (exit 1)** with typed staleness provenance; `--warn-only` downgrades as everywhere else. Add the "(Corrected — predated `indeterminate`)" marker the sibling cells got.

### H3 — "vuln-side waiver" is deferred to Growth while the PRD's flagship v1 journey (J4) is a vuln waiver

- **Location:** § Growth Features (~line 167: "vuln-side waiver") vs Journey 4 (~lines 234–242) vs FR24 (~line 547) vs § Complete Feature Set (~line 472: "Core journeys supported in v1: … J4 (bypass loop)").
- **Quote (J4):** "osv flags a `high` CVE with no upstream fix. … She runs `... --bypass --reason "no upstream fix; tracking GHSA-xxxx"`. … While a matching waiver is non-expired the gate exits 0 with `status: bypassed`…"
- **Why it burns:** FR24 grants a waiver for "a finding" (unqualified); J4 — a committed v1 journey — waives an **osv security finding**; yet Growth defers "vuln-side waiver" to v1.x. Read plainly, v1 either can or cannot waive a CVE, and the PRD says both. The phrase is inherited from the spec's v1.x row ("PRD Growth carry-overs: vuln-side waiver …") and plausibly means something narrower (e.g., waiver semantics *inside* the osv engine layer, or per-advisory waiver formats native to osv-scanner) — but the PRD never defines it, and an implementer who takes the Growth row at face value guts J4, FR24's primary use case, and the anti-metric chain (line 138 counts "an auditable expiring bypass exists (FR24)" as a v1 proxy).
- **Fix:** Define the term where it's deferred, e.g. "vuln-side waiver = engine-native (osv-scanner-level) suppression files; the FR24 `.warden-waivers.yaml` mechanism covers findings on **all** axes, including security, in v1" — or delete the Growth entry if FR24 fully subsumes it.

---

## MEDIUM

### M1 — Journey 1's bolded payoff still renders "`clean at 60% coverage`", which FR16 explicitly outlaws — and its "Reveals" footer still states the retired "warn-not-clean" invariant

- **Location:** Journey 1 climax (~line 198) + J1 *Reveals* (~line 202) vs FR16 (~line 535).
- **Quote (J1):** "it renders **`clean at 60% coverage`** … Critically: **the unresolved 40% routes to `indeterminate` … — the run exits non-zero by design**"; *Reveals:* "the `warn`-not-`clean` invariant on partial coverage".
- **Quote (FR16):** "*(The earlier "clean at N%" phrasing predated `indeterminate` — corrected 2026-07-12.)*"
- **Why it burns:** FR16's correction note names *this exact phrasing* as corrected — but it was only corrected in FR16, not at its origin. The J1 paragraph now asserts a report whose status token is `clean` *and* whose exit is non-zero via `indeterminate` — internally impossible under FR20 (one status, one exit, status governs). The trailing "(Corrected 2026-07-12…)" note in J1 targets the old "warn at minimum" phrase, so a reader reasonably concludes the bolded `clean at 60%` render survived the correction and implements the human-summary line accordingly. The stale Reveals footer ("warn-not-clean") then contradicts the corrected climax two lines above it.
- **Fix:** Change the bolded render to "**`indeterminate` at 60% coverage`**" (or "a coverage-qualified `indeterminate`"), and fix the Reveals to "the `indeterminate`-not-`clean` invariant on partial coverage."

### M2 — `--require-full-coverage` ships in the frozen v1 CLI contract with no surviving defined behavior

- **Location:** CLI § Command Structure (~line 409: "promotes any `skipped` dimension to a failing verdict") vs State-Machine (~line 445: "`--require-full-coverage` is **subsumed on this path**") vs Traceability (~line 580: "the `--fail-under-coverage` / `--require-full-coverage` flags ship v1, off").
- **Why it burns:** Post-triad, a `skipped` dimension *already* routes to `indeterminate` → exit 1 by default — the flag's one documented behavior is now the default behavior. The PRD both ships the flag in v1 and admits it's subsumed, without ever restating what it does when set. FR19 was repurposed with new residual roles for `--fail-under-coverage`; `--require-full-coverage` got no such repurposing. Devs will either implement a no-op flag in a *frozen* public contract (a removal later is a breaking change per the PRD's own INPUT-contract rules) or invent semantics.
- **Fix:** Either delete the flag from v1 (cheapest — the value space stays reservable), or define its residual role explicitly (e.g., "under `--warn-only`, `--require-full-coverage` re-escalates skipped dimensions to a failing verdict" — the mirror of FR19's role (a)).

### M3 — The exit-code-matrix Measurable Outcome omits `indeterminate → 1`, the most-litigated cell in the document

- **Location:** § Measurable Outcomes (~line 154).
- **Quote:** "Exit-code matrix 100% correct across severity tiers (clean/warn → 0, policy-violation → 1, error → 2) + each typed `error_kind` …"
- **Why it burns:** `indeterminate → exit 1` was pinned by a dedicated correction pass (2026-07-12, callout (a)) and is the load-bearing cell behind FR16/FR20, J1, J3, and the offline-DB state machine — yet the enumerated acceptance matrix that QA will transcribe into a test table doesn't contain it (nor `bypassed → 0`, nor `130`). A test suite written to this line reports "exit-code matrix 100% correct" while never exercising the one cell the PRD spent two reconciliation passes nailing.
- **Fix:** Enumerate the full projection: clean/warn/not-applicable/bypassed → 0; un-waived policy-violation → 1; **indeterminate → 1**; error → 2; SIGINT → 130.

### M4 — FR22's "never clean / non-passing" absolute has undeclared exceptions the PRD itself mandates (`--allow-empty`, `--warn-only`)

- **Location:** FR22 (~line 543) vs J3 (~line 218: "`--allow-empty` downgrades that to exit-0 + `coverage: none`") vs State-Machine (~line 445: "`--warn-only` downgrades").
- **Quote (FR22):** "treat any run that did **not meaningfully scan** (empty extraction, expected-but-missing manifest, crashed engine, or skipped coverage) as **non-passing, never clean**."
- **Why it burns:** FR22 as written is testable and absolute — and two sanctioned flags violate its letter (exit 0 on a Python-present-nothing-parsed sweep; exit 0 on skipped coverage under warn-only). The intended resolution is the status-vs-exit split (status stays non-`clean`; only the *exit* is downgraded), but FR22 says "non-passing," which conflates the two channels the PRD elsewhere insists are "deliberately different orderings" (J9). A literal implementer hard-fails `--allow-empty`; a lenient one weakens FR22. Crashed-engine, note, must *not* be downgradable by either flag (it's `error`), and FR22 doesn't say that either.
- **Fix:** Restate FR22 in channel terms: "…the run's **status is never `clean`** and its default exit is non-zero; `--allow-empty` / `--warn-only` may downgrade the **exit** for the empty-extraction and skipped-coverage cases only — never the status, and never for `error`-class outcomes (crashed engine)."

### M5 — FR40's "failed PR-open surfaces as a typed warning" is unimplementable as stated: the actuator runs strictly post-verdict, so there is no report left to warn in

- **Location:** FR40 (~line 575); NFR-S2 (~line 606).
- **Quote:** "The actuator … runs strictly post-verdict … A failed PR-open never alters the verdict or exit code (it surfaces as a **typed warning**)."
- **Why it burns:** "Typed warning" is load-bearing vagueness. If the warning lands in the `ComplianceReport`/status channel, it can flip a `clean` run to `warn` — altering the verdict FR40 promises is untouchable, and mutating a report whose verdict was "computed before and independent of actuation." If it goes to stderr only, it's untyped by the PRD's own taxonomy (typed kinds live in the report per FR21). Neither reading satisfies the sentence.
- **Fix:** Pin the channel: e.g., "a failed PR-open is recorded in a post-verdict `actuation` report section (outside status/exit composition, analogous to `review_required`) and echoed to stderr; it never feeds the FR20 lattice."
- **Resolved (AUD-WARDEN-030):** live PRD FR40 uses the post-verdict `actuation` section + stderr; this finding is historical.

---

## LOW

### L1 — "stdlib-only" survives in three *binding* v1 statements, protected only by a blanket supersession 400+ lines away

- **Location:** Technical Success (~line 148: "stdlib-only bridge"), MVP scope (~line 163: "stdlib-only, two-pass eval"), Complete Feature Set (~line 475: "E1 — manifest bridge: … (stdlib-only …)") vs reconciliation callout #6 (~line 83: "Every 'stdlib-only extraction' phrasing below is superseded by 'stdlib-lean + targeted safe libs.'").
- **Why it burns:** The blanket note technically covers these (hence LOW, not re-reported as live contradiction) — but PyYAML `safe_load` is a *required* parser in the shipped design, `jsonschema` is a runtime dep, and the binding capability contract still says "stdlib-only" in-place. A reader of § Complete Feature Set alone writes an AC that the shipped code fails.
- **Fix:** Mechanical sweep: replace in-place with "stdlib-lean (NFR-S1: no execution of untrusted input)".

### L2 — Hygiene-rule enumeration drift: "DEP002/3/4 → warn" (callout #3) vs "DEP002–005 → warn" (FR18)

- **Location:** Reconciliation callout #3 (~line 80) vs FR18 (~line 539).
- **Why it burns:** Is DEP005 in scope or not? Trivial to fix now, an hour of confusion in a story review later.
- **Fix:** Align both to the actual deptry rule set (DEP002–005 if DEP005 exists in the pinned engine range).

### L3 — Growth Features places cf_atlas promotion in the v1.x bucket; the spec's release map explicitly evicts it to Future/backlog

- **Location:** § Growth Features (~line 167: "cf_atlas promotion (FR-16/FR-18 MCP tool + pixi CLI)") vs spec § Release map v1.x-early row ("cf_atlas promotion lives in § Future/backlog").
- **Why it burns:** Growth claims to be "= the spec's v1.x bucket as re-baselined" and then includes an item the spec's v1.x row explicitly excludes. Minor tier drift against the sole source of truth.
- **Fix:** Move cf_atlas promotion into the PRD's post-v1 backlog framing (it already appears correctly in the deferred list at line 484).

### L4 — Success Criteria "User Success" and "What Makes This Special" still describe a two-axis product

- **Location:** ~line 96 ("**two independent extraction paths** … both jobs"), ~line 129 ("a unified **hygiene + vulnerability** verdict").
- **Why it burns:** D12's headline is a *four*-axis v1 with flag-activated gates; the user-success promise and the differentiation section were not lifted. Not a contradiction (extraction genuinely has two engine paths; license reads the same manifests), but the v1 promise a stakeholder reads here undersells the contract the FR block binds — and license/currency success has no User Success sentence at all (only the Measurable Outcomes bullet).
- **Fix:** One sentence in each: "…and license + currency verdicts on every resolved component (gates flag-activated, D12)."

### L5 — Frontmatter `v1_must` still points "see § Domain-Specific Requirements" for a KEV deferral that section now reverses

- **Location:** frontmatter line 39.
- **Why it burns:** Marked historical by the replan note (so: LOW, not re-reported as live) — but a historical block containing a *forward pointer into live text* ages worse than plain history; the pointer suggests the target still substantiates the claim. Compounds C1.
- **Fix:** When fixing C1, append "(reversed by D3/D12)" inside the frontmatter parenthetical or strip the pointer.

### L6 — Domain section cites "NFR3 twice-run byte-identical" as the domain requirement, eliding that byte-identical is opt-in

- **Location:** § Domain-Specific Requirements → "Determinism for forensics" (~line 349) vs NFR-R3b (~line 601).
- **Why it burns:** NFR-R3b makes the default *decision*-determinism and byte-identical an opt-in `--deterministic` mode; the domain sentence (old `NFR3` label, no mode qualifier) reads as if byte-identical is the default forensic property. A compliance reader could conclude every CI run is byte-reproducible; it isn't unless the flag is set.
- **Fix:** "…NFR-R3b twice-run byte-identical (in `--deterministic` mode) is an audit/reproducibility requirement…"

---

## Counts

| Severity | Count |
|---|---|
| Critical | 2 |
| High | 3 |
| Medium | 5 |
| Low | 6 |
| **Total** | **16** |

## What the fix pass got right (for calibration)

The D12 re-baseline itself is coherent where it landed: the header callout, FR32–FR40 (sections I–L), FR37's unconfigured-`warn` rule, the CLI axis-gate flags, NFR-S9, the Journey-6 FR39 note, the Measurable-Outcomes multi-axis bullet, and the 6-epics/29-stories scoping all agree with the spec's Reconciliation note and Release map. The FR-crosswalk table cleanly disarms the working-label collision for everything *before* the FR block. The failures above are almost all the predicted class: a fix applied at one site whose contradicting twin (Technical Success, the open-questions hand-off, a list body, a journey's bolded payoff) was not swept.
