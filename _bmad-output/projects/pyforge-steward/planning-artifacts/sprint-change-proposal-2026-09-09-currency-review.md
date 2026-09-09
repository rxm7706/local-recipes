---
title: Sprint Change Proposal — currency review and the realization gate (Epics 48–49)
date: 2026-09-09
project: pyforge-steward
chain: spec-pyforge-unifying-strategy
status: approved — operator 2026-09-09: "Approve; Unifying now, re-home later; merge now before any 44.x flip"
trigger: Currency review (research/currency-review-pyforge-unifying-strategy-2026-09-09.md) + Dream § "Where next — the unification strategy at 2026-09-09"; operator ruling 2026-09-09 retiring the ≤400-line constraint
mode: batch
scope: moderate
operator: Rxm7706
supersedes_none: true
follows: sprint-change-proposal-2026-09-05-ad-1-reopen.md
---

# Sprint Change Proposal — currency review and the realization gate (Epics 48–49)

## 1. Issue summary

Four parallel audits against `main` `fe4025ea90` (384 commits, 13 PRs since the Dream's last
substantive update) found the code healthy — 28/28 detectors, roster 40/40 measured live, the query
plane end to end, both red-team CRITICALs fixed — and the document tier stale in ways the Dream-tier
corrections of the same day could not bind. Three of those findings are contractual and one is a
live hazard:

1. **A live hazard the chain's own instructions route the operator into.** The Dream (now
   withdrawn) and `AGENTS.md:49` both mandated `sprint-ledger-sync --repair-feed` before any ledger
   write. `scripts/promote_sprint_status.py:91` guards only `done`; `blocked` is "deliberately NOT
   guarded" (`:88-90`). The Tier-3 feed holds all 15 Epic 44 rows at `backlog` (mtime Sep 7, before
   the Sep 8 restore); the tracked twin holds 14 at `blocked`. `--repair-feed` writes the feed's
   values over the twin and sets `lost = []`, bypassing the refusal. **A bare sync is no safer:**
   `main()` computes `missing` but acts on it only under `--repair-feed` (`:232-233`), so with `lost`
   empty it falls through and writes the feed over the twin — dropping twin-only keys and
   un-blocking the 14 rows. The only thing protecting the gate on either path is the accidental 47.5
   divergence (`done` in twin, `blocked` in feed). This already fired once via the generator
   (`be0a29b320`, 2026-09-06; open two days; `f527e526f0` fixed the generator only). The three
   un-gated stories are 44.3 (creates a repository), 44.9 (external PRs), 44.10 (archives this repo).
2. **`open_questions: []` / "Residual: none" is false.** `DW-RT-2026-09-02-2..6` (R-18..R-22) are
   `open`, dispositioned "Epic 45 candidate" — a slot eval-quality occupies. The Single-Spec merge
   has no story since 2026-09-01. Story 43.7 is `backlog` and unknown to the Dream.
3. **Six CAPs read `done` while their named success criterion is unexercised** (CAP-4, -7, -11,
   -12, -14, -17). The estate-wide pattern — token economy 24/24 `done` with every layer off,
   adaptive-model-tiering `realized` and unfed — is the Dream's new § *Where next* finding:
   **shipped is not in effect**, because the chain's definition of done verifies mechanism, never
   effect.
4. **The CAP namespace collapsed at ~185 sites.** `b8b142db63` normalised the AD and FR axes and
   never touched CAP (68 in the foundry spine, 61 in the bmad-suite spine, 9 in
   secure-live-dashboards, 34 in Epics 45–47).
5. **Operator ruling 2026-09-09:** the ≤400-line living-Dream constraint (`SPEC.md:488`, from 43.1)
   is retired — "not helpful for a detailed evergreen strategy that drives the future of pyforge".
   The Dream records it in Grounding; this proposal amends the Spec.

## 2. Change-navigation checklist (recorded)

