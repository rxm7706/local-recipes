# pyforge-herald — Whole-Build Retrospective (Epics 1–12)

**Date:** 2026-08-08 · **Facilitator:** Amelia (Developer, adapted) · **Project Lead:** rxm7706
**Scope:** All 12 epics / 47 stories, from the first Dream-first bmad-spec run (`e8f8abb978`,
2026-07-25) through Epic 12's docs close-out (`58a1c6dd07`, 2026-08-08). Herald is **47/47 stories
done**, merged to `main` via PRs #111, #114, #116, and #308–#316 (plus the earlier bmad-loop
scaffold/spike commits that predate the PR-per-epic pattern: #111 for 1.1, #114/#116 for 1.2).

> **Format note.** This is a solo / AI-driven effort (bmad-loop for Epics 1–2, then a mix of
> same-agent self-review and orchestrator-dispatched Blind Hunter + Edge Case Hunter passes for
> Epics 1 close-out through 12). The retro's substance is run faithfully against the real
> Review Triage Logs in all 47 story specs; no team dialogue is fabricated.

## 1. Summary

Herald shipped two genuinely different products under one name. **Epics 1–5** (17 stories) are
the `herald deck` bridge CLI — seed/pull/status/watch/push against Claude Design's MCP surface,
the actual "Moment 1: Pitch" mechanism the constitutive Dream named. **Epics 6–12** (30 stories)
are the CLI + web dashboard for the three still-missing proclamation moments (Progress, Success,
Operations) — but built to a radically scaled-down architecture after a same-day scope
correction (§4) that never made it into the epics doc that still describes them. The whole-suite
test count grew from 3 (Story 1.1) to 614+ passed / 2 skipped by Epic 9, holding through Epics
10–12 with incremental additions each epic.

## 2. What went well

- **The transport spike (Story 1.2) de-risked the whole bridge before anything else was built.**
  A live, re-runnable smoke test against `api.anthropic.com` proved the pure-MCP-client path
  works from a plain Python process — 23 tools, all 8 port tools present, a 33,985-character
  design-system prompt returned intact. This closed the architecture spine's biggest open
  question (`mcp` vs. the agent-SDK fallback) in the first real story, and every later Epic 1–5
  story built on a proven, not assumed, transport.
- **The determinism-boundary guard (AD-3: bridge-core never imports a concrete transport adapter)
  earned its keep by being *repeatedly broken and repeatedly caught*.** Four separate review
  passes on Story 1.4 alone found new ways to evade the static AST check — `from . import
  transport` (bare relative import), `import ... as x` aliasing, leaf-only alias scanning missing
  `ImportFrom.module`, then `sys.modules`/`vars`/`__dict__`/`pkgutil.resolve_name`/
  `attrgetter`/`globals()` as a second wave of evasions. Each pass hardened the guard and added a
  parameterized pinning test for the exact evasion found — the check that started as "does the
  AST mention `McpTransport`" ended as a derived, coverage-pinned sweep over every bridge-core
  module. This is the single clearest case of adversarial review compounding in value across
  passes rather than diminishing.
- **The `--json` error-path gap was caught cross-station, not just cross-story.** Story 6.1's
  review explicitly flagged that `dispatch` never rendered `--json` on its `HeraldError` catch
  branch, and named it a **repeat-risk before reviewing** because "this exact bug class had
  already been found and fixed twice this session in other stations (Steward's
  `ProvisionDuty`/`BudgetDuty`)" — and a third instance turned up in Herald. That is adversarial
  review doing its job at the right altitude: recognizing a pattern across projects, not just
  within one diff.
- **The scaled-down architecture correction (§4) held its scope boundary cleanly across five
  epics.** Once Epics 8–10 were re-specced as CLI-triggered/local-storage-only, every one of
  those stories' own "Never" boundaries (no webhook route, no scheduler dependency, no HTTP
  server) held through implementation and review with zero findings trying to smuggle the
  original live-backend shape back in.
- **Self-review-then-independent-review as a two-tier discipline was applied consistently and
  honestly.** Every Epic 1–5 story marks `followup_review_recommended: true` when it was a
  same-agent pass, and the epic close-out passes then ran genuine independent Blind Hunter +
  Edge Case Hunter review — which caught real defects the self-review missed (Story 1.6's
  self-review found a *different* high-severity gap than the close-out pass found next: the
  self-review closed the "hand-seeded bootstrap" duplicate-project risk; the close-out pass then
  found the *separate* "mid-pipeline transport failure orphans a duplicate project" risk the
  self-review's own fix had not covered). That is real evidence the two-tier discipline is not
  theater.

## 3. What was harder than expected

- **The path-length panic hit Story 1.2 mid-epic**, the same `pixi-build-python` `usize`
  underflow documented in the cross-station memory
  (`project_bmad_loop_worktree_path_length_limit.md`) — a 194-byte worktree root, 21 over the
  ~173-byte ceiling. It rolled Story 1.2's dev attempt 3 branch back to baseline (misclassified
  as a code failure), requiring a fast-forward restore into a short-path worktree to re-verify.
  Known problem, still cost a full recovery cycle.
