---
title: '23.5: The family is browsable and downloadable on Pages'
type: 'feature'
created: '2026-09-16'
status: 'done'
baseline_revision: '36ccbfa9f9d2c1b06a2a5ff7a0c2561a8a10778b'
review_loop_iteration: 0
followup_review_recommended: true
context: []
deferred:
  - summary: >-
      No PR-gating CI lane runs docsite/build.py or site-check before merge, and this
      story's own mandated Verification command (pyforge-herald-test) has zero coverage
      of docsite/, so a regression in the family-page code (or the pre-existing
      dossier/gallery/artifact code) can merge to main with every gate green.
    evidence: |-
      Verified 2026-09-18: grepped every `pull_request`-triggered workflow and
      `pr-preflight`'s dependency list in pixi.toml — none reference `docsite` or
      `site-check`. `dashboard.yml`, the only workflow that runs the build, triggers on
      `push: branches: [main]` only. No `docsite/tests/` directory or any test file
      anywhere imports `docsite/build.py`. This is pre-existing for the whole docsite
      pipeline (dossier/gallery/artifact already had zero PR-gating CI and zero unit
      tests before this story) — not introduced by this diff, so it is out of this
      story's scope to fix.
    location: >-
      pixi.toml (pr-preflight, feature.site.tasks.site-check), .github/workflows/dashboard.yml
    severity: medium
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** docsite/build.py publishes standalone infographics only — no PPTX, Marp, exec summary, or per-deck page.

**Approach:** One family page per registered deck plus an index. Poster, Infographic Deck, Executive Summary in view; PPTX(s) and Marp as downloads; etag and tree stamps. dashboard.yml remains the only deploy-pages caller.

## Boundaries & Constraints

**Always:**
- Kedro-Viz stays at /kedro-viz/.
- One deploy-pages caller.

