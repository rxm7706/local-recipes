---
title: '23.3: Sunset docs/specs/ by frontmatter status'
type: 'feature'
created: '2026-09-18'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: []
deferred: []
declared_low_risk: false
baseline_revision: 'bafc0b901c0c7809b5dba10870666d73b16095ce'
---

<intent-contract>

## Intent

**Problem:** 19 legacy intake specs live in `docs/specs/` with a YAML `status:` frontmatter field, but the directory mixes shipped/superseded historical records with live in-progress and re-runnable workflow docs, and nothing enforces that split.

**Approach:** Classify all 19 by their own frontmatter `status:` and relocate accordingly: `shipped`/`superseded` (14 files) move wholesale to `archive/docs/specs/`; `in-progress` (2 files) stay exactly where they are; `workflow` (3 files) have their body relocated to `docs/how-to/`, leaving a `status: workflow` stub + pointer behind at the original `docs/specs/<name>.md` path.

## Boundaries & Constraints

**Always:**
- No `shipped`/`superseded` Tier-1 spec remains the live home of its content under `docs/specs/`.
- `python scripts/bmad_drift_check.py --specs` still lists the three workflow stubs (by filename, with `status: workflow`).
- CLAUDE.md's Project Documentation Reference / Intake specs section still names all three workflow-stub filenames.

**Never:**
- Do not drop or narrow the `--specs` glob of `docs/specs/*.md` in `scripts/bmad_drift_check.py` — do not edit that script at all.
- Do not author new specs under `docs/specs/`.
- Do not rewrite the internal body content of the 14 `shipped`/`superseded` files being archived — they are frozen historical records (several explicitly say "historical record", "do NOT re-run BMAD on it/any part" in CLAUDE.md today) full of internal cross-references to each other and to sub-specs that no longer exist as separate files; rewriting those cross-references is out of scope and would touch thousands of unrelated lines across files up to 7764 lines long. `git mv` them verbatim.
- Do not touch `feedstock-refresh.md` or `flyte-conda-forge.md` (the two `in-progress` specs) or their CLAUDE.md rows at all.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| shipped/superseded intake | `docs/specs/<name>.md` frontmatter `status: shipped` or `status: superseded` | file lives at `archive/docs/specs/<name>.md`; no longer under `docs/specs/`; body content byte-identical (pure `git mv`) | n/a |
| workflow | `docs/specs/<name>.md` frontmatter `status: workflow` | body lives at `docs/how-to/<name>.md`; a new stub at `docs/specs/<name>.md` with `status: workflow` frontmatter + a pointer to the new body location | n/a |
| in-progress | `docs/specs/<name>.md` frontmatter `status: in-progress` | unchanged — no move, no content edit | n/a |

</intent-contract>

## Code Map

Full classification of all 19 files currently in `docs/specs/*.md`, established by reading each file's own frontmatter `status:` (verified 2026-09-18; re-verify if this spec is resumed later and the directory listing has changed):

- **`shipped` (10) — move to `archive/docs/specs/`:** `bmad-loop-adoption.md`, `cfe-atlas-datapipeline-kedro-migration.md`, `cfe-shipped-releases.md`, `conda-forge-tracker.md`, `cyclonedx-universe-inventory.md`, `db-gpt-conda-forge.md`, `langflow-conda-forge.md`, `lts-registry-gap.md`, `pyforge-warden.md`, `seed-gap-suggesters.md`
- **`superseded` (4) — move to `archive/docs/specs/`:** `bmad-copilot-adapter-upstream.md`, `claude-team-memory.md`, `copilot-bridge-vscode-extension.md`, `trendshift-conda-forge.md`
- **`workflow` (3) — body to `docs/how-to/`, stub stays at `docs/specs/`:** `feedstock-failure-remediation.md`, `feedstock-platform-expansion.md`, `presentation-deck.md`
- **`in-progress` (2) — untouched:** `feedstock-refresh.md`, `flyte-conda-forge.md`

Supporting facts gathered during investigation (rely on these; do not re-derive):

