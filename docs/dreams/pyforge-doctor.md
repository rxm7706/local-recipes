---
title: Doctor — one bedside manner for the whole fleet
type: dream
owner: doctor
status: specified
---

# Doctor — check the vitals, keep the ecosystem alive

## The Dream

The Physician's dream: **a factory is only as autonomous as its health checks.**
Before any run, verify the machinery is sound — a missing engine or broken
config fails fast, never mid-build. After anything ships, keep a finger on the
fleet's pulse: staleness, new advisories, upstream abandonment — surfaced as
signals, not surprises. And never stop at a finding: every diagnosis names its
root cause and ships an **ordered prescription** — what to patch, upgrade, or
retire, in what order. Over time, the fleet's overall condition should be
readable at a glance, not reconstructed by hand from five CLIs.

## What it looks like when real, today (v1)

- `doctor check --env --engines` — pre-flight before Marshal spins the factory.
- `doctor monitor --fleet --watch staleness,cve` — the continuous pulse (default
  two highest-signal axes; more addable per invocation).
- `doctor diagnose --target … --prescribe` — partitioned, ranked findings with a
  named root cause for each.
- `--json` on every verb, one schema-versioned `DoctorReport` envelope.

## Why this is a consolidation, not an invention

The instruments already beat inside the factory — Doctor is one bedside manner
over all of them, not a new detection engine:

- **warden · self-check**: the engine-availability doctor check, wrapped as a
  library import (never a subprocess reimplementation).
- **atlas · health & watch**: `feedstock-health`, `staleness-report`,
  `behind-upstream`, `cve-watcher`, `release-cadence` — MCP-first with CLI
  fallback.
- **The one genuinely new instrument**: a credential/environment-hygiene check
  (the `JFROG_API_KEY` unconditional-injection pattern is exactly a Doctor
  finding) — deliberately the *only* new detection capability v1 adds, not a
  precedent for adding others without a matching decision.

## The frontier — named, not yet built

Four capabilities sit outside v1's boundary on purpose — the PRD's own
non-goals name them as "a possible v1.x addition, not a v1 commitment" rather
than rejecting them outright. Real, wanted, deliberately sequenced after the
walking skeleton proves itself:

1. **Health scoring** — a composite grade (A–F) synthesizing Doctor's own
   already-gathered findings across axes (age, staleness, CVE exposure,
   abandonment signal). Not a new scanning engine — a new aggregation layer
   over data Doctor already collects, so it doesn't reopen the "no new
   instruments" boundary v1 draws.
2. **A persistent fleet-health surface** — today's `monitor --fleet` is a
   point-in-time CLI/JSON snapshot; a tracked, at-a-glance view of the whole
   fleet's condition is the natural next step once the snapshot format has
   proven itself in practice.
3. **An adoption-tracking axis** — cf_atlas's `adoption-stage` and
   `version-downloads` signals are named as candidate sources in this Dream's
   own original draft but never made it into `monitor --fleet`'s wired axis
   set. Real, cited, unbuilt.
4. **Safe upgrade-path recommendation** — `--prescribe` ranks and names a root
   cause today, but stops short of naming a target version. A narrow,
   single-hop "here is the next safe version" suggestion (not a full
   transitive dependency-graph resolver — that stays explicitly out of scope)
   is the natural extension once ranking is trusted.

## Why this is different from a fabricated dream

An earlier, separate dream (`pyforge-doctor-dependency-health.md`, created
2026-08-02) proposed most of this same frontier, but inside a bulk commit
later found to contain fabricated content elsewhere (a false migration note,
boilerplate test-architecture docs invented for six stations). Its four
genuinely new items — health scoring, the persistent dashboard, adoption
tracking, and upgrade-path recommendation — survived verification against
Doctor's real, already-authored PRD and are captured above, in Doctor's own
voice and grounded in Doctor's own existing constraints (never a new scanning
engine, never a real graph resolver). The other two-thirds of that dream —
"multi-axis A–F scoring... validated against 1000+ real packages," "95%+
obsolescence catch rate," "80%+ operator acceptance" — were invented precision
with no grounding anywhere in this project's real work, and do not carry
forward. That dream is archived; this one is the real record.

## Realization log

