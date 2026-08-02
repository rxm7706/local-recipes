---
title: One fabricated commit, eight stations of debris
type: dream
owner: marshal
status: realized
---

# One fabricated commit, eight stations of debris

## The Dream

`_bmad-output/projects/` holds every station's planning record — but a single bulk commit
(`dad47c408a`, "chore: PyForge planning artifacts and test infrastructure — all 8 stations",
2026-08-02) stamped generic, unreviewed template content across all 8 stations at once: dead
test scaffolding that collects zero real tests, a hollow `sprint-status.yaml` claiming 0%
completion regardless of real shipped work, and — in places — a fabricated `test-architecture.md`
or an unfilled `README.md` `[role]`/`[responsibilities]` placeholder. Remediation since then has
been real but inconsistent: some stations got fixed same-day (a follow-up commit rewrote
`test-architecture.md` for six of them), some never did (Genesis's still describes the wrong,
pre-split "genesis-as-installer" narrative), and the dead test scaffolding and hollow
sprint-status template were never addressed anywhere.

Every station's planning tree should tell the truth about itself — real content or an honest
placeholder, never a templated fiction that happens to compile. This Dream is that cleanup,
closed once every station's `_bmad-output/projects/<station>/` tree is either genuinely current
or has been mechanically corrected, and any orphaned single-file debris from already-completed
consolidations (a handful found, distinct from the bulk-commit problem) is archived.

## What it looks like when real

- No station's `_bmad-output/projects/<station>/` contains dead test scaffolding (a `tests/`
  tree with zero real `test_*.py` files, a `pytest.ini` pointing at a nonexistent path, or a
  `playwright.config.ts` configuring a web server the station doesn't have).
- No station's `planning-artifacts/sprint-status.yaml` claims `0%`/`stories_complete: 0` while
  its own `sprint-status-ledger.yaml` (or code) shows real shipped work — either it's deleted (the
  `-ledger` twin is what dashboards/scripts actually read everywhere) or it's regenerated to match
  reality.
- Every station's `test-architecture.md` and root `README.md` describe what's actually there —
  Genesis's especially, since it currently asserts a `src/pyforge_genesis` package and an
  installer role that moved to Marshal in the 2026-07-28 split.
- The handful of confirmed orphaned single files (below) are archived, mirroring the
  `archive/_bmad-output/...` convention already used for today's satellite-chain moves.
- `_bmad-output/PROJECTS.md`'s per-project `Dream:` pointers name the actual station-charter
  Dream file (`type: dream`), not a stale filename or a `type: practice` satellite.
- The fleet dashboard (`docs/dashboard/generate.py --source sprint-status`) reports zero
  `gaps` for herald: its brief and architecture directories are named `brief-pyforge-herald-*`
  / `architecture-pyforge-herald-*`, matching every other station's convention and the
  `_stage_globs()` pattern that scores them.
