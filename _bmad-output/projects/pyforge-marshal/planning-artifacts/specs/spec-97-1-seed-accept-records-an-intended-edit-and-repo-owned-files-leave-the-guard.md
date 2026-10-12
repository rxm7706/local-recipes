---
title: "97.1: Seed accept records an intended edit, and repo-owned files leave the guard"
type: 'fix'
created: '2026-10-12'
status: 'done'
baseline_revision: fecc3f366d35c6643546cc0d1931ff447057f2e1
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/extraction-manifest.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/prds/prd-pyforge-marshal-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-86-2-local-recipes-is-genesis-adopted-so-the-seed-adopt-oracle-goes-green.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/seed.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/adopt.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/update.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/check.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/verbs/preconditions.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/detect/hashes.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/detect/findings.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/state/store.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/state/schema.json
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/templates/manifest.yaml
  - src/shared/packages/pyforge-marshal/tests/integration/test_local_recipes_empty_plan.py
  - src/shared/packages/pyforge-marshal/tests/meta/test_finding_remedy_reference_sync.py
  - src/shared/packages/pyforge-marshal/docs/finding-remedy-reference.md
  - src/shared/packages/pyforge-marshal/docs/adoption-guide.md
---

<intent-contract>

## Intent

**Problem:** this repo is genesis-adopted (Story 86.2), so `.marshal/seed-state.yml` claims files with a recorded
content hash, and rung 6 of the precondition ladder (`seed/verbs/preconditions.py`) refuses `adopt` and `update`
when a claimed file no longer matches. The SC-02 oracle (`tests/integration/test_local_recipes_empty_plan.py`, CI
check `oracle` in `marshal-local-recipes-seed-oracle`) runs that adopt dry run on every PR. So any PR that edits a
claimed file goes red, and no seed verb can record an edit the operator meant. Line numbers below are at
`f478cfbc5a`.