- `archive/docs/specs/` already exists and currently holds only a `gists/` subdirectory (an unrelated earlier archival wave). The 14 files land flat inside it (no new subdirectory).
- `docs/how-to/README.md` has a `## Guides` table indexing every file in that directory; it does not yet mention the 3 relocated files.
- `archive/docs/README.md` documents every item under `archive/docs/` with a short bullet per arrival wave (see its `specs/gists/*` bullet for the existing pattern).
- `scripts/bmad_drift_check.py::cmd_specs()` (invoked as `--specs`) globs `docs/specs/*.md` **non-recursively** and, for each file, reads `status:` via `frontmatter_status()` (regex `^\s*status\s*:\s*([A-Za-z-]+)`, unquoted values only — the existing 3 workflow files already use unquoted `status: workflow`, keep that convention in the new stubs) and reports whether the bare filename (e.g. `feedstock-failure-remediation.md`) appears anywhere as a **substring** of `CLAUDE.md`'s text. Read-only reference — do not edit this script; after the move it will report exactly 5 files (2 `in-progress` + 3 `workflow`).
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/factory.py::check_spec_indexed()` / `check_tier_alignment()` implement the same two rules (indexed-by-substring-in-CLAUDE.md; non-`.md` files under `docs/specs/` are misfiled) as a doctor advisory source. Read-only reference — do not edit.
- Existing repo precedent for a "moved" stub (`docs/reference/manticore-studio.md`, from Story 22.5): a short `# Moved` file with a relative markdown link to the new location. Reuse this shape, but our stubs additionally need `status: workflow` frontmatter (the two rules above read it).
- Two of the three `workflow` files contain a **self-referential** `docs/specs/<own-name>.md` path inside their own body (an example BMAD invocation, or a sentence describing their own tier placement). Since these 3 files remain **live, re-runnable** documents (unlike the 14 archived ones, which are explicitly historical/frozen), these self-references must be corrected so they keep pointing at the real content after the move:
  - `docs/specs/feedstock-platform-expansion.md` line ~19: `` run quick-dev — implement docs/specs/feedstock-platform-expansion.md `` inside a fenced example block — the path must become `docs/how-to/feedstock-platform-expansion.md` once the file lives there.
  - `docs/specs/presentation-deck.md` lines ~45–46: `` (This file itself predates the model and remains in the legacy `docs/specs/` tier as a **timeless workflow** doc.) `` — this sentence describes the file's own location and becomes false; rewrite it to describe the new location (body now in `docs/how-to/`, stub retained in `docs/specs/`).
  - `feedstock-failure-remediation.md` has no such self-reference — none needed.
  - None of the 14 archived files' internal cross-references (there are many, including to each other and to sub-specs that no longer exist as standalone files) should be touched — they are frozen historical prose. None of the 2 `in-progress` files or the CLAUDE.md rows for them need any change — verified they contain zero `docs/specs/` mentions.