**Never:**
- Do not add a second Pages deploy.
- Do not bind a new Pages product.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| site-check | after family pages land | passes | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-design-sync-loop CAP-7; spec-pyforge-pages CAP-1/CAP-2`.
Surface: docsite/build.py; docsite/templates/**; docsite/content/**; docs/dashboard/**; site-check..
Ledger key: `23-5-the-family-is-browsable-and-downloadable-on-pages`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-23-5-the-family-is-browsable-and-downloadable-on-pages.md`.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` — expected: pass (the station's policy `verify_commands` entry; MRS-GATE-010 binds the dispatch gate to this Success signal, and it is read from the primary tree's tracked spec, so it must be declared here before dispatch, not by the session).

**Manual checks:**
- `site-check` passes after the family pages land; each family page shows the poster, Infographic Deck and Executive Summary in view, offers the PPTX(s) and Marp sources as downloads, and stamps each with its etag and tree; `dashboard.yml` is still the only `deploy-pages` caller and Kedro-Viz is still at `/kedro-viz/`.

## Review Triage Log

### 2026-09-18 — Review pass
- verdicts: 18 findings — high 0, medium 7, low 10, false 1, maybe-false 0
- findings:
  - `[low]` `[patch]` Landing page (`page_index.html.j2`) has cards for Dossier and Infographics but none for the new Decks section, even though `site.yml` gained a `decks` nav entry — verified: `card-grid` only has two `<a class="card">` entries plus the `site.neighbours` loop. Applied: added a third card linking `decks/index.html`, mirroring the Infographics card's shape and reporting `{{ families | length }}`.
  - `[low]` `[patch]` `publish_family_views` injects the family back-bar unconditionally, unlike `publish_infographic` which gates it behind `site_cfg["infographics"].get("inject_backbar", True)` — verified at `docsite/build.py:350-372` (no `inject` param). Currently harmless (`inject_backbar: true` in site.yml) but a real inconsistency if ever flipped. Applied: `publish_family_views` now takes an `inject: bool` param, gated the same as `publish_infographic`; the `build()` call site passes the same computed `inject` value.
  - `[low]` `[reject]` Default `page_description` for a family page always lists "Infographic Deck, Executive Summary, PowerPoint and Marp sources" regardless of what the deck actually has (2 members: Blind Hunter + Edge Case Hunter both flagged this) — verified real at `docsite/build.py:534-537`, but all 10 currently-registered decks have every artifact type (confirmed via `site-check` output), so it manifests for no deck today, and a correct fix requires new conditional branching (more than a direct correction) — rejected per the low-and-non-trivial-fix rule.
  - `[medium]` `[patch]` `check()` validates the top-level `decks/index.html` for size/existence but the per-deck `decks/<slug>/index.html` pages only get an existence check (no "suspiciously small" or unrendered-Jinja-delimiter check, unlike `dossier/index.html`) — verified at `docsite/build.py:612-629`, a truncated/half-rendered family page would pass `--check` silently. Applied: the per-family loop now also checks each `decks/<slug>/index.html` for `<500B` size and for unrendered `{{`/`{%` delimiters.
  - `[low]` `[patch]` `main()`'s console summary collapses a family's status to only `"poster+ID+ES"` or `"poster only"` (2 members: Blind Hunter + Edge Case Hunter both flagged this) — verified at `docsite/build.py:667-672`, a deck with exactly one of Infographic Deck/Executive Summary is mislabeled "poster only". Harmless today (no partial deck exists) but the fix is a direct correction. Applied: the label is now built incrementally (`poster`, `+ID` if present, `+ES` if present, `"poster only"` only when neither is present).
  - `[low]` `[patch]` `page_family_index.html.j2` hardcodes `"../infographics/..."` instead of using the `{{ rel }}` variable already passed into the template (equal to `"../"` here) — verified at the template's `data-preview` attribute; every sibling template uses `{{ rel }}`. Applied: changed to `{{ rel }}infographics/{{ fam.poster.out_name }}`.
  - `[low]` `[patch]` `_artifact_stamp`'s sidecar-stamp branch returns the etag at full length while the fallback branch truncates its digest to 12 chars, so etag display length will differ once real stamp sidecars exist — verified at `docsite/build.py:258-268`. No sidecar exists yet for any deck today (confirmed by the implementation subagent's own report), so this doesn't manifest yet, but the fix is a trivial one-line truncation, so it does not qualify for auto-reject. Applied: the sidecar branch now truncates `etag` to `[:12]` too.
  - `[false]` `[reject]` A future PR for this branch needs the `maintenance` label per this repo's PR gates, and "nothing in the diff... evidences that label has been applied" — refuted: this `bmad-build-auto` run does not open a PR at all, so there is nothing to have labeled yet; this is forward guidance for whoever opens the PR, not a defect in the diff.
  - `[low]` `[reject]` `check()`'s decks-index membership check (`if slug not in decks_index`) is a bare substring match, so a slug appearing elsewhere on the page could false-pass a broken link — verified real at `docsite/build.py:618-619`, but this is the same bare-substring pattern the pre-existing `if item["out_name"] not in gallery` infographics check already uses in this file (established precedent, not a new weaker pattern), the slugs involved are long and distinctive, and a proper fix (href-specific parsing) is more than a direct correction — rejected per the low-and-non-trivial-fix rule.
  - `[medium]` `[patch]` `_listed_files` returns every historically-dated file in a deck's `src/pptx`/`src/marp` directories, not just the current one(s) — verified live: `pyforge-atlas`'s family page downloads list ships all 6 PPTX files (3 dates × 2 product types: `pyforge-atlas-deck-*` and `pyforge-atlas_infographic_deck-*`) and all 11 Marp files, not just the current export, diverging from the intent's "PPTX(s) and Marp as downloads" (plural products, not plural dated history). Applied: `_listed_files` now groups by filename with the trailing `-YYYY-MM-DD` suffix stripped (a new `_DATE_SUFFIX_RE`) and keeps only the newest-dated file per group; verified live, `pyforge-atlas` now lists exactly 2 PPTX / 5 Marp (the current `2026-09-15` exports only).
  - `[medium]` `[defer]` No PR-gating CI lane ever runs `docsite/build.py`/`site-check` before merge, and the story's own mandated Verification command (`pyforge-herald-test`) has zero coverage of `docsite/` (3 members: Verification Gap Reviewer's main finding + Intent Alignment Auditor's same observation + Blind Hunter's "no unit tests" finding) — verified: grepped every `pull_request`-triggered workflow and `pr-preflight`'s dependency list, none reference `docsite`/`site-check`; `dashboard.yml` (the only workflow that runs the build) triggers on `push: branches: [main]` only. This is pre-existing for the whole docsite pipeline (dossier/gallery/artifact already had zero PR-gating CI and zero unit tests before this story), not introduced by this diff — routes to defer, not patch. Recorded in frontmatter `deferred`.
  - `[medium]` `[patch]` `docs/dashboard/`'s `.gitignore` block lists every `OWNED_OUTPUTS` entry individually (`index.html`, `.nojekyll`, `assets/`, `dossier/`, `infographics/`, `artifact/`) but has no `docs/dashboard/decks/` line even though this diff adds `"decks"` to `OWNED_OUTPUTS` (2 members: Verification Gap Reviewer + Intent Alignment Auditor both flagged this) — verified at `.gitignore:966-973`. A local build into `docs/dashboard/` (the same `--out` CI uses) leaves `decks/` untracked-and-not-ignored, unlike every sibling output, risking an accidental `git add` of binary PPTX exports. Applied: added `docs/dashboard/decks/` next to `docs/dashboard/infographics/`.
  - `[low]` `[patch]` `docsite/README.md`'s "Outputs land in `dist/`" table was not updated to list the two new output paths (`decks/index.html`, `decks/<slug>/index.html`) — verified: table stops at `assets/site.css`. Applied: added two rows.

## Auto Run Result

Status: done

**Summary:** `docsite/build.py` now publishes one family page per registered deck (`dist/decks/<slug>/index.html`) plus an index (`dist/decks/index.html`). "Registered" is derived from the existing infographics gallery list, never a second hand-maintained slug list. Each family page shows the poster, Infographic Deck and Executive Summary in view (each stamped with tree + etag) and offers the deck's current PPTX(s) and Marp source(s) as downloads (deduplicated to the newest export per product, not the full dated history). `dashboard.yml` remains the only `deploy-pages` caller; Kedro-Viz is untouched at `/kedro-viz/`.

**Files changed:**
- `docsite/build.py` — new deck-family pipeline (`collect_families`, `_single_file`, `_listed_files` with per-product date-dedup, `_artifact_stamp`, `_view_artifact`/`_download_artifact`, `publish_family_views`, `publish_family_downloads`); wired into `build()`, `check()` (existence/size/unrendered-Jinja/download-integrity checks), and `main()`'s console summary.
- `docsite/templates/page_family.html.j2` (new) — per-deck family page.
- `docsite/templates/page_family_index.html.j2` (new) — the decks index.
- `docsite/templates/page_index.html.j2` — added a "Decks" landing card.
- `docsite/templates/shell_page.html.j2` — the lazy-iframe-preview script, now shared (moved out of `page_gallery.html.j2` so family pages and the decks index can reuse it).
- `docsite/templates/page_gallery.html.j2` — the moved script removed from here.
- `docsite/content/site.yml` — added a `Decks` nav entry.
- `docsite/assets/_site-chrome.css` — styles for the stamp line and the download list.
- `.gitignore` — added `docs/dashboard/decks/` alongside the other `OWNED_OUTPUTS` entries.
- `docsite/README.md` — documented the two new output paths.

**Review findings breakdown** (18 findings across 4 layers, grouped into 14 entries):
- Patched (9 entries, 11 findings): landing-page Decks card; `inject_backbar` now respected by family views; `check()` now validates family-page size and unrendered-Jinja-delimiters; console summary no longer mislabels a partial deck; `page_family_index.html.j2` now uses `{{ rel }}` instead of a hardcoded `../`; `_artifact_stamp` etag truncation made consistent; `_listed_files` deduplicated to the newest export per product (medium — was silently publishing a deck's entire export history, e.g. `pyforge-atlas` dropped from 6 PPTX/11 Marp to 2 PPTX/5 Marp); `.gitignore` gained the missing `docs/dashboard/decks/` parity line (medium); `docsite/README.md`'s outputs table updated.
- Deferred (1 entry, 3 findings, medium): no PR-gating CI lane runs `docsite/build.py`/`site-check` before merge, pre-existing for the whole docsite pipeline (not introduced by this story) — recorded in frontmatter `deferred`.
- Rejected (3 entries, 4 findings): the family-page default description over-claims artifact types the deck may not have yet (low, unlikely today since all 10 decks are complete, proper fix needs new branching); the decks-index membership check is a bare substring match (low, matches an existing precedent in this file, proper fix needs more than a direct correction); the "maintenance label" observation (false — this run never opens a PR, so there is nothing to have labeled yet).

**Follow-up review recommendation: true.** Three medium-severity entries were patched this pass (the `check()` coverage gap, the `_listed_files` history-dump bug, and the `.gitignore` parity gap). Named unverified risk: `_artifact_stamp`'s sidecar-consuming branch (reading a real `<artifact>.stamp.json`) has never been exercised against an actual sidecar file in this session — no deck in the repo has one yet (that mechanism is only wired up for the `.potx` export path from Story 23.3) — so its behavior once real sidecars start appearing (via Story 23.6's `sync-all` or wider `write_stamp` adoption) is unverified beyond the fallback path exercised here.

**Verification performed:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test` (spec's mandated command): 1411 passed, 4 skipped — both before and after the patch pass.
- `pixi run -e site site-check` (manual check): passes both before and after the patch pass — `checks passed — 7 required outputs, 10 infographics, 10 deck families`; confirmed live that the download-dedup fix reduced `pyforge-atlas`'s downloads from 6 PPTX/11 Marp to 2 PPTX/5 Marp.
- Matrix Test Audit: the intent-contract's sole row (`site-check` passes after the family pages land) is covered by the manual `site-check` run above, re-run and re-verified after patching.
- Confirmed via grep: `dashboard.yml` remains the only workflow calling `deploy-pages`; `docsite/content/site.yml` still links `kedro-viz/`.
- Diff re-read in full after patching (not just the subagent's report) to verify each of the 9 patches against the actual code.

**Residual risks:** the deferred CI-gating gap above; the `_artifact_stamp` sidecar-path named above; the two rejected-low findings (family-page description over-claiming, bare-substring decks-index check) remain latent but low-impact and are not expected to manifest under current data.
