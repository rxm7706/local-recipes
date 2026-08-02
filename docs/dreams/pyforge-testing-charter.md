---
title: "Dream — PyForge Testing Charter: Systematic Testing for the Guild"
date: 2026-08-02
status: archived
archived-reason: absorbed
owner: marshal
scope: "Testing framework, quality gates, systematic coverage across all stations"
---

> **Narrative consolidated 2026-08-02 (dream-level only).** This Dream's narrative now lives
> in [`docs/dreams/pyforge-marshal.md`](pyforge-marshal.md) under "The frontier." **Its
> downstream Spec stays fully live and untouched**: `spec-pyforge-testing-charter` (5
> capabilities) is real — CAP-1 and CAP-2 are shipped (verified on disk, not this Dream's own
> claims, which this Spec found partly inaccurate when it verified them: neither herald nor
> warden had complete test architecture, and six other stations already had real pytest
> coverage this Dream's "no systematic test architecture at all" line missed). CAP-3 (a shared
> `pyforge-testing-kit` package) and CAP-4 (a CI coverage gate) are real, unbuilt, and not yet
> decomposed to a PRD. Only this top-level Dream file consolidates; the Spec and its
> `station-tea-status.md` companion were not merged, retired, or reworded.

# Dream: PyForge Testing Charter — Systematic Testing for the Guild

**Vision**: Test architecture is a first-class citizen in the Dream-to-Code pipeline. All 8 PyForge stations inherit the same systematic testing framework, eliminating duplication and ensuring quality gates are universal.

---

## The Problem

Testing is invisible and ad-hoc across the PyForge stations.

- **Herald** built test architecture manually (1,895 lines) — a masterpiece, but unrepeatable
- **Atlas, Warden, Doctor, Mason, Scribe, Steward** have no systematic test architecture at all
- **Each team re-invents** fixtures, test frameworks, quality gates — massive duplication
- **No visibility** into test coverage, risk assessment, or readiness per station
- **No automation** — test architecture generation is manual work per project
- **No guild standard** — everyone interprets "testing" differently

**Result**: Testing is a bottleneck, not a strength. We ship features without confidence.

---

## The Vision

Test architecture flows from the spec just like PRD, architecture, and epics do.

**One flow:**
```
Dream → Spec → PRD → Architecture → Epics → Stories → TEST ARCHITECTURE → Development
```

**One framework** (BMAD TEA + Playwright):
- CLI testing: subprocess spawning, output capture, exit codes
- Web testing: Page Object Model, responsive design, interactive flows
- Integration testing: cross-layer coordination, webhook simulation, state transitions
- Async testing: time mocking, cron scheduling, delayed operations
- Visual testing: screenshot diffing, layout regression
- Performance testing: latency benchmarks, throughput tracking

**One reference** (Herald):
- 1,895-line canonical test architecture
- 9 Playwright patterns
- Risk assessment (11 high, 14 medium, 7 low)
- Test matrix (54 test suites across 18 stories)
- Quality gates (unit >80%, integration >70%, e2e happy-path + 3 risks)
- Reusable pattern appendix (how to apply to other stations)

**One shared foundation** (pyforge-testing-kit):
- CLI runner fixtures (subprocess + output capture)
- Web page objects (header, tabs, sidebar, filters)
- Database factories (progress, claim, notice records)
- Auth/HTTP/time mocks
- Test data builders (fluent API)

**One automation** (bmad_tea_playwright.py):
- Input: epics-with-stories.md + ARCHITECTURE-SPINE.md
- Output: test-architecture.md + playwright.config.ts + pytest.ini + tests/ scaffold
- One command per project (no manual re-work)
- 30 seconds per station

**One guild standard** (test-charter.md):
- All 8 Smiths' testing responsibility
- Quality gates per station
- Phase 1-4 roadmap (30 min fleet deployment)
- Risk-based testing principles

---

## The Realization