- **2026-09-19 (night)** — **Proposed: the documentation is right, and refreshing it is repeatable
  — by the change that invalidated it, not by a campaign.** Seeded at the review of PR #1529 (a
  parallel session's "persona-based documentation" PR: 14 authored pages, 130 identical
  `README.md` stubs inside skill directories, a `docs-map-hygiene` source that reds on 44 files
  because it scans everything `docs/MAP.md` itself excludes, ten Spec baselines re-stamped on
  content-free memlog lines, a 32-line hand-written Spec filed as a story spec whose CAP-82 /
  Epic 29 collided with the ones minted an hour earlier). The research that fixed the shape:
  `planning-artifacts/research/documentation-currency-and-repeatable-refresh-2026-09-19.md`.
  What the estate already owns: the Diátaxis map with a scope contract (CAP-63/64, `docs/MAP.md`
  § *Outside this map*), `general-docs-consistency` (warn-only, fail-open — CAP-62's posture for
  docs detectors), and two generator + stamp + detector exemplars (`library-llms-full.md` +
  `llms-full-check`; herald's `facts.yaml` + `deck-facts`). What it lacks: any enforcement of the
  map, any notion of which pages are *generated* from a source of truth versus *authored*, and any
  currency signal for authored prose — which is why the PR's own pages shipped with dead paths, a
  non-existent CLI grammar and "fleet-picture reads the Tier-3 ledgers". Operator rulings the same
  night: remove the 130 READMEs (the installer regenerates and retires those dirs — 71 deletions in
  the 6.10→6.11 upgrade alone; no harness reads a README there); the registry is a `docs/map.yaml`
  machine twin of `MAP.md`; doctor owns the chain end-to-end (it owns CAP-48..65 already); keep the
  14 pages, corrected and registered with `sources:`. Decomposed the same night as **CAP-83** (the
  map is enforced within its own scope — missing link = fail, unmapped quadrant page = warn, the
  four quadrants only, index pages exempt; Story 30.1, landed with the PR) and **CAP-84** (documentation
  currency: `docs/map.yaml` registry with `kind: generated | authored | pointer`, `owner`, `sources`,
  stamps; generators for the pixi-task reference, the station CLI cheat sheet, the detector table
  and the skills catalog; a `docs-currency` source that reds a stale generated page, a stale
  authored page — a named source moved past `verified:` or a path/command in it no longer resolves —
  and a stray file in a managed skill dir; warn first, ratcheted to fail per check; the
  `bmad-os-docs-audit → bmad-os-diataxis` pass as the authored-page refresh, triggered by the
  finding; Stories 30.2–30.3, `backlog`).
- **2026-09-19 (evening)** — **Proposed: the sibling drift check records a per-Dream human
  acknowledgement, and knows where the sibling went.** The moment a `GH_TOKEN` reached the
  sibling (the operator's `.bashrc` now exports one from `gh auth token`), CAP-71 reported six
  Dreams diverging on status / content_hash / title: `django-accelerator-framework`,
  `enterprise-data-models-and-apis`, `miniforge-installer`, `package-inventory-eligibility`,
  `pixi-container-image`, `reusable-cicd-workflows`. All six are `archived` here — folded into
  their station Dreams on 2026-09-17 — while the sibling still holds the pre-fold copies
  (`status: dreamt`, untouched since 2026-08-13; the whole sibling repo has not been pushed to
  since 2026-08-24). The Spec's own constraints settle the direction — read-only, never a sync
  engine, their prose unlicensed, reconciliation human and per-Dream — so the answer is an
  acknowledgement, not a push. Two gaps: (1) there is no way to *record* that acknowledgement, so
  the six re-fire on every run and will drown a genuine later change; a `sibling-acknowledged:
  <sibling content_hash>` line on the local Dream should silence exactly that hash and re-fire on
  any other, and a locally `archived` Dream without one should say so in the finding. (2) The
  sibling moved: `OpenTeams-WFT-CDO/mgmt-wf-python-modernization` now 301-redirects to
  `openteams-ai/mgmt-wf-python-modernization`; `sibling_dreams.py` hard-codes the old owner and
  works only while GitHub keeps redirecting. Decomposed the same day as **CAP-82 / Epic 29 /
  Story 29.1** (doctor `DW-OPS-2026-09-19-6` carries the six as the acceptance fixture).
- **2026-09-18 (night)** — **Proposed: a frontmatter reader that stops at the
  first `---` it sees.** `sources/chain.py::_frontmatter_parse` splits a spec on
  the first `---` *anywhere in the file*, not on a line-anchored fence. Marshal
  Story 50.5's tracked spec quotes a `"---"` fence inside its first deferral's
  `evidence:`, so the YAML was cut mid-scalar, `yaml.safe_load` still returned a
  mapping, and the detector saw one deferral where two exist: the first lost its
  `location:` (and so its fingerprint, `fdd6bce25c09` for `3bc3d91bdf95`), the
  second — severity *high* — was invisible to `deferred-work` and to
  `deferred_work_intake.py`, which reported "all 118 already in tracked ledger."
  Every doctor source that reads frontmatter through this helper (spec status,
  deferrals, surface, ownership) inherits the same silent truncation, and a
  quoted fence is ordinary in any spec about frontmatter. Reconciled by hand
  tonight (DW-FU-50-5 rewritten in full-parse form, DW-FU-50-6 added). The
  fix is a line-anchored fence split (marshal's `promotion.py`/`spec_surface.py`
  already parse this way after 50.5); it is `spec-pyforge-doctor` surface, so it
  waits for its CAP and Story rather than a night-time patch. Same family as
  CAP-80's lesson: a reader that degrades silently is worse than one that
  refuses. **Decomposed 2026-09-19** as CAP-81 / **Epic 28**, Story 28.1 (27.4
  stays a reserved hole); the same helper's second defect — `if "---" in text:
  return {}, True` marks any prose file with a horizontal rule as unparseable
  frontmatter — is in the CAP's success.
- **2026-09-19 (afternoon)** — **Proposed: a hollow landing is invisible to every Doctor
  instrument.** Marshal Story 51.3 landed as PR #1501 with a branch diff of one file, +2/−1
  (its own tracked spec's status flip), and finalize promoted `51-3 → done`; `story-status`
  reported ok (the merge subject `Merge pyforge-marshal/51-3 into main` exists),
  `status-body-consistency` never compares a tracked spec's frontmatter `status:` to its
  ledger row, and `sources/ledger.py` attributes by subject alone. Two readers are missing:
  a landing-evidence route that checks the merge's first-parent diff touched the story's
  declared Surface (or any path outside `specs/spec-<key>*.md`), and a tracked-spec-status
  vs ledger-row cross-check. Both are `spec-pyforge-doctor` surface — the next `bmad-spec`
  pass. Same day, from 28.1's own review: `status_body_consistency._parse_frontmatter` is a
  verbatim pre-CAP-81 copy (DW-FU-28-1), `factory.py`'s pin-scope extractor splits the same
  way (DW-FU-28-1-2), and a docs-only PR that flips a live-repo test never fires the station
  lane (found on #1493/#1494).
- **2026-09-18 (later still)** — **Corrected: the atlas rows were a rekey, not a
  sibling.** Story 27.1 landed (PR #1471) with both halves of CAP-78 real —
  `ledger-regression` judges a PR at its merge-base, and the merge-history
  sources read each station's own `merge_subject_template` — but its dispatched
  session refused, correctly, to claim the second symptom: atlas's 13-5 / 14-4 /
  15-3 `landed-but-unpromoted` rows come from atlas's *own* bmad-loop merges
  read with pre-rekey keys (`rekey-2026-09-17.md`: 13-5→12-5, 14-4→13-4,
  15-3→14-3), which `gather_direction` cannot map because only `gather()` was
  made rekey-aware (Story 25.3). The entry below overstated the cause; CAP-78's
  success is corrected and the real fix is CAP-79 / Story 27.2. And one thing
  27.1 broke by doing exactly what CAP-78 said: reading only a station's
  *current* template orphans the merges it landed under the old one — marshal
  `34-3` (`Merge 34-3 into main`, 2026-09-12) read as `done` with no merge
  anywhere the moment marshal's policy moved to `Merge pyforge-marshal/{key}
  into main`. CAP-80 / Story 27.3: the legacy form counts for a station for the
  keys its own ledger knows, and for nothing else.
- **2026-09-18 (later)** — **Proposed: a PR is judged at its merge-base, and a
  merge subject is attributed to the station it names.** Twice today Doctor's
  merge-history sources reported a regression that was not one. (1) `ledger-
  regression` ran on herald PR #1465's `detectors` lane at 18:17Z — two minutes
  *after* `marshal factory dispatch` had merged the PR unattended and promoted
  `23-6 → done` on `main` — and compared `origin/main..HEAD`: the PR head still
  said `backlog`, main now said `done`, so the blocking step reported
  `done-key-regressed: pyforge-herald: 1 story key(s) moved out of done` and
  redded the lane on a PR whose branch never touched that row. The question a
  PR check must answer is "what does this branch change?", which is the ledger
  at `merge-base(origin/main, HEAD)` vs `HEAD` — the tip of `main` is the wrong
  base whenever main moves first, and under unattended landing it always moves
  first. (2) `ledger-direction` has reported `pyforge-atlas/13-5`, `14-4` and
  `15-3` as *landed-but-unpromoted* all day: `sources/marshal.py:87` hardcodes
  `_MERGE_SUBJECT_TEMPLATE = "Merge {key} into main"`, so another station's
  `Merge 13-5 into main` reads as atlas's 13.5 landed — the same un-scoped
  templated shape marshal's own supervisor tripped on this morning (herald
  23.x via atlas's `Merge 23-N into main`; marshal is closing its side as
  `spec-pyforge-marshal:CAP-247` and station policies now render
  `Merge <slug>/{key} into main`). Doctor's sources must read each station's
  own `merge_subject_template` from its `marshal-policy.toml` — a TOML read,
  never a marshal import — and accept only a subject whose slug is that
  station's. Seeded as CAP-78, decomposed the same day as Epic 27 / Story 27.1;
  advisory posture unchanged, and `ledger-regression` stays the one blocking
  Doctor step in CI (ruling 2026-09-14) — this makes its verdict true, not softer.
- **2026-09-18** — **Proposed: the map of what no agent can verify without a
  live proof.** Bugs cluster where agents cannot see them — not because the
  code is hard, but because verifying it correct needs a real round-trip
  against something outside the repo (a third-party API, a live browser, a
  service with its own auth and its own drift), and a dev pass's own
  self-report is never evidence of that, only a live proof is. This fleet
  already has several such surfaces, each documented only in its own
  station's prose, nowhere aggregated: herald's Claude Design MCP bridge (a
  push isn't proven until read back through the live serve URL, harness
  stripped, byte-compared), herald's live webhook host (opt-in only,
  `HERALD_LIVE_WEBHOOK=1`, never in the default gate), scribe's
  Postgres+pgvector cluster (`scribe-pg-up` first), atlas's
  Chromium/DuckDB/WASM pipeline, warden's live OSV-scanner/CISA-KEV/EPSS
  feeds. Every one already has a real, working live-proof mechanism; what's
  missing is one place that says *these exist, here's how to actually prove
  them, and a dev pass's own confidence is not enough evidence on its own.*
  Motivating incident, same session: herald's mcp SDK transport broke across
  two separate 2.x changes (`streamablehttp_client` renamed with a different
  call signature; `CallToolResult.isError` renamed to `.is_error`), caught
  by neither review nor the test suite nor a dev pass's self-report — only a
  real live push-then-read-back against Claude Design surfaced it. Shape:
  one doctor-owned, fleet-wide inventory of these surfaces (station, surface,
  what a static pass cannot see, how to prove it live, roughly how
  expensive); a story/PR touching one gets an advisory finding naming it,
  never gating, matching Doctor's own posture. Not yet a CAP or an Epic —
  recorded here as the seed; decomposition follows if greenlit.

- **2026-08-08** — **Doctor took the verdict on the Marshal's own row.** Charter §6
  has said since 2026-07-28 that the Doctor holds it, *"the one station that would
  otherwise grade itself"* — but nothing implemented it. A single `sprint-ledger-sync`
  run then destroyed 96 `done` markers across four stations and printed success, and
  all three guards written in response lived in Marshal's own surface. Doctor gained a
  ninth Source (`marshal-durability`), CAP-9, FR-14, AD-11/AD-12 and Epic 5. The
  design point worth remembering: unlike the warden source, this one **imports no
  station package** — a durability verdict assembled from the judged station's own
  code would fail exactly when that station's machinery is what broke.

- **2026-07-23** — persona defined in [[pyforge-charter]]; chapter deck seeded
  (`presentations/pyforge-doctor/`).
- **2026-07-25** — full planning chain landed: Spec (CAP-1..CAP-4), PRD
  (FR-1..FR-9), Architecture (AD-1..AD-7), Epics (3 epics, 12 stories).
- **2026-08-02** — Epic 1 shipped (5/5 stories: package scaffold, warden
  engine-check wrap, tri-state checks, credential/env-hygiene check, CLI
  wiring). Epics 2 (Fleet Pulse) and 3 (Diagnose & Prescribe) remain pending,
  7 stories. Dream consolidated same day: the fabricated `dependency-health`
  dream retired, its real remainder (four frontier items above) captured here
  and decomposed into a genuine Epic 4 (CAP-5..CAP-8, FR-10..FR-13) rather
  than left as an unlinked aspiration.

## Fold — one chain (2026-09-17)

Doctor rebases to one Dream, one Spec, one PRD, one spine, one epic chain. Folded topic Dreams are archived in place with `Consolidated into [[pyforge-doctor]]` banners. Absorbed Spec folders keep pointer + memlog + companions.

Folded Dreams: [[bmad-drift-new-artifact-shape]], [[bmad-method-version-drift]], [[capability-effect-check]], [[chain-currency-sweep]], [[deferred-work-audit-completeness]], [[deferred-work-resolution-sweep]], [[deferred-work-visibility]], [[docs-shelf-alignment]], [[fleet-hygiene-verification-exemplar-program]], [[general-docs-consistency]], [[pixi-candidate-currency]], [[pyforge-doctor-dependency-health]], [[sibling-dreams-drift]], [[status-body-consistency]].
