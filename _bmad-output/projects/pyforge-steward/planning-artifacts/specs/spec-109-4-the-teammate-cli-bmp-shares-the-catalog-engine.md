---
title: '109.4: The teammate CLI bmp shares the catalog engine'
type: 'feature'
created: '2026-10-21'
status: 'ready-for-dev'
baseline_revision: '53aed16fe1957ab340c6146cb7bf0c3f810c1746'
flag:
  key: pyforge.steward.marketplace_pages
  provider: openfeature-file
  default: {production: off, staging: off, dev: on}
  scope: global
  fallback: 'bmp is not installed; skill install stays a folder copy described on the card'
  cleanup: 90 days after ON in every environment (Q4)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - src/shared/packages/pyforge-steward/src/pyforge/steward/catalog.py
  - src/shared/packages/pyforge-steward/catalog/marketplace/index.yaml
  - _bmad-output/projects/pyforge-steward/planning-artifacts/design-thinking-bmad-marketplace-2026-10-20/prototypes/p1-cli-transcript.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/design-thinking-bmad-marketplace-2026-10-20/prototypes/p2-index-schema.yaml
  - _bmad-output/projects/pyforge-steward/planning-artifacts/deferred-work-ledger.md
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The card tells a person to copy a folder. A teammate CLI named `bmp` was decided as the later face for find and install. It does not exist. Building it before the desk test would automate a path nobody has walked.

**Approach:** When this story starts, after P4's gate (two teammates have installed a skill with the manual copy and used it), add `bmp` as a console script. The command set is `prototypes/p1-cli-transcript.md`: `source`, task search, `info`, `install` from a GitHub release or Artifactory (checksum, `skills.lock`, both skill directories), agent install that skips an unconfirmed adapter unless asked, `outdated` / `update`, `uninstall`, `new` via bmad-builder, `bmp new skill --from-session` driven by `@bmp/skillify`, `lint`, and `publish` (pull request, clean-machine CI, CODEOWNERS). The index it reads is `prototypes/p2-index-schema.yaml` as committed in `index.yaml`. It calls `CatalogEngine` (the same engine `steward catalog` uses) for find, and copies a skill folder into both `.agents/skills/<scope>-<slug>/` and `.claude/skills/<scope>-<slug>/` for install. Do not add a steward duty. Do not route skill install through `bmad-method install --custom-source`. That path is `DW-FU-60-1-4` and stays open unless this story's acceptance criteria are changed to vendor module trees on purpose. Search and MCP wait on the P4 observation that people look in-tool first. Do not build `bmp install` before that two-teammate gate.

The flag block reuses `pyforge.steward.marketplace_pages` so a second key is not minted before the command exists. The implementer confirms that reuse when the command is the reader; if the command must be gated separately, they mint a new key in the same story and say so in the spec.

## Acceptance criteria

1. `bmp` is a console script. `pyforge steward --help` does not gain a duty. Duty-count tests are unchanged.
2. `bmp find` lists the same ids `load_listings` returns for `catalog/marketplace/index.yaml`, by calling the catalog engine or `marketplace_pages.load_listings`. It does not shell out to `pixi run -e`.
3. `bmp install <id> --source github|artifactory` copies that skill's folder into `.agents/skills/<scope>-<slug>/` and `.claude/skills/<scope>-<slug>/`, records `skills.lock`, and prints both destinations. It refuses, without writing, when a `requires` package entry has `published: false`, and the message names the package. It accepts the P2 list shape and the `{packages: [...]}` shape.
4. With the flag off, `bmp install` refuses with the station's usage exit and the flag key, and writes nothing. `bmp` stays listed in its own help.
5. A test shows `bmad-method install --custom-source` is not invoked.
6. `DW-FU-60-1-4` remains open. The story's dev notes say the folder copy did not close it.
7. The story does not start until two teammates have installed a seed with the manual copy and used it (P4). `@bmp/skillify` and `bmp new` wait on one merged contribution from someone other than rxm7706. An adapter is written only when that tool's format is confirmed.

## Boundaries

- No new GitHub repository. No upload. No change to `CatalogEngine.render`.
- Do not start this story until `MANUAL-CHECKLIST.md`'s Round 0 section has a recorded result (Story 109.5's gate, which may be a note in the checklist rather than code).

</intent-contract>

## Verification

**Commands:**

- `pixi run --frozen -e pyforge-steward python -m pytest src/shared/packages/pyforge-steward/tests/unit/test_bmp.py -q` — expected: exit 0 once the story adds that file. The test covers flag off (no copy) and flag on (two destinations, refusal on an unpublished package).

**Manual checks:**

- Run `bmp install mason/environment` in a scratch repo and confirm both skill directories, or the unpublished-package refusal, by reading the directories.
