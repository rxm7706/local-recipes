# Herald Proclamation Framework — Coordinated Epic Structure

**Decision**: Moments 2–4 implemented as **one coordinated epic** with 6–7 sub-stories, prioritizing **integration correctness** over velocity-to-first-value.

---

## Epic: Herald Proclamation Framework (Moments 2–4)

**Thesis**: Complete Herald's Four Moments by delivering three missing surfaces (Progress, Success, Operations) with unified CLI, integrated web surface, and shared automation framework.

**Acceptance Criteria**:
- [ ] Herald CLI supports `herald progress`, `herald success`, `herald notice` commands
- [ ] Herald web surface unifies all three Moments in nav + layout
- [ ] Evidence linking works across Moment 3 (success) and Moment 4 (operations)
- [ ] Automation framework (weekly, on-event, on-manual) executes without errors
- [ ] All three Moments tested together (integration test suite passes)
- [ ] CLI help and documentation complete and accurate

---

## Story Breakdown

### Story 1: Herald CLI Architecture & Dispatcher
**Scope**: Design and implement unified command structure supporting progress/success/notice subcommands.

**Input**: Spec + Herald v0.1.0 CLI structure (existing).  
**Output**: CLI backbone accepting `herald progress`, `herald success`, `herald notice` with argument parsing.

**Acceptance Criteria**:
- [ ] `herald --help` lists all three subcommands
- [ ] Each subcommand has its own `--help` and argument spec
- [ ] CLI structure extensible for future Moments
- [ ] Tests pass for argument parsing + dispatch

**Estimated effort**: 2–3 stories (foundation work; unblocks all others).

---

### Story 2: Herald Web Surface Design & Layout
**Scope**: Design unified web surface layout + navigation supporting all three Moments.

**Input**: Herald web prototype (existing Moment 1 surface), Moment 2/3/4 surface specs.  
**Output**: Responsive layout with: header nav (Pitch / Progress / Success / Operations tabs), unified color scheme, sidebar filtering (by station/date/status).

**Acceptance Criteria**:
- [ ] All three Moments visible in nav without overlap
- [ ] Layout responsive (desktop + mobile)
- [ ] Color/icon convention consistent across all Moments
- [ ] Surface integrates Modernist design system (from Moment 1)

**Estimated effort**: 1.5–2 stories (design + frontend scaffold).

---

### Story 3: Moment 2 — Progress Visibility Implementation
**Scope**: Implement weekly progress summaries with cost transparency and unblock narrative.

**Input**: Sprint-status ledger, bmad-loop journals, PRD updates (data sources).  
**Output**: CLI `herald progress <station>` and web Progress tab showing: what shipped, cost (compute/tokens/time), unblocks.

**Acceptance Criteria**:
- [ ] `herald progress warden` returns JSON with latest progress (or retrieves from cache)
- [ ] Cost metrics accurate (derived from journal timestamps)
- [ ] Automation: triggers on-ship event (webhook from CI) + weekly cron Thursday 2300 UTC (fallback)
- [ ] Manual `herald progress --update` works for operators
- [ ] Web tab renders progress widget with station filter + date range
- [ ] Tests: 5 sample progress records generated and validated

**Dependencies**: Stories 1, 2.  
**Estimated effort**: 2–3 stories.

---

### Story 4: Moment 3 — Success Proclamation Implementation
**Scope**: Implement release claims with evidence linking (tests, metrics, adoption).

**Input**: Closed PRs, test results, dashboard metrics, adoption signals.  
**Output**: CLI `herald success <project>` and web Success archive showing: claim + evidence links.

**Acceptance Criteria**:
- [ ] On PR-close + passing gates, Herald auto-extracts: test results (CI), metrics (dashboard), adoption signals (downstream PRs)
- [ ] Claim generated with extracted evidence (deterministic, reproducible)
- [ ] Operator review: `herald success review <claim-id>` shows claim + evidence before publish
- [ ] `herald success publish <claim-id>` makes claim public + indexed
- [ ] Web Success tab renders claims chronologically with evidence badges (green=linked, yellow=pending)
- [ ] Evidence links are permanent and resolvable
- [ ] Tests: 5 sample claims with different evidence combinations; auto-extract logic tested

**Dependencies**: Stories 1, 2, 3.  
**Estimated effort**: 2–3 stories.

---

### Story 5: Moment 4 — Operations Proclamation Implementation
**Scope**: Implement notice board for deprecations, security fixes, end-of-life.

**Input**: Notice templates, author intent, proof/reason links.  
**Output**: CLI `herald notice author|list|archive` and web Operations notice board.

**Acceptance Criteria**:
- [ ] `herald notice author --type deprecation --component foo --reason "..." --migrate-to bar` creates notice
- [ ] Web Operations tab renders notices by date/category (YYYY-MM folder structure + category tags)
- [ ] Archive: simple index by date/category; notices permalinked and indexed (no 404s)
- [ ] Manual search (Cmd+F) works; no full-text backend needed at this scale
- [ ] Redirect rules generated for deprecated URLs
- [ ] Tests: 5 sample notices (deprecation, fix, EOL); archive retrieval works

