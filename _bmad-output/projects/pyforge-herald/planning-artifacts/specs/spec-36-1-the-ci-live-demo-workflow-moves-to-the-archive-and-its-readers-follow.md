---
title: '36.1: The CI live-demo workflow moves to the archive and its readers follow'
type: 'fix'
created: '2026-10-10'
status: 'ready-for-dev'
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/SPEC.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-19-2-one-real-ship-records-itself-against-a-persistent-store.md
  - _bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-13-6-a-ship-records-itself-end-to-end.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/live-proof-surfaces.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
  - .github/workflows/herald-live-demo.yml
  - .github/actions-policy.toml
  - scripts/pixi_version_registry.py
  - scripts/pixi_version_check.py
  - scripts/bump_pixi_version.py
  - scripts/docs_pixi_tasks.py
  - src/shared/packages/pyforge-doctor/tests/unit/test_sources_live_proof_surfaces.py
  - docs/reference/github-workflows.md
  - docs/how-to/github-actions-recipe-ci.md
  - docs/how-to/pixi-tasks.md
  - docs/how-to/run-herald-live-backend-locally.md
  - src/shared/packages/pyforge-herald/docs/operator-guide.md
  - src/shared/packages/pyforge-herald/docs/cli-runbooks.md
  - src/shared/packages/pyforge-herald/docs/automation-troubleshooting.md
  - src/shared/packages/pyforge-herald/src/pyforge/herald/webhook.py
  - src/shared/packages/pyforge-herald/src/pyforge/herald/webhook_host.py
  - src/shared/packages/pyforge-herald/pyproject.toml
  - src/shared/packages/pyforge-herald/tests/unit/test_webhook_live_smoke.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `.github/workflows/herald-live-demo.yml` is a retired proof that live files still present as current.

- **What it is.** Story 13.6 added it as a bounded, CI-contained demo of the webhook and the scheduler. Two of its three
  jobs start a standalone `pyforge.herald.webhook_host:application` under daphne (`:162`, `:267`). That is the
  per-station process Story 19.2 rejects (AGENTS.md § Policy: no `:800x` process tree; AD-14 as built: no bespoke
  Herald perimeter). All three jobs use a `runner.temp` store (`:157`, `:262`, `:385`), and the webhook jobs need a
  repository secret (`:41`).
- **Its state.** The Actions API reads `disabled_manually` (checked 2026-10-10). It has 769 runs, the last on
  2026-08-24, and the last 100 all failed.
- **Why it can go.** Story 19.2 proves a ship on this machine's loopback host, against the primary checkout's
  persistent store, with a local caller (`herald-ship-local`) and an opt-in restart smoke test. After 19.2 lands, the
  workflow proves nothing the estate still needs.
- **Who still names it** (measured on `origin/main` `8046e1b83d`, 2026-10-10):
  - `scripts/pixi_version_registry.py:82-83`: an `exact` site with `hits=3`. `pixi-version-check` reports
    `missing-file` if the file moves while the site stays, and `bump-pixi-version` rewrites its three pins
    (`:75`, `:255`, `:372`).
  - Doctor's `doctor:CAP-77` catalog, herald's *Live webhook host* row
    (`spec-pyforge-doctor/live-proof-surfaces.md:28`): both the "How to prove it live" cell and the "Surface globs"
    cell name the workflow.
  - `_HERALD_NAMED_NON_PACKAGE_PATHS` in `pyforge-doctor/tests/unit/test_sources_live_proof_surfaces.py:457-460`, the
    test's named exceptions for herald paths outside the package. The test reads only paths that `git ls-files`
    lists, so a missing path never reds it. A stale exception is still a lie in a gate's own code.
  - The workflow inventories: `docs/reference/github-workflows.md:20` and `docs/how-to/github-actions-recipe-ci.md:31`.
  - The Actions policy's comment, `.github/actions-policy.toml:24` ("Herald live demo (weekly + PR)").
  - Herald's own files: `docs/operator-guide.md:31,181`; `docs/cli-runbooks.md:17,162,304,493,496,509,520`;
    `docs/automation-troubleshooting.md:12,31,46,164`; `src/pyforge/herald/webhook.py:19`;
    `src/pyforge/herald/webhook_host.py:7,72`; `pyproject.toml:60`; `tests/unit/test_webhook_live_smoke.py:10`.
    Story 19.2's AC9 rewrites part of the two runbooks first, and its new
    `docs/how-to/run-herald-live-backend-locally.md` explains "why `herald-live-demo.yml` is not the proof". The line
    numbers above are from before 19.2 lands. AC7's grep is the authority, not this list.
  - The `bump-pixi-version` description, `pixi.toml:1244`, lists sites by name ("… herald-live-demo.yml's 3 pins …"),
    and `docs/how-to/pixi-tasks.md:186` renders it.