**When this dream is real:**

1. ✅ **Herald test architecture complete** — canonical reference, 1,895 lines with Playwright patterns
2. ✅ **Automation script created** — bmad_tea_playwright.py generates test architecture one-command-per-project
3. ✅ **Guild testing charter defined** — all 8 Smiths' testing responsibility, quality gates, Phase 1-4 roadmap
4. ⏳ **pyforge-testing-kit created** — shared fixtures package (CLI runner, web pages, database, auth, mocks)
5. ⏳ **Applied to all 8 stations** — atlas, doctor, marshal, mason, scribe, steward, warden (batch run, 30 min)
6. ⏳ **Development teams execute** — each story includes pytest unit + Playwright e2e tests
7. ⏳ **Dashboard tracks** — test-architecture status per station (complete/ready/pending)
8. ⏳ **CI gates enforce** — unit >80%, integration >70%, e2e pass before merge

---

## The Promise

**For developers:**
- Clear test matrix (which tests to write for each story)
- Reusable fixtures (no re-implementing CLI runners, page objects, DB factories)
- Playbook patterns (9 proven patterns for different test scenarios)
- Fast feedback (pytest unit tests run in seconds, Playwright e2e in <2s per scenario)

**For architects:**
- Uniform quality gates (every station targets unit >80%, integration >70%, e2e happy-path + 3 risks)
- Risk-based testing (high-risk items get 2+ test layers)
- Scalability (add new stations without overhead — same pattern applies)
- Traceability (test matrix ties back to stories, architecture decisions to tests)

**For the factory:**
- No duplication (write once, inherit everywhere)
- Determinism (same input → same test architecture every time)
- Confidence (all 8 stations ship with the same quality standard)
- Speed (one-command per project, 30 min for entire fleet)

---

## The Mottos (Guild Testing Responsibility)

Each Smith owns their testing:

| Smith | Motto | Testing Responsibility |
|-------|-------|------------------------|
| 🎺 Herald | Capture. Illustrate. Proclaim. | Visibility testing (CLI, web UI, proclamation) |
| ⚔️ Marshal | Enforce. Guard. Run the line. | Governance testing (policies, composition) |
| 🗺️ Atlas | Map. Know risks. Set foundation. | Intelligence testing (discovery, mapping, risk) |
| 🛡️ Warden | Halt. Clear axes. Protect perimeter. | Security testing (gates, compliance, validation) |
| 🧱 Mason | Orchestrate. Bridge worlds. Ship deterministically. | Build testing (orchestration, dual-ship) |
| 🏥 Doctor | Check vitals. Diagnose. Rank what matters. | Quality testing (diagnostics, prioritization) |
| 📖 Scribe | Capture. Keep graph. Answer from memory. | Memory testing (documentation, capture, recall) |
| 👑 Steward | Supply estate. Guard credentials. Ensure reliability. | Operations testing (provisioning, access, reliability) |

---

## The Roadmap (4 Phases)

### Phase 1: Foundation ✅ COMPLETE
- Herald test architecture (1,895 lines)
- Automation script (bmad_tea_playwright.py)
- Guild testing charter (test-charter.md)
- Pattern documentation (embedded in test-architecture.md)

### Phase 2: Shared Infrastructure ⏳ NEXT SPRINT (6-8 hours)
- Create pyforge-testing-kit shared package
- Add pixi task: `pixi run tea-playwright-all`
- Test full cycle on pyforge-atlas

### Phase 3: Fleet Deployment 📋 2-3 WEEKS (30 min execution)
- Run script on all 8 stations (atlas, doctor, herald, marshal, mason, scribe, steward, warden)
- Verify consistency
- Update dashboard with test-architecture column

### Phase 4: Development Integration 🚀 ONGOING
- Each station implements stories with tests
- CI gates enforce coverage (unit >80%, integration >70%, e2e)
- Dashboard tracks test status per station

---

## The Metrics (Success Looks Like)

