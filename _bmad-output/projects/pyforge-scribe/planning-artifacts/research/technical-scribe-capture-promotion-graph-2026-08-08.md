---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/retros/retro-scribe-2026-08-08.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/epics.md
  - docs/dreams/pyforge-scribe.md
  - .claude/memory/README.md
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/ (all seven modules, read in full)
workflowType: 'research'
lastStep: 6
research_type: 'technical'
research_topic: 'Scribe as shipped — capture/promotion/graph-compile/recall architecture, its concrete technical debt (the never-reviewed promote.py), and the uncaught-exception bug class the build surfaced twice'
research_goals: 'Document the real shipped architecture (not the planned one), name the review-debt and bug-class risks with evidence, and derive the hardening/opportunity backlog any post-1.0 Scribe work should start from'
user_name: 'Rxm7706'
date: '2026-08-08'
web_research_enabled: false
source_verification: true
mode: 'headless-express — grounded in the repo itself: the 2026-08-08 retro, the shipped source, git history, and the live .claude/memory/ + user-local auto-memory state; no external web claims in this report'
---

# Research Report: Technical Research — Scribe Capture, Promotion & Graph Architecture (as shipped)

**Date:** 2026-08-08
**Author:** Rxm7706
**Research Type:** Technical (post-ship; companion to the 2026-07-25 domain/market reports and their 2026-08-08 refreshes)

---

## Why this report exists

The 2026-07-25 research pair grounded Scribe's *planning*. Nothing yet documents what actually **shipped** — 9/9 stories across two epics (PR **#296** Epic 1 close-out, PR **#301** Epic 2), 88 passing tests, ~1,688 lines across seven modules in `src/shared/packages/pyforge-scribe/src/pyforge/scribe/`. This report is the missing technical tier: the real architecture, and — more importantly — the two concrete, evidence-backed technical-debt findings the 2026-08-08 retro surfaced: **`promote.py` has never been reviewed by anyone, ever** (§ Risk Register, RISK-1), and **the "uncaught exception crashes the unattended nightly pipeline" bug class shipped independently twice** (§ The recurring bug class).

---

## The shipped architecture

Scribe implements the architecture spine's event-sourced-capture / CQRS-lite paradigm end to end:

**Write side (Epic 1)** — `capture.py` (232 lines) is the *only* write path into `.claude/memory/` (AD-1/AD-2): locked (fcntl/msvcrt cross-platform advisory lock), no-clobber, appends the `MEMORY.md` index line inside the same critical section. The lock is not decorative — Story 1.1's original unlocked read-modify-write was reproduced losing 13 of 20 entries under a 20-thread race before the fix (retro § "harder than expected"). `promote.py` (389 lines) layers the promotion workflow on top: scan a user-local auto-memory dir → 4-way strict-priority classification (`already-promoted` → `stale` → `personal` → `team-relevant`) → mechanical regex team-voice rewrite (no LLM, AD-6) → a read-only `PromotionProposal` that writes **nothing** until human confirmation → `apply_promotion()` writes exclusively through `capture()`, then overwrites the *source* user-local file with a `promoted: true` pointer stub (FR-5/FR-6 — the one sanctioned write outside `.claude/memory/`).

**Projection (Epic 2)** — `compile.py` (375 lines) rebuilds the graph **from scratch every run** (never incremental, AD-1) from five named surfaces: `.claude/memory/`, `**/.memlog.md`, `**/CHANGELOG.md`, `**/*retro*.md`, and `git log` (local, read-only, capped at 100 commits). Output goes through the `GraphStore` protocol (`graph_store.py`, 214 lines, AD-5) into the v1 `FlatFileGraphStore` — one deterministic sorted-keys JSON file at `.claude/data/pyforge-scribe/graph.json` (gitignored, derived, disposable), committed via temp-file + `os.replace()` under the same advisory-lock pattern as `capture.py`. Supersession (`supersedes: "<type>/<slug>"` frontmatter) marks the prior node's bi-temporal validity ended — the Graphiti-derived invalidate-not-delete pattern the domain research recommended, implemented storage-engine-agnostically.

