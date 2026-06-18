``# Tech Spec: graphifyy installable on osx-arm64 (15-feedstock fanout)

> Fanout effort: open **15 net-new platform-expansion PRs** across the
> tree-sitter language-binding feedstocks so that `graphifyy` (which is
> `noarch: python`) resolves and installs on osx-arm64. Each PR matches
> `sumanth-manchala`'s 2026-06-07 pattern in
> `conda-forge/tree-sitter-javascript-feedstock#1`: a `conda-forge.yml`
> `provider:` addition + rerender, scoped to `osx-arm64` + `linux-aarch64`.
> Each PR is gated behind a maintainer-add issue (the killua156/mgorny
> recipe-maintainer pair owns all 22 affected feedstocks).
>
> **BMAD intake document.** Written for `bmad-quick-dev` (Quick Flow
> track, fanout variant). ~3 stories per feedstock × 15 feedstocks +
> 3 orchestration stories = ~48 stories grouped in 5 waves. Run BMAD with
> this file as the intent document; the per-feedstock work is delegated
> to [`docs/specs/feedstock-platform-expansion.md`](feedstock-platform-expansion.md)
> with `target_platforms=osx_arm64,linux_aarch64` and the feedstock name
> taken from the per-row table in Wave B below.
>
> **Per CLAUDE.md Rule 1**, any BMAD agent executing this spec MUST
> invoke the `conda-forge-expert` skill before touching recipe code or
> running recipe tooling. Per Rule 2, the effort closes with a single
> consolidated CFE-skill retrospective and a `CHANGELOG.md` entry
> covering all 15 PRs (fanout retros consolidate; they do not produce
> 15 separate entries).

---

## Status


| Field        | Value                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Status       | **🎉 CLOSED 2026-06-17 03:25Z**. 22 platform-expansion PRs + 8 canonical-conda-forge.yml sweep + tree-sitter-swift dist-info fix + graphifyy v0.8.40 PR #8 (merged `fa094fa`) all shipped in a single ~16h session. Wave D smoke-test PASS: dry-run solve of graphifyy on osx-arm64 returned a complete plan (62 pkgs / 71 MB, all 22 tree-sitter-* deps at osx-arm64 builds). Closeout retro shipped as CFE v8.26.0 (G23 + G24 + DEP-002 sub-rule). S-F4 follow-ups: 3 draft PRs OPEN on staged-recipes (2026-06-17) — [#33752 falkordb](https://github.com/conda-forge/staged-recipes/pull/33752) (win_64 ❌), [#33753 ctranslate2-suite](https://github.com/conda-forge/staged-recipes/pull/33753), [#33754 faster-whisper](https://github.com/conda-forge/staged-recipes/pull/33754) (gated on #33753). |
| Owner        | rxm7706                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| Track        | BMAD Quick Flow (fanout — 15 single-feedstock cycles + orchestration)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| Surface area | 15 conda-forge tree-sitter-* feedstocks; 15 maintainer-add issues + 15 platform-expansion PRs; watch policy on 7 in-flight PRs by`sumanth-manchala`; **no** code changes to `.claude/skills/conda-forge-expert/` (skill-internal work limited to closeout retro per Rule 2)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| Scope        | (1) Open a`@conda-forge-admin, please add user @rxm7706` issue on each of 22 affected feedstocks (15 Cat-3 + 7 Cat-2; see audit table). (2) Per Cat-3 feedstock, sync local mirror → edit `conda-forge.yml` → rerender → open DRAFT PR adding `osx_arm64` + `linux_aarch64` provider blocks. (3) Watch the 7 Cat-2 PRs by `sumanth-manchala`; after 14 days idle, open a competing PR with the same scope. (4) After all 22 PRs merge, verify `mamba install graphifyy` resolves on osx-arm64 via repodata grep. (5) One consolidated CFE-skill retro at closeout.                                                                                                                                                                                                                                        |
| Out of scope | Adding`win-arm64`. **Scope update 2026-06-16**: touching `conda-forge/graphifyy-feedstock` was originally out-of-scope ("already noarch and needs no change — the fix is in its deps") but is now in scope per Wave F § S-F1–S-F4 — driven by mid-session v0.8.10 → v0.8.40 upstream advance + 19 optional-extras enablement. Version bumps on any of the 15 feedstocks. Recipe-code changes beyond a `conda-forge.yml` block + rerender artifacts. Auto-merging any PR. **Scope update 2026-06-16**: `linux-ppc64le` was originally ruled out but has been brought back in scope after Cat-2 validated the hybrid native (linux_aarch64 + osx_arm64) + cross-compile (linux_ppc64le: linux_64) pattern. Cat-3 PRs now target osx-arm64 + linux-aarch64 + linux-ppc64le.                                |
| Created      | 2026-06-15                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| Driven by    | `graphifyy` not installable on osx-arm64. Confirmed empirically 2026-06-15: of 26 tree-sitter-* run-deps + 3 transitive Python deps, only 4 tree-sitter-* + all 3 Python deps ship osx-arm64; 7 are in-flight via `sumanth-manchala`, 15 have no PR yet.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| Predecessor  | `docs/specs/feedstock-platform-expansion.md` (the per-feedstock workflow this spec invokes 15×); `conda-forge/tree-sitter-javascript-feedstock#1` (the canonical PR diff to copy)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |

---

## Background and Context

### The problem

`graphifyy` is `noarch: python` and consumes 26 `tree-sitter-*` language
bindings + 3 transitive Python deps (`networkx`, `datasketch`,
`rapidfuzz`) at runtime. Conda's solver refuses to install a package on
a subdir where any run-dep is missing — so the gap is not in
`graphifyy` itself but in its dep coverage. Confirmed empirically
2026-06-15 against `conda.anaconda.org/conda-forge/osx-arm64/repodata.json`:

```
osx-arm64 coverage of graphifyy 0.8.10 deps:
  ✅ 7 ship: networkx, datasketch, rapidfuzz, tree-sitter (core),
                  tree-sitter-python, tree-sitter-c-sharp, tree-sitter-bash
  🟡 7 in-flight (sumanth-manchala 2026-06-07 PRs): javascript, go, groovy,
                  c, cpp, elixir, fortran
  ❌ 15 missing, no PR yet: typescript, rust, java, ruby, kotlin, scala,
                  php, swift, lua, zig, powershell, objc, julia, verilog, json
  ✅ 1 shipped this session (tree-sitter-markdown — v0.5.3 + platform
                  expansion merged 2026-06-16 22:12Z, SHA `1d7b45b`)
```

**Addendum 2026-06-16**: tree-sitter-markdown was added to Cat-3 as
the 16th feedstock and shipped same-day via PR #5 (v0.5.3 patch +
platform expansion combined) — counted as DONE in the totals above.
Backstory: Wave B would have been the natural home for it, but the
upstream v0.5.3 was a working bot-update blocker (broken setup.py
expected flat `src/parser.c` against the dual-grammar subdirectory
tarball layout — see CFE SKILL.md G5 sibling case). The closeout was:
(1) close stale autotick PR #1; (2) open PR #4 with
`bot.version_updates.exclude: [0.5.2, 0.5.3]` as a safety belt;
(3) author setup.py patch + open PR #5 (v0.5.3 + patch);
(4) operator extended PR #5 with the platform-expansion conda-forge.yml
(canonical hybrid pattern) before merging; (5) close PR #4 as
redundant. So tree-sitter-markdown is functionally done — no Wave B
work needed.

Every one of the 15 missing-without-PR feedstocks shares the same
recipe shape (verified by spot-check):
`schema_version: 1` + `compiler("c") + stdlib("c")` + `python-abi3` host

+ `version_independent: ${{ is_abi3 }}` + `abi3audit` test. Their
  `conda-forge.yml` is bare. The platform-expansion diff is the cookie-cutter
  `provider:` block from
  `conda-forge/tree-sitter-javascript-feedstock#1` — no per-recipe
  customization needed.

All 22 affected feedstocks (Cat-2 + Cat-3) have **identical** recipe
maintainers: `killua156, mgorny`. Because the user has elected a
maintainer-add-before-recipe-PR gate (matching the pattern of
`conda-forge/tree-sitter-javascript-feedstock#2`, opened by `rxm7706`
2026-06-15 with title `@conda-forge-admin, please add user @rxm7706`),
every recipe PR is preceded by an issue opening that request.

### What's been ruled out

- ~~**Adding `linux-ppc64le`.**~~ **RESOLVED 2026-06-16 — ppc64le is
  back in scope** after Cat-2 PRs validated the hybrid pattern
  (`provider: linux_aarch64+osx_arm64: default` + `build_platform: linux_ppc64le: linux_64` cross-compile). The original concern was
  transitive C-dep coverage on conda-forge in mid-2026; the actual
  conda-forge.yml pattern uses x86_64 toolchain to cross-compile for
  ppc64le, so transitive coverage on ppc64le itself isn't needed.
  Cat-2 PRs (including the 6 we uplifted) all shipped ppc64le builds
  green. Cat-3 PRs use the same shape.
- **Touching the `graphifyy-feedstock` recipe itself.** It's already
  `noarch: python` at v0.8.10. The fix is entirely in its deps. No
  change to `recipes/graphify/` or to `conda-forge/graphifyy-feedstock`
  in this effort.
- **A maintainer-add request to the conda-forge core team rather than
  the per-feedstock owners.** Per conda-forge convention, the
  `@conda-forge-admin, please add user @X` issue is the canonical
  mechanism — the existing maintainer(s) approve or reject inline; the
  bot performs the team-add on approval. We follow that pattern.
- **Opening 22 simultaneous PRs as a sympathy/co-pressure tactic on the
  existing 2-maintainer pair.** The fanout proceeds in batches of 5 to
  give `killua156`/`mgorny` reasonable review bandwidth and a chance to
  push back before the full batch ships.
- **Squashing the 15 PRs into a single conda-forge org-level PR.** No
  such mechanism exists — conda-forge feedstocks are independent
  repositories. Each platform expansion is a per-feedstock PR.

### What's available to leverage

- **`conda-forge/tree-sitter-javascript-feedstock#1`** — sumanth's
  canonical diff. Copy `conda-forge.yml` provider-block edits verbatim.
- **`docs/specs/feedstock-platform-expansion.md`** — the parameterized
  per-feedstock workflow. This spec invokes it 15× with
  `target_platforms=osx_arm64,linux_aarch64` and
  `recipe_shape=compiled`. Per-feedstock procedural detail (S1–S13)
  lives there; this spec adds only the orchestration.
- **The empirical 2026-06-15 audit** — pre-computed per-category
  classification in § Empirical state below. No need to re-audit at
  intake.
- **The maintainer-add issue template** — title `@conda-forge-admin, please add user @rxm7706`, body `### Additional comment:` with no
  response (per the `tree-sitter-javascript-feedstock#2` template).
  Single `gh issue create` per feedstock.

### Empirical state (verified 2026-06-15)