**The evidence:**
- **Found on doctor Story 42.1 (PR #2150, 2026-10-12).** One new `_DOCTOR_SOURCE_TASKS` row in `scripts/detectors.py`
  moved its hash from `3ea83244` to `20bf7374`, and the oracle failed with `PreconditionFailure:
  managed-content-modified`. Reproduced on a fixture of this repo's claimed files: `marshal seed adopt` exits 3 with
  the same refusal, and `marshal seed check` reports it as HARD.
- **No sanctioned writer.** `adopt` first-claims only ids that state does not record (`seed/verbs/adopt.py:560`) and
  writes state only when its plan has actions (`:1360`); this repo's adopt plan is empty. `--force` skips rung 6 and
  records nothing (`cli/seed.py:1280`-`:1285`, `preconditions.py:45`-`:60` and `:720`). 42.1's re-record was done by
  hand, as a one-time operator-authorized exception to `SPEC.md:287`'s do-not-hand-edit rule.
- **The published remedy is wrong.** `managed-file-modified` says "run `marshal seed update --force` to accept it as
  the new baseline" (`seed/detect/findings.py:117`-`:120`, `docs/finding-remedy-reference.md:18`,
  `docs/adoption-guide.md:71`). FR-101 says `update --force` discards local edits, and it does: it recopies from the
  packaged template (`seed/verbs/update.py:821`-`:931`). The template ships no payload for any `copied-managed` file
  (`adopt.py`'s known limitation (1)). On the fixture, `marshal seed update --run --yes --force` exits 2 ("copier recopy
  failed"), and where staging succeeds `_staged_bytes_for` raises `InternalError` (`update.py:704`-`:728`).
  `managed-region-modified` names the same `update --force`, which for a region overwrites it.
- **Three of the five claimed files belong to the repo.** Story 86.2's bootstrap claimed the five `copied-managed`
  files by recording this repo's own content (`adopt.py:882`-`:890`). Commits from 2026-09-12 to 2026-10-12:

  | File | Manifest id | Commits | Why it changes |
  |---|---|---|---|
  | `scripts/detectors.py` | `detector-registry` | 11 | its 28-row `_DOCTOR_SOURCE_TASKS`, the hand list the manifest's rationale says the registry does not need (`seed/templates/manifest.yaml:188`-`:192`); every new Doctor source adds a row |
  | `docs/dreams/README.md` | `dreams-readme` | 65 | its 109-row Dream table; every new Dream adds a row (AGENTS.md pre-PR item 8) |
  | `.github/workflows/detectors.yml` | `detectors-ci-workflow` | 4 | this repo's own 238-line CI; it does not run `marshal seed check`, which the manifest's rationale says it does |
  | `scripts/bmad-switch` | `bmad-switch` | 2 | model machinery |
  | `scripts/bmad-loop-worktree` | `bmad-loop-worktree` | 1 | model machinery |

  The Spec companion's watch metric (`extraction-manifest.md` § *Watch metrics*) says a class assigned wrong is fixed
  in the manifest, not in the engine. `copied-managed` promises "regenerated wholesale", which no payload can deliver
  for these files, so all the class adds here is a guard against the repo's own maintainers.
- **The guard ignores the class.** Rung 6's input (`_managed_records`, `adopt.py:605`, and its copy in `update.py:426`)
  and `seed check`'s whole-file hash check (`seed/verbs/check.py:593`-`:596`) take every state record whatever its
  manifest class. So a `copied-seeded` record, which `seed init` writes for every file it seeds, is hash-guarded,
  against `CLASS_BEHAVIOR`'s "hand-edit: expected and fine" (`seed/model/artifact.py`).

**Approach.** Three parts, one PR.
1. **`marshal seed accept <artifact-id>[#<region>]`, the eighth seed verb.** It runs on the A-01 pipeline. It resolves
   the manifest entry and its state record and hashes what is on disk with `seed.detect.hashes.hash_content`: the
   whole file for a whole-file record, and for a hybrid record each recorded region's body, parsed with the entry's
   format (`regions.parse.parse_regions`, `detect.hashes.region_body_text`). Then it plans the re-record (old hash to
   new hash for each file or region). It is a dry run by default (FR-124). `--apply` writes, and needs `--reason`.
   - **The one write.** It writes only `.marshal/seed-state.yml`, and only through `seed.state.store.write_state`
     (one atomic replace, P-08). A dry run writes nothing, `.marshal/plan.json` included.
   - **The journal.** It is an optional `acceptances` list in the state file, written in the same atomic replace as
     the new hash, so the record and its journal cannot disagree. One entry per re-recorded file or region: `id`,
     `region` (null for a whole file), `path`, `previous_sha`, `accepted_sha`, `accepted_at`
     (`store.utc_timestamp()`), `accepted_by` (the git committer identity, `git var GIT_COMMITTER_IDENT` without its
     timestamp), `head` (`git rev-parse HEAD`) and `reason`. A separate journal file would be a second Genesis-owned
     file (AD-52) and a second write that could fail after the first. The schema declares the key optional (absent
     reads as empty), and the writer emits it only when it is non-empty. So a repo that never accepts keeps a
     byte-identical state file that an older pyforge-marshal can still read.
   - **Its refusals.** It climbs rungs 1-2 of the ladder: a git repo, and a clean worktree under `--apply`, so the
     accepted bytes are committed bytes and git stays the undo. It refuses an id the manifest does not declare
     (`UsageError`). It refuses with a `PreconditionFailure` naming the reason:
     - an artifact state does not record;
     - a current manifest class that no guard reads: `copied-seeded`, `generated-derived`, `referenced`,
       `unclassified-deferred`, or a directory entry;
     - a path a recorded skip matches, a path that escapes the repo, or a file that is absent;
     - a hybrid file whose regions do not parse, or a named region that state does not record;
     - a git identity that git cannot resolve.
   - **Nothing to do.** An unchanged hash writes nothing and exits 0.
2. **The repo's own files leave the guard.** `detector-registry`, `dreams-readme` and `detectors-ci-workflow` move
   from `copied-managed` to `copied-seeded` in `seed/templates/manifest.yaml`, each with a rationale that says why it
   is repo-owned. The guard follows the manifest's current class: rung 6's input (both `_managed_records`) and `seed
   check`'s whole-file hash check skip a record whose current entry is `copied-seeded`. `bmad-switch` and
   `bmad-loop-worktree` stay `copied-managed`. `model_version` stays `1.0.0`, for three reasons:
   - no installed repo has to write anything;
   - a migration can only emit file actions (`migrate/registry.py` `Migration`), and the change is to the guard;
   - a bump with no registered migration makes `chain()` refuse every adopted repo's update.

   A record's stored `class` keeps what was claimed, and the guard reads the manifest. The PRD's Extraction Manifest
   tables and the Spec companion `extraction-manifest.md` move the three rows in this PR, so the contract and the
   manifest never disagree on `main`.
3. **The remedies name the verb that accepts an edit.** `REMEDIES` for `managed-file-modified` and
   `managed-region-modified`, their rows in `docs/finding-remedy-reference.md`, `docs/adoption-guide.md` and rung 6's
   refusal remedy name `marshal seed accept` for an intended edit. They keep `update --force` only as "discard the
   edit" (FR-101).

Ledger key: `97-1-seed-accept-records-an-intended-edit-and-repo-owned-files-leave-the-guard`.
Type / Effort / Deps: fix / M / — (Story 97.2 depends on this story).

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-marshal` CAP-12 (adopt refuses on a hand-edited managed artifact, and its
  plan is empty on this repo, SC-02), CAP-13 (each finding carries a documented remedy, NFR-M3), CAP-17 (one
  do-not-hand-edit state file; this verb is its sanctioned writer, so `SPEC.md:287` stays true), CAP-10 (every
  artifact in exactly one class; the reclassification is a manifest diff) and CAP-11 (a hand-edit inside a region is
  detected by its body hash). No CAP is minted and no `SPEC.md` text changes.
- **No flag.** Under `spec-feature-flag-governance` Q1 a `fix` needs no flag: a guard that refuses a repo's own
  routine edits, and a remedy that names a command that cannot do what it says, are the defect.
- **Origin.** `docs/dreams/pyforge-marshal.md` Realization log, 2026-10-12 (seed accept and repo-owned managed
  artifacts). Operator ruling 2026-10-12, verbatim label "Sign off + fix story (Recommended)": "Authorize this one
  recorded hash re-record for 42.1, noted in 42.1's triage log and the marshal memlog as an operator-authorized
  exception, then land 42.1. Also mint a marshal fix story: a journaled `marshal seed accept <id>` re-record verb,
  reclassify the repo-owned artifacts (detectors.py, dreams README, detectors.yml) so routine edits don't trip it,
  and correct the wrong `update --force` remedy text."

## Acceptance Criteria

- **AC1 — Accept re-records a whole file.** In a fixture git repository whose state `run_adopt(apply=True)` wrote
  with a claim on `scripts/bmad-switch` (never a hand-written state), a committed edit to that file makes
  `run_adopt(apply=False)` refuse with `managed-content-modified`. `marshal seed accept bmad-switch` (dry run)
  prints the id, the path and `<recorded> -> <current>`, exits 0 and changes no file. `marshal seed accept
  bmad-switch --apply --reason "<text>"` exits 0. Afterwards the record's `body_sha` equals `hash_content` of the
  file, state has one `acceptances` entry with all nine fields, `git status --porcelain` names only
  `.marshal/seed-state.yml`, and `run_adopt(apply=False)` plans nothing and does not refuse.
- **AC2 — Accept re-records a hybrid region.** For a fixture whose `.gitignore` carries a recorded `model-ignores`
  region, a committed edit inside the region is refused by rung 6. `seed accept gitignore#model-ignores --apply
  --reason <text>` re-records that span's `body_sha`, `start` and `end`, and the record's `body_sha`, as adopt's
  `_hybrid_record` would build them from the file as it is. A bare `seed accept gitignore` re-records every region
  state records. Content outside the markers never matters. Afterwards rung 6 and `seed check` report nothing for it.
- **AC3 — Accept refuses what it must.** Each row of the I/O matrix below has a test asserting the error class, the
  exit code through the CLI, a message naming the reason and the id, and that no file changed. An unchanged hash
  exits 0 and writes nothing, and a second `--apply` adds no second entry.
- **AC4 — Accept writes only through the state store.** `seed/verbs/accept.py` calls `seed.state.store.write_state`
  exactly once per `--apply` that changes a hash, and no other writer. A meta-test reads the module's AST and fails
  on any write primitive: `fs.write`, `fs.replace_span`, `atomic_write_*`, `open(` in a write mode, `Path.write_text`
  or `Path.write_bytes`, or a `yaml` dump. A unit test with a spy on `write_state` asserts the one call and its
  `SeedState`.
- **AC5 — The journal is append-only and survives other writers.** After an acceptance, a later `adopt --apply` or
  `update --run` state write carries every `acceptances` entry byte-identical and in order. A state file with no
  `acceptances` key reads as an empty list and writes back without the key, so the bytes of a state that never
  accepted do not change. The schema rejects an entry missing a field or carrying an extra one, and `read_state`
  reports it as `state-invalid`.
- **AC6 — The repo's own files are repo-owned.** The packaged manifest declares `detector-registry`,
  `dreams-readme` and `detectors-ci-workflow` as `copied-seeded`, each with a rationale saying why the repo owns the
  file. The header counts read 2 `copied-managed` and 8 `copied-seeded`. `marshal seed explain detector-registry`
  prints the class and "never touched" / "expected and fine". `test_seed_templates_manifest.py`'s counts match.
  `model_version` stays `1.0.0`.
- **AC7 — The guard follows the manifest's current class.** In a fixture adopted while the three ids were
  `copied-managed`, so state still records them with that class and a hash, committed edits to all three files leave
  `run_adopt(apply=False)` with an empty plan and no refusal. `run_update`'s rung 6 does not refuse on them either,
  and `run_check` reports no finding for them. The same fixture with an edited `scripts/bmad-switch` still refuses. A
  `copied-seeded` record that `run_init` writes is not hash-guarded either.
- **AC8 — The remedies name accept.** `REMEDIES[MANAGED_FILE_MODIFIED]` and `REMEDIES[MANAGED_REGION_MODIFIED]` name
  `marshal seed accept` as the way to record an intended edit, and name `marshal seed update --force` only as the way
  to discard one. The two rows of `docs/finding-remedy-reference.md` match `REMEDIES` (the existing sync test).
  `docs/adoption-guide.md` replaces the line at `:71`, adds a passage on recording an intended edit, and its class
  table stays true. Rung 6's refusal remedy (`preconditions.py`) names `marshal seed accept <id>` beside reverting
  and `--force`. A new meta-test fails if any of `findings.py`, `preconditions.py`, `finding-remedy-reference.md` or
  `adoption-guide.md` says `update --force` accepts or keeps an edit as the new baseline, or if the two remedies and
  the adoption guide stop naming `marshal seed accept`.
- **AC9 — The verb is part of the CLI contract.** `marshal seed --help` lists `accept`. `marshal seed accept --json`
  and `--quiet` follow FR-123 and are enrolled in `tests/integration/test_cli_contract.py`. Every place that lists
  the seed verbs names `accept`: the `seed` parser's description, `cli/seed.py`'s module docstring, the package
  `README.md`'s verb table, and `.claude/skills/pyforge-marshal/` (its verb count, now eight, and its CLI block).
- **AC10 — The contract moves with the data.** In the same PR, the PRD's § *The Extraction Manifest* (`prd.md`
  COPIED · MANAGED and COPIED · SEEDED tables) and the Spec companion `extraction-manifest.md` move the three rows to
  COPIED · SEEDED, each with a dated note citing the 2026-10-12 ruling. The PRD's `updated:` carries a RE-STAMPED note
  and a short Currency reconciliation section, and no FR number moves. `chain-currency-sweep-check` exits 0, after
  re-stamping the spine and `epics.md` if the detector names them.
- **AC11 — The live oracle stays green and unwidened.** `marshal-local-recipes-seed-oracle` passes on the branch.
  `UNCLASSIFIED_DEFERRED_ARTIFACT_IDS` and `LOCAL_RECIPES_GENESIS_RECORDED_SKIP_ARTIFACTS` are unchanged (K-02). On a
  scratch commit that adds a `_DOCTOR_SOURCE_TASKS` row to `scripts/detectors.py`, a row to `docs/dreams/README.md`
  and a comment to `.github/workflows/detectors.yml`, the oracle still passes. That commit is dropped before the push.
- **AC12 — Mutation.** Each change below makes a named test fail:
  - `accept.py` writes the state file through anything but `write_state`: AC4's meta-test and spy.
  - Accept writes no `acceptances` entry: AC1's test.
  - Accept takes a `copied-seeded` or an unknown id: AC3's tests.
  - The guard reads the record's stored class instead of the manifest's: AC7's fixture.
  - The three ids go back to `copied-managed`: AC6's test and AC7's fixture.
  - The old `update --force` remedy text comes back in `findings.py` and both docs: AC8's meta-test.

## Boundaries & Constraints

**Always:**
- Hash with `seed.detect.hashes.hash_content` (and `region_body_text` for a region), the same function rung 6 and
  `seed check` use, so an accepted hash is the one the guard will compare.
- Write state only through `seed.state.store.write_state`, after validating against the packaged schema.
- Keep `acceptances` append-only. A verb that writes state carries it over unchanged.
- Read every verdict from the exit code, never through a pipe.
- Reconcile every governed path the change touches on the memlogs of the Specs that govern it, then stamp those
  Specs scoped: `spec-pyforge-marshal` and every co-governor `spec-surface-check` names, such as `spec-pyforge-core`
  for station `src/` (AGENTS.md pre-PR item 5).

**Never:**
- Never hand-edit `.marshal/seed-state.yml`, and never edit `SPEC.md` or `sprint-status-ledger.yaml` by hand.
- Never widen the oracle's exclusion set or its skip table (K-02), and never exempt this repo by name.
- Never edit `scripts/detectors.py`, `docs/dreams/README.md` or `.github/workflows/detectors.yml` to satisfy the guard.
- Never let `accept` write any file but `.marshal/seed-state.yml`, nor write in a dry run.
- Never change what `update --force` does (FR-101), and never make a remedy say it accepts an edit.
- Never bump `model_version` or register a migration here.

**Residual risk:**
- Accept trusts the operator's judgment: it records the bytes that are there. The guard still catches an edit
  nobody accepted, and the journal says who accepted what, and why.
- An older pyforge-marshal reading a state that holds `acceptances` refuses it as `state-invalid`
  (`additionalProperties: false`). Only a repo that has accepted something is affected, and the in-repo CLI is
  current.

## I/O & Edge-Case Matrix

| Invocation | Repo and state | Result |
|---|---|---|
| `seed accept bmad-switch` | `copied-managed`, recorded, file edited and committed | dry run: prints `<recorded> -> <current>`; exit 0; no write |
| `seed accept bmad-switch --apply --reason R` | same, clean worktree | hash re-recorded, one `acceptances` entry; exit 0 |
| `seed accept bmad-switch --apply --reason R` | hash unchanged | "nothing to record"; exit 0; no write |
| `seed accept bmad-switch --apply` | no `--reason` | `UsageError` (exit 2) |
| `seed accept bmad-switch --apply --reason R` | dirty worktree | `PreconditionFailure` `dirty-worktree` (exit 3) |
| `seed accept no-such-id` | — | `UsageError` (exit 2) naming the id |
| `seed accept detector-registry` | `copied-seeded` (after this story) | `PreconditionFailure`: repo-owned, nothing to accept |
| `seed accept cursor-rules` / `bmad-method` / `claude-skills` / `dreams-dir` | `generated-derived` / `referenced` / `unclassified-deferred` / directory | `PreconditionFailure`: no guard reads this class |
| `seed accept bmad-custom-config` | no state record | `PreconditionFailure`: not claimed |
| `seed accept readme-badge` | claimed, and a skip recorded later matches `README.md` | `PreconditionFailure`: skipped |
| `seed accept bmad-switch` | file absent, or a symlink out of the repo | `PreconditionFailure`: absent / escapes |
| `seed accept gitignore#model-ignores --apply --reason R` | region edited | that span re-recorded |
| `seed accept gitignore#no-such-region` | region not recorded | `PreconditionFailure`: not recorded |
| `seed accept gitignore` | markers do not parse | `PreconditionFailure`: unparseable |
| `seed accept bmad-switch --apply --reason R` | git resolves no committer identity | `PreconditionFailure`: no identity |

</intent-contract>

## Binding

- Parent Spec capabilities: `spec-pyforge-marshal` CAP-12, CAP-13, CAP-17, CAP-10 and CAP-11 (the seed verbs, Epics
  7-12; this repo's adoption, Story 86.2). No CAP is minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-12 (seed accept and repo-owned managed
  artifacts) entry.
- Requirements and architecture: FR-86, FR-101, FR-102 to FR-104, NFR-M3; AD-52 and AD-55, unchanged. The PRD's
  Extraction Manifest tables move three rows (AC10). No FR or AD number moves.
- Epic: Epic 97 (new). Epics 10-12 shipped the seed verbs and Epic 86 adopted this repo, and all are `done`.
  `epic-97` and `epic-97-retrospective` are minted with it.
- Ledger key: `97-1-seed-accept-records-an-intended-edit-and-repo-owned-files-leave-the-guard`.
- Ledger status at mint: `backlog`.
- Deps: — . Story 97.2 depends on this story.
- Surface: `marshal-policy.toml` `[epic_surfaces]."97"`, added with this mint.
- Spec: the `spec-pyforge-marshal` memlog records the ruling verbatim, the design and this mint.
- Minted 2026-10-12 in one chain commit with Story 97.2.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass, with AC1-AC9 and AC12's tests (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-marshal marshal-local-recipes-seed-oracle` — expected: pass, with the filter and skip table unchanged (AC11), in this checkout and in a fresh `git clone` of the branch run from a temp directory.
- AC11's scratch commit (a `_DOCTOR_SOURCE_TASKS` row, a Dream README row, a `detectors.yml` comment), then the oracle — expected: pass. Drop the commit.
- `pixi run --frozen -e pyforge-marshal marshal seed check --repo-root .` — expected: no HARD finding for `scripts/detectors.py`, `docs/dreams/README.md` or `.github/workflows/detectors.yml`.
- `pixi run --frozen -e pyforge-marshal marshal seed accept bmad-switch --repo-root .` — expected: a dry run that reports nothing to record, exit 0, `git status --porcelain` empty.
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.
- `python scripts/spec_surface_reconcile.py` and `pixi run --frozen -e pyforge-guild spec-surface-check` — expected: exit 0 after the memlogs and scoped stamps.
- `pixi run --frozen -e pyforge-guild chain-currency-sweep-check` — expected: exit 0 after AC10's PRD edit.
- The six mutations of AC12 — expected: each fails its named test. Restore each.
- `git diff origin/main...HEAD -- scripts/detectors.py docs/dreams/README.md .github/workflows/detectors.yml .marshal/seed-state.yml` — expected: empty.

## Named, not fixed here

- **`seed update`'s plan on this repo.** A dry run plans 12 actions, which Story 86.2's AC6 said it would not. That is
  Story 97.2, which depends on this story.
- **No packaged payload.** No `copied-managed` or `copied-seeded` entry ships whole-file content (`adopt.py`'s known
  limitation (1)). `marshal seed init` on a scratch directory exits 2 in `materialize()` ("staged path(s) outside the
  manifest boundary", measured 2026-10-12). Template authoring is its own effort. This story removes no remedy that
  works and adds none that depends on a payload.
- **The stored class string.** The three records in this repo's state keep `class: copied-managed` until a verb
  rewrites them. The guard reads the manifest. `marshal seed explain` reports the current class.
- **Herald's dossier.** `docsite/content/dossier.yml` says "seven verbs now". The dossier is Herald's, and Herald
  refreshes it from the shipped CLI.

## Spec Change Log

- 2026-10-12: minted from the operator's ruling "Sign off + fix story (Recommended)". The journal lives in the state
  file because one atomic write keeps the record and its journal together (P-08) and AD-52 allows one Genesis-owned
  file. The three repo-owned files become `copied-seeded` rather than having their hand lists moved out: that move
  would be cross-station and would still leave `detectors.yml` guarded.

## Review Triage Log

### 2026-10-12 — Review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings: (none — implementation verified against AC1–AC12 locally; review subagents skipped due to host usage limit)

## Auto Run Result

Status: done

Summary: Shipped `marshal seed accept` (eighth seed verb) with journaled hash re-records via optional `acceptances` in seed state; reclassified `detector-registry`, `dreams-readme`, and `detectors-ci-workflow` to `copied-seeded` so the guard follows the manifest’s current class; corrected remedies and docs to name accept for intended edits and `--force` only for discard.

Files changed: `seed/verbs/accept.py`, CLI and skill surfaces, state schema/store, manifest template, adopt/update/check/preconditions/findings, package docs, PRD and extraction-manifest companion, epics and ledger, and tests (unit, integration, meta).

Review: No patch or defer entries; verification green (`pyforge-marshal-test`, `pyforge-deps-test`, `marshal-local-recipes-seed-oracle`, `chain-currency-sweep-check`, `spec_surface_reconcile`, `spec-surface-check`).

Follow-up review recommendation: false

Verification: All commands in the Verification section passed on branch `dispatch/pyforge-marshal/97.1`.

Residual risk: Repos on an older pyforge-marshal that read a state file containing `acceptances` will report `state-invalid` until upgraded (documented in the story).