**Read side** — `recall.py` (102 lines): pure deterministic lexical token-overlap ranking over `is_current` nodes, citation resolvability verified **on the return path** (AD-8) — an unresolvable top match is skipped, and zero coverage returns the explicit `grounded=False` "no grounded answer found". FR-13 determinism was proven with two independent `FlatFileGraphStore` instances asserting byte-identical answers, not by code inspection.

**Verified-in-repo state (2026-08-08):** `.claude/memory/feedback/bmad-runs-cfe-retro.md` exists with its `MEMORY.md` index line (commit `ccecbf5f1c`, Story 1.5), and the real user-local source `~/.claude/projects/.../memory/feedback_bmad_runs_cfe_retro.md` is a live pointer stub (`promoted: true`, `promoted_date: 2026-08-07`). The loop closed on real data, produced by the tool.

---

## Risk Register

### RISK-1 (named, concrete, open): `promote.py` has never been reviewed — 389 lines of core promotion logic with zero review coverage, recovered from a dangling git commit

This is the single most consequential technical-debt item Scribe carries, and it is documented fact, not hypothesis:

- Story 1.3 was deferred 2026-07-30 as a dev-session timeout whose branch diffstat read "eight insertions" — i.e. *empty*. The real work — `promote.py` (339 lines then) + `test_promote.py` (457 lines), **1,102 insertions across 6 files** — existed only in **dangling commit `91d3571f10`** ("attempt worktree snapshot", author `bmad-loop`), unreachable from any ref, one `git gc` from permanent loss. A blocked Story 1.4 session found it by hand (`git log --all -- '*promote.py'` → `git cat-file -e` → reflog trace of two consecutive resets), and it was cherry-picked to main as **`70673665d7`**, merged via **PR #168** (merge commit **`d68187f4b3`**: "scribe: recover Story 1.3 from a DANGLING commit — 1,102 lines that were one gc from gone").
- Because the original session timed out **before** the loop's review phase, no follow-up review commit ever ran against it. The spec archive (`planning-artifacts/specs/spec-1-3-promotion-workflow-proposal-then-confirm-team-voice-rewrite.md`) carries **no Review Triage Log section at all** — the debt was inherited, never paid. 47-then-88 green tests and the merge gate covered it; **no reviewer has ever read the diff.**
- Why this specific file being unreviewed matters more than any other module being unreviewed:
  1. `promote.py` holds the **only sanctioned write outside `.claude/memory/`** — `write_pointer_stub()` destructively overwrites a user's auto-memory file, and per FR-5 the original body is *intentionally not preserved*. The user-local dir is not git-tracked: a wrong classification followed by a confirmed apply is **unrecoverable data loss**. That is exactly the code path an adversarial reviewer would stress first.
  2. Its classification heuristics are load-bearing judgment encoded as regex — and one already misfired live: at Story 1.5's seed promotion (`ccecbf5f1c`), `_find_missing_repo_path()` classified `feedback_bmad_uses_cfe_skill.md` **stale** on a single missing backticked path, so the epic's binding "both entries promoted" AC actually delivered **1 of 2**. The deviation was accepted as correct classify-then-confirm behavior, but note the mechanism: *any one* dangling path reference vetoes an otherwise team-relevant entry (first match wins, no severity distinction). The 2026-08-08 retro's own delivery snapshot still says both entries were promoted — the retro over-states what the commit record shows.
  3. Epic 2's independent adversarial pass found real crash bugs in code whose self-review had come back clean **twice** (see below). `promote.py` never received even the self-review the Epic 2 modules got. By the build's own measured base rate, it is the highest-likelihood residual-bug location in the package.
