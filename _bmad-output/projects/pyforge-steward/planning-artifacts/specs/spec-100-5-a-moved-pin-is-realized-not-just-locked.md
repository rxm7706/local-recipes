---
title: '100.5: A moved pin is realized, not just locked'
type: 'feature'
created: '2026-10-13'
status: 'ready-for-dev'
baseline_revision: '233e07909b5f7e89e49744cdeb642cdc0985b177'
flag:
  key: pyforge.steward.estate_refresh          # Story 100.2's (one flag per CAP)
  provider: openfeature-file                   # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: off, dev: on}   # Story 100.2's values
  scope: global                                # v1 is global only
  fallback: the `estate realize` verb refuses naming the flag; the register and its check are flag-free (a detector judges, it never changes behaviour)
  cleanup: with Story 100.2's flag, 90 days after ON in every environment (spec-feature-flag-governance Q4)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-100-2-one-command-moves-the-library-pins-on-the-policy-and-restores-what-the-upgrade-loses.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-install-class-wiring/install-class-playbook.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/release-cadence.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-bmad-suite-lifecycle/adoption-register.md
  - docs/intake/estate-refresh/PLAN-2026-10-13.md
  - src/shared/packages/pyforge-steward/src/pyforge/steward/upgrade.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/suite.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py
  - src/shared/packages/pyforge-steward/src/pyforge/steward/session.py
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/catalog.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/seed/detect/kit.py
  - recipes/bmad-suite/suite-members.yaml
  - scripts/sbom_laptop_gate.py
  - scripts/protected_refs_ruleset_check.py
  - CLAUDE.md
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** A moved pin stops at the lock. On 2026-10-13 the `bmad-method` floor moved to 6.12.2 and the lock holds
6.12.2 builds, while `_bmad/_config/manifest.yaml` still reads 6.12.0 and nothing asked `steward upgrade bmad-core`
(CAP-10) to follow. The same gap holds for every library whose install has a side effect beyond the pixi
environment: the skf module and its skills (`bmad-module-skill-forge update`), each suite module's wiring
(`steward provision --module`, CAP-18/23, and the install-class playbook, CAP-27/28), `bmad-loop`'s harness range
sites (CAP-12) and the eight loop homes, the caveman skill and hooks (`caveman-install --only claude --with-hooks`,
`CLAUDE.md`), the headroom proxy and the codegraph index (marshal's seed kit, CAP-162), the pre-commit hooks, the
16 pixi version sites, the CLIs warden and steward shell to, the local services and the import-probed platform
libraries. Each has its own installer and its own liveness probe; none is declared in one place, and nothing
confirms the estate is live at its pins. Operator direction 2026-10-13: not just updated in `pixi.toml` but
realized and implemented — installed, tested, confirmed.

**Approach:** One tracked register, `docs/governance/realization-register.yaml`, with
`docs/governance/realization-register.schema.json`; one repo-scope check, `scripts/realization_register_check.py`;
one verb, `estate realize`, on Story 100.2's duty. The register generalizes the bmad-suite install-class playbook
to every realized library.

- **Row shape.** `package`, `env` (the pixi environment the probe and test run in), `class` (`installer-tree` |
  `module` | `harness` | `kit` | `hooks` | `pin-sites` | `cli` | `service` | `import`), `realize` (argv, or
  `none`; `operator_gate: true` where it rewrites installer-owned or settings files), `probe` (argv and `expect`:
  `locked-version` — stdout or a named file holds the version `pixi.lock` has for `package` in `env`; `kit-ok` — a
  named item is `ok` in `marshal seed check --json`'s `result.kit`; `stage-ok` — named stages are green in
  `steward suite pipeline-truth --json`; `exit-0`), `test` (a pixi task or lane), `owner`, `authority`, `notes`.
- **Seeding (every row named here, nothing invented).**
  - `installer-tree`: `bmad-method` (realize `pyforge steward upgrade bmad-core --apply` then `upgrade
    prove-landed`, CAP-10, CAP-13, CAP-14, CAP-16; probe `_bmad/_config/manifest.yaml` `locked-version`; test
    `bmad-drift-check`, `bmad-estate-check`; `operator_gate`); `bmad-module-skill-forge` (realize
    `bmad-module-skill-forge update`; probe `_bmad/_config/skf-manifest.yaml`; `operator_gate`; team memory
    2026-09-06 on config preservation).
  - `module`: one row per member of `recipes/bmad-suite/suite-members.yaml` with an install class in the playbook
    (realize `pyforge steward provision --module <m>` where the playbook class provisions through the verb, else
    `none` with the class named; probe `stage-ok` on `pipeline-truth`'s `installed` and `wired`, CAP-21, CAP-28;
    test `pyforge-steward-test`).
  - `harness`: `bmad-loop` (realize `pyforge marshal refresh --project <slug>` per loop home, by subprocess into
    marshal's CLI, plus `upgrade pin-fan-out` (CAP-12) as the report; probe `bmad-loop --version` in
    `pyforge-marshal` `locked-version` and `bmad-loop validate` per home (CAP-13); test `pyforge-marshal-test`).
  - `kit`: `caveman-installer` (realize `caveman-install --only claude --with-hooks`, `operator_gate` — it writes
    the skill and hooks), `headroom-ai` (realize `none`; the proxy is a launcher), `codegraph` (realize the index
    through marshal's grammar); probe `kit-ok` on `marshal seed check --json` (CAP-162's envelope, the shape
    `session.py` already reads); test `marshal seed check`.
  - `hooks`: `pre-commit` (realize `pre-commit install --hook-type pre-commit --hook-type pre-push --hook-type
    commit-msg`; probe `precommit-config-check`; test the same).
  - `pin-sites`: `pixi` (realize `bump-pixi-version`; probe `pixi-version-check`; test the same).
  - `cli`: `gh`, `spec-kit`, `age`, `opengrep`, `osv-scanner`, `deptry`, `kubernetes-helm` (realize `none`; probe
    `<bin> --version` `locked-version` in the owning env; test the owning station's suite — `pyforge-warden-test`
    for the three engines, `pyforge-steward-test` for `age`, the platform chart tests for `helm`).
  - `service`: `postgresql`, `redis-server`, `silo` (realize `none`; probe `<bin> --version` `locked-version` in
    `platform-dev` and a boot through `scribe-pg-up` or the `platform-dev` twin; test `platform-ci-local --
    --test`).
  - `import`: one row per import the laptop SBOM gate already probes (`scripts/sbom_laptop_gate.py`), realize
    `none`, probe reused from the gate, test `sbom-laptop-gate`.
- **The check (`realization_register_check.py`).** Schema; a row whose `package` no feature declares; coverage
  without a list (ruling Q11): every `bmad-*` / `mybmad*` pin scribe's `read_pins` enumerates and every item
  marshal's seed kit lists must have a row; a `realize` whose first token is not a pixi task, a steward or marshal
  verb, or a binary the row's env locks. Exit 0 clean, 1 findings naming the package, 2 cannot read. A
  `realization-register-check` pixi task; one `scripts/detectors.py` entry (repo scope).
- **`estate realize`.** For each row whose package moved in the journal (`realize_due`), or `--all`: run `realize`
  — an `operator_gate` row only under `--yes`, else journaled `skipped-operator-gate` (ruling Q10) — then `probe`,
  and journal `{package, from, to, platform, realize: ran | skipped-operator-gate | none, probe: live | stale |
  missing}`. `--plan` prints the rows and writes nothing; agents run `--plan`. A moved `bmad-method` or `bmad-*`
  floor also runs `upgrade bmad-core` pre-flight (CAP-9) and `upgrade pin-fan-out` (CAP-12) and writes both
  verdicts into the journal's `bmad` block; for a moved suite member it runs `suite pipeline-truth` (CAP-21) and
  names `suite advance` (CAP-22) as the next operator step, never advancing. `estate refresh` ends by listing the
  `realize_due` rows; `estate verify` (Story 100.4) runs every row's probe and each distinct test.
- **Runbook pointer.** `release-cadence.md` step 7 points at `estate refresh` and `estate realize` for the pixi
  floor bumps, `environment.yaml` and the re-apply.

Ledger key: `100-5-a-moved-pin-is-realized-not-just-locked`.
Type / Effort / Deps: feature / M / S-100.2.

### Living CAP citations

- **`spec-pyforge-steward` CAP-167** (FR-40): the register, its check and the realize verb.
- **CAP-9, CAP-10, CAP-12, CAP-13, CAP-14, CAP-16** (the core apply), **CAP-18, CAP-23** (module provisioning),
  **CAP-21, CAP-22** (pipeline-truth, advance), **CAP-24, CAP-27, CAP-28** (install matrix and classes), **CAP-162**
  (the seed-kit envelope): each is a realize or probe command, reused, never re-implemented.
- **AD-1**: every realize and probe is a subprocess into the library's own installer or an existing steward or
  marshal verb; steward imports nothing from `pyforge.marshal` or `pyforge.scribe`. **AD-8**: child exit codes are
  recorded, `main()` projects the duty's.
- **Flag:** Story 100.2's `pyforge.steward.estate_refresh`; the check is `detector-or-gate` by nature and runs
  flag-free.
- **Origin.** The 2026-10-13 Dream entry and the operator direction of the same day; rulings Q10 and Q11.

## Acceptance Criteria

- **AC1 — Seeded and covered.** The register validates and holds every row the Seeding list names;
  `python scripts/realization_register_check.py` exits 0 on the tree; removing the `bmad-loop` row, or a seed-kit
  item's row, makes it exit 1 naming the package; a row for a package no feature declares exits 1.
- **AC2 — Realize per class.** With every installer faked, `estate realize` over a journal whose moves include
  `bmad-method`, `bmad-loop`, `caveman-installer`, `pre-commit` and `pixi` records exactly the Seeding list's argv
  per row, runs `operator_gate` rows (`bmad-method`, `bmad-module-skill-forge`, `caveman-installer`) only under
  `--yes` and journals `skipped-operator-gate` otherwise, runs each probe after its realize, and never runs a probe
  that writes (the fake asserts no write argv).
- **AC3 — Probes.** A manifest fixture at 6.12.0 against a 6.12.2 lock yields `probe: stale` for `bmad-method` and
  the pre-flight report in the `bmad` block; a `marshal seed check --json` fixture with `headroom` `missing`
  yields `missing`; a `pipeline-truth` fixture with `wired: false` for `tea` yields `stale`; `bmad-loop --version`
  equal to the lock yields `live`.
- **AC4 — Plan writes nothing.** `estate realize --plan` prints the due rows and records no realize, probe or
  journal write.
- **AC5 — Wired and pointed.** `pixi run --frozen -e pyforge-guild realization-register-check` exits 0;
  `scripts/detectors.py` lists it once; `detectors-ci` stays green; `release-cadence.md` step 7 names `estate
  refresh` and `estate realize`.
- **AC6 — Nothing live.** No test runs a real installer, `caveman-install`, `pre-commit install`, `marshal`,
  `bmad-module-skill-forge` or the network; `_bmad/**`, `.claude/skills/**` and `.claude/settings.json` at `HEAD`
  are unchanged by the suite.

## Boundaries & Constraints

- Installer-owned trees are written only by their own installers, only under `--yes`, only by the operator; a
  probe never writes.
- The register is the one declared source: the duty holds no class list, no package list and no command strings
  outside it; coverage is read from scribe's `read_pins` and marshal's kit list, never a list in the check.
- `suite advance` and `anaconda upload` are never run by the refresh (CAP-22's contract).
- No doctor surface is written; doctor's drift warnings stay on doctor's chain.

## I/O & Edge-Case Matrix

| Input | Expected |
|---|---|
| a `module` row whose playbook class is `native-only` | `realize: none`, probe still runs, class named in the row |
| `marshal seed check --json` exits 1 with `result.kit` present | kit items read from the envelope (CAP-162), not "unparseable" |
| `bmad-loop` moved but a loop home fails `validate` | `probe: stale` naming the home |
| a `cli` row whose binary is absent from its env | `probe: missing` |
| `--all` with no journal | every row realized (gates honored) and probed; journal created with `moves: []` |
| `--yes` run by an agent through Bash | the session hook denies (`steward-estate-transitive` row's sibling, `steward-estate-realize-yes`, added here) |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-steward` CAP-167 (FR-40), minted 2026-10-13.
- Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-13 (estate refresh) entry.
- Epic: Epic 100, Stories 100.1–100.7.
- Ledger key: `100-5-a-moved-pin-is-realized-not-just-locked`.
- Ledger status at mint: `backlog`.
- Deps: S-100.2. `marshal factory dispatch` stamps `baseline_revision` with the launch commit (Story 100.1's run did), so no
  hand re-base is needed. Story 100.4 waits
  on this story for the probes.
- Surface: `marshal-policy.toml` `[epic_surfaces]."100"` (added with the mint; widened the same day for the
  register and the installer-owned trees).
- Minted 2026-10-13 in one chain commit.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Run before the push (not dispatch gates):**
- `pixi run --frozen -e pyforge-guild realization-register-check` — expected: exit 0 (AC1, AC5). This story creates the task, so it is never a launch-bound gate (MRS-GATE-011).
- `pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_realization_register_check.py -q` — expected: pass (AC1).
- `pixi run --frozen -e pyforge-steward python -m pytest src/shared/packages/pyforge-steward/tests/unit/test_estate_realize.py -q` — expected: pass (AC2–AC4).
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` — expected: pass.
- `pixi run --frozen -e pyforge-guild detectors-ci` and `lint-types` — expected: exit 0.
- `python3 .claude/hooks/pre-shell.py` self-check (the roster/matcher assertion, after the `steward-estate-realize-yes` row) — expected: passes.
- `pixi run --frozen -e pyforge-guild python scripts/spec_surface_reconcile.py` and `spec-surface-check` — expected: exit 0 after the memlog entries and the scoped stamps.
- `pixi run --frozen -e pyforge-guild pr-preflight` — expected: exit 0.

## Spec Change Log

- 2026-10-13: minted with CAP-167 / FR-40 and Epic 100 as "A moved BMAD floor hands to the core apply…", then
  re-titled the same day on the operator's direction (realized, not just locked: bmad, caveman, headroom and every
  installed-and-tested library confirmed) with the realization register, its check and `estate realize`; rulings
  Q10 and Q11 adopted. `type: feature`, Story 100.2's flag.
