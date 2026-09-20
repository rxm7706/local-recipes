---
title: Marshal — autonomy a human can trust
type: dream
owner: marshal
status: specified
---

# Marshal — graduated autonomy on the factory floor

## The Dream

The Commander's dream: **unattended development loops a human can actually
trust.** Not autonomy as a leap of faith — autonomy as a *gradient*: attended
stories first, then unattended loops wrapped in verify gates and quality
gates, with a hard rule that anything the agent cannot safely decide
**escalates to a human** instead of being guessed. Spec in, validated code
out, every run visible. Anti-vibe, by construction.

Execution has one owner. Skills — existing, community, and forged — are the
unit of execution; the deterministic harness is the unit of governance;
station verdicts stay independent. The thing that governs the agent cannot be
a thing the agent authors.

## What is real

**Updated 2026-09-11 (this paragraph had frozen at the original 10/50-story
snapshot).** `marshal` (module `pyforge.marshal`) has shipped 240 of 243
tracked stories across 34 epics, per `fleet-picture`; Epic 1 (provisioned,
verified loop homes) was the first to complete, and nearly all of the epics
that followed are `done` as well, with 3 stories left structurally blocked
(not waiting on an operator). The capability already exists as `bmad-loop`
and has driven two sibling stations to full completion unattended:
`pyforge-atlas` (38/38) and `pyforge-warden` (31/31). Ten real capabilities
were originally contracted in `spec-pyforge-marshal` (CAP-1 loop homes and
isolation · CAP-2 supervised unattended runs · CAP-3 gates you can run · CAP-4
landing with a durable paper trail · CAP-5 fleet visibility · CAP-6
portability proven, not claimed · CAP-7 policy composition · CAP-8 one
install yields the whole stack, plus CAP-9/CAP-10 from later decomposition);
the spec has since grown well past CAP-10 as later epics (token economy,
parallel dispatch fan-out, single-story dispatch, and more) were decomposed
in — see `spec-pyforge-marshal` directly for the current capability list
rather than this paragraph, which predates most of them.

The BMAD suite underneath: BMAD 6.10 (BMM 34+ workflows) + BMB/TEA/BMGD/CIS,
web bundles for flat-rate planning, community plugins (skill-forge), and the
multi-project machinery (`scripts/bmad-switch`, per-project config/artifact
isolation). Visibility runs through the GitHub Pages program console
(`docs/dashboard/`), regenerated from tracked ledgers, never hand-trusted.

**Dispatch autonomy hardening (2026-09-01).** A live Epic 28 drain campaign surfaced
recoverable failure modes that must not require operator archaeology: sidecar'd
journal payloads breaking auto-land, harness quota/auth permanently blocking fleet
drain, verified-but-unmerged stories stuck without land retry, and no per-invocation
`--harness` override. Interim machinery now distinguishes transient harness/verify
blocks from terminal ones, resolves AD-30 sidecars on the dispatch supervisor read
path, and reconciles campaign blocked-maps against `origin/main` merge evidence.
Stories 28.13 (sanctioned SIGTERM retry) and 28.14 (auto-derived surface) remain the
durable contracts — the hotfixes are explicitly interim where they differ.

## Six follow-on dreams, consolidated here (2026-08-02)

This Dream previously sat alongside six satellite dreams, each answering one
question the original scope raised. Five are now fully decomposed into
Marshal's real chain — their standalone dream files are archived, their
vision lives in the FRs named below, not as separate documents to track:

- **Durable runs** (bounded-loss durability) → **FR-61/62/63**. The measured
  cost of not having this: six station loop branches on no remote, ~5,150
  lines across rescue branches, one unpushed commit 40 minutes from a `git gc`.
  Stage-boundary push + fleet-launch wiring, branch retirement, durability as
  a reported fleet-status dimension.
- **Fidelity enforcement** (a gate that fires in both directions at every tier
  boundary) → **FR-64**, the Marshal-owned slice — a gate evaluation binds to
  the tracked spec's Success signal, so a spec that stops being tested does
  not silently keep passing. The Doctor- and Scribe-owned slices of the same
  Dream stay with their own stations, not folded in here.
- **One front door** (`marshal check` — the detector registry through a single
  command, context resolved once) → **FR-65**.
- **PR lifecycle** (open, label, wait for checks, merge, retire the branch,
  resync — done once by the harness instead of improvised each time) →
  **FR-59/60**, `marshal land`.