- The retro's first action item — "Retroactively review Story 1.3's `promote.py`/`test_promote.py`" — remains `[open]` as of this report. **Any post-1.0 Scribe effort should schedule this review as its first story**, ideally as a diff-only, no-shared-context adversarial pass (the configuration proven to find what self-review misses, per auto-memory `feedback_parallel_adversarial_review_validated.md`).

### RISK-2: the "nightly" compile has no scheduler — FR-11's unattended guarantee is untested in production

`compile_graph()` is unattended-*by-construction* (no prompts anywhere), but nothing actually runs it nightly: no `pixi.toml` task schedules it, no CI workflow invokes it (verified by grep, 2026-08-08). The `--nightly` flag is documented as "CLI/scheduling clarity only". Until a real scheduler exists, the crash-class bugs below had zero production exposure window — and the *next* one will have its first exposure in an unattended context where nobody sees the traceback. Wiring the compile into a real schedule (and deciding where its stderr warnings land) is an unclosed operational gap, not a code gap.

### RISK-3: Scribe's output is a trusted-context injection channel with the human preview removed

Operator decision 2026-07-31 (recorded in `pixi.toml`'s loop-approve-startup task description): the Claude CLI's CLAUDE.md external-import dialog is now pre-approved for loop homes — removing the one moment a human saw the list of files imported into the model's system context — and the imported file, `.claude/memory/MEMORY.md`, is **agent-written: Scribe's own output**. The residual control is that `.claude/memory/**` is git-tracked ("review the diff as instructions, not notes"). This makes `capture()`/`apply_promotion()`'s write path a prompt-injection surface by construction: anything that lands in team memory is injected into *every* future session of every agent. The team-voice rewrite is mechanical regex, not sanitization. Current mitigation is entirely the git-review convention; there is no in-tool guard (e.g. flagging imperative "always/never do X" phrasing entering via `--promote` from an unreviewed source). Worth an explicit design decision rather than an inherited default.

### RISK-4: flat-file scaling bounds are implicit

Full-rebuild-every-run over `repo_root.glob("**/...")` in a repo this size, `_MAX_DOC_TEXT_CHARS = 20_000` per node, 100-commit git window, whole graph deserialized into memory on every `recall`. Fine today; unmeasured. The AD-5 port means an adapter swap (the deferred embedded-engine question) is cheap *if* the trigger is defined — no story defines what "flat-file model provably runs out of headroom" means. A one-line benchmark task (compile wall-time + graph.json size, tracked over time) would convert this from vibes to data.

---

## The recurring bug class: one degraded input crashes the unattended pipeline

Epic 2's adversarial review (Blind Hunter + Edge Case Hunter, diff-only, no shared context, 2026-08-07 — landed as commit **`a53b5c581e`**, "fix Epic 2 review findings") found the same bug *class* independently in two stories, after each story's own self-review had passed clean and explicitly claimed the degradation guarantee held:

1. **`_read_git_surface` (Story 2.2):** `subprocess.run(text=True)` without `encoding=`/`errors=` — one non-UTF-8 commit raised `UnicodeDecodeError` (a `ValueError` subclass the surrounding `except (OSError, subprocess.TimeoutExpired)` did not catch), killing the entire compile. The shipped fix (`encoding="utf-8", errors="replace"`) is visible at `compile.py:283-285`.
2. **`_apply_supersession` (Story 2.3):** the supersession pass re-globbed and re-parsed `.claude/memory/*.md` a second time instead of reusing the first pass's records — a file deleted between the two scans (TOCTOU) raised an uncaught `FileNotFoundError`. The fix and its rationale are preserved verbatim as the "Review finding" comment at `compile.py:349-359`.

A third finding in the same pass was the same pattern on a different axis: `_EXCLUDED_DIR_NAMES` matched the bare name `"data"` anywhere in the tree, silently dropping legitimate CHANGELOGs/memlogs/retros under any directory named `data`; fixed to match only the adjacent pair `(".claude", "data")` (`compile.py:215-232`).

**Why this is a class, not two bugs:** both violated the *same documented guarantee* ("a single degraded surface does not abort the rest of the compile") that both self-reviews had asserted was upheld. The structural lesson the retro draws — same-session self-review is blind to "did I catch everything the docstring promises"; unattended pipelines need an independent adversarial pass before done — is Scribe's most exportable engineering finding, and it directly amplifies RISK-1: `promote.py` never received *either* review tier. Note also that `promote.py` has its own uncaught-exception exposure of exactly this shape: `_classify_one()` does `path.read_text()` with no `OSError` handling, so a file vanishing mid-scan (the identical TOCTOU that crashed `_apply_supersession`) would crash `classify_and_draft()` — unverified against tests, flagged here as a candidate first finding for the RISK-1 review.

---

## Opportunities (ranked)

1. **Pay RISK-1 now** — adversarial diff-only review of `promote.py` + `test_promote.py`; seed it with the two concrete candidates above (unhandled `OSError` in `_classify_one`; single-missing-path stale veto). Cheap, bounded, highest expected yield per the build's own base rate.
2. **Wire the nightly** — a real scheduled `scribe graph compile --nightly` invocation with warnings routed somewhere a human sees (RISK-2). Until then, "nightly-compiled knowledge graph" is a capability, not a behavior.
3. **`git fsck --no-reflogs` in the bmad-loop deferral path** (retro action item, `[open]`) — the 1.3 recovery happened only because a *blocked* session had a reason to look; the check should not depend on luck. This is a bmad-loop change, not a Scribe change, but Scribe's incident is its evidence.
4. **Soften the pointer stub's destructiveness** — FR-5 mandates the original body not persist in user-local memory, but nothing prevents the stub from carrying a content hash of what was destroyed, giving post-hoc verification that the promoted rewrite matches the source (currently only the human confirm step attests to this, and RISK-1 means the rewrite code itself is unreviewed).
5. **Recall quality has obvious headroom behind a stable seam** — v1 token-overlap returns exactly one node's raw text; the `GraphStore` port means a better ranker (BM25, multi-node synthesis with multi-citation) is a `recall.py`-only change. Keep the PRD's discipline: no LoCoMo/LongMemEval parity claims; groundedness + citation is the differentiator.
6. **Cross-station surfaces already half-exist** — the retro surface (`**/*retro*.md`) means every station's retros are *already* graph nodes; the natural next step is other stations querying Scribe (`scribe recall` from Doctor's health checks or a Warden finding's "has this been decided before?") rather than only feeding it. See the 2026-08-08 market refresh § Cross-station integration for the full analysis.

---

## Sources

- `_bmad-output/projects/pyforge-scribe/planning-artifacts/retros/retro-scribe-2026-08-08.md` (the dangling-commit incident, the recurring bug class, action items — read in full)
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/{capture,promote,compile,graph_store,recall,models,cli}.py` (shipped source, read in full; line references current at `d68187f4b3`-descended HEAD)
- Git evidence: `91d3571f10` (dangling snapshot), `70673665d7` (recovery cherry-pick), `d68187f4b3` (PR #168 merge), `a53b5c581e` (Epic 2 review-findings fix), `ccecbf5f1c` (Story 1.5 seed promotion — the 1-of-2 outcome), PRs #296/#301 (epic merges)
- `_bmad-output/projects/pyforge-scribe/planning-artifacts/epics.md` (FR inventory, ACs), `.claude/memory/README.md` (shipped schema doc), `docs/dreams/pyforge-scribe.md`
- Live state: `.claude/memory/feedback/bmad-runs-cfe-retro.md`, `~/.claude/projects/-home-rxm7706-UserLocal-Projects-Github-rxm7706-local-recipes/memory/feedback_bmad_runs_cfe_retro.md` (pointer stub, `promoted_date: 2026-08-07`), `pixi.toml` (env wiring; loop-approve-startup operator decision)