- **The `pyforge-herald` pixi environment's first extension of `pixi.lock` re-solved the entire
  shared workspace lock**, not just the new environment — pixi 0.73.0 has no per-environment
  re-solve, so a brand-new environment can never satisfy `--frozen` and tripped on the unrelated
  `bmad-ui` environment's local `build_artifacts/linux64` channel not existing in a fresh
  worktree. Story 1.1 needed a full "workstation TODO" deferral, then a repair-pass commit to
  close it once a workstation had the channel populated.
- **`state.py`'s error-handling contract needed three full follow-up passes to actually close.**
  Pass 1 wrapped `JSONDecodeError`/`KeyError`/`TypeError`. Pass 2 found `UnicodeDecodeError`
  (a `ValueError` *sibling* of `JSONDecodeError`, not a subclass — so the original catch clause
  never fired) and non-`FileNotFoundError` `OSError`s. Pass 3 found `write()` could still leak a
  raw `TypeError` on a non-serializable value, and that read/write validation was asymmetric
  (`write` refused a bad slug type; `read` returned `None` instead, masking a caller bug as
  "no state yet"). Getting a single module's error boundary to actually be airtight took real,
  repeated adversarial pressure — no single review pass found it all.
- **The whole Epics 6–12 chain shipped against a planning doc (`epics.md`) that never got
  updated after the scope correction.** `epics.md` still describes Story 8.2 as "On-Ship Webhook
  + Weekly Cron Automation" and Story 9.2 as "Auto-Extract + Operator Review Gate" — the actual
  shipped stories (`spec-8-2-implement-on-ship-webhook-and-weekly-cron-automation.md` titled
  "CLI-Triggered Progress Creation (scaled down from On-Ship Webhook & Weekly Cron)",
  `spec-9-2-cli-triggered-draft-creation.md`) carry the real scope, but a reader consulting
  `epics.md` alone would get the wrong architecture. The individual specs are internally honest
  about the divergence; the epic-level document is not.

## 4. Corrections to the skill / process — the live-backend architecture pivot

This is the single most significant finding of the whole build. Epics 8–10's story specs, as
written in `epics-with-stories.md`, assumed infrastructure Herald never had and was never going
to build in V1: a Flask/FastAPI webhook endpoint CI calls on every merge, HMAC signature
verification with retry/backoff, an APScheduler/Celery weekly cron job aggregating a bmad-loop
journal format that doesn't exist, a dashboard API and test-job-URL query for auto-extracting
claims, and downstream-PR searches as adoption signals. None of it exists anywhere in this
repo — Herald's actual architecture is a stateless CLI plus a static-JSON-snapshot web dashboard,
proven out concretely in Epics 1–5.

**The correction landed same-day, at Story 8.1's own scope decision (2026-08-08), and was
recorded explicitly rather than silently substituted:**

- `spec-8-2` (title: "CLI-Triggered Progress Creation (scaled down from On-Ship Webhook & Weekly
  Cron)") replaces the webhook+cron with `herald progress <station> --update`, an operator-run
  command with explicit `--shipped`/`--compute-hours`/`--token-spend`/`--wall-clock-hours`/
  `--unblock-narrative` flags standing in for what a webhook payload would have carried.
- `spec-9-2` (title: "Implement CLI-Triggered Draft Creation & Review Gate (Scaled Down)")
  replaces the PR-close webhook + metric-query auto-extraction with `herald success create
  <project-name>`, an operator supplying the evidence URLs directly.