- `_currency()`'s `_FEEDS` check carries a small grace period, so same-day/adjacent-day edits
  (a spec's routine memlog touch) stop reading as permanent drift, while genuine multi-day gaps
  still surface. The 5 pairs identified in Cluster 5 (warden, doctor, scribe, steward, mason) are
  re-validated and their currency stamp brought current.

## What is real

A 5-agent research-only audit ran 2026-08-02 across all 9 BMAD projects (679 files). Nothing was
moved — this section is the evidence base for the cleanup above, not yet acted on.

### Cluster 1 — the `dad47c408a` fabricated-boilerplate set (fleet-wide, the dominant finding)

| Artifact | Confirmed affected | Confirmed clean / already fixed | Notes |
|---|---|---|---|
| Dead test scaffolding (`tests/`, `pytest.ini`, `playwright.config.ts`) | atlas, doctor, marshal, warden, scribe, mason, steward (7) | herald, genesis (never generated for them) | Zero real tests anywhere in these trees; the real, wired suites all live at `src/shared/packages/pyforge-<station>/tests/`. Atlas's copy even configures a Vite dev server; Marshal's configures Playwright `e2e/web`/`e2e/pages` for a CLI-only product. |
| Hollow `planning-artifacts/sprint-status.yaml` (0%, empty arrays) | confirmed identical stub in all 8 stations | — | Distinct from `sprint-status-ledger.yaml`, which is real, tracked, and what dashboards/scripts actually read. Doctor's copy was explicitly called "stale" in a same-day follow-up commit (`17a3154075`) but never removed. |
| Fabricated `test-architecture.md` | originally atlas, warden, doctor, mason, scribe, steward | **fixed same-day** by commit `2957718d4c` (real, code-grounded content) for those 6; herald and marshal's were never fabricated in the first place | **Genesis is the one exception — never fixed.** Its `test-architecture.md` still opens "Genesis bootstraps the PyForge factory installer... initializing the complete factory stack from scratch," referencing a `src/pyforge_genesis` package that doesn't exist and directly contradicting Genesis's own current, correct, constitutive PRD/architecture ("ships no product"). |
| Unfilled `README.md` (`[role]`/`[responsibilities]` placeholder) | marshal, herald, genesis confirmed; doctor has an equivalent unfilled placeholder | — | Same generic text across all three checked; likely fleet-wide, not individually verified for the remaining 5. |

### Cluster 2 — orphaned single-file debris (distinct pattern: leftovers from *already-completed*, unrelated consolidations, never cleaned up)

- **Atlas** — `RESUME-EPIC-10.md`: self-marked "✅ CLOSED 2026-07-29... HISTORY," zero repo-wide references, its unique content (loop blind-spot lessons) already promoted into auto-memory.
- **Herald** — `intake-video-scripts-manticore-2026-07-31.md`: input material for a Dream+Spec (`video-scripts`) that was fully retired to `archive/` on 2026-08-01; this one file was left behind by oversight. Same shape as `product-brief-deckcraft.md`, which the same-day Herald consolidation already found and archived.

### Cluster 3 — content-drift, NOT archive candidates (flagged for a separate correction pass)

- `project-context.md` in Mason (claims "38/38 stories," Dream says 4/38) and Herald (claims
  "17/17," Dream says 4/17) — each is the sole copy at its path, so the fix is regeneration in
  place, not archiving.
- `_bmad-output/PROJECTS.md`'s `Dream:` pointers for two stations are stale, found while
  answering a user question about dreams/brief/PRD/architecture by station (2026-08-02, same
  session as the audit above):
  - **mason** points at `docs/dreams/packaging-factory.md`, but that file scope-noted itself
    out of the station chain on 2026-07-25 ("Mason **the station** now has his own charter:
    [[pyforge-mason]]") — it's a `type: practice` satellite, not the station charter. Should
    point at `docs/dreams/pyforge-mason.md`.
  - **herald** points at `docs/dreams/design-code-bridge.md`, which no longer exists (folded
    into the station charter during an earlier consolidation). Should point at
    `docs/dreams/pyforge-herald.md`.
  - Fix is a two-line edit to `_bmad-output/PROJECTS.md`'s Projects table; no archiving needed.

### Cluster 4 — the fleet dashboard reports a real gap for herald (found 2026-08-02, post-realization)

The user reported the program console (`docs/dashboard/`) showing stations "out of date, missing
artifacts, and a gap" for the 8 primary stations. Verified against `docs/dashboard/generate.py`'s
own fleet scan (`python3 docs/dashboard/generate.py --source sprint-status`), confirmed **on
`main`, before any of this Dream's cleanup** — not something the cleanup branch introduced:

- **Herald has real gaps: `['brief', 'arch']`.** `_stage_globs()` looks for
  `briefs/brief-pyforge-herald-*/brief*.md` and `architecture/architecture-pyforge-herald-*/*.md`
  (matching every other station's `brief-<slug>-<date>`/`architecture-<slug>-<date>` naming), but
  herald's actual directories are `briefs/brief-herald-pitch-2026-08-01/` and
  `architecture/architecture-herald-pitch-2026-08-01/` — named after the pre-consolidation
  `herald-pitch` Dream, not the station slug `pyforge-herald`. The content is current and real
  (confirmed in the earlier "dreams by station" conversation); the *directory name* is what's
  wrong. `prds/prd-pyforge-herald-2026-08-01/` already uses the correct convention — only brief
  and architecture are inconsistent within herald's own tree. Same root cause, same fix shape as
  the marshal brief CAP-9 already corrected in this cleanup.
- The other 7 stations (atlas, doctor, marshal, mason, scribe, steward, warden) show `gaps: []` —
  no real gaps. Their `partial: ['research']` and `staleBy` currency findings are, on inspection,
  either pre-existing/expected (research is intentionally inherited from the station by satellite
  chains, coded as such) or a natural, correct consequence of files this Dream's own cleanup
  touched today (a freshly-edited file is legitimately "newer" than an untouched sibling stage) —
  not bugs. "Out of date" in the user's report is this dashboard-generation snapshot being stale
  relative to the cleanup commits already on this branch, not a second defect class.

### Cluster 5 — the currency ("feeds") check has no grace period, so every station reads stale

Reported by the user after CAP-10: "now every station on the dashboard has something as
outdated." Verified against `docs/dashboard/generate.py`'s `_currency()` on the regenerated
`data.js` (2026-08-02, all 8 primary stations):

| Station | `staleBy` findings (`stage` newer than `than`, gap) |
|---|---|
| atlas | spec/prd (1d) |
| doctor | prd/arch (**8d**), spec/prd (0d), prd/gates (1d) |
| herald | spec/prd (0d), prd/gates (1d) |
| marshal | spec/prd (0d) |
| mason | spec/prd (1d), arch/epics (**8d**) |
| scribe | prd/arch (**7d**), spec/prd (1d) |
| steward | prd/arch (**7d**), spec/prd (0d) |
| warden | prd/arch (**16d**), prd/gates (**18d**) |

Root cause: `_FEEDS`' comparison (`u > d`, strict, zero grace) fires on ANY timestamp
difference. Every `spec/prd` entry above is 0–1 days — because a spec's `.memlog.md` gets a
fresh `updated:` stamp on every append (routine corrections, validation passes, cross-reference
fixes — exactly the kind CAP-9/CAP-10 just made), while a PRD is touched far less often. That
makes "spec newer than prd" true almost by construction, not a signal that the PRD needs
re-deriving — the same "always red, gets ignored" trap `_currency()`'s own code comment already
names and suppresses for the *separate* `behind-code` check (`realized` chains), but never
applied to `_FEEDS`. Mixed into that 100%-occurrence noise are real, multi-day gaps (bolded
above) that predate this Dream's cleanup and are genuine: warden's architecture/gates are 16–18
days behind a PRD that moved without them, doctor/scribe/steward's architecture is 7–8 days
behind, mason's epics are 8 days behind its architecture.

User decision (2026-08-02): fix both — soften the detector so trivial same-day/adjacent edits
stop reading as permanent red, AND catch up the genuinely stale pairs so the softened detector
isn't just hiding real drift.

### Confirmed clean, no action needed

Scribe, Steward, and Warden's satellite-Dream/Spec-kernel layers all resolved to already-correct,
archived-in-place retirement records from earlier same-day consolidation passes — zero genuine
candidates beyond Cluster 1's fleet-wide items. Mason's 5 "orphan" Spec kernels all check out as
intentional (2 live, 3 properly archived-in-place). Every `spec-archive/`, per-story spec,
`.memlog.md`, retro, change-history file, and dated snapshot report checked across all 9 projects
was confirmed to be permanent-by-design record, not clutter — none were flagged.

## Realization log

- **2026-08-02** — Dream captured from a 5-agent research-only audit (report-only, zero files
  moved) run immediately after today's Atlas/Herald/Mason/Marshal PRD/brief/architecture/Spec
  consolidation, motivated by the user noticing the file landscape looked overgrown once that
  consolidation was done. Findings above are the full evidence base; next step is `bmad-spec` (or
  direct execution, if the fix is judged mechanical enough to skip a full spec) to turn Cluster 1
  and Cluster 2 into actual archive/regeneration actions.
- **2026-08-02** — Added the mason/herald stale-`Dream:`-pointer finding to Cluster 3 (report-only;
  user chose to fold it into this pending cleanup rather than fix `PROJECTS.md` immediately).
- **2026-08-02** — Realized via `spec-bmad-output-hygiene` (branch `bmad-output-hygiene`), 9
  capabilities, all archival not deletion (user directive mid-execution). CAP-1: `tests/`,
  `pytest.ini`, `playwright.config.ts` archived from the 7 confirmed stations. CAP-2: the hollow
  `sprint-status.yaml` stub archived from all 9. CAP-3: Genesis's `test-architecture.md`
  regenerated to state plainly there is nothing to test. CAP-4: the `[role]`/`[responsibilities]`
  placeholders turned out to live in each station's **project-root** `README.md` (8 of 9
  stations, identical template — not `planning-artifacts/README.md` as this Dream's wording
  implied), also describing the CAP-1-archived scaffolding as live; all 8 fixed, plus the 6
  generic (non-literal-placeholder) `planning-artifacts/README.md` stubs rewritten with real
  content. CAP-5: both orphaned files archived. CAP-6: `project-context.md` regenerated for
  Mason/Herald — live re-check found this Dream's own cited "real" counts (4/38, 4/17) had
  themselves gone stale (now 4/48, 4/27), and both files were fabricated beyond the count
  (wrong role labels, dead reference paths). CAP-7: both `PROJECTS.md` pointers fixed, plus a
  third stale row found and fixed (Genesis's own entry, same root cause). CAP-8 (originally
  "relocate 13 misfiled local-recipes files") was **reverted in full**: the files were correctly
  moved to `pyforge-marshal` on 2026-07-28 per `bmad_drift_check.py`'s own comment, and the
  misdiagnosis traced to `CLAUDE.md` itself never being updated after that move — CAP-8 became
  fixing those two stale `CLAUDE.md` mentions instead. CAP-9 (added
  mid-execution, not originally in this Dream): marshal's genuine sole brief reshaped from a loose
  file into the standard `briefs/brief-<slug>-<date>/` layout every other station uses. Both
  drift checkers (`bmad-drift-check --integrity-only`, `dashboard_drift_check.py`) verified clean
  of everything this Dream touched before closing.
- **2026-08-02** — Reopened (`realized` → `specified`): user reported the fleet dashboard showing
  stations out of date, missing artifacts, and a gap. Verified against `main` (pre-existing, not
  branch-introduced) and root-caused to Cluster 4 above — herald's brief/architecture directories
  are misnamed. CAP-10 added to `spec-bmad-output-hygiene` to fix it.
- **2026-08-02** — CAP-10 shipped: herald's `briefs/`/`architecture/` directories renamed to the
  `pyforge-herald` convention; `docs/dashboard/data.js` regenerated. Verified
  `pyforge-herald` now reports `gaps: []` (was `['brief', 'arch']`); fleet no-gap count 8 → 9.
  Dream re-closed (`specified` → `realized`).
- **2026-08-02** — Reopened again (`realized` → `specified`): user reported every station reading
  "outdated." Root-caused to Cluster 5 (`_FEEDS` has no grace period). User chose to fix both the
  detector and the genuinely-stale artifacts. Also clarified separately: the deployed dashboard
  (GitHub Pages) only regenerates on push to `main` per `.github/workflows/dashboard.yml` — the
  herald fix is real and verified on this branch, it just hasn't deployed yet pending merge; this
  was not a second herald defect.
- **2026-08-02** — CAP-11/CAP-12 shipped. CAP-11: `_currency()`'s `_FEEDS` check gained a 2-day
  grace period; fleet currency findings 16 → 7. CAP-12: read each stale pair's PRD
  `currency_review` note to tell structural bumps from real drift — scribe/steward/warden
  (`prd`/`arch`) confirmed structural, re-stamped (and their downstream `epics.md`, to avoid
  pushing the staleness further down the pipeline); doctor (`prd`/`arch`, real FR-10..13 content
  added) and mason (`arch`/`epics`, FR-1..46 vs PRD's `frCount: 50`) left unfixed and visible —
  genuine architecture-authoring gaps, out of scope for a hygiene spec; warden's `prd`/`gates`
  left unstamped since a readiness report is a point-in-time snapshot, not a living document.
  Fleet currency findings 16 → 4, all 4 remaining genuine and intentionally visible. Dream
  re-closed (`specified` → `realized`).