- **Agent portability** (the method outlives the tool — Devin, Copilot,
  Cursor, Gemini, not just Claude) → **CAP-6 / Epic 6** ("Portability proven,
  not claimed"): skill-tree projection, adapter probe, conformance matrix,
  entry-file drift detection. A standing practice, not a one-time build — its
  narrative now lives here rather than in a separate practice document.

## Eight more, consolidated here (2026-08-08)

The 2026-08-02 pass folded six. Eight more follow, on the same terms: the
standalone dream files are archived in place, the **Spec of each stays live and
remains the contract**, and the vision lives in the FRs named below rather than
in separate documents to track. What changed is that these eight finally have
FRs at all — until today Marshal's PRD decomposed only two of its twenty-four
Specs, because a rule scoped FRs to work touching `pyforge-marshal`'s own
package. Not one open Spec did, so the rule excluded all of them by
construction. It is now an **ownership** test: a capability decomposes into
Marshal's chain iff its Dream is `owner: marshal`.

- **The shared floor** ([[pyforge-core]], minted the same day) → **FR-157..163**.
  Five primitives written between three and twenty times across eight stations —
  atomic write ×20 (6/8 stations), verdict lattice ×5, report envelope ×3
  schemas, station roster ×3+1, no shared exception root. One leaf package, pure
  stdlib, importing no station. Sequenced **before Epic 7's stories 7.2/7.3**,
  which would otherwise have minted copy #21 and copy #6 inside the very rewrite
  meant to consolidate.
- **Loop-home fleet refresh** → **FR-133..135**. Nine worktrees found 227
  commits stale on 2026-08-08 and refreshed by hand, twice, in one session.
  Staleness detection, fast-forward with a clean-worktree refusal, and the
  policy re-render as a *checked step of the same command* rather than a
  separately remembered second one.
- **Landing-to-ledger promotion** → **FR-136..139**. Three live staleness
  incidents in one session. FR-139 also carries the fix for a defect found
  while writing it: a stale feed silently overwrote the tracked ledger and
  dropped six `done` keys while reporting success — terminal states are now
  monotonic, and a write that un-finishes a story is refused and named.
  **2026-09-02 leftover:** 15.2 promoted on the operator `main` checkout
  after GitHub already moved `origin/main`, so every land left local
  `main` diverged. Isolation belongs in a throwaway worktree on the
  remote tip (same lesson as Story 4.3 `merge_branch`), not on `main`
  and not on the story dispatch branch. See [[sprint-status-auto-promote]]
  and CAP-5.
- **Dashboard path derivation** → **FR-140..143**. `generate.py` string-glued
  slugs onto project paths in several places, each with its own patch; a `TODO`
  in the code named the gap. One resolver, one override table, derived
  discovery, and an unresolvable slug fails loud instead of rendering a 404.
- **Detector self-verification** ([[dream-to-code-model-self-verification]]) →
  **FR-144..147**. Both detectors gate the tree; nothing gated the detectors.
  Three real incidents — and a fourth the same day this consolidated: a
  measurement taken with an ad-hoc regex instead of the real parser produced a
  false fleet-wide finding that had to be retracted within hours. The incident
  log is the capability.
- **Chain completeness** → **FR-148..152**. Regenerating Dream→Spec→…→Epics
  coherently, plus orphan detection. Now also carries the reconciliation
  measured on 2026-08-08: six of eight stations hold tracked story specs with
  no ledger key (herald 34, doctor 4, atlas 3, scribe 1, steward 1).
- **The governed tool surface** → **FR-153..156**. Shipped without one; the
  2026-07-28 audit found 2-of-6 station coverage with Marshal itself at zero,
  inside a Dream marked `realized`. Coverage is measured now, not asserted:
  `pyforge/marshal/mcp/coverage.py::tool_surface_coverage_report` is a live
  function, not a stamped number, and it currently returns 3/6 — Story 18.1
  gave Marshal its own 7-tool server, closing the practice-owner's own
  zero-coverage gap the 2026-07-28 audit named (see [[agent-tool-surface]]).
- **Retiring the installer's separate name** ([[genesis-installer-name-retirement]])
  → executed 2026-08-08, this session. One FR space (`FR-1..FR-163`, no gaps),
  one `epics.md` (Epics 1-12, 86 stories), one dashboard row, and the two
  contradictions the consolidation had preserved rather than resolved —
  argparse-versus-typer and the `init`/`check` verb collisions — actually
  decided (AD-51, AD-54, AD-70).

**Three Marshal-owned `type: practice` documents are deliberately NOT absorbed**
— [[agentic-sdlc-autonomy]], [[agent-tool-surface]] and [[regenerable-factory]].
A practice sits outside the lifecycle by the Dream tier's own contract
(`docs/dreams/README.md`): *tended, never finished*, excluded from Backlog and
from Realized. Archiving one would assert a completion that cannot exist. Their
*capabilities* decompose into the chain where they have any; the documents
stand.

## Kept separate on purpose

**Genesis installer** (`genesis init` / `genesis adopt` — standing up a repo
with the pixi environment, bmad-method, multi-project wiring, and the
BMM/BMB/TEA modules in one command) is real, substantial, Marshal-owned
buildable work — but it is not the `marshal` CLI itself. **Only its epics stay
kept separate now** (`epics-genesis-installer.md`, its own 6 epics / 36
stories, epics 7–12) — unchanged. *(Revised 2026-08-02, explicit user
override.)* Its brief, PRD, architecture, and Spec were **consolidated** into
this station's own single brief / PRD / architecture / Spec
(`product-brief-pyforge-marshal.md`, `prds/prd-pyforge-marshal-2026-07-25/prd.md`,
`architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md`,
`specs/spec-pyforge-marshal/SPEC.md`), each carrying a clearly labelled
"Satellite: Genesis Installer" section (brief/PRD) or continued `AD-`/`CAP-`
numbering (architecture: `AD-51..AD-65`; Spec: `CAP-10..CAP-18`) rather than
the previously-separate documents. This reverses the "not merged into
Marshal's own FR range" line that stood here before — the FR range is still
distinct (genesis-installer's own `FR1..FR62`, no dash, never renumbered into
Marshal's `FR-1..FR-65`), but the *documents* are no longer separate. The four
original standalone documents are preserved at
`archive/_bmad-output/projects/pyforge-marshal/planning-artifacts/{research/product-brief-pyforge-genesis.md,
prds/prd-genesis-installer-2026-07-25/, architecture/architecture-genesis-installer-2026-07-25/,
specs/spec-genesis-installer/}`. Constitutive records (the Charter, the
Guild's membership) and the machine that installs them are still different
nouns; that boundary is unchanged by this consolidation.

**Factory console** (the GitHub Pages program console at
`docs/dashboard/`, published from `main`, two-source refresh, the Dreamscape
lifecycle board) is shipped and real — the "every run stays visible" doctrine
above, given a front door. Folded in here 2026-08-02 (dream-level only):
`spec-factory-console` (2 companions — `console-contract.md`,
`drill-evidence.md`) stays live and untouched, since real frontier work is
still named against it — per-Dream drill-through to deck/spec/BMAD-project
rows, a delivery/notables feed, and a fleet-health strip fed from
[[pyforge-doctor]]. No PRD exists for it yet; this Spec is the current,
binding reference for that unbuilt work, not this Dream's prose.

## The frontier — real, not yet built

**Fleet-chain completeness** — an orchestrated workflow that regenerates a
project's entire Dream→Spec→Research→Brief→PRD→Architecture→Epics chain from
a consolidated Dream, pausing for human review before committing. Moved here
2026-08-02 from Herald (it is infrastructure/machinery, not Herald's "voice
and visual surface" scope) and consolidated from its own former dream file.
Genuinely unbuilt — the eight-phase workflow it describes is exactly what this
session's own dream-consolidation pass did by hand, station by station. Real
enough to warrant its own Spec — authored 2026-08-02 (`spec-fleet-chain-completeness`,
5 capabilities: orchestrated regeneration, code-status preservation, an audit
mode, review-gated orphan cleanup, per-project configurability) — not yet
decomposed to PRD/Architecture/Epics.

**Fleet-wide test architecture** (`spec-pyforge-testing-charter`, 5
capabilities) — mixed disposition, folded in 2026-08-02 from its own former
dream file. Two capabilities already shipped this session: CAP-1 (the
dashboard's `tea` glob corrected to `src/shared/packages/<slug>/tests/**/test_*.py`,
verified on disk in `pyforge.doctor.sources.fleet_scan`) and CAP-2 (real, generated
`test-architecture.md` for all 8 stations, replacing the six boilerplate
stand-ins a prior bulk commit had fabricated). CAP-5 (test architecture stays
current as stories land) is an ongoing practice, not a one-time build. **CAP-3
(a shared `pyforge-testing-kit` package — verified 2026-08-02, does not yet
exist) and CAP-4 (a CI coverage gate — verified 2026-08-02, no
`--cov-fail-under` in any workflow) are real, unbuilt, and not yet decomposed
to a PRD.** The Spec (and its `station-tea-status.md` companion — the real,
verified per-station test-file counts this Dream's own claims got wrong) stays
live as the reference for that remaining work.

**Fleet consistency standard** — the operating model has drifted from its own
instruments, and the instruments are the last place anyone looks. Measured
2026-09-07 across all 8 stations, on an operator brief of *"simplicity and
consistency decides"*:

- **`_bmad-output/EXEMPLAR-STANDARD.md` — the document that defines the model —
  is itself the largest stale customization.** Its 16-stage table names four
  skills that no longer exist (`bmad-document-project`, `bmad-create-story`,
  `bmad-check-implementation-readiness`, `bmad-dev-auto`) and three research
  skills BMAD 6.12 consolidated into `bmad-deep-recon`. It mandates
  `epics-with-stories.md`, which 6.12 produces nowhere. It carries a
  self-invalidating clause (*"when it and pyforge-atlas disagree, pyforge-atlas
  is right and this document is stale"*), and its own verification section
  admits INV-2/INV-3 were measured by hand and never mechanized.
- **`epics-with-stories.md` is a derived summary that stopped being derived** —
  frozen at 2026-08-08 in six of eight stations while `epics.md` moved to
  2026-09-06. Two of its four consumers actively *exclude* it as a derived
  file; one is an inert allowlist entry; one reads it only as a fallback.
  Retirable — except steward's suite-shape mandate is buried inside it, which
  is what a derived file accumulating contract is worth as a warning.
- **The fleet grew eight test-suite names for two concepts.** CLI-contract
  conformance (steward's `conformance/`, 32 files; marshal's `contract/`, an
  empty placeholder; herald's 12 loose `test_cli_*.py`) and oracle/engine gates
  (warden's `conformance/`, 19 files; marshal's `oracle/`, 1 file). BMAD 6.12's
  Python default is `tests/{conftest.py, unit/, integration/, api/}`. The
  coverage gate's suite map knows neither `conformance` name, so **51 real test
  files are measured by nothing**, and `marshal/support/` is a helper module
  wearing a suite's clothes.
- **`pytest-cov` is declared in 2 of 10 pixi features.** Seven station envs
  cannot run a coverage gate at all — verified live against scribe: exit 1,
  `unrecognized arguments: --cov`. Nobody has ever measured the fleet's real
  coverage, which `spec-pyforge-testing-charter`'s own assumptions already say
  out loud.
- **Three date formats for one artifact.** `implementation-readiness-report-`
  appears as `-20260801`, `-2026-08-01`, and undated across 27 files. Not
  cosmetic: `bmad_drift_check.py`'s classifier matches only the hyphenated ISO
  form, so the compact variant lands as `uncovered` the moment the detector is
  pointed at those five stations.

What is *not* drifting is worth naming, because it shows the model works when
it is mechanized: the five-tier check reports **40/40 cells green**, mason's
skill tier deliberately resolving to `conda-forge-expert` (Epic 11.1, "CFE
stays; no second recipe skill") — a documented, tested exception that a
by-hand audit would have mis-filed as a gap, and did, until the check was run.

The resolution is three-layered, and each layer has a different lifetime: the
pre-action rules go into `AGENTS.md` through `bmad-project-context` (never
hand-edited — its managed block is replaced on refresh); the reviewable
enumerations stay in `EXEMPLAR-STANDARD.md`, **rewritten as this effort's Spec
companion rather than deleted**, because `pixi.toml`'s `dream-chain` detector
names it as its `Contract:` and 33 other files reference it; and the effort
itself becomes `spec-fleet-consistency-standard` here. Coverage is deliberately
*not* folded in — it amends `spec-pyforge-testing-charter` CAP-4, which already
owns it, rather than re-minting an owned capability.

Other open frontier items, unchanged: many-lines-one-floor concurrency (a
floor that survives two writers, not just isolated worktrees); crossing the
boundary between stations as structured, machine-checkable output; a crash an
unattended reader can act on; a run that cannot be torn down while still
alive; a seam for estates this factory cannot see ([[enterprise-airgap]]).

## Realization log

- **2026-09-18** — **Proposed: the landing self-drives — what the first autonomous
  drain still needed a human for.** Herald's Epic 23 (four stories) was drained to
  zero today by `marshal factory dispatch` on the Claude harness — the first
  verified-landed-ledger-flipped stories since 2026-09-12, 46–66 min each. Every one
  landed itself, and every one still needed a human within the hour. Measured on
  the journals, not remembered: (1) the campaign supervisor cycles every 60 s and,
  inside the ~45 s between the session exiting and `dispatch_land_finalize`
  flipping the ledger, sees the story neither live nor `done`, re-dispatches it, the
  new session refuses ("already merged"), and the campaign records its own refusal
  as a story block and **exits** — four landings, four manual relaunches
  (`fleet-drain-runs/…151925342Z-82ce96c8`, `…162241936Z-bfc1f666`). (2) Cursor's
  live wording *"You're out of usage. Switch to Auto, or ask your admin to increase
  your limit"* matches none of `harness_session._QUOTA_MARKERS`, so a three-second
  cursor death classifies `unknown` → **terminal** block, never retried
  (`…132400673Z-194af3a0`). (3) `--harness claude` cannot rescue a station whose
  tier map names an inline `{ harness = "cursor", … }` — Story 28.11 puts the tier
  map's harness at the head of the walk regardless of the flag, and cursor's
  authcheck passes while the session dies on the usage wall; herald needed a policy
  PR (#1458) to move at all. (4) `Merge {key} into main` carries no station token and
  Story 35.1's `known_keys` only rejects keys the ledger does *not* know — atlas's
  seven `Merge 23-N into main` merges read as herald's 23.1/23.2/23.5/23.6 already
  merged, and the un-scoped `Story N.M:` direct-commit shape does the same across
  stations (steward's `Story 48.2:` poisons marshal 48.2 today — this very epic had
  to skip 48 and 49). (5) `_already_promoted_keys` trusts `is_valid_spec_text`,
  which requires the tracked spec to *start* with `---`; 45 tracked specs fleet-wide
  began with a `<!-- RECOVERED/MINTED/Promoted -->` banner, and finalize re-promoted
  herald's stale Tier-3 `spec-1-4` over the reconciled tracked copy (local commit
  `b0b7f3019f`, caught before push; PR #1460 moved the banners, the promoter still
  cannot read a banner). The Dream is that a drain launched at 09:00 is at zero by
  lunch with nobody watching. Decomposed the same day as CAP-244..248 / Epic 50
  (48 and 49 are reserved holes: their keys are poisoned by steward's
  `Story 48.N:` / `Story 49.N:` subjects, per the renumber-not-exclude rule). The
  sixth thing a human did — `ledger-regression` reddening a story PR's `detectors`
  lane *after* the unattended merge, because the PR head is stale against the
  promoted ledger — is doctor's source and is seeded on [[pyforge-doctor]] as `spec-pyforge-doctor:CAP-78`.
- **2026-09-18 (later)** — **Proposed: what the second drain still needed a human
  for.** With Epic 50 draining under its own fixes (50.1 ended the race-respawn,
  50.2 the quota-wording block, 50.3 the tier-map override, 50.4 the un-scoped
  evidence), doctor 27.1–27.5, herald 24.1–24.3 and marshal 50.1–50.4 all landed
  themselves the same day — and the next set of human acts is different in kind
  from the first. Measured on the journals and on `main`: (1) **verification
  never sees the merge result.** `dispatch verify` runs the station suite on the
  branch tip; a story whose baseline predates a sibling's landing on the same
  files reaches `dispatch land` *verified* and is refused there (MRS-DISP-038,
  PR left open, no re-verify-after-merge step). Marshal 50.4's review pass rewired
  doctor's `sources/marshal.py` / `sources/ledger.py`; doctor 27.5 had rewired the
  same files 42 min after 50.4's baseline. Hand-composed (`1a5895317f`) — and the
  parts git *did* auto-merge would have shipped a runtime `TypeError`
  (`bare_merge.py`'s 2-arg call against 50.4's 3-arg signature): a green branch
  suite is not a green merge. (2) **finalize promotes from the primary's Tier-3
  dir, but the session writes its record into the worktree's.** bmad-build-auto
  wrote 50.4's Review Triage Log, Auto Run Result, `followup_review_recommended:
  true` and its one deferral to `<worktree>/implementation-artifacts/spec-50-4-…`
  (with the tracked spec as `context:`), flipped only `status:` on the tracked
  copy, and the worktree is neither bind-mounted nor backlinked — so
  `dispatch_land_finalize` found nothing to promote and the tracked spec landed
  `done` with none of its record; promoted by hand (#1488), DW-FU-50-4 ingested by
  hand. Same landing: the journal's `dispatch-land` projection read `pr_number:
  null, marshal_native: false` for a refusal that happened *after* PR #1487 was
  opened, labelled and passed the native check. (3) **finalize never refreshes the
  primary checkout** — the campaign reads the promoted ledger only after an
  operator `git pull` (herald 23.x, every landing). (4) **a blocked outcome still
  lands.** Doctor 27.3's session found an intent gap, reverted to baseline and set
  `blocked`; marshal landed the empty branch (PR #1476) and promoted `27-3 → done`
  — the truth had to be written above the Auto Run Result by hand and the story
  re-minted as 27.4→27.5. (5) **MRS-DISP-043 is silent for an uncatalogued model**
  (DW-FU-50-3, from 50.3's own review). (6) **`marshal watch` infers the pattern
  from August's paused bmad-loop runs**, so a station now driven by `dispatch`
  reports the wrong run; the fleet watch read journals directly all day. (7) **a
  station-prefixed branch name poisons a key**: `doctor/27-4-mint` parsed under
  the station-branch landing grammar, so merging its PR (#1477) made 27.4 read
  landed and its first dispatch detached from a live session in one second —
  landing evidence is station-scoped (50.4) but not intent-scoped. (8) **the
  pyforge-core suite has no CI lane** since #1086 (2026-09-08) retired
  `pyforge-core.yml` as redundant: six `spec-pyforge-core` CAP-5/CAP-7
  conformance violations accumulated unseen between 09-07 and 09-15 (marshal
  `adapters/oidc_pkce.py`, `cli/watch.py`, `cli/login.py`, `cli/refresh.py`;
  warden `tea_advisory.py`; testing-kit `branch_diff_guard.py`) and surfaced only
  because 50.4's hand-merge was verified on that suite — co-governed here, owned
  by `spec-pyforge-core`. Not decomposed tonight: (1)–(7) are the next
  `bmad-spec` pass on this chain (Epic 51 onward; 48/49 stay reserved holes),
  (8) is a `spec-pyforge-core` realization gap.
  **Decomposed 2026-09-19:** (1)–(7) as CAP-249..256 / **Epic 51** (51.1–51.8, one per
  CAP, plus 50.5's two review deferrals DW-FU-50-5/-6 folded into 51.8; DW-FU-50-3 is
  51.5, DW-FU-50-4 is 51.7); (8) as `spec-pyforge-core` CAP-8/CAP-9 / **Epic 52** (52.1
  clears the six violations by hand — half the files are warden/testing-kit; 52.2 wires
  the lane). One correction on the evidence: #1086's retirement of `pyforge-core.yml`
  was coverage-neutral — that lane and `pyforge-pip-install.yml` run the same enumerated
  subset, and `tests/meta/*_sole_ownership.py` (added 2026-08-12/13) were never wired
  into any workflow; the suite was red on `main` today at 6 failed / 1855 passed.
- **2026-09-19 (the third drain, in flight)** — **Proposed: what the Epic 51 drain still
  needed a human for, measured on the day.** (1) **A hollow landing.** Story 51.3's session
  was terminated at Claude Code's print-mode ceiling (`Background tasks still running after
  600s; terminating. Set CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0 to wait indefinitely`) before
  its implementation subagent committed anything; the branch's only commit was the tracked
  spec's `ready → in-progress` flip; `has_git_progress` counted it as progress, verify was
  green on an unchanged tree, land merged PR #1501 and finalize promoted `done`. CAP-252 is
  widened to cover the hollow shape and the harness-ceiling wording; the story is re-minted as
  51.9; the durable fix for the ceiling belongs in the claude harness profile
  (`data/harness_profiles/claude.toml` sets no such env key — the remaining drain passes it
  at launch). (2) **Post-land completion reads `stopped_externally` / `external-operator-stop`
  with zero changed paths** on every successful land (51.8, 51.2, 51.3) — a classifier that
  judges completion after the merge against a tree that now equals `main`; harmless for a
  single dispatch, a false block for a campaign. (3) **The dispatched session writes no memlog
  entry** (CAP-239 is bmad-loop-only), so `spec-surface` is red with `drift` rows on `main`
  after every merge until the operator names the paths and stamps; and every landing's
  bookkeeping files (memlog tails, `.spec-surface-baseline.json`, the ledger) conflict with
  the next PR's, so each hand landing pays a union-merge. (4) **A land refused on a sibling's
  bookkeeping** (doctor 28.1 after 51.2's fallout) — CAP-249's case, but the conflicting files
  were memlogs and the baseline, not code; the re-verify-on-merged-tree step should also
  auto-resolve append-only files. (5) **`followup_review_recommended: true` carries nothing
  forward** (51.2's record) — it needs a DW entry or a scheduled follow-up dispatch, or the next
  landing on the same hub files goes unreviewed. Not decomposed today: (1) is folded into
  CAP-252's amendment (Story 51.4, widened); (2)–(5) are the next `bmad-spec` pass on this chain.
  **(6), found on 51.9's landing (13:0xZ):** CAP-250's promotion never fires for a
  pre-authored tracked spec — `_already_promoted_keys` (CAP-248) reads any valid-frontmatter
  tracked spec as already promoted, and every minted story HAS one (MRS-GATE-010 needs the
  Success signal on `main` before dispatch), so the worktree twin's Review Triage Log / Auto
  Run Result / `deferred:` are never merged in; 51.6 self-promoted only because its session
  wrote the tracked spec directly. The promotion needs a merge rule for a twin whose
  `status:` is terminal while the tracked copy's is not (or whose Auto Run Result the tracked
  copy lacks). Hand-promoted for 51.2 and 51.9.
- **2026-09-20 (night, the third drain)** — **Proposed: the watch is blind to the very runs
  it was fixed to see, and a session that halts on its own reads as an operator stop.**
  (7) `marshal watch --fleet` reported all eight stations *idle* at 00:38Z while three
  dispatch sessions (doctor 26.1, steward 61.3, marshal 51.7) were live. Story 51.6 wired
  the dispatch-run pattern into `cli/watch.py::_gather_station`, but the `marshal_home`
  probe it reads shells out to `python -m pyforge.marshal status …`, and
  `pyforge/marshal/__main__.py` does not exist — the console script is
  `pyforge.marshal.cli.main:main` — so `ProcessError` → `None` on every call, and the unit
  test for the probe *asserted that wrong argv* against a fake: the suite pinned the bug
  in place. Nothing exercised the module name against the real interpreter. Operator
  ruling (00:40Z): fix it, don't read journals by hand around it. (8) Doctor 26.1's
  session (run `…233255320Z-8f2b958e`) halted on an intent gap the way the workflow says
  to — code reverted, the tracked spec flipped to `blocked` with its triage log — but
  left both *uncommitted* in the worktree and exited. The supervisor read
  `session_alive: False` against a HEAD that still carried two wip commits with real code,
  wrote `dispatch-finalize ok:false` and `dispatch-completion stop_reason:
  external-operator-stop`, and never a `dispatch-blocked` row (CAP-252's detection reads
  committed state only; marshal 51.7's earlier halt was detected only because that session
  committed the blocked spec first). `fleet-picture` then shows the story `backlog` with no
  trace of why. **Decomposed 2026-09-20:** (7) → CAP-257 / Story 51.10 (hand-driven, same
  PR); (8) → CAP-258 / Story 51.11 (dispatch after 51.7 lands — same supervisor hub file). **Realized 2026-09-20:** 51.10–51.13 landed (#1534, #1540, #1537); Epic 51 closed with the marshal, doctor and steward lanes each showing their live run in `marshal watch`.
  **(9), found the moment (7) started returning data (01:25Z):** every live dispatch run reads
  *finished* in the watch. `marshal status` reports `dispatch_completion_verdict: live` for a
  running session (the real vocabulary is `live | completed | failed | stopped_externally`),
  and `cli/watch.py::_snapshot_dispatch` treats any verdict outside its own invented set
  `{"", "None", "pending", "in-progress"}` as terminal — its tests use `"passed"`/`"pending"`,
  strings the supervisor never emits. → CAP-260 / Story 51.13 (hand-driven, same night).
- **2026-07-25** — three loop-policy actions adopted from the pyforge-atlas
  retro: the independent review pass made standing, not self-flagged; a
  deferral repeated in a second wave promoted to contract level; story size
  capped and keystones split at authoring time.
- **2026-07-17/18** — atlas proven: a full system shipped unattended-with-gates.
- **2026-07-23** — Dream retro-seeded; execution doctrine affirmed (one owner,
  skills as the unit of execution, the harness as the unit of governance,
  deliberately not itself a skill).
- **2026-07-23 (later)** — concurrent-loop isolation shipped as
  [[regenerable-factory]] Wave 0.
- **2026-07-24** — `spec-pyforge-marshal` backfilled, binding `.bmad-loop/**`
  into governance.
- **2026-07-31** — five open questions ruled on in one sitting; sequencing
  resolved as *sequence on verdicts, never author them*. Same day, an audit
  found four factual errors written into this Dream's frontier section by a
  prior pass — the lesson recorded then and worth repeating now: a premise
  handed to an agent is not evidence.
- **2026-08-01** — durable-runs, fidelity-enforcement, and one-front-door
  decomposed into FR-61..65 / AD-46..50; PRD now FR-1..65, architecture now
  AD-1..50, epics now 6 epics / 50 stories.
- **2026-08-02** — dream consolidation: agent-portability, durable-runs,
  fidelity-enforcement, one-front-door, and pr-lifecycle archived as absorbed
  (their vision already lives in the FRs above); genesis-installer kept
  separate on purpose; fleet-chain-completeness moved in from Herald as a
  real, unbuilt frontier item. Story 2.1 found missing a resolved
  architecture decision (F-3/AD-26) in its own acceptance criteria — fixed
  the same pass. Marshal's chain re-verified end to end: all 65 FRs trace to
  a story both directions, 50/50 unique story ids, zero dangling dependencies.
- **2026-08-02 (second pass)** — factory-console archived as absorbed
  (dream-level only, `spec-factory-console` stays live for its own unbuilt
  frontier). herald-pitch (Herald's) similarly folded there. pyforge-testing-charter
  archived as absorbed — `spec-pyforge-testing-charter` stays live: 2 of its 5
  capabilities (correct dashboard TEA signal, real per-station test
  architecture) already shipped this session; the shared `pyforge-testing-kit`
  package and a CI coverage gate remain real, unbuilt, undecomposed work.
  fleet-chain-completeness's own dream file (this session's first pass had
  moved it in from Herald and given it a Spec) archived the same way —
  `spec-fleet-chain-completeness` stays live, undecomposed. All four of this
  second pass keep their Specs untouched; only the top-level Dream files
  consolidated.
- **2026-08-02 (third pass, explicit user override)** — the "genesis-installer
  kept separate on purpose" call from the pass above is **reversed for
  brief/PRD/architecture/Spec**: those four are now folded into this station's
  own single chain (§ Kept separate on purpose, above, revised). Only the
  installer's epics (`epics-genesis-installer.md`) stay separate, unchanged.
  Architecture gains AD-51..AD-65 (genesis-installer's former AD-01..AD-15);
  the Spec gains CAP-10..CAP-18 (former CAP-1..CAP-9); the PRD gains a
  Satellite section carrying genesis-installer's own FR1..FR62 (no dash,
  never renumbered into this PRD's own FR-1..FR-65). Two contradictions
  surfaced by the fold are flagged, not resolved, in the merged Spec's
  Constraints: the CLI framework (Marshal's shipped `argparse` vs
  genesis-installer's designed-but-unbuilt `typer`+`rich`), and a `check`
  verb collision (`marshal check`/FR-65 routes to `scripts/detectors.py`;
  genesis-installer's `genesis check`/CAP-13 re-implements a generic subset
  of `bmad_drift_check.py` for a different, external-repo question) — both
  feed the pre-existing Open Question 17 (installer verb mapping, still
  undecided). The four original standalone documents survive at
  `archive/_bmad-output/projects/pyforge-marshal/planning-artifacts/`.
- **2026-09-02** — landing-to-ledger leftover: promote-on-operator-`main`
  after `gh pr merge` (41.3 / 41.4 / 42.1). Bound as CAP-5 on
  [[sprint-status-auto-promote]]; land must publish the twin from an
  isolated worktree onto `origin/<base>` and never commit on the shared
  checkout.
- **2026-08-21** — **AD-61 corrected: a real, live defect in the never-write
  guard.** Story 10.7's own implementation work found that `docs/dreams/*.md`
  and `**/planning-artifacts/**` are `never_write` patterns while the
  extraction manifest also declares `dreams-readme`/`specs-readme` as
  artifacts `init`/`adopt` must write to those same locations — an exception
  `extraction-manifest.md`'s own rationale table always named, but AD-61's
  binding text never carried a mechanism to express. Confirmed live:
  `marshal seed init` refuses unconditionally on its first write (100%
  reproduction), and the already-merged `marshal seed adopt --apply` (Story
  10.6) fails identically against any target repo missing either file — a
  shipped defect, not just a blocker on unmerged work. AD-61 corrected to
  require subtracting manifest-declared writable paths (filtered by
  `applies_to`) from the guard set at construction, legacy paths still
  winning per AD-59. Fix scoped as its own story, 10.8 — not folded into
  10.7, since it touches already-merged code. 10.7's preserved
  implementation resumes unchanged once 10.8 lands.

## 2026-09-16 — One-chain fold (CAP-8 pilot)

Every previously standalone marshal Dream is now a dated section below (or already was, from 2026-08-02 / 2026-08-08 / 2026-09-16 folds). The station Dream stays `specified`; its Spec is `ready`.

## 2026-09-16 — Agent tool surface — every craft reachable through one governed API (folded from agent-tool-surface)

# Agent tool surface — the factory, callable

## The Dream

**Every capability the factory has is reachable by an agent through one
governed, typed surface** — not a pile of bespoke integrations, and not a set of
powers only a human at a shell can invoke. A Smith should be able to ask for a
recipe's vulnerabilities, a feedstock's health, or a project's dependency
closure the same way it asks for anything else: a named tool, a typed argument,
a structured answer.

This is Marshal's reach, not Mason's or Atlas's. The *tools* belong to the
crafts — 21 recipe-authoring, 21 atlas-intelligence, 2 project-scanning, 2
infrastructure — but **the surface belongs to the operating model**: it is how
any agent reaches any craft, which is the same concern as
[[agent-portability]] ("runs on whichever agent") viewed from the other side.
Splitting it by craft would leave the surface itself ownerless, which is exactly
how it went unnoticed for so long.

## What exists

- **`.claude/tools/conda_forge_server.py`** — the legacy FastMCP server, **46
  tools** over stdio, each a thin subprocess wrapper over the Tier-1 scripts so
  the CLI and the tool surface can never diverge.
- **`pyforge-atlas`'s own 11-tool FastMCP server** — additive, not a
  replacement.
- **`pyforge-marshal`'s own 7-tool FastMCP server** (`pyforge/marshal/mcp/server.py`,
  console-script `marshal-mcp`, Story 18.1) — same atlas pattern, closing the
  practice-owner's own zero-coverage gap named below. The factory now runs
  **three** servers.
- Registration is **manual**, in `~/.claude.json` under
  `mcpServers.conda_forge_server`, with machine-absolute paths into
  `.pixi/envs/local-recipes/`. There is deliberately no `.mcp.json` in the repo.

## Coverage — measured 2026-07-28, updated 2026-09-12

The Dream's headline is *"every capability the factory has is reachable."* Measured
against the eleven realized Dreams, it originally held for **two stations of six**;
Story 18.1 (marshal's own 7-tool server, landed since) brings current coverage to
**three stations of six**:

| Station | Realized capability | On the governed surface |
|---|---|---|
| mason | packaging-factory · fleet-stewardship | ✅ 21 tools |
| atlas | pyforge-atlas | ✅ 21 tools |
| marshal | agent-tool-surface · factory-console · pyforge-marshal · regenerable-factory | ✅ 7 tools (Story 18.1: `marshal_status`/`marshal_check`/`marshal_homes`/`marshal_preflight`/`marshal_upstream`/`marshal_refresh`/`list_marshal_tools`) |
| warden | pyforge-warden | ⚠️ 2 scanning tools — `warden scan` itself is CLI-only |
| herald | design-code-bridge · modernist-identity | ❌ 0 — the bridge runs on an **external** MCP the factory does not govern |
| steward | enterprise-airgap | ❌ 0 |

**Marshal, which owns this practice, had none of its own capabilities on it as of the
original 2026-07-28 measurement.** That was the sharpest evidence for the
reclassification to `type: practice` the same day: a surface at 2-of-6 coverage was not
a finished thing that shipped, it was a standing concern that is tended — and Story
18.1 landing marshal's own tools since is exactly that tending in action, not a
one-time fix. herald and steward remain at zero; the 46 + 21 + 7 tools are real,
*"every capability"* is still not yet true.

Herald's case is the most interesting: `design-code-bridge` is **realized** and works —
through `claude-design`, an MCP registered outside the repo. So the capability is
reachable by an agent but not through *one governed* surface, which is the half of the
promise that fails silently.

## Enforcement — who ensures no drift

These three Marshal practices — this one, [[agent-portability]] and
[[agentic-sdlc-autonomy]] — are **cross-cutting**: owned by one station, binding on all
eight. Every other gate in the repo is vertical (each station's suite checks its own
code). Nothing checked horizontally, which is why the coverage table above went
unmeasured until now.

The model, using the Charter's existing split of *ownership* from *verdict*
(§5: "the hand that builds is never the gate that judges"):

1. **Marshal detects** — the horizontal checks live in Marshal's own detectors, rolled up
   **by owner**, exactly as `dream_chain_check.py` already does.
2. **Each station remediates its own row** — ownership never moves; a finding against
   Herald is Herald's to close.
3. **Doctor holds the verdict on Marshal's row** — the one station that would otherwise
   grade itself. This is Doctor's standing mandate ("continuously monitor … diagnose …
   prescribe"), and it mirrors existing precedent: *the `JFROG_API_KEY` leak was a
   Steward remediation, on a Doctor finding.* Detection and remediation already separate
   across stations there.
4. **The Guildhall gates** — Charter §7 as amended: it refuses to publish a row it cannot
   attribute. Accountability made real, not merely rendered.

**Ratified 2026-07-28** (Charter §6, Realization log). Warden was considered and is **not**
the answer — and the reason is **craft, not scope**. Warden's craft is dependency and
security judgment; process conformance is a different craft, which stays true however
general Warden's ecosystem coverage becomes. Its present Python-only reach is
implementation scope, not mandate. Doctor's mandate already covers conformance drift as a
health signal, and §4 governs: *each works one craft, not all.*

**Governance is kept separate.** The Marshal may not weaken, re-threshold or disable a
check that judges the Marshal. A conformance gate is amendable by its subject only through
the Doctor's verdict — the same rule that stops Mason passing its own build by lowering
Warden's bar. Without that clause the model would be self-grading with extra steps, since
Marshal owns the detectors.

## The frontier

- **Two servers, no governing decision.** The second arrived with
  [[pyforge-atlas]]'s rebuild and is additive by accident rather than by design.
  Whether the surface federates, merges, or stays split is an open architectural
  question that this Dream now owns.
- **A fresh clone has zero tools.** Manual `~/.claude.json` registration means
  the surface does not survive a clone — the sharpest gap between "the factory
  is regenerable" ([[regenerable-factory]]) and what a new machine actually
  gets.
- **Machine-absolute paths** in that registration are the same portability
  defect [[agent-portability]] exists to kill.
- No typed contract test asserts CLI ⇄ tool parity; the thin-wrapper pattern is
  a convention held by review, not by a gate.

## Kinships

[[agent-portability]] (the same concern from the agent's side — Marshal's other
half) · [[regenerable-factory]] (a surface that needs hand-registration is not
yet regenerable) · [[packaging-factory]] (Mason's craft, which this surface
exposes — it carried this Dream as a single bullet until 2026-07-25) ·
[[pyforge-atlas]] (Atlas's craft, and the second server) ·
[[enterprise-airgap]] (the surface must resolve behind a firewall too).

## Realization log

- **2026-07-28** — reclassified `type: dream` → **`practice`**. The surface is never
  finished: every new craft capability adds tools, so it is tended, not shipped. Measured
  coverage the same day put the *"every capability"* claim at **2 stations of 6** — with
  Marshal, the practice's own owner, at zero. Enforcement model recorded (Marshal detects ·
  stations remediate · Doctor judges Marshal's row · the Guildhall gates, per the Charter §7
  amendment). The three cross-cutting Marshal practices had no horizontal check of any kind
  until this date; every gate in the repo was vertical, which is exactly how a 2-of-6
  surface went unnoticed inside a Dream marked `realized`.

- **2026-07-25** — Dream authored, closing the last unowned part of the factory.
  The FastMCP surface was Part 3 of the `local-recipes` rebuild spec (9
  features) and had **no Dream at all** — it survived only as one bullet inside
  [[packaging-factory]]. Found while decomposing `local-recipes`, the one BMAD
  p

*(truncated in fold; original file remains archived)*


## 2026-09-16 — The Agentic SDLC — four views of autonomy, one governed factory (folded from agentic-sdlc-autonomy)

# The Agentic SDLC — redefining autonomy in software engineering

## The Dream

Move the industry conversation (and our own practice) beyond "AI-assisted
coding" to the **Agentic SDLC**: agents that plan, execute, and govern software
creation while the human governs *intent*. "Autonomy" is overloaded; the dream
is to make it precise through **four views** — and to run a factory that
synthesizes all four:

1. **Taxonomy** (governance): L1–L5 levels; L3 "Context Gates" as the production
   ceiling — machine-readable boundaries, human escalation.
2. **Implementation** (process): agents mapped to pipeline stages; automated
   verification pipelines as the answer to Verification Debt; privilege drift
   contained.
3. **Architectural** (control flow): deterministic Workflows where determinism
   wins; dynamic Agents (BMad-Method + module ecosystem) where judgment is
   needed.
4. **Environmental** (workspace): from API-bounded surfaces to native terminals
   with conda-forge/pixi — capability bounded by sandbox and policy.

## What is real (the factory as living proof)

- L3 governance in production: bmad-loop's graduated gates + CRITICAL
  escalation ([[pyforge-marshal]]); Warden's never-false-green verdicts
  ([[pyforge-warden]]); per-story `mode:` fields; live Context-Gate evidence
  (the 2026-07-23 permission-boundary escalation).
- The Workflows-vs-Agents split applied deliberately (the bridge's
  deterministic no-LLM constraint vs. persona agents).
- Both ACI extremes governed: MCP-bounded Design surface + sandboxed native
  terminal.
- **The deck**: `presentations/agentic-sdlc/` (45 slides, PR #50) — the family's
  origin engine and this Dream's chapter on method.

## The frontier

- Fold the four-views white paper into the deck as a new act — all source
  material is staged in `docs/intake/agentic-sdlc/` (white paper, infographic +
  masterclass HTMLs, updated Marp draft) awaiting the refresh.
- **Formal L-level adoption**: label story modes L1–L5; publish the mapping.
- Fleet-level resource budgets; privilege-drift management ([[pyforge-doctor]]).

## Realization log

- **2026-07-11** — the agentic-sdlc deck shipped (PR #50).
- **2026-07-23** — the four-views white paper arrived; Dream retro-seeded with
  the factory's own L3 evidence.

- **2026-09-09 (fleet readiness pass — operator-approved batch)** — Dream status kept `specified`;
  **`spec-agentic-sdlc-autonomy` moves `pitched` → `ready`.** `pitched` is Dream vocabulary and was
  the fleet's only instance in a Spec's `status:` field, outside the sequence `AGENTS.md:118`
  sanctions (`draft → ready → in-progress → shipped`). Its effect was invisible: `pitched` is not in
  `OPEN_SPEC_STATUSES` (`board.py:77`), so `board.py:716` skipped the Spec before the
  `DEFERRED_SPECS` check ever ran — the carefully-worded exemption at `board.py:88-90` had never done
  anything. **The `DEFERRED_SPECS` entry stays**; `ready` makes it live and honest: a settled
  standing position with nothing to decompose, exempted on the record. Fleet ruling recorded in the
  same batch: `pitched` is not a Spec status. Batch:
  `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`.

## 2026-09-16 — A backlog authored before the code existed is a plan for a different codebase (folded from artifact-chain-reconciliation)

# A backlog authored before the code existed is a plan for a different codebase

> The semantic sibling of [[surface-drift-reconciliation]]. That Dream made the
> *file-level* reconciliation claim honest — a memlog speaks only for the paths
> it names. This one makes the *meaning-level* claim honest: a story's premise,
> a done-claim's acceptance criteria, a test suite's coverage of an epic. The
> detectors police hashes and counts; nothing polices whether the plan is still
> true. Kin: [[regenerable-factory]] (every surface regenerable from its chain),
> [[fidelity-enforcement]] (every tier boundary gated), [[bmad-output-hygiene]]
> (what is real vs. debris, mapped once — this Dream is that audit's
> forward-looking form).

## The Dream

The fleet paused at **267/335 stories, 53/64 epics** (2026-08-10 — since
resolved; see Realization log), by choice. Behind those
267 stories stands the full dream-to-code chain — Dream, Deck, Spec, Research,
Brief, PRD, UX, Architecture, Context, Epics, Sprint, TEA, Gates, Code, Tested,
Retro, Status — and almost all of it was authored **before most of that code
existed**. The 68 stories that remain were scoped against a codebase that has
since absorbed 267 landings, 13 retro-driven skill revisions, one fleet-wide
naming convention, and a per-station architecture consolidation. Some of those
68 are already implemented under another story's flag. Some contradict
invariants that hardened after they were written. Some are still exactly right.
**Nobody has measured which.**

The mechanical layer is policed: six detectors prove files match contracts,
ledgers match feeds, surfaces match baselines. The semantic layer is not. No
instrument asks *does this story's premise still hold?* or *do the acceptance
criteria of that `done` claim actually appear in code?* or *which ACs have no
covering test?* Those are judgment questions, and they have been answered so
far by the only witness available — the artifacts' own self-assessment, which
is precisely the witness that cannot be trusted. The ledger reports intent; only
the code reports fact.

The dream: **stop building, audit the chain independently against the code,
correct whichever side is wrong, and only then decompose further.** The scope
is all of PyForge — every Dream in `docs/dreams/`, every planning artifact,
every chain stage, all code — and the correction runs both ways: a stale
artifact is rebuilt against the code, and code that diverged from a
still-valid contract is corrected against the artifact. The artifacts that
drive implementation must be at least as true as the implementation they
drove. A factory that regenerates code from its chain is only as good as the
chain — and right now the chain's truth is presumed, not measured. Decomposing
on top of a stale chain compounds the drift at the exact moment it is cheapest
to correct.

## What is real (measured 2026-08-10, on `main` at `dfeb565231`)

- **267/335 stories · 53/64 epics · 0/8 stations running** — the 2026-08-10
  starting snapshot this audit measured against, since fully resolved (the
  audit itself closed the gap; see Realization log for the final tally)
  (`fleet-picture`; liveness verified against `ps`, not `engine.pid`). All eight loop homes
  fast-forwarded to `main`; zero unlanded loop merges; zero open PRs.
- **The remaining 68:** marshal 35 (+1 blocked — story 8-5, not 10-1/FR-157 as
  a prior session's note suggested), mason 28, steward 4. Steward's stop is a
  deliberate epic-boundary pause at Epic 8, 1/5. These 68 are the artifacts
  that will drive implementation the moment any station re-spins — the
  highest-leverage audit target in the repo.
- **Five stations read complete** (atlas 46, doctor 28, herald 47, scribe 9,
  warden 31) — a claim this Dream treats as *ledger intent*, to be sampled
  against code, not inherited.
- **Known mechanical debt, already partitioned into three jobs:** 51
  `[drift-presumed]` warns — atlas 24 (name-then-stamp), marshal 26 (a
  *decision* about generated artifacts, still open), mason 1. Plus ~30 dangling
  commits from six orphaned runs, presumed valueless but unverified.
- **Four decomposition chains are queued** (order decided: atlas → herald →
  doctor → steward) — queued *before* the pause-and-reconcile decision existed.
- **The precedents that shape the method are all in-house:**
  - warden lost 13/31 story specs to Tier-3 teardown and recovered 31/31 from
    session transcripts; atlas could not, and carries 30/32 contract-specs —
    the two ends of the artifact-durability spectrum this audit must respect.
  - "feed reports intent, run reports fact" — the loop marks `done` at DEV
    completion, before review; the ledger is structurally optimistic.
  - Blind parallel adversarial review (two hunters, no shared context) is
    validated at N=6 in this repo and is strictly stronger than sequential
    persona role-play over the same content.
- **No semantic detector exists, and none is possible in the mechanical sense.**
  `bmad-drift-check` proves counts and pins; `spec_surface_check` proves files
  against contract hashes. Premise validity and AC truth are judgment calls —
  which is exactly why they have never been checked, and why an independent
  audit (not another script) is the instrument.

## What it looks like when real

- **Every remaining story carries a cited verdict:** `STILL-VALID` /
  `ALREADY-DONE` / `CONTRADICTED` / `NEEDS-RESPEC` / `DROP`. No verdict without
  evidence — a `file:line` citation or a command's output. A `CONTRADICTED`
  claim with no citation is rejected in review.
- **The audit's output is a traceability matrix, not prose**, landed in an
  existing artifact class (the gate report, via
  `bmad-check-implementation-readiness`) — one row per claim:
  *Claim (FR / story / AC) · Ledger status · Code reality (citation) · Verdict ·
  Action → owning skill*. A matrix cannot hide a half-audited epic the way a
  summary can; this is "emit the full contract or nothing" applied to auditing.
- **The TEA column is refreshed by measurement:** per epic, an AC → covering-test
  map. An AC with no test is a distinct *coverage-debt* row, not a drift
  verdict — visible, non-gating, dispositioned by the operator.
- **Done-claims are sampled, not trusted:** N stories per epic on every station
  — including the five that read complete — their ACs checked in code.
- **Fixes land only through the owning skills:** `bmad-correct-course` for
  epic/story surgery, `bmad-sprint-planning` → `sprint-ledger-sync` for the
  ledger, `bmad-document-project` / `bmad-generate-project-context` for
  architecture and context re-grounding, `dashboard-gen` for the board. Every
  spec touched gets a memlog entry naming its paths, then a scoped stamp —
  never a stamp without the why.
- **Every landing is preceded by blind, lens-diverse parallel review** — one
  hunter structural/architectural, one coverage/edge-case, neither shown the
  artifacts' self-assessment before the diff.
- **The five complete stations are closed out as a verified record:** Spec
  status advanced to `shipped` where earned, retro promises confirmed landed,
  story-spec sets complete under `planning-artifacts/specs/`, board rows
  accurate, baselines re-stamped.
- **Decomposition extends only a reconciled chain.** The four queued chains run
  after their station's audit lands, with convergence checked before any new FR
  is minted — most new capability in a mature chain is already covered.
- **At the end, re-spin is an operator decision made on artifacts that are
  true** — and the projected 68 is a number that can finally be believed.

## The shape of the answer

Five phases, in order. The build stays down throughout; a station's audit
landing gates *that station's* further work, not the fleet's.

0. **Freeze + mechanical debt.** Full detector sweep for the baseline
   inventory. Close the 51 warns as the three jobs they are — atlas 24
   name-then-stamp, mason 1, marshal 26 pending the o

*(truncated in fold; original file remains archived)*


## Realization log

- **2026-08-10** — Seeded at operator request, at the 267/335 pause, immediately
  after a landing pass confirmed zero in-flight work fleet-wide — the cheapest
  moment this audit will ever have. The plan was drafted in-session; an
  external model's (Gemini) reconciliation advice was weighed against it — three
  constraints adopted (strict traceability matrices, citation enforcement, an
  explicit AC→test coverage lens), three rejected as unsafe for this repo
  (bundled context document, freehand artifact rewrites, model-side mechanical
  drift detection), and its sequential persona passes replaced by the
  repo-validated blind parallel form. The queued decomposition-first ordering
  was deliberately inverted: verify the chain, then extend it.
- **2026-08-10 (later)** — Specified. The three operator decisions landed
  (marshal's 26: regenerate + verify + stamp; serial execution; steward →
  mason → marshal), and mid-spec the operator elevated the completed stations
  from "lighter close-out" to **first-class audit scope** — a critical part
  and point of the audit, since three of the four queued decomposition chains
  extend completed stations. Two further directions in the same session
  widened the contract: the audit spans **all of PyForge** — all 61 Dreams,
  all artifacts, all stages, all code (the non-station inventory is CAP-8) —
  with completed stations queued after steward → mason → marshal; and
  **rebuilding/correcting specs, code, decisions, and artifacts is
  pre-authorized**, two-sided (stale artifact → rebuild from code; divergent
  code → correct against contract), nothing silent. Spec:
  `pyforge-marshal/planning-artifacts/specs/spec-artifact-chain-reconciliation/`
  at `ready`, CAP-1..CAP-8, with the completed-station audit as CAP-3.
- **2026-08-10 (close)** — Realized. Phases 0–4 executed in one autonomous session
  (PRs #399–#406): 51 warns to zero by measurement, 68 backlog verdicts + 21+21+4
  done-claim samples all cited, 19 story-spec recoveries, 195 citation re-issues,
  61/61 Dreams dispositioned, one decomposition landed and two held conservatively
  when the blind verifier and the consent classifier said hold. Every phase's first
  draft was refuted in part by its own blind review — the method's point, proven
  eight times. Spec `shipped`; the resume decisions are packaged in
  `resume-package-2026-08-10.md`.

- **2026-09-09 (fleet readiness pass — operator-approved batch)** — Status kept `realized` (PRs
  #399–#406 merged); **both open questions closed.**
  **OQ-1 — complete-station demotion precedent:** when sampling fails an AC on a shipped station the
  result is a **coverage-debt row** in `planning-artifacts/deferred-work-ledger.md` — **never a
  ledger reopen.** Reopening a `done` row re-arms the dispatch picker on a story whose code exists,
  which is the respawn trap auto-memory already records
  (`feedback_merged_story_with_backlog_ledger_row_respawns_forever`). The first occurrence never
  arrived: this Dream's own 2026-08-10 close records 21+21+4 done-claim samples all cited, zero
  demotions — so the ruling is precedent-setting, not remedial.
  **OQ-2 — standing practice: STALE.** It is answered by [[chain-currency-sweep]] and that Spec's own
  `DEFERRED_SPECS` entry (`board.py:100-106`), which describes exactly the recurring-runbook form
  this question asked for. The 2026-08-10 one-shot priced itself on 61 Dreams / 335 stories; the
  estate now holds 131 Dream files and atlas alone carries 137 stories — outgrown ~2×.
  Housekeeping noted for doctor: this Spec's `DEFERRED_SPECS` entry is **inert** (`shipped` ∉
  `OPEN_SPEC_STATUSES`) and is deleted in doctor's own pass. Batch:
  `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`.

## 2026-09-16 — PyForge's artifacts, patterns, and station code stay aligned to the installed BMAD era — 6.12 today, v7-ready tomorrow (folded from bmad-611-era-alignment)

# PyForge's artifacts, patterns, and station code stay aligned to the installed BMAD era

## The Dream

Upgrading the BMAD core and suite (done 2026-08-21/22: core 6.11.0, bmad-loop
0.11.0, PRs #606/#607) makes the stack *run* current — it does not make the
fleet *aligned*. Every station was built against pre-6.11 / bmad-loop-0.9-era
conventions, and the residue is concrete: retired skill names baked into
planning artifacts and seed templates, spec folders whose memlogs the 6.11
tooling refuses to touch, living factory docs whose reconciler skill no longer
exists, and marshal surfaces that cannot see or govern what bmad-loop 0.10/0.11
added. The dream: after any BMAD-era shift, one owned effort brings artifacts,
locations, patterns, and station code back into alignment — and the alignment
holds, guarded by tests, until the next era.

## Grounding — what was verified (2026-08-22, two research passes + local inventory)

**Local misalignment (all verified, none assumed):**

1. **bmad-loop's three repo-installed skills are stale vs the 0.11 package**
   (`bmad-loop-setup` 217 diff lines, `-resolve` 134, `-sweep` 7, against
   `bmad_loop/data/skills/`; `init` deliberately refuses to overwrite without
   `--force-skills`).
2. **Marshal's seed template ships a retired name to every NEW station** —
   `seed/templates/files/dream-first-workflow.md.j2` says "`bmad-loop` /
   `bmad-dev-auto`".
3. **6 station planning artifacts name retired skills** in dispatch-instruction
   text: epics.md of warden/steward/atlas/doctor/marshal + marshal's PRD.md.
   Plus one reference in AGENTS.md and three auto-memory entries.
4. **22 spec folders carry pre-6.11 memlog debt**: 14 have `SPEC.md` with no
   `.memlog.md` at all; 8 more have memlogs without frontmatter, which 6.11's
   `memlog.py` refuses outright (hit live 4× during the upgrade landing —
   hand-appends were the workaround). Any future `bmad-spec` update against
   these folders fails or violates the derive discipline. All 8 stations affected.
5. **Living factory docs lost their reconciler**: `bmad-document-project` /
   `bmad-generate-project-context` are retired; `architecture-bmad-infra.md`
   is a 6.10-era description of a now-6.11 infra (pre-render, pre-TOML, old
   names; last re-grounded 2026-07-25), and the 8 per-station
   `project-context.md` rulebooks — still consumed by build-auto's
   persistent_facts, proven by the 2026-08-22 canary — have no regenerator.
6. **Marshal's policy layer knows none of the bmad-loop 0.10/0.11 knobs**
   (`review.on_timeout`, `[review] on_status_contradiction`,
   `limits.dev_contract_nudge`, `[operator] enabled`,
   `[verify] stream_capture_kb`) — stock defaults apply, but the AD-16
   defaults→project→flags chain cannot govern them.
7. **Marshal's status vocabulary predates 0.11**: `awaiting-operator` phase,
   `confirm` verb, `preserve_ref`, `sweeps_refused` are invisible to
   `marshal status` / fleet-picture (marshal DW-BL011-1 covers only the
   stall-check mislabel). `preserve_ref` is the fleet's standing
   escalation-preservation policy, now upstream-native and unadopted.

**Upstream v7 trajectory (researched 2026-08-22; cited in the spec's companion):**

- **The only COMMITTED v7 breakage is the 20-shim removal** ("removal rides
  the v7 cut — never a 6.x minor"; shims are now opt-out on fresh installs,
  keep-by-default on updates, identified by `metadata.lifecycle: shim`).
- **The v7 planning lane is the `bmad-ticket` tree** (`ticket-master` branch,
  active through 2026-08-19): `.bmad-obeya/` work store, epic folders +
  `ticket.md`, `KEY-n-slug.md` stories, status the only stored fact, derived
  board/frontier verbs; `bmad-create-epics-and-stories` becomes a shim;
  **`sprint-status.yaml` survives only for in-flight v6 stories**;
  **`stories.yaml` is being removed** before this repo ever adopted it.
- **The config.yaml→TOML cutover is probable-at-v7 but unscheduled** — nothing
  on main moves it yet; when it lands, the multi-project planning-artifacts
  symlink mechanism dies (soft landing available: the repo-custom six-layer
  `resolve_config.py` already speaks TOML layers 5/6).
- **bmad-loop already bridges the deferred-work contract**:
  `Engine._harvest_spec_deferrals` (since 0.9.1) harvests spec-frontmatter
  `deferred:` lists into the ledger its sweep reads — so the frontmatter gap
  bites only HAND-DRIVEN build-auto runs (exactly the 2026-08-22 canary,
  whose deferred item needed a manual relay to doctor's DW ledger).
- No v7 date, milestone, or migration doc exists; `next` is a 6.11.1 patch
  line; Paige's replacement, the "explain this system" capability, and
  bmad-ux/WDS absorption all have zero implementation signal.

### The 6.12.0 era shift — verified 2026-09-05 (tagged tree + CHANGELOG + local diff, not the release page)

BMAD-METHOD **6.12.0** shipped 2026-09-03 (GitHub release 2026-09-04). The
`_bmad/` install is still 6.11.0 — the apply is steward Epic 14's
(`steward upgrade`, operator-gated) — but the era of record has moved, and
the residue this Dream owns is already visible:

1. **Shim roster: still 20, one seat swapped.** `bmad-checkpoint-preview` is
   a new shim forwarding to the new `bmad-walkthrough` (`CK` → `WT`);
   `bmad-generate-project-context` (a 6.11 shim) ships as neither a shim nor
   a `removals.txt` entry, so an update leaves its 6.11 directory orphaned in
   `.claude/skills/`. Shims are now **opt-in on fresh installs** (`--shims`);
   existing installs keep them by default. CAP-1's guard list and the two
   living docs naming `bmad-checkpoint-preview` (`architecture-bmad-infra.md`,
   `development-guide.md`) are behind.
2. **`persistent_facts` ships empty** (`bmad-build-auto/customize.toml`: the
   `file:**/project-context.md` glob is gone). The eight station
   `project-context.md` rulebooks — CAP-7's premise, "still consumed by
   build-auto" — lose their only runtime consumer. The 2026-09-05 upgrade
   planning session decided **D1: accept the empty default**; the AGENTS.md
   `bmad:context` block is the project-context surface. Consumers to
   migrate: doctor `sources/factory.py` (+ its `pin-behind (context)` row),
   `scripts/fleet_scan.py`, `scripts/bmad_drift_check.py`, and SYNC-RUNBOOK's
   living-doc cadence.
3. **The AGENTS.md HOLD is moot.** The managed `bmad:context` block was set up
   2026-09-04 (verified against `bd37dfd607`), and 6.12's
   `bmad-project-context` gains an `adopt` intent with a
   retain/rewrite/relocate/delete ledger — the rework this Dream was waiting
   out has landed.
4. **`llms.txt` / `llms-full.txt` are no longer published.** CLAUDE.md's
   "live source" pointer is dead; `.claude/docs/bmad-method-llms-full.txt`
   (generated 2026-08-17) is the last snapshot there will be.
5. **`{diff_output}` → `{diff_file}`** in review-layer overrides: no
   `_bmad/custom/` override and no bmad-loop reference uses it — no action.
6. **Build-auto spec-template drift fired** (a horizon-watch trigger): the
   "Block If" tier is gone (two tiers, Always/Never), the review log records
   a verdict + evidence per finding, and `followup_review_recommended` no
   longer HALTs on `false`. The frontmatter keys our readers consume
   (`status`, `deferred`, "blocking condition") are unchanged, and
   `bmad-spec`'s template and `memlog.py` are byte-identical at 6.12 — marshal
   `core/status.py`, `scripts/deferred_work_intake.py` and CAP-3 need nothing.
7. **Not shipped in 6.12:** the bmad-ticket tree (no `ticket` / `.bmad-obeya`
   path in the tag) and the config.yaml→TOML cutover (the installer still
   generates `_bmad/{bmm,core}/config.yaml`; no cutover language in the
   CHANGELOG). Both watches stay watches.
8. **bmad-loop 0.11.1** (2026-08-24) is installed; the repo copy of
   `bmad-loop-setup` is one line behind (`module_version: 0.11.0`) — CAP-2's
   recurrence. 0.11.1 adds no policy key (CAP-4 holds); it adds a git ≥ 2.34
   floor (`git.version` in `validate`), a hard-stop mode on
   `stop-request.js

*(truncated in fold; original file remains archived)*


## Realization log

- **2026-08-22** — Dream, Spec and decomposition landed in one commit (`2dc63365fb`):
  `spec-bmad-611-era-alignment` under pyforge-marshal (7 CAPs, 2 companions, status `ready`),
  decomposed as marshal Epic 25 (7 independent stories).
- **2026-08-24** — Epic 25 done, 7/7: 25.1 guard + sweep, 25.2 skill refresh, 25.3 memlog
  migration, 25.4 policy knobs, 25.5 status vocabulary (PR #612), 25.6 deferral intake
  (PR #721), 25.7 living docs + SYNC-RUNBOOK owner (PR #722). Status → `realized` (recorded
  2026-09-05; the flip was owed at the time).
- **2026-09-05** — BMAD-METHOD 6.12.0 re-check (released 2026-09-04): § *The 6.12.0 era shift*
  added; the Spec's memlog gained CAP-8..11 (6.12 retired-ID roster, project-context surface
  follows D1, documentation pointers, bmad-loop 0.11.1 parity) and lifted the AGENTS.md HOLD;
  `horizon-watches.md` re-checked row by row; `alignment-inventory.md` gained the 6.12 table.
  Next: decomposition as a new marshal epic, and the apply itself (steward Epic 14).

## 2026-09-16 — A story's orchestrator-recorded baseline can never drift out from under its own worktree (folded from bmad-loop-baseline-drift)

# A story's orchestrator-recorded baseline can never drift out from under its own worktree

## The Dream

`bmad-loop` mounts each story in its own isolated git worktree and records `task.baseline_commit`
once, when that worktree opens — engine.py's own comment says it is meant to stay "fixed across
the whole dev retry loop." In practice it can silently drift to a later commit while a dev session
is still running, so a story that does completely real, reviewed, honest work gets permanently
rejected by its own verify gate (`spec baseline ... does not match orchestrator-recorded
baseline ...`) and deferred — with the run then dispatching the *next* story rather than pausing
or escalating. The dream is a fix (or, short of that, a durable containment) that makes this class
of failure impossible, or at minimum loud and self-healing, instead of silently burning hours of
real compute per occurrence.

## What it looks like when real

- `task.baseline_commit`, once captured for a story's worktree, cannot be overwritten by anything
  outside that story's own dev-retry loop — whatever process/path currently mutates it out from
  under an in-flight sibling story either stops touching tasks it doesn't own, or explicitly
  rebases the affected worktree onto the new baseline (and re-stamps the spec's `baseline_revision`
  to match) rather than leaving the two to silently diverge.
- On a genuine, unavoidable divergence (e.g. an operator's own out-of-band recovery advancing the
  shared branch — exactly what PR #482 did to 9.6), the verify gate treats an *ancestor* baseline
  the same way `_verify_shared_gates`'s existing `allow_ancestor_baseline` carve-out already does
  for the re-arm path (verify.py:1220-1235) — landing the honest work instead of discarding it.
- A defer for this specific reason is loud, not silent: it should escalate/pause rather than let
  the dispatcher roll on to the next story, so `fleet-picture`'s ATTENTION block (or an equivalent)
  actually names it instead of the operator having to notice via a dashboard-accuracy audit, the
  way this Dream itself was discovered (2026-08-14).
- The existing manual recovery path (this repo's own `attempt-preserve/*` branch / `failed/*/
  changes.patch` salvage, performed by hand three times in one session — 8.1-9.5, then 9.6, then
  mason 3.6/3.7/3.9) becomes unnecessary for this specific failure mode, or at minimum scriptable
  instead of a multi-step manual git-archaeology procedure repeated per occurrence.

## What is real

- **`scm.keep_failed`'s auto-preserve safety net** (this repo's existing operational reliance) —
  every deferred story's real commits survive as an `attempt-preserve/<run>-<hash>` branch, or a
  raw `failed/<story>/changes.patch` when no such branch exists. This is what made every recovery
  this session possible; it is a safety net for the symptom, not a fix for the cause.
- **`runs.py`'s operator-driven `resolve`/re-arm path already knows this exact hazard** —
  `_resolve_escalation` (runs.py:872-908) explicitly re-stamps BOTH `task.baseline_commit` (from
  `state.project`'s live HEAD) AND the spec's `baseline_revision` together on a human-initiated
  re-drive, with comments naming precisely the failure this Dream is about ("without this, the
  re-driven step-04 would build its review diff... since the ORIGINAL pre-attempt sha, clawing
  back the very resolve-session commits the advance above just blessed"). The automatic retry path
  (`engine.py`'s `_dev_phase`/`_rollback_or_pause`) has no equivalent re-stamp.
- **`_verify_shared_gates`'s `allow_ancestor_baseline` carve-out** (verify.py:1220-1235) already
  treats an ancestor baseline as sound for the deferred-work-bundle re-arm case (#161) — the
  pattern this Dream wants extended to the plain-retry path already exists in the codebase for a
  sibling case.
- **A related, already-acknowledged-as-upstream containment exists**: `story-status-check`
  (pixi.toml, `docs/dreams/...` — "no story reads `done` in a sprint feed without having landed")
  is a DIFFERENT failure mode (dev self-marks done before review converges) with the exact same
  "the real fix belongs upstream in bmad-loop; this is the containment" framing this Dream's
  problem deserves too. `loop-stall-check` is a second precedent — a local detector containing an
  upstream bmad-loop blind spot (a session stalled at an interactive prompt reads healthy) rather
  than waiting for the upstream fix.
- **Two live, independently-confirmed occurrences in one session (2026-08-14)**: marshal's Epic 8/9
  batch (8.1-8.4, 9.1-9.5 — 9 stories, ~8 hours, PR #482) and mason's 3.6/3.7/3.9 (PR #483) both hit
  this exact signature. A THIRD occurrence — marshal 9.6 (PR #484) — happened on the very next story
  after the Epic 8/9 recovery landed, on the same live run, confirming this is not a one-off but a
  live, recurring hazard as long as `loop/pyforge-<slug>`'s tip keeps moving while sibling stories
  sit in-flight (multiple concurrent worker slots, or an out-of-band operator recovery like #482
  itself). Full per-occurrence evidence (journal excerpts, exact commit hashes, code-line citations)
  is recorded in `spec-pyforge-marshal`'s `.memlog.md`.
- **Installed version**: `bmad-loop 0.9.0` (`pixi.toml` pins `>=0.9.0`), source
  `https://github.com/bmad-code-org/bmad-loop`.

## Constraints

- **Cannot be fixed by editing the installed package in place.** `bmad_loop` ships via a
  pixi/conda-forge dependency (git-pinned upstream), not code this repo owns under `src/`; editing
  `.pixi/envs/*/site-packages/bmad_loop/` directly is wiped on the next `pixi install` and, more
  urgently, would be a live edit to a package TWO currently-running loops (marshal, mason) are
  actively importing and executing against mid-run — not something to do without stopping them
  first and confirming with the operator.
- **A local mitigation must not paper over the defer.** Whatever ships here should either make the
  underlying race genuinely impossible, or make the defer immediately loud and recoverable — not
  quietly reduce the manual-recovery burden while leaving the silent-hours-of-burned-compute
  failure mode intact.

## Non-goals

- **Not a rewrite of `bmad-loop`'s concurrency/worktree model.** The dream is the narrow baseline-
  drift bug, not a broader redesign of how the orchestrator manages parallel worker slots against
  one shared target branch.
- **Not retroactive cleanup of past occurrences.** The three known occurrences this session
  (8.1-9.5, 9.6, mason 3.6/3.7/3.9) are already recovered (PRs #482, #483, #484); this Dream is
  about preventing/containing the NEXT one.

## Backlog: what's needed to report this upstream

Per the operator's explicit 2026-08-14 request to track both an in-repo Dream/Spec AND a clear
path to reporting this upstream. Items 1–2 + filing completed 2026-08-23 (Story 20.3):

1. **Confirm repo access** — DONE 2026-08-23. Viewer `rxm7706` has `pull` only on
   `bmad-code-org/bmad-loop` (no push/triage/maintain). Issues enabled; Discussions disabled.
   Filing channel = **GitHub Issue** (not PR, not Discussion).
2. **Check for an existing issue first** — DONE 2026-08-23. Searched `baseline_commit`,
   orchestrator-recorded / mid-flight drift, `intent_gap` / `attempt-preserve` / `keep_failed`.
   No duplicate of mid-flight `task.baseline_commit` overwrite during an in-flight automatic
   retry, nor of intent-gap revert without preserve. Adjacent but distinct:
   [bmad-loop#640](https://github.com/bmad-code-org/bmad-loop/issues/640) (`rearm_escalation`
   advances task baseline without updating the spec's `baseline_revision`) — related shape on
   the *re-arm* path only.
3. **Package the evidence** — DONE 2026-08-23 (filed body includes journal timeline + source
   citations). This Dream's "What is real" section + `spec-pyforge-marshal`'s `.memlog.md`
   remain the in-repo archive.
4. **Minimal repro, if requested** — still open. The three live occurrences are enta

*(truncated in fold; original file remains archived)*


## Realization log

- **2026-08-14** — Dream captured. Surfaced during a dashboard-accuracy audit that found marshal
  story 9.6 showing `done` on the dashboard but `backlog` in the tracked ledger — investigating the
  mismatch uncovered a THIRD live occurrence of the same bug already recovered twice earlier in the
  same session (marshal 8.1-9.5 via PR #482, mason 3.6/3.7/3.9 via PR #483). Root-caused this
  occurrence against `bmad-loop`'s own journal.jsonl and installed source
  (`.pixi/envs/local-recipes/.../site-packages/bmad_loop/`), landed the recovered story (PR #484),
  then captured this Dream per the operator's explicit priority request — Dream + Spec in-repo, plus
  a tracked backlog of what reporting it upstream would require.
- **2026-08-14** — Spec authored (spec-bmad-loop-baseline-drift, pyforge-marshal) by the 2026-08-14
  dream-backlog audit: Marshal-side loud-defer containment + the gated upstream-report track. The
  drafted issue stays unfiled pending repo-access + duplicate-search.
- **2026-08-23** — Story 20.3 gated upstream filing: Gate (1) repo access → issue channel only
  (`pull`, no push; Discussions off); Gate (2) duplicate search → no match (adjacent #640 noted).
  Filed coordinated issue https://github.com/bmad-code-org/bmad-loop/issues/701 (baseline-drift +
  Story 10.1 intent-gap evidence). Registered in
  `_bmad-output/projects/pyforge-marshal/planning-artifacts/upstream-register.json`
  (`baseline-commit-midflight-drift`). No edits to the installed `bmad_loop` package.

- **2026-09-09 (fleet readiness pass — operator-approved batch)** — **`specified` → `realized`.**
  Epic 20 Stories 20.1–20.3 are `done` and neither this Dream nor its Spec recorded it:
  `scripts/bmad_loop_baseline_drift_check.py` + the `baseline-drift-check` pixi task
  (`pixi.toml:932`), the loud `--json` defer surface for fleet-picture, and the gated upstream
  filing (bmad-loop issue #701, `upstream-register.json` `baseline-commit-midflight-drift`). Both
  open questions were answered by the implementation: post-hoc journal-signature match only, and
  report-only — exit 1 plus `--json`. Spec `ready` → `shipped`.
  **Residual carried forward:** the detector scans `~/.bmad-loops/<slug>/.bmad-loop/runs/` only
  (`bmad_loop_baseline_drift_check.py:72,142`) while the live engine is `marshal factory dispatch`,
  whose journals live under `_bmad-output/projects/<slug>/implementation-artifacts/dispatch-runs/`;
  the newest loop-home run in any of the eight homes is 2026-08-22. It exits 0 "OK" on an empty
  observation plane instead of reporting could-not-observe — a false green by the repo's own
  standard (`pixi.toml:1033`). Re-pointed by marshal **Story 33.7**. Batch:
  `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`.

## 2026-09-16 — An intent-gap revert can never discard real work without a recoverable trace (folded from bmad-loop-intent-gap-work-preservation)

# An intent-gap revert can never discard real work without a recoverable trace

## The Dream

When a `bmad-loop` dev session finds an **intent_gap** (a contradiction inside the story's own
`<intent-contract>` that the workflow may not silently patch around), it correctly reverts the
attempt rather than committing broken or contract-violating work — but today that revert leaves
**no recoverable git artifact**: no `attempt-preserve/*` branch, no `failed/*/changes.patch`, a
clean reflog. This is a deliberate asymmetry with the deferred-story path, which already preserves
every attempt via `scm.keep_failed`. The dream is for an intent-gap revert to get the same
preservation guarantee — so a correct, protocol-following halt never also means the honest,
reviewed work it produced becomes unrecoverable through git.

## What it looks like when real

- Before an intent-gap revert discards tracked changes, the attempt's commits (or working-tree
  diff, for an attempt that never committed) are parked exactly the way `_preserve_attempt_commits`
  / `_preserve_attempt_worktree` already do for the deferred-story path (`engine.py`'s
  `_rollback_or_pause`, called via `rollback-auto`) — an `attempt-preserve/*` branch when there are
  real commits, a `failed/<story>/changes.patch` when there aren't.
- The spec's own "Auto Run Result" / escalation text, which already names the exact recommended
  contract fix in detail, ALSO names the preserve ref/patch path directly — so a human or a
  `bmad-loop resolve --restore-patch` re-drive doesn't have to go looking for it.
- Recovering an intent-gap revert never requires session-transcript archaeology (reconstructing a
  diff from an adversarial-review Agent prompt's embedded content, as this Dream's own motivating
  incident required) — that path should exist as a last resort for pre-existing runs, never as the
  first-choice recovery method for a NEW one.

## What is real

- **`scm.keep_failed`'s auto-preserve safety net already exists** for the sibling failure mode
  (a story that times out, or is deferred by the orchestrator) — `attempt-preserve/<run>-<hash>`
  branches and `failed/<story>/changes.patch` files, both used repeatedly this session to recover
  real work (`docs/dreams/bmad-loop-baseline-drift.md`'s three occurrences). The intent-gap path is
  the ONE story-halting flow in this session that did NOT get this treatment.
- **One live, concrete occurrence (2026-08-14)**: marshal Story 10.1 (`Copier engine wrapper — the
  single seam`) implemented `seed/engine/copier.py` in full, passed the whole `pyforge-marshal`
  suite (3646 tests) plus two adversarial reviews, then correctly found and halted on a real
  contradiction in its own `<intent-contract>` (the `never_write` Boundaries rule vs. two
  already-shipped manifest entries FR-74 needs). The revert left the worktree "confirmed clean,
  matching `baseline_revision`" — by design, per the escalation's own text — with nothing to `git
  merge-base --is-ancestor` against and no preserve branch to fetch.
- **Recovery was still possible, but only by accident of a different feature**: the adversarial-
  review Agent-tool prompts (`bmad-review-adversarial-general` / `bmad-review-edge-case-hunter`)
  embed the FULL diff-against-baseline plus the complete content of every new file, so the
  reviewed implementation could be reconstructed byte-identical from the dev session's own Claude
  Code transcript (`~/.claude/projects/**/*.jsonl`) rather than re-implemented from scratch. This
  worked, but it is fragile — it depends on the review step having run at all (an intent-gap found
  during REVIEW, as here, has this; one found earlier, during dev, might not), on locating the
  right session transcript, and on the transcript still existing on disk.
- **The escalation's own text already recommends against re-implementing from scratch** ("The
  reverted implementation in this run's transcript... is a working reference — re-implementing
  from scratch should not be necessary") — i.e. the workflow already KNOWS the work shouldn't be
  thrown away, it just doesn't currently act on that knowledge with a durable artifact.

## Constraints

- **Cannot be fixed by editing the installed package in place**, for the same reason as
  [[bmad-loop-baseline-drift]]: `bmad_loop` ships via a pixi/conda-forge dependency (git-pinned
  upstream), not code this repo owns, and two loops may be actively running against it.
- **Must not weaken the intent-gap halt itself.** The dream is preserving the discarded work, not
  changing when or whether an intent-gap should halt and revert — that protocol (never silently
  patch around a contract contradiction) is correct and should stay exactly as strict.

## Non-goals

- **Not a general "never lose any AI-generated output" system.** Scoped specifically to the
  intent-gap revert path inside `bmad-loop`'s own dev-session lifecycle.
- **Not retroactive recovery tooling.** Story 10.1's own recovery (this session) already happened,
  by transcript reconstruction; this Dream is about the NEXT occurrence not needing that.

## Kinships

[[bmad-loop-baseline-drift]] (the sibling Dream for a different `bmad-loop` work-loss failure mode
— found the same session, both traced to gaps in how the orchestrator's dev-retry lifecycle
handles an attempt that doesn't cleanly land; shared upstream report filed 2026-08-23 as
https://github.com/bmad-code-org/bmad-loop/issues/701, register id `baseline-commit-midflight-drift`) ·
[[pyforge-marshal]] (the estate; owns `bmad-loop` adoption)

## Realization log

- **2026-08-14** — Dream captured immediately after recovering marshal Story 10.1 by Claude Code
  transcript reconstruction (`_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/
  spec-pyforge-marshal/.memlog.md` has the full recovery narrative), per the operator's explicit
  request to fix marshal/bmad-loop to prevent this class of loss going forward.
- **2026-08-14** — Spec authored (spec-bmad-loop-intent-gap-work-preservation, pyforge-marshal) by the 2026-08-14 dream-backlog audit: Marshal-side preservation symmetry at the adapter seam; upstream evidence rides spec-bmad-loop-baseline-drift's gated report track.
- **2026-08-23** — Story 20.3 shared upstream report path cleared both gates and filed
  https://github.com/bmad-code-org/bmad-loop/issues/701 — body includes this Dream's Story 10.1
  intent-gap evidence (revert with no `attempt-preserve/*` / `failed/*/changes.patch`) alongside
  the baseline-drift mid-flight failure mode. Register entry
  `baseline-commit-midflight-drift` in marshal `upstream-register.json`. Marshal-side preservation
  for this mode remains Stories 20.4+; no `bmad_loop` package edits.

- **2026-09-09 (fleet readiness pass — operator-approved batch)** — **`specified` → `realized`.**
  Stories 20.4/20.5 are `done`: `pyforge/marshal/supervisor/intent_gap_preserve.py` parks the attempt
  proactively, supervisor-side, **before** the halt reverts (`:38-39`), and
  `scripts/missing_preserve_check.py` (pixi task `missing-preserve-check`, `pixi.toml:940-942`) is
  the watchdog. Both open questions were answered by the implementation: proactive supervisor
  snapshot (not adapter interception of `bmad_loop`'s own revert), and selective — a closed
  intent-gap vocabulary (`intent_gap_preserve.py:28-39`, `looks_like_intent_gap` at `:68`).
  Spec `ready` → `shipped`. **Residual:** the same observation-plane blindness as
  [[bmad-loop-baseline-drift]] — `missing_preserve_check.py:61` reads `~/.bmad-loops` only and greens
  over an empty set. Re-pointed by marshal **Story 33.7**. Batch:
  `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`.

## 2026-09-16 — Nobody has to hand-parse engine.pid to answer "is this run alive? (folded from bmad-loop-liveness-footgun)

# Nobody has to hand-parse engine.pid to answer "is this run alive?"

## The Dream

`bmad-loop` records each run's engine liveness identity as `<run_dir>/engine.pid` — and, since
0.9.0, that file is *not* a bare pid: it is `"<pid> <identity>"`, a whitespace-delimited pair where
the second token is a process-start-time float (a pid-reuse guard). This is the *correct*, already
pid-reuse-safe design internally (`runs.py`'s `read_named_pid_identity` / `engine_alive` /
`engine_liveness` / `probe_liveness`, a proper tri-state `alive`/`dead`/`unknown` API) — but nothing
outside `bmad_loop` itself is pointed at that API. The obvious, naive thing to do —
`ps -p $(cat engine.pid)` — silently breaks (the float token makes `ps -p`'s argument list
malformed, which reads as "no such process", i.e. always "dead") and nothing stops an operator, a
script, or a future Marshal feature from reaching for it. The dream is that this repo's own tooling
and its operators never touch `engine.pid` by hand again — there is one obvious, correct, already-
built way to ask "is run X alive", and it's the one everyone actually reaches for.

## What it looks like when real

- A human debugging a stuck-looking station reaches for `bmad-loop status <run_id> --json` (already
  returns a clean `"status"` field — confirmed `"stopped"`/presumably `"running"` this session) —
  not `cat engine.pid` / `ps -p $(cat engine.pid)`. The fleet-landing-pass operating instructions
  this repo already hands out ("verify liveness against real processes... engine.pid holds a float,
  not a pid... will mislead you") shrink from a manual `ps`/`tmux` workaround to "run this one
  command."
- Marshal's own `factory resume` double-drive gap (`spec-3-7-escalation-deferral-and-resume`,
  `deferred-work.md`) stops being blocked on "no `HarnessPort` counterpart and no Marshal-side
  [liveness] primitive" — this Dream's fix *is* that missing primitive, or a thin Marshal-side
  wrapper over it, unblocking that separate, already-deferred correctness fix rather than solving it
  itself.
- `fleet_picture.py` / `dashboard-gen`'s own liveness detection (currently `marshal status
  --format json`, keyed off the supervisor sidecar Marshal itself launches) has a documented,
  correct fallback path for a bmad-loop run Marshal didn't spawn — instead of silently reporting
  `UNSUPERVISED` with no cheaper way for an operator to double-check than raw `ps`/`tmux`.

## What is real

- **The two-token format is intentional, not a bug.** `write_named_pid`'s own docstring: "One
  whitespace-delimited line: `<pid>` (legacy) or `<pid> <identity>`" — the identity token exists so
  a reused pid reads as *not ours* rather than a false-alive. Nothing here is upstream's mistake to
  fix; the gap is entirely that no caller outside `bmad_loop` reuses its own correct liveness read.
- **bmad-loop already ships the fix as a public CLI surface.** `bmad-loop status <run_id> --json`
  returns a clean `{"run_id": ..., "status": "stopped"}` (confirmed live this session, run
  `20260814-201915-b953`) — this is the supported, versioned answer; `runs.py`'s
  `read_named_pid_identity`/`engine_alive`/`engine_liveness`/`probe_liveness` are the *internal*
  functions backing it (not part of any published API contract, so importing them directly would be
  a fragile private-API dependency across upstream version bumps).
- **This exact gotcha is already independently documented twice in this repo**, both discovered the
  hard way: the fleet-landing-pass operating instructions carry it verbatim as a standing warning,
  and `docs/dreams/artifact-chain-reconciliation.md`'s own Realization log notes "liveness verified
  against `ps`, not `engine.pid`" as something a prior session had to work around.
- **pyforge-marshal's own `deferred-work.md` already names the missing primitive as a blocker** for
  a real bug: `spec-3-7-escalation-deferral-and-resume`'s finding that `factory resume` can silently
  double-drive a still-live run, because "resuming would double-drive it; stop it first" (bmad-loop's
  own refusal) only fires *after* a live engine already exists, and Marshal has no cheap way to check
  liveness itself first — "Liveness is not [fixed]: it requires probing `engine.pid`, which has no
  `HarnessPort` counterpart and no Marshal-side primitive."
- **Empirically, today's dashboard/fleet-picture path never touches `engine.pid` at all** — `marshal
  status` keys off the `pyforge.marshal.supervisor` sidecar `marshal factory spin` launches
  alongside the engine, confirmed this session (a raw `bmad-loop run` invocation with no supervisor
  read correctly as `UNSUPERVISED`, not a false `RUNNING`). So the footgun is purely an
  operator-facing hand-diagnosis trap today, not something silently corrupting the dashboard — but
  it's exactly the primitive spec-3-7 already flagged as missing for a real correctness gap.
- **Installed version**: `bmad-loop 0.9.0` (`pixi.toml` pins `>=0.9.0`), source
  `https://github.com/bmad-code-org/bmad-loop`.

## Constraints

- **Cannot be fixed by editing the installed package in place** — same constraint as every other
  `bmad-loop-*` dream in this repo: `bmad_loop` ships via a pixi/conda-forge git-pinned dependency,
  not code this repo owns; a fix here means either shelling out to `bmad-loop status --json` (the
  supported surface) or asking upstream to publish `engine_liveness`/`probe_liveness` as public API,
  never patching `.pixi/envs/*/site-packages/bmad_loop/` directly.
- **Not a private-API dependency.** Whatever this repo builds must go through `bmad-loop status
  --json` (or another documented CLI/output contract), not `from bmad_loop.runs import
  engine_liveness` — an internal function with no stability guarantee across upstream bumps.

## Non-goals

- **Not a fix for Marshal's `factory resume` double-drive bug itself** (`spec-3-7`) — that is a
  separate, already-deferred, larger fix this Dream's primitive unblocks, not something this Dream
  needs to solve.
- **Not a request to change `engine.pid`'s on-disk format upstream.** The two-token identity design
  is correct and intentional; nothing here asks bmad-loop to change it.

## Kinships

[[pyforge-marshal]] (owns `bmad-loop` adoption per `docs/specs/bmad-loop-adoption.md`) ·
[[bmad-loop-baseline-drift]] (sibling bmad-loop-footgun dream, same "cannot edit the installed
package" constraint, same containment-over-upstream-fix framing) · `spec-3-7-escalation-deferral-
and-resume`'s `deferred-work.md` entry (names the missing liveness primitive as a live blocker) ·
`docs/dreams/artifact-chain-reconciliation.md` (independently rediscovered the same footgun)

## Realization log

- **2026-08-15** — Dream captured. Surfaced during a PyForge fleet landing pass: a raw `bmad-loop
  run` invocation (bypassing `marshal factory spin`) was correctly reported `UNSUPERVISED` by
  `marshal status`/`fleet-picture` (no supervisor sidecar was ever started for it — not a detector
  bug), but diagnosing *why* required manual `ps`/`tmux` checks because `engine.pid`'s two-token
  format breaks the naive `ps -p $(cat engine.pid)` check operators reach for by habit. Traced to
  `bmad-loop 0.9.0`'s `runs.py` (`read_named_pid_identity`/`engine_alive`/`engine_liveness`), found
  the correct fix already exists as `bmad-loop status --json`, and found this exact gap already
  named (but unaddressed) in pyforge-marshal's own `deferred-work.md` (spec-3-7).

- **2026-09-09 (fleet readiness pass — operator-approved batch)** — **`specified` → `realized`.**
  Epic 24 is 3/3 `done` and in effect: CAP-1 landed as `HarnessPort.engine_liveness`
  (`ports/harness.py:771-782`, tri-state `alive`/`dead`/`unknown`, `unknown` never coerced),
  implemented at `adapters/harness_bmadloop.py:1657` by shelling to `bmad-loop status <run_id>
  --json` + `list --json`, never importing `bmad_loop`; CAP-2 named that command as the documented
  operator answer (team memory `.claude/memory/reference/fleet-landing-pass-li

*(truncated in fold; original file remains archived)*


## 2026-09-16 — A BMAD write can never land in the wrong project's artifacts, mechanically (folded from bmad-switch-scope-enforcement)

# A BMAD write can never land in the wrong project's artifacts, mechanically

## The Dream

Every BMAD skill that writes planning artifacts resolves through two gitignored
compatibility symlinks (`_bmad-output/planning-artifacts`, `_bmad-output/implementation-artifacts`)
that must agree with the `.active-project` marker and with whatever project the caller actually
intended. Today that agreement is checked two different ways in two different places, and both
checks stop short of the one guarantee that actually matters: that a write lands in the project
the caller meant to write to.

`scripts/bmad-switch --current` (repo root) warns on marker/symlink disagreement, but the
warning is advisory — it's stderr text, the exit code stays 0, and nothing calls it automatically
before a write. Marshal's own ported copy (`cli/init.py`'s `MRS-INIT-003` check, provisioning a
loop home) is stricter — it hard-fails a home's `marshal init` when the marker and symlinks
disagree — but Story 1.4's own adversarial review found it checks the wrong pair: marker-vs-symlink
internal agreement, never marker-vs-*the slug the caller actually asked for*. A home whose marker
and symlinks consistently agree on the WRONG project — silently repurposed by some earlier `bmad-switch`
call, a stale worktree, or (per the live 2026-07-25 fan-out incident) a second concurrent agent
racing the same shared marker — sails through both checks clean and gets silently reconciled onto
the new target with no warning it was ever pointed elsewhere. The dream is a single verification
primitive, shared by the repo-root script and Marshal's ported copy, that checks the ONE thing
that actually matters — "does this resolve to the slug I asked for, right now" — hard-fails loud
when it doesn't, and gets called automatically at every write boundary instead of only when someone
remembers to run `--current` by hand.

## What it looks like when real

- One shared verification function — `verify_scope(root, expected_slug) -> None | ScopeDrift` —
  used by both `scripts/bmad-switch` and Marshal's `cli/init.py`, replacing today's two divergent,
  partial checks with one. It compares the marker, both symlink targets, AND the caller's
  `expected_slug` in one pass, closing DW-1-4-2's blind spot (2): a home whose marker and symlinks
  agree with EACH OTHER but not with the requested slug is now a drift, not a silent pass.
- Symlink-target parsing recognizes more than the exact `projects/<slug>/planning-artifacts`
  shape (closing DW-1-4-2's blind spot (1)) — an absolute path or a target written by different
  tooling is reported as "unrecognized," never silently treated as agreement.
- `bmad-switch --current` (and any BMAD write-skill's own preflight) exits non-zero on drift,
  not just stderr text at exit 0 — a scripted caller (or a parallel agent doing its own
  `readlink -f` discipline today, per this repo's own auto-memory) gets a real signal instead of
  having to parse warning text.
- The check is cheap enough (three file reads, no subprocess) to run before every write-skill
  invocation without meaningfully slowing anything down — closing the actual gap the 2026-07-25
  incident exposed: the switch is a mutex nobody holds, and today's mitigation is "the agents
  checked," which is discipline, not enforcement.

## What is real

Substantial prior art already exists and this Dream does not start from zero:

- **2026-07-14**: `scripts/bmad-switch` was fixed to write the marker LAST, after symlinks
  re-point successfully, so a failed re-point can no longer leave the marker disagreeing with the
  links (the 10h pyforge-warden near-miss this fixed is `bmad-switch`'s own docstring history).
- **Story 1.4** (`pyforge-marshal`, already shipped) ported this into `cli/init.py` as the
  `MRS-INIT-003` guard for loop-home provisioning — stricter than the repo-root script (hard
  exit, not just a warning), but scoped only to init-time, and only to internal marker/symlink
  agreement.
- **DW-1-4-2** (`pyforge-marshal`'s own deferred-work ledger, found during Story 1.4's
  adversarial review) already names both blind spots this Dream closes, and already says the
  fix "needs a product decision" — this Dream is that decision.
- **CLAUDE.md**'s standing rule ("PARALLEL AGENTS: never touch the switch — address projects by
  physical path... pass `BMAD_ACTIVE_PROJECT` per invocation") is today's operational workaround:
  agents are told to avoid the shared mutex rather than the mutex being made safe to share.
- **The 2026-07-25 fan-out incident** (5 concurrent agents running `bmad-switch`, the shared
  symlink observed moving `pyforge-doctor → pyforge-marshal → pyforge-mason → deckcraft` mid-run)
  is the concrete evidence this class of bug is not hypothetical — it was caught only because
  every agent independently ran `readlink -f` and noticed.
- Distant prior art: a sibling org's `bmad-workspace-integration` dream (`wf-dev-cli`'s
  `extensions/bmad.py`, 650 LOC) does a related but broader thing — automatic switch-on-workspace-open
  plus checkpoint stash/restore plus scope.yml path-boundary enforcement. That dream's automatic-switch
  trigger depends on a workspace-management capability ([[developer-workspace-management]]-shaped)
  this repo doesn't have yet; its `checkpoint` verb has no documented local pain point. This Dream
  deliberately scopes down to only the piece with a real, already-bitten, already-triaged local gap.

## Constraints

- **One verification function, not two.** `scripts/bmad-switch` and Marshal's `cli/init.py` must
  call the SAME logic, not maintain parallel copies that can drift from each other the way the
  current two checks already have.
- **Hard-fail, never a warning that can be ignored.** The whole point is replacing discipline
  ("the agents checked") with enforcement; a check that only prints to stderr at exit 0 does not
  close this gap, it just documents it more visibly.
- **Cheap enough to call on every write, not just at init/switch time.** Three file reads and a
  string compare — no subprocess, no network — so wiring it into a write-skill's preflight is
  free, not a tax anyone will disable under load.

## Non-goals

- **Not automatic switch-on-workspace-open.** That trigger needs a workspace-management capability
  this repo doesn't have; wiring it in without that capability existing would be speculative.
- **Not a `checkpoint`-style stash/restore of AI session work.** No documented local pain point
  motivates it; bmad-loop's own `keep_failed` patch-preservation already covers the adjacent
  "don't lose work on failure" concern for loop-driven stories.
- **Not a general `scope.yml` path-boundary enforcer** for arbitrary file writes outside BMAD
  artifacts — this Dream is scoped to the marker/symlink/expected-slug triangle specifically.
- **Not re-litigating whether Marshal should own `bmad-switch`'s source** — `spec-pyforge-marshal`
  already states this ("Marshal owns the source of `scripts/bmad-switch`... Genesis owns their
  delivery as COPIED·MANAGED artifacts"); this Dream operates inside that already-decided boundary.

## Kinships

[[bmad-module-provisioning]] (the other realized BMAD-infra Dream owned by a non-Marshal station,
useful as a format precedent) · [[pyforge-marshal]] (the estate; DW-1-4-2 already lives in its own
deferred-work ledger, found during Story 1.4's adversarial review) · [[genesis-installer]] (the
delivery-vs-source boundary this Dream operates inside, per `spec-pyforge-marshal`'s own SPEC.md) ·
[[scratch-worktree-lifecycle]] (a Steward-owned scratch worktree opened against a specific BMAD
project is exactly the caller this Dream's `verify_scope` primitive was designed for — cross-station
kinship, not a merge)

## Realization log

- **2026-08-14** — Dream captured. Surfaced while evaluating a sibling org's `bmad-workspace-integration`
  dream as a PyForge candidate; investigation found the broader dream's automatic-switch and
  checkpoint pieces lack local

*(truncated in fold; original file remains archived)*


## 2026-09-16 — Dashboard velocity counts every story's real effort, not just bmad-loop-journaled ones (folded from dashboard-velocity-captures-hand-driven-work)

# Dashboard velocity counts every story's real effort, not just bmad-loop-journaled ones

## The Dream

The factory console's velocity chart (`pyforge.doctor.sources.fleet_scan`'s `# ---- delivery
timing / velocity (derived from bmad-loop run journals) ----` section) shows "active
agent-compute per story" — but only for stories that ran through `bmad-loop`, because it is
literally "derived from every loop home's journals" (per-run session logs bmad-loop itself
writes). A story implemented any other way — `bmad-dev-auto` hand-driven outside the loop
(`bmad-quick-dev`, or the assistant orchestrating a sequence of `bmad-dev-auto` calls itself,
as doctor's Epic 8 was on 2026-08-15), a manual `bmad-quick-dev` session, anything that isn't
a bmad-loop run — leaves no journal, so it lands in the same "not measured" bucket as
stories that predate loop instrumentation entirely, even though real effort/duration data
exists for it (git commit timestamps, subagent session durations, or a story's own
`baseline_revision`/`final_revision` spec-file fields).

The chart's own caption is honest about this ("18 of 41 stories measured; the rest predate
loop instrumentation... deliberately absent rather than plotted"), but that caption's
framing — "predates instrumentation" — no longer covers every case in the bucket. A
hand-driven story finished TODAY, with a real git history and real timing available, is
absent from the same reason a story from before the loop existed at all is absent. Those are
different situations with the same symptom.

## What it looks like when real

- Every `done` story contributes SOME timing signal to the console, sourced from whichever
  fidelity is actually available: bmad-loop journal (highest fidelity, current behavior,
  unchanged) > a hand-authored/derived wall-clock duration from the story spec's own
  `baseline_revision`→`final_revision` git range (lower fidelity, but real) > absent only
  when genuinely no timing data exists at all (pre-instrumentation legacy stories with no
  spec file carrying those fields).
- `generate.py` already has the mechanism this needs half-built: its own docstring says
  "Hand-authored `timing`/`velocity` are PRESERVED, never overwritten" — the write path for
  a CURATED (non-derived) entry already exists (this is how Warden's/Atlas's own
  once-computed-then-preserved numbers survive re-runs today). What's missing is a
  CAPTURE step that populates that curated slot for a hand-driven story, not the storage.
- Two candidate capture points, either or both: (a) `bmad-dev-auto`'s own HALT protocol
  gains a lightweight timing stamp (it already writes `baseline_revision`/`final_revision`
  into the spec's frontmatter at exactly the right moments — adding a duration derived from
  those two commits' timestamps is a small, natural extension); (b) `generate.py` itself
  back-fills a wall-clock-only data point for any `done` story with a spec file carrying
  both revision fields but no bmad-loop journal, distinguishing it visually from
  journal-derived "active agent-compute" bars (same distinction the existing "timing strip"
  already makes for legacy stories, per the chart's own caption).

## What is real

Nothing. Confirmed absent 2026-08-15: after doctor's Epic 8 landed (4 stories, hand-driven
via `bmad-dev-auto`, real adversarial review and real landing PRs for every one), the
dashboard's velocity chart shows no bars for 8.1–8.4 — verified by reading
`generate.py`'s own velocity-derivation code, which only walks bmad-loop journals.

## Constraints

- Never fabricate a number for a story with genuinely no data — the existing "deliberately
  absent rather than plotted" discipline for undated legacy stories must survive.
- A wall-clock-derived fallback measures something DIFFERENT from bmad-loop's own
  "active agent-compute, excludes gate-pause wait" — must be visually/textually
  distinguished, not silently blended into the same bar type as if it were equally precise.
- Preserve the existing hand-authored-value-is-never-overwritten guarantee — Warden's and
  Atlas's already-curated numbers must not be touched by whatever capture mechanism lands
  here.

## Non-goals

- Not retrofitting timing for stories with no spec file at all (truly pre-instrumentation,
  no revision fields to derive from) — those stay absent, correctly.
- Not building a NEW orchestration path — this only affects how already-shipped work
  (via `bmad-dev-auto`/`bmad-quick-dev`, whichever route a story actually took) gets
  reflected in the console, not how it gets built.

## Kinships

[[factory-console]] (the console this Dream extends — owner: marshal, realized, narrative
absorbed into [[pyforge-marshal]]) · doctor's Epic 8 (2026-08-15, the concrete case that
surfaced this gap — hand-driven via `bmad-dev-auto`, see the session's own project memory
`project_session_close_2026-08-15_epic8_doctor` for the full worked example).

## Realization log

- **2026-08-15** — Dream captured. Surfaced when the user pointed out doctor's Epic 8
  (hand-driven, no bmad-loop) has no velocity bars on the live dashboard, and asked
  whether this had been captured as backlog before ending the session. It had not — only
  noted in the assistant's own personal session-memory, not as a repo-tracked Dream. This
  file is that capture.

- **2026-09-09 (fleet readiness pass — operator-approved batch)** — **`specified` → `realized` in
  mechanism, and NOT realized in effect.** Epic 23 (23.1 wall-clock derivation, 23.2 never blended,
  23.3 caption partitions by true reason) is 3/3 `done` and the code is
  `scripts/fleet_scan.py::scan_timing:3067-3250`; the Spec, still reading `draft`, moves to
  `shipped`. But steward Story 30.2 deleted the Guildhall generator: `fleet_scan.py:6` records "the
  `data.js` write CLI is retired — `main()` exits nonzero", `docs/dashboard/data.js` is gone, and
  `docs/dashboard/index.html` is a 14-line redirect stub. `scan_timing`'s only non-test caller is
  `_generate` at `:3591`, reachable only from a `main()` that returns 2 — **the derivation this Dream
  asked for exists and nothing reads it.** Seven meta-tests keep it green.
  **OQ-4 closed as moot:** `bmad-build-auto`'s HALT does not gain a duration stamp — `marshal factory
  dispatch` journals per-session timing at source (four live `journal.jsonl` runs read). OQ1–OQ3 were
  answered in the shipped code. A destination decision is owed before steward Cutover 44.1 resolves
  `scripts/fleet_scan.py`. Batch:
  `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`.

## 2026-09-16 — Durable runs — work survives the machine that made it (folded from durable-runs)

> **Superseded 2026-08-02 (dream consolidation).** Fully decomposed into `spec-pyforge-marshal`
> and the real PRD as FR-61 (bounded-loss durability, stage-boundary push + fleet-launch
> wiring), FR-62 (durability as a reported fleet-status dimension), and FR-63 (fleet-wide
> branch retirement) — see [`docs/dreams/pyforge-marshal.md`](pyforge-marshal.md). Nothing in
> this Dream's real, measured evidence (the 2026-07-31 audit table) is lost — it is cited
> directly in the consolidated Dream. See `spec-durable-runs` for the retirement record.

# Durable runs — work survives the machine that made it

## The Dream

An unattended factory that can lose its own output is not autonomous, it is
lucky. Every artifact a run produces — the commit, the story spec, the verdict,
the token spend that bought them — should be **durable the moment it exists**,
not the moment somebody remembers to save it.

The loss is never only code. A discarded story is lost **compute, tokens, and
wall-clock**: marshal 1.8 was 8.8M weighted tokens and about an hour of a
machine's life, and for forty minutes it existed as an unpushed commit on one
disk. Recovering code is possible. Re-buying the hour is not.

> A run that has to be remembered is a run that can be forgotten.

## Why now — measured, not feared

Asked on 2026-07-31 whether the fleet's work was saved, the answer was no, and
the size of "no" was the surprise:

| At risk | Extent |
|---|---|
| Station loop branches | **6** (marshal, doctor, herald, mason, scribe, steward) — none on any remote |
| `recover/*` branches | **~5,150 lines** across four rescue branches |
| herald 1.2 transport | **734 lines**, 7 files *including its story spec*, unpushed **six days** |
| Dangling commits | **156** holding real content, one `git gc` from unrecoverable |
| marshal story 1.8 | **1,748 lines**, committed by the dev phase and unpushed **40 minutes** |

Nothing detected any of it. Nine detectors ran green throughout, because not one
asked the question. And the precedent was already on the record: scribe 1.3's
1,102 lines survived only as a dangling commit and came back by luck.

**The window is not a backlog — it reopens.** "Everything is saved" was true when
said and false forty minutes later, because a dev phase had finished in between.
Nine stations, one dev phase each per 60–90 minutes: the factory spends most of
its life with an hour of unsaved work somewhere.

## What is real

- **`unpushed-work-check`** — the detector, shipped 2026-07-31. Local branches
  with unique content that are on no remote, plus dangling commits holding real
  work. `scope=runtime`, and that is load-bearing: a CI runner has neither local
  branches nor dangling objects, so this check would pass **vacuously** there —
  a gate reporting success because it stands where the failure cannot occur.
- **`loop-push-watch`** — the stopgap, shipped the same day. Pushes every loop
  home's station and per-story branches on an interval while any engine runs,
  exits by itself when the fleet does. Push is read-only against working trees,
  so it is safe beside a live run. It **bounds** worst-case loss to one interval;
  it does not remove it.
- **156 rescue tags** on origin, making previously unreachable commits reachable.

## What is real, part two — the durability signal itself (measured 2026-08-09)

FR-61 shipped and **works**: during the doctor Epic 6 run, Marshal's supervisor
journaled **22 `stage-push` records** across `dev-commit-landed`, `story-merged`
and `interval` boundaries, and `origin/loop/pyforge-doctor` carried the merges of
6-2, 6-3 and 6-4 without anyone intervening. Bounded-loss durability is real.

What is *not* real is the **signal** that reports it. Two defects, both found by
operating the thing rather than reading it, and both the same disease this repo
keeps finding: **a green nobody measured.**

- **6 of those 22 pushes reported `push-failed` (`MRS-SUPV-008`) on the success
  path.** bmad-loop deletes a story's branch when the story merges into the
  station branch; the supervisor is a *polling* observer, so by the time it acts
  on the boundary the branch is gone and `git rev-parse <branch>@{upstream}`
  answers "no such branch". `GitVcs.push` is right to raise — its docstring
  reasons that falling back would push to a target the caller never named. The
  **caller** is wrong: it asks to push a branch that was legitimately retired,
  then calls the refusal a failure. The work was safe on the station branch the
  entire time. A durability alarm that fires on success is worse than silence:
  it cost an operator an hour of wrong diagnosis on 2026-08-09, and the wrong
  diagnosis was *"durability is broken."*
- **`unpushed_work_check.py` compares branch NAMES, not tips.** `find_unpushed`
  skips any local branch with `br in remote` — so a branch whose remote copy
  merely *exists* is declared safe no matter how far behind it is.
  `loop/pyforge-doctor` sat on origin at `3f43f486c9` while the local branch was
  **8 PRs ahead** at `cbd965110b`, and the detector said nothing. It answers
  *"does a remote copy exist?"* while presenting itself as *"is the work safe?"*
  This is exactly the gap the original Dream describes — "nine detectors ran
  green throughout because none asked the durability question" — reproduced
  *inside the detector written to ask it.*

The unifying rule, and the one the original Dream already stated: **loss is
bounded only if the report is true.** A false alarm and a false all-clear are the
same defect wearing different signs, and this Dream now owns both.

## The frontier

- **The loop pushes at its own stage boundaries.** The real fix, and the reason
  this Dream exists rather than a cron entry: after the dev commit, after the
  review verdict, after the merge. Loss becomes bounded by a *stage*, not by a
  timer. Marshal owns the run lifecycle, so this is Marshal's to build —
  `bmad-loop` itself is a git-pinned external dependency, so the seam is
  marshal's supervisor around it, not a patch to someone else's completion path.
- **Interval push as the floor, not the ceiling.** Keep the watcher as the
  backstop for whatever the stage hooks miss, and make it part of a fleet launch
  rather than something started by hand — it was absent for this entire run
  because nobody thought of it, which is the same failure one level up.
- **Durability is a run property, and should be reported like one.** A run whose
  work is not on a remote is not "green"; the console should say so on the row,
  the way it refuses to publish an unowned Dream.
- **Nothing should require a human to ask.** The whole finding above surfaced
  because an operator asked twice. Once is attention; twice is luck.
- **Branch retirement — the other half of the lifecycle.** Saving work created 36
  branches and 160 rescue tags in one afternoon; nothing knows when any of them
  may be released. The question is *derivable*, not a judgement call: a story
  branch is retirable when its content is in `main` **by patch-id**, its run is
  concluded, and its story is `done` with a merge sha. Doing that by hand across
  62 branches is 62 chances to be wrong; writing it once is zero.

  Two prefixes are never candidates: `loop/*` is how the fleet works, and
  `rescue/*` tags are the **only** reachability for commits `git gc` would
  otherwise collect — untagging them re-arms the very failure they record.

  **The first pruning run must explain itself.** For each branch it proposes to
  retire it names the evidence — the merge sha, the patch-id match, the concluded
  run — and it refuses on anything it cannot prove, rather than defaulting to
  delete. Dry-run by default, like `adopt`.

  It is the inverse of `unpushed-work-check` and shares its machinery: that one
  finds what must be saved, this finds what may be released. Both answer "where
  does this content exist?"; only the sign differs.

  Recorded because the classification is genuinely hard and looks easy. Two
  q

*(truncated in fold; original file remains archived)*


## Realization log

- **2026-08-09** — Reopened for the *signal*, not the mechanism. FR-61's
  stage-boundary push was verified working in a live 9-story run; what failed was
  its reporting. Recorded as two capabilities (retired-branch classification, and
  tip-comparison in the detector) rather than a new durability feature, because
  nothing about the guarantee needs building — only the truth of the claim about
  it. Found the way the Dream's own motivating evidence was found: by looking at
  a real run, not by reading the code.

- **2026-07-31** — Dream seeded (operator call), after a push-everything sweep
  found six unpushed station branches, ~5,150 lines on `recover/*`, herald 1.2's
  734-line transport story unpushed for six days, 156 dangling commits, and
  marshal 1.8's 1,748 lines committed forty minutes earlier. Owner **marshal**
  by the run-lifecycle argument; Steward noted as the alternative if this is
  later judged an estate concern. Shipped the same day: `unpushed-work-check`
  (detector) and `loop-push-watch` (stopgap). The durable fix — the loop pushing
  at its own stage boundaries — is deliberately left to the pipeline rather than
  hand-written, which is why this file exists.

## 2026-09-16 — Factory console — the whole pipeline on one page (folded from factory-console)

> **Narrative consolidated 2026-08-02 (dream-level only).** This Dream's narrative now lives
> in [`docs/dreams/pyforge-marshal.md`](pyforge-marshal.md) under "Kept separate on purpose."
> **Planning superseded 2026-08-24:** `spec-factory-console` is retired in favor of steward
> `spec-pyforge-unifying-strategy` CAP-2 (Lane 1 Wagtail front door). The generator under
> `docs/dashboard/` remains until steward Story 30.2; Kedro-Viz (`docs/dashboard/kedro-viz/**`)
> is atlas-owned and out of scope for retirement. Companions `console-contract.md` and
> `drill-evidence.md` remain historical references for the generator until deletion.

# Factory console — the whole pipeline on one page

## The Dream

One public page where the entire "Dream to Code" factory is legible at a
glance: **every Dream and where it sits in the lifecycle**
(seeded → in-deck → in-spec → realized), every build program's epic/story
progress live from `main`, the in-flight story's clock, and the deliveries as
they land. The console is how a human governs *intent* without reading logs —
[[pyforge-marshal]]'s "every run stays visible" doctrine given a front door,
and (in the persona ideal) the stage from which Herald proclaims.

Nothing on the console is hand-maintained: sprint state derives from
`sprint-status.yaml` locally and from `main`'s commit subjects in CI; Dream
state derives from `docs/dreams/*.md` frontmatter. If the repo moved, the
console already knows.

## What is real

- **The program console** — `docs/dashboard/` (index.html + data.js +
  generate.py), published on **GitHub Pages**
  (https://rxm7706.github.io/local-recipes/) by a workflow that uploads *only*
  `docs/dashboard/` (the repo is private; the page is public — scope is a
  security boundary, never widen it without re-checking).
- **Two-source refresh** — `dashboard-gen` locally (richest: done/active/
  gated/pending from Tier-3 sprint files); `--source git` at Pages deploy time
  (derives DONE from bmad-loop merge subjects; upgrade-only, never downgrades).
- **The Dreamscape board** — every `docs/dreams/*.md` scanned at generate
  time; the board renders each Dream in its lifecycle stage, doubling as the
  frontmatter-status detector the drift-checker never had.

## The frontier

- Per-Dream drill-through: link a Dream to its deck, spec folder, and BMAD
  project row (the no-straggler policy, made visible).
- Delivery feed: notables/releases marshalled onto the page (today they live
  in commit history and CHANGELOGs).
- Fleet health strip from [[pyforge-doctor]]; run telemetry (attempt counts,
  gate outcomes) from [[pyforge-marshal]].

## Kinships

[[pyforge-marshal]] (visibility doctrine — the console is its ledger) ·
[[pyforge-steward]] (owns the Pages deployment surface) ·
[[pyforge-charter]] (the pipeline the console makes legible) ·
[[modernist-identity]] (a candidate restyle; today the console has its own
mono/panel language).

## Realization log

- **2026-08-24** — `spec-factory-console` superseded by steward Canopy CAP-2; Wagtail Lane 1
  replaces the static Guildhall as the estate front door (generator until steward 30.2).

- **2026-08-09** — Reopened for the fleet roll-up. Five stations ran in parallel
  overnight and the operator's first question was one the board could not answer:
  *how much is done, how much is left, and is anything waiting on me?* The board
  had the per-epic story lists all along but no total, and — worse — its own
  story states are `done`/`active`/`pending` only, so a BLOCKED story is
  indistinguishable from one merely not started. Six stories that will never run
  looked exactly like 119 that will. Split deliberately: the tracked half
  (done/total/blocked, roll-up) renders on Pages, the live half (run state,
  projection, ATTENTION) stays local, because it derives from tmux and
  `~/.bmad-loops` and CI has neither — publishing it would publish a number the
  deploy cannot measure.

- **2026-07** — Warden+Atlas program console built and published on Pages
  during the bmad-loop runs; `--source git` auto-refresh added so the public
  page tracks `main` hands-off.
- **2026-07-23** — retro-seeded as a Dream (the console predates the
  Dream-first model); Dreamscape lifecycle board added the same day —
  the console now lists every Dream and its stage.

- **2026-09-09 (fleet readiness pass — operator-approved batch)** — Status kept `realized` (in effect
  via Lane 1); **the governing Spec's `surface:` no longer describes its own files.**
  `spec-factory-console` is `superseded` yet still governs two paths whose meaning changed under it:
  `docs/dashboard/index.html` is now a **14-line "console moved" stub** since steward Story 30.2, and
  `scripts/fleet_scan.py` is a **parser library only** — the `data.js` write CLI is retired
  (`fleet_scan.py:6`, `:93`; `main()` returns 2 at `:3505-3511`) and `docs/dashboard/data.js` is gone
  from disk. **Cross-station:** steward Cutover **Story 44.1** requires 100 % of tracked files to
  resolve to `stays` / `dies` / a destination, and both of these currently resolve only to a
  superseded Spec whose surface no longer describes them. A destination decision for both is owed to
  44.1 — and it is the same decision [[dashboard-velocity-captures-hand-driven-work]] needs for
  `scan_timing`'s orphaned CAP-1..3. Batch:
  `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`.

## 2026-09-16 — A dead supervisor and a dead engine report identically — and only one of them needs help (folded from fleet-status-supervisor-fallback)

# A dead supervisor and a dead engine report identically — and only one of them needs help

## The Dream

`marshal status`'s fleet view (Story 5.1, FR-36/AD-5) exists so "what is
running?" is one question, not five. Its state derivation
(`core/status.py::derive_home_state`) treats supervisor liveness as an
override above everything else — its own docstring is explicit: "Supervisor
liveness overrides every other derived state... `supervisor_alive is False`
and `not finished` together are the ONLY unsupervised trigger." In code, the
very first branch:

```python
if not finished and supervisor_alive is False:
    return "unsupervised"
```

...returns before the function has looked at whether the harness itself has
any actively-running task (`"running"` via a non-terminal `TaskPhaseSnapshot`).
`supervisor_alive` is a real OS-level `process.is_alive(supervisor_pid)` probe
(`cli/status.py`) — but it only probes the *supervisor sidecar* Marshal itself
spawns, never the underlying `bmad-loop` engine process the sidecar watches.
When the sidecar is gone but the engine is not, the row still reads
`unsupervised`.

That gap is not hypothetical. On 2026-08-11, 5 live stations (marshal, doctor,
mason, steward, herald) were resumed via a bare `bmad-loop resume <run_id>`
instead of `marshal factory resume <slug>`. The bare path never spawns a
fresh supervisor sidecar, so `supervisor_alive` stayed `False` for the rest
of each run's life. Every subsequent `fleet-picture` run (the
`scripts/fleet_picture.py` wrapper around `marshal status --format json`)
reported all 5 as `UNSUPERVISED — needs re-spin` — even though each station
was independently confirmed fully alive and working: its `bmad-loop resume`
process present in `ps`, its tmux session live, and its own `state.json`
reading `stopped: false`. The report gave no way to tell "the engine actually
died too, re-spin it" from "the sidecar never attached, but the work is
fine" apart from that manual three-way cross-check — an operator (or another
AI session reading the fleet report) had to do it by hand, and did, three
separate landing-pass reports in that one session.

The immediate trigger is being closed operationally — the standing practice
is now "always resume via `marshal factory resume`, never bare `bmad-loop
resume`" — so this exact reproduction path should recur less. But the
underlying blind spot is bigger than its trigger: a supervisor sidecar can go
missing for any number of reasons independent of the engine's own health — a
sidecar crash, `marshal factory spin --foreground`'s own escape hatch that
never spawns one at all, a sidecar process that is killed and never
restarted, or (per the docstring itself) a `supervisor_pid` that is simply
never recovered. Every one of those hits the same first branch and collapses
to the same word, `"unsupervised"`, whether or not there is anything actually
wrong.

`derive_home_state`'s own AD-5 promise is that every row is derived from
journals and run state, never hand-assembled or silently guessed at — and
Story 5.1's own acceptance criterion already says "a home with a dead
supervisor is shown as unsupervised, not as healthy." That promise is half
kept: a dead supervisor is never shown as healthy, but a *healthy engine
behind a dead supervisor* is never shown as healthy either. The fleet view is
supposed to be the one question that replaces five; today, for this one
case, it silently reintroduces exactly those five.

## What it looks like when real

- When `supervisor_alive is False`, the fleet view has a second, independent
  signal to consult before it settles on `"unsupervised"` — something that
  answers "is the engine itself still doing anything?", not just "did its
  sidecar attach." What that signal is (an engine-process liveness probe, the
  run's own tmux session, freshness of `state.json`/journal activity, or some
  combination) is a design decision for the Spec and its downstream story,
  not settled here.
- The two failure shapes read differently in the report itself, so an
  operator — or an automated `fleet-picture` consumer — never again has to
  run the `ps` / `tmux ls` / `state.json` cross-check by hand to tell them
  apart.
- A run whose supervisor is gone AND whose engine is demonstrably gone too
  still reads as needing attention — this Dream narrows a false positive, it
  never softens a real one.
- The fix stays inside the spirit of AD-5: whatever the fallback checks, it
  is itself derived from journals/process state, never a hand-maintained
  flag or an operator override.

## Constraints

- This is a narrow gap-fill, not a redesign of the state model. The
  `FLEET_STATES` five-value vocabulary, and the rule that a dead supervisor
  is never reported as healthy, both stay intact.
- No implementation detail is prescribed here — not which process to probe,
  not whether tmux or `state.json` freshness is the right signal, not how
  the extra check is surfaced in the row. That is exactly what the Spec (and
  the story that decomposes it) is for.

## Realization log

- **2026-08-11** — Captured after a live reproduction the same day: 5
  stations resumed via bare `bmad-loop resume` reported `UNSUPERVISED —
  needs re-spin` for the rest of their run's life despite being
  independently verified alive and working, requiring the same manual
  cross-check (`ps`, `tmux ls`, `state.json`) three separate times in one
  session before the pattern was recognized and the operational fix
  (`marshal factory resume`, never bare `bmad-loop resume`) was adopted
  going forward. Queued as a Dream rather than patched by hand —
  `core/status.py`, `cli/status.py`, and `scripts/fleet_picture.py` were
  deliberately left untouched pending the Spec/story chain.
- **2026-08-14** — Realized — FR-181 (PRD, PR #435), Story 5.8 shipped (`d9f7691c97`), ledger-done. Status flipped by the 2026-08-14 dream-backlog chain audit.

## 2026-09-16 — One story in flight at a time, silently, by an upstream stub (folded from horizontal-run-concurrency)

# One story in flight at a time, silently, by an upstream stub

## The Dream

Every `bmad-loop` run Marshal launches works exactly one story at a time.
Marshal's own rendered policy template hard-codes it:
`adapters/harness_bmadloop.py:320` `max_parallel = 1`, with no comment
explaining why — unlike almost every other line in that template. The
question behind this Dream: is that a Marshal-side default worth revisiting,
or a hard ceiling imposed somewhere else entirely?

It is the latter, confirmed by reading the vendored `bmad_loop==0.9.0`
package directly
(`.pixi/envs/local-recipes/lib/python3.14/site-packages/bmad_loop/policy.py`).
Its own `ScmPolicy.max_parallel` field carries the answer as a comment
(`:448-451`): *"units in flight at once. Parallel fan-out (Phase 5) is not
built yet, so any value > 1 is clamped to 1 in loads() — the knob exists
but is inert until the parallel scheduler lands."* The loader backs that up
in code: `:815-817` raises `PolicyError` if the requested value is `< 1`,
then `:841-842` computes `max_parallel=min(requested_parallel, 1)` — any
value an operator asks for above 1 is silently floored to 1, with no
diagnostic surfaced back. `bmad_loop`'s own shipped policy-template comment
says the same thing in fewer words (`:1077`): *"parallel fan-out unbuilt;
values > 1 clamp to 1."* This is a stub for a feature the engine names and
has not built, not a Marshal-side conservatism. Prior art independently
confirms it: a 2026-07-16 technical-research finding for a different effort
already noted "bmad-loop v0.8.1 executes stories sequentially (`max_parallel
= 1` — fan-out is not a shipped capability)"
(`docs/specs/cfe-atlas-datapipeline-kedro-migration.md:91`) — still true two
minor versions later at 0.9.0.

Marshal's own worktree-per-story isolation already exists —
`adapters/harness_bmadloop.py:309` `isolation = "worktree"`, `:310`
`branch_per = "story"` — but that describes how the ONE story currently in
flight is isolated, not a proof that N stories in flight at once would stay
isolated from each other. Whether the shared journal (`core/journal.py`,
built multi-writer-safe at Story 3.1 for a different reason — many *loop
homes* sharing one store, not many stories inside one run), the supervisor's
idle/budget ladder, and the landing path would all hold under concurrent
dispatch is unverified in either direction, because nothing has ever
attempted it.

This gap is unregistered. Story 6.8's own tracked upstream-contribution
register (`upstream-register.json`) carries 8 entries for known `bmad-loop`
gaps and their Marshal-side workarounds — including the adjacent
"per-story-model-tiering" gap — but none for parallel fan-out. And "vertical
scaling" as a concept the operator asked about does not exist anywhere in
this repo's planning corpus at all (grep across `docs/` and `_bmad-output/`
for "vertical scal"/"horizontal scal" returns zero hits). The closest
analog — escalating a *single* story's model on a struggling retry — is a
different mechanism, captured in the sibling Dream
[[adaptive-model-tiering]], not this one. This Dream is narrowly about
whether, and how, more than one story could ever run inside one launch.

## What it looks like when real

- An operator who sets `scm.max_parallel > 1` (or the equivalent Marshal
  policy key, once one exists) is told the request is inert — a registered
  finding or advisory — instead of it being silently floored with no signal,
  the way it is today.
- The `bmad_loop` parallel-fan-out gap is tracked in the same register Story
  6.8 already maintains, so `marshal upstream` surfaces it the way it
  surfaces the other 8 known gaps, rather than it being invisible to anyone
  who hasn't read the vendored source.
- Marshal's own readiness — whether worktree isolation, the journal, the
  supervisor, and the landing path could actually support N stories in
  flight at once — is assessed and the findings recorded, so the day
  `bmad_loop`'s own Phase 5 scheduler ships, adopting it is a scoped story
  rather than a fresh investigation from zero.
- A downstream story concluding "still blocked, revisit when `bmad_loop`
  ships Phase 5" is an acceptable, complete outcome — this Dream does not
  presuppose that concurrent dispatch ships from Marshal's side at all.

## Constraints

- Marshal must not attempt to build actual concurrent story dispatch while
  `bmad_loop` 0.9.0's own `loads()` clamps `max_parallel` to 1 server-side —
  that would be building against a knob the engine itself defeats
  unconditionally.
- Nothing here touches the vendored `bmad_loop` package itself (AD-2/AD-3's
  wrap-never-fork discipline; `adapters/harness_bmadloop.py` is the one
  seam). If a parallel scheduler ever ships, it ships upstream; Marshal's
  role is to be ready to consume it, not to build one inside the wrapper.
- This is a distinct axis from the cross-project concurrency Marshal already
  supports and measures (multiple loop *homes* running simultaneously,
  `prd.md:927`'s SM-5, currently 7 provisioned) — that capability is
  unaffected and not in scope here.

## Realization log

- **2026-08-11** — Captured during the same cost/speed investigation as
  [[adaptive-model-tiering]]: why bmad-loop-driven unattended runs are
  slower and more expensive than a single supervised session, and what
  Marshal could build to help. Direct read of the vendored
  `bmad_loop==0.9.0` source confirmed `max_parallel` is an inert stub,
  clamped to 1 at policy load regardless of the requested value, with the
  engine's own comments naming the missing piece "Phase 5" and stating it
  is "not built yet." No existing FR, story, or `upstream-register.json`
  entry names this gap. Queued as a Dream rather than patched by hand —
  `adapters/harness_bmadloop.py` and `upstream-register.json` were
  deliberately left untouched pending the Spec/story chain.
- **2026-08-14** — Realized in its own declared scope — Story 3.13 (FR-184) shipped the loud advisory (`MRS-POLICY-007`), the `upstream-register.json` `parallel-fan-out` entry, and the readiness assessment. Actual concurrent dispatch stays parked by this dream's own constraint until upstream `bmad_loop` ships Phase 5; the register tracks that day. Status flipped by the 2026-08-14 audit.

## 2026-09-16 — A legitimate landing is recognizable no matter which of the three-plus paths landed it (folded from landing-evidence-grammar)

# A legitimate landing is recognizable no matter which of the three-plus paths landed it

## The Dream

Every detector and classifier that asks "did this story actually land on `main`?" consults the
same, single grammar of landing evidence — and that grammar covers every sanctioned way a story
can land: a bmad-loop native merge, a `deploy land-story` / `marshal land` templated merge, a
quick-dev PR merge, and a manual recovery landing. A story that is demonstrably on `main` is
never re-flagged as missing by one tool while another tool counts it done, and no operator ever
again proves a landing by hand with `git log --all --grep` because three classifiers each speak a
different dialect.

## What it looks like when real

- One vocabulary of recognized landing-evidence shapes — merge-subject templates, branch-name
  grammars (`land/<station>-<story>…`, `bmad-loop/<run>/<story>`), and the recovery-commit
  convention — defined once, consumed everywhere that classifies landings.
- Consumers converge on it:
  - Doctor's `story-status` evidence routes (`sources/marshal.py:479-517`) — today route 2 greps
    only bmad-loop's native `/{key} into` shape and route 3 demands the literal conjunction
    `<slug>` + `story <e>.<s>` in a `main` subject.
  - Marshal's `core.promotion.merged_story_keys` / `marshal_native_merged_keys` three-pattern
    chain (`promotion.py:93-107`), including `_GITHUB_MERGE_SUBJECT_RE`'s requirement that the
    branch's final segment *lead* with a story key — which `land/marshal-10-1-recovery` fails.
  - `marshal status`'s MRS-STATUS-010 failed-patch classifier and `marshal retire`'s
    patch-id matching (today: 0 retirement proposals because recovered branches can't be
    confirmed merged).
- A documented recovery-landing convention: a manual recovery commit/PR has a named, grammar-
  conformant subject shape, so the *next* recovery is born recognizable instead of born invisible.
- Detector deltas measured the day it ships: the three standing `story-status` false positives
  (marshal 8-2, marshal 10-1, mason 3-7 — all verified genuinely landed, PRs #482/#486/#483) go
  green with no per-story whitelist; MRS-STATUS-010's UNCONFIRMED pile shrinks to genuinely
  unlanded patches; `marshal retire` proposes real retirements again.

## What is real

- The false-positive family is live and measured (2026-08-14 detector run): 3 `story-status`
  hard-FAILs on landed stories, 26 MRS-STATUS-010 UNCONFIRMED warns, `retire` at 0 proposals —
  all one root cause: recovery-PR landings match none of the recognized grammars.
- The five stuck-orchestrator-baseline recoveries (PRs #482-#488) created the recovery-landing
  class this grammar must cover; `docs/dreams/bmad-loop-baseline-drift.md` documents why more
  recoveries may happen.
- Marshal already owns the *emitting* side end-to-end: `identity.render_merge_subject` (AD-24) and
  FR-187 (`marshal land` renders it) make Marshal-driven landings conformant going forward. The
  gap is the *consuming* side's fragmentation, plus the unconformant manual-recovery class.
- MRS-STATUS-010 already words absence-of-match honestly ("UNCONFIRMED, not proof it never
  landed", `core/status.py:836-861`) — the hedge is correct; the grammar makes it decidable.

## Constraints

- **Doctor never imports `pyforge.marshal`** (classifier-independence rule, per-check isolation).
  The shared grammar therefore cannot be a code import from Marshal: it is either a contract with
  a cross-package conformance test, a shared data artifact both read, or a `pyforge-core` home —
  the same shared-spine move Story 14.2 made for atomic-write. Deciding which is Spec work.
- Absence of evidence stays hedged where it is hedged today: the grammar widens what is
  *recognizable*, it must not convert "no match" into a confident "never landed" anywhere.
- Forward-compatible with FR-187: the templated subject is one shape in the grammar, not the
  grammar itself.

## Non-goals

- **Not** retroactive rewriting of historical merge subjects — the grammar must recognize the
  existing recovery landings as they were actually written (or accept a one-time, reviewed
  allowlist for the pre-convention era), never rewrite history.
- **Not** a new landing path — this recognizes landings, it does not perform them.
- **Not** a general provenance system — the question is exactly "did story X land on main",
  nothing broader.

## Kinships

- [[marshal-land-merge-subject]] — realized; made Marshal's own landings conformant (FR-187).
  This dream is its consuming-side completion.
- [[quick-dev-reconciliation]] — realized; `not-loop-native` completions reach the ledger
  (FR-186). This dream sharpens what `not-loop-native` can be *decomposed into*.
- [[bmad-loop-baseline-drift]] — the producer of the recovery-landing class this grammar must
  recognize.

## Realization log

- **2026-08-14** — Captured by the 2026-08-14 broken-windows audit, which root-caused the three
  standing `story-status` false positives, the 26-warn MRS-STATUS-010 pile, and `marshal
  retire`'s 0-proposal state to one shared cause: three independent classifiers, three partial
  grammars, and a recovery-landing class none of them recognize. Verified against
  `sources/marshal.py` (routes 1-3), `core/promotion.py` (three patterns), and the live recovery
  commits (`accc097e6a`, `5290c9bcd2`, `03d8fc8c86`) that each fail a different predicate.
- **2026-08-14** — Specified:
  `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-landing-evidence-grammar/SPEC.md`
  (status: ready) carries the contract — CAP-1 the shared grammar artifact (home decided at story
  level within the doctor-never-imports-marshal boundary), CAP-2 doctor-side adoption, CAP-3
  marshal-side adoption. Decomposed the same day into epics.md Epic 20 (Stories 20.8–20.10,
  FR-191).

- **2026-09-09 (fleet readiness pass — operator-approved batch)** — **`specified` → `realized`,
  verified in effect rather than by ledger.** Stories 20.8–20.11 shipped
  `pyforge.core.landing_evidence` as the shared spine (no station import — the Story 14.2 precedent),
  consumed by `doctor/sources/marshal.py:53` and `marshal/core/promotion.py:58`; Spec `ready` →
  `shipped` with both frontmatter questions resolved by 20.8 (home = a `pyforge-core` module;
  pre-convention history = a SHA-prefix allowlist, `parse_recovery_commit_sha` at `:315`, never a
  rewrite of history). Live measurement the same day:
  `pyforge.doctor.sources.marshal::gather_story_status` reports *"no `done` story contradicts its
  landing evidence (898 audited, 708 with no run record (unchecked))"*; the three standing false
  positives (marshal 8-2, marshal 10-1, mason 3-7) are fixture-pinned at
  `landing_evidence.py:441/450/461` with no per-story whitelist. **Operator ruling:** accept the
  green and record the coverage number in the success signal — the green is real over the 190 stories
  that carry a run record; no coverage story is minted, because recovering run records for
  pre-dispatch-era stories is what this Dream's own non-goals forbid. Batch:
  `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`.

## 2026-09-16 — The library catalog can't see a station's own build manifest (folded from library-catalog-manifest-sync)

# The library catalog can't see a station's own build manifest

## The Dream

`docs/reference/library-llms-full.md` and its detector (`scripts/llms_full_check.py`)
promise one thing: every dependency the factory actually runs on is documented, and
drift from `pixi.toml` is caught automatically (`regenerable-factory`'s two-layer loop,
applied to this surface). That promise has a hole. Every `pyforge-*` station carries a
**second** dependency manifest the detector never reads: its own
`src/shared/packages/pyforge-<station>/pixi.toml` `[package.run-dependencies]` table —
the one `pixi-build-python` actually builds the station's conda package from. Root
`pixi.toml` only needs to re-declare a station's run-dep when there's a separate reason
to (a shared floor, a test-tooling use); most of a station's real run-deps resolve
silently through the built package's own metadata and never touch root `pixi.toml` at
all. The catalog and its detector, both scoped to root `pixi.toml` only, are structurally
blind to that whole class of already-shipped, already-used library.

The Dream is a catalog and a detector that see **both** manifests, so "documented" keeps
meaning what it says.

## Why now — measured, not feared

Found 2026-09-12 during an operator-directed audit of the catalog's own scope (recorded
in [[pyforge-unifying-strategy]]'s Realization log, "Manifest-sync gap found"). Cross-
checking all ten stations' own `[package.run-dependencies]` against root `pixi.toml`'s
active-dependency set (`scripts/llms_full_check.py::manifest_deps()`) surfaced seven
libraries that are real, directly-imported, already-shipped station code — confirmed
importable live in each station's own pixi env today — yet never appear anywhere in root
`pixi.toml` and are undocumented in the catalog:

| Library | Import name | Used directly by |
|---|---|---|
| `packaging` | `packaging` | pyforge-marshal, pyforge-mason, pyforge-warden |
| `jsonschema` | `jsonschema` | pyforge-doctor, pyforge-marshal, pyforge-warden |
| `psutil` | `psutil` | pyforge-marshal |
| `attrs` | `attrs` | pyforge-atlas |
| `packageurl-python` | `packageurl` | pyforge-warden |
| `license-expression` | `license_expression` | pyforge-warden |

(`pydantic` is a related, already-partially-documented case — a direct run-dep of
pyforge-atlas and pyforge-scribe, but the catalog's existing note only credits it as
"present transitively via pydantic-ai/fastmcp/agno." Sharpen, don't re-add.)

This is the same station manifest `tests/meta/test_manifest_sync.py` already keeps in
sync with each station's own `pyproject.toml` — the precedent for treating it as a real,
authoritative source, not a build-tool implementation detail. Story 12.1
(`spec-12-1-full-pixi-wiring-distribution-and-repo-gate-compliance`, pyforge-marshal,
done) already wired one station member (Genesis/copier) into root `pixi.toml` +
`environment.yaml` + the catalog by hand, and its own `deferred:` block flagged
pre-existing catalog drift as a known follow-up — this Dream is that follow-up, generalized
into a standing detector fix instead of another one-off hand-wiring pass.

## What it looks like when real

- The seven libraries above are declared in root `pixi.toml` (`local-recipes` plus each
  owning station's own `[feature.pyforge-<station>.dependencies]` block) and documented
  in `docs/reference/library-llms-full.md`.
- `scripts/llms_full_check.py` parses every `src/shared/packages/pyforge-*/pixi.toml`
  `[package.run-dependencies]` table alongside root `pixi.toml`, merged into the same
  active-dependency set it already builds — so a station adding a real run-dep to its own
  manifest without mirroring or documenting it fails the check the same way an
  undocumented root `pixi.toml` dep does today.
- `pixi run -e local-recipes llms-full-check` exits 0 with the merged surface, not just
  root `pixi.toml`.
- Existing behavior is unchanged for everything the detector already covers: exit codes
  (0 clean / 1 drift / 2 missing input), the "commented-out deps are out of scope" rule,
  and ghost-entry / floor-drift detection all apply identically to the newly-scanned
  manifests.

## Constraints / Non-goals

- **Not a station library-adoption decision.** This Dream is strictly the bookkeeping gap
  — libraries already adopted and working, invisible to the truth surfaces. The aspirational
  "should station X bind library Y" questions in [[pyforge-unifying-strategy]]'s "Estate
  leverage — installed, bind now" table (including `filelock`'s marshal/scribe extension)
  are a separate, already-tracked, forward-looking question and stay out of scope here.
- **No new manifest, no new convention.** The nested `pixi.toml [package.run-dependencies]`
  tables already exist and are already the real source of a station's conda run-deps
  (`tests/meta/test_manifest_sync.py` already enforces their sync with `pyproject.toml`).
  This Dream only teaches the detector to read what already exists.
- **Detector contract stays stable.** `llms_full_check.py`'s exit-code contract and CLI
  (`pixi run -e local-recipes llms-full-check`) do not change shape; the fix widens what
  it reads, not how it is invoked or what its output means.

## Kinships

[[pyforge-unifying-strategy]] (owning Dream — the finding was made and recorded there;
this satellite carries the fix so the mega-spec doesn't absorb an unrelated tooling CAP)
· [[regenerable-factory]] (the two-layer detector/reconciler loop pattern this closes a
blind spot in) · [[pyforge-marshal]] (owner; Story 12.1's pixi-wiring precedent) ·
[[pyforge-atlas]] · [[pyforge-doctor]] · [[pyforge-mason]] · [[pyforge-warden]] (the four
stations whose undocumented run-deps this Dream closes).

## Realization log

- **2026-09-12** — Seeded (operator ruling: every effort enters through the Dream-to-Code
  chain, gap-closure included). Finding made and fully investigated in
  [[pyforge-unifying-strategy]]'s Realization log ("Manifest-sync gap found"); this
  satellite Dream carries the fix itself so it lands as a scoped `pyforge-marshal` story
  rather than a new CAP inside the Unifying mega-spec. Next act: `bmad-spec` derives
  `spec-library-catalog-manifest-sync` under `pyforge-marshal`.
- **2026-09-12 (spec + process correction)** — `bmad-spec` derived `spec-library-catalog-manifest-sync`
  (CAP-1, CAP-2; `status: ready`, zero open questions — every fact confirmed live before
  authoring). CAP-1/CAP-2 were then hand-implemented directly from the Spec with **no Story
  minted and no sprint-status ledger entry** — caught mid-turn by the operator. Reconciled
  same-turn: Epic 36 (Stories 36.1, 36.2) minted in `pyforge-marshal/epics.md`; `sprint_plan.py
  generate` + `sprint-ledger-sync` + `story-status-check` landed both `done` in the tracked
  ledger. `AGENTS.md` § Dream-first workflow gained item 5 and `CLAUDE.md`'s Dream-first
  paragraph gained a matching clause, both citing this incident, so a `ready` Spec is never
  again treated as license to skip decomposition.
- **2026-09-12 (realized)** — CAP-1 verified: seven libraries (the original six plus `filelock`,
  a CAP-1 scoping miss found and fixed the moment CAP-2's own scan went live — see Story 36.1's
  own note) mirrored into root `pixi.toml` and documented in the catalog; `llms-full-check`
  clean (352 active deps / 320 catalog entries) and `pixi lock --check` confirms every floor
  was already resolved, no new solve. CAP-2 verified: `scripts/llms_full_check.py` now scans
  every station's own nested `pixi.toml [package.run-dependencies]`, proven by a new
  `tests/scripts/test_llms_full_check.py` (5 tests, synthetic-fixture regression coverage) and
  a clean run against the real repo. Both Stories `done`; Dream `dreamt → realized`.

## 2026-09-16 — Marshal Dependency-Aware Dispatch — the fleet orders its own backlog and forgets nothing it kills (folded from marshal-dependency-aware-dispatch)

# Marshal Dependency-Aware Dispatch

## The Dream

Every station's backlog already carries its own dependency graph — `epics.md`'s
`Deps:` line on every story. Nobody reads that graph but a human (or an agent
standing in for one), by hand, right before dispatching, every single time.
`factory drain --mode drain_to_zero` walks the tracked `sprint-status-ledger.yaml`
in raw ledger order — an order that has no relationship to `Deps:` — and gets away
with it only when raw order and dependency order happen to coincide. When they
don't, a station can dispatch a story whose hard dependency isn't `done` yet,
burning a worktree and a session on a run that was never eligible to succeed.

Marshal already has a caller-supplied escape hatch for this — `--stories` (Story
22.11, FR-193 CAP-10) lets a human hand it an explicit order. But a human
deriving that order is exactly the busywork a dependency-aware `factory drain`
should be doing on its own. The dream is a drain that reads `Deps:` the same way
it reads `sprint-status-ledger.yaml`, computes a valid topological order itself,
and only falls back to raw ledger order for stories with no unmet dependency
either way. `--stories` stays — as an explicit override, not the only path to a
correct sequence.

The second half of the same dream: **a run marshal itself ends should never be
indistinguishable from a run that genuinely failed.** Today, killing a dispatch
session (SIGTERM, from outside marshal's own ladder — an operator reprioritizing,
not a story going wrong) gets journaled as `MRS-DRAIN-005: ended 'failed' by git
and process facts`, and that story is "never auto-retried, never forced past" by
`--stories` or `drain` again. The only way back in discovered live: a bare
`factory dispatch <slug> <story>` call sidesteps `drain`'s own journal check
entirely and just launches fresh — an inconsistency, not a sanctioned unblock
path. If a bare dispatch is safe to retry with, `drain`/`--stories` should offer
the same retry without requiring the operator to know the workaround. And the
operator-initiated case (a deliberate stop, not a story that broke) should be
distinguishable from a genuine failure in the first place, so it doesn't cost the
story a strike it didn't earn.

## What is real — the incident this Dream is written from

2026-08-31, this session, both findings hit inside twenty minutes of each other:

**Finding 1 — no dependency-derived ordering.** Asked to sequence `pyforge-atlas`'s
18 remaining backlog stories (Epics 21–23), the only way to get it right was to
open `epics.md`, read every `Deps:` line by hand, and topologically sort 18 nodes
myself — catching a real risk in the process: `23.9` depends on `22.1`, a
cross-epic dependency `drain_to_zero`'s ledger-order walk has no way to know
about. The already-running `drain_to_zero` (no `--stories`) had started on `21.7`
— correct, but by luck of ledger order, not by design.

**Finding 2 — no sanctioned retry after a killed-not-failed run.** Restarting
`pyforge-atlas` with the derived explicit order (`marshal factory dispatch
pyforge-atlas --stories 21.7,21.8,...`) was refused:

```
finding MRS-DRAIN-005: station 'pyforge-atlas': story '21.7' is blocked --
the last dispatch of '21.7' ... ended 'failed' by git and process facts.
It stays in the backlog, is never auto-retried, and is never forced past;
re-run with --mode skip_on_blocked to move on to this station's next story.
```

`skip_on_blocked` is the wrong tool here — it moves *past* `21.7`, and `21.8`
depends on `21.7`. The only way back in was a bare `marshal factory dispatch
pyforge-atlas 21.7` (no `--stories`), which provisions fresh and launches without
ever consulting the journal `drain` had just refused against. It worked because
it happened to skip the check, not because marshal offered a real "yes, retry
this" path.

The same session then surfaced the stakes of getting this wrong silently: killing
`pyforge-atlas`'s `21.7` dispatch cost nothing (the worktree held only a
`status: in-progress` bookkeeping stamp on the spec file). Killing
`pyforge-marshal`'s `28.2` dispatch minutes later cost a **647-line, 11-file,
fully uncommitted diff** — real implementation work, parked in
`.worktrees/dispatch-pyforge-marshal-28.2` with no marshal-native recovery path
beyond "the worktree still has the files, go look." A story a few minutes into a
kill and a story deep into real work get exactly the same `MRS-DRAIN-005` verdict
today — there's no distinction between "cheap to redispatch fresh" and "this
diff needs to be preserved before anything touches this worktree again."

## What this Dream asks for

**A. Dependency-derived ordering, by default.**
- `factory drain` (no `--stories`) parses each backlog story's `Deps:` line from
  the tracked `epics.md` (or an equivalent structured source, if `Deps:` moves to
  frontmatter/YAML — see Gates) and computes a topological order before
  dispatching, instead of walking `sprint-status-ledger.yaml` raw order.
- Cross-epic dependencies (`23.9` → `22.1`, in this incident) are honored the same
  as same-epic ones — the graph doesn't stop at epic boundaries.
- Optional stories (marked `Optional: yes`) are included in the computed order
  by default, not silently dropped — matching this session's own ask ("include
  the optional vizro identity pages"). Whether to offer an opt-out flag to
  exclude them is a Gate below.
- `--stories` remains as an explicit override for when an operator wants a
  different order than the derived one (partial runs, deliberate re-sequencing,
  a story the graph doesn't know about yet).
- Ties (multiple stories with no unmet dependency between them) fall back to
  ledger order, so the algorithm is deterministic and doesn't invent an ordering
  preference the ledger didn't express.

**B. A sanctioned retry path that survives an operator-initiated stop.**
- Distinguish, in the journal, *why* a dispatch ended: a genuine failure
  (verdict-gated, review-rejected, crashed) vs. an external stop (SIGTERM from
  outside marshal's own ladder) vs. a clean landing. `MRS-DRAIN-005` today
  collapses all non-success endings into one "failed by git and process facts"
  verdict.
- A story stopped externally (not failed) should be retryable through the normal
  `drain`/`--stories` path without a workaround — either it doesn't get journaled
  as `failed` in the first place, or `drain`/`dispatch --stories` grows an
  explicit, documented "clear and retry" affordance that does what the bare
  `dispatch <slug> <story>` workaround does today, on purpose instead of by
  accident.
- Before any retry (sanctioned or the existing workaround) touches a worktree
  that already has uncommitted changes, surface that fact loudly — size of diff,
  files touched — rather than silently letting a fresh dispatch clobber or ignore
  real work. The gap this incident exposed: nothing marshal-native flagged that
  `28.2`'s worktree held 647 real lines while `21.7`'s held three bookkeeping
  ones; a human had to `git status`/`git diff --stat` both by hand to find out.

## Guardrails — what this Dream refuses to do

- Does not touch the actual kill ladder (idle-strand detection, budget-ceiling
  stop/retry/defer) — that machinery already exists and works; this is about
  ordering *before* dispatch and recovery *after* an external stop, not about
  when marshal itself decides to stop a story.
- Does not weaken `MRS-DISP-011` (refusing redispatch while a session process is
  genuinely still alive) — that check is correct and stays.
- Does not make retry automatic/silent. A previously-killed story getting
  redispatched should still be a visible, journaled event — the ask is a
  sanctioned path, not a hidden one.
- Does not invent a second graph/ordering engine — if `Deps:` parsing already
  exists anywhere in the codebase (`bmad-sprint-planning`'s readiness gate, or
  the planning-graph work in Epic 28/Story 28.9), this dream extends that, it
  doesn't duplicate it.

## Gates and open qu

*(truncated in fold; original file remains archived)*


## Realization log

- **2026-08-31** — Seeded from a live dispatch-ordering/retry incident and folded into
  `spec-marshal-token-economy` as CAP-14..CAP-17 → marshal Epic 28 Stories 28.12–28.15
  (`5c947eebec`; that Spec's `sources` names this Dream).
- **2026-09-01** — The addenda were contracted in `spec-marshal-drain-self-resolution`
  (`e5e31c228d`: CAP-1..6 / Stories 28.18–28.23, the drain self-heal residue; `14ac9ed408`: CAP-7 /
  Story 28.24, supervisor finalizes when the harness cannot run shell), with
  [`marshal-drain-self-resolution.md`](marshal-drain-self-resolution.md) archived in place as a
  pointer. `spec-marshal-verify-fail-terminalization` (status `ready`) also references this Dream.

- **2026-09-09 (fleet readiness pass — operator-approved batch)** — **`specified` → `realized`,
  verified in effect.** This Dream is contracted across three Specs and needs no fourth; read the
  contract map here, not in any one Spec:
  A dependency-derived ordering → `spec-marshal-token-economy` CAP-14 (Story 28.12, `done`);
  B sanctioned retry after an external stop → token-economy CAP-15 (28.13, `done`);
  C auto-derived effective surface → token-economy CAP-16 (28.14, `done`);
  D scope-violation enforcement mode → token-economy CAP-17 (28.15, `done`);
  E verify-fail terminalization → `spec-marshal-verify-fail-terminalization` CAP-1..3 (28.17, `done`);
  F drain self-resolution → `spec-marshal-drain-self-resolution` CAP-1..7 (28.18–28.24, `done`).
  **Two consequences to state plainly.** Unlike their Epic-28 siblings, C and D need no declaration
  to take effect: `core/gate.py:348-423` auto-derives the station surface when no `[epic_surfaces]`
  entry exists, and `core/policy.py:609` sets `scope_violation_mode = "warn"` as the DEFAULT — so
  **AD-49's non-waivable `SCOPE_VIOLATION` refuse is no longer the fleet default**; every station runs
  advisory scope containment unless it declares `hard`. That is the intended 2026-08-31 operator
  decision, but § D of this Dream still describes it as an opt-in (*"default `hard` — today's
  non-waivable refuse"*), which is now false against `core/policy.py:609`. And C composes with Story
  28.16 into a no-op for within-station fan-out: two same-station stories share an auto-derived
  surface by construction, so the pairwise wave test refuses (marshal **Story 33.8**). Batch:
  `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`.

## 2026-09-16 — A GitHub PR-merge branch from one project never masquerades as a same-numbered story in another (folded from marshal-land-cross-project-story-key-collision)

# A GitHub PR-merge branch from one project never masquerades as a same-numbered story in another

## The Dream

`marshal land`/`marshal deploy batch-pr`'s "already landed" short-circuit
(`core/promotion.py::merged_story_keys`) confirms only that a project's OWN
story actually merged into `main` — never a same-numbered story from a
completely different project that happens to share this one repo's history.
Today it does not: `extract_story_key_from_github_merge_subject`, the
second of the function's three merge-subject patterns, extracts a
`StoryKey` from ANY GitHub PR-merge branch's final path segment with no
check that the branch actually belongs to the `project_slug` being
queried — the exact cross-project collision protection its own sibling
pattern (`extract_story_key_from_bmadloop_merge_subject`) already carries,
and whose docstring names the identical risk this repo's shared history
creates.

## What is real

Confirmed live, 2026-08-15: `marshal land pyforge-mason` reported story
`4.2` (`4-2-manifest-discovery`) as `already_landed: true` / `merged: true`
immediately after wave discovery — even though `origin/main` demonstrably
does not contain that commit (`git merge-base --is-ancestor a723618553
main` → not an ancestor; `git log main --grep="4-2\|manifest-discovery"`
finds nothing). The branch `loop/pyforge-mason` still exists, un-retired,
holding the real un-promoted merge commit — so the false positive was
caught before anything was lost, but `marshal land` reported success on a
wave that never landed.

Reproduced directly against `promotion.merged_story_keys` with
`project_slug='mason'` and real `main` history (2,898 commit subjects): it
returned `4.2` as an "already landed" mason key, plus several other
clearly-bogus mason keys (`4.5`–`4.10`, `5.2`–`5.6`, `6.1`–`6.5` — several
of which don't correspond to any real mason story in mason's own
`epics.md`) and one nonsensical `2026.8`.

Traced each to its exact source commit:

- `4.2` comes from **PR #274**, branch
  `marshal/4-2-teardown-reachability-spec-recovery` — a **marshal**
  story, unrelated to mason. `extract_story_key_from_github_merge_subject`
  (`core/promotion.py:146`) matches `_GITHUB_MERGE_SUBJECT_RE`, takes the
  branch's final `/`-separated path segment
  (`4-2-teardown-reachability-spec-recovery`), and hands it straight to
  `normalize()` with **no check at all** that the branch's leading
  `marshal/` segment matches the `project_slug` being queried — that
  segment is simply discarded.
- `2026.8` comes from **PR #441**, branch `2026-08-11-Pixi-v0.76.2` — a
  routine dependency-bump branch with no story association whatsoever.
  Same code path: `normalize()` accepts `2026-08` as a syntactically-valid
  `<epic>-<story>` pair with no plausibility bound.
- `_classify_merge_subject` (`core/promotion.py:173`) documents, in its
  own docstring, that `project_slug` "scopes the bmad-loop pattern
  **only**" — the GitHub PR-merge pattern was never given the same
  scoping its sibling pattern's own docstring says this shared-history
  repo requires.

`merged_story_keys` backs both `marshal land`'s and `marshal deploy
batch-pr`'s already-landed short-circuit, AND
`run_reconcile_completions`/`_reconcile_open_intents`'s "confirmed"
classification — so the same false positive can silently short-circuit
landing (and mis-confirm open intents) for ANY project whenever another
project's branch history carries a numerically-matching `<epic>-<story>`
segment, which is routine across 8 concurrently-active projects sharing
one repo.

**This is a known, previously-deferred gap, not a fresh discovery** —
`implementation-artifacts/deferred-work.md` (Tier-3) already carries two
entries against this exact function (2026-08-10, review passes 2 and 4,
Blind Hunter + Edge Case Hunter independently): it names the missing
`project_slug` scoping, measures it live against `main`'s then-2,353
commit subjects (mason/doctor/scribe each returning ~30 keys, "most of
them another station's"), and explicitly defers a full fix as "a dedicated
story should extend the one owner to read both shapes." `cli/status.py`'s
own `_merged_keys_for_slug` already treats a present key as "STRONGER
evidence, not proof" specifically because of this known contamination —
but `cli/land.py`'s already-landed short-circuit does NOT hedge at all,
treating `all(key in already_landed_keys ...)` as definitive. This Dream
is the first time the gap has produced a concrete, consequential failure
(a real false "already landed") rather than staying a bounded, theoretical
risk — and scopes a fix narrower than the deferred entries' own "read both
shapes" framing: only closing the cross-project false-positive hole in the
EXISTING recognized shape, not adding new shape recognition (that larger
work stays exactly as deferred).

## What it looks like when real

- `extract_story_key_from_github_merge_subject`'s branch-segment match is
  scoped to `project_slug`, the same way
  `extract_story_key_from_bmadloop_merge_subject` already is — a branch
  must actually belong to the project being queried (its own
  project-prefix convention, e.g. `marshal/…`, `land/mason-…`) before its
  trailing `<epic>-<story>` segment is trusted as that project's own key.
- A syntactically-valid-looking `<epic>-<story>` pair from an unrelated
  branch (a date stamp, a version bump) no longer masquerades as a real
  story key for ANY project.
- `marshal land pyforge-mason` reports `already_landed` only for waves
  genuinely reachable from `main` under mason's own key space — re-run
  live against the current mason wave (`4.2`) as the fix's own acceptance
  evidence: it must report a fresh landing, not a no-op.
- `deploy batch-pr`'s identical short-circuit and
  `run_reconcile_completions`'s "confirmed" classification inherit the fix
  automatically, since both call the same `merged_story_keys`.

## Constraints

- Must not regress the EXISTING single-project story-key extraction this
  pattern already gets right for the common case (a project's own
  `land/<slug>-<epic>-<seq>...` / `<slug>/<epic>-<seq>...` branches) —
  every currently-passing `test_promotion.py` case for
  `extract_story_key_from_github_merge_subject` must still pass.
- The fix must work for BOTH observed real branch-naming conventions in
  this repo's own history: `<slug>/<epic>-<seq>-<desc>` (e.g.
  `marshal/4-2-teardown-...`) and `land/<slug>-<epic>-<seq>-<desc>` (e.g.
  `land/mason-4-3-mason-environment-lock`) — scoping by a bare
  prefix-equals-`project_slug` check would silently break the second,
  more common landing-branch shape.
- Pure-function discipline (AD-4) holds: no I/O, no subprocess, no
  `pathlib` methods added to `core/promotion.py`.

## Non-goals

- Not adding a plausibility bound on raw epic/story numbers (the
  `2026.8` symptom) — that is a `core.identity.normalize` concern, a
  different function with its own contract; scoping the GitHub pattern to
  `project_slug` already prevents THIS bug's cross-project false positive
  without touching `normalize`.
- Not auditing every OTHER caller of `merged_story_keys` for downstream
  consequences of past false positives (e.g., whether
  `run_reconcile_completions` already mis-confirmed some open intent
  using a stale cross-project key) — scoped to the extraction bug itself,
  not a forensic audit of everything it may have already touched.
- Not landing mason's actual `4-2` wave — that is normal fleet operation
  once `marshal land` can be trusted again, not part of this fix.

## Kinships

[[pyforge-marshal]] (the station; `core/promotion.py` is its own core
module) · [[marshal-status-harness-run-id-poisoning]] (a sibling "trusted
a field that turned out to lie" bug, found the same day) ·
[[bmad-loop-liveness-footgun]] (same family).

## Realization log

- **2026-08-15** — Dream captured. Found live while attempting to land
  mason's story `4.2` per this repo's own "land proactively" convention —
  `marshal land` reported false success. Root

*(truncated in fold; original file remains archived)*


## 2026-09-16 — Marshal-driven landings are provably Marshal-driven (folded from marshal-land-merge-subject)

# marshal land renders a detectable merge subject

## The Dream

Every landing route Marshal itself drives — `bmad-loop`, `deploy land-story`,
`marshal land` — is detectable from its merge-subject shape alone, the same
way `deploy land-story` already renders `identity.render_merge_subject`'s
templated form. No Marshal-driven merge is ever mistaken for a human's plain
GitHub PR merge again.

## What is real (the core)

- `deploy land-story` already renders the templated subject
  (`identity.render_merge_subject`), confirmed live — `core/promotion.py`'s
  `marshal_native_merged_keys` classifies it correctly.
- `core.promotion.merged_story_keys` / `marshal_native_merged_keys` already
  classify merge subjects into templated / bmad-loop-native / generic
  GitHub-PR patterns — the classification machinery exists and is correct;
  only one of Marshal's own landing routes fails to render a subject it can
  recognize.

## The frontier

- **`marshal land` (`cli/land.py::run_land`)** defaults to
  `landing_merge_strategy: "merge"` (`core/policy.py:335`) and calls
  `forge.merge_pr`, letting GitHub write its own auto-generated subject —
  byte-identical in shape to a human's plain PR merge. Discovered
  2026-08-12 during [[pyforge-marshal]] Story 5.9's review pass: of the keys
  `merged_story_keys` finds outside the templated/native patterns, the
  large majority are `marshal land` landings, not genuine `bmad-quick-dev`
  sessions — every consumer of this classification (fleet-picture,
  `marshal status`, `dashboard-drift-check`, and 5.9's own
  `reconcile-completions`) currently mislabels them.
- Fix: change `marshal land` to render the templated subject via
  `identity.render_merge_subject`, matching `land-story`. Once landed,
  `marshal_native_merged_keys` classifies `marshal land` merges correctly
  going forward with no further change needed anywhere downstream —
  including 5.9's own `not-loop-native` bucket, which narrows back toward
  genuine quick-dev sessions automatically.
- Not a prerequisite for 5.9, which ships today with the coarser
  `not-loop-native` label (git alone cannot currently tell `marshal land`
  and `bmad-quick-dev` apart, so 5.9 reports the honest, joint fact).

## Realization log

- **2026-08-12** — Dream seeded from [[pyforge-marshal]] Story 5.9's review
  pass 2 escalation (intent-gap finding 1): `marshal_native_merged_keys`'s
  own detection is correct, but `marshal land`'s merge strategy defeats it
  for its own landings.
- **2026-08-14** — Realized — Story 5.10 (FR-187) shipped: `cli/land.py` renders the AD-24 templated subject through `ForgePort.merge_pr`. Status flipped and FR-187 backfilled into the PRD by the 2026-08-14 audit.

## 2026-09-16 — Marshal trusts the environment it launches into — until it silently doesn't (folded from marshal-launch-environment-integrity)

# Marshal trusts the environment it launches into — until it silently doesn't

## The Dream

`factory dispatch` and `factory spin` both promise the same shape: launch a
detached, unattended dev session and return promptly. Neither checks, before
launching, that the environment it is about to hand a story to is actually
correct. Four times in one recovery session (2026-09-10), that assumption was
silently false, and every one of the four failed the same way — minutes into
a run, with **zero diagnostic pointing back at the cause**. The operator had
to trace each one by hand through `bmad-loop diagnose`, raw session logs, or
an eyeballed YAML diff, because the tool itself reported `verdict: ok` or
`verdict: clean` right up until the story quietly produced nothing.

**What "environment" means here, concretely, and what went wrong with each:**

1. **Harness/model pairing.** `factory dispatch` resolves a `harness_preference`
   and a `model_tier_map` independently, from two different policy layers. On
   four of eight stations (doctor, herald, mason, scribe) the model map named a
   Cursor-only model (`composer-2.5-fast`) while the harness order still
   resolved to `claude` — a pairing Claude Code's own CLI refuses outright
   (`"composer-2.5-fast" isn't described by this version's model catalog`).
   Every dispatch to these four stations died in seconds. The other four
   stations already carried a `harness_preference = ["cursor"]` override
   with a comment explaining exactly this failure mode, discovered
   independently on 2026-09-01 — the fix was never propagated fleet-wide.
   **Fixed 2026-09-10:** mirrored the override onto the remaining four
   stations' `marshal-policy.toml` (`fix/marshal-harness-preference-4-stations`).

2. **The multiplexer binary itself.** `factory spin` needs `tmux` on `PATH` to
   launch `bmad-loop run`'s session. After a host reset, `tmux` was gone
   entirely — `bmad-loop mux` reported no available backend on this platform.
   `factory spin` did not surface this: it launched, the supervisor attached,
   and `bmad-loop`'s own engine decided there was nothing to do and completed
   in under 20ms with "0 done, 0 deferred, 0 escalated" — a clean exit, not an
   error. Every mason/scribe spin attempt looked identical to "no eligible
   stories" from the caller's side. **Fixed 2026-09-10:** `tmux` added as a
   `pyforge-marshal` pixi dependency (linux-64/osx-arm64-scoped, conda-forge
   doesn't ship it for win-64) instead of relying on a system package outside
   pixi's control (`fix/marshal-tmux-dependency`).

3. **Two unsynced views of the same fact.** `factory dispatch`/`bmad-build-auto`
   read the tracked `sprint-status-ledger.yaml` directly. `factory
   spin`/`bmad-loop` read a separate, gitignored Tier-3
   `implementation-artifacts/sprint-status.yaml`. Nothing kept them in sync
   except `bmad-sprint-planning`'s own one-shot `generate` (epics.md →
   Tier-3, run once, never re-run automatically) and `sprint-ledger-sync`
   (Tier-3 → tracked ledger, "run it when a story lands," also never
   automatic). A station's Tier-3 copy sat stale for **four days**, missing
   two whole epics, while spin reported "0 done" every run with nothing to
   contradict it. **Fixed 2026-09-10:** `marshal refresh` now regenerates
   every station's Tier-3 feed from its `epics.md` as a fourth checked step,
   independent of git state, and `factory <slug> preflight` compares the
   ledger's actionable set against Tier-3 and WARNs on drift
   (`MRS-PREFLIGHT-016`) instead of letting spin silently see fewer stories
   than dispatch does (`feat/marshal-sprint-status-sync-and-drift-detection`).

4. **The promotion tool's own regression guard has a blind spot.** Running
   the newly-fixed Tier-3 regeneration surfaced a second, independent bug:
   `scripts/promote_sprint_status.py`'s regression guard (and its
   `--repair-feed` counterpart) only detects the specific transition
   `done → backlog`. A tracked-`done` story whose Tier-3 twin held a stale
   `blocked` — genuinely completed, confirmed by its own spec's `status:
   done` frontmatter and a landed commit — passed through undetected and
   silently overwrote the ledger's correct `done` with the stale `blocked`.
   Caught only because the operator eyeballed the diff before committing.
   **Specced 2026-09-10** (`spec-sprint-status-promotion-regression-guard`);
   fix in progress the same session — widen both the refusal and repair
   paths from "feed says `backlog`" to "feed says anything other than
   `done`," with `20-4`'s live regression as the reproduction case.

5. **The operator's own fleet report trusted a stale verdict over a live
   one.** `scripts/fleet_picture.py` reads `marshal status`'s per-station row,
   which carries `dispatch_verification_verdict`/`dispatch_verification_
   failed_gate` fields that persist until the NEXT `factory dispatch` run
   overwrites them — they are not cleared when a different engine (`factory
   spin`) starts running on the same station. Scribe's row still carried a
   `refused` `MRS-GATE-007` verdict from a dispatch attempt on 2026-08-31
   (10 days stale) when a brand-new, healthy `factory spin` session
   (confirmed alive via `bmad-loop diagnose`, genuinely `dev-running`) was
   labeled **STUCK** in both the station-state cell and the ATTENTION block
   — the exact same pattern as findings 1-4: two pieces of state (a live
   process fact and a recorded verdict) sitting in the same JSON row,
   un-cross-checked. **Fixed 2026-09-10:** both call sites now require
   `dispatch_phase is not None` (only ever set while dispatch is genuinely
   the live engine) alongside the refused verdict before trusting it
   (`fix/fleet-picture-stale-dispatch-verdict`). **Known gap, not yet
   built:** the `station_state()` fix has direct unit coverage; the
   ATTENTION-block site's own ~10-line `needs.append` branch inside
   `main()` does not — it would need `subprocess.run` mocked the way
   `test_fleet_picture_verification_staleness.py` already mocks
   `marshal status`'s JSON output for a different ATTENTION probe in the
   same file, rather than driving the real fleet's own ledger state.

**The pattern underneath all five.** Every one of them is a silent-success
failure mode: the tool's own reported verdict (`ok`, `clean`, `0 done`,
`STUCK`) gave no signal that anything was wrong, and each required manual
archaeology (`bmad-loop diagnose`, raw stderr, an eyeballed diff, a raw
`marshal status --format json` dump) to even locate, let alone fix. Four of
the five are now closed with a **loud** failure, an automated repair, or a
cross-check against live process state in their place; the fourth
(`promote_sprint_status.py`) landed the same session too. What remains open,
found in the same session and not yet decomposed into a story:

- **The ATTENTION-block test-coverage gap** named in finding 5 above — the
  fix is live and correct (confirmed against the real fleet), but the
  `needs.append` branch inside `main()` has no dedicated unit test the way
  `station_state()`'s does.

- **No mid-session checkpointing.** A dispatch or spin session that crashes
  (terminal/IDE crash, not a code failure) loses every uncommitted change in
  its worktree unless the *operator* notices and manually
  `git add -A && git commit`s a recovery checkpoint before relaunching. This
  session hit that path **four separate times** (doctor 21.1 twice, herald
  19.1, steward 48.6 twice) across two terminal crashes, and every recovery
  was done by hand, live, under time pressure — real work (a completed
  story, hundreds of lines of a WebSocket-streaming feature) sat one
  `git worktree` cleanup away from silent loss each time. Marshal's own
  supervisor already watches these sessions for completion; it does not
  periodically checkpoint their in-flight worktree state.
- **A crashed session and a genuinely failed one look identical to the
  ledger.** When a dispatch session dies (crash, kill, o

*(truncated in fold; original file remains archived)*


## Realization log

- **2026-09-10** — Dream captured retroactively from a single long recovery
  session that hit all four closed findings plus the two open ones above, in
  order, while draining doctor/herald/mason/scribe/steward backlogs after two
  terminal crashes. Three of four environment-integrity findings shipped the
  same session (`fix/marshal-harness-preference-4-stations`,
  `fix/marshal-tmux-dependency`,
  `feat/marshal-sprint-status-sync-and-drift-detection`); the fourth
  (`promote_sprint_status.py`'s regression guard) is specced and mid-fix. The
  two resilience findings (no mid-session checkpoint, crashed-vs-failed
  indistinguishable to drain) are captured here, not yet decomposed into
  marshal epics.md stories — next step.
- **2026-09-10 (later, same session)** — `promote_sprint_status.py`'s
  regression guard fix landed
  (`fix/promote-sprint-status-done-strictly-senior`); the three resilience
  findings decomposed into marshal **Epic 34** (Stories 34.1-34.3, fully
  specced and dispatch-ready). A fifth environment-integrity finding
  surfaced immediately after, from the operator's own next fleet-picture
  check: `fleet_picture.py` mislabeled a healthy live spin as STUCK off a
  10-day-stale dispatch verdict — same silent-success pattern as the first
  four. Fixed the same session
  (`fix/fleet-picture-stale-dispatch-verdict`); the fix itself has direct
  unit coverage, but its ATTENTION-block sibling site does not — decomposed
  as **Story 34.4** below.
- **2026-09-11** — Retroactive `spec-marshal-launch-environment-integrity`
  authored. This Realization log had claimed `status: specified` and full
  decomposition since 2026-09-10, but no dedicated Spec file was ever
  produced — `dream-chain-check`'s INV-1 correctly flagged the gap when the
  operator asked whether any Dreams still needed specing. Epic 34
  (Stories 34.1–34.4) was already fully `done` in the tracked ledger at
  that point (confirmed via real merge commits: `local-recipes#1153`,
  `#1158`, `55153c8`/`dcda31b8cb`, `local-recipes#1145`/`02237d61b9`) — the
  new Spec documents what shipped rather than specifying new work. Status:
  specified → realized. `epic-34`'s own stale `in-progress` ledger stamp
  (all 4 stories `done` underneath it) corrected to `done` in the same
  pass.

## 2026-09-16 — Parallel dispatch fan-out when dependencies and surfaces are disjoint — without breaking the zombie guards (folded from marshal-parallel-dispatch-fanout)

# Parallel dispatch fan-out when dependencies and surfaces are disjoint

## The Dream

Today marshal's factory drain is **fast across stations, serial within one**.
`pyforge-marshal` and `pyforge-atlas` can run at the same time — Story **22.5**
(FR-193 CAP-5) explicitly allows that. But on a **single station**, the same
story forbids a second dispatch the moment *any* story is judged **live**, even
when the two stories share no dependency edge, touch no overlapping frozen
surface, and would land on separate worktrees anyway. Epic 28's eight-story
remainder and atlas's sixteen-story workbook-retirement path therefore spend
wall-clock time waiting in a queue that dependency math says could have been a
**wave** — not because the harness cannot run two cursor sessions, but because
22.5's mutex is intentionally coarse.

**Story 28.12** (backlog) will fix *order*: derive a topological sequence from
`Deps:` instead of raw ledger order or hand-maintained
`fleet-drain-queue.yaml`. This Dream fixes *width*: among stories that are
**simultaneously eligible** (dependencies satisfied), launch **more than one**
when their **declared surfaces are provably disjoint**, up to a policy cap,
while leaving Story **22.2**'s completion judge untouched — every story still
owns its own session PID, supervisor, journal run, worktree, and git-fact
verdict. A zombie on story A must never block story B when B's surface cannot
 collide with A's WIP and B does not depend on A.

The aspiration is not "turn marshal into a thread pool." It is **wave scheduling**:
each drain cycle computes a **ready set** (deps met, backlog, not done), partitions
that set into **parallel-safe batches** (pairwise surface-disjoint under the
existing AD-27 narrow-only combinator), launches one detached dispatch per batch
member, waits for the wave to **terminalize** (complete, failed-with-preserve, or
verified land) before advancing dependents — and journals the wave explicitly so
`fleet-picture` and `marshal status` show *which* stories were intentionally
in flight together, not an accident of timing.

## What is real — the incident this Dream is written from

**2026-09-01**, running Epic 28 and atlas drains in parallel:

- **Cross-station parallelism worked.** Marshal 28.7 and atlas 23.1 ran as
  separate stations — exactly what 22.5 allows.
- **Within-station parallelism did not.** The operator asked whether independent
  Epic 28 stories (or atlas stories with satisfied deps) could fan out together.
  Answer: **no** — `station_in_flight_conflict()` refuses *any* second story on
  the same station while *any* journal row is `LIVE`, with `MRS-DISP-021`.
- **`--stories` is a serial chain, not a fan-out.** Story 22.11 chains one
  dispatch at a time via the fleet supervisor; it does not interpret the list as
  a parallel batch.
- **22.2 zombie guards did their job — painfully.** Killing Claude mid-28.7 left
  four dirty paths in `.worktrees/dispatch-pyforge-marshal-28.7`. Verdict stayed
  `LIVE` ("still live by git facts") even with no process — correct for *that*
  story, but it also blocked the entire station slot until verify/preserve/land
  reconciled. The Dream must **not** loosen "uncommitted progress = live for the
  story that owns it"; it must stop that live story from blocking **unrelated**
  stories.
- **28.12 is ordering-only.** Topological sort answers "what next in sequence";
  this Dream answers "what else **now**, beside the head of the queue."

Related dreams already in flight:

- [`marshal-dependency-aware-dispatch.md`](marshal-dependency-aware-dispatch.md)
  — ordering (28.12), sanctioned retry (28.13), scope automation (28.14/28.15).
- [`marshal-single-story-dispatch.md`](marshal-single-story-dispatch.md) — the
  validated pattern; addendum already named "parallel when surfaces are disjoint"
  as an open Spec question.
- [`horizontal-run-concurrency.md`](horizontal-run-concurrency.md) — bmad-loop
  `max_parallel` stub; **this Dream is factory-dispatch fan-out**, not in-loop
  Phase 5.

## What this Dream asks for

### A. Wave scheduler beside serial drain (opt-in, default unchanged)

- **`factory drain` / `dispatch --stories` gain an explicit parallel mode**
  (name TBD: `--parallel`, `--max-in-flight`, or policy `dispatch.max_parallel`
  per station) — **default remains 1** so today's serial semantics are
  byte-identical when unset.
- **A wave** = the set of stories launched together in one fleet-supervisor cycle
  on one station, each with the existing one-worktree-one-branch provisioning
  (`dispatch/<station>/<story>`).
- **Between waves:** the supervisor waits until every member of the current wave
  reaches a **terminal dispatch outcome** (completed land, failed with preserve,
  or blocked with explicit operator classification) before computing the next
  ready set. Dependents never start in the same wave as an unfinished dependency.

### B. Ready set from the dependency graph (28.12-adjacent, shared hook)

- Reuse the **same `Deps:` graph** Story 28.12 will introduce for ordering:
  a story is *ready* when every declared dependency is `done` on the tracked
  ledger (cross-epic edges included).
- Among ready stories, **28.12 ledger-order tie-break** still applies when
  choosing batch members — parallelism does not invent a second preference.

### C. Surface-disjointness as the parallel safety proof

- Two stories may share a wave **only if** their **effective frozen surfaces**
  (AD-27: `policy_surface ∩ spec_surface`, same machinery as `MRS-GATE-007`) are
  **pairwise disjoint** — path-level, not heuristic.
- **Overlap within a station is a hard refusal** for that pair (stronger than
  today's cross-station `MRS-DISP-022` advisory). Disjointness is the proof that
  parallel landings cannot fight over the same files.
- Stories with **empty or unknown surface** do not fan out with others until
  surface is declared — conservative default, same posture as scope gates today.

### D. 22.2 zombie guards preserved per story, relaxed per station

**Do not change** `judge_dispatch_completion()`:

```text
LIVE  := session_alive OR has_git_progress(for this story's worktree)
FAILED := session dead AND no git progress AND not merged
```

**Do change** `station_in_flight_conflict()`:

| Today (22.5) | This Dream |
|---|---|
| Any `LIVE` story blocks **all** other stories on the station | Story X blocks story Y only if **Y depends on X** (transitive) **OR** surfaces overlap **OR** same story key (existing `MRS-DISP-011`) |
| Zombie with WIP blocks unrelated backlog | Zombie with WIP blocks **only** dependents and surface colliders |

Mechanically: walk in-flight journals; for each candidate next story, refuse
only on **dependency** or **surface intersection** or **same-key redispatch** —
not merely "something else is live."

Preserve capture (`dispatch-preserve` patch on failed kill) stays **per story**;
parallel story B's landing path never resets story A's worktree.

### E. Observability and operator trust

- Journal a **`dispatch-wave`** intent/outcome: member story keys, computed
  disjointness evidence (surface hashes or path lists), cap applied, refused
  candidates with reason (`dep-unmet`, `surface-overlap`, `cap`).
- `marshal status` / `fleet-picture` show **in-flight count per station** and
  wave id — not a flat "28.7" that hides a second concurrent 28.10.
- Fleet-wide advisory lock (two campaigns racing one station) **unchanged**.

## Minimal design sketch (28.12-adjacent)

```text
each supervisor tick:
  ready := backlog stories where all Deps: are done on ledger
  if max_parallel == 1:
    dispatch first(ready, ledger_tie_break)   # today
  else:
    batch := []
    for s in ready ordered by ledger_tie_break:
      if len(batch) >= max_parallel: break
      if any(dep(s, b) or surface_overlap(s, b) for b in batch): continue
      batch.append(s)
    for s in batch: dispatch_once(s)   # detached, existing path
  wait until all batch members terminal OR tick sleep
```

**Integ

*(truncated in fold; original file remains archived)*


## Realization log

- **2026-09-01** — Dream captured from live Epic 28 + atlas drain session: 22.5
  mutex, 22.2 git-fact zombies, 28.12 ordering gap, and operator ask for
  composer/cursor fan-out when deps and surfaces allow.
- **2026-09-01** — `bmad-spec` → Story **28.16** +
  `spec-marshal-parallel-dispatch-fanout/SPEC.md` (CAP-1 wave scheduler,
  CAP-2 narrowed conflict, CAP-3 journal, CAP-4 explicit cap default 1, CAP-5
  compose with 28.12). Status: `specified`.

- **2026-09-09 (fleet readiness pass — operator-approved batch)** — Mechanism shipped, **status
  deliberately NOT flipped.** Story 28.16 is `done`: the wave scheduler
  (`core/dispatch_fleet.py:750-790`), the narrowed conflict guard (`cli/dispatch.py:935`
  `station_in_flight_conflict(..., parallel_dispatch=False)`) and the wave journal
  (`cli/dispatch.py:2775`) are all real, so `spec-marshal-parallel-dispatch-fanout` moves `ready` →
  `shipped`. This Dream stays **`specified`**: `max_parallel = 1` on all eight rendered loop homes
  and **no live wave has ever run**, so § *Live proof required* is unmet — under the realization gate
  a mechanism is not the effect.
  Both open questions closed by the operator: the cap stays a **fixed integer** (token-budget
  awareness needs a measured baseline that does not exist), and the wave builder keeps the **live
  effective-surface intersection** (declaration, not cost, is the bottleneck). **New CAP-6:** factory
  fan-out gets its own **`dispatch.max_parallel`** policy key — today `cli/dispatch.py:893-902` falls
  back to bmad-loop's `scm.max_parallel`, so raising it also fires `_max_parallel_clamp_finding`
  (`core/policy.py:1537-1551`), a warn whose text names bmad_loop 0.9.0 — wrong context on the
  dispatch path. One knob currently governs two unrelated concurrency models. Decomposed as marshal
  **Story 33.8**, which also carries the second defect: within-station fan-out cannot form a wave at
  all until story specs declare their own `surface:` (CAP-16 auto-derivation vs the pairwise refusal
  at `core/dispatch_fleet.py:786`). Batch:
  `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`.

- **2026-09-10 (live incident — `factory spin` has no equivalent guard at all).** This Dream's own
  `station_in_flight_conflict` protects `factory dispatch`; `factory spin` was never given the
  same treatment. Reproduced live: two `marshal factory spin pyforge-mason` calls six seconds apart
  (an operator error, not a deliberate fan-out) both launched cleanly — no refusal, no warning, two
  live `bmad-loop run` processes and two live supervisors against the SAME loop home
  (`~/.bmad-loops/pyforge-mason`) simultaneously. Caught only because the operator happened to `ps
  aux` before either process reached a git-mutating step; the second was killed by hand. Unlike
  dispatch's worktree-per-story isolation, spin's `bmad-loop run` operates directly on the loop
  home's own single checkout on `loop/<slug>` — a genuine concurrent run there risks two sessions
  writing the same working tree, not just wasted compute. **New finding, not yet decomposed into a
  story:** `factory spin` needs the same station-in-flight check `factory dispatch` already has
  (`cli/dispatch.py:935`) before its own `subprocess.Popen` launch in
  `adapters/harness_bmadloop.py` — reusing the check, not re-deriving it, mirrors this Dream's own
  CAP-2 "narrowed conflict, not a new one" precedent.

## 2026-09-16 — The operator stops re-pasting the status prompt — marshal watches its own runs (folded from marshal-run-watch)

# The operator stops re-pasting the status prompt — marshal watches its own runs

## The Dream

Watching a live `bmad-loop` run or a `bmad-build-auto` dispatch today means an operator
hand-driving a long, repeatable ritual through a chat session: run `bmad-loop status
<run_id> --json`, run `bmad-loop list --json`, run `marshal status --project <slug>`,
diff it against what was true five minutes ago, decide whether anything changed, and
decide how long to wait before checking again. Every property of that ritual — the
exact commands, the delta logic, the boundary-aligned polling, the "story completed,
check sooner" acceleration — was worked out once, live, against the pyforge-herald
Epic 21 run on 2026-09-15, and captured as a **Claude-only project skill**
(`.claude/skills/marshal-run-watch/`) that a `/loop` session re-invokes by hand.

That skill is real, tested against a live multi-hour run, and it works. But it lives
entirely outside marshal: it is prose a coding assistant follows, not code marshal
ships, so it exists only inside a chat session with that skill installed. Nothing on
marshal's own CLI, its MCP face, its persona, or its portal UI can produce this report.

The Dream is that **watching a run is a marshal capability**, not a Claude Code
convention. `marshal watch` — one run, one station's current run, or the whole
fleet — does what the skill does today: gather ground truth, diff it against the last
observation, report only when something changed or a caller-chosen cadence boundary is
due, and recommend how long to wait before checking again. It ships once, in
`pyforge-marshal`'s own CLI, and every other face — the unified `pyforge marshal watch`
grammar, the MCP tool, the persona menu, the portal view — either gets it for free or
costs one deliberate wrapper on top, per marshal's own layering.

> A ritual a human repeats by hand, that a program could repeat exactly, is a feature
> marshal hasn't shipped yet.

## Why now — measured, not feared

Live evidence from a single afternoon (2026-09-15, pyforge-herald run
`20260914-201759-bd47`, Epic 21 deck-trio derivation):

| Observation | Where it showed up |
|---|---|
| The same five-command sequence (`bmad-loop status`, `bmad-loop list`, `marshal status`, a git-branch-SHA check, a `gh pr list` filter) was re-run by hand roughly 20 times over 90 minutes | This conversation's own tool-call history |
| The delta logic (what counts as "changed": a story's phase, its `commit_sha`, the run's overall status, a new escalation, the loop branch's SHA, a PR's state) had to be re-derived from memory each time, not read from a single source of truth | Same |
| The "is it actually stalled or just quiet" liveness check (log mtime + size growth, not just the phase field) was reinvented ad hoc when story 21.3 ran ~75 minutes with zero token checkpoints | Same — nearly escalated a healthy run as stuck |
| `marshal status --project <slug>` surfaces a **stale, unrelated** one-shot dispatch record (`dispatch_*` fields) that must be manually filtered out on every single check when a `bmad-loop` run is what's actually live | Same, called out explicitly in every report this session produced |
| The eventual fix — a Claude Skill (`marshal-run-watch`) — had to reimplement marshal's own boundary/state logic in prose, in a project directory, invisible to `pyforge marshal watch`, `POST /stations/marshal/mcp`, the `bmad-agent-marshal` persona, and the `django-marshal` portal | `.claude/skills/marshal-run-watch/SKILL.md`, authored this session |

None of this is hypothetical scale — it is the exact ritual a fleet operator (human or
the `bmad-agent-marshal` persona) will repeat every time a bmad-loop run or dispatch is
in flight, which is most of the time this factory is running.

## What it looks like when real

- **One CLI verb replaces the ritual.** `marshal watch --project <slug> [--run
  <run_id>]` (a pinned run or a station's current one) and `marshal watch --fleet`
  (every project) each do what the skill's ground-truth-gathering + delta + boundary
  logic does today, in real Python under `pyforge.marshal.cli`, next to `status`/
  `homes`/`check`.
- **The stale-dispatch trap is gone.** `marshal watch` never conflates a live
  `bmad-loop` run's per-story detail with an unrelated prior `bmad-build-auto`
  dispatch record — it reads the right ground truth for whichever pattern is actually
  live, the way the skill already learned to.
- **Delta and cadence are a library, not a memory.** The "what counts as changed"
  predicate and the boundary/backoff poll-delay recommendation are one tested module
  other marshal code (and doctor's story-status source, if it ever wants the same
  liveness signal) can import — not prose a coding assistant re-derives per session.
- **The grammar is free.** `pyforge marshal watch ...` works the day the CLI verb
  ships — `pyforge.core.dispatch`'s argv passthrough needs no changes.
- **The other three faces are named, not assumed.** An MCP tool
  (`POST /stations/marshal/mcp`), a `bmad-agent-marshal` menu entry, and a
  `django-marshal` portal view are each real, separate follow-on work — this Dream
  states plainly that shipping the CLI verb does not give you those three for free,
  and scopes them as later CAPs an operator can take up or defer.
- **The Claude skill either retires or thins to a caller.** Once `marshal watch`
  exists, `.claude/skills/marshal-run-watch/SKILL.md` either becomes a thin wrapper
  that shells out to it, or retires outright — it does not stay the only
  implementation of logic marshal itself now owns.

## Constraints / Non-goals

- **Ports the skill's logic; does not redesign it.** The skill's delta predicate
  (story phase/commit_sha, run status, escalation, loop-branch SHA, PR state) and its
  boundary/backoff pacing were validated live against a real multi-hour run this
  session. The Spec derived from this Dream should port that behavior faithfully, not
  invent a new status model.
- **CLI first; the other three faces are scoped, not bundled.** Round one is the
  `marshal watch` CLI verb alone (which the unified grammar inherits for free). The
  MCP tool, the persona menu entry, and the portal view are named as explicit
  follow-on CAPs in the Spec this Dream produces — they may land as later stories in
  the same epic, or be deferred; this Dream does not presume they ship together.
  Whether the portal view or the MCP tool comes first is itself an open question for
  the Spec to resolve, not this Dream.
- **Read-only.** `marshal watch` observes and reports; it does not resolve
  escalations, resume runs, dispatch new work, or write to any sprint ledger. Those
  remain `bmad-loop resolve`, `marshal factory resume`, and `marshal factory dispatch`.
- **No second status engine.** `marshal watch` is a caller-facing report *shape*
  (delta-aware, boundary-paced) over the SAME ground truth `marshal status` and
  `bmad-loop status`/`list` already read — journals and run state, never a
  hand-maintained feed. It does not compete with `marshal status` as a second verdict.
- **Persisted state is local and disposable.** Whatever this capability uses to
  remember "what was true last time" (mirroring the skill's own
  `.claude/data/marshal-run-watch/*.json` cache) is a local, regenerable cache, not a
  new durable ledger. A missing or stale cache degrades to "first observation," never
  to a wrong delta.
- **Consumes `run-state-one-publisher` if and when it lands, doesn't wait on it.**
  [[run-state-one-publisher]] (status: specified, not yet realized at this Dream's
  seeding) would eventually give `marshal watch` a published run-state plane instead
  of journal-scraping. This Dream does not block on that landing — `marshal watch`
  reads today's ground truth (journals, `bmad-loop status`/`list`, `marshal status`)
  the same way the skill already does, and can be re-pointed at the published plane
  later without changing its caller-facing shape.

## Kinships

[[pyfo

*(truncated in fold; original file remains archived)*


## Realization log

- **2026-09-15** — Seeded. A live, hand-driven `/loop` monitoring session against
  pyforge-herald run `20260914-201759-bd47` (Epic 21) produced a working ritual —
  captured as the Claude-only skill `.claude/skills/marshal-run-watch/` — that
  reimplements, in prose, status/delta/pacing logic that belongs in marshal itself.
  Operator asked to promote it into marshal "across its planes" (CLI, unified
  grammar, MCP, persona, UI); per the always-on Dream-first rule this Dream is the
  entry point, not a direct edit to `pyforge-marshal`'s source. Next act: `bmad-spec`
  derives the Spec under `pyforge-marshal`.
- **2026-09-15** — Specified. `spec-marshal-run-watch` derived headless/express (the Dream was
  fully seeded; no open questions raised). Mints CAP-1 (the `marshal watch` CLI verb, pinned-run/
  station/fleet scope) and CAP-2 (the stale-`dispatch_*`-record trap closed) as the implementable
  round, plus CAP-3 (MCP tool), CAP-4 (persona menu entry) and CAP-5 (portal view) as named
  follow-ons for later stories in the same epic. Both self-validate passes (coherence,
  preservation) passed clean. `status: ready`. Next act: decompose CAP-1+CAP-2 into a Story under
  `pyforge-marshal/epics.md`.

## 2026-09-16 — Single-story dispatch is a marshal verb, not a session's discipline (folded from marshal-single-story-dispatch)

# Single-story dispatch is a marshal verb, not a session's discipline

## The Dream

The fastest story-landing pattern this factory has ever run is not a marshal
capability — it is a ritual an interactive session performs by hand. One story
per fresh, worktree-isolated `bmad-dev-auto` agent; wait for its *real*
completion; independently verify (run the tests, read the diff, invoke the
live CLI); land through a PR; only then dispatch the next. On 2026-08-21 that
ritual landed **22 stories across four stations in one session**, where the
preceding `marshal factory spin` pass had stalled at roughly one story per
station on per-run token budgets. The dream is that this pattern becomes a
first-class marshal verb — `marshal factory dispatch <slug> <story>` (or a
`marshal dev` family) — with the ritual's rigor supplied by machinery instead
of by whichever session happens to remember it.

The pattern's speed is not an accident; it is structural. It sidesteps the
orchestrator layer where every documented bmad-loop failure lives: the
stuck-orchestrator baseline drift that permanently defers real reviewed work
(`docs/dreams/bmad-loop-baseline-drift.md`), the feed that reports intent as
fact, interactive-prompt stalls invisible to `status`, the worktree
path-length panic, and the ~600-second watchdog that kills a top-level
orchestrator busy-waiting on its own long-running nested review. And it adds
the one step no self-report can supply: independent verification — which
caught two live-reproducible leaks in a story that had already marked itself
shipped (doctor 12.3, round-4 review).

But run by hand, the pattern has exactly the weaknesses bmad-loop does not:
it dies with the operating session (in-flight agents orphan), it has no
budget ceilings, no resumable journal, no escalation protocol, no
`changes.patch` safety net, and its verification is rigor-by-discipline —
performed only as well as the orchestrating session performs it. The dream is
the best of both: marshal's deterministic governance wrapped around the
dispatch pattern's speed and verification honesty.

## What is real

Marshal already owns every piece of this **except the dispatch driver
itself**:

- **Worktree provisioning** — `marshal init` (Epic 1, shipped) provisions
  isolated homes with marker/symlink/backlink discipline; the Agent-tool
  worktree pattern proved per-story isolation works without a loop home.
- **Gates** — Epic 2 (shipped) provides the runnable gate set a landing must
  clear.
- **Landing paper trail** — Epic 4 (shipped) owns landing, branch retirement,
  and the one-pusher rule.
- **Hand-driven completions are already first-class in the ledger** — Story
  5.9 (FR-186, shipped) makes a story finished outside bmad-loop visible:
  `marshal deploy reconcile-completions` detects it from git and promotes the
  ledger, recording the completion path as `bmad-quick-dev`, distinct from a
  loop completion.
- **Fleet visibility** — Epic 5 (shipped) + `fleet-picture` report per-station
  state; Epic 15 (backlog) mechanizes the surrounding rituals (loop-home
  refresh, ledger promotion at landing).
- **The session-side protocol is documented** and validated at N=22:
  one story per fresh `general-purpose` + worktree-isolated agent running
  `bmad-dev-auto` with `BMAD_ACTIVE_PROJECT` passed per-invocation and
  physical artifact paths (never `bmad-switch` from a parallel agent);
  independent verification before every landing; `gh pr merge --merge`;
  - story-spec promotion to tracked `planning-artifacts/specs/`; scoped
  `sprint-ledger-sync` + `story-status-check` in the same commit.
- **Fleet drain playbook (2026-08-22/23):** eight-station campaign documented in
  `spec-marshal-single-story-dispatch/fleet-drain-playbook.md` (marshal-owned companion);
  interim runner at `.cursor/pyforge-fleet-drain/`. Merge-in-agent fleet-wide since
  2026-08-23. Six stations drained; marshal + steward backlog remain — the playbook is
  the acceptance oracle for Epic 22 CAP-7 until `marshal factory dispatch --fleet` ships.

What does **not** exist: any marshal verb that launches, awaits, or judges a
single-story dev-auto session. `marshal factory` today is `spin`/`attach`/
`resume` — bmad-loop only. A repo-wide search of all 21 marshal epics finds
no FR covering the dispatch driver.

## What the Spec must decide

1. **Completion detection must be event-grounded, never busy-waited.** The
   two traps that motivated the session-side rule
   (`feedback_single_story_dispatch_over_backlog_orchestrator`): a top-level
   orchestrator busy-waiting on a nested async agent gets watchdog-killed and
   its child's work discarded; and a "killed"/"failed" notification does not
   mean the agent stopped — one "dead" agent landed two stories after its
   failure notification, and a naive redispatch nearly duplicated the third.
   The marshal-native driver must judge completion from git facts (AD-33:
   commits, merge refs) and running-process facts, not from notifications or
   polling filler.
2. **The verification step is the product.** Self-reports are input, never
   verdicts (the same asymmetry as feed-vs-run). The driver must run the
   story's real test/verify commands itself and read the diff surface before
   any landing — the step that made the hand-run pattern trustworthy.
3. **Wrap-vs-absorb, revisited honestly.** Marshal's PRD resolved
   wrap-vs-absorb in favor of wrapping bmad-loop. This capability is the
   absorb half arriving through the back door: it replaces the orchestrator
   layer (where the documented bugs live) while keeping the dev/review
   session machinery. The Spec must name this and either bound it (dispatch
   as a *sibling* mode beside `spin`, never a replacement) or explicitly
   revise the PRD decision.
4. **Sequencing within a station, parallelism across stations.** The
   validated pattern is one story at a time per station, stations in
   parallel when their surfaces are disjoint. Whether the driver enforces
   disjointness or trusts the operator is a Spec question.
5. **What survives the operator.** Detached-by-default like `spin` (AD-22),
   or attended-by-design? The hand-run pattern's orphan-on-session-death is
   its worst property; the Spec decides how much of bmad-loop's detachment
   (tmux, journal, resume) the driver inherits.

## Addendum (2026-08-31) — station-scoped and sequence-scoped dispatch

**Problem:** `dispatch <slug> <story>` launches exactly one story and returns — no
chaining. `drain --mode <mode>` chains automatically (CAP-7) but is fleet-wide only: its
six flags (`--mode`, `--leave-remaining`, `--once`, `--max-cycles`, `--tick-seconds`,
`--campaign`) carry no station filter — confirmed against `cli/dispatch.py`'s own
argparse definition — so it always reads every station's ordered backlog and launches one
story per station in parallel. There is no way to drain just one station to zero without
touching every other station's backlog too, and no way to hand marshal an explicit ordered
list of stories to run, overriding the ledger's own order, for a single targeted push.

**Motivating incident (2026-08-31):** wanted to complete just `pyforge-scribe`'s 2
remaining backlog stories — identified that session as the fleet's smallest,
highest-leverage remaining chunk (the only cross-station `Deps:` link in the entire
remaining backlog) — without disturbing atlas's or marshal's own in-flight backlogs. No
CLI primitive existed for it: the only options were fleet-wide `drain` (wrong scope) or
two manual `dispatch` calls with a human/agent polling for landing in between, forfeiting
`drain`'s chaining/preflight/campaign-journal machinery for no reason but scope.

**Approach:** extend the dispatch surface, don't fork it — CAP-7's chaining, preflight,
and campaign-journal machinery is exactly what a station-scoped drain needs too; the only
missing dimension is *which stories, on which stations*, handed as an override to the same
per-station ordered-backlog reader CAP-7 alread

*(truncated in fold; original file remains archived)*


## Realization log

- **2026-08-21** — Seeded `dreamt` (`a17626226b`); `spec-marshal-single-story-dispatch` derived under
  pyforge-marshal the same day (`8add322204`).
- **2026-08-31** — Addendum: station-scoped and sequence-scoped dispatch.
- **2026-09-02** — Addendum: a `done` spec must not review-loop — contracted as CAP-11 in the Spec
  (`1763820bee`), Epic 29. Spec status `in-progress`.

- **2026-09-09 (fleet readiness pass — operator-approved batch)** — **`specified` → `realized`,
  verified in effect at fleet scale.** CAP-1..11 decompose to Epic 22 (22.1–22.11) and Epic 29
  (29.1–29.2), all `done`; the drain campaigns and `fleet-drain-playbook.md` are the live exercise.
  Spec `in-progress` → `shipped` with `open_questions: []`. All five questions closed:
  **OQ-1** verb = `marshal factory dispatch`, no `marshal dev` family — now a cross-package constant
  (`pyforge-core/.../landing_evidence.py:50`), so renaming would break doctor's grammar; PRD Q-15
  inherits it. **OQ-2** launch = profile-driven, shipped as Story 22.8 — with a **new Constraint**
  recorded: a dispatched session is never launched from a fork subagent (`bmad-build-auto`'s
  mandatory subagents break inside one); the profile mechanism does not enforce it. **OQ-3**
  (operator) the enforceable budget signal is wall-clock + idle-strand via the dispatch supervisor;
  token ceilings stay advisory until Epic 33's benchmark exists. **OQ-4** disjointness compares
  DECLARED surfaces only — and within-station fan-out is impossible until story specs declare their
  own `surface:`. **OQ-5** completion detection shipped as a *sibling* supervisor
  (`dispatch_supervisor/__main__.py`), neither a generalized supervisor nor Story 3.4's sidecar.
  **Consequence carried forward:** two supervisors now write run state, which is exactly why the
  CAP-17 publishing seam must be one publisher (`spec-marshal-token-economy` CAP-18, Story 33.4).
  Batch:
  `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`.

- **2026-09-11** — Addendum: CAP-3's bound verify command can miss the story's real surface
  when it crosses into a shared cross-station directory (`src/platform/`). Motivated by a live
  rescue of steward Story 49.14, which passed its bound gate while shipping four real defects
  a full `platform-ci-local -- --test` run caught — GitHub Actions' own backstop has been down
  fleet-wide the entire session, so the narrow gate was the only one running. Contracted as
  CAP-12 in the Spec. Spec status `shipped` → `in-progress` pending decomposition.

## 2026-09-16 — A spin-time poll timeout never permanently blinds marshal status to a healthy run (folded from marshal-status-harness-run-id-poisoning)

# A spin-time poll timeout never permanently blinds marshal status to a healthy run

## The Dream

`marshal status` (and everything built on it — `fleet-picture`'s per-station row, `dashboard-gen`'s
in-flight card) reports a run's real state — `running`/`idle`/`stopped` — for the run's entire
lifetime, even when the one-time poll `marshal factory spin` performs at launch to confirm
bmad-loop's own self-minted `harness_run_id` times out. Today it does not: that poll's failure
(`MRS-SPIN-004`) journals `"harness_run_id": null` into the run's launch OUTCOME entry
**permanently**, and every later status read — including the one legitimate fallback that
exists — re-derives from that same poisoned field and can never recover, even though the real
run directory (`.bmad-loop/runs/<run_id>/state.json`) sits on disk, correctly updating, for the
run's entire life.

## What is real

Confirmed live, 2026-08-15, reproduced on a real spin (`marshal factory spin pyforge-doctor
--story 9.1`): the poll timeout fired (`MRS-SPIN-004`), the journal recorded
`harness_run_id: null`, and `marshal status`/`fleet-picture` reported `pyforge-doctor` as
`UNKNOWN`/"status unreadable" for the run's entire ~40-minute life — including while the run
was demonstrably healthy (`ps` showed the process alive; `.bmad-loop/runs/<id>/state.json`
showed `dev-running`, correct baseline, no crash) and after it finished successfully. A prior
session (2026-08-13) recorded this same symptom as "resolved / no longer observed" — it was
not; it simply did not reproduce that session, and nobody had root-caused it as a real,
reproducing bug rather than a flake.

**Root cause, traced to source** (`src/shared/packages/pyforge-marshal/src/pyforge/marshal/`):

- `cli/spin.py`'s launch path polls to confirm bmad-loop's own self-minted run id and journals
  it into the run-launch OUTCOME entry (`{"pid": ..., "harness_run_id": ...}`). When that poll
  times out, the entry is journaled with `harness_run_id: null` — this is the ONLY place that
  field is ever written; nothing ever goes back and corrects it later, even after the run
  proves itself alive via supervisor heartbeats.
- `cli/status.py::_gather_home_facts` (the function every `marshal status`/`fleet-picture` row
  derives from) reads `journal_facts.harness_run_id`; when it's `None`, it falls back to
  `_resolve_harness_run_id_for_resume` (`cli/spin.py:1719`) — but that helper reads the
  **identical already-poisoned journal entry**, looking for the same field. It can never
  recover a value that was never successfully written, no matter how long the run has been
  alive or how many heartbeats it has journaled since.
- Meanwhile `cli/spin.py::_latest_run_dir` already knows how to find the real, live bmad-loop
  run directory for a project by listing `.bmad-loop/runs/` — the exact information the poll
  was trying to confirm in the first place, sitting right there on disk, unused by the fallback
  path.

## What it looks like when real

- The one-time poll can still time out (network/process-timing variance is real) — the Dream
  does not eliminate the poll or its timeout.
- When it does, `_gather_home_facts`'s fallback path recovers the harness run id by
  **filesystem discovery** (the same `.bmad-loop/runs/` enumeration `_latest_run_dir` already
  performs) rather than by re-reading the same journal field that was never written —
  self-healing on the very next status read, not permanently blind for the run's whole life.
- `marshal status --format json`'s `MRS-STATUS-002` finding (today's only signal anything is
  wrong) stops firing for a run whose journal-poll merely timed out but whose bmad-loop run
  directory is real and healthy; it keeps firing, correctly, for a genuinely unrecoverable case
  (no run directory exists at all, or it's unreadable).

## Constraints

- Must not weaken `MRS-STATUS-002`'s own honest-degradation contract for the case it actually
  protects — a run whose directory genuinely cannot be found or read must still report
  `unknown`, never silently guess.
- The filesystem-discovery fallback must not introduce a live subprocess or network call per
  status read (NFR-14's own "no live harness query per home" discipline) — `_latest_run_dir`
  is already a plain `Path.glob`, so this stays within that budget.

## Non-goals

- Not fixing the poll's own timeout window or retry behavior — this Dream is about the
  permanent-blindness consequence of a timeout, not about preventing timeouts from happening.
- Not a general audit of every other journal field with a similar single-write-no-repair shape
  — scoped to `harness_run_id` specifically, the field this session's live reproduction
  actually hit.

## Kinships

[[pyforge-marshal]] (the station; `cli/spin.py`/`cli/status.py` are its own core modules) ·
[[bmad-loop-liveness-footgun]] (a sibling status-reporting footgun — `engine.pid`'s two-field
liveness misread — same family of "status reporting trusts a field that can go stale," found
the same session).

## Realization log

- **2026-08-15** — Dream captured. Root-caused during a live fleet landing pass after the user
  challenged a recurring "UNKNOWN" status finding a prior session (2026-08-13) had incorrectly
  logged as resolved. Traced to source in `cli/spin.py`/`cli/status.py`, reproduced live against
  a real spin (`pyforge-doctor --story 9.1`), and NOT hotfixed in that session per this repo's
  Dream-first policy for any `pyforge-marshal` code change. Captured as its own Dream once the
  user asked directly to fix it.

- **2026-09-09 (fleet readiness pass — operator-approved batch)** — **`specified` → `realized`.**
  `_discover_harness_run_id_by_filesystem` (`cli/status.py:659`) is wired as the third fallback at
  `:918-921`; CAP-2's honest degradation is held at `:930-940`. Shipped by commit `e7039b9ee6`. The
  Spec, which carried **no `status:` line at all**, is set to `shipped`. Like its sibling Dream, no
  `epics.md` story owns it — the fix landed outside the story ledger.
  **Not to be confused with the surviving `pyforge-steward` `UNKNOWN`**, which
  `DW-STATUS-2026-09-08-1` traced to a different cause — a harness-native run marshal never launched
  — owned by Story 5.11 (FR-196, `backlog`). Batch:
  `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`.

## 2026-09-16 — The templated merge-subject shape never masquerades as a same-numbered story from another project (folded from marshal-templated-merge-subject-cross-project-collision)

# The templated merge-subject shape never masquerades as a same-numbered story from another project

## The Dream

`core/promotion.py::merged_story_keys`'s FIRST merge-subject shape in
precedence order — the AD-24 templated form (`merge_subject_template`,
default `"Merge {key} into main"`) via
`pyforge.core.landing_evidence.parse_templated_merge_subject` — extracts a
`StoryKeyRef` (`epic` + `seq` + `suffix`, nothing else) from a bare
prefix/suffix slice around `{key}`, with **no `project_slug` parameter at
all**. Every one of its four sibling parsers in the same precedence chain
(`parse_github_pr_merge_subject`, `parse_bmadloop_merge_subject`,
`parse_recovery_commit_subject`, `parse_story_direct_commit_subject`) takes
`project_slug` and scopes on it (branch prefix, `loop/<slug>` target,
station-name match); the templated parser is the one shape in the chain
that does not, and it is tried FIRST — so a station whose own historical
`main` history carries `"Merge 22.5 into main"`-shaped commits makes that
key falsely "already merged" for every OTHER station in the repo's shared
history that happens to mint the same epic.seq number, with zero
cross-project check anywhere in the path.

This is the sibling gap
[[marshal-land-cross-project-story-key-collision]] scoped itself away
from: that Dream (realized 2026-09-09) fixed ONLY the second parser in the
chain, `parse_github_pr_merge_subject`, via the now-shared
`_branch_belongs_to_project` helper. Its own Non-goals said "Not auditing
every OTHER caller of `merged_story_keys` for downstream consequences" —
the templated-form parser was never touched, and nothing in its
Realization log claims it was.

## What is real

Confirmed live, 2026-09-11, while dispatching `pyforge-doctor` Epic 22
(Stories 22.1–22.6) via `marshal factory dispatch --stories`. The dispatch
campaign supervisor reported `story_merged_on_main: True, verdict:
"completed"` for Stories 22.1, 22.2, and 22.4 within ~1 second of
dispatch, before their real `bmad-build-auto` sessions had done any
meaningful work (`changed_paths: []`). Root-caused to `pyforge-marshal`
having its OWN, unrelated Epic 22 (Stories 22.1 through at least 22.12),
landed earlier the same session via marshal's own native
`"Merge 22.1 into main"`-style merge subjects — those commits are
permanently present in `main`'s history now, so ANY future dispatch of a
same-numbered story for ANY OTHER station collides identically, forever.

Reproduced directly against the current `main` (5,629 commit subjects,
2026-09-11) with `project_slug='pyforge-doctor'`:

```python
promotion.merged_story_keys(subjects, 'Merge {key} into main', 'pyforge-doctor')
```

returns 129 keys, the large majority demonstrably NOT doctor's own —
`22.11`, `22.12` (real marshal-only story numbers doctor has never had),
plus entire runs of keys from other stations' epics that doctor's own
`epics.md` does not contain: `23.1`–`23.9`, `28.1`–`28.31`, `39.4`,
`40.1`–`40.2`, `41.1`–`41.4`, `42.1`–`42.5`, `43.1`–`43.6`, `46.10`,
`48.2`–`48.4`, `49.1`–`49.7`. The contamination is not a one-off — it is
the general-case behavior of this parser for every station in this
repo's shared history whenever two stations' epics happen to number the
same.

The false "already merged" verdict did not always kill the real work
underneath — 22.1/22.2/22.4's actual `bmad-build-auto` sessions kept
running independently and completed genuinely correct work despite the
supervisor's premature wrong report — but Story 22.3's session was
orphaned mid-task by the same false signal (process death with no clean
completion, real substantial work left uncommitted, recovered by hand).
The false verdict backs the SAME `merged_story_keys` call `marshal
land`'s already-landed short-circuit and `run_reconcile_completions`'s
"confirmed" classification use, so this is not scoped to dispatch alone —
any caller of `merged_story_keys` inherits it.

## What it looks like when real

- `parse_templated_merge_subject` (or its caller,
  `classify_merge_subject`'s templated-form branch) is scoped to
  `project_slug` the same way its four sibling parsers already are — a
  bare `"Merge {key} into main"` subject is trusted as THIS project's own
  key only when something in the commit (a station-prefixed branch name
  captured alongside the merge, or an equivalent scoping signal) confirms
  it belongs to `project_slug`.
- Re-running the reproduction above against the fixed code returns only
  keys doctor's own `epics.md` actually contains — no `22.11`/`22.12`, no
  `23.x`/`28.x`/`39.x`–`49.x` bleed.
- `marshal factory dispatch`/`factory drain` no longer reports a false
  `story_merged_on_main: True` for a story number another station has
  used, confirmed by re-dispatching a colliding number (e.g. doctor
  22.1–22.6 again, now against the fixed code, as a regression check —
  not to re-land anything already merged).

## Constraints

- Must not regress the templated form's correct, intended use: a story
  genuinely landed BY `pyforge-marshal` itself (`deploy land-story`,
  which renders the template from policy) for its OWN `project_slug` must
  still classify as merged.
- The templated merge subject, by construction (AD-24), carries no
  station token in its own text — `"Merge 22.5 into main"` looks
  identical regardless of which station produced it. The fix therefore
  cannot rely on parsing the subject text alone; it needs either an
  additional out-of-band scoping signal (e.g. restricting the scan to
  commits reachable only via the querying project's own tracked
  branches/worktree lineage) or a documented, deliberate narrowing of
  what the templated shape is trusted to prove — mirroring how
  `marshal_native_merged_keys`'s own docstring already reasons about what
  git alone can and cannot prove per shape.
- Pure-function discipline (AD-4) holds for `core/promotion.py` and
  `pyforge.core.landing_evidence`: no I/O, no subprocess, no `pathlib`
  methods added — if the fix needs a new scoping signal, the signal must
  be computed by an existing impure caller and passed in, not fetched by
  the pure classifier itself.

## Non-goals

- Not re-litigating the already-`realized` GitHub PR-merge fix
  ([[marshal-land-cross-project-story-key-collision]]) — that parser
  stays as-is.
- Not adding a plausibility bound on raw epic/story numbers — a
  `core.identity.normalize` concern, unrelated to this scoping gap.
- Not auditing every historical false-positive this parser may have
  already produced before this fix lands (e.g. whether a past
  `run_reconcile_completions` run silently mis-confirmed an open intent
  using a stale cross-project key) — scoped to closing the extraction
  bug itself, not a forensic audit of its past consequences.
- Not re-dispatching or re-landing any of doctor's Epic 22 work — all six
  stories (22.1–22.6) were independently recovered and landed by hand
  this session despite the false verdicts; that recovery is complete and
  is not part of this Dream's scope.

## Kinships

[[marshal-land-cross-project-story-key-collision]] (the sibling gap in
the same precedence chain, already fixed for a different parser) ·
[[pyforge-marshal]] (the station; `core/promotion.py` is its own core
module) · [[marshal-status-harness-run-id-poisoning]] (same family: "a
field trusted as proof that turned out not to be").

## Realization log

- **2026-09-11** — Dream captured. Found live during `pyforge-doctor`
  Epic 22 dispatch: three of four dispatched stories (22.1, 22.2, 22.4)
  received an instant, false "already merged" verdict from the fleet-
  drain campaign supervisor; a fourth (22.3) was actually orphaned by the
  same false signal mid-task. Root-caused to `parse_templated_merge_
  subject` lacking the `project_slug` scoping its four sibling parsers in
  the same `classify_merge_subject` precedence chain already carry.
  Reproduced directly against live `main` (5,629 subjects): doctor's own
  `project_slug` query returns 129 keys, a large majority att

*(truncated in fold; original file remains archived)*


## 2026-09-16 — Marshal Token Economy — the loop that reads less, says less, and re-learns nothing (folded from marshal-token-economy)

# Marshal Token Economy

## The Dream

Every unattended story Marshal runs today pays a tax it never questions. The
session boots and re-reads the same repo guidance it read yesterday. It
re-explores a codebase whose structure has not changed since the last
iteration. It receives test logs that are 95% passing noise around one FATAL
line. It narrates its work in polite, fully-grammatical prose that nobody but
another machine will ever read. Then the session ends, the context evaporates,
and the next story pays the whole tax again.

Marshal already knows how to **stop runaway spend** — budget ceilings, the
idle-strand ladder, prompt-cache-aware polling, model tiering. What it cannot
yet do is **make an iteration cheap in the first place**. The dream is a loop
where every token that reaches the model earns its place: tool outputs arrive
compressed but reversible, codebase structure is answered from a pre-built
graph instead of re-read files, planning context is retrieved as the 1,500
tokens a story actually needs instead of the 65,000-token document it lives in,
derived context is recomputed only when its sources change, and the agent's own
output is stripped to its semantic payload. The operator sees, per story, not
just "how much was spent" but "how much was *saved*, by which layer" — and the
budget ceilings stop being blunt kill-switches and become calibrated contracts
a normal story never brushes against.

**Dispatch drain resilience (2026-09-01).** Token economy only pays off if unattended
drain survives harness billing walls and recoverable verify failures. Interim
machinery (see `change-history/sprint-change-proposal-2026-09-01-dispatch-autonomy-hotfixes.md`)
adds harness profile failover, transient block classification for fleet retry, and
supervisor stuck-land detection — without weakening CAP-17 warn-mode visibility.

Same stories landed. Same review fidelity. A fraction of the tokens.

## What is real

> *2026-09-09: this section is the 2026-08-30 baseline and is kept as the record. Epic 28 has
> since shipped every item below as **machinery** (24/24 `done`, verified against `main`), and
> none of it is switched on — so the **behaviour** this section describes is still the live
> behaviour. See § Addendum (2026-09-09).*

**Marshal's existing token posture is brakes, not diet.** Shipped: per-story /
per-run weighted-token and wall-clock ceilings (E3.6, defaults 50M/500M
weighted), the idle ladder (nudge → stop-retry → defer), prompt-cache TTL
discipline (NFR-14, poll ≤60s, `cache_read_weight = 0.1`), difficulty-driven
model tiering (FR-51, wired but rarely fed — see
[`adaptive-model-tiering.md`](adaptive-model-tiering.md)), and single-story
dispatch (E22). Nothing in the marshal package or the bmad-loop/bmad-build-auto
chain compresses, indexes, or graph-serves context. The deferred-work ledger
confirms it: token findings are all observability gaps (`DW-FU-3-6-6`
mid-session ceiling blindness), never "context is too big".

**Where an iteration's tokens actually go** (fresh session per story):

| Sink | Rough size | Nature |
|---|---|---|
| Always-on repo docs (`CLAUDE.md`, `AGENTS.md`) | ~10k + ~3.6k tokens | identical every session |
| `project-context.md` (build-auto activation) | ~9k tokens | identical every iteration |
| Story spec + epic-context + sibling continuity | ~5k–16k tokens | per-story, partially redundant |
| Tool outputs mid-story (file reads, grep, test/build logs) | unbounded — often the dominant sink | 70–95% boilerplate |
| Codebase re-exploration | tens of k per session | structure that rarely changed |
| Review passes (4 fresh reviewer lenses × diff + context) | full context tax × N | multiplicative |
| Agent's own output (weighted heaviest) | prose ceremony | compressible ~65% |

**The five instruments are already forged — none is wired in:**

- **`recipes/headroom-ai/`** (0.32.1, Apache-2.0) — context-compression layer:
  SmartCrusher/ContentRouter/CodeCompressor over tool outputs, logs, JSON,
  diffs; 40–95% savings; **reversible** via the CCR store +
  `headroom_retrieve`; ships as library, transparent proxy, MCP server, and
  one-command agent wrap (`headroom wrap claude|copilot|cursor|…`). Critically,
  its live-zone-only design compresses only the newest blocks and leaves the
  provider cache hot zone untouched — it *cooperates* with NFR-14 instead of
  fighting it. Commented-out in `pixi.toml` (blocked per
  [`pixi-candidate-currency.md`](pixi-candidate-currency.md)).
- **`recipes/caveman/`** (2.4.0, MIT installer) — Claude Code skill cutting
  ~65% of **output** tokens (the heaviest-weighted kind) via ultra-compressed
  agent speech. This recipe ships only the MIT skill installer
  (`caveman-install`); upstream's input-side Caveman Proxy is a separate
  BSL-1.1 product, deliberately not packaged. Commented-out in `pixi.toml`.
- **`recipes/codegraph/`** (1.6.0, MIT) — pre-indexed code knowledge graph,
  kept synced on change; agents answer structure questions from the graph
  instead of re-reading files. Fully local. Active in pixi, linux-64 only.
- **`recipes/graphifyy/`** (0.9.44, MIT) — turns any folder of code/docs into a
  queryable knowledge graph. Active in pixi. Scribe already plans to bind it
  behind a `GraphStore` seam — ownership must be coordinated, not duplicated.
- **`recipes/cocoindex/`** (1.0.20, Apache-2.0, on conda-forge) — incremental
  indexing engine: derived indexes stay fresh from source updates with minimal
  recomputation. Active in pixi.
- *(Bonus instrument:* **`recipes/rtk/`** — "Rust Token Killer" proxy that
  shrinks `git`/`ls`/shell output before the agent sees it.)*

## The integration architecture — five layers, one policy surface

Each layer attacks a different sink; they compose because they operate at
different points of the pipeline. All of them live **outside** the BMAD
skills' semantics — the story contract, gates, and review verdicts are never
altered, only the encoding of what flows through.

```
                    ┌─ Layer 4: graphifyy ── planning-artifacts as a queryable
                    │            graph: retrieve the 1.5k tokens a story needs,
                    │            never load epics.md (65k) / prd.md (46k)
                    │
  bmad-build-auto ──┤─ Layer 3: cocoindex ── epic-context / project-context
     (per story)    │            distills recomputed ONLY when sources change
                    │
                    ├─ Layer 2: codegraph ── structure questions answered from
                    │            the pre-built graph, not file re-reads
                    │
  coding CLI  ──────┼─ Layer 1: headroom ─── every tool output / log / diff
  (claude/copilot)  │            compressed 40–95%, reversible via CCR
                    │
                    └─ Layer 0: caveman ──── the agent's own output stripped
                                 ~65%, heaviest-weighted tokens
  marshal ──────────── policy renders it, Genesis seeds it, supervisor
                       meters it: savings-per-layer in every journal
```

- **Layer 1 — wire compression (headroom-ai).** Marshal's harness profiles
  gain a wrap step: the coding CLI runs behind `headroom wrap <cli>` (or the
  transparent proxy for base-URL-only tools), so tool outputs, build/test
  logs, and file reads are compressed before the provider call. The CCR store
  lives inside the loop home (worktree-scoped, torn down with it), and the
  agent keeps `headroom_retrieve` for full originals — nothing is lost, which
  keeps the fidelity contract intact.
- **Layer 0 — output compression (caveman).** Genesis (`marshal seed`) deploys
  the caveman skill into each loop home's agent config; dev sessions talk
  caveman, review verdicts and journal entries stay fully articulated (the
  operator and the escalation path read those). Output tokens carry the
  highest weight in the tally, so this is the cheapest big win.
- **Layer 2 — structure from the graph (codegraph).** Loop-home provisioning
  indexes the wor

*(truncated in fold; original file remains archived)*


## Realization log

- **2026-09-16 (consolidation)** — Operator-ruled Dream fold: the five
  token-savings Dreams (`token-economy-claude-session-path`,
  `adaptive-model-tiering`, `cursor-native-tier-map`,
  `dispatch-tier-routing-fails-safe`, `bmad-cursor-interactive-routing`)
  fold into this Dream as the single starting point for the token-savings
  chain — same owner, same center, same lifecycle. Their files stay as
  `archived` pointers; their Specs stay live and remain the contracts.
  Exclusions named in § *Seams this Dream rides*. No status change: this
  Dream stays `specified` until a benchmark artifact reports a measured
  saving on a real story — the guard below stands, now for the whole
  folded family.
- **2026-08-30** — Seeded already `specified` (`da458df364`): `spec-marshal-token-economy` `ready`,
  decomposed as marshal Epic 28 (28.1–28.9, backlog). Same-day addendum — the price sheet becomes an
  instrument (CAP-11/CAP-12 → Stories 28.10/28.11).
- **2026-08-31** — Addendum: Layer 4 retrieval is only as good as the graph's freshness — landed as
  CAP-13; the live dispatch-ordering incident added CAP-14..CAP-17 (Stories 28.12–28.15) through
  [`marshal-dependency-aware-dispatch.md`](marshal-dependency-aware-dispatch.md).
- **2026-09-01** — Dispatch-autonomy hotfixes + Epic 28 artifact catch-up (`90c5a28bd6`).
- **2026-09-09** — Code-level verification against `main`: Epic 28's machinery is real
  and complete, and every layer is off — no `[context]` block is declared in any policy,
  repo, project or rendered. Both of § *Gates and open questions*' gates closed against
  the evidence: the measurement-first gate was bypassed (no benchmark artifact exists),
  and the cross-engine question is answered in the negative (the block renders
  identically on both adapters, but only dispatch/build-auto can act on the wire,
  derived-context and planning-graph layers). Recorded as the addendum above, with the
  `realized` guard learned from [`adaptive-model-tiering.md`](adaptive-model-tiering.md).
  Next: `bmad-correct-course` mints marshal Epic 33.
- **2026-09-09 (later)** — § *What is real* glossed as the dated baseline (kept as record). The
  Unifying Strategy currency review
  (`_bmad-output/projects/pyforge-steward/planning-artifacts/research/currency-review-pyforge-unifying-strategy-2026-09-09.md`)
  found the same built-but-inert shape on Unifying **CAP-17** (run state as a service): marshal has
  zero imports of `django_pyforge` and `marshal/cli/init.py` still reads `~/.bmad-loops`, so the
  supervisor never receives a bmad-loop run. The Hub's Track (`hub:CAP-3` on
  `spec-intelligence-hub` — *not* this Dream's CAP-3, which is caveman output-compression
  seeding) and this Dream's savings telemetry (CAP-7) are the same publishing seam; Epic 33
  should land them together, not as two writers. *(Citation corrected 2026-09-09 — the first
  draft of this line collapsed two Specs' CAP-3.)*

- **2026-09-09 (fleet readiness pass — operator-approved batch)** — **Epic 33 minted (10 stories)**
  by `_bmad-output/projects/pyforge-marshal/planning-artifacts/change-history/sprint-change-proposal-2026-09-09-token-economy-enablement.md`.
  Status stays **`specified`** and does not move until Story 33.1's benchmark artifact reports a
  measured saving on a real story — this Dream's own guard, learned from
  [`adaptive-model-tiering.md`](adaptive-model-tiering.md).
  The epic in order: **33.1** measurement first — the on/off benchmark artifact with CAP-7's four
  savings getters made real (`adapters/harness_bmadloop.py:1880-1898` returns `None` four times
  today); **33.2** enable the layers on `factory dispatch` (`resolve_wire_wrap` folded); **33.3**
  enable on `factory spin` (fold the repo defaults `cli/spin.py` never reads, `DW-FU-28-2-3`);
  **33.4** **CAP-18 — one publisher**: run state *and* savings telemetry to
  `django_pyforge.supervisor`, so `cli/init.py:331` and doctor's `sources/marshal.py:544` stop
  reading `~/.bmad-loops` (this is Unifying **CAP-17** — qualified, because *this* Dream's CAP-17 is
  `scope_violation_mode` — and the Hub's Track is **`hub:CAP-3`**; steward Story 49.8 is ledger
  `blocked` on 33.4); **33.5** risk-tiered review wiring; **33.6** adaptive tiering fed on all eight
  stations plus the floor-raise on dispatch; **33.7** the two Epic-20 watchdogs re-pointed off
  `~/.bmad-loops`; **33.8** the first live fan-out wave with a real `dispatch.max_parallel` key;
  **33.9** `verify_scope` at `factory dispatch`; **33.10** the derived CFE pin.
  33.2 and everything after it depend on 33.1 — the measurement-first gate this Dream's § Gates named
  and Epic 28 bypassed. Batch:
  `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`.
- **2026-09-09 (Story 33.3 shipped)** — Ruling: the loop-home launcher shim **succeeds** through
  bmad-loop's ``adapters/profile.py`` seam. ``factory spin`` now folds
  ``read_repo_policy_defaults()`` (closing ``DW-FU-28-2-3``), and when the wire layer is enabled it
  writes a loop-home ``.bmad-loop/profiles/<adapter>.toml`` overlay that points ``binary`` at
  headroom with ``launch_args = ["wrap", "<cli>", ...]`` (closing ``DW-FU-28-2`` for the claude-class
  adapters that declare a marshal ``[wrapper]``). Spin is **not** declared a two-layer-only engine:
  wire acts on spin the same way it acts on dispatch; derived-context and planning-graph remain
  dispatch/build-auto-only. Cost-sensitive drain for those two layers still belongs on
  ``factory dispatch``.

## 2026-09-16 — PR lifecycle — a story lands itself (folded from pr-lifecycle)

> **Superseded 2026-08-02 (dream consolidation).** Fully decomposed into `spec-pyforge-marshal`
> and the real PRD as FR-59 (landing rules are declared policy) and FR-60 (`marshal land` —
> idempotent open/label/wait/merge/retire/resync) — see
> [`docs/dreams/pyforge-marshal.md`](pyforge-marshal.md). See `spec-pr-lifecycle` for the
> retirement record.

# PR lifecycle — a story lands itself

## The Dream

The engine drives a story to a merged commit on its station branch and stops.
Everything after that — open the PR, know which labels this repo demands, wait
for the right checks, merge, delete the branch, resync — is done by a human
typing, or by an agent improvising the same sequence from memory each time.

A factory whose last mile is hand-driven is not unattended; it is unattended
until the interesting part. **The Dream is that a story that passed its gates
lands on `main` without anyone driving it**, and that the rules for landing are
declared once, in code, instead of remembered correctly five times a day.

> If a human has to remember the repo's merge rules, the repo's merge rules are
> not enforced — they are a habit with a good track record.

## Why now — one session's evidence

On 2026-07-31 a single session hand-drove **five PRs** (#170–#174). Every one
repeated the same sequence: create with `--repo` (this fork needs it), add the
`maintenance` label (the inherited linter reds on any non-`recipes/` change),
regenerate `environment.yaml` if `pixi.toml` moved (an **ungated** check the
label does not suppress), poll the linter, squash-merge, delete the branch,
resync `main`, and re-verify the working tree.

Every step is a written rule. Not one is enforced by anything but attention:

- **#170 merged with a broken detector.** It changed a file governed by
  `spec-pyforge-genesis` without moving that Spec's memlog. The only check that
  ran was the inherited linter, so it went green. Nothing in the landing path
  asked what the change had actually broken.
- **Label and env-sync are repo-specific and easy to miss.** They are documented
  in `CLAUDE.md` precisely because they are forgotten; documentation is what you
  write when a rule has no home in code.
- **Merge strategy is load-bearing and invisible.** Squash-merging once made
  Epic 10's story commits unreachable from `main` and froze a dashboard at 36/38
  with a ticking clock on a finished story.

The cost is not the typing. It is that the last mile is the one place with no
supervisor, no journal, and no verdict — in a factory whose whole claim is that
every stage has all three.

## What is real

- **The engine lands on the station branch.** `bmad-loop` merges each story
  worktree into `loop/<slug>` with a recorded subject. That much is automatic
  and durable.
- **From station branch to `main` is entirely manual.** No tooling owns it.
- **The pieces exist, unassembled:** `gh` is provisioned, the checks exist
  (`linter`, `detectors`), the merge-subject contract is already Marshal's
  (story 1.2), and `marshal config` already knows how to compose and record a
  policy — which is where landing rules belong.

## What is real, part two — the last mile has no idea a run is happening (measured 2026-08-09)

`marshal land` shipped and does what CAP-2 asked: open/label/wait/merge/retire/resync, no
human in the sequencing loop. Operating it during a **live** run exposed two things the
Dream never considered, because when it was written landing happened *after* a run, never
*during* one.

- **`land` would have destroyed a running fleet.** Its head branch is *the loop-home station
  branch* (`cli/land.py` resolves `head_branch` to exactly that), and
  `landing_branch_retirement` defaults to **True**. Invoked while bmad-loop was mid-story on
  `loop/pyforge-doctor`, it would have merged and then **deleted the branch the harness was
  actively merging stories into**. Nothing in the verb asks whether a run is in flight. It
  was avoided on 2026-08-09 only because a human read the source first — which is not a
  safety mechanism.
- **"Resync" does not mean what the operator needs it to mean.** `landing_resync` resyncs
  the **feed**; `landing_resync_commands` defaults to empty. Nothing brings the loop home's
  station branch back to `main` after a landing, so it drifts from the moment the first PR
  merges. Measured the same day: `loop/pyforge-doctor` **5 commits behind main** minutes
  after its own stories landed, and — before that — **8 PRs behind** on origin between runs,
  reported clean by every detector.

Both are the same shape as the durability finding of the same day: **the verb is right, its
awareness of context is missing.** A last mile that cannot tell whether the road is still in
use is not finished.

## The frontier

- **Landing as a policy surface, not a script.** Required checks, merge
  strategy, label rules, branch-delete behaviour, and the env-sync trigger
  declared in `EffectivePolicy` with provenance — the same treatment gates got.
  A repo states its rules; Marshal executes them.
- **`marshal land <story>`** — open, label, wait, merge, delete, resync. Idempotent
  and re-entrant, because the interesting failure is a half-landed story: PR open,
  checks green, merge never issued.
- **Refuses, like teardown does.** Story 1.8 established the shape — a
  destructive step that will not proceed on unmerged work without an explicit
  flag. Landing needs the same: no merge on a red required check, no merge past
  an unacknowledged advisory finding, no silent force.
- **A verdict and a paper trail for the last mile.** Which checks were required,
  which passed, what merged, under whose authority — the audit triad applied to
  landing ([[fidelity-enforcement]]: Marshal builds, Doctor judges, Scribe records).
- **Unattended is the point.** A run that ends with "somebody should open a PR"
  has not ended.

## What this is not

Marshal's Epic 4 (*landing with a durable paper trail*) is about the record a
landing leaves. This is about **performing** the landing at all. They meet, and
the record is worthless if the act is still manual.

It also does not touch the engine — **wrap, never absorb** holds. `bmad-loop`
deliberately leaves this gap open; Marshal fills it *around* the engine, in the
supervisor, exactly as it does for provisioning and teardown.

## Kinships

[[pyforge-marshal]] (this resolves an open question its Spec parked —
see the log below) · [[durable-runs]] (both are about work surviving the gap
between stages; that one saves it, this one lands it) ·
[[fidelity-enforcement]] (the required-checks decision is a gate question, and
today's advisory CI is why "merged green" and "actually green" can differ) ·
[[pyforge-doctor]] (holds the verdict on Marshal's own rows) · [[pyforge-charter]].

## Realization log

- **2026-08-09 (later)** — Reopened again, for the half FR-173 missed. That FR
  makes a LANDING leave the home current; it says nothing about pushing the
  station branch, and — decisively — a landing done **by hand** never runs that
  code at all. Every landing on 2026-08-09 was `gh pr merge`, so the eight loop
  homes drifted **33–74 commits** behind main with nothing reporting it, and
  origin's `loop/*` refs drifted further still. The cost was not cosmetic:
  mason's stale home made the S-13.7 surface guard silently stop biting (0/3
  reconciled, against steward's 4/4 from a current home) and **nothing failed and
  nothing was logged**. The durable fix is therefore a CHECK at the chokepoint
  every spin must pass — preflight — rather than a promise attached to a landing
  path that can be bypassed.

- **2026-08-09** — Reopened after operating `marshal land` alongside a live 9-story run.
  Two gaps, neither of which existed when the Dream was written because landing was then a
  post-run act: the verb retires the station branch with no live-run guard, and its
  "resync" is the feed rather than the loop home's own currency with `main`. Recorded here
  rather than as a new

*(truncated in fold; original file remains archived)*


## 2026-09-16 — Two ways to finish a story, and Marshal has only ever heard of one (folded from quick-dev-reconciliation)

# Two ways to finish a story, and Marshal has only ever heard of one

## The Dream

A human can run `bmad-quick-dev` directly against any station's codebase, right
now, with no Marshal involvement at all — it is a generic BMAD skill
(`.claude/skills/bmad-quick-dev/`), documented in `pyforge-marshal`'s own
architecture doc as a parallel choice to the loop, not something the loop
drives: `architecture-bmad-infra.md:1003`'s flow diagram shows the fork
explicitly —

```
        ┌───────┴────────┐
        │ attended       │ unattended
        ▼                ▼
4a. bmad-quick-dev   4b. bmad-loop drives DEV→VERIFY→REVIEW→VERIFY→COMMIT
    / bmad-dev-story     in a loop home (~/.bmad-loops/<slug>), one worktree
                         + branch per story, squash-merged
```

— two labelled, equally legitimate branches of the SAME step, never a
Marshal-orchestrated choice. `architecture-bmad-infra.md:455` describes
`bmad-quick-dev` as one of BMAD's four implementation skills ("implement any
intent against existing conventions"); nothing in that description, or
anywhere else `pyforge-marshal`'s own source was searched, treats it as
something Marshal is aware of. A repo-wide grep of
`src/shared/packages/pyforge-marshal/` for `quick-dev` / `quick_dev` returns
**zero matches** — every hit in the project lives in planning prose
(`architecture-bmad-infra.md`, `development-guide.md`,
`source-tree-analysis.md`), never in `core/`, `cli/`, `adapters/`, or a
schema.

That absence is not cosmetic — it is a real hole in the ledger a run-loop
story finishes into. `sprint-status-ledger.yaml`'s own header names the
mechanism precisely: it is "the TRACKED twin of
`implementation-artifacts/sprint-status.yaml`" promoted by
`scripts/promote_sprint_status.py`, and that script's docstring is explicit
about who writes the source of truth it promotes — "**bmad-loop** marks a
story `done` at DEV completion" (`scripts/promote_sprint_status.py:24`). The
`development_status:` map underneath (`sprint-status-ledger.yaml:17-`) is a
flat `<story-key>: done | backlog` vocabulary with no third value and no
sibling field for *how* a story reached `done`. A story a human finishes by
hand through `bmad-quick-dev` never touches this map at all — bmad-loop never
ran, so nothing ever calls the code path that flips its key to `done`. The
work can be real, tested, merged to `main`, and durable, and the ledger will
still show it as `backlog` forever, because the only thing that promotes a
key out of `backlog` is a signal only the loop emits.

The same gap repeats one layer up. `marshal status`'s fleet view
(`core/status.py::derive_home_state`, Story 5.1, `epics.md:1131-1140`) derives
"what is running?" from journals and run state — "never from a hand-maintained
file" is the AD-5 promise the story's own acceptance criteria state
verbatim. A quick-dev session against a station's codebase leaves no journal
entry at all: no run id, no story-sequence record, nothing `derive_home_state`
can read. So Marshal cannot distinguish "the loop is between stories, nobody
is working" from "a human just landed a real story by hand" — both report
identically as an idle home, because the fleet view was built to answer "is
the loop doing something," never "did the work get done."

Epic 4's landing machinery — the one place `pyforge-marshal` already builds a
durability guarantee around a *finished* story — makes the same assumption.
Story 4.1's spec-promotion predicate (`epics.md:792-810`) promotes "every
merged story's spec... automatically and durably" the moment bmad-loop's own
journal shows a merge; Story 4.6's reconciliation (`epics.md:893-912`) closes
an open `intent` entry only against evidence bmad-loop itself produced (a
commit sha, a worktree absence, a PR number tied to *its own* run). Neither
story has any path for "a spec that was never in loop scratch to begin with,
because a human wrote and merged it directly." A quick-dev'd story's spec —
if one exists at all — gets none of the promotion, durability, or
reconciliation guarantees a loop-landed story gets by construction.

This is a genuine gap, not a rediscovery: a repo-wide search of
`pyforge-marshal`'s 120-story backlog (`epics.md`) for "quick-dev",
"mixed mode", "hand-implement", or any reconciliation language pointed at a
non-loop completion path returns nothing. The one open question that brushes
against it — PRD `Q-16`, "the route-versus-contain boundary, per `bmad-*`
skill Marshal routes to" (`prd.md:961`) — is about whether Marshal should
*invoke* a BMAD skill on an operator's behalf, a different question from this
one: this Dream is not about Marshal calling `bmad-quick-dev`, it is about
Marshal noticing, after the fact, that someone already did.

## What it looks like when real

- An operator can hand-pick any backlog story and run `bmad-quick-dev`
  against it directly — today's workflow, unchanged — while that station's
  `bmad-loop` run sits between stories, or is actively mid-run on a
  **different** story, and Marshal's own tracked state stays coherent either
  way.
- After that quick-dev session lands (merged to the integration branch, by
  whatever path the operator used), something folds its completion into
  `sprint-status-ledger.yaml` — or the mechanism that feeds it — so the story
  reads `done`, not `backlog`, without an operator hand-editing a generated
  file.
- The recorded fact distinguishes *how* the story reached `done` — via
  `bmad-loop` or via `bmad-quick-dev` — so `marshal status` / the fleet
  dashboard can show it, and nobody has to reconstruct the answer from commit
  archaeology (the exact failure mode `promote_sprint_status.py`'s own
  docstring already documents for a different reason — PR #132's squashed
  merge subjects).
- A quick-dev'd story's spec gets the same promotion/durability treatment
  Story 4.1 already gives a loop-landed one — "promoted" still means "will
  still exist next week," regardless of which path produced it.
- None of this requires quick-dev to change, or to run *through* Marshal.
  The reconciliation happens by observing what already happened (git,
  merged specs, story identity) — the same "derive, never hand-maintain"
  discipline AD-5 and AD-33 already hold Marshal's status/journal split to.

## Constraints

- **Not a routing change.** This Dream does not decide whether Marshal ever
  *invokes* `bmad-quick-dev` on an operator's behalf — that is PRD `Q-16`'s
  open question, untouched here. This is strictly about reconciling a
  completion that already happened outside Marshal's control back into
  Marshal's own tracked state.
- **Not a concurrency mechanism.** "Mid-run, a different story" means the
  ledger stays coherent when a quick-dev completion is folded in around a
  live loop run — it does not mean Marshal orchestrates the two happening
  *simultaneously*, or arbitrates a conflict if they ever touch the same
  files. Any locking/coordination machinery for genuinely concurrent writers
  is out of scope for this Dream.
- **Stays inside AD-5/AD-33.** Whatever detects a quick-dev completion reads
  git (repository facts) and existing spec/story-identity artifacts — never
  a new hand-maintained flag, and never something the loop's own journal
  format has to grow a special case for.
- **No implementation detail is prescribed.** Whether detection watches merge
  commits, story-key naming, spec promotion, or some combination is a design
  decision for the Spec and its downstream story, not settled here.

## Realization log

- **2026-08-11** — Captured after the operator asked why `bmad-loop`-driven
  unattended development is slower/costlier than a supervised `bmad-quick-dev`
  session, and what Marshal could do to let development mix modes. Confirmed
  via grep: zero references to `quick-dev`/`quick_dev` anywhere in
  `src/shared/packages/pyforge-marshal/` (only in planning prose). Confirmed
  via `epics.md`: no existing FR/epic/story covers mixed-mode tracking.
  Queued as a Dream rathe

*(truncated in fold; original file remains archived)*


## 2026-09-16 — Regenerable factory — every line of code under a spec it can be rebuilt from (folded from regenerable-factory)

# Regenerable factory — every line of code under a spec it can be rebuilt from

## The Dream

No orphan code. Every realized surface in the repo — even the ones that
shipped before the Dream-first model existed — gets its chain **backfilled**:
Dream → PRD (where product-scope) → spec → code, so the factory can *generate
and change any code* through idea → spec → BMAD, never by hand-editing outside
the contract. The spec stops being a build record and becomes the **living
change-surface**: to alter behavior you alter the spec and re-derive.

The proof of the dream is the **regeneration drill**: pick a governed module,
delete it, and rebuild it from its spec alone — the result passes the same
gates the original did.

And because every file maps to a contract, **drift checks run on all code**:
an out-of-band edit to any governed surface is detected, named, and reconciled
— the two-layer loop (cheap deterministic detector + BMAD skills as
reconciler) that already keeps the factory's own artifacts honest, generalized
repo-wide.

## What is real (the prototype already runs)

- **The sync loop** — `bmad-drift-check` (pins, counts, coverage
  completeness: *every project file must be classified*, baseline-vs-live
  surface change) + reconciler skills (`bmad-document-project`,
  `bmad-generate-project-context`, `bmad-correct-course`) + re-stamped
  baselines. This Dream is that loop, applied to everything.
- **The transformer** — `bmad-spec` distills brownfield code + docs into the
  five-field Spec with stable CAP-IDs and an append-only memlog; re-derives
  on update instead of hand-patching. Piloted on [[design-code-bridge]].
- **The map** — 24 Dreams, no-straggler policy: every shipped surface already
  traces to a Dream; what's missing is the spec layer beneath the realized
  ones ([[packaging-factory]], [[enterprise-airgap]], [[modernist-identity]],
  [[fleet-stewardship]], [[factory-console]] have no BMAD spec;
  [[pyforge-marshal]] and [[fleet-stewardship]] lean on legacy Tier-1 specs).

## The frontier

- **Backfill waves** — brownfield-`bmad-spec` each realized Dream, smallest
  first as the dogfood pilot ([[factory-console]]), PRD-scope only where the
  surface is a product (the CFE skill under [[packaging-factory]]).
- **The surface map** — each backfilled spec declares the code paths it
  governs; a repo-wide checker enforces (a) coverage: every tracked source
  file belongs to some spec's surface, (b) drift: a governed file changed
  without its spec/memlog moving → finding, reconcile or re-derive.
- **The CI gate** — surface check joins `llms-full-check` / `bmad-drift-check`
  as a red-on-drift detector.
- **The drill** — one successful regeneration from spec alone, as the
  program's success signal.
- Decks stay a communication decision ([[pyforge-herald]]'s backlog —
  [[packaging-factory]] first); they proclaim the chain, they don't gate it.

## Kinships

[[pyforge-genesis]] (the operating model this completes — brownfield adoption
implies backfill) · [[pyforge-marshal]] (BMAD executes every change) ·
[[pyforge-warden]] (drift gate temperament: never false-green) ·
[[agent-portability]] (the Spec is what makes regeneration
framework-neutral) · [[pyforge-charter]].

## Realization log

- **2026-07-23** — doctrine decided (user call, inverting the
  "no retroactive ceremony" default): backfill PRDs/specs for realized work
  so any code is changeable through the pipeline; Dream seeded.

- **2026-09-09 (fleet readiness pass — operator-approved batch)** — Currency, status unchanged
  (`realized`). The **drift half is live**: `gather_spec_surface` over the tree returns 6 entries, 5
  informational plus *"every tracked file governed or allowlisted; no drift"*. The **drill half has
  no live oracle**: the 2026-07-23 PASS (`spec-factory-console/drill-evidence.md`) was against
  `generate.py`, and `spec-factory-console/SPEC.md:78` now records *"regeneration drill is historical
  — `generate.py` is gone."* So the estate holds no *re-runnable* proof of this Dream's own central
  claim. The successor drill is named in the Unifying Dream (§ *What the Foundry becomes*) as
  foundry's own construction, rebuild-with-the-archive-as-oracle — **no new drill is owed in
  local-recipes**. Batch: `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`.

## 2026-09-16 — A one-line doc fix and a cross-module rewrite get the identical review (folded from risk-tiered-review-depth)

# A one-line doc fix and a cross-module rewrite get the identical review

## The Dream

Every station's `marshal-policy.toml` sets `gate_mode = "none"` for unattended
operation, and its own comment is explicit about what that does and does not
skip: "`gate_mode`: unattended (operator direction, 2026-07-26). This is the
HUMAN approval gate ONLY — **the independent reviewer still runs on every
story**" (e.g. `_bmad-output/projects/pyforge-marshal/planning-artifacts/
marshal-policy.toml:26-28`, the same comment cloned into all nine loop
homes). `core/policy.py`'s `DEFAULT_POLICY` backs that with two flat, global
ceilings — `max_dev_attempts: 2`, `max_review_cycles: 3`
(`core/policy.py:275-276`) — identical for a doc-only story and a
cross-cutting rewrite. There is no dial between "review runs" and "review
skips": every story pays the same review cost, regardless of how mechanical
or how consequential the change actually is. That flatness is a real
contributor to why an unattended `bmad-loop` run is slower and costlier per
story than a supervised `bmad-quick-dev` session — the loop cannot spend less
on a change that is obviously low-risk, because nothing in the policy or the
gate knows the difference.

There is already a real precedent for classifying a story's risk shape in
this exact codebase — `core/gate.py::classify_doc_only_declaration` (Story
2.4, FR-23, `core/gate.py:237-281`). Reading it in full: it is a **pure**
function of two already-gathered facts — `declared_doc_only` (the story's own
declaration) and `has_uncommitted_changes` (from `VcsPort`) — with **no** I/O
of its own. It fails exactly one combination: no worktree changes AND not
declared doc-only, "the one combination indistinguishable from a story that
silently failed to do its work" (`core/gate.py:250-253`). Every other
combination — declared-with-no-changes, declared-with-changes, or
undeclared-with-changes — passes unconditionally. Its blast radius today is
narrow and singular: it feeds exactly one finding code (`MRS-GATE-006`) into
gate PASS/FAIL, and it says nothing at all about review — it decides whether
a story with no diff is allowed to close, never how much scrutiny a story
*with* a diff receives. It is real, working evidence that "classify a
story's risk shape as a pure function of a declaration plus an observed
fact" is an idiom this codebase already trusts — but it has never been
pointed at review depth, only at gate pass/fail for the no-change case.

Anything that reaches toward review depth has to reckon with `DW-AD23-3`
first. `_bmad-output/policy-defaults.toml:19-36` documents the incident in
full: the upstream `bmad-loop` default for `max_followup_reviews` was `1`,
and that single cap "damped five still-recommended follow-up reviews across
three projects (atlas 10.5/10.6, marshal 1.1, warden 6.3/5.1) into a
gitignored ledger" — real, reviewer-recommended follow-up work that
vanished because the cap silently discarded it once a story converged. The
incident is the reason `deferred-work-check` exists at all, and the reason
the repo-wide value is now `2`, "explicitly... with reasoning inline," never
left at a default nobody examined (`core/policy.py:277-286` carries the
matching in-code comment). The lesson is precise: **a cap that is too low
doesn't fail loudly — it produces a clean-looking envelope while dropping
real, reviewer-identified work.** Any mechanism that lets a story's review
run cheaper or fewer cycles has to avoid reproducing exactly that failure
mode for a class of stories, not just for the repo as a whole.

## What it looks like when real

- A story can be classified — mechanically, from something already true
  about it (its own declaration, its diff shape, or both) — into a review
  weight *before* review runs, the same "pure function of already-gathered
  facts" idiom `classify_doc_only_declaration` already establishes.
- **The independent reviewer still runs on every story, with no exception.**
  This Dream changes review *cost*, never review *occurrence* — the
  `gate_mode = "none"` boundary (human approval only, reviewer unconditional)
  is untouched.
- A low-weight story may run fewer review cycles or a cheaper review pass;
  a high-weight story is unaffected, or could even earn *more* scrutiny —
  the classification is a real signal, not a one-directional discount.
- **Any follow-up a review recommends is captured with the same durability
  `deferred-work-check` already enforces, at every tier.** A tightened cap
  for a low-weight story can never again cause a real recommendation to
  vanish into an unindexed ledger entry the way `DW-AD23-3` did — whatever
  this mechanism proposes has to be checked against that incident by name
  before it ships, not merely asserted safe.
- The tier a story's review ran at, and why, is visible in the same
  machine-readable envelope every other gate output already uses — never a
  silent choice.

## Constraints

- **Never skips the independent reviewer.** `gate_mode = "none"` already
  means "human approval gate only" — that boundary is load-bearing and
  stays exactly where it is. Nothing here reopens "does review run at all."
- **Never lowers `max_followup_reviews` (or an equivalent cap) below what
  `deferred-work-check` can still fully capture, for any tier.** `DW-AD23-3`
  is the concrete failure this constraint exists to prevent from recurring —
  cite it by name in the downstream Spec/story, not just in spirit.
- **Not a prescription of mechanism.** Which signal drives the
  classification (doc-only-style declaration, diff shape, surface size, a
  combination), which review lever it adjusts (cycle count, model choice, a
  cheaper lens set), and how the tier is surfaced are all design decisions
  left to the Spec and its downstream story.
- **Not model-tiering/adaptive-escalation.** A cheaper review *model* is one
  plausible lever this Dream names as a possibility, but choosing DEV-side
  models by difficulty, or adaptive escalation generally, is a separate,
  already-scoped investigation thread (a sibling effort, not this one) —
  this Dream does not decide or duplicate that mechanism.

## Realization log

- **2026-08-11** — Captured after the operator asked why `bmad-loop`-driven
  unattended development is slower/costlier than a supervised `bmad-quick-dev`
  session, and what could make unattended runs faster without weakening the
  review guarantee. Confirmed via `epics.md`: no existing FR/epic/story ties
  story risk to review depth or cycle count — `classify_doc_only_declaration`
  (Story 2.4) is the only risk-classification precedent, and it feeds gate
  pass/fail, never review scheduling. Read `DW-AD23-3`'s incident comment in
  full before drafting the Constraints section, specifically so this Dream
  cannot be read as license to shrink `max_followup_reviews` again. Queued as
  a Dream rather than touched directly — `core/gate.py`, `core/policy.py`,
  and `_bmad-output/policy-defaults.toml` were deliberately left untouched
  pending the Spec/story chain. Companion pain, same investigation, separate
  Dream (different subsystem, different epic):
  [`quick-dev-reconciliation.md`](quick-dev-reconciliation.md).
- **2026-08-14** — Realized — Story 2.8 (FR-185) shipped `classify_review_tier`/`resolve_review_cycles` in `core/gate.py`. Status flipped and FR-185 backfilled into the PRD by the 2026-08-14 audit.

- **2026-09-09 (fleet readiness pass — operator-approved batch)** — **STATUS REVERSED, `realized` →
  `specified`, under the realization gate.** Story 2.8 shipped the mechanism and only the mechanism:
  `classify_review_tier` (`core/gate.py:724`) and `resolve_review_cycles` (`:768`) have **zero
  callers anywhere outside `tests/unit/test_gate.py`**. There is no producer of `declared_low_risk`
  (no CLI flag; no `low_risk`-shaped key in either `bmad-spec`'s or `bmad-build-auto`'s
  `spec-template.md`), no `VcsPort` call computing `changed_files`, and nothing in `cli/gate.py`
  calls either functio

*(truncated in fold; original file remains archived)*


## 2026-09-16 — Run state is a service — the loop's truth leaves the laptop (folded from run-state-one-publisher)

# Run state is a service — the loop's truth leaves the laptop

## The Dream

Every run the factory makes — a bmad-loop story, a dispatch wave, an MCP `start` — should
be a fact the estate holds, not a file an operator's laptop holds. Today the platform's
`/runs/` board can answer "what is running?" only for MCP starts, because the host's
supervisor store has exactly one writer: `publish_start` on the MCP path. The two marshal
supervisors that watch the runs which actually build the fleet — the loop sidecar and the
dispatch supervisor — write their truth to journals under `~/.bmad-loops`. The front door
cannot see those runs, a completed run's timing dies with the workstation that produced it,
and two stations (marshal's own `status`, doctor's story-status source) learn run state by
scraping that home directory.

The Dream is **one publisher**. Both marshal supervisors feed a single module that publishes
start, heartbeat, completion, per-story timing and the per-layer savings numbers to the
estate's run-state service. Marshal's `status`, doctor's story-status source and the Hub's
Track all read the published plane. The home directory keeps the worktrees and journals that
bmad-loop itself needs; it stops being anyone's *source of run truth*.

> A run that only its laptop knows about is a run the estate cannot govern.

## Why now — measured, not feared

The 2026-09-09 currency review found nine "done but not in effect" capabilities. Eight are
closed. This is the ninth, and on 2026-09-12 every finding behind it is still live:

| Finding | Where it is visible |
|---|---|
| Marshal imports `django_pyforge` **zero** times | `grep -r django_pyforge src/shared/packages/pyforge-marshal/src/` → no files |
| The loop home resolves to the operator's home | `pyforge-marshal/src/pyforge/marshal/cli/init.py:336` (`BMAD_LOOP_HOME_ROOT` override, else `Path.home() / ".bmad-loops"`) |
| Doctor scrapes the same home | `pyforge-doctor/src/pyforge/doctor/sources/marshal.py:544`; the registration comment at `sources/__init__.py:223` says "preserve, don't redesign" |
| The only writer of `run_state` is the MCP path | `django-pyforge/src/django_pyforge/supervisor.py:435` `publish_start` — verifies an assertion, mints a handle, enqueues a Celery task |
| The sweep assumes a Celery task | `supervisor.py:681` `sweep_lost_runs` marks a live row `worker_lost` when no worker reports its task id — an external process would be swept as dead |
| The front door already forbids scraping | `src/platform/tests/test_front_door_queries_supervisor.py:235` asserts no laptop state is read |
| Four more home-dir readers sit outside both stories | steward `cli.py` and `upgrade.py`, scribe `promote.py`, doctor `sources/__init__.py` (story-status) |
| The two stories block each other by design | steward `49-8` and marshal `33-4` both `blocked` in the tracked ledgers; 33.4 says "joint landing with 49.8", 49.8 says "until marshal's Track story exists" — it exists, nobody has dispatched the pair |
| The contract's own verdict | Unifying `SPEC.md` CAP-17 `verified:` — "marshal loop homes still filesystem-backed; deployed egress-blocked proof unexercised" |

Every precondition the two stories name is already met: steward 49.1 (the verified column)
is done, marshal 33.1 (the benchmark with real savings getters) is done and the five savings
fields exist at `adapters/harness_bmadloop.py:743-768`, and doctor recorded the incoming
surface claim for `marshal.py:544` in its memlog on 2026-09-09. What is missing is not a
dependency. It is the act.

## What it looks like when real

- **The board shows the loop.** The front door's `/runs/` board lists a live bmad-loop story
  beside the MCP runs, in a deployed, egress-blocked namespace with no operator home mounted.
- **Timing outlives the workstation.** A completed run's per-story duration is queryable
  after the laptop that ran it is gone — the same query that already works for MCP runs.
- **One writer, provably.** `grep -r django_pyforge src/shared/packages/pyforge-marshal/src/`
  returns exactly one module, and both supervisors call it. A second importer fails a test.
- **Savings are numbers.** The per-layer savings fields on a published run carry the values
  Story 33.1 measures, not stubs.
- **The readers moved.** `marshal status`, `cli/init.py`'s home resolution and doctor's
  `marshal.py:544` read the published plane. The `~/.bmad-loops` literal remains only where
  bmad-loop's own worktrees and journals live, never in a run-state read.
- **The host sweeps by heartbeat.** An externally-published run is judged live by its
  heartbeat, not by asking Celery whether a task id exists.
- **The verified line is rewritten by evidence.** CAP-17's `verified:` names the deployed
  exercise — a live loop run on the board, in the namespace, with the home unmounted — and
  Epic 49's last open row closes on effect, not on a ledger flip.

## Constraints / Non-goals

- **No second ledger.** The supervisor store in `django_pyforge` is the run-state service;
  nothing publishes anywhere else and no station keeps a private copy of the fact.
- **Identity is carried, never trusted.** The publisher presents an assertion the host
  verifies (CAP-6's shape), or a dated, recorded exception — a forwarded header or a shared
  laptop secret is not an identity.
- **The loop home stays.** This Dream retires *reads of run state* from `~/.bmad-loops`. It
  does not delete the directory, move bmad-loop's worktrees, or change where journals land.
- **External runs stay external.** A bmad-loop run is not wrapped in a Celery task to make it
  publishable; the host learns to hold a run whose process it does not own.
- **Mints nothing already minted.** Unifying CAP-17 owns the criterion and token-economy
  CAP-18 owns the publisher; the Spec derived from this Dream binds to both and names only
  what neither covers — the host-side non-Celery publish and sweep path, the deployed proof,
  and the four residual home-dir readers.
- **Cross-station by construction.** The host-side path is steward's surface
  (`django-pyforge/**`), doctor's read is doctor's — each station records the incoming
  surface claim in its own memlog before code lands, or `spec-surface-check` reds the merge.
- **Realized on effect.** The Dream flips to `realized` when the board shows a loop run in
  the deployed namespace, never when the two ledger rows read `done`.

## Kinships

[[pyforge-unifying-strategy]] (CAP-17 — the criterion's home; steward Story 49.8 is its
in-effect story) · [[marshal-token-economy]] (CAP-18 one publisher + CAP-7 savings telemetry;
marshal Story 33.4 is the implementation story) · [[intelligence-hub]] (`hub:CAP-3`, the Track
this publisher also feeds) · [[capability-effect-check]] (the sibling relay from the same
2026-09-09 batch, and the check that will report this capability until it is reached) ·
[[durable-runs]] (the ancestor: work survives the machine that made it — this is its
run-state half) · [[fleet-status-supervisor-fallback]] (`derive_home_state` — the reader whose
truth moves off the disk) · [[pyforge-marshal]] (the station; both supervisors) ·
[[pyforge-doctor]] (`sources/marshal.py:544`) · [[pyforge-steward]] (the host's supervisor
store and the deployed proof).

## Realization log

- **2026-09-12** — Seeded (operator ruling: every effort enters through the Dream-to-Code
  chain, gap-closure included — no story drafting or dispatch before a Dream and its Spec).
  Captured after a live re-verification of the 2026-09-11 infographic's § 18 row "CAP-17 run
  state — OPEN · 33.4 + 49.8 blocked": the tracked ledgers still read `blocked`, marshal still
  imports `django_pyforge` zero times, `cli/init.py:336` and doctor's `marshal.py:544` still
  resolve the home directory, and `publish_start` is still the only writer of `run_state`. Two
  design facts found in that pass that neither story text names: the host sweep
  (`sweep_lost_runs`) would mark an externally-published run dead for l

*(truncated in fold; original file remains archived)*


## 2026-09-16 — One spec's clean reconciliation should clear another's, when they share a file (folded from spec-surface-overlap-tolerance)

# One spec's clean reconciliation should clear another's, when they share a file

## The Dream

`spec-surface-check`'s own drift half (`spec-regenerable-factory` CAP-3) checks every
governing spec of a changed file **independently**: each must show its own memlog moved
and names the file, or it gets flagged, with zero awareness that another spec governing
the *same* file may have already reconciled it cleanly. A file is routinely governed by
more than one spec at once — a station's own broad kernel spec (`spec-pyforge-<station>`)
and a narrower, actively-worked spec both match it — and the checker's own code confirms
this is not an edge case: `_governed_and_ungoverned` explicitly assigns a file to *every*
matching spec, not one winner. When the kernel spec's memlog stops moving for routine
story work (which is normal — routine work reconciles against the narrower spec that
actually owns the story), it accumulates permanent, un-clearable `drift-presumed` noise
for every file the narrower spec already handles correctly.

> A file's change is accounted for the moment *some* spec that governs it says so — not
> only when *every* spec that happens to also govern it says so.

## Why now — measured, not feared

Found and fixed at data-scale on 2026-09-12 (`maintenance/kernel-spec-surface-overlap-2026-09-12`,
PR #1288): 178 `drift-presumed` findings across 17 specs, all the identical shape — a
kernel spec double-claiming files a narrower, currently-clean spec already reconciles.
The fix landed was `surface-drift-exclude:` entries naming each specific overlapping
file per kernel spec — safe, mechanical, and immediately effective (0 findings fleet-wide
afterward), but it treats the *symptom* file-by-file. It does not stop the same pattern
from recurring the next time a new narrow spec is minted under a kernel spec's remaining
surface, which is the normal, expected shape of how this factory's planning tree grows —
every station starts as one kernel spec and decomposes into dozens of story-scoped specs
over its life. The `spec-regenerable-factory` CAP-3 contract that governs this checker
was itself never written with multi-owner overlap in mind: its own intent language reads
"a governed file changed... without *the spec's* memlog moving" — singular, one spec, by
design, at the time it was written.

## What it looks like when real

- A file governed by two or more specs is `drift-presumed`/`drift` **only when none of
  its co-governing specs' memlogs name the change** — not "only when every one of them
  does."
- A newly-minted, narrow story spec that correctly reconciles a file it shares with its
  station's kernel spec produces **zero** finding against the kernel spec for that file,
  automatically, with no manual `surface-drift-exclude:` entry ever required.
- The `surface-drift-exclude:` entries this Dream's own motivating fix landed (PR #1288)
  become historical artifacts of a workaround, not a pattern anyone needs to keep hand-
  maintaining going forward — new overlaps self-resolve.
- A genuinely unreconciled change — one where *no* co-governing spec's memlog explains
  it — is still caught exactly as today. The fix narrows a false-positive, it does not
  widen what counts as accounted-for.

## Constraints / Non-goals

- **Never weakens real drift detection.** A file with zero co-governing specs, or where
  every co-governing spec's memlog is silent on it, must still flag exactly as it does
  today. This is strictly a false-positive fix for the multi-owner case, not a general
  loosening.
- **Not a redesign of spec-surface-check's coverage half.** Coverage (`ungoverned`) stays
  exactly as it is — every tracked file needs ≥1 governing spec or an allowlist entry.
  Only the DRIFT half's per-spec independence changes.
- **Not retroactive rewriting of `surface-drift-exclude:` entries already landed.** PR
  #1288's entries stay as a correctness fallback and a record of what was found; this
  Dream's Spec does not require removing them once the detector itself improves.
- **`pyforge-doctor` owns the code, `pyforge-marshal` owns the contract** — `spec-
  regenerable-factory` CAP-3 (shipped, `pyforge-marshal`) is the capability this Dream
  extends; the implementation lives in `pyforge.doctor.sources.chain` per the existing
  cross-station convention (each station records its own incoming surface claim in its
  own memlog before code lands).

## Kinships

[[regenerable-factory]] (CAP-3 — the shipped capability this Dream extends, not
replaces) · [[mcp-host-real-station-tools]] (the sibling precedent: a gap found in an
already-shipped spec's own mechanism, closed same-day with a new, narrowly-scoped Dream
rather than reopening the shipped one) · [[pyforge-marshal]] (owns `spec-regenerable-
factory`) · [[pyforge-doctor]] (owns `pyforge.doctor.sources.chain`, the actual checker
code).

## Realization log

- **2026-09-12** — Seeded (operator ruling: gap-closure enters through the Dream-to-Code
  chain like any other effort). Found reconciling 178 `drift-presumed` findings across 17
  station-kernel specs (PR #1288): every one traced to the same root cause, confirmed by
  reading `pyforge.doctor.sources.chain`'s own `_governed_and_ungoverned` (a file is
  assigned to *every* matching spec, not one) and `_drift_findings` (drift is computed
  per-spec, independently, with no cross-spec awareness at all). The immediate 178 were
  closed with `surface-drift-exclude:` entries (a data-level, per-file fix, safe and
  already proven for two prior specs this same session); this Dream captures the
  root-cause fix so the same class of noise does not keep recurring as new narrow specs
  get minted under existing kernel specs. Next act: `bmad-spec` derives the Spec under
  `pyforge-marshal`.
- **2026-09-16** — `dreamt` → `realized` (fleet-inbox-disposition). Marshal Epic 42
  (Stories 42.1–42.2) shipped in PR #1378: overlap OR on a clean co-governor. Record:
  `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-inbox-disposition-2026-09-16.md`.

## 2026-09-16 — A drift gate nobody can clear, and a drift signal anyone can launder (folded from surface-drift-reconciliation)

# A drift gate nobody can clear, and a drift signal anyone can launder

> The enforcement half of [[regenerable-factory]]. That Dream built the surface
> map and the drift checker; this one makes the checker's verdict **clearable**
> and **trustworthy**, which it is not today.

## The Dream

`scripts/spec_surface_check.py` is the instrument that makes the regenerable
factory real: it proves every tracked file is governed by a spec surface, and
that no governed file drifted out from under its contract. It has carried a
large red for weeks — **61 findings on `main`** — and the reason is not that
the repo is 61 kinds of broken. It is that the detector has two defects that
make its verdict *unactionable in one direction and untrustworthy in the other*:

**You cannot clear it honestly.** `--write-baseline` stamps **every** spec in
one write. So the sanctioned fix for a single `[no-baseline]` finding —
registering one spec that legitimately has no baseline entry — necessarily
accepts **every other spec's pending drift as correct**. Settling one spec
destroys the evidence for ~34 others. The honest move is therefore to leave the
finding standing, which is exactly why the red has persisted. *A gate nobody can
safely clear stops being a gate.*

**You cannot trust it either.** The drift pass short-circuits **per SPEC, not
per file**: `if b["memlog"] != cur["memlog"]: continue  # spec moved — code
changes are presumed reconciled`. So appending **any** memlog entry marks every
governed file in that surface reconciled — including files the author never
touched. The drift half is defeatable by unrelated activity, silently, and the
disappearance is indistinguishable from a real fix in the findings count that
the dashboard renders. The larger a surface's governed set, the more it
launders; this surface governs four detectors.

These two are the same disease from opposite ends: **the reconciliation claim is
made at the wrong granularity.** Baselines are stamped all-or-nothing when they
should be per-spec; drift is cleared per-spec when it should be per-file. Fix
the granularity and both symptoms go away — the gate becomes clearable one spec
at a time, and a memlog entry stops speaking for files it never mentions.

Behind that is a rule this repo already believes everywhere else: **never claim
green you did not measure.** A "presumed reconciled" blanket is a claim nobody
measured. Where reconciliation genuinely cannot be proven, the honest output is
a *visible, non-gating* signal — not silence.

## What it looks like when real

- **`--write-baseline --spec <name>`** stamps one spec by merging into the
  existing baseline, so a single legitimately-unregistered spec can be settled
  without blessing anything else. Unscoped `--write-baseline` still exists, and
  says plainly in its own help text that it accepts every other spec's pending
  drift.
- **A memlog reconciles the paths it NAMES.** When a spec's contract moved, each
  drifted file is checked against the memlog text; named paths clear, unnamed
  paths surface as a distinct, informational `[drift-presumed]` line rather than
  vanishing. The set is always visible; the operator decides.
- **The 61 findings are worked to zero by category, not by one blanket stamp** —
  every `[no-baseline]` scoped-stamped, every `[drift]` either genuinely
  reconciled through its spec (the surface changed → the contract moves) or
  scoped-stamped with the reasoning recorded, the two `[ungoverned]` files given
  a surface or an allowlist entry, the one `[stale-allowlist]` pattern removed.
- **The verdict is green and stays green** — the next out-of-band edit is caught,
  because the signal is finally trustworthy enough to act on. Note the detector
  already *runs* in CI (`.github/workflows/detectors.yml`, via the `scope=repo`
  registry subset) but is **deliberately advisory, not blocking** — an operator
  decision of 2026-07-31 that [[fidelity-enforcement]] records as still open.
  This Dream does not settle it: a signal worth gating on has to be true first,
  which is what this work is for.
- **Nothing is silenced to get there.** If a finding cannot be honestly cleared
  in this effort, it is recorded as deferred work with its reason, not
  suppressed.
- **A governed surface with no contract behind it is reported, not tolerated.**
  A Spec that declares a `surface:` but ships without a `.memlog.md` is
  **drift-blind**: its contract hash is the empty string, so the contract can
  never move, so no governed change is ever reconcilable — only stampable. That
  is the third granularity error in the same family, and the detector names it.

## What is real (measured 2026-08-08, on `main` at `cf885388fe`)

- **61 findings**, partitioned: **34 `[drift]`**, **24 `[no-baseline]`**,
  **2 `[ungoverned]`**, **1 `[stale-allowlist]`**.
- Drift concentrates in five specs — `pyforge-steward/spec-pyforge-steward`
  **23**, `pyforge-scribe/spec-team-memory` **5**, and 2 each in
  `pyforge-marshal/spec-fidelity-enforcement`, `spec-factory-console`,
  `spec-durable-runs`. The steward cluster is one Epic-2/3 delivery, i.e. a real
  surface change whose contract never moved — the detector is right about it.
- The two `[ungoverned]` files are
  `docs/governance/spec-pyforge-charter/{SPEC.md,.memlog.md}` — the Charter's own
  spec sits outside every surface and every allowlist entry. The instrument that
  polices the chain does not cover the document that defines it.
- The `[stale-allowlist]` entry is `pixi.toml`, which now matches nothing.
- Both defects were **reproduced live**, not read off the source:
  `DW-SURFACE-2026-08-08-1` records appending an unrelated allowlist note to one
  memlog dropping findings **63 → 61**, clearing two pending findings
  (`scripts/bmad_drift_check.py`, `scripts/dream_chain_check.py`) that the author
  never touched — recorded verbatim in that memlog under a `(NOT RECONCILED …)`
  entry so the information survived the finding.
  `DW-SURFACE-2026-08-08-2` records the all-or-nothing stamp.
- A throwaway prototype of both fixes was written and **reverted** on 2026-08-08
  once it was clear this is chain work, not a hand-patch. It established that the
  change is small and local to `main()` — scoped merge on the write path,
  per-file check on the read path — and that no other detector reads the baseline
  format. That is design evidence for the Spec, not an implementation.

## What is real, part two — the drift-blind Spec (measured 2026-08-09, on `main` at `7dde591811`)

The first four capabilities took the detector to **0 findings**. Working with the
green gate immediately surfaced a hole none of them covered, twice in two days:

- `spec-bmad-loop-forward-dependency-blindness` (2026-08-08) and
  `spec-bmad-module-provisioning` (2026-08-09) each shipped declaring a
  `surface:` and **no `.memlog.md`**. `contract_hash()` returns `""` for them,
  the baseline stores `""`, and `""  !=  ""` is never true — so `spec_moved` is
  permanently `False`. Every future governed change reports a hard `[drift]`
  whose only exit is `--write-baseline --spec NAME`. The sanctioned remedy the
  finding *prints* — "reconcile the spec" — is unreachable, because there is no
  contract to move. Both memlogs were created by hand once noticed.
- **Nothing reports the condition.** It is invisible while the surface is
  quiet and indistinguishable from ordinary drift once it is not — a Spec can be
  drift-blind for months and the gate stays green the whole time, which is the
  precise failure mode CAP-1..CAP-4 were written to end at two other levels.
- **It is not two instances, it is seven.** Measured across the fleet on
  2026-08-09: **7 Specs govern 396 tracked files with an empty contract hash** —
  `pyforge-mason/spec-conda-forge-expert-rebuild` **370**,
  `pyforge-herald/spec-herald-moments-2-4-live-backend` **18**, four marshal
  Specs (`spec-dashboard-project-path-derivation`,
  `spec-dream-to-code-model-self-verification`, `spec-pyforge-co

*(truncated in fold; original file remains archived)*


## Realization log

- **2026-08-08** — Captured. The 61 findings had been carried as "pre-existing,
  verified identical before/after" across several sessions (PR #322's own notes
  say so) — accurate as a non-attribution, but it had hardened into a reason not
  to look. Operator pushed back on exactly that: pre-existing explains why a
  finding is not yours, never why it stays. The two tool gaps were already filed
  as `DW-SURFACE-2026-08-08-1/2` with live reproductions; this Dream is the
  decision to fix them through the chain rather than patch the detector by hand.
  A prototype of both fixes was written, then reverted, to keep Dream-first
  ordering honest — its findings are recorded above as design evidence.
- **2026-08-09** — Reopened for the drift-blind Spec. CAP-1..CAP-4 shipped
  (PRs #326, #327) and the gate reached 0 findings; using it for two days then
  exposed the third granularity error, above. Deliberately reopened *this* Dream
  rather than seeded as a new one: it is the same instrument, the same disease
  (a reconciliation claim made where it cannot be measured), and the same
  Spec's success signal — a gate that can be cleared and a signal that can be
  trusted. A gate that is green because it cannot see is neither.
- **2026-08-09 (later)** — reopened once more for the 994 presumed, on the same
  principle that seeded the Dream: a standing number is a measurement, never a
  plan. Operator called it directly — *"working them down is genuine
  reconciliation, not noise-suppression."* The measurement above is what made it
  a day's work instead of a campaign.

- **2026-09-09 (fleet readiness pass — operator-approved batch)** — Status kept `realized`;
  **`spec-surface-drift-reconciliation` moves `in-progress` → `shipped`** with `open_questions: []`
  (both entries already began "RESOLVED": S-13.3 the Charter spec folder is allowlisted, S-13.4 the
  34 `[drift]` split 9 archived-spec baseline lag / 2 genuine console change / 23 steward files whose
  contract was already correct; the resolutions are retained in the Spec's memlog). Verified **in
  effect**, not by ledger: `pyforge.doctor.sources.chain::gather_spec_surface` over the live tree
  returns **6 entries** — five informational `[drift-presumed]` (pyforge-mason ×3, pyforge-steward ×2)
  plus the green verdict *"every tracked file governed or allowlisted; no drift"*. Against this
  Dream's own opening measurement (61 findings, then 994 presumed) the instrument is clear and the
  signal is trustworthy. Epic 13 (13.1–13.7) all `done`. Batch: `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`.