- Both specs name their scope boundary explicitly ("no HTTP server, no webhook route, no HMAC
  signature verification, no retry/backoff, no cron/scheduler of any kind") and both point at a
  **new Dream** — `docs/dreams/herald-moments-2-4-live-backend.md` (commit `6cc7299496`,
  2026-08-08) — that preserves the full original spec for later, separate work, explicitly
  designed so realizing it later only needs to swap what *triggers* the storage-layer functions
  (a webhook handler calling `progress.upsert` instead of a CLI handler), not reshape the
  storage layer or the CLI/web-tab contract an operator will have already learned.
- `epics.md` and `epics-with-stories.md` were **not** updated to reflect this — they are frozen
  planning artifacts describing the pre-correction shape. Every implementing spec for 8.2/9.2
  onward explicitly quotes the epics doc's line numbers and states the deviation; a reader who
  only skims `epics.md` would not know the pivot happened.

**Lesson:** catching an architecture/spec mismatch mid-chain and redirecting explicitly, with the
original preserved as a Dream rather than deleted, is the right call and was executed cleanly.
The gap is documentation currency, not judgment — the planning-tier `epics.md` should have
carried at least a pointer note the way the individual specs do, so it stops actively
misinforming a reader who doesn't also read the per-story specs. This is exactly the "Keeping
BMAD artifacts in sync with the live repo" problem CLAUDE.md's sync-loop section names for
`pyforge-marshal`'s docs, generalized to a planning artifact that never got a reconciler pass at
all.

## 5. Recurring bug patterns (2+ independent occurrences)

These indicate systemic gaps worth carrying forward, not one-off mistakes:

1. **Raw exceptions leaking through the `HeraldError`/AD-6 CLI boundary — found repeatedly across
   three separate `state.py`/`registry.py` review passes and again in `notices.py` (Epic 10).**
   Each fix closed one exception family or one asymmetry (read vs. write validation,
   `JSONDecodeError` vs. its `UnicodeDecodeError` sibling, malformed vs. missing-field, string
   vs. non-string types) and the next pass found the next one. By spec-10-1's review, the same
   *shape* of bug recurred: `_entry_to_notice` checked unknown extras and malformed types but not
   *missing* required fields, again raising a raw `TypeError` instead of `HeraldError`. Five-plus
   independent instances of "a structural-failure boundary that isn't actually structural on
   every input shape" across the whole build.
2. **The determinism-boundary static import guard was evaded and re-hardened across at least
   four passes on Story 1.4 alone** (see §2) — a genuine cat-and-mouse pattern against an
   inherently open-ended class of dynamic-import tricks, explicitly documented as such in the
   final pass rather than claimed closed.
3. **Write-ordering / partial-failure state consistency bugs — three independent instances.**
   Story 1.6's close-out review found a mid-pipeline transport failure could orphan a duplicate
   Design project because `state.write`/`registry.register` only ran after every remote call
   succeeded. Story 2.1's Epic-2 review found the *inverse* ordering bug: the etag was recorded
   *before* re-derivation (prove/export) succeeded, so a failed export left a stale artifact but
   a state file claiming success. Story 10.1's review found markdown written *after* the index
   in `author_notice`/`publish_notice`/`close_notice`, so a markdown-write failure left a phantom
   index entry. All three are the same underlying failure mode — "record success before every
   step that could still fail has actually finished" — recurring across three unrelated modules.
4. **A CLI-boundary flag silently not honored on the error path — the `--json` gap (§2), found
   three times across two stations in one session** (Steward twice, Herald once), and separately
   **the `--json`/`--date-range`/`--station` flags only working *before* a nested subcommand, not
   after** (Story 10.4) — a related-but-distinct argparse-nesting class of the same broader
   "global flags don't compose the way an operator expects them to" problem.
5. **Missing-prerequisites gap in every doc-facing story (Epic 12).** `spec-12-1`, `spec-12-3`,
   and (by the same root cause) the automation-troubleshooting guide all independently lacked a
   "how do you get `herald` on your `PATH`" Prerequisites section — three separate docs shipped
   the same first-time-operator gap before the Epic 12 review pass caught and fixed all of them
   in the same session.
6. **Stale/reused illustrative IDs across documentation files causing self-contradiction**
   (`spec-12-1`/`spec-12-4`: the same claim id `9c3590d4-...` shown both cleanly published and
   with a broken evidence link, both within one file and across files) — a smaller but concrete
   instance of "hand-authored example data drifting out of sync across docs with no single
   source of truth," worth a general caution for any future doc-heavy story.

## 6. Lessons for the next station

1. **A scaled-down architecture correction needs a pointer in the epic-level planning doc, not
   just in each implementing spec.** The per-story specs did this right (explicit "Approach
   (scaled-down, scope decision)" sections, a preserved Dream for the deferred shape); `epics.md`
   itself never got even a one-line "Note: see spec-8-2 for the as-shipped scope" annotation.
   Future BMAD efforts that pivot mid-chain should treat the epic-level doc as needing the same
   currency discipline CLAUDE.md's sync-loop section already applies to `pyforge-marshal`'s
   architecture/PRD.
2. **A structural-failure boundary (any module's "raise `X`Error, never a bare exception"
   contract) should be tested with a systematic input-shape sweep on the FIRST pass, not
   discovered exception-family by exception-family across three follow-up reviews.** The
   `state.py`/`registry.py`/`notices.py` pattern (§5.1) suggests the review protocol for any new
   "structured error boundary" module should explicitly check: every required-field-missing
   case, every wrong-type case, every sibling-exception-class case (not just the one exception
   type the happy-path bug reproduction used), and both directions of read/write validation
   symmetry — as a checklist, not organically across passes.
3. **Write-before-every-precondition-is-confirmed is a recurring architecture smell worth a named
   pattern.** Three independent modules (§5.3) shipped the same ordering bug in different
   directions (record-too-early, record-too-late, write-secondary-before-primary). A
   "successful completion is recorded only after the last irreversible step, and the
   first-written artifact is always the one every reader consults" checklist item would have
   caught at least two of the three on first implementation.
4. **When a repeat-risk bug class is already known this session (from another station), name it
   explicitly before reviewing, the way Story 6.1's review did.** That flag turned a routine
   review into one that specifically hunted for and found the third instance of the `--json`
   error-path gap — cross-station pattern-matching is cheap and worked.
5. **Doc-heavy stories (Epic 12 style) should get a dedicated "first-run from zero" pass** — every
   Prerequisites gap found in Epic 12 was the same root cause (assuming an already-activated pixi
   environment) hitting three separate files independently; a single shared "getting started"
   fragment referenced by all doc files, rather than three copies, would have prevented the
   triplication and the fix-in-three-places cost.

## 7. Action items

| # | Action | Owner | Status |
|---|---|---|---|
| A1 | Add a one-line pointer note in `epics.md` (and `epics-with-stories.md`) at Stories 8.2/9.2 pointing to the actual shipped specs and `docs/dreams/herald-moments-2-4-live-backend.md`, so a reader who only opens the epic doc isn't misinformed about the architecture. | rxm7706 | open |
| A2 | Fold the "structural error boundary sweep" checklist (§6.2: missing-field / wrong-type / sibling-exception-class / read-write symmetry) into the review-lens guidance used for any new state/storage module, in whichever skill or shared review doc governs adversarial review across stations. | rxm7706 (next skill/process touch) | open |
| A3 | Name "record success only after the last irreversible step" as an explicit review-checklist item (§6.3) for any module doing multi-step writes with recoverable failure between steps. | rxm7706 | open |
| A4 | When a doc-heavy epic (like Epic 12) ships multiple files with a shared prerequisite, factor it into one referenced fragment instead of copy-pasting a Prerequisites section per file — would have avoided the same fix landing three times in one Epic 12 review pass. | rxm7706 (next doc-heavy story) | open |
| A5 | Herald has 4 named live proofs still deferred from Epic 2 (`herald deck pull` against real Design projects for `pyforge-marshal`/`pyforge-warden`, `--commit`, the `--target marp-deck` remote-path naming convention, and `--target standalone`) — blocked purely on `/design-login` never having been run in the working session. Run these the next time a live Design credential is available, before trusting the naming-convention assumption (finding 3) against real data. | rxm7706 | open |

Per CLAUDE.md's BMAD↔conda-forge-expert integration Rule 2: this effort touched no `recipes/`
work and invoked no `conda-forge-expert` skill surface at any point across all 47 stories (it is
a pure Python/CLI/web package under `src/shared/packages/pyforge-herald/`), so the mandatory
conda-forge-expert-skill retro does not apply here — matching Epic 4's own close-out note, which
already recorded this same non-applicability for that epic.

## 8. Readiness assessment

- **Testing/quality:** ✅ whole-package suite grew monotonically epic over epic (3 → 614+ passed,
  2 skipped by Epic 9, holding through Epic 12); every adversarial-review finding across all 47
  specs was either patched with a dedicated regression test, explicitly deferred to
  `deferred-work-ledger.md`, or rejected with a documented, verified rationale — no finding was
  silently dropped.
- **Deployment:** ✅ merged to `main` via PRs #111/#114/#116 (Epic 1's early scaffold/spike) and
  #308–#316 (Epics 3–12); Epic 1's remaining stories and Epic 2 landed via the `loop/pyforge-herald`
  branch pattern before the PR-per-epic convention took over.
  A repo-hygiene pass (`44aed22e77`) has already refreshed the fleet dashboard to reflect Herald
  Epics 6–12 done.
- **Architecture honesty:** ⚠️ live (not blocking) — `epics.md`/`epics-with-stories.md` describe
  the pre-pivot live-backend shape for Epics 8–10; the as-shipped scaled-down architecture is
  correct and complete in every implementing spec and in the new Dream, but the epic-level doc
  itself was never annotated (A1).
- **Blockers:** none for the 47 shipped stories. The four deferred live-MCP smoke proofs (A5) and
  the epic-doc annotation (A1) are the only open items, neither gating.

## 9. Next

No next epic — Herald's 12 planned epics are done (Moment 1: Pitch via Epics 1–5; Moments 2–4:
Progress/Success/Operations via Epics 6–12, scaled down). Forward work is: A1–A5 above, the
deferred live-backend Dream (`docs/dreams/herald-moments-2-4-live-backend.md`) if a real
webhook/cron/database backend is ever prioritized, and the concurrent-write/lost-update class of
deferred-work-ledger entries inherited from `state.py`'s original design (documented, not fixed,
across every module built on the same pattern).
