---
title: Adversarial review — AD-25..AD-39 (pyforge-marshal architecture spine)
type: review
lens: adversarial
project: pyforge-marshal
target: planning-artifacts/architecture.md § Invariants & Rules (AD-25..AD-39)
also-checked: planning-artifacts/prd.md (FR-22, FR-50 edits + adjacent FRs), planning-artifacts/epics.md (propagation)
reviewer-posture: default-skeptical; findings are CONFIRMED-broken unless tagged otherwise
created: 2026-07-25
verdict: BLOCKED-ON
---

# Adversarial review — AD-25 through AD-39

AD-25..39 were authored under reviewer pressure to close seven CRITICAL holes in AD-1..24.
They close those holes. This review asks the next question: **what did they open?**

Three attack axes were applied to each new AD:

1. **Letter-vs-intent** — can a builder satisfy the rule verbatim and still ship the failure it names?
2. **Contradiction** — does it collide with AD-1..24, with a PRD FR/NFR/constraint/journey, or with another new AD?
3. **Implementability** — do the named files, flags and mechanisms exist in the live repo and in the pinned harness (`bmad-loop 0.9.0`)?

Axis 3 was executed against the live checkout, not from the document. Ground truth captured
below is reproducible.

## Ground truth established (live, 2026-07-25)

