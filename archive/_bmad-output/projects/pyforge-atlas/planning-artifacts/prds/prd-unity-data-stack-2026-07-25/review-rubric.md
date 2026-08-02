---
title: "PRD Quality Review — Unity Data Stack"
reviewer: rubric-walker
date: 2026-07-25
verdict: "Strong; ready to feed the architecture stage pending OQ-1 (lock architecture) resolution — the PRD already flags this itself. Findings are mechanical (ID drift, one Assumptions Index roundtrip gap, inconsistent NFR verification pointers), not substantive."
---

# PRD Quality Review — Unity Data Stack

Reviewed: `prd.md` (1360 lines, §0–§17) + `addendum.md` (359 lines, §A–§J), both dated 2026-07-25.
Context respected per reviewer brief: headless/`[ASSUMPTION]`-tagged production is correct and not
flagged as a gap; epics/stories are deliberately out of scope; §14/§15 are non-template additions
judged on quality; the three declared research limitations (web-search unavailable, cf_atlas DB
absent, one 403'd source) are accepted as-is.

## Overall verdict

This is an unusually rigorous PRD for a headless/express run: all 60 FRs carry explicit testable
consequences, every claimed novelty is checked against two research reports and graded
CONFIRMED/STALE/WRONG/NEW (§15), and the addendum surfaces genuine three-way trade-offs (§A–G)
rather than pre-baked answers. What's at risk is downstream mechanics, not substance: a stale
feature-count line, one Assumptions Index entry with no inline tag, and an inconsistent
"verified-by" pointer across the NFR set — all cheap, low-risk fixes. The one thing that actually
blocks forward progress (OQ-1, the lock architecture) is already correctly identified and flagged
as blocking by the PRD itself, which is exactly what this dimension should do.

---

## 1. Decision-readiness — **strong**

| Item | Verdict | Justification |
|---|---|---|
| Decisions stated as decisions, not buried as considerations | PASS | OQ-1 is explicitly "Blocks: Everything. Resolve first" (§16); A-3 tags the pixi-primary lock call as unconfirmed (§17); FR-9's `[NOTE FOR PM]` names it as "the one requirement in this feature that changes the intake design rather than correcting it." |
| Trade-offs named with what was given up | PASS | Addendum §A.2 runs explicit For/Against for all three lock-architecture options — e.g. "Against (a): a consumer reading only `pylock.toml` gets the Python half," "Against (b): Contradicts Constitution Art. II." |
| Open Questions are genuinely open, not rhetorical | PASS | OQ-14: "the two intake gists disagree with each other" — a real unresolved conflict, not a question answered in the next sentence; 23 OQs total, each with an explicit blocker and owner. |
| `[NOTE FOR PM]` at real tensions | PASS | FR-35: Constitution mandates Gitflow/`develop`, "conflicts with the host repository's trunk-based `main` convention"; FR-58: PII masking is "the largest unbacked assertion in the intake set"; CR-1: the CRA→SBOM inference is "widely held but unverified here." None of these are safe-checkpoint filler. |

No findings — this dimension is a standout. The Risk table (§13) and Open Questions table (§16)
together read as genuine decision support, not risk-theater.

---

## 2. Substance over theater — **strong**

| Item | Verdict | Justification |
|---|---|---|
| Persona theater | PASS | Exactly 4 UJs ("Four carry the product," §3.3), each realizing named features and driving distinct FR clusters (UJ-3 Priya → FR-33–36 innersource model). |
| Innovation theater | PASS | §1 Vision states plainly "Unity assembles more than it invents," separating consumed capability (`pyforge-warden`, `conda-forge-expert`, `pyforge-atlas`) from genuinely new work (lock architecture, governance split, contribution model) — the opposite of inflated novelty claims. |
| NFR theater | PARTIAL | NFR-1, NFR-2, NFR-3, NFR-5 each carry an explicit "Verified by FR-X/SM-X" clause. NFR-6, NFR-7, NFR-9, NFR-10 do not (NFR-8 has an inline FR-6 mention but not the same "Verified by" phrasing) — see Finding below. |
| Vision theater | PASS | The Vision is specific and non-swappable: "six problems get solved once instead of once per team," named individually, plus the dual conda+Python resolution claim tied to market research §1.2 in the addendum rather than asserted in a vacuum. |

### Findings
- **medium** Inconsistent NFR verification discipline (§6) — NFR-1 through NFR-5 explicitly state what FR/SM verifies them; NFR-6 (Auditability), NFR-7 (Diagnosability), NFR-9 (Extensibility), NFR-10 (Supply-chain integrity) do not, even though the underlying substance is testable and traceable elsewhere (e.g. NFR-10 clearly maps to FR-39–47). *Fix:* add a "Verified by FR-X" clause to NFR-6, 7, 9, 10 matching the pattern already used for NFR-1–5, 8.

---

## 3. Strategic coherence — **strong**

| Item | Verdict | Justification |
|---|---|---|
| Stated thesis | PASS | "The value is not the monorepo. It is that six problems get solved once instead of once per team" (§1), with each of the six named. |
| Feature prioritization follows the thesis | PASS | The 9 features (§5.1–5.9) build directly toward the reproducibility + governance + compliance thesis rather than reading as an unordered capability list. |
| Success Metrics validate the thesis, not activity | PASS | SM-2 is explicitly labeled "the innersource proof; if it stays near zero the platform has failed at its premise regardless of technical quality" — not a DAU/MAU-style vanity metric. SM-4/SM-6 measure reproducibility/air-gap coverage directly. |
| Counter-metrics named | PASS | SM-C1–C4 each state precisely what primary metric or FR they counterbalance and why (e.g. SM-C1 vs SM-2: "contribution rate can be gamed by trivial PRs while people still fork"). |
| Coherent MVP scope kind | PASS | Platform-building scope logic throughout: "the pattern plus one worked Domain" (§11.2, FR-54) is internally consistent platform-MVP reasoning, not a grab-bag of easy features. |

No findings.

---

## 4. Done-ness clarity — **strong, with two medium findings**

| Item | Verdict | Justification |
|---|---|---|
| FRs have at least one testable consequence | PASS | All 60 FRs (FR-1–FR-60) carry an explicit "Consequences (testable):" block. This is the PRD's strongest mechanical habit. |
| Vague/unbounded language flagged | PARTIAL | NFR-4: "Commit-time checks complete fast enough not to be bypassed" is unbounded — the exact pattern this dimension asks to be unforgiving about — though it is self-aware and deferred to OQ-12 ("Measure, then set") rather than smuggled through as if final. |
| Acceptance criteria implied or explicit | PASS | The "Consequences (testable)" bullets function as acceptance criteria throughout; no FR lacks them. |
| Non-functional sections use bounds, not adjectives | PARTIAL | NFR-1/2/3/5/8 have bounds or a clear verification path; NFR-6/7/9/10 are descriptive without a bound or explicit pointer (see §2 finding above — same underlying issue surfaces here). |

### Findings
- **medium** NFR-4 (Feedback latency) has no testable bound (§6) — "fast enough not to be bypassed" / "fast enough to run before every push" gives no number. It is honestly flagged as `[ASSUMPTION]` A-8 with OQ-12 tracking the follow-up measurement, which mitigates but does not close the gap — architecture cannot yet write a test against this NFR. *Fix:* none needed in this PRD version beyond what OQ-12 already commits to; flag for architecture to close before the Quality Gate is implemented, not before PRD sign-off.
- **medium** — see §2 finding (NFR verification-pointer inconsistency); repeated here because it directly affects whether a reader can determine "done" for NFR-6/7/9/10 without cross-referencing the FR list by hand.

---

## 5. Scope honesty — **strong**

| Item | Verdict | Justification |
|---|---|---|
| Non-Goals section doing real work | PASS | §10 has 8 substantive non-goals, each with a one-line rationale (e.g. "Unity is not a build-graph engine... Orthogonal, and unwinnable"). |
| Explicit de-scoping callouts | PASS (substance present; literal tag format differs) | §11.2 "Out of Scope for MVP" + Addendum §J "Deferred with reasons" table both name the item, the reason, and the revisit condition. The rubric's literal `[NON-GOAL for MVP]` bracket token isn't used verbatim, but the functional content is fully present — mechanical, not substantive, gap. |
| `[ASSUMPTION]` tags indexed | PARTIAL | 13 of 14 Assumptions Index entries roundtrip cleanly to an inline tag; A-14 does not (see Mechanical notes). |
| `[NOTE FOR PM]` at deferred decisions | PASS | FR-9, FR-35, FR-58, CR-1, Art. XI (§14.2) — each is a real, load-bearing tension, not a safe checkpoint. |
| De-scoping proposed honestly, not silently | PASS | Addendum §J names 8 deferred items each with "why deferred" and "revisit when" columns. |
| Open-items density appropriate to stakes | PASS | 23 OQs + 14 assumptions is high in absolute terms, but this PRD explicitly states "Nothing tagged `[ASSUMPTION]` should be treated as confirmed scope" (§0) and OQ-1 is flagged as blocking everything — i.e., the PRD does not present itself as green-lit-to-build. Given the declared headless mode, this density is correctly calibrated rather than a red flag. |

### Findings
- **low** Addendum-level `[ASSUMPTION]` tags (§B.2, §C, §E, §F, §G) are not indexed in the PRD's §17 Assumptions Index. §17's own scope statement ("Every `[ASSUMPTION]` in this document") is arguably PRD-only by its wording, so this may be intentional — but a reader relying solely on §17 as "the" assumptions list would miss five further open assumptions that live in the addendum. *Fix:* either broaden §17's scope note to say "PRD-scoped; see addendum §B/C/E/F/G for mechanism-level assumptions," or fold the addendum's assumptions into §17 as an appendix.

---

## 6. Downstream usability — **adequate**

This PRD is chain-top (§0: "This PRD is for the architecture stage that follows it"), so this
dimension carries real weight despite epics/stories being out of scope for this run.

| Item | Verdict | Justification |
|---|---|---|
| Glossary present; terms used identically | PASS | 20-term glossary (§4); spot-checked terms (Stage, Workspace Lock, Exported Lock, Compliance Report, Trusted Committer) are used consistently in FR text — e.g. "A Stage is not an Environment" (§4) is actively reinforced at FR-9 rather than contradicted. |
| FR/UJ/SM IDs contiguous, unique, cross-refs resolve | PARTIAL | §5's own intro states "Nine features, FR-1 through FR-58" — but the section actually runs FR-1 through FR-60 (§5.9 contains FR-59, FR-60), and §11.1's own scope enumeration correctly covers FR-1–FR-60. This is a stale summary line, not a numbering defect in the FRs themselves. All other ID series (UJ-1–4, NFR-1–10, CR-1–5, R-1–10, SM-1–9/SM-C1–4, OQ-1–23, A-1–14) are contiguous with no gaps or duplicates. |
| Each section stands alone via Glossary terms | PASS | Sections lean on the Glossary rather than "see above"; the heavy dependence on the companion `addendum.md` for mechanism detail is appropriate since both are reviewed together and the PRD explicitly signposts the split (§0). |
| UJs have named protagonists | PASS | Dana (UJ-1), Marcus (UJ-2), Priya (UJ-3), Sam (UJ-4) — each introduced with role and entry-state context inline; no floating UJs. |

### Findings
- **medium** §5 intro miscounts the FR range (§5, line "Nine features, FR-1 through FR-58") — actual range is FR-1–FR-60. Low real-world impact (all FRs are individually correct and §11.1 enumerates the true range), but it's exactly the kind of drift that misleads a reader skimming only the section intro. *Fix:* change "FR-1 through FR-58" to "FR-1 through FR-60" in §5's opening line.

---

## 7. Shape fit — **strong**

| Item | Verdict | Justification |
|---|---|---|
| Product type read correctly | PASS | Internal enterprise platform with regulated-domain overlap (CRA/GDPR) and genuine multi-stakeholder cross-team dynamics — the PRD treats it as a capability spec with load-bearing UJs, not as a consumer product forced into UJ theater or an internal tool stripped of them. |
| UJs load-bearing, not overhead | PASS | UJ-3 (Priya) directly instantiates the innersource thesis (cross-team contribution without a fork) that FR-33–38 and SM-2 exist to serve — removing it would remove a load-bearing piece of the argument, not just color. |
| Constraint traceability for the regulated domain | PASS | §14 Constitution Provenance Map (mandate-by-mandate) + §7 Compliance/Regulatory (CR-1–5) + §14.3 (8 explicit required amendments to the Constitution) together give exactly the non-negotiable traceability this shape calls for. |
| Brownfield existing-code references accurate | PASS | §1 and §9 consistently distinguish consumed capability (`pyforge-warden`, `conda-forge-expert`, `pyforge-atlas`, `enterprise-airgap`) from new work, each with an explicit integration risk (e.g. §9: "Integration boundary undecided (OQ-4)"). |
| Chain-top handling | PASS | §0 explicitly names architecture as the PRD's primary downstream consumer; the OQ table (§16) assigns "Architecture" as owner on 8 of 23 items, matching the stated handoff. |

No findings — this is a well-matched shape for the product type.

---

## Mechanical notes

- **Glossary drift.** Minor: the Stage glossary entry (§4) lists branch policy, Data
  Classification, network posture, and datastore as what a Stage carries, but Addendum §B.3 adds
  "promotion policy (auto vs manual approval)" and "the Environment it resolves to" as further
  Stage attributes not reflected back into the §4 definition. Low severity — doesn't create a
  contradiction, just an incomplete glossary entry.
- **ID continuity.** One real drift: §5's "Nine features, FR-1 through FR-58" undercounts by 2
  (actual FR-1–FR-60; see Finding under Downstream usability). Every other ID series checked
  (UJ, NFR, CR, R, SM/SM-C, OQ, A) is contiguous, unique, and has no dangling cross-reference.
- **Assumptions Index roundtrip.** 13 of 14 PRD-body `[ASSUMPTION]` tags roundtrip cleanly in both
  directions against §17 (A-1 through A-13, spot-checked against their cited sections). **A-14**
  (§3.2, "The listed non-user groups are correct audience boundaries") is indexed in §17 but has
  **no corresponding inline `[ASSUMPTION]` tag** in §3.2's actual text — the index→inline direction
  breaks for this one entry. *Fix:* add an inline `[ASSUMPTION]` tag to §3.2, or remove A-14 from
  §17 if the non-user list is considered confirmed rather than inferred.
- **UJ protagonist naming.** Clean — all four UJs name a protagonist and carry role/entry-state
  context inline (Dana/data engineer/day-one; Marcus/`customer` domain; Priya/no commit rights;
  Sam/compliance owner).
- **Required sections for stakes/product type.** Complete: Vision, Why Now, Target User
  (JTBD + Non-Users + UJs), Glossary, 9 Features/60 FRs, Cross-cutting NFRs, Compliance and
  Regulatory, Constraints, Integration and Dependencies, Non-Goals, MVP Scope, Success Metrics
  (primary/secondary/counter), Risks, plus the two caller-requested additions (§14 Constitution
  Provenance Map, §15 Research Deltas), Open Questions, and Assumptions Index — a complete set for
  an enterprise capability-spec PRD headed into architecture.