| # | Item | Status | Finding |
|---|---|---|---|
| 1.1 | Triggering story | Done | None; trigger is the review + Dream § Where next. Root causes span the syncer (`scripts/`), shipped Epics 21/23/24/26/28/34 (the six CAPs), the 2026-09-08 normalisation pass, and the Spec's own frontmatter. |
| 1.2 | Problem type | Done | Mixed: *technical limitation* (syncer guards only `done`), *misunderstanding of done* (mechanism ≠ effect), *documentation drift* (residual, namespace, floor), *strategic pivot* (operator retires the length constraint; the realization gate becomes the definition of done). |
| 1.3 | Evidence | Done | Review § 0–1 with file:line for every claim, each re-verified by the reviewing session; Dream § Where next table of nine instances. |
| 2.1 | Current epics completable | Done | Epics 18–47 unchanged; nothing reopened. Epic 44 stays `blocked` as gated. 44.2's scope shrinks by the two `SPEC.md` floor lines this proposal fixes directly. |
| 2.2 | Epic-level change | Done | **Add Epics 48 and 49.** 48 = the chain tells the truth (syncer, residue, namespace, merge). 49 = shipped becomes in effect (the realization gate + six effect stories). Two epics, not one: 49's *home* is an open operator decision (§ 3). |
| 2.3 | Remaining epics | Done | Epic 44: Order gains "Epic 47 P1–P18 green" before 44.3 (already in the Dream; epics.md paragraph updated here). 44.5 already carries `S-14.9` (47.5). Marshal Epic 33 (token economy) is cross-referenced, minted by marshal's own correct-course. |
| 2.4 | Obsolete / new | Done | Nothing obsolete. New: 48, 49. |
| 2.5 | Order / priority | Done | **48.1 first** (safety, hours). Then 49.1–49.2 (they define the gate) ∥ 48.7 ∥ 48.2–48.6. Then 48.8 before any 44.x flip. Then 49.3–49.8. All drain in `local-recipes`; none waits on foundry. |
| 3.1 | PRD conflicts | Done | None. No FR added; the realization gate is a definition-of-done discipline, not a requirement. § 14 gains a dated paragraph (precedent). |
| 3.2 | Architecture conflicts | Done | None to the canopy/foundry/suite spines. Story 49.1's verified column is a Spec shape, not an AD. If the operator homes the gate on `hub:`, that Spec's own spine carries it. |
| 3.3 | UI/UX conflicts | N/A | None. |
| 3.4 | Other artifacts | Done | `scripts/promote_sprint_status.py` + its regression test (48.1); `AGENTS.md:49` via `bmad-project-context` refresh (48.1, managed block); `marshal-policy.toml [epic_surfaces]` "48"/"49"; deferred-work ledger dispositions; `sprint-status-ledger.yaml` **via `sprint_plan.py generate` only — never via sync until 48.1 lands**. |
| 4.1 | Option 1 Direct adjustment | Done | **Chosen.** Additive: two epics, one constraint amendment, one residual block, two factual floor fixes. |
| 4.2 | Option 2 Rollback | Done | Rejected. Nothing shipped is wrong; it is unexercised. |
| 4.3 | Option 3 MVP review | Done | Rejected. No scope reduction; the opposite — effect becomes part of scope. |
| 4.4 | Path forward | Done | Direct adjustment, moderate scope. |
| 5.x | Proposal components | Done | § 3–5 below. |
| 6.x | Review | Done | Batch mode; presented whole. |

## 3. Recommended approach

**Direct Adjustment, scope moderate.** Two epics, sixteen stories, all `backlog` (none is
outward; none flips a `blocked` key). Dispatch 48.1 alone and first.

| Epic | Stories | Binds | Depends on |
|---|---|---|---|
| **48 The chain tells the truth** | 48.1 syncer guards `blocked` + missing keys · 48.2 R-18 sizing · 48.3 R-19 network baseline · 48.4 R-20 secrets profile · 48.5 R-21 observability contract · 48.6 R-22 live streaming (implement or delete the pillar) · 48.7 CAP-axis namespace pass · 48.8 Single-Spec merge | `DW-RT-2026-09-02-2..6`; review § 0, § 1.2, § 1.3; Dream Grounding "Single-Spec merge — parked" | none; 48.1 has no deps and gates every later ledger write |
| **49 Shipped becomes in effect** | 49.1 the verified column on every CAP · 49.2 the effect check (doctor, advisory) · 49.3 CAP-4 effect · 49.4 CAP-7 effect · 49.5 CAP-11 effect · 49.6 CAP-12 effect · 49.7 CAP-14 effect · 49.8 CAP-17 effect | review § 1.4; Dream § Where next "The realization gate" | 49.1 → 49.2 → 49.3–49.8 |