**Per Station:**
- ✅ test-architecture.md generated (risk assessment, test matrix, scenarios, gates)
- ✅ tests/ directory scaffolded (fixtures, unit, integration, e2e, performance)
- ✅ playwright.config.ts + pytest.ini created
- ✅ First story team develops with tests (pytest + Playwright)
- ✅ CI gates passing (unit >80%, integration >70%, e2e scenarios)

**Fleet-wide:**
- ✅ All 8 stations have test architecture (generated, not manual)
- ✅ All 8 stations use pyforge-testing-kit (no duplication)
- ✅ All 8 stations pass same quality gates (consistent standard)
- ✅ Dashboard shows test-architecture status per station
- ✅ Deployment of test architecture to any new station takes <5 minutes

**Quality:**
- ✅ False-negative rate: 0% (no shipping bugs because tests missed them)
- ✅ False-positive rate: <5% (not slowing down development with flaky tests)
- ✅ Coverage growth: Stories increase test coverage as they're implemented
- ✅ Operator confidence: Every shipped feature is verified by systematic tests

---

## Fleet Completeness Tracking

| Project  | **DREAM** | Decks | **SPEC** | Research | Brief | **PRD** | **ARCH** | **EPIC** | **STORY** | **TEST** | Dev Status |
|----------|-----------|-------|----------|----------|-------|--------|----------|----------|-----------|----------|------------|
| herald   | ✅        | ✅    | ✅       | ✅       | ✅    | ✅     | ✅       | ✅       | ✅        | ✅       | 🚀 Coding  |
| atlas    | ✅        | ⏳    | ✅       | ✅       | ✅    | ✅     | ✅       | ✅       | ✅        | ⏳       | 🏗️ Ready   |
| doctor   | ✅        | 📋    | ✅       | ✅       | ✅    | ✅     | ✅       | ✅       | ✅        | ⏳       | 🏗️ Ready   |
| marshal  | ✅        | 📋    | ✅       | ✅       | ✅    | ✅     | ✅       | ✅       | ✅        | ⏳       | 📋 Queued  |
| mason    | ✅        | 🎯    | ✅       | ✅       | ✅    | ✅     | ✅       | ✅       | ✅        | ⏳       | 🎯 Next    |
| scribe   | ✅        | 🎯    | ✅       | ✅       | ✅    | ✅     | ✅       | ✅       | ✅        | ⏳       | 🎯 Next    |
| steward  | ✅        | 🎯    | ✅       | ✅       | ✅    | ✅     | ✅       | ✅       | ✅        | ⏳       | 🎯 Next    |
| warden   | ✅        | ⏳    | ✅       | ✅       | ✅    | ✅     | ✅       | ✅       | ✅        | ✅       | 🏗️ Ready   |

### BMAD-Standard (Required)

- **DREAM** (Tier 0 — mandatory)
- **SPEC** (bmad-spec output)
- **PRD** (bmad-prd output)
- **ARCH** (bmad-architecture output)
- **EPIC** (bmad-create-epics-and-stories output)
- **STORY** (bmad-create-epics-and-stories output)
- **TEST** (bmad-tea-playwright output)

### Project-Specific (Optional)

- **Decks** (Herald deck family)
- **Research** (bmad-market-research AND bmad-domain-research AND bmad-technical-research output)
- **Brief** (bmad-product-brief AND bmad-prfaq output)
- **Dev Status** (Fleet implementation tracking)

### Legend

| Symbol | Meaning      |
|--------|--------------|
| ✅     | Complete     |
| ⏳     | In Progress  |
| 📋     | Queued       |
| 🎯     | Next         |
| 🚀     | Coding       |
| 🏗️     | Ready        |

---

## The Risks We're Mitigating