- **What is not a reader.** About 20 historical planning files under `_bmad-output/`, the Dreams' dated entries, and
  `pixi.toml`'s dated 2026-08-21 `requires-pixi` comment (`:10`, `:13`) mention the workflow as history. No Spec's
  `surface:` governs the workflow file.

**Approach (operator ruling 2026-10-10, chosen option verbatim: "Archive after 19.2"):**

> "Mint a herald fix story now (Deps: S-19.2): git mv to archive/.github/workflows/, repoint doctor's catalog row and
> test exceptions, drop the pixi_version_registry entry, update inventories/docs, generalise the bump-pixi-version
> description; reconcile doctor/herald/core specs."

- **The move.** Run `git mv .github/workflows/herald-live-demo.yml archive/.github/workflows/herald-live-demo.yml` and
  leave the content alone. CHAIN-STANDARD §11 (`docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md:225-232`)
  says everything the fleet retires goes to `archive/<original path>`, structure-preserving, and "Nothing is deleted;
  every move is a `git mv`". `archive/` already holds non-doc files (`archive/_bmad-output/…`). GitHub reads workflows
  only from `.github/workflows/`, so the moved file never runs. No README is added under `archive/.github/`. The rule
  does not ask for one, and the inventory line in AC6 records the supersessor.
- **The registry.** Delete the one `_site("herald-live-demo.yml setup-pixi (3 jobs)", …)` entry (`:82-83`) and change
  no other site. `pixi-version-check` then has nothing to report for the moved file.
- **The bump description.** Rewrite the `bump-pixi-version` description so it names the registry, not its sites, for
  example: "Mutator: rewrite every site in scripts/pixi_version_registry.py to one target pixi version in a single
  pass, then …". Keep the rest of the sentence as it is: the `environment.yaml` regeneration, the convergence re-check,
  the image-tag check and the usage line. A site list in prose is what went stale here, and it went stale before
  (`pixi.toml:13` records three earlier miscounts). Then regenerate `docs/how-to/pixi-tasks.md` with `docs-pixi-tasks`,
  which also advances the page's `docs/map.yaml` stamp. Leave the dated 2026-08-21 `requires-pixi` comment alone: it
  is history, and it names the registry as the authority.