graphifyy-feedstock: v0.8.10, noarch:python, maintainers killua156+mgorny
graphifyy run-deps:    29 total (26 tree-sitter-* + networkx + datasketch + rapidfuzz)
graphifyy osx-arm64:   blocked — 22 of 29 deps not yet on osx-arm64

Per-dep status (sorted by category):

[Cat 1 — already ships osx-arm64, NO ACTION (7)]
networkx                noarch:python
datasketch              noarch:python
rapidfuzz               native osx-arm64 build present
tree-sitter (core lib)  osx-arm64 build present
tree-sitter-python      osx-arm64 build present
tree-sitter-c-sharp     osx-arm64 build present
tree-sitter-bash        osx-arm64 build present

[Cat 2 — IN-FLIGHT PR by sumanth-manchala (2026-06-07), watch only (7)]
tree-sitter-javascript   PR #1 — adds osx-arm64 + linux-aarch64 + ppc64le
tree-sitter-go           PR #1 — same scope
tree-sitter-groovy       PR #2 — same scope
tree-sitter-c            PR #1 — same scope
tree-sitter-cpp          PR #1 — same scope
tree-sitter-elixir       PR #1 — same scope
tree-sitter-fortran      PR #2 — same scope

[Cat 3 — NO PR YET, our work (15)]
Each is the same abi3 Python C-extension shape. Each gets a
maintainer-add issue first, then a platform-expansion PR scoped to
osx-arm64 + linux-aarch64 + ppc64le

tree-sitter-typescript    maintainers: killua156, mgorny
tree-sitter-rust          maintainers: killua156, mgorny
tree-sitter-java          maintainers: killua156, mgorny
tree-sitter-ruby          maintainers: killua156, mgorny
tree-sitter-kotlin        maintainers: killua156, mgorny
tree-sitter-scala         maintainers: killua156, mgorny
tree-sitter-php           maintainers: killua156, mgorny
tree-sitter-swift         maintainers: killua156, mgorny
tree-sitter-lua           maintainers: killua156, mgorny
tree-sitter-zig           maintainers: killua156, mgorny
tree-sitter-powershell    maintainers: killua156, mgorny
tree-sitter-objc          maintainers: killua156, mgorny
tree-sitter-julia         maintainers: killua156, mgorny
tree-sitter-verilog       maintainers: killua156, mgorny
tree-sitter-java          maintainers: killua156, mgorny
tree-sitter-markdown      maintainers: killua156, mgorny

→ Total work: **15 maintainer-add issues + 15 platform-expansion PRs**
on Cat-3 feedstocks; plus **7 maintainer-add issues** on Cat-2
feedstocks (so we're in a position to take over if sumanth's PR
stalls); plus **watch policy** on the 7 Cat-2 PRs with a 14-day idle
takeover trigger.

---

## Goals

1. **`mamba install graphifyy` succeeds on osx-arm64.** First-class
   acceptance — verified by Wave D smoke-test after all 22 PRs merge.
2. **15 net-new conda-forge PRs opened** adding `osx_arm64` +
   `linux_aarch64` to each Cat-3 feedstock. One PR per feedstock; no
   bundling across feedstocks (impossible — they're separate
   repositories).
3. **22 maintainer-add issues opened** (15 Cat-3 + 7 Cat-2). The Cat-2
   issues exist so the 14-day takeover policy can execute without an
   extra issue round-trip if needed.
4. **No structural recipe change** on any of the 15 Cat-3 feedstocks
   beyond `conda-forge.yml` provider blocks + standard rerender
   artifacts. Any feedstock requiring deeper changes triggers
   Stop-the-Line per the per-feedstock guide.
5. **Scope match with `sumanth-manchala`'s in-flight PRs**:
   osx-arm64 + linux-aarch64 + linux-ppc64le. Updated 2026-06-16 —
   ppc64le added to scope after Cat-2 validated the hybrid pattern
   (native aarch64+osx_arm64 + cross-compile ppc64le via
   `build_platform: linux_ppc64le: linux_64`).
6. **14-day takeover policy** on Cat-2 PRs (now moot — all 7 Cat-2
   PRs merged 2026-06-16 within ~2 hours of the native+cross uplift,
   no takeovers triggered). Original text retained for record: "if a
   sumanth PR has had no commits, no maintainer comments, and no CI
   runs for 14 calendar days, we open a competing PR with our scope.
   The competing PR credits sumanth in the body and is opened as DRAFT."
7. **One consolidated CFE-skill retro** at closeout — fanout retros
   consolidate findings; they do not produce 15 separate CHANGELOG
   entries.

---

## Five load-bearing workflow rules (apply to every story)

These five rules govern the whole fanout. The first inherits from
`feedstock-platform-expansion.md`; rules 2–5 are fanout-specific.

- **Bump `build.number` on every feedstock-PR-update at the same
  upstream version.** When a feedstock PR changes recipe shape OR
  `conda-forge.yml` shape OR rerender output on the same upstream
  version (no version bump), `recipe/recipe.yaml`'s `build.number`
  MUST increment to supersede main's currently-shipping artifacts. A
  rebase onto main resets the number to main's value (typically 0 for
  the first release); the post-rebase commit must re-bump. Forgetting
  this means the conda solver keeps preferring main's `*_0` artifacts
  over our `*_0` rebuild — solver tie-break is timestamp-on-channel,
  not local merge order, so reviewers won't catch it during PR review
  but users will install the stale build. Applies to every Cat-2 PR
  rebase + every Cat-3 PR opened in Wave B + any subsequent edit-cycle
  after the initial build.number bump (each subsequent edit cycle
  bumps again, e.g. 1 → 2 → 3 as we iterate on review feedback).
- **Every push to a feedstock PR branch is followed immediately by
  `@conda-forge-admin, please rerender`.** No judgment calls about
  "this change doesn't need a rerender" — `build.number` bumps,
  whitespace fixes, README edits, anything pushed to a feedstock PR
  gets the rerender comment. The rerender bot is idempotent and
  fast; running it unconditionally is correct. The cost of always
  commenting is zero; the cost of skipping leaves the next
  operator/reviewer wondering why some pushes get rerenders and
  others don't, and gives the auto-rerender service a chance to fire
  on its own variable timing instead of the explicit-request fast
  path. See `feedback_always_request_rerender_after_feedstock_push.md`.
- **Local mirror is the source of truth, and the mirror must be
  COMPLETE.** Per `feedstock-platform-expansion.md` § "Two load-bearing
  workflow rules": for every Cat-3 feedstock, `recipes/<feedstock>/`
  mirrors the full feedstock state (recipe.yaml + conda-forge.yml +
  LICENSE + patches + build.sh/.bat). Edit in the mirror first;
  verify-build local; mirror to fork; push; request rerender. Not
  optional.
- **Maintainer-add issue gates every recipe PR on that feedstock.**
  Per the user-set policy: because every Cat-3 feedstock's maintainers
  include `killua156` or `mgorny`, we open the `@conda-forge-admin, please add user @rxm7706` issue FIRST. The recipe PR opens only after
  one of: (a) the bot has team-added `rxm7706` (typical resolution
  time: same day), OR (b) 48 hours have passed with no objection on
  the issue (per conda-forge convention — silence implies consent for
  maintainer-adds on inactive feedstocks). The recipe PR body cites
  the maintainer-add issue number.
- **14-day takeover policy for in-flight PRs.** Cat-2 PRs are watched,
  not duplicated. We open a competing PR only when ALL THREE conditions
  hold for that PR: (1) no new commits to the head branch in 14
  calendar days, (2) no maintainer comments in 14 calendar days, (3)
  CI is not currently running. The competing PR is opened DRAFT,
  scoped to osx-arm64 + linux-aarch64 only, credits sumanth in the
  body, and references the original PR number. We do NOT close
  sumanth's PR — that's the maintainer's call.

---

## Stories — Wave A: Maintainer-add issues (22 feedstocks, fast)

Goal: open the maintainer-add issue on every Cat-2 + Cat-3 feedstock
in a single batch. These are cheap (`gh issue create` per feedstock)
and front-load the bot's team-add latency so it doesn't gate Wave B.

### S-A1. Open 15 maintainer-add issues on Cat-3 feedstocks

For each Cat-3 feedstock:

```
gh issue create \
  --repo conda-forge/<feedstock>-feedstock \
  --title "@conda-forge-admin, please add user @rxm7706" \
  --body $'### Additional comment:\n\n_No response_'
```

The title is exactly the conda-forge-admin command; no body content
required (the bot ignores it). Match the template at
`https://github.com/conda-forge/tree-sitter-javascript-feedstock/issues/2`
verbatim.

**Acceptance**: 15 issues created, one per Cat-3 feedstock. Each
returns a URL; record the issue numbers in the per-feedstock tracking
table at the bottom of this spec (Wave E populates it).

### S-A2. Open 7 maintainer-add issues on Cat-2 feedstocks

Same template, same call, but on the 7 Cat-2 feedstocks. Rationale:
even if we never need to take over sumanth's PR, having maintainer
access lets us merge cleanly when the bot processes the
team-add. If we DO need to take over, no extra issue round-trip is
needed.

**Acceptance**: 7 additional issues created. Total of 22 open
maintainer-add issues across both categories.

### S-A3. Operator-confirm checkpoint before Wave B begins

**HALT** — present to operator:

- 22 issue URLs (one block of 15 Cat-3, one block of 7 Cat-2)
- Any issue where the maintainer pair has already commented (positive
  or negative) within the first hour
- The list of feedstocks where the bot has already team-added
  `rxm7706` (visible via `gh api orgs/conda-forge/teams/<feedstock>/members`)

Operator confirms before Wave B begins. Per CLAUDE.md "Executing
actions with care", opening 15 PRs against a 2-maintainer pair is
visibly batched activity — operator gates the cadence.