**Why two epics.** Epic 48 is bookkeeping the chain owes itself and can drain now. Epic 49 is a
*policy*: it changes what `done` means. The Dream proposes it lands as `hub:CAP-*` on
`spec-intelligence-hub` (the accountability plane made concrete), which needs the operator's
reading of "align" first. So 49 is minted here on the Unifying chain as the vessel, with its
**binding home an explicit open question** — if the operator chooses `hub:`, 49's stories re-home
by memlog without changing their text. Minting them now means the six unexercised CAPs stop hiding
behind `done` today.

**Why not fold the six CAPs into 44.2 or the existing epics.** Those epics are `done`. Reopening
shipped epics for effect work would say the mechanism was wrong; it was not. Effect is new work.

**Effort / risk.** 48.1 S (two guards + a test; the regression test at
`test_promote_sprint_status_regressions.py:55` pins the bug and is rewritten). 48.2–48.6 M each
(real platform work; 48.6 is a decision story — R-22's own text says "or delete the pillar"). 48.7
S (mechanical, scoped by satellite range). 48.8 M (copy `pap:CAP-*` text, retarget Epics 10–12,
supersede the parent — never renaming the pixi env). 49.1 S (docs), 49.2 S (a doctor source
reading 49.1's column), 49.3–49.8 M each. Risk Medium, concentrated in 49.3 (MCP `start`/`get` on
six more stations), 49.6 (IdP claims on a hot path), 49.8 (marshal publishing into the host —
shares the seam with marshal Epic 33's Track).

## 4. Detailed change proposals

### 4.1 `spec-pyforge-unifying-strategy/SPEC.md`

**(a) Constraints — amend `:488`.**

OLD: `- **Always:** the living Dream is ≤ 400 lines and every diagram in it is a build target (43.1).`

NEW: `- **Always:** every diagram in the living Dream is a build target (43.1). **Amended 2026-09-09 (operator):** the line count is not a constraint on the living Dream — a detailed evergreen strategy outranks a short one; the archive holds historical topology only. \`historical-section-too-long\` keeps that meaning, never a length cap.`

Rationale: operator ruling; the cutover Spec's assumption (`:189`) already said the overage was by
design, so two Specs disagreed about one rule.

**(b) Constraints — append a dated block** `### Correct-course 2026-09-09 — currency review`:

- **Always:** a ledger sync never moves a `blocked` story off `blocked` and never drops a key
  the tracked twin holds; the twin's `blocked` is sticky in both `sprint_plan.py` and
  `promote_sprint_status.py` (48.1). **Never:** `--repair-feed` as a pre-write ritual until 48.1
  lands.
- **Always:** every capability in this Spec carries a `**verified:**` line naming which clause of
  its success criterion has a live exercise and which is fixture-only (49.1). **Never:** a Dream
  flips to `realized` on ledger bookkeeping; it flips on effect (Dream § Where next).
- **Always:** cross-spine CAP citations are qualified (`fnd:`, `suite:`, `sld:`, `pap:`, `hub:`)
  exactly as ADs and FRs are; bare `CAP-n` means Unifying (48.7).

**(c) Constraints `:315` and inherited table `:73` — factual floor fix.**

OLD: `Django \`>=5.2.15,<6\` and Python \`3.12.*\`` (both sites)
NEW: `Django \`>=5.2.17,<6\` and Python \`3.14.*\`` (both sites), with a trailing `(43.6, 2026-09-03; corrected 2026-09-09)`.

Rationale: pure drift, contradicted by the Dream, the measured matrix and `pixi.toml` at every pin
site; 44.2 is `blocked` and its scope never covered `SPEC.md`. The Django bump landed `daa35ee171`.

**(d) Replace "Residual: none" (`:52-53`) with a dated `## Residual (2026-09-09)` section** before
§ Open Questions:

- R-18..R-22 (`DW-RT-2026-09-02-2..6`) → Epic 48 Stories 48.2–48.6 (were "Epic 45 candidate").
- Single-Spec merge → Story 48.8 (parked since 2026-09-01; due before the cutover's regeneration
  drill consumes the `extends:` chain).
- Story 43.7 `backlog` (sidecar runtime validation on 3.14; added 2026-09-08).
- Six CAPs with unexercised named criteria → Epic 49 (CAP-4, -7, -11, -12, -14, -17).
- Three false statements corrected: `:346` and `:624` ("no `GraphStore` class") → it exists with
  three drivers; `resilience-invariants.md:103-104` (BS-5 `read_only=True` absent; BS-6 no
  CloudEvents envelope) → both ship.

**(e) Frontmatter.** `open_questions: []` → two entries: `realization-gate-home` ("Epic 49 binds on
this chain or re-homes to `hub:CAP-*` on `spec-intelligence-hub` — the operator's reading of
'align' decides"), `single-spec-merge-timing` ("48.8 now, or let foundry's regeneration consume
`extends:` — the Dream has called for a named story since 2026-09-01"). `updated:` → 2026-09-09.
`companions:` gains the currency review.

### 4.2 `epics.md` — Epics 48 and 49 (appended before the currency notes)

Heading and story shape mirror Epic 47. Ledger keys minted by `sprint_plan.py generate` only.

**Epic 48: The chain tells the truth (spec-pyforge-unifying-strategy Residual 2026-09-09)**

- **48.1 The ledger syncer guards `blocked` and missing keys.** Type fix · S · Deps — ·
  Surface `scripts/promote_sprint_status.py`, `src/shared/packages/pyforge-marshal/tests/unit/test_promote_sprint_status_regressions.py`, `AGENTS.md` (§ Running and verifying, via `bmad-project-context` refresh — managed block), Dream § Cutover Order line.
  Given a twin row `blocked` and the same key `backlog` in the feed When any sync runs (bare or
  `--repair-feed`) Then the twin's `blocked` survives (a `STICKY_STATUSES` set mirroring
  `sprint_plan.py:77`), and a key present in the twin but absent from the feed is restored or
  refused — never silently dropped — on the bare path too. And the regression test that pinned
  `TERMINAL == {"done"}` is rewritten to assert both guards with fail-without cases; and the
  `AGENTS.md:49` instruction is corrected through `bmad-project-context`, never by hand.
- **48.2 R-18 sizing rewrite.** Type feat · M · Deps — · per-pod requests/limits for web, worker,
  mcp-host, DB-GPT sidecar, Liquibase Job, Vizro; HPA on web and worker; PodDisruptionBudgets; LLM
  inference stated external. Closes `DW-RT-2026-09-02-2`.
- **48.3 R-19 network baseline.** Type feat · M · default-deny NetworkPolicy with explicit allows;
  `automountServiceAccountToken: false`. Closes `-3`.
- **48.4 R-20 secrets profile.** Type docs+feat · M · age key custody and rotation; an
  `ExternalSecret` example for the Vault/ESO profile; rotation runbook for `DJANGO_SECRET_KEY`,
  `REDIS_PASSWORD`, DB roles, the assertion PEM (dual-key verify). Closes `-4`.
- **48.5 R-21 observability contract.** Type feat · M · SLOs for `/ht/`, MCP p99, queue age, event
  lag; alert rules; a metrics write path for Doctor's flag kill-switch. Closes `-5`.
- **48.6 R-22 live browser streaming — implement or delete the pillar.** Type decision+feat · M ·
  `/ws/events/` as a Channels consumer over redis-broker Streams with per-`sub` filtering, **or**
  the Dream's pillar deleted with a dated ruling. Closes `-6`.
- **48.7 The CAP-axis namespace pass.** Type docs · S · Deps — · Surface `ARCHITECTURE-SPINE.md`
  satellites (foundry 578–896 → `fnd:`; bmad-suite 1426+ → `suite:`; secure-live-dashboards →
  `sld:`), `epics.md` Epics 9, 39, 45–47, the Dream's five sites already fixed. Given
  `b8b142db63`'s AD/FR convention When the same pass runs on the CAP axis, scoped by satellite range
  Then no non-canopy satellite cites a bare `CAP-n`, the six double-prefix artifacts and two
  space-form stragglers are cleaned, and the AD-citation check gains the CAP form.
- **48.8 The Single-Spec merge.** Type docs · M · Deps — · copy `pap:CAP-1..6` full text into
  the Unifying SPEC, retarget Epic 10–12 citations to `pap:CAP-*` / `pap:AD-*`, supersede
  `spec-python-agent-platform` (`absorbed-into`). **Never** in the same story: rename
  `[feature.python-agent-platform]`. Dream Grounding "Single-Spec merge — parked" → done.

**Epic 49: Shipped becomes in effect (spec-pyforge-unifying-strategy — the realization gate)**

HARD boundary: no story here reopens a shipped epic or re-mints a shipped CAP; each exercises a
criterion the Spec already states. Binding home is open (§ 4.1(e)); stories re-home by memlog.

- **49.1 The verified column.** Type docs · S · Deps — · Surface `SPEC.md` § Capabilities. Given
  the review's per-CAP grading When each CAP-1..19 gains a `**verified:**` line Then it names
  which success clause has a live exercise (artifact, deployed check, measured number) and which
  is fixture-only, with file:line; eleven read fully verified today, six read partial.
- **49.2 The effect check.** Type feat · S · Deps 49.1 · Surface `pyforge-doctor` sources. Given
  49.1's column When `capability-effect-check` runs Then it reports every CAP `done` in the ledger
  whose `verified:` line names an unexercised clause — advisory, never a second PR verdict; wired
  into `detectors` beside `story-status`.
- **49.3 CAP-4 in effect.** Type feat · M · `start`/`get` on all eight stations and a disconnect
  test that actually interrupts transport across a multi-minute op (`SPEC.md:146`).
- **49.4 CAP-7 in effect.** Type feat · M · Atlas's real Vizro/BSL board reachable through the
  host under the isolation pattern, **or** the criterion rewritten to name the fixture as the
  deliverable (`SPEC.md:180`; `test_host_board_row_isolation.py:213` currently asserts the real
  board is absent).
- **49.5 CAP-11 in effect.** Type test · M · a test that fills the cache to its eviction limit and
  proves no queued task is lost (`SPEC.md:214`); HPA if 48.2 has not landed it.
- **49.6 CAP-12 in effect.** Type feat · M · `IDP_USERINFO` / claims snapshot set in the deployed
  default so revocation lands on the next *request* (`SPEC.md:222`; `base.py:214-215`).
- **49.7 CAP-14 in effect.** Type feat · M · semantic recall backed by a real model over the plane
  (not the 7-entry synonym map), **or** the criterion rewritten honestly; the dual-write decision
  recorded (`SPEC.md:234`).
- **49.8 CAP-17 in effect.** Type feat · M · marshal publishes bmad-loop run state to the
  supervisor; marshal and doctor stop reading `~/.bmad-loops` (`SPEC.md:264`). **Shares its seam
  with the Hub's Track (`hub:CAP-3` on `spec-intelligence-hub`, published by marshal Epic 33) and the token economy's savings telemetry (CAP-7)** — one publisher, landed
  together, cross-station: ledger `blocked` on marshal 33's Track story once it exists.

### 4.3 `epics.md` — Epic 44 paragraph

Append to the Epic 44 heading paragraph: "**Order amended 2026-09-09:** Epic 47's P1–P18 readiness
lines precede the operator's 44.3 flip (47's HARD boundary); 48.1 precedes any ledger write on
this project; 48.8 precedes the regeneration drill."

### 4.4 Dream — `docs/dreams/pyforge-unifying-strategy.md`

Already applied 2026-09-09 (Grounding ruling; § Where next; Realization entries; `--repair-feed`
withdrawn). This proposal adds one Realization line naming Epics 48–49 and this file.

### 4.5 PRD `prds/prd-pyforge-steward-2026-07-25/prd.md` § 14 (Canopy satellite, `:1679`)

Dated paragraph, precedent shape: "**2026-09-09 correct-course (currency review):** Epics **48–49**
bind the review's residue and the realization gate; no FR added — effect is a definition-of-done
discipline over existing requirements. The ≤400-line living-Dream constraint is retired by operator
ruling. Record: `sprint-change-proposal-2026-09-09-currency-review.md`."

### 4.6 Deferred-work ledger

`DW-RT-2026-09-02-2..6`: `status: open` → `promoted`, disposition "Epic 45 candidate" → "→ Story
48.N". `DW-CC-2026-09-04-1` (worktree residue): `status: open` → `resolved` to match its own
`verified: resolved` line.

### 4.7 `marshal-policy.toml [epic_surfaces]`

`"48"` = Epic 47's list + `scripts/**`, `AGENTS.md`, `src/platform/deploy/**`; `"49"` = Epic 47's
list + `src/platform/**`, `src/shared/packages/django-*/**`, `src/shared/packages/pyforge-marshal/**`,
`src/shared/packages/pyforge-doctor/**`, `src/shared/packages/pyforge-scribe/**`.

### 4.8 `sprint-status-ledger.yaml`

Sixteen story keys + `epic-48`, `epic-49`, two retrospectives, all `backlog` — minted by
`sprint_plan.py generate` (safe: sticky since `f527e526f0`). **Do not run `sprint-ledger-sync` in
any form until 48.1 lands**; the feed will lag the twin by these keys and that is correct.

### 4.9 `AGENTS.md:49`

Via `bmad-project-context` refresh (48.1): "Before any ledger write: `sprint-ledger-sync -- --project
<station> --repair-feed`" → "Never run `sprint-ledger-sync --repair-feed` until Story 48.1 lands;
after it, a bare sync is safe and refuses on any regression or missing key."

## 5. Implementation handoff

**Scope: Moderate** (backlog reorganization: two new epics with a stated order). Route to Product
Owner / Developer.

| Role | Responsibility |
|---|---|
| Operator (Rxm7706) | Approve / adjust Epics 48–49; decide `realization-gate-home` (Unifying now vs `hub:` after the "align" reading) and `single-spec-merge-timing`; confirm 48.1 dispatches first and alone. |
| Steward (owner) | 48.2–48.6, 48.8, 49.1, 49.4–49.6; owns every `DW-RT` entry. |
| Marshal | 48.1 (the syncer lives under marshal's tests); 49.8 jointly with Epic 33's Track. |
| Doctor | 49.2 effect check; 48.7 AD-citation check gains the CAP form. |
| Atlas | 49.4 (the real board); 49.3 (`start`/`get` reference). |
| Scribe | 49.7. |
| Developer agent (`bmad-build`) | One story per session; `BMAD_ACTIVE_PROJECT=pyforge-steward`; physical paths; **ledger via `sprint_plan.py generate` only until 48.1 lands.** |
| Warden | PR gate as usual; no second verdict. `capability-effect-check` is advisory. |

**Success criteria.** 48.1: a test proves both guards fail-without / pass-with, and
`sprint-ledger-sync --project steward --repair-feed` run against the current feed leaves all 14
`blocked` rows intact. Epic 48 as a unit: `open_questions` is honest, no bare cross-spine `CAP-n`
survives outside canopy, the parent Spec is superseded. Epic 49 as a unit:
`capability-effect-check` reports zero unexercised `done` CAPs on this chain, and the Dream's next
`realized` flip cites an artifact, not a ledger row.

## 6. Applied

Operator approval 2026-09-09 (all three recommendations): approve; `realization-gate-home` =
Unifying now, re-home later; `single-spec-merge-timing` = now, before any 44.x flip.

- `spec-pyforge-unifying-strategy/SPEC.md` — `:488` amended; `:73` / `:315` floor → `3.14.*`;
  Constraints block *Correct-course 2026-09-09*; § Residual (2026-09-09); two `open_questions`;
  `updated: 2026-09-09`; two research companions; the two false `GraphStore` sites annotated.
- `epics.md` — Epics 48 (8 stories) and 49 (8 stories); Epic 44 order paragraph.
- `docs/dreams/pyforge-unifying-strategy.md` — Realization entry (correct-course).
- PRD § 14 — dated paragraph.
- `deferred-work-ledger.md` — `DW-RT-2026-09-02-2..6` `open → promoted` (→ 48.2–48.6);
  `DW-CC-2026-09-04-1` `open → resolved`.
- `marshal-policy.toml` — `[epic_surfaces]` "48", "49".
- `sprint-status-ledger.yaml` — 16 story keys + `epic-48`, `epic-49` + retrospectives via
  `sprint_plan.py generate`; **no sync run** (see below).
- `AGENTS.md:49` — **not** applied here; it is Story 48.1's task through `bmad-project-context`.
- `implementation-readiness-report-2026-09-09-currency-review.md` — stamped by
  `bmad-sprint-planning`.