| Risk | How Testing Mitigates |
|------|----------------------|
| Silent failures (webhooks don't fire, links 404, auth bypasses) | High-risk integration tests cover webhook reliability, evidence linking, auth gates |
| False-positive shipping (claims without evidence, notices without recipients) | Evidence validation tests run before each publish; round-trip tests verify data integrity |
| Cross-Moment coordination breaks (Progress + Claim race; Notice + Archive out of sync) | 3 end-to-end integration scenarios cover all major workflows |
| Performance degradation (CLI >1s, web >2s) | Performance benchmarks enforced in quality gates |
| Regression in future changes | Unit + integration tests act as regression suite; Playwright visual tests catch layout breaks |

---

## The Constraints

1. **No manual re-work per station** — automation script generates test architecture, no hand-rolling
2. **One framework, not many** — Playwright for CLI/web/integration, pytest for unit (not 5 different tools)
3. **Shared fixtures, not duplicated** — pyforge-testing-kit is the single source of truth
4. **Risk-driven, not coverage-chasing** — high-risk items get 2+ test layers; low-risk items get 1
5. **No fake passes** — tests that are flaky or incomplete are better than passing tests that miss bugs
6. **Determinism** — same input (epics + architecture) always produces same test architecture

---

## Why Now

1. **Herald is complete** — a masterpiece canonical reference that other stations can inherit from
2. **Other 7 stations are ready** — all have stories, architecture, PRDs; need test architecture next
3. **Pattern is proven** — Herald's BMAD TEA + Playwright approach works; ready to scale
4. **Automation is ready** — bmad_tea_playwright.py script is written and tested
5. **Guild doctrine is clear** — 8 Smiths, independent verdicts, Marshal owns execution; testing integrates cleanly

---

## The Outcome (In Six Months)

**All 8 PyForge stations ship with systematic testing baked in.**

- Every story includes pytest unit tests + Playwright e2e tests
- Every station passes the same quality gates (unit >80%, integration >70%, e2e)
- Every developer uses the same fixtures (pyforge-testing-kit), same patterns (9 Playwright patterns), same framework (Playwright + pytest)
- Dashboard shows test-architecture status across the entire fleet (complete/ready/pending)
- New developer onboarding: "Here's the test-architecture.md for your station; here's the pyforge-testing-kit to inherit fixtures from; now write your tests"
- Shipping a feature: Run tests locally, CI gates enforce coverage, confidence is high

**Test architecture stops being invisible. It becomes a first-class citizen.**

---

## The Guild's Commitment

> "The Guild Crew and Eight Smiths execute dreams to code through test-driven excellence. Every station owns their testing responsibility. Every story ships with systematic tests. Every feature is verified before merge."

**The Guild Testing Charter** — test-charter.md — makes this commitment real.

---

## Next Steps

1. **Adopt this dream** — commit to test-charter.md + test-architecture.md as fleet standard
2. **Create pyforge-testing-kit** — shared package with reusable fixtures (Phase 2)
3. **Deploy to all 8 stations** — run automation script, 30 min for entire fleet (Phase 3)
4. **Development teams execute** — build stories with tests, pass quality gates (Phase 4)

---

## References

- **Canonical Reference**: `_bmad-output/projects/pyforge-herald/planning-artifacts/test-architecture.md` (1,895+ lines with reusable pattern appendix)
- **Fleet Charter**: `docs/reference/test-charter.md` (Guild testing responsibility + Phase 1-4 roadmap)
- **Automation Script**: `_bmad/scripts/bmad_tea_playwright.py` (one-command-per-project generation)
- **Playwright Docs**: https://playwright.dev/
- **BMAD TEA Docs**: https://bmad-code-org.github.io/bmad-method-test-architecture-enterprise/llms-full.txt

---

## Dream Status

**Realized**: Phases 1 complete (Herald test architecture + automation + charter)  
**In Progress**: Phase 2 (pyforge-testing-kit shared package)  
**Planned**: Phases 3-4 (fleet deployment + development integration)

**The dream is real. The Guild is test-ready.**
