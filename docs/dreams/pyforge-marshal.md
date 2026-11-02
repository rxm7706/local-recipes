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
  **Decomposed 2026-09-28:** (2) was closed as a side effect of Story 51.9 (CAP-251, merged
  `df813208e9` the same day). Finalize now fast-forwards the primary checkout's `main` after the
  land, so the supervisor's post-land read of `main` sees the merge, and every dispatch land since
  has read `completed`. That verdict still rests on the fast-forward, which finalize skips when the
  primary is dirty or not at `main`'s own tip, and the supervisor's post-land re-resolution never
  reads the landing it has just journaled: probed 2026-09-28 on today's code, a land journaled
  `landed` with local `main` behind still writes `stopped_externally`. The hardening → CAP-276 /
  Epic 67 / Story 67.1. (5) → CAP-275 / Epic 66 / Stories 66.1 (finalize carries a recommended
  follow-up review into the station's deferred-work ledger) and 66.2 (the one-time backfill across
  the eight ledgers, and the meta test that holds it); `DW-FU-51-2-1` points at both.
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
- **2026-09-20 (evening) — The supervisor entrypoint reaches the coverage floor.** Found at Story 53.2's
  landing: the touched-module coverage floor (steward 66.1's gate) measured
  `dispatch_supervisor/__main__.py` at 35% — 623 statements, 388 uncovered, 36% on `main` before
  53.2 touched 15 of its 1,895 lines. Operator ruling: land 53.2 (Epic 53's last story, the
  permanent fix for the landing ritual) behind a per-module, dated, story-bound floor exception
  in `coverage_thresholds.toml` (35%, `until` this story — the same shape as the per-module mypy
  baseline), and backfill the supervisor to the 80% floor next session. Kinships:
  `spec-pyforge-marshal` CAP-264 → Story 53.3; steward `spec-pyforge-steward:CAP-153` (the gate).
- **2026-09-20 (morning) — Proposed: the dispatch landing pays its own surface tax.** Operator
  ruling 08:40Z after seven autonomous landings in twelve hours (26.1, 61.3, 51.11, 29.1, 61.4,
  46.7, 65.x) each left `main` red on `spec-surface` until a human named the paths: *"we need
  a permanent fix, it's causing churn and rerun."* The cause is mechanical, not behavioural —
  item (3) of the 2026-09-19 entry, never decomposed: bmad-loop pays the tax because
  `harness_bmadloop::render_policy_toml` appends `python scripts/spec_surface_reconcile.py` to
  every loop's verify commands (the S-13.7 guard, CAP-239), so a loop story cannot go green
  until the session names its paths; `marshal factory dispatch` never got that guard —
  `dispatch_verify` runs only the station's `verify_commands`, the `harness_bmadbuild` prompt
  says nothing about memlogs, and nothing in the dispatch path runs `deferred_work_intake`, so
  a frontmatter deferral with no `location:` is refused later by hand too. Two halves, both
  needed: the producer is told and gated (as the loop is), and the landing reconciles from git
  facts as the safety net — `dispatch_land` names every governed path the branch changed on the
  owning Spec and each co-governor the detector names, stamps exactly those Specs, journals
  that it had to, then merges — so `main` is never red and no landing waits on a human. Not a
  blanket stamp: the entry is per-file naming derived from `git diff`, the stamp is scoped to
  the Specs whose drift is only this branch's files, and a session that reconciled itself
  triggers nothing. **Decomposed 2026-09-20:** CAP-261 / **Epic 53** — Story 53.1 (the
  dispatched session is told and gated: prompt obligation + the S-13.7 guard in its
  verification, the deferral `location:` rule), Story 53.2 (the landing reconciles from git
  facts and runs intake; journals MRS-DISP-047 when it had to). (2), (4), (5) of the 2026-09-19
  entry remain undecomposed.
  **(10), 09:35Z:** Claude Code 2.1.277's built-in `agents-md` mod stays out of any project with a
  `CLAUDE.md` unless `instructionFiles` is `claude-md-and-agents-md` — and that option is read from
  user settings or `--settings`, never the project. A dispatched `claude -p` session therefore
  depends on the operator's machine for whether nested `AGENTS.md` files (the atlas child) load.
  The launch pins it: the claude harness profile passes `--settings` with the mode inline. →
  CAP-262 / Story 46.11 (hand-driven the same morning; scribe 19.3 owns the surface side).
  **(11), 10:15Z:** `cli/watch.py` shells `pixi run -e local-recipes bmad-loop list|status`,
  `core/gate.py` names `-e local-recipes platform-ci-local`, and `adapters/scribe_cli.py` falls
  back to `.pixi/envs/local-recipes/bin` — but `local-recipes` is the recipe factory, not a
  runtime; only `pyforge-guild` exists where marshal runs (operator ruling, steward Dream
  2026-09-20 later). bmad-loop is marshal's own run-dep. → CAP-263 / Story 46.12 (the steward
  side is 63.6).
- **2026-09-24 — Proposed: the ledger promotion is a human's job, every single landing.**
  Doctor's Epic 24 (24.1-24.3) landed three-for-three today, and 24.2 and 24.3 each needed the
  identical manual repair: `marshal factory dispatch`'s automated finalize left the tracked
  `sprint-status-ledger.yaml` key at `backlog` after a genuinely-merged, review-passed story
  (24.2: PR #1577 merged, spec `status: done`; 24.3: PR #1579 merged, spec `status: done`).
  `sprint-ledger-sync --project doctor` refused both times — correctly — because the Tier-3 feed
  (`implementation-artifacts/sprint-status.yaml`) had drifted stale on 13-14 *unrelated* keys
  (24.2's promotion: 13 keys; 24.3's, run afterward: 14, including `24-2` itself reading
  `done → backlog` in the feed again despite having just been repaired). Both times the fix was
  the identical three-step manual dance — `--repair-feed` to pull the tracked twin's `done` keys
  back into the feed, hand-flip the one new key, re-sync — followed by a SEPARATE PR
  (`doctor-24-2-ledger-repair` #1578, `doctor-24-3-ledger-promote` #1580) that exists for no
  reason but to carry a two-line YAML diff. This is the same disease Epic 51/53 already named
  (silent-success ledger state, `dispatch_land_finalize` not writing what it should) in a new
  manifestation: it is not that finalize crashes or drops work — the dispatch completes cleanly,
  the PR merges, the spec reads `done` — it is that nothing durable records the promotion at the
  one place (the Tier-3 feed) `sprint-ledger-sync`'s regression guard trusts, so the very next
  landing on the *same station* inherits the drift and refuses too. Confirmed as a repeat, not a
  one-off, within a single session on the same station.
  **What it looks like when real:** a dispatched story that lands (PR merged, spec `status:
  done`) leaves the tracked ledger `done` with no further human action — no `--repair-feed`, no
  hand-edit, no second PR — because `dispatch_land_finalize` itself keeps the Tier-3 feed current
  as part of landing, the same way it already keeps the tracked spec current.
  **The mechanism, sketched:** the regression guard's refusal is never wrong about the *fact* of
  drift — the tracked twin genuinely is more current than the feed on those 13-14 keys — so the
  refusal itself should never require a human. The twin is the authoritative record (`sprint-
  status-ledger.yaml`'s own header calls it exactly that) and `--repair-feed` already does
  nothing but pull the twin's `done` keys forward into the feed — a strictly safe, one-directional
  operation with no judgment call in it. `dispatch_land_finalize`'s own promotion attempt should
  retry with that repair automatically applied whenever the refusal names only keys *other than*
  the one it is trying to promote, and land the two-line feed-catch-up as part of the SAME commit
  that flips the just-landed story — never a separate PR. The regression guard still refuses (and
  still needs a human) for the one case that is a genuine judgment call: the twin and the feed
  disagreeing about the *story being promoted itself*. That is the whole fix: stop treating "the
  feed is behind on unrelated stories" as a reason to block the story that IS ready, when the twin
  already knows the truth and repairing toward it is provably safe.
  Kinships: continues the `dispatch_land_finalize` reliability thread above (Epic 51
  CAP-249/CAP-252, Epic 53 CAP-261); owner `spec-pyforge-marshal`.
  **Re-scoped 2026-09-28 (operator ruling): the premise above was a misread.** Doctor 24.2's and
  24.3's automatic promotions never refused over the feed: finalize computed the promotion (its
  journaled INTENT names the key) and the push died on the pre-push hook's timeout — CAP-277 /
  Story 68.1. The automatic promotion never depended on the feed at all: it advances the landed key
  in the tracked twin directly and only warns about feed drift. Feed drift blocked only the *human*
  fallback, `sprint-ledger-sync` (`scripts/promote_sprint_status.py`), whose regression guard refuses
  a whole sync when the Tier-3 feed is stale on keys the operator is not promoting. **What it looks
  like when real now:** that hand sync repairs the unrelated drift itself — the same one-directional
  pull-forward `--repair-feed` does, only toward `done`, never touching a key the feed is promoting —
  and names every key it repaired, instead of refusing. `--allow-regression` stays the one way to
  move a key out of `done`. → CAP-265 (amended) / Epic 54 / Story 54.1, same key.
- **2026-09-27 — Proposed: a landing refusal outlives the landing.** The 2026-09-25, -26 and
  -27 fleet pictures each opened ATTENTION with `doctor: landing refused (1 finding(s)) --
  MRS-DISP-020` and the same line for marshal. Both refusals were real when written: doctor
  30.3's PR #1585 and marshal 46.6's PR #1597 could not be merged cleanly by `dispatch land`.
  Both PRs merged afterwards by another route (2026-09-24 and 2026-09-25), both refused head SHAs
  are ancestors of `origin/main`, and both keys read `done` in their tracked ledgers. The line
  stayed anyway, because `marshal status` projects the newest dispatch run's last `dispatch-land`
  OUTCOME and nothing written after a landing made by hand can reach that journal. Marshal's line
  clears when its next dispatch replaces the run; doctor has no backlog left, so its line would
  stay until someone dispatched doctor again. An ATTENTION line that is not an operator decision
  teaches the operator to skip ATTENTION. Recorded as
  `DW-marshal-disp020-stale-refusal-2026-09-25`; the 2026-09-26 retro filed it as "attention
  items that are not work".
  **What it looks like when real:** a refusal whose story has since landed on `main` is reported
  as exactly that — refused, then landed — and `fleet-picture` lists it among the lines that are
  not waiting on the operator. A refusal whose story has not landed, or whose landing status cannot
  be read, stays in ATTENTION unchanged.
  **The mechanism, sketched:** the journal and git each keep their own truth (the Spec's
  truth-partition constraint), so the refusal is never deleted or rewritten. `marshal status`
  reads git beside it: when the row's story key is among `main`'s corroborated merged keys (the
  check `dispatch land` already uses to answer ALREADY_LANDED), the row carries
  `dispatch_landing_superseded: true` next to the unchanged findings. `main`'s subjects are read
  once per sweep, as the failed-patch check already does. An unreadable `main` or policy leaves
  the marker off, so the refusal is never hidden on a guess.
  Kinships: the Story 53.2 review finding (I1) that first surfaced landing findings in status;
  the Story 28.25 rule that a resolved finalize failure is not an active escalation; owner
  `spec-pyforge-marshal`.
- **2026-09-27 (later) — Proposed: a loop-home refresh does not pay a preflight for `main`'s own
  commits.** `marshal refresh` fast-forwarded all eight `loop/<slug>` homes to `origin/main`
  (67 commits each) and pushed each branch; the repo's `pre-push` hook (steward CAP-154) ran the
  full ~10-minute `pr-preflight` per push — ~80 minutes to re-check commits `main` had already
  passed CI on — unless the operator set `PYFORGE_PREFLIGHT_SKIP=1` by hand. Steward first tried a
  hook-side "nothing new" skip (Story 68.2); review refused it: under pre-commit the hook sees only
  the first ref of a multi-ref push, so it cannot prove what the others carry, and a new commit got
  through. The proof belongs to the tool that makes the push. `refresh` has it: it fast-forwarded
  the branch to `origin/main` itself a moment before pushing.
  **What it looks like when real:** a refresh against `main` pushes each loop home with the
  journaled opt-out, its reason naming the branch, `origin/main` and the sha it now points at —
  seconds, not minutes, and the skip journal says exactly why; a refresh against any other
  `--base` pushes through the preflight as before.
  **Constraints:** only a fast-forward `refresh` performed itself counts as proof, and only to
  `origin/main` (the one tip whose commits all passed CI); the opt-out is the existing one, set for
  that single `git push` process and nowhere else. Kinships: steward's 2026-09-27 (later) entry
  and CAP-154/156; owner `spec-pyforge-marshal`.
- **2026-09-27 (evening) — Proposed: the landing heal sees the conflicts it was built to heal.**
  Story 28.20's heal — union a PR whose only conflict is the sprint ledger, escalate any other
  conflict by name — has never seen a conflict. `merge_tree_conflict_paths` runs the legacy
  three-arg `git merge-tree <base> <a> <b>` and looks for `Merge conflict in <path>`; that form
  prints `changed in both` and conflict markers, never that line (only `--write-tree` prints
  `CONFLICT` messages), so every real conflict reads as clean. Found while writing real-git tests
  to lift `adapters/vcs_git.py` over the coverage floor for Story 57.1; probed on git 2.43.
  Nothing landed wrongly — the local-merge fallback still refuses a conflicted merge — but the
  ledger union never fired, and a conflicted PR was never escalated with its paths.
  **What it looks like when real:** the method returns every conflicted path — content,
  modify/delete, add/add alike — from git's own conflicted-file list; a ledger-only conflict is
  unioned and the merge retried; any other conflict escalates naming its paths; a merge-tree that
  fails (an unknown ref) is an error, never an empty list.
  **Constraints:** the heal's decisions do not change, only what it sees; git's `--write-tree`
  mode, which `merge_tree_write` already requires; a conflicted merge still never lands. Kinships:
  Story 28.20 (`spec-marshal-drain-self-resolution` CAP-3, folded here); owner
  `spec-pyforge-marshal`.
  **Follow-up, same evening (Story 58.1 review):** seeing the conflict was half of it. The
  union heal, reachable at last, rewrote the ledger in a single-parent commit on the PR branch —
  which clears a same-row status conflict but not the common one, both sides adding rows next to
  each other, where the three-way merge still conflicts. It also probed the local `main`, not
  `origin/main`, and took any project's ledger for its own. **Real means:** the union is a real
  merge of `origin/main` into the dispatch branch, the landing project's ledger resolved by union
  and any other conflict aborting the merge before it is committed; the probe reads `origin/main`
  after a fetch; another project's ledger escalates by name.
- **2026-09-27 (night) — Proposed: marshal names the remote's branch, never a name something
  local can wear.** Stories 57.1 and 59.1 each found the same trap: git resolves a short name like
  `origin/main` to a local branch or tag of that name before the remote-tracking ref, so a stray
  local `origin/main` could stand in for the remote. They closed it in `refresh` and the landing
  heal. A sweep the same night found eight more places marshal hands git the short name — the
  dispatch scope diff, the landing's behind-count, merge preview and changed files, the
  supervisor's scope base, the dispatch worktree base and its landing subjects, deploy's
  push-route subjects, spec reads at a ref, and land's ledger read and loop-home fast-forward.
  **What it looks like when real:** every one of them asks git for `refs/remotes/<remote>/<branch>`,
  from one place; a local ref named like the remote changes nothing marshal reads, diffs or
  fast-forwards to; messages people read still say `origin/main`.
  **Constraints:** no behaviour changes when no shadowing ref exists; one helper, not eight
  spellings. Kinships: CAP-267 (57.1), CAP-269 (59.1); owner `spec-pyforge-marshal`.
- **2026-09-27 (late) — Proposed: marshal names its own branches too, never a name a tag can
  wear.** Story 60.1's second review found the other half of the trap: git resolves the short
  name `main` to `refs/tags/main` before `refs/heads/main`, so a tag named `main` stands in for
  the local branch. Marshal still hands git its local branches by short name — the landing
  subjects `status`, `deploy`, `retire` and `dispatch land` read, deploy's and land's merge base
  and diff base, the gate's scope diff, the start point `init` mints a loop home from, the
  supervisor's station branch, the landing heal's reads of the dispatch branch, and the
  repo-root scripts marshal owns or runs (the dashboard's landing history, the loop-home
  provisioner, the fleet picture's behind-count, the unpushed-work check, the worktree sweep).
  Most read the tag's commit with only a warning; the push and the worktree mint refuse
  outright, and a fetch of `main` beside a tag `main` on the remote updates nothing. And the
  policy's `landing_base_branch` accepts `origin/main`, which would reach every one of those
  reads. **What it looks like when real:** every git read of a local branch asks for
  `refs/heads/<branch>`, from the same `core/refs.py`; a tag named like a branch changes nothing
  marshal reads, fetches, diffs, merges or pushes; the policy refuses a landing base that is a full ref
  or a remote's branch, and a landing refuses to run on one rather than fall back to `main`.
  **Constraints:** no behaviour change when no tag shadows a branch;
  arguments git reads as a branch *name* (`branch -D`, attaching an existing branch to a
  worktree, `<branch>@{upstream}`) stay bare. Kinships: CAP-270 (60.1); owner
  `spec-pyforge-marshal`.
- **2026-09-27 (late, cont.) — Proposed: the shared test kit's branch guards diff against the
  remote.** Doctor Story 31.1's review found the same trap in `pyforge-testing-kit`, which marshal
  seeded and every station's meta tests import: `branch_diff_guard` defaults its base to the short
  name `origin/main` (`diff_text_since`, `changed_paths_since`, `existed_at_ref`, `commits_since`,
  `unsanctioned_commits`). A local branch or tag named `origin/main` at HEAD empties every "this
  branch does not add X" guard, which then passes having checked nothing
  (`DW-marshal-testing-kit-short-origin-main-2026-09-27`). **What it looks like when real:** the
  guards default to `refs/remotes/origin/main` and read an explicit `origin/<branch>` the same
  way; a stray ref changes nothing a guard sees; the skip when the base is absent still names what
  was missing. **Constraints:** no caller changes; the kit stays importable without git
  (`pytest` only inside the skip path). The kit's charter (`spec-pyforge-testing-charter`, its
  Dream archived) co-governs the surface; the capability is marshal's, the kit's seed station.
  Kinships: CAP-270 (60.1), CAP-271 (61.1), `pyforge-doctor:CAP-85`; owner `spec-pyforge-marshal`.
- **2026-09-27 (night) — Proposed: the station-tests lane picks suites from the remote-tracking
  ref.** Doctor Story 32.1's review found the coverage gate's sibling lane with the same short base:
  `.github/workflows/pyforge-station-tests.yml` — the conformance lane `spec-pyforge-core` CAP-8 made a
  PR gate — chooses which station suites run from `git diff "$BASE"...HEAD` with
  `BASE="origin/${GITHUB_BASE_REF}"`. Its checkout fetches tags (`fetch-depth: 0`), so a pushed tag
  named `origin/main` wins over `refs/remotes/origin/main`, the selection comes out empty and the PR
  runs no station suite (`DW-marshal-station-tests-short-base-ref-2026-09-27`). **What it looks like
  when real:** the lane names `refs/remotes/origin/${GITHUB_BASE_REF}`, as `coverage-gates.yml` now
  does ("same rule, deliberately"), and a test reds any workflow that diffs from a short
  `origin/${…}` base. **Constraints:** the lane still runs the pixi tasks (CAP-8); the push path's
  sha is unchanged. Owner `spec-pyforge-core` (hosted on marshal; its Dream is archived here).
  Kinships: `spec-coverage-gate-independence` CAP-4, `spec-pyforge-mason` CAP-28 (the recipe
  workflows the same test covers).
- **2026-09-27 (late night) — Proposed: a drain can be asked what it would dispatch before it
  launches anything.** Reading steward's drain queue by hand today found a story parked only in
  prose. Steward 44.4–44.6 carry "Parked 2026-09-13 … do not dispatch" in `epics.md`, their ledger
  rows stay `backlog`, and nothing in code reads that line. 44.4's Deps (44.3, 44.12) are `done`
  and its spec has no `## Verification`, so a steward drain would have dispatched it first.
  `MRS-GATE-010` would have refused it only after a whole session, and the drain classes that gate
  transient (`core/dispatch_retry.py`), so it would have re-dispatched it every cycle. It was
  parked in code the same day with a `skip_policies` entry in `fleet-drain-queue.yaml` (a separate
  PR); the declared skip stays the one park mechanism. The same read found two more things nobody
  can see without launching. A non-empty `order_overrides` list switches the Story 28.12 Deps sort
  off even when every key in it is done (`dispatch_fleet.station_backlog`). And in serial mode (the
  default, `max_parallel = 1`) Deps only order the queue and never gate it; only the parallel
  wave gates, through `spec_deps.ready_backlog`. There is no dry run: `dispatch_once`'s first write
  is `git worktree add`, and neither `dispatch` nor `drain` has a plan or check flag. Marshal
  registers 49 `MRS-DISP`, 15 `MRS-GATE` and 17 `MRS-DRAIN` codes. Many of the refusals among them
  can be decided before anything launches but fire only after a session: `MRS-GATE-010`/`011`
  against the primary checkout's tracked spec, which the session cannot change; `MRS-GATE-003`
  against a verify command's shape; `MRS-DISP-019` against the rendered merge subject.
  **What it looks like when real:** `marshal factory drain --plan` computes each station's queue
  the way a drain cycle does, through the same functions but with no worktree, session, journal or
  lock. For the next story (and for every queued story, on request) it names each refusal it can
  decide without launching. It also names prose parks that no `skip_policies` entry mirrors, and
  override lists that change nothing but the sort. It exits non-zero when any station's next story
  would be refused. Separately, `dispatch_once` refuses a story whose tracked spec cannot bind
  before it provisions anything, so a story that can never pass the gate never costs a session and
  never enters the transient re-dispatch loop.
  **The pieces already exist, read-only:** `_dispatch_scope_refusal`,
  `dispatch_core.resolve_story_spec_path` and `resolve_dispatch_branch`, `_compose_policy`,
  `_read_fleet_queue_config`, `_station_ledger_statuses`, `dispatch_fleet.station_backlog`,
  `plan_station_queue` and `build_wave_batch`, `_station_blocked_map`,
  `station_finalize_pending_story`, `parse_spec_status` with `blocks_harness_relaunch`,
  `spec_binding.parse_success_signal` with `gate.check_spec_binding` (against the guard-appended
  verify commands, `dispatch_verify.py`), `promotion.corroborated_merged_story_keys`,
  `merge_subject_is_marshal_native` and `dispatch_verify._bare_shell_metacharacters`. The plan
  composes them and adds no second evaluator.
  **Constraints:** the plan never writes. Environment probes (harness binary, authcheck) run only
  behind an explicit flag. The plan reports a prose park but never honours one, so the declared
  skip stays the one park mechanism. Kinships: Story 22.7 (the drain), Story 28.12 (the Deps sort),
  Story 28.18 (re-preflight), the 2026-09-25 scope seed (CAP-273); owner `spec-pyforge-marshal`.
  → CAP-274 / Epic 65 / Stories 65.1, 65.2
- **2026-09-28 — Proposed: `marshal seed check` judges the paths the manifest means.** On this
  repository `marshal seed check --json` exits 1 with `failing: true`, and five of its HARD findings
  are the manifest's own placeholders read as literal paths: `docs/dreams/{{ slug }}.md`,
  `_bmad-output/projects/{{ slug }}/.bmad-config.toml`, its `specs/README.md`,
  `presentations/{{ slug }}/` and `_bmad-output/projects/{{ slug }}/` — "declared by the manifest but
  absent from the repo".
  A sixth is `.claude/skills/**`, an `unclassified-deferred` glob, also read literally. Every one of
  the eight projects here carries all five rendered paths. The manifest's paths are templated on the
  project slug (AD-55), and only `seed init` renders them; `check` never does. Story 10.7 named the gap
  and left it for a later story. Steward's session check reads this JSON, so a green repository reads
  red. **Does checking A apply at all?** Yes: the model was extracted from this repository and Story
  12.2's oracle holds it to the model (SC-02). Exempting the seed's home would hide exactly the drift
  that oracle exists to catch. What changes is that the check reads real paths.
  **What it looks like when real:** `check` renders `{{ slug }}` with the project the command already
  resolves for its `[context]` read (`--project`, then `BMAD_ACTIVE_PROJECT`, then the target's
  active-project marker), through the one renderer `seed init` uses. With no project to resolve, a
  templated entry is one INFO finding naming `--project`, never a HARD finding against a literal
  placeholder. An `unclassified-deferred` entry has no class contract and nothing `adopt` could
  materialize, so it is never reported missing. What stays on this repository after the fix is true:
  it was never adopted (`model-behind`), and its primary checkout has no `.bmad-loop/policy.toml`
  because the harness policy is rendered per loop home. That second fact is Story 12.2's K-02, not
  this fix.
  **Constraints:** no new state key (the state schema has no `slug`, by decision); no exemption by
  repository name; `init`'s behaviour is unchanged. Kinships: Story 10.7 (the gap named), Story 12.2
  (the oracle, K-02), steward session check's parse of this JSON (a separate steward CAP); owner
  `spec-pyforge-marshal`.
  **Amended 2026-09-28 (operator ruling):** the second fact above is not a gap. `.bmad-loop/policy.toml`
  is owed only in the loop homes `marshal init` provisions, never on a primary checkout, and this
  repository is the seed's home, not a loop home. The manifest entry carries that scope
  (`required_in: loop-home`), so the check on this repository can pass honestly while a loop home
  without the file still fails. The scope is the entry's, not an exemption by name. → CAP-279 amended,
  Story 70.1 (AD-55 amended in place).
- **2026-09-28 — Proposed: the front door names the environment a roster station runs in.**
  `pixi run -e pyforge-guild pyforge warden --help` answers `unknown station 'warden'; known:
  doctor, herald, marshal, scribe, steward` (exit 2), and `pyforge atlas` and `pyforge mason` answer
  the same. All three are Guild stations on the one roster (`pyforge.core.roster.STATIONS`); they are
  simply not installed in the Guild environment. Warden is left out on purpose (its `osv-scanner`
  range pin conflicts with the factory's), atlas is absent, and mason arrives with steward Story
  72.1. `pyforge.core.dispatch` builds its station map from the installed distributions and calls
  anything missing "unknown", so the operator is told a real station does not exist.
  **What it looks like when real:** a name on the roster that is not installed here reads as exactly
  that — "station 'warden' is not installed in this environment; it runs in `-e pyforge-warden`" —
  with the command to run it. A name on no roster still reads "unknown station", listing what is
  installed. `pyforge --help` names the roster stations this environment lacks and where each runs.
  **Constraints:** `pyforge-core` stays a stdlib leaf and reads no `pixi.toml`: the environment name
  is the roster's long form (`pyforge-<station>`, the form Ruling 18 fixes for packages and pixi
  environments); the exit code is unchanged; no station is installed or removed here. Owner
  `spec-pyforge-core` (hosted on marshal; its Dream is archived here). Kinships:
  `spec-pyforge-steward:CAP-161` (Story 72.1, mason in the Guild environment), steward's
  examination of atlas in the Guild environment (a separate steward chain).
- **2026-09-28 — Proposed: the dispatch supervisor judges a merge from `origin/main`.** CAP-276
  (Story 67.1) makes the supervisor trust the landing it journaled itself, because its repository
  facts read local `main`, which only moves when finalize can fast-forward the primary checkout. That
  is a workaround for the reads, not a fix of them. `gather_dispatch_git_facts` asks
  `is_branch_merged(…, into="main")` and reads the merge subjects from `refs/heads/main`, while the
  same function already diffs from `origin/main` and reads each candidate spec's status at
  `origin/main` — one fact from two refs. Three decisions consume those facts: whether to land
  (`VERIFIED` and not merged), whether a stuck land is retried (`should_retry_stuck_land`), and
  whether the supervisor may exit (`supervisor_should_exit`). With local `main` behind, a story
  merged by another route reads unmerged: the supervisor tries to land it again and counts it stuck.
  **What it looks like when real:** every merge fact the supervisor judges comes from
  `refs/remotes/origin/main`, the ref a landing writes and the supervisor already fetches every
  fifth tick; after its own land it fetches before re-reading. Local `main` can lag as long as it
  likes. **Constraints:** the landing journal still decides first (CAP-276); an unreadable
  `origin/main` is a failed gather, as today, never a merged story; the port's branch-name form stays
  for its other callers. Kinships: CAP-276 (Story 67.1), CAP-270 (Story 60.1, the full ref);
  owner `spec-pyforge-marshal`.
  **Widened 2026-09-28 (operator ruling):** `dispatch land` judged the same fact from local `main` —
  its ALREADY_LANDED check (`dispatch_land.py:687`) read merge subjects from `refs/heads/main` while
  its landing merges through the forge. It moves to `origin/main` in the same story, so every merge
  fact the dispatch path judges comes from one ref. → CAP-280 widened, Story 72.1.
- **2026-09-28 — Proposed: a drain runs the follow-up review a landed story recommended.**
  CAP-275 (Story 66.1) carries `followup_review_recommended: true` into the station's deferred-work
  ledger as an open `DW-FRR-<story>` row, and then nothing runs the review. A drain never
  dispatches a `done` key (`station_backlog` drops it; `--stories` refuses it), although
  `bmad-build-auto` already knows what to do with one: its step 01 routes a `done` spec whose flag is
  `true` to a fresh review, writing the flag `false` first. Two things stand in the way beyond the
  queue. The dispatch supervisor judges a run complete as soon as the story's merge subject is on
  `main` (`judge_dispatch_completion`), and the original landing already put it there, so a review
  run reads finished before it starts. And `dispatch land` answers ALREADY_LANDED for the same
  reason, so the review's own branch would never merge.
  **What it looks like when real:** a run on a `done` spec with the flag `true` is a follow-up review
  run, marked so in its journal with the row it answers. It is judged and landed by its own branch —
  merges after its own baseline, its own head on `origin/main` — never by the story's first landing,
  and a review whose only change is its own spec's record still counts. When it lands, finalize
  closes the row. A drain queues each open row after the station's implementable backlog, and
  `drain --plan` lists them.
  **Constraints (the respawn trap):** the row's state gates a follow-up, never the ledger key — the
  key stays `done` throughout, is never flipped and never re-enters the backlog; a closed or absent
  row is never dispatched; an open row whose spec no longer reads `done` with the flag `true` is
  reported stale, not dispatched; a follow-up's own review never chains a second one (step 04 leaves
  the flag `false`). Kinships: CAP-275 (Stories 66.1, 66.2), CAP-274 (Story 65.1, `drain --plan`),
  CAP-280 (Story 72.1, the supervisor's merge reads); owner `spec-pyforge-marshal`.
  **Amended 2026-09-28 (operator ruling):** a campaign runs a few, not all. Story 66.2's backfill opens
  181 rows at once, so a drain campaign queues at most `dispatch.max_followup_reviews_per_campaign`
  follow-ups (default 2), newest landings first; the rest wait for later campaigns. → CAP-281 amended,
  Story 73.2.
- **2026-09-29 — Proposed: every dispatch session opens on the shared codegraph index.** Operator
  direction, 2026-09-29: caveman, headroom and codegraph must be installed, working and in use before
  the next fleet drain, so the drain earns the token-economy savings.
  Measured on the first dispatches of that evening:
  - **Two layers work.**
    - `wire` (`headroom wrap claude`, a proxy on a per-worktree port) was applied. One stopped
      session had saved 15.7% of its tokens (443,514 of 2,829,915) in five minutes.
    - `output` (the caveman skill) was deployed into every dispatch worktree.
  - **The third does not.** `structure-graph` is enabled for every station by policy (Epic 55), but
    nothing on the dispatch path gives a worktree a codegraph index. The binary is not in the
    `pyforge-guild` environment that dispatch runs in (only `local-recipes` has it), the primary
    checkout has no `.codegraph/`, and `bmad-build-auto`'s step 01 only uses an index that already
    exists in its worktree (Story 28.33).
  - **Story 28.31's spike already chose the shape**
    (`benchmarks/structure-graph-dispatch-28-31.json`): share one repo-level index. A fresh
    `codegraph init -y` cost about 19 s and 222 MiB per worktree, `codegraph sync -q` from a shared
    base about 4 s, against about 52k tokens of unaided navigation.
    - Its follow-on draft (`spec-28-34-…`) was never minted and is archived, tracked as
      `DW-FU-28-31-1`. That row's own trigger ("only if the token-economy layers are switched on") has
      now fired.

  **What it looks like when real:**
  - `codegraph` is on PATH in the Guild environment, from conda-forge, beside `headroom-ai` and
    `caveman-installer`.
  - With the layer enabled, `dispatch_once` gives each new worktree a codegraph index:
    - it copies the primary checkout's `.codegraph/` and runs `codegraph sync -q`;
    - when no base exists, it runs `codegraph init -y` in the worktree and names
      `marshal context bootstrap` as the fix;
    - when the binary is absent, the session runs without an index and says so.
  - The dispatch journal records which of the three happened.
  - The primary checkout's base index is built by `marshal context bootstrap`.

  **Constraints:**
  - An unavailable instrument never blocks a dispatch: each layer's graceful-degrade contract holds.
  - The primary checkout is only read, never written. Story 64.1 keeps dispatch off the shared
    checkout's files.
  - `.codegraph/` stays gitignored, so no index is ever committed.
  - No second index format and no harness change: step 01 already reads the index.

  Kinships: Story 28.31 (the spike), Story 28.33 (step 01's reference), Epic 55 (the layer switched
  on), CAP-192 (`marshal context bootstrap`'s substrate), Story 46.9 (per-layer benchmark legs);
  owner `spec-pyforge-marshal`. → CAP-282 / Epic 77 / Story 77.1 (FR-229), specced 2026-09-29.
- **2026-09-30 — Proposed: a landing unions append-only memlogs instead of refusing.** Found landing
  wave 1, 2026-09-30:
  - **Four landings refused on one conflict (MRS-DISP-038).** Steward 74.1 (#1679), doctor 35.1 (#1682), steward
    76.1 (#1683) and doctor 36.2 (#1692, twice). Every conflicted path was a `.memlog.md`. The story and `main` had
    both appended entries, and rewritten `updated:`, in the same Spec memlogs: the owning Spec's, and the
    co-governors' (`spec-pyforge-core`, `spec-pyforge-unifying-strategy`) that every station's surface reconcile
    writes.
  - **The heal resolves one path.** CAP-4 (Story 28.20) and CAP-269 (Story 59.1) heal only the landing project's own
    sprint ledger; every other conflicted path escalates by name. So when two stories run at once and both
    reconcile a shared co-governor, the second to land is refused, however clean its code.
  - **Each refusal cost an operator hand-landing.** Merge `origin/main` in the dispatch worktree, union the memlogs,
    commit, push, wait for CI, merge with the landing subject, replay `dispatch_land_finalize`, set the Tier-3 feed
    row. Meanwhile the campaign parks the story (MRS-DISP-040) or re-dispatches it into the same conflict: doctor
    36.2 ran a second full session, then a land-only retry that held the campaign lock through the station suite.

  **What it looks like when real:**
  - The heal treats a conflicted `.memlog.md` as mechanical when both sides only appended to it since the merge
    base. The resolved text is `main`'s, followed by the story's new entries in their order, and `updated:` takes
    the later stamp.
  - It rides the real merge of `origin/main` the ledger heal already makes, so ledger and memlogs heal in one
    commit.
  - A memlog either side edited or truncated, or a frontmatter field other than `updated:` that both sides changed
    differently, escalates by name as today. The landing journal names every healed path.

  **Constraints:**
  - Only append-only memlogs join the mechanical set: not the spec-surface baseline, not another project's ledger.
  - Never a lossy resolution: every entry from both sides survives, none twice.
  - One unresolvable path aborts the merge before any commit or push.
  - No new port method: `merge_ref_resolving` already takes a map of resolutions.

  Kinships: CAP-4 (Story 28.20), CAP-269 (Story 59.1), `_bmad/scripts/memlog.py` (the append-only format), the
  S-13.7 surface-reconcile guard (why every story writes memlogs); owner `spec-pyforge-marshal`. → CAP-283 /
  Epic 78 / Story 78.1 (FR-230), specced 2026-09-30.
- **2026-10-01** — **Found: two landing gaps that keep growing the ledgers.** The 2026-09-30 deferral burn-down
  traced recurring hand work after dispatch landings to two gaps:
  - **Finalize promotes the ledger twin but not the Tier-3 feed row, nor a spec the session tracked itself.** Every
    automatic landing on 2026-09-30 (doctor 34.5, steward 76.2, scribe 25.1, marshal 74.2 and 78.1) left the story's
    feed row at `backlog`, so the next plain `sprint-ledger-sync` refused ("feed would un-finish") until a hand
    alignment (DW-OPS-2026-10-01-1). A session that commits its tracked spec and leaves no Tier-3 twin gets no spec
    promotion: scribe 25.1 landed with its spec at `backlog` (DW-FU-53-2-4).
  - **Dispatch verification never runs `lint-types`.** `dispatch/*` branches skip `pr-preflight` because the supervisor
    gates them, but the supervisor verifies only the station suite and the surface guard. Scribe 25.1 landed a format
    `ruff format` rewrites, and `lint-types` stayed red on `main` until #1690 (DW-OPS-2026-10-01-2).
  **What it looks like when fixed:** a landing leaves the feed row and the tracked spec `done` beside the twin; a
  dispatch whose change fails `lint-types` is refused before it merges.
  **Constraints:** no new CAP (defects of the landing promotion, CAP-229 and CAP-277, and of the derived verification
  guard, CAP-261 (a)); `lint-types` joins verification in one place, as the surface guard did (Story 53.1), never by
  editing eight `verify_commands` lists; the feed write is atomic and never moves a `done` or `blocked` row. The `"22"`
  and `"28"` `epic_surfaces` entries stay: their station-wide globs are what every later epic declares, and Epic 73's
  follow-up reviews of done 22.x/28.x stories need them; only their stale "stopgap" comments go (DW-FU-28-14-4,
  DW-OPS-2026-10-01-3). Owner `spec-pyforge-marshal`. → Epic 79 / Stories 79.1–79.2, specced 2026-10-01.
- **2026-10-02** — **Phase 2 of the deferral burn-down: marshal's critical and high deferrals.**
  The 2026-09-30 triage re-verified every open marshal deferral against `main`; 39 still stand (one critical, 36 high,
  and two medium that share the parallel-wave code), grouped into 13 bundles by the code they share: the gate's
  repository anchor, run liveness at landing, landing and ledger integrity, the supervisor's journal, budget and idle
  signals, retry escalation, spin guards, status and teardown, egress and gate evidence, parallel-wave journaling, and
  seed apply safety in three parts. Operator ruling 2026-10-02: start Phase 2 after the inflow wave, marshal first,
  most severe first, on two dispatch lanes.
  **Constraints:** each bundle is one `fix` story under the CAP that shipped the behaviour, so no new CAP and no flag;
  each story closes its DW rows in `deferred-work-ledger.md` when it lands.
  Owner `spec-pyforge-marshal`. → Epic 82 / Stories 82.1–82.13, specced 2026-10-02.
- **2026-10-02 (later)** — **Ruling: Story 82.7 ships its second half only.** Its dispatch blocked on an intent gap:
  the guard its first half asked for (refuse a second `factory spin` while the project's run is live) already ships,
  as Story 34.1's `spin_loop_home_in_flight_conflict` (MRS-DISP-021, from Story 28.24's 2026-09-10 fix). The deferral
  that asked for it (DW-FU-3-3-2) was last re-verified by a grep that missed the guard. Operator ruling: keep that
  guard, add no second gate and no second liveness model, and narrow 82.7 to the launch poll that never asks whether
  its child is alive (DW-FU-3-3-4). DW-FU-3-3-2 closes as resolved by Stories 28.24 and 34.1.
  Owner `spec-pyforge-marshal`. → Story 82.7 re-specced 2026-10-02.
- **2026-10-02 (night)** — **Found: seven dispatch and campaign defects while landing Phase 2.** Landing Epic 82
  and the steward and doctor lanes surfaced seven defects in marshal's own landing and campaign path, each worked around
  by hand the same day:
  - **A dead dispatch run reads as live when its pid is reused.** `PosixProcess.is_alive` is `kill(pid, 0)`, which
    succeeds for any process or thread that now holds the number. Two 2026-08-31 runs of done Story 28.4 had no
    completion entry; after pid allocation wrapped, their session pids were Firefox thread ids, and the campaign held
    its next wave on "28.4" until the two run directories were moved aside.
  - **A station's dispatch verification never runs the checks that read the whole tree.** Steward 83.2 closed two
    deferred-work rows with uncited `verified:` lines and turned doctor's ledger-citation test red on `main`;
    marshal 82.4 added an exception root that pyforge-core's CAP-5 meta-test rejects. CI caught both; dispatch
    verification caught neither.
  - **The landing heal unions memlogs but not appended deferred-work rows.** 82.9 and 82.10, run as one parallel
    wave, each appended rows at the tail of the station's `deferred-work-ledger.md`, and the heal refused 82.9
    (MRS-DISP-038) on that file alone.
  - **A strictly serial campaign starts the next story while the last one is refused and unlanded.** 82.5 launched
    while 82.4's PR sat refused on a red check; both edited the supervisor, minted the same finding codes, and
    conflicted.
  - **A campaign supervisor stops on fleet-lock contention.** The MRS-DRAIN-010 refusal carries no `data.complete`,
    so the supervisor counts it as an unreadable cycle and stops after five in a row, although the refusal's own
    comment says the supervisor simply ticks again.
  - **Every dispatch warns about a stale codegraph index after the primary checkout pulls `main`.** The session check
    (Story 63.4) reports `codegraph-index: stale` and dispatch only warns (MRS-DISP-049); `marshal seed kit --apply`
    was run by hand after each landing.
  - **A re-dispatch after a refused landing starts a whole new session.** Land-only is chosen only when
    the worktree spec reads `done`; a landing refused on a conflict or a red check leaves the spec where
    the session stopped. After 82.5's branch was fixed by hand, its re-dispatch launched a full dev and
    review session on finished work, stopped within seconds, and the PR was merged by hand.
  **What it looks like when fixed:** a run is live only while its pid is still the session it launched; every
  station's landing runs the checks that read the whole tree; the heal resolves appended deferred-work rows the way it
  resolves memlog entries; a serial campaign holds a story whose overlapping predecessor is unlanded; lock contention
  is an ordinary not-complete cycle; dispatch refreshes a stale codegraph index before it launches; and a
  re-dispatch after a refused landing lands the fixed branch without a new session.
  **Constraints:** each is a `fix` story under the capability that shipped the behaviour, so no CAP and no flag; a new
  epic because those epics are `done`. Story 83.3 widens CAP-283's mechanical set from memlogs to pure appends of whole
  rows in the station's own deferred-work ledger, and nothing more. Owner `spec-pyforge-marshal`. → Epic 83 /
  Stories 83.1–83.7, specced 2026-10-02.
- **2026-10-04 (seed skips and directories)** — **Found: seed check ignores recorded skips, and no verb can record a
  directory.** Story 70.1's build and review (#1831) found that `seed check` never reads `state.skips`, so an absent
  artifact the operator chose to skip is still HARD `artifact-missing`, whose remedy runs the very `adopt` that skips
  it. A directory entry that a commit creates makes the post-apply record read it as a file (`IsADirectoryError`), so
  `seed init` against the full packaged manifest cannot write state, and the commit dispatchers cannot create an
  absent directory at all (`DW-marshal-86-1`). The review also asked that a bad slug from the environment or the
  marker not fail the check, that a test helper render through `render_slug_paths`, and that the loop-home read be
  pinned for a symlinked target and a near-miss branch name. **What it looks like when fixed:** check honours every
  recorded skip; `adopt`, `init` and `update` create and record directory entries, and roll back a directory they
  created; only an explicit `--project` can fail the check on its slug. **Constraints:** a fix story under CAP-279, no
  new CAP or flag. It goes into Epic 70 and reopens it (operator ruling 2026-10-04: a fix joins its own epic and
  reopens it, never a new epic; doctor Story 41.5 lets `ledger-regression` accept the reopen). Owner
  `spec-pyforge-marshal`. → Story 70.2, specced 2026-10-04.
- **2026-10-04 (fix-turn reconcile)** — **Found: a fix turn's own edits fail re-verification on spec-surface drift.**
  Atlas 27.3's fix turn added a coverage test after the session had reconciled its memlog. Re-verification then
  refused on the surface guard, the run failed, and the story was reconciled and landed by hand (`f4c3bfb289`).
  Marshal 86.8's fix turn changed a test file the same way. The supervisor commits a fix turn's edits and re-verifies
  with nothing in between; the only memlog reconcile is `dispatch land`'s, which runs after verification.
  **What it looks like when fixed:** the supervisor runs that same reconcile over the paths the fix turn changed, and
  commits it, before it re-verifies; drift on any other path still refuses. **Constraints:** a fix story under
  CAP-286, no new CAP or flag. It goes into Epic 85 and reopens it (operator ruling 2026-10-04). Owner
  `spec-pyforge-marshal`. → Story 85.5, specced 2026-10-04.
- **2026-10-04 (cross-station meta-tests)** — **Found: a station story can break another station's contract and still
  land.** Atlas 27.3 landed `dashboard/scan_submit.py` shelling `-e local-recipes`, and main went red on steward's
  `tests/meta/test_no_station_assumes_local_recipes.py`, which reads every station's `src/` (hotfix #1840). Atlas's
  dispatch verification runs atlas's suite and the derived whole-tree checks, never steward's tests, and the PR's CI
  did not start `steward-test`. Doctor's two `*_stays_outside_every_station.py` contracts read every station's tree
  the same way. **What it looks like when fixed:** a story that touches any station's `src/` runs every meta-test
  outside pyforge-core that reads every station's `src/`, in its owning station's environment, before it can land.
  **Constraints:** a fix story under Epic 83, no CAP, no flag; derived beside the coverage gates, never written into a
  station's `verify_commands`. Owner `spec-pyforge-marshal`. → Story 83.23, specced 2026-10-04.
- **2026-10-04 (landing guard source)** — **Found: the landing's ledger guard judges a copy it does not overwrite.**
  Story 83.21's landing review (#1828) found that the feed-sync guard builds the ledger it protects from the primary
  checkout's local copy, while the landing publishes over `origin/main`'s. A stale primary therefore let the
  2026-10-03 epic drops through, and no test pins which copy the guard reads. The review also found that the epic
  roll-up parses with land's own parser, which stops at a column-0 comment; that the line rewrite matches a key
  anywhere in the file; that `deploy reconcile-completions` advances stories without the roll-up; and that the
  missing-module WARN fires only when there is something to publish. **What it looks like when fixed:** the guard
  judges the text it overwrites, every ledger writer reads with the sync's parser and applies the sync's roll-up, and
  a missing roll-up is always named. **Constraints:** a fix story under Epic 83, no CAP, no flag. Owner
  `spec-pyforge-marshal`. → Story 83.22, specced 2026-10-04.
- **2026-10-04 (preserved-work refs)** — **Found: preserved work has nine names and no definition, and much of it is
  not durable.** The repo keeps "preserved" work under `attempt-preserve/*`, `refs/attempt-preserve-dirty/*`, 698
  `rescue/*` tags, 45 `archive/*` tags, `bmad-loop-preserve/*`, `backup/*`, `recover/*`, gitignored
  `failed/<story>/changes.patch` files, steward tarballs and the sweeper's patch directories. Every protection is a name
  list, but survival depends on reachability. Measured: 16 of 17 dirty snapshot refs and 3 local tags hold commits on no
  `origin` ref; of the 454 tips deleted on 2026-10-04, 98 are reachable from nothing, and 83 of those 98 were under no
  protected name. bmad-loop prunes `attempt-preserve/*` at every run start while this repo parks durable work there,
  tags are unprotected server-side, and `marshal land` and Story 87.1's `--retire` delete refs the new ruleset
  protects. 23 public `rescue/dangling-*` tags, minted by the unpushed-work detector's printed remedy, re-preserved the
  history the 2026-07-24 purge removed; they were deleted from `origin` the same day, and the same remedy would now print
  about 16,000 more for marshal's own synthetic merged-check commits. An independent architecture review adopted the
  standard with changes, and the operator accepted every default it recommended the same day.
  **What it looks like when fixed:** one rule in every mode (spin, dispatch on every harness, drain, bare bmad-loop,
  bmad-build, bmad-build-auto, hand `land/*` rebuilds, steward workspaces, agent worktrees). Work outlives its working
  copy only as a commit reachable from an annotated `refs/tags/preserve/<slug>/<N.M>/<producer>-<sha8>` tag, with no
  date in the name. A local tag is enough to remove a working copy, which makes it AD-29's declared durable local ref; an
  unpushed preserve is reported as debt, never a refusal; deleting a ref on `origin` needs the tag on `origin`. Nothing
  reaches `origin` without passing a content gate (purge list, secret scan, size cap). Retirement writes an
  `archive/heads/<branch>` twin only when deletion would orphan commits, and a preserve retires by derived state. One
  declared list, unioned with a code floor, drives the rulesets, the hook and every in-code deleter, and a reachability
  guard covers every branch and tag the list does not name. **Constraints:** upstream names stay; marshal promotes them
  and renders `preserve_keep = 0`. Legacy `rescue/*` and `archive/*` tags are frozen. Nothing is deleted without an
  operator ruling, and every outward GitHub settings change is the operator's. The grammar lives in
  `pyforge.core.preserve_refs`. Owner `spec-pyforge-marshal` (co-governors `spec-pyforge-steward`,
  `spec-pyforge-core`). → CAP-287, FR-234, AD-81, Stories 87.2–87.16 (87.1 amended), specced 2026-10-04; steward twin
  `spec-pyforge-steward:CAP-165`, Stories 85.2–85.5 (85.1 amended). Research
  `_bmad-output/projects/pyforge-marshal/planning-artifacts/research/preserved-work-refs-2026-10-04.md`, its drafts and
  its review (`preserved-work-refs-2026-10-04-review.md`, same folder).
- **2026-10-04 (finalize roll-up)** — **Found: landings overwrite epic roll-ups with stale feed rows.** The landing
  finalize renders the feed into the tracked ledger without the sync's epic roll-up. The feed's epic rows lag, because
  the sync writes roll-ups only to the twin, so a landing copies the stale value. Doctor 41.5's landing set `epic-41`
  to `backlog` with two stories done. On 2026-10-03 three landings dropped done epics to `backlog`, which turned main red.
  **What it looks like when fixed:** every ledger write applies the same roll-up, so a landing never moves an epic the
  stories do not move. **Constraints:** a fix story, no CAP, no flag. Owner `spec-pyforge-marshal`. → Story 83.21,
  specced 2026-10-04.
- **2026-10-04 (late night)** — **Found: the fix turn's redaction can hang the supervisor.** Story 85.3's post-landing
  review showed the new secret rule backtracks exponentially on an unclosed quoted value full of backslashes
  (`password="` plus 32 backslashes takes 0.5 s, and 1,000 take more than 20 s). The scrub runs in the supervisor thread
  on every failed command's full output, and the fix turn is ON in dev and staging. The review also found these:
  - the URL rule is quadratic;
  - a compiler location loses its line and column;
  - five credential shapes leak;
  - the fix wait's journal heartbeat writes every second;
  - three wirings have no test;
  - one test races.
  **What it looks like when fixed:** every scrub is linear and keeps what a fix needs, the heartbeat runs at the tick
  rate, and the tests are deterministic. **Constraints:** a fix story under CAP-286, no new CAP or flag. It goes into
  Epic 85 and reopens it (operator ruling, 2026-10-04: a fix joins its own epic and reopens it, never a new epic; doctor Story 41.5 lets `ledger-regression` accept the reopen). Owner
  `spec-pyforge-marshal`. → Story 85.4, specced 2026-10-04.
- **2026-10-04 (night)** — **Found: 86.5's cite rule hides real missing cites.** Story 86.5's post-landing review
  showed its new code-linkage cite rule drops path-form cites with non-numeric ids, so 26 stale atlas
  `specs/spec-a1-…md` links (to specs renamed in 893c96110d0) and a steward cite of a folded Spec folder now
  read as prose instead of missing. A dead mypy override and stale `marshal chain regenerate` docs remain too.
  **What it looks like when fixed:** a path-form cite that resolves nowhere is counted missing and named; the
  stale links are repaired; no live doc describes the retired verb. **Constraints:** a fix story, no CAP, no flag.
  Owner `spec-pyforge-marshal`. → Story 86.8, specced 2026-10-04.
- **2026-10-04 (83.19 review)** — **Found: a rename slips out of the CFE surface, and the CFE list has five copies.**
  Story 83.19's independent review (#1860) showed a `git mv` out of `.claude/skills/conda-forge-expert/` committed in a
  `wip:` auto-checkpoint, because dispatch judges only a rename's new path; verification then refuses, and the branch
  needs a history rewrite. The four station guards still hardcode the CFE path instead of reading the kit's list, the
  retro subject names Story 83.19 for every story, MRS-GATE-020 is retried even when no retry can clear it, and the
  push precedes the refusal. **What it looks like when fixed:** both sides of a rename stay out of every non-retro
  commit, every guard reads `pyforge.testing_kit.cfe_surface`, the retro subject names its own story and CFE version,
  and an unsanctioned commit on the branch is terminal and refused before the push. **Constraints:** a fix story, no
  CAP, no flag. Owner `spec-pyforge-marshal`. → Story 83.24, specced 2026-10-04.
- **2026-10-04 (Cursor attribution)** — **Found: Cursor sessions sign their commits.** Mason 27.2's dispatch committed
  `Co-authored-by: Cursor <cursoragent@cursor.com>`, from the operator's `cli-config.json`
  (`attribution.attributeCommitsToAgent`, default `true`). Story 83.17's check refused it only at verification, after
  the build, and the branch needed a message-only rewrite and a force push to land (#1864). A repo `.cursor/cli.json`
  cannot carry the setting (its schema admits only `permissions`). **What it looks like when fixed:** every Cursor
  launch marshal makes reads a run-scoped config (`CURSOR_CONFIG_DIR`) with attribution off, the operator's file
  untouched. **Constraints:** a fix story, no CAP, no flag. Owner `spec-pyforge-marshal`. → Story 83.25, specced 2026-10-04.
- **2026-10-04 (testing kit CI)** — **Found: the testing kit's own suite runs nowhere.** `pyforge-testing-kit` is the
  seam every station's meta tests import, but no workflow runs `pyforge-testing-kit-test`, and the local
  `pyforge-station-tests` twin skips it too. The kit is only a trigger for the station jobs. Its suite is already red:
  steward Story 76.2 added flagd `metadata` to the platform flag tree, and the kit's shape check has failed since,
  unseen. **What it looks like when fixed:** a `testing-kit-test` job runs the kit's pixi task whenever the kit, the
  shared surface or an input its suite reads changes; the local twin runs it; the suite is green. **Constraints:** a
  fix story under `spec-pyforge-testing-charter` CAP-3, no new CAP, no flag. It goes into Epic 19 and reopens it.
  → Story 19.5, specced 2026-10-04.
- **2026-10-04 (later)** — **Found: the sweeper stops at local branches, so remote cleanup is hand-rolled.** A
  hand-rolled cleanup deleted the eight loop homes, the `loop/*` branches and 41 `attempt-preserve/*` branches, all of
  which `scripts/worktree_sweep.py` would have kept. All were restored from GitHub's activity log, except the loop homes'
  gitignored run history. **What it looks like when fixed:** the sweeper gives remote branches the same verdicts
  (KEEP / DELETE / INSPECT), writes a manifest before any delete, and retires a protected branch only by explicit
  name. **Constraints:** a fix story, no CAP, no flag. Owner `spec-pyforge-marshal`. → Story 87.1, specced 2026-10-04;
  steward twin Story 85.1 (the session hook).
- **2026-10-04** — **Found: a landing promotes stale pre-rekey spec copies.** Atlas 27.1's landing finalize
  committed three Tier-3 spec copies left over from atlas's 2026-09-17 rekey (13-5, 14-4, 15-3). Their stories had
  already landed and been promoted under the new keys (12-5, 13-4, 14-3). Promotion matches a candidate by its story
  number, so the stale copies read as durable and unpromoted, and every later finalize would promote them again.
  **What it looks like when fixed:** promotion skips a Tier-3 spec whose key has no ledger row, or whose story already
  has a tracked spec under another key, and reports it as an orphan. **Constraints:** a fix story, no CAP, no flag.
  Owner `spec-pyforge-marshal`. → Story 83.20, specced 2026-10-04.
- **2026-10-06 (landing gaps)** — **Found: four gaps the 2026-10-05 one-per-station dispatch left for a human.**
  Seven dispatches ran; five landed and two were refused, and every landing still needed hand bookkeeping after it.
  (1) Three automatic landings (doctor 34.3, herald 27.1, mason 19.1) flipped the ledger and the story spec but left
  the story's `**Status:**` line in `epics.md` at `backlog`; doctor's own meta-test then failed CI `doctor-test` on
  every branch. (2) Warden 14.1's single fix turn ran the warden package's whole test tree, slow corpus tests
  included, instead of the failing command, and timed out at 900 s (MRS-DISP-059); atlas 25.2's fix turn cleared one
  gate and the next refused (MRS-DISP-060). Both stories added a feature flag, and neither session knew the four places
  a flag must be registered (`flags.json`, `flag-overlays.json` per the spec's `flag.default`, core `test_flags.py`,
  platform `test_openfeature_file_flags.py`). (3) The cross-surface gate is one hardcoded rule (`src/platform/` runs
  `platform-ci-local`), so mason 19.1 landed a new station skill without `bmad-estate-check` and left it red on `main`,
  and nothing ran `flag-gate-check` on a flag story. (4) Marshal 46.10 and 70.2 landed by dispatch with
  `spec-pyforge-core` paths their journals never reconciled, so core's scoped stamp refused until a hand PR named
  them. **What it looks like when fixed:** a landing leaves `epics.md` matching the ledger; a fix turn re-runs only
  the failing commands and has the flag checklist; the cross-surface gate runs each touched surface's own check; a
  landing leaves every Spec it touched stampable. **Constraints:** fix stories, no CAP, no flag (operator,
  2026-10-06: "do marshal prevention fixes first"). Owner `spec-pyforge-marshal`. → Stories 22.13, 22.14, 53.4,
  85.6, specced 2026-10-06.
- **2026-10-07 (landing gaps, again)** — **Found: Story 22.13's epics flip misses the usual case, a launch outside
  pixi wastes every session it starts, and a land-only refusal does not say why.** (1) Herald 28.1 landed on 2026-10-07 (PR #1892, merge `6b3a1c4c30`). Its
  ledger promotion (`966b166f76`) touched only the ledger, and herald's `epics.md` still reads `**Status:** backlog`
  under `### Story 28.1:`. Story 22.13 put the flip inside `_promote_tracked_spec`, after the early return for a spec
  that is already `done` on `origin/main`. A dispatch session normally sets its own spec to `done` on the branch, so
  after the merge the flip never runs. (2) Three dispatches launched as
  `.pixi/envs/pyforge-guild/bin/marshal factory dispatch …` instead of through `pixi run` (herald
  `…20261007T055516715Z-20c28cc4`, steward `…20261007T055444723Z-4d4c948e`, warden `…20261007T055413377Z-abbfa51f`)
  ran their full sessions and were then refused at `MRS-GATE-002`. The S-13.7 guard
  `python scripts/spec_surface_reconcile.py` looks up `python` on the supervisor's PATH, and that PATH had none. The
  same launch also lost the caveman and codegraph layers (`MRS-DISP-042`, `MRS-DISP-054`). Each session's work waited
  until an operator re-verified it by hand and re-dispatched it land-only. (3) That land-only path then hid its own
  refusals. Warden 14.2 and steward 74.2, re-dispatched land-only at the same time, both answered
  `skipped-unverified` with only `MRS-DISP-014` and `MRS-DISP-040`. `_verification_verdict_for_cap4` keeps the verdict
  and drops the verification's findings, turns any caught exception into `refused` with no message, and journals
  nothing in the run dir. A hand replay on warden's worktree minutes later read `warn`. The likely cause, two
  `platform-ci-local` runs colliding on fixed ports and a fixed work dir, had to be reconstructed by hand. **What it
  looks like when fixed:** every landing leaves the story's epics line at `done`, whether or not the spec still
  needed its own publish. A dispatch either refuses before its session starts when verification could not find its
  interpreter, or runs the guard with the supervisor's own interpreter. A land-only refusal names its failing gate,
  command or exception in the dispatch output and journals a `dispatch-verification` outcome the way the supervisor
  does. **Constraints:** fix stories, no CAP, no flag; the `platform-ci-local` lock belongs to the script's owner and
  is chained separately. Owner `spec-pyforge-marshal`. → Stories 22.15, 22.16, 22.17, specced 2026-10-07.
- **2026-10-07 (baseline conflict)** — **Found: two landings that both stamped the spec-surface baseline cannot both
  land.** Since Story 53.2 a dispatch landing names its governed paths on their Specs, runs a scoped
  `--write-baseline --spec … --accept …` and commits `scripts/.spec-surface-baseline.json` on its own branch. When
  another landing stamps the same Spec on `main` first, the merge conflicts on that file. The CAP-4 heal (Story 28.20)
  treats only Spec memlogs, the station's own ledgers and `.claude/memory/MEMORY.md` as mechanical, so it refuses
  with `MRS-DISP-038` naming `scripts/.spec-surface-baseline.json`. Marshal 22.17 (PR #1899, run
  `pyforge-marshal-20261007T090238879Z-39903546`) verified and was refused exactly so, after warden 14.2, steward
  74.2 and the doctor and marshal chain PRs merged; both sides had stamped `spec-pyforge-core`. An operator merged
  `origin/main` into the branch by hand (`1e2334036d`) and kept `main`'s baseline, and `spec-surface-check` then
  passed with no further stamp, because the memlogs already named the paths. The stamp script's own docstring
  (DW-12-5-3) already gives the rule: re-stamp the Specs each side reconciled, never hand-merge the JSON. Now that
  every landing stamps, any landing that waits behind another will hit this. **What it looks like when fixed:** the
  heal resolves a baseline conflict the way it resolves a memlog conflict. It takes `main`'s baseline, re-runs the
  landing's own scoped reconcile on the merged tree, waits for the healed head's checks and retries the merge.
  Foreign drift still refuses (`MRS-DISP-048`), and any other unknown path still escalates (`MRS-DISP-038`).
  **Constraints:** a fix story, no CAP, no flag; never a bare stamp, never a `--spec` for a Spec the branch did not
  touch. Owner `spec-pyforge-marshal`. → Story 22.18, specced 2026-10-07.
- **2026-10-07 (flag registry conflict)** — **Found: two flag stories cannot land one after the other either.**
  Every flag story registers its key in the same four files, at the same place each time:
  `src/platform/config/flags.json`, `src/platform/config/flag-overlays.json` (one line at the end of each
  environment), core's `tests/unit/test_flags.py` (`_SHIPPED_CLOCKS`, `expected`, `per_environment`) and the
  platform's `tests/test_openfeature_file_flags.py` (`_SHIPPED_BOOLEANS`). So the second of two flag landings always
  conflicts there, and the heal escalates those files the way it escalated the baseline. Warden 14.3 (PR #1903, run
  `pyforge-warden-20261007T093623012Z-77c754d3`) was refused with `MRS-DISP-038` naming the baseline, both JSON files
  and `test_flags.py`, after herald 29.1 and steward 74.2 landed. Herald 29.1 itself had needed an operator merge
  (`e5432aa8d6`): the JSON files unioned key by key, `main`'s keys first, and `per_environment` kept both entries.
  **What it looks like when fixed:** the heal unions the registry the way that operator did. A key both sides set to
  different values, or a change that is not a pure addition of entries, still escalates. The landing re-runs the flag
  gate and both flag test modules on the healed tree before it pushes. **Constraints:** a fix story on 22.18's heal
  path, no CAP, no flag. Owner `spec-pyforge-marshal`. → Story 22.19, specced 2026-10-07.
- **2026-10-08 (verify and landing order)** — **Found: the supervisor formats a file after it has stamped it, and a
  story that recommends a follow-up review cannot pass its own CI.** (1) After herald 29.2's fix turn, the supervisor
  ran Story 85.5's reconcile first (`104929ec89`, `3b3d2a8fec`, `ef558bf954` named the turn's paths and stamped
  `spec-pyforge-herald` and `spec-pyforge-core`), and only then the pre-verify ruff pass of Stories 83.9 and 83.15,
  which committed a one-line format of herald's `tests/unit/test_station_api.py` (`f1b8184bd1`). Re-verification read
  that file as drift its Spec's memlog did not name and refused at `MRS-GATE-001` on
  `python scripts/spec_surface_reconcile.py` (run `pyforge-herald-20261007T183712284Z-b952633b`), and the story parked
  with `MRS-DISP-060` until an operator named the path by hand (`428a12b699`). (2) Herald 29.2's review pass then set
  its spec `done` with `followup_review_recommended: true`. Marshal's meta-test (Story 66.2) wants a `DW-FRR-<story>`
  row for every such spec, but `dispatch_land_finalize` writes that row only after the merge. So the PR's
  `marshal-test` was red, and the landing was refused with `MRS-DISP-056` (PR #1912, run
  `pyforge-herald-20261008T043732276Z-071a3953`). Each re-dispatch launched another full session on the `done`, flagged
  spec instead of landing, until an operator added the row on the branch by hand (`4d40fc9b4a`) and the next run landed
  (`cb46142c8d`). **What it looks like when fixed:** a fix turn formats before it reconciles, so one reconcile names the
  fix and the formatting together, and nothing writes a story file between that stamp and re-verification. A landing
  whose story spec is `done` and flagged writes its own `DW-FRR-<story>` row on the branch before CI sees it, and
  finalize's post-merge carry finds the row and adds nothing. **Constraints:** fix stories, no CAP, no flag; the
  meta-test keeps no exemption; the relaunch rule for a `done`, flagged spec is not changed here. Owner
  `spec-pyforge-marshal`. → Stories 22.20, 22.21, specced 2026-10-08.
- **2026-10-10 (cross-surface fix turn)** — **Found: a refusal at the cross-surface gate never gets its fix turn.**
  Dispatch verification refuses at two gates: `MRS-GATE-001`, when a story verify command fails, and `MRS-GATE-015`,
  when a cross-surface command fails (`flag-gate-check`, `platform-ci-local -- --test`, `bmad-estate-check`). Story
  85.1's fix turn reads its failed commands from the verification's `failed_commands`. That list is built by a parser
  that only accepts a message starting `verify command '…'`, from reports read only out of the envelope's `commands`.
  A `MRS-GATE-015` message starts `cross-surface verify command '…'`, and its report sits under
  `cross_surface_checks`. So a refusal whose only failure is cross-surface journals `failed_commands: []`, the
  decision reads `no failed verify command to fix`, and the run goes straight to `failed` with nothing journaled about
  the skipped turn. That happened twice: marshal 87.5 (run `pyforge-marshal-20261009T221327283Z-283f3080`) and
  steward 85.5 (run `pyforge-steward-20261010T100406402Z-aee344c6`), both on `flag-gate-check` exit 1. Both were fixed
  by hand. Herald 19.2 (run `pyforge-herald-20261010T105313078Z-a4b44f7d`) got its one turn on `MRS-GATE-001`, then
  re-verification refused at `MRS-GATE-015` on `platform-ci-local -- --test`. It parked with `MRS-DISP-060` naming no
  command (`failed_command: null`), against CAP-286's own success criterion. Its first verification counted four
  findings but handed the turn only the three `MRS-GATE-001` commands. Marshal 87.4's turn on `MRS-GATE-001` stopped
  at its reconcile, and its `flag-gate-check` failure surfaced only at hand landing. **What it looks like when
  fixed:** a cross-surface failure reaches the fix turn the way a story command does. The prompt quotes the failed
  command and its output tail and mandates the exact re-run. The budget stays one turn per run across both gates, and
  that one turn sees every failed command of both gates at once. A still-red re-verification parks with
  `MRS-DISP-060` naming the command, and the turn's journal names the gate that triggered it. Teaching the prompt the
  flag gate's two-state test shape, the trap behind two of the four refusals, is recorded as a follow-up. **Constraints:**
  a fix story under CAP-286, no CAP, no flag (it rides `pyforge.marshal.verify_fix_loop`); never a second turn, never
  an unbounded loop (operator ruling 2026-10-10: "mint the MRS-GATE-015 fix-turn marshal story"). Owner
  `spec-pyforge-marshal`. → Story 85.7, specced 2026-10-10.
- **2026-10-10 (ignored-directory commit)** — **Found: a session's work is left uncommitted when it edits a tracked
  file under an ignored directory.** Every commit marshal makes in a story worktree goes through one port,
  `commit_paths`: the supervisor's finalize, the pre-verify WIP commit, the fix-turn commit, the idle auto-checkpoint
  and the landing's bookkeeping commits. It stages each named path with `git add -- <path>`. Git refuses that for a
  file that is tracked but sits inside a directory `.gitignore` excludes: it prints "The following paths are ignored
  by one of your .gitignore files" and exits 1, whether the change is staged or not. `git add -u -- <path>` stages the
  same file and exits 0. This repo tracks 24 such files: 12 under `.cursor/` (`.gitignore:693` is `.cursor/`), 10
  under `recipes/.idea/`, one under `.junie/` and one under `.pixi/`. Doctor Story 37.1 (run
  `pyforge-doctor-20261010T145603286Z-16048b81`) edited `.cursor/rules/specs.mdc`. Its finalize journaled
  `failed_step: commit` naming that path, the run ended `stopped_externally`, and the whole story sat uncommitted
  until the operator committed it by hand (PR #2081). The idle checkpoint goes through the same port and swallows its
  failure, so it saved nothing either. **What it looks like when fixed:** a tracked path the session changed is
  committed wherever it lives, modified or deleted. A path git does not track is still refused under an ignored
  directory, and marshal never forces it in. The rename and staged-deletion handling of Story 83.16 is unchanged, and
  the landing heal's conflict staging gets the same treatment. **Constraints:** a fix story, no CAP, no flag; never
  `git add -f`, never `git add -A` (operator ruling 2026-10-10: "Mint both (Recommended)"). Owner
  `spec-pyforge-marshal`. → Story 88.1, specced 2026-10-10.
- **2026-10-10 (a failed review landed)** — **Found: a re-dispatch merged a story whose independent review had just
  failed it.** Steward 87.3's first run (`pyforge-steward-20261010T154144466Z-88c00f58`) ended `failed`: verification
  refused at `MRS-GATE-015`, and its one fix turn ran out its budget (`MRS-DISP-059`). The operator fixed two problems
  by hand, then recorded an independent review in the tracked spec on the branch: status back to `in-progress`,
  `review_loop_iteration: 1`, and a Review Triage Log entry headed "Independent review, iteration 1: FAIL (3 high, 3
  medium)". Re-running `marshal factory dispatch` was meant to send the story back to work. Instead Story 83.10's
  land-only rule read the moved head as "the operator fixed the branch" and `in-progress` as "where a session
  stopped". It re-verified green, merged the branch (`85e70dedf5`), and finalize marked the spec `done`
  (`a8eae09dce`). A forward that lets a client reach the sidecar's unauthenticated MCP faces reached `main`. The
  same two facts were right on 2026-10-02, when marshal 82.5's operator fixed a branch and left its spec at
  `in-progress`. So the status alone cannot tell a fixed branch from a sent-back one; the review entry can.
  **What it looks like when fixed:** a re-dispatch lands only a story whose spec reads `in-review` or `done` and
  whose latest review entry did not fail, latest by the order git added the entries. Otherwise it refuses by name,
  journals the refusal, and says how to go on: set `ready-for-dev` to resume, or `in-review` to land finished work.
  It never lands, and it never launches a session on a guess. A finalize never marks a spec `done` past a failed
  review. A send-back, a first run and a held landing behave as before. **Constraints:** a fix story under CAP-169
  (Story 29.2's land-only path, extended by 83.7, 83.10 and 83.18) and CAP-229 (Story 79.1's promotion), no CAP, no
  flag; marshal never edits the spec, the log or the ledger to get past its own gate (operator ruling 2026-10-10:
  "Yes, mint it (Recommended)"). Owner `spec-pyforge-marshal`. → Epic 89 / Story 89.1, specced 2026-10-10.
- **2026-10-10 (completed while the session ran)** — **Found: the supervisor recorded a dispatch `completed` 1.3
  seconds after launch, while the session went on working for six more minutes.** Atlas Story 25.1's run
  (`pyforge-atlas-20261010T232600552Z-1b28d6db`, cursor, `composer-2.5-fast`) launched at 23:26:00Z. On its first
  tick the supervisor journaled `dispatch-completion` `completed` with `session_alive: true`, `changed_paths: []`,
  `story_merged_on_main: true` and a final revision equal to its baseline, then exited. The merge it saw was not this
  run's: `origin/main` holds the 2026-09-10 landing of atlas's earlier Story 25.1 (PR #1114, from
  `dispatch/pyforge-atlas/25.1`), a key the station's 2026-09-17 rekey later gave to today's story. The check that the
  run's head is on `main` (Story 83.14) proved nothing, because the run had not committed yet and its head was
  `main`'s own tip. And the completion judge reads a merge before it reads whether the session is alive. The cursor
  session kept writing until about 23:32Z: 19 files, 869 lines, and a closing note that it had not run its review
  loop or committed. Nothing committed, verified, reviewed or landed that work; the operator committed it by hand.
  **What it looks like when fixed:** a run is complete only after every process of its session has exited, not just
  the one marshal launched. A merge counts only when the run itself has moved its head, the rule `branch_merged`
  already follows (Story 22.10). While the session lives the supervisor keeps polling, whatever `main` says. When the
  session exits with work left in the worktree, the supervisor commits, verifies and lands it as it does for any
  finished session. Tests reproduce a session whose launched process exits early while a child keeps writing.
  **Constraints:** a fix story under CAP-160 (Story 22.2's completion judgment), no CAP, no flag; completion stays
  judged from git and process facts, never the session's word (AD-75, AD-9); a fact the supervisor cannot settle never
  reads as done (AD-8) (operator ruling 2026-10-10: "Yes, mint it (Recommended)"). Owner `spec-pyforge-marshal`. →
  Epic 90 / Story 90.1, specced 2026-10-10.
- **2026-10-10 (a corrupt environment.yaml landed)** — **Found: dispatch landings carried a pixi warning inside
  `environment.yaml` onto `main` six times in one week.** The file is derived: it must equal the stdout of `pixi project
  export conda-environment -e build`. Inside a `pixi run` shell in a story worktree, pixi prints "WARN Using local
  manifest <worktree>/pixi.toml rather than <primary>/pixi.toml from environment variable `PIXI_PROJECT_MANIFEST`" on
  stderr. A session that regenerated the file with stderr captured put that coloured line first, and `yaml.safe_load`
  refuses the result. Marshal's idle checkpoint committed it as `wip: <key> (auto-checkpoint)`, and nothing on the
  dispatch path compares the file with the export. Verification runs the station's commands, `lint-types` and the
  cross-surface checks, and none of them reads the file. The landing waits on every CI check (Story 80.1), but the
  repo's only sync lint (`.github/workflows/scripts/linter.py`) runs in the `staged-recipes-linter` workflow, which
  has been disabled since 2026-08-24. The pre-push preflight skips `dispatch/*` branches. So the file reached `main` with
  the landings of marshal 86.6 (2026-10-04), herald 27.3 (2026-10-08), steward 71.5 and 71.7 (2026-10-08 and -09),
  steward 87.3 and warden 15.1 (2026-10-10, PR #2099). Each time a later merge or a hand fix took it out, and `main`
  has carried it again since warden 15.1's landing (`bab2162d73`). **What it looks like when fixed:** before dispatch
  verifies a story whose diff touches `environment.yaml` or `pixi.toml`, marshal regenerates the file from the export's
  stdout alone and commits it on the dispatch branch, journaled, the way it already applies `ruff format`. Verification
  then runs one more cross-surface check for those two paths, steward's `provision --verify`, and a mismatch refuses the
  landing under `MRS-GATE-015`, naming the file and the fix command `pixi project export conda-environment -e build
  2>/dev/null > environment.yaml`. A repo-scope detector that catches the same file on a hand-landed branch is steward's,
  recorded as a follow-up row. **Constraints:** a fix story under CAP-170 (Story 22.14's cross-surface rule table), no
  CAP, no flag; marshal never hand-edits the file and regenerates it only from the exporter (operator ruling
  2026-10-10: "yes mint both stories"). Owner `spec-pyforge-marshal`. → Epic 91 / Story 91.1, specced 2026-10-10.
- **2026-10-10 (a dead run read as live)** — **Found: once Story 90.1 landed, every dispatch run whose session had
  exited read as live, and one whose worktree was gone crashed the next launch.** Story 90.1 made session liveness read
  the session's process group through a psutil adapter. The adapter asked `psutil.process_iter` for a `pgid` attribute
  that psutil does not have, so on psutil 7.2.2 every call raised "invalid attr name 'pgid'". Story 90.1 counted a group
  read that cannot answer as alive (AD-8), and its real-process test checked only the live half. So a run with no
  `dispatch-completion` outcome read as live for good. On the host at `909a725e16`, `dispatch_session_alive` was true
  for marshal 86.6's run of 2026-10-04, whose pid 63830 has not existed since the host booted on 2026-10-06, and for a
  pid that never existed. The primary checkout fast-forwarded to 90.1 at 03:02Z (UTC), and by 03:07Z marshal 47.1's
  launch had crashed: `station_in_flight_conflict` read the stale 86.6 run as live and gathered its git facts for the
  refusal text, and `git rev-parse HEAD` failed in `.worktrees/dispatch-pyforge-marshal-86.6`, which an operator
  worktree sweep had removed. No caller caught that `VcsCommandError`. The operator moved 51 such runs on seven stations
  into `dispatch-runs-quarantine/` and launched 47.1 again at 03:07Z. That run's session finished at 03:11Z with its
  work committed, yet its supervisor kept journaling `session_alive: true` every minute afterwards, so 47.1 was neither
  verified nor landed. On 2026-10-11 the operator ruled "Revert 90.1 now (Recommended)": a hotfix (PR #2106,
  `a085cd0344`) reverted 90.1's code and tests (merge `d013fdb9fe`), and its spec, memlog and `done` key stay. That brings back the defect 90.1 fixed,
  atlas 25.1's run read `completed` while its session still wrote. **What it looks like when fixed:** 90.1's
  behaviour lands again, in a form that works. Completion is recorded only after the session's whole process group has
  exited, and a merge counts only once the run has moved its head. The group is read with calls that exist
  (`os.getpgid`, or psutil APIs present in 7.2.2), and a member counts when it started at or after the launch. A read
  error is never "alive": that tick falls back to the launched pid with its identity checked, so a reused pid is not
  the session, and the heartbeat names the error. A run whose recorded worktree no longer exists is never live and never
  crashes a launch or a status read. It is reported as stale, with the quarantine directory as the remedy, and dispatch
  goes on. The story lands only after an independent review. **Constraints:** a fix story under CAP-160 (Story 22.2's
  completion judgment, extended by Stories 83.1 and 90.1), with CAP-167, CAP-141, CAP-163 (the one-in-flight guard)
  and CAP-5 (fleet visibility), no CAP, no flag. Marshal reports a stale run and never moves or deletes one (operator
  rulings: 2026-10-10 "yes mint both stories"; 2026-10-11 "Revert 90.1 now (Recommended)" and "Retitle
  (Recommended)"). Owner `spec-pyforge-marshal`. → Epic 92 / Story 92.1 ("The dispatch supervisor reads session
  liveness correctly and never treats a vanished worktree as live"), specced 2026-10-10, reshaped 2026-10-11.
- **2026-10-11 (recall is built and never runs)** — **Found: the recall layer is built, tested and reported as enabled,
  and no live session has ever received a recall.** Stories 47.1–47.4 (`spec-marshal-recall-in-the-loop` CAP-1..4)
  landed on 2026-10-08 and 2026-10-11. `inject_recall_feedback` runs `scribe recall --mode memory` and writes the loop
  home's `recall-feedback.md`; `augment_bmad_loop_session_prompt_with_recall` folds that block into a dev or review
  prompt behind `[context.recall]`; a miss injects nothing. Nothing outside the unit tests calls the fold
  (`DW-marshal-47-2`, `DW-marshal-47-3`). `cli/spin.py` launches `bmad-loop run` with `[plugins] enabled = []`, so
  bmad-loop's `pre_session` hook, the one place its session prompt can change (`proposed_prompt`), never sees the
  block. `marshal factory dispatch` builds its `bmad-build-auto` prompt (`adapters/harness_bmadbuild.py` :415) with no
  recall at all, while every dispatch envelope reports `"context": {"recall": {"enabled": true, ...}}`: a layer
  declared on and never attempted. The Spec also sat outside this chain under a `cross-station-seam` exemption, which
  AGENTS.md reserves for the kernel and testing-kit seams. **What it looks like when fixed:** the satellite Dream is
  folded into this one (the 2026-10-11 section at the end) and moves to `archive/docs/dreams/`; its four CAPs continue as
  `spec-pyforge-marshal` CAP-288..CAP-291 and its Spec folder becomes a pointer. When `[context.recall]` is enabled,
  both engines call the one fold before a session starts: the dispatch prompt carries a grounded block, and a
  `bmad-loop` dev or review session gets the same block through `pre_session`. One `scribe recall` runs per story
  dispatch. The dispatch envelope and journal say whether recall ran and whether it grounded, missed or failed, never
  `enabled` without an attempt, and a miss injects nothing. **Constraints:** a fix story under the carried CAP-1 and
  CAP-2 (CAP-288 and CAP-289 after the render), no further CAP, no flag; scribe stays the sole owner of capture and
  grounding, recall stays a CLI subprocess, and marshal never edits bmad-loop's installed package (operator rulings
  2026-10-11: "in-progress (Recommended)", "Mint a wiring story (Recommended)" and "Fold into pyforge-marshal
  (Recommended)"). Owner `spec-pyforge-marshal`. → Epic 93 / Story 93.1, specced 2026-10-11.
- **2026-10-11 (a passing review read as older)** — **Found: the review gate read a passing review as older than the
  failure it answered, and refused a finished story.** Story 89.1's land-only gate takes the latest Review Triage Log
  entry in git's order, from `git blame --porcelain`. That format prints a commit's details, its committer time among
  them, only the first time the commit appears in the output. Marshal's parser gives every later line of the same
  commit the time 0. Steward 87.5's iteration-2 PASS commit (`a937d924be`) also changed two frontmatter lines above the
  log, so its PASS heading read 0. The older "Independent review, iteration 1: sent back" heading (`ddbd78cca7`) read
  its real time, so the gate took it as the latest entry, and `marshal factory dispatch` refused the land-only re-run
  with `MRS-DISP-063`. A commit that touched only the heading line (`b80f33a196`) worked around it. The same read
  serves the drain's plan and the landing finalize's promotion check, and the error cuts both ways: a failed review
  committed together with a frontmatter edit can read as older than the pass before it, and then a re-dispatch or a
  finalize passes it. **What it looks like when fixed:** every line git blames carries its own commit's committer
  time. A line whose time cannot be read makes the log unreadable, so the gate refuses (AD-8); it never counts as
  oldest. A test with a real repository commits a "sent back" entry, then a commit that edits the frontmatter and adds
  a later PASS heading: the gate takes the PASS, and the mirror case refuses. **Constraints:** a fix story under
  CAP-169 (the land-only path, whose gate Story 89.1 added) with CAP-229 (the promotion check), no CAP, no flag; the
  gate's rule and its callers do not change, and git's order stays the authority (operator ruling 2026-10-11: "Mint fix
  story (Recommended)", queued after Story 93.1). Owner `spec-pyforge-marshal`. → Epic 94 / Story 94.1, specced
  2026-10-11.
- **2026-10-11 (a held PR is never marked ready)** — **Found: a landing held for review is never released, so a passed
  review cannot land.** Story 83.18 holds a send-back's landing at a draft PR until the operator marks the PR ready or
  the spec reads `landing_review: passed`. Only the first route works. Marshal marks a PR a draft in two places and
  never marks one ready: the forge adapter's ready call (`gh pr ready`) has no caller. With `landing_review: passed`,
  the land-only re-dispatch decides not to hold and goes straight to the merge, and GitHub will not merge a draft.
  Steward 87.5's re-dispatch refused that way (`MRS-DISP-020` on PR #2111), and the PR was marked ready by hand. Story
  83.18's test of the passed route opens a fresh PR that was never a draft, so it never saw the gap. **What it looks
  like when fixed:** when the spec reads `landing_review: passed` and the PR is a draft, the landing marks it ready,
  records that, and merges. A ready call that fails refuses the landing and merges nothing (AD-8). A held story still
  opens or keeps a draft, and marshal never marks ready a draft whose review has not passed. **Constraints:** a fix
  story under CAP-169 (the land-only path, which Story 83.18 extended with the hold), no CAP, no flag; the hold rule
  and its predicates do not change (operator ruling 2026-10-11: "Fold into 94.1 (Recommended)"; Story 94.1 had
  already been dispatched, so the fold is a second story in the same epic). Owner `spec-pyforge-marshal`. → Epic 94 /
  Story 94.2, specced 2026-10-11.
- **2026-10-11 (pre-verify ruff covers the platform and the portal packages)** — **Found: dispatch applies ruff's
  safe fixes and format only to a story's files under `src/shared/packages/pyforge-*`, so a platform file is refused
  on a fix ruff could have made.** Stories 83.9 and 83.15 run `ruff check --fix` (safe fixes only) and `ruff format`
  before verification, but only on changed `.py` files under the ten `pyforge-*` packages, from each package's own
  directory. A story's files under `src/platform` (its own ruff table: target `py312`, line length 88,
  `force-single-line` imports, migrations excluded) get no pass, and `platform-ci-local -- --test` then refuses them
  under `MRS-GATE-015`. The nine `django-*` portal packages get no pass either; they have no ruff table today, and
  steward Story 93.1 (dispatched now) gives each one its own table and puts them under `lint-types`. Steward 91.1's run
  (`pyforge-steward-20261011T235216324Z-30fdeec5`) was refused at 00:29:48Z (UTC, 2026-10-12) on one I001 in
  `src/platform/tests/test_stations_index.py`, an import order `ruff check --fix` sorts, and its verify-fix turn was
  killed after 900 s (`MRS-DISP-059`), so the run failed. Herald 37.1's run (`pyforge-herald-20261011T190323017Z-deb8f4a9`)
  journaled a pre-verify pass at 19:10:46Z for one `pyforge-herald` file and none for its platform test. It was then
  refused under `MRS-GATE-015` on E501, RET504 and PLC0415 in `src/platform/tests/test_herald_portal_without_herald.py`,
  and the session cleared them by hand (`e62682df15`). None of those three has a safe fix, so a wider pre-verify would
  still not have cleared them. **What it looks like when fixed:** before verify, marshal groups the story's changed
  `.py` files by the nearest parent directory whose `pyproject.toml` declares a `[tool.ruff]` table: a `pyforge-*`
  package, a `django-*` package once its table lands, or `src/platform`. It runs the same safe fixes and format for
  each group from that directory, so each tree's own target, line length, import style and excludes apply (a
  `py314` table would write `except A, B:` into a `py312` tree). A file with no such parent is left alone, as is any
  file the story did not change. The journal names each group and the files it changed, and a ruff failure in one
  group is journaled without stopping the others. What ruff cannot fix safely still reaches verify. **Constraints:**
  a fix story under CAP-161 (Story 22.3's verification, under which Stories 83.9 and 83.15 run their pre-verify step),
  no CAP, no flag. Never `--unsafe-fixes`, and never a file outside the story's change set. The operator's ask,
  verbatim: "Do this task here: Extend marshal pre-verify ruff to platform and portals". The `pyforge-marshal`
  environment had no ruff, so the tests that run the real ruff skipped outside a dispatch. On the operator's ruling
  "Fold into 95.1 (Recommended)", the same story adds ruff to that pixi feature, re-locks, regenerates
  `environment.yaml`, and makes those tests fail instead of skip when ruff is missing. Owner `spec-pyforge-marshal`.
  → Epic 95 / Story 95.1, specced 2026-10-11.
- **2026-10-11 (duplicate frontmatter keys in story specs)** — **Found: dispatched sessions write a story spec's
  frontmatter key a second time instead of replacing it, and marshal reads the first copy while every other reader
  reads the last.** Measured on `main` at `a21524e9d6`: 37 of the 1,407 tracked story specs with frontmatter carry 40
  repeated keys, `followup_review_recommended` 29 times and `review_loop_iteration` 11 times, in six projects (marshal
  15, steward 7, herald 6, doctor 5, mason 4, warden 3). None of the other 900 tracked frontmatter files under
  `_bmad-output/` and `docs/` (Dreams, `SPEC.md`s, PRDs, spines, `epics.md`, memlogs) repeats a key. All 40 were
  written on `dispatch/pyforge-*` branches and committed by marshal's `supervisor finalize` (18), its `wip: <key>
  (auto-checkpoint)` commits (16) or the session's own step-04 commit (6). The writer is the `bmad-build-auto` session:
  its installed step files tell it to "write `followup_review_recommended: false`", to set `review_loop_iteration` and
  to "increment it by 1, and write it back" (`step-01-clarify-and-route.md:31`, `step-04-review.md:70` and `:107`), and
  the session adds a line where one already exists. The same step file already guards the `deferred` list ("never add
  a second `deferred:` key", `:84`, then a full YAML parse, `:95`), and no spec repeats `deferred`. Herald 37.1 was
  fixed by hand on 2026-10-11, and steward 91.1's dispatch branch has the defect again (`review_loop_iteration` 0, then
  1). The repeat is not harmless: PyYAML keeps the last value (bmad-loop, doctor's `deferred-work`), and marshal's
  `_frontmatter_scalar` (`core/dispatch_harness_done.py:83`) returns the first. Four specs hold two different values.
  Herald 29.2 reads `followup_review_recommended: true`, then `false`: marshal reads `true` and `DW-FRR-29-2` carries
  the follow-up review in herald's ledger, while bmad-loop and doctor read `false`. Which copy is right is a fact of history, not of line order: `git blame` shows the session put its write above the
  old line in 32 of the 40 repeats, so herald 29.2's `true` is the review pass's write and the trailing `false` is
  the stale line it meant to replace. **What it looks like when fixed:** a dispatched story's spec reaches
  verification with each frontmatter key once. Before it verifies, marshal collapses a repeated key to the occurrence
  git wrote last, and refuses when history cannot say (AD-8). The build skills are told to replace a key rather than
  add one, and the specs already on `main` are cleaned the same way. Doctor's detector then holds the line on every
  PR. **Constraints:** a fix story under CAP-161 (the
  pre-verify step of Story 22.3's verification, where Stories 83.9, 83.15 and 91.1 already run) with CAP-169 and
  CAP-275 (the readers of `followup_review_recommended`); no CAP, no flag. The installed step files are never edited:
  the instruction goes in `_bmad/custom/bmad-build-auto.toml` and `bmad-build.toml` (Stories 74.3 and 87.11's layer).
  The detector is doctor's, minted the same day as doctor Story 42.1 and gated on this story (operator ask 2026-10-11:
  "Do this task here: Stop story specs gaining duplicate frontmatter keys"). Owner `spec-pyforge-marshal`. → Epic 96 /
  Story 96.1, specced 2026-10-11.
- **2026-10-12 (seed accept and repo-owned managed artifacts)** — **Found: once this repo was genesis-adopted, a PR
  that edits one of the files the seed claims fails CI, and no seed verb can record the edit.** Doctor Story 42.1
  (PR #2150) adds one row to `scripts/detectors.py`'s `_DOCTOR_SOURCE_TASKS`. That changes the file's hash
  (`3ea83244` to `20bf7374`), and CI's `oracle` check (`marshal-local-recipes-seed-oracle`, the SC-02 adopt dry run in
  `tests/integration/test_local_recipes_empty_plan.py`) fails with `PreconditionFailure: managed-content-modified`:
  rung 6 (`seed/verbs/preconditions.py`) compares every claimed file with the hash `.marshal/seed-state.yml` recorded.
  Nothing sanctioned can move that hash. `adopt` first-claims only ids state does not record yet
  (`seed/verbs/adopt.py:560`) and writes state only when its plan has actions (`:1360`), and this repo's plan is empty.
  `--force` skips rung 6 and records nothing (`cli/seed.py:1280`-`:1285`, `preconditions.py:45`-`:60` and `:720`).
  The published remedy for `managed-file-modified`, "run `marshal seed update --force` to accept it as the new
  baseline" (`seed/detect/findings.py:117`-`:120`, `docs/finding-remedy-reference.md:18`, `docs/adoption-guide.md:71`),
  is wrong: `update --force` recopies the file from the packaged template (FR-101: discard local edits;
  `seed/verbs/update.py:821`-`:931`), and the template ships no payload for any `copied-managed` file. On a fixture of
  this repo's claimed files, `update --run --yes --force` exits 2 ("copier recopy failed"); where staging succeeds,
  `_staged_bytes_for` raises `InternalError` (`update.py:704`-`:728`). Story 86.2 claimed five `copied-managed` files
  by recording this repo's own content (its brownfield bootstrap, `adopt.py:882`-`:890`). Three of them are this
  repo's own files and change all the time. From 2026-09-12 to 2026-10-12, `scripts/detectors.py` changed in 11
  commits; its 28-row `_DOCTOR_SOURCE_TASKS` is the hand list the manifest's rationale says the registry does not need
  (`seed/templates/manifest.yaml:188`-`:192`). `docs/dreams/README.md` changed in 65; its 109-row Dream table gains a
  row with every new Dream (AGENTS.md pre-PR item 8). `.github/workflows/detectors.yml` changed in 4. It is this
  repo's own 238-line CI and does not run `marshal seed check`, which the manifest's rationale says it does. The two
  scripts that are model machinery, `scripts/bmad-switch` and `scripts/bmad-loop-worktree`, changed in 2 and 1.
  The Spec companion's own watch metric (`extraction-manifest.md` § *Watch metrics*) says a class assigned wrong is
  fixed in the manifest, not in the engine. Story 86.2's AC6 does not hold either. Its landing left the check as a
  manual residual. Run at `f478cfbc5a`, `marshal seed update --repo-root .` (dry run) plans 12 actions: wholesale
  regenerations of the five `copied-managed` files and the two hybrid regions, `.bmad-loop/policy.toml` (owed only in
  a loop home), `.claude/skills/**` (`unclassified-deferred`) and three literal `{{ slug }}` paths. `update`'s
  `_manifest_for_update` (`update.py:339`-`:347`) filters `applies_to` only, while `adopt`'s `_manifest_for_adopt`
  (`adopt.py:486`-`:513`) has dropped those entries since Story 86.2. **What it looks like when fixed:** an operator
  who means an edit to a claimed file runs `marshal seed accept <artifact-id>`. It hashes the file on disk (or each
  recorded region of a hybrid file) with the hash rung 6 uses, writes the new hash only through the state store's
  atomic writer, and keeps who, when, the old and new hash and the reason in the state file itself. It refuses an
  unknown id, an unclaimed artifact, and a class nothing guards. The three repo-owned files become `copied-seeded`
  (repo-owned after the first write), so a new Doctor source or a new Dream never trips the oracle. Every remedy that
  promised `update --force` would accept an edit names `seed accept` instead. And a `seed update` dry run on an
  adopted repo plans only what would really change: zero actions here. **Constraints:** fix stories under the
  capabilities that shipped the seed verbs (CAP-10, CAP-11, CAP-12, CAP-13, CAP-15, CAP-17, CAP-279), no CAP, no flag.
  `SPEC.md`'s do-not-hand-edit rule for the state file (`SPEC.md:287`) stays true: the new verb is the sanctioned
  writer. The oracle's exclusion set and skip table do not widen (K-02). The operator's ruling, verbatim (2026-10-12,
  "Sign off + fix story (Recommended)"): "Authorize this one recorded hash re-record for 42.1, noted in 42.1's triage
  log and the marshal memlog as an operator-authorized exception, then land 42.1. Also mint a marshal fix story: a
  journaled `marshal seed accept <id>` re-record verb, reclassify the repo-owned artifacts (detectors.py, dreams
  README, detectors.yml) so routine edits don't trip it, and correct the wrong `update --force` remedy text." Two
  stories, not one: the update planning fix is a separate defect in a separate path (`update.py`), found while
  checking the remedy. Owner `spec-pyforge-marshal`. → Epic 97 / Stories 97.1 and 97.2, specced 2026-10-12.
- **2026-10-12 (ci pauses at merge)** — **Found: a landing records its checks but never that a gate was paused.** With
  `PAUSE_PLATFORM_CONTAINER_BUILDS=true` since 2026-10-09 every platform-touching story landed with `container`,
  `container-dbgpt` and `golden-path-promotion` skipped, and with `PAUSE_CONTAINER_BUILDS=true` since 2026-10-04 every
  station story landed without `guild-container`; the landing journal, the PR body and the promotion record say
  nothing of it, so a reader of `landing_evidence` sees a green merge and cannot tell a skipped gate from a passed
  one. `main` has no required checks (this log, 2026-10-01 later), so a pause is invisible to the merge too. Steward's
  same-day append mints the registry (`docs/governance/ci-surfaces.yaml`) and `pyforge steward ci status --json`; the
  plan is `docs/intake/ci-pause-control-plane/PLAN-2026-10-12.md`. **What it looks like when fixed:** `dispatch_land`
  reads `steward ci status --json` at landing time and writes `ci_pauses_at_merge: [<surface ids>]` into the landing
  journal; the PR body gains one line ("CI paused at merge: container, container-dbgpt, guild-container");
  `landing_evidence` and `promotion.py` carry the list into the promotion record; an empty list is written explicitly,
  never omitted, and a `steward ci status` that cannot read live state (no `gh`, a rate limit) is recorded as
  `unknown`, not as empty. **Constraints:** a feature under CAP-4 (landing with a durable paper trail) and the
  landing-evidence grammar (CAP-126–CAP-129); behind a flag (`pyforge.marshal.landing_ci_pauses` proposed); reads
  steward through the CLI's JSON, never by import; depends on steward's `ci status` landing first; changes no landing
  verdict and waits on no CI. Operator ruling 2026-10-12: the plan's recommended answers Q1–Q8 stand. Owner
  `spec-pyforge-marshal`. → CAP-292 / FR-239, Epic 100 / Story 100.1, specced 2026-10-14 (the entry below).
- **2026-10-12 (two tests red the local preflight)** — **Found: two marshal tests fail every local `pr-preflight` run
  while CI's `marshal-test` stays green, so every push needs a journaled skip.** On 2026-10-12 the pre-push preflight
  refused four pushes, from two planning-only branches, on the same tests. (1) The NFR-P1 budget tests
  (`tests/integration/test_performance_gates.py::test_check_under_nfr_p1_budget` and
  `tests/unit/test_seed_verbs_check.py::test_run_check_completes_within_the_nfr_p1_budget`) read 5.10 s to 8.93 s
  against 5 s. Measured: the walk and classification take about 0.3 s; `seed/detect/referenced_deps.py` spawns
  `bmad-loop --version` (1.4 s) and `copier --version` (2.6 s), and first a Doctor subprocess whenever `doctor` is on
  PATH, as it is in every preflight lane. That fixed probe cost stretches under the preflight's parallel load. (2)
  `tests/unit/test_dispatch_verification.py::test_evaluate_dispatch_verification_pre_existing_packaging_gate_warns`
  reads `refused`: its fake process failed any command whose joined argv contained `pyforge-marshal-test`, and the
  preflight names each lane's scratch directory after the lane, so `tmp_path` sits under
  `…/pyforge-marshal-test/pytest-basetemp/…`. The commit-attribution `git` read of `refs/remotes/origin/main...HEAD`
  carries the worktree path, so the fake failed it (MRS-GATE-009). Reproduced in 1.2 s with `--basetemp` under a
  directory named `pyforge-marshal-test`; the same test under any other name passes. The first diagnosis, a
  module-level cache poisoned by an earlier test on the same xdist worker (captured to team memory the same day), was
  wrong. **What it looks like when fixed:** the NFR-P1 tests stub the machine-readiness probe and keep their
  wall-clock 5 s budget on the walk they were written to measure; the fake matches a pixi task as an exact argv token,
  and the packaging-gate test also runs with its worktree under a directory named like the lane, so the verdict cannot
  depend on the path; the full marshal lane passes three times under the preflight's conditions and `pr-preflight`
  passes; the team-memory entry says what really happened. **Constraints:** a fix under CAP-13 (NFR-P1, `seed check`)
  and CAP-139 (verify blast radius, `pre-existing-gate`), no CAP, no flag; tests only, no product code. The probe cost
  itself, about 4 s of NFR-P1's 5 s for `marshal seed check` end to end and more when Doctor is on PATH, is a product
  question recorded as the story's deferral. Operator ask, 2026-10-12: "Do this task here: “Fix two marshal tests that
  red local pr-preflight”". Owner `spec-pyforge-marshal`. → Epic 98 / Story 98.1, specced 2026-10-12.
- **2026-10-12 (seed check waits on its probes one at a time)** — **Found: `marshal seed check` spends most of NFR-P1's
  five seconds starting other programs one after another, and calls a slow one missing.** This is Story 98.1's
  deferral, `DW-marshal-98-1`. `seed/detect/referenced_deps.py` verifies each `referenced` manifest entry before it
  judges anything.
  - **Doctor delegation first.** When `doctor` is on PATH, as it is in every Guild lane, it first runs `python -m
    pyforge.doctor.sources genesis-referenced-deps --json`. Doctor ships no such source, so this always exits 2 and
    costs 0.32 s.
  - **Then the CLI probes, one by one.** `copier --version` (1.78 s here, 2.6 s in 98.1's measurement),
    `bmad-loop --version` (1.07 s; 1.4 s), `pixi --version` and `tmux -V`.

  Measured at `c447946b3f` on the NFR-P1 fixture, `run_check` takes 2.65-2.95 s. Only 0.05 s of that is its own work;
  the rest is child processes, and under load the sum passes 5 s. Each probe has a 5 s timeout, and a timeout maps to
  the same "referenced dependency is not installed" DRIFT finding as a missing tool. So a busy machine reports an
  installed `copier` as missing. Story 98.1 stubbed the probe in the two NFR-P1 tests, which now time the walk. Since
  then nothing times the real check against its budget. **What it looks like when fixed:** the delegation and the
  CLI probes start together, so the wall time is the slowest one rather than the sum, and a successful delegation
  still wins. Findings keep manifest order. A probe that times out says it timed out, naming the command and the
  limit. One `slow` test times the real `run_check`, with real probes, against the 5 s budget in the serial slow lane.
  **Constraints:** a fix under CAP-13 (NFR-P1) and FR-95 (Story 11.5), no CAP, no flag. No finding's severity or type
  changes, the budget stays 5 s, and the probes still test the tool on PATH, never an in-process import. Operator
  asks, 2026-10-12: "start the flaky marshal tests fix", then "merge 2171 and rescope 2172". This chain was first
  minted on PR #2172 as two stories. 98.1 fixed the test half, so it is now the product half only. Owner
  `spec-pyforge-marshal`. → Epic 99 / Story 99.1, specced 2026-10-12.
- **2026-10-14 (ci pauses at merge, specced)** — **What the 2026-10-12 entry waited for has landed: a landing can now
  ask what was paused.** Steward's Story 99.3 merged on 2026-10-13 (`7ec2ea85f3`), so steward can name every paused
  CI surface in one answer, and a landing need not guess. Its own switch is still off by default. Two things the
  earlier entry did not know turned up when the shipped answer was read. A paused surface does not always say
  `paused`: a pause past its review date says `overdue`, and a pause on a stuck workflow says `stuck`. So the
  landing must decide what did not run from what was declared and what was switched, not from the one-word verdict.
  And the switch that pauses everything at once has no line of its own in that answer, so a landing made under it
  cannot tell yet; that stays an open question for steward. **What it looks like when fixed:** as the 2026-10-12
  entry says. Every merged story's paper trail names the gates that did not run, says "none" when every gate ran,
  and says "unknown" with a reason when it could not ask; nothing about the merge itself changes. **Kinships:**
  `pyforge-steward:CAP-166` (the CI pause control plane whose answer this reads); the plan,
  `docs/intake/ci-pause-control-plane/PLAN-2026-10-12.md` § 4.4 and § 6 (its marshal row). Operator direction
  (2026-10-13): mint the doctor, herald and marshal CI-pause stories only after 99.3 lands. Owner
  `spec-pyforge-marshal`. → CAP-292 / FR-239, Epic 100 / Story 100.1, specced 2026-10-14.
- **2026-10-14 (the master switch's surfaces at merge)** — **Found: while the master switch is on, a landing names
  the master but not the gates it stopped.** Story 100.1 (#2213) lists a surface from its declared state and its own
  switch, and never from steward's verdict. Steward Story 103.1, specced the same day, gives `steward ci status
  --json` one `master:PAUSE_ALL_CI` row and marks every surface whose jobs read the master `paused`, with a new
  `paused_by_master` field set to true. 100.1's rule reads neither. So a landing made under the master will say
  `CI paused at merge: master:PAUSE_ALL_CI` and nothing of the jobs it skipped, across the 13 workflows that read it.
  100.1's spec names this as its own follow-up. One more thing turned up: the seven opt-in surfaces sit in jobs that
  read the master too, so steward will mark them paused by it even while nobody has switched them on, and they would
  not have run anyway. **What it looks like when fixed:** with the master on, the record and the PR-body line name
  the master and every surface it paused, read from steward's answer. An opt-in that is off is not called paused,
  and one that is on is. With the master off, or from a steward older than the field, the record is exactly what
  100.1 writes. **Constraints:** a fix under CAP-292, no CAP, no flag of its own (it rides
  `pyforge.marshal.landing_ci_pauses`). Marshal still never reads the master, the registry or the workflow files
  itself; steward stays the one reader of the pause state. It waits on steward 103.1, a cross-station gate the
  operator flips. **Kinships:** `pyforge-steward:CAP-166` and steward Story 103.1 (the field this reads). Operator
  ask, 2026-10-14: "chain it here". Owner `spec-pyforge-marshal`. → Epic 101 / Story 101.1, specced 2026-10-14.
- **2026-10-15 (a landing re-verifies when only main moved)** — **Found: a re-landing re-runs every gate even when the
  story's code has not changed.** When a dispatch's PR conflicts with main, someone merges main into the branch, the
  head moves, and the land-only path re-runs the station's whole `verify_commands` before it waits for CI again.
  Steward's journals of 2026-10-14 show the cost. Steward 99.6 was verified at 06:29, its landing refused on a memlog
  conflict (MRS-DISP-038) at 06:31, and after main was merged in, its two re-verifications took 19 and 27 minutes and
  both refused on load-sensitive commands. Steward 102.1 was verified at 20:35, and after that only planning commits
  and a merge of main reached its branch before its story fix (`fbb3ee095b` → `b937a1371e`): two marshal reconcile
  stamps, then the merge, whose one conflict was a herald memlog. Steward 103.1's re-verification took about 52
  minutes and then hit a load flake. Every landing makes every other open branch stale, so serial landing multiplies
  the cost. **What it looks like when fixed:** a station can opt in to reuse its verified verdict. A re-landing then
  skips the full re-verification when the story's own code is byte-identical to what was verified: every commit since
  the verified head is a merge of main or touches planning files only, no merge touched a non-planning file of the
  story's own diff, and no merge had a conflict or a hand-made change outside planning files. A narrow re-check of the
  planning surface still runs, the journal says the verdict was reused and from which one, and GitHub CI is still
  awaited, red checks refusing as before. Anything else re-verifies in full, as today. **Constraints:** a fix under
  CAP-161 (the driver verifies before any landing), with no CAP and no flag; a policy key that defaults to today's
  behaviour, opted into by the four Pages stations; never a landing on self-report, since the reused verdict is
  marshal's own independent verification of exactly the story's code. **Kinships:** steward 103.6 (the preflight fast
  mode, the same speed ask on the push side). Operator rulings, 2026-10-15: "chain it now and I'll mint the story
  chain and implement it - we need the speed to market before we move to wave 2", and "make sure we include this -
  Optional, marshal: a landing re-verification setting - that saves time too". Owner `spec-pyforge-marshal`.
  → Epic 102 / Story 102.1, specced 2026-10-15.
- **2026-10-22 (the legacy promoter dies on one commit's bytes, and misses nested refs)** — **Found:
  `scripts/legacy_preserve_promote.py` has never written a manifest.** The operator ruled on 2026-10-22 to promote the 17 `refs/attempt-preserve-dirty/*` refs
  ("go ahead"). Its first run, dry, crashed before writing anything: `UnicodeDecodeError: 'utf-8' codec can't decode
  bytes`. To classify the `rescue/dangling-*` tags, `_origin_main_patch_ids_since` runs `git show --binary | git
  patch-id` over every `origin/main` commit since 2026-06-01 (13,145), and `_git` decodes each output as UTF-8 text.
  One commit's `git show` output is not UTF-8: `e09f50352d`, a 2026-09-10 merge of `origin/main` into
  `dispatch/pyforge-doctor/21.13`, whose combined diff cuts an em-dash in a hunk header. Story 87.12's tests never fed it
  a non-UTF-8 byte. Once it ran, the independent review found the inventory silent on 8 of the legacy refs Story 87.12
  names: `for-each-ref 'refs/heads/*'` and `'refs/tags/*'` match one level only, the three kept `attempt-preserve/*`
  branches exist only on `origin`, and the archive-tag skip ran before the legacy tag table, which names two `archive/`
  tags. **What it looks like when fixed:** `_patch_id` hands `git show`'s
  bytes to `git patch-id` undecoded, and `_git` reads git's text output with `errors="replace"`, so no commit's bytes
  stop the run. The inventory reads ref prefixes, both `refs/heads/attempt-preserve/` and
  `refs/remotes/origin/attempt-preserve/`, and the legacy tag table before any skip; a legacy name carrying a date,
  which AD-81 bars from a twin's name, falls back to a `preserve/unbound/hand-*` twin. The dry run writes a complete
  manifest, and `--execute` writes the local twins. **Constraints:** a fix under
  CAP-287 (FR-234), with no CAP and no flag: the promoter is Story 87.12's one-off, dry-run-default script and is not
  flag-gated. Nothing is pushed: every push stays operator-gated behind the Story 87.15 content gate. Owner
  `spec-pyforge-marshal`. → Epic 87 / Stories 87.17 and 87.18, specced 2026-10-22.
- **2026-10-25 (marshal's own MCP server has never started)** — **Found: the `marshal` MCP server that `marshal
  init` registers cannot start, and preflight reports it healthy.** Marshal's policy declares
  `[mcp_servers.marshal] command = "marshal-mcp"` (Story 18.1), and `marshal init` renders it into the marshal loop
  home's `.mcp.json`. `marshal-mcp` builds its server on the third-party `fastmcp` package, which no environment that
  carries `marshal-mcp` installs: from `pyforge-guild` it exits 1 with `ModuleNotFoundError: No module named
  'fastmcp'`, and `local-recipes`, which has `fastmcp`, has no `marshal-mcp`. Every other server here already moved to
  the official SDK's `MCPServer` (mcp 2.x renamed `FastMCP`): atlas's, the conda-forge server and marshal's own HTTP
  face. No test builds the server, and the preflight probe (`MRS-PREFLIGHT-012`) only asks whether the command is on
  `PATH`, so it has been green since 2026-08-23 for a server no session could reach. **What it looks like when
  fixed:** `marshal-mcp` is built on the official SDK and, run from `pyforge-guild`, answers an MCP `initialize` and
  lists its tools; `marshal-mcp --help` prints its usage and exits without starting a server. `marshal preflight`
  starts each declared server, completes the handshake within a timeout and stops it. A server that crashes, hangs or
  answers with something other than an MCP reply is `MRS-PREFLIGHT-012` with the tail of its stderr; one that answers
  is reported with its tool count. **Constraints:** a fix under CAP-1 (a preflight-verified home), CAP-21 (one
  governed surface) and CAP-22 (the surface survives a clone), with no CAP and no flag. No package new to the factory:
  `pyforge-guild` already carries the `mcp` SDK, which is now declared. The probe speaks plain JSON-RPC and imports
  no SDK, so it works for any declared server. **Kinships:** DW-FU-18-2 (tool-surface coverage counts a file, not a working server).
  Operator ruling, 2026-10-25: "Go with the migration: move marshal-mcp to the official SDK MCPServer, add a real
  --help, and make preflight run a startup handshake. Plan it as one marshal story through the full Dream-to-code
  chain." Owner `spec-pyforge-marshal`. → Epic 103 / Story 103.1, specced 2026-10-25.
- **2026-10-25 (the content gate refuses what origin already holds)** — **Found: no preserve built on today's `main`
  can pass the content gate, and the gate never reads a blob an earlier commit added.** On 2026-10-25 `marshal status`
  reported 24 preserve tags that exist only locally (`MRS-STATUS-016`; 29 with the `archive/` twins), and the operator
  asked to push them. `marshal preserve push` refused because `pyforge.marshal.preserve_refs` is off. A read-only run
  of the gate's own check over the 29 tags then refused 25 of them. `run_content_gate` (Story 87.15) reads every blob
  in the tagged commit's tree, not the blobs the push would add, and today's `origin/main` fails it too: three slide
  decks over the 5 MB cap, and synthetic `sk-ant-`, `ghp_` and private-key strings in test fixtures and two story
  specs, all of them already public. Story 87.15's acceptance criteria refuse a preserve that *adds* a credential or an oversize file;
  the code judges the whole snapshot. Two more costs follow from that. A blob that an intermediate commit added and a
  later one removed is never read, although the push sends it. And each run starts two `git` processes per blob, about
  80 s per tag on this repository. Turning the flag on would push the 4 tags that pass and refuse the rest, and every
  dispatch and spin preserve would be refused the same way. A wider scan of the objects the 29 pushes would send
  (about 900; the number moves with `origin`'s refs) found no secret and no file over the cap. **What it looks like
  when fixed:** the gate judges the objects a push sends: everything reachable from the tagged commit that no branch
  or tag `git ls-remote origin` lists already reaches (pull refs are not trusted). The secret scan and the size cap
  run on every sent blob, intermediate commits included, and on the tag and commit messages, through one batched read
  on a bytes path of `pyforge.core.process`, and
  the purge-list rules still hold. A preserve whose snapshot adds nothing but clean content passes. Run read-only over
  this repository's 29 local-only tags, the gate refuses none. `MRS-STATUS-016` names a push path that works while the
  flag is off, and a second `--push-reviewed` run skips the rows the first one pushed. **Constraints:** a fix under
  CAP-287 (FR-234, AD-81), with no CAP and no flag: it makes the gate do what Story 87.15's acceptance criteria already
  say. The code lives in `pyforge.core.preserve_refs` and `pyforge.core.process`, which `spec-pyforge-core` and
  `spec-pyforge-unifying-strategy` co-govern; `ProcessPort` does not change. The story pushes nothing and the flag stays off: the push stays the operator's,
  after the row-by-row review in Story 87.12's manifest. **Kinships:** Story 87.15 (the gate), Story 87.12 (the
  reviewed manifest and `--push-reviewed`), Story 87.9 (`git ls-remote`, never local presence). Operator ruling,
  2026-10-25: "start the option 2 chain here", where option 2 is "fix the gate, then push through the reviewed
  manifest", chosen over turning the flag on in `dev`, a one-run flags override and a plain `git push`. Owner
  `spec-pyforge-marshal`. → Epic 87 / Story 87.19, specced 2026-10-25.
- **2026-10-25 (the marshal home is dirty with marshal's own file)** — **Found: `marshal refresh` refuses the marshal
  loop home because of a file marshal wrote there.** On 2026-10-25 every loop home was 180 commits behind `main`.
  `marshal refresh` fast-forwarded seven and refused `pyforge-marshal` (`MRS-REFRESH-003`, dirty working tree) for one
  untracked `.mcp.json`. `marshal init` rendered that file on 2026-10-04 from the policy's `[mcp_servers.marshal]`
  (Story 6.9 / 18.1, AD-43); no other station declares a server, so no other home has one. The refresh probe counts
  untracked files on purpose (`git status --porcelain` with `status.showUntrackedFiles=normal`), and so does
  bmad-loop's own `worktree_clean`, so `bmad-loop run` would refuse the home too. bmad-loop's Claude profile already
  calls `.mcp.json` a gitignored config it seeds into run worktrees, and this repo deliberately tracks no
  `.mcp.json`, but nothing ignores it. Two files marshal writes into loop homes had the same gap and were ignored
  for the same refusal: `.bmad-loop/profiles/` in the seeded region and `.bmad-loop/marshal-model-cost-catalog.json`
  beside it. The operator's session moved the
  file aside, refreshed and put it back, so the next refresh refuses again. **What it looks like when fixed:** the
  `.gitignore` model region that `marshal seed` manages ignores `/.mcp.json` at the repo root, so a home with
  marshal's rendered file reads clean to refresh, to bmad-loop and to the dispatch supervisor, in this repo and in
  every repo the seed installs. **Constraints:** a fix under CAP-133 (fast-forward with a clean-worktree check),
  CAP-1 (loop homes) and CAP-14 / CAP-15 (the seeded `.gitignore` region), with no CAP and no flag. The refresh probe
  stays as strict as it is; the home's file is not deleted, since preflight requires it (`MRS-PREFLIGHT-012`); and the
  shared `info/exclude` is not used. **Kinships:** Story 103.1 (the server the file registers). Operator direction,
  2026-10-25: "fix / include / resolve the gaps identified autonomously". Owner `spec-pyforge-marshal`. → Epic 104 /
  Story 104.1, specced 2026-10-25.
- **2026-10-25 (the PRD's FR arrows were numbered, not traced)** — **Found: most of the marshal PRD's `FR-n ← CAP-m`
  arrows name the wrong capability.** Two chain reviews of Stories 103.1 and 104.1 found FR-153/154 pointing at CAP-111/112
  and FR-133..135 at CAP-91..93, while the Spec carries those requirements as CAP-21/22 and CAP-132..134. Before the
  2026-09-16 fold the FR headings had no arrows; the fold commit (`1e845b55fc`) appended them by counting, so FR-128..FR-195
  read CAP-(FR−42) and the requirements added to § 7 after the first draft read whatever came next. Arrows written later,
  by Spec renders (FR-196 onward), are right. Doctor's `fr-without-cap` only checks that a cited CAP exists, so nothing
  noticed. **What it looks like when fixed:** every arrow names the capability that realizes the requirement, derived
  from evidence rather than position: the source Spec's own `CAP-k → FR-n` lines, the FR body naming its source Spec,
  stories that cite both, and matching titles, mapped through the Spec's `← spec-<old> CAP-k` provenance. A requirement
  whose source Spec no longer carries it (FR-144..FR-147) keeps its arrow, flagged for an operator decision.
  **Constraints:** a chore under `spec-one-chain-per-station` CAP-5 (FRs derive from CAPs) and CAP-8 (the marshal pilot);
  no CAP, no flag, no `SPEC.md` change; no detector rule changes. Operator ruling, 2026-10-25: "Apply the PRD FR→CAP
  re-map as proposed: 71 headings through a chore story chain, and leave FR-144..FR-147 unchanged with a note that they
  need a source-capability decision." Owner `spec-pyforge-marshal`. → Epic 105 / Story 105.1, specced 2026-10-25.
- **2026-10-25 (the seed installer's FRs never got their arrows)** — **Found: § 15's 62 requirements name no
  capability.** The fleet audit that followed Story 105.1 measured 62 marshal FRs no arrow cites, FR-66..FR-127, the
  seed installer. They came from the genesis installer's satellite PRD (renumbered into this FR space on 2026-08-08),
  whose nine capabilities were folded into this Spec on 2026-08-02 as CAP-10..CAP-18; the 2026-09-16 fold wrote no
  arrow on these bullets, and all 62 are baseline-exempt, so `fr-without-cap` never read them. **What it looks like
  when fixed:** every bullet names what realizes it, traced per requirement: the manifest CAP-10, init CAP-14, adopt
  CAP-12, check CAP-13, update CAP-15, the state file CAP-17, managed regions CAP-11, adapters CAP-16, templates CAP-18,
  the distribution CAP-8. Five requirements no capability states (Copier's public API, `--unsafe`, `--force`, the two
  version clocks, distinct exit codes) cite the Spec constraint that states them. **Constraints:** a chore under
  `spec-one-chain-per-station` CAP-5 (FRs derive from CAPs) and CAP-8 (the marshal pilot); no CAP, no flag, no
  `SPEC.md` change; no detector rule changes. Operator rulings, 2026-10-25: "Do rows 1-5 in one PR" and "Cite the
  constraint (Recommended)". Owner `spec-pyforge-marshal`. → Epic 106 / Story 106.1, specced 2026-10-25. **Amended the
  same day (the independent review; operator rulings "Apply all (Recommended)" and "CAP-15 + constraint
  (Recommended)"):** FR-116 also cites CAP-17 and CAP-12, FR-96 CAP-17, and FR-101 cites CAP-15 beside its
  constraint, so four requirements cite a constraint alone.
- **2026-10-25 (FR-144..FR-147's capabilities were dropped by the fold)** — **Ruled: restore them.** Story 105.1 left
  FR-144..FR-147 (detector self-verification) on the fold's counted arrows CAP-102..CAP-105 and opened
  `DW-marshal-105-1`: their source, `spec-dream-to-code-model-self-verification`, listed its four capabilities as a
  plain numbered list, the 2026-09-16 fold minted CAPs only from `CAP-n` lines, and so nothing carries them while
  Stories 17.1 and 17.2, which delivered them, stay done. No doctor capability carries them either, although the
  detectors now run as `pyforge-doctor` sources. **What it looks like when fixed:** `spec-pyforge-marshal` declares
  the four as shipped CAP-293..CAP-296 (the Dream-chain detector's fixtures, the drift detector's fixtures, the
  detector-incident log, the Dream hygiene mode), with that Spec as their provenance, and FR-144..FR-147 cite them one to
  one. **Constraints:** a chore under `spec-one-chain-per-station` CAP-5 and CAP-8; four CAPs restored, rendered into
  `SPEC.md` by script from the memlog decision; no flag; no FR text change; no detector rule change. Operator ruling,
  2026-10-25: "Restore 4 marshal CAPs (Recommended)". Owner `spec-pyforge-marshal`. → Epic 106 / Story 106.2, specced
  2026-10-25.
- **2026-10-25 (the refresh writes keys the ledger does not carry)** — **Found: `marshal refresh` fills every Tier-3
  feed with second copies of finished stories.** Its `sync_status` step regenerates each station's shared
  `implementation-artifacts/sprint-status.yaml` from `epics.md` through `sprint_plan.py generate`. That script's
  `_slug` cuts a title at 60 characters and keeps `_` and non-ASCII letters; the tracked ledger's keys come from
  doctor's `chain.slugify_title` (Ruling 12), which does neither. So every long or unusual title gets a second key at
  `backlog` beside the ledger's `done` one. The 04:21 refresh on 2026-10-25 wrote 550 such keys across the eight
  feeds (marshal 213, steward 122, doctor 83, mason 36, herald 33, warden 30, atlas 27, scribe 6). A `bmad-loop` spin
  reads that feed, so it sees finished stories as actionable work. The post-merge `sprint-ledger-sync` of #2319 then
  copied them into six tracked ledgers and knocked 179 epics back to `in-progress`. Nothing was committed; the feeds
  were cleaned by hand. The 14 steward duplicates found on 2026-09-25 had the same shape. **What it looks like when
  fixed:** `marshal refresh` brings the feed into step with the tracked ledger instead of re-deriving keys. Ledger keys
  the feed lacks are added; the ledger's `done` and `blocked` values win; a story the feed has advanced keeps the
  feed's value; a key whose story number the ledger carries under another slug is dropped and named, unless it is
  further along than the story's best value, which is kept and named for a re-key. A bare sync and a landing drop the
  same keys before they promote, so a stale feed cannot add a key that carries no progress to a tracked ledger.
  **Constraints:** a
  fix under CAP-265 (the hand sync repairs feed drift itself) and CAP-132 / CAP-134 (the fleet refresh and its checked
  steps), with no CAP and no flag. `sprint_plan.py` is installer-owned and stays unchanged. A story re-key still goes
  through `--rekey`. **Kinships:** Story 54.1 (CAP-265), Story 15.1 (the refresh). Operator direction, 2026-10-25:
  "Do this task here: Find what writes truncated slugs into Tier-3 feeds". Owner `spec-pyforge-marshal`. → Epic 107 /
  Story 107.1, specced 2026-10-25.
- **2026-10-03 (night, last)** — **Found: a send-back can land unreviewed, and a CFE edit cannot land at all.**
  Herald 35.1 was re-dispatched after a send-back and auto-landed before its review; drafting the PR to stop that turns
  the landing into a refusal and trips Story 83.4's hold. Doctor 41.1's CFE test edit went into `wip:` auto-checkpoint
  commits, which every station's CFE guard refuses, so the branch needs a history rewrite to land. **What it looks like
  when fixed:** a spec key or flag holds the landing for review without counting as a refusal; dispatch's own commits
  leave the CFE surface out and its CFE changes land in one `retro(cfe):` commit. **Constraints:** fix stories, no CAP,
  no flag (operator ruling 2026-10-03, "yes chain both fixes"). Owner `spec-pyforge-marshal`. → Stories 83.18-83.19,
  specced 2026-10-03.
- **2026-10-03 (night, latest)** — **Found: two more dispatch gaps.** Herald 35.1's supervisor could not commit its
  session's work because `git status --porcelain` quotes paths with spaces and the finalize passed the quoted text to
  `git add`; a Cursor session's commit on mason 27.1 carried a `Co-authored-by: Cursor` trailer that dispatch never
  checks. **What it looks like when fixed:** `changed_files` returns literal paths; dispatch verification runs the
  commit-msg rule over the branch and refuses a trailer. **Constraints:** fix stories, no CAP, no flag. Owner
  `spec-pyforge-marshal`. → Stories 83.16-83.17, specced 2026-10-03.
- **2026-10-03 (night, later)** — **Found: four gaps from today's landings.** The 83.11 team-memory union reflows the
  file's blank lines; a manual merge while a re-dispatch runs makes the supervisor declare completion and strand the
  session's later commits (83.10, 83.4); `ruff check` findings that ruff fixes safely still refuse verification (83.9
  formats only); Story 84.1 landed with tests that cannot catch a key leak and a partial listing read as complete.
  **What it looks like when fixed:** the union inserts lines without reflowing; the supervisor keys completion on the
  run's own head and lands later commits; dispatch applies ruff's safe fixes; 84.1's tests can fail. **Constraints:**
  fix stories, no CAP, no flag (operator rulings 2026-10-03). Owner `spec-pyforge-marshal`. → Stories 83.13-83.15,
  84.2, specced 2026-10-03.
- **2026-10-03 (85.1 split)** — **Ruled: split the fix turn.** Two independent reviews of Story 85.1 found the
  fix turn could not do its job (a green re-verify never landed; failed commands were read only inline; uncommitted edits
  were verified but not landed; a restart could start a second turn) and was not yet safe (credentials past redaction,
  an incomplete timeout kill, no publisher heartbeat). **What it looks like when fixed:** 85.1 lands the machinery
  dormant with the flag OFF everywhere; 85.2 makes one turn work end to end, proved by a supervisor-level test; 85.3 makes
  it safe and switches it on in dev and staging. **Constraints:** same CAP-286 and flag; keep Cursor (operator ruling
  2026-10-03). Owner `spec-pyforge-marshal`. → Stories 85.2, 85.3, specced 2026-10-03.
- **2026-10-03 (late night)** — **Found: dispatch verification passes a story that CI's coverage gate fails.** CI's
  named-module gate fails a PR when a touched module sits under the station's 80% unit floor, but dispatch verification
  never runs it and `dispatch/*` branches skip the pre-push preflight. PR #1773 went red this way (`dispatch_retry`
  78.1%) after verification passed. **What it looks like when fixed:** verification runs each touched station's coverage
  gate in that station's own environment, and an under-floor module refuses before the push. **Constraints:** a `fix`
  story, no CAP and no flag; no floor changes (operator ruling 2026-10-03). Owner `spec-pyforge-marshal`. → Story 83.12,
  specced 2026-10-03.
- **2026-10-03 (Phase 3)** — **Ruled: marshal's deferral decisions.** The operator ruled every live NEEDS-DECISION entry on
  the rulings page: for marshal 20 fix, 18 close, 2 keep. **What it looks like when fixed:** the fix rulings land as seven
  module bundles; the closes and keeps are written into the ledger with their reasons and cited evidence. **Constraints:**
  fix stories, no CAP, no flag; two rulings amend the spine directly (AD-4 `core → ports`, AD-30 payload wording).
  Owner `spec-pyforge-marshal`. → Epic 86 / Stories 86.1-86.7, specced 2026-10-03.
- **2026-10-03 (night)** — **Found: a routine memory capture blocks the next landing.** Each dispatch session's
  closeout adds a line to `.claude/memory/MEMORY.md` at the end of a section, so two stories landing one after the other
  conflict there, and the landing heal refuses the second (MRS-DISP-038): 83.7 was merged by hand and 83.4 refused.
  **What it looks like when fixed:** the heal merges appended index lines the way it merges memlog entries; an edit or
  removal still escalates. **Constraints:** a `fix` story, no CAP and no flag; sessions keep capturing (operator ruling
  2026-10-03). Owner `spec-pyforge-marshal`. → Story 83.11, specced 2026-10-03.
- **2026-10-03 (evening)** — **Found: a verification refusal throws the finished work away.** Dispatch
  verification is the one authority on a finished story's tree (2-3 minutes, no tokens), but it can only refuse. A
  campaign then relaunches a fresh session, and after two failures Story 33.6 raises the model: 83.2 ran three times
  (48 minutes, the third on opus), each refused on the same unformatted line. The other refused Cursor stories were fixed
  by hand, about four extra full-suite runs each. bmad-build-auto already tells the session to re-run the spec's checks
  after its review patches; the Cursor sessions did not, so restating that rule changes nothing.
  **What it looks like when fixed:** a verification refusal never relaunches a fresh session and never raises the model;
  the story parks, or lands once its branch is fixed; and with a flag on, the refusal first goes back to the session
  that wrote the change for one bounded fix turn, re-verified once.
  **Constraints:** verification is never relaxed; one fix turn per refusal; the resume form is profile data (AD-19); the
  retry change is a `fix` (no CAP, no flag), the fix turn is new behaviour (a CAP, flagged OFF in production). Owner
  `spec-pyforge-marshal`. → Story 83.10 and CAP-286 / Epic 85 / Story 85.1 (FR-233), specced 2026-10-03.
- **2026-10-03 (later)** — **Found: every Cursor session is refused on formatting.** Each Cursor dispatch of marshal
  Epics 83 and 66 and Story 84.1 finished its work and was refused at verification on `lint-types`, most often on
  `ruff format` alone, and was fixed by hand before landing; the sessions reported the check green.
  **What it looks like when fixed:** dispatch applies `ruff format` to the story's own files before verification and
  commits the result; type and lint errors still refuse. **Constraints:** a `fix` story, no CAP and no flag; never a
  file the story did not change. Owner `spec-pyforge-marshal`. → Story 83.9, specced 2026-10-03.
- **2026-10-03** — **Found: a session halts on the status a story is minted with.** Story specs are minted at
  `status: 'backlog'` to match their ledger row, and bmad-build-auto does not recognize `backlog`. Claude sessions fell
  through to planning; a Cursor session for 83.5 halted before any work and set the spec `blocked`.
  **What it looks like when fixed:** dispatch hands the session `ready-for-dev` in the worktree copy of a `backlog`
  spec, journaled; the spec on `main` and the ledger are untouched. **Constraints:** a `fix` story, no CAP and no flag;
  bmad-build-auto is installer-owned and stays unedited. Same day (operator ruling): marshal dispatches on Cursor with
  `composer-2.5-fast`, after the Epic 83 campaign landed 1 of 5 stories with the `sonnet` id passed straight through.
  Owner `spec-pyforge-marshal`. → Story 83.8, specced 2026-10-03.
- **2026-10-02 (night, later)** — **Wanted: refresh every harness's model list from its own live source.** The model
  ids in marshal's policies have been refreshed by hand. On 2026-10-02 Cursor no longer listed `grok-4.6`, which four
  station tier maps named, and listed a new `grok-4.7-high`; nothing in marshal could say so. Each harness exposes its
  list differently: Cursor's CLI lists the account's models (`cursor-agent models`, 246 ids on 2026-10-02); Claude Code
  and the Gemini CLI have no listing subcommand, but their APIs do (Anthropic `GET /v1/models`, Gemini `models.list`,
  both paged); the Copilot CLI documents none.
  **What it looks like when fixed:** one operator-run marshal command reads each harness's live list from the source
  its profile declares and writes a dated snapshot of every id it read. It reports each id that a station tier map, the
  price catalog or a harness profile declares and the live list no longer carries, and each id added or removed since
  the last snapshot. A harness whose source cannot be read is reported unavailable with the reason; the others still
  report.
  **Constraints:** operator-run only, never during dispatch or policy load; the listing source is profile data, never a
  per-harness branch (AD-19); no LLM client and no model call; the report is advisory. Operator rulings 2026-10-02: the
  snapshot, not the price catalog, records every live id, and the catalog keeps only priced models; the Gemini and
  Copilot CLIs stay out of the Guild environment for now. Owner `spec-pyforge-marshal`. → CAP-285 / Epic 84 /
  Story 84.1 (FR-232), specced 2026-10-02.
- **2026-10-01 (night)** — **Found: a campaign forgets `--retry-environment-blocks` after its first cycle.**
  `_spawn_campaign_supervisor` hands the detached supervisor the station, the story list, the harness and the in-flight
  cap, but not `retry_environment_blocks`. A campaign launched with the flag skipped 81.1 (an OAuth-refresh race at
  launch, classified an environment block) in its first cycle, then stopped on that same block in its second.
  **What it looks like when fixed:** every supervised cycle of a campaign runs with the flags it was launched with.
  Owner `spec-pyforge-marshal`. → Epic 81 / Story 81.3, specced 2026-10-01.
- **2026-10-01 (evening)** — **Found: Story 73.1's own rule cannot judge a follow-up run in a reused
  worktree, and three dispatch defects surfaced while relaunching it.** 73.1's dispatch implemented the whole
  story, then its review stopped it on an intent gap: `_ensure_dispatch_worktree` reuses a story's surviving
  dispatch worktree, so a follow-up run's baseline can be the pre-merge tip, `<baseline>..origin/main` still
  holds the story's first merge, and the run reads COMPLETED on its first tick, the very bug the story fixes.
  The same misreading sits in four readers outside its named Surface (the CAP-4 land-only retry, the session
  verdict, the drain's block facts, `marshal status`). Separately: a campaign whose only eligible story is held
  by unmet Deps crashed (`'dispatch' is not a valid StationCycleStatus`, latent since 2026-09-01) instead of
  saying so, which hid 73.1's undeclared-in-the-queue dependency on 66.1; and `drain --plan` reported 73.2's own
  feature rule ("Do not dispatch a follow-up whose row is closed…") as a prose park.
  **Operator rulings 2026-10-01:** (1) the launch INTENT records `origin/main`'s tip at launch, and a follow-up
  counts only merges that reach `origin/main` after it; (2) the four readers join Story 73.1; (3) the open row
  id is read from `origin/main`; (4) fix the three defects now.
  **What it looks like when fixed:** a follow-up run is LIVE until its own branch merges, whichever worktree it
  reuses, in every reader; a held wave reports `held` with its unmet Deps; a story's own boundary text is never
  read as a park. Owner `spec-pyforge-marshal`. → CAP-281 amended / Story 73.1 re-specced; Epic 81 / Stories
  81.1, 81.2, specced 2026-10-01.
- **2026-10-01 (later)** — **Found: a dispatch landing never waits for CI.** `main` has no branch protection, and the
  landing policy's `landing_rules` declare only the `maintenance` label and an ungated `linter` check, so a dispatch
  merges as soon as its own session verification passes and every CI lane reports after the merge. Doctor 38.3 merged
  with its `Detectors / scripts-suite` check already failing and reddened `main` (fixed by doctor 38.5); steward 80.1
  merged with Platform CI and Detectors still pending.
  **What it looks like when fixed:** the landing waits, up to a policy timeout, for every check run GitHub reports on
  the PR head; it merges only when all are green, and refuses by name on a red one or at the timeout, leaving the PR
  open to land on a re-run.
  **Constraints:** a pending check is never treated as passing (AD-8); the wait is bounded; `marshal land`'s
  `landing_rules` contract is unchanged. Operator ruling 2026-10-01: gate landings before the follow-up review chain
  runs. Owner `spec-pyforge-marshal`. → CAP-284 / Epic 80 / Story 80.1 (FR-231), specced 2026-10-01.
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
  material is staged in `archive/docs/intake/agentic-sdlc/` (white paper, infographic +
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
  trigger depends on a workspace-management capability (`developer-workspace-management`-shaped)
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

- **2026-09-25 (seed)** — **`verify_scope` is doing exactly its designed job, but this Dream's
  own scope never covered the launch-time gap it creates.** Live incident: a `marshal factory
  dispatch pyforge-marshal 46.9` attempt was correctly refused (`MRS-DISP-041`) while
  `pyforge-steward`'s own chained campaign (59.4→59.5→59.6, continuously live since ~06:24) held
  the shared marker + both symlinks on itself — no silent wrong-project write occurred, which is
  the guarantee this Dream shipped. `BMAD_ACTIVE_PROJECT=pyforge-marshal` was tried as a
  workaround and had **zero effect**: read `_dispatch_scope_refusal`
  (`cli/dispatch.py:278-302`) directly — the env var only catches the *opposite* contradiction
  (env disagreeing with the dispatch target), and when it agrees with the target the code falls
  straight through to the same `verify_scope(repo_root, slug)` physical read regardless. The gap
  this exposes: **there is no sanctioned way to launch a single-story dispatch on station B while
  station A's chain is continuously live**, other than waiting for a gap — even though the
  dispatch's own detached worker doesn't need the shared marker at all once running (per its own
  `--help` text: "launches ... with `BMAD_ACTIVE_PROJECT` per-invocation and physical artifact
  paths"). Re-checked this session's own earlier apparent successes (marshal 46.6 launching while
  steward 59.4 was live, ~06:42): those worked only because the marker happened to already sit on
  the right project at that instant, most plausibly a residual left by that same station's own
  immediately-preceding launch — a timing coincidence surviving because nobody's chain had
  claimed the marker back yet, not a guaranteed capability this Dream (or Story 22.5's
  cross-station allowance) actually promises. **Proposed direction, not yet specced:** since only
  the *launch* step (not the detached worker) ever touches the shared marker, and only briefly,
  `_dispatch_scope_refusal`'s call site could atomically flip-check-launch-restore instead of
  refusing on mismatch — hold a short-lived advisory lock, flip marker + both symlinks to the
  target slug, launch the detached worker (which is already self-sufficient via
  `BMAD_ACTIVE_PROJECT` + physical paths per the existing design), then restore the prior marker
  state immediately after handoff succeeds. This still never lets a *write* land in the wrong
  project — the property this Dream actually guarantees — it just stops requiring the marker to
  already, coincidentally, agree before a launch is even attempted. No CAP minted, no story
  touched.
  **Specced 2026-09-27 — no flip needed.** Read against the code, nothing the launch starts ever
  reads the primary's marker: the session runs in its own fresh dispatch worktree (the marker and
  both links are gitignored, so it has none) with `BMAD_ACTIVE_PROJECT` pinned, which BMAD's
  resolver ranks above any marker, and every launcher read and write is a physical
  `_bmad-output/projects/<slug>/` path. So the scope moves into the worktree — its own marker and
  links, checked by the same `verify_scope`, as `marshal init` already does for a loop home —
  and the shared marker is neither consulted nor flipped. A flip under a lock would repoint every
  primary-checkout writer that does not take the lock (an interactive session, `bmad-switch`) for
  the length of the launch: the wrong-project window this Dream exists to close. A contradicting
  `BMAD_ACTIVE_PROJECT`, or a worktree whose own triangle names another project, still refuses
  `MRS-DISP-041`. → CAP-273 / Epic 64 / Story 64.1
- **2026-09-28 — Proposed: the switch script runs where it is documented to run.** Every document
  names the bare form (`scripts/bmad-switch <slug>`, `scripts/bmad-switch --current`; AGENTS.md, the
  pre-shell hook's `bmad-switch-unsafe` denial, 326 tracked Markdown files, none with an interpreter
  prefix), and its shebang is `#!/usr/bin/env python3`. On this machine that is the system Python
  3.12.3, and `--current` crashes: `_load_verify_scope` first imports `pyforge.marshal.scope`, which
  the system interpreter does not have (`ModuleNotFoundError: No module named 'pyforge'`), then falls
  back to the source tree and imports `scope.py`, whose `except OSError, UnicodeDecodeError:` (line 60)
  is Python 3.14-only syntax — `ruff format` wrote it under the package's py314 target on 2026-09-20.
  `--list` crashes the same way once a marker exists; the switch itself and `--clear` never load the
  primitive and still run. Today the read verbs work only as
  `pixi run -e pyforge-guild python scripts/bmad-switch …`, which no document says.
  **What it looks like when real:** every documented form works on the primary checkout. When the
  primitive will not load, the script runs itself once more under the Guild environment and returns
  that run's exit code. When `pixi` is missing, it prints one line naming the interpreter it ran
  under, what it needs and the exact command, and exits non-zero — never a traceback.
  **Constraints:** `scope.py` stays the one primitive (no local copy, no 3.12 rewrite that the
  formatter would undo); nothing prints before the re-run; a re-run never loops; the switch and
  `--clear` are unchanged. Kinships: CAP-75..CAP-77 (the primitive and its hard fail, Stories 20.6 /
  20.7), CAP-201 (the worktree-aware switch); owner `spec-pyforge-marshal`.

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
[[pyforge-herald|modernist-identity]] (a candidate restyle; today the console has its own
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
  [`marshal-drain-self-resolution.md`](<https://github.com/rxm7706/local-recipes/blob/main/archive/docs/dreams/marshal-drain-self-resolution.md>) archived in place as a
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

- [`marshal-dependency-aware-dispatch.md`](<https://github.com/rxm7706/local-recipes/blob/main/archive/docs/dreams/marshal-dependency-aware-dispatch.md>)
  — ordering (28.12), sanctioned retry (28.13), scope automation (28.14/28.15).
- [`marshal-single-story-dispatch.md`](<https://github.com/rxm7706/local-recipes/blob/main/archive/docs/dreams/marshal-single-story-dispatch.md>) — the
  validated pattern; addendum already named "parallel when surfaces are disjoint"
  as an open Spec question.
- [`horizontal-run-concurrency.md`](<https://github.com/rxm7706/local-recipes/blob/main/archive/docs/dreams/horizontal-run-concurrency.md>) — bmad-loop
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
[`adaptive-model-tiering.md`](<https://github.com/rxm7706/local-recipes/blob/main/archive/docs/dreams/adaptive-model-tiering.md>)), and single-story
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
  [`pixi-candidate-currency.md`](<https://github.com/rxm7706/local-recipes/blob/main/archive/docs/dreams/pixi-candidate-currency.md>)).
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
  [`marshal-dependency-aware-dispatch.md`](<https://github.com/rxm7706/local-recipes/blob/main/archive/docs/dreams/marshal-dependency-aware-dispatch.md>).
- **2026-09-01** — Dispatch-autonomy hotfixes + Epic 28 artifact catch-up (`90c5a28bd6`).
- **2026-09-09** — Code-level verification against `main`: Epic 28's machinery is real
  and complete, and every layer is off — no `[context]` block is declared in any policy,
  repo, project or rendered. Both of § *Gates and open questions*' gates closed against
  the evidence: the measurement-first gate was bypassed (no benchmark artifact exists),
  and the cross-engine question is answered in the negative (the block renders
  identically on both adapters, but only dispatch/build-auto can act on the wire,
  derived-context and planning-graph layers). Recorded as the addendum above, with the
  `realized` guard learned from [`adaptive-model-tiering.md`](<https://github.com/rxm7706/local-recipes/blob/main/archive/docs/dreams/adaptive-model-tiering.md>).
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
  [`adaptive-model-tiering.md`](<https://github.com/rxm7706/local-recipes/blob/main/archive/docs/dreams/adaptive-model-tiering.md>).
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
- **2026-09-24 — Proposed: the stale-blocker leftover — wire and structure-graph still off fleet-wide.**
  Story 28.32 (done, fleet rollout) deliberately rolled out only `derived-context`+`output` to all 8
  stations, leaving `wire`+`structure-graph` declared-off pending two named blockers — Story 28.31
  (the dispatch-worktree provisioning-cost spike) and Story 28.33 (spin reference wiring). Both
  shipped (28.31 on 2026-09-10, 28.33 on 2026-09-20), but nobody returned to finish 28.32's own
  deferred scope. Found 2026-09-24 auditing token-economy state: 7 of 8 stations' `marshal-policy.toml`
  still carry the pre-28.31/28.33 3-of-5 override (`[context."planning-graph"]`/`[context."derived-
  context"]`/`[context.output]`, each just `enabled = true`) — and per `core/policy.py`'s wholesale-
  replace composition (declaring ANY part of `[context]` at station level replaces the entire 5-layer
  default), that partial override silently drops `wire` and `structure-graph` to off for every one of
  those 7 stations, even though the repo-wide default (`policy-defaults.toml`) has both enabled. Only
  `marshal` itself (which declares no override) gets all 5 layers. The fix is mechanical and safe: the
  3 declared blocks are byte-identical no-ops against the repo default, so deleting them (not adding
  two more) lets all 7 stations inherit the clean 5-layer shape — matching `policy-defaults.toml`'s
  own documented guidance ("a station file should declare nothing here to inherit this default
  shape"). Decomposed same day as **Epic 55** / Story 55.1 (hand-driven — a config-only fix, no new
  code path; a new epic because Epic 28 is `done` and a done key never moves).
  This Dream's own guard is unaffected: `status: specified` still holds until a benchmark artifact
  reports a measured saving; this entry closes a leftover deferral, not the measurement gate.

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
  on update instead of hand-patching. Piloted on [[pyforge-herald|design-code-bridge]].
- **The map** — 24 Dreams, no-straggler policy: every shipped surface already
  traces to a Dream; what's missing is the spec layer beneath the realized
  ones ([[packaging-factory]], [[enterprise-airgap]], [[pyforge-herald|modernist-identity]],
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

[[pyforge-charter|pyforge-genesis]] (the operating model this completes — brownfield adoption
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
  [`quick-dev-reconciliation.md`](<https://github.com/rxm7706/local-recipes/blob/main/archive/docs/dreams/quick-dev-reconciliation.md>).
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

## 2026-10-11 — The review bot remembers the correction you gave two weeks ago (folded from marshal-recall-in-the-loop)

*Folded 2026-10-11 under spec-one-chain-per-station CAP-11 (operator ruling 2026-10-11: "Fold into pyforge-marshal
(Recommended)"). The body below is `docs/dreams/marshal-recall-in-the-loop.md`, verbatim, with its headings demoted one
level; the file moved to `archive/docs/dreams/marshal-recall-in-the-loop.md`. Its Spec's four capabilities continue as
`spec-pyforge-marshal` CAP-288..CAP-291 (← `spec-marshal-recall-in-the-loop` CAP-1..CAP-4), and its folder stays as a
pointer. The wiring that makes them live is Story 93.1 (Realization log, 2026-10-11).*

## The review bot remembers the correction you gave two weeks ago

### The Dream

Scribe already captures corrections and feedback (`feedback` / `project` /
`reference` capture types) and can answer a grounded `recall` query — never
inventing an uncited answer, explicit about a real miss. That primitive is
shipped, real, a complete BMAD project.

What it doesn't do yet is reach forward on its own. A correction captured
today doesn't automatically show up in the next `bmad-loop` dev pass working
nearby code, and it doesn't automatically show up in the review pass grading
that work either — both still start from a blank context unless a human (or
this session, by hand) remembers to run `scribe recall` first and paste the
result in. The memory exists; the propagation into every future session that
should see it does not.

This is not identity-scoped citation (that's already real —
[[scribe-marshal-fact-visibility]] lets `recall` cite a project's own
`facts.yaml` under its own scope) and it's not token-compression (that's
[[marshal-token-economy]]'s `derived-context` layer, which recomputes
codebase/planning *structure* when its sources change — a different kind of
staleness than "a human corrected an agent and nobody downstream heard
about it").

### What it looks like when real

- Before a `bmad-loop` dev pass or review pass starts a story, it queries
  `scribe recall` scoped to the story's touched surface/station, and any
  relevant feedback entries fold into that session's starting context
  automatically — no human has to remember to run it.
- Composes with the existing `[context]` pipeline (`wire` / `output` /
  `structure-graph` / `derived-context` / `planning-graph`) as its own layer,
  rather than becoming a sixth ad hoc mechanism bolted on beside it.
- `recall`'s own honesty is preserved end to end: a genuine miss injects
  nothing, never a fabricated "no relevant corrections found" confidence
  the agent didn't earn.
- Stays within the same token-economy discipline the rest of the pipeline
  already answers to — this is a context layer, not an unbounded reread.

### Constraints / Non-goals

- Does not change what scribe *captures* — that surface is already built and
  correct.
- Does not replace human review or lower its bar; it feeds the review pass
  more of what it should already have known, not less scrutiny.
- Not a general RAG-everything layer — scoped to the same
  feedback/correction material scribe already curates, not a blanket
  full-repo retrieval pass.

### Kinships

[[pyforge-marshal]] · [[pyforge-scribe]] · [[marshal-token-economy]] ·
[[scribe-marshal-fact-visibility]]

## 2026-10-12 — REA is one pixi install away — reverse engineering as a local stdio tool

*Appended 2026-10-12 with PR #2168 (recipe `rea-agents` and its REA backends). It was drafted as a standalone
`docs/dreams/rea-integration.md` (`owner: marshal`, `status: dreamt`); under one chain per station (AGENTS.md
pre-PR item 6, `spec-one-chain-per-station`) a marshal-owned aspiration enters as a dated section of the station
Dream instead, so the standalone file never reached main. The body below is that draft, verbatim, with its
headings demoted one level. Status: dreamt; no Spec capability, epic or story is minted yet.*

## REA is one pixi install away — reverse engineering as a local stdio tool

### The Dream

An operator runs `pixi install -e pyforge-foundry-full` in local-recipes and the
`rea` CLI from [REA](https://github.com/morluto/rea) (`rea-agents` on npm, MIT)
is already on PATH. It does not need `npx`, a global npm, or a Node they picked
by hand. One Marshal registration task wires REA's MCP server into the harness
they use (Claude Code, Cursor, Codex, Grok Build), and after a restart they can
ask their agent "trace how X works in this app".

### Shape

- **No sidecar.** REA is a *local stdio MCP server* (`rea mcp`) that the agent
  starts on demand as a short-lived Node process. There is no long-running
  service, port, or database, unlike the DB-GPT or Langflow sidecars. The only
  child processes are the analysis engines it launches locally (for example,
  Ghidra). A container is worth considering later only as a sandbox for runtime
  capture of untrusted targets, and that is Warden's call.
- **Mason: recipe first.** `recipes/rea-agents` repackages the npm tarball
  together with its production `node_modules` and collected third-party
  licenses. It runs on `nodejs >=22.19`. The recipe is per-platform rather than
  noarch because `@lydell/node-pty` ships a native binary that is resolved per
  platform. It goes to SelfExplainML first, then to staged-recipes for
  conda-forge.
- **Opt-in `rea` pixi feature.** This is a small feature that is composed into
  `pyforge-foundry-full` only after the recipe is published. It is not part of
  this Dream's first PR, and pixi.toml/pixi.lock stay untouched until then.
- **Optional backends, also opt-in.** These are pulled from conda-forge where
  they exist (checked with the anaconda.org API on 2026-10-12):
  - Available: `openjdk` (25.0.2), `wabt` (1.0.41), `pwntools` (4.15.0),
    `binwalk` (3.1.0), `mitmproxy` (12.2.3).
  - Not on conda-forge, so they are now **local recipes** in this repo:
    `recipes/ghidra` (12.1.4, official NSA release with `analyzeHeadless`,
    `ghidraRun` and `pyghidraRun` wrappers on `openjdk >=21`),
    `recipes/jadx` (1.5.6, official release on `openjdk >=11`), and
    `recipes/pwndbg` (2026.09.15, on conda-forge `gdb`). pwndbg also needs
    three recipes of its own: `capstone6pwndbg` 8.0.0, `niche-elf` 0.3.6, and
    `gdb-pt-dump` 1.0.0 (the pinned commit). Like `rea-agents`, they go to
    SelfExplainML first and then to staged-recipes.
- **Commercial providers stay operator-supplied.** Hopper, IDA, and JEB are
  never packaged. They are reached only through REA's own environment
  variables, for example `REA_JEB_MCP_URL`.
- **Marshal owns registration.** A task (name to be decided; `guild-register
  rea` is a *proposal*) writes the MCP entry for each harness and copies the
  REA skill. It does not let `rea setup` rewrite agent configs. CI runs a
  readiness smoke check: `rea --help` plus an MCP `initialize` handshake.
- **Warden review before default-on.** Runtime capture executes the target, so
  Warden reviews the capability before the feature is enabled by default.
- **Lawful use.** REA is for software the operator owns or is authorised to
  analyse. The feature docs say so.

### Open questions

1. Should registration live in Marshal's MCP surface, or be a pixi task only?
2. Will staged-recipes accept the binary repackaging of ghidra and jadx, or
   does conda-forge require builds from source (Gradle)?
3. Is the osx-64/osx-arm64 native `node-pty` build covered by the recipe as
   written? So far it has only been verified on linux-64.
- **2026-10-26 (every requirement derives from a capability) — Found:** five marshal requirements cited a Spec Constraint (FR-120, FR-121, FR-125, FR-126; FR-101 beside CAP-15), by the 2026-10-25 rulings for Story 106.1, while A-04, A-05, P-10 and L-01 already carried those Constraints unnamed; the pilot fold (`1e845b55fc`) left 124 Spec titles as `from spec-<old>`, 11 as one letter, 138 bullets as '(see absorbed Spec memlog)' and 280 cut at their first line; none of the 33 lettered NFR lines cites anything; and no harness run carried the rule the way Story 74.3 carries the flag mandate. **Ruled** (2026-10-26, operator, fleet-wide: "yes forbid it" — a requirement cites one or more defined capabilities and nothing else; `spec-one-chain-per-station` CAP-5 as amended, CHAIN-STANDARD § 12; (a) FR-120 ← CAP-14, CAP-15). **For marshal:** the five arrows re-pointed (FR-121 adds CAP-12: `seed adopt` renders templates through `run_copy`); the four ADs name their Constraints; the Spec text restored by script from `1e845b55fc^` with 76 authored titles and one authored success recorded in the memlog for review; the rule carried as `persistent_facts` in `bmad-prd.toml` (new), `bmad-architecture.toml` (new) and `bmad-spec.toml`, and as the `fr-arrow` review lens in `bmad-build.toml`; the NFR backfill minted `backlog` as Story 108.2 (ruling (c)). Epic 108 / Story 108.1, built in the one-PR effort with the other seven stations; no marshal CAP minted.
- **2026-10-26 (planning artifacts outside the one-chain shape) — Found:** five loose `specs/spec-<slug>.md` files sat under the station `specs/` directory that are neither a Spec folder nor a `spec-<E>-<S>-<slug>.md` story spec: `spec-code-audit-remediation-2026-07-26.md` (a 1,617-line Tier-2 Spec of the 2026-07-26 code audit, `status: ready`, its branch abandoned and its waves closed 2026-07-27; the findings live on as deferred-work rows and in the conda-forge-expert v8.81.0 retro) and four story specs that pre-date their ledger keys or never had one: `spec-status-harness-run-id-poisoning.md` (2026-08-15; the ledger record is `spec-39-1-a-null-harness-run-id-recovers-by-filesystem-discovery.md`), `spec-marshal-land-cross-project-story-key-collision.md` (2026-08-15, direct commit `d7fd62707b`; absorbed into the station Spec's scoped-merge-pattern capability and Story 20.8's grammar), `spec-dispatch-tier-routing-fails-safe.md` (2026-09-12, direct commits `6113ac34f2` and `97ca64d1e3`; its Spec folder is absorbed and Story 33.15 superseded its config values) and `spec-land-promote-isolation.md` (`status: in-progress` since 2026-09-02, delivered the same day by `21c29320a9`; Story 68.1 carries the live contract of `commit_paths_onto_remote_tip`). The 2026-10-26 re-audit of the one-chain rule on main `97c8211773` listed all five. **What it looks like when fixed:** each file sits at `archive/<original path>` (`spec-one-chain-per-station` CAP-11; CHAIN-STANDARD § 11), moved by `git mv`, nothing deleted and no text changed except the audit Spec's `status:` (`archived`, reason `superseded`); the station `specs/` directory holds the station Spec, the declared seams, the absorbed folders and `spec-<E>-<S>-<slug>.md` story specs only; the live pointers (the tier-routing Dream's "Story spec:" line, `docs/reference/story-spec-flag-block.md`'s example) follow the move. **Constraints:** a chore under `spec-one-chain-per-station` CAP-11; no CAP, no FR, no AD, no `SPEC.md` change; no story key is minted after the fact for a fix that landed without one; dated records that name the old paths (atlas Epic 10's note of 2026-07-27, steward's 2026-09-14 identifier research, the done story specs) stay as written. Owner `spec-pyforge-marshal`. → Epic 109 / Story 109.1, specced 2026-10-26; built in the same PR with steward 113.1 and warden 21.1.
- **2026-10-26 (every pre-rule runtime capability sits behind a kill switch) — Found:** the flag inventory (doctor Story 34.4, regenerated on the fixed join) reads 37 marshal capabilities minted before the rule date as reachable at runtime with no flag; the operator ruled on 2026-09-28 that every capability ships behind a flag, with one retrofit flag per capability defaulting ON (Q6), and no station had minted its retrofit. **Ruled** (2026-10-26, operator: the CAP-7 retrofit sheet approved as recommended, R1–R8 — flag the unflagged runtime rows only, one key per CAP, an invariant's switch makes the dependent verb refuse, the 90-day clock stands and each station mints its retirement story now). **For marshal:** 37 keys `pyforge.marshal.<capability>` ON in dev, staging and production with their clocks from 2026-10-26, each read through `pyforge.core.flags` at its verb or behaviour site with one two-state test; a flag-off verb stays listed and refuses with the usage code 2 (Q3); no exit code changes. Epic 110 / Stories 110.1–110.37, built in the one-PR retrofit effort; Story 110.38 (the retirement, due 2027-01-24) minted backlog; no marshal CAP minted.

## 2026-10-26 — FR-51's model tiering is fully wired and never turned on (folded from adaptive-model-tiering)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 111.1). The body below is `docs/dreams/adaptive-model-tiering.md`, verbatim, with its headings demoted one level and its 2026-09-16 fold banner left out; the file moved to `archive/docs/dreams/adaptive-model-tiering.md`.*

## FR-51's model tiering is fully wired and never turned on

### The Dream

Every `bmad-loop`-driven dev pass in every loop home runs on the SAME model,
`sonnet`, and every review pass runs on the SAME model, `opus` — a flat,
repo-wide assignment baked into Marshal's own rendered policy template
(`adapters/harness_bmadloop.py:278` `[adapter] model = "sonnet"`, `:290`
`[adapter.review] model = "opus"`, with the comment "review misses ship
false-greens; strongest model where it pays"). That comment states the real
economics: some work is worth the stronger, more expensive model and some
is not. Today Marshal cannot tell the two apart per story — every story
pays the same review cost and gets the same dev capability, whether it is
a one-line doc fix or a foundation story touching six modules.

This is not a missing mechanism. FR-51 ("A story's declared difficulty
selects the model tier without a between-batch config edit",
`prds/prd-pyforge-marshal-2026-07-25/prd.md:769-776`) shipped completely:
`core/policy.py`'s `model_tier_map` field (`:272` default `{}`, `:480-498`
`_valid_model_tier_map`'s validator — `Mapping[difficulty, Mapping[stage in
{dev, review, triage}, model]]`) composes through the same four-layer
precedence as every other policy key. `adapters/harness_bmadloop.py`'s
`render_policy_toml` (`:373-461`) applies FR-51 tier-batching at `:450-459`:
when a `difficulty` is given and present in the map, it writes
`[adapter.<stage>].model` for each mapped stage. Story 6.1 (FR-48/FR-51/
AD-19) closed what its own spec called "the final gap" — nothing resolved
which difficulty a real story declared. `core/spec_difficulty.py` parses a
story spec's `difficulty:` frontmatter; `cli/spin.py::_story_declared_difficulty`
(`:420-474`) reads it per story, `_resolve_governing_difficulty` (`:477-533`)
picks the one difficulty that governs a launch (the harness supports only
run-level model selection, so a mixed batch is never split), and
`_resolve_model_tiering` (`:536+`) resolves per-stage models and writes the
tiered `policy.toml` before `bmad-loop run` is spawned. The whole chain is
real, tested, and wired into `marshal factory spin`.

And nothing has ever fed it. Confirmed by grep across every one of the 8
loop-home projects: zero story specs anywhere declare a `difficulty:`
value. Zero `marshal-policy.toml` files populate `model_tier_map` with a
real entry — every one of the 8 carries the identical placeholder comment
(`_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml:16-23`):
*"`model_tier_map` — it maps DIFFICULTY CLASS to {stage: model} ... the
vocabulary does not exist yet ... Populate when FR-51 tier-batching lands."*
That comment was true when written and has been stale since Story 6.1
shipped (`implementation-readiness-report-2026-08-01.md`) — nobody
revisited it once the vocabulary it was waiting on actually landed. FR-51's
own text anticipated this exact steady state and named it explicitly:
*"Difficulty is read from the story's declaration; an undeclared story
takes the mechanical default."* Every story today is the undeclared case —
by omission, not by decision.

A second, related gap: nothing escalates a model mid-story based on how
the attempt is actually going. `max_dev_attempts` and `max_review_cycles`
are flat ceilings (`core/policy.py` defaults `2`/`3`) regardless of
trajectory — there is no "attempt 1 struggled on sonnet, try attempt 2 on
opus" and no "review keeps finding issues, escalate the review model
further." This is absent on both sides of the seam: Marshal resolves a
tier once per launch, before `bmad-loop run` is ever spawned, never
per-attempt; and the vendored `bmad_loop` 0.9.0 engine itself only couples
`task.attempt` to a budget check (`escalation.py:68`
`budget_left = task.attempt < policy.limits.max_dev_attempts`) — nothing
in the engine re-selects a model based on attempt count. A story that is
visibly struggling pays the same model cost on its last attempt as its
first.

### What it looks like when real

- At least one project's `marshal-policy.toml` carries a real
  `model_tier_map` (real difficulty classes mapped to real per-stage
  models), and at least one story carries a real declared `difficulty:`
  value that measurably changes what `render_policy_toml` writes —
  provable by diffing a rendered `policy.toml` with and without the
  declaration.
- Some convention exists for a story to acquire a difficulty at all —
  authored (a human or `bmad-create-story` names it against a stated
  rubric) or derived (a heuristic over spec size / epic / prior attempt
  history, the same signals FR-14's budget advisory already reasons
  about). Which one is a downstream design decision, not settled here.
- A story that is genuinely struggling — repeated dev attempts, repeated
  review cycles — can get bumped to a stronger model without an operator
  hand-editing the rendered policy mid-run and relaunching. The bump is a
  floor-raise on top of whatever the declared tier already picked, never a
  silent downgrade.
- The run-level batching granularity FR-51 already accepted as v1 behavior
  (one difficulty governs a whole launch; a mismatched story is reported,
  never silently ignored — `upstream-register.json`'s own
  `per-story-model-tiering` entry) is not relitigated here.

### Constraints

- No new tiering *mechanism*. `model_tier_map`'s shape, `render_policy_toml`'s
  tier-batching, and `cli/spin.py`'s difficulty-resolution chain are already
  built and correct — this Dream is about feeding them real data and closing
  the retry-side gap, not rebuilding what Story 6.1 shipped.
- Whatever triggers a retry escalation must be derived from journal/attempt
  facts the fold already accumulates (AD-26), never a new hand-maintained
  flag — the same discipline every other supervisor-facing signal in this
  codebase already follows.
- A model change, declared or escalated, is journaled with the same
  intent/outcome discipline (AD-28) every other supervisor action already
  uses — never a silent substitution an operator has to notice by reading a
  transcript.

### Realization log

- **2026-08-11** — Captured during an investigation into why bmad-loop-driven
  unattended runs cost more and move slower than a single supervised
  `bmad-quick-dev` session, and what Marshal itself could do about it. Direct
  read of `core/policy.py`, `adapters/harness_bmadloop.py`, `cli/spin.py`, and
  `core/spec_difficulty.py` confirmed FR-51's full consumption chain (Story
  6.1) is built, tested, and wired into `marshal factory spin` — the gap is
  purely on the input side. Grep across every loop-home project's
  `marshal-policy.toml` and every story spec under
  `_bmad-output/projects/*/planning-artifacts/specs/*.md` returned zero real
  `model_tier_map` entries and zero `difficulty:` declarations. The retry/
  escalation half was confirmed absent in both Marshal's own code and the
  vendored `bmad_loop==0.9.0` package
  (`.pixi/envs/local-recipes/lib/python3.14/site-packages/bmad_loop/escalation.py:68`).
  No existing FR, story, or `upstream-register.json` entry covers either gap.
  Queued as a Dream rather than patched by hand — `core/policy.py`,
  `adapters/harness_bmadloop.py`, and `cli/spin.py` were deliberately left
  untouched pending the Spec/story chain.
- **2026-08-14** — Realized — decomposed 2026-08-11 as Stories 3.11 (FR-182) and 3.12 (FR-183), both shipped and ledger-done; `marshal-policy.toml` now carries real `model_tier_map` entries. Status flipped and FR-182/183 backfilled into the PRD by the 2026-08-14 dream-backlog chain audit. Residual is operational adoption: stories declaring `difficulty:`.

- **2026-09-09 (fleet readiness pass — operator-approved batch)** — Status kept `realized`; the
  **facts around it are corrected, and CAP-2 is the live gap.** CAP-1 **is fed** since 2026-08-13
  (Story 3.11): 57 story specs across six stations declare a `difficulty:` (marshal 41, atlas 4,
  doctor 4, mason 4, scribe 3, steward 1), `marshal-policy.toml:326-336` and pyforge-atlas's
  `:168-178` carry real `model_tier_map` tables, and two live dispatch journals resolved
  `"model": "composer-2.5-fast"` (marshal 28.24 on 2026-09-02; atlas 21.9 on 2026-09-01) through
  `core/dispatch.py:220-232 resolve_dispatch_model` at `cli/dispatch.py:1400`. The claim that "no
  story declares a `difficulty:` and no project populates a tier map" — carried in this Dream's
  README row and in the Unifying Strategy's realization table — is false as of today.
  **What is genuinely unrealized:** six of eight stations have no tier map and journal `"model":
  null` (verified on mason 13.1, 2026-09-02 and steward 43.6, 2026-09-03), and **CAP-2's
  retry-triggered floor-raise is unreachable** — `cli/spin.py:2268-2277 _apply_retry_escalation`
  fires only in `run_resume`, while `cli/dispatch.py` and `core/dispatch.py` contain no floor-raise
  call at all. `marshal factory dispatch` has been the live engine since ~2026-08-22. Both halves are
  marshal **Story 33.6**. Batch:
  `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`.
- **2026-09-16** — Folded into [[marshal-token-economy]] (operator-ruled token-savings
  consolidation) and archived in place. Prior status: `realized`. The Spec
  (`spec-adaptive-model-tiering`) stays live and remains the contract; the
  narrative continues in the parent's § Fold (2026-09-16).

## 2026-10-26 — Agent portability — BMAD on any agent, never vendor-locked (folded from agent-portability)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 111.1). The body below is `docs/dreams/agent-portability.md`, verbatim, with its headings demoted one level and its 2026-09-16 fold banner left out; the file moved to `archive/docs/dreams/agent-portability.md`.*

> **Superseded 2026-08-02 (dream consolidation).** This practice's concrete, buildable
> decomposition already lives in [`docs/dreams/pyforge-marshal.md`](pyforge-marshal.md) as
> CAP-6 / Epic 6 ("Portability proven, not claimed": skill-tree projection, adapter probe,
> conformance matrix, entry-file drift detection — FR-41..48 in `spec-pyforge-marshal`'s
> real PRD). As a standing practice it does not "end," but its narrative now lives in the
> consolidated Dream rather than a separate document. See `spec-agent-portability` for the
> retirement record.

## Agent portability — the method outlives the tool

### The Dream

Marshal's reach (re-scoped from Herald in the 2026-07-23 ownership review —
Herald keeps the communication face): **the operating model runs on whichever
agent the team uses** —
Devin, GitHub Copilot (and its agents), Claude, Cursor, Gemini — and planning
runs on flat-rate subscriptions instead of metered IDE tokens. The method is
the asset; the agent is a socket. Corollary (the AGENTS.md Portability
contract): the Dream and the neutral Spec are the shared layers; only
decomposition and execution are per-framework — so any framework's build can be
verified against the same oracle.

### What it looks like when real

- A Copilot subscription driven as a local model backend (five bridge patterns:
  `copilot-api`, `litellm`, `copilot-openai-api`, `copilot-api-proxy`, `c2p`).
- A sideload VS Code extension wrapping the bridge, with BMAD-runner +
  multiproject stories backing unattended `bmad-loop` on non-Claude backends.
- The `@bmad` Copilot-Chat adapter upstreamed into the official `bmad-dashboard`
  extension; BMAD web bundles installed as Gemini Gems / Custom GPTs.
- Cross-tool entry files (AGENTS.md → CLAUDE.md / `.cursor/rules` / GEMINI.md /
  copilot-instructions) staying in lockstep — enforced, not hoped.

### What is real

- The copilot-api bridge patterns (`copilot-api`, `litellm`, `copilot-openai-api`,
  `copilot-api-proxy`, `c2p`) — decision tree, auth flows, config. _(The standalone
  reference doc was removed 2026-07-24; the patterns live on in the specs below.)_
- Specs ready: `copilot-bridge-vscode-extension.md` (incl. stories 13–15),
  `bmad-copilot-adapter-upstream.md` (draft — contribution-path decision open).
- The Portability contract landed in AGENTS.md (2026-07-23); the four-pointer
  entry-file family synced the same day.

### Realization log

- **2026-07** — copilot-to-api research consolidated; extension spec waved.
- **2026-07-23** — Dream retro-seeded; named as Herald's "BMAD everywhere"
  responsibility in [[pyforge-charter]].
- **2026-07-23 (gist audit)** — grounding: `docs/intake/gists/awesome-bmad-…/` (the curated BMAD ecosystem list) + `run-bmad-in-microsoft-copilot/` (declarative-agent setup for the 6 web bundles).
- **2026-07-23 (ownership review)** — re-scoped to **Marshal** (alternate
  agents = alternate lines on the same floor); Herald retains docs/comms.

## 2026-10-26 — Agent tool surface — every craft reachable through one governed API (folded from agent-tool-surface)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 111.1). The body below is `docs/dreams/agent-tool-surface.md`, verbatim, with its headings demoted one level and its 2026-09-16 fold banner left out; the file moved to `archive/docs/dreams/agent-tool-surface.md`.*

## Agent tool surface — the factory, callable

### The Dream

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

### What exists

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

### Coverage — measured 2026-07-28, updated 2026-09-12

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

### Enforcement — who ensures no drift

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

### The frontier

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

### Kinships

[[agent-portability]] (the same concern from the agent's side — Marshal's other
half) · [[regenerable-factory]] (a surface that needs hand-registration is not
yet regenerable) · [[packaging-factory]] (Mason's craft, which this surface
exposes — it carried this Dream as a single bullet until 2026-07-25) ·
[[pyforge-atlas]] (Atlas's craft, and the second server) ·
[[enterprise-airgap]] (the surface must resolve behind a firewall too).

### Realization log

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
  project no station owned: four of its five parts already traced to Dreams; this
  was the gap. Assigned to Marshal because the surface is operating-model
  infrastructure, not any one craft.

- **2026-09-09 (fleet readiness pass — operator-approved batch)** — Status kept `realized` (this is a
  `type: practice` Dream); **Q1 is answered and the headline number is corrected.**
  **Q1 — one surface or two? Answer: FEDERATE.** The HTTP station face `POST /stations/<name>/mcp`
  (`django-pyforge/.../mcp_http.py:137`, with auth `mcp_auth.py:1`, rate-limiting `rate_limit.py:3`
  and dual-era routing `mcp_dual_era.py:29,40`) is the one **governed front door**; the stdio servers
  are **local adapters**. The question was stale as posed — it is no longer two surfaces but five
  (`conda_forge_server.py` with 46 `@mcp.tool` decorators, `gemini_server.py`,
  `pyforge/atlas/mcp/server.py`, `pyforge/marshal/mcp/server.py`, and the HTTP transport). Merging
  them re-couples the crafts the Charter deliberately split; leaving them split leaves the surface
  ownerless, which is the failure this Dream exists to name. Federation is what the code already
  implements: the HTTP face is a mount point, not a server.
  **Coverage is 3/6, not 2/6.** Running the gate this Dream asked for
  (`pyforge/marshal/mcp/coverage.py::tool_surface_coverage_report`) returns `{"ratio": "3/6",
  "coverage": 0.5}` — mason, atlas, and **marshal, the owner, no longer at zero** (Story 18.1 /
  FR-153-154). The `type: practice` argument survives the correction; the number does not.
  **Three residuals:** CLI⇄tool parity is gated for `pyforge.marshal.mcp` only
  (`tests/meta/test_cli_tool_parity.py`) — the 46 CFE tools and `pyforge/atlas/mcp/tools.py` are
  ungated, **routed cross-station to mason and atlas**; CAP-4's number is computed but published by
  no pixi task; and `.mcp.json` exists **nowhere** — not at the repo root, not in any of the eight
  loop homes, despite `cli/init.py:447 _render_mcp_json`. Batch:
  `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`.

## 2026-10-26 — A backlog authored before the code existed is a plan for a different codebase (folded from artifact-chain-reconciliation)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 111.1). The body below is `docs/dreams/artifact-chain-reconciliation.md`, verbatim, with its headings demoted one level and its 2026-09-16 fold banner left out; the file moved to `archive/docs/dreams/artifact-chain-reconciliation.md`.*

## A backlog authored before the code existed is a plan for a different codebase

> The semantic sibling of [[surface-drift-reconciliation]]. That Dream made the
> *file-level* reconciliation claim honest — a memlog speaks only for the paths
> it names. This one makes the *meaning-level* claim honest: a story's premise,
> a done-claim's acceptance criteria, a test suite's coverage of an epic. The
> detectors police hashes and counts; nothing polices whether the plan is still
> true. Kin: [[regenerable-factory]] (every surface regenerable from its chain),
> [[fidelity-enforcement]] (every tier boundary gated), [[bmad-output-hygiene]]
> (what is real vs. debris, mapped once — this Dream is that audit's
> forward-looking form).

### The Dream

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

### What is real (measured 2026-08-10, on `main` at `dfeb565231`)

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

### What it looks like when real

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

### The shape of the answer

Five phases, in order. The build stays down throughout; a station's audit
landing gates *that station's* further work, not the fleet's.

0. **Freeze + mechanical debt.** Full detector sweep for the baseline
   inventory. Close the 51 warns as the three jobs they are — atlas 24
   name-then-stamp, mason 1, marshal 26 pending the operator's
   generated-artifacts decision. Disposition the dangling commits. The audit
   is worthless while drowned in known noise.
1. **Backlog-truth audit of the three unfinished stations**, smallest first to
   calibrate the method: **steward (4) → mason (28) → marshal (35 + blocked
   8-5)**. Fresh-eyes read of epics, remaining stories, architecture, and
   context against current code; verdict matrix; done-claim sampling; fixes
   through owning skills; blind review; one landing PR per station.
2. **Completed-station audit at equal rigor** (atlas, doctor, herald, scribe,
   warden). Not a lighter close-out — a critical part and point of the audit:
   three of the four queued decomposition chains extend completed stations, so
   this audit gates decomposition exactly as Phase 1 gates re-spin. Same
   verdict matrix, same sampling discipline, chain columns reconciled, Spec
   statuses corrected to earned values. Atlas's 30 contract-specs are accepted
   as-is, not reconstructed.
3. **Decomposition on the clean base** — the four queued chains, content
   decisions unchanged, each gated on its station's audit.
4. **Re-baseline + resume decision.** `--write-baseline`, `dashboard-gen`,
   board render, fleet-picture; then per-station re-spin is the operator's
   call (FF the home + re-render policy first, per standing procedure).

Why audit-before-decomposition, when the queue said decompose first: the queue
ordering predates the pause decision. Extending atlas's chain now would build
on the very drift this Dream exists to measure. Nothing decided is undecided —
the verification step is inserted, not the decisions reopened.

### Method constraints

- **Detectors own mechanical facts; the audit spends judgment only.** Counts,
  pins, surface hashes, ledger totals come from the instruments that already
  emit them deterministically. Model attention goes exclusively to what no
  script can answer: premises, AC truth, coverage meaning.
- **Anchoring is the audit's failure mode.** An auditor steeped in the chain's
  narrative confirms it. Reading order may be artifacts-then-code, but verdicts
  ground in code, done-claims are sampled cold, and reviewers are blind to
  self-assessments.
- **Prose is not an audit output.** Matrix rows with citations, or nothing.
- Three moves were considered and **rejected** for this repo: bundling all
  artifacts into a single audit document (a satellite doc by construction);
  letting the auditor rewrite planning artifacts freehand (the laundering
  S-13.2 exists to end — rewrites go through owning skills + memlog + scoped
  stamp); and having the model re-derive mechanical drift (slower and less
  reliable than the detectors that already do).

### Non-goals

- **Not a silent re-scoping.** Correction of specs, code, decisions, and
  artifacts is pre-authorized (operator, 2026-08-10) — but every change traces
  to a cited verdict row and lands in a reviewable PR; nothing is dropped or
  rewritten without the record.
- **Not a Tier-C refresh.** Dreams are permanent record; Decks and UX refresh
  through Herald when wanted. Touched only if the audit proves one
  *contradicted*, never for polish.
- **Not a new detector.** The semantic layer cannot be mechanically gated —
  pretending otherwise would mint a false-green instrument, the exact disease
  [[surface-drift-reconciliation]] just cured elsewhere. If a recurring cadence
  is wanted later, that is a separate decision this Dream does not make.
- **Not a reconstruction of atlas's lost originals.** 30/32 contract-specs is
  the accepted end state of that recovery.
- **Not a re-spin.** No station starts building under this Dream.
- **Not a reopening of the four decomposition chains' content decisions.**
  Their order and scope stand; only their start is gated.

### Open questions

- **Marshal's 26 generated-artifact warns** — *answered 2026-08-10:
  regenerate, verify outputs match, then judge + scoped stamp.*
- **Serial or parallel?** — *answered 2026-08-10: serial, in the main session;
  the judgment stays in one context.*
- **Audit order** — *answered 2026-08-10: steward → mason → marshal confirmed.*
- **Can a "complete" station lose the claim?** If Phase-2 sampling fails an AC
  on a shipped station: reopen the story, or record a coverage-debt row and
  leave the ledger? The answer sets precedent for what `done` means here.
- **Where do the gate reports home?** Presumed: each station's own
  `planning-artifacts/` under its existing gate-report class. INV-1 separately
  requires this Dream's own Spec under
  `pyforge-marshal/planning-artifacts/specs/spec-artifact-chain-reconciliation/`.
- **One-shot campaign or standing practice?** If the audit proves cheap enough
  to repeat at every N-story boundary, it may want to become `type: practice` —
  deferred until the first pass prices it.

### Realization log

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

## 2026-10-26 — Artifact console — the factory board, hosted as a chat artifact (folded from artifact-console)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 111.1). The body below is `docs/dreams/artifact-console.md`, verbatim, with its headings demoted one level and its 2026-09-16 fold banner left out; the file moved to `archive/docs/dreams/artifact-console.md`.*

## Artifact console — the first attempt at making the factory legible

### The Dream

One page showing the whole factory at a glance — every project, every story,
what shipped and what is in flight — published as a **claude.ai Artifact**, so
it could be shared with a link and updated conversationally without any repo,
build step, or hosting.

### Why it was archived

**Retired, superseded.** The Artifact was ephemeral in exactly the way a source
of record must not be: it lived outside version control, could not be
regenerated from repo state, and drifted the moment anyone landed a commit. Its
successor — [[factory-console]], now the **Guildhall** — is generated from the
repo by `pyforge.doctor.sources.fleet_scan`, published to GitHub Pages, and governed by
a Spec whose surface check reds when the code moves without the contract. Same
intent, durable substrate.

### Kinships

[[factory-console]] (its successor, realized) · [[regenerable-factory]] (the
principle it violated: everything under a spec it can be rebuilt from).

### Realization log

- **2026-07** — replaced by the GitHub Pages console at
  `https://rxm7706.github.io/local-recipes/`.
- **2026-07-25** — **ARCHIVED (retired)** during the Dream-lifecycle
  reconciliation; formerly a hardcoded console entry with no Dream file behind it.

## 2026-10-26 — PyForge's artifacts, patterns, and station code stay aligned to the installed BMAD era — 6.12 today, v7-ready tomorrow (folded from bmad-611-era-alignment)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 111.1). The body below is `docs/dreams/bmad-611-era-alignment.md`, verbatim, with its headings demoted one level and its 2026-09-16 fold banner left out; the file moved to `archive/docs/dreams/bmad-611-era-alignment.md`.*

## PyForge's artifacts, patterns, and station code stay aligned to the installed BMAD era

### The Dream

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

### Grounding — what was verified (2026-08-22, two research passes + local inventory)

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

#### The 6.12.0 era shift — verified 2026-09-05 (tagged tree + CHANGELOG + local diff, not the release page)

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
   `stop-request.json`, and a mode-exact `graceful_stop_pending` — no marshal
   surface reads stop state today, so there is no CAP-5 gap yet.
9. **The v7 signal is unchanged:** no date, no milestone; the only committed
   breakage is still the shim removal at the v7 cut.

### Whose job this is

**Marshal.** The misaligned surfaces are overwhelmingly marshal's own orbit:
the bmad-loop wrapper and policy chain (AD-16), the status/fleet surfaces, the
seed templates that propagate conventions to new stations, and the factory
docs + SYNC-RUNBOOK that describe the BMAD infra (all live in pyforge-marshal's
planning artifacts). The deferred-work scripts are governed by marshal's
`spec-regenerable-factory`. Detection-side pieces that belong to doctor are
relayed, not absorbed (the split precedent: `bmad-method-version-drift`,
owner doctor). Steward's Epic 14 keeps the *upgrade-apply* half; this Dream is
the *post-upgrade alignment* half — kin, not overlap.

### What it looks like when real

- **No retired skill ID survives in live docs, templates, memory, or code** —
  and a regression guard (the 20-shim list as a meta-test) reds any
  reintroduction between now and the v7 cut.
- **Every spec folder accepts a 6.11 `bmad-spec` update**: all memlogs carry
  frontmatter; memlog-less folders got a genesis-baseline bootstrap.
- **bmad-loop's repo skills match the installed package** after every
  bmad-loop bump (refresh is part of the upgrade verification gate's orbit).
- **Marshal governs the full 0.10/0.11 policy surface** through the four-layer
  chain with deliberate repo defaults, and **speaks the 0.11 status
  vocabulary** (`awaiting-operator` parked runs are named as such everywhere an
  operator looks; `preserve_ref` feeds the escalation-preservation flow).
- **Deferred-work intake reads both sources** (Tier-3 `deferred-work.md` AND
  spec-frontmatter `deferred:` lists), so a hand-driven run's deferrals reach
  the tracked ledger without a human relay.
- **The living factory docs have a named re-grounding owner** and are current
  to 6.11 (plain re-grounding agents per SYNC-RUNBOOK — not waiting on
  upstream's promised-but-unstarted successor capability).

### What is real

**The 6.11 round — all of it (marshal Epic 25, 7/7 done 2026-08-24).** The
retired-ID guard (`test_no_retired_bmad_skill_ids.py`) reds a planted ID; the
three bmad-loop skills were refreshed to 0.11.0; all 22 spec folders accept a
6.11 `bmad-spec` update; the five 0.10/0.11 policy knobs flow through the
AD-16 chain; `marshal status` / fleet-picture speak `awaiting-operator` /
`preserve_ref` / `sweeps_refused` (PR #612); hand-driven deferrals reach the
tracked ledger (PR #721); the living docs were re-grounded with marshal as
the named owner (PR #722). DW-BL011-1/-2 closed with it.

**The 6.12 round — nothing yet.** Every item in § *The 6.12.0 era shift* is
open: the guard still lists the 6.11 shim roster, the rulebooks still have
consumers, CLAUDE.md still points at the dead URL, and the apply itself
waits on the operator (steward Epic 14).

### Constraints

- **Do not adopt what upstream is removing**: no `stories.yaml`, no folder+id
  dispatch, no `{spec-folder}/stories/` migration — the epic-story path is the
  surviving v6 route and v7's build-auto keeps it (V7-10).
- **The AGENTS.md HOLD is lifted (2026-09-05).** The managed `bmad:context`
  block has been live since 2026-09-04 and 6.12's `adopt` intent is the
  rework this Dream waited out; `bmad-project-context audit` is the
  post-upgrade step, and the eight station `project-context.md` rulebooks
  follow D1 — retire, with every consumer migrated first; never leave a file
  nothing loads.
- **Watch, don't build, for the unscheduled**: the TOML cutover and the
  bmad-ticket tree get named triggers (below), not code.
- Retired-name sweeps annotate historical/narrative text with the new name
  rather than rewriting history (a shipped spec's story text may keep its
  original wording with a gloss).
- Shims stay installed through the v7 cut (upstream's own rule). The guard is
  green, so the pre-sweep bar is met, but every apply still passes `--shims`
  explicitly — 6.12 made them opt-in on fresh installs; clones of this repo
  inherit the tracked `.claude/skills/`, so that default bites only a NEW
  repo's `npx bmad-method install`.

### Non-goals

- The **bmad-ticket tracking adapter** — its own future marshal Dream, trigger:
  bmad-ticket lands in a tagged release (sprint feeds, ledgers, promote,
  story-status, fleet-picture, dashboard all ride sprint-status.yaml and stay
  as-is until then).
- The **TOML-cutover symlink migration** — steward Epic 14's watch (CAP-1 must
  flag the cutover release; the named consequence lands in that spec's
  failure-modes).
- **TEA module install / tea-test-review CI gate** — optional adoption, not
  alignment; the repo-custom `bmad_tea_playwright.py` generator stays.
- Upgrading bmad-method/suite versions themselves (steward Epic 14) and
  detecting they're behind (doctor Epic 14 — both shipped or in chain).
- Paige replacement, "explain this system" — zero upstream implementation
  signal; nothing to align to. (The bmad-ux/WDS half resolved: 6.12's module
  registry marks WDS deprecated, folded into `bmad-ux`, and the suite retired
  it 2026-09-05 — see [[bmad-suite-channel-product]].)

### Kinships

[[bmad-method-core-upgrade]] (steward — the apply half; this Dream begins where
an applied upgrade ends) · [[bmad-method-version-drift]] (doctor — the ambient
detection half, incl. CAP-4 suite coverage) · marshal DW-BL011-1/-2 (the two
pre-filed gaps this Dream's chain absorbs) · [[bmad-loop-liveness-footgun]] /
marshal Epic 24 (status-truthfulness kin — the 0.11 vocabulary work sits beside
it) · `_bmad-output/projects/pyforge-marshal/SYNC-RUNBOOK.md` (the reconciler
loop whose 6.11 gaps item 5 closes) · [[bmad-suite-channel-product]] (steward —
the suite side of the same era shift; its roster moved 2026-09-05).

### Realization log

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

## 2026-10-26 — BMAD from inside Cursor's own chat — interactive routing, not just headless dispatch (folded from bmad-cursor-interactive-routing)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 111.1). The body below is `docs/dreams/bmad-cursor-interactive-routing.md`, verbatim, with its headings demoted one level and its 2026-09-16 fold banner left out; the file moved to `archive/docs/dreams/bmad-cursor-interactive-routing.md`.*

## BMAD from inside Cursor's own chat — interactive routing, not just headless dispatch

### The Dream

"Portable to Cursor" is already solved for exactly one shape: headless, unattended dispatch.
`marshal factory dispatch` / `bmad-loop` already drive `cursor-agent -p --trust --workspace <dir>
--model <m> <prompt>` (Story 22.8, FR-193, CAP-8), verified live 2026-08-27, and it is the fleet's
*current active* `harness_preference` for both pyforge-marshal and pyforge-atlas today. Nobody has
proven the other shape: a human sitting inside Cursor's own IDE chat panel, invoking a BMAD skill
the way we invoke `bmad-build` inside Claude Code's chat right now, and getting the same
disciplined workflow back — skill discovery, the `render_skill.py` → `workflow.md` trigger, and
(for `bmad-build-auto`) the mandatory context-free reviewer subagents (Blind Hunter, Edge Case
Hunter, verification-gap, intent-alignment) that this repo's own `workflow.md` HALTs
`blocked`/`no subagents` without.

The dream: BMAD skills are reachable from Cursor's own interactive chat — not only its headless
CLI dispatch path — with the same review discipline, so a human working in Cursor gets the
identical guaranteed rigor a human working in Claude Code gets. The choice of IDE stops being a
choice about workflow quality.

### Grounding — verified state (2026-09-06)

- Every BMAD `SKILL.md` (`.claude/skills/bmad-*/SKILL.md`) is a two-line trigger: run
  `uv run _bmad/scripts/render_skill.py --project-root … --skill …`, then read and follow the
  printed `workflow.md`. The rendered workflow bodies themselves (grepped across
  `_bmad/render/bmad-build*/`) contain zero references to Claude-Code tool names (`Task tool`,
  `Agent tool`, `subagent_type`, `Skill tool`, `ScheduleWakeup`) — the prose is already
  agent-neutral ("Subagents, when the capability is available…").
- `bmad-build-auto`'s `workflow.md` / `step-04-review.md` are not neutral about the *capability*,
  only the *vendor*: "Using subagents when instructed is mandatory. If you cannot, HALT with status
  `blocked` and blocking condition `no subagents`." Each reviewer (Blind Hunter, Edge Case Hunter,
  verification-gap, intent-alignment) is launched as "a context-free subagent."
- The headless path already proves the capability works *through `cursor-agent`*:
  `harness_preference = ["cursor"]` is the live setting in both
  `pyforge-marshal/planning-artifacts/marshal-policy.toml` and pyforge-atlas's, with
  `model_tier_map` routing dev to `composer-2.5-fast` and review to `composer-2.5`
  (`data/harness_profiles/cursor.toml`, verified live 2026-08-27). That proves `cursor-agent -p
  --trust` headless mode's subagent tool works — it does **not** prove Cursor's own interactive IDE
  chat surface (the panel a human types into) exposes the same tool to the model running there. No
  evidence either way was found in-repo.
- `AGENTS.md` names Cursor as a sanctioned framework and `.cursor/rules/specs.mdc` exists as the
  cross-tool Tier pointer, but there is exactly one `.cursor/rules/*.mdc` file in the repo — none
  per-skill. Cursor's nearest analog to Claude Code's description-matched `Skill` tool is an "Agent
  Requested" rule (a `.mdc` carrying a `description` the agent can pull in on its own judgment) —
  mechanically derivable from the existing `SKILL.md` frontmatter + trigger body, but nothing
  generates it yet.
- Auto-memory (`~/.claude/projects/<encoded-path>/memory/`) and `CLAUDE.md`'s
  `@.claude/memory/MEMORY.md` inline-import are Claude-Code-loader-specific; Cursor rules do not
  resolve the same `@path` import syntax at load time.

### What it looks like when real

- A `.cursor/rules/*.mdc` file per BMAD skill (or one generated router), mechanically derived from
  `.claude/skills/bmad-*/SKILL.md`'s frontmatter (`name`, `description`) and its two-step trigger
  body, so an equivalent request typed into Cursor's chat surfaces and runs the same
  `render_skill.py → workflow.md` path Claude Code runs.
- A live probe, run once, that settles the open question directly: from inside Cursor's
  interactive IDE chat (not `cursor-agent -p` headless), can the running model invoke a genuine
  context-free subagent and get a synchronous result back in the same turn? A cheap probe modeled
  on the Blind Hunter prompt shape (fixed diff in, "launch a context-free subagent that reviews
  CONTENT" instruction, real output back) is enough to answer it either way.
- If the probe succeeds: `.mdc` routing is the whole gap, and `bmad-build`/`bmad-build-auto` run
  inside Cursor's chat with full parity to Claude Code — no quality degradation.
- If the probe fails: the workflow HALTs `blocked`/`no subagents` exactly as designed rather than
  silently skipping the review it depends on, and the honest fallback gets documented (e.g., route
  `bmad-build-auto`'s review step through the already-verified headless `cursor-agent -p` dispatch
  as the "subagent," or restrict Cursor's interactive chat to skills that don't mandate one).
- Team-memory (`.claude/memory/`) reachable from Cursor chat via whatever reference mechanism
  Cursor actually resolves at load time — verified, not assumed.

### What is real

Nothing built yet for the interactive path. This Dream is the seed; the finding that triggered it
is the 2026-09-06 conversation establishing that headless dispatch (CAP-6 / Story 22.8) is already
solved and live, and that the interactive-chat shape is a distinct, unverified surface.

### Constraints

- Do not re-litigate or duplicate CAP-6 / Epic 6 ([`pyforge-marshal.md`](pyforge-marshal.md)) — that
  Dream already owns "portability proven, not claimed" for the headless/dispatch shape (Story 22.8
  is done). This Dream is scoped to the *interactive-chat* shape only.
- The probe must be live and empirical — no assuming Cursor's interactive chat has the headless
  CLI's subagent support just because the CLI does.
- `.mdc` generation, if built, stays a mechanical derivation from the existing `SKILL.md` files
  (single source of truth), never a hand-maintained fork that can drift.

### Non-goals

- Rebuilding or replacing the already-verified headless `cursor-agent` dispatch path (Story 22.8) —
  this Dream is additive to it, not a redo.
- Day-one parity for all ~90 BMAD skills; the pilot only needs `bmad-build` (no subagent
  requirement) and `bmad-build-auto` (has the requirement) to answer the real question.
- Porting Claude Code's auto-memory harness feature itself; only confirming team-memory content is
  reachable in whatever form Cursor natively supports.

### Kinships

- [`pyforge-marshal.md`](pyforge-marshal.md) — CAP-6 / Epic 6, the realized headless-dispatch
  portability capability this Dream extends into the interactive surface.
- [`agent-portability.md`](<https://github.com/rxm7706/local-recipes/blob/main/archive/docs/dreams/agent-portability.md>) — archived/absorbed into pyforge-marshal; this
  Dream is a fresh satellite for the one gap that absorption didn't cover.

### Realization log

- **2026-09-06** — Seeded from a conversation auditing what "portable to Cursor" would require.
  Finding: the unattended/headless path (`marshal factory dispatch` / `bmad-loop` via
  `cursor-agent -p`, Story 22.8, CAP-6) is already built, verified live 2026-08-27, and is the
  fleet's *current active* `harness_preference` for pyforge-marshal and pyforge-atlas. The gap is
  narrower than first assumed: (1) a mechanical `.mdc` routing layer so Cursor's own interactive
  chat can trigger BMAD skills the way Claude Code's `Skill` tool does, and (2) an unverified
  empirical question — whether Cursor's interactive IDE chat surface (not the headless CLI) can
  spawn a context-free subagent, which `bmad-build-auto`'s review step mandates. Next: run the live
  subagent probe from inside Cursor's chat before building any `.mdc` routing.

- **2026-09-09 (fleet readiness pass — operator-approved batch)** — **`dreamt` → `specified`.** All
  four of the Spec's open questions were answered by the operator, which is the condition
  `spec-bmad-cursor-interactive-routing`'s `draft` status recorded ("nothing chosen yet: CAP-1 gates
  every other CAP"); the Spec moves `draft` → `ready`. The chosen shape:
  **OQ-1** — run the live subagent probe, and **plan for a NO**: the headless profile that works is
  `cursor-agent -p --trust --force` (a one-shot where the agent owns the whole turn), while Cursor's
  interactive chat is a human-in-the-loop editor session whose parallel-agent features are
  session-level fan-out of the *same* prompt. Budget one session; treat CAP-3 as the likely branch.
  **OQ-2** — on a failed probe take **CAP-3b** (allowlist skills that mandate no subagent) now, and
  name CAP-3a a follow-on; a shelled-out `cursor-agent -p` "subagent" is the same class of substitute
  reviewer this estate was burned by twice.
  **OQ-3** — `.mdc` generation is a **maintained pixi task plus a drift detector**, never a one-time
  script (a one-time run *becomes* the hand-maintained fork this Dream's Constraint forbids).
  **OQ-4** — assume **no inline-import analog** to Claude Code's `@path`; carry team memory by
  `alwaysApply` rule content plus explicit `@file` attachment, and verify it in the same probe
  session. The Spec stays registered in doctor's `DEFERRED_SPECS` (a `ready` Spec *is* in
  `OPEN_SPEC_STATUSES`, so the exemption is live) until the probe runs and decomposition begins.
  Batch:
  `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`.

- **2026-09-15 (CAP-1 probe)** — Ran from Cursor Agent interactive chat (not
  `cursor-agent -p`, not a tool-less Ask panel). The running model invoked the Task
  tool twice: (1) Blind-Hunter-shaped review of `add`/`return a-b`, token `HUNT7K2Q`
  back in-turn; (2) clean leak check, `PARENT_USER_QUERY=UNKNOWN`. **PASS.** The
  2026-09-09 "same-prompt fan-out only" prediction did not hold for Agent+Task.
  CAP-2 is committed (mechanical `.mdc` + pixi task + drift detector for
  `bmad-build` / `bmad-build-auto`). CAP-3b remains the residual HALT on a no-Task
  surface; CAP-3a stays a later empty follow-on. CAP-4 verified: `Read` of
  `.claude/memory/MEMORY.md` works; no `@path` inline import. Leaves
  `DEFERRED_SPECS`. Dispatch home: marshal Epic 45. Dream stays `specified` until
  that epic ships.
- **2026-09-16** — Folded into [[marshal-token-economy]] (operator-ruled token-savings
  consolidation) and archived in place. Prior status: `specified`. The Spec
  (`spec-bmad-cursor-interactive-routing`) stays live and remains the contract;
  the narrative continues in the parent's § Fold (2026-09-16). The Dream's own
  "stays `specified` until Epic 45 ships" note is preserved by the Spec's
  status, not this file's.

## 2026-10-26 — A story's orchestrator-recorded baseline can never drift out from under its own worktree (folded from bmad-loop-baseline-drift)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 111.1). The body below is `docs/dreams/bmad-loop-baseline-drift.md`, verbatim, with its headings demoted one level and its 2026-09-16 fold banner left out; the file moved to `archive/docs/dreams/bmad-loop-baseline-drift.md`.*

## A story's orchestrator-recorded baseline can never drift out from under its own worktree

### The Dream

`bmad-loop` mounts each story in its own isolated git worktree and records `task.baseline_commit`
once, when that worktree opens — engine.py's own comment says it is meant to stay "fixed across
the whole dev retry loop." In practice it can silently drift to a later commit while a dev session
is still running, so a story that does completely real, reviewed, honest work gets permanently
rejected by its own verify gate (`spec baseline ... does not match orchestrator-recorded
baseline ...`) and deferred — with the run then dispatching the *next* story rather than pausing
or escalating. The dream is a fix (or, short of that, a durable containment) that makes this class
of failure impossible, or at minimum loud and self-healing, instead of silently burning hours of
real compute per occurrence.

### What it looks like when real

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

### What is real

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

### Constraints

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

### Non-goals

- **Not a rewrite of `bmad-loop`'s concurrency/worktree model.** The dream is the narrow baseline-
  drift bug, not a broader redesign of how the orchestrator manages parallel worker slots against
  one shared target branch.
- **Not retroactive cleanup of past occurrences.** The three known occurrences this session
  (8.1-9.5, 9.6, mason 3.6/3.7/3.9) are already recovered (PRs #482, #483, #484); this Dream is
  about preventing/containing the NEXT one.

### Backlog: what's needed to report this upstream

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
4. **Minimal repro, if requested** — still open. The three live occurrences are entangled with
   this repo's multi-worktree fleet; an upstream-friendly minimal repro does not exist yet.
5. **Decide the interim mitigation independent of upstream's timeline** — in progress in-repo
   (Stories 20.1–20.2 shipped loud-defer containment; 20.4+ own intent-gap preservation). Never
   edit the installed `bmad_loop` package.

#### Filed issue (was DRAFT — filed 2026-08-23)

**Upstream:** https://github.com/bmad-code-org/bmad-loop/issues/701

Prepared 2026-08-14; filed 2026-08-23 after gates 1–2 cleared (Story 20.3). Coordinated body also
carries Story 10.1 intent-gap evidence on the shared report path. Historical draft text retained
below for the paper trail:

> **Title:** `task.baseline_commit` can drift to a later commit while a story's dev session is
> still running, permanently failing its own verify gate
>
> **Body:**
>
> ### Summary
>
> A story's isolated-worktree `task.baseline_commit` is meant to stay fixed for its whole dev-retry
> loop (the comment at `engine.py` around line 1229 says so explicitly), captured once via
> `verify.rev_parse_head(self.workspace.root)` when the worktree opens (`engine.py:1707`). We
> observed it change to a *later* commit — the shared target branch's tip, many stories ahead —
> while a dev session was still mid-flight, with the story's own worktree never having moved.
> `_verify_shared_gates` (`verify.py:1211-1235`) then compares the dev session's own (correct)
> `baseline_revision` against the drifted `task.baseline_commit`, finds a mismatch, and the story
> is permanently deferred (`spec baseline ... does not match orchestrator-recorded baseline ...`)
> even though the completed attempt did real, reviewed, honest work. The run then dispatches the
> *next* story rather than pausing or escalating, so the failure is silent until an operator
> notices via other means.
>
> ### Evidence (one occurrence, full journal timeline)
>
> Run `20260813-094919-bfcb`, story `9-6-plan-and-action-types-repo-fingerprint-and-the-plan-builder`,
> `journal.jsonl`:
>
> ```
> worktree-opened      story=9-6  (branch/worktree created — baseline should be ~523e938c79 here)
> dev-decision  attempt=1  session_status=timeout  action=retry
> rollback-auto         baseline=26102ea12c6d...   <-- ALREADY drifted, ~3h after worktree-opened
> attempt-commits-preserved  ref=attempt-preserve/...-523e938c  count=124
> dev-decision  attempt=2  session_status=completed  action=defer
>   reason="spec baseline 523e938c7978 does not match orchestrator-recorded baseline 26102ea12c6d"
> story-deferred  reason=(same)
> worktree-opened  story=10-1  (dispatcher moves on)
> ```
>
> The worktree's own preserve-ref name (`attempt-preserve/20260813-094919-bfcb-523e938c`) confirms
> its real basis never moved past `523e938c79`. `task.baseline_commit` was already the later commit
> by the time `rollback-auto` fired after attempt 1's timeout — i.e. it drifted *during* attempt 1,
> not at any point our own code touched. Between those two commits, the shared target branch
> (`loop/pyforge-marshal`) had several sibling stories land (an operator-driven out-of-band
> recovery in our case, but plausibly any concurrent landing on the same branch).
>
> ### What we found in the source (`bmad-loop` 0.9.0)
>
> - `engine.py:1707` (`_dev_phase`) sets `task.baseline_commit` exactly once per dev-phase
>   invocation, from `self.workspace.root`'s HEAD — which is the per-story isolated worktree
>   (`self.workspace = unit.workspace` at `engine.py:622`, set before `drive()` runs). We could
>   not find, via static reading, the exact call site that overwrites it again mid-flight for an
>   already-open worktree; happy to help narrow this down further if useful.
> - `runs.py:872-908` (the operator-driven `resolve`/re-arm path) already handles an equivalent
>   hazard explicitly: it re-stamps BOTH `task.baseline_commit` (from `state.project`'s live HEAD)
>   AND the spec's `baseline_revision` together, with a comment naming precisely this failure
>   ("without this, the re-driven step-04 would build its review diff... clawing back the very
>   resolve-session commits the advance above just blessed"). This suggests the maintainers are
>   already aware of the *shape* of this problem for the re-arm path; we couldn't find the
>   equivalent protection on the automatic retry path.
> - `verify.py:1220-1235`'s `allow_ancestor_baseline` carve-out already treats an *ancestor*
>   baseline as sound for one specific case (#161, deferred-work-bundle re-arm). Extending that
>   carve-out (or an equivalent) to the plain-retry path looks like it would fix or at least
>   contain this.
>
> ### Impact
>
> Three occurrences in one session across two different projects (9 stories, ~8 hours; then this
> one story; then 3 more stories in a sibling project) — each required manual git archaeology
> (`attempt-preserve/*` branches, `failed/*/changes.patch`) to recover, since `scm.keep_failed`'s
> safety net preserved the work but nothing in the automatic path re-lands it.
>
> ### Environment
>
> `bmad-loop 0.9.0`, multi-worktree isolated mode, `branch_per` targeting a single shared
> `loop/<project>` branch across concurrently-scheduled stories.

### Kinships

[[pyforge-marshal]] (the estate; owns `bmad-loop` adoption per `docs/specs/bmad-loop-adoption.md`) ·
`spec-pyforge-marshal`'s `.memlog.md` (full per-occurrence journal evidence and code citations,
recorded during the 2026-08-14 recovery of 8.1-9.5, 9.6, and — via the mason project's own memlog —
3.6/3.7/3.9)

### Realization log

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

## 2026-10-26 — bmad-loop can't see a story's own documented dependency (folded from bmad-loop-forward-dependency-blindness)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 111.1). The body below is `docs/dreams/bmad-loop-forward-dependency-blindness.md`, verbatim, with its headings demoted one level; the file moved to `archive/docs/dreams/bmad-loop-forward-dependency-blindness.md`.*

## bmad-loop can't see a story's own documented dependency

### The Dream

`bmad-loop`'s picker (`next_actionable` in `bmad_loop/sprintstatus.py`, called
from `engine.py`'s `_pick_next`) is a strict file-order scan within the current
epic. It has no `depends_on` concept at all — confirmed directly against the
installed library source. Every station's `epics.md` can document a real
per-story dependency via a `**Deps:** S-X.Y` field, but the engine only ever
reads a story's status in `sprint-status.yaml` (`backlog` / `ready-for-dev` /
`in-progress` / `review` / `done`). When a story's own documented dependency
lives in a *later* epic than the story itself, the engine cannot tell — it
will dispatch that story the moment its own epic's earlier stories clear, and
burn a real dev attempt (and up to `max_review_cycles` review passes) on work
that structurally cannot complete yet.

Found 2026-08-03 while setting Marshal up to run its backlog unattended.
Marshal's own `epics.md` had *already* documented the dependency for two
stories (2.3 → S-3.2, one with a full explanatory paragraph; 2.7 → S-4.1) —
the information existed, it just never reached the one file the engine
actually reads. A third forward-dependency (8.5 → S-10.2) turned up in the
absorbed genesis-installer epics (7-12) on a full sweep of every story's
`**Deps:**` field.

This Dream exists so the gap gets closed **once**, for every station, and
stays closed: a mechanical fix per station is a one-time patch; a permanent
detector is what stops it recurring the next time someone adds a story whose
dependency happens to live in a later epic.

### What it looks like when real

- Every station's `epics.md`-family document has been swept for forward-epic
  `**Deps:**` references (a story naming a dependency in a later epic than its
  own).
- Every finding has its story's status set to a non-actionable, non-standard
  value (`blocked`) in both the loop-home's live Tier-3 feed and the tracked
  `sprint-status-ledger.yaml` twin — confirmed safe: `bmad_loop.sprintstatus
  .load()` does not validate `status` against its own declared
  `STORY_STATUSES` enum, so `ACTIONABLE_STATUSES = {"backlog", "ready-for-dev"}`
  naturally excludes it. Same mechanism the pre-existing `optional`
  retrospective status already relies on.
- A permanent detector (`scripts/*_check.py`, self-registered via the existing
  `scripts/detectors.py` registry) scans every station's structured epics doc
  for forward-epic `**Deps:**`, cross-checks each against the tracked ledger,
  and fails if a forward-dependent story is still `backlog`/`ready-for-dev` —
  so adding a new story with a forward dependency later, and forgetting to
  mark it, is caught in CI rather than discovered by a run burning compute on
  it.
- Stations whose `epics.md` uses an older narrative format with no structured
  `**Deps:**` field (confirmed: `pyforge-warden`) are reported by the detector
  as **not determinable from this format**, never silently passed as clean —
  this repo's own fidelity-enforcement doctrine (never claim green you didn't
  measure) applies here exactly as it does everywhere else.
- Flipping a `blocked` story back to `backlog` once its real dependency lands
  is a one-line edit, not a rediscovery — the PROJECT NOTES comment at the top
  of each affected `sprint-status.yaml` names exactly which dependency to
  watch for.

### What is real

- Marshal fixed: `2-3-frozen-surface-scope-check-narrowing-only` (deps
  `S-3.2`), `2-7-a-gate-binds-to-the-specs-success-signal` (deps `S-4.1`), and
  `8-5-marker-deletion-as-a-sanctioned-opt-out` (deps `S-10.2`, in the absorbed
  genesis-installer epics 7-12) — all three set `blocked` in the loop-home's
  live feed and promoted to the tracked ledger. Verified directly against the
  library: `next_actionable(epic=2)` now correctly returns 2.4, skipping both
  Epic-2 findings. `2-3`/`2-7` shipped in PR #237; `8-5` applied the same
  session, not yet in a PR at the time this Dream was captured.
- A full sweep of marshal's own two epics files (`epics.md`,
  `epics-genesis-installer.md`) confirmed these are the *only* three forward
  dependencies across all 12 epics / 86 stories — every other `**Deps:**`
  reference stays within-epic-or-earlier.
- **Cross-station audit complete: zero additional forward dependencies.** A
  research pass read every other station's epics doc(s) directly. Two are
  structured enough to carry a mechanical Deps field (atlas: `**Depends on:**`
  under an alias-first heading `### Story A1 (2.1):`, not marshal's plain
  `### Story 2.1:` shape; mason's `epics-presenton-pixi-image.md` satellite:
  marshal's exact shape) and both are clean. The other five (doctor, herald,
  mason's own main `epics.md`, scribe, steward, warden) use a narrative format
  with marshal-shaped `### Story E.N:` headings but **no Deps field of any
  kind** — several of those documents even self-validate in their own closing
  prose that no forward dependency exists ("no story depends on a future
  story within its own epic", scribe; "no forward dependencies", steward).
  Confirmed unmeasurable mechanically either way — marshal was the only
  station actually carrying the bug.
- **The permanent detector is built, tested, and passing**:
  `scripts/forward_dependency_check.py` (pixi task
  `forward-dependency-check`), self-registered via `scripts/detectors.py`.
  Imports `ACTIONABLE_STATUSES` from the installed `bmad_loop.sprintstatus`
  module rather than restating it. Extracts each story's own block (heading to
  next heading) and searches within it for the Deps field, rather than
  anchoring to a line start — the field routinely shares a line with
  `**Type:**`/`**Effort:**`. A station only counts as "measured" if at least
  one real Deps field was found anywhere in its epics doc(s); a station with
  headings but zero Deps fields (doctor/scribe/steward/warden/mason's main
  doc) reports as unmeasured rather than a false "0 findings" — caught as a
  real bug in the detector's own first draft before this Dream closed. Current
  live output: 2 stations measured (marshal, mason) clean, 6 unmeasured
  (atlas, doctor, herald, scribe, steward, warden), 0 findings, exit 0.
- Two unrelated findings surfaced by the audit, out of this Dream's scope,
  left for a separate decision: herald's live `planning-artifacts/epics.md`
  describes a different, undocumented "deck bridge" effort than what the
  tracked ledger actually drives — reading `epics.md` doesn't tell you what
  herald is building. Mason's `epics-presenton-pixi-image.md` satellite and
  doctor's newly-added Epic 4 are both absent from their tracked
  sprint-status ledgers (currency gaps, not correctness bugs).

### Constraints

- Never touch `.memlog.md` history or `archive/` content.
- The `blocked` status value is deliberately outside `STORY_STATUSES` — do not
  add it to that enum upstream in `bmad_loop` even if a PR opportunity arises;
  this repo does not vendor or patch `bmad-loop` (a declared, pinned runtime
  dependency), and inventing a status the engine doesn't formally recognize is
  the *workaround*, not a request to change the library's contract.
- A station whose epics format can't be mechanically parsed must be reported
  as unmeasured, never silently treated as "0 findings = clean."

### Non-goals

- Not a request to add `depends_on` to `bmad-loop` itself — that fix belongs
  upstream, and this repo's stance elsewhere (`scripts/story_status_check.py`'s
  own docstring) is explicit that known-upstream defects get *contained*
  locally, not patched in a vendored fork.
- Not re-litigating whether forward dependencies should exist in the epics
  structure at all — some are legitimate (a fold/aggregation step genuinely
  needs to land before a consumer can be built); the fix is making the engine
  aware of the ones that do, not restructuring epics to avoid them.

### Realization log

- **2026-08-03** — Captured after finding and fixing 3 instances in marshal
  (2.3, 2.7, 8.5) while preparing to run marshal's backlog unattended. Cross-
  station audit and the permanent detector are in progress in the same
  session; user asked explicitly for this to be recorded as a Dream and fixed
  across every station, not just marshal.
- **2026-08-03** — Realized. Cross-station audit found zero additional forward
  dependencies (marshal was the only affected station); the permanent
  detector (`scripts/forward_dependency_check.py`) is built, registered, and
  passing (2 stations measured clean, 6 correctly reported unmeasured, 0
  findings). The detector itself caught a real bug in its own first draft
  before landing — a station with headings but no Deps field would have
  silently counted as "measured, 0 findings" instead of unmeasured, the exact
  false-green class this Dream exists to prevent.
- **2026-08-03** — First real unblock: S-3.2 landed, so `2-3` was flipped
  back to `backlog` (its own dep is now satisfied) — exactly the mechanism
  this Dream designed for. Noted a known detector limitation surfaced by
  this: `forward_dependency_check.py` flags `2-3` as a finding again
  immediately after the correct unblock, because it only checks "is this
  story's status non-actionable," not "has its declared dependency actually
  landed." Not a bug in the unblock — a real enhancement opportunity for the
  detector (check the dependency story's own status, not just this story's),
  not urgent enough to build today. Left as a known, understood false
  positive rather than silenced.

## 2026-10-26 — Nobody has to hand-parse engine.pid to answer "is this run alive? (folded from bmad-loop-liveness-footgun)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 111.1). The body below is `docs/dreams/bmad-loop-liveness-footgun.md`, verbatim, with its headings demoted one level and its 2026-09-16 fold banner left out; the file moved to `archive/docs/dreams/bmad-loop-liveness-footgun.md`.*

## Nobody has to hand-parse engine.pid to answer "is this run alive?"

### The Dream

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

### What it looks like when real

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

### What is real

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

### Constraints

- **Cannot be fixed by editing the installed package in place** — same constraint as every other
  `bmad-loop-*` dream in this repo: `bmad_loop` ships via a pixi/conda-forge git-pinned dependency,
  not code this repo owns; a fix here means either shelling out to `bmad-loop status --json` (the
  supported surface) or asking upstream to publish `engine_liveness`/`probe_liveness` as public API,
  never patching `.pixi/envs/*/site-packages/bmad_loop/` directly.
- **Not a private-API dependency.** Whatever this repo builds must go through `bmad-loop status
  --json` (or another documented CLI/output contract), not `from bmad_loop.runs import
  engine_liveness` — an internal function with no stability guarantee across upstream bumps.

### Non-goals

- **Not a fix for Marshal's `factory resume` double-drive bug itself** (`spec-3-7`) — that is a
  separate, already-deferred, larger fix this Dream's primitive unblocks, not something this Dream
  needs to solve.
- **Not a request to change `engine.pid`'s on-disk format upstream.** The two-token identity design
  is correct and intentional; nothing here asks bmad-loop to change it.

### Kinships

[[pyforge-marshal]] (owns `bmad-loop` adoption per `docs/specs/bmad-loop-adoption.md`) ·
[[bmad-loop-baseline-drift]] (sibling bmad-loop-footgun dream, same "cannot edit the installed
package" constraint, same containment-over-upstream-fix framing) · `spec-3-7-escalation-deferral-
and-resume`'s `deferred-work.md` entry (names the missing liveness primitive as a live blocker) ·
`docs/dreams/artifact-chain-reconciliation.md` (independently rediscovered the same footgun)

### Realization log

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
  operator answer (team memory `.claude/memory/reference/fleet-landing-pass-liveness.md`); exercised
  live at `cli/dispatch.py:2711-2726`, which refuses a dispatch on the liveness fact.
  **Open question 1 is now answered by the operator:** the resume-preflight `unknown` policy is
  **warn-and-proceed**, with `unknown` a first-class printed reason — refusing would coerce a *probe*
  failure into `alive` semantics and would block routine resumes daily (auto-memory
  `project_steward_unknown_landing_journal`). Spec stays `in-progress` (not `shipped`) because that
  answer is still unwired: Epic 24 explicitly excluded resume-preflight consumption
  (`spec-24-2-…md:18`). Batch:
  `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`.

## 2026-10-26 — One fabricated commit, eight stations of debris (folded from bmad-output-hygiene)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 111.1). The body below is `docs/dreams/bmad-output-hygiene.md`, verbatim, with its headings demoted one level; the file moved to `archive/docs/dreams/bmad-output-hygiene.md`.*

## One fabricated commit, eight stations of debris

### The Dream

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

### What it looks like when real

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
- The fleet dashboard (`pyforge.doctor.sources.fleet_scan --source sprint-status`) reports zero
  `gaps` for herald: its brief and architecture directories are named `brief-pyforge-herald-*`
  / `architecture-pyforge-herald-*`, matching every other station's convention and the
  `_stage_globs()` pattern that scores them.
- `_currency()`'s `_FEEDS` check carries a small grace period, so same-day/adjacent-day edits
  (a spec's routine memlog touch) stop reading as permanent drift, while genuine multi-day gaps
  still surface. The 5 pairs identified in Cluster 5 (warden, doctor, scribe, steward, mason) are
  re-validated and their currency stamp brought current.

### What is real

A 5-agent research-only audit ran 2026-08-02 across all 9 BMAD projects (679 files). Nothing was
moved — this section is the evidence base for the cleanup above, not yet acted on.

#### Cluster 1 — the `dad47c408a` fabricated-boilerplate set (fleet-wide, the dominant finding)

| Artifact | Confirmed affected | Confirmed clean / already fixed | Notes |
|---|---|---|---|
| Dead test scaffolding (`tests/`, `pytest.ini`, `playwright.config.ts`) | atlas, doctor, marshal, warden, scribe, mason, steward (7) | herald, genesis (never generated for them) | Zero real tests anywhere in these trees; the real, wired suites all live at `src/shared/packages/pyforge-<station>/tests/`. Atlas's copy even configures a Vite dev server; Marshal's configures Playwright `e2e/web`/`e2e/pages` for a CLI-only product. |
| Hollow `planning-artifacts/sprint-status.yaml` (0%, empty arrays) | confirmed identical stub in all 8 stations | — | Distinct from `sprint-status-ledger.yaml`, which is real, tracked, and what dashboards/scripts actually read. Doctor's copy was explicitly called "stale" in a same-day follow-up commit (`17a3154075`) but never removed. |
| Fabricated `test-architecture.md` | originally atlas, warden, doctor, mason, scribe, steward | **fixed same-day** by commit `2957718d4c` (real, code-grounded content) for those 6; herald and marshal's were never fabricated in the first place | **Genesis is the one exception — never fixed.** Its `test-architecture.md` still opens "Genesis bootstraps the PyForge factory installer... initializing the complete factory stack from scratch," referencing a `src/pyforge_genesis` package that doesn't exist and directly contradicting Genesis's own current, correct, constitutive PRD/architecture ("ships no product"). |
| Unfilled `README.md` (`[role]`/`[responsibilities]` placeholder) | marshal, herald, genesis confirmed; doctor has an equivalent unfilled placeholder | — | Same generic text across all three checked; likely fleet-wide, not individually verified for the remaining 5. |

#### Cluster 2 — orphaned single-file debris (distinct pattern: leftovers from *already-completed*, unrelated consolidations, never cleaned up)

- **Atlas** — `RESUME-EPIC-10.md`: self-marked "✅ CLOSED 2026-07-29... HISTORY," zero repo-wide references, its unique content (loop blind-spot lessons) already promoted into auto-memory.
- **Herald** — `intake-video-scripts-manticore-2026-07-31.md`: input material for a Dream+Spec (`video-scripts`) that was fully retired to `archive/` on 2026-08-01; this one file was left behind by oversight. Same shape as `product-brief-deckcraft.md`, which the same-day Herald consolidation already found and archived.

#### Cluster 3 — content-drift, NOT archive candidates (flagged for a separate correction pass)

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

#### Cluster 4 — the fleet dashboard reports a real gap for herald (found 2026-08-02, post-realization)

The user reported the program console (`docs/dashboard/`) showing stations "out of date, missing
artifacts, and a gap" for the 8 primary stations. Verified against `pyforge.doctor.sources.fleet_scan`'s
own fleet scan (`Lane 1 /console/ (Guildhall generator retired) --source sprint-status`), confirmed **on
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

#### Cluster 5 — the currency ("feeds") check has no grace period, so every station reads stale

Reported by the user after CAP-10: "now every station on the dashboard has something as
outdated." Verified against `pyforge.doctor.sources.fleet_scan`'s `_currency()` on the regenerated
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

#### Confirmed clean, no action needed

Scribe, Steward, and Warden's satellite-Dream/Spec-kernel layers all resolved to already-correct,
archived-in-place retirement records from earlier same-day consolidation passes — zero genuine
candidates beyond Cluster 1's fleet-wide items. Mason's 5 "orphan" Spec kernels all check out as
intentional (2 live, 3 properly archived-in-place). Every `spec-archive/`, per-story spec,
`.memlog.md`, retro, change-history file, and dated snapshot report checked across all 9 projects
was confirmed to be permanent-by-design record, not clutter — none were flagged.

### Realization log

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
- **2026-08-02** — User caught a CAP-12 scoping oversight: genesis was never checked (the sweep
  only covered the 8 non-constitutive stations), but it carries its own `prd`/`arch` pair and was
  stale too. Same structural-only pattern as scribe/steward/warden, confirmed via genesis's own
  PRD `currency_review`; architecture.md and epics.md (both already state "nothing here" —
  constitutive, ships no product) re-stamped. Currency findings 4 → 3; doctor/mason/warden's 3
  genuine findings unchanged.

## 2026-10-26 — A BMAD write can never land in the wrong project's artifacts, mechanically (folded from bmad-switch-scope-enforcement)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 111.1). The body below is `docs/dreams/bmad-switch-scope-enforcement.md`, verbatim, with its headings demoted one level and its 2026-09-16 fold banner left out; the file moved to `archive/docs/dreams/bmad-switch-scope-enforcement.md`.*

## A BMAD write can never land in the wrong project's artifacts, mechanically

### The Dream

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

### What it looks like when real

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

### What is real

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
  trigger depends on a workspace-management capability (`developer-workspace-management`-shaped)
  this repo doesn't have yet; its `checkpoint` verb has no documented local pain point. This Dream
  deliberately scopes down to only the piece with a real, already-bitten, already-triaged local gap.

### Constraints

- **One verification function, not two.** `scripts/bmad-switch` and Marshal's `cli/init.py` must
  call the SAME logic, not maintain parallel copies that can drift from each other the way the
  current two checks already have.
- **Hard-fail, never a warning that can be ignored.** The whole point is replacing discipline
  ("the agents checked") with enforcement; a check that only prints to stderr at exit 0 does not
  close this gap, it just documents it more visibly.
- **Cheap enough to call on every write, not just at init/switch time.** Three file reads and a
  string compare — no subprocess, no network — so wiring it into a write-skill's preflight is
  free, not a tax anyone will disable under load.

### Non-goals

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

### Kinships

[[bmad-module-provisioning]] (the other realized BMAD-infra Dream owned by a non-Marshal station,
useful as a format precedent) · [[pyforge-marshal]] (the estate; DW-1-4-2 already lives in its own
deferred-work ledger, found during Story 1.4's adversarial review) · [[genesis-installer]] (the
delivery-vs-source boundary this Dream operates inside, per `spec-pyforge-marshal`'s own SPEC.md) ·
[[scratch-worktree-lifecycle]] (a Steward-owned scratch worktree opened against a specific BMAD
project is exactly the caller this Dream's `verify_scope` primitive was designed for — cross-station
kinship, not a merge)

### Realization log

- **2026-08-14** — Dream captured. Surfaced while evaluating a sibling org's `bmad-workspace-integration`
  dream as a PyForge candidate; investigation found the broader dream's automatic-switch and
  checkpoint pieces lack local justification, but its core "verify before write" concern maps
  directly onto an already-open, already-triaged gap in `pyforge-marshal`'s own deferred-work
  ledger (DW-1-4-2, found during Story 1.4's adversarial review, explicitly awaiting "a product
  decision"). Scoped down to just that gap. Owner assigned to `marshal` per `one-front-door.md`'s
  own multi-project-wiring ownership survey and `spec-pyforge-marshal/SPEC.md`'s explicit
  "Marshal owns the source of `scripts/bmad-switch`" statement — not Steward, despite most other
  BMAD-infra Dreams in this repo defaulting there.
- **2026-08-14** — Spec authored (spec-bmad-switch-scope-enforcement, pyforge-marshal) by the 2026-08-14 dream-backlog audit: one shared verify_scope primitive consumed by bmad-switch and cli/init.py, closing DW-1-4-2's product-decision hook.

- **2026-09-09 (fleet readiness pass — operator-approved batch)** — **`specified` → `realized`.**
  Stories 20.6/20.7 shipped one shared stdlib-only primitive (`pyforge/marshal/scope.py`) consumed by
  exactly two hard-failing call sites — `scripts/bmad-switch:207-210,232-233` and
  `pyforge/marshal/cli/init.py:247`. `DW-1-4-2` closed.
  **The open question is answered by the operator:** no further BMAD write-skill gets the preflight
  in local-recipes — `verify_scope` is wired at **`marshal factory dispatch`** instead (marshal
  **Story 33.9**), and the skill-injection mechanism is deferred to the foundry cutover's 44.5
  layout. Rationale: the remaining exposure is the parallel-agent case `CLAUDE.md` documents as a
  HARD rule, and every parallel BMAD write enters through `factory dispatch`, which already stamps
  `BMAD_ACTIVE_PROJECT` per invocation; the two gitignored compatibility symlinks this Dream guards
  may not survive the cutover at all. Spec `ready` → `in-progress` (CAP-1/2 in effect, the third call
  site unbuilt). Batch:
  `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`.

## 2026-10-26 — The tier map names Cursor models Cursor can serve (folded from cursor-native-tier-map)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 111.1). The body below is `docs/dreams/cursor-native-tier-map.md`, verbatim, with its headings demoted one level and its 2026-09-16 fold banner left out; the file moved to `archive/docs/dreams/cursor-native-tier-map.md`.*

## The tier map names Cursor models Cursor can serve

### The Dream

The four-verb campaign runs in Cursor. Unattended `factory drain` must not
launch until `model_tier_map` tells the truth about that plane: easy /
medium / heavy name **Cursor-native** models on the Ultra pool, using the
explicit `{ harness, model }` form so a Cursor string never lands on
`claude --model` again.

This IDE drives the wave. Drain is the later twin, only after this map
and the fail-safe both hold.

### Kinships

- `spec-marshal-token-economy` CAP-12 (tier → provider/model)
- `spec-dispatch-tier-routing-fails-safe` (bare-string leak; 2026-09-12 revert)
- `spec-28-29` (Cursor headless wire dead — drain stays off until proven)
- `docs/dreams/dispatch-tier-routing-fails-safe.md` (realized)

### What it looks like when real

All eight `marshal-policy.toml` maps use inline tables with
`harness = "cursor"`. Catalog contains the named Cursor models. A claude
adapter launch still gets sonnet/opus baseline, never composer. This
Cursor chat implements stories; `factory drain` is not started from this
Dream.

### Realization log

- **2026-09-13** — Specified as `spec-cursor-native-tier-map`. Story 33.15
  remaps all eight `marshal-policy.toml` `model_tier_map` stages to explicit
  `{ harness = "cursor", model = "…" }` tables. Unattended drain stays off
  until 28.29 is separately proven.
- **2026-09-16** — Folded into [[marshal-token-economy]] (operator-ruled token-savings
  consolidation) and archived in place. Prior status: `specified`. The Spec
  (`spec-cursor-native-tier-map`) stays live and remains the contract; the
  narrative continues in the parent's § Fold (2026-09-16).

## 2026-10-26 — The dashboard assumes slug == project directory — it isn't, and won't stay (folded from dashboard-project-path-derivation)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 111.1). The body below is `docs/dreams/dashboard-project-path-derivation.md`, verbatim, with its headings demoted one level; the file moved to `archive/docs/dreams/dashboard-project-path-derivation.md`.*

## The dashboard assumes slug == project directory — it isn't, and won't stay

### The Dream

`pyforge.doctor.sources.fleet_scan` and `index.html` build almost every link and
`have`/`gaps` detection by string-gluing a roster slug straight onto
`_bmad-output/projects/<slug>/planning-artifacts/...`. That held while every
chain's slug matched a live project directory 1:1. It stopped holding the
moment stations started absorbing satellite chains and dissolving outright:
`presenton-pixi-image`/`wasm-analytics-stack`/`unity-data-stack` moved into a
Smith's tree without a project dir of their own, `pyforge-genesis` was
retired to `docs/governance/` with none left at all, and `genesis-installer`
writes its epics inside `pyforge-marshal`. Each of these produced the same
bug shape twice already (found 2026-08-02): a naive `have` check reads
"nothing landed" for real, merged work, and the slug's link 404s.

Both known occurrences were just patched in place — `IMPL_CAMPAIGN`'s
`epics_path` field for the build-campaign section, `CAMPAIGN_PROJECT_OVERRIDE`
+ `planning_project` for the planning-campaign section — each with its own
override dict and its own JS link-building special case. That is a fix per
occurrence, not a fix of the pattern: the next dissolution or absorption adds
a third override dict somewhere else in `generate.py`, and a third dead-link
special case somewhere else in `index.html`.

This Dream is not urgent — both current instances are fixed and verified.
It exists so the *next* absorption doesn't rediscover the same bug shape a
third time. Someday: one small derivation helper (`slug -> real project dir,
real epics/PRD/architecture path`) that every roster-driven `have`/link
computation calls, fed by a single override table instead of one per call
site — so a future dissolution is a one-line addition, not a hunt through
`generate.py` and `index.html` for every place that assumed identity.

### What it looks like when real

- One function (Python side) maps a roster slug to its real project
  directory, consulted by every `have`/`gaps` computation in
  `generate.py` — not two separate override dicts (`CAMPAIGN_PROJECT_OVERRIDE`
  today, plus `IMPL_CAMPAIGN`'s per-entry `epics_path`) with duplicated
  reasoning in their comments.
- The generated `data.js` carries enough of that resolution (a real project
  slug, or an explicit "no project dir" marker) that `index.html`'s JS never
  re-derives or guesses a path — today it does, twice, independently.
- Adding a newly-absorbed or newly-dissolved slug to the dashboard is edits
  in exactly one place, and the existing detectors
  (`scripts/dashboard_drift_check.py`, `bmad-drift-check`) would catch a
  slug missing from that table before it ships a dead link.
- `pyforge-genesis`'s redirect to `docs/governance/` — currently a literal
  `r.slug === "pyforge-genesis"` string check inlined in `index.html` — is
  data-driven the same way as every other override, not a special case in
  the rendering code.

### Realization log

- **2026-08-02** — Captured while fixing the second live instance of this
  bug (the planning-campaign section's `CAMPAIGN_ROSTER` link-building,
  alongside the already-fixed build-campaign `IMPL_CAMPAIGN` section) after
  the user reported dissolved/absorbed satellite slugs
  (`presenton-pixi-image`, `wasm-analytics-stack`, `unity-data-stack`,
  `pyforge-genesis`) missing from the dashboard entirely — root cause was the
  same "slug == project dir" assumption in two independent code paths. User
  explicitly deferred the general fix ("seed a dream for later") while both
  concrete occurrences were patched in place same-session. Not yet specified
  or scheduled.

## 2026-10-26 — A cost-tier dispatch override that cannot resolve its harness must never launch (folded from dispatch-tier-routing-fails-safe)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 111.1). The body below is `docs/dreams/dispatch-tier-routing-fails-safe.md`, verbatim, with its headings demoted one level and its 2026-09-16 fold banner left out; the file moved to `archive/docs/dreams/dispatch-tier-routing-fails-safe.md`.*

## A cost-tier dispatch override that cannot resolve its harness must never launch

### The Dream

Marshal's FR-51 model-tier-batching feature picks a difficulty-tiered model per
dispatch, but the resolver can silently produce a hybrid, broken launch: a real,
working adapter binary paired with another provider's model string it was never
meant to receive. When that happens, the CLI crashes on startup with zero tokens
spent, tmux's `pipe-pane` races the dying window and is tolerated as non-fatal,
and bmad-loop reports the story merely "deferred" — with no signal anywhere that
the actual cause was a policy misconfiguration, not a story-content problem. A
dispatch policy that cannot resolve its own configured harness should never
partially apply; it should fall through to the full, guaranteed-safe baseline,
or fail loudly and specifically.

> The tier map should make dispatch cheaper when the alternative is real —
> never quietly break it when the alternative is not.

### Why now — measured, not feared

Found 2026-09-12 chasing three identical, silent dispatch failures for
pyforge-marshal Story 28.29 (0 tokens spent, empty logs, no surviving tmux
server, "1 deferred" every time). Root-caused by direct execution of marshal's
own resolution code: `model_tier_map.heavy.dev = "composer-2.5-fast"` (a
Cursor-only model, present in **all eight** stations' `marshal-policy.toml`)
resolves to `harness=None` (the bare-string entry carries no explicit harness
key), so `spin.py` falls back to the base `claude` adapter — but still writes
the Cursor model string into `[adapter.dev].model`. The resulting
`claude --model composer-2.5-fast` launch is invalid and crashes instantly.

Compounding this: Cursor is independently, permanently confirmed dead for
headless dispatch fleet-wide (`spec-28-29-wire-is-dead-for-cursor-...`,
shipped 2026-09-10 — "there is no headless integration path, full stop"). So
the tier map has been pointing every heavy/medium/easy-tier dispatch at a
target that can never work, for as long as it has been configured this way
(traced to at least commit `5e7f8cac4b`, well before this session — not a new
regression, a long-standing latent one this dispatch happened to trip).

The resolver already supports an explicit `{harness = "...", model = "..."}`
inline-table form (`tier_routing.py::parse_stage_entry`, `allowed = {"harness",
"model", "pool"}`) — every station's config just used the bare-string
shorthand instead, which is exactly what let the mismatch happen unnoticed.
This is a config-authoring gap plus a missing fail-safe, not a missing
capability.

### What it looks like when real

- A `model_tier_map` entry whose harness cannot be resolved to something
  actually dispatchable in the current loop home never reaches a real launch —
  it falls through to the full baseline (`[adapter]`/`[adapter.review]`),
  never a mix of one candidate's adapter and another's model.
- The default state of `model_tier_map`, fleet-wide, is the same models the
  baseline already uses — a cost-tier override exists only once a second
  harness is verified live in that loop home, not merely configured on paper.
- Enabling a real second harness (Copilot, or whatever is next) always uses
  the explicit `{harness, model}` form, never the bare-string shorthand — and
  rolls out one station at a time, proven across real dispatches, never
  flipped fleet-wide in a single config change (the way Cursor's was).
- A misconfigured or dead-harness tier entry produces a loud, attributable
  finding (an `MRS-SPIN-01x`-class code) the very first time it is hit — never
  a silent "deferred" outcome that reads as a story-content problem.

### Constraints / Non-goals

- **Not a redesign of the token-economy cost-tracking layers**
  (`model_cost_catalog`, pricing, the `context.*` compression layers) — those
  stay untouched; this is scoped to the dev/review model-tier ROUTING resolver
  and its current default values.
- **Not a decision on Copilot.** Whether and when Copilot becomes the second
  harness (its quota history and wrap-composition rework cost are already
  recorded in spec-28-29) stays a separate, explicit operator call — this
  Dream only ensures that whenever that call is made, the resolver cannot
  silently half-apply it the way it did for Cursor.
- **Marshal owns the resolver code and the config format**; the eight
  per-station `marshal-policy.toml` files are data, corrected by the same
  mechanical change once the resolver-side contract is settled.

### Kinships

[[pyforge-marshal]] (owns `core/tier_routing.py`, `cli/spin.py`,
`adapters/harness_bmadloop.py`, and every station's `marshal-policy.toml`) ·
the shipped `spec-28-29-wire-is-dead-for-cursor-specifically-copilot-is-a-real-
but-uncertain-alternative-documented-either-way.md` (2026-09-10 — the
permanent, live-verified cursor-is-dead finding this Dream's fix must respect,
never re-litigate) · [[spec-surface-overlap-tolerance]] (the same-day sibling
precedent: a gap found while chasing an unrelated failure, closed the same day
with a new, narrowly-scoped Dream rather than reopening a shipped one).

### Realization log

- **2026-09-12** — Seeded (operator-authorized: "yes go ahead, dream to code").
  Found investigating three identical silent dispatch failures for
  pyforge-marshal Story 28.29 — itself a phantom-duplicate ledger key from a
  retitle-without-reconcile, fixed separately in commit `0fc84301f2`.
  Root-caused by direct execution of `resolve_tier_launch` /
  `render_policy_toml` against the live pyforge-marshal policy, confirming the
  hybrid claude-adapter / cursor-model launch byte-for-byte. Next act:
  `bmad-spec` derives the Spec under `pyforge-marshal`.
- **2026-09-12** — Realized, same day. `resolve_stage_candidate` no longer
  fabricates an answer when nothing is genuinely available (returns `None`
  instead of "never block"); `render_policy_toml` cross-checks each
  tier-mapped stage's model against the declared `model_cost_catalog`
  (`provider_declaring_model`, new in `core/model_cost.py`) against the
  REAL, final resolved `[adapter].name`, skipping the override on a
  mismatch. Fleet-wide, all eight stations' `model_tier_map.{heavy,medium,
  easy}.{dev,review}` reverted from Cursor's `composer-2.5`/`-fast` to
  `sonnet`/`opus` — the same models the plain baseline already uses.
  Verified by re-running the exact bug-finding probe against the live
  policy (no more `[adapter.dev]` override for any tier) and the full
  `pyforge-marshal-test` suite (7919 passed). One residual, documented gap:
  `marshal factory dispatch`'s own model-resolution path doesn't route
  through the new guard (protected today only because the config no longer
  contains a cross-provider model) — `cli/dispatch.py`'s own live
  binary+authcheck preflight is a separate, already-hardened defense this
  effort did not need to duplicate. Story spec:
  `archive/_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-dispatch-tier-routing-fails-safe.md`
  (moved to the archive home on 2026-10-26, marshal Story 109.1).
- **2026-09-12** — Residual gap closed, same day, on operator request.
  `cli/dispatch.py`'s own model-resolution path (`resolve_dispatch_model_
  with_retry_escalation`) now carries the identical `provider_declaring_
  model` cross-check, applied right after the live binary+authcheck
  walk's real `resolution.profile` is known — the dispatch engine's own
  "real, final adapter" moment, the counterpart to `render_policy_toml`'s
  `doc["adapter"]["name"]`. A mismatch drops the model override to `None`
  and records a new `MRS-DISP-043` (WARN) rather than launch a
  live-verified harness with a model it was never meant to receive. Both
  dispatch engines now carry the identical guarantee; no known gap
  remains.
- **2026-09-16** — Folded into [[marshal-token-economy]] (operator-ruled token-savings
  consolidation) and archived in place. Prior status: `realized`. The Spec
  (`spec-dispatch-tier-routing-fails-safe`) stays live and remains the contract;
  the narrative continues in the parent's § Fold (2026-09-16).

## 2026-10-26 — The Dream-to-Code model has never verified itself (folded from dream-to-code-model-self-verification)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 111.1). The body below is `docs/dreams/dream-to-code-model-self-verification.md`, verbatim, with its headings demoted one level; the file moved to `archive/docs/dreams/dream-to-code-model-self-verification.md`.*

## The Dream-to-Code model has never verified itself

### The Dream

The Dream-to-Code model — Tier 0 Dreams motivating a Tier 2 Spec, decomposed
into PRD/architecture/epics, driving code, with `scripts/dream_chain_check.py`
enforcing the chain per `_bmad-output/EXEMPLAR-STANDARD.md` — was itself
established by a restructure (2026-07-23) rather than born through its own
pipeline. Two follow-ups from that restructure were named at the time and
never built: a `dream_chain_check.py --dreams` mode, and running `bmad-spec`
against the model's own governing documents (dogfooding). Both are still
genuinely open — confirmed live: `dream_chain_check.py --help` lists only
`--json` and `--inv`, no `--dreams` flag exists anywhere in the script; no
`spec-dream-to-code*` (or equivalently named) folder exists anywhere under
`_bmad-output/projects/*/planning-artifacts/specs/`.

Neither gap is urgent — `dream_chain_check.py`'s existing INV-1/2/3 checks
already do real chain-completeness enforcement, and the model plainly works
today (52 Dream files, 43 Specs, this session alone produced 5 new Dreams
through the process the model itself defines). But two things the model's
own restructure promised remain unbuilt, and nothing since has revisited
them — this Dream exists so they don't stay permanently deferred by default.

### What it looks like when real

- `dream_chain_check.py` gains a mode (`--dreams`, or folded into an existing
  `--inv` value) that specifically validates **Dream file hygiene** — status
  vocabulary correctness, `owner:` attribution, frontmatter completeness — as
  distinct from the chain-completeness checks INV-1/2/3 already run. (Concrete
  scope TBD at spec time: the exact boundary between "chain completeness"
  and "dream hygiene" needs deciding, not assumed here.)
- A Spec exists for the Dream-to-Code model itself — produced by running
  `bmad-spec` against `docs/dreams/README.md` / `AGENTS.md` § the tiers /
  `_bmad-output/EXEMPLAR-STANDARD.md`, proving the model can specify itself
  the same way it requires every station and deliverable to be specified.
  Whether this Spec lives under a station (marshal, since it owns the
  drift-check tooling) or in `docs/governance/` alongside the Charter/Lexicon
  kernels (since the model is arguably constitutive, not a single station's
  product) is an open question this Dream does not resolve.

### What is real

- Confirmed 2026-08-03: `dream_chain_check.py --help` shows no `--dreams`
  flag. The script's only filters are `--json` and `--inv {INV-1,INV-2,INV-3}`.
- Confirmed 2026-08-03: no dogfooded Spec for the model exists anywhere —
  `find _bmad-output -iname "*dream-to-code*"` returns nothing.
- The restructure that named both follow-ups (2026-07-23) is recorded only
  in auto-memory (`project_dream_to_code_model.md`), not in any tracked Dream
  file — this Dream is that follow-up's first tracked, git-visible home.

### Constraints

- Whatever `--dreams` mode is built must not duplicate INV-1/2/3's existing
  coverage — read them first (`scripts/dream_chain_check.py`) before deciding
  what a new mode actually adds.
- Dogfooding must produce a real Spec via the real `bmad-spec` skill run, not
  a hand-authored document that merely looks like one.

### Non-goals

- Not a request to re-litigate the model's own design — both items are
  mechanical follow-through on a decision already made, not new scope.

### Realization log

- **2026-08-03** — Captured while auditing open backlog items across memory
  and Dreams, at the user's request, excluding ongoing station-epic
  implementation work. Both follow-ups traced to the 2026-07-23 restructure
  memory and confirmed still genuinely open by direct inspection (no
  `--dreams` flag, no dogfooded Spec) before this Dream was written.

## 2026-10-26 — Durable runs — work survives the machine that made it (folded from durable-runs)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 111.1). The body below is `docs/dreams/durable-runs.md`, verbatim, with its headings demoted one level and its 2026-09-16 fold banner left out; the file moved to `archive/docs/dreams/durable-runs.md`.*

> **Superseded 2026-08-02 (dream consolidation).** Fully decomposed into `spec-pyforge-marshal`
> and the real PRD as FR-61 (bounded-loss durability, stage-boundary push + fleet-launch
> wiring), FR-62 (durability as a reported fleet-status dimension), and FR-63 (fleet-wide
> branch retirement) — see [`docs/dreams/pyforge-marshal.md`](pyforge-marshal.md). Nothing in
> this Dream's real, measured evidence (the 2026-07-31 audit table) is lost — it is cited
> directly in the consolidated Dream. See `spec-durable-runs` for the retirement record.

## Durable runs — work survives the machine that made it

### The Dream

An unattended factory that can lose its own output is not autonomous, it is
lucky. Every artifact a run produces — the commit, the story spec, the verdict,
the token spend that bought them — should be **durable the moment it exists**,
not the moment somebody remembers to save it.

The loss is never only code. A discarded story is lost **compute, tokens, and
wall-clock**: marshal 1.8 was 8.8M weighted tokens and about an hour of a
machine's life, and for forty minutes it existed as an unpushed commit on one
disk. Recovering code is possible. Re-buying the hour is not.

> A run that has to be remembered is a run that can be forgotten.

### Why now — measured, not feared

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

### What is real

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

### What is real, part two — the durability signal itself (measured 2026-08-09)

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

### The frontier

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
  quick heuristics were tried and both were wrong — a three-dot diff mismeasures
  squash-merged branches, a two-dot diff mismeasures branches `main` has moved
  past. And the stakes are known: herald 1.2's 734 lines *looked* dead at six
  days old, and scribe 1.3's 1,102 lines showed as 8 insertions in a diffstat.

### What this is not

[[fidelity-enforcement]] asks *does anything go red when a contract and its
artifact disagree* — enforcement. This asks *does the artifact still exist at
all* — durability. They meet at Scribe's leg of the audit triad (a verdict
nobody can retrieve is not auditable), and they must not merge: a factory can
enforce every contract perfectly on work it then loses, and has.

### Kinships

[[pyforge-marshal]] (owns the loop, the run lifecycle, and the fix) ·
[[fidelity-enforcement]] (enforcement to this Dream's durability;
`unpushed-work-check` is the third detector with nowhere to run, which is that
Dream's missing observation plane) · [[pyforge-scribe]] (the record that must
outlive the worktree) · [[pyforge-steward]] (the estate the runs stand on — a
credible claim on this Dream if durability becomes an operations concern rather
than a loop-lifecycle one) · [[pyforge-charter]].

### Realization log

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

## 2026-10-26 — Fidelity enforcement — a contract is only a contract if something fails against it (folded from fidelity-enforcement)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 111.1). The body below is `docs/dreams/fidelity-enforcement.md`, verbatim, with its headings demoted one level and its 2026-09-16 fold banner left out; the file moved to `archive/docs/dreams/fidelity-enforcement.md`.*

> **Superseded 2026-08-02 (dream consolidation).** The Marshal-owned slice is fully
> decomposed into `spec-pyforge-marshal` and the real PRD as FR-64 (a gate evaluation binds
> to the tracked spec's Success signal) — see
> [`docs/dreams/pyforge-marshal.md`](pyforge-marshal.md). The Doctor- and Scribe-owned
> slices of this same Dream (CAP-9 install-the-judge, CAP-6 actor-attributed event record)
> were explicitly out of scope for Marshal's PRD per the 2026-08-01 operator-scoping
> decision and remain those stations' own open items, not absorbed here. See
> `spec-fidelity-enforcement` for the retirement record.

## Fidelity enforcement — a contract is only a contract if something fails against it

### The Dream

Every tier boundary in the factory carries a **gate that fires in both
directions**. Not a convention, not a runbook line, not a rule an agent is
trusted to remember at 4am — a thing that goes red.

The factory already believes this in one place. Charter §7 was amended on
2026-07-28 so the Guildhall **refuses to publish** a row with no owner:
*visibility without consequence is decoration.* That sentence is not about
consoles. It is the general law of this system, discovered locally and never
generalized. Fidelity enforcement is that law applied to every boundary the
Dream→Code chain crosses:

> A contract that nothing can fail against is a plan.

The dream is a factory where **no tier boundary is held by attention** —
where the answer to "does the code still satisfy the contract it was built
from?" is an exit code, in both directions, at every layer, and the honest
answer when a boundary is ungated is that it says so out loud rather than
looking clean.

### Why now — the hole we can measure

`EXEMPLAR-STANDARD.md` states **ten** conformance requirements.
`dream_chain_check.py` enforces **INV-0…INV-3**, covering the ownership
through-line, the Dream→Spec link, and the sharded build tree. Rows **7, 8, 9
and 10** — per-story specs tracked, delivery records, the deferred-work
ledger, the layout README — are written down and enforced by nothing.

Row 7 is the one with a body count. Story specs are drafted by bmad-loop into
gitignored Tier-3 and become durable only if a human promotes them after
merge. At Dream-seed time: 125 stories done fleet-wide, 73 story specs
tracked — a gap of **~52**, and *approximately* is the point: nothing derives
that number, so this Dream cannot state it exactly without violating
`EXEMPLAR-STANDARD`'s own provenance rule 3, *derive counts; do not restate
them*.

Hand-repair does not hold. Warden and Atlas are the two stations whose story
specs were reconstructed by hand after real losses, and both have **drifted
again since** because the repair added artifacts and never added a gate. Six
stations were never repaired at all.

### The fidelity stack

Eight boundaries, most declarative-only and unchecked in the reverse
direction. Full table, the source-essay disposition, and the audit-triad's
substrate mapping: `_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-fidelity-enforcement/fidelity-stack.md`.

One property is easy to miss: **every layer is declarative.** Each states
what *should* be true, so each check compares a document to a document. What
actually happened at runtime — did the gate fire, was it skipped, who
overrode it — appears nowhere, because the factory has no observation plane.
That absence is Scribe's leg of the audit triad below, and it is why the
stack cannot currently close its own reverse direction.

### Three ideas from the provoking essay

Dispositioned in full, with the source's two blind spots, in the Spec's
`fidelity-stack.md` companion. Summary:

1. **The Spec is a layer in the fidelity stack — held, extended.** The
   Charter already says the PRD→architecture→epics chain is the Spec's
   *decomposition*, not a substitute for it. But the layering is asserted,
   not measured — INV-3 checks only the chain's *shape*. **Adds:** the
   Spec↔chain reverse gate (`EXEMPLAR-STANDARD` rows 5–6).
2. **The privileged layer fallacy — rejected in half, and the half
   matters.** Authorization stays privileged, permanently (an unattended
   factory needs something to hold intent still). Origination is not
   privileged, and never was — `bmad-drift-check`'s `surface-changed`
   reconciliation already does the essay's reverse check. **Adds:** a
   recorded fixed point per reconciliation.
3. **The resolution trap — the real gap, and it is ours specifically.** The
   spec→code gap is deliberately wide; the story spec is the factory's
   gap-narrowing device, and it is precisely the layer with no gate.
   **Adds:** Marshal builds · Doctor judges · Scribe records — INV-4,
   automatic Tier-2 promotion, and the reverse gate binding a spec's Success
   signal to the verify command that gated it.

### The audit triad — Marshal builds · Doctor judges · Scribe records

The Charter's chain reads forward as authorization (Marshal, named outright)
and backward as audit — a direction that has never had an accountable
station, though Scribe was chartered for exactly it. Extends §5's *the hand
that builds is never the gate that judges* one step further: **the hand that
judges is never the sole keeper of the judgement.**

Full definition, the five-field who/what/when/how/why event record, the four
concrete 48-hour incidents that motivate it, and the substrate mapping
(`journal.jsonl` / DuckDB / `pyforge-scribe`'s capture seam):
`.../spec-fidelity-enforcement/audit-triad.md`. Governing rule, stated here
because it is the thesis in one sentence:

> **An absent record and a clean record must never look the same.**

### What is real

Nine detectors run today: `bmad-drift-check`, `spec_surface_check`,
`dream_chain_check`, `deferred_work_check`, `dashboard_drift_check`,
`story_status_check`, `loop_stall_check`, `llms_full_check`,
`unpushed_work_check`. **The wiring, once the sharpest finding in this
Dream, shipped 2026-07-31**: `.github/workflows/detectors.yml` runs a
derived registry (`scripts/detectors.py`) on every PR and push, advisory
(findings warn, do not block). First run reconciled the concrete cost of
having had no trigger at all: the `spec_surface_check` drift PR #170
introduced and merged unnoticed.

### The frontier

The full, current capability list — with intent/success criteria, what has
shipped, and what is still open — is the Spec, not this Dream:
`_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-fidelity-enforcement/SPEC.md`.
In order, cheapest first: wire the detectors (**shipped**) → INV-4 (a
shipped story has a tracked spec) → automatic Tier-2 promotion → reverse
gates binding a spec's Success signal to its verify command → the record
rows get a station (Scribe, rows 7–9 as one trace) → the actor-attributed
event record → the ungated boundary declares itself → the fixed point
declared per change → **install the judge** — the control that makes every
other gate on this list trustworthy, and the only one currently held by
prose (Doctor over Marshal, ratified 2026-07-28, unenforced).

**Landing a gate on a factory that already violates it** — the baseline/
ratchet/grandfathering-expires migration doctrine for switching on INV-4
without redding the whole fleet — is in the Spec's
`migration-and-invariants.md` companion, borrowed from
[[pyforge-warden]]'s precedent.

### How we will know it worked

`regenerable-factory` has the regeneration drill. This Dream's equivalent:

> **Delete a tracked story spec at random, and CI names it — by story key, to
> the accountable station — within one run. Then do the same to a verdict:
> skip a gate, and the record shows a skip rather than a silence.**

Two deletions, because the Dream has two halves: the first proves the
declarative gates close, the second proves the observation plane exists —
and it is the one the factory would fail today.

### What this is not

[[regenerable-factory]] asks *does every line of code have a contract it can
be rebuilt from* — coverage, forward. Fidelity enforcement asks *does
anything go red when a contract and its artifact disagree* — enforcement,
both ways. They share a detector surface and must not share a scope.

### The Charter amendment it drives

Lexicon **§2 The Spec** defines the unit of contract but never says what
makes one binding. §7 already contains the missing sentence, scoped to the
Guildhall; the amendment generalizes it: a Spec is the unit of contract
**because something fails against it**.

A second clause, because the first is unsafe without it: per the 2026-07-28
ratification Marshal owns the detectors and the loop, so **Doctor holds the
verdict on Marshal's own rows** — an assumption this Dream depends on, not a
property it inherits (see *install the judge*, above).

A third clause — **the audit triad**: a Charter that names who builds and
who judges but not who *records* cannot deliver the backward trace it
already promises. **Scribe records events, not outcomes** — a record written
*by the verdict* is worthless for audit, because skipping the verdict then
also erases the evidence that it was skipped.

**Today none of the audit triad's five fields survives durably, and one is
deliberately erased.** `git blame` attributes to the *committer*, not the
actor. This repo's no-AI-attribution convention stays — the remedy is not to
restore a commit trailer, it is that provenance belongs in Scribe's
structured record (see `audit-triad.md`).

### Provenance

Provoked by an external essay on spec-driven development, read 2026-07-31.
Its argument, paraphrased: a specification earns the name only when
something can fail against it automatically on every change — otherwise it
is a prompt with ambitions. *(Paraphrased deliberately; the source is not
named here, at the operator's decision.)* Its fidelity-stack framing names
the layered-compression model this Dream borrows; § *Three ideas from the
provoking essay* is the authoritative record of what was adopted, adapted,
and refused.

One structural limit of the source, recorded because it is the reason this
Dream is **Charter-bound rather than merely a detector backlog**: its model
is artifact-centric and has no vocabulary for *who may weaken a gate* — that
question is not a refinement of the source's framework, it is the part an
autonomous factory cannot run without, because a system that can edit its
own gates has no gates.

### Kinships

The audit triad, in order: [[pyforge-marshal]] (builds — owns the loop that
must promote and the detectors) · [[pyforge-doctor]] (judges — holds the
verdict on Marshal's row) · [[pyforge-scribe]] (records — the record that
dies on teardown is the disease it was chartered to cure).

Then: [[regenerable-factory]] (coverage, to this Dream's enforcement) ·
[[team-memory]] (the durable trace Scribe's leg resolves to) ·
[[pyforge-warden]] (never-false-green, applied to our own board) ·
[[factory-console]] (§7, where this law was first discovered) ·
[[pyforge-charter]].

### Realization log

- **2026-07-31** — Dream seeded (operator call). Owner **marshal** by the
  cross-cutting-practice precedent; scope set to the **full fidelity
  stack**, not the story-spec row alone. Measured at seeding: 125 stories
  done, 73 story specs tracked, conformance rows 7–10 enforced by nothing.
- **2026-07-31** — **the audit triad named** (operator call): *Marshal
  builds · Doctor judges · **Scribe records***. Recorded as a Dream-level
  decision because it is larger than this Dream — the Charter's chain reads
  backward as audit and that direction has never had an accountable
  station.
- **2026-07-31** — **Scribe's leg scoped to events, not outcomes** (operator
  call): the record captures *everything an agent makes or does*, governed
  by *an absent record and a clean record must never look the same*.
  Extended the same day to actor attribution (who · what · when · how ·
  why).
- **2026-07-31** — **Scribe's record declared inclusive of runtime
  telemetry** (operator call): queried observability answering *what the
  system actually does*, alongside the curated knowledge graph answering
  *why*.
- **2026-07-31** — **independent review before commit.** Fixed three
  defects (a pronoun, a flat-restated count, an orphaned amendment clause).
  Added a migration doctrine and a success signal. Resolved the citation
  question by paraphrasing rather than quoting the source unattributed.
- **2026-07-31** — **the detectors themselves are untriggered** (found
  during the same review). No CI job or git hook invoked any of the eight
  then-existing detectors — the Dream's own thesis one level lower down.
  *Wire the eight* became the first frontier item, ahead of INV-4.
- **2026-07-31** — **the trigger shipped, advisory** (operator decision).
  Nine detectors now run on every PR and push via
  `.github/workflows/detectors.yml` and a derived registry
  (`scripts/detectors.py`). Findings warn, they do not block. Reconciled in
  the same change: the `spec_surface_check` drift PR #170 introduced and
  merged unnoticed.
- **2026-07-31** — **six invariants recorded for the trigger**, after the
  design was worked out conversationally and would otherwise have survived
  only in a session transcript. Three detectors found red on `main` at the
  time: `spec-surface-check` (broken by PR #170 itself), `dashboard-drift-
  check` (transiently), `dream_chain_check`'s INV-1 (expected until the Spec
  existed).
- **2026-08-01** — **Spec derived** (`bmad-spec`, operator-directed housekeeping
  session): `spec-fidelity-enforcement` — 9 capabilities (CAP-1 wiring
  shipped; CAP-2..9 open), 3 companions (`fidelity-stack.md`,
  `audit-triad.md`, `migration-and-invariants.md`). This Dream trimmed in
  the same session from ~652 to its current length, per the deferral
  recorded in the prior entry — mechanism detail (the fidelity-stack table,
  the disposition table, the audit-triad schema/incidents/substrate table,
  the six trigger invariants, the migration doctrine) moved to the Spec's
  companions rather than living in both places. `dream_chain_check`'s INV-1
  against marshal closed as part of the same pass (all 4 marshal-owned
  Dreams — durable-runs, fidelity-enforcement, one-front-door,
  pr-lifecycle — now have Specs).

## 2026-10-26 — Fleet Chain Completeness — Orchestrated Dream-to-Code Regeneration (folded from fleet-chain-completeness)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 111.1). The body below is `docs/dreams/fleet-chain-completeness.md`, verbatim, with its headings demoted one level and its 2026-09-16 fold banner left out; the file moved to `archive/docs/dreams/fleet-chain-completeness.md`.*

> **Ownership reassigned 2026-08-02** (herald → marshal). Herald's own constitutive dream
> draws an explicit boundary: "not infrastructure... BMAD monorepo/multi-project machinery
> and cross-agent portability moved to [[pyforge-marshal]]... Herald keeps their
> communication face only." An orchestrated Dream→Spec→Research→Brief→PRD→Architecture→
> Epics regeneration workflow is exactly that kind of machinery, not "voice and visual
> surface" work — it belongs under Marshal, which already owns the harness/governance layer
> for everything BMAD-chain-shaped in this repo (see AGENTS.md, `dream_chain_check.py`).
> No content changed; this is a placement correction, not a scope correction.

> **Narrative consolidated 2026-08-02, second pass (dream-level only).** This Dream's
> narrative now lives in [`docs/dreams/pyforge-marshal.md`](pyforge-marshal.md) under "The
> frontier." **Its downstream Spec stays fully live and untouched**: `spec-fleet-chain-completeness`
> (5 capabilities, authored via `bmad-spec` the same session, self-validated) is real, unbuilt,
> and not yet decomposed to a PRD. Only this top-level Dream file consolidates; the Spec was
> not merged, retired, or reworded.

## Fleet Chain Completeness — Orchestrated Dream-to-Code Regeneration

### The Dream

The factory has **eight layers** in the planning chain: Dream · Spec · Research · Brief · PRD · Architecture · Epics · Code. A project with **Fleet Chain Completeness** has all eight layers coherent, up-to-date, and traceable end-to-end. No gaps. No orphans. No outdated artifacts.

Today, keeping the chain complete is **manual and fragile**: when a Dream is updated or consolidated, the downstream layers fall out of sync. Specs reference deleted dreams. Epics reference orphaned specs. Code traces break.

**The Dream**: An autonomous workflow that **regenerates the entire planning chain from a consolidated Dream**, ensuring every layer stays coherent with no gaps or blockers. Run it once. Review. Commit clean. Repeat when the Dream changes.

### What This Solves

1. **Consolidation** — When multiple dreams merge into one (like Herald's four capability dreams → one consolidated dream)
2. **Drift Prevention** — After dream updates, regenerate all downstream layers automatically
3. **Completeness Verification** — Audit any project's chain: is it complete? Are all layers present? Do they agree?
4. **Cleanup** — Delete orphaned artifacts, old spec folders, stale epics from replaced specs
5. **Review Hygiene** — Generate everything, pause for human review in the IDE, then commit clean

### The Workflow: Eight Orchestrated Phases

**Phase 1: Spec Generation**
- Input: Consolidated Dream file
- Process: Run `bmad-spec` on the Dream
- Output: `spec-<project>/SPEC.md` (five-field kernel contract)
- Preserves: Capability IDs, decision log, assumptions, open questions

**Phase 2: Research Generation**
- Input: Dream + Spec
- Process: Extract research needs, generate research artifacts
- Output: Research.md or research/ folder with context, market analysis, requirements
- Preserves: Nothing yet (first time, so creates fresh)

**Phase 3: Brief Generation**
- Input: Dream + Spec + Research
- Process: Generate intake brief from consolidated inputs
- Output: Brief artifact summarizing scope, intent, success signal
- Preserves: Nothing yet (first time)

**Phase 4: PRD Generation**
- Input: Dream + Spec + Research + Brief
- Process: Run `bmad-prd` to produce full PRD
- Output: PRD with capabilities, constraints, success metrics, non-goals
- Preserves: Nothing yet (first time)

**Phase 5: Architecture Generation**
- Input: Dream + Spec + PRD
- Process: Run `bmad-architecture` to design system
- Output: Architecture artifact with components, data flow, constraints
- Preserves: Nothing yet (first time)

**Phase 6: Epics & Stories Generation**
- Input: Dream + Spec + PRD + Architecture
- Process: Run `bmad-create-epics-and-stories` to decompose into epics and stories
- Output: `epics.md` with full epic/story breakdown, IDs, acceptance criteria
- **Preserves**: Existing Code implementation status (shipped versions, v1.0 markers, story completion state)

**Phase 7: Code Verification**
- Input: Regenerated specs + epics
- Process: Trace Code implementation back to specs/epics/dream
  - Does Code still reference the correct specs?
  - Are shipped versions documented?
  - Are story completions still valid?
- Output: Linkage verification report (all traces intact, or gaps identified)
- Preserves: Code itself (read-only verification, no changes)

**Phase 8: Cleanup & Commit**
- Input: All regenerated layers + old artifact inventory
- Process:
  1. Identify old artifacts (orphaned spec folders, deleted-dream references, stale epics)
  2. Delete old files that are no longer needed
  3. Verify fleet structure is clean
  4. Audit: every file has a purpose in the chain
- Output: Cleanup report (what was deleted, what remains, fleet structure verified)
- **Does NOT commit or push** — stages for human review in IDE

### The Contract: Fleet Chain Completeness

A project achieves **Fleet Chain Completeness** when:

✓ Dream exists and is current
✓ Spec is derived from the Dream (via bmad-spec)
✓ Research artifacts exist and are current
✓ Brief exists and synthesizes Dream + Spec + Research
✓ PRD is derived from Dream + Spec (via bmad-prd)
✓ Architecture is derived from Spec + PRD (via bmad-architecture)
✓ Epics decompose the Architecture (via bmad-create-epics-and-stories)
✓ Code traces back to Epics, Specs, Dream
✓ All layers agree on scope, intent, success signal
✓ No orphaned or stale artifacts
✓ No broken references

### Configurable Parameters

When running the workflow, specify:

- **`project_slug`** — which dream/project to regenerate (e.g., `herald`, `pyforge-atlas`)
- **`dream_path`** — path to the consolidated dream file (e.g., `docs/dreams/herald-pitch.md`)
- **`preserve_code_status`** — whether to preserve existing Code implementation status (default: true)
- **`auto_commit`** — whether to auto-commit the regenerated chain (default: false — always review first)
- **`delete_orphans`** — whether to delete old spec folders and stale epics (default: true, with review pause)

### Success Criteria

- [ ] Workflow orchestrates all eight phases in sequence
- [ ] Each phase completes without manual intervention
- [ ] Spec preserves capability IDs and decision log
- [ ] Code implementation status is preserved (v1.0 shipped, stories done)
- [ ] All old/orphaned artifacts are identified and deletable
- [ ] Workflow pauses for human review before committing
- [ ] Dashboard shows project as "Fleet Chain Complete" (all eight layers present, coherent)
- [ ] Can be re-run whenever a Dream changes
- [ ] Configurable per-project without code changes

### Use Cases

1. **Dream Consolidation** (like Herald): Multiple dreams merge → one consolidated dream → run workflow → regenerate entire chain coherently
2. **Drift Recovery**: A Dream was updated → specs fell out of sync → run workflow → regenerate to match new dream
3. **Onboarding New Projects**: New dream → run workflow → automatically populate entire planning chain
4. **Audit Completeness**: Before shipping → run workflow in audit mode → verify no gaps in the chain
5. **Archive Cleanup**: Retiring a project → run workflow with `preserve_code_status=false` → clean slate for decommission

### What This Is Not

- Not a code generator (Code remains hand-written)
- Not an auto-committer (always pauses for review)
- Not a replacement for human judgment (specs and epics still need review, thought, and iteration)
- Not a one-way pipeline (can re-run at any time when the Dream changes)

### Realization Log

- **2026-08-01** — Dream seeded after running Herald Fleet Chain Completeness workflow manually. Realized the pattern is reusable, configurable, and valuable as a repeatable capability: "When a consolidated dream is ready, regenerate the entire planning chain autonomously, preserve code status, pause for review, then commit clean."

## 2026-10-26 — Retire genesis-installer — one marshal CLI, one PRD/architecture/epics chain (folded from genesis-installer-name-retirement)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 111.1). The body below is `docs/dreams/genesis-installer-name-retirement.md`, verbatim, with its headings demoted one level; the file moved to `archive/docs/dreams/genesis-installer-name-retirement.md`.*

## Retire genesis-installer — one marshal CLI, one PRD/architecture/epics chain

### The Dream

The 2026-07-28 Charter §5 split carved `genesis-installer` out of `pyforge-genesis` as
its own Dream, and the 2026-08-02 consolidation folded its brief/PRD/architecture/Spec
into `pyforge-marshal`'s own single chain — but as **satellite sections**: "Satellite:
Genesis Installer PRD," its own `FR1..FR62` numbering deliberately kept apart from
Marshal's own `FR-1..FR-65` ("distinct namespaces inside the one merged PRD," by explicit
prior override), and `epics-genesis-installer.md` left as a second, separate epics
document — the one thing that stayed fully unmerged.

That separateness leaked onto the fleet dashboard: the build-campaign section showed
`genesis-installer` as if it were still its own project, with its own row and its own
epics link, next to `pyforge-marshal`'s. A same-day stopgap (dashboard PR #233) labeled
both rows with their epic range so the split at least read as intentional — but the user
wants the split gone, not labeled: `genesis-installer` is not a second thing, it is
Marshal's own Epics 7-12, and every trace of it as a separate name or numbering island
should retire. `AD-51..65` and `CAP-10..18` already got this right — they continue
Marshal's own `AD-1..50`/`CAP-1..9` sequences with no separate namespace. `FR` did not:
the satellite section's `FR1..FR62` (no dash) needs to become `FR-66..FR-127` (with
dash), continuing Marshal's own sequence the same way AD and CAP already do. The smaller
installer-only namespaces — `NFR-O1`, `SC-01..SC-10`, `OQ-1..OQ-9`, `K-01..K-03` — need
the same treatment, folded into or reconciled against Marshal's own equivalent
numbering (`NFR-1..14`, however Marshal's PRD labels success criteria, `Q-1..Q-16`).

**Scope widened (2026-08-02, same session): this is not just a renumbering exercise.**
The mechanical "fold in" consolidation preserved two unresolved contradictions rather
than resolving them, because folding is a copy-and-renumber operation, not a design
pass: (1) Marshal's own CLI is **argparse**, already shipped (Story 1.1's
`core/{model,findings,verdict}.py` + `cli/`), while the installer satellite's own
architecture specifies **typer + rich** for its still-unbuilt CLI — one framework must
win for the one binary both live in. (2) `genesis init` collides head-on with the
already-shipped `marshal init <slug>` (loop-home provisioning), and a second collision
surfaced between `marshal check` (FR-65/AD-50, shipped, routes to
`scripts/detectors.py`'s registry) and the installer's own `check` verb (CAP-13,
answers a different question — does an *externally installed* repo still conform).
Manually renumbering IDs while leaving these open would produce one clean-looking
numbering space still describing two CLIs that don't agree on a framework or a verb
surface. The real fix is to **run the standard planning chain** —
`bmad-prd` → `bmad-architecture` → `bmad-create-epics-and-stories` — against the
already-unified Spec, so the CLI gets designed once, coherently, with these
contradictions actually decided rather than carried forward as open questions. This
supersedes the narrower "just renumber the IDs" approach as the Dream's primary target;
the renumbering above is what a clean rewrite produces as a side effect, not a thing to
hand-execute separately.

### What it looks like when real

- One `epics.md` under `pyforge-marshal`'s planning-artifacts, Epic 1 through Epic 12,
  no separate `epics-genesis-installer.md` file (its content merged in, archived not
  deleted).
- One FR space, contiguous, no bare-digit `FR62`-style leftover anywhere live, produced
  by the planning chain rather than hand-renumbered.
- `NFR-O1`/`SC-01..10`/`OQ-1..9`/`K-01..03` folded into or reconciled with Marshal's own
  equivalent sequences, not left as a second unlabeled island.
- Every "Satellite: Genesis Installer PRD/Architecture" section header, and every prose
  mention of "genesis-installer" as if it names a separate thing, gone — the content
  stays (as ordinary Marshal capability), the name doesn't.
- **The CLI framework contradiction is decided** (argparse — Marshal's own, already
  shipped — or a migration to typer+rich, but not both left standing) and **the verb
  collisions are resolved**: one `init`, one `check`, with the installer's distinct
  question ("does an externally installed repo still conform?") given its own verb name
  if `check` stays Marshal's own detector-registry route.
- The dashboard's build-campaign section shows one `pyforge-marshal` row (86 stories
  total across Epics 1-12), no second `genesis-installer` row.
- No citation left dangling: every FR/NFR/SC/OQ/K cross-reference across the PRD,
  architecture (`binds` fields), Spec (capability intent/success text), the epics
  document's acceptance criteria, and any gates/readiness report is internally
  consistent with the new chain.
- `.memlog.md` history and `archive/` content are untouched — the chain regenerates
  live, current documents; it never rewrites the historical record of how they got
  here.

### What is real

Investigated 2026-08-02, not yet acted on:

- `AD-51..65` and `CAP-10..18` are **already** unified with Marshal's own `AD-1..50`/
  `CAP-1..9` — no renumbering needed for those two namespaces.
- **Confirmed by a dedicated research pass (2026-08-02, full map in
  `spec-genesis-installer-name-retirement/citation-map.md`)**: `FR1..FR62` (installer's
  own, no dash) is the one requirement namespace not yet unified, and the sequence is
  gap-free and duplicate-free in strict ascending order — the natural sequential map
  `FR1 -> FR-66` … `FR62 -> FR-127` is valid as a starting point (the rewrite may still
  choose to reorder by topic). One caution: `FR-66..FR-69` were briefly claimed and
  reverted by an unrelated fold attempt the same day — free today, already used once.
- Three smaller installer-only namespaces still need a decision, not a mechanical
  renumber, and the research pass corrected this Dream's own original assumption about
  them: `NFR-O1` (single item) is likely redundant with Marshal's own `NFR-12`
  (near-identical substance); `SC-01..SC-10` and `K-01..K-03` (Kill criteria — the
  falsifiers of the installer's own Success Criteria) have **no existing Marshal
  namespace to fold into at all** — Marshal's PRD uses `SM-1..7`/`SM-C1..3`, never
  `SC-`, and has no kill-criteria concept; `OQ-1..OQ-9` against Marshal's own
  `Q-1..Q-16` — **corrected**: Marshal's sequence stops at `Q-16`, `Q-17` does not exist
  live anywhere, and no `OQ-*` item is actually cross-referenced into any Marshal
  `Q`-number (this Dream originally claimed otherwise; the claim wasn't borne out).
- Dashboard PR #233 (merged 2026-08-02) is the stopgap this Dream supersedes: it labeled
  the row split ("epics 1-6" / "epics 7-12") rather than removing it.

### Constraints

- **Never rewrite `.memlog.md` history or `archive/` content.** Both are the permanent,
  append-only record of how the consolidation actually happened; renumbering touches
  only live, current documents.
- **Story/epic identifiers never change.** `sprint-status-ledger.yaml`'s keys
  (`7-1-...`, `8-1-...`, etc.) and the epic numbers themselves (1-12) stay exactly as
  they are — only prose citation numbers (FR/NFR/SC/OQ/K) and section headers change.
  The active bmad-loop dev session depends on story-key stability.
- **Hold execution until the loop is clear.** A bmad-loop run against `pyforge-marshal`
  (Story 2.1, run `20260802-183704-36df`) was in flight when this Dream was captured;
  the user asked explicitly to spec this rather than edit the live planning tree while
  it runs, even though the loop-home is an isolated worktree/branch and unlikely to
  read these specific files for Story 2.1's own (Epic 2) work. **Confirmed again at the
  wider scope**: the full `bmad-prd`/`bmad-architecture`/`bmad-create-epics-and-stories`
  regeneration waits until Story 2.1's run is fully done and merged — epics.md is
  exactly what the active run's story identity (`sprint-status-ledger.yaml`) keys off
  of, and a chain rewrite is a bigger blast radius than the narrower renumbering this
  Dream started as.

### Non-goals

- Not touching `AD-51..65` or `CAP-10..18` — already unified, no action needed.
- Not a new BMAD project — this is cleanup inside `pyforge-marshal`'s own planning tree,
  same shape as `bmad-output-hygiene` and `dashboard-project-path-derivation`.

### Realization log

- **2026-08-02** — Captured after the user flagged the dashboard's `genesis-installer`
  row as still reading as a separate project even after PR #233 labeled the split, and
  asked to remove the name and reference completely rather than just label it. Offered
  three depths (dashboard+epics merge only / add prose section-title cleanup / full ID
  renumbering); user chose the full renumbering. User then asked to formalize this as a
  Dream and Spec rather than editing the live planning tree directly while the Story 2.1
  bmad-loop run is active — execution deferred to whenever the Spec is run.
- **2026-08-02 (scope widened)** — User asked to do "the entire marshal dream to spec /
  PRD / architecture chain / epic / story rewrite... so that genesis goes away and the
  marshal cli is built correctly" — reframing this from a manual FR-renumbering exercise
  to running the standard planning chain (`bmad-prd` → `bmad-architecture` →
  `bmad-create-epics-and-stories`) against the already-unified Spec, so the CLI framework
  contradiction (argparse vs typer+rich) and the verb collisions (`init`, `check`) get
  actually decided instead of carried forward. Sequencing confirmed: draft the Spec now
  (planning only, no live edits), hold the full chain regeneration until Story 2.1's
  bmad-loop run is done and merged.
- **2026-08-02 (Spec drafted, research complete)** — `spec-genesis-installer-name-retirement`
  written to `pyforge-marshal`'s planning tree (8 capabilities, self-validate PASS both
  passes). A dedicated citation-map research pass ran alongside it and confirmed the
  FR1..FR62 → FR-66..FR-127 mapping is valid, while **correcting this Dream's own
  original premise** that Marshal's Open Questions run to `Q-17` with `OQ-*` items
  already feeding it — the live sequence stops at `Q-16` and no such cross-reference
  exists. Also surfaced that Marshal has no existing `SC-`/kill-criteria namespace at
  all (not "unclear," genuinely absent), narrowing CAP-3 from a reconciliation to an
  adoption decision. Full map: `citation-map.md`, a companion of the Spec. Zero live
  edits to the PRD/architecture/epics themselves — execution stays deferred until
  Story 2.1's run clears, per the Spec's constraints.

## 2026-10-26 — Genesis installer — the seed, made executable (folded from genesis-installer)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 111.1). The body below is `docs/dreams/genesis-installer.md`, verbatim, with its headings demoted one level and its 2026-09-16 fold banner left out; the file moved to `archive/docs/dreams/genesis-installer.md`.*

> **Narrative consolidated 2026-08-02 (dream-level only).** This Dream's narrative now lives
> in [`docs/dreams/pyforge-marshal.md`](pyforge-marshal.md) under "Kept separate on purpose."
>
> **Superseded the same day (explicit user override, third pass, 2026-08-02).** The
> paragraph originally here said the downstream chain "remain[ed] exactly as they were...
> deliberately kept separate from `marshal` the CLI's own FR-1..65." That is no longer true
> for brief/PRD/architecture/Spec: `research/product-brief-pyforge-genesis.md`,
> `prds/prd-genesis-installer-2026-07-25/`, `architecture/architecture-genesis-installer-2026-07-25/`,
> and `specs/spec-genesis-installer/` were **consolidated** into `pyforge-marshal`'s own single
> brief / PRD / architecture / Spec — a "Satellite: Genesis Installer" section in the brief and
> PRD, a continued `AD-51..AD-65` in the architecture, a continued `CAP-10..CAP-18` in the Spec.
> **Only the epics genuinely stay separate**, exactly as before: `epics-genesis-installer.md`
> (6 epics / 36 stories, epics 7–12) is unchanged and was explicitly out of scope for this
> consolidation. The four original standalone documents are preserved, not deleted, at
> `archive/_bmad-output/projects/pyforge-marshal/planning-artifacts/{research/product-brief-pyforge-genesis.md,
> prds/prd-genesis-installer-2026-07-25/, architecture/architecture-genesis-installer-2026-07-25/,
> specs/spec-genesis-installer/}`. genesis-installer's own `FR1..FR62` (no dash) numbering is
> unchanged and was never renumbered into Marshal's `FR-1..FR-65` (with dash) — the two ranges
> stay distinct namespaces inside the one merged PRD.

## Genesis installer — the seed, made executable

### The Dream

[[pyforge-charter|pyforge-genesis]] is the operating model: the Charter, the Lexicon, the Guild, the
Dream→Code chain. This Dream is the **machine that installs it** — the difference between
a model that exists in one repository and a model that can be adopted by any repository.

```bash
marshal <verb>   # greenfield: a new repo born Dream-first
                 # brownfield: layer the model onto a repo without disturbing what runs
```

> **Renaming pending (operator call 2026-07-31): no `genesis` binary.** The verbs fold
> into Marshal's CLI. The name `genesis-installer` records the project this Dream was
> *carved out of* in the 2026-07-28 Charter §5 split — and that split completed on
> 2026-07-30, leaving **zero shared artifacts**: `pyforge-genesis` now holds only the two
> constitutive Dreams and an `epics.md` beginning *"No epics, and that is the contract"*,
> while this installer's whole chain lives under `pyforge-marshal`. The product is
> therefore named after a project deliberately separated from it, on the Charter's own
> grounds that *"constitutive records and the machine that installs them are different
> nouns."* The exact verb mapping is unsettled — `genesis init` collides head-on with the
> shipped `marshal init <slug>` (loop-home provisioning, story 1.4) — and is recorded as
> an open question in the Spec's memlog rather than guessed here, because the 19 story
> keys under Epics 10–12 carry the old verb names.

What it stands up — stated in the Spec's own two registers, because the difference is
the whole design and this Dream previously blurred it:

- **Verified, never installed** (`REFERENCED`): the pixi environment and Python toolchain,
  `bmad-method`, `bmad-loop`/`bmad-dev-auto`, and the BMAD module set — `skill-forge`
  and the BMM / BMB / TEA / CIS packages. Genesis asserts presence and a version floor;
  the packages come from conda-forge and are never vendored.
- **Materialized** (`COPIED` / `GENERATED` / `HYBRID`): the multi-project wiring
  (`scripts/bmad-switch`, per-project config and artifact isolation, concurrent loop
  homes via `scripts/bmad-loop-worktree`), the detector set and its CI wiring, the tier
  layout (`docs/dreams/`, `_bmad-output/projects/<station>/`), the `AGENTS.md` family,
  and the deck family.

*Corrected 2026-07-31.* The earlier wording listed `skill-forge` and BMM/BMB/TEA
alongside the copied artifacts, implying Genesis installs them. It does not, and no
capability or manifest row ever claimed it did — the promise existed only here, in
prose, which is precisely the Dream↔Spec gap [[fidelity-enforcement]] names.

### Why this is the Marshal's

Splitting this out of [[pyforge-charter|pyforge-genesis]] (2026-07-28, Charter §5 amendment) resolved a
Dream that was doing two jobs at once. Genesis-the-Dream is **constitutive** — it records
the Charter, the Lexicon, and the Guild's membership, and is owned by `guild` because it
precedes the stations. The installer is **buildable work**, and buildable work with no
accountable Smith is the exact condition the station model exists to make impossible.

It is the Marshal's by the Charter's own text, not by assignment: Marshal's toolkit already
lists every component this installs (bmad-method, bmad-loop, BMM/BMB/TEA, skill-forge,
web bundles), Marshal already owns *Monorepo & Multi-Project Operation* (`bmad-switch`,
per-project isolation, loop homes), and Marshal's CLI cadence already opens with
`marshal init — initialize a new BMAD-compliant project blueprint`. The installer is that
verb, made real.

### What is real

- **The Spec** — `spec-genesis-installer`'s 9 capabilities live on as `spec-pyforge-marshal`'s
  `CAP-10..CAP-18` *(folded in 2026-08-02, explicit user override)*, with its extraction
  manifest (now `spec-pyforge-marshal/extraction-manifest.md`): what is **copied**
  (conventions, skills, workflows) vs **referenced** (bmad-method releases) vs **generated**
  (per-repo Dreams). The original standalone Spec is preserved at
  `archive/_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-genesis-installer/`.
- **The four verbs** — `init` (CAP-14, greenfield), `adopt` (CAP-12, brownfield,
  dry-run by default), `check` (CAP-13, read-only conformance, CI-shaped), `update`
  (CAP-15, versioned migration with no hand edits) — all one `resolve → detect → plan →
  apply` pipeline. The master success switch is the **empty-plan oracle**: `genesis
  adopt --dry-run` against this repository at the shipped model version must produce an
  empty plan, or the model and the repo it was extracted from have diverged. **Zero
  execution weight so far** — all 36 stories in `epics-genesis-installer.md` (epics
  7–12) are `backlog`; no code exists under `src/shared/packages/` for any of it.
- **The proof** — this repository was the first brownfield adoption, installed by hand from
  `archive/docs/bmad-setup-plan.md`. The installer is that procedure, generalized.
- **The chain** — PRD and architecture *(folded in 2026-08-02, explicit user override)* now
  live inside `pyforge-marshal`'s own PRD (a "Satellite: Genesis Installer PRD" section,
  `FR1..FR62`) and architecture (a "Satellite: Genesis Installer Architecture" section,
  `AD-51..AD-65` continuing the station's own `AD-1..AD-50`) rather than as separate
  documents; the originals are preserved under `archive/`. **Epics stay separate, unchanged**:
  `epics-genesis-installer.md` (Foundation & the Write Guard · the Managed-Region Engine ·
  Detect & Plan, 6 epics / 36 stories) under `pyforge-marshal`, inherited from the pre-split
  `pyforge-genesis` project.

### The frontier

- **The write guard and managed regions** are the hard part: `adopt` must layer the model
  onto a live repo without clobbering what already runs. Every write is either into a
  managed region it owns, or refused.
- **Idempotent re-adoption** — running `adopt` twice must be a no-op, and running it after
  a model upgrade must migrate rather than overwrite.
- **Close the manifest's coverage holes** (found 2026-07-31 by auditing the manifest
  against a live inventory). CAP-1 promises a coverage check that HARD-fails on any
  unclassified artifact; measured against what is actually installed, the V1 manifest
  classifies **none** of: `skill-forge` (`_bmad/skf/**`, 59 directories), BMB, TEA, CIS,
  `bmad-dashboard`, or the four remaining `bmad-*` packages. An adopting repo would
  therefore inherit a model the manifest cannot describe — and CAP-1's own check would
  be the thing that reports it, if the manifest listed them to begin with.
- **Derive the detector set, do not list it.** The manifest names one detector
  (`bmad_drift_check.py`); the repo now has **ten**, discovered by `scripts/detectors.py`.
  A repo adopting the model today gets a tenth of the conformance surface. The manifest
  row should resolve through the registry, for the same reason the registry exists.
- **Version floors are hand-written and drift.** `bmad-loop` is pinned `>=0.8.1` while
  0.9.0 is what the model is exercised against. Not wrong — a floor is a minimum — but
  it is a restated number in a companion, which `EXEMPLAR-STANDARD`'s provenance rule 3
  (*derive counts; do not restate them*) exists to prevent.

### Realization log

- **2026-08-02 (dream-coverage audit)** — a separate pass audited the merged brief/PRD/
  architecture/Spec against this Dream and `docs/dreams/pyforge-marshal.md`, checking every
  substantial CAP-10..CAP-18 / FR1..FR62 / AD-51..AD-65 item for coverage and execution
  weight (epics-genesis-installer.md, Marshal's own `sprint-status.yaml`, and
  `src/shared/packages/` — genesis-installer has none of the three: all 36 stories are
  `backlog`, no code exists). One gap found and closed: this Dream named only two of the
  four verbs (`init`, `adopt`); `check` and `update` — and the empty-plan oracle that is the
  PRD's own primary success criterion (SC-01) — were absent even at summary level. Added
  above, in "What is real." Both flagged contradictions (CLI framework, `check` collision)
  confirmed to still have **zero execution weight on either side of the collision** — no
  genesis code exists, and Marshal's own `marshal check` (FR-65) is speced but its story
  (5-6) is still `backlog` too — so nothing here was silently resolved by the audit.
  Everything else in the merged chain was already reflected here or in
  `docs/dreams/pyforge-marshal.md`'s "Kept separate on purpose" section; no pruning was
  warranted.
- **2026-08-02 (explicit user override)** — **brief/PRD/architecture/Spec consolidated into
  `pyforge-marshal`'s own single chain**, reversing the "kept separate on purpose" call
  `docs/dreams/pyforge-marshal.md` made earlier the same day. `research/product-brief-pyforge-genesis.md`
  became a "Satellite: Genesis Installer" section in `product-brief-pyforge-marshal.md`;
  `prds/prd-genesis-installer-2026-07-25/prd.md` (`FR1..FR62`) became a "Satellite: Genesis
  Installer PRD" section, own numbering preserved and never renumbered into Marshal's
  `FR-1..FR-65`; `architecture/architecture-genesis-installer-2026-07-25/architecture.md`'s
  `AD-01..AD-15` became a "Satellite: Genesis Installer Architecture" section renumbered
  `AD-51..AD-65`; `specs/spec-genesis-installer/SPEC.md`'s `CAP-1..CAP-9` continued this
  station's own Spec sequence as `CAP-10..CAP-18`, its `AD-01..AD-09` references renumbered
  to match. Two contradictions surfaced by the fold, flagged rather than resolved: the CLI
  framework (Marshal's shipped `argparse` vs this installer's designed `typer`+`rich`), and a
  `marshal check` / `genesis check` verb-name collision (both feed Open Question 17). Only
  `epics-genesis-installer.md` stays a separate document, unchanged, per the same override.
  The four original standalone documents are preserved (not deleted) at
  `archive/_bmad-output/projects/pyforge-marshal/planning-artifacts/`.
- **2026-07-31** — **fold the CLI into Marshal; retire the `genesis` binary** (operator
  call), and correct the Dream's over-promise (it listed `skill-forge` and BMM/BMB/TEA
  among what Genesis *stands up*, which no capability or manifest row ever claimed —
  those are REFERENCED, verified and never installed). A manifest audit against a live
  inventory added ten missing REFERENCED rows and flagged two as restated-rather-than-
  derived: the detector row named **one** file while the repo had grown to **ten**, and
  the `bmad-loop` floor is hand-written. Findings recorded in the Spec's memlog for
  re-derivation, never hand-patched into `SPEC.md`. **The naming problem is that there is
  no relation left to name:** the 2026-07-28 split completed 2026-07-30 and the two
  projects now share zero artifacts. Verb mapping deliberately left open — `genesis init`
  collides with the shipped `marshal init <slug>`.
- **2026-07-28** — split from [[pyforge-charter|pyforge-genesis]] per the Charter §5 amendment
  ("owning is becoming — at the planning tier"). Genesis keeps the constitutive records;
  the installer becomes this Dream, owned by the Marshal. The chain (Spec, PRD,
  architecture, epics) moves to `pyforge-marshal` — physically blocked until Marshal's
  planning tree is sharded, because both trees are currently flat and their `prd.md` /
  `architecture.md` / `epics.md` would collide.

## 2026-10-26 — Refreshing every loop-home from main is a hand-run ritual (folded from loop-home-fleet-refresh)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 111.1). The body below is `docs/dreams/loop-home-fleet-refresh.md`, verbatim, with its headings demoted one level; the file moved to `archive/docs/dreams/loop-home-fleet-refresh.md`.*

## Refreshing every loop-home from main is a hand-run ritual

### The Dream

Keeping all 8 station loop-homes current with `main` is two directions, and
only one is automated. **Push** (a loop-home's own new commits reaching
origin) already has a real watcher — `scripts/loop_push_watch.py`
(`loop-push-watch` pixi task): runs on an interval for as long as any
bmad-loop engine is live, pushes every station + per-story worktree branch,
exits on its own. Found live this session: it was never actually running —
every push this session happened because a human (or agent) asked "is
anything ahead of origin?" and pushed by hand, the exact blind spot the
watcher exists to close.

**Pull** (main's new merges reaching each station's `loop/pyforge-<station>`
branch) has no automation at all. Every refresh this session was the same
manual sequence, repeated after nearly every PR merge: `git fetch origin
main`, then for each of 8 homes, `git merge --ff-only origin/main` — and
critically, a judgment call every single time on what a merge failure
*means*: a clean fast-forward (safe, just do it); a station with an ACTIVE
run (never touch, verify the root checkout is a separate git worktree from
any live session first); or a station diverged with old pre-squash-merge
history already redundant on `main` (needs a human confirmation before
force-pushing origin, verified by cross-checking one sample commit against
main's history each time). That third case happened twice this session
(doctor/herald/mason/scribe/steward, twice) — the same five stations, the
same reasoning, re-derived from scratch each time because nothing recorded
the verdict from the first pass.

### What it looks like when real

- `loop-push-watch` (and `dashboard-watch`, same gap) runs automatically
  alongside any fleet launch, not only when someone remembers to start it —
  ideally the same launch step that starts a `bmad-loop run` also ensures
  both watchers are live, rather than three separate things (the run, the
  push watcher, the dashboard watcher) a human has to remember to start
  together. A launch runbook or `.claude/skills/bmad-loop-setup/SKILL.md`
  itself naming both watchers as required companions would close most of the
  gap even without full automation.
- `unpushed-work-check` (the detector half) runs on the same standing
  check-in cadence the story-status/loop-stall detectors already get, not
  only when someone thinks to ask — so a watcher outage is caught by the
  second line of defense within one cycle, not discovered days later.
- A pixi task (or a `marshal` CLI subcommand, once one exists — see
  `docs/dreams/one-front-door.md`) does the pull side: fetch `main`,
  fast-forward every loop-home that can be fast-forwarded cleanly, and for
  each one, report rather than guess:
  - clean fast-forward → done, pushed, one line of output;
  - a live tmux session for that station → skipped, named explicitly, never
    touched;
  - genuine divergence (unique commits on the loop-home not reachable from
    main, e.g. an unlanded story merge) → reported, not touched, exactly the
    marshal case this session hit twice (Story 2.2, then Story 2.4, each
    correctly left alone until its own landing PR merged);
  - stale/redundant divergence (loop-home's unique commits are already on
    `main` under a different, squash-merged commit) → reported with the
    evidence (which commit, which PR it matches), but **the force-push
    itself stays a human decision** — this is not a case to fully automate
    away, only to stop re-deriving from scratch.
- The "already verified redundant" verdict for a specific set of stale
  commits, once given, doesn't need re-verifying next time the same commits
  show up stale again — either the force-push actually happens (closing the
  loop for good) or the verdict is recorded somewhere durable enough that a
  second pass doesn't repeat the archaeology.
- `.bmad-loop/policy.toml` rendering is a checked step of the same pull-side
  tool, not a separately-remembered `marshal config --write-harness-policy .`
  — the refresh reports a loop-home whose policy file is missing or stale
  the same way it reports a missed fast-forward.
- Opening a landing PR always re-verifies the remote branch state first
  (`git log main..origin/loop/pyforge-<station>`), never trusts a watcher's
  last-known-good push — closing the PR #243/#244 gap structurally instead
  of by discipline alone.

### What is real

- `loop_push_watch.py` exists, is a registered pixi task, and was
  **confirmed not running** for this entire session (`ps aux` came back
  empty) — started manually as a side effect of writing this Dream.
- **Root cause, investigated**: nothing starts it automatically. It is
  designed to "run for as long as any bmad-loop engine is running, then EXIT
  on its own" — but that lifecycle only closes the *stopping* half; nothing
  opens it. `bmad-loop run` does not spawn it as a companion process, and
  `.claude/skills/bmad-loop-setup/SKILL.md` — the skill that documents
  installing and using the orchestrator — describes the engine itself in
  detail but says nothing about starting `loop-push-watch` (or
  `dashboard-watch`) alongside a run. It is a fully manual, separate
  `pixi run` invocation that nothing in the launch path or its documentation
  prompts anyone to make. Every story launch this session (2.1 through 2.5)
  went through `bmad-loop run` directly, with no separate step to start the
  watcher — so it never had a chance to start.
- **`dashboard-watch` has the identical gap** — also a registered pixi task,
  also confirmed not running (`ps aux` empty). Same root cause: no
  auto-start, nothing in the launch documentation names it as a required
  companion.
- **The second line of defense was also dormant.** `unpushed-work-check`
  (the detector that finds the *symptom* — dangling/unreachable commits —
  after the fact, distinct from `loop-push-watch`'s *prevention*) had not
  been run at any point this session either. Running it live during this
  investigation returned **28 findings**: 12 unpushed local branches on the
  main checkout (pre-existing, from earlier sessions, a separate cleanup
  backlog) and 16 dangling commits — several of them exactly the exposure
  `loop-push-watch` exists to prevent, including a `WIP on
  bmad-loop/20260803-023308-65b7/2-4-doc-only-story-classification` commit
  from this session's own Story 2.4 dev pass. Three independent safety
  layers (prevention watcher, symptom detector, and the human noticing) were
  all silent at once; only the third one — this conversation's own review —
  caught it, days-late.
- No equivalent to `loop-push-watch` exists for the pull direction. Every
  refresh this session (main → all 8 loop-homes) was hand-run, multiple
  times, including the divergence triage described above.
- The doctor/herald/mason/scribe/steward stale-history case was
  independently re-verified twice this session with the same conclusion —
  concrete evidence the "re-derive the verdict every time" cost is real, not
  hypothetical.
- **A related standing risk, same theme**: `.bmad-loop/policy.toml` inside
  each loop-home is untracked (`git ls-files` confirms zero matches), so it
  cannot survive whatever event first breaks it (a fresh provision, a
  teardown/recreate, or anything short of the render step re-running) —
  recovery is `marshal config --write-harness-policy .`, a step nothing
  currently prompts for either. Checked live 2026-08-03: all 8 current
  loop-homes have their policy file present, so this is not an active break
  today — but it is the same class of gap as the two watchers above, a
  required companion step with no trigger of its own.
- **A concrete near-miss from opening a landing PR mid-session**: PR #243
  was meant to land two stories but only landed one — the second story's
  commit existed in the local loop-home checkout but had not actually been
  pushed to origin yet (the newly-started `loop-push-watch` hadn't reached
  its next interval), and `gh pr create --head loop/pyforge-marshal` builds
  the PR from the *remote* branch state, not the local one. A follow-up PR
  (#244) landed the missed story. The fix in the moment was discipline (push
  explicitly, then re-verify `git log main..origin/loop/pyforge-<station>`
  before opening any landing PR) — automation for the pull/refresh side
  described above should apply the same rule: never trust a watcher's
  interval when about to act on "what's on origin right now."

### Constraints

- Never auto-force-push. Detecting "this divergence looks stale and
  redundant" is exactly the kind of judgment call this repo's Git Safety
  Protocol treats as needing a human decision — automation should make that
  decision fast and evidence-backed, not make it unattended.
- Must detect a live tmux session (or equivalently, an active run in that
  station's `.bmad-loop/runs/*/state.json`) before touching a loop-home's
  root checkout, and must distinguish that root checkout from any per-story
  worktree branched off it (confirmed this session: the root checkout and an
  active worktree are separate git worktrees on separate branches — updating
  the root is safe even while a worktree-branch session is live).

### Non-goals

- Not a request to make the loop itself push at its own stage boundaries
  (`loop_push_watch.py`'s own docstring already names that as the durable
  fix, upstream, out of this repo's hands — this Dream is about running the
  stopgap that already exists, plus building the missing pull-side half).
- Not a request to automate opening a story's own landing PR into `main` —
  that is already fully specified as **Story 4.8, `marshal land`** ("the
  last mile lands itself," Epic 4, depends on S-4.4/S-4.7): opens/updates
  the PR without duplicating, applies labels, waits on required checks,
  merges by policy, retires the branch, resyncs, refuses on red checks,
  journals every landing. Confirmed live 2026-08-03 after manually landing
  ~10 marshal stories one PR at a time this session (2.1 through 3.2) — the
  exact gap 4.8 already closes. This Dream's own scope is the *other*
  direction (main → loop-home) plus fleet-wide push/refresh, which 4.8 does
  not cover.

### Realization log

- **2026-08-03** — Captured after refreshing main + all 8 station branches
  by hand for the second time in one session, including re-deriving the same
  stale-history verdict for 5 stations a second time. `loop-push-watch`
  started as an immediate, no-design-needed fix for half the problem; the
  pull-side automation is the open half this Dream exists to eventually
  close.
- **2026-08-03** — User asked why `loop-push-watch` wasn't running, treating
  the omission itself as a bug worth investigating, not just a missed step.
  Root cause found: no auto-start exists anywhere (not in `bmad-loop run`,
  not in the setup skill's documentation), so it is 100% opt-in and nothing
  prompts anyone to opt in. `dashboard-watch` has the identical gap.
  `unpushed-work-check`, the detector meant to catch the resulting exposure
  even if the watcher is down, had also not been run all session — live run
  returned 28 findings, including a dangling WIP commit from this session's
  own Story 2.4 dev pass. All three safety layers (prevention, detection,
  human review) were silent simultaneously; only the third caught it, late.
  Findings folded into "What is real" above.
- **2026-08-03** — Folded in a related standing risk surfaced from a memory
  review: `.bmad-loop/policy.toml` is untracked in every loop-home and has no
  render trigger of its own (previously known from PR #139's own incident,
  re-checked live — currently fine on all 8 homes, but the same
  no-auto-trigger shape as the two watchers). Also folded in a concrete
  near-miss from this same session: PR #243 silently landed only one of two
  intended stories because the PR was opened against a stale remote branch
  state — the fix (verify origin before opening any landing PR) is now a
  named requirement above, not just a lesson learned in the moment.

## 2026-10-26 — Marshal Dependency-Aware Dispatch — the fleet orders its own backlog and forgets nothing it kills (folded from marshal-dependency-aware-dispatch)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 111.1). The body below is `docs/dreams/marshal-dependency-aware-dispatch.md`, verbatim, with its headings demoted one level and its 2026-09-16 fold banner left out; the file moved to `archive/docs/dreams/marshal-dependency-aware-dispatch.md`.*

## Marshal Dependency-Aware Dispatch

### The Dream

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

### What is real — the incident this Dream is written from

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

### What this Dream asks for

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

### Guardrails — what this Dream refuses to do

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

### Gates and open questions

- **Where does `Deps:` parsing belong?** `factory drain` itself (marshal-native),
  or a shared library also used by `bmad-sprint-planning`'s readiness gate (which
  already reasons about story ordering during planning)? Reuse is preferable if
  the parsing logic is close enough to share.
- **Optional-story inclusion:** default include (as this Dream currently asks)
  or default exclude with an `--include-optional` flag? This session wanted them
  included; a different campaign might not.
- **Failed vs. stopped, mechanically:** can the supervisor actually distinguish
  "process received SIGTERM from outside" from "process crashed" from "verdict
  said no" using facts already available (exit code, signal, journal state at
  time of exit), or does marshal need a new signal handler to record intent
  before it dies?
- **Worktree-diff surfacing:** a `marshal factory status`-style check before
  retry, or baked into the retry command itself as a confirmation step?
- **Natural home:** this looks like a direct extension of the same surface Story
  22.11 (FR-193 CAP-10, station-scoped drain) already owns — `factory drain` /
  `factory dispatch --stories` — rather than a new epic. Decomposition (this
  Dream → Spec → epic/story placement in `pyforge-marshal`) will confirm.

### Addendum (2026-08-31) — the scope gate is real, but manually-fed

Landing `21.7` and `28.2` (the same two stories this Dream is written from)
surfaced a third finding in the same family: both got stuck in the identical
observation loop this Dream already describes, but the actual cause was
neither A nor B above. It was `MRS-GATE-007` — the AD-27 scope-containment
gate, deliberately non-waivable (`SCOPE_VIOLATION`, AD-49: "cannot itself be
waived to green"). Its `effective_surface` is `policy_surface ∩ spec_surface`,
and since no story spec anywhere in this repo declares its own `surface:`,
`effective_surface` collapses to `policy_surface` alone — a glob list
hand-authored per epic in `marshal-policy.toml`. `pyforge-marshal`'s epic-28
entry was scoped to exactly what Story 28.1 touched, with a comment already
admitting the gap: *"widen per-story as later Epic 28 stories land, same
pattern atlas used."* That's real, load-bearing operator toil sitting between
every future story and `drain_to_zero` actually reaching zero — an autonomous
loop that deadlocks on its own safety gate every single story isn't
autonomous, it's manual with extra steps.

**This Dream's stance stays what it was for A and B: the gate itself is not
the bug, the missing automation around it is.** `MRS-GATE-007` catches a real
class of mistake (a session touching files nobody scoped it to touch,
including a different station's package entirely) — the fix is to stop
requiring a human to hand-enumerate every path per story, not to remove the
containment property.

**C. Auto-derived effective surface, no manual per-story widening.**
`policy_surface` resolution (feeding AD-27's existing narrow-only combinator,
unchanged) auto-derives a safe per-station default — the station's own full
package tree (`src/shared/packages/pyforge-<slug>/**`, already how
`pyforge-atlas`'s epic-21 entry avoided most of this friction), its planning/
implementation-artifact trees, and the same common bookkeeping paths every
epic surface already repeats by hand (`.gitignore`, `pixi.toml`, `pixi.lock`,
`environment.yaml`, `scripts/.spec-surface-baseline.json`) — computed once at
`spin`/`dispatch` policy composition, not requiring an `[epic_surfaces]` entry
to exist at all. An explicit `[epic_surfaces]` entry, where an operator wants
tighter containment than the station-wide default, still narrows via the
existing `spec_surface`-style intersection.

**D. Scope-violation enforcement mode, policy-declared, default unchanged.**
A `hard`/`warn` flag (default `hard` — today's non-waivable refuse, byte-
identical for every station that declares nothing) lets an operator who
trusts C's auto-derivation opt a station into `warn`: `MRS-GATE-007`/`008`
still fire, still name the offending path, but land as an advisory finding
instead of a landing refusal. This is explicit, per-station, opt-in — never a
silent global downgrade of AD-49's non-waivable default.

**Gates for C/D:**
- Does a broadened default `policy_surface` blunt the gate's actual value —
  catching a session that touches a *different station's* package, or repo
  config nothing in this epic should ever need? The per-station package-tree
  default should preserve exactly that cross-station containment while
  dropping the within-station, per-file enumeration toil.
- `warn` mode's advisory finding needs to be loud enough that "unless anyone
  reads findings" (the real risk named when this was scoped) doesn't quietly
  become "nobody ever reads findings" — `marshal status`/`fleet-picture`
  surfacing it, not just the journal, is probably required, not optional.

### Addendum (2026-09-01) — verify-fail must terminalize, not heartbeat forever

**Incident:** atlas **23.1** (2026-09-01 overnight drain). Build session finished
and died; independent verify refused (`kedro-test` / `MRS-GATE-001`); WIP commit
remained on the dispatch branch. Story **22.2** kept the run **`LIVE`** by git
facts; the supervisor heartbeats every 60s indefinitely; **`dispatch-preserve`**
never ran (it only fires on supervisor exit with verdict **`failed`**). The
16-story atlas `--stories` chain stalled until an operator manual preserve,
supervisor kill, worktree reset, and bare redispatch.

**E. Verify-fail terminalization + transient auto-redispatch (Story 28.17).**
When the session is **dead**, verify outcome is **`refused`**, and git shows
progress — the supervisor must **stop as `failed`**: journal completion,
capture `failed/<story>/changes.patch`, exit. The existing transient-block
hotfix (`MRS-GATE-001` = retryable) then lets the next **`factory drain --once`**
tick **redispatch the same story** without `MRS-DRAIN-005` permanent block.
**Does not** change global 22.2 judge semantics; **does not** replace **28.13**
(SIGTERM/stopped taxonomy) — composes with it.

Spec: `spec-marshal-verify-fail-terminalization/SPEC.md` (CAP-1..3). Status:
`specified` (addendum E satisfied by bmad-spec 2026-09-01).

### Addendum (2026-09-01) — the campaign still cannot heal a named refuse

**Incident:** fleet-wide `drain_to_zero` campaign
`pyforge-marshal-20260901T123110026Z-bb6c1de1`. Stories 28.12–28.17 existed.
The supervisor still **stopped** on refuses it already knew how to name, and
recovery was a chat session.

| Refuse | Why marshal did not self-heal | Human / chat recovery |
|---|---|---|
| Steward 39.4 `MRS-DISP-005` | Drain never drafts a spec (22.7); **never re-preflights** a refused head | Draft spec, commit, bare `factory dispatch` |
| Same campaign after spec landed | `MRS-DRAIN-005` “never auto-retried” treats first look as permanent | Notice idle ≠ drained |
| PR #985 ledger conflict | CAP-4 land stops on GitHub `CONFLICTING` | Mechanical `done`∪`backlog` union |
| `gh pr merge` still `DIRTY` | Land has one backend | Local FF `main` |
| 28.13 done in worktree, no remote | Verify refuse skipped land; branch never pushed | Cherry-pick |
| `MRS-GATE-001` pandas collection | Repo-global gate; 28.17 would re-hit the same red | `importorskip` |
| fleet-picture **STUCK** after `failed` | Overlay treated terminal fail as live `verifying` | Status patch `20e88e8b0f` |
| 28.18 session “shell unavailable” | Agent claimed done; `pixi`/`git` rejected in-session; dirty leftover; no push | Chat commit + `gh pr merge` #1000 |

**F. Drain self-resolution (Stories 28.18–28.24).** Every named refuse has a
recovery the **fleet tick / CAP-4 land / supervisor** runs — not a Cursor
habit. Locked v1 (open questions closed for implementation):

- **Re-preflight** cheap predicates (spec glob, mergeable) every tick; expensive
  verify only when the refuse predicate-hash changes. “Never auto-retried”
  applies to genuine story failure after preserve, not “we looked once.”
- **Missing-spec** is `awaiting-operator` with a one-line path remedy — **no
  auto-authored stub** in v1. Idle-with-backlog is a finding.
- **Land** unions ledger-only conflicts (`done` beats `backlog`); if
  `merge-tree` is clean and GitHub is `DIRTY`, advance `main` (this repo).
- **Push** `origin/dispatch/<slug>/<story>` as soon as there is a commitable
  result — before verify can strand it.
- **Verify blast radius:** failure outside the story diff and effective surface
  is `pre-existing-gate` (WARN), not `MRS-GATE-001` story-refuse.
- **STUCK** only while refuse is live; dead tail + `failed` is idle. Stranded
  work is an **unpushed branch or open PR**, named in ATTENTION.
- **Harness finalization:** if the session reports done (or leaves a commitable
  dirty tree) but cannot run shell (`pixi` / `git commit` / `git push`), the
  **supervisor** retries those steps. It does not redispatch over dirt forever
  (`MRS-DISP-036`). If supervisor shell also fails, escalate `awaiting-operator`
  with the worktree path — never wait for chat.

Spec: `spec-marshal-drain-self-resolution/SPEC.md`. Dream file
`marshal-drain-self-resolution.md` is an archive pointer only.

### Realization log

- **2026-08-31** — Seeded from a live dispatch-ordering/retry incident and folded into
  `spec-marshal-token-economy` as CAP-14..CAP-17 → marshal Epic 28 Stories 28.12–28.15
  (`5c947eebec`; that Spec's `sources` names this Dream).
- **2026-09-01** — The addenda were contracted in `spec-marshal-drain-self-resolution`
  (`e5e31c228d`: CAP-1..6 / Stories 28.18–28.23, the drain self-heal residue; `14ac9ed408`: CAP-7 /
  Story 28.24, supervisor finalizes when the harness cannot run shell), with
  [`marshal-drain-self-resolution.md`](<https://github.com/rxm7706/local-recipes/blob/main/archive/docs/dreams/marshal-drain-self-resolution.md>) archived in place as a
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

## 2026-10-26 — Fleet drain heals itself — archive pointer (folded from marshal-drain-self-resolution)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 111.1). The body below is `docs/dreams/marshal-drain-self-resolution.md`, verbatim, with its headings demoted one level and its 2026-09-16 fold banner left out; the file moved to `archive/docs/dreams/marshal-drain-self-resolution.md`.*

## Fleet drain heals itself

> **Consolidated 2026-09-01** into
> [`marshal-dependency-aware-dispatch.md`](<https://github.com/rxm7706/local-recipes/blob/main/archive/docs/dreams/marshal-dependency-aware-dispatch.md>)
> **addendum F** (Stories 28.18–28.23). This file is archived in place so the
> slug does not 404; the contract is
> `spec-marshal-drain-self-resolution/SPEC.md` covering the parent Dream.
>
> Do not author new CAPs here.

### Realization log

- **2026-09-01** — Seeded and consolidated the same day (`e5e31c228d`) into
  [`marshal-dependency-aware-dispatch.md`](<https://github.com/rxm7706/local-recipes/blob/main/archive/docs/dreams/marshal-dependency-aware-dispatch.md>) addendum F; the
  contract is `spec-marshal-drain-self-resolution` (CAP-1..6 → marshal Stories 28.18–28.23, status
  `ready`), which covers the parent Dream. Archived in place so the slug keeps resolving.

## 2026-10-26 — A GitHub PR-merge branch from one project never masquerades as a same-numbered story in another (folded from marshal-land-cross-project-story-key-collision)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 111.1). The body below is `docs/dreams/marshal-land-cross-project-story-key-collision.md`, verbatim, with its headings demoted one level and its 2026-09-16 fold banner left out; the file moved to `archive/docs/dreams/marshal-land-cross-project-story-key-collision.md`.*

## A GitHub PR-merge branch from one project never masquerades as a same-numbered story in another

### The Dream

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

### What is real

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

### What it looks like when real

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

### Constraints

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

### Non-goals

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

### Kinships

[[pyforge-marshal]] (the station; `core/promotion.py` is its own core
module) · [[marshal-status-harness-run-id-poisoning]] (a sibling "trusted
a field that turned out to lie" bug, found the same day) ·
[[bmad-loop-liveness-footgun]] (same family).

### Realization log

- **2026-08-15** — Dream captured. Found live while attempting to land
  mason's story `4.2` per this repo's own "land proactively" convention —
  `marshal land` reported false success. Root-caused to source in
  `core/promotion.py`, reproduced directly against real `main` history
  (2,898 commit subjects, `project_slug='mason'`), and traced the two
  concrete false positives (`4.2` from PR #274/marshal, `2026.8` from PR
  #441/pixi-bump) to their exact originating commits. Not hotfixed per
  this repo's Dream-first policy for any `pyforge-marshal` code change;
  captured as its own Dream once the user asked directly to fix it
  properly rather than work around it.

- **2026-09-09 (fleet readiness pass — operator-approved batch)** — **`specified` → `realized`,
  fixture-pinned.** Fixed by direct commit `d7fd62707b` ("marshal: scope the GitHub PR-merge
  story-key pattern to project_slug") and subsequently absorbed into Story 20.8's shared grammar,
  where the scoping now lives as `_branch_belongs_to_project`
  (`pyforge-core/.../landing_evidence.py:161`, applied at `:227`). CAP-1's regression is pinned on
  the real PR #274 subject against BOTH slugs (`pyforge-core/tests/unit/test_landing_evidence.py:72`;
  `pyforge-marshal/tests/unit/test_promotion.py:42-95`). The Spec, which carried **no `status:` line
  at all**, is set to `shipped`.
  **Chain note, recorded rather than hidden:** no `epics.md` story ever owned this fix — it landed
  outside the story ledger and was back-filled by 20.8, which is why doctor's chain-completeness
  reports 2/2 CAPs uncovered. This Dream's own text says it was "NOT hotfixed per this repo's
  Dream-first policy"; it was, later. Batch:
  `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`.

## 2026-10-26 — Marshal trusts the environment it launches into — until it silently doesn't (folded from marshal-launch-environment-integrity)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 111.1). The body below is `docs/dreams/marshal-launch-environment-integrity.md`, verbatim, with its headings demoted one level and its 2026-09-16 fold banner left out; the file moved to `archive/docs/dreams/marshal-launch-environment-integrity.md`.*

## Marshal trusts the environment it launches into — until it silently doesn't

### The Dream

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
  ledger.** When a dispatch session dies (crash, kill, or a real failure),
  the run is recorded with a terminal verdict (`failed`, `stopped_externally`)
  that `factory drain` treats as permanently blocked — "never auto-retried,
  never forced past" by design, which is correct when the story genuinely
  failed. But an environment crash is not a story failure, and drain has no
  way to tell the two apart; every crash this session required the operator
  to notice the block, bypass it with a manual single-story `factory
  dispatch` (which does retry cleanly), and know that trick exists. There is
  no sanctioned "this was infrastructure, not the story — retry" path
  through `factory drain` itself.

### Non-goals

- Not a rewrite of the dispatch/spin split, the Tier-3/ledger two-file
  design, or `promote_sprint_status.py`'s architecture — every fix above
  works within the existing shape.
- Not a general crash-recovery framework for every marshal subprocess; scope
  is the dev/review session a story's worktree lives in.

### Realization log

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

## 2026-10-26 — Parallel dispatch fan-out when dependencies and surfaces are disjoint — without breaking the zombie guards (folded from marshal-parallel-dispatch-fanout)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 111.1). The body below is `docs/dreams/marshal-parallel-dispatch-fanout.md`, verbatim, with its headings demoted one level and its 2026-09-16 fold banner left out; the file moved to `archive/docs/dreams/marshal-parallel-dispatch-fanout.md`.*

## Parallel dispatch fan-out when dependencies and surfaces are disjoint

### The Dream

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

### What is real — the incident this Dream is written from

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

- [`marshal-dependency-aware-dispatch.md`](<https://github.com/rxm7706/local-recipes/blob/main/archive/docs/dreams/marshal-dependency-aware-dispatch.md>)
  — ordering (28.12), sanctioned retry (28.13), scope automation (28.14/28.15).
- [`marshal-single-story-dispatch.md`](<https://github.com/rxm7706/local-recipes/blob/main/archive/docs/dreams/marshal-single-story-dispatch.md>) — the
  validated pattern; addendum already named "parallel when surfaces are disjoint"
  as an open Spec question.
- [`horizontal-run-concurrency.md`](<https://github.com/rxm7706/local-recipes/blob/main/archive/docs/dreams/horizontal-run-concurrency.md>) — bmad-loop
  `max_parallel` stub; **this Dream is factory-dispatch fan-out**, not in-loop
  Phase 5.

### What this Dream asks for

#### A. Wave scheduler beside serial drain (opt-in, default unchanged)

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

#### B. Ready set from the dependency graph (28.12-adjacent, shared hook)

- Reuse the **same `Deps:` graph** Story 28.12 will introduce for ordering:
  a story is *ready* when every declared dependency is `done` on the tracked
  ledger (cross-epic edges included).
- Among ready stories, **28.12 ledger-order tie-break** still applies when
  choosing batch members — parallelism does not invent a second preference.

#### C. Surface-disjointness as the parallel safety proof

- Two stories may share a wave **only if** their **effective frozen surfaces**
  (AD-27: `policy_surface ∩ spec_surface`, same machinery as `MRS-GATE-007`) are
  **pairwise disjoint** — path-level, not heuristic.
- **Overlap within a station is a hard refusal** for that pair (stronger than
  today's cross-station `MRS-DISP-022` advisory). Disjointness is the proof that
  parallel landings cannot fight over the same files.
- Stories with **empty or unknown surface** do not fan out with others until
  surface is declared — conservative default, same posture as scope gates today.

#### D. 22.2 zombie guards preserved per story, relaxed per station

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

#### E. Observability and operator trust

- Journal a **`dispatch-wave`** intent/outcome: member story keys, computed
  disjointness evidence (surface hashes or path lists), cap applied, refused
  candidates with reason (`dep-unmet`, `surface-overlap`, `cap`).
- `marshal status` / `fleet-picture` show **in-flight count per station** and
  wave id — not a flat "28.7" that hides a second concurrent 28.10.
- Fleet-wide advisory lock (two campaigns racing one station) **unchanged**.

### Minimal design sketch (28.12-adjacent)

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

**Integration points** (for later Spec, not this Dream):

- `core/dispatch_fleet.py` — wave batch builder + cap
- `cli/dispatch.py` — `station_in_flight_conflict` narrowing; wave journal kinds
- `core/dispatch.py` — reuse 28.12 topo/ready helper; surface overlap already
  partially exists for `MRS-DISP-022`
- `planning-artifacts/marshal-policy.toml` — `dispatch.max_parallel` (default 1)

**Explicit non-goals in v1:**

- No shared worktree / no multi-story branch
- No automatic retry of parallel wave members (28.13 stays separate)
- No cross-station batching (stations already parallel)
- No weakening verify/land — each story still runs full gate ladder independently

### Guardrails — what this Dream refuses to do

- **Does not** replace Story 28.12 — ordering and fan-out compose; 28.12 ships
  first or in the same epic tranche, but this Dream is not "28.12 with extra steps."
- **Does not** weaken **22.2** per-story LIVE semantics or reintroduce
  notification-based completion.
- **Does not** weaken **22.3** verify-before-land or allow one story's land to
  skip another's gates.
- **Does not** silently raise `max_parallel` — cap must be declared in policy or
  flags; `fleet-picture` calls out when a station runs >1.
- **Does not** fan out stories whose surfaces are unknown — unknown means serial.
- **Does not** duplicate bmad-loop Phase 5 — that stub remains upstream; factory
  dispatch owns its own scheduler.

### Gates and open questions

- **Story placement:** **resolved 2026-09-01** — Epic 28 Story **28.16**, sibling
  to 28.12; spec `spec-marshal-parallel-dispatch-fanout/SPEC.md` (CAP-1..5).
- **Cap semantics:** fixed integer vs "as many disjoint as ready" vs token-budget
  aware (ties to token-economy Epic 28 stories 28.10/28.11).
- **Partial wave failure:** if one member of a wave fails verify and another
  succeeds, does the wave close asymmetrically or hold the survivor until the
  failed story is classified (28.13 stopped vs failed)?
- **Surface proof cost:** pairwise intersection on every tick vs precomputed
  surface index at spec-promotion time (Scribe/graph seam, 28.9-adjacent).
- **Operator override:** `--stories a,b,c` with `--parallel` — treat list as
  explicit wave (operator asserts disjoint) or re-validate surfaces and refuse?
- **Live proof required:** no fan-out ships without a fixture pinning two
  disjoint pyforge-marshal stories landing in one wave while a third overlapping
  story is correctly refused.

### Relationship to the active drain (2026-09-01)

Until this Dream is specified and built, operators should assume **serial
within station**: hand-maintained `fleet-drain-queue.yaml` order,
`--stories` chains, and cross-station parallelism only. The Epic 28 + atlas
campaigns running today are the baseline behavior this Dream improves — not
the other way around.

---

### Realization log

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

## 2026-10-26 — The operator stops re-pasting the status prompt — marshal watches its own runs (folded from marshal-run-watch)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 111.1). The body below is `docs/dreams/marshal-run-watch.md`, verbatim, with its headings demoted one level and its 2026-09-16 fold banner left out; the file moved to `archive/docs/dreams/marshal-run-watch.md`.*

## The operator stops re-pasting the status prompt — marshal watches its own runs

### The Dream

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

### Why now — measured, not feared

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

### What it looks like when real

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

### Constraints / Non-goals

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

### Kinships

[[pyforge-marshal]] (the station Dream; `marshal watch` joins `status`/`homes`/`check`
as a CLI verb under the same package) · [[fleet-status-supervisor-fallback]] (realized
— the sibling correctness fix for `marshal status`'s fleet view; `marshal watch`
reuses that same supervisor/engine liveness distinction rather than re-deriving it) ·
[[marshal-single-story-dispatch]] (realized — `marshal factory dispatch`, the
`bmad-build-auto` pattern this capability watches) · [[run-state-one-publisher]]
(specified, not realized — the future ground-truth source this capability can migrate
to without changing its report shape) · [[marshal-token-economy]] (loop-home policy
and budget fields `marshal watch` surfaces alongside phase/commit detail) ·
[[bmad-loop-liveness-footgun]] (the `UNSUPERVISED` fleet-picture trap this
capability's liveness check must not reproduce) · [[django-accelerator-framework]]
(host for the `django-marshal` portal-view follow-on CAP, if taken up).

### Realization log

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

## 2026-10-26 — Single-story dispatch is a marshal verb, not a session's discipline (folded from marshal-single-story-dispatch)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 111.1). The body below is `docs/dreams/marshal-single-story-dispatch.md`, verbatim, with its headings demoted one level and its 2026-09-16 fold banner left out; the file moved to `archive/docs/dreams/marshal-single-story-dispatch.md`.*

## Single-story dispatch is a marshal verb, not a session's discipline

### The Dream

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

### What is real

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

### What the Spec must decide

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

### Addendum (2026-08-31) — station-scoped and sequence-scoped dispatch

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
per-station ordered-backlog reader CAP-7 already owns:

1. **Station-scoped drain.** `marshal factory drain --mode <mode> --station <slug>` (or a
   sibling `dispatch-station <slug> --mode <mode>`) restricts the campaign to exactly one
   station's own backlog — same chaining/preflight/journal, one station instead of eight.
2. **Explicit sequence.** `marshal factory dispatch <slug> --stories <key1>,<key2>,...`
   chains a caller-supplied ordered list instead of the ledger's own backlog order — for
   prioritizing specific stories (today's scribe 6.2-then-6.3 finding) without editing
   `fleet-drain-queue.yaml`'s `order_overrides` for a one-off push. Every named key is
   validated against the station's actual backlog before anything launches — an unknown or
   already-done key refuses loudly, never silently skips.

**Non-goals:** not a new landing/verification mechanism (reuses `execute_dispatch_land` /
CAP-2 / CAP-4 unchanged); not a replacement for fleet-wide `drain`, which stays the
default for "drain everything."

Lands as a new CAP (CAP-10) in `spec-marshal-single-story-dispatch` when specced.

### Addendum (2026-09-02) — a `done` spec must not review-loop

**Problem:** `drain_to_zero` + `bmad-build-auto` can spend an afternoon writing
confirmatory review commits after the story is already `status: done`. Each
commit retriggers Cursor Auto-review. CAP-4 never flips the ledger, so the
fleet supervisor launches another session. The loop is not a reviewer flood; it
is the same story re-entered as a “fresh review.”

**Motivating incidents (2026-09-02):**

- Steward **41.2** ([#1017](https://github.com/rxm7706/local-recipes/pull/1017)):
  implementation done by review pass 4; passes 5–27 were 0-patch spec
  write-backs. Merge was `DIRTY` vs `main`. Fleet kept re-dispatching.
- Mason **13.2**: implementation + three real patches landed on the worktree;
  **18** confirmatory write-backs followed. **No PR** was opened. Ledger on
  `main` stayed `backlog`. Same loop.

**Two stacked causes:**

1. **Harness.** `.claude/skills/bmad-build-auto/step-01-clarify-and-route.md`
   routes `status: done` to a fresh step-04 review and resets
   `review_loop_iteration` to `0`. Step 4 writes
   `followup_review_recommended: false` and **never reads it** on the next
   start. The 5-iteration cap applies only to `bad_spec` loopbacks. Step 4
   commits the spec even when the pass applied 0 patches.
2. **Marshal.** Fleet drain treats ledger `backlog` on `main` as “dispatch
   again.” A harness halt of `done` does not make CAP-4 the *only* next step.
   Land fail (conflicts, no PR) does not park the story — it re-invokes the
   harness. `limits.max_followup_reviews` in loop `policy.toml` is not on this
   cursor dispatch path.

**Approach:** one new CAP (CAP-11), two stories — do not fork drain:

1. **Harness contract (local skill only).** `done` +
   `followup_review_recommended: false` → HALT `done` immediately (no review,
   no spec commit). `done` + `true` → at most one follow-up, then force the
   flag false. A 0-patch review pass must not commit. The vendored `bmad_loop`
   package stays unmodified. This amends the earlier “do not change
   `bmad-build-auto`” non-goal for the **in-repo skill copy only**.
2. **Dispatch terminal.** After the harness exits `done`, marshal runs CAP-4
   only (open/merge PR, ledger promote). It must not start another
   `bmad-build-auto` for that story. CAP-4 fail (conflicts, no PR, dirty)
   → CHAIN / `awaiting-operator` naming the PR or worktree. Never re-dispatch
   the harness until the operator unparks.

**Non-goals:** not a new landing path; not shrinking `max_followup_reviews`
(`docs/dreams/risk-tiered-review-depth.md`); not
`marshal-dependency-aware-dispatch` (Deps: / SIGTERM).

Lands as CAP-11 in `spec-marshal-single-story-dispatch`, Epic 29.

### Addendum (2026-09-11): CAP-3's bound verify command can miss the story's real surface

**The gap.** `MRS-GATE-010`/`011` bind CAP-3's "runs the story's real verify commands" to
exactly **one** command per station, read from that station's `marshal-policy.toml`
`verify_commands` — deliberately fixed, so a dispatched session cannot narrow its own
verification to dodge coverage (the exact exploit `MRS-GATE-011` was hardened against,
Story 49.3, this session). But `src/platform/` is a shared, cross-station surface — the one
Django host every station's portal mounts into — and a station's bound command only exercises
that station's own package (e.g. `pyforge-steward-test` never runs `src/platform/`'s own
suite: Django system checks, ruff, mypy, the full `src/platform/tests/` tree). A story whose
real diff lands in `src/platform/` can pass CAP-3's gate having never exercised the code it
changed.

**Why this is usually invisible.** The real backstop is GitHub Actions' `platform-ci.yml`,
path-triggered on every PR, which *does* run the full surface — the narrow per-station gate is
deliberately fast because that broader net is supposed to catch what it misses, before merge.

**Live evidence (this session, 2026-09-10/11).** GitHub Actions has been down fleet-wide
(account-wide billing outage) for the entire session, so the backstop has caught nothing —
every PR this whole session was merged on local verification alone. Steward Story 49.14
(CAP-10) passed its bound `pyforge-steward-test` gate and the harness's own targeted pytest
run, and its own review pass explicitly considered and rejected "verification command misses
platform tests" as false. A manual rescue pass running `platform-ci-local -- --test` (this
repo's own local replay of `platform-ci.yml`) surfaced four real, live defects the bound gate
never touched: a `ModuleNotFoundError` at Django startup masking a genuine, unresolvable
`twine`/`rich` dependency conflict; a real architectural-boundary violation
(`test_station_portal_shells.py`'s client-only portal rule); a nested-`asyncio.run()` bug in a
new transport wrapper; and four ruff findings. Sibling stories 49.6/49.7 separately surfaced a
smaller, structural instance of the same class: each dispatch worktree's own isolated
`.pixi/envs/` lacked a `local-recipes` install, so an unrelated CLI-availability meta-test
false-failed under the bound gate — not a `src/platform/` defect, but the same root cause
(the bound command's fixed scope doesn't account for what a fresh dispatch worktree actually
needs to exercise the real surface).

**Approach.** One new CAP (CAP-12), composing CAP-3 rather than replacing it — the bound
per-station command stays the anti-gaming floor, never removed or weakened:

1. The dispatch driver already computes the story's diff surface for CAP-3's frozen-surface
   check. Extend that computation: when the diff touches `src/platform/`, require
   `pixi run -e local-recipes platform-ci-local -- --test` (or a documented, cheaper
   equivalent that still exercises Django startup — the class of bug this addendum
   documents is specifically an eager-import/startup failure a narrower pytest-only
   invocation cannot see) to pass in addition to the station-bound command, before CAP-4
   land. A failure there is a loud non-landing verdict naming the failed cross-surface gate —
   same lattice CAP-3 already uses, never a silent skip.
2. Generalize past `src/platform/` specifically: any station whose own policy names a
   shared-surface prefix and a corresponding broader check gets the same treatment — this
   addendum's own motivating case is `src/platform/`, but the mechanism is not steward-only
   (every station's portal lives there).

**Non-goals:** not replacing GitHub Actions as the authoritative backstop — this is a
narrower, faster local supplement for exactly the cross-surface blind spot, not a claim to
replicate full CI fidelity; not weakening or removing the per-station `MRS-GATE-011`
byte-match binding (CAP-12 composes on top of it, never instead of it); not auto-detecting
every possible shared surface fleet-wide in the first pass — `src/platform/` is the proven,
motivating case.

Lands as CAP-12 in `spec-marshal-single-story-dispatch`.

### Realization log

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

## 2026-10-26 — The templated merge-subject shape never masquerades as a same-numbered story from another project (folded from marshal-templated-merge-subject-cross-project-collision)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 111.1). The body below is `docs/dreams/marshal-templated-merge-subject-cross-project-collision.md`, verbatim, with its headings demoted one level and its 2026-09-16 fold banner left out; the file moved to `archive/docs/dreams/marshal-templated-merge-subject-cross-project-collision.md`.*

## The templated merge-subject shape never masquerades as a same-numbered story from another project

### The Dream

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

### What is real

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

### What it looks like when real

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

### Constraints

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

### Non-goals

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

### Kinships

[[marshal-land-cross-project-story-key-collision]] (the sibling gap in
the same precedence chain, already fixed for a different parser) ·
[[pyforge-marshal]] (the station; `core/promotion.py` is its own core
module) · [[marshal-status-harness-run-id-poisoning]] (same family: "a
field trusted as proof that turned out not to be").

### Realization log

- **2026-09-11** — Dream captured. Found live during `pyforge-doctor`
  Epic 22 dispatch: three of four dispatched stories (22.1, 22.2, 22.4)
  received an instant, false "already merged" verdict from the fleet-
  drain campaign supervisor; a fourth (22.3) was actually orphaned by the
  same false signal mid-task. Root-caused to `parse_templated_merge_
  subject` lacking the `project_slug` scoping its four sibling parsers in
  the same `classify_merge_subject` precedence chain already carry.
  Reproduced directly against live `main` (5,629 subjects): doctor's own
  `project_slug` query returns 129 keys, a large majority attributable to
  other stations' epics (`22.11`/`22.12` from marshal; `23.x`/`28.x`/
  `39.x`–`49.x` from other stations entirely). All affected work (22.1,
  22.2, 22.3, 22.4) recovered and landed by hand this session
  (`local-recipes` PRs #1251–#1254); not hotfixed per this repo's
  Dream-first policy — captured as its own Dream for a real fix.
- **2026-09-11 (later, same session)** — Specced via `bmad-spec`
  (`spec-marshal-templated-merge-subject-cross-project-collision`, 1
  capability, self-validate PASS both passes), decomposed into Epic 35
  (Story 35.1), and fixed. `_classify_merge_subject`/`merged_story_keys`/
  `marshal_native_merged_keys` (`core/promotion.py`) gain an optional
  `known_keys` parameter — a templated-shape match is trusted only when
  its key is a member of the querying project's own tracked story
  catalog, corroboration the bare subject text cannot provide.
  `dispatch_supervisor/__main__.py::gather_dispatch_git_facts` (the exact
  function that produced this session's false verdicts) wired to load
  `known_keys` from the project's own `sprint-status-ledger.yaml` via a
  new `_load_known_story_keys` helper, failing closed (trusts nothing) on
  a missing or malformed ledger. Re-running this Dream's own live
  reproduction: the templated-shape match count for a `pyforge-doctor`
  query drops from 79 to 30, with `22.11`/`22.12`/`23.x`/`28.x`/`39.x`–
  `49.x` all excluded. Full `pyforge-marshal` test suite green (7,799
  passed), including new regression tests reproducing the exact
  2026-09-11 false positive against a fake filesystem/ledger. Named,
  explicit residual (not closed by this story, mirroring the sibling
  fix's own "not every caller" Non-goal): `cli/dispatch.py`'s wave/
  reconcile paths, `dispatch_land.py`, `cli/status.py`, `cli/land.py`, and
  `branch_story_merge_confirmed_by_grammar` remain unwired. Status:
  `dreamt` → `realized`; the Spec closes as `shipped`.

## 2026-10-26 — Marshal Token Economy — the loop that reads less, says less, and re-learns nothing (folded from marshal-token-economy)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 111.1). The body below is `docs/dreams/marshal-token-economy.md`, verbatim, with its headings demoted one level and its 2026-09-16 fold banner left out; the file moved to `archive/docs/dreams/marshal-token-economy.md`.*

## Marshal Token Economy

### The Dream

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

### What is real

> *2026-09-09: this section is the 2026-08-30 baseline and is kept as the record. Epic 28 has
> since shipped every item below as **machinery** (24/24 `done`, verified against `main`), and
> none of it is switched on — so the **behaviour** this section describes is still the live
> behaviour. See § Addendum (2026-09-09).*

**Marshal's existing token posture is brakes, not diet.** Shipped: per-story /
per-run weighted-token and wall-clock ceilings (E3.6, defaults 50M/500M
weighted), the idle ladder (nudge → stop-retry → defer), prompt-cache TTL
discipline (NFR-14, poll ≤60s, `cache_read_weight = 0.1`), difficulty-driven
model tiering (FR-51, wired but rarely fed — see
[`adaptive-model-tiering.md`](<https://github.com/rxm7706/local-recipes/blob/main/archive/docs/dreams/adaptive-model-tiering.md>)), and single-story
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
  [`pixi-candidate-currency.md`](<https://github.com/rxm7706/local-recipes/blob/main/archive/docs/dreams/pixi-candidate-currency.md>)).
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

### The integration architecture — five layers, one policy surface

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
  indexes the worktree and wires the agent integration; the supervisor treats
  index staleness as a run-admission finding, not a mid-run surprise.
- **Layer 3 — incremental derived context (cocoindex).** The epic-context
  compile (today an "if cache invalid, re-distill" step inside bmad-build-auto)
  becomes a cocoindex flow: story specs, epic-context, and continuity summaries
  are derived artifacts that update incrementally when planning sources change
  — never recomputed from the full PRD on a hunch, never stale.
- **Layer 4 — planning knowledge graph (graphifyy).** The planning corpus
  (PRD, epics, architecture, specs) becomes a queryable graph so step-01
  routing retrieves precisely the fields a story binds to. This layer is
  shared infrastructure with Scribe's `GraphStore` seam — Marshal consumes it,
  Scribe owns it.

### What Marshal itself must grow

1. **A context-pipeline policy block.** `EffectivePolicy` → rendered
   `policy.toml` gains a `[context]` section: which layers are on, compression
   aggressiveness, CCR store path, per-profile wrap command. Declared like
   everything else Marshal renders — never hand-configured in a loop home.
2. **Harness-profile wrapping.** The packaged profiles
   (`claude.toml`, `copilot.toml`, …) gain an optional wrapper field applied
   at spin/dispatch, so Layer 1 is a profile property, not a shell hack.
3. **Genesis seeding of the toolchain.** `marshal seed` installs and `marshal
   seed check` verifies the per-loop-home kit: caveman skill deployed,
   codegraph index built, CCR store dir present, graph endpoints reachable.
4. **Savings telemetry in the journals.** The supervisor already tallies
   weighted tokens; it learns to record per-layer savings (headroom stats,
   caveman benchmark deltas, graph-hit vs file-read counts) per story. This
   also chips at the standing `DW-FU-3-6-6` mid-session-blindness finding:
   the operator finally sees spend *and* savings while the run lives.
5. **A graduated compression ladder.** Sibling to the idle ladder: as a story
   approaches its token ceiling, the supervisor can raise compression
   aggressiveness (compression-only — model movement stays with FR-51 declared
   difficulty and the Story 3.12 upward-only floor-raise, since
   [`adaptive-model-tiering.md`](<https://github.com/rxm7706/local-recipes/blob/main/archive/docs/dreams/adaptive-model-tiering.md>) forbids downgrades) before it ever
   reaches the kill threshold. Ceilings get recalibrated once baseline savings
   are measured — 50M weighted was sized for an uncompressed world.
6. **Index-freshness as a detector.** `marshal check` (the existing detector
   front door) gains codegraph/cocoindex staleness findings — advisory,
   consistent with the "never a second gate" doctrine.
7. **Review-pass economy.** Reviewer lenses receive the compressed diff plus
   graph-served context instead of re-exploring the worktree from zero —
   multiplied across four lenses per story, this is where Layer 1+2 pay twice.
   (Depth-scheduling itself stays with
   [`risk-tiered-review-depth.md`](<https://github.com/rxm7706/local-recipes/blob/main/archive/docs/dreams/risk-tiered-review-depth.md>).)

### Guardrails — what this Dream refuses to do

- **Never compress the contract.** Story specs, acceptance criteria, gate
  verdicts, and escalation context cross the wire intact. Compression applies
  to what the agent *reads along the way* and *says*, never to what it is
  *bound by*.
- **Never break the cache to save tokens.** Any layer that rewrites the prompt
  prefix violates NFR-14 and costs more than it saves. Headroom's
  live-zone-only mode is the admission ticket; a compressor without that
  property stays out.
- **Reversible or absent.** Lossy-with-retrieval (CCR) is acceptable;
  silently-lossy is not. A compressed FATAL line must always be recoverable to
  its original.
- **No BSL surprises.** The caveman input-proxy (`@caveman-ai/cli`, BSL-1.1)
  stays unpackaged and unwired unless its license is explicitly accepted;
  headroom-ai (Apache-2.0) covers the input side instead.
- **Savings telemetry is advisory.** It informs ceilings and tiering; it never
  becomes a new pass/fail verdict (Warden doctrine: no second gate).

### Gates and open questions

- **Availability gate — RESOLVED 2026-08-30:** `headroom-ai` (0.37.0, all
  platforms) and `caveman` (2.4.0 patched build 2, linux-64) are now ACTIVE in
  `pixi.toml`. The `conda-recipe-manager` `click==8.2.1` pin chain fell by
  moving crm+feedrattler into a grayskull-only `crm` feature (nothing in
  local-recipes invokes them), and caveman was rebuilt against nodejs 24 so its
  run-export coexists with codegraph's `nodejs >=24.19,<25` pin (details in
  [`pixi-candidate-currency.md`](<https://github.com/rxm7706/local-recipes/blob/main/archive/docs/dreams/pixi-candidate-currency.md>)). Layers 0–1 no
  longer degrade on the linux loop fleet. `codegraph` and `caveman` are
  linux-64-only; the loop fleet is linux, so acceptable, but the policy block
  must still degrade gracefully on other platforms.
- **Ownership seam:** Layer 4 must land as Scribe's `GraphStore` with Marshal
  as consumer — building a second graph inside Marshal would violate the
  station charters.
- **Measurement first:** before any layer ships, a pinned benchmark story
  (same story, wrapped vs unwrapped) must establish the real baseline —
  upstream claims (65%, 40–95%) are their benchmarks, not ours. The
  counterfactual harness caveman uses upstream is the model to copy.
- **Where does compression config live** when a run spans engines (bmad-loop
  multi-story vs bmad-build-auto dispatch)? The policy block must be rendered
  identically for both adapters or the savings comparison is meaningless.

### Addendum (2026-08-30) — the price sheet becomes an instrument

The operator supplied the live 2026 model/cost catalog across the four active
subscriptions (Cursor Ultra, Anthropic Claude Max, GitHub Copilot Basic,
Google Gemini API). Snapshot + analysis:
`spec-marshal-token-economy/model-economics.md`. It changes the Dream in four
ways:

1. **Spend becomes legible in dollars.** The supervisor's weighted-token tally
   can be multiplied through a *declared* price table (input / output /
   cache-read / cache-write per provider/model), so journals, `marshal status`,
   and the benchmark artifact report estimated dollars next to weighted
   tokens. Declared data only — no live billing fetch, still advisory.
2. **The difficulty ladder gets a real price ladder.** Input rates span ~50×
   (Flash-Lite/Luna-class \$0.10–0.20 → Fable-class \$10 per 1M), output ~125×.
   Feeding FR-51's tier map with cross-provider (harness, model) entries —
   easy → economy class, medium → standard class, heavy → frontier class — is
   worth more than any single compression layer, and it is the same shipped
   seam, just a richer vocabulary.
3. **Subscription pools are the cheapest marginal token.** Cursor Ultra's
   included allowance and the Claude Max plan make some tokens effectively
   pre-paid; routing prefers those pools before metered API, journals which
   pool served, and falls through when a pool is exhausted — never blocks.
   (Copilot is Pro today with a downgrade pending — a transitional fall-through
   candidate only, never a preferred pool; GitHub Pro itself is repo features,
   not a model pool.)
4. **The 0.1 cache weight is provider-specific, not universal.** Anthropic,
   OpenAI, and Gemini all publish cache-read at 10% of input — NFR-14's
   `cache_read_weight = 0.1` is exactly right there — but Cursor first-party
   models sit at 0.25–0.40. Weights derive from the declared catalog, global
   constant as fallback.

Landed as CAP-11/CAP-12 in the spec and Stories 28.10/28.11 in Epic 28. The
review-stage floor is explicitly protected under routing: review misses ship
false-greens, so economy routing never touches the review model floor.

### Addendum (2026-08-31) — Layer 4 retrieval is only as good as the graph's freshness

A comparison against Mem0's OSS memory layer (docs.mem0.ai) surfaced a real gap in Layer
4 (planning-graph retrieval, CAP-6 / Story 28.9). Mem0's consolidation pipeline retrieves
the top-k semantically similar existing memories for every new fact and hands both to an
LLM, which picks ADD/UPDATE/DELETE/NOOP — fully model-judged, no heuristics, by design (an
LLM call on every write). Scribe's own supersession (Story 2.3) is the opposite: purely
**author-declared** — a memory's frontmatter carries `supersedes: "<type>/<slug>"`, and
compile mechanically walks only those declared links. Nothing detects a node that has gone
stale because its source moved and nobody wrote the link.

That gap lands on CAP-6/Story 28.9 directly: 28.9's own AC #4 already refuses to let a
graph answer replace the verbatim story contract (spec/ACs) — but it says nothing about
the surrounding *context* a graph node supplies, which could silently serve stale planning
history with no signal.

**Resolution — a deterministic check, not an LLM one.** Porting Mem0's per-write LLM
judgment is not worth it here: scribe's memories are already structured (explicit
`supersedes:`), so the only missing signal is "did the world move since this was
compiled" — a timestamp comparison, not a judgment call. `compile_graph` (which already
walks git history for other surfaces, `_read_git_surface`) gains one more cheap field:
a node is flagged `stale: true` when its source file's latest commit postdates the node's
own `valid_from` and no `supersedes:` edge points at it. Zero LLM calls, zero new
dependency, one more field on data compile already touches every run.

This is scribe's own compile-step capability (`GraphStore`/`compile_surface`, CAP-18) —
28.9 cannot own it (its own Boundaries already forbid touching Scribe's station code
beyond the consumer side). Landing: the staleness field ships as a new scribe Epic 6
story (sibling to 6.1's graphify extra); Story 28.9 gains a fifth AC consuming it — a graph
answer whose backing node is flagged stale falls back to the epic-context file path (Story
28.8's proven fallback), never served silently. Landed as CAP-13 in the spec.

### Addendum (2026-09-09) — built, unmeasured, and asymmetric across the two engines

Epic 28 closed `done` on all 24 stories, and a code-level verification against
`main` found the machinery real: the `[context]` block and
`resolve_context_layers` in `core/policy.py`, the wrapper seam in
`core/harness_profile.py` with its byte-identical prompt-prefix guarantee, the
Genesis kit in `seed/verbs/kit.py`, the ladder and per-layer savings in
`core/supervise.py` + `supervisor/`, `core/token_economy_benchmark.py` with a
`marshal benchmark compare` CLI, and `scripts/index_freshness_check.py`. All
five instruments are pinned in `pixi.toml` and three are on PATH.

**And every layer is off.** No `[context]` block is declared anywhere — not in
`_bmad-output/policy-defaults.toml`, not in any of the eight station
`marshal-policy.toml` files, not in any of the eight rendered loop-home
`.bmad-loop/policy.toml` files. CAP-1's own contract makes an absent block mean
every layer off and behaviour byte-identical to before, so the loop today reads
and says exactly what it did before Epic 28 landed. Three independent
corroborations, none of them the ledger: no caveman skill in any loop home, no
codegraph index in any loop home, and no benchmark comparison artifact anywhere.
`index-freshness-check` reports "all indices fresh or layers off" — the second
branch, a vacuous pass.

**This closes both of this Dream's open gates, and neither closes well.**

*"Measurement first — before any layer ships, a pinned benchmark story must
establish the real baseline."* Every layer shipped; the baseline was never
established. The Dream's own Why said the ledger's token findings were all
observability gaps "because nothing has ever measured it". That is still true
after the epic that set out to fix it.

*"Where does compression config live when a run spans engines? The policy block
must be rendered identically for both adapters or the savings comparison is
meaningless."* The block **is** rendered identically — `resolve_context_layers`
is the single composition site both adapters call, exactly as CAP-1 required.
But rendering is not acting. `resolve_wire_wrap` is imported in exactly one
place, `adapters/harness_bmadbuild.py`. On `factory spin` marshal launches
`bmad-loop run` and bmad-loop launches the coding CLI, so there is no argv to
prefix (`DW-FU-28-2`). Layers 3 and 4 are epic-context compile, which is
bmad-build-auto's step 01. So the honest matrix is:

| Layer | Instrument | `factory spin` | `factory dispatch` / build-auto |
|---|---|---|---|
| output | caveman | yes | yes |
| structure-graph | codegraph | yes | yes |
| wire | headroom | **yes** (Story 33.3 — bmad-loop profile overlay) | yes |
| derived-context | cocoindex | **no** | yes |
| planning-graph | graphifyy | **no** | yes |

Wire compression now acts on both engines when the configured bmad-loop adapter
has a marshal harness ``[wrapper]`` and headroom resolves (Story 33.3). Layers 3
and 4 remain build-auto-only (epic-context compile is bmad-build-auto step 01).
Cost-sensitive derived/planning work still belongs on ``factory dispatch``; wire
is no longer spin-exclusive.

**Three ledger entries stop being incidental debt and start blocking a named
outcome**, which is what should promote them out of the ledger and into stories:

- `DW-FU-28-2` — spin is never wrapped; the fix shape is a loop-home
  launcher shim, and the entry already names the seam (`bmad-loop`'s
  `adapters/profile.py` exposes `binary` / `launch_args` / `env`, and
  `.bmad-loop/profiles/*.toml` is an overlay marshal already writes).
- `DW-FU-28-2-3` — `cli/dispatch.py` folds `read_repo_policy_defaults()`;
  `cli/spin.py` does not. A repo-wide `[context]` block would act on one engine
  and vanish silently on the other. Until that is fixed, **declare the block in
  the per-project `marshal-policy.toml`**, which both engines read.
- `DW-FU-28-2-2` — `headroom wrap` defaults to proxy port 8787 and attaches to
  a running proxy instead of starting a second, so two concurrent wrapped
  dispatches share the first launcher's CCR store. The station-in-flight guard
  makes this rare per station and does nothing for fleet-wide parallel
  dispatch, which is precisely the scale case.

**And CAP-7 could not measure it even if it were on (found 2026-09-09, later).** The five
per-layer savings getters in `adapters/harness_bmadloop.py:1875-1898` — `_get_caveman_savings`
(Layer 0), `_get_headroom_savings`, `_get_codegraph_stats`, `_get_cocoindex_stats`,
`_get_graphifyy_savings` — are stubs that
`return None` with the comment "would integrate with actual … stats when available". So the
supervisor journals a savings block whose every field is null, `marshal status` renders nothing,
and the benchmark's per-layer rows (`token_economy_benchmark.py`) have no source to read. Scribe's
side of the Layer-4 seam is real (`extras/graphify.py` writes through the `GraphStore` port;
`compile.py:736-764` flags stale nodes); the read side is five `None`s. Epic 33's Track / CAP-7
story must fill these before the on-leg benchmark means anything.

**What the enablement actually costs.** Stages 0–2 are configuration, not code:
record the off-leg on the pinned story (`1-1-marshal-conformance-smoke`),
declare the block, run `marshal seed kit` (idempotent, never fails a run), then
record the on-leg and `marshal benchmark compare`. Its equivalence gate voids
the comparison when the on-leg does not match the off-leg's verdict, gate
results and reviewer engagement — a void is the answer, not a failed test.
Ceiling recalibration (§ *What Marshal itself must grow*, item 5: "50M weighted
was sized for an uncompressed world") is downstream of that artifact and of
nothing else.

**The guard this Dream needs, learned from its sibling.**
[`adaptive-model-tiering.md`](<https://github.com/rxm7706/local-recipes/blob/main/archive/docs/dreams/adaptive-model-tiering.md>) is the same pathology
on the other cost lever — its title is literally "FR-51's model tiering is fully
wired and never turned on" — and it carries `status: realized` while its own
README row records that no story declares a `difficulty:` and no project
populates a real tier map. It was marked realized as chain bookkeeping when the
code landed, not when the saving arrived. **This Dream is not `realized` when
its next epic closes. It is `realized` when a benchmark artifact reports a
measured saving on a real story.** Nothing else counts.

Landing: `bmad-correct-course` on `spec-marshal-token-economy` (`ready`, so it
takes the correction) mints marshal **Epic 33** — Epic 32 is the highest today,
30 and 31 sit in backlog — carrying the enablement sequence plus the three
entries above. Same shape as the 2026-09-02 red-team correction that minted
steward Epic 40. No new Dream: this chain already asked both questions.

### Fold (2026-09-16) — the token-savings Dreams come home

Operator-ruled consolidation: every Dream whose center is the cost of an
iteration folds into this one, so there is **one starting point** for the
whitepapers, the analysis, and the continuity. The fold line (operator,
2026-09-16): **same owner + same center + same lifecycle** — what rides
this Dream but is not inside it is named in § *Seams* below. The five
folded files stay in place as `archived` pointers so kinship links and
Spec `owner-dream` links keep resolving; **their Specs stay live and
remain the contracts** — archiving the Dream tier never retires the chain
below it.

#### Folded — the session path (from `token-economy-claude-session-path`, `dreamt`)

The seed: the factory already knows how to make an iteration cheap, but
the session that costs money never uses the kit — interactive Claude pays
the always-on doc tax and every station's policy prefers Cursor, which
cannot take the wire wrap (28.29). The Dream asked for a **session path**,
not a second compressor. Seeded 2026-09-16 and put through a deep
analysis + adversarial review the same day; the full decision record is
the Spec's ten-entry memlog. The load-bearing conclusions:

- **Token savings is not one currency.** Claude meters billed tokens
  (with prompt-cache discounts); Cursor meters subscription quota;
  Copilot premium requests; Gemini rate limits; Devin ACUs. A layer that
  helps one currency can be irrelevant to another — every saving is
  reported in its harness's own currency, never a blended number.
- **The five layers are two economies.** The shared substrate (codegraph,
  cocoindex distills, planning graph, team memory) amortizes
  understanding *once* and serves every harness — **primary**. The
  per-harness wire (headroom, caveman) is capability-bound residue —
  secondary. The biggest gap is sharing cache, knowledge, and memory
  across every agent, harness, and model (operator, 2026-09-16).
- **The substrate's four gaps:** it does not *travel* (cloud agents get
  a bare clone — no bootstrap path); *write-back* is harness-fragmented
  (`scribe capture` is the neutral ritual, habitual in none); the only
  portable cache is a canonical digest-pinned context bundle; *freshness*
  is the trust boundary (Scribe owns it). Centralization caveat: shared
  knowledge centralizes error — provenance, the freshness SLA, and
  capture hygiene are the mitigations.
- **The three open questions answered:** dispatch is the *measured* path,
  interactive a documented convenience path on the same instruments;
  repo-default `[context]` with wire as a capability-aware `"auto"`
  (resolves against the harness profile's declared `[wrapper]`; per-
  station only as force-override); thinning `CLAUDE.md`/`AGENTS.md`
  deferred to a later Dream.
- **The multi-harness matrix:** claude = full kit; copilot = full kit
  once one `[wrapper]` story lands (headroom ships `wrap copilot`);
  cursor = harness-agnostic layers only — intended economics (cursor-first
  dispatch *is* the spend avoidance), not a gap; gemini/devin resolve by
  the same `auto` rule. Correction recorded: the output layer is
  multi-harness (caveman ships 21 targets).
- **The sharpest open risk:** the prompt-cache collision — a wire
  compressor rewriting prefixes unstably can cost more in lost cache
  discounts than it saves. Claude wire savings stay *unverified* until
  per-layer benchmark legs with cache-hit rates exist.

Status at fold: `dreamt`; Spec seeded `draft`, then the operator ruled
**no satellite Specs** — so the contract folded too:
`spec-token-economy-claude-session-path` is `superseded` (same day it was
seeded), its capabilities re-minted as `spec-marshal-token-economy`
**CAP-19..CAP-24** (substrate, silent saves, front door, session path,
per-layer benchmark legs, matrix truth), dispatch home **marshal Epic 46**
(46.1–46.10). The superseded folder keeps the eleven-entry decision
memlog; `owner-dream` stays on this archived file so the chain link
resolves (the satellite-fold precedent).

#### Folded — adaptive model tiering (from `adaptive-model-tiering`, `realized`)

FR-51's difficulty→model chain (Story 6.1) shipped complete and was never
fed — the Dream that taught this one its realized-guard. Corrected
2026-09-09: CAP-1 *is* fed (57 story specs across six stations declare
`difficulty:`; two stations carry real `model_tier_map` tables; two live
dispatches resolved tiered models). The live gap: six of eight stations
have no tier map and journal `"model": null`, and CAP-2's retry-triggered
floor-raise is unreachable on the dispatch engine — both halves are
Story 33.6. Status at fold: `realized` (2026-08-14 chain bookkeeping;
facts corrected 2026-09-09).

#### Folded — the Cursor-native tier map (from `cursor-native-tier-map`, `specified`)

The four-verb campaign runs in Cursor, so `model_tier_map` must tell the
truth about that plane: easy/medium/heavy name Cursor-native models on
the Ultra pool in the explicit `{ harness, model }` form, so a Cursor
string never lands on `claude --model` again. Story 33.15 remaps all
eight stations. Unattended drain stays off until the wire question is
separately proven. Status at fold: `specified` (Spec
`spec-cursor-native-tier-map`).

#### Folded — tier routing fails safe (from `dispatch-tier-routing-fails-safe`, `realized`)

The 2026-09-12 incident: a bare-string tier entry (`composer-2.5-fast`,
Cursor-only, all eight stations) resolved to no harness, so the base
claude adapter launched with a Cursor model string and crashed instantly
— zero tokens, reported only as "deferred." Realized the same day:
`render_policy_toml` cross-checks each tier-mapped stage's model against
the declared cost catalog (`provider_declaring_model`) and skips a
cross-provider mismatch; `resolve_stage_candidate` no longer fabricates
an answer; dispatch's own path carries the identical guard
(`MRS-DISP-043`); all eight stations reverted to the sonnet/opus
baseline. The standing rule: a cost-tier override exists only once a
second harness is verified live, in explicit `{harness, model}` form,
rolled out one station at a time.

#### Folded — interactive routing (from `bmad-cursor-interactive-routing`, `specified`)

BMAD from inside Cursor's own chat, not just headless dispatch. The
CAP-1 probe **passed** 2026-09-15 (Cursor Agent chat invoked the Task
tool; context-free subagents work in-turn). CAP-2 is committed:
mechanical `.mdc` generation from the `SKILL.md` files as a maintained
pixi task plus a drift detector — never a hand-maintained fork. CAP-3b
remains the residual HALT on a no-Task surface. Dispatch home: marshal
Epic 45. Status at fold: `specified` until that epic ships.

### Seams this Dream rides (not inside, and why)

The fold line is center, not dependency — fold-by-dependency has no
stopping rule (33.5 would pull in `risk-tiered-review-depth`, 33.8
`marshal-parallel-dispatch-fanout`, the Hub track `intelligence-hub`,
and the closure is half the marshal project). These seams are named so
the boundary never has to be re-litigated:

- [[run-state-one-publisher]] — the publishing seam this Dream's savings
  telemetry (CAP-7 / Story 33.4) rides. Same owner, different center:
  it publishes *all* run state, not savings; it is the dream-first
  ruling's exemplar with its own `ready` Spec.
- [[pixi-candidate-currency]] — the five instruments' pin home.
  doctor-owned, `realized`, a perpetual currency practice — the wrong
  lifecycle to import into a Dream whose realized-guard is a measured
  saving.
- The Scribe substrate — [[scribe-knowledge-layers]],
  [[scribe-recall-modes]], [[scribe-planning-pointers]],
  [[scribe-graphify-nightly-currency]],
  [[scribe-code-navigation-owner]] — the knowledge layers this Dream's
  substrate-primary economy *is*. scribe-owned by charter: *Marshal
  consumes it, Scribe owns it* (§ Guardrails' ownership seam).
- [[pyforge-marshal]] (the station) · [[adaptive-model-tiering]]'s
  sibling lesson already cited above · [[risk-tiered-review-depth]]
  (review depth scheduling) · [[durable-runs]] ·
  [[marshal-parallel-dispatch-fanout]] · [[intelligence-hub]].

### Realization log

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
  [`marshal-dependency-aware-dispatch.md`](<https://github.com/rxm7706/local-recipes/blob/main/archive/docs/dreams/marshal-dependency-aware-dispatch.md>).
- **2026-09-01** — Dispatch-autonomy hotfixes + Epic 28 artifact catch-up (`90c5a28bd6`).
- **2026-09-09** — Code-level verification against `main`: Epic 28's machinery is real
  and complete, and every layer is off — no `[context]` block is declared in any policy,
  repo, project or rendered. Both of § *Gates and open questions*' gates closed against
  the evidence: the measurement-first gate was bypassed (no benchmark artifact exists),
  and the cross-engine question is answered in the negative (the block renders
  identically on both adapters, but only dispatch/build-auto can act on the wire,
  derived-context and planning-graph layers). Recorded as the addendum above, with the
  `realized` guard learned from [`adaptive-model-tiering.md`](<https://github.com/rxm7706/local-recipes/blob/main/archive/docs/dreams/adaptive-model-tiering.md>).
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
  [`adaptive-model-tiering.md`](<https://github.com/rxm7706/local-recipes/blob/main/archive/docs/dreams/adaptive-model-tiering.md>).
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

## 2026-10-26 — One front door — Marshal drives everything BMAD installs (folded from one-front-door)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 111.1). The body below is `docs/dreams/one-front-door.md`, verbatim, with its headings demoted one level and its 2026-09-16 fold banner left out; the file moved to `archive/docs/dreams/one-front-door.md`.*

> **Superseded 2026-08-02 (dream consolidation).** Fully decomposed into `spec-pyforge-marshal`
> and the real PRD as FR-65 (`marshal check` — the detector registry through a single command,
> context resolved once per invocation) — see
> [`docs/dreams/pyforge-marshal.md`](pyforge-marshal.md). This Dream's other candidate verbs
> (`run`/`status`/`land`) were found convergent with already-specified FRs (FR-9/10/11 `factory
> spin`, FR-59/60 `land`) during the 2026-08-01 decomposition and correctly did not get new FR
> numbers. See `spec-one-front-door` for the retirement record.

## One front door — Marshal drives everything BMAD installs

> **Draft for refinement.** Seeded 2026-07-31 on an operator call; the inventory
> below is derived from the tree, but the *boundaries* — what Marshal drives, what
> it merely routes to, and what it should never touch — are open. Edit freely.

### The Dream

The Charter says **execution has one owner: Marshal**. Today that is true of
accountability and false of interface. What is actually installed is a toolbox of
**11 packages, 51 BMAD skills, 16 Skill Forge skills, 10 detectors, an engine, a
dashboard and a multi-project switch** — and the way you use it is to remember
which one you need, in what order, with which project active.

The Dream is that **one front door drives all of it**. Not a new tool: a
*conductor* for the tools already here, holding the context they each need and
that a human currently holds in their head.

> A toolbox is not a factory. The difference is that somebody knows the order.

### What Marshal would drive — the inventory

Derived from the tree 2026-07-31. **This is the list to argue with.**

| # | Installed surface | What it is | Marshal's role |
|---|---|---|---|
| 1 | **`bmad-loop` 0.9.0** | The engine — run/resume/resolve/sweep/status/attach/stop/clean | **wrap** (never absorb) |
| 2 | **`bmad-method` 6.10.0** | 51 skills: planning · dev · review · sprint · personas · research · docs | **route + context** |
| 3 | **BMB** `bmad-builder` 2.1.0 | Author custom agents & workflows | route |
| 4 | **TEA** `…test-architecture-enterprise` 1.19.1 | Risk-based test strategy | route |
| 5 | **CIS** `…creative-intelligence-suite` 0.2.1 | Brainstorming, design thinking | route |
| 6 | `bmad-manticore` · `bmad-labs-skills` · `bmad-utility-skills` · `bmad-method-wds-expansion` · `bmad-module-template` | Installed, largely unexercised here | **triage — keep or drop?** |
| 7 | **Skill Forge** — 16 `skf-*` skills | Skill authoring, campaigns, audits | route |
| 8 | **`bmad-dashboard` 1.2.2.dev0** + `docs/dashboard/` | The Guildhall board | own (it reports Marshal's runs) |
| 9 | **Multi-project wiring** — `bmad-switch`, marker, two symlinks, six-layer config | Which project is active | **own — it is already Marshal's** |
| 10 | **Loop homes** — `bmad-loop-worktree`, `marshal init/homes` | Isolated worktrees per station | **own — shipped** |
| 11 | **10 detectors** + the derived registry | drift · chain · surface · story-status · stall · layout · unpushed · … | own (invoke; Doctor judges Marshal's row) |
| 12 | **Tier layout** — `docs/dreams/`, `_bmad-output/projects/<station>/` | Dream → Spec → chain → stories | own |
| 13 | **Repo gates** — linter, `maintenance` label, `environment.yaml` sync, PR lifecycle | What landing requires | own ([[pr-lifecycle]]) |
| 14 | **`conda-forge-expert` 8.81.0** | The packaging craft (Rule 1: any BMAD agent doing conda work must wield it) | route — **Mason's craft, not Marshal's** |

### Why now

This session is the argument. Driving *one* fleet run end to end meant hand-invoking:
`bmad-loop run` · `bmad-loop status` · `tmux capture-pane` · seven detectors ·
`dashboard-gen` · `dashboard-watch` · `spec-surface-check --write-baseline` ·
`git push` across nine homes · `gh pr create/edit/merge` five times.

Every one is documented. None is composed. The operator asked "is marshal's work
saved?" and the honest answer required four separate commands — because no single
thing knows what a run *is*.

And the failure modes were all seams: `dashboard-watch` was never started because
nobody thought of it; the push window reopened because nothing owned it; #170
merged broken because the landing path asked nothing. **A front door is where
seams go to be owned.**

### The frontier — and the open questions

- **`marshal <verb>` as the composed surface.** Candidate verbs, to argue with:
  `run` (drive a story/epic — wraps the engine) · `status` (one answer across
  fleet, board, detectors, unpushed work) · `check` (the detector registry) ·
  `land` ([[pr-lifecycle]]) · `switch`/`homes` (shipped) · `doctor` (delegate).
- **Route, do not re-implement.** The moment Marshal *contains* a skill instead of
  invoking it, `wrap, never absorb` has been broken one level up. Unresolved:
  where exactly is that line for the 51 skills?
- **Context is the product.** The value is not shorter commands, it is that the
  active project, loop home, policy layer and story key are supplied *once*.
- **Triage row 6.** Five installed packages this repo barely exercises. Keep,
  wrap, or remove? An unexercised dependency is surface area with no owner.
- **Row 14 is a boundary test.** CFE is Mason's craft. Marshal routing to it is
  fine; Marshal *knowing conda* is not — §4, *each works one craft, not all*.

### What this is not

[[genesis-installer]] **installs** this surface — greenfield `init`, brownfield
`adopt`, the write guard, managed regions. It is `specified` with a full chain.
This Dream is the **runtime** half: once installed, who drives it. Install-time
and run-time are different jobs, and merging them would give one Dream two.

Nor is it a replacement for any tool listed above. Every row keeps its owner and
its interface; the front door composes them.

### Kinships

[[genesis-installer]] (installs what this drives — the two halves of the same
promise) · [[pyforge-marshal]] (the station; this is its CLI cadence made real) ·
[[pr-lifecycle]] (the last mile, one verb behind this door) · [[durable-runs]]
(a seam a front door would own) · [[agent-portability]] (the door must not assume
one coding CLI) · [[pyforge-charter]] (§ Execution Doctrine — *execution has one
owner*).

### Realization log

- **2026-07-31** — Dream seeded (operator call: "Marshal should install and be an
  orchestrator and wrapper around all that's installed around BMAD"). The
  *install* half was found already owned by [[genesis-installer]] (`specified`,
  full chain), so this Dream is scoped to the **runtime** half only, and the
  boundary is stated above rather than left to be discovered. Inventory derived
  from the tree at seeding: 11 conda packages, 51 `bmad-*` skills, 16 `skf-*`,
  10 detectors, 9 projects. Left deliberately open for operator refinement: the
  verb list, the route-versus-contain line, and the row-6 triage.

## 2026-10-26 — PR lifecycle — a story lands itself (folded from pr-lifecycle)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 111.1). The body below is `docs/dreams/pr-lifecycle.md`, verbatim, with its headings demoted one level and its 2026-09-16 fold banner left out; the file moved to `archive/docs/dreams/pr-lifecycle.md`.*

> **Superseded 2026-08-02 (dream consolidation).** Fully decomposed into `spec-pyforge-marshal`
> and the real PRD as FR-59 (landing rules are declared policy) and FR-60 (`marshal land` —
> idempotent open/label/wait/merge/retire/resync) — see
> [`docs/dreams/pyforge-marshal.md`](pyforge-marshal.md). See `spec-pr-lifecycle` for the
> retirement record.

## PR lifecycle — a story lands itself

### The Dream

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

### Why now — one session's evidence

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

### What is real

- **The engine lands on the station branch.** `bmad-loop` merges each story
  worktree into `loop/<slug>` with a recorded subject. That much is automatic
  and durable.
- **From station branch to `main` is entirely manual.** No tooling owns it.
- **The pieces exist, unassembled:** `gh` is provisioned, the checks exist
  (`linter`, `detectors`), the merge-subject contract is already Marshal's
  (story 1.2), and `marshal config` already knows how to compose and record a
  policy — which is where landing rules belong.

### What is real, part two — the last mile has no idea a run is happening (measured 2026-08-09)

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

### The frontier

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

### What this is not

Marshal's Epic 4 (*landing with a durable paper trail*) is about the record a
landing leaves. This is about **performing** the landing at all. They meet, and
the record is worthless if the act is still manual.

It also does not touch the engine — **wrap, never absorb** holds. `bmad-loop`
deliberately leaves this gap open; Marshal fills it *around* the engine, in the
supervisor, exactly as it does for provisioning and teardown.

### Kinships

[[pyforge-marshal]] (this resolves an open question its Spec parked —
see the log below) · [[durable-runs]] (both are about work surviving the gap
between stages; that one saves it, this one lands it) ·
[[fidelity-enforcement]] (the required-checks decision is a gate question, and
today's advisory CI is why "merged green" and "actually green" can differ) ·
[[pyforge-doctor]] (holds the verdict on Marshal's own rows) · [[pyforge-charter]].

### Realization log

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
  rather than as a new Dream — this IS the last mile, it just turns out the last mile has
  to know whether anyone is still driving on it.

- **2026-07-31** — Dream seeded (operator call): **"Marshal should own the PR
  lifecycle."** This **resolves open question #10 in `spec-pyforge-marshal`**,
  which asked whether PR-lifecycle automation belongs to Marshal, upstream, or
  the provisioning station, and recorded it as *currently a non-goal*. The Spec's
  non-goal must therefore be amended — re-derived from its memlog, not
  hand-patched — and this Dream is the input for that. Evidence at seeding: five
  PRs hand-driven in one session, one of which (#170) merged a real detector
  break because nothing in the landing path asked. Constraint carried forward
  unchanged: **wrap, never absorb** — the engine keeps dev/verify/review/commit.

## 2026-10-26 — One primitive, one home — the shared floor under eight stations (folded from pyforge-core)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 111.1). The body below is `docs/dreams/pyforge-core.md`, verbatim, with its headings demoted one level; the file moved to `archive/docs/dreams/pyforge-core.md`.*

## One primitive, one home — the shared floor under eight stations

### The Dream

Eight stations, one namespace, and the same five primitives written eight times.
Not by accident and not by neglect — by a doctrine that was right about the thing
it was protecting and silent about the thing it wasn't. Stations are
independently conda-installable and deliberately do not import each other, so
every station that needed to write a file atomically wrote its own atomic write.
The copies know they are copies: their docstrings say *"mirrors `state.write`"*
and *"identical shape."*

The Dream is a **leaf**: one small package, pure stdlib, that no station imports
*from another station* — it sits under all of them, depended on by each and
coupling none. Adding a station stops meaning re-deriving the floor. Fixing a bug
in the floor stops meaning finding twenty copies and hoping.

The counterweight is real and is the reason this Dream is narrow: a shared
package that grows station-specific knowledge becomes exactly the coupling the
architecture has spent eight stations refusing. **Leaf or nothing.**

### What is real — the census, measured

Counted directly against the tree on 2026-08-08, not inherited from a summary:

| Primitive | Copies | Spread |
|---|---|---|
| **Atomic write** (`os.replace` + tmp-in-dir) | **20 files** | 6 of 8 stations — herald 6, atlas 5, marshal 5, steward 2, scribe 1, warden 1; doctor and mason have none |
| **Verdict / exit-code lattice** | **5** | atlas, doctor, herald, marshal, warden each declare their own |
| **Report envelope schema** | **3** | warden 22 KB · doctor 4.5 KB · marshal `envelope.v1.json` 4.3 KB — one shape, three schemas |
| **Station roster** | **3 explicit + 1 implicit** | `bmad_drift_check.STATIONS` (canonical, imported by `generate.py`) · `herald/progress.py` · `Sidebar.jsx` · plus `PROJECT_SOURCES` keyed by station |
| **Subprocess invocation** | **15 modules** | marshal 7 · steward 3 · herald 2 · doctor 1 · scribe 1 · warden 1 |
| **Base exception root** | **0 shared** | herald and mason each invented one; warden/marshal/atlas scatter 12–13 `*Error` classes with no common root |

The duplication is genuine and, for atomic write and the verdict lattice,
mechanical: zero semantic divergence, self-documented sameness. Doctor's
`verdict.py` literally describes itself as *"a subset of `pyforge.warden`'s
frozen `{0, 1, 2, 130}`"* — a dependency asserted in a docstring because there
was no package to express it in.

#### Three corrections to the source research

This Dream's census supersedes the figures in
`_bmad-output/projects/pyforge-marshal/planning-artifacts/research/technical-pyforge-unification-2026-08-08.md`
§ 7, which were the trigger for capturing it. Recorded because the third one
inverts that document's single strongest recommendation:

1. **Atomic write is 6/8 stations, not 8/8** — doctor and mason have zero copies.
2. **The report envelope is 3 schemas, not 2** — marshal's `envelope.v1.json` was
   not counted.
3. **Warden is not the subprocess outlier — Marshal is.** The research reads
   *"warden is the outlier: ~20 modules import `subprocess` with no sole-site
   guard,"* and calls fixing it *"the one item worth doing even if nothing else
   is."* That counted **mentions**, not imports. Exactly **one** warden module
   imports `subprocess` (`engines.py`), and its call site is annotated
   `# noqa: S603 — argv list, no shell; the sole seam`. Warden already has the
   guard the research says it lacks. **Marshal**, at 7 importing modules, is the
   station with the widest ungated surface — and it is the station that owns this
   Dream, which is the more uncomfortable finding and the reason it is written
   down here rather than quietly fixed.

### What it looks like when real

- One package under `src/shared/packages/`, pure stdlib, importable by any
  station and importing none of them.
- Atomic write has one implementation; the 20 copies are **retired in the same
  story that extracts them**, never left as a second path.
- The verdict lattice is declared once with per-station domain restriction, so
  doctor's `{0, 2, 130}` is expressed as a real narrowing of warden's
  `{0, 1, 2, 130}` rather than asserted in prose.
- One report-envelope schema; warden's richer fields are an extension of it, not
  a rival.
- The station roster is data with one owner, and adding a station is one edit.
- One exception root, so `except PyforgeError` is a sentence anyone can write.
- A meta-test per primitive fails the build if a second implementation appears —
  the sole-ownership pattern marshal and warden already use.

### Constraints

- **Leaf or nothing.** Pure stdlib; no station imports another station through
  it. If it ever needs a station's type, the extraction was wrong.
- **Retire the copy in the story that extracts it.** Atlas's Kedro migration is
  the cautionary precedent on record: ~29 k LOC merged and marked `shipped` while
  the 8,902-LOC legacy module stayed the live runtime, because the rebuild had no
  migration step. An extraction that leaves the copies standing has done nothing
  and claimed something.
- **Stations stay independently conda-installable.** A shared floor must not
  become a distribution constraint.
- **Extraction order follows the census**, heaviest and most mechanical first:
  atomic write → verdict lattice → report envelope → roster → exceptions →
  subprocess guard. Subprocess is last on purpose: two designs genuinely differ
  (doctor's `cli_bridge.run_cli_json` versus marshal's `ProcessPort`), and
  steward *deliberately* propagates raw `CalledProcessError`. That is a design
  reconciliation, not a copy-paste consolidation.

### Non-goals

- **Not a framework, not a plugin system, not a service.** Six primitives with a
  measured copy count each.
- **Not a home for anything with one caller.** A primitive earns its place by
  existing two or more times already.
- **Not a station.** It has no Dream of its own to deliver, no verdict, no
  station in the roster — it is a dependency, and Charter §5's roster stays at
  eight.
- **Not a rewrite of working tests.** Stations adopt the floor as they touch the
  code, except where the extracting story retires a copy outright.

### The frontier

- Whether `pyforge-testing-kit` (the testing charter's CAP-3, unbuilt) is a
  second leaf or a module of this one.
- Whether the roster belongs here or stays in the detector that already owns it —
  it is the one census entry whose canonical home already exists.

### Realization log

- **2026-08-08** — Captured during the Marshal planning rewrite, at the moment
  the unification research named as the window: *"decide `pyforge-core` scope
  now, before S-7.1 opens — it changes two Epic-7 stories."* Epic 7's stories
  7.2 (error taxonomy and exit codes) and 7.3 (the fs-write primitive and the
  never-write guard) would otherwise have minted copy #21 of atomic write and
  copy #6 of the verdict lattice inside the very rewrite meant to consolidate.
  Census re-measured directly rather than inherited; three figures corrected,
  including one that reverses the research's strongest single recommendation
  (see above). Owner `marshal` under the build-line/estate seam ratified the same
  day: the shared floor is factory machinery, not the estate beneath it.

## 2026-10-26 — Dream — PyForge Marshal: Loop Orchestrator (folded from pyforge-marshal-loop-orchestrator)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 111.1). The body below is `docs/dreams/pyforge-marshal-loop-orchestrator.md`, verbatim, with its headings demoted one level and its 2026-09-16 fold banner left out; the file moved to `archive/docs/dreams/pyforge-marshal-loop-orchestrator.md`.*

> **Superseded.** This Dream restates scope already fully governed by
> [`docs/dreams/pyforge-marshal.md`](pyforge-marshal.md) (status: realized) and its
> `spec-pyforge-marshal` → PRD (FR-1..FR-58) → Architecture (39 ADs) → Epics (6 epics /
> 50 stories) chain. Its own "Realization" list (Provisioned Loop Homes, Deterministic
> Gates, Supervised Runs, Durable Durability, Batch Landing) maps 1:1 onto
> `spec-pyforge-marshal`'s CAP-1/CAP-3/CAP-2/CAP-4, and its own Acceptance criterion
> references "all 6 epics (50 stories)" — the existing epics, not new ones. Created
> 2026-08-02 in a bulk commit later found to contain fabricated content (false
> migration claims, boilerplate test scaffolding); retired same day rather than
> spec'd as new work. See `spec-pyforge-marshal-loop-orchestrator` for the retirement
> record.

## PyForge Marshal — Loop Orchestrator

### Vision

**Marshal** is the loop orchestrator — the deterministic, offline-by-default execution engine for unattended factory runs. It provisions isolated loop homes, supervises long-running jobs, enforces gates, and lands results durably.

**The ask**: Build an orchestrator that enables hands-off, auditable, deterministic execution of complex multi-story workflows with zero silent failures and full recovery from crashes.

### Problem

- **Runs are fragile.** A long story crashes at hour 3; the operator rediscovers it manually. Did it checkpoint? Can it resume? No one knows.
- **Isolation is weak.** Two loops on the same machine can interfere. Shared temp dirs, port collisions, credential leakage.
- **Deadlines are hopeless.** No budget ceiling. One runaway task starves the rest. Operator kills everything manually.
- **Evidence disappears.** A run completes; the operator restarts the machine. The journal, the findings, the story specs are all gone.
- **Landing is error-prone.** Merge subjects don't conform. Specs aren't promoted. Feeds are stale. Manual cleanup needed.

### Realization

**Marshal** delivers:

1. **Provisioned Loop Homes** — Each loop gets an isolated, policy-composed, preflight-verified place to run. Two homes can't interfere; isolation is provable.

2. **Deterministic Execution** — No timestamps in logic paths, no random seeds, no "good enough" approximations. Same story → same output, always. Operators trust the results.

3. **Supervised Runs** — A supervisor sidecar watches every detached run: sends heartbeats, detects idle strands, enforces token budgets, escalates failures. No silent hangs.

4. **Durable Durability** — Tier-3 store via backlink survives machine restart. Every story spec promoted to git automatically. Run journal append-only and indexed. Zero data loss.

5. **Deterministic Gates** — Independent gate evaluation: standalone CLI, project-scoped, no LLM influence. Verdict never false-greens. Evidence records what ran and why.

6. **Batch Landing** — Stories land in waves: automatic spec promotion, merge-subject conformance checked, feeds refreshed, branch cleanup triggered. One command; full auditability.

### Success Criteria

- ✅ **Isolation**: Two loop homes provably isolated (no process leakage, no credential sharing)
- ✅ **Determinism**: Same story → byte-identical output; determinism verified in CI
- ✅ **Uptime**: Supervised runs survive machine restarts; zero data loss
- ✅ **Reliability**: 0 false-green verdicts over 100+ gate evaluations
- ✅ **Velocity**: Full 50-story run completes in <13 weeks single-builder; >80% parallelizable
- ✅ **Auditability**: Every decision logged, every finding code registered, every action attributed

### Acceptance

Marshal is done when:
1. All 6 epics (50 stories) implemented and passing tests
2. Isolated loop homes verified with two concurrent runs on same machine
3. Determinism proven: same story → identical output over 50+ reruns
4. Supervised runs survive 10+ crash-and-recover cycles with zero data loss
5. Batch landing tested: 20-story wave lands cleanly with all specs promoted
6. Integration with Warden gates verified: verdicts never false-green

## 2026-10-26 — Dream — PyForge Testing Charter: Systematic Testing for the Guild (folded from pyforge-testing-charter)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 111.1). The body below is `docs/dreams/pyforge-testing-charter.md`, verbatim, with its headings demoted one level and its 2026-09-16 fold banner left out; the file moved to `archive/docs/dreams/pyforge-testing-charter.md`.*

> **Narrative consolidated 2026-08-02 (dream-level only).** This Dream's narrative now lives
> in [`docs/dreams/pyforge-marshal.md`](pyforge-marshal.md) under "The frontier." **Its
> downstream Spec stays fully live and untouched**: `spec-pyforge-testing-charter` (5
> capabilities) is real — CAP-1 and CAP-2 are shipped (verified on disk, not this Dream's own
> claims, which this Spec found partly inaccurate when it verified them: neither herald nor
> warden had complete test architecture, and six other stations already had real pytest
> coverage this Dream's "no systematic test architecture at all" line missed). CAP-3 (a shared
> `pyforge-testing-kit` package) and CAP-4 (a CI coverage gate) are real, unbuilt, and not yet
> decomposed to a PRD. Only this top-level Dream file consolidates; the Spec and its
> `station-tea-status.md` companion were not merged, retired, or reworded.

## Dream: PyForge Testing Charter — Systematic Testing for the Guild

**Vision**: Test architecture is a first-class citizen in the Dream-to-Code pipeline. All 8 PyForge stations inherit the same systematic testing framework, eliminating duplication and ensuring quality gates are universal.

---

### The Problem

Testing is invisible and ad-hoc across the PyForge stations.

- **Herald** built test architecture manually (1,895 lines) — a masterpiece, but unrepeatable
- **Atlas, Warden, Doctor, Mason, Scribe, Steward** have no systematic test architecture at all
- **Each team re-invents** fixtures, test frameworks, quality gates — massive duplication
- **No visibility** into test coverage, risk assessment, or readiness per station
- **No automation** — test architecture generation is manual work per project
- **No guild standard** — everyone interprets "testing" differently

**Result**: Testing is a bottleneck, not a strength. We ship features without confidence.

---

### The Vision

Test architecture flows from the spec just like PRD, architecture, and epics do.

**One flow:**
```
Dream → Spec → PRD → Architecture → Epics → Stories → TEST ARCHITECTURE → Development
```

**One framework** (BMAD TEA + Playwright):
- CLI testing: subprocess spawning, output capture, exit codes
- Web testing: Page Object Model, responsive design, interactive flows
- Integration testing: cross-layer coordination, webhook simulation, state transitions
- Async testing: time mocking, cron scheduling, delayed operations
- Visual testing: screenshot diffing, layout regression
- Performance testing: latency benchmarks, throughput tracking

**One reference** (Herald):
- 1,895-line canonical test architecture
- 9 Playwright patterns
- Risk assessment (11 high, 14 medium, 7 low)
- Test matrix (54 test suites across 18 stories)
- Quality gates (unit >80%, integration >70%, e2e happy-path + 3 risks)
- Reusable pattern appendix (how to apply to other stations)

**One shared foundation** (pyforge-testing-kit):
- CLI runner fixtures (subprocess + output capture)
- Web page objects (header, tabs, sidebar, filters)
- Database factories (progress, claim, notice records)
- Auth/HTTP/time mocks
- Test data builders (fluent API)

**One automation** (bmad_tea_playwright.py):
- Input: epics-with-stories.md + ARCHITECTURE-SPINE.md
- Output: test-architecture.md + playwright.config.ts + pytest.ini + tests/ scaffold
- One command per project (no manual re-work)
- 30 seconds per station

**One guild standard** (test-charter.md):
- All 8 Smiths' testing responsibility
- Quality gates per station
- Phase 1-4 roadmap (30 min fleet deployment)
- Risk-based testing principles

---

### The Realization

**When this dream is real:**

1. ✅ **Herald test architecture complete** — canonical reference, 1,895 lines with Playwright patterns
2. ✅ **Automation script created** — bmad_tea_playwright.py generates test architecture one-command-per-project
3. ✅ **Guild testing charter defined** — all 8 Smiths' testing responsibility, quality gates, Phase 1-4 roadmap
4. ⏳ **pyforge-testing-kit created** — shared fixtures package (CLI runner, web pages, database, auth, mocks)
5. ⏳ **Applied to all 8 stations** — atlas, doctor, marshal, mason, scribe, steward, warden (batch run, 30 min)
6. ⏳ **Development teams execute** — each story includes pytest unit + Playwright e2e tests
7. ⏳ **Dashboard tracks** — test-architecture status per station (complete/ready/pending)
8. ⏳ **CI gates enforce** — unit >80%, integration >70%, e2e pass before merge

---

### The Promise

**For developers:**
- Clear test matrix (which tests to write for each story)
- Reusable fixtures (no re-implementing CLI runners, page objects, DB factories)
- Playbook patterns (9 proven patterns for different test scenarios)
- Fast feedback (pytest unit tests run in seconds, Playwright e2e in <2s per scenario)

**For architects:**
- Uniform quality gates (every station targets unit >80%, integration >70%, e2e happy-path + 3 risks)
- Risk-based testing (high-risk items get 2+ test layers)
- Scalability (add new stations without overhead — same pattern applies)
- Traceability (test matrix ties back to stories, architecture decisions to tests)

**For the factory:**
- No duplication (write once, inherit everywhere)
- Determinism (same input → same test architecture every time)
- Confidence (all 8 stations ship with the same quality standard)
- Speed (one-command per project, 30 min for entire fleet)

---

### The Mottos (Guild Testing Responsibility)

Each Smith owns their testing:

| Smith | Motto | Testing Responsibility |
|-------|-------|------------------------|
| 🎺 Herald | Capture. Illustrate. Proclaim. | Visibility testing (CLI, web UI, proclamation) |
| ⚔️ Marshal | Enforce. Guard. Run the line. | Governance testing (policies, composition) |
| 🗺️ Atlas | Map. Know risks. Set foundation. | Intelligence testing (discovery, mapping, risk) |
| 🛡️ Warden | Halt. Clear axes. Protect perimeter. | Security testing (gates, compliance, validation) |
| 🧱 Mason | Orchestrate. Bridge worlds. Ship deterministically. | Build testing (orchestration, dual-ship) |
| 🏥 Doctor | Check vitals. Diagnose. Rank what matters. | Quality testing (diagnostics, prioritization) |
| 📖 Scribe | Capture. Keep graph. Answer from memory. | Memory testing (documentation, capture, recall) |
| 👑 Steward | Supply estate. Guard credentials. Ensure reliability. | Operations testing (provisioning, access, reliability) |

---

### The Roadmap (4 Phases)

#### Phase 1: Foundation ✅ COMPLETE
- Herald test architecture (1,895 lines)
- Automation script (bmad_tea_playwright.py)
- Guild testing charter (test-charter.md)
- Pattern documentation (embedded in test-architecture.md)

#### Phase 2: Shared Infrastructure ⏳ NEXT SPRINT (6-8 hours)
- Create pyforge-testing-kit shared package
- Add pixi task: `pixi run tea-playwright-all`
- Test full cycle on pyforge-atlas

#### Phase 3: Fleet Deployment 📋 2-3 WEEKS (30 min execution)
- Run script on all 8 stations (atlas, doctor, herald, marshal, mason, scribe, steward, warden)
- Verify consistency
- Update dashboard with test-architecture column

#### Phase 4: Development Integration 🚀 ONGOING
- Each station implements stories with tests
- CI gates enforce coverage (unit >80%, integration >70%, e2e)
- Dashboard tracks test status per station

---

### The Metrics (Success Looks Like)

**Per Station:**
- ✅ test-architecture.md generated (risk assessment, test matrix, scenarios, gates)
- ✅ tests/ directory scaffolded (fixtures, unit, integration, e2e, performance)
- ✅ playwright.config.ts + pytest.ini created
- ✅ First story team develops with tests (pytest + Playwright)
- ✅ CI gates passing (unit >80%, integration >70%, e2e scenarios)

**Fleet-wide:**
- ✅ All 8 stations have test architecture (generated, not manual)
- ✅ All 8 stations use pyforge-testing-kit (no duplication)
- ✅ All 8 stations pass same quality gates (consistent standard)
- ✅ Dashboard shows test-architecture status per station
- ✅ Deployment of test architecture to any new station takes <5 minutes

**Quality:**
- ✅ False-negative rate: 0% (no shipping bugs because tests missed them)
- ✅ False-positive rate: <5% (not slowing down development with flaky tests)
- ✅ Coverage growth: Stories increase test coverage as they're implemented
- ✅ Operator confidence: Every shipped feature is verified by systematic tests

---

### Fleet Completeness Tracking

| Project  | **DREAM** | Decks | **SPEC** | Research | Brief | **PRD** | **ARCH** | **EPIC** | **STORY** | **TEST** | Dev Status |
|----------|-----------|-------|----------|----------|-------|--------|----------|----------|-----------|----------|------------|
| herald   | ✅        | ✅    | ✅       | ✅       | ✅    | ✅     | ✅       | ✅       | ✅        | ✅       | 🚀 Coding  |
| atlas    | ✅        | ⏳    | ✅       | ✅       | ✅    | ✅     | ✅       | ✅       | ✅        | ⏳       | 🏗️ Ready   |
| doctor   | ✅        | 📋    | ✅       | ✅       | ✅    | ✅     | ✅       | ✅       | ✅        | ⏳       | 🏗️ Ready   |
| marshal  | ✅        | 📋    | ✅       | ✅       | ✅    | ✅     | ✅       | ✅       | ✅        | ⏳       | 📋 Queued  |
| mason    | ✅        | 🎯    | ✅       | ✅       | ✅    | ✅     | ✅       | ✅       | ✅        | ⏳       | 🎯 Next    |
| scribe   | ✅        | 🎯    | ✅       | ✅       | ✅    | ✅     | ✅       | ✅       | ✅        | ⏳       | 🎯 Next    |
| steward  | ✅        | 🎯    | ✅       | ✅       | ✅    | ✅     | ✅       | ✅       | ✅        | ⏳       | 🎯 Next    |
| warden   | ✅        | ⏳    | ✅       | ✅       | ✅    | ✅     | ✅       | ✅       | ✅        | ✅       | 🏗️ Ready   |

#### BMAD-Standard (Required)

- **DREAM** (Tier 0 — mandatory)
- **SPEC** (bmad-spec output)
- **PRD** (bmad-prd output)
- **ARCH** (bmad-architecture output)
- **EPIC** (bmad-create-epics-and-stories output)
- **STORY** (bmad-create-epics-and-stories output)
- **TEST** (bmad-tea-playwright output)

#### Project-Specific (Optional)

- **Decks** (Herald deck family)
- **Research** (bmad-market-research AND bmad-domain-research AND bmad-technical-research output)
- **Brief** (bmad-product-brief AND bmad-prfaq output)
- **Dev Status** (Fleet implementation tracking)

#### Legend

| Symbol | Meaning      |
|--------|--------------|
| ✅     | Complete     |
| ⏳     | In Progress  |
| 📋     | Queued       |
| 🎯     | Next         |
| 🚀     | Coding       |
| 🏗️     | Ready        |

---

### The Risks We're Mitigating

| Risk | How Testing Mitigates |
|------|----------------------|
| Silent failures (webhooks don't fire, links 404, auth bypasses) | High-risk integration tests cover webhook reliability, evidence linking, auth gates |
| False-positive shipping (claims without evidence, notices without recipients) | Evidence validation tests run before each publish; round-trip tests verify data integrity |
| Cross-Moment coordination breaks (Progress + Claim race; Notice + Archive out of sync) | 3 end-to-end integration scenarios cover all major workflows |
| Performance degradation (CLI >1s, web >2s) | Performance benchmarks enforced in quality gates |
| Regression in future changes | Unit + integration tests act as regression suite; Playwright visual tests catch layout breaks |

---

### The Constraints

1. **No manual re-work per station** — automation script generates test architecture, no hand-rolling
2. **One framework, not many** — Playwright for CLI/web/integration, pytest for unit (not 5 different tools)
3. **Shared fixtures, not duplicated** — pyforge-testing-kit is the single source of truth
4. **Risk-driven, not coverage-chasing** — high-risk items get 2+ test layers; low-risk items get 1
5. **No fake passes** — tests that are flaky or incomplete are better than passing tests that miss bugs
6. **Determinism** — same input (epics + architecture) always produces same test architecture

---

### Why Now

1. **Herald is complete** — a masterpiece canonical reference that other stations can inherit from
2. **Other 7 stations are ready** — all have stories, architecture, PRDs; need test architecture next
3. **Pattern is proven** — Herald's BMAD TEA + Playwright approach works; ready to scale
4. **Automation is ready** — bmad_tea_playwright.py script is written and tested
5. **Guild doctrine is clear** — 8 Smiths, independent verdicts, Marshal owns execution; testing integrates cleanly

---

### The Outcome (In Six Months)

**All 8 PyForge stations ship with systematic testing baked in.**

- Every story includes pytest unit tests + Playwright e2e tests
- Every station passes the same quality gates (unit >80%, integration >70%, e2e)
- Every developer uses the same fixtures (pyforge-testing-kit), same patterns (9 Playwright patterns), same framework (Playwright + pytest)
- Dashboard shows test-architecture status across the entire fleet (complete/ready/pending)
- New developer onboarding: "Here's the test-architecture.md for your station; here's the pyforge-testing-kit to inherit fixtures from; now write your tests"
- Shipping a feature: Run tests locally, CI gates enforce coverage, confidence is high

**Test architecture stops being invisible. It becomes a first-class citizen.**

---

### The Guild's Commitment

> "The Guild Crew and Eight Smiths execute dreams to code through test-driven excellence. Every station owns their testing responsibility. Every story ships with systematic tests. Every feature is verified before merge."

**The Guild Testing Charter** — test-charter.md — makes this commitment real.

---

### Next Steps

1. **Adopt this dream** — commit to test-charter.md + test-architecture.md as fleet standard
2. **Create pyforge-testing-kit** — shared package with reusable fixtures (Phase 2)
3. **Deploy to all 8 stations** — run automation script, 30 min for entire fleet (Phase 3)
4. **Development teams execute** — build stories with tests, pass quality gates (Phase 4)

---

### References

- **Canonical Reference**: `_bmad-output/projects/pyforge-herald/planning-artifacts/test-architecture.md` (1,895+ lines with reusable pattern appendix)
- **Fleet Charter**: `docs/reference/test-charter.md` (Guild testing responsibility + Phase 1-4 roadmap)
- **Automation Script**: `_bmad/scripts/bmad_tea_playwright.py` (one-command-per-project generation)
- **Playwright Docs**: https://playwright.dev/
- **BMAD TEA Docs**: https://bmad-code-org.github.io/bmad-method-test-architecture-enterprise/llms-full.txt

---

### Dream Status

**Realized**: Phases 1 complete (Herald test architecture + automation + charter)  
**In Progress**: Phase 2 (pyforge-testing-kit shared package)  
**Planned**: Phases 3-4 (fleet deployment + development integration)

**The dream is real. The Guild is test-ready.**

## 2026-10-26 — Two ways to finish a story, and Marshal has only ever heard of one (folded from quick-dev-reconciliation)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 111.1). The body below is `docs/dreams/quick-dev-reconciliation.md`, verbatim, with its headings demoted one level and its 2026-09-16 fold banner left out; the file moved to `archive/docs/dreams/quick-dev-reconciliation.md`.*

## Two ways to finish a story, and Marshal has only ever heard of one

### The Dream

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

### What it looks like when real

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

### Constraints

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

### Realization log

- **2026-08-11** — Captured after the operator asked why `bmad-loop`-driven
  unattended development is slower/costlier than a supervised `bmad-quick-dev`
  session, and what Marshal could do to let development mix modes. Confirmed
  via grep: zero references to `quick-dev`/`quick_dev` anywhere in
  `src/shared/packages/pyforge-marshal/` (only in planning prose). Confirmed
  via `epics.md`: no existing FR/epic/story covers mixed-mode tracking.
  Queued as a Dream rather than touched directly — `core/status.py`,
  `cli/deploy.py`, `scripts/promote_sprint_status.py`, and
  `sprint-status-ledger.yaml`'s generator were deliberately left untouched
  pending the Spec/story chain. Companion pain, same investigation, separate
  Dream (different subsystem, different epic):
  [`risk-tiered-review-depth.md`](<https://github.com/rxm7706/local-recipes/blob/main/archive/docs/dreams/risk-tiered-review-depth.md>).
- **2026-08-14** — Realized — Story 5.9 (FR-186) shipped `deploy reconcile-completions` with the documented `not-loop-native` label deviation (narrows toward true quick-dev as FR-187 subjects accumulate). Status flipped and FR-186 backfilled into the PRD by the 2026-08-14 audit.

- **2026-09-09 (fleet readiness pass — operator-approved batch)** — Status kept `realized`; the
  Spec's last open question **retires to `open_questions: []`**. It was answered by Story 5.9
  (FR-186, `done`) and recorded in the Spec's Change Log on 2026-08-12 — merge-subject classification
  through the three-pattern chain (`core/promotion.py:35-36,252-256`) feeding
  `core.status.not_loop_native_completions` (`cli/deploy.py:831-835`), labelled `not-loop-native` as
  the honest joint fact, narrowing toward true quick-dev as FR-187 subjects accumulate. Only the
  frontmatter never caught up. Batch: `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`.

## 2026-10-26 — A one-line doc fix and a cross-module rewrite get the identical review (folded from risk-tiered-review-depth)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 111.1). The body below is `docs/dreams/risk-tiered-review-depth.md`, verbatim, with its headings demoted one level and its 2026-09-16 fold banner left out; the file moved to `archive/docs/dreams/risk-tiered-review-depth.md`.*

## A one-line doc fix and a cross-module rewrite get the identical review

### The Dream

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

### What it looks like when real

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

### Constraints

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

### Realization log

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
  [`quick-dev-reconciliation.md`](<https://github.com/rxm7706/local-recipes/blob/main/archive/docs/dreams/quick-dev-reconciliation.md>).
- **2026-08-14** — Realized — Story 2.8 (FR-185) shipped `classify_review_tier`/`resolve_review_cycles` in `core/gate.py`. Status flipped and FR-185 backfilled into the PRD by the 2026-08-14 audit.

- **2026-09-09 (fleet readiness pass — operator-approved batch)** — **STATUS REVERSED, `realized` →
  `specified`, under the realization gate.** Story 2.8 shipped the mechanism and only the mechanism:
  `classify_review_tier` (`core/gate.py:724`) and `resolve_review_cycles` (`:768`) have **zero
  callers anywhere outside `tests/unit/test_gate.py`**. There is no producer of `declared_low_risk`
  (no CLI flag; no `low_risk`-shaped key in either `bmad-spec`'s or `bmad-build-auto`'s
  `spec-template.md`), no `VcsPort` call computing `changed_files`, and nothing in `cli/gate.py`
  calls either function — recorded as `DW-FU-2-8-2` and `DW-FU-2-8-4`, the latter re-verified
  `2026-09-05 — STANDS`. A one-line doc fix and a cross-module rewrite therefore still get the
  identical review, which is this Dream's own title. The 2026-08-14 flip was chain bookkeeping — the
  same failure [`adaptive-model-tiering.md`](<https://github.com/rxm7706/local-recipes/blob/main/archive/docs/dreams/adaptive-model-tiering.md>) records against itself, and
  the third instance inside marshal alone.
  `spec-risk-tiered-review-depth` moves `shipped` → `in-progress` and gains one open question (where
  does `declared_low_risk` come from?). **Enablement is marshal Story 33.5**, beside the token-economy
  enablement — same "turn on what is built" shape. Batch:
  `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`.

## 2026-10-26 — Run state is a service — the loop's truth leaves the laptop (folded from run-state-one-publisher)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 111.1). The body below is `docs/dreams/run-state-one-publisher.md`, verbatim, with its headings demoted one level and its 2026-09-16 fold banner left out; the file moved to `archive/docs/dreams/run-state-one-publisher.md`.*

## Run state is a service — the loop's truth leaves the laptop

### The Dream

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

### Why now — measured, not feared

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

### What it looks like when real

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

### Constraints / Non-goals

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

### Kinships

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

### Realization log

- **2026-09-12** — Seeded (operator ruling: every effort enters through the Dream-to-Code
  chain, gap-closure included — no story drafting or dispatch before a Dream and its Spec).
  Captured after a live re-verification of the 2026-09-11 infographic's § 18 row "CAP-17 run
  state — OPEN · 33.4 + 49.8 blocked": the tracked ledgers still read `blocked`, marshal still
  imports `django_pyforge` zero times, `cli/init.py:336` and doctor's `marshal.py:544` still
  resolve the home directory, and `publish_start` is still the only writer of `run_state`. Two
  design facts found in that pass that neither story text names: the host sweep
  (`sweep_lost_runs`) would mark an externally-published run dead for lacking a Celery task,
  and four more `~/.bmad-loops` readers (steward, scribe, doctor story-status) sit outside
  both stories' Surface lines. Owner **marshal** by the C8 precedent (the surface that changes
  most — both supervisors and the publisher — is marshal's); the criterion stays on the
  Unifying Spec. Next act: `bmad-spec` derives the Spec under `pyforge-marshal`.
- **2026-09-12** — Spec derived: `spec-run-state-one-publisher` under `pyforge-marshal`
  (`bmad-spec` headless, express; `status: draft`). Binds Unifying CAP-17 and token-economy
  CAP-18/CAP-7 by kinship and mints only CAP-1..4 (the host holds a run it does not own; a
  published external run is attributable; the deployed proof is exercised and recorded; no
  run-state read from a home directory remains). Four open questions gate `ready`: the
  publisher's credential path, in-process versus host-face publishing, the proof lane, and the
  classification of steward's two `upgrade.py` reads. `dream-chain-check` and
  `dreams-hygiene-check` clean for this pair. Dream stays `dreamt` until the Spec is `ready`.
- **2026-09-12** — Specified. The four open questions were researched in parallel against the
  pyforge code, PRD, architecture and Specs, spot-checked, and accepted by the operator: (1) the
  operator's IdP bearer is exchanged once at the host for a delegated assertion, the sidecar then
  holds only a subject-bound run handle; (2) the publisher reaches the store over the host's
  `/stations/marshal/mcp` face — never an in-process `django_pyforge` import, which inverts Story
  33.4's and token-economy CAP-18's literal wording (rewording owed through their memlogs); (3)
  the proof is two-tier, `platform-ci-local --test` gating the mechanism and one attended CRC
  exercise recording the criterion, the OCP namespace written as not exercised; (4) steward's two
  `upgrade.py` reads are loop-home file reads and stay tagged, doctor's story-status read is run
  state and moves once the payload carries per-story phase and commit. Two gaps neither story
  named became CAP-5: no CLI login exists anywhere and the realm has no marshal station role.
  Spec `ready`, `open_questions: []`; Dream `dreamt → specified` per README § status.

## 2026-10-26 — The dashboard goes stale because promotion is a remembered step (folded from sprint-status-auto-promote)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 111.1). The body below is `docs/dreams/sprint-status-auto-promote.md`, verbatim, with its headings demoted one level; the file moved to `archive/docs/dreams/sprint-status-auto-promote.md`.*

## The dashboard goes stale because promotion is a remembered step

### The Dream

A story landing on a loop-home's branch does not, by itself, make the
dashboard or the tracked ledger show it as done. Two separate manual steps
have to run afterward: `python3 scripts/promote_sprint_status.py` (copies the
loop-home's live Tier-3 `sprint-status.yaml` into the tracked
`sprint-status-ledger.yaml`) and `Lane 1 /console/ (Guildhall generator retired)
--source sprint-status` (regenerates `data.js` from the current state).
Nothing enforces that either happens, and nothing reminds anyone they
haven't — the dashboard just quietly keeps showing whatever story was
in-flight the last time someone happened to run both.

Live cost the same session, three separate times: Story 2.1 landed, the
dashboard kept showing it running until the user asked why; the `8-5` block
fix landed on the loop-home feed but the tracked ledger promotion was
forgotten until the forward-dependency detector itself caught the gap; Story
2.4 landed, the dashboard again kept showing it running. Each time the fix
was the same two commands and a small `maintenance` PR — a real fix, but a
repeated one, because the trigger to run it was "a human noticed and asked,"
not anything structural.

This Dream is the idea already named out loud mid-session: fold promotion
into the standard check-in habit, or better, make it automatic — a story
landing should be the trigger, not a periodic poll that depends on someone
remembering.

### What it looks like when real

- A story landing (merge commit appears on a loop-home's branch) is never
  more than one check-in cycle away from being reflected in both the tracked
  ledger and the dashboard — today it can silently sit stale indefinitely.
- The recurring status check-in routine runs `promote_sprint_status.py` +
  the dashboard regen as a standing step every time, not only when someone
  separately remembers to ask "does the dashboard match reality?"
- Ideally this stops being a remembered step at all: a git hook, a
  `bmad-loop` lifecycle hook (post-merge-to-loop-home), or a scheduled task
  runs the promotion automatically whenever a run's `state.json` marks a
  story `done`, so a human never has to notice the staleness to begin with.
- A detector exists (or `dashboard_drift_check.py` is extended) to catch a
  landed-but-unpromoted story on its own, the same way
  `forward_dependency_check.py` caught the `8-5` promotion gap as a side
  effect of an unrelated check — that was luck, not design; this Dream is
  about not needing the luck.

### What is real

- Three live incidents this session, all the same shape: story lands on the
  loop-home branch, dashboard/tracked-ledger stay stale until a human
  notices and asks. Fixed each time with `promote_sprint_status.py` +
  `pyforge.doctor.sources.fleet_scan --source sprint-status` + a small
  `maintenance` PR (PRs #236 [closed, superseded by later work before it
  merged], #240, and the inline fix folded into PR #237's own diff for the
  `8-5` case).
- No automation exists yet for any of the three options above (check-in
  habit, git hook, drift detector) — this Dream captures the idea, not an
  implementation.

### Constraints

- Never silently skip a promotion because it "looked recent enough" — the
  whole point is that staleness is currently undetectable without running
  the check, so an automated version must actually run the check, not
  approximate it.
- Whatever automates this must not run *during* an active bmad-loop session
  for the same story it would be promoting — the loop-home's Tier-3 feed is
  the orchestrator's own write surface while a run is live (per
  `bmad_loop.sprintstatus`'s own docstring: "the orchestrator is the single
  writer... so the no-races invariant holds"); promotion should trigger on
  landing, not poll mid-run.

### Non-goals

- Not a request to change what `promote_sprint_status.py` or the dashboard
  generator actually compute — both already do the right thing when run;
  the gap is entirely about *when* they run.

### Frontier leftover (2026-09-02) — promotion must not write the operator checkout

Story 15.2 made landing the trigger (CAP-1). The leftover is *where* that
write lands. `_promote_sprint_ledger` committed
`marshal: promote sprint-status ledger…` on `repo_root()` — the operator's
shared `main` checkout — after `gh pr merge` had already advanced
`origin/main`. Two writers, no fetch of the merge first: local `main`
ended ahead-by-promote and behind-by-merge every time (41.3, 41.4, 42.1
in one drain). Rebasing the leftover is not the fix.

The story worktree is the wrong isolation (a `done` flip on the PR is a
lie until merge). Story 4.3 already taught the right isolation for
`merge_branch`: a throwaway detached worktree pinned to the tip that
will receive the commit, then a compare-and-swap / fast-forward publish
— never `git checkout` on the shared working tree. Promotion must do
the same: fetch `origin/<base>`, write the twin onto that tip, commit
there, fast-forward-push to the remote. The operator `main` checkout
stays untouched.

### Realization log

- **2026-08-03** — Captured after the third same-session incident of the
  dashboard reading stale after a story landed (2.1, the `8-5` block fix,
  2.4), each caught only because the user asked "why does the dashboard
  still show X running." Not yet acted on.
- **2026-09-02** — CAP-1 shipped (Story 15.2 / FR-136) but wrote the
  promote commit on the operator `main` checkout. Operator asked why this
  was not a worktree. Added as this leftover; contract is CAP-5 on
  `spec-sprint-status-auto-promote`.

## 2026-10-26 — A drift gate nobody can clear, and a drift signal anyone can launder (folded from surface-drift-reconciliation)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 111.1). The body below is `docs/dreams/surface-drift-reconciliation.md`, verbatim, with its headings demoted one level and its 2026-09-16 fold banner left out; the file moved to `archive/docs/dreams/surface-drift-reconciliation.md`.*

## A drift gate nobody can clear, and a drift signal anyone can launder

> The enforcement half of [[regenerable-factory]]. That Dream built the surface
> map and the drift checker; this one makes the checker's verdict **clearable**
> and **trustworthy**, which it is not today.

### The Dream

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

### What it looks like when real

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

### What is real (measured 2026-08-08, on `main` at `cf885388fe`)

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

### What is real, part two — the drift-blind Spec (measured 2026-08-09, on `main` at `7dde591811`)

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
  `spec-dream-to-code-model-self-verification`, `spec-pyforge-core`,
  `spec-sprint-status-auto-promote`) **7** between them, and
  `pyforge-steward/spec-unified-container` **1**. All seven are already in the
  committed baseline with `"memlog": ""`, so all seven are green today and
  unreconcilable tomorrow.
- **Creating the memlog is only half the disposition.** A new memlog moves the
  contract hash away from `""`, so the *next* comparison sees `spec_moved =
  True` and every drifted file downgrades from gating `[drift]` to informational
  `[drift-presumed]`. Fixing blindness by hand without stamping the baseline in
  the same move therefore trades a false green for a quiet one. The stamp is
  part of the remedy, not an optional follow-up.
- A Spec that governs **zero** files cannot drift and is not blind — eleven of
  those exist and are correctly silent. `surface-drift: exempt` records no file
  hashes at all, and `sentinel:` supplies a second hash that *can* move; neither
  is blind. The finding is for the default mode with a real governed set.

- **The producer reconciles what it drifts.** A gate the *author* of a change never
  consults is a gate paid for by whoever lands the change. bmad-loop writes governed
  code all day and has no idea `spec_surface_check` exists: on 2026-08-09 the first
  three loop-produced stories to be landed drifted **14 governed paths** across
  `spec-pyforge-doctor`, plus `pixi.toml` against two further surfaces, and every one
  had to be named by hand at landing. The rule S-13.2 built is correct; the machine
  producing most of the repo's code simply does not know it.

### What is real, part three — the 994 presumed (measured 2026-08-09, on `main` at `1b94994d42`)

CAP-2 made a previously-invisible set visible: **994 `[drift-presumed]` entries** across four
station Specs. Carrying them unexamined would repeat the mistake this Dream was seeded to
correct — a number that hardens into terrain. Measured rather than estimated:

- **932 `added`, 62 `changed`, 0 `removed`.** 94% of the set is not drift in any meaningful
  sense; it is **baseline lag** — the surface grew and nobody re-stamped. Only the 62
  `changed` pose the per-file question the detector was built to ask.
- Every one of the 994 was traced to the commit that last moved it (994/994, none orphaned).
  **178** attribute to an explicit, `done` story id; the rest to deck-family, within-epic
  review-finding, or chain commits. **Zero files were moved by a story that is not `done`.**
- **Herald is 834 of the 994 — and 751 of those are `presentations/**`**, which is a
  *declared* part of its surface, contracted by **HER-9** (six artifact formats per station,
  ~144 tracked files, an explicit tracked/gitignored split). The deck-family commits that
  landed them are HER-4/HER-7/HER-8/HER-9 delivery. This is S-13.4's steward finding at
  fleet scale: **the code caught up to a contract that was already correct.**
- Two attribution traps worth recording, both caught by checking rather than trusting: a
  commit titled only **`Atkas`** (a typo for Atlas) owns 42 of the entries and is the
  pyforge-atlas deck scaffold, entirely inside HER-9; and 68 entries appear to name a story
  `2026-07` because a naive id-regex matched the **date** in a deck-family-rebuild subject.
  Neither is an unaccounted change; both look like one until read.
- So the disposition is **a few cluster judgments and four scoped stamps**, not 994 decisions
  — and the stamp is the honest end state precisely *because* the judgment was made first.
  Naming 994 literal paths in a memlog would satisfy the matcher while recording nothing.

### Constraints

- **Fix the granularity; do not weaken the gate.** Widening a threshold,
  allowlisting the noisy specs, or making drift non-gating would clear the red
  without making the signal true. Charter §6 forbids exactly this move.
- **Never touch `.memlog.md` history.** Memlogs are append-only decisions of
  record; the fix reads them, it never rewrites them.
- **A memlog that names no paths is not an error.** Most existing entries predate
  any naming convention, so the per-file rule must degrade to a visible
  `[drift-presumed]`, never to a hard failure that would red the gate for every
  historical entry.
- `[drift-presumed]` is **informational**. It exists to make an unproven set
  visible; if it gated, it would just be the same unclearable red in a new shape.
- The baseline file is committed state — a scoped stamp must **merge**, never
  rewrite, or it silently drops every spec it did not name.

### Non-goals

- **Not** re-homing this detector to Doctor. That is Charter §6 work already
  scoped as Doctor's Epic 6 (S-6.1 → S-6.10); this Dream fixes the instrument
  where it lives. Marshal keeps the operational guard either way — only the
  *verdict* moves, later.
- **Not** a general dependency or provenance graph. The reconciliation claim is
  "does the memlog name this path", deliberately literal. Inferring intent from
  prose would reintroduce the same "presumed reconciled" blanket this replaces.
- **Not** a rewrite of the surface-glob or coverage half. Coverage works; the two
  `[ungoverned]` files are a missing entry, not a design flaw.
- **Not** an excuse to bulk-reconcile the steward cluster by stamping it. If that
  surface genuinely changed, its contract moves — that is the whole point of the
  factory.

### Realization log

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

## 2026-10-26 — Claude spends the tokens the factory already learned to save (folded from token-economy-claude-session-path)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 111.1). The body below is `docs/dreams/token-economy-claude-session-path.md`, verbatim, with its headings demoted one level and its 2026-09-16 fold banner left out; the file moved to `archive/docs/dreams/token-economy-claude-session-path.md`.*

## Claude spends the tokens the factory already learned to save

### The Dream

The factory already knows how to make an iteration cheap. Five instruments
are on PATH. Marshal can wrap Claude through headroom, seed caveman, retrieve
an epic's 1,500 tokens instead of `epics.md`, and journal what each layer
saved. That kit was built so **Claude** would read less, say less, and
re-learn nothing.

The operator still opens Claude on this repo and burns a Max pool on the
old tax: `CLAUDE.md` and `AGENTS.md` every session, then unbounded file
reads, then polite prose. Dispatch, the path that *can* wrap Claude, is
pointed at **Cursor** on every station so the Claude pool stays unused —
and Cursor cannot take the wire wrap (Story 28.29). The saving exists. The
session that costs money does not use it.

The Dream is a **session path**, not a second compressor. When the operator
runs Claude — interactively or through marshal — the same kit the loop
already has actually sits on that session: wrap on the wire, caveman on
speech, retrieve/recall instead of wholesale planning docs, codegraph
instead of a tree walk. Stations that mean to spend Claude declare Claude
and turn wire on. Stations that mean to spend Cursor keep Cursor and do
not pretend the wrap applies. A pinned compare on a real Claude-wrapped
story is what makes the saving a number, not a recipe README.

> A compressor the session never launches is a story we already shipped.

### Why now — measured, not feared

Found live 2026-09-16 while asking how to use the token-economy libraries
from Claude in this repo:

| Finding | Where it is visible |
|---|---|
| Interactive Claude always loads the fat always-on docs | `CLAUDE.md` ~51 KB, `AGENTS.md` ~30 KB, MEMORY import — every fresh chat |
| All eight stations prefer Cursor | `harness_preference = ["cursor"]` in each `planning-artifacts/marshal-policy.toml` (Claude spend-limited, 2026-09-01) |
| Wire wrap is Claude-shaped and Cursor-dead | `data/harness_profiles/claude.toml` `[wrapper]`; `cursor.toml` has none (28.29) |
| Only marshal declares all five `[context]` layers | Other seven: `output` + `derived-context` + `planning-graph` only |
| Repo defaults have no `[context]` block | `_bmad-output/policy-defaults.toml` — absent means every layer off (CAP-1) |
| Parent Dream is still `specified` | [[marshal-token-economy]] is realized only when a benchmark artifact reports a measured saving — that artifact is still the missing proof |

This is not "build headroom." Headroom, caveman, codegraph, cocoindex, and
graphifyy are already pinned. Epic 28 built the seams; Epic 33 enabled
layers on marshal dispatch and rolled output/derived/planning fleet-wide.
The leftover is **which session the operator actually runs**.

### Why this Dream widened — the 2026-09-16 analysis

Seeded as "Claude pays the uncompressed tax," the Dream went through a
deep analysis and adversarial review the same day, and the operator named
its center: **the biggest gap is sharing cache, knowledge, and memory
across every agent, harness, and model.** Three conclusions now shape the
Spec, recorded here so the reordering can be revisited at the aspiration
level:

- **Token savings is not one currency.** Claude meters billed tokens
  (with prompt-cache discounts); Cursor meters subscription quota;
  Copilot meters premium requests; Gemini meters rate limits; Devin
  meters ACUs. A layer that helps one currency can be irrelevant to
  another — wire compression is dollars on Claude, unreachable on
  Cursor, quota headroom on Copilot. Every saving gets reported in its
  harness's own currency, never one blended number.
- **The five layers are two economies.** The shared substrate —
  codegraph, cocoindex distills, the planning graph, team memory —
  amortizes understanding *once* and serves every harness. The
  per-harness wire (headroom, caveman) is the secondary,
  capability-bound residue. The substrate is primary: compression
  optimizes the marginal turn; the substrate eliminates whole categories
  of turns (the 65k-token `epics.md` re-read is the emblem).
- **The substrate's gaps are named.** It does not *travel* (cloud agents
  get a bare clone — no bootstrap path exists); *write-back* is
  harness-fragmented (`scribe capture` is the neutral ritual, habitual
  in no harness); the only portable cache is a canonical, digest-pinned
  context bundle (prefix stability), not a shared provider cache; and
  *freshness* is the trust boundary (Scribe owns it; the SLA holds).
  Centralizing knowledge also centralizes error — provenance (Scribe
  never answers uncited), the freshness SLA, and capture hygiene (no
  secrets, decision-grade facts only) are the mitigations, stated here
  so they survive the substrate becoming the default.

The review also corrected the record: output compression is multi-harness
(caveman ships 21 targets — copilot, cursor, gemini, devin among them),
and the sharpest open risk is the **prompt-cache collision** — a wire
compressor that rewrites prefixes unstably can cost more in lost cache
discounts than it saves in tokens. Claude wire savings stay *unverified*
until per-layer benchmark legs with cache-hit reporting exist.

### What it looks like when real

- **Claude dispatch is wrapped.** A station whose `harness_preference`
  leads with `claude` and whose `[context.wire]` is on launches
  `headroom wrap claude --code-memory none --port {wire_port} --`. A
  station that leads with `cursor` does not journal a wrap it cannot do.
- **Interactive Claude has a documented path.** The operator can start
  Claude from repo root through the same wrap, with caveman installed
  (`caveman-install --only claude`), and is told to retrieve/recall
  instead of `@epics.md`. That path is written once (Dream / Spec / a
  thin how-to), not rediscovered in chat.
- **Retrieve is the planning load.** `marshal context retrieve` and
  `scribe recall --mode planning` are what a Claude session uses for
  decisions and epic scope. Wholesale PRD / `epics.md` loads are a miss.
- **One compare exists.** `marshal benchmark compare` on a named
  Claude-wrapped story reports weighted tokens (and dollars if the catalog
  is declared) layers-on vs layers-off. The parent Dream's realized-guard
  can finally cite it.
- **No second kit.** No new compressor, no BSL caveman input proxy, no
  Serena / headroom `--memory` store beside Scribe.

### Constraints / Non-goals

- **Does not remint Epic 28 or 33.** Those stories shipped the machinery.
  This Dream names the *session that uses it*.
- **Does not claim [[marshal-token-economy]] realized.** That flip still
  waits on the compare artifact. This chain produces the Claude-legged
  run that artifact can cite.
- **Does not wrap Cursor.** 28.29 stays: wire is structurally dead there.
  Cursor Ultra remains a pool, not a headroom target.
- **Does not thin `CLAUDE.md` / `AGENTS.md` unless the Spec's open
  question says so.** The always-on doc tax is real; rewriting the
  cross-tool entry files is a different blast radius and a different
  ruling.
- **Does not flip every station to Claude by default.** Preference is an
  operator choice per station (or a dated fleet ruling). Silent
  fleet-wide flips recreate the 2026-09-01 spend scare.
- **No BSL surprises.** The caveman input proxy stays unpackaged.
- **Savings stay advisory.** No second PR gate; CAP-7 journals inform,
  they do not fail CI.

### Open questions (for `bmad-spec`, not answered here)

1. Is interactive Claude on the shared checkout a **supported** path
   (documented wrap + skill), or is the only sanctioned Claude path
   `marshal factory dispatch` / `spin`?
2. When the operator wants Claude savings, is the change **per-station**
   `harness_preference` + `[context.wire]`, or a repo-default that
   stations opt out of?
3. Does v1 include a thinner always-on doc surface for Claude Code, or
   is that a later Dream?

### Kinships

[[marshal-token-economy]] (the machinery and the realized-guard this
session path finally feeds) · [[adaptive-model-tiering]] (difficulty →
model; review floor never drops) · [[cursor-native-tier-map]] (the
Cursor-honest twin — this Dream is the Claude-honest twin) ·
[[pixi-candidate-currency]] (the five instruments' pin home) ·
[[run-state-one-publisher]] (CAP-7 savings numbers on a published run) ·
[[scribe-recall-modes]] / [[scribe-planning-pointers]] (retrieve, not
wholesale planning bodies) · [[scribe-code-navigation-owner]] (codegraph
for symbols) · [[pyforge-marshal]] (the station).

### Realization log

- **2026-09-16** — Seeded. Operator asked how to use the token-economy
  libraries from Claude and then asked for this Dream seed. Live join:
  station policies Cursor-first; only marshal has wire + structure-graph
  on; interactive Claude still pays the always-on doc tax; parent Dream
  still `specified`. Owner **marshal** (the harness profiles, `[context]`
  composition, and dispatch launch are marshal's). Next act: `bmad-spec`
  under `pyforge-marshal` after the three open questions are answered —
  do not mint an epic or flip `harness_preference` from this seed alone.
- **2026-09-16 (analysis)** — Deep analysis + adversarial review; full
  detail in the Spec memlog (entries 4–10). All three open questions
  answered: dispatch is the *measured* path, interactive a documented
  convenience path on the same instruments; repo-default `[context]`
  with wire as a capability-aware `"auto"`; doc thinning deferred to a
  later Dream. Multi-harness matrix ruled (claude full kit; copilot full
  kit pending one `[wrapper]` story; cursor harness-agnostic only —
  intended economics, not a gap; cloud agents bounded by the instruction
  surface). Caveman correction: the output layer is multi-harness.
  Substrate-primary reordering with four named gaps (travel, write-back,
  canonical bundle, freshness) and the centralization caveat — see
  § *Why this Dream widened* above. The re-derive should mint: the
  front-door CAP, the silent-saves CAP (tri-state, journal taxonomy,
  per-currency rollup, persistence advisory), the copilot `[wrapper]`
  story, the substrate CAP (bootstrap, write-back ritual, canonical
  bundle, freshness SLA), and per-layer benchmark legs with cache-hit
  rates.
- **2026-09-16 (fold)** — Folded into [[marshal-token-economy]] (operator-ruled
  token-savings consolidation) and archived in place, the same day it was
  seeded. Prior status: `dreamt`.
- **2026-09-16 (Spec fold)** — The operator ruled no satellite Specs, so the
  contract folded too: `spec-token-economy-claude-session-path` is
  `superseded`, its capabilities re-minted as `spec-marshal-token-economy`
  CAP-19..CAP-24, dispatch home marshal Epic 46 (46.1–46.10). The superseded
  folder keeps the eleven-entry decision memlog (OQ answers, multi-harness
  matrix, adversarial review, substrate-primary reordering).

## 2026-11-01 — A stranger reads the chain: EGM goldfish as the fleet's challenger

### The Dream

The chain has two kinds of verifier, and both are blind the same way. The
detectors count — every CAP has a story, every story a ledger key, every
governed path a hash — and never read. The review lenses read, but they were
raised in the house: every `bmad-review` subagent loads `CLAUDE.md`,
`AGENTS.md` and the team-memory index before it sees the artifact, so a wrong
idea the whole house shares is invisible to them too. Nobody on the floor can
ask whether the Spec actually covers the Dream entry it cites, whether a
story's acceptance criteria exhaust its CAP's success line, whether the code
still means what the Spec says, or whether `AGENTS.md` says what its authors
think it says.

The Dream is a **challenger**: a reviewer that walks in cold, is handed one
artifact, the station's `glossary.md` and the Dream entry the artifact claims
to realize — and nothing else: no instruction files, no conversation, no
memory, read-only tools — and reports what does not make sense, what is
assumed but never written, what is promised but never tested. Then it forgets
everything. Google's Elephant-Goldfish Model
(`google/elephant-goldfish-model`, Apache-2.0; a markdown-only Claude Code
plugin of seven skills and nine reviewer personas, each persona declaring
`omitClaudeMd: true` and `tools: [Read, Grep, Glob]`) is the first stranger
the fleet hires. The elephant stays marshal.

Three ways to run it, one switch each, all off by default. **Ad hoc**: the
operator points the challenger at one artifact from an interactive session and
reads the report. **Integrated**: `marshal factory dispatch` asks the
challenger whether a story spec is ready before a dev session starts, and
`bmad-retrospective` asks it whether the code drifted from the Spec at epic
close. **Audit**: one sweep over everything that already exists — every
station's Dream, Spec, `epics.md` and story specs, plus the repo's own rules
(`AGENTS.md`, `CHAIN-STANDARD.md`, the station `SKILL.md`s) — to say where the
fleet stands before any new chain is minted.

> A reviewer that knows the rules cannot tell you the rules are wrong.

### Why now

Operator answers, 2026-11-01: a dispatched story bounces on a Spec gap or
contradiction most weeks (a bmad-loop CRITICAL escalation, a review send-back,
or a post-merge fix story); every blind spot matters — meaning, mechanics,
code drift and the rules themselves; the challenger may question the repo's
own rules, not only the artifact under review; and the operator chose full
integration over a trial, on three conditions: everything reversible and
behind feature flags with a configuration off-switch, runnable ad hoc or
integrated, and a one-time audit over the existing stations, the repo rules
and the current state.

Found live the same day:

| Finding | Where it is visible |
|---|---|
| No challenger concept exists | `challenger` appears only in deep-recon candidate selection and party-mode |
| `bmad-review` lenses inherit the house | spawned as ordinary subagents; the instruction files and memory index load first |
| The isolation is Claude Code's, not EGM's | `.claude-plugin/agents/*.md`: `omitClaudeMd: true`, `tools: [Read, Grep, Glob]`, `model: inherit` (the Agent tool's `model` override lets a different model challenge what one model wrote) |
| A harness cannot `Skill`-invoke EGM | every `SKILL.md` is `disable-model-invocation: true`; the harness spawns the registered reviewer agents (`egm:egm-zoom-out`, `egm:egm-design`, `egm:egm-comprehension`, `egm:egm-implementation-readiness`, `egm:egm-codebase-details`, `egm:egm-synthesizer`) directly, or follows a `SKILL.md` in the main thread |
| The personas live outside the repo | `~/.claude/plugins/cache/egm/egm/<version>/`; headless runs need `Read(...)` rules on `agents/`, `docs/`, `resources/`, `skills/` |
| Young upstream | v0.1.0 released 2026-10-27; README: "not an officially supported Google product" |
| Every Spec already ships the goldfish context | `planning-artifacts/specs/spec-pyforge-<station>/glossary.md`, "Glossary-first by design" |

### What it looks like when real

- **One verb, five stages, exit 0.** `marshal factory challenge --project
  <station> --target <path> --stage {mint,decompose,readiness,drift,rules}`
  spawns the configured reviewer group, writes a flat deficiency report to
  Tier 3 (`implementation-artifacts/egm/<run>/`), journals the run beside the
  dispatch runs, and always exits 0: findings are data, never a verdict (the
  mason `doctor` pattern; doctor's and warden's rule that nothing becomes a
  second PR gate).
- **Goldfish context is the glossary and the Dream entry.** A reviewer
  receives the artifact, the Spec's `glossary.md`, the Dream entry the
  artifact cites, and the standard it is judged against — `CHAIN-STANDARD.md`
  and the five-field Spec shape for a Spec, the story-spec template for a
  story spec. Never `AGENTS.md`, never `CLAUDE.md`, never the memlog, never
  chat. EGM's own `document_standards/` are not used; its `structural` and
  `style` personas are not dispatched.
- **Ad hoc is the same verb.** An interactive session runs `marshal factory
  challenge` by hand, or reads `egm-review/SKILL.md` and follows it; the
  report lands in the same Tier-3 folder; nothing tracked changes until a
  finding is accepted.
- **Integrated is a policy block plus a flag per hook.** `marshal-policy.toml`
  gains `[challenge]` (`enabled`, `stages`, `reviewers`, `model`, `standards`,
  `artifact_dir`); absent means off, exactly as `[context]` does. The dispatch
  readiness hook and the retro drift hook each sit behind their own
  `pyforge.marshal.egm_*` kill switch, `defaultVariant: off`, one per CAP (the
  Guild flag rule, Epic 110). A red readiness report moves the story spec to
  `status: draft` with the findings recorded in it; the challenger never
  writes a ledger.
- **Audit is a sweep, once.** `marshal factory challenge --audit` runs the
  `rules` stage over `AGENTS.md`, `CHAIN-STANDARD.md` and every station
  `SKILL.md`, and the `mint` and `decompose` stages over every station's
  Dream, Spec and `epics.md`, and writes one fleet report and one per-station
  report to Tier 3. The durable residue is a dated
  `planning-artifacts/research/egm-audit-<date>.md` per station and a memlog
  entry on each Spec whose findings were accepted, landed in the PR that acts
  on them (a memlog or research file alone trips chain-currency).
- **Accepted findings travel the only write path.** `egm-resolve` proposes;
  the operator accepts; the fix is a memlog append plus a `bmad-spec`
  re-derive, or a story-spec edit — never a hand edit of `SPEC.md`, never a
  ledger write (behavioural guidelines 6 and 7). Rejected findings are
  recorded as rejected in the report, nowhere else.
- **Reversible to zero.** Turning it off is `enabled = false` or the flag;
  removing it is `claude plugin uninstall egm@egm`, deleting the Tier-3
  folder, and retiring the flags by their `cleanup_by` date. No governed file,
  detector, gate or ledger depends on EGM being installed; with the plugin
  absent the verb refuses with its own exit code and dispatch proceeds as if
  the hook were off.
- **Pinned and recorded.** The plugin is pinned to a version in the tracked
  `.claude/settings.json` `enabledPlugins`; the headless read rules on the
  plugin cache go in marshal's dispatch `--settings`; the pin is a steward
  estate row with a refresh verb, not a hand-edited path.

### Constraints / Non-goals

- **No second PR gate.** The challenger's report never fails CI, never writes
  a ledger, never flips `blocked`. The gate stays `detectors-ci` + warden.
- **Does not replace the chain's writers.** The Dream stays the operator's;
  the Spec stays `bmad-spec`'s output (the portability contract); stories
  stay `bmad-create-epics-and-stories`'s; per-story review stays
  `bmad-review`. `egm-brainstorm` and `egm-draft` are not wired;
  `bmad-forge-idea` already owns pre-Dream ideation.
- **`egm-bootstrap` is never run on this repo.** A README sweep across the
  tree reds `governance-currency` and the docs map.
- **Off by default, everywhere.** Policy block absent = off; every flag
  `defaultVariant: off`; a station opts in per stage.
- **Cost is per event, not per PR.** Mint and decompose run once per Spec
  change; readiness once per dispatch with one reviewer; drift once per epic
  close; the audit once.
- **Context isolation, not filesystem isolation.** Reviewers can read any
  accessible file; the harness passes absolute paths and never URLs
  (reviewers cannot open them).
- **One owner.** Marshal owns the verb, the hooks, the policy block and the
  flags. The doctor advisory source, the steward pin row and the scribe
  instruction-surface line are Kinship entries on those stations' Dreams,
  minted when their stories are reached, not from this entry.

### Open questions (for `bmad-spec`, not answered here)

1. Which model challenges: `inherit`, or a fixed different model from the
   `model_cost_catalog` so the author model never reviews itself?
2. Vendor the nine Apache-2.0 personas into the repo (a `.claude/agents/`
   twin with `omitClaudeMd`) so the challenger survives the plugin's absence,
   or depend on the plugin cache and pin?
3. v1 stages: all five, or `rules` + `mint` + `readiness` first, with
   `decompose` and `drift` as a second wave?
4. Does a red readiness report move the story spec to `draft` automatically
   under dispatch, or only report and leave the move to the operator?
5. Where does the audit's fleet summary live durably — one `research/` file
   per station, or a single herald fact-ledger entry?

### Kinships

[[pyforge-marshal]] (the station; the verb, hooks, policy block and flags are
its) · [[pyforge-doctor]] (an advisory `egm-challenge` source for
`fleet-picture`, later) · [[pyforge-steward]] (the plugin pin as an estate
row; the `steward setup` read rules) · [[pyforge-scribe]] (the
`EGM artifact directory:` line and the instruction-surface parity test; the
`rules` stage reads scribe's surface cold) · [[one-chain-per-station]]
(`CHAIN-STANDARD.md` is the standard the mint stage judges against) ·
[[feature-flag-governance]] (one kill switch per CAP, `cleanup_by`) ·
[[pyforge-charter]] (the Lexicon the glossary-first context inherits).

### Realization log

- **2026-11-01** — Seeded. The operator asked whether
  `google/elephant-goldfish-model` could be installed and used, then whether
  it could serve as the chain's independent challenger, then answered the four
  deciding questions (bounces most weeks; every blind spot; rules too; full
  integration) and set three conditions: reversible and behind flags with a
  configuration off-switch; runnable ad hoc or integrated; a one-time audit
  over the existing stations, repo rules and current state. Live join as in
  § *Why now*. Owner **marshal**. Next act: `bmad-spec` under
  `pyforge-marshal` after the five open questions are answered — do not mint
  an epic or install the plugin into the tracked settings from this seed
  alone. The audit may run ad hoc at user scope before the Spec exists, Tier-3
  output only; its durable residue waits for its story.
- **2026-11-01 (answers)** — The open questions answered the same day.
  (1) A fixed, different model: the challenger model comes from
  `marshal-policy.toml`'s `model_cost_catalog` and is never the author
  session's model. (2) Plugin pin, no vendoring: the personas stay in the
  plugin cache, pinned and refreshed by steward. (3) All five stages in v1,
  including `drift` and the retro hook. (4) Session default, operator
  informed: a red readiness report only reports in v1; the automatic move of
  the story spec to `draft` is wave 2 behind its own flag. (5) Session
  default, operator informed: the audit's durable residue is one
  `research/egm-audit-<date>.md` per station. The plugin was installed at
  user scope the same day so the next interactive session can run the ad hoc
  audit, Tier-3 output only. Next act: `bmad-spec` under `pyforge-marshal`.
- **2026-11-01 (the audit lands)** — The one-time audit ran by hand on 2026-11-01 (the operator ruled it
  counts as Story 113.7's run): rules over AGENTS.md, CHAIN-STANDARD.md and the eight station skills, mint and
  decompose over each station's newest CAP slice. 269 findings (42 Blocker, 205 Major, 22 Nit as audited; 1
  Blocker after verification) were re-verified on main 03a7aff5d9 and triaged 226 accepted, 41 rejected, 2
  deferred; the operator accepted every recommendation the same day. Residue: one
  research/egm-audit-2026-11-01.md per station, rules and fleet totals in
  `_bmad-output/projects/pyforge-marshal/planning-artifacts/research/egm-audit-2026-11-01.md`. Fixed in the
  113.7 PR: marshal Stories 113.8-113.13 (the challenger's partial-run, model, isolation, precondition,
  stage-standard and resolve defects) and 23 fix stories on the other stations; parked at backlog: 113.14 (a
  size ceiling and section selector, after which the first automated --audit runs).
- **2026-11-01 (the synthesizer)** — As built, the challenger never spawns `egm:egm-synthesizer`: it dispatches
  five reviewer agents (zoom-out, design, comprehension, implementation-readiness, codebase-details) in the
  per-stage groups of `DEFAULT_REVIEWERS`, and the orchestrator session itself assembles `report.json` from their
  answers. The table in § *Why now* still lists the synthesizer among the plugin's registered agents, which it
  is; it is left as written (Story 113.12).
- **2026-11-01 (goldfish context as built)** — The bullet *Goldfish context is the glossary and the Dream entry*
  stays as written; as built (Story 113.12) the rule binds the context and never the target, so the `rules`
  stage reads `AGENTS.md` cold as its target. In the `--audit` sweep a repo-rules target (`AGENTS.md`,
  `CHAIN-STANDARD.md`) takes `docs/dreams/one-chain-per-station.md` plus marshal's glossary and a station
  `SKILL.md` its whole station Dream; an ad hoc run takes its `--project` station's Dream; the glossary is
  `glossary.md` when present (six of eight stations have none). Each stage names its standard, a fallback a
  `[challenge]` block's `standards` overrides: mint `CHAIN-STANDARD.md` and
  `.claude/skills/bmad-spec/assets/spec-template.md` (the five-field shape), decompose `CHAIN-STANDARD.md` and
  the station `SPEC.md` whose capability range its stories claim, readiness
  `.claude/skills/bmad-build-auto/spec-template.md`, drift the station `SPEC.md`, rules `CHAIN-STANDARD.md`.