| Claim under test | Verified result |
| --- | --- |
| Harness policy path is configurable | **NO.** `bmad_loop/policy.py:14` → `POLICY_FILE = Path(".bmad-loop") / "policy.toml"`. `bmad-loop run --help` exposes only `--project --spec --epic --story --max-stories --dry-run`. No policy-path flag anywhere in the CLI. |
| `.bmad-loop/policy.toml` is machine-local | **NO.** `git ls-files .bmad-loop` → `bmad_loop_hook.py`, `policy.toml`. It is **git-tracked**. `.gitignore` covers `.bmad-loop/runs/` and `.bmad-loop/cache/` only. (Upstream's own comment says `bmad-loop init` gitignores it — this repo does not.) |
| Loop homes hand-edit that shared tracked file today | **YES, live right now.** `../local-recipes-loop-pyforge-herald` → ` M .bmad-loop/policy.toml` (8 insertions, 22 deletions vs `main`). |
| Loop homes publish by push to `main` | **YES.** `scripts/bmad-loop-worktree` docstring: "Loops publish results with `git push origin HEAD:main` (rebase/retry on non-FF) — `main` is never checked out twice." |
| Harness mints `<utc-compact>-<random>` run ids | **YES.** `runs.py:59` `new_run_id() = time.strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(2)`; observed `.bmad-loop/runs/20260718-101504-2c07`. Local time, 16 bits of entropy. |
| Harness has its own journal | **YES.** `bmad_loop/journal.py` → `journal.jsonl` per run dir, plus `save_state`/`load_state`. |
| Suffixed story keys are a live harness feature | **YES.** `bmad-loop run --help`: `--story  story: E-S / E.S (split suffix ok, e.g. 2-6a)`. |
| Six adapter profiles; four read `.agents/skills` | **YES.** `data/profiles/{antigravity,codex,copilot,gemini}.toml` → `skill_tree = ".agents/skills"`; `{claude,opencode}.toml` → `.claude/skills`. `.agents/` does not exist in this repo. |
| `import-linter` provisioned | **NO** — absent from `pixi.toml`, exactly as AD-3 states. |
| `src/shared/packages/` sibling convention | **YES** — `pyforge-atlas`, `pyforge-warden`. |
| `tomlkit = "<0.13.3"` is in the `local-recipes` env | **YES** — `[feature.local-recipes.dependencies]`, pinned for `dagster-dg-core`. Stack table is accurate. |
| Tracked story-spec archive path exists | **YES** — 93 tracked files under `_bmad-output/projects/*/planning-artifacts/specs/`. |
| "Seven loop homes provisioned" | **NOT REPRODUCIBLE TODAY** — `git worktree list` shows **4** loop homes (`pyforge-{doctor,herald,scribe,warden}`) + main + 3 story worktrees. |
| "92 skills" | **93** directories under `.claude/skills/`. |

---

## Per-AD verdicts

### AD-25 — Marshal owns run identity → **HOLE (2 MED, 2 LOW); core premise SOUND**

The premise survives scrutiny. The harness's own run dirs are per-worktree and gitignored, so the
collision AD-25 names cannot occur *at the harness level* — but it is exactly what would occur if
Marshal keyed its own Tier-3-store journals by `harness_run_id`, which is the design AD-25 replaces.
Minting at `intent` time correctly closes AD-6's ordering gap. Verdict on the rule: sound.

What it opens:

- **F-25 (MED).** "Non-run invocations (standalone `gate evaluate`, `adapters probe`) mint into a
  separate `sessions/` namespace and are **excluded from fleet-state folds by construction**." But
  FR-25 requires every gate evaluation to produce a record "**referenced from the journal** and
  retrievable per story," and FR-27's review-cap landing path re-runs the full gate before a manual
  merge. That gate verdict is the sole evidence for C-1/FR-26 on a hand-landed story — and AD-25
  routes it into a namespace structurally excluded from the run fold. **SM-1 ("zero false greens",
  target 100%) becomes unprovable from the run journal for exactly the stories that were landed by
  hand** — which is the population where it matters most (two warden stories, per FR-27's own
  motivating evidence). Needs an explicit `run_id` binding for session-namespace gate records.
- **F-30 (LOW).** `<slug>-<utc-compact>-<random>` is declared "lexicographically sortable." It sorts
  by slug first, so a fleet-wide chronological sort by run id does not work. `status` (FR-36) is a
  fleet view. Either reorder to `<utc>-<slug>-<random>` or drop the sortability claim.
- **F-31 (LOW).** "Run directories are created `O_EXCL`." `O_EXCL` is an `open(2)` flag; directories
  are created with `mkdir(2)`, which is exclusive by definition (`EEXIST`). Cosmetic, but it is a
  literal instruction to a builder and epics S-3.1 copies it verbatim.
- Note (informational): `harness_run_id` carries **local** time and 16 bits of entropy. Harmless
  under AD-25's "never a key" rule; would not be harmless if anyone later promoted it.

### AD-26 — accumulating state has one producer → **HOLE (2 CRITICAL, 2 HIGH)**

The diagnosis is correct and important: a policy-sourced frozen set cannot contain a mid-run freeze,
and AD-10 makes policy immutable. The prescribed cure is over-broad and collides with three things.

- **F-3 (CRITICAL).** AD-25 puts standalone `gate evaluate` in the `sessions/` namespace — **no run
  journal**. AD-26 makes the live frozen set *solely* a product of `core/journal.fold`. Therefore a
  standalone scope check has no frozen set; AD-17 ("anything not allowlisted is not permitted") and
  AD-8 turn "no frozen set available" into `unevaluable` → non-zero. **UJ-2 is the journey where the
  operator runs `marshal gate evaluate --scope-check` before approving, with no run in flight** —
  under AD-25 × AD-26 that command can never exit 0. It also breaks FR-19's "Exit code is a stable
  contract: 0 pass." Nothing in the architecture or in epics S-2.1/S-2.3 says which journal a
  standalone evaluation folds.
- **F-5 (CRITICAL, jointly with AD-27).** See AD-27.
- **F-8 (HIGH).** "Reading a `seed` field outside `core/journal.fold` is a meta-test failure"
  contradicts AD-16 and FR-54, which require `marshal config` to print **every** effective key with
  its winning layer. Frozen surfaces and gate mode are seed fields. This is not a cross-document
  inference — **epics Story 1.3 carries both requirements in the same acceptance-criteria block**
  (`marshal config` prints key/value/layer **and** reading a seed field outside the fold fails a
  meta-test). One story, two ACs, mutually exclusive. FR-53 policy validation has the same problem:
  it must range over every field, including seeds, and it runs in preflight, outside the fold.
  The rule needs a "read for display/validation" carve-out, or `EffectivePolicy` needs a
  `seed_view()` accessor the meta-test whitelists.
- **F-9 (HIGH).** AD-26 inverts the epic dependency graph. Epics **Story 2.3** (frozen-surface scope
  check) declares `Deps: S-1.2, S-2.2` and its ACs require "the frozen set is produced by the
  journal fold." The fold is **Story 3.2**, a different epic, downstream. Story 2.3 is not
  implementable in its declared position. Either S-2.3 gains `S-3.2` as a dependency (moving the
  fold into Epic 2 or the story into Epic 3), or the gate reads a fold-shaped value the run supplies.

### AD-27 — allowlists narrow only → **HOLE (2 CRITICAL, 1 HIGH)**

The core insight — a machine-drafted spec must not author the allowlist it is judged against — is
the single most valuable thing in the new set. The **enforcement channel is the problem.**

- **F-4 (CRITICAL — letter-vs-intent).** "Freeze declarations, freeze removals, and gate-mode changes
  … enter through policy or through an **operator-attributed journal entry carrying an approver
  identity**." Marshal has no authentication surface: no FR, NFR or AD defines how approver identity
  is established or verified, and the architecture declares no auth primitive. Meanwhile **C-10
  states plainly that "a worktree is not a sandbox"** and process isolation is explicitly Deferred.
  The governed agent session therefore runs with the operator's own shell, in the loop home, with
  write access to the run journal file and the ability to invoke the `marshal` CLI. **An agent can
  append an operator-attributed freeze-removal entry — or edit the JSONL directly — and AD-5 makes
  that entry authoritative.** AD-27 is satisfied to the letter (no *agent-writable artifact* was the
  source; a journal entry was) while the hole it closes is fully reopened. AD-1 does not help:
  AD-1 bars Marshal from *reading agent prose as instruction*, not from accepting CLI invocations.
  This same gap tears through AD-26 (fold inputs), AD-30 (unauthenticated appends) and AD-35
  (content hash with no verifier). **The trust model is undeclared and, as specified, unenforceable
  without the sandboxing that is Deferred.**
- **F-5 (CRITICAL — AD-26 × AD-27 head-on).** AD-26/FR-22/FR-50 say freezes declared *during* a run
  accumulate through the run record. AD-27 says freezes may only enter via policy or an
  operator-attributed entry. **In gate mode `none` — the L4 rung, the whole point of an unattended
  overnight wave (UJ-1) — there is no operator to attribute one, and the story that froze the files
  cannot declare it.** Under `per-epic` (§7.3: "The production ceiling") no human reads a story spec
  either. So the mid-run accumulation path that AD-26 exists to create has **no writer in either
  production gate mode**. The edited FR-22/FR-50 sentences describe a mechanism that cannot fire.
  UJ-2's opening line ("Story 6.1 amended a schema and froze three files") is now unrealizable.
- **F-18 (HIGH).** `policy_surface ∩ spec_surface` requires a **per-epic policy-declared surface**.
  Epics line 31 makes this explicit ("the gate intersects that with the epic's policy surface").
  **FR-50 — one of the two FRs that was edited for this — does not list it.** FR-50 enumerates
  "verify commands, the **initial** frozen-surface set, and the merge-subject form." The per-epic
  surface allowlist is a new mandatory project-policy key with no FR backing. And because AD-17
  forbids "everything except", an epic with no declared surface yields `∅` (every story fails) or
  is `unevaluable` (every story blocks) — there is no benign default. Any epic added without a
  policy surface entry silently bricks its whole epic.
- Sub-note: `∩` is also silently lossy. A spec declaring an empty surface yields `∅` → every change
  is out-of-scope. Fail-closed, so acceptable, but the finding message must distinguish
  "spec declared nothing" from "you touched a file outside scope" or the operator will chase ghosts.

### AD-28 — addressable entries; reconciliation closes, never re-performs → **HOLE (1 CRITICAL, 1 HIGH)**

Resolving the AD-6 × AD-21 collision by precedence is the right move. The mechanism is not achievable
under its sibling AD.

- **F-6 (CRITICAL).** "Every entry carries `id` (**unique, monotonic per run**)" — and AD-30
  mandates a **lock-free** protocol: a single `os.write()` on an `O_APPEND|O_CREAT` descriptor, no
  buffered stream, no coordination primitive, with **two concurrent writers by design** (AD-30's own
  rationale names "a long-lived buffered supervisor writer" and "a short-lived CLI append"; the
  runtime topology shows both `SUP --> JR` and `CLI --> JR`). Two independent processes cannot mint
  a unique monotonic per-run integer without shared state, a lock, or a read-modify-write of the
  file — all three of which AD-30 forecloses. Epics S-3.1 copies both requirements into one story
  and adds "a concurrency test with a long-lived writer and repeated short-lived writers produces
  zero malformed lines" — which tests atomicity, not id uniqueness, so the test would pass while the
  invariant is violated. Downstream: AD-28's `intent_id` pairing and AD-30's `(seq, ts)` total order
  both rest on it. Needs either a `(writer_id, counter)` composite (and then `(seq, ts)` ordering must
  be restated) or an explicit lock at the append boundary.
  - Second-order: a supervisor closing a **CLI-minted** intent must first *find* that `intent_id` by
    reading the journal — a read-then-append race AD-30's protocol does not address.
- **F-17 (HIGH).** "Absent evidence it stays open and is reported." Combined with AD-31 ("a command's
  verdict is the maximum over its emitted findings"), a permanently-open intent means every
  subsequent `deploy` emits a finding → non-zero verdict. That **breaks AD-21's stated property**
  ("running a mutating command twice against a converged system produces zero changes **and exit 0**"),
  FR-34, and NFR-7. AD-28's precedence clause resolves *who acts*; it does not resolve *what the
  verdict is*. An open intent needs a declared lattice classification (`warn`, not `error`) and an
  explicit exemption from the idempotence property, or AD-21's property must be restated as
  "zero changes" without the exit-0 clause.
- Structural gap (folded into F-6's remedy): the entry schema declares `phase ∈ intent|outcome` as
  **two-valued and mandatory**, yet most registered entry kinds are neither — gate verdicts, story
  transitions, budget samples, supervisor liveness, AD-10's policy-decision entry, AD-26's freeze
  declarations. Each must be forced into `outcome`, which AD-28 then requires to carry a mandatory
  `intent_id` that does not exist. A third phase (`observation` / `record`) is missing.

### AD-29 — promotion durable off the disposable ref → **HOLE (1 HIGH, 1 MED)**

Correctly identifies that AD-13 was satisfiable while still losing the spec. The durability predicate
is right. Its cost was not priced.

- **F-14 (HIGH).** Durability = "pushed to the remote, or merged to the integration branch."
  C-4 forbids a second `main` checkout, and `scripts/bmad-loop-worktree` confirms the live
  integration path is `git push origin HEAD:main`. So **in practice the only durability route is a
  network push** — and NFR-2 ("Offline by default … no network access except where a wrapped
  operation inherently requires it (**PR creation, the agent's own model calls**)") does not
  enumerate it. Consequences: (a) NFR-2's exception list is now factually incomplete;
  (b) `deploy` acquires a hard network dependency for its paper-trail function, so an offline
  operator cannot complete SM-3; (c) worse, **teardown's predicate is reachability computed at
  teardown time** (AD-29, epics S-4.2) — computing reachability against a remote requires a fetch, so
  an offline operator's every teardown refuses and must be forced with story keys named as abandoned.
  The destructive-refusal default becomes a routine forced operation, which is exactly how a refusal
  gate gets trained away.
- **F-26 (MED — implementability, high blast radius).** The promotion target is stated as
  "the tracked `planning-artifacts/specs/` archive path" (AD-11 target (c), epics S-4.1). In a loop
  home there are **two** such paths: `_bmad-output/planning-artifacts/specs/` (a **gitignored
  symlink**, per `.gitignore:723` and `scripts/bmad-switch`) and the real
  `_bmad-output/projects/<slug>/planning-artifacts/specs/`. Writing through the symlink and running
  `git add` on that path fails (`pathspec … is beyond a symbolic link`) or no-ops on the ignore rule
  — **promotion silently produces nothing, and AD-29's reachability predicate then correctly reports
  the spec as unpromoted, forever.** Neither AD names which path is canonical. This repo has already
  had a 10-hour marker/symlink desync near-miss on precisely this pair (CLAUDE.md, 2026-07-14).
  Name the real path explicitly.
- Consistency note (see F-19 group): AD-29 has Marshal **commit** promotions; FR-30 (unedited) still
  says "**staged for commit**." The FR and the AD now disagree on the deliverable.

### AD-30 — one serialized append protocol → **HOLE (1 CRITICAL)**

The physical protocol (single `os.write`, `O_APPEND`, `fsync` on intent, no held buffers) is correct
and well-motivated. One clause in it is a deliberately-legislated false green.

- **F-2 (CRITICAL).** "An unparseable line is quarantined and surfaced as a registered finding **on
  that record**, and **never makes the surrounding run state unevaluable**." AD-5 makes the journal
  the single source of run truth. AD-8 says any check that cannot reach a definite pass is
  `unevaluable`. NFR-3 says any state Marshal cannot verify is failure. **If the corrupt line was the
  `outcome` recording a gate failure, an escalation, or a freeze declaration, the fold omits it and
  the surrounding run state reads clean — a false green in the artifact the product exists to
  protect.** AD-30 does not merely permit this; it forbids the escalation that would prevent it.
  It also self-contradicts AD-31: verdict is the maximum over emitted findings, so if the quarantine
  finding classifies `unevaluable` the surrounding state *is* unevaluable (contradicting AD-30), and
  if it classifies `warn` the hole is open. Epics S-3.2 propagates the clause verbatim.
  The resilience goal is legitimate — one corrupt byte should not red the whole fleet — but the
  correct expression is *scoped* unevaluability: the affected story/decision is `unevaluable`,
  unaffected records are not. "Never unevaluable" is not a safe way to say that.
- Minor: the >4 KiB sidecar-blob write is a second, non-atomic filesystem operation. A crash between
  blob write and line append (or the reverse) yields a dangling reference. The fold needs a declared
  behaviour for a reference to a missing blob — and per F-2 it must not be "quarantine and continue."

### AD-31 — closed lattice with owned admission criteria → **HOLE (1 HIGH, 1 MED)**

- **F-10 (HIGH — internal self-contradiction).** The rule declares a **total classification
  `classify(finding_code) -> lattice_member`** — a function of the code alone — and then, two
  sentences later, requires the *same* code ("adapter not installed on this host") to classify
  `warn` in declared read-only surfaces and `unevaluable` everywhere a run depends on it. That is
  `classify(finding_code, command_context)`. Either the signature is wrong or two distinct codes are
  needed (`MRS-ADP-nnn-probe` vs `MRS-ADP-nnn-required`). As written, a builder implementing the
  declared signature cannot satisfy the declared behaviour, and epics S-2.2 copies the signature.
- **F-11 (HIGH, jointly with AD-36).** See AD-36.
- **F-24 (MED, jointly with AD-32).** See AD-32.
- Sound and worth preserving: the `not-attempted` / `unavailable` / `fail` split, and "SM-6 counts
  only `pass`." That genuinely de-games SM-6.
- Note: FR-44 states conformance-smoke results are "pass / fail / **unavailable**". Under AD-31,
  `adapters conform` is not a declared read-only surface and it is a command where a run depends on
  the adapter → `unevaluable` → non-zero exit. Reconcilable (the matrix cell can say `unavailable`
  while the command exits non-zero) but it should be said, or CI wiring will treat a missing adapter
  as a build break.

### AD-32 — session data is evidence, never control → **HOLE (2 MED)**

The diagnosis (a wedged session freezes its own usage file, so the token ceiling never fires) is
sharp and correct.

- **F-23 (MED — letter-vs-intent).** "**Every enforcement ceiling is expressed over at least one**
  externally-observed quantity." A builder pairs the existing session-authored token ceiling with a
  wall-clock ceiling, satisfies "at least one," and **the token ceiling itself remains exactly as
  defeatable as before**. The intent is that no *binding* constraint may rest solely on
  session-authored data; the letter only requires a companion. Restate as: every ceiling's
  *stop condition* must be reachable from externally-observed quantities alone.
- **F-24 (MED).** "A usage sample older than the idle threshold is **`unevaluable` (AD-8)**: the
  supervisor emits a registered finding and the wall-clock ceiling becomes the binding constraint."
  AD-8 says `unevaluable` "projects to a non-zero exit and **blocks progression**," and AD-31 folds
  it into the command verdict as the maximum. So the intended graceful degradation is, by the labels
  it invokes, a run halt — and it fires on the *normal* idle case, which the FR-12 ladder is
  simultaneously handling with a nudge. Two mechanisms fire on one condition with opposite
  intentions. This needs its own non-blocking classification, not `unevaluable`.
- **F-28 (MED — pre-existing, reinforced not fixed).** AD-32 strengthens AD-9, and the runtime
  topology states: "The supervisor has **no channel into** the agent session — arrows to it are
  observation only. **Its sole write is the journal.**" FR-12 requires the supervisor to
  "**nudge**, then **stop-and-retry**, then defer" (epics S-3.5 verbatim). A nudge is a write into
  the session (`tmux send-keys`); stop-and-retry kills and respawns it. The topology statement is
  false as written. It should read: observation-only *inputs*; writes limited to the journal plus a
  declared, enumerated set of control actions.

### AD-33 — truth partitioned by domain → **SOUND**

Genuinely resolves the AD-5 × AD-12 convergence-on-permanent-red problem, and the `claimed_*`
convention is the right shape for FR-39's reconciliation. No contradiction found with AD-5 (which it
narrows explicitly), FR-33, FR-39 or SM-3. The only soft spot: "every derived artifact declares, per
field, its canonical domain" implies a per-field domain registry that no module in the source tree
owns and no story creates — `core/status.py` is named for reconciliation, not for the registry.
Below the reporting bar; noting for the Epic-5 author.

### AD-34 — redaction is a port-boundary property → **HOLE (2 HIGH, 1 MED)**

The catch (AD-18's three-point enumeration is falsified by notifications, PR bodies and commit text)
is correct and the `Redacted` wrapper type is the right enforcement shape.

- **F-15 (HIGH).** The membership criterion is "**every port whose implementation emits bytes
  outside the process**," and "adding a port without classifying it fails the build." By that
  criterion `HarnessPort` and `ProcessPort` are egress ports — they spawn a child with argv and an
  environment. But an agent session **requires** its credentials in that environment. Classify them
  egress and they must accept only `Redacted` payloads → every run fails to authenticate. Classify
  them non-egress and the stated criterion is false, the registry's completeness check is
  meaningless, and NFR-11's guarantee has an undocumented exemption. The criterion needs to be
  "emits bytes to a **durable or third-party** sink," with process-spawn explicitly carved out and
  the carve-out justified.
- **F-16 (HIGH).** "**Pane-derived content is redacted at capture**, before it enters `core`,
  because `core` cannot redact (AD-4)" — and the single redactor lives in `core/egress.py`
  (source tree). So `adapters/observer_mux.py` must import `core`. The declared dependency direction
  is "**one-way and absolute**: `cli → core`, `cli → ports`, `ports ← adapters`. `core` imports
  nothing from `adapters`, `ports`, or `cli`. `adapters` never import each other." **`adapters → core`
  is never authorized.** AD-3 and AD-4 are enforced by import-linter contracts written from those
  declarations (epics S-1.1), so the contract as specified would reject the import AD-34 requires.
  Either add the edge explicitly, or the capture-time redactor is a second redactor — which
  falsifies AD-34's "one redactor" premise and reintroduces the AD-18 failure at a new site.
- **F-20 (MED).** AD-34 says "AD-18 is subsumed by this rule," and the capability map says
  "AD-34 (subsumes AD-18)" — but **AD-18 is still present, untagged, with binds, in a document whose
  status is `final`**, and its rule text ("the only three places bytes leave Marshal") is now a
  statement AD-34 proves false. A builder reading AD-18 in isolation ships the leak. Mark it
  `[SUPERSEDED BY AD-34]` in the rule text itself.

### AD-35 — content-addressed, write-once materialized policy → **HOLE (1 CRITICAL, 1 MED)**

The hazard it names (idempotent `init` re-run swapping the value under a live supervisor) is real and
the pin-at-spawn cure is right. It is also, together with AD-10, **not implementable against the
pinned harness.**

- **F-1 (CRITICAL — implementability + cross-project bleed).** Verified above:
  `bmad-loop 0.9.0` hard-codes `POLICY_FILE = .bmad-loop/policy.toml` relative to the project root and
  exposes **no** policy-path flag on `run`. That file is **git-tracked in this repo**. Therefore:
  1. A **content-addressed, never-overwritten** artifact cannot be what the harness consumes.
     Marshal must render a fixed-name file at a fixed path — the opposite of AD-35's rule.
  2. That fixed path is a **shared repo-level tracked file**, which **AD-10's closing sentence
     explicitly forbids Marshal from editing** ("No Marshal code edits a shared repo-level file to
     express project-specific configuration") and which FR-50 exists to eliminate.
  3. **FR-51's tier-batching mandates it.** "Where the harness supports only run-level model
     selection, Marshal batches stories by tier" — batching by tier *is* rewriting
     `[adapter.dev].model` between batches. That is precisely the live hand-edited
     `HARD-STORY BATCH PROCEDURE` block in `.bmad-loop/policy.toml`, which FR-51 cites as its own
     motivating evidence. The PRD requires the automation of an edit the architecture forbids.
  4. Because the file is tracked and **loops publish with `git push origin HEAD:main`**, a
     Marshal-written `policy.toml` in a loop home rides the loop's own commits to `main` and lands on
     every other project — a **real cross-project state bleed**, the exact failure AD-11 exists to
     prevent. This is not hypothetical: `../local-recipes-loop-pyforge-herald/.bmad-loop/policy.toml`
     is dirty **right now** (8+/22-) for exactly this reason.
  5. **No story owns any of this.** Grep of `epics.md` for `policy.toml` returns nothing;
     S-1.3 materializes an EffectivePolicy that nothing conveys to the harness; S-1.7 and S-3.3 use
     the seam but never render harness policy.

  The likely remedy is available and cheap — declare `.bmad-loop/policy.toml` a **derived artifact**
  under AD-12 rendered by `adapters/harness_bmadloop.py` from the canonical content-addressed
  EffectivePolicy — but it must be *decided*, because it requires (a) amending AD-10's closing
  sentence, (b) adding the file to `.gitignore` or otherwise guaranteeing it never rides a loop
  commit to `main`, and (c) a story. Without that decision the entire policy-composition epic has no
  path to the engine it is composing policy for.
- **F-27 (MED).** Content-addressed and never overwritten means there must be a **current pointer**
  — some mutable per-home file naming the live hash. AD-35 does not define one. With two artifacts on
  disk and no live run, `marshal config` (FR-54) has no defined answer, and AD-21's convergence check
  for `init` has nothing to compare against. Name the pointer and its update protocol.

### AD-36 — declared projection mechanism, non-trivial detector → **HOLE (1 HIGH)**

Catching "a symlink projection makes drift detection structurally always-clean" is a good catch, and
"reporting `clean` for a check that cannot fail is a meta-test failure" is a rule worth keeping.

- **F-11 (HIGH).** The cure introduces a result state the lattice cannot hold. AD-36 requires a link
  projection to report **`not-applicable`** for content drift. AD-31 states "**the lattice gains no
  members**" and "a command's verdict is the maximum over its emitted findings' classifications."
  `not-applicable` is not a member, so `classify()` must map it to one, and **both plausible mappings
  break something**: → `clean` is the structural false green AD-36 forbids in the same sentence;
  → `unevaluable` makes FR-42's preflight drift check block **every** symlink-projected run
  permanently (AD-8: "blocks progression"), on the default mechanism, on the default platform.
  Epics S-6.2 propagates `not-applicable` with no lattice mapping. Either AD-31 admits a
  non-participating result kind (findings that are recorded but excluded from the verdict fold — a
  meaningful change to a "closed lattice"), or AD-36 must require link projections to run a
  *different* non-trivial check (link-target identity **is** falsifiable — that is the actual answer,
  and AD-36 half-states it) and never emit `not-applicable` at all.

### AD-37 — fourth write target; ephemeral homes exempt → **HOLE (1 HIGH, 1 MED); premise WEAK**

- **F-7 (HIGH).** Three-way contradiction, propagated:
  - **FR-45** (unedited): conformance results "accumulate into a dated, **tracked** artifact." In this
    repo's vocabulary "tracked" means git-tracked — that is the entire Tier-2/Tier-3 distinction the
    glossary defines.
  - **The architecture's own Operational envelope** (§ State on disk): "The tracked spec archive
    **and the conformance matrix** live in tracked planning artifacts." AD-37 contradicts a sentence
    in its own document that was not updated.
  - **Epics S-6.4 / S-6.6** now say the record and matrix live at the machine-scoped path,
    "**not into any project's artifacts**."

  Consequences of AD-37 winning: the matrix is not in any clone, not reviewable in a PR, not durable
  under NFR-8's "self-owned evidence" in the sense every other artifact means it, and **not readable
  by anyone but the operator of that one machine** — while FR-45 designates it "the only place
  Marshal makes a portability claim" and SM-6 measures the product on it. Also note AD-37 does not
  actually solve the divergence it names: N machines still produce N matrices; the location just
  moved out of git, where the divergence would at least have been visible.
- **Premise is weak.** AD-37 asserts the matrix has "no legal home under AD-11's three targets."
  Target (c) is "explicitly-named promotion targets under the active project's tracked planning
  artifacts" — the matrix is per-machine rather than per-project, which is a real argument, but the
  stated premise ("no legal home") overstates it. A `matrix/<hostname>.md` under tracked artifacts
  satisfies AD-11 unchanged and keeps FR-45, NFR-8 and the Operational envelope all true.
- **F-29 (MED).** The ephemeral exemption is written against **AD-13** ("exempt from AD-13's
  promotion predicate"), but **AD-29 supersedes AD-13's predicate** ("Teardown's refusal predicate is
  reachability computed at teardown time, never a journal flag"). The exemption names the superseded
  rule. Vacuous today (an ephemeral home has no promotions, so reachability passes trivially), but it
  is a live trip-wire the moment the smoke story produces any tracked artifact. Epics S-6.5 copies
  "(AD-37, AD-13)".

### AD-38 — a resolved feed reports its own completeness → **HOLE (2 HIGH)**

The best-motivated of the new set — AD-23's numeric-only key would have re-created the very incident
AD-23 cites. Both halves of the cure are underspecified.

- **F-12 (HIGH — direct textual contradiction, confirmed against the live harness).** AD-38 says
  "the canonical key admits an optional ordered suffix." **AD-23's rule text still says the key is
  `<epic>.<seq>`, purely numeric on both parts**, and that "non-conforming input is a registered
  finding." AD-23 was not amended; only the Consistency Conventions table was. A builder implementing
  AD-23 as written rejects suffixed keys. And this is not academic: **the pinned harness's own CLI
  documents them** — `bmad-loop run --story` accepts "E-S / E.S (**split suffix ok, e.g. 2-6a**)".
  AD-23 as written cannot round-trip a key the harness it wraps accepts. Additionally, AD-38 says
  suffixes are "**normalized on read**" without saying normalized *to what*: if the suffix is dropped,
  `6.1a` and `6.1b` collide into one key across the journal, the spec archive, the merge subject and
  the feed — silently merging two stories, which is strictly worse than the incident. Epics S-1.2
  says "preserved and normalized," which is the right answer; the architecture must say it.
- **F-13 (HIGH — letter-vs-intent).** "Every feed resolution reports `resolved N of M` and produces a
  non-zero verdict when `N < M`." **`M` is undefined.** If `M` is the count of keys the parser
  produced, then a parser that silently drops suffixed keys yields `N == M` and the check reports
  a triumphant "resolved 18 of 18" — **exactly reproducing the documented incident that halved the
  actionable feed, now with a completeness guarantee stamped on it.** `M` must be defined as the
  count from the raw source *before* key parsing (e.g. non-empty story records in the feed file),
  and the AD must say so; the "silently shortened feed is impossible" claim is otherwise false.

### AD-39 — envelope field relationships and independent versions → **HOLE (2 MED)**

`status` as a pure function of `verdict`, and splitting `data_version` from `schema_version`, are
both correct and cheap.

- **F-21 (MED).** **AD-14's rule text still enumerates the envelope without `data_version`**
  (`{schema_version, command, status, verdict, data, findings[], assumptions[]}`), while AD-39, the
  Consistency Conventions table and epics S-1.1 all include it. AD-14 was not amended. Two normative
  envelope definitions in one `final` document.
- **F-22 (MED).** AD-39's meta-test asserts "`status`, `verdict`, and the **maximum finding
  severity** are mutually consistent." The Consistency Conventions table states "**Severity is
  presentational**; the lattice member comes from `classify(code)`." If severity is presentational it
  is free to disagree with the lattice — e.g. a code classified `unevaluable` carrying severity
  `warn` for readability. Then the meta-test fails on correct output, or severity is not
  presentational after all and the table is wrong. Pick one: either severity is derived from
  `classify()` (and the table's sentence goes), or the meta-test drops severity and asserts only
  `status ≡ f(verdict)`.

---

## PRD edit consistency check (FR-22, FR-50)

Both edits are locally accurate and correctly cite their ADs. Neither broke an adjacent FR's logic.
Three propagation gaps and one substantive gap:

- **F-18 (HIGH, above).** FR-22 now speaks of "the **project-declared** surface," a project-layer
  concept. **FR-50 is the FR that enumerates what the project layer supplies, it was edited in the
  same pass, and it does not list it.** This is the one substantive break.
- **F-19 (MED — unpropagated, 2 sites).** The edits establish that a story cannot author its own
  freeze. Two upstream PRD sites still say it can:
  - **§3 Glossary**: "**Frozen surface** — a set of files **a prior story declared** contractually
    stable." Under FR-22-as-edited + AD-27, a story cannot declare one.
  - **§2.3 UJ-2**: "**Story 6.1 amended a schema and froze three files.**" The journey's premise is
    now unrealizable in any unattended gate mode (see F-5), and its second beat — the operator
    running `marshal gate evaluate --scope-check` with no run in flight — is structurally
    `unevaluable` (see F-3). **UJ-2 is the journey that motivates the entire gate feature and it no
    longer describes a reachable sequence.**
- **FR-30 vs AD-29 (folded into F-14).** FR-30 still says the spec is "**staged for commit**";
  AD-29 and epics S-4.1 require Marshal to commit it and to treat a merely-staged file as *not*
  promoted. The FR is now describing the state AD-29 explicitly declares insufficient.
- Checked clean: FR-19/FR-20/FR-21 (unaffected by the FR-22 edit), FR-24's mid-run gate-mode decision
  record (consistent with AD-27's operator-attribution requirement), FR-49/FR-51/FR-53/FR-54
  (unaffected by FR-50's "initial" qualifier), SM-1, C-1, C-5, NFR-3, NFR-5. The word "initial" in
  FR-50 is exactly the right minimal edit.

---

## Findings, ranked

| # | Sev | AD(s) | Finding |
| --- | --- | --- | --- |
| F-1 | **CRITICAL** | AD-35, AD-10, (FR-51) | Composed policy has **no path to the harness**. `bmad-loop 0.9.0` hard-codes `.bmad-loop/policy.toml` with no policy-path flag; that file is **git-tracked** here; loops publish by `git push origin HEAD:main`, so a Marshal-written copy bleeds to `main` and to every other project. AD-10 forbids editing it; FR-51's tier-batching requires editing it. No story owns the conveyance. Live proof: `loop-pyforge-herald` has it dirty right now. |
| F-2 | **CRITICAL** | AD-30 | "An unparseable line … never makes the surrounding run state unevaluable" **legislates a false green** into the single source of run truth, against NFR-3/AD-8, and self-contradicts AD-31's max-over-findings fold. Propagated to epics S-3.2. |
| F-3 | **CRITICAL** | AD-25 × AD-26 | Standalone `gate evaluate --scope-check` has **no run journal** (AD-25 `sessions/` namespace) and therefore no frozen set (AD-26 sole-producer) → permanently `unevaluable`. Kills **UJ-2** and FR-19's stable exit contract. |
| F-4 | **CRITICAL** | AD-27 (+AD-26, AD-30, AD-35) | The "operator-attributed journal entry carrying an approver identity" escape hatch is **agent-reachable**: no auth primitive is defined anywhere, C-10 states the worktree is not a sandbox, and process isolation is Deferred — so the governed session can invoke the CLI or write the JSONL directly. AD-27 satisfied to the letter, defeated in fact. **The trust model is undeclared.** |
| F-5 | **CRITICAL** | AD-26 × AD-27 | Mid-run freeze accumulation has **no writer in gate mode `none` or `per-epic`** — the story can't declare it (AD-27) and no operator is present (unattended). The edited FR-22/FR-50 sentence describes a mechanism that cannot fire in either production mode. |
| F-6 | **CRITICAL** | AD-28 × AD-30 | A per-run **unique monotonic `id`** is unachievable under AD-30's lock-free, uncoordinated, two-writer append protocol. `intent_id` pairing and `(seq, ts)` total order both rest on it. Epics S-3.1's concurrency test would pass while the invariant is violated. Also: `phase ∈ intent|outcome` has no third value for the many entry kinds that are neither. |
| F-7 | HIGH | AD-37 | Conformance matrix location contradicts **FR-45** ("tracked artifact"), **NFR-8**, and **the architecture's own Operational envelope**; propagated to epics S-6.4/S-6.6 ("not into any project's artifacts"). AD-37's premise ("no legal home under AD-11") overstates: a per-host file under tracked artifacts satisfies AD-11 unchanged. |
| F-8 | HIGH | AD-26 × AD-16/FR-54 | "Reading a `seed` field outside the fold is a meta-test failure" vs `marshal config` printing every key and FR-53 validating every key. **Epics Story 1.3 carries both requirements in one AC block.** |
| F-9 | HIGH | AD-26 | **Epic dependency inversion**: S-2.3 (scope check) requires the journal fold, which is S-3.2 in the next epic; S-2.3 declares `Deps: S-1.2, S-2.2`. Not implementable in its declared position. |
| F-10 | HIGH | AD-31 | Self-contradiction: `classify(finding_code)` is declared total over the code alone, then required to return different members for the same code depending on the command surface. |
| F-11 | HIGH | AD-36 × AD-31 | `not-applicable` has **no lattice member** ("the lattice gains no members"). → `clean` is the false green AD-36 forbids; → `unevaluable` permanently blocks FR-42 preflight on the default mechanism. Propagated to epics S-6.2. |
| F-12 | HIGH | AD-38 × AD-23 | **AD-23's rule text still says "purely numeric on both parts"** and was not amended. Confirmed broken against the pinned harness, whose `run --story` accepts `2-6a`. "Normalized on read" also does not say whether the suffix survives — dropping it collides `6.1a`/`6.1b` into one key. |
| F-13 | HIGH | AD-38 | `resolved N of M` is **vacuous**: `M` is undefined, and if `M` comes from the parsed set a suffix-dropping parser reports "18 of 18" while reproducing the exact incident. "A silently shortened feed is impossible" is false as written. |
| F-14 | HIGH | AD-29 × NFR-2 | Promotion durability requires a **network push** (only route, given C-4 + the live `push origin HEAD:main` integration path), which NFR-2's exception list does not include. Offline `deploy` cannot satisfy SM-3, and offline **teardown refuses every time** → forced teardown becomes routine. FR-30 also still says "staged for commit." |
| F-15 | HIGH | AD-34 | The egress criterion ("emits bytes outside the process") captures `HarnessPort`/`ProcessPort`, which **must** pass credentials to the child. Classify them egress → runs cannot authenticate; classify them out → the criterion and its build-failing completeness check are meaningless. |
| F-16 | HIGH | AD-34 × dependency direction | Capture-time pane redaction requires `adapters → core`, an edge the "one-way and absolute" dependency declaration never authorizes — and which the AD-3/AD-4 import-linter contracts (epics S-1.1) would be written to reject. The alternative is a second redactor, falsifying AD-34's premise. |
| F-17 | HIGH | AD-28 × AD-21 | A permanently-open `intent` emits a finding on every subsequent run → non-zero verdict → breaks AD-21's "**exit 0**" convergence property, FR-34 and NFR-7. AD-28 resolved who acts, not what the verdict is. |
| F-18 | HIGH | AD-27 × FR-50 | The **per-epic policy surface** that `policy_surface ∩ spec_surface` requires is not in FR-50's enumeration — in the very FR edited for this change. With AD-17 in force, an epic missing the key yields `∅` or `unevaluable`: no benign default, whole epic bricked. |
| F-19 | MED | FR-22/FR-50 edits | Unpropagated: **§3 Glossary** ("a set of files a prior story declared") and **§2.3 UJ-2** ("Story 6.1 … froze three files") both still assert story-authored freezes. UJ-2 — the journey motivating the gate feature — is no longer a reachable sequence (see F-3, F-5). |
| F-20 | MED | AD-34 / AD-18 | AD-18 remains present, untagged, with binds, in a `final` document, and its rule text is now **false**. Mark it `[SUPERSEDED BY AD-34]` in the rule itself, not only in the capability map. |
| F-21 | MED | AD-39 / AD-14 | Two normative envelope definitions: AD-14's key list omits `data_version`; AD-39, the conventions table and epics S-1.1 include it. |
| F-22 | MED | AD-39 × conventions | The mutual-consistency meta-test over max finding **severity** contradicts "Severity is presentational; the lattice member comes from `classify(code)`." |
| F-23 | MED | AD-32 | "At least one externally-observed quantity" is letter-satisfiable by *pairing* a wall-clock ceiling with an unchanged, still-defeatable session-authored token ceiling. The *stop condition* must be externally reachable, not merely accompanied. |
| F-24 | MED | AD-32 × AD-8/AD-31 | Labelling a stale usage sample `unevaluable` invokes a **blocking** classification for an intended graceful degradation — and fires on the ordinary idle case the FR-12 ladder is already handling. |
| F-25 | MED | AD-25 × FR-25/FR-27 | The `sessions/` namespace strands gate-evidence records for standalone and review-cap (hand-landed) gates outside the run fold, exactly where **SM-1** most needs provable evidence. |
| F-26 | MED | AD-29/AD-11 | Promotion target is ambiguous between the **gitignored symlink** `_bmad-output/planning-artifacts/specs/` and the real `_bmad-output/projects/<slug>/…`. `git add` through the symlink fails or no-ops → promotion silently produces nothing and AD-29 then reports it unpromoted forever. This repo has a documented near-miss on this exact pair. |
| F-27 | MED | AD-35 | Content-addressed + never-overwritten with **no current pointer** defined: `marshal config` and AD-21's convergence check have no way to resolve which artifact is live. |
| F-28 | MED | AD-32/AD-9 (pre-existing) | "The supervisor has no channel into the agent session … its sole write is the journal" is falsified by FR-12's **nudge / stop-and-retry** ladder (epics S-3.5). AD-32 reinforces AD-9 without correcting it. |
| F-29 | MED | AD-37 × AD-29 | The ephemeral exemption is written against **AD-13**, whose teardown predicate **AD-29 superseded**. Vacuous today; a trip-wire the moment the smoke story produces a tracked artifact. Epics S-6.5 copies the stale citation. |
| F-30 | LOW | AD-25 | Slug-first run ids are not chronologically sortable across the fleet, contradicting "lexicographically sortable" as a fleet property (FR-36). |
| F-31 | LOW | AD-25 | "Run directories are created `O_EXCL`" — `O_EXCL` is an `open(2)` flag; `mkdir(2)` is already exclusive. Copied verbatim into epics S-3.1. |
| F-32 | LOW | doc facts | "Seven loop homes provisioned concurrently" — **4** exist today (`git worktree list`). "92 skills" — **93** directories. Both are cited as live evidence for FR-4/SM-5 and FR-41. |

**Distribution:** 6 CRITICAL · 12 HIGH · 11 MED · 3 LOW.
**By AD:** AD-26, AD-27, AD-30, AD-35, AD-38 carry the CRITICALs. **AD-33 is the only new AD with no
finding.** AD-25, AD-29, AD-32, AD-34, AD-36, AD-37, AD-39 carry HIGH/MED holes.

**Pattern.** Nine of the eighteen CRITICAL/HIGH findings are the same failure of process, not of
thought: **the new ADs amended the rule that was wrong without amending the rules, FRs and journeys
that depended on it.** AD-38 vs AD-23's untouched text; AD-39/AD-14's two envelopes; AD-34/AD-18's
false-but-live rule; AD-37 vs the Operational envelope in its own document; AD-29 vs FR-30; AD-27 vs
FR-50, the Glossary and UJ-2; AD-37's stale AD-13 citation. Each is individually cheap to fix, and
each is a live trap in a document marked `status: final` that a builder will read one AD at a time.
A single amendment pass that propagates each new AD into its predecessors, its FRs and its journeys
would clear the whole class.

**Second pattern, more serious.** F-1, F-4 and F-14 are all the same *kind* of gap: **the new ADs
reason rigorously about Marshal's internal consistency and do not reason about the substrate.**
The harness's fixed policy path, the absence of a sandbox around the governed agent, and the network
cost of git durability are all properties of the world Marshal runs in, and all three invalidate an
AD written without them.

---

## Gate verdict

> ## BLOCKED-ON
>
> 1. **F-1** — decide how composed policy reaches `bmad-loop` (the harness reads one hard-coded,
>    git-tracked path; AD-10 forbids writing it; FR-51 requires writing it; loop pushes carry it to
>    `main`). Amend AD-10/AD-35, add the `.gitignore`/render decision, and give it a story.
> 2. **F-2** — remove AD-30's "never makes the surrounding run state unevaluable" and replace it
>    with *scoped* unevaluability. As written it legislates a false green into the source of truth.
> 3. **F-3** — define which journal a standalone `gate evaluate` folds, or UJ-2 and FR-19's exit
>    contract are unreachable.
> 4. **F-4** — declare the trust model. Either state that the governed agent is trusted not to write
>    the journal/CLI (and accept that AD-27's guarantee is advisory), or specify the mechanism that
>    makes approver attribution unforgeable. Do not leave it implied.
> 5. **F-5** — resolve AD-26 × AD-27: name the writer of a mid-run freeze under gate mode `none` and
>    `per-epic`, or state that mid-run freezes require `per-story-spec-approval` and amend
>    FR-22/FR-50 to say so.
> 6. **F-6** — reconcile AD-28's unique monotonic `id` with AD-30's lock-free two-writer protocol
>    (composite id, or a declared lock), and add the third `phase` value.
>
> **Also required before Epic 1 opens** (cheap, mechanical, but they will mislead a builder on day
> one): **F-9** (S-2.3's dependency is wrong — it blocks sequencing), **F-12** and **F-21** (two
> normative definitions of the story key and of the envelope, in the two stories that establish
> them), **F-18** (FR-50 must gain the per-epic surface key), and **F-20** (AD-18 must be marked
> superseded).
>
> The remaining HIGH findings (F-7, F-10, F-11, F-13, F-14, F-15, F-16, F-17) are epic-scoped and can
> be resolved at the head of the epic that owns them — but each is a *confirmed* defect, not a
> preference, and none should reach implementation unresolved. F-13 in particular is a completeness
> guarantee that is currently false.

**On the value of AD-25..39 overall:** the fifteen ADs are a substantial net improvement and every
hole they were written to close is genuinely closed. AD-33 is exemplary. AD-38's diagnosis, AD-27's
core insight, AD-30's physical protocol, AD-29's durability predicate and AD-31's matrix-state split
are all keepers. The finding count is high because they were written fast and under pressure, not
because they were written badly — and because nothing had yet probed them. That probe is this
document. The block is on six specific decisions, not on the design.
