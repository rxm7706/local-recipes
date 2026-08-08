# pyforge-steward — Whole-Build Retrospective

**Scope:** Epics 1-4, stories 1.1-4.3 (18/18 done) — Keys (credential lifecycle), Deploy (reconciled
dashboard publishing), Provision (environment/runner access), Budget (declared resource ceilings).
**Retro produced:** 2026-08-08 (single retrospective covering the whole build — none existed prior to
this; a hygiene audit flagged the gap since Warden and Atlas both carry tracked per-epic retros and
Steward carried none).
**Facilitator:** Amelia (Developer, adapted) · **Project Lead:** rxm7706

> Format note: solo / AI-driven bmad-loop effort — substance run faithfully, no fabricated team
> dialogue. Grounded in `epics.md`, all 18 story specs' Review Triage Logs, and the actual merge
> commits on `main` (PRs #157, #291, #297, #302, #305 + the standalone scaffold commits).

## Delivery snapshot

Four epics, each landed as one merged batch: Story 1.1 (scaffold — package, `Duty` protocol,
exit-code-owning dispatcher) landed standalone; Stories 1.2+1.3 (host-scoped credentials + `age`
encryption) merged via PR #157; Stories 1.4-1.7 (rotate/list/audit/revoke) merged via PR #291 with
its own close-out review commit (`06d736a4e5`); Epic 2 (Stories 2.1-2.4, dashboard reconcile) merged
via PR #297 with review-fix commit `c854c2d869`; Epic 3 (Stories 3.1-3.4, provision) merged via
PR #302 with review-fix commit `078c2994b7`; Epic 4 (Stories 4.1-4.3, budget) merged via PR #305 with
review-fix commit `04ab96f873`. Every epic's merge was followed by a sprint-ledger sync and a dashboard
regen commit — the paper trail is consistent and traceable end to end.

## What went well

- **The close-out adversarial review caught a real, distinct bug in every single epic** — not a
  formality. Epic 1: two independently-converged findings (inventory race, ambiguous-active-entry
  resolution) on `keys-inventory.yaml`'s read-modify-write path (`06d736a4e5`). Epic 2: four findings
  in one pass (commit-scope leakage, detached-HEAD ordering, a permanently-stuck failed push, a
  status report that lied about an unpushed commit) (`c854c2d869`). Epic 3: the `--json` error-path
  bug (below). Epic 4: an uncaught `TypeError` on a malformed `ceilings` field plus a silently
  unvalidated `declared_at`. Four epics, four for-real defects, zero "nothing found" passes — this is
  the strongest empirical argument in this build for keeping close-out review mandatory, not optional.
- **Rotation's backward-compatibility property held from spec to code.** Story 1.4's whole premise —
  "rotating a key never breaks what already trusted it" — is exactly the auto-memory finding already
  on record for this domain. The spec's own Design Notes are explicit about *why*: two inventory
  fields (`scope` stable, `name` per-generation) so a retired record and its replacement can coexist
  inspectably, rather than an in-place field flip that erases what it replaced. The close-out review
  then found the one way that promise could still be violated in practice — a concurrent
  `rotate`/`revoke` race clobbering the other writer's update — and fixed it with `fcntl.flock` +
  atomic `os.replace`, proven with two real racing threads (`test_concurrent_rotations_do_not_lose_an_update`),
  not just asserted. The architectural intent and the eventual hardening match cleanly.
- **AD-1 ("wrap, never reimplement") held under real pressure.** Story 3.4 (`environment.yaml` sync
  gate) deliberately read the comparison semantics straight out of
  `.github/workflows/scripts/linter.py:65-70` rather than re-deriving them from CLAUDE.md's prose
  summary — the spec's own Design Notes call out that a prose-derived reimplementation risks silently
  disagreeing with CI on an edge case (trailing-newline sensitivity). Story 3.1 similarly caught its
  own near-miss live: a naive `pixi.toml`-as-repo-root-marker would have resolved to the *package's
  own* `pixi.toml` (no `[environments]` table) instead of the true repo root, so it uses
  `scripts/bmad-loop-worktree`'s unique existence as the marker instead.
- **Cross-station review paid off immediately.** `9b28658d3f` — Marshal's independent review pass on
  its own first story caught that Steward's (and Mason's) freshly-written `build-conda` pixi tasks
  used a `--manifest-path` flag that does not exist on `pixi build` (verified live against pixi
  0.73.0). The fix was applied to both stations' tasks the same day. This is the review-is-a-second-set-of-eyes
  principle (adopted from Atlas's retro action A1) working across station boundaries, not just within
  one.
- **The Epic 1 "fail-loud, never fail-silent" hardening on the plaintext-secret scanner was genuinely
  iterative and effective.** Across three review passes on Story 1.2/1.3, the scanning primitives were
  hardened against: an unreadable subdirectory swallowed by `Path.rglob`'s `PermissionError`, a
  dangling symlink silently reported clean, and a UTF-16-encoded secret (interleaved NULs defeating
  every regex) scanned as clean. Each was confirmed by execution before being patched, not assumed.

## What was harder than expected / recurring patterns (2+ independent occurrences)

- **The `--json` error path silently degrading to plain text is a systemic bug class, found
  independently twice.** Epic 3's close-out review (`078c2994b7`) found that any error inside
  `ProvisionDuty.run` (malformed/missing `pixi.toml`, a `repo_root()` failure) rendered as plain text
  regardless of `--json`, because `cli.main()`'s dispatch had no JSON-aware error rendering at all —
  a caller unconditionally `json.loads()`-ing the output crashed on any error path, not just the
  happy one. Story 4.2's own self-review then found the *identical shape* of bug in `BudgetDuty.run`
  before it ever shipped (`show`'s happy path honored `--json`, but its `except BudgetError` branch
  returned a bare `str(exc)` regardless of the flag) — the story spec explicitly credits Epic 3's
  finding as the reason it went looking. Two duty modules, same defect shape, found on two separate
  passes. This is a pattern that should have been caught once and prevented structurally (e.g. a
  shared `_render_error(ns, message)` helper established in `interfaces.py` at Story 1.1, used by
  every duty from day one) rather than patched twice in two different modules.
- **Host-canonicalization in the credential resolver (`_canonical_host`) needed three separate review
  passes to converge**, each finding a real, executable-confirmed defect: empty/garbage hosts entries
  matching nothing (pass 1), IPv6 literals corrupted by a naive `rsplit(":", 1)` — two *different*
  IPv6 addresses canonicalizing to the same wrong string (pass 2) — and any single-colon suffix being
  treated as a port, so `"https:artifactory.example.com"` silently canonicalized to `"https"` (pass
  3). This is the highest-stakes code in the whole build (it directly implements the FR-7 JFrog-leak
  regression), and it is reassuring that the iteration converged with regression tests at each step —
  but three passes to get one normalization function right is a real cost, and suggests host-string
  parsing should have been scoped as its own small, dedicated spec/story from the start rather than
  one AC inside Story 1.2.
- **Read-modify-write race protection was decided three different ways across three epics, and each
  decision was actually justified rather than copy-pasted.** Epic 1 added real file-locking
  (`fcntl.flock` + atomic replace) for `keys-inventory.yaml` because nothing else serializes concurrent
  writers to a bespoke YAML file. Epic 2 explicitly declined a lock for the dashboard reconcile step,
  reasoning that `git`'s own `.git/index.lock` already serializes concurrent `add`/`commit` at the
  filesystem level. Epic 4 never needed the question raised in its own reviews. This is good judgment,
  not inconsistency — but it took explicit "Design Notes" reasoning in two separate specs (1.4, 2.2)
  to establish, and a future duty module introducing a third piece of shared state should be pointed
  at those two Design Notes sections rather than re-deriving the tradeoff from scratch.
- **Epic 2's dashboard-reconcile logic needed four distinct fixes in one review pass** (`c854c2d869`):
  the commit accidentally swept in unrelated pre-staged files (no pathspec scoping), branch resolution
  ran after the commit rather than before (a detached HEAD could silently create an orphan commit), a
  failed push left the local commit permanently invisible to future runs (no retry), and `deploy
  status` reported an unpushed commit as a completed deploy. All four are variations on the same root
  cause — the git-reconcile sequence not being defensively ordered/scoped against real-world partial
  failure — which suggests the story's first draft under-invested in git-sequencing edge cases
  specifically (as opposed to the CLI-surface/argparse edge cases the other epics handled cleanly on
  the first pass).

## Corrections to process/skill guidance

- None of the findings above trace to `conda-forge-expert` skill guidance — Steward is a pure Python
  CLI-packaging effort with no recipe/conda-forge-submission surface, so the BMAD↔CFE integration
  rules (Rule 1/Rule 2) do not apply to this station's own work. No CFE-skill retro is owed for this
  effort. (Recorded explicitly per this repo's rule that an effort's retro must state this rather than
  silently omit it.)
- The recurring `--json`-error-path bug is a **bmad-quick-dev / spec-authoring** lesson, not a
  conda-forge-expert one: a duty-module template (established once, in Story 1.1, alongside the
  `Duty` protocol and the exit-code dispatcher) should have included an error-rendering contract that
  every subsequent duty module's spec inherits by reference, the same way the exit-code-ownership rule
  (AD-8) already is. This belongs in this station's own architecture spine or a future
  cross-station convention, not in `conda-forge-expert`.

## Lessons for future PyForge stations

1. **Close-out adversarial review is not optional overhead — it found a real bug in 4/4 epics of this
   build.** Any station tempted to skip it because "the self-review pass already looked clean" should
   read this retro first: Stories 3.1-3.4 and 4.1-4.3 both had clean self-reviews, and the close-out
   pass still found a real, shippable bug in each.
2. **When two duty/module boundaries share a rendering contract (e.g. "does this output honor
   `--json` on every code path, including errors"), establish it once as a shared primitive at
   scaffold time, not per-module.** This build re-discovered the same gap twice because the
   scaffold (Story 1.1) didn't standardize error rendering the way it standardized exit codes.
3. **Security-critical string-normalization logic (host/URL parsing, credential-scoping predicates)
   deserves its own dedicated story-sized surface, not one AC bundled into a larger story.** Story
   1.2's `_canonical_host` needed three review passes precisely because it was small enough to be one
   AC among several, not scoped with its own dedicated edge-case matrix from the start.
4. **git-sequencing logic (multi-step reconcile: diff → commit → push → status) is a distinct risk
   class from CLI-surface logic and should get its own explicit ordering/partial-failure review pass**
   — Epic 2 is the one epic in this build where a single review pass surfaced four related defects at
   once, all traceable to under-specified sequencing rather than isolated bugs.

## Action items

- **(low, deferred by design)** No fix needed for the shared-error-rendering gap retroactively — both
  known instances (`ProvisionDuty`, `BudgetDuty`) are already patched and regression-tested. Flag for
  a future Steward hardening pass: introduce a shared `render_error(ns, message)` helper in
  `interfaces.py` if a fifth duty module is ever added, so the pattern can't recur a third time.
- **(process, applies beyond Steward)** When scaffolding a new station's first story (the
  `interfaces.py`/dispatcher equivalent), explicitly include an error-rendering contract alongside the
  exit-code-ownership contract already established as convention (AD-8-equivalent). Candidate for a
  cross-station note in `_bmad-output/PROJECTS.md` or a shared architecture pattern doc.
- **(none required)** This retro itself closes the tracked gap identified by the hygiene audit —
  Steward now has a tracked whole-build retrospective at parity with Warden's and Atlas's per-epic
  retros.

## Readiness

18/18 stories done, 4/4 epics merged (PRs #157, #291, #297, #302, #305), every epic closed with a
review pass that found and fixed a real defect before merge. No open blockers. This retro is the
closeout artifact the hygiene audit found missing; no further action is required to consider
pyforge-steward's build phase complete.