**Acceptance**: explicit operator approval to begin Wave B (or
redirect — e.g., "wait 48h for the bot to process the team-adds
before opening any PR").

---

## Stories — Wave B: Cat-3 platform-expansion PRs (15 PRs, 3 batches of 5)

Goal: open the 15 platform-expansion PRs in 3 batches of 5, with an
operator checkpoint between batches. Per-feedstock procedural detail
is delegated to `docs/specs/feedstock-platform-expansion.md`
S1–S12; this spec sets only the parameters and the cadence.

### S-B1. Configure per-feedstock invocation parameters

Each of the 15 Cat-3 feedstocks gets a `feedstock-platform-expansion.md`
invocation with these constants:


| Parameter                 | Value                                                                                                 |
| ------------------------- | ----------------------------------------------------------------------------------------------------- |
| `target_platforms`        | `osx_arm64`, `linux_aarch64`, `linux_ppc64le`                                                         |
| `recipe_shape`            | `compiled` (15 of 16 are abi3 Python C-extensions; markdown TBD)                                      |
| `fork_owner`              | `rxm7706`                                                                                             |
| `branch_name`             | `add-osx-arm64-linux-aarch64-ppc64le`                                                                 |
| `local_test_subdir`       | `linux-64` (operator host)                                                                            |
| Maintainer-add issue gate | YES — cite the S-A1 issue number in the PR body                                                      |
| ppc64le?                  | YES — cross-compile via`build_platform: linux_ppc64le: linux_64` (hybrid pattern validated on Cat-2) |
| conda-forge.yml pattern   | Full canonical block — see § "Canonical conda-forge.yml for Wave B Cat-3 PRs" below                 |
| PR state on open          | DRAFT                                                                                                 |

### Canonical conda-forge.yml for Wave B Cat-3 PRs

Use this exact shape on every Wave B platform-expansion PR. Updated
2026-06-16 — supersedes the simpler "just provider+build_platform+test"
template used on the Cat-2 PRs and the earlier tree-sitter-markdown PR
drafts. Includes the canonical `bot:` block for grayskull-driven
autotick + solvability checks + wheel-derived run-deps, plus the
modern `conda_install_tool: pixi`.

```yaml
conda_install_tool: pixi
conda_build_tool: rattler-build
github:
  branch_name: main
  tooling_branch_name: main
conda_build:
  error_overlinking: true
conda_forge_output_validation: true
provider:
  linux_aarch64: default
  osx_arm64: default
build_platform:
  linux_ppc64le: linux_64
test: native_and_emulated
bot:
  automerge: true
  inspection: update-grayskull
  check_solvable: true
  run_deps_from_wheel: true
```

**Why each key:**

- `conda_install_tool: pixi` — canonical 2026 companion to rattler-build (faster than micromamba; matches conda-forge's standardization).
- `bot.automerge: true` — version-bump PRs that pass CI green merge automatically.
- `bot.inspection: update-grayskull` — autotick re-runs grayskull against the new upstream to refresh recipe shape, not just version+sha256. Catches upstream dep/metadata changes.
- `bot.check_solvable: true` — dep-solvability check before opening; broken PRs never reach the queue.
- `bot.run_deps_from_wheel: true` — extract run-deps from upstream's wheel metadata (more accurate than pyproject.toml for some packages).

**Pre-existing `bot:` keys**: if a feedstock's main already has a `bot:` block (e.g., `bot.version_updates.exclude` for skipped broken upstream versions), MERGE the new keys with the existing ones — don't overwrite.

Per-feedstock substitutions for `feedstock` and `upstream_version` are
populated from a `gh api` sweep at batch start (versions change between
audit and execution; do not hardcode).

**Acceptance**: a per-feedstock parameter table is materialized as
section "Per-feedstock invocation table" at the bottom of this spec.

### S-B2. Batch 1 — open PRs on 5 Cat-3 feedstocks

Recommended batch (alphabetical, no per-feedstock dependency):

```
tree-sitter-java
tree-sitter-json
tree-sitter-julia
tree-sitter-kotlin
tree-sitter-lua
```

For each: invoke `feedstock-platform-expansion.md` S1–S11 per the
per-feedstock parameter table from S-B1. All 5 PRs open as DRAFT.

**Acceptance**: 5 draft PR URLs returned. Each PR body cites the
matching S-A1 maintainer-add issue. Each PR's `conda-forge.yml` delta
is the 2-line provider block (`osx_arm64: default` +
`linux_aarch64: default`) plus rerender artifacts. No recipe-code
edits.

### S-B3. Operator-confirm checkpoint between Batch 1 and Batch 2

**HALT** — present to operator:

- 5 PR URLs
- CI status on each (`gh pr checks <PR>`)
- Any maintainer comments on the 5 PRs OR the matching S-A1 issues
- The diff size of each PR's `.ci_support/` regeneration

Operator confirms before Batch 2 ships. If `killua156` or `mgorny` has
pushed back on any of the 5 PRs (or any of the open S-A1 issues),
operator decides whether to pause the remaining 10 PRs and re-engage
the maintainers.

**Acceptance**: explicit operator approval to ship Batch 2 (or
redirect).

### S-B4. Batch 2 — open PRs on 5 more Cat-3 feedstocks

Recommended batch:

```
tree-sitter-objc
tree-sitter-php
tree-sitter-powershell
tree-sitter-ruby
tree-sitter-rust
```

Same procedure as S-B2.

**Acceptance**: 5 more draft PR URLs, same shape as Batch 1.

### S-B5. Operator-confirm checkpoint between Batch 2 and Batch 3

Same shape as S-B3. **HALT** — present 10-PR aggregate status,
confirm.

**Acceptance**: explicit operator approval to ship Batch 3.

### S-B6. Batch 3 — open PRs on the final 5 Cat-3 feedstocks

```
tree-sitter-scala
tree-sitter-swift
tree-sitter-typescript
tree-sitter-verilog
tree-sitter-zig
```

Same procedure.

**Acceptance**: 5 more draft PR URLs. Total: 15 Cat-3 draft PRs open.

### S-B7. Per-PR draft → ready-for-review transitions

For each of the 16 PRs, when CI is green on all 6 legs
(linux-64 + osx-64 + win-64 existing + osx-arm64 + linux-aarch64 native +
linux-ppc64le cross-compiled new), operator flips draft → ready via
`gh pr ready <PR>`. Per `feedstock-platform-expansion.md` S12, this is
per-PR and per-operator-gate.

**Acceptance**: each PR transitions DRAFT → READY → MERGED. Track
state per-feedstock in the Worked Example table.

---

## Stories — Wave C: Watch + native-runner uplift on Cat-2 PRs

Goal: track sumanth's 7 in-flight PRs; **proactively uplift the 6 still-emulation PRs to the native-runner pattern** that sumanth already applied to PR #1 on tree-sitter-javascript; take over only on 14-day idle.

### Scope expansion 2026-06-16 — native-runner uplift on Cat-2 PRs

**CORRECTION 2026-06-16 11:38Z** (per mgorny review on
`conda-forge/tree-sitter-javascript-feedstock#1`):
**`linux_ppc64le` is NOT natively supported on conda-forge.** Only
`linux_aarch64` and `osx_arm64` are first-class native runners. The
correct pattern for ppc64le is cross-compile via `build_platform: linux_ppc64le: linux_64` (emulated test run via QEMU on the
linux-anvil-x86_64:alma9 docker image, with `test: native_and_emulated`
exercising the actual ppc64le binary under emulation). An earlier
draft of this spec treated ppc64le as native — it is not.

**Canonical hybrid pattern** (matches latest javascript PR #1 head after
mgorny review):

```yaml
# conda-forge.yml
provider:
  linux_aarch64: default      # native aarch64 runner (linux-anvil-aarch64:alma9)
  osx_arm64: default          # native arm64 runner (macOS-15-arm64)
build_platform:
  linux_ppc64le: linux_64     # cross-compile from x86_64 (no native ppc64le runner)
test: native_and_emulated     # ppc64le test exercises the binary under QEMU emulation
```

```yaml
# recipe.yaml — simplified requirements.build (no cross-python conditional)
requirements:
  build:
    - ${{ compiler("c") }}
    - ${{ stdlib("c") }}
```

Sumanth dropped the `if: build_platform != target_platform / then: python

+ cross-python_${{ target_platform }}`conditional block from`requirements.build `(see his commit`f4efd05 `"Remove cross python deps"). The cross-compile still works because conda-smithy rerender injects the cross-python toolchain at the`.ci_support/*.yaml `level; the recipe doesn't need to declare it. Removing the block keeps the recipe simpler and matches the abi3 + version_independent pattern's intent — the abi3 stub`python-abi3` in host carries the ABI marker
  without needing a full target-platform Python in build.

Empirical baseline (verified 2026-06-16):


| Cat-2 PR                                                      | linux_aarch64                    | linux_ppc64le                                  | osx_arm64                        | Status                           |
| ------------------------------------------------------------- | -------------------------------- | ---------------------------------------------- | -------------------------------- | -------------------------------- |
| **tree-sitter-javascript #1** (canonical, post-mgorny-review) | **NATIVE** (`provider: default`) | **CROSS-COMPILE** (`build_platform: linux_64`) | **NATIVE** (`provider: default`) | Latest pattern                   |
| tree-sitter-go #1 (our 2026-06-16 push — pre-correction)     | NATIVE                           | (incorrectly) NATIVE                           | NATIVE                           | Needs ppc64le→cross-compile fix |
| tree-sitter-groovy #2                                         | emulation under linux_64         | emulation under linux_64                       | NATIVE                           | Needs aarch64 uplift             |
| tree-sitter-c #1                                              | emulation under linux_64         | emulation under linux_64                       | NATIVE                           | Needs aarch64 uplift             |
| tree-sitter-cpp #1                                            | emulation under linux_64         | emulation under linux_64                       | NATIVE                           | Needs aarch64 uplift             |
| tree-sitter-elixir #1                                         | emulation under linux_64         | emulation under linux_64                       | NATIVE                           | Needs aarch64 uplift             |
| tree-sitter-fortran #2                                        | emulation under linux_64         | emulation under linux_64                       | NATIVE                           | Needs aarch64 uplift             |

The aarch64 portion of the uplift gives true platform fidelity testing

+ faster CI (no QEMU). The ppc64le portion stays at cross-compile —
  the win there is faster CI (linux-anvil-x86_64 is faster than the
  cross-compile-onto-x86_64-then-emulate-test cycle currently used; the
  build_platform: linux_64 pattern skips the cross-compile-prep overhead
  because it just uses the x86_64 toolchain directly with target_platform
  set in the variant).

Because rxm7706 was team-added 2026-06-16, we now have direct push access to all 7 Cat-2 feedstocks. All 7 Cat-2 PRs have `maintainerCanModify: true`, so we can also push commits directly to sumanth's PR branches.

**Approach**: edit `conda-forge.yml` per Cat-2 PR to the hybrid
native+cross pattern (above), simplify `requirements.build` to drop the
cross-python conditional, then rerender via `@conda-forge-admin, please rerender`. Match the tree-sitter-javascript post-mgorny-review pattern
exactly.

### S-C0. Test the uplift on tree-sitter-go first

Before fanning out the uplift to the other 5, validate end-to-end on tree-sitter-go #1:

1. **Mirror sumanth's branch into `recipes/tree-sitter-go/`** (full feedstock state — `recipe/`, `conda-forge.yml`, etc.). Per `feedback_local_mirror_first_then_verify_then_push.md`.
2. **Edit `recipes/tree-sitter-go/conda-forge.yml`** to the hybrid pattern (above): `provider: linux_aarch64+osx_arm64: default`, `build_platform: linux_ppc64le: linux_64`, `test: native_and_emulated`.
3. **Edit `recipes/tree-sitter-go/recipe.yaml`** to drop the `if: build_platform != target_platform / then: python + cross-python_${{ target_platform }}` block from `requirements.build` (match javascript's simplified shape).
4. **Push to `sumanth-manchala:osx-arm64`** (the PR's head branch) — we have `maintainerCanModify: true`.
5. **Comment on PR #1**: `@conda-forge-admin, please rerender`. Per saved feedback, the comment is terse — no preamble or credit prose. Credit lives in commit trailers.
6. **Watch CI**: linux_aarch64 (native) + linux_ppc64le (cross-compiled) + osx_arm64 (native) + linux_64 + osx_64 + win_64 must all go green. If any leg fails, debug per `feedstock-platform-expansion.md` and the CFE Build Failure Protocol.
7. **Operator-confirm HALT** before fanning out to the remaining 5 Cat-2 PRs.

**Acceptance**: tree-sitter-go #1 ships the hybrid native+cross pattern; rerender lands clean; all 6 CI legs go green. Operator confirms the pattern works before applying to the rest.

**Historical note 2026-06-16**: an earlier iteration of this story
pushed `provider: linux_ppc64le: default` to tree-sitter-go #1 and CI
went green on all 6 legs (build artifact `tree-sitter-go-0.25.0-py310h541078d_1.conda`
68.40 KiB on linux-ppc64le). Mgorny's review on tree-sitter-javascript
clarified that ppc64le-native is not actually a thing on conda-forge —
the "native" anvil-ppc64le docker image still runs on x86_64 hardware
with QEMU emulation underneath. The `build_platform: linux_ppc64le: linux_64` pattern is faster because it skips the cross-compile-prep
overhead and just uses the x86_64 toolchain with `target_platform: linux-ppc64le` set in the variant. The fix to tree-sitter-go after the
mgorny review applies S-C0 as written.

### S-C0b. Fan out the uplift to the remaining 5 Cat-2 PRs

Once S-C0 confirms the pattern, apply the same edit to: tree-sitter-groovy, tree-sitter-c, tree-sitter-cpp, tree-sitter-elixir, tree-sitter-fortran. One commit per PR, same shape. Rerender each via `@conda-forge-admin, please rerender`.

**Acceptance**: all 6 remaining Cat-2 PRs carry the native-runner pattern; all 6 PRs' CI goes green on linux_aarch64 + linux_ppc64le + osx_arm64.

### S-C1. Materialize the Cat-2 watch table

For each of the 7 Cat-2 PRs:

```
gh pr view <PR> --repo conda-forge/<feedstock>-feedstock \
  --json number,state,updatedAt,statusCheckRollup,headRefOid
```

Capture the per-PR head SHA, last update timestamp, CI status.
Materialize as section "Cat-2 watch table" at the bottom of this spec.

**Acceptance**: 7-row watch table populated with first observation.

### S-C2. Refresh the watch table every 7 days

A `bmad-quick-dev` or cron-style runner (operator decision per § Open
Questions Q4) re-runs S-C1 every 7 days. The refresh is read-only.

**Acceptance**: watch table carries a timestamped row per refresh.

### S-C3. Trigger takeover when 14-day idle conditions hold

For each Cat-2 PR, takeover triggers when ALL THREE conditions hold:

- No new commit to the head branch in 14 calendar days
  (`headRefOid` unchanged across two consecutive 7-day refreshes).
- No maintainer comment in 14 calendar days
  (`gh pr view <PR> --json comments --jq '.comments[] | select(.author.login == "killua156" or .author.login == "mgorny") | .createdAt'` returns nothing within window).
- CI is not currently running
  (`statusCheckRollup` status is `COMPLETED` or empty, not `IN_PROGRESS`).

If ALL three hold, open a competing DRAFT PR with the same
`feedstock-platform-expansion.md` invocation as Wave B, scoped to
osx-arm64 + linux-aarch64 only. The competing PR body **must** include:

> Friendly heads-up to @sumanth-manchala — taking over to unblock the
> `graphifyy` fanout. The original PR #<N> remains open; this PR is a
> drop-in alternative scoped to osx-arm64 + linux-aarch64 only (no
> ppc64le, deferred to a follow-up). Happy to close in favor of #<N>
> if you'd like to rebase.

If any of the three conditions fails, take no action and continue
watching.

**Acceptance**: per-Cat-2-feedstock, one of: (a) sumanth's PR merged
upstream — no takeover; (b) takeover triggered — competing DRAFT PR
opened with the credit-and-handoff body.

### S-C4. Per-Cat-2 closeout

When each Cat-2 feedstock reaches a merged state (sumanth's PR
merged OR our takeover merged), record the outcome and the merge SHA
in the per-feedstock tracking table.

**Acceptance**: 7 Cat-2 feedstocks all reach a merged state. The
spec does not close until this happens.

---

## Stories — Wave D: Verify graphifyy resolves on osx-arm64

Goal: empirically confirm the whole effort actually delivered the
acceptance goal (Goal 1).

### S-D1. Wait for all 22 PRs to merge AND propagate to repodata

After the last of the 22 PRs merges, conda-forge CDN propagation
typically takes 1–6 hours. Wait until `mamba search 'tree-sitter-*' -c conda-forge --subdir osx-arm64` returns a build of every Cat-3 +
Cat-2 feedstock at the version that the merged PR shipped.

**Acceptance**: each of the 22 tree-sitter-* feedstock names returns
at least one osx-arm64 build via `mamba search`.

### S-D2. Smoke-test `mamba install graphifyy` on osx-arm64

Run the install dry-run via the osx-arm64 subdir override:

```
mamba install -n test-graphifyy -c conda-forge \
  --platform osx-arm64 \
  --dry-run \
  graphifyy
```

(The `--platform osx-arm64 --dry-run` pair lets the solver run from
any host without actually fetching osx-arm64 binaries.) Solver should
return a complete plan — no unresolved deps.

**Acceptance**: solver returns a complete plan including graphifyy and
all 26 tree-sitter-* deps + 3 transitive Python deps, all at osx-arm64
builds.

### S-D3. (Optional, host-permitting) Native install on an osx-arm64 host

If the operator has access to an osx-arm64 host:

```
mamba create -n test-graphifyy -c conda-forge graphifyy
mamba run -n test-graphifyy graphify --help
```

Confirms the actual install + entry-point invocation.

**Acceptance**: `graphify --help` returns successfully. (Skip with
"host unavailable" note if no osx-arm64 host is on hand.)

---

## Stories — Wave F: graphifyy-feedstock v0.8.40 + extras enablement (scope expansion 2026-06-16)

Original spec was scoped to making the **22 tree-sitter-\* dep feedstocks** ship osx-arm64, treating `conda-forge/graphifyy-feedstock` itself as **out of scope**. Scope expanded mid-session 2026-06-16 because:

1. Upstream PyPI advanced from v0.8.10 → v0.8.40 (30 versions; autotick bot's intermediate PRs #1/#2/#3/#5 stalled with stale shapes — all closed in favor of a direct bump).
2. Run-dep list changed materially: `datasketch` dropped (v0.8.37), `numpy>=1.21` added (v0.8.40), all tree-sitter-\* run-deps now version-pinned upstream.
3. The conda-forge.yml was bare (no `conda_install_tool: pixi`, no extended `bot:` block); modernization brings it in line with the 22 platform-expansion PRs shipped earlier in this session.
4. Upstream declares 19 `[project.optional-dependencies]` extras (mcp, neo4j, falkordb, pdf, watch, svg, leiden, office, google, postgres, video, kimi, ollama, bedrock, anthropic, gemini, openai, chinese, sql); main recipe pinned none of them.

### S-F1. Update graphifyy-feedstock to v0.8.40

Open a single PR against `conda-forge/graphifyy-feedstock` that bundles:

- **Version bump** v0.8.10 → v0.8.40 with new sha256.
- **Run-deps refresh** to match upstream `pyproject.toml [project.dependencies]`: + `numpy >=1.21`; − `datasketch`; all `tree-sitter-*` carry their lower bounds.
- **Drop upper bounds** on run-deps. `bot.run_deps_from_wheel: true` (added in S-F2) extracts lower bounds correctly on each version bump; upper bounds were redundant with `pip_check: true` + the `script: graphify --help` runtime test for catching ABI breaks.
- **Fix `tree_sitter` core dep name** to underscore-preserved form (per CFE SKILL.md G10 / `feedback_pypi_conda_mapping_unreliable.md`). conda-forge ships the core as `tree_sitter-X.Y.Z` (109 builds on linux-64), reserving the hyphen prefix `tree-sitter-LANG` for language bindings (456 builds, all our 22 platform-expansion feedstocks).
- **Restore the `script: graphify --help` test** the local mirror carried (catches CLI entry-point breakage at test time — load-bearing now that we dropped upper bounds).
- **Order maintainers alphabetically** (`killua156, mgorny, rxm7706`).
- **Add yaml-language-server schema header** per local-recipes convention.

**Acceptance**: PR opens as DRAFT; `validate` + `check-deps` (29/29 resolve) + `lint-optimize` (0 suggestions) all clean locally. Body cites the maintainer-add issue (already merged 2026-06-16) and the 22 platform-expansion PRs shipped earlier in the session.

### S-F2. Modernize conda-forge.yml to the 2026 canonical shape

In the same PR as S-F1:

```yaml
conda_install_tool: pixi
conda_build_tool: rattler-build
github:
  branch_name: main
  tooling_branch_name: main
conda_build:
  error_overlinking: true
conda_forge_output_validation: true
bot:
  automerge: true
  inspection: update-grayskull
  check_solvable: true
  run_deps_from_wheel: true
```

**Intentionally omits** the `provider:` / `build_platform:` / `test: native_and_emulated` block we shipped on the 22 tree-sitter-* platform-expansion PRs — graphifyy is `noarch: python`, so a single linux-64 build serves all subdirs automatically.

**Why each new key:**

- `conda_install_tool: pixi` — canonical 2026 companion to rattler-build.
- `bot.inspection: update-grayskull` — autotick bumps re-run grayskull against the new upstream, catching dep / metadata changes that a bare version bump misses (would have caught the `datasketch` removal at v0.8.37 if enabled earlier).
- `bot.check_solvable: true` — autotick PRs run dep-solvability check before opening; broken PRs never reach the queue.
- `bot.run_deps_from_wheel: true` — extract run-deps from upstream's wheel metadata (more accurate than parsing pyproject.toml).

**Acceptance**: conda-forge.yml byte-matches the canonical block; existing `bot.automerge: true` preserved (merged with the new keys, not overwritten).

### S-F3. Add `run_constrained` block for all available extras

Upstream defines 19 `[project.optional-dependencies]` groups. **17 of the 19 groups' deps are already on conda-forge across all 6 platforms we ship (incl. the 3 new subdirs)**. Add them to `requirements.run_constrained:` so users can opt in with explicit installs (`mamba install graphifyy mcp openai tiktoken`) and conda guarantees compatibility.

Verified extras availability (2026-06-16):


| Extra                           | Upstream deps                                     | conda-forge status                    |
| ------------------------------- | ------------------------------------------------- | ------------------------------------- |
| sql                             | tree-sitter-sql                                   | ✅ (0.3.11)                           |
| mcp                             | mcp                                               | ✅ (1.27.2)                           |
| neo4j                           | neo4j (PyPI) → neo4j-python-driver (conda-forge) | ✅ (6.2.0)                            |
| pdf                             | pypdf, markdownify                                | ✅                                    |
| watch                           | watchdog                                          | ✅                                    |
| svg                             | matplotlib, numpy>=2.0 (py>=3.13)                 | ✅                                    |
| leiden                          | graspologic (py<3.13)                             | ✅                                    |
| office                          | python-docx, openpyxl                             | ✅                                    |
| google                          | openpyxl                                          | ✅                                    |
| postgres                        | psycopg[binary] → psycopg                        | ✅                                    |
| video (yt-dlp only)             | yt-dlp                                            | ✅                                    |
| kimi / ollama / gemini / openai | openai, tiktoken                                  | ✅                                    |
| bedrock                         | boto3                                             | ✅                                    |
| anthropic                       | anthropic                                         | ✅                                    |
| chinese                         | jieba                                             | ✅                                    |
| **falkordb**                    | **falkordb**                                      | **❌ NOT ON CONDA-FORGE — see S-F4** |
| **video (faster-whisper part)** | **faster-whisper** (py>=3.11)                     | **❌ NOT ON CONDA-FORGE — see S-F4** |

**Acceptance**: PR commit `e2a999a` ships the 17-entry `run_constrained` block; check-deps passes; `mamba install graphifyy openai tiktoken mcp` on any subdir resolves cleanly post-merge.

### S-F4. Package the 2 missing extras (new conda-forge feedstocks)

Two extras blocked on conda-forge availability, drafted locally 2026-06-16:

- **`falkordb` v1.6.1** (`falkordb` extra) — Python client for the FalkorDB graph database. Pure-Python, Redis-protocol-based. **Drafted at `recipes/falkordb/recipe.yaml`** — validates clean (3/3 deps resolve: python-dateutil, redis-py; MIT license). **Ready for staged-recipes submission.**
- **`faster-whisper` v1.2.1** (`video` extra, py>=3.11) — Reimplementation of OpenAI Whisper using CTranslate2. **Drafted at `recipes/faster-whisper/recipe.yaml`** but **BLOCKED on a deeper transitive dep**: `ctranslate2` (C++ library by OpenNMT) is NOT on conda-forge. The other 5 faster-whisper run-deps (`huggingface_hub`, `tokenizers`, `onnxruntime`, `av`, `tqdm`) are all on conda-forge. Switched source from wheel-only PyPI to GitHub tag tarball to get the LICENSE + full source tree.

**Dependency chain**: graphifyy[video] → faster-whisper → ctranslate2 (C++ library, multi-platform native build, optional CUDA support, substantial recipe complexity)

**Recommended path forward**:

1. **`recipes/falkordb/` submitted to staged-recipes 2026-06-17 00:11:50Z as DRAFT [conda-forge/staged-recipes#33752](https://github.com/conda-forge/staged-recipes/pull/33752)** ("Create recipe.yaml for FalkorDB", head `falkordb`). Status: linter ✅ · linux_64 ✅ · osx_64 ✅ · win_64 ❌ — win_64 failure pending diagnosis.
2. **`recipes/ctranslate2/` submitted to staged-recipes 2026-06-17 00:34:29Z as DRAFT [conda-forge/staged-recipes#33753](https://github.com/conda-forge/staged-recipes/pull/33753)** ("Ctranslate2 suite", head `ctranslate2-suite`, sha `4cbc0189`).
3. **`recipes/faster-whisper/` submitted to staged-recipes 2026-06-17 00:44:14Z as DRAFT [conda-forge/staged-recipes#33754](https://github.com/conda-forge/staged-recipes/pull/33754)** ("Faster whisper", head `faster-whisper`, sha `9e13e5ac`). Sequencing note: gated on #33753 landing first (deps `ctranslate2` is not yet on conda-forge); kept as draft until then.
4. **`ctranslate2` packaging detail**: multi-output (`libctranslate2` + `ctranslate2`), 224 lines, adapted from `AnacondaRecipes/ctranslate2-feedstock@main` (Anaconda main channel recipe v4.7.1 by `xkong-anaconda`) with these deltas for conda-forge:

   - Main source bumped v4.7.1 → v4.8.0 (latest PyPI).
   - Converted v0 meta.yaml → v1 recipe.yaml.
   - Dropped MKL variant (Intel MKL is proprietary; conda-forge prefers OpenBLAS/Accelerate by default).
   - Dropped CUDA variants (cuda-12, cuda-13); ships as a separate `ctranslate2-cuda` recipe via conda-forge's CUDA-matrix variant pattern in a follow-up.
   - Dropped all 4 of Anaconda's patches (mkl-shared-libs, mkl-dll-libs-win, use-system-thrust, cuda13-compat) — none apply to the CPU-only OpenBLAS/Accelerate build.
   - Uses the same 3-submodule parallel-source pattern (`spdlog` 1.14.1 + `cxxopts` 3.1.1 + `cpu_features` 0.9.0) at their Anaconda-vetted SHAs.

   **Build-verified locally on linux-64 (2026-06-16)**: `libctranslate2-4.8.0-hbfe361e_0.conda` (1.2 MiB) + `ctranslate2-4.8.0-np2py310h81cc0b8_0.conda` (544 KiB) produced clean; `import ctranslate2; ctranslate2.__version__ == '4.8.0'` works; `from ctranslate2.converters import opennmt_py` succeeds. One non-blocking issue caught and fixed during verification: needed `openblas` (not `libopenblas`) in `host:` requirements — `libopenblas` is the runtime-only conda-forge package; `openblas` is the one that ships the headers + CMake config needed for `find_package(OpenBLAS)` to succeed. The Anaconda-adapted recipe + 3 submodule sources work as designed. **Pre-submission TODOs remaining** (4 items):

   - Verify submodule versions still satisfy v4.8.0's CMake checks (Anaconda's were against v4.7.1) — implicitly verified by the successful linux-64 build, but spot-check on other platforms once CI runs.
   - CUDA variants follow up as a separate `ctranslate2-cuda` recipe.
   - Spot-check `ENABLE_CPU_DISPATCH=ON` on `linux-ppc64le` (VSX) / `linux-aarch64` (NEON) once CI runs (Anaconda's recipe didn't target ARM).
   - Consider bumping spdlog → 1.15.x and cxxopts → 3.2.x once verified compatible.
5. After #33753 merges, mark #33754 ready-for-review (currently draft).
6. Final follow-up PR on graphifyy-feedstock: add `ctranslate2`, `faster-whisper`, `falkordb` to `run_constraints:` and update S-F3's omission note.

**Backend choices in the ctranslate2 draft** (CPU-only):

- Linux + Windows: WITH_OPENBLAS=ON + WITH_RUY=ON; WITH_MKL=OFF (Intel MKL is proprietary, doesn't ship as default on conda-forge).
- macOS: WITH_ACCELERATE=ON + WITH_RUY=ON (Apple's framework + ARM-friendly Ruy).
- All platforms: CUDA / cuDNN / Flash Attention / TensorParallel deferred to a future `ctranslate2-cuda` variant.

**Acceptance**: all three drafts submitted as staged-recipes DRAFT PRs (2026-06-17): #33752 (falkordb, CI partial green — win_64 ❌ outstanding), #33753 (ctranslate2-suite), #33754 (faster-whisper, sequencing on #33753).

### S-F5. tree-sitter-swift dist-info version-metadata fix (2026-06-16)

Caught during graphifyy PR #8's first CI run: `pip check` rejected the build because the installed `tree-sitter-swift` wheel ships `dist-info` declaring `version = "0.0.1"` while graphifyy 0.8.40's `pyproject.toml` pins `tree-sitter-swift<0.9,>=0.7`. The conda solver picks our 0.7.3 conda label, but pip then reads the wheel's metadata and sees `0.0.1 < 0.7` — fail.

**Survey result**: of 22 `tree-sitter-*` packages on conda-forge, only `tree-sitter-swift` has a major dist-info mismatch (0.7.3 vs 0.0.1). `tree-sitter-powershell` has a minor 0.26.5/0.26.4 nit (harmless — within graphifyy's `>=0.26,<0.28` range).

**Root cause**: upstream `alex-pinkus/tree-sitter-swift` has never bumped its `pyproject.toml [project].version` field from the placeholder `"0.0.1"` despite tagging releases up through v0.7.3. PyPI's `tree-sitter-swift` is stuck at v0.0.1 for the same reason.

**Downstream fix** (`conda-forge/tree-sitter-swift-feedstock#5`, opened 2026-06-16 by rxm7706):

1. Bump `tag` context-var template to `${{ version }}-with-generated-files` (was hardcoded `0.7.2-with-generated-files`; autotick-friendly now).
2. Replace static `patches/0001-...patch` (hardcoded destination `0.7.3`) with a `build.script` that rewrites `pyproject.toml`'s `version = ".*"` line in-place using `${{ version }}`. Works for any future version bump without recipe edits.
3. Bump `build.number` 1 → 2 to supersede currently-shipping `*_1` artifacts (same upstream-version recipe-shape change rule).

**Follow-up TODOs** (post Wave F closeout):

- **File upstream issue** at `alex-pinkus/tree-sitter-swift` requesting they bump `pyproject.toml [project].version` to track tag releases. Once they do, our `build.script` rewrite becomes a no-op (sed/python find-replace does nothing if source already matches). The fix is forward-compatible and self-healing.
- Confirm `tree-sitter-powershell`'s 0.26.5/0.26.4 minor mismatch doesn't surface elsewhere (it doesn't break graphifyy, but might break tighter downstream pins).
- Verify the `${{ version }}-with-generated-files` tag pattern works for autotick by spot-checking the bot's next bump attempt on this feedstock.
- **Simplify the Windows path**: the current fix uses a checked-in `recipe/fix_pyproject_version.py` helper because inline `sed` (Unix) + `powershell` (Windows) hit cmd.exe escaping issues — cmd ate the `^` from `[^\"]` outside the powershell-quoted string and mangled the regex (Azure buildId 1539671). A separate helper file is more code than a single inline command should require. **Preferred replacement: add `sed` to `requirements.build` (conda-forge ships GNU sed cross-platform via `m2-sed` on Windows) and use one `sed -i 's/^version = .*/version = "${{ version }}"/' pyproject.toml` line that works on every platform.** Open follow-up PR to swap the helper for the one-liner once this lands. The root cause + canonical pattern is being captured as CFE SKILL.md G23 so it doesn't get re-learned the hard way on the next recipe.

**Acceptance**: PR #5 merges + propagates → graphifyy PR #8's `pip check` passes on next CI run → no further intervention on graphifyy needed.

**Status update 2026-06-17 01:36Z**: PR #5 MERGED at `2cfc104`. Build artifacts (`tree-sitter-swift-0.7.3-*_2.conda`) propagating to conda-forge repodata (typical 30-60 min lag). Once visible on linux-64 + the other 5 subdirs, re-run graphifyy PR #8's CI to confirm `pip check` passes.

**Status update 2026-06-17 (post-propagation)**: ✅ tree-sitter-swift `*_2` build verified shipping `tree_sitter_swift-0.7.3.dist-info` (was `0.0.1`). Triggered graphifyy PR #8 rerender + CI re-run. **PR #8 CI flipped FAILURE → SUCCESS** on the same head (`3227888`) via Azure rebuild 27662710337. `mergeable: MERGEABLE`. **S-F5 acceptance criterion fully met** — no further intervention on graphifyy needed.

**🎉 PR #8 MERGED at 2026-06-17 03:00:06Z (merge SHA `fa094fa`)**. graphifyy v0.8.40 + 2026-canonical conda-forge.yml + 17-entry `run_constrained` block shipped to conda-forge. Combined with the 22 platform-expansion PRs + 8-feedstock canonical-sweep + tree-sitter-swift dist-info fix merged earlier this session, **Wave F closes the entire graphifyy osx-arm64 fanout effort end-to-end**.

### S-F6. Canonical `conda-forge.yml` retrofit sweep (2026-06-17)

Discovered while monitoring S-F5: of the 23 `tree-sitter-*` feedstocks shipped in Wave C + Wave B + tree-sitter-markdown out-of-band, **8 do not match the 2026-canonical `conda-forge.yml` block** that Wave B Batch 1+2+3 adopted. The gap is two missing keys (`conda_install_tool: pixi` + the entire `bot:` block); the rest of the block already matches.


| Subset              | Count | Feedstocks                                                                                                                       |
| ------------------- | ----- | -------------------------------------------------------------------------------------------------------------------------------- |
| ✅ Match canonical  | 15    | typescript, rust, java, ruby, kotlin, scala, php, swift, lua, zig, powershell, objc, julia, verilog, json (all Wave B Cat-3 PRs) |
| ❌ Differ           | 8     | javascript, go, groovy, c, cpp, elixir, fortran (Cat-2), markdown (Cat-3 out-of-band)                                            |
| ➖ Not a maintainer | 4     | tree-sitter (core), python, c-sharp, bash (Cat-1)                                                                                |

**Why the gap**: the 7 Cat-2 PRs shipped during Wave C (uplift of sumanth-manchala's PRs) before the richer 2026-canonical conda-forge.yml was adopted. tree-sitter-markdown was the user's out-of-band v0.5.3 + platform-expansion PR which only added platform-expansion keys, not the `bot:` block. The 15 Cat-3 PRs in Wave B Batches 1-3 shipped after the canonical was adopted and are already aligned.

**Sweep PRs opened 2026-06-17** (all DRAFT, build.number bumped on each):


| Feedstock              | PR | New build.number |
| ---------------------- | -- | ---------------- |
| tree-sitter-javascript | #4 | 1 → 2           |
| tree-sitter-go         | #4 | 1 → 2           |
| tree-sitter-groovy     | #5 | 2 → 3           |
| tree-sitter-c          | #4 | 1 → 2           |
| tree-sitter-cpp        | #4 | 1 → 2           |
| tree-sitter-elixir     | #4 | 1 → 2           |
| tree-sitter-fortran    | #5 | 2 → 3           |
| tree-sitter-markdown   | #6 | 0 → 1           |

Each PR is `+1 commit`, touching only `conda-forge.yml` (adds 5 lines) + `recipe.yaml` (1-line build.number bump). No platform-expansion or recipe-code change. Rerender requested on each.

**Acceptance**: all 8 PRs land green; subsequent autotick PRs on these feedstocks run with `inspection: update-grayskull` (more accurate dep refresh) + `check_solvable: true` (broken PRs filtered at submission) + `run_deps_from_wheel: true` (better dep-list source); install paths use pixi by default.

**Status update 2026-06-17 01:55-01:56Z**: ALL 8 PRs MERGED within ~85 seconds:


| Feedstock              | PR | Merge SHA             |
| ---------------------- | -- | --------------------- |
| tree-sitter-elixir     | #4 | `98e676f` (01:55:19Z) |
| tree-sitter-javascript | #4 | `e1fb790` (01:55:23Z) |
| tree-sitter-go         | #4 | `f9b8380` (01:55:30Z) |
| tree-sitter-groovy     | #5 | `84df721` (01:55:40Z) |
| tree-sitter-c          | #4 | `519eca5` (01:55:50Z) |
| tree-sitter-fortran    | #5 | `ae7bcba` (01:56:01Z) |
| tree-sitter-cpp        | #4 | `0cc295e` (01:56:18Z) |
| tree-sitter-markdown   | #6 | `517d8cd` (01:56:40Z) |

Post-merge canonical-match verification: **all 23 maintainer-owned `tree-sitter-*` feedstocks** (15 Wave B + 7 Cat-2 + tree-sitter-markdown) now match the 2026 canonical `conda-forge.yml` byte-for-byte. Cat-1 feedstocks (tree-sitter core, python, c-sharp, bash) are not in scope (rxm7706 isn't on those teams).

---

### S-E1. Single consolidated retro across all 22 PRs

Invoke `bmad-retrospective` (or follow its protocol manually). Survey:

- Per-feedstock build outcomes (any feedstock CI red on osx-arm64 or
  linux-aarch64? Why?)
- Maintainer-add timing (did the bot process all 22 promptly, or did
  the 48h silence-implies-consent fallback fire?)
- 14-day takeover policy outcomes (how many Cat-2 PRs needed
  takeover? Was the threshold right?)
- Per-feedstock `conda-forge.yml` diffs — did any feedstock diverge
  from the cookie-cutter pattern?
- Any reviewer pushback on ppc64le-omission (Goal 5 / Q1) — did it
  trigger?

**Retro executed 2026-06-17 (post-PR #8 merge)** — landed as CFE skill v8.26.0 (MINOR bump). Findings:


| Bucket                         | Finding                                                                                                                                                                                                                                                                                                                                                                              | Skill landing                                              |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------- |
| Addition                       | **G23** — Inline `sed`/`powershell` in `build.script` hits cmd.exe escape hell. Canonical fix: `sed` with `m2-sed` on Win                                                                                                                                                                                                                                                           | SKILL.md new gotcha section                                |
| Addition                       | **G24** — Conda label ≠ wheel `dist-info` version when upstream's `pyproject.toml` hardcodes a placeholder. Detection helper + canonical fix via G23 pattern                                                                                                                                                                                                                       | SKILL.md new gotcha section                                |
| Refinement                     | Sub-workflow "Special-case categorizations" gains a 4th bullet making upstream-declared upper bounds'`pip_check`-enforcement mechanism explicit (the existing DEP-002 note was easy to skip past — empirically confirmed)                                                                                                                                                           | SKILL.md sub-workflow categorizations table                |
| Audit outcome (no skill delta) | Maintainer-add bot: processed all 22 same-day (no 48h fallback). Takeover policy never fired — all 7 Cat-2 PRs merged via rxm7706 follow-up commits (`maintainerCanModify: true`). ppc64le reviewer pushback DID trigger (mgorny clarified ppc64le is cross-compile, not native), corrected spec mid-session. conda-forge.yml drift discovered post-merge → spawned § S-F6 sweep. | None — process worked                                     |
| Audit outcome (skill memory)   | "Drop upper bounds" without checking`pip_check` impact almost merged broken graphifyy. Empirical confirmation that the existing DEP-002 sub-rule about upstream-declared bounds is load-bearing.                                                                                                                                                                                     | Already captured in feedback memory + now in new sub-rule. |

**Counter-factual estimate**: had G23+G24+the upper-bounds sub-rule been in the skill at intake, graphifyy PR #8 would have shipped with the right shape on commit 1 (skipping iterations 1+2 — drop-upper-bounds revert + pip_check debugging). Iteration 3 (tree-sitter-swift dist-info fix) was unavoidable but would have surfaced at PR-author time, not CI-debug time. Per-future-analogous-fanout savings: ~1-2 PR-iteration cycles + ~30-60 min CI-burn.

**No cross-skill auto-memory deltas** — all findings are CFE-internal. Existing feedback memory entries (`feedback_canonical_conda_forge_yml_for_platform_expansion.md`, `feedback_bump_build_number_on_feedstock_pr_update.md`, `feedback_always_request_rerender_after_feedstock_push.md`) all validated as load-bearing during the session.

### S-E2. Land the retro deltas

Write a single `CHANGELOG.md` entry covering all 22 PRs (not 22
separate entries). Land any skill-guide refinements per Rule 2
(corrections / refinements / additions).

**Acceptance**: new dated `CHANGELOG.md` entry in
`.claude/skills/conda-forge-expert/CHANGELOG.md`. If no novel
findings: explicit "verified existing guidance held across 22-PR
fanout" entry.

---

## Open Questions (resolved 2026-06-15)

### Q1. Scope divergence from sumanth's PRs — ship osx-arm64 + linux-aarch64 only, or match his three (incl. ppc64le)?

**Original resolution (2026-06-15)**: ship osx-arm64 + linux-aarch64 only.
**Updated 2026-06-16**: match all three (osx-arm64 + linux-aarch64 + linux-ppc64le).

Rationale for the update: mgorny's review on `tree-sitter-javascript#1`
clarified that ppc64le is not native on conda-forge anyway — the
canonical pattern is hybrid `provider: linux_aarch64+osx_arm64: default`

+ `build_platform: linux_ppc64le: linux_64`, where the ppc64le build
  cross-compiles on the x86_64 toolchain and tests run emulated via
  QEMU (`test: native_and_emulated`). This sidesteps the original
  transitive-C-dep concern entirely: the build doesn't touch the ppc64le
  package graph at compile time, only at runtime-emulated-test time. All
  7 Cat-2 PRs shipped ppc64le builds green using this pattern. Cat-3 PRs
  use the same shape.

Reviewer-divergence risk: a `killua156`/`mgorny` reviewer comparing
our PRs to sumanth's may ask "why no ppc64le?". The PR body addresses
this preemptively:

> Scope deliberately narrower than #<sumanth-PR-on-this-feedstock> on
> a sibling feedstock — osx-arm64 + linux-aarch64 only. ppc64le
> deferred per `feedstock-platform-expansion.md` transitive-coverage
> caveat; happy to add in a follow-up PR once sumanth's PRs land
> green on ppc64le.

### Q2. Maintainer-add gate — issue first then PR, or both simultaneously?

**Resolution**: issue first, then PR. Either (a) wait for bot
confirmation of team-add, or (b) wait 48h with no objection on the
issue.

Rationale: the user explicitly set this policy. Mechanically simpler
to track per-feedstock; reduces reviewer load by giving maintainers a
chance to weigh in before any recipe surface area is changed.

### Q3. 14-day takeover threshold — too short, too long, or right?

**Resolution**: 14 days. Operator chose this in the intake.

Rationale: sumanth's PRs were opened 2026-06-07. As of 2026-06-15 they
are 8 days old. A 14-day threshold (so first eligible takeover at
2026-06-21) gives `killua156`/`mgorny` reasonable bandwidth without
indefinitely blocking graphifyy. The threshold is per-PR last-activity,
not per-PR open-date — so a PR that received a CI rerun yesterday
resets the clock.

### Q4. Watch-table refresh mechanism — `bmad-quick-dev` invocation or scheduled job?

**Resolution**: defer to operator at S-C1 intake. Recommended: weekly
manual invocation triggered by the operator (low effort — read-only),
not a scheduled job (the schedule infrastructure for this repo is
geared toward atlas-data refresh, not GitHub-state polling).

### Q5. Batch cadence in Wave B — 3 batches of 5 with operator gates, or one batch of 15?

**Resolution**: 3 batches of 5 with operator gates per S-B3 / S-B5.

Rationale: 22 issues + 15 PRs against a 2-maintainer pair is a visible
volume of activity. Batching gives operator visibility into maintainer
response patterns AND gives the maintainers a chance to push back
before the full batch ships. If maintainers respond enthusiastically
to Batch 1, operator may decide to ship Batches 2+3 in quick
succession.

---

## Risks and Mitigations


| Risk                                                                                                                                                                                   | Likelihood  | Impact                                                              | Mitigation                                                                                                                                                                                                                                                          |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------- | ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `killua156` or `mgorny` rejects the maintainer-add request as inappropriate (e.g. "we maintain these as a coherent set")                                                               | Low–Medium | Wave B can't proceed via the standard maintainer route              | Operator-decision branch: (a) open PRs anyway and ask reviewers to merge on our behalf via`@conda-forge-admin, please merge` once green, or (b) close the fanout and accept that graphifyy on osx-arm64 waits for sumanth's PRs + a separate ppc64le-blocked subset |
| ~~Reviewer pushback on scope divergence (no ppc64le) per Q1~~ Resolved 2026-06-16 — Cat-3 PRs now include ppc64le via hybrid cross-compile pattern, matching Cat-2 + sumanth's scope. | n/a         | n/a                                                                 | n/a                                                                                                                                                                                                                                                                 |
| A Cat-3 feedstock's`recipe.yaml` diverges from the cookie-cutter abi3 shape (recipe-shape audit was a spot-check, not exhaustive)                                                      | Low         | Per-feedstock Stop-the-Line, scope expands to recipe-authoring      | Per-feedstock S-B2/B4/B6 invokes`feedstock-platform-expansion.md` S3 (validate + check-deps), which catches this BEFORE the PR opens. Stop-the-Line per the per-feedstock guide                                                                                     |
| Sumanth's PR merges with ppc64le green on a Cat-2 feedstock between Wave A and Wave B — making the divergence point moot                                                              | Medium      | Slight reviewer-message inconsistency on our Cat-3 PRs              | Acceptable. Update the PR-body boilerplate to drop the "happy to add in a follow-up" clause if all 7 Cat-2 PRs have already merged ppc64le-green                                                                                                                    |
| Sumanth's 7 PRs all stall and need takeover — fanout balloons to 22 net-new PRs from us                                                                                               | Low         | Higher reviewer load on`killua156`/`mgorny`; longer effort timeline | 14-day threshold is the natural backstop; spec already plans for it. Worst case: 22 PRs total in 5 batches across 3+ weeks                                                                                                                                          |
| graphifyy's run-dep list changes between intake and merge (upstream version bump introduces new tree-sitter-*)                                                                         | Low–Medium | Wave D smoke-test fails even with 22 PRs merged                     | Re-run the § Empirical state audit at Wave D start; if a new dep appeared, add it to the fanout. Spec does not close until graphifyy is empirically installable on osx-arm64                                                                                       |
| Operator capacity — 5 operator gates (S-A3, S-B3, S-B5, plus per-PR draft→ready × 15)                                                                                               | High        | Operator-load-driven schedule slip                                  | Group draft→ready transitions by batch (5 at a time) instead of per-PR. Operator gates are mandatory; cadence is flexible                                                                                                                                          |

---

## Acceptance criteria (whole effort)

1. **`mamba install graphifyy --platform osx-arm64 --dry-run`** returns
   a complete plan including all 26 tree-sitter-* deps + 3 transitive
   Python deps, all at osx-arm64 builds. (Wave D, S-D2.)
2. **22 maintainer-add issues opened** (15 Cat-3 + 7 Cat-2) on
   `conda-forge/tree-sitter-*-feedstock` repos.
3. **15 platform-expansion PRs opened** on Cat-3 feedstocks, scoped to
   osx-arm64 + linux-aarch64.
4. **7 Cat-2 feedstocks reach a merged state** (sumanth's PR merged
   OR our takeover merged after 14-day idle).
5. **All 22 PRs land** their osx-arm64 builds in
   `conda-forge/osx-arm64/repodata.json` within ~6 hours of merge.
6. **One consolidated CHANGELOG entry** in
   `.claude/skills/conda-forge-expert/CHANGELOG.md` for the whole
   fanout (not 22 separate entries).
7. **Per-feedstock tracking table** at the bottom of this spec
   populated end-to-end (maintainer-add issue #, PR #, merge SHA, first
   osx-arm64 build on repodata).

---

## Reference

- Per-feedstock workflow: [`docs/specs/feedstock-platform-expansion.md`](feedstock-platform-expansion.md)
- Workflow guide (procedural detail): [`.claude/skills/conda-forge-expert/guides/feedstock-platform-expansion.md`](../../.claude/skills/conda-forge-expert/guides/feedstock-platform-expansion.md)
- Canonical PR diff to copy: `https://github.com/conda-forge/tree-sitter-javascript-feedstock/pull/1`
- Maintainer-add issue template: `https://github.com/conda-forge/tree-sitter-javascript-feedstock/issues/2`
- CFE `SKILL.md` § Critical Constraints, § Build Failure Protocol
- CFE `reference/conda-forge-yml-reference.md` — `provider:`, `workflow_settings.store_build_artifacts:`
- CLAUDE.md § "BMAD ↔ conda-forge-expert integration" — Rule 1 + Rule 2

---

# Per-feedstock tracking table

Populated as the fanout executes. One row per affected feedstock.

## Cat 3 — 15 net-new PRs (our work)


| Feedstock              | Maintainer-add issue                                                                        | Recipe PR                                                                                                                                           | CI green?                         | Merged SHA                           | First osx-arm64 build on repodata? |
| ---------------------- | ------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------- | ------------------------------------ | ---------------------------------- |
| tree-sitter-typescript | [#1](https://github.com/conda-forge/tree-sitter-typescript-feedstock/issues/1) (2026-06-16) | [#3](https://github.com/conda-forge/tree-sitter-typescript-feedstock/pull/3) (Wave B Batch 3)                                                       | (CI green at merge)               | `45da046` (merged 2026-06-16 23:22Z) | _<Wave D>_                         |
| tree-sitter-rust       | [#1](https://github.com/conda-forge/tree-sitter-rust-feedstock/issues/1) (2026-06-16)       | [#3](https://github.com/conda-forge/tree-sitter-rust-feedstock/pull/3) (Wave B Batch 2)                                                             | (CI green at merge)               | `bb70dd1` (merged 2026-06-16 23:05Z) | _<Wave D>_                         |
| tree-sitter-java       | [#2](https://github.com/conda-forge/tree-sitter-java-feedstock/issues/2) (2026-06-16)       | [#4](https://github.com/conda-forge/tree-sitter-java-feedstock/pull/4) (Wave B Batch 1)                                                             | (CI green at merge)               | `6b693f6` (merged 2026-06-16 22:42Z) | _<Wave D>_                         |
| tree-sitter-ruby       | [#1](https://github.com/conda-forge/tree-sitter-ruby-feedstock/issues/1) (2026-06-16)       | [#3](https://github.com/conda-forge/tree-sitter-ruby-feedstock/pull/3) (Wave B Batch 2)                                                             | (CI green at merge)               | `832a455` (merged 2026-06-16 23:01Z) | _<Wave D>_                         |
| tree-sitter-kotlin     | [#1](https://github.com/conda-forge/tree-sitter-kotlin-feedstock/issues/1) (2026-06-16)     | [#3](https://github.com/conda-forge/tree-sitter-kotlin-feedstock/pull/3) (Wave B Batch 1)                                                           | (CI green at merge)               | `923956e` (merged 2026-06-16 22:42Z) | _<Wave D>_                         |
| tree-sitter-scala      | [#1](https://github.com/conda-forge/tree-sitter-scala-feedstock/issues/1) (2026-06-16)      | [#3](https://github.com/conda-forge/tree-sitter-scala-feedstock/pull/3) (Wave B Batch 3)                                                            | (CI green at merge)               | `64e3924` (merged 2026-06-16 23:17Z) | _<Wave D>_                         |
| tree-sitter-php        | [#2](https://github.com/conda-forge/tree-sitter-php-feedstock/issues/2) (2026-06-16)        | [#4](https://github.com/conda-forge/tree-sitter-php-feedstock/pull/4) (Wave B Batch 2; PR #1 license-patch already merged 13:42Z)                   | (CI green at merge)               | `1cb1106` (merged 2026-06-16 22:59Z) | _<Wave D>_                         |
| tree-sitter-swift      | [#2](https://github.com/conda-forge/tree-sitter-swift-feedstock/issues/2) (2026-06-16)      | [#4](https://github.com/conda-forge/tree-sitter-swift-feedstock/pull/4) (Wave B Batch 3)                                                            | (CI green at merge)               | `73e78f3` (merged 2026-06-16 23:18Z) | _<Wave D>_                         |
| tree-sitter-lua        | [#1](https://github.com/conda-forge/tree-sitter-lua-feedstock/issues/1) (2026-06-16)        | [#3](https://github.com/conda-forge/tree-sitter-lua-feedstock/pull/3) (Wave B Batch 1)                                                              | (CI green at merge)               | `1c09c91` (merged 2026-06-16 22:42Z) | _<Wave D>_                         |
| tree-sitter-zig        | [#1](https://github.com/conda-forge/tree-sitter-zig-feedstock/issues/1) (2026-06-16)        | [#3](https://github.com/conda-forge/tree-sitter-zig-feedstock/pull/3) (Wave B Batch 3)                                                              | (CI green at merge)               | `a15d42d` (merged 2026-06-16 23:23Z) | _<Wave D>_                         |
| tree-sitter-powershell | [#3](https://github.com/conda-forge/tree-sitter-powershell-feedstock/issues/3) (2026-06-16) | [#5](https://github.com/conda-forge/tree-sitter-powershell-feedstock/pull/5) (Wave B Batch 2)                                                       | (CI green at merge)               | `79c4471` (merged 2026-06-16 23:02Z) | _<Wave D>_                         |
| tree-sitter-objc       | [#1](https://github.com/conda-forge/tree-sitter-objc-feedstock/issues/1) (2026-06-16)       | [#3](https://github.com/conda-forge/tree-sitter-objc-feedstock/pull/3) (Wave B Batch 2)                                                             | (CI green at merge)               | `2fd9e36` (merged 2026-06-16 22:57Z) | _<Wave D>_                         |
| tree-sitter-julia      | [#2](https://github.com/conda-forge/tree-sitter-julia-feedstock/issues/2) (2026-06-16)      | [#4](https://github.com/conda-forge/tree-sitter-julia-feedstock/pull/4) (Wave B Batch 1)                                                            | (CI green at merge)               | `42467c0` (merged 2026-06-16 22:43Z) | _<Wave D>_                         |
| tree-sitter-verilog    | [#1](https://github.com/conda-forge/tree-sitter-verilog-feedstock/issues/1) (2026-06-16)    | [#3](https://github.com/conda-forge/tree-sitter-verilog-feedstock/pull/3) (Wave B Batch 3)                                                          | (CI green at merge)               | `9338e52` (merged 2026-06-16 23:23Z) | _<Wave D>_                         |
| tree-sitter-json       | [#2](https://github.com/conda-forge/tree-sitter-json-feedstock/issues/2) (2026-06-16)       | [#4](https://github.com/conda-forge/tree-sitter-json-feedstock/pull/4) (Wave B Batch 1)                                                             | (CI green at merge)               | `c867432` (merged 2026-06-16 22:43Z) | _<Wave D>_                         |
| tree-sitter-markdown   | [#2](https://github.com/conda-forge/tree-sitter-markdown-feedstock/issues/2) (2026-06-16)   | [#5](https://github.com/conda-forge/tree-sitter-markdown-feedstock/pull/5) (v0.5.3 + setup.py patch + platform expansion, merged 2026-06-16 22:12Z) | (verified by author before merge) | `1d7b45b`                            | _<Wave D>_                         |

## Cat 2 — 7 in-flight (watch + conditional takeover, ALL MERGED 2026-06-16)


| Feedstock              | Maintainer-add issue                                                                          | Sumanth PR #    | Last activity            | Takeover triggered? | Our PR #                                   | Merged SHA |
| ---------------------- | --------------------------------------------------------------------------------------------- | --------------- | ------------------------ | ------------------- | ------------------------------------------ | ---------- |
| tree-sitter-javascript | [#2](https://github.com/conda-forge/tree-sitter-javascript-feedstock/issues/2) (pre-existing) | #1 (2026-06-07) | merged 2026-06-16 12:05Z | no                  | sumanth's #1                               | `d98885e`  |
| tree-sitter-go         | [#2](https://github.com/conda-forge/tree-sitter-go-feedstock/issues/2) (2026-06-16)           | #1 (2026-06-07) | merged 2026-06-16 12:08Z | no                  | sumanth's #1 (with rxm7706 commits on top) | `3d6579b`  |
| tree-sitter-groovy     | [#3](https://github.com/conda-forge/tree-sitter-groovy-feedstock/issues/3) (2026-06-16)       | #2 (2026-06-07) | merged 2026-06-16 13:45Z | no                  | sumanth's #2 (with rxm7706 commits on top) | `d28e6d7`  |
| tree-sitter-c          | [#2](https://github.com/conda-forge/tree-sitter-c-feedstock/issues/2) (2026-06-16)            | #1 (2026-06-07) | merged 2026-06-16 13:53Z | no                  | sumanth's #1 (with rxm7706 commits on top) | `2a3c115`  |
| tree-sitter-cpp        | [#2](https://github.com/conda-forge/tree-sitter-cpp-feedstock/issues/2) (2026-06-16)          | #1 (2026-06-07) | merged 2026-06-16 13:52Z | no                  | sumanth's #1 (with rxm7706 commits on top) | `ea6383e`  |
| tree-sitter-elixir     | [#2](https://github.com/conda-forge/tree-sitter-elixir-feedstock/issues/2) (2026-06-16)       | #1 (2026-06-07) | merged 2026-06-16 13:51Z | no                  | sumanth's #1 (with rxm7706 commits on top) | `01bd434`  |
| tree-sitter-fortran    | [#3](https://github.com/conda-forge/tree-sitter-fortran-feedstock/issues/3) (2026-06-16)      | #2 (2026-06-07) | merged 2026-06-16 13:47Z | no                  | sumanth's #2 (with rxm7706 commits on top) | `bbcf47d`  |

## Final state

- Wave A complete: 2026-06-16 — 22 maintainer-add issues opened; bot processed all 22 team-adds same-day. `rxm7706` confirmed on all 22 `conda-forge/tree-sitter-*` teams via `gh api orgs/conda-forge/teams/<feedstock>/members`. S-A3 checkpoint cleared.
- Wave C complete: 2026-06-16 — all 7 Cat-2 PRs merged (javascript first, then go + groovy + fortran + elixir + cpp + c). No takeovers triggered; sumanth's PRs all merged with rxm7706 follow-up commits on top (native+cross conda-forge.yml uplift via post-mgorny-review canonical pattern). Spec scope-extended addendum 2026-06-16 added tree-sitter-markdown to Cat-3 (16th feedstock).
- tree-sitter-markdown shipped 2026-06-16 22:12Z — out-of-band Cat-3 closeout via PR #5 (`1d7b45b`). Two-step closeout: (a) autotick PR #1 closed (broken upstream v0.5.3 setup.py — flat src/ layout vs dual-grammar tarball — SKILL.md G5 sibling case); (b) PR #4 opened with `bot.version_updates.exclude` as safety belt then closed when PR #5 (v0.5.3 with setup.py patch + platform expansion bundled by operator before merge) shipped the real fix. Local build verified `tree-sitter-markdown-0.5.3-py310h03a07cb_0.conda` 136 KiB before PR. Wave B remaining count drops 16 → 15.
- Wave B Batch 1 complete 2026-06-16 22:42-22:43Z — 5 Cat-3 platform-expansion PRs (tree-sitter-{java, json, julia, kotlin, lua}) all merged within ~1 minute of each other:
  - tree-sitter-java PR #4 (`6b693f6`, 22:42Z)
  - tree-sitter-json PR #4 (`c867432`, 22:43Z)
  - tree-sitter-julia PR #4 (`42467c0`, 22:43Z)
  - tree-sitter-kotlin PR #3 (`923956e`, 22:42Z)
  - tree-sitter-lua PR #3 (`1c09c91`, 22:42Z)
  - All shipped with the full 2026 canonical conda-forge.yml (conda_install_tool: pixi + platform-expansion block + bot.{automerge, inspection: update-grayskull, check_solvable, run_deps_from_wheel}) + build_number supersede + maintainer alphabetical reorder. Wave B remaining count drops 15 → 10 (Batch 2 + Batch 3).
- Wave B Batch 2 complete 2026-06-16 22:57-23:05Z — 5 Cat-3 platform-expansion PRs (tree-sitter-{objc, php, powershell, ruby, rust}) all merged within ~8 minutes:
  - tree-sitter-objc PR #3 (`2fd9e36`, 22:57Z)
  - tree-sitter-php PR #4 (`1cb1106`, 22:59Z) — PR #1 license-patch had already merged 13:42Z; this is the routine platform-expansion follow-up against main's v0.24.2 state
  - tree-sitter-powershell PR #5 (`79c4471`, 23:02Z)
  - tree-sitter-ruby PR #3 (`832a455`, 23:01Z)
  - tree-sitter-rust PR #3 (`bb70dd1`, 23:05Z)
  - Same full 2026 canonical conda-forge.yml shape as Batch 1. Wave B remaining count drops 10 → 5 (Batch 3).
- Wave B Batch 3 complete 2026-06-16 23:17-23:23Z — final 5 Cat-3 platform-expansion PRs (tree-sitter-{scala, swift, typescript, verilog, zig}) all merged within ~6 minutes:
  - tree-sitter-scala PR #3 (`64e3924`, 23:17Z)
  - tree-sitter-swift PR #4 (`73e78f3`, 23:18Z)
  - tree-sitter-typescript PR #3 (`45da046`, 23:22Z)
  - tree-sitter-verilog PR #3 (`9338e52`, 23:23Z)
  - tree-sitter-zig PR #3 (`a15d42d`, 23:23Z)
  - **🎉 Wave B closed. All 22 platform-expansion PRs merged. 16 Cat-3 (incl. markdown) + 7 Cat-2 platform expansions = 23 feedstocks now ship osx-arm64.** Next: Wave D smoke-test after CDN propagation.
- Wave D smoke-test result (2026-06-17 03:25Z): **✅ PASS**. `CONDA_OVERRIDE_OSX=11.0 mamba create -n test-graphifyy-osx-arm64 -c conda-forge --platform osx-arm64 --dry-run graphifyy` resolved cleanly — 62 packages / 71 MB. All 22 tree-sitter-* deps pulled from conda-forge osx-arm64 builds; many at `*_2` builds (Wave B platform-expansion rebuilds); `tree-sitter-swift 0.7.3 py310h28d811c_2` is the dist-info-fixed build from S-F5 PR #5. Solver picked graphifyy 0.8.10 (still-published version at smoke-test time; 0.8.40 uploaded to anaconda.org at 03:01:42Z but conda-forge repodata had not yet refreshed — typical 30-60 min lag). Dep set is identical between 0.8.10 and 0.8.40 base requirements so 0.8.40 resolves the same way once propagated. **Goal 1 (graphifyy installable on osx-arm64) empirically met.** S-D1 ✅ (all 22 names searchable). S-D2 ✅ (dry-run solve complete). S-D3 deferred (no osx-arm64 host on hand).
- Closeout retro CHANGELOG entry: **✅ landed** as CFE v8.26.0 (commit `f9ed72127f`, 2026-06-17). Three deltas: G23 (cmd.exe escape trap with sed+m2-sed canonical fix), G24 (wheel dist-info Version mismatch detection + dynamic-tag remedy), DEP-002 sub-rule (load-bearing upstream-declared upper bounds — do NOT drop). 59 files changed; 3,202 insertions; 23 tree-sitter-* feedstock mirrors synced; 3 staged-recipes drafts (now all OPEN on staged-recipes — see S-F4 follow-ups below). Skill bump 8.25.0 → 8.26.0 (MINOR; additive).
- S-F4 staged-recipes draft PRs (all OPEN 2026-06-17):
  - [#33752](https://github.com/conda-forge/staged-recipes/pull/33752) — Create recipe.yaml for FalkorDB (head `falkordb`, opened 00:11:50Z). CI: linter ✅ · linux_64 ✅ · osx_64 ✅ · win_64 ❌ outstanding.
  - [#33753](https://github.com/conda-forge/staged-recipes/pull/33753) — Ctranslate2 suite (head `ctranslate2-suite` sha `4cbc0189`, opened 00:34:29Z). Multi-output libctranslate2 + ctranslate2 (CPU-only, OpenBLAS/Accelerate, no CUDA/MKL).
  - [#33754](https://github.com/conda-forge/staged-recipes/pull/33754) — Faster whisper (head `faster-whisper` sha `9e13e5ac`, opened 00:44:14Z). Sequencing: gated on #33753 landing first; remains draft until then.
- Effort complete: **2026-06-17 03:25Z** (Wave D smoke-test pass + retro shipped + commit pushed).