**Dependencies**: Stories 1, 2.  
**Estimated effort**: 2–3 stories.

---

### Story 6: Integration Testing & Evidence Linking
**Scope**: End-to-end testing of all three Moments working together; cross-Moment evidence links.

**Input**: Stories 3, 4, 5 outputs.  
**Output**: Integration test suite; shared evidence-linking framework tested across Moment 3 & 4.

**Acceptance Criteria**:
- [ ] 3 full scenarios tested: Progress → Success → Operations (e.g., ship Atlas feature, claim success, deprecate old API)
- [ ] Evidence linking works bidirectionally (Moment 3 links to Moment 4 notice, vice versa)
- [ ] CLI + web surface tested together
- [ ] No race conditions in automation triggers
- [ ] Tests pass with >90% coverage

**Dependencies**: Stories 3, 4, 5.  
**Estimated effort**: 1–2 stories.

---

### Story 7: Documentation & CLI Help
**Scope**: Complete Herald CLI help, web surface UX guide, author guide for notices.

**Input**: All stories' outputs.  
**Output**: `herald --help` comprehensive; web surface tooltip text; authoring guide for operators.

**Acceptance Criteria**:
- [ ] `herald --help` and `herald <subcommand> --help` are clear and complete
- [ ] Web surface has inline help (tooltips, ?-button guides)
- [ ] Authoring guide published: "How to write a success claim", "How to author a deprecation notice"
- [ ] Examples provided (sample progress, sample success claim, sample notice)

**Dependencies**: All stories.  
**Estimated effort**: 0.5–1 story.

---

## Automation Rules (Locked Decisions)

- **Moment 2 (Progress)**: Trigger on-ship event (webhook) + weekly cron Thursday 2300 UTC
- **Moment 3 (Success)**: Auto-extract on PR-close + passing gates (test results, metrics, adoption). Operator review gate.
- **Moment 4 (Operations)**: Manual author + CLI-mediated (no auto-trigger). Simple date/category archive indexing.

---

## Shared Infrastructure

These are built **incrementally across stories** but designed as **unified frameworks**:

### CLI Dispatcher
- Single entry point accepting all three Moment subcommands
- Shared argument parsing (--help, --json, --date-range, etc.)
- Built in Story 1; extended in Stories 3–5

### Web Surface Layout
- Unified nav bar (Pitch / Progress / Success / Operations)
- Shared sidebar (station/date filters, search)
- Consistent color scheme and typography
- Built in Story 2; filled with content in Stories 3–5

### Evidence-Linking Framework
- Shared schema for proof/reason links (PR URL, test URL, metric URL, notice URL)
- Bidirectional link resolution (Moment 3 claim → Moment 4 notice, etc.)
- Link validation on store (dead links detected)
- Built incrementally; tested end-to-end in Story 6

### Automation Framework
- Unified trigger model (scheduled, on-event, on-manual-author)
- Shared scheduler (cron for scheduled tasks, webhook for on-event triggers)
- Automation rules stored in Herald config (extensible for future Moments)
- **Moment 2 rule**: on-ship webhook + Thursday 2300 UTC fallback cron
- **Moment 3 rule**: on-PR-close + passing gates, auto-extract evidence (test results, metrics, adoption). Operator review gate before publish.
- **Moment 4 rule**: manual author + CLI-mediated (no auto-trigger)
- Built incrementally; tested end-to-end in Story 6

---

## Timeline & Dependencies

```
Story 1 (CLI Arch)        ═══════════════════════════════════════════
Story 2 (Web Layout)      ═════════════════════════════════════════════
  ↓ (depends on 1, 2)
Story 3 (Moment 2)        ═══════════════════════════════════════════════
Story 4 (Moment 3)        ═══════════════════════════════════════════════
Story 5 (Moment 4)        ═══════════════════════════════════════════════
  ↓ (depends on 1, 2, 3, 4, 5)
Story 6 (Integration)     ═══════════════════════════════════════════════
  ↓ (depends on all)
Story 7 (Docs)            ═════════════════════════════════════════════

Critical path: Stories 1 → {3,4,5} in parallel → 6 → 7
Estimated total: 12–18 stories (lumpy work distribution due to shared infrastructure)
```

---

## Quality Gates

Before shipping this epic:

1. **CLI correctness**: All three subcommands work; help text is clear
2. **Web integration**: All three Moments visible + navigable without layout issues
3. **Evidence integrity**: No dead links; all proof is resolvable
4. **Automation reliability**: No false-positive triggers; no missed triggers
5. **Test coverage**: >90% on core logic; manual smoke tests on web surface
6. **Documentation**: No feature is undocumented

---

## What This Epic Does NOT Do

- **Does not implement Moment 1 improvements** — Pitch/deck family (spec-herald-pitch) is complete and separate
- **Does not design video pipeline integration** — Moment 4 feeds narration to bmad-manticore, but video rendering is separate
- **Does not handle multi-region Herald surfaces** — Assumes single unified Herald service (could expand in Herald v2)