- **Doctor's row.** Herald owns it (the *Station* cell reads `herald`), and doctor owns the catalog. In the herald
  *Live webhook host* row:
  - the "How to prove it live" cell names the opt-in smoke test (`HERALD_LIVE_WEBHOOK=1`,
    `test_webhook_live_smoke.py`: a real daphne process, a signed POST over loopback, and 19.2's restart case), plus
    19.2's local run (`docs/how-to/run-herald-live-backend-locally.md`, `herald-ship-local`);
  - the "Surface globs" cell keeps
    `src/shared/packages/pyforge-herald/src/pyforge/herald/webhook_host.py` and drops the workflow;
  - nothing else in the catalog changes.
- **Doctor's test.** `_HERALD_NAMED_NON_PACKAGE_PATHS` keeps `"scripts/deck_export.py"` only. The comment above it
  (`:450-456`) says one path, the PPTX-export script, and still says why it is a named exception.
- **The inventories, the policy comment, herald's files.** Each live mention is removed, or rewritten to name the
  archive path as history. Herald's docs point at 19.2's how-to for the live host. In `webhook.py`, `webhook_host.py`
  and `test_webhook_live_smoke.py` only docstrings change, and in `pyproject.toml` only a comment, so no behaviour
  moves. Where a sentence's claim stops being true without the workflow, it is corrected, not just re-pointed. Two
  examples: "the ONLY place that webhook host runs today is inside `herald-live-demo.yml`", and
  `webhook_host.py:72`'s "Every job in `herald-live-demo.yml` starts one throwaway process … so this residual is
  currently inert". After 19.2, a host does run persistently and DW-13-6-2 is reachable; 19.2's spec says so. If 19.2
  already corrected a sentence, it stays as 19.2 left it.

Ledger key: `36-1-the-ci-live-demo-workflow-moves-to-the-archive-and-its-readers-follow`.
Type / Effort / Deps: fix / M / S-19.2.

### Living CAP citations

- **Shipped behaviour.** `spec-pyforge-herald` CAP-38 (← `spec-herald-moments-2-4-live-backend` LB-2, the webhook
  endpoint). Story 13.6 shipped the workflow as that capability's CI-contained demo, and Story 19.2 replaces it as the
  proof. Retiring a demo surface adds no behaviour, so this story mints no CAP and registers no FR.
- **Cross-station rows.** Doctor's `doctor:CAP-77` catalog is doctor's, and its herald row describes herald's
  surface. Herald edits only that row and the herald exception in doctor's test, as the ruling orders. The pixi
  version registry and the `bump-pixi-version` task are the estate's: the registry entry goes, and the description
  is generalised. No other site, task or check changes.
- **Architecture.** AD-14 as built (the webhook mounts on the host ASGI; no bespoke Herald perimeter) is why the
  standalone-process demo is not a proof. No AD is amended.
- **No flag.** Under `spec-feature-flag-governance` Q1, a `fix` needs no flag. The story ships no runtime behaviour.
- **Origin.** The station Dream's 2026-10-10 (live demo archive) entry. That entry supersedes, from Story 19.2's close
  only, the 2026-10-10 (live backend, local host) constraint that the workflow "stays disabled and unchanged".

## Acceptance Criteria

- **AC1 — the gate.** Given this story is dispatched, When its preflight reads the tree, Then Story 19.2 is `done` on
  main. Both tests hold: herald's ledger row
  `19-2-one-real-ship-records-itself-against-a-persistent-store` reads `done`, and its landing is an ancestor of
  `origin/main` (`git merge-base --is-ancestor <19.2 landing> origin/main` exits 0). Otherwise the story stops and
  changes nothing: AC7 of 19.2 and its Never list still hold.
- **AC2 — the move.** Given the gate holds, When `git mv .github/workflows/herald-live-demo.yml
  archive/.github/workflows/herald-live-demo.yml` runs, Then all of these hold:
  - `git ls-files .github/workflows/herald-live-demo.yml` prints nothing;
  - `git ls-files archive/.github/workflows/herald-live-demo.yml` prints the path;
  - `git diff --find-renames=100% --name-status origin/main...HEAD -- .github/workflows/herald-live-demo.yml
    archive/.github/workflows/herald-live-demo.yml` prints exactly one `R100` line, because the file is byte-identical
    to its last live version.
- **AC3 — the registry.** Given the moved tree, Then:
  - `scripts/pixi_version_registry.py` has no site naming `herald-live-demo`, and no other site changed (the diff
    removes the one two-line `_site(…)` call and adds nothing);
  - `pixi run -e pyforge-guild pixi-version-check` exits 0;
  - the scripts suite (`pixi run -e pyforge-ci pyforge-doctor-scripts-test`, which runs
    `tests/scripts/test_pixi_version_check.py`) passes.
- **AC4 — the bump description.** Given `pixi.toml`, When `git diff origin/main...HEAD -- pixi.toml` runs, Then:
  - it changes exactly one line, the `description` of `[feature.local-recipes.tasks.bump-pixi-version]`;
  - that description says it rewrites every site in `scripts/pixi_version_registry.py`, and names no workflow,
    Containerfile, action or site count;
  - its `cmd`, and the dated `requires-pixi` comment (`:10`–`:13` on `8046e1b83d`), are unchanged.

  Also:
  - `pixi run -e pyforge-guild docs-pixi-tasks` has regenerated `docs/how-to/pixi-tasks.md` and `docs/map.yaml`'s
    stamp for it;
  - `pixi run -e pyforge-guild docs-currency-check` exits 0;
  - `environment.yaml`, regenerated as AGENTS.md § Policy requires
    (`pixi project export conda-environment -e build > environment.yaml`), is byte-unchanged;
  - `pixi.lock` is unchanged.
- **AC5 — doctor's catalog row and test.** Given `spec-pyforge-doctor/live-proof-surfaces.md`, Then:
  - in the herald *Live webhook host* row, the "How to prove it live" cell names `HERALD_LIVE_WEBHOOK=1`,
    `test_webhook_live_smoke.py`, `docs/how-to/run-herald-live-backend-locally.md` and `herald-ship-local`, and does
    not name the workflow;
  - its "Surface globs" cell is exactly `src/shared/packages/pyforge-herald/src/pyforge/herald/webhook_host.py`;
  - `git diff origin/main...HEAD` on the file changes that one table row only.

  Given `test_sources_live_proof_surfaces.py`, Then:
  - `_HERALD_NAMED_NON_PACKAGE_PATHS == ("scripts/deck_export.py",)`, and its comment names one path;
  - `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` passes;
  - with `"scripts/deck_export.py"` removed from the tuple (the mutation),
    `test_zero_false_positives_against_the_live_tracked_tree` fails. The remaining exception is still load-bearing.
    Restore the tuple afterwards.
- **AC6 — the inventories and the policy comment.** Then:
  - `docs/how-to/github-actions-recipe-ci.md` has no `herald-live-demo.yml` row;
  - in `docs/reference/github-workflows.md`, no table lists the workflow as active, and one dated line records the
    move: the date, `archive/.github/workflows/herald-live-demo.yml`, this story, and its supersessor, 19.2's
    `docs/how-to/run-herald-live-backend-locally.md`;
  - `.github/actions-policy.toml`'s comment no longer lists "Herald live demo";
  - `git diff origin/main...HEAD -- .github/actions-policy.toml` touches comment lines only, so `enabled` and
    `allow_when_enabled` parse unchanged.
- **AC7 — no live file names the live path.** Given the finished tree, Then:
  - `git grep -nP '(?<!archive/)\.github/workflows/herald-live-demo\.yml' -- . ':(exclude)_bmad-output/**'
    ':(exclude)docs/dreams/**' ':(exclude)pixi.toml'` exits 1 (no match);
  - `git grep -nP '(?<![/\w-])herald-live-demo\.yml' -- . ':(exclude)_bmad-output/**' ':(exclude)docs/dreams/**'
    ':(exclude)archive/**' ':(exclude)pixi.toml'` exits 1, so no bare filename survives either;
  - `git grep -n 'herald-live-demo' -- _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/live-proof-surfaces.md`
    exits 1;
  - every line `git grep -n 'herald-live-demo' -- pixi.toml` prints is in the dated `requires-pixi` comment at the top
    of the file, never the `bump-pixi-version` description.

  On today's tree, the first two commands together print the full reader list in § Intent.
- **AC8 — herald's behaviour does not move.** Then:
  - the diff to `webhook.py`, `webhook_host.py` and `test_webhook_live_smoke.py` changes docstrings only;
  - the diff to `pyproject.toml` changes comments only (`tomllib` parses the file identically before and after);
  - every herald sentence that claimed the workflow is the only place the host runs, or that DW-13-6-2 is inert
    because of it, is corrected or removed;
  - `pixi run --frozen -e pyforge-herald pyforge-herald-test` and `pixi run -e pyforge-guild lint-types` pass.
- **AC9 — reconcile and close.** Then:
  - every Spec `pixi run -e pyforge-guild spec-surface-check` names has a dated memlog entry naming its paths and the
    reason, and a scoped stamp (`--spec <project>/<spec>`, after `git add`, from a clean tree), and the check exits 0.
    The detector decides the set. On `8046e1b83d` the baseline lists:
    - `spec-pyforge-herald` (herald docs, `webhook.py`, `webhook_host.py`, `pyproject.toml`, the smoke test);
    - `spec-pyforge-core` (`webhook.py`, `webhook_host.py`, `pixi.toml`);
    - `spec-design-code-bridge` (`pyproject.toml`);
    - `spec-pyforge-doctor` (the doctor test, `github-actions-recipe-ci.md`, `pixi-tasks.md`, `docs/map.yaml`);
    - the other seven Specs that govern `pixi.toml`: `spec-pixi-candidate-currency`, `spec-deck-family-currency`,
      `spec-deck-family-lockstep`, `spec-pyforge-pages`, `spec-bmad-loop-baseline-drift`, `spec-pyforge-marshal` and
      `spec-pyforge-unifying-strategy`, with `spec-pyforge-core` already counted above.

    `spec-pyforge-doctor`'s memlog also records the catalog-row edit.
  - `pixi run -e pyforge-guild pyforge-station-tests` passes before the push, because a `pixi.toml` change fires every
    station suite in CI.
  - The PR carries the `maintenance` label.
  - On landing, the ledger key becomes `done` through the Tier-3 feed and `sprint-ledger-sync`, and `epic-36` follows.

## Boundaries & Constraints

**Always:**
- Check the gate (AC1) before touching any file.
- Move with `git mv`, content untouched. If a `bump-pixi-version` run on `main` rewrote the pins after 19.2 landed, the
  archived copy carries those pins. That is still its last live version.
- Repoint each reader to what 19.2 actually landed: the how-to's path, the task name and the smoke test's restart case.
  Read them from `main` at dispatch, and never from 19.2's spec alone.
- Keep `pixi.toml`'s change to the one description line.
- Reconcile and stamp every Spec the detector names, one `--spec` each, and never run a bare `--write-baseline`
  (AGENTS.md pre-PR item 5).

**Never:**
- Never `git rm`, rewrite or re-enable the workflow, or add a workflow, a CI lane or a GitHub setting in its place.
- Never change herald's webhook, host, caller or scheduler behaviour. Only docstrings, comments and docs change in the
  herald package.
- Never edit another row of doctor's catalog, another named exception in doctor's test, another registry site, or any
  `pixi.toml` line except the `bump-pixi-version` description.
- Never edit the historical planning files under `_bmad-output/` that mention the workflow (story specs, memlogs other
  than the reconcile entries, epics, PRDs, ledgers, research), or a Dream's dated entry.
- Never edit `SPEC.md`, the PRD or the spine.
- Never run `bump-pixi-version`, and never hand-edit a pixi pin.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| gate not met | 19.2 not `done`, or its landing not an ancestor of `origin/main` | nothing changes | the story stops at AC1, naming which test failed |
| moved, registry kept | the file under `archive/`, the site still at `:82` | `pixi-version-check` reports `missing-file` | AC3 fails; drop the site |
| registry dropped, file kept | the site gone, the file still live | `pixi-version-check` stays green, but AC2 fails | move the file |
| a pixi bump landed after 19.2 | the pins rewritten on `main` | archived as they stand, still an `R100` rename against the merge base | not a defect |
| 19.2 already rewrote a runbook line | `cli-runbooks.md` names the how-to | left as 19.2 wrote it | AC7's grep is the check |
| 19.2's how-to names the workflow | "why `herald-live-demo.yml` is not the proof" | rewritten to name the archive path, or reworded | AC7's bare-name grep catches it |
| doctor exception still needed | `scripts/deck_export.py` removed from the tuple | the live-tree test fails | restore it; the mutation proves it |
| the PR touches the moved path | doctor's `live-proof-surface-check` | at most one advisory WARN | advisory, never a gate |
| historical mention | a 2026-09 story spec names the workflow | unchanged | excluded from AC7 by path |

</intent-contract>

## Binding

- Dream: `docs/dreams/pyforge-herald.md` § *Realization log*, the 2026-10-10 (live demo archive) entry.
- Spec: `spec-pyforge-herald` CAP-38 (← LB-2), as the demo's origin. No CAP is minted.
  `spec-pyforge-herald/.memlog.md` records the ruling verbatim, the decisions and the mint.
- Architecture: AD-14 as built, unchanged.
- Epic: Epic 36 (minted with this story). Epic 19 closes when Story 19.2 lands, and its HARD boundary
  (`herald-live-demo.yml` stays disabled) binds Epic 19's stories. That is why the archive opens its own epic.
- Ledger key: `36-1-the-ci-live-demo-workflow-moves-to-the-archive-and-its-readers-follow`.
- Ledger status at mint: `backlog`.
- Deps: S-19.2 (station-local, so marshal's `Deps:` parser gates it).
- Dispatch note: `marshal-policy.toml` `[epic_surfaces]."36"` (added with this mint) admits:
  - the workflow and its archive path;
  - `.github/actions-policy.toml`;
  - the registry;
  - `pixi.toml`, `pixi.lock` and `environment.yaml`;
  - the two inventories, `docs/how-to/pixi-tasks.md` and `docs/map.yaml` (its stamp; `docs/MAP.md` renders no stamp,
    so it does not move);
  - 19.2's how-to;
  - doctor's catalog file and the doctor test;
  - the herald package;
  - herald's story specs;
  - the spec-surface baseline and every Spec memlog.

  Nothing else is admitted.
- Minted 2026-10-10 in one chain commit (CHAIN-STANDARD §5 filename).

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-herald pyforge-herald-test`: expected to pass (the station's `verify_commands`).
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test`: expected to pass.
- `pixi run -e pyforge-ci pyforge-doctor-scripts-test`: expected to pass.
- `pixi run -e pyforge-guild pixi-version-check`: expected to exit 0.
- `pixi run -e pyforge-guild docs-currency-check` and `pixi run -e pyforge-guild docs-map-hygiene-check`: expected to
  exit 0.
- `pixi run --frozen -e pyforge-guild lint-types`: expected to exit 0.
- `pixi run -e pyforge-guild spec-surface-check`: expected to exit 0 after the memlog reconciles and scoped stamps.
- `pixi run -e pyforge-guild pyforge-station-tests`: expected to pass.
- AC7's four `git grep` commands: each expected to exit as AC7 says. Read each exit code directly, never through a
  pipe.

**Manual checks (not a dispatch gate):**
- Mutation, registry: with the file moved and the site restored, `pixi run -e pyforge-guild pixi-version-check` is
  expected to exit non-zero, naming `missing-file` for `.github/workflows/herald-live-demo.yml`. Drop the site again.
- Mutation, doctor: AC5's tuple mutation is expected to fail the live-tree test. Restore the tuple.
- `gh api repos/rxm7706/local-recipes/actions/workflows --jq '.workflows[] | select(.path | endswith("herald-live-demo.yml")) | .state'`
  after the merge. Expected: the workflow is listed as `disabled_manually` or no longer listed. GitHub keeps a record
  for a workflow file that has been removed, so either answer is fine, and no run starts.

## Spec Change Log

- No change yet.