- `CLAUDE.md`'s "### Intake specs (`docs/specs/` — LEGACY Tier 1, being phased out)" section (currently around line 215) contains 4 tables (`Active (in-progress)`, `Ready (backlog, unimplemented): none`, `Timeless workflows`, `Shipped (historical record)`) plus one earlier bullet at line ~212 referencing `` `docs/specs/presentation-deck.md` `` § *The MCP bridge* (a pointer to actual section content inside that file, not an index-table entry).
- Occurrence counts of each filename's exact path string `docs/specs/<name>.md` inside `CLAUDE.md` today (verified by grep): every shipped/superseded filename except `trendshift-conda-forge.md` appears **exactly once** (its table-row leading cell). `trendshift-conda-forge.md` appears **3 times** (its own row's leading cell, plus two inline mentions inside the `cfe-atlas-datapipeline-kedro-migration.md` row and inside its own row's prose). `presentation-deck.md` appears **twice**: once at line ~212 (the MCP-bridge pointer, which must become `docs/how-to/presentation-deck.md` since it points at real § content) and once as its Timeless-workflows row's leading cell (which stays `docs/specs/presentation-deck.md` — see Tasks). `feedstock-platform-expansion.md` and `feedstock-failure-remediation.md` each appear once (their own row's leading cell only).

## Tasks & Acceptance

**Execution:**

1. **Move the 14 `shipped`/`superseded` files verbatim:** for each filename in the `shipped`+`superseded` lists above, run `git mv docs/specs/<name>.md archive/docs/specs/<name>.md`. Do not open or edit their contents.

2. **Move the 3 `workflow` bodies:** `git mv docs/specs/feedstock-failure-remediation.md docs/how-to/feedstock-failure-remediation.md`, `git mv docs/specs/feedstock-platform-expansion.md docs/how-to/feedstock-platform-expansion.md`, `git mv docs/specs/presentation-deck.md docs/how-to/presentation-deck.md`.

3. **Fix the two self-references** inside the moved workflow bodies (now under `docs/how-to/`), per the Code Map above: update `feedstock-platform-expansion.md`'s example invocation path, and rewrite `presentation-deck.md`'s self-location sentence to describe the new `docs/how-to/` body + `docs/specs/` stub split. Keep both edits to the one sentence/line each — do not rewrite surrounding prose.

4. **Create 3 new stub files** at `docs/specs/feedstock-failure-remediation.md`, `docs/specs/feedstock-platform-expansion.md`, `docs/specs/presentation-deck.md` (same 3 filenames, now empty at that path after step 2's `git mv`). Each stub's full content:
   ```markdown
   ---
   status: workflow
   ---

   # Moved

   This workflow's operational body relocated to
   [`docs/how-to/<name>.md`](../how-to/<name>.md) (Story 23.3). This stub
   stays so `docs/specs/*.md` keeps indexing the filename and
   `scripts/bmad_drift_check.py --specs` keeps reporting `status: workflow`.
   ```
   (substitute the real `<name>.md` and matching relative link for each of the 3).

5. **`docs/how-to/README.md`** — add 3 rows to the existing `## Guides` table (any position is fine; appending after the last existing row, before the closing "See `docs/MAP.md`..." line, is simplest):
   - `feedstock-failure-remediation.md` — a short topic description (e.g. "Red feedstock-PR remediation loop: triage FLAKE/REAL_FIX/BLOCKED, execute-locally-first, rerender-after-push")
   - `feedstock-platform-expansion.md` — (e.g. "Refresh a feedstock to the latest CFE shape and widen its build matrix in one PR")
   - `presentation-deck.md` — (e.g. "Claude Design prototype → self-contained React/Vite slide deck (Marp + PPTX exports)")
   Match the existing table's link + description style exactly (see the `one-chain-station-ops.md` row for the pattern).

6. **`archive/docs/README.md`** — append one new bullet after the existing `specs/gists/*` bullet, documenting this arrival wave, e.g.:
   ```markdown
   - `specs/*.md` (14 files, added 2026-09-18) — shipped/superseded Tier-1 intake
     specs sunset per their own frontmatter `status:` (Story 23.3); `docs/specs/`
     itself keeps the two `in-progress` specs plus the three `workflow` stubs
     (bodies moved to `docs/how-to/`).
   ```

7. **`CLAUDE.md` edits** (all within the "Intake specs" section unless noted):
   - a. Append one clause to the existing legacy blockquote (the 4-line `> **Legacy.** ...` paragraph currently ending "...during the transition.") noting the new split, e.g. add a line: `` > `shipped`/`superseded` specs sunset to `archive/docs/specs/` by their own frontmatter `status:` (Story 23.3); `docs/specs/` itself keeps only `in-progress` specs and the three `workflow` stubs (bodies moved to `docs/how-to/`). ``
   - b. For each of the **13** shipped/superseded filenames *other than* `trendshift-conda-forge.md`: in its table row, change the leading cell from `` `docs/specs/<name>.md` `` to `` `archive/docs/specs/<name>.md` ``. Leave the rest of the row's description text untouched.
   - c. For `trendshift-conda-forge.md` specifically: change **all 3** occurrences of the substring `docs/specs/trendshift-conda-forge.md` in `CLAUDE.md` to `archive/docs/specs/trendshift-conda-forge.md` (its own row's leading cell, the inline mention inside the `cfe-atlas-datapipeline-kedro-migration.md` row, and the inline mention inside its own row's prose).
   - d. For the line ~212 bullet (`` **`docs/dreams/pyforge-herald.md`** + **`docs/specs/presentation-deck.md`** § *The MCP bridge* ... ``): change `docs/specs/presentation-deck.md` → `docs/how-to/presentation-deck.md` there (this points at actual section content that moved).
   - e. For the 3 `Timeless workflows` table rows (`feedstock-platform-expansion.md`, `feedstock-failure-remediation.md`, `presentation-deck.md`): **leave the leading `` `docs/specs/<name>.md` `` cell unchanged** in all 3 (that's the stub CLAUDE.md must keep "indexing" per the Always constraint) — instead append one clause to each row's description, before the final closing `` | ``, noting the body relocation, e.g.: `` **Body relocated to `docs/how-to/<name>.md`** (Story 23.3); invoke `bmad-build` with that path — this stub carries `status: workflow` for indexing.``
   - Do not touch the `Active (in-progress)` table rows for `flyte-conda-forge.md` / `feedstock-refresh.md`, and do not touch the "Ready (backlog, unimplemented): none." note block (it references bare filenames with no `docs/specs/` prefix, nothing to fix there).

**Acceptance Criteria:**
- Given the 14 `shipped`/`superseded` files, when the move completes, then `find docs/specs -maxdepth 1 -name '*.md'` no longer lists any of them and `find archive/docs/specs -maxdepth 1 -name '*.md'` lists all 14, with content identical to before the move (pure rename, `git diff --stat` shows no content-changed lines for these 14).
- Given the 2 `in-progress` files, when the move completes, then they are still at their original `docs/specs/<name>.md` path with zero content changes.
- Given the 3 `workflow` files, when the move completes, then `docs/how-to/<name>.md` holds the real body (with the 2 self-reference fixes applied where noted) and `docs/specs/<name>.md` is a small stub carrying `status: workflow` frontmatter and a working relative link to the new location.
- Given the reorganized tree, when `python scripts/bmad_drift_check.py --specs` runs, then it reports exactly 5 files under `docs/specs/` (the 2 `in-progress` + 3 `workflow`), every one shows `INDEXED yes`, and the totals line reads `in-progress=2  workflow=3`.
- Given `CLAUDE.md`, when inspected, then it no longer states or implies any `shipped`/`superseded` spec lives at `docs/specs/<name>.md` (all 14 references now point at `archive/docs/specs/<name>.md`), and it still names all three workflow-stub filenames.

## Binding

Parent Spec capability: `spec-docs-shelf-alignment CAP-3`.
Surface: docs/specs/, docs/how-to/, archive/docs/specs/, CLAUDE.md, scripts/bmad_drift_check.py --specs..
Ledger key: `23-3-sunset-docs-specs-by-frontmatter-status`.
Minted 2026-09-16 from `epics.md` so `marshal factory dispatch` can resolve `spec-23-3-sunset-docs-specs-by-frontmatter-status.md`.

## Verification

**Commands:**
- `python scripts/bmad_drift_check.py --specs` -- expected: `docs/specs intake specs (5)`, table lists only `feedstock-refresh.md`, `flyte-conda-forge.md`, `feedstock-failure-remediation.md`, `feedstock-platform-expansion.md`, `presentation-deck.md`, all `INDEXED yes`, totals line `in-progress=2  workflow=3`.
- `find docs/specs -maxdepth 1 -name '*.md' | wc -l` -- expected: `5`.
- `find archive/docs/specs -maxdepth 1 -name '*.md' | wc -l` -- expected: `14` (was `0` flat files before, only the `gists/` subdir existed).
- `grep -l "^status: workflow$" docs/specs/*.md | wc -l` -- expected: `3`.
- `git status --short` -- expected: shows `R` (rename) entries for all 17 moved files, `A` (added) entries for the 3 new stubs, `M` entries for `CLAUDE.md`, `docs/how-to/README.md`, `archive/docs/README.md`, and the 2 touched workflow bodies under `docs/how-to/` (content-edited, not pure renames, because of the self-reference fixes) -- and nothing else.
- `grep -c "docs/specs/" CLAUDE.md` -- sanity count after edits; every remaining hit should resolve to either an `in-progress` file, a workflow-stub row/note, or prose unrelated to a specific spec's location (manually eyeball the `grep -n "docs/specs/" CLAUDE.md` output once to confirm no leftover `shipped`/`superseded` path).

**Manual checks (if no CLI):**
- Open the 3 new stub files and confirm each renders as a normal markdown "Moved" page with a clickable relative link that resolves to a real file.
- Confirm none of the 14 archived files' internal body content was modified (`git diff archive/docs/specs/` should be empty aside from the rename itself when diffed with `git diff -M`).

## Review Triage Log

### 2026-09-18 — Review pass
- verdicts: 13 findings — high 0, medium 4, low 2, false 7, maybe-false 0
- findings:
  - `[medium]` `[patch]` Blind Hunter: `archive/docs/specs/cfe-shipped-releases.md:7684` and `archive/docs/specs/langflow-conda-forge.md:413` contain relative markdown links (`../../.claude/skills/...`) written for the old 2-deep `docs/specs/` location; the move to 3-deep `archive/docs/specs/` breaks them (verified: both links exist, both now resolve one directory short) — action: prepend one more `../` in both.
  - `[medium]` `[patch]` Blind Hunter: `docs/how-to/presentation-deck.md:25` still reads "This is a **framework-neutral intake spec** (Tier 1, per `AGENTS.md`)", contradicting the Genesis section a few lines below (already edited by this diff) which says the body now lives in `docs/how-to/` as a workflow doc — verified real, same file/self-reference class as the already-fixed sentence, just an incomplete sweep — action: rewrite the sentence to describe the how-to/workflow home instead of "Tier 1 intake spec".
  - `[medium]` `[patch]` Verification Gap Reviewer: `AGENTS.md:240` still points at `` `docs/specs/presentation-deck.md` § *The MCP bridge* `` — an identical pointer in `CLAUDE.md` was already repointed to `docs/how-to/presentation-deck.md` by this diff, but the twin in `AGENTS.md` was missed (verified: confirmed the AGENTS.md line, confirmed no `diff --git a/AGENTS.md` hunk exists) — action: apply the same one-line fix.
  - `[medium]` `[patch]` Blind Hunter: `docs/MAP.md` untouched — its "Legacy intake specs (Tier 1)" row is now imprecise (doesn't mention the archive split) and it lacks rows in its own established "Relocated in Story 22.5" table for the 3 workflow-file moves, unlike the precedent already set there for `antigravity-developer-startup.md`/`manticore-studio.md` ("Redirect stub at old path") — verified real staleness against a real established pattern in the same file — action: add 3 rows following that exact pattern, and touch up the Legacy-specs row's description.
  - `[low]` `[reject]` Blind Hunter: `docs/how-to/feedstock-platform-expansion.md` / `feedstock-failure-remediation.md` keep "Tech Spec:"/"BMAD-consumable tech-spec" framing instead of the how-to directory's task-oriented voice (grouped with the parallel heading/voice-convention finding, same root cause) — real stylistic mismatch, but restyling parameterized BMAD-invocable spec prose into how-to voice is more than a direct correction and was a deliberate tradeoff (both CLAUDE.md rows explicitly tell readers to `invoke bmad-build with that path`) — not worth it for this story.
  - `[low]` `[reject]` Blind Hunter: the 3 new `docs/specs/<name>.md` stubs drop the original `spec_updated:` frontmatter field present on the 3 pre-move files — verified real (grep confirms absence), but the value isn't lost (the real file at `docs/how-to/` still carries it unchanged) and nobody is expected to read a stub's frontmatter for a currency date — reject, unlikely to be met in everyday use.
  - `[false]` `[reject]` Blind Hunter: `archive/docs/README.md`'s header sentence (dated 2026-07-23) wasn't updated to acknowledge the new 2026-09-18 arrival bullet — checked: the new bullet is self-dated and self-explanatory; the header's "retaining its original directory structure" claim is still true of the directory *shape* (link-depth breakage is a different claim, already handled above) — no bad outcome.
  - `[false]` `[reject]` Blind Hunter: `docs/specs/feedstock-refresh.md` (untouched, `in-progress`) delegates to `feedstock-platform-expansion.md` expecting inline Wave A/B/C content, now a stub — checked: the stub redirects to the real content in one hop, exactly the designed mechanism; the reference still resolves, nothing breaks.
  - `[false]` `[reject]` Blind Hunter: ~50+ repo references to `docs/specs/presentation-deck.md` (active herald specs, `presentations/*/README.md`, dream docs) weren't swept to the new path — checked: same stub-redirect design as above, and matches this repo's own established precedent (`docs/MAP.md`'s Story 22.5 table: inbound references to `antigravity-developer-startup.md`/`manticore-studio.md` were likewise never swept when those files moved, only a stub was left) — no bad outcome.
  - `[false]` `[reject]` Blind Hunter: ~10 references to `feedstock-platform-expansion.md` / 4 to `feedstock-failure-remediation.md` in `_bmad-output/pyforge-steward/`, `_bmad-output/pyforge-mason/`, `docs/dreams/pyforge-steward-feedstock-maintenance.md` unswept — same reasoning as the presentation-deck.md row above — no bad outcome.
  - `[false]` `[reject]` Blind Hunter: `CLAUDE.md`'s Timeless-workflows table rows keep their full multi-sentence descriptions alongside the new relocation note, "duplicating" content — checked: every row in that table (and the Shipped table) already carries a full descriptive summary; this is the table's normal, pre-existing indexing convention, not the kind of satellite-planning-doc duplication the "one canonical artifact" convention targets — no bad outcome.
  - `[false]` `[reject]` Intent Alignment Auditor: no verification artifact (new test/fixture) ships with the diff for the two named "Always" constraints — checked: the pre-existing `scripts/bmad_drift_check.py --specs` and `pyforge.doctor.sources.factory::check_spec_indexed`/`check_tier_alignment` already serve as the permanent regression guard for this invariant going forward (nothing about them needed to change), and I ran and confirmed every `## Verification` command in this spec by hand during implementation — no bad outcome.
  - `[false]` `[reject]` Intent Alignment Auditor: ~60 stale references to the 14 archived files scattered across `.claude/skills/conda-forge-expert/CHANGELOG.md` (23), `SKILL.md` (16), `reference/atlas-phase*-overview.md`/`atlas-phase-engineering.md` (10), `pixi.toml` (6), `docs/reference/library-llms-full.md` (2), and two package READMEs/AGENTS.md files (1 each) — checked each cluster: the 39 CHANGELOG.md/SKILL.md hits are dated historical narrative describing point-in-time facts (same category as CLAUDE.md's own untouched "Shipped (historical record)" prose, which this diff deliberately leaves alone elsewhere per the repo's own `feedback_historical_prose_keeps_original_names` convention); the `pixi.toml` hits are inert `#` comments / `description =` strings never opened or parsed by any script (verified: none of the 6 lines is a functional path argument); none of these files is in the story's declared Surface (`docs/specs/`, `docs/how-to/`, `archive/docs/specs/`, `CLAUDE.md`, `scripts/bmad_drift_check.py --specs`) — no bad outcome that this story is responsible for.
  - Patches applied and independently re-verified (relative-link resolution checked directly, `git diff` confirmed each touched file changed by exactly the intended line/paragraph): the 4 `[medium]``[patch]` findings above.

## Auto Run Result

> Landed 2026-09-18 as PR #1445 (`a8996d5abe`, branch `dispatch/pyforge-doctor/23.3`) — the ledger row stayed `backlog` and this twin was never promoted (the run's worktree was torn down); recovered 2026-09-19 from the session transcript (`~/.claude/projects/…dispatch-pyforge-doctor-23-3/3c6f060c…jsonl`, Write + 10 Edits replayed) when a re-dispatch found `story_merged_on_main`.

**Summary:** Classified all 19 `docs/specs/*.md` legacy intake specs by their own frontmatter `status:`. Moved the 14 `shipped`/`superseded` files verbatim to `archive/docs/specs/` (pure `git mv`, byte-identical). Left the 2 `in-progress` files untouched. Relocated the 3 `workflow` files' bodies to `docs/how-to/`, leaving a `status: workflow` redirect stub at each original `docs/specs/<name>.md` path. Updated every live index/pointer this move touches (`CLAUDE.md`, `docs/how-to/README.md`, `archive/docs/README.md`, `docs/MAP.md`, `AGENTS.md`) so nothing live claims a moved file still lives at its old path, while deliberately leaving dated historical narrative (CHANGELOG.md, shipped-spec cross-references, other BMAD projects' planning artifacts) untouched per the repo's own convention that historical prose keeps its original names.

**Files changed:**
- 14 `git mv docs/specs/<name>.md → archive/docs/specs/<name>.md` (pure renames; 2 of them — `cfe-shipped-releases.md`, `langflow-conda-forge.md` — got one follow-up line fixing a relative link broken by the extra directory depth)
- 3 `git mv docs/specs/<name>.md → docs/how-to/<name>.md` (bodies; `feedstock-platform-expansion.md` and `presentation-deck.md` each got one self-referential sentence corrected to describe their new home)
- 3 new `docs/specs/<name>.md` stub files (`status: workflow` + pointer to the new `docs/how-to/` location)
- `CLAUDE.md` — repointed all 14 archived-file references, the `presentation-deck.md` MCP-bridge pointer, and appended relocation notes to the 3 workflow rows
- `AGENTS.md` — repointed the twin MCP-bridge pointer to `docs/how-to/presentation-deck.md`
- `docs/MAP.md` — added a "Relocated in Story 23.3" table (3 rows) and touched up the Legacy-intake-specs row
- `docs/how-to/README.md` — added 3 rows for the relocated guides
- `archive/docs/README.md` — added one bullet documenting the 14-file arrival wave

**Review findings breakdown (13 total across 4 layers: Blind Hunter 10, Edge Case Hunter 0, Verification Gap Reviewer 1, Intent Alignment Auditor 2):**
- 4 `patch` (medium): 2 broken relative links in archived files, 1 incomplete self-reference sweep in `presentation-deck.md`, 1 missed `AGENTS.md` pointer twin, plus the `docs/MAP.md` completeness gap — all applied and re-verified (see Review Triage Log above for exact locations).
- 2 `reject` (low): stylistic "Tech Spec" framing left on 2 of 3 relocated how-to guides (deliberate — they stay `bmad-build`-invocable); `spec_updated` frontmatter dropped from the 3 stubs (value preserved on the real file, not lost).
- 7 `reject` (false): all verified as by-design (the stub-redirect pattern matches this repo's own established Story-22.5 precedent for unswept inbound references) or genuinely out of this story's declared Surface (dated historical narrative in CHANGELOG.md/SKILL.md/other BMAD projects' planning artifacts, and inert `pixi.toml` comments) — see Review Triage Log for the full refutation of each.
- 0 `defer`, 0 `intent_gap`, 0 `bad_spec`.

**Follow-up review recommendation: `true`** (2+ `medium`-verdict findings were patched this pass, per the mechanical rule — never a volume judgment call). Named unverified risk: the 4 patches were independently re-verified by direct inspection (link resolution, scoped `git diff` per file) rather than by a fresh full 4-layer review pass over the patched diff itself, so a follow-up pass should re-scan for anything the patches themselves might have introduced (e.g. `docs/MAP.md` table formatting, line-wrap correctness in the rewritten `AGENTS.md`/`presentation-deck.md` sentences).

**Verification performed:** `python scripts/bmad_drift_check.py --specs` (5 files, `in-progress=2 workflow=3`, all `INDEXED yes`); `find docs/specs -maxdepth 1 -name '*.md' | wc -l` = 5; `find archive/docs/specs -maxdepth 1 -name '*.md' | wc -l` = 14; `grep -l "^status: workflow$" docs/specs/*.md | wc -l` = 3; `pixi run -e pyforge-guild python -m pyforge.doctor.sources bmad-drift` clean of any `spec-unindexed`/`docs-specs-nonmd`/`tracked-impl-artifact` finding; both fixed relative links confirmed to resolve on disk; `git status --short` confirmed the expected file set and nothing else; every archived file confirmed byte-identical via `similarity index 100%` in the diff except the 2 that got the link fix.

**Residual risks:** none rated `medium`+ remain unaddressed. The full inventory of stale-but-out-of-scope references (CHANGELOG.md, SKILL.md, atlas reference guides, `pixi.toml` comments) is recorded in the Review Triage Log for a future dedicated sweep if ever prioritized — none of it is load-bearing for any script or gate today.
